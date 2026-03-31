# 20260319-dialect-nn-matmul-refactor

- 任务: T-20260319-b30e7676 / T-20260319-d3fd8cd7
- 执行人: 睡觉小分队
- worktree: /home/lfr/kernelcode_generate/wt-20260319-dialect-nn-matmul
- 时间: 2026-03-19 02:18:00 +0800

## 本次改动
- 删除 nn.matmul 的“待补/未实现”口径，将其纳入核心组成、Op 定义与 parse/print 约束。
- 将 TC-NN-MM-001..004 提升为正式测试清单条目，并与现有 test_matmul_* 一一映射。
- 明确 stride 口径为“不做跨 operand/result stride 等价校验”，同步测试目标与文案，避免 spec 超出实现。

## 变更文件
- /home/lfr/kernelcode_generate/wt-20260319-dialect-nn-matmul/spec/dialect/nn.md

## 实现/测试待跟进
- 无（当前仅 spec 收敛，已与现有实现/测试对齐）。

## 审查记录

### T-20260319-dbe84785

- 时间: 2026-03-19 02:22:40 +0800
- 角色: `提莫炖蘑菇`
- worktree: `/home/lfr/kernelcode_generate/wt-20260319-dialect-nn-matmul`
- 审查范围:
  - `spec/dialect/nn.md`
  - `python/dialect/nn.py`
  - `python/dialect/__init__.py`
  - `test/dialect/test_nn_dialect.py`
- 结论: 不通过
- 不通过原因（需改动位置 + 原因 + 建议改法）:
  - `spec/dialect/nn.md` 的“测试目标”对 `nn.matmul` 的覆盖表述超出当前测试实际覆盖范围:
    - 现状: spec 宣称测试覆盖 `nn.matmul` 的 `space` 约束与 rank 校验（`spec/dialect/nn.md` 的“测试目标”中包含“rank...与 space 约束”），但当前 `TC-NN-MM-001..004` 仅覆盖合法通过、contracting 维度不匹配、结果 shape 不匹配、模块 round-trip（`test/dialect/test_nn_dialect.py` 的 `test_matmul_*`），没有覆盖 `space mismatch` / `attr space mismatch` / `rank!=2` 等错误路径。
    - 影响: spec/测试无法一一对应闭环；后续合并与演进时会误判“已覆盖的错误边界”，增加回归风险。
    - 建议改法（改进测试任务，推荐优先）:
      - 新增 matmul 的空间错误路径测试（建议新增用例或扩展 TC-NN-MM-*）：
        - operands space mismatch: `lhs.space != rhs.space` -> `VerifyException`（对应 `python/dialect/nn.py` 中 `nn.matmul operands must use the same space`）
        - attr space mismatch: `op.space != operand space` 或 `op.space != result space` -> `VerifyException`
      - 新增 matmul 的 rank 错误路径测试: 传入 rank!=2 的 `NnMemoryType`，验证报错 `nn.matmul requires rank-2 memory types`。
      - 可选补齐 element_type mismatch 测试: `lhs/rhs/result element_type` 不一致时报错（对应 `nn.matmul operand/result element_type must match`）。
    - 建议改法（改进 spec 任务，备选）:
      - 若短期不补测，则需在 spec “测试目标”中把 `nn.matmul` 的覆盖表述收敛到当前确实覆盖的点（shape 与 module round-trip），避免 spec 超出测试能力。

- 补充复核（2026-03-19 02:25:43 +0800，T-20260319-71490b5a 落地后）:
  - `test/dialect/test_nn_dialect.py` 已新增 `TC-NN-MM-005..008` 覆盖 `space mismatch / attr space mismatch / rank!=2 / element_type mismatch`，已能支撑 spec 中“rank...与 space 约束”的测试目标。
  - 但 `spec/dialect/nn.md` 的“测试清单”仍仅列出 `TC-NN-MM-001..004`（未列出 `TC-NN-MM-005..008`），不满足“测试清单与实际测试用例一一对应”的口径。
  - 建议改法（改进 spec 任务，推荐）: 在 `spec/dialect/nn.md` 的“测试清单”中补充 `TC-NN-MM-005..008 -> test_matmul_op_space_mismatch / test_matmul_op_attr_space_mismatch / test_matmul_op_rank_mismatch / test_matmul_op_element_type_mismatch` 映射，并在“用例与 Op 覆盖关系”中同步更新表述（如需）。

## T-20260319-71490b5a

- 时间：2026-03-19 02:24:51 +0800
- 角色：`金铲铲大作战`
- 任务描述：补齐 nn.matmul 错误边界测试（space mismatch、attr space mismatch、rank!=2，附加 element_type mismatch）。
- worktree：`/home/lfr/kernelcode_generate/wt-20260319-dialect-nn-matmul`
- 变更文件：
  - `test/dialect/test_nn_dialect.py`
- 变更摘要：
  - 新增 matmul 边界用例覆盖 space mismatch、attr space mismatch、rank!=2。
  - 追加 element_type mismatch 用例。
