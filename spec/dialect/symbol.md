# symbol.md

## 功能简介

定义 `symbol dialect` 的类型与基础构件，用于在 IR 中显式表示“带符号值语义的整型标量”以及“最小 pointer type 承载”。同时提供 `!symbol.iter<start = #symbol.expr<...>, end = #symbol.expr<...>, step = #symbol.expr<...>>` 用于表达循环迭代变量语义，与 `!symbol.int<#symbol.expr<expr>>` 同样承载整数值语义，但额外记录迭代边界。该方言的核心目标是让类型本身携带一个符号表达，例如 `!symbol.int<#symbol.expr<N>>` 表示“这是一个整数值，其值语义为符号 `N`”，`!symbol.int<#symbol.expr<?>>` 表示“该整数值当前无法由稳定符号名或常量表达确定”。本方言同时作为 memory 相关符号标量语义的唯一归属：`shape`、`stride`、`offset`、`size`、循环边界等位置只要进入 IR 并需要表达单个整数符号值，就统一落到 `symbol dialect`。在此基础上，本方言允许最小范围的整数符号算术与比较 op，用于在 IR 中显式表达 `symbol.int` 标量之间的加、减、乘、除、整除、最小值以及比较计算，并提供 `symbol.to_int`（转为普通整型）与 `symbol.to_float`（转为 `f32`）两类显式类型转换 op；同时提供 `!symbol.ptr<dtype>` 作为 DSL `Ptr(dtype)` 在 IR 类型层的唯一最小载体。`symbol.for` 现支持旧的无 carried-value 形式，也支持单个 loop-carried `!symbol.int<#symbol.expr<...>>` 的 `iter_args(%acc = %init) ... -> !symbol.int<#symbol.expr<...>>` 公开语法，并通过 `symbol.yield` 终止循环体。该方言不负责张量、内存容器、通用控制流、pointer body op，或超出最小整数符号算术/比较范围的数值计算语义。

## API 列表

- `class SymbolExprAttr(expr: StringAttr)`
- `SymbolExprAttr.from_expr(expr: str) -> SymbolExprAttr`
- `class SymbolDimType(dim: StringAttr)`
- `SymbolDimType.from_name(name: str) -> SymbolDimType`
- `class SymbolValueType(expr: SymbolExprAttr)`
- `SymbolValueType.from_expr(expr: str) -> SymbolValueType`
- `SymbolValueType.get_value(self) -> int | str`
- `SymbolValueType.is_symbol(self) -> bool`
- `class SymbolIterAttr(start: SymbolExprAttr, end: SymbolExprAttr, step: SymbolExprAttr)`
- `SymbolIterAttr.from_bounds(start: str, end: str, step: str) -> SymbolIterAttr`
- `class SymbolIterType(start: SymbolExprAttr, end: SymbolExprAttr, step: SymbolExprAttr)`
- `SymbolIterType.from_bounds(start: str, end: str, step: str) -> SymbolIterType`
- `SymbolIterType.from_attr(attr: SymbolIterAttr) -> SymbolIterType`
- `class SymbolPtrType(dtype: Attribute)`
- `class SymbolConstOp(value: int | IntAttr, result_type: SymbolValueType | None = None)`
- `class SymbolAddOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute)`
- `class SymbolSubOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute)`
- `class SymbolMulOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute)`
- `class SymbolDivOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute)`
- `class SymbolFloorDivOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute)`
- `class SymbolMinOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute)`
- `class SymbolEqOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute = i1)`
- `class SymbolNeOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute = i1)`
- `class SymbolLtOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute = i1)`
- `class SymbolLeOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute = i1)`
- `class SymbolGtOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute = i1)`
- `class SymbolGeOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute = i1)`
- `class SymbolToFloatOp(value: SSAValue, result_type: Attribute)`
- `class SymbolToIntOp(value: SSAValue, result_type: Attribute)`
- `class SymbolCastOp(value: SSAValue, result_type: Attribute)`
- `class SymbolGetDimOp(memory: SSAValue, index: int | IntAttr)`
- `class SymbolGetStrideOp(memory: SSAValue, index: int | IntAttr)`
- `class SymbolYieldOp(value: SSAValue | Operation)`
- `class SymbolForOp(start: SSAValue | Operation, end: SSAValue | Operation, step: SSAValue | Operation, body: Region | Block | Sequence[Operation] | Sequence[Block], iter_attr: SymbolIterAttr | None = None, init: SSAValue | Operation | None = None, result_type: Attribute | None = None)`
- `class Symbol(Dialect)`

## 文档信息

