# 20260527-kernel-demo-random-runtime-symbolic

## 守护最终检验

- 时间：`2026-05-27`
- 结论：`通过，可下发`
- 检验对象：`ARCHITECTURE/plan/kernel_demo_random_runtime_symbolic_green_plan.md`
- 验证基线：计划阶段，尚未创建 execute worktree；管理员拟创建 `/home/lfr/kernelcode_generate/wt-20260527-kernel-demo-random-runtime-symbolic`
- 执行目录：`/home/lfr/kernelcode_generate`
- 合同验收摘要：本计划无必过 `expectation`；execute 禁止修改 `expectation/`、`.skills/`、`agents/standard/`
- 核对摘要：
  - Round 1 / Round 2 subagent strict review 已回写，Round 2 小李飞刀、提莫炖蘑菇、金铲铲大作战均通过；runtime profile 最小项已补。
  - 用户确认项已收口：按 kernel demo 名字决定 IR 静态 / 动态；9 个 demo runtime scale fixed-seed random；conv2d 的 `KH/KW` 与 padding 也随机。
  - 9 个 demo profile 的 seed、候选集合、预算、多 tile 和 tail 条件已锁定；守护复算确认 matmul / conv2d / Flash Attention 合同满足预算与 tail 约束。
  - conv2d static_dynamic、Flash Attention static_dynamic / dynamic_dynamic 的 `run_lowering_demo(...) + ExecutionEngine(...)` 两阶段 recipe、公开 dump 路径矩阵、source/dump 一致性、随机性重算和静态边界门禁可执行。
  - 公开 API 不变；不新增、不删除、不重命名 runner / ExecutionEngine / Memory / SymbolDim 等公开入口。
- 最小阻断项：无。

## 管理员建单记录

