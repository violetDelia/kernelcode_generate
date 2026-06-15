# multi_buffer_loop_staging_ring

## 文档状态

- 状态：计划级 execute 候选已完成实现、review 通过并进入 archive_acceptance 复验；archive_acceptance 曾发现本文仍停留在下发前口径，本轮仅同步入档状态与任务链事实。
- 守护复验：已由 `守护最好的爱莉希雅` 执行守护最终复验并通过，管理员已据此下发唯一计划级 `execute`，任务号 `T-20260607-0c4db1f1`。
- 任务链事实：唯一计划级 `execute` 已由管理员下发至 `/home/lfr/kernelcode_generate/wt-20260607-multi-buffer-loop-staging-ring`；execute / review 已完成，review 通过后进入 archive_acceptance；comments-only 裁定 A 返工已收口。
- 当前入档修复：archive_acceptance 不通过后退回 execute，仅同步本文档状态、后续流程占位和任务记录；不得修改业务逻辑、公开 API、spec、test、expectation、pipeline option 或稳定错误文本。
- 当前无必过 `expectation`：本计划无当前必过 expectation 合同验收入口，`expectation/` 继续只读且不得修改。
- 最新同步现场：2026-06-08 03:07 +0800 在本 worktree 核对，`HEAD=7cddf72301dcba958fcc0f0cedd34e09b0f24aa0`，`origin/main=b10ded364fb5b4714964faa4ca0cfb9c7cce8f62`，`merge-base=7cddf72301dcba958fcc0f0cedd34e09b0f24aa0`，ahead / behind 为 `0 / 1`；latest main 新增 reference research docs / records，与本候选 staged 路径无重叠。
- 用户需求来源：2026-06-07 用户指出 `multi-buffer` 不应只为 `kernel.matmul` 服务，而应把 loop 外 staging / scratch buffer 改写为多倍 backing storage，在 loop 内通过 `dma.current_ring` 取得当前 slot，保持 loop 内 `subview` / `dma.reinterpret` / 搬运 / 计算继续消费当前 slot view，并在 loop 尾部插入 `dma.advance_ring` 推进到下一块。
- 用户当前要求：先写计划书，把 `/home/lfr/kernelcode_generate/kernel/dump/matmul/inputs_static_tile_static_absent_bias/matmul_inputs_static_tile_static_kernel/24-multi-buffer.mlir` 的 IR 预期写进去；动态例子必须使用 dump 中真实 dynamic matmul IR，不用手写抽象例子；随后用户确认按该计划推进，并将完成目标扩展为 matmul 与 conv2d 都能变换为预期 IR 和代码。
- 用户确认目标：matmul 与 conv2d 的静态 / 动态 IR 都完成 multi-buffer 变换，生成代码逻辑正确，数值精度合格。

## 计划级任务

| 计划任务 | 任务类型 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `multi-buffer-loop-staging-ring` | 唯一计划级 `execute` | `/home/lfr/kernelcode_generate/wt-20260607-multi-buffer-loop-staging-ring` | `agents/codex-multi-agents/log/task_records/2026/23/20260607-multi-buffer-loop-staging-ring.md` |

- 计划书：`ARCHITECTURE/plan/multi_buffer_loop_staging_ring.md`。
- 任务目标：扩展 `MultiBufferPass` 的 loop staging / scratch ring 化能力，完成 matmul 与 conv2d 静态 / 动态 IR 的 `dma.make_ring` / `dma.current_ring` / `dma.advance_ring` 变换，并保证生成代码逻辑正确、数值精度合格。
- 固定流转：`execute -> review -> archive_acceptance -> merge/归档`；本计划只创建一个计划级 `execute`，S0-S6 只作为计划内小任务卡，不创建独立 TODO 任务。
- 下发前置：守护最终复验已通过且无阻断、无最小需改项、无待确认项；管理员已创建并下发唯一计划级 `execute`。
- 依赖前置：默认等待 `T-20260607-2b00a1ea / pass_dump_xdsl_pipeline_spec_options` 完成并合并后再下发；除非正式执行现场已证明包含该任务结果且不会与 `MultiBufferPass`、spec 或测试文件产生并行覆盖风险。
- 范围前置：本计划不混入 CUDA API aligned kernel codegen 计划；CUDA 方向后续另行讨论和计划。
- 共同禁止面：不修改 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`plan/1.md`；不新增 / 删除 / 重命名 / 修改公开 API；不新增 pipeline option；archive_acceptance 状态修复不得触碰业务逻辑、spec、test、pipeline option 或稳定错误文本。

## 计划目标

- 扩展 `MultiBufferPass` 的匹配语义，从当前仅支持 `kernel.matmul` lhs/rhs direct `dma.alloc` pair，提升为面向 `symbol.for` 的 staging / scratch buffer ring 化。
- 让 matmul 静态和动态 lowering dump 在 `multi-buffer` pass 后都出现预期 ring IR：
  - 静态输入 + 静态 tile：`kernel/matmul/inputs_static_tile_static.py` 生成的 absent / present bias 两个 `24-multi-buffer.mlir`。
  - 动态输入 + 动态 tile：`kernel/matmul/inputs_dynamic_tile_dynamic.py` 生成的 `24-multi-buffer.mlir`。
  - 静态输入 + 动态 tile：`kernel/matmul/inputs_static_tile_dynamic.py` 生成的 `24-multi-buffer.mlir`。
- 让 conv2d 静态和动态 lowering dump 在 `multi-buffer` pass 后都出现预期 ring IR：
  - 静态输入 + 静态 tile：`kernel/conv2d/inputs_static_tile_static.py` 生成的 absent / present bias 两个 `24-multi-buffer.mlir`。
  - 静态输入 + 动态 tile：`kernel/conv2d/inputs_static_tile_dynamic.py` 生成的 `24-multi-buffer.mlir`。
  - 动态输入 + 动态 tile：`kernel/conv2d/inputs_dynamic_tile_dynamic.py` 生成的 `24-multi-buffer.mlir`。
- 变换后生成代码必须保持 matmul / conv2d 计算逻辑正确：accumulator 初始化、K/C reduce loop partial compute、累加、bias 分支、最终 output deslice 的顺序和数据依赖不得改变。
- 运行脚本必须通过 NumPy 参考精度校验，absent / present bias 两类输出均合格。
- 目标形态：

```mlir
%buf = "dma.alloc"(...)
symbol.for ... {
  %tile = "dma.reinterpret"(%buf, ...)
  "dma.copy"(%tile, %src)
  "kernel.xxx"(..., %tile, ...)
}
"dma.free"(%buf)
```

改写为：

```mlir
%backing = "dma.alloc"(...)
%ring = "dma.make_ring"(%backing, %num, %offset)
symbol.for ... {
  %cur = "dma.current_ring"(%ring)
  %tile = "dma.reinterpret"(%cur, ...)
  "dma.copy"(%tile, %src)
  "kernel.xxx"(..., %tile, ...)
  "dma.advance_ring"(%ring)
}
"dma.free"(%backing)
```

## 完成态定义

- 静态 IR 变换完成：
  - `kernel/dump/matmul/inputs_static_tile_static_absent_bias/matmul_inputs_static_tile_static_kernel/24-multi-buffer.mlir` 含 `dma.make_ring`、`dma.current_ring`、`dma.advance_ring`。
  - `kernel/dump/matmul/inputs_static_tile_static_present_bias/matmul_inputs_static_tile_static_kernel/24-multi-buffer.mlir` 含 `dma.make_ring`、`dma.current_ring`、`dma.advance_ring`。
  - 对 innermost K loop 的 lhs/rhs staging 和 scratch 候选，原 typed `dma.alloc/free` 已删除；`dma.reinterpret` source 改为本轮 current slot。
- 动态 IR 变换完成：
  - `kernel/dump/matmul/inputs_dynamic_tile_dynamic/24-multi-buffer.mlir` 含 `dma.make_ring`、`dma.current_ring`、`dma.advance_ring`。
  - `kernel/dump/matmul/inputs_static_tile_dynamic/24-multi-buffer.mlir` 含 `dma.make_ring`、`dma.current_ring`、`dma.advance_ring`。
  - dynamic pattern0 / pattern1 的 `%16/%17/%21/%22` 同构候选按真实 dump 结构 ring 化；检查以 type、space、loop、copy/deslice/matmul use 关系为准，不依赖 printer SSA 编号。
  - static input + dynamic tile 的 `%16/%17/%21/%22` 同构候选按真实 dump 结构 ring 化；检查以 type、space、loop、copy/deslice/matmul use 关系为准，不依赖 printer SSA 编号。
  - dynamic tile 的 `num` 计算保留 `symbol.floordiv(target_capacity, total_slot_bytes)` 语义；静态可折叠路径允许后续 canonicalize 折成常量。
- conv2d IR 变换完成：
  - `kernel/dump/conv2d/inputs_static_tile_static_absent_bias/conv2d_inputs_static_tile_static_kernel/24-multi-buffer.mlir` 含 `dma.make_ring`、`dma.current_ring`、`dma.advance_ring`。
  - `kernel/dump/conv2d/inputs_static_tile_static_present_bias/conv2d_inputs_static_tile_static_kernel/24-multi-buffer.mlir` 含 `dma.make_ring`、`dma.current_ring`、`dma.advance_ring`。
  - `kernel/dump/conv2d/inputs_static_tile_dynamic/24-multi-buffer.mlir` 含 `dma.make_ring`、`dma.current_ring`、`dma.advance_ring`。
  - `kernel/dump/conv2d/inputs_dynamic_tile_dynamic/24-multi-buffer.mlir` 含 `dma.make_ring`、`dma.current_ring`、`dma.advance_ring`。
  - conv2d C-channel reduce loop 内的 input slice、weight slice、img2col col、matmul out2、transpose / partial scratch 等 per-reduce staging 候选按真实 use-def ring 化；检查以 op role、type、space、loop、producer/consumer use 关系为准，不依赖 printer SSA 编号。
  - conv2d acc/output tile 只能按 outer output tile loop 生命周期处理，不按 C reduce loop 每轮 advance。
- 代码逻辑正确：
  - ring 化只改变 staging storage 轮转，不改变 `dma.deslice`、`dma.copy`、`kernel.matmul`、`kernel.binary_elewise` 的数据流语义。
  - 变换前必须先逐个分析 `dma.alloc` 的生命周期角色，再决定是否改写；不得先按 loop 层级或 use 形态机械 ring 化。
  - acc/output tile 不按 innermost K loop 每轮 advance，避免破坏 K loop 跨轮累加。
  - 若 acc/output tile 被 ring 化，它的 current/advance 粒度必须绑定外层 output tile 生命周期：进入 reduce loop 前取一次 current，整个 reduce loop 内保持同一个 slot，reduce loop 后完成 bias / output deslice 等最后使用之后才 advance。
  - 若 K/reduce 累加维度承载的 loop-carried acc/output 能绑定外层 output tile loop，则 ring `num` 默认按该 outer output tile loop 的 target capacity / slot bytes 正常计算。
  - 若 K/reduce 累加维度承载的 loop-carried acc/output 不存在可用于跨独立 output tile 轮转的外层 loop，且仍被 ring 化，则 ring `num` 必须退化为 1。
  - bias tile / broadcast 路径不被纳入本计划的 K loop ring 化；若后续处理 outer-loop staging，另行建计划。
- 精度合格：
  - `kernel/matmul/inputs_static_tile_static.py` absent / present bias 均通过脚本内 NumPy 参考校验。
  - `kernel/matmul/inputs_static_tile_dynamic.py` absent / present bias 均通过脚本内 `np.allclose(..., atol=1e-3, rtol=1e-3)`。
  - `kernel/matmul/inputs_dynamic_tile_dynamic.py` absent / present bias 均通过脚本内 `np.allclose(..., atol=1e-3, rtol=1e-3)`。
  - 当前 dynamic 脚本 dump 写出后 source 断言失败属于基线问题，完成态必须修到脚本退出码 0。
  - `kernel/conv2d/inputs_static_tile_static.py` absent / present bias 均通过脚本内 NumPy 参考校验。
  - `kernel/conv2d/inputs_static_tile_dynamic.py` absent / present bias 均通过脚本内 NumPy 参考校验、源码 dump 一致性检查和执行入口运行。
  - `kernel/conv2d/inputs_dynamic_tile_dynamic.py` absent / present bias 均通过脚本内 NumPy 参考校验、源码 dump 一致性检查和执行入口运行。

## 公开 API 与边界

- 不新增、删除、重命名或修改公开 API。
- 保持既有公开入口：
  - `class MultiBufferPass(memory_stage: int = 2, fold: bool = True, target: str | None = None)`
  - `MultiBufferPass.from_options(options: dict[str, str]) -> MultiBufferPass`
  - `MultiBufferPass.apply(ctx: Context, module: ModuleOp) -> None`
- 只扩展 pass 内部匹配和改写行为；不新增 pipeline option。
- 本计划主口径使用既有 `target` 参数：`target` 非空时必须按 target registry 的 memory capacity 计算 ring `num`；`memory_stage` 只保留为 `target is None` 的兼容 fallback，不作为本计划 IR 预期和验收主线。
- 若为源码逻辑验收同步 `kernel/matmul/*.py` 或 `kernel/conv2d/*.py` 内部断言，只允许修同文件内部检查逻辑，不得修改公开 kernel / `main()` 签名；触达实现文件时必须同步文件级说明中的 API 列表。
- 触达 `kernel_gen/passes/memory_plan.py` 或 `kernel_gen/passes/multi_buffer.py` 时，也必须按实现文件规范同步文件级说明中的 API 列表；不得借内部 helper 名义新增未在 spec 明确定义的公开 API。
- 允许修改 `kernel_gen/passes/memory_plan.py` 的内部 auto-pad 表达式解析逻辑，只用于闭合当前 conv2d 在 memory-plan 阶段到不了 `multi-buffer` 的基线问题；不得新增公开 API、pipeline option 或改变公开错误语义。
- `expectation/` 只读，不作为本计划的修改范围。
- 不修改 `.skills/`、`agents/standard/`、`AGENTS.md`。

## 当前基线

- `npu-demo-lowering` 已在 memory-pool 前调用 `MultiBufferPass(memory_stage=2, target=target)`。
- 因 pipeline 已传入 `target=npu_demo`，本计划的 dump 预期按 target 指定口径计算：
  - `tsm_memory_size = 2097152`
  - `tlm1_memory_size = 524288`
  - `tlm2_memory_size = 1048576`
  - `tlm3_memory_size = 1048576`
- 当前 `kernel/dump/matmul/inputs_static_tile_static_absent_bias/matmul_inputs_static_tile_static_kernel/23-canonicalize.mlir -> 24-multi-buffer.mlir` 的 diff 只有首行 marker 从 `canonicalize` 变为 `multi-buffer`，IR 本体无变化。
- 当前 `kernel/dump/matmul/inputs_static_tile_static_present_bias/matmul_inputs_static_tile_static_kernel/23-canonicalize.mlir -> 24-multi-buffer.mlir` 同样只有 marker 变化，IR 本体无变化。
- 当前 `kernel/dump/matmul/inputs_static_tile_dynamic/23-canonicalize.mlir -> 24-multi-buffer.mlir` 同样只有 marker 变化，IR 本体无变化；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_dynamic.py` 当前能写出 dump，但随后 `_assert_accumulator_source` 因 `source.index("deslice(arg0", add_index)` 失败退出，完成态必须闭合该源码逻辑断言。
- 当前 `kernel/dump/matmul/inputs_dynamic_tile_dynamic/23-canonicalize.mlir -> 24-multi-buffer.mlir` 同样只有 marker 变化，IR 本体无变化；`kernel/matmul/inputs_dynamic_tile_dynamic.py` 当前能写出 dump，但随后 `_assert_accumulator_source` 因 `source.index("deslice(arg0", add_index)` 失败退出，完成态必须闭合该源码逻辑断言。
- 当前三条 conv2d demo 均无法跑到 `multi-buffer`：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_static_tile_static.py` 在 `kernel_gen/passes/memory_plan.py::_apply_auto_pad` 中解析 `min(...)` 右侧表达式时报 `symbol expr contains trailing tokens`，当前只写到 `kernel/dump/conv2d/inputs_static_tile_static_present_bias/conv2d_inputs_static_tile_static_kernel/06-lower-nn.mlir`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_static_tile_dynamic.py` 同样在 memory-plan auto-pad 解析失败，当前只写到 `kernel/dump/conv2d/inputs_static_tile_dynamic/06-lower-nn.mlir`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_dynamic_tile_dynamic.py` 同样在 memory-plan auto-pad 解析失败，当前只写到 `kernel/dump/conv2d/inputs_dynamic_tile_dynamic/06-lower-nn.mlir`。
- 当前 `MultiBufferPass` 要求 `kernel.matmul` 第 1/2 operand 的 owner 必须是 `DmaAllocOp`，因此无法处理：

```mlir
%42 = "dma.reinterpret"(%20, ...)
"dma.copy"(%42, %35)
"kernel.matmul"(%29, %42, %43, %acc)
```

- 这份 dump 中实际应优先处理的是 innermost K loop 里的四个 staging / scratch buffer：
  - `%15`: `tsm` `[48,56]`，被 `%35 = dma.reinterpret(%15, ...)` view 后写入并作为后续 copy source。
  - `%16`: `tsm` `[56,80]`，被 `%36 = dma.reinterpret(%16, ...)` view 后写入并作为后续 copy source。
  - `%20`: `tlm1` 或 `tlm2` `[48,56]`，被 `%42 = dma.reinterpret(%20, ...)` view 后作为 copy target 与 compute input。
  - `%21`: `tlm2` 或 `tlm1` `[56,80]`，被 `%43 = dma.reinterpret(%21, ...)` view 后作为 copy target 与 compute input。

## 已确认口径

