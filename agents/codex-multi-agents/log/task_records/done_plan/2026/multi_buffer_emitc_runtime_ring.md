# multi buffer emitc runtime ring 计划书 Draft 7

## 文档信息

- 计划用途：为 `npu_demo` 侧的 `dma.make_ring` / `dma.current_ring` / `dma.advance_ring` 建立真实 runtime ring 表达；让 EmitC 不再把 ring 发射成固定 offset 0 的 serial view；删除 IR 层 `DmaMakeRingOp.shape_bytes` operand；把 `multi-buffer` 默认 stage 收口为 2，并在 demo pipeline 中通过 target auto 计算真实 ring num；补齐相关 `expectation` 合同资产。
- 当前状态：Draft 7，已吸收用户对 API、`shape_bytes`、默认 stage、`bpudemo pipeline` 等同 `npu-demo-lowering`、include 完整签名与 `DmaRing` 构造语义的确认；Draft 5 两路 subagent strict review 和守护最终检验已通过，并已下发唯一计划级 execute。Draft 6 修正 `expectation.dsl.emit_c.npu_demo.dma` 目录级聚合入口错误；Draft 7 按用户最新口径将 `expectation.pass.pipeline` 及其 leaf 全部移出本计划 expectation 验收与授权范围，pipeline 接入只由 spec 与 pytest 验收。Draft 7 strict review 与守护复验通过前暂停 execute。
- 用户确认来源：
  - 2026-06-07 用户提出：“我希望在pass 添加 multi bufferpass”，“讨论一下方案，以及 emitc 的方案”，“make_ring/current/advance，这个能不能变成 dma 重解释。这个跟 num 大小有关”。
  - 2026-06-07 用户选择 runtime helper 方案：“那就C 方案吧。你列一些 api，我来修改”。
  - 2026-06-07 用户追问并认可：`shape_bytes` 不进入 runtime 公开 API，`current` / `advance` 作为 ring 结构体成员函数更合适。
  - 2026-06-07 用户要求：“按照这个出一个计划书。重点是 1. 讨论之后我来决策。2 需要补一些相关的expatation”。
  - 2026-06-07 用户确认：“DmaMakeRingOp.shape_bytes 也不保留，3 默认是2，但是在bpudemo pipeline 中是 auto”。
  - 2026-06-07 用户确认：“bpudemo pipeline 就是 npu demo”。
  - 2026-06-07 用户对计划负责人列出的 include 完整签名与构造语义确认：“2 是的”。
- 计划文件位置：`ARCHITECTURE/plan/multi_buffer_emitc_runtime_ring.md`。
- 与现有任务关系：
  - 当前已有独立执行任务 `T-20260607-3318f2e2 / pass-directory-layout-refactor`，worktree 为 `/home/lfr/kernelcode_generate/wt-20260607-pass-directory-layout-refactor`。
  - 本计划不得塞入该已下发执行任务，不得让执行人在目录重构任务中顺带实现 runtime ring API、pipeline 接入或新增 expectation。
  - 本计划执行前必须以届时最新主线为准重新核对 `MultiBufferPass` canonical import path；若 `pass-directory-layout-refactor` 已合并，则使用 `kernel_gen.passes.memory.multi_buffer` 与 `spec/pass/memory/multi_buffer.md`；若未合并，则仍按当前 main 的 `kernel_gen.passes.multi_buffer` 与 `spec/pass/multi_buffer.md` 记录并等待管理员协调。

## 目标 spec

- `spec/include/api/Dma.md`
- `spec/include/npu_demo/npu_demo.md`
- `spec/dsl/gen_kernel/emit/npu_demo/dma/__init__.md`
- `spec/pass/multi_buffer.md` 或目录重构合并后的 `spec/pass/memory/multi_buffer.md`
- `spec/pass/registry.md`
- `spec/pass/pipeline/npu_demo_lowering.md`
- `spec/dialect/dma.md`

## 候选公开 API

本节是用户已确认的目标 API。Draft 5 已完成 subagent strict review 与守护最终检验；Draft 6 不调整本节 API。

### include public API

```cpp
namespace npu_demo {

template <MemorySpace Space, typename SlotT, typename BackingT>
class DmaRing {
public:
    Memory<Space, SlotT> current() const;
    Memory<Space, SlotT> advance();
};

template <typename SlotT, MemorySpace Space, typename BackingT>
DmaRing<Space, SlotT, BackingT> make_ring(
    Memory<Space, BackingT>& backing,
    S_INT num,
    S_INT offset_bytes,
    std::initializer_list<long long> shape,
    std::initializer_list<long long> stride,
    MemoryFormat format = MemoryFormat::Norm);

}  // namespace npu_demo
```

- `shape_bytes` 不进入 include public API；runtime 由 `shape + stride + sizeof(SlotT)` 计算 slot span bytes。
- `offset_bytes` 保留；它表示相邻 ring stage 的实际字节间距，可以大于 slot span bytes。
- `current()` 返回当前 cursor slot，不修改 cursor。
- `advance()` 先执行 `cursor = (cursor + 1) % num`，再返回新 cursor slot。
- `DmaRing` 公开合同只承诺可由 `make_ring(...)` 返回值创建并调用 `current()` / `advance()`；不提供 public default constructor。
- `DmaRing` copy / move constructor 与 copy / move assignment 不作为 public stable API 承诺；实现可按 C++ 编译和生命周期需要 `delete` 或 `default`，但 spec、API 列表、expectation 与测试不得依赖这些特殊成员。
- `cursor`、`num`、`offset_bytes` 是 runtime ring 内部状态，不暴露 public accessor；测试和 expectation 通过返回 slot 的数据指针 / 写读结果验证行为。
- `BackingT` 推荐限制为 byte-sized 类型，至少要求 `sizeof(BackingT) == 1`；否则按字节偏移切 slot 容易和 typed element offset 混淆。
- runtime slot view 必须做 byte pointer arithmetic，不得用当前 `Memory::view<T>` 承接非零 byte offset，因为 `Memory::view<T>` 的 offset 是 source element offset，不是 byte offset。

### EmitC 映射

```cpp
auto lhs_ring = npu_demo::make_ring<float>(
    lhs_backing,
    lhs_num,
    lhs_offset_bytes,
    {m, k},
    {k, 1});

Memory<TLM1, float> lhs_cur = lhs_ring.current();
Memory<TLM1, float> lhs_next = lhs_ring.advance();
```

- `dma.make_ring` 必须发射 ring 变量绑定，不再发射空字符串。
- `dma.current_ring` 必须发射成员调用 `.current()`。
- `dma.advance_ring` 必须发射成员调用 `.advance()`；若 IR result 未使用，仍可发射调用语句以保留 cursor side effect。
- EmitC 不暴露 `shape_bytes` 参数；IR 层也删除 `shape_bytes` operand，slot span bytes 统一由 ring slot type 的 `shape/stride/element type` 推导。