- 时间：`2026-05-27`
- 经办：`神秘人`
- 任务类型：计划级 `execute`
- 计划书：`ARCHITECTURE/plan/kernel_demo_random_runtime_symbolic_green_plan.md`
- worktree：`/home/lfr/kernelcode_generate/wt-20260527-kernel-demo-random-runtime-symbolic`
- branch：`task/kernel-demo-random-runtime-symbolic`
- 基线：`origin/main=1778f4f717b84dc46a6a889059fc8d6fdcef895b`
- 流程：`execute -> review -> archive_acceptance -> merge/归档`
- 任务目标：按计划书把 9 个 kernel demo 统一收口为 fixed-seed random runtime scale，并按 demo 名字保持 static / dynamic IR 合同；同步必要 spec/test/demo gate，跑通计划列 pytest、9 个 kernel demo、source/dump 一致性、git diff --check 与敏感目录门禁。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md` 不得进入候选 diff。
- expectation 口径：本计划无必过 `expectation`，不得以修改或运行 `expectation` 作为通过依据。
- 自检：已确认计划正文写有守护最终检验通过、最小阻断项无；当前并行数未满，创建唯一计划级 execute。

## execute 执行记录

时间：2026-05-27 12:46 +0800
经办人：睡觉小分队
任务：T-20260527-8c2408dc / kernel-demo-random-runtime-symbolic
任务目标：按计划书完成 9 个 kernel demo fixed-seed random runtime scale、static/dynamic IR 合同、source/dump 一致性、pytest/9 demo/git diff check/敏感目录门禁闭环。
执行前阅读记录：已读取个人提示词、根 AGENTS.md、agents/standard/任务记录约定.md、agents/standard/实现文件规范.md、主仓 TODO.md 当前任务行、计划书 ARCHITECTURE/plan/kernel_demo_random_runtime_symbolic_green_plan.md、当前任务记录、kernel/runner.py、9 个 kernel demo 脚本与三组 test/kernel pytest。当前 worktree 为 /home/lfr/kernelcode_generate/wt-20260527-kernel-demo-random-runtime-symbolic，branch=task/kernel-demo-random-runtime-symbolic，基线 origin/main=1778f4f717b84dc46a6a889059fc8d6fdcef895b。
计划内小任务卡核对：S1 统一 9 demo fixed-seed random profile；S2 修复 conv2d static_dynamic、FA static_dynamic、FA dynamic_dynamic 的 run_lowering_demo + ExecutionEngine symbolic compile path；S3 补公开脚本 dump/source 回归；S4 跑 py_compile、pytest、9 demo、git diff check、敏感目录和静态边界扫描。
禁止修改面：本计划无必过 expectation；候选 diff 不得包含 expectation/、.skills/、agents/standard/、AGENTS.md、TODO.md、DONE.md。
当前现场：git status 仅任务记录为 untracked，尚未改业务文件。
结论：开始 execute 实现与验证。

## 用户补充口径

时间：2026-05-27 13:04 +0800
经办人：睡觉小分队
任务：T-20260527-8c2408dc / kernel-demo-random-runtime-symbolic
任务目标：同步用户关于随机尺寸与 IR 合同一致性的补充口径。
改动：记录用户补充要求：demo 尺寸需要 fixed-seed random；若 demo/维度是 static 合同，则生成 IR 中的静态大小必须等于本轮 fixed-seed 随机出的静态值，不得使用旧固定值，也不得让 IR 静态尺寸与 runtime 随机值不一致；dynamic demo 继续按计划保持运行时符号 / 输入合同。
验证：执行中；后续 pytest 与 9 demo gate 将按该口径检查 static IR shape/size 与随机静态值一致，dynamic IR 保持符号合同。
自检：该口径与计划目标一致，强化 static/dynamic 合同边界；当前未涉及 expectation/.skills/agents/standard/AGENTS/TODO/DONE 修改。
结论：继续 execute；若发现已写实现与该口径冲突，将记录 actual/spec/verdict 后再处理或回报。

## 用户纠偏：实现描述错误

时间：2026-05-27 13:32 +0800
经办人：睡觉小分队
任务：T-20260527-8c2408dc / kernel-demo-random-runtime-symbolic
任务目标：修正 demo 文件级说明、函数说明、stdout marker 与 pytest 断言中的 static/dynamic 随机语义。
改动：记录用户纠偏口径：大小随机是主语；每个 demo 的实际 shape/tile/conv attr 必须由 fixed-seed random profile 选出。static 不是“不随机”，而是 seed-selected value 进入编译期 static IR；dynamic 是编译 IR 保持 SymbolDim / 语义符号，runtime args/stdout 承载 seed-selected 真实值。禁止用“手写固定常量”或“static 不随机”的描述解释当前实现。
验证：执行中；已开始把文件说明、函数说明与 stdout marker 统一为 `profile=fixed-seed-random`、`static_ir=seed-selected-concrete`、`static_memory=seed-selected-concrete`、`dynamic_tile=symbolic-runtime`、`dynamic_ir=symbolic runtime=seed-selected`，并把 pytest 从手写 literal marker 改成独立 seed 重算后核对。
自检：该纠偏不改变公开 API，不涉及 expectation/.skills/agents/standard/AGENTS/TODO/DONE；如后续验证发现计划文本与该口径冲突，将按 actual/spec/verdict 回报。
结论：继续 execute，完成候选 diff 修正后复跑计划 gate。

## execute 收口记录

时间：2026-05-27 21:43 +0800
经办人：睡觉小分队
任务：T-20260527-8c2408dc / kernel-demo-random-runtime-symbolic
任务目标：完成 9 个 kernel demo fixed-seed random runtime scale、static/dynamic IR 合同、source/dump 一致性、pytest/9 demo/git diff check/敏感目录门禁闭环，并按用户纠偏修正文案和测试语义。

改动：
- 9 个 demo 脚本统一使用 fixed-seed random profile 描述和 stdout marker：static case 表达为 `static_ir=seed-selected-concrete` 或 `static_memory=seed-selected-concrete`，dynamic case 表达为 `dynamic_ir=symbolic runtime=seed-selected`。
- static case 的文件级说明、函数说明与 IR 断言改为“随机选出的具体值在 static IR 中具体化”，不再描述为手写固定常量或 static 不随机。
- dynamic case 保持编译入口 memory/tile 为 `SymbolDim` / 语义符号，runtime args/stdout 承载 seed-selected 真实值；conv2d dynamic 覆盖 `SH/SW/DH/DW/PT/PB/PL/PR` 与 tile runtime scalar。
- `conv2d/inputs_static_tile_dynamic.py`、`flash_attention/inputs_static_tile_dynamic.py`、`flash_attention/inputs_dynamic_tile_dynamic.py` 按计划使用 `run_lowering_demo(...) + ExecutionEngine(...)` 公开链路，避免 dynamic tile 在公开 dump 中静态化。
- pytest 从只看手写 marker 改为按 seed/range/candidate 独立重算 selected shape/tile/conv attr，并核对 stdout、first-ir、source dump marker 和 static/dynamic 边界。
- target script pytest 的 source dump 检查移动到每条脚本运行后立即核对，避免后续清理 dump 目录造成假红；同时把公开脚本 subprocess timeout 调整为 matmul 300s、conv2d/Flash 600s，断言语义不变。
- 删除 `flash_attention/inputs_static_tile_static.py` 中大体量 IR/source stdout 打印，只保留计划要求的 `[ARGS]` / `[CHECK]` marker，降低公开脚本 gate 的输出压力。

最小功能闭环：
- 9 个公开脚本均输出 seed、候选集合或范围、selected shape/tile、multi-tile/tail 和 `[CHECK]`。
- static demo：pytest 证明 seed-selected concrete value 出现在 IR memory/tile/conv attr 中。
- dynamic demo：pytest 证明 IR 入口保留 semantic symbols / `SymbolDim`，runtime seed-selected value 只出现在 stdout / runtime args，不静态化进入口 memory/tile type。
- symbolic compile 脚本校验 `run_lowering_demo(...)` 返回 source 与 `kernel/dump/<case>/source.cpp` 的关键 marker 一致。

验证：
- Diff 反推 pytest：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py test/kernel/test_flash_attention_symbolic_memory_genkernel.py`，exit=0，`13 passed, 1 warning`，锁定 9 demo seed 重算、static/dynamic IR、source dump 与公开脚本 gate。
- 语法检查：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel/matmul/inputs_static_tile_static.py kernel/matmul/inputs_static_tile_dynamic.py kernel/matmul/inputs_dynamic_tile_dynamic.py kernel/conv2d/inputs_static_tile_static.py kernel/conv2d/inputs_static_tile_dynamic.py kernel/conv2d/inputs_dynamic_tile_dynamic.py kernel/flash_attention/inputs_static_tile_static.py kernel/flash_attention/inputs_static_tile_dynamic.py kernel/flash_attention/inputs_dynamic_tile_dynamic.py test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py test/kernel/test_flash_attention_symbolic_memory_genkernel.py`，exit=0。
- 9 个公开脚本 gate：以下命令均 exit=0。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_static.py`：`shape=(M=166,K=217,N=172)`，`selected_tile=(M=72,N=56,K=48)`，absent/present `[CHECK]` 通过。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_static_tile_dynamic.py`：`shape=(M=197,K=178,N=184)`，`selected_tile=(72, 88, 56)`，absent/present `[CHECK]` 通过。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/matmul/inputs_dynamic_tile_dynamic.py`：`shape=(M=250,K=192,N=228)`，`selected_tile=(48, 96, 64)`，absent/present `[CHECK]` 通过。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_static_tile_static.py`：`input=(4, 49, 248, 232)`，`weight=(20, 49, 3, 5)`，`padding=(3,3,4,0)`，`selected_tile=(7,18,3,9,8)`，absent/present `[CHECK]` 通过。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_static_tile_dynamic.py`：`input=(4, 61, 254, 229)`，`weight=(21, 61, 3, 5)`，`padding=(4,3,4,3)`，`selected_tile=(7, 18, 3, 9, 8)`，absent/present `[CHECK]` 通过。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/conv2d/inputs_dynamic_tile_dynamic.py`：`input=(5, 60, 281, 243)`，`weight=(18, 60, 3, 5)`，`padding=(0, 4, 2, 0)`，`selected_tile=(7, 18, 3, 9, 8)`，absent/present `[CHECK]` 通过。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/flash_attention/inputs_static_tile_static.py`：`shape=(1, 8, 389, 48)`，`tile=(64,80)`，`[CHECK]` 通过。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/flash_attention/inputs_static_tile_dynamic.py`：`shape=(2, 8, 257, 80)`，`tile=(64, 80)`，`[CHECK]` 通过。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 kernel/flash_attention/inputs_dynamic_tile_dynamic.py`：`shape=(2, 8, 321, 80)`，`tile=(64, 80)`，`[CHECK]` 通过。
- 静态边界扫描：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py`，exit=0，`3 passed`。
- diff-scoped ctx / nested scan：计划书内 AST 脚本，exit=0，输出 `diff-scoped ctx/nested scan passed`。
- runner 签名核对：计划书内 `inspect.signature` 脚本，exit=0，输出 `runner signatures unchanged`。
- 格式检查：`git diff --check`，exit=0。
- 敏感目录门禁：
  - `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：空。
  - `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：空。
  - `git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：空。
