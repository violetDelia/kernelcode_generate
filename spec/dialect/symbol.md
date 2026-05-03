# symbol.md

## 功能简介

定义 `symbol dialect` 的类型与基础构件，用于在 IR 中显式表示“带符号值语义的整型标量”以及“最小 pointer type 承载”。同时提供 `!symbol.iter<start = "...", end = "...", step = "...">` 用于表达循环迭代变量语义，与 `!symbol.int<"expr">` 同样承载整数值语义，但额外记录迭代边界。该方言的核心目标是让类型本身携带一个符号表达，例如 `!symbol.int<"N">` 表示“这是一个整数值，其值语义为符号 `N`”。本方言同时作为 memory 相关符号标量语义的唯一归属：`shape`、`stride`、`offset`、`size`、循环边界等位置只要进入 IR 并需要表达单个整数符号值，就统一落到 `symbol dialect`。在此基础上，本方言允许最小范围的整数符号算术与比较 op，用于在 IR 中显式表达 `symbol.int` 标量之间的加、减、乘、除、整除以及比较计算，并提供 `symbol.to_int`（转为普通整型）与 `symbol.to_float`（转为 `f32`）两类显式类型转换 op；同时提供 `!symbol.ptr<dtype>` 作为 DSL `Ptr(dtype)` 在 IR 类型层的唯一最小载体。`symbol.for` 现支持旧的无 carried-value 形式，也支持单个 loop-carried `!symbol.int<"...">` 的 `iter_args(%acc = %init) ... -> !symbol.int<"...">` 公开语法，并通过 `symbol.yield` 终止循环体。该方言不负责张量、内存容器、通用控制流、pointer body op，或超出最小整数符号算术/比较范围的数值计算语义。

## API 列表

