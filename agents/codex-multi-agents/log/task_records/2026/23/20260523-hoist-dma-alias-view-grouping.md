# T-20260523-f504c795 hoist-dma-alias-view-grouping

## 下发前复核

- 时间：2026-05-23
- 角色：大闸蟹
- 结论：通过，可创建 worktree 并分发唯一计划级 execute。
- 计划书：`ARCHITECTURE/plan/hoist_dma_alias_view_grouping_green_plan.md`
- 依赖：`T-20260523-f95877f2 / kernel-pattern-generate` 已 merge/DONE，并合入 latest `origin/main=733538704f3e66a46d89eee2308fb1d44919e18c`。

### 最新同步现场

- `HEAD=733538704f3e66a46d89eee2308fb1d44919e18c`
- `origin/main=733538704f3e66a46d89eee2308fb1d44919e18c`
- `merge-base=733538704f3e66a46d89eee2308fb1d44919e18c`
- `ahead/behind=0/0`

### expectation 合同资产

- `expectation/pass/hoist_dma_alias_ops/__main__.py`
  - sha256：`6d67110fa6acdc438665fa7ff77d2779aa32958c6f5ba635a2ec5c7618e85b7f`
- `expectation/pass/hoist_dma_alias_ops/reshape.py`
  - sha256：`8c002576132b8e5df8ed6fce1bb504aa2d8ea9ef2bc605b3942b667cc77b5ed4`
- `expectation/pass/hoist_dma_alias_ops/view.py`
  - sha256：`e2af51ba1c70d8ad82a32efafdc00768bfe605cb84078989985035fde29d2aa3`

复核结果：三项 hash 与计划 manifest 一致；未修改 expectation。

### expectation 基线

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.hoist_dma_alias_ops.reshape`
  - 结果：exit=0
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.hoist_dma_alias_ops.view`
  - 结果：exit=1
  - 分类：与计划一致，仍为 2 个正例红、1 个反例绿；红点来自尚未实现 `reshape + 低维 view/deslice`，不是解析或 verifier 错误。

### 真实 demo 与 dump marker

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_static_tile_static.py`
  - 结果：exit=0
  - stdout 证据：`inputs_static_tile_static_absent_bias` 与 `inputs_static_tile_static_present_bias` 均完成数值检查。
  - dump marker：`kernel/dump/conv2d/inputs_static_tile_static_present_bias/conv2d_inputs_static_tile_static_kernel/{08,16,17}-hoist-dma-alias-ops.mlir`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_dynamic_tile_dynamic.py`
  - 结果：exit=0
  - stdout 证据：`inputs_dynamic_tile_dynamic/absent_bias` 与 `inputs_dynamic_tile_dynamic/present_bias` 均完成数值检查。
  - dump marker：`kernel/dump/conv2d/inputs_dynamic_tile_dynamic/{08,16,17}-hoist-dma-alias-ops.mlir`

复核结果：静态 present-bias 与动态 case 均可按 `hoist-dma-alias-ops` pass marker 定位；两处 dump 均存在 `dma.view + dma.deslice` 片段，计划不依赖固定 pass 编号。

### 裁定

- 前置依赖已满足。
- 计划正文、expectation hash、pipeline/dump marker 与真实 demo 验收点一致。
- 当前无下发阻断。
- 管理员可创建 worktree 并分发唯一计划级 execute；若创建 worktree 前 `origin/main` 再变化，需按计划重新核对 latest main、hash、dump marker 与 demo 验收点。

## execute 记录：金铲铲大作战

- 时间：2026-05-23
- 任务类型：计划级 execute
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260523-hoist-dma-alias-view-grouping`
- latest main 对齐：
  - `HEAD=733538704f3e66a46d89eee2308fb1d44919e18c`
  - `origin/main=733538704f3e66a46d89eee2308fb1d44919e18c`
  - `merge-base=733538704f3e66a46d89eee2308fb1d44919e18c`

### 执行前阅读

- 已重新读取个人提示词：`agents/codex-multi-agents/agents/金铲铲大作战/金铲铲大作战.prompt.md`。
- 已重新读取根规则：`AGENTS.md`。
- 已读取相关标准：
  - `agents/standard/协作执行通用规则.md`
  - `agents/standard/任务记录约定.md`
  - `agents/standard/实现文件规范.md`
  - `agents/standard/测试文件约定.md`
  - `agents/standard/expectation任务规则.md`
- 已读取计划正文：`/home/lfr/kernelcode_generate/ARCHITECTURE/plan/hoist_dma_alias_view_grouping_green_plan.md`。
- 已确认本 worktree 内任务记录已包含下发前复核；后续 execute 记录写入当前 worktree 任务记录。

### 改动清单

- `kernel_gen/passes/hoist_dma_alias_ops.py`
  - 保持公开 API 不变：`HoistDmaAliasOpsPass(fold=True)` 与 `apply(ctx, module)` 未改签名。
  - 新增当前文件内私有 `DmaViewOp` pattern 与 helper，实现紧邻 `dma.view + dma.deslice` 连续后缀维度分组。
  - source / target contiguous、view/deslice 唯一紧邻、result 无后续 use、offset/size/stride exact proof 不满足时均保持 no-op。
  - 动态乘积只用当前 block 中已支配的 `SymbolValueType` 或当前文件内新建 `symbol.mul`，不依赖 SSA/name_hint/runtime_dim 拼表达。
  - 事务式 rewrite：新 op 插入后运行 `module.verify()`；失败时撤销新增 op 并恢复原 `view/deslice`，成功时通知 rewriter 移除旧 op。
- `spec/pass/hoist_dma_alias_ops.md`
  - 同步新增 `dma.view + dma.deslice` 连续后缀维度分组合同、no-op 边界与测试矩阵。
- `test/passes/test_hoist_dma_alias_ops.py`
  - 新增只走公开 `run_ircheck_text(...)` / pass name 的公开 pytest：静态正例、动态正例、非连续内层 no-op、非紧邻 no-op、多消费者 no-op。
- `kernel_gen/tools/ircheck.py`
  - 修复公开 `run_ircheck_text(...)` 可观察 matcher 问题：裸 `[[NAME:.*]]` 捕获改为非贪婪，避免 generic op operand list 后的 type 文本被误吞。
  - 该改动不新增公开 API、不改 CLI 参数或稳定错误前缀；用于让主仓 `expectation.pass.hoist_dma_alias_ops.view` 中现有 generic op CHECK 可按预期匹配。
- `test/tools/test_ircheck_matcher.py`
  - 补公开 matcher 回归，证明 generic op 两行连续 CHECK 中复用 shape operand 捕获不再被后续 type 文本污染。

### 自检

- 接口：`HoistDmaAliasOpsPass` 公开类、`apply(ctx, module)`、registry pass name 与 option 行为未变化。
- 边界：只匹配同 block、紧邻、唯一 deslice 消费者；view result 多消费者、非紧邻、非连续内层、rank 小于 3、缺少支配 shape operand、非 contiguous memory 均 no-op。
- 异常：view grouping rewrite 后 `module.verify()` 失败会恢复原 IR；reshape-through-fill 原有 verifier rollback 不回退。
- 兼容性：不新增 pass option、pattern getter 或 package root re-export；不改变 npu-demo pipeline 顺序。
- 实现遗漏：动态正例已覆盖 `N*K`、`TN*K`、`N0*K`；静态正例覆盖 `[2,3,4] -> [2,12]`；no-op 覆盖非连续/非紧邻/多消费者。
- 冗余：新增 helper 均在当前文件内服务当前 spec API；未新增跨文件私有 helper 调用。
- 注释准确性：更新实现文件文件级说明；新增/修改函数均包含 `功能说明` 与 `使用示例`。
- 复用：沿用 xDSL `RewritePattern` / `PatternRewriteWalker`，未写手工整段 ad hoc 遍历搬 op。
- 输入/输出校验：通过 `NnMemoryType`、`SymbolExprAttr`、`SymbolValueType` 结构化比较，不使用 dump 文本、SSA name 或 name_hint。
- 并发/资源/性能：pass 仅在局部紧邻 pattern 上改写；不引入全局缓存或共享可变状态。
- 测试有效性：pytest 与主仓 expectation 均从公开 pass / ircheck / registry 入口验证行为，未直连实现私有 helper。

### Diff 反推自测

- `kernel_gen/passes/hoist_dma_alias_ops.py`、`spec/pass/hoist_dma_alias_ops.md`、`test/passes/test_hoist_dma_alias_ops.py`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/passes/test_hoist_dma_alias_ops.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py test/tools/test_ircheck_matcher.py`
  - 结果：`94 passed, 1 warning`
