"""tuner dialect tests.

创建者: 我不是牛马
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 tuner dialect 的 `tuner.param` 与 `tuner.cost` parse/print、verifier 与错误路径。
- `tuner.param` 负责返回 `!symbol.dim<"name">` 的超参数标量；`tuner.cost` 负责透传原 op operands 并固定返回 `f64` 局部成本。

使用示例:
- pytest -q test/dialect/test_tuner_dialect.py

当前覆盖率信息:
- 不再要求覆盖率；本文件以功能测试闭环为准。

覆盖率命令:
- 不再要求覆盖率命令；本文件以功能测试闭环为准。

关联文件:
- 功能实现: kernel_gen/dialect/tuner.py
- Spec 文档: spec/dialect/tuner.md
- 测试文件: test/dialect/test_tuner_dialect.py
"""

from __future__ import annotations

from io import StringIO
import sys
from pathlib import Path

import pytest
from xdsl.context import Context
from xdsl.dialects.builtin import Builtin, IndexType, IntegerType, StringAttr, SymbolRefAttr, f32, f64
from xdsl.dialects.test import Test
from xdsl.ir import Attribute, Operation
from xdsl.parser import Parser
from xdsl.printer import Printer
from xdsl.utils.exceptions import VerifyException

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.symbol import Symbol, SymbolDimType, SymbolValueType
from kernel_gen.dialect.tuner import Tuner, TunerCostOp, TunerParamOp


def _build_context() -> Context:
    """构造加载 builtin/symbol/tuner 的解析上下文。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 为 tuner dialect 的 parse/print 测试提供统一 context。

    使用示例:
    - _build_context()

    关联文件:
    - spec: spec/dialect/tuner.md
    - test: test/dialect/test_tuner_dialect.py
    - 功能实现: kernel_gen/dialect/tuner.py
    """

    ctx = Context()
    ctx.load_dialect(Builtin)
    ctx.load_dialect(Test)
    ctx.load_dialect(Symbol)
    ctx.load_dialect(Tuner)
    return ctx


def _print_ir(value: object) -> str:
    """打印 attribute、operation 或 module 为文本。

    创建者: 我不是牛马
    最后一次更改: 我不是牛马

    功能说明:
    - 为 tuner dialect 的 round-trip 测试提供稳定文本输出。

    使用示例:
    - _print_ir(module)

    关联文件:
    - spec: spec/dialect/tuner.md
    - test: test/dialect/test_tuner_dialect.py
    - 功能实现: kernel_gen/dialect/tuner.py
    """

    stream = StringIO()
    printer = Printer(stream=stream)
    if isinstance(value, Attribute):
        printer.print_attribute(value)
    elif isinstance(value, Operation):
        printer.print_op(value)
    else:
        printer.print(value)
    return stream.getvalue()


# TC-TUNER-001
# 创建者: 我不是牛马
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-27 00:18:48 +0800
# 最近一次运行成功时间: 2026-03-27 00:18:48 +0800
# 测试目的: 验证 tuner.param 的 parse/print round-trip 与结果类型稳定。
# 对应功能实现文件路径: kernel_gen/dialect/tuner.py
# 对应 spec 文件路径: spec/dialect/tuner.md
def test_tuner_param_round_trip() -> None:
    ctx = _build_context()
    module = Parser(
        ctx,
        """
builtin.module {
  %p0 = tuner.param : !symbol.dim<"BLOCK_M">
}
""",
    ).parse_module()
    module.verify()
    printed = _print_ir(module).rstrip()
    reparsed = Parser(ctx, printed).parse_module()
    reparsed.verify()
    assert _print_ir(reparsed).rstrip() == printed


# TC-TUNER-002
# 创建者: 我不是牛马
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-26 23:17:09 +0800
# 最近一次运行成功时间: 2026-03-26 23:17:09 +0800
# 测试目的: 验证 tuner.param 拒绝非 !symbol.dim<"name"> 的结果类型。
# 对应功能实现文件路径: kernel_gen/dialect/tuner.py
# 对应 spec 文件路径: spec/dialect/tuner.md
def test_tuner_param_rejects_invalid_result_type() -> None:
    invalid_types = [
        SymbolValueType.from_expr("BLOCK_M"),
        IndexType(),
        IntegerType(32),
    ]
    for invalid_type in invalid_types:
        op = TunerParamOp(invalid_type)
        with pytest.raises(VerifyException, match='tuner.param result type must be !symbol.dim<"name">'):
            op.verify()


