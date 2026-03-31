# expectation_dsl_mlir_dma_symbol_closure_plan.md

## 进度
更新日期：2026-03-31
更新规则：每个任务块进入新子阶段后立即更新本段。

| 任务 | 依赖 | 记录文件 | worktree | 当前进度 |
| --- | --- | --- | --- | --- |
| E1 | A2、P12 |  |  |  |
| E2 | E1 |  |  |  |
| E3 | E2 |  |  |  |
| E4 | E3 |  |  |  |
| E5 | E4 |  |  |  |
| E6 | E1、E2、E3、E4、E5 |  |  |  |

## 功能说明

- 本计划基于当前仓库实现重新拟定，用来把 `expectation/dsl/mlir_gen/dialect/dma` 与 `expectation/dsl/mlir_gen/dialect/symbol` 的剩余未闭环项推进到最终通过。
- 下文只描述当前已经通过的 expectation 基线、当前仍失败的 expectation 集合，以及从当前实现走到最终目标的收口顺序。
- expectation 文件默认保持只读；本计划的目标是让实现、测试和规格追上 expectation，而不是收窄 expectation。

## 使用示例

- 管理员先确认“当前 expectation 基线”，再按“本轮收口顺序”分发。
- 若执行者回报以下 expectation 已通过，则这些子域不再是本轮主线阻塞：

```bash
PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/dma/free
PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/symbol/get_dim.py
PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/symbol/get_stride.py
```

- 若执行者回报以下 expectation 仍失败，则本轮分发重点应集中在对应子域：

