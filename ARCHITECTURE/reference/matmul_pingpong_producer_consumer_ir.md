# Matmul ping-pong producer/consumer IR note

## 目的

本文记录 matmul dynamic/dynamic 场景中，`multi-buffer` 之后做 ping-pong 调度时，`producer-consumer-analysis` 的消费关系如何理解、为什么不能原样继承旧 event attr，以及推荐的 IR 改写位置。

本文是架构参考说明，不是正式计划书，不创建任务边界，不修改公开 API。

## 当前约束

- 当前基线 dump：
  - `kernel/dump/matmul/inputs_dynamic_tile_dynamic/24-multi-buffer.mlir`
  - `kernel/dump/matmul/inputs_dynamic_tile_dynamic/25-producer-consumer-analysis.mlir`
- `25-producer-consumer-analysis.mlir` 是当前基线 dump，用于说明 `multi-buffer` 后、ping-pong 前的原始依赖关系。
- 如果 `loop-pingpong` 要保持通用，不应强依赖 `producer-consumer-analysis` 的 event attr。推荐顺序是：

```text
24 multi-buffer
25 loop-pingpong
26 producer-consumer-analysis
27 memory-pool
28 cse
29 canonicalize
...
```

也就是说，`loop-pingpong` 应基于 ring current / advance 语义、MemoryEffect 与 alias 关系自行识别可调度段；`producer-consumer-analysis` 放在 ping-pong 后，对最终调度 IR 重新标注。若后置分析需要看懂跨迭代 ring slot 消费，它也需要具备 ring-aware 规则，或者由 ping-pong 输出显式可分析的 loop-carried slot。

## Ping-pong 前的 IR 与消费关系

`24-multi-buffer.mlir` 中，K 循环仍是顺序形态：

```text
symbol.for %k = 0 to K step TILE_K {
  current_ring(tsm A/B)
  global -> tsm A/B

  current_ring(tlm A/B)
  tsm -> tlm A/B

  kernel.matmul(acc, tlm A, tlm B, acc_flag)

  advance_ring(...)
}
```

在 `25-producer-consumer-analysis.mlir` 中，分析 pass 给这条链标注 event。简化后的真实结构如下：

```mlir
symbol.for %k = %c0 to %K step %TILE_K {
  %tsm_a_slot = "dma.current_ring"(%tsm_a_ring)
  %tsm_a = "dma.reinterpret"(%tsm_a_slot, ...)
  %global_a = "dma.reinterpret"(%lhs, ...)
  "dma.deslice"(%tsm_a, %global_a, ...)
    {productor = [8]}

  %tsm_b_slot = "dma.current_ring"(%tsm_b_ring)
  %tsm_b = "dma.reinterpret"(%tsm_b_slot, ...)
  %global_b = "dma.reinterpret"(%rhs, ...)
  "dma.deslice"(%tsm_b, %global_b, ...)
    {productor = [9]}

  %tlm_a_slot = "dma.current_ring"(%tlm_a_ring)
  %tlm_a = "dma.reinterpret"(%tlm_a_slot, ...)
  "dma.copy"(%tlm_a, %tsm_a)
    {consumer = [8], productor = [10]}

  %tlm_b_slot = "dma.current_ring"(%tlm_b_ring)
  %tlm_b = "dma.reinterpret"(%tlm_b_slot, ...)
  "dma.copy"(%tlm_b, %tsm_b)
    {consumer = [9], productor = [11]}

  %acc_flag = symbol.ne %k, %c0
  "kernel.matmul"(%acc, %tlm_a, %tlm_b, %acc_flag)
    {consumer = [10, 11], after_loop_productor = [12]}
}
```

这组 event 的语义可以读成：

| event | producer | consumer |
| --- | --- | --- |
| `[8]` | A 的 `global -> tsm` | A 的 `tsm -> tlm` |
| `[9]` | B 的 `global -> tsm` | B 的 `tsm -> tlm` |
| `[10]` | A 的 `tsm -> tlm` | `kernel.matmul` |
| `[11]` | B 的 `tsm -> tlm` | `kernel.matmul` |
| `[12]` | K loop body 内的 `kernel.matmul` 累加结果 | loop 后 output/bias consumer |

注意：这些编号只对当前这份 IR 的当前分析结果有意义。它们不是长期稳定 token，也不是可以跨 rewrite 原样复制的语义 ID。

## `24 multi-buffer -> 25 producer-consumer-analysis` 的实际结果

本节记录当前仓库里 `24-multi-buffer.mlir` 之后立刻跑 `producer-consumer-analysis` 得到的实际分析结果。它是 ping-pong 之前的结果，循环体仍然是：

```text
for k:
  global -> tsm
  tsm -> tlm
  matmul
  advance rings
```

所以当前 `25-producer-consumer-analysis.mlir` 中，A/B 输入链的核心边仍然都是“同一轮 loop body 内”的边：

```text
A_G2S[k] -> A_S2L[k] -> M[k]
B_G2S[k] -> B_S2L[k] -> M[k]
```

还没有变成 ping-pong 后的：

```text
A_S2L[k + 1] -> M[k + 1]
B_S2L[k + 1] -> M[k + 1]
```

### 当前 event id 总表

下面的 id 来自当前 `25-producer-consumer-analysis.mlir`，只用于说明现状，不应跨 rewrite 继承。

| id | 当前 producer | 当前 consumer | 说明 |
| --- | --- | --- | --- |
| `[0]` | `%12 = dma.alloc`，acc base | `kernel.matmul` 的 `loop_body_consumer` | acc loop body 基础生命周期摘要 |
| `[1]` | `%12 = dma.alloc`，acc base | `kernel.binary_elewise` 的 `loop_body_consumer` | bias add 读写 acc 的 loop body 摘要 |
| `[2]` | `%12 = dma.alloc`，acc base | output `dma.deslice` 的 `loop_body_consumer` | out store 读取 acc 的 loop body 摘要 |
| `[3]` | `%14 = dma.alloc`，bias vector base | `dma.broadcast` 的 `loop_body_consumer` | bias vector base 摘要 |
| `[4]` | `%15 = dma.alloc`，bias tile base | `kernel.binary_elewise` 的 `loop_body_consumer` | bias tile base 摘要 |
| `[5]` | `dma.fill(%acc, 0)` | `kernel.matmul` 的 `loop_body_consumer` | K loop 内 matmul 消费初始 acc |
| `[6]` | `dma.fill(%acc, 0)` | `kernel.binary_elewise` 的 `if_branch_consumer` | bias 分支内 acc 初值/旧值摘要 |
| `[7]` | `dma.fill(%acc, 0)` | output `dma.deslice` 的普通 `consumer` | 无 K/bias 或保守路径下 out 消费 fill 后 acc |
| `[8]` | A 的 `global -> tsm`，`dma.deslice(%tsm_a, %lhs_view)` | A 的 `tsm -> tlm`，`dma.copy(%tlm_a, %tsm_a)` | A 的 TSM 同轮边 |
| `[9]` | B 的 `global -> tsm`，`dma.deslice(%tsm_b, %rhs_view)` | B 的 `tsm -> tlm`，`dma.copy(%tlm_b, %tsm_b)` | B 的 TSM 同轮边 |
| `[10]` | A 的 `tsm -> tlm`，`dma.copy(%tlm_a, %tsm_a)` | `kernel.matmul` | A 的 TLM 同轮边 |
| `[11]` | B 的 `tsm -> tlm`，`dma.copy(%tlm_b, %tsm_b)` | `kernel.matmul` | B 的 TLM 同轮边 |
| `[12]` | `kernel.matmul` | output `dma.deslice` 的 `after_loop_consumer` | K loop 完成后的 acc 结果 |
| `[13]` | bias global -> bias vector，`dma.deslice(%bias_vec, %bias_global)` | `dma.broadcast` | bias load 到 broadcast |
| `[14]` | `dma.broadcast(%bias_tile, %bias_vec)` | `kernel.binary_elewise` | broadcast bias tile 到 bias add |
| `[15]` | `kernel.binary_elewise(%acc, %acc, %bias_tile)` | output `dma.deslice` 的 `after_if_consumer` | bias add 后的 acc |

### A 输入链：`lhs -> tsm_a_ring -> tlm_a_ring -> matmul`

当前 IR 片段的逻辑形态是：

```mlir
%tsm_a_slot = "dma.current_ring"(%tsm_a_ring)
%tsm_a = "dma.reinterpret"(%tsm_a_slot, ...)
%lhs_view = "dma.reinterpret"(%lhs, ...)
"dma.deslice"(%tsm_a, %lhs_view, ...)
  {productor = [8]}

%tlm_a_slot = "dma.current_ring"(%tlm_a_ring)
%tlm_a = "dma.reinterpret"(%tlm_a_slot, ...)
"dma.copy"(%tlm_a, %tsm_a)
  {consumer = [8], productor = [10]}

"kernel.matmul"(%acc, %tlm_a, %tlm_b, %acc_flag)
  {consumer = [10, 11], ...}
```

因此当前分析结果是：

| buffer/view | producer | consumer | event |
| --- | --- | --- | --- |
| `lhs[k]` global view | 函数入参，函数内无 producer | `dma.deslice(%tsm_a, %lhs_view)` | 不生成函数内 producer id |
| `tsm_a` current slot | `dma.deslice(%tsm_a, %lhs_view)` | `dma.copy(%tlm_a, %tsm_a)` | `[8]` |
| `tlm_a` current slot | `dma.copy(%tlm_a, %tsm_a)` | `kernel.matmul(%acc, %tlm_a, %tlm_b, ...)` | `[10]` |

注意：当前 `[10]` 是同一轮内的 `copy(k) -> matmul(k)`。因为 `24-multi-buffer.mlir` 还没有做 ping-pong，`dma.copy` 后面紧跟同轮 `kernel.matmul`，所以分析不需要跨迭代推导。

### B 输入链：`rhs -> tsm_b_ring -> tlm_b_ring -> matmul`

B 链与 A 链对称：

```mlir
%tsm_b_slot = "dma.current_ring"(%tsm_b_ring)
%tsm_b = "dma.reinterpret"(%tsm_b_slot, ...)
%rhs_view = "dma.reinterpret"(%rhs, ...)
"dma.deslice"(%tsm_b, %rhs_view, ...)
  {productor = [9]}

%tlm_b_slot = "dma.current_ring"(%tlm_b_ring)
%tlm_b = "dma.reinterpret"(%tlm_b_slot, ...)
"dma.copy"(%tlm_b, %tsm_b)
  {consumer = [9], productor = [11]}

"kernel.matmul"(%acc, %tlm_a, %tlm_b, %acc_flag)
  {consumer = [10, 11], ...}
```

当前分析结果是：

| buffer/view | producer | consumer | event |
| --- | --- | --- | --- |
| `rhs[k]` global view | 函数入参，函数内无 producer | `dma.deslice(%tsm_b, %rhs_view)` | 不生成函数内 producer id |
| `tsm_b` current slot | `dma.deslice(%tsm_b, %rhs_view)` | `dma.copy(%tlm_b, %tsm_b)` | `[9]` |
| `tlm_b` current slot | `dma.copy(%tlm_b, %tsm_b)` | `kernel.matmul(%acc, %tlm_a, %tlm_b, ...)` | `[11]` |

### TSM ring 在当前结果中的含义

当前 TSM A/B ring 的 `advance_ring` 出现在 `copy` 之后：

```text
current(tsm_a) -> deslice writes -> copy reads -> advance(tsm_a)
current(tsm_b) -> deslice writes -> copy reads -> advance(tsm_b)
```

所以 TSM 的分析边是局部的：

