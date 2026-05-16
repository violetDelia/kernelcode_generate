"""arch-parallelize pass tests.


功能说明:
- 验证 `ArchParallelizePass` 的公开 Python API、registry CLI 入口、IR 改写和稳定失败边界。
- 测试只通过公开 pass API、target registry API 与 `run_ircheck_text(...)` 入口触达行为。

使用示例:
- pytest -q test/passes/test_arch_parallelize.py

关联文件:
- 功能实现: kernel_gen/passes/arch_parallelize.py
- Spec 文档: spec/pass/arch_parallelize.md
- 测试文件: test/passes/test_arch_parallelize.py
"""

from __future__ import annotations

import pytest

from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import FunctionType, ModuleOp, i32
from xdsl.ir import Block, Region

from kernel_gen.core.error import KernelCodeError
from kernel_gen.passes.arch_parallelize import ArchParallelizePass
from kernel_gen.target import registry as target_registry
from kernel_gen.tools.ircheck import run_ircheck_text


def _empty_void_module(name: str = "kernel") -> ModuleOp:
    """构造仅包含 `func.return` 的公开测试 module。

    功能说明:
    - 为参数、target 与 no-loop 路径测试提供最小 `builtin.module`。

    使用示例:
    - module = _empty_void_module()
    """

    block = Block()
    block.add_op(func.ReturnOp())
    return ModuleOp([func.FuncOp(name, FunctionType.from_lists([], []), Region(block))])


def _return_value_module() -> ModuleOp:
    """构造有返回值的非法函数 module。

    功能说明:
    - 用于验证 `ArchParallelizePass` 拒绝非 void return。

    使用示例:
    - module = _return_value_module()
    """

    block = Block()
    block.add_op(func.ReturnOp())
    return ModuleOp([func.FuncOp("returns_value", FunctionType.from_lists([], [i32]), Region(block))])


def _multi_block_void_module() -> ModuleOp:
    """构造 multi-block 函数体的非法 module。

    功能说明:
    - 用于验证 `ArchParallelizePass` 拒绝 multi-block func body。

    使用示例:
    - module = _multi_block_void_module()
    """

    first_block = Block()
    first_block.add_op(func.ReturnOp())
    second_block = Block()
    second_block.add_op(func.ReturnOp())
    return ModuleOp(
        [
            func.FuncOp(
                "multi_block",
                FunctionType.from_lists([], []),
                Region([first_block, second_block]),
            )
        ]
    )


def _register_target_once(spec: target_registry.TargetSpec) -> None:
    """按公开 target registry API 注册测试 target。

    功能说明:
    - 重复运行同一 Python 进程时，已存在的同名 target 视为可复用状态。

    使用示例:
    - _register_target_once(TargetSpec(...))
    """

    try:
        target_registry.register_target(spec)
    except ValueError as exc:
        if "target already registered" not in str(exc):
            raise


# TC-PASS-ARCH-PARALLELIZE-001
# 功能说明: 验证单顶层 `symbol.for` 被改写为 block-strided work sharing。
# 使用示例: pytest -q test/passes/test_arch_parallelize.py -k test_arch_parallelize_rewrites_single_top_level_loop
def test_arch_parallelize_rewrites_single_top_level_loop() -> None:
    case_text = """// COMPILE_ARGS: --pass "arch-parallelize={target=npu_demo,parallel_level=block}"
// CHECK: %[[BID:{reg}]] = arch.get_block_id : !symbol.int<#symbol.expr<block_id>>
// CHECK: %[[BNUM:{reg}]] = symbol.const 1 : !symbol.int<#symbol.expr<1>>
// CHECK: %[[BID_STEP:{reg}]] = symbol.mul %[[BID]], %[[STEP:{reg}]]
// CHECK: %[[NEW_START:{reg}]] = symbol.add %[[START:{reg}]], %[[BID_STEP]]
// CHECK: %[[NEW_STEP:{reg}]] = symbol.mul %[[STEP]], %[[BNUM]]
// CHECK: symbol.for %[[IV:{reg}]] = %[[NEW_START]] to %[[END:{reg}]] step %[[NEW_STEP]]

builtin.module {
  func.func @loop_kernel() {
    %0 = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    %1 = symbol.const 16 : !symbol.int<#symbol.expr<16>>
    %2 = symbol.const 4 : !symbol.int<#symbol.expr<4>>
    symbol.for %i = %0 to %1 step %2 {iter = #symbol.iter<start = #symbol.expr<0>, end = #symbol.expr<16>, step = #symbol.expr<4>>} {
      %body = symbol.const 1 : !symbol.int<#symbol.expr<1>>
    }
    func.return
  }
}
"""
    result = run_ircheck_text(case_text, source_path="test/passes/test_arch_parallelize.py")
    assert result.ok is True, result.message


