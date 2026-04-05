# buffer_results_to_out_params_refactor_alignment_plan.md

## 进度

| 编号 | 依赖 | worktree | 记录文件 | 进度 |
| --- | --- | --- | --- | --- |
| `S1` | `无` | `wt-20260405-buffer-outparams-s1` | `20260405-buffer-outparams-s1.md` | `spec完成（T-20260405-48cff778，睡觉小分队）；复审通过（T-20260405-c87af310，不要啊教练）；实现+补测完成（T-20260405-ba1e5ef0，金铲铲大作战）；复审不通过（T-20260405-a45bc31b，不要啊教练；原因：worktree 内 expectation gate 路径缺失 exit=2）；修复完成（T-20260405-2e17c4ed，jcc你莫辜负：同步 expectation 脚本到 worktree 并复跑 callsite_rewrite.py exit=0）；复审通过（T-20260405-5857763e，不要啊教练）；已合并（commit de60e2e，T-20260405-d19748db，李白；gate exit=0）。` |
| `S2` | `S1` | `wt-20260405-buffer-outparams-s2` | `20260405-buffer-outparams-s2.md` | `实现+补测完成（T-20260405-85d7587c，jcc你莫辜负）；复审通过（T-20260405-63fb92a0，提莫炖蘑菇；gate exit=0）；已合并（commit 473e7ca，T-20260405-1e6486fe，李白；gate exit=0）。` |
| `S3` | `S1` | `wt-20260405-buffer-outparams-s3` | `20260405-buffer-outparams-s3.md` | `实现+补测完成（T-20260405-facb8a3a，jcc你莫辜负；gate exit=0）；复审通过（T-20260405-067b8e28，提莫炖蘑菇；gate exit=0）；已合并（commit 286f731，T-20260405-2051b5f2，李白；gate exit=0）。` |
| `S4` | `S2、S3` | `wt-20260405-buffer-outparams-s4` | `20260405-buffer-outparams-s4.md` | `已建任务并分发（T-20260405-6d72d4aa，jcc你莫辜负）：补齐 external declaration / multi-block / return arity / callsite mismatch / half-rewritten 的正式 expectation 合同与下游门禁。` |
| `S5` | `S4` | `wt-20260405-buffer-outparams-s5` | `20260405-buffer-outparams-s5.md` | `已合并（commit c9c0f8b，T-20260405-e4108848，李白；gate exit=0）。` |
| `S6` | `S5` | `.` | `不要求` | `已合并（commit 8f621ba，T-20260405-19d6ac20，李白；gate exit=0）。` |

## 功能说明

- 本计划用于重构 [`spec/pass/lowering/buffer_results_to_out_params.md`](/home/lfr/kernelcode_generate/spec/pass/lowering/buffer_results_to_out_params.md) 对应的公开合同、实现结构以及 pass expectation。
- 当前真实问题不是“功能完全不可用”，而是“`spec / 实现注释 / expectation 组织 / 下游 gate` 之间口径不完全一致”：
  - `spec` 仍把多结果、`memory + scalar` mixed returns、`gen_kernel` 闭环写成“本轮不要求”。
  - 当前实现和测试实际上已经支持上述能力。
  - expectation 目前能跑通，但偏“场景脚本”，还缺一组专门的边界/拒绝路径 expectation 来定义长期合同。
- 本计划的目标不是扩大到通用 function-boundary bufferization，而是把当前仓库已经公开或实际依赖的 `buffer-results-to-out-params` 语义收口成可维护的正式合同。
- 本文件只给计划，不直接修改实现。
- 分工约束补充如下：
  - 任务默认按 `spec任务` 分发，但执行时允许联动修改 `spec / 功能实现 / test`，不能机械理解成“只改 spec”。
  - 每个 `spec任务` 都是同一条任务链的起点，任务书必须覆盖其后的 `实现/重构 -> 审查（含复审） -> 合并`，而不是只写 spec 阶段。
  - `大闸蟹` 只在整个计划全部任务完成并合并后，进行统一的架构师验收；不对单个 `S*` 任务逐个验收。
  - `expectation/**` 文件不外部分发；expectation 的新增、整合、删除、边界收口统一由 `大闸蟹` 负责。

## 范围与非目标

### 范围

