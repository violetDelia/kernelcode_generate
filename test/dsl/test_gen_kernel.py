"""gen_kernel tests.

创建者: 金铲铲大作战
最后一次更改: 小李飞刀

功能说明:
- 覆盖 func.func 到目标函数源码的组装行为。

使用示例:
- pytest -q test/dsl/test_gen_kernel.py

覆盖率信息:
- 覆盖率命令: coverage run -m pytest -q test/dsl/test_emit_c.py test/dsl/test_gen_kernel.py && coverage report --include=kernel_gen/dsl/emit_c.py,kernel_gen/dsl/gen_kernel.py -m
- 覆盖率结果: emit_c 100%, gen_kernel 100%（2026-03-23 22:45:14 +0800）
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
import subprocess
import tempfile

import pytest
from xdsl.dialects import arith, func, scf
from xdsl.dialects.builtin import ArrayAttr, DictionaryAttr, FunctionType, IndexType, IntAttr, IntegerAttr, StringAttr, f16, f32, f64, i1, i32
from xdsl.ir import Block, Region
from xdsl.irdl import IRDLOperation, irdl_op_definition, result_def

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.nn import NnAddOp, NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolAddOp, SymbolValueType
from kernel_gen.dsl.emit_c import EmitCContext
from kernel_gen.dsl.gen_kernel import GenKernelError, gen_body, gen_kernel, gen_signature

gen_kernel_module = importlib.import_module("kernel_gen.dsl.gen_kernel")


@irdl_op_definition
class UnsupportedOp(IRDLOperation):
    name = "test.unsupported"
    result = result_def(i32)

    def __init__(self: "UnsupportedOp") -> None:
        super().__init__(result_types=[i32])


def _ctx() -> EmitCContext:
    return EmitCContext(target="cpu")


def _make_memory_type(shape: list[int], stride: list[int], element_type: object = i32, space: str = "global") -> NnMemoryType:
    return NnMemoryType(
        ArrayAttr([IntAttr(dim) for dim in shape]),
        ArrayAttr([IntAttr(dim) for dim in stride]),
        element_type,
        NnMemorySpaceAttr.from_name(space),
    )


def _arg_attrs(*names: str) -> ArrayAttr[DictionaryAttr]:
    return ArrayAttr([DictionaryAttr({"name": StringAttr(name)}) for name in names])


def _func(name: str, input_types: list[object], result_types: list[object], block: Block, arg_names: tuple[str, ...]) -> func.FuncOp:
    func_type = FunctionType.from_lists(input_types, result_types)
    return func.FuncOp(name, func_type, Region(block), arg_attrs=_arg_attrs(*arg_names))


def _compile_and_run(source: str) -> None:
    """编译并运行 `gen_kernel` 生成的 C++ 片段。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 使用 `g++ -std=c++17` 编译临时源码，并执行生成的可执行文件。
    - 用于锁定 `conv2d_img2col2d_tiled(...)` 的函数级骨架不仅存在，而且可编译运行。

    使用示例:
    - _compile_and_run("#include <cstdint>\\nint main() { return 0; }")

    关联文件:
    - spec: spec/dsl/gen_kernel.md
    - test: test/dsl/test_gen_kernel.py
    - 功能实现: test/dsl/test_gen_kernel.py
    """

    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / "gen_kernel_conv_test.cpp"
        binary_path = Path(tmpdir) / "gen_kernel_conv_test"
        source_path.write_text(source, encoding="utf-8")

        compile_result = subprocess.run(
            [
                "g++",
                "-std=c++17",
                "-I",
                str(REPO_ROOT),
                str(source_path),
                "-o",
                str(binary_path),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if compile_result.returncode != 0:
            raise AssertionError(
                "g++ compile failed:\n"
                f"stdout:\n{compile_result.stdout}\n"
                f"stderr:\n{compile_result.stderr}"
            )

        run_result = subprocess.run(
            [str(binary_path)],
            check=False,
            capture_output=True,
            text=True,
        )
        if run_result.returncode != 0:
            raise AssertionError(
                "compiled program failed:\n"
                f"stdout:\n{run_result.stdout}\n"
                f"stderr:\n{run_result.stderr}"
            )


# GK-001
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 22:45:14 +0800
# 最近一次运行成功时间: 2026-03-23 22:45:14 +0800
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

    empty_block = Block(arg_types=[])
    empty_block.add_op(func.ReturnOp())
    empty_func = _func("empty_kernel", [], [], empty_block, ())
    empty_source = gen_kernel(empty_func, _ctx())
    assert empty_source == "void empty_kernel() {\n}"


# GK-002
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 22:45:14 +0800
# 最近一次运行成功时间: 2026-03-23 22:45:14 +0800
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
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 22:45:14 +0800
# 最近一次运行成功时间: 2026-03-23 22:45:14 +0800
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
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 22:45:14 +0800
# 最近一次运行成功时间: 2026-03-23 22:45:14 +0800
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

    unnamed_block = Block(arg_types=[i32])
    unnamed_block.add_op(func.ReturnOp())
    unnamed_type = FunctionType.from_lists([i32], [])
    unnamed_func = func.FuncOp(
        "unnamed",
        unnamed_type,
        Region(unnamed_block),
        arg_attrs=ArrayAttr([DictionaryAttr({})]),
    )
    assert gen_signature(unnamed_func, _ctx()) == "void unnamed(int32_t arg0)"

    default_block = Block(arg_types=[i1])
    default_block.add_op(func.ReturnOp())
    default_type = FunctionType.from_lists([i1], [])
    default_func = func.FuncOp("default_names", default_type, Region(default_block))
    assert gen_signature(default_func, _ctx()) == "void default_names(bool arg0)"


# GK-005
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 22:45:14 +0800
# 最近一次运行成功时间: 2026-03-23 22:45:14 +0800
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

    def _fake_emit(op: object, _ctx: EmitCContext) -> str:
        seen.append(op.name)
        return f"// {op.name}"

    monkeypatch.setattr(gen_kernel_module, "emit_c_op", _fake_emit)

    body = gen_body(func_op, _ctx())

    assert seen == ["arith.addi", "arith.subi"]
    assert body.splitlines() == ["// arith.addi", "// arith.subi"]

    mem = _make_memory_type([2, 2], [2, 1])
    return_block = Block(arg_types=[mem])
    return_block.add_op(func.ReturnOp(return_block.args[0]))
    return_func = _func("return_body", [mem], [mem], return_block, ("input",))
    assert gen_body(return_func, _ctx()) == "out = arg0;"

    second_block = Block(arg_types=[mem, mem])
    second_block.add_op(func.ReturnOp(second_block.args[1]))
    second_func = _func("return_second", [mem, mem], [mem], second_block, ("lhs", "rhs"))
    assert gen_body(second_func, _ctx()) == "out = arg1;"


# GK-006
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 22:45:14 +0800
# 最近一次运行成功时间: 2026-03-23 22:45:14 +0800
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
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 22:45:14 +0800
# 最近一次运行成功时间: 2026-03-23 22:45:14 +0800
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
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-03-23 22:45:14 +0800
# 最近一次运行成功时间: 2026-03-23 22:45:14 +0800
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

    tuple_block = Block(arg_types=[])
    tuple_block.add_op(func.ReturnOp())
    tuple_type = FunctionType.from_lists([], [i32, i32])
    tuple_func = func.FuncOp("tuple_return", tuple_type, Region(tuple_block), arg_attrs=ArrayAttr([]))
    with pytest.raises(GenKernelError) as exc_info:
        gen_signature(tuple_func, _ctx())
    assert "unsupported return form" in str(exc_info.value)

    float_block = Block(arg_types=[f16])
    float_block.add_op(func.ReturnOp())
    float_type = FunctionType.from_lists([f16], [])
    float_func = func.FuncOp("f16_arg", float_type, Region(float_block))
    with pytest.raises(TypeError) as exc_info:
        gen_signature(float_func, _ctx())
    assert "unsupported type" in str(exc_info.value)

    bad_body_block = Block(arg_types=[i32])
    bad_body_block.add_op(func.ReturnOp(bad_body_block.args[0]))
    bad_body_type = FunctionType.from_lists([i32], [i32])
    bad_body_func = func.FuncOp("bad_body", bad_body_type, Region(bad_body_block), arg_attrs=_arg_attrs("value"))
    with pytest.raises(GenKernelError) as exc_info:
        gen_body(bad_body_func, _ctx())
    assert "unsupported return form" in str(exc_info.value)


# GK-012
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-01 15:07:50 +0800
# 最近一次运行成功时间: 2026-04-01 15:07:50 +0800
# 功能说明: 验证 f32/f64 标量与 Memory<f32/f64> 可生成 float/double 与 Memory<float>/Memory<double> 形式签名。
# 测试目的: 锁定 gen_signature 对 f32/f64 的类型映射，避免 conv2d 链路在函数签名阶段被 TypeError 阻断或类型退化。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_signature_supports_float32_scalar_and_memory
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py

def test_gen_signature_supports_float32_scalar_and_memory() -> None:
    mem_f32 = _make_memory_type([2, 2], [2, 1], element_type=f32)
    block_f32 = Block(arg_types=[mem_f32, f32])
    block_f32.add_op(func.ReturnOp(block_f32.args[0]))
    func_op_f32 = _func("float_kernel", [mem_f32, f32], [mem_f32], block_f32, ("input", "alpha"))

    signature_f32 = gen_signature(func_op_f32, _ctx())

    assert signature_f32 == "void float_kernel(const Memory<float>& input, float alpha, Memory<float>& out)"

    mem_f64 = _make_memory_type([2, 2], [2, 1], element_type=f64)
    block_f64 = Block(arg_types=[mem_f64, f64])
    block_f64.add_op(func.ReturnOp(block_f64.args[0]))
    func_op_f64 = _func("double_kernel", [mem_f64, f64], [mem_f64], block_f64, ("input", "alpha"))

    signature_f64 = gen_signature(func_op_f64, _ctx())

    assert signature_f64 == "void double_kernel(const Memory<double>& input, double alpha, Memory<double>& out)"


# GK-009
# 创建者: 金铲铲大作战
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-03-25 17:10:00 +0800
# 最近一次运行成功时间: 2026-03-25 17:10:00 +0800
# 功能说明: 验证生成源码保留函数名与参数名，并在缺失参数名时沿用默认命名。
# 测试目的: 验证 gen_kernel 使用 IR 中定义的名称；当输入参数缺失 arg_attrs.name 时，源码中的签名参数名回退为 arg{index}。
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

    unnamed_block = Block(arg_types=[i32])
    unnamed_block.add_op(func.ReturnOp())
    unnamed_type = FunctionType.from_lists([i32], [])
    unnamed_func = func.FuncOp(
        "unnamed_kernel",
        unnamed_type,
        Region(unnamed_block),
        arg_attrs=ArrayAttr([DictionaryAttr({})]),
    )

    unnamed_source = gen_kernel(unnamed_func, _ctx())

    assert unnamed_source.startswith("void unnamed_kernel(int32_t arg0)")


# GK-010
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-03-28 07:20:00 +0800
# 最近一次运行成功时间: 2026-03-28 07:20:00 +0800
# 功能说明: 验证 !symbol.int 返回在 cpu target 下可生成函数返回值。
# 测试目的: 锁定 gen_signature/gen_kernel 对 symbol 标量返回的契约，避免退化为 unsupported return form。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_supports_symbol_scalar_return
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py
def test_gen_kernel_supports_symbol_scalar_return() -> None:
    lhs_type = SymbolValueType.from_expr("3")
    rhs_type = SymbolValueType.from_expr("4")
    out_type = SymbolValueType.from_expr("7")
    block = Block(arg_types=[lhs_type, rhs_type])
    add = SymbolAddOp(block.args[0], block.args[1], out_type)
    block.add_op(add)
    block.add_op(func.ReturnOp(add.result))
    func_op = _func("symbol_sum", [lhs_type, rhs_type], [out_type], block, ("lhs", "rhs"))

    signature = gen_signature(func_op, _ctx())
    source = gen_kernel(func_op, _ctx())

    assert signature == "long long symbol_sum(long long lhs, long long rhs)"
    assert source.startswith("long long symbol_sum(long long lhs, long long rhs)")
    assert "long long v0 = (lhs + rhs);" in source
    assert "return v0;" in source


# GK-011
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-03-28 04:12:37 +0800
# 最近一次运行成功时间: 2026-03-28 04:12:37 +0800
# 功能说明: 验证非 cpu target 下 !symbol.int 返回必须报错。
# 测试目的: 锁定 gen_kernel 对 symbol 标量返回的 target=cpu 约束。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_rejects_symbol_scalar_return_on_non_cpu
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py
def test_gen_kernel_rejects_symbol_scalar_return_on_non_cpu() -> None:
    lhs_type = SymbolValueType.from_expr("3")
    rhs_type = SymbolValueType.from_expr("4")
    out_type = SymbolValueType.from_expr("7")
    block = Block(arg_types=[lhs_type, rhs_type])
    add = SymbolAddOp(block.args[0], block.args[1], out_type)
    block.add_op(add)
    block.add_op(func.ReturnOp(add.result))
    func_op = _func("symbol_sum", [lhs_type, rhs_type], [out_type], block, ("lhs", "rhs"))
    ctx = EmitCContext(target="gpu")

    with pytest.raises(GenKernelError, match="symbol scalar return is cpu-only"):
        gen_kernel(func_op, ctx)


# GK-013
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-02 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-02 00:00:00 +0800
# 功能说明: 验证 direct-return nn.add(memory, memory) 在 cpu target 下可直接绑定到 out。
# 测试目的: 锁定 unique-use + func.return + direct bind to out 的函数级特化输出为 cpu::add(lhs, rhs, out)。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_supports_direct_return_nn_add_memory_memory_on_cpu
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py
def test_gen_kernel_supports_direct_return_nn_add_memory_memory_on_cpu() -> None:
    mem = _make_memory_type([2, 2], [2, 1])
    space = NnMemorySpaceAttr.from_name("global")
    block = Block(arg_types=[mem, mem])
    add = NnAddOp(block.args[0], block.args[1], mem, space)
    block.add_op(add)
    block.add_op(func.ReturnOp(add.result))
    func_op = _func("add_direct", [mem, mem], [mem], block, ("lhs", "rhs"))

    source = gen_kernel(func_op, _ctx())

    assert source.startswith("void add_direct(const Memory<int32_t>& lhs, const Memory<int32_t>& rhs, Memory<int32_t>& out)")
    assert "cpu::add(lhs, rhs, out);" in source
    assert "out = " not in source


# GK-014
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-02 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-02 00:00:00 +0800
# 功能说明: 验证 direct-return nn.add(memory, const(i32)) 在 cpu target 下可直接绑定到 out。
# 测试目的: 锁定 const(i32) 路径函数级特化输出为 cpu::add(lhs, 1, out)。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_supports_direct_return_nn_add_memory_const_on_cpu
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py
def test_gen_kernel_supports_direct_return_nn_add_memory_const_on_cpu() -> None:
    mem = _make_memory_type([2, 2], [2, 1])
    space = NnMemorySpaceAttr.from_name("global")
    block = Block(arg_types=[mem])
    const = arith.ConstantOp(IntegerAttr(1, i32))
    add = NnAddOp(block.args[0], const.result, mem, space)
    block.add_op(const)
    block.add_op(add)
    block.add_op(func.ReturnOp(add.result))
    func_op = _func("add_const_direct", [mem], [mem], block, ("lhs",))

    source = gen_kernel(func_op, _ctx())

    assert source.startswith("void add_const_direct(const Memory<int32_t>& lhs, Memory<int32_t>& out)")
    assert "cpu::add(lhs, 1, out);" in source
    assert "out = " not in source


# GK-015
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-02 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-02 00:00:00 +0800
# 功能说明: 验证 direct-return nn.add(memory, symbol.int) 在 cpu target 下可直接绑定到 out。
# 测试目的: 锁定 symbol.int 路径函数级特化输出为 cpu::add(lhs, bias, out) 且签名暴露 long long bias。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_supports_direct_return_nn_add_memory_symbol_on_cpu
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py
def test_gen_kernel_supports_direct_return_nn_add_memory_symbol_on_cpu() -> None:
    mem = _make_memory_type([2, 2], [2, 1])
    bias_type = SymbolValueType.from_expr("bias")
    space = NnMemorySpaceAttr.from_name("global")
    block = Block(arg_types=[mem, bias_type])
    add = NnAddOp(block.args[0], block.args[1], mem, space)
    block.add_op(add)
    block.add_op(func.ReturnOp(add.result))
    func_op = _func("add_symbol_direct", [mem, bias_type], [mem], block, ("lhs", "bias"))

    source = gen_kernel(func_op, _ctx())

    assert source.startswith("void add_symbol_direct(const Memory<int32_t>& lhs, long long bias, Memory<int32_t>& out)")
    assert "cpu::add(lhs, bias, out);" in source
    assert "out = " not in source


# GK-016
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-02 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-02 00:00:00 +0800
# 功能说明: 验证 multi-use 或无法 direct bind 到 out 时，nn.add 特化继续报 unsupported op。
# 测试目的: 锁定 direct-return nn.add 的硬门禁，避免退化为 out = tmp 或其他 generic fallback。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_rejects_nn_add_specialization_on_multi_use
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py
def test_gen_kernel_rejects_nn_add_specialization_on_multi_use() -> None:
    mem = _make_memory_type([2, 2], [2, 1])
    space = NnMemorySpaceAttr.from_name("global")
    block = Block(arg_types=[mem, mem, mem])
    add = NnAddOp(block.args[0], block.args[1], mem, space)
    use_again = NnAddOp(add.result, block.args[2], mem, space)
    block.add_op(add)
    block.add_op(use_again)
    block.add_op(func.ReturnOp(add.result))
    func_op = _func("add_multi_use", [mem, mem, mem], [mem], block, ("lhs", "rhs", "extra"))

    with pytest.raises(ValueError, match="target=cpu: nn.add: unsupported op"):
        gen_kernel(func_op, _ctx())


# GK-C2-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-02 06:21:14 +0800
# 最近一次运行成功时间: 2026-04-02 06:21:14 +0800
# 功能说明: 验证 conv2d_img2col2d_tiled(...) 可生成固定 CPU 骨架并编译运行。
# 测试目的: 锁定固定 tile 常量、tile-local col_buffer/acc_buffer、cpu::img2col2d(...) 与 n/f/ho/wo 分块循环已在函数级源码中冻结。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_compiles_conv2d_img2col2d_tiled_cpu_smoke
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py
def test_gen_kernel_compiles_conv2d_img2col2d_tiled_cpu_smoke() -> None:
    input_type = _make_memory_type([1, 16, 18, 18], [5184, 324, 18, 1], element_type=f32)
    weight_type = _make_memory_type([16, 16, 3, 3], [144, 9, 3, 1], element_type=f32)
    out_type = _make_memory_type([1, 16, 16, 16], [4096, 256, 16, 1], element_type=f32)
    block = Block(arg_types=[input_type, weight_type])
    func_op = _func("conv2d_img2col2d_tiled", [input_type, weight_type], [out_type], block, ("input", "weight"))

    source = gen_kernel(func_op, _ctx())

    assert "constexpr long long Ntile = 1;" in source
    assert "constexpr long long Ctile = 16;" in source
    assert "constexpr long long Ftile = 16;" in source
    assert "constexpr long long Hotile = 16;" in source
    assert "constexpr long long Wotile = 16;" in source
    assert "float col_buffer[Ntile * ColChannels * ColPixels] = {};" in source
    assert "float acc_buffer[Ftile * Hotile * Wotile] = {};" in source
    assert "cpu::img2col2d(input_tile, col_tile, 3, 3, 1, 1, 1, 1, 0, 0, 0, 0);" in source
    assert "for (long long n0 = 0; n0 < out.shape()[0]; n0 += Ntile) {" in source
    assert "for (long long f0 = 0; f0 < out.shape()[1]; f0 += Ftile) {" in source
    assert "for (long long ho0 = 0; ho0 < out.shape()[2]; ho0 += Hotile) {" in source
    assert "for (long long wo0 = 0; wo0 < out.shape()[3]; wo0 += Wotile) {" in source

    cpp_source = f"""\
