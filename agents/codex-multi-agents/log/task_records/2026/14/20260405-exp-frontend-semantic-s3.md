时间：2026-04-05 01:07:02 +0800
经办人：咯咯咯
任务：T-20260405-29b0f834
任务目标：更新 spec/dialect/nn.md 中 nn.broadcast/nn.reduce_*/nn.img2col1d/nn.img2col2d/nn.exp 的 verifier 失败口径与结果类型合同，落实结构化输出与关键短语锁定。
改动：补充 fc/conv 在方言层下沉到 nn.matmul/nn.img2col* 的边界描述；将 nn.exp/nn.reduce_* 的 verifier 关键短语改为“失败必须包含”；补充 nn.broadcast verifier 失败关键短语；将 img2col1d/2d 结果 rank 改为 4/6 并更新示例与合同表述，明确禁止方言层压扁。
结论：已完成 spec 更新，未改实现/测试；需后续实现与补测对齐新合同。

- 时间：`2026-04-05 01:16:19 +0800`
- 经办人：`不要啊教练`
- 任务：`T-20260405-c7afbbf4`
- 任务目标：
  - 复审 `spec/dialect/nn.md` 的 verifier 失败短语与 `img2col1d/2d` rank(4/6) 合同口径，确认改动范围仅限 spec。
- 改动：
  - 追加复审结论；未修改实现/测试。
- 结论：
  - `spec/dialect/nn.md` 已明确 verifier 失败短语要求，并将 `img2col1d` 结果 rank 改为 4、`img2col2d` 结果 rank 改为 6，且声明结构化输出不可压扁；与任务口径一致。
  - `git diff` 范围仅 `spec/dialect/nn.md` 与本记录文件。
  - 漏洞与风险：文本规范变更不涉及实现路径与输入处理，未发现新增安全风险；无需测试。
