"""symbol control-flow operations.

功能说明:
- 定义 symbol.yield 与 symbol.for op。

API 列表:
- `class SymbolYieldOp(value: SSAValue | Operation)`
- `class SymbolForOp(start: SSAValue | Operation, end: SSAValue | Operation, step: SSAValue | Operation, body: Region | Block | Sequence[Operation] | Sequence[Block], iter_attr: SymbolIterAttr | None = None, init: SSAValue | Operation | None = None, result_type: Attribute | None = None)`

使用示例:
- `from kernel_gen.dialect.symbol.operation import ...`

关联文件:
- spec: spec/dialect/symbol.md
- test: test/dialect/symbol/
- 功能实现: kernel_gen/dialect/symbol/operation/control_flow.py
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar

from kernel_gen.core.error import ERROR_ACTION, ERROR_ACTUAL, ERROR_TEMPLATE
from xdsl.dialects import arith
from xdsl.dialects.builtin import BFloat16Type, Float16Type, Float32Type, Float64Type, IntAttr, IntegerAttr, IntegerType, StringAttr, f32, f64, i1, i32
from xdsl.dialect_interfaces.constant_materialization import ConstantMaterializationInterface
from xdsl.ir import Attribute, Block, Dialect, Operation, ParametrizedAttribute, Region, SSAValue, TypeAttribute
from xdsl.irdl import (
    IRDLOperation,
    attr_def,
    irdl_attr_definition,
    irdl_op_definition,
    opt_operand_def,
    opt_result_def,
    operand_def,
    param_def,
    region_def,
    result_def,
    traits_def,
    var_operand_def,
)
from xdsl.interfaces import HasFolderInterface
from xdsl.parser import AttrParser
from xdsl.printer import Printer
from xdsl.traits import IsTerminator, NoTerminator, Pure
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.nn import NnMemoryType

from ..common import _format_error, _raise_verify_error
from ..expr.parser import (_SymbolExprNode, _SymbolExprToken, _SymbolExprParserBase, _SymbolExprTextParser, _SymbolExprAttrParser, _tokenize_symbol_expr, _make_symbol_expr_const, _make_symbol_expr_symbol, _make_symbol_expr_unknown, _is_symbol_expr_unknown, _contains_symbol_expr_unknown, _contains_symbol_expr_iter, _make_symbol_expr_iter, _get_symbol_expr_const, _get_concrete_symbol_expr_node_value, _linear_symbol_expr_terms, _make_symbol_expr_neg, _make_symbol_expr_add, _make_symbol_expr_sub, _make_symbol_expr_mul, _make_symbol_expr_keyword_binary, _make_symbol_expr_min, _make_symbol_expr_max, _symbol_expr_precedence, _format_symbol_expr_node, _format_symbol_expr_add, _parse_symbol_expr_from_text, _parse_symbol_expr_from_attr_parser, _normalize_expr, _evaluate_concrete_expr, _canonicalize_symbolic_expr, _is_supported_symbol_expr, _unwrap_symbol_expr_attr_text)
from ..attr import SymbolExprAttr, SymbolIterAttr
from ..type import SymbolIterType, SymbolPtrType, SymbolValueType
from .common import (_verify_axis, _entry_to_expr, _infer_result_type, _is_symbol_int_type, _is_symbol_arith_operand_type, _is_unknown_symbol_int_type, _parse_symbol_binary_operand_types, _symbol_iter_type_expr_node, _symbol_arith_operand_expr_node, _symbol_arith_operand_contains_unknown, _symbol_expr_bounds_are_full_tiles, _linear_distance_is_positive_multiple, _symbol_expr_full_tile_residual_step, _symbol_expr_full_tile_min_step, _symbol_min_full_tile_step_value, _requires_unknown_arith_result, _infer_symbol_arith_result_expr, _alternate_symbol_arith_result_exprs, _get_concrete_symbol_int_value)

@irdl_op_definition
class SymbolYieldOp(IRDLOperation):
    """承载 symbol.for 单个 carried `!symbol.int<#symbol.expr<...>>` 的循环末尾值。"""

    name = "symbol.yield"

    value = operand_def(Attribute)
    traits = traits_def(IsTerminator())

    def __init__(self: "SymbolYieldOp", value: SSAValue | Operation) -> None:
        """初始化 symbol.yield。


        功能说明:
        - 构造仅承载一个 `!symbol.int<#symbol.expr<...>>` operand 的 terminator。
        - 该 op 只服务带 carried-value 的 `symbol.for` 循环体。

        使用示例:
        - SymbolYieldOp(value)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        super().__init__(operands=[value])

    def verify_(self: "SymbolYieldOp") -> None:
        """校验 symbol.yield 只能在 carried symbol.for 末尾使用。


        功能说明:
        - 要求 `value` 类型固定为 `!symbol.int<#symbol.expr<...>>`。
        - 要求当前 op 位于带单个 carried `!symbol.int<#symbol.expr<...>>` 的 `symbol.for` 单块 region 末尾。

        使用示例:
        - SymbolYieldOp(value).verify()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        if not _is_symbol_int_type(SSAValue.get(self.value).type):
            _raise_verify_error(f"{self.name} value must have type !symbol.int<#symbol.expr<expr>>")

        parent_op = self.parent_op()
        if not isinstance(parent_op, SymbolForOp):
            _raise_verify_error(f"{self.name} must appear inside symbol.for")
        if parent_op.init is None or parent_op.result is None:
            _raise_verify_error(f"{self.name} requires symbol.for loop-carried !symbol.int<#symbol.expr<expr>>")

        parent_block = self.parent_block()
        if parent_block is None or parent_block.last_op is not self:
            _raise_verify_error(f"{self.name} must terminate symbol.for body")

    def print(self: "SymbolYieldOp", printer: Printer) -> None:
        """打印 symbol.yield 自定义文本语法。


        功能说明:
        - 输出 `symbol.yield %value : !symbol.int<#symbol.expr<...>>` 形式文本。

        使用示例:
        - SymbolYieldOp(value).print(printer)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        printer.print_string(" ")
        printer.print_ssa_value(self.value)
        printer.print_string(" : ")
        printer.print_attribute(SSAValue.get(self.value).type)

    @classmethod
    def parse(cls: type["SymbolYieldOp"], parser: AttrParser) -> "SymbolYieldOp":
        """解析 symbol.yield 自定义文本语法。


        功能说明:
        - 解析 `symbol.yield %value : !symbol.int<#symbol.expr<...>>`。
        - 在解析阶段把 unresolved operand 解析为具体验证类型，保持 print 后再 parse 闭环。

        使用示例:
        - SymbolYieldOp.parse(parser)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        value = parser.parse_unresolved_operand()
        parser.parse_characters(":", f" in {cls.name}")
        value_type = parser.parse_type()
        value = parser.resolve_operand(value, value_type)
        return cls(value)


@irdl_op_definition
class SymbolForOp(IRDLOperation):
    """以 symbol.int 边界驱动的半开区间循环。"""

    name = "symbol.for"

    start = operand_def(Attribute)
    end = operand_def(Attribute)
    step = operand_def(Attribute)
    init = opt_operand_def(Attribute)
    iter_attr = attr_def(SymbolIterAttr, attr_name="iter")
    body = region_def()
    result = opt_result_def(Attribute)
    traits = traits_def(NoTerminator())

    def __init__(
        self: "SymbolForOp",
        start: SSAValue | Operation,
        end: SSAValue | Operation,
        step: SSAValue | Operation,
        body: Region | Block | Sequence[Operation] | Sequence[Block],
        iter_attr: SymbolIterAttr | None = None,
        init: SSAValue | Operation | None = None,
        result_type: Attribute | None = None,
    ) -> None:
        """初始化 symbol.for。


        功能说明:
        - 设置 `start/end/step` 三个 `!symbol.int<#symbol.expr<...>>` 操作数与单块循环体。
        - 兼容旧的无 carried-value 形式，也支持通过 `init` 构造单个 loop-carried `!symbol.int<#symbol.expr<...>>` 结果。
        - `iter` attribute 与块参数类型共同表达迭代边界语义。

        使用示例:
        - SymbolForOp(start, end, step, Block(arg_types=[SymbolIterType.from_bounds("0", "M", "TILE_D0")]))
        - SymbolForOp(start, end, step, Block(arg_types=[SymbolIterType.from_bounds("0", "M", "TILE_D0"), SymbolValueType.from_expr("ACC")]), init=zero, result_type=SymbolValueType.from_expr("TOTAL"))

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        if isinstance(body, Block):
            body = Region(body)
        elif not isinstance(body, Region):
            body = Region(list(body))
        if iter_attr is None:
            start_type = SSAValue.get(start).type
            end_type = SSAValue.get(end).type
            step_type = SSAValue.get(step).type
            if isinstance(start_type, SymbolValueType) and isinstance(end_type, SymbolValueType) and isinstance(step_type, SymbolValueType):
                iter_attr = SymbolIterAttr.from_bounds(
                    _normalize_expr(start_type.expr.expr.data),
                    _normalize_expr(end_type.expr.expr.data),
                    _normalize_expr(step_type.expr.expr.data),
                )
            else:
                iter_attr = SymbolIterAttr.from_bounds("0", "0", "1")
        super().__init__(
            operands=[start, end, step, [] if init is None else [init]],
            regions=[body],
            result_types=[[] if init is None else [result_type or SSAValue.get(init).type]],
            attributes={"iter": iter_attr},
        )

    def verify_(self: "SymbolForOp") -> None:
        """校验 symbol.for 约束。


        功能说明:
        - 校验 start/end/step 均为 `!symbol.int<\"expr\">`。
        - 校验 `iter` attribute 与 block 参数类型一致。
        - 校验 region 为单块；无 carried-value 时仅包含 `it` 一个块参数，带 carried-value 时包含 `it/acc` 两个块参数。
        - 校验 loop-carried `!symbol.int<#symbol.expr<...>>` 的 `init/result/symbol.yield` 口径与 terminator 形状。
        - 当 step 可静态判定为 `0` 时直接报错。

        使用示例:
        - SymbolForOp(start, end, step, body).verify_()

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        start_value = SSAValue.get(self.start)
        end_value = SSAValue.get(self.end)
        step_value = SSAValue.get(self.step)
        for operand_name, operand in (("start", start_value), ("end", end_value), ("step", step_value)):
            if not _is_symbol_int_type(operand.type):
                _raise_verify_error(f"{self.name} {operand_name} must have type !symbol.int<#symbol.expr<expr>>")

        step_type = step_value.type
        assert isinstance(step_type, SymbolValueType)
        step_expr = _normalize_expr(step_type.expr.expr.data)
        if step_expr == "0":
            _raise_verify_error(f"{self.name} step must not be zero")

        blocks = list(self.body.blocks)
        if len(blocks) != 1:
            _raise_verify_error(f"{self.name} only supports single-block regions")
        block = blocks[0]
        carried_init = self.init
        carried_result = self.result
        has_carried = carried_init is not None or carried_result is not None
        if carried_init is None and carried_result is not None:
            _raise_verify_error(f"{self.name} loop-carried !symbol.int<#symbol.expr<expr>> requires init operand")
        if carried_init is not None and carried_result is None:
            _raise_verify_error(f"{self.name} loop-carried !symbol.int<#symbol.expr<expr>> requires single symbol.int result")
        expected_block_args = 2 if has_carried else 1
        if len(block.args) != expected_block_args:
            if has_carried:
                _raise_verify_error(f"{self.name} loop-carried !symbol.int<#symbol.expr<expr>> requires exactly two block arguments")
            _raise_verify_error(f"{self.name} body must have exactly one block argument")
        iter_arg = block.args[0]
        if not isinstance(iter_arg.type, SymbolIterType):
            _raise_verify_error(f"{self.name} it must have type !symbol.iter<...>")
        iter_attr = self.iter_attr
        if not isinstance(iter_attr, SymbolIterAttr):
            _raise_verify_error(f"{self.name} iter attribute must be #symbol.iter<...>")
        start_expr = _normalize_expr(start_value.type.expr.expr.data)
        end_expr = _normalize_expr(end_value.type.expr.expr.data)
        if _normalize_expr(iter_attr.start.expr.data) != start_expr:
            _raise_verify_error(f"{self.name} iter.start must match start operand")
        if _normalize_expr(iter_attr.end.expr.data) != end_expr:
            _raise_verify_error(f"{self.name} iter.end must match end operand")
        if _normalize_expr(iter_attr.step.expr.data) != step_expr:
            _raise_verify_error(f"{self.name} iter.step must match step operand")
        expected_iter_type = SymbolIterType.from_attr(iter_attr)
        if iter_arg.type != expected_iter_type:
            _raise_verify_error(f"{self.name} it must have type {expected_iter_type}")
        if not has_carried:
            return

        if not _is_symbol_int_type(carried_init.type):
            _raise_verify_error(f"{self.name} loop-carried init must have type !symbol.int<#symbol.expr<expr>>")
        if not _is_symbol_int_type(block.args[1].type):
            _raise_verify_error(f"{self.name} loop-carried acc must have type !symbol.int<#symbol.expr<expr>>")
        if not _is_symbol_int_type(carried_result.type):
            _raise_verify_error(f"{self.name} loop-carried result must have type !symbol.int<#symbol.expr<expr>>")

        terminator = block.last_op
        if not isinstance(terminator, SymbolYieldOp):
            _raise_verify_error(f"{self.name} loop-carried body must terminate with symbol.yield")
        if not _is_symbol_int_type(SSAValue.get(terminator.value).type):
            _raise_verify_error(f"{self.name} loop-carried yield must have type !symbol.int<#symbol.expr<expr>>")

    def print(self: "SymbolForOp", printer: Printer) -> None:
        """打印 symbol.for 自定义文本语法。


        功能说明:
        - 无 carried-value 时输出旧文本语法。
        - 带 carried-value 时输出 `iter_args(%acc = %init) {iter = ...} -> !symbol.int<#symbol.expr<...>> { ... }`，与 parser 使用同一公开顺序。

        使用示例:
        - SymbolForOp(start, end, step, body, init=zero).print(printer)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        blocks = list(self.body.blocks)
        has_carried = self.init is not None and self.result is not None
        if len(blocks) != 1 or len(blocks[0].args) != (2 if has_carried else 1):
            printer.print_op_with_default_format(self)
            return
        block = blocks[0]
        iter_arg = block.args[0]
        printer.print_string(" ")
        printer.print_ssa_value(iter_arg)
        printer.print_string(" = ")
        printer.print_ssa_value(self.start)
        printer.print_string(" to ")
        printer.print_ssa_value(self.end)
        printer.print_string(" step ")
        printer.print_ssa_value(self.step)
        if has_carried:
            printer.print_string(" iter_args(")
            printer.print_ssa_value(block.args[1])
            printer.print_string(" = ")
            printer.print_ssa_value(self.init)
            printer.print_string(")")
        printer.print_string(" {iter = ")
        printer.print_attribute(self.iter_attr)
        printer.print_string("}")
        if has_carried:
            printer.print_string(" -> ")
            printer.print_attribute(self.result.type)
        printer.print_string(" {")
        if block.ops:
            with printer.indented():
                for op in block.ops:
                    printer.print_string("\n")
                    printer.print_op(op)
            printer.print_string("\n", indent=0)
        else:
            printer.print_string("\n", indent=0)
        printer.print_string("}")

    @classmethod
    def parse(cls: type["SymbolForOp"], parser: AttrParser) -> "SymbolForOp":
        """解析 symbol.for 自定义文本语法。


        功能说明:
        - 解析旧的 `symbol.for %it = %start to %end step %step {iter = #symbol.iter<...>} { ... }`。
        - 解析新的 `symbol.for %it = %start to %end step %step iter_args(%acc = %zero) {iter = #symbol.iter<...>} -> !symbol.int<#symbol.expr<...>> { ... }`。
        - 迭代变量与 carried `acc` 都在进入 region 前完成类型解析，保持 print 后再 parse 闭环。

        使用示例:
        - SymbolForOp.parse(parser)

        关联文件:
        - spec: spec/dialect/symbol.md
        - test: test/dialect/symbol/test_symbol.py
        - 功能实现: kernel_gen/dialect/symbol/
        """

        unresolved_iter = parser.parse_argument(expect_type=False)
        parser.parse_characters("=", " in symbol.for")
        start_value = parser.parse_operand()
        parser.parse_characters("to", " in symbol.for")
        end_value = parser.parse_operand()
        parser.parse_characters("step", " in symbol.for")
        step_value = parser.parse_operand()
        init_value = None
        acc_arg = None
        if parser.parse_optional_keyword("iter_args") is not None:
            parser.parse_punctuation("(", " in symbol.for")
            unresolved_acc = parser.parse_argument(expect_type=False)
            parser.parse_characters("=", " in symbol.for")
            init_value = parser.parse_operand()
            parser.parse_punctuation(")", " in symbol.for")
        parser.parse_characters("{", " in symbol.for")
        parser.parse_keyword("iter", " in symbol.for")
        parser.parse_characters("=", " in symbol.for")
        iter_attr = parser.parse_attribute()
        if not isinstance(iter_attr, SymbolIterAttr):
            raise VerifyException(_format_error("symbol.for iter attribute must be #symbol.iter<...>"))
        parser.parse_characters("}", " in symbol.for")
        iter_arg = unresolved_iter.resolve(SymbolIterType.from_attr(iter_attr))
        result_type = None
        if parser.parse_optional_characters("->") is not None:
            result_type = parser.parse_type()
        if init_value is None and result_type is not None:
            raise VerifyException(_format_error("symbol.for result type requires loop-carried !symbol.int<#symbol.expr<expr>>"))
        if init_value is not None:
            if not isinstance(result_type, SymbolValueType):
                raise VerifyException(_format_error("symbol.for loop-carried result must be !symbol.int<#symbol.expr<expr>>"))
            acc_arg = unresolved_acc.resolve(result_type)
        block_args = (iter_arg,) if acc_arg is None else (iter_arg, acc_arg)
        body = parser.parse_region(block_args)
        op = cls(start_value, end_value, step_value, body, iter_attr, init=init_value, result_type=result_type)
        return op

__all__ = ["SymbolYieldOp", "SymbolForOp"]
