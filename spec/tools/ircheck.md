# ircheck.md

## 功能简介

- 定义一个面向 IR 变换验证的轻量工具 `ircheck`：读取单文件 case，按 `COMPILE_ARGS` 运行 pass / pipeline，对规范化后的 IR 执行 `CHECK:` / `CHECK-NOT:` / `CHECK-NEXT:` 子串匹配，最终输出 `true/false`。
- 该工具用于“验证你关心的片段是否出现/不出现/是否相邻”，而不是做全量文本 diff。

## 文档信息

- 创建者：`睡觉小分队`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/tools/ircheck.md`](../../spec/tools/ircheck.md)
- `功能实现`：[`kernel_gen/tools/ircheck.py`](../../kernel_gen/tools/ircheck.py)
- `test`：
  - [`test/tools/test_ircheck_parser.py`](../../test/tools/test_ircheck_parser.py)
  - [`test/tools/test_ircheck_runner.py`](../../test/tools/test_ircheck_runner.py)
  - [`test/tools/test_ircheck_matcher.py`](../../test/tools/test_ircheck_matcher.py)

## 依赖

- pass / pipeline 名称解析：
  - [`spec/pass/registry.md`](../../spec/pass/registry.md)
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
- pass 执行容器：
  - [`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)
  - [`kernel_gen/passes/pass_manager.py`](../../kernel_gen/passes/pass_manager.py)
- IR 解析与打印（用于“规范化后的 IR”文本）：
  - [`kernel_gen/context.py`](../../kernel_gen/context.py)
  - [`kernel_gen/dialect`](../../kernel_gen/dialect)

## 术语

- `case file`：包含头部注释指令与输入 IR 的单个文本文件（推荐扩展名 `.mlir` 或 `.ircheck`）。
- `directive`：头部注释中的指令行，包括 `COMPILE_ARGS:` 与 `CHECK*:`。
- `positive check`：`CHECK:` 与 `CHECK-NEXT:`，用于定义“顺序/相邻”的命中锚点。
- `compile args`：`COMPILE_ARGS:` 指令后的一段参数串，仅承接 `--pass <name>` 或 `--pipeline <name>` 两种形式。
- `match line`：一次 positive check 命中的“规范化 IR 文本”所在行。

## 目标

- 公开一个可被 CLI / pytest 复用的最小执行链：`解析 -> 执行 pass/pipeline -> 打印 -> 匹配 -> 返回结果`。
- 把外部依赖稳定收口到三条公开 Python API：`parse_ircheck_file`、`run_ircheck_file`、`run_ircheck_text`。
- 让下游验证用例可以只写“关心的几行”，而不必在测试里拼接大量断言样板。

## 限制与边界

- 指令集只支持三条检查指令：`CHECK:`、`CHECK-NOT:`、`CHECK-NEXT:`；不支持正则、变量捕获、`CHECK-LABEL`、多 case 文件合并。
- `COMPILE_ARGS:` 只支持两种写法：
  - `--pass <pass-name>`
  - `--pipeline <pipeline-name>`
- `COMPILE_ARGS:` 必须且只能出现一次；缺失或重复都必须视为解析失败。
- `CHECK-NEXT:` 不得出现在任何 positive check 之前；否则必须视为解析失败。
- 每条 `CHECK*:` 指令的 `<text>` 不得为空串；否则必须视为解析失败。
- `ircheck` 不维护自己的 pass 名称表；它只通过 [`spec/pass/registry.md`](../../spec/pass/registry.md) 定义的注册接口解析名字。
- 输出文本：
  - 成功：标准输出仅打印 `true`
  - 失败：标准输出第一行打印 `false`，后续打印最小失败说明（至少包含错误短语与触发原因，并包含失败指令与规范化后的实际 IR）
- 错误短语要求：
  - 本文件列出的错误短语是稳定前缀；实现可以在前缀后追加上下文，但不得替换前缀本身。

## 公开接口

### CLI：`python -m kernel_gen.tools.ircheck <case-file>`

功能说明：

- 运行单个 case 文件并在标准输出打印 `true/false`。

参数说明：

- `<case-file> (str)`：单个文本文件路径。

使用示例：

```text
PYTHONPATH=. python -m kernel_gen.tools.ircheck case.ircheck
```

注意事项：

- CLI 内部应调用 `run_ircheck_file(path)` 并将返回值映射到输出与退出码（见下节）。

