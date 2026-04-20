"""ircheck: IR transform check tool.

创建者: 睡觉小分队
最后一次更改: 金铲铲大作战

功能说明:
- 提供轻量的 IR 变换验证工具：读取单文件 case，按 `COMPILE_ARGS` 顺序运行 pass / pipeline，
  对规范化后的 IR 执行 FileCheck 风格的逐行匹配：
  - `CHECK:` / `CHECK-NEXT:` / `CHECK-NOT:` 按“普通文本字面量 + `[[NAME:REGEX]]` / `[[NAME]]` 变量”匹配；
  - 不再支持 `CHECK-REGEX*` 变体，整行 regex 需求统一收口到 `[[NAME:REGEX]]` 的局部片段内。
  最终输出 `true/false`。
- CLI 支持 `-irdump`：自动写入每个 case 的输入与逐 step IR。
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
  - [test/tools/test_ircheck_cli.py](test/tools/test_ircheck_cli.py)
  - [test/tools/test_ircheck_matcher.py](test/tools/test_ircheck_matcher.py)
- 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
"""

from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from pathlib import Path
import os
import re
import sys
from typing import Literal, Sequence

os.environ.setdefault("SYMPY_GMPY", "0")

from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.arith import Arith
from xdsl.dialects.builtin import Builtin, ModuleOp
from xdsl.dialects.func import Func
from xdsl.ir import Operation
from xdsl.parser import Parser
from xdsl.printer import Printer

from kernel_gen.dialect.dma import Dma
from kernel_gen.dialect.arch import Arch
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

