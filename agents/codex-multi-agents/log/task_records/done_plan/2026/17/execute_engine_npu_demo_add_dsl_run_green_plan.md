# execute_engine_npu_demo_add_dsl_run_green_plan.md

## 文档信息

- 创建者：`榕`
- 最后一次更改：`榕`
- 目标 `spec`：
  - [`spec/tools/dsl_run.md`](../../spec/tools/dsl_run.md)
  - [`spec/pass/pipeline/npu_demo_lowering.md`](../../spec/pass/pipeline/npu_demo_lowering.md)
  - [`spec/execute_engine/execute_engine.md`](../../spec/execute_engine/execute_engine.md)
- 目标 `API`：
  - [`kernel_gen/tools/dsl_run.py`](../../kernel_gen/tools/dsl_run.py)
  - [`kernel_gen/passes/pipeline/npu_demo_lowering.py`](../../kernel_gen/passes/pipeline/npu_demo_lowering.py)
  - [`expectation/execute_engine/npu_demo/add.py`](../../expectation/execute_engine/npu_demo/add.py)
  - [`expectation/execute_engine/npu_demo/sub.py`](../../expectation/execute_engine/npu_demo/sub.py)
  - [`expectation/execute_engine/npu_demo/mul.py`](../../expectation/execute_engine/npu_demo/mul.py)
  - [`expectation/execute_engine/npu_demo/matmul.py`](../../expectation/execute_engine/npu_demo/matmul.py)
  - [`expectation/execute_engine/npu_demo/__main__.py`](../../expectation/execute_engine/npu_demo/__main__.py)
- 目标 `test`：
  - [`test/tools/test_dsl_run.py`](../../test/tools/test_dsl_run.py)
  - [`test/pass/test_pipeline_npu_demo_lowering.py`](../../test/pass/test_pipeline_npu_demo_lowering.py)
  - [`test/execute_engine/test_execute_engine_compile.py`](../../test/execute_engine/test_execute_engine_compile.py)
  - [`test/execute_engine/test_execute_engine_invoke.py`](../../test/execute_engine/test_execute_engine_invoke.py)
