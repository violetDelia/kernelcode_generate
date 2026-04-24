"""`NnLoweringPass` element_binary 系列的 `ir_text` expectation 共享入口。
[immutable-file]


创建者: 守护最好的爱莉希雅
最后一次更改: 大闸蟹

功能说明:
- 使用完整 `CASE_TEXT` 调用 `run_ircheck_text(...)`，
  展示 element_binary 类算子从 `nn.*` 到 `kernel.binary_elewise(kind=...)`
  的改写结果。
- 覆盖 `add/sub/mul/div/truediv` 五个子用例，全部使用 `ircheck`
  原生 `CHECK` / `CHECK-NEXT` / `CHECK-NOT` 语法。
- 共享入口只负责执行文本与打印实际 IR，不再做任何 token 替换。

使用示例:
- `PYTHONPATH=. python expectation/pass/lowing/nn_lowering/element_binary/add.py`
- `PYTHONPATH=. python expectation/pass/lowing/nn_lowering/element_binary`

关联文件:
- spec: [`spec/pass/lowering/nn_lowering.md`](spec/pass/lowering/nn_lowering.md)
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
- test: [`test/pass/test_lowering_nn_to_kernel.py`](test/pass/test_lowering_nn_to_kernel.py)
- 功能实现: [`kernel_gen/tools/ircheck.py`](kernel_gen/tools/ircheck.py)
- 功能实现: [`kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`](kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
"""

# Case 列表:
# - Case-add: 正例：静态/符号维度 nn.add 输入应 lower 为 dma.alloc + kernel.binary_elewise(kind=add) + func.return。
# - Case-sub: 正例：静态/符号维度 nn.sub 输入应 lower 为 dma.alloc + kernel.binary_elewise(kind=sub) + func.return。
# - Case-mul: 正例：静态/符号维度 nn.mul 输入应 lower 为 dma.alloc + kernel.binary_elewise(kind=mul) + func.return。
# - Case-div: 正例：静态/符号维度 nn.div 输入应 lower 为 dma.alloc + kernel.binary_elewise(kind=div) + func.return。
# - Case-truediv: 正例：静态/符号维度 nn.truediv 输入应 lower 为 dma.alloc + kernel.binary_elewise(kind=div) + func.return。

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
    """运行单个 element_binary 子用例的静态与符号维度文本。"""

    kind_name = "div" if op_name == "truediv" else op_name
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
                    f"expectation/pass/lowing/nn_lowering/element_binary/{op_name}.py:{variant}"
                    + (f"#{index}" if is_multi else "")
                ),
            )
            assert result.ok is True, (
                f"{label}: expected ok=True, got ok={result.ok}, exit_code={result.exit_code}, "
                f"message={result.message!r}"
            )
            assert result.exit_code == 0, f"{label}: expected exit_code=0, got {result.exit_code}"
            assert "kernel.binary_elewise" in result.actual_ir, (
                f"{label}: actual_ir must contain kernel.binary_elewise"
            )
            assert f'kind = "{kind_name}"' in result.actual_ir, (
                f'{label}: actual_ir must contain kind = "{kind_name}"'
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
    """运行单个 element_binary expectation。"""

    failures: list[tuple[str, BaseException]] = []
    run_case(
        failures,
        f"CASE-{op_name}",
        lambda: run_case_texts(op_name, case_text_static, case_text_dynamic),
    )
    raise_if_failures(f"nn_lowering element_binary {op_name} expectation", failures)


def _load_case_specs() -> dict[str, tuple[CaseText, CaseText]] :
    import importlib

    cases: dict[str, tuple[CaseText, CaseText]] = {}
    for op_name in ("add", "sub", "mul", "div", "truediv"):
        module = importlib.import_module(op_name)
        cases[op_name] = (
            module.CASE_TEXT_STATIC,
            module.CASE_TEXT_DYNAMIC,
        )
    return cases


def main(selected_ops: list[str] | None = None) -> None:
    """运行 element_binary `ir_text` expectation。"""

    cases = _load_case_specs()
    selected = selected_ops or ["add", "sub", "mul", "div", "truediv"]
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
    raise_if_failures("nn_lowering element_binary expectation", failures)


__all__ = ["main", "run_case_texts", "run_single"]
