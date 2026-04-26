# buffer_results_to_out_params.md

## 功能简介

- 定义 `buffer-results-to-out-params` pass 的公开合同。
- 该 pass 在 IR 层把 `func.func` 中作为函数返回值返回的 `memory` 结果，改写成函数最前置的输入 out 参数。
- 当前公开口径已经收口到：支持 single / multi `memory` results 与 mixed `memory + scalar` returns，模块内可解析 `func.call` 会同步改写成“caller 显式 out 实参 + 保留 scalar result 的新 `func.call`”，并要求下游 `gen_kernel` 闭环前不得保留旧 `memory return` ABI 或半改写状态。

## API 列表

- `PassContractError(message: str)`
- `BufferResultsToOutParamsPass`
  - `—— apply(ctx: Context, module: ModuleOp)`
  - `—— run(module: object) -> ModuleOp`
- `BufferResultsToOutParamsCallPattern(targets: dict[str, RewriteTarget])`
  - `—— match_and_rewrite(op: func.CallOp, rewriter: PatternRewriter)`
- `BufferResultsToOutParamsFuncPattern(targets: dict[str, RewriteTarget])`
  - `—— match_and_rewrite(op: func.FuncOp, rewriter: PatternRewriter)`
- `get_buffer_results_to_out_params_pass_patterns(targets: dict[str, RewriteTarget]) -> list[RewritePattern]`

## 文档信息

- 创建者：`朽木露琪亚`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/pass/buffer_results_to_out_params.md`](buffer_results_to_out_params.md)
- `功能实现`：
  - [`kernel_gen/passes/buffer_results_to_out_params.py`](../../../kernel_gen/passes/buffer_results_to_out_params.py)
  - [`kernel_gen/passes/lowering/__init__.py`](../../../kernel_gen/passes/lowering/__init__.py)
- `test`：[`test/pass/test_buffer_results_to_out_params.py`](../../../test/pass/test_buffer_results_to_out_params.py)

## 依赖

- [`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)
- [`kernel_gen/passes/pass_manager.py`](../../../kernel_gen/passes/pass_manager.py)
- lowered IR 中的 `func.func` / `func.return` / `func.call`

## 目标

- 新增 `BufferResultsToOutParamsPass`
- 固定公开名字：`buffer-results-to-out-params`
- canonical import path 固定为 `kernel_gen.passes.buffer_results_to_out_params`
- 把函数返回中的 `memory` 结果改写成最前置输入 out 参数
- 支持单个/多个 `memory` 返回值改写为 `arg0/arg1/...`
- 支持 mixed `memory + scalar` returns：`memory` 结果前置为 out 参数，`scalar` 结果保留为返回值
- 明确写死多个 output 的前置顺序合同：
  - 第 1 个 output -> `arg0`
  - 第 2 个 output -> `arg1`
  - 依次类推
- 对模块内可解析 `func.call` 做同步改写：移除 `memory` result，保留 `scalar` result
- 作为 `gen_kernel` 闭环前置合法化：对旧 `memory return` ABI 与半改写状态必须显式失败

## 限制与边界

- 本轮只收口 pass 自身合同和最小实现骨架。
- 当前公开范围要求支持：
  - 单个/多个 `memory` 返回值改写
  - mixed `memory + scalar` returns（`memory` 改写、`scalar` 保留）
  - 模块内可解析 `func.call` 的同步改写（`memory` result 移除、`scalar` result 保留）
- 当前仍不要求支持：
  - external declaration
  - multi-block/CFG 分支
  - 返回值个数与函数签名不一致
- 对于当前未覆盖而又无法安全同步改写的场景，必须显式报错，不允许静默保留双口径。
- 公开 `Pass` 名保持 `BufferResultsToOutParams*` 前缀。
- 公开错误类型统一使用 `kernel_gen.passes.PassContractError`。
- `BufferResultsToOutParamsCallPattern`、`BufferResultsToOutParamsFuncPattern` 与 `get_buffer_results_to_out_params_pass_patterns(...)` 也属于当前公开接口。
- `OutputSignature`、`RewriteTarget` 只作为文件内实现细节存在，不属于公开 API；实现与测试都不得跨文件直接依赖这些 helper 类名。

