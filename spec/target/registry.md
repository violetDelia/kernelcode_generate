# registry.md

## 功能简介

- 定义 target 注册中心的规范，负责提供文件化固定 target 与目录 target 的统一注册/查询入口。
- 支持三类来源：文件化固定 target、`json` 与 `txt`；其中 `json/txt` 可混用。
- target 信息用于驱动 `arch` 相关 operation/dialect/include-runtime 的“能力检查”和“硬件参数读取”，例如 `thread_num`、`sm_memory_size`、`arch.launch`、`arch.barrier`。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`咯咯咯`
- `spec`：[`spec/target/registry.md`](../../spec/target/registry.md)
- `功能实现`：[`kernel_gen/target/registry.py`](../../kernel_gen/target/registry.py)
- `test`：[`test/target/test_target_registry.py`](../../test/target/test_target_registry.py)

## 依赖

- [`spec/dialect/arch.md`](../../spec/dialect/arch.md)：读取 target 后端能力并约束 arch op 的合法性与结果类型。
- [`spec/operation/arch.md`](../../spec/operation/arch.md)：读取 target 后端硬件值并构造 operation 层返回对象。

## 目标

- 统一 target 配置加载流程，避免硬编码后端差异。
- 让 operation/dialect 在不绑定具体后端实现的前提下，读取标准硬件参数。
- 保持配置文件可读、可扩展、可校验。
- 为约定 target 冻结固定模板、launch 能力上限与能力矩阵，避免下游 codegen/runtime 再次推断硬件值或误放开未支持能力。
- 为 `analysis` 主线提供正式 baseline 来源；当前需要由 registry 对 `npu_demo` 暴露 `path_bandwidth / path_latency_ns / theoretical_compute` 三类默认参数。

## 限制与边界

- target 名称只能使用小写字母、数字、下划线，且必须与文件名（不含扩展名）一致。
- 同名 target 不能重复注册。
- `arch.supported_ops` 与 `arch.unsupported_ops` 不能有交集。
- registry 只负责“配置解析与查询”；不负责具体后端驱动初始化、设备探测或运行时调度。
- 当硬件字段缺失时，调用方必须使用自身回退逻辑（例如返回符号值或动态 shape），registry 不自动补默认业务值。
- `analysis` 默认参数与硬件参数不同：当前只对 `npu_demo` 暴露正式 analysis baseline；若 `analysis` 侧读取时缺字段，必须显式失败，不允许静默回退到调用点手写常量。
- `path_bandwidth` 与 `path_latency_ns` 的 key 空间必须与 analysis 主线的正式 `MemoryPath` 文本值一致；不得继续引入自由字符串 path。
- 对显式白名单 target，白名单外能力查询必须固定判定为未启用；不得把未列入白名单的 `arch.*` 能力视为默认可用。
- `is_arch_op_supported(...)` 的稳定输入域是 `arch.*` 能力键；`launch`、`barrier` 这类未带 `arch.` 前缀的字符串不属于 registry 公共查询接口的稳定输入。

## 配置格式

### JSON 格式

```json
{
  "name": "gpu_a",
  "arch": {
    "supported_ops": ["arch.get_thread_id", "arch.get_thread_num"],
    "unsupported_ops": ["arch.get_subthread_id"]
  },
  "hardware": {
    "thread_num": 256,
    "block_num": 4096,
    "subthread_num": 1,
    "sm_memory_size": 65536,
    "lm_memory_size": 32768,
    "tsm_memory_size": 16384,
    "tlm1_memory_size": 4096,
    "tlm2_memory_size": 2048,
    "tlm3_memory_size": 2048
  }
}
```

字段说明：

- `name (str)`：target 名称。
- `arch.supported_ops (list[str], 可选)`：显式支持的 `arch.*` op 白名单。
- `arch.unsupported_ops (list[str], 可选)`：显式不支持的 `arch.*` op 黑名单。
- `hardware (dict[str, int], 可选)`：硬件参数表，值必须是整数。

### TXT 格式

文本按 `key=value` 组织，支持空行与 `#` 注释。

