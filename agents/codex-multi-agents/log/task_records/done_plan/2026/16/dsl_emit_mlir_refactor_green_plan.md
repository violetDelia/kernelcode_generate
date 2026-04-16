# dsl_emit_mlir_refactor_green_plan.md

## 文档信息

- 创建者：`守护最好的爱莉希雅`
- 最后一次更改：`守护最好的爱莉希雅`
- 目标 `spec`：
  - [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
  - [`spec/dsl/ast.md`](../../spec/dsl/ast.md)
  - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
- 目标 `API`：
  - [`kernel_gen/dsl/mlir_gen/emit`](../../kernel_gen/dsl/mlir_gen/emit)
  - [`kernel_gen/dsl/mlir_gen/function_builder.py`](../../kernel_gen/dsl/mlir_gen/function_builder.py)
  - [`kernel_gen/dsl/mlir_gen/module_builder.py`](../../kernel_gen/dsl/mlir_gen/module_builder.py)
  - [`kernel_gen/dsl/mlir_gen/signature.py`](../../kernel_gen/dsl/mlir_gen/signature.py)
  - [`kernel_gen/dsl/ast/visitor.py`](../../kernel_gen/dsl/ast/visitor.py)
- 目标 `test`：
  - [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py)
  - [`test/dsl/test_ast.py`](../../test/dsl/test_ast.py)
  - [`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py)
  - [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py)
  - [`test/dsl/mlir_gen/emit`](../../test/dsl/mlir_gen/emit)
- 目标 `验收资产`：
  - `pytest -q test/dsl/test_emit_mlir.py`
  - `pytest -q test/dsl/test_ast.py`
  - `pytest -q test/dsl/test_ast_visitor.py`
  - `pytest -q test/dsl/test_mlir_gen.py`
  - `pytest -q test/dsl/mlir_gen/emit`
  - `rg -n "kernel_gen.dsl.emit_mlir" kernel_gen test`
- 目标 `功能实现`：
  - [`kernel_gen/dsl/mlir_gen/emit`](../../kernel_gen/dsl/mlir_gen/emit)
  - [`kernel_gen/dsl/mlir_gen`](../../kernel_gen/dsl/mlir_gen)

## 任务清单

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `S1` | `无` | `wt-20260414-emit-mlir-refactor-s1` | `20260414-emit-mlir-refactor-s1.md` |
| `S2` | `S1` | `wt-20260414-emit-mlir-refactor-s2` | `20260414-emit-mlir-refactor-s2.md` |
| `S3` | `S2` | `wt-20260414-emit-mlir-refactor-s3` | `20260414-emit-mlir-refactor-s3.md` |
| `S4` | `S3` | `wt-20260414-emit-mlir-refactor-s4` | `20260414-emit-mlir-refactor-s4.md` |
| `S5` | `S4` | `wt-20260414-emit-mlir-refactor-s5` | `20260414-emit-mlir-refactor-s5.md` |

## 前置依赖

- 本计划需等待 `ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md` 完成（双架构师终验通过且管理员执行 `-done-plan`）后再启动 `S1-S5`。

## 评审摘要

- 评审结论：`通过`
- 评审人：`守护最好的爱莉希雅`、`大闸蟹`
- 结论摘要：`本轮复核通过。此前最小阻断项已全部收口：AST -> MLIR 映射已补齐 FCAST，旧入口依赖范围已覆盖到 signature.py、test_ast.py 与 test/dsl/mlir_gen/emit/*，且 rg -n "kernel_gen.dsl.emit_mlir" kernel_gen test 已同步进入总体验收与 S3/S4/S5 阶段验收，当前计划可直接用于建任务推进。`

## 互评补充（2026-04-14 13:06 +0800）

- 互评人：`大闸蟹`
- 互评结论：`暂不通过`
- 已确认可保留项：
  - 计划目标明确，主方向成立：以 `kernel_gen/dsl/mlir_gen/emit` 收口、移除 [`emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py)、同步整理 `spec/test`，这条主线没有问题。
  - `S1 -> S5` 的串行大框架可保留，不需要整体重排。
- 最小阻断项：
  - AST -> MLIR 映射梳理还不完整。计划书在 [`AST -> MLIR 映射梳理（摘要）`](../../ARCHITECTURE/plan/dsl_emit_mlir_refactor_green_plan.md) 里没有覆盖当前真实 AST 集合中的 [`FCAST`](../../kernel_gen/dsl/ast/nodes.py)，但该节点已有公开语义“`fc(value, weight)` -> `nn.transpose + nn.matmul`”。若 `S1` 仍以“spec 已覆盖所有现有 AST 类”为验收项，就必须把 `FCAST` 以及它在 emit/spec/test 中的归属写清，否则“映射梳理完整”这一点现在还无法成立。
  - `emit_mlir.py` 移除边界未写全，现有阶段范围会漏掉真实依赖者。当前不只 [`function_builder.py`](../../kernel_gen/dsl/mlir_gen/function_builder.py) / [`module_builder.py`](../../kernel_gen/dsl/mlir_gen/module_builder.py) / `ast/visitor.py` 在引用旧入口，至少还有 [`kernel_gen/dsl/mlir_gen/signature.py`](../../kernel_gen/dsl/mlir_gen/signature.py)、[`test/dsl/test_ast.py`](../../test/dsl/test_ast.py) 以及 `test/dsl/mlir_gen/emit/*` 内的旧入口依赖；若按当前 `S2/S3` 可改文件直接删除 [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py)，会留下残余 import 或测试断链。这里需要二选一写清：要么把这些文件纳入本轮范围，要么明确哪些旧依赖本轮不删、计划目标随之收窄。
  - 验收命令不够完整，无法证明“旧入口已彻底移除”。计划书文档信息里已把 [`test/dsl/mlir_gen/emit`](../../test/dsl/mlir_gen/emit) 列为目标测试，但总体验收与 `S3/S4/S5` 只跑 `test_emit_mlir.py`、`test_ast_visitor.py`、`test_mlir_gen.py`，没有覆盖 `pytest -q test/dsl/mlir_gen/emit`；同时像 [`test/dsl/test_ast.py`](../../test/dsl/test_ast.py) 这种当前直接 import 旧入口的文件，也未进入回归集合。若目标是“删除旧文件后主仓无残余依赖”，验收命令至少要覆盖所有仍直接依赖旧入口的测试载体。
- 建议修订：
  - 在 `S1` 或映射摘要中补齐 `FCAST` 的唯一归属与 lowering 合同，并把“现有 AST 类全覆盖”明确对齐到真实节点清单。
  - 在 `S2/S3` 可改文件与阶段目标里补齐 `signature.py`、`test/dsl/test_ast.py` 以及其它当前 `rg "kernel_gen.dsl.emit_mlir"` 的残余文件，或者同步收窄“彻底移除”的目标表述。
  - 在总体验收和 `S3/S4/S5` 的必过命令里补上 `pytest -q test/dsl/mlir_gen/emit`，并把所有旧入口直连测试一并纳入最终回归集合。

## 修订记录（2026-04-14 13:40 +0800）

- 修订人：`守护最好的爱莉希雅`
- 修订摘要：
  - AST -> MLIR 映射摘要补齐 `FCAST` 并写明 `fc` lowering 归属。
  - `S2/S3` 可改文件补齐 `kernel_gen/dsl/mlir_gen/signature.py`、`test/dsl/test_ast.py` 与 `test/dsl/mlir_gen/emit/*`。
  - 总体验收与阶段验收补齐 `pytest -q test/dsl/mlir_gen/emit` 与 `pytest -q test/dsl/test_ast.py`，并新增 `rg -n "kernel_gen.dsl.emit_mlir" kernel_gen test` 作为旧入口清理校验。

## 修订记录（2026-04-14 13:52 +0800）

- 修订人：`守护最好的爱莉希雅`
- 修订摘要：
  - 将 `rg -n "kernel_gen.dsl.emit_mlir" kernel_gen test` 同步加入 `S3/S4/S5` 的验收必过项目，保证测试迁移、review、merge 均能复核旧入口清理状态。

## 复核结论（2026-04-14 13:12 +0800）

- 复核人：`大闸蟹`
- 复核结论：`暂不通过`
- 已收口项：
  - `FCAST` 已进入 AST -> MLIR 映射摘要，映射完整性问题已基本解决。
  - `kernel_gen/dsl/mlir_gen/signature.py`、`test/dsl/test_ast.py` 与 `test/dsl/mlir_gen/emit/*` 已纳入目标范围，旧入口依赖边界已基本补齐。
  - 总体验收已补上 `pytest -q test/dsl/mlir_gen/emit` 与 `rg -n "kernel_gen.dsl.emit_mlir" kernel_gen test`。
- 当前最小阻断项：
  - `rg -n "kernel_gen.dsl.emit_mlir" kernel_gen test` 仍只出现在总体验收与 `S2`，没有进入 `S3/S4/S5` 的阶段验收。由于 `S3` 本身就在修改 `test/dsl/test_emit_mlir.py`、`test/dsl/test_ast.py`、`test/dsl/test_ast_visitor.py`、`test/dsl/test_mlir_gen.py` 与 `test/dsl/mlir_gen/emit/*`，如果这些改动重新引入旧入口文本或导入，当前 `S4/S5` 只跑 pytest 也发现不了，最终链路就无法机械证明“emit_mlir.py 已彻底移除且无残余依赖”。
- 修订建议：
  - 将 `rg -n "kernel_gen.dsl.emit_mlir" kernel_gen test` 同步加入 `S3`、`S4`、`S5` 的验收必过项目，使测试迁移、review、merge 三段都能直接复核旧入口清理状态。

## 复核结论（2026-04-14 13:17 +0800）

- 复核人：`大闸蟹`
- 复核结论：`通过`
- 复核摘要：
  - `FCAST` 已进入 AST -> MLIR 映射摘要，映射范围与 lowering 归属已写清。
  - `kernel_gen/dsl/mlir_gen/signature.py`、`test/dsl/test_ast.py` 与 `test/dsl/mlir_gen/emit/*` 已纳入本轮范围，旧入口依赖边界完整。
  - `rg -n "kernel_gen.dsl.emit_mlir" kernel_gen test` 已同步进入总体验收以及 `S3`、`S4`、`S5` 的验收必过项目，测试迁移、review、merge 三段都能机械复核旧入口清理状态。
  - 当前计划书的阶段拆分、移除边界与回归命令已闭环，可以按当前版本建任务并通知 `神秘人` 推进。

## 计划目标

- 彻底移除 `kernel_gen/dsl/emit_mlir.py`，将其职责整合进 `kernel_gen/dsl/mlir_gen/emit`。
- 梳理现有 AST 种类与对应 MLIR lowering，更新 `spec/dsl/emit_mlir.md` 的映射与边界。
- 调整 `mlir_gen` / `ast_visitor` / test 入口到新的 emit 目录结构，保持结构清晰、可维护。
- 补齐测试与文档，使新结构与新 API 成为唯一稳定入口。

## 当前基线

- `kernel_gen/dsl/emit_mlir.py` 仍是核心实现，且 `mlir_gen/emit/*` 多数只是旧实现的薄封装。
- 现有 `kernel_gen/dsl/mlir_gen/emit` 已存在 `dispatch/control_flow/value/type_utils/shape_utils/call_arch/call_symbol`，但均依赖旧 `emit_mlir.py`。
- 多处核心路径仍 `from kernel_gen.dsl.emit_mlir import ...`（`mlir_gen/function_builder.py`、`mlir_gen/module_builder.py`、`mlir_gen/signature.py`、`ast/visitor.py`、`test/dsl/test_ast.py`、`test/dsl/mlir_gen/emit/*` 等）。
- `spec/dsl/emit_mlir.md` 仍指向旧文件为主要实现入口，AST -> MLIR 映射分散且与新拆分不一致。

## 方案比较与选型

- 不采用方案：仅在 `emit_mlir.py` 内部做局部清理。
  - 原因：无法消除模块边界混乱，也无法兑现“emit_mlir.py 不再存在”的要求。
- 不采用方案：只保留 `emit_mlir.py`，同时新增 `mlir_gen/emit` 作为二级入口。
  - 原因：旧 API 与新结构并存，维护成本更高。
- 采用方案：
  - 以 `kernel_gen/dsl/mlir_gen/emit` 为唯一实现入口；
  - 在代码、spec、test 中移除对 `kernel_gen/dsl/emit_mlir.py` 的依赖；
  - 将旧实现按 AST 族群与职责拆分到清晰模块，并更新测试映射。

## 公开 API 设计

- 新唯一入口：`from kernel_gen.dsl.mlir_gen.emit import EmitContext, emit_mlir`
- `EmitContext` 与 `LoweringError` 统一定义于 `kernel_gen/dsl/mlir_gen/emit/context.py`
- `kernel_gen/dsl/__init__.py` 不再暴露 `emit_mlir.py`；只暴露 `mlir_gen.emit` 入口（如需保留 facade，由 `mlir_gen.emit` 提供）

## AST -> MLIR 映射梳理（摘要）

> 详细映射与错误边界写入 `spec/dsl/emit_mlir.md`，本计划只列出梳理范围与分组。

- **结构节点（不直接发射 op）**
  - `ModuleAST` / `FunctionAST` / `BlockAST`：由 `mlir_gen` builder 负责组织，不直接在 emit 内发射。
- **控制流**
  - `ForAST` -> `symbol.for`（满足 symbol 语义时）或拒绝；循环参数保持 symbol 类型。
- **常量/变量/索引**
  - `ConstAST` / `VarAST` / `TensorAST` / `ScalarArgAST` / `PtrArgAST` / `TensorAxisAccessAST` / `SymbolToFloatAST` -> 常量或 `symbol.*` op。
- **DMA family**
  - `DmaAllocAST` / `DmaCopyAST` / `DmaCastAST` / `DmaViewAST` / `DmaReshapeAST` / `DmaFlattenAST` / `DmaFreeAST` / `LoadAST` / `StoreAST` -> `dma.*` ops。
- **NN family**
  - `NnUnaryAST` / `NnReduceAST` / `NnSoftmaxAST` / `MatmulAST` / `Img2ColAST` / `ConvAST` / `FCAST` / `NnBroadcastAST` / `NnBroadcastToAST` / `NnTransposeAST` -> `nn.*` ops 或组合（conv 走 img2col + reshape + matmul + reshape；fc 走 transpose + matmul）。
- **表达式**
  - `BinaryExprAST` / `CompareExprAST` -> `nn.*` 或 `symbol.*`（按 operand 类型分支）。
- **Arch family**
  - `ArchQueryAST` / `ArchGetDynamicMemoryAST` / `ArchBarrierAST` / `ArchLaunchKernelAST` -> `arch.*` ops。
- **Call 统一入口**
  - `PythonCalleeCallAST` 仅做路由，禁止在 dispatch 层直接实现 family 细节。

## 完成态定义

- `kernel_gen/dsl/emit_mlir.py` 不再存在。
- 所有 `emit_mlir` 入口与 helper 都位于 `kernel_gen/dsl/mlir_gen/emit`。
- `spec/dsl/emit_mlir.md` 已明确 AST -> MLIR 映射与错误边界。
- `test/dsl/*` 与 `test/dsl/mlir_gen/emit/*` 通过，引用路径完成迁移。
- 新增或改动的模块与关键函数均补齐功能说明、使用示例、创建者、最后修改人，以及 `spec/test/功能实现` 链接（满足根目录 `AGENTS.md`）。

## 验收设计

- 必过命令：
  - `pytest -q test/dsl/test_emit_mlir.py`
  - `pytest -q test/dsl/test_ast.py`
  - `pytest -q test/dsl/test_ast_visitor.py`
  - `pytest -q test/dsl/test_mlir_gen.py`
  - `pytest -q test/dsl/mlir_gen/emit`
  - `rg -n "kernel_gen.dsl.emit_mlir" kernel_gen test`

## 阶段拆分

### S1：spec 与映射梳理

#### 阶段目标

- 明确 AST 种类与对应 MLIR 映射边界，更新 spec。

#### 目标 spec / API

- `spec/dsl/emit_mlir.md`
- `spec/dsl/ast.md`

#### 可改文件

- `spec/dsl/emit_mlir.md`
- `spec/dsl/ast.md`
- `spec/dsl/mlir_gen.md`

#### 预期示例代码

```text
BinaryExprAST(op="add") + memory operands -> nn.add
ForAST + symbol bounds -> symbol.for
```

#### 目标验收资产

- `spec/dsl/emit_mlir.md` AST -> MLIR 对应表

#### 验收必过项目

- 文本核对：spec 已覆盖所有现有 AST 类（含 `FCAST`）

#### 任务新建建议

- `任务类型：spec`
- `任务目标：梳理 AST -> MLIR 映射并补齐 emit spec`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260414-emit-mlir-refactor-s1.md`

### S2：核心实现重构

#### 阶段目标

- 将 `emit_mlir.py` 拆分并迁移至 `mlir_gen/emit`，并删除旧文件。

#### 目标 spec / API

- `spec/dsl/emit_mlir.md`
- `公开 API：kernel_gen.dsl.mlir_gen.emit.EmitContext/emit_mlir`

#### 可改文件

- `kernel_gen/dsl/mlir_gen/emit/*`
- `kernel_gen/dsl/mlir_gen/function_builder.py`
- `kernel_gen/dsl/mlir_gen/module_builder.py`
- `kernel_gen/dsl/mlir_gen/signature.py`
- `kernel_gen/dsl/ast/visitor.py`
- `kernel_gen/dsl/__init__.py`
- `kernel_gen/dsl/emit_mlir.py`（删除）

#### 预期示例代码

```python
from kernel_gen.dsl.mlir_gen.emit import EmitContext, emit_mlir
value = emit_mlir(node, ctx)
```

#### 目标验收资产

- 代码中不再出现 `kernel_gen.dsl.emit_mlir` import

#### 验收必过项目

- `rg -n "kernel_gen.dsl.emit_mlir" kernel_gen test` 无命中

#### 任务新建建议

- `任务类型：build`
- `任务目标：完成 emit_mlir 迁移并删除旧文件`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260414-emit-mlir-refactor-s2.md`

### S3：测试与样例迁移

#### 阶段目标

- 更新 tests / examples 指向新入口并补齐缺口。

#### 目标 spec / API

- `spec/dsl/emit_mlir.md`

#### 可改文件

- `test/dsl/test_emit_mlir.py`
- `test/dsl/test_ast.py`
- `test/dsl/test_ast_visitor.py`
- `test/dsl/test_mlir_gen.py`
- `test/dsl/mlir_gen/emit/*`

#### 验收必过项目

- `pytest -q test/dsl/test_emit_mlir.py`
- `pytest -q test/dsl/test_ast.py`
- `pytest -q test/dsl/test_ast_visitor.py`
- `pytest -q test/dsl/test_mlir_gen.py`
- `pytest -q test/dsl/mlir_gen/emit`
- `rg -n "kernel_gen.dsl.emit_mlir" kernel_gen test`

#### 任务新建建议

- `任务类型：build`
- `任务目标：迁移 emit 相关测试到新入口`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260414-emit-mlir-refactor-s3.md`

### S4：review

#### 阶段目标

- review S2/S3 变更，核对映射与验收命令。

#### 验收必过项目

- `pytest -q test/dsl/test_emit_mlir.py`
- `pytest -q test/dsl/test_ast.py`
- `pytest -q test/dsl/test_ast_visitor.py`
- `pytest -q test/dsl/test_mlir_gen.py`
- `pytest -q test/dsl/mlir_gen/emit`
- `rg -n "kernel_gen.dsl.emit_mlir" kernel_gen test`

#### 任务新建建议

- `任务类型：review`
- `任务目标：review emit_mlir 重构与映射`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260414-emit-mlir-refactor-s4.md`

### S5：merge

#### 阶段目标

- 合并变更并完成终验。

#### 验收必过项目

- `pytest -q test/dsl/test_emit_mlir.py`
- `pytest -q test/dsl/test_ast.py`
- `pytest -q test/dsl/test_ast_visitor.py`
- `pytest -q test/dsl/test_mlir_gen.py`
- `pytest -q test/dsl/mlir_gen/emit`
- `rg -n "kernel_gen.dsl.emit_mlir" kernel_gen test`

#### 任务新建建议

- `任务类型：merge`
- `任务目标：合并 emit_mlir 重构`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260414-emit-mlir-refactor-s5.md`

## 当前主仓终验（2026-04-16 01:00 +0800）

- 终验人：`守护最好的爱莉希雅`
- 当前结论：`不通过`
- 依据：
  - `test -e kernel_gen/dsl/emit_mlir.py && echo EXISTS || echo MISSING` -> `MISSING`；旧文件已删除。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_emit_mlir.py` -> `72 passed`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_ast.py` -> `45 passed, 2 failed`；当前失败点集中在 `barrier` DSL 入口仍按旧 `MemorySpace.TSM/TLM` 文本写测试，实际实现已切到 `BarrierVisibility.TSM/TLM`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_ast_visitor.py` -> `202 passed, 1 failed`；当前失败点为 `test_build_func_op_rejects_dma_alloc_helper_with_invalid_space` 仍期望 `TypeError`，实际抛出 `AstVisitorError: alloc space must be MemorySpace`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_mlir_gen.py` -> `149 passed, 1 failed`；当前失败点与上条相同，仍是 `alloc space` 异常类型合同不一致。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/mlir_gen/emit` -> `29 passed`。
  - `rg -n "kernel_gen\\.dsl\\.emit_mlir" kernel_gen test` -> 无命中；旧入口残留已清空。
- 最小阻断项：
  - [`test/dsl/test_ast.py`](../../test/dsl/test_ast.py)、[`spec/dsl/ast.md`](../../spec/dsl/ast.md)、[`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md) 与 [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md) 的 `barrier` DSL 口径仍保留旧 `MemorySpace.TSM/TLM` / `MemorySpace list` / `#nn.space<...>` 文本，但当前 [`kernel_gen/dsl/ast/parser.py`](../../kernel_gen/dsl/ast/parser.py) 与 [`kernel_gen/dsl/ast/nodes.py`](../../kernel_gen/dsl/ast/nodes.py) 已切到 `BarrierVisibility.TSM/TLM`。这会直接导致 `test/dsl/test_ast.py` 的 `arch_barrier` 用例失败。
  - [`kernel_gen/dsl/mlir_gen/function_builder.py`](../../kernel_gen/dsl/mlir_gen/function_builder.py) 当前只把 `slice space must be MemorySpace` 与 `cast dtype must be NumericType` 映射为 `TypeError`；`alloc space must be MemorySpace` 仍按 `AstVisitorError` 抛出。但 [`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py) 与 [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py) 仍固定期望 `TypeError`，当前实现与测试合同未统一。
- 终验说明：
  - 虽然 `emit_mlir.py` 已删除、旧入口 import 已清空，且 `test_emit_mlir.py` / `test/dsl/mlir_gen/emit` 已通过，但本计划正文列出的主验收命令当前未全绿，因此不得进入归档链。
  - 本计划正文的前置依赖仍要求 [`ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md`](../../ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md) 完成双架构师终验并由管理员执行 `-done-plan` 后，再继续本计划后续推进；当前该计划仍处于 `进行中`。
  - 因此本计划当前既不满足功能终验条件，也不满足归档前置条件。

## 修复任务补建（2026-04-16 01:00 +0800）

- 补建人：`守护最好的爱莉希雅`
- 修复任务：[`T-20260416-9021c1c2`](../../TODO.md)
- 任务类型：`build`
- 唯一修复范围：
  - 不再继续推进预建的 [`T-20260414-6d614822`](../../TODO.md) 与 [`T-20260414-928d6f0b`](../../TODO.md)。这两条是早于当前主仓阻断面创建的 `review/merge` 占位任务；当前主仓失败点已变成共享 DSL 合同与异常类型合同，继续推进它们不能收口现状。
  - `barrier` 旧 `MemorySpace.TSM/TLM` 文本的共享阻断，沿现有 [`T-20260415-89abd30e`](../../TODO.md) 继续收口，不在本计划下重复创建同类修复链。
  - 本计划下新补建的唯一修复任务只处理剩余独立阻断：统一 `build_func_op(...)` 对非法 `alloc space` 的异常类型合同，使 [`kernel_gen/dsl/mlir_gen/function_builder.py`](../../kernel_gen/dsl/mlir_gen/function_builder.py)、[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py) 与 [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py) 回到同一口径；完成后重新复跑本计划全部验收命令。
- 续推口径：
  - 当前不得创建归档任务，也不得执行 `-done-plan`。
  - 当前唯一继续项应以 [`T-20260416-9021c1c2`](../../TODO.md) 为准，并显式依赖共享阻断链 [`T-20260415-89abd30e`](../../TODO.md) 与前置计划继续项 [`T-20260416-65613a5a`](../../TODO.md)；待这两个依赖完成后，再推进本计划修复链。
  - 待共享 `barrier/TLM` 文本阻断与 `dsl_mlir_gen_expectation` 前置链完成、且 [`T-20260416-9021c1c2`](../../TODO.md) 收口 `alloc space` 异常类型后，再回到本计划重新终验。

## 当前主仓终验（2026-04-16 14:24 +0800）

- 终验人：`守护最好的爱莉希雅`
- 当前结论：`不通过`
- 依据：
  - 管理员已同步 [`T-20260416-9021c1c2`](../../DONE.md) 由李白合入主仓并 `-done`，提交为 `f29797e`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_emit_mlir.py` -> `71 passed, 1 failed`；失败仍为 [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py) 的 `test_emit_mlir_infer_expr_type_branches`，当前 scalar-only add 未按合同报 `nn.add requires at least one nn.memory operand`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_ast.py` -> `47 passed`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_ast_visitor.py` -> `200 passed, 3 failed`；当前失败集中在 [`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py) 的 `alloc space must be MemorySpace` 仍未转成 `TypeError`、`conv2d_img2col2d_tiled_npu_demo` helper call 仍报 `Unsupported call expression`，以及与 `test_emit_mlir.py` 同源的 scalar-only add 类型推导回归。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_mlir_gen.py` -> `132 passed, 19 failed`；首个业务失败仍是 helper call 路径未闭合，`img2col1d` / `img2col2d` / `matmul` / `reduce_*` / `softmax` / `conv` 等 helper call 仍报 `Unsupported call expression`，同时 `alloc space must be MemorySpace` 对外异常类型仍与测试合同不一致。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/mlir_gen/emit` -> `30 passed`。
  - `rg -n "kernel_gen\\.dsl\\.emit_mlir" kernel_gen test` -> 无命中；旧入口残留已清空。
- 最小阻断项：
  - [`kernel_gen/dsl/mlir_gen/emit/call_nn.py`](../../kernel_gen/dsl/mlir_gen/emit/call_nn.py) / [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py) / [`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py) 当前对 scalar-only add 的类型推导合同不一致；计划正文要求的 emit 层验收仍未恢复通过。
  - [`kernel_gen/dsl/mlir_gen/function_builder.py`](../../kernel_gen/dsl/mlir_gen/function_builder.py) 对 `alloc space must be MemorySpace` 的公开异常类型仍未与 [`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py) / [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py) 统一。
  - imported nn helper call 的解析路径在主仓仍未闭合，导致 [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py) 与 [`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py) 中的 `img2col1d / img2col2d / matmul / reduce_* / softmax / conv` 等 helper call 回归仍失败。
- 终验说明：
  - 虽然 `kernel_gen/dsl/emit_mlir.py` 已删除、旧入口 import 已清空，且 [`test/dsl/test_ast.py`](../../test/dsl/test_ast.py) 与 [`test/dsl/mlir_gen/emit`](../../test/dsl/mlir_gen/emit) 已通过，但本计划正文列出的主验收命令当前仍未全绿，因此当前仍`不通过`，且`不可进入归档链`。
  - 本计划正文的前置依赖仍要求 [`ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md`](../../ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md) 完成双架构师终验并由管理员执行 `-done-plan` 后，再进入归档链；当前该计划仍处于 `进行中`，也尚未满足本计划归档前置条件。
- 唯一继续项：
  - 保留 [`T-20260416-8d6903cc`](../../TODO.md) 作为当前唯一修复任务；任务目标已直接收口本轮最小阻断项：scalar-only add 类型推导、alloc 非法 space 异常类型、imported nn helper call 解析回归，并恢复本计划正文点名的 pytest 总验收。
  - 已完成的 [`T-20260416-9021c1c2`](../../DONE.md) 不再继续复用；当前不得创建归档任务，也不得执行 `-done-plan`。

## 当前主仓终验复核（2026-04-16 14:20 +0800）

- 终验人：`大闸蟹`
- 当前结论：`不通过`
- 依据：
  - `test -e kernel_gen/dsl/emit_mlir.py && echo EXISTS || echo MISSING` -> `MISSING`；旧文件仍已删除。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_emit_mlir.py` -> `1 failed, 71 passed`；失败用例为 [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py) 的 `test_emit_mlir_infer_expr_type_branches`，当前 scalar-only `BinaryExprAST(op="add")` 未再抛出 `_LoweringError("nn.add requires at least one nn.memory operand")`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_ast.py` -> `47 passed`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_ast_visitor.py` -> `exit=3`，先出现 `55 passed` 后 pytest 生成失败报告时触发内部异常；用 `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_ast_visitor.py -x` 复核到首个业务失败为 `test_build_func_op_rejects_dma_alloc_helper_with_invalid_space`，当前仍抛 `AstVisitorError: alloc space must be MemorySpace`，未按测试合同转为 `TypeError`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_mlir_gen.py` -> `exit=3`，失败报告阶段触发 pytest 内部异常；用 `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_mlir_gen.py -x` 复核到首个业务失败为 `test_build_func_op_supports_img2col1d_helper_call`，当前 `build_func_op` 对 imported `img2col1d(...)` helper call 仍报 `AstVisitorError: Unsupported call expression`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/mlir_gen/emit` -> `30 passed`。
  - `rg -n "kernel_gen\.dsl\.emit_mlir" kernel_gen test` -> `exit=1` 且无输出；旧入口 import 未检出残留。
  - [`TODO.md`](../../TODO.md) 当前仍显示 [`ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md`](../../ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md) 为 `14 / 13 / 1 / 进行中`，本计划正文写明的前置归档条件仍未满足。
- 最小阻断项：
  - [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py) 与 [`kernel_gen/dsl/mlir_gen/emit`](../../kernel_gen/dsl/mlir_gen/emit) 的 scalar-only add 类型推导合同不一致；当前实现已不再按 `nn.add requires at least one nn.memory operand` 报错。
  - [`kernel_gen/dsl/mlir_gen/function_builder.py`](../../kernel_gen/dsl/mlir_gen/function_builder.py)、[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py) 与 [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py) 的非法 `alloc space` 异常类型合同仍未统一。
  - [`kernel_gen/dsl/ast/parser.py`](../../kernel_gen/dsl/ast/parser.py)、[`kernel_gen/dsl/mlir_gen/function_builder.py`](../../kernel_gen/dsl/mlir_gen/function_builder.py) 与 [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py) 对 imported `nn` helper call 的解析仍未闭合，最先暴露为 `img2col1d(...)` 报 `Unsupported call expression`。
  - 本计划前置依赖 [`ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md`](../../ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md) 仍在进行中，尚未满足“双架构师终验通过并完成归档”的启动/归档条件。
- 终验说明：
  - 尽管 [`T-20260416-9021c1c2`](../../DONE.md) 已合入主仓，当前主仓仍未满足本计划正文列出的验收命令，因此本计划当前仍`不通过`，且`不可进入归档链`。
- 修复任务：[`T-20260416-8d6903cc`](../../TODO.md)
- `worktree`：`wt-20260416-emit-mlir-refactor-r2`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/16/20260416-emit-mlir-refactor-r2.md`
- 修复范围：
  - 收口 scalar-only add 类型推导合同，恢复 [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py)。
  - 统一 `build_func_op(...)` 对非法 `alloc space` 的异常类型合同，恢复 [`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py) 与 [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py) 对应用例。
  - 收口 imported `nn` helper call 解析回归，至少恢复 [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py) 中 `img2col1d` 等 helper call 用例。
  - 修复后重新复跑本计划全部验收命令，并继续核对 [`ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md`](../../ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md) 的前置状态。
- 续推说明：
  - 已完成的 [`T-20260416-9021c1c2`](../../DONE.md) 不再继续复用。
  - 以 [`T-20260416-8d6903cc`](../../TODO.md) 作为本轮唯一继续项；待其完成并回到本计划复核通过后，再判断是否具备归档链条件。

## 当前主仓终验复核（2026-04-16 17:01 +0800）

- 终验人：`大闸蟹`
- 当前结论：`不通过`
- 依据：
  - 管理员已同步 [`T-20260416-8d6903cc`](../../DONE.md) 由李白合入主仓并 `-done`，提交为 `056c937`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_emit_mlir.py` -> `1 failed, 71 passed`；失败用例仍为 [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py) 的 `test_emit_mlir_infer_expr_type_branches`，当前 scalar-only `BinaryExprAST(op="add")` 未按既有合同报 `_LoweringError("nn.add requires at least one nn.memory operand")`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_ast.py` -> `47 passed`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_ast_visitor.py -x` -> `1 failed, 55 passed`；首个业务失败仍为 [`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py) 的 `test_build_func_op_rejects_dma_alloc_helper_with_invalid_space`，当前仍抛 `AstVisitorError: alloc space must be MemorySpace`，未按测试合同转成 `TypeError`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_mlir_gen.py -x` -> `1 failed, 27 passed`；首个业务失败仍为 [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py) 的 `test_build_func_op_supports_img2col1d_helper_call`，当前 imported `img2col1d(...)` helper call 仍报 `AstVisitorError: Unsupported call expression`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/mlir_gen/emit` -> `30 passed`。
  - `rg -n "kernel_gen\.dsl\.emit_mlir" kernel_gen test` -> `exit=1` 且无输出；旧入口 import 未检出残留。
  - [`TODO.md`](../../TODO.md) 当前已将 [`ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md`](../../ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md) 调整回 `15 / 14 / 1 / 进行中`，本计划正文写明的前置依赖仍未满足。
- 最小阻断项：
  - [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py) 与 [`kernel_gen/dsl/mlir_gen/emit`](../../kernel_gen/dsl/mlir_gen/emit) 的 scalar-only add 类型推导合同仍不一致。
  - [`kernel_gen/dsl/mlir_gen/function_builder.py`](../../kernel_gen/dsl/mlir_gen/function_builder.py)、[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py) 与 [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py) 的非法 `alloc space` 异常类型合同仍未统一。
  - imported `nn` helper call 的解析路径在主仓仍未闭合，最先暴露为 [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py) 中 `img2col1d(...)` 仍报 `Unsupported call expression`。
  - 本计划前置依赖 [`ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md`](../../ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md) 仍在进行中，尚未满足“双架构师终验通过并完成归档”的启动/归档条件。
- 终验说明：
  - 尽管 [`T-20260416-8d6903cc`](../../DONE.md) 已合入主仓，当前主仓仍未满足本计划正文列出的验收命令，因此本计划当前仍`不通过`，且`不可进入归档链`。
- 修复任务：[`T-20260416-093fce7c`](../../TODO.md)
- `worktree`：`wt-20260416-emit-mlir-refactor-r3`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/16/20260416-emit-mlir-refactor-r3.md`
- 修复范围：
  - 收口 scalar-only add 类型推导合同，恢复 [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py)。
  - 统一 `build_func_op(...)` 对非法 `alloc space` 的异常类型合同，恢复 [`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py) 与 [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py) 对应用例。
  - 收口 imported `nn` helper call 解析回归，至少恢复 [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py) 中 `img2col1d` helper call 用例。
  - 修复后重新复跑本计划全部验收命令，并继续核对前置计划 [`ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md`](../../ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md) 的归档状态。
- 续推说明：
  - 已完成的 [`T-20260416-8d6903cc`](../../DONE.md) 不再继续复用。
  - 以 [`T-20260416-093fce7c`](../../TODO.md) 作为本轮唯一继续项，并显式依赖 [`T-20260416-16fcb9bf`](../../TODO.md)；待前置修复链与本任务均完成后，再回到本计划重新终验。

## 当前主仓终验（2026-04-16 17:02 +0800）

- 终验人：`守护最好的爱莉希雅`
- 当前结论：`不通过`
- 归档结论：`不可进入归档链`
- 当前主仓实跑：
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_emit_mlir.py` -> `1 failed, 71 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_ast.py` -> `47 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_ast_visitor.py` -> `3 failed, 200 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_mlir_gen.py -x` -> `1 failed, 27 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/mlir_gen/emit` -> `30 passed`
  - `rg -n "kernel_gen\\.dsl\\.emit_mlir" kernel_gen test` -> `exit=1` 且无输出
- 最小阻断项：
  - [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py) 的 `test_emit_mlir_infer_expr_type_branches` 仍失败；当前 scalar-only add 未按既有合同报 `nn.add requires at least one nn.memory operand`。
  - [`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py) 仍未收口 `alloc space must be MemorySpace` 的公开异常类型；当前仍抛 `AstVisitorError`，未统一到测试要求的 `TypeError`。
  - [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py) 的首个业务失败仍是 `test_build_func_op_supports_img2col1d_helper_call`；imported `nn` helper call 解析仍报 `Unsupported call expression`。
  - [`TODO.md`](../../TODO.md) 当前已不是“完成待检查”，而是 `6 / 5 / 1 / 进行中`；这也说明本计划当前尚未达到可归档状态。
- 唯一继续项：
  - 保留 [`T-20260416-093fce7c`](../../TODO.md) 作为本轮唯一继续项。
  - 已完成的 [`T-20260416-8d6903cc`](../../DONE.md) 不再继续复用；当前不得创建归档任务，也不得执行 `-done-plan`。

## 当前主仓终验复核（2026-04-16 19:26 +0800）

- 终验人：`大闸蟹`
- 当前结论：`不通过`
- 依据：
  - 管理员已同步 [`T-20260416-093fce7c`](../../DONE.md) 由李白合入主仓并 `-done`，完成时间为 `2026-04-16 19:21:30 +0800`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_emit_mlir.py` -> `1 failed, 71 passed`；失败用例仍为 [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py) 的 `test_emit_mlir_infer_expr_type_branches`，当前 scalar-only `BinaryExprAST(op="add")` 未按既有合同报 `_LoweringError("nn.add requires at least one nn.memory operand")`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_ast.py` -> `47 passed`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_ast_visitor.py -x` -> `1 failed, 55 passed`；首个业务失败仍为 [`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py) 的 `test_build_func_op_rejects_dma_alloc_helper_with_invalid_space`，当前仍抛 `AstVisitorError: alloc space must be MemorySpace`，未按测试合同转成 `TypeError`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_mlir_gen.py -x` -> `1 failed, 27 passed`；首个业务失败仍为 [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py) 的 `test_build_func_op_supports_img2col1d_helper_call`，当前 imported `img2col1d(...)` helper call 仍报 `AstVisitorError: Unsupported call expression`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/mlir_gen/emit` -> `30 passed`。
  - `rg -n "kernel_gen\.dsl\.emit_mlir" kernel_gen test` -> `exit=1` 且无输出；旧入口 import 未检出残留。
  - 当前 [`TODO.md`](../../TODO.md) 已从 `6 / 6 / 0 / 完成待检查` 回退为 `7 / 6 / 1 / 进行中`，说明本轮终验未通过且已补建新的继续项。
  - 本计划正文写明的前置依赖 [`ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md`](../../ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md) 当前仍为 `进行中`，尚未满足“双架构师终验通过并完成归档”的条件。
- 最小阻断项：
  - [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py) 与 [`kernel_gen/dsl/mlir_gen/emit`](../../kernel_gen/dsl/mlir_gen/emit) 的 scalar-only add 类型推导合同仍不一致。
  - [`kernel_gen/dsl/mlir_gen/function_builder.py`](../../kernel_gen/dsl/mlir_gen/function_builder.py)、[`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py) 与 [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py) 的非法 `alloc space` 异常类型合同仍未统一。
  - imported `nn` helper call 的解析路径在主仓仍未闭合，最先暴露为 [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py) 中 `img2col1d(...)` 仍报 `Unsupported call expression`。
  - 前置计划 [`ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md`](../../ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md) 仍未完成归档，本计划当前也不具备进入归档链条件。
- 终验说明：
  - 尽管 [`T-20260416-093fce7c`](../../DONE.md) 已合入主仓，当前主仓仍未满足本计划正文列出的验收命令，因此本计划当前仍`不通过`，且`不可进入归档链`。
- 修复任务：[`T-20260416-c695f3a2`](../../TODO.md)
- `worktree`：`wt-20260416-emit-mlir-refactor-r4`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/16/20260416-emit-mlir-refactor-r4.md`
- 修复范围：
  - 收口 scalar-only add 类型推导合同，恢复 [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py)。
  - 统一 `build_func_op(...)` 对非法 `alloc space` 的异常类型合同，恢复 [`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py) 与 [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py) 对应用例。
  - 收口 imported `nn` helper call 解析回归，至少恢复 [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py) 中 `img2col1d` helper call 用例。
  - 修复后重新复跑本计划全部验收命令，并继续核对前置计划 [`ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md`](../../ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md) 的归档状态。
- 续推说明：
  - 已完成的 [`T-20260416-093fce7c`](../../DONE.md) 不再继续复用。
  - 以 [`T-20260416-c695f3a2`](../../TODO.md) 作为本轮唯一继续项，并显式依赖 [`T-20260416-9a89b3e4`](../../TODO.md)；待前置修复链与本任务均完成后，再回到本计划重新终验。

## 当前主仓终验（2026-04-16 19:28 +0800）

- 终验人：`守护最好的爱莉希雅`
- 当前结论：`不通过`
- 归档结论：`不可进入归档链`
- 当前主仓实跑：
  - `test -e kernel_gen/dsl/emit_mlir.py && echo EXISTS || echo MISSING` -> `MISSING`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_emit_mlir.py` -> `1 failed, 71 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_ast.py` -> `47 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_ast_visitor.py` -> `3 failed, 200 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_mlir_gen.py -x` -> `1 failed, 27 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/mlir_gen/emit` -> `30 passed`
  - `rg -n "kernel_gen\\.dsl\\.emit_mlir" kernel_gen test` -> `exit=1` 且无输出
- 最小阻断项：
  - [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py) 的 `test_emit_mlir_infer_expr_type_branches` 仍失败；当前 scalar-only add 未按既有合同报 `nn.add requires at least one nn.memory operand`。
  - [`test/dsl/test_ast_visitor.py`](../../test/dsl/test_ast_visitor.py) 仍未收口 `alloc space must be MemorySpace` 的公开异常类型；当前仍抛 `AstVisitorError`，未统一到测试要求的 `TypeError`。
  - [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py) 的首个业务失败仍是 `test_build_func_op_supports_img2col1d_helper_call`；imported `nn` helper call 解析仍报 `Unsupported call expression`。
  - [`TODO.md`](../../TODO.md) 当前已不是“6/6/0 完成待检查”，而是 `7 / 6 / 1 / 进行中`；同时前置计划 [`ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md`](../../ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md) 仍未归档完成，本计划当前也不具备进入归档链条件。
- 唯一继续项：
  - 保留 [`T-20260416-c695f3a2`](../../TODO.md) 作为本轮唯一继续项。
  - 已完成的 [`T-20260416-093fce7c`](../../DONE.md) 不再继续复用；当前不得创建归档任务，也不得执行 `-done-plan`。

## 当前主仓终验口径同步（2026-04-16 20:53 +0800）

- 同步人：`咯咯咯`
- 当前结论：`通过（功能口径已收口）`
- 归档结论：`不可进入归档链`
- 同步依据：
  - `git -C /home/lfr/kernelcode_generate/wt-20260416-emit-mlir-refactor-r4 pull --ff-only origin main` -> `Updating 8f20a27..3587654`，当前口径已对齐最新主线。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_emit_mlir.py test/dsl/test_ast.py test/dsl/test_ast_visitor.py test/dsl/test_mlir_gen.py test/dsl/mlir_gen/emit` -> `505 passed, 1 warning in 2.17s`
  - `rg -n "kernel_gen\.dsl\.emit_mlir" kernel_gen test` -> `exit=1` 且无输出
- 当前主仓口径：
  - scalar-only add 类型推导、`alloc` 非法 `space` 异常类型与 imported `nn` helper call 三项阻断已在最新主线自然收口；`2026-04-16 19:26 +0800` 与 `2026-04-16 19:28 +0800` 两段保留为收口前历史快照，不再作为现行继续依据。
  - 本计划正文点名的 pytest 总体验收当前已全绿，旧入口清理口径继续以 `kernel_gen.dsl.emit_mlir` 无残留为准。
- 唯一继续项：
  - 本计划内不再保留新的实现修复任务；[`T-20260416-c695f3a2`](../../TODO.md) 完成后，不再继续等待已完成并停用的 [`T-20260416-08225f2f`](../../DONE.md)。
  - 前置计划 [`ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md`](../../ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md) 的最新双架构师终验已统一写为“`通过` / `可进入归档链`”；因此，本计划当前唯一后续动作改为等待前置计划按该终验结论完成归档链，而不是继续等待前置计划的实现/审查/合并任务。
- 后续归档说明：
  - 当前不得直接对本计划执行 `-done-plan`，也不再为本计划补建新的实现修复任务。
  - 待前置计划完成其归档链后，管理员再为本计划创建唯一归档任务，并按“归档任务 -> 合并 -> 归档任务 `-done` -> 原计划 `-done-plan`”链路推进。

## 当前主仓终验复核（2026-04-16 22:12 +0800）

- 终验人：`大闸蟹`
- 当前结论：`通过`
- 归档结论：`可进入归档链`
- 验证基线：
  - 以最新同步现场 ` /home/lfr/kernelcode_generate/wt-20260416-emit-mlir-refactor-r4 ` 为终验基线；该基线已在本页 [`当前主仓终验口径同步（2026-04-16 20:53 +0800）`](#当前主仓终验口径同步2026-04-16-2053-0800) 中写明。
  - 该同步现场当时已对齐最新主线：`git -C /home/lfr/kernelcode_generate/wt-20260416-emit-mlir-refactor-r4 pull --ff-only origin main -> Updating 8f20a27..3587654`。
  - 基线现场验收结果已写明：
    - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_emit_mlir.py test/dsl/test_ast.py test/dsl/test_ast_visitor.py test/dsl/test_mlir_gen.py test/dsl/mlir_gen/emit` -> `505 passed, 1 warning`
    - `rg -n "kernel_gen\.dsl\.emit_mlir" kernel_gen test` -> `exit=1` 且无输出
  - 本轮在当前仓库补跑同一组验收，结果与基线一致：
    - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_emit_mlir.py test/dsl/test_ast.py test/dsl/test_ast_visitor.py test/dsl/test_mlir_gen.py test/dsl/mlir_gen/emit` -> `505 passed, 1 warning in 2.72s`
    - `rg -n "kernel_gen\.dsl\.emit_mlir" kernel_gen test` -> `exit=1` 且无输出
- 终验说明：
  - 前置计划 [`ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md`](../../ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md) 当前已完成归档链并执行 `-done-plan`；此前阻挡本计划归档的前置条件已消失。
  - 因此，本计划应以最新同步现场已收口、且当前仓库复核结果一致为准；本页 `19:26 +0800`、`19:28 +0800` 的不通过段继续仅作历史快照，不再作为现行继续依据。
- 当前状态：
  - [`T-20260416-c695f3a2`](../../DONE.md) 已完成并停用，不再续接。
  - 本计划当前不再保留新的实现修复任务；管理员可按现行流程补建唯一归档任务。

## 当前同步现场终验（2026-04-16 22:21 +0800）

- 终验人：`守护最好的爱莉希雅`
- 当前结论：`不通过`
- 归档结论：`不可进入归档链`
- 验证基线：
  - 同步现场：`/home/lfr/kernelcode_generate`
  - 验证时间：`2026-04-16 22:21:10 +0800`
  - [`TODO.md`](../../TODO.md) 当前显示本计划为 `7 / 7 / 0 / 完成待检查`。
  - 前置计划 [`ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md`](../../ARCHITECTURE/plan/dsl_mlir_gen_expectation_green_plan.md) 已完成归档并执行 `-done-plan`；本轮不再以前置计划状态作为阻断。
- 当前同步现场实跑：
  - `test -e kernel_gen/dsl/emit_mlir.py && echo EXISTS || echo MISSING` -> `MISSING`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_emit_mlir.py` -> `72 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_ast.py` -> `47 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_ast_visitor.py` -> `203 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_mlir_gen.py` -> `153 passed, 1 warning`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/mlir_gen/emit` -> `30 passed`
  - `rg -n "kernel_gen\\.dsl\\.emit_mlir" kernel_gen test` -> `exit=1` 且无输出
  - `PYTHONDONTWRITEBYTECODE=1 python - <<'PY' ... importlib.import_module(\"expectation.utils.compare\") ... PY` -> `ModuleNotFoundError: No module named 'kernel_gen.dsl.emit_mlir'`
  - `rg -n "kernel_gen\\.dsl\\.emit_mlir" spec expectation ARCHITECTURE` -> 命中：
    - [`expectation/utils/compare.py`](../../expectation/utils/compare.py)
    - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
- 最小阻断项：
  - [`expectation/utils/compare.py`](../../expectation/utils/compare.py) 第 38 行仍直接 `from kernel_gen.dsl.emit_mlir import _memory_to_nn_type`；由于 [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py) 已按本计划删除，当前同步现场 `import expectation.utils.compare` 直接失败。这不是旧主仓差异，而是当前同步现场中的真实断链。
  - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md) 第 46 行仍把 `kernel_gen.dsl.emit_mlir` facade 写成公开入口，并在同文件第 64 行把已删除的 [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py) 描述为“只允许保留 facade 入口、转发或兼容壳层职责”。这与本计划“删除旧文件并以 `kernel_gen.dsl.mlir_gen.emit` 作为唯一入口”的选型与完成态不一致。
- 终验说明：
  - 按本计划正文点名的机械验收命令，当前同步现场的功能测试已经全绿，`kernel_gen/test` 范围内对旧 dotted import 的清理也已完成。
  - 但本计划的公开选型并不是“只要 pytest 通过即可”，而是“删除 [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py) 并收口为 `kernel_gen.dsl.mlir_gen.emit` 唯一入口”。当前同步现场仍保留一个真实的 expectation 运行时断链，以及一处 target spec 的公开合同残留，因此本计划当前仍`不通过`，且`不可进入归档链`。

## 修复任务补建（2026-04-16 22:21 +0800）

- 补建人：`守护最好的爱莉希雅`
- 修复任务：[`T-20260416-8680d55f`](../../TODO.md)
- 任务类型：`build`
- 执行授权：
  - 本段授权仅绑定当前任务号 [`T-20260416-3537457d`](../../TODO.md)，不沿用上一轮 [`T-20260416-8680d55f`](../../DONE.md) 的授权文本，也不自动延伸到后续新任务号。
  - 本任务按 [`agents/standard/expectation任务规则.md`](../../agents/standard/expectation任务规则.md) 做当前任务号的一次性例外授权；若由 `build` 角色承接，明确授权被分发的 `build` 执行人直接修改 [`expectation/utils/compare.py`](../../expectation/utils/compare.py)。
  - 同一任务号内，同时明确授权该 `build` 执行人修改 [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)，用于收口公开合同文本。
  - 精确写集仅限以下两处：
    - [`expectation/utils/compare.py`](../../expectation/utils/compare.py)
    - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
  - 不得扩大到其他 `expectation` 路径、其他 `spec`、任何实现文件、测试文件、`.gitignore`、`agents` 文档或其他 ignored 路径。
- 唯一修复范围：
  - 修复 [`expectation/utils/compare.py`](../../expectation/utils/compare.py) 对已删除 [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py) 的断链依赖，收口到当前唯一有效入口。
  - 修正 [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md) 中仍将 `kernel_gen.dsl.emit_mlir` 写成公开 facade 的陈旧合同，明确 `kernel_gen.dsl.mlir_gen.emit` 为唯一入口。
- 验收命令：
  - `PYTHONDONTWRITEBYTECODE=1 python - <<'PY'`
    `import importlib`
    `importlib.import_module("expectation.utils.compare")`
    `print("OK")`
    `PY`
  - `rg -n "kernel_gen\\.dsl\\.emit_mlir" expectation/utils/compare.py spec/dsl/mlir_gen.md`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_emit_mlir.py test/dsl/test_ast.py test/dsl/test_ast_visitor.py test/dsl/test_mlir_gen.py test/dsl/mlir_gen/emit`
- 续推说明：
  - 已完成的 [`T-20260416-c695f3a2`](../../DONE.md) 不再继续复用；它收口的是此前的功能阻断，不覆盖本轮新定位出的 expectation 断链与 spec 合同残留。
  - 当前不得创建归档任务，也不得执行 `-done-plan`。
  - 待 [`T-20260416-8680d55f`](../../TODO.md) 完成后，再回到本计划按最新同步现场重新终验。

## 当前同步现场终验复核（2026-04-16 23:27 +0800）

- 终验人：`大闸蟹`
- 当前结论：`不通过`
- 归档结论：`不可进入归档链`
- 验证基线：
  - 终验目录：`/home/lfr/kernelcode_generate`
  - 终验时间：`2026-04-16 23:27 +0800`
  - 本轮以当前可访问现场为准；管理员较早同步的“`T-20260416-8680d55f` 已完成、`TODO` 为空、计划为 `8/8/0`”口径，已被当前本地任务表更新覆盖。
  - 当前 [`TODO.md`](../../TODO.md) 实际状态为：[`ARCHITECTURE/plan/dsl_emit_mlir_refactor_green_plan.md`](../../ARCHITECTURE/plan/dsl_emit_mlir_refactor_green_plan.md) 已变为 `9 / 8 / 1 / 进行中`，且新增唯一继续项 [`T-20260416-3537457d`](../../TODO.md)，创建时间为 `2026-04-16 23:26:09 +0800`。
- 当前同步现场实跑：
  - `test -e kernel_gen/dsl/emit_mlir.py && echo EXISTS || echo MISSING` -> `MISSING`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_emit_mlir.py` -> `72 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_ast.py` -> `47 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_ast_visitor.py` -> `203 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_mlir_gen.py` -> `153 passed, 1 warning`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/mlir_gen/emit` -> `30 passed`
  - `rg -n "kernel_gen\\.dsl\\.emit_mlir" kernel_gen test` -> `exit=1` 且无输出
  - `PYTHONDONTWRITEBYTECODE=1 python - <<'PY' ... importlib.import_module("expectation.utils.compare") ... PY` -> `ModuleNotFoundError: No module named 'kernel_gen.dsl.emit_mlir'`
  - `rg -n "kernel_gen\\.dsl\\.emit_mlir" expectation/utils/compare.py spec/dsl/mlir_gen.md` -> 命中：
    - [`expectation/utils/compare.py`](../../expectation/utils/compare.py)
    - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
- 最小阻断项：
  - [`expectation/utils/compare.py`](../../expectation/utils/compare.py) 仍直接依赖已删除的 [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py)，当前 `import expectation.utils.compare` 仍会立即失败。
  - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md) 仍把 `kernel_gen.dsl.emit_mlir` 写成公开 facade，和本计划“以 `kernel_gen.dsl.mlir_gen.emit` 作为唯一入口”的完成态不一致。
- 终验说明：
  - 本计划正文点名的 `pytest` 与 `kernel_gen/test` 范围扫描当前都已恢复通过，但本轮新增的 expectation 断链与 spec 残留仍是当前同步现场中的真实缺口。
  - 因此，本计划截至 `2026-04-16 23:27 +0800` 仍应维持`不通过`，且`不可进入归档链`。
- 唯一继续项：
  - 保留 [`T-20260416-3537457d`](../../TODO.md) 作为当前唯一继续项。
  - 此前管理员同步的 [`T-20260416-8680d55f`](../../TODO.md) 完成口径，不再作为本轮归档判断依据；需待当前唯一继续项收口后，再回到本计划重新终验。

## R6 授权口径同步（2026-04-16 23:28 +0800）

- 记录人：`大闸蟹`
- 适用任务：[`T-20260416-3537457d`](../../TODO.md)
- 当前口径：
  - 本任务写集包含 [`expectation/utils/compare.py`](../../expectation/utils/compare.py)，因此仍属于 expectation 例外授权场景。
  - 上一轮 [`T-20260416-8680d55f`](../../TODO.md) 的一次性 expectation 授权，不自动沿用到当前新任务号 [`T-20260416-3537457d`](../../TODO.md)。
  - 当前任务由 `守护最好的爱莉希雅` 发起，且 expectation 例外授权也由其上一轮补建；因此本轮应继续以 `守护最好的爱莉希雅` 为唯一授权来源，由她对当前任务号补齐一次性授权、精确写集与验收命令。
  - `大闸蟹` 本轮不再为同一任务号另起第二套 expectation 授权口径，避免出现双口径并行。
- 管理续推说明：
  - 在 `守护最好的爱莉希雅` 对 [`T-20260416-3537457d`](../../TODO.md) 写明当前任务号的一次性 expectation 授权前，管理员应继续保持“暂不分发”。
  - 待该授权补齐后，再按当前任务号继续推进，不需要重建平行修复任务。

## 当前同步现场终验（2026-04-16 23:25 +0800）

- 终验人：`守护最好的爱莉希雅`
- 当前结论：`不通过`
- 归档结论：`不可进入归档链`
- 验证基线：
  - 同步现场：`/home/lfr/kernelcode_generate`
  - 验证时间：`2026-04-16 23:25:55 +0800`
  - 管理员已同步 [`T-20260416-8680d55f`](../../DONE.md) 于 `2026-04-16 23:10:10 +0800` merge 并 `-done`，提交号为 `43635c8`。
  - 但当前磁盘现场未找到比根目录更晚且可复核的同步 worktree，也未找到 `20260416-emit-mlir-refactor-r5.md` 记录文件；因此本轮只能以当前根目录现场作为“最新可复核同步现场”执行终验，而不能凭 DONE 口径直接判定通过。
  - [`TODO.md`](../../TODO.md) 当前显示本计划为 `8 / 8 / 0 / 完成待检查`。
- 当前同步现场实跑：
  - `test -e kernel_gen/dsl/emit_mlir.py && echo EXISTS || echo MISSING` -> `MISSING`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_emit_mlir.py test/dsl/test_ast.py test/dsl/test_ast_visitor.py test/dsl/test_mlir_gen.py test/dsl/mlir_gen/emit` -> `505 passed, 1 warning in 1.99s`
  - `rg -n "kernel_gen\\.dsl\\.emit_mlir" kernel_gen test` -> `exit=1` 且无输出
  - `PYTHONDONTWRITEBYTECODE=1 python - <<'PY' ... importlib.import_module("expectation.utils.compare") ... PY` -> `ModuleNotFoundError: No module named 'kernel_gen.dsl.emit_mlir'`
  - `rg -n "kernel_gen\\.dsl\\.emit_mlir" expectation/utils/compare.py spec/dsl/mlir_gen.md` -> 命中：
    - [`expectation/utils/compare.py`](../../expectation/utils/compare.py)
    - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
- 最小阻断项：
  - [`expectation/utils/compare.py`](../../expectation/utils/compare.py) 第 38 行仍直接 `from kernel_gen.dsl.emit_mlir import _memory_to_nn_type`；当前同步现场中 [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py) 已删除，导致 `import expectation.utils.compare` 直接失败。这是本计划点名的 expectation 支撑资产真实断链，不属于“旧主仓未同步”的可忽略差异。
  - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md) 第 46 行仍把 `kernel_gen.dsl.emit_mlir` 写成共享 facade 公开入口，第 64 行仍把已删除的 [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py) 描述为允许保留的 facade/兼容壳层职责。这与本计划“删除旧文件并收口为 `kernel_gen.dsl.mlir_gen.emit` 唯一入口”的公开选型和完成态不一致。
- 终验说明：
  - 按本计划正文列出的主功能验收命令，当前同步现场已经全绿，且 `kernel_gen/test` 范围内对旧 dotted import 的清理完成。
  - 但本计划的完成态不仅要求“测试通过”，还要求 expectation 支撑资产与公开 spec 同步收口到 `kernel_gen.dsl.mlir_gen.emit` 唯一入口。当前这两处残留说明 `T-20260416-8680d55f` 的合入结果尚未在当前可复核同步现场完全体现，因此本计划当前仍`不通过`，且`不可进入归档链`。

## 修复任务补建（2026-04-16 23:25 +0800）

- 补建人：`守护最好的爱莉希雅`
- 修复任务：[`T-20260416-3537457d`](../../TODO.md)
- 任务类型：`build`
- 执行授权：
  - 本任务按 [`agents/standard/expectation任务规则.md`](../../agents/standard/expectation任务规则.md) 做一次性例外授权；允许被分发的 `build` 执行人直接修改 [`expectation/utils/compare.py`](../../expectation/utils/compare.py)。
  - 同一任务内同时允许修改 [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)，用于收口公开合同文本。
  - 精确写集仅限以下两处：
    - [`expectation/utils/compare.py`](../../expectation/utils/compare.py)
    - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
  - 不得扩大到其他 `expectation` 路径、其他 `spec`、任何实现文件、测试文件、`.gitignore`、`agents` 文档或其他 ignored 路径。
- 唯一修复范围：
  - 修复 [`expectation/utils/compare.py`](../../expectation/utils/compare.py) 对已删除 [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py) 的断链依赖，收口到当前唯一有效入口。
  - 修正 [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md) 中仍将 `kernel_gen.dsl.emit_mlir` 写成公开 facade 的陈旧合同，明确 `kernel_gen.dsl.mlir_gen.emit` 为唯一入口。
- 验收命令：
  - `PYTHONDONTWRITEBYTECODE=1 python - <<'PY'`
    `import importlib`
    `importlib.import_module("expectation.utils.compare")`
    `print("OK")`
    `PY`
  - `rg -n "kernel_gen\\.dsl\\.emit_mlir" expectation/utils/compare.py spec/dsl/mlir_gen.md`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_emit_mlir.py test/dsl/test_ast.py test/dsl/test_ast_visitor.py test/dsl/test_mlir_gen.py test/dsl/mlir_gen/emit`
- 续推说明：
  - 已完成的 [`T-20260416-8680d55f`](../../DONE.md) 不再继续复用；它未在当前可复核同步现场中彻底收口 expectation compare helper 与 `mlir_gen` facade 合同残留。
  - 当前管理员可直接按 [`T-20260416-3537457d`](../../TODO.md) 分发；本轮 expectation 例外授权、精确写集与验收命令已在本计划正文与对应任务记录中写明，不需要再补建平行任务。
  - 当前不得补建归档任务，也不得执行 `-done-plan`。
  - 待 [`T-20260416-3537457d`](../../TODO.md) 完成后，再回到本计划按最新同步现场重新终验。

## R6 任务授权确认（2026-04-16 23:31 +0800）

- 记录人：`守护最好的爱莉希雅`
- 适用任务：[`T-20260416-3537457d`](../../TODO.md)
- 当前口径：
  - 当前任务类型虽为 `build`，但任务目标直接包含 [`expectation/utils/compare.py`](../../expectation/utils/compare.py)，因此需要针对当前任务号单独补 expectation 例外授权。
  - 现明确授权：若 [`T-20260416-3537457d`](../../TODO.md) 由 `build` 角色承接，则该任务号下被分发的 `build` 执行人可直接修改 [`expectation/utils/compare.py`](../../expectation/utils/compare.py) 与 [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)。
  - 本授权仅适用于当前任务号 [`T-20260416-3537457d`](../../TODO.md)；上一轮 [`T-20260416-8680d55f`](../../DONE.md) 的授权文本不沿用，后续若再新建任务，也需由架构师重新写明。
  - 精确写集仅限：
    - [`expectation/utils/compare.py`](../../expectation/utils/compare.py)
    - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
  - 不得扩到任何其他 `expectation`、其他 `spec`、任何实现文件、测试文件、`.gitignore`、`agents` 文档或其他 ignored 路径。
- 验收命令：
  - `PYTHONDONTWRITEBYTECODE=1 python - <<'PY'`
    `import importlib`
    `importlib.import_module("expectation.utils.compare")`
    `print("OK")`
    `PY`
  - `rg -n "kernel_gen\\.dsl\\.emit_mlir" expectation/utils/compare.py spec/dsl/mlir_gen.md`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_emit_mlir.py test/dsl/test_ast.py test/dsl/test_ast_visitor.py test/dsl/test_mlir_gen.py test/dsl/mlir_gen/emit`
- 管理续推说明：
  - 神秘人可直接按当前任务号分发，不需要等待额外授权文本。
  - 本轮只推进 [`T-20260416-3537457d`](../../TODO.md)，不改派、不并行补建同范围任务。

## R6 merge 交付口径（2026-04-16 23:33 +0800）

- 记录人：`大闸蟹`
- 适用任务：[`T-20260416-3537457d`](../../TODO.md)
- 当前结论：
  - 允许沿当前任务号继续推进，不停止当前任务，也不改由架构/spec 侧另起平行链。
  - merge 阶段仅允许对 [`expectation/utils/compare.py`](../../expectation/utils/compare.py) 执行 `git add -f` 纳入交付；[`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md) 为 tracked 文件，按普通 staged 处理即可。
- 精确交付边界：
  - 允许纳入交付：
    - [`expectation/utils/compare.py`](../../expectation/utils/compare.py)
    - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
  - merge 阶段对 ignored 路径的唯一例外动作仅限：
    - `git add -f expectation/utils/compare.py`
  - 不得修改 [`.gitignore`](../../.gitignore)。
  - 不得扩大到其他 `expectation` 路径、其他 `spec`、任何实现文件、测试文件、`agents` 文档或其他 ignored 路径。
- 说明：
  - [`expectation/utils/compare.py`](../../expectation/utils/compare.py) 虽为 ignored/untracked，但它是本计划正文已点名的唯一 expectation 修复资产，且当前任务号 [`T-20260416-3537457d`](../../TODO.md) 已写明一次性 expectation build 授权与精确写集。
  - 因此，本轮 review / merge 不应按“普通 expectation 一律拒绝”处理，而应按“单文件例外交付”处理；边界以上述两文件为准。
- 管理续推说明：
  - 神秘人可恢复 [`T-20260416-3537457d`](../../TODO.md) 当前任务号，按既有链路继续推进。
  - 若 review / merge 再发现写集超出上述两文件，或出现任何额外 ignored 路径，则应再次暂停并回报，不得自行放宽范围。

## 当前同步现场终验（2026-04-17 00:48 +0800）

- 终验人：`守护最好的爱莉希雅`
- 当前结论：`通过`
- 归档结论：`可进入归档链`
- 验证基线：
  - 最新可复核同步现场：`/home/lfr/kernelcode_generate/wt-20260417-dsl-emit-mlir-final-check`
  - 同步现场 `HEAD`：`b154eb98fa92a047792663c38b15d9dfff9dc083`
  - 当前根目录仓库的 `origin/main` 远端引用同样指向 `b154eb98fa92a047792663c38b15d9dfff9dc083`；因此该同步现场与管理员回报的 `T-20260416-3537457d` merge 提交一致，可作为本轮终验基线。
  - 根目录 [`/home/lfr/kernelcode_generate`](../../) 当前未同步到上述提交；根目录中旧版 [`expectation/utils/compare.py`](../../expectation/utils/compare.py) 与 [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md) 仅记为现场状态差异，不再单独作为功能阻断。
  - [`TODO.md`](../../TODO.md) 当前显示本计划为 `9 / 9 / 0 / 完成待检查`。
- 当前同步现场实跑：
  - `test -e kernel_gen/dsl/emit_mlir.py && echo EXISTS || echo MISSING` -> `MISSING`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_emit_mlir.py` -> `72 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_ast.py` -> `47 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_ast_visitor.py` -> `203 passed`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_mlir_gen.py` -> `153 passed, 1 warning`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/mlir_gen/emit` -> `31 passed`
  - `rg -n "kernel_gen\\.dsl\\.emit_mlir" kernel_gen test` -> `exit=1` 且无输出
  - `PYTHONDONTWRITEBYTECODE=1 python - <<'PY' ... importlib.import_module("expectation.utils.compare") ... PY` -> `OK`
  - `rg -n "kernel_gen\\.dsl\\.emit_mlir" expectation/utils/compare.py spec/dsl/mlir_gen.md` -> `exit=1` 且无输出
- 终验说明：
  - 本轮按计划正文列出的逐条验收命令，在最新同步现场逐项复核；不再以未同步根目录快照替代最新主线现场。
  - 同步现场中 [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py) 已删除，`kernel_gen/test` 范围与此前补件的 expectation/spec 资产均已收口到 `kernel_gen.dsl.mlir_gen.emit` 唯一入口。
  - 因此，本计划当前已满足完成态与验收设计要求，应改判为`通过`，并且`可进入归档链`。
- 当前状态：
  - [`T-20260416-3537457d`](../../DONE.md) 已完成并停用，不再续接。
  - 本页 `2026-04-16 23:25 +0800`、`23:27 +0800` 的不通过段仅保留为旧现场快照；自本段起，以最新同步现场终验结论作为现行唯一口径。

## 当前同步现场终验复核（2026-04-17 00:33 +0800）

- 终验人：`大闸蟹`
- 当前结论：`通过`
- 归档结论：`可进入归档链`
- 验证基线：
  - 最新可复核同步现场：`/home/lfr/kernelcode_generate/wt-20260417-dsl-emit-mlir-final-check`
  - 同步现场 `HEAD`：`b154eb98fa92a047792663c38b15d9dfff9dc083`
  - `git rev-parse HEAD && git rev-parse origin/main`（workdir=`/home/lfr/kernelcode_generate/wt-20260417-dsl-emit-mlir-final-check`）-> 两者同为 `b154eb98fa92a047792663c38b15d9dfff9dc083`
  - 当前根目录工作区 `/home/lfr/kernelcode_generate` 仍停在较早提交 `52c9d62dcfce1be0b1212facb9e4c57a11173ad1`；该差异仅记为现场状态差异，不再单独作为功能阻断。
  - [`TODO.md`](../../TODO.md) 当前显示本计划为 `9 / 9 / 0 / 完成待检查`。
- 当前同步现场实跑：
  - `rg -n "kernel_gen\\.dsl\\.emit_mlir" kernel_gen test expectation/utils/compare.py spec/dsl/mlir_gen.md` -> `exit=1` 且无输出
  - `PYTHONDONTWRITEBYTECODE=1 python - <<'PY' ... importlib.import_module("expectation.utils.compare") ... PY` -> `OK`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_emit_mlir.py test/dsl/test_ast.py test/dsl/test_ast_visitor.py test/dsl/test_mlir_gen.py test/dsl/mlir_gen/emit` -> `506 passed, 1 warning in 2.19s`
- 终验说明：
  - 本轮复核基线与上一段 `2026-04-17 00:48 +0800` 的同步现场结论一致；我侧已在同一同步现场独立补跑旧入口扫描、`expectation.utils.compare` 导入与计划正文点名的 pytest 组合。
  - 复核结果表明：旧 facade `kernel_gen.dsl.emit_mlir` 已在 `kernel_gen/test` 与本轮补件的 expectation/spec 资产中全部清空，`expectation/utils/compare.py` 与 [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md) 也已收口到 `kernel_gen.dsl.mlir_gen.emit` 唯一入口。
  - 因此，本计划在最新同步现场下满足完成态与验收设计要求；当前现行唯一口径应为`通过`，并且`可进入归档链`。
- 当前状态：
  - [`T-20260416-3537457d`](../../DONE.md) 已完成并停用，不再续接。
  - 管理员可按现行归档规则补建唯一归档任务；本计划当前不再保留新的继续项。

## 归档记录

时间：2026-04-17 00:41 +0800
经办人：李白
任务：T-20260417-a8f3f6bc
任务目标：将 `ARCHITECTURE/plan/dsl_emit_mlir_refactor_green_plan.md` 归档到 `agents/codex-multi-agents/log/task_records/done_plan/2026/16/dsl_emit_mlir_refactor_green_plan.md`，并完成归档 merge 收口。
改动：
- 管理员指定的 `worktree=/home/lfr/kernelcode_generate/wt-20260417-archive-dsl-emit-mlir-refactor-green-plan` 与任务分支 `T-20260417-a8f3f6bc` 原本不存在；已按当前远端主分支 `origin/main@b154eb9` 补建归档 `worktree` 与对应分支。
- 核对发现源计划书 `ARCHITECTURE/plan/dsl_emit_mlir_refactor_green_plan.md` 当前只存在于主仓本地文件系统，既不在 `origin/main` tracked 集合中，也不在当前新建 `worktree` 的 tracked 集合中；目标 `done_plan` 文件在远端主分支中同样不存在。
- 按归档任务口径，将主仓本地源计划书整体迁移到任务 `worktree` 内的目标归档路径 `agents/codex-multi-agents/log/task_records/done_plan/2026/16/dsl_emit_mlir_refactor_green_plan.md`，并在文件尾部追加本次归档记录；本次合并范围限定为该归档文件，不修改 `.gitignore`、`TODO.md`、`DONE.md` 或其他共享文件。
- 按用户要求，主仓本地源计划书 `ARCHITECTURE/plan/dsl_emit_mlir_refactor_green_plan.md` 已同步移除，不在主目录保留副本。
验证：
- `rg -n "T-20260417-a8f3f6bc" /home/lfr/kernelcode_generate/TODO.md` -> 确认任务为 `merge/进行中/指派=李白`
- `git -C /home/lfr/kernelcode_generate worktree add -b T-20260417-a8f3f6bc /home/lfr/kernelcode_generate/wt-20260417-archive-dsl-emit-mlir-refactor-green-plan origin/main` -> 成功创建归档 `worktree`
- `git -C /home/lfr/kernelcode_generate rev-parse --verify origin/main` -> `b154eb98fa92a047792663c38b15d9dfff9dc083`
- `git -C /home/lfr/kernelcode_generate show origin/main:ARCHITECTURE/plan/dsl_emit_mlir_refactor_green_plan.md` -> 报 `fatal: path ... exists on disk, but not in 'origin/main'`，确认远端主分支无源计划书 tracked 版本
- `test -f /home/lfr/kernelcode_generate/ARCHITECTURE/plan/dsl_emit_mlir_refactor_green_plan.md && echo ROOT_PLAN_EXISTS || echo ROOT_PLAN_MISSING` -> 迁移前为 `ROOT_PLAN_EXISTS`
- `test -f /home/lfr/kernelcode_generate/wt-20260417-archive-dsl-emit-mlir-refactor-green-plan/agents/codex-multi-agents/log/task_records/done_plan/2026/16/dsl_emit_mlir_refactor_green_plan.md && echo ARCHIVE_READY && test -e /home/lfr/kernelcode_generate/ARCHITECTURE/plan/dsl_emit_mlir_refactor_green_plan.md || echo ROOT_REMOVED` -> `ARCHIVE_READY`、`ROOT_REMOVED`
结论：归档文件已在指定 `worktree` 内生成并写入归档记录；下一步提交并推送该归档文件，随后执行当前 merge 任务 `-done` 并回报管理员继续 `-done-plan`。
