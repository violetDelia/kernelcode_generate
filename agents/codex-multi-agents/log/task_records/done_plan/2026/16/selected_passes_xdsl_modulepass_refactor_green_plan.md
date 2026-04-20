# selected_passes_xdsl_modulepass_refactor_green_plan.md

## 文档信息

- 创建者：`榕`
- 最后一次更改：`榕`
- 目标 `spec`：
  - [`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)
  - [`spec/pass/registry.md`](../../spec/pass/registry.md)
  - [`spec/pass/lowering/nn_lowering.md`](../../spec/pass/lowering/nn_lowering.md)
  - [`spec/pass/lowering/nn_lowering/element_binary_lowering.md`](../../spec/pass/lowering/nn_lowering/element_binary_lowering.md)
  - [`spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md`](../../spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md)
  - [`spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md`](../../spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md)
  - [`spec/pass/lowering/nn_lowering/select_cast_lowering.md`](../../spec/pass/lowering/nn_lowering/select_cast_lowering.md)
  - [`spec/pass/lowering/nn_lowering/dma_structured_lowering.md`](../../spec/pass/lowering/nn_lowering/dma_structured_lowering.md)
  - [`spec/pass/lowering/buffer_results_to_out_params.md`](../../spec/pass/lowering/buffer_results_to_out_params.md)
  - [`spec/pass/decompass.md`](../../spec/pass/decompass.md)
  - [`spec/pass/outline_device_kernel.md`](../../spec/pass/outline_device_kernel.md)
  - [`spec/pass/symbol_loop_hoist.md`](../../spec/pass/symbol_loop_hoist.md)
- 目标 `API`：
  - [`kernel_gen/passes/pass_manager.py`](../../kernel_gen/passes/pass_manager.py)
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
  - [`kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
  - [`kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py)
  - [`kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py)
  - [`kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py)
  - [`kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py)
  - [`kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py)
  - [`kernel_gen/passes/buffer_results_to_out_params.py`](../../kernel_gen/passes/buffer_results_to_out_params.py)
  - [`kernel_gen/passes/decompass.py`](../../kernel_gen/passes/decompass.py)
  - [`kernel_gen/passes/outline_device_kernel.py`](../../kernel_gen/passes/outline_device_kernel.py)
  - [`kernel_gen/passes/symbol_loop_hoist.py`](../../kernel_gen/passes/symbol_loop_hoist.py)
- 目标 `test`：
  - [`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)
  - [`test/pass/test_pass_registry.py`](../../test/pass/test_pass_registry.py)
  - [`test/pass/nn_lowering/test_lowering_nn_lowering.py`](../../test/pass/nn_lowering/test_lowering_nn_lowering.py)
  - [`test/pass/test_buffer_results_to_out_params.py`](../../test/pass/test_buffer_results_to_out_params.py)
  - [`test/pass/decompass/test_softmax.py`](../../test/pass/decompass/test_softmax.py)
  - [`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../test/pass/outline_device_kernel/test_outline_device_kernel.py)
  - [`test/pass/test_symbol_loop_hoist.py`](../../test/pass/test_symbol_loop_hoist.py)
- 目标 `验收资产`：
  - [`expectation/pass/lowing/nn_lowering`](../../expectation/pass/lowing/nn_lowering)
  - [`expectation/pass/buffer_results_to_out_params`](../../expectation/pass/buffer_results_to_out_params)
  - [`expectation/pass/decompass`](../../expectation/pass/decompass)
  - [`expectation/pass/outline_device_kernel`](../../expectation/pass/outline_device_kernel)
  - [`expectation/pass/symbol_loop_hoist`](../../expectation/pass/symbol_loop_hoist)
- 目标 `功能实现`：
  - [`kernel_gen/passes/pass_manager.py`](../../kernel_gen/passes/pass_manager.py)
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
  - [`kernel_gen/passes/lowering/nn_lowering`](../../kernel_gen/passes/lowering/nn_lowering)
  - [`kernel_gen/passes/buffer_results_to_out_params.py`](../../kernel_gen/passes/buffer_results_to_out_params.py)
  - [`kernel_gen/passes/decompass.py`](../../kernel_gen/passes/decompass.py)
  - [`kernel_gen/passes/outline_device_kernel.py`](../../kernel_gen/passes/outline_device_kernel.py)
  - [`kernel_gen/passes/symbol_loop_hoist.py`](../../kernel_gen/passes/symbol_loop_hoist.py)

## 任务清单

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `S1` | `无` | `待管理员创建（ModulePass-registry-base）` | `待管理员创建（selected-passes-xdsl-s1.md）` |
| `S2` | `S1` | `待管理员创建（nn-lowering-family-modulepass）` | `待管理员创建（selected-passes-xdsl-s2.md）` |
| `S3` | `S1` | `待管理员创建（buffer-results-plus-decompass）` | `待管理员创建（selected-passes-xdsl-s3.md）` |
| `S4` | `S1` | `待管理员创建（outline-plus-symbol-loop-hoist）` | `待管理员创建（selected-passes-xdsl-s4.md）` |

## 评审摘要

- 评审结论：`通过`
- 评审人：`守护最好的爱莉希雅`、`大闸蟹`
- 结论摘要：`S1~S4 任务拆分合理，公开 API、ModulePass、registry 兼容边界清楚；兼容桥已写死：本专题目标 pass 由 build_registered_pass(...) 直接返回 ModulePass，PassManager.run(...) 直接兼容执行 ModulePass.apply(ctx, module)，default-lowering 迁移期可混用旧 Pass 与新 ModulePass；nn_lowering 已按 convert_memref_to_ptr.py 风格收口到“辅助函数 + 单 op RewritePattern + 薄 ModulePass.apply()”；其余 pass 也已尽量收成单 op pattern，确实不适合时才退到单局部结构 pattern。`

## 输入摘要

- 目标：让指定 pass 更多使用 xdsl 的 `fold / canonicalize / pattern rewriter / CSE` 基础设施，并改成 `ModulePass`。
- 不做什么：本轮不改其他 pass，不重做整体 pipeline，不为 `symbol.for` 额外引入 control-flow interface，不先自造仓库级 wrapper。
- 当前痛点：仓库 pass 主要是自定义 `Pass.run(...)` + 手写遍历/重建 IR；op 的 fold/canonicalize 能力没有通过 pass 自动触发，修改面大、维护成本高。
- 完成后最想看到的例子：`build_registered_pass("lower-nn")`、`build_registered_pass("decompass")` 等公开入口保持不变，但返回的对象已经是 `ModulePass`，内部通过 xdsl pattern/fold/canonicalize/CSE 完成改写。

## 计划目标

- 把 `nn_lowering` whole family、`buffer-results-to-out-params`、`decompass`、`outline-device-kernel`、`symbol-loop-hoist` 重构为基于 xdsl `ModulePass` 的实现。
- 让这些 pass 的改写逻辑优先迁移到 op 级 `fold`、canonicalization patterns、`PatternRewriteWalker` 与 `GreedyRewritePatternApplier`，减少大块手写 IR 重建。
- `nn_lowering` family 的目标组织方式明确参考 [`xdsl/transforms/convert_memref_to_ptr.py`](/home/lfr/.local/lib/python3.12/site-packages/xdsl/transforms/convert_memref_to_ptr.py)：辅助函数 + 若干单 op `RewritePattern` + 一个薄的 `ModulePass.apply()` 入口。
- 保持公开 pass 名和 `build_registered_pass(...)` 入口不变，只替换实现内核。
- 保留 [`register_decompass_rewrite(...)`](../../kernel_gen/passes/decompass.py) 公开 API，只把内部执行方式改成 op rewrite pattern 驱动。
- 不把 `canonicalize` / `CSE` 先设计成新的公开 standalone pipeline pass；这轮只考虑单 pass 内部如何直接消费 xdsl 现成基础设施。

## 当前基线

- 当前公开合同：
  - [`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md) 与 [`spec/pass/registry.md`](../../spec/pass/registry.md) 仍以仓库自定义 `Pass.run(...)` 为主。
  - `nn_lowering`、`buffer-results-to-out-params`、`decompass`、`outline-device-kernel`、`symbol-loop-hoist` 的 spec 目前都没有把 `ModulePass`、pattern rewriter、`fold/canonicalize/CSE` 写成明确合同。
- 当前公开 API：
  - [`kernel_gen/passes/pass_manager.py`](../../kernel_gen/passes/pass_manager.py) 提供自定义 `Pass` 与 `PassManager`。
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py) 只接受 `Pass` 子类注册与构造。
  - [`kernel_gen/passes/decompass.py`](../../kernel_gen/passes/decompass.py) 暴露 `register_decompass_rewrite(op_name, rewrite)`，当前内部仍是手写 block 级重写。
