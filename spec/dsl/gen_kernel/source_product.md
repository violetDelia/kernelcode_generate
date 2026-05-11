# source_product.md

## 功能简介

- 定义 `ModuleOp` emit handler 的源码产物合同。
- 单文件源码用 `str` 表示。
- 多文件源码用 `Mapping[str, str]` 表示，并由 emit registry 编码为 SourceBundle aggregate string。

## API 列表

- `emit_c_impl(*types: type[Any], target: str | None = None, override: bool = False) -> Callable[[OpHandler], OpHandler]`
- `emit_c(obj: SSAValue | Operation | func.FuncOp | ModuleOp, ctx: EmitCContext) -> str`
- `gen_kernel(obj: Operation | func.FuncOp | ModuleOp, ctx: EmitCContext) -> str`

## 文档信息

- `spec`：`spec/dsl/gen_kernel/source_product.md`
- `功能实现`：`kernel_gen/dsl/gen_kernel/emit/register.py`
- `功能实现`：`kernel_gen/dsl/gen_kernel/gen_kernel.py`
- `test`：`test/dsl/gen_kernel/test_module_emitter.py`
- `test`：`test/dsl/gen_kernel/test_source_bundle.py`

## 依赖

- [`spec/dsl/gen_kernel/emit/register.md`](emit/register.md)
- [`spec/dsl/gen_kernel/source_bundle.md`](source_bundle.md)
- [`spec/dsl/gen_kernel/gen_kernel.md`](gen_kernel.md)

## 目标

- 允许第三方 backend 用同一个 `emit_c_impl(ModuleOp, target=...)` 入口返回单文件或多文件源码。
- 避免新增 `emit_c_module_impl` 平行公开 API。
- 让 `gen_kernel(..., ctx)` 保持公开签名不变，同时能 dump 多文件 artifact。

## 模块边界

- 只允许 `str` 或 `Mapping[str, str]` 作为 `ModuleOp` handler 返回值。
- `Mapping` key 是 POSIX 风格安全相对路径；value 是源码文本。
- 非字符串内容必须以 `source_product_invalid` 失败。
- 非法路径、重复路径或包含 SourceBundle marker 行的内容必须以 `source_bundle_malformed` 失败。
- SourceBundle encode/decode/write/serialize/parse helper 不公开。

## API详细说明

### `emit_c_impl(*types: type[Any], target: str | None = None, override: bool = False) -> Callable[[OpHandler], OpHandler]`

- 参数：
  - `types`：要注册的 operation 类型；`ModuleOp` handler 可返回 SourceProduct。
  - `target`：target 名称；`None` 表示默认注册表。
  - `override`：是否允许覆盖已有 handler。
- 返回值：装饰器。
- 功能说明：当注册 `ModuleOp` handler 时，handler 返回值可为 `str | Mapping[str, str]`。
- 使用示例：

  ```python
  from xdsl.dialects.builtin import ModuleOp

  from kernel_gen.dsl.gen_kernel.emit.register import emit_c_impl

  @emit_c_impl(ModuleOp, target="dummy_generic")
  def emit_module(op, ctx):
      return {
          "kernel.cpp": "void kernel() {}\\n",
          "include/kernel.h": "#pragma once\\n",
      }
  ```
- 注意事项：handler 返回类型不是 `str` 或 `Mapping[str, str]` 时以 `source_product_invalid` 失败；`Mapping` 中 path 非法、path 重复或 content 含完整 SourceBundle marker 行时以 `source_bundle_malformed` 失败。

## 测试

- 测试文件：`test/dsl/gen_kernel/test_module_emitter.py`
- 测试文件：`test/dsl/gen_kernel/test_source_bundle.py`
- 执行命令：`pytest -q test/dsl/gen_kernel/test_module_emitter.py test/dsl/gen_kernel/test_source_bundle.py`

### 测试目标

- 验证 `ModuleOp` handler 返回字符串源码。
- 验证 `ModuleOp` handler 返回多文件 `Mapping[str, str]`。
- 验证非法返回类型与非法 SourceBundle 内容失败。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TG-SOURCE-PRODUCT-001 | 单文件源码 | handler 返回 `str`。 | 注册 dummy backend。 | 调用 `emit_c(module_op, ctx)`。 | 返回普通源码字符串。 | `test_module_handler_returns_single_source_string` |
| TG-SOURCE-PRODUCT-002 | 多文件源码 | handler 返回 `Mapping[str, str]`。 | 注册 dummy backend。 | 调用 `emit_c(module_op, ctx)`。 | 返回 SourceBundle aggregate string。 | `test_module_handler_returns_mapping_as_source_bundle` |
| TG-SOURCE-PRODUCT-003 | 错误语义 | handler 返回非法类型。 | 注册非法 handler。 | 调用 `emit_c(module_op, ctx)`。 | 抛出 `source_product_invalid`。 | `test_module_handler_rejects_invalid_source_product` |
