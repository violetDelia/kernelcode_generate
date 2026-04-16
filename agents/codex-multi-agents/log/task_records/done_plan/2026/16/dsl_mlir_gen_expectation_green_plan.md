# dsl_mlir_gen_expectation_green_plan.md

## 文档信息

- 创建者：`守护最好的爱莉希雅`
- 最后一次更改：`大闸蟹`
- 目标 `spec`：
  - [`spec/dsl/ast.md`](../../spec/dsl/ast.md)
  - [`spec/dsl/ast_visitor.md`](../../spec/dsl/ast_visitor.md)
  - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
  - [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
  - [`spec/tools/mlir_gen_compare.md`](../../spec/tools/mlir_gen_compare.md)
- 目标 `API`：
  - `parse_function(fn) -> FunctionAST`
  - `AstVisitor.visit(node) -> object`
  - `build_func_op(fn, *runtime_args, globals=None, builtins=None) -> func.func`
  - `build_func_op_from_ast(func_ast, runtime_args=None, config=None) -> func.func`
  - `mlir_gen(fn, *runtime_args, globals=None, builtins=None, config=None) -> builtin.module`
  - `EmitContext(builder, symbols, types, config)`
  - `emit_mlir(node, ctx) -> Operation | SSAValue | None`
  - `mlir_gen_compare(fn, runtime_args, config, mlir_file) -> bool`
  - `mlir_gen_compare_text(fn, runtime_args, config, mlir_text) -> bool`
- 目标 `test`：
  - [`test/dsl/ast`](../../test/dsl/ast)
  - [`test/dsl/mlir_gen`](../../test/dsl/mlir_gen)
  - [`test/dsl/mlir_gen/emit`](../../test/dsl/mlir_gen/emit)
  - [`test/tools/test_mlir_gen_compare.py`](../../test/tools/test_mlir_gen_compare.py)
- 目标 `验收资产`：
  - [`expectation/dsl/mlir_gen`](../../expectation/dsl/mlir_gen)
- 目标 `功能实现`：
  - [`kernel_gen/dsl/ast`](../../kernel_gen/dsl/ast)
  - [`kernel_gen/dsl/mlir_gen`](../../kernel_gen/dsl/mlir_gen)
  - [`kernel_gen/dsl/mlir_gen/emit`](../../kernel_gen/dsl/mlir_gen/emit)
  - [`kernel_gen/tools/mlir_gen_compare.py`](../../kernel_gen/tools/mlir_gen_compare.py)

## 任务清单

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `S1` | `无` | `wt-20260413-dsl-mlir-gen-s1` | `20260413-dsl-mlir-gen-s1.md` |
| `S2` | `S1` | `wt-20260413-dsl-mlir-gen-s2` | `20260413-dsl-mlir-gen-s2.md` |
| `S3` | `S2` | `wt-20260413-dsl-mlir-gen-s3` | `20260413-dsl-mlir-gen-s3.md` |
| `S4` | `S3` | `wt-20260413-dsl-mlir-gen-s4` | `20260413-dsl-mlir-gen-s4.md` |
| `S5` | `S4` | `wt-20260413-dsl-mlir-gen-s5` | `20260413-dsl-mlir-gen-s5.md` |
| `S6` | `S5` | `wt-20260413-dsl-mlir-gen-s6` | `20260413-dsl-mlir-gen-s6.md` |
| `S7` | `S6` | `wt-20260413-dsl-mlir-gen-s7` | `20260413-dsl-mlir-gen-s7.md` |
| `S8` | `S7` | `wt-20260415-dsl-mlir-gen-final-fix` | `20260415-dsl-mlir-gen-final-fix.md` |

## 评审摘要

- 评审结论：`通过（已采纳 1 处文字口径修订）`
- 评审人：`守护最好的爱莉希雅`、`大闸蟹`
- 结论摘要：`任务划分、三层目录设计、后续维护性与文本清晰度均通过；已把各阶段“任务新建建议”统一为默认按 spec/build/review/merge 路线推进，本阶段只定义收口范围。`

## 当前终验复核（2026-04-15）

- 复核人：`大闸蟹`
- 当前结论：`不通过`
- 复核依据：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen` -> `exit=1`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.arch` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.symbol` -> `exit=1`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.dma` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn` -> `exit=1`
  - `pytest -q test/dsl/ast test/dsl/mlir_gen test/dsl/mlir_gen/emit test/tools/test_mlir_gen_compare.py` -> `57 passed`
- 最小阻断项：
  - `expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py` 仍失败：`CASE-1` 实际报 `AstVisitorError: nn.add requires at least one nn.memory operand`，说明 `symbol.add` 场景仍未按计划正文收口。
  - `expectation/dsl/mlir_gen/dialect/nn/__main__.py` 缺失，导致 `python -m expectation.dsl.mlir_gen.dialect.nn` 不能直接执行。
  - 根目录入口 `expectation/dsl/mlir_gen/__main__.py` 仍汇总失败，当前至少包含 `top.import_bound_helper`、`top.return_type_from_body_not_signature`、`dialect.nn.conv`、`dialect.nn.fc`、`dialect.nn.img2col1d`、`dialect.nn.img2col2d`、`dialect.nn.matmul`、`dialect.nn.reduce`、`dialect.nn.softmax`、`dialect.symbol.element_binary`、`dialect.symbol.for_loop` 未收口。

## 当前主仓终验（2026-04-16 17:00 +0800）

- 终验人：`守护最好的爱莉希雅`
- 当前结论：`不通过`
- 归档结论：`不可进入归档链`
- 主仓实跑：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen` -> `exit=1`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.arch` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.symbol` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.dma` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn` -> `exit=1`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/ast test/dsl/mlir_gen test/dsl/mlir_gen/emit test/tools/test_mlir_gen_compare.py` -> `1 failed, 57 passed`
- 最小阻断项：
  - `expectation.dsl.mlir_gen.dialect.nn` 目录入口仍未收口，当前仍有 `11` 组 `nn family` expectation 失败；失败形态集中为 `Unsupported annotation` 与 `Unsupported call expression`，涉及 `broadcast`、`broadcast_to`、`conv`、`fc`、`img2col1d`、`img2col2d`、`matmul`、`reduce_*`、`softmax`。
  - 根入口 `expectation.dsl.mlir_gen` 仍因 `dialect.nn` 汇总失败而退出，说明目录级合同未闭环。
  - `pytest` 总验收仍有首个业务失败：[`test/dsl/ast/test_parser.py`](../../test/dsl/ast/test_parser.py) 的 `test_parse_function_helper_call` 仍报 `AstVisitorError: Unsupported call expression`，`imported helper call parser` 回归尚未真正进入当前主仓。
- 唯一继续项：
  - `T-20260416-16fcb9bf`
  - 任务目标：`修复：收口 nn family 目录级 expectation 失败与 helper call parser 回归`

## 当前主仓终验（2026-04-16 17:30 +0800）

- 终验人：`守护最好的爱莉希雅`
- 当前结论：`不通过`
- 归档结论：`不可进入归档链`
- 主仓实跑：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen` -> `exit=1`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.arch` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.symbol` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.dma` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn` -> `exit=1`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/ast test/dsl/mlir_gen test/dsl/mlir_gen/emit test/tools/test_mlir_gen_compare.py` -> `1 failed, 57 passed`
- 最小阻断项：
  - `expectation.dsl.mlir_gen.dialect.nn` 目录入口仍未收口，当前仍有 `11` 组 `nn family` expectation 失败；失败形态仍集中为 `Unsupported annotation` 与 `Unsupported call expression`。
  - 根入口 `expectation.dsl.mlir_gen` 仍因 `dialect.nn` 汇总失败而退出，目录级合同未闭环。
  - `pytest` 总验收的首个业务失败仍是 [`test/dsl/ast/test_parser.py`](../../test/dsl/ast/test_parser.py) 的 `test_parse_function_helper_call`，当前仍报 `AstVisitorError: Unsupported call expression`，说明 imported helper call parser 回归尚未真正进入根目录主仓。
  - [`TODO.md`](../../TODO.md) 当前已不是 `15 / 15 / 0 / 完成待检查`，而是 `16 / 15 / 1 / 进行中`；这与当前主仓实跑结果一致，说明本计划尚未达到归档状态。
- 唯一继续项：
  - 保留 [`T-20260416-d7591ac6`](../../TODO.md) 作为当前唯一修复任务。
  - 已完成的 [`T-20260416-16fcb9bf`](../../DONE.md) 不再继续复用；当前不得创建归档任务，也不得执行 `-done-plan`。

## 计划目标

- 让 [`expectation/dsl/mlir_gen`](../../expectation/dsl/mlir_gen) 下全部可执行 case 最终都能运行通过，并成为 DSL 到 MLIR 的唯一目录级合同。
- 把前端实现收口为三层：
  - `kernel_gen/dsl/ast/`：AST 节点、解析、visitor；
  - `kernel_gen/dsl/mlir_gen/`：函数入口、module 组装、公开生成入口；
  - `kernel_gen/dsl/mlir_gen/emit/`：节点到 MLIR op 的发射逻辑。
- 把绑定规则统一为“`runtime_args + AST` 决定输入与返回类型”，不再保留另一套独立的函数签名推导路径。
- 把 `expectation/dsl/mlir_gen` 的写法统一为：
  - 展示函数不写签名；
  - 输入固定写在 `CASE_N_RUNTIME_ARGS`；
  - 完整 `builtin.module` 固定通过 `mlir_gen_compare_text(...)` 比较；
  - 若某个 helper 支持静态 / 动态 / `symbol.const` / `symbol` 标量 / 失败例子，则 expectation 直接把这些写全。

## 当前基线

- 当前主要入口仍在：
  - [`kernel_gen/dsl/ast.py`](../../kernel_gen/dsl/ast.py)
  - [`kernel_gen/dsl/ast_nodes.py`](../../kernel_gen/dsl/ast_nodes.py)
  - [`kernel_gen/dsl/ast_parser.py`](../../kernel_gen/dsl/ast_parser.py)
  - [`kernel_gen/dsl/ast_visitor.py`](../../kernel_gen/dsl/ast_visitor.py)
  - [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py)
  - [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py)
- 当前 `expectation/dsl/mlir_gen` 共有 `85` 个 Python 文件；语法检查 `85/85` 通过；可执行脚本 `75` 个。
- 当前运行现状：
  - `dialect/arch = 6/8`
  - `dialect/dma = 0/11`
  - `dialect/nn = 0/28`
  - `dialect/symbol = 0/15`
  - 顶层脚本 `1/3`
- 当前主要问题：
  - 前端仍大量报 `AstVisitorError: Missing annotation`，与“无签名函数 + runtime_args 驱动”的目标不一致；
  - `emit_mlir.py` 与 `mlir_gen.py` 体量过大，职责混杂；
  - `expectation/dsl/mlir_gen` 的目录入口和子目录入口不完整；
  - `pytest` 仍集中在少量大文件里，无法直接约束文件职责。

## 方案比较与选型

- 不采用“继续保留 `ast.py / ast_parser.py / ast_visitor.py / mlir_gen.py / emit_mlir.py` 五个顶层大文件”的方案。
  - 原因：职责继续混在一起，执行人无法从文件名判断该把解析、绑定、发射、module 组装放到哪里。
- 不采用“`emit` 第一层按 `nn / dma / arch / symbol` 拆目录”的方案。
  - 原因：`emit` 的第一职责是 AST 节点发射，不是 dialect 分类；如果第一层先按 dialect 拆，`AssignAST / ReturnAST / ForAST / CallAST` 的公共逻辑仍会回流到一个大文件。
- 采用“三层目录 + 二层 call family”的方案：
  - `kernel_gen/dsl/ast/` 只负责 AST；
  - `kernel_gen/dsl/mlir_gen/` 只负责函数级与 module 级入口；
  - `kernel_gen/dsl/mlir_gen/emit/` 只负责节点发射；
  - `emit` 内部第一层按职责域拆，`CallAST` 再按 `nn / dma / arch / symbol` 分流。

## 公开 API 设计

- `parse_function(fn) -> FunctionAST`
  - 公开层级：AST facade。
  - 参数：`fn` 为 Python 函数对象。
  - 返回：`FunctionAST`。
  - 最小示例：

```python
def add_kernel(x, y):
    return x + y

func_ast = parse_function(add_kernel)
```

- `AstVisitor.visit(node) -> object`
  - 公开层级：AST visitor。
  - 参数：任一 AST 节点。
  - 返回：节点对应 visit 方法的结果；未注册节点抛 `AstVisitorError`。
  - 最小示例：

```python
visitor = AstVisitor()
value = visitor.visit(func_ast.body[0])
```

- `build_func_op(fn, *runtime_args, globals=None, builtins=None) -> func.func`
  - 公开层级：函数级 MLIR 构造。
  - 参数顺序固定为：`fn`、`runtime_args`、`globals`、`builtins`。
  - 返回：单个 `func.func`。
  - 最小示例：

```python
func_op = build_func_op(
    exp_kernel,
    Memory([2, 2], NumericType.Float32, space=MemorySpace.GM),
)
```

- `build_func_op_from_ast(func_ast, runtime_args=None, config=None) -> func.func`
  - 公开层级：基于 AST 的函数级构造。
  - 参数顺序固定为：`func_ast`、`runtime_args`、`config`。
  - 返回：单个 `func.func`。

- `mlir_gen(fn, *runtime_args, globals=None, builtins=None, config=None) -> builtin.module`
  - 公开层级：完整 module 构造。
  - 参数顺序固定为：`fn`、`runtime_args`、`globals`、`builtins`、`config`。
  - 返回：完整 `builtin.module`。
  - 说明：输入绑定、返回类型推导、callee 收集都来自 `runtime_args + AST`，不再独立依赖函数签名。

- `EmitContext(builder, symbols, types, config)`
  - 公开层级：emit 上下文。
  - 字段职责：
    - `builder`：当前 IR builder；
    - `symbols`：symbol 与 SSAValue 绑定；
    - `types`：dtype / memory type / result type 缓存；
    - `config`：target / printer / helper 配置。

- `emit_mlir(node, ctx) -> Operation | SSAValue | None`
  - 公开层级：节点发射入口。
  - 说明：只负责单个 AST 节点到 MLIR op / SSAValue，不负责 module 组装。

- `mlir_gen_compare(fn, runtime_args, config, mlir_file) -> bool`
- `mlir_gen_compare_text(fn, runtime_args, config, mlir_text) -> bool`
  - 公开层级：黑盒比较工具。
  - 返回：`True / False`。
  - 说明：以完整 `builtin.module` 为比较对象。

## 文件边界与 `spec` 对应

### 一、AST 目录

- [`kernel_gen/dsl/ast/__init__.py`](../../kernel_gen/dsl/ast/__init__.py)
  - 对应 [`spec/dsl/ast.md`](../../spec/dsl/ast.md)
  - 只做 AST facade 导出。
- [`kernel_gen/dsl/ast/nodes.py`](../../kernel_gen/dsl/ast/nodes.py)
  - 对应 [`spec/dsl/ast.md`](../../spec/dsl/ast.md)
  - 只放 AST dataclass 与节点定义。
- [`kernel_gen/dsl/ast/parser.py`](../../kernel_gen/dsl/ast/parser.py)
  - 对应 [`spec/dsl/ast.md`](../../spec/dsl/ast.md)
  - 只放 Python 函数到 AST 的解析。
- [`kernel_gen/dsl/ast/visitor.py`](../../kernel_gen/dsl/ast/visitor.py)
  - 对应 [`spec/dsl/ast_visitor.md`](../../spec/dsl/ast_visitor.md)
  - 只放 visitor 分发与错误定义。

### 二、`mlir_gen` 外层目录

- [`kernel_gen/dsl/mlir_gen/__init__.py`](../../kernel_gen/dsl/mlir_gen/__init__.py)
  - 对应 [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
  - 只导出 `build_func_op`、`build_func_op_from_ast`、`mlir_gen`。
- [`kernel_gen/dsl/mlir_gen/function_builder.py`](../../kernel_gen/dsl/mlir_gen/function_builder.py)
  - 对应 [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
  - 只负责 `func.func` 壳子、参数绑定结果写回与返回语句组装。
- [`kernel_gen/dsl/mlir_gen/parse_env.py`](../../kernel_gen/dsl/mlir_gen/parse_env.py)
  - 对应 [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
  - 只负责 `runtime_args / globals / builtins` 的解析环境。
- [`kernel_gen/dsl/mlir_gen/signature.py`](../../kernel_gen/dsl/mlir_gen/signature.py)
  - 对应 [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
  - 只负责函数级输入 / 返回类型校验与规范化，不直接发射具体 op。
- [`kernel_gen/dsl/mlir_gen/module_builder.py`](../../kernel_gen/dsl/mlir_gen/module_builder.py)
  - 对应 [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
  - 只负责根函数、callee 闭包与 `builtin.module` 组装。

### 三、`emit` 目录

- [`kernel_gen/dsl/mlir_gen/emit/__init__.py`](../../kernel_gen/dsl/mlir_gen/emit/__init__.py)
  - 对应 [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
  - 只导出 `EmitContext` 与 `emit_mlir`。
- [`kernel_gen/dsl/mlir_gen/emit/context.py`](../../kernel_gen/dsl/mlir_gen/emit/context.py)
  - 对应 [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
  - 只放 `EmitContext` 与 emit 侧配置检查。
- [`kernel_gen/dsl/mlir_gen/emit/dispatch.py`](../../kernel_gen/dsl/mlir_gen/emit/dispatch.py)
  - 对应 [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
  - 只做 AST 节点总分发。
- [`kernel_gen/dsl/mlir_gen/emit/control_flow.py`](../../kernel_gen/dsl/mlir_gen/emit/control_flow.py)
  - 对应 [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
  - 只处理 `AssignAST / ReturnAST / ForAST`。
- [`kernel_gen/dsl/mlir_gen/emit/call_dispatch.py`](../../kernel_gen/dsl/mlir_gen/emit/call_dispatch.py)
  - 对应 [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
  - 只做 `CallAST` 到各 family 的路由。
- [`kernel_gen/dsl/mlir_gen/emit/call_nn.py`](../../kernel_gen/dsl/mlir_gen/emit/call_nn.py)
  - 对应 [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)、[`spec/dialect/nn.md`](../../spec/dialect/nn.md)、[`spec/operation/nn.md`](../../spec/operation/nn.md)
  - 只处理 `nn.*` 调用。
- [`kernel_gen/dsl/mlir_gen/emit/call_dma.py`](../../kernel_gen/dsl/mlir_gen/emit/call_dma.py)
  - 对应 [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)、[`spec/dialect/dma.md`](../../spec/dialect/dma.md)、[`spec/operation/dma.md`](../../spec/operation/dma.md)
  - 只处理 `dma.*` 调用。
- [`kernel_gen/dsl/mlir_gen/emit/call_arch.py`](../../kernel_gen/dsl/mlir_gen/emit/call_arch.py)
  - 对应 [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)、[`spec/dialect/arch.md`](../../spec/dialect/arch.md)
  - 只处理 `arch.*` 调用。
- [`kernel_gen/dsl/mlir_gen/emit/call_symbol.py`](../../kernel_gen/dsl/mlir_gen/emit/call_symbol.py)
  - 对应 [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)、[`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)
  - 只处理 `symbol.*` 调用。
