时间：2026-04-12 10:15
经办人：小李飞刀
任务：T-20260411-40f2c480
任务目标：收口 matmul/img2col lowering 与测试
改动：更新 `kernel_gen/passes/lowering/nn_to_kernel.py`（img2col 参数归一为 symbol.int、补 stride/dilation/pad attr、动态维构造与返回修复）；扩展 `kernel_gen/dialect/nn.py` _parse_dim_list 支持表达式维度；调整 `kernel_gen/tools/ircheck.py` 归一 kernel.img2col1d 行的 #builtin.int；新增 `test/pass/nn_lowering/matmul.py`、`test/pass/nn_lowering/img2col1d.py`、`test/pass/nn_lowering/img2col2d.py`。
验证：pytest -q test/pass/nn_lowering/matmul.py -> 1 passed；pytest -q test/pass/nn_lowering/img2col1d.py -> 1 passed；SYMPY_GMPY=0 pytest -q test/pass/nn_lowering/img2col2d.py -> 1 passed；PYTHONDONTWRITEBYTECODE=1 SYMPY_GMPY=0 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260411-nn-lowering-s5:/home/lfr/kernelcode_generate python /home/lfr/kernelcode_generate/expectation/pass/lowing/nn_lowering/matmul.py -> ok；PYTHONDONTWRITEBYTECODE=1 SYMPY_GMPY=0 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260411-nn-lowering-s5:/home/lfr/kernelcode_generate python /home/lfr/kernelcode_generate/expectation/pass/lowing/nn_lowering/img2col/img2col1d.py -> ok；PYTHONDONTWRITEBYTECODE=1 SYMPY_GMPY=0 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260411-nn-lowering-s5:/home/lfr/kernelcode_generate python /home/lfr/kernelcode_generate/expectation/pass/lowing/nn_lowering/img2col/img2col2d.py -> ok。
结论：build 已完成；本地需设置 SYMPY_GMPY=0 避免 sympy SystemError，当前结果可流转下一阶段。

时间：2026-04-12 10:20
经办人：不要啊教练
任务：T-20260411-40f2c480
任务目标：复核 matmul/img2col lowering 与测试、expectation 证据
改动：
- 复核文件：kernel_gen/passes/lowering/nn_to_kernel.py、kernel_gen/dialect/nn.py、kernel_gen/tools/ircheck.py、test/pass/nn_lowering/matmul.py、test/pass/nn_lowering/img2col1d.py、test/pass/nn_lowering/img2col2d.py、spec/pass/lowering/nn_lowering.md、spec/dialect/nn.md、spec/operation/nn.md。
- 复核结果：img2col 参数归一为 symbol.int 且 attr 由 symbol-int 派生；matmul/img2col 的 dynamic alloc 与输出形态与 spec/用例一致；新增测试文件头注释与示例齐全。
- 问题列表：未发现需修改项。
- 漏洞排查结果：
  - 输入校验绕过：未发现新增风险。
  - 类型/形状绕过：未发现新增风险。
  - 边界越界：未发现新增风险。
  - 错误处理缺失：未发现新增风险。
  - 状态污染：未发现新增风险。
  - 资源释放问题：未发现新增风险。
- 改进建议：未发现额外改进点。
验证：
- PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/nn_lowering/matmul.py -> 1 passed
- PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/nn_lowering/img2col1d.py -> 1 passed
- SYMPY_GMPY=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/nn_lowering/img2col2d.py -> 1 passed
- PYTHONDONTWRITEBYTECODE=1 SYMPY_GMPY=0 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260411-nn-lowering-s5:/home/lfr/kernelcode_generate python /home/lfr/kernelcode_generate/expectation/pass/lowing/nn_lowering/matmul.py -> exit 0
- PYTHONDONTWRITEBYTECODE=1 SYMPY_GMPY=0 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260411-nn-lowering-s5:/home/lfr/kernelcode_generate python /home/lfr/kernelcode_generate/expectation/pass/lowing/nn_lowering/img2col/img2col1d.py -> exit 0
- PYTHONDONTWRITEBYTECODE=1 SYMPY_GMPY=0 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260411-nn-lowering-s5:/home/lfr/kernelcode_generate python /home/lfr/kernelcode_generate/expectation/pass/lowing/nn_lowering/img2col/img2col2d.py -> exit 0
结论：通过；建议进入 merge 任务。
