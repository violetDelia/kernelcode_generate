# ircheck.md

## 功能简介

- 定义一个面向 IR 变换验证的轻量工具 `ircheck`：读取 case 文本，按 `COMPILE_ARGS` 运行 pass / pipeline，对规范化后的 IR 执行 `CHECK:` / `CHECK-NOT:` / `CHECK-NEXT:` 子串匹配，以及 `CHECK-REGEX:` / `CHECK-NEXT-REGEX:` / `CHECK-NOT-REGEX:` 正则匹配，最终输出 `true/false`。
- 支持使用 `// -----` 在同一文件/文本中分隔多个 case（lit 风格），按顺序执行并在首个失败处停止。
- 该工具用于“验证你关心的片段是否出现/不出现/是否相邻”，而不是做全量文本 diff；正则指令额外支持 `[[NAME:REGEX]]` 变量捕获与 `[[NAME]]` 复用。

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
- 默认解析上下文加载的 dialect：
  - `xdsl.dialects.builtin` / `xdsl.dialects.func` / `xdsl.dialects.arith`
  - `kernel_gen.dialect.nn` / `kernel_gen.dialect.kernel`

## 术语

- `case file`：包含头部注释指令与输入 IR 的单个文本文件（推荐扩展名 `.mlir` 或 `.ircheck`）。
- `case block`：被 `// -----` 分隔出来的一个独立 case 单元。
- `directive`：头部注释中的指令行，包括 `COMPILE_ARGS:` 与 `CHECK*:`。
- `positive check`：`CHECK:`、`CHECK-NEXT:`、`CHECK-REGEX:` 与 `CHECK-NEXT-REGEX:`，用于定义“顺序/相邻”的命中锚点。
  - 其中可作为首条正向锚点的只有 `CHECK:` 与 `CHECK-REGEX:`；
  - `CHECK-NEXT:` 与 `CHECK-NEXT-REGEX:` 必须依附前一条已命中的 positive check。
- `compile args`：`COMPILE_ARGS:` 指令后的一段参数串，支持 `--pass <name>` / `--pipeline <name>`，以及带 `{k=v}` 选项块的 `--pass "<name>{k=v}"` / `--pipeline "<name>{k=v}"`。

## 目标

- 公开一个可被 CLI / pytest 复用的最小执行链：`解析 -> 执行 pass/pipeline -> 打印 -> 匹配 -> 返回结果`。
- 把外部依赖稳定收口到三条公开 Python API：`parse_ircheck_file`、`run_ircheck_file`、`run_ircheck_text`。
- 让下游验证用例可以只写“关心的几行”，而不必在测试里拼接大量断言样板。

## 样例目录

- `expectation/tools/ircheck/basic_true.py`：验证 `run_ircheck_text(...)` 成功路径返回 `ok=True`。
- `expectation/tools/ircheck/basic_false.py`：验证 `run_ircheck_text(...)` 返回 `ok=False` 且错误短语稳定。
- `expectation/tools/ircheck/check_next_false.py`：验证相邻行匹配失败时返回稳定错误短语。
- `expectation/tools/ircheck/multi_pass_true.py`：验证多 step 顺序执行与成功路径输出。
- `expectation/tools/ircheck/multi_pass_fail.py`：验证失败 step 的定位信息与 `actual_ir` 语义。
- `expectation/tools/ircheck/ir_dump_true.py`：验证 `-irdump` 的目录与文件命名。
- `expectation/tools/ircheck/regex_variable_true.py`：验证 `CHECK-REGEX*` 与变量捕获/引用的成功路径。
- `expectation/tools/ircheck/regex_variable_false.py`：验证正则/变量写法失败时的稳定错误短语。
- `expectation/tools/ircheck/README.md`：样例入口与迁移写法，强调三条公开 API 为稳定合同，并补齐 regex/variable 示例。

## 迁移建议

