"""core.print tests.

功能说明:
- 覆盖 `kernel_gen.core.print.print_operation_with_aliases(...)` 的公开 alias 打印合同。
- 验证 alias IR 可重新解析，且 raw attr/type 打印不被污染。

使用示例:
- pytest -q test/core/test_print.py

关联文件:
- spec: [spec/core/print.md](../../spec/core/print.md)
- 功能实现: [kernel_gen/core/print.py](../../kernel_gen/core/print.py)
- test: [test/core/test_print.py](../../test/core/test_print.py)
"""

from __future__ import annotations

from io import StringIO

import pytest
from xdsl.dialects.builtin import ModuleOp
from xdsl.parser import Parser
from xdsl.printer import Printer

from kernel_gen.core.context import build_default_context
from kernel_gen.core.print import print_operation_with_aliases
from kernel_gen.dialect.symbol import SymbolValueType


def _parse_module(source_ir: str) -> ModuleOp:
    """解析完整 module IR。

    功能说明:
    - 复用公开 `build_default_context()` 构造 parser 上下文。

    使用示例:
    - module = _parse_module("builtin.module {}")
    """

    parsed = Parser(build_default_context(), source_ir).parse_module()
    assert isinstance(parsed, ModuleOp)
    return parsed


def _module_body(alias_ir: str) -> str:
    """提取 alias IR 的 module 正文。

    功能说明:
    - 便于断言正文不残留长形态 symbol attr。

    使用示例:
    - body = _module_body(alias_ir)
    """

    return alias_ir.split("builtin.module", 1)[1]


def _print_attribute_text(value: SymbolValueType) -> str:
    """用 xDSL 公开 Printer 打印 symbol type。

    功能说明:
    - 检查 raw attr/type 打印未受 alias printer 污染。

    使用示例:
    - text = _print_attribute_text(SymbolValueType.from_expr("N"))
    """

    stream = StringIO()
    Printer(stream=stream).print_attribute(value)
    return stream.getvalue()


# TC-CORE-PRINT-001
# 测试目的: 验证 core.print 公开入口可直接导入。
# 使用示例: pytest -q test/core/test_print.py -k test_print_operation_with_aliases_public_import
# 对应功能实现文件路径: kernel_gen/core/print.py
# 对应 spec 文件路径: spec/core/print.md
# 对应测试文件路径: test/core/test_print.py
def test_print_operation_with_aliases_public_import() -> None:
    assert callable(print_operation_with_aliases)


# TC-CORE-PRINT-002
# 测试目的: 验证常量、单符号和复杂 symbol expr 会生成 alias，且输出可 round-trip parse。
# 使用示例: pytest -q test/core/test_print.py -k test_print_operation_with_aliases_aliases_symbol_exprs_and_round_trips
# 对应功能实现文件路径: kernel_gen/core/print.py
# 对应 spec 文件路径: spec/core/print.md
# 对应测试文件路径: test/core/test_print.py
def test_print_operation_with_aliases_aliases_symbol_exprs_and_round_trips() -> None:
    module = _parse_module(
        """
builtin.module {
  func.func @alias_exprs(%n : !symbol.int<#symbol.expr<N>>, %m : !symbol.int<#symbol.expr<N + 1>>) {
    %zero = "symbol.const"() {value = #builtin.int<0>} : () -> !symbol.int<#symbol.expr<0>>
    %step = "symbol.const"() {value = #builtin.int<2>} : () -> !symbol.int<#symbol.expr<2>>
    func.return
  }
}
"""
    )

    actual = print_operation_with_aliases(module)

    assert "#C0 = #symbol.expr<0>" in actual
    assert "#C2 = #symbol.expr<2>" in actual
    assert "#S_N = #symbol.expr<N>" in actual
    assert "#S1 = #symbol.expr<N + 1>" in actual
    assert "!symbol.int<#S_N>" in actual
    assert "!symbol.int<#S1>" in actual
    assert "#symbol.expr<" not in _module_body(actual)
    _parse_module(actual)