- `class SymbolExprAttr(expr: StringAttr)`
- `class SymbolDimType(expr: SymbolExprAttr)`
- `class SymbolValueType(expr: SymbolExprAttr)`
- `class SymbolIterAttr(start: StringAttr, end: StringAttr, step: StringAttr)`
- `class SymbolIterType(iter_attr: SymbolIterAttr)`
- `class SymbolPtrType(base_type: Attribute, shape: ArrayAttr[Attribute], stride: ArrayAttr[Attribute])`
- `class SymbolConstOp(value: IntegerAttr | IntAttr | int)`
- `class SymbolAddOp(lhs: SSAValue, rhs: SSAValue)`
- `class SymbolSubOp(lhs: SSAValue, rhs: SSAValue)`
- `class SymbolMulOp(lhs: SSAValue, rhs: SSAValue)`
- `class SymbolDivOp(lhs: SSAValue, rhs: SSAValue)`
- `class SymbolFloorDivOp(lhs: SSAValue, rhs: SSAValue)`
- `class SymbolEqOp(lhs: SSAValue, rhs: SSAValue)`
- `class SymbolNeOp(lhs: SSAValue, rhs: SSAValue)`
- `class SymbolLtOp(lhs: SSAValue, rhs: SSAValue)`
- `class SymbolLeOp(lhs: SSAValue, rhs: SSAValue)`
- `class SymbolGtOp(lhs: SSAValue, rhs: SSAValue)`
- `class SymbolGeOp(lhs: SSAValue, rhs: SSAValue)`
- `class SymbolToFloatOp(value: SSAValue, result_type: Attribute)`
- `class SymbolToIntOp(value: SSAValue, result_type: Attribute)`
- `class SymbolCastOp(value: SSAValue, result_type: Attribute)`
- `class SymbolGetDimOp(memory: SSAValue, index: int | IntAttr)`
- `class SymbolGetStrideOp(memory: SSAValue, index: int | IntAttr)`
- `class SymbolYieldOp(value: SSAValue | None = None)`
- `class SymbolForOp(iter_attr: SymbolIterAttr, start: SSAValue, end: SSAValue, step: SSAValue, body: Region, init: SSAValue | None = None)`
- `class Symbol(Dialect)`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
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
- 提供最小整数符号算术与比较接口，使 `!symbol.int<"expr">` 标量可在方言内完成基础加、减、乘、除、整除组合与相等/大小关系判断，而无需回退到其他算术方言。
- 明确 `symbol.gt` / `symbol.le` / `symbol.lt` / `symbol.ne` 与 `symbol.to_float` 的 dialect 合同，使上游 `a > b`、`a <= b`、`a < b`、`a != b` 与 `float(n)` 在进入 `symbol dialect` 后拥有稳定目标 op。
- 提供 `!symbol.ptr<dtype>` 作为 DSL `Ptr(dtype)` 的最小 IR pointer type 载体，使函数签名 lowering 可以稳定表达“指向某个 pointee dtype 的指针输入”。
- 提供 `SymbolIterType`，用于表达循环迭代变量语义，并支持 `!symbol.iter<start = "...", end = "...", step = "...">` 文本形式。
- 提供 `symbol.yield` 与带单个 carried `!symbol.int<"...">` 的 `symbol.for`，用于表达循环体终止与最小归约语义。
- 保持类型表达尽量简单，优先服务开发者理解和方言间协同，而不是追求复杂的符号推导系统。
- 本文件中的“符号值”指与 SSA value 绑定的单个整数值语义表达，可以是具名符号、整型表达式或整型常量，如 `N`、`M + 1`、`B * K`、`1`、`2`、`3`。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- `symbol dialect` 只定义符号值类型、最小整数符号算术 op、基础约束、`symbol.for` 的最小循环结构以及从 memory type 读取单个 dim/stride 值的查询接口；不定义张量类型、内存类型、通用控制流 op、通用内存搬运 op 或逐元素张量算术 op。
- 本方言的重点是“值的符号语义如何表达”，不是“如何求值”或“如何解方程”。
- 本方言不负责通用符号化简、约束求解、范围分析、证明或 SMT 集成。
- 符号表达式只要求可稳定打印、可比较、可校验；不要求在 dialect 内部完成复杂等价变换。
- 普通整数类型与符号值类型是不同概念：`int` 与 `!symbol.int<"N">` 不是同一类型。
- `!symbol.int<"1">`、`!symbol.int<"2">`、`!symbol.int<"3">` 这类常量整数值类型是合法的，表示“值语义已知为该整数常量”。
- `!symbol.int<"N">` 中字符串里的表达式表示“值语义”，不是附加注释，也不是 shape 维度列表。
- 类型中的符号表达应面向单个标量值；shape 列表、stride 列表等多值结构不直接放入本方言标量类型中。
- `Memory`、`MemorySpace`、`LocalSpaceMeta` 这类高层内存容器或空间枚举不属于本方言；本方言只负责它们内部可能出现的单个整型符号值语义。
- `symbol.get_dim` / `symbol.get_stride` 只读取 memory type 中已存在的单个维度或步幅分量，不引入新的 shape/stride 推导规则。
- `symbol.get_dim` / `symbol.get_stride` 当前只接受 IR 层 memory SSA value；按当前方言体系，该 memory type 统一指向 `MemoryType`，其当前文本载体仍为 `!nn.memory<...>`。
- `symbol.get_dim` / `symbol.get_stride` 查询到静态整数 shape/stride 条目时支持常量折叠，可在通用 folding 中物化为 `symbol.const`；符号表达与匿名动态值不得被折叠成常量。
- 若目标维度或步幅条目为匿名动态值 `?`，由于无法稳定映射为 `!symbol.int<"...">`，必须报错；本接口只接受可表示为整数常量或符号表达的条目。
- `symbol.get_dim` / `symbol.get_stride` 的轴号当前必须是静态整数索引；越界、负数或非整数轴号必须报错。
- 本方言暂不定义“未知但无名字”的匿名符号值；若需要动态未知值，应优先使用具名符号或由其他方言以 SSA value 传递。
- 当前只定义整数语义，不区分 `int/int8/int16/int32/int64` 等具体整型宽度，也不定义 `index`、浮点或其他非整型 symbol 类型。
- `SymbolIterType` 只用于表达循环迭代变量语义；`symbol.for` 的 `start/end/step` 仍要求 `!symbol.int<"expr">`，`it` 则要求 `!symbol.iter<...>`。
- `symbol.for` 支持的循环承载值仅限一个 `!symbol.int<"...">` 累计值；该能力服务于成本函数一类“循环内累计、循环外返回”的 IR 表达，不扩展为通用多值控制流。
- `symbol.ptr` 只定义 `!symbol.ptr<dtype>` 这一类最小 pointer type；它只承载 pointee dtype，不承载名字、地址值、shape、stride、offset 或 memory space。
- `!symbol.ptr<dtype>` 中的 `dtype` 必须是合法 `TypeAttribute`，且不得为 `!symbol.int<"...">`；当前不定义 `!symbol.ptr<!symbol.int<"...">>` 这类“指向 symbol.int”的 pointer carrier。
- 当前最小算术/比较范围仅包含 `symbol.add`、`symbol.sub`、`symbol.mul`、`symbol.div`、`symbol.floordiv`、`symbol.eq`、`symbol.ne`、`symbol.lt`、`symbol.le`、`symbol.gt`、`symbol.ge`；不定义取模、按位运算、布尔逻辑组合、广播或张量级算术。
- 当前仅定义 `symbol.to_int` 与 `symbol.to_float` 两类转换：`symbol.to_int` 将 `!symbol.int<"...">` 转为普通整型（覆盖各整型变体），`symbol.to_float` 将 `!symbol.int<"...">` 转为 `f32`；不定义反向转换或其他跨类型规则。
- `symbol.ne` / `symbol.lt` / `symbol.le` / `symbol.gt` 属于同一 compare family：统一采用二元 `!symbol.int<"...">, !symbol.int<"..."> -> i1` 签名、统一 verifier 约束与统一 parse/print 规则，不能拆成互不一致的四套合同。
- 当前不在 `symbol dialect` 中定义 `ptr.load`、`ptr.store`、pointer arithmetic、pointer compare、address cast 或任何基于 `symbol.ptr` 的 body-level 计算 op。
- `symbol.const` 只用于生成整数常量的 `!symbol.int<"...">`，不承载其他类型或宽度。

### 文本语法

- 功能说明：

