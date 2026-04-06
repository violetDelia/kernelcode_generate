时间：2026-04-07 00:34:27 +0800
经办人：咯咯咯
任务：T-20260407-3095eb5e（emit_c_cpp_execution_engine_green_plan-S4-计划回写）
任务目标：把 S1-S3 已确认的 `execute_engine` 接口、示例、失败短语与检查命令回写到 `ARCHITECTURE/plan/emit_c_cpp_execution_engine_green_plan.md`，确保计划正文前后一致。
改动：
- 更新计划文档进度表：将 `S3` 改为已收口并记录审查通过信息；补上 `S4` 的 `worktree`、记录文件与当前收口状态。
- 在计划正文新增 “S1-S3 已确认接口摘要”，集中写清 `compile -> execute` 生命周期、`CompileRequest / ExecuteRequest / CompiledKernel / ExecuteResult` 字段与默认值、`target/include/entry shim` 约定、7 个失败短语的触发条件。
- 对齐现有段落中的示例与说明：补入默认 `entry_point=kg_execute_entry`、`compiler=None -> g++`、`compiler_flags` 基线 `-std=c++17`，并把 `entry shim` 可省略条件改为“与 `CompileRequest.entry_point` 同名同签名的 `extern \"C\"` 入口”。
结论：
- 已完成计划回写，计划文档中的接口、示例、失败短语与检查命令与当前 `spec/execute_engine/execute_engine.md`、`spec/execute_engine/execute_engine_api.md`、`spec/execute_engine/execute_engine_target.md` 保持一致。
- 本次仅修改计划文档与任务记录，未改实现、测试或其他 `spec` 文件。
收口的合同：
- `CompileRequest.entry_point` 默认 `"kg_execute_entry"`，`ExecuteRequest.entry_point=None` 时使用 `CompiledKernel.entry_point`。
- `CompileRequest.compiler=None` 时使用 `g++`，`compiler_flags` 默认 `("-std=c++17",)`，`link_flags` 默认 `()`。
- `target=cpu` 对应 `include/cpu/Memory.h + include/cpu/Nn.h`；`target=npu_demo` 对应 `include/npu_demo/npu_demo.h`。
- 7 个失败短语固定为：`target_header_mismatch`、`source_empty_or_invalid`、`compile_failed`、`symbol_resolve_failed`、`runtime_throw_or_abort`、`stream_not_supported`、`function_output_capture_not_supported`。
边界：
- 仅修改 `ARCHITECTURE/plan/emit_c_cpp_execution_engine_green_plan.md` 与本记录文件。
- 未新增未确认字段，也未改实现和测试。
拒绝路径：
- `target/include` 不一致 -> `target_header_mismatch`
- 空或非法 `source` -> `source_empty_or_invalid`
- 编译失败 -> `compile_failed`
- `function` 或 `entry_point` 无法解析 -> `symbol_resolve_failed`
- 运行期异常、参数顺序不匹配、参数类型/形状不合法 -> `runtime_throw_or_abort`
- `stream != None` -> `stream_not_supported`
- `capture_function_output=True` -> `function_output_capture_not_supported`
引用文件：
- `ARCHITECTURE/plan/emit_c_cpp_execution_engine_green_plan.md`
- `spec/execute_engine/execute_engine.md`
- `spec/execute_engine/execute_engine_api.md`
- `spec/execute_engine/execute_engine_target.md`
下游影响：
- 后续审查可直接按计划书核对 S1-S3 结果与计划正文是否一致，无需再回查零散任务信息。
- 若后续进入实现阶段，可直接复用计划书中的字段默认值、示例和检查命令。
下一步建议：
- 派生唯一审查任务，核对本次计划回写是否完整覆盖 S1-S3 已确认内容，并确认计划书未引入与现有 `spec` 不一致的新表述。

时间：2026-04-07 00:40:32 +0800
经办人：提莫炖蘑菇
任务：T-20260407-24bb4020（emit_c_cpp_execution_engine_green_plan-S4-审查）
任务目标：核对计划书 S4 回写内容与 S1-S3 规范一致（接口字段、示例、失败短语、检查命令不相互冲突）。
改动：无（只读审查）。
结论：通过。计划书回写内容与 `spec/execute_engine/execute_engine.md`、`spec/execute_engine/execute_engine_api.md`、`spec/execute_engine/execute_engine_target.md` 对齐，未发现字段/示例/失败短语/检查命令存在相互矛盾或偏离。
问题清单：无。
风险：未发现新增风险；后续若三份 spec 变更需同步计划书回写段落。
验证命令：未执行（spec-only）。
关键输出：不适用。
下一步建议：派生唯一“合并”任务给李白，合并本次计划书回写。
