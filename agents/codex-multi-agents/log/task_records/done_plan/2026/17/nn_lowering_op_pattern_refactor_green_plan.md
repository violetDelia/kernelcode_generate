# nn_lowering_op_pattern_refactor_green_plan.md

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`大闸蟹`
- 目标 `spec`：
  - [`spec/pass/lowering/nn_lowering/spec.md`](../../spec/pass/lowering/nn_lowering/spec.md)
  - [`spec/pass/lowering/nn_lowering/element_binary_lowering.md`](../../spec/pass/lowering/nn_lowering/element_binary_lowering.md)
  - [`spec/pass/lowering/nn_lowering/select_cast_lowering.md`](../../spec/pass/lowering/nn_lowering/select_cast_lowering.md)
  - [`spec/pass/lowering/nn_lowering/dma_structured_lowering.md`](../../spec/pass/lowering/nn_lowering/dma_structured_lowering.md)
  - [`spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md`](../../spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md)
  - [`spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md`](../../spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md)
  - [`spec/pass/lowering/nn_lowering/nn_lowering_utility.md`](../../spec/pass/lowering/nn_lowering/nn_lowering_utility.md)
- 目标 `API`：
  - [`kernel_gen/passes/lowering/nn_lowering/__init__.py`](../../kernel_gen/passes/lowering/nn_lowering/__init__.py)
  - [`kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
  - [`kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py)
  - [`kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py)
  - [`kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py)
  - [`kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py)
  - [`kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py)
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
  - [`kernel_gen/passes/pass_manager.py`](../../kernel_gen/passes/pass_manager.py)
