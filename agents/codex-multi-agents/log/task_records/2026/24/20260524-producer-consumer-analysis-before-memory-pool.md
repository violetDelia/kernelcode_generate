时间：2026-05-24 23:10 +0800
经办人：神秘人
任务：T-20260524-6dacd489 / producer-consumer-analysis-before-memory-pool / 管理员创建
任务目标：在依赖 T-20260524-ebee86b8 merge/DONE 后，创建普通小任务 execute，调整 npu-demo-lowering 中 ProducerConsumerAnalysisPass 的位置到第二段 SymbolBufferHoistPass 之后、MemoryPoolPass(rewrite=True, alignment=0) 之前，并同步实现说明、spec 与 pipeline pytest。
改动：已基于 origin/main@7dbe05d3874a6f8f4705e948a318fda167898515 创建 worktree `/home/lfr/kernelcode_generate/wt-20260524-producer-consumer-analysis-before-memory-pool`，本记录用于后续 execute/review/merge 追加。任务边界：不修改 ProducerConsumerAnalysisPass 算法语义，不新增公开 pass/API/option，不修改 expectation。
验证：管理员只读核对 T-20260524-ebee86b8 已 merge/DONE，主仓 HEAD=origin/main=7dbe05d3874a6f8f4705e948a318fda167898515；新 worktree 创建成功。管理员不执行 pytest/expectation。
自检：任务目标为可执行动作，依赖已解除；该任务为普通小任务，后续按 execute -> review -> merge 流转。若主仓只读 expectation.pass.pipeline.npu_demo_lowering 因旧顺序失败，执行人只记录 actual/expected/spec/verdict 并回架构裁定，不得修改 expectation。
结论：可分发 execute。

时间：2026-05-25 00:23 +0800
经办人：金铲铲大作战
任务：T-20260524-6dacd489 / producer-consumer-analysis-before-memory-pool / execute
任务目标：将 `npu-demo-lowering` 中 `ProducerConsumerAnalysisPass` 移到第二段 `SymbolBufferHoistPass` 之后、`MemoryPoolPass(rewrite=True, alignment=0)` 之前，同步实现说明、spec 与 pipeline pytest；遇到主仓只读 expectation 旧顺序时记录 actual/expected/spec/verdict 并回报裁定，不修改 `expectation/`。

执行前阅读记录：
- 已重读个人提示词、根 `AGENTS.md`、`agents/standard/任务记录约定.md`、`agents/standard/审查规范.md` 与本任务记录。
- 已核对任务边界：不修改 `ProducerConsumerAnalysisPass` 算法语义，不新增公开 pass / API / option，不修改 `expectation/`、`.skills/`、`agents/standard/`。
- `git fetch --prune origin` 后核对：执行目录 `/home/lfr/kernelcode_generate/wt-20260524-producer-consumer-analysis-before-memory-pool`；`HEAD=origin/main=merge-base=7dbe05d3874a6f8f4705e948a318fda167898515`；latest main 未前进，无同步冲突或覆盖风险。

最小功能闭环：
- `kernel_gen/pipeline/npu_demo_lowering.py`：将第二段 `SymbolBufferHoistPass()` 后的 `ProducerConsumerAnalysisPass()` 前移到 `MemoryPoolPass(rewrite=True, alignment=0)` 前；memory-pool 后顺序收口为 `CanonicalizePass -> ArchParallelizePass -> AttachArchInformationPass -> OutlineDeviceKernelPass -> TemplateNameInferPass`。
- `kernel_gen/pipeline/npu_demo_lowering.py` 文件级说明与 `build_npu_demo_lowering_pipeline(...)` 函数说明同步更新，明确 producer-consumer-analysis 在 memory-pool 前读取 typed `dma.alloc`，memory-pool 之后不再运行 producer-consumer-analysis。
- `spec/pass/pipeline/npu_demo_lowering.md`：同步术语、目标、公开 pass 顺序、TC-002/TC-004/TC-007 测试矩阵，要求 `symbol-buffer-hoist -> producer-consumer-analysis -> memory-pool`，并要求 producer stage 保留 typed `dma.alloc`。
- `test/passes/pipeline/test_npu_demo_lowering.py`：同步公开 pipeline 顺序测试和 dump 测试，断言 producer-consumer-analysis 紧跟第二段 `symbol-buffer-hoist`、位于 `memory-pool` 前，且该 stage 有 `dma.alloc` / `!nn.memory`、无 `arch.get_dynamic_memory`。

