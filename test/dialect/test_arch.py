"""arch dialect tests.


功能说明:
- 覆盖 arch dialect 的固定结果类型查询、动态 memory 入口与 kernel 启动描述的 parse/print 与 verifier。

使用示例:
- pytest -q test/dialect/test_arch.py

当前覆盖率信息:
- 不再要求覆盖率；本文件以功能测试闭环为准。

覆盖率命令:
- 不再要求覆盖率命令；本文件以功能测试闭环为准。

关联文件:
- 功能实现: kernel_gen/dialect/arch.py
- Spec 文档: spec/dialect/arch.md
- 测试文件: test/dialect/test_arch.py
"""

from __future__ import annotations

from io import StringIO
import sys
from pathlib import Path

import pytest
from xdsl.context import Context
from xdsl.dialects.builtin import ArrayAttr, Builtin, IntAttr, StringAttr, SymbolRefAttr, i8, i32
from xdsl.dialects.test import Test, TestOp as _TestOp
from xdsl.ir import Attribute, Operation, SSAValue
from xdsl.parser import Parser
from xdsl.printer import Printer
from xdsl.utils.exceptions import VerifyException

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.arch import (
    Arch,
    ArchBarrierOp,
    ArchGetBlockIdOp,
    ArchGetBlockNumOp,
    ArchGetDynamicMemoryOp,
    ArchGetSubthreadIdOp,
    ArchGetSubthreadNumOp,
    ArchGetThreadIdOp,
    ArchGetThreadNumOp,
    ArchLaunchOp,
    ArchLaunchKernelOp,
    ArchScopeAttr,
    ArchVisibilityAttr,
)
from kernel_gen.dialect import (
    Arch as ArchFromPackage,
    ArchGetBlockIdOp as ArchGetBlockIdOpFromPackage,
    ArchGetBlockNumOp as ArchGetBlockNumOpFromPackage,
    ArchGetDynamicMemoryOp as ArchGetDynamicMemoryOpFromPackage,
    ArchGetSubthreadIdOp as ArchGetSubthreadIdOpFromPackage,
    ArchGetSubthreadNumOp as ArchGetSubthreadNumOpFromPackage,
    ArchGetThreadIdOp as ArchGetThreadIdOpFromPackage,
    ArchGetThreadNumOp as ArchGetThreadNumOpFromPackage,
    ArchLaunchKernelOp as ArchLaunchKernelOpFromPackage,
)
import kernel_gen.dialect as dialect_pkg
from kernel_gen.dialect.nn import Nn, NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import Symbol, SymbolExprAttr, SymbolValueType
from kernel_gen.target import registry as target_registry


def _build_context() -> Context:
    """构造加载 builtin/test/symbol/nn/arch 的解析上下文。


    功能说明:
    - 为 arch dialect 的 parse/print 测试提供统一 context。

    使用示例:
    - _build_context()

    关联文件:
    - spec: spec/dialect/arch.md
    - test: test/dialect/test_arch.py
    - 功能实现: kernel_gen/dialect/arch.py
    """

    ctx = Context()
    ctx.load_dialect(Builtin)
    ctx.load_dialect(Test)
    ctx.load_dialect(Symbol)
    ctx.load_dialect(Nn)
    ctx.load_dialect(Arch)
    return ctx


