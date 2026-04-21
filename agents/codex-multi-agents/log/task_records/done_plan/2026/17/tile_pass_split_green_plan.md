# tile_pass_split_green_plan.md

## 文档信息

- 创建者：`榕`
- 最后一次更改：`榕`
- 目标 `spec`：
  - [`spec/pass/lowering/tile.md`](../../spec/pass/lowering/tile.md)
  - 新增 [`spec/pass/lowering/tile_analysis.md`](../../spec/pass/lowering/tile_analysis.md)
  - 新增 [`spec/pass/lowering/tile_elewise.md`](../../spec/pass/lowering/tile_elewise.md)
  - 新增 [`spec/pass/lowering/tile_reduce.md`](../../spec/pass/lowering/tile_reduce.md)
  - [`spec/pass/registry.md`](../../spec/pass/registry.md)
  - [`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)
  - [`spec/dialect/tuner.md`](../../spec/dialect/tuner.md)
  - [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
  - 删除 [`spec/pass/lowering/kernel_split.md`](../../spec/pass/lowering/kernel_split.md)
- 目标 `API`：
  - 删除 [`kernel_gen/passes/lowering/tile.py`](../../kernel_gen/passes/lowering/tile.py)
  - 新增 [`kernel_gen/passes/lowering/tile_analysis.py`](../../kernel_gen/passes/lowering/tile_analysis.py)
  - 新增 [`kernel_gen/passes/lowering/tile_elewise.py`](../../kernel_gen/passes/lowering/tile_elewise.py)
  - 新增 [`kernel_gen/passes/lowering/tile_reduce.py`](../../kernel_gen/passes/lowering/tile_reduce.py)
  - 删除 [`kernel_gen/passes/lowering/kernel_split.py`](../../kernel_gen/passes/lowering/kernel_split.py)
  - [`kernel_gen/passes/lowering/__init__.py`](../../kernel_gen/passes/lowering/__init__.py)
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
  - [`kernel_gen/passes/pass_manager.py`](../../kernel_gen/passes/pass_manager.py)
  - [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)
  - [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py)
- 目标 `test`：
  - 删除或重写 [`test/pass/test_lowering_tile.py`](../../test/pass/test_lowering_tile.py)
  - 删除或重写 [`test/pass/test_lowering_kernel_split.py`](../../test/pass/test_lowering_kernel_split.py)
  - 新增 `test/pass/test_lowering_tile_analysis.py`（由执行者补齐）
  - 新增 `test/pass/test_lowering_tile_elewise.py`（由执行者补齐）
  - 新增 `test/pass/test_lowering_tile_reduce.py`（由执行者补齐）
  - [`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)
  - [`test/pass/test_pass_registry.py`](../../test/pass/test_pass_registry.py)
  - [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)
- 目标 `验收资产`：
  - [`expectation/pass/tile/analysis`](../../expectation/pass/tile/analysis)
  - [`expectation/pass/tile/elewise`](../../expectation/pass/tile/elewise)
  - [`expectation/pass/tile/reduce`](../../expectation/pass/tile/reduce)
  - [`expectation/pass/tile/__main__.py`](../../expectation/pass/tile/__main__.py)
- 目标 `功能实现`：
  - [`kernel_gen/passes/lowering/__init__.py`](../../kernel_gen/passes/lowering/__init__.py)
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
  - [`kernel_gen/passes/pass_manager.py`](../../kernel_gen/passes/pass_manager.py)
  - [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)
  - [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py)

## 任务清单

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `S1` | `无` | `待管理员创建（tile-analysis-modulepass）` | `待管理员创建（tile-pass-split-s1.md）` |
| `S2` | `S1` | `待管理员创建（tile-elewise-modulepass）` | `待管理员创建（tile-pass-split-s2.md）` |
| `S3` | `S1` | `待管理员创建（tile-reduce-modulepass）` | `待管理员创建（tile-pass-split-s3.md）` |
| `S4` | `S2,S3` | `待管理员创建（tile-cleanup-codegen-removal）` | `待管理员创建（tile-pass-split-s4.md）` |

## 评审摘要

- 当前状态：`正式互评已通过`
- 评审人：`守护最好的爱莉希雅`、`大闸蟹`
- 结论摘要：
  - `S1~S4` 的拆分与依赖合理：`S1` 先收 `analysis + registry/pass_manager` 底座，`S2/S3` 并行收 `elewise/reduce`，`S4` 再统一删除旧 pass、旧 bridge 并迁移 codegen 合同，边界清楚。
  - 三个 `ModulePass` 的公开 API 与删除边界清楚：旧 `TilePass / KernelSplitPass / tile.step_value / kernel_split.tile_value / tile.symbol_literal / kernel_split.symbol_literal` 都已明确列入删除范围，`PassManager` 的旧 `"tile"` 顺序约束迁移点也已写入 `S4`。
  - `gen_kernel` 的边界合适：只消费新 split-after-IR 结果，保留对直接消费对象的最小 malformed-input 拒绝，但不重复承担上游 tile family 的全量合同验证。
  - `spec/pass/lowering/tile.md` 降级为总览/索引、`worktree-first` 验收口径、以及实现/审查/维护三类角色询问记录都已写实落正文，当前版本可按计划书标准继续推进。

