"""Emit shape utils tests.

创建者: jcc你莫辜负
最后一次更改: jcc你莫辜负

功能说明:
- 覆盖 index/shape/stride 构造工具的最小行为。

使用示例:
- pytest -q test/dsl/mlir_gen/emit/test_shape_utils.py

覆盖率信息:
- 覆盖率命令: coverage run -m pytest -q test/dsl/mlir_gen/emit/test_shape_utils.py && coverage report --include=kernel_gen/dsl/mlir_gen/emit/shape_utils.py -m
- 覆盖率结果: 未统计（待补充）
- 达标线: 90%

关联文件:
- 功能实现: kernel_gen/dsl/mlir_gen/emit/shape_utils.py
- Spec 文档: spec/dsl/emit_mlir.md
- 测试文件: test/dsl/mlir_gen/emit/test_shape_utils.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from xdsl.dialects.builtin import ArrayAttr, IntAttr
from xdsl.ir import Block

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dsl.ast import ConstAST
from kernel_gen.dsl.mlir_gen.emit import EmitContext
from kernel_gen.dsl.mlir_gen.emit.shape_utils import (
    build_index_attrs,
    build_index_operands_exact,
    build_index_operands_from_layout,
    build_stride_attrs,
    resolve_index_expr,
)


# EMIT-SHAPE-001
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-13 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-13 00:00:00 +0800
# 功能说明: 验证 build_index_attrs 的默认补值行为。
# 测试目的: 锁定 rank=2 的索引 operand 生成数量。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_shape_utils.py -k test_build_index_attrs_default
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/shape_utils.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_shape_utils.py
def test_build_index_attrs_default() -> None:
    ctx = EmitContext(builder=Block(), symbols={}, types={})
    result = build_index_attrs(None, rank=2, ctx=ctx, default_value=0)
    if len(result) != 2:
        raise AssertionError("expected two index operands")


# EMIT-SHAPE-002
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-13 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-13 00:00:00 +0800
# 功能说明: 验证 build_index_operands_from_layout 的最小行为。
# 测试目的: 锁定 layout -> operand 的列表长度。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_shape_utils.py -k test_build_index_operands_from_layout
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/shape_utils.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_shape_utils.py
def test_build_index_operands_from_layout() -> None:
    ctx = EmitContext(builder=Block(), symbols={}, types={})
    layout = ArrayAttr([IntAttr(2), IntAttr(3)])
    result = build_index_operands_from_layout(layout, ctx)
    if len(result) != 2:
        raise AssertionError("expected two layout operands")


# EMIT-SHAPE-003
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-13 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-13 00:00:00 +0800
# 功能说明: 验证 build_index_operands_exact 的最小行为。
# 测试目的: 锁定显式索引列表的长度。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_shape_utils.py -k test_build_index_operands_exact
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/shape_utils.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_shape_utils.py
def test_build_index_operands_exact() -> None:
    ctx = EmitContext(builder=Block(), symbols={}, types={})
    result = build_index_operands_exact([ConstAST(1), ConstAST(2)], ctx)
    if len(result) != 2:
        raise AssertionError("expected two explicit operands")


def test_shape_utils_private_helper_edges() -> None:
    ctx = EmitContext(builder=Block(), symbols={}, types={})

    assert resolve_index_expr(ConstAST(3), ctx) == 3

    strides = build_stride_attrs(None, rank=2, ctx=ctx)
    assert len(strides) == 2
