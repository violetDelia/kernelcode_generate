# ircheck.md

## 功能简介

- `ircheck` 是面向 IR 变换验证的轻量工具。
- 输入是一段 case 文本或 case 文件，流程固定为：
  - 解析 `COMPILE_ARGS`
  - 顺序执行 pass / pipeline
  - 对规范化 IR 或 emitc 源码做 `CHECK*` 匹配
- 公开稳定入口以 `API 列表` 为准，分为三类：
  - CLI 入口：`python -m kernel_gen.tools.ircheck(...)` 与 `main(...)`
  - 数据模型：`IrcheckCaseBlock`、`CheckDirective`、`IrcheckCase`、`IrcheckResult`、`IrcheckCompileStep`
  - 函数入口：`parse_ircheck_file(...)`、`run_ircheck_file(...)`、`run_ircheck_text(...)`

## API 列表

- `python -m kernel_gen.tools.ircheck(argv: Sequence[str]) -> int`
- `class IrcheckCaseBlock(text: str, start_line: int)`
- `class CheckDirective(kind: CheckKind, text: str, line_no: int)`
- `class IrcheckCase(compile_args: str, checks: list[CheckDirective], input_ir: str, source_path: str | None = None)`
- `class IrcheckResult(ok: bool, exit_code: int, actual_ir: str, failed_check: CheckDirective | None = None, message: str | None = None)`
- `class IrcheckCompileStep(kind: Literal["pass", "pipeline"], name: str, options: dict[str, str])`
- `parse_ircheck_file(path: str) -> IrcheckCase`
- `run_ircheck_file(path: str, *, irdump: bool = False, emitc_target: str | None = None) -> IrcheckResult`
- `run_ircheck_text(text: str, source_path: str | None = None, emitc_target: str | None = None) -> IrcheckResult`
- `main(argv: Sequence[str] | None = None) -> int`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/tools/ircheck.md`](../../spec/tools/ircheck.md)
- `功能实现`：[`kernel_gen/tools/ircheck.py`](../../kernel_gen/tools/ircheck.py)
- `test`：
  - [`test/tools/test_ircheck_parser.py`](../../test/tools/test_ircheck_parser.py)
  - [`test/tools/test_ircheck_runner.py`](../../test/tools/test_ircheck_runner.py)
  - [`test/tools/test_ircheck_matcher.py`](../../test/tools/test_ircheck_matcher.py)
  - [`test/tools/test_ircheck_cli.py`](../../test/tools/test_ircheck_cli.py)

## 依赖

- 无额外 spec 依赖。

## 额外补充

### helper 边界

- `_build_default_context(...)`、`_parse_ircheck_cases(...)`、`_run_ircheck_case(...)`、`_normalize_ir(...)`、`_match_checks(...)` 等下划线 helper 只服务当前文件内部实现。
- 实现、测试和外部调用方不得跨文件导入或断言这些 helper；公开行为只能通过 `API 列表` 中列出的 CLI、数据模型和函数观察。

## API详细说明

### `python -m kernel_gen.tools.ircheck(argv: Sequence[str]) -> int`

- api：`python -m kernel_gen.tools.ircheck(argv: Sequence[str]) -> int`
- 参数：
  - `irdump`：CLI 布尔开关，控制是否输出 IR dump 诊断信息；类型 `CLI flag`；默认值 `False`；不允许 `None` 或空值作为稳定输入；按只读命令行参数消费；非法组合必须触发稳定错误；输出 `.mlir` 诊断文件时默认使用 `kernel_gen.core.print.print_operation_with_aliases(...)` 的 alias IR。
  - `emitc_target`：EmitC 目标名称，用于选择 `-emitc{target=<target>}` 的输出后端；类型 `str | None`；默认值 `None`；仅默认值允许空目标；按只读命令行参数消费；未知 target 必须触发稳定错误。
  - `case_file`：待检查的 case 文件路径，提供 `ircheck` 读取和验证的输入资产；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空路径；按只读路径参数消费；路径不存在或内容非法必须触发稳定错误。
- 返回值：进程退出码；`0` 表示成功，`1` 表示匹配失败，`2` 表示解析、compile args、pass/pipeline 或 emitc 生成失败。
- 使用示例：

  ```python
  import subprocess

  completed = subprocess.run(
      ["python", "-m", "kernel_gen.tools.ircheck", "<case-file>"],
      check=False,
  )
  ```
- 功能说明：执行 `ircheck` CLI，对 case 文件运行 pass/pipeline 并检查规范化 IR 或 emitc 源码。
- 注意事项：
  - `--help` 或 `-h` 单独出现时必须输出帮助文本并返回 `0`；帮助输出不得以 `true` / `false` 开头。
  - 只支持 `CHECK:`、`CHECK-NEXT:`、`CHECK-NOT:` 三条检查指令。
  - 普通文本按字面量匹配；regex 能力只允许出现在局部变量片段 `[[NAME:REGEX]]` 和引用片段 `[[NAME]]`。
  - `CHECK-NEXT:` 不能作为第一条正向检查。
  - `CHECK-NOT:` 不能定义新变量，只能引用前面已绑定的变量。
  - 多 case 只支持 `// -----` 分隔，按顺序执行并在首个失败处停止。
  - 传入 `emitc_target` 时，匹配对象切换为生成的源码文本；不做 IR / 源码双路径混合匹配。
  - 解析失败固定前缀包括 `IrcheckParseError: invalid ircheck header`、`IrcheckParseError: missing input ir`、`IrcheckParseError: invalid regex check`、`IrcheckParseError: undefined regex variable`、`IrcheckParseError: duplicate regex variable`、`IrcheckParseError: CHECK-NOT cannot define variables`。
  - compile args 不支持固定前缀为 `IrcheckCompileArgsError: unsupported compile args`。
  - pass / pipeline 执行失败固定前缀为 `IrcheckRunError: pass execution failed`。
  - emitc 生成失败固定前缀为 `IrcheckEmitCError: emit_c generation failed`。
  - 匹配失败固定前缀包括 `IrcheckMatchError: CHECK not found`、`IrcheckMatchError: CHECK-NEXT not found on next line`、`IrcheckMatchError: CHECK-NOT matched forbidden text`。
  - 命令行失败通过退出码和公开错误文本表达；调用方不得依赖临时文件、锁文件或内部日志格式。