- `spec`
  - [`spec/pass/lowering/buffer_results_to_out_params.md`](/home/lfr/kernelcode_generate/spec/pass/lowering/buffer_results_to_out_params.md)
  - [`spec/pass/pass_manager.md`](/home/lfr/kernelcode_generate/spec/pass/pass_manager.md)
  - [`spec/dsl/gen_kernel.md`](/home/lfr/kernelcode_generate/spec/dsl/gen_kernel.md)
- `功能实现`
  - [`kernel_gen/passes/lowering/buffer_results_to_out_params.py`](/home/lfr/kernelcode_generate/kernel_gen/passes/lowering/buffer_results_to_out_params.py)
  - [`kernel_gen/passes/lowering/__init__.py`](/home/lfr/kernelcode_generate/kernel_gen/passes/lowering/__init__.py)
  - [`kernel_gen/passes/pass_manager.py`](/home/lfr/kernelcode_generate/kernel_gen/passes/pass_manager.py)
  - [`kernel_gen/dsl/gen_kernel.py`](/home/lfr/kernelcode_generate/kernel_gen/dsl/gen_kernel.py)
- `expectation`
  - [`expectation/pass/lowing/buffer_results_to_out_params/callsite_rewrite.py`](/home/lfr/kernelcode_generate/expectation/pass/lowing/buffer_results_to_out_params/callsite_rewrite.py)
  - [`expectation/pass/lowing/buffer_results_to_out_params/multi_output.py`](/home/lfr/kernelcode_generate/expectation/pass/lowing/buffer_results_to_out_params/multi_output.py)
  - [`expectation/pass/lowing/buffer_results_to_out_params/mixed_output.py`](/home/lfr/kernelcode_generate/expectation/pass/lowing/buffer_results_to_out_params/mixed_output.py)
  - 允许新增：`expectation/pass/lowing/buffer_results_to_out_params/boundary.py`
  - 若为减少重复有必要，允许新增：`expectation/utils/pass_buffer_results_to_out_params.py`
- `test`
  - [`test/pass/test_buffer_results_to_out_params.py`](/home/lfr/kernelcode_generate/test/pass/test_buffer_results_to_out_params.py)
  - [`test/dsl/test_gen_kernel.py`](/home/lfr/kernelcode_generate/test/dsl/test_gen_kernel.py)
  - [`test/pass/test_pass_manager.py`](/home/lfr/kernelcode_generate/test/pass/test_pass_manager.py)

### 非目标