## 必须禁止的旧口径

- 不允许只改 `func.func` 输入/输出签名，不改 `func.return`
- 不允许把前置 out 参数和同一个 `memory` 返回值同时保留在函数合同里
- 不允许对 external declaration 做半改写
- 不允许把已经可同步改写成功的模块内 caller/callee 继续写成必须失败
- 不允许先改 callee 签名和 `func.return`，再把 caller 静默留在旧 `func.call -> memory result` 口径
- 不允许出现“改了 out 参数但仍保留 `memory` return”的半改写 ABI

## 公开接口

### `class PassContractError(ValueError)`

- 功能说明：`kernel_gen.passes` 共享的显式错误类型。
- 参数说明：
  - `message: str`：错误文本。
- 使用示例：`raise PassContractError("external declaration is not supported")`
- 注意事项：所有“半改半留必须失败”的场景都应统一抛出该错误。
- 返回与限制：抛错即终止当前 pass。

### `class BufferResultsToOutParamsPass(Pass)`

- 功能说明：将函数返回中的 `memory` 结果改写为最前置 out 参数。
- 参数说明：无。
- 使用示例：

```python
from kernel_gen.passes.buffer_results_to_out_params import BufferResultsToOutParamsPass

module = BufferResultsToOutParamsPass().run(module)
```

- 注意事项：
  - pass 以 `ModuleOp` 为输入。
  - 当前公开范围若遇到 external declaration、multi-block、返回值个数不一致或无法安全同步改写的 callsite，必须显式报错。
  - 半改写 ABI（例如保留 `memory return`、caller/callee 口径不一致）必须显式报错。
- 返回与限制：返回改写后的同一 `ModuleOp`。

## 实现约束

- `kernel_gen/passes/buffer_results_to_out_params.py` 中的公开 pattern 名固定为 `BufferResultsToOutParamsCallPattern`、`BufferResultsToOutParamsFuncPattern`。
- 不再使用带私有前缀的 `_BufferResultsToOutParamsCallPattern`、`_BufferResultsToOutParamsFuncPattern`。
- `BufferResultsToOutParamsPass.apply()` 必须通过 `get_buffer_results_to_out_params_pass_patterns(...)` 组装 pattern，不再在 `apply()` 内手写重复列表。

### `class BufferResultsToOutParamsCallPattern(RewritePattern)`

- 功能说明：处理命中的旧 `memory result` `func.call`，把 caller 改写为显式 out 实参形式。
- 参数说明：
  - `targets: dict[str, RewriteTarget]`：待改写 callee 的签名信息。
- 使用示例：

```python
from kernel_gen.passes.buffer_results_to_out_params import BufferResultsToOutParamsCallPattern

pattern = BufferResultsToOutParamsCallPattern(targets)
```

- 注意事项：
  - 只处理模块内可解析且命中 target 的 `func.call`。
  - 若 callsite 不再返回 `memory` result，则 pattern 不应重复触发。
- 返回与限制：仅作为 rewrite pattern 使用，不单独执行模块遍历。

### `class BufferResultsToOutParamsFuncPattern(RewritePattern)`

- 功能说明：处理命中的 `func.func`，把 `memory` 返回值改写为最前置 out 参数。
- 参数说明：
  - `targets: dict[str, RewriteTarget]`：待改写函数的签名信息。
- 使用示例：

```python
from kernel_gen.passes.buffer_results_to_out_params import BufferResultsToOutParamsFuncPattern

pattern = BufferResultsToOutParamsFuncPattern(targets)
```

- 注意事项：
  - 只处理 target 集合中仍保留旧 `memory` outputs 的函数。
  - 不应对已经改写完成的函数重复触发。
- 返回与限制：仅作为 rewrite pattern 使用，不单独执行模块遍历。

### `def get_buffer_results_to_out_params_pass_patterns(targets) -> list[RewritePattern]`

- 功能说明：返回当前 pass 公开使用的 pattern 列表。
- 参数说明：
  - `targets: dict[str, RewriteTarget]`：待改写函数与 callsite 的统一签名信息。