```text
WRITE(tsm_a current slot) by A_G2S[k]
READ(tsm_a same slot)     by A_S2L[k]

WRITE(tsm_b current slot) by B_G2S[k]
READ(tsm_b same slot)     by B_S2L[k]
```

对应 event：

```text
A_G2S[k] -> A_S2L[k] = [8]
B_G2S[k] -> B_S2L[k] = [9]
```

### TLM ring 在当前结果中的含义

当前 TLM A/B ring 的 `advance_ring` 出现在 `matmul` 之后：

```text
current(tlm_a) -> copy writes -> matmul reads -> advance(tlm_a)
current(tlm_b) -> copy writes -> matmul reads -> advance(tlm_b)
```

所以当前 TLM 的分析边仍是同轮：

```text
WRITE(tlm_a current slot) by A_S2L[k]
READ(tlm_a same slot)     by M[k]

WRITE(tlm_b current slot) by B_S2L[k]
READ(tlm_b same slot)     by M[k]
```

对应 event：

```text
A_S2L[k] -> M[k] = [10]
B_S2L[k] -> M[k] = [11]
```

这就是 multi-buffer 后、ping-pong 前的关键事实：ring 已经存在，但 producer/consumer 还是同一轮内的局部链。只有做 ping-pong 后，TLM 的 `copy -> matmul` 才会变成跨阶段/跨迭代：

```text
prologue A_S2L[0] -> M[0]
body A_S2L[k + 1] -> next M[k + 1]
```

### `acc` 在当前结果中的含义

当前 `acc` 是 `%103`，来自 `%12` 的 reinterpret。`25-producer-consumer-analysis.mlir` 对它的标注是摘要式的：

```mlir
%12 = "dma.alloc"(...)
  {loop_body_productor = [0, 1, 2]}

"dma.fill"(%103, %zero)
  {loop_body_productor = [5], if_branch_productor = [6], productor = [7]}

"kernel.matmul"(%103, %120, %123, %acc_flag)
  {loop_body_consumer = [0, 5], consumer = [10, 11], after_loop_productor = [12]}

"kernel.binary_elewise"(%103, %103, %106)
  {loop_body_consumer = [1, 4], if_branch_consumer = [6], consumer = [14], after_if_productor = [15]}

"dma.deslice"(%out, %103, ...)
  {loop_body_consumer = [2], consumer = [7], after_loop_consumer = [12], after_if_consumer = [15]}
```

按语义读，它表达的是：

| producer | consumer | event |
| --- | --- | --- |
| `dma.fill(%acc, 0)` | K loop 内 `kernel.matmul` | `[5]`，并带 `loop_body_consumer` |
| `kernel.matmul` 的 K loop 累加结果 | K loop 后 output store | `[12]`，`after_loop_productor/consumer` |
| `dma.fill(%acc, 0)` | bias if 分支内 bias add 的 acc 输入摘要 | `[6]`，`if_branch_*` |
| `kernel.binary_elewise` bias add 后结果 | output store | `[15]`，`after_if_*` |
| `dma.fill(%acc, 0)` | output store 的保守普通 consumer | `[7]` |

当前分析没有把每一轮 `M[k] -> M[k + 1]` 展开成单独 event；它用 `loop_body_consumer` / `after_loop_productor` 摘要 K loop 内和 loop 后的 acc 生命周期。

### bias / out 在当前结果中的含义

如果 bias 指针存在，当前分析结果是：

```mlir
"dma.deslice"(%bias_vec, %bias_global, ...)
  {productor = [13]}

"dma.broadcast"(%bias_tile, %bias_vec)
  {loop_body_consumer = [3], consumer = [13], productor = [14]}

"kernel.binary_elewise"(%acc, %acc, %bias_tile)
  {loop_body_consumer = [1, 4], if_branch_consumer = [6], consumer = [14], after_if_productor = [15]}

"dma.deslice"(%out, %acc, ...)
  {loop_body_consumer = [2], consumer = [7], after_loop_consumer = [12], after_if_consumer = [15]}
```

对应关系：

| buffer/view | producer | consumer | event |
| --- | --- | --- | --- |
| `bias_vec` | bias global `dma.deslice` | `dma.broadcast` | `[13]` |
| `bias_tile` | `dma.broadcast` | `kernel.binary_elewise` | `[14]` |
| `acc` K loop result | `kernel.matmul` | output `dma.deslice` | `[12]` |
| `acc` bias add result | `kernel.binary_elewise` | output `dma.deslice` | `[15]` |

### 当前结果与 ping-pong 后结果的差异

对比 multi-buffer 后当前结果和 ping-pong 后目标结果：

| buffer | `24 -> 25` 当前结果 | ping-pong 后目标结果 |
| --- | --- | --- |
| `tsm_a_ring` | `A_G2S[k] -> A_S2L[k]`，同轮 | 仍是 `A_G2S[t] -> A_S2L[t]`，通常仍在 preload 阶段内 |
| `tsm_b_ring` | `B_G2S[k] -> B_S2L[k]`，同轮 | 仍是 `B_G2S[t] -> B_S2L[t]`，通常仍在 preload 阶段内 |
| `tlm_a_ring` | `A_S2L[k] -> M[k]`，同轮 `[10]` | `A_S2L[0] -> M[0]`，`A_S2L[t+1] -> M[t+1]`，跨 prologue/body/epilogue |
| `tlm_b_ring` | `B_S2L[k] -> M[k]`，同轮 `[11]` | `B_S2L[0] -> M[0]`，`B_S2L[t+1] -> M[t+1]`，跨 prologue/body/epilogue |
| `acc` | loop 摘要：fill/matmul/bias/out | 基本不变，仍是 K loop 累加和后处理链 |
| `bias/out` | bias load/broadcast/add/out store | 基本不变，位置仍在 K loop 后 |

所以，`multi-buffer` 后的分析结果能直接证明原始同轮链：

```text
global -> tsm -> tlm -> matmul
```

但它不能原样作为 ping-pong 后的 attr 结果，因为 ping-pong 会把 TLM 的 `copy -> matmul` 从“同一轮”改成“prologue/上一轮 preload -> 当前轮 compute”。

### 完整分析后 IR 草稿：multi-buffer 后、ping-pong 前

下面是刚才这个 `multi-buffer -> producer-consumer-analysis` 例子的完整分析后 IR 草稿。它保留所有 memory-affecting op 和 producer/consumer attr；纯 symbol shape 计算用 `...` 省略，因为它们不参与生产消费关系。

