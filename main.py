"""本地端到端运行入口。

创建者: 金铲铲大作战
最后一次更改: 大闸蟹

功能说明:
- 演示一个 tiled matmul DSL 函数如何通过 `dsl_run(...)` 走完
  `mlir_gen -> npu-demo-lowering -> gen_kernel -> execute_engine`。
- 使用显式 out 参数，符合当前 `dsl_run` 不支持 DSL 值返回的公开合同。
- 运行后会打印 lowered IR、host source、kernel source、完整 source、执行结果和数值校验摘要。
- host/kernel 段均从同一次 lowered module 的真实发射结果中提取，不手写拼接源码。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 main.py`

关联文件:
- spec: [`spec/tools/dsl_run.md`](spec/tools/dsl_run.md)
- spec: [`spec/pass/pipeline/npu_demo_lowering.md`](spec/pass/pipeline/npu_demo_lowering.md)
- test: [`test/test_main_npu_demo_pipeline.py`](test/test_main_npu_demo_pipeline.py)
- 功能实现: [`kernel_gen/tools/dsl_run.py`](kernel_gen/tools/dsl_run.py)
"""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import torch
from xdsl.dialects import func
from xdsl.dialects.builtin import ModuleOp

from kernel_gen.core.config import set_target
from kernel_gen.dialect.arch import ArchLaunchOp
from kernel_gen.operation.dma import deslice, slice
from kernel_gen.operation.nn import matmul
from kernel_gen.operation.scf import loop
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.tools.dsl_run import dsl_run


REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_NPU_DEMO_PRELUDE = '#include "include/npu_demo/npu_demo.h"\nusing namespace npu_demo;\n\n'


def _walk_ops(op: object) -> list[object]:
    """深度遍历并收集 op 子树中的所有 operation。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 递归扫描 operation / region / block 层级，便于在 lowered module 中定位 wrapper 与 kernel。
    - 只用于 main.py 的展示切分，不承担任何 IR 变换职责。

    使用示例:
    - ops = _walk_ops(module)

    关联文件:
    - spec: [`spec/tools/dsl_run.md`](spec/tools/dsl_run.md)
    - test: [`test/test_main_npu_demo_pipeline.py`](test/test_main_npu_demo_pipeline.py)
    - 功能实现: [`main.py`](main.py)
    """

    items: list[object] = [op]
    regions = getattr(op, "regions", ())
    for region in regions:
        for block in getattr(region, "blocks", ()):
            for inner in getattr(block, "ops", ()):
                items.extend(_walk_ops(inner))
    return items


def _is_npu_demo_wrapper(func_op: func.FuncOp) -> bool:
    """判断 lowered module 里的 `func.func` 是否为 npu_demo wrapper。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - wrapper 的唯一机械特征是其子树中含有 `arch.launch`。
    - body kernel 则不含 `arch.launch`，且生成源码不再暴露 `npu_demo::KernelContext& ctx` 参数。

    使用示例:
    - assert _is_npu_demo_wrapper(wrapper_func) is True

    关联文件:
    - spec: [`spec/pass/pipeline/npu_demo_lowering.md`](spec/pass/pipeline/npu_demo_lowering.md)
    - test: [`test/test_main_npu_demo_pipeline.py`](test/test_main_npu_demo_pipeline.py)
    - 功能实现: [`main.py`](main.py)
    """

    return any(isinstance(inner, ArchLaunchOp) for inner in _walk_ops(func_op))