- `kernel_gen/tools/ircheck.py`、`test/tools/test_ircheck_matcher.py`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/tools/test_ircheck_runner.py`
  - 结果：`52 passed, 1 warning`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/tools/test_ircheck_matcher.py`
  - 结果：已包含在上方计划 pytest，matcher 子集通过。
- `py_compile`
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/hoist_dma_alias_ops.py kernel_gen/tools/ircheck.py test/passes/test_hoist_dma_alias_ops.py test/tools/test_ircheck_matcher.py`
  - 结果：exit=0

### 合同验收

- 主仓只读 expectation 真源 hash：
  - `/home/lfr/kernelcode_generate/expectation/pass/hoist_dma_alias_ops/__main__.py`
    - `6d67110fa6acdc438665fa7ff77d2779aa32958c6f5ba635a2ec5c7618e85b7f`
  - `/home/lfr/kernelcode_generate/expectation/pass/hoist_dma_alias_ops/reshape.py`
    - `8c002576132b8e5df8ed6fce1bb504aa2d8ea9ef2bc605b3942b667cc77b5ed4`
  - `/home/lfr/kernelcode_generate/expectation/pass/hoist_dma_alias_ops/view.py`
    - `e2af51ba1c70d8ad82a32efafdc00768bfe605cb84078989985035fde29d2aa3`
- 主仓只读 expectation：
  - `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260523-hoist-dma-alias-view-grouping PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260523-hoist-dma-alias-view-grouping:/home/lfr/kernelcode_generate python3 -m expectation.pass.hoist_dma_alias_ops`
  - 结果：exit=0
  - 说明：`reshape` 正例通过；`view` 的静态/动态正例红转绿，动态非连续反例保持绿。
- import proof：
  - `expectation.pass.hoist_dma_alias_ops.reshape -> /home/lfr/kernelcode_generate/expectation/pass/hoist_dma_alias_ops/reshape.py`
  - `expectation.pass.hoist_dma_alias_ops.view -> /home/lfr/kernelcode_generate/expectation/pass/hoist_dma_alias_ops/view.py`
  - `expectation.utils.case_runner -> /home/lfr/kernelcode_generate/expectation/utils/case_runner.py`
  - `kernel_gen.passes.hoist_dma_alias_ops -> /home/lfr/kernelcode_generate/wt-20260523-hoist-dma-alias-view-grouping/kernel_gen/passes/hoist_dma_alias_ops.py`

### demo gate

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_static_tile_static.py`
  - 结果：exit=0
  - 摘要：`inputs_static_tile_static_absent_bias` 与 `inputs_static_tile_static_present_bias` 均完成数值检查，`max_abs_diff=4.1961669921875e-05`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_dynamic_tile_dynamic.py`
  - 结果：exit=0
  - 摘要：`inputs_dynamic_tile_dynamic/absent_bias` 与 `inputs_dynamic_tile_dynamic/present_bias` 均完成数值检查，`max_abs_diff=4.57763671875e-05`。
- dump 核对：
  - 动态 dump 中存在 `kernel/dump/conv2d/inputs_dynamic_tile_dynamic/08-hoist-dma-alias-ops.mlir` 与 `17-hoist-dma-alias-ops.mlir`。
  - dump 中可见本轮低维分组形态，例如 `dma.reshape` 后接低维 `dma.view` / `dma.deslice`。
  - 静态 demo 当前 stdout 数值 gate 通过；本次执行未发现计划相关阻断。

### 静态扫描与敏感目录

- `git diff --check`
  - 结果：exit=0
- 敏感目录空 diff：
  - `git diff --name-only -- expectation .skills agents/standard`
  - `git diff --cached --name-only -- expectation .skills agents/standard`
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`
  - 结果：三条均无输出。
- 私有 API / ctx 能力探测 / 嵌套函数扫描：
  - `rg -n "hasattr\\(|getattr\\(|callable\\(getattr|from .* import .*_[A-Za-z]|\\._[A-Za-z]" kernel_gen/passes/hoist_dma_alias_ops.py kernel_gen/tools/ircheck.py test/passes/test_hoist_dma_alias_ops.py test/tools/test_ircheck_matcher.py spec/pass/hoist_dma_alias_ops.md || true`
  - 结果：未发现本轮 `hoist_dma_alias_ops.py` 跨文件私有 API、ctx 能力探测或 name_hint 依赖；`kernel_gen/tools/ircheck.py` 仍有既有 `build_default_context as _build_default_context_base` 私有别名导入，非本轮新增，已由 ircheck 既有公开入口测试覆盖。
  - AST 嵌套函数扫描结果：无输出。

### 候选 diff

- `git diff --name-only`
  - `kernel_gen/passes/hoist_dma_alias_ops.py`
  - `kernel_gen/tools/ircheck.py`
  - `spec/pass/hoist_dma_alias_ops.md`
  - `test/passes/test_hoist_dma_alias_ops.py`
  - `test/tools/test_ircheck_matcher.py`
- `git diff --shortstat`
  - `5 files changed, 1012 insertions(+), 10 deletions(-)`
- `expectation/`、`.skills/`、`agents/standard/**` 无候选 diff。

### 结论

- 计划内实现/spec/pytest/主仓只读 expectation/demo gate 已闭合。
- 未新增公开 pass API、pass option、pattern getter 或 package re-export。
- 未修改、复制、新建或同步 `expectation/`、`.skills/`、`agents/standard/**`。
- 可按流程流转 review。

## 2026-05-23 12:37 CST 提莫炖蘑菇 review

### review 前置同步

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260523-hoist-dma-alias-view-grouping`
- 已执行 `git fetch origin`。
- 当前基线：
  - `HEAD=733538704f3e66a46d89eee2308fb1d44919e18c`
  - `origin/main=733538704f3e66a46d89eee2308fb1d44919e18c`
  - `merge-base=733538704f3e66a46d89eee2308fb1d44919e18c`
- 同步结论：待审 worktree 已在最新 `origin/main` 基线上，无需 merge/rebase；未覆盖任务 diff。
- 计划书读取：目标 worktree 不含计划文件，按下发路径从主仓只读读取 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/hoist_dma_alias_view_grouping_green_plan.md`。
- 候选 diff：
  - `kernel_gen/passes/hoist_dma_alias_ops.py`
  - `kernel_gen/tools/ircheck.py`
  - `spec/pass/hoist_dma_alias_ops.md`
  - `test/passes/test_hoist_dma_alias_ops.py`
  - `test/tools/test_ircheck_matcher.py`
