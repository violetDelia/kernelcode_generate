# registry.md

## 功能简介

- 定义 target 注册中心的规范，负责提供目录 target 的统一注册/查询入口。
- 支持 `json` 与 `txt` 两类来源；其中 `npu_demo` 的公开真源是 `kernel_gen/target/targets/npu_demo.txt`，不再以 Python 内置模板形式对外承诺。
- target 信息用于驱动 `arch` 相关 operation/dialect/include-runtime 的“能力检查”和“硬件参数读取”，例如 `thread_num`、`sm_memory_size`、`arch.launch`、`arch.barrier`。

## API 列表

- `class TargetSpec(name: str, arch_supported_ops: set[str] | None, arch_unsupported_ops: set[str], hardware: dict[str, int])`
- `load_targets(directory: Path) -> dict[str, TargetSpec]`
- `register_target(spec: TargetSpec) -> None`
- `set_current_target(target: str | None) -> None`
- `get_current_target() -> str | None`
- `is_arch_op_supported(target: str, op_name: str) -> bool`
- `get_target_hardware(target: str, key: str) -> int | None`
- `get_current_target_hardware(key: str) -> int | None`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/target/registry.md`](../../spec/target/registry.md)
- `功能实现`：[`kernel_gen/target/registry.py`](../../kernel_gen/target/registry.py)
- `test`：[`test/target/test_registry.py`](../../test/target/test_registry.py)

## 依赖

- [`spec/dialect/arch.md`](../../spec/dialect/arch.md)：读取 target 后端能力并约束 arch op 的合法性与结果类型。
- [`spec/operation/arch.md`](../../spec/operation/arch.md)：读取 target 后端硬件值并构造 operation 层返回对象。

## 目标

- 统一 target 配置加载流程，避免硬编码后端差异。
- 让 operation/dialect 在不绑定具体后端实现的前提下，读取标准硬件参数。
- 保持配置文件可读、可扩展、可校验。
- 为约定 target 冻结目录文件语义、launch 能力上限与能力矩阵，避免下游 codegen/runtime 再次推断硬件值或误放开未支持能力。
- 为 `operation/arch.py` 与 `dialect/arch.py` 提供合法的 current target 查询与设置公开入口，避免继续跨文件访问私有 helper。

## API详细说明

### `class TargetSpec(name: str, arch_supported_ops: set[str] | None, arch_unsupported_ops: set[str], hardware: dict[str, int])`

- api：`class TargetSpec(name: str, arch_supported_ops: set[str] | None, arch_unsupported_ops: set[str], hardware: dict[str, int])`
- 参数：
  - `name`：target 名称；类型 `str`；无默认值，调用方必须显式提供；只能使用小写字母、数字、下划线。
  - `arch_supported_ops`：显式支持的 `arch.*` op 白名单；类型 `set[str] | None`；无默认值，调用方必须显式提供；`None` 表示未配置白名单。
  - `arch_unsupported_ops`：显式不支持的 `arch.*` op 黑名单；类型 `set[str]`；无默认值，调用方必须显式提供。
  - `hardware`：硬件参数表；类型 `dict[str, int]`；无默认值，调用方必须显式提供；key 必须属于 registry 支持的硬件字段集合，值必须是整数。
- 返回值：`TargetSpec` 实例。
- 使用示例：

  ```python
  from kernel_gen.target.registry import TargetSpec

  spec = TargetSpec(
      name="cpu",
      arch_supported_ops=None,
      arch_unsupported_ops={"arch.get_thread_id"},
      hardware={"thread_num": 1, "sm_memory_size": 0},
  )
  ```
- 功能说明：描述一个 target 的标准化元数据与能力。
- 注意事项：`arch_supported_ops` 与 `arch_unsupported_ops` 不能有交集；同名 target 不能重复注册；实例字段是公开数据载体，未列入参数的缓存或派生字段不作为公开 API。

### `load_targets(directory: Path) -> dict[str, TargetSpec]`

- api：`load_targets(directory: Path) -> dict[str, TargetSpec]`
- 参数：
  - `directory`：目录路径，指定读取、写入或扫描的根目录；类型 `Path`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`dict[str, TargetSpec]`。
- 使用示例：

  ```python
  from pathlib import Path

  from kernel_gen.target import registry

  loaded = registry.load_targets(Path("kernel_gen/target/targets"))
  ```
- 功能说明：扫描目录并加载 `*.json` 与 `*.txt` target 文件。
- 注意事项：返回值是本次加载集合；target 名称必须与文件名不含扩展名部分一致；`npu_demo` 的公开真源是目录中的 `npu_demo.txt`；加载会注册解析出的 target，重复加载默认目录必须保持幂等。

### `register_target(spec: TargetSpec) -> None`

- api：`register_target(spec: TargetSpec) -> None`
- 参数：
  - `spec`：`spec` 输入值，参与 `register_target` 的公开处理流程；类型 `TargetSpec`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  from kernel_gen.target.registry import TargetSpec, register_target

  spec = TargetSpec("gpu", None, set(), {"thread_num": 256})
  register_target(spec)
  ```