### `class IrcheckCaseBlock(text: str, start_line: int)`

- api：`class IrcheckCaseBlock(text: str, start_line: int)`
- 参数：
  - `text`：输入文本或待解析文本；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `start_line`：`start_line` 输入值，参与 `IrcheckCaseBlock` 的公开处理流程；类型 `int`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`IrcheckCaseBlock` 实例。
- 使用示例：

  ```python
  ircheck_case_block = IrcheckCaseBlock(text=text, start_line=start_line)
  ```
- 功能说明：构造 `IrcheckCaseBlock` 实例。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `class CheckDirective(kind: CheckKind, text: str, line_no: int)`

- api：`class CheckDirective(kind: CheckKind, text: str, line_no: int)`
- 参数：
  - `kind`：类别标识，指定当前接口处理的 pass、cost、target、节点或输出种类；类型 `CheckKind`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `text`：输入文本或待解析文本；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `line_no`：`line_no` 输入值，参与 `CheckDirective` 的公开处理流程；类型 `int`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`CheckDirective` 实例。
- 使用示例：

  ```python
  check_directive = CheckDirective(kind=kind, text=text, line_no=line_no)
  ```
- 功能说明：构造 `CheckDirective` 实例。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `class IrcheckCase(compile_args: str, checks: list[CheckDirective], input_ir: str, source_path: str | None = None)`

- api：`class IrcheckCase(compile_args: str, checks: list[CheckDirective], input_ir: str, source_path: str | None = None)`
- 参数：
  - `compile_args`：`compile_args` 输入值，参与 `IrcheckCase` 的公开处理流程；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `checks`：检查项集合，定义当前接口需要执行的校验规则；类型 `list[CheckDirective]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按可变容器传入时，是否修改输入必须以本接口功能说明和注意事项为准；非法值按该 API 的公开错误语义处理。
  - `input_ir`：`input_ir` 输入值，参与 `IrcheckCase` 的公开处理流程；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `source_path`：文件或目录路径；类型 `str | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`IrcheckCase` 实例。
- 使用示例：

  ```python
  ircheck_case = IrcheckCase(compile_args=compile_args, checks=checks, input_ir=input_ir, source_path=None)
  ```
- 功能说明：构造 `IrcheckCase` 实例。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `class IrcheckResult(ok: bool, exit_code: int, actual_ir: str, failed_check: CheckDirective | None = None, message: str | None = None)`

- api：`class IrcheckResult(ok: bool, exit_code: int, actual_ir: str, failed_check: CheckDirective | None = None, message: str | None = None)`
- 参数：
  - `ok`：`ok` 输入值，参与 `IrcheckResult` 的公开处理流程；类型 `bool`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `exit_code`：`exit_code` 输入值，参与 `IrcheckResult` 的公开处理流程；类型 `int`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `actual_ir`：`actual_ir` 输入值，参与 `IrcheckResult` 的公开处理流程；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `failed_check`：`failed_check` 输入值，参与 `IrcheckResult` 的公开处理流程；类型 `CheckDirective | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `message`：诊断或错误消息文本，用于构造稳定错误或校验输出；类型 `str | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`bool`，表示判断结果。
- 使用示例：

  ```python
  ircheck_result = IrcheckResult(ok=ok, exit_code=exit_code, actual_ir=actual_ir, failed_check=None, message=None)
  ```
