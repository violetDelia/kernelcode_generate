# ptr_symbol_func_input_plan.md

## 进度
更新日期：2026-04-01
更新规则：每个任务块进入新子阶段后立即更新本段。

| 任务 | 依赖 | 记录文件 | worktree | 当前进度 |
| --- | --- | --- | --- | --- |
| P1 | 无 | `20260401-ptr-symbol-func-input-p1.md` | `/wt-20260401-ptr-p1` | `已完成并合并（2026-04-01 04:44:49 +0800，T-20260401-15913d60，李白）` |
| P2 | P1 | `20260401-ptr-symbol-func-input-p2.md` | `/wt-20260401-ptr-p2` | `已放行（T-20260401-35733aa2，待执行）` |
| P3 | P1 | `20260401-ptr-symbol-func-input-p3.md` | `/wt-20260401-ptr-p3` | `spec完成（2026-04-01 04:56:36 +0800，T-20260401-097adbdb，咯咯咯）` |
| P4 | P1、P3 | `20260401-ptr-symbol-func-input-p4.md` | `/wt-20260401-ptr-p4` | `已放行（T-20260401-35484fb5，待执行）` |
| P5 | P3、P4 | `20260401-ptr-symbol-func-input-p5.md` | `/wt-20260401-ptr-p5` | `已建档（T-20260401-34a5e426，待 P3/P4 DONE）` |
| P6 | P2、P3、P4 | `20260401-ptr-symbol-func-input-p6.md` | `/wt-20260401-ptr-p6` | `已建档（T-20260401-94085d65，待 P2/P3/P4 DONE）` |
| I1 | — |  |  |  |
| I2 | P1~P6 |  |  |  |

## 功能说明

- 本计划基于当前仓库实现重新拟定，用来把 `Ptr` 相关链路从“已有 spec/dialect/AST 基线”推进到“用户可直接构造 `Ptr(dtype)` 并完成函数输入 lowering”的最终目标。
- 下文只以当前实现为起点描述已具备能力、最终目标和剩余 gap；管理员后续分发应直接按本计划推进。
- 当前最关键的判断是：P1 已在主线补齐 `Ptr(dtype)` 运行时对象与独立测试，而 P3 负责冻结 `symbol.ptr` 的 dialect 契约；当前主阻塞已收敛为 Python 包入口导出、`symbol.ptr` 的 dialect 测试闭环，以及 `build_func_op(...)` 侧的签名 lowering。

## 使用示例

- 管理员先确认当前 `Ptr` 基线，再按“本轮收口顺序”推进。
- 若执行者在以下文件中已经能看到 `Ptr` 相关规格与 AST 节点，说明本轮不应再把精力投回纯规格设计：

```bash
rg -n 'class Ptr|PtrArgAST|symbol\.ptr|!symbol\.ptr' spec kernel_gen/dsl/ast.py kernel_gen/dialect/symbol.py -S
```