```txt
name=cpu
arch.supported_ops=
arch.unsupported_ops=arch.get_thread_id
hw.thread_num=1
hw.block_num=1
hw.subthread_num=1
hw.sm_memory_size=0
hw.lm_memory_size=0
hw.tsm_memory_size=0
hw.tlm1_memory_size=0
hw.tlm2_memory_size=0
hw.tlm3_memory_size=0
```

字段映射：

- `name` -> `TargetSpec.name`
- `arch.supported_ops` -> `TargetSpec.arch_supported_ops`
- `arch.unsupported_ops` -> `TargetSpec.arch_unsupported_ops`
- `hw.thread_num` -> `hardware["thread_num"]`
- `hw.block_num` -> `hardware["block_num"]`
- `hw.subthread_num` -> `hardware["subthread_num"]`
- `hw.sm_memory_size` -> `hardware["sm_memory_size"]`
- `hw.lm_memory_size` -> `hardware["lm_memory_size"]`
- `hw.tsm_memory_size` -> `hardware["tsm_memory_size"]`
- `hw.tlm1_memory_size` -> `hardware["tlm1_memory_size"]`
- `hw.tlm2_memory_size` -> `hardware["tlm2_memory_size"]`
- `hw.tlm3_memory_size` -> `hardware["tlm3_memory_size"]`

解析规则：

- `arch.*` 的值按英文逗号分隔。
- 对于 `arch.supported_ops`：
  - 一般 target：空值归一化为“空集合”（显式白名单为空，表示不允许任何 `arch.*` op）。
  - `name=cpu` 的 `cpu.txt`：空值归一化为 `None`（未配置白名单），最终语义由 `arch.unsupported_ops` 黑名单决定。
- 对于 `arch.unsupported_ops`：空值归一化为“空集合”。
- `hw.*` 必须可解析为整数。
- 未识别 key 必须报错，防止静默拼写错误。

### 文件化固定 target

除目录中的 `json/txt` 文件外，registry 可为保留 target 提供文件化固定 target。本轮必须固定 `npu_demo` 的能力矩阵与硬件参数，调用方通过 `kernel_gen/target/targets/npu_demo.txt` 获得该 target 的唯一标准数据源，不再要求额外提供 `npu_demo.json`。

`npu_demo` 的固定模板语义等价于：

```python
TargetSpec(
    name="npu_demo",
    arch_supported_ops={
        "arch.get_block_id",
        "arch.get_block_num",
        "arch.get_thread_id",
        "arch.get_thread_num",
        "arch.get_subthread_id",
        "arch.get_subthread_num",
        "arch.get_dynamic_memory",
        "arch.barrier",
        "arch.launch",
    },
    arch_unsupported_ops=set(),
    hardware={
        "block_num": 1,
        "thread_num": 1,
        "subthread_num": 1,
        "sm_memory_size": 0,
        "lm_memory_size": 0,
        "tsm_memory_size": 24576,
        "tlm1_memory_size": 1024,
        "tlm2_memory_size": 512,
        "tlm3_memory_size": 512,
    },
)
```

语义说明：

- `npu_demo` 使用显式白名单；除上述 `arch.get_*` 查询、`arch.get_dynamic_memory`、`arch.barrier` 与 `arch.launch` 外，其他能力查询固定判定为未启用。
- `arch.launch` / `arch.barrier` 是 `npu_demo` P0 真实并行 + 同步路径的正式能力键；旧名 `arch.launch_kernel` 不再进入 `npu_demo` 已启用能力矩阵。
- `launch` 与 `barrier` 这类未带 `arch.` 前缀的字符串不属于 registry 的稳定输入域；若上层错误传入此类字符串，结果必须仍然收敛为未启用。
- `block_num=1`、`thread_num=1`、`subthread_num=1` 表示 `npu_demo` P0 launch 能力上限：`block` 固定为 `1`、`subthread` 固定为 `1`、`thread` 固定为 `1`；这些字段不再直接表示 launched body 中当前可见的运行时 extent。
- `sm_memory_size=0` 与 `lm_memory_size=0` 表示 `npu_demo` 不提供 `SM/LM` 动态内存容量；`tsm_memory_size=24576`、`tlm1_memory_size=1024`、`tlm2_memory_size=512`、`tlm3_memory_size=512` 为固定片上容量。
- `npu_demo` 的标准注册入口是 registry 的文件化固定 target 加载流程，标准 target 文件路径是 `kernel_gen/target/targets/npu_demo.txt`；标准查询入口是 `is_arch_op_supported(...)`、`get_target_hardware(...)` 与 `get_current_target_hardware(...)`。
- `npu_demo` 的 analysis 默认参数也由 registry 固定提供，当前至少包含：
  - `path_bandwidth["GM->LM"] = 64`
  - `path_bandwidth["GM->SM"] = 96`
  - `path_bandwidth["GM->TSM"] = 32`
  - `path_bandwidth["TSM->TLM"] = 16`
  - `path_latency_ns["GM->LM"] = 20`
  - `path_latency_ns["GM->SM"] = 18`
  - `path_latency_ns["GM->TSM"] = 24`
  - `path_latency_ns["TSM->TLM"] = 8`
  - `theoretical_compute["scalar"] = 1`
  - `theoretical_compute["vector"] = 8`
  - `theoretical_compute["tensor"] = 64`
