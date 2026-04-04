时间：2026-04-05 00:24:31 +0800
经办人：睡觉小分队
任务：T-20260404-bf8b2d33
任务目标：对齐 spec/operation/nn.md 的 broadcast_to(source,target_shape,space) 与 img2col1d/img2col2d 结构化输出合同，使 spec 与已合入实现/测试/expectation(immutable) 一致。
改动：
- `spec/operation/nn.md`：broadcast_to 改为 `source/target_shape/space` 合同，补齐 `target_shape` 维度类型（含 `str` 语义）与 `out.format/out.stride` 约束；img2col1d/img2col2d 明确 `Farmat.Norm/CLast` 输入形态、结构化输出维度、符号公式与 `bool` 参数类型错误边界；同步测试目标与用例清单口径。
结论：spec 已完成对齐；未运行测试（spec-only 变更）。

时间：2026-04-05 01:06:20 +0800
经办人：提莫炖蘑菇
任务：T-20260405-c2723d6b
任务目标：复审 nn spec 对齐（spec-only）：仅允许 spec/operation/nn.md + 记录；核对 broadcast_to/img2col1d/img2col2d 合同与已合并实现/expectation 口径一致性。
改动：无（复审）

范围/越界核对：
- cd /home/lfr/kernelcode_generate/wt-20260404-exp-frontend-semantic-s1-nn-spec && git diff --name-only
  - spec/operation/nn.md
  - （记录文件为未跟踪文件）
结论：diff 未越界；未触碰 expectation/* 与实现/测试文件。

一致性核对（合同层）：
- broadcast_to 已改为公开签名 `broadcast_to(source, target_shape, space)`，并明确：
  - target_shape 类型 `Sequence[int|SymbolDim|str]`；不接受 Memory 作为 target；
  - out.format 固定 Norm，out.stride 为 Memory 默认 stride（与 expectation/实现默认布局口径一致）。
- img2col1d/img2col2d：
  - 输入 format 支持 Norm/CLast 两形态；输出为结构化 rank-4/rank-6（与 expectation 三脚本所需的结构化维度口径一致）。

问题列表：
- P1｜文档内部术语不一致，易误导（需修正后才能判定通过）
  - 位置：spec/operation/nn.md#L1020、#L1021（“测试目标”两条）
  - 现状：写为 `Farmat.Norm/NWC` 与 `Farmat.Norm/NHWC`，其中 NWC/NHWC 为 layout 术语而非 Farmat 枚举值。
  - 影响：与同文件其它位置（以 `Farmat.Norm/Farmat.CLast` 描述）不一致，易造成读者将 NWC/NHWC 误当作 format；也会影响“spec 对齐实现/expectation”的可读性与可执行性。
  - 建议修正：将两条统一为 `Farmat.Norm/Farmat.CLast`，并在括号中注明对应 layout（img2col1d：Norm->NCHW，CLast->NWC；img2col2d：Norm->NCHW，CLast->NHWC）。

- P2｜“bool 参数必须 TypeError”口径可能超出现有证据覆盖（建议澄清/降级表述）
  - 位置：spec/operation/nn.md#L921~924、#L937~940 及 img2col2d 对应段落
  - 风险：expectation 三脚本未显式覆盖 bool 入参错误口径；若实现未显式拒绝 bool（Python 中 bool 是 int 子类），则该条款可能与实际行为不一致。
  - 建议：若要作为硬合同，请在 operation test 映射或 expectation 中补覆盖；否则建议在 spec 中改为“实现建议/可选约束”或移除硬性 TypeError 承诺，以避免 spec/实现偏差。

漏洞/风险排查（spec 复审侧重合同边界）：
- 输入校验绕过：broadcast_to 已明确类型/rank/逐维兼容错误必须显式报错；img2col 明确 format 限定与 W_out/H_out<=0 报错（结论：合同边界清晰）。
- 误判完成风险：上述 P1/P2 文案不一致/超证据覆盖，容易导致“spec 看似对齐但口径仍可歧义”，需修正后再合并。

结论：需修改（P1 文档术语不一致；P2 需澄清 bool 错误口径证据覆盖）

时间：2026-04-05 00:39:06 +0800
经办人：睡觉小分队
任务：T-20260405-98a68a1c
任务目标：修复 spec/operation/nn.md 的测试目标口径与 img2col bool 入参条款歧义。
改动：
- `spec/operation/nn.md`：测试目标由 `Farmat.Norm/NWC`、`Farmat.Norm/NHWC` 统一为 `Farmat.Norm/Farmat.CLast` 并补充布局映射；img2col1d/2d 对 `bool` 入参改为非强制条款（不在支持范围内，实现可选择抛 TypeError）。
结论：spec 修复完成；未运行测试（spec-only 变更）。

时间：2026-04-05 00:42:17 +0800
经办人：提莫炖蘑菇
任务：T-20260405-c96dff02
任务目标：spec-only 复审 nn.md 修复（仅允许 `spec/operation/nn.md` + 同链记录），确认已满足验收口径且无越界/新口径混入。
改动：无（复审）

范围/越界核对：
- cd /home/lfr/kernelcode_generate/wt-20260404-exp-frontend-semantic-s1-nn-spec && git diff --name-only
  - spec/operation/nn.md
  - （记录文件为未跟踪文件）
结论：diff 未越界；未触碰 expectation/*、kernel_gen/*、test/*。

验收点核对：
- A1｜测试目标口径修复：已将“测试目标”两条统一为 `Farmat.Norm/Farmat.CLast`，并补充 layout 映射（img2col1d：`Norm -> NCHW`，`CLast -> NWC`；img2col2d：`Norm -> NCHW`，`CLast -> NHWC`）。
  - 证据：`spec/operation/nn.md#L1020`、`#L1021`。
- A2｜img2col bool 入参条款弱化/澄清：`bool` 不在支持范围内，且“实现可选择抛出 TypeError”，不再作为必须满足的硬合同。
  - 证据：`spec/operation/nn.md#L937`、`#L977`（对应 img2col1d/img2col2d 注意事项）。
- A3｜口径洁净：未引入 pipeline/lowered IR/gen_kernel/codegen 等阶段性口径；本次变更聚焦 operation 层合同与测试目标描述。

漏洞/风险排查（spec 复审）：
- 误判完成风险：已消除“layout 术语混入 Farmat 枚举”的歧义；bool 入参不再被 spec 锁死为 TypeError，降低 spec/实现偏差风险。

结论：通过（可进入合并收口任务）
