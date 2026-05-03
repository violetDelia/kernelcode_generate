"""DSL AST arch plugin tests.


功能说明:
- 覆盖 `kernel_gen.dsl.ast.plugin.arch` 注册后的 arch helper 解析行为。
- 测试结构对应 `spec/dsl/ast/plugin/arch.md` 与 `kernel_gen/dsl/ast/plugin/arch.py`。

使用示例:
- pytest -q test/dsl/ast/plugin/test_arch.py

关联文件:
- 功能实现: kernel_gen/dsl/ast/plugin/arch.py
- Spec 文档: spec/dsl/ast/plugin/arch.md
- 测试文件: test/dsl/ast/plugin/test_arch.py
"""

from __future__ import annotations

import random

import pytest

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dsl.ast import (
    ArchBarrierAST,
    ArchGetBlockIdAST,
    ArchGetBlockNumAST,
    ArchGetDynamicMemoryAST,
    ArchGetSubthreadIdAST,
    ArchGetSubthreadNumAST,
    ArchGetThreadIdAST,
    ArchGetThreadNumAST,
    ArchLaunchKernelAST,
    ReturnAST,
    parse_function,
)
from kernel_gen.operation.arch import (
    BarrierScope,
    BarrierVisibility,
    barrier,
    get_block_id,
    get_block_num,
    get_dynamic_memory,
    get_subthread_id,
    get_subthread_num,
    get_thread_id,
    get_thread_num,
    launch_kernel,
)
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType


def _arch_get_block_id_kernel():
    return get_block_id()


def _arch_get_block_num_kernel():
    return get_block_num()


def _arch_get_thread_id_kernel():
    return get_thread_id()


def _arch_get_thread_num_kernel():
    return get_thread_num()


def _arch_get_subthread_id_kernel():
    return get_subthread_id()


def _arch_get_subthread_num_kernel():
    return get_subthread_num()


def _arch_dynamic_memory_kernel():
    return get_dynamic_memory(MemorySpace.TLM1)


def _arch_dynamic_memory_expr_kernel():
    return get_dynamic_memory(get_thread_id())


def _arch_barrier_kernel():
    barrier(visibility=[BarrierVisibility.TSM, BarrierVisibility.TLM], scope=BarrierScope.THREAD)


def _arch_barrier_tuple_kernel():
    barrier(visibility=(BarrierVisibility.TSM, BarrierVisibility.TLM), scope=BarrierScope.BLOCK)


def _arch_launch_body(x):
    return x


def _arch_launch_kernel(x):
    launch_kernel[2, 8, 1, 0](_arch_launch_body, x)


def _arch_launch_symbol_extent_kernel(block, thread, subthread, shared_memory_size, x):
    launch_kernel[block, thread, subthread, shared_memory_size](_arch_launch_body, x)


def _arch_bad_dynamic_memory_space_kernel():
    return get_dynamic_memory(MemorySpace.GM)


def _arch_bad_dynamic_memory_arity_kernel():
    return get_dynamic_memory(MemorySpace.SM, MemorySpace.LM)


def _arch_bad_dynamic_memory_type_kernel():
    return get_dynamic_memory("sm")


def _arch_bad_barrier_visibility_kernel():
    barrier(visibility=[BarrierVisibility.TSM], scope=BarrierScope.THREAD)


def _arch_bad_barrier_duplicate_visibility_kernel():
    barrier(visibility=[BarrierVisibility.TSM, BarrierVisibility.TSM], scope=BarrierScope.THREAD)


def _arch_bad_barrier_visibility_type_kernel():
    barrier(visibility="tsm", scope=BarrierScope.THREAD)


def _arch_bad_barrier_item_type_kernel():
    barrier(visibility=[BarrierVisibility.TSM, MemorySpace.TLM1], scope=BarrierScope.THREAD)


def _arch_bad_barrier_scope_kernel():
    barrier(visibility=[BarrierVisibility.TSM, BarrierVisibility.TLM], scope="thread")


def _arch_bad_barrier_scope_expr_kernel():
    barrier(visibility=[BarrierVisibility.TSM, BarrierVisibility.TLM], scope=get_thread_id())


def _arch_bad_barrier_arity_kernel():
    barrier([BarrierVisibility.TSM, BarrierVisibility.TLM], scope=BarrierScope.THREAD)


def _arch_bad_barrier_literal_visibility_items_kernel():
    barrier(visibility=["tsm", "tlm"], scope=BarrierScope.THREAD)


def _arch_bad_barrier_expr_visibility_item_kernel():
    barrier(visibility=[get_thread_id(), BarrierVisibility.TLM], scope=BarrierScope.THREAD)


