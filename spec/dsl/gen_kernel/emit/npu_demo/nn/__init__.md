# __init__.md

## 功能简介

- 本目录承载 `npu_demo` target 下 `nn.*` 节点的 emit 实现。
- 当前仅覆盖 `nn.add` 的节点级 emit。

## API 列表

- 无公开 API。

## 文档信息

- 创建者：`OpenAI Codex`
- 最后一次更改：`OpenAI Codex`
- `spec`：[`spec/dsl/gen_kernel/emit/npu_demo/nn/__init__.md`](../../../../../../spec/dsl/gen_kernel/emit/npu_demo/nn/__init__.md)
- `功能实现`：[`kernel_gen/dsl/gen_kernel/emit/npu_demo/nn/add.py`](../../../../../../kernel_gen/dsl/gen_kernel/emit/npu_demo/nn/add.py)
- `test`：[`test/dsl/gen_kernel/emit/test_emit.py`](../../../../../../test/dsl/gen_kernel/emit/test_emit.py)

## 依赖

- [`spec/dialect/nn.md`](../../../../../../spec/dialect/nn.md)

## 目标

- 收口 `nn.add` 在 `npu_demo` 下的节点级 emit 规则。

## 限制与边界

- 当前不承诺 `nn` family 其他节点的公开 emit 合同。

## 测试

- 测试文件：[`test/dsl/gen_kernel/emit/test_emit.py`](../../../../../../test/dsl/gen_kernel/emit/test_emit.py)
- 执行命令：`pytest -q test/dsl/gen_kernel/emit/test_emit.py`
- 测试目标：`nn.add` 节点 emit 稳定
