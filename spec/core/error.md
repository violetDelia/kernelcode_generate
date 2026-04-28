# core/error

## 功能简介

- 定义项目级公共错误底座，统一承载错误模块、错误类别、稳定消息文本和少量诊断 metadata。
- 仓库内公开失败统一使用 `KernelCodeError`；不再新增或导出模块级专属错误类。

## API 列表

- `class ErrorModule()`
- `class ErrorKind()`
- `class KernelCodeError(kind: ErrorKind | str, module: ErrorModule | str, message: str, **metadata: object)`
- `KernelCodeError.message() -> str`
- `KernelCodeError.kind() -> str`
- `KernelCodeError.module() -> str`
- `kernel_code_error(kind: ErrorKind | str, module: ErrorModule | str, message: str, **metadata: object) -> KernelCodeError`

## 文档信息

- 创建者：`OpenAI Codex`
- 最后一次更改：`OpenAI Codex`
- `spec`：[`spec/core/error.md`](../../spec/core/error.md)
- `test`：[`test/core/test_error.py`](../../test/core/test_error.py)
- `功能实现`：[`kernel_gen/core/error.py`](../../kernel_gen/core/error.py)

## 依赖

- 无

## 公开接口

### `class ErrorModule()`

功能说明：

- 公开项目通用错误模块枚举。
- 当前稳定模块集合为：
  - `ast`
  - `mlir_gen`
  - `dialect`
  - `gen_kernel`
  - `operation`
  - `pass`
  - `pipeline`
  - `target`
  - `tools`
  - `execute_engine`

使用示例：

```python
from kernel_gen.core.error import ErrorModule

assert ErrorModule.PASS == "pass"
```

### `class ErrorKind()`

功能说明：

- 公开项目通用错误类别枚举。
- 当前稳定类别集合为：
  - `index_out_of_range`
  - `invalid_value`
  - `unimplemented`
  - `contract`
  - `unsupported`
  - `verify`
  - `internal`

使用示例：

```python
from kernel_gen.core.error import ErrorKind

assert ErrorKind.UNIMPLEMENTED == "unimplemented"
```

### `class KernelCodeError(kind: ErrorKind | str, module: ErrorModule | str, message: str, **metadata: object)`

功能说明：

- 承载稳定错误类别、来源模块和消息文本。
- `str(err)` 必须直接返回传入的 `message`。
- `kind()`、`module()`、`message()` 是对外稳定读取接口，返回规范化后的字符串值。
- `**metadata` 用于承载 `location`、`diagnostics`、`failure_phrase` 等诊断字段，并以同名只读属性形式挂到错误对象上。
- `message_text` 保留原始消息文本；禁止用 metadata 覆盖 `message`、`kind`、`module` 等公开方法名。

使用示例：

```python
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError

err = KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "invalid pass input")
assert str(err) == "invalid pass input"
assert err.kind() == "contract"
assert err.module() == "pass"
assert err.message() == "invalid pass input"

located = KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, "parse failed", location="line 1")
assert located.location == "line 1"
```

### `kernel_code_error(kind: ErrorKind | str, module: ErrorModule | str, message: str, **metadata: object) -> KernelCodeError`

功能说明：

- 提供统一公共错误构造入口。
- 返回值必须是 `KernelCodeError`。

使用示例：

```python
from kernel_gen.core.error import ErrorKind, ErrorModule, kernel_code_error

err = kernel_code_error(ErrorKind.CONTRACT, ErrorModule.PASS, "invalid pass input")
assert isinstance(err, Exception)
assert err.kind() == "contract"
```

## 限制与边界

- 模块内部和对外公开失败都应使用 `KernelCodeError(kind, module, message, **metadata)` 表达，不得再新增模块级专属错误类。
- 非公开 helper 仅允许存在于本文件内部，禁止跨文件调用。
- `message()`、`kind()`、`module()` 是对外稳定接口；不要求外部直接读取内部字段。
- 允许继续保留历史稳定错误短语作为 `message` 内容的一部分，但错误对象类型必须是 `KernelCodeError`。

## 测试

- 测试文件：[`test/core/test_error.py`](../../test/core/test_error.py)
- 执行命令：`pytest -q test/core/test_error.py`
- 测试目标：
  - 验证 `ErrorModule`、`ErrorKind` 的稳定枚举值。
  - 验证 `KernelCodeError` 的 `message()/kind()/module()` 与 `str(err)` 行为。
  - 验证 metadata 会透传为错误对象属性。
  - 验证 `kernel_code_error(...)` 返回统一错误类型。
  - 验证非法模块名或类别名会稳定失败。
