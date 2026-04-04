"""gen_kernel tests.

创建者: 金铲铲大作战
最后一次更改: jcc你莫辜负

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
from xdsl.dialects.builtin import ArrayAttr, DictionaryAttr, FunctionType, IndexType, IntAttr, IntegerAttr, ModuleOp, StringAttr, f16, f32, f64, i1, i32
from xdsl.ir import Block, Region
from xdsl.irdl import IRDLOperation, irdl_op_definition, result_def

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.nn import NnAddOp, NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolAddOp, SymbolValueType
from kernel_gen.dsl.emit_c import EmitCContext
from kernel_gen.dsl.gen_kernel import GenKernelError, gen_kernel
from kernel_gen.dsl.mlir_gen import build_func_op
from kernel_gen.passes.lowering.nn_to_kernel import LowerNnToKernelPass
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

gen_kernel_module = importlib.import_module("kernel_gen.dsl.gen_kernel")


@irdl_op_definition
class UnsupportedOp(IRDLOperation):
    name = "test.unsupported"
    result = result_def(i32)

    def __init__(self: "UnsupportedOp") -> None:
        super().__init__(result_types=[i32])


def _ctx() -> EmitCContext:
    return EmitCContext(target="cpu")


def _npu_ctx() -> EmitCContext:
    return EmitCContext(target="npu_demo")


def _make_memory_type(shape: list[int], stride: list[int], element_type: object = i32, space: str = "global") -> NnMemoryType:
    return NnMemoryType(
        ArrayAttr([IntAttr(dim) for dim in shape]),
        ArrayAttr([IntAttr(dim) for dim in stride]),
        element_type,
        NnMemorySpaceAttr.from_name(space),
    )


def _tensor_arg(shape: list[int | str], dtype: NumericType = NumericType.Int32) -> Memory:
    return Memory(shape, dtype)


def _arg_attrs(*names: str) -> ArrayAttr[DictionaryAttr]:
    return ArrayAttr([DictionaryAttr({"name": StringAttr(name)}) for name in names])


def _func(name: str, input_types: list[object], result_types: list[object], block: Block, arg_names: tuple[str, ...]) -> func.FuncOp:
    func_type = FunctionType.from_lists(input_types, result_types)
    return func.FuncOp(name, func_type, Region(block), arg_attrs=_arg_attrs(*arg_names))


def _lower_func(func_op: func.FuncOp) -> func.FuncOp:
    """对单个 `func.func` 执行 `LowerNnToKernelPass` 并返回改写后的函数。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 为 I3 的 pass-after IR codegen 测试提供最小包装。
    - 直接在 module 内原地执行 lowering，并返回同一函数实例。

    使用示例:
    - lowered = _lower_func(func_op)

    关联文件:
    - spec: spec/dsl/gen_kernel.md
    - test: test/dsl/test_gen_kernel.py
    - 功能实现: test/dsl/test_gen_kernel.py
    """

    module = ModuleOp([func_op])
    LowerNnToKernelPass().run(module)
    return next(op for op in module.ops if isinstance(op, func.FuncOp))


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
# 最后一次更改: jcc你莫辜负
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

    mem = _make_memory_type([2, 2], [2, 1])
    memory_block = Block(arg_types=[mem])
    memory_block.add_op(func.ReturnOp(memory_block.args[0]))
    memory_func = _func("memory_kernel", [mem], [mem], memory_block, ("input",))
    memory_source = gen_kernel(memory_func, _ctx())
    assert memory_source.startswith("void memory_kernel(const Memory<int32_t>& input, Memory<int32_t>& out)")
    assert "out = input;" in memory_source


# GK-014
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-04 20:25:00 +0800
# 最近一次运行成功时间: 2026-04-04 20:25:00 +0800
# 功能说明: 验证 gen_kernel 模块对外只保留唯一稳定公开入口。
# 测试目的: 锁定 gen_kernel/__all__ 的公开边界，避免 gen_signature/gen_body 继续作为公开稳定接口回流。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_is_the_only_public_entry
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py

def test_gen_kernel_is_the_only_public_entry() -> None:
    assert gen_kernel_module.__all__ == ["GenKernelError", "gen_kernel"]

    namespace: dict[str, object] = {}
    exec("from kernel_gen.dsl.gen_kernel import *", namespace)
    public_names = {name for name in namespace if name != "__builtins__"}

    assert public_names == {"GenKernelError", "gen_kernel"}
    assert namespace["GenKernelError"] is GenKernelError
    assert namespace["gen_kernel"] is gen_kernel
    assert "gen_signature" not in public_names
    assert "gen_body" not in public_names


# GK-001A
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 功能说明: 验证单个普通 op 输入会直接委托给 emit_c。
# 测试目的: 锁定 gen_kernel(op_or_func, ctx) 对单个非 func op 复用 emit_c_op 的公开合同。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_delegates_single_op_input_to_emit_c
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py

def test_gen_kernel_delegates_single_op_input_to_emit_c(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def _fake_emit(op: object, _ctx: EmitCContext) -> str:
        seen.append(op.name)
        return "// single-op"

    monkeypatch.setattr(gen_kernel_module, "emit_c_op", _fake_emit)

    source = gen_kernel(UnsupportedOp(), _ctx())

    assert source == "// single-op"
    assert seen == ["test.unsupported"]


# GK-002
# 创建者: 金铲铲大作战
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-03-23 22:45:14 +0800
# 最近一次运行成功时间: 2026-03-23 22:45:14 +0800
# 功能说明: 验证输入 Memory 参数使用只读签名。
# 测试目的: 验证 gen_kernel 生成的完整源码对 Memory 输入使用 const 引用。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_uses_readonly_memory_inputs
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py

def test_gen_kernel_uses_readonly_memory_inputs() -> None:
    mem = _make_memory_type([2, 2], [2, 1])
    block = Block(arg_types=[mem])
    block.add_op(func.ReturnOp())
    func_op = _func("read_only", [mem], [], block, ("input",))

    source = gen_kernel(func_op, _ctx())

    assert source.startswith("void read_only(const Memory<int32_t>& input)")


# GK-003
# 创建者: 金铲铲大作战
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-03-23 22:45:14 +0800
# 最近一次运行成功时间: 2026-03-23 22:45:14 +0800
# 功能说明: 验证 Memory 结果降为输出参数。
# 测试目的: 验证 gen_kernel 生成的完整源码对 Memory 返回值生成 out 参数。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_lowers_memory_result_to_out_param
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py

def test_gen_kernel_lowers_memory_result_to_out_param() -> None:
    mem = _make_memory_type([2, 2], [2, 1])
    block = Block(arg_types=[mem])
    block.add_op(func.ReturnOp(block.args[0]))
    func_op = _func("produce", [mem], [mem], block, ("input",))

    source = gen_kernel(func_op, _ctx())

    assert source.startswith("void produce(const Memory<int32_t>& input, Memory<int32_t>& out)")


# GK-004
# 创建者: 金铲铲大作战
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-03-23 22:45:14 +0800
# 最近一次运行成功时间: 2026-03-23 22:45:14 +0800
# 功能说明: 验证缺失参数名时仍生成稳定默认命名。
# 测试目的: 验证 gen_kernel 在完整源码中保持标量参数顺序，并在缺失 `arg_attrs.name` 时使用 `arg{index}`。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_uses_default_arg_names_when_missing_attrs
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py

def test_gen_kernel_uses_default_arg_names_when_missing_attrs() -> None:
    block = Block(arg_types=[i32, IndexType(), i32])
    block.add_op(func.ReturnOp())
    func_op = _func("ordered", [i32, IndexType(), i32], [], block, ("lhs", "index", "rhs"))

    source = gen_kernel(func_op, _ctx())

    assert source.startswith("void ordered(int32_t lhs, long long index, int32_t rhs)")

    unnamed_block = Block(arg_types=[i32])
    unnamed_block.add_op(func.ReturnOp())
    unnamed_type = FunctionType.from_lists([i32], [])
    unnamed_func = func.FuncOp(
        "unnamed",
        unnamed_type,
        Region(unnamed_block),
        arg_attrs=ArrayAttr([DictionaryAttr({})]),
    )
    unnamed_source = gen_kernel(unnamed_func, _ctx())
    assert unnamed_source.startswith("void unnamed(int32_t arg0)")

    default_block = Block(arg_types=[i1])
    default_block.add_op(func.ReturnOp())
    default_type = FunctionType.from_lists([i1], [])
    default_func = func.FuncOp("default_names", default_type, Region(default_block))
    default_source = gen_kernel(default_func, _ctx())
    assert default_source.startswith("void default_names(bool arg0)")


# GK-005
# 创建者: 金铲铲大作战
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-03-23 22:45:14 +0800
# 最近一次运行成功时间: 2026-03-23 22:45:14 +0800
# 功能说明: 验证完整源码中的普通 op 顺序与 IR 一致。
# 测试目的: 验证 gen_kernel 的函数级主遍历不改变 IR 中的 op 顺序。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_emits_ops_in_order
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py

def test_gen_kernel_emits_ops_in_order() -> None:
    block = Block(arg_types=[i32, i32])
    first = arith.AddiOp(block.args[0], block.args[1])
    second = arith.SubiOp(block.args[0], block.args[1])
    block.add_op(first)
    block.add_op(second)
    block.add_op(func.ReturnOp())
    func_op = _func("ordered_body", [i32, i32], [], block, ("lhs", "rhs"))
    source = gen_kernel(func_op, _ctx())

    add_idx = source.index("int32_t v0 = (lhs + rhs);")
    sub_idx = source.index("int32_t v1 = (lhs - rhs);")
    assert add_idx < sub_idx


# GK-005A
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 功能说明: 验证普通 op 逐个委托到 emit_c。
# 测试目的: 锁定 gen_kernel 的函数级主遍历只把非 return op 委托给 emit_c_op。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_delegates_to_emit_c_for_non_return_ops
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py

def test_gen_kernel_delegates_to_emit_c_for_non_return_ops(monkeypatch: pytest.MonkeyPatch) -> None:
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
        return f"{_ctx.current_indent}// {op.name}"

    monkeypatch.setattr(gen_kernel_module, "emit_c_op", _fake_emit)

    source = gen_kernel(func_op, _ctx())

    assert seen == ["arith.addi", "arith.subi"]
    assert "// arith.addi" in source
    assert "// arith.subi" in source
    assert "func.return" not in seen


# GK-005B
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 功能说明: 验证 func.return/out 绑定由函数级主遍历流程处理。
# 测试目的: 锁定 return 收尾不走普通 emit_c_op 公开职责，避免 `func.return` 回流为节点级公开接口。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_handles_func_return_and_out_binding_in_main_flow
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py

def test_gen_kernel_handles_func_return_and_out_binding_in_main_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    mem = _make_memory_type([2, 2], [2, 1])
    second_block = Block(arg_types=[mem, mem])
    second_block.add_op(func.ReturnOp(second_block.args[1]))
    second_func = _func("return_second", [mem, mem], [mem], second_block, ("lhs", "rhs"))

    def _unexpected_emit(op: object, _ctx: EmitCContext) -> str:
        raise AssertionError(f"emit_c_op should not see {op}")

    monkeypatch.setattr(gen_kernel_module, "emit_c_op", _unexpected_emit)

    source = gen_kernel(second_func, _ctx())

    assert source.startswith("void return_second(const Memory<int32_t>& lhs, const Memory<int32_t>& rhs, Memory<int32_t>& out)")
    assert "out = rhs;" in source


# GK-006
# 创建者: 金铲铲大作战
# 最后一次更改: jcc你莫辜负
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
# 测试目的: 验证 gen_kernel 拒绝不支持的返回形式与输入类型。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_rejects_unsupported_return_form
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py

def test_gen_kernel_rejects_unsupported_return_form() -> None:
    block = Block(arg_types=[i32])
    block.add_op(func.ReturnOp(block.args[0]))
    func_op = _func("scalar_return", [i32], [i32], block, ("value",))

    with pytest.raises(GenKernelError) as exc_info:
        gen_kernel(func_op, _ctx())

    assert "unsupported return form" in str(exc_info.value)

    tuple_block = Block(arg_types=[])
    tuple_block.add_op(func.ReturnOp())
    tuple_type = FunctionType.from_lists([], [i32, i32])
    tuple_func = func.FuncOp("tuple_return", tuple_type, Region(tuple_block), arg_attrs=ArrayAttr([]))
    with pytest.raises(GenKernelError) as exc_info:
        gen_kernel(tuple_func, _ctx())
    assert "unsupported return form" in str(exc_info.value)

    float_block = Block(arg_types=[f16])
    float_block.add_op(func.ReturnOp())
    float_type = FunctionType.from_lists([f16], [])
    float_func = func.FuncOp("f16_arg", float_type, Region(float_block))
    with pytest.raises(TypeError) as exc_info:
        gen_kernel(float_func, _ctx())
    assert "unsupported type" in str(exc_info.value)

    bad_body_block = Block(arg_types=[i32])
    bad_body_block.add_op(func.ReturnOp(bad_body_block.args[0]))
    bad_body_type = FunctionType.from_lists([i32], [i32])
    bad_body_func = func.FuncOp("bad_body", bad_body_type, Region(bad_body_block), arg_attrs=_arg_attrs("value"))
    with pytest.raises(GenKernelError) as exc_info:
        gen_kernel(bad_body_func, _ctx())
    assert "unsupported return form" in str(exc_info.value)


# GK-012
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-01 15:07:50 +0800
# 最近一次运行成功时间: 2026-04-01 15:07:50 +0800
# 功能说明: 验证 f32/f64 标量与 Memory<f32/f64> 可生成 float/double 与 Memory<float>/Memory<double> 形式签名。
# 测试目的: 锁定 gen_kernel 在完整源码签名中的 f32/f64 类型映射，避免 conv2d 链路在函数级入口阶段被 TypeError 阻断或类型退化。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_supports_float32_scalar_and_memory
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py

def test_gen_kernel_supports_float32_scalar_and_memory() -> None:
    mem_f32 = _make_memory_type([2, 2], [2, 1], element_type=f32)
    block_f32 = Block(arg_types=[mem_f32, f32])
    block_f32.add_op(func.ReturnOp(block_f32.args[0]))
    func_op_f32 = _func("float_kernel", [mem_f32, f32], [mem_f32], block_f32, ("input", "alpha"))

    source_f32 = gen_kernel(func_op_f32, _ctx())

    assert source_f32.startswith("void float_kernel(const Memory<float>& input, float alpha, Memory<float>& out)")

    mem_f64 = _make_memory_type([2, 2], [2, 1], element_type=f64)
    block_f64 = Block(arg_types=[mem_f64, f64])
    block_f64.add_op(func.ReturnOp(block_f64.args[0]))
    func_op_f64 = _func("double_kernel", [mem_f64, f64], [mem_f64], block_f64, ("input", "alpha"))

    source_f64 = gen_kernel(func_op_f64, _ctx())

    assert source_f64.startswith("void double_kernel(const Memory<double>& input, double alpha, Memory<double>& out)")


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
# 测试目的: 锁定 gen_kernel 对 symbol 标量返回的契约，避免退化为 unsupported return form。
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

    source = gen_kernel(func_op, _ctx())

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
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-02 23:04:42 +0800
# 最近一次运行成功时间: 2026-04-02 23:04:42 +0800
# 功能说明: 验证 `build_func_op -> pass -> gen_kernel` 的 memory+memory add 在 cpu target 下可生成源码。
# 测试目的: 清理 raw `nn.add` 直出源码的旧成功口径，锁定 pass 后 `kernel.add` 已被消费为 `cpu::add(lhs, rhs, out)`。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_supports_lowered_nn_add_memory_memory_on_cpu
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py
def test_gen_kernel_supports_lowered_nn_add_memory_memory_on_cpu() -> None:
    def add_direct(lhs: "Tensor[i32, 2, 2]", rhs: "Tensor[i32, 2, 2]") -> "Tensor[i32, 2, 2]":
        return lhs + rhs

    func_op = build_func_op(add_direct, _tensor_arg([2, 2]), _tensor_arg([2, 2]))
    source = gen_kernel(_lower_func(func_op), _ctx())

    assert source.startswith("void add_direct(const Memory<int32_t>& arg0, const Memory<int32_t>& arg1, Memory<int32_t>& out)")
    assert "cpu::add(arg0, arg1, out);" in source
    assert "kernel.add" not in source
    assert "nn.add" not in source
    assert "out = " not in source


# GK-014
# 创建者: jcc你莫辜负
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-02 23:04:42 +0800
# 最近一次运行成功时间: 2026-04-02 23:04:42 +0800
# 功能说明: 验证 `build_func_op -> pass -> gen_kernel` 的 memory+const(i32) add 会先经 `dma.fill` 再生成源码。
# 测试目的: 清理 raw mixed `nn.add` 直接出源码的旧成功口径，锁定 pass 后 `dma.fill + cpu::add(lhs, v0, out)` 文本。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_supports_lowered_nn_add_memory_const_on_cpu
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py
def test_gen_kernel_supports_lowered_nn_add_memory_const_on_cpu() -> None:
    def add_const_direct(lhs: "Tensor[i32, 2, 2]") -> "Tensor[i32, 2, 2]":
        return lhs + 1

    func_op = build_func_op(add_const_direct, _tensor_arg([2, 2]))
    source = gen_kernel(_lower_func(func_op), _ctx())

    assert source.startswith("void add_const_direct(const Memory<int32_t>& arg0, Memory<int32_t>& out)")
    assert "cpu::add(arg0, v0, out);" in source
    assert "for (long long fill0_i = 0; fill0_i < v0.element_count(); ++fill0_i) {" in source
    assert "v0.data()[fill0_i] = 1;" in source
    assert "kernel.add" not in source
    assert "nn.add" not in source
    assert "out = " not in source


# GK-015
# 创建者: jcc你莫辜负
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-02 23:04:42 +0800
# 最近一次运行成功时间: 2026-04-02 23:04:42 +0800
# 功能说明: 验证 `build_func_op -> pass -> gen_kernel` 的 memory+symbol.int add 会先经 `dma.fill` 再生成源码。
# 测试目的: 清理 raw `nn.add(memory, symbol.int)` 直接出源码的旧成功口径，锁定 pass 后 `dma.fill + cpu::add(lhs, v0, out)` 文本与 long long bias 签名。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_supports_lowered_nn_add_memory_symbol_on_cpu
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py
def test_gen_kernel_supports_lowered_nn_add_memory_symbol_on_cpu() -> None:
    def add_symbol_direct(lhs: "Tensor[i32, 2, 2]", bias: int) -> "Tensor[i32, 2, 2]":
        return lhs + bias

    func_op = build_func_op(add_symbol_direct, _tensor_arg([2, 2]), SymbolDim("bias"))
    source = gen_kernel(_lower_func(func_op), _ctx())

    assert source.startswith("void add_symbol_direct(const Memory<int32_t>& arg0, long long arg1, Memory<int32_t>& out)")
    assert "cpu::add(arg0, v0, out);" in source
    assert "for (long long fill0_i = 0; fill0_i < v0.element_count(); ++fill0_i) {" in source
    assert "v0.data()[fill0_i] = arg1;" in source
    assert "kernel.add" not in source
    assert "nn.add" not in source
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


# GK-017
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-02 21:00:00 +0800
# 最近一次运行成功时间: 2026-04-02 21:00:00 +0800
# 功能说明: 验证 npu_demo target 可生成包含 KernelContext 与 thread 查询的 body-level kernel 骨架。
# 测试目的: 锁定签名首参为 `npu_demo::KernelContext& ctx`，并显式生成 `ctx.thread_id()` / `ctx.thread_num()`。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_emits_npu_demo_body_level_kernel
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py
def test_gen_kernel_emits_npu_demo_body_level_kernel() -> None:
    mem = _make_memory_type([64], [1], element_type=f32)
    block = Block(arg_types=[IndexType(), mem])
    func_op = _func("demo_kernel", [IndexType(), mem], [mem], block, ("ctx", "source"))

    source = gen_kernel(func_op, _npu_ctx())

    assert source.startswith(
        "void demo_kernel(npu_demo::KernelContext& ctx, const Memory<float>& source, Memory<float>& out)"
    )
    assert "long long tid = ctx.thread_id();" in source
    assert "long long tnum = ctx.thread_num();" in source
    assert "npu_demo::KernelContext& ctx" in source
    assert "launch" not in source
    assert "barrier" not in source
    assert "arch.launch_kernel" not in source


# GK-018
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-02 21:00:00 +0800
# 最近一次运行成功时间: 2026-04-02 21:00:00 +0800
# 功能说明: 验证 npu_demo target 可生成固定的 dynamic memory/view/slice/deslice/add 管线。
# 测试目的: 锁定 `TSM/TLM`、`view/slice/deslice/add` 固定顺序，并防止回退到 `.view/load/store` 风格。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_emits_npu_demo_memory_pipeline
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py
def test_gen_kernel_emits_npu_demo_memory_pipeline() -> None:
    mem = _make_memory_type([64], [1], element_type=f32)
    block = Block(arg_types=[IndexType(), mem])
    func_op = _func("demo_kernel", [IndexType(), mem], [mem], block, ("ctx", "source"))

    source = gen_kernel(func_op, _npu_ctx())

    tsm_idx = source.index("Memory<float> tsm = ctx.get_dynamic_memory<float>(MemorySpace::TSM);")
    tlm_idx = source.index("Memory<float> tlm = ctx.get_dynamic_memory<float>(MemorySpace::TLM);")
    src_view_idx = source.index("auto src_view = view(source, tid * 16, 16, 1);")
    work_view_idx = source.index("auto work_tile = view(tsm, 0, 16, 1);")
    out_view_idx = source.index("auto out_tile = view(tlm, 0, 16, 1);")
    slice_idx = source.index("slice(work_tile, src_view, 0, 16, 1);")
    add_idx = source.index("add(work_tile, work_tile, out_tile);")
    deslice_idx = source.index("deslice(out_tile, out, tid * 16, 16, 1);")

    assert tsm_idx < tlm_idx < src_view_idx < work_view_idx < out_view_idx < slice_idx < add_idx < deslice_idx
    assert ".view<" not in source
    assert "load<" not in source
    assert "store<" not in source
    assert "slice(source" not in source
    assert "arch.launch_kernel" not in source


# GK-019
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-02 21:25:00 +0800
# 最近一次运行成功时间: 2026-04-02 21:25:00 +0800
# 功能说明: 验证 npu_demo body-level kernel 若 body 含未知 op，必须继续报错。
# 测试目的: 防止固定骨架静默吞掉非法 body 中的未知 op。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_rejects_npu_demo_body_level_kernel_with_unknown_body_op
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py
def test_gen_kernel_rejects_npu_demo_body_level_kernel_with_unknown_body_op() -> None:
    mem = _make_memory_type([64], [1], element_type=f32)
    block = Block(arg_types=[IndexType(), mem])
    block.add_op(UnsupportedOp())
    func_op = _func("demo_kernel", [IndexType(), mem], [mem], block, ("ctx", "source"))

    with pytest.raises(GenKernelError) as exc_info:
        gen_kernel(func_op, _npu_ctx())

    assert "test.unsupported" in str(exc_info.value)


# GK-020
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-02 21:25:00 +0800
# 最近一次运行成功时间: 2026-04-02 21:25:00 +0800
# 功能说明: 验证 npu_demo body-level kernel 若 body 非空但不含未知 op，仍必须报错。
# 测试目的: 锁定当前冻结子集只接受空 body，避免非法 return 等结构被固定骨架吞掉。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_rejects_npu_demo_body_level_kernel_with_nonempty_body
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py
def test_gen_kernel_rejects_npu_demo_body_level_kernel_with_nonempty_body() -> None:
    mem = _make_memory_type([64], [1], element_type=f32)
    block = Block(arg_types=[IndexType(), mem])
    block.add_op(func.ReturnOp())
    func_op = _func("demo_kernel", [IndexType(), mem], [mem], block, ("ctx", "source"))

    with pytest.raises(GenKernelError, match="body must match frozen subset"):
        gen_kernel(func_op, _npu_ctx())


# GK-021
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-04 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-04 00:00:00 +0800
# 功能说明: 验证函数级特化在黑盒 `gen_kernel(...)` 输出上保持既有合同。
# 测试目的: 锁定 direct-return `nn.add`、`conv2d_img2col2d_tiled`、`npu_demo` 三类特化继续只通过 `gen_kernel(...)` 黑盒验证，不依赖内部 helper、内部策略函数或内部策略名。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_black_box_direct_return_nn_add_conv2d_img2col2d_tiled_and_npu_demo_contracts
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py
def test_gen_kernel_black_box_direct_return_nn_add_conv2d_img2col2d_tiled_and_npu_demo_contracts() -> None:
    mem = _make_memory_type([2, 2], [2, 1])
    space = NnMemorySpaceAttr.from_name("global")
    add_block = Block(arg_types=[mem, mem])
    add_op = NnAddOp(add_block.args[0], add_block.args[1], mem, space)
    add_block.add_op(add_op)
    add_block.add_op(func.ReturnOp(add_op.result))
    add_func = _func("add_direct", [mem, mem], [mem], add_block, ("lhs", "rhs"))
    add_source = gen_kernel(add_func, _ctx())
    assert "cpu::add(lhs, rhs, out);" in add_source
    assert "out = " not in add_source

    input_type = _make_memory_type([1, 16, 18, 18], [5184, 324, 18, 1], element_type=f32)
    weight_type = _make_memory_type([16, 16, 3, 3], [144, 9, 3, 1], element_type=f32)
    out_type = _make_memory_type([1, 16, 16, 16], [4096, 256, 16, 1], element_type=f32)
    conv_block = Block(arg_types=[input_type, weight_type])
    conv_func = _func("conv2d_img2col2d_tiled", [input_type, weight_type], [out_type], conv_block, ("input", "weight"))
    conv_source = gen_kernel(conv_func, _ctx())
    assert "cpu::img2col2d(" in conv_source
    assert "constexpr long long Ntile = 1;" in conv_source
    assert "out.at(out_indices) = acc_buffer[((fi * Hotile) + hi) * Wotile + wi];" in conv_source

    npu_mem = _make_memory_type([64], [1], element_type=f32)
    npu_block = Block(arg_types=[IndexType(), npu_mem])
    npu_func = _func("demo_kernel", [IndexType(), npu_mem], [npu_mem], npu_block, ("ctx", "source"))
    npu_source = gen_kernel(npu_func, _npu_ctx())
    assert "ctx.thread_id()" in npu_source
    assert "ctx.get_dynamic_memory<float>(MemorySpace::TSM)" in npu_source
    assert "deslice(out_tile, out, tid * 16, 16, 1);" in npu_source


# GK-I2-001
# 创建者: 大闸蟹
# 最后一次更改: 小李飞刀
# 功能说明: 验证 `build_func_op -> pass -> gen_kernel` 的三条 nn.add CPU 路径可生成源码并完成编译执行。
# 测试目的: 作为 I4 的统一 smoke，确认公开成功链路来自 `build_func_op -> LowerNnToKernelPass -> gen_kernel`，而不是 raw `nn.add` direct-return 特化。
# 使用示例: pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_compiles_and_runs_lowered_nn_add_variants_on_cpu
# 对应功能实现文件路径: kernel_gen/dsl/gen_kernel.py
# 对应 spec 文件路径: spec/dsl/gen_kernel.md
# 对应测试文件路径: test/dsl/test_gen_kernel.py
def test_gen_kernel_compiles_and_runs_lowered_nn_add_variants_on_cpu() -> None:
    def add_direct(lhs: "Tensor[i32, 2, 2]", rhs: "Tensor[i32, 2, 2]") -> "Tensor[i32, 2, 2]":
        return lhs + rhs

    def add_const_direct(lhs: "Tensor[i32, 2, 2]") -> "Tensor[i32, 2, 2]":
        return lhs + 1

    def add_symbol_direct(lhs: "Tensor[i32, 2, 2]", bias: int) -> "Tensor[i32, 2, 2]":
        return lhs + bias

    pair_source = gen_kernel(
        _lower_func(build_func_op(add_direct, _tensor_arg([2, 2]), _tensor_arg([2, 2]))),
        _ctx(),
    )
    const_source = gen_kernel(
        _lower_func(build_func_op(add_const_direct, _tensor_arg([2, 2]))),
        _ctx(),
    )
    symbol_source = gen_kernel(
        _lower_func(build_func_op(add_symbol_direct, _tensor_arg([2, 2]), SymbolDim("bias"))),
        _ctx(),
    )

    assert "cpu::add(arg0, arg1, out);" in pair_source
    assert "kernel.add" not in pair_source
    assert "nn.add" not in pair_source
    assert "arg0.shape()[0]" in const_source
    assert "arg0.shape()[1]" in const_source
    assert "cpu::add(arg0, v0, out);" in const_source
    assert "for (long long fill0_i = 0; fill0_i < v0.element_count(); ++fill0_i) {" in const_source
    assert "v0.data()[fill0_i] = 1;" in const_source
    assert "kernel.add" not in const_source
    assert "nn.add" not in const_source
    assert "arg0.shape()[0]" in symbol_source
    assert "arg0.shape()[1]" in symbol_source
    assert "cpu::add(arg0, v0, out);" in symbol_source
    assert "for (long long fill0_i = 0; fill0_i < v0.element_count(); ++fill0_i) {" in symbol_source
    assert "v0.data()[fill0_i] = arg1;" in symbol_source
    assert "kernel.add" not in symbol_source
    assert "nn.add" not in symbol_source

    cpp_source = f"""\