## S4 合同资产授权记录

- 授权人：`大闸蟹`
- 授权时间：`2026-04-21`
- 授权范围：`T-20260421-6bc350a7` 当前 S4 合同任务可纳入 5 个 `expectation/pass/tile` 合同资产：[`expectation/pass/tile/__main__.py`](../../expectation/pass/tile/__main__.py)、[`expectation/pass/tile/reduce/__init__.py`](../../expectation/pass/tile/reduce/__init__.py)、[`expectation/pass/tile/reduce/__main__.py`](../../expectation/pass/tile/reduce/__main__.py)、[`expectation/pass/tile/reduce/fc.py`](../../expectation/pass/tile/reduce/fc.py)、[`expectation/pass/tile/reduce/matmul.py`](../../expectation/pass/tile/reduce/matmul.py)。
- 处理口径：不调整 `S4` 验收边界；[`expectation/pass/tile/reduce`](../../expectation/pass/tile/reduce) 与 [`expectation/pass/tile/__main__.py`](../../expectation/pass/tile/__main__.py) 仍是计划书目标验收资产。
- 复核要求：review 必须基于已纳入索引的 `expectation/pass/tile` 文件执行目录入口验证，不得用被忽略的本地副本证明通过。

## 终验 / 复验 / 修复复核记录

- 结论人：`守护最好的爱莉希雅`
- 结论时间：`2026-04-21 21:14:27 +0800`
- 结论：`通过`
- 验证基线：`主目录 /home/lfr/kernelcode_generate 已执行 git fetch origin main；HEAD=origin/main=9f64a3a41544ceefad70138f3628c0abf35c9bd4，head_is_ancestor=0 且 origin_is_ancestor=0，主目录已对齐最新主线，无需改用其他远端现场。`
- 执行目录：`/home/lfr/kernelcode_generate`
- 验证命令与结果：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate python3 -m expectation.pass.tile.analysis`：`exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate python3 -m expectation.pass.tile.elewise`：`exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate python3 -m expectation.pass.tile.reduce`：`exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate python3 -m expectation.pass.tile`：`exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate pytest -q test/pass/test_lowering_tile_analysis.py test/pass/test_lowering_tile_elewise.py test/pass/test_lowering_tile_reduce.py`：`13 passed`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate pytest -q test/pass/test_pass_registry.py -k "tile_analysis or tile_elewise or tile_reduce"`：`3 passed, 24 deselected`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate pytest -q test/pass/test_pass_manager.py -k "tile"`：`11 passed, 13 deselected`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate pytest -q test/dsl/test_gen_kernel.py -k "tile or kernel_split"`：`12 passed, 49 deselected`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate pytest -q test/pass/test_lowering_tile.py`：`2 passed`
- 补充审计：`load_builtin_passes()` 后 `build_registered_pass("tile-analysis")`、`build_registered_pass("tile-elewise")`、`build_registered_pass("tile-reduce")` 均可构造目标 `ModulePass`；`build_registered_pass("tile")` 稳定报 `PassRegistryError`。旧 bridge 字符串仅出现在拒绝逻辑、负向断言、测试和文档描述中；公开旧 `TilePass / KernelSplitPass` 类未残留。
- 说明：`kernel_gen/passes/lowering/tile.py` 当前按实现收口为 helper-only 模块，`test/pass/test_lowering_tile.py` 已锁定其不再公开旧 `TilePass / TileAnalysisPass / bridge op`；该 helper 保留不构成公开旧 pass 残留。
- 最小阻断项：`无`
- 是否满足归档前置条件：`是`
- 大闸蟹复核结论人：`大闸蟹`
- 大闸蟹复核结论：`通过`
- 大闸蟹复核验证基线：`执行目录=/home/lfr/kernelcode_generate；已执行 git fetch origin main；git merge --ff-only origin/main 返回 Already up to date；HEAD_REF=refs/heads/main，main=origin/main=9f64a3a41544ceefad70138f3628c0abf35c9bd4`
- 大闸蟹复核命令与结果：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate:/home/lfr/kernelcode_generate python3 -m expectation.pass.tile.analysis`：`exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate:/home/lfr/kernelcode_generate python3 -m expectation.pass.tile.elewise`：`exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate:/home/lfr/kernelcode_generate python3 -m expectation.pass.tile.reduce`：`exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate:/home/lfr/kernelcode_generate python3 -m expectation.pass.tile`：`exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate:/home/lfr/kernelcode_generate pytest -q test/pass/test_lowering_tile_analysis.py test/pass/test_lowering_tile_elewise.py test/pass/test_lowering_tile_reduce.py`：`13 passed`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate:/home/lfr/kernelcode_generate pytest -q test/pass/test_pass_registry.py -k "tile_analysis or tile_elewise or tile_reduce"`：`3 passed, 24 deselected`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate:/home/lfr/kernelcode_generate pytest -q test/pass/test_pass_manager.py -k "tile"`：`11 passed, 13 deselected`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate:/home/lfr/kernelcode_generate pytest -q test/dsl/test_gen_kernel.py -k "tile or kernel_split"`：`12 passed, 49 deselected`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate:/home/lfr/kernelcode_generate pytest -q test/pass/test_lowering_tile.py`：`2 passed`
- 大闸蟹复核补充检查：`rg 残留检查未发现旧公开 class TilePass / class KernelSplitPass / build_registered_pass("tile")；kernel_split.py、kernel_split.md、test_lowering_kernel_split.py 未出现在索引文件列表；kernel_gen/passes/lowering/tile.py 仅保留 TilePassError / _raise_tile_error helper。`
- 大闸蟹复核最小阻断项：`无`
- 大闸蟹复核是否满足归档前置条件：`是`

