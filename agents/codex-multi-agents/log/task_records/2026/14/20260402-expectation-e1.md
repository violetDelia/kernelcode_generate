时间：2026-04-02 03:16:20 +0800
任务：T-20260402-1b18a675
任务目标：在 `spec/dialect/dma.md` 冻结 `dma.view` 的结果类型与 verifier 合同；仅修改该 spec 文件，不改 DSL 文件、实现、测试、expectation。
改动：
- 核对任务前置：
  - `worktree=/home/lfr/kernelcode_generate/wt-20260402-expectation-e1` 可访问。
  - 当前无其他进行中任务，已向管理员同步“已开工、暂无阻塞”。
  - 当前链路记录文件不存在，按规范在当前 `worktree` 下补建。
- 阅读并对齐当前基线：
  - 复核 `spec/dialect/dma.md` 中 `dma.view` 的通用约束、operation API 映射与 `dma.view` 小节。
  - 复核 `test/dialect/test_dma_dialect.py::test_dma_view_accepts_matching_numel_subset_with_explicit_stride`，确认 verifier 口径为“`numel` 一致时允许显式 `stride/result` 布局与 source 不同，只要求与 `stride` operand 对齐”。
  - 复核同链路历史记录 `agents/codex-multi-agents/log/task_records/2026/14/20260330-expectation-e2.md` 与 `test/dsl/test_mlir_gen.py::test_build_func_op_supports_dma_helper_calls`，确认 expectation 闭环依赖 `result_type.shape <- size`、`result_type.stride <- stride`，且 `func.return.type == dma.view.result.type`。
- 更新 `spec/dialect/dma.md`：
  - 在 `dma.view` 通用约束中明确：`result_type.shape` 必须由 `shape` operand / DSL `size` 确定，`result_type.stride` 必须由 `stride` operand / DSL `stride` 确定，不能只因“生成了 dma.view op”就视为 expectation 对齐成功。
  - 新增 expectation 返回边界：当 `dma.view` 结果直接参与 `func.return` 时，返回的 `!nn.memory<...>` 类型必须与同一份 `result_type` 完全一致；`expectation/dsl/mlir_gen/dialect/dma/view` 的 `EXPECTED_MEMORY` 比对依赖这一边界。
  - 在 operation API 映射与 `dma.view` 小节注意事项中同步写清 `view(source, offset, size, stride)` 的结果类型来源：`result_type.shape == size`、`result_type.stride == stride`，并强调不得回退为复用 `source.shape/source.stride` 或其他既有 `Memory` 元信息。
  - 在测试目标与用例清单中新增 expectation 对齐描述与 `TC-DMA-019C`，明确 expectation 通过条件不是“只生成了 dma.view”，而是 `func.return` 类型与 `dma.view.result_type` 一致且 `EXPECTED_MEMORY` 比对成功。
- 自检：
  - `rg -n "dma.view|result type|Memory|EXPECTED_MEMORY" spec/dialect/dma.md`（exit 0）
  - `git diff --check -- spec/dialect/dma.md`（exit 0）
  - `git status --short`（exit 0；仅 `spec/dialect/dma.md` 与本记录文件为当前任务增量）
