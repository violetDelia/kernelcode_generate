"""Emit arch public integration tests.

创建者: jcc你莫辜负
最后一次更改: jcc你莫辜负

功能说明:
- 只覆盖 `kernel_gen.dsl.mlir_gen.emit` 包根公开入口的 arch family 可观察行为。
- 不再把 `call_arch.py` 子模块 helper 视为测试合同。

使用示例:
- pytest -q test/dsl/mlir_gen/emit/test_call_arch.py

关联文件:
- 功能实现: kernel_gen/dsl/mlir_gen/emit/__init__.py
- Spec 文档: spec/dsl/emit_mlir.md
- 测试文件: test/dsl/mlir_gen/emit/test_call_arch.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xdsl.ir import Block

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.arch import ArchGetDynamicMemoryOp, ArchGetThreadNumOp
from kernel_gen.dsl.ast import ArchGetDynamicMemoryAST, ArchQueryAST, ConstAST
from kernel_gen.dsl.mlir_gen.emit import EmitContext, emit_mlir
from kernel_gen.symbol_variable.memory import MemorySpace


# EMIT-CALL-ARCH-001
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-13 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-13 00:00:00 +0800
# 功能说明: 验证公开 `emit_mlir(...)` 可 lowering get_dynamic_memory。
# 测试目的: 锁定公开入口会生成单个 arch.get_dynamic_memory op。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_call_arch.py -k test_emit_mlir_lowers_get_dynamic_memory
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_call_arch.py
def test_emit_mlir_lowers_get_dynamic_memory() -> None:
    block = Block()
    ctx = EmitContext(builder=block, symbols={}, types={})

    result = emit_mlir(ArchGetDynamicMemoryAST(space=MemorySpace.LM, location=None), ctx)

    body_ops = list(block.ops)
    assert len(body_ops) == 1
    assert isinstance(body_ops[0], ArchGetDynamicMemoryOp)
    assert result is body_ops[0].result
    assert body_ops[0].memory_space.space.data == "local"


# EMIT-CALL-ARCH-002
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-13 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-13 00:00:00 +0800
# 功能说明: 验证公开 `emit_mlir(...)` 可 lowering arch query。
# 测试目的: 锁定公开 query 会生成对应 query op。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_call_arch.py -k test_emit_mlir_lowers_arch_query
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_call_arch.py
def test_emit_mlir_lowers_arch_query() -> None:
    block = Block()
    ctx = EmitContext(builder=block, symbols={}, types={})

    result = emit_mlir(ArchQueryAST(query_name="get_thread_num", location=None), ctx)

    body_ops = list(block.ops)
    assert len(body_ops) == 1
    assert isinstance(body_ops[0], ArchGetThreadNumOp)
    assert result is body_ops[0].result


# EMIT-CALL-ARCH-003
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-13 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-13 00:00:00 +0800
# 功能说明: 验证公开 `emit_mlir(...)` 会拒绝非法 on-chip dynamic memory 空间。
# 测试目的: 锁定公开 arch lowering 的错误边界不依赖 `call_arch.py` 子模块入口。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_call_arch.py -k test_emit_mlir_rejects_invalid_dynamic_memory_space
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_call_arch.py
def test_emit_mlir_rejects_invalid_dynamic_memory_space() -> None:
    block = Block()
    ctx = EmitContext(builder=block, symbols={}, types={})

    with pytest.raises(KernelCodeError, match="get_dynamic_memory space must be on-chip MemorySpace"):
        emit_mlir(ArchGetDynamicMemoryAST(space=MemorySpace.GM, location=ConstAST(1).location), ctx)