## 输入摘要

- 目标：做新的 tile family pass，直接使用 xdsl / MLIR 风格基础设施，公开上只保留 `tile-analysis`、`tile-elewise`、`tile-reduce` 三个 pass。
- 不做什么：本轮不重做整体 pipeline，不为 `symbol.for` 额外引入 control-flow interface，不重构其他无关 pass family。
- 当前痛点：仓库实现和 spec 仍停留在旧 `TilePass + option`、`KernelSplitPass`、`tile.step_value / kernel_split.tile_value` 口径，而 expectation 已经先改成三 pass + `tile.analysis / tile.tile_exprs` 新合同，公开层已经分叉。
- 完成后最想看到的例子：`build_registered_pass("tile-analysis")`、`build_registered_pass("tile-elewise")`、`build_registered_pass("tile-reduce")` 都直接返回 `ModulePass`；tile 后 IR 保留 `tile.analysis` 和 `tile.tile_exprs`；`gen_kernel(...)` 不再依赖 `kernel_split.tile_value / tile.step_value`。
- 额外收口点：`gen_kernel / emit_c` 里遗留的 `kernel_split.symbol_literal / tile.symbol_literal` 旧桥也必须一并清掉；`PassManager.run(...)` 里对单一 `"tile"` 名字的顺序约束也必须迁到新三 pass 名的明确规则。

## 计划目标

- 删除旧 `TilePass`、旧 `KernelSplitPass` 以及它们对应的公开 spec / registry / test / expectation 合同。
- 新增并收口三个公开 `ModulePass`：`TileAnalysisPass`、`TileElewisePass`、`TileReducePass`。
- 让这三个 pass 的实现尽量直接使用 xdsl 的 `ModulePass`、`PatternRewriteWalker`、`GreedyRewritePatternApplier`、fold / canonicalize / CSE 基础设施；不再继续扩张手写整块 IR 重建。
- 让 tile family 的公开 IR 合同分层清楚：
  - `tile-analysis` 只负责写入 `tile.analysis + tile.tile_exprs`
  - `tile-elewise / tile-reduce` 负责消费这两类元信息并把“未切分 op”改写成 tiled IR
  - `gen_kernel` 只消费经过 tile family 正常收口后的 split-after-IR 结果，不再依赖 `tile.step_value / kernel_split.tile_value / tile.symbol_literal / kernel_split.symbol_literal`
- 让 `gen_kernel / emit_c / spec/dsl/gen_kernel.md` 同步迁到新 split-after-IR 合同，禁止继续依赖旧 bridge op。
- 保持 `build_registered_pass(...)` 和 `PassManager.run(...)` 的调用方式稳定；对外只变公开 pass 名，不变工具调用形态。

## 当前基线

- 当前公开合同：
  - [`expectation/pass/tile/analysis`](../../expectation/pass/tile/analysis)、[`expectation/pass/tile/elewise`](../../expectation/pass/tile/elewise)、[`expectation/pass/tile/reduce`](../../expectation/pass/tile/reduce) 已经按三个公开 pass 的新合同编排。
  - 这些 expectation 已明确：
    - `tile-analysis` 产出 `tile.analysis` 与 `tile.tile_exprs`
    - `tile-elewise` / `tile-reduce` after IR 继续保留 `tile.analysis` 与 `tile.tile_exprs`
    - `tuner.param` 直接参与 tile，不再出现 `tile.step_value`
    - `tile-analysis` 只做分析与标注，不负责切分
    - `tile-elewise / tile-reduce` 只对“已有 tile.analysis + tile.tile_exprs 且尚未切分”的目标 op 生效
  - 但 [`spec/pass/lowering/tile.md`](../../spec/pass/lowering/tile.md) 与 [`spec/pass/lowering/kernel_split.md`](../../spec/pass/lowering/kernel_split.md) 仍是旧单 pass / 兼容 alias 合同。
