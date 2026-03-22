"""emit_c tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 emit_c 节点级源码片段生成与错误路径。

使用示例:
- pytest -q test/dsl/test_emit_c.py

覆盖率信息:
- 覆盖率命令: coverage run -m pytest -q test/dsl/test_emit_c.py test/dsl/test_gen_kernel.py && coverage report --include=kernel_gen/dsl/emit_c.py,kernel_gen/dsl/gen_kernel.py -m
- 覆盖率结果: emit_c 80%, gen_kernel 88%（2026-03-22 20:12:02 +0800）
- 达标线: 95%

关联文件:
- 功能实现: kernel_gen/dsl/emit_c.py
- Spec 文档: spec/dsl/emit_c.md
- 测试文件: test/dsl/test_emit_c.py
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest
from xdsl.dialects import arith, scf
from xdsl.dialects.builtin import ArrayAttr, IndexType, IntAttr, IntegerAttr, i32
from xdsl.ir import Block
from xdsl.irdl import IRDLOperation, irdl_op_definition, result_def

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.dma import DmaLoadOp, DmaStoreOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dsl.emit_c import EmitCContext, EmitCError, emit_c_op, emit_c_value


@irdl_op_definition
class UnsupportedOp(IRDLOperation):
    name = "test.unsupported"
    result = result_def(i32)

    def __init__(self) -> None:
        super().__init__(result_types=[i32])


def _ctx() -> EmitCContext:
    return EmitCContext(target="cpu")


def _make_memory_type(shape: list[int], stride: list[int], space: str = "global") -> NnMemoryType:
    return NnMemoryType(
        ArrayAttr([IntAttr(dim) for dim in shape]),
        ArrayAttr([IntAttr(dim) for dim in stride]),
        i32,
        NnMemorySpaceAttr.from_name(space),
    )


# EC-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 20:12:02 +0800
# 最近一次运行成功时间: 2026-03-22 20:12:02 +0800
# 功能说明: 验证算术 op 可生成赋值语句。
# 测试目的: 验证 emit_c_op 可把 addi 生成为右值赋值语句。
# 使用示例: pytest -q test/dsl/test_emit_c.py -k test_emit_c_op_lowers_arith_add
# 对应功能实现文件路径: kernel_gen/dsl/emit_c.py
# 对应 spec 文件路径: spec/dsl/emit_c.md
# 对应测试文件路径: test/dsl/test_emit_c.py

def test_emit_c_op_lowers_arith_add() -> None:
    block = Block(arg_types=[i32, i32])
    ctx = _ctx()
    ctx.bind_name(block.args[0], "lhs")
    ctx.bind_name(block.args[1], "rhs")
    op = arith.AddiOp(block.args[0], block.args[1])

    stmt = emit_c_op(op, ctx)

    assert stmt == "int32_t v0 = (lhs + rhs);"


# EC-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 20:12:02 +0800
# 最近一次运行成功时间: 2026-03-22 20:12:02 +0800
# 功能说明: 验证比较 value 可生成比较表达式。
# 测试目的: 验证 emit_c_value 可把 cmpi 结果生成为布尔表达式。
# 使用示例: pytest -q test/dsl/test_emit_c.py -k test_emit_c_value_lowers_compare
# 对应功能实现文件路径: kernel_gen/dsl/emit_c.py
# 对应 spec 文件路径: spec/dsl/emit_c.md
# 对应测试文件路径: test/dsl/test_emit_c.py

def test_emit_c_value_lowers_compare() -> None:
    block = Block(arg_types=[i32, i32])
    ctx = _ctx()
    ctx.bind_name(block.args[0], "lhs")
    ctx.bind_name(block.args[1], "rhs")
    op = arith.CmpiOp(block.args[0], block.args[1], "eq")

    expr = emit_c_value(op.result, ctx)

    assert expr == "(lhs == rhs)"


# EC-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 20:12:02 +0800
# 最近一次运行成功时间: 2026-03-22 20:12:02 +0800
# 功能说明: 验证 scf.for 可生成目标循环结构。
# 测试目的: 验证 emit_c_op 可拼装 for 循环与循环体语句。
# 使用示例: pytest -q test/dsl/test_emit_c.py -k test_emit_c_op_lowers_scf_for
# 对应功能实现文件路径: kernel_gen/dsl/emit_c.py
# 对应 spec 文件路径: spec/dsl/emit_c.md
# 对应测试文件路径: test/dsl/test_emit_c.py

def test_emit_c_op_lowers_scf_for() -> None:
    ctx = _ctx()
    start = arith.ConstantOp(IntegerAttr(0, IndexType()))
    end = arith.ConstantOp(IntegerAttr(4, IndexType()))
    step = arith.ConstantOp(IntegerAttr(1, IndexType()))
    body = Block(arg_types=[IndexType()])
    add = arith.AddiOp(body.args[0], body.args[0], result_type=IndexType())
    body.add_op(add)
    body.add_op(scf.YieldOp())
    loop = scf.ForOp(start.result, end.result, step.result, [], body)

    stmt = emit_c_op(loop, ctx)

    assert "for (long long i0 = 0; i0 < 4; i0 += 1) {" in stmt
    assert "long long v1 = (i0 + i0);" in stmt


# EC-004
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 20:12:02 +0800
# 最近一次运行成功时间: 2026-03-22 20:12:02 +0800
# 功能说明: 验证访存 op 可生成索引访问代码。
# 测试目的: 验证 unit-tile dma.load/store 可生成索引读写语句。
# 使用示例: pytest -q test/dsl/test_emit_c.py -k test_emit_c_op_lowers_memory_access
# 对应功能实现文件路径: kernel_gen/dsl/emit_c.py
# 对应 spec 文件路径: spec/dsl/emit_c.md
# 对应测试文件路径: test/dsl/test_emit_c.py

def test_emit_c_op_lowers_memory_access() -> None:
    source_type = _make_memory_type([2, 4], [4, 1])
    tile_type = _make_memory_type([1, 1], [1, 1])
    block = Block(arg_types=[source_type, source_type])
    ctx = _ctx()
    ctx.bind_name(block.args[0], "source")
    ctx.bind_name(block.args[1], "target")
    c0 = arith.ConstantOp(IntegerAttr(0, IndexType()))
    c1 = arith.ConstantOp(IntegerAttr(1, IndexType()))
    load = DmaLoadOp(block.args[0], [c0.result, c1.result], [c1.result, c1.result], [c1.result, c1.result], tile_type, NnMemorySpaceAttr.from_name("global"))
    load_stmt = emit_c_op(load, ctx)
    store = DmaStoreOp(load.result, block.args[1], [c0.result, c1.result], [c1.result, c1.result], [c1.result, c1.result])

    store_stmt = emit_c_op(store, ctx)

    assert load_stmt == "int32_t v0 = source[0][1];"
    assert store_stmt == "target[0][1] = v0;"


# EC-005
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 20:12:02 +0800
# 最近一次运行成功时间: 2026-03-22 20:12:02 +0800
# 功能说明: 验证不支持 op 时抛出带 op 名称的错误。
# 测试目的: 验证 emit_c_op 对未知 op 明确失败。
# 使用示例: pytest -q test/dsl/test_emit_c.py -k test_emit_c_op_rejects_unsupported_op
# 对应功能实现文件路径: kernel_gen/dsl/emit_c.py
# 对应 spec 文件路径: spec/dsl/emit_c.md
# 对应测试文件路径: test/dsl/test_emit_c.py

def test_emit_c_op_rejects_unsupported_op() -> None:
    with pytest.raises(EmitCError) as exc_info:
        emit_c_op(UnsupportedOp(), _ctx())

    assert "test.unsupported" in str(exc_info.value)


# EC-006
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 20:12:02 +0800
# 最近一次运行成功时间: 2026-03-22 20:12:02 +0800
# 功能说明: 验证依赖非法的 value 生成时报错。
# 测试目的: 验证 emit_c_value 不接受未知依赖来源。
# 使用示例: pytest -q test/dsl/test_emit_c.py -k test_emit_c_value_rejects_invalid_dependency
# 对应功能实现文件路径: kernel_gen/dsl/emit_c.py
# 对应 spec 文件路径: spec/dsl/emit_c.md
# 对应测试文件路径: test/dsl/test_emit_c.py

def test_emit_c_value_rejects_invalid_dependency() -> None:
    with pytest.raises(EmitCError) as exc_info:
        emit_c_value(UnsupportedOp().result, _ctx())

    assert "invalid dependency" in str(exc_info.value)
    assert "test.unsupported" in str(exc_info.value)
