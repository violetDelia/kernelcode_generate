# symbol.md

## 功能简介

定义 `symbol dialect` 的类型与基础构件，用于在 IR 中显式表示“带符号值语义的整型标量”。该方言的核心目标是让类型本身携带一个符号表达，例如 `!symbol.int<"N">` 表示“这是一个整数值，其值语义为符号 `N`”。本方言同时作为 memory 相关符号标量语义的唯一归属：`shape`、`stride`、`offset`、`size`、循环边界等位置只要进入 IR 并需要表达单个整数符号值，就统一落到 `symbol dialect`。在此基础上，本方言允许最小范围的整数符号算术与比较 op，用于在 IR 中显式表达 `symbol.int` 标量之间的加、减、乘以及比较计算。该方言不负责张量、内存容器、通用控制流或超出最小整数符号算术/比较范围的数值计算语义。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`我不是牛马`
- `spec`：[`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)
- `test`：[`test/dialect/test_symbol_dialect.py`](../../test/dialect/test_symbol_dialect.py)
- `功能实现`：[`kernel_gen/dialect/symbol.py`](../../kernel_gen/dialect/symbol.py)

## 依赖

- [`spec/symbol_variable/symbol_dim.md`](../../spec/symbol_variable/symbol_dim.md)：提供符号维度与符号表达的基础语义。
- [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)：高层 `Memory` 容器复用本方言的 memory 相关符号标量语义。
- [`spec/dialect/nn.md`](../../spec/dialect/nn.md)：提供当前 IR 层唯一合法的 `MemoryType`（当前文本载体仍为 `!nn.memory<...>`）。
- [`kernel_gen/dialect/symbol.py`](../../kernel_gen/dialect/symbol.py)：`symbol dialect` 的实现入口。

## 目标

- 为项目提供统一的“符号值类型”表达，使 IR 能直接表示某个整型标量值对应的符号语义。
- 让 `shape`、`offset`、`stride`、循环边界、算子属性等场景中的整型符号值可以在类型层面保持稳定表达。
- 收敛 memory 相关符号标量的方言归属：`Memory`、`MemoryType`、`dma` 相关 op 若需要表达单个维度、步幅、偏移或切片大小的整数符号语义，应统一复用 `SymbolExprAttr` / `SymbolValueType`，而不是在各自 spec 中再定义一套标量 symbol type。
- 提供从 memory type 读取单个维度或步幅并返回 symbol value 的查询接口，避免其他方言重复定义 `dim/stride -> value` 读取语义。
- 为后续 `nn`、`dma`、`kernel`、`dsl` 等方言提供统一的符号值口径，避免每个方言各自维护一套符号标量表达。
- 提供最小整数符号算术与比较接口，使 `!symbol.int<"expr">` 标量可在方言内完成基础加、减、乘组合与相等/大小关系判断，而无需回退到其他算术方言。
- 保持类型表达尽量简单，优先服务开发者理解和方言间协同，而不是追求复杂的符号推导系统。
- 本文件中的“符号值”指与 SSA value 绑定的单个整数值语义表达，可以是具名符号、整型表达式或整型常量，如 `N`、`M + 1`、`B * K`、`1`、`2`、`3`。

## 限制与边界

- `symbol dialect` 只定义符号值类型、最小整数符号算术 op、基础约束以及从 memory type 读取单个 dim/stride 值的查询接口；不定义张量类型、内存类型、通用控制流 op、通用内存搬运 op 或逐元素张量算术 op。
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
- 若目标维度或步幅条目为匿名动态值 `?`，由于无法稳定映射为 `!symbol.int<"...">`，必须报错；本接口只接受可表示为整数常量或符号表达的条目。
- `symbol.get_dim` / `symbol.get_stride` 的轴号当前必须是静态整数索引；越界、负数或非整数轴号必须报错。
- 本方言暂不定义“未知但无名字”的匿名符号值；若需要动态未知值，应优先使用具名符号或由其他方言以 SSA value 传递。
- 当前只定义整数语义，不区分 `int/int8/int16/int32/int64` 等具体整型宽度，也不定义 `index`、浮点或其他非整型 symbol 类型。
- 当前最小算术/比较范围仅包含 `symbol.add`、`symbol.sub`、`symbol.mul`、`symbol.eq`、`symbol.ne`、`symbol.lt`、`symbol.le`、`symbol.gt`、`symbol.ge`；不定义除法、取模、按位运算、布尔逻辑组合、广播或张量级算术。

## 公开接口

### 方言公开构件

功能说明：

- `symbol dialect` 的公开构件由两部分组成：
  - `SymbolValueType`：带符号值语义的整型标量类型
  - `SymbolExprAttr`：用于承载符号表达的 attribute

参数说明：

- 无参数。

使用示例：

```python
from kernel_gen.dialect.symbol import SymbolExprAttr, SymbolValueType
```

注意事项：

- `SymbolValueType` 当前固定表示整数语义的符号值类型。
- `SymbolExprAttr` 只承载单个标量值对应的整数值语义表达。

返回与限制：

- 返回 `symbol dialect` 对外暴露的类型与 attribute 定义。

### `SymbolExprAttr`

功能说明：

- 表示一个可打印、可比较、可校验的整数值语义表达。
- 用于给 `SymbolValueType` 提供值语义来源。

参数说明：

- `expr(string)`：整数值语义表达文本，例如 `N`、`M + 1`、`B * K`、`1`、`2`、`3`。

使用示例：

```python
expr = SymbolExprAttr("N")
expr2 = SymbolExprAttr("M + 1")
```

注意事项：

- 表达式必须是非空字符串。
- 表达式应使用稳定文本格式，避免同义但不同打印形式导致比较不一致。
- 表达式中的名字应与项目中的符号命名规则保持一致；纯整数字面量同样合法。

返回与限制：

- 返回类型：`SymbolExprAttr`
- 限制：仅承载单个标量值的符号表达。

### `SymbolValueType`

功能说明：

- 表示“整数语义 + 符号值语义”的组合类型。
- 对应的正式文本形式为 `!symbol.int<"expr">`，例如 `!symbol.int<"N">`、`!symbol.int<"M + 1">`。

参数说明：

- `expr(SymbolExprAttr)`：该值对应的符号表达。

使用示例：

```python
ty = SymbolValueType.from_expr("N")
const_ty = SymbolValueType.from_expr("3")
```

注意事项：

- `expr` 必须存在，不允许创建无符号表达的 `SymbolValueType`。
- 当前 `SymbolValueType` 只表示整数语义，不再携带或区分整型宽度。
- `expr` 可以是具名符号，也可以是常量整数值，如 `1`、`2`、`3`。
- `SymbolValueType` 的打印语义应稳定映射为 `!symbol.int<"expr">`。

返回与限制：

- 返回类型：`SymbolValueType`
- 限制：只表示单个整型标量值的符号语义，不表示 shape 列表或张量。

### 文本语法

功能说明：

- 规定 `symbol dialect` 在文档、打印和调试中的正式文本语法。

参数说明：

- `expr`：符号表达。

使用示例：

```text
#symbol.expr<"N">
#symbol.expr<"M + 1">
!symbol.int<"N">
!symbol.int<"3">
```

注意事项：

- `SymbolExprAttr` 使用 `#symbol.expr<"expr">`。
- `SymbolValueType` 使用 `!symbol.int<"expr">`。
- 当前不接受按位宽区分的 legacy 整型文本，或任何非整型文本变体。

返回与限制：

- 返回类型：文本约定。
- 限制：当前 spec 只定义上述两种正式语法，不额外定义等价别名。

### 类型校验规则

功能说明：

- 规定 `SymbolValueType` 的 verifier 行为。

参数说明：

- `expr`：待校验符号表达。

使用示例：

```python
SymbolValueType.from_expr("N")
```

注意事项：

- `expr` 不能为空。
- `expr` 中若出现非法字符、空白后为空、或不可解析的表达式，必须报错。
- `expr` 允许纯整数字面量，`!symbol.int<"1">`、`!symbol.int<"2">`、`!symbol.int<"3">` 都必须视为合法类型表达。
- 同一个 `SymbolValueType` 的相等性比较只比较整数语义下的 `expr`。
- 打印后再解析必须能得到等价类型对象。
- `!symbol.int<"N">` 表示“该 SSA value 的整数值由符号 `N` 表示”，不是变量声明；`!symbol.int<"1">`、`!symbol.int<"2">`、`!symbol.int<"3">` 表示该值已知为对应常量整数。

返回与限制：

- 返回类型：校验规则定义。
- 限制：仅校验整数符号类型表达合法性，不负责判断两个不同表达式是否数学等价。

### Memory 相关符号标量归属

功能说明：

- 规定 memory 相关符号值在 IR 层的归属边界。
- 当 `shape`、`stride`、`offset`、`size` 等 memory 元信息被单独建模为整数标量 attribute/type 时，统一由 `symbol dialect` 负责其整数符号语义表达。

参数说明：

- `expr(string)`：单个 memory 元信息标量对应的整数语义表达，例如 `N`、`K*N`、`3`。

使用示例：

```text
#symbol.expr<"K*N">
!symbol.int<"3">
!symbol.int<"N">
```

注意事项：

- 本归属规则只覆盖“单个整数标量”的 symbol 语义，不直接承载 `shape=[M, N]` 这类多值结构。
- `spec/symbol_variable/memory.md` 负责高层 `Memory` 对象、空间枚举与默认 stride 规则；`symbol dialect` 负责其中单个维度或步幅分量的整数 symbol 语义。
- 常量整数分量与具名符号分量同样适用本规则；`!symbol.int<"1">`、`!symbol.int<"2">`、`!symbol.int<"3">` 都是合法 memory 元信息标量表达。

返回与限制：

- 返回类型：归属规则定义。
- 限制：只定义 memory 元信息中的单值整型 symbol 语义，不定义 memory 容器、memory type 或 memory space。

### `symbol.add` / `symbol.sub` / `symbol.mul`

功能说明：

- 定义 `symbol dialect` 内最小范围的整数符号算术 op。
- `symbol.add` 表示两个 `!symbol.int<"expr">` 标量的整数加法。
- `symbol.sub` 表示两个 `!symbol.int<"expr">` 标量的整数减法。
- `symbol.mul` 表示两个 `!symbol.int<"expr">` 标量的整数乘法。

参数说明：

- `lhs(value)`：左操作数，类型必须为 `!symbol.int<"expr">`。
- `rhs(value)`：右操作数，类型必须为 `!symbol.int<"expr">`。
- `result_type(type)`：结果类型，必须为 `!symbol.int<"expr">`。

使用示例：

```text
%sum = symbol.add %m, %one : !symbol.int<"M">, !symbol.int<"1"> -> !symbol.int<"M + 1">
%diff = symbol.sub %n, %one : !symbol.int<"N">, !symbol.int<"1"> -> !symbol.int<"N - 1">
%prod = symbol.mul %m, %n : !symbol.int<"M">, !symbol.int<"N"> -> !symbol.int<"M*N">
```

注意事项：

- `lhs`、`rhs` 与结果都必须是 `!symbol.int<"expr">`；不接受普通整数、浮点、`index` 或其他 dialect 标量类型。
- 这组 op 只表达整数符号值之间的标量算术，不承担张量逐元素计算、广播、循环控制或 memory 语义。
- verifier 只约束类型一致性、结果类型合法性与 parse/print 稳定性；不要求在方言内证明不同表达式的数学等价性。
- `symbol.add/sub/mul` 可以用于构造后续 `symbol.for` 边界、memory 元信息或其他要求 `!symbol.int<"...">` 的整数标量值，但不会自动化简表达式。
- parse/print 必须稳定遵循 `symbol.<op> %lhs, %rhs : !symbol.int<"...">, !symbol.int<"..."> -> !symbol.int<"...">` 的公开文本形式。
- 错误信息至少应包含具体 op 名称、失败原因以及出错操作数或结果类型。

返回与限制：

- 返回类型：`!symbol.int<"expr">`
- 返回语义：返回保留 symbol 整数值语义的单结果 SSA value。
- 限制：当前只定义二元单结果算术 op，不定义一元取负、n 元折叠、常量折叠或跨类型提升规则。

### `symbol.eq` / `symbol.ne` / `symbol.lt` / `symbol.le` / `symbol.gt` / `symbol.ge`

功能说明：

- 定义 `symbol dialect` 内最小范围的整数符号比较 op。
- `symbol.eq` / `symbol.ne` 表示两个 `!symbol.int<"expr">` 标量的相等/不等比较。
- `symbol.lt` / `symbol.le` / `symbol.gt` / `symbol.ge` 表示两个 `!symbol.int<"expr">` 标量的大小关系比较。
- 比较结果统一表达 true/false 语义，结果类型固定为 `i1`。

参数说明：

- `lhs(value)`：左操作数，类型必须为 `!symbol.int<"expr">`。
- `rhs(value)`：右操作数，类型必须为 `!symbol.int<"expr">`。
- `result_type(type)`：结果类型，必须为 `i1`。

使用示例：

```text
%is_same = symbol.eq %m, %n : !symbol.int<"M">, !symbol.int<"N"> -> i1
%is_less = symbol.lt %i, %end : !symbol.int<"i">, !symbol.int<"N"> -> i1
%is_last = symbol.ge %i, %limit : !symbol.int<"i">, !symbol.int<"N - 1"> -> i1
```

注意事项：

- `lhs` 与 `rhs` 必须都是 `!symbol.int<"expr">`；不接受普通整数、浮点、`index` 或其他 dialect 标量类型。
- 结果类型固定为 `i1`，用于表达 true/false 语义；不允许结果继续保留为 `!symbol.int<"...">` 或其他非布尔类型。
- 这组 op 只表达标量比较关系，不承担分支、短路逻辑、张量级比较、广播或控制流语义。
- verifier 只约束操作数类型、结果类型、op 名称对应的语义类别与 parse/print 稳定性；不要求在方言内证明两个符号表达式的数学关系是否恒真或恒假。
- parse/print 必须稳定遵循 `symbol.<cmp> %lhs, %rhs : !symbol.int<"...">, !symbol.int<"..."> -> i1` 的公开文本形式。
- 错误信息至少应包含具体 op 名称、失败原因以及出错操作数或结果类型。

返回与限制：

- 返回类型：`i1`
- 返回语义：返回表达 true/false 语义的单结果 SSA value。
- 限制：当前只定义二元单结果比较 op，不定义三路比较、链式比较、逻辑与/或/非、谓词折叠或跨类型比较规则。

### `symbol.get_dim`

功能说明：

- 从 memory SSA value 的 memory type 中读取指定轴上的真实 `shape` 分量，并返回对应的整数 symbol value。
- 该接口只做“读取已有类型信息并转成 value”的语义收敛，不负责形状推导或约束求解。

参数说明：

- `source(SSA value)`：待读取的 memory 值；当前必须具有 `MemoryType`。
- `axis(int)`：要读取的维度下标，按 `source.type.shape` 的顺序从 `0` 开始计数。

使用示例：

```text
%d0 = symbol.get_dim %mem[0] : !nn.memory<[4, 8], [8, 1], i32, #nn.space<global>> -> !symbol.int<"4">
%d1 = symbol.get_dim %mem[1] : !nn.memory<[M, N], [N, 1], i32, #nn.space<global>> -> !symbol.int<"N">
```

注意事项：

- `source` 必须是 memory SSA value，且其类型当前必须为 `MemoryType`。
- 返回值语义直接来自 `source.type.shape[axis]`：静态整数分量返回对应常量整数 value，符号分量返回对应符号表达 value。
- 当目标分量为 `?`、轴号越界、轴号为负数或轴号不是静态整数时，必须报错。
- 本接口只读取真实 dim，不读取 stride、offset、size 或 element type。

返回与限制：

- 返回类型：`!symbol.int<"expr">`
- 限制：`expr` 必须可稳定表示为整数常量或符号表达；不支持匿名动态条目 `?`。

### `symbol.get_stride`

功能说明：

- 从 memory SSA value 的 memory type 中读取指定轴上的真实 `stride` 分量，并返回对应的整数 symbol value。
- 该接口只做“读取已有类型信息并转成 value”的语义收敛，不负责默认 stride 推导或布局修复。

参数说明：

- `source(SSA value)`：待读取的 memory 值；当前必须具有 `MemoryType`。
- `axis(int)`：要读取的步幅下标，按 `source.type.stride` 的顺序从 `0` 开始计数。

使用示例：

```text
%s0 = symbol.get_stride %mem[0] : !nn.memory<[4, 8], [8, 1], i32, #nn.space<global>> -> !symbol.int<"8">
%s1 = symbol.get_stride %mem[1] : !nn.memory<[M, N], [K*N, N], i32, #nn.space<global>> -> !symbol.int<"N">
```

注意事项：

- `source` 必须是 memory SSA value，且其类型当前必须为 `MemoryType`。
- 返回值语义直接来自 `source.type.stride[axis]`：静态整数分量返回对应常量整数 value，符号分量返回对应符号表达 value。
- 当目标分量为 `?`、轴号越界、轴号为负数或轴号不是静态整数时，必须报错。
- 本接口只读取真实 stride，不读取 shape、offset、size 或 element type。

返回与限制：

- 返回类型：`!symbol.int<"expr">`
- 限制：`expr` 必须可稳定表示为整数常量或符号表达；不支持匿名动态条目 `?`。

### `symbol.for`

功能说明：

- 定义 `symbol dialect` 中面向整数符号值的循环 op。
- 用于在 IR 层显式表达“以符号整数边界驱动的半开区间循环”，其中 `start`、`end`、`step` 与迭代变量 `it` 都统一采用 `!symbol.int<"expr">` 语义。
- 该 op 只负责循环边界与迭代变量的符号整数约束，不扩展为通用控制流方言；循环体内部承载的具体计算或访存语义仍由其他 dialect 负责。
- `it` 的类型基线必须是 `SymbolValueType`；用户口径中的“symbol scf”迭代变量，本质上就是 `symbol.for` 暴露的 `!symbol.int<"expr">` block argument。

参数说明：

- `start(value)`：循环起始值，类型必须为 `!symbol.int<"expr">`。
- `end(value)`：循环结束值，类型必须为 `!symbol.int<"expr">`。
- `step(value)`：循环步长值，类型必须为 `!symbol.int<"expr">`。
- `it(block argument)`：循环体块参数，表示当前迭代值，类型必须为 `!symbol.int<"expr">`，并与循环变量语义绑定。
- `body(region)`：循环体 region；当前仅要求是单 region、单块结构。

使用示例：

```text
symbol.for %i = %start to %end step %step
    : !symbol.int<"M">, !symbol.int<"N">, !symbol.int<"1"> {
  %d = symbol.get_dim %mem[0] : !nn.memory<[M, N], [N, 1], i32, #nn.space<global>> -> !symbol.int<"M">
}
```

注意事项：

- 语义采用半开区间：从 `start` 开始，每轮累加 `step`，当下一轮将不再满足区间进入条件时终止；不包含 `end` 本身。
- `start`、`end`、`step`、`it` 必须全部是 `!symbol.int<"expr">`，不接受普通整数类型、浮点类型或其他 dialect 的标量类型。
- verifier 必须逐项校验 `it` 为 `SymbolValueType`；即使 `start/end/step` 合法，只要 `it` 为 `f32`、`f64`、`index`、普通 `i32` 或其他非 `SymbolValueType`，都必须报错。
- `it` 是循环体内部可见的迭代变量，其值语义应与当前迭代点一致；打印与解析时必须保持 `it` 的类型稳定。
- 当前 verifier 只约束类型、region 结构、文本语法与可静态判定的错误路径；不要求在 `symbol dialect` 内完成一般符号大小关系证明。
- 若 `step` 的表达式可静态判定为 `0`，必须报错；若 `step` 为纯符号表达且当前无法静态证明为非零，本 spec 不额外引入证明规则，由后续实现按最小可实现口径处理。
- `symbol.for` 不负责推导循环 trip count，不负责循环展开、融合或 lowering 到其他控制流方言。
- 当前文本语法中的类型段按 `start/end/step` 的顺序显式打印，`it` 类型由块参数与前三者共享的 `!symbol.int<"...">` 语义共同约束。
- parse/print 必须保持 round-trip 稳定；错误信息至少应包含出错操作、失败原因以及相关操作数或 region 位置。

返回与限制：

- 返回类型：无结果 op。
- 返回语义：通过 region 承载循环体，并在循环体块参数中暴露当前迭代变量 `it`。
- 限制：当前只定义单迭代变量、单 region、单块的 `symbol.for`；不定义循环携带值、并行循环、多结果循环或提前退出语义。

## 测试

- 测试文件：[`test/dialect/test_symbol_dialect.py`](../../test/dialect/test_symbol_dialect.py)
- 执行命令：`pytest -q test/dialect/test_symbol_dialect.py`

### 测试目标

- 验证 `SymbolExprAttr` 的表达式构造、打印与解析。
- 验证 `SymbolValueType` 的整数-only 符号表达绑定关系。
- 验证 `#symbol.expr<"expr">` 与 `!symbol.int<"expr">` 的 parse/print 稳定性。
- 验证 legacy 宽度整型文本、空表达式、非法表达式的错误路径。
- 验证 parse/print 循环稳定。
- 验证 memory 相关标量语义复用同一套整数-only symbol 规则，包括具名维度表达、乘法步幅表达与常量步幅表达。
- 验证 `symbol.add/sub/mul` 的最小整数符号算术语义、`!symbol.int<"...">` 类型约束、parse/print 稳定性与错误路径。
- 验证 `symbol.eq/ne/lt/le/gt/ge` 的最小整数符号比较语义、`!symbol.int<"..."> -> i1` 约束、parse/print 稳定性与错误路径。
- 验证 `symbol.get_dim` / `symbol.get_stride` 能从 memory type 读取真实 dim/stride，并返回对应的 symbol value。
- 验证 `symbol.get_dim` / `symbol.get_stride` 的错误路径，包括非 memory type、轴号越界、匿名动态条目 `?` 与非法轴号。
- 验证 `symbol.for` 的半开区间循环语义、`!symbol.int<"...">` 类型约束、parse/print 稳定性与 verifier 错误路径。
- 验证 `symbol.for` 的迭代变量 `it` 必须为 `SymbolValueType`，不能是浮点、builtin 整数或其他非 `!symbol.int<"...">` 类型。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 对应测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-SYM-001 | `SymbolExprAttr` | 基础符号表达 | 无 | 解析 `#symbol.expr<"N">` | verifier 通过；打印结果稳定 | `test_symbol_expr_attr_round_trip` |
| TC-SYM-002 | `SymbolExprAttr` | 符号表达式 | 无 | 解析 `#symbol.expr<"M + 1">` | verifier 通过；打印结果稳定 | `test_symbol_expr_attr_round_trip` |
| TC-SYM-003 | `SymbolExprAttr` | 空表达式与非法字符非法 | 无 | 构造空字符串表达式，或构造非法字符表达式 | verifier 报错 | `test_symbol_expr_attr_rejects_empty_expr`、`test_symbol_verifier_rejects_illegal_expression_characters` |
| TC-SYM-004 | `SymbolValueType` | 基础整数符号值 | 无 | 解析 `!symbol.int<"N">` | verifier 通过 | `test_symbol_value_type_round_trip_for_integer_only_semantics` |
| TC-SYM-005 | `SymbolValueType` | 整数表达式 | 无 | 解析 `!symbol.int<"M + 1">` | verifier 通过 | `test_symbol_value_type_round_trip_for_integer_only_semantics` |
| TC-SYM-006 | `SymbolValueType` | 常量值语义 | 无 | 解析 `!symbol.int<"3">` | verifier 通过 | `test_symbol_value_type_round_trip_for_integer_only_semantics` |
| TC-SYM-007 | `SymbolValueType` | legacy 文本或非法字符非法 | 无 | 解析 `!symbol.int64<"N">`，或构造非法字符表达式 | parse/verifier 报错 | `test_symbol_value_type_rejects_unsupported_legacy_text_forms`、`test_symbol_verifier_rejects_illegal_expression_characters` |
| TC-SYM-008 | `SymbolValueType` | 缺少表达式 | 无 | 解析 `!symbol.int` | parse 报错 | `test_symbol_value_type_rejects_unsupported_legacy_text_forms` |
| TC-SYM-009 | parse/print | 循环稳定 | 已实现文本语法 | parse 后再 print | attr/type 语义保持一致 | `test_symbol_expr_attr_round_trip`、`test_symbol_value_type_round_trip_for_integer_only_semantics` |
| TC-SYM-010 | 相等性 | 相同表达式 | 无 | 比较两个 `!symbol.int<"N">` | 相等 | `test_symbol_value_type_equality_depends_on_expr_only` |
| TC-SYM-011 | 相等性 | 不再区分整型宽度 | 无 | 在整数-only 语义下比较相同表达式类型 | 不因宽度差异产生额外类型分支 | `test_symbol_value_type_equality_depends_on_expr_only` |
| TC-SYM-012 | 相等性 | 表达式不同 | 无 | 比较 `!symbol.int<"N">` 与 `!symbol.int<"M">` | 不相等 | `test_symbol_value_type_equality_depends_on_expr_only` |
| TC-SYM-013 | memory 元信息标量 | 符号维度或步幅分量 | 无 | 解析 `#symbol.expr<"K*N">` 或 `!symbol.int<"N">` | 作为 memory 相关单值整数语义合法并稳定 round-trip | `test_symbol_expr_attr_round_trip`、`test_symbol_value_type_round_trip_for_integer_only_semantics`、`test_memory_scalar_components_round_trip_through_symbol_dialect` |
| TC-SYM-014 | memory 元信息标量 | 常量步幅或常量维度分量 | 无 | 解析 `!symbol.int<"1">`、`!symbol.int<"2">`、`!symbol.int<"3">` | 作为常量整数值语义合法 | `test_symbol_value_type_round_trip_for_integer_only_semantics`、`test_memory_scalar_components_round_trip_through_symbol_dialect` |
| TC-SYM-015 | `symbol.add/sub/mul` | 基础算术合法路径 | `lhs/rhs/result` 均为 `!symbol.int<"...">` | 构造 `symbol.add`、`symbol.sub`、`symbol.mul` | verifier 通过；返回 `!symbol.int<"...">` | `test_symbol_arith_ops_verify_success` |
| TC-SYM-016 | `symbol.add/sub/mul` | parse/print 稳定 | 已实现公开文本语法 | parse 后再 print | 文本与结果类型稳定 | `test_symbol_arith_ops_round_trip` |
| TC-SYM-017 | `symbol.add/sub/mul` | 非 symbol 类型非法 | 任一操作数或结果不是 `!symbol.int<"...">` | 构造并校验 op | verifier 报错 | `test_symbol_arith_ops_reject_non_symbol_int_types` |
| TC-SYM-018 | `symbol.add/sub/mul` | 文本或结果签名非法 | 缺少结果类型、操作数数量错误或文本不完整 | parse / 构造并校验 op | parse/verifier 报错 | `test_symbol_arith_ops_reject_malformed_signatures` |
| TC-SYM-019 | `symbol.add/sub/mul` | 错误信息闭环 | 触发类型或签名错误 | verifier / parse 失败 | 错误信息包含具体 op 名称与失败原因 | `test_symbol_arith_ops_error_messages_include_context` |
| TC-SYM-020 | `symbol.eq/ne/lt/le/gt/ge` | 基础比较合法路径 | `lhs/rhs` 为 `!symbol.int<"...">`，结果为 `i1` | 构造各比较 op | verifier 通过；返回 true/false 语义结果 | `test_symbol_compare_ops_verify_success` |
| TC-SYM-021 | `symbol.eq/ne/lt/le/gt/ge` | parse/print 稳定 | 已实现公开文本语法 | parse 后再 print | 文本、谓词与结果类型稳定 | `test_symbol_compare_ops_round_trip` |
| TC-SYM-022 | `symbol.eq/ne/lt/le/gt/ge` | 非 symbol 类型操作数非法 | 任一操作数不是 `!symbol.int<"...">` | 构造并校验 op | verifier 报错 | `test_symbol_compare_ops_reject_non_symbol_int_operands` |
| TC-SYM-023 | `symbol.eq/ne/lt/le/gt/ge` | 非布尔结果非法 | 结果类型不是 `i1` | 构造并校验 op | verifier 报错 | `test_symbol_compare_ops_reject_non_i1_result` |
| TC-SYM-024 | `symbol.eq/ne/lt/le/gt/ge` | 文本或签名非法 | 缺少结果类型、操作数数量错误或文本不完整 | parse / 构造并校验 op | parse/verifier 报错 | `test_symbol_compare_ops_reject_malformed_signatures` |
| TC-SYM-025 | `symbol.eq/ne/lt/le/gt/ge` | 错误信息闭环 | 触发类型或签名错误 | verifier / parse 失败 | 错误信息包含具体 op 名称与失败原因 | `test_symbol_compare_ops_error_messages_include_context` |
| TC-SYM-026 | `symbol.get_dim` | 静态维度读取 | `source.type.shape[axis]` 为静态整数 | 读取指定轴 dim | 返回对应 `!symbol.int<"...">` value | `test_symbol_get_dim_reads_static_dim_from_memory_type` |
| TC-SYM-027 | `symbol.get_dim` | 符号维度读取 | `source.type.shape[axis]` 为符号表达 | 读取指定轴 dim | 返回对应符号表达 value | `test_symbol_get_dim_reads_symbolic_dim_from_memory_type` |
| TC-SYM-028 | `symbol.get_stride` | 静态步幅读取 | `source.type.stride[axis]` 为静态整数 | 读取指定轴 stride | 返回对应 `!symbol.int<"...">` value | `test_symbol_get_stride_reads_static_stride_from_memory_type` |
| TC-SYM-029 | `symbol.get_stride` | 符号步幅读取 | `source.type.stride[axis]` 为符号表达 | 读取指定轴 stride | 返回对应符号表达 value | `test_symbol_get_stride_reads_symbolic_stride_from_memory_type` |
| TC-SYM-030 | `symbol.get_dim/get_stride` | 轴号非法 | `axis` 越界、负数或非静态整数 | 构造并校验 op | verifier 报错 | `test_symbol_get_dim_rejects_invalid_axis`、`test_symbol_get_stride_rejects_invalid_axis` |
| TC-SYM-031 | `symbol.get_dim/get_stride` | memory type 非法或匿名动态条目非法 | `source` 非 `MemoryType`，或目标条目为 `?` | 构造并校验 op | verifier 报错 | `test_symbol_get_dim_rejects_non_memory_type`、`test_symbol_get_stride_rejects_unknown_entry` |
| TC-SYM-032 | `symbol.for` | 基础半开区间循环 | `start/end/step` 与块参数 `it` 均为 `!symbol.int<"...">` | 构造 `symbol.for %i = %start to %end step %step` | verifier 通过；`it` 作为 `SymbolValueType` 块参数暴露；循环采用半开区间语义 | `test_symbol_for_accepts_symbol_int_bounds_and_iter_arg` |
| TC-SYM-033 | `symbol.for` | parse/print 稳定 | 已实现 `symbol.for` 文本语法 | parse 后再 print | 文本与 region 结构稳定 round-trip | `test_symbol_for_round_trip` |
| TC-SYM-034 | `symbol.for` | 非 symbol.int 类型非法 | `start/end/step` 或 `it` 含非 `!symbol.int<"...">` 类型，如 `f32`、`f64`、`index`、`i32` | 构造并校验 op | verifier 报错；`it` 不得为任何非 `SymbolValueType` | `test_symbol_for_rejects_non_symbol_int_operands` |
| TC-SYM-035 | `symbol.for` | `step = 0` 非法 | `step` 可静态判定为 `!symbol.int<"0">` | 构造并校验 op | verifier 报错 | `test_symbol_for_rejects_zero_step` |
| TC-SYM-036 | `symbol.for` | region 结构非法 | 缺少 region、块参数缺失或块参数类型不匹配 | 构造并校验 op | verifier 报错 | `test_symbol_for_rejects_invalid_region_shape` |
| TC-SYM-037 | `symbol.for` | 文本语法非法 | 缺少 `to/step` 片段，或类型段数量不匹配 | parse `symbol.for` 文本 | parse 报错 | `test_symbol_for_parse_rejects_malformed_text` |
| TC-SYM-038 | `symbol.for` | 错误信息闭环 | 操作数类型、步长或 region 校验失败 | 触发 verifier / parse 错误 | 错误信息包含 op 名称与失败原因 | `test_symbol_for_error_messages_include_context` |
