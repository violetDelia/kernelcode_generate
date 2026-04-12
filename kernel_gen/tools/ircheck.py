"""ircheck: IR transform check tool.

创建者: 睡觉小分队
最后一次更改: 小李飞刀

功能说明:
- 提供轻量的 IR 变换验证工具：读取单文件 case，按 `COMPILE_ARGS` 运行 pass / pipeline，
  对规范化后的 IR 执行 `CHECK:` / `CHECK-NEXT:` / `CHECK-NOT:` 子串匹配，输出 `true/false`。
- 对外仅三条公开 API 作为稳定合同：`parse_ircheck_file`、`run_ircheck_file`、`run_ircheck_text`，
  便于 CLI / pytest / 脚本复用。

使用示例:
- PYTHONPATH=. python -m kernel_gen.tools.ircheck case.ircheck
- from kernel_gen.tools.ircheck import run_ircheck_text
- result = run_ircheck_text(\"\"\"// COMPILE_ARGS: --pass no-op
// CHECK: builtin.module

builtin.module {}
\"\"\")
- assert result.ok is True

关联文件:
- spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
- expectation:
  - [expectation/tools/ircheck/basic_true.py](expectation/tools/ircheck/basic_true.py)
  - [expectation/tools/ircheck/basic_false.py](expectation/tools/ircheck/basic_false.py)
  - [expectation/tools/ircheck/check_next_false.py](expectation/tools/ircheck/check_next_false.py)
  - [expectation/tools/ircheck/README.md](expectation/tools/ircheck/README.md)
- test:
  - [test/tools/test_ircheck_parser.py](test/tools/test_ircheck_parser.py)
  - [test/tools/test_ircheck_runner.py](test/tools/test_ircheck_runner.py)
  - [test/tools/test_ircheck_matcher.py](test/tools/test_ircheck_matcher.py)
- 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
"""

from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from pathlib import Path
import os
import re
import shlex
import sys
from typing import Literal, Sequence

os.environ.setdefault("SYMPY_GMPY", "0")

from xdsl.context import Context
from xdsl.dialects.arith import Arith
from xdsl.dialects.builtin import Builtin
from xdsl.dialects.func import Func
from xdsl.ir import Operation
from xdsl.parser import Parser
from xdsl.printer import Printer

from kernel_gen.dialect.dma import Dma
from kernel_gen.dialect.kernel import Kernel
from kernel_gen.dialect.nn import Nn
from kernel_gen.dialect.symbol import Symbol
from kernel_gen.dialect.tuner import Tuner
from kernel_gen.passes.registry import (
    PassRegistryError,
    build_registered_pass,
    build_registered_pipeline,
    load_builtin_passes,
)
from kernel_gen.passes.pass_manager import Pass, PassManager

CheckKind = Literal["CHECK", "CHECK-NEXT", "CHECK-NOT"]
CASE_SEPARATOR = "// -----"


class IrcheckParseError(ValueError):
    """ircheck case 文件解析错误。

    创建者: 睡觉小分队
    最后一次更改: 小李飞刀

    功能说明:
    - 表示 case 文件头部指令区与输入 IR 正文的结构性错误。
    - `str(e)` 必须以 `spec/tools/ircheck.md` 列出的错误短语之一开头。

    使用示例:
    - raise IrcheckParseError("IrcheckParseError: missing input ir")

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_parser.py](test/tools/test_ircheck_parser.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """


@dataclass(frozen=True)
class IrcheckCaseBlock:
    """由分隔符切分得到的原始 case 文本块。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 表示一个尚未解析的 case 文本块及其在原始文本中的起始行号。
    - 用于支持“单文件多 case（lit 风格分隔符）”的顺序执行语义。

    使用示例:
    - blocks = _split_ircheck_text_into_case_blocks(text)
    - assert blocks[0].start_line == 1

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_runner.py](test/tools/test_ircheck_runner.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    text: str
    start_line: int


@dataclass(frozen=True)
class CheckDirective:
    """一条检查指令。

    创建者: 睡觉小分队
    最后一次更改: 小李飞刀

    功能说明:
    - 表示头部注释区中的一条 `CHECK*:` 指令。

    使用示例:
    - directive = CheckDirective(kind="CHECK", text="func.func @main", line_no=2)

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_parser.py](test/tools/test_ircheck_parser.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    kind: CheckKind
    text: str
    line_no: int


@dataclass(frozen=True)
class IrcheckCase:
    """解析后的 case 对象（尚未执行）。

    创建者: 睡觉小分队
    最后一次更改: 小李飞刀

    功能说明:
    - 保存 `compile_args`、检查指令列表与输入 IR 正文。

    使用示例:
    - case = parse_ircheck_file("case.ircheck")
    - assert case.compile_args.startswith("--pass ")

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_parser.py](test/tools/test_ircheck_parser.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    compile_args: str
    checks: list[CheckDirective]
    input_ir: str
    source_path: str | None = None


@dataclass(frozen=True)
class IrcheckResult:
    """一次执行结果。

    创建者: 睡觉小分队
    最后一次更改: 小李飞刀

    功能说明:
    - 汇总执行是否成功、退出码、规范化后的 IR 与失败信息。

    使用示例:
    - result = run_ircheck_file("case.ircheck")
    - assert result.exit_code in (0, 1, 2)

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_runner.py](test/tools/test_ircheck_runner.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    ok: bool
    exit_code: int
    actual_ir: str
    failed_check: CheckDirective | None = None
    message: str | None = None


def parse_ircheck_file(path: str) -> IrcheckCase:
    """从磁盘读取并解析单个 case 文件。

    创建者: 睡觉小分队
    最后一次更改: 小李飞刀

    功能说明:
    - 解析头部注释区指令（`COMPILE_ARGS:` 与 `CHECK*:`）与输入 IR 正文。

    使用示例:
    - case = parse_ircheck_file("case.ircheck")
    - assert case.source_path == "case.ircheck"

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_parser.py](test/tools/test_ircheck_parser.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    text = Path(path).read_text(encoding="utf-8")
    blocks = _split_ircheck_text_into_case_blocks(text)
    if len(blocks) != 1:
        raise IrcheckParseError("IrcheckParseError: invalid ircheck header")
    return _parse_ircheck_text(text, source_path=path)


def run_ircheck_file(path: str) -> IrcheckResult:
    """运行单个 case 文件。

    创建者: 睡觉小分队
    最后一次更改: 小李飞刀

    功能说明:
    - 读取并解析 case 文件后执行 pass/pipeline。
    - 对规范化 IR 执行 `CHECK*:` 指令匹配，并返回结构化结果。

    使用示例:
    - result = run_ircheck_file("case.ircheck")
    - assert result.ok is True

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_runner.py](test/tools/test_ircheck_runner.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    try:
        text = Path(path).read_text(encoding="utf-8")
        cases = _parse_ircheck_cases(text, source_path=path)
    except Exception as exc:
        return IrcheckResult(
            ok=False,
            exit_code=2,
            actual_ir="",
            failed_check=None,
            message=str(exc),
        )
    return _run_ircheck_cases(cases)


def run_ircheck_text(text: str, source_path: str | None = None) -> IrcheckResult:
    """运行一段 case 文本。

    创建者: 睡觉小分队
    最后一次更改: 小李飞刀

    功能说明:
    - 直接运行完整 case 文本（无需写入文件），其语义与 `run_ircheck_file` 一致。

    使用示例:
    - result = run_ircheck_text(\"\"\"// COMPILE_ARGS: --pass no-op
// CHECK: builtin.module

builtin.module {}
\"\"\")
    - assert result.exit_code == 0

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_runner.py](test/tools/test_ircheck_runner.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    try:
        cases = _parse_ircheck_cases(text, source_path=source_path)
    except Exception as exc:
        return IrcheckResult(
            ok=False,
            exit_code=2,
            actual_ir="",
            failed_check=None,
            message=str(exc),
        )
    return _run_ircheck_cases(cases)


def _split_ircheck_text_into_case_blocks(text: str) -> list[IrcheckCaseBlock]:
    """按 lit 风格分隔符把文本切成多个 case 文本块。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 支持使用 `// -----` 作为 case 分隔符。
    - 返回值保留每个文本块在原始文本中的起始行号，便于错误定位。
    - 若包含分隔符但某个文本块为空，按解析失败处理。

    使用示例:
    - blocks = _split_ircheck_text_into_case_blocks(text)
    - assert len(blocks) >= 1

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_parser.py](test/tools/test_ircheck_parser.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    lines = text.splitlines()
    if not lines:
        return [IrcheckCaseBlock(text=text, start_line=1)]

    blocks: list[IrcheckCaseBlock] = []
    current_lines: list[str] = []
    current_start_line = 1
    saw_separator = False

    for line_no, line in enumerate(lines, start=1):
        if line.strip() == CASE_SEPARATOR:
            saw_separator = True
            block_text = "\n".join(current_lines).strip("\n")
            if not block_text.strip():
                raise IrcheckParseError("IrcheckParseError: invalid ircheck header")
            blocks.append(IrcheckCaseBlock(text=block_text, start_line=current_start_line))
            current_lines = []
            current_start_line = line_no + 1
            continue
        current_lines.append(line)

    tail_text = "\n".join(current_lines).strip("\n")
    if saw_separator and not tail_text.strip():
        raise IrcheckParseError("IrcheckParseError: invalid ircheck header")
    if tail_text.strip():
        blocks.append(IrcheckCaseBlock(text=tail_text, start_line=current_start_line))

    if not blocks:
        blocks.append(IrcheckCaseBlock(text=text, start_line=1))
    return blocks


def _parse_ircheck_cases(text: str, *, source_path: str | None) -> list[IrcheckCase]:
    """解析文本中的一个或多个 case。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 单 case：行为与 `_parse_ircheck_text` 完全一致。
    - 多 case：按 `// -----` 分隔，逐块解析并保留全局行号。

    使用示例:
    - cases = _parse_ircheck_cases(text, source_path="suite.ircheck")
    - assert len(cases) >= 1

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_runner.py](test/tools/test_ircheck_runner.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    blocks = _split_ircheck_text_into_case_blocks(text)
    if len(blocks) == 1:
        return [_parse_ircheck_text(blocks[0].text, source_path=source_path, line_offset=blocks[0].start_line - 1)]

    cases: list[IrcheckCase] = []
    for index, block in enumerate(blocks, start=1):
        case_source = source_path
        if source_path is not None:
            case_source = f"{source_path}#case-{index}"
        case = _parse_ircheck_text(block.text, source_path=case_source, line_offset=block.start_line - 1)
        cases.append(case)
    return cases


def _run_ircheck_cases(cases: Sequence[IrcheckCase]) -> IrcheckResult:
    """顺序执行多个 case，并按 fail-fast 返回结果。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 顺序执行每个 case。
    - 多 case 下任一失败立即返回，并在 message 追加失败 case 序号。
    - 全部通过时返回最后一个 case 的结果。

    使用示例:
    - result = _run_ircheck_cases(cases)
    - assert result.exit_code in (0, 1, 2)

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_runner.py](test/tools/test_ircheck_runner.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    if not cases:
        return IrcheckResult(
            ok=False,
            exit_code=2,
            actual_ir="",
            failed_check=None,
            message="IrcheckParseError: invalid ircheck header",
        )

    last_success: IrcheckResult | None = None
    multi_case = len(cases) > 1
    for index, case in enumerate(cases, start=1):
        result = _run_ircheck_case(case)
        if not result.ok:
            if multi_case and result.message:
                return IrcheckResult(
                    ok=False,
                    exit_code=result.exit_code,
                    actual_ir=result.actual_ir,
                    failed_check=result.failed_check,
                    message=f"{result.message} [case {index}]",
                )
            return result
        last_success = result

    assert last_success is not None  # pragma: no cover - guarded by empty check
    return last_success


def _parse_ircheck_text(text: str, *, source_path: str | None, line_offset: int = 0) -> IrcheckCase:
    """解析 case 文本为结构化对象。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 按 `spec/tools/ircheck.md` 解析头部注释区与输入 IR 正文。
    - 仅解析文件结构，不验证输入 IR 的合法性。

    使用示例:
    - case = _parse_ircheck_text(text, source_path="inline.ircheck")

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_parser.py](test/tools/test_ircheck_parser.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    lines = text.splitlines()
    header_lines: list[tuple[int, str]] = []
    body_start = len(lines)
    for idx, line in enumerate(lines):
        if line.startswith("//"):
            header_lines.append((idx + 1 + line_offset, line))
            continue
        body_start = idx
        break

    input_ir = "\n".join(lines[body_start:])
    if not input_ir.strip():
        raise IrcheckParseError("IrcheckParseError: missing input ir")

    compile_args: str | None = None
    checks: list[CheckDirective] = []
    saw_check = False
    for line_no, raw in header_lines:
        content = raw[2:].lstrip()
        if content.startswith("COMPILE_ARGS:"):
            if compile_args is not None:
                raise IrcheckParseError("IrcheckParseError: invalid ircheck header")
            compile_args = content[len("COMPILE_ARGS:") :].strip()
            if not compile_args:
                raise IrcheckParseError("IrcheckParseError: invalid ircheck header")
            continue
        if content.startswith("CHECK-NEXT:"):
            check_text = content[len("CHECK-NEXT:") :].strip()
            if not check_text:
                raise IrcheckParseError("IrcheckParseError: invalid ircheck header")
            if not saw_check:
                raise IrcheckParseError("IrcheckParseError: invalid ircheck header")
            checks.append(
                CheckDirective(
                    kind="CHECK-NEXT",
                    text=check_text,
                    line_no=line_no,
                )
            )
            continue
        if content.startswith("CHECK-NOT:"):
            check_text = content[len("CHECK-NOT:") :].strip()
            if not check_text:
                raise IrcheckParseError("IrcheckParseError: invalid ircheck header")
            checks.append(
                CheckDirective(
                    kind="CHECK-NOT",
                    text=check_text,
                    line_no=line_no,
                )
            )
            continue
        if content.startswith("CHECK:"):
            check_text = content[len("CHECK:") :].strip()
            if not check_text:
                raise IrcheckParseError("IrcheckParseError: invalid ircheck header")
            checks.append(
                CheckDirective(
                    kind="CHECK",
                    text=check_text,
                    line_no=line_no,
                )
            )
            saw_check = True
            continue

    if compile_args is None:
        raise IrcheckParseError("IrcheckParseError: invalid ircheck header")

    return IrcheckCase(
        compile_args=compile_args,
        checks=checks,
        input_ir=input_ir,
        source_path=source_path,
    )


def _run_ircheck_case(case: IrcheckCase) -> IrcheckResult:
    """执行单个解析后的 case。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 解析 compile args 并通过 pass registry 执行 pass/pipeline。
    - 打印规范化 IR，并按检查语义做子串匹配。

    使用示例:
    - case = parse_ircheck_file("case.ircheck")
    - result = _run_ircheck_case(case)

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_runner.py](test/tools/test_ircheck_runner.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    compile_mode = _parse_compile_args(case.compile_args)
    if compile_mode is None:
        return IrcheckResult(
            ok=False,
            exit_code=2,
            actual_ir="",
            failed_check=None,
            message=f"IrcheckCompileArgsError: unsupported compile args: {case.compile_args}",
        )

    ctx = _build_default_context()
    try:
        module = Parser(ctx, case.input_ir).parse_module()
    except Exception as exc:
        return IrcheckResult(
            ok=False,
            exit_code=2,
            actual_ir="",
            failed_check=None,
            message=f"IrcheckRunError: pass execution failed: failed to parse input ir ({exc})",
        )

    load_builtin_passes()
    try:
        output = _run_compile_mode(module, compile_mode)
    except Exception as exc:
        return IrcheckResult(
            ok=False,
            exit_code=2,
            actual_ir="",
            failed_check=None,
            message=f"IrcheckRunError: pass execution failed: {exc}",
        )

    try:
        actual_ir = _normalize_ir(output)
    except Exception as exc:
        return IrcheckResult(
            ok=False,
            exit_code=2,
            actual_ir="",
            failed_check=None,
            message=f"IrcheckRunError: pass execution failed: failed to print output ({exc})",
        )

    ok, failed_check, message = _match_checks(actual_ir, case.checks, source_path=case.source_path)
    if not ok:
        return IrcheckResult(
            ok=False,
            exit_code=1,
            actual_ir=actual_ir,
            failed_check=failed_check,
            message=message,
        )

    return IrcheckResult(ok=True, exit_code=0, actual_ir=actual_ir, failed_check=None, message=None)


def _parse_name_and_options(value: str) -> tuple[str, dict[str, str]] | None:
    """解析 name 与可选的 {k=v} 选项块。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 `name` 与 `name={k=v}` 两种形态。
    - option 仅接受 `k=v` 形式，逗号分隔，且 key 不可重复。
    - `k` 与 `v` 去掉首尾空白后均不可为空。
    - 发现花括号但不符合语法时返回 `None`。

    使用示例:
    - _parse_name_and_options("tile") == ("tile", {})
    - _parse_name_and_options("tile={analysis-only=true}") == ("tile", {"analysis-only": "true"})

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_runner.py](test/tools/test_ircheck_runner.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    if "{" in value or "}" in value:
        if "={" not in value or not value.endswith("}"):
            return None
        name, option_block = value.split("={", 1)
        if not name:
            return None
        options_text = option_block[:-1]
        if not options_text:
            return None
        options: dict[str, str] = {}
        for item in options_text.split(","):
            if not item or "=" not in item:
                return None
            key, raw_value = item.split("=", 1)
            key = key.strip()
            raw_value = raw_value.strip()
            if not key or not raw_value:
                return None
            if key in options:
                return None
            options[key] = raw_value
        return (name, options)
    if not value:
        return None
    return (value, {})


def _parse_compile_args(compile_args: str) -> tuple[str, str, dict[str, str]] | None:
    """解析 `COMPILE_ARGS:` 字段为执行模式。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持以下写法：
      - `--pass <name>` / `--pipeline <name>`
      - `--pass "<name>{k=v}"` / `--pipeline "<name>{k=v}"`
    - 其他形态一律返回 `None`。

    使用示例:
    - mode = _parse_compile_args("--pass no-op")
    - assert mode == ("pass", "no-op", {})

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_runner.py](test/tools/test_ircheck_runner.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    if "{" in compile_args or "}" in compile_args:
        if re.match(r'^\s*(--pass|--pipeline)\s+("[^"]*"|\'[^\']*\')\s*$', compile_args) is None:
            return None
    try:
        tokens = shlex.split(compile_args)
    except ValueError:
        return None
    if len(tokens) != 2:
        return None
    flag, name = tokens
    parsed = _parse_name_and_options(name)
    if parsed is None:
        return None
    pass_name, options = parsed
    if flag == "--pass":
        return ("pass", pass_name, options)
    if flag == "--pipeline":
        return ("pipeline", pass_name, options)
    return None


def _build_default_context() -> Context:
    """构造用于解析与打印的默认 xdsl Context。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 加载 `builtin` / `func` / `arith` 与仓库内公开 dialect。
    - 默认支持 `nn` / `kernel` / `dma` / `symbol` / `tuner`，便于直接解析 lowering /
      pipeline expectation 中常见的 bridge op 与 memory op。

    使用示例:
    - ctx = _build_default_context()
    - module = Parser(ctx, ir_text).parse_module()

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_runner.py](test/tools/test_ircheck_runner.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    ctx = Context()
    ctx.load_dialect(Builtin)
    ctx.load_dialect(Func)
    ctx.load_dialect(Arith)
    ctx.load_dialect(Nn)
    ctx.load_dialect(Kernel)
    ctx.load_dialect(Dma)
    ctx.load_dialect(Symbol)
    ctx.load_dialect(Tuner)
    return ctx


def _run_compile_mode(module: Operation, compile_mode: tuple[str, str, dict[str, str]]) -> Operation:
    """按 compile mode 执行 pass 或 pipeline。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - `("pass", name, options)`：构造并运行单个 pass。
    - `("pipeline", name, options)`：构造并运行 pipeline（PassManager）。

    使用示例:
    - out = _run_compile_mode(module, ("pass", "no-op", {}))

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_runner.py](test/tools/test_ircheck_runner.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    kind, name, options = compile_mode
    if kind == "pass":
        pass_obj = build_registered_pass(name, options)
        if not isinstance(pass_obj, Pass):
            raise TypeError("built pass is not Pass instance")
        out = pass_obj.run(module)
    elif kind == "pipeline":
        pm = build_registered_pipeline(name, options)
        if not isinstance(pm, PassManager):
            raise TypeError("built pipeline is not PassManager instance")
        out = pm.run(module)
    else:  # pragma: no cover - internal invariant
        raise ValueError(f"unexpected compile mode: {kind}")

    if not isinstance(out, Operation):
        raise TypeError("pass/pipeline did not return xdsl Operation")
    return out


def _normalize_ir(value: Operation) -> str:
    """打印 operation 为规范化 IR 文本。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 使用 xdsl `Printer` 将 operation 打印为文本，用于后续的 line-based 匹配。
    - 对 `kernel.img2col1d` 行做最小格式归一，避免 `#builtin.int` 噪音影响文本匹配。

    使用示例:
    - actual_ir = _normalize_ir(module)

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_runner.py](test/tools/test_ircheck_runner.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    stream = StringIO()
    printer = Printer(stream=stream)
    printer.print_op(value)
    text = stream.getvalue().rstrip()
    if "kernel.img2col1d" in text:
        lines = text.splitlines()
        for idx, line in enumerate(lines):
            if "kernel.img2col1d" not in line:
                continue
            lines[idx] = re.sub(r"#builtin\.int<(-?\d+)>", r"\1", line)
        text = "\n".join(lines)
    return text


def _match_checks(
    actual_ir: str, checks: Sequence[CheckDirective], *, source_path: str | None
) -> tuple[bool, CheckDirective | None, str | None]:
    """在规范化 IR 文本上执行检查指令匹配。

    创建者: 睡觉小分队
    最后一次更改: 小李飞刀

    功能说明:
    - 按 `spec/tools/ircheck.md` 定义的子串匹配语义实现：
      - `CHECK:`：从上一次 positive check 命中行之后继续查找。
      - `CHECK-NEXT:`：必须出现在上一条 positive check 命中行的下一行。
      - `CHECK-NOT:`：禁止出现在相邻两条 positive check 命中行之间（或起始/末尾区间）。

    使用示例:
    - ok, failed, message = _match_checks(actual_ir, case.checks, source_path=case.source_path)

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_runner.py](test/tools/test_ircheck_runner.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    if not checks:
        return (True, None, None)

    lines = actual_ir.splitlines()
    last_positive_line: int | None = None
    pending_not: list[CheckDirective] = []

    def _fail(prefix: str, directive: CheckDirective, detail: str) -> tuple[bool, CheckDirective, str]:
        location = f"{source_path}:{directive.line_no}" if source_path else f"line {directive.line_no}"
        return (
            False,
            directive,
            f"{prefix}: {detail} ({location})",
        )

    def _check_not_range(start_line: int, end_line_exclusive: int) -> tuple[bool, CheckDirective | None, str | None]:
        for directive in pending_not:
            for line in lines[start_line:end_line_exclusive]:
                if directive.text and directive.text in line:
                    return _fail(
                        "IrcheckMatchError: CHECK-NOT matched forbidden text",
                        directive,
                        f"forbidden text '{directive.text}' matched",
                    )
        return (True, None, None)

    def _find_check_line(start_line: int, needle: str) -> int | None:
        for idx in range(start_line, len(lines)):
            if needle and needle in lines[idx]:
                return idx
        return None

    for directive in checks:
        if directive.kind == "CHECK-NOT":
            pending_not.append(directive)
            continue

        if directive.kind == "CHECK":
            start_line = 0 if last_positive_line is None else last_positive_line + 1
            match_line = _find_check_line(start_line, directive.text)
            if match_line is None:
                return _fail(
                    "IrcheckMatchError: CHECK not found",
                    directive,
                    f"text '{directive.text}' not found",
                )
            ok, failed, message = _check_not_range(start_line, match_line)
            if not ok:
                return (ok, failed, message)
            pending_not.clear()
            last_positive_line = match_line
            continue

        if directive.kind == "CHECK-NEXT":
            if last_positive_line is None:
                return _fail(
                    "IrcheckMatchError: CHECK-NEXT not found on next line",
                    directive,
                    "CHECK-NEXT requires previous positive check",
                )
            start_line = last_positive_line + 1
            match_line = start_line
            ok, failed, message = _check_not_range(start_line, match_line)
            if not ok:
                return (ok, failed, message)
            if match_line >= len(lines) or not (directive.text and directive.text in lines[match_line]):
                return _fail(
                    "IrcheckMatchError: CHECK-NEXT not found on next line",
                    directive,
                    f"text '{directive.text}' not found on next line",
                )
            pending_not.clear()
            last_positive_line = match_line
            continue

        return _fail(  # pragma: no cover - internal invariant
            "IrcheckMatchError: CHECK not found",
            directive,
            f"unknown directive kind {directive.kind!r}",
        )

    if pending_not:
        start_line = 0 if last_positive_line is None else last_positive_line + 1
        ok, failed, message = _check_not_range(start_line, len(lines))
        if not ok:
            return (ok, failed, message)

    return (True, None, None)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI 入口：`python -m kernel_gen.tools.ircheck <case-file>`。

    创建者: 睡觉小分队
    最后一次更改: 小李飞刀

    功能说明:
    - 运行单个 case 文件并在标准输出打印 `true/false`。
    - 若文件中包含 `// -----` 分隔符，会按顺序执行多个 case（fail-fast）。
    - 退出码约束见 `spec/tools/ircheck.md`。

    使用示例:
    - PYTHONPATH=. python -m kernel_gen.tools.ircheck case.ircheck

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_runner.py](test/tools/test_ircheck_runner.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("false")
        print("IrcheckCliError: invalid arguments")
        return 2

    result = run_ircheck_file(args[0])
    if result.ok:
        print("true")
        return 0

    print("false")
    if result.message:
        print(result.message)
    if result.failed_check is not None:
        print(f"failed_check: {result.failed_check.kind} {result.failed_check.text!r}")
    if result.actual_ir:
        print("actual_ir:")
        print(result.actual_ir)
    return result.exit_code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = [
    "CheckDirective",
    "IrcheckCase",
    "IrcheckParseError",
    "IrcheckResult",
    "parse_ircheck_file",
    "run_ircheck_file",
    "run_ircheck_text",
]