- 目标 `test`：
  - [`test/pass/nn_lowering`](../../test/pass/nn_lowering)
  - [`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)
  - [`test/pass/test_pipeline_default_lowering.py`](../../test/pass/test_pipeline_default_lowering.py)
  - [`test/pass/test_pipeline_npu_demo_lowering.py`](../../test/pass/test_pipeline_npu_demo_lowering.py)
- 目标 `验收资产`：
  - [`expectation/pass/lowing/nn_lowering`](../../expectation/pass/lowing/nn_lowering)
  - `python3 -m expectation.pass.lowing.nn_lowering`
  - `pytest -q test/pass/nn_lowering`
- 目标 `功能实现`：
  - [`kernel_gen/passes/lowering/nn_lowering`](../../kernel_gen/passes/lowering/nn_lowering)

## 任务清单

| 任务 | TODO 任务 ID | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- | --- |
| `S1` | `T-20260421-df8cc06e` | `无` | [`wt-20260421-nn-lowering-pattern-driver-s1`](../../wt-20260421-nn-lowering-pattern-driver-s1) | [`agents/codex-multi-agents/log/task_records/2026/16/20260421-nn-lowering-pattern-driver-s1.md`](../../agents/codex-multi-agents/log/task_records/2026/16/20260421-nn-lowering-pattern-driver-s1.md) |
| `S2` | `T-20260421-a334fc82` | `T-20260421-df8cc06e` | [`wt-20260421-nn-lowering-elementwise-patterns-s2`](../../wt-20260421-nn-lowering-elementwise-patterns-s2) | [`agents/codex-multi-agents/log/task_records/2026/16/20260421-nn-lowering-elementwise-patterns-s2.md`](../../agents/codex-multi-agents/log/task_records/2026/16/20260421-nn-lowering-elementwise-patterns-s2.md) |
| `S3` | `T-20260421-d2d31351` | `T-20260421-df8cc06e` | [`wt-20260421-nn-lowering-structured-patterns-s3`](../../wt-20260421-nn-lowering-structured-patterns-s3) | [`agents/codex-multi-agents/log/task_records/2026/16/20260421-nn-lowering-structured-patterns-s3.md`](../../agents/codex-multi-agents/log/task_records/2026/16/20260421-nn-lowering-structured-patterns-s3.md) |
| `S4` | `T-20260421-6e366827` | `T-20260421-a334fc82, T-20260421-d2d31351` | [`wt-20260421-nn-lowering-reduce-boundary-patterns-s4`](../../wt-20260421-nn-lowering-reduce-boundary-patterns-s4) | [`agents/codex-multi-agents/log/task_records/2026/16/20260421-nn-lowering-reduce-boundary-patterns-s4.md`](../../agents/codex-multi-agents/log/task_records/2026/16/20260421-nn-lowering-reduce-boundary-patterns-s4.md) |

## 评审摘要

- 评审结论：`通过`
- 评审人：`大闸蟹`、`守护最好的爱莉希雅`
- 结论摘要：`每个受支持 nn op 对应一个 RewritePattern + @op_type_rewrite_pattern 的范围清楚，范围以当前 lower-nn 支持集为准；未纳入的 nn.floordiv / relu / sigmoid 等继续走 unsupported reject 边界。S1-S4 拆分和依赖合理：先收 driver，再并行收 elementwise 与 structured，最后收 exp/reduce/softmax 边界并跑全链路。本轮不扩 op 语义、不改公开 pass 名、不新增 pipeline，只做 nn_lowering 内部 pattern 化；helper 可复用，但主路径不再保留通用 op 名称分发。`

## 终验 / 复验 / 修复复核记录

- 结论人：`大闸蟹`
- 结论：`通过`
- 验证基线：`执行目录=/home/lfr/kernelcode_generate；已执行 git fetch origin main；git merge --ff-only origin/main 返回 Already up to date；HEAD_REF=refs/heads/main，main=origin/main=180b2c92a030cbdc7b6bf4cc10b7b4645ea06df6`
- 最小阻断项或通过摘要：`无阻断项。T-20260421-6e366827 已合入最新主线；python3 -m expectation.pass.lowing.nn_lowering exit 0；pytest -q test/pass/nn_lowering 结果为 43 passed；pytest -q test/pass/test_pass_manager.py test/pass/test_pipeline_default_lowering.py test/pass/test_pipeline_npu_demo_lowering.py 结果为 28 passed。补充结构检查确认 NnLoweringPass.apply 使用 PatternRewriteWalker(GreedyRewritePatternApplier(nn_lowering_patterns(), dce_enabled=False))，未发现 _LowerNnSupportedOpPattern / _SUPPORTED_NN_OP_NAMES 主路径残留，受支持 op 已按独立 RewritePattern 组织。`
- 是否已创建修复任务：`不需要`
- 修复任务创建人：`不适用`
- 另一位架构师补充重点：`守护最好的爱莉希雅复验通过。2026-04-21 21:54:35 +0800 已在主目录 /home/lfr/kernelcode_generate 执行 git fetch origin main，并确认 HEAD=origin/main=180b2c92a030cbdc7b6bf4cc10b7b4645ea06df6；head_is_ancestor=0 且 origin_is_ancestor=0，主目录已对齐最新主线，无需改用其他远端现场。复跑 python3 -m expectation.pass.lowing.nn_lowering exit 0；pytest -q test/pass/nn_lowering 为 43 passed；pytest -q test/pass/test_pass_manager.py test/pass/test_pipeline_default_lowering.py test/pass/test_pipeline_npu_demo_lowering.py 为 28 passed。补充结构审计确认当前支持集 typed pattern：element_binary_lowering.py 11 个、select_cast_lowering.py 3 个、dma_structured_lowering.py 2 个、matmul_img2col_lowering.py 3 个、reduce_softmax_lowering.py 4 个；_LowerNnSupportedOpPattern 未残留，direct nn.softmax 仍由 NnSoftmaxOp pattern 显式拒绝。lower_*_family 兼容 helper 仍供现有 spec / 单元测试直接调用，但主 driver 已不依赖通用 family/name 分发；无最小阻断项。`

## 输入摘要

- 目标：重构 [`kernel_gen/passes/lowering/nn_lowering`](../../kernel_gen/passes/lowering/nn_lowering)，让每个受支持的 `nn.*` op 都由独立 `RewritePattern` 负责改写。
- 不做什么：不改公开 pass 名，不新增公开 pipeline，不扩展新的 `nn` op 语义，不把 `nn.softmax` 改成在 `lower-nn` 内直接 lowering。
- 当前痛点：当前主入口已经使用 `PatternRewriteWalker`，但仍存在 `_LowerNnSupportedOpPattern` 统一匹配和 `_lower_op(...)` 名称分发，review 时很难按单个 op 检查改写合同。
- 完成后用户最想看到的例子：`nn.add`、`nn.sub`、`nn.reduce_sum`、`nn.matmul` 等分别有自己的 pattern 类或 pattern 函数，并通过 `@op_type_rewrite_pattern` 匹配对应 op 类型。

## 计划目标

- 保持 `NnLoweringPass.name == "lower-nn"`、`NnLoweringPass.apply(ctx, module)`、`NnLoweringPass.run(module)` 和 `NnLoweringError` 的公开入口不变。
- 将 `nn_lowering` 内部主路径收口为：辅助函数 + 单 op `RewritePattern` 集合 + 薄 `NnLoweringPass.apply(...)` 驱动。
- `NnLoweringPass.apply(...)` 的实现必须使用 `PatternRewriteWalker(GreedyRewritePatternApplier(...))` 统一执行 pattern 集合，不允许回退到手写 block 遍历逐个调用 lowering helper。
- 移除 `_LowerNnSupportedOpPattern` 这种按名称统一兜住所有受支持 op 的主路径，避免一个 pattern 内继续做大分发。
- 现有 expectation 与 pytest 继续作为行为真源；本计划只重构组织方式，不改变 IR 输出、错误短语和受支持 op 集合。
- `nn.softmax` 继续作为“进入 lower-nn 前应先分解”的显式错误边界，不能因为 pattern 化而静默通过。

## 当前基线

- 当前公开合同：
  - [`spec/pass/lowering/nn_lowering/spec.md`](../../spec/pass/lowering/nn_lowering/spec.md) 规定 `NnLoweringPass` 是唯一公开入口，`lower-nn` 只负责 `nn -> dma/kernel` 的 op rewrite。
  - `nn.softmax` 仍要求先由上游分解；若直接进入本 pass，应抛出 `NnLoweringError`。
- 当前公开 API：
  - [`kernel_gen/passes/lowering/nn_lowering/__init__.py`](../../kernel_gen/passes/lowering/nn_lowering/__init__.py) 导出 `NnLoweringError` 与 `NnLoweringPass`。
  - [`kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/nn_lowering.py) 提供 `NnLoweringPass.apply(ctx, module)` 与兼容 `run(module)`。
