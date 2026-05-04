# core/config

## 功能简介

- 定义项目级公共配置底座，统一承载显式公开的 target、dump_dir 与 runtime trance 配置及稳定读写接口。
- 当前公共配置文件是公开 target 配置真源；`mlir_gen`、`dsl_run`、`gen_kernel`/`EmitCContext` 相关公开入口不得再接收任意 `config` 字典承载行为开关。
- `dump_dir` 是公开诊断落盘配置真源；`dsl_run(...)` 不再通过自身入参接收该选项。
- `trance_enabled` 是 runtime kernel log 的公开开关；工具、源码生成与执行链路不得另增同义入口参数。
- 外部值拒绝与 Python callee 调用均为默认开启行为，不提供公开配置开关。

## API 列表

- `set_target(value: str | None) -> None`
- `get_target() -> str | None`
- `set_dump_dir(value: str | Path | None) -> None`
- `get_dump_dir() -> Path | None`
- `set_trance_enabled(value: bool) -> None`
- `get_trance_enabled() -> bool`
- `reset_config() -> None`
- `class CoreConfigSnapshot(target: str | None, dump_dir: Path | None, trance_enabled: bool)`
- `snapshot_config() -> CoreConfigSnapshot`
- `restore_config(snapshot: CoreConfigSnapshot) -> None`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/core/config.md`](../../spec/core/config.md)
- `test`：[`test/core/test_config.py`](../../test/core/test_config.py)
- `功能实现`：[`kernel_gen/core/config.py`](../../kernel_gen/core/config.py)

## 依赖

- 无

## API详细说明

### `set_target(value: str | None) -> None`

- api：`set_target(value: str | None) -> None`
- 参数：
  - `value`：当前接口处理或写入的业务值，作为生成、转换、比较或存储语义的主要输入；类型 `str | None`；无默认值，调用方必须显式提供；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  set_target(value=value)
  ```
- 功能说明：设置 `target`。
- 注意事项：仅接受 `str | None`；传入 `None` 表示清空当前显式目标；target 配置只能通过 `set_target/get_target` 读写，不提供 `dict` 式任意 key 入口。

### `get_target() -> str | None`

- api：`get_target() -> str | None`
- 参数：无。
- 返回值：`str | None`。
- 使用示例：

  ```python
  result = get_target()
  ```
- 功能说明：读取 `target`。
- 注意事项：返回 `None` 表示当前没有显式 target 设置；调用方不得读取本模块内部变量替代该接口。

### `set_dump_dir(value: str | Path | None) -> None`

- api：`set_dump_dir(value: str | Path | None) -> None`
- 参数：
  - `value`：当前接口处理或写入的业务值，作为生成、转换、比较或存储语义的主要输入；类型 `str | Path | None`；无默认值，调用方必须显式提供；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  set_dump_dir(value=value)
  ```
- 功能说明：设置 `dump_dir`。
- 注意事项：仅接受 `str | Path | None`；`None` 与空字符串都关闭诊断产物落盘；`dsl_run(...)` 从本配置读取 `dump_dir`，不得另设公开 `dump_dir` 入参。

### `get_dump_dir() -> Path | None`

- api：`get_dump_dir() -> Path | None`
- 参数：无。
- 返回值：`Path | None`。
- 使用示例：

  ```python
  result = get_dump_dir()
  ```
- 功能说明：读取 `dump_dir`。
- 注意事项：返回 `None` 表示当前未启用诊断产物落盘；调用方不得读取本模块内部变量替代该接口。

### `reset_config() -> None`

- api：`reset_config() -> None`
- 参数：无。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  reset_config()
  ```
- 功能说明：执行 `reset_config`。
- 注意事项：该接口会把 `target` 与 `dump_dir` 恢复为 `None`，并把 `trance_enabled` 恢复为 `False`；测试和工具入口应在跨 case 修改配置后调用该接口或使用 `snapshot_config/restore_config` 恢复现场。

### `set_trance_enabled(value: bool) -> None`

- api：`set_trance_enabled(value: bool) -> None`
- 参数：
  - `value`：runtime trance kernel log 开关；类型 `bool`；必填；`True` 表示编译链注入 `TRANCE` 宏并在运行期输出日志，`False` 表示完全关闭该能力。
- 返回值：无返回值；调用成功表示开关已更新。
- 使用示例：

  ```python
  from kernel_gen.core.config import set_trance_enabled

  set_trance_enabled(True)
  ```
- 功能说明：设置 runtime trance kernel log 是否开启。
- 注意事项：仅接受 `bool`；非法类型必须按公开错误语义失败，错误文本为 `trance_enabled must be bool`；不得通过 `dsl_run(...)`、`gen_kernel(...)`、runner 或执行引擎新增平行开关参数。

### `get_trance_enabled() -> bool`

- api：`get_trance_enabled() -> bool`
- 参数：无。
- 返回值：`bool`，`True` 表示 runtime trance 当前开启。
- 使用示例：

  ```python
  from kernel_gen.core.config import get_trance_enabled

  enabled = get_trance_enabled()
  ```