- 本计划的 innermost K loop staging / scratch IR 预期默认只把 `%15/%16/%20/%21` ring 化。
- 本计划默认不把 `%12/%13` bias / broadcast 路径纳入 K loop ring 化；`%11` acc/output 必须按 outer output tile loop 规则单独分析：
  - `%11` 是 output / acc tile backing，`%29` 跨 innermost K loop 累加，并在 K loop 后继续被 bias / store 消费，不能在 K loop 每轮换 slot。
  - 当前真实 static dump 中 `%11` 外侧存在 `%22` / `%26` 两层 output tile loop；若 `%11` 被证明可作为 outer output tile loop ring 候选，则只能在 reduce loop 前 current，并在 reduce loop、bias 分支和最终 output deslice 都结束后 advance，`num` 按 outer output tile loop 的 target capacity / slot bytes 正常计算。
  - 若未来某个 `%11` 同构形态只有 reduce loop 这一层可见循环、没有外层 output tile loop 可以在不同 output tile 间轮转，则 `%11` ring 化时 `num` 为 1。
  - `%12/%13` 属于 bias / broadcast 路径，生命周期不属于 innermost K loop 的每轮 staging；如果要做 outer M/N loop 级 ring，需要另行明确 target loop 与跨 nested use 的支配 / last-use 插入规则。
- 对应真实 dynamic dump，默认只把 `%16/%17/%21/%22` 纳入 innermost K loop staging / scratch ring 化；`%12` acc/output 必须按 outer output tile loop 规则单独分析，不把 `%14/%15` bias / broadcast 纳入 K loop ring 化：
  - `%12` 是 output / acc tile backing，`%30` 跨 innermost K loop 累加。
  - 当前真实 dynamic dump 中 `%12` 外侧存在 `%23` / `%27` 两层 output tile loop；若 `%12` 被证明可作为 outer output tile loop ring 候选，则只能在 reduce loop 前 current，并在 reduce loop、bias 分支和最终 output deslice 都结束后 advance，`num` 按 outer output tile loop 的 target capacity / slot bytes 正常计算。
  - 若未来某个 `%12` 同构形态只有 reduce loop 这一层可见循环、没有外层 output tile loop 可以在不同 output tile 间轮转，则 `%12` ring 化时 `num` 为 1。
  - `%14/%15` 属于 bias / broadcast 路径。
- 对应真实 conv2d `06-lower-nn.mlir` 基线：
  - conv2d loop 结构是 outer output tile loops `f0/n0/ho0/wo0`，其内存在 batch/`ni` loop，再内层 `c0` 是 C-channel reduce loop。
  - static/static present bias dump 中，acc `%63`、bias tile `%65`、bias full `%67` 在 C reduce loop 外创建；`%63` 跨 C reduce loop 累加并在 bias 分支和最终 output deslice 后结束生命周期，不能按 C reduce loop 每轮 advance。
  - static/static present bias dump 中，C reduce loop 内 `%75` input slice、`%76` weight slice、`%77` img2col col、`%80` matmul out2、`%85` transpose output、`%86` partial scratch 是 per-reduce staging / scratch 候选；若 type/alias/free/last-use 可证明，应按 C reduce loop ring 化。
  - static/dynamic dump 中同构候选为 `%77/%78/%79/%82/%87/%88`，acc/output `%65` 只能按 outer output tile loop 单独分析。
  - dynamic/dynamic dump 中同构候选为 `%101/%102/%103/%106/%112/%113`，acc/output `%89` 只能按 outer output tile loop 单独分析。
  - conv2d bias tile / broadcast full 不纳入本计划的 reduce-loop ring 主线；若后续需要 outer output tile ring，必须遵守 acc/output lifecycle 与 `num` 规则。
- 本轮待用户确认项：无。

## 目标行为

- 支持 `dma.reinterpret(%alloc, ...)`、`dma.view(%alloc, ...)`、`dma.reshape(%alloc, ...)` 作为 staging / scratch direct alias。
- 支持 direct alloc use：当 `dma.slice`、`kernel.img2col2d`、`kernel.matmul`、`dma.transpose`、`dma.fill`、`dma.deslice`、`kernel.binary_elewise` 等 op 的某个 memory operand 直接使用原始 `dma.alloc`，且 type、loop、读写方向和 last-use 均可证明时，该 operand 可直接改为本轮 `dma.current_ring` result，不要求中间一定存在 view op。
- 支持 alias result 被 `dma.copy`、`dma.deslice`、`dma.slice`、`dma.transpose`、`kernel.*` 等 loop 内 op 消费，而不是只识别 `kernel.matmul`。
- 必须先分析每个候选 `dma.alloc`，再执行变换：
  - 先识别 role：per-iteration staging / scratch、loop-carried accumulator / output、post-reduce bias / broadcast staging、未知 / escape。
  - 再决定 `target_loop`、`advance_loop`、`num` 计算口径和是否允许删除原 alloc/free。
  - 未能证明 role、target loop 或 last-use 的 alloc 保持 no-op。
- 只在可证明每轮迭代独立时 ring 化：
  - 原始 `dma.alloc` 位于目标 loop 外。
  - 原始 `dma.free` 位于目标 loop 后。
  - 原始 `dma.alloc` 的 loop 内 use 全部通过同一目标 loop 内的 direct alias 或 direct use 进入。
  - alias result 不逃逸出目标 loop。
  - direct use operand 不逃逸出目标 loop，且该 operand 的读写角色可纳入同一个 slot 的本轮 first-use / last-use 计算。
  - 对同一 slot 的本轮最后一次 use 可在目标 loop 内确定。
- 保留 `dma.reinterpret` / `dma.view` / `dma.reshape` / `dma.subview` 等 view op，用 `dma.current_ring` result 替换 view source。
- 对无 view 的 direct use，直接用 `dma.current_ring` result 替换该 op 的对应 memory operand；替换后 op 的其它 operand、result type、属性和执行顺序保持不变。
- 在目标 loop 内第一个本轮 use 之前插入 `dma.current_ring`。
- 在目标 loop 内该 slot 本轮最后一次 use 后插入 `dma.advance_ring`。
- `dma.advance_ring` 的插入点必须按 value lifetime 决定，不得机械地放在出现 use 的最内层 loop 尾部：
  - 每轮独立 staging / scratch buffer：在对应 target loop 本轮最后一次 use 后 advance，典型为 innermost K loop 的 lhs/rhs staging。
  - loop-carried accumulator / output tile：如果 value 在 reduce loop 多轮之间保持状态，并在 reduce loop 后继续被 bias/store 消费，则 target loop 必须是外层 output tile loop，current 必须支配整个 reduce loop，advance 必须在 reduce loop 之后、所有 post-reduce use 之后，`num` 按 target capacity 正常计算。
  - 只有 reduce loop、没有可轮转外层 loop 的 loop-carried accumulator / output tile：如果仍生成 ring，`num` 必须为 1。
  - 无法证明 target loop 与 advance loop 时保持 no-op。
- 删除原 staging `dma.alloc/free`：变换完成后，原来的 typed `dma.alloc` 及其匹配 `dma.free` 不应再留在 IR 中；只保留新增的一维 `i8` backing `dma.alloc/free` 与对应 `dma.make_ring`。

## target 指定的 num 计算口径

- 本计划正式执行时默认按 `target` 非空路径验收；`npu-demo-lowering` 当前就是 `MultiBufferPass(memory_stage=2, target="npu_demo")`。
- `num` 不使用 `memory_stage=2` 固定值，而是按 target registry capacity 计算。
- capacity / slot bytes 公式适用于已证明 target loop 的 ring 候选：
  - 每轮独立 staging / scratch 使用对应 producer / consumer loop，典型为 innermost K loop。
  - loop-carried accumulator / output 使用外层 output tile loop，且 advance 在 reduce loop 与 post-reduce last use 之后。
- loop-carried accumulator / output tile 不得混入 innermost K loop staging / scratch 的 same-space 分组；它必须先按 reduce-carried 规则确定 outer output tile loop，能确定时按该 loop 正常计算 `num`，只有一层 reduce loop、无外层可轮转 loop 时 ring `num` 退化为 1，无法证明 lifecycle 时 no-op。
- 分组规则：
  - 同一个 target loop 内、同一个 memory space 的所有本轮 ring 候选共享一个 `num`。
  - 不同 memory space 独立计算 `num`。
- 计算公式：
  - `slot_bytes = element_byte_width * product(slot_shape)`
  - `space_total_slot_bytes = sum(slot_bytes for same loop and same memory space)`
  - `num = target_space_capacity floordiv space_total_slot_bytes`
  - `backing_bytes(candidate) = num * slot_bytes(candidate)`
- 如果 target 缺少对应 `*_memory_size`、capacity <= 0、`space_total_slot_bytes <= 0` 或静态可判定 `num <= 0`，该组保持 no-op，不生成畸形 ring。
- 对当前 `npu_demo` dump：
  - `tsm` lhs/rhs staging 共享 `num = 2097152 floordiv (lhs_slot_bytes + rhs_slot_bytes)`。
  - `tlm1/tlm2/tlm3` 候选按各自 space capacity 独立计算；若同一 loop 同一 local space 内后续出现多个候选，也按该 space 的 slot bytes 合计共享 `num`。
  - 静态 `%11` / dynamic `%12` 这类 acc/output backing 不参与上述 K-loop `tsm` staging 分组；当前真实 dump 有外层 output tile loop，若被证明可 ring 化，则按 outer output tile loop 正常计算 `num`；只有没有外层可轮转 output loop 的形态才 `num = 1`。

## 非目标

- 不做 async / barrier / wait / sign overlap。
- 不做通用 alias escape 分析。
- 不处理多层 alias chain；v1 只支持 direct `dma.reinterpret(%alloc, ...)` / `dma.view(%alloc, ...)` / `dma.reshape(%alloc, ...)` alias，以及已证明的 direct alloc use。
- 不处理已有 ring 再 ring 化。
- 不修改 memory-pool 后是否加 CSE的策略。
- 不改源码发射层 `+ 0` 清理。
- 不新增 pipeline option。
- 不把 `memory_stage` 固定 stage 模式作为本计划验收主线；该模式仅作为 `target is None` 的既有兼容行为保留。
- 不混入 `cuda_sm86` API aligned kernel codegen、CUTLASS/cuBLAS 或 CUDA 后端计划；CUDA 方向在本计划之外另行讨论。

## IR 预期：`inputs_static_tile_static_absent_bias`

- 输入路径：`/home/lfr/kernelcode_generate/kernel/dump/matmul/inputs_static_tile_static_absent_bias/matmul_inputs_static_tile_static_kernel/24-multi-buffer.mlir`
- 本节分两层：
  - 先给 `multi-buffer` pass 刚改写出来、尚未经过 `canonicalize` / fold 的动态计算 IR 片段，说明 `slot_bytes -> num -> backing_bytes` 的计算逻辑。
  - 再给折叠后的完整结构检查预期，便于对照当前 static dump 的 pattern0 / pattern1。
- 动态 shape 示例使用真实 dump：`/home/lfr/kernelcode_generate/kernel/dump/matmul/inputs_dynamic_tile_dynamic/24-multi-buffer.mlir`。
- 真实 printer 可重新编号 SSA；检查时以 op 顺序、type、ring source、copy/compute operand 和 free 关系为准。

### 未 canonicalize/fold 的动态计算片段

- 这个片段展示 `target=npu_demo` 时 pass 自己应生成的计算链；即使输入 shape 是 `%8 = 48`、`%14 = 56`、`%9 = 80` 这种静态 SSA，pass 也可以先产出 `symbol.mul/add/floordiv`，后续 `canonicalize` 再把它们折成 `#C10752`、`#C73`、`#C784896` 等常量。
- 对 pattern0 的 `%15/%16` 两个 `tsm` staging buffer，同一 space 需要共享同一个 `num`，所以先把两个 slot bytes 相加：

```mlir
// 已有 tile shape SSA：
// %8  = 48
// %9  = 80
// %14 = 56
%bpe = symbol.const 4 : !symbol.int<#symbol.expr<4>>

// 原 %15: !nn.memory<[48,56], [56,1], f32, tsm>
%tsm_lhs_numel = symbol.mul %8, %14 : !symbol.int<#C48>, !symbol.int<#C56> -> !symbol.int<#symbol.expr<48*56>>
%tsm_lhs_slot_bytes = symbol.mul %tsm_lhs_numel, %bpe : !symbol.int<#symbol.expr<48*56>>, !symbol.int<#symbol.expr<4>> -> !symbol.int<#symbol.expr<4*48*56>>

// 原 %16: !nn.memory<[56,80], [80,1], f32, tsm>
%tsm_rhs_numel = symbol.mul %14, %9 : !symbol.int<#C56>, !symbol.int<#C80> -> !symbol.int<#symbol.expr<56*80>>
%tsm_rhs_slot_bytes = symbol.mul %tsm_rhs_numel, %bpe : !symbol.int<#symbol.expr<56*80>>, !symbol.int<#symbol.expr<4>> -> !symbol.int<#symbol.expr<4*56*80>>

// tsm capacity = 2097152，same-space pair 共享 num。
%tsm_total_slot_bytes = symbol.add %tsm_lhs_slot_bytes, %tsm_rhs_slot_bytes : !symbol.int<#symbol.expr<4*48*56>>, !symbol.int<#symbol.expr<4*56*80>> -> !symbol.int<#symbol.expr<4*48*56 + 4*56*80>>
%tsm_capacity = symbol.const 2097152 : !symbol.int<#symbol.expr<2097152>>
%tsm_num = symbol.floordiv %tsm_capacity, %tsm_total_slot_bytes : !symbol.int<#symbol.expr<2097152>>, !symbol.int<#symbol.expr<4*48*56 + 4*56*80>> -> !symbol.int<#symbol.expr<2097152 floordiv (4*48*56 + 4*56*80)>>

// backing bytes = num * slot_bytes。这里故意保留动态表达式，不提前折成 784896 / 1308160。
%tsm_lhs_backing_bytes = symbol.mul %tsm_num, %tsm_lhs_slot_bytes : !symbol.int<#symbol.expr<2097152 floordiv (4*48*56 + 4*56*80)>>, !symbol.int<#symbol.expr<4*48*56>> -> !symbol.int<#symbol.expr<(2097152 floordiv (4*48*56 + 4*56*80))*(4*48*56)>>
%tsm_rhs_backing_bytes = symbol.mul %tsm_num, %tsm_rhs_slot_bytes : !symbol.int<#symbol.expr<2097152 floordiv (4*48*56 + 4*56*80)>>, !symbol.int<#symbol.expr<4*56*80>> -> !symbol.int<#symbol.expr<(2097152 floordiv (4*48*56 + 4*56*80))*(4*56*80)>>

%tsm_lhs_backing = "dma.alloc"(%tsm_lhs_backing_bytes) <{operandSegmentSizes = array<i32: 1>}> : (!symbol.int<#symbol.expr<(2097152 floordiv (4*48*56 + 4*56*80))*(4*48*56)>>) -> !nn.memory<[#symbol.expr<(2097152 floordiv (4*48*56 + 4*56*80))*(4*48*56)>], [#C1], i8, #nn.space<tsm>>
%tsm_lhs_ring = "dma.make_ring"(%tsm_lhs_backing, %tsm_num, %tsm_lhs_slot_bytes) : (!nn.memory<[#symbol.expr<(2097152 floordiv (4*48*56 + 4*56*80))*(4*48*56)>], [#C1], i8, #nn.space<tsm>>, !symbol.int<#symbol.expr<2097152 floordiv (4*48*56 + 4*56*80)>>, !symbol.int<#symbol.expr<4*48*56>>) -> !dma.ring<!nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tsm>>>

%tsm_rhs_backing = "dma.alloc"(%tsm_rhs_backing_bytes) <{operandSegmentSizes = array<i32: 1>}> : (!symbol.int<#symbol.expr<(2097152 floordiv (4*48*56 + 4*56*80))*(4*56*80)>>) -> !nn.memory<[#symbol.expr<(2097152 floordiv (4*48*56 + 4*56*80))*(4*56*80)>], [#C1], i8, #nn.space<tsm>>
%tsm_rhs_ring = "dma.make_ring"(%tsm_rhs_backing, %tsm_num, %tsm_rhs_slot_bytes) : (!nn.memory<[#symbol.expr<(2097152 floordiv (4*48*56 + 4*56*80))*(4*56*80)>], [#C1], i8, #nn.space<tsm>>, !symbol.int<#symbol.expr<2097152 floordiv (4*48*56 + 4*56*80)>>, !symbol.int<#symbol.expr<4*56*80>>) -> !dma.ring<!nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tsm>>>
```

- 对 pattern0 的 `%20/%21`，它们分别在 `tlm1` / `tlm2`，不同 space 不相加，各自用本 space capacity 算 `num`：

```mlir
// 原 %20: !nn.memory<[48,56], [56,1], f32, tlm1>
%tlm1_capacity = symbol.const 524288 : !symbol.int<#symbol.expr<524288>>
%tlm1_num = symbol.floordiv %tlm1_capacity, %tsm_lhs_slot_bytes : !symbol.int<#symbol.expr<524288>>, !symbol.int<#symbol.expr<4*48*56>> -> !symbol.int<#symbol.expr<524288 floordiv (4*48*56)>>
%tlm1_backing_bytes = symbol.mul %tlm1_num, %tsm_lhs_slot_bytes : !symbol.int<#symbol.expr<524288 floordiv (4*48*56)>>, !symbol.int<#symbol.expr<4*48*56>> -> !symbol.int<#symbol.expr<(524288 floordiv (4*48*56))*(4*48*56)>>
%tlm1_backing = "dma.alloc"(%tlm1_backing_bytes) <{operandSegmentSizes = array<i32: 1>}> : (!symbol.int<#symbol.expr<(524288 floordiv (4*48*56))*(4*48*56)>>) -> !nn.memory<[#symbol.expr<(524288 floordiv (4*48*56))*(4*48*56)>], [#C1], i8, #nn.space<tlm1>>
%tlm1_ring = "dma.make_ring"(%tlm1_backing, %tlm1_num, %tsm_lhs_slot_bytes) : (!nn.memory<[#symbol.expr<(524288 floordiv (4*48*56))*(4*48*56)>], [#C1], i8, #nn.space<tlm1>>, !symbol.int<#symbol.expr<524288 floordiv (4*48*56)>>, !symbol.int<#symbol.expr<4*48*56>>) -> !dma.ring<!nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tlm1>>>

// 原 %21: !nn.memory<[56,80], [80,1], f32, tlm2>
%tlm2_capacity = symbol.const 1048576 : !symbol.int<#symbol.expr<1048576>>
%tlm2_num = symbol.floordiv %tlm2_capacity, %tsm_rhs_slot_bytes : !symbol.int<#symbol.expr<1048576>>, !symbol.int<#symbol.expr<4*56*80>> -> !symbol.int<#symbol.expr<1048576 floordiv (4*56*80)>>
%tlm2_backing_bytes = symbol.mul %tlm2_num, %tsm_rhs_slot_bytes : !symbol.int<#symbol.expr<1048576 floordiv (4*56*80)>>, !symbol.int<#symbol.expr<4*56*80>> -> !symbol.int<#symbol.expr<(1048576 floordiv (4*56*80))*(4*56*80)>>
%tlm2_backing = "dma.alloc"(%tlm2_backing_bytes) <{operandSegmentSizes = array<i32: 1>}> : (!symbol.int<#symbol.expr<(1048576 floordiv (4*56*80))*(4*56*80)>>) -> !nn.memory<[#symbol.expr<(1048576 floordiv (4*56*80))*(4*56*80)>], [#C1], i8, #nn.space<tlm2>>
%tlm2_ring = "dma.make_ring"(%tlm2_backing, %tlm2_num, %tsm_rhs_slot_bytes) : (!nn.memory<[#symbol.expr<(1048576 floordiv (4*56*80))*(4*56*80)>], [#C1], i8, #nn.space<tlm2>>, !symbol.int<#symbol.expr<1048576 floordiv (4*56*80)>>, !symbol.int<#symbol.expr<4*56*80>>) -> !dma.ring<!nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tlm2>>>
```

