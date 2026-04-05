# expectation_pass_nn_to_kernel_green_plan.md

## 进度

| 编号 | 依赖 | worktree | 记录文件 | 进度 |
| --- | --- | --- | --- | --- |
| `S1` | `无` | `/wt-20260405-exp-pass-nn-to-kernel-s1` | `20260405-exp-pass-nn-to-kernel-s1.md` | `已合并（2026-04-05，T-20260405-f3f39cd9，3b1e080）。` |
| `S2` | `S1` |  |  | `未开始` |
| `S3` | `S2` |  |  | `未开始` |
| `S4` | `S3` |  |  | `未开始` |
| `I*` | `S1、S2、S3、S4` |  |  | `当前无新增任务。` |

## 功能说明

- 为 `expectation_pass_nn_to_kernel_green_plan` 提供当前推进状态与可分发视图。
- 本文件只维护进度与收口口径，不替代计划书正文。

## 使用示例

- 管理员按计划书顺序分发任务；每个编号仅在依赖完成后启动。
- 每条进度更新需附对应任务记录文件证据。

## 文档信息

- 创建者：`神秘人`
- 最后一次更改：`咯咯咯`
- `文档`：[`ARCHITECTURE/plan/expectation_pass_nn_to_kernel_green_plan.md`](../../ARCHITECTURE/plan/expectation_pass_nn_to_kernel_green_plan.md)
- `spec`：[`spec/pass/lowering/nn_to_kernel.md`](../../spec/pass/lowering/nn_to_kernel.md)
- `功能实现`：[`kernel_gen/passes/lowering/nn_to_kernel.py`](../../kernel_gen/passes/lowering/nn_to_kernel.py)
- `test`：[`test/pass/test_lowering_nn_to_kernel.py`](../../test/pass/test_lowering_nn_to_kernel.py)

## 当前范围

- 只收口 `nn -> kernel` lowering 链路与对应 expectation gate。
- 不在本文件扩写上游计划正文。

## 目标终态

- `expectation/pass/lowing/nn_to_kernel` gate 清单稳定可执行。
- `nn_to_kernel` lowering 结果与 gate 口径一致。

## 计划任务

- 以 `ARCHITECTURE/plan/expectation_pass_nn_to_kernel_green_plan.md` 为准，本文件仅维护进度与收口口径。

## 推荐收口顺序

1. 先完成 spec 收口并锁定 gate。
2. 再对齐实现与测试。
3. 最后完成审查/复审与合并。

## 统一验收口径

- 以计划书中列出的 gate 命令与验收标准为准。

## 当前验收结论

- 未完成。

## 建议新增任务

- 当前无新增任务。

## 当前最直接的下一步

- 推进 S2。
