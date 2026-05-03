# pass_manager.md

## 功能简介

- 定义 Pass 管理与调度的最小可用规范，描述 `Pass` 与 xdsl `ModulePass` 的组织、排序与执行规则。
- 面向 `builtin.module` 的通用优化/规范化流程，不绑定具体后端。
- `Pass` 默认启用 `fold=True`，`PassManager` 在每个 pass 后对 `ModuleOp` 做一次 folding + DCE sweep。

## API 列表

- `class Pass(XdslModulePass)`
- `Pass.__init__(fold: bool = True) -> None`
- `class PassManager`
- `PassManager.__init__(name: str | None = None) -> None`
- `PassManager.add_pass(pass_obj: XdslModulePass) -> None`
- `PassManager.extend(passes: Sequence[XdslModulePass]) -> None`
- `PassManager.run(target: ModuleOp) -> ModuleOp`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)
- `功能实现`：[`kernel_gen/passes/pass_manager.py`](../../kernel_gen/passes/pass_manager.py)
- `test`：[`test/passes/test_pass_manager.py`](../../test/passes/test_pass_manager.py)

## 依赖

- 无（当前仅定义 Pass 管理抽象，不绑定具体 IR 类型）。

## 目标

- 提供可组合的 Pass 管理器，支持按顺序执行多个 Pass。
- 统一 Pass 的注册、执行与错误传播规则，便于后续实现与测试闭环。
- PassManager 只负责 Pass 编排与执行，不承载默认 pipeline builder；默认 builder 见 [`spec/pass/pipeline/default_lowering.md`](../../spec/pass/pipeline/default_lowering.md)。
- PassManager 固定支持两类公开对象：`Pass` 与 xdsl `ModulePass`；执行时内部创建并复用单个 `Context`。
- `dump_dir` 是来自 `kernel_gen.core.config` 的诊断开关；非空时写入初始 IR 与逐 pass 后 IR，不改变 pass 执行结果。
- fold 是 pass 级通用开关；未声明 `fold` 的第三方 `ModulePass` 按 `fold=True` 处理，只有显式 `fold=False` 才关闭 pass 后 folding + DCE sweep。
- 通用 fold sweep 启用 folding 与 DCE；DCE 仅删除无使用者且无副作用的 op，不承担 CSE、业务重写或 canonicalization pattern。
- 业务顺序约束不属于 PassManager 职责；具体 lowering / tuning / tile / backend pipeline 的顺序由对应 builder 与其 spec 固定。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 不定义任何具体 Pass 的业务逻辑，仅规范 Pass 组织、执行流程与通用 fold 调度。
- 不引入跨模块依赖或后端 lowering 规则。
- Pass 固定以 `apply(ctx, module)` 原地改写 `ModuleOp`，不再支持返回新对象的单 pass 执行合同。
- `PassManager` 以 `apply(ctx, module)` 的副作用作为结果，继续返回原 `module` 对象。
- 通用 fold sweep 当前只承诺对实现 folder 的 symbol 算术、静态 memory 元信息查询等 foldable op 生效，并删除 xdsl 可判定的死 op；不会把 CSE 或具体 lowering pattern 混入 PassManager。
- 当管理器中无 Pass 时，执行结果必须等于输入（无副作用的空操作）。
- PassManager 不解释 pass 名称语义，不根据 pass 名称施加排序或依赖约束。

### 当前调用说明

- `PassManager` 与 `Pass` 的 canonical public path 固定为 `kernel_gen.passes.pass_manager`。
- default / npu-demo pipeline builder 的 canonical public path 固定为 `kernel_gen.passes.pipeline`。
- `LowerDmaMemoryHierarchyPass` 与 `MemoryPoolPass` 的 canonical public path 固定为 `kernel_gen.passes.dma_memory_hierarchy` 与 `kernel_gen.passes.memory_pool`。
- tile family 的 canonical public path 固定为：
  - `kernel_gen.passes.tile.analysis`
  - `kernel_gen.passes.tile.elewise`
  - `kernel_gen.passes.tile.reduce`
