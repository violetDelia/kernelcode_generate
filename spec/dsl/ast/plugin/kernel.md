# kernel.md

## 功能简介

定义 `kernel_gen.dsl.ast.plugin.kernel` 的 builtin 注册合同。导入本模块时，它把 `kernel_gen.operation.kernel` 公开 helper 注册到 DSL AST builtin registry，使 Python DSL 中的 out-first kernel helper 能被解析为 kernel AST 节点。

## API 列表

- 无公开函数或类；本文件只提供导入副作用。

## 文档信息

- `spec`：`spec/dsl/ast/plugin/kernel.md`
- `功能实现`：`kernel_gen/dsl/ast/plugin/kernel.py`
- `test`：`test/dsl/ast/plugin/test_kernel.py`
- `expectation`：`expectation/dsl/mlir_gen/dialect/kernel/**`

## 依赖

- `spec/operation/kernel.md`：公开 helper 签名。
- `spec/dsl/ast/plugin/registry.md`：`dsl_builtin(...)` 与 `lookup_builtin(...)`。
- `spec/dsl/ast/nodes/kernel.md`：目标 AST 节点。

## 模块行为

- `kernel.binary_elewise(out, lhs, rhs, *, kind=KernelBinaryElewiseKind.X)` 注册到 `KernelBinaryElewiseAST`。
- `kernel.add/sub/mul/div/truediv/eq/ne/lt/le/gt/ge(out, lhs, rhs)` 注册到对应固定 kind AST 节点。
- `kernel.matmul(out, lhs, rhs)` 注册到 `KernelMatmulAST`。
- `kernel.img2col1d(out, input_value, k, s=1, d=1, p_left=0, p_right=0)` 注册到 `KernelImg2Col1dAST`。
- `kernel.img2col2d(out, input_value, kh, kw, sh=1, sw=1, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)` 注册到 `KernelImg2Col2dAST`。

## 注意事项

- 本模块不导出公开 helper；调用方只通过 `kernel_gen.operation.kernel` 与 `kernel_gen.dsl.ast.plugin.lookup_builtin(...)` 观察注册效果。
- `binary_elewise` 的 `kind` 必须是 `KernelBinaryElewiseKind`，字符串不是公开输入。
- `kernel.add/sub/...` 只接受 `out/lhs/rhs` 三个位置参数，不接受 keyword。
- `kernel.matmul` 不接受 `memoryspace` 或其它 keyword。
- `img2col1d/2d` 的窗口参数可用位置参数或本 spec 中列出的 keyword；未列出的 keyword 必须拒绝。
- `img2col1d/2d` 的同一窗口参数不得同时以位置参数和 keyword 传入。

## 测试

- 测试文件：`test/dsl/ast/plugin/test_kernel.py`
- 执行命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/ast/plugin/test_kernel.py`

### 测试目标

- 验证导入 plugin 后，`kernel_gen.operation.kernel` 公开 helper 均可通过 builtin registry 查到。
- 验证 parse_function 能把 out-first kernel helper 构造成对应 statement AST。
- 验证 `binary_elewise` 只接受 `KernelBinaryElewiseKind`，不接受字符串 kind。
- 验证 `img2col1d/2d` 的窗口参数只接受合法位置/keyword 组合，重复传参和未知 keyword 必须失败。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-DSL-AST-PLUGIN-KERNEL-001 | 公开入口 | helper registered | 导入 plugin 包。 | 调用 `lookup_builtin(...)`。 | `kernel.add`、`binary_elewise`、`matmul`、`img2col2d` 均有注册项。 | `test_kernel_plugin_registers_public_helpers` |
| TC-DSL-AST-PLUGIN-KERNEL-002 | 解析/打印 | statement helper parse | 准备公开 `Memory` 入参。 | `parse_function(...)`。 | 生成对应 kernel statement AST；`return kernel.matmul(...)` 被视为 returns None。 | `test_kernel_plugin_parse_function_builds_statement_nodes` |
| TC-DSL-AST-PLUGIN-KERNEL-003 | 解析/打印 | img2col2d kwargs | 准备 `kh/kw` 和 padding keyword。 | `parse_function(...)`。 | 生成 `KernelImg2Col2dAST`。 | `test_kernel_plugin_parses_img2col2d_keyword_parameters` |
| TC-DSL-AST-PLUGIN-KERNEL-004 | 边界/异常 | non API shapes rejected | 准备 `kernel.add(..., kind=...)` 与字符串 kind。 | `parse_function(...)`。 | 按公开错误语义抛 `KernelCodeError`。 | `test_kernel_plugin_rejects_non_api_call_shapes` |
| TC-DSL-AST-PLUGIN-KERNEL-005 | 边界/异常 | img2col duplicate args rejected | 准备 `img2col1d/2d` 同时以位置参数和 keyword 传入同一窗口参数。 | `parse_function(...)`。 | 抛 `KernelCodeError`，错误文本包含 `position and keyword`。 | `test_kernel_plugin_rejects_img2col_duplicate_positional_keyword_parameters` |