- 旧测试中若手写字符串断言，可迁移为单文件 case + `ircheck` 检查指令。
- expectation 文档统一写法：仅 `parse_ircheck_file`、`run_ircheck_file`、`run_ircheck_text` 为稳定合同，其余符号视为内部细节。
- 固定文本仍优先使用 `CHECK:` / `CHECK-NEXT:` / `CHECK-NOT:`；当维度、符号名或 SSA 名需要“先捕获再复用”时，改用 `CHECK-REGEX:` / `CHECK-NEXT-REGEX:` / `CHECK-NOT-REGEX:`。

## 限制与边界

- 指令集支持六条检查指令：`CHECK:`、`CHECK-NOT:`、`CHECK-NEXT:`、`CHECK-REGEX:`、`CHECK-NEXT-REGEX:`、`CHECK-NOT-REGEX:`；仍不支持 `CHECK-LABEL`。
- `CHECK:` / `CHECK-NEXT:` / `CHECK-NOT:` 继续按“逐行子串匹配”工作；`CHECK-REGEX:` / `CHECK-NEXT-REGEX:` / `CHECK-NOT-REGEX:` 按“逐行正则匹配”工作，不做跨行拼接匹配。
- 变量捕获语法 `[[NAME:REGEX]]` 与引用语法 `[[NAME]]` 仅在 `CHECK-REGEX*` 指令中生效；变量作用域只限当前 case，不跨 case 共享。
- `CHECK-NOT-REGEX:` 禁止定义新变量；只允许引用已经在更早的 positive regex check 中成功捕获的变量。
- IR 自身的字面量 `[` / `]` 不是变量语法的一部分；在正则指令中仍必须单独写作 `\[` / `\]`。
- 内置正则别名仅允许出现在 `[[NAME:REGEX]]` 的 `REGEX` 区段内：
  - `{reg}`：`[A-Za-z_][A-Za-z0-9_]*`
  - `{dim}`：`[1-9][0-9]*`
  - `{int}`：`-?[0-9]+`
- 多 case 仅支持固定分隔符 `// -----`；不支持 case 命名、标签跳转或条件执行。
- `COMPILE_ARGS:` 支持重复 step，并按文本顺序执行；单个 step 仍沿用以下写法：
  - `--pass <pass-name>`
  - `--pass "<pass-name>{k=v}"`
  - `--pass "<pass-name>{k1=v1,k2=v2}"`
  - `--pipeline <pipeline-name>`
  - `--pipeline "<pipeline-name>{k=v}"`
  - `--pipeline "<pipeline-name>{k1=v1,k2=v2}"`
- 当 `compile args` 中包含 `{` / `}` 时，必须使用单引号或双引号包住整个 `<name>{k=v}`；未加引号视为不支持的写法。
- 单个 case 内任一步执行失败必须立即停止，后续 step 不再执行。
- 选项块语法为 `name={k=v[,k=v]}`：
  - `k` 与 `v` 去掉首尾空白后都不得为空；
  - `k` 不可重复；
  - 不支持嵌套 `{}`、不支持列表、不支持再包引号；
  - 选项值按原始字符串透传给 registry，不在工具层解析为布尔或数字。
- `ircheck` 不维护自己的 pass/pipeline 名称表，也不判断 option 业务语义；它只通过 [`spec/pass/registry.md`](../../spec/pass/registry.md) 定义的注册接口解析名字与选项。
- 输出文本：
  - 成功：标准输出仅打印 `true`
  - 失败：标准输出第一行打印 `false`，后续打印最小失败说明（至少包含错误短语与触发原因）
- 错误短语要求：
  - 本文件列出的错误短语是稳定前缀；实现可以在前缀后追加上下文，但不得替换前缀本身。

## 公开接口

### CLI：`python -m kernel_gen.tools.ircheck <case-file>`

功能说明：

- 运行一个 case 文件并在标准输出打印 `true/false`。
- 当文件包含 `// -----` 时，按 case block 顺序执行（fail-fast）。

参数说明：

- `<case-file> (str)`：单个文本文件路径。