- 当前仍允许 pass manager caller 通过下列活跃模块导入 lowering family：
  - `kernel_gen.passes.lowering`
- 以下旧路径在当前基线中必须稳定失败：
  - `kernel_gen.analysis`
  - `kernel_gen.analysis.analysis`
  - `kernel_gen.analysis.compute`
  - `kernel_gen.analysis.memory`
  - `kernel_gen.passes.analysis`
  - `kernel_gen.passes.analysis.func_cost`
  - `kernel_gen.passes.lowering.pass_manager`
  - `kernel_gen.passes.lowering.registry`
  - `kernel_gen.passes.lowering.dma_memory_hierarchy`
  - `kernel_gen.passes.lowering.memory_pool`
  - `kernel_gen.passes.lowering.tile_analysis`
  - `kernel_gen.passes.lowering.tile_elewise`
  - `kernel_gen.passes.lowering.tile_reduce`
- `LowerDmaMemoryHierarchyPass` 与 `MemoryPoolPass` 的调用方不得再把 lowering compat 路径当作主入口；若需要添加这两个 pass，应从上级模块导入后再交给 `PassManager`。
- `MemoryPoolPass` 的 `rewrite` 与 `alignment` 由 `MemoryPoolPass(...)` 或 registry/ircheck 构造入口决定；`PassManager` 只负责按 pass 对象现有配置执行和处理通用 `fold` sweep，不解析 `memory-pool` 专属 option。
- 以下旧兼容入口在当前基线中必须稳定失败：
  - `kernel_gen.passes.pass_manager.build_default_lowering_pass_manager`
- 当前文件级公开 API 只包含 `Pass` 与 `PassManager`；pipeline / registry / test 不得跨文件调用额外 helper。


### `class Pass(fold: bool = True)`

- 功能说明：

- 表示可执行的单个 Pass。
- 只提供通用 `fold` 开关；具体 pass 必须实现 xdsl `ModulePass.apply(ctx, module)`。

- 参数：

- `name (str)`：Pass 标识名称，用于诊断与测试断言。
- `fold (bool)`：是否允许该 pass 后执行通用 folding + DCE sweep，默认 `True`。

- 使用示例：

```python
class MyPass(Pass):
    name = "my-pass"
    def apply(self, ctx, module):
        pass

pass_obj = MyPass(fold=False)
```

- 注意事项：

- 不再提供单 pass `run(...)` 兼容入口。
- `apply(ctx, module)` 必须原地改写 `ModuleOp` 或显式抛错。
- `name` 需可读且稳定，便于测试匹配。
- `fold=False` 只关闭通用 folding + DCE sweep，不允许 pass 因此跳过自身必须执行的业务校验。

前置条件：

- 传入 `apply(ctx, module)` 的对象必须是 `ModuleOp`。

后置条件：

- `apply(ctx, module)` 完成后同一 `ModuleOp` 作为下游 Pass 输入；若无法继续传递必须显式抛错。
- 当 `fold=True` 时，PassManager 会在该 pass 后执行一次 folding + DCE sweep。

- 返回值：

- 单 pass 不提供返回式执行入口。
- `apply` 内抛出的异常应向上抛出，管理器不吞异常。

### `class PassManager`

- 功能说明：

- 维护 Pass 列表并按顺序执行。

- 参数：

- `name (str|None)`：管理器名称，可选，用于调试与日志。

- 使用示例：

```python
pm = PassManager(name="opt")
pm.add_pass(MyPass())
result = pm.run(module)
```

```python
from xdsl.context import Context
from xdsl.passes import ModulePass

class MyModulePass(ModulePass):
    name = "my-module-pass"

    def apply(self, ctx: Context, module):
        return None

pm = PassManager(name="opt")
pm.add_pass(MyModulePass())
result = pm.run(module)
```

- 注意事项：

