# registry.md

## 功能简介

- 定义 pass / pipeline 的公开注册与查询接口：把“名字”与“构造器”解耦，使工具层（如 `ircheck`）只依赖稳定名称而不依赖具体 Python 模块路径。
- 该注册表服务于 CLI / pytest / 工具脚本的统一入口；同一名字在进程内必须唯一。

## 文档信息

- 创建者：`睡觉小分队`
- 最后一次更改：`金铲铲大作战`
- `spec`：[`spec/pass/registry.md`](../../spec/pass/registry.md)
- `功能实现`：[`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
- `test`：[`test/pass/test_pass_registry.py`](../../test/pass/test_pass_registry.py)

## 依赖

- pass 抽象与 pass manager：
  - [`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)
  - [`kernel_gen/passes/pass_manager.py`](../../kernel_gen/passes/pass_manager.py)

## 术语

- `pass name`：对外公开的 pass 标识字符串（来自 `Pass.name`）。
- `pipeline name`：对外公开的 pipeline 标识字符串。
- `constructible`：对 `build_registered_pass(name)` 来说，表示该 pass 可用无参方式构造为实例；若构造失败则视为不可构造。

## 目标

- 对外只暴露“名字 -> 实例/PassManager”的查询能力，避免工具层与测试层散落 import 细节。
- 支持通过装饰器完成注册，降低新增 pass/pipeline 的接入成本。
- 为 `ircheck` 的 `COMPILE_ARGS: --pass/--pipeline` 提供唯一的名字解析来源。

## 与 ircheck 的衔接

- `ircheck` 仅通过 `load_builtin_passes` + `build_registered_pass/build_registered_pipeline` 解析名字。
- 样例与统一写法见 [`spec/tools/ircheck.md`](../../spec/tools/ircheck.md) 与 [`expectation/tools/ircheck/README.md`](../../expectation/tools/ircheck/README.md)。

## 限制与边界

- 注册表不接收用户输入的任意 import path；也不负责扫描文件系统自动发现。
- 注册发生在 Python import 时；因此对“内置 pass/pipeline”必须提供一个显式加载入口（见 `load_builtin_passes`）。
- `build_registered_pass/build_registered_pipeline` 不得隐式调用 `load_builtin_passes()`；加载时机由调用方控制，以保持工具入口行为可预测。
- 重复注册同名 pass 或 pipeline 必须立即失败，不得覆盖旧项。
- 为便于工具与测试编写最小用例，仓库内置 pass 至少应包含：
  - `no-op`：恒等 pass（对输入 module 不做任何改写），且必须满足“可构造”要求（`pass_cls()` 可成功执行）。

## 公开接口

### 异常：`PassRegistryError`

功能说明：

- 表示 pass / pipeline 注册与查询阶段的可预期失败。

注意事项：

- `PassRegistryError` 的 `str(e)` 必须以本文件列出的错误短语之一开头，便于测试做机械匹配。

### `register_pass(pass_cls)`

功能说明：

- 装饰器：注册一个公开 pass 类（`Pass` 子类），使用 `pass_cls.name` 作为 key。

参数说明：

- `pass_cls (type[Pass])`：待注册的 pass 类。

使用示例：

```python
from kernel_gen.passes.pass_manager import Pass
from kernel_gen.passes.registry import register_pass

@register_pass
class TilePass(Pass):
    name = "tile"

    def run(self, module):
        return module
```

注意事项：

- `pass_cls` 必须是 `Pass` 子类。
- `pass_cls.name` 必须是非空字符串。
- 若同名 pass 已存在，必须抛出 `PassRegistryError`。

返回与限制：

- 返回输入 `pass_cls`（便于装饰器叠加）。

### `register_pipeline(name: str)`

功能说明：

- 装饰器工厂：注册一个公开 pipeline builder，使用 `name` 作为 key。

参数说明：