- 合同验收：本计划无必过 expectation，未运行 expectation 作为通过依据，未修改 expectation。

Diff 反推自测：
- 改动文件为 `kernel/{matmul,conv2d,flash_attention}/inputs_*.py` 与 `test/kernel/test_*_symbolic_memory_genkernel.py`，反推测试为三组 kernel pytest、9 个公开脚本、py_compile、source dump marker、private API boundary gate、diff-scoped ctx/nested scan、runner signature gate。
- 三组 kernel pytest 覆盖实际 diff：seed 重算、static concrete IR、dynamic symbolic IR、stdout marker、公开 dump 与 source marker、公开脚本 subprocess gate。
- 9 个公开脚本覆盖实际执行链：NumPy reference / generated source compile / ExecutionEngine execution / `[CHECK]` 数值结果。

减法检查：
- 新增或改动 private callable 均为当前文件内测试/demo helper，已由 `test_private_api_boundaries.py` 证明不少于 5 行有效代码且无 private-to-private 调用链违规。
- 关键 private callable 范围：`_symbolic_compile_args`、`_assert_*_ir`、`_assert_source_dump_matches`、`_execute_*_source`、`_assert_outputs_close`、`_run_kernel_script`、`_assert_source_dump_contains` 等，均只服务当前文件公开 demo 或 pytest。
- 被替代旧逻辑：替换旧“static 固定/不随机”描述；替换 conv2d static_dynamic 与 Flash dynamic-tile 脚本旧 `run_numpy_demo(...)` dump 口径；删除 Flash static_static 的大体量 IR/source stdout 打印；移除 target script pytest 循环结束后再读 source dump 的脆弱检查方式。
- 保留旧逻辑依据：static_static 仍保留 `run_numpy_demo(...)` 公开入口，因为计划允许 static IR 具体化且脚本已用 seed-selected static value 证明；runner API 未改。

自检：
- 接口/API：未新增、删除、重命名公开 API；`kernel/runner.py` 签名未变。
- 边界/异常：static/dynamic IR 边界由 pytest 正反 marker 锁定；source dump 缺失、marker 缺失、IR 静态化/符号化错误会失败。
- 兼容性：9 个公开 demo 均 exit=0；公开脚本 stdout 保留 `[ARGS]` / `[CHECK]` 可读 marker。
- 实现遗漏/冗余：已按用户纠偏同步 demo 文件级说明、函数说明、stdout marker 和 pytest 断言；未发现仍使用“static 不随机”或“手写固定常量”口径。
- 注释准确性：文件/函数说明已改为 seed-selected static concrete 与 dynamic symbolic runtime 的表述。
- 复用/函数粒度：新增 helper 均为当前文件内局部逻辑；未跨文件调用非公开 helper。
- 输入输出/资源/性能：9 demo 使用计划锁定规模；删除大体量 stdout 输出；pytest 子进程 timeout 调高以覆盖全量组合运行资源波动。
- 并发：验证命令顺序运行公开 demo，未依赖并发状态。
- 测试有效性：三文件 pytest 和 9 demo gate 均已运行，测试会在 seed 漂移、IR 形态回退、source dump 缺失或公开脚本失败时失败。

结论：execute 已闭环，候选 diff 不含 expectation/.skills/agents/standard/AGENTS/TODO/DONE；可按计划级流程续接 review。

## review 复审记录

时间：2026-05-27 22:58 +0800
经办人：提莫炖蘑菇
任务：T-20260527-8c2408dc / kernel-demo-random-runtime-symbolic
任务目标：审查 fixed-seed random profile、static/dynamic IR 合同、source/dump 一致性、Diff 反推自测、9 demo gate、静态扫描与敏感目录门禁。