- loop 内仍然保留原来的 tile view 计算；区别只是 view source 从原 alloc 换成 current slot：

```mlir
symbol.for %32 = %7 to %5 step %14 {iter = #It3} {
  %34 = symbol.min %14, %33 : !symbol.int<#C56>, !symbol.int<#S6> -> !symbol.int<#S7>

  %cur_lhs = "dma.current_ring"(%tlm1_ring) : (!dma.ring<!nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tlm1>>>) -> !nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tlm1>>
  %42 = "dma.reinterpret"(%cur_lhs, %7, %24, %34, %34, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tlm1>>, !symbol.int<#C0>, !symbol.int<#S2>, !symbol.int<#S7>, !symbol.int<#S7>, !symbol.int<#C1>) -> !nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tlm1>>
  "dma.copy"(%42, %35) : (!nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tlm1>>, !nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tsm>>) -> ()

  "kernel.matmul"(%29, %42, %43, %acc) ...
  "dma.advance_ring"(%tlm1_ring) : (!dma.ring<!nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tlm1>>>) -> !nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tlm1>>
}
```

### 真实 static input + dynamic tile matmul dump 例子

- 输入路径：`/home/lfr/kernelcode_generate/kernel/dump/matmul/inputs_static_tile_dynamic/24-multi-buffer.mlir`
- 该 dump 可由 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_dynamic.py` 写出；当前脚本在 dump 写出后继续进入 `_assert_accumulator_source` 并因旧源码字符串断言失败退出，失败点不影响本节引用的 MLIR dump。
- 当前 static input + dynamic tile dump 的 `23-canonicalize.mlir -> 24-multi-buffer.mlir` diff 仍只有首行 marker 从 `canonicalize` 变为 `multi-buffer`，说明现有 pass 没有处理这些 dynamic tile staging alias。
- 真实 static input + dynamic tile pattern0 中 innermost K loop 应优先 ring 化 `%16/%17/%21/%22`，而不是 `%12/%14/%15`：
  - `%12` 是 output / acc tile backing，`%30` 跨 K loop 累加，K loop 每轮不能换 slot；若被 ring 化，只能绑定外层 `%23/%27` output tile loop 生命周期。
  - `%14/%15` 属于 bias / broadcast 路径，不是 K loop 的每轮 lhs/rhs staging。
  - `%16/%17` 是 global -> tsm 的 K loop staging。
  - `%21/%22` 是 tsm -> tlm 的 K loop scratch / compute input。
- pattern0 使用真实 shape 符号 `%4 = TILE_H`、`%5 = TILE_W`、`%6 = TILE_K`，K loop 是 `symbol.for %34 = %10 to %8 step %6`，其中 `%8 = 241`；pattern1 同构，区别只在 `%21/%22` 的 local space 互换。
- ring 计算与 loop 改写预期沿用下方真实 dynamic matmul 小节的未 fold 公式：
  - `tsm` `%16/%17` 同一 target loop、同一 space 共享 `num = 2097152 floordiv (4*TILE_H*TILE_K + 4*TILE_K*TILE_W)`。
  - pattern0 `%21` 在 `tlm1`，`num = 524288 floordiv (4*TILE_H*TILE_K)`；pattern0 `%22` 在 `tlm2`，`num = 1048576 floordiv (4*TILE_K*TILE_W)`。
  - pattern1 `%21` 在 `tlm2`，`num = 1048576 floordiv (4*TILE_H*TILE_K)`；pattern1 `%22` 在 `tlm1`，`num = 524288 floordiv (4*TILE_K*TILE_W)`。
- 完成态检查必须把 `kernel/dump/matmul/inputs_static_tile_dynamic/24-multi-buffer.mlir` 与 `inputs_dynamic_tile_dynamic/24-multi-buffer.mlir` 同等看待：都必须包含 ring op，且 use-def 检查必须证明 `%37/%38/%44/%45` 同构 view 的 source 来自对应 current slot，`kernel.matmul` 仍消费 local-space tile view，`dma.advance_ring` 位于本轮最后一次 `dma.deslice` / `dma.copy` / `kernel.matmul` 使用之后。

### 真实 dynamic matmul dump 例子

- 输入路径：`/home/lfr/kernelcode_generate/kernel/dump/matmul/inputs_dynamic_tile_dynamic/24-multi-buffer.mlir`
- 该 dump 可由 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py` 生成；当前脚本在 dump 写出后会继续进入 source 断言并失败，失败点不影响本节引用的 MLIR dump。
- 当前 dynamic dump 的 `23-canonicalize.mlir -> 24-multi-buffer.mlir` diff 仍只有首行 marker 从 `canonicalize` 变为 `multi-buffer`，说明现有 pass 没有处理这些 dynamic staging alias。
- 真实 dynamic pattern0 中 innermost K loop 应优先 ring 化 `%16/%17/%21/%22`，而不是 `%12/%14/%15`：
  - `%12` 是 output / acc tile backing，`%30` 跨 K loop 累加，K loop 每轮不能换 slot。
  - `%14/%15` 属于 bias / broadcast 路径，不是 K loop 的每轮 lhs/rhs staging。
  - `%16/%17` 是 global -> tsm 的 K loop staging。
  - `%21/%22` 是 tsm -> tlm 的 K loop scratch / compute input。

真实 pattern0 基线片段如下：

```mlir
func.func @matmul_inputs_dynamic_tile_dynamic_kernel_pattern0(
  %0: !nn.memory<[#S_H, #S_W], [#S_W, #C1], f32, #nn.space<global>>,
  %1: !nn.memory<[#S_H, #S_K], [#S_K, #C1], f32, #nn.space<global>>,
  %2: !nn.memory<[#S_K, #S_W], [#S_W, #C1], f32, #nn.space<global>>,
  %3: !nn.memory<[#S_W], [#C1], f32, #nn.space<global>>,
  %4: !symbol.int<#S_TILE_H>,
  %5: !symbol.int<#S_TILE_W>,
  %6: !symbol.int<#S_TILE_K>) {
  %16 = "dma.alloc"(%4, %6) <{operandSegmentSizes = array<i32: 2>}> : (!symbol.int<#S_TILE_H>, !symbol.int<#S_TILE_K>) -> !nn.memory<[#S_TILE_H, #S_TILE_K], [#S_TILE_K, #C1], f32, #nn.space<tsm>>
  %17 = "dma.alloc"(%6, %5) <{operandSegmentSizes = array<i32: 2>}> : (!symbol.int<#S_TILE_K>, !symbol.int<#S_TILE_W>) -> !nn.memory<[#S_TILE_K, #S_TILE_W], [#S_TILE_W, #C1], f32, #nn.space<tsm>>
  %21 = "dma.alloc"(%4, %6) <{operandSegmentSizes = array<i32: 2>}> : (!symbol.int<#S_TILE_H>, !symbol.int<#S_TILE_K>) -> !nn.memory<[#S_TILE_H, #S_TILE_K], [#S_TILE_K, #C1], f32, #nn.space<tlm1>>
  %22 = "dma.alloc"(%6, %5) <{operandSegmentSizes = array<i32: 2>}> : (!symbol.int<#S_TILE_K>, !symbol.int<#S_TILE_W>) -> !nn.memory<[#S_TILE_K, #S_TILE_W], [#S_TILE_W, #C1], f32, #nn.space<tlm2>>

  symbol.for %34 = %10 to %8 step %6 {iter = #It3} {
    %35 = symbol.sub %8, %34 : !symbol.int<#S_K>, !symbol.iter<start = #C0, end = #S_K, step = #S_TILE_K> -> !symbol.int<#S6>
    %36 = symbol.min %6, %35 : !symbol.int<#S_TILE_K>, !symbol.int<#S6> -> !symbol.int<#S7>
    %37 = "dma.reinterpret"(%16, %10, %25, %36, %36, %11) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#S_TILE_H, #S_TILE_K], [#S_TILE_K, #C1], f32, #nn.space<tsm>>, !symbol.int<#C0>, !symbol.int<#S2>, !symbol.int<#S7>, !symbol.int<#S7>, !symbol.int<#C1>) -> !nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tsm>>
    %38 = "dma.reinterpret"(%17, %10, %36, %29, %29, %11) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#S_TILE_K, #S_TILE_W], [#S_TILE_W, #C1], f32, #nn.space<tsm>>, !symbol.int<#C0>, !symbol.int<#S7>, !symbol.int<#S5>, !symbol.int<#S5>, !symbol.int<#C1>) -> !nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tsm>>
    "dma.deslice"(%37, %40, %10, %10, %25, %36, %11, %11) : (!nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tsm>>, !nn.memory<[#S2, #S7], [#S_K, #C1], f32, #nn.space<global>>, !symbol.int<#C0>, !symbol.int<#C0>, !symbol.int<#S2>, !symbol.int<#S7>, !symbol.int<#C1>, !symbol.int<#C1>) -> ()
    "dma.deslice"(%38, %43, %10, %10, %36, %29, %11, %11) : (!nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tsm>>, !nn.memory<[#S7, #S5], [#S_W, #C1], f32, #nn.space<global>>, !symbol.int<#C0>, !symbol.int<#C0>, !symbol.int<#S7>, !symbol.int<#S5>, !symbol.int<#C1>, !symbol.int<#C1>) -> ()
    %44 = "dma.reinterpret"(%21, %10, %25, %36, %36, %11) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#S_TILE_H, #S_TILE_K], [#S_TILE_K, #C1], f32, #nn.space<tlm1>>, !symbol.int<#C0>, !symbol.int<#S2>, !symbol.int<#S7>, !symbol.int<#S7>, !symbol.int<#C1>) -> !nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tlm1>>
    "dma.copy"(%44, %37) : (!nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tlm1>>, !nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tsm>>) -> ()
    %45 = "dma.reinterpret"(%22, %10, %36, %29, %29, %11) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#S_TILE_K, #S_TILE_W], [#S_TILE_W, #C1], f32, #nn.space<tlm2>>, !symbol.int<#C0>, !symbol.int<#S7>, !symbol.int<#S5>, !symbol.int<#S5>, !symbol.int<#C1>) -> !nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tlm2>>
    "dma.copy"(%45, %38) : (!nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tlm2>>, !nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tsm>>) -> ()
    %acc = symbol.ne %34, %10 : !symbol.iter<start = #C0, end = #S_K, step = #S_TILE_K>, !symbol.int<#C0> -> i1
    "kernel.matmul"(%30, %44, %45, %acc) {space = #nn.space<tsm>} : (!nn.memory<[#S2, #S5], [#S5, #C1], f32, #nn.space<tsm>>, !nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tlm1>>, !nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tlm2>>, i1) -> ()
  }
}
```

- 对真实 dynamic pattern0，pass 应生成的未 fold 计算链如下。这里的 `%4/%5/%6` 就是 dump 里的 `TILE_H/TILE_W/TILE_K` 参数，不是手写占位符：

```mlir
%bpe = symbol.const 4 : !symbol.int<#symbol.expr<4>>

// 原 %16: !nn.memory<[TILE_H,TILE_K], [TILE_K,1], f32, tsm>
%tsm_lhs_numel = symbol.mul %4, %6 : !symbol.int<#S_TILE_H>, !symbol.int<#S_TILE_K> -> !symbol.int<#symbol.expr<TILE_H*TILE_K>>
%tsm_lhs_slot_bytes = symbol.mul %tsm_lhs_numel, %bpe : !symbol.int<#symbol.expr<TILE_H*TILE_K>>, !symbol.int<#symbol.expr<4>> -> !symbol.int<#symbol.expr<4*TILE_H*TILE_K>>

// 原 %17: !nn.memory<[TILE_K,TILE_W], [TILE_W,1], f32, tsm>
%tsm_rhs_numel = symbol.mul %6, %5 : !symbol.int<#S_TILE_K>, !symbol.int<#S_TILE_W> -> !symbol.int<#symbol.expr<TILE_K*TILE_W>>
%tsm_rhs_slot_bytes = symbol.mul %tsm_rhs_numel, %bpe : !symbol.int<#symbol.expr<TILE_K*TILE_W>>, !symbol.int<#symbol.expr<4>> -> !symbol.int<#symbol.expr<4*TILE_K*TILE_W>>

// tsm 同一 space 的 lhs/rhs staging 共享同一个 num。
%tsm_total_slot_bytes = symbol.add %tsm_lhs_slot_bytes, %tsm_rhs_slot_bytes : !symbol.int<#symbol.expr<4*TILE_H*TILE_K>>, !symbol.int<#symbol.expr<4*TILE_K*TILE_W>> -> !symbol.int<#symbol.expr<4*TILE_H*TILE_K + 4*TILE_K*TILE_W>>
%tsm_capacity = symbol.const 2097152 : !symbol.int<#symbol.expr<2097152>>
%tsm_num = symbol.floordiv %tsm_capacity, %tsm_total_slot_bytes : !symbol.int<#symbol.expr<2097152>>, !symbol.int<#symbol.expr<4*TILE_H*TILE_K + 4*TILE_K*TILE_W>> -> !symbol.int<#symbol.expr<2097152 floordiv (4*TILE_H*TILE_K + 4*TILE_K*TILE_W)>>
%tsm_lhs_backing_bytes = symbol.mul %tsm_num, %tsm_lhs_slot_bytes : !symbol.int<#symbol.expr<2097152 floordiv (4*TILE_H*TILE_K + 4*TILE_K*TILE_W)>>, !symbol.int<#symbol.expr<4*TILE_H*TILE_K>> -> !symbol.int<#symbol.expr<(2097152 floordiv (4*TILE_H*TILE_K + 4*TILE_K*TILE_W))*(4*TILE_H*TILE_K)>>
%tsm_rhs_backing_bytes = symbol.mul %tsm_num, %tsm_rhs_slot_bytes : !symbol.int<#symbol.expr<2097152 floordiv (4*TILE_H*TILE_K + 4*TILE_K*TILE_W)>>, !symbol.int<#symbol.expr<4*TILE_K*TILE_W>> -> !symbol.int<#symbol.expr<(2097152 floordiv (4*TILE_H*TILE_K + 4*TILE_K*TILE_W))*(4*TILE_K*TILE_W)>>

%tsm_lhs_backing = "dma.alloc"(%tsm_lhs_backing_bytes) <{operandSegmentSizes = array<i32: 1>}> : (!symbol.int<#symbol.expr<(2097152 floordiv (4*TILE_H*TILE_K + 4*TILE_K*TILE_W))*(4*TILE_H*TILE_K)>>) -> !nn.memory<[#symbol.expr<(2097152 floordiv (4*TILE_H*TILE_K + 4*TILE_K*TILE_W))*(4*TILE_H*TILE_K)>], [#C1], i8, #nn.space<tsm>>
%tsm_lhs_ring = "dma.make_ring"(%tsm_lhs_backing, %tsm_num, %tsm_lhs_slot_bytes) : (!nn.memory<[#symbol.expr<(2097152 floordiv (4*TILE_H*TILE_K + 4*TILE_K*TILE_W))*(4*TILE_H*TILE_K)>], [#C1], i8, #nn.space<tsm>>, !symbol.int<#symbol.expr<2097152 floordiv (4*TILE_H*TILE_K + 4*TILE_K*TILE_W)>>, !symbol.int<#symbol.expr<4*TILE_H*TILE_K>>) -> !dma.ring<!nn.memory<[#S_TILE_H, #S_TILE_K], [#S_TILE_K, #C1], f32, #nn.space<tsm>>>
%tsm_rhs_backing = "dma.alloc"(%tsm_rhs_backing_bytes) <{operandSegmentSizes = array<i32: 1>}> : (!symbol.int<#symbol.expr<(2097152 floordiv (4*TILE_H*TILE_K + 4*TILE_K*TILE_W))*(4*TILE_K*TILE_W)>>) -> !nn.memory<[#symbol.expr<(2097152 floordiv (4*TILE_H*TILE_K + 4*TILE_K*TILE_W))*(4*TILE_K*TILE_W)>], [#C1], i8, #nn.space<tsm>>
%tsm_rhs_ring = "dma.make_ring"(%tsm_rhs_backing, %tsm_num, %tsm_rhs_slot_bytes) : (!nn.memory<[#symbol.expr<(2097152 floordiv (4*TILE_H*TILE_K + 4*TILE_K*TILE_W))*(4*TILE_K*TILE_W)>], [#C1], i8, #nn.space<tsm>>, !symbol.int<#symbol.expr<2097152 floordiv (4*TILE_H*TILE_K + 4*TILE_K*TILE_W)>>, !symbol.int<#symbol.expr<4*TILE_K*TILE_W>>) -> !dma.ring<!nn.memory<[#S_TILE_K, #S_TILE_W], [#S_TILE_W, #C1], f32, #nn.space<tsm>>>

// pattern0 原 %21 在 tlm1，独立使用 tlm1 capacity。
%tlm1_capacity = symbol.const 524288 : !symbol.int<#symbol.expr<524288>>
%tlm1_lhs_num = symbol.floordiv %tlm1_capacity, %tsm_lhs_slot_bytes : !symbol.int<#symbol.expr<524288>>, !symbol.int<#symbol.expr<4*TILE_H*TILE_K>> -> !symbol.int<#symbol.expr<524288 floordiv (4*TILE_H*TILE_K)>>
%tlm1_lhs_backing_bytes = symbol.mul %tlm1_lhs_num, %tsm_lhs_slot_bytes : !symbol.int<#symbol.expr<524288 floordiv (4*TILE_H*TILE_K)>>, !symbol.int<#symbol.expr<4*TILE_H*TILE_K>> -> !symbol.int<#symbol.expr<(524288 floordiv (4*TILE_H*TILE_K))*(4*TILE_H*TILE_K)>>
%tlm1_lhs_backing = "dma.alloc"(%tlm1_lhs_backing_bytes) <{operandSegmentSizes = array<i32: 1>}> : (!symbol.int<#symbol.expr<(524288 floordiv (4*TILE_H*TILE_K))*(4*TILE_H*TILE_K)>>) -> !nn.memory<[#symbol.expr<(524288 floordiv (4*TILE_H*TILE_K))*(4*TILE_H*TILE_K)>], [#C1], i8, #nn.space<tlm1>>
%tlm1_lhs_ring = "dma.make_ring"(%tlm1_lhs_backing, %tlm1_lhs_num, %tsm_lhs_slot_bytes) : (!nn.memory<[#symbol.expr<(524288 floordiv (4*TILE_H*TILE_K))*(4*TILE_H*TILE_K)>], [#C1], i8, #nn.space<tlm1>>, !symbol.int<#symbol.expr<524288 floordiv (4*TILE_H*TILE_K)>>, !symbol.int<#symbol.expr<4*TILE_H*TILE_K>>) -> !dma.ring<!nn.memory<[#S_TILE_H, #S_TILE_K], [#S_TILE_K, #C1], f32, #nn.space<tlm1>>>

// pattern0 原 %22 在 tlm2，独立使用 tlm2 capacity。
%tlm2_capacity = symbol.const 1048576 : !symbol.int<#symbol.expr<1048576>>
%tlm2_rhs_num = symbol.floordiv %tlm2_capacity, %tsm_rhs_slot_bytes : !symbol.int<#symbol.expr<1048576>>, !symbol.int<#symbol.expr<4*TILE_K*TILE_W>> -> !symbol.int<#symbol.expr<1048576 floordiv (4*TILE_K*TILE_W)>>
%tlm2_rhs_backing_bytes = symbol.mul %tlm2_rhs_num, %tsm_rhs_slot_bytes : !symbol.int<#symbol.expr<1048576 floordiv (4*TILE_K*TILE_W)>>, !symbol.int<#symbol.expr<4*TILE_K*TILE_W>> -> !symbol.int<#symbol.expr<(1048576 floordiv (4*TILE_K*TILE_W))*(4*TILE_K*TILE_W)>>
%tlm2_rhs_backing = "dma.alloc"(%tlm2_rhs_backing_bytes) <{operandSegmentSizes = array<i32: 1>}> : (!symbol.int<#symbol.expr<(1048576 floordiv (4*TILE_K*TILE_W))*(4*TILE_K*TILE_W)>>) -> !nn.memory<[#symbol.expr<(1048576 floordiv (4*TILE_K*TILE_W))*(4*TILE_K*TILE_W)>], [#C1], i8, #nn.space<tlm2>>
%tlm2_rhs_ring = "dma.make_ring"(%tlm2_rhs_backing, %tlm2_rhs_num, %tsm_rhs_slot_bytes) : (!nn.memory<[#symbol.expr<(1048576 floordiv (4*TILE_K*TILE_W))*(4*TILE_K*TILE_W)>], [#C1], i8, #nn.space<tlm2>>, !symbol.int<#symbol.expr<1048576 floordiv (4*TILE_K*TILE_W)>>, !symbol.int<#symbol.expr<4*TILE_K*TILE_W>>) -> !dma.ring<!nn.memory<[#S_TILE_K, #S_TILE_W], [#S_TILE_W, #C1], f32, #nn.space<tlm2>>>
```

