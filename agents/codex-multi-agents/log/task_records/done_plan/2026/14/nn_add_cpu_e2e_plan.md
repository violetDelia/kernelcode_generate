# nn_add_cpu_e2e_plan.md

## 进度

| 编号 | 依赖 | worktree | 记录文件 | 进度 |
| --- | --- | --- | --- | --- |
| `S1` | `无` | `/wt-20260402-nn-add-s1` | `20260402-nn-add-cpu-s1.md` | `spec完成（2026-04-02 01:04:11 +0800，T-20260402-3ae4e4ad，睡觉小分队）；审查完成（需修改，2026-04-02 01:12:11 +0800，T-20260402-af233cf9，提莫炖蘑菇）；修正spec完成（2026-04-02 01:17:57 +0800，T-20260402-af60e147，睡觉小分队）；复审完成（2026-04-02 01:24:39 +0800，T-20260402-1cb5a501，不要啊教练）；已合并（2026-04-02 01:31:27 +0800，T-20260402-bfbae366，李白）` |
| `S2` | `S1` | `/wt-20260402-nn-add-s2` | `20260402-nn-add-cpu-s2.md` | `已建档（2026-04-02 01:33:26 +0800，T-20260402-4abc1814）；spec完成（2026-04-02 02:58:03 +0800，T-20260402-4abc1814，咯咯咯）；审查完成（需修改，2026-04-02 03:04:42 +0800，T-20260402-2f6a27cb，提莫炖蘑菇）；修正spec完成（2026-04-02 03:08:20 +0800，T-20260402-64549ec4，睡觉小分队）；复审完成（2026-04-02 03:53:21 +0800，T-20260402-fb677811，提莫炖蘑菇）；已合并（2026-04-02 04:00:52 +0800，T-20260402-c5431899，李白）` |
| `S3` | `S1、S2` | `/wt-20260402-nn-add-s3` | `20260402-nn-add-cpu-s3.md` | `已建档（2026-04-02 04:02:22 +0800，T-20260402-d4426a40）；spec完成（2026-04-02 04:21:38 +0800，T-20260402-d4426a40，睡觉小分队）；审查完成（需修改，2026-04-02 04:25:35 +0800，T-20260402-7c61ed67，提莫炖蘑菇）；修正spec完成（2026-04-02 04:30:28 +0800，T-20260402-7c435987，睡觉小分队）；复审完成（2026-04-02 04:34:22 +0800，T-20260402-c36f1c9b，不要啊教练）；已合并（2026-04-02 05:23:49 +0800，T-20260402-f62e301e，李白）` |
| `I1` | `S1、S2、S3` | `/wt-20260402-nn-add-i1` | `20260402-nn-add-i1.md` | `已完成并合并；按计划书口径验收通过（2026-04-02，大闸蟹）。` |
| `I2` | `I1` | `/wt-20260402-nn-add-i2` | `20260402-nn-add-i2.md` | `已完成；test/dsl/test_gen_kernel.py compile/run gate 由实现链补齐，expectation/dsl/emit_c/cpu/add.py 由大闸蟹负责并已回写；按计划书口径验收通过（2026-04-02，大闸蟹）。` |

## 功能说明

- 为 `nn.add` 的 CPU 端到端收口提供当前可执行计划。
- 本计划只描述“现在应该收敛成什么样”，不记录历史推进、旧任务状态或回退路径。
- 默认产物是交给管理员即可分发的任务清单、详细目标示例、下游收口顺序与机械验收标准。

## 使用示例