- 当前公开 API：
  - 唯一实现仍是 [`kernel_gen/passes/lowering/tile.py`](../../kernel_gen/passes/lowering/tile.py) 里的 `TilePass(Pass)` 与 `TileAnalysisPass(Pass)`。
  - [`kernel_gen/passes/lowering/kernel_split.py`](../../kernel_gen/passes/lowering/kernel_split.py) 仍是旧 `TilePass` 的兼容别名，公开名仍指向 `"tile"`。
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py) 仍注册旧 `TilePass` / `TileAnalysisPass`，没有新的 `tile-elewise` / `tile-reduce` 公开入口。
  - [`kernel_gen/passes/pass_manager.py`](../../kernel_gen/passes/pass_manager.py) 仍把 `"tile"` 作为 `symbol-loop-hoist` 的顺序前置名，尚未迁到新三 pass 名。
- 当前实现入口：
  - 旧 `tile.py` 里仍内置 `_TileSymbolLiteralOp`、`_TileStepValueOp`，并在 matmul/elewise 改写里生成 `tile.step_value`。
  - [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py) 和 [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md) 仍显式要求 `kernel_split.tile_value / tile.step_value` 作为 split-after-IR 的 tile bridge。
  - [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py) 仍保留 `tile.symbol_literal / tile.step_value` 的发射逻辑。
  - `gen_kernel / emit_c` 里旧 `kernel_split.symbol_literal / tile.symbol_literal` 路径当前仍存在，需在 `S4` 与新 split-after-IR codegen 合同里一并清理。
- 当前测试与验收资产：
  - expectation 已转向新合同，但 pytest 仍主要锁旧 `TilePass`、旧 options、旧 `KernelSplitPass` alias 与旧 bridge op。
  - [`test/pass/test_lowering_kernel_split.py`](../../test/pass/test_lowering_kernel_split.py) 仍把 `KernelSplitPass` 和旧 `TilePass` 绑定成兼容行为。
- 当前缺口或失败点：
  - 公开 expectation 与公开 spec / registry / implementation / codegen 已经明显分叉。
  - 旧 `TilePass` 把 analysis、elewise、reduce 都塞在一个类和一组选项里，不符合当前三 pass 合同。
  - 旧 split-after-IR codegen 仍依赖 `kernel_split.tile_value / tile.step_value`，与用户刚确认的“不要了”直接冲突。

## 合同真源顺序

- `expectation/pass/tile/{analysis,elewise,reduce} > spec/pass/lowering/tile_{analysis,elewise,reduce}.md + spec/dsl/gen_kernel.md + spec/dialect/tuner.md > test/pass/test_lowering_tile_*.py + test/dsl/test_gen_kernel.py > 当前实现`

## 方案比较与选型

- 不采用方案：继续保留 `TilePass`，只把内部 option 改成 `tile-analysis / tile-elewise / tile-reduce` 三种分支。
  - 原因：公开 API 仍是单 pass，和 expectation 真源已经定下的“三个 pass”不一致；维护成本不会下降。
- 不采用方案：保留 `KernelSplitPass` 兼容壳，只把它内部转发到新的 `TileReducePass`。
  - 原因：用户已经明确“去除之前的 tile pass 和 kernel tile 这两个 pass”，继续保留旧兼容名只会拖长双合同时期。
- 不采用方案：新 tile family 仍继续使用 `tile.step_value / kernel_split.tile_value` 作为 bridge。
  - 原因：用户已明确旧 bridge op 不要；expectation 也已经全面转向 `tuner.param + tile.analysis + tile.tile_exprs + symbol.for + dma.view`。
- 不采用方案：保留旧 `tile.symbol_literal / kernel_split.symbol_literal` 作为“只读常量桥”。
  - 原因：这会留下第二套 split-after-IR 元信息来源，继续拖长新旧合同共存期。
- 采用方案：
  - 新增 `TileAnalysisPass`、`TileElewisePass`、`TileReducePass` 三个 `ModulePass`；
  - 删除旧 `TilePass`、旧 `KernelSplitPass`、旧 `tile.step_value / kernel_split.tile_value / tile.symbol_literal / kernel_split.symbol_literal` 及其公开 spec / emit / gen_kernel 合同；
  - 保持 `build_registered_pass(...)` / `PassManager.run(...)` 调用方式稳定，但公开 pass 名只剩：
    - `tile-analysis`
    - `tile-elewise`
    - `tile-reduce`