#include <cstdint>
#include "include/cpu/Memory.h"
#include "include/cpu/Nn.h"

using cpu::Memory;
using cpu::MemoryFormat;
using cpu::MemorySpace;

{pair_source}

{const_source}

{symbol_source}

static int fail(int code) {{ return code; }}

int main() {{
    int32_t lhs_data[4] = {{1, 2, 3, 4}};
    int32_t rhs_data[4] = {{10, 20, 30, 40}};
    int32_t out_pair_data[4] = {{0, 0, 0, 0}};
    int32_t out_const_data[4] = {{0, 0, 0, 0}};
    int32_t out_symbol_data[4] = {{0, 0, 0, 0}};
    long long shape[2] = {{2, 2}};
    long long stride[2] = {{2, 1}};

    Memory<int32_t> lhs(lhs_data, 2, shape, stride);
    Memory<int32_t> rhs(rhs_data, 2, shape, stride);
    Memory<int32_t> out_pair(out_pair_data, 2, shape, stride);
    Memory<int32_t> out_const(out_const_data, 2, shape, stride);
    Memory<int32_t> out_symbol(out_symbol_data, 2, shape, stride);

    add_direct(lhs, rhs, out_pair);
    add_const_direct(lhs, out_const);
    add_symbol_direct(lhs, 7, out_symbol);

    int32_t expected_pair[4] = {{11, 22, 33, 44}};
    int32_t expected_const[4] = {{2, 3, 4, 5}};
    int32_t expected_symbol[4] = {{8, 9, 10, 11}};
    for (int i = 0; i < 4; ++i) {{
        if (out_pair_data[i] != expected_pair[i]) {{
            return fail(1);
        }}
        if (out_const_data[i] != expected_const[i]) {{
            return fail(2);
        }}
        if (out_symbol_data[i] != expected_symbol[i]) {{
            return fail(3);
        }}
    }}
    return 0;
}}
"""
    _compile_and_run(cpp_source)


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
