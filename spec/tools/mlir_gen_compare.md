# mlir_gen_compare.md

## 文档信息

- 创建者：`睡觉小分队`
- 最后一次更改：`金铲铲大作战`
- `spec`：[`spec/tools/mlir_gen_compare.md`](../../spec/tools/mlir_gen_compare.md)
- `功能实现`：[`kernel_gen/tools/mlir_gen_compare.py`](../../kernel_gen/tools/mlir_gen_compare.py)
- `test`：[`test/tools/test_mlir_gen_compare.py`](../../test/tools/test_mlir_gen_compare.py)

## 功能简介

- `mlir_gen_compare` 用来比较 `mlir_gen(...)` 产出的 `builtin.module` 与预期 `.mlir` 文件是否一致。
- 比较口径固定为“两边都先解析，再统一打印后比较字符串”。
- 只返回 `bool`；不执行 pass、不做 lowering、不输出 diff。

## API 列表

- `mlir_gen_compare(fn, runtime_args, config, mlir_file) -> bool`
- `mlir_gen_compare_text(fn, runtime_args, config, mlir_text) -> bool`
- `compare_mlir_file(fn, runtime_args, config, mlir_file) -> bool`

## 公开接口

### `mlir_gen_compare(fn, runtime_args, config, mlir_file) -> bool`

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
    config=None,
    mlir_file="expected/add.mlir",
)
assert ok is True
```

### `mlir_gen_compare_text(fn, runtime_args, config, mlir_text) -> bool`

- 语义与 `mlir_gen_compare(...)` 一致
- 区别只在 expected 来源是内存字符串，不是磁盘文件

### `compare_mlir_file(fn, runtime_args, config, mlir_file) -> bool`

- 旧兼容入口
- 行为等价于 `mlir_gen_compare(...)`

## 失败边界

- `mlir_gen(...)` 返回值不是 `builtin.module` -> `False`
- expected 文件读取失败或非 UTF-8 -> `False`
- expected 文本解析失败或解析结果不是 `builtin.module` -> `False`
- 归一化失败 -> `False`
- 归一化文本不一致 -> `False`
- `mlir_gen(...)` 自身抛错时，不重新包裹，直接向上传播

## 依赖

- `mlir_gen(...)`：[`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
- 默认解析上下文：[`kernel_gen/context.py`](../../kernel_gen/context.py)

## 测试

- 测试文件：[`test/tools/test_mlir_gen_compare.py`](../../test/tools/test_mlir_gen_compare.py)
- 执行命令：`pytest -q test/tools/test_mlir_gen_compare.py`
- 覆盖目标：
  - 一致时返回 `True`
  - 不一致或 expected 非法时返回 `False`
  - 旧兼容入口与主入口行为一致