### Python / IR API

本轮修改以下公开 IR API：

- `class DmaMakeRingOp(memory: SSAValue | Operation, num: SSAValue | Operation, offset: SSAValue | Operation, result_type: DmaRingType)`
- `class DmaCurrentRingOp(ring: SSAValue | Operation, result_type: NnMemoryType | None = None)`
- `class DmaAdvanceRingOp(ring: SSAValue | Operation, result_type: NnMemoryType | None = None)`
- `class MultiBufferPass(memory_stage: int = 2, fold: bool = True, target: str | None = None)`

- `DmaMakeRingOp.shape_bytes` operand 删除；verifier 改为由 result `DmaRingType.slot_type` 推导 slot span bytes，并校验静态可判定场景中的 `offset >= slot_span_bytes`。
- `MultiBufferPass` direct constructor 与 `from_options({})` 默认 stage 均改为 2。
- 不新增 `memory-stage=auto` pass option；auto 只通过 pipeline 传入非空 `target` 触发现有 target-registry capacity 计算。
- 用户已确认 `bpudemo pipeline` 指 `npu-demo-lowering`；本计划只更新 `npu-demo-lowering`，不新增也不条件纳入单独 `bpudemo` / `bpu_demo` pipeline。

## 当前基线

- `kernel_gen/passes/multi_buffer.py` 当前已经存在 `MultiBufferPass(memory_stage: int = 3, fold: bool = True, target: str | None = None)`，可把 matmul lhs/rhs staging alloc/free 改写为 `dma.make_ring/current_ring/advance_ring`；本计划要把默认值改为 2，并同步 `from_options({})` 默认值、文件级 API 列表、`spec/pass/multi_buffer.md` 与 pass pytest。
- `spec/pass/multi_buffer.md` 当前声明 `npu-demo-lowering` 固定调用 `MultiBufferPass(memory_stage=3)`，但 `spec/pass/pipeline/npu_demo_lowering.md` 当前又明确“不接入 `multi-buffer`”；这是当前计划必须收口的公开合同冲突。Draft 4 按用户决策改为默认 stage 2，`npu-demo-lowering` 传 target 走 auto。
- `kernel_gen/pipeline/npu_demo_lowering.py` 当前 pass order 不包含 `MultiBufferPass`；`test/passes/pipeline/test_npu_demo_lowering.py` 当前按“不包含 multi-buffer”基线锁定。当前主仓不存在 `expectation/pass/pipeline` 合同资产，本计划不新增 pipeline expectation。
- `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py` 当前：
  - `dma.make_ring` 发射为空字符串。
  - `dma.current_ring` / `dma.advance_ring` 发射为 backing memory 的固定 `{0}` offset typed view / reshape。
  - 当前行为忽略 cursor 和 `num`，只能作为可编译 serial fallback，不能表达真实 multi-buffer。
- `include/api/Dma.h` / `include/npu_demo/Dma.h` 当前没有 `DmaRing` / `make_ring` public runtime API。
- `include/npu_demo/Memory.h` 当前 `Memory::view<ViewT>(...)` 的 offset 按 source element 线性偏移处理；对 i8 backing 切 `float` slot 的非零 byte offset 不能直接用 `.view<float>({offset_bytes}, ...)`。
- 已有相关 expectation：
  - `expectation/dialect/dma/operation/make_ring.py`
  - `expectation/dialect/dma/operation/current_ring.py`
  - `expectation/dialect/dma/operation/advance_ring.py`
  - `expectation/pass/multi_buffer/matmul_ring_memory_stage.py`
  - `expectation/pass/multi_buffer/matmul_ring_target.py`
- 当前缺口：
  - 没有 `expectation/dsl/emit_c/npu_demo/dma/ring.py` 锁定 npu_demo EmitC ring 源码。
  - 没有 include/runtime 层 expectation 锁定 `DmaRing` cursor、byte offset、成员函数与边界错误。
  - 现有 dialect / pass expectation 仍锁定 `dma.make_ring(memory, num, offset, shape_bytes)` 旧签名，需要随用户确认的 breaking change 一起更新。
  - 若接入 `npu-demo-lowering` 默认链路，需要更新 pipeline spec 与 pytest，避免旧“不包含 multi-buffer”测试合同继续阻断；`expectation.pass.pipeline` 不作为本计划验收入口。
  - `kernel_gen/dialect/dma/__init__.py` 与 `kernel_gen/dialect/dma/operation/__init__.py` 文件级 API 列表当前仍会受到 `DmaMakeRingOp` 签名删除影响，必须随 S1 同步清扫。

## 方案比较与选型

### 方案 A：保持当前 serial view no-op

- 做法：`make_ring` 继续空发射，`current/advance` 继续返回 backing offset 0 的 view。
- 优点：改动小，现有测试冲击小。
- 问题：`num` 完全无效，`advance` 没有 cursor 语义，无法支撑真实 multi-buffer。
- 结论：不采用。

### 方案 B：EmitC 直接把 ring 降成 `dma.reinterpret`

- 做法：由 EmitC 或 IR lowering 把 `current/advance` 展开为 `slot_idx = iv % num`、`slot_offset = slot_idx * offset_bytes`，再用 byte reinterpret 形成 slot memory。
- 优点：没有 C++ runtime ring 状态对象，IR 语义更显式。
- 问题：需要稳定 loop IV 到 ring op 的关联、`symbol.mod` / C++ modulo 映射、advance result 与 cursor side effect 的一致性；当前 IR 的 `dma.advance_ring` 是有副作用 op，不只是纯 reinterpret。
- 结论：本计划不采用，可作为后续 IR canonicalization 方向。

### 方案 C：runtime `DmaRing` public API + EmitC 成员调用

- 做法：在 include public API 新增 `DmaRing` 与 `npu_demo::make_ring(...)`；EmitC 把 ring op 发射成 runtime ring object 和 `.current()` / `.advance()` 成员调用。
- 优点：真实表达 `num` 和 cursor，EmitC 映射清晰，不要求本轮新增 modulo IR 或重写 ring dialect。
- 风险：新增 include public API，必须补 spec、API 列表、pytest、expectation，并获得用户确认。
- 本计划采用：方案 C；IR 与 runtime API 均不保留 `shape_bytes`，slot span bytes 从 result slot type 推导。

## 完成态定义

- include 层：
  - `include/api/Dma.h` 声明 `DmaRing` 和 `npu_demo::make_ring` public API。
  - `include/npu_demo/Dma.h` 实现 runtime ring descriptor，不复制 backing memory。
  - `include/npu_demo/npu_demo.h` 文件级 API 列表同步新增 ring API。
  - 非法 `num <= 0`、`offset_bytes <= 0`、slot span 超出 offset、`num * offset_bytes` 超出 backing 可用范围时失败；本计划不冻结 include runtime exact error text，pytest / expectation 只验证失败类别与行为，不匹配具体文本。