#include "include/cpu/Memory.h"
#include "include/cpu/Nn.h"

using cpu::Memory;
using cpu::MemoryFormat;
using cpu::MemorySpace;

{source}

static int fail(int code) {{ return code; }}

int main() {{
    float input_data[5184] = {{0}};
    float weight_data[2304] = {{0}};
    float out_data[4096] = {{0}};
    long long input_shape[4] = {{1, 16, 18, 18}};
    long long input_stride[4] = {{5184, 324, 18, 1}};
    long long weight_shape[4] = {{16, 16, 3, 3}};
    long long weight_stride[4] = {{144, 9, 3, 1}};
    long long out_shape[4] = {{1, 16, 16, 16}};
    long long out_stride[4] = {{4096, 256, 16, 1}};

    Memory<float> input(input_data, 4, input_shape, input_stride);
    Memory<float> weight(weight_data, 4, weight_shape, weight_stride);
    Memory<float> out(out_data, 4, out_shape, out_stride);

    conv2d_img2col2d_tiled(input, weight, out);

    for (float value : out_data) {{
        if (value != 0.0f) {{
            return fail(1);
        }}
    }}
    return 0;
}}
"""
    _compile_and_run(cpp_source)


# GK-C2-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-02 06:21:14 +0800
# 最近一次运行成功时间: 2026-04-02 06:21:14 +0800
# 功能说明: 验证 conv2d_img2col2d_tiled(...) 生成源码存在最终写回 out 的固定循环骨架。
# 测试目的: 锁定函数级骨架不止停在局部 acc_buffer，而是显式写回 `out`。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_writes_back_conv_output_tile
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py
def test_gen_kernel_writes_back_conv_output_tile() -> None:
    input_type = _make_memory_type([1, 16, 18, 18], [5184, 324, 18, 1], element_type=f32)
    weight_type = _make_memory_type([16, 16, 3, 3], [144, 9, 3, 1], element_type=f32)
    out_type = _make_memory_type([1, 16, 16, 16], [4096, 256, 16, 1], element_type=f32)
    block = Block(arg_types=[input_type, weight_type])
    func_op = _func("conv2d_img2col2d_tiled", [input_type, weight_type], [out_type], block, ("input", "weight"))

    source = gen_kernel(func_op, _ctx())

    assert "for (long long c0 = 0; c0 < weight.shape()[1]; c0 += Ctile) {" in source
    assert "for (long long fi = 0; fi < Ftile; ++fi) {" in source
    assert "for (long long hi = 0; hi < Hotile; ++hi) {" in source
    assert "for (long long wi = 0; wi < Wotile; ++wi) {" in source
    assert "long long out_indices[4] = {n0, f0 + fi, ho0 + hi, wo0 + wi};" in source
    assert "out.at(out_indices) = acc_buffer[((fi * Hotile) + hi) * Wotile + wi];" in source


# GK-C2-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-02 06:30:51 +0800
# 最近一次运行成功时间: 2026-04-02 06:30:51 +0800
# 功能说明: 验证同名 conv2d_img2col2d_tiled 若 body 含未知 op 必须继续报错。
# 测试目的: 防止固定骨架特化静默吞掉非法 body 中的未知 op。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_rejects_conv2d_img2col2d_tiled_with_unknown_body_op
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py
def test_gen_kernel_rejects_conv2d_img2col2d_tiled_with_unknown_body_op() -> None:
    input_type = _make_memory_type([1, 16, 18, 18], [5184, 324, 18, 1], element_type=f32)
    weight_type = _make_memory_type([16, 16, 3, 3], [144, 9, 3, 1], element_type=f32)
    out_type = _make_memory_type([1, 16, 16, 16], [4096, 256, 16, 1], element_type=f32)
    block = Block(arg_types=[input_type, weight_type])
    block.add_op(UnsupportedOp())
    func_op = _func("conv2d_img2col2d_tiled", [input_type, weight_type], [out_type], block, ("input", "weight"))

    with pytest.raises(GenKernelError) as exc_info:
        gen_kernel(func_op, _ctx())

    assert "test.unsupported" in str(exc_info.value)


# GK-C2-004
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-02 06:30:51 +0800
# 最近一次运行成功时间: 2026-04-02 06:30:51 +0800
# 功能说明: 验证同名 conv2d_img2col2d_tiled 若 body 非空但无未知 op 仍必须报错。
# 测试目的: 锁定当前冻结子集仅接受空 body，避免非法 return 等结构被骨架特化吞掉。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_rejects_conv2d_img2col2d_tiled_with_nonempty_body
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py
def test_gen_kernel_rejects_conv2d_img2col2d_tiled_with_nonempty_body() -> None:
    input_type = _make_memory_type([1, 16, 18, 18], [5184, 324, 18, 1], element_type=f32)
    weight_type = _make_memory_type([16, 16, 3, 3], [144, 9, 3, 1], element_type=f32)
    out_type = _make_memory_type([1, 16, 16, 16], [4096, 256, 16, 1], element_type=f32)
    block = Block(arg_types=[input_type, weight_type])
    block.add_op(func.ReturnOp())
    func_op = _func("conv2d_img2col2d_tiled", [input_type, weight_type], [out_type], block, ("input", "weight"))

    with pytest.raises(GenKernelError, match="body must match frozen subset"):
        gen_kernel(func_op, _ctx())
