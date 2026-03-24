## 正在执行的任务
| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 指派 | 状态 | 用户指导 | 记录文件 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T-20260325-bb5cc638 | 神秘人 | 2026-03-25 02:28:33 +0800 | /home/lfr/kernelcode_generate/wt-20260325-expectation-mlir-gen-symbol-arith-group | 整体实现收敛 expectation symbol 算术链路：在 /home/lfr/kernelcode_generate/wt-20260325-expectation-mlir-gen-symbol-arith-group 以 expectation/dsl/mlir_gen/dialect/symbol/{add,sub,mul,truediv,floordiv}.py 为基线，补齐 symbol.div 与 symbol.floordiv 的 dialect op / emit lowering，最小扩展 spec/dsl/mlir_gen.md 与 test/dsl/test_ast_visitor.py 对 sub/mul/truediv/floordiv 的 lowering 测试和 MGEN 映射，并逐个执行 expectation 与必要 pytest 验证；该任务已获用户明确授权可修改 expectation。完成后回报改动、验证与后续建议，不要自行使用 -done。 | 朽木露琪亚 | 进行中 |  | agents/codex-multi-agents/log/task_records/2026/12/20260325-expectation-mlir-gen-symbol-arith-group.md |
| T-20260325-754706ca | 神秘人 | 2026-03-25 02:38:34 +0800 | /home/lfr/kernelcode_generate/wt-20260324-spec-clean-nn | 清理已合并的 nn spec-clean worktree：在 /home/lfr/kernelcode_generate/wt-20260324-spec-clean-nn 核对主分支提交 26f4920 已包含 spec/operation/nn.md 与 test/operation/test_operation_nn.py 业务改动后，删除该 worktree 与对应分支；不得改动 agents/TODO/DONE/AGENTS/skills/expectation。完成后回报清理范围与残留情况，不要自行使用 -done。 | 金铲铲大作战 | 进行中 |  | agents/codex-multi-agents/log/task_records/2026/12/20260324-spec-clean-nn.md |
| T-20260325-eccde831 | 神秘人 | 2026-03-25 02:38:39 +0800 | /home/lfr/kernelcode_generate/wt-20260325-expectation-alloc-py | 严格复审 alloc expectation 链路：在 /home/lfr/kernelcode_generate/wt-20260325-expectation-alloc-py 以 expectation/operation/dma/alloc.py 为唯一有效 expectation 基线，只读核对 spec/operation/dma.md、test/operation/test_operation_dma.py 与 expectation 的映射闭环，确认新增 TC-OP-DMA-AF-007 与 test_alloc_default_stride_for_symbolic_shape 是否满足规则；不要修改业务文件。完成后回报通过/需修改/阻塞，不要自行使用 -done。 | 摸鱼小分队 | 进行中 |  | agents/codex-multi-agents/log/task_records/2026/12/20260325-expectation-alloc-py.md |
| T-20260325-35b37330 | 神秘人 | 2026-03-25 02:38:43 +0800 | /home/lfr/kernelcode_generate/wt-20260325-expectation-mlir-gen-add-scalar | 只读复审 add_scalar expectation 链路：在 /home/lfr/kernelcode_generate/wt-20260325-expectation-mlir-gen-add-scalar 核对 expectation/dsl/mlir_gen/add_scalar.py 的授权改动是否最小且必要，并确认当前 spec/实现/测试无需变更的判断成立；不要修改业务文件。完成后回报通过/需修改/阻塞，不要自行使用 -done。 | 李白 | 进行中 |  | agents/codex-multi-agents/log/task_records/2026/12/20260325-expectation-mlir-gen-add-scalar.md |
| T-20260325-0def5288 | 神秘人 | 2026-03-25 02:38:47 +0800 | /home/lfr/kernelcode_generate/wt-20260325-symbol-to-float-r2 | 补齐 symbol.to_float expectation 链路：在 /home/lfr/kernelcode_generate/wt-20260325-symbol-to-float-r2 新增 symbol.to_float 的有效 expectation 基线，并最小收敛对应 spec/dialect/symbol.md、kernel_gen/dialect/symbol.py、test/dialect/test_symbol_dialect.py 或相关 lowering/IR 说明，使 expectation/spec/实现/测试闭环；该任务已获用户明确授权可新增 expectation。完成后执行必要 expectation 与 pytest 验证，回报改动、验证与后续建议，不要自行使用 -done。 | 我不是牛马 | 进行中 |  | agents/codex-multi-agents/log/task_records/2026/12/20260325-symbol-to-float-r2.md |

## 任务列表
| 任务 ID | 发起人 | 创建时间 | worktree | 描述 | 指派 | 记录文件 |
| --- | --- | --- | --- | --- | --- | --- |

## 需要用户确认的事项
| 任务 ID | 创建时间 | worktree | 描述 | 用户确认状态 | 记录文件 |
| --- | --- | --- | --- | --- | --- |