返回与限制：

- 退出码：
  - `0`：检查通过
  - `1`：检查不通过（匹配失败）
  - `2`：解析失败、参数不支持、或 pass/pipeline 执行失败

### `parse_ircheck_file(path: str) -> IrcheckCase`

功能说明：

- 从磁盘读取单个 case 文件，解析出 `compile_args`、`checks` 与 `input_ir`。

参数说明：

- `path (str)`：case 文件路径。

使用示例：

```python
from kernel_gen.tools.ircheck import parse_ircheck_file

case = parse_ircheck_file("case.ircheck")
assert case.compile_args.startswith("--pass ")
```

注意事项：

- 文件结构由两部分组成：
  1. 文件起始处的“头部注释区”：连续的 `// ...` 行
  2. 输入 IR 正文：从第一行“非 `//` 开头的行”起，到文件结束
- 头部注释区内支持的指令：
  - `// COMPILE_ARGS: <args>`
  - `// CHECK: <text>`
  - `// CHECK-NEXT: <text>`
  - `// CHECK-NOT: <text>`
- 头部注释区内允许出现其他注释行：解析时忽略。
- 解析期必须做的合法性检查（任一失败都视为解析失败）：
  - `COMPILE_ARGS:` 缺失或重复
  - 出现未知指令头（例如拼写错误的 `CHECKX:`）
  - 任一 `CHECK*:` 的 `<text>` 为空串
  - 任一 `CHECK-NEXT:` 出现在任何 positive check 之前
- 若输入 IR 正文为空，必须视为解析失败。

返回与限制：

- 失败时必须抛出异常，且错误信息前缀为下述之一：
  - `IrcheckParseError: invalid ircheck header`
  - `IrcheckParseError: missing input ir`

### `run_ircheck_file(path: str) -> IrcheckResult`

功能说明：

- 读取文件、执行 pass/pipeline、打印规范化 IR，并对规范化 IR 执行检查指令。

参数说明：

- `path (str)`：case 文件路径。

使用示例：

```python
from kernel_gen.tools.ircheck import run_ircheck_file

result = run_ircheck_file("case.ircheck")
assert result.ok is True
```

注意事项：

- `COMPILE_ARGS` 解析规则：
  - 仅支持 `--pass <name>` 与 `--pipeline <name>` 两种形式
  - 其他参数形态必须视为不支持
- 名称解析与执行顺序要求：
  1. 调用 `load_builtin_passes()`
  2. `--pass <name>`：调用 `build_registered_pass(name)` 得到 `Pass` 实例并执行
  3. `--pipeline <name>`：调用 `build_registered_pipeline(name)` 得到 `PassManager` 并执行

返回与限制：

- 若 `COMPILE_ARGS` 不支持，返回 `ok=False`，`exit_code=2`，且 `message` 前缀为：
  - `IrcheckCompileArgsError: unsupported compile args`
- 若 pass/pipeline 执行抛错或无法输出规范化 IR，返回 `ok=False`，`exit_code=2`，且 `message` 前缀为：
  - `IrcheckRunError: pass execution failed`
- 若匹配失败，返回 `ok=False`，`exit_code=1`，且 `message` 前缀为：
  - `IrcheckMatchError: CHECK not found`
  - `IrcheckMatchError: CHECK-NEXT not found on next line`
  - `IrcheckMatchError: CHECK-NOT matched forbidden text`

### `run_ircheck_text(text: str, source_path: str | None = None) -> IrcheckResult`

功能说明：

- 直接运行一段 case 文本（无需写入文件），其语义与 `run_ircheck_file` 一致。

参数说明：

- `text (str)`：完整 case 文本。
- `source_path (str|None)`：可选，用于错误信息中的定位说明；不参与语义。

使用示例：

```python
from kernel_gen.tools.ircheck import run_ircheck_text

result = run_ircheck_text(
    \"\"\"// COMPILE_ARGS: --pass no-op
// CHECK: func.func @main

builtin.module { func.func @main() { func.return } }
\"\"\",
    source_path="inline.ircheck",
)
assert result.ok is True
```

注意事项：

- `no-op` 是建议的内置 pass 名称：其语义为“返回输入不变”，用于 matcher 的最小验证链。

返回与限制：

- 返回行为与 `run_ircheck_file` 相同；仅输入源不同。

### 数据对象：`IrcheckCase` / `CheckDirective` / `IrcheckResult`

