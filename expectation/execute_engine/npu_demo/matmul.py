"""execute_engine tiled matmul expectation（npu_demo 真编译合同）。

创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 构造一个固定 shape 的 tiled matmul DSL 函数，目标是走通
  `AST -> MLIR -> nn lowering -> emit_c/gen_kernel(target=npu_demo) -> compile -> execute`。
- 同时锁定前端 `MemorySpace.TSM` 的 IR 合同：凡是前端显式声明为 `TSM` 的 tile memory，
  进入 IR 后必须保持为 `#nn.space<tsm>`，不能退化成 `#nn.space<shared>`。
- 本 expectation 明确要求 loop region 内的 `nn.matmul` 必须先被 lower 为 `kernel.matmul`，
  再生成 `npu_demo` 家族源码并完成真实编译与真实执行。
- expectation 作为架构合同存在；若当前实现尚未支持 tiled matmul，它应直接失败暴露缺口，
  不能静默回退为 `cpu::matmul`、只生成源码、或 dry-run 编译。

使用示例:
- `PYTHONPATH=. python expectation/execute_engine/npu_demo/matmul.py`

关联文件:
- spec: `spec/execute_engine/execute_engine.md`
- spec: `spec/execute_engine/execute_engine_api.md`
- spec: `spec/execute_engine/execute_engine_target.md`
- spec: `spec/dsl/mlir_gen.md`
- spec: `spec/dsl/emit_mlir.md`
- spec: `spec/pass/lowering/nn_lowering.md`
- spec: `spec/dsl/emit_c.md`
- spec: `spec/dsl/gen_kernel.md`
- test: `test/pass/nn_lowering/matmul.py`
- test: `test/dsl/test_emit_c.py`
- test: `test/dsl/test_gen_kernel.py`
- 功能实现: `kernel_gen/dsl/mlir_gen.py`
- 功能实现: `kernel_gen/dsl/emit_mlir.py`
- 功能实现: `kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`
- 功能实现: `kernel_gen/dsl/emit_c.py`
- 功能实现: `kernel_gen/dsl/gen_kernel.py`
- 功能实现: `kernel_gen/execute_engine/execution_engine.py`
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from xdsl.dialects import func
from xdsl.dialects.builtin import ModuleOp

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.case_runner import raise_if_failures, run_case
from kernel_gen.dsl.ast import parse_function
from kernel_gen.dsl.emit_c import EmitCContext
from kernel_gen.dsl.gen_kernel import gen_kernel
from kernel_gen.dsl.mlir_gen import build_func_op_from_ast
from kernel_gen.execute_engine import CompileRequest, ExecutionEngine
from kernel_gen.operation.dma import alloc, deslice, slice
from kernel_gen.operation.nn import matmul
from kernel_gen.operation.scf import loop
from kernel_gen.passes.lowering.buffer_results_to_out_params import BufferResultsToOutParamsPass
from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.type import NumericType

try:
    import torch
except ImportError as exc:  # pragma: no cover - expectation 必须真实跑 torch
    raise RuntimeError("expectation/execute_engine/npu_demo/matmul.py requires torch") from exc


PREFERRED_TARGET = "npu_demo"


def matmul_kernel(lhs: "Tensor[f32, 32, 16]", rhs: "Tensor[f32, 16, 32]") -> "Tensor[f32, 32, 32]":
    out = alloc([32, 32], NumericType.Float32, MemorySpace.GM)
    for m0 in loop(0, 32, 16):
        for n0 in loop(0, 32, 16):
            lhs_tile = slice(lhs, [m0, 0], [16, 16], [1, 1], MemorySpace.TSM)
            rhs_tile = slice(rhs, [0, n0], [16, 16], [1, 1], MemorySpace.TSM)
            partial = matmul(lhs_tile, rhs_tile)
            deslice(partial, out, [m0, n0], [16, 16], [1, 1])
    return out


def _build_raw_func(fn: object, runtime_args: list[object]) -> func.FuncOp:
    """执行 `AST -> MLIR` 并返回原始 `func.func`。"""

    func_ast = parse_function(fn)
    return build_func_op_from_ast(func_ast, runtime_args=runtime_args)


def _lower_and_rewrite_func(fn: object, runtime_args: list[object]) -> func.FuncOp:
    """执行 `AST -> MLIR -> nn lowering -> rewrite` 并返回改写后函数。"""

    func_op = _build_raw_func(fn, runtime_args)
    module = ModuleOp([func_op])
    NnLoweringPass().run(module)
    BufferResultsToOutParamsPass().run(module)
    return next(op for op in module.ops if isinstance(op, func.FuncOp))


def _emit_source(rewritten_func: func.FuncOp) -> str:
    """对 rewrite 后函数执行 `gen_kernel(target=npu_demo)`。"""

    return gen_kernel(rewritten_func, EmitCContext(target=PREFERRED_TARGET))


def _compile_and_execute_with_engine(
    source: str,
    lhs: "torch.Tensor",
    rhs: "np.ndarray",
) -> tuple["torch.Tensor", object, object]:
    """通过 ExecutionEngine 真实编译并执行 tiled matmul。"""

    if lhs.dtype != torch.float32:
        raise AssertionError("lhs dtype must be torch.float32")
    if lhs.ndim != 2 or lhs.shape != (32, 16):
        raise AssertionError("lhs must be shape (32, 16)")
    if not isinstance(rhs, np.ndarray):
        raise AssertionError("rhs must be numpy.ndarray")
    if rhs.dtype != np.float32:
        raise AssertionError("rhs dtype must be np.float32")
    if rhs.ndim != 2 or rhs.shape != (16, 32):
        raise AssertionError("rhs must be shape (16, 32)")
    lhs = lhs.contiguous()
    rhs = np.ascontiguousarray(rhs)
    out = torch.empty((32, 32), dtype=torch.float32)

    engine = ExecutionEngine(target=PREFERRED_TARGET)
    request = CompileRequest(
        source=source,
        target=PREFERRED_TARGET,
        function=matmul_kernel.__name__,
        entry_point="kg_execute_entry",
        compiler="g++",
        compiler_flags=("-std=c++17", "-O2"),
        link_flags=(),
    )
    kernel = engine.compile(request=request)

    args = (out, lhs, rhs)
    execute_result = kernel.execute(args=args)
    if not execute_result.ok:
        raise AssertionError(
            "execute failed:\n"
            f"failure_phrase={execute_result.failure_phrase}\n"
            f"status_code={execute_result.status_code}\n"
            f"run_stderr={execute_result.run_stderr}"
        )
    return out, kernel, execute_result


def case_matmul_emit_compile_execute() -> None:
    """固定 shape tiled matmul 必须生成 npu_demo 源码并执行成功。"""

    print("[CASE-3] tiled matmul 生成 npu_demo 源码并执行，结果等于 torch.matmul(lhs, rhs)")
    lhs = Memory([32, 16], NumericType.Float32)
    rhs = Memory([16, 32], NumericType.Float32)
    rewritten_func = _lower_and_rewrite_func(matmul_kernel, [lhs, rhs])
    source = _emit_source(rewritten_func)

    print("[REWRITTEN]")
    print(rewritten_func)
    print("[SOURCE]")
    print(source)

    rewritten_text = str(rewritten_func)
    assert "kernel.matmul" in rewritten_text
    assert "nn.matmul" not in rewritten_text

    assert source.startswith('#include "include/npu_demo/npu_demo.h"\n')
    assert "npu_demo::matmul(" in source
    assert "cpu::matmul(" not in source
    assert source.count("for (") >= 2
    assert "slice(" in source
    assert "deslice(" in source
    assert f"void {matmul_kernel.__name__}(" in source

    print("[COMPILE]")
    lhs_tensor = torch.arange(32 * 16, dtype=torch.float32).reshape(32, 16) / 17.0
    rhs_numpy = (np.arange(16 * 32, dtype=np.float32).reshape(16, 32) - 11.0) / 19.0
    expected = torch.matmul(lhs_tensor, torch.from_numpy(rhs_numpy))
    result, kernel, execute_result = _compile_and_execute_with_engine(
        source,
        lhs_tensor,
        rhs_numpy,
    )
    print(kernel.soname_path)
    print(execute_result)
    assert not kernel.compile_stdout.startswith("dry-run: "), "Expectation: execute_engine 必须真实编译，不能 dry-run"

    print("[EXECUTE]")
    print(result)
    assert isinstance(result, torch.Tensor)
    assert result.dtype == torch.float32
    assert result.shape == (32, 32)
    assert torch.allclose(result, expected, atol=1e-5, rtol=1e-5)


def case_frontend_tsm_space_contract() -> None:
    """前端显式 `TSM` tile memory 必须在 IR 中保持为 `#nn.space<tsm>`。"""

    print("[CASE-1] 前端 MemorySpace.TSM 在 raw IR 中必须保持为 #nn.space<tsm>")
    lhs = Memory([32, 16], NumericType.Float32)
    rhs = Memory([16, 32], NumericType.Float32)
    raw_func = _build_raw_func(matmul_kernel, [lhs, rhs])
    raw_text = str(raw_func)

    print("[RAW]")
    print(raw_func)

    assert "#nn.space<tsm>" in raw_text, "frontend TSM memory must materialize as #nn.space<tsm> in raw IR"
    assert "#nn.space<shared>" not in raw_text, "frontend TSM memory must not degrade to #nn.space<shared>"
    assert 'space = #nn.space<tsm>' in raw_text, "nn.matmul tile space must remain #nn.space<tsm>"


def case_lowering_rewrites_loop_matmul_and_keeps_tsm() -> None:
    """loop 内 `nn.matmul` 必须 lower 为 `kernel.matmul`，且 TSM 口径保持不变。"""

    print("[CASE-2] lowering 后 loop 内 nn.matmul -> kernel.matmul，且 TSM 仍为 #nn.space<tsm>")
    lhs = Memory([32, 16], NumericType.Float32)
    rhs = Memory([16, 32], NumericType.Float32)
    rewritten_func = _lower_and_rewrite_func(matmul_kernel, [lhs, rhs])
    rewritten_text = str(rewritten_func)

    print("[REWRITTEN]")
    print(rewritten_func)

    assert "#nn.space<tsm>" in rewritten_text, "rewritten IR must keep #nn.space<tsm> for TSM tile memory"
    assert "#nn.space<shared>" not in rewritten_text, "rewritten IR must not degrade TSM tile memory to #nn.space<shared>"
    assert "kernel.matmul" in rewritten_text, "loop-region nn.matmul must be lowered to kernel.matmul"
    assert "nn.matmul" not in rewritten_text, "rewritten IR must not keep residual nn.matmul"


def main() -> None:
    """运行 execute_engine tiled matmul expectation。"""

    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-1", case_frontend_tsm_space_contract)
    run_case(failures, "CASE-2", case_lowering_rewrites_loop_matmul_and_keeps_tsm)
    run_case(failures, "CASE-3", case_matmul_emit_compile_execute)
    raise_if_failures("execute_engine tiled matmul expectation", failures)


if __name__ == "__main__":
    main()
