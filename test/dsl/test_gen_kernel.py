"""gen_kernel tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 func.func 到目标函数源码的组装行为。

使用示例:
- pytest -q test/dsl/test_gen_kernel.py

覆盖率信息:
- 覆盖率命令: coverage run -m pytest -q test/dsl/test_emit_c.py test/dsl/test_gen_kernel.py && coverage report --include=kernel_gen/dsl/emit_c.py,kernel_gen/dsl/gen_kernel.py -m
- 覆盖率结果: emit_c 80%, gen_kernel 88%（2026-03-22 20:12:02 +0800）
- 达标线: 95%

关联文件:
- 功能实现: kernel_gen/dsl/gen_kernel.py
- Spec 文档: spec/dsl/gen_kernel.md
- 测试文件: test/dsl/test_gen_kernel.py
"""

from __future__ import annotations

from pathlib import Path
import sys
import importlib

import pytest
from xdsl.dialects import arith, func, scf
from xdsl.dialects.builtin import ArrayAttr, DictionaryAttr, FunctionType, IndexType, IntAttr, IntegerAttr, StringAttr, i32
from xdsl.ir import Block, Region
from xdsl.irdl import IRDLOperation, irdl_op_definition, result_def

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dsl.emit_c import EmitCContext
from kernel_gen.dsl.gen_kernel import GenKernelError, gen_body, gen_kernel, gen_signature

gen_kernel_module = importlib.import_module("kernel_gen.dsl.gen_kernel")


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


def _arg_attrs(*names: str) -> ArrayAttr[DictionaryAttr]:
    return ArrayAttr([DictionaryAttr({"name": StringAttr(name)}) for name in names])


def _func(name: str, input_types: list[object], result_types: list[object], block: Block, arg_names: tuple[str, ...]) -> func.FuncOp:
    func_type = FunctionType.from_lists(input_types, result_types)
    return func.FuncOp(name, func_type, Region(block), arg_attrs=_arg_attrs(*arg_names))


# GK-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 20:12:02 +0800
# 最近一次运行成功时间: 2026-03-22 20:12:02 +0800
# 功能说明: 验证 func.func 可生成完整后端源码。
# 测试目的: 验证 gen_kernel 返回签名与函数体文本。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_returns_target_source
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py

def test_gen_kernel_returns_target_source() -> None:
    block = Block(arg_types=[i32, i32])
    add = arith.AddiOp(block.args[0], block.args[1])
    block.add_op(add)
    block.add_op(func.ReturnOp())
    func_op = _func("sum_kernel", [i32, i32], [], block, ("lhs", "rhs"))

    source = gen_kernel(func_op, _ctx())

    assert source.startswith("void sum_kernel(int32_t lhs, int32_t rhs)")
    assert "int32_t v0 = (lhs + rhs);" in source


# GK-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 20:12:02 +0800
# 最近一次运行成功时间: 2026-03-22 20:12:02 +0800
# 功能说明: 验证输入 Memory 参数使用只读签名。
# 测试目的: 验证 gen_signature 对 Memory 输入生成 const 引用。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_signature_uses_readonly_memory_inputs
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py

def test_gen_signature_uses_readonly_memory_inputs() -> None:
    mem = _make_memory_type([2, 2], [2, 1])
    block = Block(arg_types=[mem])
    block.add_op(func.ReturnOp())
    func_op = _func("read_only", [mem], [], block, ("input",))

    signature = gen_signature(func_op, _ctx())

    assert signature == "void read_only(const Memory<int32_t>& input)"


# GK-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 20:12:02 +0800
# 最近一次运行成功时间: 2026-03-22 20:12:02 +0800
# 功能说明: 验证 Memory 结果降为输出参数。
# 测试目的: 验证 gen_signature 对 Memory 返回值生成 out 参数。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_signature_lowers_memory_result_to_out_param
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py

def test_gen_signature_lowers_memory_result_to_out_param() -> None:
    mem = _make_memory_type([2, 2], [2, 1])
    block = Block(arg_types=[mem])
    block.add_op(func.ReturnOp(block.args[0]))
    func_op = _func("produce", [mem], [mem], block, ("input",))

    signature = gen_signature(func_op, _ctx())

    assert signature == "void produce(const Memory<int32_t>& input, Memory<int32_t>& out)"


# GK-004
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 20:12:02 +0800
# 最近一次运行成功时间: 2026-03-22 20:12:02 +0800
# 功能说明: 验证标量参数顺序与 IR 一致。
# 测试目的: 验证 gen_signature 保持标量参数顺序和命名。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_signature_preserves_scalar_arg_order
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py

def test_gen_signature_preserves_scalar_arg_order() -> None:
    block = Block(arg_types=[i32, IndexType(), i32])
    block.add_op(func.ReturnOp())
    func_op = _func("ordered", [i32, IndexType(), i32], [], block, ("lhs", "index", "rhs"))

    signature = gen_signature(func_op, _ctx())

    assert signature == "void ordered(int32_t lhs, long long index, int32_t rhs)"