```mlir
// function arguments:
//   %out  : global output
//   %lhs  : global A input
//   %rhs  : global B input
//   %bias : optional global bias

%zero = arith.constant 0.000000e+00 : f32

// Non-ring buffers used after K loop.
%acc_base = "dma.alloc"(...)
  {loop_body_productor = [0, 1, 2]}
  : (...) -> !nn.memory<[#S_TILE_H, #S_TILE_W], [#S_TILE_W, #C1], f32, #nn.space<tsm>>

%bias_vec_base = "dma.alloc"(...)
  {loop_body_productor = [3]}
  : (...) -> !nn.memory<[#S_TILE_W], [#C1], f32, #nn.space<tsm>>

%bias_tile_base = "dma.alloc"(...)
  {loop_body_productor = [4]}
  : (...) -> !nn.memory<[#S_TILE_H, #S_TILE_W], [#S_TILE_W, #C1], f32, #nn.space<tsm>>

// Rings created by multi-buffer. producer-consumer-analysis does not attach
// payload producer/consumer events to make_ring/current_ring/advance_ring here;
// the events attach to the ops that actually read/write the slot views.
%tsm_a_storage = "dma.alloc"(...)
  : (...) -> !nn.memory<[...], [#C1], i8, #nn.space<tsm>>
%tsm_a_ring = "dma.make_ring"(%tsm_a_storage, %tsm_a_slots, %tsm_a_slot_bytes)
  : (...) -> !dma.ring<!nn.memory<[#S_TILE_H, #S_TILE_K], [#S_TILE_K, #C1], f32, #nn.space<tsm>>>

%tsm_b_storage = "dma.alloc"(...)
  : (...) -> !nn.memory<[...], [#C1], i8, #nn.space<tsm>>
%tsm_b_ring = "dma.make_ring"(%tsm_b_storage, %tsm_b_slots, %tsm_b_slot_bytes)
  : (...) -> !dma.ring<!nn.memory<[#S_TILE_K, #S_TILE_W], [#S_TILE_W, #C1], f32, #nn.space<tsm>>>

%tlm_a_storage = "dma.alloc"(...)
  : (...) -> !nn.memory<[...], [#C1], i8, #nn.space<tlm1>>
%tlm_a_ring = "dma.make_ring"(%tlm_a_storage, %tlm_a_slots, %tlm_a_slot_bytes)
  : (...) -> !dma.ring<!nn.memory<[#S_TILE_H, #S_TILE_K], [#S_TILE_K, #C1], f32, #nn.space<tlm1>>>

%tlm_b_storage = "dma.alloc"(...)
  : (...) -> !nn.memory<[...], [#C1], i8, #nn.space<tlm2>>
%tlm_b_ring = "dma.make_ring"(%tlm_b_storage, %tlm_b_slots, %tlm_b_slot_bytes)
  : (...) -> !dma.ring<!nn.memory<[#S_TILE_K, #S_TILE_W], [#S_TILE_W, #C1], f32, #nn.space<tlm2>>>

symbol.for %i = %c0 to %H step %TILE_H {
  symbol.for %j = %c0 to %W step %TILE_W {
    %acc = "dma.reinterpret"(%acc_base, ...)
      : (...) -> !nn.memory<[#S_H_EFF, #S_W_EFF], [#S_W_EFF, #C1], f32, #nn.space<tsm>>

    // acc initialization. The current analysis emits several summary events
    // because %acc can be consumed by the K loop, by the bias if, and by output.
    "dma.fill"(%acc, %zero)
      {loop_body_productor = [5], if_branch_productor = [6], productor = [7]}
      : (!nn.memory<[#S_H_EFF, #S_W_EFF], [#S_W_EFF, #C1], f32, #nn.space<tsm>>, f32) -> ()

    %bias_vec = "dma.reinterpret"(%bias_vec_base, ...)
      : (...) -> !nn.memory<[#S_W_EFF], [#C1], f32, #nn.space<tsm>>

    %bias_vec_2d = "dma.reinterpret"(%bias_vec_base, ...)
      : (...) -> !nn.memory<[#C1, #S_W_EFF], [#S_W_EFF, #C1], f32, #nn.space<tsm>>

    %bias_tile = "dma.reinterpret"(%bias_tile_base, ...)
      : (...) -> !nn.memory<[#S_H_EFF, #S_W_EFF], [#S_W_EFF, #C1], f32, #nn.space<tsm>>

    symbol.for %k = %c0 to %K step %TILE_K {
      // A: global -> TSM current slot.
      %tsm_a_slot = "dma.current_ring"(%tsm_a_ring)
        : (...) -> !nn.memory<[#S_TILE_H, #S_TILE_K], [#S_TILE_K, #C1], f32, #nn.space<tsm>>
      %tsm_a = "dma.reinterpret"(%tsm_a_slot, ...)
        : (...) -> !nn.memory<[#S_H_EFF, #S_K_EFF], [#S_K_EFF, #C1], f32, #nn.space<tsm>>
      %lhs_view = "dma.reinterpret"(%lhs, ...)
        : (...) -> !nn.memory<[#S_H_EFF, #S_K_EFF], [#S_K, #C1], f32, #nn.space<global>>
      "dma.deslice"(%tsm_a, %lhs_view, ...)
        {productor = [8]}
        : (...) -> ()

      // B: global -> TSM current slot.
      %tsm_b_slot = "dma.current_ring"(%tsm_b_ring)
        : (...) -> !nn.memory<[#S_TILE_K, #S_TILE_W], [#S_TILE_W, #C1], f32, #nn.space<tsm>>
      %tsm_b = "dma.reinterpret"(%tsm_b_slot, ...)
        : (...) -> !nn.memory<[#S_K_EFF, #S_W_EFF], [#S_W_EFF, #C1], f32, #nn.space<tsm>>
      %rhs_view = "dma.reinterpret"(%rhs, ...)
        : (...) -> !nn.memory<[#S_K_EFF, #S_W_EFF], [#S_W, #C1], f32, #nn.space<global>>
      "dma.deslice"(%tsm_b, %rhs_view, ...)
        {productor = [9]}
        : (...) -> ()

      // A: TSM current slot -> TLM current slot.
      %tlm_a_slot = "dma.current_ring"(%tlm_a_ring)
        : (...) -> !nn.memory<[#S_TILE_H, #S_TILE_K], [#S_TILE_K, #C1], f32, #nn.space<tlm1>>
      %tlm_a = "dma.reinterpret"(%tlm_a_slot, ...)
        : (...) -> !nn.memory<[#S_H_EFF, #S_K_EFF], [#S_K_EFF, #C1], f32, #nn.space<tlm1>>
      "dma.copy"(%tlm_a, %tsm_a)
        {consumer = [8], productor = [10]}
        : (!nn.memory<[#S_H_EFF, #S_K_EFF], [#S_K_EFF, #C1], f32, #nn.space<tlm1>>,
           !nn.memory<[#S_H_EFF, #S_K_EFF], [#S_K_EFF, #C1], f32, #nn.space<tsm>>) -> ()

      // The A TSM slot is no longer needed after A_S2L[k].
      "dma.advance_ring"(%tsm_a_ring)
        : (...) -> !nn.memory<[#S_TILE_H, #S_TILE_K], [#S_TILE_K, #C1], f32, #nn.space<tsm>>

      // B: TSM current slot -> TLM current slot.
      %tlm_b_slot = "dma.current_ring"(%tlm_b_ring)
        : (...) -> !nn.memory<[#S_TILE_K, #S_TILE_W], [#S_TILE_W, #C1], f32, #nn.space<tlm2>>
      %tlm_b = "dma.reinterpret"(%tlm_b_slot, ...)
        : (...) -> !nn.memory<[#S_K_EFF, #S_W_EFF], [#S_W_EFF, #C1], f32, #nn.space<tlm2>>
      "dma.copy"(%tlm_b, %tsm_b)
        {consumer = [9], productor = [11]}
        : (!nn.memory<[#S_K_EFF, #S_W_EFF], [#S_W_EFF, #C1], f32, #nn.space<tlm2>>,
           !nn.memory<[#S_K_EFF, #S_W_EFF], [#S_W_EFF, #C1], f32, #nn.space<tsm>>) -> ()

      // The B TSM slot is no longer needed after B_S2L[k].
      "dma.advance_ring"(%tsm_b_ring)
        : (...) -> !nn.memory<[#S_TILE_K, #S_TILE_W], [#S_TILE_W, #C1], f32, #nn.space<tsm>>

      %acc_flag = symbol.ne %k, %c0 : (...) -> i1

      // Compute consumes the same-iteration TLM writes [10] and [11].
      "kernel.matmul"(%acc, %tlm_a, %tlm_b, %acc_flag)
        {space = #nn.space<tsm>, loop_body_consumer = [0, 5], consumer = [10, 11], after_loop_productor = [12]}
        : (!nn.memory<[#S_H_EFF, #S_W_EFF], [#S_W_EFF, #C1], f32, #nn.space<tsm>>,
           !nn.memory<[#S_H_EFF, #S_K_EFF], [#S_K_EFF, #C1], f32, #nn.space<tlm1>>,
           !nn.memory<[#S_K_EFF, #S_W_EFF], [#S_W_EFF, #C1], f32, #nn.space<tlm2>>,
           i1) -> ()

      // TLM slots are advanced after matmul because current IR is not ping-pong:
      // copy(k) writes current, matmul(k) reads current, then current can advance.
      "dma.advance_ring"(%tlm_b_ring)
        : (...) -> !nn.memory<[#S_TILE_K, #S_TILE_W], [#S_TILE_W, #C1], f32, #nn.space<tlm2>>
      "dma.advance_ring"(%tlm_a_ring)
        : (...) -> !nn.memory<[#S_TILE_H, #S_TILE_K], [#S_TILE_K, #C1], f32, #nn.space<tlm1>>
    }

    scf.if %has_bias {
      %bias_global = "dma.reinterpret"(%bias, ...)
        : (...) -> !nn.memory<[#S_W_EFF], [#C1], f32, #nn.space<global>>

      "dma.deslice"(%bias_vec, %bias_global, ...)
        {productor = [13]}
        : (...) -> ()

      "dma.broadcast"(%bias_tile, %bias_vec_2d)
        {tile.analysis = [["elewise", "elewise"], ["expand", "elewise"]],
         tile.tile_exprs = [["", ""], ["", ""]],
         loop_body_consumer = [3], consumer = [13], productor = [14]}
        : (!nn.memory<[#S_H_EFF, #S_W_EFF], [#S_W_EFF, #C1], f32, #nn.space<tsm>>,
           !nn.memory<[#C1, #S_W_EFF], [#S_W_EFF, #C1], f32, #nn.space<tsm>>) -> ()

      "kernel.binary_elewise"(%acc, %acc, %bias_tile)
        {kind = "add", space = #nn.space<tsm>,
         tile.analysis = [["elewise", "elewise"], ["elewise", "elewise"], ["elewise", "elewise"]],
         tile.tile_exprs = [["", ""], ["", ""], ["", ""]],
         loop_body_consumer = [1, 4], if_branch_consumer = [6], consumer = [14], after_if_productor = [15]}
        : (!nn.memory<[#S_H_EFF, #S_W_EFF], [#S_W_EFF, #C1], f32, #nn.space<tsm>>,
           !nn.memory<[#S_H_EFF, #S_W_EFF], [#S_W_EFF, #C1], f32, #nn.space<tsm>>,
           !nn.memory<[#S_H_EFF, #S_W_EFF], [#S_W_EFF, #C1], f32, #nn.space<tsm>>) -> ()
    }

    "dma.deslice"(%out, %acc, ...)
      {loop_body_consumer = [2], consumer = [7], after_loop_consumer = [12], after_if_consumer = [15]}
      : (!nn.memory<[#S_H, #S_W], [#S_W, #C1], f32, #nn.space<global>>,
         !nn.memory<[#S_H_EFF, #S_W_EFF], [#S_W_EFF, #C1], f32, #nn.space<tsm>>) -> ()
  }
}
```

把这段 IR 的核心边抽出来，就是：

```text
[8]  A global -> TSM      producer: dma.deslice(%tsm_a, %lhs_view)
     A TSM -> TLM         consumer: dma.copy(%tlm_a, %tsm_a)

[9]  B global -> TSM      producer: dma.deslice(%tsm_b, %rhs_view)
     B TSM -> TLM         consumer: dma.copy(%tlm_b, %tsm_b)

[10] A TSM -> TLM         producer: dma.copy(%tlm_a, %tsm_a)
     matmul               consumer: kernel.matmul(..., %tlm_a, ...)

[11] B TSM -> TLM         producer: dma.copy(%tlm_b, %tsm_b)
     matmul               consumer: kernel.matmul(..., %tlm_b, ...)

[12] K loop matmul result producer: kernel.matmul
     output store         consumer: dma.deslice(%out, %acc, ...)

[13] bias load            producer: dma.deslice(%bias_vec, %bias_global)
     broadcast            consumer: dma.broadcast(%bias_tile, %bias_vec_2d)

[14] broadcast            producer: dma.broadcast(%bias_tile, %bias_vec_2d)
     bias add             consumer: kernel.binary_elewise(%acc, %acc, %bias_tile)

[15] bias add             producer: kernel.binary_elewise(%acc, %acc, %bias_tile)
     output store         consumer: dma.deslice(%out, %acc, ...)
```

## Ping-pong 后的目标 IR 形态

ping-pong 后，K 维调度会从“本轮搬、本轮算”变成“先预取、循环中算当前并预取下一轮、最后收尾算”。概念形态如下：

```text
prologue:
  preload k0 into slot0

steady loop:
  compute current slot
  preload k+1 into next slot

epilogue:
  compute last slot
```

展开成接近 IR 的伪结构：

```mlir
// prologue: load tile k0
%tsm_a0 = "dma.current_ring"(%tsm_a_ring)
%tsm_b0 = "dma.current_ring"(%tsm_b_ring)
"dma.deslice"(%tsm_a0_view, %global_a_k0, ...)
"dma.deslice"(%tsm_b0_view, %global_b_k0, ...)

%tlm_a0 = "dma.current_ring"(%tlm_a_ring)
%tlm_b0 = "dma.current_ring"(%tlm_b_ring)
"dma.copy"(%tlm_a0_view, %tsm_a0_view)
"dma.copy"(%tlm_b0_view, %tsm_b0_view)
"dma.advance_ring"(%tsm_a_ring)
"dma.advance_ring"(%tsm_b_ring)
// 注意：这里不推进 tlm ring。tlm 当前 slot 已经装入 k0，steady loop 第一轮要先消费它。

symbol.for %k = %c0 to %steady_end step %TILE_K {
  // compute current tile loaded by previous prologue/body
  %tlm_a_current = "dma.current_ring"(%tlm_a_ring)
  %tlm_b_current = "dma.current_ring"(%tlm_b_ring)
  "kernel.matmul"(%acc, %tlm_a_current_view, %tlm_b_current_view, %acc_flag)

  // 当前 compute slot 的最后一次使用在 matmul，之后才能推进到 next writable slot。
  "dma.advance_ring"(%tlm_a_ring)
  "dma.advance_ring"(%tlm_b_ring)

  // preload next tile into the other ring slot
  %k_next = symbol.add %k, %TILE_K
  %tsm_a_next = "dma.current_ring"(%tsm_a_ring)
  %tsm_b_next = "dma.current_ring"(%tsm_b_ring)
  "dma.deslice"(%tsm_a_next_view, %global_a_next, ...)
  "dma.deslice"(%tsm_b_next_view, %global_b_next, ...)

  %tlm_a_next = "dma.current_ring"(%tlm_a_ring)
  %tlm_b_next = "dma.current_ring"(%tlm_b_ring)
  "dma.copy"(%tlm_a_next_view, %tsm_a_next_view)
  "dma.copy"(%tlm_b_next_view, %tsm_b_next_view)
  "dma.advance_ring"(%tsm_a_ring)
  "dma.advance_ring"(%tsm_b_ring)
  // 注意：这里也不推进 tlm ring。下一轮开头的 current_ring 要读到刚 copy 的 next tile。
}

// epilogue: compute final preloaded tile
%tlm_a_last = "dma.current_ring"(%tlm_a_ring)
%tlm_b_last = "dma.current_ring"(%tlm_b_ring)
"kernel.matmul"(%acc, %tlm_a_last_view, %tlm_b_last_view, %acc_flag_last)
"dma.advance_ring"(%tlm_a_ring)
"dma.advance_ring"(%tlm_b_ring)
```

真实实现可以选择不同的首尾分离方式，但核心关系是：

```text
prologue preload(k0)        -> first compute(k0)
body preload(k + TILE_K)    -> next compute(k + TILE_K)
last preload                -> epilogue compute(last)
```

## 备选草稿：先分离，再分析

如果选择先做首尾分离，再运行 `producer-consumer-analysis`，分析 pass 看到的就不再是原始单 loop 内的 `global -> tsm -> tlm -> matmul` 顺序链，而是已经被拆成 prologue / steady / epilogue 的控制流。

