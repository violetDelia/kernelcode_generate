# decompass_pass_rehome_green_plan.md

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`咯咯咯`
- 目标 `spec`：
  - [`spec/pass/decompass.md`](../../spec/pass/decompass.md)
  - [`spec/pass/pipeline/default_lowering.md`](../../spec/pass/pipeline/default_lowering.md)
  - [`spec/dialect/nn.md`](../../spec/dialect/nn.md)
- 目标 `API`：
  - [`kernel_gen/passes/decompass.py`](../../kernel_gen/passes/decompass.py)
  - [`kernel_gen/passes/__init__.py`](../../kernel_gen/passes/__init__.py)
  - [`kernel_gen/passes/lowering/__init__.py`](../../kernel_gen/passes/lowering/__init__.py)
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
  - [`kernel_gen/passes/pipeline/default_lowering.py`](../../kernel_gen/passes/pipeline/default_lowering.py)
- 目标 `test`：
  - [`test/pass/decompass/test_softmax.py`](../../test/pass/decompass/test_softmax.py)
  - [`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)
  - [`test/pass/test_pipeline_default_lowering.py`](../../test/pass/test_pipeline_default_lowering.py)
- 目标 `验收资产`：
  - 正式合入资产：
    - [`spec/pass/decompass.md`](../../spec/pass/decompass.md)
    - [`spec/pass/pipeline/default_lowering.md`](../../spec/pass/pipeline/default_lowering.md)
    - [`kernel_gen/passes/decompass.py`](../../kernel_gen/passes/decompass.py)
    - [`test/pass/decompass/test_softmax.py`](../../test/pass/decompass/test_softmax.py)
    - [`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)
    - [`test/pass/test_pipeline_default_lowering.py`](../../test/pass/test_pipeline_default_lowering.py)
  - 架构侧合同参考：
    - [`expectation/pass/decompass/__main__.py`](../../expectation/pass/decompass/__main__.py)
    - [`expectation/pass/decompass/softmax.py`](../../expectation/pass/decompass/softmax.py)
    - [`expectation/pass/pipeline/default_lowering.py`](../../expectation/pass/pipeline/default_lowering.py)
    - `python3 -m expectation.pass.decompass`
- 目标 `功能实现`：
  - [`kernel_gen/passes/decompass.py`](../../kernel_gen/passes/decompass.py)
  - [`kernel_gen/passes/__init__.py`](../../kernel_gen/passes/__init__.py)
  - [`kernel_gen/passes/lowering/__init__.py`](../../kernel_gen/passes/lowering/__init__.py)
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
  - [`kernel_gen/passes/pipeline/default_lowering.py`](../../kernel_gen/passes/pipeline/default_lowering.py)

## 任务清单

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `S1` | `无` | `wt-20260419-decompass-pass-s1` | `agents/codex-multi-agents/log/task_records/2026/16/20260419-decompass-pass-s1.md` |

## 评审摘要

- 评审结论：`通过`
- 评审人：`大闸蟹`、`守护最好的爱莉希雅`
- 结论摘要：`同意 decompass 不再归属 lowing/lowering，expectation / spec / 实现 / 专属 pytest 统一收口到同主题目录；实现主文件、专题 spec、专属 test 迁移，default_lowering / registry / pass_manager 与 spec/dialect/nn 只同步引用；S1 单任务足够，但正文需显式纳入 kernel_gen/passes/lowering/__init__.py、expectation/pass/pipeline/default_lowering.py 与 expectation/pass/decompass 旧 helper 依赖清理。`

## 最终验收结论（2026-04-20 03:49:36 +0800）

- 验收人：`守护最好的爱莉希雅`
- 验收结论：`通过`
- 验证基线：
  - 当前主仓执行目录：`/home/lfr/kernelcode_generate`
  - 当前 `HEAD`：`d39014d2f34caf608534776104bb09c3c64e0885`