- EmitC 层：
  - `dma.make_ring` 发射 ring object 变量绑定。
  - `dma.current_ring` / `dma.advance_ring` 发射成员调用，不再生成固定 offset 0 的 `view`。
  - 生成源码不得出现 `dma.make_ring` / `dma.current_ring` / `dma.advance_ring` IR 名称。
- Pass / pipeline 层：
  - `MultiBufferPass` 构造签名保持同名参数，但默认值从 `memory_stage=3` 改为 `memory_stage=2`。
  - `from_options({})` 默认 stage 同步改为 2；`memory-stage=<positive-int>` 仍可覆盖固定 stage。
  - `npu-demo-lowering` 在 `kernel-decompose -> memory-plan -> symbol-hoist-pipeline -> cse -> canonicalize` 之后、`producer-consumer-analysis` 之前插入 `MultiBufferPass(memory_stage=2, target=<pipeline target>)`。
  - 用户所说 `bpudemo pipeline` 按 `npu-demo-lowering` 处理；本计划不创建、不修改单独 `bpudemo` / `bpu_demo` pipeline。
- expectation：
  - 新增 emitc ring expectation，锁定 `make_ring(...).current().advance()` 生成源码。
  - 新增 include/runtime ring expectation 或等价合同入口，锁定 cursor 轮转与 byte offset。
  - 更新 dialect / pass expectation，使其不再出现 `shape_bytes` operand。
  - 更新 pipeline spec 与 pytest，明确新 pass order、默认 stage 2 与 pipeline target auto 口径，旧“不包含 multi-buffer”断言退出；不新增 `expectation.pass.pipeline` 合同资产。

## 计划级任务

- 计划级任务目标：为 npu_demo 添加 runtime `DmaRing` public API，删除 `DmaMakeRingOp.shape_bytes` operand，把 `MultiBufferPass` 默认 stage 改为 2，重写 EmitC ring 发射为真实 cursor ring 成员调用，将 demo pipeline 中的 `multi-buffer` 阶段按 target auto 口径接入，并补齐 pytest 与 expectation 合同验收。
- 任务类型：`execute`。
- 固定流转：`execute -> review -> archive_acceptance / 计划书入档验收 -> merge/归档`。
- 当前下发状态：Draft 5 已吸收用户决策、完成 strict review 收敛与守护最终检验，并已创建唯一计划级 execute；Draft 7 修订 strict review 与守护复验通过前不得恢复 execute。

| 计划任务 | 任务类型 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `multi-buffer-emitc-runtime-ring` | `execute` | 管理员确认后创建的新独立 worktree | `agents/codex-multi-agents/log/task_records/2026/<week>/YYYYMMDD-multi-buffer-emitc-runtime-ring.md` |

## 计划内小任务

### S1：收口公开 API spec 与 dialect ring 签名

- 为什么做：runtime ring 和 IR ring 都是公开 API，用户已确认 `shape_bytes` 不保留，必须先在 spec、API 列表和 dialect 合同中冻结签名。
- 做什么：更新 `spec/include/api/Dma.md`、`include/api/Dma.h` 文件级 API 列表与声明；同步 `spec/include/npu_demo/npu_demo.md` / `include/npu_demo/npu_demo.h` API 索引；更新 `spec/dialect/dma.md`、`kernel_gen/dialect/dma/operation/ring.py`、`kernel_gen/dialect/dma/__init__.py`、`kernel_gen/dialect/dma/operation/__init__.py` 与 `test/dialect/dma/test_operation_ring.py` 的 `DmaMakeRingOp` 签名。
- 不做什么：不新增 free function `current_ring(...)` / `advance_ring(...)` 作为 public API；不保留旧 `shape_bytes` compat overload；不新增 `memory-stage=auto` pass option。
- 怎么验收：运行 include / dialect API pytest；核对 API 列表紧跟功能说明；文本确认 C++ 与 IR API 都没有 `shape_bytes` 参数。
- 卡住问谁：公开 API 签名、错误语义或是否保留旧 compat overload 卡住时问用户。

详细执行：
1. 在 `spec/include/api/Dma.md` 增补 `DmaRing` class 与 `make_ring` API 详细说明。
2. 在 `include/api/Dma.h` 加声明并更新文件级 API 列表。
3. 在 `spec/include/npu_demo/npu_demo.md` 与 `include/npu_demo/npu_demo.h` 聚合 API 索引中加入 ring API。
4. 在 `spec/dialect/dma.md` 把 `DmaMakeRingOp` 公开签名改为 `(memory, num, offset, result_type)`。
5. 在 `kernel_gen/dialect/dma/operation/ring.py` 删除 `shape_bytes` operand、constructor 参数、verifier 对该 operand 的依赖；静态 slot span bytes 从 result slot type 推导。
6. 更新 `test/dialect/dma/test_operation_ring.py`，覆盖新签名 parse/verify、`offset >= slot_span_bytes` 静态失败、动态 offset 正例。
7. 更新 `kernel_gen/dialect/dma/__init__.py` 与 `kernel_gen/dialect/dma/operation/__init__.py` 文件级 API 列表，删除旧 `shape_bytes` 签名。
8. 错误语义只冻结失败类别：invalid num、invalid offset、invalid slot layout、backing storage too small；include runtime exact error text 不作为本计划公开合同。
9. 自检跨文件 private API：不得让测试或实现直连非公开 helper。
10. 增加文本清扫：`rg -n "shape_bytes|DmaMakeRingOp\\([^\\n]*shape_bytes" kernel_gen/dialect/dma spec/dialect/dma.md test/dialect/dma expectation/dialect/dma/operation/make_ring.py` 不得命中旧签名。

验收：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_dma.py test/include/npu_demo/test_public_namespace.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/dma/test_operation_ring.py test/dialect/dma/test_type.py
```

合同验收：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.include.npu_demo.dma_ring
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dialect.dma.operation.make_ring
```

### S2：实现 runtime `DmaRing`

- 为什么做：EmitC 需要一个真实 cursor-bearing runtime 对象表达 `num` 与 `advance`。
- 做什么：在 `include/npu_demo/Dma.h` 实现 `DmaRing` 与 `make_ring`；slot view 使用 byte pointer arithmetic。
- 不做什么：不改 `Memory::view` 公开语义；不把 ring 做成数据复制；不引入异步 DMA / barrier / sign / wait。
- 怎么验收：编译/运行 include runtime 测试，覆盖 `current -> advance -> current` 的 cursor 轮转和越界错误。
- 卡住问谁：runtime 错误文本或 backing size 无法从现有 `Memory` public API 推导时问用户 / 架构师。