改动：
- `kernel_gen/pipeline/npu_demo_lowering.py`
- `spec/pass/pipeline/npu_demo_lowering.md`
- `test/passes/pipeline/test_npu_demo_lowering.py`
- 本任务记录。

验证：
- `python3 -m py_compile kernel_gen/pipeline/npu_demo_lowering.py`：exit=0。
- `python3 -m py_compile test/passes/pipeline/test_npu_demo_lowering.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py`：exit=0，`10 passed, 1 warning`。锁定公开 builder 顺序、dump marker 与 producer-consumer-analysis pre-pool typed alloc 形态。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`：exit=0，present/absent bias 均通过，输出 `max_abs_diff=3.4332275390625e-05`。
- present-bias dump 核对脚本：exit=0，`26-producer-consumer-analysis.mlir` 存在 `dma.alloc` / `!nn.memory`，不存在 `arch.get_dynamic_memory`；`27-memory-pool.mlir` 存在 `arch.get_dynamic_memory` / `dma.reinterpret`。
- import proof：`expectation.pass.pipeline.npu_demo_lowering` 与 `expectation.utils.case_runner` 来自主仓 `/home/lfr/kernelcode_generate/expectation/...`；`kernel_gen.pipeline.npu_demo_lowering` 来自任务 worktree `/home/lfr/kernelcode_generate/wt-20260524-producer-consumer-analysis-before-memory-pool/kernel_gen/pipeline/npu_demo_lowering.py`。
- 主仓只读合同验收：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-producer-consumer-analysis-before-memory-pool:/home/lfr/kernelcode_generate python3 -m expectation.pass.pipeline.npu_demo_lowering`：exit=1，失败 1 例，见下方 actual/expected/spec/verdict；未修改 expectation。
- `git diff --check`：exit=0。
- 敏感目录门禁：`git diff --name-only -- expectation .skills agents/standard`、`git diff --cached --name-only -- expectation .skills agents/standard`、`git status --short --ignored --untracked-files=all -- expectation .skills agents/standard | sed -n '1,80p'`：任务 worktree 无 tracked/cached/untracked 候选 diff 输出。
- 静态扫描：`git diff --unified=0 -- '*.py' | rg '^\+\s*(def _|async def _|class _|\s+def _)' || true`、`git diff -- '*.py' | rg 'hasattr\(|getattr\(|callable\(' || true`、`git diff -- '*.py' | rg 'from .* import _|\._[A-Za-z0-9_]+\(' || true` 均无输出；AST 嵌套函数扫描 `kernel_gen/pipeline/npu_demo_lowering.py` 与 `test/passes/pipeline/test_npu_demo_lowering.py` 无输出。

主仓只读 expectation 旧顺序归因：
- actual：`... memory-plan:insert_free=True:fold=False -> symbol-buffer-hoist -> producer-consumer-analysis -> memory-pool -> canonicalize -> arch-parallelize -> attach-arch-information -> outline-device-kernel -> template-name-infer`。
- expected：`... memory-plan:insert_free=True:fold=False -> symbol-buffer-hoist -> memory-pool -> canonicalize -> arch-parallelize -> producer-consumer-analysis -> attach-arch-information -> outline-device-kernel -> template-name-infer`。
- spec：本任务目标与已同步 `spec/pass/pipeline/npu_demo_lowering.md` 要求 `ProducerConsumerAnalysisPass` 位于第二段 `SymbolBufferHoistPass` 之后、`MemoryPoolPass(rewrite=True, alignment=0)` 之前；该 stage 保留 typed `dma.alloc` 供分析读取。
- verdict：主仓只读 `expectation.pass.pipeline.npu_demo_lowering` 仍锁旧顺序，属于合同资产旧顺序未同步；execute 无权修改 expectation，已按任务要求记录并回报管理员/架构裁定。

