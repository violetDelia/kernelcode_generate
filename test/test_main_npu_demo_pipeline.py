"""main.py npu_demo end-to-end pipeline tests.


功能说明:
- 覆盖 `python3 main.py` 的端到端输出与执行结果，锁定 S3 计划要求的 host/kernel/source 区段。
- 通过 subprocess 运行真实入口，确保脚本走 `dsl_run + npu-demo-lowering + gen_kernel + execute_engine` 正向链路。

使用示例:
- pytest -q test/test_main_npu_demo_pipeline.py

关联文件:
- spec: [`spec/tools/dsl_run.md`](spec/tools/dsl_run.md)
- spec: [`spec/pass/pipeline/npu_demo_lowering.md`](spec/pass/pipeline/npu_demo_lowering.md)
- 功能实现: [`main.py`](main.py)
- test: [`test/test_main_npu_demo_pipeline.py`](test/test_main_npu_demo_pipeline.py)
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


def _find_repo_root(start: Path) -> Path:
    """向上定位当前仓库根目录。


    功能说明:
    - 兼容 worktree 与主仓两种执行环境，优先返回包含 `main.py` 与 `spec/tools/dsl_run.md` 的最近祖先目录。
    - 让端到端测试始终指向当前现场真实可执行入口，而不是写死某一级父目录。

    使用示例:
    - repo_root = _find_repo_root(Path(__file__).resolve().parents[1])

    关联文件:
    - spec: [`spec/tools/dsl_run.md`](spec/tools/dsl_run.md)
    - 功能实现: [`main.py`](main.py)
    - test: [`test/test_main_npu_demo_pipeline.py`](test/test_main_npu_demo_pipeline.py)
    """

    for candidate in (start, *start.parents):
        if (candidate / "main.py").is_file() and (candidate / "spec/tools/dsl_run.md").is_file():
            return candidate
    raise FileNotFoundError("cannot locate main.py and spec/tools/dsl_run.md")


REPO_ROOT = _find_repo_root(Path(__file__).resolve().parents[1])
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from xdsl.dialects import func
from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import Operation

from kernel_gen.core.config import reset_config, set_target
from kernel_gen.dialect.arch import ArchLaunchOp

pytestmark = pytest.mark.npu_demo


def _run_main() -> subprocess.CompletedProcess[str]:
    """按当前 worktree 真实运行 `main.py`。


    功能说明:
    - 使用 `PYTHONPATH` 指向当前 worktree，确保执行的是本轮 diff。
    - 通过 subprocess 运行脚本，保证输出区段和真实编译执行链路都被覆盖。

    使用示例:
    - result = _run_main()

    关联文件:
    - spec: [`spec/tools/dsl_run.md`](spec/tools/dsl_run.md)
    - spec: [`spec/pass/pipeline/npu_demo_lowering.md`](spec/pass/pipeline/npu_demo_lowering.md)
    - 功能实现: [`main.py`](main.py)
    - test: [`test/test_main_npu_demo_pipeline.py`](test/test_main_npu_demo_pipeline.py)
    """

    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(REPO_ROOT)
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "main.py")],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _walk_test_ops(op: Operation) -> list[Operation]:
    """深度遍历 op 子树。


    功能说明:
    - 作为当前测试文件的局部 fixture，避免直连 `main.py` 私有 helper。

    使用示例:
    - ops = _walk_test_ops(func_op)

    关联文件:
    - spec: [`spec/pass/pipeline/npu_demo_lowering.md`](spec/pass/pipeline/npu_demo_lowering.md)
    - 功能实现: [`main.py`](main.py)
    - test: [`test/test_main_npu_demo_pipeline.py`](test/test_main_npu_demo_pipeline.py)
    """

    items: list[Operation] = [op]
    for region in op.regions:
        for block in region.blocks:
            for inner in block.ops:
                items.extend(_walk_test_ops(inner))
    return items


def _select_test_npu_demo_source_functions(module: ModuleOp) -> tuple[func.FuncOp, func.FuncOp]:
    """在测试内定位 npu_demo wrapper/body 函数。


    功能说明:
    - 只使用 lowered module 的公开 IR 结构，不调用 `main.py` 私有 helper。

    使用示例:
    - wrapper, body = _select_test_npu_demo_source_functions(result.module)

    关联文件:
    - spec: [`spec/pass/pipeline/npu_demo_lowering.md`](spec/pass/pipeline/npu_demo_lowering.md)
    - 功能实现: [`main.py`](main.py)
    - test: [`test/test_main_npu_demo_pipeline.py`](test/test_main_npu_demo_pipeline.py)
    """

    func_ops = [op for op in module.ops if isinstance(op, func.FuncOp)]
    wrapper_funcs = [
        func_op
        for func_op in func_ops
        if any(isinstance(inner, ArchLaunchOp) for inner in _walk_test_ops(func_op))
    ]
    assert len(wrapper_funcs) == 1
    wrapper_func = wrapper_funcs[0]
    launch_ops = [inner for inner in _walk_test_ops(wrapper_func) if isinstance(inner, ArchLaunchOp)]
    assert len(launch_ops) == 1
    callee_name = launch_ops[0].callee.root_reference.data
    body_func = next((func_op for func_op in func_ops if func_op.sym_name.data == callee_name), None)
    assert body_func is not None
    return wrapper_func, body_func


def _extract_test_npu_demo_function_source(source: str, function_name: str) -> str:
    """在测试内从完整源码截取单个函数定义。


    功能说明:
    - 复制测试所需的源码定位逻辑，避免直连 `main.py` 私有 helper。

    使用示例:
    - host_source = _extract_test_npu_demo_function_source(source, "matmul_kernel")

    关联文件:
    - spec: [`spec/tools/dsl_run.md`](spec/tools/dsl_run.md)
    - 功能实现: [`main.py`](main.py)
    - test: [`test/test_main_npu_demo_pipeline.py`](test/test_main_npu_demo_pipeline.py)
    """

    signature_markers = (f"void {function_name}(", f"static void {function_name}(")
    offset = 0
    start_offset = None
    for line in source.splitlines(keepends=True):
        if any(marker in line for marker in signature_markers) and "{" in line and not line.rstrip().endswith(";"):
            start_offset = offset
            break
        offset += len(line)
    assert start_offset is not None

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
    raise AssertionError(f"unterminated function source for {function_name!r}")


def test_main_npu_demo_pipeline_prints_host_kernel_source_sections() -> None:
    """验证 main.py 会打印 host/kernel/source 区段并使用四字段 launch。


    功能说明:
    - 锁定 `python3 main.py` 的用户可见输出结构。
    - 锁定 host 段、kernel 段、完整 source、执行与数值校验摘要。

    使用示例:
    - pytest -q test/test_main_npu_demo_pipeline.py -k prints_host_kernel_source_sections

    关联文件:
    - spec: [`spec/tools/dsl_run.md`](spec/tools/dsl_run.md)
    - spec: [`spec/pass/pipeline/npu_demo_lowering.md`](spec/pass/pipeline/npu_demo_lowering.md)
    - 功能实现: [`main.py`](main.py)
    - test: [`test/test_main_npu_demo_pipeline.py`](test/test_main_npu_demo_pipeline.py)
    """

    result = _run_main()
    assert result.returncode == 0, result.stderr
    stdout = result.stdout
    assert "[LOWERED IR]" in stdout
    assert "[HOST SOURCE]" in stdout
    assert "[KERNEL SOURCE]" in stdout
    assert "[SOURCE]" in stdout
    assert "[EXECUTE]" in stdout
    assert "[CHECK]" in stdout
    assert "npu_demo::launch<c_0, c_1, c_2, c_3>(matmul_kernel_device" in stdout
    assert "static void matmul_kernel_device(npu_demo::KernelContext& ctx" not in stdout
    assert "static void matmul_kernel_device(" in stdout
    assert "_cost_DMA_matmul_kernel_device" in stdout
    assert "_cost_MAC_matmul_kernel_device" in stdout
    assert "output matches torch.matmul" in stdout
    assert "npu_demo::launch<1, 1, 1>(" not in stdout


def test_main_npu_demo_pipeline_helpers_split_wrapper_and_kernel_sources() -> None:
    """验证 main.py 的 host/kernel 切分 helper 能定位唯一 wrapper 与 kernel。


    功能说明:
    - 直接导入 `main.py`，对 helper 做机械级回归。
    - 若 lowered module 形态退化为多 wrapper 或缺失 wrapper，helper 会显式失败。

    使用示例:
    - pytest -q test/test_main_npu_demo_pipeline.py -k helpers_split_wrapper_and_kernel_sources

    关联文件:
    - spec: [`spec/tools/dsl_run.md`](spec/tools/dsl_run.md)
    - spec: [`spec/pass/pipeline/npu_demo_lowering.md`](spec/pass/pipeline/npu_demo_lowering.md)
    - 功能实现: [`main.py`](main.py)
    - test: [`test/test_main_npu_demo_pipeline.py`](test/test_main_npu_demo_pipeline.py)
    """

    import importlib

    main_module = importlib.import_module("main")
    set_target("npu_demo")
    try:
        result = main_module.dsl_run(
            main_module.matmul_kernel,
            (
                __import__("torch").empty((32, 32), dtype=__import__("torch").float32),
                __import__("torch").arange(32 * 16, dtype=__import__("torch").float32).reshape(32, 16) / 17.0,
                (__import__("numpy").arange(16 * 32, dtype=__import__("numpy").float32).reshape(16, 32) - 11.0) / 19.0,
            ),
            "npu-demo-lowering",
        )
    finally:
        reset_config()
    wrapper_func, body_func = _select_test_npu_demo_source_functions(result.module)
    host_source = _extract_test_npu_demo_function_source(result.source, wrapper_func.sym_name.data)
    kernel_source = _extract_test_npu_demo_function_source(result.source, body_func.sym_name.data)

    assert wrapper_func.sym_name.data == "matmul_kernel"
    assert body_func.sym_name.data == "matmul_kernel_device"
    assert "_cost_DMA_matmul_kernel_device" in result.source
    assert "_cost_MAC_matmul_kernel_device" in result.source
    assert host_source.startswith("void matmul_kernel(")
    assert "npu_demo::launch<c_0, c_1, c_2, c_3>(matmul_kernel_device" in host_source
    assert kernel_source.startswith("static void matmul_kernel_device(")
    assert "npu_demo::KernelContext& ctx" not in kernel_source
