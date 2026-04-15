# execute_engine_npu_demo_matmul_green_plan.md

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`大闸蟹`
- 目标 `spec`：
  - [`spec/execute_engine/execute_engine.md`](../../spec/execute_engine/execute_engine.md)
  - [`spec/execute_engine/execute_engine_api.md`](../../spec/execute_engine/execute_engine_api.md)
  - [`spec/execute_engine/execute_engine_target.md`](../../spec/execute_engine/execute_engine_target.md)
  - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
  - [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
  - [`spec/pass/lowering/nn_lowering.md`](../../spec/pass/lowering/nn_lowering.md)
  - [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md)
  - [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
  - [`spec/include/api/Nn.md`](../../spec/include/api/Nn.md)
- 目标 `API`：
  - [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py)
  - [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py)
  - [`kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
  - [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py)
  - [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)
  - [`kernel_gen/execute_engine/compiler.py`](../../kernel_gen/execute_engine/compiler.py)
  - [`kernel_gen/execute_engine/execution_engine.py`](../../kernel_gen/execute_engine/execution_engine.py)
  - [`include/npu_demo/Nn.h`](../../include/npu_demo/Nn.h)
- 目标 `test`：
  - [`test/pass/nn_lowering/matmul.py`](../../test/pass/nn_lowering/matmul.py)
  - [`test/dsl/test_emit_c.py`](../../test/dsl/test_emit_c.py)
  - [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)
  - [`test/execute_engine/test_execute_engine_compile.py`](../../test/execute_engine/test_execute_engine_compile.py)
  - [`test/execute_engine/test_execute_engine_invoke.py`](../../test/execute_engine/test_execute_engine_invoke.py)
- 目标 `验收资产`：
  - [`expectation/execute_engine/npu_demo/matmul.py`](../../expectation/execute_engine/npu_demo/matmul.py)
- 目标 `功能实现`：
  - [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py)
  - [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py)
  - [`kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`](../../kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
  - [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py)
  - [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)
  - [`kernel_gen/execute_engine/compiler.py`](../../kernel_gen/execute_engine/compiler.py)
  - [`kernel_gen/execute_engine/execution_engine.py`](../../kernel_gen/execute_engine/execution_engine.py)
  - [`include/npu_demo/Nn.h`](../../include/npu_demo/Nn.h)

## 任务清单

> 本轮只补计划书与 expectation 合同，不建任务。待用户检查通过、且完成互评后，再按下表创建并推进。

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `S1` | `无` | `wt-20260414-execute-engine-matmul-s1` | `20260414-execute-engine-matmul-s1.md` |
| `S2` | `S1` | `wt-20260414-execute-engine-matmul-s2` | `20260414-execute-engine-matmul-s2.md` |
| `S3` | `S2` | `wt-20260414-execute-engine-matmul-s3` | `20260414-execute-engine-matmul-s3.md` |
| `S4` | `S3` | `wt-20260414-execute-engine-matmul-s4` | `20260414-execute-engine-matmul-s4.md` |
| `S5` | `S4` | `wt-20260414-execute-engine-matmul-s5` | `20260414-execute-engine-matmul-s5.md` |
| `S6` | `S5` | `wt-20260414-execute-engine-matmul-s6` | `20260414-execute-engine-matmul-s6.md` |
| `S7` | `S6` | `wt-20260414-execute-engine-matmul-s7` | `20260414-execute-engine-matmul-s7.md` |

## 评审摘要

- 评审结论：`通过`
- 评审人：`大闸蟹`、`守护最好的爱莉希雅`
- 结论摘要：`本轮互评确认：计划已明确写清 TSM 空间保真、loop 内 nn.matmul lowering、npu_demo emit_c/gen_kernel 最小 op 子集、execute_engine 真执行四段边界；expectation/execute_engine/npu_demo/matmul.py 的 3 个 case 也已分别锁定前端 TSM、lowering 与 emit_c/编译执行口径；阶段拆分与 ignored expectation 的 git add -f 交付口径可直接建任务。`

## 互评结论（2026-04-14 21:31 +0800）

- 互评人：`守护最好的爱莉希雅`
- 互评结论：`通过`
- 互评要点：
  - 四段边界已经写清，不再是“只缺 matmul emit_c”这种过窄口径：计划在 `计划目标`、`当前基线`、`方案比较与选型`、`完成态定义` 与 `S2/S3/S4/S5` 中都明确分开了 `MemorySpace.TSM -> #nn.space<tsm>` 的前端空间保真、loop region 内 `nn.matmul -> kernel.matmul` 的 lowering、`target=npu_demo` 的 emit_c/gen_kernel 最小 op 子集，以及 execute_engine 的真实编译执行四段职责。
  - [`expectation/execute_engine/npu_demo/matmul.py`](../../expectation/execute_engine/npu_demo/matmul.py) 的 `CASE-1/2/3` 分工足够稳定：`CASE-1` 锁 raw IR 的 `TSM -> #nn.space<tsm>`；`CASE-2` 锁 lowering 后 `kernel.matmul` 与 `nn.matmul` 清空；`CASE-3` 锁生成源码、`npu_demo::matmul(...)`、真实 compile/execute 与数值结果。三条合起来已覆盖本轮需要冻结的前端、lowering 和 emit_c/执行口径。
  - 阶段拆分可直接推进：`S1` 收合同与 expectation，`S2/S3/S4/S5` 分别对应前端 / lowering / emit_c-gen_kernel / execute_engine-helper，`S6` 统一 review，`S7` 收最终交付；ignored expectation 的 `git add -f expectation/execute_engine/npu_demo/matmul.py` 与“不改 .gitignore”也已在总述、完成态定义、`S1` 和 `S7` 写成唯一交付口径，可直接按当前计划建任务。

## 终验结论（2026-04-15 09:23 +0800）

- 终验人：`守护最好的爱莉希雅`
- 终验结论：`不通过`
- 最小阻断项：
  - [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py) 仍在 `_make_npu_demo_add_barrier_module(...)` 中构造旧 `space="tlm"`（当前主仓见第 228 行）；而 [`kernel_gen/dialect/nn.py`](../../kernel_gen/dialect/nn.py) 已把公开 `nn space` 合同收口为 `global/shared/local/tsm/tlm1/tlm2/tlm3`，导致计划书要求的总体验收命令 `pytest -q test/pass/nn_lowering/matmul.py test/dsl/test_emit_c.py test/dsl/test_gen_kernel.py test/execute_engine/test_execute_engine_compile.py test/execute_engine/test_execute_engine_invoke.py` 在 `test/dsl/test_gen_kernel.py` 收集阶段即失败，当前主仓尚不满足本计划完成态。
- 终验记录：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/execute_engine/npu_demo/matmul.py`：通过。`CASE-1/CASE-2/CASE-3` 全部通过，真实编译执行成功，输出与 `torch.matmul(lhs, rhs)` 一致。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/nn_lowering/matmul.py test/dsl/test_emit_c.py test/dsl/test_gen_kernel.py test/execute_engine/test_execute_engine_compile.py test/execute_engine/test_execute_engine_invoke.py`：不通过；失败点固定为 `test/dsl/test_gen_kernel.py` 在 collection 阶段构造 `space="tlm"` 时触发 `VerifyException: nn space must be one of global/shared/local/tsm/tlm1/tlm2/tlm3`。
- 唯一收口口径：
  - `T-20260414-afcd18ce` 已实际承接并推进了本链当前实现与合并结果；`T-20260414-e259dc60`、`T-20260414-f18f36b7`、`T-20260414-218e8ddc` 未形成独立有效推进链，现应视为重复占位任务，停止继续分发。
  - 本轮终验不通过后，后续仅保留一条修复链，目标直接收口上述最小阻断项；在修复完成并重新跑通计划书总体验收前，不进入归档。

## 继续终验结论（2026-04-15 12:41 +0800）

- 终验人：`守护最好的爱莉希雅`
- 终验结论：`不通过`
- 最小阻断项：
  - 当前主仓仍未包含 `T-20260415-f564cb3a` 在 `wt-20260415-execute-engine-matmul-final-fix` 中已验证通过的 `emit_c/gen_kernel` 修复，导致“执行侧回报已通过”与“当前主仓终验仍失败”并存。该阻断现在已经不是计划合同不清，而是“已验证差异尚未进入主仓”：
    - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_emit_c.py` 当前主仓仍为 `4 failed`；其中两个用例还在构造旧 `space="tlm"`，另外两个 add lowering 用例仍按旧 `KernelAddOp` 形态断言。
    - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_gen_kernel.py` 当前主仓仍在 collection 阶段因 `_make_npu_demo_add_barrier_module(...)` 使用旧 `space="tlm"` 而失败。
    - 与已在 `wt-20260415-execute-engine-matmul-final-fix` 中跑通的版本对照，当前主仓仍缺少以下文件中的对应修复：`kernel_gen/dsl/emit_c.py`、`kernel_gen/dsl/gen_kernel.py`、`test/dsl/test_emit_c.py`、`test/dsl/test_gen_kernel.py`。
- 终验记录：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/execute_engine/npu_demo/matmul.py`：通过。`CASE-1/CASE-2/CASE-3` 全部通过，说明 expectation 合同本身已成立。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_emit_c.py`：不通过，当前主仓结果为 `4 failed, 16 passed`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_gen_kernel.py`：不通过，当前主仓在 collection 阶段即因旧 `tlm` 文本失败。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/nn_lowering/matmul.py test/dsl/test_emit_c.py test/dsl/test_gen_kernel.py test/execute_engine/test_execute_engine_compile.py test/execute_engine/test_execute_engine_invoke.py`：不通过，失败点仍固定在 `test/dsl/test_gen_kernel.py` collection。
- 唯一收口口径：
  - 当前计划继续判定为 `不通过`；后续只保留一条修复/合并链，把 `wt-20260415-execute-engine-matmul-final-fix` 中已验证通过的 `emit_c/gen_kernel` 与对应测试改动合法合入主仓后，再按当前主仓重跑上述三条终验命令。

## 终验复核结论（2026-04-15 13:31 +0800）

- 终验人：`守护最好的爱莉希雅`
- 终验结论：`通过`
- 终验记录：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/execute_engine/npu_demo/matmul.py`：通过。`CASE-1/CASE-2/CASE-3` 全部通过，真实 compile/execute 成功，输出与 `torch.matmul(lhs, rhs)` 一致。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_emit_c.py`：通过，`20 passed`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_gen_kernel.py`：通过，`55 passed`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/nn_lowering/matmul.py test/dsl/test_emit_c.py test/dsl/test_gen_kernel.py test/execute_engine/test_execute_engine_compile.py test/execute_engine/test_execute_engine_invoke.py`：通过，`94 passed`。
- 结论摘要：
  - `T-20260415-f998eb18` 已把此前卡在主仓之外的 `emit_c/gen_kernel` 与对应测试修复合入主线；当前主仓已不再残留旧 `space="tlm"` 口径，`execute_engine_npu_demo_matmul` 计划书要求的 expectation 与总体验收命令均已跑通。

## 终验复核结论（2026-04-15 13:44 +0800）

- 终验人：`大闸蟹`
- 终验结论：`通过`
- 终验记录：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/execute_engine/npu_demo/matmul.py`：通过。`CASE-1/CASE-2/CASE-3` 全部通过，raw IR 保持 `#nn.space<tsm>`，rewrite 后 `kernel.matmul` 生效，真实 compile/execute 输出与 `torch.matmul(lhs, rhs)` 一致。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_emit_c.py`：通过，`20 passed`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_gen_kernel.py`：通过，`55 passed`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/nn_lowering/matmul.py test/dsl/test_emit_c.py test/dsl/test_gen_kernel.py test/execute_engine/test_execute_engine_compile.py test/execute_engine/test_execute_engine_invoke.py`：通过，`94 passed`。
- 结论摘要：
  - 当前主仓已满足本计划书完成态与验收设计。按现行归档规则，本计划可进入“先建唯一归档任务，再执行归档链路”的下一步；不需要再补修复任务。

## 计划目标

- 让 [`expectation/execute_engine/npu_demo/matmul.py`](../../expectation/execute_engine/npu_demo/matmul.py) 成为唯一 smoke 合同：固定 shape 的 tiled matmul 必须走完 `DSL -> nn lowering -> emit_c/gen_kernel(target=npu_demo) -> compile -> execute` 全链。
- 明确 `npu_demo` 方向本轮只做后端专用能力，不把 `matmul` 反向扩展进 [`spec/include/api/Nn.md`](../../spec/include/api/Nn.md) 这一逐元素统一 API。
- 收口前端 `MemorySpace.TSM -> IR #nn.space<tsm>` 的空间保真、loop-region 内 `nn.matmul` 的 lowering、`target=npu_demo` 的 emit_c/gen_kernel 实际命中 op 子集、以及 execute_engine 真实编译执行四段职责边界，取消任何“回退到 cpu”或“只生成源码不执行”的兼容口径。
- 预先补齐 expectation 资产，避免执行者后续只看文字计划、不知道源码与数值结果应当长什么样。

## 当前基线

- 当前 [`matmul.plan.md`](../../matmul.plan.md) 说明了 tiled matmul 的目标内核与 CPU 向缺口，但没有形成可直接推进的正式计划书，也没有位于 `expectation/execute_engine` 的验收资产。
- 当前 [`expectation/execute_engine`](../../expectation/execute_engine) 只有 [`add.py`](../../expectation/execute_engine/add.py)；仓库里还没有 `npu_demo` matmul 的 compile + execute 合同。
- 当前 [`spec/pass/lowering/nn_lowering.md`](../../spec/pass/lowering/nn_lowering.md) 已要求“输出 module 不应再包含 `nn` op”，但现有 [`test/pass/nn_lowering/matmul.py`](../../test/pass/nn_lowering/matmul.py) 只覆盖平铺 `nn.matmul -> kernel.matmul`，没有覆盖 tiled loop region 中的 `nn.matmul`。
- 当前前端链对 [`expectation/execute_engine/npu_demo/matmul.py`](../../expectation/execute_engine/npu_demo/matmul.py) 的 raw IR 试跑结果显示：前端显式写成 `MemorySpace.TSM` 的 tile memory，进入 IR 后被物化成 `#nn.space<shared>`，没有保持成 `#nn.space<tsm>`；这与本轮用户口径不一致，必须单独收口。
- 当前 [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py) 在 `target=npu_demo` 下不只是缺 `kernel.matmul`；从当前 expectation 试跑看，实际先撞到的是 `symbol.const` 不支持，说明 tiled matmul 链真实命中的 `symbol.const / symbol.for / dma.alloc / dma.slice / dma.deslice / kernel.matmul` 等 op family 还没有完整打通。
- 当前 [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py) 的 `target=npu_demo` 子集仍集中在 add/memory-pipeline 与 launch-wrapper 受控形态，尚未覆盖 “tile loop + slice + matmul + deslice” 的 body。
- 按当前新补的 [`expectation/execute_engine/npu_demo/matmul.py`](../../expectation/execute_engine/npu_demo/matmul.py) 试跑，当前三条真实缺口分别是：
  - raw IR 里 `MemorySpace.TSM -> #nn.space<shared>`，没有保持为 `#nn.space<tsm>`；
  - lowering 后 loop region 内仍残留 `nn.matmul`；
  - 继续进入 `emit_c` 时首个失败点为 `EmitCError: target=npu_demo: symbol.const: unsupported op`。
- 当前 [`include/npu_demo/Nn.h`](../../include/npu_demo/Nn.h) 只有逐元素与比较类 helper，没有 `matmul`；而 [`spec/include/api/Nn.md`](../../spec/include/api/Nn.md) 明确说明统一 API 不包含 `matmul` 等非逐元素算子。
- 当前仓库 `.gitignore` 含 `/expectation/`；新增 [`expectation/execute_engine/npu_demo/matmul.py`](../../expectation/execute_engine/npu_demo/matmul.py) 后，后续 merge 阶段必须显式 `git add -f`，且不得修改 `.gitignore`。

## 方案比较与选型

- 不采用方案：沿用 CPU 目标，把 execute_engine matmul expectation 写到 `target=cpu`。
  - 原因：用户已明确要求 expectation 放在 [`expectation/execute_engine`](../../expectation/execute_engine) 且 target 为 `npu_demo`；改成 CPU 会偏离本轮目标。
- 不采用方案：只补 “生成源码成功” 的 expectation，不要求真实 compile + execute。
  - 原因：[`expectation/execute_engine/add.py`](../../expectation/execute_engine/add.py) 的现有口径已经是“真实编译 + 真实执行 + 真实输出”；matmul 若退回到只看源码，执行者仍需猜测后端 helper 与运行结果。
- 不采用方案：把本轮问题继续描述成“只缺 matmul helper / 只缺 kernel.matmul emit_c”。
  - 原因：当前 expectation 试跑已经证明更前面的 `TSM` 空间保真、loop lowering、`symbol.const` 发码都在挡路；若计划只写 matmul helper，执行链会直接走偏。
- 不采用方案：把 `matmul` 扩进 [`spec/include/api/Nn.md`](../../spec/include/api/Nn.md) 并要求所有后端统一暴露。
  - 原因：这会扩大统一 API 的职责范围，与当前“统一 API 只覆盖逐元素与显式 broadcast”相冲突；本轮只需要 `npu_demo` 后端专用 leaf helper。
- 采用方案：
  - 以 [`expectation/execute_engine/npu_demo/matmul.py`](../../expectation/execute_engine/npu_demo/matmul.py) 作为唯一验收资产，先把固定 shape 的 tiled matmul smoke 合同写清。
  - 前端 / MLIR gen 先收口 `MemorySpace.TSM -> #nn.space<tsm>` 的空间保真，禁止退化为 `#nn.space<shared>`。
  - `NnLoweringPass` 需要能把 loop region 内的 `nn.matmul` 收口为 `kernel.matmul`，且输出不再残留 `nn.matmul`。
  - `emit_c/gen_kernel(target="npu_demo")` 需要按 tiled matmul 实际命中的 op family 收口，至少覆盖 `symbol.const / symbol.for / dma.alloc / dma.slice / dma.deslice / kernel.matmul`，不保留 `cpu::matmul` 或“只支持 add 子集”的兼容旁路。
  - `include/npu_demo/Nn.h` 补后端专用 `matmul` helper，供 `npu_demo::matmul(...)` 目标源码真实编译和真实执行；不修改 [`spec/include/api/Nn.md`](../../spec/include/api/Nn.md) 的公开边界。
  - expectation 资产继续放在 ignored 的 [`expectation/execute_engine/npu_demo`](../../expectation/execute_engine/npu_demo) 路径，merge 阶段使用 `git add -f expectation/execute_engine/npu_demo/matmul.py` 纳入交付。

## 公开 API 设计

- 公开入口：
  - `NnLoweringPass.run(module)`
  - `gen_kernel(func_op, EmitCContext(target="npu_demo"))`
  - `ExecutionEngine.compile(request).execute(args=(out, lhs, rhs))`
- 参数顺序：
  - DSL 合同：`matmul_kernel(lhs, rhs) -> out`
  - rewrite 后执行 ABI：`(out, lhs, rhs)`
  - compile 请求：`source, target, function, entry_point`
- 参数类型：`lhs`: `Tensor[f32, 32, 16]`
- 参数类型：`rhs`: `Tensor[f32, 16, 32]`
- 参数类型：`out`: `Tensor[f32, 32, 32]`
- 参数类型：`target`: 固定 `"npu_demo"`
- 参数类型：`tile memory space`: 固定 `TSM -> IR #nn.space<tsm>`
- 返回值：
  - `gen_kernel(...) -> str`
  - `CompiledKernel.execute(...) -> ExecuteResult`

```python
def matmul_kernel(lhs: "Tensor[f32, 32, 16]", rhs: "Tensor[f32, 16, 32]") -> "Tensor[f32, 32, 32]":
    out = alloc([32, 32], NumericType.Float32, MemorySpace.GM)
    for m0 in loop(0, 32, 16):
        for n0 in loop(0, 32, 16):
            lhs_tile = slice(lhs, [m0, 0], [16, 16], [1, 1], MemorySpace.TSM)
            rhs_tile = slice(rhs, [0, n0], [16, 16], [1, 1], MemorySpace.TSM)
            partial = matmul(lhs_tile, rhs_tile)
            deslice(partial, out, [m0, n0], [16, 16], [1, 1])
    return out
```

## 完成态定义

- [`expectation/execute_engine/npu_demo/matmul.py`](../../expectation/execute_engine/npu_demo/matmul.py) 可独立运行，并把固定 shape tiled matmul 的源码与数值结果作为唯一验收口径。
- raw IR 中，前端显式 `MemorySpace.TSM` 的 tile memory 必须保持为 `#nn.space<tsm>`；不得出现 `#nn.space<shared>` 作为本轮 tile memory 的 IR 口径。
- `NnLoweringPass` 处理上述 tiled kernel 后，loop region 内为 `kernel.matmul`，输出 IR 中不再残留 `nn.matmul`。
- `gen_kernel(target="npu_demo")` 对该 rewrite 后 IR 生成的源码：
  - 以 `#include "include/npu_demo/npu_demo.h"` 开头；
  - 包含 `npu_demo::matmul(`；
  - 不包含 `cpu::matmul(`。
- [`include/npu_demo/Nn.h`](../../include/npu_demo/Nn.h) 已补 matmul leaf helper，且它只作为 `npu_demo` 后端实现存在，不改写 [`spec/include/api/Nn.md`](../../spec/include/api/Nn.md) 的逐元素统一边界。
- `ExecutionEngine(target="npu_demo")` 对该源码执行真实编译和真实运行，`kernel.compile_stdout` 不再是 `dry-run:`，输出张量与 `torch.matmul(lhs, rhs)` 数值一致。
- merge 阶段已按 `git add -f expectation/execute_engine/npu_demo/matmul.py` 纳入 expectation 资产，且 `.gitignore` 不变。

## 验收设计

- 验收资产：
  - [`expectation/execute_engine/npu_demo/matmul.py`](../../expectation/execute_engine/npu_demo/matmul.py)
- 输入样例：
  - `lhs`: `torch.float32`，shape=`(32, 16)`
  - `rhs`: `numpy.float32`，shape=`(16, 32)`
  - tile 口径：`M=32, K=16, N=32, TILE_M=16, TILE_N=16`
- 锁定输出：
  - raw IR 含 `#nn.space<tsm>`，且不含把本轮 tile memory 写成 `#nn.space<shared>` 的退化结果
  - rewrite 后 IR 含 `kernel.matmul`，不含 `nn.matmul`
  - 生成源码包含 `npu_demo::matmul(`、`slice(`、`deslice(`，且不出现 `cpu::matmul(`
  - 运行输出 shape=`(32, 32)`，数值与 `torch.matmul(lhs, rhs)` 一致
- 必过命令：
  - `PYTHONPATH=. python expectation/execute_engine/npu_demo/matmul.py`
  - `pytest -q test/pass/nn_lowering`
  - `pytest -q test/dsl/test_emit_c.py`
  - `pytest -q test/dsl/test_gen_kernel.py`
  - `pytest -q test/execute_engine/test_execute_engine_compile.py`
  - `pytest -q test/execute_engine/test_execute_engine_invoke.py`

## 阶段拆分

### S1：expectation 合同与边界收口

#### 阶段目标

- 把 `execute_engine + npu_demo + tiled matmul` 的唯一合同写进 expectation 与计划书，后续实现只按该口径推进。

#### 目标 spec / API

- `spec/execute_engine/execute_engine.md`
- `spec/dsl/emit_c.md`
- `spec/dsl/gen_kernel.md`
- `公开 API：gen_kernel(..., EmitCContext(target="npu_demo")) / ExecutionEngine.compile(...).execute(...)`

#### 可改文件

- `ARCHITECTURE/plan/execute_engine_npu_demo_matmul_green_plan.md`
- `expectation/execute_engine/npu_demo/matmul.py`

#### 预期示例代码

```python
lhs_tile = slice(lhs, [m0, 0], [16, 16], [1, 1], MemorySpace.TSM)
rhs_tile = slice(rhs, [0, n0], [16, 16], [1, 1], MemorySpace.TSM)
partial = matmul(lhs_tile, rhs_tile)
deslice(partial, out, [m0, n0], [16, 16], [1, 1])
```

#### 预期输出

```text
#include "include/npu_demo/npu_demo.h"
...
npu_demo::matmul(lhs_tile, rhs_tile, partial);
```

#### 目标验收资产

- `expectation/execute_engine/npu_demo/matmul.py`
- `merge 阶段必须 git add -f expectation/execute_engine/npu_demo/matmul.py，且不得修改 .gitignore`

#### 验收必过项目

- 文本核对：计划书已写清“不扩展 include/api/Nn.h，只补 npu_demo 后端 leaf helper”
- 文本核对：计划书已写清 expectation 资产在 ignored 路径，merge 阶段必须 `git add -f`
- `python -m py_compile expectation/execute_engine/npu_demo/matmul.py`

#### 任务新建建议

- `任务类型：spec`
- `任务目标：收口 execute_engine npu_demo matmul expectation 合同`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260414-execute-engine-matmul-s1.md`

### S2：前端 TSM 空间保真收口

#### 阶段目标

- 让前端显式 `MemorySpace.TSM` 的 tile memory 在 raw IR 中保持为 `#nn.space<tsm>`，不再退化为 `#nn.space<shared>`。

#### 目标 spec / API

- `spec/dsl/mlir_gen.md`
- `spec/dsl/emit_mlir.md`
- `公开 API：build_func_op_from_ast(...) / emit_mlir(...)`

#### 可改文件

- `kernel_gen/dsl/mlir_gen.py`
- `kernel_gen/dsl/emit_mlir.py`
- `expectation/execute_engine/npu_demo/matmul.py`

#### 预期示例代码

```text
!nn.memory<[16, 16], [16, 1], f32, #nn.space<tsm>>
```

#### 预期输出

```text
#nn.space<tsm>
```

#### 目标验收资产

- `expectation/execute_engine/npu_demo/matmul.py`

#### 验收必过项目

- `PYTHONPATH=. python expectation/execute_engine/npu_demo/matmul.py`

#### 任务新建建议

- `任务类型：build`
- `任务目标：收口前端 TSM tile memory 的 IR 空间保真`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260414-execute-engine-matmul-s2.md`

### S3：loop region 内 matmul lowering 收口

#### 阶段目标

- 让 tiled loop region 内的 `nn.matmul` 能稳定 lower 为 `kernel.matmul`，不再残留 `nn` 级 matmul。

#### 目标 spec / API

- `spec/pass/lowering/nn_lowering.md`
- `公开 API：NnLoweringPass.run(module)`

#### 可改文件

- `kernel_gen/passes/lowering/nn_lowering/nn_lowering.py`
- `test/pass/nn_lowering/matmul.py`
- `expectation/execute_engine/npu_demo/matmul.py`

#### 预期示例代码

```text
symbol.for ... {
  "kernel.matmul"(%lhs_tile, %rhs_tile, %out_tile) ...
}
```

#### 预期输出

```text
CHECK: kernel.matmul
CHECK-NOT: nn.matmul
```

#### 目标验收资产

- `expectation/execute_engine/npu_demo/matmul.py`
- `test/pass/nn_lowering/matmul.py`

#### 验收必过项目

- `pytest -q test/pass/nn_lowering`
- `PYTHONPATH=. python expectation/execute_engine/npu_demo/matmul.py`

#### 任务新建建议

- `任务类型：build`
- `任务目标：收口 tiled loop region 内的 nn.matmul lowering`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260414-execute-engine-matmul-s3.md`

### S4：npu_demo emit_c/gen_kernel 子集收口

#### 阶段目标

- 让 `emit_c/gen_kernel(target="npu_demo")` 能覆盖 tiled matmul 实际命中的最小 op 子集，并生成正确的 `npu_demo` 源码。

#### 目标 spec / API

- `spec/dsl/emit_c.md`
- `spec/dsl/gen_kernel.md`
- `公开 API：emit_c_op(...) / gen_kernel(...)`

#### 可改文件

- `kernel_gen/dsl/emit_c.py`
- `kernel_gen/dsl/gen_kernel.py`
- `test/dsl/test_emit_c.py`
- `test/dsl/test_gen_kernel.py`
- `expectation/execute_engine/npu_demo/matmul.py`

#### 预期示例代码

```cpp
long long c0 = 0;
for (...) {
    slice(lhs_tile, lhs, ...);
    npu_demo::matmul(lhs_tile, rhs_tile, partial);
    deslice(partial, out, ...);
}
```

#### 预期输出

```text
symbol.const / symbol.for / dma.slice / dma.deslice / kernel.matmul
npu_demo::matmul(
```

#### 目标验收资产

- `expectation/execute_engine/npu_demo/matmul.py`
- `test/dsl/test_emit_c.py`
- `test/dsl/test_gen_kernel.py`

#### 验收必过项目

- `pytest -q test/dsl/test_emit_c.py`
- `pytest -q test/dsl/test_gen_kernel.py`
- `PYTHONPATH=. python expectation/execute_engine/npu_demo/matmul.py`

#### 任务新建建议

- `任务类型：build`
- `任务目标：补齐 npu_demo target 的 tiled matmul emit_c/gen_kernel 最小 op 子集`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260414-execute-engine-matmul-s4.md`

### S5：npu_demo 后端 helper 与 execute_engine 真执行

#### 阶段目标

- 补齐 `npu_demo` 后端 matmul helper，并让 execute_engine 对生成源码完成真实编译与真实执行。

#### 目标 spec / API

- `spec/execute_engine/execute_engine.md`
- `spec/execute_engine/execute_engine_target.md`
- `公开 API：ExecutionEngine.compile(...) / CompiledKernel.execute(...)`

#### 可改文件

- `include/npu_demo/Nn.h`
- `kernel_gen/execute_engine/compiler.py`
- `kernel_gen/execute_engine/execution_engine.py`
- `test/execute_engine/test_execute_engine_compile.py`
- `test/execute_engine/test_execute_engine_invoke.py`
- `expectation/execute_engine/npu_demo/matmul.py`

#### 预期示例代码

```python
kernel = engine.compile(request=request)
result = kernel.execute(args=(out, lhs, rhs))
```

#### 预期输出

```text
compile_stdout 不是 dry-run
result == torch.matmul(lhs, rhs)
```

#### 目标验收资产

- `expectation/execute_engine/npu_demo/matmul.py`
- `test/execute_engine/test_execute_engine_compile.py`
- `test/execute_engine/test_execute_engine_invoke.py`

#### 验收必过项目

- `pytest -q test/execute_engine/test_execute_engine_compile.py`
- `pytest -q test/execute_engine/test_execute_engine_invoke.py`
- `PYTHONPATH=. python expectation/execute_engine/npu_demo/matmul.py`

#### 任务新建建议

- `任务类型：build`
- `任务目标：补齐 npu_demo matmul helper 并打通 execute_engine 真执行`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260414-execute-engine-matmul-s5.md`

### S6：回归与 expectation 对齐

#### 阶段目标

- 统一 pass / codegen / execute_engine 三段回归，并确认 expectation 与实现一致。

#### 目标 spec / API

- `spec/pass/lowering/nn_lowering.md`
- `spec/dsl/emit_c.md`
- `spec/dsl/gen_kernel.md`
- `spec/execute_engine/execute_engine.md`

#### 可改文件

- `test/pass/nn_lowering/matmul.py`
- `test/dsl/test_emit_c.py`
- `test/dsl/test_gen_kernel.py`
- `test/execute_engine/test_execute_engine_compile.py`
- `test/execute_engine/test_execute_engine_invoke.py`
- `expectation/execute_engine/npu_demo/matmul.py`

#### 预期示例代码

```text
kernel.matmul -> npu_demo::matmul -> execute_engine result
```

#### 预期输出

```text
all checks passed
```

#### 目标验收资产

- `expectation/execute_engine/npu_demo/matmul.py`
- `pytest -q test/pass/nn_lowering`
- `pytest -q test/dsl/test_emit_c.py`
- `pytest -q test/dsl/test_gen_kernel.py`

#### 验收必过项目

- `pytest -q test/pass/nn_lowering`
- `pytest -q test/dsl/test_emit_c.py`
- `pytest -q test/dsl/test_gen_kernel.py`
- `pytest -q test/execute_engine/test_execute_engine_compile.py`
- `pytest -q test/execute_engine/test_execute_engine_invoke.py`
- `PYTHONPATH=. python expectation/execute_engine/npu_demo/matmul.py`

#### 任务新建建议

- `任务类型：review`
- `任务目标：统一回归 execute_engine npu_demo matmul 全链结果`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260414-execute-engine-matmul-s6.md`

### S7：交付与 ignored expectation 纳入

#### 阶段目标

- 完成最终交付整理，并把 ignored expectation 资产按唯一口径纳入合并结果。

#### 目标 spec / API

- `ARCHITECTURE/plan/execute_engine_npu_demo_matmul_green_plan.md`
- `公开交付：expectation/execute_engine/npu_demo/matmul.py`

#### 可改文件

- `ARCHITECTURE/plan/execute_engine_npu_demo_matmul_green_plan.md`
- `expectation/execute_engine/npu_demo/matmul.py`

#### 预期示例代码

```text
git add -f expectation/execute_engine/npu_demo/matmul.py
```

#### 预期输出

```text
expectation 资产进入最终交付，.gitignore 不变
```

#### 目标验收资产

- `expectation/execute_engine/npu_demo/matmul.py`
- `merge 记录需写明 git add -f expectation/execute_engine/npu_demo/matmul.py`

#### 验收必过项目

- 文本核对：merge 记录已写明 `git add -f expectation/execute_engine/npu_demo/matmul.py`
- 文本核对：`.gitignore` 未修改

#### 任务新建建议

- `任务类型：merge`
- `任务目标：纳入 execute_engine matmul expectation 并完成最终交付`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260414-execute-engine-matmul-s7.md`

## 待确认项

- 问题：`第一轮验收是否只要求固定 shape smoke（32x16 x 16x32, tile=16），还是要同时支持 runtime scalar 形式的 M/K/N/TILE 参数化接口？`
- 可选项：`A. 只做固定 shape smoke；B. 同轮支持 runtime scalar 参数化`
- 差异：`A` 只聚焦 matmul lowering/codegen/execute 三段；`B` 还会把 execute_engine 标量 ABI、symbol loop 和动态 tile 参数一并拉进本轮，范围明显变大。
- 推荐项：`A. 先收固定 shape smoke；参数化接口作为后续单独计划。`

## 参考资料

- [`matmul.plan.md`](../../matmul.plan.md)
- [`expectation/execute_engine/add.py`](../../expectation/execute_engine/add.py)
- [`expectation/pass/lowing/nn_lowering/matmul.py`](../../expectation/pass/lowing/nn_lowering/matmul.py)
- [`include/npu_demo/Nn.h`](../../include/npu_demo/Nn.h)

## 终验结论（2026-04-15 09:22 +0800）

- 终验人：`大闸蟹`
- 终验结论：`不通过`
- 终验依据：
  - 当前主仓可直接复跑的 matmul 专项链路已经通过：
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/execute_engine/npu_demo/matmul.py` -> `CASE-1/CASE-2/CASE-3` 全通过；源码命中 `npu_demo::matmul(...)`，`kernel.compile_stdout` 为空且非 dry-run，`ExecuteResult(ok=True, status_code=0, failure_phrase=None)`。
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/nn_lowering` -> `41 passed`
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_execute_engine_compile.py test/execute_engine/test_execute_engine_invoke.py` -> `17 passed`
  - 但按本计划 `S6` / `完成态定义` / `验收设计` 的总体验收口径，仍要求全量通过 `test/dsl/test_emit_c.py` 与 `test/dsl/test_gen_kernel.py`。当前主仓复跑结果仍未收口：
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/test_emit_c.py` -> `4 failed, 16 passed`
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/test_gen_kernel.py` -> collection error；失败点仍是旧 `tlm` 文本与当前 `tlm1/tlm2/tlm3` 合同不一致
  - 按本计划 `S7` 口径，merge 记录还必须写明 `git add -f expectation/execute_engine/npu_demo/matmul.py`。当前可访问环境里未找到用户提供的 `wt-20260414-execute-engine-matmul-s3/.../20260414-execute-engine-matmul-s3.md` 记录文件，也未在当前仓库索引中看到 `expectation/execute_engine/npu_demo/matmul.py` 的交付证据，因此最终交付文本证据仍不完整。
- 最小阻断项：
  - `S6/S7` 末端收口未闭环：`test/dsl/test_emit_c.py`、`test/dsl/test_gen_kernel.py` 的计划内全量回归仍未通过，且 `expectation/execute_engine/npu_demo/matmul.py` 的 ignored 资产纳入交付证据仍未补齐。
- 唯一修复任务口径：
  - 保留已存在的修复任务 `T-20260415-f564cb3a` 作为唯一有效修复链路。
  - 该任务收口范围应以本终验最小阻断项为准：不仅要修复 `test/dsl/test_gen_kernel.py` 中旧 `tlm` 文本与新合同不一致，还要一并收口 `test/dsl/test_emit_c.py` 当前失败面，并在最终 merge 记录中补齐 `git add -f expectation/execute_engine/npu_demo/matmul.py` 的唯一交付证据。
- 任务链收口口径：
  - 按管理员当前唯一口径，`T-20260414-afcd18ce` 是这条链实际继续推进到 merge 的任务号。
  - 因此任务列表中的 `T-20260414-e259dc60`、`T-20260414-f18f36b7`、`T-20260414-218e8ddc` 应视为重复占位，不再继续分发。

## 归档记录

时间：2026-04-15 14:00 +0800
经办人：李白
任务：T-20260415-7631a51d
任务目标：将 `ARCHITECTURE/plan/execute_engine_npu_demo_matmul_green_plan.md` 归档到 `agents/codex-multi-agents/log/task_records/done_plan/2026/16/execute_engine_npu_demo_matmul_green_plan.md`，并完成归档 merge 收口。
改动：
- 管理员指定的 `worktree=/home/lfr/kernelcode_generate/wt-20260415-archive-execute-engine-matmul-plan` 原本不存在，已按当前远端主分支 `origin/main@0ff3f82` 新建任务分支 `T-20260415-7631a51d` 与对应归档 `worktree`。
- 核对发现源计划书 `ARCHITECTURE/plan/execute_engine_npu_demo_matmul_green_plan.md` 当前为主仓本地计划书文件，未被 `git ls-files` 跟踪，且 `origin/main` 中既无该源计划书也无目标 `done_plan` 文件；因此在指定归档 `worktree` 内将源计划书内容复制为归档目标文件，并在文件尾部追加本次归档记录。
- 本次归档合并范围限定为新增 `agents/codex-multi-agents/log/task_records/done_plan/2026/16/execute_engine_npu_demo_matmul_green_plan.md`；按用户要求，主仓本地源计划书已删除，不修改 `.gitignore`、`TODO.md`、`DONE.md` 或其它共享状态文件。
验证：
- `rg -n "T-20260415-7631a51d" /home/lfr/kernelcode_generate/TODO.md` -> 确认任务为 `merge/进行中/指派=李白`
- `git -C /home/lfr/kernelcode_generate worktree add -b T-20260415-7631a51d /home/lfr/kernelcode_generate/wt-20260415-archive-execute-engine-matmul-plan origin/main` -> 成功创建归档 `worktree`
- `git -C /home/lfr/kernelcode_generate rev-parse --verify origin/main` -> `0ff3f8206f0899a9f432ca292d95c4ff3d06a6b0`
- `git -C /home/lfr/kernelcode_generate ls-tree --name-only origin/main ARCHITECTURE/plan/execute_engine_npu_demo_matmul_green_plan.md agents/codex-multi-agents/log/task_records/done_plan/2026/16/execute_engine_npu_demo_matmul_green_plan.md` -> 无输出，确认远端主分支当前无源计划书与目标归档文件
- `git -C /home/lfr/kernelcode_generate ls-files --stage -- ARCHITECTURE/plan/execute_engine_npu_demo_matmul_green_plan.md agents/codex-multi-agents/log/task_records/done_plan/2026/16/execute_engine_npu_demo_matmul_green_plan.md` -> 无输出，确认两者在主仓当前均未跟踪
- `test -e /home/lfr/kernelcode_generate/ARCHITECTURE/plan/execute_engine_npu_demo_matmul_green_plan.md; echo $?` -> `1`，确认主仓本地源计划书已按用户要求移除
结论：归档文件已在指定 `worktree` 内生成并写入归档记录；下一步提交并推送归档文件，随后执行当前 merge 任务 `-done` 并回报管理员继续 `-done-plan`。
