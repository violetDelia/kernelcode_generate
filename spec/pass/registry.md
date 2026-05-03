# registry.md

## 功能简介

- 定义 pass / pipeline 的公开注册与查询接口：把“名字”与“构造器”解耦，使工具层（如 `ircheck`）只依赖稳定名称而不依赖具体 Python 模块路径。
- 支持 xdsl `ModulePass` 的注册与构造。
- 该注册表服务于 CLI / pytest / 工具脚本的统一入口；同一名字在进程内必须唯一。
- `build_registered_pass(...)` 支持所有 pass 通用 `options={"fold": "true|false"}`，默认仍为 pass 自身的 `fold=True`。

## API 列表

- `class KernelCodeError(kind: ErrorKind | str, module: ErrorModule | str, message: str)`
- `register_pass(pass_cls: type[PassType]) -> type[PassType]`
- `register_pipeline(name: str) -> Callable[[Callable[..., PassManager]], Callable[..., PassManager]]`
- `build_registered_pass(name: str, options: dict[str, str] | None = None) -> ModulePass`
- `build_registered_pipeline(name: str, options: dict[str, str] | None = None) -> PassManager`
- `load_builtin_passes() -> None`
- `list_registered_passes() -> list[str]`
- `list_registered_pipelines() -> list[str]`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/pass/registry.md`](../../spec/pass/registry.md)
- `功能实现`：[`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
- `test`：[`test/passes/test_registry.py`](../../test/passes/test_registry.py)

## 依赖