- [`kernel_gen/dsl/mlir_gen/emit/value.py`](../../kernel_gen/dsl/mlir_gen/emit/value.py)
  - 对应 [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
  - 只放变量、常量、symbol 常量、索引值与 SSAValue 物化。
- [`kernel_gen/dsl/mlir_gen/emit/type_utils.py`](../../kernel_gen/dsl/mlir_gen/emit/type_utils.py)
  - 对应 [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
  - 只放 dtype、memory type、广播、结果类型推导。
- [`kernel_gen/dsl/mlir_gen/emit/shape_utils.py`](../../kernel_gen/dsl/mlir_gen/emit/shape_utils.py)
  - 对应 [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
  - 只放 shape、stride、layout、index helper。

### 四、顶层 facade

- [`kernel_gen/dsl/ast.py`](../../kernel_gen/dsl/ast.py)
- [`kernel_gen/dsl/ast_visitor.py`](../../kernel_gen/dsl/ast_visitor.py)
- [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py)
- [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py)
  - 这四个文件若保留，只做 facade / 转发，不再承载主要实现。

### 五、测试与验收资产

- [`test/dsl/ast`](../../test/dsl/ast)
  - 对应 [`spec/dsl/ast.md`](../../spec/dsl/ast.md)、[`spec/dsl/ast_visitor.md`](../../spec/dsl/ast_visitor.md)
  - 只测 AST 解析与 visitor 分发。
- [`test/dsl/mlir_gen`](../../test/dsl/mlir_gen)
  - 对应 [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
  - 只测函数级、module 级入口与绑定。
- [`test/dsl/mlir_gen/emit`](../../test/dsl/mlir_gen/emit)
  - 对应 [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
  - 只测 emit 共享逻辑与 family 发射。
- [`test/tools/test_mlir_gen_compare.py`](../../test/tools/test_mlir_gen_compare.py)
  - 对应 [`spec/tools/mlir_gen_compare.md`](../../spec/tools/mlir_gen_compare.md)
  - 只测 `builtin.module` 比较工具。
- [`expectation/dsl/mlir_gen`](../../expectation/dsl/mlir_gen)
  - 负责 DSL 到 MLIR 的黑盒合同；
  - 每个 case 必须同时展示函数正文、`runtime_args` 和完整预期 IR。

## 验收设计

- 黑盒合同以 [`expectation/dsl/mlir_gen`](../../expectation/dsl/mlir_gen) 为准。
  - 每个 case 都固定比较完整 `builtin.module`；
  - 若某类 helper 支持静态 / 动态 / `symbol.const` / `symbol` 标量 / 失败例子，则 expectation 直接写全。
- 目录入口必须可运行。
  - 根目录：`python -m expectation.dsl.mlir_gen`
  - 一级目录：`arch / symbol / dma / nn`
  - 需要子目录入口的 family：其 `__main__.py` 也必须可运行。
- `pytest` 只承接职责域测试，不替代 expectation。
  - `test/dsl/ast` 只收 AST；
  - `test/dsl/mlir_gen` 只收函数级与 module 级入口；
  - `test/dsl/mlir_gen/emit` 只收 emit；
  - `test/tools/test_mlir_gen_compare.py` 只收 compare。
- 最终以三类结果共同判定：
  - expectation 全目录通过；
  - `pytest` 三组目录通过；
  - 顶层旧文件只剩 facade，不再包含主要实现。

## expectation 统一模板

- 所有展示函数固定不写签名。
- `runtime_args` 固定放在 `CASE_N_RUNTIME_ARGS`。
- 如果该 helper 支持以下场景，expectation 默认都要给出：
  - 静态；
  - 动态；
  - `symbol.const`；
  - `symbol` 标量；
  - 失败例子。
- 统一比较方式：

```python
assert mlir_gen_compare_text(case_1_kernel, CASE_1_RUNTIME_ARGS, None, CASE_1_IR)
```

- 统一展示模板：

```python
CASE_1_DESC = "静态正向：展示无签名函数 + runtime_args 绑定。"
CASE_1_RUNTIME_ARGS = (...)
CASE_1_IR = """builtin.module {
  ...
}"""

def case_1_kernel(x):
    return x
```

## 完成态定义

- [`expectation/dsl/mlir_gen`](../../expectation/dsl/mlir_gen) 下全部可执行 case 运行通过。
- `python -m expectation.dsl.mlir_gen`、各一级目录入口、各子目录入口都可直接运行。
- `mlir_gen`、`emit_mlir`、`ast` 三组实现按目录拆开，顶层旧文件仅保留 facade。
- `test/dsl/ast/`、`test/dsl/mlir_gen/`、`test/dsl/mlir_gen/emit/`、`test/tools/test_mlir_gen_compare.py` 同时通过。
- DSL 到 MLIR 的合同以 expectation 目录为准；实现输出与 expectation 不一致时，优先修实现。

## 验收命令

- `PYTHONPATH=. python -m expectation.dsl.mlir_gen`
- `PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.arch`
- `PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.symbol`
- `PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.dma`
- `PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn`
- `pytest -q test/dsl/ast test/dsl/mlir_gen test/dsl/mlir_gen/emit test/tools/test_mlir_gen_compare.py`

## 阶段拆分

### S1：`ast` 目录与解析 / visitor 合同

#### 阶段目标

- 只处理 `kernel_gen/dsl/ast/` 与对应 `spec / test`。
- 不进入 `mlir_gen` 的函数级组装。
- 不进入 `emit` 的具体 op 发射。

#### 可改文件

- `spec/dsl/ast.md`
- `spec/dsl/ast_visitor.md`
- `kernel_gen/dsl/ast/`
- `kernel_gen/dsl/ast.py`
- `kernel_gen/dsl/ast_visitor.py`
- `test/dsl/ast/`

#### 目标 `spec` / API

- `parse_function(fn) -> FunctionAST`
- `AstVisitor.visit(node) -> object`
- `AstVisitorError`

#### 文件职责收口

- `kernel_gen/dsl/ast/nodes.py`
  - 只放 `FunctionAST / TensorAST / ScalarArgAST / ForAST / ConstAST / CallAST` 这类节点定义；
  - 不放解析逻辑，不放 visitor 分发。
- `kernel_gen/dsl/ast/parser.py`
  - 只负责 Python AST 到 DSL AST；
  - 不放 `emit_mlir`、不放 MLIR type 推导。
- `kernel_gen/dsl/ast/visitor.py`
  - 只放 visitor 路由、默认报错、节点注册；
  - 不放节点 dataclass，不放 `func.func` 组装。

#### 预期示例代码

```python
def copy_kernel(x):
    y = x
    return y
```

```python
def loop_kernel(x):
    for i in range(0, 4, 1):
        x = x
    return x
```

```python
def invalid_step_kernel(x):
    for i in range(0, 4, 0):
        x = x
    return x
```

#### 预期输出

```text
FunctionAST(
  name="copy_kernel",
  args=[TensorAST(name="x")],
  body=[
    VarAST(name="y", expr=VarAST(name="x")),
    ReturnAST(value=VarAST(name="y")),
  ],
)
```

```text
FunctionAST(
  name="loop_kernel",
  body=[
    ForAST(
      var_name="i",
      start=ConstAST(value=0),
      end=ConstAST(value=4),
      step=ConstAST(value=1),
      body=[VarAST(name="x", expr=VarAST(name="x"))],
    ),
    ReturnAST(value=VarAST(name="x")),
  ],
)
```

```text
AstParserError: for range step must not be zero
```

#### 预期示例说明

- `parse_function(...)` 能稳定产出 `FunctionAST / TensorAST / ForAST / ConstAST`；
- `AstVisitor.visit(...)` 对已注册节点能分发到对应 visit 方法；
- `ast.py`、`ast_visitor.py` 顶层文件只做导出，不再放主要实现。
- `for range(..., step=0)` 在 AST 解析阶段直接报错，不延后到 emit 阶段。

#### 预期输出细节

- `test/dsl/ast/test_parser.py` 覆盖：
  - 基础赋值；
  - `for` 循环；
  - 常量；
  - helper call 解析入口。
  - `step=0` 解析报错。
- `test/dsl/ast/test_visitor.py` 覆盖：
  - 已注册节点分发；
  - 未注册节点抛 `AstVisitorError`。

#### 目标验收资产

- `test/dsl/ast/test_parser.py`
- `test/dsl/ast/test_visitor.py`

#### 验收必过项目

- `pytest -q test/dsl/ast`

#### 任务新建建议

- `推进方式：按默认 spec/build/review/merge 路线推进，本阶段只定义收口范围。`
- `阶段目标：把 AST 节点、解析、visitor 收口到 kernel_gen/dsl/ast/，并补齐对应 spec 与测试。`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/15/20260413-dsl-mlir-gen-s1.md`

### S2：`mlir_gen` 外层入口与 compare 工具

#### 阶段目标

- 只处理 `mlir_gen` 的函数级入口、module 组装、compare 工具。
- 不进入 `emit` 的具体 family lowering。

#### 可改文件

- `spec/dsl/mlir_gen.md`
- `spec/tools/mlir_gen_compare.md`
- `kernel_gen/dsl/mlir_gen/__init__.py`
- `kernel_gen/dsl/mlir_gen/function_builder.py`
- `kernel_gen/dsl/mlir_gen/parse_env.py`
- `kernel_gen/dsl/mlir_gen/signature.py`
- `kernel_gen/dsl/mlir_gen/module_builder.py`
- `kernel_gen/tools/mlir_gen_compare.py`
- `test/dsl/mlir_gen/test_function_builder.py`
- `test/dsl/mlir_gen/test_parse_env.py`
- `test/dsl/mlir_gen/test_signature.py`
- `test/dsl/mlir_gen/test_module_builder.py`
- `test/tools/test_mlir_gen_compare.py`
- `expectation/dsl/mlir_gen/import_bound_helper.py`
- `expectation/dsl/mlir_gen/return_type_from_body_not_signature.py`
- `expectation/dsl/mlir_gen/use_global_value.py`

#### 目标 `spec` / API

- `build_func_op(...) -> func.func`
- `build_func_op_from_ast(...) -> func.func`
- `mlir_gen(...) -> builtin.module`
- `mlir_gen_compare(...) -> bool`
- `mlir_gen_compare_text(...) -> bool`

#### 文件职责收口

- `kernel_gen/dsl/mlir_gen/function_builder.py`
  - 只负责函数参数、返回值、函数体 builder 建立；
  - 不负责 helper callee 收集，不负责 compare。
- `kernel_gen/dsl/mlir_gen/parse_env.py`
  - 只负责 `runtime_args / globals / builtins` 绑定；
  - 不放 `func.func` 组装。
- `kernel_gen/dsl/mlir_gen/module_builder.py`
  - 只负责根函数与 callee 的 `builtin.module`；
  - 不直接发射 `nn / dma / arch / symbol` op。
- `kernel_gen/tools/mlir_gen_compare.py`
  - 只负责生成 module、规范化文本、比较结果；
  - 不反向承接 `mlir_gen` 主流程实现。

#### 预期示例代码

```python
CASE_1_RUNTIME_ARGS = (
    Memory([2, 2], NumericType.Float32, space=MemorySpace.GM),
)

def exp_kernel(x):
    return exp(x)
```

```python
CASE_2_RUNTIME_ARGS = (
    Memory([SymbolDim("M"), 4], NumericType.Float32, space=MemorySpace.GM),
)

def helper_bound_kernel(x):
    return reshape_like_helper(x)
```

```python
assert mlir_gen_compare_text(exp_kernel, CASE_1_RUNTIME_ARGS, None, CASE_1_IR) is True
```

#### 预期输出

```text
builtin.module {
  func.func @exp_kernel(%0 : !nn.memory<[2, 2], [2, 1], f32, #nn.space<global>>)
      -> !nn.memory<[2, 2], [2, 1], f32, #nn.space<global>> {
    %1 = "nn.exp"(%0) : (...) -> !nn.memory<[2, 2], [2, 1], f32, #nn.space<global>>
    func.return %1 : !nn.memory<[2, 2], [2, 1], f32, #nn.space<global>>
  }
}
```

```text
builtin.module {
  func.func @helper_bound_kernel(%0 : !nn.memory<[M, 4], [4, 1], f32, #nn.space<global>>)
      -> !nn.memory<[M, 4], [4, 1], f32, #nn.space<global>>
  func.func @reshape_like_helper(%0 : !nn.memory<[M, 4], [4, 1], f32, #nn.space<global>>)
      -> !nn.memory<[M, 4], [4, 1], f32, #nn.space<global>>
}
```

#### 预期输出细节

- 无签名函数仅靠 `runtime_args` 完成输入绑定；
- `return` 类型来自 AST + runtime 绑定，不退回函数签名；
- `mlir_gen_compare_text(...)` 比较完整 `builtin.module`；
- root helper / import-bound helper 形成 callee 时，callee 会出现在 `builtin.module` 中。

#### 目标验收资产

- `expectation/dsl/mlir_gen/import_bound_helper.py`
- `expectation/dsl/mlir_gen/return_type_from_body_not_signature.py`
- `expectation/dsl/mlir_gen/use_global_value.py`

#### 验收必过项目

- `PYTHONPATH=. python expectation/dsl/mlir_gen/import_bound_helper.py`
- `PYTHONPATH=. python expectation/dsl/mlir_gen/return_type_from_body_not_signature.py`
- `PYTHONPATH=. python expectation/dsl/mlir_gen/use_global_value.py`
- `pytest -q test/dsl/mlir_gen/test_function_builder.py test/dsl/mlir_gen/test_parse_env.py test/dsl/mlir_gen/test_signature.py test/dsl/mlir_gen/test_module_builder.py test/tools/test_mlir_gen_compare.py`

#### 任务新建建议

- `推进方式：按默认 spec/build/review/merge 路线推进，本阶段只定义收口范围。`
- `阶段目标：收口 mlir_gen 外层公开入口、module 组装和完整 module 比较工具。`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/15/20260413-dsl-mlir-gen-s2.md`

### S3：`emit` 共享核心

#### 阶段目标

- 只处理 `EmitContext`、总分发、结构节点、value / type / shape 公共逻辑。
- 不进入 `nn / dma / arch / symbol` 的 family 细节。

#### 可改文件

- `spec/dsl/emit_mlir.md`
- `kernel_gen/dsl/mlir_gen/emit/__init__.py`
- `kernel_gen/dsl/mlir_gen/emit/context.py`
- `kernel_gen/dsl/mlir_gen/emit/dispatch.py`
- `kernel_gen/dsl/mlir_gen/emit/control_flow.py`
- `kernel_gen/dsl/mlir_gen/emit/value.py`
- `kernel_gen/dsl/mlir_gen/emit/type_utils.py`
- `kernel_gen/dsl/mlir_gen/emit/shape_utils.py`
- `kernel_gen/dsl/emit_mlir.py`
- `test/dsl/mlir_gen/emit/test_dispatch.py`
- `test/dsl/mlir_gen/emit/test_control_flow.py`
- `test/dsl/mlir_gen/emit/test_value.py`
- `test/dsl/mlir_gen/emit/test_type_utils.py`
- `test/dsl/mlir_gen/emit/test_shape_utils.py`
- `expectation/dsl/mlir_gen/__main__.py`

#### 目标 `spec` / API

- `EmitContext(builder, symbols, types, config)`
- `emit_mlir(node, ctx) -> Operation | SSAValue | None`

#### 文件职责收口

- `kernel_gen/dsl/mlir_gen/emit/dispatch.py`
  - 只做节点类型到处理函数的路由；
  - 不直接写 `nn.* / dma.* / arch.* / symbol.*` 细节。
- `kernel_gen/dsl/mlir_gen/emit/control_flow.py`
  - 只处理 `AssignAST / ReturnAST / ForAST`；
  - 不直接解析 helper 名称。
- `kernel_gen/dsl/mlir_gen/emit/value.py`
  - 只处理变量取值、字面量、`symbol.const`、索引值；
  - 不直接构造 `nn.add`、`dma.slice` 这类 family op。
- `kernel_gen/dsl/mlir_gen/emit/type_utils.py`
  - 只处理 dtype、memory type、结果类型、broadcast 类型规则；
  - 不放 builder 插入逻辑。
- `kernel_gen/dsl/mlir_gen/emit/shape_utils.py`
  - 只处理 shape、stride、layout、index 规范化；
  - 不直接发射最终 operation。

#### 预期示例代码

```python
CASE_1_RUNTIME_ARGS = (
    Memory([2, 2], NumericType.Float32, space=MemorySpace.GM),
)

def identity_kernel(x):
    y = x
    return y
```

```python
CASE_2_RUNTIME_ARGS = (
    Memory([SymbolDim("M")], NumericType.Float32, space=MemorySpace.GM),
)

def simple_loop_kernel(x):
    for i in range(0, 4, 1):
        x = x
    return x
```

#### 预期输出

```text
func.func @identity_kernel(%0 : !nn.memory<[2, 2], [2, 1], f32, #nn.space<global>>)
    -> !nn.memory<[2, 2], [2, 1], f32, #nn.space<global>> {
  func.return %0 : !nn.memory<[2, 2], [2, 1], f32, #nn.space<global>>
}
```

```text
symbol.const 0 : !symbol.int<"0">
symbol.const 4 : !symbol.int<"4">
symbol.const 1 : !symbol.int<"1">
symbol.for %i = (%c0, %c4, %c1) : !symbol.int<"0">, !symbol.int<"4">, !symbol.int<"1">
```

#### 预期输出细节

- `dispatch.py` 只做节点分发；
- `control_flow.py` 只承接结构节点；
- `value.py` 负责常量、symbol 常量、索引值物化；
- `type_utils.py` / `shape_utils.py` 不直接组装 family op；
- root `expectation/dsl/mlir_gen/__main__.py` 在本阶段只要求“入口存在并能启动”；
- `arch / symbol / dma / nn` family 的具体 case 通过与否，分别留给 `S4 / S5 / S6 / S7` 收口；
- 因此若 `python -m expectation.dsl.mlir_gen` 继续报 family 级失败，只要失败归属在 `arch / symbol / dma / nn`，不作为 `S3` 阻断。

#### 目标验收资产

- `expectation/dsl/mlir_gen/__main__.py`

#### 验收必过项目

- `python -m py_compile expectation/dsl/mlir_gen/__main__.py`
- `pytest -q test/dsl/mlir_gen/emit/test_dispatch.py test/dsl/mlir_gen/emit/test_control_flow.py test/dsl/mlir_gen/emit/test_value.py test/dsl/mlir_gen/emit/test_type_utils.py test/dsl/mlir_gen/emit/test_shape_utils.py`

#### 当前阶段补充（2026-04-13）

- `S3` 当前只负责补齐根目录入口 `expectation/dsl/mlir_gen/__main__.py` 与 `emit` 共享核心。
- 该入口当前会串起 `arch / symbol / dma / nn` 全部 family；因此执行时出现的跨 family 失败应按所属阶段继续分流：
  - `arch / symbol` -> `S4`
  - `dma` -> `S5`
  - `nn` elementwise -> `S6`
  - `nn` structured 与目录全量 -> `S7`
- `S3` 不要求在本阶段拉通 `PYTHONPATH=. python -m expectation.dsl.mlir_gen` 的全目录通过；该命令的全量通过属于计划最终完成态。

#### 任务新建建议

- `推进方式：按默认 spec/build/review/merge 路线推进，本阶段只定义收口范围。`
- `阶段目标：把 emit 的共享核心从 family 逻辑中拆开，并补齐根目录入口。`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/15/20260413-dsl-mlir-gen-s3.md`

### S4：`arch` 与 `symbol` family

#### 阶段目标

- 只处理 `call_arch.py`、`call_symbol.py` 及其 expectation。
- 不进入 `dma` 与 `nn`。

#### 可改文件

- `spec/dsl/emit_mlir.md`
- `spec/dialect/arch.md`
- `spec/dialect/symbol.md`
- `kernel_gen/dsl/mlir_gen/emit/call_dispatch.py`
- `kernel_gen/dsl/mlir_gen/emit/call_arch.py`
- `kernel_gen/dsl/mlir_gen/emit/call_symbol.py`
- `test/dsl/test_emit_mlir.py`
- `test/dsl/test_ast_visitor.py`
- `test/dsl/test_mlir_gen.py`
- `expectation/dsl/mlir_gen/dialect/arch`
- `expectation/dsl/mlir_gen/dialect/symbol`

#### 目标 `spec` / API

- `emit_mlir(node, ctx) -> Operation | SSAValue | None`
- `build_func_op_from_ast(...) -> func.func`

#### 文件职责收口

- `kernel_gen/dsl/mlir_gen/emit/call_dispatch.py`
  - 只根据 helper 名称把调用路由到 `call_arch.py` 或 `call_symbol.py`；
  - 不自己写最终 op。
- `kernel_gen/dsl/mlir_gen/emit/call_arch.py`
  - 只承接 `get_thread_num / get_thread_id / get_dynamic_memory / launch_kernel`；
  - 不处理 `symbol.const / symbol.to_float`。
- `kernel_gen/dsl/mlir_gen/emit/call_symbol.py`
  - 只承接 `symbol.const / symbol.to_float / get_dim / get_stride / symbol.for` 相关 lowering；
  - 不写 `dma.*` 或 `nn.*`。

#### 预期示例代码

```python
CASE_1_RUNTIME_ARGS = ()

def thread_query_kernel():
    return get_thread_num()
```

```python
CASE_2_RUNTIME_ARGS = (SymbolDim("M"),)

def symbol_add_kernel(m):
    return m + 2
```

```python
CASE_3_RUNTIME_ARGS = (
    SymbolDim("START"),
    SymbolDim("END"),
    SymbolDim("STEP"),
)

def symbol_loop_kernel(start, end, step):
    for i in range(start, end, step):
        pass
```

#### 预期输出

```text
%0 = arch.get_thread_num : !symbol.int<"thread_num">
```

```text
%1 = symbol.const 2 : !symbol.int<"2">
%2 = symbol.add %0, %1 : !symbol.int<"M">, !symbol.int<"2"> -> !symbol.int<"M + 2">
```

```text
symbol.for %i = %start to %end step %step {iter = #symbol.iter<start = "START", end = "END", step = "STEP">}
```

```text
%0 = arch.get_dynamic_memory #nn.space<local> : !nn.memory<[LM_SIZE], [1], i8, #nn.space<local>>
```

#### 预期输出细节

- `arch.get_dynamic_memory(...)` 维持单入口命名；
- `symbol.const` 用于整数常量，不再把这类整数直接落到 `arith.constant i32`；
- `LoopRange` 文本目标固定为 `symbol.for {iter = #symbol.iter<...>}`，循环块参数 `it` 固定为 `!symbol.iter<...>`；
- `symbol.to_float`、`get_dim`、`get_stride` 仍由 `call_symbol.py` 统一承接。

#### 目标验收资产

- `expectation/dsl/mlir_gen/dialect/arch`
- `expectation/dsl/mlir_gen/dialect/symbol`

#### 验收必过项目

- `PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.arch`
- `PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.arch.execution_dims`
- `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/arch/get_dynamic_memory.py`
- `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/arch/launch_kernel.py`
- `PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.symbol`
- `PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.symbol.element_binary`
- `PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.symbol.element_compare`
- `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/symbol/get_dim.py`
- `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/symbol/get_stride.py`
- `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/symbol/to_float.py`
- `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/symbol/for_loop.py`
- `pytest -q test/dsl/test_emit_mlir.py test/dsl/test_ast_visitor.py test/dsl/test_mlir_gen.py`

#### 当前阶段补充（2026-04-14）

- 已由架构侧直接补齐 [`expectation/dsl/mlir_gen/dialect/arch/__main__.py`](../../expectation/dsl/mlir_gen/dialect/arch/__main__.py) 与 [`expectation/dsl/mlir_gen/dialect/symbol/__main__.py`](../../expectation/dsl/mlir_gen/dialect/symbol/__main__.py)。
- 已由架构侧直接收口 `symbol.for` 的公开合同：[`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)、[`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)、[`expectation/dsl/mlir_gen/dialect/symbol/for_loop.py`](../../expectation/dsl/mlir_gen/dialect/symbol/for_loop.py) 统一为 `start/end/step -> !symbol.int<"...">`、`it -> !symbol.iter<...>`。
- 当前 `PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.arch` 已通过；`PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.symbol` 仍未通过。
- 当前 `symbol` 包剩余失败为 [`expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py`](../../expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py) 的 `AstVisitorError: nn.add requires at least one nn.memory operand`。
- 该失败按 2026-04-14 架构口径归类为实现问题，不回退 expectation/spec 合同；本阶段后续由 build 执行链继续处理实现与验证，不授权执行人以“修 expectation”方式绕过该失败。
- `2026-04-14 compare 合同补充`：
  - [`spec/tools/mlir_gen_compare.md`](../../spec/tools/mlir_gen_compare.md) 继续以“`mlir_gen(...)` 失败直接向上传播”为唯一工具合同，不新增 compare 层异常归一。
  - `symbol.element_compare` family 的 `CASE-3` 若仍使用“未注解 float runtime 参数”作为负例，则必须锁定当前公开失败语义 `Missing annotation`，不得改写为 `TypeError: Unsupported comparison type`。
  - 若后续需要专门覆盖“比较对象不是 symbol/int”的语义错误，应另建能穿过 AST 注解层的负例，不得通过修改 `mlir_gen_compare` 来掩盖上游失败语义。

#### 任务新建建议

- `推进方式：按默认 spec/build/review/merge 路线推进，本阶段只定义收口范围。`
- `阶段目标：收口 arch 与 symbol family 的发射文件、spec、测试和 expectation。`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/15/20260413-dsl-mlir-gen-s4.md`

### S5：`dma` family

#### 阶段目标

- 只处理 `call_dma.py` 及 `dma` expectation。
- 包含基础 helper 与结构化 helper。
- 不进入 `nn`。

#### 可改文件

- `spec/dsl/emit_mlir.md`
- `spec/dialect/dma.md`
- `spec/operation/dma.md`
- `kernel_gen/dsl/mlir_gen/emit/call_dma.py`
- `test/dsl/mlir_gen/emit/test_call_dma.py`
- `expectation/dsl/mlir_gen/dialect/dma`

#### 目标 `spec` / API

- `emit_mlir(node, ctx) -> Operation | SSAValue | None`

#### 文件职责收口

- `kernel_gen/dsl/mlir_gen/emit/call_dma.py`
  - 统一承接 `alloc / free / copy / cast / view / slice / deslice / reshape / read_tile / writeback`；
  - 不把 `nn.*` 或 `symbol` 计算规则塞进来。
- `call_dma.py` 内允许调用 `value.py / type_utils.py / shape_utils.py`；
  - 不反向把 `dma` 专有规则写回这些公共文件。

#### 预期示例代码

```python
CASE_1_RUNTIME_ARGS = ()

def dma_alloc_kernel():
    return alloc([2, 3], NumericType.Float32, MemorySpace.SM)
```

```python
CASE_2_RUNTIME_ARGS = (
    Memory([SymbolDim("N")], NumericType.Float32, space=MemorySpace.GM),
)

def dma_slice_kernel(x):
    return load(x, [1], [1], [1])
```

```python
CASE_3_RUNTIME_ARGS = (
    Memory([SymbolDim("N")], NumericType.Float32, space=MemorySpace.GM),
)

def dma_deslice_kernel(x):
    store(x, [1], [1], [1])
```

```python
CASE_4_DESC = "失败例子：静态 alloc 的 shape 个数与调用参数不一致时直接报错。"
```

#### 预期输出

```text
%0 = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[2, 3], [3, 1], f32, #nn.space<shared>>
```

```text
%1 = symbol.const 1 : !symbol.int<"1">
%2 = "dma.slice"(%0, %1, %1, %1) : (!nn.memory<[N], [1], f32, #nn.space<global>>, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"1">) -> !nn.memory<[1], [1], f32, #nn.space<global>>
```

```text
%1 = symbol.const 1 : !symbol.int<"1">
"dma.deslice"(%0, %1, %1, %1) : (!nn.memory<[1], [1], f32, #nn.space<global>>, !symbol.int<"1">, !symbol.int<"1">, !symbol.int<"1">) -> ()
```

```text
DmaEmitError: static alloc shape rank does not match provided extents
```

#### 预期输出细节

- 静态 `alloc` 不传动态 shape 操作数；
- 动态 / symbol 情况统一通过 `symbol.const`、`symbol.int` 进入 `dma` op；
- `read_tile / reshape_family / writeback` 全部挂在同一个 `call_dma.py`；
- `copy.py` 相关 expectation 不能再触发标准库 `copy` 的导入冲突。
- 静态越界、shape 个数不一致、slice 参数长度不一致都要在 expectation 中有失败例子。

#### 目标验收资产

- `expectation/dsl/mlir_gen/dialect/dma/alloc.py`
- `expectation/dsl/mlir_gen/dialect/dma/cast.py`
- `expectation/dsl/mlir_gen/dialect/dma/copy.py`
- `expectation/dsl/mlir_gen/dialect/dma/free.py`
- `expectation/dsl/mlir_gen/dialect/dma/view.py`
- `expectation/dsl/mlir_gen/dialect/dma/read_tile`
- `expectation/dsl/mlir_gen/dialect/dma/reshape_family`
- `expectation/dsl/mlir_gen/dialect/dma/writeback`

#### 验收必过项目

- `PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.dma`
- `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/dma/alloc.py`
- `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/dma/cast.py`
- `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/dma/copy.py`
- `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/dma/free.py`
- `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/dma/view.py`
- `PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.dma.read_tile`
- `PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.dma.reshape_family`
- `PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.dma.writeback`
- `pytest -q test/dsl/mlir_gen/emit/test_call_dma.py`

#### 补充记录（2026-04-14）

- 已补齐 `expectation/dsl/mlir_gen/dialect/dma/__main__.py` 作为 dma family 包级入口。
- `alloc.py / cast.py / free.py / view.py` 入口统一移除当前目录 `sys.path`，避免 `copy.py` 阴影标准库 `copy`。
- 本次仅收口 expectation 入口与 import 冲突，`call_dma.py / test_call_dma.py` 仍由 S5 build 继续推进。

#### 任务新建建议

- `推进方式：按默认 spec/build/review/merge 路线推进，本阶段只定义收口范围。`
- `阶段目标：把 dma 的基础 helper、结构化 helper 和目录入口统一收进 call_dma.py 对应边界。`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/15/20260413-dsl-mlir-gen-s5.md`

### S6：`nn` 元素级 family

#### 阶段目标

- 只处理 `call_nn.py` 中的元素级路径：
  - `element_unary`
  - `element_binary`
  - `element_compare`
- 不进入 `reduce / softmax / matmul / conv / img2col`。

#### 可改文件

- `spec/dsl/emit_mlir.md`
- `spec/dialect/nn.md`
- `spec/operation/nn.md`
- `kernel_gen/dsl/mlir_gen/emit/call_nn.py`
- `test/dsl/mlir_gen/emit/test_call_nn.py`
- `expectation/dsl/mlir_gen/dialect/nn/element_unary`
- `expectation/dsl/mlir_gen/dialect/nn/element_binary`
- `expectation/dsl/mlir_gen/dialect/nn/element_compare`

#### 目标 `spec` / API

- `emit_mlir(node, ctx) -> Operation | SSAValue | None`

#### 文件职责收口

- `kernel_gen/dsl/mlir_gen/emit/call_nn.py`
  - 当前阶段只承接 `element_unary / element_binary / element_compare`；
  - 不提前把 `reduce / conv / img2col / matmul` 混进本阶段提交。
- 广播、dtype cast、`memory + const`、`memory + symbol` 的公共规则统一写在 `call_nn.py`；
  - 不回流到 `type_utils.py` 做 `nn` 专用 builder 逻辑。

#### 执行边界补充（2026-04-14 21:05 +0800）

- 鉴于 `T-20260413-db4d3dfd` 的 review 已确认：若只改 [`kernel_gen/dsl/mlir_gen/emit/call_nn.py`](../../kernel_gen/dsl/mlir_gen/emit/call_nn.py)，不足以把 `nn` elementwise 的公共规则完整收口到单一实现点；本阶段允许同步调整最小桥接范围。
- 本阶段新增允许联动文件：
  - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
  - [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py)
  - [`kernel_gen/dsl/mlir_gen/emit/__init__.py`](../../kernel_gen/dsl/mlir_gen/emit/__init__.py)
  - [`kernel_gen/dsl/mlir_gen/function_builder.py`](../../kernel_gen/dsl/mlir_gen/function_builder.py)
  - [`kernel_gen/dsl/mlir_gen/signature.py`](../../kernel_gen/dsl/mlir_gen/signature.py)
  - [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py)
  - [`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
  - [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py)
- 新增联动文件只允许承接三类改动：
  - 把 `element_unary / element_binary / element_compare` 的共享规则转发、桥接到 `call_nn.py`
  - 对齐 `build_func_op(...)` / `AstVisitor` / facade 路径上的异常暴露与调用入口
  - 删除或收缩旧路径中仍残留的 `nn` elementwise 专用实现，避免形成第二份长期规则
- 不允许借本轮顺手扩写 `reduce / softmax / matmul / conv / img2col`；这些仍留在 `S7`。
- 本阶段完成时，`nn` elementwise 的长期实现归属仍以 [`kernel_gen/dsl/mlir_gen/emit/call_nn.py`](../../kernel_gen/dsl/mlir_gen/emit/call_nn.py) 为准；其它联动文件只保留入口、转发或兼容壳层职责。

#### 补充记录（2026-04-14 21:31 +0800）

- 鉴于 `T-20260413-db4d3dfd` 已恢复 `build_func_op(...)` 在隐式 broadcast 维度不兼容场景下抛出 `AstVisitorError` 的公开合同，S6 对应的 tracked expectation 失败用例也必须同步收口到同一异常面。
- 本轮由架构侧直接更新以下 expectation 负例分支，把 `except ValueError` 统一改为 `except AstVisitorError`，不再要求 build 角色越权改 tracked expectation：
  - [`expectation/dsl/mlir_gen/dialect/nn/element_binary/floordiv.py`](../../expectation/dsl/mlir_gen/dialect/nn/element_binary/floordiv.py)
  - [`expectation/dsl/mlir_gen/dialect/nn/element_binary/mul.py`](../../expectation/dsl/mlir_gen/dialect/nn/element_binary/mul.py)
  - [`expectation/dsl/mlir_gen/dialect/nn/element_binary/sub.py`](../../expectation/dsl/mlir_gen/dialect/nn/element_binary/sub.py)
  - [`expectation/dsl/mlir_gen/dialect/nn/element_binary/truediv.py`](../../expectation/dsl/mlir_gen/dialect/nn/element_binary/truediv.py)
  - [`expectation/dsl/mlir_gen/dialect/nn/element_compare/eq.py`](../../expectation/dsl/mlir_gen/dialect/nn/element_compare/eq.py)
  - [`expectation/dsl/mlir_gen/dialect/nn/element_compare/ge.py`](../../expectation/dsl/mlir_gen/dialect/nn/element_compare/ge.py)
  - [`expectation/dsl/mlir_gen/dialect/nn/element_compare/gt.py`](../../expectation/dsl/mlir_gen/dialect/nn/element_compare/gt.py)
  - [`expectation/dsl/mlir_gen/dialect/nn/element_compare/le.py`](../../expectation/dsl/mlir_gen/dialect/nn/element_compare/le.py)
  - [`expectation/dsl/mlir_gen/dialect/nn/element_compare/lt.py`](../../expectation/dsl/mlir_gen/dialect/nn/element_compare/lt.py)
  - [`expectation/dsl/mlir_gen/dialect/nn/element_compare/ne.py`](../../expectation/dsl/mlir_gen/dialect/nn/element_compare/ne.py)
- 本次收口只对齐异常合同，不新增 S6 的实现范围，也不改变 `call_nn.py` 为长期归属的边界。

#### 补充记录（2026-04-14 21:42 +0800）

- `T-20260413-db4d3dfd` 在复跑 `PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn.element_unary` 时，新增暴露出 `leaky_relu.py` 与 `hard_sigmoid.py` 仍沿用“未注解 float runtime 参数”旧写法，导致 `CASE-1/2/3` 统一报 `AstVisitorError: Missing annotation`。
- 经核对 AST 合同，`float` 当前只开放给 `-> float` 返回位，不开放为函数输入注解；因此这两份 unary expectation 的正确收口方式不是增加 `alpha: float` / `beta: float` 形参，而是改回 DSL 已公开支持的“函数体常量 kwarg”入口。
- 本轮由架构侧直接修正这两份 tracked expectation，将 `alpha / beta` 从 runtime 输入改为函数体内的常量实参，并同步调整 expectation IR 与说明文字：
  - [`expectation/dsl/mlir_gen/dialect/nn/element_unary/leaky_relu.py`](../../expectation/dsl/mlir_gen/dialect/nn/element_unary/leaky_relu.py)
  - [`expectation/dsl/mlir_gen/dialect/nn/element_unary/hard_sigmoid.py`](../../expectation/dsl/mlir_gen/dialect/nn/element_unary/hard_sigmoid.py)
- 本次仍只收口 expectation 合同，不扩大 build 角色边界；执行人无需修改 tracked expectation。

#### 补充记录（2026-04-14 21:50 +0800）

- `T-20260413-db4d3dfd` 的 review 已确认：当前 worktree 中的 [`kernel_gen/dsl/ast/parser.py`](../../kernel_gen/dsl/ast/parser.py) 与 [`kernel_gen/dialect/nn.py`](../../kernel_gen/dialect/nn.py) 并非顺手扩面，而是 `call_nn.py` 收口 `element_compare` / mixed scalar / unary helper 合同所依赖的最小桥接实现。
- 因此，S6 在 `21:05 +0800` 的 bridge 白名单基础上，再补充允许以下两个联动文件：
  - [`kernel_gen/dsl/ast/parser.py`](../../kernel_gen/dsl/ast/parser.py)
  - [`kernel_gen/dialect/nn.py`](../../kernel_gen/dialect/nn.py)
- 新增的这两个文件只允许承接以下最小范围：
  - 在 parser 中补齐 `nn.eq/ne/lt/le/gt/ge` 到 `CompareExprAST` 的 helper 解析入口，保证 `call_nn.py` 的 compare family 有唯一前端入口。
  - 在 `kernel_gen/dialect/nn.py` 中补齐 `element_unary / element_binary / element_compare` 当前公开合同所必需的 verifier、op 壳层与 mixed scalar 校验逻辑，保证 `call_nn.py` 不需要回退到旧实现点。
- 仍不允许借此顺手扩写 `reduce / softmax / matmul / conv / img2col`，也不允许把新的长期规则再回流到 `emit_mlir.py` 之外的其它文件。
- 本次补充的目的仅是把 S6 文档化 bridge 范围与当前实际提交面对齐；`nn` elementwise 的长期实现归属仍以 [`kernel_gen/dsl/mlir_gen/emit/call_nn.py`](../../kernel_gen/dsl/mlir_gen/emit/call_nn.py) 为准。

#### 预期示例代码

```python
CASE_1_RUNTIME_ARGS = (
    Memory([2, 2], NumericType.Float32, space=MemorySpace.GM),
)

def unary_kernel(x):
    return exp(x)
```

```python
CASE_2_RUNTIME_ARGS = (
    Memory([2, 2], NumericType.Float32, space=MemorySpace.GM),
)

def add_const_kernel(x):
    return x + 1
```

```python
CASE_3_RUNTIME_ARGS = (
    Memory([2, 2], NumericType.Float32, space=MemorySpace.GM),
    SymbolDim("K"),
)

def add_symbol_kernel(x, k):
    return x + float(k)
```

```python
CASE_4_RUNTIME_ARGS = (
    Memory([2, 2], NumericType.Float32, space=MemorySpace.GM),
    Memory([1, 2], NumericType.Float16, space=MemorySpace.GM),
)

def compare_kernel(x, y):
    return x > y
```

#### 预期输出

```text
%1 = "nn.exp"(%0) : (...) -> !nn.memory<[2, 2], [2, 1], f32, #nn.space<global>>
```

```text
%1 = symbol.const 1 : !symbol.int<"1">
%2 = symbol.to_float %1 : !symbol.int<"1"> -> f32
%3 = "nn.add"(%0, %2) : (!nn.memory<[2, 2], [2, 1], f32, #nn.space<global>>, f32) -> !nn.memory<[2, 2], [2, 1], f32, #nn.space<global>>
```

```text
%1 = symbol.to_float %0 : !symbol.int<"K"> -> f32
%2 = "nn.add"(%x, %1) : (!nn.memory<[2, 2], [2, 1], f32, #nn.space<global>>, f32) -> !nn.memory<[2, 2], [2, 1], f32, #nn.space<global>>
```

```text
%1 = "nn.cast"(%y) : !nn.memory<[1, 2], [2, 1], f16, #nn.space<global>> -> !nn.memory<[1, 2], [2, 1], f32, #nn.space<global>>
%2 = "nn.broadcast_to"(%1) : ... -> !nn.memory<[2, 2], [2, 1], f32, #nn.space<global>>
%3 = "nn.gt"(%x, %2) : ... -> !nn.memory<[2, 2], [2, 1], i1, #nn.space<global>>
```

#### 预期输出细节

- `memory + const` 走 `symbol.const` 再按需要转成目标浮点类型；
- `memory + symbol` 走 `symbol.to_float`；
- 隐式 broadcast 与 dtype cast 在 `call_nn.py` 内统一处理；
- `hard_sigmoid`、`add`、`mul`、`sub`、`truediv`、比较类 expectation 都要给出静态 / 动态 / `const` / `symbol` 例子。

#### 目标验收资产

- `expectation/dsl/mlir_gen/dialect/nn/element_unary`
- `expectation/dsl/mlir_gen/dialect/nn/element_binary`
- `expectation/dsl/mlir_gen/dialect/nn/element_compare`

#### 验收必过项目

- `PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn.element_unary`
- `PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn.element_binary`
- `PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn.element_compare`
- `pytest -q test/dsl/mlir_gen/emit/test_call_nn.py -k \"element_unary or element_binary or element_compare\"`

#### 任务新建建议

- `推进方式：按默认 spec/build/review/merge 路线推进，本阶段只定义收口范围。`
- `阶段目标：收口 nn 元素级 helper 的发射边界、测试与 expectation。`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/15/20260413-dsl-mlir-gen-s6.md`

### S7：`nn` 结构化 family 与目录总收口

#### 阶段目标

- 只处理 `call_nn.py` 中的结构化路径：
  - `broadcast`
  - `broadcast_to`
  - `reduce`
  - `softmax`
  - `matmul`
  - `fc`
  - `img2col1d`
  - `img2col2d`
  - `conv`
- 收尾整个 `expectation/dsl/mlir_gen` 目录和全部目录入口。

#### 可改文件

- `spec/dsl/emit_mlir.md`
- `spec/dialect/nn.md`
- `spec/operation/nn.md`
- `kernel_gen/dsl/mlir_gen/emit/call_nn.py`
- `expectation/dsl/mlir_gen/dialect/nn`
- `expectation/dsl/mlir_gen/__main__.py`
- `test/dsl/mlir_gen/emit/test_call_nn.py`
- `test/dsl/mlir_gen/`

#### 目标 `spec` / API

- `emit_mlir(node, ctx) -> Operation | SSAValue | None`
- `mlir_gen(...) -> builtin.module`

#### 文件职责收口

- `kernel_gen/dsl/mlir_gen/emit/call_nn.py`
  - 本阶段补齐 `broadcast / broadcast_to / reduce / softmax / matmul / fc / img2col1d / img2col2d / conv`；
  - 不再新建额外 `nn_*` 实现文件。
- `test/dsl/mlir_gen/emit/test_call_nn.py`
  - 只按 family 分组补 case；
  - 不把 expectation 的完整 IR 文本复制进单元测试。

#### 预期示例代码

```python
CASE_1_RUNTIME_ARGS = (
    Memory([2, 4], NumericType.Float32, space=MemorySpace.GM),
)

def reduce_sum_kernel(x):
    return reduce_sum(x, axis=1, keepdim=False)
```

```python
CASE_2_RUNTIME_ARGS = (
    Memory([SymbolDim("N"), SymbolDim("C"), SymbolDim("H"), SymbolDim("W")], NumericType.Float32, space=MemorySpace.GM),
    Memory([SymbolDim("OC"), SymbolDim("IC"), 3, 3], NumericType.Float32, space=MemorySpace.GM),
)

def conv_kernel(x, w):
    return conv(x, w, sh=1, sw=1, ph=1, pw=1)
```

```python
CASE_3_RUNTIME_ARGS = (
    Memory([SymbolDim("N"), SymbolDim("C"), SymbolDim("W")], NumericType.Float32, space=MemorySpace.GM),
)

def img2col1d_kernel(x):
    return img2col1d(x, kw=3, pad=1, layout="clast", norm=True)
```

```python
CASE_4_RUNTIME_ARGS = (
    Memory([2, 1], NumericType.Float32, space=MemorySpace.GM),
)

def broadcast_kernel(x):
    return broadcast_to(x, [2, 4])
```

#### 预期输出

```text
%1 = "nn.reduce"(%0) {kind = "sum", axis = array<i64: 1>, keepdim = false} : (!nn.memory<[2, 4], [4, 1], f32, #nn.space<global>>) -> !nn.memory<[2], [1], f32, #nn.space<global>>
```

```text
%1 = "nn.img2col2d"(%0) {kh = 3, kw = 3, ph = 1, pw = 1, sh = 1, sw = 1, layout = "clast", norm = false} : (!nn.memory<[N, C, H, W], [C*H*W, H*W, W, 1], f32, #nn.space<global>>) -> !nn.memory<[N, OH, OW, C*3*3], [OH*OW*C*3*3, OW*C*3*3, C*3*3, 1], f32, #nn.space<global>>
%2 = "nn.matmul"(%1, %w) : (!nn.memory<[N, OH, OW, C*3*3], [OH*OW*C*3*3, OW*C*3*3, C*3*3, 1], f32, #nn.space<global>>, !nn.memory<[OC, IC, 3, 3], [IC*3*3, 3*3, 3, 1], f32, #nn.space<global>>) -> !nn.memory<[N, OC, OH, OW], [OC*OH*OW, OH*OW, OW, 1], f32, #nn.space<global>>
```

```text
%1 = "nn.img2col1d"(%0) {kw = 3, pad = 1, layout = "clast", norm = true} : (!nn.memory<[N, C, W], [C*W, W, 1], f32, #nn.space<global>>) -> !nn.memory<[N, OW, C*3], [OW*C*3, C*3, 1], f32, #nn.space<global>>
```

```text
%1 = "nn.broadcast_to"(%0) {shape = [2, 4]} : !nn.memory<[2, 1], [1, 1], f32, #nn.space<global>> -> !nn.memory<[2, 4], [4, 1], f32, #nn.space<global>>
```

#### 预期输出细节

- `reduce` 必须覆盖 `keepdim=False` 与动态 axis；
- `conv` / `img2col` 要把 `layout`、`norm`、`pad`、kernel size 参数直接体现在 expectation 文本里；
- `broadcast` / `broadcast_to` 仍由 `call_nn.py` 承接，不额外分出新实现文件；
- 完成本阶段后，`python -m expectation.dsl.mlir_gen` 应能一次性跑通全目录。
- `conv` 的 expectation 必须锁住输入 rank 4 输出 rank 4，不接受额外维度膨胀。

#### 目标验收资产

- `expectation/dsl/mlir_gen/dialect/nn`
- `expectation/dsl/mlir_gen/__main__.py`

#### 验收必过项目

- `PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn`
- `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/broadcast.py`
- `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/broadcast_to.py`
- `PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn.reduce`
- `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/matmul.py`
- `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/fc.py`
- `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/softmax.py`
- `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/img2col1d.py`
- `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/img2col2d.py`
- `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/conv.py`
- `PYTHONPATH=. python -m expectation.dsl.mlir_gen`
- `pytest -q test/dsl/ast test/dsl/mlir_gen test/dsl/mlir_gen/emit test/tools/test_mlir_gen_compare.py`

#### 任务新建建议

- `推进方式：按默认 spec/build/review/merge 路线推进，本阶段只定义收口范围。`
- `阶段目标：收口 nn 结构化 helper，并让整个 expectation/dsl/mlir_gen 目录最终一次性跑通。`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/15/20260413-dsl-mlir-gen-s7.md`

### S8：终验修复补充

#### 阶段目标

- 只处理当前终验仍未收口的剩余项，不再扩写新的 family、helper 或目录结构。
- 让计划正文列出的最终目录入口与总体验收命令在主仓直接通过。

#### 可改文件

- `ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md`
- `spec/dsl/emit_mlir.md`
- `spec/dsl/mlir_gen.md`
- `kernel_gen/dsl/mlir_gen/emit/call_symbol.py`
- `kernel_gen/dsl/mlir_gen/emit/call_nn.py`
- `kernel_gen/dsl/mlir_gen/emit/value.py`
- `expectation/dsl/mlir_gen/__main__.py`
- `expectation/dsl/mlir_gen/dialect/symbol`
- `expectation/dsl/mlir_gen/dialect/nn`
- `test/dsl/mlir_gen/emit/test_call_symbol.py`
- `test/dsl/mlir_gen/emit/test_call_nn.py`
- `test/dsl/mlir_gen`

#### 本阶段只收口的内容

- `symbol.add` 必须稳定生成 `symbol.add`，不允许再落到 `nn.add` 路径。
- `expectation/dsl/mlir_gen/dialect/nn/__main__.py` 必须补齐，使 `python -m expectation.dsl.mlir_gen.dialect.nn` 可直接执行。
- `expectation/dsl/mlir_gen/__main__.py` 中当前仍失败的这些入口必须逐项收口：
  - `top.import_bound_helper`
  - `top.return_type_from_body_not_signature`
  - `dialect.nn.conv`
  - `dialect.nn.fc`
  - `dialect.nn.img2col1d`
  - `dialect.nn.img2col2d`
  - `dialect.nn.matmul`
  - `dialect.nn.reduce`
  - `dialect.nn.softmax`
  - `dialect.symbol.element_binary`
  - `dialect.symbol.for_loop`

#### 不纳入本阶段的内容

- 不新增新的 DSL helper。
- 不新增新的 `emit` 一级目录。
- 不改 `expectation/dsl/mlir_gen` 既有统一模板。

#### 预期示例代码

```python
def symbol_add_kernel(lhs, rhs):
    return lhs + rhs
```

```python
CASE_RUNTIME_ARGS = (SymbolDim("M"), SymbolDim("N"))
```

```text
%2 = symbol.add %0, %1 : !symbol.int<"M">, !symbol.int<"N"> -> !symbol.int<"M + N">
```

#### 预期输出细节

- `symbol` family 的 `element_binary/add.py` 在 `CASE-1/2/3` 都必须直接通过，不再出现 `nn.add requires at least one nn.memory operand`。
- `nn` 目录入口既要能 `python -m expectation.dsl.mlir_gen.dialect.nn`，也要在根目录入口里不再留下残余失败项。
- `top` 层三个脚本与四个一级目录入口的执行结果，必须与计划正文的最终完成态一致。

#### 目标验收资产

- `expectation/dsl/mlir_gen/__main__.py`
- `expectation/dsl/mlir_gen/dialect/symbol`
- `expectation/dsl/mlir_gen/dialect/nn`

#### 验收必过项目

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.symbol`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen`
- `pytest -q test/dsl/ast test/dsl/mlir_gen test/dsl/mlir_gen/emit test/tools/test_mlir_gen_compare.py`

#### 任务新建建议

- `推进方式：按默认 spec/build/review/merge 路线推进，本阶段只定义终验补充范围。`
- `阶段目标：收口 symbol.add 路径、nn 目录入口与根目录剩余 expectation。`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260415-dsl-mlir-gen-final-fix.md`

## 已确定事项

- `LoopRange` 的目标文本按独立 `symbol.for` 推进，不再使用 `scf.for + symbol.iter`。
- `arch.get_dynamic_memory(...)` 保留单入口命名，不拆成按 memory space 分名的多个入口。

## 参考资料

- [`spec/dsl/ast.md`](../../spec/dsl/ast.md)
- [`spec/dsl/ast_visitor.md`](../../spec/dsl/ast_visitor.md)
- [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
- [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
- [`spec/tools/mlir_gen_compare.md`](../../spec/tools/mlir_gen_compare.md)
- [`expectation/dsl/mlir_gen`](../../expectation/dsl/mlir_gen)

## 终验结论（2026-04-15 04:40 +0800）

- 终验人：`守护最好的爱莉希雅`
- 协同复核人：`大闸蟹`
- 终验结论：`不通过`
- 依据：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen` -> `exit=1`；根目录入口仍有 `11` 组失败，包含顶层脚本、`dialect.nn` 结构化 helper、`dialect.symbol` 等失败面，尚未达到“全目录一次性跑通”的完成态。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.arch` -> `exit=0`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.symbol` -> `exit=1`；当前仍报 `dsl mlir_gen symbol.add expectation failed (1 cases): CASE-1: AstVisitorError: nn.add requires at least one nn.memory operand`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.dma` -> `exit=0`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn` -> `exit=1`；当前主仓缺少 [`expectation/dsl/mlir_gen/dialect/nn/__main__.py`](../../expectation/dsl/mlir_gen/dialect/nn/__main__.py)，目录入口未闭合。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/ast test/dsl/mlir_gen test/dsl/mlir_gen/emit test/tools/test_mlir_gen_compare.py` -> `57 passed`；说明测试层基本稳定，但不能替代目录级 expectation 完成态。
- 最小阻断项：
  - 根目录入口 [`expectation/dsl/mlir_gen/__main__.py`](../../expectation/dsl/mlir_gen/__main__.py) 仍未跑通；除 `symbol.add` 外，还包含 [`expectation/dsl/mlir_gen/import_bound_helper.py`](../../expectation/dsl/mlir_gen/import_bound_helper.py)、[`expectation/dsl/mlir_gen/return_type_from_body_not_signature.py`](../../expectation/dsl/mlir_gen/return_type_from_body_not_signature.py)、[`expectation/dsl/mlir_gen/dialect/nn/conv.py`](../../expectation/dsl/mlir_gen/dialect/nn/conv.py)、[`expectation/dsl/mlir_gen/dialect/nn/fc.py`](../../expectation/dsl/mlir_gen/dialect/nn/fc.py)、[`expectation/dsl/mlir_gen/dialect/nn/img2col1d.py`](../../expectation/dsl/mlir_gen/dialect/nn/img2col1d.py)、[`expectation/dsl/mlir_gen/dialect/nn/img2col2d.py`](../../expectation/dsl/mlir_gen/dialect/nn/img2col2d.py)、[`expectation/dsl/mlir_gen/dialect/nn/matmul.py`](../../expectation/dsl/mlir_gen/dialect/nn/matmul.py)、[`expectation/dsl/mlir_gen/dialect/nn/reduce`](../../expectation/dsl/mlir_gen/dialect/nn/reduce)、[`expectation/dsl/mlir_gen/dialect/nn/softmax.py`](../../expectation/dsl/mlir_gen/dialect/nn/softmax.py)、[`expectation/dsl/mlir_gen/dialect/symbol/for_loop.py`](../../expectation/dsl/mlir_gen/dialect/symbol/for_loop.py) 的失败面。
  - [`expectation/dsl/mlir_gen/dialect/nn`](../../expectation/dsl/mlir_gen/dialect/nn) 缺少目录入口 `__main__.py`，计划正文要求的 `python -m expectation.dsl.mlir_gen.dialect.nn` 当前无法直接运行。
- 终验说明：
  - 当前主仓只满足测试层通过与 `arch/dma` 两个 family 入口通过；尚未满足根目录 expectation 与 `nn/symbol` family 入口两项完成态。
  - [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py) 的顶层 facade 收口已由后续计划 [`ARCHITECTURE/plan/dsl_emit_mlir_refactor_green_plan.md`](../../ARCHITECTURE/plan/dsl_emit_mlir_refactor_green_plan.md) 单独承接，不作为本次终验修复范围。
  - 因此本计划暂不具备归档条件；需先补修复任务，收口上述 expectation 失败面，再回到终验。

## 修复任务补建（2026-04-15 04:42 +0800）

- 补建人：`守护最好的爱莉希雅`
- 修复任务：[`T-20260415-a4a3183f`](../../TODO.md)
- 任务类型：`build`
- `worktree`：`wt-20260415-dsl-mlir-gen-final-fix`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/16/20260415-dsl-mlir-gen-final-fix.md`
- 唯一修复范围：
  - 补齐 [`expectation/dsl/mlir_gen/dialect/nn/__main__.py`](../../expectation/dsl/mlir_gen/dialect/nn/__main__.py) 并让 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn` 可直接运行。
  - 收口 [`expectation/dsl/mlir_gen/import_bound_helper.py`](../../expectation/dsl/mlir_gen/import_bound_helper.py)、[`expectation/dsl/mlir_gen/return_type_from_body_not_signature.py`](../../expectation/dsl/mlir_gen/return_type_from_body_not_signature.py)、[`expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py`](../../expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py)、[`expectation/dsl/mlir_gen/dialect/symbol/for_loop.py`](../../expectation/dsl/mlir_gen/dialect/symbol/for_loop.py) 的终验失败面。
  - 收口 [`expectation/dsl/mlir_gen/dialect/nn/conv.py`](../../expectation/dsl/mlir_gen/dialect/nn/conv.py)、[`expectation/dsl/mlir_gen/dialect/nn/fc.py`](../../expectation/dsl/mlir_gen/dialect/nn/fc.py)、[`expectation/dsl/mlir_gen/dialect/nn/img2col1d.py`](../../expectation/dsl/mlir_gen/dialect/nn/img2col1d.py)、[`expectation/dsl/mlir_gen/dialect/nn/img2col2d.py`](../../expectation/dsl/mlir_gen/dialect/nn/img2col2d.py)、[`expectation/dsl/mlir_gen/dialect/nn/matmul.py`](../../expectation/dsl/mlir_gen/dialect/nn/matmul.py)、[`expectation/dsl/mlir_gen/dialect/nn/reduce`](../../expectation/dsl/mlir_gen/dialect/nn/reduce)、[`expectation/dsl/mlir_gen/dialect/nn/softmax.py`](../../expectation/dsl/mlir_gen/dialect/nn/softmax.py) 的结构化 helper 失败面。
- 续推口径：
  - 当前不得进入归档链。
  - 若 [`T-20260415-f0ecdd70`](../../TODO.md) 仍留在 `TODO.md`，视为重复修复任务，不再推进；以 [`T-20260415-a4a3183f`](../../TODO.md) 作为唯一继续项。
  - 待 [`T-20260415-a4a3183f`](../../TODO.md) 完成并复核通过后，回到本计划重新执行终验。

## 终验复核（2026-04-15 14:03 +0800）

- 终验人：`大闸蟹`
- 当前结论：`不通过`
- 依据：
  - 当前主仓：`HEAD=bb51390`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.arch` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.dma` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.symbol` -> `exit=1`；当前仍报 `dsl mlir_gen symbol.add expectation failed (1 cases): CASE-1: AstVisitorError: nn.add requires at least one nn.memory operand`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn` -> `exit=1`；当前主仓仍缺 [`expectation/dsl/mlir_gen/dialect/nn/__main__.py`](../../expectation/dsl/mlir_gen/dialect/nn/__main__.py)
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen` -> `exit=1`；当前在导入 [`expectation/dsl/mlir_gen/dialect/nn/broadcast.py`](../../expectation/dsl/mlir_gen/dialect/nn/broadcast.py) 时即触发 `AttributeError: TLM. Did you mean: 'LM'?`，说明根目录入口仍包含旧 `MemorySpace.TLM` 口径
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/ast test/dsl/mlir_gen test/dsl/mlir_gen/emit test/tools/test_mlir_gen_compare.py` -> `57 passed`
- 最小阻断项：
  - [`expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py`](../../expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py) 的 `CASE-1` 仍未收口，`symbol.add` 场景还在走 `nn.add` 路径。
  - [`expectation/dsl/mlir_gen/dialect/nn`](../../expectation/dsl/mlir_gen/dialect/nn) 目录入口仍未闭合；计划正文要求的 `python -m expectation.dsl.mlir_gen.dialect.nn` 目前无法直接执行。
  - 根目录入口 [`expectation/dsl/mlir_gen/__main__.py`](../../expectation/dsl/mlir_gen/__main__.py) 仍未恢复到可执行状态；当前最先暴露的阻断是 [`expectation/dsl/mlir_gen/dialect/nn/broadcast.py`](../../expectation/dsl/mlir_gen/dialect/nn/broadcast.py) 仍引用已移除的 `MemorySpace.TLM`，导致目录级 expectation 在 import 阶段即失败。
- 终验说明：
  - [`T-20260415-a4a3183f`](../../TODO.md) 已完成并合入主仓，但当前主仓结果仍未达到本计划完成态定义中的“expectation 全目录通过 + family 目录入口可直接运行”。
  - 当前测试层 `57 passed` 只能证明 AST / mlir_gen / emit / compare 基本稳定，不能替代目录级 expectation 完成态。
  - 因此本计划当前仍不具备归档条件；需继续沿唯一修复任务收口上述三项剩余阻断。

## 修复任务补记（2026-04-15 14:04 +0800）

- 补记人：`大闸蟹`
- 唯一继续项：[`T-20260415-b085f193`](../../TODO.md)
- 任务类型：`build`
- `worktree`：`wt-20260415-dsl-mlir-gen-r2-fix`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/16/20260415-dsl-mlir-gen-r2-fix.md`
- 唯一修复范围：
  - 收口 [`expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py`](../../expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py) 的 `CASE-1`，确保 `symbol.add` 不再误走 `nn.add` 路径。
  - 补齐 [`expectation/dsl/mlir_gen/dialect/nn/__main__.py`](../../expectation/dsl/mlir_gen/dialect/nn/__main__.py)，让 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn` 可直接执行。
  - 收口 [`expectation/dsl/mlir_gen/dialect/nn/broadcast.py`](../../expectation/dsl/mlir_gen/dialect/nn/broadcast.py) 中旧 `MemorySpace.TLM` 口径，恢复 [`expectation/dsl/mlir_gen/__main__.py`](../../expectation/dsl/mlir_gen/__main__.py) 的可执行性。
- 续推口径：
  - 当前不得创建归档任务，也不得执行 `-done-plan`。
  - 以 [`T-20260415-b085f193`](../../TODO.md) 作为本轮唯一继续项；若后续再出现同范围修复任务，按重复任务处理，不再继续分发。

## 当前主仓终验（2026-04-16 09:16 +0800）

- 终验人：`守护最好的爱莉希雅`
- 当前结论：`不通过`
- 依据：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.arch` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.dma` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.symbol` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn` -> `exit=1`；当前汇总 `11` 组失败，集中为 `broadcast/broadcast_to/conv/fc/img2col1d/img2col2d/matmul/reduce/softmax` 的 `Unsupported annotation` / `Unsupported call expression` 等前端失败。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen` -> `exit=1`；当前根目录入口已不再卡在 `symbol`，唯一首个剩余失败面为 `dialect.nn` family。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/ast test/dsl/mlir_gen test/dsl/mlir_gen/emit test/tools/test_mlir_gen_compare.py` -> `1 failed, 57 passed`；当前失败为 [`test/dsl/ast/test_parser.py::test_parse_function_helper_call`](../../test/dsl/ast/test_parser.py)，错误为 `AstParseError: Unsupported call expression`。
- 最小阻断项：
  - [`expectation/dsl/mlir_gen/dialect/nn`](../../expectation/dsl/mlir_gen/dialect/nn) 当前整组结构化 helper 仍未收口到现行前端合同；公开 `nn` helper 的 expectation 运行仍大面积报 `Unsupported annotation` 或 `Unsupported call expression`，因此 `python -m expectation.dsl.mlir_gen.dialect.nn` 与 `python -m expectation.dsl.mlir_gen` 都不能通过。
  - [`test/dsl/ast/test_parser.py`](../../test/dsl/ast/test_parser.py) 的 helper call 黑盒回归当前也失败，说明这不只是 expectation 文案问题，而是 AST / mlir_gen 前端对公开 helper call 的支持尚未闭合。
- 终验说明：
  - 相比 2026-04-15 14:03 的终验，`symbol` family 与此前补齐的入口支撑资产已收口；当前阻断已收敛为 `nn` family 前端 / expectation 的单一失败面。
  - 由于本计划完成态要求 `expectation/dsl/mlir_gen` 全目录入口通过，且 `test/dsl/ast test/dsl/mlir_gen test/dsl/mlir_gen/emit test/tools/test_mlir_gen_compare.py` 同时通过，当前主仓仍不具备归档条件。

## 修复任务补建（2026-04-16 09:16 +0800）

- 补建人：`守护最好的爱莉希雅`
- 唯一继续项：[`T-20260416-505b3a01`](../../TODO.md)
- 任务类型：`build`
- `worktree`：`wt-20260416-dsl-mlir-gen-r4-fix`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/16/20260416-dsl-mlir-gen-r4-fix.md`
- 唯一修复范围：
  - 收口 [`expectation/dsl/mlir_gen/dialect/nn`](../../expectation/dsl/mlir_gen/dialect/nn) 当前目录级失败，使 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn` 重新通过。
  - 收口导致上述失败的前端 / 发射实现与必要测试，范围限于 [`kernel_gen/dsl/ast`](../../kernel_gen/dsl/ast)、[`kernel_gen/dsl/mlir_gen`](../../kernel_gen/dsl/mlir_gen)、[`kernel_gen/dsl/mlir_gen/emit`](../../kernel_gen/dsl/mlir_gen/emit)、[`test/dsl/ast`](../../test/dsl/ast)、[`test/dsl/mlir_gen`](../../test/dsl/mlir_gen)、[`test/dsl/mlir_gen/emit`](../../test/dsl/mlir_gen/emit)、[`test/tools/test_mlir_gen_compare.py`](../../test/tools/test_mlir_gen_compare.py) 与 [`expectation/dsl/mlir_gen`](../../expectation/dsl/mlir_gen) 中与 `nn` family 直接相关的资产。
  - 目标同时恢复 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen` 与 `pytest -q test/dsl/ast test/dsl/mlir_gen test/dsl/mlir_gen/emit test/tools/test_mlir_gen_compare.py`。
- 续推口径：
  - 当前不得创建归档任务，也不得执行 `-done-plan`。
  - 以 [`T-20260416-505b3a01`](../../TODO.md) 作为本轮唯一继续项；此前已完成的 `symbol/__main__/broadcast TLM` 修复链不再重复推进。
  - 待 [`T-20260415-b085f193`](../../TODO.md) 完成并回到本计划复核通过后，再进入归档链。

## 当前主仓终验（2026-04-16 00:07 +0800）

- 终验人：`守护最好的爱莉希雅`
- 当前结论：`不通过`
- 依据：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen` -> `exit=1`；当前仍在导入 [`expectation/dsl/mlir_gen/dialect/nn/broadcast.py`](../../expectation/dsl/mlir_gen/dialect/nn/broadcast.py) 时因旧 `MemorySpace.TLM` 口径失败：`AttributeError: TLM. Did you mean: 'LM'?`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.arch` -> `exit=0`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.symbol` -> `exit=1`；当前仍报 `dsl mlir_gen symbol.add expectation failed (1 cases): CASE-1: AstVisitorError: nn.add requires at least one nn.memory operand`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.dma` -> `exit=0`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn` -> `exit=1`；当前主仓仍缺 [`expectation/dsl/mlir_gen/dialect/nn/__main__.py`](../../expectation/dsl/mlir_gen/dialect/nn/__main__.py)，目录入口未闭合。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/ast test/dsl/mlir_gen test/dsl/mlir_gen/emit test/tools/test_mlir_gen_compare.py` -> `57 passed`。
- 最小阻断项：
  - [`expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py`](../../expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py) 的 `CASE-1` 仍未收口，`symbol.add` 场景还在误走 `nn.add` 路径。
  - [`expectation/dsl/mlir_gen/dialect/nn`](../../expectation/dsl/mlir_gen/dialect/nn) 目录入口仍未闭合；计划正文要求的 `python -m expectation.dsl.mlir_gen.dialect.nn` 当前无法直接执行。
  - 根目录入口 [`expectation/dsl/mlir_gen/__main__.py`](../../expectation/dsl/mlir_gen/__main__.py) 仍未恢复可执行；当前最先暴露的阻断是 [`expectation/dsl/mlir_gen/dialect/nn/broadcast.py`](../../expectation/dsl/mlir_gen/dialect/nn/broadcast.py) 仍引用已移除的 `MemorySpace.TLM`。
- 终验说明：
  - 当前主仓只满足 `arch/dma` 两个 family 入口与 `pytest` 测试层通过，尚未达到本计划完成态定义中的“根目录 expectation 入口通过 + `nn/symbol` family 入口可直接运行”。
  - 因此本计划当前仍不具备归档条件；需继续沿唯一修复任务收口上述三项剩余阻断。

## 修复任务补建（2026-04-16 00:07 +0800）

- 补建人：`守护最好的爱莉希雅`
- 修复任务：[`T-20260416-65613a5a`](../../TODO.md)
- 任务类型：`build`
- `worktree`：`wt-20260416-dsl-mlir-gen-r3-fix`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/16/20260416-dsl-mlir-gen-r3-fix.md`
- 唯一修复范围：
  - 收口 [`expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py`](../../expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py) 的 `CASE-1`，确保 `symbol.add` 不再误走 `nn.add` 路径。
  - 补齐 [`expectation/dsl/mlir_gen/dialect/nn/__main__.py`](../../expectation/dsl/mlir_gen/dialect/nn/__main__.py)，让 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn` 可直接执行。
  - 收口 [`expectation/dsl/mlir_gen/dialect/nn/broadcast.py`](../../expectation/dsl/mlir_gen/dialect/nn/broadcast.py) 中旧 `MemorySpace.TLM` 口径，恢复 [`expectation/dsl/mlir_gen/__main__.py`](../../expectation/dsl/mlir_gen/__main__.py) 的可执行性。
- 续推口径：
  - 当前不得创建归档任务，也不得执行 `-done-plan`。
  - 以 [`T-20260416-65613a5a`](../../TODO.md) 作为本轮唯一继续项；此前已完成的 [`T-20260415-b085f193`](../../TODO.md) 不再继续复用为续推任务。
  - 待 [`T-20260416-65613a5a`](../../TODO.md) 完成并回到本计划复核通过后，再进入归档链。

## 当前主仓终验复核（2026-04-16 00:19 +0800）

- 终验人：`大闸蟹`
- 当前结论：`不通过`
- 依据：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen` -> `exit=1`；当前仍在导入 [`expectation/dsl/mlir_gen/dialect/nn/broadcast.py`](../../expectation/dsl/mlir_gen/dialect/nn/broadcast.py) 时因旧 `MemorySpace.TLM` 口径失败：`AttributeError: TLM. Did you mean: 'LM'?`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.arch` -> `exit=0`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.symbol` -> `exit=1`；当前仍报 `dsl mlir_gen symbol.add expectation failed (1 cases): CASE-1: AstVisitorError: nn.add requires at least one nn.memory operand`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.dma` -> `exit=0`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn` -> `exit=1`；当前主仓仍缺 [`expectation/dsl/mlir_gen/dialect/nn/__main__.py`](../../expectation/dsl/mlir_gen/dialect/nn/__main__.py)，目录入口未闭合。
  - `pytest -q test/dsl/ast test/dsl/mlir_gen test/dsl/mlir_gen/emit test/tools/test_mlir_gen_compare.py` -> `57 passed`。
- 最小阻断项：
  - [`expectation/dsl/mlir_gen/dialect/nn/broadcast.py`](../../expectation/dsl/mlir_gen/dialect/nn/broadcast.py) 仍引用已移除的 `MemorySpace.TLM`，导致根目录入口 [`expectation/dsl/mlir_gen/__main__.py`](../../expectation/dsl/mlir_gen/__main__.py) 在 import 阶段即失败。
  - [`expectation/dsl/mlir_gen/dialect/nn`](../../expectation/dsl/mlir_gen/dialect/nn) 仍缺目录入口 `__main__.py`，计划正文要求的 `python -m expectation.dsl.mlir_gen.dialect.nn` 当前无法直接运行。
  - [`expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py`](../../expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py) 的 `CASE-1` 仍未收口，`symbol.add` 场景还在误走 `nn.add` 路径。
- 续推说明：
  - 当前 [`TODO.md`](../../TODO.md) 计划表已为 `10 | 9 | 1 | 进行中`，不再属于“完成待检查”状态。
  - 以 [`T-20260416-65613a5a`](../../TODO.md) 作为唯一继续项；当前不得补建归档任务，也不得执行 `-done-plan`。

## 当前主仓终验（2026-04-16 01:50 +0800）

- 终验人：`守护最好的爱莉希雅`
- 当前结论：`不通过`
- 依据：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen` -> `exit=1`；当前仍在导入 [`expectation/dsl/mlir_gen/dialect/nn/broadcast.py`](../../expectation/dsl/mlir_gen/dialect/nn/broadcast.py) 时因旧 `MemorySpace.TLM` 口径失败：`AttributeError: TLM. Did you mean: 'LM'?`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.arch` -> `exit=0`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.symbol` -> `exit=1`；当前仍报 `dsl mlir_gen symbol.add expectation failed (1 cases): CASE-1: AstVisitorError: nn.add requires at least one nn.memory operand`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.dma` -> `exit=0`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn` -> `exit=1`；当前主仓仍缺 [`expectation/dsl/mlir_gen/dialect/nn/__main__.py`](../../expectation/dsl/mlir_gen/dialect/nn/__main__.py)，目录入口未闭合。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/ast test/dsl/mlir_gen test/dsl/mlir_gen/emit test/tools/test_mlir_gen_compare.py` -> `57 passed`。
- 最小阻断项：
  - [`expectation/dsl/mlir_gen/dialect/nn/__main__.py`](../../expectation/dsl/mlir_gen/dialect/nn/__main__.py) 仍缺失，计划正文要求的 `python -m expectation.dsl.mlir_gen.dialect.nn` 当前无法直接执行。
  - [`expectation/dsl/mlir_gen/dialect/nn/broadcast.py`](../../expectation/dsl/mlir_gen/dialect/nn/broadcast.py) 仍引用已移除的 `MemorySpace.TLM`；同时 [`expectation/dsl/mlir_gen/dialect/nn/broadcast_to.py`](../../expectation/dsl/mlir_gen/dialect/nn/broadcast_to.py) 也仍保留同一旧口径，若只修前者，根入口后续仍会在 `broadcast_to` 同类路径再次失败。
  - [`expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py`](../../expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py) 的 `CASE-1` 仍未收口；当前应优先通过实现 / 测试收口 `symbol.add` 误走 `nn.add` 的问题，不应改写该 expectation 合同本身。
- 终验说明：
  - 尽管 [`T-20260416-65613a5a`](../../TODO.md) 已合入主仓，但当前主仓结果仍未达到本计划完成态定义中的“根目录 expectation 入口通过 + `arch/symbol/dma/nn` family 入口可直接运行 + pytest 职责域通过”。
  - 因此本计划当前仍`不通过`，且`不可进入归档链`。
  - 当前唯一继续项以 [`T-20260416-1cdb79f0`](../../TODO.md) 为准；其修复范围应以本节最小阻断项为准，至少收口 `nn/__main__.py`、`nn/{broadcast.py,broadcast_to.py}` 两处旧 `MemorySpace.TLM` 口径，以及 `symbol.add` 的实现 / 测试闭环，再回到本计划重新终验。

## 当前主仓终验复核（2026-04-16 01:49 +0800）

- 终验人：`大闸蟹`
- 当前结论：`不通过`
- 依据：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen` -> `exit=1`；当前仍在导入 [`expectation/dsl/mlir_gen/dialect/nn/broadcast.py`](../../expectation/dsl/mlir_gen/dialect/nn/broadcast.py) 时因旧 `MemorySpace.TLM` 口径失败：`AttributeError: TLM. Did you mean: 'LM'?`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.arch` -> `exit=0`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.symbol` -> `exit=1`；当前仍报 `dsl mlir_gen symbol.add expectation failed (1 cases): CASE-1: AstVisitorError: nn.add requires at least one nn.memory operand`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.dma` -> `exit=0`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn` -> `exit=1`；当前主仓仍缺 [`expectation/dsl/mlir_gen/dialect/nn/__main__.py`](../../expectation/dsl/mlir_gen/dialect/nn/__main__.py)，目录入口未闭合。
  - `pytest -q test/dsl/ast test/dsl/mlir_gen test/dsl/mlir_gen/emit test/tools/test_mlir_gen_compare.py` -> `57 passed`。
- 最小阻断项：
  - [`expectation/dsl/mlir_gen/dialect/nn/broadcast.py`](../../expectation/dsl/mlir_gen/dialect/nn/broadcast.py) 仍引用已移除的 `MemorySpace.TLM`，导致根目录入口 [`expectation/dsl/mlir_gen/__main__.py`](../../expectation/dsl/mlir_gen/__main__.py) 在 import 阶段即失败。
  - [`expectation/dsl/mlir_gen/dialect/nn`](../../expectation/dsl/mlir_gen/dialect/nn) 仍缺目录入口 `__main__.py`，计划正文要求的 `python -m expectation.dsl.mlir_gen.dialect.nn` 当前无法直接运行。
  - [`expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py`](../../expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py) 的 `CASE-1` 仍未收口，`symbol.add` 场景还在误走 `nn.add` 路径。
- 终验说明：
  - [`T-20260416-65613a5a`](../../TODO.md) 已合入主仓，但当前主仓结果与 `2026-04-16 00:19 +0800` 复核相比没有新增收口；阻断仍停留在 `nn.broadcast` 旧 `TLM`、`nn` 包入口缺失、`symbol.add` 误走 `nn.add` 三项。
  - 现阶段仍不满足本计划完成态定义中的“根目录 expectation 入口通过 + `nn/symbol` family 入口可直接运行”，因此不得进入归档链。
- 修复任务：[`T-20260416-1cdb79f0`](../../TODO.md)
- `worktree`：`wt-20260416-dsl-mlir-gen-r4-fix`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/16/20260416-dsl-mlir-gen-r4-fix.md`
- 修复范围：
  - 收口 [`expectation/dsl/mlir_gen/dialect/nn/broadcast.py`](../../expectation/dsl/mlir_gen/dialect/nn/broadcast.py) 中残留的旧 `MemorySpace.TLM` 口径，恢复根目录入口 [`expectation/dsl/mlir_gen/__main__.py`](../../expectation/dsl/mlir_gen/__main__.py) 的可执行性。
  - 补齐 [`expectation/dsl/mlir_gen/dialect/nn/__main__.py`](../../expectation/dsl/mlir_gen/dialect/nn/__main__.py)，让 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn` 可直接执行。
  - 收口 [`expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py`](../../expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py) 的 `CASE-1`，确保 `symbol.add` 不再误走 `nn.add` 路径。
- 续推说明：
  - 以 [`T-20260416-1cdb79f0`](../../TODO.md) 作为本轮唯一继续项；已完成的 [`T-20260416-65613a5a`](../../TODO.md) 不再继续复用。
  - 待 [`T-20260416-1cdb79f0`](../../TODO.md) 完成并回到本计划复核通过后，再进入归档链。

## 当前主仓终验复核（2026-04-16 09:18 +0800）

- 终验人：`大闸蟹`
- 当前结论：`不通过`
- 依据：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen` -> `exit=1`；当前根目录入口的失败已收敛到 `dialect.nn` family，`broadcast` / `broadcast_to` / `conv` / `fc` / `img2col1d` / `img2col2d` / `matmul` / `reduce_*` / `softmax` 仍分别报 `Unsupported annotation` 或 `Unsupported call expression`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.arch` -> `exit=0`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.symbol` -> `exit=0`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.dma` -> `exit=0`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn` -> `exit=1`；当前 `nn` 目录入口已存在，但 family 级用例仍有 `11` 组失败。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/ast test/dsl/mlir_gen test/dsl/mlir_gen/emit test/tools/test_mlir_gen_compare.py` -> `1 failed, 57 passed`；失败用例为 [`test/dsl/ast/test_parser.py`](../../test/dsl/ast/test_parser.py) 的 `test_parse_function_helper_call`，当前 `parse_function` 对 `from kernel_gen.operation.nn import relu` 后的 `relu(x)` 仍报 `AstParseError: Unsupported call expression`。
- 最小阻断项：
  - [`expectation/dsl/mlir_gen/dialect/nn`](../../expectation/dsl/mlir_gen/dialect/nn) 当前虽已补齐目录入口，但 family 级合同仍未收口，导致 [`expectation/dsl/mlir_gen/__main__.py`](../../expectation/dsl/mlir_gen/__main__.py) 仍不能直接通过。
  - 计划正文要求的 `pytest -q test/dsl/ast test/dsl/mlir_gen test/dsl/mlir_gen/emit test/tools/test_mlir_gen_compare.py` 当前仍未恢复通过；最先暴露的回归是 `helper import + unary nn call` 的 AST 解析路径未闭合。
- 终验说明：
  - 与 `2026-04-16 01:49 +0800` 相比，`arch/symbol/dma` 三个 family 入口已恢复通过，`symbol.add` 目录级合同也已收口；但 `nn` family 与 pytest 职责域仍未达到本计划完成态。
  - 因此本计划当前仍`不通过`，且`不可进入归档链`。
- 修复任务：[`T-20260416-505b3a01`](../../TODO.md)
- `worktree`：`wt-20260416-dsl-mlir-gen-r4-fix`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/16/20260416-dsl-mlir-gen-r4-fix.md`
- 修复范围：
  - 收口 [`expectation/dsl/mlir_gen/dialect/nn`](../../expectation/dsl/mlir_gen/dialect/nn) family 当前目录级失败，并恢复 [`expectation/dsl/mlir_gen/__main__.py`](../../expectation/dsl/mlir_gen/__main__.py) 的可执行性。
  - 一并收口 [`test/dsl/ast/test_parser.py`](../../test/dsl/ast/test_parser.py) 中 `test_parse_function_helper_call` 暴露的 imported helper call AST 解析回归，确保计划正文点名的 pytest 总验收恢复通过。
- 续推说明：
  - 已完成的 [`T-20260416-1cdb79f0`](../../TODO.md) 不再继续复用。
  - 以 [`T-20260416-505b3a01`](../../TODO.md) 作为本轮唯一继续项；待其完成并回到本计划复核通过后，再进入归档链。

## 当前主仓终验（2026-04-16 09:24 +0800）

- 终验人：`守护最好的爱莉希雅`
- 当前结论：`不通过`
- 依据：
  - 管理员已同步最新 merge 为 [`T-20260416-1cdb79f0`](../../TODO.md)，提交 `b07908d` 已进入主仓。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.arch` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.dma` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.symbol` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn` -> `exit=1`；当前仍为 `11` 组失败，集中在 `broadcast / broadcast_to / conv / fc / img2col1d / img2col2d / matmul / reduce_* / softmax` 的 `Unsupported annotation` / `Unsupported call expression`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen` -> `exit=1`；当前根目录入口唯一首个失败面仍为 `dialect.nn` family。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/ast test/dsl/mlir_gen test/dsl/mlir_gen/emit test/tools/test_mlir_gen_compare.py` -> `1 failed, 57 passed`；失败仍为 [`test/dsl/ast/test_parser.py`](../../test/dsl/ast/test_parser.py) 的 `test_parse_function_helper_call`，错误为 `AstParseError: Unsupported call expression`。
- 最小阻断项：
  - [`expectation/dsl/mlir_gen/dialect/nn`](../../expectation/dsl/mlir_gen/dialect/nn) family 当前目录级合同仍未收口，导致 [`expectation/dsl/mlir_gen/__main__.py`](../../expectation/dsl/mlir_gen/__main__.py) 继续失败。
  - imported helper call 的 AST 解析路径仍未闭合，`parse_function` 对 `from kernel_gen.operation.nn import relu` 后的 `relu(x)` 仍报 `Unsupported call expression`；这已直接挡住计划正文点名的 pytest 总验收。
- 终验说明：
  - 与 `2026-04-16 09:18 +0800` 的双架构复核相比，当前主仓结果没有新增收口；`arch / dma / symbol` 已通过，但 `nn` family 与 helper-call parser 回归仍未完成。
  - 因此本计划当前仍`不通过`，且`不可进入归档链`。
  - 本轮唯一继续项继续固定为 [`T-20260416-505b3a01`](../../TODO.md)；已完成的 [`T-20260416-1cdb79f0`](../../TODO.md) 不再继续复用。

## T-20260416-505b3a01 执行口径补充（2026-04-16 09:24 +0800）

- 补充人：`守护最好的爱莉希雅`
- 适用任务：[`T-20260416-505b3a01`](../../TODO.md)
- expectation 单次授权：
  - 允许执行人在本轮 `build` 中直接修改 [`expectation/dsl/mlir_gen/__main__.py`](../../expectation/dsl/mlir_gen/__main__.py)。
  - 允许直接修改 [`expectation/dsl/mlir_gen/dialect/nn/__main__.py`](../../expectation/dsl/mlir_gen/dialect/nn/__main__.py)。
  - 允许直接修改 [`expectation/dsl/mlir_gen/dialect/nn/broadcast.py`](../../expectation/dsl/mlir_gen/dialect/nn/broadcast.py)、[`expectation/dsl/mlir_gen/dialect/nn/broadcast_to.py`](../../expectation/dsl/mlir_gen/dialect/nn/broadcast_to.py)、[`expectation/dsl/mlir_gen/dialect/nn/conv.py`](../../expectation/dsl/mlir_gen/dialect/nn/conv.py)、[`expectation/dsl/mlir_gen/dialect/nn/fc.py`](../../expectation/dsl/mlir_gen/dialect/nn/fc.py)、[`expectation/dsl/mlir_gen/dialect/nn/img2col1d.py`](../../expectation/dsl/mlir_gen/dialect/nn/img2col1d.py)、[`expectation/dsl/mlir_gen/dialect/nn/img2col2d.py`](../../expectation/dsl/mlir_gen/dialect/nn/img2col2d.py)、[`expectation/dsl/mlir_gen/dialect/nn/matmul.py`](../../expectation/dsl/mlir_gen/dialect/nn/matmul.py)、[`expectation/dsl/mlir_gen/dialect/nn/softmax.py`](../../expectation/dsl/mlir_gen/dialect/nn/softmax.py)。
  - 允许直接修改 [`expectation/dsl/mlir_gen/dialect/nn/reduce/__main__.py`](../../expectation/dsl/mlir_gen/dialect/nn/reduce/__main__.py)、[`expectation/dsl/mlir_gen/dialect/nn/reduce/_shared.py`](../../expectation/dsl/mlir_gen/dialect/nn/reduce/_shared.py)、[`expectation/dsl/mlir_gen/dialect/nn/reduce/reduce_max.py`](../../expectation/dsl/mlir_gen/dialect/nn/reduce/reduce_max.py)、[`expectation/dsl/mlir_gen/dialect/nn/reduce/reduce_min.py`](../../expectation/dsl/mlir_gen/dialect/nn/reduce/reduce_min.py)、[`expectation/dsl/mlir_gen/dialect/nn/reduce/reduce_sum.py`](../../expectation/dsl/mlir_gen/dialect/nn/reduce/reduce_sum.py)。
- 实现 / 测试续接口径：
  - 本轮不再把实现与测试收口限定到更小子目录；凡是为收口 `nn` family 目录级失败与 `test_parse_function_helper_call` 所必需的直接相关实现 / 测试文件，执行人可在当前任务内继续调整。
  - 若 expectation 合同与实现不一致，且问题不是包入口、依赖缺失、聚合入口脚本等 expectation 侧专属原因，应优先收口实现 / 测试，不把现有 expectation 语义直接回退成旧实现行为。
- 限制：
  - 本轮不改 [`expectation/dsl/mlir_gen/dialect/symbol`](../../expectation/dsl/mlir_gen/dialect/symbol)、[`expectation/dsl/mlir_gen/dialect/arch`](../../expectation/dsl/mlir_gen/dialect/arch)、[`expectation/dsl/mlir_gen/dialect/dma`](../../expectation/dsl/mlir_gen/dialect/dma) 与其他无关 expectation 资产。
  - 本轮不改计划书以外的 `spec`、`agents`、配置文件，也不处理归档链动作。
  - 若修复过程中暴露新的 expectation 问题且不在上述授权路径内，先写任务记录，再回到架构侧确认。

## 当前主仓终验（2026-04-16 10:30 +0800）

- 终验人：`守护最好的爱莉希雅`
- 当前结论：`不通过`
- 依据：
  - 管理员已同步最新 merge 为 [`T-20260416-505b3a01`](../../TODO.md)，提交 `acdef92` 已进入主仓。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.arch` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.symbol` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.dma` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn` -> `exit=1`；当前仍为 `11` 组失败，集中在 `broadcast / broadcast_to / conv / fc / img2col1d / img2col2d / matmul / reduce_* / softmax` 的 `Unsupported annotation` 或 `Unsupported call expression`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen` -> `exit=1`；根目录入口当前唯一首个失败面仍为 `dialect.nn` family。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/ast test/dsl/mlir_gen test/dsl/mlir_gen/emit test/tools/test_mlir_gen_compare.py` -> `1 failed, 57 passed`；失败仍为 [`test/dsl/ast/test_parser.py`](../../test/dsl/ast/test_parser.py) 的 `test_parse_function_helper_call`，错误为 `AstParseError: Unsupported call expression`。
- 最小阻断项：
  - [`expectation/dsl/mlir_gen/dialect/nn`](../../expectation/dsl/mlir_gen/dialect/nn) family 当前目录级合同仍未收口，导致 [`expectation/dsl/mlir_gen/__main__.py`](../../expectation/dsl/mlir_gen/__main__.py) 继续失败。
  - imported helper call 的 AST 解析路径仍未闭合，`parse_function` 对 `from kernel_gen.operation.nn import relu` 后的 `relu(x)` 仍报 `Unsupported call expression`；这直接挡住计划正文点名的 pytest 总验收。
- 终验说明：
  - 与 `2026-04-16 09:24 +0800` 相比，`acdef92` 合入后主仓没有新增收口；当前仍只满足 `arch / dma / symbol` 三个 family 入口通过。
  - 因此本计划当前仍`不通过`，且`不可进入归档链`。
- 唯一继续项：
  - 保留 [`T-20260416-b4cf037d`](../../TODO.md) 作为当前唯一修复任务；其任务目标与当前最小阻断项一致，继续收口 `nn` family 当前目录级失败与 helper-call parser 回归。
  - 已完成的 [`T-20260416-505b3a01`](../../TODO.md) 不再继续复用；当前不得创建归档任务，也不得执行 `-done-plan`。

## 当前主仓终验复核（2026-04-16 10:29 +0800）

- 终验人：`大闸蟹`
- 当前结论：`不通过`
- 依据：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen` -> `exit=1`；当前根目录入口的失败仍收敛在 `dialect.nn` family，`broadcast` / `broadcast_to` / `conv` / `fc` / `img2col1d` / `img2col2d` / `matmul` / `reduce_*` / `softmax` 仍分别报 `Unsupported annotation` 或 `Unsupported call expression`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.arch` -> `exit=0`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.symbol` -> `exit=0`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.dma` -> `exit=0`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn` -> `exit=1`；当前 `nn` family 仍有 `11` 组失败。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/ast test/dsl/mlir_gen test/dsl/mlir_gen/emit test/tools/test_mlir_gen_compare.py` -> `1 failed, 57 passed`；失败用例仍为 [`test/dsl/ast/test_parser.py`](../../test/dsl/ast/test_parser.py) 的 `test_parse_function_helper_call`，`parse_function` 对 `from kernel_gen.operation.nn import relu` 后的 `relu(x)` 仍报 `AstParseError: Unsupported call expression`。
- 最小阻断项：
  - [`expectation/dsl/mlir_gen/dialect/nn`](../../expectation/dsl/mlir_gen/dialect/nn) family 当前目录级合同仍未收口，导致 [`expectation/dsl/mlir_gen/__main__.py`](../../expectation/dsl/mlir_gen/__main__.py) 继续失败。
  - 计划正文点名的 `pytest -q test/dsl/ast test/dsl/mlir_gen test/dsl/mlir_gen/emit test/tools/test_mlir_gen_compare.py` 仍未恢复通过；当前直接阻断项是 imported helper call 的 AST 解析路径未闭合。
- 终验说明：
  - 尽管 [`T-20260416-505b3a01`](../../DONE.md) 已合入主仓，但当前主仓结果与 `2026-04-16 09:24 +0800` 相比没有新增收口；`arch / dma / symbol` 已通过，`nn` family 与 helper-call parser 回归仍未完成。
  - 因此本计划当前仍`不通过`，且`不可进入归档链`。
- 修复任务：[`T-20260416-b4cf037d`](../../TODO.md)
- `worktree`：`wt-20260416-dsl-mlir-gen-r5-fix`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/16/20260416-dsl-mlir-gen-r5-fix.md`
- 修复范围：
  - 收口 [`expectation/dsl/mlir_gen/dialect/nn`](../../expectation/dsl/mlir_gen/dialect/nn) family 当前目录级失败，并恢复 [`expectation/dsl/mlir_gen/__main__.py`](../../expectation/dsl/mlir_gen/__main__.py) 的可执行性。
  - 一并修复 [`test/dsl/ast/test_parser.py`](../../test/dsl/ast/test_parser.py) 中 `test_parse_function_helper_call` 暴露的 imported helper call parser 回归，恢复计划正文点名的 pytest 总验收。
- 续推说明：
  - 已完成的 [`T-20260416-505b3a01`](../../DONE.md) 不再继续复用。
  - 以 [`T-20260416-b4cf037d`](../../TODO.md) 作为本轮唯一继续项；待其完成并回到本计划复核通过后，再进入归档链。

## 当前主仓终验复核（2026-04-16 14:10 +0800）

- 终验人：`大闸蟹`
- 当前结论：`不通过`
- 依据：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen` -> `exit=1`；当前根目录入口仍收敛到 `dialect.nn` family 失败，`broadcast` / `broadcast_to` / `conv` / `fc` / `img2col1d` / `img2col2d` / `matmul` / `reduce_*` / `softmax` 仍分别报 `Unsupported annotation` 或 `Unsupported call expression`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.arch` -> `exit=0`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.symbol` -> `exit=0`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.dma` -> `exit=0`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn` -> `exit=1`；当前 `nn` family 仍有 `11` 组失败。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/ast test/dsl/mlir_gen test/dsl/mlir_gen/emit test/tools/test_mlir_gen_compare.py` -> `1 failed, 57 passed`；失败用例仍为 [`test/dsl/ast/test_parser.py`](../../test/dsl/ast/test_parser.py) 的 `test_parse_function_helper_call`，`parse_function` 对 `from kernel_gen.operation.nn import relu` 后的 `relu(x)` 仍报 `AstParseError: Unsupported call expression`。
- 最小阻断项：
  - [`expectation/dsl/mlir_gen/dialect/nn`](../../expectation/dsl/mlir_gen/dialect/nn) family 当前目录级合同仍未收口，导致 [`expectation/dsl/mlir_gen/__main__.py`](../../expectation/dsl/mlir_gen/__main__.py) 继续失败。
  - 计划正文点名的 `pytest -q test/dsl/ast test/dsl/mlir_gen test/dsl/mlir_gen/emit test/tools/test_mlir_gen_compare.py` 仍未恢复通过；当前直接阻断项仍是 imported helper call 的 AST 解析路径未闭合。
- 终验说明：
  - 尽管 [`T-20260416-b4cf037d`](../../DONE.md) 已合入主仓，当前主仓结果与 `2026-04-16 10:30 +0800` / `2026-04-16 10:29 +0800` 相比没有新增收口；`arch / dma / symbol` 已通过，`nn` family 与 helper-call parser 回归仍未完成。
  - 因此本计划当前仍`不通过`，且`不可进入归档链`。
- 唯一继续项：
  - 保留 [`T-20260416-25981558`](../../TODO.md) 作为当前唯一修复任务；其任务目标与当前最小阻断项一致，继续收口 `nn` family 当前目录级失败与 helper-call parser 回归。
  - 已完成的 [`T-20260416-b4cf037d`](../../DONE.md) 不再继续复用；当前不得创建归档任务，也不得执行 `-done-plan`。

## 当前主仓终验（2026-04-16 14:10 +0800）

- 终验人：`守护最好的爱莉希雅`
- 当前结论：`不通过`
- 依据：
  - 管理员已同步最新 merge 为 `T-20260416-b4cf037d`，提交 `e81c544` 已进入主仓。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.arch` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.symbol` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.dma` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn` -> `exit=1`；当前仍为 `11` 组失败，集中在 `broadcast / broadcast_to / conv / fc / img2col1d / img2col2d / matmul / reduce_* / softmax` 的 `Unsupported annotation` 或 `Unsupported call expression`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen` -> `exit=1`；根目录入口当前唯一首个失败面仍为 `dialect.nn` family。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/ast test/dsl/mlir_gen test/dsl/mlir_gen/emit test/tools/test_mlir_gen_compare.py` -> `1 failed, 57 passed`；失败仍为 [`test/dsl/ast/test_parser.py`](../../test/dsl/ast/test_parser.py) 的 `test_parse_function_helper_call`，错误为 `AstParseError: Unsupported call expression`。
- 最小阻断项：
  - [`expectation/dsl/mlir_gen/dialect/nn`](../../expectation/dsl/mlir_gen/dialect/nn) family 当前目录级合同仍未收口，导致 [`expectation/dsl/mlir_gen/__main__.py`](../../expectation/dsl/mlir_gen/__main__.py) 继续失败。
  - imported helper call 的 AST 解析路径仍未闭合，`parse_function` 对 `from kernel_gen.operation.nn import relu` 后的 `relu(x)` 仍报 `Unsupported call expression`；这直接挡住计划正文点名的 pytest 总验收。
- 终验说明：
  - 与 `2026-04-16 10:30 +0800` 相比，`e81c544` 合入后主仓没有新增收口；当前仍只满足 `arch / dma / symbol` 三个 family 入口通过。
  - 因此本计划当前仍`不通过`，且`不可进入归档链`。
- 唯一继续项：
  - 新补建 [`T-20260416-25981558`](../../TODO.md) 作为当前唯一修复任务；任务目标继续收口 `nn` family 当前目录级失败与 helper-call parser 回归。
  - 已完成的 `T-20260416-b4cf037d` 不再继续复用；当前不得创建归档任务，也不得执行 `-done-plan`。

## 当前主仓终验复核（2026-04-16 17:00 +0800）

- 终验人：`大闸蟹`
- 当前结论：`不通过`
- 依据：
  - 管理员已同步 [`T-20260416-25981558`](../../DONE.md) 由李白合入主仓并 `-done`，提交为 `3d8524b`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen` -> `exit=1`；当前根目录入口仍收敛到 `dialect.nn` family 失败。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn` -> `exit=1`；当前 `nn` family 仍有 `11` 组失败，分布在 `broadcast / broadcast_to / conv / fc / img2col1d / img2col2d / matmul / reduce_* / softmax`，错误仍为 `Unsupported annotation`、`Unsupported call expression` 或同源断言失败。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/ast test/dsl/mlir_gen test/dsl/mlir_gen/emit test/tools/test_mlir_gen_compare.py` -> `1 failed, 57 passed`；失败用例仍为 [`test/dsl/ast/test_parser.py`](../../test/dsl/ast/test_parser.py) 的 `test_parse_function_helper_call`，`parse_function` 对 `from kernel_gen.operation.nn import relu` 后的 `relu(x)` 仍报 `AstParseError: Unsupported call expression`。
- 最小阻断项：
  - [`expectation/dsl/mlir_gen/dialect/nn`](../../expectation/dsl/mlir_gen/dialect/nn) family 当前目录级合同仍未收口，导致 [`expectation/dsl/mlir_gen/__main__.py`](../../expectation/dsl/mlir_gen/__main__.py) 继续失败。
  - imported helper call 的 AST 解析路径仍未闭合，计划正文点名的 pytest 总验收仍被 [`test/dsl/ast/test_parser.py`](../../test/dsl/ast/test_parser.py) 的 `test_parse_function_helper_call` 挡住。
- 终验说明：
  - 尽管 [`T-20260416-25981558`](../../DONE.md) 已合入主仓，当前主仓与 `2026-04-16 14:10 +0800` 相比没有新增收口；`arch / dma / symbol` 已通过，但 `nn` family 与 helper-call parser 回归仍未完成。
  - 因此本计划当前仍`不通过`，且`不可进入归档链`。
- 修复任务：[`T-20260416-16fcb9bf`](../../TODO.md)
- `worktree`：`wt-20260416-dsl-mlir-gen-r7-fix`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/16/20260416-dsl-mlir-gen-r7-fix.md`
- 修复范围：
  - 收口 [`expectation/dsl/mlir_gen/dialect/nn`](../../expectation/dsl/mlir_gen/dialect/nn) family 当前目录级失败，并恢复 [`expectation/dsl/mlir_gen/__main__.py`](../../expectation/dsl/mlir_gen/__main__.py) 的可执行性。
  - 一并修复 [`test/dsl/ast/test_parser.py`](../../test/dsl/ast/test_parser.py) 中 `test_parse_function_helper_call` 暴露的 imported helper call parser 回归，恢复计划正文点名的 pytest 总验收。
- 续推说明：
  - 已完成的 [`T-20260416-25981558`](../../DONE.md) 不再继续复用。
  - 以 [`T-20260416-16fcb9bf`](../../TODO.md) 作为本轮唯一继续项；待其完成并回到本计划复核通过后，再判断是否具备归档链条件。

## 当前主仓终验复核（2026-04-16 17:31 +0800）

- 终验人：`大闸蟹`
- 当前结论：`不通过`
- 依据：
  - 管理员已同步 [`T-20260416-16fcb9bf`](../../DONE.md) 由李白合入主仓并 `-done`，提交为 `17:26` 时段进入主仓。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen` -> `exit=1`；当前根目录入口仍收敛到 `dialect.nn` family 失败。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn` -> `exit=1`；当前 `nn` family 仍有 `11` 组失败，分布在 `broadcast / broadcast_to / conv / fc / img2col1d / img2col2d / matmul / reduce_* / softmax`，错误仍为 `Unsupported annotation`、`Unsupported call expression` 或同源断言失败。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/ast test/dsl/mlir_gen test/dsl/mlir_gen/emit test/tools/test_mlir_gen_compare.py` -> `1 failed, 57 passed`；失败用例仍为 [`test/dsl/ast/test_parser.py`](../../test/dsl/ast/test_parser.py) 的 `test_parse_function_helper_call`，`parse_function` 对 `from kernel_gen.operation.nn import relu` 后的 `relu(x)` 仍报 `AstParseError: Unsupported call expression`。
  - 当前 [`TODO.md`](../../TODO.md) 已从 `15 / 15 / 0 / 完成待检查` 回退为 `16 / 15 / 1 / 进行中`，说明本轮终验未通过且已补建新的继续项。
- 最小阻断项：
  - [`expectation/dsl/mlir_gen/dialect/nn`](../../expectation/dsl/mlir_gen/dialect/nn) family 当前目录级合同仍未收口，导致 [`expectation/dsl/mlir_gen/__main__.py`](../../expectation/dsl/mlir_gen/__main__.py) 继续失败。
  - imported helper call 的 AST 解析路径仍未闭合，计划正文点名的 pytest 总验收仍被 [`test/dsl/ast/test_parser.py`](../../test/dsl/ast/test_parser.py) 的 `test_parse_function_helper_call` 挡住。
- 终验说明：
  - 尽管 [`T-20260416-16fcb9bf`](../../DONE.md) 已合入主仓，当前主仓与 `2026-04-16 17:00 +0800` 相比没有新增收口；`arch / dma / symbol` 已通过，但 `nn` family 与 helper-call parser 回归仍未完成。
  - 因此本计划当前仍`不通过`，且`不可进入归档链`。
- 修复任务：[`T-20260416-d7591ac6`](../../TODO.md)
- `worktree`：`wt-20260416-dsl-mlir-gen-r8-fix`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/16/20260416-dsl-mlir-gen-r8-fix.md`
- 修复范围：
  - 收口 [`expectation/dsl/mlir_gen/dialect/nn`](../../expectation/dsl/mlir_gen/dialect/nn) family 当前目录级失败，并恢复 [`expectation/dsl/mlir_gen/__main__.py`](../../expectation/dsl/mlir_gen/__main__.py) 的可执行性。
  - 一并修复 [`test/dsl/ast/test_parser.py`](../../test/dsl/ast/test_parser.py) 中 `test_parse_function_helper_call` 暴露的 imported helper call parser 回归，恢复计划正文点名的 pytest 总验收。
- 续推说明：
  - 已完成的 [`T-20260416-16fcb9bf`](../../DONE.md) 不再继续复用。
  - 以 [`T-20260416-d7591ac6`](../../TODO.md) 作为本轮唯一继续项；待其完成并回到本计划复核通过后，再判断是否具备归档链条件。

## 当前主仓终验复核（2026-04-16 19:17 +0800）

- 终验人：`大闸蟹`
- 当前结论：`不通过`
- 依据：
  - 管理员已同步 [`T-20260416-d7591ac6`](../../DONE.md) 由李白合入主仓并 `-done`，完成时间为 `2026-04-16 19:15:10 +0800`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen` -> `exit=1`；当前根目录入口仍收敛到 `dialect.nn` family 失败。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn` -> `exit=1`；当前 `nn` family 仍有 `11` 组失败，分布在 `broadcast / broadcast_to / conv / fc / img2col1d / img2col2d / matmul / reduce_* / softmax`，错误仍为 `Unsupported annotation`、`Unsupported call expression` 或同源断言失败。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/ast test/dsl/mlir_gen test/dsl/mlir_gen/emit test/tools/test_mlir_gen_compare.py` -> `1 failed, 57 passed`；失败用例仍为 [`test/dsl/ast/test_parser.py`](../../test/dsl/ast/test_parser.py) 的 `test_parse_function_helper_call`，`parse_function` 对 `from kernel_gen.operation.nn import relu` 后的 `relu(x)` 仍报 `AstParseError: Unsupported call expression`。
  - 当前 [`TODO.md`](../../TODO.md) 已从 `16 / 16 / 0 / 完成待检查` 回退为 `17 / 16 / 1 / 进行中`，说明本轮终验未通过且已补建新的继续项。
- 最小阻断项：
  - [`expectation/dsl/mlir_gen/dialect/nn`](../../expectation/dsl/mlir_gen/dialect/nn) family 当前目录级合同仍未收口，导致 [`expectation/dsl/mlir_gen/__main__.py`](../../expectation/dsl/mlir_gen/__main__.py) 继续失败。
  - imported helper call 的 AST 解析路径仍未闭合，计划正文点名的 pytest 总验收仍被 [`test/dsl/ast/test_parser.py`](../../test/dsl/ast/test_parser.py) 的 `test_parse_function_helper_call` 挡住。
- 终验说明：
  - 尽管 [`T-20260416-d7591ac6`](../../DONE.md) 已合入主仓，当前主仓与 `2026-04-16 17:31 +0800` 相比没有新增收口；`arch / dma / symbol` 已通过，但 `nn` family 与 helper-call parser 回归仍未完成。
  - 因此本计划当前仍`不通过`，且`不可进入归档链`。
- 修复任务：[`T-20260416-9a89b3e4`](../../TODO.md)
- `worktree`：`wt-20260416-dsl-mlir-gen-r9-fix`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/16/20260416-dsl-mlir-gen-r9-fix.md`
- 修复范围：
  - 收口 [`expectation/dsl/mlir_gen/dialect/nn`](../../expectation/dsl/mlir_gen/dialect/nn) family 当前目录级失败，并恢复 [`expectation/dsl/mlir_gen/__main__.py`](../../expectation/dsl/mlir_gen/__main__.py) 的可执行性。
  - 一并修复 [`test/dsl/ast/test_parser.py`](../../test/dsl/ast/test_parser.py) 中 `test_parse_function_helper_call` 暴露的 imported helper call parser 回归，恢复计划正文点名的 pytest 总验收。
- 续推说明：
  - 已完成的 [`T-20260416-d7591ac6`](../../DONE.md) 不再继续复用。
  - 以 [`T-20260416-9a89b3e4`](../../TODO.md) 作为本轮唯一继续项；待其完成并回到本计划复核通过后，再判断是否具备归档链条件。

## 当前主仓终验（2026-04-16 19:18 +0800）

- 终验人：`守护最好的爱莉希雅`
- 当前结论：`不通过`
- 依据：
  - 管理员已同步 [`T-20260416-d7591ac6`](../../DONE.md) 由李白合入主仓并 `-done`，提交为 `eee73d5`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen` -> `exit=1`；当前根目录入口仍收敛到 `dialect.nn` family 失败。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.arch` -> `exit=0`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.symbol` -> `exit=0`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.dma` -> `exit=0`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn` -> `exit=1`；当前仍为 `11` 组失败，集中在 `broadcast / broadcast_to / conv / fc / img2col1d / img2col2d / matmul / reduce_* / softmax` 的 `Unsupported annotation`、`Unsupported call expression` 或同源断言失败。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/ast test/dsl/mlir_gen test/dsl/mlir_gen/emit test/tools/test_mlir_gen_compare.py` -> `1 failed, 57 passed`；失败仍为 [`test/dsl/ast/test_parser.py`](../../test/dsl/ast/test_parser.py) 的 `test_parse_function_helper_call`，错误为 `AstParseError: Unsupported call expression`。
- 最小阻断项：
  - [`expectation/dsl/mlir_gen/dialect/nn`](../../expectation/dsl/mlir_gen/dialect/nn) family 当前目录级合同仍未收口，导致 [`expectation/dsl/mlir_gen/__main__.py`](../../expectation/dsl/mlir_gen/__main__.py) 继续失败。
  - imported helper call 的 AST 解析路径仍未闭合，计划正文点名的 pytest 总验收仍被 [`test/dsl/ast/test_parser.py`](../../test/dsl/ast/test_parser.py) 的 `test_parse_function_helper_call` 挡住。
- 终验说明：
  - 尽管 [`T-20260416-d7591ac6`](../../DONE.md) 已合入主仓，且 merge 回报写有“最新 main 已收口 nn family 目录入口、根目录入口与 imported helper call parser 路径”，但我在当前根目录主仓复跑得到的结果与该回报不一致；以当前可复核的主仓现场为准，本轮没有新增收口。
  - 当前 [`TODO.md`](../../TODO.md) 已不再是 `16 / 16 / 0 / 完成待检查`，而是 `17 / 16 / 1 / 进行中`。
  - 因此本计划当前仍`不通过`，且`不可进入归档链`。
- 唯一继续项：
  - 保留 [`T-20260416-9a89b3e4`](../../TODO.md) 作为当前唯一修复任务；任务目标继续收口 `nn` family 当前目录级失败与 imported helper call parser 回归。
  - 已完成的 [`T-20260416-d7591ac6`](../../DONE.md) 不再继续复用；当前不得创建归档任务，也不得执行 `-done-plan`。

## 当前主仓终验复核（2026-04-16 19:37 +0800）

- 终验人：`大闸蟹`
- 当前结论：`不通过`
- 依据：
  - 管理员已同步 [`T-20260416-9a89b3e4`](../../DONE.md) 由李白合入主仓并 `-done`；按管理员口径，对应提交为 `8f20a27`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen` -> `exit=1`；当前根目录入口仍收敛到 `dialect.nn` family 失败。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn` -> `exit=1`；当前 `nn` family 仍有 `11` 组失败，分布在 `broadcast / broadcast_to / conv / fc / img2col1d / img2col2d / matmul / reduce_* / softmax`，错误仍为 `Unsupported annotation`、`Unsupported call expression` 或同源断言失败。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/ast test/dsl/mlir_gen test/dsl/mlir_gen/emit test/tools/test_mlir_gen_compare.py` -> `1 failed, 57 passed`；失败用例仍为 [`test/dsl/ast/test_parser.py`](../../test/dsl/ast/test_parser.py) 的 `test_parse_function_helper_call`，`parse_function` 对 `from kernel_gen.operation.nn import relu` 后的 `relu(x)` 仍报 `AstParseError: Unsupported call expression`。
  - 当前 [`TODO.md`](../../TODO.md) 已从 `17 / 17 / 0 / 完成待检查` 回退为 `18 / 17 / 1 / 进行中`，说明本轮终验未通过且已补建新的继续项。
- 最小阻断项：
  - [`expectation/dsl/mlir_gen/dialect/nn`](../../expectation/dsl/mlir_gen/dialect/nn) family 当前目录级合同仍未收口，导致 [`expectation/dsl/mlir_gen/__main__.py`](../../expectation/dsl/mlir_gen/__main__.py) 继续失败。
  - imported helper call 的 AST 解析路径仍未闭合，计划正文点名的 pytest 总验收仍被 [`test/dsl/ast/test_parser.py`](../../test/dsl/ast/test_parser.py) 的 `test_parse_function_helper_call` 挡住。
- 终验说明：
  - 尽管 [`T-20260416-9a89b3e4`](../../DONE.md) 已合入主仓，当前主仓与 `2026-04-16 19:17 +0800` / `2026-04-16 19:18 +0800` 相比没有新增收口；`arch / dma / symbol` 已通过，但 `nn` family 与 helper-call parser 回归仍未完成。
  - 因此本计划当前仍`不通过`，且`不可进入归档链`。
- 修复任务：[`T-20260416-08225f2f`](../../TODO.md)
- `worktree`：`wt-20260416-dsl-mlir-gen-r10-fix`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/16/20260416-dsl-mlir-gen-r10-fix.md`
- 修复范围：
  - 收口 [`expectation/dsl/mlir_gen/dialect/nn`](../../expectation/dsl/mlir_gen/dialect/nn) family 当前目录级失败，并恢复 [`expectation/dsl/mlir_gen/__main__.py`](../../expectation/dsl/mlir_gen/__main__.py) 的可执行性。
  - 一并修复 [`test/dsl/ast/test_parser.py`](../../test/dsl/ast/test_parser.py) 中 `test_parse_function_helper_call` 暴露的 imported helper call parser 回归，恢复计划正文点名的 pytest 总验收。
- 续推说明：
  - 已完成的 [`T-20260416-9a89b3e4`](../../DONE.md) 不再继续复用。
  - 以 [`T-20260416-08225f2f`](../../TODO.md) 作为本轮唯一继续项；待其完成并回到本计划复核通过后，再判断是否具备归档链条件。

## 当前主仓终验（2026-04-16 19:38 +0800）

- 终验人：`守护最好的爱莉希雅`
- 当前结论：`不通过`
- 归档结论：`不可进入归档链`
- 当前主仓实跑：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen` -> `exit=1`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.arch` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.symbol` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.dma` -> `exit=0`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn` -> `exit=1`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/ast test/dsl/mlir_gen test/dsl/mlir_gen/emit test/tools/test_mlir_gen_compare.py` -> `1 failed, 57 passed`
- 最小阻断项：
  - [`expectation/dsl/mlir_gen/dialect/nn`](../../expectation/dsl/mlir_gen/dialect/nn) family 当前目录级合同仍未收口；当前 `broadcast / broadcast_to / conv / fc / img2col1d / img2col2d / matmul / reduce_* / softmax` 仍分别报 `Unsupported annotation`、`Unsupported call expression` 或同源断言失败，导致 [`expectation/dsl/mlir_gen/__main__.py`](../../expectation/dsl/mlir_gen/__main__.py) 继续失败。
  - imported helper call 的 AST 解析路径仍未闭合；计划正文点名的 pytest 总验收仍被 [`test/dsl/ast/test_parser.py`](../../test/dsl/ast/test_parser.py) 的 `test_parse_function_helper_call` 挡住，错误仍为 `AstParseError: Unsupported call expression`。
- 终验说明：
  - 尽管 [`T-20260416-9a89b3e4`](../../DONE.md) 已由李白合入主仓并回报提交 `8f20a27`，且回报声称“本轮业务文件相对 origin/main 无差异，仅提交当前任务记录文件”，我在当前根目录主仓复跑得到的结果与“自然收口”口径不一致；以当前可复核的主仓现场为准，本轮没有新增收口。
  - 当前 [`TODO.md`](../../TODO.md) 已不再是 `17 / 17 / 0 / 完成待检查`，而是 `18 / 17 / 1 / 进行中`。
  - 因此本计划当前仍`不通过`，且`不可进入归档链`。
- 唯一继续项：
  - 保留 [`T-20260416-08225f2f`](../../TODO.md) 作为当前唯一修复任务。
  - 已完成的 [`T-20260416-9a89b3e4`](../../DONE.md) 不再继续复用；当前不得创建归档任务，也不得执行 `-done-plan`。

## 当前主仓终验复核（2026-04-16 21:23 +0800）

- 终验人：`大闸蟹`
- 当前结论：`通过`
- 归档结论：`可进入归档链`
- 验证基线：
  - 以同步现场 ` /home/lfr/kernelcode_generate/wt-20260416-dsl-mlir-gen-r10-fix ` 为准；对应记录见 [`agents/codex-multi-agents/log/task_records/2026/16/20260416-dsl-mlir-gen-r10-fix.md`](../../agents/codex-multi-agents/log/task_records/2026/16/20260416-dsl-mlir-gen-r10-fix.md)。
  - 该记录在 `2026-04-16 19:43 +0800` 已写明：当前 worktree 与最新主线 `HEAD...origin/main = 0 0`，相关业务路径相对 `origin/main` 无差异。
  - 同一记录已写明以下终验在该同步现场全部通过：
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn` -> `exit 0`
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen` -> `exit 0`
    - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/ast/test_parser.py -k test_parse_function_helper_call -vv` -> `1 passed, 5 deselected`
    - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/ast test/dsl/mlir_gen test/dsl/mlir_gen/emit test/tools/test_mlir_gen_compare.py` -> `59 passed`
  - 管理员已同步 [`T-20260416-08225f2f`](../../DONE.md) 由李白合入主仓并推送，提交为 `3587654`；该 merge 只继续带入同链记录，与上述同步现场结论一致。
- 终验说明：
  - 先前根目录主仓工作目录出现的 `expectation.dsl.mlir_gen` / `dialect.nn` 失败，不再单独作为功能阻断；若与上述同步现场不一致，只记为现场状态差异。
  - 因此，本计划应以“最新同步现场的 `nn family` 目录入口、根入口与 parser 总验收均已通过”为准，不再继续保留修复任务。
- 当前状态：
  - [`T-20260416-08225f2f`](../../DONE.md) 已完成并停用，不再续接。
  - 管理员可按归档流程补建唯一归档任务，再执行后续归档动作。

## 当前主仓终验复核（2026-04-16 21:41 +0800）

- 终验人：`守护最好的爱莉希雅`
- 当前结论：`通过`
- 归档结论：`可进入归档链`
- 验证基线：
  - 以最新同步现场 `/home/lfr/kernelcode_generate/wt-20260416-dsl-mlir-gen-r10-fix` 为主基线；对应记录见 [`agents/codex-multi-agents/log/task_records/2026/16/20260416-dsl-mlir-gen-r10-fix.md`](../../agents/codex-multi-agents/log/task_records/2026/16/20260416-dsl-mlir-gen-r10-fix.md)。
  - 该记录已写明：`2026-04-16 19:43 +0800` 在同步现场复核时，`HEAD...origin/main = 0 0`，相关业务路径相对 `origin/main` 无差异，且 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn`、`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen`、`pytest -q test/dsl/ast/test_parser.py -k test_parse_function_helper_call -vv`、`pytest -q test/dsl/ast test/dsl/mlir_gen test/dsl/mlir_gen/emit test/tools/test_mlir_gen_compare.py` 均已通过。
  - 管理员已同步 [`T-20260416-08225f2f`](../../DONE.md) 由李白合入主仓并推送，提交为 `3587654`；该 merge 仅继续带入同链记录，与同步现场结论一致。
  - 我在根目录当前现场补做一致性复跑，结果与同步现场一致：
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen` -> `exit=0`
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.arch` -> `exit=0`
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.symbol` -> `exit=0`
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.dma` -> `exit=0`
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn` -> `exit=0`
    - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/ast test/dsl/mlir_gen test/dsl/mlir_gen/emit test/tools/test_mlir_gen_compare.py` -> `59 passed`
- 终验说明：
  - 当前主线已满足计划正文列出的根入口、一级目录入口与 pytest 总验收要求；根目录当前现场与最新同步现场结论一致，不再存在需要继续收口的差异。
  - 因此，本计划当前可直接进入归档链，不再保留新的继续项。
- 当前状态：
  - [`T-20260416-08225f2f`](../../DONE.md) 已完成并停用，不再续接。
  - 当前无新的继续项；管理员可按现行规则补建唯一归档任务，再执行后续归档动作。

## 归档记录

时间：2026-04-16 22:14 +0800
经办人：李白
任务：T-20260416-5c54f449
任务目标：将 `ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md` 归档到 `agents/codex-multi-agents/log/task_records/done_plan/2026/16/dsl_mlir_gen_expectation_green_plan.md`，并完成归档 merge 收口
改动：
- 管理员指定的 `worktree=/home/lfr/kernelcode_generate/wt-20260416-archive-dsl-mlir-gen-expectation-green-plan` 原本不存在，已按当前远端主分支 `origin/main@ed042be` 新建任务分支 `T-20260416-5c54f449` 与对应归档 `worktree`。
- 核对发现源计划书 `ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md` 当前只存在于主仓本地计划目录，命中 `.gitignore` 且未被 `git ls-files` 跟踪；`origin/main` 中既无该源计划书，也无目标 `done_plan` 文件。
- 因此在指定归档 `worktree` 内将源计划书内容复制为归档目标文件 `agents/codex-multi-agents/log/task_records/done_plan/2026/16/dsl_mlir_gen_expectation_green_plan.md`，并在文件尾部追加本次归档记录。
- 按用户要求，主仓本地源计划书 `ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md` 已删除；本次归档合并范围限定为新增上述 `done_plan` 文件，不修改 `.gitignore`、`TODO.md`、`DONE.md` 或其它共享状态文件。
验证：
- `git worktree add -b T-20260416-5c54f449 /home/lfr/kernelcode_generate/wt-20260416-archive-dsl-mlir-gen-expectation-green-plan origin/main` -> 成功创建归档 `worktree`
- `test -f /home/lfr/kernelcode_generate/ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md && echo ROOT_PLAN_EXISTS || echo ROOT_PLAN_MISSING; test -f /home/lfr/kernelcode_generate/wt-20260416-archive-dsl-mlir-gen-expectation-green-plan/ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md && echo WT_PLAN_EXISTS || echo WT_PLAN_MISSING` -> `ROOT_PLAN_EXISTS`；`WT_PLAN_MISSING`
- `git ls-files --stage -- ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md agents/codex-multi-agents/log/task_records/done_plan/2026/16/dsl_mlir_gen_expectation_green_plan.md` -> 无输出，确认两者当前均未被 Git 跟踪
- `git ls-tree --name-only origin/main ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md agents/codex-multi-agents/log/task_records/done_plan/2026/16/dsl_mlir_gen_expectation_green_plan.md` -> 无输出，确认远端主分支当前无源计划书与目标归档文件
- `git check-ignore -v ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md agents/codex-multi-agents/log/task_records/done_plan/2026/16/dsl_mlir_gen_expectation_green_plan.md` -> 仅源计划书命中 `.gitignore:21:ARCHITECTURE/plan/`
- `test -f /home/lfr/kernelcode_generate/wt-20260416-archive-dsl-mlir-gen-expectation-green-plan/agents/codex-multi-agents/log/task_records/done_plan/2026/16/dsl_mlir_gen_expectation_green_plan.md && echo ARCHIVE_FILE_READY && test ! -e /home/lfr/kernelcode_generate/ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md && echo ROOT_PLAN_REMOVED` -> `ARCHIVE_FILE_READY`；`ROOT_PLAN_REMOVED`
结论：归档文件已在指定 `worktree` 内生成并写入归档记录；下一步提交并推送该归档文件，随后执行当前 merge 任务 `-done` 并回报管理员继续 `-done-plan`。