- 规定 `symbol dialect` 在文档、打印和调试中的正式文本语法。

- 参数：

- `expr`：符号表达。
- `dtype`：pointer pointee dtype。

- 使用示例：

```text
#symbol.expr<"N">
#symbol.expr<"M + 1">
!symbol.int<"N">
!symbol.int<"3">
!symbol.iter<start = "0", end = "index", step = "1">
!symbol.ptr<f32>
!symbol.ptr<i32>
```

- 注意事项：

- `SymbolExprAttr` 使用 `#symbol.expr<"expr">`。
- `SymbolValueType` 使用 `!symbol.int<"expr">`。
- `SymbolIterType` 使用 `!symbol.iter<start = "...", end = "...", step = "...">`。
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
- `expr` 中若出现非法字符、空白后为空、或不可解析的表达式，必须报错。
- `expr` 允许纯整数字面量，`!symbol.int<"1">`、`!symbol.int<"2">`、`!symbol.int<"3">` 都必须视为合法类型表达。
- `SymbolIterType` 的表达式规则与 `SymbolValueType` 一致，打印后再解析必须得到等价类型对象。
- 兼容解析旧文本 `!symbol.iter<"expr">`，解析后应等价于 `!symbol.iter<start = "0", end = "expr", step = "1">`。
- 同一个 `SymbolValueType` 的相等性比较只比较整数语义下的 `expr`。
- 打印后再解析必须能得到等价类型对象。
- `!symbol.int<"N">` 表示“该 SSA value 的整数值由符号 `N` 表示”，不是变量声明；`!symbol.int<"1">`、`!symbol.int<"2">`、`!symbol.int<"3">` 表示该值已知为对应常量整数。
- `SymbolPtrType` 的 `dtype` 必须为 `TypeAttribute`；若不是类型 attribute，必须报错。
- `SymbolPtrType` 的 `dtype` 不得为 `SymbolValueType`；`!symbol.ptr<!symbol.int<"N">>` 必须视为非法。
- `!symbol.ptr<dtype>` 打印后再解析必须能得到等价类型对象。

- 返回值：

- 返回类型：校验规则定义。
- 限制：仅校验整数符号类型表达与 pointer carrier 的合法性，不负责判断两个不同表达式是否数学等价，也不定义 pointer body 语义。

### Memory 相关符号标量归属

- 功能说明：

- 规定 memory 相关符号值在 IR 层的归属边界。
- 当 `shape`、`stride`、`offset`、`size` 等 memory 元信息被单独建模为整数标量 attribute/type 时，统一由 `symbol dialect` 负责其整数符号语义表达。

- 参数：

- `expr(string)`：单个 memory 元信息标量对应的整数语义表达，例如 `N`、`K*N`、`3`。

- 使用示例：

```text
#symbol.expr<"K*N">
!symbol.int<"3">
!symbol.int<"N">
```

- 注意事项：

- 本归属规则只覆盖“单个整数标量”的 symbol 语义，不直接承载 `shape=[M, N]` 这类多值结构。
- `spec/symbol_variable/memory.md` 负责高层 `Memory` 对象、空间枚举与默认 stride 规则；`symbol dialect` 负责其中单个维度或步幅分量的整数 symbol 语义。
- 常量整数分量与具名符号分量同样适用本规则；`!symbol.int<"1">`、`!symbol.int<"2">`、`!symbol.int<"3">` 都是合法 memory 元信息标量表达。

- 返回值：

- 返回类型：归属规则定义。
- 限制：只定义 memory 元信息中的单值整型 symbol 语义，不定义 memory 容器、memory type 或 memory space。

### `symbol.const`

- 功能说明：

- 定义整数常量进入 `symbol dialect` 的最小 op。
- 以整数 attribute 记录常量值，并输出对应的 `!symbol.int<"...">` 结果类型。

- 参数：

- `value(integer)`：整数常量。
- `result_type(type)`：结果类型，必须为 `!symbol.int<"...">`。

- 使用示例：

```text
%one = symbol.const 1 : !symbol.int<"1">
%neg = symbol.const -4 : !symbol.int<"-4">
```

- 注意事项：

- `value` 必须是整数 attribute；不接受布尔值或浮点值。
- 结果类型必须为 `!symbol.int<"...">`，且表达式内容必须与常量值一致。
- parse/print 必须稳定遵循 `symbol.const <value> : !symbol.int<"...">` 的公开文本形式。

- 返回值：

- 返回类型：`!symbol.int<"value">`
- 限制：仅用于生成整数常量，不承载其他类型或宽度。

## API详细说明

### `class SymbolExprAttr(expr: StringAttr)`

- api：`class SymbolExprAttr(expr: StringAttr)`
- 参数：
  - `expr`：符号表达式文本；类型 `StringAttr`；无默认值；不允许 None 或空字符串；必须可稳定打印和解析。
- 返回值：`SymbolExprAttr` 实例。
- 使用示例：

  ```python
    from kernel_gen.dialect.symbol import SymbolExprAttr

    value = SymbolExprAttr(expr=expr)
    ```
