# dsl_run.md

## 功能简介

- `dsl_run(func, real_args, pipeline)` 是面向测试和脚本的单入口工具。
- 负责串起 `mlir_gen -> pass/pipeline -> gen_kernel -> ExecutionEngine.compile/execute`。
- 公开合同只覆盖这条一体化路径，不扩展到无关 pass、无关 dialect、无关工具。
- `kernel_gen.tools` 包根稳定暴露 `DslRunResult`、`kernel_gen.tools.dsl_run(...)` 与 `kernel_gen.tools.dsl_cost_run(...)`，不把 `dsl_run` 子模块对象当作公开合同。
- 诊断落盘根目录统一来自 `kernel_gen.core.config.set_dump_dir(...)`，不作为 `dsl_run(...)` 入参；IR dump 文件默认使用 `kernel_gen.core.print.print_operation_with_aliases(...)` 的 alias IR。
- runtime trance kernel log 开关统一来自 `kernel_gen.core.config.set_trance_enabled(...)`，不作为 `dsl_run(...)` 或 `dsl_cost_run(...)` 入参。
- 失败统一抛出 `KernelCodeError(ErrorModule.TOOLS, message)`；不再定义或导出工具专属错误类。
- `dsl_run(...)` 不向 kernel 函数隐式注入 operation helper、`MemorySpace`、`NumericType` 或 `SymbolDim`；kernel 体引用的名称必须来自显式 import、闭包或函数全局绑定，缺失时必须报错。
- `real_args` 支持真实 tensor/array 参数和运行期整数标量参数；Python `int` 与 numpy integer 标量会规整为 Python `int` 后绑定到 DSL 函数形参，供 runtime tile、stride、padding 等 `SymbolDim` 形参使用；`bool` 与 `float` 必须拒绝。

## API 列表

- `class DslRunResult(func_op: func.FuncOp, module: ModuleOp, source: str, compiled_kernel: CompiledKernel, execute_result: ExecuteResult, runtime_args: tuple[RuntimeRealArg, ...])`
- `dsl_run(func_obj: Callable[..., DslFunctionReturn], real_args: tuple[RuntimeRealArg, ...] | list[RuntimeRealArg], pipeline: str | PassManager) -> DslRunResult`
- `dsl_cost_run(func_obj: Callable[..., DslFunctionReturn], real_args: tuple[RuntimeRealArg, ...] | list[RuntimeRealArg], pipeline: str | PassManager, cost_kind: str) -> int`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/tools/dsl_run.md`](../../spec/tools/dsl_run.md)
- `功能实现`：[`kernel_gen/tools/dsl_run.py`](../../kernel_gen/tools/dsl_run.py)
- `test`：[`test/tools/test_dsl_run.py`](../../test/tools/test_dsl_run.py)

## 依赖

- DSL 解析：[`spec/dsl/ast/mlir_gen.md`](../../spec/dsl/ast/mlir_gen.md)
- 源码生成：[`spec/dsl/gen_kernel/gen_kernel.md`](../../spec/dsl/gen_kernel/gen_kernel.md)
- 执行引擎：[`spec/execute_engine/execute_engine.md`](../../spec/execute_engine/execute_engine.md)
- pass / pipeline：[`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)、[`spec/pass/registry.md`](../../spec/pass/registry.md)

## 额外补充

### 导入约定

- 直接模块入口：`from kernel_gen.tools.dsl_run import DslRunResult, dsl_run, dsl_cost_run`。
- 包根稳定入口：`import kernel_gen.tools as tools`，再使用 `tools.DslRunResult`、`tools.dsl_run(...)`、`tools.dsl_cost_run(...)`。
- 包根稳定导入：`from kernel_gen.tools import DslRunResult, dsl_run, dsl_cost_run`。

### helper 边界

- 当前文件内 `_runtime_module_name(...)`、`_normalize_real_args(...)`、`_resolve_pipeline(...)`、`_run_pipeline_with_optional_dump(...)`、`_select_source_and_entry(...)`、`_append_cost_capture_wrapper(...)` 等下划线 helper 只服务当前文件内部实现。
- 实现、测试和外部调用方不得跨文件导入或断言这些 helper；公开行为只能通过 `DslRunResult(...)`、`dsl_run(...)` 与 `dsl_cost_run(...)` 观察。
- `RuntimeRealArg` 是文档类型别名，表示 `torch.Tensor | numpy.ndarray | int`；Python `int` 与 numpy integer 属于合法整数 scalar，`bool` 与 `float` 不属于合法 runtime scalar。该别名不新增独立可调用公开入口。