def _print_ir(value: Attribute | Operation) -> str:
    """打印 attribute、operation 或 module 为文本。


    功能说明:
    - 为 arch dialect round-trip 测试提供稳定文本输出。

    使用示例:
    - _print_ir(module)

    关联文件:
    - spec: spec/dialect/arch.md
    - test: test/dialect/test_arch.py
    - 功能实现: kernel_gen/dialect/arch.py
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


def _make_space(name: str) -> NnMemorySpaceAttr:
    """构造 nn.space attribute。


    功能说明:
    - 为动态 memory 测试复用统一的 memory space 构造。

    使用示例:
    - _make_space("shared")

    关联文件:
    - spec: spec/dialect/arch.md
    - test: test/dialect/test_arch.py
    - 功能实现: kernel_gen/dialect/arch.py
    """

    return NnMemorySpaceAttr(StringAttr(name))


def _expr_attr(expr: str | int) -> SymbolExprAttr:
    """构造公开 SymbolExprAttr。

    功能说明:
    - 让 arch dialect 测试统一使用结构化 memory shape/stride 表达。

    使用示例:
    - _expr_attr("SM_SIZE")

    关联文件:
    - spec: spec/dialect/arch.md
    - test: test/dialect/test_arch.py
    - 功能实现: kernel_gen/dialect/arch.py
    """

    return SymbolExprAttr.from_expr(str(expr))


def _make_visibility(name: str) -> ArchVisibilityAttr:
    """构造 arch.visibility attribute。


    功能说明:
    - 为 `arch.barrier` 复用统一的聚合可见域构造。

    使用示例:
    - _make_visibility("tsm")

    关联文件:
    - spec: spec/dialect/arch.md
    - test: test/dialect/test_arch.py
    - 功能实现: kernel_gen/dialect/arch.py
    """

    return ArchVisibilityAttr.from_name(name)


def _make_barrier_visibility() -> ArrayAttr[Attribute]:
    """构造 `arch.barrier` 需要的 visibility 列表。


    功能说明:
    - 统一生成 `[#arch.visibility<tsm>, #arch.visibility<tlm>]` 供 barrier 成功路径与 round-trip 复用。

    使用示例:
    - _make_barrier_visibility()

    关联文件:
    - spec: spec/dialect/arch.md
    - test: test/dialect/test_arch.py
    - 功能实现: kernel_gen/dialect/arch.py
    """

    return ArrayAttr([_make_visibility("tsm"), _make_visibility("tlm")])


def _make_dynamic_memory_type(
    space: str = "shared",
    *,
    shape: ArrayAttr[Attribute] | None = None,
    stride: ArrayAttr[Attribute] | None = None,
    element_type: Attribute = i8,
) -> NnMemoryType:
    """构造用于 `arch.get_dynamic_memory` 的 nn.memory 类型。


    功能说明:
    - 默认构造合法的一维动态字节缓冲类型。

    使用示例:
    - _make_dynamic_memory_type()

    关联文件:
    - spec: spec/dialect/arch.md
    - test: test/dialect/test_arch.py
    - 功能实现: kernel_gen/dialect/arch.py
    """

    capacity_by_space = {
        "shared": "SM_SIZE",
        "local": "LM_SIZE",
        "tsm": "TSM_SIZE",
        "tlm1": "TLM1_SIZE",
        "tlm2": "TLM2_SIZE",
        "tlm3": "TLM3_SIZE",
    }
    return NnMemoryType(
        shape or ArrayAttr([_expr_attr(capacity_by_space[space])]),
        stride or ArrayAttr([_expr_attr(1)]),
        element_type,
        _make_space(space),
    )


def _make_symbol_value(expr: str) -> SSAValue:
    """构造携带 `!symbol.int<\"expr\">` 的测试 SSA value。


    功能说明:
    - 为 `arch.launch` 测试复用统一的 symbol.int operand 构造。

    使用示例:
    - _make_symbol_value("8")

    关联文件:
    - spec: spec/dialect/arch.md
    - test: test/dialect/test_arch.py
    - 功能实现: kernel_gen/dialect/arch.py
    """

    return _TestOp(result_types=[SymbolValueType.from_expr(expr)]).results[0]


def _assert_fixed_result_type(op: Operation, expected: str) -> None:
    """断言固定结果类型查询 op 的 verifier 与文本表示。


    功能说明:
    - 复用六个执行维度查询 op 的共性断言。

    使用示例:
    - _assert_fixed_result_type(ArchGetBlockIdOp(), "block_id")

    关联文件:
    - spec: spec/dialect/arch.md
    - test: test/dialect/test_arch.py
    - 功能实现: kernel_gen/dialect/arch.py
    """

    op.verify()
    result = op.results[0]
    assert result.type == SymbolValueType.from_expr(expected)
    assert _print_ir(op) == f"%0 = {op.name} : !symbol.int<#symbol.expr<{expected}>>"


# TC-ARCH-001
# 测试目的: 验证 arch.get_block_id 固定返回 !symbol.int<#symbol.expr<block_id>>。
# 对应功能实现文件路径: kernel_gen/dialect/arch.py
# 对应 spec 文件路径: spec/dialect/arch.md
def test_arch_get_block_id_result_type() -> None:
    _assert_fixed_result_type(ArchGetBlockIdOp(), "block_id")


# TC-ARCH-002
# 测试目的: 验证 arch.get_block_num 固定返回 !symbol.int<#symbol.expr<block_num>>。
# 对应功能实现文件路径: kernel_gen/dialect/arch.py
# 对应 spec 文件路径: spec/dialect/arch.md
def test_arch_get_block_num_result_type() -> None:
    _assert_fixed_result_type(ArchGetBlockNumOp(), "block_num")


# TC-ARCH-003
# 测试目的: 验证 arch.get_thread_id 固定返回 !symbol.int<#symbol.expr<thread_id>>。
# 对应功能实现文件路径: kernel_gen/dialect/arch.py
# 对应 spec 文件路径: spec/dialect/arch.md
def test_arch_get_thread_id_result_type() -> None:
    _assert_fixed_result_type(ArchGetThreadIdOp(), "thread_id")


# TC-ARCH-004
# 测试目的: 验证 arch.get_thread_num 固定返回 !symbol.int<#symbol.expr<thread_num>>。
# 对应功能实现文件路径: kernel_gen/dialect/arch.py
# 对应 spec 文件路径: spec/dialect/arch.md
def test_arch_get_thread_num_result_type() -> None:
    _assert_fixed_result_type(ArchGetThreadNumOp(), "thread_num")


# TC-ARCH-005
# 测试目的: 验证 arch.get_subthread_id 固定返回 !symbol.int<#symbol.expr<subthread_id>>。
# 对应功能实现文件路径: kernel_gen/dialect/arch.py
# 对应 spec 文件路径: spec/dialect/arch.md
def test_arch_get_subthread_id_result_type() -> None:
    _assert_fixed_result_type(ArchGetSubthreadIdOp(), "subthread_id")


# TC-ARCH-006
# 测试目的: 验证 arch.get_subthread_num 固定返回 !symbol.int<#symbol.expr<subthread_num>>。
# 对应功能实现文件路径: kernel_gen/dialect/arch.py
# 对应 spec 文件路径: spec/dialect/arch.md
def test_arch_get_subthread_num_result_type() -> None:
    _assert_fixed_result_type(ArchGetSubthreadNumOp(), "subthread_num")


# TC-ARCH-006A
# 测试目的: 验证 `#arch.scope<global>` 与 `#arch.visibility<tsm|tlm>` 可 parse/print/verifier。
# 对应功能实现文件路径: kernel_gen/dialect/arch.py
# 对应 spec 文件路径: spec/dialect/arch.md
def test_arch_scope_and_visibility_attr_round_trip() -> None:
    ctx = _build_context()

    scope = Parser(ctx, "#arch.scope<global>").parse_attribute()
    assert isinstance(scope, ArchScopeAttr)
    scope.verify()
    assert _print_ir(scope) == "#arch.scope<global>"

    for text in ["#arch.visibility<tsm>", "#arch.visibility<tlm>"]:
        visibility = Parser(ctx, text).parse_attribute()
        assert isinstance(visibility, ArchVisibilityAttr)
        visibility.verify()
        assert _print_ir(visibility) == text


# TC-ARCH-007
# 测试目的: 验证 arch.get_dynamic_memory 在合法 memory_space 与结果类型下可通过 verifier。
# 对应功能实现文件路径: kernel_gen/dialect/arch.py
# 对应 spec 文件路径: spec/dialect/arch.md
def test_arch_get_dynamic_memory_success() -> None:
    op = ArchGetDynamicMemoryOp(_make_space("shared"))
    op.verify()
    assert op.result.type == _make_dynamic_memory_type()
    assert _print_ir(op) == "%0 = arch.get_dynamic_memory #nn.space<shared> : !nn.memory<[#symbol.expr<SM_SIZE>], [#symbol.expr<1>], i8, #nn.space<shared>>"


# TC-ARCH-007A
# 测试目的: 验证 arch.get_dynamic_memory 支持 `tlm1/tlm2/tlm3` 三块动态内存文本。
# 对应功能实现文件路径: kernel_gen/dialect/arch.py
# 对应 spec 文件路径: spec/dialect/arch.md
def test_arch_get_dynamic_memory_supports_tlm123() -> None:
    for space in ("tlm1", "tlm2", "tlm3"):
        op = ArchGetDynamicMemoryOp(_make_space(space))
        op.verify()
        assert op.result.type == _make_dynamic_memory_type(space=space)
        assert _print_ir(op) == (
            f"%0 = arch.get_dynamic_memory #nn.space<{space}> : !nn.memory<[#symbol.expr<{space.upper()}_SIZE>], [#symbol.expr<1>], i8, #nn.space<{space}>>"
        )


# TC-ARCH-008
# 测试目的: 验证 arch.get_dynamic_memory 会拒绝非法 memory_space 或不符合规范的结果类型。
# 对应功能实现文件路径: kernel_gen/dialect/arch.py
# 对应 spec 文件路径: spec/dialect/arch.md
def test_arch_get_dynamic_memory_verify_errors() -> None:
    with pytest.raises(VerifyException, match="shared/local/tsm/tlm1/tlm2/tlm3"):
        ArchGetDynamicMemoryOp(_make_space("global")).verify()

    with pytest.raises(VerifyException, match="shared/local/tsm/tlm1/tlm2/tlm3"):
        ArchGetDynamicMemoryOp(_make_space("tlm")).verify()

    with pytest.raises(VerifyException, match="result must be 1-D"):
        ArchGetDynamicMemoryOp(
            _make_space("shared"),
            _make_dynamic_memory_type(
                shape=ArrayAttr([_expr_attr("?"), _expr_attr(4)]),
                stride=ArrayAttr([_expr_attr(4), _expr_attr(1)]),
            ),
        ).verify()

    with pytest.raises(VerifyException, match=r"result stride must be \[#symbol\.expr<1>\]"):
        ArchGetDynamicMemoryOp(
            _make_space("shared"),
            _make_dynamic_memory_type(stride=ArrayAttr([_expr_attr(2)])),
        ).verify()

    with pytest.raises(VerifyException, match="result element type must be i8"):
        ArchGetDynamicMemoryOp(
            _make_space("shared"),
            _make_dynamic_memory_type(element_type=i32),
        ).verify()

    with pytest.raises(VerifyException, match="result space must match memory_space"):
        ArchGetDynamicMemoryOp(
            _make_space("shared"),
            _make_dynamic_memory_type(space="local", shape=ArrayAttr([_expr_attr("SM_SIZE")])),
        ).verify()

    with pytest.raises(VerifyException, match="base attribute nn.memory"):
        ArchGetDynamicMemoryOp(_make_space("shared"), i32).verify()

    with pytest.raises(VerifyException, match="shape and stride rank must match"):
        ArchGetDynamicMemoryOp(
            _make_space("shared"),
            _make_dynamic_memory_type(stride=ArrayAttr([_expr_attr(1), _expr_attr(1)])),
        ).verify()

    with pytest.raises(VerifyException, match=r"result shape must be \[#symbol\.expr<SM_SIZE>\]"):
        ArchGetDynamicMemoryOp(
            _make_space("shared"),
            _make_dynamic_memory_type(shape=ArrayAttr([_expr_attr("LM_SIZE")])),
        ).verify()

    ctx = _build_context()
    with pytest.raises(VerifyException, match="memory_space must be #nn.space"):
        Parser(
            ctx,
            """