- 最小公开接口：
  - `build_registered_pass("tile-analysis")`
  - `build_registered_pass("tile-elewise")`
  - `build_registered_pass("tile-reduce")`

## 公开 API 设计

### TileAnalysisPass

- 公开入口：
  - `kernel_gen.passes.lowering.tile_analysis.TileAnalysisPass`
  - `build_registered_pass("tile-analysis")`
- 公开类基类：
  - `xdsl.passes.ModulePass`
- 公开方法签名：
  - `apply(ctx: Context, op: builtin.ModuleOp) -> None`
- 公开行为：
  - 只给支持的原始 op 写入 `tile.analysis` 与 `tile.tile_exprs`
  - 不生成 `symbol.for`
  - 不生成 `dma.view`
  - 不生成 `tuner.param`
  - 不生成旧 bridge op
  - 对已经带有 split 结果的 op 不重复改写
- 最小示例：

```python
from xdsl.context import Context
from xdsl.dialects import builtin
from kernel_gen.passes.registry import build_registered_pass

ctx = Context()
module = builtin.ModuleOp([])
tile_analysis = build_registered_pass("tile-analysis")
tile_analysis.apply(ctx, module)
```

### TileElewisePass

- 公开入口：
  - `kernel_gen.passes.lowering.tile_elewise.TileElewisePass`
  - `build_registered_pass("tile-elewise")`
- 公开类基类：
  - `xdsl.passes.ModulePass`
- 公开方法签名：
  - `apply(ctx: Context, op: builtin.ModuleOp) -> None`
- 公开行为：
  - 消费现有 `tile.analysis` / `tile.tile_exprs`
  - 只处理“已有 `tile.analysis + tile.tile_exprs` 且尚未切分”的目标 op
  - 只处理纯 elewise family：
    - `kernel.binary_elewise`
    - compare 风格 `kernel.binary_elewise`
    - `dma.broadcast`
    - expectation 中 `fc` 链路里的 elewise 部分
  - 可以生成：
    - `tuner.param`
    - `symbol.for`
    - `dma.view`
  - after IR 必须继续保留被改写原 op 上的：
    - `tile.analysis`
    - `tile.tile_exprs`
  - 不得生成：
    - `tile.step_value`
    - `kernel_split.tile_value`
  - 前置失败合同：
    - 若目标 op 缺失 `tile.analysis` 或 `tile.tile_exprs`，则拒绝按 tile 路径改写
    - 若目标 op 已经是 split 后形态，则拒绝重复切分
- 最小示例：

```python
tile_analysis = build_registered_pass("tile-analysis")
tile_elewise = build_registered_pass("tile-elewise")
tile_analysis.apply(ctx, module)
tile_elewise.apply(ctx, module)
```

### TileReducePass

- 公开入口：
  - `kernel_gen.passes.lowering.tile_reduce.TileReducePass`
  - `build_registered_pass("tile-reduce")`
- 公开类基类：
  - `xdsl.passes.ModulePass`
- 公开方法签名：
  - `apply(ctx: Context, op: builtin.ModuleOp) -> None`
- 公开行为：
  - 消费现有 `tile.analysis` / `tile.tile_exprs`
  - 只处理“已有 `tile.analysis + tile.tile_exprs` 且尚未切分”的目标 op
  - 只处理 reduction family：
    - `kernel.matmul`
    - `fc` 风格链路中的 matmul-reduction 部分
  - 只 tile reduce 轴，不额外切 elewise 轴
  - 可生成：
    - `tuner.param`
    - `symbol.for`
    - `dma.view`
    - 临时 `dma.alloc + dma.fill`（仅当当前 reduction 合同需要显式累加缓冲）
  - after IR 继续保留被改写原 op 上的：
    - `tile.analysis`
    - `tile.tile_exprs`
  - 不得生成：
    - `tile.step_value`
    - `kernel_split.tile_value`
  - 前置失败合同：
    - 若目标 op 缺失 `tile.analysis` 或 `tile.tile_exprs`，则拒绝按 tile 路径改写
    - 若目标 op 已经是 split 后形态，则拒绝重复切分
- 最小示例：

```python
tile_analysis = build_registered_pass("tile-analysis")
tile_reduce = build_registered_pass("tile-reduce")
tile_analysis.apply(ctx, module)
tile_reduce.apply(ctx, module)
```

### PassManager / registry 兼容桥

- 公开入口保持：
  - `build_registered_pass(...)`
  - `PassManager.run(...)`