def _select_npu_demo_source_functions(module: ModuleOp) -> tuple[func.FuncOp, func.FuncOp]:
    """从 lowered module 中定位唯一 host wrapper 与 device kernel。

    创建者: 金铲铲大作战
    最后一次更改: 大闸蟹

    功能说明:
    - 允许 module 在 wrapper 与 device kernel 之外继续包含 sibling cost function。
    - wrapper 通过唯一 `arch.launch` 识别，device kernel 通过 launch callee 精确定位。
    - 若 wrapper/callee 结构不符合当前 pipeline 形态，显式失败，避免 main.py 静默打印错误区段。

    使用示例:
    - wrapper_func, body_func = _select_npu_demo_source_functions(result.module)

    关联文件:
    - spec: [`spec/pass/pipeline/npu_demo_lowering.md`](spec/pass/pipeline/npu_demo_lowering.md)
    - test: [`test/test_main_npu_demo_pipeline.py`](test/test_main_npu_demo_pipeline.py)
    - 功能实现: [`main.py`](main.py)
    """

    func_ops = [op for op in module.ops if isinstance(op, func.FuncOp)]
    wrapper_funcs = [func_op for func_op in func_ops if _is_npu_demo_wrapper(func_op)]
    if len(wrapper_funcs) != 1:
        raise RuntimeError("npu-demo-lowering module does not contain a unique arch.launch wrapper")
    wrapper_func = wrapper_funcs[0]
    launch_ops = [inner for inner in _walk_ops(wrapper_func) if isinstance(inner, ArchLaunchOp)]
    if len(launch_ops) != 1:
        raise RuntimeError("npu-demo-lowering wrapper does not contain a unique arch.launch")
    callee_name = launch_ops[0].callee.root_reference.data
    body_func = next((func_op for func_op in func_ops if func_op.sym_name.data == callee_name), None)
    if body_func is None:
        raise RuntimeError(f"npu-demo-lowering module does not contain launch callee {callee_name!r}")
    return wrapper_func, body_func


def _strip_npu_demo_prelude(source: str) -> str:
    """去掉 npu_demo 公共 prelude，便于单独展示 host/kernel 区段。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - `gen_kernel(target="npu_demo")` 会自动加上统一 prelude。
    - main.py 的 `[HOST SOURCE]` / `[KERNEL SOURCE]` 只展示具体函数源码，避免重复打印 prelude。

    使用示例:
    - body_source = _strip_npu_demo_prelude(gen_kernel(wrapper_func, EmitCContext()))

    关联文件:
    - spec: [`spec/tools/dsl_run.md`](spec/tools/dsl_run.md)
    - test: [`test/test_main_npu_demo_pipeline.py`](test/test_main_npu_demo_pipeline.py)
    - 功能实现: [`main.py`](main.py)
    """

    if source.startswith(_NPU_DEMO_PRELUDE):
        return source[len(_NPU_DEMO_PRELUDE) :]
    return source


def _extract_npu_demo_function_source(source: str, function_name: str) -> str:
    """从完整 source 中截取 npu_demo 的单个函数定义。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - `dsl_run(...)` 的完整 source 已包含 host wrapper 与 device kernel。
    - 这里按函数名截取具体定义，避免再次走旧 `gen_kernel(...)` 发射面。
    - 仅用于 main.py 展示分段，不承担任何 IR 变换职责。

    使用示例:
    - host_source = _extract_npu_demo_function_source(result.source, wrapper_func.sym_name.data)

    关联文件:
    - spec: [`spec/dsl/gen_kernel/gen_kernel.md`](spec/dsl/gen_kernel/gen_kernel.md)
    - test: [`test/test_main_npu_demo_pipeline.py`](test/test_main_npu_demo_pipeline.py)
    - 功能实现: [`main.py`](main.py)
    """

    signature_markers = (f"void {function_name}(", f"static void {function_name}(")
    start_offset = None
    for line_start, line in _iterate_source_lines(source):
        if any(marker in line for marker in signature_markers) and "{" in line and not line.rstrip().endswith(";"):
            start_offset = line_start
            break
    if start_offset is None:
        raise RuntimeError(f"unable to locate function source for {function_name!r}")

    brace_depth = 0
    started = False
    for index in range(start_offset, len(source)):
        char = source[index]
        if char == "{":
            brace_depth += 1
            started = True
        elif char == "}":
            brace_depth -= 1
            if started and brace_depth == 0:
                return source[start_offset : index + 1].strip()
    raise RuntimeError(f"unterminated function source for {function_name!r}")


