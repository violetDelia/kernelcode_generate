"""main.py npu_demo end-to-end pipeline tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

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

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

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

from kernel_gen.core.config import reset_config, set_target

pytestmark = pytest.mark.npu_demo


def _run_main() -> subprocess.CompletedProcess[str]:
    """按当前 worktree 真实运行 `main.py`。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

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


def test_main_npu_demo_pipeline_prints_host_kernel_source_sections() -> None:
    """验证 main.py 会打印 host/kernel/source 区段并使用四字段 launch。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

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
    assert "npu_demo::launch<1, 1, 1, 0>(matmul_kernel_device" in stdout
    assert "static void matmul_kernel_device(npu_demo::KernelContext& ctx" not in stdout
    assert "static void matmul_kernel_device(" in stdout
    assert "_cost_DMA_matmul_kernel_device" in stdout
    assert "_cost_MAC_matmul_kernel_device" in stdout
    assert "output matches torch.matmul" in stdout
    assert "npu_demo::launch<1, 1, 1>(" not in stdout


def test_main_npu_demo_pipeline_helpers_split_wrapper_and_kernel_sources() -> None:
    """验证 main.py 的 host/kernel 切分 helper 能定位唯一 wrapper 与 kernel。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

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
    wrapper_func, body_func = main_module._select_npu_demo_source_functions(result.module)
    host_source = main_module._extract_npu_demo_function_source(result.source, wrapper_func.sym_name.data)
    kernel_source = main_module._extract_npu_demo_function_source(result.source, body_func.sym_name.data)

    assert wrapper_func.sym_name.data == "matmul_kernel"
    assert body_func.sym_name.data == "matmul_kernel_device"
    assert "_cost_DMA_matmul_kernel_device" in result.source
    assert "_cost_MAC_matmul_kernel_device" in result.source
    assert host_source.startswith("void matmul_kernel(")
    assert "npu_demo::launch<1, 1, 1, 0>(matmul_kernel_device" in host_source
    assert kernel_source.startswith("static void matmul_kernel_device(")
    assert "npu_demo::KernelContext& ctx" not in kernel_source
