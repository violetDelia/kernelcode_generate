# symbol_loop_hoist

## 功能简介

- 定义 `symbol-loop-hoist` pass 的公开合同。
- 该 pass 以 pattern 驱动方式扫描 `symbol.for` 的单 block 循环体，把满足循环不变条件的受支持符号类 op 外提到所属 `symbol.for` 之前。
- 目标不是通用 LICM；公开语义只覆盖本文件列出的白名单、顺序边界、no-op 行为与最小错误包装。

## API 列表

- `class SymbolLoopHoistPass()`
  - `name: str`
  - `apply(ctx: Context, module: ModuleOp) -> None`
- `class SymbolConstHoistPattern()`
- `class TunerParamHoistPattern()`
- `class SymbolGetDimHoistPattern()`
- `class SymbolGetStrideHoistPattern()`
- `class SymbolAddHoistPattern()`
- `class SymbolSubHoistPattern()`
- `class SymbolMulHoistPattern()`
- `class SymbolDivHoistPattern()`
- `class SymbolFloorDivHoistPattern()`
- `get_symbol_loop_hoist_patterns() -> list[RewritePattern]`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/pass/symbol_loop_hoist.md`](../../spec/pass/symbol_loop_hoist.md)
- `功能实现`：[`kernel_gen/passes/symbol_loop_hoist.py`](../../kernel_gen/passes/symbol_loop_hoist.py)
- `test`：
  - [`test/passes/test_symbol_loop_hoist.py`](../../test/passes/test_symbol_loop_hoist.py)
  - [`test/passes/test_pass_manager.py`](../../test/passes/test_pass_manager.py)

## 依赖

- pass 调度与顺序约束：[`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)
- pass 注册入口：[`spec/pass/registry.md`](../../spec/pass/registry.md)
- Symbol dialect：[`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)
- Tuner dialect：[`spec/dialect/tuner.md`](../../spec/dialect/tuner.md)

## 目标

- 保持公开 pass 名称 `symbol-loop-hoist` 与根路径导入 `kernel_gen.passes.symbol_loop_hoist.SymbolLoopHoistPass` 稳定；失败类型统一使用 `kernel_gen.core.error.KernelCodeError`。
- 保持 `kernel_gen.passes.lowering` 与 `kernel_gen.passes.lowering.symbol_loop_hoist` 当前对同名对象的 re-export 继续可用，不在本阶段移除。
- 保持 `build_registered_pass("symbol-loop-hoist")` 可构造出该 pass，并返回可直接执行的 xDSL `ModulePass` 实例。
- 将公开语义收口为“每种受支持 op 一个公开 RewritePattern + 反复驱动直到当前 `symbol.for` 达到稳定态”，而不是把外提行为描述为不透明的手写循环。
- 明确 no-op 边界、固定失败短语与 `PassManager` 顺序合同，保证下游 `build/review` 可机械验收。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 该 pass 只处理 `symbol.for` 的单 block 循环体；多 block body、缺少父 block 或最终 `module.verify()` 失败，都必须以 `SymbolLoopHoistVerifierError` 对外报告。
- 该 pass 不是通用 LICM，不负责：
  - 推断未列入白名单的副作用语义。
  - 改写 `func.func` 签名、创建 helper function、引入新 control-flow 结构。
  - 把整个嵌套 `symbol.for` 当作候选对象外提。
- 当前文件的公开 API 仅限本 spec 列出的 pass、错误类型、公开 pattern 与 getter；外提判定逻辑属于各公开 pattern 自身实现的一部分，不额外公开文件级 helper 供跨文件调用。
- 只有“当前候选 op 的全部 operand 都定义在当前 loop body 外部”时，才允许进入外提判定；依赖 loop iv 或 loop-carried 值的 op 必须保留在 loop 内。
- 公开白名单固定为：
  - `tuner.param`
  - `symbol.const`
  - `symbol.get_dim`
  - `symbol.get_stride`
  - `symbol.add/sub/mul/div/floordiv`
- 未列入白名单的 op 一律不由本 pass 主动处理：
  - 不承诺外提
  - 不承诺显式错误
  - 默认保持原位不动
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
  - `SymbolLoopHoistVerifierError`

### 失败类型

- 功能说明：

- 表示 `symbol-loop-hoist` 的显式失败类型。
- 最终 `module.verify()` 失败必须统一包装；`str(error)` 必须以本文件约定的固定失败短语前缀开头，便于 pytest 做机械匹配。

- 参数：

- `message: str`：错误文本。

- 使用示例：

```python
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError

raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "SymbolLoopHoistVerifierError: value")
```

- 注意事项：

- 调用方不得依赖完整错误正文，只能依赖固定前缀与必要诊断信息。

- 返回值：

- 抛出后立即终止当前 pass。

### `class SymbolLoopHoistPass()`

- 功能说明：

- 表示 `symbol-loop-hoist` 的唯一公开 pass 类型。
- 通过 `apply(ctx, module)` 走 xDSL `ModulePass` 主入口，不再提供单 pass `run(module)` 兼容入口。
- 同时公开每种受支持 op 对应的 pattern 类与 pattern getter。

- 参数：

- 无构造参数。

- 使用示例：

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

```python
from kernel_gen.passes.symbol_loop_hoist import get_symbol_loop_hoist_patterns

