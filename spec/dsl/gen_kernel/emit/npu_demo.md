# npu_demo.md

## 功能简介

- 定义 `target="npu_demo"` 的节点级 emit 实现目录合同。
- 当前实现目录按 `dialect/op.py`、`type/`、`include.py` 展开。
- `npu_demo` 下每个可发射 op 必须对应一个独立实现文件，并通过注册体系接入；不得再回退到 `ops.py`、`values.py`、`core.py` 这类聚合大文件。

## API 列表

- 无公开 API。

## 文档信息

- 创建者：`OpenAI Codex`
- 最后一次更改：`OpenAI Codex`
- `spec`：[`spec/dsl/gen_kernel/emit/npu_demo.md`](../../../../spec/dsl/gen_kernel/emit/npu_demo.md)
- `功能实现`：
  - [`kernel_gen/dsl/gen_kernel/emit/npu_demo/__init__.py`](../../../../kernel_gen/dsl/gen_kernel/emit/npu_demo/__init__.py)
  - [`kernel_gen/dsl/gen_kernel/emit/npu_demo/include.py`](../../../../kernel_gen/dsl/gen_kernel/emit/npu_demo/include.py)
- `test`：[`test/dsl/gen_kernel/emit/test_emit.py`](../../../../test/dsl/gen_kernel/emit/test_emit.py)

## 依赖

- [`spec/dsl/gen_kernel/emit/npu_demo/include.md`](../../../../spec/dsl/gen_kernel/emit/npu_demo/include.md)
- [`spec/dsl/gen_kernel/emit/npu_demo/arch/__init__.md`](../../../../spec/dsl/gen_kernel/emit/npu_demo/arch/__init__.md)
- [`spec/dsl/gen_kernel/emit/npu_demo/dma/__init__.md`](../../../../spec/dsl/gen_kernel/emit/npu_demo/dma/__init__.md)
- [`spec/dsl/gen_kernel/emit/npu_demo/kernel/__init__.md`](../../../../spec/dsl/gen_kernel/emit/npu_demo/kernel/__init__.md)
- [`spec/dsl/gen_kernel/emit/npu_demo/nn/__init__.md`](../../../../spec/dsl/gen_kernel/emit/npu_demo/nn/__init__.md)
- [`spec/dsl/gen_kernel/emit/npu_demo/symbol/__init__.md`](../../../../spec/dsl/gen_kernel/emit/npu_demo/symbol/__init__.md)
- [`spec/dsl/gen_kernel/emit/npu_demo/tuner/__init__.md`](../../../../spec/dsl/gen_kernel/emit/npu_demo/tuner/__init__.md)
- [`spec/dsl/gen_kernel/emit/npu_demo/type/__init__.md`](../../../../spec/dsl/gen_kernel/emit/npu_demo/type/__init__.md)

## 目标

- 把 `npu_demo` 节点级实现按实际目录结构拆成稳定 spec 子树。
- 明确 `npu_demo` emitter 的实现粒度以“每个 op 一个实现文件”为准。
- 固定 `target="npu_demo"` 的 target-specific 逻辑只能通过注册体系接入。

## 限制与边界

- 本模块不额外公开 API。
- 目录中的实现只通过上层 `emit` 注册体系生效。
- 每个可发射 op 必须独占一个实现文件，路径形态固定为 `emit/npu_demo/<dialect>/<op>.py`。
- 不得再新增 `ops.py`、`values.py`、`core.py`、`function.py`、`module.py` 这类聚合多个 op 行为的 target 大文件。
- 非公开 helper 必须使用 `_` 前缀，且不得跨文件直接调用。

## 测试

- 测试文件：[`test/dsl/gen_kernel/emit/test_emit.py`](../../../../test/dsl/gen_kernel/emit/test_emit.py)
- 执行命令：`pytest -q test/dsl/gen_kernel/emit/test_emit.py`
- 测试目标：`npu_demo` target 节点级 emit 行为稳定