- 管理员先阅读“目标终态”和“详细示例”，确认实现者知道最终源码应该长什么样。
- 再按 `S1 -> S2 -> S3` 顺序分发任务；每个任务只改一个 `md` 文件。
- 相关文档约定明确后，再按“`include -> emit_c -> gen_kernel -> expectation -> 审查/复审/合并`”顺序推进实现链路。

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`大闸蟹`
- `文档`：[`ARCHITECTURE/plan/nn_add_cpu_e2e_plan.md`](../../ARCHITECTURE/plan/nn_add_cpu_e2e_plan.md)
- `spec`：
  - [`spec/dialect/nn.md`](../../spec/dialect/nn.md)
  - [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
  - [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md)
  - [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
  - [`spec/include/cpu/cpu.md`](../../spec/include/cpu/cpu.md)
- `功能实现`：
  - [`kernel_gen/dialect/nn.py`](../../kernel_gen/dialect/nn.py)
  - [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py)
  - [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py)
  - [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py)
  - [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)
  - [`include/cpu/Nn.h`](../../include/cpu/Nn.h)
- `test`：
  - [`test/dialect/test_nn_dialect.py`](../../test/dialect/test_nn_dialect.py)
  - [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py)
  - [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py)
  - [`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
  - [`test/dsl/test_emit_c.py`](../../test/dsl/test_emit_c.py)
  - [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)
  - [`test/include/cpu/test_nn.py`](../../test/include/cpu/test_nn.py)
  - [`expectation/dsl/emit_c/cpu/add.py`](../../expectation/dsl/emit_c/cpu/add.py)
  - [`expectation/pass/lowing/nn_to_kernel/add.py`](../../expectation/pass/lowing/nn_to_kernel/add.py)

## 当前范围

- 只收口 `target=cpu`。
- 只收口以下三条成功路径：
  - `memory + memory`
  - `memory + const(i32)`
  - `memory + symbol.int`
- 只收口 direct-return 场景：
  - `nn.add` 的结果唯一使用者是 `func.return`
  - 函数结果是 `Memory`
  - 终态必须落到 `cpu::add(..., out);`
- 不在本轮收口：
  - `f16/f32` mixed scalar codegen
  - 通用 memory SSA 临时物化
  - 多 use 的 `nn.add.result`
  - `sub/mul/truediv` 的同类 CPU E2E

## 目标终态

- 前半链路继续保持现状：
  - DSL / `build_func_op` / `emit_mlir` 可以生成 `nn.add`
  - `nn.add` mixed verifier 与 lowering 规则不回退
- CPU 终点统一收敛成：
  - 节点级：`emit_c` 对 `nn.add` 生成 `cpu::add(...)`
  - 函数级：`gen_kernel` 对 direct-return `nn.add` 生成 `cpu::add(..., out);`
  - expectation：[`expectation/dsl/emit_c/cpu/add.py`](../../expectation/dsl/emit_c/cpu/add.py) 三条路径全部成功

## 详细示例

### 示例 1：`memory + memory`

DSL 输入应允许写成：

```python
def add(lhs: "Tensor[i32, 2, 3]", rhs: "Tensor[i32, 2, 3]") -> "Tensor[i32, 2, 3]":
    return lhs + rhs
```

函数级目标源码应收敛成：

```cpp
void add(const Memory<int32_t>& lhs, const Memory<int32_t>& rhs, Memory<int32_t>& out) {
    cpu::add(lhs, rhs, out);
}
```

节点级目标语句应收敛成：

```cpp
cpu::add(lhs, rhs, out);
```

不能收敛成：

```cpp
Memory<int32_t> v0(...);
cpu::add(lhs, rhs, v0);
out = v0;
```

也不能收敛成：

```cpp
auto v0 = /* nn.add result */;
out = v0;
```

### 示例 2：`memory + const(i32)`

DSL 输入应允许写成：

```python
def add(lhs: "Tensor[i32, 2, 3]") -> "Tensor[i32, 2, 3]":
    return lhs + 1
```

函数级目标源码应收敛成：

```cpp
void add(const Memory<int32_t>& lhs, Memory<int32_t>& out) {
    cpu::add(lhs, 1, out);
}
```

节点级目标语句应收敛成：

```cpp
cpu::add(lhs, 1, out);
```

这里的目标重点是：

- 常量直接作为 CPU 标量实参出现。
- 不需要先把常量包成临时 `Memory`。
- 不需要把 `nn.add` 结果先命名成中间 memory 再写给 `out`。

### 示例 3：`memory + symbol.int`

DSL 输入应允许写成：

```python
def add(lhs: "Tensor[i32, 2, 3]", bias: int) -> "Tensor[i32, 2, 3]":
    return lhs + bias
```

函数级目标源码应收敛成：

```cpp
void add(const Memory<int32_t>& lhs, long long bias, Memory<int32_t>& out) {
    cpu::add(lhs, bias, out);
}
```

节点级目标语句应收敛成：

```cpp
cpu::add(lhs, bias, out);
```

这里必须明确一件事：

- `!symbol.int` 到 CPU 侧后的稳定公开形态是什么。
- 本轮计划要求在 [`spec/include/cpu/cpu.md`](../../spec/include/cpu/cpu.md) 里把这件事写死，不能把它留给实现自由发挥。

### 示例 4：本轮明确不做的形态

下面这种不是本轮目标：

```python
def add(lhs: "Tensor[f16, 2, 3]", bias: int) -> "Tensor[f16, 2, 3]":
    return lhs + bias
```

原因不是它永远不支持，而是：

- 这会引入 `f16` 的 C 类型映射
- 会引入标量 cast value 的节点级发射
- 会把当前 `i32` 最小闭环和 mixed dtype codegen 混成一个任务

下面这种也不是本轮目标：

```python
def add(lhs: "Tensor[i32, 2, 3]", rhs: "Tensor[i32, 2, 3]") -> "Tensor[i32, 2, 3]":
    tmp = lhs + rhs
    use(tmp)
    return tmp
```

因为这不是 direct-return unique-use 场景；本轮不把它定义成通用 `nn.add` codegen 合同。

## 错误示例

以下结果都不应被写进 spec、测试预期或 expectation 成功口径：

```cpp
out = v0;
```

```cpp
out = arg0;
```

```cpp
return v0;
```

```cpp
// 生成结果里仍出现 nn.add 或 kernel.add
```

```python
# expectation 里仍把 memory + const / memory + symbol 写成应该失败
```

## 关键边界

- `emit_c` 的职责：
  - 只负责单个 `nn.add` 节点如何发成 `cpu::add(...)`
  - 不负责决定什么时候把结果绑定成函数级 `out`
- `gen_kernel` 的职责：
  - 只负责 direct-return unique-use 场景下把目标写成 `cpu::add(..., out);`
  - 不负责扩展成通用 memory SSA 物化框架
- `include/cpu` 的职责：
  - 只负责把 CPU 公开接口契约写死
  - 不负责 DSL / IR lowering
- expectation 的职责：
  - 只在 `spec + 实现 + 测试` 成功口径都稳定后切换
  - 不得提前把失败 expectation 改成中间态成功 expectation

## 计划任务

### `S1`

- `任务类型`：`实现 nn.add CPU 标量接口说明功能`
- `目标`：在 [`spec/include/cpu/cpu.md`](../../spec/include/cpu/cpu.md) 明确 `nn.add` CPU 终点所依赖的标量接口契约，尤其是 `memory + symbol.int` 到 CPU 标量形态的公开口径。
- `任务示例`：
  - `S1 任务：仅修改 spec/include/cpu/cpu.md，在 cpu::add 相关小节补齐 memory + const(i32) 与 memory + symbol.int 的公开合同。`
  - `文档里应出现接近以下示例：void add(const Memory<int32_t>& lhs, long long bias, Memory<int32_t>& out) { cpu::add(lhs, bias, out); }`
  - `文档里不得出现“标量类型由实现决定”“mixed add 标量侧类型自适应”这类留白表述。`
- `边界`：
  - 只改 [`spec/include/cpu/cpu.md`](../../spec/include/cpu/cpu.md)
  - 不改 [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md)
  - 不改 [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
  - 不改实现、测试、expectation
- `注意事项`：
  - 必须明确 `memory + const(i32)` 的目标调用形态
  - 必须明确 `memory + symbol.int` 的目标调用形态
  - 不能写成“标量类型由实现决定”
  - 不能顺手把 `f16/f32` mixed scalar 也冻进去
- `依赖`：`无`
- `可改文件`：[`spec/include/cpu/cpu.md`](../../spec/include/cpu/cpu.md)
- `下游需要覆盖层`：
  - `include`
  - `emit_c`
  - `gen_kernel`
  - `expectation`
- `验证命令`：
  - `rg -n "cpu::add\\(|symbol.int|long long|memory \\+ const|memory \\+ symbol" spec/include/cpu/cpu.md`
- `验收标准`：
  - `test_cpu_nn_add_scalar_rhs_success`：输入 `lhs=[1,2,3,4]`、`rhs_scalar=3`，预期 `out=[4,5,6,7]`。
  - `test_cpu_nn_add_scalar_lhs_success`：输入 `lhs_scalar=2`、`rhs=[5,6,7,8]`，预期 `out=[7,8,9,10]`。
  - `test_cpu_nn_add_scalar_rhs_accepts_long_long`：输入 `lhs=[1,2,3,4]`、`bias=7LL`，预期编译成功并运行得到 `out=[8,9,10,11]`。

### `S2`

- `任务类型`：`实现 nn.add 节点级 CPU 发射说明功能`
- `目标`：在 [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md) 明确 `nn.add` 的节点级 CPU 发射规则。
- `任务示例`：
  - `S2 任务：仅修改 spec/dsl/emit_c.md，在 target=cpu 条目下新增 nn.add 的节点级发射规则。`
  - `文档里应分别给出三条示例：cpu::add(lhs, rhs, out);、cpu::add(lhs, 1, out);、cpu::add(lhs, bias, out);`
  - `文档里必须明确：只有调用方已把 nn.add.result 绑定到 out 时，本层才生成上述语句；不能偷偷补一个临时 Memory v0 再 out = v0。`
- `边界`：
  - 只改 [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md)
  - 只定义节点级语句
  - 不定义函数级 direct-return 条件
  - 不定义临时 `Memory` 物化策略
- `注意事项`：
  - 必须分别写清 `memory + memory`、`memory + const(i32)`、`memory + symbol.int`
  - 必须明确本层成功语句长什么样
  - 必须明确未绑定目标 result 时本层不兜底生成临时 memory
  - 必须明确 `non-cpu target` 的失败边界
- `依赖`：`S1 已完成`
- `可改文件`：[`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md)
- `下游需要覆盖层`：
  - `emit_c`
  - `gen_kernel`
  - `expectation`
- `验证命令`：
  - `rg -n "nn.add|cpu::add|symbol.int|target=cpu|unsupported op" spec/dsl/emit_c.md`
- `验收标准`：
  - `test_emit_c_op_lowers_nn_add_memory_memory_to_cpu_add`：输入 `NnAddOp(memory, memory)`，且 `ctx` 已把 `result` 绑定为 `out`；预期输出精确等于 `cpu::add(lhs, rhs, out);`。
  - `test_emit_c_op_lowers_nn_add_memory_const_i32_to_cpu_add`：输入 `NnAddOp(memory, i32 const)`，且 `ctx` 已把 `result` 绑定为 `out`；预期输出精确等于 `cpu::add(lhs, 1, out);`。
  - `test_emit_c_op_lowers_nn_add_memory_symbol_to_cpu_add`：输入 `NnAddOp(memory, !symbol.int)`，且 `ctx` 已把 `result` 绑定为 `out`；预期输出精确等于 `cpu::add(lhs, bias, out);`。
  - `test_emit_c_op_rejects_nn_add_without_prebound_result_target`：输入合法 `NnAddOp`，但不预绑定 result；预期报错 `EmitCError`，错误消息包含 `target=cpu: nn.add: unsupported op`。
  - `test_emit_c_op_rejects_nn_add_on_non_cpu`：输入合法 `NnAddOp`，`EmitCContext(target="npu_demo")`；预期报错 `EmitCError`，错误消息包含 `target=npu_demo: nn.add: unsupported op`。

### `S3`

- `任务类型`：`实现 direct-return nn.add 函数级说明功能`
- `目标`：在 [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md) 明确 direct-return `nn.add -> cpu::add(..., out)` 的函数级合同。
- `任务示例`：
  - `S3 任务：仅修改 spec/dsl/gen_kernel.md，在 Memory 返回值小节补一段 direct-return nn.add 的专门规则。`
  - `文档里应给出接近以下目标源码：void add(const Memory<int32_t>& lhs, const Memory<int32_t>& rhs, Memory<int32_t>& out) { cpu::add(lhs, rhs, out); }`
  - `文档里必须同时写反例：若 nn.add.result 有多个 use，则当前仍报 EmitCError target=cpu: nn.add: unsupported op，而不是退化为 out = tmp。`
- `边界`：
  - 只改 [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
  - 只覆盖 `func.return` 唯一使用 `nn.add.result` 的场景
  - 不覆盖多 use
  - 不覆盖 generic `out = tmp`
- `注意事项`：
  - 必须明确签名形态
  - 必须明确函数体形态
  - 必须明确“唯一 use 为 `func.return`”是硬门禁
  - 必须明确非特化路径仍是失败，不是 silent fallback
- `依赖`：`S1、S2 已完成`
- `可改文件`：[`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
- `下游需要覆盖层`：
  - `gen_kernel`
  - `expectation`
- `验证命令`：
  - `rg -n "nn.add|cpu::add\\(.*out\\)|unique-use|func.return|unsupported op" spec/dsl/gen_kernel.md`
- `验收标准`：
  - `test_gen_kernel_supports_direct_return_nn_add_memory_memory_on_cpu`：输入 `return lhs + rhs`；预期签名包含 `Memory<int32_t>& out`，函数体包含 `cpu::add(lhs, rhs, out);`。
  - `test_gen_kernel_supports_direct_return_nn_add_memory_const_on_cpu`：输入 `return lhs + 1`；预期函数体包含 `cpu::add(lhs, 1, out);`。
  - `test_gen_kernel_supports_direct_return_nn_add_memory_symbol_on_cpu`：输入 `return lhs + bias`；预期签名包含 `long long bias`，函数体包含 `cpu::add(lhs, bias, out);`。
  - `test_gen_kernel_rejects_nn_add_specialization_on_multi_use`：输入 `nn.add.result` 有多个 use；预期固定报错 `EmitCError target=cpu: nn.add: unsupported op`。

## 推荐收口顺序

1. 先完成 [`spec/include/cpu/cpu.md`](../../spec/include/cpu/cpu.md) 的文档收口。
2. 再完成 [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md) 的文档收口。
3. 再完成 [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md) 的文档收口。
4. 然后实现 [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py) 与 [`test/dsl/test_emit_c.py`](../../test/dsl/test_emit_c.py)。
5. 再实现 [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py) 与 [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)。
6. 仅在前述 `spec + 实现 + 测试` 全部稳定后，改写 [`expectation/dsl/emit_c/cpu/add.py`](../../expectation/dsl/emit_c/cpu/add.py) 为成功口径。
7. 最后做审查、复审与合并。

## 统一验收口径

### 前半链路不得回退

- `test_add_op_accepts_memory_const_rhs`
- `test_add_op_accepts_memory_symbol_rhs`
- `test_emit_mlir_lower_expr_branches`
- `test_build_func_op_lowers_nn_add_memory_const_without_dma_cast`
- `test_build_func_op_lowers_nn_add_memory_symbol_with_scalar_promotion`

这些测试继续通过，只证明前半链路仍在，不代表 CPU E2E 已完成。

### 节点级 CPU 发射必须新增

- `test_emit_c_op_lowers_nn_add_memory_memory_to_cpu_add`
- `test_emit_c_op_lowers_nn_add_memory_const_i32_to_cpu_add`
- `test_emit_c_op_lowers_nn_add_memory_symbol_to_cpu_add`

### 函数级 CPU E2E 必须新增

- `test_gen_kernel_supports_direct_return_nn_add_memory_memory_on_cpu`
- `test_gen_kernel_supports_direct_return_nn_add_memory_const_on_cpu`
- `test_gen_kernel_supports_direct_return_nn_add_memory_symbol_on_cpu`
- `test_gen_kernel_rejects_nn_add_specialization_on_multi_use`

### 编译执行 gate

- `test_gen_kernel_supports_direct_return_nn_add_memory_memory_on_cpu`：
  - 生成源码后必须能连同 [`include/cpu/Nn.h`](../../include/cpu/Nn.h) 编译并运行。
  - 输入 `lhs=[[1,2,3],[4,5,6]]`、`rhs=[[10,20,30],[40,50,60]]`
  - 预期 `out=[[11,22,33],[44,55,66]]`
- `test_gen_kernel_supports_direct_return_nn_add_memory_const_on_cpu`：
  - 输入 `lhs=[[1,2,3],[4,5,6]]`、`const=1`
  - 预期 `out=[[2,3,4],[5,6,7]]`
- `test_gen_kernel_supports_direct_return_nn_add_memory_symbol_on_cpu`：
  - 输入 `lhs=[[1,2,3],[4,5,6]]`、`bias=7`
  - 预期 `out=[[8,9,10],[11,12,13]]`

### 机械 grep gate

生成源码必须命中：

```text
Memory<...>& out
cpu::add(lhs, rhs, out);
cpu::add(lhs, 1, out);
cpu::add(lhs, bias, out);
```

生成源码不得命中：

```text
nn.add
kernel.add
out = v
out = arg
return v
return arg
```

### expectation gate

- [`expectation/dsl/emit_c/cpu/add.py`](../../expectation/dsl/emit_c/cpu/add.py) 必须覆盖：
  - `memory + memory`
  - `memory + const`
  - `memory + symbol`
- `PYTHONPATH=. python expectation/dsl/emit_c/cpu/add.py`
  - 预期退出码 `0`
- expectation 中不允许再保留以下旧断言：
  - `memory + memory` 在 `emit_c` 应失败
  - `memory + const` 在 `build_func_op` 应失败
  - `memory + symbol` 在 `build_func_op` 应失败

### 仍需保留但不得冒充终态的 gate

- `PYTHONPATH=. python expectation/pass/lowing/nn_to_kernel/add.py`
- `pytest -q test/include/cpu/test_nn.py -k 'test_cpu_nn_add_scalar_rhs_success or test_cpu_nn_add_scalar_lhs_success'`

这两类 gate 只能证明链路局部仍在，不能单独作为 direct-return `nn.add` CPU E2E 完成的证据。

## 当前验收结论

- 通过。
- 当前已符合预期的部分：
  - `PYTHONPATH=. python expectation/pass/lowing/nn_to_kernel/add.py` 通过。
  - `pytest -q test/dsl/test_emit_c.py -k 'test_emit_c_op_lowers_prebound_nn_add_variants_to_cpu_add or test_emit_c_op_keeps_nn_add_unsupported_without_prebound_result_or_on_non_cpu'` 通过。
  - [`test/dsl/test_emit_c.py`](../../test/dsl/test_emit_c.py) 已锁定 `nn.add` 节点级 CPU 发射三条成功路径：
    - `memory + memory -> cpu::add(lhs, rhs, out);`
    - `memory + const(i32) -> cpu::add(lhs, 1, out);`
    - `memory + symbol.int -> cpu::add(lhs, bias, out);`
  - [`test/dsl/test_emit_c.py`](../../test/dsl/test_emit_c.py) 已锁定以下拒绝边界：
    - 未预绑定 `result`
    - `const(i32) + memory`
    - `symbol.int + memory`
    - `target != cpu`
  - `PYTHONPATH=. python expectation/dsl/emit_c/cpu/add.py` 通过；[`expectation/dsl/emit_c/cpu/add.py`](../../expectation/dsl/emit_c/cpu/add.py) 已切到成功口径。
  - `pytest -q test/dsl/test_gen_kernel.py -k 'test_gen_kernel_compiles_and_runs_direct_return_nn_add_variants_on_cpu or test_gen_kernel_supports_direct_return_nn_add_memory_memory_on_cpu or test_gen_kernel_supports_direct_return_nn_add_memory_const_on_cpu or test_gen_kernel_supports_direct_return_nn_add_memory_symbol_on_cpu or test_gen_kernel_rejects_nn_add_specialization_on_multi_use'` 通过。
  - [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py) 已补 direct-return `nn.add` 的 compile/run gate，且 `memory + symbol.int` 已能连同 [`include/cpu/Nn.h`](../../include/cpu/Nn.h) 编译运行。
  - `pytest -q test/include/cpu/test_nn.py -k 'test_cpu_nn_add_scalar_rhs_success or test_cpu_nn_add_scalar_rhs_long_long_success or test_cpu_nn_add_scalar_lhs_success'` 通过。

## 建议新增任务

- 当前无新增任务。

## 当前最直接的下一步

- 当前无新增任务；等待管理员按“已通过”口径继续后续链路收口。
