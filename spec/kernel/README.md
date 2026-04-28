# kernel/README.md

## 功能简介

- 汇总 `expectation/kernel` 只读合同资产所依赖的公开 API、解析、lowering、代码生成、pytest 与合同验收口径。
- 当前专题只覆盖两份只读资产：
  - [`expectation/kernel/flash_attention.py`](/home/lfr/kernelcode_generate/expectation/kernel/flash_attention.py)
  - [`expectation/kernel/matmul.py`](/home/lfr/kernelcode_generate/expectation/kernel/matmul.py)
- 这两份资产不允许改写；后续实现阶段必须以“保持资产原样可运行”为目标，通过补齐公开 API、解析、pass/pipeline 与代码生成能力收口。

## API 列表

- `kernel_gen.dsl.build_func_op(fn: Callable[..., object], *runtime_args: object, globals: dict[str, object] | None = None, builtins: dict[str, object] | object | None = None) -> func.FuncOp`
- `kernel_gen.dsl.mlir_gen.mlir_gen(fn: callable, *runtime_args, globals: dict[str, object] | None = None, builtins: dict[str, object] | object | None = None) -> builtin.ModuleOp`
- `kernel_gen.dsl.gen_kernel.EmitCContext()`
- `kernel_gen.dsl.gen_kernel.gen_kernel(obj: object, ctx: EmitCContext) -> str`
- `kernel_gen.passes.pipeline.build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager`
- `kernel_gen.passes.SymbolLoopHoistPass()`
- `kernel_gen.passes.lowering.NnLoweringPass()`
- `kernel_gen.symbol_variable.memory.Memory(shape: ShapeLike, dtype: NumericType | None = None, space: MemorySpace = MemorySpace.GM, stride: ShapeLike | None = None, format: Farmat = Farmat.Norm)`
- `kernel_gen.symbol_variable.memory.MemorySpace`
- `kernel_gen.symbol_variable.symbol_dim.SymbolDim(value)`
- `kernel_gen.symbol_variable.type.NumericType`
- `kernel_gen.operation.dma.alloc(shape, dtype, space=MemorySpace.GM, stride=None, format=Farmat.Norm)`
- `kernel_gen.operation.dma.fill(target, value)`
- `kernel_gen.operation.dma.slice(source, offsets, sizes, strides=None, space=None)`
- `kernel_gen.operation.dma.deslice(target, source, offsets, sizes, strides=None)`
- `kernel_gen.operation.dma.reshape(source, shape)`
- `kernel_gen.operation.nn.add(lhs, rhs)`
- `kernel_gen.operation.nn.broadcast_to(source, target_shape, space)`
- `kernel_gen.operation.nn.exp(value)`
- `kernel_gen.operation.nn.matmul(lhs, rhs, memoryspace=None)`
- `kernel_gen.operation.nn.mul(lhs, rhs)`
- `kernel_gen.operation.nn.reduce_max(value, axis=None, keepdim=False)`
- `kernel_gen.operation.nn.reduce_sum(value, axis=None, keepdim=False)`
- `kernel_gen.operation.nn.softmax(value, axis=-1)`
- `kernel_gen.operation.nn.sub(lhs, rhs)`
- `kernel_gen.operation.nn.transpose(value, perm)`
- `kernel_gen.operation.nn.truediv(lhs, rhs)`
- `kernel_gen.operation.scf.loop(start, end, step, trip_count=1)`

## 文档信息