- 真实 dynamic pattern0 的 loop 改写预期如下；计算逻辑不变，只把 `dma.reinterpret` 的 source 从原 alloc 换成本轮 current slot，并在本轮最后使用后 advance：

```mlir
symbol.for %34 = %10 to %8 step %6 {iter = #It3} {
  %35 = symbol.sub %8, %34 : !symbol.int<#S_K>, !symbol.iter<start = #C0, end = #S_K, step = #S_TILE_K> -> !symbol.int<#S6>
  %36 = symbol.min %6, %35 : !symbol.int<#S_TILE_K>, !symbol.int<#S6> -> !symbol.int<#S7>

  %tsm_lhs_cur = "dma.current_ring"(%tsm_lhs_ring) : (!dma.ring<!nn.memory<[#S_TILE_H, #S_TILE_K], [#S_TILE_K, #C1], f32, #nn.space<tsm>>>) -> !nn.memory<[#S_TILE_H, #S_TILE_K], [#S_TILE_K, #C1], f32, #nn.space<tsm>>
  %37 = "dma.reinterpret"(%tsm_lhs_cur, %10, %25, %36, %36, %11) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#S_TILE_H, #S_TILE_K], [#S_TILE_K, #C1], f32, #nn.space<tsm>>, !symbol.int<#C0>, !symbol.int<#S2>, !symbol.int<#S7>, !symbol.int<#S7>, !symbol.int<#C1>) -> !nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tsm>>

  %tsm_rhs_cur = "dma.current_ring"(%tsm_rhs_ring) : (!dma.ring<!nn.memory<[#S_TILE_K, #S_TILE_W], [#S_TILE_W, #C1], f32, #nn.space<tsm>>>) -> !nn.memory<[#S_TILE_K, #S_TILE_W], [#S_TILE_W, #C1], f32, #nn.space<tsm>>
  %38 = "dma.reinterpret"(%tsm_rhs_cur, %10, %36, %29, %29, %11) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#S_TILE_K, #S_TILE_W], [#S_TILE_W, #C1], f32, #nn.space<tsm>>, !symbol.int<#C0>, !symbol.int<#S7>, !symbol.int<#S5>, !symbol.int<#S5>, !symbol.int<#C1>) -> !nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tsm>>

  "dma.deslice"(%37, %40, %10, %10, %25, %36, %11, %11) : (!nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tsm>>, !nn.memory<[#S2, #S7], [#S_K, #C1], f32, #nn.space<global>>, !symbol.int<#C0>, !symbol.int<#C0>, !symbol.int<#S2>, !symbol.int<#S7>, !symbol.int<#C1>, !symbol.int<#C1>) -> ()
  "dma.deslice"(%38, %43, %10, %10, %36, %29, %11, %11) : (!nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tsm>>, !nn.memory<[#S7, #S5], [#S_W, #C1], f32, #nn.space<global>>, !symbol.int<#C0>, !symbol.int<#C0>, !symbol.int<#S7>, !symbol.int<#S5>, !symbol.int<#C1>, !symbol.int<#C1>) -> ()

  %tlm1_lhs_cur = "dma.current_ring"(%tlm1_lhs_ring) : (!dma.ring<!nn.memory<[#S_TILE_H, #S_TILE_K], [#S_TILE_K, #C1], f32, #nn.space<tlm1>>>) -> !nn.memory<[#S_TILE_H, #S_TILE_K], [#S_TILE_K, #C1], f32, #nn.space<tlm1>>
  %44 = "dma.reinterpret"(%tlm1_lhs_cur, %10, %25, %36, %36, %11) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#S_TILE_H, #S_TILE_K], [#S_TILE_K, #C1], f32, #nn.space<tlm1>>, !symbol.int<#C0>, !symbol.int<#S2>, !symbol.int<#S7>, !symbol.int<#S7>, !symbol.int<#C1>) -> !nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tlm1>>
  "dma.copy"(%44, %37) : (!nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tlm1>>, !nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tsm>>) -> ()

  %tlm2_rhs_cur = "dma.current_ring"(%tlm2_rhs_ring) : (!dma.ring<!nn.memory<[#S_TILE_K, #S_TILE_W], [#S_TILE_W, #C1], f32, #nn.space<tlm2>>>) -> !nn.memory<[#S_TILE_K, #S_TILE_W], [#S_TILE_W, #C1], f32, #nn.space<tlm2>>
  %45 = "dma.reinterpret"(%tlm2_rhs_cur, %10, %36, %29, %29, %11) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#S_TILE_K, #S_TILE_W], [#S_TILE_W, #C1], f32, #nn.space<tlm2>>, !symbol.int<#C0>, !symbol.int<#S7>, !symbol.int<#S5>, !symbol.int<#S5>, !symbol.int<#C1>) -> !nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tlm2>>
  "dma.copy"(%45, %38) : (!nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tlm2>>, !nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tsm>>) -> ()

  %acc = symbol.ne %34, %10 : !symbol.iter<start = #C0, end = #S_K, step = #S_TILE_K>, !symbol.int<#C0> -> i1
  "kernel.matmul"(%30, %44, %45, %acc) {space = #nn.space<tsm>} : (!nn.memory<[#S2, #S5], [#S5, #C1], f32, #nn.space<tsm>>, !nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tlm1>>, !nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tlm2>>, i1) -> ()

  "dma.advance_ring"(%tsm_lhs_ring) : (!dma.ring<!nn.memory<[#S_TILE_H, #S_TILE_K], [#S_TILE_K, #C1], f32, #nn.space<tsm>>>) -> !nn.memory<[#S_TILE_H, #S_TILE_K], [#S_TILE_K, #C1], f32, #nn.space<tsm>>
  "dma.advance_ring"(%tsm_rhs_ring) : (!dma.ring<!nn.memory<[#S_TILE_K, #S_TILE_W], [#S_TILE_W, #C1], f32, #nn.space<tsm>>>) -> !nn.memory<[#S_TILE_K, #S_TILE_W], [#S_TILE_W, #C1], f32, #nn.space<tsm>>
  "dma.advance_ring"(%tlm1_lhs_ring) : (!dma.ring<!nn.memory<[#S_TILE_H, #S_TILE_K], [#S_TILE_K, #C1], f32, #nn.space<tlm1>>>) -> !nn.memory<[#S_TILE_H, #S_TILE_K], [#S_TILE_K, #C1], f32, #nn.space<tlm1>>
  "dma.advance_ring"(%tlm2_rhs_ring) : (!dma.ring<!nn.memory<[#S_TILE_K, #S_TILE_W], [#S_TILE_W, #C1], f32, #nn.space<tlm2>>>) -> !nn.memory<[#S_TILE_K, #S_TILE_W], [#S_TILE_W, #C1], f32, #nn.space<tlm2>>
}
```

- pattern1 使用同一真实 dynamic dump 的同构规则，区别只在 `%21/%22` 的 local space 互换：
  - pattern1 `%21`: `tlm2` `[TILE_H,TILE_K]`，`num = 1048576 floordiv (4*TILE_H*TILE_K)`。
  - pattern1 `%22`: `tlm1` `[TILE_K,TILE_W]`，`num = 524288 floordiv (4*TILE_K*TILE_W)`。

### canonicalize/fold 后的完整结构预期

- 下方是增强后 `multi-buffer` 经后续 fold 后的结构检查预期，主要用来对照当前 static dump。
- 本预期新增的静态符号：
  - `#C29`: pattern1 `tlm1` rhs ring num。
  - `#C58`: `tlm2` rhs ring num。
  - `#C73`: `tsm` lhs/rhs same-space ring num。
  - `#C97`: pattern1 `tlm2` lhs ring num。
  - `#C10752`: `[48,56] f32` slot bytes。
  - `#C17920`: `[56,80] f32` slot bytes。
  - `#C516096`: pattern0 `tlm1` lhs backing bytes。
  - `#C519680`: pattern1 `tlm1` rhs backing bytes。
  - `#C784896`: `tsm` lhs backing bytes。
  - `#C1039360`: pattern0 `tlm2` rhs backing bytes。
  - `#C1042944`: pattern1 `tlm2` lhs backing bytes。
  - `#C1308160`: `tsm` rhs backing bytes。