- 功能说明：构造或表示 `SymbolExprAttr` 对应的 symbol dialect attribute。
- 注意事项：只允许使用本 API 列表中的公开入口；测试不得直连当前文件之外的非公开 helper。

### `class SymbolDimType(expr: SymbolExprAttr)`

- api：`class SymbolDimType(expr: SymbolExprAttr)`
- 参数：
  - `expr`：符号表达式文本；类型 `SymbolExprAttr`；无默认值；不允许 None 或空字符串；必须可稳定打印和解析。
- 返回值：`SymbolDimType` 实例。
- 使用示例：

  ```python
    from kernel_gen.dialect.symbol import SymbolDimType

    value = SymbolDimType(expr=expr)
    ```
- 功能说明：构造或表示 `SymbolDimType` 对应的 symbol dialect type。
- 注意事项：只允许使用本 API 列表中的公开入口；测试不得直连当前文件之外的非公开 helper。

### `class SymbolValueType(expr: SymbolExprAttr)`

- api：`class SymbolValueType(expr: SymbolExprAttr)`
- 参数：
  - `expr`：符号表达式文本；类型 `SymbolExprAttr`；无默认值；不允许 None 或空字符串；必须可稳定打印和解析。
- 返回值：`SymbolValueType` 实例。
- 使用示例：

  ```python
    from kernel_gen.dialect.symbol import SymbolValueType

    value = SymbolValueType(expr=expr)
    ```
- 功能说明：构造或表示 `SymbolValueType` 对应的 symbol dialect type。
- 注意事项：只允许使用本 API 列表中的公开入口；测试不得直连当前文件之外的非公开 helper。

### `class SymbolIterAttr(start: StringAttr, end: StringAttr, step: StringAttr)`

- api：`class SymbolIterAttr(start: StringAttr, end: StringAttr, step: StringAttr)`
- 参数：
  - `start`：循环起始符号表达式；类型 `StringAttr`；无默认值；不允许 None。
  - `end`：循环结束符号表达式；类型 `StringAttr`；无默认值；不允许 None。
  - `step`：循环步长符号表达式；类型 `StringAttr`；无默认值；不允许 None。
- 返回值：`SymbolIterAttr` 实例。
- 使用示例：

  ```python
    from kernel_gen.dialect.symbol import SymbolIterAttr

    value = SymbolIterAttr(start=start, end=end, step=step)
    ```
- 功能说明：构造或表示 `SymbolIterAttr` 对应的 symbol dialect attribute。
- 注意事项：只允许使用本 API 列表中的公开入口；测试不得直连当前文件之外的非公开 helper。

### `class SymbolIterType(iter_attr: SymbolIterAttr)`

- api：`class SymbolIterType(iter_attr: SymbolIterAttr)`
- 参数：
  - `iter_attr`：循环迭代属性；类型 `SymbolIterAttr`；无默认值；不允许 None；承载 start/end/step 文本。
- 返回值：`SymbolIterType` 实例。
- 使用示例：

  ```python
    from kernel_gen.dialect.symbol import SymbolIterType

    value = SymbolIterType(iter_attr=iter_attr)
    ```
- 功能说明：构造或表示 `SymbolIterType` 对应的 symbol dialect type。
- 注意事项：只允许使用本 API 列表中的公开入口；测试不得直连当前文件之外的非公开 helper。

### `class SymbolPtrType(base_type: Attribute, shape: ArrayAttr[Attribute], stride: ArrayAttr[Attribute])`

- api：`class SymbolPtrType(base_type: Attribute, shape: ArrayAttr[Attribute], stride: ArrayAttr[Attribute])`
- 参数：
  - `base_type`：指针承载的基础类型；类型 `Attribute`；无默认值；不允许 None；必须是公开 xDSL Attribute。
  - `shape`：形状序列；类型 `ArrayAttr[Attribute]`；无默认值；不允许 None；每个维度必须满足符号维度公开合同。
  - `stride`：步幅序列；类型 `ArrayAttr[Attribute]`；无默认值；传入时长度必须与 shape 语义匹配。
- 返回值：`SymbolPtrType` 实例。
- 使用示例：

  ```python
    from kernel_gen.dialect.symbol import SymbolPtrType

    value = SymbolPtrType(base_type=base_type, shape=shape, stride=stride)
    ```
- 功能说明：构造或表示 `SymbolPtrType` 对应的 symbol dialect type。
- 注意事项：`base_type` 必须是合法 xDSL type attribute；不得把 `!symbol.int` 用作 pointer pointee。

### `class SymbolConstOp(value: IntegerAttr | IntAttr | int)`

- api：`class SymbolConstOp(value: IntegerAttr | IntAttr | int)`
- 参数：
  - `value`：输入值；类型 `IntegerAttr | IntAttr | int`；无默认值；不允许 None，除非签名显式允许；用于当前节点、op 或转换的主输入。
- 返回值：`SymbolConstOp` 实例。
- 使用示例：

  ```python
    from kernel_gen.dialect.symbol import SymbolConstOp

    value = SymbolConstOp(value=value)
    ```
- 功能说明：构造或表示 `SymbolConstOp` 对应的 symbol dialect operation。
- 注意事项：只允许使用本 API 列表中的公开入口；测试不得直连当前文件之外的非公开 helper。