功能说明：

- `IrcheckCase`：解析后的 case 对象（尚未执行）。
- `CheckDirective`：一条检查指令。
- `IrcheckResult`：一次执行结果。

参数说明：

- `IrcheckCase` 建议字段：
  - `compile_args (str)`
  - `checks (list[CheckDirective])`
  - `input_ir (str)`
  - `source_path (str|None)`
- `CheckDirective` 建议字段：
  - `kind (Literal[\"CHECK\", \"CHECK-NEXT\", \"CHECK-NOT\"])`
  - `text (str)`
  - `line_no (int)`：原始行号（从 1 开始）
- `IrcheckResult` 建议字段：
  - `ok (bool)`
  - `exit_code (int)`
  - `actual_ir (str)`：规范化后的 IR 文本（若解析失败可为空串）
  - `failed_check (CheckDirective|None)`
  - `message (str|None)`

使用示例：

```python
result = run_ircheck_text(\"\"\"// COMPILE_ARGS: --pass no-op
// CHECK: func.return

builtin.module { func.func @main() { func.return } }
\"\"\")
assert result.exit_code == 0
```

注意事项：

- `failed_check` 仅在匹配失败时必须给出；其他失败类型可为 `None`。
- `message` 的前缀必须使用本文件列出的错误短语之一。

返回与限制：

- `ok=True` 时 `exit_code` 必须为 `0`。

### 检查语义

功能说明：

- 定义 `CHECK:` / `CHECK-NEXT:` / `CHECK-NOT:` 三类指令在“规范化 IR 文本”上的匹配规则。

注意事项：

- 匹配规则为“子串匹配”，不做正则解释。
- 匹配对象为 pass/pipeline 执行后的规范化 IR 文本 `actual_ir`，不匹配原始输入文本。
- 建议实现以 `actual_ir.splitlines()` 得到行数组，并以“match line”为核心承载 `CHECK-NEXT` 与 `CHECK-NOT` 的区间语义。

返回与限制：

- `CHECK:`：
  - 从上一次 positive check 命中位置之后继续查找；
  - 找不到则失败，错误短语为 `IrcheckMatchError: CHECK not found`；
  - 命中时需要确定其 `match line`（命中子串所在行）。
- `CHECK-NEXT:`：
  - 必须出现在至少一条 positive check 之后（解析期已检查该约束）；
  - 其目标文本必须出现在上一条 positive check 命中行的下一行；
  - 若下一行不命中则失败，错误短语为 `IrcheckMatchError: CHECK-NEXT not found on next line`；
  - 命中时 `match line` 等于该下一行。
- `CHECK-NOT:`：
  - 其语义依赖于 directive 顺序中的相邻 positive check（不依赖于“按文本再次搜索得到的其他潜在命中”）；
  - 若位于两条 positive check 之间，则禁止文本出现在这两条命中行之间（不含边界行）；
  - 若位于文件开头到第一条 positive check 之前，则禁止文本出现在文件起始到第一条命中行之前；
  - 若位于最后一条 positive check 之后，则禁止文本出现在最后一条命中行之后；
  - 若违反则失败，错误短语为 `IrcheckMatchError: CHECK-NOT matched forbidden text`，并在 `failed_check` 指向触发失败的 `CHECK-NOT` 指令。

## 测试

- 测试文件：
  - [`test/tools/test_ircheck_parser.py`](../../test/tools/test_ircheck_parser.py)
  - [`test/tools/test_ircheck_runner.py`](../../test/tools/test_ircheck_runner.py)
  - [`test/tools/test_ircheck_matcher.py`](../../test/tools/test_ircheck_matcher.py)
- 执行命令：
  - `pytest -q test/tools/test_ircheck_parser.py`
  - `pytest -q test/tools/test_ircheck_runner.py`
  - `pytest -q test/tools/test_ircheck_matcher.py`
- 测试目标：
  - parser：能稳定解析头部注释区、提取 compile_args 与检查指令，并对缺失/重复/顺序非法返回稳定错误短语。
  - matcher：`CHECK:` 顺序匹配、`CHECK-NEXT:` 严格相邻、`CHECK-NOT:` 区间禁止语义与错误短语可机械比对。
  - runner：能通过 pass registry 解析 `--pass/--pipeline` 并执行，输出 `IrcheckResult` 的 `ok/exit_code/message` 行为与本文件一致。
