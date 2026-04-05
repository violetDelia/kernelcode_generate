时间: 2026-04-05 14:44:24 +0800
经办人: 朽木露琪亚
任务: T-20260405-ac6ab834
任务目标: analysis_engine_refactor S5：补齐 nn.matmul/img2col1d/img2col2d/softmax 公式并对齐结构化 shape 合同。
改动:
- 更新 `kernel_gen/analysis/compute/nn.py`：softmax 采用 `VECTOR=4*N-2*G` + `MATH=N` 双 compute item；img2col1d/2d 仅做合同校验不再统计 compute。
- 更新 `kernel_gen/analysis/memory/nn.py`：新增 softmax 读写统计（compute path）与 img2col1d/2d direct-path 读写统计，并补齐 shape/attr 校验。
- 更新 `test/analysis/test_analysis.py`：新增 softmax/img2col1d/img2col2d compute+memory 口径测试。
结论:
- Gate: `PYTHONPATH=. pytest -q test/analysis/test_analysis.py test/pass/test_analysis_func_cost.py test/pass/test_pass_manager.py` -> exit 0（87 passed）。
- 状态: 完成，无阻塞。

时间: 2026-04-05 15:08:00 +0800
经办人: 提莫炖蘑菇
任务: T-20260405-dd0246d1（复审：analysis S5）
任务目标: 复核 `kernel_gen/analysis/compute/nn.py`、`kernel_gen/analysis/memory/nn.py`、`test/analysis/test_analysis.py` + 记录；复跑 analysis gate；重点核对 softmax `VECTOR+MATH` 公式、img2col `compute=0` 与 direct-path 访存，以及结构化 shape 合同/动态维边界。

结论: 不通过（结构化 shape 合同在动态符号维场景存在硬缺口；按审查规范只要存在改进建议/证据缺口即不通过）。

范围核对:
- `git diff --name-only` 仅含：
  - `kernel_gen/analysis/compute/nn.py`
  - `kernel_gen/analysis/memory/nn.py`
  - `test/analysis/test_analysis.py`
- `git diff --cached --name-only` 为空
- 记录文件为未跟踪新增：`agents/codex-multi-agents/log/task_records/2026/14/20260405-analysis-engine-refactor-s5.md`

复跑证据:
- `PYTHONPATH=. pytest -q test/analysis/test_analysis.py test/pass/test_analysis_func_cost.py test/pass/test_pass_manager.py`
  - 结果：`87 passed in 0.41s`

通过项（本轮已确认）:
- `nn.softmax` compute analyzer 已按 `VECTOR = 4*N - 2*G`、`MATH = N` 产出双 compute item；memory analyzer 走 `GM->compute / compute->GM` 这类 compute-path，不落 `MemoryPath.UNKNOWN`。
- `nn.img2col1d/img2col2d` 当前 compute analyzer 返回 `compute=0`；memory analyzer 走 direct-path（`src->dst`），正例测试中不落 `MemoryPath.UNKNOWN`。

不通过点（硬断点）:
1) `img2col1d/img2col2d` 的“结构化 shape 合同”只在全静态整数维时校验，动态符号维会被静默放过：
   - `kernel_gen/analysis/compute/nn.py` 与 `kernel_gen/analysis/memory/nn.py` 都使用：
     - `if all(isinstance(dim, sp.Integer) for dim in input_dims + result_dims): ... expected_shape 校验`
   - 这意味着只要输入/输出任一维是符号表达式，analysis 就不会校验结果 shape 是否满足 img2col 合同，仍会继续统计 bytes/path。
   - 该行为与任务目标“对齐结构化 shape 合同”不一致，也会让错误的 symbolic result shape 混入 cost 统计。

复现证据（均 exit=0，但语义错误）:
- `PYTHONPATH=. python - <<'PY'`
  `from xdsl.dialects.builtin import ArrayAttr, IntAttr, StringAttr, f32`
  `from xdsl.ir import Block`
  `from kernel_gen.analysis.analysis import analysis, AnalysisConfig`
  `from kernel_gen.dialect.nn import NnImg2col1dOp, NnImg2col2dOp, NnMemorySpaceAttr, NnMemoryType`
  `space = NnMemorySpaceAttr.from_name("global")`
  `def make_memory_type(shape):`
  `    return NnMemoryType(ArrayAttr(shape), ArrayAttr([IntAttr(1) for _ in shape]), f32, space)`
  `input1 = make_memory_type([StringAttr("N"), StringAttr("C"), StringAttr("W")])`
  `wrong1 = make_memory_type([StringAttr("N"), StringAttr("C"), StringAttr("KW"), StringAttr("BAD")])`
  `op1 = NnImg2col1dOp(Block(arg_types=[input1]).args[0], wrong1, kw=3, sw=1, dw=1, pl=1, pr=1, space=space)`
  `print(analysis(op1, AnalysisConfig(enable_compute=True, enable_memory=True, dtype_size_overrides={"f32": 4})).total_read_bytes)`
  `input2 = make_memory_type([StringAttr("N"), StringAttr("C"), StringAttr("H"), StringAttr("W")])`
  `wrong2 = make_memory_type([StringAttr("N"), StringAttr("C"), StringAttr("KH"), StringAttr("KW"), StringAttr("BADH"), StringAttr("BADW")])`
  `op2 = NnImg2col2dOp(Block(arg_types=[input2]).args[0], wrong2, kh=3, kw=3, sh=1, sw=1, dh=1, dw=1, ph=1, pw=1, pl=1, pr=1, space=space)`
  `print(analysis(op2, AnalysisConfig(enable_compute=True, enable_memory=True, dtype_size_overrides={"f32": 4})).total_read_bytes)`
  `PY`
