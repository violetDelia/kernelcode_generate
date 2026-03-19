# Kernelcode Generate README

## 功能简介

`kernelcode_generate` 用于组织符号语义、操作层 API、方言层 IR 和 DSL 语义的 spec、实现、测试与协作流程。仓库目标不是只堆放实现文件，而是把每条链路都收敛为“spec 先定义行为，代码按 spec 落地，测试按 spec 映射”的可追溯结构，便于多人协作、审查和合并。

## 文档信息

- 创建者：`金铲铲大作战`
- 最后一次更改：`朽木露琪亚`（2026-03-19）
- `spec`：[`AGENTS.md`](AGENTS.md)
- `test`：[`test/codex-multi-agents/test_codex-multi-agents-task.py`](test/codex-multi-agents/test_codex-multi-agents-task.py)
- `功能实现`：[`skills/codex-multi-agents/scripts/codex-multi-agents-task.sh`](skills/codex-multi-agents/scripts/codex-multi-agents-task.sh)

## 项目目标

- 提供可追溯的 spec、实现、测试协作流程。
- 形成稳定的 `symbol_variable -> operation -> dialect -> dsl` 分层语义。
- 保证实现与测试严格映射到 spec，便于审查与合并。
- 明确 README、spec、脚本与任务记录之间的协作边界，减少文档与主线行为漂移。

## 协作主线

- 默认协作链路：`spec -> 实现 -> 审查 -> 改进 spec/改进实现 -> 再审查 -> 合入 main`
- `spec/*` 定义接口、边界、错误语义和测试清单。
- `python/*` 落地当前主线行为。
- `test/*` 负责把 spec 中的测试目标收敛成可执行用例。
- `agents/codex-multi-agents/log/task_records/*` 记录任务过程和阶段结论，用于后续派发与复盘。

## 仓库结构总览

| 目录 | 作用 | 说明 |
| --- | --- | --- |
| [`spec/`](spec) | 规范文档 | 定义接口、约束、错误语义、测试清单和跨层关系 |
| [`python/`](python) | 主线实现 | 落地 symbol、operation、dialect、dsl 的当前行为 |
| [`test/`](test) | pytest 测试 | 验证实现与 spec 是否一致 |
| [`agents/`](agents) | 协作调度 | 角色提示词、任务记录、会话日志、状态清单 |
| [`skills/`](skills) | 协作脚本 | 任务派发、会话同步、状态维护等工具 |

## 分层结构与入口映射