Diff 反推自测：
- `kernel_gen/pipeline/npu_demo_lowering.py` 改动直接影响公开 builder 顺序，因此反推运行 `pytest -q test/passes/pipeline/test_npu_demo_lowering.py` 与 `py_compile`。
- `spec/pass/pipeline/npu_demo_lowering.md` 改动影响 TC-002/TC-004/TC-007 公开测试矩阵，因此反推运行同一 pipeline pytest，并核对 dump marker 文本。
- `test/passes/pipeline/test_npu_demo_lowering.py` 改动增加 producer-consumer-analysis pre-pool typed alloc 断言，因此反推运行完整 pipeline pytest 与 `test/passes/pipeline/test_npu_demo_lowering.py` 自身 `py_compile`。
- demo gate 反推自测覆盖真实 npu-demo lowering dump：`kernel/matmul/inputs_static_tile_static.py` 生成 present-bias dump，并用脚本锁定 producer stage 在 memory-pool 前且保留 typed `dma.alloc`。
- `expectation` 仅作为合同验收资产单列，不计入 Diff 反推自测。

减法检查：
- 新增 / 改动 private callable：无。静态 diff 未新增 `def _...` / `class _...`。
- 被替代旧逻辑：替代旧 pipeline 顺序中 memory-pool 后的 `ProducerConsumerAnalysisPass()` 位置；旧位置已删除，仅保留新的 pre-pool 调用。
- 保留旧逻辑依据：`ProducerConsumerAnalysisPass` 算法实现、公开 API、registry 名称和 option 合同均未改动；本任务只改 pipeline 调用位置。
- 删除 / 未删除验证：`git diff` 显示旧的 `pm.add_pass(ProducerConsumerAnalysisPass())` 从 `ArchParallelizePass` 后删除；pipeline pytest 与 dump 断言证明新位置生效。

自检：
- 接口 / API：未新增、删除、重命名公开 API；未新增 pipeline option；未改 `build_npu_demo_lowering_pipeline(...)` 签名。
- 边界 / 异常：unknown option、target 校验和 standalone pass 行为未改；producer-consumer-analysis 仅移动执行阶段，不改变算法语义。
- 兼容性：memory-pool 后仍保留 `canonicalize -> arch-parallelize -> attach-arch-information -> outline-device-kernel -> template-name-infer`，late attach 继续特化 memory-pool 生成的 `arch.get_dynamic_memory`。
- 实现遗漏 / 冗余：实现说明、spec 与 pytest 均同步；未发现重复 producer-consumer-analysis 调用。
- 注释准确性：文件级说明与函数说明已从旧“arch 后、attach 前”改为“第二段 symbol-buffer-hoist 后、memory-pool 前”。
- 复用 / 函数粒度：只调整 pipeline builder 顺序，未引入 helper 或额外抽象。
- 输入输出校验：现有 target / unknown option 校验保持不变。
- 资源 / 并发 / 性能：本轮仅调整 pass 顺序，无新增资源生命周期或并发状态。
- 测试有效性：pytest 通过 monkeypatch 顺序和真实 dump 双重锁定；demo dump 脚本证明 producer stage 尚未进入 pool 形态。
- 敏感目录：候选 diff 中 `expectation/`、`.skills/`、`agents/standard/` 为空。

结论：实现、spec、pytest、demo dump、diff check 与静态门禁已闭合；主仓只读 `expectation.pass.pipeline.npu_demo_lowering` 仍因旧顺序断言 exit=1。按任务要求不修改 expectation，已记录 actual/expected/spec/verdict，需管理员/架构裁定或同步合同后再流转 review。

