# __init__.md

## 功能简介

- 本目录承载 `npu_demo` target 下 `kernel.*` 节点的 emit 实现。
- 当前覆盖：
  - `binary_elewise`
  - `exp`
  - `img2col1d`
  - `img2col2d`
  - `matmul`
  - `reduce`
  - `select`

## API 列表

- 无公开 API。

## 文档信息

- 创建者：`OpenAI Codex`
- 最后一次更改：`OpenAI Codex`
- `spec`：[`spec/dsl/gen_kernel/emit/npu_demo/kernel/__init__.md`](../../../../../../spec/dsl/gen_kernel/emit/npu_demo/kernel/__init__.md)
- `功能实现`：[`kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel`](../../../../../../kernel_gen/dsl/gen_kernel/emit/npu_demo/kernel)
- `test`：[`test/dsl/gen_kernel/emit/test_emit.py`](../../../../../../test/dsl/gen_kernel/emit/test_emit.py)

## 依赖

- [`spec/dialect/kernel.md`](../../../../../../spec/dialect/kernel.md)
- [`spec/include/api/Kernel.md`](../../../../../../spec/include/api/Kernel.md)

## 目标

- 收口 `kernel` family 在 `npu_demo` 下的节点级 emit 规则。

## 限制与边界

- 本目录只通过注册体系生效，不额外导出公开 API。

## 测试

- 测试文件：[`test/dsl/gen_kernel/emit/test_emit.py`](../../../../../../test/dsl/gen_kernel/emit/test_emit.py)
- 执行命令：`pytest -q test/dsl/gen_kernel/emit/test_emit.py`
- 测试目标：`kernel` family emit 稳定
