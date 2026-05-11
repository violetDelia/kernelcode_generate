# source_bundle.md

## 功能简介

- 定义 SourceBundle aggregate string 的公开可观测格式。
- SourceBundle 用于在 `gen_kernel(..., ctx)` 签名不变的前提下承载多文件源码。
- helper 不公开；调用方只能通过 `emit_c(...)` / `gen_kernel(...)` 观察源码文本与 dump 文件。

## API 列表

- `gen_kernel(obj: Operation | func.FuncOp | ModuleOp, ctx: EmitCContext) -> str`
- `emit_c(obj: SSAValue | Operation | func.FuncOp | ModuleOp, ctx: EmitCContext) -> str`

## 文档信息

- `spec`：`spec/dsl/gen_kernel/source_bundle.md`
- `功能实现`：`kernel_gen/dsl/gen_kernel/gen_kernel.py`
- `功能实现`：`kernel_gen/dsl/gen_kernel/emit/register.py`
- `test`：`test/dsl/gen_kernel/test_source_bundle.py`

## 依赖

- [`spec/dsl/gen_kernel/source_product.md`](source_product.md)
- [`spec/dsl/gen_kernel/gen_kernel.md`](gen_kernel.md)
- [`spec/core/config.md`](../../core/config.md)

## 目标

- 让第三方 backend 可以返回多文件源码。
- 让 `dump_dir` 同时写出 aggregate `source.cpp` 和 artifact 文件。
- 防止 artifact 路径逃逸 dump 目录。

## 模块边界

- aggregate marker 格式固定为 `// __KG_BUNDLE_FILE__:<relative/path>`。
- artifact path 必须是安全相对路径；不得为空、绝对路径、包含 `..`、反斜杠、NUL 或重复。
- artifact content 中不得包含完整 SourceBundle marker 行。
- `dump_dir` 写出时必须拒绝 symlink 逃逸。

## API详细说明

### `gen_kernel(obj: Operation | func.FuncOp | ModuleOp, ctx: EmitCContext) -> str`

- 参数：
  - `obj`：待生成源码的 IR 对象。
  - `ctx`：公开 EmitC 上下文。
- 返回值：单文件源码字符串或 SourceBundle aggregate string。
- 功能说明：当 `emit_c(...)` 返回 SourceBundle aggregate string 且 `dump_dir` 非空时，写出 `source.cpp` 和所有 artifact。
- 使用示例：

  ```python
  from kernel_gen.core.config import set_dump_dir, set_target
  from kernel_gen.dsl.gen_kernel import gen_kernel
  from kernel_gen.dsl.gen_kernel.emit_context import EmitCContext

  set_target("dummy_generic")
  set_dump_dir("/tmp/kernel-dump")
  source = gen_kernel(module_op, EmitCContext())
  ```
- 注意事项：`gen_kernel(...)` 不公开 SourceBundle parser；非法 bundle 或 dump 路径必须抛出 `KernelCodeError`。

## 测试

- 测试文件：`test/dsl/gen_kernel/test_source_bundle.py`
- 执行命令：`pytest -q test/dsl/gen_kernel/test_source_bundle.py`

### 测试目标

- 验证 SourceBundle dump 写出 aggregate 与 artifact。
- 验证 marker 内容、非法路径和 symlink 逃逸被拒绝。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TG-SOURCE-BUNDLE-001 | dump 写出 | 多文件源码写入 dump 目录。 | 设置 `dump_dir`。 | 调用 `gen_kernel(module_op, ctx)`。 | `source.cpp` 与 artifact 文件存在。 | `test_source_bundle_dump_writes_aggregate_and_artifacts` |
| TG-SOURCE-BUNDLE-002 | 错误语义 | artifact 内容包含 marker 行。 | 注册返回非法内容的 handler。 | 调用 `gen_kernel(module_op, ctx)`。 | 抛出 `source_bundle_malformed`。 | `test_source_bundle_rejects_marker_line_in_content` |
| TG-SOURCE-BUNDLE-003 | 错误语义 | artifact path 非法。 | 注册返回非法路径的 handler。 | 调用 `gen_kernel(module_op, ctx)`。 | 抛出 `source_bundle_malformed`。 | `test_source_bundle_rejects_malformed_artifact_path` |
| TG-SOURCE-BUNDLE-004 | 错误语义 | dump 目录下存在逃逸 symlink。 | 创建 artifact symlink 指向 dump 外。 | 调用 `gen_kernel(module_op, ctx)`。 | 抛出 `source_bundle_path_escape`。 | `test_source_bundle_dump_rejects_symlink_escape` |
