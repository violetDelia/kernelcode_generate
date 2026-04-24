"""`expectation/pass/lowing` 共享 IR 打印辅助。

创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 为 `expectation/pass/lowing` 目录下的 expectation 提供统一的 case 注释与 IR 打印格式。
- 统一输出 `# CASE-x IR：...`、`# CASE-x 输入 IR：...` 这类带说明的注释头，便于直接查看每个 case 的实际 IR 或输入 IR。
- 支持 `ircheck` 文本 case 与直接操作 xDSL `Operation` / `ModuleOp` 的 expectation 共享同一套打印入口。

使用示例:
- `print_case_actual_ir("CASE-1", CASE_TEXT, result.actual_ir, fallback="静态 lower 结果")`
- `print_case_input_ir("CASE-2", CASE_TEXT, fallback="失败输入")`
- `print_case_ir("CASE-3", "outline 成功结果", module)`

关联文件:
- spec: [`spec/tools/ircheck.md`](../../../spec/tools/ircheck.md)
- spec: [`spec/pass/lowering/nn_lowering.md`](../../../spec/pass/lowering/nn_lowering.md)
- test: [`test/tools/test_ircheck_runner.py`](../../../test/tools/test_ircheck_runner.py)
- 功能实现: [`expectation/pass/lowing/_shared.py`](../../../expectation/pass/lowing/_shared.py)
"""

# Case 列表:
# - 无：本文件仅提供共享打印辅助。

from __future__ import annotations

from io import StringIO
import os

from xdsl.ir import Operation
from xdsl.printer import Printer


def render_case_ir(operation_or_text: Operation | str) -> str:
    """把 operation 或文本渲染成稳定 IR 字符串。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 若输入为 xDSL `Operation`，则使用统一 `Printer` 打印完整 IR。
    - 若输入本身就是文本，则去掉首尾空白并保持正文不变。

    使用示例:
    - `rendered = render_case_ir(module)`
    - `rendered = render_case_ir(result.actual_ir)`

    关联文件:
    - spec: [`spec/tools/ircheck.md`](../../../spec/tools/ircheck.md)
    - test: [`test/tools/test_ircheck_runner.py`](../../../test/tools/test_ircheck_runner.py)
    - 功能实现: [`expectation/pass/lowing/_shared.py`](../../../expectation/pass/lowing/_shared.py)
    """

    if isinstance(operation_or_text, str):
        return operation_or_text.strip()

    stream = StringIO()
    Printer(stream=stream).print_op(operation_or_text)
    return stream.getvalue().rstrip()


def extract_case_desc(case_text: str, fallback: str) -> str:
    """从 `CASE_TEXT` 头部提取 `// CASE:` 描述。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 扫描 `ircheck` 文本中的 `// CASE:` 头。
    - 若未找到，则返回调用方提供的 `fallback`。

    使用示例:
    - `desc = extract_case_desc(CASE_TEXT_STATIC, "static")`

    关联文件:
    - spec: [`spec/tools/ircheck.md`](../../../spec/tools/ircheck.md)
    - test: [`test/tools/test_ircheck_runner.py`](../../../test/tools/test_ircheck_runner.py)
    - 功能实现: [`expectation/pass/lowing/_shared.py`](../../../expectation/pass/lowing/_shared.py)
    """

    for line in case_text.splitlines():
        if line.startswith("// CASE:"):
            return line.split("// CASE:", 1)[1].strip()
    return fallback


def extract_case_payload_ir(case_text: str) -> str:
    """从 `ircheck` 文本中提取真正送入 pass 的 IR 正文。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 跳过 `// COMPILE_ARGS` 与 `// CHECK*` 头部。
    - 返回空行之后的 `builtin.module { ... }` IR 正文。

    使用示例:
    - `input_ir = extract_case_payload_ir(CASE_TEXT_DYNAMIC)`

    关联文件:
    - spec: [`spec/tools/ircheck.md`](../../../spec/tools/ircheck.md)
    - test: [`test/tools/test_ircheck_runner.py`](../../../test/tools/test_ircheck_runner.py)
    - 功能实现: [`expectation/pass/lowing/_shared.py`](../../../expectation/pass/lowing/_shared.py)
    """

    normalized = case_text.strip()
    if "\n\n" in normalized:
        return normalized.split("\n\n", 1)[1].rstrip()
    return normalized


