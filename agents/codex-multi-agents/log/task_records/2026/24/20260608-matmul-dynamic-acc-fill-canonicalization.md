# T-20260608-197a37da matmul-dynamic-acc-fill-canonicalization

## 2026-06-08 管理员创建记录

- 任务：`T-20260608-197a37da`
- 阶段：`execute`
- 责任人：待分发给空闲计划级 execute 角色
- worktree：`/home/lfr/kernelcode_generate/wt-20260608-matmul-dynamic-acc-fill-canonicalization`
- 计划书：`ARCHITECTURE/plan/matmul_dynamic_acc_fill_canonicalization.md`
- 计划对象：主仓 index 与任务 worktree index 均为 `100644 7b93cdead7616b30207220095df489d94287e301 0`
- 计划 sha256：`8a6cf035d3b60df8465d3ae143e9f6e677f4f3e1432046f4e7b970c068d27d1b`
- 守护最终检验：`守护最好的爱莉希雅` 本人回执见 `agents/codex-multi-agents/log/talk.log:11938`，结论=通过，阻断项=无，最小需改项=无，待确认项=无，允许管理员创建唯一计划级 execute。

### 管理员交接

本任务是 `ARCHITECTURE/plan/matmul_dynamic_acc_fill_canonicalization.md` 的唯一计划级 execute，不拆 S1-S5 为独立 TODO。

执行目标：

- 按计划实现 `KernelDecomposePass` 只分解不删除 fill。
- 扩展 `dma.fill` canonicalization，支持 dynamic acc matmul 与受控 `scf.if` dead-fill。
- 覆盖 static/dynamic positive runtime tile step acc fill 删除。
- 保留 dynamic/dynamic acc fill 非必删口径。
- 同步相关 spec、实现、pytest 和验收记录。

执行边界：

