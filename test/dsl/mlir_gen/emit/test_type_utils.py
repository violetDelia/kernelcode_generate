"""Emit type public integration tests.

创建者: jcc你莫辜负
最后一次更改: 小李飞刀

功能说明:
- 只覆盖 `kernel_gen.dsl.mlir_gen.emit` 包根公开入口中的类型相关可观察行为。
- 不再把 `type_utils.py` 子模块 helper 视为测试合同。

使用示例:
- pytest -q test/dsl/mlir_gen/emit/test_type_utils.py

关联文件:
- 功能实现: kernel_gen/dsl/mlir_gen/emit/__init__.py
- Spec 文档: spec/dsl/emit_mlir.md
- 测试文件: test/dsl/mlir_gen/emit/test_type_utils.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from xdsl.dialects import arith
from xdsl.dialects.builtin import f32, i32
from xdsl.ir import Block

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.nn import NnMemorySpaceAttr
from kernel_gen.dsl.ast import ConstAST
from kernel_gen.dsl.mlir_gen.emit import EmitContext, emit_mlir, memory_type_from_memory
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.type import NumericType


def test_emit_package_root_memory_type_from_memory_builds_public_layout() -> None:
    mem_type = memory_type_from_memory(Memory([2, "N"], NumericType.Float32, space=MemorySpace.TSM))

    assert [dim.data for dim in mem_type.shape.data] == [2, "N"]
    assert [dim.data for dim in mem_type.stride.data] == ["N", 1]
    assert mem_type.element_type == f32
    assert mem_type.space == NnMemorySpaceAttr.from_name("tsm")


def test_emit_package_root_memory_type_from_memory_keeps_i32_element_type() -> None:
    mem_type = memory_type_from_memory(Memory([4], NumericType.Int32, space=MemorySpace.GM))

    assert [dim.data for dim in mem_type.shape.data] == [4]
    assert [dim.data for dim in mem_type.stride.data] == [1]
    assert mem_type.element_type == i32
    assert mem_type.space == NnMemorySpaceAttr.from_name("global")


def test_emit_mlir_const_keeps_public_i32_type() -> None:
    block = Block()
    ctx = EmitContext(builder=block, symbols={}, types={})

    result = emit_mlir(ConstAST(1), ctx)

    assert isinstance(result.owner, arith.ConstantOp)
    assert result.type == i32
