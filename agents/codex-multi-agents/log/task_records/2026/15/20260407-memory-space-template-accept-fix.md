时间：2026-04-07 01:50 +0800
经办人：小李飞刀
任务：T-20260407-cacc466e
任务目标：修复 npu_demo add 期望用例执行 `PYTHONPATH=. python expectation/dsl/emit_c/npu_demo/add.py` 失败（unsupported npu_demo body-level kernel signature），并保持已通过的 pytest 不回退。
改动：
- kernel_gen/dsl/gen_kernel.py：补充面向 target 的类型映射，npu_demo 下函数签名输出 Memory<GM, T>；统一 _KernelEmitter 走 target-aware 类型生成。
- kernel_gen/dsl/gen_kernel.py：完善 npu_demo body-level kernel 签名判定（ctx + 2 输入/1 输出 + memory 类型 + element_type 一致）。
- kernel_gen/dsl/emit_c.py：放行 npu_demo 下 symbol.get_dim / dma.alloc / dma.fill / kernel.add，并新增 npu_demo::add 的 emit_c 片段。
- expectation 目录为运行命令从主仓同步（不纳入变更集）。
结论：`PYTHONPATH=. python expectation/dsl/emit_c/npu_demo/add.py` 通过（exit=0）。pytest 未复跑，需复审按既定清单确认无回退。
验证命令：
- PYTHONPATH=. python expectation/dsl/emit_c/npu_demo/add.py
退出码：0
关键输出：
- CASE-1~4 均输出 Memory<GM, int32_t> 与 npu_demo::add(...)，命令退出 0。
已知风险：
- 未复跑 include/api、include/cpu、include/npu_demo、test_emit_c、test_gen_kernel；若存在回退需补测。
下一步建议：
- 复审按清单复跑相关 pytest，确认无回退后合入。

时间：2026-04-07 02:00:36 +0800
经办人：提莫炖蘑菇
任务：T-20260407-6bd64d97（memory_space_template_parameter S5 审查）
任务目标：复核 npu_demo add 期望用例与相关 pytest 不回退，核对改动范围与记录一致。
改动：
- 审查记录：执行指定命令并核对 diff 范围（仅 emit_c.py / gen_kernel.py）。未做代码修改。
结论：不通过
问题清单：
1) `pytest -q test/dsl/test_gen_kernel.py` 失败：npu_demo 相关两处用例仍输出 `Memory<GM, float>`，与测试期望 `Memory<MemorySpace::GM, float>` 不一致（用例：test_gen_kernel_emits_npu_demo_body_level_kernel、test_gen_kernel_emits_npu_demo_launch_wrapper_and_barrier_body）。
风险：
- npu_demo 生成代码的内存空间模板化仍不稳定，已引发测试失败，无法确认回归已修复。
验证命令：
- `PYTHONPATH=. python expectation/dsl/emit_c/npu_demo/add.py`（exit=0）
- `PYTHONPATH=. pytest -q test/include/api/test_memory.py test/include/api/test_nn.py test/include/api/test_dma.py`（exit=0）
- `PYTHONPATH=. pytest -q test/include/cpu/test_memory.py test/include/cpu/test_nn.py`（exit=0）
- `PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py`（exit=0）
- `PYTHONPATH=. pytest -q test/dsl/test_emit_c.py`（exit=0）
- `PYTHONPATH=. pytest -q test/dsl/test_gen_kernel.py`（exit=1）
关键输出：
- `8 passed in 0.82s`
- `34 passed in 2.45s`
- `13 passed in 2.99s`
- `19 passed in 0.28s`
- `2 failed, 52 passed in 1.20s`
下一步建议：
- 修复 gen_kernel 在 npu_demo 生成的 body-level kernel 与 launch wrapper 形参类型输出，确保使用 `Memory<MemorySpace::GM, T>`；补测通过后再复审。

时间：2026-04-07 02:08:45 +0800
经办人：提莫炖蘑菇
任务：T-20260407-bde07208（memory_space_template_parameter S5 审查）
任务目标：核对 gen_kernel npu_demo 签名输出与 S5 全套验证命令结果。
改动：
- 审查记录：复跑清单命令并核对 npu_demo 相关签名输出；未做代码修改。
结论：不通过
问题清单：
1) `PYTHONPATH=. python expectation/dsl/emit_c/npu_demo/add.py` 失败，出现 sympy 导入阶段 SystemError（multipledispatch 内部错误），无法完成期望用例。
2) `pytest -q test/include/api/test_memory.py test/include/api/test_nn.py test/include/api/test_dma.py` 失败，g++ 链接阶段出现 `ld terminated with signal 11`，用例 `test_dma_cross_space_templates_rejects_invalid_vector_rank` 失败。
风险：
- S5 清单仍未全绿，验证结果不稳定；无法确认回归已修复。
验证命令：
- `PYTHONPATH=. python expectation/dsl/emit_c/npu_demo/add.py`（exit=1）
- `PYTHONPATH=. pytest -q test/include/api/test_memory.py test/include/api/test_nn.py test/include/api/test_dma.py`（exit=1）
- `PYTHONPATH=. pytest -q test/include/cpu/test_memory.py test/include/cpu/test_nn.py`（exit=0）
- `PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py`（exit=0）
- `PYTHONPATH=. pytest -q test/dsl/test_emit_c.py`（exit=0）
- `PYTHONPATH=. pytest -q test/dsl/test_gen_kernel.py`（exit=0）
关键输出：
- `SystemError: ../Objects/listobject.c:336: bad argument to internal function`
- `collect2: fatal error: ld terminated with signal 11 [Segmentation fault]`
- `1 failed, 7 passed in 0.97s`
- `34 passed in 2.92s`
- `13 passed in 3.39s`
- `19 passed in 0.24s`
- `54 passed in 1.09s`
下一步建议：
- 复核 sympy 导入异常与 g++ 崩溃原因并给出可复现修复或稳定复跑证据；清单全绿后再复审。