- 测试说明：
  - `pytest -q test/dialect/test_nn_dialect.py`
  - 结果：20 passed in 0.40s
- 下一阶段申请：
  - 申请继续审查 matmul 相关实现与测试覆盖。

## T-20260319-692290f6

- 时间：2026-03-19 02:36:00 +0800
- 角色：`朽木露琪亚`
- 任务描述：改进 `spec/dialect/nn.md`，补齐 `nn.matmul` 测试清单中的 `TC-NN-MM-005..008`，并映射到当前真实测试函数；同步收敛测试目标与覆盖关系表述，不改 `python/test`。
- worktree：`/home/lfr/kernelcode_generate/wt-20260319-dialect-nn-matmul`
- 变更文件：
  - `spec/dialect/nn.md`
- 变更摘要：
  - 将 `文档信息` 中的最后修改人更新为 `朽木露琪亚`。
  - 在 `测试目标` 中把 `nn.matmul` 的覆盖表述收敛为当前实现与测试已覆盖的 `rank`、contracting/result shape、`space` 与 `element_type` 约束，并保留“不做跨 operand/result stride 等价校验”的现有口径。
  - 在 `测试清单` 中补齐 `TC-NN-MM-005..008`，分别映射到 `test_matmul_op_space_mismatch`、`test_matmul_op_attr_space_mismatch`、`test_matmul_op_rank_mismatch`、`test_matmul_op_element_type_mismatch`。
  - 在 `用例与 Op 覆盖关系` 中同步说明 `nn.matmul` 当前已由独立 verifier/round-trip 测试覆盖 contracting dim、result shape、operand/op `space`、rank、`element_type` 与模块 round-trip，避免 spec 仍停留在只列 `TC-NN-MM-001..004` 的旧口径。
- 影响范围：
  - 仅更新 `spec/dialect/nn.md`；未修改实现或测试。
- 测试说明：
  - 按任务要求未执行测试。
- 后续待跟进项：
  - 无新增实现/测试任务；本次 spec 已与当前 `test/dialect/test_nn_dialect.py` 中 `TC-NN-MM-001..008` 的现状对齐。
- 下一阶段申请：
  - 建议进入 `dialect/nn matmul` 链路再次审查，重点核对 `spec/dialect/nn.md` 的测试目标、测试清单与 `test/dialect/test_nn_dialect.py` 是否已完全一一对应。

### T-20260319-40900394

- 时间: 2026-03-19 02:33:15 +0800
- 角色: `提莫炖蘑菇`
- worktree: `/home/lfr/kernelcode_generate/wt-20260319-dialect-nn-matmul`
- 审查范围:
  - `spec/dialect/nn.md`
  - `python/dialect/nn.py`
  - `python/dialect/__init__.py`
  - `test/dialect/test_nn_dialect.py`
- 结论: 不通过
- 不通过原因（需改动位置 + 原因 + 建议改法）:
  1. `spec/dialect/nn.md` 的“测试目标”与当前测试现状不一致（stride 覆盖宣称无对应测试）：
     - 现状: “测试目标”包含“验证 `nn.matmul` 不做跨 operand/result `stride` 等价校验”，但 `test/dialect/test_nn_dialect.py` 的 `TC-NN-MM-001..008` 未提供任何“stride 不一致但 verifier 仍通过”的正向用例，因此该条测试目标无法被当前测试事实支撑。
     - 影响: 规格宣称的覆盖边界与实际测试脱节；后续若误引入 `matmul` 的跨 operand/result stride 校验，测试无法阻止回归，且 spec 会造成“已验证”的误导。
     - 建议改法（改进 spec 任务，最小修复，推荐优先）:
       - 将该条从 `spec/dialect/nn.md` 的“测试目标”中移除（或改写为“规格约束说明”而非“测试目标”），使测试目标严格反映当前 `TC-NN-MM-001..008` 的实际覆盖范围。
     - 建议改法（改进测试 + spec 任务，增强防回归，备选）:
       - 新增一个 `TC-NN-MM-009`：构造 shape/space/element_type 合法但 stride 在 lhs/rhs/result 之间不一致的 `nn.matmul`，断言 `op.verify()` 仍通过；并在 spec 的“测试清单”补齐 `TC-NN-MM-009 -> test_matmul_op_stride_mismatch_allowed`（命名可调整但需闭环）。
  2. `spec/dialect/nn.md` 的 Parse/Print 约束存在术语不一致（疑似笔误）：
     - 现状: `Parse/Print 约束`中写为“包含 `nn.add/sub/mul/truediv/eq/ne/lt/le/gt/ge/matmul`...”，其中 `matmul` 缺少 `nn.` 前缀，与同段落其他 op 命名风格不一致。
     - 影响: 容易造成 spec 读者误解（是否存在非 `nn.matmul` 的 `matmul` op），不利于公开接口口径收敛。
     - 建议改法（改进 spec 任务）: 将 `matmul` 更正为 `nn.matmul`。