- 目标 `验收资产`：
  - [`expectation/execute_engine/npu_demo/add.py`](../../expectation/execute_engine/npu_demo/add.py)
  - [`expectation/execute_engine/npu_demo/sub.py`](../../expectation/execute_engine/npu_demo/sub.py)
  - [`expectation/execute_engine/npu_demo/mul.py`](../../expectation/execute_engine/npu_demo/mul.py)
  - [`expectation/execute_engine/npu_demo/matmul.py`](../../expectation/execute_engine/npu_demo/matmul.py)
  - [`expectation/execute_engine/npu_demo/__main__.py`](../../expectation/execute_engine/npu_demo/__main__.py)
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate python3 expectation/execute_engine/npu_demo/add.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate python3 expectation/execute_engine/npu_demo/sub.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate python3 expectation/execute_engine/npu_demo/mul.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate python3 expectation/execute_engine/npu_demo/matmul.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate python3 -m expectation.execute_engine.npu_demo`
- 目标 `功能实现`：
  - [`kernel_gen/tools/dsl_run.py`](../../kernel_gen/tools/dsl_run.py)
  - [`kernel_gen/passes/pipeline/npu_demo_lowering.py`](../../kernel_gen/passes/pipeline/npu_demo_lowering.py)
  - [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)
  - [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py)
  - [`kernel_gen/execute_engine/execution_engine.py`](../../kernel_gen/execute_engine/execution_engine.py)

## 任务清单

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `S1` | `无` | `待创建` | `待创建` |
| `S2` | `S1` | `待创建` | `待创建` |
| `S3` | `S1` | `待创建` | `待创建` |

## 评审摘要

- 评审结论：`通过`
- 评审人：`守护最好的爱莉希雅 / 大闸蟹`
- 结论摘要：`在 add/sub/mul/matmul 四条 execute_engine expectation 的最新范围下，S1/S2/S3 拆分合理：S1 统一收 add/sub/mul 的 dsl_run 黑盒，S2 单独收静态 tile for-loop add，S3 单独收 matmul 的 TSM / kernel.matmul 合同。公开 API 稳定收口到 dsl_run(..., "npu-demo-lowering", EmitCContext(target="npu_demo"))，default-lowering 不再承担 execute_engine 正向合同；add 的静态 tile for-loop 与 matmul 的 TSM / kernel.matmul 合同都已写成机械可判的完成态与验收项，当前版本可直接推进任务创建。`

## 终验 / 复验 / 修复复核记录

- 结论人：`大闸蟹`
- 结论：`通过`
- 验证基线：`主目录 /home/lfr/kernelcode_generate 已执行 git fetch origin main，git merge --ff-only origin/main 返回 Already up to date；HEAD_REF=refs/heads/main，main=origin/main=b3ea3299456984252ca05a84352cc60e5e8c4328`
- 最小阻断项或通过摘要：`无阻断项。S1/S2/S3 已合入主线；在主目录执行 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate python3 -m expectation.execute_engine.npu_demo 通过；add/sub/mul/matmul 四个单入口均 exit 0；pytest -q test/tools/test_dsl_run.py test/pass/test_pipeline_npu_demo_lowering.py test/execute_engine/test_execute_engine_compile.py test/execute_engine/test_execute_engine_invoke.py 结果为 37 passed。验证覆盖 add slice+store、静态 tile for-loop add、sub、mul、matmul 的 dsl_run + npu-demo-lowering + npu_demo 真实 compile/execute 链。`
- 是否已创建修复任务：`不需要`
- 修复任务创建人：`不适用`
- 另一位架构师补充重点：`守护最好的爱莉希雅复验通过。2026-04-21 20:57:34 +0800 已在主目录 /home/lfr/kernelcode_generate 执行 git fetch origin main，并确认 HEAD=origin/main=37177a55d5fb6f4ac27ceb09864c67847716e9c0；head_is_ancestor=0 且 origin_is_ancestor=0，主目录已处于最新主线，无需额外 fast-forward。执行目录为 /home/lfr/kernelcode_generate，PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. 下复跑 python3 expectation/execute_engine/npu_demo/add.py、sub.py、mul.py、matmul.py 均 exit 0，python3 -m expectation.execute_engine.npu_demo exit 0，pytest -q test/tools/test_dsl_run.py 为 18 passed，pytest -q test/pass/test_pipeline_npu_demo_lowering.py 为 2 passed。无最小阻断项；S1/S2/S3 当前满足归档前置条件。`

## 计划目标

- 把 [`expectation/execute_engine/npu_demo/add.py`](../../expectation/execute_engine/npu_demo/add.py)、[`sub.py`](../../expectation/execute_engine/npu_demo/sub.py)、[`mul.py`](../../expectation/execute_engine/npu_demo/mul.py)、[`matmul.py`](../../expectation/execute_engine/npu_demo/matmul.py) 统一收口到 `dsl_run(..., "npu-demo-lowering", EmitCContext(target="npu_demo"))` 这一条公开执行链。
- 保持 `execute_engine` expectation 仍锁“真实编译 + 真实执行 + 显式 out 参数写回 / 返回值结果”，不能回退成只 lower、只出源码、或 dry-run。
- 以现有 expectation 文件作为合同真源和验收资产；执行阶段默认不要求直接修改这些 expectation 文件，重点收口实现、公开 pipeline、工具行为与 pytest。
- 继续保留 add 的两条正向合同：
  - `slice + store` 局部 add
  - 固定静态 tile 的 `for + slice + store` add
- 同时要求 `sub`、`mul`、`matmul` 也能通过 `dsl_run + npu-demo-lowering` 走通真实 compile/execute。
- 明确把“tile 从运行时参数来”“从 tensor shape 推 loop bound/step”的 add case 排除出本轮范围。

## 当前基线

- 当前公开合同：
  - [`spec/tools/dsl_run.md`](../../spec/tools/dsl_run.md) 已把 `dsl_run(func, real_args, pipeline, emitcconfig)` 收口到 `npu-demo-lowering` 正向工具合同。
  - [`spec/pass/pipeline/npu_demo_lowering.md`](../../spec/pass/pipeline/npu_demo_lowering.md) 已定义 `decompass -> lower-nn -> symbol-loop-hoist` 的最小公开 pipeline。
  - [`spec/execute_engine/execute_engine.md`](../../spec/execute_engine/execute_engine.md) 已定义 `compile -> execute` 两段式真实执行总合同。
- 当前公开 API：
  - `dsl_run(...)`、`build_npu_demo_lowering_pipeline()` 已存在并作为公开入口。
  - `expectation/tools/dsl_run/add.py` 已经是 `dsl_run + npu-demo-lowering + npu_demo` 的正向黑盒样例。
- 当前实现入口：
  - `execute_engine/npu_demo` 目录下的 [`add.py`](../../expectation/execute_engine/npu_demo/add.py) 已被探索性改写为 `dsl_run + npu-demo-lowering` 形态，但本计划不把 expectation 文件本身当成执行阶段必须修改面。
  - [`sub.py`](../../expectation/execute_engine/npu_demo/sub.py)、[`mul.py`](../../expectation/execute_engine/npu_demo/mul.py)、[`matmul.py`](../../expectation/execute_engine/npu_demo/matmul.py) 仍使用手工 `AST -> lowering -> gen_kernel -> compile -> execute` 链。
- 当前测试与验收资产：
  - [`expectation/execute_engine/npu_demo/__main__.py`](../../expectation/execute_engine/npu_demo/__main__.py) 聚合 `add/mul/sub/matmul` 四条 expectation。
  - `test/tools/test_dsl_run.py` 与 `test/pass/test_pipeline_npu_demo_lowering.py` 已收口工具与 pipeline 层，但未直接锁定 `execute_engine/npu_demo` 四条 expectation 的整组迁移目标。
- 当前缺口或失败点：
  - `sub`、`mul`、`matmul` 仍未进入 `dsl_run + npu-demo-lowering` 黑盒路径。
  - `add` 的 `slice + store` 合同可沿当前探索路径收口，但静态 tile `for-loop add` 仍需要单独打通 codegen / compile 路径。
  - `matmul` 当前 expectation 还锁 `TSM` 前端空间合同与 loop-region lowering 细节，迁移时不能丢掉这些机械可判断言。
  - 动态 tile、非整除 tile、从 tensor shape 推 loop bound/step 仍不满足当前 `dsl_run` 与前端 lowering 约束，本轮不能当正向合同。

## 合同真源顺序

- `expectation/execute_engine/npu_demo/add.py + sub.py + mul.py + matmul.py > spec/tools/dsl_run.md + spec/pass/pipeline/npu_demo_lowering.md + spec/execute_engine/execute_engine.md > test/tools/test_dsl_run.py + test/pass/test_pipeline_npu_demo_lowering.py + test/execute_engine/test_execute_engine_compile.py + test/execute_engine/test_execute_engine_invoke.py > 当前实现`

## 方案比较与选型

- 不采用方案：`只把 add expectation 切到 dsl_run，其余 sub/mul/matmul 继续保留手工 parse/lower/gen/compile/execute 链`
- 不采用原因：
  - 会让同一目录下四条 execute_engine expectation 长期分叉成两种公开合同。
  - 无法复用已经收口好的 `dsl_run` 工具入口与 `npu-demo-lowering` 黑盒资产。
  - 后续再补更多 execute_engine case 时，维护成本仍会继续堆在手工链路上。
- 采用方案：`把 execute_engine/npu_demo family 统一切到 dsl_run + npu-demo-lowering，只在 execute_engine 层继续锁真实 compile/execute 结果；将 add 的静态 for-loop codegen 缺口单独拆阶段收口`
- 最小公开接口：
  - `dsl_run(add_slice_store_kernel, (out, lhs, rhs), "npu-demo-lowering", EmitCContext(target="npu_demo"))`
  - `dsl_run(sub_out_wrapper, (out, lhs, rhs), "npu-demo-lowering", EmitCContext(target="npu_demo"))`
  - `dsl_run(mul_out_wrapper, (out, lhs, rhs), "npu-demo-lowering", EmitCContext(target="npu_demo"))`
  - `dsl_run(matmul_out_wrapper, (out, lhs, rhs), "npu-demo-lowering", EmitCContext(target="npu_demo"))`
  - `dsl_run(...)` 本轮不扩展为支持 DSL value-return kernel；返回值语义通过 out-param wrapper / rewrite 后公开行为收口

## 公开 API 设计

- 公开入口：`dsl_run(func_obj, real_args, pipeline, emitcconfig) -> DslRunResult`
- 参数顺序：`func_obj, real_args, pipeline, emitcconfig`
- 参数类型：
  - `func_obj`: DSL 根函数
  - `real_args`: `tuple | list`，元素为 `torch.Tensor | numpy.ndarray`
  - `pipeline`: `str | PassManager`
  - `emitcconfig`: `EmitCContext`
- 返回值：`DslRunResult`

```python
from kernel_gen.dsl.emit_c import EmitCContext
from kernel_gen.tools.dsl_run import dsl_run