patterns = get_symbol_loop_hoist_patterns()
```

- 注意事项：

- 公开语义要求 `apply(...)` 使用 pattern 驱动方式把单个候选 op 外提到所属 `symbol.for` 之前，并持续驱动到稳定态。
- 不得恢复 `run(module)` 或与 `apply(...)` 形成两套不同语义。
- pass 执行结束后必须对 module 做校验；校验异常需统一包装为 `SymbolLoopHoistVerifierError`。

- 返回值：

- `apply(...)` 原地改写输入 `module`，返回 `None`。
- 不提供返回式 `run(module)` 执行入口。

#### `name: str`

- 功能说明：

- 暴露当前 pass 的稳定公开名称。

- 使用示例：

```python
from kernel_gen.passes.symbol_loop_hoist import SymbolLoopHoistPass

assert SymbolLoopHoistPass.name == "symbol-loop-hoist"
```

- 返回值：

- 固定为 `"symbol-loop-hoist"`。

#### `apply(ctx: Context, module: ModuleOp) -> None`

- 功能说明：

- 对输入 `ModuleOp` 执行 `symbol-loop-hoist`。
- 对每个命中的 `symbol.for` 循环体重复应用外提规则，直到该循环体达到稳定态。

- 参数：

- `ctx: Context`：xDSL pass 上下文。
- `module: ModuleOp`：待处理的模块。

- 使用示例：

```python
from xdsl.context import Context
from kernel_gen.passes.symbol_loop_hoist import SymbolLoopHoistPass

SymbolLoopHoistPass().apply(Context(), module)
```

- 注意事项：

- `ctx` 只作为 `ModulePass` 标准签名的一部分；该 pass 不额外定义 context 侧状态协议。
- 当 module 中没有 `symbol.for`，或命中的 `symbol.for` 没有可外提 op 时，必须直接返回且不报错。
- 若同一循环体内存在“先 hoist `symbol.const`，再 hoist 依赖它的 `symbol.add`”这类链式候选，`apply(...)` 必须在一次执行中把整条链推进到稳定态。

- 返回值：

- 返回 `None`。
- 显式失败只能抛出 `KernelCodeError`。

#### `apply(ctx: Context, module: ModuleOp) -> None`

- 功能说明：

- 不再提供 legacy `Pass.run(target)` 兼容入口。
- 内部语义只由 `apply(ctx, module)` 承载。

- 参数：

- `module: ModuleOp`：待处理的模块。

- 使用示例：

```python
from kernel_gen.passes.symbol_loop_hoist import SymbolLoopHoistPass

SymbolLoopHoistPass().apply(Context(), module)
```

- 注意事项：

- 不得恢复 `run(module)` 绕过 pattern 驱动主路径或跳过最终校验。

- 返回值：

- 返回被原地改写后的同一 `ModuleOp`。

### `class SymbolConstHoistPattern()`

- 功能说明：

- 处理 `symbol.const` 的循环不变外提。

### `class TunerParamHoistPattern()`

- 功能说明：

- 处理 `tuner.param` 的循环不变外提。

### `class SymbolGetDimHoistPattern()`

- 功能说明：

- 处理 `symbol.get_dim` 的循环不变外提。

### `class SymbolGetStrideHoistPattern()`

- 功能说明：

- 处理 `symbol.get_stride` 的循环不变外提。

### `class SymbolAddHoistPattern()`

- 功能说明：

- 处理 `symbol.add` 的循环不变外提。

### `class SymbolSubHoistPattern()`

- 功能说明：

- 处理 `symbol.sub` 的循环不变外提。

### `class SymbolMulHoistPattern()`

- 功能说明：

- 处理 `symbol.mul` 的循环不变外提。

### `class SymbolDivHoistPattern()`

- 功能说明：

- 处理 `symbol.div` 的循环不变外提。

### `class SymbolFloorDivHoistPattern()`

- 功能说明：

- 处理 `symbol.floordiv` 的循环不变外提。

### `get_symbol_loop_hoist_patterns() -> list[RewritePattern]`

当前公开的 pattern 类固定为：

- `SymbolConstHoistPattern`
- `TunerParamHoistPattern`
- `SymbolGetDimHoistPattern`
- `SymbolGetStrideHoistPattern`
- `SymbolAddHoistPattern`
- `SymbolSubHoistPattern`
- `SymbolMulHoistPattern`
- `SymbolDivHoistPattern`
- `SymbolFloorDivHoistPattern`

- 功能说明：

- 公开返回 `symbol-loop-hoist` 当前使用的 pattern 列表。
- 顺序即为当前 pass 的 pattern 应用顺序。

- 使用示例：

```python
from kernel_gen.passes.symbol_loop_hoist import (
    SymbolConstHoistPattern,
    get_symbol_loop_hoist_patterns,
)