- 若执行者在 [`kernel_gen/symbol_variable/__init__.py`](../../kernel_gen/symbol_variable/__init__.py)、[`kernel_gen/symbol_variable/`](../../kernel_gen/symbol_variable) 与 [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py) 中仍找不到 `Ptr` 运行时对象与 `!symbol.ptr<dtype>` 的签名 lowering，则当前主阻塞仍在 Python 包入口和函数签名生成侧。

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`咯咯咯`
- `文档`：[`ARCHITECTURE/plan/ptr_symbol_func_input_plan.md`](../../ARCHITECTURE/plan/ptr_symbol_func_input_plan.md)
- `spec`：
  - [`spec/symbol_variable/ptr.md`](../../spec/symbol_variable/ptr.md)
  - [`spec/symbol_variable/package_api.md`](../../spec/symbol_variable/package_api.md)
  - [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)
  - [`spec/dsl/ast.md`](../../spec/dsl/ast.md)
  - [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
  - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
- `功能实现`：
  - [`kernel_gen/symbol_variable/ptr.py`](../../kernel_gen/symbol_variable/ptr.py)
  - [`kernel_gen/symbol_variable/__init__.py`](../../kernel_gen/symbol_variable/__init__.py)
  - [`kernel_gen/dialect/symbol.py`](../../kernel_gen/dialect/symbol.py)
  - [`kernel_gen/dsl/ast.py`](../../kernel_gen/dsl/ast.py)
  - [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py)
- `test`：
  - [`test/symbol_variable/test_ptr.py`](../../test/symbol_variable/test_ptr.py)
  - [`test/symbol_variable/test_package_api.py`](../../test/symbol_variable/test_package_api.py)
  - [`test/dialect/test_symbol_dialect.py`](../../test/dialect/test_symbol_dialect.py)
  - [`test/dsl/test_ast.py`](../../test/dsl/test_ast.py)
  - [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py)
  - [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py)

## 当前实现基线

### 已具备

- [`spec/symbol_variable/ptr.md`](../../spec/symbol_variable/ptr.md) 已经定义 `Ptr(dtype)` 的公开语义。
- 主线已具备 [`kernel_gen/symbol_variable/ptr.py`](../../kernel_gen/symbol_variable/ptr.py) 与 [`test/symbol_variable/test_ptr.py`](../../test/symbol_variable/test_ptr.py)，P1 的 `Ptr(dtype)` 运行时对象、`ptr.dtype`、`repr(ptr)` 与缺参/多参错误边界已形成最小闭环。
- [`kernel_gen/dialect/symbol.py`](../../kernel_gen/dialect/symbol.py) 已经实现 `symbol.ptr` 类型承载。
- [`kernel_gen/dsl/ast.py`](../../kernel_gen/dsl/ast.py) 已经包含 `PtrArgAST`，并写入 `Ptr(dtype)` 注解解析分支。

### 当前断点

1. [`kernel_gen/symbol_variable/__init__.py`](../../kernel_gen/symbol_variable/__init__.py) 当前仍没有导出 `Ptr`，因此用户还不能通过 `from kernel_gen.symbol_variable import Ptr` 走包入口直接构造该对象。

2. [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md) 与 [`test/dialect/test_symbol_dialect.py`](../../test/dialect/test_symbol_dialect.py) 当前尚未形成 `SymbolPtrType` 的公开契约与测试闭环；`symbol.ptr` 实现已存在，但缺少与 parse/print/verifier 对齐的 spec/test 锚点。

3. [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py) 当前没有 `PtrArgAST`、`symbol.ptr` 或 `Pointer argument ...` 相关签名 lowering 逻辑，因此 `build_func_op(...)` 还不能把 `Ptr(dtype)` 形参稳定 lower 为 `!symbol.ptr<dtype>`。

## 最终目标

- 用户可以通过 `from kernel_gen.symbol_variable import Ptr` 直接构造 `Ptr(dtype)`。
- DSL 可以解析 `def kernel(data: Ptr(f32)) -> None:` 这类函数输入注解。
- `build_func_op(...)` / `build_func_op_from_ast(...)` 能把 `Ptr(f32)` 形参 lowering 为 `func.func` 的 `!symbol.ptr<f32>` 输入签名。
- `ptr` 在 v1 中只作为函数输入类型承载存在，函数体内仍保持拒绝算术、比较和 memory metadata 查询。

## 本轮边界

- 不在本轮引入 `ptr.load`、`ptr.store`、pointer arithmetic、pointer compare、address cast 或 codegen。
- 不新增独立 `ptr dialect`。
- 不把 `Ptr` 混回 `Memory` 或 `SymbolDim` 的兼容别名。

## 本轮收口顺序

1. 先在 [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md) 冻结 `SymbolPtrType` / `!symbol.ptr<dtype>` 的公开契约，并在实现阶段为 [`test/dialect/test_symbol_dialect.py`](../../test/dialect/test_symbol_dialect.py) 补 parse/print/verifier 用例。
2. 再在 [`kernel_gen/symbol_variable/__init__.py`](../../kernel_gen/symbol_variable/__init__.py) 中对外导出 `Ptr`，让 Python 包入口与已合并的 P1 运行时对象接通。
3. 在 [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py) 中接通 `PtrArgAST + Ptr(dtype)` 到 `!symbol.ptr<dtype>` 的函数签名 lowering，并补对应测试。
4. 在 `mlir_gen` 接通后，再确认 [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md) 的 body-level 拒绝边界与实现一致。

## 管理员执行口径

- `symbol.ptr` 的 dialect 契约和测试必须先闭环，再继续放大到 package export 或 `mlir_gen` 签名 lowering；否则后续链路会缺少统一的 IR 类型基线。
- `Ptr` 不属于 body-level 运算功能，本轮不要分发任何 `ptr` 算术或比较相关实现任务。
- 若执行者试图把 `Ptr` 实现成 `Memory`、`SymbolDim` 或其它现有对象的兼容别名，应直接退回。

## 本轮验收口径

- Python 包入口收口：
  - [`kernel_gen/symbol_variable/__init__.py`](../../kernel_gen/symbol_variable/__init__.py) 必须导出 `Ptr`。
  - 必须新增 `test/symbol_variable/test_ptr.py`，至少覆盖：
    - `Ptr(f32)` 构造成功
    - `Ptr()` 报 `Ptr requires exactly one dtype`
    - `Ptr(f32, f32)` 报 `Ptr requires exactly one dtype`
    - `Ptr` 与 `Memory`、`SymbolDim` 职责边界不同

- AST 与函数签名收口：
  - [`kernel_gen/dsl/ast.py`](../../kernel_gen/dsl/ast.py) 继续保留 `PtrArgAST` 注解入口。
  - [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py) 必须能把 `Ptr(f32)` 形参 lowering 为 `!symbol.ptr<f32>`。
  - 必须新增并通过以下能力断言：
    - `build_func_op(kernel, Ptr(f32))` 成功
    - `func.func` 输入类型打印为 `!symbol.ptr<f32>`
    - 运行时参数不是 `Ptr(dtype)` 或 dtype 不一致时固定报错

- body-level 边界继续保持：
  - `ptr` 形参进入算术、比较、`get_shape()`、`get_stride()` 时仍报固定错误。

## 当前最直接的下一步

- 沿 P3 对 [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md) 的收口结果，先补 `SymbolPtrType` 对应的 dialect 测试与最小实现对齐；并行链路再由 P2 处理包入口导出。
