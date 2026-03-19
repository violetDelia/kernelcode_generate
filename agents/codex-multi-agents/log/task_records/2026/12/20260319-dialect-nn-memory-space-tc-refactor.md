# 20260319-dialect-nn-memory-space-tc-refactor

- 任务: T-20260319-a2c7545a
- 执行人: 摸鱼小分队
- worktree: /home/lfr/kernelcode_generate
- 时间: 2026-03-19 01:05:00 +0800

## 本次改动
- 在 `spec/dialect/nn.md` 增加 `tsm/tlm` memory space，收敛 text form、parse/print、verifier 与测试清单口径。

## 变更文件
- `spec/dialect/nn.md`

## 后续实现/测试待跟进
- `python/dialect/nn.py` 与 `test/dialect/test_nn_dialect.py` 尚未支持 `tsm/tlm`，需补齐 parse/print/verifier 与对应测试（TC-NN-002）。

## T-20260319-a3c814ee

- 时间：2026-03-19 01:02:17 +0800
- 角色：`小李飞刀`
- 任务描述：按 spec 收敛 nn dialect memory space，补齐 TSM/TLM parse/print/verifier 与测试。
- worktree：`/home/lfr/kernelcode_generate/wt-20260319-dialect-nn-memory-space-tc`
- 产出文件：
  - `python/dialect/nn.py`
  - `python/dialect/__init__.py`
  - `test/dialect/test_nn_dialect.py`
- 变更摘要：
  - 扩展 NnMemorySpaceAttr 支持 `tsm/tlm`，并更新 verifier 错误信息。
  - TC-NN-002 覆盖全空间 round-trip，更新非法 space 断言。
  - 更新测试注释时间戳。
- 测试说明：
  - `pytest -q test/dialect/test_nn_dialect.py`
  - 结果：12 passed in 0.37s
- 剩余风险：
  - 未发现新增风险。
- 下一阶段申请：
  - 申请创建审查任务，范围覆盖 `python/dialect/nn.py`、`python/dialect/__init__.py`、`test/dialect/test_nn_dialect.py`。

## 审查记录 T-20260319-39588a0e

- 时间：2026-03-19 01:43:21 +0800
- 角色：`不要啊教练`
- worktree：`/home/lfr/kernelcode_generate/wt-20260319-dialect-nn-memory-space-tc`
- 审查范围：
  - `spec/dialect/nn.md`
  - `python/dialect/nn.py`
  - `python/dialect/__init__.py`
  - `test/dialect/test_nn_dialect.py`
- 结论：不通过
- 是否按 spec 收敛：未完全收敛（TSM/TLM 与 spec space 列表不一致）

问题清单（需改动，未闭合前不建议进入提交整理阶段）：
1) `NnMemorySpaceAttr` 支持空间集合与 spec 不一致
   - 位置：
     - `spec/dialect/nn.md`：仅声明 `global/shared/local` 三种空间。
     - `python/dialect/nn.py`：`_VALID_SPACES` 含 `tsm/tlm`，`NnMemorySpaceAttr` 文档与 verifier 同步放宽。
     - `test/dialect/test_nn_dialect.py`：`test_space_attr_round_trip` 覆盖 `tsm/tlm`，`test_invalid_space_attr_rejected` 期望错误信息包含 `tsm/tlm`。
     - `python/dialect/__init__.py`：文档声称“覆盖 TSM/TLM 空间语义”。
   - 影响：TC-NN-002 “全空间 round-trip” 与 spec 定义的空间集合不一致，导致 parse/print/verifier 行为超出 spec；后续合并会产生口径漂移。
   - 建议改法（改进实现/测试阶段，按当前 spec 收敛）：
     - 在 `python/dialect/nn.py` 将 `_VALID_SPACES` 收敛为 `global/shared/local`，同步修改 `NnMemorySpaceAttr` 文档与 verifier 错误信息；`from_name` 注释同步。
     - 在 `test/dialect/test_nn_dialect.py` 的 `test_space_attr_round_trip` 移除 `tsm/tlm`，并更新 `test_invalid_space_attr_rejected` 期望的错误信息。
     - 在 `python/dialect/__init__.py` 移除“TSM/TLM”字样，保持文档与 spec 一致。
     - 若团队决定保留 `tsm/tlm`，则需先更新 `spec/dialect/nn.md` 的空间列表与 TC-NN-002 说明，再保持实现/测试一致（该路径不符合“按当前 spec 核对”的要求，需管理员确认）。