result = dsl_run(
    sub_out_wrapper,
    (out, lhs, rhs),
    "npu-demo-lowering",
    EmitCContext(target="npu_demo"),
)
assert result.execute_result.ok is True
```

## 完成态定义

- [`expectation/execute_engine/npu_demo/add.py`](../../expectation/execute_engine/npu_demo/add.py)、[`sub.py`](../../expectation/execute_engine/npu_demo/sub.py)、[`mul.py`](../../expectation/execute_engine/npu_demo/mul.py)、[`matmul.py`](../../expectation/execute_engine/npu_demo/matmul.py) 全部只走 `dsl_run + npu-demo-lowering + npu_demo` 链，不再在 expectation 中手工拼装 parse/lower/gen/compile。
- `add`：
  - `CASE-1` 锁 `slice + store` 局部 add 的真实执行合同。
  - `CASE-2` 锁固定静态 tile 的 `for + slice + store` add，要求 lowered IR 保留 `symbol.for`、源码真实可编译执行。
- `sub / mul`：
  - 锁 `kernel.binary_elewise(kind="sub" | "mul")` 的 lowering 结果、`npu_demo::sub<` / `npu_demo::mul<` 源码片段、out-param wrapper 真实 execute 结果。
- `matmul`：
  - 锁 `TSM` 前端空间在 raw IR 与 rewritten IR 中仍保持 `#nn.space<tsm>`。
  - 锁 loop-region `nn.matmul` 已 lower 为 `kernel.matmul`。
  - 锁 `npu_demo::matmul<` 通过 out-param wrapper 真实编译执行，不能回退为 `cpu::matmul` 或 dry-run。