| 层级 | 职责 | 主要 spec | 主要实现 | 主要测试 |
| --- | --- | --- | --- | --- |
| `symbol_variable` | 定义维度、形状、类型、内存等基础语义 | [`spec/symbol_variable/type.md`](spec/symbol_variable/type.md), [`spec/symbol_variable/symbol_dim.md`](spec/symbol_variable/symbol_dim.md), [`spec/symbol_variable/symbol_shape.md`](spec/symbol_variable/symbol_shape.md), [`spec/symbol_variable/memory.md`](spec/symbol_variable/memory.md), [`spec/symbol_variable/package_api.md`](spec/symbol_variable/package_api.md) | [`python/symbol_variable/type.py`](python/symbol_variable/type.py), [`python/symbol_variable/symbol_dim.py`](python/symbol_variable/symbol_dim.py), [`python/symbol_variable/symbol_shape.py`](python/symbol_variable/symbol_shape.py), [`python/symbol_variable/memory.py`](python/symbol_variable/memory.py), [`python/symbol_variable/__init__.py`](python/symbol_variable/__init__.py) | [`test/symbol_variable/test_type.py`](test/symbol_variable/test_type.py), [`test/symbol_variable/test_symbol_dim.py`](test/symbol_variable/test_symbol_dim.py), [`test/symbol_variable/test_symbol_shape.py`](test/symbol_variable/test_symbol_shape.py), [`test/symbol_variable/test_memory.py`](test/symbol_variable/test_memory.py), [`test/symbol_variable/test_package_api.py`](test/symbol_variable/test_package_api.py) |
| `operation` | 定义高层 API 语义，不直接承诺 IR 细节 | [`spec/operation/nn.md`](spec/operation/nn.md), [`spec/operation/dma.md`](spec/operation/dma.md) | [`python/operation/nn.py`](python/operation/nn.py), [`python/operation/dma.py`](python/operation/dma.py) | [`test/operation/test_operation_nn.py`](test/operation/test_operation_nn.py), [`test/operation/test_operation_dma.py`](test/operation/test_operation_dma.py), [`test/operation/test_memory_operation.py`](test/operation/test_memory_operation.py) |
| `dialect` | 定义 IR 字段、parse/print 和 verifier 规则 | [`spec/dialect/nn.md`](spec/dialect/nn.md), [`spec/dialect/dma.md`](spec/dialect/dma.md) | [`python/dialect/nn.py`](python/dialect/nn.py), [`python/dialect/dma.py`](python/dialect/dma.py), [`python/dialect/__init__.py`](python/dialect/__init__.py) | [`test/dialect/test_nn_dialect.py`](test/dialect/test_nn_dialect.py), [`test/dialect/test_dma_dialect.py`](test/dialect/test_dma_dialect.py) |
| `dsl` | 定义 AST、visitor、lowering 和 MLIR 生成约束 | [`spec/dsl/ast.md`](spec/dsl/ast.md), [`spec/dsl/ast_visitor.md`](spec/dsl/ast_visitor.md), [`spec/dsl/lowering.md`](spec/dsl/lowering.md), [`spec/dsl/mlir_gen.md`](spec/dsl/mlir_gen.md) | [`python/dsl/ast.py`](python/dsl/ast.py), [`python/dsl/ast_visitor.py`](python/dsl/ast_visitor.py), [`python/dsl/lowering.py`](python/dsl/lowering.py), [`python/dsl/__init__.py`](python/dsl/__init__.py) | [`test/dsl/test_ast_visitor.py`](test/dsl/test_ast_visitor.py) |
| `codex-multi-agents` | 维护任务、状态和会话同步 | [`spec/codex-multi-agents/scripts/codex-multi-agents-list.md`](spec/codex-multi-agents/scripts/codex-multi-agents-list.md), [`spec/codex-multi-agents/scripts/codex-multi-agents-task.md`](spec/codex-multi-agents/scripts/codex-multi-agents-task.md), [`spec/codex-multi-agents/scripts/codex-multi-agents-tmux.md`](spec/codex-multi-agents/scripts/codex-multi-agents-tmux.md) | [`skills/codex-multi-agents/scripts/codex-multi-agents-list.sh`](skills/codex-multi-agents/scripts/codex-multi-agents-list.sh), [`skills/codex-multi-agents/scripts/codex-multi-agents-task.sh`](skills/codex-multi-agents/scripts/codex-multi-agents-task.sh), [`skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh`](skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh) | [`test/codex-multi-agents/test_codex-multi-agents-list.py`](test/codex-multi-agents/test_codex-multi-agents-list.py), [`test/codex-multi-agents/test_codex-multi-agents-task.py`](test/codex-multi-agents/test_codex-multi-agents-task.py), [`test/codex-multi-agents/test_codex-multi-agents-tmux.py`](test/codex-multi-agents/test_codex-multi-agents-tmux.py) |

## 关键测试映射说明

### symbol_variable

- `type` 链路：[`spec/symbol_variable/type.md`](spec/symbol_variable/type.md) -> [`python/symbol_variable/type.py`](python/symbol_variable/type.py) -> [`test/symbol_variable/test_type.py`](test/symbol_variable/test_type.py)
- `symbol_dim` 链路：[`spec/symbol_variable/symbol_dim.md`](spec/symbol_variable/symbol_dim.md) -> [`python/symbol_variable/symbol_dim.py`](python/symbol_variable/symbol_dim.py) -> [`test/symbol_variable/test_symbol_dim.py`](test/symbol_variable/test_symbol_dim.py)
- `symbol_shape` 链路：[`spec/symbol_variable/symbol_shape.md`](spec/symbol_variable/symbol_shape.md) -> [`python/symbol_variable/symbol_shape.py`](python/symbol_variable/symbol_shape.py) -> [`test/symbol_variable/test_symbol_shape.py`](test/symbol_variable/test_symbol_shape.py)
- `memory` 链路：[`spec/symbol_variable/memory.md`](spec/symbol_variable/memory.md) -> [`python/symbol_variable/memory.py`](python/symbol_variable/memory.py) -> [`test/symbol_variable/test_memory.py`](test/symbol_variable/test_memory.py)
- `package_api` 链路：[`spec/symbol_variable/package_api.md`](spec/symbol_variable/package_api.md) -> [`python/symbol_variable/__init__.py`](python/symbol_variable/__init__.py) -> [`test/symbol_variable/test_package_api.py`](test/symbol_variable/test_package_api.py)

### operation 与 dialect

