# __init__.md

## 功能简介

- 本目录承载 `npu_demo` target 下 `dma.*` 节点的 emit 实现。
- 当前覆盖：
  - `alloc`
  - `broadcast`
  - `cast`
  - `copy`
  - `deslice`
  - `fill`
  - `free`
  - `load`
  - `reshape`
  - `slice`
  - `store`
  - `transpose`
  - `view`

## API 列表

- 无公开 API。

## 文档信息

- 创建者：`OpenAI Codex`
- 最后一次更改：`OpenAI Codex`
- `spec`：[`spec/dsl/gen_kernel/emit/npu_demo/dma/__init__.md`](../../../../../../spec/dsl/gen_kernel/emit/npu_demo/dma/__init__.md)
- `功能实现`：[`kernel_gen/dsl/gen_kernel/emit/npu_demo/dma`](../../../../../../kernel_gen/dsl/gen_kernel/emit/npu_demo/dma)
- `test`：[`test/dsl/gen_kernel/emit/test_emit.py`](../../../../../../test/dsl/gen_kernel/emit/test_emit.py)

## 依赖

- [`spec/dialect/dma.md`](../../../../../../spec/dialect/dma.md)
- [`spec/include/api/Dma.md`](../../../../../../spec/include/api/Dma.md)

## 目标

- 收口 `dma` family 在 `npu_demo` 下的节点级 emit 规则。

## 限制与边界

- 本目录只定义 `npu_demo` target 的 `dma` 节点映射。

## 测试

- 测试文件：[`test/dsl/gen_kernel/emit/test_emit.py`](../../../../../../test/dsl/gen_kernel/emit/test_emit.py)
- 执行命令：`pytest -q test/dsl/gen_kernel/emit/test_emit.py`
- 测试目标：`dma` family emit 稳定
