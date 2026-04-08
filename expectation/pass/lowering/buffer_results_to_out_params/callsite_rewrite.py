"""buffer_results_to_out_params callsite rewrite expectation.

创建者: jcc你莫辜负
最后一次更改: 小李飞刀

功能说明:
- 以黑盒方式锁定 `LowerNnToKernelPass -> BufferResultsToOutParamsPass -> gen_kernel(...)` 的 O5 成功链路。
- 锁定 rewrite 后单 output、mixed output、caller/callee callsite 改写，以及 half-rewritten IR 的显式失败。

使用示例:
- `PYTHONPATH=. python expectation/pass/lowering/buffer_results_to_out_params/callsite_rewrite.py`

关联文件:
- spec: `spec/dsl/gen_kernel.md`, `spec/pass/lowering/buffer_results_to_out_params.md`, `spec/pass/lowering/nn_to_kernel.md`
- test: `test/dsl/test_gen_kernel.py`, `test/pass/test_buffer_results_to_out_params.py`
- 功能实现: `kernel_gen/dsl/gen_kernel.py`, `kernel_gen/passes/lowering/buffer_results_to_out_params.py`, `kernel_gen/passes/lowering/nn_to_kernel.py`
"""

from __future__ import annotations

from pathlib import Path
import sys

from xdsl.dialects import arith, func
from xdsl.dialects.builtin import ArrayAttr, DictionaryAttr, FunctionType, IntAttr, IntegerAttr, ModuleOp, StringAttr, i1, i32
from xdsl.ir import Block, Region

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.case_runner import raise_if_failures, run_case
from kernel_gen.dialect.dma import DmaFillOp
from kernel_gen.dialect.nn import NnAddOp, NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dsl.emit_c import EmitCContext
from kernel_gen.dsl.gen_kernel import GenKernelError, gen_kernel
from kernel_gen.dsl.mlir_gen import build_func_op
from kernel_gen.passes.lowering.buffer_results_to_out_params import BufferResultsToOutParamsPass
from kernel_gen.passes.lowering.nn_to_kernel import LowerNnToKernelPass
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType


def _make_memory_type(shape: list[int], stride: list[int], element_type: object = i32, space: str = "global") -> NnMemoryType:
    """构造 expectation 用的 `nn.memory` 类型。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 为 O5 expectation 中的 rewritten callee/caller 样例统一构造 `NnMemoryType`。
    - 仅服务于当前 expectation，不扩展业务语义。

    使用示例:
    - mem = _make_memory_type([2, 2], [2, 1])

    关联文件:
    - spec: spec/dsl/gen_kernel.md
    - test: test/dsl/test_gen_kernel.py
    - 功能实现: expectation/pass/lowering/buffer_results_to_out_params/callsite_rewrite.py
    """
    return NnMemoryType(
        ArrayAttr([IntAttr(dim) for dim in shape]),
        ArrayAttr([IntAttr(dim) for dim in stride]),
        element_type,
        NnMemorySpaceAttr.from_name(space),
    )


def _arg_attrs(*names: str) -> ArrayAttr[DictionaryAttr]:
    """为 expectation 内的 `func.func` 构造 `arg_attrs.name`。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 用于显式指定 rewritten out 参数和普通输入参数的名字。
    - 让 expectation 的 IR/源码断言可机械锁定 `arg0/arg1/...` 前置顺序。

    使用示例:
    - attrs = _arg_attrs("arg0", "lhs", "rhs")

    关联文件:
    - spec: spec/pass/lowering/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: expectation/pass/lowering/buffer_results_to_out_params/callsite_rewrite.py
    """
    return ArrayAttr([DictionaryAttr({"name": StringAttr(name)}) for name in names])


def _tensor_arg(shape: list[int]) -> Memory:
    """构造前端 expectation 用的 tensor 参数。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 为 `build_func_op(...)` 提供 `Tensor[i32, ...]` 运行时参数样例。
    - 固定使用 `NumericType.Int32`，与 O5 的 CPU add expectation 对齐。

    使用示例:
    - lhs = _tensor_arg([2, 2])

    关联文件:
    - spec: spec/dsl/mlir_gen.md
    - test: test/dsl/test_gen_kernel.py
    - 功能实现: expectation/pass/lowering/buffer_results_to_out_params/callsite_rewrite.py
    """
    return Memory(shape, NumericType.Int32)


def _func(name: str, input_types: list[object], result_types: list[object], block: Block, arg_names: tuple[str, ...]) -> func.FuncOp:
    """构造 expectation 使用的具名 `func.func`。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 把 block、输入输出类型和 `arg_attrs.name` 组装为单个 `func.FuncOp`。
    - 用于 O5 的 rewritten single output、mixed output 和 half-rewritten IR 样例。

    使用示例:
    - func_op = _func("callee", [mem], [mem], block, ("src",))

    关联文件:
    - spec: spec/dsl/gen_kernel.md
    - test: test/dsl/test_gen_kernel.py
    - 功能实现: expectation/pass/lowering/buffer_results_to_out_params/callsite_rewrite.py
    """
    func_type = FunctionType.from_lists(input_types, result_types)
    return func.FuncOp(name, func_type, Region(block), arg_attrs=_arg_attrs(*arg_names))


def add_direct(lhs: "Tensor[i32, 2, 2]", rhs: "Tensor[i32, 2, 2]") -> "Tensor[i32, 2, 2]":
    return lhs + rhs


