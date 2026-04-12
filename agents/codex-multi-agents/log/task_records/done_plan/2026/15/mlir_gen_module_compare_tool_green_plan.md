# mlir_gen_module_compare_tool_green_plan.md

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`大闸蟹`
- 目标 `spec`：
  - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
  - [`spec/tools/mlir_gen_compare.md`](../../spec/tools/mlir_gen_compare.md)
- 目标 `test`：
  - [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py)
  - [`test/tools/test_mlir_gen_compare.py`](../../test/tools/test_mlir_gen_compare.py)
- 目标 `功能实现`：
  - [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py)
  - [`kernel_gen/tools/mlir_gen_compare.py`](../../kernel_gen/tools/mlir_gen_compare.py)

## 进度

| 编号 | 依赖 | worktree | 记录文件 | 进度 |
| --- | --- | --- | --- | --- |
| `S1` | `无` | `wt-20260409-mlir-gen-module-s1` | `20260409-mlir-gen-module-s1.md` | `已完成` |
| `S2` | `S1` | `wt-20260409-mlir-gen-module-s2` | `20260409-mlir-gen-module-s2.md` | `已完成` |
| `S3` | `S2` | `wt-20260409-mlir-gen-module-s3` | `20260409-mlir-gen-module-s3.md` | `已完成` |
| `S4` | `S2,S3` | `wt-20260409-mlir-gen-module-s4` | `20260409-mlir-gen-module-s4.md` | `已完成` |

## 评审摘要

- `评审结论`：`已评审通过`
- `评审人`：`大闸蟹`、`守护最好的爱莉希雅`
- `摘要`：
  - `mlir_gen/build_func_op` 的绑定与推导只按 `runtime_args + AST`，不使用函数签名做独立绑定或推导；
  - 稳定公开入口固定为 `mlir_gen(...)`、`mlir_gen_compare(...)`、`mlir_gen_compare_text(...)`，`compare_mlir_file(...)` 仅保留兼容别名；
  - 已补主目录黑盒 expectation：`basic_true.py`、`basic_false.py`、`invalid_mlir_false.py`、`multi_func_true.py`；
  - 当前正文已与 `TODO.md` 对齐：`S1~S4` 全部已完成，计划状态为 `4/4 完成待检查`。

## 最终公开合同摘要

- 当前稳定公开入口为：
  - `mlir_gen(...) -> builtin.module`
  - `mlir_gen_compare(...) -> bool`
  - `mlir_gen_compare_text(...) -> bool`
- `compare_mlir_file(...) -> bool` 保留为兼容别名，语义等价于 `mlir_gen_compare(...)`，不再作为主公开名称。
- 当前归档前的收口口径以 [`spec/tools/mlir_gen_compare.md`](../../spec/tools/mlir_gen_compare.md) 与 [`kernel_gen/tools/mlir_gen_compare.py`](../../kernel_gen/tools/mlir_gen_compare.py) 为准。

## 计划目标

- 在 [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py) 增加一个新的公开入口 `mlir_gen(...)`：
  - 输入：`Python func`、`runtime_args`、可选 `config`
  - 输出：带 `builtin.module` 包装的 MLIR in-memory IR
- 该入口在处理根函数时，若函数体中出现“当前前端已支持、且应当表达为 `func.call` 的 Python 函数调用”，则返回的 `builtin.module` 中必须同时包含根函数与被调用函数。
- 在 [`kernel_gen/tools`](../../kernel_gen/tools) 下增加一个新工具：
  - 输入：`func`、`runtime_args`、`config`、`mlir_file`
  - 行为：用 `mlir_gen(...)` 生成模块，读取 `mlir_file`，对两边做同一套 parse + print 归一化，然后返回 `true/false`
- 目标用途是给后续 `expectation` 与手工排查提供一条“函数 -> 模块 IR -> 与预期文件精确对比”的公共路径，减少重复拼装 `ModuleOp([func_op])` 和手写字符串比对。

## 当前基线（2026-04-09）

- 当前 [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md) 的公开边界仍然写的是：
  - 只生成 `func.func`
  - 不生成 `builtin.module`
  - 不负责文本打印
- 当前 [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py) 的公开入口只有：
  - `build_func_op(...) -> func.FuncOp`
  - `build_func_op_from_ast(...) -> func.FuncOp`
- 当前仓库里如果要把函数变成 module，通常是调用方手工写：