- 文档正文明确写死：动态 tile 参数、不规则整除、从 tensor shape 推 loop bound/step 不在本轮范围内。

## 验收设计

- 验收资产：
  - [`expectation/execute_engine/npu_demo/add.py`](../../expectation/execute_engine/npu_demo/add.py)
  - [`expectation/execute_engine/npu_demo/sub.py`](../../expectation/execute_engine/npu_demo/sub.py)
  - [`expectation/execute_engine/npu_demo/mul.py`](../../expectation/execute_engine/npu_demo/mul.py)
  - [`expectation/execute_engine/npu_demo/matmul.py`](../../expectation/execute_engine/npu_demo/matmul.py)
  - [`expectation/execute_engine/npu_demo/__main__.py`](../../expectation/execute_engine/npu_demo/__main__.py)
  - `pytest -q test/tools/test_dsl_run.py`
  - `pytest -q test/pass/test_pipeline_npu_demo_lowering.py`
- 锁定输出：
  - `source` 以 `#include "include/npu_demo/npu_demo.h"` 开头
  - `add` 的 `source` 命中 `slice(`、`store(`、`npu_demo::add<`
  - `sub` 的 `source` 命中 `npu_demo::sub<`
  - `mul` 的 `source` 命中 `npu_demo::mul<`
  - `matmul` 的 `source` 命中 `npu_demo::matmul<`
  - `matmul` 的 lowered IR 命中 `kernel.matmul` 且保留 `#nn.space<tsm>`
  - `add CASE-2` 的 lowered IR 命中 `symbol.for`
  - `execute_result.ok is True`
  - 显式 `out` 与预期 `torch` / `numpy` 结果一致
  - `matmul`、`add CASE-2` 均不得回退成只 lower、只出源码、或 dry-run
- 必过命令：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate python3 expectation/execute_engine/npu_demo/add.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate python3 expectation/execute_engine/npu_demo/sub.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate python3 expectation/execute_engine/npu_demo/mul.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate python3 expectation/execute_engine/npu_demo/matmul.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate python3 -m expectation.execute_engine.npu_demo`

## 阶段拆分

### S1：elementwise execute_engine family 切到 dsl_run

#### 阶段目标

- 把 `add/sub/mul` 的 execute_engine expectation 收口为 `dsl_run + npu-demo-lowering + npu_demo` 的真实执行合同。
- `dsl_run` 本轮继续保持“拒绝 DSL value-return kernel”的公开边界；`sub/mul` 通过 out-param wrapper / rewrite 后公开行为收口。

#### 目标 spec / API

- `spec/tools/dsl_run.md`
- `spec/pass/pipeline/npu_demo_lowering.md`
- `spec/execute_engine/execute_engine.md`
- `公开 API：dsl_run(func_obj, real_args, pipeline, emitcconfig) -> DslRunResult`

#### 禁止修改面 / 合同真源

- `禁止修改面：执行阶段默认不要求直接修改 expectation/execute_engine/npu_demo/add.py、sub.py、mul.py；由其作为合同真源与验收资产固定公开行为`
- `合同真源：expectation/execute_engine/npu_demo/add.py + sub.py + mul.py`

#### 预期输出

```text
[SOURCE]
#include "include/npu_demo/npu_demo.h"
...
npu_demo::add<...>(...)
npu_demo::sub<...>(...)
npu_demo::mul<...>(...)

