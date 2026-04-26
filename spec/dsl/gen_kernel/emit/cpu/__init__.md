# __init__.md

## 功能简介

- 本目录承载 `target="cpu"` 的节点级 emit 实现。
- 当前只有 `__init__.py` 单入口文件。

## API 列表

- 无公开 API。

## 文档信息

- 创建者：`OpenAI Codex`
- 最后一次更改：`OpenAI Codex`
- `spec`：[`spec/dsl/gen_kernel/emit/cpu/__init__.md`](../../../../../spec/dsl/gen_kernel/emit/cpu/__init__.md)
- `功能实现`：[`kernel_gen/dsl/gen_kernel/emit/cpu/__init__.py`](../../../../../kernel_gen/dsl/gen_kernel/emit/cpu/__init__.py)
- `test`：[`test/dsl/gen_kernel/emit/test_emit.py`](../../../../../test/dsl/gen_kernel/emit/test_emit.py)

## 依赖

- [`spec/dsl/gen_kernel/emit.md`](../../../../../spec/dsl/gen_kernel/emit.md)

## 目标

- 承接 `cpu` target 的节点级 emit 规则。

## 限制与边界

- 本目录不对外暴露额外公开 API，只通过上层 `emit` 与注册体系生效。

## 测试

- 测试文件：[`test/dsl/gen_kernel/emit/test_emit.py`](../../../../../test/dsl/gen_kernel/emit/test_emit.py)
- 执行命令：`pytest -q test/dsl/gen_kernel/emit/test_emit.py`
- 测试目标：`cpu` target 节点级 emit 行为稳定