- `name (str)`：pipeline 名称，必须为非空字符串。

使用示例：

```python
from kernel_gen.passes.pass_manager import PassManager
from kernel_gen.passes.registry import register_pipeline

@register_pipeline("default-lowering")
def build_default_lowering() -> PassManager:
    pm = PassManager(name="lowering")
    # pm.add_pass(...)
    return pm
```

注意事项：

- 被装饰函数必须返回 `PassManager`。
- 若同名 pipeline 已存在，必须抛出 `PassRegistryError`。

返回与限制：

- 返回被装饰函数本身。

### `build_registered_pass(name: str) -> Pass`

功能说明：

- 根据 pass 名称构造并返回 pass 实例。

参数说明：

- `name (str)`：已注册 pass 名称。

使用示例：

```python
from kernel_gen.passes.registry import load_builtin_passes, build_registered_pass

load_builtin_passes()
pass_obj = build_registered_pass("tile")
```

注意事项：

- 调用方应在首次查询前调用 `load_builtin_passes()`，以保证内置模块已完成 import 与装饰器注册。
- pass 构造规则：
  - 以“无参构造”为准（等价于 `pass_cls()` 可成功执行）
  - 若构造抛错或缺少无参构造路径，必须报告“不可构造”

返回与限制：

- 失败时必须抛出 `PassRegistryError`，且错误短语前缀为：
  - `PassRegistryError: unknown pass '<name>'`
  - `PassRegistryError: pass '<name>' is not constructible`

### `build_registered_pipeline(name: str) -> PassManager`

功能说明：

- 根据 pipeline 名称构造并返回 `PassManager`。

参数说明：

- `name (str)`：已注册 pipeline 名称。

使用示例：

```python
from kernel_gen.passes.registry import load_builtin_passes, build_registered_pipeline

load_builtin_passes()
pm = build_registered_pipeline("default-lowering")
```

注意事项：

- 调用方应在首次查询前调用 `load_builtin_passes()`。
- builder 返回值必须为 `PassManager`；否则必须视为失败。

返回与限制：

- 失败时必须抛出 `PassRegistryError`，且错误短语前缀为：
  - `PassRegistryError: unknown pipeline '<name>'`
  - `PassRegistryError: pipeline '<name>' did not return PassManager`

### `load_builtin_passes() -> None`

功能说明：

- 主动加载仓库内置 pass / pipeline 模块，使装饰器注册生效。

使用示例：

```python
from kernel_gen.passes.registry import load_builtin_passes

load_builtin_passes()
```

注意事项：

- 该函数必须满足幂等性：重复调用不会重复注册或造成副作用。
- 只加载仓库内置模块；不得接收用户输入的任意模块路径。
- 建议至少提供一个内置 pass 名称 `no-op`，其语义为“返回输入不变”，用于工具链与 matcher 的最小验证链。

返回与限制：

- 无返回值；加载失败应抛出异常向上抛出。

### `list_registered_passes() -> list[str]` / `list_registered_pipelines() -> list[str]`

功能说明：

- 返回当前已注册的 pass / pipeline 名称列表。

使用示例：

```python
from kernel_gen.passes.registry import load_builtin_passes, list_registered_passes

load_builtin_passes()
names = list_registered_passes()
```

注意事项：

- 返回值顺序必须可预测，便于测试断言；建议按字典序排序。

返回与限制：

- 返回名称列表；不得返回重复项。

## 测试

- 测试文件：[`test/pass/test_pass_registry.py`](../../test/pass/test_pass_registry.py)
- 执行命令：`pytest -q test/pass/test_pass_registry.py`
- 测试目标：
  - `register_pass/register_pipeline`：重复注册立即失败，错误短语可机械匹配。
  - `build_registered_pass/build_registered_pipeline`：未知名称与不可构造/返回值非法路径报告稳定错误短语。
  - `list_registered_*`：返回值顺序确定且不含重复项。