时间：2026-05-25 00:43 +0800
经办人：金铲铲大作战
任务：T-20260524-6dacd489 / producer-consumer-analysis-before-memory-pool / execute 复验与流转
任务目标：按架构裁定同步后的主仓只读 expectation 真源复验任务闭环，在不修改 `expectation/`、`.skills/`、`agents/standard/` 的前提下确认 pytest / demo / dump / diff check / 敏感目录门禁均通过，并流转 review。

执行前阅读记录：
- 已读神秘人同步：守护最好的爱莉希雅已裁定并由架构侧极窄同步主仓 ignored `expectation/pass/pipeline/npu_demo_lowering.py`，目标顺序为 `second symbol-buffer-hoist -> producer-consumer-analysis -> memory-pool`，hash=`80d365790227e6af293be8b4114d1e147b4eaa9234603048cb5c524b1af4e198`。
- 已核对本轮只做复验、记录与流转；不修改 `expectation/`、`.skills/`、`agents/standard/`。
- `git fetch --prune origin` 后核对：执行目录 `/home/lfr/kernelcode_generate/wt-20260524-producer-consumer-analysis-before-memory-pool`；`HEAD=origin/main=merge-base=7dbe05d3874a6f8f4705e948a318fda167898515`；latest main 未前进，无同步冲突或覆盖风险。

改动：
- 仅追加本轮复验记录；实现/spec/test 候选 diff 沿用上一段 execute 已收口内容。

