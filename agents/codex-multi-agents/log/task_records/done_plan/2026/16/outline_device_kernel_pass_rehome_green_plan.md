# outline_device_kernel_pass_rehome_green_plan.md

## 文档信息

- 创建者：`守护最好的爱莉希雅`
- 最后一次更改：`咯咯咯`
- 目标 `spec`：
  - [`spec/pass/outline_device_kernel.md`](../../spec/pass/outline_device_kernel.md)
  - [`spec/pass/README.md`](../../spec/pass/README.md)
  - [`spec/pass/pipeline/default_lowering.md`](../../spec/pass/pipeline/default_lowering.md)
  - [`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)
- 目标 `API`：
  - [`kernel_gen/passes/outline_device_kernel.py`](../../kernel_gen/passes/outline_device_kernel.py)
  - [`kernel_gen/passes/__init__.py`](../../kernel_gen/passes/__init__.py)
  - [`kernel_gen/passes/lowering/__init__.py`](../../kernel_gen/passes/lowering/__init__.py)
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
- 目标 `test`：
  - [`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../test/pass/outline_device_kernel/test_outline_device_kernel.py)
  - [`test/pass/test_pass_registry.py`](../../test/pass/test_pass_registry.py)
  - [`test/pass/test_pipeline_default_lowering.py`](../../test/pass/test_pipeline_default_lowering.py)
- 目标 `验收资产`：
  - [`expectation/pass/outline_device_kernel/__main__.py`](../../expectation/pass/outline_device_kernel/__main__.py)
  - [`expectation/pass/outline_device_kernel/basic.py`](../../expectation/pass/outline_device_kernel/basic.py)
  - [`expectation/pass/outline_device_kernel/multi_function.py`](../../expectation/pass/outline_device_kernel/multi_function.py)
  - [`expectation/pass/outline_device_kernel/invalid_attr.py`](../../expectation/pass/outline_device_kernel/invalid_attr.py)
- 目标 `功能实现`：
  - [`kernel_gen/passes/lowering/outline_device_kernel.py`](../../kernel_gen/passes/lowering/outline_device_kernel.py)
  - [`kernel_gen/passes/lowering/__init__.py`](../../kernel_gen/passes/lowering/__init__.py)
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)

## 任务清单

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `S1` | `无` | `wt-20260419-outline-device-kernel-pass-s1` | `agents/codex-multi-agents/log/task_records/2026/16/20260419-outline-device-kernel-pass-s1.md` |

## 评审摘要

- 评审结论：`通过`
- 评审人：
  - `小李飞刀`
  - `金铲铲大作战`
  - `提莫炖蘑菇`
  - `大闸蟹`
- 结论摘要：
  - `同意本轮一次性收“迁移 + shared_memory_size 校验轻量重构 + expectation 全通过”，不单拆 spec-only 任务。`
  - `边界固定为 outline_device_kernel 最近合同面：expectation/spec/实现/专属 pytest；registry、kernel_gen.passes.__init__、lowering.__init__ 只同步引用，不扩无关 pass family。`
  - `shared_memory_size 校验应放在 pass 入口的候选收集/规整阶段，统一报 int-like / 非负约束错误；对应 expectation 应作为直接通过合同，不再写成当前缺口。`
  - `计划中必须单列旧路径/旧 import/旧测试入口的残留搜索验收，防止新旧双轨长期并存。`

## 最终验收结论（2026-04-20 00:46:58 +0800）

- 验收人：`守护最好的爱莉希雅`
- 验收结论：`不通过`
- 验证基线：
  - 当前主仓执行目录：`/home/lfr/kernelcode_generate`
  - 当前 `HEAD`：`c44ef67b55cd5675c595094a0ffa6dc4e03bafce`