def _iterate_source_lines(source: str) -> list[tuple[int, str]]:
    """列举 source 中的每一行及其起始偏移。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 为 `_extract_npu_demo_function_source(...)` 提供行首偏移，便于定位 definition 起点。
    - 仅用于 main.py 的展示切分。

    使用示例:
    - for line_start, line in _iterate_source_lines(result.source):

    关联文件:
    - spec: [`spec/tools/dsl_run.md`](spec/tools/dsl_run.md)
    - test: [`test/test_main_npu_demo_pipeline.py`](test/test_main_npu_demo_pipeline.py)
    - 功能实现: [`main.py`](main.py)
    """

    lines: list[tuple[int, str]] = []
    offset = 0
    for line in source.splitlines(keepends=True):
        lines.append((offset, line))
        offset += len(line)
    return lines


def matmul_kernel(
    out: "Tensor[f32, 32, 32]",
    lhs: "Tensor[f32, 32, 16]",
    rhs: "Tensor[f32, 16, 32]",
) -> None:
    """固定 tile 的 matmul DSL 样例。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 以 `16x16` tile 切分输出的 M/N 轴。
    - 每个 tile 内先把 `lhs/rhs` 切到 `TSM`，再调用 `nn.matmul`，最后写回 out。
    - 函数没有 DSL 返回值，输出只通过 `out` 参数写回。

    使用示例:
    - `set_target("npu_demo"); dsl_run(matmul_kernel, (out, lhs, rhs), "npu-demo-lowering")`

    关联文件:
    - spec: [`spec/tools/dsl_run.md`](spec/tools/dsl_run.md)
    - test: [`test/test_main_npu_demo_pipeline.py`](test/test_main_npu_demo_pipeline.py)
    - 功能实现: [`main.py`](main.py)
    """

    for m0 in loop(0, 32, 16):
        for n0 in loop(0, 32, 16):
            lhs_tile = slice(lhs, [m0, 0], [16, 16], [1, 1], MemorySpace.TSM)
            rhs_tile = slice(rhs, [0, n0], [16, 16], [1, 1], MemorySpace.TSM)
            partial = matmul(lhs_tile, rhs_tile)
            deslice(out, partial, [m0, n0], [16, 16], [1, 1])


def main() -> None:
    """运行 tiled matmul 端到端样例并校验输出。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 构造 torch/numpy 混合真实参数。
    - 调用 `dsl_run` 使用注册名 `npu-demo-lowering` 完成 lowering、源码生成、编译和执行。
    - 用 `torch.matmul` 作为数值参考，失败时抛出异常。
    - 按 S3 计划打印 `[LOWERED IR]`、`[HOST SOURCE]`、`[KERNEL SOURCE]`、`[SOURCE]`、`[EXECUTE]`、`[CHECK]`。

    使用示例:
    - `main()`

    关联文件:
    - spec: [`spec/tools/dsl_run.md`](spec/tools/dsl_run.md)
    - test: [`test/test_main_npu_demo_pipeline.py`](test/test_main_npu_demo_pipeline.py)
    - 功能实现: [`main.py`](main.py)
    """

    out = torch.empty((32, 32), dtype=torch.float32)
    lhs = torch.arange(32 * 16, dtype=torch.float32).reshape(32, 16) / 17.0
    rhs = (np.arange(16 * 32, dtype=np.float32).reshape(16, 32) - 11.0) / 19.0
    expected = torch.matmul(lhs, torch.from_numpy(rhs))

    set_target("npu_demo")
    result = dsl_run(matmul_kernel, (out, lhs, rhs), "npu-demo-lowering")

    wrapper_func, body_func = _select_npu_demo_source_functions(result.module)
    host_source = _extract_npu_demo_function_source(result.source, wrapper_func.sym_name.data)
    kernel_source = _extract_npu_demo_function_source(result.source, body_func.sym_name.data)

    print("[LOWERED IR]")
    print(result.module)
    print("[HOST SOURCE]")
    print(host_source)
    print("[KERNEL SOURCE]")
    print(kernel_source)
    print("[SOURCE]")
    print(result.source)
    print("[EXECUTE]")
    print(result.execute_result)

    if not result.execute_result.ok:
        raise RuntimeError(f"execute failed: {result.execute_result.failure_phrase!r}")

    max_abs_diff = torch.max(torch.abs(out - expected)).item()
    print(f"[CHECK] output matches torch.matmul, max_abs_diff={max_abs_diff:.6g}")


if __name__ == "__main__":
    main()