验证：
- 主仓 expectation hash：`sha256sum /home/lfr/kernelcode_generate/expectation/pass/pipeline/npu_demo_lowering.py` -> `80d365790227e6af293be8b4114d1e147b4eaa9234603048cb5c524b1af4e198`，与架构同步值一致。
- import proof：`expectation.pass.pipeline.npu_demo_lowering` 与 `expectation.utils.case_runner` 来自主仓 `/home/lfr/kernelcode_generate/expectation/...`；`kernel_gen.pipeline.npu_demo_lowering` 来自任务 worktree `/home/lfr/kernelcode_generate/wt-20260524-producer-consumer-analysis-before-memory-pool/kernel_gen/pipeline/npu_demo_lowering.py`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-producer-consumer-analysis-before-memory-pool:/home/lfr/kernelcode_generate python3 -m expectation.pass.pipeline.npu_demo_lowering`：exit=0，输出 `[pass-pipeline-npu_demo_lowering-order-1] pass: npu-demo-lowering order is stable.`。
- `python3 -m py_compile kernel_gen/pipeline/npu_demo_lowering.py test/passes/pipeline/test_npu_demo_lowering.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py`：exit=0，`10 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`：exit=0，present/absent bias 均通过，输出 `max_abs_diff=3.4332275390625e-05`。
- present-bias dump gate：exit=0，`26-producer-consumer-analysis.mlir` 含 `dma.alloc` / `!nn.memory` 且不含 `arch.get_dynamic_memory`；`27-memory-pool.mlir` 含 `arch.get_dynamic_memory` / `dma.reinterpret`。
- `git diff --check`：exit=0。
- 敏感目录门禁：`git diff --name-only -- expectation .skills agents/standard`、`git diff --cached --name-only -- expectation .skills agents/standard`、`git status --short --ignored --untracked-files=all -- expectation .skills agents/standard | sed -n '1,80p'`：均无输出。
- 静态边界扫描：`private callable` 新增扫描、`hasattr/getattr/callable` ctx 能力探测扫描、跨文件私有导入 / 私有调用扫描均无输出。

Diff 反推自测：
- 本轮没有新增实现/spec/test diff；按上一轮实际候选 diff 复跑 pipeline pytest、py_compile、真实 matmul demo 与 present-bias dump gate，确认架构侧 expectation 同步后没有引入回归。
- `expectation` 仍单列为合同验收资产，不计入 Diff 反推自测。

减法检查：
- 新增 / 改动 private callable：无。
- 被替代旧逻辑与处理结果沿用上一段 execute：旧的 memory-pool 后 `ProducerConsumerAnalysisPass()` 位置已删除，保留新的 pre-pool 调用。
- 本轮未新增可删旧逻辑；无保留旧逻辑的新理由。

自检：
- 公开 API：未新增或修改公开 API、pipeline option、工具参数或稳定错误语义。
- 权限边界：未修改、复制、新建、删除 `expectation/`、`.skills/`、`agents/standard/`。
- 测试有效性：pytest 顺序测试和 dump gate 同时证明 producer-consumer-analysis 位于 memory-pool 前且分析时仍看到 typed `dma.alloc`。
- 合同验收：主仓只读 expectation 已按正确导入边界 exit=0，hash 已记录。
- 仍可改进点：未发现当前任务范围内新的实现、spec、测试或记录阻断。

结论：T-20260524-6dacd489 execute 已闭合；实现/spec/test、计划内 pytest、demo、dump gate、主仓只读 expectation、diff check、静态扫描与敏感目录门禁均通过。下一步按普通任务流程流转 review。

时间：2026-05-25 00:29 +0800
经办人：守护最好的爱莉希雅
任务：T-20260524-6dacd489 / producer-consumer-analysis-before-memory-pool / 架构裁定
任务目标：裁定主仓只读 `expectation.pass.pipeline.npu_demo_lowering` 旧顺序失败是否阻断本任务，以及是否授权架构侧极窄同步合同资产。
改动：
- 裁定采用 A：由架构侧极窄同步主仓 ignored expectation `expectation/pass/pipeline/npu_demo_lowering.py`，不调整本任务实现 / spec / pytest / demo 验收口径。
- 裁定理由：本任务目标与 worktree 内 `spec/pass/pipeline/npu_demo_lowering.md`、`test/passes/pipeline/test_npu_demo_lowering.py` 均已要求 `second symbol-buffer-hoist -> producer-consumer-analysis -> memory-pool`，且 execute 记录的 actual 与该合同一致；失败只来自主仓 expectation 仍锁旧顺序 `second symbol-buffer-hoist -> memory-pool -> canonicalize -> arch-parallelize -> producer-consumer-analysis`。
- 授权 scope：仅同步 `expectation/pass/pipeline/npu_demo_lowering.py` 的说明和 `EXPECTED_ORDER` 中 `producer-consumer-analysis` 的相对位置；不得修改其它 expectation 文件，不得由 execute/admin 修改 expectation，不得把 expectation 写入本任务候选 diff。
- 主仓 expectation hash：同步前 `8251fc981115eb145571fe56e2c076859fa1d9a94084b5ff6f8370f6e2ea2529`；同步后 `80d365790227e6af293be8b4114d1e147b4eaa9234603048cb5c524b1af4e198`。
验证：
- 正确导入边界复跑：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-producer-consumer-analysis-before-memory-pool:/home/lfr/kernelcode_generate python3 -m expectation.pass.pipeline.npu_demo_lowering`，cwd=`/home/lfr/kernelcode_generate/wt-20260524-producer-consumer-analysis-before-memory-pool`，exit=0，输出 `[pass-pipeline-npu_demo_lowering-order-1] pass: npu-demo-lowering order is stable.`。
- `git status --short --ignored -- expectation/pass/pipeline/npu_demo_lowering.py` 在主仓显示 `!! expectation/pass/`，该 expectation 为主仓 ignored 合同资产；任务 worktree 候选 diff 中 `expectation/.skills/agents/standard` 仍必须为空。
自检：
- 公开 API：未新增 / 删除 / 重命名公开 API，裁定只同步既有 pipeline expectation 的顺序合同。
- 权限边界：expectation 仅由架构侧在本记录授权 scope 内极窄同步；execute/admin 仍不得修改或复制 expectation。
- 验收有效性：同步后的 expectation 在正确 worktree 优先导入边界下通过，证明旧顺序阻断已解除。
结论：主仓只读 expectation 旧顺序阻断已按架构侧极窄同步解除；本任务可恢复流转，执行/管理员需记录同步 hash 并在 review 前保留候选 diff 中 `expectation/` 为空。