使用示例：

```text
PYTHONPATH=. python -m kernel_gen.tools.ircheck case.ircheck
```

注意事项：

- CLI 内部应调用 `run_ircheck_file(path)` 并将返回值映射到输出与退出码（见下节）。
- CLI 支持 `-irdump` 选项：开启后将每个 case 的每一步 IR 写入 `<cwd>/.irdump/<stem>/case_<index>/`。

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
- 头部注释区内：
  - `COMPILE_ARGS:` 允许出现一次且必须出现一次
  - `CHECK:` / `CHECK-NOT:` / `CHECK-NEXT:` / `CHECK-REGEX:` / `CHECK-NEXT-REGEX:` / `CHECK-NOT-REGEX:` 可出现零次或多次，按出现顺序保存
  - 非上述指令的注释行允许存在，解析时忽略
- `COMPILE_ARGS:` 的参数串（冒号后内容）去掉首尾空白后不得为空。
- `CHECK:` / `CHECK-NOT:` / `CHECK-NEXT:` / `CHECK-REGEX:` / `CHECK-NEXT-REGEX:` / `CHECK-NOT-REGEX:` 的检查文本（冒号后内容）去掉首尾空白后都不得为空。
- `CHECK-NEXT:` 与 `CHECK-NEXT-REGEX:` 都不得作为“第一条 positive check”出现；也即：
  - 在所有 `CHECK:` / `CHECK-NEXT:` / `CHECK-REGEX:` / `CHECK-NEXT-REGEX:` 中，第一条必须为 `CHECK:` 或 `CHECK-REGEX:`；
  - 若第一条 positive check 为 `CHECK-NEXT:` 或 `CHECK-NEXT-REGEX:`，必须返回解析失败。
- `CHECK-REGEX*` 指令的变量语法验证规则：
  - `[[NAME:REGEX]]` 表示“定义变量 `NAME` 并用 `REGEX` 捕获该段文本”；
  - `[[NAME]]` 表示“引用先前已捕获的变量 `NAME`，按字面量匹配”；
  - 同一 case 内，变量名只能定义一次；重复定义必须返回解析失败；
  - 引用变量时，变量定义必须先于当前指令出现；引用未定义变量必须返回解析失败；
  - `CHECK-NOT-REGEX:` 中出现 `[[NAME:REGEX]]` 必须返回解析失败；
  - `{reg}` / `{dim}` / `{int}` 仅在 `[[NAME:REGEX]]` 的 `REGEX` 段内展开，在其他文本中保持普通字符含义。
- 若输入 IR 正文在去掉空白后为空，必须返回解析失败。
- `parse_ircheck_file` 只处理单 case；若文本包含 `// -----` 多 case 分隔符，必须返回 `IrcheckParseError: invalid ircheck header`。

返回与限制：

- 失败时必须抛出异常，且错误信息前缀为下述之一：
  - `IrcheckParseError: invalid ircheck header`
  - `IrcheckParseError: missing input ir`
  - `IrcheckParseError: invalid regex check`
  - `IrcheckParseError: undefined regex variable`
  - `IrcheckParseError: duplicate regex variable`
  - `IrcheckParseError: CHECK-NOT-REGEX cannot define variables`

### `run_ircheck_file(path: str) -> IrcheckResult`

功能说明：

- 读取文件、执行 pass/pipeline、打印规范化 IR，并对规范化 IR 执行检查指令。
- 若文件中存在 `// -----` 分隔符，按 case block 顺序执行。

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
  - 支持重复 `--pass` / `--pipeline`，并按文本顺序执行
  - 支持 `--pass <name>` / `--pipeline <name>`
  - 支持 `--pass "<name>{k=v}"` / `--pipeline "<name>{k=v}"`
  - 选项块语法非法或未加引号时，必须视为不支持
