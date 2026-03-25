"""arch dialect tests.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 覆盖 arch dialect 的固定结果类型查询、动态 memory 入口与 kernel 启动描述的 parse/print 与 verifier。

使用示例:
- pytest -q test/dialect/test_arch_dialect.py

当前覆盖率信息:
- 不再要求覆盖率；本文件以功能测试闭环为准。

覆盖率命令:
- 不再要求覆盖率命令；本文件以功能测试闭环为准。

关联文件:
- 功能实现: kernel_gen/dialect/arch.py
- Spec 文档: spec/dialect/arch.md
- 测试文件: test/dialect/test_arch_dialect.py
"""

from __future__ import annotations

from io import StringIO
import sys
from pathlib import Path

import pytest
from xdsl.context import Context
from xdsl.dialects.builtin import ArrayAttr, Builtin, IntAttr, StringAttr, i8, i32
from xdsl.dialects.test import Test, TestOp as _TestOp
from xdsl.ir import Attribute, Operation, SSAValue
from xdsl.parser import Parser
from xdsl.printer import Printer
from xdsl.utils.exceptions import ParseError, VerifyException

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.arch import (
    Arch,
    ArchGetBlockIdOp,
    ArchGetBlockNumOp,
    ArchGetDynamicMemoryOp,
    ArchGetSubthreadIdOp,
    ArchGetSubthreadNumOp,
    ArchGetThreadIdOp,
    ArchGetThreadNumOp,
    ArchLaunchKernelOp,
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
from kernel_gen.dialect.symbol import Symbol, SymbolValueType
from kernel_gen.target import registry as target_registry


def _build_context() -> Context:
    """构造加载 builtin/test/symbol/nn/arch 的解析上下文。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 为 arch dialect 的 parse/print 测试提供统一 context。

    使用示例:
    - _build_context()

    关联文件:
    - spec: spec/dialect/arch.md
    - test: test/dialect/test_arch_dialect.py
    - 功能实现: kernel_gen/dialect/arch.py
    """

    ctx = Context()
    ctx.load_dialect(Builtin)
    ctx.load_dialect(Test)
    ctx.load_dialect(Symbol)
    ctx.load_dialect(Nn)
    ctx.load_dialect(Arch)
    return ctx


def _print_ir(value: object) -> str:
    """打印 attribute、operation 或 module 为文本。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 为 arch dialect round-trip 测试提供稳定文本输出。

    使用示例:
    - _print_ir(module)

    关联文件:
    - spec: spec/dialect/arch.md
    - test: test/dialect/test_arch_dialect.py
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

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 为动态 memory 测试复用统一的 memory space 构造。

    使用示例:
    - _make_space("shared")

    关联文件:
    - spec: spec/dialect/arch.md
    - test: test/dialect/test_arch_dialect.py
    - 功能实现: kernel_gen/dialect/arch.py
    """

    return NnMemorySpaceAttr(StringAttr(name))


def _make_dynamic_memory_type(
    space: str = "shared",
    *,
    shape: ArrayAttr[Attribute] | None = None,
    stride: ArrayAttr[Attribute] | None = None,
    element_type: Attribute = i8,
) -> NnMemoryType:
    """构造用于 `arch.get_dynamic_memory` 的 nn.memory 类型。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 默认构造合法的一维动态字节缓冲类型。

    使用示例:
    - _make_dynamic_memory_type()

    关联文件:
    - spec: spec/dialect/arch.md
    - test: test/dialect/test_arch_dialect.py
    - 功能实现: kernel_gen/dialect/arch.py
    """

    return NnMemoryType(
        shape or ArrayAttr([StringAttr("?")]),
        stride or ArrayAttr([IntAttr(1)]),
        element_type,
        _make_space(space),
    )


def _make_symbol_value(expr: str) -> SSAValue:
    """构造携带 `!symbol.int<\"expr\">` 的测试 SSA value。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 为 `arch.launch_kernel` 测试复用统一的 symbol.int operand 构造。

    使用示例:
    - _make_symbol_value("8")

    关联文件:
    - spec: spec/dialect/arch.md
    - test: test/dialect/test_arch_dialect.py
    - 功能实现: kernel_gen/dialect/arch.py
    """

    return _TestOp(result_types=[SymbolValueType.from_expr(expr)]).results[0]


def _assert_fixed_result_type(op: Operation, expected: str) -> None:
    """断言固定结果类型查询 op 的 verifier 与文本表示。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 复用六个执行维度查询 op 的共性断言。

    使用示例:
    - _assert_fixed_result_type(ArchGetBlockIdOp(), "block_id")

    关联文件:
    - spec: spec/dialect/arch.md
    - test: test/dialect/test_arch_dialect.py
    - 功能实现: kernel_gen/dialect/arch.py
    """

    op.verify()
    result = op.results[0]
    assert result.type == SymbolValueType.from_expr(expected)
    assert _print_ir(op) == f"%0 = {op.name} : !symbol.int<\"{expected}\">"


# TC-ARCH-001
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 04:30:00 +0800
# 最近一次运行成功时间: 2026-03-25 04:30:00 +0800
# 测试目的: 验证 arch.get_block_id 固定返回 !symbol.int<"block_id">。
# 对应功能实现文件路径: kernel_gen/dialect/arch.py
# 对应 spec 文件路径: spec/dialect/arch.md
def test_arch_get_block_id_result_type() -> None:
    _assert_fixed_result_type(ArchGetBlockIdOp(), "block_id")


# TC-ARCH-002
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 04:30:00 +0800
# 最近一次运行成功时间: 2026-03-25 04:30:00 +0800
# 测试目的: 验证 arch.get_block_num 固定返回 !symbol.int<"block_num">。
# 对应功能实现文件路径: kernel_gen/dialect/arch.py
# 对应 spec 文件路径: spec/dialect/arch.md
def test_arch_get_block_num_result_type() -> None:
    _assert_fixed_result_type(ArchGetBlockNumOp(), "block_num")


# TC-ARCH-003
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 04:30:00 +0800
# 最近一次运行成功时间: 2026-03-25 04:30:00 +0800
# 测试目的: 验证 arch.get_thread_id 固定返回 !symbol.int<"thread_id">。
# 对应功能实现文件路径: kernel_gen/dialect/arch.py
# 对应 spec 文件路径: spec/dialect/arch.md
def test_arch_get_thread_id_result_type() -> None:
    _assert_fixed_result_type(ArchGetThreadIdOp(), "thread_id")


# TC-ARCH-004
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 04:30:00 +0800
# 最近一次运行成功时间: 2026-03-25 04:30:00 +0800
# 测试目的: 验证 arch.get_thread_num 固定返回 !symbol.int<"thread_num">。
# 对应功能实现文件路径: kernel_gen/dialect/arch.py
# 对应 spec 文件路径: spec/dialect/arch.md
def test_arch_get_thread_num_result_type() -> None:
    _assert_fixed_result_type(ArchGetThreadNumOp(), "thread_num")


# TC-ARCH-005
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 04:30:00 +0800
# 最近一次运行成功时间: 2026-03-25 04:30:00 +0800
# 测试目的: 验证 arch.get_subthread_id 固定返回 !symbol.int<"subthread_id">。
# 对应功能实现文件路径: kernel_gen/dialect/arch.py
# 对应 spec 文件路径: spec/dialect/arch.md
def test_arch_get_subthread_id_result_type() -> None:
    _assert_fixed_result_type(ArchGetSubthreadIdOp(), "subthread_id")


# TC-ARCH-006
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 04:30:00 +0800
# 最近一次运行成功时间: 2026-03-25 04:30:00 +0800
# 测试目的: 验证 arch.get_subthread_num 固定返回 !symbol.int<"subthread_num">。
# 对应功能实现文件路径: kernel_gen/dialect/arch.py
# 对应 spec 文件路径: spec/dialect/arch.md
def test_arch_get_subthread_num_result_type() -> None:
    _assert_fixed_result_type(ArchGetSubthreadNumOp(), "subthread_num")


# TC-ARCH-007
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 04:30:00 +0800
# 最近一次运行成功时间: 2026-03-25 04:30:00 +0800
# 测试目的: 验证 arch.get_dynamic_memory 在合法 memory_space 与结果类型下可通过 verifier。
# 对应功能实现文件路径: kernel_gen/dialect/arch.py
# 对应 spec 文件路径: spec/dialect/arch.md
def test_arch_get_dynamic_memory_success() -> None:
    op = ArchGetDynamicMemoryOp(_make_space("shared"))
    op.verify()
    assert op.result.type == _make_dynamic_memory_type()
    assert _print_ir(op) == "%0 = arch.get_dynamic_memory #nn.space<shared> : !nn.memory<[?], [1], i8, #nn.space<shared>>"


# TC-ARCH-008
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 04:30:00 +0800
# 最近一次运行成功时间: 2026-03-25 04:30:00 +0800
# 测试目的: 验证 arch.get_dynamic_memory 会拒绝非法 memory_space 或不符合规范的结果类型。
# 对应功能实现文件路径: kernel_gen/dialect/arch.py
# 对应 spec 文件路径: spec/dialect/arch.md
def test_arch_get_dynamic_memory_verify_errors() -> None:
    with pytest.raises(VerifyException, match="shared/local/tsm/tlm"):
        ArchGetDynamicMemoryOp(_make_space("global")).verify()

    with pytest.raises(VerifyException, match="result must be 1-D"):
        ArchGetDynamicMemoryOp(
            _make_space("shared"),
            _make_dynamic_memory_type(
                shape=ArrayAttr([StringAttr("?"), IntAttr(4)]),
                stride=ArrayAttr([IntAttr(4), IntAttr(1)]),
            ),
        ).verify()

    with pytest.raises(VerifyException, match="result stride must be \\[1\\]"):
        ArchGetDynamicMemoryOp(
            _make_space("shared"),
            _make_dynamic_memory_type(stride=ArrayAttr([IntAttr(2)])),
        ).verify()

    with pytest.raises(VerifyException, match="result element type must be i8"):
        ArchGetDynamicMemoryOp(
            _make_space("shared"),
            _make_dynamic_memory_type(element_type=i32),
        ).verify()

    with pytest.raises(VerifyException, match="result space must match memory_space"):
        ArchGetDynamicMemoryOp(
            _make_space("shared"),
            _make_dynamic_memory_type(space="local"),
        ).verify()


# TC-ARCH-009
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 04:30:00 +0800
# 最近一次运行成功时间: 2026-03-25 04:30:00 +0800
# 测试目的: 验证 arch.launch_kernel 在非空名称与合法 symbol.int 启动规模下可通过 verifier。
# 对应功能实现文件路径: kernel_gen/dialect/arch.py
# 对应 spec 文件路径: spec/dialect/arch.md
def test_arch_launch_kernel_success() -> None:
    op = ArchLaunchKernelOp("my_kernel", _make_symbol_value("grid_x"), _make_symbol_value("8"), _make_symbol_value("1"))
    op.verify()
    assert _print_ir(op) == (
        'arch.launch_kernel "my_kernel", %0, %1, %2 : '
        '!symbol.int<"grid_x">, !symbol.int<"8">, !symbol.int<"1">'
    )


# TC-ARCH-010
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 04:30:00 +0800
# 最近一次运行成功时间: 2026-03-25 04:30:00 +0800
# 测试目的: 验证 arch.launch_kernel 会拒绝空名称、非 symbol.int operand 与静态非法规模。
# 对应功能实现文件路径: kernel_gen/dialect/arch.py
# 对应 spec 文件路径: spec/dialect/arch.md
def test_arch_launch_kernel_verify_errors() -> None:
    with pytest.raises(VerifyException, match="kernel name must not be empty"):
        ArchLaunchKernelOp("", _make_symbol_value("1"), _make_symbol_value("1"), _make_symbol_value("1")).verify()

    non_symbol_value = _TestOp(result_types=[i32]).results[0]
    with pytest.raises(VerifyException, match='block must have type !symbol.int<"expr">'):
        ArchLaunchKernelOp("my_kernel", non_symbol_value, _make_symbol_value("1"), _make_symbol_value("1")).verify()

    with pytest.raises(VerifyException, match="thread must be > 0 when statically known"):
        ArchLaunchKernelOp("my_kernel", _make_symbol_value("1"), _make_symbol_value("0"), _make_symbol_value("1")).verify()

    with pytest.raises(VerifyException, match="subthread must be > 0 when statically known"):
        ArchLaunchKernelOp("my_kernel", _make_symbol_value("1"), _make_symbol_value("1"), _make_symbol_value("-1")).verify()


# TC-ARCH-011
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 04:30:00 +0800
# 最近一次运行成功时间: 2026-03-25 04:30:00 +0800
# 测试目的: 验证 arch dialect 文本可完成 parse/print round-trip，并对不完整 launch 签名给出 parse 错误。
# 对应功能实现文件路径: kernel_gen/dialect/arch.py
# 对应 spec 文件路径: spec/dialect/arch.md
def test_arch_parse_print_round_trip() -> None:
    ctx = _build_context()
    module = Parser(
        ctx,
        """
builtin.module {
  %block = "test.op"() : () -> !symbol.int<"grid_x">
  %thread = "test.op"() : () -> !symbol.int<"block_x">
  %subthread = "test.op"() : () -> !symbol.int<"subthread_x">
  %bid = arch.get_block_id : !symbol.int<"block_id">
  %bnum = arch.get_block_num : !symbol.int<"block_num">
  %tid = arch.get_thread_id : !symbol.int<"thread_id">
  %tnum = arch.get_thread_num : !symbol.int<"thread_num">
  %stid = arch.get_subthread_id : !symbol.int<"subthread_id">
  %stnum = arch.get_subthread_num : !symbol.int<"subthread_num">
  %smem = arch.get_dynamic_memory #nn.space<shared> : !nn.memory<[?], [1], i8, #nn.space<shared>>
  arch.launch_kernel "my_kernel", %block, %thread, %subthread : !symbol.int<"grid_x">, !symbol.int<"block_x">, !symbol.int<"subthread_x">
}
""",
    ).parse_module()

    module.verify()
    printed = _print_ir(module).rstrip()
    reparsed = Parser(ctx, printed).parse_module()
    reparsed.verify()
    assert _print_ir(reparsed).rstrip() == printed

    with pytest.raises(ParseError, match="arch.launch_kernel"):
        Parser(
            ctx,
            """
builtin.module {
  %block = "test.op"() : () -> !symbol.int<"grid_x">
  %thread = "test.op"() : () -> !symbol.int<"block_x">
  arch.launch_kernel "my_kernel", %block, %thread : !symbol.int<"grid_x">, !symbol.int<"block_x">
}
""",
        ).parse_module()


# TC-ARCH-012
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 04:33:15 +0800
# 最近一次运行成功时间: 2026-03-25 04:33:15 +0800
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
    assert expected_arch_exports <= set(dialect_pkg.__all__)
    assert {name for name in dialect_pkg.__all__ if name.startswith("Arch")} == expected_arch_exports


# TC-ARCH-013
# 创建者: 我不是牛马
# 最后一次更改: 我不是牛马
# 最近一次运行测试时间: 2026-03-26 01:38:06 +0800
# 最近一次运行成功时间: 2026-03-26 01:38:06 +0800
# 测试目的: 验证 cpu target 下拒绝 arch.get_thread_id。
# 对应功能实现文件路径: kernel_gen/dialect/arch.py
# 对应 spec 文件路径: spec/dialect/arch.md
def test_target_registry_cpu_rejects_thread_id() -> None:
    target_registry._set_current_target("cpu")
    try:
        with pytest.raises(VerifyException, match="arch.get_thread_id"):
            ArchGetThreadIdOp().verify()
    finally:
        target_registry._set_current_target(None)