builtin.module {
  %mem = arch.get_dynamic_memory #arch.scope<block> : !nn.memory<[#symbol.expr<SM_SIZE>], [#symbol.expr<1>], i8, #nn.space<shared>>
}
""",
        ).parse_module()


# TC-ARCH-009
# 测试目的: 验证 arch.barrier 在合法 scope + [tsm, tlm] visibility 下通过 verifier 与 print。
# 使用示例: PYTHONPATH=. pytest -q test/dialect/test_arch.py -k test_arch_barrier_success
# 对应功能实现文件路径: kernel_gen/dialect/arch.py
# 对应 spec 文件路径: spec/dialect/arch.md
# 对应测试文件路径: test/dialect/test_arch.py
def test_arch_barrier_success() -> None:
    op = ArchBarrierOp(ArchScopeAttr.from_name("block"), _make_barrier_visibility())

    op.verify()
    assert _print_ir(op) == "arch.barrier {scope = #arch.scope<block>, visibility = [#arch.visibility<tsm>, #arch.visibility<tlm>]}"

    global_scope_op = ArchBarrierOp(ArchScopeAttr.from_name("global"), _make_barrier_visibility())
    global_scope_op.verify()
    assert _print_ir(global_scope_op) == (
        "arch.barrier {scope = #arch.scope<global>, visibility = [#arch.visibility<tsm>, #arch.visibility<tlm>]}"
    )


# TC-ARCH-010
# 测试目的: 验证 arch.barrier 会拒绝非法 scope、空 visibility、重复 visibility 与旧 nn.space visibility。
# 使用示例: PYTHONPATH=. pytest -q test/dialect/test_arch.py -k test_arch_barrier_verify_errors
# 对应功能实现文件路径: kernel_gen/dialect/arch.py
# 对应 spec 文件路径: spec/dialect/arch.md
# 对应测试文件路径: test/dialect/test_arch.py
def test_arch_barrier_verify_errors() -> None:
    with pytest.raises(VerifyException, match="arch.scope must be block/thread/subthread/global"):
        ArchBarrierOp(ArchScopeAttr.from_name("warp"), _make_barrier_visibility()).verify()

    with pytest.raises(VerifyException, match="visibility must not be empty"):
        ArchBarrierOp(ArchScopeAttr.from_name("block"), ArrayAttr([])).verify()

    with pytest.raises(VerifyException, match="visibility must not contain duplicates"):
        ArchBarrierOp(
            ArchScopeAttr.from_name("block"),
            ArrayAttr([_make_visibility("tsm"), _make_visibility("tsm")]),
        ).verify()

    with pytest.raises(VerifyException, match="visibility items must be #arch.visibility<...>"):
        ArchBarrierOp(
            ArchScopeAttr.from_name("block"),
            ArrayAttr([_make_visibility("tsm"), _make_space("tlm1")]),
        ).verify()

    with pytest.raises(VerifyException, match="base attribute array"):
        ArchBarrierOp(ArchScopeAttr.from_name("block"), _make_visibility("tsm")).verify()

    with pytest.raises(VerifyException, match="contain both"):
        ArchBarrierOp(ArchScopeAttr.from_name("block"), ArrayAttr([_make_visibility("tsm")])).verify()

    with pytest.raises(VerifyException, match="arch.visibility must be tsm/tlm"):
        _make_visibility("global")


# TC-ARCH-011
# 测试目的: 验证 arch.launch 使用 `arch.launch<...>(@callee, args...)` 文本与合法 verifier 边界。
# 使用示例: PYTHONPATH=. pytest -q test/dialect/test_arch.py -k test_arch_launch_success
# 对应功能实现文件路径: kernel_gen/dialect/arch.py
# 对应 spec 文件路径: spec/dialect/arch.md
# 对应测试文件路径: test/dialect/test_arch.py
def test_arch_launch_success() -> None:
    block = _make_symbol_value("grid_x")
    thread = _make_symbol_value("8")
    subthread = _make_symbol_value("1")
    shared_memory_size = _make_symbol_value("0")
    arg = _make_symbol_value("arg_n")
    op = ArchLaunchOp("my_kernel", block, thread, subthread, shared_memory_size, (arg,))

    op.verify()
    assert _print_ir(op) == (
        "arch.launch<%0, %1, %2, %3>(@my_kernel, %4) : (!symbol.int<#symbol.expr<arg_n>>) -> ()"
    )


# TC-ARCH-012
# 测试目的: 验证 arch.launch 会拒绝非法 callee 形态、非 symbol.int operand 与静态非法规模。
# 使用示例: PYTHONPATH=. pytest -q test/dialect/test_arch.py -k test_arch_launch_verify_errors
# 对应功能实现文件路径: kernel_gen/dialect/arch.py
# 对应 spec 文件路径: spec/dialect/arch.md
# 对应测试文件路径: test/dialect/test_arch.py
def test_arch_launch_verify_errors() -> None:
    non_symbol_value = _TestOp(result_types=[i32]).results[0]
    with pytest.raises(VerifyException, match="callee must be flat @symbol"):
        ArchLaunchOp(
            SymbolRefAttr("my_kernel", ["nested"]),
            _make_symbol_value("1"),
            _make_symbol_value("1"),
            _make_symbol_value("1"),
            _make_symbol_value("0"),
        ).verify()

    with pytest.raises(VerifyException, match="base attribute symbol_ref"):
        ArchLaunchOp(
            StringAttr("my_kernel"),
            _make_symbol_value("1"),
            _make_symbol_value("1"),
            _make_symbol_value("1"),
            _make_symbol_value("0"),
        ).verify()

    with pytest.raises(VerifyException, match="callee must not be empty"):
        ArchLaunchOp(
            SymbolRefAttr(""),
            _make_symbol_value("1"),
            _make_symbol_value("1"),
            _make_symbol_value("1"),
            _make_symbol_value("0"),
        ).verify()

    with pytest.raises(VerifyException, match='block must have type !symbol.int<#symbol.expr<expr>>'):
        ArchLaunchOp(
            "my_kernel",
            non_symbol_value,
            _make_symbol_value("1"),
            _make_symbol_value("1"),
            _make_symbol_value("0"),
        ).verify()

    with pytest.raises(VerifyException, match="thread must be > 0 when statically known"):
        ArchLaunchOp(
            "my_kernel",
            _make_symbol_value("1"),
            _make_symbol_value("0"),
            _make_symbol_value("1"),
            _make_symbol_value("0"),
        ).verify()

    with pytest.raises(VerifyException, match="subthread must be > 0 when statically known"):
        ArchLaunchOp(
            "my_kernel",
            _make_symbol_value("1"),
            _make_symbol_value("1"),
            _make_symbol_value("-1"),
            _make_symbol_value("0"),
        ).verify()

    with pytest.raises(VerifyException, match="shared_memory_size must be >= 0 when statically known"):
        ArchLaunchOp(
            "my_kernel",
            _make_symbol_value("1"),
            _make_symbol_value("1"),
            _make_symbol_value("1"),
            _make_symbol_value("-1"),
        ).verify()


# TC-ARCH-012A
# 测试目的: 验证 arch 固定查询与 launch parser 对公开结果/参数类型段的失败边界。
# 对应功能实现文件路径: kernel_gen/dialect/arch.py
# 对应 spec 文件路径: spec/dialect/arch.md
def test_arch_result_and_launch_parser_rejection_edges() -> None:
    with pytest.raises(VerifyException, match="base attribute symbol.int"):
        ArchGetBlockIdOp(i32).verify()

    ctx = _build_context()
    common_prefix = """