- 实际复跑结果：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.outline_device_kernel` -> `exit 1`
- 最小阻断项：
  - [`expectation/pass/outline_device_kernel/invalid_attr.py`](../../expectation/pass/outline_device_kernel/invalid_attr.py) 的 `CASE-6` 与 `CASE-7` 仍失败；当前实现仍接受非法 `shared_memory_size`，未按合同对“非 int-like”与“负值”显式报错。
- 结论说明：
  - 当前 `TODO.md` 中该计划状态虽为 `完成待检查`，但主仓终验命令未全绿，因此不满足归档前置条件。
  - 本段为本轮按规则补回的正文终验结论与验证基线。

## 复核结论（2026-04-20 00:47:21 +0800）

- 复核人：`大闸蟹`
- 复核结论：`不通过`
- 复核基线：
  - 当前主仓执行目录：`/home/lfr/kernelcode_generate`
  - 当前 `HEAD`：`c44ef67b55cd5675c595094a0ffa6dc4e03bafce`
- 实际复跑结果：
  - `python3 -m pytest -q test/pass/outline_device_kernel/test_outline_device_kernel.py` -> `exit 4`（`file or directory not found`）
  - `python3 -m pytest -q test/pass/test_pass_registry.py -k outline_device_kernel` -> `1 passed, 17 deselected`
  - `python3 -m pytest -q test/pass/test_pipeline_default_lowering.py` -> `2 passed`
  - `rg -n "expectation/pass/lowing/outline_device_kernel|spec/pass/lowering/outline_device_kernel|kernel_gen/passes/lowering/outline_device_kernel|test/pass/test_outline_device_kernel|from kernel_gen\\.passes\\.lowering\\.outline_device_kernel import" spec test kernel_gen` -> `exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.outline_device_kernel` -> `exit 1`
- 最小阻断项：
  - 正式验收命令仍点名不存在的 [`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../test/pass/outline_device_kernel/test_outline_device_kernel.py)；当前专属 pytest 入口尚未迁移完成，或正文验收项未与仓库现场同步。
  - [`spec/pass/lowering/outline_device_kernel.md`](../../spec/pass/lowering/outline_device_kernel.md)、[`kernel_gen/passes/lowering/outline_device_kernel.py`](../../kernel_gen/passes/lowering/outline_device_kernel.py)、[`test/pass/test_outline_device_kernel.py`](../../test/pass/test_outline_device_kernel.py) 及其导入/文档引用仍残留，旧专题源头尚未清理完成。
  - [`expectation/pass/outline_device_kernel/invalid_attr.py`](../../expectation/pass/outline_device_kernel/invalid_attr.py) 的 `CASE-6/CASE-7` 仍失败；当前实现仍接受非法 `shared_memory_size`，未满足“int-like 且 >= 0”的公开失败合同。
- 结论说明：
  - 当前仍不满足归档前置条件。
  - 本段为本轮按规则补回的正文复核结论与验证基线。

## 当前唯一修复任务（2026-04-20 03:57:32 +0800）

- 任务号：`T-20260420-1d7d4842`
- `worktree`：`/home/lfr/kernelcode_generate/wt-20260420-outline-device-kernel-pass-s3`
- 记录文件：`/home/lfr/kernelcode_generate/agents/codex-multi-agents/log/task_records/2026/16/20260420-outline-device-kernel-pass-s3.md`
- 最小修复目标：
  - 在 [`kernel_gen/passes/outline_device_kernel.py`](../../kernel_gen/passes/outline_device_kernel.py) / 当前实现入口中补齐 `shared_memory_size` 的 `int-like` 与非负校验，使 [`expectation/pass/outline_device_kernel/invalid_attr.py`](../../expectation/pass/outline_device_kernel/invalid_attr.py) `CASE-6/CASE-7` 恢复通过。
  - 同步收口正式验收口径与旧路径残留，保证验收命令、专属 pytest 路径与当前仓库布局一致。
- 说明：
  - 该任务承接上一轮已完成的合并任务 [`T-20260420-fc52a758`](../../DONE.md)，作为当前唯一保留的修复入口。

## 复验结论（2026-04-20 04:06:48 +0800）

- 复验人：`守护最好的爱莉希雅`
- 复验结论：`通过`
- 验证基线：
  - 当前主仓执行目录：`/home/lfr/kernelcode_generate`
  - 当前 `HEAD`：`f6aa9316bf7b75420807ae139acbf15fdf163946`
- 正式验收结果：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/outline_device_kernel/test_outline_device_kernel.py` -> `12 passed`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_pass_registry.py -k outline_device_kernel` -> `1 passed`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_pipeline_default_lowering.py` -> `2 passed`
  - `rg -n "expectation/pass/lowing/outline_device_kernel|spec/pass/lowering/outline_device_kernel|kernel_gen/passes/lowering/outline_device_kernel|test/pass/test_outline_device_kernel|from kernel_gen\\.passes\\.lowering\\.outline_device_kernel import" spec test kernel_gen` -> `exit 1`（未命中旧路径残留）
- 补充核对结果：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.outline_device_kernel` -> `exit 0`
- 必要摘要：
  - `outline_device_kernel` 的专题 `spec / 实现 / 专属 pytest / registry` 已按计划收口，旧 `lowering` 路径残留已清空。
  - `shared_memory_size` 的 `int-like` 与非负校验已对齐 expectation，`CASE-6/CASE-7` 不再失败。
  - 当前已满足归档前置条件。

