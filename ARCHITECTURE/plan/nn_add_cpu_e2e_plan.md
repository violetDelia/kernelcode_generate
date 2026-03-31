# nn_add_cpu_e2e_plan.md

## 进度
更新日期：2026-04-01
更新规则：每个任务块进入新子阶段后立即更新本段。

| 任务 | 依赖 | 记录文件 | worktree | 当前进度 |
| --- | --- | --- | --- | --- |
| A1 | 无 |  |  |  |
| A2 | A1 |  |  |  |
| A3 | A2 |  |  |  |
| A4 | 无 |  |  |  |
| A5 | A3、A4 |  |  |  |
| A6 | A5 |  |  |  |

## 功能说明

- 本计划基于当前仓库实现重新拟定，用来收敛 `nn.add` 的真实剩余工作，而不是继续把 mixed add 的前半链路当成“尚未落地”的规划项。
- `## 进度` 段仅保留管理员后续填写入口；从本节开始的“当前实现复核”和“本轮收口顺序”才是本轮管理员分发的依据。
- 当前实际状态是：`dialect -> emit_mlir -> mlir_gen -> include/cpu` 已经显著前进，但 `emit_c/gen_kernel` 仍未接住 `nn.add` memory 结果，expectation 也还没有切到最终成功口径。

## 使用示例

- 管理员先阅读“当前实现复核”，再按“本轮收口顺序”放行。
- 若执行者回报以下命令均通过，说明 mixed add 前半链路已经成形，不应再把注意力放回方言或 AST 层：

```bash
pytest -q test/dialect/test_nn_dialect.py -k 'test_add_op_accepts_memory_const_rhs or test_add_op_accepts_memory_symbol_rhs'
pytest -q test/dsl/test_emit_mlir.py -k 'mixed_const_add or mixed_symbol_add'
pytest -q test/dsl/test_mlir_gen.py -k 'memory_symbol_add or memory_const_add'
```