def _arch_bad_barrier_single_visibility_attr_kernel():
    barrier(visibility=BarrierVisibility.TSM, scope=BarrierScope.THREAD)


def _arch_bad_barrier_visibility_expr_kernel():
    barrier(visibility=get_thread_id(), scope=BarrierScope.THREAD)


def _arch_bad_launch_extent_count_kernel(x):
    launch_kernel[2, 8](_arch_launch_body, x)


def _arch_bad_launch_extent_kernel(x):
    launch_kernel[0, 8, 1, 0](_arch_launch_body, x)


def _arch_bad_launch_thread_extent_kernel(x):
    launch_kernel[2, 0, 1, 0](_arch_launch_body, x)


def _arch_bad_launch_subthread_extent_kernel(x):
    launch_kernel[2, 8, -1, 0](_arch_launch_body, x)


def _arch_bad_launch_shared_memory_extent_kernel(x):
    launch_kernel[2, 8, 1, -1](_arch_launch_body, x)


def _arch_bad_launch_callee_kernel(x):
    launch_kernel[2, 8, 1, 0](x, x)


def _arch_bad_launch_literal_callee_kernel(x):
    launch_kernel[2, 8, 1, 0]("body", x)


def _arch_bad_launch_direct_arity_kernel(x):
    launch_kernel(2, 8, 1, 0)


def _arch_bad_launch_kwargs_kernel(x):
    launch_kernel[2, 8, 1, 0](_arch_launch_body, x, extra=1)


def _arch_bad_block_id_arity_kernel(x):
    return get_block_id(1)


def _arch_bad_block_num_arity_kernel(x):
    return get_block_num(1)


def _arch_bad_thread_id_arity_kernel(x):
    return get_thread_id(1)


def _arch_bad_thread_num_arity_kernel(x):
    return get_thread_num(1)


def _arch_bad_subthread_id_arity_kernel(x):
    return get_subthread_id(1)


def _arch_bad_subthread_num_arity_kernel(x):
    return get_subthread_num(1)


_ARCH_QUERY_CASES = tuple(
    random.Random(20260503).sample(
        [
            (_arch_get_block_id_kernel, ArchGetBlockIdAST),
            (_arch_get_block_num_kernel, ArchGetBlockNumAST),
            (_arch_get_thread_id_kernel, ArchGetThreadIdAST),
            (_arch_get_thread_num_kernel, ArchGetThreadNumAST),
            (_arch_get_subthread_id_kernel, ArchGetSubthreadIdAST),
            (_arch_get_subthread_num_kernel, ArchGetSubthreadNumAST),
        ],
        6,
    )
)

_ARCH_INVALID_QUERY_CASES = tuple(
    random.Random(20260505).sample(
        [
            (_arch_bad_block_id_arity_kernel, "Unsupported get_block_id arity"),
            (_arch_bad_block_num_arity_kernel, "Unsupported get_block_num arity"),
            (_arch_bad_thread_id_arity_kernel, "Unsupported get_thread_id arity"),
            (_arch_bad_thread_num_arity_kernel, "Unsupported get_thread_num arity"),
            (_arch_bad_subthread_id_arity_kernel, "Unsupported get_subthread_id arity"),
            (_arch_bad_subthread_num_arity_kernel, "Unsupported get_subthread_num arity"),
        ],
        6,
    )
)

_ARCH_INVALID_CONTRACT_CASES = tuple(
    random.Random(20260505).sample(
        [
            (_arch_bad_dynamic_memory_space_kernel, "get_dynamic_memory space must be on-chip MemorySpace"),
            (_arch_bad_dynamic_memory_arity_kernel, "Unsupported get_dynamic_memory arity"),
            (_arch_bad_dynamic_memory_type_kernel, "get_dynamic_memory space must be MemorySpace"),
            (_arch_dynamic_memory_expr_kernel, "get_dynamic_memory space must be MemorySpace"),
            (_arch_bad_barrier_visibility_kernel, "barrier visibility must contain TSM and TLM exactly once"),
            (_arch_bad_barrier_duplicate_visibility_kernel, "barrier visibility must not contain duplicates"),
            (_arch_bad_barrier_visibility_type_kernel, "barrier visibility must be non-empty BarrierVisibility list"),
            (_arch_bad_barrier_item_type_kernel, "barrier visibility must be non-empty BarrierVisibility list"),
            (_arch_bad_barrier_literal_visibility_items_kernel, "barrier visibility must be non-empty BarrierVisibility list"),
            (_arch_bad_barrier_expr_visibility_item_kernel, "barrier visibility must be non-empty BarrierVisibility list"),
            (_arch_bad_barrier_single_visibility_attr_kernel, "barrier visibility must be non-empty BarrierVisibility list"),
            (_arch_bad_barrier_visibility_expr_kernel, "barrier visibility must be non-empty BarrierVisibility list"),
            (_arch_bad_barrier_scope_kernel, "barrier scope must be BarrierScope"),
            (_arch_bad_barrier_scope_expr_kernel, "barrier scope must be BarrierScope"),
            (_arch_bad_barrier_arity_kernel, "Unsupported barrier arity"),
            (_arch_bad_launch_extent_count_kernel, "Unsupported launch_kernel arity"),
            (_arch_bad_launch_extent_kernel, "launch_kernel block must be > 0"),
            (_arch_bad_launch_thread_extent_kernel, "launch_kernel thread must be > 0"),
            (_arch_bad_launch_subthread_extent_kernel, "launch_kernel subthread must be > 0"),
            (_arch_bad_launch_shared_memory_extent_kernel, "launch_kernel shared_memory_size must be >= 0"),
            (_arch_bad_launch_callee_kernel, "launch_kernel callee must be function symbol reference"),
            (_arch_bad_launch_literal_callee_kernel, "launch_kernel callee must be function symbol reference"),
            (_arch_bad_launch_direct_arity_kernel, "Unsupported launch_kernel arity"),
            (_arch_bad_launch_kwargs_kernel, "Unsupported launch_kernel arity"),
        ],
        24,
    )
)