## 复验结论（2026-04-20 04:26:09 +0800）

- 复验人：`大闸蟹`
- 复验结论：`通过`
- 验证基线：
  - 当前主仓执行目录：`/home/lfr/kernelcode_generate`
  - 当前分支：`main`
  - 当前 `HEAD`：`f6aa9316bf7b75420807ae139acbf15fdf163946`
- 正式验收结果：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/outline_device_kernel/test_outline_device_kernel.py` -> `12 passed`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_pass_registry.py -k outline_device_kernel` -> `1 passed, 17 deselected`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_pipeline_default_lowering.py` -> `2 passed`
  - `rg -n "expectation/pass/lowing/outline_device_kernel|spec/pass/lowering/outline_device_kernel|kernel_gen/passes/lowering/outline_device_kernel|test/pass/test_outline_device_kernel|from kernel_gen\\.passes\\.lowering\\.outline_device_kernel import" spec test kernel_gen` -> `exit 1`（未命中旧路径残留）
- 补充核对结果：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.outline_device_kernel` -> `exit 0`
- 必要摘要：
  - 当前主线 `spec / 实现 / 专属 pytest / registry` 已与新专题目录对齐，旧 `lowering` 路径残留未再命中。
  - `shared_memory_size` 的非法类型与负值失败合同已稳定通过，目录级 expectation runner 全绿。
  - 当前已满足归档前置条件，可进入唯一归档任务链。

## 输入摘要

- 目标：`outline_device_kernel` 不再继续归属 `lowing/lowering` 旧路径；本轮要把专题目录迁出并顺手完成最小必要的公开合同重构。
- 当前已完成：
  - expectation 已迁到 [`expectation/pass/outline_device_kernel`](../../expectation/pass/outline_device_kernel)
  - expectation 已补齐：
    - 单函数成功路径
    - helper + kernel 多函数路径
    - 同一 kernel 多次调用
    - 同一 module 中两个 launch-marked kernel 同时存在
    - 非法 attrs / 非零返回值 / `_device` 命名冲突 / 非 `builtin.module`
    - `shared_memory_size` 的非法类型与负值失败合同
- 当前未完成：
  - `spec` 仍在 [`spec/pass/lowering/outline_device_kernel.md`](../../spec/pass/lowering/outline_device_kernel.md)
  - 实现仍在 [`kernel_gen/passes/lowering/outline_device_kernel.py`](../../kernel_gen/passes/lowering/outline_device_kernel.py)
  - 专属 pytest 仍在 [`test/pass/test_outline_device_kernel.py`](../../test/pass/test_outline_device_kernel.py)
  - 当前实现尚未校验 `shared_memory_size`，导致新加的失败 expectation 不能通过

## 计划目标