- `analysis` 侧读取这些值时，不能再在 `AnalysisConfig(...)` 调用点重复手写同样常量。

## 公开接口

### `TargetSpec`

功能说明：

- 描述一个 target 的标准化元数据与能力。

字段：

- `name: str`
- `arch_supported_ops: set[str] | None`
- `arch_unsupported_ops: set[str]`
- `hardware: dict[str, int]`

使用示例：

```python
spec = TargetSpec(
    name="cpu",
    arch_supported_ops=None,
    arch_unsupported_ops={"arch.get_thread_id"},
    hardware={"thread_num": 1, "sm_memory_size": 0},
)
```

### `load_targets(directory: Path) -> dict[str, TargetSpec]`

功能说明：

- 扫描目录并加载 `*.json` 与 `*.txt` target 文件。
- 成功加载后返回“本次加载集合”。
- 文件化固定 target 不依赖目录扫描来源；`load_targets(...)` 不是 `npu_demo` 的唯一注册入口。

使用示例：

```python
from pathlib import Path
from kernel_gen.target import registry

loaded = registry.load_targets(Path("kernel_gen/target/targets"))
```

### `register_target(spec: TargetSpec) -> None`

功能说明：

- 注册单个 target；用于测试或运行时增量注入。
- 文件化固定 target（如 `npu_demo`）不要求调用方手工调用该接口注册。

### `is_arch_op_supported(target: str, op_name: str) -> bool`

功能说明：

- 判断某个 `arch.*` 能力键是否被指定 target 支持。
- `op_name` 的稳定输入域限定为 `arch.*`；`launch`、`barrier` 等上层能力语义不作为本接口的标准输入。

### `get_target_hardware(target: str, key: str) -> int | None`

功能说明：

- 按 target 名称读取硬件参数；缺失返回 `None`。

### `get_current_target_hardware(key: str) -> int | None`

功能说明：

- 按“当前 target”读取硬件参数；未设置当前 target 或字段缺失时返回 `None`。

### `get_target_analysis_defaults(target: str) -> dict[str, dict[str, int]]`

功能说明：

- 按 target 名称读取 analysis 默认参数。
- 当前正式收口到 `npu_demo`；返回至少包含：
  - `path_bandwidth`
  - `path_latency_ns`
  - `theoretical_compute`

## 与 arch 层的联动约束

- `operation/arch` 与 include/runtime 需要区分“能力上限”和“当前 launch 值”：registry 只提供能力上限与静态容量，不直接承诺 launched body 中的当前 extent。
- 在无 launch 上下文时，`operation/arch` 查询数量类 helper（如 `get_thread_num`）可读取 `hardware` 作为能力上限或静态回退值；一旦进入 launched body，当前值必须由 runtime 上下文提供。
- `operation/arch.get_dynamic_memory(space)` 可读取 `*_memory_size` 作为静态 shape；无值时回退动态 shape。
- `dialect/arch` 在 verifier 阶段可根据“当前 target”校验 op 支持性。
- 当 `target="npu_demo"` 时，`block_num=1`、`thread_num=1`、`subthread_num=1` 必须作为 P0 能力上限读取；`SM/LM` 动态内存容量固定为 `0`，`TSM/TLM1/TLM2/TLM3` 动态内存容量固定为 `24576/1024/512/512`。
- 当 `target="npu_demo"` 时，`analysis` 侧的 `path_bandwidth / path_latency_ns / theoretical_compute` 默认参数也必须由 registry 提供；当前不允许 `analysis` 在调用点长期手写这些常量。
- 当 `target="npu_demo"` 时，`arch.launch` 与 `arch.barrier` 通过 `is_arch_op_supported(...)` 查询必须返回已启用；旧名 `arch.launch_kernel` 必须保持未启用。

