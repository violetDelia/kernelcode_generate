# dsl_run.md

## 文档信息

- 创建者：`朽木露琪亚`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/tools/dsl_run.md`](../../spec/tools/dsl_run.md)
- `功能实现`：[`kernel_gen/tools/dsl_run.py`](../../kernel_gen/tools/dsl_run.py)
- `test`：[`test/tools/test_dsl_run.py`](../../test/tools/test_dsl_run.py)

## 功能简介

- `dsl_run(func, real_args, pipeline, emitcconfig)` 是面向测试和脚本的单入口工具。
- 负责串起 `mlir_gen -> pass/pipeline -> gen_kernel -> ExecutionEngine.compile/execute`。
- 公开合同只覆盖这条一体化路径，不扩展到无关 pass、无关 dialect、无关工具。
- `kernel_gen.tools` 包根稳定暴露 `DslRunError`、`DslRunResult` 与属性入口 `kernel_gen.tools.dsl_run(...)`，不把 `dsl_run` 子模块对象当作公开合同。

## API 列表

- `DslRunError(message: str)`
- `DslRunResult(func_op: func.FuncOp, module: ModuleOp, source: str, compiled_kernel: CompiledKernel, execute_result: ExecuteResult, runtime_args: tuple[object, ...])`
- `dsl_run(func_obj, real_args, pipeline, emitcconfig) -> DslRunResult`

## 导入约定

- 直接模块入口：`from kernel_gen.tools.dsl_run import DslRunError, DslRunResult, dsl_run`
- 包根稳定入口：`import kernel_gen.tools as tools`，再使用 `tools.DslRunError`、`tools.DslRunResult`、`tools.dsl_run(...)`
- 包根稳定导入：`from kernel_gen.tools import DslRunError, DslRunResult, dsl_run`

## helper 清单

- `_runtime_module_name(value: object) -> str`
- `_is_torch_tensor(value: object) -> bool`
- `_is_numpy_array(value: object) -> bool`
- `_build_dsl_globals_table(fn: Callable[..., object]) -> dict[str, object]`
- `_normalize_real_args(real_args: tuple[object, ...] | list[object]) -> tuple[object, ...]`
- `_resolve_pipeline(pipeline: str | PassManager) -> PassManager`
- `_find_first_func(module: ModuleOp) -> func.FuncOp`
- `_find_func_by_sym_name(module: ModuleOp, sym_name: str) -> func.FuncOp`
- `_select_source_and_entry(module: ModuleOp, emitcconfig: EmitCContext) -> tuple[str, str, func.FuncOp]`

## 使用示例

```python
from kernel_gen.dsl.gen_kernel import EmitCContext
from kernel_gen.tools.dsl_run import dsl_run


def add_kernel(out, lhs, rhs):
    store(lhs + rhs, out, [0], [6], [1])


result = dsl_run(
    add_kernel,
    (out, lhs, rhs),
    "npu-demo-lowering",
    EmitCContext(config={"target": "npu_demo"}),
)
assert result.execute_result.ok is True
```

## 输入与失败边界

- `emitcconfig` 仅接受 `EmitCContext`
- `emitcconfig.config["target"]` 必须是非空 `str`；若调用方在构造后篡改该字段，`dsl_run(...)` 仍必须在公开入口显式失败
- `pipeline` 仅接受 `str | PassManager`
- `real_args` 容器仅接受 `tuple | list`，元素仅允许 `torch.Tensor` 或 `numpy.ndarray`
- DSL 函数只要存在值返回，就必须失败
- `emitcconfig.config["target"]` 决定源码生成与执行目标，不做跨 target 自动猜测
- `target == "npu_demo"` 时，lowered module 必须包含且仅包含一个带 `arch.launch` 的 wrapper func；否则必须显式失败
- `target == "npu_demo"` 且存在唯一 wrapper 时，该 wrapper 指向的 body func 必须在 lowered module 内可达；缺失时必须显式失败
- pipeline lowering 的返回值必须是 `builtin.module`
- lowering 后若入口函数不满足当前 target 的公开 `gen_kernel(...)` 合同，`dsl_run(...)` 直接透传对应公开错误，不额外包装
- lowering 后残留的透明 `builtin.unrealized_conversion_cast` 允许由工具层源码生成自动吞掉

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
  - `torch` / `numpy` 参数归一化
  - `real_args` 非 `tuple/list` 与空 `target` 边界
  - `npu_demo` wrapper 唯一性失败边界
  - pipeline 返回空 / 非 `builtin.module`、wrapper 缺 body func 与公开 codegen 失败透传
  - 固定错误短语
