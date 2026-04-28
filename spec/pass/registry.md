# registry.md

## 功能简介

- 定义 pass / pipeline 的公开注册与查询接口：把“名字”与“构造器”解耦，使工具层（如 `ircheck`）只依赖稳定名称而不依赖具体 Python 模块路径。
- 支持 xdsl `ModulePass` 的注册与构造。
- 该注册表服务于 CLI / pytest / 工具脚本的统一入口；同一名字在进程内必须唯一。
- `build_registered_pass(...)` 支持所有 pass 通用 `options={"fold": "true|false"}`，默认仍为 pass 自身的 `fold=True`。

## API 列表

- `异常：`KernelCodeError`
- `register_pass(pass_cls)`
- `register_pipeline(name: str)`
- `build_registered_pass(name: str, options: dict[str, str] | None = None) -> ModulePass`
- `build_registered_pipeline(name: str, options: dict[str, str] | None = None) -> PassManager`
- `load_builtin_passes() -> None`
- `list_registered_passes() -> list[str]` / `list_registered_pipelines() -> list[str]`

## 文档信息

- 创建者：`睡觉小分队`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/pass/registry.md`](../../spec/pass/registry.md)
- `功能实现`：[`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
- `test`：[`test/pass/test_pass_registry.py`](../../test/pass/test_pass_registry.py)

## 依赖

- pass 抽象与 pass manager：
  - [`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)
  - [`kernel_gen/passes/pass_manager.py`](../../kernel_gen/passes/pass_manager.py)
- pipeline 目录与默认 pipeline：
  - [`spec/pass/pipeline/README.md`](../../spec/pass/pipeline/README.md)
  - [`spec/pass/pipeline/default_lowering.md`](../../spec/pass/pipeline/default_lowering.md)
  - [`spec/pass/pipeline/npu_demo_lowering.md`](../../spec/pass/pipeline/npu_demo_lowering.md)
- standalone tuning pass：
  - [`spec/pass/tuning/launch_kernel_cost_func.md`](../../spec/pass/tuning/launch_kernel_cost_func.md)

## 术语

- `pass name`：对外公开的 pass 标识字符串（来自 `Pass.name`）。
- `pipeline name`：对外公开的 pipeline 标识字符串。
- `constructible`：对 `build_registered_pass(name)` 来说，表示该 pass 可用无参方式构造为实例；若构造失败则视为不可构造。
- `options`：构造 pass / pipeline 时的键值字典（`dict[str, str]`）；空字典与 `None` 表示不提供选项。
- `fold`：所有 pass 的通用 options key；合法值为 `true/false/1/0/yes/no/on/off`，控制 pass 后通用 folding sweep。

## 目标

- 对外只暴露“名字 -> 实例/PassManager”的查询能力，避免工具层与测试层散落 import 细节。
- 支持通过装饰器完成注册，降低新增 pass/pipeline 的接入成本。
- 供工具层（如 ircheck）通过 `load_builtin_passes` + `build_registered_pass/build_registered_pipeline` 完成名字解析。

## 限制与边界

- 注册表不接收用户输入的任意 import path；也不负责扫描文件系统自动发现。
- 注册发生在 Python import 时；因此对“内置 pass/pipeline”必须提供一个显式加载入口（见 `load_builtin_passes`）。
- `build_registered_pass/build_registered_pipeline` 不得隐式调用 `load_builtin_passes()`；加载时机由调用方控制，以保持工具入口行为可预测。
- 除 pass 通用 `fold` 选项外，注册表不解析其它 `options` 语义；其它 pass options 继续交给 pass / pipeline 构造入口。
- 内置 pipeline 模块放在 `kernel_gen/passes/pipeline`；`load_builtin_passes()` 负责导入这些模块以触发注册。
- 当前内置 pipeline 至少包含 `default-lowering` 与 `npu-demo-lowering` 两个公开 builder。
- `npu-demo-lowering` 公开 builder 支持 `options={"target": "npu_demo"}`；`only-kernel` / `only_kernel` 之类选项必须显式失败，不能把 host wrapper 与 device body 的 outline 流程裁成仅 kernel 形态。
- registry 只负责注册与查询，不承载具体 pipeline builder 实现。
- 重复注册同名 pass 或 pipeline 必须立即失败，不得覆盖旧项。
- 为便于工具与测试编写最小用例，仓库内置 pass 至少应包含：
  - `no-op`：恒等 pass（对输入 module 不做任何改写），且必须满足“可构造”要求（`pass_cls()` 可成功执行）。
  - `inline`：module 内 helper 展平 pass，供 `npu-demo-lowering` 前置收口。
  - `attach-arch-information`：把 target registry 的 launch extent 写回入口 `func.func`。
  - `symbol-buffer-hoist`：把 `symbol.for` 单 block 循环体内可安全外提的 `dma.alloc` 提到 loop 之前。
  - `tile-analysis` / `tile-elewise` / `tile-reduce`：tile family 的公开 `ModulePass` 名称，供 pytest 与工具层统一解析。