# TC-PASS-ARCH-PARALLELIZE-002
# 功能说明: 验证无 loop 函数被包裹为 block0 guard，且 `func.return` 保持在 `scf.if` 后。
# 使用示例: pytest -q test/passes/test_arch_parallelize.py -k test_arch_parallelize_wraps_no_loop_body_in_block0_guard
def test_arch_parallelize_wraps_no_loop_body_in_block0_guard() -> None:
    case_text = """// COMPILE_ARGS: --pass "arch-parallelize={target=npu_demo,parallel_level=block}"
// CHECK: %[[BID:{reg}]] = arch.get_block_id : !symbol.int<#symbol.expr<block_id>>
// CHECK: %[[ZERO:{reg}]] = symbol.const 0 : !symbol.int<#symbol.expr<0>>
// CHECK: %[[NOT_BLOCK0:{reg}]] = symbol.ne %[[BID]], %[[ZERO]]
// CHECK: scf.if %[[NOT_BLOCK0]] {
// CHECK: } else {
// CHECK: %[[BODY:{reg}]] = symbol.const 7 : !symbol.int<#symbol.expr<7>>
// CHECK: func.return

builtin.module {
  func.func @scalar_kernel() {
    %0 = symbol.const 7 : !symbol.int<#symbol.expr<7>>
    func.return
  }
}
"""
    result = run_ircheck_text(case_text, source_path="test/passes/test_arch_parallelize.py")
    assert result.ok is True, result.message
    assert result.actual_ir.rfind("scf.if") < result.actual_ir.rfind("func.return")


# TC-PASS-ARCH-PARALLELIZE-003
# 功能说明: 验证动态嵌套 loop 只改写外层顶层 loop。
# 使用示例: pytest -q test/passes/test_arch_parallelize.py -k test_arch_parallelize_rewrites_only_outer_dynamic_loop
def test_arch_parallelize_rewrites_only_outer_dynamic_loop() -> None:
    case_text = """// COMPILE_ARGS: --pass "arch-parallelize={target=npu_demo,parallel_level=block}"
// CHECK: func.func @dynamic_nested(%[[N:{reg}]] : !symbol.int<#symbol.expr<N>>, %[[M:{reg}]] : !symbol.int<#symbol.expr<M>>, %[[OUTER_STEP:{reg}]] : !symbol.int<#symbol.expr<TILE_M>>, %[[INNER_STEP:{reg}]] : !symbol.int<#symbol.expr<TILE_N>>)
// CHECK: %[[ZERO:{reg}]] = symbol.const 0 : !symbol.int<#symbol.expr<0>>
// CHECK: %[[BID:{reg}]] = arch.get_block_id : !symbol.int<#symbol.expr<block_id>>
// CHECK: %[[BNUM:{reg}]] = symbol.const 1 : !symbol.int<#symbol.expr<1>>
// CHECK: %[[BID_STEP:{reg}]] = symbol.mul %[[BID]], %[[OUTER_STEP]]
// CHECK: %[[NEW_START:{reg}]] = symbol.add %[[ZERO]], %[[BID_STEP]]
// CHECK: %[[NEW_STEP:{reg}]] = symbol.mul %[[OUTER_STEP]], %[[BNUM]]
// CHECK: symbol.for %[[I:{reg}]] = %[[NEW_START]] to %[[N]] step %[[NEW_STEP]]
// CHECK: symbol.for %[[J:{reg}]] = %[[ZERO]] to %[[M]] step %[[INNER_STEP]]

builtin.module {
  func.func @dynamic_nested(%n : !symbol.int<#symbol.expr<N>>, %m : !symbol.int<#symbol.expr<M>>, %outer_step : !symbol.int<#symbol.expr<TILE_M>>, %inner_step : !symbol.int<#symbol.expr<TILE_N>>) {
    %0 = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    symbol.for %i = %0 to %n step %outer_step {iter = #symbol.iter<start = #symbol.expr<0>, end = #symbol.expr<N>, step = #symbol.expr<TILE_M>>} {
      symbol.for %j = %0 to %m step %inner_step {iter = #symbol.iter<start = #symbol.expr<0>, end = #symbol.expr<M>, step = #symbol.expr<TILE_N>>} {
        %one = symbol.const 1 : !symbol.int<#symbol.expr<1>>
      }
    }
    func.return
  }
}
"""
    result = run_ircheck_text(case_text, source_path="test/passes/test_arch_parallelize.py")
    assert result.ok is True, result.message


