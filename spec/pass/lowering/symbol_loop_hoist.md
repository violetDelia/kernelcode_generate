# symbol_loop_hoist

## 功能简介

`symbol-loop-hoist` 是一个 lowering pass，仅处理 `symbol.for` 场景，用于把循环体内“只依赖循环外 SSA 值”的对象外提到循环外，从而避免在 split 后的 `symbol.for` 体内重复构造 invariant 的符号查询、形状计算、以及可复用的 buffer/视图描述。

该 pass 的目标不是通用 LICM，而是以白名单为主，提供稳定、可测试的外提合同。

## 文档信息

- 创建者：朽木露琪亚
- 最后一次更改：朽木露琪亚
- spec：[`spec/pass/lowering/symbol_loop_hoist.md`](spec/pass/lowering/symbol_loop_hoist.md)
- 功能实现：[`kernel_gen/passes/lowering/symbol_loop_hoist.py`](kernel_gen/passes/lowering/symbol_loop_hoist.py)
- test：[`test/pass/test_symbol_loop_hoist.py`](test/pass/test_symbol_loop_hoist.py)

## 依赖

- IR 与 Pass 基础：
  - [`kernel_gen/passes/pass_manager.py`](kernel_gen/passes/pass_manager.py)
  - xDSL `ModuleOp` / `Block` / `Operation`
- 参与的 dialect（直接依赖）：
  - [`kernel_gen/dialect/symbol.py`](kernel_gen/dialect/symbol.py)
  - [`kernel_gen/dialect/tuner.py`](kernel_gen/dialect/tuner.py)
  - [`kernel_gen/dialect/dma.py`](kernel_gen/dialect/dma.py)

## 公开接口

### `SymbolLoopHoistPass`

功能说明：
- pass 名称固定为 `symbol-loop-hoist`。
- 遍历 module 内的 `symbol.for`，在不改变 loop 语义的前提下外提循环 invariant 的对象到 `symbol.for` 之前。

参数说明：
- `module(ModuleOp)`: 输入 module。

返回与限制：
- 返回重写后的 `module`（就地改写）。
- 若 module 中不存在 `symbol.for`，应执行 no-op（不报错）。
- 不新建函数，不改变函数签名，不引入 helper function。

使用示例：
- `from kernel_gen.passes.lowering.symbol_loop_hoist import SymbolLoopHoistPass`
- `module = SymbolLoopHoistPass().run(module)`

注意事项：
- 外提采用白名单策略；不在白名单中的 op 不应被“猜测性外提”。
- 对 `dma.*` 仅处理明确列出的子集；禁止项必须保留在循环体内。

### 外提白名单（首版）

- `tuner.param`
- `symbol.get_dim / symbol.get_stride`
- `symbol.add/sub/mul/div/floordiv`
- `symbol.eq/ne/lt/le/gt/ge`
- `symbol.to_int / symbol.to_float`
- `dma.alloc`
- `dma.view / dma.reshape`
- 固定窗口、只读来源、且结果在循环体内不被写回的 `dma.slice / dma.load`

### 明确禁止项（首版）

- 任何依赖 loop iv 或 loop-carried value 的对象不得外提
- `dma.deslice / dma.copy / dma.store / dma.fill / dma.free` 不得外提

### 失败短语

本 pass 在显式失败时必须使用以下固定短语之一作为错误信息前缀（用于测试稳定匹配）：

- `SymbolLoopHoistRequiresSymbolFor`（PassManager 顺序/前置条件校验）
- `SymbolLoopHoistSideEffectOp`
- `SymbolLoopHoistAllocLifetimeUnsafe`
- `SymbolLoopHoistFixedReadSourceMutated`
- `SymbolLoopHoistFixedReadResultRewritten`
- `SymbolLoopHoistVerifierError`

## 测试

- 测试文件：[`test/pass/test_symbol_loop_hoist.py`](test/pass/test_symbol_loop_hoist.py)
- 执行命令：
  - `pytest -q test/pass/test_symbol_loop_hoist.py`
- 测试目标：
  - 验证 `symbol.get_dim + dma.alloc` 能从 `symbol.for` 内外提到 `symbol.for` 之前
  - 验证固定窗口 `dma.slice` 在只读来源且结果不被改写时可外提
  - 验证禁止项（例如 `dma.deslice`）在 loop invariant 形态下会触发显式失败短语
  - 验证 `PassManager` 的 `symbol-loop-hoist` 顺序约束（在 `test/pass/test_pass_manager.py` 中覆盖）

功能与用例清单：
- `TC-SLH-001`：外提 `symbol.get_dim + dma.alloc`
- `TC-SLH-002`：固定窗口只读 `dma.slice` 外提
- `TC-SLH-003`：禁止项 `dma.deslice` 显式失败短语
- `TC-SLH-004`：`dma.alloc` 在 loop 内释放触发 `SymbolLoopHoistAllocLifetimeUnsafe`
- `TC-SLH-005`：固定窗口 `dma.slice` 的目标 buffer 在 loop 内仍被写触发 `SymbolLoopHoistFixedReadResultRewritten`
- `TC-SLH-006`：固定窗口 `dma.slice` 的来源在 loop 内被写触发 `SymbolLoopHoistFixedReadSourceMutated`
- `TC-SLH-007`：`module.verify()` 失败包装为 `SymbolLoopHoistVerifierError`