- Pass 执行顺序与添加顺序一致。
- `add_pass` 只接受 `Pass` 或 xdsl `ModulePass` 实例；不再接受仅靠 duck typing 暴露 `name/apply` 的 pass-like 对象。
- 业务顺序由调用方决定；PassManager 只保证“按添加顺序执行”。

前置条件：

- `run` 的输入必须是上游 AST/IR 发射已完成的对象；若输入尚未完成发射，必须由上游阶段抛出错误或中止。

后置条件：

- `run` 返回最后一个 Pass 的输出；当无 Pass 时，返回对象与输入为同一语义对象。

- 返回值：

- `run` 返回最后一个 Pass 的输出；无 Pass 时返回原输入。
- 不得返回多返回值结构。

### `PassManager.add_pass(pass_obj)`

- 功能说明：

- 注册单个 Pass 到管理器。

- 参数：

- `pass_obj (Pass | ModulePass)`：待注册的 Pass 实例。

- 使用示例：

```python
pm.add_pass(MyPass())
```

- 注意事项：

- `pass_obj` 必须是 `Pass` 或 xdsl `ModulePass` 实例，且 `name` 必须是稳定字符串。

- 返回值：

- 返回 `None`；非法类型应抛出 `TypeError`。

### `PassManager.extend(passes)`

- 功能说明：

- 批量注册 Pass。

- 参数：

- `passes (Sequence[Pass | ModulePass])`：Pass 列表。

- 使用示例：

```python
pm.extend([PassA(), PassB()])
```

- 注意事项：

- 任一元素不是 `Pass` 或 xdsl `ModulePass`，或 `name` 不是字符串时必须抛出 `TypeError`。

- 返回值：

- 返回 `None`。

### `PassManager.run(module)`

- 功能说明：

- 依序执行所有 Pass。

- 参数：

- `module (ModuleOp)`：待处理的 `builtin.module`。
- 诊断目录通过 `kernel_gen.core.config.set_dump_dir(...)` 设置；非空时写入 pass IR 产物。

- 使用示例：

```python
result = pm.run(module)
set_dump_dir("dump/kernel")
result = pm.run(module)
```

- 注意事项：

- 每个 pass 必须原地改写同一 `ModuleOp`。
- 任何 Pass 抛出的异常应原样传播。
- 所有 pass 固定走 `apply(ctx, module)`；不再按“是否额外提供 run/apply”做兼容优先级分支。
- `kernel_gen.core.config.dump_dir` 非空时，目录内必须包含 `01-first-ir.mlir`；每个 pass 完成后写入 `NN-<pass-name>.mlir`。
- 每个 pass 后 dump 文件第一行必须是当前 pass 的可解析名称文本，后续内容为该 pass 后的 IR 文本。

前置条件：

- `module` 必须是 `builtin.module`。

后置条件：

- 若未抛出异常，同一 `ModuleOp` 必须满足最后一个 Pass 的输出约束，且可供后续验证/打印阶段使用。

- 返回值：

- 返回最终 Pass 的输出；无 Pass 时返回输入本身。
- `dump_dir` 不参与返回值，不允许改变 pass 业务结果。

## API详细说明

### `class Pass(XdslModulePass)`

- api：`class Pass(XdslModulePass)`
- 参数：无。
- 返回值：`Pass` 实例。
- 使用示例：

  ```python
  pass = Pass()
  ```
- 功能说明：定义 `Pass` pass 对象。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `Pass.__init__(fold: bool = True) -> None`