- `operation/nn` 链路：[`spec/operation/nn.md`](spec/operation/nn.md) -> [`python/operation/nn.py`](python/operation/nn.py) -> [`test/operation/test_operation_nn.py`](test/operation/test_operation_nn.py)
- `operation/dma` 链路：[`spec/operation/dma.md`](spec/operation/dma.md) -> [`python/operation/dma.py`](python/operation/dma.py) -> [`test/operation/test_operation_dma.py`](test/operation/test_operation_dma.py)
- `Memory` 运算辅助链路：[`spec/symbol_variable/memory.md`](spec/symbol_variable/memory.md) / [`spec/operation/nn.md`](spec/operation/nn.md) -> [`python/symbol_variable/memory.py`](python/symbol_variable/memory.py) -> [`test/operation/test_memory_operation.py`](test/operation/test_memory_operation.py)
- `dialect/nn` 链路：[`spec/dialect/nn.md`](spec/dialect/nn.md) -> [`python/dialect/nn.py`](python/dialect/nn.py) -> [`test/dialect/test_nn_dialect.py`](test/dialect/test_nn_dialect.py)
- `dialect/dma` 链路：[`spec/dialect/dma.md`](spec/dialect/dma.md) -> [`python/dialect/dma.py`](python/dialect/dma.py) -> [`test/dialect/test_dma_dialect.py`](test/dialect/test_dma_dialect.py)

### dsl

- `dsl` 主测试入口：[`spec/dsl/ast_visitor.md`](spec/dsl/ast_visitor.md), [`spec/dsl/lowering.md`](spec/dsl/lowering.md), [`spec/dsl/mlir_gen.md`](spec/dsl/mlir_gen.md) -> [`python/dsl/ast_visitor.py`](python/dsl/ast_visitor.py), [`python/dsl/lowering.py`](python/dsl/lowering.py) -> [`test/dsl/test_ast_visitor.py`](test/dsl/test_ast_visitor.py)
- 当前 DSL 测试主入口集中在 [`test/dsl/test_ast_visitor.py`](test/dsl/test_ast_visitor.py)；README 在此明确这一点，是为了避免误以为 `ast/lowering/mlir_gen` 各自已有独立测试文件。

## 当前待补链路说明

- [`spec/operation/nn.md`](spec/operation/nn.md) 已定义高层 `broadcast` 与 `matmul` 契约，但当前主线 [`python/operation/nn.py`](python/operation/nn.py) 与 [`test/operation/test_operation_nn.py`](test/operation/test_operation_nn.py) 仍以现有算术/比较 API 为主，`broadcast/matmul` 仍处于待补闭环状态。
- [`spec/dialect/nn.md`](spec/dialect/nn.md) 已收敛五空间 `global/shared/local/tsm/tlm` 口径；当前主线实现与测试已完成闭环并覆盖测试，`nn.matmul` / `nn.broadcast` 的待补方言规范仍以 spec 说明为准。
- README 只负责给出仓库入口、分层关系和测试映射，不替代各 spec 的字段级约束、错误语义和测试清单。

## 交付/合并/仓库使用说明

- 交付范围以任务授权为准，只改指定文件与链路；出现冲突按最新改动时间为主，无法判断先回报管理员。
- 合并要求收敛为单个可审查提交；从 worktree 合入 main 后，必须清理对应 worktree/分支/.lock，避免残留。
- README 维护职责是说明入口、映射和协作规则，不替代 spec 的字段级语义与测试清单。
- 常用仓库操作示例（在仓库根目录执行）：

```bash
git status -sb
git diff
pytest -q test/dialect/test_nn_dialect.py
```

## 术语、边界与协作说明

- `symbol_variable` 只定义基础语义，不直接承诺 operation/dialect 的调用方式。
- `operation` 只定义高层 API 语义，不直接写 parse/print 或 verifier 细节。
- `dialect` 只定义 IR 层字段、attribute/type/op 与 verifier 约束，不反向改写高层 API 语义。
- `dsl` 负责 AST、visitor、lowering 和生成链路，不应在 README 中被写成“独立于 spec 的另一套规则”。
- `Memory.stride` 表示布局语义；切片参数如 `offsets/sizes/strides` 是否保留、如何传给下游，应以对应 `operation/dma` 与 `dialect/dma` spec 为准，不能由 README 擅自重定义。
- 协作日志、任务记录和角色状态属于调度材料，不是公开 API，也不作为稳定程序依赖。

## 调度与日志目录说明

- [`agents/codex-multi-agents/log/`](agents/codex-multi-agents/log/)：任务记录与会话日志。
- [`agents/codex-multi-agents/agents-lists.md`](agents/codex-multi-agents/agents-lists.md)：角色状态与职责列表。
- [`agents/codex-multi-agents/agents/`](agents/codex-multi-agents/agents/)：角色提示词与归档目录。

## 测试方式