- pass 抽象与 pass manager：
  - [`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)
  - [`kernel_gen/passes/pass_manager.py`](../../kernel_gen/passes/pass_manager.py)
- pipeline 目录与默认 pipeline：
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

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
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
- `lower-dma-memory-hierarchy` 接受 pass 专属 `options={"apply_op": "matmul{[\\"\\", \\"tlm1\\", \\"tlm2\\"]}"}`；registry 只负责透传该 option，规则语法与错误语义由 `LowerDmaMemoryHierarchyPass.from_options(...)` 承载。
- `memory-pool` 接受 pass 专属 `options={"rewrite": "true|false", "alignment": "<non-negative-int>"}`；`fold` 仍由 registry 通用 option 处理。`rewrite` 非 bool、`alignment` 负数或非整数、未知 option 必须由 `MemoryPoolPass.from_options(...)` 失败并由 registry 保留为 `PassRegistryError: pass 'memory-pool' option error: <原因>`。
- registry 只解析 pass 通用 `fold` 选项；剩余 `options` 仅按字典透传给 pass 或 pipeline 构造入口。

### 当前公开路径与迁移矩阵

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
  - `test/passes/test_registry.py` 负责锁定 canonical public path、`symbol-buffer-hoist` 的稳定注册名与包根 re-export、旧路径失败边界、`analyze-func-cost` 构造失败与 registry caller 的 `importlib` 消费者矩阵。
  - `test/passes/test_pass_manager.py` 负责锁定 pass manager / pipeline caller 的 `importlib` 消费者矩阵。

### S2 导入矩阵补充

- 对 out-param / nn lowering caller，当前 canonical public path 收口为：
  - `kernel_gen.passes.buffer_results_to_out_params`
  - `kernel_gen.passes.lowering.nn_lowering`
- 下列 compat shim 从 `S2` 起必须稳定失败：
  - `kernel_gen.passes.lowering.buffer_results_to_out_params`
  - `kernel_gen.passes.lowering.nn_to_kernel`
- `kernel_gen.passes` 与 `kernel_gen.passes.lowering` package 级别的 re-export 若继续存在，只能视为迁移辅助；`S2` 的 pytest 证明必须落在 canonical submodule path 与旧路径失败边界上。
- 机械验收口径：
  - [`test/passes/test_buffer_results_to_out_params.py`](../../test/passes/test_buffer_results_to_out_params.py) 负责锁定 `buffer_results_to_out_params` 的 canonical import 成功与 lowering compat 模块失败。
  - [`test/passes/lowering/nn_lowering/test_public_name.py`](../../test/passes/lowering/nn_lowering/test_public_name.py) 负责锁定 `nn_lowering` 的 canonical import 成功与 `nn_to_kernel` 旧模块失败。
  - `expectation/pass/buffer_results_to_out_params/**` 仍只作合同验收资产单列，不替代上述 pytest。


### 异常：`KernelCodeError`

- 功能说明：

- 表示 pass / pipeline 注册与查询阶段的可预期失败。

- 注意事项：

- `KernelCodeError` 的 `str(e)` 必须以本文件列出的错误短语之一开头，便于测试做机械匹配。
- 与 `options` 相关的错误短语：
  - `PassRegistryError: pass '<name>' does not accept options`
  - `PassRegistryError: pass '<name>' option error`
  - `PassRegistryError: pass '<name>' option error: <pass 专属原因>`
  - `PassRegistryError: option 'fold' expects bool`
  - `PassRegistryError: pipeline '<name>' does not accept options`
  - `PassRegistryError: pipeline '<name>' option error`

### `register_pass(pass_cls)`

- 功能说明：

- 装饰器：注册一个公开 `ModulePass` 子类，使用 `pass_cls.name` 作为 key。

- 参数：

- `pass_cls (type[ModulePass])`：待注册的 pass 类。

- 使用示例：

```python
from xdsl.passes import ModulePass
from kernel_gen.passes.registry import register_pass

@register_pass
class TileAnalysisPass(ModulePass):
    name = "tile-analysis"

    def apply(self, ctx, module):
        return None
```

- 注意事项：

- `pass_cls` 必须是 `ModulePass` 子类。
- `pass_cls.name` 必须是非空字符串。
- 若同名 pass 已存在，必须抛出 `KernelCodeError`。

- 返回值：

- 返回输入 `pass_cls`（便于装饰器叠加）。

### `register_pipeline(name: str)`

- 功能说明：

- 装饰器工厂：注册一个公开 pipeline builder，使用 `name` 作为 key。

- 参数：

- `name (str)`：pipeline 名称，必须为非空字符串。

- 使用示例：

```python
from kernel_gen.passes.pass_manager import PassManager
from kernel_gen.passes.registry import register_pipeline

@register_pipeline("default-lowering")
def build_default_lowering_pipeline() -> PassManager:
    pm = PassManager(name="default-lowering")
    # pm.add_pass(value)
    return pm
```

- 注意事项：

- 被装饰函数必须返回 `PassManager`。
- 若 pipeline 需要接收选项，builder 应提供 `builder(options: dict[str, str]) -> PassManager` 形态。
- 若同名 pipeline 已存在，必须抛出 `KernelCodeError`。

- 返回值：

- 返回被装饰函数本身。

### `build_registered_pass(name: str, options: dict[str, str] | None = None) -> ModulePass`

- 功能说明：

- 根据 pass 名称构造并返回 pass 实例。
- 返回值必须是 xdsl `ModulePass` 实例。
- 若 `options` 中包含 `fold`，registry 先解析并设置到返回 pass 实例；剩余 options 再按原规则交给 pass 自身构造入口。

- 参数：

- `name (str)`：已注册的 pass 名称。
- `options (dict[str, str] | None)`：构造选项；`fold` 为所有 pass 通用选项，其它选项由具体 pass 定义。

- 使用示例：

```python
load_builtin_passes()
pass_obj = build_registered_pass("inline", {"fold": "false"})
assert pass_obj.fold is False
```

- 参数：

- `name (str)`：已注册 pass 名称。
- `options (dict[str, str] | None)`：可选选项字典；`None` 或空字典表示不提供选项。

- 使用示例：

```python
from kernel_gen.passes.registry import load_builtin_passes, build_registered_pass

load_builtin_passes()
pass_obj = build_registered_pass("tile-analysis")
pass_obj = build_registered_pass("tile-reduce")
inline_pass = build_registered_pass("inline")
attach_pass = build_registered_pass("attach-arch-information")
hoist_pass = build_registered_pass("symbol-buffer-hoist")
cost_pass = build_registered_pass("launch-kernel-cost-func", {"cost_kind": "compute|memory"})
memory_pool_pass = build_registered_pass("memory-pool", {"rewrite": "true", "fold": "false", "alignment": "0"})
default_cost_pass = build_registered_pass("launch-kernel-cost-func")
```

- 注意事项：

- 调用方应在首次查询前调用 `load_builtin_passes()`，以保证内置模块已完成 import 与装饰器注册。
- pass 构造规则：
  - `options` 为空或 `None`：以无参构造为准（等价于 `pass_cls()` 可成功执行）。
  - `options` 非空：pass 类必须提供 `from_options(options)` 构造入口。
  - `from_options` 抛出 `KernelCodeError` 时，registry 必须报告 `option error` 前缀并保留 pass 专属原因。
  - `from_options` 发生其他异常或返回非 `ModulePass` 实例时，必须报告 `option error`。
  - 无参构造失败时必须报告“不可构造”。

- 返回值：

- 失败时必须抛出 `KernelCodeError`，且错误短语前缀为：
  - `PassRegistryError: unknown pass '<name>'`
  - `PassRegistryError: pass '<name>' is not constructible`
  - `PassRegistryError: pass '<name>' does not accept options`
  - `PassRegistryError: pass '<name>' option error`
  - `PassRegistryError: pass '<name>' option error: <pass 专属原因>`

### `build_registered_pipeline(name: str, options: dict[str, str] | None = None) -> PassManager`

- 功能说明：

- 根据 pipeline 名称构造并返回 `PassManager`。

- 参数：

- `name (str)`：已注册 pipeline 名称。
- `options (dict[str, str] | None)`：可选选项字典；`None` 或空字典表示不提供选项。

- 使用示例：

```python
from kernel_gen.passes.registry import load_builtin_passes, build_registered_pipeline

load_builtin_passes()
pm = build_registered_pipeline("default-lowering")
pm = build_registered_pipeline("npu-demo-lowering")
pm = build_registered_pipeline("npu-demo-lowering", {"target": "npu_demo"})
pm = build_registered_pipeline("default-lowering", {"bufferize": "true"})
```

- 注意事项：

- 调用方应在首次查询前调用 `load_builtin_passes()`。
- 工具侧（如 ircheck）仅通过该接口解析 pipeline 名称，不直接 import pipeline builder。
- `options` 为空或 `None` 时，调用 builder 的无参路径。
- `options` 非空时，builder 必须接受 `options` 参数；否则必须报告“不接受选项”。
- `npu-demo-lowering` builder 支持 `options={"target": "npu_demo"}`；其他未知选项必须显式失败。
- builder 返回值必须为 `PassManager`；否则必须视为失败。

- 返回值：

- 失败时必须抛出 `KernelCodeError`，且错误短语前缀为：
  - `PassRegistryError: unknown pipeline '<name>'`
  - `PassRegistryError: pipeline '<name>' did not return PassManager`
  - `PassRegistryError: pipeline '<name>' does not accept options`
  - `PassRegistryError: pipeline '<name>' option error`

### `load_builtin_passes() -> None`

- 功能说明：

- 主动加载仓库内置 pass / pipeline 模块，使装饰器注册生效。

- 使用示例：

```python
from kernel_gen.passes.registry import load_builtin_passes

load_builtin_passes()
```

- 注意事项：

- 该函数必须满足幂等性：重复调用不会重复注册或造成副作用。
- 只加载仓库内置模块；不得接收用户输入的任意模块路径。
- 建议至少提供一个内置 pass 名称 `no-op`，其语义为“返回输入不变”，用于工具链与 matcher 的最小验证链。
- 当前内置 pipeline 至少应包含 `default-lowering` 与 `npu-demo-lowering`。

- 返回值：

- 无返回值；加载失败应抛出异常向上抛出。

### `list_registered_passes() -> list[str]` / `list_registered_pipelines() -> list[str]`

- 功能说明：

- 返回当前已注册的 pass / pipeline 名称列表。

- 使用示例：

```python
from kernel_gen.passes.registry import load_builtin_passes, list_registered_passes

load_builtin_passes()
names = list_registered_passes()
```

- 注意事项：

- 返回值顺序必须可预测，便于测试断言；建议按字典序排序。

- 返回值：

- 返回名称列表；不得返回重复项。

## API详细说明

### `class KernelCodeError(kind: ErrorKind | str, module: ErrorModule | str, message: str)`

- api：`class KernelCodeError(kind: ErrorKind | str, module: ErrorModule | str, message: str)`
- 参数：
  - `kind`：类别标识，指定当前接口处理的 pass、cost、target、节点或输出种类；类型 `ErrorKind | str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `module`：模块级 IR 对象，作为 pass、校验或代码生成的处理主体；类型 `ErrorModule | str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `message`：诊断或错误消息文本，用于构造稳定错误或校验输出；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`KernelCodeError` 实例。
- 使用示例：

  ```python
  kernel_code_error = KernelCodeError(kind=kind, module=module, message=message)
  ```
- 功能说明：构造 `KernelCodeError` 实例。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `register_pass(pass_cls: type[PassType]) -> type[PassType]`

- api：`register_pass(pass_cls: type[PassType]) -> type[PassType]`
- 参数：
  - `pass_cls`：`pass_cls` 输入值，参与 `register_pass` 的公开处理流程；类型 `type[PassType]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`type[PassType]`。
- 使用示例：

  ```python
  result = register_pass(pass_cls=pass_cls)
  ```
- 功能说明：注册 `pass`。
- 注意事项：注册名必须稳定；重复注册、未知名称或非法 options 必须按公开错误语义处理。

### `register_pipeline(name: str) -> Callable[[Callable[..., PassManager]], Callable[..., PassManager]]`

- api：`register_pipeline(name: str) -> Callable[[Callable[..., PassManager]], Callable[..., PassManager]]`
- 参数：
  - `name`：公开名称、符号名或注册名，用于查找、打印、注册或生成稳定标识；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Callable[[Callable[..., PassManager]], Callable[..., PassManager]]`。
- 使用示例：

  ```python
  result = register_pipeline(name=name)
  ```
- 功能说明：注册 `pipeline`。
- 注意事项：注册名必须稳定；重复注册、未知名称或非法 options 必须按公开错误语义处理。

### `build_registered_pass(name: str, options: dict[str, str] | None = None) -> ModulePass`

- api：`build_registered_pass(name: str, options: dict[str, str] | None = None) -> ModulePass`
- 参数：
  - `name`：公开名称、符号名或注册名，用于查找、打印、注册或生成稳定标识；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `options`：IR operation；类型 `dict[str, str] | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按可变容器传入时，是否修改输入必须以本接口功能说明和注意事项为准；非法值按该 API 的公开错误语义处理。
- 返回值：`ModulePass`。
- 使用示例：

  ```python
  result = build_registered_pass(name=name, options=None)
  ```
- 功能说明：构建 `registered_pass`。
- 注意事项：注册名必须稳定；重复注册、未知名称或非法 options 必须按公开错误语义处理。

### `build_registered_pipeline(name: str, options: dict[str, str] | None = None) -> PassManager`

- api：`build_registered_pipeline(name: str, options: dict[str, str] | None = None) -> PassManager`
- 参数：
  - `name`：公开名称、符号名或注册名，用于查找、打印、注册或生成稳定标识；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `options`：IR operation；类型 `dict[str, str] | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按可变容器传入时，是否修改输入必须以本接口功能说明和注意事项为准；非法值按该 API 的公开错误语义处理。
- 返回值：`PassManager`。
- 使用示例：

  ```python
  result = build_registered_pipeline(name=name, options=None)
  ```
- 功能说明：构建 `registered_pipeline`。
- 注意事项：注册名必须稳定；重复注册、未知名称或非法 options 必须按公开错误语义处理。

### `load_builtin_passes() -> None`

- api：`load_builtin_passes() -> None`
- 参数：无。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  load_builtin_passes()
  ```
- 功能说明：加载 `builtin_passes`。
- 注意事项：输入 memory、offset、size、stride 和 dtype 必须符合 DMA operation 合同；非法组合必须稳定失败。

### `list_registered_passes() -> list[str]`

- api：`list_registered_passes() -> list[str]`
- 参数：无。
- 返回值：`list[str]`。
- 使用示例：

  ```python
  result = list_registered_passes()
  ```
- 功能说明：执行 `list_registered_passes`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `list_registered_pipelines() -> list[str]`

- api：`list_registered_pipelines() -> list[str]`
- 参数：无。
- 返回值：`list[str]`。
- 使用示例：

  ```python
  result = list_registered_pipelines()
  ```
- 功能说明：执行 `list_registered_pipelines`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

## 测试

- 测试文件：`test/passes/test_registry.py`
- 执行命令：
  - `pytest -q test/passes/test_registry.py`
  - ` 形式公开给 registry / pipeline / pytest 入口。
- `

### 测试目标

- 验证 `spec/pass/registry.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证非法输入、边界条件和错误语义按公开合同失败。
- 验证公开导入、注册名、CLI 或命名空间入口只暴露 spec 定义的 API。
- 验证 pass 或 pipeline 对目标 IR 的改写、no-op 与顺序约束。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-PASS-REGISTRY-001 | 边界/异常 | register pass duplicate fails | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_register_pass_duplicate_fails`。 | “register pass duplicate fails”场景按公开错误语义失败或被拒绝。 | `test_register_pass_duplicate_fails` |
| TC-PASS-REGISTRY-002 | 边界/异常 | register pipeline duplicate fails | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_register_pipeline_duplicate_fails`。 | “register pipeline duplicate fails”场景按公开错误语义失败或被拒绝。 | `test_register_pipeline_duplicate_fails` |
| TC-PASS-REGISTRY-003 | 公开入口 | build registered pass unknown | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_pass_unknown`。 | 公开入口在“build registered pass unknown”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_pass_unknown` |
| TC-PASS-REGISTRY-004 | 公开入口 | build registered pass not constructible | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_pass_not_constructible`。 | 公开入口在“build registered pass not constructible”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_pass_not_constructible` |
| TC-PASS-REGISTRY-005 | 公开入口 | build registered pipeline unknown | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_pipeline_unknown`。 | 公开入口在“build registered pipeline unknown”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_pipeline_unknown` |
| TC-PASS-REGISTRY-006 | 公开入口 | build registered pipeline must return pass manager | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_pipeline_must_return_pass_manager`。 | 公开入口在“build registered pipeline must return pass manager”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_pipeline_must_return_pass_manager` |
| TC-PASS-REGISTRY-007 | 公开入口 | list registered are sorted | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_list_registered_are_sorted`。 | 公开入口在“list registered are sorted”场景下可导入、构造、注册或按名称发现。 | `test_list_registered_are_sorted` |
| TC-PASS-REGISTRY-008 | 公开入口 | build registered outline device kernel pass | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_outline_device_kernel_pass`。 | 公开入口在“build registered outline device kernel pass”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_outline_device_kernel_pass` |
| TC-PASS-REGISTRY-008A | 公开入口 | lower-dma-memory-hierarchy apply_op options | 加载内置 pass。 | 运行 `test_build_registered_dma_memory_hierarchy_apply_op_pass`。 | registry 能构造 `lower-dma-memory-hierarchy`，透传 `apply_op`，并应用通用 `fold=false`。 | `test_build_registered_dma_memory_hierarchy_apply_op_pass` |
| TC-PASS-REGISTRY-009 | 公开入口 | build registered tile analysis pass | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_tile_analysis_pass`。 | 公开入口在“build registered tile analysis pass”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_tile_analysis_pass` |
| TC-PASS-REGISTRY-010 | 公开入口 | build registered tile reduce pass | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_tile_reduce_pass`。 | 公开入口在“build registered tile reduce pass”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_tile_reduce_pass` |
| TC-PASS-REGISTRY-011 | 公开入口 | build registered tile elewise pass | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_tile_elewise_pass`。 | 公开入口在“build registered tile elewise pass”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_tile_elewise_pass` |
| TC-PASS-REGISTRY-012 | 公开入口 | registry surviving public paths match consumer matrix | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_registry_surviving_public_paths_match_consumer_matrix`。 | 公开入口在“registry surviving public paths match consumer matrix”场景下可导入、构造、注册或按名称发现。 | `test_registry_surviving_public_paths_match_consumer_matrix` |
| TC-PASS-REGISTRY-013 | 公开入口 | build registered NN lowering pass is module pass | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_nn_lowering_pass_is_module_pass`。 | 公开入口在“build registered NN lowering pass is module pass”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_nn_lowering_pass_is_module_pass` |
| TC-PASS-REGISTRY-014 | 公开入口 | build registered launch kernel cost func pass | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_launch_kernel_cost_func_pass`。 | 公开入口在“build registered launch kernel cost func pass”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_launch_kernel_cost_func_pass` |
| TC-PASS-REGISTRY-015 | 公开入口 | build registered launch kernel cost func default kind | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_launch_kernel_cost_func_default_kind`。 | 公开入口在“build registered launch kernel cost func default kind”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_launch_kernel_cost_func_default_kind` |
| TC-PASS-REGISTRY-016 | 边界/异常 | build registered launch kernel cost func rejects invalid kind | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_build_registered_launch_kernel_cost_func_rejects_invalid_kind`。 | “build registered launch kernel cost func rejects invalid kind”场景按公开错误语义失败或被拒绝。 | `test_build_registered_launch_kernel_cost_func_rejects_invalid_kind` |
| TC-PASS-REGISTRY-017 | 公开入口 | build registered module pass | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_module_pass`。 | 公开入口在“build registered module pass”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_module_pass` |
| TC-PASS-REGISTRY-018 | 公开入口 | build registered module pass with options | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_module_pass_with_options`。 | 公开入口在“build registered module pass with options”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_module_pass_with_options` |
| TC-PASS-REGISTRY-019 | 公开入口 | build registered buffer results to out params pass | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_buffer_results_to_out_params_pass`。 | 公开入口在“build registered buffer results to out params pass”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_buffer_results_to_out_params_pass` |
| TC-PASS-REGISTRY-020 | 公开入口 | build registered decompass pass | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_decompass_pass`。 | 公开入口在“build registered decompass pass”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_decompass_pass` |
| TC-PASS-REGISTRY-021 | 公开入口 | build registered inline pass | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_inline_pass`。 | 公开入口在“build registered inline pass”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_inline_pass` |
| TC-PASS-REGISTRY-022 | 公开入口 | build registered pass accepts universal fold option | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_pass_accepts_universal_fold_option`。 | 公开入口在“build registered pass accepts universal fold option”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_pass_accepts_universal_fold_option` |
| TC-PASS-REGISTRY-023 | 边界/异常 | build registered pass rejects invalid fold option | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_build_registered_pass_rejects_invalid_fold_option`。 | “build registered pass rejects invalid fold option”场景按公开错误语义失败或被拒绝。 | `test_build_registered_pass_rejects_invalid_fold_option` |
| TC-PASS-REGISTRY-023A | 公开入口 | memory-pool rewrite/alignment options | 加载内置 pass 并提供 `rewrite/fold/alignment` option。 | 运行 `test_build_registered_memory_pool_alignment_options`。 | registry 构造 `MemoryPoolPass`，`rewrite=True`、`fold=False`、`alignment=0`。 | `test_build_registered_memory_pool_alignment_options` |
| TC-PASS-REGISTRY-023B | 边界/异常 | memory-pool alignment/options 非法值 | 准备非法 `rewrite`、非法 `alignment` 或未知 option。 | 运行 `test_build_registered_memory_pool_alignment_rejects_invalid_options`。 | registry 报 `PassRegistryError: pass 'memory-pool' option error: <原因>`。 | `test_build_registered_memory_pool_alignment_rejects_invalid_options` |
| TC-PASS-REGISTRY-024 | 公开入口 | build registered attach arch information pass | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_attach_arch_information_pass`。 | 公开入口在“build registered attach arch information pass”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_attach_arch_information_pass` |
| TC-PASS-REGISTRY-025 | 边界/异常 | registry old lowering paths fail fast | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_registry_old_lowering_paths_fail_fast`。 | “registry old lowering paths fail fast”场景按公开错误语义失败或被拒绝。 | `test_registry_old_lowering_paths_fail_fast` |
| TC-PASS-REGISTRY-026 | 边界/异常 | registry retired analysis pass name fails fast | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_registry_retired_analysis_pass_name_fails_fast`。 | “registry retired analysis pass name fails fast”场景按公开错误语义失败或被拒绝。 | `test_registry_retired_analysis_pass_name_fails_fast` |
| TC-PASS-REGISTRY-027 | 公开入口 | build registered symbol buffer hoist pass | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_symbol_buffer_hoist_pass`。 | 公开入口在“build registered symbol buffer hoist pass”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_symbol_buffer_hoist_pass` |
| TC-PASS-REGISTRY-028 | 公开入口 | build registered npu demo lowering pipeline | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_npu_demo_lowering_pipeline`。 | 公开入口在“build registered npu demo lowering pipeline”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_npu_demo_lowering_pipeline` |
| TC-PASS-REGISTRY-029 | pass 改写 | load builtin passes is idempotent | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_load_builtin_passes_is_idempotent`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“load builtin passes is idempotent”场景。 | `test_load_builtin_passes_is_idempotent` |
| TC-PASS-REGISTRY-030 | pass 改写 | load builtin passes after reload registers default lowering | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_load_builtin_passes_after_reload_registers_default_lowering`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“load builtin passes after reload registers default lowering”场景。 | `test_load_builtin_passes_after_reload_registers_default_lowering` |
| TC-PASS-REGISTRY-031 | 公开入口 | build registered npu demo lowering pipeline with options | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_npu_demo_lowering_pipeline_with_options`。 | 公开入口在“build registered npu demo lowering pipeline with options”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_npu_demo_lowering_pipeline_with_options` |
| TC-PASS-REGISTRY-032 | 边界/异常 | build registered npu demo lowering pipeline rejects unknown option | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_build_registered_npu_demo_lowering_pipeline_rejects_unknown_option`。 | “build registered npu demo lowering pipeline rejects unknown option”场景按公开错误语义失败或被拒绝。 | `test_build_registered_npu_demo_lowering_pipeline_rejects_unknown_option` |
| TC-PASS-REGISTRY-033 | 公开入口 | build registered pass with options | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_pass_with_options`。 | 公开入口在“build registered pass with options”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_pass_with_options` |
| TC-PASS-REGISTRY-034 | 公开入口 | build registered pass options not supported | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_pass_options_not_supported`。 | 公开入口在“build registered pass options not supported”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_pass_options_not_supported` |
| TC-PASS-REGISTRY-035 | 边界/异常 | build registered pass option error | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_build_registered_pass_option_error`。 | “build registered pass option error”场景按公开错误语义失败或被拒绝。 | `test_build_registered_pass_option_error` |
| TC-PASS-REGISTRY-036 | 公开入口 | build registered pipeline with options | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_pipeline_with_options`。 | 公开入口在“build registered pipeline with options”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_pipeline_with_options` |
| TC-PASS-REGISTRY-037 | 公开入口 | build registered pipeline options not supported | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_build_registered_pipeline_options_not_supported`。 | 公开入口在“build registered pipeline options not supported”场景下可导入、构造、注册或按名称发现。 | `test_build_registered_pipeline_options_not_supported` |
| TC-PASS-REGISTRY-038 | 边界/异常 | build registered pipeline option error | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_build_registered_pipeline_option_error`。 | “build registered pipeline option error”场景按公开错误语义失败或被拒绝。 | `test_build_registered_pipeline_option_error` |
