"""symbol.to_float expectation.

创建者: 我不是牛马
最后一次更改: 我不是牛马

功能说明:
- 验证 `symbol.to_float` 可以将 `!symbol.int<"...">` 输入稳定转换为 `f32` 结果。
- 验证 `symbol.to_float` 的 parse/print round-trip 与 verifier 错误路径符合公开语义。

使用示例:
- python expectation/dialect/symbol/to_float.py

关联文件:
- spec: spec/dialect/symbol.md
- test: test/dialect/test_symbol_dialect.py
- 功能实现: kernel_gen/dialect/symbol.py
"""

from __future__ import annotations

from io import StringIO
from pathlib import Path
import sys

from xdsl.context import Context
from xdsl.dialects.builtin import Builtin, f32, f64, i32
from xdsl.dialects.test import Test, TestOp
from xdsl.ir import SSAValue
from xdsl.parser import Parser
from xdsl.printer import Printer
from xdsl.utils.exceptions import VerifyException

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.symbol import Symbol, SymbolToFloatOp, SymbolValueType


def _build_context() -> Context:
    """构造解析与打印 symbol.to_float 所需的 dialect 上下文。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 加载 builtin、test 与 symbol dialect，供 expectation 解析 module 文本与验证 verifier。

    使用示例:
    - _build_context()

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/test_symbol_dialect.py
    - 功能实现: expectation/dialect/symbol/to_float.py
    """

    ctx = Context()
    ctx.load_dialect(Builtin)
    ctx.load_dialect(Test)
    ctx.load_dialect(Symbol)
    return ctx


def _print_attr(value: object) -> str:
    """打印 attribute/type 为稳定文本。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 将 expectation 关心的返回类型打印为字符串，便于断言 `f32` 结果口径。

    使用示例:
    - _print_attr(f32)

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/test_symbol_dialect.py
    - 功能实现: expectation/dialect/symbol/to_float.py
    """

    stream = StringIO()
    printer = Printer(stream=stream)
    printer.print_attribute(value)
    return stream.getvalue()


def _print_op(op: object) -> str:
    """打印 operation 或 module 为稳定文本。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 用于验证 `symbol.to_float` 的 round-trip 文本保持公开打印格式。

    使用示例:
    - _print_op(module)

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/test_symbol_dialect.py
    - 功能实现: expectation/dialect/symbol/to_float.py
    """

    stream = StringIO()
    printer = Printer(stream=stream)
    printer.print_op(op)
    return stream.getvalue()


def _make_symbol_value(expr: str) -> SSAValue:
    """构造一个 `!symbol.int<"...">` 的测试 SSA value。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 使用 `test.op` 结果值生成 expectation 需要的 symbol 输入，避免引入额外业务依赖。

    使用示例:
    - _make_symbol_value("N")

    关联文件:
    - spec: spec/dialect/symbol.md
    - test: test/dialect/test_symbol_dialect.py
    - 功能实现: expectation/dialect/symbol/to_float.py
    """

    return TestOp(result_types=[SymbolValueType.from_expr(expr)]).results[0]


ctx = _build_context()

verify_op = SymbolToFloatOp(_make_symbol_value("N"), f32)
verify_op.verify()
assert _print_attr(verify_op.result.type) == "f32"

module = Parser(
    ctx,
    """
builtin.module {
  %n = "test.op"() : () -> !symbol.int<"N">
  %f = symbol.to_float %n : !symbol.int<"N"> -> f32
}
""",
).parse_module()
module.verify()
printed = _print_op(module)
assert 'symbol.to_float %n : !symbol.int<"N"> -> f32' in printed

non_symbol_value = TestOp(result_types=[i32]).results[0]
try:
    SymbolToFloatOp(non_symbol_value, f32).verify()
    raise AssertionError("symbol.to_float should reject non-symbol.int source")
except VerifyException as exc:
    assert 'symbol.to_float source must have type !symbol.int<"expr">' in str(exc)

try:
    SymbolToFloatOp(_make_symbol_value("N"), f64).verify()
    raise AssertionError("symbol.to_float should reject non-f32 result type")
except VerifyException as exc:
    assert "symbol.to_float result type must be f32" in str(exc)