复测说明：按任务要求未额外复测。

下一步建议：
- 发起“改进实现/测试”任务，按当前 spec 收敛 space 列表；或由管理员确认是否需改 spec 后再重审。

## T-20260319-02b0d8eb

- 时间：2026-03-19 01:54:33 +0800
- 角色：`朽木露琪亚`
- 任务描述：修复 `spec/dialect/nn.md` 中 nn dialect memory space 关于 `tsm/tlm` 的自相矛盾表述，统一为五种合法空间口径，并校准示例、verifier 说明、测试目标与测试映射。
- worktree：`/home/lfr/kernelcode_generate`
- 变更文件：
  - `spec/dialect/nn.md`
- 变更摘要：
  - 统一 `NnMemorySpaceAttr` 与 `NnMemoryType.space` 的 spec 口径为 `global/shared/local/tsm/tlm` 五种合法空间，明确 `tsm/tlm` 与其余三种空间在当前方言层共用同一 parse/print 与 verifier 路径，不引入额外特判分支。
  - 校准示例，补成可直接体现五空间口径的 `tsm/tlm` 构造示例，避免文档示例只落在 `global` 上导致读者误解为仅前三种空间合法。
  - 修正测试目标与测试清单中关于 space round-trip 的表述，把 `TC-NN-002` 的测试映射收敛为现有实现/测试链路中的真实函数名 `test_space_attr_round_trip`，并明确其覆盖五种 space text form。
- 影响范围：
  - 仅 spec 文档更新；实现与测试未改动。
- 测试说明：
  - 按任务要求未执行测试。
- 与现有实现/测试链路的一致性说明：
  - 本次 spec 以现有 `TSM/TLM` 实现/测试链路口径为准：五种空间共用同一 `NnMemorySpaceAttr` parse/print/verifier 规则，`TC-NN-002` 对应测试函数名为 `test_space_attr_round_trip`。
- 是否建议进入再次审查：
  - 建议进入再次审查。
  - 审查重点应聚焦 `spec/dialect/nn.md` 中五种 memory space 的统一口径、`TC-NN-002` 测试映射是否与现有 `TSM/TLM` 链路一致，以及示例/错误文案是否已不存在“仅允许 global/shared/local”残留。

## 审查记录 T-20260319-12042072

- 时间：2026-03-19 01:59:25 +0800
- 角色：`不要啊教练`
- worktree：`/home/lfr/kernelcode_generate/wt-20260319-dialect-nn-memory-space-tc`
- 审查范围：
  - `spec/dialect/nn.md`
  - `python/dialect/nn.py`
  - `python/dialect/__init__.py`
  - `test/dialect/test_nn_dialect.py`
- 结论：不通过
- 是否按 spec 收敛：未完全收敛（五空间口径与 spec 不一致）

问题清单（需改动，未闭合前不建议进入提交整理阶段）：
1) 五空间口径与 spec 未对齐
   - 位置：
     - `spec/dialect/nn.md`：仍仅声明 `global/shared/local` 三空间，TC-NN-002 也仅对应三空间口径。
     - `python/dialect/nn.py`：`_VALID_SPACES` 与文档/错误文案已包含 `tsm/tlm`。
     - `test/dialect/test_nn_dialect.py`：`test_space_attr_round_trip` 覆盖 `tsm/tlm`，`test_invalid_space_attr_rejected` 期望错误信息包含 `tsm/tlm`。
     - `python/dialect/__init__.py`：文案声明“覆盖 TSM/TLM 空间语义”。
   - 影响：实现/测试先行扩展到五空间，spec 未更新导致 TC-NN-002 与 `test_space_attr_round_trip` 语义不闭环，审查口径不一致。
   - 建议改法（需管理员确认采用哪条路径）：
     - 路径 A（按当前 spec 收敛）：
       - 将 `python/dialect/nn.py` 的 `_VALID_SPACES` 收敛为 `global/shared/local`，同步修正文档/错误文案与 `from_name` 注释。
       - 在 `test/dialect/test_nn_dialect.py` 的 `test_space_attr_round_trip` 移除 `tsm/tlm`，并更新 `test_invalid_space_attr_rejected` 断言。
       - 在 `python/dialect/__init__.py` 移除 TSM/TLM 文案。
     - 路径 B（确认为五空间规格）：
       - 更新 `spec/dialect/nn.md` 的 Space 建模、合法取值、示例、预期行为、TC-NN-002 描述与测试清单，明确包含 `tsm/tlm`；再保持实现/测试一致。

