# include.md

## 功能简介

- 定义 `target="npu_demo"` 的头文件文本注册合同。
- 当前负责把 include 文本收口到 `#include "include/npu_demo/npu_demo.h"` 与对应命名空间口径。

## API 列表

- 无公开 API。

## 文档信息

- 创建者：`OpenAI Codex`
- 最后一次更改：`OpenAI Codex`
- `spec`：[`spec/dsl/gen_kernel/emit/npu_demo/include.md`](../../../../../spec/dsl/gen_kernel/emit/npu_demo/include.md)
- `功能实现`：[`kernel_gen/dsl/gen_kernel/emit/npu_demo/include.py`](../../../../../kernel_gen/dsl/gen_kernel/emit/npu_demo/include.py)
- `test`：[`test/dsl/gen_kernel/emit/test_emit.py`](../../../../../test/dsl/gen_kernel/emit/test_emit.py)

## 依赖

- [`spec/include/npu_demo/npu_demo.md`](../../../../../spec/include/npu_demo/npu_demo.md)
- [`spec/dsl/gen_kernel/emit/register.md`](../../../../../spec/dsl/gen_kernel/emit/register.md)

## 目标

- 固定 `npu_demo` 的 include 文本来源。

## 限制与边界

- 头文件文本通过注册体系接入，不单独作为 package 公开 API 暴露。

## 测试

- 测试文件：[`test/dsl/gen_kernel/emit/test_emit.py`](../../../../../test/dsl/gen_kernel/emit/test_emit.py)
- 执行命令：`pytest -q test/dsl/gen_kernel/emit/test_emit.py`
- 测试目标：`npu_demo` include 文本稳定
