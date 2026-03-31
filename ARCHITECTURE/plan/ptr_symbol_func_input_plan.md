# ptr_symbol_func_input_plan.md

## 进度

- 更新日期：2026-03-31
- 更新规则：每个任务块进入新子阶段后立即更新本段。
- 当前状态：用户已确认按本计划推进；`I1` 已完成回退修复、复审与合并收口；`P1/P2` 已完成二次复审与合并；`P3/P4/P5`、`P6` 已建档待推进，不再按“仅 spec 完成”停留；抢跑建档的 `I2` 已清理，待前置任务块闭环后再重建。
- `P1`：spec 完成（T-20260331-9ca8b863）；实现/测试修复完成（T-20260331-1a0e9a80）；复审不通过（T-20260331-c6687cf5，PM-003 未覆盖 `symbol_variable.ptr` 旧子模块禁止导入）；legacy 闭环修复完成（T-20260331-7021c77d）；二次复审通过（T-20260331-7e44f461）；合并前同步确认通过（T-20260331-12791f9c）；合并完成（T-20260331-4aff734d，commit=29e6c29，`git fetch origin` 成功，cleanup 已完成）。
- `P2`：spec 完成（T-20260331-3a5920a8）；审查不通过（T-20260331-00bde293，`Ptr` 未导出且 `PM-008/PM-009` 缺失）；实现/测试修复完成（T-20260331-1a0e9a80）；复审不通过（T-20260331-c6687cf5，PM-003 未覆盖 `symbol_variable.ptr` 旧子模块禁止导入）；legacy 闭环修复完成（T-20260331-7021c77d）；二次复审通过（T-20260331-7e44f461）；随 `P1` 合并完成（T-20260331-4aff734d，commit=29e6c29）。
- `P3`：spec 完成（T-20260331-113a2e65）；审查不通过（T-20260331-75761e56，`dialect/ast/emit_mlir` 侧实现与测试缺失）；当前进入实现/测试修复链路（T-20260331-975657f4）。
- `P4`：spec 完成（T-20260331-435f624d）；审查不通过（T-20260331-75761e56，`dialect/ast/emit_mlir` 侧实现与测试缺失）；当前并入实现/测试修复链路（T-20260331-975657f4）。
- `P5`：spec 完成（T-20260331-4368dd76）；审查不通过（T-20260331-75761e56，`dialect/ast/emit_mlir` 侧实现与测试缺失）；当前并入实现/测试修复链路（T-20260331-975657f4）。
- `P6`：spec 完成（T-20260331-531607b5）；审查不通过（T-20260331-d0973316，`PtrArgAST + build_func_op/build_func_op_from_ast` 到 `!symbol.ptr<f32>` 的实现/测试缺失）；当前进入实现/测试修复链路（T-20260331-ca4d08b2）。
- `I1`：实现完成（T-20260331-eeead1f1）；复审不通过（T-20260331-06dc7aec，`spec/symbol_variable/package_api.md` 中 Ptr dtype 示例与实现不一致）；spec 修复完成（T-20260331-e66286b4）；复审通过（T-20260331-96e43990）；合并完成（T-20260331-b6fb538a，commit=bc0f7db，单次 `git fetch origin` 超时，不影响完成判定，cleanup 已完成）。
- `I2`：抢跑建档已清理（原 T-20260331-2cda06b1 已删除）；待 `P1~P6` 任务块闭环后再重建。
- 当前建议推进顺序：`P1/P2` 已封板；下一步在实现位空闲后推进 `P3/P4/P5` 修复（T-20260331-975657f4），随后推进 `P6` 实现/测试修复（T-20260331-ca4d08b2）；待 `P1~P6` 任务块按“spec+实现/测试+审查/复审+合并”闭环后，再决定是否重建 `I2`。

## 功能说明

