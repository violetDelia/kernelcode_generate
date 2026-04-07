"""DSL emit_c npu_demo add expectation（静态/动态 + int/symbol 计算）。

创建者: 守护最好的爱莉希雅
最后一次更改: 守护最好的爱莉希雅

功能说明:
- 覆盖 add kernel 的四类公开链路：静态 memory+memory、动态 memory+memory、memory+int、memory+symbol。
- 每个 case 统一走 `parse_function -> build_func_op_from_ast -> LowerNnToKernelPass -> BufferResultsToOutParamsPass -> gen_kernel`。
- 代码生成固定 `target=npu_demo`，不允许 fallback 到 `target=cpu`。
- 锁定 pass 后 ABI 与 emit C 源码关键片段，明确目标口径为 `Memory<GM, int32_t>` 与 `npu_demo::add(...)`。

使用示例:
- `PYTHONPATH=. python expectation/dsl/emit_c/npu_demo/add.py`

关联文件:
- spec: `spec/dsl/ast.md`, `spec/dsl/mlir_gen.md`, `spec/pass/lowering/nn_to_kernel.md`, `spec/pass/lowering/buffer_results_to_out_params.md`, `spec/dsl/emit_c.md`, `spec/dsl/gen_kernel.md`
- test: `test/dsl/test_ast.py`, `test/dsl/test_mlir_gen.py`, `test/pass/test_lowering_nn_to_kernel.py`, `test/pass/test_buffer_results_to_out_params.py`, `test/dsl/test_emit_c.py`, `test/dsl/test_gen_kernel.py`
- 功能实现: `kernel_gen/dsl/ast.py`, `kernel_gen/dsl/mlir_gen.py`, `kernel_gen/passes/lowering/nn_to_kernel.py`, `kernel_gen/passes/lowering/buffer_results_to_out_params.py`, `kernel_gen/dsl/emit_c.py`, `kernel_gen/dsl/gen_kernel.py`
"""

from __future__ import annotations

from pathlib import Path
import sys

from xdsl.dialects import func
from xdsl.dialects.builtin import ModuleOp

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.case_runner import raise_if_failures, run_case
from kernel_gen.dialect.dma import DmaFillOp
from kernel_gen.dialect.kernel import KernelAddOp
from kernel_gen.dialect.symbol import SymbolGetDimOp
from kernel_gen.dsl.ast import parse_function
from kernel_gen.dsl.emit_c import EmitCContext
from kernel_gen.dsl.gen_kernel import gen_kernel
from kernel_gen.dsl.mlir_gen import build_func_op_from_ast
from kernel_gen.passes.lowering.buffer_results_to_out_params import BufferResultsToOutParamsPass
from kernel_gen.passes.lowering.nn_to_kernel import LowerNnToKernelPass
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

STATIC_LHS = Memory([2, 3], NumericType.Int32)
STATIC_RHS = Memory([2, 3], NumericType.Int32)
DYNAMIC_LHS = Memory([SymbolDim("M"), SymbolDim("N")], NumericType.Int32)
DYNAMIC_RHS = Memory([SymbolDim("M"), SymbolDim("N")], NumericType.Int32)
PREFERRED_TARGET = "npu_demo"


def add_static(lhs: "Tensor[i32, 2, 3]", rhs: "Tensor[i32, 2, 3]") -> "Tensor[i32, 2, 3]":
    return lhs + rhs


def add_dynamic(lhs: "Tensor[i32, M, N]", rhs: "Tensor[i32, M, N]") -> "Tensor[i32, M, N]":
    return lhs + rhs


def add_int(lhs: "Tensor[i32, 2, 3]") -> "Tensor[i32, 2, 3]":
    return lhs + 7


def add_symbol(lhs: "Tensor[i32, 2, 3]", bias: int) -> "Tensor[i32, 2, 3]":
    return lhs + bias


def _run_pipeline(fn: object, runtime_args: list[object]) -> tuple[str, str, func.FuncOp, str]:
    """执行单个函数的 AST/MLIR/lowering/emit C 全链路。"""

    func_ast = parse_function(fn)
    func_op = build_func_op_from_ast(func_ast, runtime_args=runtime_args)
    module = ModuleOp([func_op])
    raw_ir = str(module)
    LowerNnToKernelPass().run(module)
    lowered_ir = str(module)
    BufferResultsToOutParamsPass().run(module)
    rewritten_func = next(op for op in module.ops if isinstance(op, func.FuncOp))
    source = gen_kernel(rewritten_func, EmitCContext(target=PREFERRED_TARGET))
    return raw_ir, lowered_ir, rewritten_func, source


def _assert_rewrite_contract(rewritten_func: func.FuncOp) -> None:
    """断言 add 链路在 rewrite 后的 ABI 收口合同。"""

    rewritten_ops = tuple(rewritten_func.body.block.ops)
    kernel_add = next(op for op in rewritten_ops if isinstance(op, KernelAddOp))
    return_op = next(op for op in rewritten_ops if isinstance(op, func.ReturnOp))
    assert sum(isinstance(op, SymbolGetDimOp) for op in rewritten_ops) == 2
    assert len(tuple(rewritten_func.function_type.outputs)) == 0
    assert kernel_add.out == rewritten_func.args[0]
    assert len(return_op.arguments) == 0


