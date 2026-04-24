"""`NnLoweringPass` img2col 系列的 `ir_text` expectation 共享入口。
[immutable-file]


创建者: 守护最好的爱莉希雅
最后一次更改: 大闸蟹

功能说明:
- 为 `nn.img2col1d/img2col2d` 提供静态与符号形状两组 `ir_text` expectation。
- 保证 `kernel.img2col*` 出现且不残留 `nn.img2col*`。

使用示例:
- `PYTHONPATH=. python expectation/pass/lowing/nn_lowering/img2col/img2col1d.py`
- `PYTHONPATH=. python expectation/pass/lowing/nn_lowering/img2col`

关联文件:
- spec: [`spec/pass/lowering/nn_lowering.md`](spec/pass/lowering/nn_lowering.md)
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
- test: [`test/pass/test_lowering_nn_to_kernel.py`](test/pass/test_lowering_nn_to_kernel.py)
- 功能实现: [`kernel_gen/tools/ircheck.py`](kernel_gen/tools/ircheck.py)
- 功能实现: [`kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`](kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
"""

# Case 列表:
# - Case-img2col1d: 正例：静态/符号维度 nn.img2col1d 输入应 lower 为 dma.alloc + kernel.img2col1d + func.return。
# - Case-img2col2d: 正例：静态/符号维度 nn.img2col2d 输入应 lower 为 dma.alloc + kernel.img2col2d + func.return。

from __future__ import annotations

from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "kernel_gen").exists())
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from importlib import import_module

print_case_actual_ir = import_module("expectation.pass.lowing._shared").print_case_actual_ir
from expectation.utils.case_runner import raise_if_failures, run_case
from kernel_gen.tools.ircheck import run_ircheck_text


def run_case_texts(
    op_name: str,
    case_text_static: str,
    case_text_dynamic: str,
) -> None:
    """运行单个 img2col 子用例的静态与符号维度文本。"""

    for variant, case_text in (
        ("static", case_text_static),
        ("dynamic", case_text_dynamic),
    ):
        result = run_ircheck_text(
            case_text,
            source_path=(
                f"expectation/pass/lowing/nn_lowering/img2col/{op_name}.py:{variant}"
            ),
        )
        assert result.ok is True, (
            f"{op_name}({variant}): expected ok=True, got ok={result.ok}, "
            f"exit_code={result.exit_code}, message={result.message!r}"
        )
        assert result.exit_code == 0, (
            f"{op_name}({variant}): expected exit_code=0, got {result.exit_code}"
        )
        assert f"kernel.{op_name}" in result.actual_ir, (
            f"{op_name}({variant}): actual_ir must contain kernel.{op_name}"
        )
        assert f"nn.{op_name}" not in result.actual_ir, (
            f"{op_name}({variant}): actual_ir must not contain residual nn.{op_name}"
        )
        print_case_actual_ir(
            f"CASE-{op_name}-{variant}",
            case_text,
            result.actual_ir,
            fallback=f"{op_name}:{variant}",
        )


def run_single(
    op_name: str,
    case_text_static: str,
    case_text_dynamic: str,
) -> None:
    """运行单个 img2col expectation。"""
    failures: list[tuple[str, BaseException]] = []
    run_case(
        failures,
        f"CASE-{op_name}",
        lambda: run_case_texts(op_name, case_text_static, case_text_dynamic),
    )
    raise_if_failures(f"nn_lowering img2col {op_name} expectation", failures)


def _load_case_specs() -> dict[str, tuple[str, str]] :
    import importlib

    cases: dict[str, tuple[str, str]] = {}
    for op_name in ("img2col1d", "img2col2d"):
        module = importlib.import_module(op_name)
        cases[op_name] = (
            module.CASE_TEXT_STATIC,
            module.CASE_TEXT_DYNAMIC,
        )
    return cases


def main(selected_ops: list[str] | None = None) -> None:
    """运行 img2col `ir_text` expectation。"""

    cases = _load_case_specs()
    selected = selected_ops or ["img2col1d", "img2col2d"]
    failures: list[tuple[str, BaseException]] = []
    for op_name in selected:
        if op_name not in cases:
            raise ValueError(f"unknown img2col op: {op_name}")
        case_text_static, case_text_dynamic = cases[op_name]
        run_case(
            failures,
            f"CASE-{op_name}",
            lambda op=op_name, st=case_text_static, dt=case_text_dynamic: run_case_texts(
                op,
                st,
                dt,
            ),
        )
    raise_if_failures("nn_lowering img2col expectation", failures)


__all__ = ["main", "run_case_texts", "run_single"]
