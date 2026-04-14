时间：2026-04-15 07:12
经办人：朽木露琪亚
任务：T-20260414-d647232b
任务目标：收口前端 TSM tile memory 的 IR 空间保真
改动：更新 kernel_gen/dsl/emit_mlir.py，将静态 memory space 映射中的 MemorySpace.TSM/TLM 改为 #nn.space<tsm>/#nn.space<tlm>；在 test/dsl/test_mlir_gen.py 新增 matmul tiled raw IR 用例，覆盖 build_func_op 与 build_func_op_from_ast 两个入口，确认 TSM tile memory 与 nn.matmul 的 space 属性保持为 #nn.space<tsm>。
验证：1) PYTHONPATH=. pytest -q test/dsl/test_mlir_gen.py -k 'test_build_func_op_matmul_tsm_tile_memory_keeps_tsm_in_raw_ir or test_build_func_op_lowers_arch_barrier' -> 2 passed；2) 在 worktree 根目录执行 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260414-execute-engine-matmul-s2:/home/lfr/kernelcode_generate python /home/lfr/kernelcode_generate/expectation/execute_engine/npu_demo/matmul.py -> exit 1；CASE-1 已通过，CASE-2 仅剩 loop 内 nn.matmul 未改写为 kernel.matmul，CASE-3 仍为 target=npu_demo: symbol.const: unsupported op。
结论：本轮 build 已完成，S2 前端 TSM 空间保真已收口；当前全量 expectation 未全通过的剩余项属于后续 S3/S4 范围，可继续交由 review 复核本轮改动并据此推进下一阶段。

时间：2026-04-15 07:02 +0800
经办人：不要啊教练
任务：T-20260414-d647232b
任务目标：复核 execute_engine_npu_demo_matmul S2 前端 TSM 空间保真改动与验证结果。
改动：
- 审查结论：通过。
- 范围核对：`git diff --name-only` 仅包含 `kernel_gen/dsl/emit_mlir.py`、`test/dsl/test_mlir_gen.py`，与 S2 阶段目标一致。
- 合同核对：
  - `emit_mlir` 的 `_MEMORY_SPACE_MAP` 已将 `MemorySpace.TSM` 映射为 `tsm`（不再映射到 `shared`），`MemorySpace.TLM` 映射为 `tlm`。
  - 新增 `test_build_func_op_matmul_tsm_tile_memory_keeps_tsm_in_raw_ir` 同时覆盖 `build_func_op` 与 `build_func_op_from_ast`，断言 raw IR 包含 `#nn.space<tsm>` 且不包含 `#nn.space<shared>`。
  - expectation 复跑结果显示 `CASE-1` 通过，`CASE-2/CASE-3` 失败点分别为 loop 内 matmul lowering 与 npu_demo 发码，符合计划书后续 S3/S4 的职责划分。
- 风险排查结果：
  - 输入校验绕过：本轮仅调整空间字符串映射，不新增输入入口。
  - 类型/形状绕过：本轮无 shape 计算逻辑改动。
  - 边界越界：本轮无内存索引逻辑改动。
  - 错误处理缺失：本轮无新增错误分支；既有路径行为保持一致。
  - 状态污染：映射常量与测试新增为局部改动，无全局状态副作用。
  - 资源释放问题：本轮不涉及资源生命周期管理。
- 改进建议：未发现本阶段额外改进项。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/test_mlir_gen.py -k 'test_build_func_op_matmul_tsm_tile_memory_keeps_tsm_in_raw_ir or test_build_func_op_lowers_arch_barrier'` -> `2 passed, 146 deselected`，exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260414-execute-engine-matmul-s2:/home/lfr/kernelcode_generate python /home/lfr/kernelcode_generate/expectation/execute_engine/npu_demo/matmul.py` -> exit=1；输出显示 `CASE-1` 通过，`CASE-2` 失败短语为 `loop-region nn.matmul must be lowered to kernel.matmul`，`CASE-3` 失败短语为 `target=npu_demo: symbol.const: unsupported op`。
结论：S2 目标（前端 TSM 空间保真）已满足，当前结果可续接 merge；后续 S3/S4 继续处理 CASE-2/CASE-3。
