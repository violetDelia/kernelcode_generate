时间: 2026-03-28 17:25:00 +0800
任务: T-20260328-193d9f9b
任务目标: 统一 spec 术语与阶段命名（lowering/emit_c/gen_kernel/operation/dialect）。
改动: 经办人=摸鱼小分队；统一 spec/pass/lowing/nn_to_kernel.md 中 lowing->lowering 命名，更新 spec/功能实现/测试链接与示例引用，移除 expectation 相关执行命令与用例映射，保留 test_lowing_nn_to_kernel.py 对应的 COV-N2K-001..009 映射。
结论: 已完成术语统一并满足 rg 校验；实现/测试侧命名与路径需后续任务同步到 lowering。
时间: 2026-03-28 19:41:20 +0800
任务: T-20260328-849e9377
任务目标: 同步 lowing->lowering 命名，重命名 pass 目录与测试文件并更新引用，保持与 spec/pass/lowering/nn_to_kernel.md 一致。
改动: 重命名 kernel_gen/passes/lowing -> kernel_gen/passes/lowering、spec/pass/lowing -> spec/pass/lowering、test/pass/test_lowing_nn_to_kernel.py -> test/pass/test_lowering_nn_to_kernel.py；更新 kernel_gen/passes/lowering/{__init__,nn_to_kernel}.py 与 test/pass/test_lowering_nn_to_kernel.py 内所有 lowing 引用与导入路径；全仓 rg 检查无残留业务引用。
结论: pytest -q test/pass/test_lowering_nn_to_kernel.py 通过（exit 0，21 passed），命名统一完成，待审查。
时间: 2026-03-28 19:48:13 +0800
任务: T-20260328-8cc3e269
任务目标: 复核 nn_to_kernel pass 的 lowing->lowering 命名同步闭环，确认目录/导入/测试文件/文档路径一致，并验证 test/pass/test_lowering_nn_to_kernel.py 可通过。
改动: 审查 spec/pass/lowering/nn_to_kernel.md、kernel_gen/passes/lowering/{__init__,nn_to_kernel}.py、test/pass/test_lowering_nn_to_kernel.py 与目录结构；rg 检查无残留 lowing 业务引用；复测 pytest -q test/pass/test_lowering_nn_to_kernel.py。
结论: 通过。命名同步闭环一致，未发现残留 lowing 引用；测试 exit 0（21 passed）。漏洞排查覆盖：输入校验绕过/类型形状绕过/边界越界/错误处理缺失/状态污染/资源释放均未发现新增风险；可维护性未发现改进点。
