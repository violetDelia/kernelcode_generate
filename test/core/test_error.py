"""core error tests.

创建者: OpenAI Codex
最后一次更改: OpenAI Codex

功能说明:
- 覆盖 `kernel_gen.core.error` 中公共错误底座的枚举值、消息文本和统一构造入口。

使用示例:
- pytest -q test/core/test_error.py

关联文件:
- 功能实现: [kernel_gen/core/error.py](../../kernel_gen/core/error.py)
- Spec 文档: [spec/core/error.md](../../spec/core/error.md)
- 测试文件: [test/core/test_error.py](../../test/core/test_error.py)
"""

from __future__ import annotations

from kernel_gen.core.error import KernelCodeError
from kernel_gen.core.error import ErrorKind, ErrorModule, kernel_code_error


# CE-001
# 创建者: OpenAI Codex
# 最后一次更改: OpenAI Codex
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 验证 ErrorModule 的稳定公开枚举值保持不变。
# 使用示例: pytest -q test/core/test_error.py -k test_error_module_values
# 对应功能实现文件路径: kernel_gen/core/error.py
# 对应 spec 文件路径: spec/core/error.md
# 对应测试文件路径: test/core/test_error.py
def test_error_module_values() -> None:
    assert ErrorModule.AST == "ast"
    assert ErrorModule.MLIR_GEN == "mlir_gen"
    assert ErrorModule.DIALECT == "dialect"
    assert ErrorModule.GEN_KERNEL == "gen_kernel"
    assert ErrorModule.OPERATION == "operation"
    assert ErrorModule.PASS == "pass"
    assert ErrorModule.PIPELINE == "pipeline"
    assert ErrorModule.TARGET == "target"
    assert ErrorModule.TOOLS == "tools"
    assert ErrorModule.EXECUTE_ENGINE == "execute_engine"


# CE-002
# 创建者: OpenAI Codex
# 最后一次更改: OpenAI Codex
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 验证 ErrorKind 的稳定公开枚举值保持不变。
# 使用示例: pytest -q test/core/test_error.py -k test_error_kind_values
# 对应功能实现文件路径: kernel_gen/core/error.py
# 对应 spec 文件路径: spec/core/error.md
# 对应测试文件路径: test/core/test_error.py
def test_error_kind_values() -> None:
    assert ErrorKind.INDEX_OUT_OF_RANGE == "index_out_of_range"
    assert ErrorKind.INVALID_VALUE == "invalid_value"
    assert ErrorKind.UNIMPLEMENTED == "unimplemented"
    assert ErrorKind.CONTRACT == "contract"
    assert ErrorKind.UNSUPPORTED == "unsupported"
    assert ErrorKind.VERIFY == "verify"
    assert ErrorKind.INTERNAL == "internal"


# CE-003
# 创建者: OpenAI Codex
# 最后一次更改: OpenAI Codex
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 验证 KernelCodeError 会稳定返回 message/kind/module，并让 str(err) 等于 message。
# 使用示例: pytest -q test/core/test_error.py -k test_kernel_code_error_methods_and_str
# 对应功能实现文件路径: kernel_gen/core/error.py
# 对应 spec 文件路径: spec/core/error.md
# 对应测试文件路径: test/core/test_error.py
def test_kernel_code_error_methods_and_str() -> None:
    err = KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "invalid pass input", location="line 1")

    assert err.kind() == "contract"
    assert err.module() == "pass"
    assert err.message() == "invalid pass input"
    assert err.message_text == "invalid pass input"
    assert err.location == "line 1"
    assert str(err) == "invalid pass input"


# CE-004
# 创建者: OpenAI Codex
# 最后一次更改: OpenAI Codex
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 验证 kernel_code_error(...) 会返回统一错误类型，并接受公开枚举输入。
# 使用示例: pytest -q test/core/test_error.py -k test_kernel_code_error_factory
# 对应功能实现文件路径: kernel_gen/core/error.py
# 对应 spec 文件路径: spec/core/error.md
# 对应测试文件路径: test/core/test_error.py
def test_kernel_code_error_factory() -> None:
    err = kernel_code_error(ErrorKind.UNIMPLEMENTED, ErrorModule.GEN_KERNEL, "not implemented")

    assert isinstance(err, KernelCodeError)
    assert err.kind() == "unimplemented"
    assert err.module() == "gen_kernel"
    assert err.message() == "not implemented"


# CE-005
# 创建者: OpenAI Codex
# 最后一次更改: OpenAI Codex
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 验证字符串输入会按名称和值两种形式做规范化。
# 使用示例: pytest -q test/core/test_error.py -k test_kernel_code_error_string_normalization
# 对应功能实现文件路径: kernel_gen/core/error.py
# 对应 spec 文件路径: spec/core/error.md
# 对应测试文件路径: test/core/test_error.py
def test_kernel_code_error_string_normalization() -> None:
    err = KernelCodeError("CONTRACT", "PASS", "normalized")

    assert err.kind() == "contract"
    assert err.module() == "pass"
    assert err.message() == "normalized"


# CE-006
# 创建者: OpenAI Codex
# 最后一次更改: OpenAI Codex
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 验证非法 kind 或 module 会稳定失败。
# 使用示例: pytest -q test/core/test_error.py -k test_kernel_code_error_rejects_unknown_kind_or_module
# 对应功能实现文件路径: kernel_gen/core/error.py
# 对应 spec 文件路径: spec/core/error.md
# 对应测试文件路径: test/core/test_error.py
def test_kernel_code_error_rejects_unknown_kind_or_module() -> None:
    import pytest

    with pytest.raises(ValueError, match="unknown error kind: weird"):
        KernelCodeError("weird", ErrorModule.PASS, "bad kind")

    with pytest.raises(ValueError, match="unknown error module: weird"):
        KernelCodeError(ErrorKind.CONTRACT, "weird", "bad module")