# TC-TUNER-003
# 创建者: 我不是牛马
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-26 23:17:09 +0800
# 最近一次运行成功时间: 2026-03-26 23:17:09 +0800
# 测试目的: 验证 tuner.param 对非法 name 的错误路径。
# 对应功能实现文件路径: kernel_gen/dialect/tuner.py
# 对应 spec 文件路径: spec/dialect/tuner.md
def test_tuner_param_rejects_invalid_name() -> None:
    with pytest.raises(VerifyException, match="symbol dim name must not be empty"):
        SymbolDimType(StringAttr("")).verify()

    with pytest.raises(VerifyException, match="symbol dim name must match"):
        SymbolDimType(StringAttr("BLOCK-M")).verify()

    ctx = _build_context()
    module_empty = Parser(
        ctx,
        """
builtin.module {
  %p0 = tuner.param : !symbol.dim<"">
}
""",
    ).parse_module()
    with pytest.raises(VerifyException, match="symbol dim name must not be empty"):
        module_empty.verify()

    module_bad = Parser(
        ctx,
        """
builtin.module {
  %p0 = tuner.param : !symbol.dim<"BLOCK-M">
}
""",
    ).parse_module()
    with pytest.raises(VerifyException, match="symbol dim name must match"):
        module_bad.verify()


# TC-TUNER-004
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-17 10:30:00 +0800
# 最近一次运行成功时间: 2026-04-17 10:30:00 +0800
# 测试目的: 验证 tuner.cost 的 parse/print round-trip、operand 透传与固定 f64 结果。
# 对应功能实现文件路径: kernel_gen/dialect/tuner.py
# 对应 spec 文件路径: spec/dialect/tuner.md
def test_tuner_cost_round_trip() -> None:
    ctx = _build_context()
    module = Parser(
        ctx,
        """
builtin.module {
  %tile_m = "test.op"() : () -> !symbol.int<"TILE_M">
  %k = "test.op"() : () -> !symbol.int<"K">
  %cost0 = tuner.cost(%tile_m, %k) {kind = "move", cost_kind = "all", op_name = "dma.alloc", device_func = @_device_matmul_kernel_} : (!symbol.int<"TILE_M">, !symbol.int<"K">) -> f64
}
""",
    ).parse_module()

    module.verify()
    printed = _print_ir(module).rstrip()
    reparsed = Parser(ctx, printed).parse_module()
    reparsed.verify()
    assert "tuner.cost(%tile_m, %k)" in printed
    assert 'cost_kind = "all"' in printed
    assert printed == _print_ir(reparsed).rstrip()


# TC-TUNER-005
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-17 10:30:00 +0800
# 最近一次运行成功时间: 2026-04-17 10:30:00 +0800
# 测试目的: 验证 tuner.cost 的 kind / cost_kind 仅接受公开合同允许值。
# 对应功能实现文件路径: kernel_gen/dialect/tuner.py
# 对应 spec 文件路径: spec/dialect/tuner.md
def test_tuner_cost_rejects_invalid_kind_attrs() -> None:
    value = TunerParamOp(SymbolDimType.from_name("BLOCK_M")).result

    with pytest.raises(VerifyException, match="tuner.cost kind must be one of compute or move"):
        TunerCostOp(
            [value],
            kind=StringAttr("all"),
            cost_kind=StringAttr("all"),
            op_name=StringAttr("dma.alloc"),
            device_func=SymbolRefAttr("kernel"),
        ).verify()

    with pytest.raises(VerifyException, match="tuner.cost cost_kind must be one of compute, move or all"):
        TunerCostOp(
            [value],
            kind=StringAttr("move"),
            cost_kind=StringAttr("other"),
            op_name=StringAttr("dma.alloc"),
            device_func=SymbolRefAttr("kernel"),
        ).verify()


# TC-TUNER-006
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-17 10:30:00 +0800
# 最近一次运行成功时间: 2026-04-17 10:30:00 +0800
# 测试目的: 验证 tuner.cost 缺少必填 attrs 或结果类型不是 f64 时会报错。
# 对应功能实现文件路径: kernel_gen/dialect/tuner.py
# 对应 spec 文件路径: spec/dialect/tuner.md
def test_tuner_cost_rejects_missing_attrs_or_invalid_result_type() -> None:
    ctx = _build_context()
    value = TunerParamOp(SymbolDimType.from_name("BLOCK_M")).result

    with pytest.raises(VerifyException, match="tuner.cost result type must be f64"):
        TunerCostOp(
            [value],
            kind=StringAttr("move"),
            cost_kind=StringAttr("all"),
            op_name=StringAttr("dma.alloc"),
            device_func=SymbolRefAttr("kernel"),
            result_type=f32,
        ).verify()

    with pytest.raises(VerifyException, match="tuner.cost requires attribute device_func"):
        Parser(
            ctx,
            """
builtin.module {
  %tile_m = "test.op"() : () -> !symbol.int<"TILE_M">
  %cost0 = tuner.cost(%tile_m) {kind = "move", cost_kind = "all", op_name = "dma.alloc"} : (!symbol.int<"TILE_M">) -> f64
}
""",
        ).parse_module()