patterns = get_symbol_loop_hoist_patterns()
assert isinstance(patterns[0], SymbolConstHoistPattern)
```

## API详细说明

### `class SymbolLoopHoistPass()`

- api：`class SymbolLoopHoistPass()`
- 参数：无。
- 返回值：`SymbolLoopHoistPass` 实例。
- 使用示例：

  ```python
  symbol_loop_hoist_pass = SymbolLoopHoistPass()
  ```
- 功能说明：定义 `SymbolLoopHoistPass` pass 对象。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `name: str`

- api：`name: str`
- 参数：无。
- 返回值：`str` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  from kernel_gen.passes.symbol_loop_hoist import SymbolLoopHoistPass

  assert SymbolLoopHoistPass.name == "symbol-loop-hoist"
  ```
- 功能说明：执行 `str`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `apply(ctx: Context, module: ModuleOp) -> None`

- api：`apply(ctx: Context, module: ModuleOp) -> None`
- 参数：
  - `ctx`：公开上下文对象，提供代码生成、emit、pass 或工具执行所需的配置与状态；类型 `Context`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `module`：模块级 IR 对象，作为 pass、校验或代码生成的处理主体；类型 `ModuleOp`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  apply(ctx=ctx, module=module)
  ```
- 功能说明：执行 `apply`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `class SymbolConstHoistPattern()`

- api：`class SymbolConstHoistPattern()`
- 参数：无。
- 返回值：`SymbolConstHoistPattern` 实例。
- 使用示例：

  ```python
  symbol_const_hoist_pattern = SymbolConstHoistPattern()
  ```
- 功能说明：定义 `SymbolConstHoistPattern` rewrite pattern 对象。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `class TunerParamHoistPattern()`

- api：`class TunerParamHoistPattern()`
- 参数：无。
- 返回值：`TunerParamHoistPattern` 实例。
- 使用示例：

  ```python
  tuner_param_hoist_pattern = TunerParamHoistPattern()
  ```
- 功能说明：定义 `TunerParamHoistPattern` rewrite pattern 对象。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `class SymbolGetDimHoistPattern()`

- api：`class SymbolGetDimHoistPattern()`
- 参数：无。
- 返回值：`SymbolGetDimHoistPattern` 实例。
- 使用示例：

  ```python
  symbol_get_dim_hoist_pattern = SymbolGetDimHoistPattern()
  ```
- 功能说明：定义 `SymbolGetDimHoistPattern` rewrite pattern 对象。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `class SymbolGetStrideHoistPattern()`

- api：`class SymbolGetStrideHoistPattern()`
- 参数：无。
- 返回值：`SymbolGetStrideHoistPattern` 实例。
- 使用示例：

  ```python
  symbol_get_stride_hoist_pattern = SymbolGetStrideHoistPattern()
  ```
- 功能说明：定义 `SymbolGetStrideHoistPattern` rewrite pattern 对象。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `class SymbolAddHoistPattern()`

- api：`class SymbolAddHoistPattern()`
- 参数：无。
- 返回值：`SymbolAddHoistPattern` 实例。
- 使用示例：

  ```python
  symbol_add_hoist_pattern = SymbolAddHoistPattern()
  ```
- 功能说明：定义 `SymbolAddHoistPattern` rewrite pattern 对象。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `class SymbolSubHoistPattern()`

- api：`class SymbolSubHoistPattern()`
- 参数：无。
- 返回值：`SymbolSubHoistPattern` 实例。
- 使用示例：

  ```python
  symbol_sub_hoist_pattern = SymbolSubHoistPattern()
  ```
- 功能说明：定义 `SymbolSubHoistPattern` rewrite pattern 对象。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `class SymbolMulHoistPattern()`

- api：`class SymbolMulHoistPattern()`
- 参数：无。
- 返回值：`SymbolMulHoistPattern` 实例。
- 使用示例：

  ```python
  symbol_mul_hoist_pattern = SymbolMulHoistPattern()
  ```
- 功能说明：定义 `SymbolMulHoistPattern` rewrite pattern 对象。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `class SymbolDivHoistPattern()`

- api：`class SymbolDivHoistPattern()`
- 参数：无。
- 返回值：`SymbolDivHoistPattern` 实例。
- 使用示例：

  ```python
  symbol_div_hoist_pattern = SymbolDivHoistPattern()
  ```
- 功能说明：定义 `SymbolDivHoistPattern` rewrite pattern 对象。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `class SymbolFloorDivHoistPattern()`

- api：`class SymbolFloorDivHoistPattern()`
- 参数：无。
- 返回值：`SymbolFloorDivHoistPattern` 实例。
- 使用示例：

  ```python
  symbol_floor_div_hoist_pattern = SymbolFloorDivHoistPattern()
  ```
- 功能说明：定义 `SymbolFloorDivHoistPattern` rewrite pattern 对象。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `get_symbol_loop_hoist_patterns() -> list[RewritePattern]`

- api：`get_symbol_loop_hoist_patterns() -> list[RewritePattern]`
- 参数：无。
- 返回值：`list[RewritePattern]`。
- 使用示例：

  ```python
  result = get_symbol_loop_hoist_patterns()
  ```
- 功能说明：读取 `symbol_loop_hoist_patterns`。
- 注意事项：该接口只读取公开状态；返回对象的内部可变结构不作为额外公开合同。

## 测试

- 测试文件：
  - `test/passes/test_pass_manager.py`
  - `test/passes/test_symbol_loop_hoist.py`
- 执行命令：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_symbol_loop_hoist.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_pass_manager.py -k "symbol_loop_hoist or symbol-loop-hoist"`

