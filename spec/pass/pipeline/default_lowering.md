# default_lowering.md

## 功能简介

- 定义默认 lowering pipeline 的公开合同与 pass 顺序。
- 公开 builder：`build_default_lowering_pipeline()`。

## 文档信息

- 创建者：`咯咯咯`
- 最后一次更改：`咯咯咯`（2026-04-11）
- `spec`：[`spec/pass/pipeline/default_lowering.md`](../../../spec/pass/pipeline/default_lowering.md)
- `功能实现`：[`kernel_gen/passes/pipeline/default_lowering.py`](../../../kernel_gen/passes/pipeline/default_lowering.py)
- `test`：[`test/pass/test_pipeline_default_lowering.py`](../../../test/pass/test_pipeline_default_lowering.py)

## 依赖

- Pass 管理与排序：[`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)
- 注册表：[`spec/pass/registry.md`](../../../spec/pass/registry.md)

## 术语

- `default-lowering`：默认 pipeline 名称。

## 目标

- 提供可复用的默认 lowering pipeline 构造器。
- 明确 pass 顺序，保证后续工具与测试有一致入口。

## 限制与边界

- builder 必须返回 `PassManager`。
- builder 必须通过 `register_pipeline("default-lowering")` 注册。
- registry 只负责注册与查询，不承载 builder 实现。

## 公开接口

### `build_default_lowering_pipeline() -> PassManager`

功能说明：

- 构造默认 lowering pipeline，并返回 `PassManager`。

参数说明：

- 无参数。

使用示例：

```python
from kernel_gen.passes.pipeline import build_default_lowering_pipeline

pm = build_default_lowering_pipeline()
module = pm.run(module)
```

注意事项：

- pipeline 名称为 `default-lowering`。
- pass 顺序必须为：
  1. `DecompassPass`
  2. `LowerNnToKernelPass`
  3. `BufferResultsToOutParamsPass`
  4. `LowerDmaMemoryHierarchyPass`

返回与限制：

- 返回 `PassManager` 实例。

## 测试

- 测试文件：[`test/pass/test_pipeline_default_lowering.py`](../../../test/pass/test_pipeline_default_lowering.py)
- 执行命令：`pytest -q test/pass/test_pipeline_default_lowering.py`
- 测试目标：
  - pipeline 名称与 pass 顺序可验证。
  - builder 返回 `PassManager`。