- api：`Pass.__init__(fold: bool = True) -> None`
- 参数：
  - `fold`：`fold` 输入值，参与 `__init__` 的公开处理流程；类型 `bool`；默认值 `True`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  pass = Pass(fold=True)
  ```
- 功能说明：执行 `__init__`。
- 注意事项：该特殊方法只承接 Python 对应协议语义；不得额外暴露内部字段。

### `class PassManager`

- api：`class PassManager`
- 参数：无。
- 返回值：`PassManager` 实例。
- 使用示例：

  ```python
  pass_manager = PassManager()
  ```
- 功能说明：定义 `PassManager` 公开类型。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `PassManager.__init__(name: str | None = None) -> None`

- api：`PassManager.__init__(name: str | None = None) -> None`
- 参数：
  - `name`：公开名称、符号名或注册名，用于查找、打印、注册或生成稳定标识；类型 `str | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  pass_manager = PassManager(name=None)
  ```
- 功能说明：执行 `__init__`。
- 注意事项：该特殊方法只承接 Python 对应协议语义；不得额外暴露内部字段。

### `PassManager.add_pass(pass_obj: XdslModulePass) -> None`

- api：`PassManager.add_pass(pass_obj: XdslModulePass) -> None`
- 参数：
  - `pass_obj`：`pass_obj` 输入值，参与 `add_pass` 的公开处理流程；类型 `XdslModulePass`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  pass_manager = pass_manager
  pass_manager.add_pass(pass_obj=pass_obj)
  ```
- 功能说明：执行 `add_pass`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `PassManager.extend(passes: Sequence[XdslModulePass]) -> None`

- api：`PassManager.extend(passes: Sequence[XdslModulePass]) -> None`
- 参数：
  - `passes`：pass 列表或 pass 名称序列，定义 pass manager 需要执行的处理流程；类型 `Sequence[XdslModulePass]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  pass_manager = pass_manager
  pass_manager.extend(passes=passes)
  ```
- 功能说明：执行 `extend`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `PassManager.run(target: ModuleOp) -> ModuleOp`

- api：`PassManager.run(target: ModuleOp) -> ModuleOp`
- 参数：
  - `target`：目标对象、目标名称或目标缓冲区，指定当前操作写入或作用的位置；类型 `ModuleOp`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`ModuleOp`。
- 使用示例：

  ```python
  pass_manager = pass_manager
  result = pass_manager.run(target=target)
  ```
- 功能说明：执行 `run`。
- 注意事项：输入解析、执行失败和校验失败必须通过本条目声明的返回值或公开错误文本表达。

## 测试

- 测试文件：`test/passes/test_pass_manager.py`
- 执行命令：`pytest -q test/passes/test_pass_manager.py`

### 测试目标

- 验证 Pass 注册与执行顺序一致。
- 验证空管理器执行返回原输入。
- 验证 `dump_dir` 写入初始 IR 与逐 pass 后 IR。
- 验证显式注册非法 Pass 时触发 `TypeError`。
- 验证 Pass 异常可向上抛出。
- 验证 PassManager 不承载旧默认 builder 兼容入口。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-PASS-001 | pass 改写 | 单 Pass 正常执行 | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_pass_manager_single_pass`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“单 Pass 正常执行”场景。 | `test_pass_manager_single_pass` |
| TC-PASS-002 | pass 改写 | 多 Pass 顺序执行 | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_pass_manager_multiple_passes_order`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“多 Pass 顺序执行”场景。 | `test_pass_manager_multiple_passes_order` |
| TC-PASS-003 | pass 改写 | 空管理器返回原输入 | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_pass_manager_empty_returns_input`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“空管理器返回原输入”场景。 | `test_pass_manager_empty_returns_input` |
| TC-PASS-004 | 边界/异常 | 非法 Pass 类型报错 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_pass_manager_invalid_pass_type`。 | “非法 Pass 类型报错”场景按公开错误语义失败或被拒绝。 | `test_pass_manager_invalid_pass_type` |
| TC-PASS-005 | pass 改写 | Pass 异常向上抛出 | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_pass_manager_exception_propagation`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“Pass 异常向上抛出”场景。 | `test_pass_manager_exception_propagation` |
| TC-PASS-006 | pass 改写 | 旧默认 builder 兼容入口已退场 | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_pass_manager_has_no_legacy_default_lowering_builder`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“旧默认 builder 兼容入口已退场”场景。 | `test_pass_manager_has_no_legacy_default_lowering_builder` |