- 功能说明：构造 `IrcheckResult` 实例。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `class IrcheckCompileStep(kind: Literal["pass", "pipeline"], name: str, options: dict[str, str])`

- api：`class IrcheckCompileStep(kind: Literal["pass", "pipeline"], name: str, options: dict[str, str])`
- 参数：
  - `kind`：类别标识，指定当前接口处理的 pass、cost、target、节点或输出种类；类型 `Literal["pass", "pipeline"]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `name`：公开名称、符号名或注册名，用于查找、打印、注册或生成稳定标识；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `options`：IR operation；类型 `dict[str, str]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按可变容器传入时，是否修改输入必须以本接口功能说明和注意事项为准；非法值按该 API 的公开错误语义处理。
- 返回值：`IrcheckCompileStep` 实例。
- 使用示例：

  ```python
  ircheck_compile_step = IrcheckCompileStep(kind=kind, name=name, options=options)
  ```
- 功能说明：构造 `IrcheckCompileStep` 实例。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `parse_ircheck_file(path: str) -> IrcheckCase`

- api：`parse_ircheck_file(path: str) -> IrcheckCase`
- 参数：
  - `path`：文件或目录路径，指定读取、写入、加载或诊断产物的位置；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`IrcheckCase`。
- 使用示例：

  ```python
  result = parse_ircheck_file(path=path)
  ```
- 功能说明：解析 `ircheck_file`。
- 注意事项：
  - 只解析 case 文件并返回 `IrcheckCase`，不执行 pass、pipeline 或 check 匹配。
  - 文件头、输入 IR、regex 片段或变量引用非法时必须通过 `IrcheckParseError: ...` 固定前缀表达。
  - 调用方不得依赖未列入 API 的 parser helper、临时缓存或内部诊断对象。

### `run_ircheck_file(path: str, *, irdump: bool = False, emitc_target: str | None = None) -> IrcheckResult`

- api：`run_ircheck_file(path: str, *, irdump: bool = False, emitc_target: str | None = None) -> IrcheckResult`
- 参数：
  - `path`：文件或目录路径，指定读取、写入、加载或诊断产物的位置；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `irdump`：`irdump` 输入值，参与 `run_ircheck_file` 的公开处理流程；类型 `bool`；默认值 `False`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理；为 `True` 时写出的 `.mlir` dump 默认是 alias IR。
  - `emitc_target`：目标后端名称或目标配置；类型 `str | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`IrcheckResult`。
- 使用示例：

  ```python
  result = run_ircheck_file(path=path, irdump=False, emitc_target=None)
  ```
- 功能说明：运行 `ircheck_file`。
- 注意事项：
  - `irdump=True` 时允许输出 alias IR dump 诊断文件；`irdump=False` 时不承诺写入诊断产物。
  - CHECK 匹配仍使用 `run_ircheck_file(...)` 的规范化实际 IR，不因 `-irdump` 诊断 alias 文本改变。
  - `emitc_target` 非空时匹配对象切换为生成的源码文本；不做 IR / 源码双路径混合匹配。
  - compile args 不支持时返回 `IrcheckResult(ok=False, exit_code=2, ...)`，消息必须使用 `IrcheckCompileArgsError: unsupported compile args` 前缀。
  - pass / pipeline 执行失败时返回 `exit_code=2`，消息必须使用 `IrcheckRunError: pass execution failed` 前缀。
  - emitc 生成失败时返回 `exit_code=2`，消息必须使用 `IrcheckEmitCError: emit_c generation failed` 前缀。
  - 匹配失败时返回 `exit_code=1`，消息必须使用 `IrcheckMatchError: ...` 前缀。

### `run_ircheck_text(text: str, source_path: str | None = None, emitc_target: str | None = None) -> IrcheckResult`

- api：`run_ircheck_text(text: str, source_path: str | None = None, emitc_target: str | None = None) -> IrcheckResult`
- 参数：
  - `text`：输入文本或待解析文本；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `source_path`：文件或目录路径；类型 `str | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `emitc_target`：目标后端名称或目标配置；类型 `str | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`IrcheckResult`。
- 使用示例：

  ```python
  result = run_ircheck_text(text=text, source_path=None, emitc_target=None)
  ```
- 功能说明：运行 `ircheck_text`。
- 注意事项：
  - `text` 使用与文件入口相同的 `COMPILE_ARGS`、`CHECK:`、`CHECK-NEXT:`、`CHECK-NOT:` 语义。
  - `source_path` 只作为诊断来源标识，不改变解析或匹配规则。
  - 解析失败、compile args 不支持、pass/pipeline 执行失败、emitc 生成失败和匹配失败的固定前缀必须与 `run_ircheck_file(...)` 一致。

### `main(argv: Sequence[str] | None = None) -> int`

- api：`main(argv: Sequence[str] | None = None) -> int`
- 参数：
  - `argv`：`argv` 输入值，参与 `main` 的公开处理流程；类型 `Sequence[str] | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`int`，表示计数、维度或状态值。
