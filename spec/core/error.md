# core/error

## 功能简介

- 定义项目级公共错误底座，统一承载错误模块、错误类别和稳定消息文本。
- 定义 verifier / operation / target 校验错误复用的模板文字。
- 仓库内公开失败统一使用 `KernelCodeError`；不再新增或导出模块级专属错误类。

## API 列表

- `class ErrorModule()`
- `class ErrorKind()`
- `ERROR_TEMPLATE: str`
- `ERROR_ACTION: str`
- `ERROR_ACTUAL: str`
- `class KernelCodeError(kind: ErrorKind | str, module: ErrorModule | str, message: str)`
- `KernelCodeError.message() -> str`
- `KernelCodeError.kind() -> str`
- `KernelCodeError.module() -> str`
- `kernel_code_error(kind: ErrorKind | str, module: ErrorModule | str, message: str) -> KernelCodeError`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/core/error.md`](../../spec/core/error.md)
- `test`：[`test/core/test_error.py`](../../test/core/test_error.py)
- `功能实现`：[`kernel_gen/core/error.py`](../../kernel_gen/core/error.py)

## 依赖

- 无

## API详细说明

### `class ErrorModule()`

- api：`class ErrorModule()`
- 参数：无。
- 返回值：`ErrorModule` 枚举值。
- 使用示例：

  ```python
  from kernel_gen.core.error import ErrorModule

  assert ErrorModule.PASS == "pass"
  ```
- 功能说明：定义项目通用错误模块枚举。
- 注意事项：稳定模块集合为 `ast`、`mlir_gen`、`dialect`、`gen_kernel`、`operation`、`pass`、`pipeline`、`target`、`tools`、`execute_engine`；枚举内部实现细节不作为公开 API。

### `class ErrorKind()`

- api：`class ErrorKind()`
- 参数：无。
- 返回值：`ErrorKind` 枚举值。
- 使用示例：

  ```python
  from kernel_gen.core.error import ErrorKind

  assert ErrorKind.UNIMPLEMENTED == "unimplemented"
  ```
- 功能说明：定义项目通用错误类别枚举。
- 注意事项：稳定类别集合为 `index_out_of_range`、`invalid_value`、`unimplemented`、`contract`、`unsupported`、`verify`、`internal`；枚举内部实现细节不作为公开 API。

### `ERROR_TEMPLATE: str`

- api：`ERROR_TEMPLATE: str`
- 参数：无。
- 返回值：统一错误模板字符串。
- 使用示例：

  ```python
  from kernel_gen.core.error import ERROR_ACTION, ERROR_ACTUAL, ERROR_TEMPLATE

  message = ERROR_TEMPLATE.format(
      scene="dma.alloc 参数校验",
      expected="shape must be a dimension sequence",
      actual=ERROR_ACTUAL,
      action=ERROR_ACTION,
  )
  ```
- 功能说明：提供统一错误模板字符串，保证错误信息字段顺序一致。
- 注意事项：固定文本为 `"场景: {scene}; 期望: {expected}; 实际: {actual}; 建议动作: {action}"`；调用方只能通过公开常量读取，不得在业务模块重复定义下划线前缀的本地模板文本变量。

### `ERROR_ACTION: str`

- api：`ERROR_ACTION: str`
- 参数：无。
- 返回值：统一错误建议动作默认文本。
- 使用示例：

  ```python
  from kernel_gen.core.error import ERROR_ACTION

  assert ERROR_ACTION == "请按接口约束传参"
  ```
- 功能说明：提供统一错误建议动作默认文本。
- 注意事项：固定文本为 `"请按接口约束传参"`；调用方只能通过公开常量读取，不得在业务模块重复定义下划线前缀的本地模板文本变量。

### `ERROR_ACTUAL: str`

- api：`ERROR_ACTUAL: str`
- 参数：无。
- 返回值：统一错误实际值默认文本。
- 使用示例：

  ```python
  from kernel_gen.core.error import ERROR_ACTUAL

  assert ERROR_ACTUAL == "不满足期望"
  ```
- 功能说明：提供统一错误实际值默认文本。
- 注意事项：固定文本为 `"不满足期望"`；调用方只能通过公开常量读取，不得在业务模块重复定义下划线前缀的本地模板文本变量。

### `class KernelCodeError(kind: ErrorKind | str, module: ErrorModule | str, message: str)`

- api：`class KernelCodeError(kind: ErrorKind | str, module: ErrorModule | str, message: str)`
- 参数：
  - `kind`：错误类别；类型 `ErrorKind | str`；无默认值，调用方必须显式提供；不允许 `None` 或空值；字符串输入按公开枚举名或枚举值规范化；非法值抛出 `ValueError`。
  - `module`：错误来源模块；类型 `ErrorModule | str`；无默认值，调用方必须显式提供；不允许 `None` 或空值；字符串输入按公开枚举名或枚举值规范化；非法值抛出 `ValueError`。
  - `message`：诊断或错误消息文本，用于构造稳定错误或校验输出；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`KernelCodeError` 实例。
- 使用示例：

  ```python
  from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError

  err = KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "invalid pass input")
  assert str(err) == "invalid pass input"
  ```
- 功能说明：承载稳定错误类别、来源模块和消息文本。
- 注意事项：`str(err)` 必须直接返回传入的 `message`；`kind()`、`module()`、`message()` 返回规范化后的字符串值；构造函数不接受 `**metadata` 或其他额外关键字，调用方不得把 `location`、`diagnostics`、`failure_phrase`、`detail` 等上下文作为参数传入；`message_text` 保留原始消息文本，禁止通过额外构造参数覆盖 `message`、`kind`、`module` 等公开方法名。

### `KernelCodeError.message() -> str`

- api：`KernelCodeError.message() -> str`
- 参数：无。
- 返回值：`str`，表示生成或格式化后的文本。
- 使用示例：

  ```python
  from kernel_gen.core.error import KernelCodeError

  err = KernelCodeError("contract", "pass", "invalid pass input")
  result = err.message()
  ```
- 功能说明：返回稳定错误消息文本。
- 注意事项：返回值必须等于构造函数传入的 `message`；内部字段不作为公开可变入口。

### `KernelCodeError.kind() -> str`

- api：`KernelCodeError.kind() -> str`
- 参数：无。
- 返回值：`str`，表示生成或格式化后的文本。
- 使用示例：

  ```python
  from kernel_gen.core.error import KernelCodeError

  err = KernelCodeError("CONTRACT", "pass", "invalid pass input")
  result = err.kind()
  ```
- 功能说明：返回稳定错误类别。
- 注意事项：返回值必须是规范化后的字符串枚举值；内部字段不作为公开可变入口。

### `KernelCodeError.module() -> str`

- api：`KernelCodeError.module() -> str`
- 参数：无。
- 返回值：`str`，表示生成或格式化后的文本。
- 使用示例：

  ```python
  from kernel_gen.core.error import KernelCodeError

  err = KernelCodeError("contract", "PASS", "invalid pass input")
  result = err.module()
  ```
- 功能说明：返回稳定错误来源模块。
- 注意事项：返回值必须是规范化后的字符串枚举值；内部字段不作为公开可变入口。

### `kernel_code_error(kind: ErrorKind | str, module: ErrorModule | str, message: str) -> KernelCodeError`

- api：`kernel_code_error(kind: ErrorKind | str, module: ErrorModule | str, message: str) -> KernelCodeError`
- 参数：
  - `kind`：错误类别；类型 `ErrorKind | str`；无默认值，调用方必须显式提供；不允许 `None` 或空值；字符串输入按公开枚举名或枚举值规范化；非法值抛出 `ValueError`。
  - `module`：错误来源模块；类型 `ErrorModule | str`；无默认值，调用方必须显式提供；不允许 `None` 或空值；字符串输入按公开枚举名或枚举值规范化；非法值抛出 `ValueError`。
  - `message`：诊断或错误消息文本，用于构造稳定错误或校验输出；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`KernelCodeError`。
- 使用示例：

  ```python
  from kernel_gen.core.error import ErrorKind, ErrorModule, kernel_code_error

  err = kernel_code_error(ErrorKind.CONTRACT, ErrorModule.PASS, "invalid pass input")
  assert isinstance(err, Exception)
  ```
- 功能说明：提供统一公共错误构造入口。
- 注意事项：返回值必须是 `KernelCodeError`；参数规范化、非法类别和非法模块的失败语义与 `KernelCodeError(...)` 一致。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 模块内部和对外公开失败都应使用 `KernelCodeError(kind, module, message)` 表达，不得再新增模块级专属错误类。
- 复用错误模板文字时，只能从本文件 API 列表中的 `ERROR_TEMPLATE`、`ERROR_ACTION`、`ERROR_ACTUAL` 读取；不得在业务模块重复定义下划线前缀的本地模板文本变量。
- 非公开 helper 仅允许存在于本文件内部，禁止跨文件调用。
- `message()`、`kind()`、`module()` 是对外稳定接口；不要求外部直接读取内部字段。
- 允许继续保留历史稳定错误短语作为 `message` 内容的一部分，但错误对象类型必须是 `KernelCodeError`。

## 测试

- 测试文件：`test/core/test_error.py`
- 执行命令：`pytest -q test/core/test_error.py`

### 测试目标

- 验证 `spec/core/error.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证非法输入、边界条件和错误语义按公开合同失败。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-CORE-ERROR-001 | 边界/异常 | error module values | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_error_module_values`。 | “error module values”场景按公开错误语义失败或被拒绝。 | `test_error_module_values` |
| TC-CORE-ERROR-002 | 边界/异常 | error kind values | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_error_kind_values`。 | “error kind values”场景按公开错误语义失败或被拒绝。 | `test_error_kind_values` |
| TC-CORE-ERROR-003 | 边界/异常 | error template text values | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_error_template_text_values`。 | “error template text values”场景按公开错误语义失败或被拒绝。 | `test_error_template_text_values` |
| TC-CORE-ERROR-004 | 边界/异常 | kernel code error methods and str | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_kernel_code_error_methods_and_str`。 | “kernel code error methods and str”场景按公开错误语义失败或被拒绝。 | `test_kernel_code_error_methods_and_str` |
| TC-CORE-ERROR-005 | 边界/异常 | kernel code error factory | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_kernel_code_error_factory`。 | “kernel code error factory”场景按公开错误语义失败或被拒绝。 | `test_kernel_code_error_factory` |
| TC-CORE-ERROR-006 | 边界/异常 | kernel code error string normalization | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_kernel_code_error_string_normalization`。 | “kernel code error string normalization”场景按公开错误语义失败或被拒绝。 | `test_kernel_code_error_string_normalization` |
| TC-CORE-ERROR-007 | 边界/异常 | kernel code error rejects unknown kind or module | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_kernel_code_error_rejects_unknown_kind_or_module`。 | “kernel code error rejects unknown kind or module”场景按公开错误语义失败或被拒绝。 | `test_kernel_code_error_rejects_unknown_kind_or_module` |
