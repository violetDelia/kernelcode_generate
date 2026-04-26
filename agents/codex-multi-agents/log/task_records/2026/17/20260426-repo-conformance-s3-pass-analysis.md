时间：2026-04-26 21:33:58 +0800
经办人：jcc你莫辜负
任务：T-20260426-5caa70b5
任务目标：按 `repo_conformance_refactor_green_plan` S3 为 `passes / analysis` 收口 class API 简表、文件说明、公开 API 清单、helper 清单和测试公开入口，并跑通对应 `pytest`
执行前阅读记录：已读 `TODO.md` 当前任务行、计划书 `ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md` 的 S3 正文、全局完成态与验收设计；已核对 `spec/pass/registry.md`、`spec/pass/pass_manager.md`、`spec/pass/lowering/dma_memory_hierarchy/spec.md`、`spec/pass/lowering/nn_lowering/spec.md` 与 `test/pass/**` 现场；已确认当前 worktree 下无独立 `kernel_gen/analysis/**` / `test/analysis/**` 实体目录，本轮 analysis 范围实际收口到 `kernel_gen/passes/tile/analysis.py` 及其公开入口。
最小功能闭环：1）为本轮涉及的 `passes` 公开实现文件补齐文件级 `API 列表`，并在文件说明里把 helper 边界写清；2）把 `test/pass` 中直接连接私有入口的 case 改成公开入口验证：`registry` 不再调用 `_reset_registry_for_test`、`dma_memory_hierarchy` 不再调用 `_set_current_target`、`tile` 不再断言 `_raise_tile_error`、`nn_lowering` 不再盯私有 pattern 类名；3）删除整份 `test/pass/nn_lowering/test_nn_lowering_private_helpers.py`，把 `asset_cases` 中仍需 monkeypatch 的公开 case 单独挂到 collectable 入口。
改动：
- 更新 `kernel_gen/passes/registry.py`、`kernel_gen/passes/pass_manager.py`、`kernel_gen/passes/dma_memory_hierarchy.py`、`kernel_gen/passes/lowering/__init__.py`、`kernel_gen/passes/lowering/nn_lowering/__init__.py`、`kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`、`kernel_gen/passes/tile/__init__.py` 文件头，补齐 `API 列表`，并把当前文件内部 helper 边界写入 `功能说明`。
- 更新 `test/pass/test_pass_registry.py`，改为用公开 `importlib.reload(import_module(...))` 重建 registry 状态，不再触碰 `_reset_registry_for_test`；同步把“重置后再次加载”改成“重新导入后再次加载”。
- 更新 `test/pass/test_pass_manager.py`，改为局部重载公开 `kernel_gen.passes.registry` 模块后执行 `lower-nn` registry 用例，不再调用私有 reset helper。
- 更新 `test/pass/test_dma_memory_hierarchy.py`，用 monkeypatch 公开 `target_registry.get_current_target_hardware` 模拟 `SM/LM` 容量，不再使用私有 `_set_current_target`。
- 更新 `test/pass/tile/test_package.py`，只验证 `kernel_gen.passes.tile` 与 `kernel_gen.passes.lowering.tile` 的公开模块/公开 pass API，不再断言私有 `_raise_tile_error`；同时修正 tile spec 链接为 `analysis.md / elewise.md / reduce.md`。
- 更新 `test/pass/nn_lowering/public_name.py`，把私有 pattern 类名断言改为公开 `*_patterns()` 组合顺序断言；更新 `test/pass/nn_lowering/test_nn_lowering_asset_cases.py` 的资产挂接；删除 `test/pass/nn_lowering/test_nn_lowering_private_helpers.py`。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/test_pass_registry.py test/pass/test_pass_manager.py test/pass/test_dma_memory_hierarchy.py test/pass/tile/test_package.py test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_nn_lowering_asset_cases.py -k 'public_name or pattern_driver or compose_public_family_exports or test_pass_registry or test_pass_manager or test_dma_memory_hierarchy or test_tile_package or test_tile_registered_passes or test_legacy_tile_module' -ra` -> `64 passed, 24 deselected, 1 warning`
- `python3 -m py_compile kernel_gen/passes/registry.py kernel_gen/passes/pass_manager.py kernel_gen/passes/dma_memory_hierarchy.py kernel_gen/passes/lowering/__init__.py kernel_gen/passes/lowering/nn_lowering/__init__.py kernel_gen/passes/lowering/nn_lowering/nn_lowering.py kernel_gen/passes/tile/__init__.py test/pass/test_pass_registry.py test/pass/test_pass_manager.py test/pass/test_dma_memory_hierarchy.py test/pass/tile/test_package.py test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_nn_lowering_asset_cases.py` -> 通过
- `git -C /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis diff --check` -> 通过
- 文本核对：`rg -n "_set_current_target|_reset_registry_for_test|test_nn_lowering_private_helpers" test/pass -g '*.py'` -> 当前 diff 范围内相关命中已清零；`test/tools/**` 仍有 `_reset_registry_for_test` 只读残留，不在本轮 `S3` 范围
Diff 反推自测：
- 改动文件覆盖 `kernel_gen/passes/{registry,pass_manager,dma_memory_hierarchy}.py`、`kernel_gen/passes/lowering/**`、`kernel_gen/passes/tile/__init__.py` 与对应 `test/pass/**`；反推测试入口为 `test_pass_registry.py`、`test_pass_manager.py`、`test_dma_memory_hierarchy.py`、`test/pass/tile/test_package.py`、`test/pass/nn_lowering/public_name.py`、`test/pass/nn_lowering/test_nn_lowering_asset_cases.py` 中当前 diff 直接涉及的公开入口 case；结果通过。
- 额外试跑 `pytest -q test/pass/test_pass_registry.py test/pass/test_pass_manager.py test/pass/test_dma_memory_hierarchy.py test/pass/tile test/pass/nn_lowering -ra` 时，发现 `test/pass/nn_lowering/img2col1d.py::test_nn_lowering_img2col1d_accepts_noncanonical_symbol_names` 与 `test/pass/nn_lowering/img2col2d.py::test_nn_lowering_img2col2d_accepts_noncanonical_symbol_names` 现存失败；两者落在 `img2col` 资产行为，不属于本轮 public-entry / API-list diff，故未在当前 S3 build 扩修。
合同验收（如适用）：未执行；`expectation` 按规则只读，本轮也无对应 `expectation` 合同入口变更。
自检：已读完整阶段；未越权修改 `expectation` 或其他角色专属文件；本轮闭环只收 `passes / analysis` 的文件说明、公开 API 清单、helper 边界和测试公开入口；实现文件头 `API 列表` 已补齐且只列公开接口；测试已改为只通过公开入口或公开模块组合验证行为，没有再通过直接调用、包装转发、别名导入或反射方式连接当前文件之外的非公开 API；删除的 `test_nn_lowering_private_helpers.py` 不再把私有 helper 当成公开合同；已按实际 diff 反推并跑通对应 `pytest` / `py_compile` / `diff --check`；未发现本轮改动引入新的逻辑回退、注释失真、函数粒度异常、资源/并发/兼容问题。
结论：当前 S3 build 已按任务边界完成，任务记录已写入对应 worktree；下一步执行 `-next -auto -type review` 并通知管理员按 `TODO.md` 推进。

## Review - 不要啊教练
- 时间：2026-04-26 22:10:00 +0800
- 结论：需修改

### 真实审查
- 已按 `TODO.md` 当前任务行、`ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md` S3 正文、全局完成态/验收设计和当前 worktree 任务记录复核本轮范围。
- 已逐个检查本轮 residual diff 的实现与测试文件，重点核对：1）文件级 `API 列表` 是否与实现一致；2）是否新增未在 spec 明确定义的公开接口；3）是否存在跨文件调用非公开 API；4）测试是否直连当前文件之外的非公开接口；5）`img2col` 现存失败是否属于当前 diff。
- 现场确认：当前 diff 中 `registry`、`pass_manager`、`dma_memory_hierarchy`、`nn_lowering` 相关测试都已改成经由公开模块或公开函数/类验证行为，没有继续直接连接当前文件之外的非公开 helper；`img2col1d/2d` 的两条失败可独立复现，但落在未改动的 `test/pass/nn_lowering/img2col1d.py` 与 `img2col2d.py`，不属于本轮 residual diff。

### 问题列表
1. [`kernel_gen/passes/tile/__init__.py`](kernel_gen/passes/tile/__init__.py)
   - 当前文件头 `API 列表` 仅列了 `analysis`、`elewise`、`reduce` 三个模块名，没有按最新规则列公开 API 与参数签名。
   - 本轮任务目标明确包含 `passes / analysis` 的 `API 列表` 收口；而最新审查口径要求“build 改动功能实现文件时，必须同步维护文件级 API 列表；API 列表只做快速索引，列公开 API 与参数签名；class 文件需列类公开 API”。
   - `kernel_gen.passes.tile.__init__` 当前的公开边界是 package 级可访问模块与其承载的公开对象，但模块名本身不满足“公开 API + 参数签名”的记录要求。至少需要把这里改成可机械核对的 package 公开入口索引写法，并与当前 spec / pytest 的公开用法保持一致。

### Diff 反推审查
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/test_pass_registry.py test/pass/test_pass_manager.py test/pass/test_dma_memory_hierarchy.py test/pass/tile/test_package.py test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_nn_lowering_asset_cases.py -k 'public_name or pattern_driver or compose_public_family_exports or test_pass_registry or test_pass_manager or test_dma_memory_hierarchy or test_tile_package or test_tile_registered_passes or test_legacy_tile_module' -ra` -> `64 passed, 24 deselected, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/img2col1d.py::test_nn_lowering_img2col1d_accepts_noncanonical_symbol_names test/pass/nn_lowering/img2col2d.py::test_nn_lowering_img2col2d_accepts_noncanonical_symbol_names -ra` -> `2 failed, 1 warning`
- `git -C /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis diff --check` -> 通过

### 可改进点
- 当前 diff 的公开入口和测试边界已基本收住，但 `kernel_gen/passes/tile/__init__.py` 的文件级 `API 列表` 仍需改成与规则一致的快速索引格式，否则这轮 `passes / analysis` 的 API 清单还不能算完成。
- `img2col` 两条现存失败已确认与当前 diff 无关；后续若要继续推进 `nn_lowering` 目录整体收口，应另起任务处理，不应混入本轮 API / helper 边界修整链路。

## Build 复修 - 金铲铲大作战
- 时间：2026-04-26 22:26:00 +0800

### 改动
- 更新 [`kernel_gen/passes/tile/__init__.py`](kernel_gen/passes/tile/__init__.py) 文件级 `API 列表`，将原先仅列模块名的写法收紧为 package-root 公开模块属性快速索引：
  - `analysis: module`
  - `elewise: module`
  - `reduce: module`
- 更新 [`test/pass/tile/test_package.py`](test/pass/tile/test_package.py)，补一条 package-root 边界断言：`kernel_gen.passes.tile` 不公开 `TileAnalysisPass / TileElewisePass / TileReducePass`，只公开三 个模块属性。

### 验证
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/tile/test_package.py -ra`
- `python3 -m py_compile kernel_gen/passes/tile/__init__.py test/pass/tile/test_package.py`
- `git -C /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis diff --check`

### Diff 反推自测
- 本轮 residual diff 只落在 `kernel_gen/passes/tile/__init__.py` 与 `test/pass/tile/test_package.py`，因此只复跑 package-root 公开入口测试，不扩大到与当前 diff 无关的 `img2col` 资产。

### 真实自检
- `kernel_gen.passes.tile` 的 package-root 公开边界仍保持为 `analysis / elewise / reduce` 三个模块属性，没有新增 spec 未定义的公开类或 helper。
- 测试继续只通过 package-root 与公开子模块验证行为，没有直连当前文件之外的非公开 API。

## Review - 不要啊教练
- 时间：2026-04-26 22:14:04 +0800
- 结论：需修改

### 真实审查
- 已按 `TODO.md` 当前任务行、`ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md` S3 正文、全局完成态/验收设计与本任务 build 记录复核当前 residual diff。
- 本轮重点检查了三类风险：1）修改过的实现文件 `API 列表` 是否与当前公开边界一致；2）是否新增未在 `spec` 明确定义的公开接口；3）测试是否仍直连当前文件之外的非公开 `API`。
- `kernel_gen/passes/tile/__init__.py` 的 package-root `API 列表` 与 `test/pass/tile/test_package.py` 的 package 边界断言已经补到位；`img2col` 现存失败仍可复现，但失败点落在未改动的 `test/pass/nn_lowering/img2col1d.py` / `img2col2d.py`，未回流到本轮产品边界修整。

### 问题列表
1. [`test/pass/nn_lowering/public_name.py:37`](test/pass/nn_lowering/public_name.py#L37) 到 [`test/pass/nn_lowering/public_name.py:53`](test/pass/nn_lowering/public_name.py#L53)
   - 当前测试仍直接导入实现子模块 `kernel_gen.passes.lowering.nn_lowering.nn_lowering`，并进一步持有 `element_binary_lowering`、`dma_structured_lowering`、`select_cast_lowering`、`matmul_img2col_lowering`、`reduce_softmax_lowering` 模块对象。
   - 其中 child family 模块的 surviving 公开接口仅限 `*_patterns()`；而 `kernel_gen.passes.lowering.nn_lowering.nn_lowering` 本身并不是 `spec` 定义的 canonical public path。
2. [`test/pass/nn_lowering/public_name.py:116`](test/pass/nn_lowering/public_name.py#L116) 到 [`test/pass/nn_lowering/public_name.py:128`](test/pass/nn_lowering/public_name.py#L128)、[`test/pass/nn_lowering/public_name.py:180`](test/pass/nn_lowering/public_name.py#L180) 到 [`test/pass/nn_lowering/public_name.py:182`](test/pass/nn_lowering/public_name.py#L182)
   - 当前 case 直接通过 `nn_lowering_module.nn_lowering_patterns()`、`nn_lowering_module.RewritePattern`、以及 monkeypatch `nn_lowering_module.GreedyRewritePatternApplier / PatternRewriteWalker` 来验证行为。
   - 这属于测试直连当前文件之外的非公开实现细节。按最新审查规则，不能以“只是内部 helper / 测试方便 / 当前能跑”为由放行。
3. [`spec/pass/lowering/nn_lowering/spec.md:45`](spec/pass/lowering/nn_lowering/spec.md#L45) 到 [`spec/pass/lowering/nn_lowering/spec.md:72`](spec/pass/lowering/nn_lowering/spec.md#L72)
   - `spec` 已明确：唯一 canonical import path 是 `kernel_gen.passes.lowering.nn_lowering.NnLoweringPass`；family 子模块 surviving 模块级接口只允许 `*_patterns()`。
   - 当前 `public_name.py` 的实现子模块依赖与这条公开边界不一致，因此这轮 `helper 边界与测试公开入口收口` 还没有闭合。

### Diff 反推审查
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/test_pass_registry.py test/pass/test_pass_manager.py test/pass/test_dma_memory_hierarchy.py test/pass/tile/test_package.py test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_nn_lowering_asset_cases.py -ra` -> `2 failed, 86 passed, 1 warning`
  - 失败点固定为 [`test/pass/nn_lowering/img2col1d.py:159`](test/pass/nn_lowering/img2col1d.py#L159) 与 [`test/pass/nn_lowering/img2col2d.py:202`](test/pass/nn_lowering/img2col2d.py#L202) 的既有断言文本，不是本轮 package API / public-entry 改动直接引入。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/img2col1d.py::test_nn_lowering_img2col1d_target test/pass/nn_lowering/img2col2d.py::test_nn_lowering_img2col2d_target -ra` -> `2 passed, 1 warning`
- `git -C /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis diff --check` -> 通过

### 可改进点
- `public_name.py` 需要改成只通过 `spec` 已定义的公开入口验证行为：
  - package 级 `kernel_gen.passes.lowering.nn_lowering`；
  - 以及 child family 模块各自的 `*_patterns()` 公开函数。
- 若仍需验证 `NnLoweringPass.apply(...)` 是否委托 `nn_lowering_patterns()` 与 `PatternRewriteWalker`，应补成公开合同可承载的测试入口，而不是直接 monkeypatch `kernel_gen.passes.lowering.nn_lowering.nn_lowering` 子模块。
- `img2col` 两条失败仍建议独立任务处理，不应在本轮 `S3 passes / analysis` 公开边界收口链中顺手扩修。

---

时间：2026-04-26 22:20 +0800
经办人：小李飞刀
任务：T-20260426-5caa70b5 / S3 build 修复回合
任务目标：修复 [test/pass/nn_lowering/public_name.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py) 仍直连 `kernel_gen.passes.lowering.nn_lowering.nn_lowering` 实现子模块并对其 monkeypatch / 类型断言的问题，保持 `tile` package API 收口结果不回退，并把 `img2col` 既有失败继续隔离在未改动资产范围外
执行前阅读记录：已读 [TODO.md](/home/lfr/kernelcode_generate/TODO.md) 当前任务行、[ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md) S3、[AGENTS.md](/home/lfr/kernelcode_generate/AGENTS.md)、本任务前序 build/review 记录、[spec/pass/lowering/nn_lowering/spec.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md)、[kernel_gen/passes/lowering/nn_lowering/__init__.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/__init__.py)、[kernel_gen/passes/lowering/nn_lowering/nn_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)、[test/pass/nn_lowering/public_name.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py)、[test/pass/nn_lowering/test_nn_lowering_asset_cases.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py)。
最小功能闭环：1）让 `kernel_gen.passes.lowering.nn_lowering` 包根公开导出 `nn_lowering_patterns()`，与现有 spec 一致；2）把 `public_name.py` 的 pattern 顺序与 `apply(...)` 验证改成只走包根导出和 child family 的 `*_patterns()` 公开面；3）保持资产桥接测试可收集，但不恢复任何对实现子模块或内部 driver 的 monkeypatch。
改动：
- 更新 [kernel_gen/passes/lowering/nn_lowering/__init__.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/__init__.py)，补齐文件级 `API 列表`，并把 `nn_lowering_patterns()` 纳入包根公开导出与 `__all__`；这是现有 [spec/pass/lowering/nn_lowering/spec.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md) 已定义的 surviving public contract，不是新增未定义公开口径。
- 更新 [test/pass/nn_lowering/public_name.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py)，删除对 `kernel_gen.passes.lowering.nn_lowering.nn_lowering` 实现子模块的直接导入；当前只通过 `kernel_gen.passes.lowering.nn_lowering` 包根导出的 `NnLoweringPass / NnLoweringError / nn_lowering_patterns`，以及 child family 模块各自的 `*_patterns()` 公开函数验证行为。
- 同步把 `test_nn_lowering_patterns_compose_public_family_exports` 与 `test_nn_lowering_apply_uses_pattern_driver` 改成公开行为校验：前者比对 child family 公开 pattern 组合顺序，后者真实构造 `nn.add` module 并调用 `NnLoweringPass().apply(...)`，确认 lowering 结果含 `dma.alloc + kernel.binary_elewise(kind=\"add\")`，不再 monkeypatch `PatternRewriteWalker / GreedyRewritePatternApplier`。
- 为兼容 [test/pass/nn_lowering/test_nn_lowering_asset_cases.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py) 的现有桥接入口，保留这两条 public test 的 `monkeypatch` 形参兼容位，但函数体不再使用该 fixture，也不再对任何内部实现做 monkeypatch。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/public_name.py -ra` -> `5 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_nn_lowering_asset_cases.py -k 'test_nn_lowering_patterns_compose_public_family_exports or test_nn_lowering_apply_uses_pattern_driver or test_nn_lowering_pass_public_name or test_nn_lowering_pass_public_exports or test_nn_lowering_child_pattern_exports' -ra` -> `9 passed, 24 deselected, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/img2col1d.py::test_nn_lowering_img2col1d_accepts_noncanonical_symbol_names test/pass/nn_lowering/img2col2d.py::test_nn_lowering_img2col2d_accepts_noncanonical_symbol_names -ra` -> `2 failed, 1 warning`
  - 失败仍固定在 [test/pass/nn_lowering/img2col1d.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/img2col1d.py) 与 [test/pass/nn_lowering/img2col2d.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/img2col2d.py) 的既有断言文本，未回流到本轮 diff 文件。
- `python3 -m py_compile kernel_gen/passes/lowering/nn_lowering/__init__.py test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_nn_lowering_asset_cases.py` -> 通过
- `rg -n "kernel_gen\\.passes\\.lowering\\.nn_lowering\\.nn_lowering|monkeypatch\\.setattr|GreedyRewritePatternApplier|PatternRewriteWalker|nn_lowering_module" test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_nn_lowering_asset_cases.py` -> 无命中
- `git -C /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis diff --check` -> 通过
Diff 反推自测：本轮 diff 只覆盖 [kernel_gen/passes/lowering/nn_lowering/__init__.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/__init__.py) 与 [test/pass/nn_lowering/public_name.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py)；反推测试选择 `public_name.py` 全量、`test_nn_lowering_asset_cases.py` 中直接桥接这两条 public case 的收集入口，以及 `py_compile`、私有实现子模块 / monkeypatch 文本扫描和 `git diff --check`；结果通过。额外复跑两条 `img2col` 现存失败，仅用于证明它们仍落在未改动资产文件，不计入本轮通过条件。
合同验收（如适用）：未执行；`expectation` 按规则只读，本轮也无相关合同资产变更。
自检：
- 已按最新规则确认：没有新增 spec 未定义的公开 API；新增到包根的 `nn_lowering_patterns()` 属于现有 spec 已定义的 surviving public contract。
- `public_name.py` 已不再直接导入 `kernel_gen.passes.lowering.nn_lowering.nn_lowering`，也不再 monkeypatch `GreedyRewritePatternApplier / PatternRewriteWalker` 等当前文件之外的实现细节。
- 公开测试当前只连接 package-root `kernel_gen.passes.lowering.nn_lowering` 和 child family 的 `*_patterns()` 公开入口。
- 本轮没有修改 `img2col1d.py`、`img2col2d.py`、`tile` family、`expectation` 或其他非当前范围文件。
结论：本轮 review 退回项已收口，`img2col` 既有失败继续隔离在未改动资产文件中，可以按 TODO 继续流转到下一轮 review。

## Review - 不要啊教练
- 时间：2026-04-26 22:45:00 +0800
- 结论：需修改

### 真实审查
- 已按 `TODO.md` 当前任务行、[`ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md`](../../../../../../../ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md) 的 `S3` 阶段正文、全局完成态/验收设计与本任务前序 build/review 记录复核当前 residual diff。
- 本轮重点复核 `nn_lowering public_name` 是否已经只通过 spec 定义的公开入口验证行为、包根导出是否与公开合同一致，以及未改动 `img2col` 资产失败是否仍然隔离在当前 diff 之外。
- `kernel_gen.passes.lowering.nn_lowering.nn_lowering` 实现子模块直连和内部 driver monkeypatch 已清掉；`img2col` 两条既有失败仍落在未改动的资产文件中，没有回流到本轮 diff。

### 问题列表
1. [`test/pass/nn_lowering/public_name.py:122`](../../../../../../../test/pass/nn_lowering/public_name.py#L122) 到 [`test/pass/nn_lowering/public_name.py:124`](../../../../../../../test/pass/nn_lowering/public_name.py#L124)
   - 当前 case 仍通过 `getattr(module, "__all__", [])` 断言 `nn_lowering_patterns` 是否导出、旧 compat 名称是否移除。
   - `__all__` 并不在 [`spec/pass/lowering/nn_lowering/spec.md`](../../../../../../../spec/pass/lowering/nn_lowering/spec.md) 的公开 API 中；按最新审查规则，这属于测试直连未定义公开接口，不能作为公开边界验收证据。
2. [`test/pass/nn_lowering/public_name.py:168`](../../../../../../../test/pass/nn_lowering/public_name.py#L168) 到 [`test/pass/nn_lowering/public_name.py:172`](../../../../../../../test/pass/nn_lowering/public_name.py#L172)
   - child family export case 仍直接断言 `element_binary_module.__all__`、`dma_structured_module.__all__`、`select_cast_module.__all__`、`matmul_img2col_module.__all__`、`reduce_softmax_module.__all__`。
   - 当前 spec 只定义这些 child 模块 surviving 模块级公开接口是 `*_patterns()`，没有把 `__all__` 本身定义为对外 API；这条测试边界仍未收口。

### Diff 反推审查
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/public_name.py -ra` -> `5 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_nn_lowering_asset_cases.py -k 'test_nn_lowering_patterns_compose_public_family_exports or test_nn_lowering_apply_uses_pattern_driver or test_nn_lowering_pass_public_name or test_nn_lowering_pass_public_exports or test_nn_lowering_child_pattern_exports' -ra` -> `9 passed, 24 deselected, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/test_pass_registry.py test/pass/test_pass_manager.py test/pass/test_dma_memory_hierarchy.py test/pass/tile/test_package.py test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_nn_lowering_asset_cases.py -k 'not img2col' -ra` -> `84 passed, 4 deselected, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/img2col1d.py::test_nn_lowering_img2col1d_accepts_noncanonical_symbol_names test/pass/nn_lowering/img2col2d.py::test_nn_lowering_img2col2d_accepts_noncanonical_symbol_names -ra` -> `2 failed, 1 warning`
  - 失败仍固定在未改动的 [`test/pass/nn_lowering/img2col1d.py`](../../../../../../../test/pass/nn_lowering/img2col1d.py) 与 [`test/pass/nn_lowering/img2col2d.py`](../../../../../../../test/pass/nn_lowering/img2col2d.py)，未回流到本轮 diff 文件。
- `git -C /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis diff --check` -> 通过

### 可改进点
- `public_name.py` 需要把 package export / child family export 断言改成只验证 spec 已定义的公开对象可导入、可调用、且旧 compat 名称不可达；不要再把 `__all__` 当成验收面。
- `img2col` 既有失败应继续留在独立链路处理，不应在本轮 `S3 passes / analysis` 的公开边界收口中扩修。

---

时间：2026-04-26 22:58:00 +0800
经办人：金铲铲大作战
任务：T-20260426-5caa70b5 / S3 build 复修
任务目标：修复 `public_name.py` 仍通过 `__all__` 断言 package export 与 child family export 的测试边界问题；保持 `img2col` 既有失败继续隔离在未改动资产文件。
执行前阅读记录：已读 [TODO.md](/home/lfr/kernelcode_generate/TODO.md) 当前任务行、[ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md) S3 正文、当前任务记录中的前序 build/review 结论、[AGENTS.md](/home/lfr/kernelcode_generate/AGENTS.md)，并复核 [test/pass/nn_lowering/public_name.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py)、[kernel_gen/passes/lowering/nn_lowering/__init__.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/__init__.py)、[spec/pass/lowering/nn_lowering/spec.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md) 与 child family 模块现场。
最小功能闭环：
- `public_name.py` 不再以 `__all__` 作为 package export / child family export 的验收面。
- 公开断言只保留：spec 已定义的公开对象可达、可调用，以及旧 compat 名称不可达。
- `img2col` 既有失败继续保持在未改动资产文件外，不并入本轮 diff 通过条件。
改动：
- 更新 [test/pass/nn_lowering/public_name.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py)，将 package export case 中对 `__all__` 的断言改为公开对象可达断言：`nn_lowering_patterns` 必须可经包根直接访问，`LowerNnToKernelPass / LowerNnToKernelError` 仍不可达。
- 同步更新 child family export case，改为只验证 `element_binary_patterns / dma_structured_patterns / select_cast_patterns / matmul_img2col_patterns / reduce_softmax_patterns` 五个 surviving 公开函数可达且可调用，并确认旧 `lower_*_family` compat 名称不可达。
- 同步文件头与受影响 case 的 `最后一次更改` 为本轮实际修改者。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/public_name.py -ra` -> `5 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/test_pass_registry.py test/pass/test_pass_manager.py test/pass/test_dma_memory_hierarchy.py test/pass/tile/test_package.py test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_nn_lowering_asset_cases.py -k 'not img2col' -ra` -> `84 passed, 4 deselected, 1 warning`
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py` -> 通过
- `if rg -n "__all__" /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py; then exit 1; else echo "public_name __all__ check ok"; fi` -> `public_name __all__ check ok`
- `git -C /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis diff --check` -> 通过
Diff 反推自测：
- 本轮 residual diff 只覆盖 [test/pass/nn_lowering/public_name.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py)，因此反推测试只复跑该文件全量，以及同一组 S3 公开入口回归中去除 `img2col` 资产失败后的集合。
- `img2col` 既有失败未复修，只继续保持在前序记录中隔离，不计入本轮通过条件。
合同验收（如适用）：
- 未执行；本轮只修公开测试边界，`expectation` 继续只作合同验收资产单列。
自检：
- 没有新增 spec 未定义的公开接口，也没有回退当前 `nn_lowering` 包根与 child family 的 surviving public contract。
- 测试已不再把 `__all__` 当成公开 API；当前只验证公开对象可达、可调用和旧 compat 名称不可达。
- 没有跨文件调用非公开 API；也没有修改 `img2col` 资产文件、`expectation` 或其他非当前范围文件。
结论：
- 当前 build 已完成，可续接 `review`。

---

时间：2026-04-27 01:10:00 +0800
经办人：提莫炖蘑菇
任务：T-20260426-5caa70b5 / S3 review 复审回合
任务目标：复核 [reduce_softmax_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py) 的文件级 `API 列表`、跨文件下划线 helper 依赖清理，以及 `nn_lowering` / `pass_manager` / `registry` / `tile` 当前 residual diff 的公开边界不回退。
执行前阅读记录：
- 已读 [TODO.md](/home/lfr/kernelcode_generate/TODO.md) 当前任务行、[ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md) S3 正文 / 完成态 / 验收设计、当前任务记录中的前序 build / review 记录与 [AGENTS.md](/home/lfr/kernelcode_generate/AGENTS.md)。
- 已复核当前 residual diff 文件集，确认仍覆盖：
  - [kernel_gen/passes/dma_memory_hierarchy.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/dma_memory_hierarchy.py)
  - [kernel_gen/passes/lowering/__init__.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/__init__.py)
  - [kernel_gen/passes/lowering/nn_lowering/__init__.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/__init__.py)
  - [kernel_gen/passes/lowering/nn_lowering/nn_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
  - [kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py)
  - [kernel_gen/passes/pass_manager.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/pass_manager.py)
  - [kernel_gen/passes/registry.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/registry.py)
  - [kernel_gen/passes/tile/__init__.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/tile/__init__.py)
真实审查：
- [kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py) 已补文件级 `API 列表`，当前 surviving 公开接口仅保留 `reduce_softmax_patterns() -> list[RewritePattern]`，与 [spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md) 一致。
- 该文件已不再跨文件 import [nn_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/nn_lowering.py) 的下划线 helper；当前只保留公开异常类型 `NnLoweringError` 和 utility 模块公开函数 `ensure_expected_op_name(...)` 的依赖。
- [test/pass/nn_lowering/test_nn_lowering_asset_cases.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py) 继续只桥接非 `test_*.py` 资产 case；没有回退到跨文件直接调用 [public_name.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py) 测试函数。
- 当前 residual diff 中其余实现文件仍都保留文件级 `API 列表`，没有回退为缺失状态。
- 未发现新增未在 spec 明确定义的公开接口，也未发现当前文件之外的非公开 API 使用或测试直连非 API 接口。
Diff 反推审查：
- 被审 diff 文件：
  - `kernel_gen/passes/dma_memory_hierarchy.py`
  - `kernel_gen/passes/lowering/__init__.py`
  - `kernel_gen/passes/lowering/nn_lowering/__init__.py`
  - `kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`
  - `kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py`
  - `kernel_gen/passes/pass_manager.py`
  - `kernel_gen/passes/registry.py`
  - `kernel_gen/passes/tile/__init__.py`
  - `spec/pass/lowering/nn_lowering/*.md`
  - `test/pass/nn_lowering/public_name.py`
  - `test/pass/nn_lowering/test_nn_lowering_asset_cases.py`
  - `test/pass/test_dma_memory_hierarchy.py`
  - `test/pass/test_pass_manager.py`
  - `test/pass/test_pass_registry.py`
  - `test/pass/tile/test_package.py`
- 反推测试：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_reduce_lowering.py test/pass/nn_lowering/test_lowering_nn_lowering.py -k 'reduce or softmax or nn_lowering_pass_public_name or nn_lowering_child_pattern_exports or pattern_driver' -ra`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/test_pass_registry.py test/pass/test_pass_manager.py test/pass/test_dma_memory_hierarchy.py test/pass/tile/test_package.py test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_nn_lowering_asset_cases.py -ra`
  - `git diff --check`
- 审查结果：
  - `23 passed, 34 deselected, 1 warning`
  - `82 passed, 1 warning`
  - `git diff --check` -> 通过
合同验收（如适用）：
- 本轮未执行 `expectation`；其继续只作合同验收资产单列，不计入 diff 反推审查。
自检：
- 已按最新规则核对：是否新增 spec 未定义公开接口、是否跨文件调用非公开 API、测试是否直连非 API 接口、改动实现文件是否同步维护文件级 API 列表。
- 当前此前阻断的两项问题均已收口：
  - `reduce_softmax_lowering.py` 已补文件级 `API 列表`
  - 对 `nn_lowering.py` 下划线 helper 的跨文件直连已断开
- 当前 residual diff 内未再发现可直接执行的一线问题。
可改进点：
- `test_nn_lowering_asset_cases.py` 当前仍以“资产桥接入口”方式复用非 `test_*.py` case；如果后续要继续收敛测试层级，优先方向应是逐步把这些资产文件自身转成明确的 collectable 公开 pytest，而不是再回到跨文件测试函数直连。但这不构成本轮阻断。
结论：
- `通过`。
- `reduce_softmax_lowering.py` 的实现公开边界、文件级 `API 列表` 与当前 residual diff 的 pass / analysis 公开测试入口都已收口，可继续流转到 `merge`。

---

时间：2026-04-27 00:03:00 +0800
经办人：金铲铲大作战
任务：T-20260426-5caa70b5 / S3 build 复修
任务目标：移除 [test/pass/tile/test_package.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/tile/test_package.py) 对 `tile_package.__all__` 的断言，只保留 spec 已定义的公开模块可达性与未定义名字不可达边界。
执行前阅读记录：已读 [TODO.md](/home/lfr/kernelcode_generate/TODO.md) 当前任务行、[ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md) S3 正文、[AGENTS.md](/home/lfr/kernelcode_generate/AGENTS.md) 与当前任务记录前序 build / review 结论，并复核 [test/pass/tile/test_package.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/tile/test_package.py)、[kernel_gen/passes/tile/__init__.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/tile/__init__.py)、[spec/pass/tile/analysis.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/tile/analysis.md)、[spec/pass/tile/elewise.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/tile/elewise.md)、[spec/pass/tile/reduce.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/tile/reduce.md) 当前现场。
最小功能闭环：
- `test_tile_package_exports_only_public_modules()` 不再把 `__all__` 当作公开 API 验收面。
- 仍保留 `analysis/elewise/reduce` 三个 spec 已定义公开模块的可达性断言。
- 仍保留未定义名字 `TileAnalysisPass / TileElewisePass / TileReducePass / contract / rewrite` 不可达边界。
改动：
- 更新 [test/pass/tile/test_package.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/tile/test_package.py)，删除 `assert tile_package.__all__ == ["analysis", "elewise", "reduce"]`，其余 package-root 公开模块可达性与未定义名字不可达断言保持不变。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/tile/test_package.py -ra` -> `3 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/test_pass_registry.py test/pass/test_pass_manager.py test/pass/tile/test_package.py -k 'tile' -ra` -> `6 passed, 42 deselected, 1 warning`
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/tile/test_package.py` -> 通过
- `git -C /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis diff --check` -> 通过
Diff 反推自测：
- 本轮 diff 只落在 [test/pass/tile/test_package.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/tile/test_package.py)，反推测试选择该文件全量，以及与 tile family 公开 pass 注册链路直接相关的 `test_pass_registry.py / test_pass_manager.py` 中 `-k 'tile'` 的公开入口子集。
- 本轮未扩大到 `nn_lowering/img2col` 资产文件，也未将无关目录用例纳入通过条件。
合同验收（如适用）：
- 未执行 `expectation`；当前 diff 只修公开测试边界，`expectation` 继续只作合同验收资产单列。
真实自检：
- 未新增 spec 未定义的公开接口，也未回退 `kernel_gen.passes.tile` 的公开模块边界。
- 测试不再把 `__all__` 当成公开 API；当前只验证 spec 已定义模块可达性与未定义名字不可达。
- 未跨文件调用非公开 API，未修改 `expectation`，未扩修与本轮无关的资产失败。
结论：
- 当前 build 已完成，可续接 `review`。
- review 指出的 `__all__` 测试边界问题已收口；`img2col` 既有失败继续隔离在未改动资产文件外。

---

时间：2026-04-26 22:32:33 +0800
经办人：朽木露琪亚
任务：T-20260426-5caa70b5 / S3 review
任务目标：复核 `public_name.py` 这轮“公开测试边界复修”是否已真正收口为只验证 spec 定义的公开对象可达、可调用与旧 compat 名称不可达，并确认相关 spec / pytest 不再回退。
执行前阅读记录：已读 [TODO.md](/home/lfr/kernelcode_generate/TODO.md) 当前任务行、[ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md) S3 正文、[AGENTS.md](/home/lfr/kernelcode_generate/AGENTS.md)、本任务前序 build / review 记录，以及 [spec/pass/lowering/nn_lowering/spec.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md)、[test/pass/nn_lowering/public_name.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py)、[test/pass/nn_lowering/test_nn_lowering_asset_cases.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py) 现场。
改动：
- 审查结论为 `需修改`，未改代码。
- 发现 [test/pass/nn_lowering/public_name.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py) 的 `TC-PASS-NNL-003` 仍通过 `type(pattern)` 列表和 reject pattern 类型差异锁定私有实现类身份，未完全收成“只测 spec 定义的公开对象可达、可调用与旧 compat 名称不可达”。
- 发现 [test/pass/nn_lowering/public_name.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py) 的 `TC-PASS-NNL-004` 已从“验证 `NnLoweringPass.apply(...)` 直接使用 `PatternRewriteWalker + GreedyRewritePatternApplier + nn_lowering_patterns()` 驱动改写”弱化成只验证 `nn.add` lowering 结果，无法继续覆盖 [spec/pass/lowering/nn_lowering/spec.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md) 中对 driver 形态的硬约束。
- 发现 [spec/pass/lowering/nn_lowering/spec.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md) 的测试索引仍挂着已删除的 [test/pass/nn_lowering/test_nn_lowering_private_helpers.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_private_helpers.py) 与旧用例名 `test_nn_lowering_patterns_register_reject_last`，与本轮“公开测试边界复修”的真实现场不一致。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_nn_lowering_asset_cases.py -k 'public_name or compose_public_family_exports or pattern_driver' -ra` -> `9 passed, 24 deselected, 1 warning`
- `git -C /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis diff --check` -> 通过
- 文本核对：
  - [test/pass/nn_lowering/public_name.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py):143-155 仍以 `type(pattern)` / reject 类型差异断言内部实现身份
  - [test/pass/nn_lowering/public_name.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py):187-203 只验证 `nn.add` lowering 结果，不再验证 driver 直接消费 `nn_lowering_patterns()`
  - [spec/pass/lowering/nn_lowering/spec.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md):24-27 仍引用已删除测试文件；[spec/pass/lowering/nn_lowering/spec.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md):322 仍写旧用例名
Diff 反推审查：
- 本轮被审 residual diff 事实入口是 [test/pass/nn_lowering/public_name.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py)，其桥接收集入口是 [test/pass/nn_lowering/test_nn_lowering_asset_cases.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py)；因此反推复跑上述两份 pytest，并补做对应 spec 文本核对。
- 复跑结果说明：当前测试能通过，但通过条件已经弱化或仍掺入私有实现身份断言，不能证明“公开测试边界复修”真正达成。
- 本轮未执行 `expectation`；其仍只属于合同验收资产，不计入 diff 反推审查。
自检：
- 已逐项审查当前 residual diff 及其对应 spec / pytest 入口；特殊情况、边界、可维护性、测试有效性与文档一致性已检查。
- 本轮未越权修改 `expectation` 或其他不在审查范围内的文件；仅记录审查结论。
- 发现 3 个可执行的最小需改项，已全部写明；按审查规则本轮结论只能是 `需修改`。
结论：
- `需修改`。下一步应回到 `build`：
  1. 将 `TC-PASS-NNL-003` 收成只依赖 spec 定义的公开对象可达、可调用与旧 compat 名称不可达，不再锁定 `type(pattern)` 等私有类身份；
  2. 为 `TC-PASS-NNL-004` 恢复对 “`apply(...)` 直接使用 `nn_lowering_patterns()` driver” 的合同覆盖，但测试入口仍需保持在公开 API 边界内；
  3. 同步修正 [spec/pass/lowering/nn_lowering/spec.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md) 中已删除 / 已改名的测试索引。

---

时间：2026-04-26 22:37:08 +0800
经办人：朽木露琪亚
任务：T-20260426-5caa70b5 / S3 build 修复回合
任务目标：收口 `nn_lowering public_name` 公开测试边界残留问题：1）`TC-PASS-NNL-003` 不再锁私有 pattern 类型身份；2）`TC-PASS-NNL-004` 恢复对 `apply(...)` 直接使用 `nn_lowering_patterns()` driver 的合同覆盖；3）同步修正 `spec/pass/lowering/nn_lowering/spec.md` 中已删除 / 已改名测试索引。
执行前阅读记录：已读 [TODO.md](/home/lfr/kernelcode_generate/TODO.md) 当前任务行、[ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md) S3 正文、[AGENTS.md](/home/lfr/kernelcode_generate/AGENTS.md)、同一记录文件中的前序 build / review 结论，并复核 [test/pass/nn_lowering/public_name.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py)、[test/pass/nn_lowering/test_nn_lowering_asset_cases.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py)、[spec/pass/lowering/nn_lowering/spec.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md) 当前现场。
最小功能闭环：
- `TC-PASS-NNL-003` 继续验证 `nn_lowering_patterns()` 的公开组合顺序，但只借 child family 的公开 `*_patterns()` 入口观测顺序，不再用 `type(pattern)` / reject 类型差异锁定私有类身份。
- `TC-PASS-NNL-004` 继续验证 `apply(...)` 直接使用 `nn_lowering_patterns()` driver，但只通过 monkeypatch 公开 `*_patterns()` 入口注入可观测 sentinel，不再借私有 driver 类或实现子模块细节。
- `spec` 中与这轮改动直接相关的测试文件列表、执行命令和用例名与当前真实 pytest 入口保持一致。
改动：
- 更新 [test/pass/nn_lowering/public_name.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py)，将 `TC-PASS-NNL-003` 改为 monkeypatch 各 child family 公开 `*_patterns()` 函数并比对返回 token 顺序，只验证公开组合顺序和 reject-last，不再断言私有 `type(pattern)` 身份。
- 同文件中将 `TC-PASS-NNL-004` 改为仅 monkeypatch 公开 `element_binary_patterns()` 等入口，向 `apply(...)` 注入 sentinel `RewritePattern` 并用异常证明 `NnLoweringPass.apply(...)` 直接消费了由公开 family 入口组合出的 driver；不再退化成只看 `nn.add` lowering 结果。
- 更新 [spec/pass/lowering/nn_lowering/spec.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md)，把已删除的 `test_nn_lowering_private_helpers.py` 索引替换为当前 collectable 入口 `test_nn_lowering_asset_cases.py`，同步修正 `TC-PASS-NNL-003` 的用例名和 `TC-PASS-NNL-005` 的测试索引表述。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_nn_lowering_asset_cases.py -k 'public_name or compose_public_family_exports or pattern_driver' -ra` -> `9 passed, 24 deselected, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/test_pass_registry.py test/pass/test_pass_manager.py test/pass/test_dma_memory_hierarchy.py test/pass/tile/test_package.py test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_nn_lowering_asset_cases.py -k 'not img2col' -ra` -> `84 passed, 4 deselected, 1 warning`
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py` -> 通过
- `rg -n "test_nn_lowering_private_helpers|test_nn_lowering_patterns_register_reject_last" /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md` -> 无命中
- `git -C /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis diff --check` -> 通过
Diff 反推自测：
- 本轮 diff 直接落在 [test/pass/nn_lowering/public_name.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py) 与 [spec/pass/lowering/nn_lowering/spec.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md)；因此反推测试复跑 `public_name.py` 全量与 [test/pass/nn_lowering/test_nn_lowering_asset_cases.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py) 中桥接 `compose_public_family_exports / pattern_driver` 的 collectable 入口。
- 额外回归 `test_pass_registry.py`、`test_pass_manager.py`、`test_dma_memory_hierarchy.py`、`test/pass/tile/test_package.py` 与 `nn_lowering` 公开入口的 `not img2col` 集合，只用于确认本轮 public-boundary 修复没有把同链路公开接口回退；结果通过。
- 本轮未把 `img2col` 既有失败纳入通过条件，也未把 `expectation` 算入 diff 反推测试。
合同验收（如适用）：未执行；`expectation` 继续只作合同验收资产单列，本轮未修改也未引用其通过性作为自测证据。
自检：
- 已读完整阶段；未越权修改 `expectation` 或非当前范围文件；本轮闭环只收 `public_name` 公开测试边界和直接关联 `spec` 索引。
- 没有新增 `spec` 未定义的公开 API；测试仍只连接 package-root `kernel_gen.passes.lowering.nn_lowering` 与 child family 的公开 `*_patterns()` 入口，没有跨文件调用当前文件之外的非公开 API。
- `TC-PASS-NNL-003` 与 `TC-PASS-NNL-004` 的断言现在都基于公开可观测行为：前者观察公开 family 组合顺序，后者通过公开 family sentinel 证明 `apply(...)` 消费 driver；没有再用私有 pattern 类型身份或私有 driver 类名做验收面。
- 注释、用例名和 `spec` 测试索引已与当前实现和 pytest 入口同步；未发现本轮 residual diff 的已知逻辑回退、边界漏测或文档失真。
结论：
- 当前 build 已完成，可以续接 `review`。
- 前一轮 review 提出的 3 个最小需改项已收口；`img2col` 既有失败继续隔离在未改动资产文件外。

---

时间：2026-04-26 23:08:00 +0800
经办人：不要啊教练
任务：T-20260426-5caa70b5 / review
任务目标：复核 `nn_lowering public_name` 公开测试边界返修，确认 1）`TC-PASS-NNL-003` 只经公开 `*_patterns()` 入口观测组合顺序；2）`TC-PASS-NNL-004` 仍覆盖 `apply(...)` 直接消费 `nn_lowering_patterns()` driver；3）`spec/pass/lowering/nn_lowering/spec.md` 的已删除 / 已改名测试索引已同步，并确认 `img2col` 现存失败不属于当前 diff。
执行前阅读记录：已读 [TODO.md](/home/lfr/kernelcode_generate/TODO.md) 当前任务行、[ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md) S3 正文、[AGENTS.md](/home/lfr/kernelcode_generate/AGENTS.md)、当前任务记录中的前序 build / review 结论，并复核 [test/pass/nn_lowering/public_name.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py)、[test/pass/nn_lowering/test_nn_lowering_asset_cases.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py)、[kernel_gen/passes/lowering/nn_lowering/__init__.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/__init__.py)、[kernel_gen/passes/lowering/nn_lowering/nn_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)、[spec/pass/lowering/nn_lowering/spec.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md) 现场。

### 真实审查
1. [`test/pass/nn_lowering/public_name.py:195`](../../../../../../../test/pass/nn_lowering/public_name.py#L195) 到 [`test/pass/nn_lowering/public_name.py:216`](../../../../../../../test/pass/nn_lowering/public_name.py#L216)
   - `TC-PASS-NNL-004` 现在通过 monkeypatch 各 child family 公开 `*_patterns()` 入口，并在 `element_binary_patterns()` 中注入 sentinel pattern 后调用 `NnLoweringPass().apply(...)`。
   - 这能证明 `apply(...)` 会消费某组公开 family patterns，但还不能证明它“必须直接调用公开 `nn_lowering_patterns()` driver”。如果后续有人把 [`kernel_gen/passes/lowering/nn_lowering/nn_lowering.py:939`](../../../../../../../kernel_gen/passes/lowering/nn_lowering/nn_lowering.py#L939) 到 [`:949`](../../../../../../../kernel_gen/passes/lowering/nn_lowering/nn_lowering.py#L949) 的 `nn_lowering_patterns()` 调用改回内联 family 组装，这条测试仍会通过。
   - 这与 [spec/pass/lowering/nn_lowering/spec.md:56](../../../../../../../spec/pass/lowering/nn_lowering/spec.md#L56)、[spec/pass/lowering/nn_lowering/spec.md:169](../../../../../../../spec/pass/lowering/nn_lowering/spec.md#L169)、[spec/pass/lowering/nn_lowering/spec.md:305](../../../../../../../spec/pass/lowering/nn_lowering/spec.md#L305) 写明的“`apply(...)` 必须直接消费 `nn_lowering_patterns()` driver”还差最后一层合同锁定。
2. [`test/pass/nn_lowering/public_name.py:137`](../../../../../../../test/pass/nn_lowering/public_name.py#L137) 到 [`:163`](../../../../../../../test/pass/nn_lowering/public_name.py#L163)
   - `TC-PASS-NNL-003` 已改成只经公开 `*_patterns()` 入口观测组合顺序，不再用 `type(pattern)` 锁私有实现类身份；这一条已对齐当前公开边界。
3. [spec/pass/lowering/nn_lowering/spec.md:24](../../../../../../../spec/pass/lowering/nn_lowering/spec.md#L24) 到 [`:27`](../../../../../../../spec/pass/lowering/nn_lowering/spec.md#L27)、[spec/pass/lowering/nn_lowering/spec.md:293](../../../../../../../spec/pass/lowering/nn_lowering/spec.md#L293) 到 [`:299`](../../../../../../../spec/pass/lowering/nn_lowering/spec.md#L299)、[spec/pass/lowering/nn_lowering/spec.md:322](../../../../../../../spec/pass/lowering/nn_lowering/spec.md#L322) 到 [`:323`](../../../../../../../spec/pass/lowering/nn_lowering/spec.md#L323)
   - 已删除 / 已改名测试索引已同步到 `public_name.py` 与 `test_nn_lowering_asset_cases.py`，旧 `test_nn_lowering_private_helpers.py` 与旧用例名不再残留。
4. `img2col` 既有失败仍固定在未改动资产文件 [test/pass/nn_lowering/img2col1d.py](../../../../../../../test/pass/nn_lowering/img2col1d.py) 与 [test/pass/nn_lowering/img2col2d.py](../../../../../../../test/pass/nn_lowering/img2col2d.py)，未回流到本轮 diff。

### Diff 反推审查
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_nn_lowering_asset_cases.py -k 'test_nn_lowering_patterns_compose_public_family_exports or test_nn_lowering_apply_uses_pattern_driver or test_nn_lowering_pass_public_name or test_nn_lowering_pass_public_exports or test_nn_lowering_child_pattern_exports' -ra` -> `9 passed, 24 deselected, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/test_pass_registry.py test/pass/test_pass_manager.py test/pass/test_dma_memory_hierarchy.py test/pass/tile/test_package.py test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_nn_lowering_asset_cases.py -k 'not img2col' -ra` -> `84 passed, 4 deselected, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/img2col1d.py::test_nn_lowering_img2col1d_accepts_noncanonical_symbol_names test/pass/nn_lowering/img2col2d.py::test_nn_lowering_img2col2d_accepts_noncanonical_symbol_names -ra` -> `2 failed, 1 warning`
- `git -C /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis diff --check` -> 通过

### 合同验收（如适用）
- 本轮未执行 `expectation`；其继续只作合同验收资产单列，不计入 diff 反推审查。

### 自检
- 已检查 spec、实现、测试三侧的公开 API 边界、跨文件非公开 API 使用和测试直连未定义公开接口情况。
- 本轮没有新增未在 spec 定义的公开接口；`TC-PASS-NNL-003` 与索引同步项已收口。
- 仍存在 1 个可执行改进点：`TC-PASS-NNL-004` 没有真正锁住 `apply(...) -> nn_lowering_patterns()` 这条公开 driver 合同。

### 可改进点
- 将 `TC-PASS-NNL-004` 收紧为直接围绕公开 `nn_lowering_patterns()` 做可观测约束，例如 monkeypatch 包级 `nn_lowering_patterns` 或通过只替换该公开函数返回 sentinel pattern 列表来证明 `apply(...)` 必须调用它，而不是允许实现把 family 组装内联后测试仍然通过。

### 结论
- `需修改`。
- `TC-PASS-NNL-003` 与 spec 索引同步已经收口，但 `TC-PASS-NNL-004` 仍未直接证明 `apply(...)` 消费的是公开 `nn_lowering_patterns()` driver；`img2col` 既有失败继续隔离在未改动资产文件外。

---

时间：2026-04-26 22:43:13 +0800
经办人：jcc你莫辜负
任务：T-20260426-5caa70b5 / S3 build 返修
任务目标：按最新 review 退回口径收口 `TC-PASS-NNL-004`，直接锁住 `NnLoweringPass.apply(...)` 必须消费公开 `nn_lowering_patterns()` driver，并确认 `img2col` 既有失败继续隔离在当前 diff 外。
执行前阅读记录：已读 [TODO.md](/home/lfr/kernelcode_generate/TODO.md) 当前任务行、[ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md) S3 正文、[AGENTS.md](/home/lfr/kernelcode_generate/AGENTS.md)、当前任务记录中的前序 build / review 结论，并复核 [kernel_gen/passes/lowering/nn_lowering/nn_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)、[kernel_gen/passes/lowering/nn_lowering/__init__.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/__init__.py)、[test/pass/nn_lowering/public_name.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py) 和 [spec/pass/lowering/nn_lowering/spec.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md) 的当前现场。
最小功能闭环：
- `NnLoweringPass.apply(...)` 现在通过 canonical public path 取得 `nn_lowering_patterns()`，不再只靠同文件局部名字解析。
- `TC-PASS-NNL-004` 直接 monkeypatch 包级公开 `nn_lowering_patterns()`，并用 sentinel pattern 证明 `apply(...)` 必须消费这个公开 driver。
- 本轮只收 `nn_lowering` public driver 合同，不扩到 `img2col` 既有资产失败、`expectation` 或其它 pass family。
改动：
- 更新 [kernel_gen/passes/lowering/nn_lowering/nn_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)，为 `NnLoweringPass.apply(...)` 补齐完整函数注释，并将 driver 获取方式改为 `from kernel_gen.passes.lowering import nn_lowering as nn_lowering_pkg` 后调用 `nn_lowering_pkg.nn_lowering_patterns()`；这样 `apply(...)` 的实际行为与 `spec` 约定的 canonical public driver 保持同一入口。
- 更新 [test/pass/nn_lowering/public_name.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py)，将 `TC-PASS-NNL-004` 改成直接 monkeypatch 公开 `nn_lowering_pkg.nn_lowering_patterns` 并返回 sentinel `RewritePattern`；调用 `NnLoweringPass().apply(...)` 时现在必须抛出 sentinel，才能证明 `apply(...)` 直接消费的是公开 driver，而不是内联 family 组装。同步更新文件头与该测试块的 `最后一次更改`。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_nn_lowering_asset_cases.py -k 'test_nn_lowering_patterns_compose_public_family_exports or test_nn_lowering_apply_uses_pattern_driver or test_nn_lowering_pass_public_name or test_nn_lowering_pass_public_exports or test_nn_lowering_child_pattern_exports' -ra` -> `9 passed, 24 deselected, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -ra` -> `42 passed, 2 warnings`
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/nn_lowering.py /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py` -> 通过
- `git -C /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis diff --check` -> 通过
Diff 反推自测：
- 对应 [test/pass/nn_lowering/public_name.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py) 与 [kernel_gen/passes/lowering/nn_lowering/nn_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/nn_lowering.py) 的当前 diff，已反推 `pytest -q test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_nn_lowering_asset_cases.py -k 'test_nn_lowering_patterns_compose_public_family_exports or test_nn_lowering_apply_uses_pattern_driver or test_nn_lowering_pass_public_name or test_nn_lowering_pass_public_exports or test_nn_lowering_child_pattern_exports' -ra`，结果 `9 passed, 24 deselected, 1 warning`，覆盖 `TC-PASS-NNL-003/004` 与 package-root 公开导出。
- 对应 `apply(...)` 实现改动，已反推 `pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -ra`，结果 `42 passed, 2 warnings`，确认 pass 实际 lowering 行为未回退。
- 对应当前改动实现/测试文件，已反推 `python3 -m py_compile .../nn_lowering.py .../public_name.py`，结果通过。
- 对应当前 residual diff，已反推 `git diff --check`，结果通过。
合同验收（如适用）：未执行；`expectation` 继续只作合同验收资产单列，本轮未修改也未把其通过性作为自测证据。
自检：
- 本轮没有新增 `spec` 未定义的公开接口；只是让 `apply(...)` 的实现与已有公开 `nn_lowering_patterns()` 合同对齐。
- 没有跨文件调用非公开 API；`apply(...)` 改为通过 canonical public path 获取 driver，测试也只 monkeypatch 包级公开 `nn_lowering_patterns()`。
- 修改了功能实现文件，已同步为 `apply(...)` 补齐完整函数注释；文件级 `API 列表` 保持不变，因为公开接口集合未变化。
- 未改动 `expectation`，未扩修 `img2col` 既有失败，也未把这些资产算入本轮 diff 反推测试。
结论：
- 当前 build 已完成，可续接 `review`。
- `TC-PASS-NNL-004` 现在已直接锁住 `apply(...) -> nn_lowering_patterns()` 这条公开 driver 合同；若后续有人把 family 组装内联回 `apply(...)`，当前测试会直接失效。

---

时间：2026-04-26 23:15:00 +0800
经办人：不要啊教练
任务：T-20260426-5caa70b5 / review
任务目标：复核 S3 `nn_lowering` public driver 返修，确认 `TC-PASS-NNL-004` 已直接锁住 `NnLoweringPass.apply(...)` 必须消费公开 `nn_lowering_patterns()`，并确认 `test_lowering_nn_lowering` 现有 lowering 行为未回退。
执行前阅读记录：已读 [TODO.md](/home/lfr/kernelcode_generate/TODO.md) 当前任务行、[ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md) S3 正文、[AGENTS.md](/home/lfr/kernelcode_generate/AGENTS.md)、当前任务记录中的前序 build / review 结论，并复核 [kernel_gen/passes/lowering/nn_lowering/nn_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)、[test/pass/nn_lowering/public_name.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py)、[test/pass/nn_lowering/test_nn_lowering_asset_cases.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py)、[test/pass/nn_lowering/test_lowering_nn_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_lowering_nn_lowering.py)、[spec/pass/lowering/nn_lowering/spec.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md) 现场。

### 真实审查
1. [`test/pass/nn_lowering/public_name.py:195`](../../../../../../../test/pass/nn_lowering/public_name.py#L195) 到 [`:212`](../../../../../../../test/pass/nn_lowering/public_name.py#L212)
   - `TC-PASS-NNL-004` 本轮已直接 monkeypatch 包级公开 `nn_lowering_pkg.nn_lowering_patterns`，并通过 sentinel pattern 证明 `NnLoweringPass.apply(...)` 必须消费公开 `nn_lowering_patterns()` driver。
   - 配合实现现场 [`kernel_gen/passes/lowering/nn_lowering/nn_lowering.py:958`](../../../../../../../kernel_gen/passes/lowering/nn_lowering/nn_lowering.py#L958) 到 [`:962`](../../../../../../../kernel_gen/passes/lowering/nn_lowering/nn_lowering.py#L962)，这一条合同已收口。
2. [`test/pass/nn_lowering/test_nn_lowering_asset_cases.py:109`](../../../../../../../test/pass/nn_lowering/test_nn_lowering_asset_cases.py#L109) 到 [`:128`](../../../../../../../test/pass/nn_lowering/test_nn_lowering_asset_cases.py#L128)、[`test/pass/nn_lowering/test_nn_lowering_asset_cases.py:131`](../../../../../../../test/pass/nn_lowering/test_nn_lowering_asset_cases.py#L131) 到 [`:152`](../../../../../../../test/pass/nn_lowering/test_nn_lowering_asset_cases.py#L152)
   - 这里仍通过 `public_name_cases.test_nn_lowering_apply_uses_pattern_driver(...)` 和 `public_name_cases.test_nn_lowering_patterns_compose_public_family_exports(...)` 跨文件直接调用 `public_name.py` 里的测试函数。
   - 这些测试函数不是 [spec/pass/lowering/nn_lowering/spec.md](../../../../../../../spec/pass/lowering/nn_lowering/spec.md) 定义的公开 API，也不是任何文件级 `API 列表` 声明的对外接口。按最新审查规则，这属于测试直连当前文件之外的非公开接口，不能通过。
   - 即使本轮功能目标达成，这条资产桥接仍把“测试实现细节”当成可复用接口，公开边界未闭合。
3. `test_lowering_nn_lowering` 现有 lowering 行为未回退：`42 passed`，`img2col` 既有失败也没有回流到当前 diff。

### Diff 反推审查
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_nn_lowering_asset_cases.py -k 'test_nn_lowering_patterns_compose_public_family_exports or test_nn_lowering_apply_uses_pattern_driver or test_nn_lowering_pass_public_name or test_nn_lowering_pass_public_exports or test_nn_lowering_child_pattern_exports' -ra` -> `9 passed, 24 deselected, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py -ra` -> `42 passed, 2 warnings`
- `git -C /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis diff --check` -> 通过

### 合同验收（如适用）
- 本轮未执行 `expectation`；其继续只作合同验收资产单列，不计入 diff 反推审查。

### 自检
- 已核对本轮 public driver 修复、公开 API 边界、跨文件非公开 API 使用和测试直连非公开接口情况。
- `TC-PASS-NNL-004` 的目标合同已达成，但 `test_nn_lowering_asset_cases.py` 仍在跨文件复用非公开测试函数，属于新的明确阻断项。
- 本轮未越权修改 `expectation` 或其它不在审查范围内的文件。

### 可改进点
- 将 `test_nn_lowering_asset_cases.py` 中依赖 fixture 的 case 收成真正的 collectable 公开测试入口，不要直接调用 `public_name.py` 里的测试函数；可以抽取共享测试 helper 到同文件私有 helper，或把需要 collect 的断言直接内联到 asset case 文件内，但不能把测试函数本身当跨文件接口复用。

### 结论
- `需修改`。
- `TC-PASS-NNL-004` 已直接锁住 `apply(...) -> nn_lowering_patterns()`，`test_lowering_nn_lowering` 行为也未回退；当前阻断点变为 `test_nn_lowering_asset_cases.py` 跨文件直连 `public_name.py` 的测试函数，违反公开 API / 测试边界规则。

---

时间：2026-04-26 22:54:26 +0800
经办人：朽木露琪亚
任务：T-20260426-5caa70b5 / S3 build 复修
任务目标：修复 [test/pass/nn_lowering/test_nn_lowering_asset_cases.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py) 仍跨文件直接调用 [test/pass/nn_lowering/public_name.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py) 测试函数的问题，使 collectable 资产入口不再直连当前文件之外的非公开测试接口。
执行前阅读记录：已读 [TODO.md](/home/lfr/kernelcode_generate/TODO.md) 当前任务行、[ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md) S3 正文、[AGENTS.md](/home/lfr/kernelcode_generate/AGENTS.md)、当前任务记录中的前序 build / review 结论，并复核 [test/pass/nn_lowering/test_nn_lowering_asset_cases.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py) 与 [test/pass/nn_lowering/public_name.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py) 当前现场。
最小功能闭环：
- `test_nn_lowering_asset_cases.py` 只桥接非 `test_*.py` 资产 case。
- `public_name.py` 继续独立作为 collectable pytest 文件承担公开合同测试。
- 本轮不扩大到 `img2col` 既有失败，也不改 `expectation`。
改动：
- 删除 [test/pass/nn_lowering/test_nn_lowering_asset_cases.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py) 中的 `public_name_cases` 跨文件导入。
- 从 `ASSET_CASES` 中删除 `public_name::test_nn_lowering_pass_public_exports`、`public_name::test_nn_lowering_pass_public_name` 与 `public_name::test_nn_lowering_patterns_register_reject_last`。
- 删除本文件中跨文件包装 `public_name.py` 测试函数的 asset wrapper，用 collectable 公开测试入口和 asset case 入口分离职责。
- 同步更新文件头 `最后一次更改` 与文件级功能说明，明确已经是 `test_*.py` 的 collectable 公开测试文件不再通过本文件跨文件复用测试函数。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/public_name.py -ra` -> `5 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/test_nn_lowering_asset_cases.py -k 'not img2col' -ra` -> `20 passed, 4 deselected, 1 warning`
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py` -> 通过
- `rg -n "public_name_cases|public_name::|test_nn_lowering_apply_uses_pattern_driver_asset|test_nn_lowering_patterns_compose_public_family_exports_asset" /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py` -> 无命中
- `git -C /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis diff --check` -> 通过
Diff 反推自测：
- 当前 diff 只改 [test/pass/nn_lowering/test_nn_lowering_asset_cases.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py)，已反推 `pytest -q test/pass/nn_lowering/public_name.py -ra`，确认公开合同测试继续独立收集并通过，结果 `5 passed, 1 warning`。
- 已反推 `pytest -q test/pass/nn_lowering/test_nn_lowering_asset_cases.py -k 'not img2col' -ra`，确认移除跨文件测试函数复用后，剩余资产入口仍可收集并通过，结果 `20 passed, 4 deselected, 1 warning`。
- 已反推 `python3 -m py_compile .../test_nn_lowering_asset_cases.py`，确认当前测试文件语法通过。
- 已反推 `rg -n "public_name_cases|public_name::|test_nn_lowering_apply_uses_pattern_driver_asset|test_nn_lowering_patterns_compose_public_family_exports_asset" .../test_nn_lowering_asset_cases.py`，确认残留跨文件直连标记清零。
- 已反推 `git diff --check`，确认当前 residual diff 无格式问题。
合同验收（如适用）：
- 本轮未执行 `expectation`；其继续只作合同验收资产单列，不计入 diff 反推自测。
真实自检：
- 未修改 `expectation` 或其它超出当前 review 退回边界的文件。
- 未新增 `spec` 未定义公开 API，也未新增跨文件 helper；本轮只移除测试对当前文件之外非公开测试接口的直连。
- `public_name.py` 与 `test_nn_lowering_asset_cases.py` 的职责已分离：前者承担 collectable 公开合同测试，后者只桥接非 `test_*.py` 资产 case。
- 未发现本轮修复引入的回归、冗余包装或额外公开测试边界泄漏。
结论：
- 当前 build 已完成，可续接 `review`。
- 本轮 review 指出的跨文件测试函数直连问题已收口。

---

时间：2026-04-26 23:12:00 +0800
经办人：提莫炖蘑菇
任务：T-20260426-5caa70b5 / S3 review 复审回合
任务目标：复核 [test/pass/nn_lowering/test_nn_lowering_asset_cases.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py) 已不再跨文件直接调用 [test/pass/nn_lowering/public_name.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py) 测试函数，确认 collectable 资产入口只桥接非 `test_*.py` 资产 case，且 `public_name.py` 继续独立承担公开合同测试。
执行前阅读记录：
- 已读 [TODO.md](/home/lfr/kernelcode_generate/TODO.md) 当前任务行、[ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md) S3 正文 / 完成态 / 验收设计、当前任务记录中的前序 build / review 记录与 [AGENTS.md](/home/lfr/kernelcode_generate/AGENTS.md)。
- 已复核 [test/pass/nn_lowering/public_name.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py)、[test/pass/nn_lowering/test_nn_lowering_asset_cases.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py)、[spec/pass/lowering/nn_lowering/spec.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md) 与当前 residual diff 文件集现场。
真实审查：
- [test/pass/nn_lowering/test_nn_lowering_asset_cases.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py) 里的 `public_name_cases` 跨文件导入已经移除；当前 `ASSET_CASES` 只桥接 `cast.py`、`exp.py`、`img2col1d.py`、`img2col2d.py`、`matmul.py`、`select.py` 这类非 `test_*.py` 资产 case。
- [test/pass/nn_lowering/public_name.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py) 继续作为独立 collectable pytest 承担 `NnLoweringPass` 公开合同测试；单独入口已通过。
- 但 collectable 资产入口本身仍未闭环：直接运行 [test/pass/nn_lowering/test_nn_lowering_asset_cases.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py) 会稳定失败在 `img2col1d/2d accepts_noncanonical_symbol_names` 两个 case 上，因此“资产入口只桥接非 test_*.py 资产 case”虽然成立，但“该 collectable 资产入口可直接作为公开 pytest 入口使用”仍不成立。
- 当前 build 记录只复跑了 `-k 'not img2col'` 子集；而 [spec/pass/lowering/nn_lowering/spec.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md) 的执行命令仍写 `pytest -q test/pass/nn_lowering/test_nn_lowering_asset_cases.py` 整体入口，这和现场真实状态不一致。
Diff 反推审查：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/public_name.py -ra` -> `5 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/test_nn_lowering_asset_cases.py -ra` -> `2 failed, 22 passed, 1 warning`
- `git -C /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis diff --check` -> 通过
合同验收（如适用）：
- 本轮未执行 `expectation`；其继续只作合同验收资产单列，不计入 diff 反推审查。
自检：
- 已按最新规则核对：是否新增 spec 未定义的公开接口、是否跨文件调用非公开 API、测试是否直连非 API 接口、文件级 / spec API 边界是否回退。
- 当前跨文件直连 `public_name.py` 测试函数的问题已收住；本轮阻断点变成 collectable 资产入口的真实可执行性与 spec 执行命令不一致。
- 未修改 `expectation` 或其它超出当前 review 范围的文件。
可改进点：
- 若 `img2col1d/2d accepts_noncanonical_symbol_names` 仍属已知未收口资产，就不应继续把整个 [test/pass/nn_lowering/test_nn_lowering_asset_cases.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py) 宣称为当前可直接执行的 collectable 公开入口；至少要么先把这两例修绿，要么把执行命令 / 收集范围改成与现场一致的可通过子集。
结论：
- `需修改`。
- `public_name.py` 的独立公开合同测试职责已与资产桥接入口分离，但 `test_nn_lowering_asset_cases.py` 作为 collectable 资产入口仍然不是当前可直接执行的绿色公开 pytest 入口，本轮还不能通过。

---

时间：2026-04-26 23:32:00 +0800
经办人：金铲铲大作战
任务：T-20260426-5caa70b5 / S3 build 复修
任务目标：收口 [test/pass/nn_lowering/test_nn_lowering_asset_cases.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py) 的 collectable 公开入口边界，使其直接运行转绿，并同步 [spec/pass/lowering/nn_lowering/spec.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md) 的执行命令与测试范围表述。
执行前阅读记录：已读 [TODO.md](/home/lfr/kernelcode_generate/TODO.md) 当前任务行、[ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md) S3 正文、[AGENTS.md](/home/lfr/kernelcode_generate/AGENTS.md)、当前任务记录中的前序 build / review 结论，并复核 [test/pass/nn_lowering/test_nn_lowering_asset_cases.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py)、[spec/pass/lowering/nn_lowering/spec.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md)、[test/pass/nn_lowering/img2col1d.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/img2col1d.py)、[test/pass/nn_lowering/img2col2d.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/img2col2d.py) 当前现场。
最小功能闭环：
- `test_nn_lowering_asset_cases.py` 作为 collectable 公开入口直接运行必须转绿。
- 入口范围只保留当前可直接通过的非 `test_*.py` 资产 case。
- `spec` 的执行命令和 `TC-PASS-NNL-005` 表述与这一公开入口范围保持一致。
改动：
- 更新 [test/pass/nn_lowering/test_nn_lowering_asset_cases.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py)，从 `ASSET_CASES` 中移除 `img2col1d/2d accepts_noncanonical_symbol_names` 两例，并同步文件头与 `test_nn_lowering_asset_case(...)` 的功能说明 / 元数据，明确 collectable 入口只桥接当前可直接通过的非 `test_*.py` 资产 case。
- 更新 [spec/pass/lowering/nn_lowering/spec.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md)，保持 `pytest -q test/pass/nn_lowering/test_nn_lowering_asset_cases.py` 为当前可直接执行的公开命令，并把 `TC-PASS-NNL-005` 与测试目标同步改成“当前已纳入 collectable 入口的非 `test_*.py` helper / boundary case”；同时单列说明 `img2col1d/2d accepts_noncanonical_symbol_names` 继续由各自资产文件维护，不属于本入口范围。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/test_nn_lowering_asset_cases.py -ra` -> `22 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_nn_lowering_asset_cases.py -ra` -> `27 passed, 1 warning`
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py` -> 通过
- `git -C /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis diff --check` -> 通过
Diff 反推自测：
- 本轮 diff 直接落在 [test/pass/nn_lowering/test_nn_lowering_asset_cases.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py) 与 [spec/pass/lowering/nn_lowering/spec.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md)；反推测试入口因此直接复跑 `pytest -q test/pass/nn_lowering/test_nn_lowering_asset_cases.py -ra`，确认 collectable 公开入口已可直接执行并转绿。
- 额外复跑 `pytest -q test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_nn_lowering_asset_cases.py -ra`，确认公开合同测试与 collectable 资产入口同时通过，且没有再跨文件复用测试函数。
- 当前 diff 不涉及 `img2col1d.py` / `img2col2d.py` 实现或其单独资产用例，本轮未把这两条 standalone case 纳入通过条件。
合同验收（如适用）：
- 本轮未执行 `expectation`；`expectation` 继续只作合同验收资产单列，不计入 diff 反推自测。
真实自检：
- 未修改 `expectation` 或其它超出当前 review 退回边界的文件。
- 没有新增 `spec` 未定义的公开接口，也没有跨文件调用当前文件之外的非公开 API；测试仍只走 collectable 公开入口与独立公开 pytest 文件。
- `test_nn_lowering_asset_cases.py` 现在可以作为当前现场的绿色公开 collectable 入口直接运行；`spec` 执行命令和测试目标已与之对齐。
- `img2col1d/2d accepts_noncanonical_symbol_names` 仍保持 standalone 资产状态，没有在本轮被错误纳入公开入口或通过条件。
结论：
- 当前 build 已完成，可续接 `review`。

---

时间：2026-04-26 23:57:00 +0800
经办人：不要啊教练
任务：T-20260426-5caa70b5 / S3 review 复审回合
任务目标：复核 `nn_lowering public_name` 公开入口收口、`test_nn_lowering_asset_cases.py` collectable 入口范围与 `img2col` 隔离结果，并按当前 residual diff 继续核对 `passes / tile / dma_memory_hierarchy / registry / pass_manager` 的公开 API 边界。
执行前阅读记录：已读 [TODO.md](/home/lfr/kernelcode_generate/TODO.md) 当前任务行、[ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md) S3 正文 / 全局完成态 / 验收设计、[AGENTS.md](/home/lfr/kernelcode_generate/AGENTS.md)、当前任务记录中的前序 build / review 结论，并复核 [test/pass/nn_lowering/public_name.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py)、[test/pass/nn_lowering/test_nn_lowering_asset_cases.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py)、[test/pass/tile/test_package.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/tile/test_package.py)、[kernel_gen/passes/tile/__init__.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/tile/__init__.py)、[spec/pass/lowering/nn_lowering/spec.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md) 当前现场。
真实审查：
- [test/pass/nn_lowering/public_name.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py) 这轮已收口到公开边界：`TC-PASS-NNL-003` 只经 child family 的公开 `*_patterns()` 入口观测组合顺序，不再锁私有 pattern 类型身份；`TC-PASS-NNL-004` 也已改为直接 monkeypatch package-root 公开 `nn_lowering_patterns()`，明确锁定 `NnLoweringPass.apply(...)` 必须消费该公开 driver。
- [test/pass/nn_lowering/test_nn_lowering_asset_cases.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py) 当前 collectable 入口已剔除 standalone `img2col1d/2d accepts_noncanonical_symbol_names`，直接运行可转绿；[spec/pass/lowering/nn_lowering/spec.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md) 的执行命令与 `TC-PASS-NNL-005` 表述也已同步到当前公开入口范围。
- `img2col` 现存资产问题未回流到当前 collectable 入口；未改动的 standalone 资产仍在各自文件维护，不属于本轮通过条件。
- 但当前 residual diff 仍包含 [test/pass/tile/test_package.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/tile/test_package.py)，其中对 `tile_package.__all__` 的断言继续把未进入 `spec` / 文件级 `API 列表` 的模块元数据当成公开接口使用。按最新审查规则，这一项命中后本轮不能通过。
问题列表：
1. [test/pass/tile/test_package.py:51](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/tile/test_package.py:51)
   - 现象：`test_tile_package_exports_only_public_modules()` 仍直接断言 `tile_package.__all__ == ["analysis", "elewise", "reduce"]`。
   - 依据：当前文件级公开清单 [kernel_gen/passes/tile/__init__.py:12](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/tile/__init__.py:12) 到 [:15](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/tile/__init__.py:12) 只定义 `analysis: module`、`elewise: module`、`reduce: module`；对应 tile family spec 也只收公开模块与公开 pass / pattern 入口，没有把 `__all__` 定义为公开 API。
   - 风险：测试仍在直连未定义公开接口；如果后续实现用别的方式暴露同样的公开模块集，`__all__` 变化会造成与合同无关的假失败。
   - 建议：把该断言改成只验证 `tile_package.analysis / elewise / reduce` 三个公开模块对象可达、以及未定义名字不可达，不再把 `__all__` 当公开合同。
Diff 反推审查：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_nn_lowering_asset_cases.py test/pass/tile/test_package.py -ra` -> `30 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/test_pass_registry.py test/pass/test_pass_manager.py test/pass/test_dma_memory_hierarchy.py test/pass/tile/test_package.py test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_nn_lowering_asset_cases.py -ra` -> `82 passed, 1 warning`
- `git -C /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis diff --check` -> 通过
合同验收（如适用）：
- 本轮未执行 `expectation`；其继续只作合同验收资产单列，不计入 diff 反推审查。
可改进点：
- `nn_lowering public_name / asset_cases` 这一轮返修本身已经对齐公开边界；剩余收口点集中在 `tile package` 的 `__all__` 断言。只要把这一条未定义公开接口测试去掉或改成真正的公开模块可达性断言，当前 residual diff 才能进入下一步。
自检：
- 已按最新规则核对：是否新增 `spec` 未定义公开接口、是否跨文件调用非公开 API、测试是否直连非 API 接口、文件级 `API 列表` 与 spec 公开面是否回退。
- 本轮未越权修改 `expectation`、实现、`spec` 或测试；仅记录审查结论。
- 当前唯一剩余阻断点已可定位、可执行，结论只能为 `需修改`。
结论：
- `需修改`。
- `nn_lowering public_name`、`asset_cases` collectable 入口和 `img2col` 隔离结果都已收口；但当前 residual diff 仍有 [test/pass/tile/test_package.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/tile/test_package.py) 直连 `tile_package.__all__` 这一未定义公开接口，必须回到 `build` 收掉后再复审。

---

时间：2026-04-27 00:12:00 +0800
经办人：不要啊教练
任务：T-20260426-5caa70b5 / S3 review 复审回合
任务目标：复核 `tile package` 公开模块边界返修是否已收口，并继续检查当前 residual diff 对应的 `nn_lowering` 公开测试 / child spec / 文件说明是否与“删除 test_nn_lowering_private_helpers.py”后的现场一致。
执行前阅读记录：已读 [TODO.md](/home/lfr/kernelcode_generate/TODO.md) 当前任务行、[ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md) S3 正文 / 完成态 / 验收设计、[AGENTS.md](/home/lfr/kernelcode_generate/AGENTS.md)、当前任务记录中的前序 build / review 结论，并复核 [test/pass/tile/test_package.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/tile/test_package.py)、[test/pass/nn_lowering/public_name.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py)、[test/pass/nn_lowering/test_nn_lowering_asset_cases.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py)、[spec/pass/lowering/nn_lowering/spec.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md) 及删除 `test_nn_lowering_private_helpers.py` 后仍引用它的 child spec / 文件说明。
真实审查：
- [test/pass/tile/test_package.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/tile/test_package.py) 这轮已移除对 `tile_package.__all__` 的断言，当前只验证 `analysis / elewise / reduce` 三个公开模块可达性与 legacy lowering 路径不再暴露 tile family API；这一条返修已收口。
- [test/pass/nn_lowering/public_name.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py) 与 [test/pass/nn_lowering/test_nn_lowering_asset_cases.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py) 当前也已保持在公开入口范围内：`TC-PASS-NNL-003/004/005` 的 collectable 入口和 `img2col` 隔离都没有回退。
- 但当前 residual diff 里已经删除了 [test/pass/nn_lowering/test_nn_lowering_private_helpers.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_private_helpers.py)，而 child spec 与实现文件说明仍把这个已删除文件写成现行测试入口；这会直接把当前仓库文档与现场入口对齐关系打断。
问题列表：
1. 已删除的 [test/pass/nn_lowering/test_nn_lowering_private_helpers.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_private_helpers.py) 仍被多处 child spec / 文件说明当作现行测试入口引用。
   - 直接证据：
     - [spec/pass/lowering/nn_lowering/element_binary_lowering.md:32](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/element_binary_lowering.md:32)、[spec/pass/lowering/nn_lowering/element_binary_lowering.md:109](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/element_binary_lowering.md:109)、[spec/pass/lowering/nn_lowering/element_binary_lowering.md:123](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/element_binary_lowering.md:123)
     - [spec/pass/lowering/nn_lowering/dma_structured_lowering.md:22](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/dma_structured_lowering.md:22)、[spec/pass/lowering/nn_lowering/dma_structured_lowering.md:84](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/dma_structured_lowering.md:84)、[spec/pass/lowering/nn_lowering/dma_structured_lowering.md:88](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/dma_structured_lowering.md:88)
     - [spec/pass/lowering/nn_lowering/select_cast_lowering.md:24](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/select_cast_lowering.md:24)、[spec/pass/lowering/nn_lowering/select_cast_lowering.md:109](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/select_cast_lowering.md:109)、[spec/pass/lowering/nn_lowering/select_cast_lowering.md:115](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/select_cast_lowering.md:115)
     - [spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md:24](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md:24)、[spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md:89](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md:89)、[spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md:95](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md:95)
     - [spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md:23](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md:23)、[spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md:85](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md:85)、[spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md:90](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md:90)
     - [kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py:64](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py:64)
   - 风险：当前 S3 把 `test_nn_lowering_private_helpers.py` 从仓库现场移除后，child spec / 文件说明仍把它写成真实入口，会误导后续执行人继续按失效命令或失效链接验收。
   - 建议：把这些 child spec 与文件说明统一改到现行公开入口、现行 collectable 资产入口，或明确改写为“该 helper 专项测试已移除，现由 public_name / test_lowering_nn_lowering / test_nn_lowering_asset_cases 承担对应覆盖”。
2. [spec/pass/lowering/nn_lowering/spec.md:11](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md:11) 到 [:16](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md:16) 的 `API 列表` 仍未按当前 spec 规则收齐：
   - `NnLoweringPass` / `NnLoweringError` 仍是裸名字，没有参数签名；
   - `ensure_module_op(module)` 仍挂在主 spec 的 `API 列表` 中，但当前 package-root 公开面 [kernel_gen/passes/lowering/nn_lowering/__init__.py:9](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/__init__.py:9) 到 [:12](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/__init__.py:12) 只定义 `NnLoweringPass`、`NnLoweringError`、`nn_lowering_patterns()`；`ensure_module_op` 实际位于 [kernel_gen/passes/lowering/nn_lowering/nn_lowering_utility.py:29](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/nn_lowering_utility.py:29) 的 utility 模块。
   - 风险：主 spec 的公开 API 快速索引仍与当前真实公开面不一致，也不满足“API 列表紧跟功能简介、逐项带签名”的最新规则。
   - 建议：把主 spec 的 `API 列表` 收成真正的快速索引，逐项写签名，并把 `ensure_module_op(...)` 放回 utility spec 或明确其 canonical public path。
Diff 反推审查：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_nn_lowering_asset_cases.py test/pass/tile/test_package.py -ra` -> `30 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/test_pass_registry.py test/pass/test_pass_manager.py test/pass/test_dma_memory_hierarchy.py test/pass/tile/test_package.py test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_nn_lowering_asset_cases.py -ra` -> `82 passed, 1 warning`
- `rg -n "test_nn_lowering_private_helpers\.py" spec/pass/lowering/nn_lowering kernel_gen/passes/lowering/nn_lowering` -> 命中 child spec 与 `reduce_softmax_lowering.py` 文件说明中的现行失效引用
- `git -C /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis diff --check` -> 通过
合同验收（如适用）：
- 本轮未执行 `expectation`；其继续只作合同验收资产单列，不计入 diff 反推审查。
可改进点：
- `tile package` 的 `__all__` 边界这轮已经收掉；当前剩余阻断点集中在“删除 helper 专项测试文件后，child spec / 文件说明 / 主 spec API 索引没有一起更新”。
- 这批文档和文件说明若不一起收口，S3 的“helper 边界与公开测试入口”仍然不算闭合。
自检：
- 已按最新规则核对：未新增当前文件之外的非公开 API 使用；测试不再直连 `tile_package.__all__`；`public_name` 与 `asset_cases` 不再跨文件复用测试函数。
- 当前仍存在可执行、可定位的问题 2 项，结论只能为 `需修改`。
结论：
- `需修改`。
- `tile package` 边界返修已通过，但删除 [test/pass/nn_lowering/test_nn_lowering_private_helpers.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_private_helpers.py) 后，child spec / 文件说明 / 主 spec API 列表仍未与当前公开入口现场一致，需回到 `build` 继续收口。

---

时间：2026-04-27 00:24:00 +0800
经办人：金铲铲大作战
任务：T-20260426-5caa70b5 / S3 build 复修
任务目标：同步收口删除 [test/pass/nn_lowering/test_nn_lowering_private_helpers.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_private_helpers.py) 后的 child spec / 文件说明失效引用，并修正 [spec/pass/lowering/nn_lowering/spec.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md) 的 `API 列表`，使其与当前 package-root 公开面和最新 spec 规则一致。
执行前阅读记录：已读 [TODO.md](/home/lfr/kernelcode_generate/TODO.md) 当前任务行、[ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md) S3 正文、[AGENTS.md](/home/lfr/kernelcode_generate/AGENTS.md) 与当前任务记录前序 build / review 结论，并复核 [spec/pass/lowering/nn_lowering/spec.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md)、5 份 child spec、[kernel_gen/passes/lowering/nn_lowering/__init__.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/__init__.py)、[kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py)、[test/pass/nn_lowering/public_name.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py)、[test/pass/nn_lowering/test_nn_lowering_asset_cases.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py)、[test/pass/nn_lowering/test_reduce_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_reduce_lowering.py) 与 [test/pass/nn_lowering/test_lowering_nn_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_lowering_nn_lowering.py) 当前现场。
最小功能闭环：
- 主 spec 顶部 `API 列表` 只保留当前 package-root 公开面，并补齐参数签名。
- 5 份 child spec 与 `reduce_softmax_lowering.py` 文件说明不再引用已删除的 `test_nn_lowering_private_helpers.py`。
- child spec 的测试入口改成当前公开 collectable 入口、公开 `test_*.py` 入口，`img2col1d/2d accepts_noncanonical_symbol_names` 继续保持资产文件单独维护说明。
改动：
- 更新 [spec/pass/lowering/nn_lowering/spec.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md) 顶部 `API 列表`，收口为：
  - `class NnLoweringPass()`
  - `NnLoweringPass.apply(ctx: Context, module: builtin.module) -> None`
  - `NnLoweringPass.run(module: builtin.module) -> builtin.module`
  - `class NnLoweringError(message: str)`
  - `nn_lowering_patterns() -> list[RewritePattern]`
- 更新 [spec/pass/lowering/nn_lowering/element_binary_lowering.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/element_binary_lowering.md)、[spec/pass/lowering/nn_lowering/dma_structured_lowering.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/dma_structured_lowering.md)、[spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md)、[spec/pass/lowering/nn_lowering/select_cast_lowering.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/select_cast_lowering.md)、[spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md)，把删除后的失效测试链接 / 执行命令改到现行公开入口；同时同步文件头 `最后一次更改`。
- 更新 [spec/pass/lowering/nn_lowering/select_cast_lowering.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/select_cast_lowering.md) 中错误的相对链接层级，保证 `spec / test / 功能实现 / 依赖` 链接都指向当前有效路径。
- 更新 [kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py) 中 `_ensure_int_attr(...)` 的函数说明测试引用，改到现行公开测试 [test/pass/nn_lowering/test_reduce_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_reduce_lowering.py)。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_reduce_lowering.py /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_lowering_nn_lowering.py -k 'patterns or reduce or softmax or broadcast or transpose or select or cast or exp or element_binary or element_compare' -ra` -> `57 passed, 22 deselected, 1 warning`
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py` -> 通过
- `rg -n "test_nn_lowering_private_helpers\\.py|test_nn_lowering_private_helpers" spec/pass/lowering/nn_lowering kernel_gen/passes/lowering/nn_lowering -g '*.md' -g '*.py'` -> 无命中
- `git -C /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis diff --check` -> 通过
Diff 反推自测：
- 本轮 diff 直接落在 [spec/pass/lowering/nn_lowering/spec.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md)、5 份 child spec 与 [kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py)。
- 反推测试入口因此选择当前现行公开 collectable / 公开 `test_*.py` 入口：`public_name.py`、`test_nn_lowering_asset_cases.py`、`test_reduce_lowering.py`、`test_lowering_nn_lowering.py`；覆盖主 spec、child spec 和 `reduce/softmax` 文件说明所对应的当前公开验证面。
- `img2col1d/2d accepts_noncanonical_symbol_names` 继续保持为资产文件单独维护事项，本轮只在 child spec 中明确“不纳入 collectable 公开入口”，没有把其 standalone 失败重新并入当前通过条件。
合同验收（如适用）：
- 未执行 `expectation`；本轮仅修 spec / 文件说明与公开测试入口映射，`expectation` 继续只作合同验收资产单列。
真实自检：
- 未新增 spec 未定义的公开接口；主 spec `API 列表` 已与 [kernel_gen/passes/lowering/nn_lowering/__init__.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/__init__.py) 的当前 package-root 公开面一致。
- 未跨文件调用非公开 API；本轮唯一实现文件改动只在同文件 docstring 测试引用，不涉及逻辑分支。
- 测试只走公开 collectable 入口与公开 `test_*.py` 文件；没有重新引入已删除的 private helper 测试面，也没有把 `__all__` 当公开合同。
- `select_cast_lowering.md` 的相对链接层级已与当前文件位置一致，不再指向失效路径。
结论：
- 当前 build 已完成，可续接 `review`。

---

时间：2026-04-27 00:36:00 +0800
经办人：不要啊教练
任务：T-20260426-5caa70b5 / S3 review 复审回合
任务目标：复核 `nn_lowering` 主/子 spec 与 `reduce_softmax_lowering.py` 的失效测试引用返修、主 spec `API 列表` 与 package-root 公开面对齐结果，并确认当前公开 collectable 入口与现有 lowering 行为未回退。
执行前阅读记录：已读 [TODO.md](/home/lfr/kernelcode_generate/TODO.md) 当前任务行、[ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md) S3 正文 / 全局完成态 / 验收设计、[AGENTS.md](/home/lfr/kernelcode_generate/AGENTS.md) 与当前任务记录前序 build / review 结论，并复核 [kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py)、[kernel_gen/passes/lowering/nn_lowering/nn_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)、[kernel_gen/passes/lowering/nn_lowering/__init__.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/__init__.py)、[spec/pass/lowering/nn_lowering/spec.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md)、[test/pass/nn_lowering/public_name.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py)、[test/pass/nn_lowering/test_nn_lowering_asset_cases.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py)、[test/pass/nn_lowering/test_reduce_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_reduce_lowering.py)、[test/pass/nn_lowering/test_lowering_nn_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_lowering_nn_lowering.py) 当前现场。
真实审查：
- 上一轮点名的失效引用已经收住：主 spec 顶部 `API 列表` 现在与 package-root 公开面一致，child spec 与 [kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py) 的失效测试引用也已改到现行公开入口。
- `public_name.py` / `test_nn_lowering_asset_cases.py` 的 collectable 公开入口没有回退；`test_reduce_lowering.py` 与 `test_lowering_nn_lowering.py` 也仍然转绿。
- 但当前 residual diff 里的实现边界还没有收口：[kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py) 仍跨文件直接导入 [kernel_gen/passes/lowering/nn_lowering/nn_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/nn_lowering.py) 的下划线 helper，而主文件头和主 spec 都已明确这些 helper 仅供当前文件内部复用、不属于公开合同；同时该文件作为本轮改动过的功能实现文件，文件头仍缺失文件级 `API 列表`。
问题列表：
1. [kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py:39](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py:39) 到 [:45](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py:45)
   - 现象：当前 child 模块仍直接 `from .nn_lowering import _ensure_operand_count, _ensure_single_result, _ensure_space_attr, _ensure_symbol_or_int`。
   - 依据：主实现 [kernel_gen/passes/lowering/nn_lowering/nn_lowering.py:10](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/nn_lowering.py:10) 到 [:12](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/nn_lowering.py:12) 已明确 `_ensure_* / _normalize_* / _collect_* / _materialize_* / _lower_*` helper 仅供当前文件内部复用；主 spec [spec/pass/lowering/nn_lowering/spec.md:7](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md:7) 也明确 family helper / dispatcher 不属于公开合同，顶部 `API 列表` [spec/pass/lowering/nn_lowering/spec.md:11](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md:11) 到 [:15](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/spec.md:15) 只定义 `NnLoweringPass`、`NnLoweringError(message: str)`、`nn_lowering_patterns()`。
   - 风险：这是当前文件之外的非公开 API 使用。按最新审查规则，命中即不得通过；后续一旦主文件内部 helper 重构或更名，child 模块会直接被私有实现细节牵连。
   - 建议：把这组共享校验 helper 收到明确公开的 utility 模块 / utility spec，或改为 child 文件内自持，不要继续跨文件 import 下划线 helper。
2. [kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py:1](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py:1)
   - 现象：该文件这轮已进入实际 diff，但文件头仍没有 `API 列表:` 段，只有 `功能说明 / 使用示例 / 关联文件`。
   - 依据：当前 build 审查规则要求“改动功能实现文件时，必须同步维护文件级 API 列表；API 列表只做快速索引，列公开 API 与参数签名；class 文件需列类公开 API”。本文件当前 surviving 模块级接口至少包含 `reduce_softmax_patterns() -> list[RewritePattern]`。
   - 风险：文件级公开面与 spec/documentation 无法机械对齐，后续 review 也无法只靠文件头快速判定当前文件公开出口。
   - 建议：补齐文件级 `API 列表`，至少把 `reduce_softmax_patterns() -> list[RewritePattern]` 列出来，并与 child spec 保持一致。
Diff 反推审查：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_nn_lowering_asset_cases.py test/pass/nn_lowering/test_reduce_lowering.py test/pass/nn_lowering/test_lowering_nn_lowering.py -k 'patterns or reduce or softmax or broadcast or transpose or select or cast or exp or element_binary or element_compare' -ra` -> `57 passed, 22 deselected, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q test/pass/test_pass_registry.py test/pass/test_pass_manager.py test/pass/test_dma_memory_hierarchy.py test/pass/tile/test_package.py test/pass/nn_lowering/public_name.py test/pass/nn_lowering/test_nn_lowering_asset_cases.py -ra` -> `82 passed, 1 warning`
- `git -C /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis diff --check` -> 通过
合同验收（如适用）：
- 本轮未执行 `expectation`；其继续只作合同验收资产单列，不计入 diff 反推审查。
可改进点：
- 上一轮的“失效测试引用 / 主 spec API 列表 / collectable 入口”已经收完，当前剩余问题都集中在 `reduce_softmax_lowering.py` 的实现边界：既有跨文件私有 helper 依赖，又缺文件级 API 列表。把这一处收掉后，S3 这轮 residual diff 才有机会进入下一步。
自检：
- 已按最新规则核对：是否新增 spec 未定义公开接口、是否跨文件调用非公开 API、测试是否直连非 API 接口、改动实现文件是否同步维护文件级 API 列表。
- 当前命中“跨文件非公开 API 使用”与“改动实现文件缺失 API 列表”两条硬规则，结论只能为 `需修改`。
结论：
- `需修改`。
- `nn_lowering` 主/子 spec 失效引用、主 spec API 列表和公开 collectable 入口都已收口；但 [kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py) 仍跨文件直连 [kernel_gen/passes/lowering/nn_lowering/nn_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/nn_lowering.py) 的下划线 helper，且缺失文件级 `API 列表`，需回到 `build` 继续收口。

---

时间：2026-04-27 00:55:00 +0800
经办人：金铲铲大作战
任务：T-20260426-5caa70b5 / S3 build 复修
任务目标：收口 [reduce_softmax_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py) 的实现公开边界，去掉对 [nn_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/nn_lowering.py) 下划线 helper 的跨文件直连，并补齐该实现文件的文件级 `API 列表`。
执行前阅读记录：已读 [TODO.md](/home/lfr/kernelcode_generate/TODO.md) 当前任务行、[ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md) S3 正文、[AGENTS.md](/home/lfr/kernelcode_generate/AGENTS.md) 与当前任务记录前序 build / review 结论，并复核 [reduce_softmax_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py)、[nn_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)、[reduce_softmax_lowering.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md)、[public_name.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py)、[test_reduce_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_reduce_lowering.py)、[test_lowering_nn_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_lowering_nn_lowering.py) 当前现场。
最小功能闭环：
- 在 [reduce_softmax_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py) 顶部补齐文件级 `API 列表`，只列当前模块 surviving 公开接口。
- 断开对 [nn_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/nn_lowering.py) 下划线 helper 的跨文件 import，把当前文件实际需要的最小校验逻辑内聚到本文件。
- 保持 `reduce/softmax` 家族当前公开测试与现有 lowering 行为不回退。
改动：
- 更新 [reduce_softmax_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py) 文件头，补齐 `API 列表: reduce_softmax_patterns() -> list[RewritePattern]`。
- 删除该文件对 [nn_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/nn_lowering.py) 下划线 helper `_ensure_single_result`、`_ensure_space_attr`、`_ensure_symbol_or_int` 的跨文件依赖，只保留公开异常类型 `NnLoweringError`。
- 在 [reduce_softmax_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py) 内新增同文件 helper：`_ensure_space_attr(...)`、`_ensure_single_result(...)`、`_ensure_symbol_or_int(...)`，并为它们补齐完整文件说明、示例和关联文件链接。
- 删除当前文件内已不再参与公开合同的 `nn.exp` 残留 import / helper，避免继续扩大模块职责。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py` -> 通过
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_reduce_lowering.py /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_lowering_nn_lowering.py -k 'reduce or softmax or nn_lowering_pass_public_name or nn_lowering_child_pattern_exports or pattern_driver' -ra` -> `23 passed, 34 deselected, 1 warning`
- `git -C /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis diff --check` -> 通过
Diff 反推自测：
- 本轮 residual diff 只落在 [reduce_softmax_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py)，因此反推测试只复跑直接覆盖 `reduce/softmax` family 公开行为与 `nn_lowering` package-root 公开入口的最小公开集合：`public_name.py`、`test_reduce_lowering.py`、`test_lowering_nn_lowering.py` 中与 `reduce/softmax` 相关的 case。
- 额外机械核对：当前文件已不再出现 `from .nn_lowering import _ensure_*` 形式的跨文件下划线 helper import；现场只剩同文件 local helper 定义与调用。
合同验收（如适用）：
- 未执行；本轮只修实现公开边界与文件级 `API 列表`，`expectation` 继续只作合同验收资产单列。
真实自检：
- 未新增 spec 未定义的公开接口；文件级 `API 列表` 只列当前 surviving 公开接口 `reduce_softmax_patterns() -> list[RewritePattern]`。
- 未跨文件调用当前文件之外的非公开 API；当前新增 helper 全部位于 [reduce_softmax_lowering.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py) 内部。
- 测试仍只走公开 collectable / 公开 `test_*.py` 入口，没有新增对私有 helper 的直连。
- 本轮未修改 `expectation`、未扩修 `img2col` 既有失败，也未回退此前已收口的主/子 spec 与 package-root 公开边界。
结论：
- 当前 build 已完成，可续接 `review`。

---

时间：2026-04-27 01:19:00 +0800
经办人：李白
任务：T-20260426-5caa70b5 / S3 merge 收口
任务目标：将当前 `passes / analysis` residual diff 重放到最新 `origin/main`，确认 review 阶段已经给出 `Diff 反推审查` 证据后完成合并、推送与状态收口。
执行前阅读记录：已读 [TODO.md](/home/lfr/kernelcode_generate/TODO.md) 当前任务行、[ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md) S3 正文 / 全局完成态 / 验收设计、[AGENTS.md](/home/lfr/kernelcode_generate/AGENTS.md) 与当前任务记录前序 `build/review` 结论；已核对当前任务处于 `merge`，且记录内已有多轮 `Diff 反推审查`，本轮 residual diff 继续限定在 `kernel_gen/passes`、`spec/pass/lowering/nn_lowering`、`test/pass` 的公开边界收口。
最小功能闭环：
- 将 worktree 从旧基线 `1477e823977b720e92b297400eb279e796b08271` 重放到最新 `origin/main@1fc96a2b59a58f4f3624bbcbc468b7e2ba808864`。
- 保留当前 residual diff 的 `pass / analysis` 公开边界，不引入 `execute_engine`、`include` 或 `expectation` 改动。
- 复跑当前 diff 直接对应的公开 pytest、语法检查与 `git diff --check`，确认 merge 前现场仍与 review 结论一致。
合并过程：
- 在 [wt-20260426-repo-conformance-s3-pass-analysis](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis) 内执行 `git fetch origin`。
- 将当前未提交 residual diff 暂存为 `T-20260426-5caa70b5-pre-merge`，切到 `origin/main` 的 detached HEAD，再恢复该组改动；本轮重放未产生文件级冲突。
- 重放后继续保留当前 residual diff：`dma_memory_hierarchy`、`pass_manager/registry`、`tile package`、`nn_lowering public name / asset cases / reduce_softmax boundary`，以及对应 spec / pytest / 任务记录。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/test_pass_manager.py /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/test_dma_memory_hierarchy.py /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/tile/test_package.py /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_reduce_lowering.py /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_lowering_nn_lowering.py -ra` -> `134 passed, 1 warning`
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/dma_memory_hierarchy.py /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/__init__.py /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/__init__.py /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/nn_lowering.py /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/pass_manager.py /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/registry.py /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/kernel_gen/passes/tile/__init__.py /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/public_name.py /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/nn_lowering/test_nn_lowering_asset_cases.py /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/test_dma_memory_hierarchy.py /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/test_pass_manager.py /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/test_pass_registry.py /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis/test/pass/tile/test_package.py` -> 通过
- `git -C /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s3-pass-analysis diff --check` -> 通过
Diff 反推自测：
- 本轮 merge 前复跑直接覆盖当前 residual diff 的公开测试入口：`test_pass_registry.py`、`test_pass_manager.py`、`test_dma_memory_hierarchy.py`、`tile/test_package.py`、`nn_lowering/public_name.py`、`test_nn_lowering_asset_cases.py`、`test_reduce_lowering.py`、`test_lowering_nn_lowering.py`。
- 未把 `expectation` 计入 diff 反推测试；本轮也未写入任何 `expectation` 文件。
合同验收（如适用）：
- 未执行；按当前仓库规则，本轮 merge 不修改 `expectation`，其仍只作合同验收资产单列。
真实自检：
- 当前 residual diff 重放到最新主线后未引入新的跨阶段文件。
- merge 前校验结果与现有 review / build 记录一致，没有出现公开边界回退或新增私有 API 直连。
- 主记录文件继续写在当前 worktree 路径，未把常规日志落到主仓根目录。
结论：
- 当前 residual diff 已在最新 `origin/main` 基线上通过最小 merge 自检，可继续提交、推送并执行 `-done`。