### `class SymbolAddOp(lhs: SSAValue, rhs: SSAValue)`

- api：`class SymbolAddOp(lhs: SSAValue, rhs: SSAValue)`
- 参数：
  - `lhs`：左操作数；类型 `SSAValue`；无默认值；不允许 None；必须与右操作数满足同一 API 的类型约束。
  - `rhs`：右操作数；类型 `SSAValue`；无默认值；不允许 None；必须与左操作数满足同一 API 的类型约束。
- 返回值：`SymbolAddOp` 实例。
- 使用示例：

  ```python
    from kernel_gen.dialect.symbol import SymbolAddOp

    value = SymbolAddOp(lhs=lhs, rhs=rhs)
    ```
- 功能说明：构造或表示 `SymbolAddOp` 对应的 symbol dialect operation。
- 注意事项：只允许使用本 API 列表中的公开入口；测试不得直连当前文件之外的非公开 helper。

### `class SymbolSubOp(lhs: SSAValue, rhs: SSAValue)`

- api：`class SymbolSubOp(lhs: SSAValue, rhs: SSAValue)`
- 参数：
  - `lhs`：左操作数；类型 `SSAValue`；无默认值；不允许 None；必须与右操作数满足同一 API 的类型约束。
  - `rhs`：右操作数；类型 `SSAValue`；无默认值；不允许 None；必须与左操作数满足同一 API 的类型约束。
- 返回值：`SymbolSubOp` 实例。
- 使用示例：

  ```python
    from kernel_gen.dialect.symbol import SymbolSubOp

    value = SymbolSubOp(lhs=lhs, rhs=rhs)
    ```
- 功能说明：构造或表示 `SymbolSubOp` 对应的 symbol dialect operation。
- 注意事项：只允许使用本 API 列表中的公开入口；测试不得直连当前文件之外的非公开 helper。

### `class SymbolMulOp(lhs: SSAValue, rhs: SSAValue)`

- api：`class SymbolMulOp(lhs: SSAValue, rhs: SSAValue)`
- 参数：
  - `lhs`：左操作数；类型 `SSAValue`；无默认值；不允许 None；必须与右操作数满足同一 API 的类型约束。
  - `rhs`：右操作数；类型 `SSAValue`；无默认值；不允许 None；必须与左操作数满足同一 API 的类型约束。
- 返回值：`SymbolMulOp` 实例。
- 使用示例：

  ```python
    from kernel_gen.dialect.symbol import SymbolMulOp

    value = SymbolMulOp(lhs=lhs, rhs=rhs)
    ```
- 功能说明：构造或表示 `SymbolMulOp` 对应的 symbol dialect operation。
- 注意事项：只允许使用本 API 列表中的公开入口；测试不得直连当前文件之外的非公开 helper。

### `class SymbolDivOp(lhs: SSAValue, rhs: SSAValue)`

- api：`class SymbolDivOp(lhs: SSAValue, rhs: SSAValue)`
- 参数：
  - `lhs`：左操作数；类型 `SSAValue`；无默认值；不允许 None；必须与右操作数满足同一 API 的类型约束。
  - `rhs`：右操作数；类型 `SSAValue`；无默认值；不允许 None；必须与左操作数满足同一 API 的类型约束。
- 返回值：`SymbolDivOp` 实例。
- 使用示例：

  ```python
    from kernel_gen.dialect.symbol import SymbolDivOp

    value = SymbolDivOp(lhs=lhs, rhs=rhs)
    ```
- 功能说明：构造或表示 `SymbolDivOp` 对应的 symbol dialect operation。
- 注意事项：只允许使用本 API 列表中的公开入口；测试不得直连当前文件之外的非公开 helper。

### `class SymbolFloorDivOp(lhs: SSAValue, rhs: SSAValue)`

- api：`class SymbolFloorDivOp(lhs: SSAValue, rhs: SSAValue)`
- 参数：
  - `lhs`：左操作数；类型 `SSAValue`；无默认值；不允许 None；必须与右操作数满足同一 API 的类型约束。
  - `rhs`：右操作数；类型 `SSAValue`；无默认值；不允许 None；必须与左操作数满足同一 API 的类型约束。
- 返回值：`SymbolFloorDivOp` 实例。
- 使用示例：

  ```python
    from kernel_gen.dialect.symbol import SymbolFloorDivOp

    value = SymbolFloorDivOp(lhs=lhs, rhs=rhs)
    ```
- 功能说明：构造或表示 `SymbolFloorDivOp` 对应的 symbol dialect operation。
- 注意事项：只允许使用本 API 列表中的公开入口；测试不得直连当前文件之外的非公开 helper。

### `class SymbolEqOp(lhs: SSAValue, rhs: SSAValue)`

- api：`class SymbolEqOp(lhs: SSAValue, rhs: SSAValue)`
- 参数：
  - `lhs`：左操作数；类型 `SSAValue`；无默认值；不允许 None；必须与右操作数满足同一 API 的类型约束。
  - `rhs`：右操作数；类型 `SSAValue`；无默认值；不允许 None；必须与左操作数满足同一 API 的类型约束。
