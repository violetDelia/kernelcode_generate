# mlir_gen_compare.md

## 文档信息

- 创建者：`睡觉小分队`
- 最后一次更改：`榕`
- `spec`：[`spec/tools/mlir_gen_compare.md`](../../spec/tools/mlir_gen_compare.md)
- `功能实现`：[`kernel_gen/tools/mlir_gen_compare.py`](../../kernel_gen/tools/mlir_gen_compare.py)
- `test`：[`test/tools/test_mlir_gen_compare.py`](../../test/tools/test_mlir_gen_compare.py)

## 功能简介

- `mlir_gen_compare` 用来比较 `mlir_gen(...)` 产出的 `builtin.module` 与预期 `.mlir` 文件是否一致。
- 比较口径固定为“两边都先解析，再统一打印后比较字符串”。
- 只返回 `bool`；不执行 pass、不做 lowering、不输出 diff。
- 工具层只依赖公开 `mlir_gen(fn, *runtime_args)`；若当前文件保留延迟加载或文本归一化 helper，它们都不是公开 API。
- expected 文本与实际 module 的解析 Context 必须复用 `kernel_gen.core.context.build_default_context()`；不得在本工具内维护第二套 dialect 注册列表。默认 Context 必须覆盖 `scf.if` 这类 mlir_gen 公开可能产出的控制流 op。

## API 列表

- `mlir_gen_compare(fn: Callable[..., object], runtime_args: tuple[object, ...] | list[object] | None, mlir_file: str) -> bool`
- `mlir_gen_compare_text(fn: Callable[..., object], runtime_args: tuple[object, ...] | list[object] | None, mlir_text: str) -> bool`
- `compare_mlir_file(fn: Callable[..., object], runtime_args: tuple[object, ...] | list[object] | None, mlir_file: str) -> bool`

## 公开接口

### `mlir_gen_compare(fn, runtime_args, mlir_file) -> bool`

功能说明：

- 用 `mlir_gen(...)` 生成实际 module
- 读取并解析 `mlir_file`
- 对两边做同一套归一化比较

使用示例：

```python
from kernel_gen.tools.mlir_gen_compare import mlir_gen_compare

ok = mlir_gen_compare(
    fn=add,
    runtime_args=[lhs, rhs],
    mlir_file="expected/add.mlir",
)
assert ok is True
```

### `mlir_gen_compare_text(fn, runtime_args, mlir_text) -> bool`

- 语义与 `mlir_gen_compare(...)` 一致
- 区别只在 expected 来源是内存字符串，不是磁盘文件

### `compare_mlir_file(fn, runtime_args, mlir_file) -> bool`

- 旧兼容入口
- 行为等价于 `mlir_gen_compare(...)`

## 失败边界

- `mlir_gen(...)` 返回值不是 `builtin.module` -> `False`
- expected 文件读取失败或非 UTF-8 -> `False`
- expected 文本解析失败或解析结果不是 `builtin.module` -> `False`
- 归一化失败 -> `False`
- 归一化文本不一致 -> `False`
- `mlir_gen(...)` 自身抛错时，不重新包裹，直接向上传播
- `_mlir_gen_compare_expected_text(...)`、`_build_compare_context(...)` 与 `_normalize_module_text(...)` 只允许作为当前文件内 helper 存在；实现、工具与测试不得跨文件把这些 helper 当成公开 API

## 依赖

- `mlir_gen(...)`：[`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)

## 测试

- 测试文件：[`test/tools/test_mlir_gen_compare.py`](../../test/tools/test_mlir_gen_compare.py)
- 执行命令：`pytest -q test/tools/test_mlir_gen_compare.py`
- 覆盖目标：
  - 一致时返回 `True`
  - 不一致或 expected 非法时返回 `False`
  - 旧兼容入口与主入口行为一致
  - 测试只通过 `mlir_gen_compare(...)`、`mlir_gen_compare_text(...)`、`compare_mlir_file(...)` 观察公开行为，不直接依赖当前文件内 helper