复测说明：按任务要求未额外复测。

下一步建议：
- 由管理员确认应采用三空间或五空间口径；确认后发起相应“改进 spec”或“改进实现/测试”任务并再复审。

## T-20260319-5bbfe3a9

- 时间：2026-03-19 02:04:34 +0800
- 角色：`朽木露琪亚`
- 任务描述：将 `/home/lfr/kernelcode_generate/wt-20260319-dialect-nn-memory-space-tc/spec/dialect/nn.md` 同步到 `main` 当前五空间基线，统一后续审查口径。
- worktree：`/home/lfr/kernelcode_generate/wt-20260319-dialect-nn-memory-space-tc`
- 变更文件：
  - `wt-20260319-dialect-nn-memory-space-tc/spec/dialect/nn.md`
- 变更摘要：
  - 以 `main` 当前 [`spec/dialect/nn.md`](../../../../../../spec/dialect/nn.md) 为准，完整同步 worktree 内同文件，使其从旧的三空间版本收敛到 `global/shared/local/tsm/tlm` 五空间口径。
  - 同步补齐 worktree 中此前缺失的分层说明、`nn.matmul`/`nn.broadcast` 待补方言规范、五空间测试目标与 `TC-NN-002 -> test_space_attr_round_trip` 的真实测试映射，确保后续审查基线与 `main` 一致。
  - 保持边界不变：仅修改 worktree 内 spec 文件，不改 `python/dialect/nn.py`、`python/dialect/__init__.py`、`test/dialect/test_nn_dialect.py`。
- 一致性检查：
  - 已确认 worktree 中 `wt-20260319-dialect-nn-memory-space-tc/spec/dialect/nn.md` 与 `main` 中 `spec/dialect/nn.md` 内容一致。
- 测试说明：
  - 按任务要求未执行测试。
- 是否建议再次审查：
  - 建议再次审查。
  - 审查重点应聚焦 worktree 中 `spec/dialect/nn.md` 是否已完全切换为五空间口径，以及其与 `python/dialect/nn.py`、`test/dialect/test_nn_dialect.py` 当前 `TSM/TLM` 实现/测试链路是否一致。

## 审查记录 T-20260319-ac81ab54

- 时间：2026-03-19 02:08:23 +0800
- 角色：`不要啊教练`
- worktree：`/home/lfr/kernelcode_generate/wt-20260319-dialect-nn-memory-space-tc`
- 审查范围：
  - `spec/dialect/nn.md`
  - `python/dialect/nn.py`
  - `python/dialect/__init__.py`
  - `test/dialect/test_nn_dialect.py`
- 结论：通过
- 是否按 spec 收敛：已按 spec 收敛

核对要点：
- spec 已明确 `global/shared/local/tsm/tlm` 五空间口径，示例与预期行为一致；实现 `_VALID_SPACES` 与错误文案同步五空间。
- `python/dialect/__init__.py` 文案与 spec 一致，未见旧口径残留。
- TC-NN-002 映射 `test_space_attr_round_trip`，测试覆盖五空间 text form，parse/print/verifier 闭环一致。

判断：
- 五空间口径、示例/错误文案、TC-NN-002 与测试映射已完全一致，可进入提交整理阶段。

## 合并记录 T-20260319-d9ae9db7

- 时间：2026-03-19 02:11:56 +0800
- 角色：李白
- worktree：/home/lfr/kernelcode_generate/wt-20260319-dialect-nn-memory-space-tc
- 提交整理：
  - worktree 提交：`c772dde`
  - 主线提交：`72149b2`
- 合入范围：
  - `spec/dialect/nn.md`
  - `python/dialect/nn.py`
  - `python/dialect/__init__.py`
  - `test/dialect/test_nn_dialect.py`
- 冲突处理：
  - 主线已有 `spec/dialect/nn.md` 与 `python/dialect/nn.py` 的本地修改，已临时 stash，完成合入后已回放，无冲突。
- 测试说明：按要求未额外复测。

## 清理记录 T-20260319-d9ae9db7

- 时间：2026-03-19 02:11:56 +0800
- 已删除 worktree：`/home/lfr/kernelcode_generate/wt-20260319-dialect-nn-memory-space-tc`
- .lock：未发现残留