详细执行：
1. 在 `include/npu_demo/Dma.h` 增加当前文件内必要 helper；helper 不进入 public API。
2. 同步 `include/npu_demo/Dma.h` 文件级 `API 列表`，列出 `DmaRing.current()`、`DmaRing.advance()` 和 `npu_demo::make_ring(...)`，不得列出 `cursor()` / `num()` / `offset_bytes()` accessor 或 default/copy/move/assignment 特殊成员。
3. `make_ring` 校验 rank、shape、stride、num、offset bytes。
4. 用 `shape + stride` 计算 slot span bytes，支持 padded stride；不得只用 `product(shape)`。
5. 用 `reinterpret_cast<unsigned char*>(backing.data()) + cursor * offset_bytes` 定位 slot。
6. 构造 `Memory<Space, SlotT>(slot_ptr, shape, stride, rank, format)` 返回 slot view。
7. 保证 `advance()` 修改 ring 内部 cursor，并返回推进后的 slot。

验收：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_dma.py
```

合同验收：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.include.npu_demo.dma_ring
```

### S3：重写 npu_demo EmitC ring 发射

- 为什么做：当前 EmitC ring 忽略 `num` 和 cursor，不能支撑 multi-buffer。
- 做什么：更新 `spec/dsl/gen_kernel/emit/npu_demo/dma/__init__.md`，把 `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py` 改为发射 `npu_demo::make_ring<SlotT>(...)`、`.current()` 和 `.advance()`。
- 不做什么：不新增跨文件公开 helper；不使用 `getattr/hasattr(ctx, ...)` 能力探测；不保留旧 `shape_bytes` operand 兼容分支。
- 怎么验收：运行 EmitC pytest 和新增 ring expectation，确认源码包含 `make_ring<...>`、`.current()`、`.advance()`，且不再出现固定 offset 0 view 作为 ring current/advance。
- 卡住问谁：EmitC 命名绑定或 result unused 的 side effect 发射口径卡住时问架构师；公开 API 文本卡住时问用户。

详细执行：
1. `dma.make_ring` 使用 `ctx.create_or_get_name(op.result)` 创建 ring 变量名。
2. 从 `DmaRingType.slot_type` 或 current/advance result type 提取 `SlotT`、space、shape、stride、format。
3. 使用现有公开 emit 入口发射 `memory`、`num`、`offset` operands；不得再读取 `shape_bytes` operand。
4. `dma.current_ring` 发射 `result_cpp_type result = ring.current();`。
5. `dma.advance_ring` 发射 `result_cpp_type result = ring.advance();`；如果 result 无 SSA 名称消费，仍保留语句，避免丢 side effect。
6. 同步 `spec/dsl/gen_kernel/emit/npu_demo/dma/__init__.md`，删除固定 `{0}` ring view、serial no-op ring 和 runtime helper 不在范围的旧口径。
7. 同步 `kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py` 文件级说明和函数注释，删除旧 serial fallback 描述。
8. 保持错误语义：ring source 不是 `dma.make_ring` 时失败；slot result 不是 `nn.memory` 时失败；匿名 `?` shape 不得直接进入 generated C++。
9. 增加文本清扫：`rg -n "fixed \\{0\\}|固定 \\{0\\}|serial no-op|runtime helper 不在范围|shape_bytes" spec/dsl/gen_kernel/emit/npu_demo/dma/__init__.md kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/ring.py` 不得命中旧口径。

验收：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_package.py
```

合同验收：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma.ring
```

- `expectation.dsl.emit_c.npu_demo.dma` 目录级聚合不列为本计划必过入口；该聚合会运行 alloc/broadcast/copy/deslice/fill/load/slice/store/transpose 等未授权旧 expectation，超出本计划当前 D4 授权范围。

### S4：按 target auto 口径接入 npu-demo pipeline

- 为什么做：用户希望在 pass 流程中添加 `multi-buffer`，并确认默认 stage 为 2、demo pipeline 中按 auto 计算 ring num。
- 做什么：更新 `MultiBufferPass` spec、实现、pytest、registry spec、registry option 测试、pipeline spec、pipeline 实现、pipeline pytest 和 expectation；用户已确认 `bpudemo pipeline` 就是 `npu demo`，因此只接入当前存在的 `npu-demo-lowering`。
- 不做什么：不新增 pipeline option；不新增 `memory-stage=auto` 字符串 option；不把 `multi-buffer` 放到 `memory-pool` 之后。
- 怎么验收：pipeline pass order pytest 与 pipeline spec 和确认后的顺序一致，且 pipeline 中 `MultiBufferPass(memory_stage=2, target=<pipeline target>)` 触发 target auto。
- 卡住问谁：若 `npu-demo-lowering` target registry 缺少 capacity，或 pipeline target 无法传入 `MultiBufferPass`，问用户 / 架构师。

推荐插入点：

```text
... KernelAggregatePass(matmul_acc=True)
-> KernelDecomposePass
-> MemoryPlanPass(insert_free=True, reuse=True, fold=False, auto_pad=True)
-> SymbolHoistPipelinePass
-> CommonSubexpressionElimination
-> CanonicalizePass
-> MultiBufferPass(memory_stage=2, target=<pipeline target>)
-> ProducerConsumerAnalysisPass
-> MemoryPoolPass(rewrite=True, alignment=1024)
...
```

执行步骤：
1. 更新 `spec/pass/multi_buffer.md` 或目录重构后的 `spec/pass/memory/multi_buffer.md`，把 API 列表、option 默认值、测试矩阵和示例从默认 3 改为默认 2。
2. 更新 `spec/pass/registry.md` 中 `multi-buffer` / `memory-stage` 默认值、示例和 target auto 口径。
3. 更新 `kernel_gen/passes/multi_buffer.py` 或目录重构后的 `kernel_gen/passes/memory/multi_buffer.py`：文件级 API 列表、class docstring、`__init__(memory_stage: int = 2, ...)`、`from_options({})` 默认值、示例全部同步。
4. 更新 `kernel_gen/passes/__init__.py` 或目录重构后的 package root/API 列表文件，删除 `MultiBufferPass(memory_stage=3)` 旧公开索引 / 示例。
5. 更新 `test/passes/test_multi_buffer.py` 或目录重构后的 `test/passes/memory/test_multi_buffer.py`，覆盖 direct constructor 默认值、`from_options({})` 默认值、`memory-stage=<positive-int>` 覆盖和 target auto 优先。
6. 更新 `test/passes/test_registry.py`，覆盖 registry 构造 `multi-buffer` 的默认 `memory_stage=2`、`fold` 通用 option 与 `memory-stage=<positive-int>` pass 专属 option 组合。
7. 更新 pipeline 实现导入路径和 pass order，把 `MultiBufferPass(memory_stage=2, target=<pipeline target>)` 插在推荐位置。
8. 更新 `spec/pass/pipeline/npu_demo_lowering.md` 和 `test/passes/pipeline/test_npu_demo_lowering.py`，删除旧“不包含 multi-buffer”断言；不新增或修改 `expectation/pass/pipeline`。
9. 增加文本清扫：`rg -n "memory_stage=3|memory_stage: int = 3|memory-stage.*default.*3" kernel_gen/passes spec/pass test/passes` 不得命中旧默认，历史基线说明除外。
10. 增加文本清扫：`rg -n "bpudemo|bpu_demo|test_bpudemo|expectation.pass.pipeline.bpudemo" spec kernel_gen test expectation` 不得命中本计划新增的单独 pipeline 接入痕迹；历史无关文本若命中，必须在任务记录中说明。