- 不扩展到通用跨模块、跨文件、不可解析 symbol 的 `func.call` 改写。
- 不把 `buffer-results-to-out-params` 升级成完整 MLIR 通用 bufferization 框架。
- 不在本轮支持多 block / CFG 分支 / loop-carried buffer result 改写。
- 不通过删除现有 expectation 或放弱断言来“伪对齐”。
- 不改 `dsl/emit_c` 和不相关 pass。

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`大闸蟹`
- `文档`：[`ARCHITECTURE/plan/buffer_results_to_out_params_refactor_alignment_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/buffer_results_to_out_params_refactor_alignment_plan.md)
- `spec`：
  - [`spec/pass/lowering/buffer_results_to_out_params.md`](/home/lfr/kernelcode_generate/spec/pass/lowering/buffer_results_to_out_params.md)
  - [`spec/pass/pass_manager.md`](/home/lfr/kernelcode_generate/spec/pass/pass_manager.md)
  - [`spec/dsl/gen_kernel.md`](/home/lfr/kernelcode_generate/spec/dsl/gen_kernel.md)
- `功能实现`：
  - [`kernel_gen/passes/lowering/buffer_results_to_out_params.py`](/home/lfr/kernelcode_generate/kernel_gen/passes/lowering/buffer_results_to_out_params.py)
  - [`kernel_gen/passes/pass_manager.py`](/home/lfr/kernelcode_generate/kernel_gen/passes/pass_manager.py)
  - [`kernel_gen/dsl/gen_kernel.py`](/home/lfr/kernelcode_generate/kernel_gen/dsl/gen_kernel.py)
- `test`：
  - [`test/pass/test_buffer_results_to_out_params.py`](/home/lfr/kernelcode_generate/test/pass/test_buffer_results_to_out_params.py)
  - [`test/dsl/test_gen_kernel.py`](/home/lfr/kernelcode_generate/test/dsl/test_gen_kernel.py)
  - [`test/pass/test_pass_manager.py`](/home/lfr/kernelcode_generate/test/pass/test_pass_manager.py)

## 外部参考

- 仅作语义校准，不替代仓库内 spec：
  - MLIR Bufferization：<https://mlir.llvm.org/docs/Bufferization/>
  - 重点关注：
    - `Destination-Passing Style`
    - `function boundary` 相关约束
- 这些资料说明了“buffer 结果转显式 out 参数”和“调用点同步改写”属于函数边界 bufferization 的常见做法；但本仓库仍应以自身 `nn.memory`、`dma.alloc`、`gen_kernel` 口径为准。

## 当前实测状态

### 基线命令

```bash
pytest -q test/pass/test_buffer_results_to_out_params.py
for f in expectation/pass/lowing/buffer_results_to_out_params/*.py; do
  PYTHONPATH=. python "$f"
done
pytest -q test/dsl/test_gen_kernel.py -k 'buffer_results_to_out_params or half_rewritten'
pytest -q test/pass/test_pass_manager.py -k 'buffer_results_to_out_params'
```

### 当前结果（2026-04-05）

- `pytest -q test/pass/test_buffer_results_to_out_params.py`：`7 passed`
- `expectation/pass/lowing/buffer_results_to_out_params/*.py`：`全部通过`
- `pytest -q test/dsl/test_gen_kernel.py -k 'buffer_results_to_out_params or half_rewritten'`：`4 passed`
- `pytest -q test/pass/test_pass_manager.py -k 'buffer_results_to_out_params'`：`2 passed`

### 当前真实缺口

| 层级 | 当前状态 | 真实缺口 |
| --- | --- | --- |
| `spec` | `滞后` | 仍把多 output、mixed output、`gen_kernel` 闭环写成“本轮不要求” |
| `实现` | `可用` | 主流程已支持 single / multi / mixed / callsite rewrite，但内部注释与 helper 口径不完全一致 |
| `expectation` | `通过` | 已覆盖主路径，但还缺独立的失败边界 expectation；重复 helper 也偏多 |
| `test` | `通过` | 用例齐，但 feature id / spec 公开口径需要补齐 |

### 现状判断

- 当前仓库已经把下面这些能力实质性暴露为公开行为：
  - 单个 `memory` 返回值改写成前置 `arg0`
  - 多个 `memory` 返回值改写成前置 `arg0 / arg1 / ...`
  - `memory + scalar` mixed returns：memory 变 out param，scalar 继续保留返回
  - 模块内可解析 `func.call` 同步改写成“caller 显式 out 实参 + 新 call 保留 scalar results”
  - `gen_kernel` 对 rewrite 后 ABI 的成功闭环，以及对 half-rewritten ABI 的显式拒绝
- 因此本轮重构重点不是“补功能可用性”，而是“把现有真实能力固化成统一合同，并补齐拒绝路径 expectation”。

## 重构原则

- expectation 先定义合同边界，再驱动实现；不依赖当前实现细节写死内部 helper 行为。
- expectation 的维护权固定在 `大闸蟹`，其他执行人只按 spec / 实现 / test 推进，不直接改 expectation 文件。
- 计划里的每个 `S*` 任务块都按“单任务链”维护：`spec -> 实现/重构 -> 审查（含复审） -> 合并`。
- 管理员推进时不得把“后续实现/审查”从任务书中省略；只要 `READY_IF` 满足，就应沿同一任务链继续推进下一阶段。
- 支持路径必须通过公开入口证明：
  - pass：经 `BufferResultsToOutParamsPass().run(module)`
  - 黑盒链路：经 `build_func_op(...) -> LowerNnToKernelPass -> BufferResultsToOutParamsPass -> gen_kernel(...)`
- 失败路径必须锁定失败层级，不允许“任意报错都算过”：
  - `BufferResultsToOutParamsError`
  - `GenKernelError`
  - 关键短语至少锁一个
- 同一类 ABI 合同尽量合并 expectation，减少重复 helper 和样板代码。

## 完成定义

- `spec / 实现 / expectation / test` 四层公开口径一致。
- 每个 `S*` 任务都完成完整阶段链：`spec完成`、`实现完成`、`审查完成`、`已合并`。
- 仅当全部 `S*` 任务都已合并后，整个计划才进入 `待架构师验收`。
- 现有四组 gate 持续通过：

```bash
pytest -q test/pass/test_buffer_results_to_out_params.py
for f in expectation/pass/lowing/buffer_results_to_out_params/*.py; do
  PYTHONPATH=. python "$f"
done
pytest -q test/dsl/test_gen_kernel.py -k 'buffer_results_to_out_params or half_rewritten'
pytest -q test/pass/test_pass_manager.py -k 'buffer_results_to_out_params'
```

- expectation 结构按“合同族”而不是“零散脚本”组织，至少收口为：
  - `abi_contract.py` 或等价 grouped expectation：single / multi / mixed ABI
  - `callsite_rewrite.py`：黑盒链路 + `gen_kernel` 闭环
  - `boundary.py`：external declaration / multi-block / return-output arity mismatch / half-rewritten or callsite mismatch 等拒绝路径
- `spec` 正式写明当前支持和明确不支持的边界，不能再出现“实现已支持，spec 却写未支持”的双口径。

## 计划任务

### `S1`

- `任务类型`：`spec任务（允许联动 spec / test / 实现；不分发 expectation 修改）`
- `阶段链路`：`spec -> 实现/重构 -> 审查（含复审） -> 合并`
- `目标`：把 [`spec/pass/lowering/buffer_results_to_out_params.md`](/home/lfr/kernelcode_generate/spec/pass/lowering/buffer_results_to_out_params.md) 改写成与当前真实行为一致的正式合同。
- `需要收口的合同`：
  - single memory result
  - multiple memory results 的固定前置顺序
  - mixed `memory + scalar` returns
  - 模块内可解析 `func.call` 的 caller/callee 同步改写
  - `gen_kernel` 闭环和 half-rewritten ABI 的显式拒绝
  - 仍明确不支持：external declaration、multi-block、返回值个数和函数签名不一致
- `代码示例`：

```text
func.func @single(%src: !nn.memory<...>) -> (!nn.memory<...>) {
  ...
  func.return %0
}
```

```text
func.func @single(%arg0: !nn.memory<...>, %src: !nn.memory<...>) {
  ...
  func.return
}
```

```text
%out0 = dma.alloc ...
%flag = func.call @mixed(%out0, %src, %cond) : (...) -> i1
```

- `可改文件`：
  - [`spec/pass/lowering/buffer_results_to_out_params.md`](/home/lfr/kernelcode_generate/spec/pass/lowering/buffer_results_to_out_params.md)
  - [`spec/pass/pass_manager.md`](/home/lfr/kernelcode_generate/spec/pass/pass_manager.md)
  - [`spec/dsl/gen_kernel.md`](/home/lfr/kernelcode_generate/spec/dsl/gen_kernel.md)
- `验收标准`：
  - `spec` 不再把 multi / mixed / `gen_kernel` 写成“本轮不要求”
  - feature id 至少覆盖：single、external reject、callsite rewrite、pipeline order、multi-output、mixed-output、half-rewritten reject
  - 支持与不支持边界分层明确

### `S2`

- `任务类型`：`spec任务（实现重构子任务）`
- `阶段链路`：`spec -> 实现/重构 -> 审查（含复审） -> 合并`
- `目标`：重构 [`kernel_gen/passes/lowering/buffer_results_to_out_params.py`](/home/lfr/kernelcode_generate/kernel_gen/passes/lowering/buffer_results_to_out_params.py) 的内部结构，让“校验 / callsite rewrite / callee rewrite”三层职责更机械。
- `建议重构点`：
  - 抽取统一的 output 分解逻辑，避免 memory/scalar 分类在多个 helper 中重复出现
  - 让 `_validate_candidate(...)`、`_rewrite_callsite(...)`、`_rewrite_memory_results_to_out_params(...)` 的前后置条件一致
  - 修正文档注释与 helper 说明中“只支持单结果 callsite”的陈旧描述
  - 保持模块级原子失败：先收集并校验，再批量改写
- `代码示例`：

```python
targets = _collect_rewrite_targets(module)
_rewrite_callsites(module, targets)
for func_op in targets.values():
    _rewrite_memory_results_to_out_params(func_op)
```

```python
memory_indices = [0, 2]
scalar_indices = [1]
```

- `可改文件`：
  - [`kernel_gen/passes/lowering/buffer_results_to_out_params.py`](/home/lfr/kernelcode_generate/kernel_gen/passes/lowering/buffer_results_to_out_params.py)
- `验收标准`：
  - 代码结构能直接映射到 spec 的 single / multi / mixed / callsite 四类合同
  - helper 注释与真实能力一致
  - 不引入行为回退

### `S3`

- `任务类型`：`spec任务（expectation 由大闸蟹自持执行）`
- `阶段链路`：`spec -> expectation实现 -> 审查（含复审） -> 合并`
- `目标`：重组 pass expectation，按“ABI 合同族”组织，减少重复脚本和重复 helper。
- `推荐目录形态`：
  - 保留黑盒链路文件：[`expectation/pass/lowing/buffer_results_to_out_params/callsite_rewrite.py`](/home/lfr/kernelcode_generate/expectation/pass/lowing/buffer_results_to_out_params/callsite_rewrite.py)
  - 合并 `multi_output.py` + `mixed_output.py` 为 `abi_contract.py`，或同等 grouped expectation
  - 新增 [`expectation/pass/lowing/buffer_results_to_out_params/boundary.py`](/home/lfr/kernelcode_generate/expectation/pass/lowing/buffer_results_to_out_params/boundary.py)
  - 如重复明显，新增 [`expectation/utils/pass_buffer_results_to_out_params.py`](/home/lfr/kernelcode_generate/expectation/utils/pass_buffer_results_to_out_params.py)
- `必须覆盖的 case`：
  - `[CASE-1]` single memory result -> 前置 `arg0`
  - `[CASE-2]` multi outputs -> 前置 `arg0 / arg1 / ...`
  - `[CASE-3]` mixed output -> memory 前置 + scalar 保留 return
  - `[CASE-4]` caller/callee callsite rewrite 后旧 memory call result SSA 消失
- `代码示例`：

```python
assert list(func_op.function_type.inputs) == [mem_a, mem_b, original_input]
assert list(func_op.function_type.outputs) == [i1]
```

```python
assert tuple(rewritten_call.arguments) == (caller_alloc_0.result, caller_alloc_1.result, caller.args[0])
assert len(rewritten_call.results) == 1
```

- `可改文件`：
  - [`expectation/pass/lowing/buffer_results_to_out_params/callsite_rewrite.py`](/home/lfr/kernelcode_generate/expectation/pass/lowing/buffer_results_to_out_params/callsite_rewrite.py)
  - [`expectation/pass/lowing/buffer_results_to_out_params/multi_output.py`](/home/lfr/kernelcode_generate/expectation/pass/lowing/buffer_results_to_out_params/multi_output.py)
  - [`expectation/pass/lowing/buffer_results_to_out_params/mixed_output.py`](/home/lfr/kernelcode_generate/expectation/pass/lowing/buffer_results_to_out_params/mixed_output.py)
  - 允许新增：[`expectation/pass/lowing/buffer_results_to_out_params/boundary.py`](/home/lfr/kernelcode_generate/expectation/pass/lowing/buffer_results_to_out_params/boundary.py)
  - 允许新增：[`expectation/utils/pass_buffer_results_to_out_params.py`](/home/lfr/kernelcode_generate/expectation/utils/pass_buffer_results_to_out_params.py)
- `验收标准`：
  - expectation 结构比当前更少重复
  - 每个文件都有明确 `Case` 列表
  - grouped expectation 能直接映射 spec 条目

### `S4`

- `任务类型`：`spec任务（边界收口子任务）`
- `阶段链路`：`spec -> 实现/重构 -> 审查（含复审） -> 合并`
- `目标`：把当前仅在 unit test 中存在、但 expectation 未正式承载的失败边界补成独立 expectation 合同。
- `必须补的边界`：
  - external declaration -> `BufferResultsToOutParamsError`
  - multi-block function -> `BufferResultsToOutParamsError`
  - `func.return` 参数个数与 `function_type.outputs` 不一致 -> `BufferResultsToOutParamsError`
  - callsite result 个数和 callee outputs 不一致 -> `BufferResultsToOutParamsError`
  - half-rewritten ABI -> `GenKernelError`
- `代码示例`：

```python
with pytest.raises(BufferResultsToOutParamsError, match="external declaration"):
    BufferResultsToOutParamsPass().run(module)
```

```python
with pytest.raises(GenKernelError, match="legacy memory return ABI is not supported"):
    gen_kernel(func_op, ctx)
```

- `可改文件`：
  - [`expectation/pass/lowing/buffer_results_to_out_params/boundary.py`](/home/lfr/kernelcode_generate/expectation/pass/lowing/buffer_results_to_out_params/boundary.py)
  - [`test/pass/test_buffer_results_to_out_params.py`](/home/lfr/kernelcode_generate/test/pass/test_buffer_results_to_out_params.py)
  - [`test/dsl/test_gen_kernel.py`](/home/lfr/kernelcode_generate/test/dsl/test_gen_kernel.py)
- `验收标准`：
  - expectation 不再只验证正例
  - 每个失败边界都锁定错误类型或关键短语之一
  - 不允许 fallback、半改写、或静默保留旧 ABI

### `S5`

- `任务类型`：`spec任务（下游联动子任务）`
- `阶段链路`：`spec -> 实现/重构 -> 审查（含复审） -> 合并`
- `目标`：统一 `pass_manager` 与 `gen_kernel` 的下游合同，避免“pass 已改 ABI、下游仍接受旧 ABI”或“顺序错了仍侥幸通过”。
- `需要锁定的内容`：
  - `LowerNnToKernelPass -> BufferResultsToOutParamsPass` 的固定顺序
  - `gen_kernel` 只接受 rewrite 后 ABI
  - mixed output 下 caller 只保留 scalar result，memory result 不再经 call result 传递
- `代码示例`：

```python
pm.add_pass(LowerNnToKernelPass())
pm.add_pass(BufferResultsToOutParamsPass())
```

```python
with pytest.raises(ValueError, match="lowered IR"):
    pm.run(module)
```

- `可改文件`：
  - [`test/pass/test_pass_manager.py`](/home/lfr/kernelcode_generate/test/pass/test_pass_manager.py)
  - [`test/dsl/test_gen_kernel.py`](/home/lfr/kernelcode_generate/test/dsl/test_gen_kernel.py)
  - [`spec/pass/pass_manager.md`](/home/lfr/kernelcode_generate/spec/pass/pass_manager.md)
- `验收标准`：
  - 顺序错误必须失败
  - rewrite 后 ABI 闭环继续通过
  - old ABI 不被下游接受

### `S6`

- `任务类型`：`spec任务（最终收口子任务）`
- `阶段链路`：`spec -> 实现/重构 -> 审查（含复审） -> 合并`
- `目标`：完成最终绿灯和文档回填，确保重构不是“代码过了、合同没跟上”。
- `执行命令`：

```bash
pytest -q test/pass/test_buffer_results_to_out_params.py
for f in expectation/pass/lowing/buffer_results_to_out_params/*.py; do
  PYTHONPATH=. python "$f"
done
pytest -q test/dsl/test_gen_kernel.py -k 'buffer_results_to_out_params or half_rewritten'
pytest -q test/pass/test_pass_manager.py -k 'buffer_results_to_out_params'
```

- `可改文件`：
  - [`spec/pass/lowering/buffer_results_to_out_params.md`](/home/lfr/kernelcode_generate/spec/pass/lowering/buffer_results_to_out_params.md)
  - [`kernel_gen/passes/lowering/buffer_results_to_out_params.py`](/home/lfr/kernelcode_generate/kernel_gen/passes/lowering/buffer_results_to_out_params.py)
  - [`expectation/pass/lowing/buffer_results_to_out_params/callsite_rewrite.py`](/home/lfr/kernelcode_generate/expectation/pass/lowing/buffer_results_to_out_params/callsite_rewrite.py)
  - [`expectation/pass/lowing/buffer_results_to_out_params/multi_output.py`](/home/lfr/kernelcode_generate/expectation/pass/lowing/buffer_results_to_out_params/multi_output.py)
  - [`expectation/pass/lowing/buffer_results_to_out_params/mixed_output.py`](/home/lfr/kernelcode_generate/expectation/pass/lowing/buffer_results_to_out_params/mixed_output.py)
  - 新增文件如 `boundary.py` / `abi_contract.py` / `expectation/utils/pass_buffer_results_to_out_params.py`
- `验收标准`：
  - 所有 gate 通过
  - `spec / 实现 / expectation / test` 口径一致
  - 文件结构比当前更少重复、更容易扩展新 case

## 建议优先级

- 先做 `S1`，因为当前最大缺口是 `spec` 落后于真实能力。
- 再并行推进 `S2` 与 `S3`：
  - `S2` 由执行人收实现结构
  - `S3` 由 `大闸蟹` 收 expectation 组织
- 最后做 `S4-S6` 统一边界、下游和 gate。