- 敏感目录：
  - `git diff --name-only -- expectation .skills agents/standard` 无输出。
  - `git diff --cached --name-only -- expectation .skills agents/standard` 无输出。
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard` 无输出。

### 真实审查

- `kernel_gen/passes/hoist_dma_alias_ops.py`
  - 公开 API 未新增，`HoistDmaAliasOpsPass(fold=True)` 与 `apply(ctx, module)` 未改签名。
  - 新增逻辑集中在当前文件内私有 view/deslice candidate、suffix 证明与事务式 rewrite helper，未看到跨文件私有 helper 直连。
  - 候选筛选覆盖紧邻、唯一 view result consumer、deslice result 无后续 use、source/target contiguous、shape/size exact 证明等关键条件。
  - 阻断风险：计划要求 `非 byte-pool typed view`；当前 `_view_grouping_candidate` 仅检查 `NnMemoryType` 与 contiguous，`rg -n "byte|i8|byte_pool"` 对实现/spec/pytest 无命中。若 byte-pool typed view 可落到相同 `NnMemoryType` 连续布局，该实现缺少显式 no-op guard 或公开测试证明。
- `spec/pass/hoist_dma_alias_ops.md`
  - 已补 view/deslice 连续维度分组合同和 TC-011 到 TC-015。
  - 阻断风险：计划 S3 明确要求的 view/deslice no-op/rollback 测试项未全部进入 spec 测试矩阵；当前矩阵只覆盖静态正例、动态正例、非连续内层、非紧邻、view 多消费者。
- `test/passes/test_hoist_dma_alias_ops.py`
  - 新增公开 ircheck 入口测试，未直连实现私有 helper。
  - 已覆盖静态正例、动态正例、非完整 K、非紧邻、view 多消费者。
  - 阻断风险：计划 S3 的必测项未补齐，见下方“可改进点 / 阻断项”。
- `kernel_gen/tools/ircheck.py` 与 `test/tools/test_ircheck_matcher.py`
  - 新增 `[[NAME:.*]]` 非贪婪捕获回归，属于本轮 expectation generic op 捕获所需支撑；未新增公开 API。

### Diff 反推审查

- 本轮复跑：
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/passes/test_hoist_dma_alias_ops.py test/tools/test_ircheck_matcher.py`
  - 结果：`28 passed, 1 warning`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/passes/test_hoist_dma_alias_ops.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py test/tools/test_ircheck_matcher.py`
  - 结果：`94 passed, 1 warning`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/tools/test_ircheck_runner.py`
  - 结果：`52 passed, 1 warning`
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/hoist_dma_alias_ops.py kernel_gen/tools/ircheck.py test/passes/test_hoist_dma_alias_ops.py test/tools/test_ircheck_matcher.py`
  - 结果：exit=0
  - `git diff --check`
  - 结果：exit=0
- 主仓只读 expectation：
  - `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260523-hoist-dma-alias-view-grouping PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260523-hoist-dma-alias-view-grouping:/home/lfr/kernelcode_generate python3 -m expectation.pass.hoist_dma_alias_ops`
  - 结果：exit=0
- demo gate：
  - `PYTHONPATH=. python3 kernel/conv2d/inputs_static_tile_static.py`
  - 结果：exit=0
  - `PYTHONPATH=. python3 kernel/conv2d/inputs_dynamic_tile_dynamic.py`
  - 结果：exit=0
- 说明：运行证据通过，但通过命令没有覆盖计划列为硬门禁的全部 view/deslice no-op 与 rollback 边界，因此不能据此放行。

### 可改进点 / 阻断项

1. `test/passes/test_hoist_dma_alias_ops.py` 尚未覆盖计划 S3 全部 view/deslice 必测边界。
   - 依据：计划 S3 要求补 `stride != 1 no-op`、`source/target 非连续 no-op`、`cross block/region no-op`、`deslice result 有后续非 terminator use no-op`、`代数等价但非结构化 SymbolExprAttr exact equality no-op`、`内层 offset 非 0 no-op`、`verifier 拒绝候选时无部分改写` 等。
   - 当前测试只看到静态正例、动态正例、`TK != K`、非紧邻、view 多消费者。
   - 影响：rewrite 的安全边界主要依赖 no-op 证明；缺少公开 pytest 会让错误外提、错误合并或事务回滚缺陷假绿。
   - 需修改：补齐上述公开 pytest；通过公开 pass / ircheck / op 构造入口验证，不直连私有 helper；对 no-op 用 module 文本或结构保持不变断言。
2. `spec/pass/hoist_dma_alias_ops.md` 测试矩阵未与计划 S3 必测项对齐。
   - 依据：spec 当前 TC-011 到 TC-015 只覆盖 view/deslice 五类场景；计划要求更多 no-op/rollback 边界进入审查矩阵。
   - 影响：后续 review/终验无法机械核对每个安全边界是否由 spec 定义并由 pytest 承接。
   - 需修改：把缺失边界补入 spec 测试矩阵，并把每个新增 pytest 测试名映射到对应 TC。
3. byte-pool typed view 边界未被实现或测试显式证明。
   - 依据：计划候选匹配写明 `非 byte-pool typed view`；当前实现候选筛选只见 `NnMemoryType` 与 contiguous 判断，`byte/i8/byte_pool` 相关扫描无命中。
   - 影响：如果 byte-pool view 能满足 contiguous layout，当前 rewrite 可能越过计划禁止面；如果类型系统已保证不可能进入，也缺少公开 no-op/不可构造测试证明。
   - 需修改：补显式 guard 或补公开测试/记录证明该形态无法命中；若补 guard，同步 spec 与 pytest。

### review 结论

- 结论：不通过，需退回 execute。
- 当前运行结果通过项可以保留为证据，但不足以替代计划 S3 的完整公开 pytest 和 spec 矩阵。
- 本次 review 未修改 `expectation/`、`.skills/`、`agents/standard/**`，只追加任务记录。

## 2026-05-23 13:04 CST execute 返工：金铲铲大作战

### 执行前阅读

- 已重新读取个人提示词：`agents/codex-multi-agents/agents/金铲铲大作战/金铲铲大作战.prompt.md`。
- 已重新读取根规则：`AGENTS.md`。
- 已重新读取相关标准：
  - `agents/standard/协作执行通用规则.md`
  - `agents/standard/任务记录约定.md`
  - `agents/standard/实现文件规范.md`
  - `agents/standard/测试文件约定.md`
  - `agents/standard/expectation任务规则.md`
- 已读取主仓共享计划：`/home/lfr/kernelcode_generate/ARCHITECTURE/plan/hoist_dma_alias_view_grouping_green_plan.md`。
- 已读取本任务记录中 `2026-05-23 12:37 CST 提莫炖蘑菇 review` 退回项。
- 当前执行目录：`/home/lfr/kernelcode_generate/wt-20260523-hoist-dma-alias-view-grouping`。
- 当前同步现场：
  - `HEAD=733538704f3e66a46d89eee2308fb1d44919e18c`
  - `origin/main=733538704f3e66a46d89eee2308fb1d44919e18c`
  - `merge-base=733538704f3e66a46d89eee2308fb1d44919e18c`

### 返工目标

- 收口 review 最小阻断：补齐 view/deslice 分组计划 S3 的公开 pytest 与 spec 矩阵。
- 必须覆盖：`stride != 1`、source/target 非连续、cross block/region、deslice result 后续非 terminator use、exact equality 负例、内层 offset 非 0、verifier rollback、byte-pool typed view guard/证明。
- 继续保持：不修改/复制/新建 `expectation/`、`.skills/`、`agents/standard/**`，不新增公开 pass API、option、pattern getter 或 package re-export。

### 改动

- `kernel_gen/passes/hoist_dma_alias_ops.py`
  - 新增当前文件内私有 `_is_i8_byte_pool_memory_type(...)`，通过公开 `NnMemoryType` 字段与 xDSL `IntegerType` 判断一维 i8 byte pool。
  - `_view_grouping_candidate(...)` 对 byte-pool typed view 显式 no-op，避免该计划外形态落入 view/deslice 分组 rewrite。
  - `_rewrite_view_deslice_grouping(...)` 在 verifier rollback 路径中对临时插入的新 op 调用 `rewriter.handle_operation_removal(...)`，防止 xDSL walker 继续处理已 detach 的临时 op。
- `test/passes/test_hoist_dma_alias_ops.py`
  - 补齐 S3 公开 pytest：`TC-HOIST-DMA-ALIAS-014` 到 `TC-HOIST-DMA-ALIAS-024`。
  - 新增测试均只走公开 `run_ircheck_text(...)` 或公开 `HoistDmaAliasOpsPass.apply(...)`，未直连实现私有 helper。
  - 新增/补齐测试名：
    - `test_hoist_dma_alias_ops_keeps_non_unit_view_stride_noop`
    - `test_hoist_dma_alias_ops_keeps_non_contiguous_source_layout_noop`
    - `test_hoist_dma_alias_ops_keeps_non_contiguous_target_layout_noop`
    - `test_hoist_dma_alias_ops_keeps_multiple_view_consumers_noop`
    - `test_hoist_dma_alias_ops_keeps_view_deslice_cross_region_noop`
    - `test_hoist_dma_alias_ops_keeps_non_adjacent_view_deslice_noop`
    - `test_hoist_dma_alias_ops_keeps_deslice_result_later_use_noop`
    - `test_hoist_dma_alias_ops_keeps_non_exact_symbol_expr_equality_noop`
    - `test_hoist_dma_alias_ops_keeps_inner_offset_nonzero_noop`
    - `test_hoist_dma_alias_ops_rolls_back_view_grouping_when_verifier_rejects`
    - `test_hoist_dma_alias_ops_keeps_byte_pool_typed_view_noop`
- `spec/pass/hoist_dma_alias_ops.md`
  - 将非目标改为“不做任意 `dma.view -> dma.reshape` combine；只做连续 suffix `view + single deslice` 分组 rewrite”，避免和本轮受限目标冲突。
  - 测试矩阵从 `TC-HOIST-DMA-ALIAS-011` 到 `TC-HOIST-DMA-ALIAS-026` 明确列出 S3 正反例、rollback、byte-pool 与 registry/pipeline 映射。

### 最小功能闭环

- `stride != 1`：`test_hoist_dma_alias_ops_keeps_non_unit_view_stride_noop` 通过动态 `S` stride 证明 pass 不把非 unit logical stride 分组。
- source 非连续：`test_hoist_dma_alias_ops_keeps_non_contiguous_source_layout_noop` 使用非行主序 source stride，断言 no-op。
- target 非连续：`test_hoist_dma_alias_ops_keeps_non_contiguous_target_layout_noop` 使用非行主序 target stride，断言 no-op。
- cross region：`test_hoist_dma_alias_ops_keeps_view_deslice_cross_region_noop` 用外层 view 与 `scf.if` region 内 deslice，断言 module 文本不变。
- deslice result 后续 use：`test_hoist_dma_alias_ops_keeps_deslice_result_later_use_noop` 用后续 `dma.reshape` 消费 deslice result，断言 module 文本不变。
- exact equality 负例：`test_hoist_dma_alias_ops_keeps_non_exact_symbol_expr_equality_noop` 使用 `K` 与 `K_ALIAS`，断言不通过名字或文本猜测合并。
- 内层 offset 非 0：`test_hoist_dma_alias_ops_keeps_inner_offset_nonzero_noop` 使用动态 `K0` inner offset，断言 no-op。
- verifier rollback：`test_hoist_dma_alias_ops_rolls_back_view_grouping_when_verifier_rejects` 通过公开 pass 入口模拟 verifier 拒绝，断言 module 文本完全恢复。
- byte-pool typed view：`test_hoist_dma_alias_ops_keeps_byte_pool_typed_view_noop` 使用一维 i8 backing memory 到三维 f32 typed view，断言不生成 reshape。

### Diff 反推自测

- `kernel_gen/passes/hoist_dma_alias_ops.py` / `test/passes/test_hoist_dma_alias_ops.py`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/passes/test_hoist_dma_alias_ops.py -q`
  - 结果：`25 passed, 1 warning`，exit=0。
- `kernel_gen/passes/hoist_dma_alias_ops.py` / `spec/pass/hoist_dma_alias_ops.md` / `test/passes/test_hoist_dma_alias_ops.py` / `test/tools/test_ircheck_matcher.py`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/passes/test_hoist_dma_alias_ops.py test/tools/test_ircheck_matcher.py`
  - 结果：`37 passed, 1 warning`，exit=0。
- 计划 pytest：
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/passes/test_hoist_dma_alias_ops.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py test/tools/test_ircheck_matcher.py`
  - 结果：`103 passed, 1 warning`，exit=0。
- ircheck matcher / runner 回归：
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/tools/test_ircheck_runner.py`
  - 结果：`52 passed, 1 warning`，exit=0。
- py_compile：
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/hoist_dma_alias_ops.py kernel_gen/tools/ircheck.py test/passes/test_hoist_dma_alias_ops.py test/tools/test_ircheck_matcher.py`
  - 结果：exit=0。

### 合同验收

- 主仓只读 expectation hash：
  - `/home/lfr/kernelcode_generate/expectation/pass/hoist_dma_alias_ops/__main__.py`
    - `6d67110fa6acdc438665fa7ff77d2779aa32958c6f5ba635a2ec5c7618e85b7f`
  - `/home/lfr/kernelcode_generate/expectation/pass/hoist_dma_alias_ops/reshape.py`
    - `8c002576132b8e5df8ed6fce1bb504aa2d8ea9ef2bc605b3942b667cc77b5ed4`
  - `/home/lfr/kernelcode_generate/expectation/pass/hoist_dma_alias_ops/view.py`
    - `e2af51ba1c70d8ad82a32efafdc00768bfe605cb84078989985035fde29d2aa3`
- 主仓只读 expectation：
  - `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260523-hoist-dma-alias-view-grouping PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260523-hoist-dma-alias-view-grouping:/home/lfr/kernelcode_generate python3 -m expectation.pass.hoist_dma_alias_ops`
  - 结果：exit=0。
- import proof：
  - `expectation.pass.hoist_dma_alias_ops.reshape -> /home/lfr/kernelcode_generate/expectation/pass/hoist_dma_alias_ops/reshape.py`
  - `expectation.pass.hoist_dma_alias_ops.view -> /home/lfr/kernelcode_generate/expectation/pass/hoist_dma_alias_ops/view.py`
  - `expectation.utils.case_runner -> /home/lfr/kernelcode_generate/expectation/utils/case_runner.py`
  - `kernel_gen.passes.hoist_dma_alias_ops -> /home/lfr/kernelcode_generate/wt-20260523-hoist-dma-alias-view-grouping/kernel_gen/passes/hoist_dma_alias_ops.py`

### demo gate

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_static_tile_static.py`
  - 结果：exit=0。
  - 摘要：`inputs_static_tile_static_absent_bias` 与 `inputs_static_tile_static_present_bias` 均完成数值检查，`max_abs_diff=4.1961669921875e-05`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_dynamic_tile_dynamic.py`
  - 结果：exit=0。
  - 摘要：`inputs_dynamic_tile_dynamic/absent_bias` 与 `inputs_dynamic_tile_dynamic/present_bias` 均完成数值检查，`max_abs_diff=4.57763671875e-05`。

### 静态扫描与敏感目录

- `git diff --check`
  - 结果：exit=0。
- 敏感目录门禁：
  - `git diff --name-only -- expectation .skills agents/standard`
  - `git diff --cached --name-only -- expectation .skills agents/standard`
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`
  - 结果：三条均无输出。
- 私有 API / ctx 能力探测 / name_hint 扫描：
  - `rg -n "hasattr\\(|getattr\\(|callable\\(getattr|from .* import .*_[A-Za-z]|\\._[A-Za-z]|name_hint" kernel_gen/passes/hoist_dma_alias_ops.py kernel_gen/tools/ircheck.py test/passes/test_hoist_dma_alias_ops.py test/tools/test_ircheck_matcher.py spec/pass/hoist_dma_alias_ops.md || true`
  - 结果：未发现 `hoist_dma_alias_ops.py` 跨文件私有 API、ctx 能力探测或 name_hint 依赖；`kernel_gen/tools/ircheck.py` 仍有既有 `build_default_context as _build_default_context_base` 私有别名导入，非本轮新增。
- 嵌套函数 AST 扫描：
  - 覆盖 `kernel_gen/passes/hoist_dma_alias_ops.py`、`kernel_gen/tools/ircheck.py`、`test/passes/test_hoist_dma_alias_ops.py`、`test/tools/test_ircheck_matcher.py`
  - 结果：无输出。

### 自检

- 接口：未新增公开 API，未改 `HoistDmaAliasOpsPass(fold=True)` / `apply(ctx, module)` 签名。
- 边界：已补齐 review 点名的 stride、source/target contiguous、cross region、deslice result use、exact equality、inner offset、byte-pool 与 rollback 边界。
- 异常：view/deslice rollback 初次新增测试暴露 walker worklist 仍可能处理已 detach 临时 op；已通过 `handle_operation_removal(...)` 修复并由 `test_hoist_dma_alias_ops_rolls_back_view_grouping_when_verifier_rejects` 锁定。
- 兼容：不新增 pass option、pattern getter、package root re-export；不改 npu-demo pipeline 顺序。
- 实现遗漏：S3 必测项均有公开 pytest 映射；spec 测试矩阵已同步到 `TC-HOIST-DMA-ALIAS-026`。
- 冗余与复用：byte-pool guard 为当前文件内 helper，不调用 dma dialect 私有 `_is_i8_byte_pool`；其余新增测试 helper 仅服务公开测试输入构造。
- 注释：新增/修改函数均有 `功能说明 / 使用示例`。
- 输入/输出校验：继续只依赖结构化 `SymbolValueType` / `SymbolExprAttr`，不使用 SSA name、name_hint、dump 文本或 runtime_dim 拼表达。
- 资源/并发/性能：改动保持局部 pattern rewrite，不引入全局缓存或共享状态。
- 测试有效性：新增测试均可在对应 guard/rollback 被破坏时失败，且不以 expectation 替代 Diff 反推 pytest。

### 候选 diff

- `kernel_gen/passes/hoist_dma_alias_ops.py`
- `kernel_gen/tools/ircheck.py`
- `spec/pass/hoist_dma_alias_ops.md`
- `test/passes/test_hoist_dma_alias_ops.py`
- `test/tools/test_ircheck_matcher.py`
- `agents/codex-multi-agents/log/task_records/2026/23/20260523-hoist-dma-alias-view-grouping.md`

### 结论

- review 退回的 S3 公开 pytest 与 spec 矩阵缺口已补齐。
- 主仓只读 `expectation.pass.hoist_dma_alias_ops`、计划 pytest、ircheck runner、py_compile、demo gate、`git diff --check`、敏感目录空 diff和静态扫描均通过。
- 未修改/复制/新建 `expectation/`、`.skills/`、`agents/standard/**`。
- 可按流程重新流转 review。

## 2026-05-23 13:14 CST 不要啊教练 review 复审

### review 前置同步

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260523-hoist-dma-alias-view-grouping`
- 已重新读取：`agents/codex-multi-agents/agents/不要啊教练/不要啊教练.prompt.md`、根 `AGENTS.md`、`agents/standard/审查规范.md`、`agents/standard/任务记录约定.md`。
- 已执行 `git fetch origin`。
- 当前基线：
  - `HEAD=733538704f3e66a46d89eee2308fb1d44919e18c`
  - `origin/main=733538704f3e66a46d89eee2308fb1d44919e18c`
  - `merge-base=733538704f3e66a46d89eee2308fb1d44919e18c`
  - `ahead/behind=0/0`
- 同步结论：待审 worktree 与最新 `origin/main` 同基线，未执行 merge/rebase，不存在覆盖任务 diff 或本地改动的风险。
- TODO 核对：`T-20260523-f504c795` 当前为 `review / 不要啊教练 / 进行中`，记录文件为本文件。
- 计划书读取：本轮以主仓共享计划 `ARCHITECTURE/plan/hoist_dma_alias_view_grouping_green_plan.md` 为合同真源。

### 被审 diff

- `kernel_gen/passes/hoist_dma_alias_ops.py`
- `kernel_gen/tools/ircheck.py`
- `spec/pass/hoist_dma_alias_ops.md`
- `test/passes/test_hoist_dma_alias_ops.py`
- `test/tools/test_ircheck_matcher.py`
- `agents/codex-multi-agents/log/task_records/2026/23/20260523-hoist-dma-alias-view-grouping.md`

### 真实审查

- `kernel_gen/passes/hoist_dma_alias_ops.py`
  - 公开 API 未新增，仍为 `HoistDmaAliasOpsPass(fold: bool = True)` 与 `apply(ctx: Context, module: ModuleOp) -> None`。
  - 文件级 API 列表紧跟功能说明，未新增公开 pattern getter、pass option 或 package root re-export。
  - view/deslice 分组实现使用当前文件内私有候选、suffix 证明、symbol product、rollback helper；未发现本轮新增跨文件私有 helper 调用。
  - 已补 `_is_i8_byte_pool_memory_type(...)`，通过公开 `NnMemoryType` 与 xDSL `IntegerType` 判断一维 i8 byte-pool source，并在 `_view_grouping_candidate(...)` 显式 no-op。
  - `_candidate_deslice(...)` 继续约束同 block 紧邻、唯一 view consumer、deslice result 无后续 use；cross-region 和 result-use 风险由公开 pytest 覆盖。
  - `_rewrite_view_deslice_grouping(...)` 在 verifier 失败时 detach 新 op、通知 rewriter removal 并恢复原 view/deslice；公开 rollback 测试覆盖该路径。
- `spec/pass/hoist_dma_alias_ops.md`
  - 已将 `dma.view -> dma.reshape combine` 从绝对非目标改为仅允许连续 suffix `view + single deslice` 分组 rewrite。
  - 测试矩阵已扩到 `TC-HOIST-DMA-ALIAS-026`，覆盖上轮退回的 stride、source/target 非 contiguous、cross-region、deslice result 后续 use、exact equality、inner offset、verifier rollback、byte-pool typed view 等边界。
- `test/passes/test_hoist_dma_alias_ops.py`
  - 新增测试只走公开 `run_ircheck_text(...)` 或公开 `HoistDmaAliasOpsPass.apply(...)`，未直连实现私有 helper。
  - S3 必测项均有对应公开 pytest 名称：`test_hoist_dma_alias_ops_keeps_non_unit_view_stride_noop`、`test_hoist_dma_alias_ops_keeps_non_contiguous_source_layout_noop`、`test_hoist_dma_alias_ops_keeps_non_contiguous_target_layout_noop`、`test_hoist_dma_alias_ops_keeps_view_deslice_cross_region_noop`、`test_hoist_dma_alias_ops_keeps_deslice_result_later_use_noop`、`test_hoist_dma_alias_ops_keeps_non_exact_symbol_expr_equality_noop`、`test_hoist_dma_alias_ops_keeps_inner_offset_nonzero_noop`、`test_hoist_dma_alias_ops_rolls_back_view_grouping_when_verifier_rejects`、`test_hoist_dma_alias_ops_keeps_byte_pool_typed_view_noop`。
  - no-op 测试通过 module 文本保持或 `CHECK-NOT: "dma.reshape"` 证明不会误改写；正例测试锁定低维 reshape/view/deslice 与动态 `symbol.mul`。
- `kernel_gen/tools/ircheck.py` / `test/tools/test_ircheck_matcher.py`
  - 本轮 matcher 支撑修复仍通过公开 `run_ircheck_text(...)` 可观察行为验证，不新增公开 API、不改 CLI 参数。
  - 静态扫描命中既有 `build_default_context as _build_default_context_base`，非本轮新增；本轮未扩大该私有别名依赖。

### Diff 反推审查

- 复跑命令：`PYTHONDONTWRITEBYTECODE=1 pytest -q test/passes/test_hoist_dma_alias_ops.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py test/tools/test_ircheck_matcher.py`
  - 结果：`103 passed, 1 warning`，exit=0。
  - 覆盖：hoist pass 正反例、registry、pipeline、ircheck matcher 本轮 diff。
- 复跑命令：`PYTHONDONTWRITEBYTECODE=1 pytest -q test/tools/test_ircheck_runner.py`
  - 结果：`52 passed, 1 warning`，exit=0。
  - 覆盖：`kernel_gen/tools/ircheck.py` matcher/runner 相关回归。
- 复跑命令：`PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/hoist_dma_alias_ops.py kernel_gen/tools/ircheck.py test/passes/test_hoist_dma_alias_ops.py test/tools/test_ircheck_matcher.py && git diff --check`
  - 结果：exit=0。
- 合同验收命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260523-hoist-dma-alias-view-grouping:/home/lfr/kernelcode_generate python3 -m expectation.pass.hoist_dma_alias_ops`
  - cwd：`/home/lfr/kernelcode_generate/wt-20260523-hoist-dma-alias-view-grouping`
  - 结果：exit=0。
  - 说明：主仓只读 expectation 作为合同验收资产，不计入 Diff 反推测试。
- demo gate：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_static_tile_static.py`
  - 结果：exit=0，stdout 含 absent/present bias 数值检查通过，`max_abs_diff=4.1961669921875e-05`。
- demo gate：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_dynamic_tile_dynamic.py`
  - 结果：exit=0，stdout 含 absent/present bias 数值检查通过，`max_abs_diff=4.57763671875e-05`。
- 敏感目录门禁：
  - `git diff --name-only -- expectation .skills agents/standard` 无输出。
  - `git diff --cached --name-only -- expectation .skills agents/standard` 无输出。
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard` 无输出。
- 静态扫描：
  - `rg -n "hasattr\(|getattr\(|callable\(getattr|from .* import .*_[A-Za-z]|\._[A-Za-z]|name_hint|\bobject\b" ... || true` 未发现本轮阻断命中；命中项为文档说明、公开导入或既有 ircheck 私有别名导入。
  - AST 嵌套函数扫描覆盖本轮 Python 文件，无输出。

### findings

- 无阻断项。
- 上轮 review 指出的 S3 公开 pytest/spec 矩阵、byte-pool guard、verifier rollback 缺口已由本轮返工收口，并由公开 pytest、主仓只读 expectation、demo gate 和敏感目录门禁复核通过。

### 自检

- 已读取实际 diff，而非只看执行摘要。
- 已按计划 S1-S5 核对 spec、实现、测试、合同验收、demo gate 与禁止修改面。
- 已核对公开 API 未新增、测试未直连实现私有 helper、实现未新增跨文件非公开 API 调用、无 ctx 能力探测、无非装饰器嵌套函数、未修改 `expectation/` / `.skills` / `agents/standard`。
- 已按实际 diff 复跑 pytest/py_compile/diff check，并单列 expectation 合同验收。
- 当前未发现可执行返工项；残余风险为后续架构复核/终验需继续核对真实 dump 形态和 merge 候选范围。

### 结论

- 结论：通过。
- 本任务为计划级任务，review 通过后应进入架构复核/终验；review 不直接 merge。

## 2026-05-23 14:24 CST 守护最好的爱莉希雅第二架构终验

### 终验前置同步

- 执行目录：`/home/lfr/kernelcode_generate/wt-20260523-hoist-dma-alias-view-grouping`
- 已重新读取：根 `AGENTS.md`、`agents/standard/计划书标准.md`、`agents/standard/任务记录约定.md`、`agents/codex-multi-agents/agents/守护最好的爱莉希雅/守护最好的爱莉希雅.prompt.md`。
- 计划书：worktree 内无 `ARCHITECTURE/plan/hoist_dma_alias_view_grouping_green_plan.md`，按前序记录使用主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/hoist_dma_alias_view_grouping_green_plan.md` 作为合同真源。
- 同步基线：
  - `HEAD=733538704f3e66a46d89eee2308fb1d44919e18c`
  - `origin/main=733538704f3e66a46d89eee2308fb1d44919e18c`
  - `merge-base=733538704f3e66a46d89eee2308fb1d44919e18c`
  - `ahead/behind=0/0`
- 候选 tracked diff：
  - `kernel_gen/passes/hoist_dma_alias_ops.py`
  - `kernel_gen/tools/ircheck.py`
  - `spec/pass/hoist_dma_alias_ops.md`
  - `test/passes/test_hoist_dma_alias_ops.py`
  - `test/tools/test_ircheck_matcher.py`
- 记录文件当前为 untracked：`agents/codex-multi-agents/log/task_records/2026/23/20260523-hoist-dma-alias-view-grouping.md`；merge 前必须与代码/spec/test 同批纳入，不得遗漏。

### 合同验收

- 命令：`PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260523-hoist-dma-alias-view-grouping PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260523-hoist-dma-alias-view-grouping:/home/lfr/kernelcode_generate python3 -m expectation.pass.hoist_dma_alias_ops`
  - 结果：exit=0。
  - 摘要：`reshape` 静态正例、`view` 静态/动态正例和动态不连续反例均通过。
- 导入边界：
  - `expectation.pass.hoist_dma_alias_ops.reshape -> /home/lfr/kernelcode_generate/expectation/pass/hoist_dma_alias_ops/reshape.py`
  - `expectation.pass.hoist_dma_alias_ops.view -> /home/lfr/kernelcode_generate/expectation/pass/hoist_dma_alias_ops/view.py`
  - `expectation.utils.case_runner -> /home/lfr/kernelcode_generate/expectation/utils/case_runner.py`
  - `kernel_gen.passes.hoist_dma_alias_ops -> /home/lfr/kernelcode_generate/wt-20260523-hoist-dma-alias-view-grouping/kernel_gen/passes/hoist_dma_alias_ops.py`

### 复跑验证

- 计划 pytest：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_hoist_dma_alias_ops.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py test/tools/test_ircheck_matcher.py`
  - 结果：`103 passed, 1 warning`，exit=0。
- ircheck runner 回归：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_ircheck_runner.py`
  - 结果：`52 passed, 1 warning`，exit=0。
- py_compile：`PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/hoist_dma_alias_ops.py kernel_gen/tools/ircheck.py test/passes/test_hoist_dma_alias_ops.py test/tools/test_ircheck_matcher.py`
  - 结果：exit=0。
- demo gate：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_static_tile_static.py`
    - 结果：exit=0。
    - 摘要：`inputs_static_tile_static_absent_bias` 与 `inputs_static_tile_static_present_bias` 均通过，`max_abs_diff=4.1961669921875e-05`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_dynamic_tile_dynamic.py`
    - 结果：exit=0。
    - 摘要：`inputs_dynamic_tile_dynamic/absent_bias` 与 `inputs_dynamic_tile_dynamic/present_bias` 均通过，`max_abs_diff=4.57763671875e-05`。
- dump marker 核对：
  - `find kernel/dump/conv2d -path '*hoist-dma-alias-ops.mlir'` 可定位 static absent/present 与 dynamic 的 `08/17-hoist-dma-alias-ops.mlir`。
  - static present 与 dynamic dump 中均存在 `dma.view` / `dma.deslice` 片段；低维分组正反例由公开 pytest 与主仓 expectation 锁定，不绑定固定 SSA 编号。
- 格式与敏感目录：
  - `git diff --check`：exit=0。
  - `git diff --name-only -- expectation .skills agents/standard`：无输出。
  - `git diff --cached --name-only -- expectation .skills agents/standard`：无输出。
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`：无输出。
- 静态边界扫描：
  - `rg -n "hasattr\(|getattr\(|callable\(getattr|from .* import .*_[A-Za-z]|\._[A-Za-z]|name_hint|\bobject\b" ...` 仅命中 spec 中禁止 `name_hint` 的说明、公开 import 示例和 `kernel_gen/tools/ircheck.py` 既有 `_build_default_context_base` 私有别名导入；未发现本轮阻断命中。
  - AST 嵌套函数扫描覆盖本轮 Python 文件，无输出。

### 自检

- 公开 API：未新增 pass、option、pattern getter、package root re-export 或稳定错误文本；仍扩展既有 `HoistDmaAliasOpsPass` 行为。
- 任务范围：候选 diff 位于计划指定模块与记录文件；未修改 `expectation/`、`.skills/`、`agents/standard/**`。
- 测试有效性：pytest 覆盖静态/动态正例、stride/source/target/layout/cross-region/result-use/exact-equality/inner-offset/byte-pool/verifier rollback 等边界；主仓 expectation 红转绿验证合同入口。
- 残余风险：任务记录当前未跟踪，merge 角色必须确认它与代码/spec/test 同批加入候选提交。

### 结论

- 第二架构终验结论：通过。
- 最小阻断项：无。
- 可进入 merge；merge 前必须把本记录文件纳入候选 diff，并继续保持 `expectation/`、`.skills/`、`agents/standard/**` 空 diff。

## 2026-05-23 14:22 CST 大闸蟹计划级架构复核 / 终验

### 最新同步现场

- 角色：大闸蟹
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260523-hoist-dma-alias-view-grouping`
- 计划书：`/home/lfr/kernelcode_generate/ARCHITECTURE/plan/hoist_dma_alias_view_grouping_green_plan.md`
- `HEAD=733538704f3e66a46d89eee2308fb1d44919e18c`
- `origin/main=733538704f3e66a46d89eee2308fb1d44919e18c`
- 主仓 `/home/lfr/kernelcode_generate` 也已同步到同一 `origin/main`。
- 候选 tracked diff：
  - `kernel_gen/passes/hoist_dma_alias_ops.py`
  - `kernel_gen/tools/ircheck.py`
  - `spec/pass/hoist_dma_alias_ops.md`
  - `test/passes/test_hoist_dma_alias_ops.py`
  - `test/tools/test_ircheck_matcher.py`
- 任务记录为本文件，需与候选 diff 同批进入 review/merge。

### 复核重点

- 已核对 review 退回项已闭合：S3 view/deslice no-op 边界、byte-pool guard、verifier rollback 与 spec 测试矩阵均已补入公开 pytest / spec。
- `HoistDmaAliasOpsPass(fold=True)`、`apply(ctx, module)`、pass name、registry option、package root re-export 均未新增公开 API。
- 实现仍限制在当前 pass 内部 helper；未发现本轮跨文件私有 helper 调用、ctx 能力探测、非装饰器嵌套函数或 `name_hint` 依赖。
- `kernel_gen/tools/ircheck.py` 的 matcher 修复由公开 `run_ircheck_text(...)` 测试覆盖；既有 `_build_default_context_base` 私有别名导入不是本轮新增。

### 验证命令

- `PYTHONDONTWRITEBYTECODE=1 pytest -q test/passes/test_hoist_dma_alias_ops.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py test/tools/test_ircheck_matcher.py`
  - 结果：`103 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 pytest -q test/tools/test_ircheck_runner.py`
  - 结果：`52 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260523-hoist-dma-alias-view-grouping PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260523-hoist-dma-alias-view-grouping:/home/lfr/kernelcode_generate python3 -m expectation.pass.hoist_dma_alias_ops`
  - 结果：exit=0
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_static_tile_static.py`
  - 结果：exit=0；absent/present bias 数值检查通过，`max_abs_diff=4.1961669921875e-05`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_dynamic_tile_dynamic.py`
  - 结果：exit=0；absent/present bias 数值检查通过，`max_abs_diff=4.57763671875e-05`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/hoist_dma_alias_ops.py kernel_gen/tools/ircheck.py test/passes/test_hoist_dma_alias_ops.py test/tools/test_ircheck_matcher.py && git diff --check`
  - 结果：exit=0
- 敏感目录门禁：
  - `git diff --name-only -- expectation .skills agents/standard`
  - `git diff --cached --name-only -- expectation .skills agents/standard`
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`
  - 结果：三条均无输出。
- 静态扫描：
  - `rg -n "hasattr\\(|getattr\\(|callable\\(getattr|from .* import .*_[A-Za-z]|\\._[A-Za-z]|name_hint|\\bobject\\b" kernel_gen/passes/hoist_dma_alias_ops.py kernel_gen/tools/ircheck.py test/passes/test_hoist_dma_alias_ops.py test/tools/test_ircheck_matcher.py spec/pass/hoist_dma_alias_ops.md || true`
  - 命中均为 spec/注释/公开导入或既有 ircheck 私有别名导入，未形成本轮阻断。
- AST 嵌套函数扫描覆盖本轮 Python 文件，结果无输出。

### 合同真源与导入边界

- 主仓只读 expectation hash 与计划 manifest 一致：
  - `expectation/pass/hoist_dma_alias_ops/__main__.py`：`6d67110fa6acdc438665fa7ff77d2779aa32958c6f5ba635a2ec5c7618e85b7f`
  - `expectation/pass/hoist_dma_alias_ops/reshape.py`：`8c002576132b8e5df8ed6fce1bb504aa2d8ea9ef2bc605b3942b667cc77b5ed4`
  - `expectation/pass/hoist_dma_alias_ops/view.py`：`e2af51ba1c70d8ad82a32efafdc00768bfe605cb84078989985035fde29d2aa3`
- 导入边界核对：
  - `expectation.pass.hoist_dma_alias_ops.reshape -> /home/lfr/kernelcode_generate/expectation/pass/hoist_dma_alias_ops/reshape.py`
  - `expectation.pass.hoist_dma_alias_ops.view -> /home/lfr/kernelcode_generate/expectation/pass/hoist_dma_alias_ops/view.py`
  - `expectation.utils.case_runner -> /home/lfr/kernelcode_generate/expectation/utils/case_runner.py`
  - `kernel_gen.passes.hoist_dma_alias_ops -> /home/lfr/kernelcode_generate/wt-20260523-hoist-dma-alias-view-grouping/kernel_gen/passes/hoist_dma_alias_ops.py`

### 结论

- 结论：通过。
- 最小阻断项：无。
- 通过摘要：计划列名 pytest、Diff 反推 pytest、主仓只读 `expectation.pass.hoist_dma_alias_ops`、两个 conv2d demo、py_compile、git diff check、敏感目录空 diff和静态边界扫描均通过；review 退回项已由公开 pytest/spec 矩阵闭合；候选 diff 未触碰 `expectation/`、`.skills/`、`agents/standard/**`。
- 本结论仅表示大闸蟹侧计划级架构复核 / 终验通过；双架构通过前不得 merge。

## 2026-05-23 14:27 CST 守护最好的爱莉希雅第二架构终验补充确认

### 最新同步现场

- 经办人：守护最好的爱莉希雅
- 任务：T-20260523-f504c795 / hoist-dma-alias-view-grouping
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260523-hoist-dma-alias-view-grouping`
- 计划书：`/home/lfr/kernelcode_generate/ARCHITECTURE/plan/hoist_dma_alias_view_grouping_green_plan.md`
- `HEAD=733538704f3e66a46d89eee2308fb1d44919e18c`
- `origin/main=733538704f3e66a46d89eee2308fb1d44919e18c`
- `merge-base=733538704f3e66a46d89eee2308fb1d44919e18c`
- `ahead/behind=0/0`
- 候选 tracked diff 仍为：
  - `kernel_gen/passes/hoist_dma_alias_ops.py`
  - `kernel_gen/tools/ircheck.py`
  - `spec/pass/hoist_dma_alias_ops.md`
  - `test/passes/test_hoist_dma_alias_ops.py`
  - `test/tools/test_ircheck_matcher.py`
- 本任务记录当前为 untracked 文件，merge 前必须与代码/spec/test 同批纳入。

### 合同验收与门禁

- 主仓只读 expectation 命令：
  - `PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260523-hoist-dma-alias-view-grouping PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260523-hoist-dma-alias-view-grouping:/home/lfr/kernelcode_generate python3 -m expectation.pass.hoist_dma_alias_ops`
  - 结果：exit=0。
  - 摘要：`reshape` 静态正例、`view` 静态/动态正例和动态不连续反例均通过。
- 敏感目录门禁：
  - `git diff --name-only -- expectation .skills agents/standard`：无输出。
  - `git diff --cached --name-only -- expectation .skills agents/standard`：无输出。
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`：无输出。
- 大闸蟹侧与本角色前序终验已复核：
  - 计划 pytest：`103 passed, 1 warning`。
  - `test/tools/test_ircheck_runner.py`：`52 passed, 1 warning`。
  - 两个 conv2d demo：exit=0。
  - `py_compile` / `git diff --check` / 静态边界扫描：通过。

### 自检

- 公开 API：未新增 pass、option、pattern getter、package root re-export 或稳定错误文本；仍为既有 `HoistDmaAliasOpsPass` 行为扩展。
- 合同真源：`expectation` 从主仓只读加载，`kernel_gen.passes.hoist_dma_alias_ops` 从任务 worktree 加载。
- 任务范围：候选 diff 未包含 `expectation/`、`.skills/`、`agents/standard/**`；本记录需同批合入。
- 残余风险：无功能阻断；仅需 merge 阶段确认记录文件被纳入候选提交。

### 结论

- 第二架构终验结论：通过。
- 最小阻断项：无。
- 可进入 merge；双架构终验已齐备，merge 前必须保持敏感目录空 diff，并把本任务记录与代码/spec/test 同批纳入。

---

时间：2026-05-23 14:43 CST
经办人：李白
任务：T-20260523-f504c795 / hoist-dma-alias-view-grouping / merge
任务目标：按 merge 职责合入已通过 review 复审与双架构终验的 hoist-dma-alias-view-grouping 候选 diff；核对 latest main、候选范围、任务记录同批、主仓只读 `expectation.pass.hoist_dma_alias_ops`、计划 pytest/ircheck/demo gate、git diff check 与敏感目录空 diff。

合并前同步与来源：
- 已重新读取 `agents/codex-multi-agents/agents/李白/李白.prompt.md`、根 `AGENTS.md`、`agents/standard/合并规范.md`、`agents/standard/任务记录约定.md`、`agents/standard/expectation任务规则.md`。
- 任务 worktree：`/home/lfr/kernelcode_generate/wt-20260523-hoist-dma-alias-view-grouping`。
- 主仓集成目录：`/home/lfr/kernelcode_generate`。
- 计划真源：主仓只读 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/hoist_dma_alias_view_grouping_green_plan.md`；任务 worktree 内不存在该计划文件。
- 合并前 `git fetch --prune origin` 后，主仓与任务 worktree 均为 `HEAD=origin/main=733538704f3e66a46d89eee2308fb1d44919e18c`，`ahead/behind=0/0`。
- 任务记录当前为 untracked 文件，已在 merge 前核对并准备与代码/spec/test 同批纳入，不做代码先合后补记录。

实际合入范围：
- 实现：`kernel_gen/passes/hoist_dma_alias_ops.py`、`kernel_gen/tools/ircheck.py`。
- spec：`spec/pass/hoist_dma_alias_ops.md`。
- test：`test/passes/test_hoist_dma_alias_ops.py`、`test/tools/test_ircheck_matcher.py`。
- 同批任务记录：`agents/codex-multi-agents/log/task_records/2026/23/20260523-hoist-dma-alias-view-grouping.md`。
- 不纳入 `expectation/`、`.skills/`、`agents/standard/**`；不纳入 demo 运行产生的 ignored `kernel/dump/**`。

验证：
- 计划 pytest：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_hoist_dma_alias_ops.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py test/tools/test_ircheck_matcher.py`
  - 结果：exit=0，`103 passed, 1 warning`。
- ircheck runner 回归：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_ircheck_runner.py`
  - 结果：exit=0，`52 passed, 1 warning`。
- 主仓只读 expectation：`PYTHONDONTWRITEBYTECODE=1 EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260523-hoist-dma-alias-view-grouping PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260523-hoist-dma-alias-view-grouping:/home/lfr/kernelcode_generate python3 -m expectation.pass.hoist_dma_alias_ops`
  - 结果：exit=0。
  - 摘要：`reshape` 静态正例、`view` 静态/动态正例和动态不连续反例均通过；`expectation` 只作为合同验收单列。
- py_compile：`PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/hoist_dma_alias_ops.py kernel_gen/tools/ircheck.py test/passes/test_hoist_dma_alias_ops.py test/tools/test_ircheck_matcher.py`
  - 结果：exit=0。
- demo gate：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_static_tile_static.py`
  - 结果：exit=0；stdout 含 `inputs_static_tile_static_absent_bias` 与 `inputs_static_tile_static_present_bias` 数值检查通过，`max_abs_diff=4.1961669921875e-05`。
- demo gate：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_dynamic_tile_dynamic.py`
  - 结果：exit=0；stdout 含动态 memory-pool marker 与 absent/present bias 数值检查通过，`max_abs_diff=4.57763671875e-05`。
- `git diff --check`：exit=0。
- 敏感目录核对：
  - `git diff --name-only -- expectation .skills agents/standard`：无输出。
  - `git diff --cached --name-only -- expectation .skills agents/standard`：无输出。
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`：无输出。
- 静态扫描：
  - `rg -n "hasattr\\(|getattr\\(|callable\\(getattr|from .* import .*_[A-Za-z]|\\._[A-Za-z]|name_hint|\\bobject\\b" kernel_gen/passes/hoist_dma_alias_ops.py kernel_gen/tools/ircheck.py test/passes/test_hoist_dma_alias_ops.py test/tools/test_ircheck_matcher.py spec/pass/hoist_dma_alias_ops.md || true` 命中均为 spec/注释/公开导入或 `kernel_gen/tools/ircheck.py` 既有 `_build_default_context_base` 私有别名导入；未形成本轮阻断。
  - AST 嵌套函数扫描覆盖本轮 Python 文件，无输出。

冲突处理：
- 任务 worktree 与主仓 latest main 基线一致，候选 diff 可直接从 worktree 应用到主仓；未发现与最新主线重叠冲突。
- demo 产生的 `kernel/dump/**` 为 ignored 输出，不作为候选 diff，也不清理。

剩余风险：
- 本轮不修改 `expectation/`，只读取并运行主仓合同资产；若后续主仓 expectation 合同变化，需要由对应计划重新验收。
- 任务 worktree 在主仓合入后仍会保留未提交候选改动；如需回收，必须在确认主仓提交覆盖候选且不使用破坏性 reset/force 的前提下另行处理。

结论：merge gate 通过，可将上述实现 / spec / test 与本任务记录同批提交、推送并执行 `-done`。
