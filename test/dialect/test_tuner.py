"""tuner dialect tests.


功能说明:
- 覆盖 tuner dialect 的 `tuner.param`、`tuner.cost`、`tuner.select` 与 `tuner.launch` parse/print、verifier 与错误路径。
- `tuner.param` 负责返回 `!symbol.int<#symbol.expr<name>>` 的超参数标量；`tuner.cost` 负责透传原 op operands 并固定返回 `!symbol.int<#symbol.expr<expr>>` 局部成本。
- `tuner.select` 与 `tuner.launch` 只通过公开 constructor 或公开文本 IR parse/verify 入口验证。

使用示例:
- pytest -q test/dialect/test_tuner.py

当前覆盖率信息:
- 不再要求覆盖率；本文件以功能测试闭环为准。

覆盖率命令:
- 不再要求覆盖率命令；本文件以功能测试闭环为准。

关联文件:
- 功能实现: kernel_gen/dialect/tuner.py
- Spec 文档: spec/dialect/tuner.md
- 测试文件: test/dialect/test_tuner.py
"""

from __future__ import annotations

import inspect
from io import StringIO
import sys
from pathlib import Path

import pytest
from xdsl.context import Context
from xdsl.dialects.builtin import Builtin, IndexType, IntegerType, StringAttr, f32
from xdsl.dialects.func import Func
from xdsl.dialects.test import Test
from xdsl.ir import Attribute, Operation
from xdsl.parser import Parser
from xdsl.printer import Printer
from xdsl.utils.exceptions import VerifyException

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.symbol import Symbol, SymbolValueType
from kernel_gen.dialect.tuner import Tuner, TunerCostOp, TunerLaunchOp, TunerParamOp, TunerSelectOp


def _build_context() -> Context:
    """构造加载 builtin/symbol/tuner 的解析上下文。


    功能说明:
    - 为 tuner dialect 的 parse/print 测试提供统一 context。

    使用示例:
    - _build_context()

    关联文件:
    - spec: spec/dialect/tuner.md
    - test: test/dialect/test_tuner.py
    - 功能实现: kernel_gen/dialect/tuner.py
    """

    ctx = Context()
    ctx.load_dialect(Builtin)
    ctx.load_dialect(Func)
    ctx.load_dialect(Test)
    ctx.load_dialect(Symbol)
    ctx.load_dialect(Tuner)
    return ctx


def _print_ir(value: Attribute | Operation) -> str:
    """打印 attribute、operation 或 module 为文本。


    功能说明:
    - 为 tuner dialect 的 round-trip 测试提供稳定文本输出。

    使用示例:
    - _print_ir(module)

    关联文件:
    - spec: spec/dialect/tuner.md
    - test: test/dialect/test_tuner.py
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
# 测试目的: 验证 tuner.param 的 parse/print round-trip 与结果类型稳定。
# 对应功能实现文件路径: kernel_gen/dialect/tuner.py
# 对应 spec 文件路径: spec/dialect/tuner.md
def test_tuner_param_round_trip() -> None:
    ctx = _build_context()
    module = Parser(
        ctx,
        """
builtin.module {
  %p0 = tuner.param : !symbol.int<#symbol.expr<BLOCK_M>>
}
""",
    ).parse_module()
    module.verify()
    printed = _print_ir(module).rstrip()
    reparsed = Parser(ctx, printed).parse_module()
    reparsed.verify()
    assert _print_ir(reparsed).rstrip() == printed


# TC-TUNER-002
# 测试目的: 验证 tuner.param 拒绝非 !symbol.int<#symbol.expr<name>> 的结果类型。
# 对应功能实现文件路径: kernel_gen/dialect/tuner.py
# 对应 spec 文件路径: spec/dialect/tuner.md
def test_tuner_param_rejects_invalid_result_type() -> None:
    invalid_types = [
        IndexType(),
        IntegerType(32),
    ]
    for invalid_type in invalid_types:
        op = TunerParamOp(invalid_type)
        with pytest.raises(VerifyException, match="tuner.param result type must be !symbol.int"):
            op.verify()


# TC-TUNER-003
# 测试目的: 验证 tuner.param 对非名称 symbol.int 的错误路径。
# 对应功能实现文件路径: kernel_gen/dialect/tuner.py
# 对应 spec 文件路径: spec/dialect/tuner.md
def test_tuner_param_rejects_invalid_name() -> None:
    for result_type in [
        SymbolValueType.from_expr("1"),
        SymbolValueType.from_expr("?"),
        SymbolValueType.from_expr("BLOCK_M + 1"),
    ]:
        with pytest.raises(VerifyException, match="tuner.param result symbol name must match"):
            TunerParamOp(result_type).verify()

    ctx = _build_context()
    module_bad = Parser(
        ctx,
        """