# TC-CORE-PRINT-003
# 测试目的: 验证 symbol.iter attr 会生成 #It alias 且正文不展开 iter 长形态。
# 使用示例: pytest -q test/core/test_print.py -k test_print_operation_with_aliases_aliases_symbol_iter
# 对应功能实现文件路径: kernel_gen/core/print.py
# 对应 spec 文件路径: spec/core/print.md
# 对应测试文件路径: test/core/test_print.py
def test_print_operation_with_aliases_aliases_symbol_iter() -> None:
    module = _parse_module(
        """
builtin.module {
  func.func @alias_iter(%end : !symbol.int<#symbol.expr<N>>) {
    %start = "symbol.const"() {value = #builtin.int<0>} : () -> !symbol.int<#symbol.expr<0>>
    %step = "symbol.const"() {value = #builtin.int<1>} : () -> !symbol.int<#symbol.expr<1>>
    "symbol.for"(%start, %end, %step) ({
    ^bb0(%i: !symbol.iter<start = #symbol.expr<0>, end = #symbol.expr<N>, step = #symbol.expr<1>>):
    }) {iter = #symbol.iter<start = #symbol.expr<0>, end = #symbol.expr<N>, step = #symbol.expr<1>>} : (!symbol.int<#symbol.expr<0>>, !symbol.int<#symbol.expr<N>>, !symbol.int<#symbol.expr<1>>) -> ()
    func.return
  }
}
"""
    )

    actual = print_operation_with_aliases(module)
    body = _module_body(actual)

    assert "#It1 = #symbol.iter<start = #C0, end = #S_N, step = #C1>" in actual
    assert "iter = #It1" in body
    assert "#symbol.iter<" not in body
    assert "#symbol.expr<" not in body
    _parse_module(actual)


# TC-CORE-PRINT-004
# 测试目的: 验证 nn.memory shape/stride 内的 symbol expr 使用 alias。
# 使用示例: pytest -q test/core/test_print.py -k test_print_operation_with_aliases_aliases_memory_shape_and_stride
# 对应功能实现文件路径: kernel_gen/core/print.py
# 对应 spec 文件路径: spec/core/print.md
# 对应测试文件路径: test/core/test_print.py
def test_print_operation_with_aliases_aliases_memory_shape_and_stride() -> None:
    module = _parse_module(
        """
builtin.module {
  func.func @alias_memory(%memory : !nn.memory<[#symbol.expr<N>, #symbol.expr<M>], [#symbol.expr<M>, #symbol.expr<1>], i32, #nn.space<global>>) {
    func.return
  }
}
"""
    )

    actual = print_operation_with_aliases(module)

    assert "#C1 = #symbol.expr<1>" in actual
    assert "#S_N = #symbol.expr<N>" in actual
    assert "#S_M = #symbol.expr<M>" in actual
    assert "!nn.memory<[#S_N, #S_M], [#S_M, #C1], i32, #nn.space<global>>" in actual
    assert "#symbol.expr<" not in _module_body(actual)
    _parse_module(actual)


# TC-CORE-PRINT-005
# 测试目的: 验证非 xDSL operation 输入按公开 TypeError 失败。
# 使用示例: pytest -q test/core/test_print.py -k test_print_operation_with_aliases_rejects_non_operation
# 对应功能实现文件路径: kernel_gen/core/print.py
# 对应 spec 文件路径: spec/core/print.md
# 对应测试文件路径: test/core/test_print.py
def test_print_operation_with_aliases_rejects_non_operation() -> None:
    with pytest.raises(TypeError, match="operation must be xdsl Operation"):
        print_operation_with_aliases("builtin.module {}")  # type: ignore[arg-type]


# TC-CORE-PRINT-006
# 测试目的: 验证 alias printer 不污染 raw attr/type 打印。
# 使用示例: pytest -q test/core/test_print.py -k test_print_operation_with_aliases_does_not_pollute_raw_attribute_printing
# 对应功能实现文件路径: kernel_gen/core/print.py
# 对应 spec 文件路径: spec/core/print.md
# 对应测试文件路径: test/core/test_print.py
def test_print_operation_with_aliases_does_not_pollute_raw_attribute_printing() -> None:
    module = _parse_module(
        """
builtin.module {
  func.func @alias_raw(%n : !symbol.int<#symbol.expr<N>>) {
    func.return
  }
}
"""
    )

    _ = print_operation_with_aliases(module)

    assert _print_attribute_text(SymbolValueType.from_expr("N")) == "!symbol.int<#symbol.expr<N>>"