```mlir
multi-buffer
#C233 = #symbol.expr<233>
#C195 = #symbol.expr<195>
#C1 = #symbol.expr<1>
#C163 = #symbol.expr<163>
#C0 = #symbol.expr<0>
#C48 = #symbol.expr<48>
#C80 = #symbol.expr<80>
#C56 = #symbol.expr<56>
#C29 = #symbol.expr<29>
#C58 = #symbol.expr<58>
#C73 = #symbol.expr<73>
#C97 = #symbol.expr<97>
#C10752 = #symbol.expr<10752>
#C17920 = #symbol.expr<17920>
#C516096 = #symbol.expr<516096>
#C519680 = #symbol.expr<519680>
#C784896 = #symbol.expr<784896>
#C1039360 = #symbol.expr<1039360>
#C1042944 = #symbol.expr<1042944>
#C1308160 = #symbol.expr<1308160>
#S_pattern_id = #symbol.expr<pattern_id>
#S_Q = #symbol.expr<?>
#S1 = #symbol.expr<233 - iter<0,233,48>>
#S2 = #symbol.expr<min(48, 233 - iter<0,233,48>)>
#S3 = #symbol.expr<163*iter<0,233,48>>
#S4 = #symbol.expr<195 - iter<0,195,80>>
#S5 = #symbol.expr<min(80, 195 - iter<0,195,80>)>
#S6 = #symbol.expr<163 - iter<0,163,56>>
#S7 = #symbol.expr<min(56, 163 - iter<0,163,56>)>
#S8 = #symbol.expr<163*iter<0,233,48> + iter<0,163,56>>
#S9 = #symbol.expr<195*iter<0,163,56>>
#S10 = #symbol.expr<195*iter<0,163,56> + iter<0,195,80>>
#It1 = #symbol.iter<start = #C0, end = #C233, step = #C48>
#It2 = #symbol.iter<start = #C0, end = #C195, step = #C80>
#It3 = #symbol.iter<start = #C0, end = #C163, step = #C56>

builtin.module {
  func.func @matmul_inputs_static_tile_static_kernel(%0: !nn.memory<[#C233, #C195], [#C195, #C1], f32, #nn.space<global>>, %1: !nn.memory<[#C233, #C163], [#C163, #C1], f32, #nn.space<global>>, %2: !nn.memory<[#C163, #C195], [#C195, #C1], f32, #nn.space<global>>, %3: !nn.memory<[#C195], [#C1], f32, #nn.space<global>>) attributes {entry_point} {
    %4 = tuner.select {patterns = [@matmul_inputs_static_tile_static_kernel_pattern0, @matmul_inputs_static_tile_static_kernel_pattern1]} : !symbol.int<#S_pattern_id>
    %5 = "symbol.const"() {value = #builtin.int<0>} : () -> !symbol.int<#C0>
    %6 = "symbol.eq"(%4, %5) : (!symbol.int<#S_pattern_id>, !symbol.int<#C0>) -> i1
    scf.if %6 {
      tuner.launch(@matmul_inputs_static_tile_static_kernel_pattern0, %0, %1, %2, %3) : (!nn.memory<[#C233, #C195], [#C195, #C1], f32, #nn.space<global>>, !nn.memory<[#C233, #C163], [#C163, #C1], f32, #nn.space<global>>, !nn.memory<[#C163, #C195], [#C195, #C1], f32, #nn.space<global>>, !nn.memory<[#C195], [#C1], f32, #nn.space<global>>) -> ()
    } else {
      tuner.launch(@matmul_inputs_static_tile_static_kernel_pattern1, %0, %1, %2, %3) : (!nn.memory<[#C233, #C195], [#C195, #C1], f32, #nn.space<global>>, !nn.memory<[#C233, #C163], [#C163, #C1], f32, #nn.space<global>>, !nn.memory<[#C163, #C195], [#C195, #C1], f32, #nn.space<global>>, !nn.memory<[#C195], [#C1], f32, #nn.space<global>>) -> ()
    }
    func.return
  }

  func.func @matmul_inputs_static_tile_static_kernel_pattern0(%0: !nn.memory<[#C233, #C195], [#C195, #C1], f32, #nn.space<global>>, %1: !nn.memory<[#C233, #C163], [#C163, #C1], f32, #nn.space<global>>, %2: !nn.memory<[#C163, #C195], [#C195, #C1], f32, #nn.space<global>>, %3: !nn.memory<[#C195], [#C1], f32, #nn.space<global>>) attributes {kernel.pattern_id = #builtin.int<0>} {
    %4 = symbol.const 233 : !symbol.int<#C233>
    %5 = symbol.const 163 : !symbol.int<#C163>
    %6 = symbol.const 195 : !symbol.int<#C195>
    %7 = symbol.const 0 : !symbol.int<#C0>
    %8 = symbol.const 48 : !symbol.int<#C48>
    %9 = symbol.const 80 : !symbol.int<#C80>
    %10 = symbol.const 1 : !symbol.int<#C1>
    %11 = "dma.alloc"(%8, %9) <{operandSegmentSizes = array<i32: 2>}> : (!symbol.int<#C48>, !symbol.int<#C80>) -> !nn.memory<[#C48, #C80], [#C80, #C1], f32, #nn.space<tsm>>
    %12 = "dma.alloc"(%9) <{operandSegmentSizes = array<i32: 1>}> : (!symbol.int<#C80>) -> !nn.memory<[#C80], [#C1], f32, #nn.space<tsm>>
    %13 = "dma.alloc"(%8, %9) <{operandSegmentSizes = array<i32: 2>}> : (!symbol.int<#C48>, !symbol.int<#C80>) -> !nn.memory<[#C48, #C80], [#C80, #C1], f32, #nn.space<tsm>>
    %14 = symbol.const 56 : !symbol.int<#C56>
    %17 = memory.get_data %3 : !nn.memory<[#C195], [#C1], f32, #nn.space<global>> -> !symbol.ptr<f32>
    %18 = symbol.cast %17 : !symbol.ptr<f32> -> !symbol.int<#S_Q>
    %19 = symbol.ne %18, %7 : !symbol.int<#S_Q>, !symbol.int<#C0> -> i1

    %tsm_lhs_backing = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#C784896], [#C1], i8, #nn.space<tsm>>
    %tsm_lhs_num = symbol.const 73 : !symbol.int<#C73>
    %tsm_lhs_offset = symbol.const 10752 : !symbol.int<#C10752>
    %tsm_lhs_ring = "dma.make_ring"(%tsm_lhs_backing, %tsm_lhs_num, %tsm_lhs_offset) : (!nn.memory<[#C784896], [#C1], i8, #nn.space<tsm>>, !symbol.int<#C73>, !symbol.int<#C10752>) -> !dma.ring<!nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tsm>>>
    %tsm_rhs_backing = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#C1308160], [#C1], i8, #nn.space<tsm>>
    %tsm_rhs_num = symbol.const 73 : !symbol.int<#C73>
    %tsm_rhs_offset = symbol.const 17920 : !symbol.int<#C17920>
    %tsm_rhs_ring = "dma.make_ring"(%tsm_rhs_backing, %tsm_rhs_num, %tsm_rhs_offset) : (!nn.memory<[#C1308160], [#C1], i8, #nn.space<tsm>>, !symbol.int<#C73>, !symbol.int<#C17920>) -> !dma.ring<!nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tsm>>>
    %tlm1_lhs_backing = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#C516096], [#C1], i8, #nn.space<tlm1>>
    %tlm1_lhs_num = symbol.const 48 : !symbol.int<#C48>
    %tlm1_lhs_offset = symbol.const 10752 : !symbol.int<#C10752>
    %tlm1_lhs_ring = "dma.make_ring"(%tlm1_lhs_backing, %tlm1_lhs_num, %tlm1_lhs_offset) : (!nn.memory<[#C516096], [#C1], i8, #nn.space<tlm1>>, !symbol.int<#C48>, !symbol.int<#C10752>) -> !dma.ring<!nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tlm1>>>
    %tlm2_rhs_backing = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#C1039360], [#C1], i8, #nn.space<tlm2>>
    %tlm2_rhs_num = symbol.const 58 : !symbol.int<#C58>
    %tlm2_rhs_offset = symbol.const 17920 : !symbol.int<#C17920>
    %tlm2_rhs_ring = "dma.make_ring"(%tlm2_rhs_backing, %tlm2_rhs_num, %tlm2_rhs_offset) : (!nn.memory<[#C1039360], [#C1], i8, #nn.space<tlm2>>, !symbol.int<#C58>, !symbol.int<#C17920>) -> !dma.ring<!nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tlm2>>>

    symbol.for %22 = %7 to %4 step %8 {iter = #It1} {
      %23 = symbol.sub %4, %22 : !symbol.int<#C233>, !symbol.iter<start = #C0, end = #C233, step = #C48> -> !symbol.int<#S1>
      %24 = symbol.min %8, %23 : !symbol.int<#C48>, !symbol.int<#S1> -> !symbol.int<#S2>
      %25 = symbol.mul %22, %5 : !symbol.iter<start = #C0, end = #C233, step = #C48>, !symbol.int<#C163> -> !symbol.int<#S3>
      symbol.for %26 = %7 to %6 step %9 {iter = #It2} {
        %27 = symbol.sub %6, %26 : !symbol.int<#C195>, !symbol.iter<start = #C0, end = #C195, step = #C80> -> !symbol.int<#S4>
        %28 = symbol.min %9, %27 : !symbol.int<#C80>, !symbol.int<#S4> -> !symbol.int<#S5>
        %29 = "dma.reinterpret"(%11, %7, %24, %28, %28, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C48, #C80], [#C80, #C1], f32, #nn.space<tsm>>, !symbol.int<#C0>, !symbol.int<#S2>, !symbol.int<#S5>, !symbol.int<#S5>, !symbol.int<#C1>) -> !nn.memory<[#S2, #S5], [#S5, #C1], f32, #nn.space<tsm>>
        %30 = "dma.reinterpret"(%12, %7, %28, %10) <{operandSegmentSizes = array<i32: 1, 1, 1, 1>}> : (!nn.memory<[#C80], [#C1], f32, #nn.space<tsm>>, !symbol.int<#C0>, !symbol.int<#S5>, !symbol.int<#C1>) -> !nn.memory<[#S5], [#C1], f32, #nn.space<tsm>>
        %31 = "dma.reinterpret"(%13, %7, %24, %28, %28, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C48, #C80], [#C80, #C1], f32, #nn.space<tsm>>, !symbol.int<#C0>, !symbol.int<#S2>, !symbol.int<#S5>, !symbol.int<#S5>, !symbol.int<#C1>) -> !nn.memory<[#S2, #S5], [#S5, #C1], f32, #nn.space<tsm>>
        symbol.for %32 = %7 to %5 step %14 {iter = #It3} {
          %33 = symbol.sub %5, %32 : !symbol.int<#C163>, !symbol.iter<start = #C0, end = #C163, step = #C56> -> !symbol.int<#S6>
          %34 = symbol.min %14, %33 : !symbol.int<#C56>, !symbol.int<#S6> -> !symbol.int<#S7>
          %tsm_lhs_cur = "dma.current_ring"(%tsm_lhs_ring) : (!dma.ring<!nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tsm>>>) -> !nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tsm>>
          %35 = "dma.reinterpret"(%tsm_lhs_cur, %7, %24, %34, %34, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tsm>>, !symbol.int<#C0>, !symbol.int<#S2>, !symbol.int<#S7>, !symbol.int<#S7>, !symbol.int<#C1>) -> !nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tsm>>
          %tsm_rhs_cur = "dma.current_ring"(%tsm_rhs_ring) : (!dma.ring<!nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tsm>>>) -> !nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tsm>>
          %36 = "dma.reinterpret"(%tsm_rhs_cur, %7, %34, %28, %28, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tsm>>, !symbol.int<#C0>, !symbol.int<#S7>, !symbol.int<#S5>, !symbol.int<#S5>, !symbol.int<#C1>) -> !nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tsm>>
          %37 = symbol.add %25, %32 : !symbol.int<#S3>, !symbol.iter<start = #C0, end = #C163, step = #C56> -> !symbol.int<#S8>
          %38 = "dma.reinterpret"(%1, %37, %24, %34, %5, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C233, #C163], [#C163, #C1], f32, #nn.space<global>>, !symbol.int<#S8>, !symbol.int<#S2>, !symbol.int<#S7>, !symbol.int<#C163>, !symbol.int<#C1>) -> !nn.memory<[#S2, #S7], [#C163, #C1], f32, #nn.space<global>>
          %39 = symbol.mul %32, %6 : !symbol.iter<start = #C0, end = #C163, step = #C56>, !symbol.int<#C195> -> !symbol.int<#S9>
          %40 = symbol.add %39, %26 : !symbol.int<#S9>, !symbol.iter<start = #C0, end = #C195, step = #C80> -> !symbol.int<#S10>
          %41 = "dma.reinterpret"(%2, %40, %34, %28, %6, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C163, #C195], [#C195, #C1], f32, #nn.space<global>>, !symbol.int<#S10>, !symbol.int<#S7>, !symbol.int<#S5>, !symbol.int<#C195>, !symbol.int<#C1>) -> !nn.memory<[#S7, #S5], [#C195, #C1], f32, #nn.space<global>>
          "dma.deslice"(%35, %38, %7, %7, %24, %34, %10, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2, 2>}> : (!nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tsm>>, !nn.memory<[#S2, #S7], [#C163, #C1], f32, #nn.space<global>>, !symbol.int<#C0>, !symbol.int<#C0>, !symbol.int<#S2>, !symbol.int<#S7>, !symbol.int<#C1>, !symbol.int<#C1>) -> ()
          "dma.deslice"(%36, %41, %7, %7, %34, %28, %10, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2, 2>}> : (!nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tsm>>, !nn.memory<[#S7, #S5], [#C195, #C1], f32, #nn.space<global>>, !symbol.int<#C0>, !symbol.int<#C0>, !symbol.int<#S7>, !symbol.int<#S5>, !symbol.int<#C1>, !symbol.int<#C1>) -> ()
          %tlm1_lhs_cur = "dma.current_ring"(%tlm1_lhs_ring) : (!dma.ring<!nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tlm1>>>) -> !nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tlm1>>
          %42 = "dma.reinterpret"(%tlm1_lhs_cur, %7, %24, %34, %34, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tlm1>>, !symbol.int<#C0>, !symbol.int<#S2>, !symbol.int<#S7>, !symbol.int<#S7>, !symbol.int<#C1>) -> !nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tlm1>>
          "dma.copy"(%42, %35) : (!nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tlm1>>, !nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tsm>>) -> ()
          %tlm2_rhs_cur = "dma.current_ring"(%tlm2_rhs_ring) : (!dma.ring<!nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tlm2>>>) -> !nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tlm2>>
          %43 = "dma.reinterpret"(%tlm2_rhs_cur, %7, %34, %28, %28, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tlm2>>, !symbol.int<#C0>, !symbol.int<#S7>, !symbol.int<#S5>, !symbol.int<#S5>, !symbol.int<#C1>) -> !nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tlm2>>
          "dma.copy"(%43, %36) : (!nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tlm2>>, !nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tsm>>) -> ()
          %acc = symbol.ne %32, %7 : !symbol.iter<start = #C0, end = #C163, step = #C56>, !symbol.int<#C0> -> i1
          "kernel.matmul"(%29, %42, %43, %acc) {space = #nn.space<tsm>} : (!nn.memory<[#S2, #S5], [#S5, #C1], f32, #nn.space<tsm>>, !nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tlm1>>, !nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tlm2>>, i1) -> ()
          "dma.advance_ring"(%tsm_lhs_ring) : (!dma.ring<!nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tsm>>>) -> !nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tsm>>
          "dma.advance_ring"(%tsm_rhs_ring) : (!dma.ring<!nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tsm>>>) -> !nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tsm>>
          "dma.advance_ring"(%tlm1_lhs_ring) : (!dma.ring<!nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tlm1>>>) -> !nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tlm1>>
          "dma.advance_ring"(%tlm2_rhs_ring) : (!dma.ring<!nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tlm2>>>) -> !nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tlm2>>
        }
        scf.if %19 {
          %44 = "dma.reinterpret"(%3, %26, %28, %10) <{operandSegmentSizes = array<i32: 1, 1, 1, 1>}> : (!nn.memory<[#C195], [#C1], f32, #nn.space<global>>, !symbol.iter<start = #C0, end = #C195, step = #C80>, !symbol.int<#S5>, !symbol.int<#C1>) -> !nn.memory<[#S5], [#C1], f32, #nn.space<global>>
          %45 = "dma.reinterpret"(%12, %7, %10, %28, %28, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C80], [#C1], f32, #nn.space<tsm>>, !symbol.int<#C0>, !symbol.int<#C1>, !symbol.int<#S5>, !symbol.int<#S5>, !symbol.int<#C1>) -> !nn.memory<[#C1, #S5], [#S5, #C1], f32, #nn.space<tsm>>
          "dma.deslice"(%30, %44, %7, %28, %10) <{operandSegmentSizes = array<i32: 1, 1, 1, 1, 1>}> : (!nn.memory<[#S5], [#C1], f32, #nn.space<tsm>>, !nn.memory<[#S5], [#C1], f32, #nn.space<global>>, !symbol.int<#C0>, !symbol.int<#S5>, !symbol.int<#C1>) -> ()
          "dma.broadcast"(%31, %45) {tile.analysis = [["elewise", "elewise"], ["expand", "elewise"]], tile.tile_exprs = [["", ""], ["", ""]]} : (!nn.memory<[#S2, #S5], [#S5, #C1], f32, #nn.space<tsm>>, !nn.memory<[#C1, #S5], [#S5, #C1], f32, #nn.space<tsm>>) -> ()
          "kernel.binary_elewise"(%29, %29, %31) {kind = "add", space = #nn.space<tsm>, tile.analysis = [["elewise", "elewise"], ["elewise", "elewise"], ["elewise", "elewise"]], tile.tile_exprs = [["", ""], ["", ""], ["", ""]]} : (!nn.memory<[#S2, #S5], [#S5, #C1], f32, #nn.space<tsm>>, !nn.memory<[#S2, #S5], [#S5, #C1], f32, #nn.space<tsm>>, !nn.memory<[#S2, #S5], [#S5, #C1], f32, #nn.space<tsm>>) -> ()
        }
        "dma.deslice"(%0, %29, %22, %26, %24, %28, %10, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2, 2>}> : (!nn.memory<[#C233, #C195], [#C195, #C1], f32, #nn.space<global>>, !nn.memory<[#S2, #S5], [#S5, #C1], f32, #nn.space<tsm>>, !symbol.iter<start = #C0, end = #C233, step = #C48>, !symbol.iter<start = #C0, end = #C195, step = #C80>, !symbol.int<#S2>, !symbol.int<#S5>, !symbol.int<#C1>, !symbol.int<#C1>) -> ()
      }
    }
    "dma.free"(%tlm2_rhs_backing) : (!nn.memory<[#C1039360], [#C1], i8, #nn.space<tlm2>>) -> ()
    "dma.free"(%tlm1_lhs_backing) : (!nn.memory<[#C516096], [#C1], i8, #nn.space<tlm1>>) -> ()
    "dma.free"(%tsm_rhs_backing) : (!nn.memory<[#C1308160], [#C1], i8, #nn.space<tsm>>) -> ()
    "dma.free"(%tsm_lhs_backing) : (!nn.memory<[#C784896], [#C1], i8, #nn.space<tsm>>) -> ()
    "dma.free"(%13) : (!nn.memory<[#C48, #C80], [#C80, #C1], f32, #nn.space<tsm>>) -> ()
    "dma.free"(%12) : (!nn.memory<[#C80], [#C1], f32, #nn.space<tsm>>) -> ()
    "dma.free"(%11) : (!nn.memory<[#C48, #C80], [#C80, #C1], f32, #nn.space<tsm>>) -> ()
    func.return
  }

  func.func @matmul_inputs_static_tile_static_kernel_pattern1(%0: !nn.memory<[#C233, #C195], [#C195, #C1], f32, #nn.space<global>>, %1: !nn.memory<[#C233, #C163], [#C163, #C1], f32, #nn.space<global>>, %2: !nn.memory<[#C163, #C195], [#C195, #C1], f32, #nn.space<global>>, %3: !nn.memory<[#C195], [#C1], f32, #nn.space<global>>) attributes {kernel.pattern_id = #builtin.int<1>} {
    %4 = symbol.const 233 : !symbol.int<#C233>
    %5 = symbol.const 163 : !symbol.int<#C163>
    %6 = symbol.const 195 : !symbol.int<#C195>
    %7 = symbol.const 0 : !symbol.int<#C0>
    %8 = symbol.const 48 : !symbol.int<#C48>
    %9 = symbol.const 80 : !symbol.int<#C80>
    %10 = symbol.const 1 : !symbol.int<#C1>
    %11 = "dma.alloc"(%8, %9) <{operandSegmentSizes = array<i32: 2>}> : (!symbol.int<#C48>, !symbol.int<#C80>) -> !nn.memory<[#C48, #C80], [#C80, #C1], f32, #nn.space<tsm>>
    %12 = "dma.alloc"(%9) <{operandSegmentSizes = array<i32: 1>}> : (!symbol.int<#C80>) -> !nn.memory<[#C80], [#C1], f32, #nn.space<tsm>>
    %13 = "dma.alloc"(%8, %9) <{operandSegmentSizes = array<i32: 2>}> : (!symbol.int<#C48>, !symbol.int<#C80>) -> !nn.memory<[#C48, #C80], [#C80, #C1], f32, #nn.space<tsm>>
    %14 = symbol.const 56 : !symbol.int<#C56>
    %17 = memory.get_data %3 : !nn.memory<[#C195], [#C1], f32, #nn.space<global>> -> !symbol.ptr<f32>
    %18 = symbol.cast %17 : !symbol.ptr<f32> -> !symbol.int<#S_Q>
    %19 = symbol.ne %18, %7 : !symbol.int<#S_Q>, !symbol.int<#C0> -> i1

    %tsm_lhs_backing = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#C784896], [#C1], i8, #nn.space<tsm>>
    %tsm_lhs_num = symbol.const 73 : !symbol.int<#C73>
    %tsm_lhs_offset = symbol.const 10752 : !symbol.int<#C10752>
    %tsm_lhs_ring = "dma.make_ring"(%tsm_lhs_backing, %tsm_lhs_num, %tsm_lhs_offset) : (!nn.memory<[#C784896], [#C1], i8, #nn.space<tsm>>, !symbol.int<#C73>, !symbol.int<#C10752>) -> !dma.ring<!nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tsm>>>
    %tsm_rhs_backing = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#C1308160], [#C1], i8, #nn.space<tsm>>
    %tsm_rhs_num = symbol.const 73 : !symbol.int<#C73>
    %tsm_rhs_offset = symbol.const 17920 : !symbol.int<#C17920>
    %tsm_rhs_ring = "dma.make_ring"(%tsm_rhs_backing, %tsm_rhs_num, %tsm_rhs_offset) : (!nn.memory<[#C1308160], [#C1], i8, #nn.space<tsm>>, !symbol.int<#C73>, !symbol.int<#C17920>) -> !dma.ring<!nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tsm>>>
    %tlm2_lhs_backing = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#C1042944], [#C1], i8, #nn.space<tlm2>>
    %tlm2_lhs_num = symbol.const 97 : !symbol.int<#C97>
    %tlm2_lhs_offset = symbol.const 10752 : !symbol.int<#C10752>
    %tlm2_lhs_ring = "dma.make_ring"(%tlm2_lhs_backing, %tlm2_lhs_num, %tlm2_lhs_offset) : (!nn.memory<[#C1042944], [#C1], i8, #nn.space<tlm2>>, !symbol.int<#C97>, !symbol.int<#C10752>) -> !dma.ring<!nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tlm2>>>
    %tlm1_rhs_backing = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[#C519680], [#C1], i8, #nn.space<tlm1>>
    %tlm1_rhs_num = symbol.const 29 : !symbol.int<#C29>
    %tlm1_rhs_offset = symbol.const 17920 : !symbol.int<#C17920>
    %tlm1_rhs_ring = "dma.make_ring"(%tlm1_rhs_backing, %tlm1_rhs_num, %tlm1_rhs_offset) : (!nn.memory<[#C519680], [#C1], i8, #nn.space<tlm1>>, !symbol.int<#C29>, !symbol.int<#C17920>) -> !dma.ring<!nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tlm1>>>

    symbol.for %22 = %7 to %4 step %8 {iter = #It1} {
      %23 = symbol.sub %4, %22 : !symbol.int<#C233>, !symbol.iter<start = #C0, end = #C233, step = #C48> -> !symbol.int<#S1>
      %24 = symbol.min %8, %23 : !symbol.int<#C48>, !symbol.int<#S1> -> !symbol.int<#S2>
      %25 = symbol.mul %22, %5 : !symbol.iter<start = #C0, end = #C233, step = #C48>, !symbol.int<#C163> -> !symbol.int<#S3>
      symbol.for %26 = %7 to %6 step %9 {iter = #It2} {
        %27 = symbol.sub %6, %26 : !symbol.int<#C195>, !symbol.iter<start = #C0, end = #C195, step = #C80> -> !symbol.int<#S4>
        %28 = symbol.min %9, %27 : !symbol.int<#C80>, !symbol.int<#S4> -> !symbol.int<#S5>
        %29 = "dma.reinterpret"(%11, %7, %24, %28, %28, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C48, #C80], [#C80, #C1], f32, #nn.space<tsm>>, !symbol.int<#C0>, !symbol.int<#S2>, !symbol.int<#S5>, !symbol.int<#S5>, !symbol.int<#C1>) -> !nn.memory<[#S2, #S5], [#S5, #C1], f32, #nn.space<tsm>>
        %30 = "dma.reinterpret"(%12, %7, %28, %10) <{operandSegmentSizes = array<i32: 1, 1, 1, 1>}> : (!nn.memory<[#C80], [#C1], f32, #nn.space<tsm>>, !symbol.int<#C0>, !symbol.int<#S5>, !symbol.int<#C1>) -> !nn.memory<[#S5], [#C1], f32, #nn.space<tsm>>
        %31 = "dma.reinterpret"(%13, %7, %24, %28, %28, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C48, #C80], [#C80, #C1], f32, #nn.space<tsm>>, !symbol.int<#C0>, !symbol.int<#S2>, !symbol.int<#S5>, !symbol.int<#S5>, !symbol.int<#C1>) -> !nn.memory<[#S2, #S5], [#S5, #C1], f32, #nn.space<tsm>>
        symbol.for %32 = %7 to %5 step %14 {iter = #It3} {
          %33 = symbol.sub %5, %32 : !symbol.int<#C163>, !symbol.iter<start = #C0, end = #C163, step = #C56> -> !symbol.int<#S6>
          %34 = symbol.min %14, %33 : !symbol.int<#C56>, !symbol.int<#S6> -> !symbol.int<#S7>
          %tsm_lhs_cur = "dma.current_ring"(%tsm_lhs_ring) : (!dma.ring<!nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tsm>>>) -> !nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tsm>>
          %35 = "dma.reinterpret"(%tsm_lhs_cur, %7, %24, %34, %34, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tsm>>, !symbol.int<#C0>, !symbol.int<#S2>, !symbol.int<#S7>, !symbol.int<#S7>, !symbol.int<#C1>) -> !nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tsm>>
          %tsm_rhs_cur = "dma.current_ring"(%tsm_rhs_ring) : (!dma.ring<!nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tsm>>>) -> !nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tsm>>
          %36 = "dma.reinterpret"(%tsm_rhs_cur, %7, %34, %28, %28, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tsm>>, !symbol.int<#C0>, !symbol.int<#S7>, !symbol.int<#S5>, !symbol.int<#S5>, !symbol.int<#C1>) -> !nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tsm>>
          %37 = symbol.add %25, %32 : !symbol.int<#S3>, !symbol.iter<start = #C0, end = #C163, step = #C56> -> !symbol.int<#S8>
          %38 = "dma.reinterpret"(%1, %37, %24, %34, %5, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C233, #C163], [#C163, #C1], f32, #nn.space<global>>, !symbol.int<#S8>, !symbol.int<#S2>, !symbol.int<#S7>, !symbol.int<#C163>, !symbol.int<#C1>) -> !nn.memory<[#S2, #S7], [#C163, #C1], f32, #nn.space<global>>
          %39 = symbol.mul %32, %6 : !symbol.iter<start = #C0, end = #C163, step = #C56>, !symbol.int<#C195> -> !symbol.int<#S9>
          %40 = symbol.add %39, %26 : !symbol.int<#S9>, !symbol.iter<start = #C0, end = #C195, step = #C80> -> !symbol.int<#S10>
          %41 = "dma.reinterpret"(%2, %40, %34, %28, %6, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C163, #C195], [#C195, #C1], f32, #nn.space<global>>, !symbol.int<#S10>, !symbol.int<#S7>, !symbol.int<#S5>, !symbol.int<#C195>, !symbol.int<#C1>) -> !nn.memory<[#S7, #S5], [#C195, #C1], f32, #nn.space<global>>
          "dma.deslice"(%35, %38, %7, %7, %24, %34, %10, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2, 2>}> : (!nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tsm>>, !nn.memory<[#S2, #S7], [#C163, #C1], f32, #nn.space<global>>, !symbol.int<#C0>, !symbol.int<#C0>, !symbol.int<#S2>, !symbol.int<#S7>, !symbol.int<#C1>, !symbol.int<#C1>) -> ()
          "dma.deslice"(%36, %41, %7, %7, %34, %28, %10, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2, 2>}> : (!nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tsm>>, !nn.memory<[#S7, #S5], [#C195, #C1], f32, #nn.space<global>>, !symbol.int<#C0>, !symbol.int<#C0>, !symbol.int<#S7>, !symbol.int<#S5>, !symbol.int<#C1>, !symbol.int<#C1>) -> ()
          %tlm2_lhs_cur = "dma.current_ring"(%tlm2_lhs_ring) : (!dma.ring<!nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tlm2>>>) -> !nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tlm2>>
          %42 = "dma.reinterpret"(%tlm2_lhs_cur, %7, %24, %34, %34, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tlm2>>, !symbol.int<#C0>, !symbol.int<#S2>, !symbol.int<#S7>, !symbol.int<#S7>, !symbol.int<#C1>) -> !nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tlm2>>
          "dma.copy"(%42, %35) : (!nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tlm2>>, !nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tsm>>) -> ()
          %tlm1_rhs_cur = "dma.current_ring"(%tlm1_rhs_ring) : (!dma.ring<!nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tlm1>>>) -> !nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tlm1>>
          %43 = "dma.reinterpret"(%tlm1_rhs_cur, %7, %34, %28, %28, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tlm1>>, !symbol.int<#C0>, !symbol.int<#S7>, !symbol.int<#S5>, !symbol.int<#S5>, !symbol.int<#C1>) -> !nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tlm1>>
          "dma.copy"(%43, %36) : (!nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tlm1>>, !nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tsm>>) -> ()
          %acc = symbol.ne %32, %7 : !symbol.iter<start = #C0, end = #C163, step = #C56>, !symbol.int<#C0> -> i1
          "kernel.matmul"(%29, %42, %43, %acc) {space = #nn.space<tsm>} : (!nn.memory<[#S2, #S5], [#S5, #C1], f32, #nn.space<tsm>>, !nn.memory<[#S2, #S7], [#S7, #C1], f32, #nn.space<tlm2>>, !nn.memory<[#S7, #S5], [#S5, #C1], f32, #nn.space<tlm1>>, i1) -> ()
          "dma.advance_ring"(%tsm_lhs_ring) : (!dma.ring<!nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tsm>>>) -> !nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tsm>>
          "dma.advance_ring"(%tsm_rhs_ring) : (!dma.ring<!nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tsm>>>) -> !nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tsm>>
          "dma.advance_ring"(%tlm2_lhs_ring) : (!dma.ring<!nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tlm2>>>) -> !nn.memory<[#C48, #C56], [#C56, #C1], f32, #nn.space<tlm2>>
          "dma.advance_ring"(%tlm1_rhs_ring) : (!dma.ring<!nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tlm1>>>) -> !nn.memory<[#C56, #C80], [#C80, #C1], f32, #nn.space<tlm1>>
        }
        scf.if %19 {
          %44 = "dma.reinterpret"(%3, %26, %28, %10) <{operandSegmentSizes = array<i32: 1, 1, 1, 1>}> : (!nn.memory<[#C195], [#C1], f32, #nn.space<global>>, !symbol.iter<start = #C0, end = #C195, step = #C80>, !symbol.int<#S5>, !symbol.int<#C1>) -> !nn.memory<[#S5], [#C1], f32, #nn.space<global>>
          %45 = "dma.reinterpret"(%12, %7, %10, %28, %28, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (!nn.memory<[#C80], [#C1], f32, #nn.space<tsm>>, !symbol.int<#C0>, !symbol.int<#C1>, !symbol.int<#S5>, !symbol.int<#S5>, !symbol.int<#C1>) -> !nn.memory<[#C1, #S5], [#S5, #C1], f32, #nn.space<tsm>>
          "dma.deslice"(%30, %44, %7, %28, %10) <{operandSegmentSizes = array<i32: 1, 1, 1, 1, 1>}> : (!nn.memory<[#S5], [#C1], f32, #nn.space<tsm>>, !nn.memory<[#S5], [#C1], f32, #nn.space<global>>, !symbol.int<#C0>, !symbol.int<#S5>, !symbol.int<#C1>) -> ()
          "dma.broadcast"(%31, %45) {tile.analysis = [["elewise", "elewise"], ["expand", "elewise"]], tile.tile_exprs = [["", ""], ["", ""]]} : (!nn.memory<[#S2, #S5], [#S5, #C1], f32, #nn.space<tsm>>, !nn.memory<[#C1, #S5], [#S5, #C1], f32, #nn.space<tsm>>) -> ()
          "kernel.binary_elewise"(%29, %29, %31) {kind = "add", space = #nn.space<tsm>, tile.analysis = [["elewise", "elewise"], ["elewise", "elewise"], ["elewise", "elewise"]], tile.tile_exprs = [["", ""], ["", ""], ["", ""]]} : (!nn.memory<[#S2, #S5], [#S5, #C1], f32, #nn.space<tsm>>, !nn.memory<[#S2, #S5], [#S5, #C1], f32, #nn.space<tsm>>, !nn.memory<[#S2, #S5], [#S5, #C1], f32, #nn.space<tsm>>) -> ()
        }
        "dma.deslice"(%0, %29, %22, %26, %24, %28, %10, %10) <{operandSegmentSizes = array<i32: 1, 1, 2, 2, 2>}> : (!nn.memory<[#C233, #C195], [#C195, #C1], f32, #nn.space<global>>, !nn.memory<[#S2, #S5], [#S5, #C1], f32, #nn.space<tsm>>, !symbol.iter<start = #C0, end = #C233, step = #C48>, !symbol.iter<start = #C0, end = #C195, step = #C80>, !symbol.int<#S2>, !symbol.int<#S5>, !symbol.int<#C1>, !symbol.int<#C1>) -> ()
      }
    }
    "dma.free"(%tlm1_rhs_backing) : (!nn.memory<[#C519680], [#C1], i8, #nn.space<tlm1>>) -> ()
    "dma.free"(%tlm2_lhs_backing) : (!nn.memory<[#C1042944], [#C1], i8, #nn.space<tlm2>>) -> ()
    "dma.free"(%tsm_rhs_backing) : (!nn.memory<[#C1308160], [#C1], i8, #nn.space<tsm>>) -> ()
    "dma.free"(%tsm_lhs_backing) : (!nn.memory<[#C784896], [#C1], i8, #nn.space<tsm>>) -> ()
    "dma.free"(%13) : (!nn.memory<[#C48, #C80], [#C80, #C1], f32, #nn.space<tsm>>) -> ()
    "dma.free"(%12) : (!nn.memory<[#C80], [#C1], f32, #nn.space<tsm>>) -> ()
    "dma.free"(%11) : (!nn.memory<[#C48, #C80], [#C80, #C1], f32, #nn.space<tsm>>) -> ()
    func.return
  }
}
```

