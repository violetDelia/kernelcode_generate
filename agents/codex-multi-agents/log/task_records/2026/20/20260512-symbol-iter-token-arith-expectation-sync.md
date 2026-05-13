# 20260512-symbol-iter-token-arith-expectation-sync

- 关联任务：`T-20260512-cd17da9c`
- sync worktree：`/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith-expectation-sync`
- sync 分支：`arch/symbol-iter-token-arith-expectation-sync`
- 任务 worktree：`/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith`
- 记录用途：记录架构侧 `expectation` 合同同步 / 恢复现场；普通 execute / review / admin / merge 不得写该落点的 `expectation/`。

## 架构恢复记录（2026-05-13 23:24 +0800，守护最好的爱莉希雅）

### 恢复原因

- 管理员回报：`git worktree list` 登记的唯一 sync 落点 `/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith-expectation-sync` 曾实际缺失，review 固定 `PYTHONPATH` 依赖该路径时 `python3 -m expectation` 报 `expectation.utils` / `expectation.dialect` 缺失。
- 按当前架构口径，管理员不能用主仓 `expectation/` 替代，也不能自行重建合同资产；本次由架构侧恢复唯一 sync 落点。

### 恢复结果

- `git worktree list --porcelain` 当前显示该路径已绑定 `arch/symbol-iter-token-arith-expectation-sync`。
- sync worktree `HEAD=83fa20746c1a0dfce716cc10b536b670093e8dbd`。
- sync worktree 当前包含完整 `expectation/` 合同树：`694` 个文件，其中排除 `__pycache__` 后 `418` 个文件。
- `expectation/utils`、`expectation/dialect`、`expectation/operation`、`expectation/pass`、`expectation/tools` 等入口均存在；不再是缺包现场。

### 当前 sync diff scope

与主仓 `/home/lfr/kernelcode_generate/expectation` 按 SHA256 对比，排除 `__pycache__` 后：

- 新增文件：`0`
- 删除文件：`0`
- 变更文件：`10`

变更文件均在当前白名单 / 已同步范围内：

- `expectation/dsl/mlir_gen/dialect/nn/activation/hard_sigmoid.py`
- `expectation/dsl/mlir_gen/dialect/nn/activation/leaky_relu.py`
- `expectation/operation/arch/get_block_id.py`
- `expectation/operation/arch/get_block_num.py`
- `expectation/operation/arch/get_dynamic_memory.py`
- `expectation/operation/arch/get_subthread_id.py`
- `expectation/operation/arch/get_subthread_num.py`
- `expectation/operation/arch/get_thread_id.py`
- `expectation/operation/arch/get_thread_num.py`
- `expectation/operation/arch/launch_kernel.py`

### 恢复验证