概念 IR 如下。该片段用于说明依赖关系，不是当前仓库可直接 parse 的完整 IR；真正落地时还要解决 `%tlm_a_cur` / `%tlm_b_cur` 这类“上一阶段已预取 tile view”如何在 steady loop 中表达的问题。

```mlir
// prologue: preload k0
%k0 = symbol.const 0 : !symbol.int<#C0>
%k1 = symbol.add %k0, %tile_k : !symbol.int<#C0>, !symbol.int<#S_TILE_K> -> !symbol.int<#S_K1>

%tsm_a0_slot = "dma.current_ring"(%tsm_a_ring)
%tsm_a0 = "dma.reinterpret"(%tsm_a0_slot, %c0, %tile_h_eff, %tile_k0_eff, ...)
%global_a0 = "dma.reinterpret"(%lhs, %lhs_offset_k0, %tile_h_eff, %tile_k0_eff, ...)
"dma.deslice"(%tsm_a0, %global_a0, ...)

%tsm_b0_slot = "dma.current_ring"(%tsm_b_ring)
%tsm_b0 = "dma.reinterpret"(%tsm_b0_slot, %c0, %tile_k0_eff, %tile_w_eff, ...)
%global_b0 = "dma.reinterpret"(%rhs, %rhs_offset_k0, %tile_k0_eff, %tile_w_eff, ...)
"dma.deslice"(%tsm_b0, %global_b0, ...)

%tlm_a0_slot = "dma.current_ring"(%tlm_a_ring)
%tlm_a0 = "dma.reinterpret"(%tlm_a0_slot, %c0, %tile_h_eff, %tile_k0_eff, ...)
"dma.copy"(%tlm_a0, %tsm_a0)

%tlm_b0_slot = "dma.current_ring"(%tlm_b_ring)
%tlm_b0 = "dma.reinterpret"(%tlm_b0_slot, %c0, %tile_k0_eff, %tile_w_eff, ...)
"dma.copy"(%tlm_b0, %tsm_b0)

"dma.advance_ring"(%tsm_a_ring)
"dma.advance_ring"(%tsm_b_ring)

// steady loop: compute current, preload next
// TLM ring 在 prologue copy 后没有 advance；第一轮 current_ring 读到 k0。
symbol.for %k = %k0 to %steady_end step %tile_k {
  %acc_flag = symbol.ne %k, %k0
  %tlm_a_cur_slot = "dma.current_ring"(%tlm_a_ring)
  %tlm_a_cur = "dma.reinterpret"(%tlm_a_cur_slot, %c0, %tile_h_eff, %tile_k_eff, ...)
  %tlm_b_cur_slot = "dma.current_ring"(%tlm_b_ring)
  %tlm_b_cur = "dma.reinterpret"(%tlm_b_cur_slot, %c0, %tile_k_eff, %tile_w_eff, ...)
  "kernel.matmul"(%acc, %tlm_a_cur, %tlm_b_cur, %acc_flag)

  // matmul 后才推进 TLM ring，后续 copy next 写入新的 current slot。
  "dma.advance_ring"(%tlm_a_ring)
  "dma.advance_ring"(%tlm_b_ring)

  %k_next = symbol.add %k, %tile_k
  %tile_k_next_eff = symbol.min %tile_k, %K_minus_k_next

  %tsm_a_next_slot = "dma.current_ring"(%tsm_a_ring)
  %tsm_a_next = "dma.reinterpret"(%tsm_a_next_slot, %c0, %tile_h_eff, %tile_k_next_eff, ...)
  %global_a_next = "dma.reinterpret"(%lhs, %lhs_offset_next, %tile_h_eff, %tile_k_next_eff, ...)
  "dma.deslice"(%tsm_a_next, %global_a_next, ...)

  %tsm_b_next_slot = "dma.current_ring"(%tsm_b_ring)
  %tsm_b_next = "dma.reinterpret"(%tsm_b_next_slot, %c0, %tile_k_next_eff, %tile_w_eff, ...)
  %global_b_next = "dma.reinterpret"(%rhs, %rhs_offset_next, %tile_k_next_eff, %tile_w_eff, ...)
  "dma.deslice"(%tsm_b_next, %global_b_next, ...)

  %tlm_a_next_slot = "dma.current_ring"(%tlm_a_ring)
  %tlm_a_next = "dma.reinterpret"(%tlm_a_next_slot, %c0, %tile_h_eff, %tile_k_next_eff, ...)
  "dma.copy"(%tlm_a_next, %tsm_a_next)

  %tlm_b_next_slot = "dma.current_ring"(%tlm_b_ring)
  %tlm_b_next = "dma.reinterpret"(%tlm_b_next_slot, %c0, %tile_k_next_eff, %tile_w_eff, ...)
  "dma.copy"(%tlm_b_next, %tsm_b_next)

  "dma.advance_ring"(%tsm_a_ring)
  "dma.advance_ring"(%tsm_b_ring)

  // 注意：这里不推进 TLM ring。下一轮 loop 开头的 current_ring 应读到本轮刚 copy 的 next tile。
}

// epilogue: compute last preloaded tile
%tlm_a_last_slot = "dma.current_ring"(%tlm_a_ring)
%tlm_a_last = "dma.reinterpret"(%tlm_a_last_slot, ...)
%tlm_b_last_slot = "dma.current_ring"(%tlm_b_ring)
%tlm_b_last = "dma.reinterpret"(%tlm_b_last_slot, ...)
"kernel.matmul"(%acc, %tlm_a_last, %tlm_b_last, %acc_flag_last)
"dma.advance_ring"(%tlm_a_ring)
"dma.advance_ring"(%tlm_b_ring)
```

### 完整分析后 IR 草稿：分离后、ring-aware 分析

下面是上面这段 ping-pong IR 在“ring-aware producer-consumer-analysis”之后的完整标注草稿。这里引入了几个概念 attr：

- `loop_first_productor` / `loop_first_consumer`：prologue 生产，steady loop 第一轮消费。
- `loop_carried_productor` / `loop_carried_consumer`：steady loop 第 `t` 轮生产，steady loop 第 `t + 1` 轮消费。
- `after_loop_productor` / `after_loop_consumer`：steady loop 最后一轮生产，epilogue 消费。

这些 attr 名字是为了把关系讲完整；如果当前实现不新增这类分类，仅靠现有 `loop_body_*` / `after_loop_*` 不能无损表达这段 IR 的所有消费边。

```mlir
// prologue: preload k0
%k0 = symbol.const 0 : !symbol.int<#C0>
%k1 = symbol.add %k0, %tile_k : !symbol.int<#C0>, !symbol.int<#S_TILE_K> -> !symbol.int<#S_K1>

// A k0: global -> TSM current slot.
%tsm_a0_slot = "dma.current_ring"(%tsm_a_ring)
%tsm_a0 = "dma.reinterpret"(%tsm_a0_slot, %c0, %tile_h_eff, %tile_k0_eff, ...)
%global_a0 = "dma.reinterpret"(%lhs, %lhs_offset_k0, %tile_h_eff, %tile_k0_eff, ...)
"dma.deslice"(%tsm_a0, %global_a0, ...)
  {productor = [100]}

// B k0: global -> TSM current slot.
%tsm_b0_slot = "dma.current_ring"(%tsm_b_ring)
%tsm_b0 = "dma.reinterpret"(%tsm_b0_slot, %c0, %tile_k0_eff, %tile_w_eff, ...)
%global_b0 = "dma.reinterpret"(%rhs, %rhs_offset_k0, %tile_k0_eff, %tile_w_eff, ...)
"dma.deslice"(%tsm_b0, %global_b0, ...)
  {productor = [101]}

// A k0: TSM current slot -> TLM current slot.
// TLM ring 在 copy 后不 advance，所以 steady 第一轮 current(tlm_a) 仍是这个 slot。
%tlm_a0_slot = "dma.current_ring"(%tlm_a_ring)
%tlm_a0 = "dma.reinterpret"(%tlm_a0_slot, %c0, %tile_h_eff, %tile_k0_eff, ...)
"dma.copy"(%tlm_a0, %tsm_a0)
  {consumer = [100], loop_first_productor = [102]}

// B k0: TSM current slot -> TLM current slot.
%tlm_b0_slot = "dma.current_ring"(%tlm_b_ring)
%tlm_b0 = "dma.reinterpret"(%tlm_b0_slot, %c0, %tile_k0_eff, %tile_w_eff, ...)
"dma.copy"(%tlm_b0, %tsm_b0)
  {consumer = [101], loop_first_productor = [103]}

// TSM 的 k0 staging 已经被 copy 消费，可以 advance。
// 这里不 advance TLM。
"dma.advance_ring"(%tsm_a_ring)
"dma.advance_ring"(%tsm_b_ring)

// steady loop: compute current tile, then preload next tile.
symbol.for %k = %k0 to %steady_end step %tile_k {
  %acc_flag = symbol.ne %k, %k0

  // Loop entry current(tlm_*) 指向“已经生产好、等待 matmul 读取”的 tile。
  // 第一轮消费 prologue 的 [102]/[103]；
  // 后续轮次消费上一轮 body copy 生产的 [106]/[107]。
  %tlm_a_cur_slot = "dma.current_ring"(%tlm_a_ring)
  %tlm_a_cur = "dma.reinterpret"(%tlm_a_cur_slot, %c0, %tile_h_eff, %tile_k_eff, ...)
  %tlm_b_cur_slot = "dma.current_ring"(%tlm_b_ring)
  %tlm_b_cur = "dma.reinterpret"(%tlm_b_cur_slot, %c0, %tile_k_eff, %tile_w_eff, ...)
  "kernel.matmul"(%acc, %tlm_a_cur, %tlm_b_cur, %acc_flag)
    {loop_first_consumer = [102, 103],
     loop_carried_consumer = [106, 107],
     after_loop_productor = [200]}

  // matmul 读完当前 TLM slot 后，advance 到 next slot。
  // advance 不产生 producer/consumer，只改变后续 current_ring 的 slot。
  "dma.advance_ring"(%tlm_a_ring)
  "dma.advance_ring"(%tlm_b_ring)

  %k_next = symbol.add %k, %tile_k
  %tile_k_next_eff = symbol.min %tile_k, %K_minus_k_next

  // A next: global -> TSM current slot.
  %tsm_a_next_slot = "dma.current_ring"(%tsm_a_ring)
  %tsm_a_next = "dma.reinterpret"(%tsm_a_next_slot, %c0, %tile_h_eff, %tile_k_next_eff, ...)
  %global_a_next = "dma.reinterpret"(%lhs, %lhs_offset_next, %tile_h_eff, %tile_k_next_eff, ...)
  "dma.deslice"(%tsm_a_next, %global_a_next, ...)
    {productor = [104]}

  // B next: global -> TSM current slot.
  %tsm_b_next_slot = "dma.current_ring"(%tsm_b_ring)
  %tsm_b_next = "dma.reinterpret"(%tsm_b_next_slot, %c0, %tile_k_next_eff, %tile_w_eff, ...)
  %global_b_next = "dma.reinterpret"(%rhs, %rhs_offset_next, %tile_k_next_eff, %tile_w_eff, ...)
  "dma.deslice"(%tsm_b_next, %global_b_next, ...)
    {productor = [105]}

  // A next: TSM current slot -> TLM current slot after TLM advance.
  // 对非最后一轮，它生产下一轮 loop entry matmul 消费的 A tile：[106]。
  // 对最后一轮，它生产 epilogue matmul 消费的 A tile：[108]。
  %tlm_a_next_slot = "dma.current_ring"(%tlm_a_ring)
  %tlm_a_next = "dma.reinterpret"(%tlm_a_next_slot, %c0, %tile_h_eff, %tile_k_next_eff, ...)
  "dma.copy"(%tlm_a_next, %tsm_a_next)
    {consumer = [104], loop_carried_productor = [106], after_loop_productor = [108]}

  // B next: TSM current slot -> TLM current slot after TLM advance.
  %tlm_b_next_slot = "dma.current_ring"(%tlm_b_ring)
  %tlm_b_next = "dma.reinterpret"(%tlm_b_next_slot, %c0, %tile_k_next_eff, %tile_w_eff, ...)
  "dma.copy"(%tlm_b_next, %tsm_b_next)
    {consumer = [105], loop_carried_productor = [107], after_loop_productor = [109]}

  // TSM next staging 已经被 copy 消费，可以 advance。
  "dma.advance_ring"(%tsm_a_ring)
  "dma.advance_ring"(%tsm_b_ring)

  // 这里不 advance TLM。下一轮 loop entry 的 current(tlm_*) 仍是刚写入的 next slot。
}

// epilogue: compute last preloaded tile.
// steady loop 最后一轮 body copy 写入 TLM 后没有 advance；
// 因此这里 current(tlm_*) 仍指向最后一次 copy 写入的 slot。
%tlm_a_last_slot = "dma.current_ring"(%tlm_a_ring)
%tlm_a_last = "dma.reinterpret"(%tlm_a_last_slot, ...)
%tlm_b_last_slot = "dma.current_ring"(%tlm_b_ring)
%tlm_b_last = "dma.reinterpret"(%tlm_b_last_slot, ...)
"kernel.matmul"(%acc, %tlm_a_last, %tlm_b_last, %acc_flag_last)
  {after_loop_consumer = [108, 109], after_loop_productor = [201]}
"dma.advance_ring"(%tlm_a_ring)
"dma.advance_ring"(%tlm_b_ring)
```