- 使用示例：

```python
from kernel_gen.passes.buffer_results_to_out_params import (
    get_buffer_results_to_out_params_pass_patterns,
)

patterns = get_buffer_results_to_out_params_pass_patterns(targets)
```

- 注意事项：
  - 返回顺序固定为 `BufferResultsToOutParamsCallPattern` 在前、`BufferResultsToOutParamsFuncPattern` 在后。
  - `BufferResultsToOutParamsPass.apply()` 与外部组合逻辑都应复用该入口。
- 返回与限制：返回当前 pass 使用的 pattern 实例列表。

## 导入与兼容边界

- caller 的 canonical public path 固定为：

```python
from kernel_gen.passes import PassContractError
from kernel_gen.passes.buffer_results_to_out_params import (
    BufferResultsToOutParamsPass,
    BufferResultsToOutParamsCallPattern,
    BufferResultsToOutParamsFuncPattern,
    get_buffer_results_to_out_params_pass_patterns,
)
```

- `kernel_gen.passes.lowering.buffer_results_to_out_params` 属于旧 compat 模块；从 `S2` 起导入必须以 `ModuleNotFoundError` 失败。
- `kernel_gen.passes` package 若仍保留同名符号的 re-export，只能视为迁移辅助，不作为本阶段验收入口。
- [`test/pass/test_buffer_results_to_out_params.py`](../../../test/pass/test_buffer_results_to_out_params.py) 必须同时证明“canonical import 成功 + 旧 lowering 模块失败”；[`expectation/pass/buffer_results_to_out_params`](../../../expectation/pass/buffer_results_to_out_params) 只作合同验收资产单列，不能再依赖已移除的兼容错误名。

## 最小改写合同

### 单个 memory result

改写前：

```text
func.func @single(%src: !nn.memory<...>) -> (!nn.memory<...>) {
  ...
  func.return %0
}
```

改写后：

```text
func.func @single(%arg0: !nn.memory<...>, %src: !nn.memory<...>) {
  ...
  func.return
}
```

必须满足：

- 新 out 参数前置到最前面
- 新前置参数名固定为 `arg0`
- 原 `memory` 返回类型从 `function_type.outputs` 中移除
- `func.return` 变为空 return

### 多个 outputs 的固定顺序

- 第 1 个 `memory` output -> `arg0`
- 第 2 个 `memory` output -> `arg1`
- 依次类推
- 禁止多 output 场景未来再引入其他前置顺序或双口径并存。

### 多个 memory results

改写前：

```text
func.func @multi(%src: !nn.memory<...>) -> (!nn.memory<...>, !nn.memory<...>) {
  ...
  func.return %0, %1
}
```

改写后：

```text
func.func @multi(%arg0: !nn.memory<...>, %arg1: !nn.memory<...>, %src: !nn.memory<...>) {
  ...
  func.return
}
```

必须满足：

- 多个 `memory` 结果按 `arg0/arg1/...` 前置顺序改写
- `func.return` 变为空 return

### mixed `memory + scalar` returns

改写前：

```text
func.func @mixed(%src: !nn.memory<...>, %cond: i1) -> (!nn.memory<...>, i1) {
  ...
  func.return %0, %flag
}
```

改写后：

```text
func.func @mixed(%arg0: !nn.memory<...>, %src: !nn.memory<...>, %cond: i1) -> i1 {
  ...
  func.return %flag
}
```

必须满足：

- `memory` 结果前置为 out 参数
- `scalar` 结果保留在 `func.return` 与函数返回类型中

### external declaration

- 若函数是 external declaration 且返回值中包含 `memory`，pass 必须显式失败。
- 错误消息必须包含 `external declaration` 或等价关键字。

### 模块内 callsite 同步改写

- 若模块内存在可解析的 `caller + callee`，且 callee 命中 `memory` 返回值改写，pass 必须同步把 caller 侧旧 `func.call` 改写成“显式 out 实参 + 移除 `memory` result、保留 `scalar` result 的新 `func.call`”。
- caller 侧必须先补 out buffer，并把旧 memory call result SSA 全量替换为 caller 显式 out buffer。
- 当前公开成功口径下，不再把这类模块内可解析 callsite 写成必须失败。

