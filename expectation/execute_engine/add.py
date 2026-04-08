"""execute_engine add expectation（emit_c 生成源码 + execute_engine 调用路径校验）。

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 构造一个最小 add DSL 函数，经过 AST/MLIR/lowering/emit_c 生成 `target=npu_demo` 的 C++ 源码。
- 通过 `ExecutionEngine.compile(...).execute(...)` 覆盖 execute_engine 的调用链：
  - 编译侧：target include family 校验 + entry shim 注入（当前实现可能为 dry-run）。
  - 运行侧：args 支持 mixed 类型输入（固定 `lhs=torch.Tensor` + `rhs=numpy.ndarray`）。
- “真实编译 + 真实执行 + 真值输出”是目标完成态定义：
  - 若当前 `compile_stdout` 仍为 dry-run，脚本会打印差异并跳过数值断言（但仍要求 compile/execute 返回 ok）。
  - 若已进入真实编译执行，则必须断言输出数值等于 `lhs + rhs`。

使用示例:
- `PYTHONPATH=. python expectation/execute_engine/add.py`

关联文件:
- spec: [`spec/execute_engine/execute_engine.md`](spec/execute_engine/execute_engine.md)
- spec: [`spec/execute_engine/execute_engine_api.md`](spec/execute_engine/execute_engine_api.md)
- spec: [`spec/execute_engine/execute_engine_target.md`](spec/execute_engine/execute_engine_target.md)
- test: [`test/execute_engine/test_execute_engine_compile.py`](test/execute_engine/test_execute_engine_compile.py)
- test: [`test/execute_engine/test_execute_engine_invoke.py`](test/execute_engine/test_execute_engine_invoke.py)
- 功能实现: [`kernel_gen/execute_engine/execution_engine.py`](kernel_gen/execute_engine/execution_engine.py)
- 功能实现: [`kernel_gen/dsl/emit_c.py`](kernel_gen/dsl/emit_c.py)
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from xdsl.dialects import func
from xdsl.dialects.builtin import ModuleOp

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dsl.ast import parse_function
from kernel_gen.dsl.emit_c import EmitCContext
from kernel_gen.dsl.gen_kernel import gen_kernel
from kernel_gen.dsl.mlir_gen import build_func_op_from_ast
from kernel_gen.execute_engine import CompileRequest, ExecutionEngine
from kernel_gen.passes.lowering.buffer_results_to_out_params import BufferResultsToOutParamsPass
from kernel_gen.passes.lowering.nn_to_kernel import LowerNnToKernelPass
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType

try:
    import torch
except ImportError as exc:  # pragma: no cover - expectation 需要真实 torch 环境
    raise RuntimeError("expectation/execute_engine/add.py requires torch") from exc


PREFERRED_TARGET = "npu_demo"


def add_kernel(lhs: "Tensor[i32, 6]", rhs: "Tensor[i32, 6]") -> "Tensor[i32, 6]":
    # 创建者: 小李飞刀
    # 最后一次更改: 小李飞刀
    #
    # 功能说明:
    # - 最小 add kernel（用于 DSL/emit_c 管线），便于稳定生成 `npu_demo::add` 调用代码。
    #
    # 使用示例:
    # - func_ast = parse_function(add_kernel)
    #
    # 关联文件:
    # - spec: spec/execute_engine/execute_engine.md
    # - test: test/execute_engine/test_execute_engine_compile.py
    # - 功能实现: kernel_gen/dsl/ast.py
    return lhs + rhs


def _emit_source(fn: object, runtime_args: list[object]) -> tuple[func.FuncOp, str]:
    """执行 `AST -> MLIR -> lowering -> emit_c` 并返回改写后函数与源码。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 从 Python DSL 函数出发，生成可被 execute_engine 编译的 C++ 源码。
    - 固定 target 为 `npu_demo`，用于校验生成代码路径是否指向 `npu_demo::add`。

    使用示例:
    - lhs = Memory([6], NumericType.Int32)
    - rhs = Memory([6], NumericType.Int32)
    - _, source = _emit_source(add_kernel, [lhs, rhs])

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_execute_engine_compile.py
    - 功能实现: kernel_gen/dsl/mlir_gen.py
    """

    func_ast = parse_function(fn)
    func_op = build_func_op_from_ast(func_ast, runtime_args=runtime_args)
    module = ModuleOp([func_op])
    LowerNnToKernelPass().run(module)
    BufferResultsToOutParamsPass().run(module)
    rewritten_func = next(op for op in module.ops if isinstance(op, func.FuncOp))
    source = gen_kernel(rewritten_func, EmitCContext(target=PREFERRED_TARGET))
    return rewritten_func, source


def _compile_and_execute_with_engine(
    *,
    source: str,
    lhs: "torch.Tensor",
    rhs: "np.ndarray",
) -> tuple["torch.Tensor", object, object]:
    """通过 ExecutionEngine 编译并执行 add，返回输出/编译产物/执行结果。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 固定 `lhs=torch.Tensor`、`rhs=numpy.ndarray`，覆盖 mixed 入参绑定路径。
    - 当前若 compile 仍为 dry-run，本函数仍要求 execute_result.ok=True；数值断言由上层根据 dry-run 状态决定。

    使用示例:
    - out, kernel, execute_result = _compile_and_execute_with_engine(source=source, lhs=lhs, rhs=rhs)

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_execute_engine_invoke.py
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    """

    if lhs.dtype != torch.int32:
        raise AssertionError("lhs dtype must be torch.int32")
    if lhs.ndim != 1:
        raise AssertionError("lhs must be rank-1 tensor")
    if not isinstance(rhs, np.ndarray):
        raise AssertionError("rhs must be numpy.ndarray")
    if rhs.dtype != np.int32:
        raise AssertionError("rhs dtype must be np.int32")
    if rhs.ndim != 1:
        raise AssertionError("rhs must be rank-1 ndarray")
    if int(lhs.shape[0]) != int(rhs.shape[0]):
        raise AssertionError("lhs/rhs shape mismatch")

    lhs = lhs.contiguous()
    rhs = np.ascontiguousarray(rhs)
    out = torch.empty_like(lhs)
    out.fill_(-99)

    engine = ExecutionEngine(target=PREFERRED_TARGET)
    request = CompileRequest(
        source=source,
        target=PREFERRED_TARGET,
        function=add_kernel.__name__,
        entry_point="kg_execute_entry",
        compiler="g++",
        compiler_flags=("-std=c++17", "-O2"),
        link_flags=(),
    )
    kernel = engine.compile(request=request)

    execute_result = kernel.execute(args=(out, lhs, rhs))
    if not execute_result.ok:
        raise AssertionError(
            "execute failed:\n"
            f"failure_phrase={execute_result.failure_phrase}\n"
            f"status_code={execute_result.status_code}\n"
            f"run_stderr={execute_result.run_stderr}"
        )
    return out, kernel, execute_result


def main() -> None:
    """运行 execute_engine add expectation。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 生成 `target=npu_demo` 的 add C++ 源码并校验目标符号为 `npu_demo::add`。
    - 通过 execute_engine 编译并执行：
      - compile dry-run：记录差异并跳过真值断言；
      - compile 非 dry-run：必须断言输出数值等于 `lhs + rhs`。

    使用示例:
    - `PYTHONPATH=. python expectation/execute_engine/add.py`

    关联文件:
    - spec: spec/execute_engine/execute_engine.md
    - test: test/execute_engine/test_execute_engine_compile.py
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    """

    print("[CASE-1] add 生成源码并走 execute_engine：lhs=torch.tensor, rhs=numpy.ndarray")

    lhs_sym = Memory([6], NumericType.Int32)
    rhs_sym = Memory([6], NumericType.Int32)
    rewritten_func, source = _emit_source(add_kernel, [lhs_sym, rhs_sym])

    print("[REWRITTEN]")
    print(rewritten_func)
    print("[SOURCE]")
    print(source)

    assert source.startswith('#include "include/npu_demo/npu_demo.h"\n')
    assert "npu_demo::add(" in source
    assert "cpu::add(" not in source
    assert f"void {add_kernel.__name__}(" in source

    lhs_tensor = torch.tensor([1, 2, 3, 4, 5, 6], dtype=torch.int32)
    rhs_numpy = np.array([10, 20, 30, 40, 50, 60], dtype=np.int32)
    expected = lhs_tensor + torch.from_numpy(rhs_numpy)

    out, kernel, execute_result = _compile_and_execute_with_engine(
        source=source,
        lhs=lhs_tensor,
        rhs=rhs_numpy,
    )

    print("[COMPILE]")
    print(kernel.soname_path)
    print(kernel.compile_stdout)
    assert kernel.target == PREFERRED_TARGET
    assert kernel.function == add_kernel.__name__
    assert execute_result.compile_stdout == kernel.compile_stdout
    assert execute_result.compile_stderr == kernel.compile_stderr

    print("[EXECUTE]")
    print(out)

    if kernel.compile_stdout.startswith("dry-run: "):
        print("[NOTE] compile 为 dry-run：当前仅记录差异，暂不对 out 做真值断言。")
        print("[EXPECTED]")
        print(expected)
        print("[EQUAL?]")
        print(bool(torch.equal(out, expected)))
        return

    assert torch.equal(out, expected), "execute_engine real run must match lhs + rhs"


if __name__ == "__main__":
    main()
