# core/config

## 功能简介

- 定义项目级公共配置底座，统一承载显式公开的 target 与 dump_dir 配置及稳定读写接口。
- 当前公共配置文件是公开 target 配置真源；`mlir_gen`、`dsl_run`、`gen_kernel`/`EmitCContext` 相关公开入口不得再接收任意 `config` 字典承载行为开关。
- `dump_dir` 是公开诊断落盘配置真源；`dsl_run(...)` 不再通过自身入参接收该选项。
- 外部值拒绝与 Python callee 调用均为默认开启行为，不提供公开配置开关。

## API 列表

- `set_target(value: str | None) -> None`
- `get_target() -> str | None`
- `set_dump_dir(value: str | Path | None) -> None`
- `get_dump_dir() -> Path | None`
- `reset_config() -> None`
- `CoreConfigSnapshot(target: str | None, dump_dir: Path | None)`
- `snapshot_config() -> CoreConfigSnapshot`
- `restore_config(snapshot: CoreConfigSnapshot) -> None`

## 文档信息

- 创建者：`OpenAI Codex`
- 最后一次更改：`OpenAI Codex`
- `spec`：[`spec/core/config.md`](../../spec/core/config.md)
- `test`：[`test/core/test_config.py`](../../test/core/test_config.py)
- `功能实现`：[`kernel_gen/core/config.py`](../../kernel_gen/core/config.py)

## 依赖

- 无

## 公开接口

## 配置项说明

### `target`

设置说明：

- 用于显式声明当前调用链预期使用的目标名称。
- 推荐值示例：`cpu`、`npu_demo`。
- 传入 `None` 表示清空当前显式目标，让后续调用方自行决定默认目标或继续保持未指定状态。

示例：

```python
from kernel_gen.core.config import get_target, set_target

set_target("npu_demo")
assert get_target() == "npu_demo"

set_target(None)
assert get_target() is None
```

### `dump_dir`

设置说明：

- 用于显式声明当前 DSL/Pass 诊断产物根目录。
- 推荐值示例：`"dump"`、`Path("dump")`。
- 传入 `None` 或空字符串表示关闭诊断产物落盘。
- `dsl_run(...)` 从本配置读取 `dump_dir`，不得另设公开 `dump_dir` 入参。

示例：

```python
from pathlib import Path

from kernel_gen.core.config import get_dump_dir, set_dump_dir

set_dump_dir("dump")
assert get_dump_dir() == Path("dump")

set_dump_dir(None)
assert get_dump_dir() is None

set_dump_dir("")
assert get_dump_dir() is None
```

### `set_target(value: str | None) -> None`

功能说明：

- 设置公开 `target` 配置。
- 仅接受 `str` 或 `None`。
- 当你希望一次执行链路明确绑定到某个目标时，应先调用这个接口。

使用示例：

```python
from kernel_gen.core.config import get_target, set_target

set_target("npu_demo")
assert get_target() == "npu_demo"
```

### `get_target() -> str | None`

功能说明：

- 读取公开 `target` 配置。
- 返回 `None` 表示当前没有显式目标设置。

### `set_dump_dir(value: str | Path | None) -> None`

功能说明：

- 设置公开 `dump_dir` 配置。
- 仅接受 `str`、`Path` 或 `None`。
- `None` 与空字符串都会关闭诊断落盘。
- 当你希望一次执行链路写出诊断产物时，应先调用这个接口。

使用示例：

```python
from pathlib import Path

from kernel_gen.core.config import get_dump_dir, set_dump_dir

set_dump_dir(Path("dump"))
assert get_dump_dir() == Path("dump")
```

### `get_dump_dir() -> Path | None`

功能说明：

- 读取公开 `dump_dir` 配置。
- 返回 `None` 表示当前未启用诊断产物落盘。

### `reset_config() -> None`

功能说明：

- 恢复公开配置默认值。
- `target` 与 `dump_dir` 恢复为 `None`。

### `snapshot_config() -> CoreConfigSnapshot`

功能说明：

- 返回当前公开 target 与 dump_dir 配置的不可变快照。
- 用于工具入口临时设置 target 后恢复调用前状态，避免 pytest 或嵌套调用串状态。

### `restore_config(snapshot: CoreConfigSnapshot) -> None`

功能说明：

- 恢复由 `snapshot_config()` 产生的公开配置快照。
- 只接受 `CoreConfigSnapshot`，不接受任意 dict。

## 限制与边界

- 本文件只定义公共行为配置底座，不承载单次生成状态。
- 未在本文件 `API 列表` 中显式列出的配置项，都不是公开配置。
- target 配置对外只能通过 `set_target/get_target` 接口读写，不提供 `dict` 式任意 key 入口。
- `EmitCContext` 的 SSA 名字表、缩进层级、runtime args、parse globals/builtins、callee registry/compiler 与 loop vars 都不是公共配置，不得迁入本文件。
- `hardware` 不属于公共 `config` 底座职责；这类硬件结构化信息应放在 `target` 侧收口。
- `dump_dir` 只承载诊断产物根目录；pass IR 与 `gen_kernel(...)` 最终源码可按该目录落盘，但源码文本本身和执行结果不属于 config 状态。
- 非公开 helper 仅允许存在于本文件内部，禁止跨文件调用。

## 测试

- 测试文件：[`test/core/test_config.py`](../../test/core/test_config.py)
- 执行命令：`pytest -q test/core/test_config.py`
- 测试目标：验证 `set_target/get_target/set_dump_dir/get_dump_dir/reset/snapshot/restore` 公开接口的稳定行为，并验证非法类型输入会稳定失败。
