# ircheck.md

## 文档信息

- 创建者：`睡觉小分队`
- 最后一次更改：`金铲铲大作战`
- `spec`：[`spec/tools/ircheck.md`](../../spec/tools/ircheck.md)
- `功能实现`：[`kernel_gen/tools/ircheck.py`](../../kernel_gen/tools/ircheck.py)
- `test`：
  - [`test/tools/test_ircheck_parser.py`](../../test/tools/test_ircheck_parser.py)
  - [`test/tools/test_ircheck_runner.py`](../../test/tools/test_ircheck_runner.py)
  - [`test/tools/test_ircheck_matcher.py`](../../test/tools/test_ircheck_matcher.py)
  - [`test/tools/test_ircheck_cli.py`](../../test/tools/test_ircheck_cli.py)

## 功能简介

- `ircheck` 是面向 IR 变换验证的轻量工具。
- 输入是一段 case 文本或 case 文件，流程固定为：
  - 解析 `COMPILE_ARGS`
  - 顺序执行 pass / pipeline
  - 对规范化 IR 或 emitc 源码做 `CHECK*` 匹配
- 公开稳定入口只有：
  - `parse_ircheck_file`
  - `run_ircheck_file`
  - `run_ircheck_text`

## API 列表

- `CLI：`python -m kernel_gen.tools.ircheck [-irdump] [-emitc{target=<target>}] <case-file>`
- `IrcheckParseError(message: str)`
- `IrcheckCaseBlock(text: str, start_line: int)`
- `CheckDirective(kind: CheckKind, text: str, line_no: int)`
- `IrcheckCase(compile_args: str, checks: list[CheckDirective], input_ir: str, source_path: str | None = None)`
- `IrcheckResult(ok: bool, exit_code: int, actual_ir: str, failed_check: CheckDirective | None = None, message: str | None = None)`
- `IrcheckCompileStep(kind: Literal["pass", "pipeline"], name: str, options: dict[str, str])`
- `parse_ircheck_file(path: str) -> IrcheckCase`
- `run_ircheck_file(path: str, *, irdump: bool = False, emitc_target: str | None = None) -> IrcheckResult`
- `run_ircheck_text(text: str, source_path: str | None = None, emitc_target: str | None = None) -> IrcheckResult`
- `main(argv: Sequence[str] | None = None) -> int`

## 公开 API 清单

- `CLI：python -m kernel_gen.tools.ircheck [-irdump] [-emitc{target=<target>}] <case-file>`
- `IrcheckParseError`
- `IrcheckCaseBlock`
- `CheckDirective`
- `IrcheckCase`
- `IrcheckResult`
- `IrcheckCompileStep`
- `parse_ircheck_file(path: str) -> IrcheckCase`
- `run_ircheck_file(path: str, *, irdump: bool = False, emitc_target: str | None = None) -> IrcheckResult`
- `run_ircheck_text(text: str, source_path: str | None = None, emitc_target: str | None = None) -> IrcheckResult`
- `main(argv: Sequence[str] | None = None) -> int`

## helper 清单

- `_build_default_context() -> Context`
- `_tokenize_check_pattern(text: str) -> list[tuple[str, str, str | None]]`
- `_decode_literal_check_fragment(literal: str) -> str`
- `_contains_invalid_regex_literal_fragment(literal: str) -> bool`
- `_compile_literal_fragment(literal: str) -> str`
- `_expand_regex_aliases(regex_text: str) -> str`
- `_validate_pattern_directive(text: str, kind: CheckKind, declared_variables: set[str]) -> list[str]`
- `_compile_pattern_directive(...)`
- `_split_ircheck_text_into_case_blocks(text: str) -> list[IrcheckCaseBlock]`
- `_parse_ircheck_cases(text: str, *, source_path: str | None) -> list[IrcheckCase]`
- `_run_ircheck_cases(...)`
- `_parse_ircheck_text(text: str, *, source_path: str | None, line_offset: int = 0) -> IrcheckCase`
- `_run_ircheck_case(...)`
- `_render_emitc_text(operation: Operation, emitc_target: str) -> str`
- `_is_empty_npu_demo_func(func_op: func.FuncOp) -> bool`
- `_normalize_emitc_text(text: str, *, emitc_target: str, source_path: str | None) -> str`
- `_parse_cli_args(args: Sequence[str]) -> tuple[str, bool, str | None] | None`
- `_build_irdump_root(source_path: str | None, *, enabled: bool) -> Path | None`
- `_write_irdump_file(path: Path, content: str) -> None`
- `_parse_name_and_options(value: str) -> tuple[str, dict[str, str]] | None`
- `_parse_compile_args(compile_args: str) -> list[IrcheckCompileStep] | None`
- `_run_compile_step(ctx: Context, module: Operation, step: IrcheckCompileStep) -> Operation`
- `_normalize_ir(value: Operation) -> str`
- `_match_checks(...)`

## 核心语义

- 只支持三条检查指令：
  - `CHECK:`
  - `CHECK-NEXT:`
  - `CHECK-NOT:`
- 普通文本按字面量匹配；regex 能力只允许出现在局部变量片段：
  - `[[NAME:REGEX]]`
  - `[[NAME]]`
- `CHECK-NEXT:` 不能作为第一条正向检查。
- `CHECK-NOT:` 不能定义新变量，只能引用前面已绑定的变量。
- 多 case 只支持 `// -----` 分隔，按顺序执行并在首个失败处停止。
- 传入 `emitc_target` 时，匹配对象切换为生成的源码文本；不做 IR / 源码双路径混合匹配。

