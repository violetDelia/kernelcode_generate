# __init__.md

## 功能简介

- 本目录承载 `npu_demo` target 下 `arch.*` 节点的 emit 实现。
- 当前覆盖：
  - `get_dynamic_memory`
  - `get_thread_id`
  - `get_thread_num`

## API 列表

- 无公开 API。

## 文档信息

- 创建者：`OpenAI Codex`
- 最后一次更改：`OpenAI Codex`
- `spec`：[`spec/dsl/gen_kernel/emit/npu_demo/arch/__init__.md`](../../../../../../spec/dsl/gen_kernel/emit/npu_demo/arch/__init__.md)
- `功能实现`：
  - [`kernel_gen/dsl/gen_kernel/emit/npu_demo/arch/get_dynamic_memory.py`](../../../../../../kernel_gen/dsl/gen_kernel/emit/npu_demo/arch/get_dynamic_memory.py)
  - [`kernel_gen/dsl/gen_kernel/emit/npu_demo/arch/get_thread_id.py`](../../../../../../kernel_gen/dsl/gen_kernel/emit/npu_demo/arch/get_thread_id.py)
  - [`kernel_gen/dsl/gen_kernel/emit/npu_demo/arch/get_thread_num.py`](../../../../../../kernel_gen/dsl/gen_kernel/emit/npu_demo/arch/get_thread_num.py)
- `test`：[`test/dsl/gen_kernel/emit/test_emit.py`](../../../../../../test/dsl/gen_kernel/emit/test_emit.py)

## 依赖

- [`spec/dialect/arch.md`](../../../../../../spec/dialect/arch.md)

## 目标

- 收口 `arch` 查询类节点在 `npu_demo` 下的文本映射。

## 限制与边界

- 本目录只通过注册体系生效。

## 测试

- 测试文件：[`test/dsl/gen_kernel/emit/test_emit.py`](../../../../../../test/dsl/gen_kernel/emit/test_emit.py)
- 执行命令：`pytest -q test/dsl/gen_kernel/emit/test_emit.py`
- 测试目标：`arch` 查询类节点 emit 稳定