## IR 预期：`conv2d`

- 当前 conv2d 三条 demo 在 memory-plan auto-pad 解析处失败，尚无真实 `24-multi-buffer.mlir`；本节以已生成的真实 `06-lower-nn.mlir` 结构定义完成态。
- `06-lower-nn.mlir` 只用于识别 conv2d 的语义角色和 producer/consumer 关系；实际 `MultiBufferPass` 仍在 memory-plan / symbol-hoist / canonicalize 后的 `23-canonicalize.mlir -> 24-multi-buffer.mlir` 上执行，候选必须以执行时 IR 中已可证明的 alloc / free / loop 位置为准。
- 真实基线路径：
  - `kernel/dump/conv2d/inputs_static_tile_static_present_bias/conv2d_inputs_static_tile_static_kernel/06-lower-nn.mlir`
  - `kernel/dump/conv2d/inputs_static_tile_dynamic/06-lower-nn.mlir`
  - `kernel/dump/conv2d/inputs_dynamic_tile_dynamic/06-lower-nn.mlir`
- 完成后必须新增 / 写出对应 `24-multi-buffer.mlir`：
  - `kernel/dump/conv2d/inputs_static_tile_static_absent_bias/conv2d_inputs_static_tile_static_kernel/24-multi-buffer.mlir`
  - `kernel/dump/conv2d/inputs_static_tile_static_present_bias/conv2d_inputs_static_tile_static_kernel/24-multi-buffer.mlir`
  - `kernel/dump/conv2d/inputs_static_tile_dynamic/24-multi-buffer.mlir`
  - `kernel/dump/conv2d/inputs_dynamic_tile_dynamic/24-multi-buffer.mlir`
- conv2d 预期 ring 化按 role 判断，不按 SSA 编号硬编码：
  - per-reduce input slice：`dma.alloc` -> `dma.slice` -> `kernel.img2col2d` input。
  - per-reduce weight slice：`dma.alloc` -> `dma.slice` -> `dma.reshape` -> `kernel.matmul` lhs。
  - per-reduce img2col col：`dma.alloc` -> `kernel.img2col2d` -> `dma.reshape` -> `kernel.matmul` rhs。
  - per-reduce matmul output / transpose / partial scratch：`dma.alloc` -> `kernel.matmul` / `dma.reshape` / `dma.transpose` / `dma.deslice` / `kernel.binary_elewise`。
- 这些 per-reduce staging / scratch 候选的 target loop 是 C-channel reduce loop：

```mlir
symbol.for ... {          // outer output tile loops: f0/n0/ho0/wo0/ni
  %acc = "dma.alloc"(...)
  "dma.fill"(%acc, %zero)
  symbol.for ... {        // C reduce loop
    %cur = "dma.current_ring"(%ring)
    %tile = "dma.view"(%cur, ...)
    "dma.slice"(%tile, %global, ...)
    ...
    "dma.advance_ring"(%ring)
  }
  // bias and final output store still use the same logical acc tile.
  "dma.deslice"(%out, %acc_view, ...)
}
```

- acc/output tile 预期：
  - static/static `%63`、static/dynamic `%65`、dynamic/dynamic `%89` 同构 acc 是 C reduce loop carried value，不得接 C reduce loop 的 `dma.current_ring`。
  - 若实现把 acc/output 纳入 outer output tile ring，`dma.current_ring` 必须在 C reduce loop 前，`dma.advance_ring` 必须在 C reduce loop、bias 分支和最终 output deslice 之后，`num` 按 outer output tile loop 的 target capacity / slot bytes 正常计算。
  - 若某个未来 conv2d 形态只有 C reduce loop、没有外层 output tile loop 可轮转，acc/output ring `num` 必须为 1。
- bias tile / broadcast full 预期：
  - 本计划默认不把 bias tile / broadcast full 纳入 C reduce loop ring 化。
  - 若后续需要 outer output tile ring，必须另行证明 lifecycle 与 last-use，不得影响本计划主线。

## 计划内小任务

### S0. 闭合 conv2d 到不了 multi-buffer 的 memory-plan 基线问题

- 为什么做：conv2d 当前停在 memory-plan auto-pad 解析错误，无法跑到 `24-multi-buffer.mlir`，会阻断本计划的 conv2d 验收。
- 做什么：最小修复 `memory_plan.py` 内部 auto-pad 复杂 `min(...)` / symbol 表达式解析，使三条 conv2d demo 能继续进入 multi-buffer 阶段。
- 不做什么：不新增公开 API，不改 pipeline option，不改公开错误语义，不做 conv2d 专用字符串特判。
- 怎么验收：新增或更新覆盖 auto-pad 复杂表达式解析的 pass / pipeline 测试，并运行三条 conv2d demo 证明能写到 `24-multi-buffer.mlir`；合同验收：本卡无当前必过 `expectation`，`expectation/` 只读。
- 卡住问谁：表达式 parser / auto-pad 合同冲突问架构师；流程和依赖状态问管理员；公开 API 需求问用户。
- 修改 `kernel_gen/passes/memory_plan.py` 内部 auto-pad 表达式解析逻辑。
- 当前失败点在 `_apply_auto_pad` 解析 top-level `min(left,right)` 时，用手写 comma split 后对右侧表达式调用 `SymbolExprAttr.from_expr(...)`，在 conv2d 生成的复杂 `min(...)` / 符号表达式上报 `symbol expr contains trailing tokens`。
- 实现要求：
  - 不新增公开 API。
  - 不改 pipeline option。
  - 不改公开错误语义。
  - 使用现有符号表达式 parser / printer 能力，避免新增 ad-hoc 只适配 conv2d 的字符串特判。
  - 修复后三条 conv2d demo 必须能继续跑到 `24-multi-buffer.mlir`，不能只让 memory-plan 单步通过。
- 测试要求：
  - 增加覆盖 auto-pad `min(...)` 复杂表达式解析的 pass 或 pipeline 测试，测试输入应来自 conv2d `06-lower-nn` 同构形态。
  - diff 反推测试必须包含触达 `memory_plan.py` 的相关测试，不得只靠 conv2d demo 脚本替代。

### S1. 修订 multi-buffer spec 为 loop staging ring 化合同