- 创建者：`睡觉小分队`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/kernel/README.md`](../../spec/kernel/README.md)

## 依赖

- [`spec/dsl/package_api.md`](../dsl/package_api.md)：`kernel_gen.dsl` 包根导出边界。
- [`spec/dsl/mlir_gen.md`](../dsl/mlir_gen.md)：`build_func_op(...)` / `mlir_gen(...)` 合同。
- [`spec/dsl/ast/parser.md`](../dsl/ast/parser.md)：helper 识别、`fill` 字符串字面量与环境控制边界。
- [`spec/dsl/gen_kernel/emit_context.md`](../dsl/gen_kernel/emit_context.md)：`EmitCContext` 公开构造口径。
- [`spec/dsl/gen_kernel/gen_kernel.md`](../dsl/gen_kernel/gen_kernel.md)：`gen_kernel(...)` 入口。
- [`spec/operation/dma.md`](../operation/dma.md)：`alloc/fill/slice/deslice/reshape` 合同。
- [`spec/operation/nn.md`](../operation/nn.md)：`matmul`、逐元素、broadcast、reduce 与 `softmax` 合同。
- [`spec/operation/scf.md`](../operation/scf.md)：`loop(...)` 合同。
- [`spec/symbol_variable/memory.md`](../symbol_variable/memory.md)：`Memory` / `MemorySpace` 合同。
- [`spec/symbol_variable/symbol_dim.md`](../symbol_variable/symbol_dim.md)：`SymbolDim` 合同。
- [`spec/symbol_variable/type.md`](../symbol_variable/type.md)：`NumericType` 合同。
- [`spec/pass/symbol_loop_hoist.md`](../pass/symbol_loop_hoist.md)：`SymbolLoopHoistPass` 合同。
- [`spec/pass/lowering/nn_lowering/spec.md`](../pass/lowering/nn_lowering/spec.md)：`NnLoweringPass` 合同。
- [`spec/pass/pipeline/npu_demo_lowering.md`](../pass/pipeline/npu_demo_lowering.md)：`build_npu_demo_lowering_pipeline(...)` 合同。
- 只读合同资产：
  - [`expectation/kernel/flash_attention.py`](/home/lfr/kernelcode_generate/expectation/kernel/flash_attention.py)
  - [`expectation/kernel/matmul.py`](/home/lfr/kernelcode_generate/expectation/kernel/matmul.py)

## 合同真源顺序

1. 本文负责收口 `expectation/kernel` 专题的资产矩阵、导入路径、测试矩阵与合同验收口径。
2. `dsl` 相关真源按以下顺序读取：
   - [`spec/dsl/package_api.md`](../dsl/package_api.md)
   - [`spec/dsl/mlir_gen.md`](../dsl/mlir_gen.md)
   - [`spec/dsl/ast/parser.md`](../dsl/ast/parser.md)
   - [`spec/dsl/gen_kernel/emit_context.md`](../dsl/gen_kernel/emit_context.md)
   - [`spec/dsl/gen_kernel/gen_kernel.md`](../dsl/gen_kernel/gen_kernel.md)
3. `operation` / `symbol_variable` / `pass` 的单模块语义继续分别由各自 spec 承接；本文不重复定义这些模块的细节，只定义“哪条资产依赖哪组公开入口”。
4. `expectation/kernel/*.py` 只作为只读合同验收资产；它们不替代公开 API 真源，也不替代 diff 反推 pytest。

## 资产矩阵

### `flash_attention.py`

- 该资产当前要求两类公开能力同时成立：
  - `kernel_gen.dsl.build_func_op(...)` 可直接消费导入绑定后的 DSL callable
  - `kernel_gen.operation.dma` / `kernel_gen.operation.nn` / `kernel_gen.operation.scf` / `kernel_gen.symbol_variable.*` 的公开 helper 与类型可直接导入并执行
- 当前文件体内实际执行路径停在：
  - `Memory(...)`
  - `SymbolDim(...)`
  - `loop(...)`
  - `slice(...)` / `reshape(...)` / `alloc(...)` / `fill(...)` / `deslice(...)`
  - `matmul(...)` / `transpose(...)` / `broadcast_to(...)` / `reduce_*` / `exp(...)` / `add(...)` / `sub(...)` / `mul(...)` / `truediv(...)`
  - `build_func_op(flash_attention_kernel, ...)`
- 虽然该资产还导入了 `SymbolLoopHoistPass`、`NnLoweringPass` 与 `build_npu_demo_lowering_pipeline(...)`，但当前文件体并不执行这些 pass；后续实现不得以“当前没调到”作为删掉这些公开导入路径的理由，因为资产导入本身也是合同的一部分。

### `matmul.py`

- 该资产要求三段公开链路在同一现场可连续执行：
  1. `mlir_gen(matmul_kernel, ...)`
  2. `build_npu_demo_lowering_pipeline().run(module)`
  3. `set_target("npu_demo")` 后 `gen_kernel(module, EmitCContext())`
- `matmul.py` 当前还显式导入：
  - `EmitCContext`
  - `SymbolLoopHoistPass`
  - `NnLoweringPass`
- 这意味着后续实现既要保证 module 路径可运行，也要保证这些导入路径本身继续有效。
- 当 `matmul_kernel(...)` 带 `SymbolDim` tile / shape 参数时，公开链 `set_target("npu_demo") -> mlir_gen(...) -> build_npu_demo_lowering_pipeline().run(module) -> gen_kernel(module, EmitCContext())` 还必须保留这些 trailing symbol scalar：
  - wrapper 对外继续暴露 `lhs/rhs/out + trailing symbol scalar` 公开签名；
  - device body 不再暴露 `KernelContext` 参数，只保留 `lhs/rhs/out + trailing symbol scalar` 公开签名；
  - `npu_demo::launch<...>(body, ...)` 必须把 trailing symbol scalar 与 memory 参数一起原样透传。

## 公开导入与非公开边界

- `expectation/kernel` 专题下允许后续实现依赖的公开导入路径固定为：
  - `kernel_gen.dsl`
  - `kernel_gen.dsl.mlir_gen`
  - `kernel_gen.dsl.gen_kernel`
  - `kernel_gen.operation.dma`
  - `kernel_gen.operation.nn`
  - `kernel_gen.operation.scf`
  - `kernel_gen.symbol_variable.memory`
  - `kernel_gen.symbol_variable.type`
  - `kernel_gen.passes`
  - `kernel_gen.passes.lowering`
  - `kernel_gen.passes.pipeline`
- 不允许把以下入口当作后续实现、测试或专题验收的稳定依赖：
  - `kernel_gen.dsl.ast.parser.parse_function_with_env(...)`
  - `kernel_gen.dsl.mlir_gen` 文件内 parse-env / signature helper
  - `kernel_gen.dsl.gen_kernel.kernel_emitter` 与同目录非公开 helper
  - `kernel_gen.passes.pipeline.npu_demo_lowering` 文件内非公开顺序 helper
  - `kernel_gen.passes.symbol_loop_hoist` / `nn_lowering` 文件内未列入各自 `API 列表` 的 pattern helper
- 若后续 build 需要兼容旧调用形态，只能通过已经列入公开 API 的同文件入口做参数归一或包装，不能新增跨文件 private helper 依赖。

## 解析与 lowering 口径

- helper 识别继续以 [`spec/dsl/ast/parser.md`](../dsl/ast/parser.md) 的“显式 import 绑定到真实公开 helper 对象 + 调用形态”作为真源，不允许依赖 helper Python 签名做解析分支。
- `fill(...)` 的字符串字面量继续只允许 `"inf"` 与 `"-inf"`；`flash_attention.py` 中的 `fill(m_acc, "-inf")` 直接由这条公开口径解释，不允许后续实现改成别的字符串别名再要求资产跟着变。
- `build_npu_demo_lowering_pipeline(...)` 继续只接受 `target=npu_demo` 这条公开 builder 路径，不扩大到 `dsl_run` 或 `execute_engine` 相关工具入口。
- `EmitCContext` 在本专题内只接受无参构造；target 必须先通过 `kernel_gen.core.config.set_target("npu_demo")` 设置。
- `expectation/kernel/matmul.py` 若参与本轮合同验收，应同步到 `set_target("npu_demo") + EmitCContext()` 公开链路。
- `kernel_gen.passes.lowering.NnLoweringPass` 与 `kernel_gen.passes.SymbolLoopHoistPass` 继续作为当前专题只读资产可导入路径承接；后续若要下收或移位，必须先给这两份资产准备新的公开承接路径，再另开任务处理。

## 测试矩阵

- 解析 / 包根导出：
  - `pytest -q test/dsl/test_package_api.py`
  - `pytest -q test/dsl/ast/test_package.py test/dsl/ast/test_parser.py`
  - `pytest -q test/dsl/mlir_gen/test_function_builder.py test/dsl/test_mlir_gen.py`
- operation / symbol_variable：
  - `pytest -q test/operation/test_operation_dma.py test/operation/test_operation_nn.py test/operation/test_operation_scf.py`
  - `pytest -q test/symbol_variable/test_memory.py test/symbol_variable/test_symbol_dim.py test/symbol_variable/test_type.py`
- lowering / pipeline / gen_kernel：
  - `pytest -q test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_lowering_nn_lowering.py`
  - `pytest -q test/pass/test_symbol_loop_hoist.py test/pass/test_pipeline_npu_demo_lowering.py`
  - `pytest -q test/dsl/gen_kernel/test_gen_kernel.py`
- 上述 pytest 只锁公开 API，不直连 parser / emit / pass 的跨文件非公开 helper。

## 合同验收

- 本专题的合同验收资产固定为：
  - `python3 expectation/kernel/flash_attention.py`
  - `python3 expectation/kernel/matmul.py`
- 这两条命令只作为合同验收，不计入 `Diff 反推自测`。
- 合同验收只允许只读执行，不允许修改、移动、重命名或新增 `expectation/kernel/**` 文件。
- 若后续 build 在 pytest 全部通过后仍无法跑通上述资产，必须把失败归因写回任务记录，并明确是：
  - 导入路径缺失
  - parser/helper 识别不一致
  - lowering/pipeline 不满足 module 链路
  - `EmitCContext` / `gen_kernel` 公开入口与只读资产调用形态不一致