时间：2026-05-25 00:37 +0800
经办人：提莫炖蘑菇
任务：T-20260524-6dacd489 / producer-consumer-analysis-before-memory-pool / review
任务目标：审查 producer-consumer-analysis-before-memory-pool 的 pipeline 顺序、spec/test 同步、主仓只读 expectation hash/import proof、pytest/demo/dump gate、diff check、静态扫描与敏感目录空 diff。

最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260524-producer-consumer-analysis-before-memory-pool`。
- 已执行：`git fetch origin`。
- `HEAD=origin/main=merge-base=7dbe05d3874a6f8f4705e948a318fda167898515`。
- `git status --short --branch` 显示候选 diff 仅包含 `kernel_gen/pipeline/npu_demo_lowering.py`、`spec/pass/pipeline/npu_demo_lowering.md`、`test/passes/pipeline/test_npu_demo_lowering.py` 与未跟踪任务记录；无主线落后、冲突或覆盖风险。

审查范围：
- `kernel_gen/pipeline/npu_demo_lowering.py`：将 `ProducerConsumerAnalysisPass()` 从 memory-pool / arch-parallelize 后移动到第二段 `SymbolBufferHoistPass()` 后、`MemoryPoolPass(rewrite=True, alignment=0)` 前；文件级说明和函数说明同步。
- `spec/pass/pipeline/npu_demo_lowering.md`：公开顺序、术语、目标、API 注意事项和测试矩阵同步为 `symbol-buffer-hoist -> producer-consumer-analysis -> memory-pool`。
- `test/passes/pipeline/test_npu_demo_lowering.py`：顺序测试与 dump gate 同步，新增 producer-consumer-analysis stage 保留 typed `dma.alloc`、不含 `arch.get_dynamic_memory` 的断言。
- 主仓只读 `expectation/pass/pipeline/npu_demo_lowering.py`：仅核对 hash、导入边界和执行结果，不纳入候选 diff。

Diff 反推审查：
- 实现 diff 只改公开 pipeline builder 顺序，未修改 `ProducerConsumerAnalysisPass` 算法、公开 API、registry name、option 或错误语义。
- spec diff 与实现顺序一致：公开顺序第 25 阶段为 `ProducerConsumerAnalysisPass`，第 26 阶段为 `MemoryPoolPass(rewrite=True, alignment=0)`，memory-pool 后顺序收口为 `canonicalize -> arch-parallelize -> attach-arch-information -> outline-device-kernel -> template-name-infer`。
- 测试 diff 有效锁定两类行为：monkeypatch 顺序列表证明 pass manager 调用顺序，公开 dump marker 证明真实 pipeline 中 producer-consumer-analysis 位于 memory-pool 前且仍看到 typed `dma.alloc`。
- `expectation` 仅作为合同验收资产单列，不计入 Diff 反推测试；导入证明显示 expectation 来自主仓、`kernel_gen` 来自任务 worktree。

验证：
- `python3 -m py_compile kernel_gen/pipeline/npu_demo_lowering.py test/passes/pipeline/test_npu_demo_lowering.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py`：首次并行复跑出现一次 `1 failed, 9 passed`，失败点为 `test_npu_demo_lowering_pipeline_static_dump_uses_pool_without_multi_buffer` 中 `hoist-dma-alias-ops` 抛出 `Worklist object is not iterable`；随后单跑该用例 exit=0，完整文件连续 5 次复跑均为 `10 passed, 1 warning`。该瞬时失败未复现，按残余风险记录，不作为当前 diff 阻断。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k static_dump_uses_pool_without_multi_buffer`：exit=0，`1 passed, 9 deselected, 1 warning`。
- `for i in 1 2 3; do PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py; done`：三轮均 exit=0，每轮 `10 passed, 1 warning`；加上前两次完整复跑，共 5 次连续通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`：exit=0；present / absent bias 均通过，输出 `max_abs_diff=3.4332275390625e-05`。
- present-bias dump gate：`kernel/dump/matmul/inputs_static_tile_static_present_bias/matmul_inputs_static_tile_static_kernel/26-producer-consumer-analysis.mlir` 含 `dma.alloc` 与 `!nn.memory`，不含 `arch.get_dynamic_memory`；`27-memory-pool.mlir` 含 `arch.get_dynamic_memory` 与 `dma.reinterpret`，不含 `dma.alloc`。
- 主仓只读合同验收：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-producer-consumer-analysis-before-memory-pool:/home/lfr/kernelcode_generate python3 -m expectation.pass.pipeline.npu_demo_lowering`：exit=0，输出 `[pass-pipeline-npu_demo_lowering-order-1] pass: npu-demo-lowering order is stable.`。
- 主仓 expectation hash：`sha256sum /home/lfr/kernelcode_generate/expectation/pass/pipeline/npu_demo_lowering.py` -> `80d365790227e6af293be8b4114d1e147b4eaa9234603048cb5c524b1af4e198`，与架构裁定记录一致。
- import proof：`expectation.pass.pipeline.npu_demo_lowering` 与 `expectation.utils.case_runner` 来自 `/home/lfr/kernelcode_generate/expectation/...`；`kernel_gen.pipeline.npu_demo_lowering` 来自任务 worktree 的 `kernel_gen/pipeline/npu_demo_lowering.py`。
- `git diff --check` 与 `git diff --cached --check`：exit=0。
- 敏感目录门禁：`git diff --name-only -- expectation .skills agents/standard`、`git diff --cached --name-only -- expectation .skills agents/standard`、`git status --short --ignored --untracked-files=all -- expectation .skills agents/standard | sed -n '1,80p'` 均无输出。
- 静态边界扫描：新增 private callable 扫描、`hasattr/getattr/callable` 能力探测扫描、跨文件私有导入 / 私有调用扫描均无输出。