- 若执行者回报 `PYTHONPATH=. python expectation/dsl/emit_c/cpu/add.py` 仍失败，则当前主断点仍在代码生成与 expectation 对齐，而不是 mixed add lowering 本身。

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`大闸蟹`
- `文档`：[`ARCHITECTURE/plan/nn_add_cpu_e2e_plan.md`](../../ARCHITECTURE/plan/nn_add_cpu_e2e_plan.md)
- `spec`：
  - [`spec/dialect/nn.md`](../../spec/dialect/nn.md)
  - [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
  - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
  - [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
  - [`spec/include/cpu/cpu.md`](../../spec/include/cpu/cpu.md)
- `功能实现`：
  - [`kernel_gen/dialect/nn.py`](../../kernel_gen/dialect/nn.py)
  - [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py)
  - [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py)
  - [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py)
  - [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)
  - [`include/cpu/Nn.h`](../../include/cpu/Nn.h)
- `test`：
  - [`test/dialect/test_nn_dialect.py`](../../test/dialect/test_nn_dialect.py)
  - [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py)
  - [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py)
  - [`test/dsl/test_emit_c.py`](../../test/dsl/test_emit_c.py)
  - [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)
  - [`test/include/cpu/test_nn.py`](../../test/include/cpu/test_nn.py)
  - [`expectation/dsl/emit_c/cpu/add.py`](../../expectation/dsl/emit_c/cpu/add.py)

## 当前实现复核

### 已落地

- [`kernel_gen/dialect/nn.py`](../../kernel_gen/dialect/nn.py) 已支持 `nn.memory + const`、`nn.memory + !symbol.int` 的 `NnAddOp` verifier；实测命令：

```bash
pytest -q test/dialect/test_nn_dialect.py -k 'test_add_op_accepts_memory_const_rhs or test_add_op_accepts_memory_symbol_rhs'
```

结果为 `4 passed`（同批命中含 `img2col` 相关 case）。

- [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py) 已能把 mixed `add` lowering 为 `nn.add`；实测命令：

```bash
pytest -q test/dsl/test_emit_mlir.py -k 'mixed_const_add or mixed_symbol_add'
```

结果通过。

- [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py) 已能沿现有公开入口串起 mixed add；实测命令：

```bash
pytest -q test/dsl/test_mlir_gen.py -k 'memory_symbol_add or memory_const_add'
```

结果通过。

- [`include/cpu/Nn.h`](../../include/cpu/Nn.h) 与 [`spec/include/cpu/cpu.md`](../../spec/include/cpu/cpu.md) 已经包含 `cpu::add(lhs, rhs, out)`、`cpu::add(lhs, rhs_scalar, out)`、`cpu::add(lhs_scalar, rhs, out)` 三种公开入口。

### 当前断点

1. [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py) 当前只支持 `arith.*`、`symbol.add`、`scf.for`、`dma.load/store` 等最小子集，不支持 `nn.add`。因此 mixed add 虽然能生成 `func.func`，却仍无法落到 CPU C/C++ 文本。

2. [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py) 对 memory 返回的当前行为仍是 `out = value;`，而不是把 direct-return 的 `nn.add.result` 收敛成 `cpu::add(..., out);`。

3. [`expectation/dsl/emit_c/cpu/add.py`](../../expectation/dsl/emit_c/cpu/add.py) 仍在描述与当前 lowering 不一致的口径。实测命令：

```bash
PYTHONPATH=. python expectation/dsl/emit_c/cpu/add.py
```

当前现象是：
  - `CASE-1` 标量链路通过；
  - `CASE-2` 仍把 `memory + memory` 定义成 emit_c 失败；
  - `CASE-3/CASE-4` 仍断言 mixed add 应该在 `build_func_op` 阶段失败，但当前实现实际上已经能通过 lowering，因此 expectation 自身已经过时。

### 计划基线

- mixed add 已经进入方言、emit_mlir、mlir_gen 与 CPU runtime。
- 当前主断点位于 `emit_c/gen_kernel` 与 expectation 口径对齐。

## 本轮计划目标

- 把 direct-return 的 `nn.add` memory 结果真正收敛到 `cpu::add(..., out);`。
- 让 `emit_c/gen_kernel` 覆盖 `memory + memory`、`memory + const`、`memory + symbol` 三条成功路径。
- 在代码生成链可用后，把 [`expectation/dsl/emit_c/cpu/add.py`](../../expectation/dsl/emit_c/cpu/add.py) 改写为目标成功路径。

## 本轮非目标

- 不再回到方言、AST 或 mixed add lowering 入口重开规格任务。
- 不扩展 `sub/mul/truediv` 的 mixed memory-scalar 路径。
- 不新增任何虚拟 DSL 公开入口名。
- 不把 `gen_kernel` 偷扩成通用 memory SSA 物化框架。

## 管理员执行口径

- 前半链路已基本落地，当前分发重点必须后移到 [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py)、[`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py) 与 [`expectation/dsl/emit_c/cpu/add.py`](../../expectation/dsl/emit_c/cpu/add.py)。
- 在 `emit_c/gen_kernel` 尚未支持 `nn.add` 前，不得把 expectation 失败归因于 mixed add lowering。
- expectation 只能在代码生成链跑通后改写；不得继续把“当前代码还没支持”写回 expectation 作为长期目标。

## 本轮收口顺序

1. 在 [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py) 增加 `nn.add` 到 `cpu::add` 的节点级文本映射，至少覆盖 direct-return 场景需要的 operand 组合。
2. 在 [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py) 把 direct-return 的 `nn.add.result` 收敛为 `cpu::add(..., out);`，而不是 `out = value;`。
3. 在代码生成链通过后，重写 [`expectation/dsl/emit_c/cpu/add.py`](../../expectation/dsl/emit_c/cpu/add.py)，把 `memory + memory`、`memory + const`、`memory + symbol` 三条路径统一切换为成功口径。

## 本轮验收口径

- mixed add 前半链路继续保持通过：

```bash
pytest -q test/dialect/test_nn_dialect.py -k 'test_add_op_accepts_memory_const_rhs or test_add_op_accepts_memory_symbol_rhs'
pytest -q test/dsl/test_emit_mlir.py -k 'mixed_const_add or mixed_symbol_add'
pytest -q test/dsl/test_mlir_gen.py -k 'memory_symbol_add or memory_const_add'
```

预期：全部退出码为 `0`。

- 代码生成链新增直连覆盖：
  - [`test/dsl/test_emit_c.py`](../../test/dsl/test_emit_c.py) 必须新增 `nn.add` 正向生成用例。
  - [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py) 必须新增 direct-return `nn.add -> cpu::add(..., out)` 用例。
  - 生成源码必须可机械命中 `cpu::add(lhs, rhs, out);`、`cpu::add(lhs, 1, out);`、`cpu::add(lhs, rhs, out);` 与 `long long rhs`。

- expectation 切换完成：

```bash
PYTHONPATH=. python expectation/dsl/emit_c/cpu/add.py
```

预期：脚本退出码为 `0`，且不再出现“memory + const / memory + symbol 应在 build_func_op 阶段失败”的断言。

## 当前最直接的下一步

- 先在 [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py) 为 `nn.add` 补节点级映射；这是当前 `nn_add` 端到端链路里最靠前、最确定的硬断点。
