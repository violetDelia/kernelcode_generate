"""Emit control flow tests.

创建者: jcc你莫辜负
最后一次更改: jcc你莫辜负

功能说明:
- 覆盖 emit control_flow 的最小行为与拒绝路径。

使用示例:
- pytest -q test/dsl/mlir_gen/emit/test_control_flow.py

覆盖率信息:
- 覆盖率命令: coverage run -m pytest -q test/dsl/mlir_gen/emit/test_control_flow.py && coverage report --include=kernel_gen/dsl/mlir_gen/emit/control_flow.py -m
- 覆盖率结果: 未统计（待补充）
- 达标线: 90%

关联文件:
- 功能实现: kernel_gen/dsl/mlir_gen/emit/control_flow.py
- Spec 文档: spec/dsl/emit_mlir.md
- 测试文件: test/dsl/mlir_gen/emit/test_control_flow.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xdsl.ir import Block

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.symbol import SymbolForOp
from kernel_gen.dsl.ast import BlockAST, ConstAST, ForAST, VarAST
from kernel_gen.dsl.mlir_gen.emit import EmitContext, LoweringError
from kernel_gen.dsl.mlir_gen.emit.control_flow import emit_control_flow, emit_for


# EMIT-CF-001
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-13 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-13 00:00:00 +0800
# 功能说明: 验证 ForAST 的控制流入口能发射 symbol.for。
# 测试目的: 锁定 emit_for 的最小循环发射语义。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_control_flow.py -k test_emit_for_lowers_symbol_for
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/control_flow.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_control_flow.py
def test_emit_for_lowers_symbol_for() -> None:
    block = Block()
    ctx = EmitContext(builder=block, symbols={}, types={})
    loop = ForAST(
        var=VarAST("i"),
        start=ConstAST(0),
        end=ConstAST(2),
        step=ConstAST(1),
        body=BlockAST(statements=[ConstAST(0)]),
    )

    emit_for(loop, ctx)

    body_ops = list(block.ops)
    if not any(isinstance(op, SymbolForOp) for op in body_ops):
        raise AssertionError("expected SymbolForOp emitted for ForAST")


# EMIT-CF-002
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-13 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-13 00:00:00 +0800
# 功能说明: 验证 control_flow 入口拒绝非 ForAST 节点。
# 测试目的: 锁定 emit_control_flow 的输入边界。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_control_flow.py -k test_emit_control_flow_rejects_non_for
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/control_flow.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_control_flow.py
def test_emit_control_flow_rejects_non_for() -> None:
    block = Block()
    ctx = EmitContext(builder=block, symbols={}, types={})

    with pytest.raises(LoweringError, match="emit_control_flow only handles ForAST"):
        emit_control_flow(ConstAST(0), ctx)