固定 `PYTHONPATH` 导入 sanity：

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith:/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith-expectation-sync \
python3 - <<'PY'
import expectation
import expectation.utils
import expectation.dialect
print("ok")
PY
```

结果：`exit=0`。

单项验证：

```bash
EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith \
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith:/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith-expectation-sync \
python3 -m expectation.operation.arch
```

结果：`exit=0`。

```bash
EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith \
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith:/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith-expectation-sync \
python3 -m expectation.dsl.mlir_gen.dialect.nn.activation.leaky_relu
```

结果：`exit=0`。

```bash
EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith \
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith:/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith-expectation-sync \
python3 -m expectation.dsl.mlir_gen.dialect.nn.activation.hard_sigmoid
```

结果：`exit=0`。

固定 full expectation smoke：

```bash
EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith \
OMP_NUM_THREADS=1 \
OPENBLAS_NUM_THREADS=1 \
MKL_NUM_THREADS=1 \
NUMEXPR_NUM_THREADS=1 \
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith:/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith-expectation-sync \
timeout 300s python3 -m expectation
```

结果：`exit=124`，300 秒超时；命令已进入 full suite 并持续运行大量 case，未再出现 `expectation.utils` / `expectation.dialect` 缺失。该 smoke 不构成 review 通过依据；review / execute 仍必须按任务硬门禁使用固定环境跑完整 `3/3 exit=0`。

### 当前裁定

- 唯一有效 sync 落点仍是 `/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith-expectation-sync`。
- 固定验证命令继续使用：

```bash
EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith \
OMP_NUM_THREADS=1 \
OPENBLAS_NUM_THREADS=1 \
MKL_NUM_THREADS=1 \
NUMEXPR_NUM_THREADS=1 \
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith:/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith-expectation-sync \
timeout 900s python3 -m expectation
```

- 恢复完成只解决“sync 落点缺包 / 缺合同资产”问题，不等价于计划级 review 或终验通过。
- 没有 fixed full expectation `3/3 exit=0` 前，不得 review 通过、不得终验、不得 merge。

## 架构恢复补录（2026-05-13 23:52 +0800，大闸蟹）

### 恢复动作

- 核对到 `git worktree list --porcelain` 仍登记 `/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith-expectation-sync`，但路径实际缺失且为 `prunable`。
- 已执行 `git worktree prune` 并在同一路径恢复 `arch/symbol-iter-token-arith-expectation-sync`。
- 已从主仓当前只读 `expectation/` 基线恢复完整合同树到 sync worktree，再仅重建白名单合同同步。

### 当前白名单 sync diff scope

相对主仓 `/home/lfr/kernelcode_generate/expectation`，排除 `__pycache__` 后当前仅以下文件不同：

- `expectation/operation/arch/get_block_id.py`
- `expectation/operation/arch/get_block_num.py`
- `expectation/operation/arch/get_dynamic_memory.py`
- `expectation/operation/arch/get_subthread_id.py`
- `expectation/operation/arch/get_subthread_num.py`
- `expectation/operation/arch/get_thread_id.py`
- `expectation/operation/arch/get_thread_num.py`
- `expectation/operation/arch/launch_kernel.py`
- `expectation/dsl/mlir_gen/dialect/nn/activation/leaky_relu.py`
- `expectation/dsl/mlir_gen/dialect/nn/activation/hard_sigmoid.py`
- `expectation/dsl/mlir_gen/dialect/nn/conv.py`
- `expectation/dsl/mlir_gen/dialect/nn/fc.py`
- `expectation/tools/dsl_run/invalid_contract.py`
- `expectation/tools/dsl_cost_run/invalid_contract.py`
- `expectation/pass/tuning/launch_kernel_cost_func/basic_all.py`
- `expectation/pass/tuning/launch_kernel_cost_func/multi_kind.py`
- `expectation/pass/tuning/launch_kernel_cost_func/shared_callee_once.py`

### 单项验证

固定环境均使用：

```bash
PYTHONDONTWRITEBYTECODE=1 \
EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith \
PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith:/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith-expectation-sync:/home/lfr/kernelcode_generate
```

已通过单项：

- `python3 -m expectation.operation.arch`：`exit=0`
- `python3 -m expectation.dsl.mlir_gen.dialect.nn.activation.leaky_relu`：`exit=0`
- `python3 -m expectation.dsl.mlir_gen.dialect.nn.activation.hard_sigmoid`：`exit=0`
- `python3 -m expectation.dsl.mlir_gen.dialect.nn.fc`：`exit=0`
- `python3 -m expectation.dsl.mlir_gen.dialect.nn.conv`：`exit=0`
- `python3 -m expectation.tools.dsl_run.invalid_contract`：`exit=0`
- `python3 -m expectation.tools.dsl_cost_run.invalid_contract`：`exit=0`
- `python3 -m expectation.pass.tuning.launch_kernel_cost_func`：`exit=0`

### Full expectation smoke

命令：

```bash
PYTHONDONTWRITEBYTECODE=1 \
OMP_NUM_THREADS=1 \
OPENBLAS_NUM_THREADS=1 \
MKL_NUM_THREADS=1 \
NUMEXPR_NUM_THREADS=1 \
EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith \
PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith:/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith-expectation-sync:/home/lfr/kernelcode_generate \
python3 -m expectation
```

结果：`exit=1`，日志 `/tmp/t20260512_full_expectation_restored_sync_1.log`。

该失败不再是 sync 路径缺失或 `expectation.utils` / `expectation.dialect` 缺包问题；当前失败矩阵包含更广泛的旧合同不一致，超过本次“恢复唯一 sync 落点 + 白名单 sync”动作可裁定范围。没有 fixed full expectation `3/3 exit=0` 前，仍不得 review 通过、不得终验、不得 merge。

## 架构同步补录（2026-05-14，大闸蟹）

### 用户授权

- 用户榕已确认：不回退当前公开 `spec` / 实现合同，继续授权架构侧对剩余 9 项做极窄 `expectation` sync。
- 授权 scope 仅限：
  - `expectation/pass/lowing/nn_lowering/element_binary/{add.py,div.py,mul.py,sub.py,truediv.py}` 的 dynamic case。
  - `expectation/pass/lowing/nn_lowering/img2col/{img2col1d.py,img2col2d.py}` 的 dynamic case。
  - `expectation/pass/tile/analysis/broadcast.py` 的 `tiled_dynamic` case。
  - `expectation/tools/dsl_run/invalid_contract.py` 的 case6。
- 本次同步不得扩到其它 `expectation`，不得要求 execute 回退公开合同或恢复旧错误短语。

### 本次同步内容

- `element_binary` 五个文件：
  - 将 dynamic `memory + (const + symbol)` case 的结果类型从旧 `1 + S` 文本同步为当前 `SymbolExprAttr` canonical `S + 1`。
  - 不改变输入 IR 的公开语义，只同步 CHECK 文本。
- `img2col1d.py` / `img2col2d.py`：
  - dynamic case 继续使用完整输入 IR。
  - 将旧长 CHECK 文本收敛为公开 lowering 结构合同：`dma.alloc + kernel.img2col* + func.return`，避免把当前 canonical 表达式打印顺序误当合同。
- `broadcast.py`：
  - `tiled_dynamic` case 继续使用完整输入 IR。
  - 将旧长 CHECK 文本收敛为公开结构合同：`symbol.for + dma.broadcast + tile.analysis/tile.tile_exprs`，具体属性由现有 Python 断言继续校验。
- `invalid_contract.py`：
  - case6 继续锁定当前公开错误短语 `Unsupported call expression`，未恢复旧 `DslRunUnsupportedRealArg`。

### 单项验收

固定环境：

```bash
PYTHONDONTWRITEBYTECODE=1 \
EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith \
PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith:/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith-expectation-sync:/home/lfr/kernelcode_generate
```

通过命令：

- `python3 -m expectation.pass.lowing.nn_lowering.element_binary.add`
- `python3 -m expectation.pass.lowing.nn_lowering.element_binary.div`
- `python3 -m expectation.pass.lowing.nn_lowering.element_binary.mul`
- `python3 -m expectation.pass.lowing.nn_lowering.element_binary.sub`
- `python3 -m expectation.pass.lowing.nn_lowering.element_binary.truediv`
- `python3 -m expectation.pass.lowing.nn_lowering.img2col.img2col1d`
- `python3 -m expectation.pass.lowing.nn_lowering.img2col.img2col2d`
- `python3 -m expectation.pass.tile.analysis.broadcast`
- `python3 -m expectation.tools.dsl_run.invalid_contract`

`py_compile` 验收：

```bash
PYTHONPYCACHEPREFIX=/tmp/t20260514_sync_pycache python3 -m py_compile \
  expectation/pass/lowing/nn_lowering/element_binary/add.py \
  expectation/pass/lowing/nn_lowering/element_binary/div.py \
  expectation/pass/lowing/nn_lowering/element_binary/mul.py \
  expectation/pass/lowing/nn_lowering/element_binary/sub.py \
  expectation/pass/lowing/nn_lowering/element_binary/truediv.py \
  expectation/pass/lowing/nn_lowering/img2col/img2col1d.py \
  expectation/pass/lowing/nn_lowering/img2col/img2col2d.py \
  expectation/pass/tile/analysis/broadcast.py \
  expectation/tools/dsl_run/invalid_contract.py