builtin.module {
  %block = "test.op"() : () -> !symbol.int<#symbol.expr<1>>
  %thread = "test.op"() : () -> !symbol.int<#symbol.expr<1>>
  %subthread = "test.op"() : () -> !symbol.int<#symbol.expr<1>>
  %smem = "test.op"() : () -> !symbol.int<#symbol.expr<0>>
  %arg = "test.op"() : () -> !symbol.int<#symbol.expr<N>>
"""
    with pytest.raises(VerifyException, match="result types must be"):
        Parser(
            ctx,
            common_prefix
            + """
  arch.launch<%block, %thread, %subthread, %smem>(@my_kernel) : () -> (!symbol.int<#symbol.expr<N>>)
}
""",
        ).parse_module()

    with pytest.raises(VerifyException, match="arg type list must match operand count"):
        Parser(
            ctx,
            common_prefix
            + """
  arch.launch<%block, %thread, %subthread, %smem>(@my_kernel, %arg) : () -> ()
}
""",
        ).parse_module()

    with pytest.raises(VerifyException, match="arg types must match operand types"):
        Parser(
            ctx,
            common_prefix
            + """
  arch.launch<%block, %thread, %subthread, %smem>(@my_kernel, %arg) : (i32) -> ()
}
""",
        ).parse_module()


# TC-ARCH-013
# 测试目的: 验证 arch dialect 文本可完成包含 barrier/launch 的 parse/print round-trip，并拒绝字符串 callee。
# 使用示例: PYTHONPATH=. pytest -q test/dialect/test_arch.py -k test_arch_parse_print_round_trip
# 对应功能实现文件路径: kernel_gen/dialect/arch.py
# 对应 spec 文件路径: spec/dialect/arch.md
# 对应测试文件路径: test/dialect/test_arch.py
def test_arch_parse_print_round_trip() -> None:
    ctx = _build_context()
    module = Parser(
        ctx,
        """