验收：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_multi_buffer.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py
```

若目录重构计划已合并，使用迁移后的测试路径：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py
```

合同验收：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer
```

### S5：补齐 expectation 合同资产

- 为什么做：用户明确要求补相关 expectation；runtime ring 与 EmitC ring 是新的合同面，不能只靠 pytest。
- 做什么：在用户授权范围内新增 / 更新 listed expectation；保持 expectation 与 diff 反推 pytest 分开。
- 不做什么：不借 expectation 反向放宽 spec；不修改无关 expectation；不运行全量 expectation 作为本计划默认必过。
- 怎么验收：新增 leaf expectation 单独通过；聚合入口只运行本计划相关聚合，避免把已知无关历史失败升级为阻断。
- 卡住问谁：任何 expectation 本体新增、重命名、删除或旧合同冲突问用户 / 架构师。

拟新增或更新：
- 新增 `expectation/dsl/emit_c/npu_demo/dma/ring.py`，锁定本计划新增 EmitC ring 合同；即使 `expectation.dsl.emit_c.npu_demo.dma.__main__` 可自动发现该 leaf，也不代表本计划要求运行目录级聚合入口。
- 新增 `expectation/include/npu_demo/dma_ring.py`，锁定 runtime `DmaRing` cursor 和 byte offset。
- 更新 `expectation/dialect/dma/operation/make_ring.py`，删除旧 `shape_bytes` operand 断言。
- 更新 `expectation/pass/multi_buffer/matmul_ring_memory_stage.py` 与 `expectation/pass/multi_buffer/matmul_ring_target.py`，删除旧 `shape_bytes` operand 断言，并锁定默认 stage 2。
- `expectation.pass.pipeline` 不作为本计划验收入口；当前主仓不存在 `expectation/pass/pipeline` 合同资产，本计划不新增该目录或 leaf。

合同验收：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma.ring
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.include.npu_demo.dma_ring
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dialect.dma.operation.make_ring
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer
```

### S6：计划级自检、review 与入档验收

- 为什么做：该计划同时改 include public API、EmitC、pipeline 和 expectation，必须按计划流程闭环。
- 做什么：执行人完成 diff 反推测试、合同验收、文本门禁和任务记录；review 检查公开 API、非公开 helper、expectation 授权与测试有效性；入档验收运行计划列为必过的 expectation。
- 不做什么：不直接修改 `TODO.md`；不在主仓根目录写常规日志；不把现有 active worktree 的无关现场纳入本计划。
- 怎么验收：所有计划列出的 pytest、expectation 和文本门禁通过，任务记录写清自检和 diff 反推测试。
- 卡住问谁：流程 / TODO 状态问管理员；守护最终检验和入档口径问架构师。

文本门禁：

```bash
git diff --check -- ARCHITECTURE/plan/multi_buffer_emitc_runtime_ring.md spec include kernel_gen test expectation
git status --short --untracked-files=all -- .skills agents/standard AGENTS.md TODO.md DONE.md plan/1.md ARCHITECTURE/plan/multi_buffer_emitc_runtime_ring.md
```

## 验收设计

### Diff 反推 pytest

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_dma.py test/include/npu_demo/test_public_namespace.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/dma/test_operation_ring.py test/dialect/dma/test_type.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_package.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_multi_buffer.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py
```

若目录重构计划已合并，计划级最低 pytest 改用迁移后的 multi-buffer 路径：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_dma.py test/include/npu_demo/test_public_namespace.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/dma/test_operation_ring.py test/dialect/dma/test_type.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_package.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py
```

执行人和 review 必须按实际 diff 继续补充更小范围或更宽范围测试；上述命令只是最低集合。

### 合同验收 expectation

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma.ring
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.include.npu_demo.dma_ring
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dialect.dma.operation.make_ring
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.multi_buffer
```

- `expectation.pass.pipeline` 及其 leaf 均不列为本计划默认必过；当前主仓不存在 `expectation/pass/pipeline` 合同资产，pipeline 接入由 `spec/pass/pipeline/npu_demo_lowering.md` 与 `test/passes/pipeline/test_npu_demo_lowering.py` 验收。除非用户后续明确要求新增 pipeline expectation，否则不得升级为本计划阻断。
- `expectation.dsl.emit_c.npu_demo.dma` 聚合入口不列为本计划默认必过；当前该聚合包含多个未授权旧 EmitC DMA leaf，与本计划只授权 `expectation/dsl/emit_c/npu_demo/dma/ring.py` 的合同范围冲突，除非用户明确要求并扩展授权，否则不得升级为本计划阻断。
- `expectation/` 是合同资产；execute 只能在本计划和用户确认授权列出的文件范围内新增 / 修改，不得扩散。

## 禁止修改面

- 未经明确授权不得修改 `.skills/`。
- 不得修改 `agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`plan/1.md`。
- 执行任务不得修改本计划文件 `ARCHITECTURE/plan/multi_buffer_emitc_runtime_ring.md`；若 review 退回需要修计划，必须回到计划负责人修订并重新 strict review。
- 不得把现有 `pass-directory-layout-refactor` task worktree、任务记录或无关 staged diff 纳入本计划。
- `expectation/` 只能在用户确认的 listed 文件范围内修改。
- 不得删除或重命名公开 API，除非用户明确选择 breaking change；本计划已确认的 breaking change 仅限 `DmaMakeRingOp.shape_bytes` operand 删除与 `MultiBufferPass.memory_stage` 默认值从 3 改为 2。
- 不得新增跨文件 private API 调用；测试不得直连非公开 helper。
- 不得使用 `hasattr(ctx, ...)`、`getattr(ctx, ...)` 等 runtime 能力探测为 EmitC context 做兼容分支。

## 已确认决策

### D1：include runtime API

