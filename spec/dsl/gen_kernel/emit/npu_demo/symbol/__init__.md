# __init__.md

## 功能简介

- 本目录承载 `npu_demo` target 下 `symbol.*` 节点的 emit 实现。
- 当前覆盖：
  - `binary`
  - `cast`
  - `const`
  - `for_loop`
  - `get_dim`
  - `get_stride`
  - `to_float`

## API 列表

- 无公开 API。

## 文档信息

- 创建者：`OpenAI Codex`
- 最后一次更改：`OpenAI Codex`
- `spec`：[`spec/dsl/gen_kernel/emit/npu_demo/symbol/__init__.md`](../../../../../../spec/dsl/gen_kernel/emit/npu_demo/symbol/__init__.md)
- `功能实现`：[`kernel_gen/dsl/gen_kernel/emit/npu_demo/symbol`](../../../../../../kernel_gen/dsl/gen_kernel/emit/npu_demo/symbol)
- `test`：[`test/dsl/gen_kernel/emit/test_emit.py`](../../../../../../test/dsl/gen_kernel/emit/test_emit.py)

## 依赖

- [`spec/dialect/symbol.md`](../../../../../../spec/dialect/symbol.md)

## 目标

- 收口 `symbol` family 在 `npu_demo` 下的节点级 emit 规则。

## 限制与边界

- 本目录只通过注册体系生效。

## 测试

- 测试文件：[`test/dsl/gen_kernel/emit/test_emit.py`](../../../../../../test/dsl/gen_kernel/emit/test_emit.py)
- 执行命令：`pytest -q test/dsl/gen_kernel/emit/test_emit.py`
- 测试目标：`symbol` family emit 稳定
