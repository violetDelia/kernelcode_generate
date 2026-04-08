时间：2026-04-08 09:57:36 +0800
经办人：提莫炖蘑菇
任务：T-20260408-f42ccf22
任务目标：复核 S3C-1（exp）收口一致性与验证命令可复现性。
改动：
- 执行 `cd wt-20260408-nn-mlir-lowering-s3c && PYTHONPATH=. pytest -q test/pass/test_lowering_nn_to_kernel.py -k "exp"`，退出码 5（无用例命中，34 deselected）。
- 执行 `cd wt-20260408-nn-mlir-lowering-s3c && PYTHONPATH=. pytest -q test/dialect/test_kernel_dialect.py -k "exp"`，退出码 5（无用例命中，10 deselected）。
- 执行 `cd /home/lfr/kernelcode_generate && PYTHONPATH=wt-20260408-nn-mlir-lowering-s3c:. python expectation/pass/lowing/nn_to_kernel/exp.py`，exit=1；输出显示 `nn.exp` 未 lower 为 `kernel.exp`，报 `Unsupported nn op: nn.exp`。
结论：
- 不通过：验证命令未通过且 expectation 失败，当前无法证明 `nn.exp -> kernel.exp` 已收口；测试选择表达式未命中用例也需修正。

时间：2026-04-08 10:20:49 +0800
经办人：小李飞刀
任务：T-20260408-f42ccf22
任务目标：收口 S3C-1（exp）：实现 `nn.exp -> kernel.exp` lowering，并补齐对应 expectation 与单测。
改动：
- 新增 `kernel.exp` op：[`kernel_gen/dialect/kernel.py`](kernel_gen/dialect/kernel.py)（新增 `KernelExpOp`，约束 input/out layout 一致且 element_type 为 float）。
- pass 支持 `nn.exp -> kernel.exp`：[`kernel_gen/passes/lowering/nn_to_kernel.py`](kernel_gen/passes/lowering/nn_to_kernel.py)（在 `_build_kernel_op` 增加 `nn.exp` 分支并引入 `KernelExpOp`）。
- 补齐 kernel dialect `exp` 单测：[`test/dialect/test_kernel_dialect.py`](test/dialect/test_kernel_dialect.py)（新增 `test_kernel_exp_success/test_kernel_exp_requires_float`，并在 `test_kernel_ops_no_result` 覆盖 `kernel.exp`）。
- 补齐 pass `exp` lowering 单测：[`test/pass/test_lowering_nn_to_kernel.py`](test/pass/test_lowering_nn_to_kernel.py)（新增 `test_lower_exp_to_kernel`）。
- 新增 expectation：[`expectation/pass/lowing/nn_to_kernel/exp.py`](expectation/pass/lowing/nn_to_kernel/exp.py)（断言 after IR 命中 `kernel.exp`，且不包含 `nn.exp`）。
- 验证：
  - `cd wt-20260408-nn-mlir-lowering-s3c && pytest -q test/pass/test_lowering_nn_to_kernel.py -k "exp"`：`1 passed, 34 deselected`。
  - `cd wt-20260408-nn-mlir-lowering-s3c && pytest -q test/dialect/test_kernel_dialect.py -k "exp"`：`2 passed, 10 deselected`。
  - `cd wt-20260408-nn-mlir-lowering-s3c && PYTHONPATH=. python expectation/pass/lowing/nn_to_kernel/exp.py`：exit=0，after IR 打印包含 `"kernel.exp"`。
结论：
- 通过：以上验证项均通过，after IR 命中 `kernel.exp` 且无 `nn.exp` 残留，可进入后续审查阶段。

时间：2026-04-08 10:36:31 +0800
经办人：不要啊教练
任务：T-20260408-f42ccf22
任务目标：复审 S3C-1（exp）收口一致性、边界条件与失败路径文案稳定性。
改动：
- 复跑：`cd wt-20260408-nn-mlir-lowering-s3c && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_lowering_nn_to_kernel.py -k "exp"`：exit=0；`1 passed, 34 deselected in 0.25s`。
- 复跑：`cd wt-20260408-nn-mlir-lowering-s3c && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_kernel_dialect.py -k "exp"`：exit=0；`2 passed, 10 deselected in 0.20s`。
- 复跑：`cd wt-20260408-nn-mlir-lowering-s3c && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/pass/lowing/nn_to_kernel/exp.py`：exit=0；after IR 打印包含 `"kernel.exp"` 且不包含 `"nn.exp"`。
- 合同核对：
  - `KernelExpOp.verify_`：[`kernel_gen/dialect/kernel.py`](kernel_gen/dialect/kernel.py) 仅接受 `f16/f32/f64`。
  - `nn` 浮点集合：[`kernel_gen/dialect/nn.py`](kernel_gen/dialect/nn.py) 的 `_is_float_element_type(...)` 允许 `f16/bf16/f32/f64`。
  - `nn.exp` 文档只写“浮点类型”，但 `nn` 文档的其它浮点约束项明确包含 `bf16`：[`spec/dialect/nn.md`](spec/dialect/nn.md)。
  - `kernel.exp` 文档只写“浮点类型”，未明确是否包含 `bf16`：[`spec/dialect/kernel.md`](spec/dialect/kernel.md)。