- 返回值：`SymbolEqOp` 实例。
- 使用示例：

  ```python
    from kernel_gen.dialect.symbol import SymbolEqOp

    value = SymbolEqOp(lhs=lhs, rhs=rhs)
    ```
- 功能说明：构造或表示 `SymbolEqOp` 对应的 symbol dialect operation。
- 注意事项：只允许使用本 API 列表中的公开入口；测试不得直连当前文件之外的非公开 helper。

### `class SymbolNeOp(lhs: SSAValue, rhs: SSAValue)`

- api：`class SymbolNeOp(lhs: SSAValue, rhs: SSAValue)`
- 参数：
  - `lhs`：左操作数；类型 `SSAValue`；无默认值；不允许 None；必须与右操作数满足同一 API 的类型约束。
  - `rhs`：右操作数；类型 `SSAValue`；无默认值；不允许 None；必须与左操作数满足同一 API 的类型约束。
- 返回值：`SymbolNeOp` 实例。
- 使用示例：

  ```python
    from kernel_gen.dialect.symbol import SymbolNeOp

    value = SymbolNeOp(lhs=lhs, rhs=rhs)
    ```
- 功能说明：构造或表示 `SymbolNeOp` 对应的 symbol dialect operation。
- 注意事项：只允许使用本 API 列表中的公开入口；测试不得直连当前文件之外的非公开 helper。

### `class SymbolLtOp(lhs: SSAValue, rhs: SSAValue)`

- api：`class SymbolLtOp(lhs: SSAValue, rhs: SSAValue)`
- 参数：
  - `lhs`：左操作数；类型 `SSAValue`；无默认值；不允许 None；必须与右操作数满足同一 API 的类型约束。
  - `rhs`：右操作数；类型 `SSAValue`；无默认值；不允许 None；必须与左操作数满足同一 API 的类型约束。
- 返回值：`SymbolLtOp` 实例。
- 使用示例：

  ```python
    from kernel_gen.dialect.symbol import SymbolLtOp

    value = SymbolLtOp(lhs=lhs, rhs=rhs)
    ```
- 功能说明：构造或表示 `SymbolLtOp` 对应的 symbol dialect operation。
- 注意事项：只允许使用本 API 列表中的公开入口；测试不得直连当前文件之外的非公开 helper。

### `class SymbolLeOp(lhs: SSAValue, rhs: SSAValue)`

- api：`class SymbolLeOp(lhs: SSAValue, rhs: SSAValue)`
- 参数：
  - `lhs`：左操作数；类型 `SSAValue`；无默认值；不允许 None；必须与右操作数满足同一 API 的类型约束。
  - `rhs`：右操作数；类型 `SSAValue`；无默认值；不允许 None；必须与左操作数满足同一 API 的类型约束。
- 返回值：`SymbolLeOp` 实例。
- 使用示例：

  ```python
    from kernel_gen.dialect.symbol import SymbolLeOp

    value = SymbolLeOp(lhs=lhs, rhs=rhs)
    ```
- 功能说明：构造或表示 `SymbolLeOp` 对应的 symbol dialect operation。
- 注意事项：只允许使用本 API 列表中的公开入口；测试不得直连当前文件之外的非公开 helper。

### `class SymbolGtOp(lhs: SSAValue, rhs: SSAValue)`

- api：`class SymbolGtOp(lhs: SSAValue, rhs: SSAValue)`
- 参数：
  - `lhs`：左操作数；类型 `SSAValue`；无默认值；不允许 None；必须与右操作数满足同一 API 的类型约束。
  - `rhs`：右操作数；类型 `SSAValue`；无默认值；不允许 None；必须与左操作数满足同一 API 的类型约束。
- 返回值：`SymbolGtOp` 实例。
- 使用示例：

  ```python
    from kernel_gen.dialect.symbol import SymbolGtOp

    value = SymbolGtOp(lhs=lhs, rhs=rhs)
    ```
- 功能说明：构造或表示 `SymbolGtOp` 对应的 symbol dialect operation。
- 注意事项：只允许使用本 API 列表中的公开入口；测试不得直连当前文件之外的非公开 helper。

### `class SymbolGeOp(lhs: SSAValue, rhs: SSAValue)`

- api：`class SymbolGeOp(lhs: SSAValue, rhs: SSAValue)`
- 参数：
  - `lhs`：左操作数；类型 `SSAValue`；无默认值；不允许 None；必须与右操作数满足同一 API 的类型约束。
  - `rhs`：右操作数；类型 `SSAValue`；无默认值；不允许 None；必须与左操作数满足同一 API 的类型约束。
- 返回值：`SymbolGeOp` 实例。
- 使用示例：

  ```python
    from kernel_gen.dialect.symbol import SymbolGeOp

    value = SymbolGeOp(lhs=lhs, rhs=rhs)
    ```
- 功能说明：构造或表示 `SymbolGeOp` 对应的 symbol dialect operation。
- 注意事项：只允许使用本 API 列表中的公开入口；测试不得直连当前文件之外的非公开 helper。

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

### `class SymbolYieldOp(value: SSAValue | None = None)`

