时间：2026-04-13 01:52
经办人：咯咯咯
任务：T-20260413-20957b44
任务目标：更新默认 pipeline 顺序并补充 lower-nn-to-kernel 命名说明。
改动：
- 更新 spec/pass/pipeline/default_lowering.md：pass 顺序改为 DecompassPass -> LowerNnToKernelPass -> BufferResultsToOutParamsPass -> LowerDmaMemoryHierarchyPass；补充 lower-nn-to-kernel 命名说明。
验证：未执行命令，原因：文档更新。
结论：spec 已更新；可进入后续审查/合并流程。
时间：2026-04-13 03:44
经办人：李白
任务：T-20260413-20957b44
任务目标：合并 decompass 迁移与 default_lowering 顺序/命名说明改动
改动：准备从 wt-20260413-decompass-move-s1 合入 decompass 迁移相关实现、registry、spec、测试与记录文件。
验证：未执行命令，原因：合并阶段沿用记录中的验证结果。
结论：进入合并流程，完成后回报管理员执行 -done。