```bash
PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/dma/view
PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/symbol/gt.py
PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/symbol/le.py
PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/symbol/lt.py
PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/symbol/ne.py
PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/symbol/to_float.py
```

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`大闸蟹`
- `文档`：[`ARCHITECTURE/plan/expectation_dsl_mlir_dma_symbol_closure_plan.md`](../../ARCHITECTURE/plan/expectation_dsl_mlir_dma_symbol_closure_plan.md)
- `spec`：
  - [`spec/dsl/ast.md`](../../spec/dsl/ast.md)
  - [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
  - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
  - [`spec/dialect/dma.md`](../../spec/dialect/dma.md)
  - [`spec/dialect/symbol.md`](../../spec/dialect/symbol.md)
- `功能实现`：
  - [`kernel_gen/dsl/ast.py`](../../kernel_gen/dsl/ast.py)
  - [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py)
  - [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py)
  - [`kernel_gen/dialect/dma.py`](../../kernel_gen/dialect/dma.py)
  - [`kernel_gen/dialect/symbol.py`](../../kernel_gen/dialect/symbol.py)
- `test`：
  - [`test/dsl/test_ast.py`](../../test/dsl/test_ast.py)
  - [`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
  - [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py)
  - [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py)
  - [`test/dialect/test_dma_dialect.py`](../../test/dialect/test_dma_dialect.py)
  - [`test/dialect/test_symbol_dialect.py`](../../test/dialect/test_symbol_dialect.py)

## 当前 expectation 基线

### 已通过

- [`expectation/dsl/mlir_gen/dialect/dma/free`](../../expectation/dsl/mlir_gen/dialect/dma/free) 已通过，说明 `dma.free` 语句型 lowering 已形成稳定基线。
- [`expectation/dsl/mlir_gen/dialect/symbol/get_dim.py`](../../expectation/dsl/mlir_gen/dialect/symbol/get_dim.py) 已通过，说明 `Memory.get_shape()[axis]` 主链已闭环。
- [`expectation/dsl/mlir_gen/dialect/symbol/get_stride.py`](../../expectation/dsl/mlir_gen/dialect/symbol/get_stride.py) 已通过，说明 `Memory.get_stride()[axis]` 主链已闭环。

### 当前未通过

1. [`expectation/dsl/mlir_gen/dialect/dma/view`](../../expectation/dsl/mlir_gen/dialect/dma/view)
   - 当前失败表现：生成了 `dma.view`，但返回 `Memory` 类型与 expectation 要求不一致。

2. [`expectation/dsl/mlir_gen/dialect/symbol/gt.py`](../../expectation/dsl/mlir_gen/dialect/symbol/gt.py)、[`expectation/dsl/mlir_gen/dialect/symbol/le.py`](../../expectation/dsl/mlir_gen/dialect/symbol/le.py)、[`expectation/dsl/mlir_gen/dialect/symbol/lt.py`](../../expectation/dsl/mlir_gen/dialect/symbol/lt.py)、[`expectation/dsl/mlir_gen/dialect/symbol/ne.py`](../../expectation/dsl/mlir_gen/dialect/symbol/ne.py)
   - 当前失败表现：`build_func_op(...)` 在推导比较表达式类型时直接报 `Unsupported symbol compare op`。

3. [`expectation/dsl/mlir_gen/dialect/symbol/to_float.py`](../../expectation/dsl/mlir_gen/dialect/symbol/to_float.py)
   - 当前失败表现：函数返回注解 `-> float` 在 AST 解析阶段仍报 `Unsupported annotation`，因此 `symbol.to_float` 链路尚未进入 lowering。

## 最终目标

- `dma.view` expectation 通过，保证 `view(src, offset, size, stride)` 的 lowering 结果类型与 expectation 一致。
- `symbol` compare family (`gt/le/lt/ne`) expectation 全部通过。
- `symbol.to_float` expectation 通过，保证 `-> float` 与 `float(symbol.int)` 都能沿当前 DSL 主链完成 lowering。
- 在以上子域通过后，再做全量 expectation 回归。

## 本轮边界

- 不修改 expectation 文件本体，除非用户后续单独授权。
- 不把已经通过的 `dma.free`、`get_dim`、`get_stride` 重新拉回本轮主线。
- 不在本轮引入与 expectation 无关的新 DSL 能力。

## 本轮收口顺序

1. 先收口 [`expectation/dsl/mlir_gen/dialect/dma/view`](../../expectation/dsl/mlir_gen/dialect/dma/view)，让 `dma.view` 返回类型与 expectation 对齐；这条链只涉及一个 expectation 文件，边界最清晰。
2. 再收口 `symbol` compare family，把 `gt/le/lt/ne` 一次性按同一条类型推导与 lowering 链打通。
3. compare family 通过后，再收口 [`expectation/dsl/mlir_gen/dialect/symbol/to_float.py`](../../expectation/dsl/mlir_gen/dialect/symbol/to_float.py)。
4. 以上子域都通过后，最后再做全量 expectation 回归。

## 管理员执行口径

- `dma.view` 与 `symbol` compare family 不应混成一个任务；二者根因不同，修改文件组也不同。
- `gt/le/lt/ne` 应按同一组实现一起推进，不要拆成四个分散任务反复修改同一批 DSL lowering 文件。
- `to_float` 依赖返回注解和 builtin lowering 两个点，建议放在 compare family 之后单独收口。

## 本轮验收口径

- `dma.view` 收口：

```bash
PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/dma/view
PYTHONPATH=. pytest -q test/dialect/test_dma_dialect.py -k 'test_dma_view_accepts_matching_numel_subset_with_explicit_stride or test_dma_view_dynamic_symbol_int_layout_operands_valid'
PYTHONPATH=. pytest -q test/dsl/test_ast_visitor.py -k test_build_func_op_supports_dma_view_helper
```

预期：全部退出码为 `0`，且 expectation 中的 `EXPECTED_MEMORY` 对比通过。

- `symbol` compare family 收口：

```bash
PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/symbol/gt.py
PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/symbol/le.py
PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/symbol/lt.py
PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/symbol/ne.py
PYTHONPATH=. pytest -q test/dsl/test_ast.py test/dsl/test_emit_mlir.py test/dsl/test_mlir_gen.py -k 'symbol_gt or symbol_le or symbol_lt or symbol_ne'
```

预期：全部退出码为 `0`，且不再出现 `Unsupported symbol compare op`。

- `symbol.to_float` 收口：

```bash
PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/symbol/to_float.py
PYTHONPATH=. pytest -q test/dsl/test_ast.py test/dsl/test_emit_mlir.py test/dsl/test_mlir_gen.py -k 'to_float or float_return_annotation'
```

预期：全部退出码为 `0`，且不再出现 `Unsupported annotation`。

- 全量回归：

```bash
find expectation -type f ! -path "*/__pycache__/*" ! -path "expectation/utils/*" | sort | while IFS= read -r f; do PYTHONPATH=. python "$f"; done
```

预期：退出码为 `0`。

## 当前最直接的下一步

- 先收口 [`expectation/dsl/mlir_gen/dialect/dma/view`](../../expectation/dsl/mlir_gen/dialect/dma/view)；这是当前 expectation 主链里边界最清晰、最独立的未闭环项。
