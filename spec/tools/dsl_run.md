# dsl_run.md

## 文档信息

- 创建者：`朽木露琪亚`
- 最后一次更改：`金铲铲大作战`
- `spec`：[`spec/tools/dsl_run.md`](../../spec/tools/dsl_run.md)
- `功能实现`：[`kernel_gen/tools/dsl_run.py`](../../kernel_gen/tools/dsl_run.py)
- `test`：[`test/tools/test_dsl_run.py`](../../test/tools/test_dsl_run.py)

## 功能简介

- `dsl_run(func, real_args, pipeline, emitcconfig)` 是面向测试和脚本的单入口工具。
- 负责串起 `mlir_gen -> pass/pipeline -> gen_kernel -> ExecutionEngine.compile/execute`。
- 公开合同只覆盖这条一体化路径，不扩展到无关 pass、无关 dialect、无关工具。

## API 列表

- `DslRunError`
- `DslRunResult`
- `dsl_run(func_obj, real_args, pipeline, emitcconfig) -> DslRunResult`

## 公开接口

### `DslRunError`

- 类型：`ValueError`
- 用途：收口 `dsl_run(...)` 的公开失败短语。

### `DslRunResult`

- 字段：
  - `func_op`
  - `module`
  - `source`
  - `compiled_kernel`
  - `execute_result`
  - `runtime_args`
- 约束：
  - `runtime_args` 必须保持为 `tuple`
  - 只承载一次执行结果，不承担缓存或 diff 分析职责

### `dsl_run(func_obj, real_args, pipeline, emitcconfig) -> DslRunResult`

功能说明：

- 先校验 `emitcconfig`、`real_args`、`pipeline`
- 用 `mlir_gen(...)` 生成 `builtin.module`
- 对 module 执行指定 pipeline
- 用 `gen_kernel(...)` 生成源码
- 交给 `ExecutionEngine` 真实编译与执行
- 返回 `DslRunResult`

使用示例：

```python
from kernel_gen.dsl.gen_kernel import EmitCContext
from kernel_gen.tools.dsl_run import dsl_run


def add_kernel(out, lhs, rhs):
    store(lhs + rhs, out, [0], [6], [1])


result = dsl_run(
    add_kernel,
    (out, lhs, rhs),
    "npu-demo-lowering",
    EmitCContext(target="npu_demo"),
)
assert result.execute_result.ok is True
```

## 输入与失败边界

- `emitcconfig` 仅接受 `EmitCContext`
- `pipeline` 仅接受 `str | PassManager`
- `real_args` 仅接受 `tuple | list`，元素仅允许 `torch.Tensor` 或 `numpy.ndarray`
- DSL 函数只要存在值返回，就必须失败
- `emitcconfig.target` 决定源码生成与执行目标，不做跨 target 自动猜测
- `target == "npu_demo"` 时，lowered module 必须包含且仅包含一个带 `arch.launch` 的 wrapper func；否则必须显式失败
- lowering 后残留的透明 `builtin.unrealized_conversion_cast` 允许由工具层源码生成自动吞掉

## 依赖

- DSL 解析：[`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
- 源码生成：[`spec/dsl/gen_kernel/gen_kernel.md`](../../spec/dsl/gen_kernel/gen_kernel.md)
- 执行引擎：[`spec/execute_engine/execute_engine.md`](../../spec/execute_engine/execute_engine.md)
- pass / pipeline：[`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)、[`spec/pass/registry.md`](../../spec/pass/registry.md)

## 测试

- 测试文件：[`test/tools/test_dsl_run.py`](../../test/tools/test_dsl_run.py)
- 执行命令：`pytest -q test/tools/test_dsl_run.py`
- 覆盖目标：
  - 正向执行与结果模型
  - `str` / `PassManager` 两类 pipeline 入口
  - `torch` / `numpy` 参数归一化
  - `npu_demo` wrapper 唯一性失败边界
  - 固定错误短语