```python
func_op = build_func_op_from_ast(func_ast, runtime_args=runtime_args)
module = ModuleOp([func_op])
```

- 当前仓库已经有 [`kernel_gen/tools/ircheck.py`](../../kernel_gen/tools/ircheck.py)，但它解决的是“给一段输入 IR 跑 pass 再做 `CHECK:` 匹配”，不是“给一个 Python func 生成 module 再和预期 module 文件做精确比较”。
- 当前没有一个公共入口能完成以下链路：
  1. 输入 Python 函数；
  2. 生成 `builtin.module`；
  3. 自动补齐同一调用闭包中的其他已支持函数；
  4. 与磁盘中的 `.mlir` 文件做稳定比较。

## 讨论结论

### 计划目标

- 这次不改现有 `build_func_op(...)` / `build_func_op_from_ast(...)` 的返回类型。
- 现有接口继续返回 `func.func`，避免已有调用方全部改写。
- 新能力通过“并列的新公开入口”提供：
  - `mlir_gen(...) -> builtin.module`
  - `compare_mlir_file(...) -> bool`
- 工具目标不是跑 pass，不是做 lowering，不是做源码生成，只比较 `mlir_gen` 这一层的 module 结果。

### 是否有更合理的方案

- 不采用“直接把 `build_func_op(...)` 改成返回 `builtin.module`”。
  - 原因：这会破坏当前所有依赖 `func.func` 的上层调用方。
- 不采用“继续让 expectation 自己手工 `ModuleOp([func_op])`”。
  - 原因：这会把 module 包装、辅助函数补齐、文本归一化、文件比较分散到每个 expectation 里。
- 不采用“直接复用 `ircheck`”。
  - 原因：`ircheck` 的输入是已有 IR 文本；这里的输入是 Python 函数对象，两者职责不同。
- 第一版采用“新增 module builder + 新增 compare tool”的方案：
  - `mlir_gen(...)` 负责函数到 module
  - `compare_mlir_file(...)` 负责 module 精确比较

### 依赖

