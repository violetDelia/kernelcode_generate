# registry.md

## 功能简介

- 定义 target 注册中心的规范，负责从 target 配置文件加载后端能力，并提供统一查询接口。
- 支持两种配置来源：`json` 与 `txt`，两者可混用。
- target 信息用于驱动 `arch` 相关 operation/dialect 的“能力检查”和“硬件参数读取”，例如 `thread_num`、`sm_memory_size`。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`榕`
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

## 限制与边界

- target 名称只能使用小写字母、数字、下划线，且必须与文件名（不含扩展名）一致。
- 同名 target 不能重复注册。
- `arch.supported_ops` 与 `arch.unsupported_ops` 不能有交集。
- registry 只负责“配置解析与查询”；不负责具体后端驱动初始化、设备探测或运行时调度。
- 当硬件字段缺失时，调用方必须使用自身回退逻辑（例如返回符号值或动态 shape），registry 不自动补默认业务值。

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
    "tlm_memory_size": 8192
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
hw.tlm_memory_size=0
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
- `hw.tlm_memory_size` -> `hardware["tlm_memory_size"]`

解析规则：

- `arch.*` 的值按英文逗号分隔。
- 对于 `arch.supported_ops`：
  - 一般 target：空值归一化为“空集合”（显式白名单为空，表示不允许任何 `arch.*` op）。
  - `name=cpu` 的 `cpu.txt`：空值归一化为 `None`（未配置白名单），最终语义由 `arch.unsupported_ops` 黑名单决定。
- 对于 `arch.unsupported_ops`：空值归一化为“空集合”。
- `hw.*` 必须可解析为整数。
- 未识别 key 必须报错，防止静默拼写错误。

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

使用示例：

```python
from pathlib import Path
from kernel_gen.target import registry

loaded = registry.load_targets(Path("kernel_gen/target/targets"))
```

### `register_target(spec: TargetSpec) -> None`

功能说明：

- 注册单个 target；用于测试或运行时增量注入。

### `is_arch_op_supported(target: str, op_name: str) -> bool`

功能说明：

- 判断某个 `arch.*` op 是否被指定 target 支持。

### `get_target_hardware(target: str, key: str) -> int | None`

功能说明：

- 按 target 名称读取硬件参数；缺失返回 `None`。

### `get_current_target_hardware(key: str) -> int | None`

功能说明：

- 按“当前 target”读取硬件参数；未设置当前 target 或字段缺失时返回 `None`。

## 与 arch 层的联动约束

- `operation/arch` 查询数量类 helper（如 `get_thread_num`）可优先读取 `hardware` 静态值；无值时回退符号语义。
- `operation/arch.get_dynamic_memory(space)` 可读取 `*_memory_size` 作为静态 shape；无值时回退动态 shape。
- `dialect/arch` 在 verifier 阶段可根据“当前 target”校验 op 支持性。

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
hw.tlm_memory_size=0
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
- `name` 缺失、格式非法、与文件名不一致时报错。
- `arch.supported_ops` 与 `arch.unsupported_ops` 冲突时报错。
- `hw.*` 非整数时报错。
- 未知 key 报错。
- `get_target_hardware` 与 `get_current_target_hardware` 在“存在/缺失/未设置当前 target”三类场景行为正确。
