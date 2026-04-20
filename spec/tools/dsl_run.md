# dsl_run.md

## 功能简介

- 定义 `dsl_run(func, real_args, pipeline, emitcconfig)` 的一体化公开合同。
- 该工具负责把 DSL 函数解析为 `builtin.module`，按指定 pipeline 做 lowering，再生成源码并交给执行引擎真实编译/执行。
- 该规范只收口 `dsl_run` 本身，不扩展到无关 pass、无关 dialect 或其他工具入口。

## 文档信息

- 创建者：`朽木露琪亚`
- 最后一次更改：`朽木露琪亚`
- `spec`：[`spec/tools/dsl_run.md`](../../spec/tools/dsl_run.md)
- `功能实现`：[`kernel_gen/tools/dsl_run.py`](../../kernel_gen/tools/dsl_run.py)
- `test`：[`test/tools/test_dsl_run.py`](../../test/tools/test_dsl_run.py)

## 依赖

- DSL 解析入口：[`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
- 函数源码生成：[`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
- C++ 运行时编译与执行：[`spec/execute_engine/execute_engine.md`](../../spec/execute_engine/execute_engine.md)
- Pass 管理器：[`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)
- Pass / pipeline 注册：[`spec/pass/registry.md`](../../spec/pass/registry.md)
- target 当前态读取：[`spec/target/registry.md`](../../spec/target/registry.md)
- DSL helper 命名空间：[`spec/operation/arch.md`](../../spec/operation/arch.md)、[`spec/operation/dma.md`](../../spec/operation/dma.md)、[`spec/operation/nn.md`](../../spec/operation/nn.md)、[`spec/operation/scf.md`](../../spec/operation/scf.md)

## 目标

- 提供一个最小而完整的工具入口，让 expectation 和 pytest 不再分别拼装 parse / pipeline / gen / execute 链路。
- 让 `dsl_run` 的输入输出合同稳定、可机械比较，并把失败短语收口到固定字符串。
- 让 `dsl_run` 可直接处理 `expectation/tools/dsl_run` 中的正向与反向样例。

## 限制与边界

- `emitcconfig` 仅接受 `EmitCContext`。
- `pipeline` 仅接受 `str | PassManager`。
- `real_args` 仅接受 `list | tuple`，并且元素只允许 `torch.Tensor` 或 `numpy.ndarray`。
- DSL 函数只要存在值返回，就必须失败。
- `DslRunError` 继承 `ValueError`，用于稳定收口公开失败短语。
- `DslRunResult.runtime_args` 必须保持为 tuple。
- `dsl_run` 会根据 `emitcconfig.target` 决定源码生成与执行目标，不做跨 target 的自动猜测。
- lowering 链路可能残留透明的 `builtin.unrealized_conversion_cast`，工具层代码生成会自动吞掉这一层包装。
- 需要 `lower-dma-memory-hierarchy` 的 pipeline 依赖当前 target 提供 `sm_memory_size` 与 `lm_memory_size`。

## 公开接口

### `DslRunError`

- 类型：`ValueError`
- 用途：`dsl_run` 的公开失败基类，便于 expectation 和 pytest 直接做机械匹配。

### `DslRunResult`

- 字段：
  - `func_op`: 选中的 `func.func`
  - `module`: lowering 后的 `builtin.module`
  - `source`: 生成的源码字符串
  - `compiled_kernel`: `ExecutionEngine.compile(...)` 的编译产物
  - `execute_result`: 执行返回结果
  - `runtime_args`: 规整后的运行时参数 tuple
- 说明：
  - `DslRunResult` 只承载一次执行的结果，不承担缓存、重放或差异分析职责。

### `dsl_run(func_obj, real_args, pipeline, emitcconfig) -> DslRunResult`

功能说明：

- 先校验 `emitcconfig`，再规整 `real_args` 并解析 `pipeline`。
- 使用 `mlir_gen(...)` 生成 `builtin.module`。
- 若 DSL 函数存在值返回，立即失败。
- 对 module 执行指定 pipeline。
- 以 `gen_kernel(...)` 生成源码，并交给 `ExecutionEngine` 真实编译与执行。
- 将 `func_op`、`module`、`source`、`compiled_kernel`、`execute_result`、`runtime_args` 一并返回。

参数说明：

- `func_obj`：待执行的 DSL 根函数。
- `real_args`：根函数的真实运行时参数，支持 `tuple` 与 `list`。
- `pipeline`：`PassManager` 实例或已注册 pipeline 名称。
- `emitcconfig`：必须是 `EmitCContext`。

返回说明：

- 返回 `DslRunResult`。
- 若输入不满足合同，抛出 `DslRunError`，并使用固定错误短语。

使用示例：

```python
from kernel_gen.dsl.emit_c import EmitCContext
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

## Expectation 口径

- `expectation/tools/dsl_run/add.py` 覆盖正向合同：
  - 字符串 pipeline，正向主合同使用 `npu-demo-lowering`
  - `PassManager` pipeline
  - `torch.Tensor` 与 `numpy.ndarray` 的混合运行时参数
  - `numpy.ndarray` 输出位
- `expectation/tools/dsl_run/invalid_contract.py` 覆盖反向合同：
  - 值返回函数失败
  - 错误 `emitcconfig` 失败
  - 未知 pipeline 失败
  - 非法 `pipeline` 类型失败
  - 非法 runtime 参数类型失败
  - runtime 参数数量不匹配失败

## 测试

- 测试文件：[`test/tools/test_dsl_run.py`](../../test/tools/test_dsl_run.py)
- 执行命令：`pytest -q test/tools/test_dsl_run.py`
- 测试目标：
  - `dsl_run` 正向链路可执行并返回完整结果
  - `PassManager` 与字符串 pipeline 行为一致
  - 错误输入会返回固定短语
  - `runtime_args` 保持 tuple 口径