- tuning pass `launch-kernel-cost-func` 既可通过 pass registry 显式启用，也作为 `npu-demo-lowering` 的末尾 pass 运行；不自动进入 `default-lowering`。
- `launch-kernel-cost-func` 默认 `cost_kind="DMA|MAC"`，并接受 `options={"cost_kind": "compute|memory"}`；非法 `cost_kind` 必须由 pass 构造入口或 pass 本身显式失败，registry 不吞掉该错误。
- registry 只解析 pass 通用 `fold` 选项；剩余 `options` 仅按字典透传给 pass 或 pipeline 构造入口。

## 当前公开路径与迁移矩阵

- 本节记录当前公开导入基线与消费者迁移矩阵；已完成收口的旧路径按失败边界处理，不再保留“继续可导入”的兼容表述。
- 对 registry / pass manager caller，当前 canonical public path 固定为：
  - `kernel_gen.passes.registry`
  - `kernel_gen.passes.pass_manager`
- 对根路径 pass caller，当前 canonical public path 固定为：
  - `kernel_gen.passes.buffer_results_to_out_params`
  - `kernel_gen.passes.inline`
  - `kernel_gen.passes.attach_arch_information`
  - `kernel_gen.passes.decompass`
  - `kernel_gen.passes.dma_memory_hierarchy`
  - `kernel_gen.passes.memory_pool`
  - `kernel_gen.passes.outline_device_kernel`
  - `kernel_gen.passes.symbol_buffer_hoist`
  - `kernel_gen.passes.symbol_loop_hoist`
- 对当前仍存活的 compat / family caller，当前基线仍允许继续导入，但不承诺永久保留：
  - `kernel_gen.passes.lowering`
  - `kernel_gen.passes.lowering.buffer_results_to_out_params`
  - `kernel_gen.passes.lowering.nn_to_kernel`
  - `kernel_gen.passes.lowering.outline_device_kernel`
  - `kernel_gen.passes.lowering.symbol_loop_hoist`
- 对已退场的旧路径，`S1` 当前必须稳定失败：
  - `kernel_gen.analysis`
  - `kernel_gen.analysis.analysis`
  - `kernel_gen.analysis.compute`
  - `kernel_gen.analysis.memory`
  - `kernel_gen.passes.analysis`
  - `kernel_gen.passes.analysis.func_cost`
  - `kernel_gen.passes.lowering.registry`
  - `kernel_gen.passes.lowering.pass_manager`
  - `kernel_gen.passes.lowering.inline`
  - `kernel_gen.passes.lowering.attach_arch_information`
  - `kernel_gen.passes.lowering.decompass`
  - `kernel_gen.passes.lowering.dma_memory_hierarchy`
  - `kernel_gen.passes.lowering.memory_pool`
  - `kernel_gen.passes.lowering.tile_analysis`
  - `kernel_gen.passes.lowering.tile_elewise`
  - `kernel_gen.passes.lowering.tile_reduce`