## 公开接口

### CLI：`python -m kernel_gen.tools.ircheck [-irdump] [-emitc{target=<target>}] <case-file>`

- 成功退出码：`0`
- 匹配失败退出码：`1`
- 解析失败、compile args 不支持、pass/pipeline 执行失败、emitc 生成失败退出码：`2`

### `parse_ircheck_file(path: str) -> IrcheckCase`

功能说明：

- 读取单个 case 文件
- 解析 `COMPILE_ARGS`、`CHECK*` 与输入 IR
- 只处理单 case；遇到 `// -----` 必须直接失败

### `run_ircheck_file(path: str, *, irdump: bool = False, emitc_target: str | None = None) -> IrcheckResult`

功能说明：

- 执行 case 文件
- 支持单文件多 case
- 返回统一 `IrcheckResult`

### `run_ircheck_text(text: str, source_path: str | None = None, emitc_target: str | None = None) -> IrcheckResult`

功能说明：

- 直接执行 case 文本
- 语义与 `run_ircheck_file(...)` 一致

## 失败前缀

- 解析失败：
  - `IrcheckParseError: invalid ircheck header`
  - `IrcheckParseError: missing input ir`
  - `IrcheckParseError: invalid regex check`
  - `IrcheckParseError: undefined regex variable`
  - `IrcheckParseError: duplicate regex variable`
  - `IrcheckParseError: CHECK-NOT cannot define variables`
- compile args 不支持：
  - `IrcheckCompileArgsError: unsupported compile args`
- pass / pipeline 执行失败：
  - `IrcheckRunError: pass execution failed`
- emitc 生成失败：
  - `IrcheckEmitCError: emit_c generation failed`
- 匹配失败：
  - `IrcheckMatchError: CHECK not found`
  - `IrcheckMatchError: CHECK-NEXT not found on next line`
  - `IrcheckMatchError: CHECK-NOT matched forbidden text`

## 使用示例

```mlir
// COMPILE_ARGS: --pass no-op
// CHECK: builtin.module
// CHECK: func.func @main
// CHECK-NEXT: func.return

builtin.module {
  func.func @main() {
    func.return
  }
}
```

## 测试

- 解析与指令约束：[`test/tools/test_ircheck_parser.py`](../../test/tools/test_ircheck_parser.py)
- 匹配语义：[`test/tools/test_ircheck_matcher.py`](../../test/tools/test_ircheck_matcher.py)
- 执行流程：[`test/tools/test_ircheck_runner.py`](../../test/tools/test_ircheck_runner.py)
- CLI：[`test/tools/test_ircheck_cli.py`](../../test/tools/test_ircheck_cli.py)
- 执行命令：`pytest -q test/tools/test_ircheck_*.py`