- 公开兼容合同：
  - 对 tile family 新 pass，`build_registered_pass(...)` 直接返回 `ModulePass`
  - `PassManager.run(...)` 直接兼容执行 `ModulePass.apply(ctx, module)`
  - `PassManager.run(...)` 中原来依赖单一 `"tile"` 名字的顺序约束，统一迁为：
    - `symbol-loop-hoist` 允许依赖 `tile-elewise` 或 `tile-reduce` 已经 materialize `symbol.for`
    - 不再把旧 `"tile"` 当作合法前置名
  - 不再为 tile family 新增“伪 Pass 适配器”或旧 `run(...)` 包装壳
- 最小示例：

```python
from kernel_gen.passes.pass_manager import PassManager
from kernel_gen.passes.registry import build_registered_pass

pm = PassManager(name="tile")
pm.add_pass(build_registered_pass("tile-analysis"))
pm.add_pass(build_registered_pass("tile-elewise"))
module = pm.run(module)
```

## 完成态定义

- 仓库对外不再暴露：
  - `TilePass`
  - `KernelSplitPass`
  - `build_registered_pass("tile")`
  - `tile.step_value`
  - `kernel_split.tile_value`
  - `tile.symbol_literal`
  - `kernel_split.symbol_literal`
- 仓库对外只保留：
  - `tile-analysis`
  - `tile-elewise`
  - `tile-reduce`
- `expectation/pass/tile/analysis`、`elewise`、`reduce` 三个 family 与实现一致，不再要求旧 option 组合或旧 bridge op。
- `tile-elewise` / `tile-reduce` 输出的 after IR 中，原始被改写 op 上的 `tile.analysis` 与 `tile.tile_exprs` 必须保留。
- `gen_kernel(...)` 的 split-after-IR 合同改成依赖：
  - `tile-analysis / tile-elewise / tile-reduce` 产出的新 split-after-IR 语义
  - `tile.analysis`
  - `tile.tile_exprs`
  - `tuner.param`
  - `symbol.for`
  不再接受 `kernel_split.tile_value / tile.step_value / kernel_split.symbol_literal / tile.symbol_literal`。
  - 旧 bridge op 与不完整 tile 合同的失败，应在进入 codegen 前的 tile/pipeline 阶段暴露；`gen_kernel` 不额外承担这层专门检测逻辑。
  - `gen_kernel` 仍保留对其直接消费对象的最小 malformed-input 拒绝，但不重复承担上游 tile family 的全量合同验证。
- 旧 `kernel_split` 相关 spec、test、compat path 完成清理，不再作为公开入口保留。

## 验收设计