## API详细说明

### `class DslRunResult(func_op: func.FuncOp, module: ModuleOp, source: str, compiled_kernel: CompiledKernel, execute_result: ExecuteResult, runtime_args: tuple[RuntimeRealArg, ...])`

- api：`class DslRunResult(func_op: func.FuncOp, module: ModuleOp, source: str, compiled_kernel: CompiledKernel, execute_result: ExecuteResult, runtime_args: tuple[RuntimeRealArg, ...])`
- 参数：
  - `func_op`：函数级 IR operation，作为构建、lowering 或代码生成输入；类型 `func.FuncOp`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `module`：模块级 IR 对象，作为 pass、校验或代码生成的处理主体；类型 `ModuleOp`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `source`：源对象、源缓冲区或源文本，提供当前操作读取的数据来源；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `compiled_kernel`：编译后的 kernel 句柄，用于执行阶段调用；类型 `CompiledKernel`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `execute_result`：执行结果对象，记录运行状态和输出信息；类型 `ExecuteResult`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `runtime_args`：运行期实参序列，与 DSL 函数形参按顺序对应；类型 `tuple[RuntimeRealArg, ...]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`DslRunResult` 实例。
- 使用示例：

  ```python
  dsl_run_result = DslRunResult(func_op=func_op, module=module, source=source, compiled_kernel=compiled_kernel, execute_result=execute_result, runtime_args=runtime_args)
  ```
- 功能说明：构造 `DslRunResult` 实例。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `dsl_run(func_obj: Callable[..., DslFunctionReturn], real_args: tuple[RuntimeRealArg, ...] | list[RuntimeRealArg], pipeline: str | PassManager) -> DslRunResult`

- api：`dsl_run(func_obj: Callable[..., DslFunctionReturn], real_args: tuple[RuntimeRealArg, ...] | list[RuntimeRealArg], pipeline: str | PassManager) -> DslRunResult`
- 参数：
  - `func_obj`：函数对象或函数级 IR；类型 `Callable[..., DslFunctionReturn]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `real_args`：运行期真实实参序列；类型 `tuple[RuntimeRealArg, ...] | list[RuntimeRealArg]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按可变容器传入时，是否修改输入必须以本接口功能说明和注意事项为准；非法值按该 API 的公开错误语义处理。
  - `pipeline`：pass pipeline 名称或 PassManager 对象；类型 `str | PassManager`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`DslRunResult`。
- 使用示例：

  ```python
  from kernel_gen.core.config import set_dump_dir, set_target
  from kernel_gen.operation import store
  from kernel_gen.tools.dsl_run import dsl_run

  def add_kernel(out, lhs, rhs):
      store(out, lhs + rhs, [0], [6], [1])

  set_target("npu_demo")
  set_dump_dir("dump")
  result = dsl_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering")
  assert result.execute_result.ok is True
  ```
- 功能说明：执行 `dsl_run` 工具入口。
- 注意事项：
  - target 只能来自 `kernel_gen.core.config.get_target()`；未设置或不是非空 `str` 时必须失败，固定短语为 `DslRunInvalidTarget: core config target must be non-empty str`。
  - `pipeline` 仅接受 `str | PassManager`。
  - `real_args` 容器仅接受 `tuple | list`，元素仅允许 `torch.Tensor`、`numpy.ndarray`、Python `int` 或 numpy integer 标量。
  - `bool` 不属于运行期标量参数；不允许借 `bool` 是 `int` 子类的 Python 行为进入 DSL runtime。
  - 运行期整数标量不构造成 `Memory`，必须规整为 Python `int` 后传入 `mlir_gen(...)` 并继续作为执行阶段真实参数。
  - 名称以 `tile_` 开头的运行期标量必须是正整数；`0`、负数、`float` 或 `bool` 必须失败，固定短语为 `DslRunInvalidTileValue: tile runtime scalar must be positive int`。
  - 非 tensor/array 且非合法整数标量的元素必须失败，固定短语为 `DslRunUnsupportedRealArg: real_args only supports torch.Tensor, numpy.ndarray and integer scalar`。
  - DSL 函数只要存在值返回，就必须失败。
  - DSL 函数体引用未显式导入或绑定的 helper / enum 名称时，必须由 DSL parser 显式失败；`dsl_run(...)` 不得补写 `func.__globals__`。
  - `core.config.target` 决定源码生成与执行目标，不做跨 target 自动猜测。
  - `target == "npu_demo"` 时，lowered module 必须包含且仅包含一个带 `arch.launch` 的 wrapper func；否则必须显式失败。
  - `target == "npu_demo"` 且存在唯一 wrapper 时，该 wrapper 指向的 body func 必须在 lowered module 内可达；缺失时必须显式失败。
  - pipeline lowering 的返回值必须是 `builtin.module`。
  - lowering 后若入口函数不满足当前 target 的公开 `gen_kernel(...)` 合同，`dsl_run(...)` 直接透传对应公开错误，不额外包装。
  - lowering 后残留的透明 `builtin.unrealized_conversion_cast` 允许由工具层源码生成自动吞掉。
  - `dump_dir` 由 `kernel_gen.core.config.set_dump_dir(...)` 配置；配置为 `None` 或空字符串时不写诊断文件，非空时按 `dump_dir/<kernel name>/` 写入诊断文件。
  - `kernel_gen.core.config.dump_dir` 非空时，`dsl_run(...)` 必须按 DSL 函数名创建 kernel 子目录，例如 `dump/add_kernel/`。
  - `kernel_gen.core.config.trance_enabled` 为 `True` 且 `dump_dir is None` 时，runtime trance 必须把日志输出到 stdout；日志至少包含 `in func: <entry> template=<none>`、`args =` 与真实运行参数摘要。
  - `kernel_gen.core.config.trance_enabled` 为 `True` 且 `dump_dir` 非空时，runtime trance 文件必须写入 `dump_dir/<kernel name>/<entry>_trace.txt`，其中 `<kernel name>` 是 DSL 函数名目录，`<entry>` 是执行引擎实际编译入口名；同名文件再次执行时必须覆盖旧内容。
  - runtime trance 只作为诊断输出，不改变 `DslRunResult` 字段、执行结果、源码文本或数学语义。
  - kernel 子目录内必须写入 `01-first-ir.mlir`，内容为 `mlir_gen(...)` 之后、pipeline 执行前的初始 alias IR。
  - 标准 `PassManager` pipeline 必须写入每个 pass 后的 `NN-<pass-name>.mlir`；文件第一行为 pass 名称文本，后续为 pass 后 IR。
  - 自定义 `PassManager` 子类若覆盖 `run(module)` 且不使用标准 config dump，工具层只保证写入初始 alias IR 与 `02-pipeline.mlir` 粗粒度 alias IR 结果。
  - `dump_dir/<kernel name>/*.mlir` 的 IR 正文默认使用 alias IR；普通 `str(op)`、raw attr/type 打印和比较工具默认文本不因 `dsl_run(...)` 改变。
  - 源码生成成功后必须由 `gen_kernel(...)` 的公开 dump 链路写入 `source.cpp`，内容与 `DslRunResult.source` 一致。
  - `dump_dir` 只用于诊断，不改变 `module/source/compile/execute` 正常路径语义。
  - 调用方不得依赖实现内部状态。

### `dsl_cost_run(func_obj: Callable[..., DslFunctionReturn], real_args: tuple[RuntimeRealArg, ...] | list[RuntimeRealArg], pipeline: str | PassManager, cost_kind: str) -> int`

- api：`dsl_cost_run(func_obj: Callable[..., DslFunctionReturn], real_args: tuple[RuntimeRealArg, ...] | list[RuntimeRealArg], pipeline: str | PassManager, cost_kind: str) -> int`
- 参数：
  - `func_obj`：函数对象；类型 `Callable[..., DslFunctionReturn]`；无默认值，调用方必须显式提供。
  - `real_args`：运行期真实实参序列；类型 `tuple[RuntimeRealArg, ...] | list[RuntimeRealArg]`；校验规则与 `dsl_run(...)` 一致。
  - `pipeline`：pass pipeline 名称或 `PassManager` 对象；类型 `str | PassManager`；校验规则与 `dsl_run(...)` 一致。
  - `cost_kind`：成本统计视角；类型 `str`；无默认值；只接受 `DMA1`、`DMA2`、`DMA3`、`DMA4`、`MAC`、`VECTOR1`、`VECTOR2`。
- 返回值：`int`，来自 `_cost_<cost_kind>_<device body>` sibling cost function 的 `S_INT` 返回值。
- 使用示例：

  ```python
  from kernel_gen.core.config import set_target
  from kernel_gen.operation import store
  from kernel_gen.tools.dsl_run import dsl_cost_run

  def add_kernel(out, lhs, rhs):
      store(out, lhs + rhs, [0], [128], [1])

  set_target("npu_demo")
  cost = dsl_cost_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering", "VECTOR1")
  assert isinstance(cost, int)
  ```
- 功能说明：执行 `dsl_cost_run` 工具入口，生成并执行 `npu_demo` cost sibling function。
- 注意事项：
  - `dsl_cost_run(...)` 不修改 `dsl_run(...)` 返回模型，不接受默认 `cost_kind`，也不在缺少 cost sibling 时 fallback 到普通 kernel。
  - `DMA1/DMA2/DMA3/DMA4` 返回同一 cost function 内匹配 DMA helper 的有效字节总和取整结果，即 `ceil(total_matching_bytes / 64)`。
  - DMA 聚合只允许通过 `dsl_cost_run(...)` 生成源码中的本地 raw-bytes helper 完成；生成源码和 include 公开层不得跨文件调用 `npu_demo::cost::detail` 非公开聚合状态。
  - target 只能是 `npu_demo`；其他 target 必须失败，固定短语为 `DslCostRunInvalidTarget: dsl_cost_run only supports target 'npu_demo'`。
  - 非法 `cost_kind` 必须失败，固定短语为 `DslCostRunInvalidCostKind: cost_kind must be one of ['DMA', 'MAC']`；`DMA1/DMA2/DMA3/DMA4/MAC/VECTOR1/VECTOR2` 仍作为 npu_demo 七类 kind 兼容执行。
  - lowering 后缺少目标 cost sibling 必须失败，固定短语前缀为 `DslCostRunMissingCostFunction:`。
  - cost 函数返回值通过工具层当前文件内部追加的捕获 wrapper 写入临时 `S_INT` 输出参数；该 wrapper 不作为执行引擎或 include 的公开 API。
  - `kernel_gen.core.config.trance_enabled` 为 `True` 时，cost 捕获 wrapper 必须在执行期间输出 `return = <cost>`；该输出只作为 runtime trance 诊断，不改变返回值或缺 sibling 失败语义。

## 测试

- 测试文件：
  - `test/tools/test_dsl_run.py`
  - `test/tools/test_dsl_cost_run.py`
  - `test/tools/test_package.py`
- 执行命令：`pytest -q test/tools/test_dsl_run.py test/tools/test_dsl_cost_run.py test/tools/test_package.py`

### 测试目标

- 验证 `tools/dsl_run` 的公开 API、边界与错误语义。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-TOOLS-DSL-RUN-001 | pass 改写 | DSL run string pipeline with torch numpy mix | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_dsl_run_string_pipeline_with_torch_numpy_mix`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“DSL run string pipeline with torch numpy mix”场景。 | `test_dsl_run_string_pipeline_with_torch_numpy_mix` |
| TC-TOOLS-DSL-RUN-002 | pass 改写 | DSL run dump dir writes alias pass IR and source | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_dsl_run_dump_dir_writes_pass_ir_and_source`。 | dump `.mlir` 文件使用 alias IR，源码文件内容与 `DslRunResult.source` 一致。 | `test_dsl_run_dump_dir_writes_pass_ir_and_source` |
| TC-TOOLS-DSL-RUN-003 | 执行结果 | DSL run empty dump dir disables dump | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_dsl_run_empty_dump_dir_disables_dump`。 | 命令返回码、输出、执行结果或状态变更体现“DSL run empty dump dir disables dump”场景。 | `test_dsl_run_empty_dump_dir_disables_dump` |
| TC-TOOLS-DSL-RUN-004 | pass 改写 | DSL run pass manager with list real args | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_dsl_run_pass_manager_with_list_real_args`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“DSL run pass manager with list real args”场景。 | `test_dsl_run_pass_manager_with_list_real_args` |
| TC-TOOLS-DSL-RUN-005 | 执行结果 | DSL run numpy output | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_dsl_run_numpy_output`。 | 命令返回码、输出、执行结果或状态变更体现“DSL run numpy output”场景。 | `test_dsl_run_numpy_output` |
| TC-TOOLS-DSL-RUN-006 | 公开入口 | DSL run add slice store matches public contract | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_dsl_run_add_slice_store_matches_public_contract`。 | 公开入口在“DSL run add slice store matches public contract”场景下可导入、构造、注册或按名称发现。 | `test_dsl_run_add_slice_store_matches_public_contract` |
| TC-TOOLS-DSL-RUN-007 | 公开入口 | DSL run add for loop matches public contract | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_dsl_run_add_for_loop_matches_public_contract`。 | 公开入口在“DSL run add for loop matches public contract”场景下可导入、构造、注册或按名称发现。 | `test_dsl_run_add_for_loop_matches_public_contract` |
| TC-TOOLS-DSL-RUN-008 | 公开入口 | DSL run sub matches public contract | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_dsl_run_sub_matches_public_contract`。 | 公开入口在“DSL run sub matches public contract”场景下可导入、构造、注册或按名称发现。 | `test_dsl_run_sub_matches_public_contract` |
| TC-TOOLS-DSL-RUN-009 | 公开入口 | DSL run mul matches public contract | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_dsl_run_mul_matches_public_contract`。 | 公开入口在“DSL run mul matches public contract”场景下可导入、构造、注册或按名称发现。 | `test_dsl_run_mul_matches_public_contract` |
| TC-TOOLS-DSL-RUN-010 | pass 改写 | DSL run supports tiled matmul kernel on npu demo | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_dsl_run_supports_tiled_matmul_kernel_on_npu_demo`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“DSL run supports tiled matmul kernel on npu demo”场景。 | `test_dsl_run_supports_tiled_matmul_kernel_on_npu_demo` |
| TC-TOOLS-DSL-RUN-011 | 边界/异常 | DSL run rejects npu demo module without unique wrapper | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dsl_run_rejects_npu_demo_module_without_unique_wrapper`。 | “DSL run rejects npu demo module without unique wrapper”场景按公开错误语义失败或被拒绝。 | `test_dsl_run_rejects_npu_demo_module_without_unique_wrapper` |
| TC-TOOLS-DSL-RUN-012 | 边界/异常 | DSL run rejects value return kernel | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dsl_run_rejects_value_return_kernel`。 | “DSL run rejects value return kernel”场景按公开错误语义失败或被拒绝。 | `test_dsl_run_rejects_value_return_kernel` |
| TC-TOOLS-DSL-RUN-013 | 边界/异常 | DSL run rejects missing operation helper import | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dsl_run_rejects_missing_operation_helper_import`。 | “DSL run rejects missing operation helper import”场景按公开错误语义失败或被拒绝。 | `test_dsl_run_rejects_missing_operation_helper_import` |
| TC-TOOLS-DSL-RUN-014 | 边界/异常 | DSL run rejects missing memory space import | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dsl_run_rejects_missing_memory_space_import`。 | “DSL run rejects missing memory space import”场景按公开错误语义失败或被拒绝。 | `test_dsl_run_rejects_missing_memory_space_import` |
| TC-TOOLS-DSL-RUN-015 | 边界/异常 | DSL run rejects missing core target | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dsl_run_rejects_missing_core_target`。 | “DSL run rejects missing core target”场景按公开错误语义失败或被拒绝。 | `test_dsl_run_rejects_missing_core_target` |
| TC-TOOLS-DSL-RUN-016 | 边界/异常 | DSL run rejects invalid core target type | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dsl_run_rejects_invalid_core_target_type`。 | “DSL run rejects invalid core target type”场景按公开错误语义失败或被拒绝。 | `test_dsl_run_rejects_invalid_core_target_type` |
| TC-TOOLS-DSL-RUN-017 | 边界/异常 | DSL run rejects unknown pipeline name | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dsl_run_rejects_unknown_pipeline_name`。 | “DSL run rejects unknown pipeline name”场景按公开错误语义失败或被拒绝。 | `test_dsl_run_rejects_unknown_pipeline_name` |
| TC-TOOLS-DSL-RUN-018 | 边界/异常 | DSL run rejects invalid pipeline type | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dsl_run_rejects_invalid_pipeline_type`。 | “DSL run rejects invalid pipeline type”场景按公开错误语义失败或被拒绝。 | `test_dsl_run_rejects_invalid_pipeline_type` |
| TC-TOOLS-DSL-RUN-019 | 边界/异常 | DSL run rejects invalid real args container | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dsl_run_rejects_invalid_real_args_container`。 | “DSL run rejects invalid real args container”场景按公开错误语义失败或被拒绝。 | `test_dsl_run_rejects_invalid_real_args_container` |
| TC-TOOLS-DSL-RUN-020 | 边界/异常 | DSL run rejects empty core target name | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dsl_run_rejects_empty_core_target_name`。 | “DSL run rejects empty core target name”场景按公开错误语义失败或被拒绝。 | `test_dsl_run_rejects_empty_core_target_name` |
| TC-TOOLS-DSL-RUN-021 | 边界/异常 | DSL run rejects unsupported runtime arg type | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dsl_run_rejects_unsupported_runtime_arg_type`。 | “DSL run rejects unsupported runtime arg type”场景按公开错误语义失败或被拒绝。 | `test_dsl_run_rejects_unsupported_runtime_arg_type` |
| TC-TOOLS-DSL-RUN-022 | 边界/异常 | DSL run rejects arity mismatch | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dsl_run_rejects_arity_mismatch`。 | “DSL run rejects arity mismatch”场景按公开错误语义失败或被拒绝。 | `test_dsl_run_rejects_arity_mismatch` |
| TC-TOOLS-DSL-RUN-023 | 边界/异常 | DSL run rejects pipeline returning empty module | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dsl_run_rejects_pipeline_returning_empty_module`。 | “DSL run rejects pipeline returning empty module”场景按公开错误语义失败或被拒绝。 | `test_dsl_run_rejects_pipeline_returning_empty_module` |
| TC-TOOLS-DSL-RUN-024 | 边界/异常 | DSL run rejects npu demo wrapper without body func | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dsl_run_rejects_npu_demo_wrapper_without_body_func`。 | “DSL run rejects npu demo wrapper without body func”场景按公开错误语义失败或被拒绝。 | `test_dsl_run_rejects_npu_demo_wrapper_without_body_func` |
| TC-TOOLS-DSL-RUN-025 | 边界/异常 | DSL run re raises codegen failure for cpu launch wrapper | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dsl_run_re_raises_codegen_failure_for_cpu_launch_wrapper`。 | “DSL run re raises codegen failure for cpu launch wrapper”场景按公开错误语义失败或被拒绝。 | `test_dsl_run_re_raises_codegen_failure_for_cpu_launch_wrapper` |
| TC-TOOLS-DSL-RUN-026 | 边界/异常 | DSL run rejects pipeline returning non module | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_dsl_run_rejects_pipeline_returning_non_module`。 | “DSL run rejects pipeline returning non module”场景按公开错误语义失败或被拒绝。 | `test_dsl_run_rejects_pipeline_returning_non_module` |
| TC-TOOLS-DSL-RUN-027 | 执行结果 | DSL run contract files exist | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_dsl_run_contract_files_exist`。 | 命令返回码、输出、执行结果或状态变更体现“DSL run contract files exist”场景。 | `test_dsl_run_contract_files_exist` |
| TC-TOOLS-DSL-RUN-028 | 公开入口 | tools package public exports | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_tools_package_public_exports`。 | 公开入口在“tools package public exports”场景下可导入、构造、注册或按名称发现。 | `test_tools_package_public_exports` |
| TC-TOOLS-DSL-RUN-029 | 公开入口 | tools package supports direct DSL run import | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_tools_package_supports_direct_dsl_run_import`。 | 公开入口在“tools package supports direct DSL run import”场景下可导入、构造、注册或按名称发现。 | `test_tools_package_supports_direct_dsl_run_import` |
| TC-TOOLS-DSL-RUN-030 | 边界/异常 | tools package rejects unknown public name | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_tools_package_rejects_unknown_public_name`。 | “tools package rejects unknown public name”场景按公开错误语义失败或被拒绝。 | `test_tools_package_rejects_unknown_public_name` |
| TC-TOOLS-DSL-RUN-031 | 执行结果 | DSL run accepts runtime scalar tile args | 准备带 `tile_*` 形参的公开 DSL kernel 和真实 torch/numpy 张量。 | 运行 `test_dsl_run_add_dynamic_tile_scalar_matches_public_contract`。 | `int` runtime tile 绑定到 `SymbolDim` 形参，生成并执行 npu_demo 链路。 | `test_dsl_run_add_dynamic_tile_scalar_matches_public_contract` |
| TC-TOOLS-DSL-RUN-032 | 边界/异常 | DSL run rejects non-positive tile scalar | 准备 `tile_*` 形参并传入 `0` 或负数。 | 运行 `test_dsl_run_rejects_non_positive_tile_runtime_scalar`。 | 按 `DslRunInvalidTileValue: tile runtime scalar must be positive int` 失败。 | `test_dsl_run_rejects_non_positive_tile_runtime_scalar` |
| TC-TOOLS-DSL-RUN-033 | 边界/异常 | DSL run empty function name uses kernel dump fallback | 设置 `dump_dir` 且 DSL 函数名为空，同时传入 arity 不匹配的公开参数。 | 运行 `test_dsl_run_empty_function_name_uses_kernel_dump_fallback`。 | `dsl_run(...)` 先稳定解析 dump 子目录 fallback，再按公开 arity 错误失败。 | `test_dsl_run_empty_function_name_uses_kernel_dump_fallback` |
| TC-TOOLS-DSL-RUN-034 | 边界/异常 | DSL run custom pipeline dump uses public fallback name | 设置 `dump_dir` 并传入覆盖 `run(...)`、名称为空的公开 `PassManager` 子类。 | 运行 `test_dsl_run_custom_pipeline_dump_uses_public_fallback_name`。 | 工具写出 alias `01-first-ir.mlir` 与 alias `02-pipeline.mlir`，pipeline dump 首行回退为 `pipeline`，后续 CPU 源码生成按公开错误失败。 | `test_dsl_run_custom_pipeline_dump_uses_public_fallback_name` |
| TC-TOOLS-DSL-RUN-035 | 边界/异常 | DSL run rejects target cleared after pipeline | 传入公开 `PassManager` 子类，在 `run(...)` 后使 core target 变为空字符串。 | 运行 `test_dsl_run_rejects_target_cleared_after_pipeline`。 | 源码生成入口按公开 target 错误 `DslRunInvalidTarget` 失败。 | `test_dsl_run_rejects_target_cleared_after_pipeline` |
| TC-TOOLS-DSL-RUN-036 | 边界/异常 | DSL run rejects unsupported numpy dtype | 传入 `numpy.ndarray` 且 dtype 不在 DSL `NumericType` 公开枚举中。 | 运行 `test_dsl_run_rejects_unsupported_numpy_dtype`。 | real_args 转换阶段按 `DslRunUnsupportedRealArg` 失败。 | `test_dsl_run_rejects_unsupported_numpy_dtype` |
| TC-TOOLS-DSL-RUN-037 | 边界/异常 | DSL run maps bfloat16 runtime dtype before pipeline validation | 传入 `torch.bfloat16` tensors 与返回非 module 的公开 `PassManager` 子类。 | 运行 `test_dsl_run_maps_bfloat16_runtime_dtype_before_pipeline_validation`。 | dtype 先映射为 DSL `bf16`，再按公开 pipeline 结果错误失败。 | `test_dsl_run_maps_bfloat16_runtime_dtype_before_pipeline_validation` |
| TC-TOOLS-DSL-RUN-038 | 执行结果 | DSL cost run returns VECTOR1 cost | 准备 npu_demo add kernel 与公开真实参数。 | 运行 `test_dsl_cost_run_returns_public_vector1_cost`。 | `dsl_cost_run(...)` 返回 `int` 且为当前 vector cost 公式的非零结果。 | `test_dsl_cost_run_returns_public_vector1_cost` |
| TC-TOOLS-DSL-RUN-039 | 执行结果 | DSL cost run returns DMA aggregate cost | 准备两路 GM->TSM slice 与一路 TSM->GM store，且单路字节数不能整除 64 的 npu_demo add kernel。 | 运行 `test_dsl_cost_run_returns_dma1_aggregate_cost`。 | `DMA1` 返回 `ceil((lhs_bytes + rhs_bytes) / 64)`，`DMA2` 返回 `ceil(out_bytes / 64)`。 | `test_dsl_cost_run_returns_dma1_aggregate_cost` |
| TC-TOOLS-DSL-RUN-040 | 边界/异常 | DSL cost run DMA source avoids private detail | 开启 `dump_dir` 并运行 DMA1 cost。 | 运行 `test_dsl_cost_run_dma_source_avoids_non_public_detail_helpers`。 | 生成源码不出现 `npu_demo::cost::detail`、`reset_dma_cost_accumulator` 或 `finalize_dma_cost_accumulator`。 | `test_dsl_cost_run_dma_source_avoids_non_public_detail_helpers` |
| TC-TOOLS-DSL-RUN-040A | 执行结果 | DSL cost run rank2 store layout compiles | 准备 rank=2 显式 `slice + add + store` kernel。 | 运行 `test_dsl_cost_run_compiles_rank2_store_vector_layout`。 | `DMA1/DMA2` 返回公开公式成本，生成源码中的普通 `store(...)` 行不再使用裸 `{..}` layout，并可真实编译执行。 | `test_dsl_cost_run_compiles_rank2_store_vector_layout` |
| TC-TOOLS-DSL-RUN-041 | 执行结果 | DSL cost run returns zero for VECTOR2 | 准备 npu_demo add kernel 与公开真实参数。 | 运行 `test_dsl_cost_run_returns_zero_for_vector2_reserved_kind`。 | `VECTOR2` 当前保留 kind 返回 `0`。 | `test_dsl_cost_run_returns_zero_for_vector2_reserved_kind` |
| TC-TOOLS-DSL-RUN-042 | 边界/异常 | DSL cost run rejects old cost kind | 传入旧 `compute` kind。 | 运行 `test_dsl_cost_run_rejects_old_cost_kind`。 | 按 `DslCostRunInvalidCostKind` 公开错误失败。 | `test_dsl_cost_run_rejects_old_cost_kind` |
| TC-TOOLS-DSL-RUN-043 | 公开入口 | tools package supports direct DSL cost run import | 从 `kernel_gen.tools` 包根导入 `dsl_cost_run`。 | 运行 `test_tools_package_supports_direct_dsl_cost_run_import`。 | 包根公开入口可达且指向可调用公开函数。 | `test_tools_package_supports_direct_dsl_cost_run_import` |
| TC-TOOLS-DSL-RUN-044 | 边界/异常 | DSL cost run rejects missing cost sibling without fallback | 准备不包含 `LaunchKernelCostFuncPass` 的公开 `PassManager` 链路。 | 运行 `test_dsl_cost_run_rejects_missing_cost_sibling_without_fallback`。 | 按 `DslCostRunMissingCostFunction` 公开错误失败，输出参数保持原值，不 fallback 到普通 kernel。 | `test_dsl_cost_run_rejects_missing_cost_sibling_without_fallback` |
| TC-TOOLS-DSL-RUN-045 | 边界/异常 | DSL cost run rejects non npu demo target | 通过公开 target 配置设置 `target="cpu"`。 | 运行 `test_dsl_cost_run_rejects_non_npu_demo_target`。 | 按 `DslCostRunInvalidTarget` 公开错误失败。 | `test_dsl_cost_run_rejects_non_npu_demo_target` |
| TC-TOOLS-DSL-RUN-046 | 执行结果 | DSL cost run accepts numpy torch mixed real args | 准备 `torch.Tensor` 输出、`numpy.ndarray` 输入和 `torch.Tensor` 输入。 | 运行 `test_dsl_cost_run_accepts_numpy_torch_mixed_real_args`。 | `dsl_cost_run(...)` 返回 `int` 且为当前 vector cost 公式的非零结果。 | `test_dsl_cost_run_accepts_numpy_torch_mixed_real_args` |
| TC-TOOLS-DSL-RUN-047 | 执行结果 | DSL run runtime trance stdout logs entry and args | 设置 `set_trance_enabled(True)` 且不设置 `dump_dir`，准备公开 add kernel 与真实运行参数。 | 运行 `test_dsl_run_trance_stdout_logs_entry_and_runtime_args`。 | stdout 包含 `in func:`、`template=<none>`、`args =` 和 `Memory` 参数摘要。 | `test_dsl_run_trance_stdout_logs_entry_and_runtime_args` |
| TC-TOOLS-DSL-RUN-048 | 执行结果 | DSL run runtime trance dump file writes and overwrites | 设置 `set_dump_dir(tmp_path)` 与 `set_trance_enabled(True)`，重复执行同一公开 kernel。 | 运行 `test_dsl_run_trance_dump_dir_writes_and_overwrites_trace_file`。 | `dump/<kernel>/<entry>_trace.txt` 存在并包含参数摘要；第二次执行覆盖旧文件内容。 | `test_dsl_run_trance_dump_dir_writes_and_overwrites_trace_file` |
| TC-TOOLS-DSL-RUN-049 | 执行结果 | DSL cost run runtime trance logs return value | 设置 `set_trance_enabled(True)`，执行 `dsl_cost_run(...)` 正向 VECTOR1 成本链路。 | 运行 `test_dsl_cost_run_trance_logs_return_value`。 | stdout 包含 `return = <cost>`，Python 返回值仍是同一 `int` 成本。 | `test_dsl_cost_run_trance_logs_return_value` |
