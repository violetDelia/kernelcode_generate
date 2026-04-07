# 20260406-nn-mlir-lowering-s2c

时间: 2026-04-07 01:38:36 +0800
经办人: jcc你莫辜负
任务: T-20260407-b32e6210（nn_mlir_gen_lowering_expectation_green_plan-S2C-收口）
任务目标: conv helper 分解为 nn.img2col2d + nn.matmul，fc helper 分解为 nn.matmul，并补齐测试与验证。
结论: 按用户要求暂停，等待继续指示。
证据:
- 暂停命令: bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file TODO.md -pause -task_id T-20260407-b32e6210 -agents-list agents/codex-multi-agents/agents-lists.md
- 暂停原因: 用户要求暂停。
- 恢复条件: 管理员/用户明确恢复指令后继续。

时间: 2026-04-07 13:51:59 +0800
经办人: 朽木露琪亚
任务: T-20260407-632a9602（nn_mlir_gen_lowering_expectation_green_plan-S2C-1-收口任务）
任务目标: 仅收口 conv 的前端分解，输出 raw nn.img2col2d + nn.matmul，并补齐规格、实现与测试证据。
改动:
- kernel_gen/dsl/ast.py：纳入同链 conv helper import 绑定与 AST 解析改动，保证 build_func_op 可识别 conv(value, weight, ...)。
- kernel_gen/dsl/emit_mlir.py：修正 conv lowering 的 numel 表达式拼装；为 symbol 场景补齐 symbol.get_dim/symbol.mul 维度构造；保持输出为 raw nn.img2col2d + dma.reshape + nn.matmul + dma.reshape。
- kernel_gen/dsl/mlir_gen.py：返回注解比较改为支持符号表达式语义等价，避免 H/W 等价表达式误报不一致。
- spec/dsl/mlir_gen.md、spec/dsl/emit_mlir.md：补充 conv helper 合同、失败短语与测试映射（MGEN-C1C/C1D/C1E、EMIT-C1C）。
- test/dsl/test_mlir_gen.py：新增 conv 正向/负向用例，覆盖 raw lowering、symbol 结果、非法 stride 与参数个数错误。
结论: 已完成当前阶段；两条验证命令均通过，conv helper 生成 raw nn.img2col2d + nn.matmul，未出现 Unsupported call expression 与 nn.conv。
证据:
- git diff --name-only：kernel_gen/dsl/ast.py、kernel_gen/dsl/emit_mlir.py、kernel_gen/dsl/mlir_gen.py、spec/dsl/emit_mlir.md、spec/dsl/mlir_gen.md、test/dsl/test_mlir_gen.py。
- 验证命令：PYTHONPATH=. pytest -q test/dsl/test_mlir_gen.py -k "conv or img2col2d or matmul"；exit=0；摘要：10 passed, 129 deselected, 1 warning。
- 验证命令：PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/conv.py；exit=0；摘要：CASE-1~CASE-4 全部通过，输出含 nn.img2col2d 与 nn.matmul，symbol H/W 表达式保留在返回类型与 raw IR 中。
- 备注：当前收口范围仅限 conv 前端分解与对应文档/测试；未扩展处理链路外的 reshape contiguous 合同整治。

时间: 2026-04-07 13:59:37 +0800
经办人: 不要啊教练
任务: T-20260407-96a1323f（nn_mlir_gen_lowering_expectation_green_plan-S2C-1-审查）
任务目标:
- 复核 conv 前端分解仅产出 raw `nn.img2col2d + nn.matmul`（允许出现为 shape 对齐引入的 `dma.reshape`），不得生成 `nn.conv`，不得回退为 `Unsupported call expression`。
- 复核记录中的验证命令与结果可复现一致。
- 复核变更范围在本阶段允许文件内。
改动:
- 仅复跑验证命令并核对输出；未修改 spec/实现/测试。
结论: 通过
范围核对:
- `git diff --name-only`（worktree=wt-20260406-nn-mlir-lowering-s2c）：`kernel_gen/dsl/{ast,emit_mlir,mlir_gen}.py`、`spec/dsl/{emit_mlir,mlir_gen}.md`、`test/dsl/test_mlir_gen.py`，与 S2C-1 记录一致。
- `git diff --cached --name-only`：无输出。
验证命令与关键输出（本次复跑）:
- `PYTHONPATH=. pytest -q test/dsl/test_mlir_gen.py -k "conv or img2col2d or matmul"`：exit=0；关键输出：`10 passed, 129 deselected, 1 warning`
- `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/conv.py`：exit=0；关键输出：CASE-1/2 的打印 IR 均包含 `nn.img2col2d` 与 `nn.matmul`，且未出现 `nn.conv`；CASE-3/4 为失败边界说明未报错。
口径复核（conv 分解输出）:
- `test_build_func_op_supports_conv_helper_call` 断言 `nn.img2col2d`/`nn.matmul` 出现且 `nn.conv` 不出现，符合 S2C-1 “conv -> raw nn.img2col2d + nn.matmul”目标。
- expectation CASE-1/2 的 func.func 文本同样符合：出现 `nn.img2col2d` 与 `nn.matmul`；中间 `dma.reshape` 仅用于矩阵乘法 shape 对齐，不构成 `nn.conv` 输出。

