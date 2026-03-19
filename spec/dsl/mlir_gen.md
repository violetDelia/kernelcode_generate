# mlir_gen.md

## 功能简介

- 定义 DSL 入口的 MLIR 文本生成规范（mlir_gen 概念层）。
- 公开入口为 `emit_mlir`：输入 Python 函数或 `nn dialect` 的模块对象，输出 MLIR 风格文本。
- 本文只约束文本生成的输入/输出与结构性要求，不替代 AST 构建与 IR 生成规则。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`咯咯咯`
- `spec`：[`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
- `关联 AST`：[`spec/dsl/ast.md`](../../spec/dsl/ast.md)
- `关联 ast_visitor`：[`spec/dsl/ast_visitor.md`](../../spec/dsl/ast_visitor.md)
- `关联 IR 生成`：[`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
- `关联 Dialect`：[`spec/dialect/nn.md`](../../spec/dialect/nn.md)
- `test`：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
- `功能实现（当前入口）`：[`python/dsl/ast_visitor.py`](../../python/dsl/ast_visitor.py)
- [immutable]`功能实现`：[`python/dsl/ast_visitor.py`](../../python/dsl/mlir_gen.py)

## 依赖

- AST 结构：[`spec/dsl/ast.md`](../../spec/dsl/ast.md)
- AST 入口与诊断：[`spec/dsl/ast_visitor.md`](../../spec/dsl/ast_visitor.md)
- IR 生成规则：[`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
- 目标方言：[`spec/dialect/nn.md`](../../spec/dialect/nn.md)

## 目标

- 为 DSL 入口提供稳定的 MLIR 文本输出能力。
- 明确 `emit_mlir` 的输入范围、输出结构与错误语义。
- 保证输出文本与当前 `nn dialect` IR 结构一致，保持表达式顺序与 SSA 依赖关系。

## 限制与边界

- 不负责 Python AST 解析与 AST 构建，入口规则由 `ast_visitor` 约束。
- 不定义 AST 到 IR 的 lowering 规则，行为以 `spec/dsl/emit_mlir.md` 为准。
- 不做优化、融合、bufferization 或后端生成。
- 不替代 `nn dialect` 的 verifier 规则；不负责自动修正非法 IR。

## 公开接口

### `emit_mlir(value, globals=None, builtins=None, config=None) -> str`

功能说明：

- 当 `value` 为可调用对象时：先走 `visit_to_nn_ir` 生成 `nn dialect` 模块，再打印为 MLIR 文本。
- 当 `value` 为模块对象时：直接打印文本。

参数说明：

- `value`：Python 函数或 `nn dialect` 模块对象。
- `globals/builtins`：传递给 `visit_function` 的注解解析上下文。
- `config`：传递给 `visit_function/visit_to_nn_ir` 的配置参数。

返回与限制：

- 返回非空字符串，包含 `func.func` 与对应 `nn.*` op 的文本。
- 输出格式由 `xdsl.printer.Printer` 决定，文本换行/空格不作为稳定语义。

使用示例：

```python
text = emit_mlir(add)
```

错误与约束：

- 当 `value` 为函数且 AST/IR 生成失败时，抛 `AstVisitorError` 并携带诊断信息。
- 当 `value` 不是函数也不是模块对象时，由实现抛出类型相关错误。

## 输出结构约束

- 输出必须包含 `func.func` 与 `func.return`，且函数名与输入函数名一致。
- 表达式对应的 `nn.*` op 必须按源码依赖顺序出现在函数体中。
- 标量参数应在 `func.func` 签名中体现为基础标量类型（当前为 `i32`）。

## 测试

- 测试文件：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
- 执行命令：`pytest -q test/dsl/test_ast_visitor.py`

### 测试映射

| 用例 ID | 测试点 | 对应测试 |
| --- | --- | --- |
| MLIR-001 | `emit_mlir` 输出包含 `func.func` 与 `nn` op 文本 | `test_emit_mlir_output` |

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