这段完整标注 IR 中，各 id 的含义是：

| id | producer | consumer | 控制流关系 |
| --- | --- | --- | --- |
| `[100]` | prologue `A_G2S[0]` | prologue `A_S2L[0]` | prologue 内 |
| `[101]` | prologue `B_G2S[0]` | prologue `B_S2L[0]` | prologue 内 |
| `[102]` | prologue `A_S2L[0]` | steady 第一轮 `M[0]` | prologue -> loop first |
| `[103]` | prologue `B_S2L[0]` | steady 第一轮 `M[0]` | prologue -> loop first |
| `[104]` | body `A_G2S[t + 1]` | body `A_S2L[t + 1]` | 同一 steady iteration |
| `[105]` | body `B_G2S[t + 1]` | body `B_S2L[t + 1]` | 同一 steady iteration |
| `[106]` | body `A_S2L[t + 1]` | 下一轮 body `M[t + 1]` | loop-carried |
| `[107]` | body `B_S2L[t + 1]` | 下一轮 body `M[t + 1]` | loop-carried |
| `[108]` | body 最后一轮 `A_S2L[N - 1]` | epilogue `M[N - 1]` | loop -> epilogue |
| `[109]` | body 最后一轮 `B_S2L[N - 1]` | epilogue `M[N - 1]` | loop -> epilogue |
| `[200]` | steady loop body `kernel.matmul` | loop 后 acc consumer | acc 摘要，不属于 A/B ping-pong slot |
| `[201]` | epilogue `kernel.matmul` | loop 后 acc consumer | acc 摘要，不属于 A/B ping-pong slot |

如果 `N == 1`，steady loop 为空，prologue 的 `A_S2L[0]` / `B_S2L[0]` 会直接被 epilogue `M[0]` 消费。此时 `[102]/[103]` 的分类不再是 `loop_first`，而应退化为 `prologue -> epilogue`；slot 证明仍然是“prologue copy 后没有 TLM advance，epilogue current 读到同一个 TLM slot”。

对比一下，如果在这种分离后 IR 上继续使用当前非 ring-aware 的 `producer-consumer-analysis`，它最多容易得到下面这种不完整结果。这里的 `matmul` 通过 `dma.current_ring(%tlm_*_ring)` 读取当前 TLM slot；body 中 `matmul` 后先 `advance_ring`，再把 next tile copy 到新的 current slot。运行时这正是 ping-pong，但当前分析若不跟踪 ring cursor 状态，就无法把 body 后半段的 `copy(next)` 标成“下一轮 body 开头 `matmul(next)` 的 producer”。

```mlir
// prologue after producer-consumer-analysis
%tsm_a0_slot = "dma.current_ring"(%tsm_a_ring)
%tsm_a0 = "dma.reinterpret"(%tsm_a0_slot, ...)
%global_a0 = "dma.reinterpret"(%lhs, ...)
"dma.deslice"(%tsm_a0, %global_a0, ...)
  {productor = [0]}

%tsm_b0_slot = "dma.current_ring"(%tsm_b_ring)
%tsm_b0 = "dma.reinterpret"(%tsm_b0_slot, ...)
%global_b0 = "dma.reinterpret"(%rhs, ...)
"dma.deslice"(%tsm_b0, %global_b0, ...)
  {productor = [1]}

%tlm_a0_slot = "dma.current_ring"(%tlm_a_ring)
%tlm_a0 = "dma.reinterpret"(%tlm_a0_slot, ...)
"dma.copy"(%tlm_a0, %tsm_a0)
  {consumer = [0]}

%tlm_b0_slot = "dma.current_ring"(%tlm_b_ring)
%tlm_b0 = "dma.reinterpret"(%tlm_b0_slot, ...)
"dma.copy"(%tlm_b0, %tsm_b0)
  {consumer = [1]}

// 上面两个 copy 在运行时也生产了 TLM current slot 的内容。
// 如果分析能证明 loop 开头的 current_ring 仍指向同一 slot，理想标注应是：
//   "dma.copy"(%tlm_a0, %tsm_a0) {consumer = [0], loop_body_productor = [4]}
//   "dma.copy"(%tlm_b0, %tsm_b0) {consumer = [1], loop_body_productor = [5]}
// 但当前 producer-consumer-analysis 只按 SSA alias/use-def 建边；
// %tlm_a0 和 loop 里的 %tlm_a_cur 来自两次不同的 current_ring，当前不会自动判成同一 slot。

symbol.for %k = %k0 to %steady_end step %tile_k {
  // runtime 上，这个 current slot 是 prologue 或上一轮 body copy 好的 tile。
  // 静态分析若不建模 ring cursor，看不到它与那些 copy op 的 producer edge。
  %tlm_a_cur_slot = "dma.current_ring"(%tlm_a_ring)
  %tlm_a_cur = "dma.reinterpret"(%tlm_a_cur_slot, ...)
  %tlm_b_cur_slot = "dma.current_ring"(%tlm_b_ring)
  %tlm_b_cur = "dma.reinterpret"(%tlm_b_cur_slot, ...)
  "kernel.matmul"(%acc, %tlm_a_cur, %tlm_b_cur, %acc_flag)
    // 缺口：这里理想上应消费 prologue/body preload 的结果。

  "dma.advance_ring"(%tlm_a_ring)
  "dma.advance_ring"(%tlm_b_ring)

  %tsm_a_next_slot = "dma.current_ring"(%tsm_a_ring)
  %tsm_a_next = "dma.reinterpret"(%tsm_a_next_slot, ...)
  %global_a_next = "dma.reinterpret"(%lhs, ...)
  "dma.deslice"(%tsm_a_next, %global_a_next, ...)
    {productor = [2]}

  %tsm_b_next_slot = "dma.current_ring"(%tsm_b_ring)
  %tsm_b_next = "dma.reinterpret"(%tsm_b_next_slot, ...)
  %global_b_next = "dma.reinterpret"(%rhs, ...)
  "dma.deslice"(%tsm_b_next, %global_b_next, ...)
    {productor = [3]}

  %tlm_a_next_slot = "dma.current_ring"(%tlm_a_ring)
  %tlm_a_next = "dma.reinterpret"(%tlm_a_next_slot, ...)
  "dma.copy"(%tlm_a_next, %tsm_a_next)
    {consumer = [2], after_loop_productor = [4]}

  %tlm_b_next_slot = "dma.current_ring"(%tlm_b_ring)
  %tlm_b_next = "dma.reinterpret"(%tlm_b_next_slot, ...)
  "dma.copy"(%tlm_b_next, %tsm_b_next)
    {consumer = [3], after_loop_productor = [5]}

  "dma.advance_ring"(%tsm_a_ring)
  "dma.advance_ring"(%tsm_b_ring)
  // TLM ring 不在 copy 后 advance；下一轮 matmul 前的 current_ring 应读到这个 next tile。
  // 这两个 copy 在 runtime 上生产下一轮 loop 开头 matmul 的输入；
  // 当前分析若不建模 ring cursor，只容易标出 after_loop 到 epilogue 的消费边，
  // 难以标出 “本轮 copy -> 下一轮 matmul” 的 loop-carried producer/consumer 边。
}

// epilogue after producer-consumer-analysis
"kernel.matmul"(%acc, %tlm_a_last, %tlm_b_last, %acc_flag_last)
  {after_loop_consumer = [4, 5]}
```

如果为了让第一轮 compute 直接消费 prologue 的 `%tlm_a0/%tlm_b0`，把 steady loop 的 matmul 写成直接用 `%tlm_a0/%tlm_b0`，分析可以得到：

```mlir
"dma.copy"(%tlm_a0, %tsm_a0)
  {consumer = [0], loop_body_productor = [2]}
"dma.copy"(%tlm_b0, %tsm_b0)
  {consumer = [1], loop_body_productor = [3]}

symbol.for %k = %k0 to %steady_end step %tile_k {
  "kernel.matmul"(%acc, %tlm_a0, %tlm_b0, %acc_flag)
    {loop_body_consumer = [2, 3]}
  ...
}
```

但这个 IR 语义是错的：每一轮都会消费 prologue 的 k0 tile，而不是消费上一轮 body preload 出来的 next tile。因此它只能说明当前分析能标注 prologue-to-loop edge，不能作为正确 ping-pong IR。

| edge | producer | consumer | 说明 |
| --- | --- | --- | --- |
| P0-A | prologue `global A k0 -> tsm` | prologue `tsm A k0 -> tlm` | prologue 内普通 edge |
| P0-B | prologue `global B k0 -> tsm` | prologue `tsm B k0 -> tlm` | prologue 内普通 edge |
| P1-A | prologue `tsm A k0 -> tlm` | steady 第一次 `matmul(k0)` | prologue 到 loop body edge |
| P1-B | prologue `tsm B k0 -> tlm` | steady 第一次 `matmul(k0)` | prologue 到 loop body edge |
| S0-A | steady `global A k_next -> tsm` | steady `tsm A k_next -> tlm` | steady body 内普通 edge |
| S0-B | steady `global B k_next -> tsm` | steady `tsm B k_next -> tlm` | steady body 内普通 edge |
| S1-A | steady `tsm A k_next -> tlm` | 下一轮 steady `matmul(k_next)` 或 epilogue `matmul(last)` | loop-carried / after-loop edge |
| S1-B | steady `tsm B k_next -> tlm` | 下一轮 steady `matmul(k_next)` 或 epilogue `matmul(last)` | loop-carried / after-loop edge |

这里的难点是 `S1-A` / `S1-B`。当前 `producer-consumer-analysis` 第一阶段只承诺静态分类，不承诺 loop-carried runtime 精确语义。因此，先分离再分析会让核心 ping-pong 关系落到“本轮 preload 供下一轮 compute”这种跨迭代边上，分析复杂度比在原始 `24 -> 25` 上读取 `copy -> matmul` 关系更高。

