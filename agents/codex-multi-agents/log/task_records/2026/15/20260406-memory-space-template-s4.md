# 20260406-memory-space-template-s4

- 时间: 2026-04-06 15:30:00 +0800
- 经办人: 金铲铲大作战
- 任务: T-20260406-9595a49e（memory_space_template_parameter_green_plan#S4）
- 任务目标: gen_kernel 函数签名与 npu_demo body 临时内存声明按 space 模板化输出，不再出现/依赖 Memory<T> 文本；补齐/更新 test/dsl/test_gen_kernel.py 覆盖。

## 改动
- kernel_gen/dsl/gen_kernel.py
  - CPU 侧 emit_c 语句后处理，规范 Memory<T> → Memory<MemorySpace::GM, T>，并清理冗余 MemorySpace::GM 构造参数。
  - conv2d img2col2d tiled 骨架改用 GM 空间的 col_tile。
  - npu_demo add+barrier 与 body-level kernel 的 out_tile 改为 TSM（避免 add 空间不一致）。
- spec/dsl/gen_kernel.md
  - npu_demo body 示例更新为 out_tsm + add/deslice 对 TSM 输出。
- test/dsl/test_gen_kernel.py
  - npu_demo add+barrier module 与断言更新为 out_tsm 管线。
  - 相关编译/顺序断言与 MemorySpace::GM 模板化输出对齐。

## 额外阅读说明
- 为确认 npu_demo add/slice/deslice 模板空间约束，额外阅读 include/npu_demo/Nn.h 与 include/npu_demo/Dma.h（仅阅读，用于定位编译失败原因）。

## 验证
- 命令: PYTHONPATH=. pytest -q test/dsl/test_gen_kernel.py
- 退出码: 0
- 关键输出: 54 passed in 2.28s

## 结论
- gen_kernel 输出已按 MemorySpace 模板化收口，npu_demo/CPU 编译用例与新增断言全部通过。

## 已知风险
- 无。

## 下一步建议
- 进入审查：核对 S4 生成源码与 spec/测试一致性，关注 npu_demo out_tsm 语义是否接受。

- 时间: 2026-04-06 23:03:28 +0800
- 经办人: 提莫炖蘑菇
- 任务: T-20260406-2c86c732（memory_space_template_parameter plan S4 审查）
- 任务目标: 核对 gen_kernel 输出对 Memory<Space,T> 的模板化口径、CPU 语句规范与 npu_demo 管线一致性；核对 spec/test 与实现一致；复跑验证命令。

## 改动
- kernel_gen/dsl/gen_kernel.py
  - 增补 MemorySpace 模板映射与 Memory<Space,T> 输出；CPU 侧 emit_c 语句归一化 Memory<T> → Memory<MemorySpace::GM, T>；npu_demo body 管线对齐 out_tsm/TSM/TLM 模板调用。
- spec/dsl/gen_kernel.md
  - CPU 与 npu_demo 示例更新为 Memory<MemorySpace::GM, T> / get_dynamic_memory<MemorySpace::TSM/TLM, T>()，并体现 out_tsm 管线。
- test/dsl/test_gen_kernel.py
  - 断言与编译用例同步到 Memory<MemorySpace::GM, T> 与 out_tsm 形态。

## 结论
- 通过：spec/实现/测试一致，CPU 语句规范化与 npu_demo 管线模板化满足合同；未见 silent fallback 或错误短语漂移。

## 问题清单
- 无。

## 风险
- 未发现新增漏洞风险（未见输入绕过、异常路径缺失或错误处理遗漏）。

## 漏洞排查结果
- 重点检查 Memory 模板化、CPU 语句归一化与 npu_demo out_tsm 管线，未发现越界/类型绕过或异常处理缺失。

## 验证命令
- PYTHONPATH=. pytest -q test/dsl/test_gen_kernel.py

## 关键输出
- 54 passed in 1.84s

## 下一步建议
- 进入合并收口。