# TC-PASS-ARCH-PARALLELIZE-004
# 功能说明: 验证 module 中每个非声明函数独立处理。
# 使用示例: pytest -q test/passes/test_arch_parallelize.py -k test_arch_parallelize_processes_each_non_declaration_func
def test_arch_parallelize_processes_each_non_declaration_func() -> None:
    case_text = """// COMPILE_ARGS: --pass "arch-parallelize={target=npu_demo,parallel_level=block}"
// CHECK: func.func @first()
// CHECK: arch.get_block_id
// CHECK: func.func @second()
// CHECK: arch.get_block_id

builtin.module {
  func.func @first() {
    func.return
  }
  func.func @second() {
    func.return
  }
}
"""
    result = run_ircheck_text(case_text, source_path="test/passes/test_arch_parallelize.py")
    assert result.ok is True, result.message
    assert result.actual_ir.count("arch.get_block_id") == 2


# TC-PASS-ARCH-PARALLELIZE-005
# 功能说明: 验证已有 block 语义的函数被跳过。
# 使用示例: pytest -q test/passes/test_arch_parallelize.py -k test_arch_parallelize_skips_existing_block_parallel_func
def test_arch_parallelize_skips_existing_block_parallel_func() -> None:
    case_text = """// COMPILE_ARGS: --pass "arch-parallelize={target=npu_demo,parallel_level=block}"
// CHECK: func.func @already_parallel()
// CHECK: arch.get_block_id
// CHECK: func.return

builtin.module {
  func.func @already_parallel() {
    %0 = arch.get_block_id : !symbol.int<#symbol.expr<block_id>>
    func.return
  }
}
"""
    result = run_ircheck_text(case_text, source_path="test/passes/test_arch_parallelize.py")
    assert result.ok is True, result.message
    assert result.actual_ir.count("arch.get_block_id") == 1


# TC-PASS-ARCH-PARALLELIZE-006
# 功能说明: 验证多个顶层 `symbol.for` 稳定失败。
# 使用示例: pytest -q test/passes/test_arch_parallelize.py -k test_arch_parallelize_rejects_multiple_top_level_loops
def test_arch_parallelize_rejects_multiple_top_level_loops() -> None:
    case_text = """// COMPILE_ARGS: --pass "arch-parallelize={target=npu_demo,parallel_level=block}"
// CHECK: builtin.module {

builtin.module {
  func.func @bad_loops() {
    %0 = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    %1 = symbol.const 8 : !symbol.int<#symbol.expr<8>>
    %2 = symbol.const 1 : !symbol.int<#symbol.expr<1>>
    symbol.for %i = %0 to %1 step %2 {iter = #symbol.iter<start = #symbol.expr<0>, end = #symbol.expr<8>, step = #symbol.expr<1>>} {
    }
    symbol.for %j = %0 to %1 step %2 {iter = #symbol.iter<start = #symbol.expr<0>, end = #symbol.expr<8>, step = #symbol.expr<1>>} {
    }
    func.return
  }
}
"""
    result = run_ircheck_text(case_text, source_path="test/passes/test_arch_parallelize.py")
    assert result.ok is False
    assert result.message is not None
    assert "multiple top-level symbol.for loops are not supported" in result.message


# TC-PASS-ARCH-PARALLELIZE-007
# 功能说明: 验证 loop-carried `symbol.for` 稳定失败。
# 使用示例: pytest -q test/passes/test_arch_parallelize.py -k test_arch_parallelize_rejects_loop_carried_symbol_for
def test_arch_parallelize_rejects_loop_carried_symbol_for() -> None:
    case_text = """// COMPILE_ARGS: --pass "arch-parallelize={target=npu_demo,parallel_level=block}"
// CHECK: builtin.module {

builtin.module {
  func.func @carried_loop() {
    %0 = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    %1 = symbol.const 8 : !symbol.int<#symbol.expr<8>>
    %2 = symbol.const 1 : !symbol.int<#symbol.expr<1>>
    symbol.for %i = %0 to %1 step %2 iter_args(%acc = %0) {iter = #symbol.iter<start = #symbol.expr<0>, end = #symbol.expr<8>, step = #symbol.expr<1>>} -> !symbol.int<#symbol.expr<0>> {
      symbol.yield %acc : !symbol.int<#symbol.expr<0>>
    }
    func.return
  }
}
"""
    result = run_ircheck_text(case_text, source_path="test/passes/test_arch_parallelize.py")
    assert result.ok is False
    assert result.message is not None
    assert "loop-carried symbol.for is not supported" in result.message


