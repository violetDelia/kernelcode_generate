时间：2026-04-05 01:05
经办人：睡觉小分队
任务：T-20260405-98a68a1c
任务目标：在 spec/operation/dma.md 增补 alloc(format) 公开合同，并统一 copy/load/slice/reshape/flatten 的输出语义与错误边界，满足 S2 口径。
改动：更新 alloc 签名与参数说明，补充 format 示例与默认值约束；补充 copy/load/slice/reshape/flatten 的错误关键短语约束与 lowering 语义（dma.alloc/dma.copy/dma.load/dma.slice/dma.reshape）。
结论：已完成 spec 侧合同补齐，未执行验证命令，待复审。

时间：2026-04-05 01:21:10 +0800
经办人：提莫炖蘑菇
任务：T-20260405-64e716ff
任务目标：复审 S2（spec-only）：仅核对 `spec/operation/dma.md` 改动范围与口径；不触碰实现/测试/expectation；无需 pytest。
改动：无（复审）

范围/越界核对：
- cd /home/lfr/kernelcode_generate/wt-20260405-exp-frontend-semantic-s2 && git diff --name-only
  - spec/operation/dma.md
  - （记录文件为未跟踪文件）
结论：diff 未越界；未触碰 expectation/*、kernel_gen/*、test/*。

口径核对（按本轮复审关注点）：
- alloc(format)：
  - `alloc(..., format=Farmat.Norm)` 已作为公开签名出现，并明确 `format` 类型与默认值，返回 `Memory.format == format`。
  - 证据：`spec/operation/dma.md#L53`、`#L65`、`#L82~84`、`#L93`。
- copy/load/slice/reshape/flatten 输出语义与错误边界：
  - copy：明确类型校验边界（helper/build_func_op）与关键短语要求；并要求 lowering 生成 `dma.alloc + dma.copy`。
    - 证据：`spec/operation/dma.md#L141~165`。
  - load：细化 TypeError/ValueError 的关键短语约束；并要求 lowering 直接生成 `dma.load`。
    - 证据：`spec/operation/dma.md#L225~237`。
  - slice：补充 space 类型错误与“沿用 load 关键短语约定”；并明确 lowering 桥接到目标式链路（alloc target + dma.slice）。
    - 证据：`spec/operation/dma.md#L262~277`。
  - reshape/flatten：细化非 Memory/非连续布局/shape-numel 不一致等错误关键短语约束；并明确 lowering 绑定 `dma.reshape`。
    - 证据：`spec/operation/dma.md#L389~459`。
- 阶段口径洁净：
  - `spec/operation/dma.md` 未引入 pipeline/lowered IR/gen_kernel/codegen 等口径（仅涉及 operation->dialect 的 lowering 映射约束）。

漏洞/风险排查（spec 复审侧重合同边界）：
- 类型/边界校验：针对 `Memory`/`MemorySpace` 的类型错误与 rank/sizes/out-of-bounds 的 ValueError 已给出明确“必须显式报错”合同，降低静默绕过风险。
- 错误信息关键短语：约束粒度为关键词级别（非完全匹配），可作为测试锚点且相对稳定，不构成明显脆弱点。

结论：通过（可进入合并收口任务）

时间：2026-04-05 01:33:08 +0800
经办人：李白
任务：T-20260405-6449a15a
任务目标：合并收口 S2（spec-only）：仅合入 `spec/operation/dma.md` + 记录文件；不触碰 expectation/*、kernel_gen/*、test/*。
改动：无（合并前范围核对）

范围核对：
- cd /home/lfr/kernelcode_generate/wt-20260405-exp-frontend-semantic-s2 && git diff --name-only
  - spec/operation/dma.md
  - （记录文件为未跟踪文件）
结论：范围符合要求，可执行合并收口。