- 功能说明：注册单个 target。
- 注意事项：注册名必须满足 target 命名规则；重复注册非默认 target 必须失败；该接口可用于测试或运行时增量注入。

### `set_current_target(target: str | None) -> None`

- api：`set_current_target(target: str | None) -> None`
- 参数：
  - `target`：目标对象、目标名称或目标缓冲区，指定当前操作写入或作用的位置；类型 `str | None`；无默认值，调用方必须显式提供；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  from kernel_gen.target.registry import set_current_target

  set_current_target("cpu")
  set_current_target(None)
  ```
- 功能说明：设置 current target 名称。
- 注意事项：`None` 表示关闭 current target 校验；非 `None` 值必须已经完成注册；该接口会修改当前 target 公开状态。

### `get_current_target() -> str | None`

- api：`get_current_target() -> str | None`
- 参数：无。
- 返回值：`str | None`。
- 使用示例：

  ```python
  from kernel_gen.target.registry import get_current_target

  target_name = get_current_target()
  ```
- 功能说明：读取 `current_target`。
- 注意事项：未设置时返回 `None`；该接口只读取公开状态，不暴露 registry 内部可变结构。

### `is_arch_op_supported(target: str, op_name: str) -> bool`

- api：`is_arch_op_supported(target: str, op_name: str) -> bool`
- 参数：
  - `target`：目标对象、目标名称或目标缓冲区，指定当前操作写入或作用的位置；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `op_name`：公开名称或符号名；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`bool`，表示判断结果。
- 使用示例：

  ```python
  from kernel_gen.target.registry import is_arch_op_supported

  supported = is_arch_op_supported("cpu", "arch.get_block_num")
  ```
- 功能说明：判断某个 `arch.*` 能力键是否被指定 target 支持。
- 注意事项：`op_name` 的稳定输入域限定为 `arch.*` 能力键；`launch`、`barrier` 等未带 `arch.` 前缀的字符串不属于本接口稳定输入；对显式白名单 target，白名单外能力查询必须固定判定为未启用。

### `get_target_hardware(target: str, key: str) -> int | None`

- api：`get_target_hardware(target: str, key: str) -> int | None`
- 参数：
  - `target`：目标对象、目标名称或目标缓冲区，指定当前操作写入或作用的位置；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `key`：查找键或注册键，用于定位 registry、映射表或缓存中的公开条目；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`int | None`。
- 使用示例：

  ```python
  from kernel_gen.target.registry import get_target_hardware

  thread_num = get_target_hardware("cpu", "thread_num")
  ```
- 功能说明：读取 `target_hardware`。
- 注意事项：缺失字段返回 `None`；registry 不自动补默认业务值，调用方必须使用自身回退逻辑；该接口只读取公开状态，不暴露 registry 内部可变结构。

### `get_current_target_hardware(key: str) -> int | None`

- api：`get_current_target_hardware(key: str) -> int | None`
- 参数：
  - `key`：查找键或注册键，用于定位 registry、映射表或缓存中的公开条目；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`int | None`。
- 使用示例：

  ```python
  from kernel_gen.target.registry import get_current_target_hardware

  thread_num = get_current_target_hardware("thread_num")
  ```
- 功能说明：读取 `current_target_hardware`。
- 注意事项：未设置 current target 或字段缺失时返回 `None`；registry 不自动补默认业务值，调用方必须使用自身回退逻辑；该接口只读取公开状态，不暴露 registry 内部可变结构。


## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- registry 只负责“配置解析与查询”；不负责具体后端驱动初始化、设备探测或运行时调度。
- 当硬件字段缺失时，调用方必须使用自身回退逻辑（例如返回符号值或动态 shape），registry 不自动补默认业务值。
- 下游实现与测试只能通过 `TargetSpec`、`load_targets(...)`、`register_target(...)`、`set_current_target(...)`、`get_current_target(...)`、`is_arch_op_supported(...)`、`get_target_hardware(...)` 与 `get_current_target_hardware(...)` 访问 target registry 能力。

### 配置格式

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

### `npu_demo.txt` 目录 target

- `npu_demo` 的标准注册入口是 `kernel_gen/target/targets/npu_demo.txt`；调用方通过 `load_targets(...)` 从目录加载，registry 不再把 `npu_demo` 当作 Python 内置模板对外承诺。
- `npu_demo.txt` 的字段使用普通 TXT 语法，字段与 `cpu.txt` 同类：`name`、`arch.supported_ops`、`arch.unsupported_ops` 与 `hw.*`。

`kernel_gen/target/targets/npu_demo.txt` 的推荐内容语义等价于：

```txt
name=npu_demo
arch.supported_ops=arch.get_block_id,arch.get_block_num,arch.get_thread_id,arch.get_thread_num,arch.get_subthread_id,arch.get_subthread_num,arch.get_dynamic_memory,arch.barrier,arch.launch
arch.unsupported_ops=arch.launch_kernel
hw.block_num=1
hw.thread_num=1
hw.subthread_num=1
hw.sm_memory_size=0
hw.lm_memory_size=0
hw.tsm_memory_size=24576
hw.tlm1_memory_size=1024
hw.tlm2_memory_size=512
hw.tlm3_memory_size=512
```

语义说明：

- `npu_demo` 使用显式白名单；除上述 `arch.get_*` 查询、`arch.get_dynamic_memory`、`arch.barrier` 与 `arch.launch` 外，其他能力查询固定判定为未启用。
- `arch.launch` / `arch.barrier` 是 `npu_demo` P0 真实并行 + 同步路径的正式能力键；旧名 `arch.launch_kernel` 不再进入 `npu_demo` 已启用能力矩阵。
- `launch` 与 `barrier` 这类未带 `arch.` 前缀的字符串不属于 registry 的稳定输入域；若上层错误传入此类字符串，结果必须仍然收敛为未启用。
- `block_num=1`、`thread_num=1`、`subthread_num=1` 表示 `npu_demo` P0 launch 能力上限：`block` 固定为 `1`、`subthread` 固定为 `1`、`thread` 固定为 `1`；这些字段不再直接表示 launched body 中当前可见的运行时 extent。
- `sm_memory_size=0` 与 `lm_memory_size=0` 表示 `npu_demo` 不提供 `SM/LM` 动态内存容量；`tsm_memory_size=24576`、`tlm1_memory_size=1024`、`tlm2_memory_size=512`、`tlm3_memory_size=512` 为固定片上容量。
- `npu_demo` 的标准注册入口是 `kernel_gen/target/targets/npu_demo.txt`；标准查询入口是 `is_arch_op_supported(...)`、`get_target_hardware(...)` 与 `get_current_target_hardware(...)`。

### helper 说明

- 当前文件内存在若干解析、校验与默认 target 组装 helper。
- 这些 helper 仅用于 `registry.py` 内部复用，不属于公开合同。

### 与 arch 层的联动约束

- `operation/arch` 与 include/runtime 需要区分“能力上限”和“当前 launch 值”：registry 只提供能力上限与静态容量，不直接承诺 launched body 中的当前 extent。
- 在无 launch 上下文时，`operation/arch` 查询数量类 helper（如 `get_thread_num`）可读取 `hardware` 作为能力上限或静态回退值；一旦进入 launched body，当前值必须由 runtime 上下文提供。
- `operation/arch.get_dynamic_memory(space)` 可读取 `*_memory_size` 作为静态 shape；无值时回退动态 shape。
- `dialect/arch` 在 verifier 阶段可根据“当前 target”校验 op 支持性。
- 当 `target="npu_demo"` 时，`block_num=1`、`thread_num=1`、`subthread_num=1` 必须作为 P0 能力上限读取；`SM/LM` 动态内存容量固定为 `0`，`TSM/TLM1/TLM2/TLM3` 动态内存容量固定为 `24576/1024/512/512`。
- 当 `target="npu_demo"` 时，`arch.launch` 与 `arch.barrier` 通过 `is_arch_op_supported(...)` 查询必须返回已启用；旧名 `arch.launch_kernel` 必须保持未启用。

### CPU TXT 示例

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

#

## 测试

- 测试文件：`test/target/test_registry.py`
- 执行命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/target/test_registry.py`