- 功能说明：读取 runtime trance kernel log 开关。
- 注意事项：返回值只表示当前全局公开配置状态；调用方不得读取本模块内部变量替代该接口。

### `class CoreConfigSnapshot(target: str | None, dump_dir: Path | None, trance_enabled: bool)`

- api：`class CoreConfigSnapshot(target: str | None, dump_dir: Path | None, trance_enabled: bool)`
- 参数：
  - `target`：目标对象、目标名称或目标缓冲区，指定当前操作写入或作用的位置；类型 `str | None`；无默认值，调用方必须显式提供；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `dump_dir`：诊断输出目录，指定 IR、源码或中间产物写入位置；类型 `Path | None`；无默认值，调用方必须显式提供；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `trance_enabled`：runtime trance kernel log 开关；类型 `bool`；无默认值，调用方必须显式提供；非法值按该 API 的公开错误语义处理。
- 返回值：`CoreConfigSnapshot` 实例。
- 使用示例：

  ```python
  core_config_snapshot = CoreConfigSnapshot(target=target, dump_dir=dump_dir, trance_enabled=False)
  ```
- 功能说明：构造 `CoreConfigSnapshot` 实例。
- 注意事项：该类型只保存公开 `target`、`dump_dir` 与 `trance_enabled` 快照；不得塞入任意 dict、硬件配置、emit 上下文状态或临时生成状态。

### `snapshot_config() -> CoreConfigSnapshot`

- api：`snapshot_config() -> CoreConfigSnapshot`
- 参数：无。
- 返回值：`CoreConfigSnapshot`。
- 使用示例：

  ```python
  result = snapshot_config()
  ```
- 功能说明：执行 `snapshot_config`。
- 注意事项：快照用于工具入口临时设置 target 或 dump_dir 后恢复调用前状态，避免 pytest 或嵌套调用串状态；不得把快照对象当作可变配置入口。

### `restore_config(snapshot: CoreConfigSnapshot) -> None`

- api：`restore_config(snapshot: CoreConfigSnapshot) -> None`
- 参数：
  - `snapshot`：快照数据，用于记录或比较当前对象在某一时刻的状态；类型 `CoreConfigSnapshot`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  restore_config(snapshot=snapshot)
  ```
- 功能说明：执行 `restore_config`。
- 注意事项：只接受 `CoreConfigSnapshot`，不接受任意 dict；该接口会恢复快照中的 `target`、`dump_dir` 与 `trance_enabled`，不会恢复未列入本文件 API 的内部状态。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 本文件只定义公共行为配置底座，不承载单次生成状态。
- 未在本文件 `API 列表` 中显式列出的配置项，都不是公开配置。
- target 配置对外只能通过 `set_target/get_target` 接口读写，不提供 `dict` 式任意 key 入口。
- `EmitCContext` 的 SSA 名字表、缩进层级、runtime args、解析环境、callee registry/compiler 与 loop vars 都不是公共配置，不得迁入本文件。
- `hardware` 不属于公共 `config` 底座职责；这类硬件结构化信息应放在 `target` 侧收口。
- `dump_dir` 只承载诊断产物根目录；pass IR、`gen_kernel(...)` 最终源码和 runtime trance 文件可按该目录派生落盘，但源码文本本身和执行结果不属于 config 状态。
- `trance_enabled` 只控制 runtime kernel log 宏注入和运行期输出，不改变 IR、源码生成结果、数学语义或执行成功条件。
- 非公开 helper 仅允许存在于本文件内部，禁止跨文件调用。

## 测试

- 测试文件：`test/core/test_config.py`
- 执行命令：`pytest -q test/core/test_config.py`

### 测试目标

- 验证 `set_target/get_target/set_dump_dir/get_dump_dir/set_trance_enabled/get_trance_enabled/reset/snapshot/restore` 公开接口的稳定行为，并验证非法类型输入会稳定失败。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-CORE-CONFIG-001 | 解析/打印 | target round trip | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_target_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_target_round_trip` |
| TC-CORE-CONFIG-002 | 解析/打印 | dump dir round trip | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_dump_dir_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_dump_dir_round_trip` |
| TC-CORE-CONFIG-003 | 边界/异常 | config setters reject invalid types | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_config_setters_reject_invalid_types`。 | “config setters reject invalid types”场景按公开错误语义失败或被拒绝。 | `test_config_setters_reject_invalid_types` |
| TC-CORE-CONFIG-004 | 公开入口 | reset config restores public defaults | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_reset_config_restores_public_defaults`。 | 公开入口在“reset config restores public defaults”场景下可导入、构造、注册或按名称发现。 | `test_reset_config_restores_public_defaults` |
| TC-CORE-CONFIG-005 | 解析/打印 | snapshot and restore config round trip | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_snapshot_and_restore_config_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_snapshot_and_restore_config_round_trip` |
| TC-CORE-CONFIG-006 | 公开入口 | trance enabled round trip | 设置、读取、快照和恢复 runtime trance 开关。 | 运行 `test_trance_enabled_round_trip`。 | `set_trance_enabled(True)` 后读取为 `True`，`reset_config()` 后恢复为 `False`，非法类型被拒绝。 | `test_trance_enabled_round_trip` |
