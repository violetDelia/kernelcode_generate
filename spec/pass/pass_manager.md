# pass_manager.md

## 功能简介

- 定义 Pass 管理与调度的最小可用规范，描述 `Pass` 与 xdsl `ModulePass` 的组织、排序与执行规则。
- 面向上层 IR/DSL 的通用优化/规范化流程，不绑定具体 IR 类型或后端。

## API 列表

- `Pass`
  - `—— run(target: object) -> object`
- `PassManager`
  - `—— init(name: str | None = None)`
  - `—— add_pass(pass_obj: Pass | ModulePass)`
  - `—— extend(passes: Iterable[Pass | ModulePass])`
  - `—— run(target: object) -> object`

## 文档信息

- 创建者：`李白`
- 最后一次更改：`金铲铲大作战`
- `spec`：[`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)
- `功能实现`：[`kernel_gen/passes/pass_manager.py`](../../kernel_gen/passes/pass_manager.py)
- `test`：[`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)

## 依赖

- 无（当前仅定义 Pass 管理抽象，不绑定具体 IR 类型）。

## 目标

- 提供可组合的 Pass 管理器，支持按顺序执行多个 Pass。
- 统一 Pass 的注册、执行与错误传播规则，便于后续实现与测试闭环。
- PassManager 只负责 Pass 编排与执行，不承载默认 pipeline builder；默认 builder 见 [`spec/pass/pipeline/default_lowering.md`](../../spec/pass/pipeline/default_lowering.md)。
- PassManager 固定支持两类公开对象：`Pass` 与 xdsl `ModulePass`；执行时内部创建并复用单个 `Context`。
- 业务顺序约束不属于 PassManager 职责；具体 lowering / tuning / tile / backend pipeline 的顺序由对应 builder 与其 spec 固定。

## 限制与边界

- 不定义任何具体 Pass 的业务逻辑，仅规范 Pass 组织与执行流程。
- 不引入跨模块依赖或后端 lowering 规则。
- 不要求 Pass 修改输入的方式（可返回新对象或就地修改），以 `run` 返回值为准。
- 不要求 `ModulePass.apply` 返回值；`PassManager` 以 `apply(ctx, module)` 的副作用作为结果，继续返回原 `module` 对象。
- 当管理器中无 Pass 时，执行结果必须等于输入（无副作用的空操作）。
- PassManager 不解释 pass 名称语义，不根据 pass 名称施加排序或依赖约束。

## 当前调用边界

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
- 以下旧兼容入口在当前基线中必须稳定失败：
  - `kernel_gen.passes.pass_manager.build_default_lowering_pass_manager`
- 当前文件级公开 API 只包含 `Pass` 与 `PassManager`；pipeline / registry / test 不得跨文件调用额外 helper。

## 公开接口

### `class Pass`

功能说明：

- 表示可执行的单个 Pass。

参数说明：

- `name (str)`：Pass 标识名称，用于诊断与测试断言。

使用示例：

```python
class MyPass(Pass):
    name = "my-pass"
    def run(self, target):
        return target
```

注意事项：

- `run` 必须接收一个输入并返回一个输出对象。
- `name` 需可读且稳定，便于测试匹配。

前置条件：

- 传入 `run` 的对象必须满足该 Pass 的输入类型约束（由具体 Pass 规范定义）。

后置条件：

- `run` 返回值必须可作为下游 Pass 的输入；若无法继续传递必须显式抛错。

返回与限制：

- `run` 返回值作为下游 Pass 的输入。
- `run` 内抛出的异常应向上抛出，管理器不吞异常。

### `class PassManager`

功能说明：

- 维护 Pass 列表并按顺序执行。

参数说明：

- `name (str|None)`：管理器名称，可选，用于调试与日志。

使用示例：