- 使用示例：

  ```python
  result = main(argv=None)
  ```
- 功能说明：执行 `main`。
- 注意事项：
  - `argv=None` 表示读取进程命令行参数。
  - `argv=["--help"]` 与 `argv=["-h"]` 表示帮助入口，必须输出 usage 帮助文本并返回 `0`。
  - 返回码必须与 CLI API 一致：成功 `0`，匹配失败 `1`，解析、compile args、pass/pipeline 或 emitc 生成失败 `2`。
  - 非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

## 测试

- 测试文件：
  - `test/tools/test_ircheck_cli.py`
  - `test/tools/test_ircheck_matcher.py`
  - `test/tools/test_ircheck_parser.py`
  - `test/tools/test_ircheck_runner.py`
- 执行命令：`pytest -q test/tools/test_ircheck_*.py`

### 测试目标

- 验证 `tools/ircheck` 的公开 API、边界与错误语义。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-TOOLS-IRCHECK-001 | 边界/异常 | ircheck cli match failure outputs actual IR | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_ircheck_cli_match_failure_outputs_actual_ir`。 | “ircheck cli match failure outputs actual IR”场景按公开错误语义失败或被拒绝。 | `test_ircheck_cli_match_failure_outputs_actual_ir` |
| TC-TOOLS-IRCHECK-002 | 公开入口 | ircheck cli multi case success | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_ircheck_cli_multi_case_success`。 | 公开入口在“ircheck cli multi case success”场景下可导入、构造、注册或按名称发现。 | `test_ircheck_cli_multi_case_success` |
| TC-TOOLS-IRCHECK-003 | 公开入口 | ircheck cli irdump creates alias files | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_ircheck_cli_irdump_creates_files`。 | `-irdump` 写出逐 step `.mlir` 文件，dump IR 正文使用 alias IR，CHECK 匹配文本保持公开规范化 IR。 | `test_ircheck_cli_irdump_creates_files` |
| TC-TOOLS-IRCHECK-004 | 生成/编译 | ircheck cli emitc cpu success | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_ircheck_cli_emitc_cpu_success`。 | 生成源码、IR 文本或编译结果体现“ircheck cli emitc cpu success”场景。 | `test_ircheck_cli_emitc_cpu_success` |
| TC-TOOLS-IRCHECK-005 | 边界/异常 | ircheck cli invalid emitc arguments | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_ircheck_cli_invalid_emitc_arguments`。 | “ircheck cli invalid emitc arguments”场景按公开错误语义失败或被拒绝。 | `test_ircheck_cli_invalid_emitc_arguments` |
| TC-TOOLS-IRCHECK-006 | 边界/异常 | ircheck cli emitc missing target rejected | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_ircheck_cli_emitc_missing_target_rejected`。 | “ircheck cli emitc missing target rejected”场景按公开错误语义失败或被拒绝。 | `test_ircheck_cli_emitc_missing_target_rejected` |
| TC-TOOLS-IRCHECK-007 | 边界/异常 | ircheck cli emitc npu demo failure outputs actual IR | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_ircheck_cli_emitc_npu_demo_failure_outputs_actual_ir`。 | “ircheck cli emitc npu demo failure outputs actual IR”场景按公开错误语义失败或被拒绝。 | `test_ircheck_cli_emitc_npu_demo_failure_outputs_actual_ir` |
| TC-TOOLS-IRCHECK-008 | 生成/编译 | ircheck cli irdump emitc cpu creates files | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_ircheck_cli_irdump_emitc_cpu_creates_files`。 | 生成源码、IR 文本或编译结果体现“ircheck cli irdump emitc cpu creates files”场景。 | `test_ircheck_cli_irdump_emitc_cpu_creates_files` |
| TC-TOOLS-IRCHECK-009 | 边界/异常 | run ircheck text reports sequential check search failure | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_reports_sequential_check_search_failure`。 | “run ircheck text reports sequential check search failure”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_reports_sequential_check_search_failure` |
| TC-TOOLS-IRCHECK-010 | 边界/异常 | run ircheck text reports check next failure | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_reports_check_next_failure`。 | “run ircheck text reports check next failure”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_reports_check_next_failure` |
| TC-TOOLS-IRCHECK-011 | 边界/异常 | run ircheck text reports check not between positives failure | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_reports_check_not_between_positives_failure`。 | “run ircheck text reports check not between positives failure”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_reports_check_not_between_positives_failure` |
| TC-TOOLS-IRCHECK-012 | 边界/异常 | run ircheck text reports check not before first positive failure | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_reports_check_not_before_first_positive_failure`。 | “run ircheck text reports check not before first positive failure”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_reports_check_not_before_first_positive_failure` |
| TC-TOOLS-IRCHECK-013 | 边界/异常 | run ircheck text reports check not after last positive failure | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_reports_check_not_after_last_positive_failure`。 | “run ircheck text reports check not after last positive failure”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_reports_check_not_after_last_positive_failure` |
| TC-TOOLS-IRCHECK-014 | 执行结果 | run ircheck text supports variable capture and reuse | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_run_ircheck_text_supports_variable_capture_and_reuse`。 | 命令返回码、输出、执行结果或状态变更体现“run ircheck text supports variable capture and reuse”场景。 | `test_run_ircheck_text_supports_variable_capture_and_reuse` |
| TC-TOOLS-IRCHECK-015 | 解析/打印 | parse ircheck file basic | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_parse_ircheck_file_basic`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_parse_ircheck_file_basic` |
| TC-TOOLS-IRCHECK-016 | 边界/异常 | parse ircheck file missing compile args fails | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_parse_ircheck_file_missing_compile_args_fails`。 | “parse ircheck file missing compile args fails”场景按公开错误语义失败或被拒绝。 | `test_parse_ircheck_file_missing_compile_args_fails` |
| TC-TOOLS-IRCHECK-017 | 边界/异常 | parse ircheck file duplicate compile args fails | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_parse_ircheck_file_duplicate_compile_args_fails`。 | “parse ircheck file duplicate compile args fails”场景按公开错误语义失败或被拒绝。 | `test_parse_ircheck_file_duplicate_compile_args_fails` |
| TC-TOOLS-IRCHECK-018 | 边界/异常 | parse ircheck file missing input IR fails | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_parse_ircheck_file_missing_input_ir_fails`。 | “parse ircheck file missing input IR fails”场景按公开错误语义失败或被拒绝。 | `test_parse_ircheck_file_missing_input_ir_fails` |
| TC-TOOLS-IRCHECK-019 | 边界/异常 | parse ircheck file empty compile args fails | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_parse_ircheck_file_empty_compile_args_fails`。 | “parse ircheck file empty compile args fails”场景按公开错误语义失败或被拒绝。 | `test_parse_ircheck_file_empty_compile_args_fails` |
| TC-TOOLS-IRCHECK-020 | 边界/异常 | parse ircheck file empty check text fails | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_parse_ircheck_file_empty_check_text_fails`。 | “parse ircheck file empty check text fails”场景按公开错误语义失败或被拒绝。 | `test_parse_ircheck_file_empty_check_text_fails` |
| TC-TOOLS-IRCHECK-021 | 边界/异常 | parse ircheck file check next first positive fails | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_parse_ircheck_file_check_next_first_positive_fails`。 | “parse ircheck file check next first positive fails”场景按公开错误语义失败或被拒绝。 | `test_parse_ircheck_file_check_next_first_positive_fails` |
| TC-TOOLS-IRCHECK-022 | 边界/异常 | parse ircheck file legacy regex directives fail | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_parse_ircheck_file_legacy_regex_directives_fail`。 | “parse ircheck file legacy regex directives fail”场景按公开错误语义失败或被拒绝。 | `test_parse_ircheck_file_legacy_regex_directives_fail` |
| TC-TOOLS-IRCHECK-023 | 边界/异常 | parse ircheck file rejects multi case separator | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_parse_ircheck_file_rejects_multi_case_separator`。 | “parse ircheck file rejects multi case separator”场景按公开错误语义失败或被拒绝。 | `test_parse_ircheck_file_rejects_multi_case_separator` |
| TC-TOOLS-IRCHECK-024 | 解析/打印 | parse ircheck file variable directives | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_parse_ircheck_file_variable_directives`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_parse_ircheck_file_variable_directives` |
| TC-TOOLS-IRCHECK-025 | 边界/异常 | parse ircheck file invalid variable regex fails | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_parse_ircheck_file_invalid_variable_regex_fails`。 | “parse ircheck file invalid variable regex fails”场景按公开错误语义失败或被拒绝。 | `test_parse_ircheck_file_invalid_variable_regex_fails` |
| TC-TOOLS-IRCHECK-026 | 边界/异常 | parse ircheck file unclosed escaped variable fails | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_parse_ircheck_file_unclosed_escaped_variable_fails`。 | “parse ircheck file unclosed escaped variable fails”场景按公开错误语义失败或被拒绝。 | `test_parse_ircheck_file_unclosed_escaped_variable_fails` |
| TC-TOOLS-IRCHECK-027 | 解析/打印 | parse ircheck file escaped double brackets literal ok | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_parse_ircheck_file_escaped_double_brackets_literal_ok`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_parse_ircheck_file_escaped_double_brackets_literal_ok` |
| TC-TOOLS-IRCHECK-028 | 解析/打印 | parse ircheck file escaped double open brackets prefix ok | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_parse_ircheck_file_escaped_double_open_brackets_prefix_ok`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_parse_ircheck_file_escaped_double_open_brackets_prefix_ok` |
| TC-TOOLS-IRCHECK-029 | 边界/异常 | parse ircheck file undefined variable fails | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_parse_ircheck_file_undefined_variable_fails`。 | “parse ircheck file undefined variable fails”场景按公开错误语义失败或被拒绝。 | `test_parse_ircheck_file_undefined_variable_fails` |
| TC-TOOLS-IRCHECK-030 | 边界/异常 | parse ircheck file duplicate or not variable fails | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_parse_ircheck_file_duplicate_or_not_variable_fails`。 | “parse ircheck file duplicate or not variable fails”场景按公开错误语义失败或被拒绝。 | `test_parse_ircheck_file_duplicate_or_not_variable_fails` |
| TC-TOOLS-IRCHECK-031 | 边界/异常 | run ircheck text multi case failure reports case suffix | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_multi_case_failure_reports_case_suffix`。 | “run ircheck text multi case failure reports case suffix”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_multi_case_failure_reports_case_suffix` |
| TC-TOOLS-IRCHECK-032 | 边界/异常 | run ircheck text separator only maps to parse error | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_separator_only_maps_to_parse_error`。 | “run ircheck text separator only maps to parse error”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_separator_only_maps_to_parse_error` |
| TC-TOOLS-IRCHECK-033 | 边界/异常 | run ircheck file missing file maps to parse error | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_file_missing_file_maps_to_parse_error`。 | “run ircheck file missing file maps to parse error”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_file_missing_file_maps_to_parse_error` |
| TC-TOOLS-IRCHECK-034 | pass 改写 | run ircheck text pass ok | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_run_ircheck_text_pass_ok`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“run ircheck text pass ok”场景。 | `test_run_ircheck_text_pass_ok` |
| TC-TOOLS-IRCHECK-035 | pass 改写 | run ircheck text module pass ok | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_run_ircheck_text_module_pass_ok`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“run ircheck text module pass ok”场景。 | `test_run_ircheck_text_module_pass_ok` |
| TC-TOOLS-IRCHECK-036 | pass 改写 | run ircheck text pass ok with arch dialect | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_run_ircheck_text_pass_ok_with_arch_dialect`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“run ircheck text pass ok with arch dialect”场景。 | `test_run_ircheck_text_pass_ok_with_arch_dialect` |
| TC-TOOLS-IRCHECK-037 | 生成/编译 | run ircheck text unsupported compile args | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_run_ircheck_text_unsupported_compile_args`。 | 生成源码、IR 文本或编译结果体现“run ircheck text unsupported compile args”场景。 | `test_run_ircheck_text_unsupported_compile_args` |
| TC-TOOLS-IRCHECK-038 | 边界/异常 | run ircheck text parse error maps to exit code 2 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_parse_error_maps_to_exit_code_2`。 | “run ircheck text parse error maps to exit code 2”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_parse_error_maps_to_exit_code_2` |
| TC-TOOLS-IRCHECK-039 | 执行结果 | run ircheck text check not found | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_run_ircheck_text_check_not_found`。 | 命令返回码、输出、执行结果或状态变更体现“run ircheck text check not found”场景。 | `test_run_ircheck_text_check_not_found` |
| TC-TOOLS-IRCHECK-040 | 边界/异常 | run ircheck text check next failure | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_check_next_failure`。 | “run ircheck text check next failure”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_check_next_failure` |
| TC-TOOLS-IRCHECK-041 | 生成/编译 | run ircheck text emitc npu demo single symbol func | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_run_ircheck_text_emitc_npu_demo_single_symbol_func`。 | 生成源码、IR 文本或编译结果体现“run ircheck text emitc npu demo single symbol func”场景。 | `test_run_ircheck_text_emitc_npu_demo_single_symbol_func` |
| TC-TOOLS-IRCHECK-042 | 边界/异常 | run ircheck text check not failure between positives | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_check_not_failure_between_positives`。 | “run ircheck text check not failure between positives”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_check_not_failure_between_positives` |
| TC-TOOLS-IRCHECK-043 | pass 改写 | run ircheck text pass with options | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_run_ircheck_text_pass_with_options`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“run ircheck text pass with options”场景。 | `test_run_ircheck_text_pass_with_options` |
| TC-TOOLS-IRCHECK-044 | 边界/异常 | run ircheck text unquoted options rejected | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_unquoted_options_rejected`。 | “run ircheck text unquoted options rejected”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_unquoted_options_rejected` |
| TC-TOOLS-IRCHECK-045 | 生成/编译 | run ircheck text emitc cpu success | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_run_ircheck_text_emitc_cpu_success`。 | 生成源码、IR 文本或编译结果体现“run ircheck text emitc cpu success”场景。 | `test_run_ircheck_text_emitc_cpu_success` |
| TC-TOOLS-IRCHECK-046 | 边界/异常 | run ircheck text emitc npu demo failure keeps IR | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_emitc_npu_demo_failure_keeps_ir`。 | “run ircheck text emitc npu demo failure keeps IR”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_emitc_npu_demo_failure_keeps_ir` |
| TC-TOOLS-IRCHECK-047 | 生成/编译 | run ircheck text emitc npu demo plain DMA alloc success | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_run_ircheck_text_emitc_npu_demo_plain_dma_alloc_success`。 | 生成源码、IR 文本或编译结果体现“run ircheck text emitc npu demo plain DMA alloc success”场景。 | `test_run_ircheck_text_emitc_npu_demo_plain_dma_alloc_success` |
| TC-TOOLS-IRCHECK-048 | 边界/异常 | run ircheck text emitc invalid target | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_emitc_invalid_target`。 | “run ircheck text emitc invalid target”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_emitc_invalid_target` |
| TC-TOOLS-IRCHECK-049 | 边界/异常 | run ircheck text invalid options syntax | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_invalid_options_syntax`。 | “run ircheck text invalid options syntax”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_invalid_options_syntax` |
| TC-TOOLS-IRCHECK-050 | pass 改写 | run ircheck text pipeline with options | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_run_ircheck_text_pipeline_with_options`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“run ircheck text pipeline with options”场景。 | `test_run_ircheck_text_pipeline_with_options` |
| TC-TOOLS-IRCHECK-051 | pass 改写 | run ircheck text pipeline ok | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_run_ircheck_text_pipeline_ok`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“run ircheck text pipeline ok”场景。 | `test_run_ircheck_text_pipeline_ok` |
| TC-TOOLS-IRCHECK-052 | 执行结果 | run ircheck text multi case ok | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_run_ircheck_text_multi_case_ok`。 | 命令返回码、输出、执行结果或状态变更体现“run ircheck text multi case ok”场景。 | `test_run_ircheck_text_multi_case_ok` |
| TC-TOOLS-IRCHECK-053 | 边界/异常 | run ircheck text multi case failfast marks case index | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_multi_case_failfast_marks_case_index`。 | “run ircheck text multi case failfast marks case index”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_multi_case_failfast_marks_case_index` |
| TC-TOOLS-IRCHECK-054 | pass 改写 | run ircheck text pass with options ok | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_run_ircheck_text_pass_with_options_ok`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“run ircheck text pass with options ok”场景。 | `test_run_ircheck_text_pass_with_options_ok` |
| TC-TOOLS-IRCHECK-055 | pass 改写 | run ircheck text pipeline with options ok | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_run_ircheck_text_pipeline_with_options_ok`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“run ircheck text pipeline with options ok”场景。 | `test_run_ircheck_text_pipeline_with_options_ok` |
| TC-TOOLS-IRCHECK-056 | 边界/异常 | run ircheck text rejects invalid option syntax | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_rejects_invalid_option_syntax`。 | “run ircheck text rejects invalid option syntax”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_rejects_invalid_option_syntax` |
| TC-TOOLS-IRCHECK-057 | 边界/异常 | run ircheck text rejects unquoted pass options | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_rejects_unquoted_pass_options`。 | “run ircheck text rejects unquoted pass options”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_rejects_unquoted_pass_options` |
| TC-TOOLS-IRCHECK-058 | 边界/异常 | run ircheck text rejects unquoted pipeline options | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_rejects_unquoted_pipeline_options`。 | “run ircheck text rejects unquoted pipeline options”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_rejects_unquoted_pipeline_options` |
| TC-TOOLS-IRCHECK-059 | pass 改写 | run ircheck text multi pass sequence | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_run_ircheck_text_multi_pass_sequence`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“run ircheck text multi pass sequence”场景。 | `test_run_ircheck_text_multi_pass_sequence` |
| TC-TOOLS-IRCHECK-060 | 边界/异常 | run ircheck text failing step reports actual IR | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_failing_step_reports_actual_ir`。 | “run ircheck text failing step reports actual IR”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_failing_step_reports_actual_ir` |
| TC-TOOLS-IRCHECK-061 | 执行结果 | run ircheck text variable success | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_run_ircheck_text_variable_success`。 | 命令返回码、输出、执行结果或状态变更体现“run ircheck text variable success”场景。 | `test_run_ircheck_text_variable_success` |
| TC-TOOLS-IRCHECK-062 | 边界/异常 | run ircheck text invalid variable regex maps to exit code 2 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_invalid_variable_regex_maps_to_exit_code_2`。 | “run ircheck text invalid variable regex maps to exit code 2”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_invalid_variable_regex_maps_to_exit_code_2` |
| TC-TOOLS-IRCHECK-063 | 执行结果 | run ircheck text unclosed escaped variable maps to exit code 2 | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_run_ircheck_text_unclosed_escaped_variable_maps_to_exit_code_2`。 | 命令返回码、输出、执行结果或状态变更体现“run ircheck text unclosed escaped variable maps to exit code 2”场景。 | `test_run_ircheck_text_unclosed_escaped_variable_maps_to_exit_code_2` |
| TC-TOOLS-IRCHECK-064 | 执行结果 | run ircheck text escaped double brackets literal ok | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_run_ircheck_text_escaped_double_brackets_literal_ok`。 | 命令返回码、输出、执行结果或状态变更体现“run ircheck text escaped double brackets literal ok”场景。 | `test_run_ircheck_text_escaped_double_brackets_literal_ok` |
| TC-TOOLS-IRCHECK-065 | 执行结果 | run ircheck text escaped double open brackets prefix ok | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_run_ircheck_text_escaped_double_open_brackets_prefix_ok`。 | 命令返回码、输出、执行结果或状态变更体现“run ircheck text escaped double open brackets prefix ok”场景。 | `test_run_ircheck_text_escaped_double_open_brackets_prefix_ok` |
| TC-TOOLS-IRCHECK-066 | 执行结果 | run ircheck text check not define variable maps to exit code 2 | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_run_ircheck_text_check_not_define_variable_maps_to_exit_code_2`。 | 命令返回码、输出、执行结果或状态变更体现“run ircheck text check not define variable maps to exit code 2”场景。 | `test_run_ircheck_text_check_not_define_variable_maps_to_exit_code_2` |
| TC-TOOLS-IRCHECK-067 | 执行结果 | run ircheck text variables are case local | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_run_ircheck_text_variables_are_case_local`。 | 命令返回码、输出、执行结果或状态变更体现“run ircheck text variables are case local”场景。 | `test_run_ircheck_text_variables_are_case_local` |
| TC-TOOLS-IRCHECK-068 | 执行结果 | run ircheck text reg alias matches ssa ids | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_run_ircheck_text_reg_alias_matches_ssa_ids`。 | 命令返回码、输出、执行结果或状态变更体现“run ircheck text reg alias matches ssa ids”场景。 | `test_run_ircheck_text_reg_alias_matches_ssa_ids` |
| TC-TOOLS-IRCHECK-069 | 执行结果 | run ircheck text val alias matches identifiers | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_run_ircheck_text_val_alias_matches_identifiers`。 | 命令返回码、输出、执行结果或状态变更体现“run ircheck text val alias matches identifiers”场景。 | `test_run_ircheck_text_val_alias_matches_identifiers` |
| TC-TOOLS-IRCHECK-070 | 执行结果 | run ircheck text numeric ssa signature keeps colon tight | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_run_ircheck_text_numeric_ssa_signature_keeps_colon_tight`。 | 命令返回码、输出、执行结果或状态变更体现“run ircheck text numeric ssa signature keeps colon tight”场景。 | `test_run_ircheck_text_numeric_ssa_signature_keeps_colon_tight` |
| TC-TOOLS-IRCHECK-071 | 生成/编译 | run ircheck text emitc cpu matches generated source | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_run_ircheck_text_emitc_cpu_matches_generated_source`。 | 生成源码、IR 文本或编译结果体现“run ircheck text emitc cpu matches generated source”场景。 | `test_run_ircheck_text_emitc_cpu_matches_generated_source` |
| TC-TOOLS-IRCHECK-072 | 边界/异常 | run ircheck text emitc cpu match failure reports generated source | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_emitc_cpu_match_failure_reports_generated_source`。 | “run ircheck text emitc cpu match failure reports generated source”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_emitc_cpu_match_failure_reports_generated_source` |
| TC-TOOLS-IRCHECK-073 | 边界/异常 | run ircheck text emitc npu demo maps generation failure | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_emitc_npu_demo_maps_generation_failure`。 | “run ircheck text emitc npu demo maps generation failure”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_emitc_npu_demo_maps_generation_failure` |
| TC-TOOLS-IRCHECK-074 | 解析/打印 | run ircheck text literal regex and parse error matrix | 准备包含 inline regex literal、无 CHECK case 与非法 regex / 变量片段的公开 ircheck 文本。 | 运行 `test_run_ircheck_text_literal_regex_and_parse_error_matrix`。 | inline regex 与无 CHECK case 按公开入口执行成功；非法 regex、空变量 regex 和残缺转义变量按 `IrcheckParseError: invalid regex check` 失败，未定义变量引用按 `IrcheckParseError: undefined regex variable` 失败。 | `test_run_ircheck_text_literal_regex_and_parse_error_matrix` |
| TC-TOOLS-IRCHECK-075 | 边界/异常 | run ircheck text public failure boundary matrix | 准备空输入、尾部分隔符、非法 IR、越界 `CHECK-NEXT` 与 CPU emitc 多函数 module。 | 运行 `test_run_ircheck_text_public_failure_boundary_matrix`。 | 各输入分别按公开结果返回 `missing input ir`、`invalid ircheck header`、输入 IR 解析失败、`CHECK-NEXT` 匹配失败与 CPU emitc 输入形态错误。 | `test_run_ircheck_text_public_failure_boundary_matrix` |