- 当前实现入口：
  - `nn_lowering` family 当前仍由手写函数遍历和重建 IR 主导。
  - `buffer-results-to-out-params`、`decompass`、`outline-device-kernel`、`symbol-loop-hoist` 也都继承仓库自定义 `Pass`，不直接消费 xdsl 的 `ModulePass`/pattern infra。
- 当前测试与验收资产：
  - `nn_lowering` 使用 [`expectation/pass/lowing/nn_lowering`](../../expectation/pass/lowing/nn_lowering) 与 [`test/pass/nn_lowering/test_lowering_nn_lowering.py`](../../test/pass/nn_lowering/test_lowering_nn_lowering.py)。
  - `buffer-results-to-out-params`、`decompass`、`outline-device-kernel`、`symbol-loop-hoist` 各自已有 expectation 或 pytest 入口。
- 当前缺口或失败点：
  - 仓库 pass 几乎没有直接使用 xdsl `PatternRewriteWalker`、`GreedyRewritePatternApplier`、`CanonicalizePass`、`CommonSubexpressionElimination`。
  - op 的 `fold` / canonicalization 能力没有系统性接入 pass。
  - `build_registered_pass(...)`、`PassManager.run(...)` 与 `default-lowering` 目前都默认以仓库自定义 `Pass.run(...)` 为主合同，尚未把 `ModulePass.apply(ctx, module)` 的兼容桥写死。
  - 若继续沿手写遍历扩展，后续维护成本与影响面都会持续增大。
  - 当前本地 xdsl 已升级到 `0.62.1`，基础设施已足够支持本轮目标，缺口主要在仓库接入，而不是 xdsl 版本本身。

## 合同真源顺序

- `expectation/pass/lowing/nn_lowering + expectation/pass/buffer_results_to_out_params + expectation/pass/decompass + expectation/pass/outline_device_kernel + expectation/pass/symbol_loop_hoist > spec/pass/* > test/pass/* > 当前实现`

## 方案比较与选型

- 不采用方案：继续沿仓库自定义 `Pass.run(...)` 框架增量补手写遍历。
  - 原因：不能自动触发 op fold / canonicalize，局部改动容易演变成整段 IR 重建，维护成本高。
- 不采用方案：先自造一层仓库级 `rewrite driver / canonicalize wrapper / cse wrapper`，再让目标 pass 间接调用。
  - 原因：这轮用户已经明确要优先直接用 xdsl 已封好的基础设施；当前范围只覆盖指定 5 组 pass，没有必要先引入新的仓库抽象层。
- 采用方案：
  - 目标 pass 直接继承 xdsl `ModulePass`；
  - 目标 pass 内部直接使用 xdsl 现有基础设施：
    - `HasFolderInterface`
    - `HasCanonicalizationPatternsTrait`
    - `PatternRewriteWalker`
    - `GreedyRewritePatternApplier`
    - `CanonicalizePass`
    - `CommonSubexpressionElimination`
  - 其中 `nn_lowering` family 的组织方式按 `convert_memref_to_ptr.py` 收口：
    - 先抽辅助构造函数
    - 再按单个 op 拆成多个 `RewritePattern`
    - 最后由一个薄的 `ModulePass.apply()` 组装 `GreedyRewritePatternApplier([...])`
  - 其他目标 pass 也尽可能按同一结构收口：
    - 辅助函数
    - 若干单 op `RewritePattern`
    - 若确实不适合按单 op 切分，则退到单一局部结构 `RewritePattern`
    - 一个薄的 `ModulePass.apply()`
  - 仓库只保留必要的 registry / pass_manager 兼容适配，保证公开 pass 名与 `build_registered_pass(...)` 入口保持不变。
  - 兼容桥写死：
    - `build_registered_pass(...)` 对本专题目标 pass 直接返回 `ModulePass`
    - `PassManager.run(...)` 在迁移期直接兼容执行 `ModulePass.apply(ctx, module)`
    - 不采用“把 ModulePass 再包成伪 Pass 适配器”的方案
    - `default-lowering` 在迁移期允许同时混用旧 `Pass` 与新 `ModulePass`
- 最小公开接口：
  - `build_registered_pass("lower-nn")`
  - `build_registered_pass("buffer-results-to-out-params")`
  - `build_registered_pass("decompass")`
  - `build_registered_pass("outline-device-kernel")`
  - `build_registered_pass("symbol-loop-hoist")`

## 公开 API 设计

### 公开 pass 构造口径

- 公开入口保持不变：
  - `build_registered_pass("<pass-name>")`