减法审查：
- 新增 / 改动 private callable：无；diff 未新增 `def _...`、`class _...` 或私有方法。
- 被替代旧逻辑：旧 pipeline 中 `ArchParallelizePass` 后、`AttachArchInformationPass` 前的 `ProducerConsumerAnalysisPass()` 调用已删除。
- 保留依据：`ProducerConsumerAnalysisPass` 算法实现、公开 API、registry 名称和 option 合同均未改，本任务仅改公开 pipeline 调用位置。
- 删除验证：`git diff` 明确显示旧位置删除，新位置插入在第二段 `SymbolBufferHoistPass()` 后；pytest 顺序列表和真实 dump gate 均证明旧位置不再运行。

findings：
- 无阻断 finding。
- 残余风险：完整 pipeline pytest 首次并行复跑出现一次 `hoist-dma-alias-ops` / xDSL worklist 异常，但随后聚焦用例和完整文件连续 5 次复跑通过，demo 与 expectation 也通过；当前无法归因到本轮 diff，已记录为观察项。

自检：
- 公开 API：未新增、删除、重命名或修改公开 API、工具参数、pipeline option 或稳定错误语义。
- 非公开 API：实现 diff 未跨文件调用非公开 API；测试使用公开 pipeline builder、公开 pass class 和公开 dump/config 入口。
- ctx 能力探测 / object 签名 / 嵌套函数：本轮 diff 未新增相关命中。
- 测试有效性：顺序测试与真实 dump gate 均会在 producer-consumer-analysis 未前移、memory-pool 前 typed alloc 不存在或 memory-pool 形态提前出现时失败。
- expectation 权限：任务候选 diff 中 `expectation/` 为空；主仓 ignored expectation 仅按架构授权 hash 只读验收。
- 记录完整性：execute 记录包含执行前阅读、最小功能闭环、Diff 反推自测、减法检查、自检、expectation 旧顺序归因与架构裁定同步。

结论：通过。T-20260524-6dacd489 是普通小任务，review 通过后按流程续接 merge；merge 时需确保三份候选文件与本任务记录同批纳入，并保持 `expectation/`、`.skills/`、`agents/standard/` 无未授权 diff。

