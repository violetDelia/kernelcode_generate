# mlir_gen.md

用于定义 `mlir_gen` 这一层的设计规范。该组件负责根据受限 Python 函数生成对应的 MLIR `func.func`，并在函数体中按照源码表达式顺序构造对应的 MLIR op 与 SSA value。但本文件关注的核心是“如何从函数内容生成 MLIR IR”，而不是把目标限定为某一个固定 dialect。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`榕`
- `spec`：[`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
- `关联 Visitor`：[`spec/dsl/ast_visitor.md`](../../spec/dsl/ast_visitor.md)
- `关联 Dialect`：[`spec/dialect/nn.md`](../../spec/dialect/nn.md)
- `关联运算`：[`spec/operation/nn.md`](../../spec/operation/nn.md)
- `关联形状`：[`spec/symbol_variable/symbol_shape.md`](../../spec/symbol_variable/symbol_shape.md)
- `test`：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
- `功能实现`：[`python/dsl/ast_visitor.py`](../../python/dsl/ast_visitor.py)

## 范围与目标

- 根据受限 Python 函数生成对应的 MLIR `func.func`。
- 约束 `ast visitor -> AST -> MLIR value/op -> func.func` 这一生成链路。
- 明确函数参数、局部表达式、返回值如何映射为 MLIR block argument、SSA value 和 op。
- 约束函数体中的 op 必须与原函数中的表达式语义一一对应。
- 保证最终 IR 可以再被 printer 输出为稳定的 MLIR 风格文本。
- 支持根据表达式语义生成不同目标 dialect 的 op；`nn` 只是当前已有实现的一类目标。

## 非目标

- 不负责 AST 构建细节；AST 语义由 [`spec/dsl/ast_visitor.md`](../../spec/dsl/ast_visitor.md) 约束。
- 不负责逐节点 lowering 规则；lowering 语义由 visitor 与 dialect 规范共同决定。
- 不负责优化、canonicalization、bufferization、codegen 或后端执行。
- 不定义新的 MLIR dialect；只约束如何生成兼容 MLIR / xDSL 生态的 op 与类型。

## 设计背景

- 当前项目中没有独立的 `mlir_gen.py` 模块；相关入口在 [`python/dsl/ast_visitor.py`](../../python/dsl/ast_visitor.py) 中。
- `mlir_gen` 的实质职责不是“简单打印文本”，而是：
  1. 读取函数
  2. 借助 `ast visitor` 遍历函数 AST
  3. 根据不同表达式节点生成对应的 MLIR op / SSA value
  4. 组织成 `func.func`
  5. 挂入 `builtin.module`
- `emit_mlir(...)` 只是该链路的文本输出入口；其上游必须已经完成 `func.func` 与函数体 op 的生成。
- 当前项目里最成熟的生成目标是 `nn` 相关 op，但该层设计上不应把目标固定为 `nn`。

## 输入与输出

### 输入

`mlir_gen` 的核心输入是 Python 函数对象。


生成流程中也允许接收已经存在的 AST 或 module，但那属于复用入口，不是本层的主要设计目标。

### 输出

本层有两类输出：

- 结构化输出：`builtin.module` / `func.func` / 目标 dialect op 组成的 IR 对象
- 文本输出：由 printer 打印得到的 MLIR 风格字符串

其中，结构化 IR 是主输出，文本只是该 IR 的序列化表现。
- 结构化 IR 中的 op 可以来自 `func`、`builtin`、`nn` 或后续引入的其他目标 dialect。

## MLIR 结构约束

本节约束生成出来的 IR 结构，不要求完全复制 LLVM MLIR 官方方言的全部能力，但要求保持与 MLIR 的核心组织方式一致。

### `func.func`

- 每个 DSL 函数在文本中对应一个 `func.func`。
- 每个 DSL 函数在 IR 中首先必须生成一个对应的 `func.func` op。
- `func.func` 的符号名默认与 Python 函数名一致。
- `func.func` 的输入参数与返回类型由 lowering 后的函数类型决定。
- `func.func` 体为单个 `SSACFG` region。
- 本层不允许函数体隐式捕获外部 SSA 值；所有值必须来自参数、局部 op 结果或合法 attribute。
- `func.func` 在文本层允许内联参数语法，但语义上这些参数必须对应入口 block argument。
- 函数体中的操作必须和原始函数中的表达式语义对应，不能脱离源码结构凭空生成无关 op。

### block argument

- 函数参数在 MLIR 文本中表现为 `func.func` 入口 block 的 block argument。
- 张量型参数应 lowering 为 `!nn.memory<...>`。
- 标量参数应 lowering 为对应的基础标量类型；当前实现中 `int` 参数 lowering 为 `i32`。
- block argument 顺序必须与 Python 函数签名顺序一致。
- SSA 值名只用于文本可读性，不作为稳定语义的一部分；打印时允许由 printer 重新编号。

### 局部 SSA value

- 函数体中的中间表达式必须 lowering 为局部 SSA value。
- 每个表达式节点的返回值，要么复用已有 SSA value，要么生成新的 SSA value。
- 赋值语句会把表达式结果绑定到 visitor 的局部符号表，供后续表达式引用。

### `func.return`

- `func.return` 必须是函数体终结语句。
- `func.return` 的返回值个数和类型必须与 `func.func` 签名一致。
- 如果上游返回的是 `Memory` 张量语义对象，则返回值类型应为 `!nn.memory<...>`。
- 若函数签名无返回值，则应打印为空结果的 `func.return`。

## 类型文本约束

- 若输入值对应张量或内存语义对象，则其类型文本必须由目标 dialect 的类型系统明确表达。
- 当前项目已有实现里，`Memory` 与 `SymbolShape` 经 lowering 后，使用 `!nn.memory<shape, stride, element_type, space>` 表示。
- 若未来引入其他类型表示，本层允许根据目标 dialect 切换类型打印策略，但必须保持参数、局部值、返回值类型明确。

### shape

- `shape` 由 `SymbolShape` 对应的维度列表打印得到。
- 静态维度保留为整数。
- 动态维度保留为 `?` 或符号文本，不在文本输出阶段被折叠为静态值。

### stride

- `stride` 与 `shape` 一样保留静态、动态或符号表示。
- `stride` 的 rank 必须与 `shape` 一致。

### element type

- 元素类型由 `NumericType` lowering 到对应的 MLIR / xDSL 元素类型。
- 当前文本中应输出明确的元素类型，而不是 DSL 层枚举名。

### space

- `space` 使用 `#nn.space<global>`、`#nn.space<shared>`、`#nn.space<local>` 形式输出。
- `space` 语义由 [`spec/dialect/nn.md`](../../spec/dialect/nn.md) 约束。

## 表达式到 MLIR 的生成约束

### 总体规则

- `mlir_gen` 必须依赖 `ast visitor` 遍历函数中的所有节点。
- visitor 在遍历过程中，按节点类型决定生成哪种 MLIR value 或 op。
- 生成顺序必须与函数体中表达式的依赖顺序一致。
- 一个表达式若依赖前一表达式的结果，必须消费对应的 SSA value，而不是重复从源码重新构造。

### 参数引用

- `Name` 节点若引用函数参数，应映射到对应的 block argument。
- `Name` 节点若引用局部变量，应映射到符号表中之前绑定的 SSA value。

### 常量

- `Constant` 节点应生成可被后续 op 消费的常量 value 或 attribute。
- 常量的具体表示可由当前 lowering 约定决定，但必须保持类型明确。

### 二元表达式

- `BinOp` 节点应根据运算符和操作数语义生成对应的目标 op。
- 如果操作数是张量或 `Memory` 语义对象，当前实现可映射为：
  - `A + B` -> `nn.add`
  - `A - B` -> `nn.sub`
  - `A * B` -> `nn.mul`
  - `A / B` -> `nn.truediv`
- 如果后续引入其他 lowering 策略，本层允许把相同语法节点映射到其他 dialect，只要语义一致。
- 结果必须生成新的 SSA value，并可被后续表达式继续引用。

### 比较表达式

- `Compare` 节点应根据比较符和操作数语义生成对应的目标 compare op。
- 如果操作数是张量或 `Memory` 语义对象，当前实现可映射为：
  - `A == B` -> `nn.eq`
  - `A != B` -> `nn.ne`
  - `A < B` -> `nn.lt`
  - `A <= B` -> `nn.le`
  - `A > B` -> `nn.gt`
  - `A >= B` -> `nn.ge`
- 如果后续引入其他比较 lowering，本层允许生成其他 dialect 的 compare op。

### Return

- `Return` 节点必须生成 `func.return`。
- `func.return` 的操作数来自当前返回表达式对应的 SSA value。

## 目标 Op 约束

- DSL 中的表达式必须在生成后的 MLIR IR / 文本中映射为语义对应的目标 op。
- 当前实现中，逐元素张量运算至少支持以下 `nn` op：
  - `nn.add`
  - `nn.sub`
  - `nn.mul`
  - `nn.truediv`
  - `nn.eq`
  - `nn.ne`
  - `nn.lt`
  - `nn.le`
  - `nn.gt`
  - `nn.ge`
- 这些 `nn` op 的 operand/result 类型必须与 [`spec/dialect/nn.md`](../../spec/dialect/nn.md) 的 verifier 规则保持一致。
- 若后续表达式更适合 lowering 到其他 dialect，本层允许生成对应目标 dialect 的 op；但生成出的 op 必须与输入表达式语义一致，并满足该 dialect 自身的 verifier 约束。

## 生成流程

### `mlir_gen(fn)` 的逻辑语义

建议流程：

1. 读取 Python 函数对象
2. 构建或获取函数 AST
3. 通过 `ast visitor` 遍历函数中的所有节点
4. 根据不同 `expr` / `stmt` 生成对应的 MLIR op / SSA value
5. 组织得到 `func.func`
6. 将 `func.func` 挂入 `builtin.module`

预期行为：

- 生成结果中必须存在与输入函数同名的 `func.func`
- 函数体中的 op 必须与源码中的表达式内容对应
- 中间表达式必须通过 SSA value 串联

## [immutable]示例

DSL 输入示例：

```python
from python.symbol_variable.memory import Memory
from python.symbol_variable.type import NumericType

A = Memory(["N", 32], NumericType.Float32, stride=["C", 1])
B = Memory(["N", 32], NumericType.Float32, stride=["C", 1])

def func_B(A, B):
    C = A + B
    return C
```

期望的结构化文本语义示例：

```mlir
builtin.module {
  func.func @func_B(%arg0: !nn.memory<[N, 32], [C, 1], f32, #nn.space<global>>, %arg1: !nn.memory<[N, 32], [C, 1], f32, #nn.space<global>>) -> !nn.memory<[N, 32], [C, 1], f32, #nn.space<global>> {
    %0 = "nn.add"(%arg0, %arg1) {space = #nn.space<global>} : (!nn.memory<[N, 32], [C, 1], f32, #nn.space<global>>, !nn.memory<[N, 32], [C, 1], f32, #nn.space<global>>) -> !nn.memory<[N, 32], [C, 1], f32, #nn.space<global>>
    func.return %0 : !nn.memory<[N, 32], [C, 1], f32, #nn.space<global>>
  }
}
```

说明：

- 这里强调的是“函数 -> `func.func` -> op / value”的结构与约束，不要求文本细节必须和当前 printer 的空格、换行完全一致。
- 示例中使用 `nn.add` 只是因为这是当前已有实现，不表示 `mlir_gen` 只能输出 `nn` dialect。
- 具体文本细节以当前 printer 输出为准，但结构必须满足本 spec。

## 错误规则

- AST 生成失败：向上抛出 `AstVisitorError`。
- visitor 无法识别某个节点：必须给出可定位的诊断，而不是 silently 跳过。
- Lowering 失败：由 `visit_to_nn_ir` 转换为 `AstVisitorError` 并保留诊断信息。
- 输入不是可调用对象也不是可打印 module：由实现抛出对应类型错误。
- 打印阶段若 IR 本身非法，错误应由前序 verifier 或 printer 触发，不允许 silently 修正。

## 测试

- 主要测试文件：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
- 关联方言测试：[`test/dialect/test_nn_dialect.py`](../../test/dialect/test_nn_dialect.py)
- 执行命令：`pytest -q test/dsl/test_ast_visitor.py`

### 测试目标

- 验证函数能够被转换为对应的 `func.func`。
- 验证函数体中的表达式会生成语义对应的目标 op 与 SSA value 链路。
- 验证 `visit_to_nn_ir` 能生成 `builtin.module`。
- 验证生成的 module 中包含 `func.func` 和对应表达式语义的目标 op。
- 验证 `emit_mlir` 输出中包含 `func.func` 与对应目标 op 文本。
- 验证标量参数会进入 `func.func` 签名并降低为基础标量类型。
- 验证 AST / lowering 失败时可通过诊断信息回报。

### 测试清单

| 用例 ID | 测试点 | 说明 | 对应测试 |
| --- | --- | --- | --- |
| TC-MLIR-001 | AST 到 `func.func` 入口 | `visit_to_nn_ir` 返回 `builtin.module`，且内部包含 `func.func` 与当前表达式对应的 op | `test_visit_to_nn_ir_builds_module` |
| TC-MLIR-002 | MLIR 文本输出 | `emit_mlir` 输出包含 `func.func` 与当前表达式对应的 op 文本 | `test_emit_mlir_output` |
| TC-MLIR-003 | 标量参数签名 lowering | 标量参数进入 `func.func` 签名并降低为 `i32` | `test_scalar_arg_lowering_in_signature` |
| TC-MLIR-004 | 注解入口兼容 | `globals/builtins` 可参与 AST 与 IR 入口构造 | `test_globals_and_builtins_annotation_entry` |
| TC-MLIR-005 | AST 诊断传播 | 未知名称等错误能够通过 visitor 诊断回报 | `test_unknown_name_reports_diagnostics` |

### 与方言测试的关系

- 本文件关注“生成出来的文本是否符合 MLIR 风格结构，以及函数内容是否被正确生成成 op/value”。
- `!nn.memory` 的 parse/print、`space` mismatch、compare result type 等方言级约束，由 [`test/dialect/test_nn_dialect.py`](../../test/dialect/test_nn_dialect.py) 覆盖。
- 因此，本文件不重复定义 `nn dialect` verifier 细节，而是要求 `emit_mlir` 生成的文本必须能满足当前目标 dialect 的 verifier 规则。

## 测试标准

- `pytest -q test/dsl/test_ast_visitor.py` 返回码必须为 `0`。
- 输出文本必须至少能稳定包含 `func.func`、`func.return` 和与源码表达式对应的目标 op。
- 新增 DSL 表达式类型、参数类型或返回形式时，必须同步更新本文件示例与测试清单。

## 兼容性

- 本 spec 绑定当前项目的 `emit_mlir` 入口，而不是抽象的外部生成器。
- 若未来把文本生成逻辑迁移到独立模块，例如 `python/dsl/mlir_gen.py`，需保持本文件中定义的输入输出契约不变。
- 若 `nn.memory` 的文本表示发生变化，需同步更新 [`spec/dialect/nn.md`](../../spec/dialect/nn.md) 与本文件中的示例和测试清单。
- 若后续引入新的目标 dialect，本文件应补充“表达式 -> 目标 op”的映射规则，而不是把所有生成语义都写死到 `nn` 上。
