# pass README

## 功能简介

- 说明 pass 与 pipeline 的公共文档入口，提供最小编写与使用范式。
- 区分职责：pass 定义在 `kernel_gen/passes`，pipeline 定义在 `kernel_gen/passes/pipeline`。
- 引导调用方通过 registry 的名字入口访问 pipeline。

## 文档信息

- 创建者：`睡觉小分队`
- 最后一次更改：`咯咯咯`
- `spec`：[`spec/pass/README.md`](../../spec/pass/README.md)
- `功能实现`：
  - [`kernel_gen/passes/pass_manager.py`](../../kernel_gen/passes/pass_manager.py)
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
  - [`kernel_gen/passes/pipeline/default_lowering.py`](../../kernel_gen/passes/pipeline/default_lowering.py)
- `test`：
  - [`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)
  - [`test/pass/test_pass_registry.py`](../../test/pass/test_pass_registry.py)
  - [`test/pass/test_pipeline_default_lowering.py`](../../test/pass/test_pipeline_default_lowering.py)

## 依赖

- Pass 管理与排序：[`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)
- Pass/pipeline 注册表：[`spec/pass/registry.md`](../../spec/pass/registry.md)
- Pipeline 目录说明：[`spec/pass/pipeline/README.md`](../../spec/pass/pipeline/README.md)
- 默认 pipeline 合同：[`spec/pass/pipeline/default_lowering.md`](../../spec/pass/pipeline/default_lowering.md)
- host launch outline 合同：[`spec/pass/outline_device_kernel.md`](../../spec/pass/outline_device_kernel.md)

## 目标

- 给出 pass 编写与使用的最小范式。
- 明确 pipeline 目录位置与默认 pipeline builder 的入口。
- 说明 registry 是 pipeline 名字查询入口。
- 说明 standalone pass 与默认 pipeline 的边界：`outline-device-kernel` 这类显式 opt-in pass 不自动进入 `default-lowering`。

## 限制与边界

- 本文件只描述通用用法，不替代具体 pass 的独立 spec。
- pipeline 的顺序与构造细节以 pipeline 目录下的 spec 为准。
- registry 只负责注册与查询，不执行 pass。
- standalone pass 的 expectation runner 应与 pass 名保持稳定映射；`outline-device-kernel` 的目录约定固定为 `expectation/pass/outline_device_kernel/`，其中 runner 入口为 `__main__.py`，子资产为 `basic.py`、`multi_function.py`、`invalid_attr.py`。
- `expectation/pass/pipeline/default_lowering.py` 只服务默认 pipeline 黑盒验收，不与 `expectation/pass/outline_device_kernel/` 混用。

## 公开接口

### `class Pass`

功能说明：

- 表示单个可执行 pass。

参数说明：

- `name (str)`：pass 名称。
- `run(self, target)`：接收并返回处理后的对象。

使用示例：

```python
from kernel_gen.passes.pass_manager import Pass


class NnLoweringPass(Pass):
    name = "lower-nn"

    def run(self, target):
        return target
```

注意事项：

- `run` 必须返回一个对象，供下一个 pass 使用。

返回与限制：

- `run` 返回值作为下游 pass 输入。

### `class PassManager`

功能说明：

- 维护 pass 列表并按顺序执行。

参数说明：

- `name (str | None)`：管理器名称，可选。

使用示例：

```python
from kernel_gen.passes.pass_manager import PassManager

manager = PassManager(name="opt")
manager.add_pass(NnLoweringPass())
result = manager.run(target)
```

```python
manager = PassManager()
manager.extend([NnLoweringPass()])
result = manager.run(target)
```

注意事项：

- 执行顺序与添加顺序一致。

返回与限制：

- `run` 返回最后一个 pass 的输出；无 pass 时返回输入。

### `build_default_lowering_pipeline()` / `build_registered_pipeline(name)`

功能说明：

- `build_default_lowering_pipeline()`：直接构造默认 lowering pipeline。
- `build_registered_pipeline(name)`：通过 registry 名字查询构造 pipeline。

参数说明：

- `name (str)`：pipeline 名称，如 `default-lowering`。

使用示例：

```python
from kernel_gen.passes.pipeline import build_default_lowering_pipeline

pm = build_default_lowering_pipeline()
module = pm.run(module)
```

```python
from kernel_gen.passes.registry import load_builtin_passes, build_registered_pipeline

load_builtin_passes()
pm = build_registered_pipeline("default-lowering")
module = pm.run(module)
```

注意事项：

- 通过 registry 查询前必须调用 `load_builtin_passes()`。
- 若调用方需要 host launch outline，必须显式构造 `build_registered_pass("outline-device-kernel")` 或直接实例化 `OutlineDeviceKernelPass`；`default-lowering` remains unchanged。

返回与限制：

- 返回 `PassManager` 实例。

## 测试

- 测试文件：
  - [`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)
  - [`test/pass/test_pass_registry.py`](../../test/pass/test_pass_registry.py)
  - [`test/pass/test_pipeline_default_lowering.py`](../../test/pass/test_pipeline_default_lowering.py)
- 执行命令：
  - `pytest -q test/pass/test_pass_manager.py`
  - `pytest -q test/pass/test_pass_registry.py`
  - `pytest -q test/pass/test_pipeline_default_lowering.py`
- 测试目标：
  - pass 顺序执行与空管理器行为。
  - registry 的注册与查询行为。
  - 默认 pipeline 的构造与顺序。