若坚持该路线，需要先明确至少一个 IR 承载方式：

- `symbol.for` 支持显式 loop-carried tile view / ring slot view。
- 或新增 / 明确 ring slot 的相对访问语义，例如 current / next / previous slot view。
- 或 ping-pong pass 自己维护调度映射，并不依赖分离后重新分析出 loop-carried edge。

在未确认这些承载方式前，`先分离、再分析` 更适合作为设计草稿，不建议作为第一版实现路线。

## 备选草稿：multi-buffer 前先分离

另一种方案是在 `multi-buffer` 之前先做首尾分离，然后再尝试让 `multi-buffer` 对分离后的 staging buffer 做 ring 化。此时 IR 中还没有 `dma.make_ring` / `dma.current_ring` / `dma.advance_ring`，只有普通 staging buffer。

概念 IR 如下：

```mlir
// loop 外普通 staging alloc，尚未 multi-buffer/ring 化
%acc = "dma.alloc"(%tile_h, %tile_w)
  : (...) -> !nn.memory<[#S_TILE_H, #S_TILE_W], ..., #nn.space<tsm>>

%tsm_a = "dma.alloc"(%tile_h, %tile_k)
  : (...) -> !nn.memory<[#S_TILE_H, #S_TILE_K], ..., #nn.space<tsm>>
%tsm_b = "dma.alloc"(%tile_k, %tile_w)
  : (...) -> !nn.memory<[#S_TILE_K, #S_TILE_W], ..., #nn.space<tsm>>

%tlm_a = "dma.alloc"(%tile_h, %tile_k)
  : (...) -> !nn.memory<[#S_TILE_H, #S_TILE_K], ..., #nn.space<tlm1>>
%tlm_b = "dma.alloc"(%tile_k, %tile_w)
  : (...) -> !nn.memory<[#S_TILE_K, #S_TILE_W], ..., #nn.space<tlm2>>

"dma.fill"(%acc, %zero)

// prologue: preload k0
%k0 = symbol.const 0 : !symbol.int<#C0>
%k0_size = symbol.min %tile_k, %K

%global_a0 = "dma.reinterpret"(%lhs, %lhs_offset_k0, %tile_h_eff, %k0_size, ...)
%global_b0 = "dma.reinterpret"(%rhs, %rhs_offset_k0, %k0_size, %tile_w_eff, ...)

%tsm_a0 = "dma.reinterpret"(%tsm_a, %c0, %tile_h_eff, %k0_size, ...)
%tsm_b0 = "dma.reinterpret"(%tsm_b, %c0, %k0_size, %tile_w_eff, ...)

"dma.deslice"(%tsm_a0, %global_a0, ...)
"dma.deslice"(%tsm_b0, %global_b0, ...)

%tlm_a0 = "dma.reinterpret"(%tlm_a, %c0, %tile_h_eff, %k0_size, ...)
%tlm_b0 = "dma.reinterpret"(%tlm_b, %c0, %k0_size, %tile_w_eff, ...)

"dma.copy"(%tlm_a0, %tsm_a0)
"dma.copy"(%tlm_b0, %tsm_b0)

// steady: compute current, then preload next into the same buffers
symbol.for %k = %k0 to %steady_end step %tile_k {
  %acc_flag = symbol.ne %k, %k0

  %k_cur_size = symbol.min %tile_k, %K_minus_k
  %tlm_a_cur = "dma.reinterpret"(%tlm_a, %c0, %tile_h_eff, %k_cur_size, ...)
  %tlm_b_cur = "dma.reinterpret"(%tlm_b, %c0, %k_cur_size, %tile_w_eff, ...)

  "kernel.matmul"(%acc, %tlm_a_cur, %tlm_b_cur, %acc_flag)

  %k_next = symbol.add %k, %tile_k
  %k_next_size = symbol.min %tile_k, %K_minus_k_next

  %global_a_next = "dma.reinterpret"(%lhs, %lhs_offset_next, %tile_h_eff, %k_next_size, ...)
  %global_b_next = "dma.reinterpret"(%rhs, %rhs_offset_next, %k_next_size, %tile_w_eff, ...)

  %tsm_a_next = "dma.reinterpret"(%tsm_a, %c0, %tile_h_eff, %k_next_size, ...)
  %tsm_b_next = "dma.reinterpret"(%tsm_b, %c0, %k_next_size, %tile_w_eff, ...)

  "dma.deslice"(%tsm_a_next, %global_a_next, ...)
  "dma.deslice"(%tsm_b_next, %global_b_next, ...)

  %tlm_a_next = "dma.reinterpret"(%tlm_a, %c0, %tile_h_eff, %k_next_size, ...)
  %tlm_b_next = "dma.reinterpret"(%tlm_b, %c0, %k_next_size, %tile_w_eff, ...)

  "dma.copy"(%tlm_a_next, %tsm_a_next)
  "dma.copy"(%tlm_b_next, %tsm_b_next)
}

// epilogue: compute last preloaded tile
%tlm_a_last = "dma.reinterpret"(%tlm_a, %c0, %tile_h_eff, %k_last_size, ...)
%tlm_b_last = "dma.reinterpret"(%tlm_b, %c0, %k_last_size, %tile_w_eff, ...)

"kernel.matmul"(%acc, %tlm_a_last, %tlm_b_last, %true)

// bias / output writeback 仍在 K 维完成后
"dma.deslice"(%out, %acc, %i, %j, %tile_h_eff, %tile_w_eff, ...)
```

这个方案给 `multi-buffer` 的输入关系变成：

```text
prologue copy(k0) -> steady matmul(k0)
steady copy(k+1)  -> 下一轮 steady matmul(k+1)
steady copy(last) -> epilogue matmul(last)
```

而当前 `multi-buffer` 更容易处理的是未分离前的局部关系：

```text
symbol.for %k {
  copy(k)
  matmul(k)
}
```

因此，`multi-buffer` 前先分离会把原本局部的 producer/consumer 链拆成跨 prologue / loop / epilogue、跨迭代的生命周期。若要让现有 `multi-buffer` pass 处理这种输入，需要增强它至少识别：

- prologue、steady loop、epilogue 三段共同使用的同一组 staging buffer。
- steady loop 中 `matmul(current)` 先读、`copy(next)` 后写的 slot 生命周期。
- `copy(next)` 到下一轮 `matmul(current)` 的 loop-carried 使用关系。
- epilogue 对最后一次 preload 的消费关系。

这会把 `multi-buffer` 从“ring 化局部 staging 生命周期”的 pass 推向“识别并实现 ping-pong 调度”的 pass，复杂度接近直接做 `loop-pingpong`。因此该方案可以保留为设计草稿，但不建议作为第一版路线。

## 通用草稿：基于 ring current / advance 的关系识别

如果 `loop-pingpong` 要通用，它不应匹配固定的 `dma.copy -> kernel.matmul`，而应匹配同一个 ring 上的 current / advance 状态变化：

```text
WRITE(current slot)
READ(current slot)
advance ring
WRITE(new current slot)
下一轮 READ(current slot)
```

概念 IR 如下。`some.writer` / `some.reader` 代表任意带 MemoryEffect 的 op，不限定为 `dma.copy` 或 `kernel.matmul`。

```mlir
// ring 已由 multi-buffer 建好
%ring = "dma.make_ring"(%backing, %num, %slot_bytes)
  : (...) -> !dma.ring<!nn.memory<[...], [...], f32, #nn.space<tlm1>>>

// prologue: 写入初始 current slot，写完后不 advance
%slot0 = "dma.current_ring"(%ring)
%slot0_view = "dma.reinterpret"(%slot0, ...)
"some.writer"(%slot0_view, %src0)
  // WRITE(%slot0_view), READ(%src0)

symbol.for %i = %c0 to %steady_end step %step {
  // 读取当前 slot；第一轮读 prologue 写入的 slot，
  // 后续轮次读上一轮 body 写入的 slot。
  %slot_cur = "dma.current_ring"(%ring)
  %slot_cur_view = "dma.reinterpret"(%slot_cur, ...)
  "some.reader"(%slot_cur_view)
    // READ(%slot_cur_view)

  // 推进 cursor。advance 本身只改变后续 current_ring 看到的 slot，
  // 不携带读/写含义。
  "dma.advance_ring"(%ring)

  // advance 后的 current_ring 取得 next slot；这里选择把它作为写入目标。
  // 写完后不 advance；下一轮 loop entry 的 current_ring 仍会取得这个 slot。
  %slot_next = "dma.current_ring"(%ring)
  %slot_next_view = "dma.reinterpret"(%slot_next, ...)
  "some.writer"(%slot_next_view, %src_next)
    // WRITE(%slot_next_view), READ(%src_next)
}

// epilogue: 消费最后一次 body 写入但尚未 advance 的 slot
%slot_last = "dma.current_ring"(%ring)
%slot_last_view = "dma.reinterpret"(%slot_last, ...)
"some.reader"(%slot_last_view)
  // READ(%slot_last_view)
"dma.advance_ring"(%ring)
```

这段 IR 的通用运行时关系是：

| 阶段 | producer | consumer |
| --- | --- | --- |
| prologue -> loop first | prologue `some.writer(%slot0)` | steady 第一轮 `some.reader(current_ring(%ring))` |
| loop-carried | 本轮 body `some.writer(%slot_next)` | 下一轮 body `some.reader(current_ring(%ring))` |
| loop -> epilogue | 最后一轮 body `some.writer(%slot_next)` | epilogue `some.reader(current_ring(%ring))` |

这个表只是在抽象层面说“谁供谁用”，还不够。真正判断边时，必须把 ring cursor 和 MemoryEffect 分成两个维度：

- `current_ring` 先出现，再 `advance_ring`，说明前者拿到的是“advance 前的当前 slot”。
- `advance_ring` 先出现，再 `current_ring`，说明后者拿到的是“advance 后的新 current slot”。
- 已经 materialize 出来的 `%slot_cur` 不会因为后面又 `advance_ring` 而改名；`advance_ring` 只影响后续新的 `current_ring`。
- `advance_ring` 本身不表示读或写；某个 slot 是 producer 还是 consumer，要看使用该 slot view 的 op 是 `WRITE` 还是 `READ`。

所以，分析时不能只问“是不是同一个 ring”，还要先根据 `current` / `advance` 还原每个 slot view 对应哪个 cursor 位置，再根据 MemoryEffect 判断它是写入还是读取。producer/consumer 边来自“同一个 slot 上先 WRITE、后 READ”，不是来自 `advance_ring` 自己。

更精确地说，分析分两步：

| 步骤 | 看什么 | 得到什么 |
| --- | --- | --- |
| cursor trace | `current_ring` / `advance_ring` 的顺序 | `%view0` 是 `slot0`，`%view1` 是 `slot1`，下一轮 `%view2` 又是哪个 slot |
| effect trace | 使用这些 view 的 op 的 MemoryEffect | `WRITE(slot0)`、`READ(slot0)`、`WRITE(slot1)`、`READ(slot1)` |

只有把这两步合起来，才得到 producer/consumer：

```text
WRITE(slot0) -> 后续 READ(slot0)
WRITE(slot1) -> 后续 READ(slot1)
```

### 最小例子：只靠 ring cursor 推导消费边

假设 `%ring` 有两个 slot，cursor 初始指向 `slot0`。下面例子故意不用 `dma.copy` / `kernel.matmul`，只用抽象的 `demo.produce` 和 `demo.consume` 表达 MemoryEffect：

