# ircheck.md

## 功能简介

- 定义一个面向 IR 变换验证的轻量工具 `ircheck`：读取 case 文本，按 `COMPILE_ARGS` 运行 pass / pipeline，对规范化后的 IR 执行 FileCheck 风格的逐行匹配：
  - `CHECK:` / `CHECK-NEXT:` / `CHECK-NOT:`：普通文本按字面量匹配，`[[NAME:REGEX]]` / `[[NAME]]` 变量片段可捕获与复用。
- 当显式启用 `emitc_target` 时，`ircheck` 在 compile steps 完成后改为对目标源码文本执行同一套 `CHECK*` 匹配；默认路径仍只匹配规范化 IR，不自动回退或混合双路径。
- 支持使用 `// -----` 在同一文件/文本中分隔多个 case，按顺序执行并在首个失败处停止。
- 整行 regex 语义不再单独提供指令变体；所有 regex 能力统一收口到 `[[NAME:REGEX]]` 的局部片段内。

## 文档信息

- 创建者：`睡觉小分队`
- 最后一次更改：`守护最好的爱莉希雅`
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
- IR 解析与打印：
  - [`kernel_gen/context.py`](../../kernel_gen/context.py)
  - [`kernel_gen/dialect`](../../kernel_gen/dialect)
- `emitc` 代码生成分支：
  - [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
  - [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md)
  - [`kernel_gen/dsl/gen_kernel/__init__.py`](../../kernel_gen/dsl/gen_kernel/__init__.py)
  - [`kernel_gen/dsl/gen_kernel/emit_c/__init__.py`](../../kernel_gen/dsl/gen_kernel/emit_c/__init__.py)

## 术语

- `case file`：包含头部注释指令与输入 IR 的单个文本文件。
- `case block`：被 `// -----` 分隔出来的一个独立 case 单元。
- `directive`：头部注释中的指令行，包括 `COMPILE_ARGS:` 与 `CHECK*:`。
- `正向检查`：`CHECK:` 与 `CHECK-NEXT:`，用于定义“顺序/相邻”的命中锚点。
  - 其中可作为首条正向锚点的只有 `CHECK:`；
  - `CHECK-NEXT:` 必须依附前一条已命中的正向检查。
- `compile args`：`COMPILE_ARGS:` 指令后的一段参数串，支持 `--pass <name>` / `--pipeline <name>`，以及带 `{k=v}` 选项块的 `--pass "<name>{k=v}"` / `--pipeline "<name>{k=v}"`。
- `emitc mode`：指 `run_ircheck_file(...)` / `run_ircheck_text(...)` 显式提供 `emitc_target` 后，在 compile steps 结束后把匹配对象从规范化 IR 切换为生成源码文本的执行分支。

## 目标

- 公开一个可被 CLI / pytest 复用的最小执行链：`解析 -> 执行 pass/pipeline -> 打印 -> 匹配 -> 返回结果`。
- 把外部依赖稳定收口到三条公开 Python API：`parse_ircheck_file`、`run_ircheck_file`、`run_ircheck_text`。
- 让下游验证用例可以只写“关心的几行”，而不必在测试里拼接大量断言样板。

## 测试目录

- [`test/tools/test_ircheck_parser.py`](../../test/tools/test_ircheck_parser.py)：解析与指令校验。
- [`test/tools/test_ircheck_runner.py`](../../test/tools/test_ircheck_runner.py)：pass / pipeline 执行与多 case 流程。
- [`test/tools/test_ircheck_matcher.py`](../../test/tools/test_ircheck_matcher.py)：`CHECK*` 匹配语义与变量复用。
- [`test/tools/test_ircheck_cli.py`](../../test/tools/test_ircheck_cli.py)：命令行入口与 `-irdump` / `-emitc` 分支。

## 迁移建议

- 旧测试中若手写字符串断言，可迁移为单文件 case + `ircheck` 检查指令。
- 测试文档统一写法：仅 `parse_ircheck_file`、`run_ircheck_file`、`run_ircheck_text` 为稳定合同，其余符号视为内部细节。
- 默认优先使用 `CHECK:` / `CHECK-NEXT:` / `CHECK-NOT:`：
  - 普通文本直接按字面量写，不需要像 Python regex 一样转义 `.`、`(`、`)`、`[`、`]` 等字符；
  - 若同一行需要捕获或复用 SSA 名、维度名、符号名，再在该行局部使用 `[[NAME:REGEX]]` / `[[NAME]]`。
- 不再提供 `CHECK-REGEX` / `CHECK-NEXT-REGEX` / `CHECK-NOT-REGEX`；整行 regex 需求必须改写为“固定文本 + 局部 `[[NAME:REGEX]]`”的形式。

## 限制与边界

- 指令集只支持三条检查指令：`CHECK:`、`CHECK-NOT:`、`CHECK-NEXT:`；不支持 `CHECK-LABEL`，也不兼容任何 `*-REGEX` 变体。
- `CHECK:` / `CHECK-NEXT:` / `CHECK-NOT:` 按“逐行字面量 + 局部变量片段”匹配工作，不做跨行拼接匹配。
- 变量捕获语法 `[[NAME:REGEX]]` 与引用语法 `[[NAME]]` 在全部 `CHECK*` 指令中都生效；变量作用域只限当前 case，不跨 case 共享。
- `CHECK-NOT:` 禁止定义新变量；只允许引用已经在更早的正向检查中成功捕获的变量。
- IR 自身的字面量 `[` / `]` 不是变量语法的一部分，在 `CHECK*` 中直接写即可。
- `emitc_target` 只接受 `cpu`、`npu_demo` 与 `None`。
- 一旦进入 `emitc mode`，`actual_ir` 与 `CHECK*` 的匹配对象都固定为生成源码文本；不得在同一次执行中同时匹配 IR 与源码，也不得在生成失败时静默回退到 IR 匹配。
- `emitc` 生成失败、`emitc_target` 不受支持、或目标 target 与当前 IR 结构不兼容时，统一返回 `IrcheckEmitCError: emit_c generation failed` 前缀。
- 内置正则别名仅允许出现在 `[[NAME:REGEX]]` 的 `REGEX` 区段内：
  - `{reg}`：`(?:[A-Za-z_][A-Za-z0-9_]*|[0-9]+)`
  - `{val}`：`[A-Za-z_][A-Za-z0-9_]*`
  - `{dim}`：`[1-9][0-9]*`
  - `{int}`：`-?[0-9]+`
- 多 case 仅支持固定分隔符 `// -----`；不支持 case 命名、标签跳转或条件执行。
- `COMPILE_ARGS:` 支持重复 step，并按文本顺序执行。

## 公开接口

### CLI：`python -m kernel_gen.tools.ircheck [-irdump] [-emitc{target=<target>}] <case-file>`

功能说明：

- 运行一个 case 文件并在标准输出打印 `true/false`。
- 当文件包含 `// -----` 时，按 case block 顺序执行。
- 当显式提供 `-emitc{target=<target>}` 时，compile steps 完成后改为对目标源码文本执行 `CHECK*`。

参数说明：

- `-irdump (flag)`：可选，导出每个 case 的逐步 IR。
- `-emitc{target=<target>} (flag)`：可选，要求 compile steps 后把匹配对象切换为目标源码文本；`target` 只接受 `cpu`、`npu_demo`。
- `<case-file> (str)`：单个文本文件路径。

返回与限制：

- 退出码：
  - `0`：检查通过
  - `1`：检查不通过
  - `2`：解析失败、参数不支持、pass/pipeline 执行失败、或 `emitc` 生成失败

### `parse_ircheck_file(path: str) -> IrcheckCase`

功能说明：

- 从磁盘读取单个 case 文件，解析出 `compile_args`、`checks` 与 `input_ir`。

注意事项：

- 文件结构由两部分组成：
  1. 文件起始处的头部注释区：连续的 `// ...` 行
  2. 输入 IR 正文：从第一行非 `//` 开头的行起，到文件结束
- 头部注释区内：
  - `COMPILE_ARGS:` 允许出现一次且必须出现一次
  - `CHECK:` / `CHECK-NOT:` / `CHECK-NEXT:` 可出现零次或多次，按出现顺序保存
  - 非上述指令的注释行允许存在，解析时忽略
- `COMPILE_ARGS:` 的参数串去掉首尾空白后不得为空。
- `CHECK:` / `CHECK-NOT:` / `CHECK-NEXT:` 的检查文本去掉首尾空白后都不得为空。
- `CHECK-NEXT:` 不得作为第一条正向检查出现。
- 全部 `CHECK*` 指令共用以下变量语法验证规则：
  - `[[NAME:REGEX]]` 表示定义变量 `NAME` 并用 `REGEX` 捕获该段文本；
  - `[[NAME]]` 表示引用先前已捕获的变量 `NAME`，按字面量匹配；
  - 同一 case 内，变量名只能定义一次；
  - 引用变量时，变量定义必须先于当前指令出现；
  - `CHECK-NOT:` 中出现 `[[NAME:REGEX]]` 必须返回解析失败；
  - `{reg}` / `{val}` / `{dim}` / `{int}` 仅在 `[[NAME:REGEX]]` 的 `REGEX` 段内展开。
- 若输入 IR 正文在去掉空白后为空，必须返回解析失败。
- `parse_ircheck_file` 只处理单 case；若文本包含 `// -----` 多 case 分隔符，必须返回 `IrcheckParseError: invalid ircheck header`。

返回与限制：

- 失败时必须抛出异常，且错误信息前缀为下述之一：
  - `IrcheckParseError: invalid ircheck header`
  - `IrcheckParseError: missing input ir`
  - `IrcheckParseError: invalid regex check`
  - `IrcheckParseError: undefined regex variable`
  - `IrcheckParseError: duplicate regex variable`
  - `IrcheckParseError: CHECK-NOT cannot define variables`

### `run_ircheck_file(path: str, *, irdump: bool = False, emitc_target: str | None = None) -> IrcheckResult`

功能说明：

- 读取文件、执行 pass/pipeline、打印规范化 IR，并对规范化 IR 执行检查指令。
- 若文件中存在 `// -----` 分隔符，按 case block 顺序执行。

返回与限制：

- 若 case 文本解析失败，返回 `ok=False`，`exit_code=2`，且 `message` 前缀为：
  - `IrcheckParseError: invalid ircheck header`
  - `IrcheckParseError: missing input ir`
  - `IrcheckParseError: invalid regex check`
  - `IrcheckParseError: undefined regex variable`
  - `IrcheckParseError: duplicate regex variable`
  - `IrcheckParseError: CHECK-NOT cannot define variables`
- 若 `COMPILE_ARGS` 不支持，返回 `ok=False`，`exit_code=2`，且 `message` 前缀为：
  - `IrcheckCompileArgsError: unsupported compile args`
- 若 pass/pipeline 执行抛错或返回不可打印的对象，返回 `ok=False`，`exit_code=2`，且 `message` 前缀为：
  - `IrcheckRunError: pass execution failed`
- 若 `emitc` 生成抛错、`emitc_target` 不受支持、或 target 与当前 IR 结构不兼容，返回 `ok=False`，`exit_code=2`，且 `message` 前缀为：
  - `IrcheckEmitCError: emit_c generation failed`
- 若匹配失败，返回 `ok=False`，`exit_code=1`，且 `message` 前缀为：
  - `IrcheckMatchError: CHECK not found`
  - `IrcheckMatchError: CHECK-NEXT not found on next line`
  - `IrcheckMatchError: CHECK-NOT matched forbidden text`

### `run_ircheck_text(text: str, source_path: str | None = None, emitc_target: str | None = None) -> IrcheckResult`

功能说明：

- 直接运行一段 case 文本，其语义与 `run_ircheck_file` 一致。
- 支持 `// -----` 多 case 分隔，执行语义与 `run_ircheck_file` 完全一致。

### 数据对象：`IrcheckCase` / `CheckDirective` / `IrcheckResult`

参数说明：

- `IrcheckCase` 建议字段：
  - `compile_args (str)`
  - `checks (list[CheckDirective])`
  - `input_ir (str)`
  - `source_path (str|None)`
- `CheckDirective` 建议字段：
  - `kind (Literal["CHECK", "CHECK-NEXT", "CHECK-NOT"])`
  - `text (str)`
  - `line_no (int)`
- `IrcheckResult` 建议字段：
  - `ok (bool)`
  - `exit_code (int)`
  - `actual_ir (str)`
  - `failed_check (CheckDirective|None)`
  - `message (str|None)`

## 检查语义

功能说明：

- 定义 `CHECK:` / `CHECK-NEXT:` / `CHECK-NOT:` 在 `actual_ir` 上的匹配规则。

注意事项：

- 匹配按“行”进行：把 `actual_ir` 视为按换行符拆分的行序列，每条指令都只在单行上匹配。
- `CHECK:` / `CHECK-NEXT:` / `CHECK-NOT:` 在单行文本上做“字面量 + 局部变量片段”匹配：
  - 非 `[[...]]` 的普通文本都按字面量解释；
  - `[[NAME:REGEX]]` 片段内部的 `REGEX` 仍按 regex 解释。
- 变量处理顺序固定为：
  1. 先读取当前 case 已成功捕获的变量表；
  2. 把 `[[NAME]]` 替换为 `re.escape(value)` 形式的字面量匹配；
  3. 把 `[[NAME:REGEX]]` 转成记录命中原文的捕获片段，并在其中展开 `{reg}` / `{val}` / `{dim}` / `{int}`；
  4. 普通文本一律按字面量转义；
  5. 当前指令匹配成功后，才把本条新定义的变量写回变量表。
- 指令按在 case 文件中的出现顺序依次处理；`CHECK-NOT` 不改变后续正向检查的搜索起点。

返回与限制：

- 正向检查命中规则：
  - 初始 `last_positive_line = None`。
  - `CHECK:`：
    - 令 `start = 0`，或 `last_positive_line + 1`；
    - 从 `lines[start:]` 中按行向后查找第一条满足模式的行；
    - 若找不到，则失败，错误短语为 `IrcheckMatchError: CHECK not found`。
  - `CHECK-NEXT:`：
    - 该指令只能在 `last_positive_line is not None` 时出现；
    - 要求下一行存在且满足给定模式；
    - 若不命中，则失败，错误短语为 `IrcheckMatchError: CHECK-NEXT not found on next line`。
- `CHECK-NOT:` 命中规则：
  - 以区间约束的方式生效，约束区间由其两侧最近的正向检查命中行决定。
  - 若 `CHECK-NOT` 违反禁止区间，则失败，错误短语为 `IrcheckMatchError: CHECK-NOT matched forbidden text`。

## 用户文档

- 一个 case file 由两部分组成：
  - 头部注释区：文件起始处连续的 `// ...` 行，包含恰好一条 `COMPILE_ARGS:` 与零到多条 `CHECK*:` 指令；
  - 输入 IR 正文：从第一行非 `//` 开头的行起，到文件结束。
- 单文件多 case 写法：
  - 使用独占一行的 `// -----` 分隔相邻 case block；
  - 每个 block 都必须包含自己的 `COMPILE_ARGS:` 与输入 IR；
  - 分隔符前后不允许出现空 block。
- 推荐写法：
  - 先用 `CHECK:` 选择一个稳定锚点，再用 `CHECK:` / `CHECK-NEXT:` 逐步收紧局部相邻关系；
  - 用 `CHECK-NOT:` 表达“在两条正向检查之间不得出现”的否定约束；
  - 当只需要在固定文本中局部捕获/复用 SSA 名、维度名、符号名时，优先使用 `CHECK*` 内的 `[[NAME:REGEX]]` / `[[NAME]]`。

### 最小示例

```mlir
// COMPILE_ARGS: --pass lower-nn
// CHECK: func.func @exp_kernel(%arg0 : !nn.memory<[[[M:{dim}]], [[N:{dim}]]], [[[N]], 1], f32, #nn.space<global>>) -> !nn.memory<[[[M]], [[N]]], [[[N]], 1], f32, #nn.space<global>>
// CHECK-NEXT: %[[ALLOC:{reg}]] = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[[[M]], [[N]]], [[[N]], 1], f32, #nn.space<global>>
// CHECK-NEXT: func.return %[[ALLOC]] : !nn.memory<[[[M]], [[N]]], [[[N]], 1], f32, #nn.space<global>>

builtin.module { /* ... */ }
```

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
  - parser：能稳定解析头部注释区、提取 compile_args 与三类检查指令，并对缺失/重复指令、非法 regex 语法、未定义变量、重复变量、`CHECK-NOT` 非法定义变量返回稳定错误短语。
  - runner：能通过 pass registry 解析 `--pass/--pipeline` 与其 options 形式并执行，输出 `IrcheckResult` 的 `ok/exit_code/message` 行为与本文件一致；支持多 case 顺序执行与 fail-fast。
  - matcher：能按本文件“检查语义”规则稳定处理 `CHECK/CHECK-NEXT/CHECK-NOT` 的顺序、相邻、区间与变量复用约束，并在失败时返回稳定错误短语。