- 名称解析与执行顺序要求：
  1. 调用 `load_builtin_passes()`
  2. 按 `COMPILE_ARGS` 文本顺序逐个 step 执行
  3. `--pass <name>`：调用 `build_registered_pass(name, options)` 得到 `Pass` 实例并执行
  4. `--pipeline <name>`：调用 `build_registered_pipeline(name, options)` 得到 `PassManager` 并执行
- `options` 为空或未提供时，视为无参构造路径。
- 名称解析仅走 registry 提供的接口，不直接 import pipeline builder。
- 多 case 执行语义：
  1. 按文件中的 case block 顺序逐个执行；
  2. 任一 case 失败则立即返回（fail-fast）；
  3. 全部通过时返回最后一个 case 的成功结果。

返回与限制：

- 若 case 文本解析失败，返回 `ok=False`，`exit_code=2`，且 `message` 前缀为：
  - `IrcheckParseError: invalid ircheck header`
  - `IrcheckParseError: missing input ir`
  - `IrcheckParseError: invalid regex check`
  - `IrcheckParseError: undefined regex variable`
  - `IrcheckParseError: duplicate regex variable`
  - `IrcheckParseError: CHECK-NOT-REGEX cannot define variables`
- 若 `COMPILE_ARGS` 不支持（含选项块语法非法或未加引号），返回 `ok=False`，`exit_code=2`，且 `message` 前缀为：
  - `IrcheckCompileArgsError: unsupported compile args`
- 若 pass/pipeline 执行抛错或返回不可打印的对象，返回 `ok=False`，`exit_code=2`，且 `message` 前缀为：
  - `IrcheckRunError: pass execution failed`
- 若匹配失败，返回 `ok=False`，`exit_code=1`，且 `message` 前缀为：
  - `IrcheckMatchError: CHECK not found`
  - `IrcheckMatchError: CHECK-NEXT not found on next line`
  - `IrcheckMatchError: CHECK-NOT matched forbidden text`
  - `IrcheckMatchError: CHECK-REGEX not found`
  - `IrcheckMatchError: CHECK-NEXT-REGEX not found on next line`
  - `IrcheckMatchError: CHECK-NOT-REGEX matched forbidden text`
- 若多 step 执行中途失败：
  - `message` 必须包含失败 step 序号（从 1 开始）、step 类型（pass/pipeline）与 step 名字（不含选项块）。
  - `actual_ir` 必须返回失败前一刻的规范化 IR：
    - step 1 失败时返回输入 IR 的规范化文本；
    - step N 失败时返回第 N-1 步执行后的规范化 IR。

### `run_ircheck_text(text: str, source_path: str | None = None) -> IrcheckResult`

功能说明：

- 直接运行一段 case 文本（无需写入文件），其语义与 `run_ircheck_file` 一致。
- 支持 `// -----` 多 case 分隔，执行语义与 `run_ircheck_file` 完全一致。

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

返回与限制：

- 返回行为与 `run_ircheck_file` 相同；仅输入源不同。
 - `COMPILE_ARGS` 支持重复 `--pass` / `--pipeline` 并按文本顺序执行。

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
  - `kind (Literal["CHECK", "CHECK-NEXT", "CHECK-NOT", "CHECK-REGEX", "CHECK-NEXT-REGEX", "CHECK-NOT-REGEX"])`
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
- `actual_ir` 在解析失败时允许为空；执行失败时按 “run_ircheck_file” 的 step 失败规则返回失败前一刻的 IR。

返回与限制：

- `ok=True` 时 `exit_code` 必须为 `0`。

### 检查语义

功能说明：

- 定义 `CHECK:` / `CHECK-NEXT:` / `CHECK-NOT:` 与 `CHECK-REGEX:` / `CHECK-NEXT-REGEX:` / `CHECK-NOT-REGEX:` 在“规范化 IR 文本”上的匹配规则。

注意事项：

