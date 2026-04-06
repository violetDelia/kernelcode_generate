时间：2026-04-06 22:09:37 +0800
经办人：金铲铲大作战
任务：T-20260406-f6e4bf89（memory_space_template_parameter_green_plan#S3 收口）
任务目标：emit_c 收口 nn.space -> Memory<Space, T> 模板参数与 dynamic memory 模板调用，并更新 spec/测试覆盖。
改动：
- spec/dsl/emit_c.md：明确 Memory<Space, T> 合同与示例，更新 dynamic memory 模板调用文本。
- kernel_gen/dsl/emit_c.py：nn.memory 发射改为 Memory<Space, T>；_space_to_c/_space_name_to_c 映射 GM/SM/LM/TSM/TLM；memory/view/dma.alloc/dynamic memory 发射移除 MemorySpace 实参并改为模板参数。
- test/dsl/test_emit_c.py：更新期望文本为 Memory<Space, T>；重命名用例以命中 gate 关键字并更新说明。
结论：实现与补测完成，目标 gate 通过。
改动文件：spec/dsl/emit_c.md；kernel_gen/dsl/emit_c.py；test/dsl/test_emit_c.py。
验证命令：PYTHONPATH=. pytest -q test/dsl/test_emit_c.py -k "memory_space_template or maps_nn_space"
退出码：0
关键输出：2 passed, 17 deselected in 0.59s
已知风险：仅运行指定 gate 子集，未覆盖其他 emit_c 用例。
下一步建议：进入审查，确认 emit_c 模板文本与合同一致。

时间：
2026-04-06 22:16 +0800

经办人：
提莫炖蘑菇

任务：
T-20260406-148df647（memory_space_template_parameter_green_plan#S3-审查）

任务目标：
- 核对 emit_c 对 Memory<Space, T> 的稳定发射与 spec/test 对齐
- 核对失败短语与测试断言一致
- 核对改动范围无越界

改动：
- spec/dsl/emit_c.md、kernel_gen/dsl/emit_c.py、test/dsl/test_emit_c.py

结论：
- 通过

问题清单：
- 无

风险：
- 未发现新增风险

验证命令：
- git diff --name-only
- git diff
- PYTHONPATH=. pytest -q test/dsl/test_emit_c.py -k "memory_space_template or maps_nn_space"

关键输出：
- git diff --name-only 仅 3 个文件：spec/dsl/emit_c.md、kernel_gen/dsl/emit_c.py、test/dsl/test_emit_c.py
- 2 passed, 17 deselected in 0.47s

漏洞排查结果：
- 未发现明显边界或异常路径缺口；错误短语与测试断言一致

改进建议：
- 无

下一步建议：
- 创建合并任务，由李白合并

最终结论：
- 通过
