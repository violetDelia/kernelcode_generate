"""ircheck: IR transform check tool.

创建者: 睡觉小分队
最后一次更改: 小李飞刀

功能说明:
- 提供轻量的 IR 变换验证工具：读取单文件 case，按 `COMPILE_ARGS` 运行 pass / pipeline，
  对规范化后的 IR 执行 `CHECK:` / `CHECK-NEXT:` / `CHECK-NOT:` 子串匹配，输出 `true/false`。
- 对外只暴露三条稳定 Python API：`parse_ircheck_file`、`run_ircheck_file`、`run_ircheck_text`，
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
import shlex
import sys
from typing import Literal, Sequence

from xdsl.context import Context
from xdsl.dialects.arith import Arith
from xdsl.dialects.builtin import Builtin
from xdsl.dialects.func import Func
from xdsl.ir import Operation
from xdsl.parser import Parser
from xdsl.printer import Printer

from kernel_gen.dialect.kernel import Kernel
from kernel_gen.dialect.nn import Nn
from kernel_gen.passes.registry import (
    PassRegistryError,
    build_registered_pass,
    build_registered_pipeline,
    load_builtin_passes,
)
from kernel_gen.passes.pass_manager import Pass, PassManager

CheckKind = Literal["CHECK", "CHECK-NEXT", "CHECK-NOT"]


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
    - test: [test/tools/test_ircheck_cli.py](test/tools/test_ircheck_cli.py)
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
        case = parse_ircheck_file(path)
    except Exception as exc:
        return IrcheckResult(
            ok=False,
            exit_code=2,
            actual_ir="",
            failed_check=None,
            message=str(exc),
        )
    return _run_ircheck_case(case)


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
        case = _parse_ircheck_text(text, source_path=source_path)
    except Exception as exc:
        return IrcheckResult(
            ok=False,
            exit_code=2,
            actual_ir="",
            failed_check=None,
            message=str(exc),
        )
    return _run_ircheck_case(case)


def _parse_ircheck_text(text: str, *, source_path: str | None) -> IrcheckCase:
    """解析 case 文本为结构化对象。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

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
            header_lines.append((idx + 1, line))
            continue
        body_start = idx
        break

    input_ir = "\n".join(lines[body_start:])
    if not input_ir.strip():
        raise IrcheckParseError("IrcheckParseError: missing input ir")

    compile_args: str | None = None
    checks: list[CheckDirective] = []
    has_seen_positive_check = False
    for line_no, raw in header_lines:
        content = raw[2:].lstrip()
        if content.startswith("COMPILE_ARGS:"):
            if compile_args is not None:
                raise IrcheckParseError("IrcheckParseError: invalid ircheck header")
            compile_args = content[len("COMPILE_ARGS:") :].strip()
            continue
        if content.startswith("CHECK-NEXT:"):
            if not has_seen_positive_check:
                raise IrcheckParseError("IrcheckParseError: invalid ircheck header")
            check_text = content[len("CHECK-NEXT:") :].strip()
            if not check_text:
                raise IrcheckParseError("IrcheckParseError: invalid ircheck header")
            checks.append(
                CheckDirective(
                    kind="CHECK-NEXT",
                    text=check_text,
                    line_no=line_no,
                )
            )
            has_seen_positive_check = True
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
            has_seen_positive_check = True
            continue
        if content.startswith("CHECK") and ":" in content:
            raise IrcheckParseError("IrcheckParseError: invalid ircheck header")

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
    最后一次更改: 小李飞刀

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


def _parse_compile_args(compile_args: str) -> tuple[str, str] | None:
    """解析 `COMPILE_ARGS:` 字段为执行模式。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅支持两种写法：
      - `--pass <name>`
      - `--pipeline <name>`
    - 其他形态一律返回 `None`。

    使用示例:
    - mode = _parse_compile_args("--pass no-op")
    - assert mode == ("pass", "no-op")

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_runner.py](test/tools/test_ircheck_runner.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    try:
        tokens = shlex.split(compile_args)
    except ValueError:
        return None
    if len(tokens) != 2:
        return None
    flag, name = tokens
    if flag == "--pass":
        return ("pass", name)
    if flag == "--pipeline":
        return ("pipeline", name)
    return None


def _build_default_context() -> Context:
    """构造用于解析与打印的默认 xdsl Context。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 加载 `builtin` / `func` / `arith` 与仓库内 dialect（`nn` / `kernel`）。

    使用示例:
    - ctx = _build_default_context()
    - module = Parser(ctx, ir_text).parse_module()

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_runner.py](test/tools/test_ircheck_runner.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    ctx = Context()
    ctx.load_dialect(Arith)
    ctx.load_dialect(Builtin)
    ctx.load_dialect(Func)
    ctx.load_dialect(Nn)
    ctx.load_dialect(Kernel)
    return ctx


def _run_compile_mode(module: Operation, compile_mode: tuple[str, str]) -> Operation:
    """按 compile mode 执行 pass 或 pipeline。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - `("pass", name)`：构造并运行单个 pass。
    - `("pipeline", name)`：构造并运行 pipeline（PassManager）。

    使用示例:
    - out = _run_compile_mode(module, ("pass", "no-op"))

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_runner.py](test/tools/test_ircheck_runner.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    kind, name = compile_mode
    if kind == "pass":
        pass_obj = build_registered_pass(name)
        if not isinstance(pass_obj, Pass):
            raise TypeError("built pass is not Pass instance")
        out = pass_obj.run(module)
    elif kind == "pipeline":
        pm = build_registered_pipeline(name)
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
    return stream.getvalue().rstrip()


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