- 当前实现入口：
  - `nn_lowering.py` 已引入 `GreedyRewritePatternApplier`、`PatternRewriteWalker`、`RewritePattern` 与 `@op_type_rewrite_pattern`。
  - 但主路径仍有 `_LowerNnSupportedOpPattern` 统一匹配 `_SUPPORTED_NN_OP_NAMES`，再调用 `_lower_with_current_op(...)` 和 `_lower_op(...)`。
  - `_lower_op(...)` 继续按 family/name 分发到 `element_binary`、`reduce_softmax`、`matmul_img2col`、`dma_structured` 等 helper。
  - [`select_cast_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py) 已有 `select_cast_patterns()`，是本轮可沿用的单 op pattern 方向。
- 当前测试与验收资产：
  - [`expectation/pass/lowing/nn_lowering`](../../expectation/pass/lowing/nn_lowering) 覆盖 broadcast、cast、element binary、compare、exp、img2col、matmul、reduce、select、transpose。
  - [`test/pass/nn_lowering`](../../test/pass/nn_lowering) 覆盖公开名、逐元素、比较、结构化、reduce、matmul、img2col 等路径。
- 当前缺口或失败点：
  - 现有结构不能保证“一个 op 一个 pattern”的 review 形态。
  - 受支持 op 集合、pattern 注册顺序和 unsupported `nn.*` 报错之间没有在 spec 中写清。
  - family helper 可以保留复用，但主路径不能继续依赖单个通用 pattern 加名称分发。

## 合同真源顺序

- `expectation/pass/lowing/nn_lowering > spec/pass/lowering/nn_lowering* > test/pass/nn_lowering > 当前实现`

## 方案比较与选型

- 不采用方案：继续保留 `_LowerNnSupportedOpPattern` 统一匹配所有受支持 op，再在 `_lower_op(...)` 内按名称分发。
  - 原因：虽然能跑通行为，但没有满足用户提出的“每个 op 对应一个 pattern”，也不利于单 op review。
- 不采用方案：为每个 family 只建一个 pattern，例如 `ElementBinaryPattern` 同时处理 add/sub/mul/div/compare。
  - 原因：仍然把多个 op 的行为压在同一个 pattern 内，不满足本轮架构目标。
- 采用方案：
  - 每个受支持 op 建一个独立 `RewritePattern`，`match_and_rewrite(...)` 使用 `@op_type_rewrite_pattern`，参数类型指向具体 `nn` op 类。
  - pattern 内允许调用共享 helper，例如 `lower_binary_op(...)`、`lower_reduce_op(...)`、`lower_dma_structured_op(...)`，避免复制构造逻辑。
  - 主入口只负责收集 `nn_lowering_patterns()`，再通过 `PatternRewriteWalker(GreedyRewritePatternApplier([...]))` 执行。
  - `_RejectUnsupportedNnOpPattern` 保留在最后，只处理未纳入受支持集合的 `nn.*` op。
- 最小公开接口：
  - `NnLoweringPass`
  - `NnLoweringError`
  - `build_registered_pass("lower-nn")`
  - `PassManager(["lower-nn"]).run(module)`

## 公开 API 设计

- 公开入口：`NnLoweringPass`
- 参数顺序：
  - `apply(self, ctx, module)`
  - `run(self, module)`
- 参数类型：
  - `ctx`: `xdsl.context.Context`
  - `module`: `xdsl.dialects.builtin.ModuleOp`
- 返回值：
  - `apply(...) -> None`
  - `run(...) -> ModuleOp`
- 内部 pattern 注册入口：
  - `nn_lowering_patterns() -> list[RewritePattern]`
  - family 子模块可提供 `element_binary_patterns()`、`dma_structured_patterns()`、`matmul_img2col_patterns()`、`reduce_softmax_patterns()`、`select_cast_patterns()`。
- pass 执行合同：
  - `NnLoweringPass.apply(...)` 必须通过 `PatternRewriteWalker(GreedyRewritePatternApplier(nn_lowering_patterns(), dce_enabled=False)).rewrite_module(module)` 执行。
  - `run(module)` 只作为兼容入口委托 `apply(...)`，不得单独保留另一套手写 lowering 路径。

```python
from xdsl.context import Context
from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass

ctx = Context()
lower_nn = NnLoweringPass()
lower_nn.apply(ctx, module)
```

```python
def _lower_module(module: ModuleOp) -> None:
    PatternRewriteWalker(
        GreedyRewritePatternApplier(nn_lowering_patterns(), dce_enabled=False)
    ).rewrite_module(module)
```

```python
from xdsl.pattern_rewriter import PatternRewriter, RewritePattern, op_type_rewrite_pattern
from kernel_gen.dialect.nn import NnAddOp


class LowerNnAddPattern(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: NnAddOp, rewriter: PatternRewriter, /) -> None:
        lower_element_binary_op(op, rewriter, kind="add")
```

## 完成态定义

- `NnLoweringPass` 公开入口、公开 pass 名和 registry / pass manager 调用方式保持不变。
- `NnLoweringPass.apply(...)` 的 pass 实现使用 `PatternRewriteWalker + GreedyRewritePatternApplier` 统一驱动全部 nn lowering pattern。
- `nn_lowering.py` 不再依赖 `_LowerNnSupportedOpPattern` 统一匹配全部受支持 op 作为主路径。
- 每个受支持 op 都能在对应 family 模块中找到单独 `RewritePattern`：
  - `NnAddOp`、`NnSubOp`、`NnMulOp`、`NnDivOp`、`NnTrueDivOp`
  - `NnEqOp`、`NnNeOp`、`NnLtOp`、`NnLeOp`、`NnGtOp`、`NnGeOp`
  - `NnSelectOp`、`NnCastOp`、`NnExpOp`
  - `NnBroadcastOp`、`NnTransposeOp`
  - `NnImg2col1dOp`、`NnImg2col2dOp`、`NnMatmulOp`
  - `NnReduceSumOp`、`NnReduceMinOp`、`NnReduceMaxOp`
  - `NnSoftmaxOp` 对应显式拒绝 pattern，错误短语保持当前合同。
- pattern 可共享 helper，但不得在单个 pattern 中继续处理多个 op 名称。
- 现有 expectation 和 pytest 在重构后继续通过；输出 IR 与稳定错误文本不因本轮重构改变。
- spec 写清 pattern 组织方式、注册顺序、unsupported `nn.*` 处理顺序与 `nn.softmax` 边界。

## 验收设计

- 验收资产：
  - [`expectation/pass/lowing/nn_lowering`](../../expectation/pass/lowing/nn_lowering)：锁定外部 IR 输出与错误路径。
  - [`test/pass/nn_lowering`](../../test/pass/nn_lowering)：锁定公开 pass、各 op lowering 与 family 行为。
  - `test/pass/test_pass_manager.py`、`test/pass/test_pipeline_default_lowering.py`、`test/pass/test_pipeline_npu_demo_lowering.py`：锁定 registry / pass manager / pipeline 兼容。
- 输入样例：
  - `nn.add` 输入应继续输出 `dma.alloc + kernel.binary_elewise(kind="add")`。
  - `nn.reduce_sum` 输入应继续输出 `kernel.reduce(kind="sum")`。
  - direct `nn.softmax` 输入应继续报 `nn.softmax must be decomposed before lower-nn`。
- 锁定输出：
  - 输出 IR 不再包含已受支持的 `nn.*` op。
  - 输出 op 形态、kind attr、dynamic shape operand 顺序和错误短语沿用现有 expectation。
  - 代码结构检查应能确认每个受支持 op 有独立 pattern。
- 必过命令：
  - `python3 -m expectation.pass.lowing.nn_lowering`
  - `pytest -q test/pass/nn_lowering`
  - `pytest -q test/pass/test_pass_manager.py test/pass/test_pipeline_default_lowering.py test/pass/test_pipeline_npu_demo_lowering.py`

## 阶段拆分

### S1：pattern driver 与注册骨架

#### 阶段目标

- 将 `NnLoweringPass` 主驱动收口为 pattern 集合注册与 walker 执行，并为后续 family 单 op pattern 提供统一入口。

#### 目标 spec / API

- `spec/pass/lowering/nn_lowering/spec.md`
- `公开 API：NnLoweringPass / NnLoweringError / build_registered_pass("lower-nn")`
- `内部 API：nn_lowering_patterns() -> list[RewritePattern]`

#### 禁止修改面 / 合同真源

- `禁止修改面：不改公开 pass 名，不改 expectation 输出语义，不新增公开 pipeline`
- `合同真源：expectation/pass/lowing/nn_lowering > spec/pass/lowering/nn_lowering/spec.md > test/pass/nn_lowering`

#### 预期示例代码

```python
def nn_lowering_patterns() -> list[RewritePattern]:
    return [
        *element_binary_patterns(),
        *select_cast_patterns(),
        *dma_structured_patterns(),
        *matmul_img2col_patterns(),
        *reduce_softmax_patterns(),
        RejectUnsupportedNnOpPattern(),
    ]


def _lower_module(module: ModuleOp) -> None:
    PatternRewriteWalker(
        GreedyRewritePatternApplier(nn_lowering_patterns(), dce_enabled=False)
    ).rewrite_module(module)
```

#### 预期输出

```text
build_registered_pass("lower-nn").name == "lower-nn"
NnLoweringPass().apply(ctx, module) 使用 PatternRewriteWalker + GreedyRewritePatternApplier 执行 pattern 集合
```

#### 目标验收资产

- `pytest -q test/pass/nn_lowering/public_name.py`
- `pytest -q test/pass/test_pass_manager.py`
- `pytest -q test/pass/test_pipeline_default_lowering.py test/pass/test_pipeline_npu_demo_lowering.py`

#### 验收必过项目

- `NnLoweringPass` 公开导出不变。
- registry 与 pass manager 仍能按 `lower-nn` 构造并执行。
- `_RejectUnsupportedNnOpPattern` 注册在受支持 pattern 之后。

#### 任务新建建议

- `任务类型：refactor`
- `任务目标：收口 nn_lowering pattern driver 与 registry/pass manager 兼容，不改变现有 lowering 行为。`
- `记录文件：待管理员创建（nn-lowering-pattern-driver-s1.md）`

### S2：elementwise / compare / select / cast 单 op pattern

#### 阶段目标

- 将逐元素、比较、select、cast 改成每个 op 一个 `RewritePattern`。

#### 目标 spec / API

- `spec/pass/lowering/nn_lowering/element_binary_lowering.md`
- `spec/pass/lowering/nn_lowering/select_cast_lowering.md`
- `公开 API：NnLoweringPass`
- `内部 API：element_binary_patterns() / select_cast_patterns()`

#### 禁止修改面 / 合同真源

- `禁止修改面：不改 elementwise/compare/select/cast 的 IR 输出与错误短语`
- `合同真源：expectation/pass/lowing/nn_lowering/element_binary + expectation/pass/lowing/nn_lowering/select.py + expectation/pass/lowing/nn_lowering/cast.py + expectation/pass/lowing/nn_lowering/element_compare.py`

#### 预期示例代码

```python
class LowerNnSubPattern(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: NnSubOp, rewriter: PatternRewriter, /) -> None:
        lower_element_binary_op(op, rewriter, kind="sub")
```

#### 预期输出

```text
nn.sub -> dma.alloc + kernel.binary_elewise(kind="sub")
nn.ge  -> dma.alloc + kernel.binary_elewise(kind="ge")
nn.cast -> dma.cast
```

#### 目标验收资产

- `python3 -m expectation.pass.lowing.nn_lowering.element_binary`
- `python3 -m expectation.pass.lowing.nn_lowering.select`
- `python3 -m expectation.pass.lowing.nn_lowering.cast`
- `python3 -m expectation.pass.lowing.nn_lowering.element_compare`

#### 验收必过项目

- `pytest -q test/pass/nn_lowering/element_binary_add.py test/pass/nn_lowering/element_binary_sub.py test/pass/nn_lowering/element_binary_mul.py test/pass/nn_lowering/element_binary_div.py test/pass/nn_lowering/element_binary_truediv.py`
- `pytest -q test/pass/nn_lowering/element_compare_eq.py test/pass/nn_lowering/element_compare_ne.py test/pass/nn_lowering/element_compare_lt.py test/pass/nn_lowering/element_compare_le.py test/pass/nn_lowering/element_compare_gt.py test/pass/nn_lowering/element_compare_ge.py`
- `pytest -q test/pass/nn_lowering/select.py test/pass/nn_lowering/cast.py`

#### 任务新建建议

- `任务类型：refactor`
- `任务目标：按单 op pattern 收口 elementwise/compare/select/cast，复用 helper 但不保留通用 op 名称分发。`
- `记录文件：待管理员创建（nn-lowering-elementwise-patterns-s2.md）`

### S3：broadcast / transpose / img2col / matmul 单 op pattern

#### 阶段目标

- 将结构化 memory 与 compute op 改成每个 op 一个 `RewritePattern`。

#### 目标 spec / API

- `spec/pass/lowering/nn_lowering/dma_structured_lowering.md`
- `spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md`
- `公开 API：NnLoweringPass`
- `内部 API：dma_structured_patterns() / matmul_img2col_patterns()`

#### 禁止修改面 / 合同真源

- `禁止修改面：不改 broadcast/transpose/img2col/matmul 的 IR 输出与校验语义`
- `合同真源：expectation/pass/lowing/nn_lowering/broadcast.py + expectation/pass/lowing/nn_lowering/transpose.py + expectation/pass/lowing/nn_lowering/img2col + expectation/pass/lowing/nn_lowering/matmul.py`

#### 预期示例代码

```python
class LowerNnMatmulPattern(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: NnMatmulOp, rewriter: PatternRewriter, /) -> None:
        lower_matmul_op(op, rewriter)
```

#### 预期输出

```text
nn.broadcast -> dma.alloc + dma.broadcast
nn.transpose -> dma.alloc + dma.transpose
nn.matmul -> dma.alloc + kernel.matmul
```

#### 目标验收资产

- `python3 -m expectation.pass.lowing.nn_lowering.broadcast`
- `python3 -m expectation.pass.lowing.nn_lowering.transpose`
- `python3 -m expectation.pass.lowing.nn_lowering.img2col`
- `python3 -m expectation.pass.lowing.nn_lowering.matmul`

#### 验收必过项目

- `pytest -q test/pass/nn_lowering/img2col1d.py test/pass/nn_lowering/img2col2d.py test/pass/nn_lowering/matmul.py`
- `pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py`

#### 任务新建建议

- `任务类型：refactor`
- `任务目标：按单 op pattern 收口 broadcast/transpose/img2col/matmul，保持现有外部行为。`
- `记录文件：待管理员创建（nn-lowering-structured-patterns-s3.md）`

### S4：exp / reduce / softmax 边界 pattern 与全链路验收

#### 阶段目标

- 将 `nn.exp`、`nn.reduce_*` 与 direct `nn.softmax` 边界收口为单 op pattern，并跑通全链路验收。

#### 目标 spec / API

- `spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md`
- `spec/pass/lowering/nn_lowering/select_cast_lowering.md`
- `公开 API：NnLoweringPass`
- `内部 API：reduce_softmax_patterns()`

#### 禁止修改面 / 合同真源

- `禁止修改面：不把 direct nn.softmax 变成 lower-nn 支持项，不改 reduce axis/keepdim 输出语义`
- `合同真源：expectation/pass/lowing/nn_lowering/reduce + expectation/pass/lowing/nn_lowering/exp.py + test/pass/nn_lowering`

#### 预期示例代码

```python
class RejectNnSoftmaxPattern(RewritePattern):
    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: NnSoftmaxOp, rewriter: PatternRewriter, /) -> None:
        raise NnLoweringError("nn.softmax must be decomposed before lower-nn")
