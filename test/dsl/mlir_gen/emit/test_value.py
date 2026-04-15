"""Emit value tests.

创建者: jcc你莫辜负
最后一次更改: jcc你莫辜负

功能说明:
- 覆盖 emit value/index 入口的最小行为与错误路径。

使用示例:
- pytest -q test/dsl/mlir_gen/emit/test_value.py

覆盖率信息:
- 覆盖率命令: coverage run -m pytest -q test/dsl/mlir_gen/emit/test_value.py && coverage report --include=kernel_gen/dsl/mlir_gen/emit/value.py -m
- 覆盖率结果: 未统计（待补充）
- 达标线: 90%

关联文件:
- 功能实现: kernel_gen/dsl/mlir_gen/emit/value.py
- Spec 文档: spec/dsl/emit_mlir.md
- 测试文件: test/dsl/mlir_gen/emit/test_value.py
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

from kernel_gen.dialect.symbol import SymbolConstOp, SymbolValueType
from kernel_gen.dsl.ast import ConstAST, VarAST
from kernel_gen.dsl.mlir_gen.emit import EmitContext
from kernel_gen.dsl.mlir_gen.emit.context import LoweringError
from kernel_gen.dsl.mlir_gen.emit.value import emit_index_operand, emit_value


# EMIT-VALUE-001
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-13 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-13 00:00:00 +0800
# 功能说明: 验证 emit_value 对 ConstAST 的最小下沉行为。
# 测试目的: 确保 emit_value 返回常量 op 结果。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_value.py -k test_emit_value_const
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/value.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_value.py
def test_emit_value_const() -> None:
    block = Block()
    ctx = EmitContext(builder=block, symbols={}, types={})

    result = emit_value(ConstAST(1), ctx)

    body_ops = list(block.ops)
    if len(body_ops) != 1:
        raise AssertionError("expected one emitted op")
    if not isinstance(body_ops[0], arith.ConstantOp):
        raise AssertionError("expected arith.ConstantOp")
    if result is not body_ops[0].result:
        raise AssertionError("expected result to be constant op result")


# EMIT-VALUE-002
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-13 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-13 00:00:00 +0800
# 功能说明: 验证 emit_value 对未知变量的错误路径。
# 测试目的: 锁定 value 入口的缺失引用诊断。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_value.py -k test_emit_value_unknown_var
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/value.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_value.py
def test_emit_value_unknown_var() -> None:
    block = Block()
    ctx = EmitContext(builder=block, symbols={}, types={})

    with pytest.raises(LoweringError, match="Unknown input reference"):
        emit_value(VarAST("x"), ctx)


# EMIT-VALUE-003
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-13 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-13 00:00:00 +0800
# 功能说明: 验证 emit_index_operand 下沉 symbol.const。
# 测试目的: 锁定索引 operand 的 symbol.const 结果类型。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_value.py -k test_emit_index_operand_const
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/value.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_value.py
def test_emit_index_operand_const() -> None:
    block = Block()
    ctx = EmitContext(builder=block, symbols={}, types={})

    result = emit_index_operand(ConstAST(2), ctx)

    body_ops = list(block.ops)
    if not isinstance(body_ops[0], SymbolConstOp):
        raise AssertionError("expected SymbolConstOp emitted")
    if not isinstance(result.type, SymbolValueType):
        raise AssertionError("expected symbol int type for index operand")