```python
pm = PassManager(name="opt")
pm.add_pass(MyPass())
result = pm.run(ir)
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

注意事项：

- Pass 执行顺序与添加顺序一致。
- `add_pass` 只接受 `Pass` 或 xdsl `ModulePass` 实例；不再接受仅靠 duck typing 暴露 `name/run/apply` 的 pass-like 对象。
- 业务顺序由调用方决定；PassManager 只保证“按添加顺序执行”。

前置条件：

- `run` 的输入必须是上游 AST/IR 发射已完成的对象；若输入尚未完成发射，必须由上游阶段抛出错误或中止。

后置条件：

- `run` 返回最后一个 Pass 的输出；当无 Pass 时，返回对象与输入为同一语义对象。

返回与限制：

- `run` 返回最后一个 Pass 的输出；无 Pass 时返回原输入。
- 不得返回多返回值结构。

### `PassManager.add_pass(pass_obj)`

功能说明：

- 注册单个 Pass 到管理器。

参数说明：

- `pass_obj (Pass | ModulePass)`：待注册的 Pass 实例。

使用示例：

```python
pm.add_pass(MyPass())
```

注意事项：

- `pass_obj` 必须是 `Pass` 或 xdsl `ModulePass` 实例，且 `name` 必须是稳定字符串。

返回与限制：

- 返回 `None`；非法类型应抛出 `TypeError`。

### `PassManager.extend(passes)`

功能说明：

- 批量注册 Pass。

参数说明：

- `passes (Sequence[Pass | ModulePass])`：Pass 列表。

使用示例：

```python
pm.extend([PassA(), PassB()])
```

注意事项：

- 任一元素不是 `Pass` 或 xdsl `ModulePass`，或 `name` 不是字符串时必须抛出 `TypeError`。

返回与限制：

- 返回 `None`。

### `PassManager.run(target)`

功能说明：

- 依序执行所有 Pass。

参数说明：

- `target (object)`：待处理对象（IR/AST 等）。

使用示例：

```python
result = pm.run(ir)
```

注意事项：

- Pass 的输出必须作为下一个 Pass 的输入。
- 任何 Pass 抛出的异常应原样传播。
- `Pass` 固定走 `run(target)`；其它 xdsl `ModulePass` 固定走 `apply(ctx, target)`，不再按“是否额外提供 run/apply”做兼容优先级分支。

前置条件：

- `target` 必须满足第一个 Pass 的输入约束。

后置条件：

- 若未抛出异常，输出必须满足最后一个 Pass 的输出约束，且可供后续验证/打印阶段使用。

返回与限制：

- 返回最终 Pass 的输出；无 Pass 时返回输入本身。

## 测试

- 测试文件：[`test/pass/test_pass_manager.py`](../../test/pass/test_pass_manager.py)
- 执行命令：`pytest -q test/pass/test_pass_manager.py`

### 测试目标

- 验证 Pass 注册与执行顺序一致。
- 验证空管理器执行返回原输入。
- 验证显式注册非法 Pass 时触发 `TypeError`。
- 验证 Pass 异常可向上抛出。
- 验证 PassManager 不承载旧默认 builder 兼容入口。

### 功能与用例清单

| 用例 ID | 约束点 | 对应测试 |
| --- | --- | --- |
| TC-PASS-001 | 单 Pass 正常执行 | `test_pass_manager_single_pass` |
| TC-PASS-002 | 多 Pass 顺序执行 | `test_pass_manager_multiple_passes_order` |
| TC-PASS-003 | 空管理器返回原输入 | `test_pass_manager_empty_returns_input` |
| TC-PASS-004 | 非法 Pass 类型报错 | `test_pass_manager_invalid_pass_type` |
| TC-PASS-005 | Pass 异常向上抛出 | `test_pass_manager_exception_propagation` |
| TC-PASS-006 | 旧默认 builder 兼容入口已退场 | `test_pass_manager_has_no_legacy_default_lowering_builder` |

## 失败归因

- AST 发射失败：上游 DSL/AST 构建阶段无法生成合法 IR，表现为进入 PassManager 前已抛错或传入 `target` 为空/类型不符。
- Dialect verify 失败：某 Pass 调用 verifier 或验证器抛错，原因通常为 IR 类型、attribute 或 operand 约束不满足。
- Lowering 失败：具体 lowering Pass 在 op 映射、类型转换或结果分配时抛错，PassManager 仅负责透传异常，不做吞并或重写。