builtin.module {
  %block = "test.op"() : () -> !symbol.int<#symbol.expr<grid_x>>
  %thread = "test.op"() : () -> !symbol.int<#symbol.expr<block_x>>
  %subthread = "test.op"() : () -> !symbol.int<#symbol.expr<subthread_x>>
  %arg = "test.op"() : () -> !symbol.int<#symbol.expr<arg_n>>
  %bid = arch.get_block_id : !symbol.int<#symbol.expr<block_id>>
  %bnum = arch.get_block_num : !symbol.int<#symbol.expr<block_num>>
  %tid = arch.get_thread_id : !symbol.int<#symbol.expr<thread_id>>
  %tnum = arch.get_thread_num : !symbol.int<#symbol.expr<thread_num>>
  %stid = arch.get_subthread_id : !symbol.int<#symbol.expr<subthread_id>>
  %stnum = arch.get_subthread_num : !symbol.int<#symbol.expr<subthread_num>>
  %smem_size = arch.get_dynamic_memory #nn.space<shared> : !nn.memory<[#symbol.expr<SM_SIZE>], [#symbol.expr<1>], i8, #nn.space<shared>>
  %tlm1 = arch.get_dynamic_memory #nn.space<tlm1> : !nn.memory<[#symbol.expr<TLM1_SIZE>], [#symbol.expr<1>], i8, #nn.space<tlm1>>
  arch.barrier {scope = #arch.scope<global>, visibility = [#arch.visibility<tsm>, #arch.visibility<tlm>]}
  %smem = "test.op"() : () -> !symbol.int<#symbol.expr<smem_n>>
  arch.launch<%block, %thread, %subthread, %smem>(@my_kernel, %arg) : (!symbol.int<#symbol.expr<arg_n>>) -> ()
}
""",
    ).parse_module()

    module.verify()
    printed = _print_ir(module).rstrip()
    reparsed = Parser(ctx, printed).parse_module()
    reparsed.verify()
    assert _print_ir(reparsed).rstrip() == printed

    invalid_module = Parser(
        ctx,
        """
builtin.module {
  %block = "test.op"() : () -> !symbol.int<#symbol.expr<grid_x>>
  %thread = "test.op"() : () -> !symbol.int<#symbol.expr<block_x>>
  %subthread = "test.op"() : () -> !symbol.int<#symbol.expr<subthread_x>>
  %smem = "test.op"() : () -> !symbol.int<#symbol.expr<smem_n>>
  arch.launch<%block, %thread, %subthread, %smem>("my_kernel") : () -> ()
}
""",
    ).parse_module()
    with pytest.raises(VerifyException, match="symbol_ref|callee must be @symbol"):
        invalid_module.verify()


# TC-ARCH-012
# 测试目的: 验证 kernel_gen.dialect 的包级导出已包含 9 个 arch 公开符号并与实现同一。
# 对应功能实现文件路径: kernel_gen/dialect/__init__.py
# 对应 spec 文件路径: spec/dialect/arch.md
def test_arch_package_exports() -> None:
    expected_arch_exports = {
        "Arch",
        "ArchGetBlockIdOp",
        "ArchGetBlockNumOp",
        "ArchGetThreadIdOp",
        "ArchGetThreadNumOp",
        "ArchGetSubthreadIdOp",
        "ArchGetSubthreadNumOp",
        "ArchGetDynamicMemoryOp",
        "ArchLaunchKernelOp",
    }

    assert ArchFromPackage is Arch
    assert ArchGetBlockIdOpFromPackage is ArchGetBlockIdOp
    assert ArchGetBlockNumOpFromPackage is ArchGetBlockNumOp
    assert ArchGetThreadIdOpFromPackage is ArchGetThreadIdOp
    assert ArchGetThreadNumOpFromPackage is ArchGetThreadNumOp
    assert ArchGetSubthreadIdOpFromPackage is ArchGetSubthreadIdOp
    assert ArchGetSubthreadNumOpFromPackage is ArchGetSubthreadNumOp
    assert ArchGetDynamicMemoryOpFromPackage is ArchGetDynamicMemoryOp
    assert ArchLaunchKernelOpFromPackage is ArchLaunchKernelOp
    assert {name for name in expected_arch_exports if hasattr(dialect_pkg, name)} == expected_arch_exports


# TC-ARCH-013
# 测试目的: 验证 cpu target 下拒绝 arch.get_thread_id。
# 对应功能实现文件路径: kernel_gen/dialect/arch.py
# 对应 spec 文件路径: spec/dialect/arch.md
def test_target_registry_cpu_rejects_thread_id() -> None:
    target_registry.set_current_target("cpu")
    try:
        with pytest.raises(VerifyException, match="arch.get_thread_id"):
            ArchGetThreadIdOp().verify()
    finally:
        target_registry.set_current_target(None)