# GK-005
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 20:12:02 +0800
# 最近一次运行成功时间: 2026-03-22 20:12:02 +0800
# 功能说明: 验证函数体按 op 顺序调用 emit_c。
# 测试目的: 验证 gen_body 不改变 IR 中的 op 顺序。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_body_emits_ops_in_order
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py

def test_gen_body_emits_ops_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    block = Block(arg_types=[i32, i32])
    first = arith.AddiOp(block.args[0], block.args[1])
    second = arith.SubiOp(block.args[0], block.args[1])
    block.add_op(first)
    block.add_op(second)
    block.add_op(func.ReturnOp())
    func_op = _func("ordered_body", [i32, i32], [], block, ("lhs", "rhs"))
    seen: list[str] = []

    def _fake_emit(op, _ctx) -> str:
        seen.append(op.name)
        return f"// {op.name}"

    monkeypatch.setattr(gen_kernel_module, "emit_c_op", _fake_emit)

    body = gen_body(func_op, _ctx())

    assert seen == ["arith.addi", "arith.subi"]
    assert body.splitlines() == ["// arith.addi", "// arith.subi"]


# GK-006
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 20:12:02 +0800
# 最近一次运行成功时间: 2026-03-22 20:12:02 +0800
# 功能说明: 验证 loop 片段可拼装到完整函数中。
# 测试目的: 验证 gen_kernel 保留 scf.for 生成结果。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_assembles_loop_body
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py

def test_gen_kernel_assembles_loop_body() -> None:
    block = Block(arg_types=[])
    c0 = arith.ConstantOp(IntegerAttr(0, IndexType()))
    c4 = arith.ConstantOp(IntegerAttr(4, IndexType()))
    c1 = arith.ConstantOp(IntegerAttr(1, IndexType()))
    for op in (c0, c4, c1):
        block.add_op(op)
    loop_body = Block(arg_types=[IndexType()])
    loop_body.add_op(arith.AddiOp(loop_body.args[0], loop_body.args[0], result_type=IndexType()))
    loop_body.add_op(scf.YieldOp())
    block.add_op(scf.ForOp(c0.result, c4.result, c1.result, [], loop_body))
    block.add_op(func.ReturnOp())
    func_op = _func("loop_kernel", [], [], block, ())

    source = gen_kernel(func_op, _ctx())

    assert "for (long long i0 = 0; i0 < 4; i0 += 1) {" in source
    assert "long long v1 = (i0 + i0);" in source


# GK-007
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 20:12:02 +0800
# 最近一次运行成功时间: 2026-03-22 20:12:02 +0800
# 功能说明: 验证 emit_c 错误可向上抛出。
# 测试目的: 验证 gen_kernel 不吞掉 emit_c 失败原因。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_propagates_emit_c_error
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py

def test_gen_kernel_propagates_emit_c_error() -> None:
    block = Block(arg_types=[])
    block.add_op(UnsupportedOp())
    block.add_op(func.ReturnOp())
    func_op = _func("bad_kernel", [], [], block, ())

    with pytest.raises(ValueError) as exc_info:
        gen_kernel(func_op, _ctx())

    assert "test.unsupported" in str(exc_info.value)


# GK-008
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 20:12:02 +0800
# 最近一次运行成功时间: 2026-03-22 20:12:02 +0800
# 功能说明: 验证不合法返回形式时报错。
# 测试目的: 验证 gen_signature 拒绝标量返回值。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_signature_rejects_unsupported_return_form
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py

def test_gen_signature_rejects_unsupported_return_form() -> None:
    block = Block(arg_types=[i32])
    block.add_op(func.ReturnOp(block.args[0]))
    func_op = _func("scalar_return", [i32], [i32], block, ("value",))

    with pytest.raises(GenKernelError) as exc_info:
        gen_signature(func_op, _ctx())

    assert "unsupported return form" in str(exc_info.value)


# GK-009
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-22 20:12:02 +0800
# 最近一次运行成功时间: 2026-03-22 20:12:02 +0800
# 功能说明: 验证生成源码保留函数名与参数名。
# 测试目的: 验证 gen_kernel 使用 IR 中定义的名称。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_preserves_function_and_arg_names
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py

def test_gen_kernel_preserves_function_and_arg_names() -> None:
    mem = _make_memory_type([2, 2], [2, 1])
    block = Block(arg_types=[mem, i32])
    block.add_op(func.ReturnOp(block.args[0]))
    func_op = _func("named_kernel", [mem, i32], [mem], block, ("tensor", "scale"))

    source = gen_kernel(func_op, _ctx())

    assert source.startswith("void named_kernel(const Memory<int32_t>& tensor, int32_t scale, Memory<int32_t>& out)")
    assert "out = tensor;" in source