### 测试目标

- 验证 `spec/pass/symbol_loop_hoist.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证 SymbolDim、shape、stride、axis 或 symbol IR 语义。
- 验证公开导入、注册名、CLI 或命名空间入口只暴露 spec 定义的 API。
- 验证 cost kind、tuning 属性和调优 IR 输出。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-PASS-SYMBOL-LOOP-HOIST-001 | 符号语义 | `symbol.get_dim` 外提。 | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `TC-SLH-001`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“`symbol.get_dim` 外提。”场景。 | `TC-SLH-001` |
| TC-PASS-SYMBOL-LOOP-HOIST-002 | 符号语义 | invariant `symbol.const` 外提。 | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `TC-SLH-001A`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“invariant `symbol.const` 外提。”场景。 | `TC-SLH-001A` |
| TC-PASS-SYMBOL-LOOP-HOIST-003 | 公开入口 | 公开 pattern 与 getter 可导入且顺序稳定。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `TC-SLH-001B`。 | 公开入口在“公开 pattern 与 getter 可导入且顺序稳定。”场景下可导入、构造、注册或按名称发现。 | `TC-SLH-001B` |
| TC-PASS-SYMBOL-LOOP-HOIST-004 | 成本/调优 | `tuner.param` 外提。 | 准备公开 cost kind、kernel/DMA 参数或 tuning IR 输入。 | 运行 `TC-SLH-001C`。 | 成本函数、tuning 属性或 cost IR 输出体现“`tuner.param` 外提。”场景。 | `TC-SLH-001C` |
| TC-PASS-SYMBOL-LOOP-HOIST-005 | 符号语义 | `symbol.add/sub/mul/div/floordiv` 外提。 | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `TC-SLH-001D`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“`symbol.add/sub/mul/div/floordiv` 外提。”场景。 | `TC-SLH-001D` |
| TC-PASS-SYMBOL-LOOP-HOIST-006 | pass 改写 | `apply(ctx, module)` 保持 `ModulePass` 入口。 | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `TC-SLH-001E`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`apply(ctx, module)` 保持 `ModulePass` 入口。”场景。 | `TC-SLH-001E` |
| TC-PASS-SYMBOL-LOOP-HOIST-007 | 公开入口 | loop-carried 依赖的符号 op 保持原位。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `TC-SLH-002`。 | 公开入口在“loop-carried 依赖的符号 op 保持原位。”场景下可导入、构造、注册或按名称发现。 | `TC-SLH-002` |
| TC-PASS-SYMBOL-LOOP-HOIST-008 | 边界/异常 | 校验失败包装为 `SymbolLoopHoistVerifierError`。 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `TC-SLH-007`。 | “校验失败包装为 `SymbolLoopHoistVerifierError`。”场景按公开错误语义失败或被拒绝。 | `TC-SLH-007` |
| TC-PASS-SYMBOL-LOOP-HOIST-012 | pass 改写 | 验证 `symbol-loop-hoist` 在缺少 tile family 时允许加入 pipeline 并可作为 no-op 执行。 | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `pytest -q test/passes/test_pass_manager.py -k "symbol_loop_hoist or symbol-loop-hoist"`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“验证 `symbol-loop-hoist` 在缺少 tile family 时允许加入 pipeline 并可作为 no-op 执行。”场景。 | pytest -q test/passes/test_pass_manager.py -k "symbol_loop_hoist or symbol-loop-hoist" |
| TC-PASS-SYMBOL-LOOP-HOIST-013 | 边界/异常 | 验证 `symbol-loop-hoist` 位于 tile family 之前、位于 `lower-dma-memory-hierarchy` 之后时会触发 `SymbolLoopHoistRequiresSymbolFor`。 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `pytest -q test/passes/test_pass_manager.py -k "symbol_loop_hoist or symbol-loop-hoist"`。 | “验证 `symbol-loop-hoist` 位于 tile family 之前、位于 `lower-dma-memory-hierarchy` 之后时会触发 `SymbolLoopHoistRequiresSymbolFor`。”场景按公开错误语义失败或被拒绝。 | pytest -q test/passes/test_pass_manager.py -k "symbol_loop_hoist or symbol-loop-hoist" |
| TC-PASS-SYMBOL-LOOP-HOIST-014 | pass 改写 | 验证 `symbol-loop-hoist` 位于 `tile-reduce` 之后、`lower-dma-memory-hierarchy` 之前时顺序合法。 | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `pytest -q test/passes/test_pass_manager.py -k "symbol_loop_hoist or symbol-loop-hoist"`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“验证 `symbol-loop-hoist` 位于 `tile-reduce` 之后、`lower-dma-memory-hierarchy` 之前时顺序合法。”场景。 | pytest -q test/passes/test_pass_manager.py -k "symbol_loop_hoist or symbol-loop-hoist" |
| TC-PASS-SYMBOL-LOOP-HOIST-015 | 边界/异常 | 插在 `tile-analysis` 与 `tile-reduce` 之间时报错。 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `TC-PASS-013B`。 | “插在 `tile-analysis` 与 `tile-reduce` 之间时报错。”场景按公开错误语义失败或被拒绝。 | `TC-PASS-013B` |
| TC-PASS-SYMBOL-LOOP-HOIST-016 | pass 改写 | 缺少 tile family 时允许 no-op。 | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `TC-PASS-015`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“缺少 tile family 时允许 no-op。”场景。 | `TC-PASS-015` |
| TC-PASS-SYMBOL-LOOP-HOIST-017 | 边界/异常 | `TC-PASS-016` / `TC-PASS-016A`：位于 tile family 之前时报错。 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `pytest -q test/passes/test_pass_manager.py -k "symbol_loop_hoist or symbol-loop-hoist"`。 | “`TC-PASS-016` / `TC-PASS-016A`：位于 tile family 之前时报错。”场景按公开错误语义失败或被拒绝。 | pytest -q test/passes/test_pass_manager.py -k "symbol_loop_hoist or symbol-loop-hoist" |
| TC-PASS-SYMBOL-LOOP-HOIST-018 | 边界/异常 | 位于 `lower-dma-memory-hierarchy` 之后时报错。 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `TC-PASS-017`。 | “位于 `lower-dma-memory-hierarchy` 之后时报错。”场景按公开错误语义失败或被拒绝。 | `TC-PASS-017` |
| TC-PASS-SYMBOL-LOOP-HOIST-019 | pass 改写 | 位于 `tile-reduce` 之后且位于 `lower-dma-memory-hierarchy` 之前时顺序合法。 | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `TC-PASS-017A`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“位于 `tile-reduce` 之后且位于 `lower-dma-memory-hierarchy` 之前时顺序合法。”场景。 | `TC-PASS-017A` |