- 实际输出：
  - `4*BAD*C*KW*N`
  - `4*BADH*BADW*C*KH*KW*N`
- 期望：
  - 对 symbolic 维同样校验结构化输出公式，不匹配时抛 `AnalysisError`，而不是直接接受错误 result shape 并继续产出统计。

风险评估:
- 这是 analysis 合同级缺口：错误的 symbolic img2col 结果形状会被当作合法 IR 参与 compute/memory 汇总，可能污染下游 `AnalyzeFuncCostPass` 与 pass manager 成本决策。
- 当前新增测试仅覆盖静态正例，未覆盖 symbolic mismatch 负例，证据不足以证明“结构化 shape 合同”已真正收口。

唯一下一步建议:
- 派生唯一修复任务：在 `kernel_gen/analysis/compute/nn.py`、`kernel_gen/analysis/memory/nn.py` 中对 `img2col1d/img2col2d` 引入 symbolic shape 合同校验（至少比较 `N/C/K*` 维保持一致，输出窗口维与公式表达式一致），并在 `test/analysis/test_analysis.py` 补充 symbolic mismatch 负例；复跑本任务 gate 保持 exit=0。

时间：2026-04-05 15:40:00 +0800
经办人：金铲铲大作战
任务：T-20260405-a11cfab8（analysis_engine_refactor S5 修复）
任务目标：保证 symbolic img2col1d/2d 形状不匹配时抛 AnalysisError，禁止静默继续统计。
改动：
- `kernel_gen/analysis/compute/nn.py`：img2col1d/2d 统一校验结构化输出形状，symbolic 维度也必须匹配。
- `kernel_gen/analysis/memory/nn.py`：img2col1d/2d 统一校验结构化输出形状，symbolic 维度也必须匹配。
- `test/analysis/test_analysis.py`：新增 img2col1d/2d symbolic mismatch 负例，分别覆盖 compute-only 与 memory-only 分支。
- 运行 `PYTHONPATH=. pytest -q test/analysis/test_analysis.py test/pass/test_analysis_func_cost.py test/pass/test_pass_manager.py`，结果：exit=0，89 passed。
结论：symbolic img2col shape mismatch 将抛 AnalysisError，避免统计链路误接收错误形状。

时间：2026-04-05 15:08:37 +0800
经办人：金铲铲大作战
任务：T-20260405-a11cfab8（analysis_engine_refactor S5 修复）
任务目标：复跑 gate 验证 analysis S5 修复稳定通过。
改动：
- 运行 `PYTHONPATH=. pytest -q test/analysis/test_analysis.py test/pass/test_analysis_func_cost.py test/pass/test_pass_manager.py`，结果：exit=0，89 passed。
结论：gate 复跑通过。
时间: 2026-04-05 15:53:00 +0800
经办人: 不要啊教练
任务: T-20260405-e71a9ff7
任务目标: 复审 analysis S5 symbolic img2col mismatch 修复，核对 `kernel_gen/analysis/compute/nn.py`、`kernel_gen/analysis/memory/nn.py`、`test/analysis/test_analysis.py` 与同链记录文件是否在授权范围内，确认 symbolic img2col mismatch 必须抛 `AnalysisError`，不得静默接受并继续统计。
改动:
- 第一轮范围核对：`git diff --name-only` 为空；`git diff --cached --name-only` 仅含 `kernel_gen/analysis/compute/nn.py`、`kernel_gen/analysis/memory/nn.py`、`test/analysis/test_analysis.py` 与同链记录文件，未发现越界文件。
- 第二轮合同核对：`kernel_gen/analysis/compute/nn.py:343-450` 与 `kernel_gen/analysis/memory/nn.py:473-560` 已对 `nn.img2col1d/2d` 统一执行 rank/attr/结构化输出 shape 校验，不再以“全静态维”作为前置条件；symbolic 维同样参与 `expected_shape` 比较，不匹配即抛 `AnalysisError`。
- 负例门禁核对：`test/analysis/test_analysis.py:1858-1892`、`test/analysis/test_analysis.py:1946-2000` 已新增 `img2col1d/2d` symbolic mismatch 负例，并分别覆盖 `enable_compute=True, enable_memory=False` 与 `enable_compute=False, enable_memory=True` 两条链路。
- 复跑 gate：`PYTHONPATH=. pytest -q test/analysis/test_analysis.py test/pass/test_analysis_func_cost.py test/pass/test_pass_manager.py`，结果：`exit=0，89 passed in 0.44s`。
- 追加复现核对：在 worktree 内构造 symbolic `nn.img2col1d/2d` 错误结果形状，分别以 `(compute,memory)=(True,False)/(False,True)/(True,True)` 调用 `analysis(...)`，六种组合均抛出 `AnalysisError`，关键输出为 `nn.img2col1d output shape mismatch` / `nn.img2col2d output shape mismatch`。
结论: 通过。

时间：2026-04-05 15:25:37 +0800
经办人：李白
任务：T-20260405-48bb68d6（合并收口）
任务目标：按要求复跑 gate 并记录；合入指定文件与记录。
改动：
- 复跑 gate：
  - `PYTHONPATH=. pytest -q test/analysis/test_analysis.py test/pass/test_analysis_func_cost.py test/pass/test_pass_manager.py`
  - 结果：`exit=0，89 passed in 0.42s`
结论：gate 通过，满足合并条件。