- 不新增、删除、重命名或修改公开 API。
- 不修改 `KernelDecomposePass`、`DmaFillOp`、`build_npu_demo_lowering_pipeline` 签名、pipeline option 或稳定错误文本。
- `expectation/` 只读；旧 `expectation.pass.kernel_decompose` initial fill 删除 case 仅作历史只读来源，不列当前必过合同验收。
- 禁止修改 `.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`plan/1.md`。
- 若发现必须调整公开 API、稳定错误语义或 expectation 本体，停止并回报管理员转用户或架构师确认。

流程要求：

- 执行前核对 worktree 基线、计划 staged 真源和 latest main 状态。
- 在本记录写清执行前阅读、最小功能闭环、自检、Diff 反推自测、减法检查、验收命令和结论。
- 完成后按计划级链路续接 `review`，不得跳过 `archive_acceptance` 或直接进入 `merge`。

## 2026-06-08 睡觉小分队 execute 启动

- 角色：`睡觉小分队`，计划级 `execute`。
- 执行前阅读：
  - 已阅读根 `AGENTS.md`、`agents/codex-multi-agents/agents/睡觉小分队/睡觉小分队.prompt.md`、`agents/standard/任务记录约定.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`。
  - 已阅读 `TODO.md` 当前任务交接、本任务记录、计划书 `ARCHITECTURE/plan/matmul_dynamic_acc_fill_canonicalization.md`。
  - 已阅读目标 `spec/pass/kernel/kernel_decompose.md`、`spec/dialect/dma.md`、`spec/pass/pipeline/npu_demo_lowering.md`，以及目标实现 / 测试文件。
- 执行前核对：
  - worktree：`/home/lfr/kernelcode_generate/wt-20260608-matmul-dynamic-acc-fill-canonicalization`。
  - `git status --short --branch`：仅管理员预置的计划书与本任务记录为 staged add，无执行实现改动。
  - 计划 staged 真源：`100644 7b93cdead7616b30207220095df489d94287e301 0`。
  - 计划 sha256：`8a6cf035d3b60df8465d3ae143e9f6e677f4f3e1432046f4e7b970c068d27d1b`。
  - latest main：`HEAD=origin/main=merge-base=cd63f945117051f9ed9e2524d0dce2e77093e7b4`，`git fetch origin --prune --quiet` 后仍一致。
  - 守护本人回执：已核对 `agents/codex-multi-agents/log/talk.log:11938`，结论通过，阻断项 / 最小需改项 / 待确认项均无。
- 最小功能闭环：
  - `kernel-decompose` 只做 `kernel.matmul_fusion -> kernel.matmul(..., dynamic acc)`，不删除 `dma.fill`。
  - `dma.fill` canonicalization 统一承接可证明 dead fill 删除，覆盖 dynamic acc matmul、positive runtime tile step 与受控 `scf.if`。
  - static/dynamic pipeline/source 测试锁定 acc/input/bias dead fill 删除；dynamic/dynamic 不把 acc fill 删除列为必达。
  - `expectation/` 保持只读，旧 `expectation.pass.kernel_decompose` initial fill 删除 case 只记录为历史只读来源。

## 2026-06-08 睡觉小分队 execute 完成

- 最新任务状态核对：
  - 按管理员二次指令重新读取 `/home/lfr/kernelcode_generate/TODO.md`：`T-20260608-197a37da` 仍为 `execute / 睡觉小分队 / 进行中`，任务列表为空，未发现重复待领任务。
  - latest main 复核：当前任务 worktree `HEAD=cd63f945117051f9ed9e2524d0dce2e77093e7b4`，`origin/main=4ecae4ac8d96508ea33d3e6f7255ec49289fe57f`，`merge-base=cd63f945117051f9ed9e2524d0dce2e77093e7b4`；`HEAD..origin/main` 仅涉及 `agents/codex-multi-agents/agents/*prompt.md` 与 `20260607-prompt-guard-fullname-rong-architect.md`，未触及本任务实现 / spec / 测试 / 计划范围。未把该无关主线提交并入任务 diff。

- 计划内小任务卡核对：
  - S1 已完成：更新 `spec/pass/kernel/kernel_decompose.md`、`spec/dialect/dma.md`、`spec/pass/pipeline/npu_demo_lowering.md`，明确 `kernel-decompose` 不删 fill、`dma.fill` canonicalization 承接 dynamic acc 与受控 `scf.if` dead-fill，记录 DU1-A / DU2-A / DU3-B 口径。
  - S2 已完成：`kernel_gen/passes/kernel/kernel_decompose.py` 删除旧 initial fill 删除链路，仅保留 fusion 分解；`test/passes/kernel/test_kernel_decompose.py` 改为断言 fill 保留、fusion 消失、dynamic acc matmul 生成。
  - S3 已完成：`kernel_gen/dialect/dma/canonicalization.py` 增加 dynamic acc matmul dead-fill 规则；`test/dialect/dma/test_canonicalization.py` 覆盖静态正 trip、`TILE_*` 正步长、fusion / 非零 fill / dynamic end / loop 前读 / body 前读等反例。
  - S4 已完成：同一 canonicalization 扩展受控 `scf.if` local alloc dead-fill；测试覆盖 full deslice before alias read 正例与 partial write、分支读、nested region、target escape 等反例。
  - S5 已完成：`test/passes/pipeline/test_npu_demo_lowering.py` 与 `test/kernel/test_matmul_symbolic_memory_genkernel.py` 锁定 static/static、static/dynamic 无 acc fill，dynamic/dynamic 保留 acc fill 非必删口径；`kernel/matmul/inputs_static_tile_dynamic.py` 同步脚本自检。
  - Diff 反推同步项：`test/tools/test_kernel_code_error_static_gate.py` 删除已失效的 `kernel_decompose` 旧 helper allowlist 项，避免减法后门禁残留死配置。

- 改动摘要：
  - `kernel-decompose` 只执行 `KernelMatmulFusionOp -> KernelMatmulOp` 替换，不再扫描、证明或删除 `dma.fill`。
  - `dma.fill` canonicalization 新增窄口径证明：零填充、同 block、target / 一跳 alias、可证明正 trip 的 `symbol.for + kernel.matmul(dynamic_acc)`；dynamic end 保守保留。
  - `dma.fill` canonicalization 新增 local alloc + 受控 `scf.if` 分支证明：每个读取 target / alias 的分支必须先由 full `dma.deslice` 覆盖，未知 region / partial write / 逃逸保守保留。
  - 未修改 `kernel_gen/pipeline/npu_demo_lowering.py` pass 顺序，未新增 pipeline option，未修改公开 API 签名或稳定错误文本。

- 验证：
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/dialect/dma/canonicalization.py kernel_gen/passes/kernel/kernel_decompose.py test/dialect/dma/test_canonicalization.py test/passes/pipeline/test_npu_demo_lowering.py test/kernel/test_matmul_symbolic_memory_genkernel.py kernel/matmul/inputs_static_tile_dynamic.py test/tools/test_kernel_code_error_static_gate.py`：退出码 0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/kernel/test_kernel_decompose.py`：11 passed，1 warning。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/dma/test_canonicalization.py`：12 passed，1 warning。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k "matmul or symbol_hoist_pipeline"`：2 passed，9 deselected，1 warning。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py`：4 passed，1 warning。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_kernel_code_error_static_gate.py`：3 passed。
  - `git diff --check`：退出码 0。
  - 过程中静态门首次暴露旧 allowlist 项残留，已删除对应死配置并重跑上述完整命令全绿。

- Diff 反推自测：
  - `kernel_gen/passes/kernel/kernel_decompose.py` 与 `test/passes/kernel/test_kernel_decompose.py`：用 kernel-decompose 单测反推验证纯分解、fill 保留、旧 rollback 删除行为不再存在。
  - `kernel_gen/dialect/dma/canonicalization.py`、`test/dialect/dma/helpers.py`、`test/dialect/dma/test_canonicalization.py`：用 DMA canonicalization 单测反推验证 dynamic acc 正例、positive runtime tile step 正例、dynamic end / fusion / 非零 / 读写边界反例与受控 `scf.if` 正反例。
  - `spec/pass/pipeline/npu_demo_lowering.md`、`test/passes/pipeline/test_npu_demo_lowering.py`、`test/kernel/test_matmul_symbolic_memory_genkernel.py`、`kernel/matmul/inputs_static_tile_dynamic.py`：用 pipeline/source 回归反推验证 post-decompose canonicalize 后 static/dynamic fill 消除，dynamic/dynamic acc fill 保留口径。
  - `test/tools/test_kernel_code_error_static_gate.py`：用静态门测试反推验证旧 private helper allowlist 已随删除同步清理。

- 减法检查：
  - 已删除旧 `kernel-decompose` fill 删除链路：`initial_zero_fill_for_fusion`、`loop_body_before_fusion_blocks_initial_fill`、`operations_before_index_block_alias_closure`、`erase_fill_with_verify_rollback`、`owner_symbol_for`、`has_positive_static_trip_count`、`acc_is_iter_ne_start`、`is_zero_fill_value`、`alias_closure_before_index`、`extend_alias_closure`、`operation_blocks_alias_closure`、`static_int_expr` 等旧逻辑不再出现在 `kernel_gen/`、`test/`、`spec/`；计划书与本记录仅保留历史基线 / 减法说明引用。
  - 新增 private callable：`_DmaCanonicalizationRules.has_later_matmul_or_private_alloc_dead_path(...)`，有效代码超过 5 行，未调用其它 private callable；承担 dynamic acc matmul 与受控 `scf.if` 两个 proof 的共享入口，直接内联到 rewrite 方法会让公开 pattern 方法过长且混合多类 dialect 证明分支。
  - 改动 private callable：`kernel/matmul/inputs_static_tile_dynamic.py::_assert_accumulator_source(...)`，有效代码超过 5 行，未调用其它 private callable；它是脚本自检 helper，随 static/dynamic 完成态从“要求 fill”改为“要求无 fill 且保留 accumulator matmul 顺序”。
  - 删除旧 rollback 单测辅助与 kernel-decompose 旧删除用例；旧行为迁移到 DMA canonicalization 测试，避免 kernel pass 继续背负 fill DSE 职责。
  - 验证命令：`rg --no-ignore -n 'initial_zero_fill_for_fusion|erase_fill_with_verify_rollback|owner_symbol_for|has_positive_static_trip_count|acc_is_iter_ne_start|loop_body_before_fusion_blocks_initial_fill|operations_before_index_block_alias_closure|alias_closure_before_index|operation_blocks_alias_closure|is_zero_fill_value' kernel_gen test spec || true` 无输出。

- 自检：
  - 公开 API：未新增、删除、重命名或改签名；未修改 `KernelDecomposePass`、`DmaFillOp`、`build_npu_demo_lowering_pipeline(...)` 公开入口；未新增 pipeline option。
  - 合同资产：`expectation/` 无 diff；旧 `expectation.pass.kernel_decompose` initial fill 删除 case 未运行为当前必过验收，仅按 DU3-B 作为历史只读来源记录。
  - 禁止修改面：`git diff --name-only | rg '^(expectation/|\.skills/|agents/standard/|AGENTS\.md|TODO\.md|DONE\.md|plan/1\.md)' || true` 无输出。
  - 能力探测：`rg -n 'hasattr\(ctx|getattr\(ctx|callable\(getattr\(ctx|emit_barrier' kernel_gen kernel || true` 无输出。
  - 文件级说明 / API 列表：已随实现文件职责变化更新 `kernel_decompose.py` 与 `canonicalization.py` 的说明；测试改动均通过公开 pass / operation 行为断言，不跨文件直连非公开 helper。
  - 质量与边界：反例覆盖 dynamic end、fusion、非零 fill、loop/body 读、partial write、nested region、target escape；实现遇未知 region / alias / effect 保守保留 fill，不做通用 CFG DSE。

- 结论：
  - 计划级 execute 已完成，可进入 `review`。

## 2026-06-08 睡觉小分队流转记录

- 已执行 `-next`：`OK: next T-20260608-197a37da`。
- 自动派发结果：`T-20260608-197a37da -> 不要啊教练`，当前阶段为 `review`。
- 已通过 `codex-multi-agents-tmux.sh -talk` 显式回报管理员 `神秘人`：execute 已完成、记录已写入、验证全绿、未改公开 API / expectation / 禁止修改面、已续接 review。

## 2026-06-08 不要啊教练 review

时间：2026-06-08 01:11 CST
经办人：不要啊教练
任务：T-20260608-197a37da / matmul-dynamic-acc-fill-canonicalization / review
结论：不通过；存在 1 个阻断项，退回 execute 收口。不得进入 `archive_acceptance`。

最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260608-matmul-dynamic-acc-fill-canonicalization`。
- 已执行 `git fetch origin --prune`。
- `HEAD=cd63f945117051f9ed9e2524d0dce2e77093e7b4`，`origin/main=4ecae4ac8d96508ea33d3e6f7255ec49289fe57f`，`merge-base=cd63f945117051f9ed9e2524d0dce2e77093e7b4`。
- `HEAD..origin/main` 仅为 `T-20260607-f7d1ad26 / prompt-guard-fullname-rong-architect` 的角色 prompt 与记录合并，未触及本任务实现 / spec / 测试 / 计划范围；当前 review 继续基于任务 worktree diff 审查。

审查范围：
- staged：`ARCHITECTURE/plan/matmul_dynamic_acc_fill_canonicalization.md`、本任务记录。
- unstaged：`kernel_gen/passes/kernel/kernel_decompose.py`、`kernel_gen/dialect/dma/canonicalization.py`、`kernel/matmul/inputs_static_tile_dynamic.py`、`spec/dialect/dma.md`、`spec/pass/kernel/kernel_decompose.md`、`spec/pass/pipeline/npu_demo_lowering.md`、`test/dialect/dma/helpers.py`、`test/dialect/dma/test_canonicalization.py`、`test/passes/kernel/test_kernel_decompose.py`、`test/passes/pipeline/test_npu_demo_lowering.py`、`test/kernel/test_matmul_symbolic_memory_genkernel.py`、`test/tools/test_kernel_code_error_static_gate.py`。

Findings：
- 阻断 1：`kernel_gen/dialect/dma/canonicalization.py:716` 的新增 alias/full-overwrite 路径会把后续 partial alias writer 当成对原 fill target 的完整覆盖，错误删除仍会被读取的 root fill。复现最小形态：`dma.fill(root, 0) -> dma.subview(root, size=4 of 8) -> dma.fill(subview, 1) -> dma.copy(reader, root)`；当前 canonicalization 后 root fill 被删除，只剩 subview fill，后续 root read 会观察到未初始化的非 subview 区域。影响：`dma.fill` canonicalization 违反 spec 中 partial writer / target read 必须保留 fill 的边界，属于语义错误。最小返工动作：收窄 `has_later_matmul_or_private_alloc_dead_path(...)` 中 `candidate.target in aliases` 的 full-overwrite 判断；只有能证明 writer 完整覆盖原 fill target 时才返回 True。对 `dma.subview`、partial `dma.reinterpret` 或其它仅覆盖局部的 alias target，必须保守保留或继续扫描且不得跳过后续 root read。补充 `test/dialect/dma/test_canonicalization.py` 反例，至少覆盖 `fill(root) -> subview(root partial) -> fill(subview) -> read root` 保留 root fill。

验证与核验证据：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/dma/test_canonicalization.py -k "fill"`：9 passed，3 deselected，1 warning。现有 fill 测试通过，但未覆盖阻断反例。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/kernel/test_kernel_decompose.py`：11 passed，1 warning。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/dialect/dma/canonicalization.py kernel_gen/passes/kernel/kernel_decompose.py test/dialect/dma/test_canonicalization.py test/passes/kernel/test_kernel_decompose.py kernel/matmul/inputs_static_tile_dynamic.py test/tools/test_kernel_code_error_static_gate.py`：退出码 0。
- `git diff --check && git diff --cached --check`：退出码 0。
- 阻断反例复现命令：
```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 - <<'PY'
from test.dialect.dma.helpers import (
    _canonicalized_module,
    _count_ops,
    _dim_array,
    _make_memory_type,
    _make_symbol_value_op,
    _TestOp,
    DmaFillOp,
    DmaSubviewOp,
    DmaCopyOp,
    i8,
)

root_type = _make_memory_type(shape=_dim_array([8]), stride=_dim_array([1]), element_type=i8)
sub_type = _make_memory_type(shape=_dim_array([4]), stride=_dim_array([1]), element_type=i8)
root = _TestOp(result_types=[root_type])
reader = _TestOp(result_types=[root_type])
c0 = _make_symbol_value_op(0)
c1 = _make_symbol_value_op(1)
c4 = _make_symbol_value_op(4)
sub = DmaSubviewOp(root.results[0], c0.results[0], c4.results[0], c1.results[0], sub_type)
module = _canonicalized_module([
    root, reader, c0, c1, c4,
    DmaFillOp(root.results[0], c0.results[0]),
    sub,
    DmaFillOp(sub.result, c1.results[0]),
    DmaCopyOp(reader.results[0], root.results[0]),
])
fill_count = _count_ops(module, DmaFillOp)
assert fill_count == 2, f"expected root fill and subview fill to remain; got {fill_count}\n{module}"
PY
```
当前结果：退出码 1，`AssertionError: expected root fill and subview fill to remain; got 1`。

执行记录核对：
- 执行记录已包含执行前阅读、最小功能闭环、验证、`Diff 反推自测`、`减法检查`、自检和结论。
- 记录已说明旧 `expectation.pass.kernel_decompose` initial fill 删除 case 按 DU3-B 为历史只读来源，不列当前必过合同验收。

Diff 反推审查：
- 已按真实 diff 核对 `kernel-decompose`：旧 initial fill 删除链路已移除，单独 pass 保留 fill 的方向符合计划。
- 已按真实 diff 核对 `dma.fill` canonicalization：dynamic acc 与 safe-if 新规则存在上述 partial alias writer 漏测和误删风险，需要返工。
- 已核对 pipeline/source 测试：static/dynamic 无 fill 与 dynamic/dynamic 保留 acc fill 的断言方向与 DU1-A / DU2-A 一致；阻断点不在 pipeline 顺序，而在底层 canonicalization proof 边界。
- 合同验收：本计划无当前必过 expectation；旧 expectation 仅历史只读，不作为通过依据。

减法审查：
- 旧 `kernel-decompose` fill 删除 helper 已删除，`rg --no-ignore -n 'initial_zero_fill_for_fusion|erase_fill_with_verify_rollback|owner_symbol_for|has_positive_static_trip_count|acc_is_iter_ne_start|loop_body_before_fusion_blocks_initial_fill|operations_before_index_block_alias_closure|alias_closure_before_index|operation_blocks_alias_closure|is_zero_fill_value' kernel_gen test spec` 无输出。
- 新增 / 改动 private callable 记录已覆盖，未发现小于 5 行有效代码的新增 / 改动 private callable；阻断点是新增 private proof 的语义边界，不是 private callable 形态。

禁止修改面与公开 API：
- `git diff --name-only -- .skills agents/standard AGENTS.md TODO.md DONE.md expectation plan/1.md agents/codex-multi-agents/agents-lists.md` 无输出；cached 同范围无输出。
- 未发现 `KernelDecomposePass`、`DmaFillOp`、`build_npu_demo_lowering_pipeline(...)` 签名或 pipeline option 改动。
- `rg -n 'hasattr\(ctx|getattr\(ctx|callable\(getattr\(ctx|emit_barrier' kernel_gen kernel test || true` 无输出。

最小返工验收：
- 修复 `kernel_gen/dialect/dma/canonicalization.py` 中 alias writer 判断，补充上述 partial subview writer + root read 反例测试。
- 复跑：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/dma/test_canonicalization.py -k "fill"`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/kernel/test_kernel_decompose.py`
  - `git diff --check && git diff --cached --check`
- 任务记录补充返工收口、Diff 反推自测、减法检查和自检。

自检：
- 已读取实际 diff，而不是只看执行摘要。
- 已核对 latest main、执行记录、公开 API、合同验收、禁止修改面、private callable 与 diff check。
- 因存在可复现语义阻断，结论不得写通过。

## 2026-06-08 睡觉小分队 execute 返工收口

时间：2026-06-08 01:18 CST
经办人：睡觉小分队
任务：T-20260608-197a37da / matmul-dynamic-acc-fill-canonicalization / execute 返工
任务目标：修复 review 阻断项，避免 `dma.fill` canonicalization 把 partial alias writer 误判为对 root fill target 的完整覆盖。

改动：
- 已处理 review 阻断 1：`kernel_gen/dialect/dma/canonicalization.py` 中 `has_later_matmul_or_private_alloc_dead_path(...)` 新增局部 `full_aliases` 集合，把“参与读写阻断的 aliases”和“可证明完整覆盖原 fill target 的 aliases”分开。
- `dma.subview`、`dma.reinterpret`、非完整 `dma.view` 等局部 alias 仍会进入 `aliases` 参与读 / 写 / escape 保守阻断，但不再进入完整覆盖判定；后续 `dma.fill` / `dma.copy` / `dma.broadcast` / `dma.deslice` 只有 target 属于 `full_aliases` 时才允许返回 True 删除原 fill。
- dynamic acc matmul 分支改为要求 matmul out 属于 `body_full_aliases`，避免 partial alias matmul output 删除 root fill。
- safe-if 分支内 full `dma.deslice` 覆盖也要求 deslice target 属于 `branch_full_aliases`，partial alias writer 保守失败。
- `test/dialect/dma/test_canonicalization.py` 新增反例 `test_dma_fill_canonicalization_keeps_root_fill_before_partial_alias_writer_and_root_read`，覆盖 `fill(root) -> subview(root partial) -> fill(subview) -> read(root)` 必须保留 root fill。

失败复现：
- 新增测试在修复前执行 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/dma/test_canonicalization.py -k partial_alias_writer` 失败：`expected 2 fills, got 1`，复现 review 记录中的误删路径。

验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/dma/test_canonicalization.py -k "partial_alias_writer or fill"`：10 passed，3 deselected，1 warning。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/dma/test_canonicalization.py -k fill`：10 passed，3 deselected，1 warning。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/kernel/test_kernel_decompose.py`：11 passed，1 warning。
- `git diff --check && git diff --cached --check`：退出码 0。
- 额外自测：`PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/dialect/dma/canonicalization.py test/dialect/dma/test_canonicalization.py`：退出码 0。
- 额外自测：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/dma/test_canonicalization.py`：13 passed，1 warning。

Diff 反推自测：
- 实际改动文件 `kernel_gen/dialect/dma/canonicalization.py`：反推测试为 `test/dialect/dma/test_canonicalization.py -k fill` 与全量 `test/dialect/dma/test_canonicalization.py`，锁定 dead-fill 正例仍删除、partial alias writer + root read 反例保留。
- 实际改动文件 `test/dialect/dma/test_canonicalization.py`：新增反例先失败后通过，证明测试能捕获本次 review 阻断。
- 回归触达 `test/passes/kernel/test_kernel_decompose.py`：确认返工未影响 `kernel-decompose` 只分解不删 fill 的既有完成态。

减法检查：
- 新增 private callable：无。
- 改动 private callable：`_DmaCanonicalizationRules.has_later_matmul_or_private_alloc_dead_path(...)`；仍超过 5 行有效代码，未新增调用其它 private callable；本轮只在函数内部拆分 `aliases` / `full_aliases` 语义，不新增外露 helper。
- 被替代旧逻辑：替代原先 `candidate.target in aliases` 直接视为完整覆盖的过宽判断；partial alias writer 现在保守进入 effect / operand 阻断路径，或在分支内直接失败，不会跳过后续 root read。
- 保留旧逻辑依据：`dma.reshape` 仍可随 source full-alias 进入 `full_aliases`，因为 reshape verifier 约束为同元素 / 同空间 / 同 numel 的连续全量重解释；`dma.subview` 和 `dma.reinterpret` 未加入 full-alias，避免无法证明完整覆盖时误删。

自检：
- 公开 API：未新增、删除、重命名或改签名；未修改 `DmaFillOp`、`KernelDecomposePass`、pipeline option 或稳定错误文本。
- 合同资产：未修改 `expectation/`，旧 `expectation.pass.kernel_decompose` initial fill 删除 case 仍仅作历史只读来源。
- 禁止修改面：`git diff --name-only | rg '^(expectation/|\.skills/|agents/standard/|AGENTS\.md|TODO\.md|DONE\.md|plan/1\.md|agents/codex-multi-agents/agents-lists\.md)' || true` 无输出。
- 能力探测：`rg -n 'hasattr\(ctx|getattr\(ctx|callable\(getattr\(ctx|emit_barrier' kernel_gen kernel test || true` 无输出。
- 边界：partial alias writer 不再删除 root fill；后续 root read 会保留 fill；dynamic acc、safe-if、kernel-decompose 回归通过。

结论：
- review 阻断项已收口，可重新进入 `review`。

## 2026-06-08 睡觉小分队返工流转记录

时间：2026-06-08 01:18 CST
经办人：睡觉小分队
任务：T-20260608-197a37da / execute 返工 -> review
改动：已执行 `-next`，脚本输出 `OK: next T-20260608-197a37da`，自动派发 `T-20260608-197a37da -> 不要啊教练`。
验证：重新读取 `/home/lfr/kernelcode_generate/TODO.md`，当前任务为 `review / 不要啊教练 / 进行中`。
自检：状态推进通过脚本完成，未手工修改 `TODO.md`。
结论：已通过 `codex-multi-agents-tmux.sh -talk` 显式回报管理员 `神秘人`，等待 review 复审。

## 2026-06-08 不要啊教练 review 复审记录

时间：2026-06-08 01:23 CST
经办人：不要啊教练
任务：T-20260608-197a37da / matmul-dynamic-acc-fill-canonicalization / review 复审
任务目标：复审 execute 返工是否收口上轮 review 阻断，重点核对 partial alias writer 不再被当作 root fill target 完整覆盖，并核对新增反例、验证、Diff 反推自测、减法检查和自检记录。

最新同步现场：
- worktree：`/home/lfr/kernelcode_generate/wt-20260608-matmul-dynamic-acc-fill-canonicalization`
- 计划书：`ARCHITECTURE/plan/matmul_dynamic_acc_fill_canonicalization.md`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/24/20260608-matmul-dynamic-acc-fill-canonicalization.md`
- `git fetch origin --prune` 已执行。
- `HEAD=cd63f945117051f9ed9e2524d0dce2e77093e7b4`
- `origin/main=4ecae4ac8d96508ea33d3e6f7255ec49289fe57f`
- `merge-base=cd63f945117051f9ed9e2524d0dce2e77093e7b4`
- 当前分支落后 `origin/main` 1 个提交：`4ecae4ac Merge prompt guard fullname rong architect`。该提交为提示词 / 任务记录合并，不触及本任务实现、spec、test、计划书或 expectation diff，未作为本轮阻断。

结论先行：
- Finding：无阻断项。
- 最小需改项：无。
- 复审结论：通过，可按计划级链路进入 `archive_acceptance` / 计划书入档验收；不得直接进入 `merge`。

执行记录核对：
- execute 返工记录已写明上轮阻断复现：修复前 `pytest -q test/dialect/dma/test_canonicalization.py -k partial_alias_writer` 可复现 `expected 2 fills, got 1`。
- execute 返工记录已写明修复点：`aliases` 继续用于读 / 写 / escape 保守阻断，新增 `full_aliases` 仅用于可证明完整覆盖原 fill target 的删除判定。
- execute 返工记录已补齐验证、`Diff 反推自测`、`减法检查`、自检和结论。

Diff 反推审查：
- `kernel_gen/dialect/dma/canonicalization.py`：已核对 `has_later_matmul_or_private_alloc_dead_path(...)`。`dma.subview`、`dma.reinterpret`、非完整 `dma.view` 只进入 `aliases`，不进入 `full_aliases`；后续 `dma.fill` / `dma.copy` / `dma.broadcast` / `dma.deslice` 只有 target 属于 `full_aliases` 时才允许删除原 fill。上轮阻断的 `fill(root) -> subview(root partial) -> fill(subview) -> read(root)` 路径会保留 root fill。
- `test/dialect/dma/test_canonicalization.py`：已核对新增反例 `test_dma_fill_canonicalization_keeps_root_fill_before_partial_alias_writer_and_root_read`，断言 canonicalization 后保留 2 个 `DmaFillOp` 和 1 个 `DmaSubviewOp`，覆盖 partial alias writer + root read 的误删风险。
- `kernel_gen/passes/kernel/kernel_decompose.py` 与 `test/passes/kernel/test_kernel_decompose.py`：复审重点仍符合“只分解、不删除 fill”的当前计划口径，返工未扩大到重新引入 kernel-decompose fill 删除链路。
- `spec/` 与 pipeline/source 相关测试改动未反推出新的公开 API 改签名或新的必过 expectation。

本轮复验命令：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/dma/test_canonicalization.py -k partial_alias_writer`：1 passed，12 deselected，1 warning。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/dma/test_canonicalization.py -k fill`：10 passed，3 deselected，1 warning。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/kernel/test_kernel_decompose.py`：11 passed，1 warning。
- `git diff --cached --check && git diff --check`：退出码 0。

门禁与禁止修改面：
- `git diff --name-only -- .skills agents/standard AGENTS.md TODO.md DONE.md expectation plan/1.md agents/codex-multi-agents/agents-lists.md` 无输出；cached 同范围无输出。
- `rg -n 'hasattr\(ctx|getattr\(ctx|callable\(getattr\(ctx|emit_barrier' kernel_gen kernel test || true` 无输出。
- `rg --no-ignore -n 'initial_zero_fill_for_fusion|erase_fill_with_verify_rollback|owner_symbol_for|has_positive_static_trip_count|acc_is_iter_ne_start|loop_body_before_fusion_blocks_initial_fill|operations_before_index_block_alias_closure|alias_closure_before_index|operation_blocks_alias_closure|is_zero_fill_value' kernel_gen test spec` 无输出。
- 未修改 `expectation/`；本计划当前无必过 expectation，旧 `expectation.pass.kernel_decompose` initial fill 删除 case 仅作为历史只读来源，不作为本轮通过依据或阻断项。

减法审查：
- 新增 private callable：无。
- 改动 private callable：`_DmaCanonicalizationRules.has_later_matmul_or_private_alloc_dead_path(...)`，本轮只是收窄别名完整覆盖判定，没有新增跨文件 private API 调用。
- 已删除旧 kernel-decompose fill 删除 helper 未回流；未发现以测试便利为由直接调用当前文件外非公开 API 的新增用法。

公开 API 与规范审查：
- 未发现 `DmaFillOp`、`KernelDecomposePass`、pipeline option、工具入口、公开错误文本或 spec/API 列表发生未经确认的新增、删除、重命名或改签名。
- 未发现 `hasattr/getattr/callable(getattr)` 形式的上下文能力探测。
- 未发现除装饰器必需闭包外的新增函数体内嵌套函数。

自检：
- 已读取实际 diff 与 execute 返工记录，而不是只依赖任务摘要。
- 已按上轮 Finding 反推复验新增反例，并复跑任务目标要求的 `fill`、`kernel_decompose`、diff check。
- 已核对禁止修改面、公开 API、private API 边界、expectation 口径、减法检查和任务记录完整性。

结论：
- T-20260608-197a37da review 复审通过，无阻断、无最小需改项。
- 下一步按计划级链路流转到 `archive_acceptance` / 计划书入档验收，不得直接进入 `merge`。

## 2026-06-08 不要啊教练 review 流转记录

时间：2026-06-08 01:27 CST
经办人：不要啊教练
任务：T-20260608-197a37da / review -> archive_acceptance
流转：
- 已执行标准脚本 `-next`，脚本输出 `OK: next T-20260608-197a37da`。
- 已按计划级链路续接为 `archive_acceptance`，指派给 `提莫炖蘑菇`，脚本输出 `OK: next-dispatch T-20260608-197a37da -> 提莫炖蘑菇`。
- 脚本已自动通知 `提莫炖蘑菇` 与管理员 `神秘人`。
验证：
- 重新读取 `TODO.md`：当前任务为 `archive_acceptance / 提莫炖蘑菇 / 进行中`。
自检：
- 状态推进通过任务脚本完成，未手工修改 `TODO.md`。
- review 复审只追加任务记录，未修改实现、spec、test、expectation 或敏感目录。
结论：
- review 阶段已释放，等待 `archive_acceptance` / 计划书入档验收。

## 2026-06-08 提莫炖蘑菇 archive_acceptance 记录

时间：2026-06-08 01:31 +0800
经办人：提莫炖蘑菇
任务：T-20260608-197a37da / matmul-dynamic-acc-fill-canonicalization / archive_acceptance
任务目标：执行计划级 review 通过后的计划书入档验收，核对计划正文、任务记录、最新同步现场、当前无必过 expectation、公开 API / private API 边界、spec/test/pipeline/source 同步、Diff 反推自测、减法检查、自检、敏感目录空 diff 与可归档性。

结论先行：
- Finding：无阻断项。
- 最小需改项：无。
- archive_acceptance 结论：通过。可按计划级链路续接 `merge`，但本阶段不直接合并。

最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260608-matmul-dynamic-acc-fill-canonicalization`。
- `git fetch --prune origin` 已执行。
- `HEAD=cd63f945117051f9ed9e2524d0dce2e77093e7b4`，`origin/main=4ecae4ac8d96508ea33d3e6f7255ec49289fe57f`，`merge-base=cd63f945117051f9ed9e2524d0dce2e77093e7b4`，ahead/behind=`0 1`。
- `HEAD..origin/main` 仅触碰角色 prompt 与 `20260607-prompt-guard-fullname-rong-architect.md` 记录，未触碰本任务实现、spec、test、计划书、记录或 `expectation/` 路径；未发现覆盖风险。

计划正文与记录核对：
- 计划书：`ARCHITECTURE/plan/matmul_dynamic_acc_fill_canonicalization.md`。
- 计划 index blob：`100644 7b93cdead7616b30207220095df489d94287e301 0`。
- 计划 sha256：`8a6cf035d3b60df8465d3ae143e9f6e677f4f3e1432046f4e7b970c068d27d1b`，与管理员创建记录一致。
- 计划正文已写明 Draft 2-R5、DU1-A / DU2-A / DU3-B 用户确认、两路最终 subagent strict review 通过、守护最终检验通过、固定链路 `execute -> review -> archive_acceptance -> merge/归档`。
- 任务记录已包含管理员创建、execute、首次 review 退回、execute 返工收口、review 复审通过和本次入档验收记录；记录文件当前作为候选资产纳入待合入 diff。
- 当前候选现场为计划书与任务记录 staged add，代码 / spec / test 为 unstaged working-tree diff；archive_acceptance 已按完整 working tree diff 验收。merge 阶段需把计划书、任务记录、实现、spec、测试同批合入。

合同验收与 expectation：
- 本计划当前无必过 `expectation`。
- 旧 `expectation.pass.kernel_decompose` initial fill 删除 case 按 DU3-B 只作为历史只读来源，不列为当前必过合同验收，不作为本次通过依据。
- `expectation/` 无 diff、无 staged diff、无 status 输出；未修改、移动、新建或删除合同资产。

公开 API / private API 边界：
- 未发现 `KernelDecomposePass`、`DmaFillOp`、`build_npu_demo_lowering_pipeline(...)`、pipeline option、工具入口或稳定错误文本发生未经确认的新增、删除、重命名或改签名。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py`：exit=0，`4 passed`；锁定当前 diff private callable 形态与跨文件 private API 边界。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_kernel_code_error_static_gate.py`：exit=0，`3 passed`；锁定 KCE / 静态门禁。
- `rg -n 'hasattr\([^\n]*(ctx|context)|getattr\([^\n]*(ctx|context)|callable\(getattr\([^\n]*(ctx|context)|emit_barrier' kernel_gen kernel test`：exit=1，无输出；未发现上下文能力探测写法。

复验命令：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/dma/test_canonicalization.py -k partial_alias_writer`：exit=0，`1 passed, 12 deselected, 1 warning`；锁定 partial alias writer 不再误删 root fill。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/dma/test_canonicalization.py -k fill`：exit=0，`10 passed, 3 deselected, 1 warning`；锁定 dma.fill 正反例完成态。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/dma/test_canonicalization.py`：exit=0，`13 passed, 1 warning`；闭合 DMA canonicalization 总体验收。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/kernel/test_kernel_decompose.py`：exit=0，`11 passed, 1 warning`；锁定 kernel-decompose 只分解、不删 fill。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k "matmul or symbol_hoist_pipeline"`：exit=0，`2 passed, 9 deselected, 1 warning`；锁定 npu-demo-lowering pipeline dump 完成态。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py`：exit=0，`4 passed, 1 warning`；锁定 matmul source 同步。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/dialect/dma/canonicalization.py kernel_gen/passes/kernel/kernel_decompose.py test/dialect/dma/test_canonicalization.py test/passes/kernel/test_kernel_decompose.py test/passes/pipeline/test_npu_demo_lowering.py test/kernel/test_matmul_symbolic_memory_genkernel.py kernel/matmul/inputs_static_tile_dynamic.py test/tools/test_kernel_code_error_static_gate.py`：exit=0。
- `git diff --cached --check && git diff --check`：exit=0。

文本门禁与敏感目录：
- `rg --no-ignore -n 'initial_zero_fill_for_fusion|erase_fill_with_verify_rollback|owner_symbol_for|has_positive_static_trip_count|acc_is_iter_ne_start|loop_body_before_fusion_blocks_initial_fill|operations_before_index_block_alias_closure|alias_closure_before_index|operation_blocks_alias_closure|is_zero_fill_value' kernel_gen test spec`：exit=1，无输出；旧 kernel-decompose fill 删除 helper 未残留在实现 / 测试 / spec。
- `git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md plan/1.md agents/codex-multi-agents/agents-lists.md`：无输出。
- `git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md plan/1.md agents/codex-multi-agents/agents-lists.md`：无输出。
- `git diff --cached --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md plan/1.md agents/codex-multi-agents/agents-lists.md`：无输出。

Diff 反推验收：
- `kernel_gen/passes/kernel/kernel_decompose.py` / `test/passes/kernel/test_kernel_decompose.py`：由 kernel-decompose 全量测试覆盖，证明 fusion 分解、fill 保留和旧 rollback / fill 删除链路未回流。
- `kernel_gen/dialect/dma/canonicalization.py` / `test/dialect/dma/helpers.py` / `test/dialect/dma/test_canonicalization.py`：由 partial alias writer、`-k fill` 和全量 DMA canonicalization 覆盖，证明 dynamic acc、positive runtime tile step、safe-if 正例和反例边界。
- `spec/dialect/dma.md`、`spec/pass/kernel/kernel_decompose.md`、`spec/pass/pipeline/npu_demo_lowering.md` 与 pipeline/source 测试：由 pipeline dump 与 matmul source pytest 覆盖，证明 DU1-A / DU2-A / DU3-B 口径同步。
- `test/tools/test_kernel_code_error_static_gate.py`：由 KCE 静态门覆盖，证明旧 allowlist 死配置已清理。
- `expectation` 单列为合同验收资产，本计划无当前必过 expectation；未把 expectation 当作 diff 反推测试。

减法审查：
- 旧 `kernel-decompose` fill 删除职责已迁出并删除，旧 helper 文本门禁无命中；`kernel-decompose` 当前只负责 fusion 分解。
- 新增 / 改动 private callable 以 review 复审记录为准：新增 / 改动集中在 `_DmaCanonicalizationRules.has_later_matmul_or_private_alloc_dead_path(...)` 与脚本自检 helper；仓库 private conformance 已通过，未发现小于 5 行有效代码、private callable 调用 private callable、跨文件直连非公开 API 或测试绕过公开 API 的当前阻断。
- partial alias writer 返工已把 `aliases` 与 `full_aliases` 区分清楚，保留 partial alias 读写阻断语义，不再把局部 alias writer 当作 root 完整覆盖。

自检：
- 已读取实际 diff、计划正文、任务记录和 review 复审记录，并核对 latest main；未只依赖摘要。
- 已核对当前无必过 expectation、敏感目录空 diff、公开 API / private API 边界、spec/test/pipeline/source 同步、Diff 反推自测、减法检查和自检记录。
- 本轮只追加入档验收记录，未修改实现、spec、test、plan、expectation 或任务状态文件。
- 未发现剩余可执行返工项。

可归档性：
- 计划级入档验收通过；可续接 `merge`。
- 合并阶段必须把计划书、任务记录、实现、spec、测试同批合入，并在合并记录中再次核对 staged / unstaged 候选资产，避免遗漏当前 working-tree 实现 diff。

## 2026-06-08 提莫炖蘑菇 archive_acceptance 流转记录

时间：2026-06-08 01:33 +0800
经办人：提莫炖蘑菇
任务：T-20260608-197a37da / archive_acceptance -> merge
任务目标：按计划级链路把已通过入档验收的候选续接给 merge 角色。
改动：已执行标准脚本 `codex-multi-agents-task.sh -next -type merge -auto`；脚本输出 `OK: next T-20260608-197a37da`、`OK: auto-dispatch T-20260608-197a37da -> 李白`，并向 `李白` 与管理员 `神秘人` 发送 talk。
验证：重新读取主仓 `TODO.md`，当前任务为 `merge / 李白 / 进行中`；交接消息已写明合并阶段必须同批合入计划书、任务记录、实现、spec、测试，并再次核对 staged / unstaged 候选资产、`expectation/` 无 diff、敏感目录空 diff、`git diff --check` 与 `git diff --cached --check`。
自检：状态推进通过标准脚本完成，未手工修改 `TODO.md`；本轮只追加 archive_acceptance 记录与流转记录，未修改实现、spec、test、plan 或 `expectation/`。
结论：archive_acceptance 已释放，下一阶段由 `李白` merge。

## 2026-06-08 李白 merge 合并前记录

时间：2026-06-08 01:36 +0800
经办人：李白
任务：T-20260608-197a37da / matmul-dynamic-acc-fill-canonicalization / merge
任务目标：按计划级合并规范核对 latest main、archive_acceptance 结论、当前 staged 计划 / 记录与 working-tree 实现 diff、`expectation/` 无 diff、敏感目录空 diff、`git diff --check` / `--cached --check`，并准备同批合入计划书、任务记录、实现、spec、测试和计划归档。

最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260608-matmul-dynamic-acc-fill-canonicalization`。
- 合并前已执行 `git fetch --prune origin`，发现任务分支落后 `origin/main` 1 个提交。
- `HEAD..origin/main` 仅包含 `4ecae4ac8d96508ea33d3e6f7255ec49289fe57f Merge prompt guard fullname rong architect`，触碰角色 prompt 与 `20260607-prompt-guard-fullname-rong-architect.md` 记录；与本任务计划书、任务记录、实现、spec、test、`expectation/` 均无路径重叠。
- 已执行 `git merge --ff-only origin/main`，本任务 worktree 快进到 latest main；未发生冲突，候选 staged / working-tree diff 保留。
- 同步后 `git rev-parse HEAD origin/main`：`HEAD=4ecae4ac8d96508ea33d3e6f7255ec49289fe57f`，`origin/main=4ecae4ac8d96508ea33d3e6f7255ec49289fe57f`。
- 同步后 `git rev-list --left-right --count HEAD...origin/main`：`0 0`。

链路与合入范围：
- 计划级链路：`execute -> review -> archive_acceptance -> merge`；archive_acceptance 结论为通过，无阻断、无最小需改项。
- staged 候选：`ARCHITECTURE/plan/matmul_dynamic_acc_fill_canonicalization.md` 与 `agents/codex-multi-agents/log/task_records/2026/24/20260608-matmul-dynamic-acc-fill-canonicalization.md`。
- staged 计划 index blob：`100644 7b93cdead7616b30207220095df489d94287e301 0`。
- 计划 sha256：`8a6cf035d3b60df8465d3ae143e9f6e677f4f3e1432046f4e7b970c068d27d1b`。
- working-tree 实现 / spec / test diff：12 个路径，合并阶段必须同批 stage 并合入，避免遗漏当前 working-tree 实现 diff。
- 计划原路径：`ARCHITECTURE/plan/matmul_dynamic_acc_fill_canonicalization.md`。
- 计划归档目标：`agents/codex-multi-agents/log/task_records/done_plan/2026/matmul_dynamic_acc_fill_canonicalization.md`；本记录写入后执行 `git mv`，并在提交前复核源路径已移出 `ARCHITECTURE/plan/`、目标进入 staged diff。

同批合入文件：
- `kernel/matmul/inputs_static_tile_dynamic.py`
- `kernel_gen/dialect/dma/canonicalization.py`
- `kernel_gen/passes/kernel/kernel_decompose.py`
- `spec/dialect/dma.md`
- `spec/pass/kernel/kernel_decompose.md`
- `spec/pass/pipeline/npu_demo_lowering.md`
- `test/dialect/dma/helpers.py`
- `test/dialect/dma/test_canonicalization.py`
- `test/kernel/test_matmul_symbolic_memory_genkernel.py`
- `test/passes/kernel/test_kernel_decompose.py`
- `test/passes/pipeline/test_npu_demo_lowering.py`
- `test/tools/test_kernel_code_error_static_gate.py`
- `agents/codex-multi-agents/log/task_records/2026/24/20260608-matmul-dynamic-acc-fill-canonicalization.md`
- `agents/codex-multi-agents/log/task_records/done_plan/2026/matmul_dynamic_acc_fill_canonicalization.md`

验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/dma/test_canonicalization.py -k fill`：exit=0，`10 passed, 3 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/dma/test_canonicalization.py`：exit=0，`13 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/kernel/test_kernel_decompose.py`：exit=0，`11 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k "matmul or symbol_hoist_pipeline"`：exit=0，`2 passed, 9 deselected, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py`：exit=0，`4 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py test/tools/test_kernel_code_error_static_gate.py`：exit=0，`7 passed`。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/dialect/dma/canonicalization.py kernel_gen/passes/kernel/kernel_decompose.py test/dialect/dma/test_canonicalization.py test/passes/kernel/test_kernel_decompose.py test/passes/pipeline/test_npu_demo_lowering.py test/kernel/test_matmul_symbolic_memory_genkernel.py kernel/matmul/inputs_static_tile_dynamic.py test/tools/test_kernel_code_error_static_gate.py`：exit=0。
- `git diff --cached --check && git diff --check`：exit=0。
- `rg --no-ignore -n 'initial_zero_fill_for_fusion|erase_fill_with_verify_rollback|owner_symbol_for|has_positive_static_trip_count|acc_is_iter_ne_start|loop_body_before_fusion_blocks_initial_fill|operations_before_index_block_alias_closure|alias_closure_before_index|operation_blocks_alias_closure|is_zero_fill_value' kernel_gen test spec || true`：无输出；旧 kernel-decompose fill 删除 helper 未残留。
- `rg -n 'hasattr\([^\n]*(ctx|context)|getattr\([^\n]*(ctx|context)|callable\(getattr\([^\n]*(ctx|context)|emit_barrier' kernel_gen kernel test || true`：无输出；未发现上下文能力探测写法。

合同验收与敏感目录：
- 本计划当前无必过 `expectation`；旧 `expectation.pass.kernel_decompose` initial fill 删除 case 按 DU3-B 只作为历史只读来源，不列为当前必过合同验收。
- `git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md plan/1.md agents/codex-multi-agents/agents-lists.md`：无输出。
- `git diff --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md plan/1.md agents/codex-multi-agents/agents-lists.md`：无输出。
- `git diff --cached --name-status -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md plan/1.md agents/codex-multi-agents/agents-lists.md`：无输出。
- 不纳入 `.skills/`、`expectation/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`plan/1.md` 或 `agents-lists.md`。

冲突处理与剩余风险：
- 与 latest main 同步时仅 fast-forward prompt 任务提交，未发生冲突。
- 合并阶段不补做实现、审查或架构裁定；只合入已通过 archive_acceptance 的候选。
- 提交前将复核 staged diff、计划归档源/目标、禁止面空 diff、`git diff --check` / `--cached --check` 和 worktree 无剩余未 staged 授权候选。

结论：合并前记录已写入任务链记录；下一步执行计划归档、stage 实现 / spec / test / 任务记录并提交推送。
