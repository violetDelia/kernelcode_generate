时间：2026-04-05 01:43
经办人：睡觉小分队
任务：T-20260405-6fef6361
任务目标：在 spec/dsl/emit_mlir.md 收口 DMA/NN helper lowering 矩阵与非法输入失败边界。
改动：在 emit_mlir 额外补充中整理 DMA/NN helper lowering 矩阵，明确 copy/slice 需 alloc+op，补充 free 固定诊断与各 helper 非法输入失败边界，并统一 free 必须发射 dma.free 的口径。
结论：已完成 spec 更新，未执行验证命令，待复审。

时间：2026-04-05 01:56:13 +0800
经办人：提莫炖蘑菇
任务：T-20260405-3e0c3f18
任务目标：复审 spec/dsl/emit_mlir.md（DMA/NN helper lowering 矩阵与失败边界），spec-only；无需 pytest。
改动：无（复审）

范围/越界核对：
- cd /home/lfr/kernelcode_generate/wt-20260405-exp-frontend-semantic-s4 && git diff --name-only
  - spec/dsl/emit_mlir.md
  - （记录文件为未跟踪文件）
结论：diff 未越界；未触碰实现/测试/expectation。

口径核对（DMA/NN helper lowering 矩阵与失败边界）：
- DMA helper lowering 矩阵：
  - `alloc(...) -> dma.alloc`（返回 memory value）
  - `copy(...) -> dma.alloc + dma.copy`（返回 alloc 结果）
  - `slice(...) -> dma.alloc + dma.slice`（返回 alloc 结果）
  - `load(...) -> dma.load`
  - `reshape/flatten(...) -> dma.reshape`（flatten 为一维 reshape）
  - `store/deslice/free` 为语句；其中 `free(...)` 在 emit 阶段生成单个 `dma.free`
  - 证据：`spec/dsl/emit_mlir.md#L144~169`
- NN helper lowering 矩阵：
  - `img2col1d/img2col2d -> nn.img2col1d/nn.img2col2d`
  - `matmul -> nn.matmul`（必要时插入最少 `dma.cast`）
  - 证据：`spec/dsl/emit_mlir.md#L158~166`
- 失败边界与诊断：
  - 明确“emit 阶段必须在入口校验并保留错误位置”，并对各 helper 非法输入给出失败边界约束。
  - 对 `free` 给出固定诊断锚点：`Unsupported free arity` / `Operand must be nn.memory`，避免 fallback 到 generic unsupported。
  - 证据：`spec/dsl/emit_mlir.md#L144`、`#L170~172`

阶段口径洁净：
- 文档未引入 pipeline/lowered IR/gen_kernel/codegen 口径；本次新增内容仅收口 emit 阶段 helper->dialect 的 lowering 矩阵与失败边界。

漏洞/风险排查（复审侧重边界/异常路径）：
- 主要风险点是“非法输入静默通过/落入 generic unsupported”导致误判完成；本次通过矩阵+固定诊断把失败边界前移到 emit 入口，方向正确。
- 对 copy/slice 明确必须 alloc+op 并返回 alloc 结果，避免把 dialect 目标式 op 误当作“返回值式 helper”，降低 IR 口径混淆风险。

结论：通过（可进入合并收口任务）

时间：2026-04-05 02:05:41 +0800
经办人：李白
任务：T-20260405-b0ea5b7f
任务目标：合并收口 S4（spec-only）：仅合入 `spec/dsl/emit_mlir.md` + 记录文件；不触碰实现/测试/expectation。
改动：无（合并前范围核对）

范围核对：
- cd /home/lfr/kernelcode_generate/wt-20260405-exp-frontend-semantic-s4 && git diff --name-only
  - spec/dsl/emit_mlir.md
  - （记录文件为未跟踪文件）
结论：范围符合要求，可执行合并收口。