- DSL 前端：
  - [`spec/dsl/ast.md`](../../spec/dsl/ast.md)
  - [`spec/dsl/ast_visitor.md`](../../spec/dsl/ast_visitor.md)
  - [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
  - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
- 目标实现：
  - [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py)
  - [`kernel_gen/tools`](../../kernel_gen/tools)
- 目标验证：
  - [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py)
  - [`test/tools`](../../test/tools)
  - [`expectation`](../../expectation)

### 验证合理性

- `mlir_gen(...)` 必须覆盖三类最小场景：
  1. 单函数：输入一个函数，输出只含一个 `func.func` 的 `builtin.module`
  2. 多函数：根函数调用另一个已支持函数，输出 module 中包含两个或更多 `func.func`
  3. 失败路径：遇到不支持的 callee、递归调用或不一致签名时，返回固定错误短语
- `compare_mlir_file(...)` 必须覆盖三类最小场景：
  1. 文件与生成结果一致，返回 `true`
  2. 文件与生成结果不一致，返回 `false`
  3. `mlir_file` 不是 `builtin.module`，返回 `false`
- 文本比较必须基于“同 parser + 同 printer”归一化后的结果，避免只因为空格、注释、空行不同而误判。

### 可维护性

- 公开接口只保留两条稳定入口：
  - `mlir_gen(...)`
  - `compare_mlir_file(...)`
- 其余如“callee 收集”“module 排序”“文本归一化”“diff 生成”都作为内部 helper，不写成新的公开 API。
- 这能保证后面改内部实现时，不必同步修改大量 expectation。

## 参考资料

- MLIR Language Reference：顶层 IR 以 operation / region / block 组织，`func.func` 是顶层可打印 operation 之一；文本 IR 适合 round-trip 与测试  
  - https://mlir.llvm.org/docs/LangRef/
- MLIR Symbols and Symbol Tables：`func.func` 是 symbol，symbol 需要放在定义 `SymbolTable` 的父容器下，`builtin.module` 是自然的顶层容器  
  - https://mlir.llvm.org/docs/SymbolsAndSymbolTables/
- MLIR Testing Guide：IR 变换测试通常使用统一 parser/printer 与 `FileCheck` 风格的最小断言；本计划借鉴其“统一比较口径”的做法，但不直接引入 `lit` 依赖  
  - https://mlir.llvm.org/getting_started/TestingGuide/

## 固定合同（草案）

### 一、`mlir_gen(...)` 的公开接口

建议新增到 [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py)：

```python
def mlir_gen(
    fn: Callable[..., object],
    *runtime_args: object,
    globals: dict[str, object] | None = None,
    builtins: dict[str, object] | object | None = None,
    config: dict[str, object] | None = None,
) -> ModuleOp:
    ...
```

#### 作用

- 直接从 Python 函数生成 `builtin.module`
- 模块中至少包含根函数对应的 `func.func`
- 若根函数引用了“当前前端已支持、且应当形成 `func.call`”的其他 Python 函数，则模块中还要补齐这些 callee 的 `func.func`
- callee 收集范围固定为“从根函数出发的已支持 Python callee 传递闭包”，不是只看一层调用

#### 参数含义

- `fn`
  - 根函数
  - 作为 module 的主入口函数
- `runtime_args`
  - 根函数的运行时参数
  - 作用与当前 `build_func_op(...)` 相同，只用于根函数签名推导
  - 根函数的绑定与类型推导只允许基于 `runtime_args + AST`
  - 不允许把 Python 函数签名、返回注解或参数注解当作独立的绑定来源
- `globals` / `builtins`
  - 解析环境补充
  - 作用保持与现有 `build_func_op(...)` 一致
- `config`
  - 透传给 visitor / lowering 的可选配置
  - 仅影响当前已有 `mlir_gen` 配置项，不得改变 module 组装的公开顺序规则

#### 返回值

- 返回 `builtin.module`
- 不直接返回字符串
- 文本形式由统一 printer 负责

#### 最小示例：单函数

```python
from kernel_gen.dsl.mlir_gen import mlir_gen
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType


def add(lhs: "Tensor[i32, 4]", rhs: "Tensor[i32, 4]") -> "Tensor[i32, 4]":
    return lhs + rhs


module = mlir_gen(
    add,
    Memory([4], NumericType.Int32),
    Memory([4], NumericType.Int32),
)
```

预期 module 形态：

```text
builtin.module {
  func.func @add(...)
}
```

#### 最小示例：多函数

```python
def helper(x: "Tensor[i32, 4]") -> "Tensor[i32, 4]":
    return x + x


def main(x: "Tensor[i32, 4]") -> "Tensor[i32, 4]":
    return helper(x)
```

预期 module 形态：

```text
builtin.module {
  func.func @main(...)
  func.func @helper(...)
}
```

#### 函数收集规则

- 只收集“当前 AST 解析与 lowering 已支持、并应表示为普通 Python 函数调用”的 callee
- 收集范围是传递闭包：
  - `main -> helper1 -> helper2` 时，若三者都属于当前支持范围，module 中必须同时包含 `main/helper1/helper2`
- 不把 DSL helper 当作额外函数收集，例如：
  - `softmax(...)`
  - `broadcast_to(...)`
  - `matmul(...)`
- 这类 helper 仍然按 op lower，不会在 module 里新增 `func.func`

#### callee 签名推导规则

- 根函数签名由 `runtime_args` 决定，规则保持与当前 `build_func_op(...)` 一致
- 根函数与 callee 的绑定、形状推导、类型推导都只允许依赖：
  - `runtime_args`
  - AST 中的调用关系与表达式
- 不允许额外把 Python 函数签名注解当作另一套独立推导输入
- callee 不能要求调用者额外再传一份 `runtime_args`
- callee 的 `func.func` 签名必须由其 call-site operand 类型推导
- 如果同一个 callee 被多个 call-site 使用，且推导出的签名不一致，必须失败

#### module 内函数顺序

- 需要固定顺序，避免同一输入每次打印顺序不同
- 第一版建议固定为：
  1. 根函数在前
  2. callee 按 AST 中首次出现的调用顺序做 DFS 追加
- 同一个 callee 只放一次

示例：

```python
def c(x):
    return x + x


def b(x):
    return c(x)


def a(x):
    y = b(x)
    return c(y)
```

预期顺序：

```text
builtin.module {
  func.func @a(...)
  func.func @b(...)
  func.func @c(...)
}
```

#### 第一版不支持

- 递归函数调用
- 同名不同签名的 callee 合流
- 匿名函数、lambda、本地闭包函数
- 需要运行 pass 之后才能知道签名的 callee

#### 固定失败短语（仅 `mlir_gen(...)`）

- `MlirGenModuleError: unsupported callee function`
- `MlirGenModuleError: recursive callee graph is not supported`
- `MlirGenModuleError: inconsistent callee signature`

### 二、`compare_mlir_file(...)` 的公开接口

建议新增到 [`kernel_gen/tools/mlir_gen_compare.py`](../../kernel_gen/tools/mlir_gen_compare.py)：

```python
def compare_mlir_file(
    fn: Callable[..., object],
    runtime_args: tuple[object, ...] | list[object] | None,
    config: dict[str, object] | None,
    mlir_file: str,
) -> bool:
    ...
```

#### 作用

- 调用 `mlir_gen(...)` 生成 `builtin.module`
- 读取磁盘上的 `mlir_file`
- 对“生成结果”和“文件内容”做同一套 parse + print 归一化
- 若两者完全一致，返回 `true`
- 若不一致，返回 `false`

#### 参数含义

- `fn`
  - 待比较的根函数
- `runtime_args`
  - 传给 `mlir_gen(...)` 的根函数参数
- `config`
  - 透传给 `mlir_gen(...)`
- `mlir_file`
  - 预期 MLIR 文件
  - 文件内容必须是完整的 `builtin.module`

#### 比较规则

- 不是直接比原始文本
- 比较顺序固定为：
  1. `actual_module = mlir_gen(...)`
  2. 读取 `mlir_file`
  3. `expected_module = parse(mlir_file_text)`
  4. 对两者使用同一 printer 重新打印
  5. 比较规范化后的文本是否完全一致

#### 为什么不直接比较原始文本

- 这样可以忽略：
  - 注释
  - 空行
  - 缩进差异
- 同时保留：
  - op 顺序
  - type
  - attribute
  - callee 是否存在
  - module 是否完整

#### 最小示例：True

```python
ok = compare_mlir_file(
    fn=add,
    runtime_args=[Memory([4], NumericType.Int32), Memory([4], NumericType.Int32)],
    config=None,
    mlir_file="expectation/tools/mlir_gen_compare/add_expected.mlir",
)
assert ok is True
```

#### 最小示例：False

```python
ok = compare_mlir_file(
    fn=main,
    runtime_args=[Memory([4], NumericType.Int32)],
    config=None,
    mlir_file="expectation/tools/mlir_gen_compare/mismatch.mlir",
)
assert ok is False
```

#### 第一版固定返回

- 只返回 `bool`
- 先不引入 CLI
- 先不引入 diff 对象
- 先不引入 `json` 输出

#### 返回规则

- 以下场景统一返回 `false`，不把错误短语纳入公开合同：
  - `mlir_file` 解析失败
  - `mlir_file` 不是 `builtin.module`
  - 规范化后的 module 文本不一致
- 后续若需要诊断对象，可新增并列接口；本轮的公开合同只有 `bool`

### 三、与现有 `build_func_op(...)` 的关系

- `build_func_op(...)`
  - 继续负责“函数 -> `func.func`”
- `mlir_gen(...)`
  - 新负责“函数 -> `builtin.module`”
- 这两条入口并存，不互相替代
- 当前所有直接依赖 `func.func` 的路径都不需要因为这次计划整体改写

### 四、与现有 `ircheck` 的关系

- [`kernel_gen/tools/ircheck.py`](../../kernel_gen/tools/ircheck.py)
  - 输入是现成 IR 文本
  - 目标是“跑 pass 再做 `CHECK`”
- `compare_mlir_file(...)`
  - 输入是 Python 函数对象
  - 目标是“生成 module 后和预期 module 文件精确比较”
- 两者可共存，不互相合并

## 任务拆解

### `S1`：规格收口（先规格，再实现，再测试）

- `任务类型`：`收口任务（先规格，再实现，再测试）`
- `任务目标`：
  - 把 `mlir_gen(...)` 与 `compare_mlir_file(...)` 的公开合同写清
  - 明确 module 组装范围、callee 收集规则、顺序规则、失败短语、比较规则
- `依赖`：`无`
- `优先处理文件`：
  - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
  - [`spec/tools/mlir_gen_compare.md`](../../spec/tools/mlir_gen_compare.md)
- `示例代码`：

```python
module = mlir_gen(main, arg0, arg1, config={"reject_external_values": True})
ok = compare_mlir_file(main, [arg0, arg1], {"reject_external_values": True}, "expected.mlir")
```

- `预期输出（机械判定）`：

```text
mlir_gen(...) -> builtin.module
compare_mlir_file(...) -> bool
不再要求调用方自己写 ModuleOp([func_op])
根函数绑定与推导只允许基于 runtime_args + AST
```

- `必须通过测试`：
  - `pytest -q test/dsl/test_mlir_gen.py -k "existing"`
  - `pytest -q test/tools/test_ircheck_parser.py -k "existing"`
- `完成判断`：
  - 规格文字清楚说明“保留旧接口 + 新增 module builder + 新增 compare tool”
  - 规格文字清楚说明多函数收集边界
  - 规格文字清楚说明 `mlir_gen/build_func_op` 不使用函数签名做独立绑定/推导，只按 `runtime_args + AST`

### `S2`：`mlir_gen(...)` 主链收口（先规格，再实现，再测试）

- `任务类型`：`收口任务（先规格，再实现，再测试）`
- `任务目标`：
  - 新增 `mlir_gen(...)`
  - 单函数路径直接返回 `builtin.module`
  - 多函数路径能补齐已支持 callee
  - 失败路径返回固定短语
- `依赖`：`S1`
- `优先处理文件`：
  - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
  - [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py)
  - [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py)
- `示例代码`：

```python
def helper(x: "Tensor[i32, 4]") -> "Tensor[i32, 4]":
    return x + x


def main(x: "Tensor[i32, 4]") -> "Tensor[i32, 4]":
    return helper(x)


module = mlir_gen(main, Memory([4], NumericType.Int32))
```

- `预期输出（机械判定）`：

```text
命中: builtin.module
命中: func.func @main
命中: func.func @helper
禁止: 调用方手工 ModuleOp([func_op])
```

- `必须通过测试`：
  - `pytest -q test/dsl/test_mlir_gen.py -k "mlir_gen or module or nested_call"`
- `完成判断`：
  - 单函数 case 通过
  - 多函数 case 通过
  - 递归 / 不一致签名 case 触发固定短语

### `S3`：`compare_mlir_file(...)` 收口（先规格，再实现，再测试）

- `任务类型`：`收口任务（先规格，再实现，再测试）`
- `任务目标`：
  - 新增 `compare_mlir_file(...)`
  - 按统一 parser/printer 做 module 精确比较
  - 返回 `true/false`
- `依赖`：`S2`
- `优先处理文件`：
  - [`spec/tools/mlir_gen_compare.md`](../../spec/tools/mlir_gen_compare.md)
  - [`kernel_gen/tools/mlir_gen_compare.py`](../../kernel_gen/tools/mlir_gen_compare.py)
  - [`test/tools/test_mlir_gen_compare.py`](../../test/tools/test_mlir_gen_compare.py)
  - [`expectation/tools/mlir_gen_compare`](../../expectation/tools/mlir_gen_compare)
- `建议 expectation 文件`：
  - [`expectation/tools/mlir_gen_compare/basic_true.py`](../../expectation/tools/mlir_gen_compare/basic_true.py)
  - [`expectation/tools/mlir_gen_compare/basic_false.py`](../../expectation/tools/mlir_gen_compare/basic_false.py)
  - [`expectation/tools/mlir_gen_compare/invalid_mlir_false.py`](../../expectation/tools/mlir_gen_compare/invalid_mlir_false.py)
  - [`expectation/tools/mlir_gen_compare/multi_func_true.py`](../../expectation/tools/mlir_gen_compare/multi_func_true.py)
  - [`expectation/tools/mlir_gen_compare/basic_true_expected.mlir`](../../expectation/tools/mlir_gen_compare/basic_true_expected.mlir)
  - [`expectation/tools/mlir_gen_compare/basic_false_expected.mlir`](../../expectation/tools/mlir_gen_compare/basic_false_expected.mlir)
  - [`expectation/tools/mlir_gen_compare/invalid_mlir_false_expected.mlir`](../../expectation/tools/mlir_gen_compare/invalid_mlir_false_expected.mlir)
  - [`expectation/tools/mlir_gen_compare/multi_func_true_expected.mlir`](../../expectation/tools/mlir_gen_compare/multi_func_true_expected.mlir)
  - [`expectation/tools/mlir_gen_compare/transitive_true_expected.mlir`](../../expectation/tools/mlir_gen_compare/transitive_true_expected.mlir)
- `示例代码`：

```python
ok = compare_mlir_file(
    fn=main,
    runtime_args=[Memory([4], NumericType.Int32)],
    config=None,
    mlir_file="expectation/tools/mlir_gen_compare/multi_func_expected.mlir",
)
```

- `预期输出（机械判定）`：

```text
一致时返回: true
不一致时返回: false
expected 不是 builtin.module 时返回: false
expected 解析失败时返回: false
```

- `必须通过测试`：
  - `pytest -q test/tools/test_mlir_gen_compare.py`
  - `PYTHONPATH=. python expectation/tools/mlir_gen_compare/basic_true.py`
  - `PYTHONPATH=. python expectation/tools/mlir_gen_compare/basic_false.py`
  - `PYTHONPATH=. python expectation/tools/mlir_gen_compare/invalid_mlir_false.py`
  - `PYTHONPATH=. python expectation/tools/mlir_gen_compare/multi_func_true.py`
- `完成判断`：
  - 公开函数直接可用
  - `expectation` 黑盒脚本可直接跑通
  - 直接 callee 与传递闭包两类 `.mlir` 对照都已收进主目录 expectation
  - 非法 `mlir_file` 文本路径已通过黑盒 expectation 锁定 `False`

### `S4`：整体验证与接入说明（先规格，再实现，再测试）

- `任务类型`：`收口任务（先规格，再实现，再测试）`
- `任务目标`：
  - 用真实 expectation 样例证明“后续写 expectation 时可以直接复用”
  - 把推荐写法补到文档
- `依赖`：`S2,S3`
- `优先处理文件`：
  - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
  - [`spec/tools/mlir_gen_compare.md`](../../spec/tools/mlir_gen_compare.md)
  - [`expectation/tools/mlir_gen_compare`](../../expectation/tools/mlir_gen_compare)
  - [`expectation/dsl/mlir_gen`](../../expectation/dsl/mlir_gen)
- `示例代码`：

```python
func_ast = parse_function(add_kernel)
module = mlir_gen(add_kernel, lhs, rhs)
ok = compare_mlir_file(add_kernel, [lhs, rhs], None, "expected/add_module.mlir")
assert ok is True
```

- `预期输出（机械判定）`：

```text
新的 expectation 不再手工拼 ModuleOp([func_op])
对比逻辑统一走 compare_mlir_file(...)
expectation 目录内同时保留 .py 调用入口与 .mlir 预期文件
```

- `必须通过测试`：
  - `pytest -q test/dsl/test_mlir_gen.py -k "mlir_gen or module or nested_call"`
  - `pytest -q test/tools/test_mlir_gen_compare.py`
  - `PYTHONPATH=. python expectation/tools/mlir_gen_compare/basic_true.py`
  - `PYTHONPATH=. python expectation/tools/mlir_gen_compare/basic_false.py`
  - `PYTHONPATH=. python expectation/tools/mlir_gen_compare/invalid_mlir_false.py`
  - `PYTHONPATH=. python expectation/tools/mlir_gen_compare/multi_func_true.py`
- `完成判断`：
  - 新工具已能被真实 expectation 直接复用
  - 文档示例与实现一致

## 补充说明

### 为什么输出选择 `builtin.module` 而不是纯字符串

- 现有 `build_func_op(...)` 返回 in-memory IR 对象
- 新 `mlir_gen(...)` 延续这一做法更自然
- 这样后续如果还要做：
  - verify
  - pass
  - printer
  - expectation 内部拼接
  仍然方便
- 文本输出统一交给 printer，可以减少“接口一处返回 op、一处返回字符串”的混乱

### 为什么 `compare_mlir_file(...)` 第一版只返回 `bool`

- 这是用户当前直接需要的能力
- expectation 层最容易消费
- 若后面确实需要 diff，再在不破坏当前 `bool` 合同的前提下补一个结果对象或调试 helper

### 多函数场景最容易出问题的点

- callee 签名到底跟注解走，还是跟 call-site operand 走
  - 本计划固定为：跟 call-site operand 走
- 同一个 callee 被多个位置调用时，签名不一致怎么办
  - 本计划固定为：直接失败
- 递归怎么办
  - 本计划第一版固定为：不支持

### 后续不在本轮范围内的内容

- 命令行 CLI
- diff 文本对象
- JSON 输出
- 自动扫描整个 Python 模块并生成所有函数
- 运行 pass 后再比较
- 使用 `FileCheck` 风格而不是精确比较