# TC-PASS-ARCH-PARALLELIZE-008
# 功能说明: 验证 options 与 target 失败边界。
# 使用示例: pytest -q test/passes/test_arch_parallelize.py -k test_arch_parallelize_rejects_invalid_options_and_targets
@pytest.mark.parametrize(
    ("pass_obj", "message"),
    [
        (ArchParallelizePass(target="", parallel_level="block"), "target must be non-empty string"),
        (ArchParallelizePass(target="missing_arch_parallelize_target", parallel_level="block"), "target not registered"),
        (ArchParallelizePass(target="npu_demo", parallel_level="block_thread"), "parallel_level block_thread is not supported yet"),
        (ArchParallelizePass(target="npu_demo", parallel_level="thread"), "unsupported parallel_level"),
    ],
)
def test_arch_parallelize_rejects_invalid_options_and_targets(
    pass_obj: ArchParallelizePass,
    message: str,
) -> None:
    module = _empty_void_module()
    with pytest.raises(KernelCodeError, match=message):
        pass_obj.apply(Context(), module)


# TC-PASS-ARCH-PARALLELIZE-009
# 功能说明: 验证 target 支持性和 block_num 硬件字段失败边界。
# 使用示例: pytest -q test/passes/test_arch_parallelize.py -k test_arch_parallelize_rejects_target_contract_gaps
def test_arch_parallelize_rejects_target_contract_gaps() -> None:
    _register_target_once(
        target_registry.TargetSpec("arch_parallelize_no_block_id", set(), set(), {"block_num": 1})
    )
    _register_target_once(
        target_registry.TargetSpec("arch_parallelize_no_block_num", {"arch.get_block_id"}, set(), {})
    )
    _register_target_once(
        target_registry.TargetSpec("arch_parallelize_bad_block_num", {"arch.get_block_id"}, set(), {"block_num": 0})
    )
    with pytest.raises(KernelCodeError, match="target does not support arch.get_block_id"):
        ArchParallelizePass(target="arch_parallelize_no_block_id").apply(Context(), _empty_void_module())
    with pytest.raises(KernelCodeError, match="target block_num must be positive integer"):
        ArchParallelizePass(target="arch_parallelize_no_block_num").apply(Context(), _empty_void_module())
    with pytest.raises(KernelCodeError, match="target block_num must be positive integer"):
        ArchParallelizePass(target="arch_parallelize_bad_block_num").apply(Context(), _empty_void_module())


# TC-PASS-ARCH-PARALLELIZE-010
# 功能说明: 验证 `from_options` 未知 option 稳定失败。
# 使用示例: pytest -q test/passes/test_arch_parallelize.py -k test_arch_parallelize_from_options_rejects_unknown_option
def test_arch_parallelize_from_options_rejects_unknown_option() -> None:
    with pytest.raises(KernelCodeError, match=r"unknown option\(s\): extra"):
        ArchParallelizePass.from_options({"extra": "1"})


# TC-PASS-ARCH-PARALLELIZE-011
# 功能说明: 验证非 void return 稳定失败。
# 使用示例: pytest -q test/passes/test_arch_parallelize.py -k test_arch_parallelize_rejects_return_values
def test_arch_parallelize_rejects_return_values() -> None:
    with pytest.raises(KernelCodeError, match="function return values are not supported"):
        ArchParallelizePass().apply(Context(), _return_value_module())


# TC-PASS-ARCH-PARALLELIZE-012
# 功能说明: 验证 multi-block 函数体稳定失败。
# 使用示例: pytest -q test/passes/test_arch_parallelize.py -k test_arch_parallelize_rejects_multi_block_func_body
def test_arch_parallelize_rejects_multi_block_func_body() -> None:
    with pytest.raises(KernelCodeError, match="multi-block func body is not supported"):
        ArchParallelizePass().apply(Context(), _multi_block_void_module())


# TC-PASS-ARCH-PARALLELIZE-013
# 功能说明: 验证唯一顶层 loop 后存在同级 op 时稳定失败为 unsupported loop structure。
# 使用示例: pytest -q test/passes/test_arch_parallelize.py -k test_arch_parallelize_rejects_unsupported_loop_structure
def test_arch_parallelize_rejects_unsupported_loop_structure() -> None:
    case_text = """// COMPILE_ARGS: --pass "arch-parallelize={target=npu_demo,parallel_level=block}"
// CHECK: builtin.module {

builtin.module {
  func.func @loop_with_trailing_op() {
    %0 = symbol.const 0 : !symbol.int<#symbol.expr<0>>
    %1 = symbol.const 8 : !symbol.int<#symbol.expr<8>>
    %2 = symbol.const 1 : !symbol.int<#symbol.expr<1>>
    symbol.for %i = %0 to %1 step %2 {iter = #symbol.iter<start = #symbol.expr<0>, end = #symbol.expr<8>, step = #symbol.expr<1>>} {
    }
    %3 = symbol.const 2 : !symbol.int<#symbol.expr<2>>
    func.return
  }
}
"""
    result = run_ircheck_text(case_text, source_path="test/passes/test_arch_parallelize.py")
    assert result.ok is False
    assert result.message is not None
    assert "unsupported loop structure" in result.message