结论：
- 需修改。
- 问题列表：
  - P1：`nn.exp` 允许的浮点集合与 `kernel.exp` verifier 的浮点集合不一致（`bf16` 处于不闭合状态）。当前链路对 `bf16` 输入的行为缺少明确合同与可复现证据，可能表现为 lowering 后被 dialect verifier 拒绝，且失败信息不易与 `nn.exp` 的失败短语对齐。
  - P1：测试/expectation 仅覆盖 `f32`，缺少 `bf16` 的“应支持/应拒绝”证据，导致后续演进时易引入不一致回归。
- 漏洞排查结果（6 类）：
  - 输入校验绕过：存在（`bf16` 路径从 `nn` 到 `kernel` 的类型集合不一致，缺少一处稳定失败说明）。
  - 类型/形状绕过：类型集合不一致风险存在；shape/stride/space 一致性由 `KernelExpOp.verify_` 覆盖。
  - 边界越界：未发现（本次变更仅涉及 verifier 与 IR 重写）。
  - 错误处理缺失：存在（对 `bf16` 的失败路径缺少端到端可复现断言）。
  - 状态污染：未发现（未见全局可变状态写入）。
  - 资源释放问题：未发现（Python 侧构造与校验，无显式资源管理点）。
- 建议动作（需派生后续任务落地后再复审）：
  - 明确 `kernel.exp` 支持的浮点集合与 `nn.exp` 的一致性策略（二选一：`kernel.exp` 支持 `bf16`；或在 lowering 前明确拒绝并锁定失败短语），并补齐对应单测与 expectation 覆盖。

时间：2026-04-08 10:51:30 +0800
经办人：jcc你莫辜负
任务：T-20260408-f42ccf22
任务目标：收口 S3C-1（exp）：补齐 bf16 口径并通过验证命令。
改动：
- 更新 kernel.exp 验证集合包含 bf16：`kernel_gen/dialect/kernel.py`（KernelExpOp 允许 BFloat16Type）。
- 补充 pass 侧 bf16 测试：`test/pass/test_lowering_nn_to_kernel.py`（新增 `test_lower_exp_to_kernel_bf16`）。
- 补充 kernel dialect bf16 测试：`test/dialect/test_kernel_dialect.py`（新增 `test_kernel_exp_supports_bf16`）。
- expectation 覆盖 f32/bf16：`expectation/pass/lowing/nn_to_kernel/exp.py`（同脚本两类 element_type）。
- 验证：
  - `pytest -q test/pass/test_lowering_nn_to_kernel.py -k "exp"`：`2 passed, 34 deselected in 0.25s`。
  - `pytest -q test/dialect/test_kernel_dialect.py -k "exp"`：`3 passed, 10 deselected in 0.18s`。
  - `PYTHONPATH=. python expectation/pass/lowing/nn_to_kernel/exp.py`：exit=0，after IR 中 f32/bf16 均命中 `kernel.exp`，且无 `nn.exp`。
结论：
- 通过：bf16 口径闭合，三条验证命令均通过，可进入后续审查。
时间：2026-04-08 10:56:19 +0800
经办人：提莫炖蘑菇
任务：T-20260408-f42ccf22
任务目标：复核 S3C-1（exp）一致性，覆盖 bf16 支持与异常路径，并确认验证命令可复现。
改动：
- 复跑 `cd wt-20260408-nn-mlir-lowering-s3c && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_lowering_nn_to_kernel.py -k "exp"`，exit=0（2 passed, 34 deselected）。
- 复跑 `cd wt-20260408-nn-mlir-lowering-s3c && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_kernel_dialect.py -k "exp"`，exit=0（3 passed, 10 deselected）。
- 复跑 `cd wt-20260408-nn-mlir-lowering-s3c && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/pass/lowing/nn_to_kernel/exp.py`，exit=0；f32/bf16 after IR 均命中 `kernel.exp` 且无 `nn.exp`。
结论：
- 通过：验证覆盖 f32/bf16 与非浮点拒绝路径，证据可复现，未发现边界与异常路径问题。