- 结论：采用 `DmaRing` class 成员函数 `current()` / `advance()`，只保留 free function `make_ring(...)`，不公开 `current_ring(...)` / `advance_ring(...)`，也不公开 `cursor()` / `num()` / `offset_bytes()` accessor。
- 公开签名：`template <MemorySpace Space, typename SlotT, typename BackingT> class DmaRing`；`template <typename SlotT, MemorySpace Space, typename BackingT> DmaRing<Space, SlotT, BackingT> make_ring(Memory<Space, BackingT>& backing, S_INT num, S_INT offset_bytes, std::initializer_list<long long> shape, std::initializer_list<long long> stride, MemoryFormat format = MemoryFormat::Norm)`。
- 构造语义：`DmaRing` 只承诺由 `make_ring(...)` 返回值创建并使用；不提供 public default constructor；copy / move constructor 与 copy / move assignment 不作为 public stable API。
- 影响：新增 include public API；execute 必须同步 spec、文件级 API 列表、pytest 和 expectation。
- 确认来源：2026-06-07 用户先确认方案 C，随后认可 `current` / `advance` 作为 ring 结构体成员函数更合适；2026-06-07 用户对上述完整签名与构造语义确认：“2 是的”。

### D2：IR 层 `DmaMakeRingOp.shape_bytes`

- 结论：不保留 `shape_bytes` operand。
- 影响：这是 dialect public API breaking change；execute 必须更新 `spec/dialect/dma.md`、`kernel_gen/dialect/dma/operation/ring.py`、dialect tests、`expectation/dialect/dma/operation/make_ring.py`、`expectation/pass/multi_buffer/matmul_ring_memory_stage.py` 和 `expectation/pass/multi_buffer/matmul_ring_target.py`。
- 确认来源：2026-06-07 用户明确：“DmaMakeRingOp.shape_bytes 也不保留”。

### D3：默认 stage 与 pipeline auto

- 结论：`MultiBufferPass` direct constructor 与 `from_options({})` 默认 `memory_stage=2`；demo pipeline 中使用 `MultiBufferPass(memory_stage=2, target=<pipeline target>)`，由非空 target 触发 target registry auto 计算 ring `num`。
- 影响：execute 必须更新 pass spec、实现、registry option 测试和 pipeline order 测试；不新增 pipeline expectation。
- 确认来源：2026-06-07 用户明确：“3 默认是2，但是在bpudemo pipeline 中是 auto”；2026-06-07 用户补充确认：“bpudemo pipeline 就是 npu demo”。
- 当前基线说明：本计划把用户所说 `bpudemo pipeline` 收口为现有 `npu-demo-lowering`，只更新该 pipeline，不新增或条件纳入单独 `bpudemo` / `bpu_demo` pipeline。

### D4：`expectation/` 授权范围

- 结论：用户要求“需要补一些相关的 expectation”，本计划将 expectation 写权限限定在正文列出的 ring / dialect / pass / pipeline 合同资产，不扩散到其它 expectation。
- 本计划授权范围：
  - 新增 `expectation/dsl/emit_c/npu_demo/dma/ring.py`
  - 新增 `expectation/include/npu_demo/dma_ring.py`
  - 更新 `expectation/dialect/dma/operation/make_ring.py`
  - 更新 `expectation/pass/multi_buffer/matmul_ring_memory_stage.py`
  - 更新 `expectation/pass/multi_buffer/matmul_ring_target.py`
- 未列出的 `expectation/` 文件仍为只读。

### D6：include runtime 错误文本

- 结论：本计划不冻结 exact runtime error text。
- 影响：pytest / expectation 只验证失败类别和失败行为，例如非法 `num`、非法 `offset_bytes`、slot span 超出 offset、backing storage 不足；不得匹配具体异常文本作为稳定合同。
- 原因：用户未确认具体错误文本；根规则要求稳定错误文本属于公开 API，不能由 strict review 代替用户确认。

### D5：与当前目录重构计划的依赖顺序

- 结论：不作为用户阻断决策；管理员下发时必须避开当前 `pass-directory-layout-refactor` 任务现场。推荐等待目录重构计划合并后再执行；若并行，必须创建独立 worktree 并在任务记录中写清 rebase / 同步策略。
- 影响：执行时以最新主线 canonical path 为准；若目录重构已合并，则使用 `kernel_gen.passes.memory.multi_buffer` 与 `spec/pass/memory/multi_buffer.md`。

## 迭代审阅记录

### Draft 1：主线起草

- 审阅对象：`ARCHITECTURE/plan/multi_buffer_emitc_runtime_ring.md` Draft 1。
- 输入来源：用户 2026-06-07 关于方案 C、`shape_bytes`、member function、决策流程与补 expectation 的要求；当前 main 代码与 spec / expectation 基线。
- 当前状态：未发起 subagent strict review。原因是 Draft 1 明确存在 D1-D5 待用户决策项，按根 `AGENTS.md` 不能在公开 API、pipeline 和 expectation 授权未确认时进入互评通过或守护最终检验。
- 后续处理：用户已在 2026-06-07 确认 D1-D5，计划负责人已修订为 Draft 2；Draft 2 仍需发起至少两路 Codex subagent strict review，所有审阅任务无阻断、无最小需改项、无待确认项后，才允许进入 `守护最好的爱莉希雅` 守护最终检验。

### Draft 2：用户决策吸收

- 审阅对象：`ARCHITECTURE/plan/multi_buffer_emitc_runtime_ring.md` Draft 2。
- 输入来源：用户 2026-06-07 对 `DmaMakeRingOp.shape_bytes` 删除、默认 stage 2、demo pipeline auto 口径的确认。
- 主线处理：
  - 将 `spec/dialect/dma.md` 从条件范围改为必改范围。
  - 将 `DmaMakeRingOp` 公开签名改为 `(memory, num, offset, result_type)`。
  - 将 `MultiBufferPass` 默认值从 `memory_stage=3` 改为 `memory_stage=2`。
  - 将 pipeline 接入点固定为第三段 cleanup 后、`producer-consumer-analysis` 前，构造为 `MultiBufferPass(memory_stage=2, target=<pipeline target>)`。
  - 将 expectation 授权范围扩展到 dialect make_ring、multi_buffer pass 和当时设想的 pipeline expectation；Draft 7 已按用户最新口径撤回 pipeline expectation 授权。
  - 核对当前 main 未发现 `bpudemo` / `bpu_demo` pipeline 文件；计划保留若执行基线出现则同步纳入的条件分支。
- 审阅任务：
  - `Ptolemy / 019e9e16-c5ff-7a42-b1c8-ab46d15020c1`：不通过。
  - `Kierkegaard / 019e9e16-782d-7451-a288-17ebffc15b4d`：不通过。
- 发现问题：
  1. `DmaRing::cursor()/num()/offset_bytes()` accessor 属于新增 public API，但用户确认只覆盖 `make_ring` 与 `current/advance` 成员调用。
  2. runtime exact error text 被写成后续冻结项，但用户未确认稳定错误文本。
  3. `shape_bytes` 删除影响面未列全，漏掉 `kernel_gen/dialect/dma/__init__.py` 与 `kernel_gen/dialect/dma/operation/__init__.py` 文件级 API 列表；同时小任务未明确要求修改 `kernel_gen/passes/multi_buffer.py`、`spec/pass/multi_buffer.md`、registry option 测试和旧 `shape_bytes` 生成路径。
  4. expectation 授权存在“或新增同目录 leaf”和 `expectation/pass/multi_buffer/*` 通配，范围不够精确。
  5. 禁止修改面和敏感状态检查未包含当前计划文件。
  6. 与目录重构计划合并后的测试路径兼容不完整。