结论：
- 已完成本任务要求，改动范围仅 `wt-20260402-expectation-e1/spec/dialect/dma.md` 与本记录文件。
- 测试情况：本任务为 spec 阶段，未运行 `pytest` 或 expectation；已完成关键词校验与 diff 格式校验。
- 阻塞点：无。
- 下一步建议：创建唯一后续实现任务，在同一 `worktree` 中仅修正 `dma.view` 的 expectation/实现闭环，重点核对 `expectation/dsl/mlir_gen/dialect/dma/view`、`emit_mlir/mlir_gen` 与 `kernel_gen/dialect/dma.py` 是否继续满足 `result_type.shape <- size`、`result_type.stride <- stride` 与 `func.return.type == dma.view.result.type` 的合同。
时间：2026-04-02 03:20:49 +0800
任务：T-20260402-4e1357df
任务目标：审查 `spec/dialect/dma.md` 是否与 `ARCHITECTURE/plan/expectation_dsl_mlir_dma_symbol_closure_plan.md` 的 `E1` 目标、边界、注意事项、验证命令、验收标准一致；重点核对 `dma.view` 的 `result_type.shape <- size`、`result_type.stride <- stride`、`func.return.type` 与 `dma.view.result_type` 一致，以及 `EXPECTED_MEMORY` 比对边界。
改动：
- 只读审查范围：
  - `spec/dialect/dma.md`
  - `test/dialect/test_dma_dialect.py`
  - `test/dsl/test_mlir_gen.py`
  - `test/dsl/test_emit_mlir.py`
  - `test/dsl/test_ast_visitor.py`
  - `/home/lfr/kernelcode_generate/expectation/dsl/mlir_gen/dialect/dma/view`
  - `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/expectation_dsl_mlir_dma_symbol_closure_plan.md`
- 复核命令：
  - `git -C /home/lfr/kernelcode_generate/wt-20260402-expectation-e1 diff -- spec/dialect/dma.md`（exit 0）
  - `nl -ba spec/dialect/dma.md | sed -n '52,130p;272,305p;508,548p'`（exit 0）
  - `nl -ba test/dialect/test_dma_dialect.py | sed -n '680,725p'`（exit 0）
  - `sed -n '1,260p' /home/lfr/kernelcode_generate/expectation/dsl/mlir_gen/dialect/dma/view`（exit 0）
  - `sed -n '1000,1075p' test/dsl/test_mlir_gen.py`（exit 0）
- 审查结果：
  - `spec/dialect/dma.md:63-65` 已明确 `dma.view` 的 `result_type.shape` 来自 `shape` operand / DSL `size`，`result_type.stride` 来自 `stride` operand / DSL `stride`，并保持静态可判定时 `numel` 一致，符合 `E1` 目标与注意事项。
  - `spec/dialect/dma.md:64`、`spec/dialect/dma.md:120`、`spec/dialect/dma.md:290` 已把 `func.return` 类型必须与 `dma.view.result_type` 完全一致写成 expectation 边界；这与 expectation 文件 `/home/lfr/kernelcode_generate/expectation/dsl/mlir_gen/dialect/dma/view:97-101`、`:123-127` 的真实断言一致，后者同时比较 `view_ops[0].result.type` 与 `return_ops[0].arguments[0].type` 是否等于 `EXPECTED_MEMORY`。
  - `spec/dialect/dma.md:546-547` 的 `TC-DMA-019B/019C` 与现有 verifier/DSL 证据一致：`test/dialect/test_dma_dialect.py:699-716` 已覆盖“显式 stride 与 source 不同但和 stride operand 对齐时 verifier 通过”；`test/dsl/test_mlir_gen.py:1059-1067` 已覆盖 `view_func.function_type.outputs == [view_ops[0].result.type]` 且 `func.return` 参数类型等于 `dma.view.result.type`。
- 漏洞/歧义排查：
  - 输入校验绕过：未发现将 `shape/stride` 来源退回为仅依赖上层 `Memory` 元信息的留白。
  - 类型/形状绕过：`shape <- size`、`stride <- stride`、`func.return.type == dma.view.result_type` 的边界已明确，未见形状/布局口径歧义。
  - 边界越界：`offsets` 非负与静态边界校验约束仍保留，未回退。
  - 错误处理缺失：Expectation 通过条件不再被“只生成了 dma.view op”替代，错误边界完整。
  - 状态污染：未发现。
  - 资源释放问题：本轮为 spec-only，无新增资源生命周期风险。
结论：
- 通过。
- 未发现额外改进点。
- 测试情况：本次为审查阶段，未执行 `pytest` 或 expectation；证据来自 plan/spec/test/expectation 的静态对照与行号复核。
- 下一步建议：按链路进入 `E2` spec 任务，仅修改 `spec/dialect/symbol.md`，冻结 `gt/le/lt/ne` 与 `to_float` 的 dialect 合同。