def print_case_ir(
    case_name: str,
    case_desc: str,
    operation_or_text: Operation | str,
    *,
    title: str = "IR",
) -> str:
    """按统一注释格式打印单个 case 的 IR。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 默认至少打印一行 `[CASE-x] 描述`，让批量运行时能看到用例进度。
    - 仅当环境变量 `EXPECTATION_PRINT_CASE_IR` 为真值（如 `1/true/yes/on`）时，
      才额外打印 `# CASE-x ...` 注释头与 IR 正文。
    - 无论是否打印，都返回渲染后的 IR，供调用方复用。

    使用示例:
    - `print_case_ir("CASE-1", "静态 lower 结果", result.actual_ir, title="实际 IR")`
    - `EXPECTATION_PRINT_CASE_IR=1 python expectation/pass/lowing/nn_lowering/broadcast.py`

    关联文件:
    - spec: [`spec/tools/ircheck.md`](../../../spec/tools/ircheck.md)
    - test: [`test/tools/test_ircheck_runner.py`](../../../test/tools/test_ircheck_runner.py)
    - 功能实现: [`expectation/pass/lowing/_shared.py`](../../../expectation/pass/lowing/_shared.py)
    """

    rendered = render_case_ir(operation_or_text)
    print(f"[{case_name}] {case_desc}")
    if os.environ.get("EXPECTATION_PRINT_CASE_IR", "").strip().lower() in {"1", "true", "yes", "on"}:
        print(f"# {case_name} {title}：{case_desc}")
        print(rendered)
    return rendered


def print_case_actual_ir(
    case_name: str,
    case_text: str,
    actual_ir: str,
    *,
    fallback: str,
) -> str:
    """打印 `ircheck` case 的实际输出 IR。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 从 `CASE_TEXT` 自动提取 `// CASE:` 描述。
    - 按统一格式打印 pass 后的 `actual_ir`。

    使用示例:
    - `print_case_actual_ir("CASE-1", CASE_TEXT, result.actual_ir, fallback="static")`

    关联文件:
    - spec: [`spec/tools/ircheck.md`](../../../spec/tools/ircheck.md)
    - test: [`test/tools/test_ircheck_runner.py`](../../../test/tools/test_ircheck_runner.py)
    - 功能实现: [`expectation/pass/lowing/_shared.py`](../../../expectation/pass/lowing/_shared.py)
    """

    return print_case_ir(
        case_name,
        extract_case_desc(case_text, fallback),
        actual_ir,
        title="实际 IR",
    )


def print_case_input_ir(case_name: str, case_text: str, *, fallback: str) -> str:
    """打印 `ircheck` case 的输入 IR。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 从 `CASE_TEXT` 自动提取描述与真实输入 IR。
    - 适用于失败路径或需要额外展示 pass 前输入的 expectation。

    使用示例:
    - `print_case_input_ir("CASE-2", CASE_TEXT_DYNAMIC, fallback="dynamic input")`

    关联文件:
    - spec: [`spec/tools/ircheck.md`](../../../spec/tools/ircheck.md)
    - test: [`test/tools/test_ircheck_runner.py`](../../../test/tools/test_ircheck_runner.py)
    - 功能实现: [`expectation/pass/lowing/_shared.py`](../../../expectation/pass/lowing/_shared.py)
    """

    return print_case_ir(
        case_name,
        extract_case_desc(case_text, fallback),
        extract_case_payload_ir(case_text),
        title="输入 IR",
    )


__all__ = [
    "extract_case_desc",
    "extract_case_payload_ir",
    "print_case_actual_ir",
    "print_case_input_ir",
    "print_case_ir",
    "render_case_ir",
]