- 匹配对象为 pass/pipeline 执行后的规范化 IR 文本 `actual_ir`，不匹配原始输入文本。
- 匹配按“行”进行：把 `actual_ir` 视为按换行符拆分的行序列 `lines`（等价于 `actual_ir.splitlines()`），每条指令都在 `lines[i]` 上做子串查找；不做跨行拼接匹配。
- `CHECK:` / `CHECK-NEXT:` / `CHECK-NOT:` 保持“子串匹配”语义，不做正则解释。
- `CHECK-REGEX:` / `CHECK-NEXT-REGEX:` / `CHECK-NOT-REGEX:` 在单行文本上做正则匹配；IR 字面量 `[` / `]` 仍需单独写作 `\[` / `\]`。
- 正则变量处理顺序固定为：
  1. 先读取当前 case 已成功捕获的变量表；
  2. 把 `[[NAME]]` 替换为 `re.escape(value)` 形式的字面量匹配；
  3. 把 `[[NAME:REGEX]]` 转成“记录命中原文”的捕获片段，并在其中展开 `{reg}` / `{dim}` / `{int}`；
  4. 当前 regex directive 匹配成功后，才把本条新定义的变量写回变量表；若本条匹配失败，则不得提交部分变量。
- 指令按在 case 文件中的出现顺序依次处理；`CHECK-NOT` 与 `CHECK-NOT-REGEX` 都不改变后续 positive check 的搜索起点。

返回与限制：

- `positive check` 指令命中规则（会更新“当前命中行”；本节的 `positive check` 固定指 `CHECK:`、`CHECK-NEXT:`、`CHECK-REGEX:`、`CHECK-NEXT-REGEX:`）：
  - 初始 `last_positive_line = None`。
  - `CHECK:`：
    - 令 `start = 0`（当 `last_positive_line is None`）或 `start = last_positive_line + 1`；
    - 从 `lines[start:]` 中按行向后查找第一条包含 `text` 子串的行，命中行号为 `hit_line`；
    - 若找不到，则失败，错误短语为 `IrcheckMatchError: CHECK not found`；
    - 命中后：`last_positive_line = hit_line`。
  - `CHECK-REGEX:`：
    - 令 `start = 0`（当 `last_positive_line is None`）或 `start = last_positive_line + 1`；
    - 从 `lines[start:]` 中按行向后查找第一条满足 regex 搜索的行，命中行号为 `hit_line`；
    - 若找不到，则失败，错误短语为 `IrcheckMatchError: CHECK-REGEX not found`；
    - 命中后：`last_positive_line = hit_line`，并提交本条新捕获的变量。
  - `CHECK-NEXT:`：
    - 该指令只能在 `last_positive_line is not None` 时出现（否则属于“无前置 positive check”，必须在解析阶段失败）；
    - 令 `hit_line = last_positive_line + 1`，要求 `hit_line` 存在且 `text` 为 `lines[hit_line]` 的子串；
    - 若不命中，则失败，错误短语为 `IrcheckMatchError: CHECK-NEXT not found on next line`；
    - 命中后：`last_positive_line = hit_line`。
  - `CHECK-NEXT-REGEX:`：
    - 该指令只能在 `last_positive_line is not None` 时出现（否则属于“无前置 positive check”，必须在解析阶段失败）；
    - 令 `hit_line = last_positive_line + 1`，要求 `hit_line` 存在且当前 regex 能在 `lines[hit_line]` 上命中；
    - 若不命中，则失败，错误短语为 `IrcheckMatchError: CHECK-NEXT-REGEX not found on next line`；
    - 命中后：`last_positive_line = hit_line`，并提交本条新捕获的变量。
