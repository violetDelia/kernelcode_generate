时间：2026-04-09 05:32:45 +0800
经办人：不要啊教练
任务：T-20260409-eae1ec92（审查）
任务目标：审查 nn_to_kernel 的 broadcast/broadcast_to dynamic_shape 修复（SymbolGetDimOp 读取维度、拒绝 singleton->symbol）与测试覆盖一致性，并核对与 spec 的一致性与风险点。
改动：
- 新建记录文件并补充审查记录（此前缺失同名记录文件）。
- 核对变更范围（仅用于定位审查目标）：kernel_gen/passes/lowering/nn_to_kernel.py、test/pass/test_lowering_nn_to_kernel.py。
- 验证命令与结果：
  - PYTHONPATH=. pytest -q test/pass/test_lowering_nn_to_kernel.py -k "broadcast" -> 4 passed, 38 deselected（exit=0）
  - PYTHONPATH=. pytest -q test/pass/test_lowering_nn_to_kernel.py -> 42 passed（exit=0）
- 规格一致性核对（仅阅读，不改动）：spec/pass/lowering/nn_to_kernel.md、spec/dialect/nn.md、spec/operation/nn.md。
结论：需修改

问题列表：
1) 文件：spec/operation/nn.md（broadcast/broadcast_to 合同）、spec/dialect/nn.md（nn.broadcast 合同）、kernel_gen/passes/lowering/nn_to_kernel.py（LowerNnToKernelPass 行为）、test/pass/test_lowering_nn_to_kernel.py（pass 单测）
   - 现象：operation/dialect 规格对广播合同的描述允许“singleton dim 扩张到符号维”（例如 spec/operation/nn.md 的 broadcast_to 示例与 test/operation/test_operation_nn.py: test_nn_broadcast_success），但当前 nn_to_kernel pass 在 lowering 阶段显式拒绝“singleton 扩张为符号维”（含隐式前置维与显式维），并在单测中固定了该拒绝行为与错误文案。
   - 风险：规格对外语义与可编译子集边界不清晰；用户按 operation/dialect 规格构造的 nn.broadcast（或通过 operation.broadcast_to 归一化进入方言）可能在 lowering 阶段失败，且失败原因仅体现在 pass 的错误文案与测试中，不在 spec 中可直接查到。
   - 建议：补齐规格闭环，至少在 spec/pass/lowering/nn_to_kernel.md（必要时同步 spec/operation/nn.md 的注意事项段落）明确说明“nn_to_kernel 不支持把 singleton 扩张为新的符号维”，并给出明确失败短语/错误归因，避免规格误导；或（若计划允许）调整 lowering 支持该形态并以可诊断的符号来源构造 dynamic_shape。
   - 优先级：P1

漏洞排查结果（按审查规范 6 类）：
- 输入校验绕过：本次变更倾向于加强校验（拒绝无法从 source 获得的符号维），但需补齐 spec 层对“可编译子集”的说明以避免误用。
- 类型/形状绕过：拒绝路径已被单测锁定（singleton->symbol、implicit singleton->symbol），但规格未描述该限制。
- 边界越界：本次关注点不涉及 axis/rank 越界计算；未发现新增越界风险。
- 错误处理缺失：拒绝路径的错误文案已被单测锁定，但规格缺少对应失败归因说明。
- 状态污染：未发现。
- 资源释放问题：未发现。

最终结论：
- 需修改。建议派生后续任务以补齐 spec 对该限制的明确说明（或回收 pass 的限制并实现可诊断的符号来源），并在修复后再复审确认规格/实现/测试一致性。

时间：2026-04-09 05:40:00 +0800
经办人：睡觉小分队
任务：T-20260409-eae1ec92（spec）
任务目标：补齐 nn_to_kernel 对 `nn.broadcast` 动态形状的约束说明：符号维必须可从 source 读取；不支持 singleton 扩张为新符号维；并明确失败归因与关键短语。
改动：
- 更新 [`spec/pass/lowering/nn_to_kernel.md`](../../../../../spec/pass/lowering/nn_to_kernel.md)：新增 “`nn.broadcast` 的动态形状约束” 条款（`result.shape` 的 `symbol dim` 必须出现在 `input.shape`；不支持把 singleton 维扩张为新符号维），并写明失败时抛出 `LowerNnToKernelError` 且错误信息必须包含关键短语 `LowerNnToKernelBroadcastSymbolDimNotFromSource`。
- 在 lowering 矩阵与失败归因段落补充同一限制的定位说明，避免读者把该限制误解为 `nn.broadcast` verifier 合同的一部分。
结论：
- spec 已补齐 `nn_to_kernel` 对 `nn.broadcast` 动态形状的可编译子集约束与失败短语；本次未改动实现与测试。

