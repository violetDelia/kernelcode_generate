# mlir_gen_compare.md

## 功能简介

- 定义一个面向 `mlir_gen(...)` 产物的轻量比较工具：对同一 Python 函数生成的 `builtin.module` 与磁盘 `.mlir` 文件进行“解析后再打印”的归一化比较，并返回 `bool`。
- 该工具用于写可机械判定的期望：一致返回 `True`，不一致返回 `False`；不提供 diff 对象，也不跑 pass。

## 文档信息

- 创建者：`睡觉小分队`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/tools/mlir_gen_compare.md`](../../spec/tools/mlir_gen_compare.md)
- `功能实现`：[`kernel_gen/tools/mlir_gen_compare.py`](../../kernel_gen/tools/mlir_gen_compare.py)
- `test`：[`test/tools/test_mlir_gen_compare.py`](../../test/tools/test_mlir_gen_compare.py)

## 依赖

- module 生成入口（actual）：[`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
- 依赖的实现模块（actual）：[`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py)
- IR 解析与打印（归一化比较）：[`kernel_gen/context.py`](../../kernel_gen/context.py)
- 默认解析上下文加载的 dialect（至少）：
  - `xdsl.dialects.builtin` / `xdsl.dialects.func` / `xdsl.dialects.arith`
  - `kernel_gen.dialect.nn` / `kernel_gen.dialect.kernel` / `kernel_gen.dialect.symbol`
  - `kernel_gen.dialect.dma` / `kernel_gen.dialect.arch`

## 目标

- 让“函数 -> module IR -> 与预期 `.mlir` 对照”的比较口径在工具层收敛为一个公开函数，避免下游重复手写：
  - 手工组装 module
  - 手工打印字符串再比对
  - 因空白/注释/缩进不同导致的误报

## 限制与边界

- 只比较 `mlir_gen(...)` 层的 module 结果；不执行 pass、不做 lowering、不做源码生成。
- 只返回 `bool`；不返回 diff、也不打印差异文本。
- 比较的输入必须是完整 `builtin.module`：
  - expected 来自 `mlir_file` 文件内容
  - actual 来自 `mlir_gen(...)` 的返回值

## 公开接口

### `compare_mlir_file(fn, runtime_args, config, mlir_file) -> bool`

功能说明：

- 使用 `mlir_gen(...)` 生成 `builtin.module`（actual）。
- 读取 `mlir_file` 并解析为 `builtin.module`（expected）。
- 对 actual 与 expected 分别做“解析后再打印”的归一化，比较两边规范化文本是否完全一致。

参数说明：

- `fn` (`callable`)：待比较的根函数。
- `runtime_args` (`tuple[object, ...] | list[object] | None`)：
  - 传给 `mlir_gen(fn, *runtime_args, config=config)` 的根函数运行时参数。
  - `None` 等价于空参数列表，仅适用于零入参函数。
- `config` (`dict[str, object] | None`)：透传给 `mlir_gen(...)` 的配置。
- `mlir_file` (`str`)：预期 `.mlir` 文件路径；文件内容必须是完整 `builtin.module`。

使用示例：

```python
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType
from kernel_gen.tools.mlir_gen_compare import compare_mlir_file


def add(lhs: "Tensor[i32, 4]", rhs: "Tensor[i32, 4]") -> "Tensor[i32, 4]":
    return lhs + rhs


ok = compare_mlir_file(
    fn=add,
    runtime_args=[Memory([4], NumericType.Int32), Memory([4], NumericType.Int32)],
    config=None,
    mlir_file="expected/add.mlir",
)
assert ok is True
```

```python
from pathlib import Path

mlir_file = str(Path(__file__).with_name("add_expected.mlir"))
ok = compare_mlir_file(
    fn=add,
    runtime_args=[Memory([4], NumericType.Int32), Memory([4], NumericType.Int32)],
    config=None,
    mlir_file=mlir_file,
)
assert ok is True
```

注意事项：

- 建议将调用入口脚本与对应 `.mlir` 预期文件放在同一目录中，并通过相对路径或 `__file__` 拼出 `mlir_file`。
- 比较流程必须对两边使用同一套“解析 + 打印”归一化口径；不得直接比较原始文件文本。
- `mlir_file` 读入失败、解析失败，或解析结果不是 `builtin.module` 时，必须返回 `False`。
- 若 `mlir_gen(...)` 返回值不是 `builtin.module`，必须返回 `False`。
- 归一化后的文本不一致时，必须返回 `False`。
- 归一化过程中的二次解析失败（例如 dialect 未注册导致的解析失败）也必须返回 `False`。
- 上述返回 `False` 的分支不要求提供稳定的错误短语；若下游需要诊断对象，应通过新增并列接口承载。
- `mlir_gen(...)` 的失败语义不由本函数重新定义：若 `mlir_gen(...)` 抛错，本函数应直接向上传播。

返回与限制：

- 返回 `True`：actual 与 expected 的归一化文本完全一致。
- 返回 `False`：`mlir_gen(...)` 返回值不是 `builtin.module`，或 `mlir_file` 不可读/不可解析/不是 `builtin.module`，或归一化后的文本不一致。

## 测试

- 测试文件：[`test/tools/test_mlir_gen_compare.py`](../../test/tools/test_mlir_gen_compare.py)
- 执行命令：`pytest -q test/tools/test_mlir_gen_compare.py`
- 测试目标：
  - 一致时返回 `True`
  - 不一致时返回 `False`
  - expected 不是 `builtin.module` 时返回 `False`
  - expected 解析失败时返回 `False`