时间: 2026-04-07 14:45:17 +0800
经办人: 小李飞刀
任务: T-20260407-141d537d（nn_mlir S2C-2 收口：fc -> nn.matmul）
任务目标: build_func_op 可识别 fc helper，输出 raw nn.transpose + nn.matmul；fc 失败边界按 expectation 触发显式错误。
改动:
- kernel_gen/dsl/ast.py：新增 fc helper 解析与 FCAST 节点，纳入允许的 nn helper 列表。
- kernel_gen/dsl/emit_mlir.py：补齐 FCAST 类型推导与 lowering，生成 nn.transpose + nn.matmul，并纳入支持集合。
- expectation 资源同步：从 /home/lfr/kernelcode_generate/expectation/ 拷贝 expectation/dsl/mlir_gen/dialect/nn/fc.py 与 expectation/utils/{case_runner.py, compare.py} 以补齐 worktree 缺失文件。
结论: 验收命令通过，fc helper 生成 nn.transpose + nn.matmul，失败边界按 expectation 报错。
改动文件:
- kernel_gen/dsl/ast.py
- kernel_gen/dsl/emit_mlir.py
- expectation/dsl/mlir_gen/dialect/nn/fc.py
- expectation/utils/case_runner.py
- expectation/utils/compare.py
验证命令:
- pytest -q test/dsl/test_mlir_gen.py -k "fc or matmul"
- PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/fc.py
退出码:
- 0
- 0
关键输出:
- 1 passed, 138 deselected in 0.53s
- CASE-1~CASE-3 通过；IR 含 nn.transpose 与 nn.matmul
已知风险: 无
下一步建议: 创建 S2C-2 审查任务，复核 fc lowering 与验证命令可复现。

时间: 2026-04-07 14:57:37 +0800
经办人: 小李飞刀
任务: T-20260407-0c7f4314（nn_mlir S2C-2 fc 收口）
任务目标: 仅收口 fc helper 前端分解，输出 raw nn.matmul；复核 expectation/dsl/mlir_gen/dialect/nn/fc.py 通过。
改动:
- 无新增实现改动；复跑验收命令并确认 fc helper lowering 为 nn.transpose + nn.matmul，未出现 nn.fc 与 Unsupported call expression。
结论: 验收命令通过，收口完成。
改动文件:
- kernel_gen/dsl/ast.py
- kernel_gen/dsl/emit_mlir.py
- agents/codex-multi-agents/log/task_records/2026/15/20260406-nn-mlir-lowering-s2c.md
范围说明:
- git diff --name-only：agents/codex-multi-agents/log/task_records/2026/15/20260406-nn-mlir-lowering-s2c.md、kernel_gen/dsl/ast.py、kernel_gen/dsl/emit_mlir.py
验证命令:
- pytest -q test/dsl/test_mlir_gen.py -k "fc or matmul"
- PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/fc.py
退出码:
- 0
- 0
关键输出:
- 1 passed, 138 deselected in 0.26s
- CASE-1~CASE-3 通过；IR 含 nn.transpose 与 nn.matmul
已知风险: 无
下一步建议: 新建 S2C-2 审查任务，复核 fc lowering 与命令可复现。

时间: 2026-04-07 16:17:45 +0800
经办人: 提莫炖蘑菇
任务: T-20260407-009053a4（nn_mlir_gen_lowering_expectation_green_plan-S2C-2-审查）
任务目标:
- 复核 fc helper 不生成 nn.fc，分解为 nn.transpose + nn.matmul。
- 复核变更范围与记录一致。
- 复核两条验收命令可复现。
改动:
- 范围核对：git diff --name-only = agents/codex-multi-agents/log/task_records/2026/15/20260406-nn-mlir-lowering-s2c.md、kernel_gen/dsl/ast.py、kernel_gen/dsl/emit_mlir.py。
- 仅复跑验收命令并核对输出；未修改 spec/实现/测试。
结论: 通过
问题清单: 无
风险: 未发现明显风险与异常路径缺口。
验证命令:
- pytest -q test/dsl/test_mlir_gen.py -k "fc or matmul"（exit=0）
- PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/fc.py（exit=0）
关键输出:
- 1 passed, 138 deselected in 0.44s
- CASE-1~CASE-3 通过；IR 含 nn.transpose 与 nn.matmul，未出现 nn.fc
下一步建议: 新建合并任务给李白。