审查前置同步：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260527-kernel-demo-random-runtime-symbolic`
- 初始送审基线：`HEAD=1778f4f717b84dc46a6a889059fc8d6fdcef895b`，`origin/main=60ce5561d716948c93eebe40bbe10d69b467ba79`，`merge-base=1778f4f717b84dc46a6a889059fc8d6fdcef895b`。
- 首轮同步检查发现 worktree behind 1；`HEAD..origin/main` 仅含 execute-engine rebalance 相关文件与任务记录，和本任务候选 `kernel/{matmul,conv2d,flash_attention}/inputs_*.py`、`test/kernel/test_*_symbolic_memory_genkernel.py` 无重叠，已安全执行 `git merge --ff-only origin/main`。
- 复验期间 `origin/main` 又推进到 `eac2af53c6f6a67717114173d91c70b2af7ccf32`；新增主线 diff 为 kernel matmul dynamic acc decompose 相关 `kernel_gen/**`、`spec/**`、`test/passes/**` 等，和本任务候选文件无重叠，已再次安全执行 `git merge --ff-only origin/main`。
- 最终复审基线：`HEAD=origin/main=merge-base=eac2af53c6f6a67717114173d91c70b2af7ccf32`。

审查发现：
- 不通过：`test/kernel/test_matmul_symbolic_memory_genkernel.py`、`test/kernel/test_conv2d_symbolic_memory_genkernel.py`、`test/kernel/test_flash_attention_symbolic_memory_genkernel.py` 的公开脚本 gate 未按计划矩阵读取 9 个公开脚本产生的 `kernel/dump/<case>/01-first-ir.mlir`，且 `run_numpy_demo(...)` 的 static-static 公开 dump/source 覆盖缺失。计划书 `公开 dump 路径与 marker 矩阵` 明确要求读取公开脚本 dump，带 bias static script 要分别核对 absent / present 两个 case 的 dump 和 source，并在 S3 写明“运行公开脚本后读取公开 `kernel/dump/<case>/01-first-ir.mlir`”。当前三组 target script 测试只断言 stdout marker；`source_markers` 仅覆盖 static_dynamic / dynamic_dynamic 两类 symbolic compile 脚本，未覆盖 matmul static_static absent/present、conv2d static_static absent/present、flash_attention static_static 的 source marker，也没有覆盖任一公开脚本 `01-first-ir.mlir` 的正反 marker。对应代码位置：`test/kernel/test_matmul_symbolic_memory_genkernel.py:326-349`、`test/kernel/test_conv2d_symbolic_memory_genkernel.py:543-565`、`test/kernel/test_flash_attention_symbolic_memory_genkernel.py:477-498`。风险是 test-only `run_lowering_demo("test/...")` dump 或 stdout 仍可通过，而公开脚本真实 dump 回退为旧 static/dynamic 形态时不会被 pytest 捕获。

Diff 反推审查：
- 已核对候选 diff 范围：9 个 kernel demo 脚本与 3 个 `test/kernel/test_*_symbolic_memory_genkernel.py`，未纳入 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。
- 已核对计划书合同：本计划无必过 `expectation`，不以 `expectation` 作为通过依据；本轮未运行 `expectation`。
- 已复跑 Diff 反推 pytest：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py test/kernel/test_flash_attention_symbolic_memory_genkernel.py`，最终最新基线 exit=0，`13 passed, 1 warning`。
- 已复跑语法检查：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel/matmul/inputs_static_tile_static.py kernel/matmul/inputs_static_tile_dynamic.py kernel/matmul/inputs_dynamic_tile_dynamic.py kernel/conv2d/inputs_static_tile_static.py kernel/conv2d/inputs_static_tile_dynamic.py kernel/conv2d/inputs_dynamic_tile_dynamic.py kernel/flash_attention/inputs_static_tile_static.py kernel/flash_attention/inputs_static_tile_dynamic.py kernel/flash_attention/inputs_dynamic_tile_dynamic.py test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py test/kernel/test_flash_attention_symbolic_memory_genkernel.py`，exit=0。
- 已复跑 private boundary：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py`，exit=0，`3 passed`。
- 已复跑 diff-scoped ctx / nested scan：计划书 AST 脚本，exit=0，输出 `diff-scoped ctx/nested scan passed`。
- 已复跑 runner 签名 gate：计划书 `inspect.signature` 脚本，exit=0，输出 `runner signatures unchanged`。
- 已复跑格式与敏感目录门禁：`git diff --check` exit=0；`git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`、`git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`、`git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md` 均为空。

减法审查：
- 未发现候选 diff 修改敏感目录或新增公开 runner API。
- 未发现新增 ctx 能力探测、非装饰器嵌套函数或跨文件非公开 API 使用。
- 现有 private helper 边界由 `test/repo_conformance/test_private_api_boundaries.py` 通过证明；本轮阻断点不是 helper 规范，而是公开 dump 测试矩阵未闭合。

最小需改项：
- 退回 execute：补齐 9 个公开脚本 dump gate。运行公开脚本后，pytest 必须读取计划矩阵列出的真实公开 dump 路径：
  - `run_numpy_demo(...)` static-static：读取函数名子目录 `01-first-ir.mlir`，并分别核对 matmul/conv2d absent 与 present 两个 case 的根 `source.cpp`；Flash Attention static_static 也需核对根 `source.cpp`。
  - symbolic compile 脚本：继续核对根 `source.cpp`，同时读取公开脚本 case 根目录 `01-first-ir.mlir`，按计划要求检查入口 memory / tile 参数类型和对应 `symbol.for step`。
- 补齐后复跑三组 kernel pytest、9 个公开脚本 gate、py_compile、private boundary、diff-scoped ctx/nested scan、runner signature gate、git diff --check 和敏感目录三条门禁，并在任务记录更新 Diff 反推自测。

自检：
- 特殊情况：已在最新 `origin/main=eac2af53c6f6a67717114173d91c70b2af7ccf32` 同步现场复验，避免旧基线结论失效。
- 完整性：已审查计划书要求、候选 diff、任务记录和实际 pytest 断言路径；阻断项有明确文件位置和返工方式。
- 维护性/扩展性：要求补公开脚本 dump 矩阵，避免后续同类 demo 只测 test-only dump 或 stdout。
- 测试有效性：现有测试可跑通但未覆盖计划指定公开 dump 真源，因此不能放行。

结论：review 不通过，退回 execute；不得进入 archive_acceptance 或 merge。

## execute 返工收口记录

时间：2026-05-27 22:37 +0800
经办人：咯咯咯
任务：T-20260527-8c2408dc / kernel-demo-random-runtime-symbolic
任务目标：按 review 最小阻断项补齐 9 个公开脚本运行后的公开 dump `01-first-ir.mlir` 与 `source.cpp` 正反 marker gate，并复跑计划要求验证。

执行前阅读记录：
- 已读取最新个人提示词 `agents/codex-multi-agents/agents/咯咯咯/咯咯咯.prompt.md`、根 `AGENTS.md`、`agents/standard/协作执行通用规则.md`、`agents/standard/任务记录约定.md`。
- 已读取计划书 `ARCHITECTURE/plan/kernel_demo_random_runtime_symbolic_green_plan.md` 中公开 dump 路径与 marker 矩阵、S3/S4 验收设计和禁止修改面。
- 已读取本任务记录末尾 review 复审记录，确认最小阻断项为公开脚本 dump gate 未闭合。
- 当前 worktree：`/home/lfr/kernelcode_generate/wt-20260527-kernel-demo-random-runtime-symbolic`；记录文件：`agents/codex-multi-agents/log/task_records/2026/25/20260527-kernel-demo-random-runtime-symbolic.md`。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`；本轮未修改这些路径。
- latest main 核对：返工前 `HEAD=origin/main=merge-base=eac2af53c6f6a67717114173d91c70b2af7ccf32`；返工后执行 `git fetch origin`，再次核对 `HEAD=origin/main=merge-base=eac2af53c6f6a67717114173d91c70b2af7ccf32`，`git rev-list --left-right --count HEAD...origin/main` 输出 `0 0`。

返工收口：
- review 问题：公开脚本 gate 只验证 stdout 与部分 `source.cpp`，未读取 9 个公开脚本真实写出的 `kernel/dump/<case>/01-first-ir.mlir`，static-static `run_numpy_demo(...)` absent/present 根 `source.cpp` 覆盖也不完整。
- 实际修复：在三组 kernel pytest 内新增当前文件内 `_assert_first_ir_dump_contains(...)` helper，直接读取公开脚本生成的 `kernel/dump/<case>/01-first-ir.mlir`，核对入口 memory/tile 与 `symbol.for` step 正反 marker。
- matmul：`inputs_static_tile_static.py` 分别核对 absent/present 函数名子目录 first-ir 与根 `source.cpp`；`static_tile_dynamic` / `dynamic_tile_dynamic` 核对公开 case 根目录 first-ir/source，锁定 static memory、dynamic tile、dynamic memory 与 K loop step。
- conv2d：`inputs_static_tile_static.py` 分别核对 absent/present 函数名子目录 first-ir 与根 `source.cpp`；`static_tile_dynamic` / `dynamic_tile_dynamic` 核对公开 case 根目录 first-ir/source，锁定 static memory/KH/KW、tile symbols、dynamic memory/attrs 与 tile loop step。
- Flash Attention：`inputs_static_tile_static.py` 补根 `source.cpp` 与函数名子目录 first-ir；`static_tile_dynamic` / `dynamic_tile_dynamic` 核对公开 case 根目录 first-ir/source，锁定 memory、`BR/BC` tile 与 query/key loop step。

最小功能闭环：
- 9 个公开脚本测试均在运行脚本前清理对应 `kernel/dump/<case>/`，脚本 exit=0 后立即读取公开 dump 路径，不再用 `test/<op>/...` 临时 dump 或 stdout 代替公开 dump 真源。
- first-ir gate 包含正向 marker：`func.func` 入口、入口 memory 类型、入口 tile 参数、对应 `symbol.for step`。
- first-ir gate 包含反向 marker：static-static 不出现 dynamic tile symbol；static-dynamic 不把 runtime tile 数字写入 loop step；dynamic-dynamic 不把本次 runtime shape/tile 静态化到入口 memory/tile。
- static-static `run_numpy_demo(...)` 已覆盖 matmul/conv2d absent/present 两个 case 的函数名子目录 first-ir 与根 `source.cpp`；Flash static_static 已覆盖根 `source.cpp`。

验证：
- Diff 反推 pytest：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py test/kernel/test_flash_attention_symbolic_memory_genkernel.py`，exit=0，`13 passed, 1 warning in 411.55s`。断言锁定 9 个公开脚本 stdout、公开 first-ir、公开 source dump、static/dynamic IR 边界和 seed-selected profile。
- 9 个公开 demo 脚本：逐项执行 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 <script>`，以下均 exit=0：`kernel/matmul/inputs_static_tile_static.py`、`kernel/matmul/inputs_static_tile_dynamic.py`、`kernel/matmul/inputs_dynamic_tile_dynamic.py`、`kernel/conv2d/inputs_static_tile_static.py`、`kernel/conv2d/inputs_static_tile_dynamic.py`、`kernel/conv2d/inputs_dynamic_tile_dynamic.py`、`kernel/flash_attention/inputs_static_tile_static.py`、`kernel/flash_attention/inputs_static_tile_dynamic.py`、`kernel/flash_attention/inputs_dynamic_tile_dynamic.py`。
- 语法检查：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel/matmul/inputs_static_tile_static.py kernel/matmul/inputs_static_tile_dynamic.py kernel/matmul/inputs_dynamic_tile_dynamic.py kernel/conv2d/inputs_static_tile_static.py kernel/conv2d/inputs_static_tile_dynamic.py kernel/conv2d/inputs_dynamic_tile_dynamic.py kernel/flash_attention/inputs_static_tile_static.py kernel/flash_attention/inputs_static_tile_dynamic.py kernel/flash_attention/inputs_dynamic_tile_dynamic.py test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py test/kernel/test_flash_attention_symbolic_memory_genkernel.py`，exit=0。
- private boundary：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py`，exit=0，`3 passed in 1.52s`。
- diff-scoped ctx/nested scan：计划书 AST 脚本，exit=0，输出 `diff-scoped ctx/nested scan passed`。
- runner signature：计划书 `inspect.signature` 脚本，exit=0，输出 `runner signatures unchanged`。
- 格式检查：`git diff --check`，exit=0。
- 敏感目录门禁：`git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`、`git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`、`git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md` 均为空。
- 合同验收：计划书明确本计划无必过 `expectation`；本轮未运行 `expectation` 作为通过依据，未修改 `expectation/`。

Diff 反推自测：
- 实际候选 diff 覆盖 `kernel/{matmul,conv2d,flash_attention}/inputs_*.py`、`test/kernel/test_*_symbolic_memory_genkernel.py` 和任务记录；本轮返工实际改动集中在三组 `test/kernel` pytest 的公开 dump gate。
- 反推测试为三组 kernel pytest、9 个公开 demo 脚本、py_compile、private boundary、diff-scoped ctx/nested scan、runner signature、git diff check 和敏感目录门禁。
- 新增 first-ir gate 会在公开脚本未写 dump、dump 路径回退、static/dynamic IR 入口错误、symbol.for step 静态化或 source.cpp 缺关键 marker 时失败，覆盖 review 指出的测试有效性缺口。

减法检查：
- 新增 private callable：`_assert_first_ir_dump_contains(...)`，分别位于 `test/kernel/test_matmul_symbolic_memory_genkernel.py`、`test/kernel/test_conv2d_symbolic_memory_genkernel.py`、`test/kernel/test_flash_attention_symbolic_memory_genkernel.py`；均为当前文件内 helper，服务公开脚本 pytest gate，均超过 5 行有效代码，且不调用其它 private callable。
- 本轮未新增公开 API，未改 runner 签名，未新增跨文件非公开 helper 调用。
- 被替代旧逻辑：target script 测试中“只看 stdout / 仅部分 source.cpp”作为公开 dump 证明的不足，已替换为脚本运行后读取公开 first-ir/source 的矩阵化断言。
- 保留旧逻辑依据：既有 demo 实现、seed-selected profile、公开脚本执行链和原有 first-ir scratch/accumulator 测试仍有效；本轮仅补最小 dump gate，不扩大实现范围。

自检：
- 接口/API：未新增、删除、重命名公开 API；`kernel/runner.py` 签名核对通过。
- 边界/异常：脚本运行失败、公开 first-ir/source 缺失、marker 缺失、runtime 数字错误进入 dynamic 入口或 static tile 错误符号化都会触发 pytest 失败。
- 兼容性：9 个公开 demo 均 exit=0；原三组 kernel pytest仍全部通过。
- 实现遗漏/冗余：已补齐 review 点名的 9 个公开脚本 first-ir、static-static absent/present source、Flash static_static source；未发现仍只依赖 test-only dump 的新增 gate。
- 注释准确性：新增 helper docstring 明确只读取公开 dump，不把 stdout 当作 dump 证明。
- 复用/函数粒度：新增 helper 为当前文件局部，避免跨文件 helper；字典化 marker 保持每条公开脚本路径可追踪。
- 输入输出/资源/性能：测试仍按计划固定 seed 与预算运行；无并发共享状态；运行前清理 dump 避免旧文件污染。
- 测试有效性：三组 pytest 已证明新增 gate 在真实公开脚本后读取实际 dump；9 demo 单独复跑证明公开入口可执行。

结论：execute 返工已收口，候选 diff 不含 `expectation/.skills/agents/standard/AGENTS/TODO/DONE`；可按计划级流程续接 review。

## review 复审记录（公开脚本 dump gate 返工）

时间：2026-05-27 22:59 +0800
经办人：提莫炖蘑菇
任务：T-20260527-8c2408dc / kernel-demo-random-runtime-symbolic
任务目标：复审公开脚本 dump gate、三组 kernel pytest、9 demo、py_compile、private boundary、diff-scoped ctx/nested、runner signature、git diff check、敏感目录门禁与任务记录。

审查前置同步：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260527-kernel-demo-random-runtime-symbolic`
- 计划书：主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/kernel_demo_random_runtime_symbolic_green_plan.md`
- `git fetch origin` 后核对：`HEAD=eac2af53c6f6a67717114173d91c70b2af7ccf32`，`origin/main=eac2af53c6f6a67717114173d91c70b2af7ccf32`，`merge-base=eac2af53c6f6a67717114173d91c70b2af7ccf32`，`git rev-list --left-right --count HEAD...origin/main` 输出 `0 0`。
- 当前候选 diff 为 9 个 `kernel/{matmul,conv2d,flash_attention}/inputs_*.py`、3 个 `test/kernel/test_*_symbolic_memory_genkernel.py` 与本任务记录；无需要合并的 latest main 偏移，无冲突或覆盖风险。

审查发现：
- 未发现阻断项。
- 上轮阻断项已收口：三组 `test/kernel/test_*_symbolic_memory_genkernel.py` 已新增公开 `source.cpp` 与 `01-first-ir.mlir` 读取 helper，公开脚本运行前清理对应 `kernel/dump/<case>/`，脚本 exit=0 后读取真实公开 dump 路径；static-static absent/present、static-dynamic 和 dynamic-dynamic 均按计划矩阵核对入口 memory / tile / `symbol.for step` 正反 marker。
- 本轮为 review 退回后的复审；未发现新增问题、重复阻断或范围扩大。

Diff 反推审查：
- 被审 diff 文件：
  - `kernel/matmul/inputs_static_tile_static.py`
  - `kernel/matmul/inputs_static_tile_dynamic.py`
  - `kernel/matmul/inputs_dynamic_tile_dynamic.py`
  - `kernel/conv2d/inputs_static_tile_static.py`
  - `kernel/conv2d/inputs_static_tile_dynamic.py`
  - `kernel/conv2d/inputs_dynamic_tile_dynamic.py`
  - `kernel/flash_attention/inputs_static_tile_static.py`
  - `kernel/flash_attention/inputs_static_tile_dynamic.py`
  - `kernel/flash_attention/inputs_dynamic_tile_dynamic.py`
  - `test/kernel/test_matmul_symbolic_memory_genkernel.py`
  - `test/kernel/test_conv2d_symbolic_memory_genkernel.py`
  - `test/kernel/test_flash_attention_symbolic_memory_genkernel.py`
- 公开 dump gate 人工核对：`_run_kernel_script(...)` 清理公开 dump 目录；`_assert_source_dump_contains(...)` 读取 `kernel/dump/<case>/source.cpp`；`_assert_first_ir_dump_contains(...)` 读取 `kernel/dump/<case>/01-first-ir.mlir` 或 static-static 函数名子目录 first-ir，覆盖 matmul/conv2d absent + present bias 和 Flash Attention static/static-dynamic/dynamic-dynamic 三类 case。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py test/kernel/test_flash_attention_symbolic_memory_genkernel.py`：exit=0，`13 passed, 1 warning in 382.15s`。
- 9 个公开 demo 脚本逐项复跑均 exit=0：`kernel/matmul/inputs_static_tile_static.py`、`kernel/matmul/inputs_static_tile_dynamic.py`、`kernel/matmul/inputs_dynamic_tile_dynamic.py`、`kernel/conv2d/inputs_static_tile_static.py`、`kernel/conv2d/inputs_static_tile_dynamic.py`、`kernel/conv2d/inputs_dynamic_tile_dynamic.py`、`kernel/flash_attention/inputs_static_tile_static.py`、`kernel/flash_attention/inputs_static_tile_dynamic.py`、`kernel/flash_attention/inputs_dynamic_tile_dynamic.py`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel/matmul/inputs_static_tile_static.py kernel/matmul/inputs_static_tile_dynamic.py kernel/matmul/inputs_dynamic_tile_dynamic.py kernel/conv2d/inputs_static_tile_static.py kernel/conv2d/inputs_static_tile_dynamic.py kernel/conv2d/inputs_dynamic_tile_dynamic.py kernel/flash_attention/inputs_static_tile_static.py kernel/flash_attention/inputs_static_tile_dynamic.py kernel/flash_attention/inputs_dynamic_tile_dynamic.py test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py test/kernel/test_flash_attention_symbolic_memory_genkernel.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py`：exit=0，`3 passed in 1.50s`。
- diff-scoped ctx / nested scan：exit=0，输出 `diff-scoped ctx/nested scan passed`。
- runner signature gate：exit=0，输出 `runner signatures unchanged`。
- `git diff --check`：exit=0。
- 敏感目录门禁：`git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`、`git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`、`git status --short --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`、`git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md` 均为空。
- 合同验收：本计划无必过 `expectation`；本轮未运行 `expectation` 作为通过依据，候选 diff 未修改 `expectation/`。

减法审查：
- 本轮新增/调整的公开 dump gate 替代了上轮“仅 stdout / 部分 source marker / test-only dump 可通过”的旧测试证明方式；旧不足已由公开 `source.cpp` 与公开 `01-first-ir.mlir` 矩阵断言替换。
- 本轮未新增、删除或修改公开 API；未修改 `kernel/runner.py` 签名。
- 私有 helper 审查：重点核对本轮新增的 `_assert_source_dump_contains(...)`、`_assert_first_ir_dump_contains(...)`、`_run_kernel_script(...)` 公开 dump gate helper，以及各 demo 内 `_assert_source_dump_matches(...)` / `_execute_*` / `_assert_outputs_close(...)` 等当前文件内 helper；均为当前文件内使用，未跨文件导入，新增 dump gate helper有效代码不少于 5 行且无 private-to-private 调用链。`test/repo_conformance/test_private_api_boundaries.py` 已通过。
- diff-scoped ctx/nested scan 未发现 `hasattr/getattr/callable(getattr)` 上下文能力探测或非装饰器嵌套函数。
- 保留旧逻辑依据：static-static 仍保留 `run_numpy_demo(...)`，符合计划矩阵；symbolic compile case 使用 `run_lowering_demo(...) + ExecutionEngine(...)`，不扩展 runner API。

自检：
- 特殊情况：已在 latest `origin/main=eac2af53c6f6a67717114173d91c70b2af7ccf32` 同步现场复审，避免旧基线通过结论失效。
- 完整性：已核对计划矩阵、执行记录、实际候选 diff、公开 dump gate、三组 pytest、9 demo、静态边界扫描和敏感目录门禁。
- 维护性：新增 dump/source 断言集中在各测试文件内，路径矩阵清晰，未引入跨文件测试 helper。
- 测试有效性：pytest 现在直接读取公开脚本产物，不再只依赖 stdout 或 test-only dump；公开脚本真实执行也已单独复跑。
- 残余风险：无已知阻断；Flash/conv2d 脚本耗时较长，但已在本轮复跑通过。

结论：review 通过；这是计划级任务，应续接 `archive_acceptance / 计划书入档验收`，不得直接进入 merge。

## archive_acceptance / 计划书入档验收记录

时间：2026-05-27 23:01 +0800
经办人：提莫炖蘑菇
任务：T-20260527-8c2408dc / kernel-demo-random-runtime-symbolic
任务目标：核对计划级 review 通过后的最新同步现场、任务记录、Diff 反推审查、公开脚本 dump gate、pytest/9 demo/静态门禁、敏感目录空 diff 和可入档性。

最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260527-kernel-demo-random-runtime-symbolic`
- `git fetch origin` 后核对：`HEAD=eac2af53c6f6a67717114173d91c70b2af7ccf32`，`origin/main=eac2af53c6f6a67717114173d91c70b2af7ccf32`，`merge-base=eac2af53c6f6a67717114173d91c70b2af7ccf32`，`git rev-list --left-right --count HEAD...origin/main` 输出 `0 0`。
- 候选 diff 范围：9 个 `kernel/{matmul,conv2d,flash_attention}/inputs_*.py`、3 个 `test/kernel/test_*_symbolic_memory_genkernel.py`，以及本任务记录 `agents/codex-multi-agents/log/task_records/2026/25/20260527-kernel-demo-random-runtime-symbolic.md`。任务记录当前为 untracked，merge 阶段必须与代码/test 同批纳入。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md` 均无 tracked / staged / untracked / ignored 变更。

入档核对：
- 计划书流程：该任务为计划级任务，执行链为 `execute -> review -> archive_acceptance -> merge/归档`；review 已通过，未直接进入 merge。
- 计划正文与任务记录一致：本计划无新增/修改公开 API；本计划无必过 `expectation`，任务记录已明确未以 `expectation` 作为通过依据。
- 上轮 review 退回项闭合：公开脚本 dump gate 已补齐，三组 pytest 现在直接读取公开 `kernel/dump/<case>/source.cpp` 与公开 `01-first-ir.mlir`，覆盖 static-static absent/present、static-dynamic、dynamic-dynamic 的正反 marker。
- Diff 反推审查完整：review 记录已列明候选 diff、pytest/9 demo/py_compile/private boundary/ctx-nested/runner signature/diff check/敏感目录门禁结果。
- 减法审查完整：review 记录已写明旧的 stdout / 部分 source / test-only dump 证明方式被公开 source + first-ir 矩阵断言替代；未发现未说明保留的旧证明路径。
- 私有 helper 审查完整：新增 dump gate helper 为当前文件内 helper，未跨文件导入；private boundary pytest 通过；未发现新增 ctx 能力探测或非装饰器嵌套函数。

验证复核：
- 直接采用同一 latest 基线下刚完成的 review 复跑结果：三组 kernel pytest `13 passed, 1 warning`；9 个公开 demo 脚本均 exit=0；py_compile exit=0；private boundary `3 passed`；diff-scoped ctx/nested scan exit=0；runner signature gate exit=0；`git diff --check` exit=0。
- 入档阶段补充核对命令：
  - `git fetch origin && git rev-list --left-right --count HEAD...origin/main`：exit=0，输出 `0 0`。
  - `git diff --name-only`：仅列计划内 kernel/test 文件。
  - `git diff --cached --name-only`：空。
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：空。
- 合同验收：无当前必过 `expectation`；未运行 `expectation` 作为通过依据。

自检：
- 最新基线、执行目录、候选 diff、任务记录、review 结论与敏感目录门禁均已核对。
- 未发现 review 结论缺失、Diff 反推审查缺失、禁止目录 diff、expectation 越权或公开 API 未确认变更。
- 剩余合并要求：merge 阶段必须把本任务记录与代码/test 同批合入，不得只合业务文件。

结论：archive_acceptance / 计划书入档验收通过；可续接 merge/归档。merge 必须同批纳入任务记录与候选代码/test。

## merge 记录：李白

时间：`2026-05-27 23:04 +0800`
经办人：`李白`
任务：`T-20260527-8c2408dc / kernel-demo-random-runtime-symbolic`
任务目标：合入已通过 review 与 archive_acceptance 的 9 个 kernel demo、3 个 kernel pytest 与同批任务记录，保持 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md` 不进入候选 diff。

合并前核对：
- 来源 worktree：`/home/lfr/kernelcode_generate/wt-20260527-kernel-demo-random-runtime-symbolic`
- 来源分支：`task/kernel-demo-random-runtime-symbolic`
- 最新基线：`HEAD=origin/main=eac2af53c6f6a67717114173d91c70b2af7ccf32`
- 计划书：`ARCHITECTURE/plan/kernel_demo_random_runtime_symbolic_green_plan.md`
- `review` 复审结论：`2026-05-27 22:59 +0800` 通过，无剩余阻断项。
- `archive_acceptance` 结论：`2026-05-27 23:01 +0800` 通过，要求 merge 同批纳入代码/test 与本任务记录。
- 本计划无必过 `expectation`，merge 记录不把 expectation 写作通过依据。

实际合入文件：
- `kernel/matmul/inputs_static_tile_static.py`
- `kernel/matmul/inputs_static_tile_dynamic.py`
- `kernel/matmul/inputs_dynamic_tile_dynamic.py`
- `kernel/conv2d/inputs_static_tile_static.py`
- `kernel/conv2d/inputs_static_tile_dynamic.py`
- `kernel/conv2d/inputs_dynamic_tile_dynamic.py`
- `kernel/flash_attention/inputs_static_tile_static.py`
- `kernel/flash_attention/inputs_static_tile_dynamic.py`
- `kernel/flash_attention/inputs_dynamic_tile_dynamic.py`
- `test/kernel/test_matmul_symbolic_memory_genkernel.py`
- `test/kernel/test_conv2d_symbolic_memory_genkernel.py`
- `test/kernel/test_flash_attention_symbolic_memory_genkernel.py`
- `agents/codex-multi-agents/log/task_records/2026/25/20260527-kernel-demo-random-runtime-symbolic.md`

验证：
- `git fetch --prune origin`：exit=0，主仓与任务 worktree 均已对齐 `origin/main=eac2af53c6f6a67717114173d91c70b2af7ccf32`。
- `git diff --check`：exit=0。
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。
- `git ls-files --others --exclude-standard -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：exit=0，无输出。
- `archive_acceptance` 已在同一 latest 基线记录通过：三组 kernel pytest `13 passed, 1 warning`；9 个公开 demo 脚本均 exit=0；`py_compile` exit=0；private boundary `3 passed`；diff-scoped ctx/nested scan、runner signature gate、`git diff --check` 与敏感目录门禁均通过。

冲突处理：
- 无冲突；任务 worktree 已与 latest `origin/main` 同步，候选为工作区 diff。

敏感文件核对：
- `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md` 未进入候选 diff。
- 本轮未修改、复制、移动、新建或删除 `expectation/`；本计划无必过 expectation。

剩余风险：
- 未发现 merge 阻断项。
- 合并提交号在 push 后回报，不再为补提交号追加任务记录提交。

结论：`merge 可执行`；代码/test 与本任务记录将同批暂存、提交并推送到 `origin/main`，随后执行 `-done`。