- `CHECK-NOT:` / `CHECK-NOT-REGEX:` 指令命中规则（不更新 `last_positive_line`）：
  - `CHECK-NOT` 与 `CHECK-NOT-REGEX` 都以“区间约束”的方式生效：它们约束的区间由其两侧最近的 positive check 的“命中行”决定。
  - 推荐实现方式（用于定义确定性合同）：
    1. 依序扫描指令；遇到 `CHECK-NOT` / `CHECK-NOT-REGEX` 先加入 `pending_not` 列表。
    2. 当遇到下一条 positive check 并成功命中行 `hit_line` 后，计算 `pending_not` 的禁止区间并逐条验证，然后清空 `pending_not`：
       - `forbid_start = 0`（当上一条 positive check 不存在）或 `forbid_start = prev_positive_line + 1`
       - `forbid_end = hit_line - 1`
       - 区间为闭区间 `[forbid_start, forbid_end]`；当 `forbid_start > forbid_end` 时区间为空，视为自动通过
       - 对每条 `CHECK-NOT: text`：要求 `text` 不得成为区间内任一行的子串
       - 对每条 `CHECK-NOT-REGEX: regex`：要求 `regex` 不得在区间内任一行命中；该指令只允许引用已存在变量，不得定义新变量
    3. 所有指令处理完成后，若 `pending_not` 非空，按“最后一条 positive check 命中行之后到文件末尾”的区间验证：
       - `forbid_start = 0`（当不存在任何 positive check）或 `forbid_start = last_positive_line + 1`
       - `forbid_end = len(lines) - 1`
  - 若 `CHECK-NOT` 违反禁止区间，则失败，错误短语为 `IrcheckMatchError: CHECK-NOT matched forbidden text`。
  - 若 `CHECK-NOT-REGEX` 违反禁止区间，则失败，错误短语为 `IrcheckMatchError: CHECK-NOT-REGEX matched forbidden text`。

## 额外补充

### 用户文档（case file 编写）

- 一个 case file 由两部分组成：
  - 头部注释区：文件起始处连续的 `// ...` 行，包含恰好一条 `COMPILE_ARGS:` 与零到多条 `CHECK*:` 指令；
  - 输入 IR 正文：从第一行“非 `//` 开头的行”起，到文件结束。
- 单文件多 case 写法：
  - 使用独占一行的 `// -----` 分隔相邻 case block；
  - 每个 block 都必须包含自己的 `COMPILE_ARGS:` 与输入 IR；
  - 分隔符前后不允许出现空 block（否则视为解析失败）。
- 推荐写法：
  - 先用 `CHECK:` 选择一个稳定锚点（例如 `func.func @main`），再用 `CHECK:` / `CHECK-NEXT:` 逐步收紧局部相邻关系；
  - 用 `CHECK-NOT:` 表达“在两条 positive check 之间不得出现”的否定约束；
  - 当维度、符号名或 SSA 名是动态值时，优先用 `CHECK-REGEX:` 定义变量，再用 `CHECK-NEXT-REGEX:` / `CHECK-NOT-REGEX:` 复用。
- 最小示例：

```mlir
// COMPILE_ARGS: --pass lower-nn
// CHECK: kernel.add
// CHECK-NOT: nn.add

builtin.module { /* ... */ }
```

- 正则 / 变量最小示例：

> `[[NAME:REGEX]]` / `[[NAME]]` 只表示 ircheck 变量占位；IR 自身的字面量 `[` / `]` 仍需单独写作 `\[` / `\]`。

```mlir
// COMPILE_ARGS: --pass lower-nn
// CHECK-REGEX: func.func @exp_kernel\(%arg0 : !nn.memory<\[[[M:{dim}]], [[N:{dim}]]\], \[[[N]], 1\], f32, #nn.space<global>>\) -> !nn.memory<\[[[M]], [[N]]\], \[[[N]], 1\], f32, #nn.space<global>>
// CHECK-NEXT-REGEX: "dma.alloc"() .* -> !nn.memory<\[[[M]], [[N]]\], \[[[N]], 1\], f32, #nn.space<global>>

builtin.module { /* ... */ }
```

### 多 step 示例

```mlir
// COMPILE_ARGS: --pass lower-nn --pass buffer-results-to-out-params --pass "tile={tile-only=true,tile-elewise=true}"
// CHECK: symbol.for

builtin.module { /* ... */ }
```