def test_arch_query_helper_uses_specific_ast_node() -> None:
    """arch 查询 helper 解析为专用 AST，不再依赖 query 字符串字段。"""

    func_ast = parse_function(_arch_get_thread_num_kernel)

    return_nodes = [node for node in func_ast.body.statements if isinstance(node, ReturnAST)]
    assert len(return_nodes) == 1
    assert any(isinstance(value, ArchGetThreadNumAST) for value in return_nodes[0].values)


@pytest.mark.parametrize(("kernel", "expected_type"), _ARCH_QUERY_CASES)
def test_arch_query_public_helpers_parse_to_specific_nodes(kernel, expected_type: type) -> None:
    """确定性随机遍历 arch 查询 helper，验证公开注册入口与 AST 节点映射。"""

    func_ast = parse_function(kernel)

    return_nodes = [node for node in func_ast.body.statements if isinstance(node, ReturnAST)]
    assert len(return_nodes) == 1
    assert any(isinstance(value, expected_type) for value in return_nodes[0].values)


def test_arch_memory_barrier_and_launch_helpers_parse_public_nodes() -> None:
    """dynamic memory、barrier 与 launch_kernel 公开 helper 均解析为对应 AST。"""

    memory = Memory([4], NumericType.Float32)
    block = SymbolDim("B")
    thread = SymbolDim("T")
    subthread = SymbolDim("S")
    shared_memory_size = SymbolDim("SMEM")

    dynamic_ast = parse_function(_arch_dynamic_memory_kernel)
    dynamic_returns = [node for node in dynamic_ast.body.statements if isinstance(node, ReturnAST)]
    assert any(isinstance(value, ArchGetDynamicMemoryAST) for value in dynamic_returns[0].values)

    barrier_ast = parse_function(_arch_barrier_kernel)
    assert any(isinstance(node, ArchBarrierAST) for node in barrier_ast.body.statements)

    tuple_barrier_ast = parse_function(_arch_barrier_tuple_kernel)
    assert any(isinstance(node, ArchBarrierAST) for node in tuple_barrier_ast.body.statements)

    launch_ast = parse_function(_arch_launch_kernel, memory)
    assert any(isinstance(node, ArchLaunchKernelAST) for node in launch_ast.body.statements)

    dynamic_launch_ast = parse_function(_arch_launch_symbol_extent_kernel, block, thread, subthread, shared_memory_size, memory)
    assert any(isinstance(node, ArchLaunchKernelAST) for node in dynamic_launch_ast.body.statements)


@pytest.mark.parametrize(("kernel", "match"), _ARCH_INVALID_QUERY_CASES)
def test_arch_query_rejects_invalid_helper_arity(kernel, match: str) -> None:
    """arch 查询 helper 非法参数矩阵均报稳定错误。"""

    memory = Memory([1], NumericType.Float32)

    with pytest.raises(KernelCodeError, match=match):
        parse_function(kernel, memory)


@pytest.mark.parametrize(("kernel", "match"), _ARCH_INVALID_CONTRACT_CASES)
def test_arch_public_helpers_reject_invalid_contracts(kernel, match: str) -> None:
    """公开 arch helper 的空间、barrier 与 launch 参数矩阵保持稳定拒绝。"""

    memory = Memory([4], NumericType.Float32)

    with pytest.raises(KernelCodeError, match=match):
        parse_function(kernel, memory)
