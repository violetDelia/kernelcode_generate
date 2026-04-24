"""`NnLoweringPass` reduce 系列的 `ir_text` expectation 共享入口。
[immutable-file]


创建者: 守护最好的爱莉希雅
最后一次更改: 大闸蟹

功能说明:
- 为 `reduce_min/reduce_sum/reduce_max` 提供静态与符号形状两组 `ir_text`
  expectation。
- 三类 reduce 统一 lower 为 `kernel.reduce`，并通过 `kind` 区分
  `sum/min/max`。
- 共享入口只负责运行完整 `CASE_TEXT` 与打印实际 IR，不做 token 替换。

使用示例:
- `PYTHONPATH=. python expectation/pass/lowing/nn_lowering/reduce/reduce_min.py`
- `PYTHONPATH=. python expectation/pass/lowing/nn_lowering/reduce`

关联文件:
- spec: [`spec/pass/lowering/nn_lowering.md`](spec/pass/lowering/nn_lowering.md)
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
- test: [`test/pass/nn_lowering/reduce_sum.py`](test/pass/nn_lowering/reduce_sum.py)
- test: [`test/pass/nn_lowering/reduce_min.py`](test/pass/nn_lowering/reduce_min.py)
- test: [`test/pass/nn_lowering/reduce_max.py`](test/pass/nn_lowering/reduce_max.py)
- 功能实现: [`kernel_gen/tools/ircheck.py`](kernel_gen/tools/ircheck.py)
- 功能实现: [`kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`](kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
"""

# Case 列表:
# - Case-reduce-sum: 正例：静态/符号维度 nn.reduce_sum 输入应 lower 为 dma.alloc + kernel.reduce(kind=sum) + func.return。
# - Case-reduce-min: 正例：静态/符号维度 nn.reduce_min 输入应 lower 为 dma.alloc + kernel.reduce(kind=min) + func.return。
# - Case-reduce-max: 正例：静态/符号维度 nn.reduce_max 输入应 lower 为 dma.alloc + kernel.reduce(kind=max) + func.return。

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

CaseText = str | list[str] | tuple[str, ...]


def _normalize_case_texts(case_text: CaseText | list[CaseText] | tuple[CaseText, ...]) -> list[str]:
    """把单条或多条 case 文本归一为 list[str]。"""

    if isinstance(case_text, str):
        return [case_text]
    texts: list[str] = []
    for item in case_text:
        if isinstance(item, str):
            texts.append(item)
        else:
            texts.extend(_normalize_case_texts(item))
    return texts


def run_case_texts(
    op_name: str,
    case_text_static: CaseText,
    case_text_dynamic: CaseText,
) -> None:
    """运行单个 reduce 子用例的静态与符号维度文本。"""

    for variant, case_text in (
        ("static", case_text_static),
        ("dynamic", case_text_dynamic),
    ):
        texts = _normalize_case_texts(case_text)
        is_multi = len(texts) > 1
        for index, text in enumerate(texts, start=1):
            label = f"{op_name}:{variant}"
            if is_multi:
                label = f"{label}#{index}"
            result = run_ircheck_text(
                text,
                source_path=(
                    f"expectation/pass/lowing/nn_lowering/reduce/{op_name}.py:{variant}"
                    + (f"#{index}" if is_multi else "")
                ),
            )
            assert result.ok is True, (
                f"{label}: expected ok=True, got ok={result.ok}, "
                f"exit_code={result.exit_code}, message={result.message!r}"
            )
            assert result.exit_code == 0, f"{label}: expected exit_code=0, got {result.exit_code}"
            assert "kernel.reduce" in result.actual_ir, (
                f"{label}: actual_ir must contain kernel.reduce"
            )
            assert f"nn.{op_name}" not in result.actual_ir, (
                f"{label}: actual_ir must not contain residual nn.{op_name}"
            )
            print_case_actual_ir(
                f"CASE-{op_name}-{variant}" + (f"-{index}" if is_multi else ""),
                text,
                result.actual_ir,
                fallback=label,
            )


def run_single(
    op_name: str,
    case_text_static: CaseText,
    case_text_dynamic: CaseText,
) -> None:
    """运行单个 reduce expectation。"""

    failures: list[tuple[str, BaseException]] = []
    run_case(
        failures,
        f"CASE-{op_name}",
        lambda: run_case_texts(op_name, case_text_static, case_text_dynamic),
    )
    raise_if_failures(f"nn_lowering reduce {op_name} expectation", failures)


def _load_case_specs() -> dict[str, tuple[CaseText, CaseText]] :
    import importlib

    cases: dict[str, tuple[CaseText, CaseText]] = {}
    for op_name in ("reduce_sum", "reduce_min", "reduce_max"):
        module = importlib.import_module(op_name)
        cases[op_name] = (
            module.CASE_TEXT_STATIC,
            module.CASE_TEXT_DYNAMIC,
        )
    return cases


def main(selected_ops: list[str] | None = None) -> None:
    """运行 reduce `ir_text` expectation。"""

    cases = _load_case_specs()
    selected = selected_ops or ["reduce_sum", "reduce_min", "reduce_max"]
    failures: list[tuple[str, BaseException]] = []
    for op_name in selected:
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
    raise_if_failures("nn_lowering reduce expectation", failures)


__all__ = ["main", "run_case_texts", "run_single"]