- `spec`：[`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)
- `test`：[`test/dialect/test_symbol.py`](../../test/dialect/test_symbol.py)
- `功能实现`：[`kernel_gen/dialect/symbol.py`](../../kernel_gen/dialect/symbol.py)

## 依赖

- [`spec/symbol_variable/symbol_dim.md`](../../spec/symbol_variable/symbol_dim.md)：提供符号维度与符号表达的基础语义。
- [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)：高层 `Memory` 容器复用本方言的 memory 相关符号标量语义。
- [`spec/symbol_variable/ptr.md`](../../spec/symbol_variable/ptr.md)：定义 Python 上层 `Ptr(dtype)` 的公开语义；本文件负责其 IR 层 `!symbol.ptr<dtype>` 类型归属。
- [`spec/dialect/nn.md`](../../spec/dialect/nn.md)：提供当前 IR 层唯一合法的 `MemoryType`（当前文本载体仍为 `!nn.memory<...>`）。
- [`kernel_gen/dialect/symbol.py`](../../kernel_gen/dialect/symbol.py)：`symbol dialect` 的实现入口。

## 目标

- 为项目提供统一的“符号值类型”表达，使 IR 能直接表示某个整型标量值对应的符号语义。
- 让 `shape`、`offset`、`stride`、循环边界、算子属性等场景中的整型符号值可以在类型层面保持稳定表达。
- 收敛 memory 相关符号标量的方言归属：`Memory`、`MemoryType`、`dma` 相关 op 若需要表达单个维度、步幅、偏移或切片大小的整数符号语义，应统一复用 `SymbolExprAttr` / `SymbolValueType`，而不是在各自 spec 中再定义一套标量 symbol type。
- 提供从 memory type 读取单个维度或步幅并返回 symbol value 的查询接口，避免其他方言重复定义 `dim/stride -> value` 读取语义。
- 为后续 `nn`、`dma`、`kernel`、`dsl` 等方言提供统一的符号值口径，避免每个方言各自维护一套符号标量表达。
- 提供最小整数符号算术与比较接口，使 `!symbol.int<#symbol.expr<expr>>` 标量可在方言内完成基础加、减、乘、除、整除、最小值组合与相等/大小关系判断，而无需回退到其他算术方言。
- 明确 `symbol.gt` / `symbol.le` / `symbol.lt` / `symbol.ne` 与 `symbol.to_float` 的 dialect 合同，使上游 `a > b`、`a <= b`、`a < b`、`a != b` 与 `float(n)` 在进入 `symbol dialect` 后拥有稳定目标 op。
- 提供 `!symbol.ptr<dtype>` 作为 DSL `Ptr(dtype)` 的最小 IR pointer type 载体，使函数签名 lowering 可以稳定表达“指向某个 pointee dtype 的指针输入”。
- 提供 `SymbolIterType`，用于表达循环迭代变量语义，并支持 `!symbol.iter<start = #symbol.expr<...>, end = #symbol.expr<...>, step = #symbol.expr<...>>` 文本形式。
- 提供 `symbol.yield` 与带单个 carried `!symbol.int<#symbol.expr<...>>` 的 `symbol.for`，用于表达循环体终止与最小归约语义。
- 保持类型表达尽量简单，优先服务开发者理解和方言间协同，而不是追求复杂的符号推导系统。
- 本文件中的“符号值”指与 SSA value 绑定的单个整数值语义表达，可以是具名符号、整型表达式或整型常量，如 `N`、`M + 1`、`B*K`、`1`、`2`、`3`。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- `symbol dialect` 只定义符号值类型、最小整数符号算术 op、基础约束、`symbol.for` 的最小循环结构以及从 memory type 读取单个 dim/stride 值的查询接口；不定义张量类型、内存类型、通用控制流 op、通用内存搬运 op 或逐元素张量算术 op。
- 本方言的重点是“值的符号语义如何表达”，不是“如何求值”或“如何解方程”。
- 本方言不负责通用符号化简、约束求解、范围分析、证明或 SMT 集成。
- 符号表达式只要求可稳定打印、可比较、可校验；不要求在 dialect 内部完成复杂等价变换。
- 普通整数类型与符号值类型是不同概念：`int` 与 `!symbol.int<#symbol.expr<N>>` 不是同一类型。
- `!symbol.int<#symbol.expr<1>>`、`!symbol.int<#symbol.expr<2>>`、`!symbol.int<#symbol.expr<3>>` 这类常量整数值类型是合法的，表示“值语义已知为该整数常量”。
- `!symbol.int<#symbol.expr<N>>` 中的 `SymbolExprAttr` 表示“值语义”，不是附加注释，也不是 shape 维度列表。
- 类型中的符号表达应面向单个标量值；shape 列表、stride 列表等多值结构不直接放入本方言标量类型中。
- `Memory`、`MemorySpace`、`LocalSpaceMeta` 这类高层内存容器或空间枚举不属于本方言；本方言只负责它们内部可能出现的单个整型符号值语义。
- `symbol.get_dim` / `symbol.get_stride` 只读取 memory type 中已存在的单个维度或步幅分量，不引入新的 shape/stride 推导规则。
- `symbol.get_dim` / `symbol.get_stride` 当前只接受 IR 层 memory SSA value；按当前方言体系，该 memory type 统一指向 `MemoryType`，其当前文本载体仍为 `!nn.memory<...>`。
- `symbol.get_dim` / `symbol.get_stride` 查询到静态整数 shape/stride 条目时支持常量折叠，可在通用 folding 中物化为 `symbol.const`；符号表达与匿名动态值不得被折叠成常量。
- 若目标维度或步幅条目为匿名动态值 `?`，由于无法稳定映射为 `!symbol.int<#symbol.expr<...>>`，必须报错；本接口只接受可表示为整数常量或符号表达的条目。
- `symbol.get_dim` / `symbol.get_stride` 的轴号当前必须是静态整数索引；越界、负数或非整数轴号必须报错。
- 本方言定义 `?` 作为 unknown symbol value，仅表示当前 `!symbol.int` 的值语义无法稳定命名或静态确定；`?` 不是具名符号，不参与符号化简，也不得扩展为 memory shape/stride 的匿名动态条目。
- 当前只定义整数语义，不区分 `int/int8/int16/int32/int64` 等具体整型宽度，也不定义 `index`、浮点或其他非整型 symbol 类型。
- `SymbolIterType` 只用于表达循环迭代变量语义；`symbol.for` 的 `start/end/step` 仍要求 `!symbol.int<#symbol.expr<expr>>`，`it` 则要求 `!symbol.iter<start = #symbol.expr<...>, end = #symbol.expr<...>, step = #symbol.expr<...>>`。
- `symbol.for` 支持的循环承载值仅限一个 `!symbol.int<#symbol.expr<...>>` 累计值；该能力服务于成本函数一类“循环内累计、循环外返回”的 IR 表达，不扩展为通用多值控制流。
- `symbol.ptr` 只定义 `!symbol.ptr<dtype>` 这一类最小 pointer type；它只承载 pointee dtype，不承载名字、地址值、shape、stride、offset 或 memory space。
- `!symbol.ptr<dtype>` 中的 `dtype` 必须是合法 `TypeAttribute`，且不得为 `!symbol.int<#symbol.expr<...>>`；当前不定义 `!symbol.ptr<!symbol.int<#symbol.expr<...>>>` 这类“指向 symbol.int”的 pointer carrier。
- 当前最小算术/比较 op 范围仅包含 `symbol.add`、`symbol.sub`、`symbol.mul`、`symbol.div`、`symbol.floordiv`、`symbol.min`、`symbol.eq`、`symbol.ne`、`symbol.lt`、`symbol.le`、`symbol.gt`、`symbol.ge`；不定义取模 op、按位运算、布尔逻辑组合、广播或张量级算术。`SymbolExprAttr` 文本表达允许 `mod`，但该能力不等于新增 `symbol.mod` operation。
- `symbol.min(lhs, rhs)` 是二元整数符号最小值 op，结果类型必须为 `!symbol.int<#symbol.expr<min(lhs, rhs)>>` 或等价常量表达；它不定义多参数 `min`、张量级最小值或比较谓词结果。
- `SymbolExprAttr` 表达式层允许二元 `min(lhs, rhs)` 与 `max(lhs, rhs)`；`max` 只属于 attribute 表达式语法，本轮不新增 `symbol.max` operation。
- 当前仅定义 `symbol.to_int` 与 `symbol.to_float` 两类转换：`symbol.to_int` 将 `!symbol.int<#symbol.expr<...>>` 转为普通整型（覆盖各整型变体），`symbol.to_float` 将 `!symbol.int<#symbol.expr<...>>` 转为 `f32`；不定义反向转换或其他跨类型规则。
- `symbol.ne` / `symbol.lt` / `symbol.le` / `symbol.gt` 属于同一 compare family：统一采用二元 `!symbol.int<#symbol.expr<...>>, !symbol.int<#symbol.expr<...>> -> i1` 签名、统一 verifier 约束与统一 parse/print 规则，不能拆成互不一致的四套合同。
- 当前不在 `symbol dialect` 中定义 `ptr.load`、`ptr.store`、pointer arithmetic、pointer compare、address cast 或任何基于 `symbol.ptr` 的 body-level 计算 op。
- `symbol.const` 只用于生成整数常量的 `!symbol.int<#symbol.expr<...>>`，不承载其他类型或宽度。

### 文本语法

- 功能说明：

- 规定 `symbol dialect` 在文档、打印和调试中的正式文本语法。

- 参数：

- `expr`：符号表达。
- `dtype`：pointer pointee dtype。

- 使用示例：

```text
#symbol.expr<N>
#symbol.expr<?>
#symbol.expr<M + 1>
!symbol.int<#symbol.expr<N>>
!symbol.int<#symbol.expr<?>>
!symbol.int<#symbol.expr<3>>
!symbol.iter<start = #symbol.expr<0>, end = #symbol.expr<index>, step = #symbol.expr<1>>
!symbol.ptr<f32>
!symbol.ptr<i32>
```

- 注意事项：

- `SymbolExprAttr` 使用 `#symbol.expr<expr>`。
- `SymbolValueType` 使用 `!symbol.int<#symbol.expr<expr>>`。
- `SymbolIterType` 使用 `!symbol.iter<start = #symbol.expr<...>, end = #symbol.expr<...>, step = #symbol.expr<...>>`。
- `SymbolPtrType` 使用 `!symbol.ptr<dtype>`。
- 当前不接受按位宽区分的 legacy 整型文本，或任何非整型文本变体；`symbol.ptr` 也不定义别名文本。

- 返回值：

- 返回类型：文本约定。
- 限制：当前 spec 只定义上述四种正式语法，不额外定义等价别名。

### 类型校验规则

- 功能说明：

- 规定 `SymbolValueType`、`SymbolIterType` 与 `SymbolPtrType` 的 verifier 行为。

- 参数：

- `expr`：待校验符号表达。
- `dtype`：待校验的 pointer pointee dtype。

- 使用示例：

```python
SymbolValueType.from_expr("N")
SymbolIterType.from_bounds("0", "index", "1")
SymbolPtrType(f32)
```

- 注意事项：

- `expr` 不能为空。
- `expr` 中若出现非法字符、空白后为空、或不可解析的表达式，必须报错；公开表达式允许 `min(lhs, rhs)` 与 `max(lhs, rhs)` 表示整数符号最值，允许 `floordiv`、`ceildiv`、`mod` 关键字中缀，拒绝裸 `/` 与 `//`。
- `expr` 允许纯整数字面量，`!symbol.int<#symbol.expr<1>>`、`!symbol.int<#symbol.expr<2>>`、`!symbol.int<#symbol.expr<3>>` 都必须视为合法类型表达。
- `expr` 允许单独的 `?`，`SymbolValueType.from_expr("?").get_value()` 必须返回 `"?"`，`SymbolValueType.from_expr("?").is_symbol()` 必须返回 `False`。
- `iter<begin,end,step>` 文本不是 `SymbolValueType` 或 `SymbolExprAttr` 的合法表达片段；`2 - iter<0, 8, 1>`、`2 - f0` 这类由 SSA 名称或迭代变量文本拼出的 result 表达不得作为迭代变量算术结果。
- `SymbolIterType` 的表达式规则与 `SymbolValueType` 一致，打印后再解析必须得到等价类型对象。
- 旧文本 `!symbol.iter<"expr">` 不再是公开语法，必须被 parser 拒绝；调用方必须显式写出 `start/end/step` 三个 `SymbolExprAttr`。
- 同一个 `SymbolValueType` 的相等性比较只比较整数语义下的 `expr`。
- 打印后再解析必须能得到等价类型对象。
- `!symbol.int<#symbol.expr<N>>` 表示“该 SSA value 的整数值由符号 `N` 表示”，不是变量声明；`!symbol.int<#symbol.expr<1>>`、`!symbol.int<#symbol.expr<2>>`、`!symbol.int<#symbol.expr<3>>` 表示该值已知为对应常量整数。
- `SymbolPtrType` 的 `dtype` 必须为 `TypeAttribute`；若不是类型 attribute，必须报错。
- `SymbolPtrType` 的 `dtype` 不得为 `SymbolValueType`；`!symbol.ptr<!symbol.int<#symbol.expr<N>>>` 必须视为非法。
- `!symbol.ptr<dtype>` 打印后再解析必须能得到等价类型对象。

- 返回值：

- 返回类型：校验规则定义。
- 限制：仅校验整数符号类型表达与 pointer carrier 的合法性，不负责判断两个不同表达式是否数学等价，也不定义 pointer body 语义。

### Unknown、算术 verifier 与 fold 规则

- 功能说明：

- 规定 `?`、`symbol.iter`、binary arithmetic 与 compare fold 的公开语义。

- 参数：

- `lhs`：二元 op 左操作数，类型必须是 `!symbol.int<#symbol.expr<...>>` 或 `!symbol.iter<...>`。
- `rhs`：二元 op 右操作数，类型必须是 `!symbol.int<#symbol.expr<...>>` 或 `!symbol.iter<...>`。
- `result_type`：二元算术 op 的结果类型，必须是 `!symbol.int<#symbol.expr<...>>`；compare op 的结果类型固定为 `i1`。

- 使用示例：

```python
from xdsl.dialects.builtin import i1
from kernel_gen.dialect.symbol import SymbolAddOp, SymbolEqOp, SymbolValueType

unknown_type = SymbolValueType.from_expr("?")
sum_op = SymbolAddOp(lhs, rhs, unknown_type)
eq_op = SymbolEqOp(lhs, rhs, i1)
```

- 注意事项：

- `symbol.add/sub/mul/div/floordiv/min` 任一 operand 为 `!symbol.iter<...>` 时，result type 必须为 `!symbol.int<#symbol.expr<?>>`。
- `symbol.add/sub/mul/div/floordiv/min` 任一 operand 为 `!symbol.int<#symbol.expr<?>>` 时，result type 必须为 `!symbol.int<#symbol.expr<?>>`。
- 两个 operand 均为确定 `!symbol.int` 时，result type 可以是确定表达，也可以保守写成 `!symbol.int<#symbol.expr<?>>`。
- fold 只在当前 operand 均为静态整数时发生；result type 为 `!symbol.int<#symbol.expr<?>>` 时仍应物化为确定 `symbol.const`。
- 当前 operand 为 `!symbol.int<#symbol.expr<?>>`、动态符号表达或 `!symbol.iter<...>` 时不得 fold 为常量。
- `symbol.eq/ne/lt/le/gt/ge` 结果固定为 `i1`；静态整数 operand 可 fold 为 `arith.constant` 的 `i1` bool，动态符号、`?` 或 `symbol.iter` operand 不 fold。

- 返回值：

- 返回类型：arith op 返回 `SymbolAddOp` / `SymbolSubOp` / `SymbolMulOp` / `SymbolDivOp` / `SymbolFloorDivOp` / `SymbolMinOp` 实例；compare op 返回 `SymbolEqOp` / `SymbolNeOp` / `SymbolLtOp` / `SymbolLeOp` / `SymbolGtOp` / `SymbolGeOp` 实例。
- 限制：`?` 仅表示 unknown scalar symbol value，不定义 `!symbol.bool<?>`，不允许 compare 返回 `!symbol.int<#symbol.expr<...>>`。

### Memory 相关符号标量归属

- 功能说明：

- 规定 memory 相关符号值在 IR 层的归属边界。
- 当 `shape`、`stride`、`offset`、`size` 等 memory 元信息被单独建模为整数标量 attribute/type 时，统一由 `symbol dialect` 负责其整数符号语义表达。

- 参数：

- `expr(string)`：单个 memory 元信息标量对应的整数语义表达，例如 `N`、`K*N`、`3`。

- 使用示例：

```text
#symbol.expr<K*N>
!symbol.int<#symbol.expr<3>>
!symbol.int<#symbol.expr<N>>
```

- 注意事项：

- 本归属规则只覆盖“单个整数标量”的 symbol 语义，不直接承载 `shape=[M, N]` 这类多值结构。
- `spec/symbol_variable/memory.md` 负责高层 `Memory` 对象、空间枚举与默认 stride 规则；`symbol dialect` 负责其中单个维度或步幅分量的整数 symbol 语义。
- 常量整数分量与具名符号分量同样适用本规则；`!symbol.int<#symbol.expr<1>>`、`!symbol.int<#symbol.expr<2>>`、`!symbol.int<#symbol.expr<3>>` 都是合法 memory 元信息标量表达。

- 返回值：

- 返回类型：归属规则定义。
- 限制：只定义 memory 元信息中的单值整型 symbol 语义，不定义 memory 容器、memory type 或 memory space。

### `symbol.const`

- 功能说明：

- 定义整数常量进入 `symbol dialect` 的最小 op。
- 以整数 attribute 记录常量值，并输出对应的 `!symbol.int<#symbol.expr<...>>` 结果类型。

- 参数：

- `value(integer)`：整数常量。
- `result_type(type)`：结果类型，必须为 `!symbol.int<#symbol.expr<...>>`。

- 使用示例：

```text
%one = symbol.const 1 : !symbol.int<#symbol.expr<1>>
%neg = symbol.const -4 : !symbol.int<#symbol.expr<-4>>
```

- 注意事项：

- `value` 必须是整数 attribute；不接受布尔值或浮点值。
- 结果类型必须为 `!symbol.int<#symbol.expr<...>>`，且表达式内容必须与常量值一致。
- parse/print 必须稳定遵循 `symbol.const <value> : !symbol.int<#symbol.expr<...>>` 的公开文本形式。

- 返回值：

- 返回类型：`!symbol.int<#symbol.expr<value>>`
- 限制：仅用于生成整数常量，不承载其他类型或宽度。

## API详细说明

### `class SymbolExprAttr(expr: StringAttr)`

- api：`class SymbolExprAttr(expr: StringAttr)`
- 参数：
  - `expr`：符号表达式文本；类型 `StringAttr`；无默认值；不允许 `None` 或空字符串；必须是可 canonicalize 的公开表达式。
- 返回值：`SymbolExprAttr` 实例。
- 使用示例：

  ```python
  from xdsl.dialects.builtin import StringAttr
  from kernel_gen.dialect.symbol import SymbolExprAttr

  value = SymbolExprAttr(StringAttr("1 + N"))
  ```
- 功能说明：构造或表示 `SymbolExprAttr` 对应的 symbol dialect attribute，构造期将表达式归一到 canonical 文本。
- 注意事项：表达式允许整数、标识符、`?`、`+`、`-`、`*`、`floordiv`、`ceildiv`、`mod`、`min(lhs, rhs)`、`max(lhs, rhs)` 和括号；裸 `/`、`//`、quoted string、`iter<...>` 片段和 nested alias 不是公开语法。

### `SymbolExprAttr.from_expr(expr: str) -> SymbolExprAttr`

- api：`SymbolExprAttr.from_expr(expr: str) -> SymbolExprAttr`
- 参数：
  - `expr`：符号表达式文本；类型 `str`；无默认值；不允许 `None` 或空字符串；规则同 `SymbolExprAttr(...)`。
- 返回值：`SymbolExprAttr` 实例。
- 使用示例：

  ```python
  from kernel_gen.dialect.symbol import SymbolExprAttr

  value = SymbolExprAttr.from_expr("N floordiv 2")
  ```
- 功能说明：从公开字符串构造 `SymbolExprAttr`，并立即按 canonical 规则归一。
- 注意事项：该入口不接受裸 `/` 或 `//`；除法相关表达必须写作 `floordiv`、`ceildiv` 或 `mod`。

### `class SymbolDimType(dim: StringAttr)`

- api：`class SymbolDimType(dim: StringAttr)`
- 参数：
  - `dim`：符号维度名称；类型 `StringAttr`；无默认值；不允许 `None` 或空字符串；必须匹配 `[A-Za-z_][A-Za-z0-9_]*`。
- 返回值：`SymbolDimType` 实例。
- 使用示例：

  ```python
  from xdsl.dialects.builtin import StringAttr
  from kernel_gen.dialect.symbol import SymbolDimType

  value = SymbolDimType(StringAttr("BLOCK_M"))
  ```
- 功能说明：构造或表示 `SymbolDimType` 对应的 symbol dialect type。
- 注意事项：`SymbolDimType` 本轮不删除，但 `SymbolExprAttr` 内部不引入 `dim<...>` 表达节点。

### `SymbolDimType.from_name(name: str) -> SymbolDimType`

- api：`SymbolDimType.from_name(name: str) -> SymbolDimType`
- 参数：
  - `name`：符号维度名称；类型 `str`；无默认值；不允许 `None` 或空字符串；必须匹配 `[A-Za-z_][A-Za-z0-9_]*`。
- 返回值：`SymbolDimType` 实例。
- 使用示例：

  ```python
  from kernel_gen.dialect.symbol import SymbolDimType

  value = SymbolDimType.from_name("BLOCK_M")
  ```
- 功能说明：从公开字符串名称构造 `SymbolDimType`。
- 注意事项：该入口只承接 symbol dim 名称，不承接 `SymbolExprAttr` 表达式。

### `class SymbolValueType(expr: SymbolExprAttr)`

- api：`class SymbolValueType(expr: SymbolExprAttr)`
- 参数：
  - `expr`：符号表达式文本；类型 `SymbolExprAttr`；无默认值；不允许 None 或空字符串；必须可稳定打印和解析。
- 返回值：`SymbolValueType` 实例。
- 使用示例：

  ```python
  from kernel_gen.dialect.symbol import SymbolExprAttr, SymbolValueType

  value = SymbolValueType(SymbolExprAttr.from_expr("N"))
  ```
- 功能说明：构造或表示 `SymbolValueType` 对应的 symbol dialect type。
- 注意事项：只允许使用本 API 列表中的公开入口；测试不得直连当前文件之外的非公开 helper。

### `SymbolValueType.from_expr(expr: str) -> SymbolValueType`

- api：`SymbolValueType.from_expr(expr: str) -> SymbolValueType`
- 参数：
  - `expr`：符号表达式文本；类型 `str`；无默认值；不允许 `None` 或空字符串；规则同 `SymbolExprAttr.from_expr(...)`。
- 返回值：`SymbolValueType` 实例。
- 使用示例：

  ```python
  from kernel_gen.dialect.symbol import SymbolValueType

  value = SymbolValueType.from_expr("N + 1")
  ```
- 功能说明：从公开字符串构造 `!symbol.int<#symbol.expr<...>>` 类型，并复用 `SymbolExprAttr` 的 canonical 规则。
- 注意事项：该入口只承接单个整数值语义，不承接 `symbol.iter`、quoted string、裸 `/` 或 `//` 文本。

### `SymbolValueType.get_value(self) -> int | str`

- api：`SymbolValueType.get_value(self) -> int | str`
- 参数：
  - `self`：当前 `SymbolValueType` 实例；由 Python 方法调用自动传入。
- 返回值：`int | str`；常量表达返回 `int`，动态符号表达返回 canonical 表达文本。
- 使用示例：

  ```python
  from kernel_gen.dialect.symbol import SymbolValueType

  assert SymbolValueType.from_expr("2 + 3").get_value() == 5
  assert SymbolValueType.from_expr("N + 1").get_value() == "N + 1"
  ```
- 功能说明：读取 `SymbolValueType` 的公开值语义，用于区分可静态确定的整数常量与仍需保留的符号表达文本。
- 注意事项：返回的字符串是表达语义文本，不是 alias 名称、SSA 名称或完整 IR 文本。

### `SymbolValueType.is_symbol(self) -> bool`

- api：`SymbolValueType.is_symbol(self) -> bool`
- 参数：
  - `self`：当前 `SymbolValueType` 实例；由 Python 方法调用自动传入。
- 返回值：`bool`；动态符号表达返回 `True`，常量表达与 `?` 返回 `False`。
- 使用示例：

  ```python
  from kernel_gen.dialect.symbol import SymbolValueType

  assert SymbolValueType.from_expr("N").is_symbol() is True
  assert SymbolValueType.from_expr("3").is_symbol() is False
  ```
- 功能说明：判断当前 `SymbolValueType` 是否承载具名或组合动态符号表达。
- 注意事项：`?` 表示未知整数值，不视为可复用的具名 symbol。

### `class SymbolIterAttr(start: SymbolExprAttr, end: SymbolExprAttr, step: SymbolExprAttr)`

- api：`class SymbolIterAttr(start: SymbolExprAttr, end: SymbolExprAttr, step: SymbolExprAttr)`
- 参数：
  - `start`：循环起始符号表达式；类型 `SymbolExprAttr`；无默认值；不允许 `None`。
  - `end`：循环结束符号表达式；类型 `SymbolExprAttr`；无默认值；不允许 `None`。
  - `step`：循环步长符号表达式；类型 `SymbolExprAttr`；无默认值；不允许 `None`。
- 返回值：`SymbolIterAttr` 实例。
- 使用示例：

  ```python
  from kernel_gen.dialect.symbol import SymbolExprAttr, SymbolIterAttr

  value = SymbolIterAttr(SymbolExprAttr.from_expr("0"), SymbolExprAttr.from_expr("N"), SymbolExprAttr.from_expr("1"))
  ```
- 功能说明：构造或表示 `#symbol.iter<start = #symbol.expr<...>, end = #symbol.expr<...>, step = #symbol.expr<...>>`。
- 注意事项：旧的单字符串迭代语法不是公开兼容入口。

### `SymbolIterAttr.from_bounds(start: str, end: str, step: str) -> SymbolIterAttr`

- api：`SymbolIterAttr.from_bounds(start: str, end: str, step: str) -> SymbolIterAttr`
- 参数：
  - `start`：循环起始表达式；类型 `str`；无默认值；规则同 `SymbolExprAttr.from_expr(...)`。
  - `end`：循环结束表达式；类型 `str`；无默认值；规则同 `SymbolExprAttr.from_expr(...)`。
  - `step`：循环步长表达式；类型 `str`；无默认值；规则同 `SymbolExprAttr.from_expr(...)`。
- 返回值：`SymbolIterAttr` 实例。
- 使用示例：

  ```python
  from kernel_gen.dialect.symbol import SymbolIterAttr

  value = SymbolIterAttr.from_bounds("0", "N", "TILE")
  ```
- 功能说明：从三个公开字符串表达构造 `SymbolIterAttr`。
- 注意事项：三个参数分别 canonicalize；不得传入旧 `iter<...>` 片段。

### `class SymbolIterType(start: SymbolExprAttr, end: SymbolExprAttr, step: SymbolExprAttr)`

- api：`class SymbolIterType(start: SymbolExprAttr, end: SymbolExprAttr, step: SymbolExprAttr)`
- 参数：
  - `start`：循环起始符号表达式；类型 `SymbolExprAttr`；无默认值；不允许 `None`。
  - `end`：循环结束符号表达式；类型 `SymbolExprAttr`；无默认值；不允许 `None`。
  - `step`：循环步长符号表达式；类型 `SymbolExprAttr`；无默认值；不允许 `None`。
- 返回值：`SymbolIterType` 实例。
- 使用示例：

  ```python
  from kernel_gen.dialect.symbol import SymbolExprAttr, SymbolIterType

  value = SymbolIterType(SymbolExprAttr.from_expr("0"), SymbolExprAttr.from_expr("N"), SymbolExprAttr.from_expr("1"))
  ```
- 功能说明：构造或表示 `!symbol.iter<start = #symbol.expr<...>, end = #symbol.expr<...>, step = #symbol.expr<...>>`。
- 注意事项：旧 `SymbolIterType.from_expr(expr: str)` 不属于公开 API。

### `SymbolIterType.from_bounds(start: str, end: str, step: str) -> SymbolIterType`

- api：`SymbolIterType.from_bounds(start: str, end: str, step: str) -> SymbolIterType`
- 参数：
  - `start`：循环起始表达式；类型 `str`；无默认值；规则同 `SymbolExprAttr.from_expr(...)`。
  - `end`：循环结束表达式；类型 `str`；无默认值；规则同 `SymbolExprAttr.from_expr(...)`。
  - `step`：循环步长表达式；类型 `str`；无默认值；规则同 `SymbolExprAttr.from_expr(...)`。
- 返回值：`SymbolIterType` 实例。
- 使用示例：

  ```python
  from kernel_gen.dialect.symbol import SymbolIterType

  value = SymbolIterType.from_bounds("0", "N", "TILE")
  ```
- 功能说明：从三个公开字符串表达构造 `SymbolIterType`。
- 注意事项：该入口不接受旧单字符串 iter 表达。

### `SymbolIterType.from_attr(attr: SymbolIterAttr) -> SymbolIterType`

- api：`SymbolIterType.from_attr(attr: SymbolIterAttr) -> SymbolIterType`
- 参数：
  - `attr`：循环迭代 attribute；类型 `SymbolIterAttr`；无默认值；不允许 `None`。
- 返回值：`SymbolIterType` 实例。
- 使用示例：

  ```python
  from kernel_gen.dialect.symbol import SymbolIterAttr, SymbolIterType

  value = SymbolIterType.from_attr(SymbolIterAttr.from_bounds("0", "N", "1"))
  ```
- 功能说明：将 `#symbol.iter<...>` 转换为对应的 `!symbol.iter<...>`。
- 注意事项：不展开、不重命名、不兼容旧单字符串 iter 文本。

### `class SymbolPtrType(dtype: Attribute)`

- api：`class SymbolPtrType(dtype: Attribute)`
- 参数：
  - `dtype`：指针承载的 pointee 类型；类型 `Attribute`；无默认值；不允许 `None`；必须是公开 xDSL type attribute。
- 返回值：`SymbolPtrType` 实例。
- 使用示例：

  ```python
  from xdsl.dialects.builtin import f32
  from kernel_gen.dialect.symbol import SymbolPtrType

  value = SymbolPtrType(f32)
  ```
- 功能说明：构造或表示 `SymbolPtrType` 对应的 symbol dialect type。
- 注意事项：`dtype` 必须是合法 xDSL type attribute；不得把 `!symbol.int` 用作 pointer pointee。

### `class SymbolConstOp(value: int | IntAttr, result_type: SymbolValueType | None = None)`

- api：`class SymbolConstOp(value: int | IntAttr, result_type: SymbolValueType | None = None)`
- 参数：
  - `value`：输入值；类型 `int | IntAttr`；无默认值；不允许 None；用于构造 `symbol.const` 的整数常量。
  - `result_type`：结果类型；类型 `SymbolValueType | None`；默认值 `None`；为 `None` 时按 `value` 推导 `!symbol.int<#symbol.expr<...>>`。
- 返回值：`SymbolConstOp` 实例。
- 使用示例：

  ```python
    from kernel_gen.dialect.symbol import SymbolConstOp, SymbolValueType

    value = SymbolConstOp(3)
    typed = SymbolConstOp(3, SymbolValueType.from_expr("3"))
    ```
- 功能说明：构造或表示 `SymbolConstOp` 对应的 symbol dialect operation。
- 注意事项：只允许使用本 API 列表中的公开入口；测试不得直连当前文件之外的非公开 helper。`bool`、`IntAttr(data=True/False)` 与 `IntegerAttr` 不是 `SymbolConstOp(...)` 的公开输入；需要 `i1` compare fold 时由 `SymbolConstantMaterializationInterface` 物化为 `arith.constant`，不经由 `symbol.const`。调用者不得把 `SymbolValueType.from_expr("?")` 作为 `symbol.const` 的直接结果类型；当 arithmetic fold 的目标 result type 是 `!symbol.int<#symbol.expr<?>>` 时，`materialize_constant(IntAttr(3), SymbolValueType.from_expr("?"))` 必须物化为确定的 `SymbolConstOp(3)` / `!symbol.int<#symbol.expr<3>>`。

### `class SymbolAddOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute)`

- api：`class SymbolAddOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute)`
- 参数：
  - `lhs`：左操作数；类型 `SSAValue | Operation`；无默认值；必须为 `!symbol.int<#symbol.expr<...>>` 或 `!symbol.iter<...>`。
  - `rhs`：右操作数；类型 `SSAValue | Operation`；无默认值；必须为 `!symbol.int<#symbol.expr<...>>` 或 `!symbol.iter<...>`。
  - `result_type`：结果类型；类型 `Attribute`；无默认值；必须为 `SymbolValueType`；若任一 operand 为 `!symbol.iter<...>` 或 `!symbol.int<#symbol.expr<?>>`，必须为 `SymbolValueType.from_expr("?")`。
- 返回值：`SymbolAddOp` 实例。
- 使用示例：

  ```python
  from kernel_gen.dialect.symbol import SymbolAddOp, SymbolValueType

  value = SymbolAddOp(lhs, rhs, SymbolValueType.from_expr("N + 1"))
  ```
- 功能说明：构造或表示 `symbol.add`。
- 注意事项：静态整数 operand 可 fold；动态、`?` 或 iter operand 不 fold，且 `?` / iter operand 的结果必须保守为 `!symbol.int<#symbol.expr<?>>`。

### `class SymbolSubOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute)`

- api：`class SymbolSubOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute)`
- 参数：同 `SymbolAddOp`。
- 返回值：`SymbolSubOp` 实例。
- 使用示例：

  ```python
  from kernel_gen.dialect.symbol import SymbolSubOp, SymbolValueType

  value = SymbolSubOp(lhs, rhs, SymbolValueType.from_expr("N - 1"))
  ```
- 功能说明：构造或表示 `symbol.sub`。
- 注意事项：不得用 SSA 名称或 `name_hint` 拼出 `2 - f0` 这类 result type；涉及 `symbol.iter` 时必须使用 `!symbol.int<#symbol.expr<?>>`。

### `class SymbolMulOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute)`

- api：`class SymbolMulOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute)`
- 参数：同 `SymbolAddOp`。
- 返回值：`SymbolMulOp` 实例。
- 使用示例：

  ```python
  from kernel_gen.dialect.symbol import SymbolMulOp, SymbolValueType

  value = SymbolMulOp(lhs, rhs, SymbolValueType.from_expr("M*N"))
  ```
- 功能说明：构造或表示 `symbol.mul`。
- 注意事项：`?` 与 `symbol.iter` 传播规则同 `SymbolAddOp`。

### `class SymbolDivOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute)`

- api：`class SymbolDivOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute)`
- 参数：同 `SymbolAddOp`。
- 返回值：`SymbolDivOp` 实例。
- 使用示例：

  ```python
  from kernel_gen.dialect.symbol import SymbolDivOp, SymbolValueType

  value = SymbolDivOp(lhs, rhs, SymbolValueType.from_expr("M floordiv N"))
  ```
- 功能说明：构造或表示 `symbol.div`。
- 注意事项：`symbol.div` 的 symbolic result 公开文本使用 `floordiv` 表达；静态 fold 仅在整除且除数非零时发生；`?` 与 `symbol.iter` 传播规则同 `SymbolAddOp`。

### `class SymbolFloorDivOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute)`

- api：`class SymbolFloorDivOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute)`
- 参数：同 `SymbolAddOp`。
- 返回值：`SymbolFloorDivOp` 实例。
- 使用示例：

  ```python
  from kernel_gen.dialect.symbol import SymbolFloorDivOp, SymbolValueType

  value = SymbolFloorDivOp(lhs, rhs, SymbolValueType.from_expr("M floordiv N"))
  ```
- 功能说明：构造或表示 `symbol.floordiv`。
- 注意事项：静态 fold 仅在除数非零时发生；`?` 与 `symbol.iter` 传播规则同 `SymbolAddOp`。

### `class SymbolMinOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute)`

- api：`class SymbolMinOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute)`
- 参数：同 `SymbolAddOp`。
- 返回值：`SymbolMinOp` 实例。
- 使用示例：

  ```python
  from kernel_gen.dialect.symbol import SymbolMinOp, SymbolValueType

  value = SymbolMinOp(lhs, rhs, SymbolValueType.from_expr("min(T, N)"))
  ```
- 功能说明：构造或表示 `symbol.min`，结果为左右整数符号值的最小值。
- 注意事项：只允许二元 `min`；不得扩展为多参数、张量级或浮点最小值；涉及 `symbol.iter` 或 `?` 时结果必须保守为 `!symbol.int<#symbol.expr<?>>`。

### `class SymbolEqOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute = i1)`

- api：`class SymbolEqOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute = i1)`
- 参数：
  - `lhs`：左操作数；类型 `SSAValue | Operation`；无默认值；必须为 `!symbol.int<#symbol.expr<...>>` 或 `!symbol.iter<...>`。
  - `rhs`：右操作数；类型 `SSAValue | Operation`；无默认值；必须为 `!symbol.int<#symbol.expr<...>>` 或 `!symbol.iter<...>`。
  - `result_type`：结果类型；类型 `Attribute`；默认值 `i1`；必须固定为 `i1`。
- 返回值：`SymbolEqOp` 实例。
- 使用示例：

  ```python
  from xdsl.dialects.builtin import i1
  from kernel_gen.dialect.symbol import SymbolEqOp

  value = SymbolEqOp(lhs, rhs, i1)
  ```
- 功能说明：构造或表示 `symbol.eq`。
- 注意事项：静态整数 operand 可 fold 为 `i1` bool 常量；动态、`?` 或 iter operand 不 fold。

### `class SymbolNeOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute = i1)`

- api：`class SymbolNeOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute = i1)`
- 参数：同 `SymbolEqOp`。
- 返回值：`SymbolNeOp` 实例。
- 使用示例：

  ```python
  from kernel_gen.dialect.symbol import SymbolNeOp

  value = SymbolNeOp(lhs, rhs)
  ```
- 功能说明：构造或表示 `symbol.ne`。
- 注意事项：compare family 结果固定为 `i1`，不定义 `!symbol.bool<?>`。

### `class SymbolLtOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute = i1)`

- api：`class SymbolLtOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute = i1)`
- 参数：同 `SymbolEqOp`。
- 返回值：`SymbolLtOp` 实例。
- 使用示例：

  ```python
  from kernel_gen.dialect.symbol import SymbolLtOp

  value = SymbolLtOp(lhs, rhs)
  ```
- 功能说明：构造或表示 `symbol.lt`。
- 注意事项：compare family 结果固定为 `i1`，不定义 compare result `symbol.int`。

### `class SymbolLeOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute = i1)`

- api：`class SymbolLeOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute = i1)`
- 参数：同 `SymbolEqOp`。
- 返回值：`SymbolLeOp` 实例。
- 使用示例：

  ```python
  from kernel_gen.dialect.symbol import SymbolLeOp

  value = SymbolLeOp(lhs, rhs)
  ```
- 功能说明：构造或表示 `symbol.le`。
- 注意事项：compare family 结果固定为 `i1`。

### `class SymbolGtOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute = i1)`

- api：`class SymbolGtOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute = i1)`
- 参数：同 `SymbolEqOp`。
- 返回值：`SymbolGtOp` 实例。
- 使用示例：

  ```python
  from kernel_gen.dialect.symbol import SymbolGtOp

  value = SymbolGtOp(lhs, rhs)
  ```
- 功能说明：构造或表示 `symbol.gt`。
- 注意事项：compare family 结果固定为 `i1`。

### `class SymbolGeOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute = i1)`

- api：`class SymbolGeOp(lhs: SSAValue | Operation, rhs: SSAValue | Operation, result_type: Attribute = i1)`
- 参数：同 `SymbolEqOp`。
- 返回值：`SymbolGeOp` 实例。
- 使用示例：

  ```python
  from kernel_gen.dialect.symbol import SymbolGeOp

  value = SymbolGeOp(lhs, rhs)
  ```
- 功能说明：构造或表示 `symbol.ge`。
- 注意事项：compare family 结果固定为 `i1`。

### `class SymbolToFloatOp(value: SSAValue, result_type: Attribute)`

- api：`class SymbolToFloatOp(value: SSAValue, result_type: Attribute)`
- 参数：
  - `value`：输入值；类型 `SSAValue`；无默认值；不允许 None，除非签名显式允许；用于当前节点、op 或转换的主输入。
  - `result_type`：`result_type` 参数；类型 `Attribute`；无默认值；不允许 None。
- 返回值：`SymbolToFloatOp` 实例。
- 使用示例：

  ```python
    from kernel_gen.dialect.symbol import SymbolToFloatOp

    value = SymbolToFloatOp(value=value, result_type=result_type)
    ```
- 功能说明：构造或表示 `SymbolToFloatOp` 对应的 symbol dialect operation。
- 注意事项：只允许使用本 API 列表中的公开入口；测试不得直连当前文件之外的非公开 helper。

### `class SymbolToIntOp(value: SSAValue, result_type: Attribute)`

- api：`class SymbolToIntOp(value: SSAValue, result_type: Attribute)`
- 参数：
  - `value`：输入值；类型 `SSAValue`；无默认值；不允许 None，除非签名显式允许；用于当前节点、op 或转换的主输入。
  - `result_type`：`result_type` 参数；类型 `Attribute`；无默认值；不允许 None。
- 返回值：`SymbolToIntOp` 实例。
- 使用示例：

  ```python
    from kernel_gen.dialect.symbol import SymbolToIntOp

    value = SymbolToIntOp(value=value, result_type=result_type)
    ```
- 功能说明：构造或表示 `SymbolToIntOp` 对应的 symbol dialect operation。
- 注意事项：只允许使用本 API 列表中的公开入口；测试不得直连当前文件之外的非公开 helper。

### `class SymbolCastOp(value: SSAValue, result_type: Attribute)`

- api：`class SymbolCastOp(value: SSAValue, result_type: Attribute)`
- 参数：
  - `value`：输入值；类型 `SSAValue`；无默认值；不允许 None，除非签名显式允许；用于当前节点、op 或转换的主输入。
  - `result_type`：`result_type` 参数；类型 `Attribute`；无默认值；不允许 None。
- 返回值：`SymbolCastOp` 实例。
- 使用示例：

  ```python
    from kernel_gen.dialect.symbol import SymbolCastOp

    value = SymbolCastOp(value=value, result_type=result_type)
    ```
- 功能说明：构造或表示 `SymbolCastOp` 对应的 symbol dialect operation。
- 注意事项：只允许使用本 API 列表中的公开入口；测试不得直连当前文件之外的非公开 helper。

### `class SymbolGetDimOp(memory: SSAValue, index: int | IntAttr)`

- api：`class SymbolGetDimOp(memory: SSAValue, index: int | IntAttr)`
- 参数：
  - `memory`：内存对象或 memory SSA value；类型 `SSAValue`；无默认值；不允许 None。
  - `index`：维度或步幅索引；类型 `int | IntAttr`；无默认值；不允许 None；必须是非负静态整数。
- 返回值：`SymbolGetDimOp` 实例。
- 使用示例：

  ```python
    from kernel_gen.dialect.symbol import SymbolGetDimOp

    value = SymbolGetDimOp(memory=memory, index=index)
    ```
- 功能说明：构造或表示 `SymbolGetDimOp` 对应的 symbol dialect operation。
- 注意事项：只能读取 memory type 中可表示为整数常量或符号表达的静态条目；负数、越界或匿名动态条目必须失败。

### `class SymbolGetStrideOp(memory: SSAValue, index: int | IntAttr)`

- api：`class SymbolGetStrideOp(memory: SSAValue, index: int | IntAttr)`
- 参数：
  - `memory`：内存对象或 memory SSA value；类型 `SSAValue`；无默认值；不允许 None。
  - `index`：维度或步幅索引；类型 `int | IntAttr`；无默认值；不允许 None；必须是非负静态整数。
- 返回值：`SymbolGetStrideOp` 实例。
- 使用示例：

  ```python
    from kernel_gen.dialect.symbol import SymbolGetStrideOp

    value = SymbolGetStrideOp(memory=memory, index=index)
    ```
- 功能说明：构造或表示 `SymbolGetStrideOp` 对应的 symbol dialect operation。
- 注意事项：只能读取 memory type 中可表示为整数常量或符号表达的静态条目；负数、越界或匿名动态条目必须失败。

### `class SymbolYieldOp(value: SSAValue | Operation)`

- api：`class SymbolYieldOp(value: SSAValue | Operation)`
- 参数：
  - `value`：yield 输入值；类型 `SSAValue | Operation`；无默认值；不允许 `None`；必须与所在 `symbol.for` 的 loop-carried result 类型一致。
- 返回值：`SymbolYieldOp` 实例。
- 使用示例：

  ```python
    from kernel_gen.dialect.symbol import SymbolYieldOp

    value = SymbolYieldOp(value=value)
    ```
- 功能说明：构造或表示 `symbol.yield` 终止 op。
- 注意事项：仅用于带单个 loop-carried value 的 `symbol.for` body；无 carried-value 的 `symbol.for` body 继续使用 no-terminator region 形状。

### `class SymbolForOp(start: SSAValue | Operation, end: SSAValue | Operation, step: SSAValue | Operation, body: Region | Block | Sequence[Operation] | Sequence[Block], iter_attr: SymbolIterAttr | None = None, init: SSAValue | Operation | None = None, result_type: Attribute | None = None)`

- api：`class SymbolForOp(start: SSAValue | Operation, end: SSAValue | Operation, step: SSAValue | Operation, body: Region | Block | Sequence[Operation] | Sequence[Block], iter_attr: SymbolIterAttr | None = None, init: SSAValue | Operation | None = None, result_type: Attribute | None = None)`
- 参数：
  - `start`：循环起始符号值；类型 `SSAValue | Operation`；无默认值；不允许 `None`；必须为 `!symbol.int<#symbol.expr<...>>`。
  - `end`：循环结束符号值；类型 `SSAValue | Operation`；无默认值；不允许 `None`；必须为 `!symbol.int<#symbol.expr<...>>`。
  - `step`：循环步长符号值；类型 `SSAValue | Operation`；无默认值；不允许 `None`；必须为 `!symbol.int<#symbol.expr<...>>` 且静态 `0` 必须被拒绝。
  - `body`：循环体；类型 `Region | Block | Sequence[Operation] | Sequence[Block]`；无默认值；不允许 `None`；必须是单块。
  - `iter_attr`：循环迭代属性；类型 `SymbolIterAttr | None`；默认值 `None`；为 `None` 时由 `start/end/step` 的 `SymbolValueType` 推导。
  - `init`：loop-carried 初始值；类型 `SSAValue | Operation | None`；默认值 `None`；`None` 表示无 carried value。
  - `result_type`：loop-carried 结果类型；类型 `Attribute | None`；默认值 `None`；传入 `init` 时必须为 `SymbolValueType` 或由 `init` 推导。
- 返回值：`SymbolForOp` 实例。
- 使用示例：

  ```python
  from kernel_gen.dialect.symbol import SymbolForOp

  value = SymbolForOp(start, end, step, body, iter_attr=iter_attr, init=init, result_type=result_type)
  ```
- 功能说明：构造或表示 `symbol.for` 半开区间循环。
- 注意事项：只承接公开 `symbol.for` 语法；loop-carried value 当前仅支持单个 `!symbol.int` 累计值，body 必须以 `symbol.yield` 结束。

### `class Symbol(Dialect)`

- api：`class Symbol(Dialect)`
- 参数：
  - `Dialect`：`Dialect` 参数；类型 `未显式标注`；无默认值；不允许 None。
- 返回值：`Symbol` 实例。
- 使用示例：

  ```python
    from kernel_gen.dialect.symbol import Symbol

    public_type = Symbol
    ```
- 功能说明：导出 symbol dialect 对象，向 xDSL 注册本文件声明的公开 attr、type 与 op。
- 注意事项：只允许使用本 API 列表中的公开入口；测试不得直连当前文件之外的非公开 helper。

## 测试

- 测试文件：`test/dialect/test_symbol.py`
- 执行命令：`pytest -q test/dialect/test_symbol.py`

### 测试目标

- 验证 `SymbolExprAttr` 的表达式构造、打印与解析。
- 验证 `SymbolValueType` 的整数-only 符号表达绑定关系。
- 验证 `SymbolIterType` 的 parse/print 稳定性与表达式校验规则。
- 验证 `#symbol.expr<expr>` 与 `!symbol.int<#symbol.expr<expr>>` 的 parse/print 稳定性。
- 验证 legacy 宽度整型文本、空表达式、非法表达式的错误路径。
- 验证 parse/print 循环稳定。
- 验证 memory 相关标量语义复用同一套整数-only symbol 规则，包括具名维度表达、乘法步幅表达与常量步幅表达。
- 验证 `symbol.add/sub/mul/div/floordiv/min` 的最小整数符号算术语义、`!symbol.int<#symbol.expr<...>>` 类型约束、parse/print 稳定性与错误路径。
- 验证 `symbol.eq/ne/lt/le/gt/ge` 的最小整数符号比较语义、`!symbol.int<#symbol.expr<...>> -> i1` 约束、parse/print 稳定性与错误路径。
- 验证 `symbol.to_int` 的整数符号到普通整型转换语义、整型变体覆盖、类型约束与 parse/print 稳定性。
- 验证 `symbol.to_float` 的整数符号到 `f32` 转换语义、类型约束与 parse/print 稳定性。
- 验证 `SymbolPtrType` 的 `!symbol.ptr<dtype>` 文本语法、verifier 约束、parse/print 稳定性，以及拒绝 `!symbol.int<#symbol.expr<...>>` 作为 dtype 的错误路径。
- 验证 `symbol.get_dim` / `symbol.get_stride` 能从 memory type 读取真实 dim/stride，并返回对应的 symbol value。
- 验证 `symbol.get_dim` / `symbol.get_stride` 读取静态整数 dim/stride 时可折叠为 `symbol.const`，读取符号表达时不折叠。
- 验证 `symbol.get_dim` / `symbol.get_stride` 的错误路径，包括非 memory type、轴号越界、匿名动态条目 `?` 与非法轴号。
- 验证 `symbol.for` 的半开区间循环语义、`start/end/step` 的 `!symbol.int<#symbol.expr<...>>` 约束、`it` 的 `!symbol.iter<...>` 约束、parse/print 稳定性与 verifier 错误路径。
- 验证 `symbol.for` 的迭代变量 `it` 必须为 `SymbolIterType`，不能是浮点、builtin 整数或其他非 `!symbol.iter<...>` 类型。
- 验证 `symbol.for` 的单个 loop-carried `!symbol.int<#symbol.expr<...>>` 形式，包括 `iter_args`、第二块参数、单结果、`symbol.yield` 与旧无 carried-value 形式继续兼容。
- 验证 `symbol.const` 生成常量的 `!symbol.int<#symbol.expr<...>>` 结果类型、parse/print 稳定性与结果类型一致性错误路径。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-SYM-001 | 解析/打印 | `SymbolExprAttr` | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_expr_attr_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_expr_attr_round_trip` |
| TC-SYM-002 | 解析/打印 | `SymbolExprAttr` | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_expr_attr_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_expr_attr_round_trip` |
| TC-SYM-003 | 边界/异常 | `SymbolExprAttr` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_expr_attr_rejects_empty_expr`、`test_symbol_verifier_rejects_illegal_expression_characters`。 | “`SymbolExprAttr`”场景按公开错误语义失败或被拒绝。 | `test_symbol_expr_attr_rejects_empty_expr`、`test_symbol_verifier_rejects_illegal_expression_characters` |
| TC-SYM-004 | 解析/打印 | `SymbolValueType` | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_value_type_round_trip_for_integer_only_semantics`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_value_type_round_trip_for_integer_only_semantics` |
| TC-SYM-005 | 解析/打印 | `SymbolValueType` | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_value_type_round_trip_for_integer_only_semantics`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_value_type_round_trip_for_integer_only_semantics` |
| TC-SYM-006 | 解析/打印 | `SymbolValueType` | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_value_type_round_trip_for_integer_only_semantics`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_value_type_round_trip_for_integer_only_semantics` |
| TC-SYM-006A | 符号语义 | `!symbol.int<#symbol.expr<?>>` unknown 公开语义 | 准备 `SymbolValueType.from_expr("?")` 与旧 `iter<...>` 文本。 | 运行 `test_symbol_value_type_unknown_public_semantics`。 | `get_value()` 返回 `"?"`，`is_symbol()` 返回 `False`，旧 `iter<...>` 表达片段被拒绝。 | `test_symbol_value_type_unknown_public_semantics` |
| TC-SYM-007 | 边界/异常 | `SymbolValueType` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_value_type_rejects_unsupported_legacy_text_forms`、`test_symbol_verifier_rejects_illegal_expression_characters`。 | “`SymbolValueType`”场景按公开错误语义失败或被拒绝。 | `test_symbol_value_type_rejects_unsupported_legacy_text_forms`、`test_symbol_verifier_rejects_illegal_expression_characters` |
| TC-SYM-008 | 边界/异常 | `SymbolValueType` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_value_type_rejects_unsupported_legacy_text_forms`。 | “`SymbolValueType`”场景按公开错误语义失败或被拒绝。 | `test_symbol_value_type_rejects_unsupported_legacy_text_forms` |
| TC-SYM-052 | 解析/打印 | `SymbolIterType` | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_iter_type_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_iter_type_round_trip` |
| TC-SYM-009 | 解析/打印 | parse/print | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_expr_attr_round_trip`、`test_symbol_value_type_round_trip_for_integer_only_semantics`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_expr_attr_round_trip`、`test_symbol_value_type_round_trip_for_integer_only_semantics` |
| TC-SYM-010 | 符号语义 | 相等性 | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_symbol_value_type_equality_depends_on_expr_only`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“相等性”场景。 | `test_symbol_value_type_equality_depends_on_expr_only` |
| TC-SYM-011 | 符号语义 | 相等性 | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_symbol_value_type_equality_depends_on_expr_only`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“相等性”场景。 | `test_symbol_value_type_equality_depends_on_expr_only` |
| TC-SYM-012 | 符号语义 | 相等性 | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_symbol_value_type_equality_depends_on_expr_only`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“相等性”场景。 | `test_symbol_value_type_equality_depends_on_expr_only` |
| TC-SYM-013 | 解析/打印 | memory 元信息标量 | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_expr_attr_round_trip`、`test_symbol_value_type_round_trip_for_integer_only_semantics`、`test_memory_scalar_components_round_trip_through_symbol_dialect`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_expr_attr_round_trip`、`test_symbol_value_type_round_trip_for_integer_only_semantics`、`test_memory_scalar_components_round_trip_through_symbol_dialect` |
| TC-SYM-014 | 解析/打印 | memory 元信息标量 | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_value_type_round_trip_for_integer_only_semantics`、`test_memory_scalar_components_round_trip_through_symbol_dialect`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_value_type_round_trip_for_integer_only_semantics`、`test_memory_scalar_components_round_trip_through_symbol_dialect` |
| TC-SYM-015 | 符号语义 | `symbol.add/sub/mul/div/floordiv/min` | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_symbol_arith_ops_verify_success`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“`symbol.add/sub/mul/div/floordiv/min`”场景。 | `test_symbol_arith_ops_verify_success` |
| TC-SYM-015A | 边界/异常 | `?` 与 `symbol.iter` 算术结果必须为 unknown | 准备 `!symbol.int<#symbol.expr<?>>` 与 `!symbol.iter<...>` operand。 | 运行 `test_symbol_arith_ops_require_unknown_result_for_unknown_or_iter_operands`。 | 合法 unknown result 通过 verifier，`N + 1`、`2 - f0` 这类 result type 被拒绝。 | `test_symbol_arith_ops_require_unknown_result_for_unknown_or_iter_operands` |
| TC-SYM-016 | 解析/打印 | `symbol.add/sub/mul/div/floordiv/min` | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_arith_ops_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_arith_ops_round_trip` |
| TC-SYM-017 | 边界/异常 | `symbol.add/sub/mul/div/floordiv/min` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_arith_ops_reject_non_symbol_int_types`。 | “`symbol.add/sub/mul/div/floordiv/min`”场景按公开错误语义失败或被拒绝。 | `test_symbol_arith_ops_reject_non_symbol_int_types` |
| TC-SYM-018 | 边界/异常 | `symbol.add/sub/mul/div/floordiv/min` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_arith_ops_reject_malformed_signatures`。 | “`symbol.add/sub/mul/div/floordiv/min`”场景按公开错误语义失败或被拒绝。 | `test_symbol_arith_ops_reject_malformed_signatures` |
| TC-SYM-019 | 边界/异常 | `symbol.add/sub/mul/div/floordiv/min` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_arith_ops_error_messages_include_context`。 | “`symbol.add/sub/mul/div/floordiv/min`”场景按公开错误语义失败或被拒绝。 | `test_symbol_arith_ops_error_messages_include_context` |
| TC-SYM-019A | 解析/打印 | `symbol.min` 类型和值语义 | 准备 `!symbol.int` 或 `!symbol.iter` 操作数。 | 运行 `test_symbol_arith_ops_verify_success` 与 `test_symbol_arith_ops_round_trip`。 | `symbol.min` 可打印解析，结果类型保留 `min(lhs, rhs)` 或等价常量语义。 | `test_symbol_arith_ops_verify_success`、`test_symbol_arith_ops_round_trip` |
| TC-SYM-020 | 符号语义 | `symbol.eq/ne/lt/le/gt/ge` | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_symbol_compare_ops_verify_success`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“`symbol.eq/ne/lt/le/gt/ge`”场景。 | `test_symbol_compare_ops_verify_success` |
| TC-SYM-020A | 符号语义 | compare 静态整数 fold 为 `i1` | 准备静态整数 `symbol.const` operand。 | 运行 `test_symbol_compare_ops_fold_static_operands_to_i1_bool`。 | eq/ne/lt/le/gt/ge 均可在静态整数输入下 fold 为 `arith.constant` i1。 | `test_symbol_compare_ops_fold_static_operands_to_i1_bool` |
| TC-SYM-020B | 边界/异常 | compare 动态、`?` 与 `symbol.iter` 不 fold | 准备动态 symbol、unknown 与 iter operand。 | 运行 `test_symbol_compare_ops_reject_dynamic_unknown_and_iter_fold`。 | compare result 仍为 `i1`，但不发生常量 fold。 | `test_symbol_compare_ops_reject_dynamic_unknown_and_iter_fold` |
| TC-SYM-021 | 解析/打印 | `symbol.eq/ne/lt/le/gt/ge` | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_compare_ops_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_compare_ops_round_trip` |
| TC-SYM-022 | 边界/异常 | `symbol.eq/ne/lt/le/gt/ge` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_compare_ops_reject_non_symbol_int_operands`。 | “`symbol.eq/ne/lt/le/gt/ge`”场景按公开错误语义失败或被拒绝。 | `test_symbol_compare_ops_reject_non_symbol_int_operands` |
| TC-SYM-023 | 边界/异常 | `symbol.eq/ne/lt/le/gt/ge` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_compare_ops_reject_non_i1_result`。 | “`symbol.eq/ne/lt/le/gt/ge`”场景按公开错误语义失败或被拒绝。 | `test_symbol_compare_ops_reject_non_i1_result` |
| TC-SYM-024 | 边界/异常 | `symbol.eq/ne/lt/le/gt/ge` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_compare_ops_reject_malformed_signatures`。 | “`symbol.eq/ne/lt/le/gt/ge`”场景按公开错误语义失败或被拒绝。 | `test_symbol_compare_ops_reject_malformed_signatures` |
| TC-SYM-025 | 边界/异常 | `symbol.eq/ne/lt/le/gt/ge` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_compare_ops_error_messages_include_context`。 | “`symbol.eq/ne/lt/le/gt/ge`”场景按公开错误语义失败或被拒绝。 | `test_symbol_compare_ops_error_messages_include_context` |
| TC-SYM-026 | 内存/DMA | `symbol.get_dim` | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_symbol_get_dim_reads_static_dim_from_memory_type`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`symbol.get_dim`”场景。 | `test_symbol_get_dim_reads_static_dim_from_memory_type` |
| TC-SYM-026A | 符号语义 | `symbol.get_dim` | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_symbol_get_dim_folds_static_dim_to_const_attr`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“`symbol.get_dim`”场景。 | `test_symbol_get_dim_folds_static_dim_to_const_attr` |
| TC-SYM-027 | 内存/DMA | `symbol.get_dim` | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_symbol_get_dim_reads_symbolic_dim_from_memory_type`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`symbol.get_dim`”场景。 | `test_symbol_get_dim_reads_symbolic_dim_from_memory_type` |
| TC-SYM-028 | 内存/DMA | `symbol.get_stride` | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_symbol_get_stride_reads_static_stride_from_memory_type`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`symbol.get_stride`”场景。 | `test_symbol_get_stride_reads_static_stride_from_memory_type` |
| TC-SYM-028A | 内存/DMA | `symbol.get_stride` | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_symbol_get_stride_folds_static_stride_to_const_attr`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`symbol.get_stride`”场景。 | `test_symbol_get_stride_folds_static_stride_to_const_attr` |
| TC-SYM-029 | 内存/DMA | `symbol.get_stride` | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_symbol_get_stride_reads_symbolic_stride_from_memory_type`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`symbol.get_stride`”场景。 | `test_symbol_get_stride_reads_symbolic_stride_from_memory_type` |
| TC-SYM-029A | 内存/DMA | `symbol.get_dim/get_stride` 解析结构化 memory 条目 | 准备 `!nn.memory<[#symbol.expr<...>], [#symbol.expr<...>], ...>` 公开 IR。 | 运行 `test_symbol_memory_query_parses_symbol_expr_entries_from_public_ir`。 | `symbol.get_dim` 与 `symbol.get_stride` 可从结构化 shape/stride 条目推导 `!symbol.int<#symbol.expr<...>>` 结果类型。 | `test_symbol_memory_query_parses_symbol_expr_entries_from_public_ir` |
| TC-SYM-030 | 边界/异常 | `symbol.get_dim/get_stride` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_get_dim_rejects_invalid_axis`、`test_symbol_get_stride_rejects_invalid_axis`。 | “`symbol.get_dim/get_stride`”场景按公开错误语义失败或被拒绝。 | `test_symbol_get_dim_rejects_invalid_axis`、`test_symbol_get_stride_rejects_invalid_axis` |
| TC-SYM-031 | 边界/异常 | `symbol.get_dim/get_stride` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_get_dim_rejects_non_memory_type`、`test_symbol_get_stride_rejects_unknown_entry`。 | “`symbol.get_dim/get_stride`”场景按公开错误语义失败或被拒绝。 | `test_symbol_get_dim_rejects_non_memory_type`、`test_symbol_get_stride_rejects_unknown_entry` |
| TC-SYM-032 | 符号语义 | `symbol.for` | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_symbol_for_accepts_symbol_int_bounds_and_iter_arg`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“`symbol.for`”场景。 | `test_symbol_for_accepts_symbol_int_bounds_and_iter_arg` |
| TC-SYM-033 | 解析/打印 | `symbol.for` | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_for_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_for_round_trip` |
| TC-SYM-034 | 边界/异常 | `symbol.for` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_for_rejects_non_symbol_int_operands`。 | “`symbol.for`”场景按公开错误语义失败或被拒绝。 | `test_symbol_for_rejects_non_symbol_int_operands` |
| TC-SYM-035 | 边界/异常 | `symbol.for` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_for_rejects_zero_step`。 | “`symbol.for`”场景按公开错误语义失败或被拒绝。 | `test_symbol_for_rejects_zero_step` |
| TC-SYM-036 | 边界/异常 | `symbol.for` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_for_rejects_invalid_region_shape`。 | “`symbol.for`”场景按公开错误语义失败或被拒绝。 | `test_symbol_for_rejects_invalid_region_shape` |
| TC-SYM-037 | 边界/异常 | `symbol.for` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_for_parse_rejects_malformed_text`。 | “`symbol.for`”场景按公开错误语义失败或被拒绝。 | `test_symbol_for_parse_rejects_malformed_text` |
| TC-SYM-038 | 边界/异常 | `symbol.for` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_for_error_messages_include_context`。 | “`symbol.for`”场景按公开错误语义失败或被拒绝。 | `test_symbol_for_error_messages_include_context` |
| TC-SYM-038A | 解析/打印 | `symbol.for` | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_for_loop_carried_symbol_int_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_for_loop_carried_symbol_int_round_trip` |
| TC-SYM-038B | 边界/异常 | `symbol.for` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_for_rejects_invalid_loop_carried_symbol_int`。 | “`symbol.for`”场景按公开错误语义失败或被拒绝。 | `test_symbol_for_rejects_invalid_loop_carried_symbol_int` |
| TC-SYM-039 | 符号语义 | `symbol.to_float` | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_symbol_to_float_verify_success`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“`symbol.to_float`”场景。 | `test_symbol_to_float_verify_success` |
| TC-SYM-040 | 解析/打印 | `symbol.to_float` | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_to_float_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_to_float_round_trip` |
| TC-SYM-041 | 边界/异常 | `symbol.to_float` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_to_float_rejects_invalid_types`。 | “`symbol.to_float`”场景按公开错误语义失败或被拒绝。 | `test_symbol_to_float_rejects_invalid_types` |
| TC-SYM-042 | 符号语义 | `symbol.to_int` | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_symbol_to_int_verify_success_for_integer_variants`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“`symbol.to_int`”场景。 | `test_symbol_to_int_verify_success_for_integer_variants` |
| TC-SYM-043 | 解析/打印 | `symbol.to_int` | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_to_int_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_to_int_round_trip` |
| TC-SYM-044 | 边界/异常 | `symbol.to_int` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_to_int_rejects_invalid_types`。 | “`symbol.to_int`”场景按公开错误语义失败或被拒绝。 | `test_symbol_to_int_rejects_invalid_types` |
| TC-SYM-045 | 符号语义 | `SymbolPtrType` | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_symbol_ptr_type_verify_success`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“`SymbolPtrType`”场景。 | `test_symbol_ptr_type_verify_success` |
| TC-SYM-046 | 解析/打印 | `SymbolPtrType` | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_ptr_type_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_ptr_type_round_trip` |
| TC-SYM-047 | 边界/异常 | `SymbolPtrType` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_ptr_type_rejects_symbol_value_dtype`。 | “`SymbolPtrType`”场景按公开错误语义失败或被拒绝。 | `test_symbol_ptr_type_rejects_symbol_value_dtype` |
| TC-SYM-048 | 边界/异常 | `SymbolPtrType` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_ptr_type_rejects_non_type_dtype`。 | “`SymbolPtrType`”场景按公开错误语义失败或被拒绝。 | `test_symbol_ptr_type_rejects_non_type_dtype` |
| TC-SYM-049 | 符号语义 | `symbol.const` | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_symbol_const_op_verify_success`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“`symbol.const`”场景。 | `test_symbol_const_op_verify_success` |
| TC-SYM-050 | 解析/打印 | `symbol.const` | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_const_op_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_const_op_round_trip` |
| TC-SYM-051 | 边界/异常 | `symbol.const` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_const_op_rejects_mismatched_type`。 | “`symbol.const`”场景按公开错误语义失败或被拒绝。 | `test_symbol_const_op_rejects_mismatched_type` |
| TC-SYM-051A | 边界/异常 | `SymbolConstOp` 拒绝 `IntegerAttr` 输入 | 准备 `IntegerAttr(3, i32)`。 | 运行 `test_symbol_const_op_rejects_integer_attr_input`。 | `SymbolConstOp(...)` 公开构造只接受 `int | IntAttr`，`IntegerAttr` 被稳定拒绝。 | `test_symbol_const_op_rejects_integer_attr_input` |
| TC-SYM-051B | 边界/异常 | `SymbolConstOp` 拒绝 bool 输入 | 准备 `True`、`False`、`IntAttr(data=True)` 与 `IntAttr(data=False)`。 | 运行 `test_symbol_const_op_rejects_boolean_inputs`。 | `SymbolConstOp(...)` 公开构造拒绝 bool 与 bool-backed `IntAttr`，不把布尔值误当作 `!symbol.int<#symbol.expr<1>>` 或 `!symbol.int<#symbol.expr<0>>`。 | `test_symbol_const_op_rejects_boolean_inputs` |
| TC-SYM-058 | 符号语义 | `SymbolValueType.get_value()/is_symbol()` 对常量、负数、`floordiv`、`ceildiv` 与 `mod` 的公开值语义 | 准备公开 `!symbol.int<#symbol.expr<...>>` 文本与构造入口。 | 运行 `test_symbol_value_type_public_expression_matrix`。 | 常量表达归一为整数，符号表达返回 canonical 文本，`is_symbol()` 与公开值语义一致。 | `test_symbol_value_type_public_expression_matrix` |
| TC-SYM-059 | 解析/打印 | `SymbolDimType` 与 `SymbolIterType` 公开构造、字符串化和 legacy iter parser | 准备公开 symbol dim 名称、iter bounds 与 legacy iter 文本。 | 运行 `test_symbol_dim_and_iter_public_constructor_matrix`。 | 合法名称与 iter 文本稳定，空名称、非法名称和 malformed iter 文本按公开错误语义失败。 | `test_symbol_dim_and_iter_public_constructor_matrix` |
| TC-SYM-060 | 边界/异常 | `symbol.add/div/floordiv` 公开 folding 拒绝除零、非整除与 result type 不匹配 | 准备公开 `Folder.try_fold(...)` 入口和 `symbol.const` 操作数。 | 运行 `test_symbol_binary_arith_fold_public_rejection_matrix`。 | 除零、非整除和 result type 不匹配均不发生错误折叠。 | `test_symbol_binary_arith_fold_public_rejection_matrix` |
| TC-SYM-061 | 边界/异常 | `SymbolValueType.is_symbol()` 对除零和 raw division 的公开边界 | 准备公开 `!symbol.int<#symbol.expr<7 floordiv 0>>`、`#symbol.expr<N / 2>` 与 `#symbol.expr<N // 2>` 文本。 | 运行 `test_symbol_value_type_public_non_concrete_division_edges`、`test_symbol_expr_attr_rejects_raw_division_tokens`。 | 除零和 raw `/` / `//` 均被拒绝，不被误归一为符号表达。 | `test_symbol_value_type_public_non_concrete_division_edges`、`test_symbol_expr_attr_rejects_raw_division_tokens` |
| TC-SYM-062 | 边界/异常 | `symbol.get_dim/get_stride` 公开 folding 拒绝非 memory、非静态轴号、越界轴号与匿名动态条目 | 准备公开 memory SSA value、非 memory value、`?` shape/stride 与非法 axis。 | 运行 `test_symbol_memory_query_fold_public_rejection_matrix`。 | 非可折叠输入均返回 `None`，不产生错误常量折叠。 | `test_symbol_memory_query_fold_public_rejection_matrix` |
| TC-SYM-063 | 边界/异常 | `symbol.yield` 父 op 与 loop-carried 约束 | 准备独立 `symbol.yield` 与无 carried-value 的 `symbol.for` 循环体。 | 运行 `test_symbol_yield_public_parent_and_carried_edges`。 | `symbol.yield` 不在 `symbol.for` 内或缺 loop-carried 上下文时按公开错误语义失败。 | `test_symbol_yield_public_parent_and_carried_edges` |
| TC-SYM-064 | 边界/异常 | `symbol.for` iter attribute、block argument 与 loop-carried block 形状一致性 | 准备 start/end/step 不匹配、iter block type 不匹配和 carried block arg 数错误的公开构造。 | 运行 `test_symbol_for_rejects_iter_attr_mismatch_matrix`。 | 每类不一致输入均由 verifier 给出稳定公开错误。 | `test_symbol_for_rejects_iter_attr_mismatch_matrix` |
| TC-SYM-065 | 解析/打印 | `symbol.for` 对结构不完整 body 的打印回退 | 准备公开 `SymbolForOp` 构造但 body block 参数不完整。 | 运行 `test_symbol_for_prints_default_format_for_invalid_body_shape`。 | printer 不误用自定义文本，回退到稳定 default format。 | `test_symbol_for_prints_default_format_for_invalid_body_shape` |