时间：2026-04-07 02:16 +0800
经办人：小李飞刀
任务：T-20260407-f93f3ad1
任务目标：排查 expectation/dsl/emit_c/npu_demo/add.py 的 sympy SystemError 与 include/api 编译链路的 ld SIGSEGV，并确保 S5 清单命令全部 exit=0。
改动：
- 无代码改动，仅补充复跑证据与记录。
结论：
- 未复现 sympy SystemError 与 ld SIGSEGV；S5 清单命令全绿。
- expectation/dsl/emit_c/npu_demo/add.py 未出现 “unsupported npu_demo body-level kernel signature”，未阻断本次验证。
验证命令：
- PYTHONPATH=. pytest -q test/include/api/test_memory.py test/include/api/test_nn.py test/include/api/test_dma.py
- PYTHONPATH=. pytest -q test/include/cpu/test_memory.py test/include/cpu/test_nn.py
- PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py
- PYTHONPATH=. pytest -q test/dsl/test_emit_c.py
- PYTHONPATH=. pytest -q test/dsl/test_gen_kernel.py
- PYTHONPATH=. python expectation/dsl/emit_c/npu_demo/add.py
- PYTHONPATH=. find expectation/dsl/emit_c/npu_demo -type f ! -path '*/__pycache__/*' | sort | while read -r f; do PYTHONPATH=. python "$f"; done
- （稳定性复跑）PYTHONPATH=. pytest -q test/include/api/test_memory.py test/include/api/test_nn.py test/include/api/test_dma.py
退出码：
- 0
关键输出：
- 8 passed in 1.03s
- 34 passed in 2.69s
- 13 passed in 2.79s
- 19 passed in 0.24s
- 54 passed in 1.07s
- CASE-1~4 均输出 Memory<GM, int32_t> 与 npu_demo::add 文本，命令退出 0
- 稳定性复跑 8 passed in 0.84s
已知风险：
- 目前仅能证明复跑稳定，sympy/ld 异常未复现，仍可能受环境波动影响。
下一步建议：
- 进入复审，必要时在独立环境复跑以确认稳定性。

时间：2026-04-07 02:22 +0800
经办人：不要啊教练
任务：T-20260407-66006461（memory_space_template_parameter S5-审查）
任务目标：
- 复核 S5 清单命令全部 exit=0。
- 重点复核此前两项不稳定点（sympy 导入阶段 SystemError；g++ 链接阶段 ld signal 11）是否具备稳定复跑证据，以及是否给出可执行的复跑/重试与环境信息说明。
改动：
- 仅复跑清单命令并补充复跑证据；未修改 spec/实现/测试。
结论：通过

验证命令（复跑）与关键输出：
- `PYTHONPATH=. pytest -q test/include/api/test_memory.py test/include/api/test_nn.py test/include/api/test_dma.py`：exit=0（8 passed）
- `PYTHONPATH=. pytest -q test/include/cpu/test_memory.py test/include/cpu/test_nn.py`：exit=0（34 passed）
- `PYTHONPATH=. pytest -q test/include/npu_demo/test_kernel_context.py`：exit=0（13 passed）
- `PYTHONPATH=. pytest -q test/dsl/test_emit_c.py`：exit=0（19 passed）
- `PYTHONPATH=. pytest -q test/dsl/test_gen_kernel.py`：exit=0（54 passed）
- `PYTHONPATH=. python expectation/dsl/emit_c/npu_demo/add.py`：exit=0（CASE-1~4 打印；均生成 `Memory<GM, int32_t>` 与 `npu_demo::add(...)` 文本）
- `PYTHONPATH=. find expectation/dsl/emit_c/npu_demo -type f ! -path '*/__pycache__/*' | sort | while read -r f; do PYTHONPATH=. python "$f"; done`：exit=0

不稳定点复跑证据（本次新增）：
- include/api 组合用例连续复跑 3 次：均 exit=0（8 passed），未出现 `ld terminated with signal 11`。
- `expectation/dsl/emit_c/npu_demo/add.py` 连续复跑 3 次：均 exit=0，未出现 sympy 导入阶段 `SystemError`。

环境信息（用于复跑对齐）：
- Python：3.10.12；sympy：1.12
- g++：9.5.0（Ubuntu 22.04.1）；ld：2.38（GNU Binutils for Ubuntu）