时间：2026-05-25 00:42 +0800
经办人：李白
任务：T-20260524-6dacd489 / producer-consumer-analysis-before-memory-pool / merge
任务目标：合入已通过 review 的 `producer-consumer-analysis-before-memory-pool` 候选 diff，并保持敏感目录无未授权 diff。
改动：
- 已重新读取个人提示词、根 `AGENTS.md`、`agents/standard/合并规范.md`、`agents/standard/任务记录约定.md`。
- 已确认本任务是普通小任务，管理员创建记录明确按 `execute -> review -> merge` 流转；前序 review 结论为通过，不需要 `archive_acceptance`。
- 最新同步现场：执行目录 `/home/lfr/kernelcode_generate/wt-20260524-producer-consumer-analysis-before-memory-pool`，`HEAD=origin/main=merge-base=7dbe05d3874a6f8f4705e948a318fda167898515`，主仓 `/home/lfr/kernelcode_generate` 同步为 `HEAD=origin/main=7dbe05d3874a6f8f4705e948a318fda167898515` 且无 tracked dirty。
- 候选范围复核：`git diff --name-status` 仅包含 `kernel_gen/pipeline/npu_demo_lowering.py`、`spec/pass/pipeline/npu_demo_lowering.md`、`test/passes/pipeline/test_npu_demo_lowering.py`；`git ls-files --others --exclude-standard` 仅包含本任务记录。
- 实际合入内容：将 `ProducerConsumerAnalysisPass()` 从 memory-pool / arch-parallelize 后移动到第二段 `SymbolBufferHoistPass()` 后、`MemoryPoolPass(rewrite=True, alignment=0)` 前；同步 pipeline 文件级说明、函数说明、spec 顺序 / 验收矩阵和公开 pipeline pytest。
验证：
- `python3 -m py_compile kernel_gen/pipeline/npu_demo_lowering.py test/passes/pipeline/test_npu_demo_lowering.py && python3 -m compileall -q kernel_gen/pipeline test/passes/pipeline/test_npu_demo_lowering.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q -p no:cacheprovider test/passes/pipeline/test_npu_demo_lowering.py`：exit=0，`10 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`：exit=0，present / absent bias 均通过，输出 `max_abs_diff=3.4332275390625e-05`。
- present-bias dump gate：`26-producer-consumer-analysis.mlir` 含 `dma.alloc` 与 `!nn.memory`，不含 `arch.get_dynamic_memory`；`27-memory-pool.mlir` 含 `arch.get_dynamic_memory` 与 `dma.reinterpret`。
- 合同验收单列：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-producer-consumer-analysis-before-memory-pool:/home/lfr/kernelcode_generate python3 -m expectation.pass.pipeline.npu_demo_lowering`：exit=0，输出 `[pass-pipeline-npu_demo_lowering-order-1] pass: npu-demo-lowering order is stable.`。
- 主仓只读 expectation hash：`80d365790227e6af293be8b4114d1e147b4eaa9234603048cb5c524b1af4e198  /home/lfr/kernelcode_generate/expectation/pass/pipeline/npu_demo_lowering.py`，与架构裁定记录一致；本任务候选 diff 不纳入 `expectation/`。
- import proof：`expectation.pass.pipeline.npu_demo_lowering` 与 `expectation.utils.case_runner` 来自主仓 `/home/lfr/kernelcode_generate/expectation/...`；`kernel_gen.pipeline.npu_demo_lowering` 来自任务 worktree。
- `git diff --check && git diff --cached --check`：exit=0。
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE/plan`：无输出；`git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE/plan`：无输出。
- `git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md ARCHITECTURE/plan`：无输出。
- 静态边界扫描：`kernel_gen/pipeline/npu_demo_lowering.py` 无新增 private callable 或嵌套函数；`test/passes/pipeline/test_npu_demo_lowering.py` 的 private helper 为存量测试辅助；`rg` 未发现 `ctx` 能力探测、`object` 签名、跨文件私有导入 / 私有调用新增命中。
结论：
- review 记录、架构裁定记录、合同验收、Diff 反推测试与敏感目录门禁齐全；候选范围明确，可只合入三份 pipeline/spec/test 文件和本任务记录，随后 push、执行 `-done` 并清理完成 worktree/branch。