```

#### 预期输出

```text
nn.exp -> dma.alloc + kernel.exp
nn.reduce_max -> dma.alloc + kernel.reduce(kind="max")
nn.softmax -> NnLoweringError("nn.softmax must be decomposed before lower-nn")
```

#### 目标验收资产

- `python3 -m expectation.pass.lowing.nn_lowering.exp`
- `python3 -m expectation.pass.lowing.nn_lowering.reduce`
- `python3 -m expectation.pass.lowing.nn_lowering`

#### 验收必过项目

- `pytest -q test/pass/nn_lowering/exp.py test/pass/nn_lowering/reduce_sum.py test/pass/nn_lowering/reduce_min.py test/pass/nn_lowering/reduce_max.py`
- `pytest -q test/pass/nn_lowering`
- `python3 -m expectation.pass.lowing.nn_lowering`
- `pytest -q test/pass/test_pass_manager.py test/pass/test_pipeline_default_lowering.py test/pass/test_pipeline_npu_demo_lowering.py`

#### 任务新建建议

- `任务类型：refactor`
- `任务目标：收口 exp/reduce/softmax 边界 pattern，并完成 nn_lowering 全链路验收。`
- `记录文件：待管理员创建（nn-lowering-reduce-boundary-patterns-s4.md）`

## 待确认项

- 问题：`无`
- 可选项：`不适用`
- 差异：`用户已明确要求每个 op 对应一个 RewritePattern，并使用 @op_type_rewrite_pattern。`
- 推荐项：`不适用`

## 用户确认与协同约束

- `用户确认状态：已确认`
- `未确认事项：无`
- `用户确认结论：用户明确要求重构 kernel_gen/passes/lowering/nn_lowering，使每一个 op 对应一个 pattern，并使用 MLIR 风格 RewritePattern 与 @op_type_rewrite_pattern。`
- `未确认前处理要求：不适用`
- `若用户要求至少询问 3 人：无`
- `询问记录 1：已通过 -talk 发起互评；对象=守护最好的爱莉希雅；结果=通过，按当前版本可以推进任务创建`
- `询问记录 2：无`
- `询问记录 3：无`

## 参考资料

- [`kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)：当前 pattern driver 与通用分发入口。
- [`kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py)：已存在的单 op pattern 写法。
- [`kernel_gen/dialect/nn.py`](../../kernel_gen/dialect/nn.py)：`NnAddOp`、`NnSubOp`、`NnReduceSumOp` 等具体 op 类型。
- [`agents/codex-multi-agents/log/task_records/done_plan/2026/16/selected_passes_xdsl_modulepass_refactor_green_plan.md`](../../agents/codex-multi-agents/log/task_records/done_plan/2026/16/selected_passes_xdsl_modulepass_refactor_green_plan.md)：旧专题曾给出 `nn_lowering` 的单 op pattern 总方向，本计划只收窄到 `nn_lowering` 专题重构。