- 本计划用于收敛“在 Python 上层新增公开 `class Ptr`，允许它作为 DSL 函数输入解析，并在 IR 中以 `!symbol.ptr<dtype>` 承载”的公开契约。
- 当前阶段已进入实现、测试、审查、复审与合并收口，不允许停留在 spec-only 状态。
- 本次方案明确采用两层表示：
  - Python 上层：公开 `class Ptr`，用于用户编写 DSL 函数注解与传入 runtime args。
  - IR 层：归属 `symbol dialect` 的 `!symbol.ptr<dtype>`，用于 `func.func` 输入签名承载。
- `ptr` 不带名字，只表达 pointee dtype；不表达地址名、shape、stride、rank、space 或 offset。
- 文档中出现的 `Ptr`、`PtrArgAST`、`!symbol.ptr<f32>` 都是目标公开名字/目标公开文本；当前主仓尚未实现，管理员与执行者不得把它们误认为现有接口。

## 使用示例

```python
from kernel_gen.symbol_variable import Ptr
from kernel_gen.dsl.mlir_gen import build_func_op
from xdsl.dialects.builtin import f32

def kernel(data: Ptr(f32)) -> None:
    return None


func_op = build_func_op(kernel, Ptr(f32))
```

- 目标签名：`func.func @kernel(%arg0: !symbol.ptr<f32>)`。
- 上层 `Ptr(f32)` 与 IR `!symbol.ptr<f32>` 的共同含义都是“指向 `f32` 的指针类型”，而不是“名为 data 的指针”。
- 本示例只说明目标输入签名与公开类型收敛方向；当前主仓并不承诺已经支持这段代码。

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`大闸蟹`
- `文档`：[`ARCHITECTURE/plan/ptr_symbol_func_input_plan.md`](../../ARCHITECTURE/plan/ptr_symbol_func_input_plan.md)
- `spec`：
  - `spec/symbol_variable/ptr.md`（计划新增）
  - [`spec/symbol_variable/package_api.md`](../../spec/symbol_variable/package_api.md)
  - [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)
  - [`spec/dsl/ast.md`](../../spec/dsl/ast.md)
  - [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
  - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
- `功能实现`：
  - `kernel_gen/symbol_variable/ptr.py`（计划新增）
  - [`kernel_gen/symbol_variable/__init__.py`](../../kernel_gen/symbol_variable/__init__.py)
  - [`kernel_gen/dialect/symbol.py`](../../kernel_gen/dialect/symbol.py)
  - [`kernel_gen/dsl/ast.py`](../../kernel_gen/dsl/ast.py)
  - [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py)
  - [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py)
- `test`：
  - `test/symbol_variable/test_ptr.py`（计划新增）
  - [`test/symbol_variable/test_package_api.py`](../../test/symbol_variable/test_package_api.py)
  - [`test/dialect/test_symbol_dialect.py`](../../test/dialect/test_symbol_dialect.py)
  - [`test/dsl/test_ast.py`](../../test/dsl/test_ast.py)
  - [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py)
  - [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py)

## 管理员分发入口

- 计划文件：[`ARCHITECTURE/plan/ptr_symbol_func_input_plan.md`](../../ARCHITECTURE/plan/ptr_symbol_func_input_plan.md)
- 当前可放行任务：`ptr` 首批实现/测试任务（需由管理员新建，并继续遵守一人一任务与依赖顺序）
- 放行顺序：
  1. `P1 DONE` 后，才可放行 `P2`、`P3`
  2. `P1/P3 DONE` 后，才可放行 `P4`
  3. `P3/P4 DONE` 后，才可放行 `P5`
  4. `P2/P3/P4 DONE` 后，才可放行 `P6`
- 硬门禁：
  - `P1~P6` 未全部 `DONE` 前，不得创建实现/测试/审查/复审任务。
  - 不得把本文中的目标公开名误判为“仓库当前已存在接口”。
  - 不得新增 `ptr dialect`、`SymbolPtr`、`parse_ptr`、`emit_ptr`、`lower_ptr` 这类额外 facade。

## 计划目标

- 在 Python 上层新增公开 `class Ptr`，作为 DSL 用户可直接构造和传入的类型对象。
- 在 `kernel_gen.symbol_variable` 包入口公开导出 `Ptr`。
- 在 `symbol dialect` 中新增 `!symbol.ptr<dtype>` 类型分支，固定承载 `Ptr(dtype)` 的 IR 形态。
- 让 DSL 能解析 `def kernel(data: Ptr(f32)) -> None:` 这类函数输入，并在 `build_func_op(...)` / `build_func_op_from_ast(...)` 中将其 lowering 为 `func.func` 的 `!symbol.ptr<f32>` 输入签名。
- 明确 `Ptr(dtype)` / `!symbol.ptr<dtype>` 与 `SymbolDim` / `!symbol.int<"expr">` 同属项目公开类型体系，但职责完全不同：前者是 pointer type carrier，后者是整数符号值。

## 非目标

- 不在本计划中定义 pointer 名字、地址值、地址表达式、offset、shape、stride、rank、layout 或 memory 元信息。
- 不在本计划中定义解引用、load/store、pointer arithmetic、pointer compare、address cast、alias analysis、ownership、lifetime 或 pointee memory model。
- 不在本计划中定义 `emit_c`、`gen_kernel`、runtime/include、backend codegen 行为。
- `ptr` v1 只冻结“上层类型 + 包导出 + 函数输入解析 + IR 类型承载 + 签名 lowering + 表达式拒绝边界”；不承诺 `ptr` 返回值，不承诺函数体内 `ptr` 运算语义。
- 不新增独立 `ptr dialect`，也不新增具名 `SymbolPtr` 对象。

## 当前真实断点

1. [`kernel_gen/symbol_variable`](../../kernel_gen/symbol_variable) 当前没有公开 `Ptr` 类。
2. [`spec/symbol_variable/package_api.md`](../../spec/symbol_variable/package_api.md) 当前包导出集合没有 `Ptr`。
3. [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md) 当前只承诺整数符号值 `!symbol.int<...>`，没有 `!symbol.ptr<dtype>`。
4. [`spec/dsl/ast.md`](../../spec/dsl/ast.md) 当前函数输入只有 `TensorAST` 与 `ScalarArgAST`；没有独立的 `PtrArgAST`，也没有 `Ptr(f32)` 注解入口。
5. [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md) 当前没有固定“ptr 只能承载函数输入类型、不能进入算术/shape/stride 查询”的拒绝边界。
6. [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md) 当前 `build_func_op(...)` 没有 `Ptr(f32) -> !symbol.ptr<f32>` 的签名 lowering 契约。

## 目标公开契约草案

### Python 上层 `class Ptr`

- 名称：`Ptr`
- 目标公开导入：`from kernel_gen.symbol_variable import Ptr`
- 含义：表示“指向某个 element dtype 的指针类型对象”。
- 当前最小强制示例：`Ptr(f32)`。
- 目标约束：
  - `Ptr` 必须只接收 `1` 个 dtype 参数。
  - `Ptr` 不带名字；`Ptr(f32)` 与 `Ptr(f32)` 的等价性只由 dtype 决定。
  - `Ptr` 不得承载 shape、stride、rank、space、offset 或地址字面量。
  - `Ptr` 不是 `Memory`，也不是 `SymbolDim`。

### IR 类型 `!symbol.ptr<dtype>`

- 正式文本：`!symbol.ptr<f32>`
- 目标约束：
  - `symbol.ptr` 归属 `symbol dialect`，不是独立 `ptr dialect`。
  - `dtype` 表示 pointee element type，不表示地址名，不表示 shape。
  - `!symbol.ptr<f32>` 与 `!symbol.int<"N">` 不是同一类，不允许隐式互转。
  - `symbol.ptr` 不参与 `symbol.add/sub/mul/div/floordiv`、`symbol.eq/ne/lt/le/gt/ge`、`symbol.get_dim`、`symbol.get_stride`。

### DSL 输入语义

- 目标 AST 节点名：`PtrArgAST`
- 目标公开注解：`def kernel(data: Ptr(f32)) -> None: ...`
- `build_func_op(kernel, Ptr(f32))` 必须把函数第一个输入 lowering 为 `!symbol.ptr<f32>`。
- 若注解是 `Ptr(f32)`，但运行时实参不是 `Ptr(f32)` 族对象，必须报错，不得回退成 `!symbol.int<...>`、`i32` 或 `!nn.memory<...>`。
- 若注解 dtype 与运行时 `Ptr(dtype)` 的 dtype 不一致，必须报错，不得静默改签名。
- v1 不要求 `ptr` 能参与函数体内表达式计算；任何算术、比较、`get_shape()`、`get_stride()`、memory metadata 查询都必须明确拒绝。

## 管理执行规则

- 本计划只定义 `spec任务`，不在本文中分发实现任务。
- 每个任务只改 `1` 个 `md` 文件。
- 依赖统一写成硬门禁：`未满足则不得开始`。
- 任务关闭条件以“文档命中 + 绑定测试函数定义完整”为准，不以当前代码是否已实现为准。
- 若执行者试图跳过 Python 上层 `Ptr`、只在 dialect 层做类型，或把 `ptr` 再拆成独立 dialect、继续加 pointer name、或把 `ptr` 混回 `symbol.int` 整数链路，应直接退回。

## 任务依赖

- `P1`：无前置，必须首先完成。
- `P2`：依赖 `P1`。
- `P3`：依赖 `P1`。
- `P4`：依赖 `P1 DONE` 与 `P3 DONE`。
- `P5`：依赖 `P3 DONE` 与 `P4 DONE`。
- `P6`：依赖 `P2 DONE` 与 `P3 DONE` 与 `P4 DONE`。
- `P2` / `P3`：在 `P1 DONE` 后可并行。
- 任意实现任务：依赖 `P1 DONE`、`P2 DONE`、`P3 DONE`、`P4 DONE`、`P5 DONE`、`P6 DONE`。

## 任务清单

### P1. 新增 Python 上层 `Ptr` 公开契约

- 任务类型：`spec任务`
- 目标文件：`spec/symbol_variable/ptr.md`
- 目标：新增 Python 上层 `class Ptr` 的公开语义、构造参数、失败边界与示例。
- 边界：只定义上层 `Ptr` 类型对象；不定义 IR 文本，不定义 DSL lowering，不定义 codegen。
- 注意事项：
  - 不得把 `Ptr` 写成 `SymbolDim` 的别名、子类兼容名或 `Memory` 的特例。
  - 不得给 `Ptr` 增加 name 参数；不允许 `Ptr("data", f32)` 这类具名形式。
  - 必须明确 `Ptr` 只表示 pointee dtype，不表示地址值、shape 或 stride。
- 依赖：`BLOCKER: none`
- 可改文件：`spec/symbol_variable/ptr.md`
- 下游需要覆盖层：`symbol_variable/__init__.py`、`dialect/symbol.py`、`dsl/ast`、`dsl/mlir_gen`
- 示例：

```python
from kernel_gen.symbol_variable import Ptr
from xdsl.dialects.builtin import f32

ptr = Ptr(f32)
```

- 验收标准：
  - `test_ptr_preserves_pointee_dtype`
    - 输入：`ptr = Ptr(f32)`。
    - 预期输出：`repr(ptr)` 或等价公开文本包含 `Ptr(f32)`；`ptr` 的公开 pointee dtype 为 `f32`。
  - `test_ptr_rejects_missing_dtype`
    - 输入：`Ptr()`。
    - 预期输出：抛 `TypeError`，消息包含 `Ptr requires exactly one dtype`。
  - `test_ptr_rejects_extra_args`
    - 输入：`Ptr(f32, f32)`。
    - 预期输出：抛 `TypeError`，消息包含 `Ptr requires exactly one dtype`。
  - `test_ptr_is_not_memory_or_symbol_dim`
    - 输入：`Ptr(f32)` 与 `Memory(...)` / `SymbolDim("N")`。
    - 预期输出：文档明确三者不是同类，不存在公开别名关系。
- 验证命令：

```bash
rg -n 'class Ptr|Ptr\(f32\)|Ptr requires exactly one dtype|不带名字|不表示地址值|不是 Memory|不是 SymbolDim' spec/symbol_variable/ptr.md -S
```

- `READY_IF: spec/symbol_variable/ptr.md 不被其他在途任务占用`
- `DISPATCH_RULE: ONLY_IF READY_IF=true`
- `CLOSE_IF: 上述 rg 命令 exit code == 0`
- `FAIL_ROUTING: 若文档把 Ptr 写成具名指针、Memory 特例或 SymbolDim 变体，退回 P1`

### P2. 冻结 `kernel_gen.symbol_variable` 包导出 `Ptr`

- 任务类型：`spec任务`
- 目标文件：[`spec/symbol_variable/package_api.md`](../../spec/symbol_variable/package_api.md)
- 目标：明确 `kernel_gen.symbol_variable` 对外导出 `Ptr`，并写清 `Ptr` 与 `Memory` / `SymbolDim` 的职责边界。
- 边界：只改 package API 文档，不定义 IR 类型，不定义 DSL lowering。
- 注意事项：
  - 不得要求用户从 `dialect` 层导入 `Ptr` 作为 Python 上层唯一入口。
  - 不得把 `Ptr` 与 `Memory`、`SymbolDim` 混写成“都属于同一上层 shape 类型”。
- 依赖：`BLOCKER: P1`
- 可改文件：[`spec/symbol_variable/package_api.md`](../../spec/symbol_variable/package_api.md)
- 下游需要覆盖层：`symbol_variable/__init__.py`
- 示例：

```python
from kernel_gen.symbol_variable import Memory, Ptr, SymbolDim
```

- 验收标准：
  - `test_symbol_variable_package_exports_ptr`
    - 输入：`from kernel_gen.symbol_variable import Ptr`。
    - 预期输出：导入成功，且 `Ptr(f32)` 可构造。
  - `test_symbol_variable_package_keeps_ptr_memory_symbol_dim_distinct`
    - 输入：`Ptr(f32)`、`Memory(...)`、`SymbolDim("N")`。
    - 预期输出：文档明确三者公开职责不同。
- 验证命令：

```bash
rg -n 'Ptr' spec/symbol_variable/package_api.md -S
rg -n 'Memory.*Ptr|Ptr.*Memory|SymbolDim.*Ptr|Ptr.*SymbolDim|不同公开语义|不同对象' spec/symbol_variable/package_api.md -S
```

- `READY_IF: P1 CLOSE_IF=true`
- `DISPATCH_RULE: ONLY_IF READY_IF=true`
- `CLOSE_IF: 上述 2 条 rg 命令 exit code == 0`
- `FAIL_ROUTING: 若 package_api 仍未导出 Ptr 或职责边界混写，退回 P2`

### P3. 在 symbol dialect 冻结 `!symbol.ptr<dtype>` 公开契约

- 任务类型：`spec任务`
- 目标文件：[`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)
- 目标：在 `symbol dialect` 中新增 `ptr` 类型公开契约，冻结 `!symbol.ptr<dtype>` 的文本、verifier 和非目标边界，并明确它与上层 `Ptr(dtype)` 的桥接关系。
- 边界：只定义 IR 类型及桥接责任；不定义 ptr op，不定义 codegen，不定义 runtime/include。
- 注意事项：
  - 不得新建 `spec/dialect/ptr.md`。
  - 不得把 `symbol.ptr` 写成 `symbol.int` 的别名或“先按 int 表示，后续再收敛”。
  - 必须明确 `symbol.ptr` 不参与 `symbol.add/sub/mul/div/floordiv`、比较、`get_dim`、`get_stride`。
- 依赖：`BLOCKER: P1`
- 可改文件：[`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)
- 下游需要覆盖层：`dialect/symbol.py`、`dsl/ast`、`dsl/emit_mlir`、`dsl/mlir_gen`
- 示例：

```text
!symbol.ptr<f32>
```

- 验收标准：
  - `test_symbol_ptr_type_round_trip`
    - 输入：文本 `!symbol.ptr<f32>`。
    - 预期输出：parse/print round-trip 稳定；打印结果仍为 `!symbol.ptr<f32>`。
  - `test_symbol_ptr_type_rejects_symbol_int_payload`
    - 输入：将 `!symbol.int<"N">` 当成 `symbol.ptr` 使用。
    - 预期输出：文档明确二者不是同类，不存在隐式转换。
  - `test_symbol_ptr_type_is_bridge_of_python_ptr`
    - 输入：上层 `Ptr(f32)`。
    - 预期输出：文档明确其 IR 对应类型为 `!symbol.ptr<f32>`。
- 验证命令：

```bash
rg -n '!symbol\.ptr<f32>|Ptr\(f32\).*对应.*!symbol\.ptr<f32>|不新增独立 ptr dialect|不参与 symbol\.add|不参与 symbol\.get_dim|不参与 symbol\.get_stride' spec/dialect/symbol.md -S
```

- `READY_IF: P1 CLOSE_IF=true`
- `DISPATCH_RULE: ONLY_IF READY_IF=true`
- `CLOSE_IF: 上述 rg 命令 exit code == 0`
- `FAIL_ROUTING: 若文档仍把 ptr 写成独立 dialect、具名指针或 symbol.int 变体，退回 P3`

### P4. 在 AST 层新增 `PtrArgAST` 与 `Ptr(f32)` 注解入口

- 任务类型：`spec任务`
- 目标文件：[`spec/dsl/ast.md`](../../spec/dsl/ast.md)
- 目标：在函数签名 AST 中新增 `PtrArgAST`，并冻结 `Ptr(f32)` 参数注解的解析规则与拒绝路径。
- 边界：只定义 AST 节点与注解解析规则；不定义签名 lowering 结果，不定义 body-level ptr 运算。
- 注意事项：
  - 不得继续把 `Ptr(f32)` 输入塞进 `ScalarArgAST(value_type=int)`。
  - 必须明确 `Ptr(f32)` 是显式注解入口；不要写成“未注解也可自动推断 ptr”。
  - 必须明确 `PtrArgAST` 不支持 `get_shape()`、`get_stride()`。
  - 不得把 `Ptr(f32)` 说成 `TensorAST` 或 `Memory`。
- 依赖：`BLOCKER: P1 P3`
- 可改文件：[`spec/dsl/ast.md`](../../spec/dsl/ast.md)
- 下游需要覆盖层：`dsl/ast.py`、`dsl/emit_mlir.py`、`dsl/mlir_gen.py`
- 示例：

```python
from kernel_gen.symbol_variable import Ptr
from xdsl.dialects.builtin import f32


def kernel(data: Ptr(f32)) -> None:
    return None
```

- 验收标准：
  - `test_parse_function_accepts_ptr_annotation`
    - 输入：`def kernel(data: Ptr(f32)) -> None: return None`。
    - 预期输出：`func_ast.inputs == [PtrArgAST(name="data", pointee_type=f32)]`；`func_ast.outputs == []`。
  - `test_parse_function_rejects_ptr_without_dtype`
    - 输入：`def kernel(data: Ptr()) -> None: return None`。
    - 预期输出：抛 `AstParseError`，消息包含 `Ptr requires exactly one dtype`。
  - `test_parse_function_rejects_ptr_extra_args`
    - 输入：`def kernel(data: Ptr(f32, f32)) -> None: return None`。
    - 预期输出：抛 `AstParseError`，消息包含 `Ptr requires exactly one dtype`。
  - `test_parse_function_rejects_get_shape_on_ptr_arg`
    - 输入：函数体包含 `data.get_shape()[0]`，其中 `data: Ptr(f32)`。
    - 预期输出：抛解析错误，消息包含 `ptr input does not support get_shape`。
- 验证命令：

```bash
rg -n 'PtrArgAST|Ptr\(f32\)|Ptr requires exactly one dtype|ptr input does not support get_shape|ptr input does not support get_stride|不支持未注解推断 ptr' spec/dsl/ast.md -S
```

- `READY_IF: P1 CLOSE_IF=true AND P3 CLOSE_IF=true`
- `DISPATCH_RULE: ONLY_IF READY_IF=true`
- `CLOSE_IF: 上述 rg 命令 exit code == 0`
- `FAIL_ROUTING: 若 AST 仍把 ptr 写成 ScalarArgAST、TensorAST 或允许未注解推断，退回 P4`

### P5. 在 emit_mlir 层冻结 ptr 表达式拒绝边界

- 任务类型：`spec任务`
- 目标文件：[`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
- 目标：明确 `ptr` 在 v1 只作为函数输入类型承载存在；一旦进入表达式 lowering，必须固定报错而不是隐式降级。
- 边界：只定义 body-level 拒绝边界；不定义 ptr op，不定义解引用、load/store、算术、比较或 memory query。
- 注意事项：
  - 不得在本任务中引入 `symbol.ptr.add`、`ptr.load`、`ptr.store` 等新 op 名。
  - 不得把 `ptr` 误写为可以参与 `symbol.add/sub/mul/div/floordiv` 或比较链路。
  - 必须把拒绝路径写成固定错误，不允许“实现自定”或“后续再看”。
- 依赖：`BLOCKER: P3 P4`
- 可改文件：[`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
- 下游需要覆盖层：`dsl/emit_mlir.py`
- 示例：

```python
from kernel_gen.symbol_variable import Ptr
from xdsl.dialects.builtin import f32


def kernel(data: Ptr(f32)):
    return data + data
```

- 验收标准：
  - `test_emit_mlir_rejects_ptr_arithmetic`
    - 输入：`return data + data`，其中 `data: Ptr(f32)`。
    - 预期输出：抛 `_LoweringError`，消息包含 `ptr operand does not support arithmetic`。
  - `test_emit_mlir_rejects_ptr_compare`
    - 输入：`return data == data`，其中 `data: Ptr(f32)`。
    - 预期输出：抛 `_LoweringError`，消息包含 `ptr operand does not support compare`。
  - `test_emit_mlir_rejects_ptr_get_stride`
    - 输入：函数体包含 `data.get_stride()[0]`，其中 `data: Ptr(f32)`。
    - 预期输出：抛 `_LoweringError` 或前端错误，消息包含 `ptr input does not support get_stride`。
- 验证命令：

```bash
rg -n 'ptr operand does not support arithmetic|ptr operand does not support compare|ptr input does not support get_stride|仅作为函数输入类型承载|不定义 ptr\.load|不定义 ptr\.store' spec/dsl/emit_mlir.md -S
```

- `READY_IF: P3 CLOSE_IF=true AND P4 CLOSE_IF=true`
- `DISPATCH_RULE: ONLY_IF READY_IF=true`
- `CLOSE_IF: 上述 rg 命令 exit code == 0`
- `FAIL_ROUTING: 若 emit_mlir 文档给 ptr 打开 body-level 运算空间或错误消息不固定，退回 P5`

### P6. 在 mlir_gen 层冻结 `Ptr(f32) -> !symbol.ptr<f32>` 签名 lowering

- 任务类型：`spec任务`
- 目标文件：[`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
- 目标：定义 `build_func_op(...)` / `build_func_op_from_ast(...)` 如何把 `PtrArgAST + Ptr(f32)` lowering 为 `func.func` 的 `!symbol.ptr<f32>` 输入签名。
- 边界：只冻结函数输入签名 lowering；不定义 ptr 返回值，不定义 body-level ptr lowering，不定义 codegen。
- 注意事项：
  - 这里只允许复用现有公开入口 `build_func_op(...)` 与 `build_func_op_from_ast(...)`；不得新增 facade 名。
  - 不得把 `Ptr(f32)` lowering 为 `!symbol.int<...>`、`i32`、`index` 或 `!nn.memory<...>`。
  - 不得允许注解是 `Ptr(f32)`、运行时实参却传 `123`、`Memory(...)`、`SymbolDim("N")` 时静默回退。
  - 必须明确：对 ptr 形参来说，runtime arg 的作用是“验证它也是 `Ptr(dtype)` 且 dtype 一致”，不是重新推导名字或 shape。
- 依赖：`BLOCKER: P2 P3 P4`
- 可改文件：[`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
- 下游需要覆盖层：`dsl/mlir_gen.py`
- 示例：

```python
from kernel_gen.symbol_variable import Ptr
from kernel_gen.dsl.mlir_gen import build_func_op
from xdsl.dialects.builtin import f32


def kernel(data: Ptr(f32)) -> None:
    return None


func_op = build_func_op(kernel, Ptr(f32))
```

- 验收标准：
  - `test_build_func_op_lowers_ptr_arg_to_symbol_ptr_type`
    - 输入：`def kernel(data: Ptr(f32)) -> None: return None`；`runtime_args=[Ptr(f32)]`。
    - 预期输出：`list(func_op.function_type.inputs)` 打印后等于 `["!symbol.ptr<f32>"]`；`list(func_op.function_type.outputs) == []`。
  - `test_build_func_op_rejects_non_ptr_runtime_arg_for_ptr_annotation`
    - 输入：同一函数，`runtime_args=[123]`。
    - 预期输出：抛 `AstVisitorError` 或 `_LoweringError`，消息包含 `Pointer argument requires Ptr runtime arg`。
  - `test_build_func_op_rejects_ptr_dtype_mismatch`
    - 输入：同一函数，`runtime_args=[Ptr(i32)]`。
    - 预期输出：抛 `AstVisitorError` 或 `_LoweringError`，消息包含 `Pointer argument dtype mismatch`。
  - `test_build_func_op_does_not_lower_ptr_to_symbol_int`
    - 输入：同一函数，`runtime_args=[Ptr(f32)]`。
    - 预期输出：文档明确输入类型不是 `!symbol.int<"...">`。
- 验证命令：

```bash
rg -n 'PtrArgAST|Ptr\(f32\)|!symbol\.ptr<f32>|Pointer argument requires Ptr runtime arg|Pointer argument dtype mismatch|not !symbol\.int|不定义 ptr 返回值' spec/dsl/mlir_gen.md -S
```

- `READY_IF: P2 CLOSE_IF=true AND P3 CLOSE_IF=true AND P4 CLOSE_IF=true`
- `DISPATCH_RULE: ONLY_IF READY_IF=true`
- `CLOSE_IF: 上述 rg 命令 exit code == 0`
- `FAIL_ROUTING: 若 mlir_gen 仍允许 ptr 回退到 symbol.int/i32/index/nn.memory，退回 P6`

## 自检结论

- 这版计划已经把“Python 上层 class Ptr”和“IR 中的 !symbol.ptr<dtype>”同时冻结，避免只做低层类型、缺少用户侧入口。
- 任务已经细化为 6 个单文件 spec 任务，其中 `P2/P3` 可在 `P1` 后并行，`P5/P6` 分别冻结 body-level 拒绝边界和函数签名 lowering。
- 验收标准已写成“测试函数名 + 输入 + 预期输出/报错”，管理员或评审不需要先读实现代码。
- 文本中没有再把说明性占位名写成现有仓库接口，也没有把 `ptr` 不必要地扩到 codegen/runtime。