```mlir
// cursor = slot0
%ring = "dma.make_ring"(%buffer, %c2, %slot_bytes)
  : (...) -> !dma.ring<!nn.memory<[...], [...], f32, #nn.space<tlm1>>>

// prologue: 生产 slot0，写完不 advance。
%p0_slot = "dma.current_ring"(%ring)
%p0_view = "dma.reinterpret"(%p0_slot, ...)
"demo.produce"(%p0_view, %src0)
  // WRITE(slot0)

symbol.for %i = %c0 to %n_minus_1 step %c1 {
  // loop entry cursor 指向“已经生产好、等待消费”的 slot。
  %read_slot = "dma.current_ring"(%ring)
  %read_view = "dma.reinterpret"(%read_slot, ...)
  "demo.consume"(%read_view)
    // READ(current slot)

  // 推进 cursor。advance 不说明前面的 op 是读，也不说明后面的 op 是写；
  // 它只让后续 current_ring 取得下一个 slot。
  "dma.advance_ring"(%ring)

  // advance 后的 current_ring 取得 slot1；这里选择写它。
  // 因为写完后不 advance，下一轮 loop entry 的 current_ring 仍然取得 slot1。
  %write_slot = "dma.current_ring"(%ring)
  %write_view = "dma.reinterpret"(%write_slot, ...)
  "demo.produce"(%write_view, %src_next)
    // WRITE(next slot)

  // 这里不 advance。下一轮 loop entry 的 current_ring 仍然读到刚写的 slot。
}

// epilogue: loop 最后一轮写完后未 advance 的 slot。
%last_slot = "dma.current_ring"(%ring)
%last_view = "dma.reinterpret"(%last_slot, ...)
"demo.consume"(%last_view)
  // READ(last produced slot)
"dma.advance_ring"(%ring)
```

这个例子中，producer/consumer 关系可以由 cursor 状态直接推出：

| 时间点 | cursor 状态 | 事件 | 推出的边 |
| --- | --- | --- | --- |
| prologue | `slot0` | `demo.produce(slot0)` | 生产第一轮输入 |
| loop 第 0 轮入口 | `slot0` | `demo.consume(slot0)` | prologue produce -> 第 0 轮 consume |
| loop 第 0 轮 advance 后 | `slot1` | `demo.produce(slot1)` | 生产第 1 轮输入 |
| loop 第 1 轮入口 | `slot1` | `demo.consume(slot1)` | 第 0 轮 produce -> 第 1 轮 consume |
| loop 第 1 轮 advance 后 | `slot0` | `demo.produce(slot0)` | 生产第 2 轮输入 |
| loop 退出后 | 最后一轮写入的 slot | `demo.consume(current)` | 最后一轮 produce -> epilogue consume |

所以这里不是“不能分析”。准确说，必须是 ring-aware 分析：分析状态里要记录同一个 `%ring` 的 cursor，在 `current_ring` 时读出当前 slot，在 `advance_ring` 时更新 cursor，并把同一 slot 上最近一次 WRITE 连到后续 READ。

若分析只把每次 `dma.current_ring(%ring)` 的 SSA 结果当成彼此无关的值，就会漏掉：

```text
body produce(next slot) -> 下一轮 body consume(current slot)
```

而 ring-aware 后，这条边并不依赖 op 名字，`demo.produce/demo.consume`、`dma.copy/kernel.matmul` 都是同一种模式。

因此 `loop-pingpong` 的通用判断点是：

- 同一个 `%ring` 上，reader 使用 `current_ring(%ring)` 的 slot。
- reader 的最后一次读之后出现 `dma.advance_ring(%ring)`。
- advance 后的 writer 使用新的 `current_ring(%ring)` slot。
- writer 后到 loop 尾之间没有再次 `dma.advance_ring(%ring)`。
- prologue 写初始 current slot后不 advance；epilogue 消费最后 current slot后再 advance。

这套规则只依赖 ring cursor 语义和 MemoryEffect，不依赖具体 op 名字。`matmul/copy` 只是该模式的一个实例：

```text
some.reader = kernel.matmul 读 tlm slot
some.writer = dma.copy 或 dma.deslice 写 tlm/tsm slot
```

如果 `producer-consumer-analysis` 放在 ping-pong 后，它要完整标出上表关系，就不能只看 SSA use-def；还需要具备同样的 ring-aware 状态规则，或消费 ping-pong pass 留下的显式调度元信息 / loop-carried slot。

## Ping-pong 后逐 buffer 的生产消费结果

本节给出 `24-multi-buffer.mlir` 对应的 matmul dynamic/dynamic 在完成 ping-pong 后，理想 `producer-consumer-analysis` 应该看到的逻辑结果。这里用符号事件名说明关系，不承诺最终 attr 必须使用这些名字。

### Buffer 清单

当前 `24-multi-buffer.mlir` 中与 K 维 staging 相关的 buffer 可以按功能分成：

| 名称 | 当前 IR 中的对象 | 空间 | 是否 ring | 作用 |
| --- | --- | --- | --- | --- |
| `lhs` | `%1` | global | 否 | A 矩阵全局输入 |
| `rhs` | `%2` | global | 否 | B 矩阵全局输入 |
| `tsm_a_ring` | `%66` | tsm | 是 | A tile 的 global -> tsm staging |
| `tsm_b_ring` | `%69` | tsm | 是 | B tile 的 global -> tsm staging |
| `tlm_a_ring` | `%82` | tlm1 | 是 | A tile 的 tsm -> tlm staging，供 matmul 读 |
| `tlm_b_ring` | `%95` | tlm2 | 是 | B tile 的 tsm -> tlm staging，供 matmul 读 |
| `acc` | `%103`，来自 `%12` | tsm | 否 | H/W output tile accumulator |
| `bias_vec` | `%104/%105`，来自 `%14` | tsm | 否 | bias vector tile |
| `bias_tile` | `%106`，来自 `%15` | tsm | 否 | broadcast 后的 bias tile |
| `out` | `%0` | global | 否 | output 全局写回目标 |

其中只有 A/B 输入链路参与 K 维 ping-pong：

```text
lhs/rhs -> tsm_a/tsm_b -> tlm_a/tlm_b -> matmul
```

`acc`、`bias_vec`、`bias_tile`、`out` 不参与 A/B 输入 ping-pong。它们仍然要参与 producer/consumer 分析，但不是 ring cursor 问题。

### 事件命名

令 K 维共有 `N` 个 tile，tile 序号为 `t = 0 .. N-1`。ping-pong 后可把事件命名为：

| 事件 | IR 操作形态 | 读 | 写 |
| --- | --- | --- | --- |
| `A_G2S[t]` | `dma.deslice(%tsm_a_t, %lhs_t, ...)` | `lhs[t]` | `tsm_a_slot_for_t` |
| `B_G2S[t]` | `dma.deslice(%tsm_b_t, %rhs_t, ...)` | `rhs[t]` | `tsm_b_slot_for_t` |
| `A_S2L[t]` | `dma.copy(%tlm_a_t, %tsm_a_t)` | `tsm_a_slot_for_t` | `tlm_a_slot_for_t` |
| `B_S2L[t]` | `dma.copy(%tlm_b_t, %tsm_b_t)` | `tsm_b_slot_for_t` | `tlm_b_slot_for_t` |
| `M[t]` | `kernel.matmul(%acc, %tlm_a_t, %tlm_b_t, %acc_flag_t)` | `tlm_a_slot_for_t`, `tlm_b_slot_for_t`, old `acc` when accumulating | new `acc` |
| `ACC_FILL` | `dma.fill(%acc, %zero)` | constant | `acc` |
| `BIAS_LOAD` | `dma.deslice(%bias_vec, %bias_global, ...)` | global bias | `bias_vec` |
| `BIAS_BCAST` | `dma.broadcast(%bias_tile, %bias_vec)` | `bias_vec` | `bias_tile` |
| `BIAS_ADD` | `kernel.binary_elewise(%acc, %acc, %bias_tile)` | old `acc`, `bias_tile` | new `acc` |
| `OUT_STORE` | `dma.deslice(%out, %acc, ...)` | final `acc` | `out` |

### Ping-pong 调度后的 cursor 形态

用 `A_TSM[t]` 表示承载第 `t` 个 A tile 的 TSM slot，用 `A_TLM[t]` 表示承载第 `t` 个 A tile 的 TLM slot；B 同理。它们不是固定 SSA 名字，而是 ring cursor 在运行时对应的逻辑 slot。

```text
prologue:
  current(tsm_a) -> A_TSM[0]
  A_G2S[0] writes A_TSM[0]
  current(tlm_a) -> A_TLM[0]
  A_S2L[0] reads A_TSM[0], writes A_TLM[0]
  advance(tsm_a)
  // tlm_a 不 advance，第一轮 M[0] 要读 A_TLM[0]

  current(tsm_b) -> B_TSM[0]
  B_G2S[0] writes B_TSM[0]
  current(tlm_b) -> B_TLM[0]
  B_S2L[0] reads B_TSM[0], writes B_TLM[0]
  advance(tsm_b)
  // tlm_b 不 advance

steady body for t = 0 .. N-2:
  current(tlm_a) -> A_TLM[t]
  current(tlm_b) -> B_TLM[t]
  M[t] reads A_TLM[t], B_TLM[t], updates acc

  advance(tlm_a)
  advance(tlm_b)

  current(tsm_a) -> A_TSM[t + 1]
  A_G2S[t + 1] writes A_TSM[t + 1]
  current(tlm_a) -> A_TLM[t + 1]
  A_S2L[t + 1] reads A_TSM[t + 1], writes A_TLM[t + 1]
  advance(tsm_a)
  // tlm_a 不 advance，下一轮 M[t + 1] 要读 A_TLM[t + 1]

  current(tsm_b) -> B_TSM[t + 1]
  B_G2S[t + 1] writes B_TSM[t + 1]
  current(tlm_b) -> B_TLM[t + 1]
  B_S2L[t + 1] reads B_TSM[t + 1], writes B_TLM[t + 1]
  advance(tsm_b)
  // tlm_b 不 advance

epilogue:
  current(tlm_a) -> A_TLM[N - 1]
  current(tlm_b) -> B_TLM[N - 1]
  M[N - 1] reads A_TLM[N - 1], B_TLM[N - 1], updates acc
  advance(tlm_a)
  advance(tlm_b)
```

当 `N == 1` 时，steady body 可以为空，关系退化为：

```text
prologue A_S2L[0] / B_S2L[0] -> epilogue M[0]
```

也就是说，分类从 `prologue -> loop first` 变成 `prologue -> epilogue`，但 slot 证明仍然一样：TLM copy 后没有 advance，epilogue 的 `current(tlm_*)` 仍指向同一个 slot。

这里最关键的是 TLM ring：

```text
A_S2L[0]       -> M[0]       // prologue -> loop first
A_S2L[t + 1]   -> M[t + 1]   // body t -> next body, 或 body last -> epilogue
B_S2L[0]       -> M[0]
B_S2L[t + 1]   -> M[t + 1]
```

TSM ring 不形成这个跨迭代消费边。TSM 的生产和消费仍在同一个 preload 阶段内完成：

```text
A_G2S[t] -> A_S2L[t]
B_G2S[t] -> B_S2L[t]
```

### 逐 buffer 的 producer/consumer 边

#### `lhs` / `rhs` global input

`lhs` 和 `rhs` 是函数入参，全局输入在函数内没有 producer。它们作为 source 被每个 K tile 的 global -> tsm 搬运读取：

| buffer | producer | consumer |
| --- | --- | --- |
| `lhs[t]` | 函数外部输入 | `A_G2S[t]` |
| `rhs[t]` | 函数外部输入 | `B_G2S[t]` |

如果当前分析只标函数内 op，则可以不为函数入参生成 `productor`，只记录 `A_G2S[t]` / `B_G2S[t]` 对 global view 的 READ。

#### `tsm_a_ring`