## CPU TXT 示例

以下是推荐的 `cpu.txt` 模板内容：

```txt
name=cpu
arch.supported_ops=
arch.unsupported_ops=arch.get_thread_id
hw.thread_num=1
hw.block_num=1
hw.subthread_num=1
hw.sm_memory_size=0
hw.lm_memory_size=0
hw.tsm_memory_size=0
hw.tlm1_memory_size=0
hw.tlm2_memory_size=0
hw.tlm3_memory_size=0
```

建议落盘路径：

- `kernel_gen/target/targets/cpu.txt`

语义说明：

- 对 `cpu.txt` 而言，`arch.supported_ops=` 的空值会被归一化为 `None`（未配置白名单），因此 `cpu` 默认允许除 `arch.unsupported_ops` 外的 `arch.*` 查询 op。
- 以上述示例为准，`arch.get_thread_id` 由黑名单拒绝，`arch.get_block_num` 等不在黑名单中的 op 默认可用。

## 测试清单

- 能加载合法 `json` target。
- 能加载合法 `txt` target。
- `json` 与 `txt` 混合目录可同时加载。
- 默认目录 `kernel_gen/target/targets` 加载后，`cpu.txt` 的 `arch.supported_ops=` 空值应归一化为 `None`，并保持 `arch.get_block_num` 可用、`arch.get_thread_id` 受黑名单限制。
- 默认目录重复加载应保持幂等，不得因内置 `cpu` 与 `cpu.txt` 冲突而失败。
- `npu_demo` 固定 target 应通过标准查询入口满足以下能力/容量值：`block_num=1`、`thread_num=1`、`subthread_num=1`、`sm_memory_size=0`、`lm_memory_size=0`、`tsm_memory_size=24576`、`tlm1_memory_size=1024`、`tlm2_memory_size=512`、`tlm3_memory_size=512`。
- `npu_demo.txt` 作为唯一标准 target 数据源，必须能被 `load_targets(Path("kernel_gen/target/targets"))` 一并加载；默认目录重复加载应保持幂等，不得因 `npu_demo` 与内置注册冲突而失败。
- `npu_demo` 固定模板应通过 `get_target_analysis_defaults("npu_demo")` 暴露 analysis 默认参数；至少覆盖 `path_bandwidth["GM->LM"]`、`path_latency_ns["GM->LM"]` 与 `theoretical_compute["scalar"/"tensor"]`。
- `npu_demo` 的 `arch.launch` / `arch.barrier` 查询必须固定判定为已启用；旧名 `arch.launch_kernel` 与未带 `arch.` 前缀的 `launch` / `barrier` 不属于已启用能力。
- `name` 缺失、格式非法、与文件名不一致时报错。
- `arch.supported_ops` 与 `arch.unsupported_ops` 冲突时报错。
- `hw.*` 非整数时报错。
- 未知 key 报错。
- `get_target_hardware` 与 `get_current_target_hardware` 在“存在/缺失/未设置当前 target”三类场景行为正确。
- 下游待补验收标准建议使用 `test_target_registry_npu_demo_supports_launch_and_barrier_caps`：输入 `target="npu_demo"`；预期通过 `is_arch_op_supported(...)` 读取到 `arch.launch=True`、`arch.barrier=True`、`arch.launch_kernel=False`，并通过 `get_target_hardware(...)` / `get_current_target_hardware(...)` 读到 `block_num=1`、`thread_num=1`、`subthread_num=1`、`sm_memory_size=0`、`lm_memory_size=0`、`tsm_memory_size=24576`、`tlm1_memory_size=1024`、`tlm2_memory_size=512`、`tlm3_memory_size=512`。
