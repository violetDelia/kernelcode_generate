# 20260319-dialect-nn-broadcast-refactor

- 任务: T-20260319-d0879d44
- 执行人: 摸鱼小分队
- worktree: /home/lfr/kernelcode_generate
- 时间: 2026-03-19 01:22:00 +0800

## 本次改动
- 在 `spec/dialect/nn.md` 补充 `nn.broadcast` 的待补方言规范（字段、verifier、parse/print）与测试清单，并明确与上游 `operation/nn` broadcast 的分层关系。

## 变更文件
- `spec/dialect/nn.md`

## 实现/测试待跟进
- 当前 `python/dialect/nn.py` 与 `test/dialect/test_nn_dialect.py` 尚未提供 `nn.broadcast`；需补齐 `NnBroadcastOp` 与 TC-NN-BC-001..004。