[EXECUTE]
ok=True
```

#### 目标验收资产

- `expectation/execute_engine/npu_demo/add.py`
- `expectation/execute_engine/npu_demo/sub.py`
- `expectation/execute_engine/npu_demo/mul.py`

#### 验收必过项目

- `python3 expectation/execute_engine/npu_demo/add.py`
- `python3 expectation/execute_engine/npu_demo/sub.py`
- `python3 expectation/execute_engine/npu_demo/mul.py`

#### 任务新建建议

- `任务类型：refactor`
- `任务目标：收口实现/spec/pytest，使 execute_engine/npu_demo/add.py、sub.py、mul.py 对齐 dsl_run + npu-demo-lowering + npu_demo 的真实执行合同；dsl_run 不扩到 value-return kernel，sub/mul 通过 out-param wrapper / rewrite 后公开行为收口；不要求本任务直接修改 expectation`
- `记录文件：待创建`

### S2：静态 tile 的 for-loop add 收口

#### 阶段目标

- 新增并打通固定静态 tile 的 `for + slice + store` add 真实执行合同。

#### 目标 spec / API

- `spec/tools/dsl_run.md`
- `spec/pass/pipeline/npu_demo_lowering.md`
- `spec/execute_engine/execute_engine.md`
- `公开 API：dsl_run(func_obj, real_args, pipeline, emitcconfig) -> DslRunResult`

#### 禁止修改面 / 合同真源

- `禁止修改面：不扩展为动态 tile 参数、不支持从 tensor shape 推 loop bound/step`
- `合同真源：expectation/execute_engine/npu_demo/add.py（执行阶段默认不要求直接修改 expectation）`

#### 预期示例代码

```python
def add_for_loop_kernel(
    out: "Tensor[i32, 8]",
    lhs: "Tensor[i32, 8]",
    rhs: "Tensor[i32, 8]",
) -> None:
    for index in loop(0, 8, 2):
        lhs_tile = slice(lhs, [index], [2], [1], MemorySpace.TSM)
        rhs_tile = slice(rhs, [index], [2], [1], MemorySpace.TSM)
        store(lhs_tile + rhs_tile, out, [index], [2], [1])
```

#### 预期输出

```text
[LOWERED]
...
symbol.for
...
dma.slice
dma.store
...