- 返回对象合同改为：
  - refactor 后的目标 pass 必须是 `xdsl.passes.ModulePass` 实例
- 公开类与 pass 名保持不变：
  - `NnLoweringPass.name == "lower-nn"`
  - `BufferResultsToOutParamsPass.name == "buffer-results-to-out-params"`
  - `DecompassPass.name == "decompass"`
  - `OutlineDeviceKernelPass.name == "outline-device-kernel"`
  - `SymbolLoopHoistPass.name == "symbol-loop-hoist"`
- 公开方法签名目标：
  - `def apply(self, ctx: Context, op: builtin.ModuleOp) -> None`
- 兼容口径：
  - `build_registered_pass("<name>")` 的调用方式保持不变
  - registry 对外仍按原 pass 名查找，不引入新的公开别名
  - 对本专题目标 pass，`build_registered_pass(...)` 直接返回 `ModulePass`
  - `PassManager.run(...)` 负责兼容执行 `ModulePass.apply(ctx, module)`，不要求调用方手工包适配器
  - `default-lowering` 在迁移期可以混用旧 `Pass` 与新 `ModulePass`
  - 原来若有 `from_options(...)` 公开入口，则只有在现有 spec 已定义时才保留；本专题涉及的 5 个 pass 本轮不新增新的公开 options
- 最小示例：

```python
from xdsl.context import Context
from xdsl.dialects import builtin
from xdsl.passes import ModulePass
from kernel_gen.passes.registry import build_registered_pass

ctx = Context()
pass_obj = build_registered_pass("decompass")
assert isinstance(pass_obj, ModulePass)
assert pass_obj.name == "decompass"
module = builtin.ModuleOp([])
pass_obj.apply(ctx, module)
```

### 公开类级 API

#### NnLoweringPass

- 公开类：
  - [`kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/nn_lowering.py) 中的 `NnLoweringPass`
- 公开合同：
  - `name = "lower-nn"`
  - `apply(ctx, module)` 作为唯一 pass 执行入口
  - `nn_lowering.py` 仍是唯一公开 pass 文件；其余 `*_lowering.py` 子模块不单独暴露新 pass 名

```python
ctx = Context()
module = builtin.ModuleOp([])
lower_nn = build_registered_pass("lower-nn")
lower_nn.apply(ctx, module)
```

#### BufferResultsToOutParamsPass

- 公开类：
  - [`kernel_gen/passes/buffer_results_to_out_params.py`](../../kernel_gen/passes/buffer_results_to_out_params.py) 中的 `BufferResultsToOutParamsPass`
- 公开合同：
  - `name = "buffer-results-to-out-params"`
  - 继续只对 `builtin.module` 生效
  - 不新增新的公开 options

```python
ctx = Context()
rewrite_pass = build_registered_pass("buffer-results-to-out-params")
rewrite_pass.apply(ctx, module)
```

#### DecompassPass 与 register_decompass_rewrite

- 公开类：
  - [`kernel_gen/passes/decompass.py`](../../kernel_gen/passes/decompass.py) 中的 `DecompassPass`
- 公开扩展函数：
  - [`register_decompass_rewrite(op_name, rewrite)`](../../kernel_gen/passes/decompass.py)
- 公开合同：
  - `name = "decompass"`
  - `register_decompass_rewrite(...)` 保留为外部注册额外 rewrite 的唯一公开入口
  - 内部改成 pattern 驱动后，不改变该函数的外部调用方式

```python
def rewrite_fn(op, rewriter): ...

register_decompass_rewrite("nn.some_op", rewrite_fn)
decompass_pass = build_registered_pass("decompass")
decompass_pass.apply(ctx, module)
```

#### OutlineDeviceKernelPass

- 公开类：
  - [`kernel_gen/passes/outline_device_kernel.py`](../../kernel_gen/passes/outline_device_kernel.py) 中的 `OutlineDeviceKernelPass`
- 公开合同：
  - `name = "outline-device-kernel"`
  - 继续只处理带 launch attrs 的 `func.func`
  - 公开语义仍是“把原函数改成 wrapper，并生成 sibling device func”

```python
outline_pass = build_registered_pass("outline-device-kernel")
outline_pass.apply(ctx, module)
```

#### SymbolLoopHoistPass

- 公开类：
  - [`kernel_gen/passes/symbol_loop_hoist.py`](../../kernel_gen/passes/symbol_loop_hoist.py) 中的 `SymbolLoopHoistPass`
- 公开合同：
  - `name = "symbol-loop-hoist"`
  - 继续只围绕 `symbol.for` 做 invariant hoist
  - 不新增新的公开 control-flow interface 或 loop analysis API

```python
hoist_pass = build_registered_pass("symbol-loop-hoist")
hoist_pass.apply(ctx, module)
```

### 公开扩展口径

- `decompass` 保留：
  - [`register_decompass_rewrite(op_name, rewrite)`](../../kernel_gen/passes/decompass.py)
- 最小示例：

```python
from kernel_gen.passes.decompass import register_decompass_rewrite

register_decompass_rewrite("nn.some_op", rewrite_fn)
```

### 本轮不收口为公开能力的内容

- 不新增独立公开 `canonicalize` pass
- 不新增独立公开 `cse` pass
- 不为 `symbol.for` 新增控制流 interface 公开合同
- 不改其他 pass 的公开名字或公开行为

## 完成态定义

- 指定 5 组 pass 都已改为 `ModulePass`。
- `build_registered_pass(...)`、现有 pass 名、`register_decompass_rewrite(...)` 这些公开入口保持不变。
- 目标 pass 内部主要通过 xdsl 的 fold / canonicalize / pattern rewriter / CSE 组织改写逻辑，不再以大段手写遍历重建为主。
- `symbol.for` 仍然是仓库当前唯一控制流 op，但本轮不会为它额外引入 control-flow interface；相关 pass 仍按 region/block 级 pattern 处理。
- 其他 pass 不进入本轮修改面。

## 验收设计

- 验收资产：
  - [`expectation/pass/lowing/nn_lowering`](../../expectation/pass/lowing/nn_lowering)
  - [`expectation/pass/buffer_results_to_out_params`](../../expectation/pass/buffer_results_to_out_params)
  - [`expectation/pass/decompass`](../../expectation/pass/decompass)
  - [`expectation/pass/outline_device_kernel`](../../expectation/pass/outline_device_kernel)
  - [`expectation/pass/symbol_loop_hoist`](../../expectation/pass/symbol_loop_hoist)
  - [`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)
  - [`test/pass/test_pass_registry.py`](../../test/pass/test_pass_registry.py)
  - [`test/pass/nn_lowering/test_lowering_nn_lowering.py`](../../test/pass/nn_lowering/test_lowering_nn_lowering.py)
  - [`test/pass/test_buffer_results_to_out_params.py`](../../test/pass/test_buffer_results_to_out_params.py)
  - [`test/pass/decompass/test_softmax.py`](../../test/pass/decompass/test_softmax.py)
  - [`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../test/pass/outline_device_kernel/test_outline_device_kernel.py)
  - [`test/pass/test_symbol_loop_hoist.py`](../../test/pass/test_symbol_loop_hoist.py)
- 锁定输出：
  - 公开入口不变，内部实现切换到 `ModulePass` + xdsl 基础设施；
  - `nn_lowering` family 的 lowering 结果、`buffer-results-to-out-params` 的返回合同改写、`decompass` 的 softmax 分解、`outline-device-kernel` 的 outline 结果、`symbol-loop-hoist` 的 invariant hoist 行为都与现有 expectation / pytest 保持一致或按执行阶段同步更新 expectation；
  - 不新增“为了重构而重构”的公开兼容层。
- 本轮不单独拆一个“验收阶段”；每个任务链内部都要完成 spec/build/review 闭环。

## 阶段拆分

### S1：ModulePass 接入与运行约定收口

#### 阶段目标

- 让仓库现有 `registry / pass_manager` 能稳定构造并执行 refactor 后的 `ModulePass`，同时不改公开 pass 名和 `build_registered_pass(...)` 入口。
- 把 `build_registered_pass(...)`、`PassManager.run(...)` 与 `default-lowering` 的兼容桥一次性写死，避免迁移期合同悬空。

#### 目标 spec / API

- [`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)
- [`spec/pass/registry.md`](../../spec/pass/registry.md)
- [`kernel_gen/passes/pass_manager.py`](../../kernel_gen/passes/pass_manager.py)
- [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)