- 已退场的 analysis family 不再提供公开 pass 名或 registry 构造入口；`build_registered_pass("analyze-func-cost")` 必须显式失败。
- 机械验收口径：
  - `test/pass/test_pass_registry.py` 负责锁定 canonical public path、`symbol-buffer-hoist` 的稳定注册名与包根 re-export、旧路径失败边界、`analyze-func-cost` 构造失败与 registry caller 的 `importlib` 消费者矩阵。
  - `test/pass/test_pass_manager.py` 负责锁定 pass manager / pipeline caller 的 `importlib` 消费者矩阵。

## S2 导入矩阵补充

- 对 out-param / nn lowering caller，当前 canonical public path 收口为：
  - `kernel_gen.passes.buffer_results_to_out_params`
  - `kernel_gen.passes.lowering.nn_lowering`
- 下列 compat shim 从 `S2` 起必须稳定失败：
  - `kernel_gen.passes.lowering.buffer_results_to_out_params`
  - `kernel_gen.passes.lowering.nn_to_kernel`
- `kernel_gen.passes` 与 `kernel_gen.passes.lowering` package 级别的 re-export 若继续存在，只能视为迁移辅助；`S2` 的 pytest 证明必须落在 canonical submodule path 与旧路径失败边界上。
- 机械验收口径：
  - [`test/pass/test_buffer_results_to_out_params.py`](../../test/pass/test_buffer_results_to_out_params.py) 负责锁定 `buffer_results_to_out_params` 的 canonical import 成功与 lowering compat 模块失败。
  - [`test/pass/nn_lowering/public_name.py`](../../test/pass/nn_lowering/public_name.py) 负责锁定 `nn_lowering` 的 canonical import 成功与 `nn_to_kernel` 旧模块失败。
  - `expectation/pass/buffer_results_to_out_params/**` 仍只作合同验收资产单列，不替代上述 pytest。

## 公开接口

### 异常：`KernelCodeError`

功能说明：

- 表示 pass / pipeline 注册与查询阶段的可预期失败。

注意事项：

- `KernelCodeError` 的 `str(e)` 必须以本文件列出的错误短语之一开头，便于测试做机械匹配。
- 与 `options` 相关的错误短语：
  - `PassRegistryError: pass '<name>' does not accept options`
  - `PassRegistryError: pass '<name>' option error`
  - `PassRegistryError: option 'fold' expects bool`
  - `PassRegistryError: pipeline '<name>' does not accept options`
  - `PassRegistryError: pipeline '<name>' option error`

### `register_pass(pass_cls)`

功能说明：

- 装饰器：注册一个公开 `ModulePass` 子类，使用 `pass_cls.name` 作为 key。

参数说明：

- `pass_cls (type[ModulePass])`：待注册的 pass 类。

使用示例：

```python
from xdsl.passes import ModulePass
from kernel_gen.passes.registry import register_pass

@register_pass
class TileAnalysisPass(ModulePass):
    name = "tile-analysis"

    def apply(self, ctx, module):
        return None
```

注意事项：

- `pass_cls` 必须是 `ModulePass` 子类。
- `pass_cls.name` 必须是非空字符串。
- 若同名 pass 已存在，必须抛出 `KernelCodeError`。

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
def build_default_lowering_pipeline() -> PassManager:
    pm = PassManager(name="default-lowering")
    # pm.add_pass(...)
    return pm
```

注意事项：

- 被装饰函数必须返回 `PassManager`。
- 若 pipeline 需要接收选项，builder 应提供 `builder(options: dict[str, str]) -> PassManager` 形态。
- 若同名 pipeline 已存在，必须抛出 `KernelCodeError`。

返回与限制：

- 返回被装饰函数本身。

### `build_registered_pass(name: str, options: dict[str, str] | None = None) -> ModulePass`

功能说明：

- 根据 pass 名称构造并返回 pass 实例。
- 返回值必须是 xdsl `ModulePass` 实例。
- 若 `options` 中包含 `fold`，registry 先解析并设置到返回 pass 实例；剩余 options 再按原规则交给 pass 自身构造入口。

参数说明：

- `name (str)`：已注册的 pass 名称。
- `options (dict[str, str] | None)`：构造选项；`fold` 为所有 pass 通用选项，其它选项由具体 pass 定义。

使用示例：

```python
load_builtin_passes()
pass_obj = build_registered_pass("inline", {"fold": "false"})
assert pass_obj.fold is False
```

参数说明：

- `name (str)`：已注册 pass 名称。
- `options (dict[str, str] | None)`：可选选项字典；`None` 或空字典表示不提供选项。

使用示例：

```python
from kernel_gen.passes.registry import load_builtin_passes, build_registered_pass