- 把 `outline_device_kernel` 的 expectation / spec / 实现 / 专属 pytest 统一收口到非 `lowing/lowering` 的同主题目录。
- 保持 `outline-device-kernel` 仍是 standalone pass，不自动进入 `default-lowering`。
- 让 [`expectation/pass/outline_device_kernel`](../../expectation/pass/outline_device_kernel) 成为唯一 expectation 入口，并作为只读合同真源。
- 让 [`spec/pass/outline_device_kernel.md`](../../spec/pass/outline_device_kernel.md) 成为唯一专题 spec。
- 让 [`kernel_gen/passes/outline_device_kernel.py`](../../kernel_gen/passes/outline_device_kernel.py) 成为唯一实现入口。
- 让 [`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../test/pass/outline_device_kernel/test_outline_device_kernel.py) 成为唯一专属 pytest 入口。
- 在迁移同一任务内完成最小必要重构：
  - `shared_memory_size` 在候选收集/规整阶段完成 `int-like` 与 `>= 0` 校验
  - 保持稳定错误前缀与 step-1 pass 失败口径

## 当前基线

- 当前 expectation 入口：
  - [`expectation/pass/outline_device_kernel/__main__.py`](../../expectation/pass/outline_device_kernel/__main__.py)
- 当前 expectation 结果：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 expectation/pass/outline_device_kernel/multi_function.py`：通过
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 expectation/pass/outline_device_kernel/invalid_attr.py`：失败
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.outline_device_kernel`：失败
- 当前目录级失败点：
  - [`expectation/pass/outline_device_kernel/invalid_attr.py`](../../expectation/pass/outline_device_kernel/invalid_attr.py)
    - `CASE-6`：`shared_memory_size` 不是 `int-like`
    - `CASE-7`：`shared_memory_size` 为负值
  - 失败原因：当前实现仍接受 `"bad"` 和 `-1 : i64`，未按公开合同显式报错
- 当前旧归属仍存在于：
  - [`spec/pass/lowering/outline_device_kernel.md`](../../spec/pass/lowering/outline_device_kernel.md)
  - [`kernel_gen/passes/lowering/outline_device_kernel.py`](../../kernel_gen/passes/lowering/outline_device_kernel.py)
  - [`test/pass/test_outline_device_kernel.py`](../../test/pass/test_outline_device_kernel.py)
- 当前引用残留：
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py) 仍从 `kernel_gen.passes.lowering.outline_device_kernel` 导入
  - [`kernel_gen/passes/lowering/__init__.py`](../../kernel_gen/passes/lowering/__init__.py) 仍把 `outline_device_kernel` 当作 lowering 家族的直接入口
  - [`spec/pass/README.md`](../../spec/pass/README.md) 与 [`spec/pass/lowering/outline_device_kernel.md`](../../spec/pass/lowering/outline_device_kernel.md) 仍把 expectation runner 写成 `expectation/pass/lowing/outline_device_kernel/`
  - [`test/pass/test_outline_device_kernel.py`](../../test/pass/test_outline_device_kernel.py) 仍直接引用旧实现路径

## 合同真源顺序

- `expectation/pass/outline_device_kernel > spec/pass/outline_device_kernel.md > test/pass/outline_device_kernel/test_outline_device_kernel.py > 当前实现`

## 方案比较与选型

- 不采用方案：只迁目录，不补 `shared_memory_size` 校验。
  - 原因：这样目录会迁对，但新增的失败合同继续保持红灯，计划完成态不成立。
- 不采用方案：把 `shared_memory_size` 继续写成“当前缺口暴露资产”。
  - 原因：`shared_memory_size` 非法值属于公开失败语义，已被 expectation 明确锁定，应直接作为必过合同。
- 不采用方案：拆成“先迁移、后重构”两阶段。
  - 原因：迁移、`shared_memory_size` 校验、专属 pytest/registry 同步共享同一批验收资产，强拆会增加往返成本。
- 不采用方案：扩大范围，顺手迁移 `default_lowering` 或其他 pass family。
  - 原因：本轮只收 `outline_device_kernel`，无关 pass family 不应混入。
- 采用方案：
  - expectation 保持在 [`expectation/pass/outline_device_kernel`](../../expectation/pass/outline_device_kernel)，不再修改
  - spec 迁到 [`spec/pass/outline_device_kernel.md`](../../spec/pass/outline_device_kernel.md)
  - 实现迁到 [`kernel_gen/passes/outline_device_kernel.py`](../../kernel_gen/passes/outline_device_kernel.py)
  - 专属 pytest 迁到 [`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../test/pass/outline_device_kernel/test_outline_device_kernel.py)
  - `shared_memory_size` 校验放在 pass 入口的候选收集/规整阶段
  - [`kernel_gen/passes/lowering/__init__.py`](../../kernel_gen/passes/lowering/__init__.py) 只保留兼容转发
  - `registry / kernel_gen.passes.__init__ / spec README / default-lowering spec/test` 只同步引用与说明

## 公开 API 设计

- 主公开入口：
  - `kernel_gen.passes.outline_device_kernel.OutlineDeviceKernelPass`
  - `kernel_gen.passes.outline_device_kernel.OutlineDeviceKernelError`
- 兼容入口：
  - `from kernel_gen.passes.lowering import OutlineDeviceKernelPass`
  - 仅通过 [`kernel_gen/passes/lowering/__init__.py`](../../kernel_gen/passes/lowering/__init__.py) 转发，不再保留 `kernel_gen.passes.lowering.outline_device_kernel` 作为主实现模块
- 参数顺序：
  - `OutlineDeviceKernelPass.run(module)`
- 参数类型：
  - `module: ModuleOp`
- 返回值：
  - `run(module) -> module`

```python
from kernel_gen.passes.outline_device_kernel import OutlineDeviceKernelPass

module = OutlineDeviceKernelPass().run(module)
```

## 完成态定义

- [`expectation/pass/outline_device_kernel`](../../expectation/pass/outline_device_kernel) 是唯一架构侧 expectation 入口，且执行任务不再修改其中任何文件；当前任务的正式交付不包含该目录本体。
- [`spec/pass/outline_device_kernel.md`](../../spec/pass/outline_device_kernel.md) 成为唯一专题 spec，不再保留 `spec/pass/lowering/outline_device_kernel.md`。
- [`kernel_gen/passes/outline_device_kernel.py`](../../kernel_gen/passes/outline_device_kernel.py) 成为唯一实现入口，不再保留 `kernel_gen/passes/lowering/outline_device_kernel.py`。
- [`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../test/pass/outline_device_kernel/test_outline_device_kernel.py) 成为唯一专属 pytest，不再保留 `test/pass/test_outline_device_kernel.py`。
- [`kernel_gen/passes/lowering/__init__.py`](../../kernel_gen/passes/lowering/__init__.py) 只保留兼容转发，不再继续把 `outline_device_kernel` 作为 lowering 专题文档/实现源头。
- `default-lowering remains unchanged`：
  - builder 顺序不变
  - 不自动插入 `outline-device-kernel`