#### 禁止修改面 / 合同真源

- `禁止修改面：除目标 5 组 pass 外，其他 pass 的公开行为不在本阶段改动`
- `合同真源：本计划书 > spec/pass/pass_manager.md + spec/pass/registry.md`

#### 预期示例代码

```python
from xdsl.context import Context
from xdsl.passes import ModulePass
from kernel_gen.passes.registry import build_registered_pass
from kernel_gen.passes.pass_manager import PassManager

ctx = Context()
pass_obj = build_registered_pass("symbol-loop-hoist")
assert isinstance(pass_obj, ModulePass)
pass_obj.apply(ctx, module)

pm = PassManager(name="lowering")
pm.add_pass(build_registered_pass("lower-nn"))
pm.run(module)
```

#### 预期输出

```text
- build_registered_pass("lower-nn" / "decompass" / ...) 入口保持不变
- 本专题目标 pass 由 registry 直接返回 ModulePass
- PassManager.run(...) 直接兼容执行 ModulePass.apply(ctx, module)
- default-lowering 在迁移期可以混用旧 Pass 与新 ModulePass
```

#### 目标验收资产

- [`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)
- [`test/pass/test_pass_registry.py`](../../test/pass/test_pass_registry.py)

#### 验收必过项目

- `test/pass/test_pass_manager.py`
- `test/pass/test_pass_registry.py`

#### 任务新建建议

## 最终验收结论（2026-04-21 00:13:08 +0800）

- 验收结论：`不通过`
- 验证基线：
  - `main@5088dd93ce62700b891475d4ae678e993af4867a`
  - 主仓当前落后 `origin/main` 且存在未跟踪 worktree，因此本轮在干净 detached worktree `/home/lfr/kernelcode_generate/wt-20260421-selected-passes-final-check` 上复验
  - 由于 `expectation/` 资产不在该 clean worktree 中，目录级 expectation 统一通过 `PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260421-selected-passes-final-check:/home/lfr/kernelcode_generate` 组合主线实现与主仓 expectation 真源执行
- 最小阻断项：
  - [`expectation/pass/buffer_results_to_out_params`](../../expectation/pass/buffer_results_to_out_params) 目录级 expectation 仍失败；最小复现为 `python3 -m expectation.pass.buffer_results_to_out_params.single_output`
  - 具体失败点为 [`expectation/pass/buffer_results_to_out_params/single_output.py`](../../expectation/pass/buffer_results_to_out_params/single_output.py) 的 `CASE-1` 与 `CASE-2`，当前 `CHECK-NEXT` 锁定的 `func.func @copy(...)` 函数签名未能匹配最新主线 pass 输出
- 复验摘要：
  - 已通过：
    - `pytest -q test/pass/test_pass_manager.py test/pass/test_pass_registry.py` -> `42 passed`
    - `python3 -m expectation.pass.lowing.nn_lowering` -> `exit 0`
    - `python3 -m expectation.pass.decompass` -> `exit 0`
    - `python3 -m expectation.pass.outline_device_kernel` -> `exit 0`
    - `python3 -m expectation.pass.symbol_loop_hoist` -> `exit 0`
    - `pytest -q test/pass/nn_lowering/test_lowering_nn_lowering.py test/pass/test_buffer_results_to_out_params.py test/pass/decompass/test_softmax.py test/pass/outline_device_kernel/test_outline_device_kernel.py test/pass/test_symbol_loop_hoist.py` -> `84 passed`
  - 未通过：
    - `python3 -m expectation.pass.buffer_results_to_out_params` -> `exit 1`

## 当前唯一修复任务（2026-04-21 00:14:25 +0800）

- 任务号：`T-20260421-3f4b68f2`
- `worktree`：`/home/lfr/kernelcode_generate/wt-20260421-selected-passes-xdsl-s5-repair`
- 记录文件：[`agents/codex-multi-agents/log/task_records/2026/16/20260421-selected-passes-xdsl-s5-repair.md`](../../agents/codex-multi-agents/log/task_records/2026/16/20260421-selected-passes-xdsl-s5-repair.md)
- 最小修复目标：
  - 收口 [`expectation/pass/buffer_results_to_out_params/single_output.py`](../../expectation/pass/buffer_results_to_out_params/single_output.py) 的 `CASE-1` / `CASE-2` 与最新主线 `ModulePass` 输出，使 `python3 -m expectation.pass.buffer_results_to_out_params.single_output` 恢复通过
  - 进一步恢复 `python3 -m expectation.pass.buffer_results_to_out_params` 全绿
  - 同时保持已通过的 `pass_manager / registry`、`nn_lowering`、`decompass`、`outline_device_kernel`、`symbol_loop_hoist` expectation 与 pytest 子集不回退

## 复验结论（2026-04-21 00:40:49 +0800）

- 验收结论：`不通过`
- 验证基线：
  - `main@7963caf3cdac851f33807256c8e040906fbe4bea`
  - 已按最新管理员口径直接更新主仓到最新主线现场后复验
- 最小阻断项：
  - [`expectation/pass/outline_device_kernel/basic.py`](../../expectation/pass/outline_device_kernel/basic.py) 的 `CASE-1` 仍失败；最小复现为 `python3 -m expectation.pass.outline_device_kernel.basic`
  - 当前报错为：`IrcheckMatchError: CHECK-NEXT not found on next line: pattern 'func.func @kernel(%[[ARG0:{reg}]] : !nn.memory<[4], [1], f32, #nn.space<global>>) {' not found on next line`
- 复验摘要：
  - 已恢复通过：
    - `python3 -m expectation.pass.buffer_results_to_out_params` -> `exit 0`
    - `pytest -q test/pass/test_pass_manager.py test/pass/test_pass_registry.py test/pass/nn_lowering/test_lowering_nn_lowering.py test/pass/test_buffer_results_to_out_params.py test/pass/decompass/test_softmax.py test/pass/outline_device_kernel/test_outline_device_kernel.py test/pass/test_symbol_loop_hoist.py` -> `126 passed`
    - `python3 -m expectation.pass.lowing.nn_lowering` -> `exit 0`
    - `python3 -m expectation.pass.decompass` -> `exit 0`
    - `python3 -m expectation.pass.symbol_loop_hoist` -> `exit 0`
  - 当前仅剩 `outline_device_kernel` 目录级 expectation 未绿，因此仍不满足归档前置条件

## 当前唯一修复任务（2026-04-21 00:43:57 +0800）

- 任务号：`T-20260421-c3d8c12f`
- `worktree`：`/home/lfr/kernelcode_generate/wt-20260421-selected-passes-xdsl-s6-repair`
- 记录文件：[`agents/codex-multi-agents/log/task_records/2026/16/20260421-selected-passes-xdsl-s6-repair.md`](../../agents/codex-multi-agents/log/task_records/2026/16/20260421-selected-passes-xdsl-s6-repair.md)
- 最小修复目标：
  - 收口 [`expectation/pass/outline_device_kernel/basic.py`](../../expectation/pass/outline_device_kernel/basic.py) 的 `CASE-1`，使 `ircheck` 不再把 SSA/参数名绑定过死
  - 恢复：
    - `python3 -m expectation.pass.outline_device_kernel.basic`
    - `python3 -m expectation.pass.outline_device_kernel`
    通过
  - 同时保持已通过的：
    - `python3 -m expectation.pass.buffer_results_to_out_params`
    - `pytest -q test/pass/test_pass_manager.py test/pass/test_pass_registry.py test/pass/nn_lowering/test_lowering_nn_lowering.py test/pass/test_buffer_results_to_out_params.py test/pass/decompass/test_softmax.py test/pass/outline_device_kernel/test_outline_device_kernel.py test/pass/test_symbol_loop_hoist.py`
    - `python3 -m expectation.pass.lowing.nn_lowering`
    - `python3 -m expectation.pass.decompass`
    - `python3 -m expectation.pass.symbol_loop_hoist`
    不回退

## 复验结论（2026-04-21 09:08:00 +0800）

- 验收结论：`不通过`
- 验证基线：
  - `main@7963caf3cdac851f33807256c8e040906fbe4bea`
  - 主仓执行目录：`/home/lfr/kernelcode_generate`
  - 按管理员本轮口径，直接在当前主仓最新同步现场复验
- 最小阻断项：
  - [`expectation/pass/outline_device_kernel/basic.py`](../../expectation/pass/outline_device_kernel/basic.py) 的 `CASE-1` 仍失败；最小复现为 `python3 -m expectation.pass.outline_device_kernel.basic`
  - 当前报错仍是：`IrcheckMatchError: CHECK-NEXT not found on next line: pattern 'func.func @kernel(%[[ARG0:{reg}]] : !nn.memory<[4], [1], f32, #nn.space<global>>) {' not found on next line`
  - 本轮复验补充确认：实际 IR 已生成正确的 `wrapper + device` 双函数，但 [`basic.py`](../../expectation/pass/outline_device_kernel/basic.py) 的 `CHECK-NEXT` 把 wrapper/device 的 SSA 名与参数名绑定成 `%[[ARG0]] / %[[DEV_ARG]]`，而当前实际输出使用 `%0 / %1 / %2 / %3 / %arg0`，导致在第二行即发生文本匹配失配
- 复验摘要：
  - 已复现失败：
    - `python3 -m expectation.pass.outline_device_kernel.basic` -> `exit 1`
    - `python3 -m expectation.pass.outline_device_kernel` -> `exit 1`
  - 实际 IR 摘要：
    - wrapper `func.func @kernel(%0: !nn.memory<[4], [1], f32, #nn.space<global>>)` 已存在
    - wrapper 内 `symbol.const 1 / 4 / 1`、`arch.launch<...>(@kernel_device, %0)` 与 `func.return` 已存在
    - `func.func @kernel_device(%arg0 : !nn.memory<[4], [1], f32, #nn.space<global>>) attributes {shared_memory_size = 0 : i64}` 已存在
  - 结论：
    - 当前最小阻断项已稳定收敛为 `outline_device_kernel basic expectation` 的 `ircheck` 文本失配；其余链路按上一轮复验结果保持通过，但在该 expectation 未恢复前，计划仍不满足归档前置条件

- `任务类型：refactor`
- `任务目标：收口 ModulePass 接入、registry 兼容与运行约定`
- `记录文件：待管理员创建`

### S2：nn_lowering family 重构为 op rewrite pattern

#### 阶段目标

- 将 `nn_lowering` whole family 重构为 `ModulePass + op rewrite pattern + fold/canonicalize/CSE` 驱动，同时保持 `lower-nn` 公开入口不变。
- 具体组织方式按 [`convert_memref_to_ptr.py`](/home/lfr/.local/lib/python3.12/site-packages/xdsl/transforms/convert_memref_to_ptr.py) 收口：辅助函数、单 op pattern、薄的 pass 入口三层分离。
- 子模块拆分目标直接写死：
  - `element_binary_lowering.py`：`nn.add`、`nn.sub`、`nn.mul`、`nn.div`、`nn.truediv`、各 compare op 各自单独 pattern
  - `reduce_softmax_lowering.py`：`nn.reduce_sum`、`nn.reduce_min`、`nn.reduce_max`、`nn.softmax` 各自单独 pattern
  - `select_cast_lowering.py`：`nn.select`、`nn.cast`、`nn.exp` 各自单独 pattern
  - `dma_structured_lowering.py`：`nn.broadcast`、`nn.transpose` 等结构化 dma 相关 op 各自单独 pattern
  - `matmul_img2col_lowering.py`：`nn.matmul`、`nn.img2col1d`、`nn.img2col2d`、`nn.fc` 各自单独 pattern
  - `nn_lowering.py`：只负责组装 pattern 集合、调度 rewrite walker、串接必要的 canonicalize/CSE，不再继续承载大块手写 lowering 主逻辑

#### 目标 spec / API

- [`spec/pass/lowering/nn_lowering.md`](../../spec/pass/lowering/nn_lowering.md)
- [`spec/pass/lowering/nn_lowering/element_binary_lowering.md`](../../spec/pass/lowering/nn_lowering/element_binary_lowering.md)
- [`spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md`](../../spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md)
- [`spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md`](../../spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md)
- [`spec/pass/lowering/nn_lowering/select_cast_lowering.md`](../../spec/pass/lowering/nn_lowering/select_cast_lowering.md)
- [`spec/pass/lowering/nn_lowering/dma_structured_lowering.md`](../../spec/pass/lowering/nn_lowering/dma_structured_lowering.md)
- [`kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
- [`kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py)
- [`kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py)
- [`kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py)
- [`kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py)
- [`kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py)

#### 禁止修改面 / 合同真源

- `禁止修改面：不修改其他 lowering pass；不把 tile / tuning / dma_memory_hierarchy 一起纳入本阶段`
- `合同真源：expectation/pass/lowing/nn_lowering > nn_lowering 系列 spec > nn_lowering pytest`

#### 预期示例代码

```python
from xdsl.context import Context
from xdsl.pattern_rewriter import GreedyRewritePatternApplier, PatternRewriteWalker
from kernel_gen.passes.registry import build_registered_pass

ctx = Context()
pass_obj = build_registered_pass("lower-nn")
pass_obj.apply(ctx, module)

# 目标结构示意：
# class LowerNnAddPattern(RewritePattern): ...
# class LowerNnSoftmaxPattern(RewritePattern): ...
# class LowerNnMatmulPattern(RewritePattern): ...
# class LowerNnBroadcastPattern(RewritePattern): ...
# class NnLoweringPass(ModulePass):
#     def apply(self, ctx, op):
#         PatternRewriteWalker(
#             GreedyRewritePatternApplier([...])
#         ).rewrite_module(op)
```

#### 预期输出

```text
- lower-nn 仍是唯一公开 pass 名
- 内部 lowering 主要通过 op rewrite pattern 组织
- 文件结构接近 convert_memref_to_ptr.py，而不是继续堆叠大块 _lower_module/_lower_func 手写遍历
- nn_lowering.py 退化为薄 orchestrator；主要 rewrite 逻辑下沉到各 lowering 子模块的 pattern 集合
- 适合的 op fold / canonicalize 能自动触发
```

#### 子模块目标结构

- [`kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py)
  - 目标：围绕各个二元算子 op 的辅助函数与单 op `RewritePattern` 集合
  - 不再保留“大而全”的跨 family 遍历入口
- [`kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py)
  - 目标：围绕 `reduce_sum`、`reduce_min`、`reduce_max`、`softmax` 的单 op pattern 集合
  - 适合的恒等、常量、轴规整逻辑优先放到 op fold / canonicalize
- [`kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py)
  - 目标：围绕 `select` / `cast` / `exp` 的单 op pattern 集合
  - 避免继续以共享手写 block 改写函数承载不相关 op
- [`kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/dma_structured_lowering.py)
  - 目标：围绕 structured dma 风格各 op 的单 op pattern 集合
  - `broadcast / transpose` 相关 rewrite 逻辑在此 family 内闭环
- [`kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py)
  - 目标：围绕 `matmul / img2col / fc` 的单 op pattern 集合
  - 共享的形状/符号/offset 构造走辅助函数，不再散落在 pass orchestrator 里
- [`kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
  - 目标：只保留 `ModulePass` 入口、pattern 汇总、rewrite walker 调用与必要的后处理
  - 不再直接承载各 family 的 lowering 细节

#### 目标验收资产

- [`expectation/pass/lowing/nn_lowering`](../../expectation/pass/lowing/nn_lowering)
- [`test/pass/nn_lowering/test_lowering_nn_lowering.py`](../../test/pass/nn_lowering/test_lowering_nn_lowering.py)

#### 验收必过项目

- `expectation/pass/lowing/nn_lowering`
- `test/pass/nn_lowering/test_lowering_nn_lowering.py`

#### 任务新建建议

- `任务类型：refactor`
- `任务目标：将 nn_lowering family 迁到 ModulePass 与 op rewrite pattern`
- `记录文件：待管理员创建`

### S3：buffer-results-to-out-params 与 decompass 收口

#### 阶段目标

- 将 `buffer-results-to-out-params` 与 `decompass` 两个局部 IR 改写 pass 迁到 `ModulePass` 与 pattern 驱动，同时保持公开入口不变。
- 两个 pass 都尽可能采用与 `convert_memref_to_ptr.py` 相同的组织方式：辅助函数、单 op 或单局部结构 pattern、薄的 `ModulePass.apply()`。

#### 目标 spec / API

- [`spec/pass/lowering/buffer_results_to_out_params.md`](../../spec/pass/lowering/buffer_results_to_out_params.md)
- [`spec/pass/decompass.md`](../../spec/pass/decompass.md)
- [`kernel_gen/passes/buffer_results_to_out_params.py`](../../kernel_gen/passes/buffer_results_to_out_params.py)
- [`kernel_gen/passes/decompass.py`](../../kernel_gen/passes/decompass.py)

#### 禁止修改面 / 合同真源

- `禁止修改面：不扩展 decompass 的新公开 op 范围；当前仍以 softmax 为主合同`
- `合同真源：expectation/pass/buffer_results_to_out_params + expectation/pass/decompass > 对应 spec > 对应 pytest`

#### 预期示例代码

```python
from kernel_gen.passes.decompass import register_decompass_rewrite
from kernel_gen.passes.registry import build_registered_pass

register_decompass_rewrite("nn.some_op", rewrite_fn)
pass_obj = build_registered_pass("decompass")
```

#### 预期输出

```text
- buffer-results-to-out-params 仍保持同名公开入口
- register_decompass_rewrite(...) 仍保留
- decompass 内部改成 op rewrite pattern 驱动
- buffer-results-to-out-params 不再以单个超长 run() / rewrite 函数承载主逻辑
- 两个 pass 的主文件都收成“薄 pass + 单 op / 单局部结构 pattern”
```

#### 子模块目标结构

- [`kernel_gen/passes/buffer_results_to_out_params.py`](../../kernel_gen/passes/buffer_results_to_out_params.py)
  - 目标：把 callsite 改写、callee 改写、signature/arg attr 更新等逻辑拆成辅助函数 + 若干单局部结构 `RewritePattern`
  - `BufferResultsToOutParamsPass` 只保留 `ModulePass.apply()` 与必要的前置校验/后置校验
  - 避免继续以一个超长文件内的顺序式重写函数串起全部行为
- [`kernel_gen/passes/decompass.py`](../../kernel_gen/passes/decompass.py)
  - 目标：保留 `register_decompass_rewrite(...)` 公开 API，但内部把 `softmax` 等 rewrite 收成按单个 op 注册的 `RewritePattern`
  - `DecompassPass` 只负责 pattern 汇总与 walker 调用
  - 已注册 rewrite 与默认 rewrite 在统一 pattern 驱动下执行，不再继续走手写 block 遍历主链

#### 目标验收资产

- [`expectation/pass/buffer_results_to_out_params`](../../expectation/pass/buffer_results_to_out_params)
- [`expectation/pass/decompass`](../../expectation/pass/decompass)
- [`test/pass/test_buffer_results_to_out_params.py`](../../test/pass/test_buffer_results_to_out_params.py)
- [`test/pass/decompass/test_softmax.py`](../../test/pass/decompass/test_softmax.py)

#### 验收必过项目

- `expectation/pass/buffer_results_to_out_params`
- `expectation/pass/decompass`
- `test/pass/test_buffer_results_to_out_params.py`
- `test/pass/decompass/test_softmax.py`

#### 任务新建建议

- `任务类型：refactor`
- `任务目标：收口 buffer-results-to-out-params 与 decompass 的 ModulePass/pattern 实现`
- `记录文件：待管理员创建`

### S4：outline-device-kernel 与 symbol-loop-hoist 收口

#### 阶段目标

- 将 `outline-device-kernel` 与 `symbol-loop-hoist` 迁到 `ModulePass` 和 xdsl rewrite/fold/canonicalize/CSE 基础设施，同时不引入额外 `symbol.for` control-flow interface。
- 两个 pass 也尽可能采用“辅助函数 + 单 op / 单局部结构 pattern + 薄 pass 入口”的结构，而不是继续在 `run()` 中承载主要改写逻辑。

#### 目标 spec / API

- [`spec/pass/outline_device_kernel.md`](../../spec/pass/outline_device_kernel.md)
- [`spec/pass/symbol_loop_hoist.md`](../../spec/pass/symbol_loop_hoist.md)
- [`kernel_gen/passes/outline_device_kernel.py`](../../kernel_gen/passes/outline_device_kernel.py)
- [`kernel_gen/passes/symbol_loop_hoist.py`](../../kernel_gen/passes/symbol_loop_hoist.py)

#### 禁止修改面 / 合同真源

- `禁止修改面：不为 symbol.for 新增 control-flow interface；不顺手改 pipeline 顺序策略`
- `合同真源：expectation/pass/outline_device_kernel + expectation/pass/symbol_loop_hoist > 对应 spec > 对应 pytest`

#### 预期示例代码

```python
from kernel_gen.passes.registry import build_registered_pass

outline_pass = build_registered_pass("outline-device-kernel")
hoist_pass = build_registered_pass("symbol-loop-hoist")
```

#### 预期输出

```text
- outline-device-kernel 继续只负责 outline，不扩 scope
- symbol-loop-hoist 继续围绕 symbol.for 做 region/block 级重写
- 二者内部实现迁到 ModulePass 与 xdsl 基础设施
- outline-device-kernel 与 symbol-loop-hoist 都尽可能收成薄 pass 入口 + 单 op / 单局部结构 pattern/helper 结构
```

#### 子模块目标结构

- [`kernel_gen/passes/outline_device_kernel.py`](../../kernel_gen/passes/outline_device_kernel.py)
  - 目标：优先把单个待 outline 的函数改写收口成 `func.FuncOp` 的 `RewritePattern`
  - `OutlineDeviceKernelPass` 只保留 `ModulePass.apply()`、必要的 module 级前置校验与 pattern 调度
  - module 级逻辑只保留真正跨函数的预检，例如 `_device` 命名冲突、全模块候选收集一致性、避免半改写状态
  - 不再继续以单个 `run()` 承载完整 outline 主流程
- [`kernel_gen/passes/symbol_loop_hoist.py`](../../kernel_gen/passes/symbol_loop_hoist.py)
  - 目标：优先把可外提对象改成单 op `RewritePattern`
  - 各 pattern 自己判断当前 op 是否位于 `symbol.for` 内、是否满足 hoist 条件、以及如何移动到外层 block
  - `SymbolLoopHoistPass` 只保留 `ModulePass.apply()` 与最终 verify / error translate
  - 虽然本轮不为 `symbol.for` 新增 control-flow interface，但 loop 内 invariant 处理仍尽可能通过单 op pattern 和 xdsl 现成 canonicalize/CSE 组织

#### 目标验收资产

- [`expectation/pass/outline_device_kernel`](../../expectation/pass/outline_device_kernel)
- [`expectation/pass/symbol_loop_hoist`](../../expectation/pass/symbol_loop_hoist)
- [`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../test/pass/outline_device_kernel/test_outline_device_kernel.py)
- [`test/pass/test_symbol_loop_hoist.py`](../../test/pass/test_symbol_loop_hoist.py)

#### 验收必过项目

- `expectation/pass/outline_device_kernel`
- `expectation/pass/symbol_loop_hoist`
- `test/pass/outline_device_kernel/test_outline_device_kernel.py`
- `test/pass/test_symbol_loop_hoist.py`

#### 任务新建建议

- `任务类型：refactor`
- `任务目标：收口 outline-device-kernel 与 symbol-loop-hoist 的 ModulePass/pattern 实现`
- `记录文件：待管理员创建`

## 待确认项

- `无`

## 用户确认与协同约束

- `用户确认状态：已确认`
- `未确认事项：无`
- `用户确认结论：`
  - 只重构以下 pass：`nn_lowering whole family`、`buffer_results_to_out_params`、`decompass`、`outline_device_kernel`、`symbol_loop_hoist`
  - 其他 pass 不进入本轮修改面
  - `symbol.for` 本轮不引入额外 control-flow interface
  - 只考虑单 pass，不先考虑 pipeline
  - 优先直接使用 xdsl 已封好的基础设施
  - 目标 pass 继承 `ModulePass`
  - `register_decompass_rewrite(...)` 保留
  - 公开 pass 名和 registry 入口保持不变，只换实现内核
- `未确认前处理要求：不适用`
- `若用户要求至少询问 3 人：已执行 3 个对象询问`
- `询问记录 1：大闸蟹 / 已回复 / 建议拆为 S1 公共接入、S2 nn_lowering、S3 buffer-results-to-out-params + decompass、S4 outline-device-kernel + symbol-loop-hoist；并建议 S1 采用“可降级底座”口径，避免先做过早抽象。`
- `询问记录 2：睡觉小分队 / 已询问 / 当前初稿阶段尚未收到回复`
- `询问记录 3：提莫炖蘑菇 / 已询问 / 当前初稿阶段尚未收到回复`

## 复验结论（2026-04-21 02:29:04 +0800）

- 验收结论：`通过`
- 验证基线：
  - `main@34bc4f579f3f684b37a0b26ed093c8b81881cf2f`
  - 按管理员最新口径，直接在已同步到 `origin/main` 的主仓现场复验
- 复验摘要：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.lowing.nn_lowering -> exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.buffer_results_to_out_params -> exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.decompass -> exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.outline_device_kernel -> exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.symbol_loop_hoist -> exit 0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_pass_manager.py test/pass/test_pass_registry.py test/pass/nn_lowering/test_lowering_nn_lowering.py test/pass/test_buffer_results_to_out_params.py test/pass/decompass/test_softmax.py test/pass/outline_device_kernel/test_outline_device_kernel.py test/pass/test_symbol_loop_hoist.py -> 127 passed`
  - 上一轮阻断项已消除：
    - `decompass/softmax` 的函数签名 `ircheck` 文本已对齐真实打印
    - `nn_lowering` 目录级 expectation 的旧 `%[[...]]:` 签名文本与 `img2col1d(static)` attr 文本已对齐当前主线 IR 打印
  - 当前这份计划覆盖的 expectation / pytest / pass_manager / registry 验收链路均已恢复全绿，已满足归档前置条件

## 复验结论（2026-04-21 02:31:26 +0800）

- 验收结论：`通过`
- 验证基线：
  - `main@34bc4f579f3f684b37a0b26ed093c8b81881cf2f`
  - 本轮按管理员最新口径继续在主仓现场复验；当前 `HEAD` 已等于指定主线提交，无需额外更新主仓
- 复验摘要：
  - `python3 -m expectation.pass.outline_device_kernel.basic -> exit 0`
  - `python3 -m expectation.pass.outline_device_kernel -> exit 0`
  - `python3 -m expectation.pass.buffer_results_to_out_params -> exit 0`
  - `python3 -m expectation.pass.decompass -> exit 0`
  - `python3 -m expectation.pass.symbol_loop_hoist -> exit 0`
  - `python3 -m expectation.pass.lowing.nn_lowering -> exit 0`
  - `pytest -q test/pass/test_pass_manager.py test/pass/test_pass_registry.py test/pass/nn_lowering/test_lowering_nn_lowering.py test/pass/test_buffer_results_to_out_params.py test/pass/decompass/test_softmax.py test/pass/outline_device_kernel/test_outline_device_kernel.py test/pass/test_symbol_loop_hoist.py -> 128 passed`
  - 上一轮唯一阻断项 `expectation/pass/outline_device_kernel/basic.py` 的 `CASE-1` 已恢复通过；本轮补跑后未见新的回退，计划覆盖的 expectation / pytest / pass_manager / registry 验收链路继续保持全绿，已满足归档前置条件

## 参考资料

- [`tile_pass_split_green_plan.md`](../../ARCHITECTURE/plan/tile_pass_split_green_plan.md)
- [`agents/standard/计划书标准.md`](../../agents/standard/计划书标准.md)
- [`agents/standard/计划书模板.md`](../../agents/standard/计划书模板.md)
- [`/home/lfr/.local/lib/python3.12/site-packages/xdsl/passes.py`](/home/lfr/.local/lib/python3.12/site-packages/xdsl/passes.py)
- [`/home/lfr/.local/lib/python3.12/site-packages/xdsl/pattern_rewriter.py`](/home/lfr/.local/lib/python3.12/site-packages/xdsl/pattern_rewriter.py)
- [`/home/lfr/.local/lib/python3.12/site-packages/xdsl/interfaces.py`](/home/lfr/.local/lib/python3.12/site-packages/xdsl/interfaces.py)
- [`/home/lfr/.local/lib/python3.12/site-packages/xdsl/transforms/canonicalize.py`](/home/lfr/.local/lib/python3.12/site-packages/xdsl/transforms/canonicalize.py)
- [`/home/lfr/.local/lib/python3.12/site-packages/xdsl/transforms/common_subexpression_elimination.py`](/home/lfr/.local/lib/python3.12/site-packages/xdsl/transforms/common_subexpression_elimination.py)

## 归档任务记录

时间：2026-04-21 02:34 +0800
经办人：李白
任务：T-20260421-2a54626d
任务目标：将 `ARCHITECTURE/plan/selected_passes_xdsl_modulepass_refactor_green_plan.md` 归档到 `agents/codex-multi-agents/log/task_records/done_plan/2026/16/selected_passes_xdsl_modulepass_refactor_green_plan.md`，并在归档合并完成后通知管理员执行 `-done-plan`；同步清理 `ARCHITECTURE/plan/selected_passes_xdsl_modulepass_refactor_green_plan.md`。
改动：在指定 `worktree` 中新增归档文件 `agents/codex-multi-agents/log/task_records/done_plan/2026/16/selected_passes_xdsl_modulepass_refactor_green_plan.md`（内容同步自主仓本地计划书）；同步清理动作按任务口径执行，确保 `ARCHITECTURE/plan/selected_passes_xdsl_modulepass_refactor_green_plan.md` 在当前 `worktree` 与主仓本地现场均已清理。
验证：`git -C /home/lfr/kernelcode_generate/wt-20260421-archive-selected-passes-xdsl-modulepass-plan status --short --branch` -> 仅命中当前归档文件；`cmp -s /home/lfr/kernelcode_generate/ARCHITECTURE/plan/selected_passes_xdsl_modulepass_refactor_green_plan.md /home/lfr/kernelcode_generate/wt-20260421-archive-selected-passes-xdsl-modulepass-plan/agents/codex-multi-agents/log/task_records/done_plan/2026/16/selected_passes_xdsl_modulepass_refactor_green_plan.md` -> `0`（归档正文与源计划一致）；`test -f /home/lfr/kernelcode_generate/ARCHITECTURE/plan/selected_passes_xdsl_modulepass_refactor_green_plan.md` -> `1`（已清理）。
结论：当前归档 merge 收口完成，提交后继续执行 `git push`、合并后 `git fetch`、`-done`，并回报管理员继续执行 `-done-plan`。