- 主线处理：
  - Draft 3 删除 `DmaRing` public accessor，只保留 `current()` / `advance()`。
  - Draft 3 将 runtime exact error text 降级为非稳定合同，只验失败类别与行为。
  - Draft 3 将 `kernel_gen/dialect/dma/__init__.py`、`kernel_gen/dialect/dma/operation/__init__.py` 纳入 S1，并增加旧 `shape_bytes` 签名清扫验收。
  - Draft 3 在 S4 明确修改 `MultiBufferPass` spec、实现、pytest、registry option 默认值和 pipeline。
  - Draft 3 将 expectation 授权精确到具体文件，不再使用“同目录 leaf”或通配授权。
  - Draft 3 将当前计划文件纳入禁止修改面和敏感状态检查，并补目录重构后的替代 pytest 路径。
- 当前状态：Draft 2 strict review 未通过，已按问题修订为 Draft 3；需发起下一轮 strict review。

### Draft 3：Draft 2-R1 修订后 strict review

- 审阅对象：`ARCHITECTURE/plan/multi_buffer_emitc_runtime_ring.md` Draft 3。
- 输入来源：Draft 2-R1 修订文本、根 `AGENTS.md`、相关标准、Draft 2 review 问题、禁止修改面、必过 pytest 与 expectation 命令。
- 审阅任务：
  - `Ptolemy / 019e9e16-c5ff-7a42-b1c8-ab46d15020c1`：不通过。
  - `Kierkegaard / 019e9e16-782d-7451-a288-17ebffc15b4d`：不通过。
- 发现问题：
  1. `bpudemo pipeline` 口径仍有歧义。Draft 3 把它写成“若执行基线存在则纳入”，但当前 main 只有 `npu-demo-lowering`，用户原话需要确认是单独 pipeline 还是指 npu demo。
  2. include public API 虽列出 `DmaRing` / `make_ring`，但完整模板签名、参数顺序、factory-only 构造语义，以及 default/copy/move/assignment 是否属于公开稳定 API 仍需用户确认。
  3. S2 漏写 `include/npu_demo/Dma.h` 文件级 API 列表更新；S3 需明确更新 `spec/dsl/gen_kernel/emit/npu_demo/dma/__init__.md`；S4 需纳入 `spec/pass/registry.md` 与 `kernel_gen/passes/__init__.py`；总验收需保留目录重构后的 `test/passes/memory/test_multi_buffer.py` 替代路径。
- 主线处理：
  - Draft 4 根据用户确认“bpudemo pipeline 就是 npu demo”，删除单独 `bpudemo` / `bpu_demo` pipeline 的条件分支、expectation 授权和额外 pytest 命令，只更新 `npu-demo-lowering`。
  - Draft 4 根据用户确认“2 是的”，冻结 include 完整签名，明确 `DmaRing` factory-only 构造语义，不提供 public default constructor，copy / move / assignment 不作为 public stable API。
  - Draft 4 已补齐 S2 / S3 / S4 / 验收中的 API 列表、spec、registry、package root 和目录重构替代测试路径要求。
- 当前状态：Draft 3 strict review 未通过，已按问题修订为 Draft 4；需发起下一轮 strict review。

### Draft 4：Draft 3-R1 修订后 strict review

- 审阅对象：`ARCHITECTURE/plan/multi_buffer_emitc_runtime_ring.md` Draft 4。
- 计划 sha256：`55adafe02b9fc3e1314045b6d5998c5912dffc87d09e129a6c16406afc468f9d`。
- 输入来源：Draft 4 计划全文、根 `AGENTS.md`、相关标准、Draft 3 review 问题、本轮用户确认、禁止修改面、必过 pytest 与 expectation 命令。
- 审阅任务：
  - `Ptolemy / 019e9e16-c5ff-7a42-b1c8-ab46d15020c1`：通过；阻断项无、最小需改项无、待确认项无。
  - `Kierkegaard / 019e9e16-782d-7451-a288-17ebffc15b4d`：不通过；阻断项无、待确认项无、最小需改项 1 项。
- 发现问题：
  1. `spec/pass/registry.md` 已在 S4 列为需更新项，但未出现在目标 spec 列表；计划级 pytest 未纳入 `test/passes/test_registry.py`，导致 registry 公开合同、默认 stage=2、`fold` 通用 option 与 pass 专属 option 组合行为缺少验收闭环。
- 主线处理：
  - Draft 5 将 `spec/pass/registry.md` 加入目标 spec。
  - Draft 5 在 S4 执行步骤中明确更新 `test/passes/test_registry.py`，覆盖 registry 构造 `multi-buffer` 默认 `memory_stage=2`、`fold` 通用 option 与 `memory-stage=<positive-int>` pass 专属 option 组合。
  - Draft 5 将 `test/passes/test_registry.py` 加入 S4 和计划级 Diff 反推 pytest 命令，目录重构替代测试路径也同步保留 registry pytest。
- 当前状态：Draft 4 strict review 未收敛，已按最小需改项修订为 Draft 5；需发起下一轮 strict review。

### Draft 5：Draft 4-R1 修订后 strict review

- 审阅对象：`ARCHITECTURE/plan/multi_buffer_emitc_runtime_ring.md` Draft 5。
- 计划 sha256：`e500ffd888d6414c4ced7a89849a2176742068485d449be70b4f8954d4108d5a`。
- 输入来源：Draft 5 计划全文、根 `AGENTS.md`、相关标准、Draft 4 review 结果和最小修订、禁止修改面、必过 pytest 与 expectation 命令。
- 审阅任务：
  - `Ptolemy / 019e9e16-c5ff-7a42-b1c8-ab46d15020c1`：通过；阻断项无、最小需改项无、待确认项无。
  - `Kierkegaard / 019e9e16-782d-7451-a288-17ebffc15b4d`：通过；阻断项无、最小需改项无、待确认项无。
- 关键证据：
  - `spec/pass/registry.md` 已加入目标 spec；S4 和总体验收均纳入 `test/passes/test_registry.py`。
  - include 完整签名、factory-only 构造语义、`bpudemo pipeline` 等同 `npu-demo-lowering`、expectation 授权范围、pytest / expectation 分列、禁止修改面和现有 `pass-directory-layout-refactor` 隔离均经两路复审确认。
- 当前状态：Draft 5 strict review 已收敛；可进入 `守护最好的爱莉希雅` 守护最终检验。

### Draft 6：review Finding 1 验收口径修订

