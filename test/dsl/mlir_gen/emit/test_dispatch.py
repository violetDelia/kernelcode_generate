"""Emit dispatch tests.

创建者: jcc你莫辜负
最后一次更改: 小李飞刀

功能说明:
- 覆盖 emit dispatch/call_dispatch 的最小行为。

使用示例:
- pytest -q test/dsl/mlir_gen/emit/test_dispatch.py

覆盖率信息:
- 覆盖率命令: coverage run -m pytest -q test/dsl/mlir_gen/emit/test_dispatch.py && coverage report --include=kernel_gen/dsl/mlir_gen/emit/dispatch.py -m
- 覆盖率结果: 未统计（待补充）
- 达标线: 90%

关联文件:
- 功能实现: kernel_gen/dsl/mlir_gen/emit/dispatch.py
- Spec 文档: spec/dsl/emit_mlir.md
- 测试文件: test/dsl/mlir_gen/emit/test_dispatch.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xdsl.dialects import arith
from xdsl.ir import Block

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dsl.ast import ConstAST
from kernel_gen.dsl.mlir_gen.emit import EmitContext
from kernel_gen.dsl.mlir_gen.emit.context import LoweringError
from kernel_gen.dsl.mlir_gen.emit.dispatch import call_dispatch, emit_mlir


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


# EMIT-DISP-002
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-13 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-13 00:00:00 +0800
# 功能说明: 验证 call_dispatch 对非 PythonCalleeCallAST 的拒绝路径。
# 测试目的: 锁定 call_dispatch 的输入边界。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_dispatch.py -k test_call_dispatch_rejects_non_callee
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/dispatch.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_dispatch.py
def test_call_dispatch_rejects_non_callee() -> None:
    block = Block()
    ctx = EmitContext(builder=block, symbols={}, types={})

    with pytest.raises(LoweringError, match="call_dispatch expects PythonCalleeCallAST"):
        call_dispatch(ConstAST(1), ctx)  # type: ignore[arg-type]


# EMIT-DISP-003
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-16 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-16 00:00:00 +0800
# 功能说明: 验证 emit 包根仅公开 `EmitContext` 与 `emit_mlir` 两个稳定入口。
# 测试目的: 锁定 `kernel_gen.dsl.mlir_gen.emit` 的包根公开集合，避免 `LoweringError`、`call_dispatch` 等 helper 被继续视为稳定 API。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_dispatch.py -k test_emit_package_root_exports_only_stable_api
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/__init__.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_dispatch.py
def test_emit_package_root_exports_only_stable_api() -> None:
    import kernel_gen.dsl.mlir_gen.emit as emit_pkg

    if emit_pkg.__all__ != ["EmitContext", "emit_mlir"]:
        raise AssertionError(f"unexpected package root exports: {emit_pkg.__all__}")
    if hasattr(emit_pkg, "LoweringError"):
        raise AssertionError("package root should not expose LoweringError")
    if hasattr(emit_pkg, "call_dispatch"):
        raise AssertionError("package root should not expose call_dispatch")