```

结果：`exit=0`。

### out-of-scope 观察

- 额外运行 `python3 -m expectation.pass.lowing.nn_lowering` 时，发现 `expectation/pass/lowing/nn_lowering/transpose.py` 的 dynamic CHECK 仍按旧文本失败。
- 该文件不在本次用户授权 scope 内，本次未修改。
- 若 fixed full expectation 后续仍暴露该 out-of-scope 红点，应回用户/架构追加极窄授权；不得由 execute/review/admin 越权修改。

## 架构同步补录（2026-05-14，守护最好的爱莉希雅）

### 用户裁定

- `expectation.tools.dsl_run.invalid_contract` case6 继续按当前 actual 极窄同步，稳定错误短语为 `DslRunUnsupportedRealArg: real_args only supports torch.Tensor and numpy.ndarray`。
- 本次只授权架构侧在唯一 sync 落点修改 case6 对应断言 / 说明；不改产品 `dsl_run` 实现，不回退 `Unsupported call expression`。
- 授权架构侧极窄修正 `expectation/utils/suite_runner.py` 的验证现场路径编排，避免以 case 文件路径作为 `argv[0]` 导致 case 目录进入 `sys.path[0]` 并遮蔽 stdlib。
- runner 边界：不改变 case discovery 语义，不扩展 expectation 合同，不改产品实现；子进程继续使用 `python -m <module_name>`，由固定 `PYTHONPATH` 保证 execute worktree 代码优先、sync expectation 次之、主仓合同资产兜底。

### 本次落位

- `expectation/tools/dsl_run/invalid_contract.py`：
  - case6 期望错误短语从 `Unsupported call expression` 同步为 `DslRunUnsupportedRealArg: real_args only supports torch.Tensor and numpy.ndarray`。
- `expectation/utils/suite_runner.py`：
  - `_run_case_module(...)` 统一使用 `python -m <module_name>` 运行 case 子进程。
  - 删除以同步 case 文件路径直接作为 `argv[0]` 的执行路径，避免 `expectation/.../operation/copy.py` 等 case 目录遮蔽 stdlib `copy`。
  - 保留 `_subprocess_env(...)` 的 fixed `PYTHONPATH` 编排：`worktree_root` 在前，调用方 `PYTHONPATH` 中的 sync worktree 与主仓路径按顺序保留。

### 验证

执行目录：`/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith`。

固定环境：

```bash
EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith \
OMP_NUM_THREADS=1 \
OPENBLAS_NUM_THREADS=1 \
MKL_NUM_THREADS=1 \
NUMEXPR_NUM_THREADS=1 \
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith:/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith-expectation-sync:/home/lfr/kernelcode_generate
```

通过命令：

- `python3 -m expectation.tools.dsl_run.invalid_contract` -> `exit=0`；case6 actual 为 `DslRunUnsupportedRealArg: real_args only supports torch.Tensor and numpy.ndarray`。
- `python3 -m expectation.operation.dma.copy` -> `exit=0`。
- `python3 -m expectation.operation.dma` -> `exit=0`；覆盖包含 `copy.py` 的 package runner，未再触发 stdlib `copy` 遮蔽问题。
- `PYTHONPYCACHEPREFIX=/tmp/t20260514_symbol_iter_sync_pycache python3 -m py_compile expectation/tools/dsl_run/invalid_contract.py expectation/utils/suite_runner.py` -> `exit=0`。

### 结论

- 本次架构侧已按用户裁定完成 `case6` 与 runner 验证现场路径编排的极窄同步。
- 未修改产品实现，未改变 case discovery 语义，未扩大 expectation 合同。
- fixed full expectation `3/3 exit=0` 仍由 execute 在原任务 worktree 复跑；未达到前不得 review / merge。

## 架构复核补录（2026-05-14，大闸蟹）

### 复核口径

- 接受用户对 `case6` 的最新裁定：`expectation.tools.dsl_run.invalid_contract` case6 固定为 `DslRunUnsupportedRealArg: real_args only supports torch.Tensor and numpy.ndarray`。
- `suite_runner` 路径编排按极窄授权处理：case 子进程必须以 `python -m <module_name>` 运行，不得以 case 文件路径作为 `argv[0]`，避免 case 目录进入 `sys.path[0]` 遮蔽 stdlib。
- 本次复核不授权普通 execute / review / admin 修改 expectation；同步落点仍为唯一 sync worktree。

### 验证结果

执行目录：`/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith-expectation-sync`。

固定命令：

```bash
PYTHONDONTWRITEBYTECODE=1 \
EXPECTATION_WORKTREE_ROOT=/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith \
PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith:/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith-expectation-sync:/home/lfr/kernelcode_generate \
python3 -m expectation
```

结果：`exit=0`，日志：`/tmp/t20260512_arch_full_expectation_after_runner_fix.log`。

补充验证：

- `python3 -m expectation.tools.dsl_run.invalid_contract` 在待验 worktree `cwd` 下 `exit=0`，case6 actual 为 `DslRunUnsupportedRealArg: real_args only supports torch.Tensor and numpy.ndarray`。
- 通过固定 `PYTHONPATH` 导入的 `expectation.utils.suite_runner` 来自 `/home/lfr/kernelcode_generate/wt-20260512-symbol-iter-token-arith-expectation-sync/expectation/utils/suite_runner.py`。
- `_run_case_module("expectation.tools.dsl_run.invalid_contract", repo_root)` 以 suite runner 子进程路径执行 `exit=0`，确认不再按 case 文件路径执行。

### 结论

- `case6` 合同同步与 runner 路径污染修正已在架构侧复核通过。
- 我侧只完成单轮 fixed full expectation smoke；计划要求的 `3/3 exit=0` 仍由 execute 按同一固定命令复跑并写回原任务记录。
- 若 execute 后续出现新非授权红点，应继续回用户 / 架构裁定，不得由普通角色扩大 expectation 修改范围。