- 触发来源：`T-20260607-e1685c52 / multi-buffer-emitc-runtime-ring` review 发现计划在 S3 与计划级合同验收中把 `python3 -m expectation.dsl.emit_c.npu_demo.dma` 列为必过入口，但 D4 仅授权新增 / 更新 `expectation/dsl/emit_c/npu_demo/dma/ring.py`，未授权修改同目录 alloc/broadcast/copy/deslice/fill/load/slice/store/transpose 等旧 leaf；review 复跑聚合入口失败于这些旧 leaf。
- 架构裁定：选择 B。目录级 `expectation.dsl.emit_c.npu_demo.dma` 聚合入口不应作为当前计划必过合同入口；本计划只要求 `expectation.dsl.emit_c.npu_demo.dma.ring` leaf 必过。不得为通过目录级聚合而扩大 expectation 授权或修改旧 leaf。
- 计划 sha256：`e8889cc0a3c3af10d26f44f887b8d47524896db43b7c70be141e99b3bc0d2d1f`。
- 主线处理：
  - Draft 6 删除 S3 和计划级合同验收中的 `python3 -m expectation.dsl.emit_c.npu_demo.dma` 必过命令。
  - Draft 6 明确该聚合属于历史 / 无关基线，不作为当前计划阻断；仅用户后续明确要求全量 EmitC DMA 聚合并扩展授权时，才能另行纳入。
  - Finding 2 `test/repo_conformance/test_private_api_boundaries.py -x` private callable conformance 仍为 execute 返工项；待 Draft 6 复验通过后恢复 execute 处理。
- 审阅任务：
  - `Ptolemy / 019e9e16-c5ff-7a42-b1c8-ab46d15020c1`：通过；阻断项无、最小需改项无、待确认项无。
  - `Kierkegaard / 019e9e16-782d-7451-a288-17ebffc15b4d`：通过；阻断项无、最小需改项无、待确认项无。
- 当前状态：Draft 6 strict review 已收敛；需完成守护复验；通过前不得恢复 execute。

### Draft 7：pipeline expectation 验收口径修订

- 触发来源：`T-20260607-e1685c52 / multi-buffer-emitc-runtime-ring` execute 恢复后报告主仓不存在 `expectation/pass/pipeline` 目录；Draft 6 仍把 `python3 -m expectation.pass.pipeline.npu_demo_lowering` 列为必过合同验收，实际运行失败为 `ModuleNotFoundError: No module named expectation.pass.pipeline`。
- 用户口径：2026-06-07 用户明确：“expectation.pass.pipeline 不再作为验收”。
- 架构裁定：选择 B，修订计划验收口径；不由 execute 新增 `expectation/pass/pipeline` 目录或 leaf；不改变 `npu-demo-lowering` 接入 `MultiBufferPass(memory_stage=2, target=<pipeline target>)` 的实现 / spec / pytest 目标。
- 主线处理：
  - 从 D4 `expectation/` 授权范围删除 `expectation/pass/pipeline/npu_demo_lowering.py`。
  - 从 S4、S5 和计划级合同验收删除 `python3 -m expectation.pass.pipeline.npu_demo_lowering` 必过命令。
  - 明确 `expectation.pass.pipeline` 及其 leaf 均不作为本计划验收入口；pipeline 接入由 `spec/pass/pipeline/npu_demo_lowering.md` 与 `test/passes/pipeline/test_npu_demo_lowering.py` 验收。
- review 必查项：复核执行 diff 未新增 / 修改 `expectation/pass/pipeline/**`；复核 pipeline spec、pipeline 实现和 `test/passes/pipeline/test_npu_demo_lowering.py` 锁定 `MultiBufferPass(memory_stage=2, target=<pipeline target>)`；复核 4 个当前必过 expectation 与 private API conformance 通过。
- 待用户确认项：无。若后续要新增 pipeline expectation 合同资产，必须另行取得用户确认。
- 审阅任务：
  - `Kierkegaard / 019e9e16-782d-7451-a288-17ebffc15b4d`：通过；阻断项无、最小需改项无、待确认项无。
  - `Ptolemy / 019e9e16-c5ff-7a42-b1c8-ab46d15020c1`：通过；阻断项无、最小需改项无、待确认项无。
- 审阅证据摘要：
  - 两路均核对计划级必过 expectation 仅为 4 项：`expectation.dsl.emit_c.npu_demo.dma.ring`、`expectation.include.npu_demo.dma_ring`、`expectation.dialect.dma.operation.make_ring`、`expectation.pass.multi_buffer`。
  - 两路均确认 `expectation.pass.pipeline` 及其 leaf 已从验收和 D4 授权清单移除，正文明确不新增 / 修改 `expectation/pass/pipeline/**`。
  - 两路均确认 pipeline 接入仍由 `spec/pass/pipeline/npu_demo_lowering.md` 与 `test/passes/pipeline/test_npu_demo_lowering.py` 验收，用户最新口径已记录，无待用户确认项。
- 当前状态：Draft 7 strict review 已收敛；正等待守护复验。守护复验通过前不得恢复 execute。

### subagent 收敛结论

- 当前结论：Draft 5 两路 subagent strict review 已收敛；Draft 6 两路 strict review 已收敛；Draft 7 两路 strict review 已收敛，`Ptolemy / 019e9e16-c5ff-7a42-b1c8-ab46d15020c1` 与 `Kierkegaard / 019e9e16-782d-7451-a288-17ebffc15b4d` 均通过，阻断项无、最小需改项无、待确认项无。
- 不可恢复 execute 原因：Draft 7 尚未完成守护复验。

### 守护最终检验

- 当前状态：Draft 5 已通过；Draft 6 修订已完成 strict review；Draft 7 修订已完成 strict review，待守护复验。
- 前置条件：Draft 7 已完成 subagent strict review 收敛；计划正文无待确认项。

## 计划书入档验收 / 复验 / 修复复核记录

- 结论人：待计划级 `execute` 完成后由计划书入档验收角色填写。
- 结论：待填写。
- 验证基线：待填写。
- 执行目录：待填写。
- 合同验收摘要：待填写。
- 最小阻断项或通过摘要：待填写。

## 用户确认与协同约束

- Draft 7 已记录用户对 include runtime API、include 完整签名与构造语义、IR `shape_bytes` 删除、默认 stage 2、`bpudemo pipeline` 等同 `npu-demo-lowering`、demo pipeline auto、补 expectation 以及 `expectation.pass.pipeline` 不作为验收入口的确认。
- Draft 7 当前无待用户确认项；本轮只收缩 pipeline expectation 验收与授权范围，不新增公开 API 或 expectation 授权。
- Draft 7 strict review 与守护复验通过前，不得恢复 `T-20260607-e1685c52` execute。
- 执行阶段若发现 `npu-demo-lowering` 的 target registry、capacity 键或 pipeline 参数传递方式与计划不一致，必须停下回报用户 / 架构师；不得自行新增单独 `bpudemo` / `bpu_demo` pipeline。