- 测试框架：`pytest`
- 全量执行：`pytest -q`
- 常用入口：
  - `pytest -q test/symbol_variable/test_type.py`
  - `pytest -q test/symbol_variable/test_memory.py`
  - `pytest -q test/operation/test_operation_nn.py`
  - `pytest -q test/operation/test_operation_dma.py`
  - `pytest -q test/dialect/test_nn_dialect.py`
  - `pytest -q test/dsl/test_ast_visitor.py`
  - `pytest -q test/codex-multi-agents/test_codex-multi-agents-task.py`

## 实现与测试入口示例

说明：
- 本节仅展示仓库级入口与最小可执行示例，不替代各 spec 的字段级约束。
- 所有示例保持“spec -> 实现 -> 测试”映射口径，链接遵循 `AGENTS.md` 约定。

### symbol_variable

- spec：[`spec/symbol_variable/type.md`](spec/symbol_variable/type.md)
- 实现：[`python/symbol_variable/type.py`](python/symbol_variable/type.py)
- 测试：[`test/symbol_variable/test_type.py`](test/symbol_variable/test_type.py)

使用示例（Python）：

```python
from python.symbol_variable.type import NumericType, Farmat

dtype = NumericType.Float32
layout = Farmat.Norm
```

### operation/nn

- spec：[`spec/operation/nn.md`](spec/operation/nn.md)
- 实现：[`python/operation/nn.py`](python/operation/nn.py)
- 测试：[`test/operation/test_operation_nn.py`](test/operation/test_operation_nn.py)

使用示例（Python）：

```python
from python.operation.nn import add, eq
from python.symbol_variable.memory import Memory
from python.symbol_variable.type import NumericType

lhs = Memory(["M", "N"], NumericType.Float32)
rhs = Memory(["M", "N"], NumericType.Float32)
out = add(lhs, rhs)
cmp = eq(lhs, rhs)
```

### dialect/nn

- spec：[`spec/dialect/nn.md`](spec/dialect/nn.md)
- 实现：[`python/dialect/nn.py`](python/dialect/nn.py)
- 测试：[`test/dialect/test_nn_dialect.py`](test/dialect/test_nn_dialect.py)

使用示例（pytest）：

```bash
pytest -q test/dialect/test_nn_dialect.py -k test_add_op_verify_success
```

### dsl

- spec：[`spec/dsl/ast_visitor.md`](spec/dsl/ast_visitor.md)
- 实现：[`python/dsl/ast_visitor.py`](python/dsl/ast_visitor.py)
- 测试：[`test/dsl/test_ast_visitor.py`](test/dsl/test_ast_visitor.py)

使用示例（Python）：

```python
from python.dsl.ast_visitor import emit_mlir

def add(x: "Tensor[f32, 2, 2]", y: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
    return x + y

mlir_text = emit_mlir(add)
```

## 开发约定

- 每个 spec 原则上对应一个实现文件；若一个测试文件覆盖多份 spec，README 必须明确该聚合关系。
- spec、实现、测试需要保持可追溯映射；README 负责给出目录级和文件级入口，不替代 spec 内部测试清单。
- 不得修改带有 `[immutable]` 标记的段落。
- 测试函数必须包含创建者、最后一次更改、最近一次运行与成功时间等注释字段。
- 任务记录、日志、`agents-lists.md` 和会话同步文件统一在 `main` 更新；worktree 中只处理授权范围内的代码或文档文件。

## spec 文档规范

推荐结构（与 AGENTS 约定一致）：
- `功能简介`：说明该 spec 对应的模块/类/方法的职责。
- `文档信息`：包含创建者、最后一次更改、`spec`、`功能实现`、`test` 的文件链接。
- `依赖`：列出直接依赖的文件或模块并附路径。
- `目标`（可选）：说明对外能力、使用方式与预期场景。
- `限制与边界`（可选）：明确实现必须满足的限制与不负责范围。
- `公开接口`：每个 API 至少包含功能说明、参数说明、使用示例、注意事项、返回与限制。
- `测试`：列出测试文件、执行命令、测试目标与用例清单。

编写要求：
- spec 只写设计边界、API 与测试目标，不写迁移过程或重构步骤。
- spec 中的接口说明、测试目标和示例必须与实现和测试保持一致。
- 若存在“一个 spec 对应多个实现文件”的情况，需在 spec 中显式说明原因。

## 常用入口

- 状态查询：`./skills/codex-multi-agents/scripts/codex-multi-agents-list.sh -file agents/codex-multi-agents/agents-lists.md -status`
- 任务派发：`./skills/codex-multi-agents/scripts/codex-multi-agents-task.sh`
- 会话同步：`./skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh -talk -from <sender> -to <target> -session-id <id> -message "..." -log ./agents/codex-multi-agents/log/talk.log`