- api：`class SymbolYieldOp(value: SSAValue | None = None)`
- 参数：
  - `value`：输入值；类型 `SSAValue | None`；默认值 `None`；不允许 None，除非签名显式允许；用于当前节点、op 或转换的主输入。
- 返回值：`SymbolYieldOp` 实例。
- 使用示例：

  ```python
    from kernel_gen.dialect.symbol import SymbolYieldOp

    value = SymbolYieldOp(value=value)
    ```
- 功能说明：构造或表示 `SymbolYieldOp` 对应的 symbol dialect operation。
- 注意事项：只允许使用本 API 列表中的公开入口；测试不得直连当前文件之外的非公开 helper。

### `class SymbolForOp(iter_attr: SymbolIterAttr, start: SSAValue, end: SSAValue, step: SSAValue, body: Region, init: SSAValue | None = None)`

- api：`class SymbolForOp(iter_attr: SymbolIterAttr, start: SSAValue, end: SSAValue, step: SSAValue, body: Region, init: SSAValue | None = None)`
- 参数：
  - `iter_attr`：循环迭代属性；类型 `SymbolIterAttr`；无默认值；不允许 None；承载 start/end/step 文本。
  - `start`：循环起始符号表达式；类型 `SSAValue`；无默认值；不允许 None。
  - `end`：循环结束符号表达式；类型 `SSAValue`；无默认值；不允许 None。
  - `step`：循环步长符号表达式；类型 `SSAValue`；无默认值；不允许 None。
  - `body`：循环或函数体 region；类型 `Region`；无默认值；不允许 None。
  - `init`：loop-carried 初始值；类型 `SSAValue | None`；默认值 `None`；None 表示无 carried value。
- 返回值：`SymbolForOp` 实例。
- 使用示例：

  ```python
    from kernel_gen.dialect.symbol import SymbolForOp

    value = SymbolForOp(iter_attr=iter_attr, start=start, end=end, step=step, body=body, init=init)
    ```