def _case_1() -> None:
    print("[CASE-1] build_func_op -> LowerNnToKernelPass -> BufferResultsToOutParamsPass -> gen_kernel")
    frontend_func = build_func_op(add_direct, _tensor_arg([2, 2]), _tensor_arg([2, 2]))
    frontend_module = ModuleOp([frontend_func])
    LowerNnToKernelPass().run(frontend_module)
    frontend_before_ir = str(frontend_module)
    BufferResultsToOutParamsPass().run(frontend_module)
    rewritten_frontend = next(op for op in frontend_module.ops if isinstance(op, func.FuncOp))
    frontend_source = gen_kernel(rewritten_frontend, EmitCContext(target="cpu"))
    frontend_ir = str(rewritten_frontend)

    print("[BEFORE]")
    print(frontend_before_ir)
    print("[AFTER]")
    print(rewritten_frontend)
    print(frontend_source)

    assert "-> (!nn.memory" not in frontend_ir
    assert "func.return %" not in frontend_ir
    assert frontend_source.startswith(
        "void add_direct(Memory<int32_t>& arg0, const Memory<int32_t>& arg1, const Memory<int32_t>& arg2)"
    )
    assert "cpu::add(arg1, arg2, arg0);" in frontend_source
    assert "out = " not in frontend_source


def _case_2() -> None:
    print("[CASE-2] mixed output 重写后，memory 走 arg0，scalar 保留 return")
    mem = _make_memory_type([2, 2], [2, 1])
    mixed_block = Block(arg_types=[mem, i1])
    mixed_block.add_op(func.ReturnOp(mixed_block.args[0], mixed_block.args[1]))
    mixed_func = _func("mixed_out", [mem, i1], [mem, i1], mixed_block, ("input", "flag"))
    mixed_module = ModuleOp([mixed_func])
    mixed_before_ir = str(mixed_module)
    BufferResultsToOutParamsPass().run(mixed_module)
    rewritten_mixed = next(op for op in mixed_module.ops if isinstance(op, func.FuncOp))
    mixed_source = gen_kernel(rewritten_mixed, EmitCContext(target="cpu"))

    print("[BEFORE]")
    print(mixed_before_ir)
    print("[AFTER]")
    print(rewritten_mixed)
    print(mixed_source)

    assert "-> (!nn.memory" not in str(rewritten_mixed)
    assert mixed_source.startswith("bool mixed_out(Memory<int32_t>& arg0, const Memory<int32_t>& input, bool flag)")
    assert "return flag;" in mixed_source


def _case_3() -> None:
    print("[CASE-3] caller/callee callsite rewrite 后不再保留旧 memory call result SSA")
    mem = _make_memory_type([2, 2], [2, 1])
    callee_block = Block(arg_types=[mem])
    callee_block.add_op(func.ReturnOp(callee_block.args[0]))
    callee = _func("callee", [mem], [mem], callee_block, ("src",))

    caller_block = Block(arg_types=[mem])
    fill_value = arith.ConstantOp(IntegerAttr(7, i32))
    call_op = func.CallOp("callee", [caller_block.args[0]], [mem])
    fill_op = DmaFillOp(call_op.results[0], fill_value.result)
    caller_block.add_ops([fill_value, call_op, fill_op, func.ReturnOp()])
    caller = _func("caller", [mem], [], caller_block, ("src",))

    callsite_module = ModuleOp([callee, caller])
    callsite_before_ir = str(callsite_module)
    BufferResultsToOutParamsPass().run(callsite_module)

    rewritten_callee = next(op for op in callsite_module.ops if isinstance(op, func.FuncOp) and op.sym_name.data == "callee")
    rewritten_caller = next(op for op in callsite_module.ops if isinstance(op, func.FuncOp) and op.sym_name.data == "caller")
    caller_ops = list(rewritten_caller.body.blocks.first.ops)
    rewritten_call = next(op for op in caller_ops if isinstance(op, func.CallOp))

    print("[BEFORE]")
    print(callsite_before_ir)
    print("[AFTER]")
    print(rewritten_callee)
    print(rewritten_caller)

    assert list(rewritten_callee.function_type.outputs) == []
    assert len(rewritten_call.results) == 0
    assert len(rewritten_call.arguments) == 2
    assert isinstance(caller_ops[0], arith.ConstantOp)


def _case_4() -> None:
    print("[CASE-4] half-rewritten IR 必须显式失败")
    mem = _make_memory_type([2, 2], [2, 1])
    half_block = Block(arg_types=[mem, mem, mem])
    space = NnMemorySpaceAttr.from_name("global")
    half_add = NnAddOp(half_block.args[1], half_block.args[2], mem, space)
    half_block.add_op(half_add)
    half_block.add_op(func.ReturnOp(half_block.args[0]))
    half_func = _func("half_rewritten", [mem, mem, mem], [mem], half_block, ("arg0", "lhs", "rhs"))

    try:
        gen_kernel(half_func, EmitCContext(target="cpu"))
    except GenKernelError as exc:
        print(f"[EXPECTED-FAILURE] {type(exc).__name__}: {exc}")
        assert "legacy memory return ABI is not supported" in str(exc)
    else:
        raise AssertionError("Expected gen_kernel(...) to reject half-rewritten memory return ABI")


def main() -> None:
    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-1", _case_1)
    run_case(failures, "CASE-2", _case_2)
    run_case(failures, "CASE-3", _case_3)
    run_case(failures, "CASE-4", _case_4)
    raise_if_failures("buffer_results_to_out_params callsite rewrite expectation", failures)


if __name__ == "__main__":
    main()
