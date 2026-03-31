# ptr_symbol_func_input_plan.md

## 进度
更新日期：2026-04-01
更新规则：每个任务块进入新子阶段后立即更新本段。

| 任务 | 依赖 | 记录文件 | worktree | 当前进度 |
| --- | --- | --- | --- | --- |
| P1 | 无 | `20260401-ptr-symbol-func-input-p1.md` | `/wt-20260401-ptr-p1` | `spec进行中（2026-04-01 02:36:58 +0800，T-20260401-098531c0，睡觉小分队）` |
| P2 | P1 | `20260401-ptr-symbol-func-input-p2.md` | `/wt-20260401-ptr-p2` | `已建档（T-20260401-35733aa2，待 P1 DONE）` |
| P3 | P1 | `20260401-ptr-symbol-func-input-p3.md` | `/wt-20260401-ptr-p3` | `已建档（T-20260401-097adbdb，待 P1 DONE）` |
| P4 | P1、P3 | `20260401-ptr-symbol-func-input-p4.md` | `/wt-20260401-ptr-p4` | `已建档（T-20260401-35484fb5，待 P1/P3 DONE）` |
| P5 | P3、P4 | `20260401-ptr-symbol-func-input-p5.md` | `/wt-20260401-ptr-p5` | `已建档（T-20260401-34a5e426，待 P3/P4 DONE）` |
| P6 | P2、P3、P4 | `20260401-ptr-symbol-func-input-p6.md` | `/wt-20260401-ptr-p6` | `已建档（T-20260401-94085d65，待 P2/P3/P4 DONE）` |
| I1 | — |  |  |  |
| I2 | P1~P6 |  |  |  |

## 功能说明

- 本计划基于当前仓库实现重新拟定，用来把 `Ptr` 相关链路从“已有 spec/dialect/AST 基线”推进到“用户可直接构造 `Ptr(dtype)` 并完成函数输入 lowering”的最终目标。
- 下文只以当前实现为起点描述已具备能力、最终目标和剩余 gap；管理员后续分发应直接按本计划推进。
- 当前最关键的判断是：`spec/symbol_variable/ptr.md`、`symbol.ptr` 类型和 `PtrArgAST` 已经存在，但 Python 包入口与 `build_func_op(...)` 侧还没有把这条链真正接通。

## 使用示例

- 管理员先确认当前 `Ptr` 基线，再按“本轮收口顺序”推进。
- 若执行者在以下文件中已经能看到 `Ptr` 相关规格与 AST 节点，说明本轮不应再把精力投回纯规格设计：

```bash
rg -n 'class Ptr|PtrArgAST|symbol\.ptr|!symbol\.ptr' spec kernel_gen/dsl/ast.py kernel_gen/dialect/symbol.py -S
```

- 若执行者在 [`kernel_gen/symbol_variable/__init__.py`](../../kernel_gen/symbol_variable/__init__.py)、[`kernel_gen/symbol_variable/`](../../kernel_gen/symbol_variable) 与 [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py) 中仍找不到 `Ptr` 运行时对象与 `!symbol.ptr<dtype>` 的签名 lowering，则当前主阻塞仍在 Python 包入口和函数签名生成侧。

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`大闸蟹`
- `文档`：[`ARCHITECTURE/plan/ptr_symbol_func_input_plan.md`](../../ARCHITECTURE/plan/ptr_symbol_func_input_plan.md)
- `spec`：
  - [`spec/symbol_variable/ptr.md`](../../spec/symbol_variable/ptr.md)
  - [`spec/symbol_variable/package_api.md`](../../spec/symbol_variable/package_api.md)
  - [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)
  - [`spec/dsl/ast.md`](../../spec/dsl/ast.md)
  - [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
  - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
- `功能实现`：
  - [`kernel_gen/symbol_variable/__init__.py`](../../kernel_gen/symbol_variable/__init__.py)
  - [`kernel_gen/dialect/symbol.py`](../../kernel_gen/dialect/symbol.py)
  - [`kernel_gen/dsl/ast.py`](../../kernel_gen/dsl/ast.py)
  - [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py)
- `test`：
  - [`test/symbol_variable/test_package_api.py`](../../test/symbol_variable/test_package_api.py)
  - [`test/dialect/test_symbol_dialect.py`](../../test/dialect/test_symbol_dialect.py)
  - [`test/dsl/test_ast.py`](../../test/dsl/test_ast.py)
  - [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py)
  - [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py)

## 当前实现基线

### 已具备

- [`spec/symbol_variable/ptr.md`](../../spec/symbol_variable/ptr.md) 已经定义 `Ptr(dtype)` 的公开语义。
- [`kernel_gen/dialect/symbol.py`](../../kernel_gen/dialect/symbol.py) 已经实现 `symbol.ptr` 类型承载。
- [`kernel_gen/dsl/ast.py`](../../kernel_gen/dsl/ast.py) 已经包含 `PtrArgAST`，并写入 `Ptr(dtype)` 注解解析分支。

### 当前断点

1. [`kernel_gen/symbol_variable/`](../../kernel_gen/symbol_variable) 当前没有 `ptr.py`；[`kernel_gen/symbol_variable/__init__.py`](../../kernel_gen/symbol_variable/__init__.py) 也没有导出 `Ptr`。这意味着用户还没有可直接构造的 Python 运行时对象。

2. [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py) 当前没有 `PtrArgAST`、`symbol.ptr` 或 `Pointer argument ...` 相关签名 lowering 逻辑，因此 `build_func_op(...)` 还不能把 `Ptr(dtype)` 形参稳定 lower 为 `!symbol.ptr<dtype>`。

3. 当前测试集中也没有 `test/symbol_variable/test_ptr.py`，说明 `Ptr` 运行时对象本身仍未形成独立测试闭环。

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

1. 在 [`kernel_gen/symbol_variable/`](../../kernel_gen/symbol_variable) 中新增 `Ptr` 运行时对象，并在 [`kernel_gen/symbol_variable/__init__.py`](../../kernel_gen/symbol_variable/__init__.py) 对外导出。
2. 为 `Ptr` 运行时对象补独立测试，覆盖构造参数数量、dtype 保留、与 `Memory/SymbolDim` 的职责边界。
3. 在 [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py) 中接通 `PtrArgAST + Ptr(dtype)` 到 `!symbol.ptr<dtype>` 的函数签名 lowering，并补对应测试。
4. 在 `mlir_gen` 接通后，再确认 [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md) 的 body-level 拒绝边界与实现一致。

## 管理员执行口径

- `Ptr` 运行时对象和 `mlir_gen` 签名 lowering 必须连续推进；前者不落地，后者无法形成可运行入口。
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

- 先补 [`kernel_gen/symbol_variable/`](../../kernel_gen/symbol_variable) 中的 `Ptr` 运行时对象和包导出；这是整条 `ptr` 输入链从规格骨架走向真实可用入口的第一道硬断点。