`tsm_a_ring` 的每个 slot 是临时中转：被 `A_G2S[t]` 写入，然后立刻被 `A_S2L[t]` 读取。之后 TSM ring 可以 advance 到下一个可写 slot。

| tile | producer | consumer | 边类型 |
| --- | --- | --- | --- |
| `t = 0` | prologue `A_G2S[0]` | prologue `A_S2L[0]` | 同 block / same phase |
| `1 <= t <= N-1` | body `A_G2S[t]` | body `A_S2L[t]` | 同一 steady iteration 的 preload 阶段 |

分析方法：

```text
current(tsm_a) -> view X
A_G2S writes X
A_S2L reads X
advance(tsm_a)
```

因此 producer/consumer 是 `WRITE(X) -> READ(X)`。`advance(tsm_a)` 只说明后续 `current(tsm_a)` 不再是 X，不参与该边本身。

#### `tsm_b_ring`

`tsm_b_ring` 与 `tsm_a_ring` 对称：

| tile | producer | consumer | 边类型 |
| --- | --- | --- | --- |
| `t = 0` | prologue `B_G2S[0]` | prologue `B_S2L[0]` | 同 block / same phase |
| `1 <= t <= N-1` | body `B_G2S[t]` | body `B_S2L[t]` | 同一 steady iteration 的 preload 阶段 |

分析方法同样是：

```text
current(tsm_b) -> view Y
B_G2S writes Y
B_S2L reads Y
advance(tsm_b)
```

#### `tlm_a_ring`

`tlm_a_ring` 是 ping-pong 的核心。它的写发生在 preload 阶段，读发生在后续 compute 阶段。

| tile | producer | consumer | 边类型 |
| --- | --- | --- | --- |
| `t = 0` | prologue `A_S2L[0]` | steady 第一轮 `M[0]` | prologue -> loop first |
| `1 <= t <= N-2` | steady 第 `t-1` 轮 `A_S2L[t]` | steady 第 `t` 轮 `M[t]` | loop-carried |
| `t = N-1` | steady 第 `N-2` 轮 `A_S2L[N-1]` | epilogue `M[N-1]` | loop -> epilogue |

对应 cursor trace：

```text
prologue:
  current(tlm_a) -> A_TLM[0]
  A_S2L[0] writes A_TLM[0]
  // no advance(tlm_a)

steady t:
  current(tlm_a) -> A_TLM[t]
  M[t] reads A_TLM[t]
  advance(tlm_a)
  current(tlm_a) -> A_TLM[t + 1]
  A_S2L[t + 1] writes A_TLM[t + 1]
  // no advance(tlm_a)

next steady:
  current(tlm_a) -> A_TLM[t + 1]
  M[t + 1] reads A_TLM[t + 1]
```

producer/consumer 来自：

```text
WRITE(A_TLM[t]) -> READ(A_TLM[t])
```

不是来自 `advance(tlm_a)`。`advance(tlm_a)` 只是把后续写切到另一个 slot，从而避免覆盖当前正在被 `M[t]` 读取的 slot。

#### `tlm_b_ring`

`tlm_b_ring` 与 `tlm_a_ring` 对称：

| tile | producer | consumer | 边类型 |
| --- | --- | --- | --- |
| `t = 0` | prologue `B_S2L[0]` | steady 第一轮 `M[0]` | prologue -> loop first |
| `1 <= t <= N-2` | steady 第 `t-1` 轮 `B_S2L[t]` | steady 第 `t` 轮 `M[t]` | loop-carried |
| `t = N-1` | steady 第 `N-2` 轮 `B_S2L[N-1]` | epilogue `M[N-1]` | loop -> epilogue |

对应 producer/consumer：

```text
WRITE(B_TLM[t]) -> READ(B_TLM[t])
```

#### `acc`

`acc` 不参与 ping-pong，它是整个 K loop 的累加目标。ping-pong 只改变 A/B tile 何时进入 TLM，不改变 `acc` 的生命周期。

| 阶段 | producer | consumer |
| --- | --- | --- |
| 初始化 | `ACC_FILL` | `M[0]` 或 zero-K 情况下的 post-loop consumer |
| K 累加 | `M[t]` | `M[t + 1]` |
| K loop 结束 | `M[N - 1]` | `BIAS_ADD` 或 `OUT_STORE` |
| bias add 后 | `BIAS_ADD` | `OUT_STORE` |

如果 `kernel.matmul` 在 `acc_flag=false` 的第一轮语义上完全覆盖 `acc`，那么 `ACC_FILL -> M[0]` 可以被更精细的语义削弱；但在当前 pass 视角下，更保守的 MemoryEffect 是把 `kernel.matmul(%acc, ...)` 当作对 `acc` 的读写，保留 `ACC_FILL -> M[0]` 不会破坏正确性。

#### `bias_vec` / `bias_tile`

bias 发生在 K loop 之后，不参与 ping-pong。

| buffer | producer | consumer |
| --- | --- | --- |
| `bias_vec` | `BIAS_LOAD` | `BIAS_BCAST` |
| `bias_tile` | `BIAS_BCAST` | `BIAS_ADD` |
| `acc` | `M[N - 1]` | `BIAS_ADD` |
| `acc` | `BIAS_ADD` | `OUT_STORE` |

如果 bias 指针为空，整个 if 分支不存在或不执行，则结果是：

```text
M[N - 1] -> OUT_STORE
```

#### `out`

`out` 是最终全局写回目标。函数内最后一个 producer 是：

```text
OUT_STORE writes out tile
```

它在当前函数内通常没有后续 consumer；函数外 consumer 不属于本 pass 的局部分析范围。

### 分析算法草稿

后置 `producer-consumer-analysis` 若要分析 ping-pong 后 IR，需要按下面顺序做。

第一步，建立 view alias：

```text
dma.current_ring(%ring) 产生 ring slot view
dma.reinterpret(%slot, ...) 继承 slot 身份，只改变 view range/shape
普通 dma.reinterpret(%mem, ...) 继承 base memory 身份
```

第二步，做 ring cursor trace。对每个 `%ring` 单独维护一个 symbolic cursor：

```text
current_ring(%ring)  -> 读取当前 cursor 对应的 slot
advance_ring(%ring)  -> cursor = cursor + 1 mod ring_size
```

在 loop 中，不需要知道真实 slot 编号，也可以用相对状态表达：

```text
entry current = slot(t)
after advance current = slot(t + 1)
body 末尾如果没有 advance，则下一轮 entry current 仍是 slot(t + 1)
```

第三步，收集 MemoryEffect：

| op | 读 | 写 |
| --- | --- | --- |
| `dma.deslice(dst, src, ...)` | `src` | `dst` |
| `dma.copy(dst, src)` | `src` | `dst` |
| `kernel.matmul(acc, a, b, flag)` | `a`, `b`, conservative old `acc` | new `acc` |
| `dma.fill(dst, value)` | value | `dst` |
| `dma.broadcast(dst, src)` | `src` | `dst` |
| `kernel.binary_elewise(dst, lhs, rhs)` | `lhs`, `rhs` | `dst` |

第四步，对每个 slot/view 维护最近一次 writer：

```text
on WRITE(view):
  last_writer[view] = current op

on READ(view):
  if last_writer[view] exists:
    add edge last_writer[view] -> current op
```

对于 in-place op，例如：

```mlir
"kernel.binary_elewise"(%acc, %acc, %bias_tile)
```

要先处理 READ，再处理 WRITE：

```text
READ(old acc)  -> edge old_acc_writer -> BIAS_ADD
READ(bias_tile)-> edge BIAS_BCAST -> BIAS_ADD
WRITE(acc)     -> last_writer[acc] = BIAS_ADD
```

第五步，按控制流位置给边分类：

| producer 位置 | consumer 位置 | 分类 |
| --- | --- | --- |
| prologue | steady 第一轮 | prologue -> loop first |
| steady 第 `t` 轮 | steady 第 `t` 轮 | same-iteration |
| steady 第 `t` 轮 | steady 第 `t + 1` 轮 | loop-carried |
| steady 最后一轮 | epilogue | after-loop / loop -> epilogue |
| loop 前 | loop 后 | after-loop |
| if branch 内 | if 后 | after-if |

当前 attr 体系如果没有显式的 `loop_carried_productor` / `loop_carried_consumer`，就不能无损表达 `A_S2L[t] -> M[t]` 这类“body 第 `t-1` 轮写、body 第 `t` 轮读”的边。可以有两种落地方式：

- 给后置分析新增明确的 loop-carried 分类。
- 或由 `loop-pingpong` 输出显式调度元信息，让后续 pass 不需要只靠旧 attr 猜这个跨迭代边。

无论采用哪种方式，核心证明都还是同一个：

```text
cursor trace 证明两个 view 是同一个 ring slot
MemoryEffect 证明前者 WRITE、后者 READ
控制流位置证明这是 prologue/loop-carried/epilogue 哪一类边
```

## 为什么不能原样继承旧 attr

旧 attr 可以作为 ping-pong pass 的输入证据，但不能在 clone/reorder 后原样复制到新 op。

错误示例：

```text
ping-pong 前:
  copy(k)    {productor = [10]}
  matmul(k)  {consumer = [10]}

ping-pong 后如果原样 clone:
  prologue_copy(k0)  {productor = [10]}
  body_matmul(k0)    {consumer = [10]}
  body_copy(k1)      {productor = [10]}
  body_matmul(k1)    {consumer = [10]}
  epilogue_matmul    {consumer = [10]}
```

这里 `[10]` 同时表示多条不同 runtime 边：

```text
prologue_copy(k0) -> body_matmul(k0)
body_copy(k1)     -> next body_matmul(k1)
body_copy(last)   -> epilogue_matmul(last)
```

因此旧编号失真。更重要的是，边的控制流分类也会变：

- 原来同一 loop body 内的普通 producer/consumer edge，可能变成 prologue 到 loop body 的 edge。
- 原来同一轮内的 `copy -> matmul`，可能变成跨迭代的 `preload(k+1) -> compute(k+1)`。
- 原来 body 内 producer 到 loop 后 consumer 的 `after_loop_*`，在首尾分离后可能需要重新判断。

所以可以继承的是“谁生产的数据供谁消费”这个抽象关系，不能继承的是 `{productor = [id]}` / `{consumer = [id]}` 这类旧编号和旧分类。

## 推荐实现口径

ping-pong pass 应按以下方式处理：

1. 在 `multi-buffer` 之后、`producer-consumer-analysis` 之前运行。
2. 不依赖旧 `productor` / `consumer` attr，直接基于 `dma.current_ring` / `dma.advance_ring`、MemoryEffect 和 alias 关系识别 ring reader/writer 调度段。
3. 对 matmul dynamic/dynamic，这个通用模式会落到 A/B 的链路：

```text
global -> tsm -> tlm -> kernel.matmul
```

4. 基于 ring 状态机生成 prologue / steady / epilogue。
5. 生成新 IR 时清理旧 `productor` / `consumer` / `loop_body_*` / `after_loop_*` / `if_branch_*` / `after_if_*` attr。
6. 后续重新运行 `producer-consumer-analysis`；若它需要完整表达 loop-carried ring slot 消费，应补 ring-aware 规则或读取 ping-pong 输出的显式调度元信息。

## Accumulator 边界

输出 accumulator 不参与 A/B 输入 staging 的 ping-pong。

当前 dynamic/dynamic matmul 中，输出 tile `%acc` 对应的 `dma.fill`、`kernel.matmul` 累加、bias add 和最终 output `dma.deslice` 是跨整个 K loop 的结果链。ping-pong 只应调度 A/B 输入搬运和计算之间的重叠，不应把 output accumulator 当作随 K tile 轮换的 ring slot。