- 正式验收结果：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/decompass/test_softmax.py` -> `6 passed`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_pass_manager.py -k decompass` -> `1 passed`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_pipeline_default_lowering.py` -> `2 passed`
  - `rg -n --glob '!spec/pass/decompass.md' "kernel_gen\\.passes\\.lowering\\.decompass|spec/pass/lowering/decompass|test/pass/test_decompose_nn_softmax" kernel_gen spec test` -> `exit 1`（未命中旧路径残留）
- 架构侧补充核对：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.decompass` -> `exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.pipeline.default_lowering` -> `exit 0`
- 必要摘要：
  - `decompass` 专题 `spec / 实现 / 专属 pytest` 已从旧 `lowering` 归属收口到独立主题目录，默认 pipeline 顺序保持不变。
  - `axis=-1` 继续按当前 expectation / spec / pytest / 实现一致口径处理，不再由旧目录兼容逻辑兜底。
  - 当前已满足归档前置条件。

## 输入摘要

- 目标：新建一个任务，修复 `decompass` expectation，并把该 pass 的实现与专属 test 从 `lowing/lowering` 归属中迁出。
- 目标：新建一个任务，修复 `decompass` expectation，并把该 pass 的实现与专属 test 从 `lowing/lowering` 归属中迁出；在不扩专题范围的前提下允许做轻量重构，提高实现与测试可读性、导入边界清晰度与目录一致性。
- 不做什么：不把整个默认 pipeline 重新分类，不顺手改其它 pass 目录，不把与 `decompass` 无关的 `nn_lowering` 家族一起迁移。
- 当前痛点：`expectation/pass/decompass` 已经上移，但实现仍在 [`kernel_gen/passes/lowering/decompass.py`](../../kernel_gen/passes/lowering/decompass.py)，专属 pytest 仍在 [`test/pass/test_decompose_nn_softmax.py`](../../test/pass/test_decompose_nn_softmax.py)，目录口径已经分叉。
- 完成后最想看到的例子：`DecompassPass` 统一从 `kernel_gen.passes.decompass` 导入，专属 expectation 在 `expectation/pass/decompass`，专属 pytest 在 `test/pass/decompass`，`python3 -m expectation.pass.decompass` 的失败只代表合同未满足，不再混入旧目录残留。

## 计划目标

- 把 `decompass` 的公开归属从 `lowing/lowering` 调整为独立的 `pass/decompass` 主题目录。
- 修复当前架构侧 `expectation/pass/decompass` 基线与实现 / test 目录不一致的问题，并明确其保管范围与正常合入边界。
- 固定 `DecompassPass`、`DecompassError`、`register_decompass_rewrite(...)` 的新导入路径。
- 保持默认 pipeline 中 `decompass -> lower-nn -> buffer-results-to-out-params -> lower-dma-memory-hierarchy` 的执行顺序不变，只调整引用路径与目录归属。
- 允许在迁移过程中做轻量重构，提升 `decompass` 实现与专属 pytest 的结构清晰度、重复逻辑收口程度与导入边界可读性，但不扩大到无关 pass 家族。
- 让执行人只围绕 `decompass` 专题收口实现、测试与公开引用，不再猜哪些文件应迁、哪些 expectation 仅作架构侧合同参考。

## 当前基线

- 当前公开合同：
  - [`spec/pass/lowering/decompass.md`](../../spec/pass/lowering/decompass.md) 仍把 `decompass` 定义为 `lowering` 目录下的 pass，并写死旧导入路径。
  - [`spec/pass/pipeline/default_lowering.md`](../../spec/pass/pipeline/default_lowering.md) 把 `decompass` 当作默认 pipeline 的第一步预处理 pass。
  - [`spec/dialect/nn.md`](../../spec/dialect/nn.md) 仍把 `nn.softmax` 的分解前置说明链接到 `spec/pass/lowering/decompass.md`。
- 当前公开 API：
  - [`kernel_gen/passes/lowering/decompass.py`](../../kernel_gen/passes/lowering/decompass.py) 当前公开 `DecompassPass`、`DecompassError` 与 `register_decompass_rewrite(...)`。
  - [`kernel_gen/passes/pipeline/default_lowering.py`](../../kernel_gen/passes/pipeline/default_lowering.py) 与 [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py) 仍从 `kernel_gen.passes.lowering.decompass` 导入实现。