时间：2026-04-09 05:49:49 +0800
经办人：睡觉小分队
任务：T-20260409-eae1ec92（spec 补充）
任务目标：清理 `spec/pass/lowering/nn_to_kernel.md` 中的禁词与脚本绑定表述，避免与当前提示词规则冲突。
改动：
- 更新 [`spec/pass/lowering/nn_to_kernel.md`](../../../../../spec/pass/lowering/nn_to_kernel.md)：调整职责矩阵中对 `dma.broadcast/dma.transpose` 的措辞为“本计划规定”；将测试段落与用例表中的目录级黑盒验证相关表述统一为“目录级黑盒验证”，并避免在 spec 内绑定具体验证脚本路径。
结论：
- spec 文本已清理完成；`nn.broadcast` 符号维来源约束与关键短语 `LowerNnToKernelBroadcastSymbolDimNotFromSource` 不变。

时间：2026-04-09 05:56:08 +0800
经办人：提莫炖蘑菇
任务：T-20260409-eae1ec92（复审）
任务目标：复核 nn.broadcast 符号维来源限制与错误短语一致性。
改动：无代码改动；仅核对与执行验证命令。
验证：
- PYTHONPATH=. pytest -q test/pass/test_lowering_nn_to_kernel.py -k 'broadcast' -> 4 passed, 38 deselected
结论：
- 问题列表：
  1) spec 要求错误信息包含 LowerNnToKernelBroadcastSymbolDimNotFromSource，但实现与测试当前仅断言 "cannot expand singleton dim to symbol dim" 等文案，未覆盖该短语。
- 漏洞排查结果：
  1) 输入校验：已有符号维来源限制校验，但错误短语与 spec 不一致
  2) 异常路径：测试覆盖 singleton 扩张拒绝，但未覆盖 spec 约定短语
  3) 资源分配：broadcast alloc 逻辑未见异常
  4) 语义一致性：spec 与实现/测试存在不一致
  5) 兼容性：现有错误短语可能影响下游诊断聚类
  6) 影响面：仅涉及 nn.broadcast 符号维错误诊断
- 改进建议：补齐错误短语与测试断言，确保与 spec 一致
- 最终结论：需修改

时间：2026-04-09 06:10:50 +0800
经办人：小李飞刀
任务：T-20260409-eae1ec92（实现）
任务目标：对齐 nn.broadcast 符号维来源错误短语，确保 LowerNnToKernelBroadcastSymbolDimNotFromSource 出现在相关错误并更新测试断言。
改动：
- 更新 [`kernel_gen/passes/lowering/nn_to_kernel.py`](../../../../../kernel_gen/passes/lowering/nn_to_kernel.py)：在 singleton/implicit singleton 扩张为符号维时抛出的 `LowerNnToKernelError` 中增加关键短语 `LowerNnToKernelBroadcastSymbolDimNotFromSource`（作为错误信息前缀）。
- 更新 [`test/pass/test_lowering_nn_to_kernel.py`](../../../../../test/pass/test_lowering_nn_to_kernel.py)：调整两条拒绝用例的 `match` 断言，覆盖关键短语与原有错误文本。
- 验证命令与结果：
  - PYTHONPATH=. pytest -q test/pass/test_lowering_nn_to_kernel.py -k 'broadcast' -> 4 passed, 38 deselected（exit=0）
结论：
- 已完成；实现与测试已对齐 spec 中关键短语要求。

时间：2026-04-09 06:15:22 +0800
经办人：提莫炖蘑菇
任务：T-20260409-eae1ec92（审查；broadcast 符号维错误短语一致性）
任务目标：复核 nn.broadcast lowering 错误短语与 spec 一致性，并确认 broadcast 相关用例覆盖与可复现验证。
改动：
- 无代码改动；仅核对 spec/实现/测试并复测。
结论：
- 一致性：spec 中对符号维来源限制与错误短语要求，与实现抛错前缀及测试断言一致。
- 用例覆盖：broadcast lower 为 dma.broadcast、符号维读取、singleton 扩张拒绝等用例已覆盖。
- 验证：PYTHONPATH=. pytest -q test/pass/test_lowering_nn_to_kernel.py -k 'broadcast'（exit=0，4 passed, 38 deselected in 0.43s）。

问题列表：
- 无。

漏洞排查结果：
- 输入校验绕过：未见（符号维来源限制已校验）。
- 类型/形状绕过：未见（singleton 扩张拒绝路径有断言）。
- 边界越界：未见（rank/shape 约束已有校验与测试）。
- 错误处理缺失：未见（错误短语覆盖到位）。
- 状态污染：未见。
- 资源释放问题：未见。

改进建议：
- 未发现额外改进点。

最终结论：
- 通过。