改写前：

```text
%0 = func.call @add(%lhs, %rhs) : (...) -> (!nn.memory<...>)
use %0
```

改写后：

```text
%out = dma.alloc ...
func.call @add(%out, %lhs, %rhs) : (...) -> ()
use %out
```

必须满足：

- 新 `func.call` 第一个实参固定传 caller 侧显式 out buffer
- 旧 memory call result SSA 不再存在
- caller 对旧 result 的后续使用必须改绑到 caller 侧 out buffer

当存在 mixed returns 时，改写前：

```text
%0, %flag = func.call @mixed(%src, %cond) : (...) -> (!nn.memory<...>, i1)
```

改写后：

```text
%out = dma.alloc ...
%flag = func.call @mixed(%out, %src, %cond) : (...) -> i1
```

必须满足：

- `memory` result 被移除并以 caller 显式 out buffer 替代
- `scalar` result 仍保留为 `func.call` 的返回值

### 半改写 ABI 拒绝

- 若 `func.func` 已包含前置 out 参数，但仍保留 `memory` return，必须显式失败。
- 若 `caller`/`callee` 在 `memory` 返回口径上不一致（例如 caller 仍消费旧 `memory` result），必须显式失败。
- 错误消息必须包含 `half-rewritten`、`half rewritten` 或等价关键字。

## 测试

- 测试文件：[`test/pass/test_buffer_results_to_out_params.py`](../../../test/pass/test_buffer_results_to_out_params.py)
- 验证命令：
  - `pytest -q test/pass/test_buffer_results_to_out_params.py`
  - `pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k 'buffer_results_to_out_params or half_rewritten'`
- 测试目标：
  - 锁定 canonical import path `kernel_gen.passes.buffer_results_to_out_params` 可用。
  - 锁定 `kernel_gen.passes.lowering.buffer_results_to_out_params` 旧模块导入失败。
  - 锁定单 / 多 `memory` result、mixed returns、模块内 callsite 同步改写与 pipeline 顺序边界。

## 功能与用例清单

- `BROTP-001`：单个 `memory` 返回值会被改写为最前置 `arg0`，并清空 `func.return`。（`test_rewrite_single_memory_result_to_front_out_param`）
- `BROTP-002`：external declaration 不允许半改写，必须显式报错。（`test_rewrite_rejects_external_declaration`）
- `BROTP-003`：模块内 caller/callee 会同步改写成“caller 显式 out 实参 + 零 result `func.call`”，旧 memory call result SSA 不再可被消费。（`test_rewrite_callsite_replaces_old_memory_result_ssa`）
- `BROTP-004`：在 lowering pipeline 中，`BufferResultsToOutParamsPass` 固定运行在 `NnLoweringPass` 之后。（`test_pass_manager_runs_lower_then_buffer_results_to_out_params`、`test_pipeline_position_pass_manager_runs_lower_then_buffer_results_to_out_params`）
- `BROTP-005`：[`test/pass/test_buffer_results_to_out_params.py`](../../../test/pass/test_buffer_results_to_out_params.py) 锁死“callee 的 memory result -> 前置 arg0；caller 补 out 实参；`func.call` 零 memory result”的公开口径。
- `BROTP-006`：多个 `memory` results 固定改写为 `arg0/arg1/...`，caller 侧 `func.call` 同步替换为显式 out 实参。（`test_rewrite_multiple_memory_results_to_arg0_arg1`）
- `BROTP-007`：mixed `memory + scalar` returns 改写后，caller 侧 `func.call` 仅保留 scalar result，旧 memory result SSA 被替换。（`test_rewrite_mixed_memory_and_scalar_results_preserves_scalar_return`）
- `BROTP-008`：`test/pass/test_buffer_results_to_out_params.py` 需要同时证明 canonical import path 成功、`kernel_gen.passes.lowering.buffer_results_to_out_params` 旧模块失败，且不得用 package re-export 代替该证明。
