# __init__.md

## 功能简介

- 本目录承载 `npu_demo` target 下 `tuner.*` 节点的 emit 实现。
- 当前仅覆盖 `tuner.cost`。

## API 列表

- 无公开 API。

## 文档信息

- 创建者：`OpenAI Codex`
- 最后一次更改：`OpenAI Codex`
- `spec`：[`spec/dsl/gen_kernel/emit/npu_demo/tuner/__init__.md`](../../../../../../spec/dsl/gen_kernel/emit/npu_demo/tuner/__init__.md)
- `功能实现`：[`kernel_gen/dsl/gen_kernel/emit/npu_demo/tuner/cost.py`](../../../../../../kernel_gen/dsl/gen_kernel/emit/npu_demo/tuner/cost.py)
- `test`：[`test/dsl/gen_kernel/emit/test_emit.py`](../../../../../../test/dsl/gen_kernel/emit/test_emit.py)

## 依赖

- [`spec/dialect/tuner.md`](../../../../../../spec/dialect/tuner.md)
- [`spec/include/api/cost/Core.md`](../../../../../../spec/include/api/cost/Core.md)
- [`spec/include/api/cost/Kernel.md`](../../../../../../spec/include/api/cost/Kernel.md)
- [`spec/include/api/cost/Dma.md`](../../../../../../spec/include/api/cost/Dma.md)

## 目标

- 收口 `tuner.cost` 在 `npu_demo` 下的节点级 emit 规则。

## 限制与边界

- 当前仅定义 `tuner.cost`，不扩展其他 `tuner.*` 节点。

## 测试

- 测试文件：[`test/dsl/gen_kernel/emit/test_emit.py`](../../../../../../test/dsl/gen_kernel/emit/test_emit.py)
- 执行命令：`pytest -q test/dsl/gen_kernel/emit/test_emit.py`
- 测试目标：`tuner.cost` emit 稳定