- 当前实现入口：
  - 唯一实现文件仍是 [`kernel_gen/passes/lowering/decompass.py`](../../kernel_gen/passes/lowering/decompass.py)。
  - [`kernel_gen/passes/__init__.py`](../../kernel_gen/passes/__init__.py) 目前没有独立暴露 `decompass` 根路径入口。
- 当前测试与验收资产：
  - expectation 已迁到 [`expectation/pass/decompass`](../../expectation/pass/decompass)。
  - 专属 pytest 仍是 [`test/pass/test_decompose_nn_softmax.py`](../../test/pass/test_decompose_nn_softmax.py)。
  - [`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py) 与 [`test/pass/test_pipeline_default_lowering.py`](../../test/pass/test_pipeline_default_lowering.py) 仍使用旧 import 路径。
- 当前缺口或失败点：
  - `python3 -m expectation.pass.decompass` 当前可运行，但 [`expectation/pass/decompass/softmax.py`](../../expectation/pass/decompass/softmax.py) 的 `CASE-3` 仍失败，因为实现还把 `axis=-1` 规整后继续分解。
  - expectation 已不在 `lowing`，但实现 / spec / 专属 test 仍留在 `lowering` 归属，目录语义前后不一致。
  - 当前 expectation 文件仍引用 `expectation.pass.lowing._shared` 与 `expectation.pass.lowing.nn_lowering._random_utils`，目录上移后仍残留旧家族依赖，需要一并收口。
  - [`test/pass/test_decompose_nn_softmax.py`](../../test/pass/test_decompose_nn_softmax.py) 还把“负轴规整”为正例合同，这与当前 expectation 已经冲突。

## 合同真源顺序

- `架构侧 expectation 基线 > spec/pass/decompass.md > test/pass/decompass/test_softmax.py > 当前实现`

## 方案比较与选型

- 不采用方案：只修 `expectation/pass/decompass/softmax.py`，保留 `kernel_gen/passes/lowering/decompass.py` 与 `test/pass/test_decompose_nn_softmax.py` 不动。
  - 原因：这会继续保留“合同已迁、实现和专属 test 还在旧目录”的双口径状态，后续维护者仍需要猜目录归属。
- 不采用方案：把 `decompass` 继续视为 `lowering` 子项，只在 `expectation/pass/decompass` 旁边加兼容入口。
  - 原因：用户已经明确该 pass 不应再在 `lowing/lowering` 里面；继续保留旧归属只会延长清理周期。
- 采用方案：
  - `spec` 改到 [`spec/pass/decompass.md`](../../spec/pass/decompass.md)；
  - 实现改到 [`kernel_gen/passes/decompass.py`](../../kernel_gen/passes/decompass.py)；
  - 专属 pytest 改到 [`test/pass/decompass/test_softmax.py`](../../test/pass/decompass/test_softmax.py)；
  - expectation 保持在 [`expectation/pass/decompass`](../../expectation/pass/decompass)；
  - `pipeline / registry / pass_manager` 相关文件只同步引用，不跟着迁目录。
- 最小公开接口：
  - `from kernel_gen.passes.decompass import DecompassPass`
  - `from kernel_gen.passes.decompass import DecompassError`
  - `from kernel_gen.passes.decompass import register_decompass_rewrite`

## 公开 API 设计

- 公开入口：
  - `kernel_gen.passes.decompass.DecompassPass`
  - `kernel_gen.passes.decompass.DecompassError`
  - `kernel_gen.passes.decompass.register_decompass_rewrite`
- 参数顺序：
  - `register_decompass_rewrite(op_name, rewrite)`
- 参数类型：
  - `op_name: str`
  - `rewrite: Callable[[Operation, Block], None]`
- 返回值：
  - `DecompassPass.run(module) -> module`
  - `register_decompass_rewrite(...) -> None`

```python
from kernel_gen.passes.decompass import DecompassPass
from kernel_gen.passes.pass_manager import PassManager

pm = PassManager(name="default-lowering")
pm.add_pass(DecompassPass())
module = pm.run(module)
```

```python
from kernel_gen.passes.decompass import register_decompass_rewrite

register_decompass_rewrite("nn.exp", rewrite_exp)
```

## 完成态定义

- [`spec/pass/decompass.md`](../../spec/pass/decompass.md) 成为 `decompass` 的唯一专题 `spec`，不再保留 `spec/pass/lowering/decompass.md`。
- [`kernel_gen/passes/decompass.py`](../../kernel_gen/passes/decompass.py) 成为唯一实现入口，不再保留 `kernel_gen/passes/lowering/decompass.py`。
- [`test/pass/decompass/test_softmax.py`](../../test/pass/decompass/test_softmax.py) 成为唯一专属 pytest 入口，不再保留 `test/pass/test_decompose_nn_softmax.py`。
- 架构侧保管的 [`expectation/pass/decompass`](../../expectation/pass/decompass) 继续作为目录级合同入口；当前任务若在 `worktree` 内临时放置同名副本，只用于现场复现，不属于正常合入内容。
- `default_lowering` pipeline 的行为顺序与 pass 名保持不变，但所有导入与文档引用统一指向新目录。
- `axis=-1` 非法这一条在 expectation、spec、专属 pytest 与实现上收口一致。

## 验收设计

- 验收资产：
  - 正式合入资产：
    - [`spec/pass/decompass.md`](../../spec/pass/decompass.md)
    - [`spec/pass/pipeline/default_lowering.md`](../../spec/pass/pipeline/default_lowering.md)
    - [`kernel_gen/passes/decompass.py`](../../kernel_gen/passes/decompass.py)
    - [`test/pass/decompass/test_softmax.py`](../../test/pass/decompass/test_softmax.py)
    - [`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)
    - [`test/pass/test_pipeline_default_lowering.py`](../../test/pass/test_pipeline_default_lowering.py)
  - 架构侧合同参考：
    - [`expectation/pass/decompass/__main__.py`](../../expectation/pass/decompass/__main__.py)
    - [`expectation/pass/decompass/softmax.py`](../../expectation/pass/decompass/softmax.py)
    - [`expectation/pass/pipeline/default_lowering.py`](../../expectation/pass/pipeline/default_lowering.py)
