"""`NnLoweringPass` 的 ircheck 共享辅助。
[immutable-file]


创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 为 `expectation/pass/lowing/nn_lowering` 提供统一的 IR 渲染与 `ircheck` 匹配入口。
- 约定 expectation 使用 `ir_text` + `run_ircheck_text(...)` 进行结构断言。
- 公开 `assert_ircheck_matches(...)`，让每个 case 只关心“当前 module 的文本是否符合预期”。

使用示例:
- `assert_ircheck_matches(module, [("CHECK", "dma.alloc"), ("CHECK-NOT", "nn.add")], source_path=__file__)`

关联文件:
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
- spec: [`spec/pass/lowering/nn_lowering.md`](spec/pass/lowering/nn_lowering.md)
- test: [`test/tools/test_ircheck_runner.py`](test/tools/test_ircheck_runner.py)
- 功能实现: [`kernel_gen/tools/ircheck.py`](kernel_gen/tools/ircheck.py)
"""

# Case 列表:
# - 无：本文件仅提供 ircheck 共享辅助函数。

from __future__ import annotations

from io import StringIO
from pathlib import Path
import sys
from typing import TypeAlias

from xdsl.ir import Operation
from xdsl.printer import Printer

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from importlib import import_module

print_case_actual_ir = import_module("expectation.pass.lowing._shared").print_case_actual_ir
from kernel_gen.tools.ircheck import run_ircheck_text

IrcheckDirective: TypeAlias = tuple[str, str]


def render_operation(operation_or_text: Operation | str) -> str:
    """把 operation 或文本转成 `ircheck` 输入所需的 IR 文本。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 若输入为 xDSL operation，则使用统一 `Printer` 打印。
    - 若输入已经是文本，则只做首尾空白整理。

    使用示例:
    - `actual_ir = render_operation(module)`
    - `actual_ir = render_operation("builtin.module {}")`

    关联文件:
    - spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
    - test: [`test/tools/test_ircheck_runner.py`](test/tools/test_ircheck_runner.py)
    - 功能实现: [`expectation/pass/lowing/nn_lowering/_shared.py`](expectation/pass/lowing/nn_lowering/_shared.py)
    """

    if isinstance(operation_or_text, str):
        return operation_or_text.strip()

    stream = StringIO()
    printer = Printer(stream=stream)
    printer.print_op(operation_or_text)
    return stream.getvalue().rstrip()


def build_ircheck_case(actual_ir: str, directives: list[IrcheckDirective]) -> str:
    """构造基于 `no-op` 的最小 ircheck case 文本。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 统一把 `actual_ir` 嵌入 `// COMPILE_ARGS: --pass no-op` 头部。
    - 让 `ircheck` 只负责匹配，不再额外改写输入 IR。

    使用示例:
    - `case_text = build_ircheck_case(actual_ir, [("CHECK", "kernel.add")])`

    关联文件:
    - spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
    - test: [`test/tools/test_ircheck_runner.py`](test/tools/test_ircheck_runner.py)
    - 功能实现: [`expectation/pass/lowing/nn_lowering/_shared.py`](expectation/pass/lowing/nn_lowering/_shared.py)
    """

    lines = ["// COMPILE_ARGS: --pass no-op"]
    for directive, text in directives:
        lines.append(f"// {directive}: {text}")
    lines.append("")
    lines.append(actual_ir.strip())
    return "\n".join(lines) + "\n"


def assert_ircheck_matches(
    operation_or_text: Operation | str,
    directives: list[IrcheckDirective],
    *,
    source_path: str,
    case_name: str | None = None,
    case_desc: str | None = None,
) -> None:
    """断言当前 IR 能通过给定 `ircheck` 指令集合。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 把 lowering 后的 `module` 或已有 IR 文本送进 `run_ircheck_text(...)`。
    - 统一要求匹配成功；若失败，则把 `failed_check`、`message` 与 `actual_ir` 一并暴露。

    使用示例:
    - `assert_ircheck_matches(module, [("CHECK", "dma.alloc")], source_path=__file__)`
    - `assert_ircheck_matches(module, directives, source_path=__file__, case_name="CASE-1", case_desc="静态 lower")`

    关联文件:
    - spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
    - test: [`test/tools/test_ircheck_runner.py`](test/tools/test_ircheck_runner.py)
    - 功能实现: [`expectation/pass/lowing/nn_lowering/_shared.py`](expectation/pass/lowing/nn_lowering/_shared.py)
    """

    actual_ir = render_operation(operation_or_text)
    case_text = build_ircheck_case(actual_ir, directives)
    result = run_ircheck_text(case_text, source_path=source_path)
    assert result.ok is True, (
        f"ircheck expected ok=True, got ok={result.ok}, exit_code={result.exit_code}, "
        f"failed_check={result.failed_check}, message={result.message!r}, actual_ir=\n{result.actual_ir}"
    )
    assert result.exit_code == 0, f"ircheck expected exit_code=0, got {result.exit_code}"
    if case_name is not None:
        print_case_actual_ir(
            case_name,
            case_text,
            result.actual_ir,
            fallback=case_desc or case_name,
        )


__all__ = [
    "IrcheckDirective",
    "assert_ircheck_matches",
    "build_ircheck_case",
    "render_operation",
]