- 为什么做：当前 spec 仍偏 matmul direct pair 行为，不能指导 loop-local staging / scratch ring 化实现和审查。
- 做什么：把 `spec/pass/multi_buffer.md` 修订为通用 loop staging ring 化合同，明确 matmul / conv2d 是验收用例而非专用逻辑。
- 不做什么：不新增公开 API，不新增 pipeline option，不修改 `expectation/`。
- 怎么验收：spec 中写清 direct alias、direct alloc use、last-use、alias escape、nested region no-op 和 target `num` 口径，并通过 `git diff --check`；合同验收：本卡无当前必过 `expectation`，`expectation/` 只读。
- 卡住问谁：spec 合同或公开 API 边界问用户；验收口径问架构师；流程状态问管理员。
- 更新 `spec/pass/multi_buffer.md`。
- 明确 `multi-buffer` 不是 matmul 专用 pass，而是面向可证明 loop-local staging / scratch buffer。
- 明确 matmul 与 conv2d 都只是该通用 loop staging ring 化合同的验收用例。
- 保留现有 direct matmul pair 行为作为兼容子集。
- 写清 `dma.reinterpret(%alloc, ...)` / direct alloc use / last-use / alias escape / nested region no-op 边界。
- 写清当前计划不新增公开 API 和 pipeline option。

### S2. 重构 MultiBufferPass 候选识别

- 为什么做：当前 pass 只识别 `kernel.matmul` lhs/rhs direct alloc pair，不能处理真实 dump 中的 `reinterpret/view/reshape` alias 和 conv2d direct alloc use。
- 做什么：重构候选识别为逐个 `dma.alloc` 分析，建立 `RingCandidate`，分类 staging / scratch、loop-carried acc/output、bias/broadcast 和未知逃逸。
- 不做什么：不做通用 alias escape 分析，不处理多层 alias chain，不处理已有 ring 再 ring 化。
- 怎么验收：`test/passes/test_multi_buffer.py` 覆盖 direct alias、direct alloc use、acc/output no-op 或 outer-loop ring、escape no-op 和 target `num` 计算；合同验收：本卡无当前必过 `expectation`，`expectation/` 只读。
- 卡住问谁：候选 role / loop lifecycle 无法判定问架构师；公开 API 需求问用户；流程状态问管理员。
- 修改 `kernel_gen/passes/multi_buffer.py`。
- 从当前 `_rewrite_matmul_if_pair(symbol_for, matmul, ...)` 转为扫描 `DmaAllocOp` 构造 `RingCandidate`。
- 候选字段至少包含：
  - 原始 `alloc_op`
  - 原始 `free_op`
  - `role`
  - `reduce_loop` 或 `producer_consumer_loop`
  - `target_loop`
  - `advance_loop` 或等价 last-use lifecycle 分类
  - `slot_type`
  - `slot_bytes`
  - `ring_num_policy`
  - 需要改 source 的 alias ops
  - 需要直接替换 memory operand 的 direct-use ops 与 operand index / role
  - 本轮 first use / last use anchor
- 支持 direct `dma.reinterpret(%alloc, ...)`。
- 支持 direct `dma.view(%alloc, ...)`、`dma.reshape(%alloc, ...)` 作为 v1 direct alias；conv2d lowering 当前主要使用 `dma.view` / `dma.reshape` 而不是 `dma.reinterpret`。
- 支持 alias result 被 `dma.deslice`、`dma.slice`、`dma.copy`、`dma.transpose`、`kernel.img2col2d`、`kernel.matmul`、`kernel.binary_elewise` 等 op 消费。
- 支持 direct alloc use 被纳入同一个 candidate：
  - `dma.slice` 的 target / source memory operand 若直接来自候选 alloc，必须能替换为 current slot 并纳入 producer / consumer first-use。
  - `kernel.img2col2d` 的 input / output memory operand 若直接来自候选 alloc，必须按读写角色纳入 first-use / last-use。
  - `kernel.matmul` 的 output / lhs / rhs memory operand 若直接来自候选 alloc，必须区分 per-iteration scratch 与 loop-carried acc/output。
  - `dma.transpose` 的 source / target memory operand 若直接来自候选 alloc，必须按其 producer / consumer 顺序纳入 last-use。
  - `dma.fill`、`dma.deslice`、`kernel.binary_elewise` 的 direct memory operand 只作为 lifecycle 锚点使用；能证明为 per-iteration staging / scratch 时才替换，属于 acc/output 或 bias/broadcast 时按对应 no-op / outer-loop 规则处理。
- 必须区分 per-iteration staging / scratch 与 loop-carried accumulator：
  - staging / scratch 在本轮写入后被本轮消费，允许按 innermost target loop advance。
  - accumulator 在 reduce loop 多轮之间读写同一逻辑值，不能按 reduce loop 每轮 advance；若存在外层 output tile loop 且能把 advance 放到 reduce loop 与 post-reduce last use 之后，则 `target_loop = outer_output_tile_loop`，`ring_num_policy = target_capacity`。
  - accumulator 若只有一层 reduce loop、没有外层可轮转 output loop，则 `ring_num_policy = const_1`；不得使用 target capacity 公式给它计算多 slot。
  - accumulator 若无法证明 outer output tile loop 或 post-reduce last use，则保持 no-op。
- 不支持多层 alias、alias escape、跨多个 sibling loop、已有 ring。

### S3. 实现 ring 改写

- 为什么做：完成候选识别后，需要把原 typed alloc/free 改写成 backing i8 alloc + ring + current/advance，并保持原数据流语义。
- 做什么：生成 backing、`num`、`offset/slot_bytes`、`dma.make_ring`，在 first use 前插入 `dma.current_ring`，在真实 last use 后插入 `dma.advance_ring`，替换 alias source 和 direct-use operand，删除原 alloc/free。
- 不做什么：不按 loop 尾机械插入 advance，不把 acc/output 混入 K/C reduce loop 每轮 advance，不生成畸形 `num <= 0` ring。
- 怎么验收：pytest 和 dump 检查证明 current slot use-def、advance 位置、target capacity `num`、acc/output 生命周期和原 alloc/free 删除都正确；合同验收：本卡无当前必过 `expectation`，`expectation/` 只读。
- 卡住问谁：IR rewrite 插入点或 verifier 冲突问架构师；流程状态问管理员；公开 API 需求问用户。
- 对每个候选生成 backing `dma.alloc`、`num` SSA、`offset/slot_bytes` SSA、`dma.make_ring`。
- 本计划主实现口径为 target 非空路径，按 target registry memory capacity 计算 `num`：
  - same-space 候选按同一 target loop 与同一 memory space 的 slot bytes 合计计算共享 `num`。
  - different-space 候选各自按本 space capacity 计算 `num`。
  - 动态 shape 下保留 `symbol.floordiv(capacity, total_slot_bytes)`；静态 shape 可在当前 pass 或后续 canonicalize 中折成常量。
  - 上述 capacity 公式用于已证明 target loop 的候选；per-iteration staging / scratch 使用其 producer / consumer loop，loop-carried acc/output 使用 outer output tile loop。
  - loop-carried acc/output 不参与 innermost K loop staging / scratch 的 same-space 分组；若 outer output tile loop 可证明，则按该 loop 与 memory space 参与正常 target capacity 计算。
  - loop-carried acc/output 若被明确 ring 化且无外层可轮转 output loop，生成 `symbol.const 1` 作为 `num`。
  - `target is None` 时仅保留现有 `memory_stage` fallback 行为，不作为新增测试主线。
- 在 target loop 内 first use 前插入 `dma.current_ring`。
- 将 direct alias source 从原 alloc 改为 current slot。
- 将已纳入 candidate 的 direct-use memory operand 从原 alloc 改为 current slot；该替换必须覆盖 conv2d 中 direct `dma.slice` target、`kernel.img2col2d` input/output、`kernel.matmul` output/lhs/rhs、`dma.transpose` target/source，以及 `dma.fill` / `dma.deslice` / `kernel.binary_elewise` 的 lifecycle 锚点场景。
- direct-use operand 与 alias result use 必须共同参与本轮 first-use / last-use 计算；不能只按 alias op 的位置决定 `current_ring` / `advance_ring` 插入点。
- 在该 ring 的真实 lifecycle last use 后插入 `dma.advance_ring`：
  - innermost K loop staging / scratch：位于本轮 `dma.deslice` / `dma.copy` / `kernel.matmul` 最后使用之后。
  - reduce loop carried acc/output：位于 reduce loop 之后，且在 bias 分支、broadcast/binary elewise、最终 output deslice 等所有 post-reduce use 之后。
- 删除原 staging `dma.alloc/free`；变换后原 typed alloc/free 不残留，只保留 backing `dma.alloc/free`。

### S4. 同步测试

- 为什么做：ring 化风险集中在 use-def、advance 位置和 acc/output 生命周期，不能只靠是否出现 ring op 文本判断。
- 做什么：同步 pass pytest、pipeline dump 检查和真实 dump use-def 断言，覆盖 matmul、conv2d、direct alias、direct use、no-op 和 target `num`。
- 不做什么：不修改 `expectation/`，不把 expectation 当作 diff 反推测试，不放宽源码逻辑和精度校验。
- 怎么验收：运行 `test/passes/test_multi_buffer.py`、`test/passes/pipeline/test_npu_demo_lowering.py -k "multi_buffer or static_dump or dynamic"`，并执行计划 here-doc 检查所有目标 dump；合同验收：本卡无当前必过 `expectation`，`expectation/` 只读。
- 卡住问谁：测试真源和验收口径问架构师；流程状态问管理员。
- 更新 `test/passes/test_multi_buffer.py`：
  - 保留现有 direct matmul pair 测试。
  - 增加 `dma.reinterpret(%alloc, ...)` alias 被 copy / kernel consumer 消费的正例。
  - 增加 `dma.view(%alloc, ...)` 与 `dma.reshape(%alloc, ...)` alias 被 kernel consumer 消费的正例，覆盖 conv2d 当前 lowering 形态。
  - 增加无 view 的 direct alloc use 正例，覆盖 direct `dma.slice` target、`kernel.img2col2d` input/output、`kernel.matmul` output/lhs/rhs、`dma.transpose` target/source 的 operand 替换和 first/last-use 计算。
  - 增加 `dma.deslice` producer + copy + kernel consumer 的正例，覆盖本计划中的 absent_bias K loop 结构。
  - 增加 `dma.slice` producer + `kernel.img2col2d` + `kernel.matmul` + transpose / partial scratch 的 conv2d 正例，覆盖 C reduce loop staging / scratch 结构。
  - 增加 alias escape、跨 sibling loop、多层 alias、acc/output buffer 不按 reduce loop 每轮 advance 等 no-op 测试。
  - 增加 loop-carried accumulator 生命周期测试：如果 acc 被纳入 ring 候选且存在 outer output tile loop，`dma.current_ring` 必须在 reduce loop 前，`dma.advance_ring` 必须在 reduce loop 和 post-reduce last use 后，`num` 必须按 outer output tile loop 的 target capacity 正常计算；若无法证明该 lifecycle，必须保持 acc no-op。
  - 增加单层 reduce loop accumulator 测试：若实现生成 ring，`num` 必须为 1；不得按 target capacity 算出多 slot，也不得把 `advance_ring` 插在 reduce loop body 每轮尾部。
  - 增加 target `npu_demo` same-space / different-space num 计算断言。
- 更新 `test/passes/pipeline/test_npu_demo_lowering.py` 中对应 dump 检查：
  - 静态 absent / present bias 的 `24-multi-buffer.mlir` 必须包含 ring op。
  - static input + dynamic tile 的 `24-multi-buffer.mlir` 必须包含 ring op。
  - dynamic tile dump 必须包含 target capacity 计算链或 fold 后的等价 ring op。
  - conv2d static/static absent / present、static/dynamic、dynamic/dynamic 的 `24-multi-buffer.mlir` 必须包含 ring op。
  - 原 K loop typed staging alloc/free 不再作为完成态残留。
  - 增加真实 dump use-def 断言，不能只检查 ring op 文本存在：
    - 静态 absent / present bias 的 innermost K loop staging / scratch ring 候选是 `%15/%16/%20/%21` 同构 alloc；acc/output backing `%11` 不得接 K-loop 的 `dma.current_ring`，若 `%11` 作为 outer output tile loop ring 候选，则按 acc/output lifecycle 与 `num` 规则另行检查；bias/broadcast backing `%12/%13` 不接 K-loop `dma.current_ring`。
    - static input + dynamic tile dump 的 innermost K loop staging / scratch ring 候选是 `%16/%17/%21/%22` 同构 alloc；acc/output backing `%12` 不得接 K-loop 的 `dma.current_ring`，若 `%12` 作为 outer output tile loop ring 候选，则按 acc/output lifecycle 与 `num` 规则另行检查；bias/broadcast backing `%14/%15` 不接 K-loop `dma.current_ring`。
    - dynamic dump 的 innermost K loop staging / scratch ring 候选是 `%16/%17/%21/%22` 同构 alloc；acc/output backing `%12` 不得接 K-loop 的 `dma.current_ring`，若 `%12` 作为 outer output tile loop ring 候选，则按 acc/output lifecycle 与 `num` 规则另行检查；bias/broadcast backing `%14/%15` 不接 K-loop `dma.current_ring`。
    - lhs/rhs staging 的 `dma.reinterpret` source 来自对应 `dma.current_ring` result；`dma.deslice` / `dma.copy` / `kernel.matmul` 仍消费原本逻辑 tile view。
    - `kernel.matmul` 的 lhs/rhs operands 来自 local-space current slot view，output/acc operand 仍是同一 K loop 内跨轮累加的 acc view。
    - 每个 `dma.advance_ring` 位于该 ring 本轮最后一次 `dma.deslice` / `dma.copy` / `kernel.matmul` 使用之后。
    - 若实现把 acc/output 纳入 outer-loop ring，dump 检查必须证明对应 `dma.advance_ring` 位于 reduce loop 之后、bias/store last use 之后，而不是 K loop 每轮 advance，且 `num` 是 outer output tile loop 的 target capacity 正常计算结果。
    - 若某个 dump 形态只有单层 reduce loop 且 acc/output 被 ring 化，dump 检查必须证明 `dma.make_ring` 的 `num` 为 `1`。
    - `dma.broadcast` 和 bias `kernel.binary_elewise` 路径不因本计划改写为 ring current source。
    - conv2d reduce-loop staging / scratch ring 候选必须覆盖 input slice、weight slice、img2col col、matmul output、transpose output、partial scratch 同构角色；direct alloc operand 必须和 alias result 一起纳入 use-def / first-use / last-use 检查；acc/output 不得接 C reduce loop 的 `dma.current_ring`。
    - conv2d 若实现 outer output tile loop acc/output ring，dump 检查必须证明 `dma.advance_ring` 位于 C reduce loop、bias 分支和最终 output deslice 之后，且 `num` 是 outer output tile loop 的 target capacity 正常计算结果。
- 不修改 `expectation/`。

### S5. matmul demo 源码逻辑与精度验收

- 为什么做：IR ring 化必须最终反映到 matmul demo 的生成代码和数值结果，不能只停在 pass 单测。
- 做什么：运行 static/static、static/dynamic、dynamic/dynamic matmul demo，必要时同步同文件内部源码断言到当前生成源码形态。
- 不做什么：不修改公开 kernel / `main()` 签名，不删除源码逻辑校验，不放宽精度阈值。
- 怎么验收：三条 matmul demo 均退出码 0，absent / present bias 均通过脚本内 NumPy 参考校验和源码逻辑检查；合同验收：本卡无当前必过 `expectation`，`expectation/` 只读。
- 卡住问谁：源码断言对应公开生成形态争议问架构师；精度阈值变更需求问用户；流程状态问管理员。
- 运行 `kernel/matmul/inputs_static_tile_static.py`，要求 absent / present bias 都输出 `[CHECK]` 且退出码 0。
- 运行 `kernel/matmul/inputs_static_tile_dynamic.py`，要求 absent / present bias 都通过 `np.allclose(..., atol=1e-3, rtol=1e-3)` 且退出码 0。
- 运行 `kernel/matmul/inputs_dynamic_tile_dynamic.py`，要求 absent / present bias 都通过 `np.allclose(..., atol=1e-3, rtol=1e-3)` 且退出码 0。
- 源码断言 `_assert_accumulator_source` 必须通过；若生成源码中 output deslice 形态不再是旧字符串 `deslice(arg0`，execute 需在同文件内把断言改成当前公开源码形态的等价顺序检查，不能删除源码逻辑校验。

### S6. conv2d demo 源码逻辑与精度验收

- 为什么做：用户已把完成目标扩展到 conv2d，必须证明 conv2d 静态 / 动态也能跑到 ring IR、生成代码并保持精度。
- 做什么：运行 static/static、static/dynamic、dynamic/dynamic conv2d demo，必要时同步同文件内部源码 / IR 断言到当前生成形态。
- 不做什么：不修改公开 kernel / `main()` 签名，不让 demo 只停在 `06-lower-nn.mlir`，不绕过源码 dump 一致性检查。
- 怎么验收：三条 conv2d demo 均退出码 0，absent / present bias 均通过脚本内 NumPy 参考校验，且写出完整 `24-multi-buffer.mlir` 与后续 `source.cpp`；合同验收：本卡无当前必过 `expectation`，`expectation/` 只读。
- 卡住问谁：conv2d layout / tile / source 断言争议问架构师；精度阈值变更需求问用户；流程状态问管理员。
- 运行 `kernel/conv2d/inputs_static_tile_static.py`，要求 absent / present bias 都输出 `[CHECK]` 且退出码 0。
- 运行 `kernel/conv2d/inputs_static_tile_dynamic.py`，要求 absent / present bias 都通过脚本内 NumPy 参考校验，源码 dump 一致性检查通过，退出码 0。
- 运行 `kernel/conv2d/inputs_dynamic_tile_dynamic.py`，要求 absent / present bias 都通过脚本内 NumPy 参考校验，源码 dump 一致性检查通过，退出码 0。
- 三条 conv2d demo 必须写出完整 `24-multi-buffer.mlir` 与后续 `source.cpp`，不得只停在 `06-lower-nn.mlir`。
- 若需要同步 conv2d demo 内部源码 / IR 断言，只允许修同文件内部检查逻辑，不得修改公开 kernel / `main()` 签名。