- 输入样例：
  - `nn.softmax(..., axis=1)` 正例
  - `nn.softmax(..., axis=-1)` 非法输入
  - `PassManager(name="default-lowering").add_pass(DecompassPass())`
- 锁定输出：
  - `DecompassPass` 只从 `kernel_gen.passes.decompass` 导入
  - `axis=-1` 明确报错，不再被规整
  - 默认 pipeline 顺序仍为 `decompass -> lower-nn -> buffer-results-to-out-params -> lower-dma-memory-hierarchy`
- 正式验收命令：
  - `pytest -q test/pass/decompass/test_softmax.py`
  - `pytest -q test/pass/test_pass_manager.py -k decompass`
  - `pytest -q test/pass/test_pipeline_default_lowering.py`
  - `rg -n --glob '!spec/pass/decompass.md' "kernel_gen\\.passes\\.lowering\\.decompass|spec/pass/lowering/decompass|test/pass/test_decompose_nn_softmax" kernel_gen spec test`
- 架构侧补充核对命令：
  - `PYTHONPATH=<task_worktree>:<repo_root> python3 -m expectation.pass.decompass`
  - `PYTHONPATH=<task_worktree>:<repo_root> python3 -m expectation.pass.pipeline.default_lowering`
- 验证基线：
  - 正式验收在最新同步任务现场的 `worktree` 中执行；若根目录旧现场与任务 `worktree` 不一致，只记为现场差异，不单独作为阻断依据。
  - `expectation` 目录按 [`agents/standard/expectation任务规则.md`](../../agents/standard/expectation任务规则.md) 由架构侧保管；当前任务若需本地 runner，只可作为临时复现材料，不得当作正常合入内容。

## 阶段拆分

### S1：decompass 目录迁移与合同收口

#### 阶段目标