- 验收资产：
  - [`expectation/pass/tile/analysis`](../../expectation/pass/tile/analysis)
  - [`expectation/pass/tile/elewise`](../../expectation/pass/tile/elewise)
  - [`expectation/pass/tile/reduce`](../../expectation/pass/tile/reduce)
  - [`expectation/pass/tile/__main__.py`](../../expectation/pass/tile/__main__.py)
  - `test/pass/test_lowering_tile_analysis.py`
  - `test/pass/test_lowering_tile_elewise.py`
  - `test/pass/test_lowering_tile_reduce.py`
  - [`test/pass/test_pass_registry.py`](../../test/pass/test_pass_registry.py)
  - [`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)
  - [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)
- 锁定输出：
  - `tile-analysis` 只新增/更新 `tile.analysis + tile.tile_exprs`
  - `tile-elewise` 只切 elewise 轴
  - `tile-reduce` 只切 reduce 轴
  - after IR 保留 `tile.analysis + tile.tile_exprs`
  - 全链路不再出现 `tile.step_value` / `kernel_split.tile_value`
  - `tile-elewise / tile-reduce` 对缺失 `tile.analysis / tile.tile_exprs` 或已切分目标 op 有稳定失败合同
  - 旧 bridge op 与不完整 split-after-IR 输入在 tile/pipeline 阶段被稳定拦截，不要求 `gen_kernel` 额外专门检测
- 最终必过命令：
  - `PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate python3 -m expectation.pass.tile.analysis`
  - `PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate python3 -m expectation.pass.tile.elewise`
  - `PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate python3 -m expectation.pass.tile.reduce`
  - `PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate python3 -m expectation.pass.tile`
  - `PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate pytest -q test/pass/test_lowering_tile_analysis.py test/pass/test_lowering_tile_elewise.py test/pass/test_lowering_tile_reduce.py`
  - `PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate pytest -q test/pass/test_pass_registry.py -k "tile_analysis or tile_elewise or tile_reduce"`
  - `PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate pytest -q test/pass/test_pass_manager.py -k "tile"`
  - `PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate pytest -q test/dsl/test_gen_kernel.py -k "tile or kernel_split"`
- 执行阶段边界：
  - `S2/S3/S4` 默认不直接修改 `expectation/pass/tile/**`；这些文件作为合同真源与最终验收资产保留。
  - 若某个执行 worktree 的索引中未包含 `expectation/pass/tile/**` 改动，不得使用该 worktree 中未纳入索引的本地 expectation 副本证明 `python3 -m expectation.pass.tile.reduce` 或 `python3 -m expectation.pass.tile` 通过。
  - 目录级 expectation 全绿属于最终验收 / 明确授权合同任务的职责；普通 build 任务只需证明实现、spec、pytest 与 codegen 清理不回退，并保留失败现场供后续合同任务或终验判断。

## 阶段拆分

### S1：收口 TileAnalysisPass 与新公共合同底座

#### 阶段目标

- 新建 `TileAnalysisPass(ModulePass)`，并让 registry / pass_manager / spec / tuner contract / expectation analysis family 全部对齐到新口径。
- 明确 `tuner.param` 在 tile family 内直接作为 `!symbol.int` 使用，不再需要 `tile.step_value`。
- 明确 [`spec/pass/lowering/tile.md`](../../spec/pass/lowering/tile.md) 只保留总览 / 索引、旧合同退场与迁移说明，不再继续承载新 tile family 的公开行为定义。

#### 目标 spec / API

- [`spec/pass/lowering/tile.md`](../../spec/pass/lowering/tile.md)
- 新增 [`spec/pass/lowering/tile_analysis.md`](../../spec/pass/lowering/tile_analysis.md)
- [`spec/pass/registry.md`](../../spec/pass/registry.md)
- [`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)
- [`spec/dialect/tuner.md`](../../spec/dialect/tuner.md)
- 新增 [`kernel_gen/passes/lowering/tile_analysis.py`](../../kernel_gen/passes/lowering/tile_analysis.py)
- [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
- [`kernel_gen/passes/pass_manager.py`](../../kernel_gen/passes/pass_manager.py)

#### 合同真源

- `expectation/pass/tile/analysis > spec/pass/lowering/tile_analysis.md > test/pass/test_lowering_tile_analysis.py > 当前实现`

#### 预期输出

```text
build_registered_pass("tile-analysis") -> ModulePass
tile-analysis 只写 tile.analysis + tile.tile_exprs
不再有 TilePass、analysis-only、tile.step_value
spec/pass/lowering/tile.md 仅保留旧合同退场/迁移说明
spec/pass/lowering/tile.md 降级为 tile family 总览 / 索引
```

#### 任务新建建议

- `任务类型：build`
- `任务目标：实现 TileAnalysisPass(ModulePass) 并收口 registry/pass_manager/tuner 新合同`

### S2：收口 TileElewisePass

#### 阶段目标

- 新建 `TileElewisePass(ModulePass)`，按 xdsl pattern rewriter 风格重构 elewise tile。
- after IR 与 `expectation/pass/tile/elewise` 既有合同真源对齐。

#### 目标 spec / API

- 新增 [`spec/pass/lowering/tile_elewise.md`](../../spec/pass/lowering/tile_elewise.md)
- 新增 [`kernel_gen/passes/lowering/tile_elewise.py`](../../kernel_gen/passes/lowering/tile_elewise.py)
- [`expectation/pass/tile/elewise`](../../expectation/pass/tile/elewise)（合同真源 / 验收资产）

#### 合同真源

- `expectation/pass/tile/elewise > spec/pass/lowering/tile_elewise.md > test/pass/test_lowering_tile_elewise.py > 当前实现`

#### 预期输出

```text
tile-elewise 只切 elewise 轴
after IR 继续保留 tile.analysis + tile.tile_exprs
无 tile.step_value / kernel_split.tile_value
缺失 tile.analysis / tile.tile_exprs 或已切分目标 op 时走稳定失败合同
```

#### 任务新建建议

- `任务类型：build`
- `任务目标：实现 TileElewisePass(ModulePass)，收口对应 spec/pytest/registry/codegen，并让输出与现有 elewise expectation 真源对齐；本阶段 expectation 作为合同真源与验收资产，不要求 build 角色直接修改`

### S3：收口 TileReducePass

#### 阶段目标

- 新建 `TileReducePass(ModulePass)`，按 xdsl pattern rewriter 风格重构 reduce tile。
- after IR 与 `expectation/pass/tile/reduce` 既有合同真源对齐。

#### 目标 spec / API

- 新增 [`spec/pass/lowering/tile_reduce.md`](../../spec/pass/lowering/tile_reduce.md)
- 新增 [`kernel_gen/passes/lowering/tile_reduce.py`](../../kernel_gen/passes/lowering/tile_reduce.py)
- [`expectation/pass/tile/reduce`](../../expectation/pass/tile/reduce)（合同真源 / 验收资产）

#### 合同真源

- `expectation/pass/tile/reduce > spec/pass/lowering/tile_reduce.md > test/pass/test_lowering_tile_reduce.py > 当前实现`

#### 预期输出

```text
tile-reduce 只切 reduce 轴
after IR 继续保留 tile.analysis + tile.tile_exprs
无 tile.step_value / kernel_split.tile_value
缺失 tile.analysis / tile.tile_exprs 或已切分目标 op 时走稳定失败合同
```

#### 任务新建建议

- `任务类型：build`
- `任务目标：实现 TileReducePass(ModulePass)，收口对应 spec/pytest/registry/codegen，并让输出与现有 reduce expectation 真源对齐；本阶段 expectation 作为合同真源与验收资产，不要求 build 角色直接修改`

### S4：删除旧 TilePass / KernelSplitPass 并迁移 codegen 合同

#### 阶段目标

- 删除旧 `TilePass`、旧 `KernelSplitPass`、旧 bridge op 与其 spec / test / registry / codegen 合同。
- 把 `gen_kernel / emit_c / spec/dsl/gen_kernel.md` 迁到新 tile family 合同。
- 一并清掉 `gen_kernel / emit_c` 中遗留的 `kernel_split.symbol_literal / tile.symbol_literal` 旧桥，并把 `PassManager` 中原先依赖 `"tile"` 的顺序约束迁到新三 pass 名。

#### 目标 spec / API

- 删除 [`kernel_gen/passes/lowering/tile.py`](../../kernel_gen/passes/lowering/tile.py)
- 删除 [`kernel_gen/passes/lowering/kernel_split.py`](../../kernel_gen/passes/lowering/kernel_split.py)
- 删除 [`spec/pass/lowering/kernel_split.md`](../../spec/pass/lowering/kernel_split.md)
- [`kernel_gen/passes/lowering/__init__.py`](../../kernel_gen/passes/lowering/__init__.py)
- [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)
- [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py)
- [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
- [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)

#### 合同真源

- `expectation/pass/tile/{analysis,elewise,reduce} + spec/dsl/gen_kernel.md > test/dsl/test_gen_kernel.py > 当前实现`
- `S4` 执行任务不直接接管 `expectation/pass/tile/**` 修改；若当前索引不包含这些合同资产，`S4` 不得用未纳入索引的本地副本证明目录入口通过。

#### 预期输出

```text
仓库不再有 TilePass / KernelSplitPass
gen_kernel / emit_c 不再接受 kernel_split.tile_value / tile.step_value / kernel_split.symbol_literal / tile.symbol_literal
split-after-IR 统一依赖新的 tile family 产出语义，不再把 dma.view 绑定成唯一合法 materialize 形式
PassManager 不再依赖单一 "tile" 名字做顺序判断
```

#### 任务新建建议

- `任务类型：build`
- `任务目标：删除旧 tile/kernel_split pass，并迁移 gen_kernel/emit_c/spec/test 到新合同；不要求本任务直接修改 expectation/pass/tile/**，目录级 expectation 通过由最终验收或明确授权合同任务处理`

## 用户确认与协同约束

- 用户已确认：
  - 旧 `TilePass` 与旧 `KernelSplitPass` 都要移除。
  - `kernel_split.tile_value / tile.step_value` 不再保留。
  - `tile.tile_exprs` 作为公开 attr，统一承接静态/动态 tile 表达式。
  - 这轮重点是使用 xdsl / MLIR 风格基础设施重构 pass；不先重做 pipeline。
- 已完成的不同角色视角询问记录：
  - `小李飞刀（实现/结构）`：
    - `S1~S4` 拆分可行；
    - `TileAnalysisPass / TileElewisePass / TileReducePass` 按 `ModulePass + pattern rewriter` 方向可落地；
    - 补充要求在 `S4` 明确清理 `gen_kernel / emit_c` 中的 `kernel_split.symbol_literal / tile.symbol_literal` 旧桥，并把 `PassManager` 从单一 `"tile"` 名的顺序约束迁到新三 pass 名。
  - `睡觉小分队（合同/spec）`：
    - 旧 `TilePass / KernelSplitPass / tile.step_value / kernel_split.tile_value` 的删除边界基本可接受；
    - 需明确 `spec/pass/lowering/tile.md` 降级为总览 / 索引；
    - 需补 `tile-elewise / tile-reduce` 缺失 `tile.analysis / tile.tile_exprs` 或目标 op 已切分时的前置失败合同。
  - `提莫炖蘑菇（review/验收）`：
    - `expectation/pass/tile` 作为合同真源的边界已写清；
    - 需把 `worktree-first` 的 `PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate` 明确写入最终必过命令；
    - 需确保旧 `TilePass / KernelSplitPass` 删除后，`spec / registry / pytest / gen_kernel` 残留消费者在正文中被点名并清理。