- 功能说明：构造或表示 `SymbolForOp` 对应的 symbol dialect operation。
- 注意事项：只承接公开 `symbol.for` 语法；loop-carried value 当前仅支持单个 `!symbol.int` 累计值。

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
- 验证 `#symbol.expr<"expr">` 与 `!symbol.int<"expr">` 的 parse/print 稳定性。
- 验证 legacy 宽度整型文本、空表达式、非法表达式的错误路径。
- 验证 parse/print 循环稳定。
- 验证 memory 相关标量语义复用同一套整数-only symbol 规则，包括具名维度表达、乘法步幅表达与常量步幅表达。
- 验证 `symbol.add/sub/mul/div/floordiv` 的最小整数符号算术语义、`!symbol.int<"...">` 类型约束、parse/print 稳定性与错误路径。
- 验证 `symbol.eq/ne/lt/le/gt/ge` 的最小整数符号比较语义、`!symbol.int<"..."> -> i1` 约束、parse/print 稳定性与错误路径。
- 验证 `symbol.to_int` 的整数符号到普通整型转换语义、整型变体覆盖、类型约束与 parse/print 稳定性。
- 验证 `symbol.to_float` 的整数符号到 `f32` 转换语义、类型约束与 parse/print 稳定性。
- 验证 `SymbolPtrType` 的 `!symbol.ptr<dtype>` 文本语法、verifier 约束、parse/print 稳定性，以及拒绝 `!symbol.int<"...">` 作为 dtype 的错误路径。
- 验证 `symbol.get_dim` / `symbol.get_stride` 能从 memory type 读取真实 dim/stride，并返回对应的 symbol value。
- 验证 `symbol.get_dim` / `symbol.get_stride` 读取静态整数 dim/stride 时可折叠为 `symbol.const`，读取符号表达时不折叠。
- 验证 `symbol.get_dim` / `symbol.get_stride` 的错误路径，包括非 memory type、轴号越界、匿名动态条目 `?` 与非法轴号。
- 验证 `symbol.for` 的半开区间循环语义、`start/end/step` 的 `!symbol.int<"...">` 约束、`it` 的 `!symbol.iter<...>` 约束、parse/print 稳定性与 verifier 错误路径。
- 验证 `symbol.for` 的迭代变量 `it` 必须为 `SymbolIterType`，不能是浮点、builtin 整数或其他非 `!symbol.iter<...>` 类型。
- 验证 `symbol.for` 的单个 loop-carried `!symbol.int<"...">` 形式，包括 `iter_args`、第二块参数、单结果、`symbol.yield` 与旧无 carried-value 形式继续兼容。
- 验证 `symbol.const` 生成常量的 `!symbol.int<"...">` 结果类型、parse/print 稳定性与结果类型一致性错误路径。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-SYM-001 | 解析/打印 | `SymbolExprAttr` | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_expr_attr_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_expr_attr_round_trip` |
| TC-SYM-002 | 解析/打印 | `SymbolExprAttr` | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_expr_attr_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_expr_attr_round_trip` |
| TC-SYM-003 | 边界/异常 | `SymbolExprAttr` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_expr_attr_rejects_empty_expr`、`test_symbol_verifier_rejects_illegal_expression_characters`。 | “`SymbolExprAttr`”场景按公开错误语义失败或被拒绝。 | `test_symbol_expr_attr_rejects_empty_expr`、`test_symbol_verifier_rejects_illegal_expression_characters` |
| TC-SYM-004 | 解析/打印 | `SymbolValueType` | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_value_type_round_trip_for_integer_only_semantics`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_value_type_round_trip_for_integer_only_semantics` |
| TC-SYM-005 | 解析/打印 | `SymbolValueType` | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_value_type_round_trip_for_integer_only_semantics`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_value_type_round_trip_for_integer_only_semantics` |
| TC-SYM-006 | 解析/打印 | `SymbolValueType` | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_value_type_round_trip_for_integer_only_semantics`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_value_type_round_trip_for_integer_only_semantics` |
| TC-SYM-007 | 边界/异常 | `SymbolValueType` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_value_type_rejects_unsupported_legacy_text_forms`、`test_symbol_verifier_rejects_illegal_expression_characters`。 | “`SymbolValueType`”场景按公开错误语义失败或被拒绝。 | `test_symbol_value_type_rejects_unsupported_legacy_text_forms`、`test_symbol_verifier_rejects_illegal_expression_characters` |
| TC-SYM-008 | 边界/异常 | `SymbolValueType` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_value_type_rejects_unsupported_legacy_text_forms`。 | “`SymbolValueType`”场景按公开错误语义失败或被拒绝。 | `test_symbol_value_type_rejects_unsupported_legacy_text_forms` |
| TC-SYM-052 | 解析/打印 | `SymbolIterType` | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_iter_type_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_iter_type_round_trip` |
| TC-SYM-009 | 解析/打印 | parse/print | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_expr_attr_round_trip`、`test_symbol_value_type_round_trip_for_integer_only_semantics`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_expr_attr_round_trip`、`test_symbol_value_type_round_trip_for_integer_only_semantics` |
| TC-SYM-010 | 符号语义 | 相等性 | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_symbol_value_type_equality_depends_on_expr_only`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“相等性”场景。 | `test_symbol_value_type_equality_depends_on_expr_only` |
| TC-SYM-011 | 符号语义 | 相等性 | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_symbol_value_type_equality_depends_on_expr_only`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“相等性”场景。 | `test_symbol_value_type_equality_depends_on_expr_only` |
| TC-SYM-012 | 符号语义 | 相等性 | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_symbol_value_type_equality_depends_on_expr_only`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“相等性”场景。 | `test_symbol_value_type_equality_depends_on_expr_only` |
| TC-SYM-013 | 解析/打印 | memory 元信息标量 | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_expr_attr_round_trip`、`test_symbol_value_type_round_trip_for_integer_only_semantics`、`test_memory_scalar_components_round_trip_through_symbol_dialect`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_expr_attr_round_trip`、`test_symbol_value_type_round_trip_for_integer_only_semantics`、`test_memory_scalar_components_round_trip_through_symbol_dialect` |
| TC-SYM-014 | 解析/打印 | memory 元信息标量 | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_value_type_round_trip_for_integer_only_semantics`、`test_memory_scalar_components_round_trip_through_symbol_dialect`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_value_type_round_trip_for_integer_only_semantics`、`test_memory_scalar_components_round_trip_through_symbol_dialect` |
| TC-SYM-015 | 符号语义 | `symbol.add/sub/mul/div/floordiv` | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_symbol_arith_ops_verify_success`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“`symbol.add/sub/mul/div/floordiv`”场景。 | `test_symbol_arith_ops_verify_success` |
| TC-SYM-016 | 解析/打印 | `symbol.add/sub/mul/div/floordiv` | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_symbol_arith_ops_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_symbol_arith_ops_round_trip` |
| TC-SYM-017 | 边界/异常 | `symbol.add/sub/mul/div/floordiv` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_arith_ops_reject_non_symbol_int_types`。 | “`symbol.add/sub/mul/div/floordiv`”场景按公开错误语义失败或被拒绝。 | `test_symbol_arith_ops_reject_non_symbol_int_types` |
| TC-SYM-018 | 边界/异常 | `symbol.add/sub/mul/div/floordiv` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_arith_ops_reject_malformed_signatures`。 | “`symbol.add/sub/mul/div/floordiv`”场景按公开错误语义失败或被拒绝。 | `test_symbol_arith_ops_reject_malformed_signatures` |
| TC-SYM-019 | 边界/异常 | `symbol.add/sub/mul/div/floordiv` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_symbol_arith_ops_error_messages_include_context`。 | “`symbol.add/sub/mul/div/floordiv`”场景按公开错误语义失败或被拒绝。 | `test_symbol_arith_ops_error_messages_include_context` |
| TC-SYM-020 | 符号语义 | `symbol.eq/ne/lt/le/gt/ge` | 准备公开 SymbolDim、shape、stride、axis 或 symbol IR 输入。 | 运行 `test_symbol_compare_ops_verify_success`。 | 符号表达、shape/stride/axis 结果或 symbol IR 文本体现“`symbol.eq/ne/lt/le/gt/ge`”场景。 | `test_symbol_compare_ops_verify_success` |
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