- 收口 `decompass` 的 spec、实现与专属 test 目录归属，并明确架构侧 expectation 资产的保管范围、复现方式与正常合入边界。
- 在不改变公开 pass 行为与默认 pipeline 顺序的前提下，对 `decompass` 实现与专属测试做小范围重构，减少旧目录残留与重复导入。

#### 目标 spec / API

- [`spec/pass/decompass.md`](../../spec/pass/decompass.md)
- `公开 API：kernel_gen.passes.decompass.DecompassPass`
- `公开 API：kernel_gen.passes.decompass.DecompassError`
- `公开 API：kernel_gen.passes.decompass.register_decompass_rewrite`
- `同步引用：kernel_gen/passes/lowering/__init__.py、kernel_gen/passes/registry.py、kernel_gen/passes/pipeline/default_lowering.py`

#### 禁止修改面 / 合同真源

- `禁止修改面：非架构师不得把 expectation 文件纳入正常合并内容；执行人只可修改与 decompass 目录迁移直接相关的实现、测试、spec 与公开引用，不应把无关 pass 家族一起迁移。若确需调整 expectation 本体或 helper 归属，必须转交架构侧单独处理。`
- `合同真源：架构侧 expectation 基线 > spec/pass/decompass.md > test/pass/decompass/test_softmax.py > 当前实现；当前任务 worktree 内若存在 expectation 副本，只作为现场复现材料，不改变正常合入边界。`

#### 预期示例代码

```python
from kernel_gen.passes.decompass import DecompassPass

module = DecompassPass().run(module)
```

```python
from kernel_gen.passes.decompass import register_decompass_rewrite

register_decompass_rewrite("nn.exp", rewrite_exp)
```

#### 预期输出

```text
- 旧路径 kernel_gen/passes/lowering/decompass.py 已删除
- 旧路径 test/pass/test_decompose_nn_softmax.py 已删除
- spec/pass/lowering/decompass.md 已迁为 spec/pass/decompass.md
- 架构侧 expectation runner 如存在，保持不依赖 expectation.pass.lowing 共享 helper 名
- decompass 实现与专属测试中的旧路径导入、重复辅助逻辑与残留兼容别名已做最小重构收口
- 正式验收不依赖当前 task worktree 内被忽略的 expectation 副本
- axis=-1 在 expectation / spec / pytest / 实现中统一为非法输入
```

#### 目标验收资产