### 测试目标

- 验证本文件 `API 列表` 中公开 API 的稳定行为、边界和错误语义。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-TARGET-REGISTRY-001 | 公开入口 | target registry loads json specs | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_target_registry_loads_json_specs`。 | 公开入口在“target registry loads json specs”场景下可导入、构造、注册或按名称发现。 | `test_target_registry_loads_json_specs` |
| TC-TARGET-REGISTRY-002 | 边界/异常 | target registry rejects invalid specs | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_target_registry_rejects_invalid_specs`, `test_target_registry_rejects_invalid_json_files`。 | “target registry rejects invalid specs”场景按公开错误语义失败或被拒绝。 | `test_target_registry_rejects_invalid_specs`, `test_target_registry_rejects_invalid_json_files` |
| TC-TARGET-REGISTRY-003 | 边界/异常 | target registry rejects conflicting ops | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_target_registry_rejects_conflicting_ops`。 | “target registry rejects conflicting ops”场景按公开错误语义失败或被拒绝。 | `test_target_registry_rejects_conflicting_ops` |
| TC-TARGET-REGISTRY-004 | 边界/异常 | target registry cpu rejects thread id | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_target_registry_cpu_rejects_thread_id`。 | “target registry cpu rejects thread id”场景按公开错误语义失败或被拒绝。 | `test_target_registry_cpu_rejects_thread_id` |
| TC-TARGET-REGISTRY-005 | 公开入口 | target registry loads txt specs | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_target_registry_loads_txt_specs`。 | 公开入口在“target registry loads txt specs”场景下可导入、构造、注册或按名称发现。 | `test_target_registry_loads_txt_specs` |
| TC-TARGET-REGISTRY-006 | 公开入口 | target registry loads mixed formats | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_target_registry_loads_mixed_formats`。 | 公开入口在“target registry loads mixed formats”场景下可导入、构造、注册或按名称发现。 | `test_target_registry_loads_mixed_formats` |
| TC-TARGET-REGISTRY-007 | 公开入口 | target registry loads default cpu directory | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_target_registry_loads_default_cpu_directory`。 | 公开入口在“target registry loads default cpu directory”场景下可导入、构造、注册或按名称发现。 | `test_target_registry_loads_default_cpu_directory` |
| TC-TARGET-REGISTRY-008 | 公开入口 | target registry default directory idempotent load | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_target_registry_default_directory_idempotent_load`。 | 公开入口在“target registry default directory idempotent load”场景下可导入、构造、注册或按名称发现。 | `test_target_registry_default_directory_idempotent_load` |
| TC-TARGET-REGISTRY-009 | 边界/异常 | target registry rejects txt invalid fields | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_target_registry_rejects_txt_invalid_fields`。 | “target registry rejects txt invalid fields”场景按公开错误语义失败或被拒绝。 | `test_target_registry_rejects_txt_invalid_fields` |
| TC-TARGET-REGISTRY-010 | 公开入口 | target registry current target hardware | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_target_registry_current_target_hardware`。 | 公开入口在“target registry current target hardware”场景下可导入、构造、注册或按名称发现。 | `test_target_registry_current_target_hardware` |
| TC-TARGET-REGISTRY-011 | 边界/异常 | target registry set current target rejects unregistered target | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_target_registry_set_current_target_rejects_unregistered_target`, `test_target_registry_public_api_error_matrix`。 | “target registry set current target rejects unregistered target”场景按公开错误语义失败或被拒绝。 | `test_target_registry_set_current_target_rejects_unregistered_target`, `test_target_registry_public_api_error_matrix` |
| TC-TARGET-REGISTRY-012 | 公开入口 | target registry public exports include current target API | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_target_registry_public_exports_include_current_target_api`。 | 公开入口在“target registry public exports include current target API”场景下可导入、构造、注册或按名称发现。 | `test_target_registry_public_exports_include_current_target_api` |
| TC-TARGET-REGISTRY-013 | 公开入口 | target registry npu demo template | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_target_registry_npu_demo_template`。 | 公开入口在“target registry npu demo template”场景下可导入、构造、注册或按名称发现。 | `test_target_registry_npu_demo_template` |
| TC-TARGET-REGISTRY-014 | 边界/异常 | target registry npu demo rejects unsupported ops | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_target_registry_npu_demo_rejects_unsupported_ops`。 | “target registry npu demo rejects unsupported ops”场景按公开错误语义失败或被拒绝。 | `test_target_registry_npu_demo_rejects_unsupported_ops` |
| TC-TARGET-REGISTRY-015 | 公开入口 | target registry npu demo supports launch and barrier caps | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_target_registry_npu_demo_supports_launch_and_barrier_caps`。 | 公开入口在“target registry npu demo supports launch and barrier caps”场景下可导入、构造、注册或按名称发现。 | `test_target_registry_npu_demo_supports_launch_and_barrier_caps` |
| TC-TARGET-REGISTRY-016 | 边界/异常 | target registry rejects invalid load_targets directory | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_target_registry_load_targets_rejects_invalid_directory`。 | 缺失路径和非目录路径均按公开错误语义失败。 | `test_target_registry_load_targets_rejects_invalid_directory` |
