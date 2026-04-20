# pipeline README

## 功能简介

- 说明 pipeline 目录职责与命名约定，为 pass 顺序组合提供统一入口。
- pipeline builder 放在 `kernel_gen/passes/pipeline`，通过 registry 名字入口对外提供构造能力。
- 默认 pipeline 的公开合同见 `default_lowering.md`。
- `npu-demo-lowering` 的公开合同见 `npu_demo_lowering.md`。

## 文档信息

- 创建者：`咯咯咯`
- 最后一次更改：`咯咯咯`（2026-04-11）
- `spec`：[`spec/pass/pipeline/README.md`](../../../spec/pass/pipeline/README.md)
- `功能实现`：
  - [`kernel_gen/passes/pipeline/__init__.py`](../../../kernel_gen/passes/pipeline/__init__.py)
  - [`kernel_gen/passes/pipeline/default_lowering.py`](../../../kernel_gen/passes/pipeline/default_lowering.py)
  - [`kernel_gen/passes/pipeline/npu_demo_lowering.py`](../../../kernel_gen/passes/pipeline/npu_demo_lowering.py)
  - [`kernel_gen/passes/registry.py`](../../../kernel_gen/passes/registry.py)
- `test`：
  - [`test/pass/test_pipeline_default_lowering.py`](../../../test/pass/test_pipeline_default_lowering.py)
  - [`test/pass/test_pipeline_npu_demo_lowering.py`](../../../test/pass/test_pipeline_npu_demo_lowering.py)
  - [`test/pass/test_pass_registry.py`](../../../test/pass/test_pass_registry.py)

## 依赖

- Pass 管理与排序：[`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)
- 注册表：[`spec/pass/registry.md`](../../../spec/pass/registry.md)
- 默认 pipeline：[`spec/pass/pipeline/default_lowering.md`](../../../spec/pass/pipeline/default_lowering.md)
- npu-demo pipeline：[`spec/pass/pipeline/npu_demo_lowering.md`](../../../spec/pass/pipeline/npu_demo_lowering.md)

## 术语

- `pipeline name`：对外公开的 pipeline 标识字符串（如 `default-lowering`、`npu-demo-lowering`）。
- `builder`：构造并返回 `PassManager` 的函数。

## 目标

- 给出 pipeline 目录位置与命名约定，便于新增 pipeline。
- 统一通过 registry 名字入口构造 pipeline，避免散落 import 细节。

## 限制与边界

- pipeline builder 只负责构造 `PassManager`，不执行 pass。
- pipeline builder 必须通过 `register_pipeline(name)` 注册，便于统一查询。
- registry 只负责注册与查询，不承载具体 builder 实现。

## 公开接口

### `build_default_lowering_pipeline() -> PassManager`

功能说明：

- 构造默认 lowering pipeline。

参数说明：

- 无参数。

使用示例：

```python
from kernel_gen.passes.pipeline import build_default_lowering_pipeline

pm = build_default_lowering_pipeline()
module = pm.run(module)
```

注意事项：

- 具体 pass 顺序见 `default_lowering.md`。

返回与限制：

- 返回 `PassManager` 实例。

### `build_npu_demo_lowering_pipeline() -> PassManager`

功能说明：

- 构造 `npu-demo-lowering` pipeline。

参数说明：

- 无参数。

使用示例：

```python
from kernel_gen.passes.pipeline import build_npu_demo_lowering_pipeline

pm = build_npu_demo_lowering_pipeline()
module = pm.run(module)
```

注意事项：

- 具体 pass 顺序见 `npu_demo_lowering.md`。

返回与限制：

- 返回 `PassManager` 实例。

### `build_registered_pipeline(name: str) -> PassManager`

功能说明：

- 通过 registry 名字构造 pipeline。

参数说明：

- `name (str)`：pipeline 名称，如 `default-lowering` 或 `npu-demo-lowering`。

使用示例：

```python
from kernel_gen.passes.registry import load_builtin_passes, build_registered_pipeline

load_builtin_passes()
pm = build_registered_pipeline("default-lowering")
pm = build_registered_pipeline("npu-demo-lowering")
module = pm.run(module)
```

注意事项：

- 调用前必须确保 `load_builtin_passes()` 已执行。

返回与限制：

- 返回 `PassManager` 实例。

## 测试

- 测试文件：
  - [`test/pass/test_pipeline_default_lowering.py`](../../../test/pass/test_pipeline_default_lowering.py)
  - [`test/pass/test_pipeline_npu_demo_lowering.py`](../../../test/pass/test_pipeline_npu_demo_lowering.py)
  - [`test/pass/test_pass_registry.py`](../../../test/pass/test_pass_registry.py)
- 执行命令：
  - `pytest -q test/pass/test_pipeline_default_lowering.py`
  - `pytest -q test/pass/test_pipeline_npu_demo_lowering.py`
  - `pytest -q test/pass/test_pass_registry.py`
- 测试目标：
  - pipeline builder 可构造并返回 `PassManager`。
  - registry 名字查询可返回默认 pipeline 与 npu-demo pipeline。