### `-irdump` 目录与文件命名

- 开启 `-irdump` 后默认写入 `<cwd>/.irdump/<stem>/case_<index>/`。
- 多 case 时目录必须按 `case_01`、`case_02`、`case_03` 递增编号；编号基于 case 在文件中的顺序。
- 每个 case 内的文件命名固定为：
  - `00-input.mlir`
  - `01-pass-<name>.mlir` / `01-pipeline-<name>.mlir`
  - 若某一步失败，额外写入 `NN-before-failed-<type>-<name>.mlir`。

### 迁移建议（从字符串断言到 ircheck）

- `assert "X" in actual_ir` -> `// CHECK: X`
- `assert "X" not in actual_ir` -> `// CHECK-NOT: X`
  - 建议把 `CHECK-NOT` 放在两个 positive check 之间（或文件末尾），以明确其禁止区间，避免歧义。
- “相邻行”断言 -> `// CHECK: <anchor>` + `// CHECK-NEXT: <next>`
- 动态维度 / 动态符号名断言 -> `// CHECK-REGEX: <...[[NAME:REGEX]]...>` + `// CHECK-NEXT-REGEX: <...[[NAME]]...>`

### 稳定接口范围（可复用表述）

- 对外可复用且承诺长期兼容的 Python 接口仅包含：
  - `parse_ircheck_file`
  - `run_ircheck_file`
  - `run_ircheck_text`
- 本文件中提到的 `IrcheckCase` / `CheckDirective` / `IrcheckResult` 的字段名、以及 `kernel_gen.tools.ircheck` 内部实现细节，均不作为稳定承诺；下游应以“公开接口”一节描述的入参与返回语义（如 `ok/exit_code/message`）为对齐依据。

## 测试

- 测试文件：
  - [`test/tools/test_ircheck_parser.py`](../../test/tools/test_ircheck_parser.py)
  - [`test/tools/test_ircheck_runner.py`](../../test/tools/test_ircheck_runner.py)
  - [`test/tools/test_ircheck_matcher.py`](../../test/tools/test_ircheck_matcher.py)
  - [`test/tools/test_ircheck_cli.py`](../../test/tools/test_ircheck_cli.py)
- 执行命令：
  - `pytest -q test/tools/test_ircheck_parser.py`
  - `pytest -q test/tools/test_ircheck_runner.py`
  - `pytest -q test/tools/test_ircheck_matcher.py`
  - `pytest -q test/tools/test_ircheck_cli.py`
- 测试目标：
  - parser：能稳定解析头部注释区、提取 compile_args 与六类检查指令，并对缺失/重复指令、非法 regex 语法、未定义变量、重复变量、`CHECK-NOT-REGEX` 非法定义变量返回稳定错误短语；`parse_ircheck_file` 对多 case 分隔符稳定拒绝。
  - runner：能通过 pass registry 解析 `--pass/--pipeline` 与其 options 形式并执行，输出 `IrcheckResult` 的 `ok/exit_code/message` 行为与本文件一致；支持多 case 顺序执行与 fail-fast。
  - runner：多 step 失败时必须返回 step 序号/类型/名字，并按失败前一刻 IR 填充 `actual_ir`；覆盖 `expectation/tools/ircheck/multi_pass_fail.py` 与 `test/tools/test_ircheck_runner.py` 对应用例。
  - matcher：能按本文件“检查语义”规则稳定处理 `CHECK/CHECK-NEXT/CHECK-NOT` 与 `CHECK-REGEX/CHECK-NEXT-REGEX/CHECK-NOT-REGEX` 的顺序、相邻、区间与变量复用约束，并在失败时返回稳定错误短语。
  - cli：开启 `-irdump` 后需生成 `.irdump/<stem>/case_01/`、`.irdump/<stem>/case_02/` 等目录与逐 step IR 文件；覆盖 `expectation/tools/ircheck/ir_dump_true.py` 与 `test/tools/test_ircheck_cli.py` 对应用例。