builtin.module {
  %p0 = tuner.param : !symbol.int<#symbol.expr<BLOCK_M + 1>>
}
""",
    ).parse_module()
    with pytest.raises(VerifyException, match="tuner.param result symbol name must match"):
        module_bad.verify()


# TC-TUNER-004
# 测试目的: 验证 tuner.cost 的 parse/print round-trip、operand 透传与固定 symbol.int 结果。
# 对应功能实现文件路径: kernel_gen/dialect/tuner.py
# 对应 spec 文件路径: spec/dialect/tuner.md
def test_tuner_cost_round_trip() -> None:
    ctx = _build_context()
    module = Parser(
        ctx,
        """
builtin.module {
  %tile_m = "test.op"() : () -> !symbol.int<#symbol.expr<TILE_M>>
  %k = "test.op"() : () -> !symbol.int<#symbol.expr<K>>
  %cost0 = tuner.cost(%tile_m, %k) {cost_kind = "memory", op_name = "dma.copy"} : (!symbol.int<#symbol.expr<TILE_M>>, !symbol.int<#symbol.expr<K>>) -> !symbol.int<#symbol.expr<LOCAL>>
}
""",
    ).parse_module()

    module.verify()
    printed = _print_ir(module).rstrip()
    reparsed = Parser(ctx, printed).parse_module()
    reparsed.verify()
    assert "tuner.cost(%tile_m, %k)" in printed
    assert 'cost_kind = "memory"' in printed
    assert 'op_name = "dma.copy"' in printed
    assert "{kind =" not in printed
    assert "device_func =" not in printed
    assert printed == _print_ir(reparsed).rstrip()


# TC-TUNER-004B
# 测试目的: 验证 tuner.cost 对任意非空 cost_kind 字符串都可 parse/print 与 verify。
# 对应功能实现文件路径: kernel_gen/dialect/tuner.py
# 对应 spec 文件路径: spec/dialect/tuner.md
def test_tuner_cost_accepts_arbitrary_non_empty_cost_kinds() -> None:
    ctx = _build_context()
    module = Parser(
        ctx,
        """
builtin.module {
  %tile_m = "test.op"() : () -> !symbol.int<#symbol.expr<TILE_M>>
  %cost0 = tuner.cost(%tile_m) {cost_kind = "compute", op_name = "dma.copy"} : (!symbol.int<#symbol.expr<TILE_M>>) -> !symbol.int<#symbol.expr<LOCAL>>
  %cost1 = tuner.cost(%tile_m) {cost_kind = "memory", op_name = "dma.copy"} : (!symbol.int<#symbol.expr<TILE_M>>) -> !symbol.int<#symbol.expr<LOCAL>>
  %cost2 = tuner.cost(%tile_m) {cost_kind = "latency", op_name = "dma.copy"} : (!symbol.int<#symbol.expr<TILE_M>>) -> !symbol.int<#symbol.expr<LOCAL>>
  %cost3 = tuner.cost(%tile_m) {cost_kind = "memory_traffic", op_name = "dma.copy"} : (!symbol.int<#symbol.expr<TILE_M>>) -> !symbol.int<#symbol.expr<LOCAL>>
}
""",
    ).parse_module()
    module.verify()

    printed = _print_ir(module).rstrip()
    for kind in ("compute", "memory", "latency", "memory_traffic"):
        assert f'cost_kind = "{kind}"' in printed
    assert printed.count("tuner.cost") == 4


# TC-TUNER-005
# 测试目的: 验证 tuner.cost 拒绝空白 cost_kind，并继续拒绝旧公开 attrs。
# 对应功能实现文件路径: kernel_gen/dialect/tuner.py
# 对应 spec 文件路径: spec/dialect/tuner.md
def test_tuner_cost_rejects_invalid_kind_attrs() -> None:
    value = TunerParamOp(SymbolValueType.from_expr("BLOCK_M")).result

    with pytest.raises(
        VerifyException,
        match="tuner.cost cost_kind must be non-empty string attr",
    ):
        TunerCostOp(
            [value],
            cost_kind=StringAttr("   "),
            op_name=StringAttr("dma.copy"),
        ).verify()

    with pytest.raises(VerifyException, match="tuner.cost kind attr is not part of public contract"):
        TunerCostOp(
            [value],
            cost_kind=StringAttr("compute"),
            op_name=StringAttr("dma.copy"),
            extra_attrs={"kind": StringAttr("move")},
        ).verify()

    with pytest.raises(VerifyException, match="tuner.cost device_func attr is not part of public contract"):
        TunerCostOp(
            [value],
            cost_kind=StringAttr("compute"),
            op_name=StringAttr("dma.copy"),
            extra_attrs={"device_func": StringAttr("kernel")},
        ).verify()


# TC-TUNER-006
# 测试目的: 验证 tuner.cost 缺少必填 attrs 或结果类型不是 symbol.int 时会报错。
# 对应功能实现文件路径: kernel_gen/dialect/tuner.py
# 对应 spec 文件路径: spec/dialect/tuner.md
def test_tuner_cost_rejects_missing_attrs_or_invalid_result_type() -> None:
    ctx = _build_context()
    value = TunerParamOp(SymbolValueType.from_expr("BLOCK_M")).result

    with pytest.raises(VerifyException, match="tuner.cost result type must be !symbol.int<#symbol.expr<expr>>"):
        TunerCostOp(
            [value],
            cost_kind=StringAttr("compute"),
            op_name=StringAttr("dma.copy"),
            result_type=f32,
        ).verify()

    with pytest.raises(VerifyException, match="tuner.cost requires attribute op_name"):
        Parser(
            ctx,
            """
builtin.module {
  %tile_m = "test.op"() : () -> !symbol.int<#symbol.expr<TILE_M>>
  %cost0 = tuner.cost(%tile_m) {cost_kind = "compute"} : (!symbol.int<#symbol.expr<TILE_M>>) -> !symbol.int<#symbol.expr<LOCAL>>
}
""",
        ).parse_module()


# TC-TUNER-007
# 测试目的: 验证 tuner.select 的 parse/print、patterns attrs 与固定 pattern_id 结果类型。
# 对应功能实现文件路径: kernel_gen/dialect/tuner.py
# 对应 spec 文件路径: spec/dialect/tuner.md
def test_tuner_select_round_trip() -> None:
    ctx = _build_context()
    module = Parser(
        ctx,
        """
builtin.module {
  %pattern_id = tuner.select {patterns = [@entry_pattern0, @entry_pattern1]} : !symbol.int<#symbol.expr<pattern_id>>
}
""",
    ).parse_module()

    module.verify()
    printed = _print_ir(module).rstrip()
    reparsed = Parser(ctx, printed).parse_module()
    reparsed.verify()
    assert "@entry_pattern0" in printed
    assert "@entry_pattern1" in printed
    assert "!symbol.int<#symbol.expr<pattern_id>>" in printed
    assert printed == _print_ir(reparsed).rstrip()


# TC-TUNER-008
# 测试目的: 验证 tuner.select 拒绝空 patterns、非 flat SymbolRefAttr 与非 pattern_id 结果类型。
# 对应功能实现文件路径: kernel_gen/dialect/tuner.py
# 对应 spec 文件路径: spec/dialect/tuner.md
def test_tuner_select_rejects_invalid_contract() -> None:
    with pytest.raises(VerifyException, match="tuner.select patterns must be non-empty"):
        TunerSelectOp([]).verify()

    with pytest.raises(VerifyException, match="tuner.select result type must be !symbol.int"):
        TunerSelectOp(["entry"], result_type=SymbolValueType.from_expr("OTHER")).verify()

    ctx = _build_context()
    with pytest.raises(VerifyException, match="tuner.select patterns must be non-empty"):
        Parser(
            ctx,
            """
builtin.module {
  %pattern_id = tuner.select {patterns = ["entry"]} : !symbol.int<#symbol.expr<pattern_id>>
}
""",
        ).parse_module().verify()

    module_bad = Parser(
        ctx,
        """
builtin.module {
  %pattern_id = tuner.select {patterns = [@entry::@nested]} : !symbol.int<#symbol.expr<pattern_id>>
}
""",
    ).parse_module()
    with pytest.raises(VerifyException, match="tuner.select patterns must be non-empty"):
        module_bad.verify()


# TC-TUNER-009
# 测试目的: 验证 tuner.launch 的 parse/print、callee 与 operand type list 合同。
# 对应功能实现文件路径: kernel_gen/dialect/tuner.py
# 对应 spec 文件路径: spec/dialect/tuner.md
def test_tuner_launch_round_trip() -> None:
    ctx = _build_context()
    module = Parser(
        ctx,
        """
builtin.module {
  func.func @entry(%arg0 : !symbol.int<#symbol.expr<N>>) {
    tuner.launch(@entry_pattern0, %arg0) : (!symbol.int<#symbol.expr<N>>) -> ()
    func.return
  }
}
""",
    ).parse_module()

    module.verify()
    printed = _print_ir(module).rstrip()
    reparsed = Parser(ctx, printed).parse_module()
    reparsed.verify()
    assert "tuner.launch(@entry_pattern0" in printed
    assert printed == _print_ir(reparsed).rstrip()


# TC-TUNER-010
# 测试目的: 验证 tuner.launch 拒绝嵌套 callee、错误参数类型列表与非空 result。
# 对应功能实现文件路径: kernel_gen/dialect/tuner.py
# 对应 spec 文件路径: spec/dialect/tuner.md
def test_tuner_launch_rejects_invalid_contract() -> None:
    ctx = _build_context()
    invalid_cases = [
        (
            """
builtin.module {
  func.func @entry() {
    tuner.launch("entry_pattern0") : () -> ()
    func.return
  }
}
""",
            "tuner.launch callee must be SymbolRefAttr",
        ),
        (
            """
builtin.module {
  func.func @entry(%arg0 : !symbol.int<#symbol.expr<N>>) {
    tuner.launch(@entry::@nested, %arg0) : (!symbol.int<#symbol.expr<N>>) -> ()
    func.return
  }
}
""",
            "tuner.launch callee must be SymbolRefAttr",
        ),
        (
            """
builtin.module {
  func.func @entry(%arg0 : !symbol.int<#symbol.expr<N>>) {
    tuner.launch(@entry_pattern0, %arg0) : (!symbol.int<#symbol.expr<M>>) -> ()
    func.return
  }
}
""",
            "tuner.launch arg types must match operand types",
        ),
        (
            """
builtin.module {
  func.func @entry(%arg0 : !symbol.int<#symbol.expr<N>>) {
    tuner.launch(@entry_pattern0, %arg0) : (!symbol.int<#symbol.expr<N>>) -> (!symbol.int<#symbol.expr<N>>)
    func.return
  }
}
""",
            "tuner.launch result types must be",
        ),
    ]
    for text, message in invalid_cases:
        with pytest.raises(VerifyException, match=message):
            Parser(ctx, text).parse_module().verify()


# TC-TUNER-011
# 测试目的: 验证 TunerLaunchOp constructor 签名只暴露 spec/API 定义的 callee 与 args。
# 对应功能实现文件路径: kernel_gen/dialect/tuner.py
# 对应 spec 文件路径: spec/dialect/tuner.md
def test_tuner_launch_public_signature_matches_spec() -> None:
    signature = inspect.signature(TunerLaunchOp)

    assert "parse_error" not in signature.parameters
    assert str(signature) == "(callee: 'str | SymbolRefAttr', args: 'Sequence[SSAValue | Operation]' = ()) -> 'None'"


# TC-TUNER-012
# 测试目的: 验证导入 tuner dialect 不会全局替换 xDSL Context.load_dialect。
# 对应功能实现文件路径: kernel_gen/dialect/tuner.py
# 对应 spec 文件路径: spec/dialect/tuner.md
def test_tuner_import_does_not_patch_context_load_dialect() -> None:
    assert Context.load_dialect.__module__ == "xdsl.context"
