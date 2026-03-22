# symbol.md

## 功能简介

定义 `symbol dialect` 的类型与基础构件，用于在 IR 中显式表示“带符号值语义的整型标量”。该方言的核心目标是让类型本身携带一个符号表达，例如 `!symbol.int<"N">` 表示“这是一个整数值，其值语义为符号 `N`”。本方言同时作为 memory 相关符号标量语义的唯一归属：`shape`、`stride`、`offset`、`size`、循环边界等位置只要进入 IR 并需要表达单个整数符号值，就统一落到 `symbol dialect`。该方言不负责张量、内存容器、控制流或数值计算方言语义。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`榕`
- `spec`：[`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)
- `test`：[`test/dialect/test_symbol_dialect.py`](../../test/dialect/test_symbol_dialect.py)
- `功能实现`：[`kernel_gen/dialect/symbol.py`](../../kernel_gen/dialect/symbol.py)

## 依赖

- [`spec/symbol_variable/symbol_dim.md`](../../spec/symbol_variable/symbol_dim.md)：提供符号维度与符号表达的基础语义。
- [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)：高层 `Memory` 容器复用本方言的 memory 相关符号标量语义。
- [`kernel_gen/dialect/symbol.py`](../../kernel_gen/dialect/symbol.py)：`symbol dialect` 的实现入口。

## 目标

- 为项目提供统一的“符号值类型”表达，使 IR 能直接表示某个整型标量值对应的符号语义。
- 让 `shape`、`offset`、`stride`、循环边界、算子属性等场景中的整型符号值可以在类型层面保持稳定表达。
- 收敛 memory 相关符号标量的方言归属：`Memory`、`NnMemoryType`、`dma` 相关 op 若需要表达单个维度、步幅、偏移或切片大小的整数符号语义，应统一复用 `SymbolExprAttr` / `SymbolValueType`，而不是在各自 spec 中再定义一套标量 symbol type。
- 为后续 `nn`、`dma`、`kernel`、`dsl` 等方言提供统一的符号值口径，避免每个方言各自维护一套符号标量表达。
- 保持类型表达尽量简单，优先服务开发者理解和方言间协同，而不是追求复杂的符号推导系统。
- 本文件中的“符号值”指与 SSA value 绑定的单个整数值语义表达，可以是具名符号、整型表达式或整型常量，如 `N`、`M + 1`、`B * K`、`1`、`2`、`3`。

## 限制与边界

- `symbol dialect` 只定义符号值类型与基础约束，不定义张量类型、内存类型、控制流 op、内存 op 或逐元素算术 op。
- 本方言的重点是“值的符号语义如何表达”，不是“如何求值”或“如何解方程”。
- 本方言不负责通用符号化简、约束求解、范围分析、证明或 SMT 集成。
- 符号表达式只要求可稳定打印、可比较、可校验；不要求在 dialect 内部完成复杂等价变换。
- 普通整数类型与符号值类型是不同概念：`int` 与 `!symbol.int<"N">` 不是同一类型。
- `!symbol.int<"1">`、`!symbol.int<"2">`、`!symbol.int<"3">` 这类常量整数值类型是合法的，表示“值语义已知为该整数常量”。
- `!symbol.int<"N">` 中字符串里的表达式表示“值语义”，不是附加注释，也不是 shape 维度列表。
- 类型中的符号表达应面向单个标量值；shape 列表、stride 列表等多值结构不直接放入本方言标量类型中。
- `Memory`、`MemorySpace`、`LocalSpaceMeta` 这类高层内存容器或空间枚举不属于本方言；本方言只负责它们内部可能出现的单个整型符号值语义。
- 本方言暂不定义“未知但无名字”的匿名符号值；若需要动态未知值，应优先使用具名符号或由其他方言以 SSA value 传递。
- 当前只定义整数语义，不区分 `int/int8/int16/int32/int64` 等具体整型宽度，也不定义 `index`、浮点或其他非整型 symbol 类型。

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
