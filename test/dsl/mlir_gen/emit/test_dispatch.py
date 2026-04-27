"""Emit public dispatch tests.

创建者: jcc你莫辜负
最后一次更改: 小李飞刀

功能说明:
- 覆盖 `kernel_gen.dsl.mlir_gen.emit` 包根公开入口的最小分发行为。

使用示例:
- pytest -q test/dsl/mlir_gen/emit/test_dispatch.py

覆盖率信息:
- 覆盖率命令: coverage run -m pytest -q test/dsl/mlir_gen/emit/test_dispatch.py && coverage report --include=kernel_gen/dsl/mlir_gen/emit/dispatch.py -m
- 覆盖率结果: 未统计（待补充）
- 达标线: 90%

关联文件:
- 功能实现: kernel_gen/dsl/mlir_gen/emit/__init__.py
- 功能实现: kernel_gen/dsl/mlir_gen/emit/dispatch.py
- Spec 文档: spec/dsl/emit_mlir.md
- 测试文件: test/dsl/mlir_gen/emit/test_dispatch.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xdsl.dialects import arith
from xdsl.dialects.builtin import f32
from xdsl.ir import Block

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.nn import NnMemorySpaceAttr
from kernel_gen.dsl.ast import ConstAST
from kernel_gen.dsl.mlir_gen.emit import EmitContext, emit_mlir, memory_type_from_memory
from kernel_gen.symbol_variable.memory import Memory, MemorySpace, NumericType

# EMIT-DISP-001
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-13 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-13 00:00:00 +0800
# 功能说明: 验证 emit dispatch 对 ConstAST 的最小分发行为。
# 测试目的: 确保 dispatch 入口可返回常量 op 的结果。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_dispatch.py -k test_emit_mlir_dispatches_const
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/dispatch.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_dispatch.py
def test_emit_mlir_dispatches_const() -> None:
    block = Block()
    ctx = EmitContext(builder=block, symbols={}, types={})

    result = emit_mlir(ConstAST(1), ctx)

    body_ops = list(block.ops)
    if len(body_ops) != 1:
        raise AssertionError("expected one emitted op")
    if not isinstance(body_ops[0], arith.ConstantOp):
        raise AssertionError("expected arith.ConstantOp")
    if result is not body_ops[0].result:
        raise AssertionError("expected result to be constant op result")


# EMIT-DISP-003
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-16 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-16 00:00:00 +0800
# 功能说明: 验证 emit 包根仅公开稳定入口集合。
# 测试目的: 锁定 `kernel_gen.dsl.mlir_gen.emit` 的包根公开集合，避免 `LoweringError`、`call_dispatch` 等内部 helper 被继续视为稳定 API。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_dispatch.py -k test_emit_package_root_exports_only_stable_api
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_dispatch.py
def test_emit_package_root_exports_only_stable_api() -> None:
    import kernel_gen.dsl.mlir_gen.emit as emit_pkg

    if emit_pkg.EmitContext is not EmitContext:
        raise AssertionError("package root should expose EmitContext")
    if emit_pkg.emit_mlir is not emit_mlir:
        raise AssertionError("package root should expose emit_mlir")
    if emit_pkg.memory_type_from_memory is not memory_type_from_memory:
        raise AssertionError("package root should expose memory_type_from_memory")
    if hasattr(emit_pkg, "LoweringError"):
        raise AssertionError("package root should not expose LoweringError")
    if hasattr(emit_pkg, "call_dispatch"):
        raise AssertionError("package root should not expose call_dispatch")


# EMIT-DISP-004
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-16 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-16 00:00:00 +0800
# 功能说明: 验证 emit 包根公开的 `memory_type_from_memory(...)` 可生成稳定 memory type。
# 测试目的: 锁定 tooling 通过包根而非 `.core` 私有 helper 复用 memory type 转换能力。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_dispatch.py -k test_emit_package_root_exposes_memory_type_from_memory
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/mlir_gen.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_dispatch.py
def test_emit_package_root_exposes_memory_type_from_memory() -> None:
    mem_type = memory_type_from_memory(Memory([2, 3], NumericType.Float32))

    if [dim.data for dim in mem_type.shape.data] != [2, 3]:
        raise AssertionError(f"unexpected shape from package root helper: {mem_type.shape.data}")
    if mem_type.element_type != f32:
        raise AssertionError(f"unexpected element type from package root helper: {mem_type.element_type}")


# EMIT-DISP-005
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 验证 emit 包根公开的 `memory_type_from_memory(...)` 对 on-chip 临时空间保持稳定映射。
# 测试目的: 锁定 TSM/TLM* 这组公开 `MemorySpace` 不再依赖 `.core` 私有 helper 后仍映射到 dialect 接受的 space 名。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_dispatch.py -k test_emit_package_root_memory_type_from_memory_keeps_tsm_space
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_dispatch.py
def test_emit_package_root_memory_type_from_memory_keeps_tsm_space() -> None:
    mem_type = memory_type_from_memory(Memory([2, "N"], NumericType.Float32, space=MemorySpace.TSM))

    if [dim.data for dim in mem_type.shape.data] != [2, "N"]:
        raise AssertionError(f"unexpected shape from package root helper: {mem_type.shape.data}")
    if mem_type.space != NnMemorySpaceAttr.from_name("tsm"):
        raise AssertionError(f"unexpected space from package root helper: {mem_type.space}")
