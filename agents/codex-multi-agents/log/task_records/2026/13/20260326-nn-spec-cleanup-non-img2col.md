时间：2026-03-26
任务：T-20260326-9bc725fe（经办人：咯咯咯）
任务目标：清理 spec/operation/nn.md 中非 img2col 的 expectation 相关内容，并收敛测试映射到现有测试用例。
改动：移除 spec/operation/nn.md 的 expectation 相关描述与测试映射条目中的 expectation 命令，保留与 test/operation/test_operation_nn.py 一一对应的测试函数引用。
结论：已完成非 img2col 段落的 expectation 清理，测试映射仅保留实际测试用例，等待后续复审。

时间: 2026-03-26 23:10:34 +0800
经办人: 不要啊教练
任务: T-20260326-ccb74448
任务目标: 复审 spec/operation/nn.md 非 img2col expectation 清理与测试映射调整。
结论: 需修改。
问题:
1) spec/test 映射未一一对应：spec 表中 OP-008 与 OP-014 同指向 test_nn_dtype_mismatch，但 test 中无 OP-014 标注；test_nn_dtype_invalid_error 仍标注 OP-008，导致同编号覆盖多测试。
2) 非 img2col 用例仍存在多测试共用编号：test_nn_sub_reverse_and_dtype_mismatch、test_nn_sub_format_fallback 仍标 OP-002；test_nn_add_bool_scalar 仍标 OP-005；test_nn_add_stride_dim_serialization 仍标 OP-016。spec 表仅映射各编号到单一测试，未覆盖上述用例。
3) matmul 编号漂移：test_nn_matmul_space_override 使用 OP-MM-008，但 spec 表仅存在 OP-MM-002（指向同测试），编号不一致且 OP-MM-008 未出现在 spec。
4) 本次 worktree 仍包含 kernel_gen/operation/nn.py 与 test/operation/test_operation_nn.py 的 img2col 改动，超出“非 img2col expectation 清理”复审范围；需拆分或明确职责后再复审。
建议:
- 统一 OP 编号与测试注释为一一对应（必要时为 test_nn_sub_*、test_nn_add_bool_scalar、test_nn_dtype_invalid_error、test_nn_add_stride_dim_serialization、test_nn_matmul_space_override 分配独立编号并同步 spec）。
- 若 OP-014 计划保留，请补齐对应测试注释；否则移除或合并编号。
- 将 img2col 相关实现/测试改动拆分到独立任务链路。

时间：2026-03-26 23:15:35 +0800
经手人：睡觉小分队
任务：T-20260326-9e229fa0
任务目标：修正 nn 非 img2col 测试映射，确保 spec/operation/nn.md 与 test/operation/test_operation_nn.py 的 OP 编号一一对应，并修复 OP-MM 编号漂移。
改动：
- spec/operation/nn.md：补齐并拆分编号映射，新增 OP-002A/OP-002B、OP-005A、OP-016A；将 OP-008 收敛为 dtype 非法输入错误路径并映射 test_nn_dtype_invalid_error；保留 OP-014 映射 test_nn_dtype_mismatch；保持 OP-MM-001..007 与测试函数一一对应。
- test/operation/test_operation_nn.py：仅调整测试注释编号，不改断言逻辑；修正 OP-002/005/008/014/016 多测试共号问题；将 matmul 区段 OP-MM-008 -> OP-MM-002，并顺延后续 OP-MM 编号至 OP-MM-007。
- img2col 相关实现/测试内容本轮未改动，保持在独立链路处理。
结论：非 img2col 编号映射已收敛为 spec/test 一一对应；matmul 编号漂移已修复；回归测试通过（pytest -q test/operation/test_operation_nn.py，39 passed）。
时间：2026-03-26 23:18:58
经手人：李白
任务：T-20260326-fa116e51
审查范围：spec/operation/nn.md、test/operation/test_operation_nn.py
问题：未发现 OP-002/005/008/014/016 与 OP-MM-001..007 的编号映射偏差；img2col 变更未扩散到非 img2col 编号；spec 未出现 expectation 内容；Python 参数类型提示齐全。
结论：通过

时间：2026-03-27 00:58:00 +0800
经手人：朽木露琪亚
任务：T-20260326-3062528b
任务目标：合并 nn 非 img2col 编号映射收敛并清理 worktree。
改动：移除 spec/operation/nn.md 与 test/operation/test_operation_nn.py 中误带的 img2col 公开接口/测试与映射条目，仅保留非 img2col 编号收敛内容；清理多余任务记录草稿文件。
结论：范围内文件已收敛为非 img2col 变更，待合并与清理。