- 正式合入资产：
  - [`spec/pass/decompass.md`](../../spec/pass/decompass.md)
  - [`spec/pass/pipeline/default_lowering.md`](../../spec/pass/pipeline/default_lowering.md)
  - [`kernel_gen/passes/decompass.py`](../../kernel_gen/passes/decompass.py)
  - [`kernel_gen/passes/lowering/__init__.py`](../../kernel_gen/passes/lowering/__init__.py)
  - [`test/pass/decompass/test_softmax.py`](../../test/pass/decompass/test_softmax.py)
  - [`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)
  - [`test/pass/test_pipeline_default_lowering.py`](../../test/pass/test_pipeline_default_lowering.py)
- 架构侧合同参考：
  - [`expectation/pass/decompass/__main__.py`](../../expectation/pass/decompass/__main__.py)
  - [`expectation/pass/decompass/softmax.py`](../../expectation/pass/decompass/softmax.py)
  - [`expectation/pass/pipeline/default_lowering.py`](../../expectation/pass/pipeline/default_lowering.py)
- `expectation 文件中的共享辅助导入若仍带有 lowing 家族名，应由架构侧 runner 基线统一收口；普通 build/review/merge 不把本地 expectation 副本作为交付物。`

#### 验收必过项目

- `pytest -q test/pass/decompass/test_softmax.py`
- `pytest -q test/pass/test_pass_manager.py -k decompass`
- `pytest -q test/pass/test_pipeline_default_lowering.py`
- `rg -n --glob '!spec/pass/decompass.md' "kernel_gen\\.passes\\.lowering\\.decompass|spec/pass/lowering/decompass|test/pass/test_decompose_nn_softmax" kernel_gen spec test`
- `若当前同步现场具备架构侧 expectation runner，可额外执行 PYTHONPATH=<task_worktree>:<repo_root> python3 -m expectation.pass.decompass 与 PYTHONPATH=<task_worktree>:<repo_root> python3 -m expectation.pass.pipeline.default_lowering；该项仅作补充核对，不作为正常合入前置。`

#### 任务新建建议

- `任务类型：build`
- `任务目标：修复 decompass expectation，并将 decompass 的 spec / 实现 / 专属 test 迁移到非 lowing 的 decompass 目录；同步更新 pipeline、registry 与 pass_manager 引用；在同专题边界内做轻量重构，提升实现与测试质量`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260419-decompass-pass-s1.md`

## 待确认项

- 问题：`无`
- 可选项：`无`
- 差异：`无`
- 推荐项：`无`

## 用户确认与协同约束

- `用户确认状态：已确认`
- `未确认事项：无`
- `用户确认结论：本轮直接新建一个任务；修复 decompass expectation；将实现和 test 文件迁移到与 expectation 同主题目录；该 pass 不再属于 lowing/lowering。`
- `未确认前处理要求：无`
- `若用户要求至少询问 3 人：无`
- `询问记录 1：守护最好的爱莉希雅 / 已互评通过 / 补充要求已纳入正文：kernel_gen/passes/lowering/__init__.py、expectation/pass/pipeline/default_lowering.py 与 expectation/pass/decompass 的旧 helper 依赖清理`
- `询问记录 2：无`
- `询问记录 3：无`

## 参考资料

- [`expectation/pass/decompass/__main__.py`](../../expectation/pass/decompass/__main__.py)
- [`expectation/pass/decompass/softmax.py`](../../expectation/pass/decompass/softmax.py)
- [`kernel_gen/passes/lowering/decompass.py`](../../kernel_gen/passes/lowering/decompass.py)
- [`test/pass/test_decompose_nn_softmax.py`](../../test/pass/test_decompose_nn_softmax.py)
- [`spec/pass/lowering/decompass.md`](../../spec/pass/lowering/decompass.md)
- [`spec/pass/pipeline/default_lowering.md`](../../spec/pass/pipeline/default_lowering.md)

## 归档任务记录

时间：2026-04-20 03:55 +0800
经办人：李白
任务：T-20260420-40a1c19e
任务目标：将 `ARCHITECTURE/plan/decompass_pass_rehome_green_plan.md` 归档到 `agents/codex-multi-agents/log/task_records/done_plan/2026/16/decompass_pass_rehome_green_plan.md`，并在归档合并后通知管理员执行 `-done-plan`；同步清理 `ARCHITECTURE/plan/decompass_pass_rehome_green_plan.md`。
改动：在指定 `worktree` 中新增归档文件 `agents/codex-multi-agents/log/task_records/done_plan/2026/16/decompass_pass_rehome_green_plan.md`（内容同步自主仓本地计划书）；同步清理动作按任务口径执行，确保 `ARCHITECTURE/plan/decompass_pass_rehome_green_plan.md` 在当前 `worktree` 与主仓本地现场均已清理。
验证：`git -C /home/lfr/kernelcode_generate/wt-20260420-archive-decompass-plan status --short --branch` -> 仅命中当前归档文件；`diff -u /home/lfr/kernelcode_generate/ARCHITECTURE/plan/decompass_pass_rehome_green_plan.md <(sed -n '1,309p' /home/lfr/kernelcode_generate/wt-20260420-archive-decompass-plan/agents/codex-multi-agents/log/task_records/done_plan/2026/16/decompass_pass_rehome_green_plan.md)` -> 同步前已核对无差异（前 309 行与源计划书一致）；`test -f /home/lfr/kernelcode_generate/wt-20260420-archive-decompass-plan/ARCHITECTURE/plan/decompass_pass_rehome_green_plan.md` -> 失败（已清理）；`test -f /home/lfr/kernelcode_generate/ARCHITECTURE/plan/decompass_pass_rehome_green_plan.md` -> 失败（已清理）。
结论：当前归档 merge 输入已收口，下一步执行单次提交、`git push`、合并后 `git fetch`、`-done`，并回报管理员继续执行 `-done-plan`。