## 验收设计

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_multi_buffer.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k "multi_buffer or static_dump or dynamic"`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_dynamic.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_static_tile_static.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_static_tile_dynamic.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_dynamic_tile_dynamic.py`
- 逐文件检查 `24-multi-buffer.mlir` 同时包含 `"dma.make_ring"`、`"dma.current_ring"`、`"dma.advance_ring"`：
```bash
python3 - <<'PY'
from pathlib import Path

paths = [
    Path("kernel/dump/matmul/inputs_static_tile_static_absent_bias/matmul_inputs_static_tile_static_kernel/24-multi-buffer.mlir"),
    Path("kernel/dump/matmul/inputs_static_tile_static_present_bias/matmul_inputs_static_tile_static_kernel/24-multi-buffer.mlir"),
    Path("kernel/dump/matmul/inputs_static_tile_dynamic/24-multi-buffer.mlir"),
    Path("kernel/dump/matmul/inputs_dynamic_tile_dynamic/24-multi-buffer.mlir"),
    Path("kernel/dump/conv2d/inputs_static_tile_static_absent_bias/conv2d_inputs_static_tile_static_kernel/24-multi-buffer.mlir"),
    Path("kernel/dump/conv2d/inputs_static_tile_static_present_bias/conv2d_inputs_static_tile_static_kernel/24-multi-buffer.mlir"),
    Path("kernel/dump/conv2d/inputs_static_tile_dynamic/24-multi-buffer.mlir"),
    Path("kernel/dump/conv2d/inputs_dynamic_tile_dynamic/24-multi-buffer.mlir"),
]
needles = ('"dma.make_ring"', '"dma.current_ring"', '"dma.advance_ring"')
for path in paths:
    text = path.read_text(encoding="utf-8")
    missing = [needle for needle in needles if needle not in text]
    if missing:
        raise SystemExit(f"{path}: missing {missing}")
PY
```
- `git diff --check`
- `git diff --name-only HEAD -- kernel_gen kernel/matmul kernel/conv2d spec test expectation .skills agents/standard AGENTS.md ARCHITECTURE/plan | sort`
- diff 文件清单预期：
  - `kernel_gen/passes/memory_plan.py`
  - `kernel_gen/passes/multi_buffer.py`
  - `spec/pass/multi_buffer.md`
  - `test/passes/test_multi_buffer.py`
  - `test/passes/pipeline/test_npu_demo_lowering.py`
  - 若源码断言需同步当前生成源码形态：`kernel/matmul/inputs_static_tile_dynamic.py` / `kernel/matmul/inputs_dynamic_tile_dynamic.py`
  - 若源码断言需同步当前生成源码形态：`kernel/conv2d/inputs_static_tile_static.py` / `kernel/conv2d/inputs_static_tile_dynamic.py` / `kernel/conv2d/inputs_dynamic_tile_dynamic.py`
  - 本计划正式化前会包含 `ARCHITECTURE/plan/multi_buffer_loop_staging_ring.md`
- 禁止出现：
  - `expectation/**`
  - `.skills/**`
  - `agents/standard/**`
  - `AGENTS.md`
  - 公开 API 签名变更

## 迭代审阅记录

### Round 1

- 标准包：
  - 根 `AGENTS.md`。
  - `agents/standard/审查规范.md`。
  - `agents/standard/任务记录约定.md`。
  - 本计划 Draft 3 全文。
  - 用户确认目标：matmul 静态 / 动态 IR 都完成 multi-buffer 变换，生成代码逻辑正确，数值精度合格。
  - 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`；不新增 / 删除 / 重命名 / 修改公开 API；不新增 pipeline option。
- Reviewer A：Carver / `019ea129-78a6-7c22-beb3-6196c659b105`。
  - 结论：不通过。
  - 发现：验收 diff 清单未覆盖 `kernel/matmul`，但计划允许同步 matmul demo 内部源码断言，正式验收会漏查实际 diff。
  - 主线处理：验收命令从 `kernel_gen spec test ...` 扩展为 `kernel_gen kernel/matmul spec test ...`，覆盖允许修改的 demo 文件。
- Reviewer B：Carson / `019ea129-ae22-7f50-a0d1-c63cb55a0066`。
  - 结论：不通过。
  - 发现 1：dump 检查 here-doc 在旧版文本中不可复跑。
  - 发现 2：IR 语义验收不够闭环，只检查 ring op 存在，未锁定 current slot use-def、advance 位置、acc/bias 不误纳。
  - 主线处理：补完整可复制 here-doc；S4 增加真实 dump use-def 断言，覆盖只 ring 化目标 staging、acc/output 与 bias/broadcast 不接 current ring、reinterpret / matmul operand 数据流和 advance 位置。

### Round 2

- 标准包：
  - 根 `AGENTS.md`。
  - `agents/standard/审查规范.md`。
  - `agents/standard/任务记录约定.md`。
  - Round 1 发现与主线修订后的最新计划全文。
  - 待用户确认项：无。
  - 禁止修改面与必过验收命令：以本计划最新正文为准。
- Reviewer A：Carver / `019ea129-78a6-7c22-beb3-6196c659b105`。
  - 结论：通过。
  - 阻断项：无。
  - 最小需改项：无。
  - 待确认项：无。
  - 关键证据：上一轮 diff 清单漏覆盖 `kernel/matmul` 已收口；计划仍明确不改公开 API、不新增 pipeline option、`expectation/` 只读。
- Reviewer B：Carson / `019ea129-ae22-7f50-a0d1-c63cb55a0066`。
  - 结论：通过。
  - 阻断项：无。
  - 最小需改项：无。
  - 待确认项：无。
  - 关键证据：here-doc 验收脚本已补完整；S4 已明确真实 dump use-def 断言，覆盖 ring 候选、acc/bias no-op、matmul operand 和 advance 位置。

### Round 3

- 触发来源：用户追加关键语义规则，指出累加 acc 不应按 reduce loop 每轮 advance；如果 ring 化，应在 reduce loop 后、完成 bias/store/output deslice 等最后 use 后再 advance。
- 标准包：
  - 根 `AGENTS.md`。
  - `agents/standard/审查规范.md`。
  - `agents/standard/任务记录约定.md`。
  - 用户追加规则与主线修订后的最新计划全文。
  - 待用户确认项：无。
  - 禁止修改面与必过验收命令：以本计划最新正文为准。
- Reviewer A：Ampere / `019ea142-d85f-7ce0-ba03-70207a98379d`。
  - 结论：通过。
  - 阻断项：无。
  - 最小需改项：无。
  - 待确认项：无。
  - 关键证据：新增规则已写入完成态；当时已确认口径仍默认只 ring K-loop staging/scratch，acc/output 与 bias/broadcast no-op；S2-S4 已把 lifecycle 分类、acc no-op fallback、advance 插入点和对应测试断言写成可执行动作。该 acc/output 默认 no-op 口径已被 Round 5 前用户修正规则取代：有 outer output tile loop 时 `num` 正常计算，无外层可轮转 loop 时才 `num=1`。
- Reviewer B：Ptolemy / `019ea143-1c43-7650-8bab-b81977ab16c4`。
  - 结论：通过。
  - 阻断项：无。
  - 最小需改项：无。
  - 待确认项：无。
  - 关键证据：计划已把 acc/output advance 粒度写成完成态、实现和验收硬约束；真实 dump 口径匹配，静态 `%11`、动态 `%12` 是跨 K-loop 累加的 output/acc，K-loop ring 候选仍为静态 `%15/%16/%20/%21`、动态 `%16/%17/%21/%22`。

### Round 4

- 触发来源：用户追加关键语义规则，指出必须先逐个分析 `dma.alloc` 再变换；若 alloc 是 K/reduce 累加维度承载的 loop-carried acc/output，应在 reduce loop 外 current/advance；若只有一层 reduce loop、没有外层 output tile loop 可轮转，则 ring `num` 为 1，或当时计划默认保持 no-op。后续用户已在 Round 5 前修正为：有 outer output tile loop 时 `num` 正常计算，无外层可轮转 loop 时才 `num=1`。
- 标准包：
  - 根 `AGENTS.md`。
  - `agents/standard/审查规范.md`。
  - `agents/standard/任务记录约定.md`。
  - 用户追加 per-alloc analysis / reduce-carried num 规则与主线修订后的最新计划全文。
  - 待用户确认项：无。
  - 禁止修改面与必过验收命令：以本计划最新正文为准。
- Reviewer A：Pascal / `019ea149-607c-7012-85d9-3122d0c73197`。
  - 结论：通过。
  - 阻断项：无。
  - 最小需改项：无。
  - 待确认项：无。
  - 关键证据：新增规则已写入完成态，要求先逐个分析 `dma.alloc` 生命周期 role；当时静态 `%11`、dynamic `%12` 默认 no-op，acc/output 不混入 K-loop same-space capacity 分组；S2-S4 已把候选字段、实现步骤、acc 生命周期测试和单层 reduce `num=1` 测试写成可执行动作。该默认 no-op 口径已被 Round 5 前用户修正规则取代。
- Reviewer B：Maxwell / `019ea14b-0f3b-71f3-8102-8ba0445578cb`。
  - 结论：通过。
  - 阻断项：无。
  - 最小需改项：无。
  - 待确认项：无。
  - 关键证据：per-alloc / reduce-carried 规则在完成态、目标行为、capacity 规则和 S2-S4 均闭合；真实 dump 口径保持只 ring 静态 `%15/%16/%20/%21`、dynamic `%16/%17/%21/%22`，排除静态 `%11/%12/%13`、dynamic `%12/%14/%15`；边界仍不新增公开 API、不改 `expectation/`、不混入 memory-pool 后 CSE 或源码发射 `+ 0` 清理。

### Round 5

- 触发来源：用户修正 acc/output `num` 口径：若没有外层 output tile loop 可轮转，ring 化时 `num = 1`；否则默认按 target capacity / slot bytes 正常计算 `num`。
- 标准包：
  - 根 `AGENTS.md`。
  - `agents/standard/审查规范.md`。
  - `agents/standard/任务记录约定.md`。
  - 用户修正规则与主线修订后的最新计划全文。
  - 待用户确认项：无。
  - 禁止修改面与必过验收命令：以本计划最新正文为准。
- Reviewer A：Hilbert / `019ea165-1ef9-7220-88ab-30a30011f82b`。
  - 结论：通过。
  - 阻断项：无。
  - 最小需改项：无。
  - 待确认项：无。
  - 关键证据：完成态已明确 acc/output 不按 K loop 每轮 advance；outer output tile loop 可绑定时 `num` 正常按 target capacity / slot bytes 计算，无外层可轮转 loop 时才 `num=1`；static `%11` 外有 `%22/%26` output tile loops，dynamic `%12` 外有 `%23/%27` output tile loops；target num 口径和 S2-S4 均已闭合，历史 Round 3/4 旧 no-op 口径已标为当时口径。
- Reviewer B：Arendt / `019ea165-7602-7ba1-ace5-6267593977de`。
  - 结论：通过。
  - 阻断项：无。
  - 最小需改项：无。
  - 待确认项：无。
  - 关键证据：S2 要先逐 alloc 分类并设置 `target_loop` / `ring_num_policy`；S3 明确 outer acc/output 参与正常 target capacity、无外层时 `symbol.const 1`；S4 明确 dump 检查不能误杀 outer acc/output ring，同时阻止 K-loop 每轮 current/advance；API / expectation 边界仍清楚。

### Round 6

- 触发来源：用户将完成目标从 matmul 扩展为 matmul + conv2d，要求二者都能变换为预期 IR 和代码。
- 标准包：
  - 根 `AGENTS.md`。
  - `agents/standard/审查规范.md`。
  - `agents/standard/任务记录约定.md`。
  - 用户扩展目标与主线修订后的最新计划全文。
  - 待用户确认项：无。
  - 禁止修改面与必过验收命令：以本计划最新正文为准。
- Reviewer A：Chandrasekhar / `019ea177-61b4-7163-8ede-2640ba9868e6`。
  - 结论：不通过。
  - 阻断项 1：matmul `inputs_static_tile_dynamic` 的 IR 完成态没有闭合，正文目标要求 matmul 静态 / 动态 IR 都完成，但完成态、当前基线、IR 预期和验收脚本没有纳入 `kernel/dump/matmul/inputs_static_tile_dynamic/24-multi-buffer.mlir`。
  - 阻断项 2：conv2d direct alloc use 改写步骤不够可执行，`dma.slice`、`kernel.img2col2d`、`kernel.matmul`、`dma.transpose` 等 direct use 没有明确 operand 替换和 first/last-use 计算。
  - 主线处理：已把 `inputs_static_tile_dynamic` 纳入计划目标、完成态、当前基线、IR 预期、S4 dump 检查和 here-doc 验收；已把 direct alloc use 的 operand index / role、operand 替换、lifecycle 锚点与 conv2d op 覆盖写入目标行为、S2、S3 和 S4；已补充触达 `memory_plan.py` / `multi_buffer.py` 时同步文件级 API 列表的要求。
- Reviewer B：Copernicus / `019ea177-aaf5-7842-bb0b-ec0fad2eedb5`。
  - 结论：通过。
  - 阻断项：无。
  - 最小需改项：无。
  - 待确认项：无。
  - 关键证据：conv2d 计划明确 `06-lower-nn.mlir` 只用于识别语义角色，实际 `MultiBufferPass` 在 `23-canonicalize.mlir -> 24-multi-buffer.mlir` 执行；真实 conv2d role mapping、acc/output 外层生命周期、target `num` 规则和非文本化验收均已闭合。

### Round 7

- 触发来源：Round 6 发现项完成主线修订后，复验 matmul `inputs_static_tile_dynamic` 闭合、conv2d direct alloc use 可执行性和边界一致性。
- 标准包：
  - 根 `AGENTS.md`。
  - `agents/standard/审查规范.md`。
  - `agents/standard/任务记录约定.md`。
  - Round 6 发现与主线修订后的最新计划全文。
  - 待用户确认项：无。
  - 禁止修改面与必过验收命令：以本计划最新正文为准。
- Reviewer A：Gauss / `019ea17f-c120-7890-9e6a-26b78ef86b16`。
  - 结论：不通过。
  - 阻断项：无。
  - 最小需改项：非目标仍写着 v1 只支持 direct `dma.reinterpret(%alloc, ...)`，与目标行为中 `dma.view` / `dma.reshape` / direct alloc use 支持冲突。
  - 待确认项：无。
  - 主线处理：已把非目标修正为“不处理多层 alias chain；v1 只支持 direct `dma.reinterpret(%alloc, ...)` / `dma.view(%alloc, ...)` / `dma.reshape(%alloc, ...)` alias，以及已证明的 direct alloc use”，保持不支持多层 alias 的边界不变。
- Reviewer B：Anscombe / `019ea17f-fd09-7422-8040-bcbbd99e130e`。
  - 结论：通过。
  - 阻断项：无。
  - 最小需改项：无。
  - 待确认项：无。
  - 关键证据：matmul static/static、static/dynamic、dynamic/dynamic 覆盖闭合；conv2d input slice、weight slice、img2col col、matmul out2、transpose output、partial scratch role mapping 与 direct alloc operand use-def 检查闭合；acc/output 生命周期和 target `num` 规则闭合；验收不止 ring op 文本。

### Round 8

- 触发来源：Round 7 Reviewer A 最小需改项完成主线修订后，定向复验非目标边界与目标行为一致性。
- 标准包：
  - 根 `AGENTS.md`。
  - `agents/standard/审查规范.md`。
  - `agents/standard/任务记录约定.md`。
  - Round 7 发现与主线修订后的最新计划全文。
  - 待用户确认项：无。
  - 禁止修改面与必过验收命令：以本计划最新正文为准。
- Reviewer A：Gauss / `019ea17f-c120-7890-9e6a-26b78ef86b16`。
  - 结论：通过。
  - 阻断项：无。
  - 最小需改项：无。
  - 待确认项：无。
  - 关键证据：非目标边界已与目标行为、S2、S4 一致；公开 API / pipeline option / `expectation/` 边界仍闭合；S2/S3/S4 对 direct-use operand 替换、first/last-use、conv2d role 覆盖和 acc/output 生命周期有可执行约束；验收设计列入 matmul + conv2d 脚本、IR dump、源码逻辑和精度命令。

### 收敛结论

- 截至 Round 8，已发起并完成八轮、合计十五次 subagent strict review / 复验；Round 6 与 Round 7 发现项均已完成主线修订并经后续复验通过。
- 当前剩余阻断项：无。
- 当前剩余最小需改项：无。
- 剩余待确认项：无。
- 守护最终复验已通过，管理员已创建并下发唯一计划级 `execute`；当前任务链已完成 execute / review，正在进行 archive_acceptance 入档复验。
- 当前无必过 `expectation` 合同验收入口，`expectation/` 继续只读；当前入档状态修复只同步本文档状态与任务记录，不改变技术方案、公开 API、验收资产、禁止修改面或 pipeline option。

## 后续流程占位

- 已完成：
  - subagent strict review Round 1 / Round 2 / Round 3 / Round 4 / Round 5 / Round 6 / Round 7 / Round 8 收敛记录。
  - 守护最终检验 G1：结论不通过；阻断项为缺少正式计划级任务 / 标准小任务卡，以及未写明 `T-20260607-2b00a1ea / pass_dump_xdsl_pipeline_spec_options` 下发依赖。
  - Draft 9-R1：仅修订计划结构、计划级任务落地信息、S0-S6 五行短口径和下发依赖；不改变技术方案、公开 API、验收资产、`expectation` 授权或禁止修改面。
  - 守护最终复验：已通过，允许管理员下发唯一计划级 `execute`。
  - 管理员下发：已创建并分发 `T-20260607-0c4db1f1 / multi_buffer_loop_staging_ring`，worktree 为 `/home/lfr/kernelcode_generate/wt-20260607-multi-buffer-loop-staging-ring`。
  - execute / review：计划级 execute 已完成实现、spec、测试、demo、dump 与任务记录闭环；review 复审已通过并流转 archive_acceptance。
  - comments-only 裁定 A 返工：大闸蟹裁定 A 后，已完成 `_MultiBufferRewriteRules` docstring 与 `ring.py::_emit_npu_demo_dma_make_ring` 函数说明修复；未改业务逻辑、公开 API、spec、test、expectation、pipeline option 或稳定错误文本。
  - archive_acceptance 第一次复验：发现本文仍停留下发前 / 守护复验前状态，本轮已按任务链事实同步入档状态、latest main 现场、当前无必过 `expectation`、禁止修改面和后续流程占位。
- 仍需完成：
  - archive_acceptance 复验通过后进入 `merge/归档`；不得在 archive_acceptance 通过前直接 merge。
