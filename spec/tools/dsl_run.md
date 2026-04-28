# dsl_run.md

## 文档信息

- 创建者：`朽木露琪亚`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/tools/dsl_run.md`](../../spec/tools/dsl_run.md)
- `功能实现`：[`kernel_gen/tools/dsl_run.py`](../../kernel_gen/tools/dsl_run.py)
- `test`：[`test/tools/test_dsl_run.py`](../../test/tools/test_dsl_run.py)

## 功能简介

- `dsl_run(func, real_args, pipeline)` 是面向测试和脚本的单入口工具。
- 负责串起 `mlir_gen -> pass/pipeline -> gen_kernel -> ExecutionEngine.compile/execute`。
- 公开合同只覆盖这条一体化路径，不扩展到无关 pass、无关 dialect、无关工具。
- `kernel_gen.tools` 包根稳定暴露 `DslRunResult` 与属性入口 `kernel_gen.tools.dsl_run(...)`，不把 `dsl_run` 子模块对象当作公开合同。
- 诊断落盘根目录统一来自 `kernel_gen.core.config.set_dump_dir(...)`，不作为 `dsl_run(...)` 入参。
- 失败统一抛出 `KernelCodeError(ErrorModule.TOOLS, message)`；不再定义或导出工具专属错误类。

## API 列表

- `DslRunResult(func_op: func.FuncOp, module: ModuleOp, source: str, compiled_kernel: CompiledKernel, execute_result: ExecuteResult, runtime_args: tuple[object, ...])`
- `dsl_run(func_obj, real_args, pipeline) -> DslRunResult`

## 导入约定

- 直接模块入口：`from kernel_gen.tools.dsl_run import DslRunResult, dsl_run`
- 包根稳定入口：`import kernel_gen.tools as tools`，再使用 `tools.DslRunResult`、`tools.dsl_run(...)`
- 包根稳定导入：`from kernel_gen.tools import DslRunResult, dsl_run`

## helper 清单

- `_runtime_module_name(value: object) -> str`
- `_is_torch_tensor(value: object) -> bool`
- `_is_numpy_array(value: object) -> bool`
- `_sanitize_dump_component(value: str) -> str`
- `_resolve_dump_kernel_dir(func_obj: Callable[..., object]) -> Path | None`
- `_write_dump_file(path: Path, content: str) -> None`
- `_build_dsl_globals_table(fn: Callable[..., object]) -> dict[str, object]`
- `_normalize_real_args(real_args: tuple[object, ...] | list[object]) -> tuple[object, ...]`
- `_resolve_pipeline(pipeline: str | PassManager) -> PassManager`
- `_pipeline_uses_config_dump(pipeline: PassManager) -> bool`
- `_run_pipeline_with_optional_dump(pipeline: PassManager, module: ModuleOp, dump_dir: Path | None) -> object`
- `_find_first_func(module: ModuleOp) -> func.FuncOp`
- `_find_func_by_sym_name(module: ModuleOp, sym_name: str) -> func.FuncOp`
- `_select_source_and_entry(module: ModuleOp, emit_context: EmitCContext) -> tuple[str, str, func.FuncOp]`

## 使用示例

```python
from kernel_gen.core.config import set_dump_dir, set_target
from kernel_gen.tools.dsl_run import dsl_run


def add_kernel(out, lhs, rhs):
    store(out, lhs + rhs, [0], [6], [1])


set_target("npu_demo")
result = dsl_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering")
set_dump_dir("dump")
result = dsl_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering")
assert result.execute_result.ok is True
```

## 输入与失败边界

- target 只能来自 `kernel_gen.core.config.get_target()`；未设置或不是非空 `str` 时必须失败，固定短语为 `DslRunInvalidTarget: core config target must be non-empty str`
- `pipeline` 仅接受 `str | PassManager`
- `dump_dir` 由 `kernel_gen.core.config.set_dump_dir(...)` 配置；配置为 `None` 或空字符串时不写诊断文件，非空时按 `dump_dir/<kernel name>/` 写入诊断文件
- `real_args` 容器仅接受 `tuple | list`，元素仅允许 `torch.Tensor` 或 `numpy.ndarray`
- DSL 函数只要存在值返回，就必须失败
- `core.config.target` 决定源码生成与执行目标，不做跨 target 自动猜测
- `target == "npu_demo"` 时，lowered module 必须包含且仅包含一个带 `arch.launch` 的 wrapper func；否则必须显式失败
- `target == "npu_demo"` 且存在唯一 wrapper 时，该 wrapper 指向的 body func 必须在 lowered module 内可达；缺失时必须显式失败
- pipeline lowering 的返回值必须是 `builtin.module`
- lowering 后若入口函数不满足当前 target 的公开 `gen_kernel(...)` 合同，`dsl_run(...)` 直接透传对应公开错误，不额外包装
- lowering 后残留的透明 `builtin.unrealized_conversion_cast` 允许由工具层源码生成自动吞掉

## dump_dir 诊断产物

- `kernel_gen.core.config.dump_dir` 非空时，`dsl_run(...)` 必须按 DSL 函数名创建 kernel 子目录，例如 `dump/add_kernel/`。
- `kernel_gen.core.config.dump_dir` 为 `None` 或空字符串时，`dsl_run(...)` 不得创建诊断目录或 dump 文件。
- kernel 子目录内必须写入 `01-first-ir.mlir`，内容为 `mlir_gen(...)` 之后、pipeline 执行前的初始 IR。
- 标准 `PassManager` pipeline 必须写入每个 pass 后的 `NN-<pass-name>.mlir`；文件第一行为 pass 名称文本，后续为 pass 后 IR。
- 自定义 `PassManager` 子类若覆盖 `run(module)` 且不使用标准 config dump，工具层只保证写入初始 IR 与 `02-pipeline.mlir` 粗粒度结果。
- 源码生成成功后必须由 `gen_kernel(...)` 的公开 dump 链路写入 `source.cpp`，内容与 `DslRunResult.source` 一致。
- `dump_dir` 只用于诊断，不改变 `module/source/compile/execute` 正常路径语义。

## 依赖

- DSL 解析：[`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
- 源码生成：[`spec/dsl/gen_kernel/gen_kernel.md`](../../spec/dsl/gen_kernel/gen_kernel.md)
- 执行引擎：[`spec/execute_engine/execute_engine.md`](../../spec/execute_engine/execute_engine.md)
- pass / pipeline：[`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)、[`spec/pass/registry.md`](../../spec/pass/registry.md)

## 测试

- 测试文件：[`test/tools/test_dsl_run.py`](../../test/tools/test_dsl_run.py)
- 包根公开入口测试：[`test/tools/test_package_api.py`](../../test/tools/test_package_api.py)
- 执行命令：`pytest -q test/tools/test_dsl_run.py`
- 覆盖目标：
  - 正向执行与结果模型
  - `str` / `PassManager` 两类 pipeline 入口
  - `dump_dir` 目录结构、pass IR 与最终源码落盘
  - `torch` / `numpy` 参数归一化
  - `real_args` 非 `tuple/list` 与空 `target` 边界
  - `npu_demo` wrapper 唯一性失败边界
  - pipeline 返回空 / 非 `builtin.module`、wrapper 缺 body func 与公开 codegen 失败透传
  - 固定错误短语