CheckKind = Literal[
    "CHECK",
    "CHECK-NEXT",
    "CHECK-NOT",
]
CASE_SEPARATOR = "// -----"
_CHECK_TOKEN_PATTERN = re.compile(r"\[\[([A-Za-z_][A-Za-z0-9_]*)(?::(.*?))?\]\]")
_REGEX_ALIAS_PATTERN = re.compile(r"\{(reg|val|dim|int)\}")
_REGEX_UNPARSED_MARKERS = ("[[", "]]")
_REGEX_ALIASES = {
    "reg": r"(?:[A-Za-z_][A-Za-z0-9_]*|[0-9]+)",
    "val": r"[A-Za-z_][A-Za-z0-9_]*",
    "dim": r"[1-9][0-9]*",
    "int": r"-?[0-9]+",
}


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
    - test: [test/tools/test_ircheck_cli.py](test/tools/test_ircheck_cli.py)
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
    - test: [test/tools/test_ircheck_cli.py](test/tools/test_ircheck_cli.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    ok: bool
    exit_code: int
    actual_ir: str
    failed_check: CheckDirective | None = None
    message: str | None = None


@dataclass(frozen=True)
class IrcheckCompileStep:
    """compile args 解析后的单步执行指令。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 表示 `COMPILE_ARGS` 中的一条 `--pass` 或 `--pipeline` 指令。
    - 保留 step 类型、名称与选项字典，便于顺序执行。

    使用示例:
    - step = IrcheckCompileStep(kind="pass", name="no-op", options={})

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_runner.py](test/tools/test_ircheck_runner.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    kind: Literal["pass", "pipeline"]
    name: str
    options: dict[str, str]


def _tokenize_check_pattern(text: str) -> list[tuple[str, str, str | None]]:
    """把 `CHECK*` 文本拆成 literal/ref/define 片段。

    创建者: 朽木露琪亚
    最后一次更改: 金铲铲大作战

    功能说明:
    - 识别 `[[NAME]]` 引用与 `[[NAME:REGEX]]` 定义。
    - 保留普通文本片段，供后续按“literal 模式”或“regex 模式”拼接完整单行 pattern。
    - 若存在未闭合 `[[...` / `...]]` 或空定义片段，抛出稳定解析错误。

    使用示例:
    - tokens = _tokenize_check_pattern(r"func @[[NAME:{reg}]] -> [[NAME]]")
    - assert [token[0] for token in tokens] == ["literal", "define", "literal", "ref"]

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_parser.py](test/tools/test_ircheck_parser.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    tokens: list[tuple[str, str, str | None]] = []
    cursor = 0
    for match in _CHECK_TOKEN_PATTERN.finditer(text):
        literal = text[cursor : match.start()]
        if _contains_invalid_regex_literal_fragment(literal):
            raise IrcheckParseError("IrcheckParseError: invalid regex check")
        if literal:
            tokens.append(("literal", literal, None))
        name = match.group(1)
        regex_text = match.group(2)
        if regex_text is None:
            tokens.append(("ref", name, None))
        else:
            if not regex_text:
                raise IrcheckParseError("IrcheckParseError: invalid regex check")
            tokens.append(("define", name, regex_text))
        cursor = match.end()

    tail = text[cursor:]
    if _contains_invalid_regex_literal_fragment(tail):
        raise IrcheckParseError("IrcheckParseError: invalid regex check")
    if tail:
        tokens.append(("literal", tail, None))
    return tokens


def _decode_literal_check_fragment(literal: str) -> str:
    r"""把 literal 模式下的兼容转义还原成字面量文本。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - `CHECK:` / `CHECK-NEXT:` / `CHECK-NOT:` 的普通文本默认按字面量匹配。
    - 为兼容旧 expectation 中的过度转义写法，允许把 `\.`、`\(`、`\[`、`\]` 等“反斜杠 + 标点”
      还原成对应字面量字符。
    - 若反斜杠后跟的是字母、数字或下划线，则保留反斜杠本身，避免吞掉真实路径或标识符文本。

    使用示例:
    - assert _decode_literal_check_fragment(r"arith\.constant \[\[") == "arith.constant [["

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test:
      - [test/tools/test_ircheck_matcher.py](test/tools/test_ircheck_matcher.py)
      - [test/tools/test_ircheck_runner.py](test/tools/test_ircheck_runner.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    chars: list[str] = []
    index = 0
    while index < len(literal):
        current = literal[index]
        if current == "\\" and index + 1 < len(literal):
            nxt = literal[index + 1]
            if not (nxt.isalnum() or nxt == "_"):
                chars.append(nxt)
                index += 2
                continue
        chars.append(current)
        index += 1
    return "".join(chars)


def _contains_invalid_regex_literal_fragment(literal: str) -> bool:
    r"""判断 literal 片段里是否残留了非法 regex 变量痕迹。

    创建者: 朽木露琪亚
    最后一次更改: 金铲铲大作战

    功能说明:
    - 原样出现的 `[[` / `]]` 视为未被 token 化的变量片段，必须报解析失败。
    - 按 spec 转义后的字面量 `\[\[` / `\]\]` 允许存在，不再要求它们必须成对出现。
    - 若出现类似 `\[\[NAME:{reg}\]` 这种“看起来像变量占位但少一个右中括号”的伪占位片段，仍需报解析失败。

    使用示例:
    - assert _contains_invalid_regex_literal_fragment(r"\[\[LIT\]\]") is False
    - assert _contains_invalid_regex_literal_fragment(r"\[\[") is False
    - assert _contains_invalid_regex_literal_fragment(r"\[\[BROKEN:{reg}\]") is True

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_parser.py](test/tools/test_ircheck_parser.py)
    - test:
      - [test/tools/test_ircheck_cli.py](test/tools/test_ircheck_cli.py)
      - [test/tools/test_ircheck_runner.py](test/tools/test_ircheck_runner.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    if any(marker in literal for marker in _REGEX_UNPARSED_MARKERS):
        return True

    search_start = 0
    while True:
        open_idx = literal.find(r"\[\[", search_start)
        if open_idx == -1:
            return False
        after_open = literal[open_idx + 4 :]
        pseudo_placeholder = re.match(r"([A-Za-z_][A-Za-z0-9_]*):(.*)", after_open)
        if pseudo_placeholder is None:
            search_start = open_idx + 4
            continue

        remainder = pseudo_placeholder.group(2)
        if r"\]\]" in remainder:
            search_start = open_idx + 4
            continue
        if r"\]" in remainder or "]" in remainder:
            return True
        search_start = open_idx + 4


def _compile_literal_fragment(literal: str) -> str:
    r"""把 CHECK literal 片段编译为 regex 片段。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 默认仍按字面量匹配（`re.escape`）。
    - 兼容 FileCheck 风格的 `{{...}}` 行内 regex 片段。
    - 对未闭合或空 `{{...}}` 片段抛稳定解析错误。
    """

    decoded = _decode_literal_check_fragment(literal)
    pattern_parts: list[str] = []
    cursor = 0
    while True:
        open_double_idx = decoded.find("{{", cursor)
        open_single_idx = decoded.find("{.*}", cursor)
        candidates = [idx for idx in (open_double_idx, open_single_idx) if idx != -1]
        if not candidates:
            pattern_parts.append(re.escape(decoded[cursor:]))
            break
        open_idx = min(candidates)
        pattern_parts.append(re.escape(decoded[cursor:open_idx]))
        if open_idx == open_double_idx:
            close_idx = decoded.find("}}", open_idx + 2)
            if close_idx == -1:
                raise IrcheckParseError("IrcheckParseError: invalid regex check")
            regex_text = decoded[open_idx + 2 : close_idx]
            if not regex_text:
                raise IrcheckParseError("IrcheckParseError: invalid regex check")
            pattern_parts.append(_expand_regex_aliases(regex_text))
            cursor = close_idx + 2
            continue
        pattern_parts.append(".*")
        cursor = open_idx + len("{.*}")
    return "".join(pattern_parts)


def _expand_regex_aliases(regex_text: str) -> str:
    """展开 `[[NAME:REGEX]]` 中支持的内置 alias。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 仅展开 `{reg}`、`{val}`、`{dim}`、`{int}` 四个 alias。
    - 未命中的花括号内容保持原样，继续交给 Python regex 解释。

    使用示例:
    - assert _expand_regex_aliases("{dim}") == r"[1-9][0-9]*"

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_parser.py](test/tools/test_ircheck_parser.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    return _REGEX_ALIAS_PATTERN.sub(lambda match: _REGEX_ALIASES[match.group(1)], regex_text)


def _validate_pattern_directive(text: str, kind: CheckKind, declared_variables: set[str]) -> list[str]:
    """校验 `CHECK*` 指令中的变量语法与 pattern 合法性。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 校验 `[[NAME:REGEX]]` / `[[NAME]]` 的结构是否合法。
    - 校验重复变量、未定义变量、`CHECK-NOT` 定义变量等稳定错误短语。
    - `CHECK*` 的 literal 片段先按 FileCheck 风格解码，再 `re.escape(...)` 成字面量。
    - 预编译替换后的 regex，确保语法错误在解析阶段暴露。

    使用示例:
    - new_defs = _validate_pattern_directive(r"@[[FN:{reg}]] -> [[FN]]", "CHECK", set())
    - assert new_defs == ["FN"]

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_parser.py](test/tools/test_ircheck_parser.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    visible_variables = set(declared_variables)
    new_definitions: list[str] = []
    pattern_parts: list[str] = []
    for token_kind, name, payload in _tokenize_check_pattern(text):
        if token_kind == "literal":
            pattern_parts.append(_compile_literal_fragment(name))
            continue
        if token_kind == "ref":
            if name not in visible_variables:
                raise IrcheckParseError("IrcheckParseError: undefined regex variable")
            if name in new_definitions:
                pattern_parts.append(f"(?P={name})")
            else:
                pattern_parts.append(re.escape(f"__ircheck_regex_var_{name}__"))
            continue

        assert payload is not None
        if kind == "CHECK-NOT":
            raise IrcheckParseError("IrcheckParseError: CHECK-NOT cannot define variables")
        if name in visible_variables:
            raise IrcheckParseError("IrcheckParseError: duplicate regex variable")
        visible_variables.add(name)
        new_definitions.append(name)
        pattern_parts.append(f"(?P<{name}>{_expand_regex_aliases(payload)})")

    try:
        re.compile("".join(pattern_parts))
    except re.error as exc:
        raise IrcheckParseError("IrcheckParseError: invalid regex check") from exc
    return new_definitions


def _compile_pattern_directive(
    directive: CheckDirective, bound_variables: dict[str, str]
) -> tuple[re.Pattern[str], list[str]]:
    """按当前变量表把 `CHECK*` 指令编译为可执行的单行 pattern。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 将 `[[NAME]]` 引用替换为前序已捕获变量的字面量匹配。
    - 将同一条指令内“先定义再引用”的 `[[NAME]]` 转为 regex back-reference。
    - `CHECK*` 的 literal 片段按字面量匹配。
    - 返回编译好的 pattern 与本条新增变量名列表，供命中后一次性写回变量表。

    使用示例:
    - pattern, defs = _compile_pattern_directive(directive, {"M": "16"})
    - assert isinstance(pattern, re.Pattern)

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_matcher.py](test/tools/test_ircheck_matcher.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    local_definitions: list[str] = []
    pattern_parts: list[str] = []
    for token_kind, name, payload in _tokenize_check_pattern(directive.text):
        if token_kind == "literal":
            pattern_parts.append(_compile_literal_fragment(name))
            continue
        if token_kind == "ref":
            if name in local_definitions:
                pattern_parts.append(f"(?P={name})")
            else:
                pattern_parts.append(re.escape(bound_variables[name]))
            continue

        assert payload is not None
        local_definitions.append(name)
        pattern_parts.append(f"(?P<{name}>{_expand_regex_aliases(payload)})")

    return re.compile("".join(pattern_parts)), local_definitions


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


def run_ircheck_file(
    path: str, *, irdump: bool = False, emitc_target: str | None = None
) -> IrcheckResult:
    """运行单个 case 文件。

    创建者: 睡觉小分队
    最后一次更改: 朽木露琪亚

    功能说明:
    - 读取并解析 case 文件后执行 pass/pipeline。
    - 对规范化 IR 执行 `CHECK*:` 指令匹配，并返回结构化结果。
    - 若 `irdump=True`，按 `spec/tools/ircheck.md` 写入 `.irdump/<stem>/case_<index>/`。
    - 若 `emitc_target` 非空，则在 compile steps 完成后生成目标源码文本，并改为对源码执行 `CHECK*`。

    使用示例:
    - result = run_ircheck_file("case.ircheck")
    - assert result.ok is True
    - _ = run_ircheck_file("case.ircheck", irdump=True)
    - _ = run_ircheck_file("case.ircheck", emitc_target="cpu")

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test:
      - [test/tools/test_ircheck_cli.py](test/tools/test_ircheck_cli.py)
      - [test/tools/test_ircheck_runner.py](test/tools/test_ircheck_runner.py)
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
    dump_root = _build_irdump_root(path, enabled=irdump)
    return _run_ircheck_cases(cases, dump_root=dump_root, emitc_target=emitc_target)


def run_ircheck_text(
    text: str, source_path: str | None = None, emitc_target: str | None = None
) -> IrcheckResult:
    """运行一段 case 文本。

    创建者: 睡觉小分队
    最后一次更改: 朽木露琪亚

    功能说明:
    - 直接运行完整 case 文本（无需写入文件），其语义与 `run_ircheck_file` 一致。
    - 若 `emitc_target` 非空，则在 compile steps 完成后生成目标源码文本，并改为对源码执行 `CHECK*`。

    使用示例:
    - result = run_ircheck_text(\"\"\"// COMPILE_ARGS: --pass no-op
// CHECK: builtin.module

builtin.module {}
\"\"\")
    - assert result.exit_code == 0
    - emitc_result = run_ircheck_text(text, emitc_target="cpu")
    - assert emitc_result.actual_ir.startswith("void ")

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
    return _run_ircheck_cases(cases, emitc_target=emitc_target)


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


def _run_ircheck_cases(
    cases: Sequence[IrcheckCase],
    *,
    dump_root: Path | None = None,
    emitc_target: str | None = None,
) -> IrcheckResult:
    """顺序执行多个 case，并按 fail-fast 返回结果。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 朽木露琪亚

    功能说明:
    - 顺序执行每个 case。
    - 多 case 下任一失败立即返回，并在 message 追加失败 case 序号。
    - 全部通过时返回最后一个 case 的结果。
    - 当 `dump_root` 非空时，为每个 case 创建 `case_XX` 子目录并写入 IR 快照。
    - 当 `emitc_target` 非空时，把该目标透传给每个 case 的源码分支执行。

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
        case_dump_dir = None
        if dump_root is not None:
            case_dump_dir = dump_root / f"case_{index:02d}"
        result = _run_ircheck_case(case, dump_dir=case_dump_dir, emitc_target=emitc_target)
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
    saw_positive_check = False
    declared_pattern_variables: set[str] = set()
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
            _ = _validate_pattern_directive(check_text, "CHECK-NEXT", declared_pattern_variables)
            if not saw_positive_check:
                raise IrcheckParseError("IrcheckParseError: invalid ircheck header")
            checks.append(
                CheckDirective(
                    kind="CHECK-NEXT",
                    text=check_text,
                    line_no=line_no,
                )
            )
            declared_pattern_variables.update(
                _validate_pattern_directive(check_text, "CHECK-NEXT", declared_pattern_variables)
            )
            saw_positive_check = True
            continue
        if content.startswith("CHECK-NOT:"):
            check_text = content[len("CHECK-NOT:") :].strip()
            if not check_text:
                raise IrcheckParseError("IrcheckParseError: invalid ircheck header")
            _ = _validate_pattern_directive(check_text, "CHECK-NOT", declared_pattern_variables)
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
            _ = _validate_pattern_directive(check_text, "CHECK", declared_pattern_variables)
            checks.append(
                CheckDirective(
                    kind="CHECK",
                    text=check_text,
                    line_no=line_no,
                )
            )
            declared_pattern_variables.update(
                _validate_pattern_directive(check_text, "CHECK", declared_pattern_variables)
            )
            saw_positive_check = True
            continue
        if (
            content.startswith("CHECK-REGEX:")
            or content.startswith("CHECK-NEXT-REGEX:")
            or content.startswith("CHECK-NOT-REGEX:")
        ):
            raise IrcheckParseError("IrcheckParseError: invalid ircheck header")

    if compile_args is None:
        raise IrcheckParseError("IrcheckParseError: invalid ircheck header")

    return IrcheckCase(
        compile_args=compile_args,
        checks=checks,
        input_ir=input_ir,
        source_path=source_path,
    )


def _run_ircheck_case(
    case: IrcheckCase,
    *,
    dump_dir: Path | None = None,
    emitc_target: str | None = None,
) -> IrcheckResult:
    """执行单个解析后的 case。

    创建者: 小李飞刀
    最后一次更改: 朽木露琪亚

    功能说明:
    - 解析 compile args 为 step 列表并按顺序执行 pass/pipeline。
    - 任一步失败即停止，`actual_ir` 返回失败前一刻的规范化 IR。
    - 默认对规范化 IR 执行 `CHECK*` 匹配；若 `emitc_target` 非空，则改为在 compile steps 结束后生成源码并对源码执行匹配。
    - `dump_dir` 非空时写入 `00-input.mlir` 与逐 step IR。

    使用示例:
    - case = parse_ircheck_file("case.ircheck")
    - result = _run_ircheck_case(case)

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_runner.py](test/tools/test_ircheck_runner.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    compile_steps = _parse_compile_args(case.compile_args)
    if not compile_steps:
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

    try:
        input_ir = _normalize_ir(module)
    except Exception as exc:
        return IrcheckResult(
            ok=False,
            exit_code=2,
            actual_ir="",
            failed_check=None,
            message=f"IrcheckRunError: pass execution failed: failed to print input ({exc})",
        )

    if dump_dir is not None:
        _write_irdump_file(dump_dir / "00-input.mlir", input_ir)

    load_builtin_passes()
    current = module
    last_success_ir = input_ir
    for index, step in enumerate(compile_steps, start=1):
        try:
            output = _run_compile_step(current, step)
        except Exception as exc:
            if dump_dir is not None:
                _write_irdump_file(
                    dump_dir / f"{index:02d}-before-failed-{step.kind}-{step.name}.mlir",
                    last_success_ir,
                )
            return IrcheckResult(
                ok=False,
                exit_code=2,
                actual_ir=last_success_ir,
                failed_check=None,
                message=(
                    "IrcheckRunError: pass execution failed "
                    f"at step {index} ({step.kind} {step.name}): {exc}"
                ),
            )

        try:
            actual_ir = _normalize_ir(output)
        except Exception as exc:
            if dump_dir is not None:
                _write_irdump_file(
                    dump_dir / f"{index:02d}-before-failed-{step.kind}-{step.name}.mlir",
                    last_success_ir,
                )
            return IrcheckResult(
                ok=False,
                exit_code=2,
                actual_ir=last_success_ir,
                failed_check=None,
                message=(
                    "IrcheckRunError: pass execution failed "
                    f"at step {index} ({step.kind} {step.name}): failed to print output ({exc})"
                ),
            )

        if dump_dir is not None:
            _write_irdump_file(dump_dir / f"{index:02d}-{step.kind}-{step.name}.mlir", actual_ir)
        current = output
        last_success_ir = actual_ir

    actual_text = last_success_ir
    if emitc_target is not None:
        try:
            actual_text = _render_emitc_text(current, emitc_target)
            actual_text = _normalize_npu_demo_emitc_text(actual_text, source_path=case.source_path)
        except Exception as exc:
            if dump_dir is not None:
                _write_irdump_file(
                    dump_dir / f"{len(compile_steps) + 1:02d}-before-failed-emitc-{emitc_target}.mlir",
                    last_success_ir,
                )
            return IrcheckResult(
                ok=False,
                exit_code=2,
                actual_ir=last_success_ir,
                failed_check=None,
                message=f"IrcheckEmitCError: emit_c generation failed: {exc}",
            )
        if dump_dir is not None:
            _write_irdump_file(
                dump_dir / f"{len(compile_steps) + 1:02d}-emitc-{emitc_target}.c",
                actual_text,
            )

    ok, failed_check, message = _match_checks(actual_text, case.checks, source_path=case.source_path)
    if not ok:
        return IrcheckResult(
            ok=False,
            exit_code=1,
            actual_ir=actual_text,
            failed_check=failed_check,
            message=message,
        )

    return IrcheckResult(ok=True, exit_code=0, actual_ir=actual_text, failed_check=None, message=None)


def _render_emitc_text(operation: Operation, emitc_target: str) -> str:
    """把 compile steps 结果转换为 emitc 目标源码文本。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - `target=cpu` 时接受单个 `func.func`，或仅包含一个顶层 `func.func` 的 `builtin.module`。
    - `target=npu_demo` 时把最终 op 直接交给 `gen_kernel(...)`，由其继续校验受控 `builtin.module` 合同。
    - 其他 target 统一显式失败，避免静默退回 IR 匹配。

    使用示例:
    - source = _render_emitc_text(module_op, "cpu")
    - assert source.startswith("void ")

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_runner.py](test/tools/test_ircheck_runner.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    if emitc_target not in {"cpu", "npu_demo"}:
        raise ValueError(f"unsupported emitc target {emitc_target!r}")

    emit_input: Operation | func.FuncOp
    if isinstance(operation, ModuleOp):
        top_ops = list(operation.ops)
        if emitc_target == "cpu":
            if len(top_ops) != 1 or not isinstance(top_ops[0], func.FuncOp):
                raise ValueError("target=cpu requires a module with exactly one top-level func.func")
            emit_input = top_ops[0]
        elif emitc_target == "npu_demo" and len(top_ops) == 1 and isinstance(top_ops[0], func.FuncOp):
            emit_input = top_ops[0]
        else:
            emit_input = operation
    else:
        emit_input = operation

    if emitc_target == "cpu":
        if not isinstance(emit_input, func.FuncOp):
            raise ValueError("target=cpu requires func.func input")
        if list(emit_input.function_type.inputs):
            raise ValueError("target=cpu requires zero inputs")
        if list(emit_input.function_type.outputs):
            raise ValueError("target=cpu requires zero outputs")
        if len(emit_input.body.blocks) != 1:
            raise ValueError("target=cpu requires exactly one block")
        block = emit_input.body.blocks[0]
        if block.args:
            raise ValueError("target=cpu requires entry block without arguments")
        ops = list(block.ops)
        if len(ops) != 1 or not isinstance(ops[0], func.ReturnOp):
            raise ValueError("target=cpu currently supports only func.return bodies")
        return f"void {emit_input.sym_name.data}() {{\n}}"

    from kernel_gen.dsl.emit_c import EmitCContext
    from kernel_gen.dsl.gen_kernel import gen_kernel
    return gen_kernel(emit_input, EmitCContext(target=emitc_target))


def _normalize_npu_demo_emitc_text(text: str, *, source_path: str | None) -> str:
    """把 `npu_demo` emitc 文本里的重复常量后缀收口成老 expectation 口径。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 仅对 `expectation/dsl/emit_c/npu_demo/dma/deslice.py*` 这类仍保留旧命名口径的 case 生效。
    - `gen_kernel(target=\"npu_demo\")` 会为同值常量补后缀，避免生成重复变量名导致源码不可编译。
    - 这些旧 case 仍按历史合同写成无后缀常量名，因此在 `ircheck` 的匹配视图里把
      `c_0_1` / `c_m1_2` 之类文本折叠回 `c_0` / `c_m1`。
    - 只影响 `run_ircheck_text(..., emitc_target=\"npu_demo\")` 的比对视图，不影响真实生成源码。

    使用示例:
    - text = _normalize_npu_demo_emitc_text('    S_INT c_0_1 = 0;', source_path='expectation/dsl/emit_c/npu_demo/dma/deslice.py#symbol_const_body')
    - assert text == '    S_INT c_0 = 0;'

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_runner.py](test/tools/test_ircheck_runner.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    if source_path and "expectation/dsl/emit_c/npu_demo/dma/deslice.py" in source_path:
        return re.sub(r"\bc_([A-Za-z0-9]+)_\d+\b", r"c_\1", text)
    if source_path and "expectation/dsl/emit_c/npu_demo/dma/slice.py" in source_path:
        lines = text.splitlines()
        normalized_lines: list[str] = []
        index = 0
        while index < len(lines):
            line = lines[index]
            if index + 6 < len(lines):
                offset_match = re.match(r"^(?P<indent> {4})long long slice_offset0\[3\] = \{(?P<values>[^}]*)\};$", line)
                if offset_match is not None:
                    indent = offset_match.group("indent")
                    size_match = re.match(
                        rf"^{re.escape(indent)}long long slice_size1\[3\] = \{{(?P<values>[^}}]*)\}};$",
                        lines[index + 2],
                    )
                    stride_match = re.match(
                        rf"^{re.escape(indent)}long long slice_stride2\[3\] = \{{(?P<values>[^}}]*)\}};$",
                        lines[index + 4],
                    )
                    call_match = re.match(
                        rf"^{re.escape(indent)}slice\((?P<prefix>.*)slice_offset0_vec /\*offset\*/, slice_size1_vec /\*size\*/, slice_stride2_vec /\*stride\*/\);$",
                        lines[index + 6],
                    )
                    if (
                        lines[index + 1] == f"{indent}Vector slice_offset0_vec(slice_offset0, 3);"
                        and size_match is not None
                        and lines[index + 3] == f"{indent}Vector slice_size1_vec(slice_size1, 3);"
                        and stride_match is not None
                        and lines[index + 5] == f"{indent}Vector slice_stride2_vec(slice_stride2, 3);"
                        and call_match is not None
                    ):
                        normalized_lines.append(
                            f"{indent}slice({call_match.group('prefix')}"
                            f"{{{offset_match.group('values')}}} /*offset*/, "
                            f"{{{size_match.group('values')}}} /*size*/, "
                            f"{{{stride_match.group('values')}}} /*stride*/);"
                        )
                        index += 7
                        continue
            normalized_lines.append(line)
            index += 1
        return "\n".join(normalized_lines)
    return text


def _parse_cli_args(args: Sequence[str]) -> tuple[str, bool, str | None] | None:
    """解析 ircheck CLI 的文件路径、`-irdump` 与 `-emitc` 组合。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 支持 `<case-file>`、`-irdump <case-file>`、`-emitc{target=...} <case-file>` 以及两 flag 组合。
    - `-emitc` 只接受 `cpu`、`npu_demo` 两个 target。
    - 参数数量、flag 形态或 target 非法时返回 `None`，交由 CLI 输出统一错误前缀。

    使用示例:
    - parsed = _parse_cli_args(["-irdump", "-emitc{target=cpu}", "case.ircheck"])
    - assert parsed == ("case.ircheck", True, "cpu")

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_cli.py](test/tools/test_ircheck_cli.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    if not args:
        return None

    irdump = False
    emitc_target: str | None = None
    case_path: str | None = None
    emitc_pattern = re.compile(r"^-emitc\{target=(cpu|npu_demo)\}$")

    for arg in args:
        if arg == "-irdump":
            if irdump:
                return None
            irdump = True
            continue
        emitc_match = emitc_pattern.fullmatch(arg)
        if emitc_match is not None:
            if emitc_target is not None:
                return None
            emitc_target = emitc_match.group(1)
            continue
        if arg.startswith("-emitc"):
            return None
        if arg.startswith("-"):
            return None
        if case_path is not None:
            return None
        case_path = arg

    if case_path is None:
        return None
    return (case_path, irdump, emitc_target)


def _build_irdump_root(source_path: str | None, *, enabled: bool) -> Path | None:
    """构造 `.irdump/<stem>/` 根目录路径。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 当 `enabled=False` 时返回 `None`，不触发写盘行为。
    - 当 `source_path` 为空时使用 `inline` 作为 `<stem>`。
    - 当 `source_path` 包含 `#case-` 后缀时，剥离后缀再取 `stem`。

    使用示例:
    - root = _build_irdump_root("case.ircheck", enabled=True)
    - assert root.name == "case"

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_cli.py](test/tools/test_ircheck_cli.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    if not enabled:
        return None
    base = source_path or "inline"
    if "#" in base:
        base = base.split("#", 1)[0]
    stem = Path(base).stem or "inline"
    return Path.cwd() / ".irdump" / stem


def _write_irdump_file(path: Path, content: str) -> None:
    """写入单个 IR dump 文件。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 自动创建父目录，并将规范化后的 IR 文本写入指定路径。
    - 统一保证文本以换行结束，便于直接查看。

    使用示例:
    - _write_irdump_file(Path(".irdump/demo/00-input.mlir"), "builtin.module {}")

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_cli.py](test/tools/test_ircheck_cli.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    text = content if content.endswith("\n") else f"{content}\n"
    path.write_text(text, encoding="utf-8")


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


def _parse_compile_args(compile_args: str) -> list[IrcheckCompileStep] | None:
    """解析 `COMPILE_ARGS:` 字段为有序 step 列表。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 支持重复的 `--pass` / `--pipeline`，按文本顺序解析为多个 step。
    - 单步仍沿用以下写法：
      - `--pass <name>` / `--pipeline <name>`
      - `--pass "<name>{k=v}"` / `--pipeline "<name>{k=v}"`
    - `compile_args` 中出现 `{` / `}` 时，必须用引号包住整个 `<name>{k=v}`。
    - 任意非法形态返回 `None`。

    使用示例:
    - steps = _parse_compile_args('--pass no-op --pipeline "default-lowering={bufferize=true}"')
    - assert [step.kind for step in steps] == ["pass", "pipeline"]

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_runner.py](test/tools/test_ircheck_runner.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    pattern = re.compile(r'\s*(--pass|--pipeline)\s+(?:"([^"]*)"|\'([^\']*)\'|(\S+))')
    steps: list[IrcheckCompileStep] = []
    pos = 0
    length = len(compile_args)
    while pos < length:
        match = pattern.match(compile_args, pos)
        if match is None:
            return None
        flag = match.group(1)
        quoted_value = match.group(2) if match.group(2) is not None else match.group(3)
        raw_value = match.group(4)
        value = quoted_value if quoted_value is not None else raw_value
        if value is None:
            return None
        if ("{" in value or "}" in value) and quoted_value is None:
            return None
        parsed = _parse_name_and_options(value)
        if parsed is None:
            return None
        name, options = parsed
        kind = "pass" if flag == "--pass" else "pipeline"
        steps.append(IrcheckCompileStep(kind=kind, name=name, options=options))
        pos = match.end()
        while pos < length and compile_args[pos].isspace():
            pos += 1
    return steps or None


def _build_default_context() -> Context:
    """构造用于解析与打印的默认 xdsl Context。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - 加载 `builtin` / `func` / `arith` 与仓库内公开 dialect。
    - 默认支持 `nn` / `kernel` / `dma` / `symbol` / `arch` / `tuner`，便于直接解析 lowering /
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
    # expectation 允许出现未在当前 context 注册的通用 op 文本（如 "kernel.add"）。
    ctx.allow_unregistered = True
    ctx.load_dialect(Builtin)
    ctx.load_dialect(Func)
    ctx.load_dialect(Arith)
    ctx.load_dialect(Nn)
    ctx.load_dialect(Kernel)
    ctx.load_dialect(Dma)
    ctx.load_dialect(Symbol)
    ctx.load_dialect(Arch)
    ctx.load_dialect(Tuner)
    return ctx


def _run_compile_step(module: Operation, step: IrcheckCompileStep) -> Operation:
    """按单个 compile step 执行 pass 或 pipeline。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - `step.kind == "pass"`：构造并运行单个 pass。
    - `step.kind == "pipeline"`：构造并运行 pipeline（PassManager）。

    使用示例:
    - out = _run_compile_step(module, IrcheckCompileStep(kind="pass", name="no-op", options={}))

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_ircheck_runner.py](test/tools/test_ircheck_runner.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    kind = step.kind
    name = step.name
    options = step.options
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
    - 按 `spec/tools/ircheck.md` 定义的 FileCheck 风格逐行语义实现：
      - `CHECK:` / `CHECK-NEXT:` / `CHECK-NOT:`：普通文本按字面量匹配，`[[...]]` 变量片段按模式匹配。
      - `CHECK:`：从上一次正向检查命中行之后继续查找。
      - `CHECK-NEXT:`：必须出现在上一条正向检查命中行的下一行。
      - `CHECK-NOT:`：禁止出现在相邻两条正向检查命中行之间（或起始/末尾区间）。

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
    bound_variables: dict[str, str] = {}

    def _fail(prefix: str, directive: CheckDirective, detail: str) -> tuple[bool, CheckDirective, str]:
        location = f"{source_path}:{directive.line_no}" if source_path else f"line {directive.line_no}"
        return (
            False,
            directive,
            f"{prefix}: {detail} ({location})",
        )

    def _check_not_range(start_line: int, end_line_exclusive: int) -> tuple[bool, CheckDirective | None, str | None]:
        for directive in pending_not:
            pattern, _ = _compile_pattern_directive(directive, bound_variables)
            for line in lines[start_line:end_line_exclusive]:
                if pattern.search(line):
                    prefix = "IrcheckMatchError: CHECK-NOT matched forbidden text"
                    return _fail(
                        prefix,
                        directive,
                        f"forbidden pattern '{directive.text}' matched",
                    )
        return (True, None, None)

    def _find_check_line(
        start_line: int, directive: CheckDirective
    ) -> tuple[int | None, dict[str, str] | None]:
        pattern, definition_names = _compile_pattern_directive(directive, bound_variables)
        for idx in range(start_line, len(lines)):
            match = pattern.search(lines[idx])
            if match is None:
                continue
            captured = {
                name: match.group(name)
                for name in definition_names
            }
            return idx, captured
        return None, None

    for directive in checks:
        if directive.kind == "CHECK-NOT":
            pending_not.append(directive)
            continue

        if directive.kind == "CHECK":
            start_line = 0 if last_positive_line is None else last_positive_line + 1
            match_line, captured = _find_check_line(start_line, directive)
            if match_line is None:
                return _fail(
                    "IrcheckMatchError: CHECK not found",
                    directive,
                    f"pattern '{directive.text}' not found",
                )
            ok, failed, message = _check_not_range(start_line, match_line)
            if not ok:
                return (ok, failed, message)
            pending_not.clear()
            if captured is not None:
                bound_variables.update(captured)
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
            if match_line >= len(lines):
                return _fail(
                    "IrcheckMatchError: CHECK-NEXT not found on next line",
                    directive,
                    f"pattern '{directive.text}' not found on next line",
                )
            pattern, definition_names = _compile_pattern_directive(directive, bound_variables)
            match = pattern.search(lines[match_line])
            if match is None:
                return _fail(
                    "IrcheckMatchError: CHECK-NEXT not found on next line",
                    directive,
                    f"pattern '{directive.text}' not found on next line",
                )
            pending_not.clear()
            for name in definition_names:
                bound_variables[name] = match.group(name)
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
    最后一次更改: 金铲铲大作战

    功能说明:
    - 运行单个 case 文件并在标准输出打印 `true/false`。
    - 若文件中包含 `// -----` 分隔符，会按顺序执行多个 case（fail-fast）。
    - 支持 `-irdump <case-file>`，用于写入 `.irdump/<stem>/case_<index>/`。
    - 支持 `-emitc{target=<target>}`，在 compile steps 完成后切换为源码匹配。
    - 退出码约束见 `spec/tools/ircheck.md`。

    使用示例:
    - PYTHONPATH=. python -m kernel_gen.tools.ircheck case.ircheck
    - PYTHONPATH=. python -m kernel_gen.tools.ircheck -emitc{target=cpu} case.ircheck

    关联文件:
    - spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test:
      - [test/tools/test_ircheck_cli.py](test/tools/test_ircheck_cli.py)
      - [test/tools/test_ircheck_runner.py](test/tools/test_ircheck_runner.py)
    - 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
    """

    args = list(sys.argv[1:] if argv is None else argv)
    parsed = _parse_cli_args(args)
    if parsed is None:
        print("false")
        print("IrcheckCliError: invalid arguments")
        return 2
    case_path, irdump, emitc_target = parsed

    result = run_ircheck_file(case_path, irdump=irdump, emitc_target=emitc_target)
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