- 后续任务建议（按任务链路）:
  - 申请创建 `改进 spec` 任务：修正 `spec/dialect/nn.md` 的“测试目标”stride 覆盖口径与 Parse/Print 约束中的 `matmul` 命名；完成后需继续创建“再次审查”任务复核闭环。

## T-20260319-ce3c7111

- 时间：2026-03-19 02:43:00 +0800
- 角色：`朽木露琪亚`
- 任务描述：对 `spec/dialect/nn.md` 做最小 spec 修复，收敛 `stride` 测试目标表述并修正 Parse/Print 段落中的 `nn.matmul` 命名；不改 `python/test`。
- worktree：`/home/lfr/kernelcode_generate/wt-20260319-dialect-nn-matmul`
- 变更文件：
  - `spec/dialect/nn.md`
- 变更摘要：
  - 从“测试目标”中移除超出当前测试事实的 `stride` 覆盖宣称，不再把“`nn.matmul` 不做跨 operand/result stride 等价校验”写成已由现有测试验证的目标。
  - 在“用例与 Op 覆盖关系”中将 `stride` 口径改写为规格约束说明：当前规则仍是不做跨 operand/result `stride` 等价校验，但该点尚无独立正向回归测试。
  - 修正 `Parse/Print 约束` 段的命名笔误，将 `matmul` 统一为 `nn.matmul`。
- 影响范围：
  - 仅更新 `spec/dialect/nn.md`；未修改实现或测试。
- 测试说明：
  - 按任务要求未执行测试。
- 后续待跟进项：
  - 仍建议后续补一个 `stride` 正向回归测试，用例方向可为“shape/space/element_type 合法但 lhs/rhs/result stride 不一致时 `nn.matmul` verifier 仍通过”，用于防止未来误引入跨 operand/result stride 等价校验。
- 下一阶段申请：
  - 建议继续进入再次审查，重点复核“测试目标”是否已严格对应当前测试事实，以及 `stride` 是否已被正确降级为规格约束说明。

### T-20260319-b13cb31e

- 时间: 2026-03-19 02:38:51 +0800
- 角色: `提莫炖蘑菇`
- worktree: `/home/lfr/kernelcode_generate/wt-20260319-dialect-nn-matmul`
- 审查范围:
  - `spec/dialect/nn.md`
  - `python/dialect/nn.py`
  - `python/dialect/__init__.py`
  - `test/dialect/test_nn_dialect.py`
- 结论: 通过
- 通过理由（关键一致性核对点）:
  - `TC-NN-MM-001..008` 已在 `spec/dialect/nn.md` 的“测试清单”中与 `test/dialect/test_nn_dialect.py` 的 `test_matmul_*` 一一映射，且用例编号与函数名一致。
  - `spec/dialect/nn.md` 的“测试目标/用例与 Op 覆盖关系”已与当前测试现状对齐：不再把 “`nn.matmul` 不做跨 operand/result `stride` 等价校验”表述为已覆盖项，仅作为规格约束说明，并明确当前无独立正向回归测试。
  - `Parse/Print 约束` 的命名已统一使用 `nn.matmul`（不再出现无前缀 `matmul`），与当前实现/测试中 `nn.matmul` 的 op 名称一致。
  - `stride/space/rank/element_type` 口径与实现一致：`python/dialect/nn.py` 中 `NnMatmulOp.verify_` 检查 rank=2、space 一致与 element_type 一致及 contracting/result shape；不引入跨 operand/result 的 stride 等价校验，仅依赖 `NnMemoryType` 自身的合法性校验，与 spec 描述一致。
- 测试说明:
  - 按任务要求未执行测试（本次为文档/实现/测试一致性复核）。
- 后续任务建议（按任务链路）:
  - 建议进入 `合并` 阶段：将 worktree `/home/lfr/kernelcode_generate/wt-20260319-dialect-nn-matmul` 的 `spec/dialect/nn.md`、`python/dialect/nn.py`、`python/dialect/__init__.py`、`test/dialect/test_nn_dialect.py` 合入 `main`。
  - 在该方言基线可合并的前提下，可继续推进下一阶段 `operation/nn matmul` 的实现与测试任务。

## T-20260319-9f8fd0f0

- 时间: 2026-03-19 04:04:59 +0800
- 角色: 李白
- worktree: `/home/lfr/kernelcode_generate/wt-20260319-dialect-nn-matmul`
- 合并说明:
  - main cherry-pick `4f0aab9`，生成提交 `232673c`。
  - 解决冲突文件：`spec/dialect/nn.md`、`python/dialect/nn.py`、`test/dialect/test_nn_dialect.py`。
- 变更文件:
  - `spec/dialect/nn.md`
  - `python/dialect/nn.py`
  - `python/dialect/__init__.py`
  - `test/dialect/test_nn_dialect.py`
- 测试说明: 未执行（按任务要求）。
- 清理:
  - 已移除 worktree `/home/lfr/kernelcode_generate/wt-20260319-dialect-nn-matmul`。