load_builtin_passes()
pass_obj = build_registered_pass("tile-analysis")
pass_obj = build_registered_pass("tile-reduce")
inline_pass = build_registered_pass("inline")
attach_pass = build_registered_pass("attach-arch-information")
hoist_pass = build_registered_pass("symbol-buffer-hoist")
cost_pass = build_registered_pass("launch-kernel-cost-func", {"cost_kind": "compute|memory"})
default_cost_pass = build_registered_pass("launch-kernel-cost-func")
```

注意事项：

- 调用方应在首次查询前调用 `load_builtin_passes()`，以保证内置模块已完成 import 与装饰器注册。
- pass 构造规则：
  - `options` 为空或 `None`：以无参构造为准（等价于 `pass_cls()` 可成功执行）。
  - `options` 非空：pass 类必须提供 `from_options(options)` 构造入口。
  - `from_options` 失败或返回非 `ModulePass` 实例时，必须报告 `option error`。
  - 无参构造失败时必须报告“不可构造”。

返回与限制：

- 失败时必须抛出 `KernelCodeError`，且错误短语前缀为：
  - `PassRegistryError: unknown pass '<name>'`
  - `PassRegistryError: pass '<name>' is not constructible`
  - `PassRegistryError: pass '<name>' does not accept options`
  - `PassRegistryError: pass '<name>' option error`

### `build_registered_pipeline(name: str, options: dict[str, str] | None = None) -> PassManager`

功能说明：

- 根据 pipeline 名称构造并返回 `PassManager`。

参数说明：

- `name (str)`：已注册 pipeline 名称。
- `options (dict[str, str] | None)`：可选选项字典；`None` 或空字典表示不提供选项。

使用示例：

```python
from kernel_gen.passes.registry import load_builtin_passes, build_registered_pipeline

load_builtin_passes()
pm = build_registered_pipeline("default-lowering")
pm = build_registered_pipeline("npu-demo-lowering")
pm = build_registered_pipeline("npu-demo-lowering", {"target": "npu_demo"})
pm = build_registered_pipeline("default-lowering", {"bufferize": "true"})
```

注意事项：

- 调用方应在首次查询前调用 `load_builtin_passes()`。
- 工具侧（如 ircheck）仅通过该接口解析 pipeline 名称，不直接 import pipeline builder。
- `options` 为空或 `None` 时，调用 builder 的无参路径。
- `options` 非空时，builder 必须接受 `options` 参数；否则必须报告“不接受选项”。
- `npu-demo-lowering` builder 支持 `options={"target": "npu_demo"}`；其他未知选项必须显式失败。
- builder 返回值必须为 `PassManager`；否则必须视为失败。

返回与限制：

- 失败时必须抛出 `KernelCodeError`，且错误短语前缀为：
  - `PassRegistryError: unknown pipeline '<name>'`
  - `PassRegistryError: pipeline '<name>' did not return PassManager`
  - `PassRegistryError: pipeline '<name>' does not accept options`
  - `PassRegistryError: pipeline '<name>' option error`

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
- 当前内置 pipeline 至少应包含 `default-lowering` 与 `npu-demo-lowering`。

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
  - `build_registered_pass/build_registered_pipeline`：未知名称、不可构造、选项不被接受、返回值非法路径报告稳定错误短语。
- `launch-kernel-cost-func`：通过 `load_builtin_passes()` 后可查询；无参构造默认 `DMA|MAC`；`cost_kind=compute|memory` 选项可透传构造；非法 `cost_kind` 不被 registry 层吞掉。
- `tile-analysis` / `tile-elewise` / `tile-reduce`：通过 `load_builtin_passes()` 后可查询；三者均以 `ModulePass` 形式公开给 registry / pipeline / pytest 入口。
- `list_registered_*`：返回值顺序确定且不含重复项。
