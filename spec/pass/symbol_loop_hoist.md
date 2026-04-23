# symbol_loop_hoist

## 功能简介

- 定义 `symbol-loop-hoist` pass 的公开合同。
- 该 pass 以 pattern 驱动方式扫描 `symbol.for` 的单 block 循环体，把满足循环不变条件的符号类 op、元数据类 `dma` op 与固定读 op 外提到所属 `symbol.for` 之前。
- 目标不是通用 LICM；公开语义只覆盖本文件列出的白名单、顺序边界、no-op 行为与固定失败短语。

## 文档信息

- 创建者：`朽木露琪亚`
- 最后一次更改：`咯咯咯`
- `spec`：[`spec/pass/symbol_loop_hoist.md`](../../spec/pass/symbol_loop_hoist.md)
- `功能实现`：[`kernel_gen/passes/symbol_loop_hoist.py`](../../kernel_gen/passes/symbol_loop_hoist.py)
- `test`：
  - [`test/pass/test_symbol_loop_hoist.py`](../../test/pass/test_symbol_loop_hoist.py)
  - [`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)

## 依赖

- pass 调度与顺序约束：[`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)
- pass 注册入口：[`spec/pass/registry.md`](../../spec/pass/registry.md)
- Symbol dialect：[`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)
- DMA dialect：[`spec/dialect/dma.md`](../../spec/dialect/dma.md)
- Tuner dialect：[`spec/dialect/tuner.md`](../../spec/dialect/tuner.md)

## 目标

- 保持公开 pass 名称 `symbol-loop-hoist` 与根路径导入 `kernel_gen.passes.symbol_loop_hoist.SymbolLoopHoistPass` / `SymbolLoopHoistError` 稳定。
- 保持 `kernel_gen.passes.lowering` 与 `kernel_gen.passes.lowering.symbol_loop_hoist` 当前对同名对象的 re-export 继续可用，不在本阶段移除。
- 保持 `build_registered_pass("symbol-loop-hoist")` 可构造出该 pass，并返回可直接执行的 xDSL `ModulePass` 实例。
- 将公开语义收口为“单 op pattern + 反复驱动直到当前 `symbol.for` 达到稳定态”，而不是把外提行为描述为不透明的手写循环。
- 明确 no-op 边界、固定失败短语与 `PassManager` 顺序合同，保证下游 `build/review` 可机械验收。

## 限制与边界

- 该 pass 只处理 `symbol.for` 的单 block 循环体；多 block body、缺少父 block 或最终 `module.verify()` 失败，都必须以 `SymbolLoopHoistVerifierError` 对外报告。
- 该 pass 不是通用 LICM，不负责：
  - 推断未列入白名单的副作用语义。
  - 改写 `func.func` 签名、创建 helper function、引入新 control-flow 结构。
  - 把整个嵌套 `symbol.for` 当作候选对象外提。
- 只有“当前候选 op 的全部 operand 都定义在当前 loop body 外部”时，才允许进入外提判定；依赖 loop iv 或 loop-carried 值的 op 必须保留在 loop 内。
- 公开白名单固定为：
  - 纯符号类：`tuner.param`、`symbol.const`、`symbol.get_dim`、`symbol.get_stride`、`symbol.add/sub/mul/div/floordiv`、`symbol.eq/ne/lt/le/gt/ge`、`symbol.to_int`、`symbol.to_float`
  - 元数据类：`dma.alloc`、`dma.view`、`dma.reshape`
  - 固定读类：`dma.slice`、`dma.load`
- `dma.alloc` 外提附加条件：
  - 若其结果值在同一 `symbol.for` 内仍被 `dma.free` 消费，必须报 `SymbolLoopHoistAllocLifetimeUnsafe`，不得外提。
- 固定读类外提附加条件：
  - `dma.slice` / `dma.load` 的来源 memory 在同一 `symbol.for` 内必须保持只读；否则报 `SymbolLoopHoistFixedReadSourceMutated`。
  - `dma.slice` 的目标 buffer 与 `dma.load` 的结果值在同一 `symbol.for` 内不得再被写回；否则报 `SymbolLoopHoistFixedReadResultRewritten`。
- 明确禁止的 invariant 副作用 op 为：`dma.deslice`、`dma.copy`、`dma.store`、`dma.fill`、`dma.free`。
  - 当这些 op 自身已经满足 loop-invariant 条件时，必须直接报 `SymbolLoopHoistSideEffectOp`，不得静默跳过。
  - 当这些 op 依赖 loop iv 时，允许继续留在 loop 内；它们是否影响固定读外提，由上面的只读检查决定。
- 稳定态规则：
  - 实现必须以“单个候选 op 匹配后立刻外提一层，再继续驱动下一轮匹配”的 pattern 语义工作，直到当前 `symbol.for` 体内不存在新的可外提候选。
  - 若 op `B` 仅依赖同一 loop 内另一个可外提 op `A` 的结果，那么在 `A` 被外提后，`B` 必须能在同一次 pass 执行中继续变为候选并被外提。
  - 外提后的 op 必须插入到所属 `symbol.for` 之前，且保持原 loop 体内能观察到的依赖顺序；未外提 op 在 loop 体内的相对顺序不得被该 pass 重新排序。
  - 当 module 不含 `symbol.for`，或某个 `symbol.for` 中不存在可外提候选时，pass 必须表现为 no-op。
- 顺序边界：
  - 当 pipeline 中存在 tile family 时，`symbol-loop-hoist` 必须位于 `tile-analysis` / `tile-elewise` / `tile-reduce` 之后，且位于 `lower-dma-memory-hierarchy` 之前。
  - 违反上述顺序时，失败由 `PassManager` 以 `SymbolLoopHoistRequiresSymbolFor` 报告；`symbol_loop_hoist.py` 本身不承担调度诊断。
  - 当 pipeline 中不存在 tile family 时，允许显式注册该 pass；此时它可以直接 no-op，不额外要求前置 tile pass。
- 固定失败短语前缀仅允许使用：
  - `SymbolLoopHoistRequiresSymbolFor`
  - `SymbolLoopHoistSideEffectOp`
  - `SymbolLoopHoistAllocLifetimeUnsafe`
  - `SymbolLoopHoistFixedReadSourceMutated`
  - `SymbolLoopHoistFixedReadResultRewritten`
  - `SymbolLoopHoistVerifierError`

## 公开接口

### `class SymbolLoopHoistError(ValueError)`

功能说明：

- 表示 `symbol-loop-hoist` 的显式失败类型。
- `str(error)` 必须以本文件约定的固定失败短语前缀开头，便于 pytest 做机械匹配。

参数说明：

- `message(str)`：错误文本。

使用示例：

```python
from kernel_gen.passes.symbol_loop_hoist import SymbolLoopHoistError

raise SymbolLoopHoistError("SymbolLoopHoistSideEffectOp: unsupported invariant op dma.deslice")
```

注意事项：

- 调用方不得依赖完整错误正文，只能依赖固定前缀与必要诊断信息。

返回与限制：

- 抛出后立即终止当前 pass。

### `class SymbolLoopHoistPass(Pass, ModulePass)`

功能说明：

- 表示 `symbol-loop-hoist` 的唯一公开 pass 类型。
- 通过 `apply(ctx, module)` 走 xDSL `ModulePass` 主入口，通过 `run(module)` 保持 legacy `Pass` 调用兼容。

参数说明：

- `name(str)`：固定为 `"symbol-loop-hoist"`。

使用示例：

```python
from xdsl.context import Context
from kernel_gen.passes.symbol_loop_hoist import SymbolLoopHoistPass

pass_obj = SymbolLoopHoistPass()
pass_obj.apply(Context(), module)
```

```python
from kernel_gen.passes.registry import build_registered_pass

pass_obj = build_registered_pass("symbol-loop-hoist")
pass_obj.apply(ctx, module)
```

注意事项：

- 公开语义要求 `apply(...)` 使用 pattern 驱动方式把单个候选 op 外提到所属 `symbol.for` 之前，并持续驱动到稳定态。
- `run(module)` 仅是兼容入口，不得与 `apply(...)` 形成两套不同语义。
- pass 执行结束后必须对 module 做校验；校验异常需统一包装为 `SymbolLoopHoistVerifierError`。

返回与限制：

- `apply(...)` 原地改写输入 `module`，返回 `None`。
- `run(module)` 返回被原地改写后的同一 `module`。

### `SymbolLoopHoistPass.apply(ctx, module)`

功能说明：

- 对输入 `ModuleOp` 执行 `symbol-loop-hoist`。
- 对每个命中的 `symbol.for` 循环体重复应用外提规则，直到该循环体达到稳定态。

参数说明：

- `ctx(Context)`：xDSL pass 上下文。
- `module(ModuleOp)`：待处理的模块。

使用示例：

```python
from xdsl.context import Context
from kernel_gen.passes.symbol_loop_hoist import SymbolLoopHoistPass

SymbolLoopHoistPass().apply(Context(), module)
```

注意事项：

- `ctx` 只作为 `ModulePass` 标准签名的一部分；该 pass 不额外定义 context 侧状态协议。
- 当 module 中没有 `symbol.for`，或命中的 `symbol.for` 没有可外提 op 时，必须直接返回且不报错。
- 若同一循环体内存在“先 hoist `symbol.get_dim`，再 hoist 依赖它的 `dma.alloc`”这类链式候选，`apply(...)` 必须在一次执行中把整条链推进到稳定态。

返回与限制：

- 返回 `None`。
- 显式失败只能抛出 `SymbolLoopHoistError`。

### `SymbolLoopHoistPass.run(module)`

功能说明：

- 提供 legacy `Pass.run(target)` 兼容入口。
- 内部语义必须与 `apply(Context(), module)` 完全一致。

参数说明：

- `module(ModuleOp)`：待处理的模块。

使用示例：

```python
from kernel_gen.passes.symbol_loop_hoist import SymbolLoopHoistPass

module = SymbolLoopHoistPass().run(module)
```

注意事项：

- `run(module)` 不得绕过 pattern 驱动主路径，也不得跳过最终校验。

返回与限制：

- 返回被原地改写后的同一 `ModuleOp`。

## 测试

- 测试文件：[`test/pass/test_symbol_loop_hoist.py`](../../test/pass/test_symbol_loop_hoist.py)
- 执行命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_symbol_loop_hoist.py`
- 测试目标：
  - 验证 `SymbolLoopHoistPass` / `SymbolLoopHoistError` 的根路径导入与 `kernel_gen.passes.lowering` re-export 可用。
  - 验证 `apply(ctx, module)` 与 `run(module)` 共用同一公开语义。
  - 验证 `symbol.const`、`symbol.get_dim + dma.alloc`、固定读 `dma.slice` 的外提主路径。
  - 验证 `SymbolLoopHoistSideEffectOp`、`SymbolLoopHoistAllocLifetimeUnsafe`、`SymbolLoopHoistFixedReadSourceMutated`、`SymbolLoopHoistFixedReadResultRewritten`、`SymbolLoopHoistVerifierError` 等固定失败前缀。
- 功能与用例清单：
  - `TC-SLH-001`：`symbol.get_dim + dma.alloc` 外提。
  - `TC-SLH-001A`：invariant `symbol.const` 外提。
  - `TC-SLH-001B`：`apply(ctx, module)` 保持 `ModulePass` 入口。
  - `TC-SLH-002`：固定窗口只读 `dma.slice` 外提。
  - `TC-SLH-003`：invariant `dma.deslice` 报 `SymbolLoopHoistSideEffectOp`。
  - `TC-SLH-004`：loop 内释放的 `dma.alloc` 报 `SymbolLoopHoistAllocLifetimeUnsafe`。
  - `TC-SLH-005`：固定读结果被改写时报 `SymbolLoopHoistFixedReadResultRewritten`。
  - `TC-SLH-006`：固定读来源被改写时报 `SymbolLoopHoistFixedReadSourceMutated`。
  - `TC-SLH-007`：校验失败包装为 `SymbolLoopHoistVerifierError`。

- 测试文件：[`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)
- 执行命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_pass_manager.py -k "symbol_loop_hoist or symbol-loop-hoist"`
- 测试目标：
  - 验证 `symbol-loop-hoist` 在缺少 tile family 时允许加入 pipeline 并可作为 no-op 执行。
  - 验证 `symbol-loop-hoist` 位于 tile family 之前、位于 `lower-dma-memory-hierarchy` 之后时会触发 `SymbolLoopHoistRequiresSymbolFor`。
  - 验证 `symbol-loop-hoist` 位于 `tile-reduce` 之后、`lower-dma-memory-hierarchy` 之前时顺序合法。
- 功能与用例清单：
  - `TC-PASS-013B`：插在 `tile-analysis` 与 `tile-reduce` 之间时报错。
  - `TC-PASS-015`：缺少 tile family 时允许 no-op。
  - `TC-PASS-016` / `TC-PASS-016A`：位于 tile family 之前时报错。
  - `TC-PASS-017`：位于 `lower-dma-memory-hierarchy` 之后时报错。
  - `TC-PASS-017A`：位于 `tile-reduce` 之后且位于 `lower-dma-memory-hierarchy` 之前时顺序合法。
