# __init__.md

## 功能简介

- 本目录承载 `npu_demo` target 下的 type / memory-space 映射注册实现。
- 当前覆盖：
  - `space.py`
  - `type.py`

## API 列表

- 无公开 API。

## 文档信息

- 创建者：`OpenAI Codex`
- 最后一次更改：`OpenAI Codex`
- `spec`：[`spec/dsl/gen_kernel/emit/npu_demo/type/__init__.md`](../../../../../../spec/dsl/gen_kernel/emit/npu_demo/type/__init__.md)
- `功能实现`：
  - [`kernel_gen/dsl/gen_kernel/emit/npu_demo/type/space.py`](../../../../../../kernel_gen/dsl/gen_kernel/emit/npu_demo/type/space.py)
  - [`kernel_gen/dsl/gen_kernel/emit/npu_demo/type/type.py`](../../../../../../kernel_gen/dsl/gen_kernel/emit/npu_demo/type/type.py)
- `test`：[`test/dsl/gen_kernel/emit/test_emit.py`](../../../../../../test/dsl/gen_kernel/emit/test_emit.py)

## 依赖

- [`spec/include/api/Memory.md`](../../../../../../spec/include/api/Memory.md)
- [`spec/include/npu_demo/npu_demo.md`](../../../../../../spec/include/npu_demo/npu_demo.md)

## 目标

- 收口 `npu_demo` target 下的 type / space 文本映射。

## 限制与边界

- 本目录只通过 `EmitCContext` 与注册体系生效。

## 测试

- 测试文件：[`test/dsl/gen_kernel/emit/test_emit.py`](../../../../../../test/dsl/gen_kernel/emit/test_emit.py)
- 执行命令：`pytest -q test/dsl/gen_kernel/emit/test_emit.py`
- 测试目标：type / space 映射稳定
