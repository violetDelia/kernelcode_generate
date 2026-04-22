# case_runner.md

## 功能简介

- 定义 `kernel_gen.tools.case_runner` 的轻量 case 汇总合同。
- 提供两个稳定 helper：单 case 执行收集 `run_case(...)` 和失败统一汇总 `raise_if_failures(...)`。
- 用于工具型测试、case 驱动脚本与后续逐步迁入的 public tool 逻辑，不依赖 expectation 路径。

## 文档信息

- 创建者：`金铲铲大作战`
- 最后一次更改：`金铲铲大作战`
- `spec`：[`spec/tools/case_runner.md`](../../spec/tools/case_runner.md)
- `功能实现`：[`kernel_gen/tools/case_runner.py`](../../kernel_gen/tools/case_runner.py)
- `test`：[`test/tools/test_case_runner.py`](../../test/tools/test_case_runner.py)

## 公开接口

### `run_case(failures, case_name, case_fn) -> None`

功能说明：

- 执行 `case_fn`。
- 成功时不改动 `failures`。
- 捕获普通异常并追加 `(case_name, exc)`。

参数说明：

- `failures(list[tuple[str, BaseException]])`：用于累计失败 case 的列表。
- `case_name(str)`：case 名称，必须非空。
- `case_fn(callable)`：待执行的 case 函数。

使用示例：

```python
failures: list[tuple[str, BaseException]] = []
run_case(failures, "CASE-1", lambda: None)
```

### `raise_if_failures(title, failures) -> None`

功能说明：

- `failures` 为空时直接返回。
- `failures` 非空时抛出 `AssertionError`，错误文本包含 case 数量和逐条失败摘要。

参数说明：

- `title(str)`：失败摘要标题。
- `failures(list[tuple[str, BaseException]])`：case 失败收集结果。

使用示例：

```python
raise_if_failures("tile reduce example", failures)
```

## 测试

- 测试文件：[`test/tools/test_case_runner.py`](../../test/tools/test_case_runner.py)
- 执行命令：`pytest -q test/tools/test_case_runner.py`
- 测试目标：
  - 成功 case 不修改失败列表。
  - 普通异常被收集到失败列表。
  - 失败摘要格式稳定。
  - 非法参数显式报错。
