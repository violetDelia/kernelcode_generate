"""Project-wide common error definitions.

创建者: OpenAI Codex
最后一次更改: 大闸蟹

功能说明:
- 定义项目级公共错误底座，统一承载错误模块、错误类别和稳定消息文本。
- 定义可复用的错误模板文本，供 verifier / operation / target 校验错误复用。
- 仓库内公开失败统一使用 `KernelCodeError`；不再新增模块级错误类。

API 列表:
- `ERROR_TEMPLATE: str`
- `ERROR_ACTION: str`
- `ERROR_ACTUAL: str`
- `class ErrorModule()`
- `class ErrorKind()`
- `class KernelCodeError(kind: ErrorKind | str, module: ErrorModule | str, message: str)`
- `KernelCodeError.message() -> str`
- `KernelCodeError.kind() -> str`
- `KernelCodeError.module() -> str`
- `kernel_code_error(kind: ErrorKind | str, module: ErrorModule | str, message: str) -> KernelCodeError`

使用示例:
- from kernel_gen.core.error import ErrorKind, ErrorModule, kernel_code_error
- err = kernel_code_error(ErrorKind.CONTRACT, ErrorModule.PASS, "symbol.for body must end with symbol.yield")
- assert err.kind() == "contract"
- assert err.module() == "pass"
- assert err.message() == "symbol.for body must end with symbol.yield"

关联文件:
- spec: [spec/core/error.md](../../spec/core/error.md)
- test: [test/core/test_error.py](../../test/core/test_error.py)
- 功能实现: [kernel_gen/core/error.py](../../kernel_gen/core/error.py)
"""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "ERROR_TEMPLATE",
    "ERROR_ACTION",
    "ERROR_ACTUAL",
    "ErrorModule",
    "ErrorKind",
    "KernelCodeError",
    "kernel_code_error",
]

ERROR_TEMPLATE = "场景: {scene}; 期望: {expected}; 实际: {actual}; 建议动作: {action}"
ERROR_ACTION = "请按接口约束传参"
ERROR_ACTUAL = "不满足期望"


class ErrorModule(StrEnum):
    """项目通用错误模块枚举。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 统一约束项目公共错误的来源模块。
    - 为后续不同子系统并入公共错误底座提供稳定模块集合。

    使用示例:
    - assert ErrorModule.PASS == "pass"
    """

    AST = "ast"
    MLIR_GEN = "mlir_gen"
    DIALECT = "dialect"
    GEN_KERNEL = "gen_kernel"
    OPERATION = "operation"
    PASS = "pass"
    PIPELINE = "pipeline"
    TARGET = "target"
    TOOLS = "tools"
    EXECUTE_ENGINE = "execute_engine"


class ErrorKind(StrEnum):
    """项目通用错误类别枚举。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 统一约束项目公共错误的语义类别。
    - 避免后续用大量细碎异常子类表达可枚举的错误含义。

    使用示例:
    - assert ErrorKind.UNIMPLEMENTED == "unimplemented"
    """

    INDEX_OUT_OF_RANGE = "index_out_of_range"
    INVALID_VALUE = "invalid_value"
    UNIMPLEMENTED = "unimplemented"
    CONTRACT = "contract"
    UNSUPPORTED = "unsupported"
    VERIFY = "verify"
    INTERNAL = "internal"


def _normalize_error_module(module: ErrorModule | str) -> str:
    """把模块输入规范化为稳定字符串。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 接受 `ErrorModule` 或字符串模块名。
    - 对字符串输入做大小写和名称规范化，失败时抛出 `ValueError`。

    使用示例:
    - assert _normalize_error_module(ErrorModule.PASS) == "pass"
    - assert _normalize_error_module("PASS") == "pass"
    """

    if isinstance(module, ErrorModule):
        return module.value
    normalized = module.strip().lower()
    for candidate in ErrorModule:
        if normalized in {candidate.value, candidate.name.lower()}:
            return candidate.value
    raise ValueError(f"unknown error module: {module}")


def _normalize_error_kind(kind: ErrorKind | str) -> str:
    """把错误类别输入规范化为稳定字符串。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 接受 `ErrorKind` 或字符串类别名。
    - 对字符串输入做大小写和名称规范化，失败时抛出 `ValueError`。

    使用示例:
    - assert _normalize_error_kind(ErrorKind.CONTRACT) == "contract"
    - assert _normalize_error_kind("CONTRACT") == "contract"
    """

    if isinstance(kind, ErrorKind):
        return kind.value
    normalized = kind.strip().lower()
    for candidate in ErrorKind:
        if normalized in {candidate.value, candidate.name.lower()}:
            return candidate.value
    raise ValueError(f"unknown error kind: {kind}")


class KernelCodeError(TypeError, ValueError):
    """项目通用错误类型。

    创建者: OpenAI Codex
    最后一次更改: 大闸蟹

    功能说明:
    - 统一承载项目公共错误的模块、类别和稳定消息文本。
    - 仓库内公开失败必须直接抛出本类型，不再定义模块级错误子类。
    - 同时归入 `TypeError` / `ValueError` 异常族，兼容历史 expectation 对参数错误族的断言。

    使用示例:
    - err = KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "invalid pass input")
    - assert err.kind() == "contract"
    """

    def __init__(
        self,
        kind: ErrorKind | str,
        module: ErrorModule | str,
        message: str,
    ) -> None:
        """构造项目公共错误实例。

        创建者: OpenAI Codex
        最后一次更改: 大闸蟹

        功能说明:
        - 规范化模块和类别字段。
        - 把稳定 `message` 注册为异常主文本，保证 `str(err)` 可直接用于公开错误消息。

        使用示例:
        - err = KernelCodeError("contract", "pass", "invalid pass input")
        - assert str(err) == "invalid pass input"
        """

        self._kind = _normalize_error_kind(kind)
        self._module = _normalize_error_module(module)
        self._message = message
        self.message_text = message
        super().__init__(message)

    def message(self) -> str:
        """返回稳定错误消息文本。

        创建者: OpenAI Codex
        最后一次更改: OpenAI Codex

        功能说明:
        - 提供项目统一的消息读取接口。

        使用示例:
        - err = KernelCodeError("contract", "pass", "invalid pass input")
        - assert err.message() == "invalid pass input"
        """

        return self._message

    def kind(self) -> str:
        """返回稳定错误类别。

        创建者: OpenAI Codex
        最后一次更改: OpenAI Codex

        功能说明:
        - 提供项目统一的错误类别读取接口，返回规范化后的字符串值。

        使用示例:
        - err = KernelCodeError("contract", "pass", "invalid pass input")
        - assert err.kind() == "contract"
        """

        return self._kind

    def module(self) -> str:
        """返回稳定错误来源模块。

        创建者: OpenAI Codex
        最后一次更改: OpenAI Codex

        功能说明:
        - 提供项目统一的模块读取接口，返回规范化后的字符串值。

        使用示例:
        - err = KernelCodeError("contract", "pass", "invalid pass input")
        - assert err.module() == "pass"
        """

        return self._module


def kernel_code_error(
    kind: ErrorKind | str,
    module: ErrorModule | str,
    message: str,
) -> KernelCodeError:
    """构造项目通用错误对象。

    创建者: OpenAI Codex
    最后一次更改: 大闸蟹

    功能说明:
    - 提供统一的公共错误构造入口。
    - 供各模块在未来逐步替换本地错误类型时直接复用。

    使用示例:
    - err = kernel_code_error(ErrorKind.CONTRACT, ErrorModule.PASS, "invalid pass input")
    - assert isinstance(err, KernelCodeError)
    """

    return KernelCodeError(kind, module, message)