- pass 行为合同固定为：
  - 三项 launch attrs 同时存在才触发
  - 输出 `wrapper + device` 双函数
  - 同一 `module` 中多个被标记 kernel 可同时 outline，各自产生一份 `wrapper + device`
  - `shared_memory_size` 为 metadata-only，但仍需显式校验 `int-like` 与 `>= 0`
  - 非法 attrs / 非正 extent / 非零返回值 / 命名冲突 / 非法 `shared_memory_size` 稳定报错

## 验收设计

- 验收资产：
  - 正式合入资产：
    - [`spec/pass/outline_device_kernel.md`](../../spec/pass/outline_device_kernel.md)
    - [`spec/pass/README.md`](../../spec/pass/README.md)
    - [`spec/pass/pipeline/default_lowering.md`](../../spec/pass/pipeline/default_lowering.md)
    - [`kernel_gen/passes/outline_device_kernel.py`](../../kernel_gen/passes/outline_device_kernel.py)
    - [`kernel_gen/passes/__init__.py`](../../kernel_gen/passes/__init__.py)
    - [`kernel_gen/passes/lowering/__init__.py`](../../kernel_gen/passes/lowering/__init__.py)
    - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
    - [`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../test/pass/outline_device_kernel/test_outline_device_kernel.py)
    - [`test/pass/test_pass_registry.py`](../../test/pass/test_pass_registry.py)
    - [`test/pass/test_pipeline_default_lowering.py`](../../test/pass/test_pipeline_default_lowering.py)
  - 架构侧合同参考：
    - [`expectation/pass/outline_device_kernel/__main__.py`](../../expectation/pass/outline_device_kernel/__main__.py)
    - [`expectation/pass/outline_device_kernel/multi_function.py`](../../expectation/pass/outline_device_kernel/multi_function.py)
    - [`expectation/pass/outline_device_kernel/invalid_attr.py`](../../expectation/pass/outline_device_kernel/invalid_attr.py)
- 锁定输出：
  - 架构侧 expectation 路径稳定为 `expectation/pass/outline_device_kernel`
  - `shared_memory_size` 非法值必须在 step-1 pass 阶段稳定失败
  - `default-lowering` 不自动插入 `outline-device-kernel`
  - 正式合入资产中的 spec / 实现 / test / registry / 导出路径不再保留旧专题源头
- 必过命令：
  - `pytest -q test/pass/outline_device_kernel/test_outline_device_kernel.py`
  - `pytest -q test/pass/test_pass_registry.py -k outline_device_kernel`
  - `pytest -q test/pass/test_pipeline_default_lowering.py`
  - `rg -n "expectation/pass/lowing/outline_device_kernel|spec/pass/lowering/outline_device_kernel|kernel_gen/passes/lowering/outline_device_kernel|test/pass/test_outline_device_kernel|from kernel_gen\\.passes\\.lowering\\.outline_device_kernel import" spec test kernel_gen`
- 架构侧补充核对命令：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<task_worktree>:<repo_root> python3 -m expectation.pass.outline_device_kernel`
- 验证基线：
  - 正式验收只依赖当前任务 `worktree` 内的正式合入资产，不要求 `worktree` 自带 `expectation/` 目录。
  - `expectation/pass/outline_device_kernel/**` 由架构侧保管；如需补充核对目录级 runner，应在当前任务 `worktree` 下执行，并把仓库根目录追加到 `PYTHONPATH`，以便同时加载当前现场实现与架构侧 expectation 资产。

## 阶段拆分

### S1：outline_device_kernel 迁移与轻量重构收口

#### 阶段目标

- 一次性收口 `outline_device_kernel` 的专题迁移、`shared_memory_size` 校验重构与专属 pytest/registry 同步，不再拆第二阶段。

#### 目标 spec / API

- [`spec/pass/outline_device_kernel.md`](../../spec/pass/outline_device_kernel.md)
- [`spec/pass/README.md`](../../spec/pass/README.md)
- [`spec/pass/pipeline/default_lowering.md`](../../spec/pass/pipeline/default_lowering.md)
- [`kernel_gen/passes/outline_device_kernel.py`](../../kernel_gen/passes/outline_device_kernel.py)
- [`kernel_gen/passes/__init__.py`](../../kernel_gen/passes/__init__.py)
- [`kernel_gen/passes/lowering/__init__.py`](../../kernel_gen/passes/lowering/__init__.py)
- [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
- [`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../test/pass/outline_device_kernel/test_outline_device_kernel.py)
- `公开 API：kernel_gen.passes.outline_device_kernel.OutlineDeviceKernelPass`

#### 禁止修改面 / 合同真源

- `禁止修改面：expectation/pass/outline_device_kernel/** 由架构侧保管且只读；不改 .gitignore；不把无关 pass family 一起扩进来。`
- `合同真源：架构侧 expectation/pass/outline_device_kernel > spec/pass/outline_device_kernel.md > test/pass/outline_device_kernel/test_outline_device_kernel.py > 当前实现`

#### 预期示例代码

```python
from kernel_gen.passes.outline_device_kernel import OutlineDeviceKernelPass

module = OutlineDeviceKernelPass().run(module)
```

#### 预期输出

```text
- expectation/pass/outline_device_kernel 成为唯一 expectation 入口，目录级入口全部通过
- spec/pass/outline_device_kernel.md 成为唯一专题 spec
- kernel_gen/passes/outline_device_kernel.py 成为唯一实现入口
- test/pass/outline_device_kernel/test_outline_device_kernel.py 成为唯一专属 pytest
- shared_memory_size 非法值在 step-1 pass 阶段稳定失败
- default-lowering remains unchanged
```

#### 目标验收资产

- 正式合入资产：
  - [`spec/pass/outline_device_kernel.md`](../../spec/pass/outline_device_kernel.md)
  - [`spec/pass/README.md`](../../spec/pass/README.md)
  - [`spec/pass/pipeline/default_lowering.md`](../../spec/pass/pipeline/default_lowering.md)
  - [`kernel_gen/passes/outline_device_kernel.py`](../../kernel_gen/passes/outline_device_kernel.py)
  - [`kernel_gen/passes/__init__.py`](../../kernel_gen/passes/__init__.py)
  - [`kernel_gen/passes/lowering/__init__.py`](../../kernel_gen/passes/lowering/__init__.py)
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
  - [`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../test/pass/outline_device_kernel/test_outline_device_kernel.py)
  - [`test/pass/test_pass_registry.py`](../../test/pass/test_pass_registry.py)
  - [`test/pass/test_pipeline_default_lowering.py`](../../test/pass/test_pipeline_default_lowering.py)
- 架构侧合同参考：
  - [`expectation/pass/outline_device_kernel/__main__.py`](../../expectation/pass/outline_device_kernel/__main__.py)
  - [`expectation/pass/outline_device_kernel/multi_function.py`](../../expectation/pass/outline_device_kernel/multi_function.py)
  - [`expectation/pass/outline_device_kernel/invalid_attr.py`](../../expectation/pass/outline_device_kernel/invalid_attr.py)

#### 验收必过项目

- `pytest -q test/pass/outline_device_kernel/test_outline_device_kernel.py`
- `pytest -q test/pass/test_pass_registry.py -k outline_device_kernel`
- `pytest -q test/pass/test_pipeline_default_lowering.py`
- `rg -n "expectation/pass/lowing/outline_device_kernel|spec/pass/lowering/outline_device_kernel|kernel_gen/passes/lowering/outline_device_kernel|test/pass/test_outline_device_kernel|from kernel_gen\\.passes\\.lowering\\.outline_device_kernel import" spec test kernel_gen`
- `若需补充核对架构侧 expectation runner，应在当前任务 worktree 下执行：PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<task_worktree>:<repo_root> python3 -m expectation.pass.outline_device_kernel；该项不作为当前任务正式合入前置。`

#### 任务新建建议

- `任务类型：refactor`
- `任务目标：迁移 outline_device_kernel 的 spec / 实现 / 专属 pytest 到非 lowering 目录，并在同任务内补齐 shared_memory_size 校验与旧路径清理，保持 expectation 合同全部通过`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260419-outline-device-kernel-pass-s1.md`

## 待确认项

- `无阻塞性待确认项。`

## 用户确认与协同约束

- `用户确认状态：已确认`
- `未确认事项：无`
- `用户确认结论：本轮先只修改 expectation；在 expectation 已补齐后，再单独起“迁移并重构”的计划书。`
- `协同约束：本轮计划书已通过 -talk 直接询问 小李飞刀、金铲铲大作战、提莫炖蘑菇、大闸蟹；执行阶段不得修改 expectation 文件。`

## 参考资料

- [`expectation/pass/outline_device_kernel/__main__.py`](../../expectation/pass/outline_device_kernel/__main__.py)
- [`expectation/pass/outline_device_kernel/multi_function.py`](../../expectation/pass/outline_device_kernel/multi_function.py)
- [`expectation/pass/outline_device_kernel/invalid_attr.py`](../../expectation/pass/outline_device_kernel/invalid_attr.py)
- [`kernel_gen/passes/lowering/outline_device_kernel.py`](../../kernel_gen/passes/lowering/outline_device_kernel.py)
- [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
- [`test/pass/test_outline_device_kernel.py`](../../test/pass/test_outline_device_kernel.py)
- [`spec/pass/lowering/outline_device_kernel.md`](../../spec/pass/lowering/outline_device_kernel.md)

## 归档任务记录

时间：2026-04-20 04:17 +0800
经办人：李白
任务：T-20260420-7de140f8
任务目标：将 `ARCHITECTURE/plan/outline_device_kernel_pass_rehome_green_plan.md` 归档到 `agents/codex-multi-agents/log/task_records/done_plan/2026/16/outline_device_kernel_pass_rehome_green_plan.md`，并在归档合并完成后通知管理员执行 `-done-plan`；同步清理 `ARCHITECTURE/plan/outline_device_kernel_pass_rehome_green_plan.md`。
改动：在指定 `worktree` 中新增归档文件 `agents/codex-multi-agents/log/task_records/done_plan/2026/16/outline_device_kernel_pass_rehome_green_plan.md`（内容同步自主仓本地计划书）；同步清理动作按任务口径执行，确保 `ARCHITECTURE/plan/outline_device_kernel_pass_rehome_green_plan.md` 在当前 `worktree` 与主仓本地现场均已清理。
验证：`git -C /home/lfr/kernelcode_generate/wt-20260420-archive-outline-device-kernel-plan status --short --branch` -> 仅命中当前归档文件；`cmp -s /home/lfr/kernelcode_generate/wt-20260420-archive-outline-device-kernel-plan/ARCHITECTURE/plan/outline_device_kernel_pass_rehome_green_plan.md /home/lfr/kernelcode_generate/wt-20260420-archive-outline-device-kernel-plan/agents/codex-multi-agents/log/task_records/done_plan/2026/16/outline_device_kernel_pass_rehome_green_plan.md` -> `0`（归档正文与源计划一致）；`test -f /home/lfr/kernelcode_generate/wt-20260420-archive-outline-device-kernel-plan/ARCHITECTURE/plan/outline_device_kernel_pass_rehome_green_plan.md` 与 `test -f /home/lfr/kernelcode_generate/ARCHITECTURE/plan/outline_device_kernel_pass_rehome_green_plan.md` -> 均失败（已清理）。
结论：当前归档 merge 收口完成，提交后继续执行 `git push`、合并后 `git fetch`、`-done`，并回报管理员继续执行 `-done-plan`。