def _assert_emit_c_npu_demo_contract(
    source: str,
    fn_name: str,
    *,
    has_temp_buffer: bool,
    has_symbol_scalar: bool,
) -> None:
    """断言 emit C 源码满足 npu_demo 目标合同与 Memory<Space, T> 文本口径。"""

    assert source.startswith('#include "include/npu_demo/npu_demo.h"\n\n')
    assert "cpu::add(" not in source
    assert "fallback to cpu" not in source
    assert f"void {fn_name}(" in source
    assert "Memory<GM, int32_t>& arg0" in source
    assert "const Memory<GM, int32_t>& arg1" in source
    assert "npu_demo::add(" in source
    if has_temp_buffer:
        assert "Memory<GM, int32_t> v0(" in source
        assert "v0.data()[fill0_i] = " in source
        assert "npu_demo::add(arg1, v0, arg0);" in source
    else:
        assert "Memory<GM, int32_t> v0(" not in source
        assert "npu_demo::add(arg1, arg2, arg0);" in source
    if has_symbol_scalar:
        assert "long long arg2" in source


def case_static_add() -> None:
    print("[CASE-1] 静态 add：memory+memory 必须经过 lowering 与 out-param 改写；完成态必须生成 Memory<GM, int32_t> 与 npu_demo::add 文本。")
    raw_ir, lowered_ir, rewritten_func, source = _run_pipeline(add_static, [STATIC_LHS, STATIC_RHS])
    rewritten_ir = str(rewritten_func)
    print("[RAW]")
    print(raw_ir)
    print("[REWRITTEN]")
    print(rewritten_ir)
    print("[SOURCE]")
    print(source)
    _assert_rewrite_contract(rewritten_func)
    assert "nn.add" in raw_ir
    assert "kernel.add" in lowered_ir
    assert "dma.fill" not in lowered_ir
    assert "-> (!nn.memory" not in rewritten_ir
    _assert_emit_c_npu_demo_contract(
        source,
        "add_static",
        has_temp_buffer=False,
        has_symbol_scalar=False,
    )


def case_dynamic_add() -> None:
    print("[CASE-2] 动态 add：shape 符号 M/N 必须保留到 lower IR；完成态必须生成 Memory<GM, int32_t> 与 npu_demo::add 文本。")
    raw_ir, lowered_ir, rewritten_func, source = _run_pipeline(add_dynamic, [DYNAMIC_LHS, DYNAMIC_RHS])
    rewritten_ir = str(rewritten_func)
    print("[RAW]")
    print(raw_ir)
    print("[REWRITTEN]")
    print(rewritten_ir)
    print("[SOURCE]")
    print(source)
    _assert_rewrite_contract(rewritten_func)
    assert "!symbol.int<\"M\">" in lowered_ir
    assert "!symbol.int<\"N\">" in lowered_ir
    assert "kernel.add" in lowered_ir
    assert "dma.fill" not in lowered_ir
    assert "-> (!nn.memory" not in rewritten_ir
    _assert_emit_c_npu_demo_contract(
        source,
        "add_dynamic",
        has_temp_buffer=False,
        has_symbol_scalar=False,
    )


def case_int_add() -> None:
    print("[CASE-3] int 计算 add：memory+const(i32) 必须物化 dma.fill 后再 kernel.add；完成态必须生成 Memory<GM, int32_t> 与 npu_demo::add 文本。")
    raw_ir, lowered_ir, rewritten_func, source = _run_pipeline(add_int, [STATIC_LHS])
    rewritten_ir = str(rewritten_func)
    rewritten_ops = tuple(rewritten_func.body.block.ops)
    print("[RAW]")
    print(raw_ir)
    print("[REWRITTEN]")
    print(rewritten_ir)
    print("[SOURCE]")
    print(source)
    _assert_rewrite_contract(rewritten_func)
    assert any(isinstance(op, DmaFillOp) for op in rewritten_ops)
    assert "arith.constant 7" in lowered_ir
    assert "dma.fill" in lowered_ir
    assert "kernel.add" in lowered_ir
    _assert_emit_c_npu_demo_contract(
        source,
        "add_int",
        has_temp_buffer=True,
        has_symbol_scalar=False,
    )
    assert "v0.data()[fill0_i] = 7;" in source


def case_symbol_add() -> None:
    print("[CASE-4] symbol 计算 add：memory+symbol 必须物化 dma.fill 并透传 symbol 参数；完成态必须生成 Memory<GM, int32_t> 与 npu_demo::add 文本。")
    raw_ir, lowered_ir, rewritten_func, source = _run_pipeline(add_symbol, [STATIC_LHS, SymbolDim("bias")])
    rewritten_ir = str(rewritten_func)
    rewritten_ops = tuple(rewritten_func.body.block.ops)
    print("[RAW]")
    print(raw_ir)
    print("[REWRITTEN]")
    print(rewritten_ir)
    print("[SOURCE]")
    print(source)
    _assert_rewrite_contract(rewritten_func)
    assert any(isinstance(op, DmaFillOp) for op in rewritten_ops)
    assert "!symbol.int<\"bias\">" in lowered_ir
    assert "dma.fill" in lowered_ir
    assert "kernel.add" in lowered_ir
    _assert_emit_c_npu_demo_contract(
        source,
        "add_symbol",
        has_temp_buffer=True,
        has_symbol_scalar=True,
    )
    assert "v0.data()[fill0_i] = arg2;" in source


def main() -> None:
    """运行 add expectation 全部 case。"""

    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-1", case_static_add)
    run_case(failures, "CASE-2", case_dynamic_add)
    run_case(failures, "CASE-3", case_int_add)
    run_case(failures, "CASE-4", case_symbol_add)
    raise_if_failures("dsl emit_c npu_demo add expectation", failures)


if __name__ == "__main__":
    main()
