# mlir_gen.md

## 功能简介

- 综合 AST 解析、AST 遍历与节点发射规则，将 Python 函数转换为 MLIR `func.func` op。
- 统一约束函数签名、参数与返回值的生成规则。
- 不生成 module，不负责文本打印。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`朽木露琪亚`
- `spec`：[`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
- `功能实现`：[`python/dsl/ast_visitor.py`](../../python/dsl/ast_visitor.py)
- `test`：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
- [immutable]`功能实现`：[`python/dsl/ast_visitor.py`](../../python/dsl/mlir_gen.py)

## 依赖

- AST 节点与解析入口：[`spec/dsl/ast.md`](../../spec/dsl/ast.md)
- AST 遍历访问器：[`spec/dsl/ast_visitor.md`](../../spec/dsl/ast_visitor.md)
- 节点发射规则：[`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)

## 目标

- 以统一入口生成 `func.func` op。
- 保证函数签名、参数顺序与返回类型与 AST 一致。
- 为上层打印或封装提供稳定的 func op 结果。

## 限制与边界

- 不生成 `builtin.module`。
- 不负责 MLIR 文本打印或后端代码生成。
- 不定义节点级发射细节，节点发射规则由 `emit_mlir` 约束。
- 不做优化或自动修复非法 IR。

## 公开接口

### `build_func_op(fn, globals=None, builtins=None, config=None)`

功能说明：

- 解析 Python 函数并生成 `func.func` op。
- 内部依次调用 `parse_function(...)`、`AstVisitor` 与 `emit_mlir`。

参数说明：

- `fn` (`callable`)：受限 Python 函数。
- `globals` (`dict|None`)：注解解析上下文（可选）。
- `builtins` (`dict|None`)：注解解析上下文（可选）。
- `config` (`dict|None`)：行为配置（可选）。

使用示例：

```python
func_op = build_func_op(add)
```

注意事项：

- 解析失败或发射失败必须抛出可定位的错误。

返回与限制：

- 返回 `func.func` op。
- 不返回 module。

### `build_func_op_from_ast(func_ast, config=None)`

功能说明：

- 基于已构建的 `FunctionAST` 生成 `func.func` op。
- 不重复解析 Python 源码。

参数说明：

- `func_ast` (`FunctionAST`)：函数 AST。
- `config` (`dict|None`)：行为配置（可选）。

使用示例：

```python
func_ast = parse_function(add)
func_op = build_func_op_from_ast(func_ast)
```

注意事项：

- 输入 AST 必须满足 `ast.md` 的结构约束。

返回与限制：

- 返回 `func.func` op。

## 额外补充

- 若需要 module 封装，由上层调用方完成。
- 该文件约束的输出为 `func.func`；示例中的 module 结构仅作语义示意。


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

## 测试

- 测试文件：[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
- 执行命令：`pytest -q test/dsl/test_ast_visitor.py`
- 测试目标：
  - 验证 `build_func_op(...)` 生成 `func.func`。
  - 验证函数签名与返回值类型与 AST 一致。
- 功能与用例清单：
  - MGEN-001：`build_func_op(...)` 返回 `func.func`。
  - MGEN-002：参数顺序与 AST 一致。
  - MGEN-003：返回值类型与 AST 对齐。