[SOURCE]
#include "include/npu_demo/npu_demo.h"
...
for (
slice(...)
npu_demo::add<...>(...)
store(...)

[EXECUTE]
ok=True
```

#### 目标验收资产

- `expectation/execute_engine/npu_demo/add.py`
- `该阶段锁定：静态 tile for-loop add 的 symbol.for 保留、source 可编译、真实执行结果正确`
- `失败边界：动态 tile 参数、非整除 tile、从 tensor shape 推 loop bound/step、lowering 后丢失 symbol.for、只 lower/只出源码/dry-run 均不算正向合同`

#### 验收必过项目

- `python3 expectation/execute_engine/npu_demo/add.py`

#### 任务新建建议

- `任务类型：refactor`
- `任务目标：打通 execute_engine/npu_demo/add.py 中静态 tile for-loop add 的 codegen/compile/execute 链`
- `记录文件：待创建`

### S3：matmul 切到 dsl_run 并保留 TSM / kernel.matmul 合同

#### 阶段目标

- 把 `execute_engine/npu_demo/matmul.py` 收口为 `dsl_run + npu-demo-lowering + npu_demo` 的真实执行合同，同时保留当前 `TSM` 前端空间和 `kernel.matmul` lowering 合同。
- `dsl_run` 本轮继续保持“拒绝 DSL value-return kernel”的公开边界；`matmul` 通过 out-param wrapper / rewrite 后公开行为收口。

#### 目标 spec / API

- `spec/tools/dsl_run.md`
- `spec/pass/pipeline/npu_demo_lowering.md`
- `spec/execute_engine/execute_engine.md`
- `公开 API：dsl_run(func_obj, real_args, pipeline, emitcconfig) -> DslRunResult`

#### 禁止修改面 / 合同真源

- `禁止修改面：执行阶段默认不要求直接修改 expectation/execute_engine/npu_demo/matmul.py；由其作为合同真源与验收资产固定公开行为`
- `合同真源：expectation/execute_engine/npu_demo/matmul.py`

#### 预期输出

```text
[RAW]
#nn.space<tsm>

[LOWERED]
kernel.matmul
#nn.space<tsm>

[SOURCE]
#include "include/npu_demo/npu_demo.h"
npu_demo::matmul<...>

[EXECUTE]
ok=True
```

#### 目标验收资产

- `expectation/execute_engine/npu_demo/matmul.py`
- `该阶段锁定：TSM 保留、kernel.matmul lowering、真实编译执行、不得回退 cpu::matmul / dry-run`

#### 验收必过项目

- `python3 expectation/execute_engine/npu_demo/matmul.py`

#### 任务新建建议

- `任务类型：refactor`
- `任务目标：收口 execute_engine/npu_demo/matmul.py 到 dsl_run + npu-demo-lowering + npu_demo，并保留 TSM 与 kernel.matmul 合同；dsl_run 不扩到 value-return kernel，matmul 通过 out-param wrapper / rewrite 后公开行为收口；不要求本任务直接修改 expectation`
- `记录文件：待创建`

## 待确认项

- `无`

## 用户确认与协同约束

- `用户确认状态：已确认`
- `未确认事项：无`
- `用户确认结论：`
  - `execute_engine/npu_demo/add` 要改为使用 `dsl_run + npu-demo-lowering`
  - `CASE-1` 为 `slice + store` add
  - `CASE-2` 为 `for + slice + store` add
  - `tile 从参数来` 这条路线本轮不做，先收口静态可整除 tile
  - `计划书不应把 expectation 修改本身当作执行阶段必需目标；expectation 先作为合同真源固定下来`
  - `当前计划不能只覆盖 add，sub/mul/matmul 也要支持`
  - `当前计划不能只覆盖 add，sub/mul/matmul 也要支持`
- `未确认前处理要求：不得自行补假设`
- `已询问角色与结论：`
  - `小李飞刀：最小需改项；指出目录级聚合入口 python3 -m expectation.execute_engine.npu_demo 不应同时挂在 S1 和 S3 的阶段必过项里，应提升为全专题总验收。此项已吸收进最新正文。`
  - `睡觉小分队：通过；确认在 add/sub/mul/matmul 四条 execute_engine expectation 的新范围下，dsl_run / npu-demo-lowering / execute_engine 三层责任边界清楚，动态 tile、非整除 tile、shape 驱动 loop、symbol.for 丢失、cpu::matmul 回退、只 lower/只出源码/dry-run 等失败边界已补到可执行程度。`
  - `守护最好的爱莉希雅：通过；确认在新范围下 S1/S2/S3 拆分仍合理，公开 API 仍稳定收口到 dsl_run(..., "npu-demo-lowering", EmitCContext(target="npu_demo"))，而 add 的静态 tile for-loop 合同与 matmul 的 TSM / kernel.matmul 合同都已写成机械可判的完成态与验收项。`
  - `大闸蟹：通过；确认 S1/S2/S3 的粒度、依赖与 expectation 作为合同真源的边界都已清楚，当前版本可直接推进任务创建。`

## 参考资料

- [`expectation/tools/dsl_run/add.py`](../../expectation/tools/dsl_run/add.py)：当前 `dsl_run + npu-demo-lowering` 正向合同样例。
- [`expectation/execute_engine/npu_demo/add.py`](../../expectation/execute_engine/npu_demo/add.py)：add 合同真源。
- [`expectation/execute_engine/npu_demo/sub.py`](../../expectation/execute_engine/npu_demo/sub.py)：sub 合同真源。
- [`expectation/execute_engine/npu_demo/mul.py`](../../expectation/execute_engine/npu_demo/mul.py)：mul 合同真源。
- [`expectation/execute_engine/npu_demo/matmul.py`](../../expectation/execute_engine/npu_demo/matmul.py)：matmul 合同真源。
- [`spec/tools/dsl_run.md`](../../spec/tools/dsl_run.md)：`dsl_run` 公开接口与工具边界。
- [`spec/pass/pipeline/npu_demo_lowering.md`](../../spec/pass/pipeline/npu_demo_lowering.md)：`npu-demo-lowering` 顺序与 no-op 边界。
