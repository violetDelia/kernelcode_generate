时间：2026-04-26 21:42 +0800
经办人：朽木露琪亚
任务：T-20260426-b41011d8 / S4 build
任务目标：为 execute_engine / include 收口 class API 简表、文件说明、公开 API 清单、helper 清单和测试公开入口，并跑通对应 pytest
执行前阅读记录：已读 [TODO.md](/home/lfr/kernelcode_generate/TODO.md) 本任务行、[ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md) S4 正文、[AGENTS.md](/home/lfr/kernelcode_generate/AGENTS.md)、[agents/standard/实现文件规范.md](/home/lfr/kernelcode_generate/agents/standard/实现文件规范.md)、[agents/standard/任务记录约定.md](/home/lfr/kernelcode_generate/agents/standard/任务记录约定.md)、相关 spec [spec/execute_engine/execute_engine.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/spec/execute_engine/execute_engine.md)、[spec/execute_engine/execute_engine_api.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/spec/execute_engine/execute_engine_api.md)、[spec/execute_engine/execute_engine_target.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/spec/execute_engine/execute_engine_target.md)、[spec/include/api/Core.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/spec/include/api/Core.md)、[spec/include/api/Arch.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/spec/include/api/Arch.md)、[spec/include/api/Memory.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/spec/include/api/Memory.md)、[spec/include/api/Dma.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/spec/include/api/Dma.md)、[spec/include/api/Kernel.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/spec/include/api/Kernel.md)、[spec/include/api/cost/Core.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/spec/include/api/cost/Core.md)、[spec/include/api/cost/Dma.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/spec/include/api/cost/Dma.md)、[spec/include/api/cost/Kernel.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/spec/include/api/cost/Kernel.md)、[spec/include/npu_demo/npu_demo.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/spec/include/npu_demo/npu_demo.md)；已读测试入口 [test/execute_engine/test_execute_engine_compile.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/test/execute_engine/test_execute_engine_compile.py)、[test/execute_engine/test_execute_engine_private_helpers.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/test/execute_engine/test_execute_engine_private_helpers.py)、`test/include/**`；已核对当前 worktree 原本不存在，已在最新 `main` 基线上创建指定现场。
最小功能闭环：1）为 `kernel_gen/execute_engine` 的公开模块补齐文件级 `API 列表 / helper 清单`；2）为 `include/api` 与 `include/npu_demo` 中 class/聚合入口及 `include/api` 纯函数声明头补齐文件说明与公开 API 索引；3）把 `test/execute_engine` 中直连私有 helper 的测试改为只测 `default_compiler / build_compile_command / build_compile_unit / compile_source / needs_entry_shim / build_entry_shim_source / target_includes` 这些公开 API；4）删除对 `kernel_gen.execute_engine.execution_engine.compile_source` 的内部 monkeypatch 断言。
改动：
- 更新 [kernel_gen/execute_engine/__init__.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/kernel_gen/execute_engine/__init__.py)、[kernel_gen/execute_engine/compiler.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/kernel_gen/execute_engine/compiler.py)、[kernel_gen/execute_engine/entry_shim_builder.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/kernel_gen/execute_engine/entry_shim_builder.py)、[kernel_gen/execute_engine/execution_engine.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/kernel_gen/execute_engine/execution_engine.py)、[kernel_gen/execute_engine/target_registry.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/kernel_gen/execute_engine/target_registry.py) 文件头，补齐公开 API 签名与 helper 清单。
- 更新 [include/api/Core.h](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/include/api/Core.h)、[include/api/Arch.h](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/include/api/Arch.h)、[include/api/Memory.h](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/include/api/Memory.h)、[include/api/Dma.h](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/include/api/Dma.h)、[include/api/Kernel.h](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/include/api/Kernel.h)、[include/api/cost/Core.h](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/include/api/cost/Core.h)、[include/api/cost/Dma.h](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/include/api/cost/Dma.h)、[include/api/cost/Kernel.h](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/include/api/cost/Kernel.h) 文件头，补齐公开 API 清单。
- 更新 [include/npu_demo/Core.h](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/include/npu_demo/Core.h)、[include/npu_demo/Arch.h](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/include/npu_demo/Arch.h)、[include/npu_demo/Memory.h](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/include/npu_demo/Memory.h)、[include/npu_demo/npu_demo.h](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/include/npu_demo/npu_demo.h) 文件头，补齐 class/聚合入口的公开 API 简表与 helper 清单。
- 更新 [test/execute_engine/test_execute_engine_private_helpers.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/test/execute_engine/test_execute_engine_private_helpers.py)，去掉全部跨文件私有 helper 导入，改成公开 target API 覆盖。
- 更新 [test/execute_engine/test_execute_engine_compile.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/test/execute_engine/test_execute_engine_compile.py)，删除对内部 `compile_source` 绑定的 monkeypatch 失败路径测试。
验证：
- `pytest -q test/execute_engine test/include -ra` -> `107 passed`
- `python3 -m py_compile kernel_gen/execute_engine/__init__.py kernel_gen/execute_engine/compiler.py kernel_gen/execute_engine/entry_shim_builder.py kernel_gen/execute_engine/execution_engine.py kernel_gen/execute_engine/target_registry.py test/execute_engine/test_execute_engine_compile.py test/execute_engine/test_execute_engine_private_helpers.py` -> 通过
- `git diff --check` -> 通过
- `rg -n 'from kernel_gen\\.execute_engine\\.[A-Za-z_]+ import [^#\\n]*\\b_[A-Za-z]|import kernel_gen\\.execute_engine\\.[A-Za-z_]+ as .*|monkeypatch\\.setattr\\(\"kernel_gen\\.execute_engine\\.[^\"]+\\._|monkeypatch\\.setattr\\(\"kernel_gen\\.execute_engine\\.[^\"]+\", .*_[A-Za-z]' test/execute_engine test/include` -> 无命中
Diff 反推自测：本轮 diff 覆盖 `kernel_gen/execute_engine/**` 文件级说明、`include/api/**` 与 `include/npu_demo/**` 头文件说明、`test/execute_engine/test_execute_engine_private_helpers.py` 与 `test/execute_engine/test_execute_engine_compile.py`；反推测试选择 `pytest -q test/execute_engine test/include -ra` 作为公开 API 回归主入口，并辅以 `py_compile`、私有导入扫描与 `git diff --check`；结果全部通过。
合同验收（如适用）：未执行 `expectation`；本轮任务明确要求 `expectation` 只读不可写，且 `Diff 反推自测` 不把 `expectation` 计入测试。
自检：已读完整阶段、计划正文、全局验收设计、相关 spec/test/实现与任务约束；未修改 `expectation`、`.skills` 或其他越权目录；最小闭环已完成；已按实际 diff 反推 `pytest` 与脚本自检；已把 class 场景的文件头 API 简表补到 `execute_engine` 与 `include` 相关入口；测试入口已切到公开 API，未再跨文件调用非公开 API；注释、示例、API 列表与当前实现一致；未新增公开接口，也未通过别名/反射/包装转发使用当前文件之外的非公开 API；未发现已知逻辑 bug、无效断言、资源泄漏或未处理的回归失败。
结论：当前 build 已完成，任务记录已写回本 worktree；下一步按 TODO 继续执行 `-next -auto -type review` 并回报管理员。

---

时间：2026-04-26 21:49 +0800
经办人：提莫炖蘑菇
任务：T-20260426-b41011d8 / S4 review
任务目标：复核 execute_engine / include 本轮文件说明、class API 简表、公开 API 清单、helper 边界与公开测试入口收口结果
执行前阅读记录：已读 [TODO.md](/home/lfr/kernelcode_generate/TODO.md) 本任务行、[ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md) S4 正文与全局完成态/验收设计、当前任务记录、相关 spec [spec/execute_engine/execute_engine.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/spec/execute_engine/execute_engine.md)、[spec/execute_engine/execute_engine_api.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/spec/execute_engine/execute_engine_api.md)、[spec/execute_engine/execute_engine_target.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/spec/execute_engine/execute_engine_target.md)、[spec/include/api/Memory.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/spec/include/api/Memory.md)，以及当前 diff 中的实现/头文件/测试入口。
真实审查：
- 逐项核对当前 diff 的 19 个文件，重点检查 [`kernel_gen/execute_engine/compiler.py`](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/kernel_gen/execute_engine/compiler.py)、[`kernel_gen/execute_engine/entry_shim_builder.py`](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/kernel_gen/execute_engine/entry_shim_builder.py)、[`kernel_gen/execute_engine/target_registry.py`](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/kernel_gen/execute_engine/target_registry.py) 的文件级 `API 列表 / helper 清单` 与对应 spec 是否一致。
- 核对 [`test/execute_engine/test_execute_engine_private_helpers.py`](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/test/execute_engine/test_execute_engine_private_helpers.py) 与 [`test/execute_engine/test_execute_engine_compile.py`](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/test/execute_engine/test_execute_engine_compile.py) 是否只连接 spec 明确定义的公开 API；现场确认其直接导入的 `default_compiler / build_compile_command / build_compile_unit / compile_source / needs_entry_shim / build_entry_shim_source / target_includes` 均已在 [`spec/execute_engine/execute_engine_target.md`](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/spec/execute_engine/execute_engine_target.md) 定义。
- 重点抽查 [`include/api/Memory.h`](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/include/api/Memory.h) 与 [`spec/include/api/Memory.md`](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/spec/include/api/Memory.md) 的公开口径一致性，确认文件级 `API 列表` 是否完整覆盖当前实现暴露的公开符号。
Diff 反推审查：
- `pytest -q test/execute_engine test/include -ra` -> `107 passed`
- `rg -n "from kernel_gen\\.execute_engine\\.[A-Za-z0-9_]+ import _|from kernel_gen\\.execute_engine\\.[A-Za-z0-9_]+ import .*_[A-Za-z]|import kernel_gen\\.execute_engine\\.[A-Za-z0-9_]+ as .*_|\\._[A-Za-z]" test/execute_engine test/include` -> 未发现测试直连 `_private` 符号
- `git diff --check` -> 通过
自检：
- 当前 review 结论只基于实际 diff、相关 spec 和现场测试结果。
- 未把 `expectation` 计入 `Diff 反推审查`，也未修改 `expectation`。
- 已按新口径检查“新增未在 spec 定义的公开接口 / 跨文件调用非公开 API / 测试直连非 API 接口”，本轮未命中这三类问题。
可改进点：
- [`include/api/Memory.h`](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/include/api/Memory.h) 的文件级 `API 列表` 当前漏列了实现中已经公开的模板参数简写常量：`GM`、`SM`、`LM`、`TSM`、`TLM1`、`TLM2`、`TLM3`（实现见同文件 [#L113](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/include/api/Memory.h#L113) 起）。
- 这组常量不是内部 helper；[`spec/include/api/Memory.md`](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/spec/include/api/Memory.md#L125) 已明确允许使用 `GM/SM/LM/TSM/TLM1/TLM2/TLM3` 作为等价常量，因此当前文件级 `API 列表` 与实现、spec 不一致。
结论：需修改。当前 diff 的公开测试入口与 helper 边界已基本收口，但 [`include/api/Memory.h`](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/include/api/Memory.h) 的文件级 `API 列表` 尚未完整覆盖已公开实现，未满足“build 改动功能实现文件时必须同步维护文件级 API 列表”的硬规则；应先补齐这组公开常量后再进入 merge。

---

时间：2026-04-26 21:50 +0800
经办人：朽木露琪亚
任务：T-20260426-b41011d8 / S4 build 修复回合
任务目标：按 review 退回项补齐 [`include/api/Memory.h`](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/include/api/Memory.h) 文件级 `API 列表` 中遗漏的公开常量 `GM/SM/LM/TSM/TLM1/TLM2/TLM3`
改动：
- 更新 [include/api/Memory.h](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/include/api/Memory.h)，在文件级 `API 列表` 中补齐 `inline constexpr MemorySpace GM/SM/LM/TSM/TLM1/TLM2/TLM3` 七个公开常量，保持文件头索引与当前实现、spec 一致。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/include/api/test_memory.py -ra` -> `5 passed`
- `git diff --check` -> 通过
Diff 反推自测：本轮 diff 只涉及 [include/api/Memory.h](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/include/api/Memory.h) 的文件级公开 API 索引修复；反推测试选择直接覆盖该头文件公开常量与 `Memory` 公开入口的 [test/include/api/test_memory.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/test/include/api/test_memory.py)，并辅以 `git diff --check` 验证补丁格式；结果全部通过。
真实自检：
- 已确认本轮只补 review 指出的文件级 `API 列表` 漏项，没有新增公开接口、没有改动实现语义、没有跨文件调用任何非公开 API。
- 已核对 [spec/include/api/Memory.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/spec/include/api/Memory.md) 中 `GM/SM/LM/TSM/TLM1/TLM2/TLM3` 的公开口径，当前文件头索引已与 spec、实现一致。
结论：review 退回项已收口，可以按 TODO 继续流转到下一轮 review。

---

时间：2026-04-26 21:55 +0800
经办人：不要啊教练
任务：T-20260426-b41011d8 / S4 review 复审
任务目标：复核 [include/api/Memory.h](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/include/api/Memory.h) 文件级 API 列表补齐 `GM/SM/LM/TSM/TLM1/TLM2/TLM3` 后的收口结果，并确认 `execute_engine / include` 本轮公开 API 清单、helper 边界与公开测试入口不回退
执行前阅读记录：已读 [TODO.md](/home/lfr/kernelcode_generate/TODO.md) 本任务行、[ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md) S4 正文、当前任务记录、[AGENTS.md](/home/lfr/kernelcode_generate/AGENTS.md)、[spec/include/api/Memory.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/spec/include/api/Memory.md)、`kernel_gen/execute_engine/**` 当前 diff 文件与 `test/execute_engine` / `test/include` 公开测试入口。
真实审查：
- 逐项核对当前 diff 中的 `execute_engine`、`include/api`、`include/npu_demo` 与对应公开测试入口，重点复查 [include/api/Memory.h](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/include/api/Memory.h) 文件头 API 简表、[spec/include/api/Memory.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/spec/include/api/Memory.md) API 列表与“限制与边界”、以及 [test/include/api/test_memory.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/test/include/api/test_memory.py) 的公开测试用法。
- 复查结果：`execute_engine` 侧未见新的跨文件非公开 API 调用，`test/execute_engine` 当前直连的 `default_compiler / build_compile_command / build_compile_unit / compile_source / needs_entry_shim / build_entry_shim_source / target_includes` 仍有对应 spec 定义；`include/api/Memory.h` 文件级 API 简表已补齐 `GM/SM/LM/TSM/TLM1/TLM2/TLM3`，但 `Memory` 公开合同仍未完全收口。
Diff 反推审查：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include:/home/lfr/kernelcode_generate pytest -q test/execute_engine test/include -ra` -> `107 passed`
- `rg -n "from kernel_gen\\.execute_engine\\.[A-Za-z0-9_]+ import _|from kernel_gen\\.execute_engine\\.[A-Za-z0-9_]+ import .*_[A-Za-z]|\\.linear_offset\\(|\\.at\\(" test/execute_engine test/include` -> 命中 [test/include/api/test_memory.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/test/include/api/test_memory.py:177)、[:180](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/test/include/api/test_memory.py:180)、[:183](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/test/include/api/test_memory.py:183) 的 `linear_offset/at` 直连；`execute_engine` 子集未见 `_private` 直连
- `git diff --check` -> 通过
合同验收：未执行 `expectation`。本轮仅复核实现 / spec / pytest 的公开 API 清单与测试边界，`expectation` 继续只作合同验收资产单列，不计入 `Diff 反推审查`。
自检：已按最新口径检查“新增未在 spec 明确定义的公开接口 / 跨文件调用非公开 API / 测试直连非 API 接口 / 文件级 API 列表是否与实现一致”。本轮命中后两项问题，因此不予通过。
可改进点：
- [spec/include/api/Memory.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/spec/include/api/Memory.md:13) 的 `API 列表` 仍未列出 `GM/SM/LM/TSM/TLM1/TLM2/TLM3` 七个公开常量；当前 spec 正文 [#L125](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/spec/include/api/Memory.md#L125) 已承认这组常量允许作为等价常量，文件级 API 索引却还没同步，和 [include/api/Memory.h](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/include/api/Memory.h:6) 的当前公开清单不一致。
- [test/include/api/test_memory.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/test/include/api/test_memory.py:177) / [:180](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/test/include/api/test_memory.py:180) / [:183](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/test/include/api/test_memory.py:183) 仍直接测试 `linear_offset()` / `at()`；但 [spec/include/api/Memory.md:69](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/spec/include/api/Memory.md:69) 已明确这组辅助接口“不属于本轮稳定公开合同”。按当前审查规则，测试不得直连非 API 接口，这一项必须先收回。
- 同时 [include/api/Memory.h](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/include/api/Memory.h:460) / [:478](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/include/api/Memory.h:478) / [:496](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/include/api/Memory.h:496) 仍把 `linear_offset/at` 放在 public 区域，而文件级 API 简表没有列出它们；要么将其纳入 spec 与 API 简表，要么从公开测试入口退出，不能维持当前“实现公开、spec 不公开、测试直连”的三方不一致状态。
结论：需修改。`execute_engine` 侧本轮公开 API 清单、helper 边界与公开测试入口未见回退，但 `Memory` 相关 spec / 头文件 API 简表 / 公开测试入口仍未一致收口，暂不能进入 merge。

---

时间：2026-04-26 22:12 +0800
经办人：小李飞刀
任务：T-20260426-b41011d8 / S4 build 修复回合
任务目标：修复 [include/api/Memory.h](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/include/api/Memory.h) 的 API 简表与 [spec/include/api/Memory.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/spec/include/api/Memory.md)、[test/include/api/test_memory.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/test/include/api/test_memory.py) 的不一致，补齐 `GM/SM/LM/TSM/TLM1/TLM2/TLM3` 的 spec API 列表，并让公开测试退出 `linear_offset/at` 直连
执行前阅读记录：已读 [TODO.md](/home/lfr/kernelcode_generate/TODO.md) 当前任务行、[ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md) S4、[AGENTS.md](/home/lfr/kernelcode_generate/AGENTS.md)、本任务前序 build/review 记录，以及本轮直接相关文件 [include/api/Memory.h](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/include/api/Memory.h)、[spec/include/api/Memory.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/spec/include/api/Memory.md)、[include/npu_demo/Memory.h](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/include/npu_demo/Memory.h)、[test/include/api/test_memory.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/test/include/api/test_memory.py)。
最小功能闭环：1）补齐 `spec/include/api/Memory.md` 的 `API 列表`，让它和 [include/api/Memory.h](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/include/api/Memory.h) 的当前公开声明一致；2）把 `test/include/api/test_memory.py` 的公开入口用例收回到当前稳定合同，不再直接触碰 `linear_offset/at`；3）保持 `test/execute_engine` 与 `test/include` 整体公开入口不回退。
改动：
- 更新 [include/api/Memory.h](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/include/api/Memory.h)，在文件级 `API 列表` 中补齐 `Memory::linear_offset(...)` 与两组 `Memory::at(...)` 声明，并在对应函数说明中标注“当前实现保留的索引辅助接口，不属于本轮稳定公开测试入口”。
- 更新 [spec/include/api/Memory.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/spec/include/api/Memory.md)，补齐 `GM/SM/LM/TSM/TLM1/TLM2/TLM3` 与 `linear_offset/at` 的 `API 列表` 索引，同时把“限制与边界”中的稳定测试入口描述改成与现有公开测试一致：保留 `element_count()/is_contiguous()`，继续把 `shape()/stride()/linear_offset()/at()` 归为当前不承接的稳定测试入口。
- 更新 [test/include/api/test_memory.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/test/include/api/test_memory.py)，移除 `mem.linear_offset(index)`、`mem.at(index)` 的公开测试直连，改为通过 `data()`、`element_count()`、`is_contiguous()` 等当前稳定公开入口完成同一条正向用例。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include:/home/lfr/kernelcode_generate pytest -q test/execute_engine test/include -ra` -> `107 passed`
- `rg -n "\\.linear_offset\\(|\\.at\\(" test/include/api/test_memory.py` -> 无命中
- `rg -n "inline constexpr MemorySpace GM|Memory::linear_offset\\(|Memory::at\\(const long long\\* indices\\)" include/api/Memory.h spec/include/api/Memory.md` -> 命中 `include/api/Memory.h` 与 `spec/include/api/Memory.md` 的同步条目
- `git diff --check` -> 通过
Diff 反推自测：本轮 diff 只覆盖 [include/api/Memory.h](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/include/api/Memory.h)、[spec/include/api/Memory.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/spec/include/api/Memory.md)、[test/include/api/test_memory.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/test/include/api/test_memory.py)；反推测试选择 `pytest -q test/execute_engine test/include -ra` 作为本轮公开入口回归，并辅以 `rg` 扫描 `linear_offset/at` 残留和 API 列表文本同步，再用 `git diff --check` 验证补丁格式；结果全部通过。
合同验收（如适用）：未执行 `expectation`；本轮任务明确要求 `expectation` 只读不可写，且 `Diff 反推自测` 不把 `expectation` 计入测试。
自检：
- 已按当前规则确认本轮没有新增公开 API，也没有恢复任何跨文件非公开 API 调用。
- 已核对 `linear_offset/at` 当前仍被 `include/cpu` 与 `include/npu_demo` 的实现层直接使用，因此这轮不在 S4 范围内调整其访问级别，只先把 “实现声明 / spec API 索引 / 公开测试入口” 收到一致。
- 已确认 `execute_engine` 公开 API 清单、helper 边界与 `test/execute_engine` 公开入口未回退。
- 已确认本轮修改没有触碰 `expectation`、`.skills`、`operation/arch.py`、`dialect/arch.py` 等非当前范围文件。
结论：本轮 review 退回项已收口，可以按 TODO 继续流转到下一轮 review。

---

时间：2026-04-26 22:18 +0800
经办人：提莫炖蘑菇
任务：T-20260426-b41011d8 / S4 review（复审）
任务目标：复核 S4 include/api/Memory 的 API 简表、spec API 列表、稳定公开测试入口与 execute_engine / include 本轮公开边界收口结果
执行前阅读记录：已重读 [TODO.md](/home/lfr/kernelcode_generate/TODO.md) 本任务行、[ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md) S4 正文与全局完成态/验收设计、前序 build/review 记录，以及当前 residual diff 中的 [include/api/Memory.h](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/include/api/Memory.h)、[spec/include/api/Memory.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/spec/include/api/Memory.md)、[test/include/api/test_memory.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/test/include/api/test_memory.py)、[test/execute_engine/test_execute_engine_compile.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/test/execute_engine/test_execute_engine_compile.py)、[test/execute_engine/test_execute_engine_private_helpers.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/test/execute_engine/test_execute_engine_private_helpers.py)。
真实审查：
- 复核 [include/api/Memory.h](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/include/api/Memory.h) 的文件级 `API 列表`，确认此前缺失的 `GM/SM/LM/TSM/TLM1/TLM2/TLM3` 常量已补齐；同时核对 `linear_offset/at` 已在文件级 `API 列表` 和 [spec/include/api/Memory.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/spec/include/api/Memory.md) 的 `API 列表` 中同步声明，不再存在“实现公开 / spec 索引缺失”的分叉。
- 复核 [test/include/api/test_memory.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/test/include/api/test_memory.py) 公开入口用法，确认当前测试只连接 `rank/get_shape/get_stride/element_count/is_contiguous/data/format/space/view/reshape/build_contiguous_stride` 等当前承接的公开入口，已退出对 `linear_offset/at` 的直连。
- 复核 `execute_engine` 侧公开测试入口与导入边界，确认 [test/execute_engine/test_execute_engine_compile.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/test/execute_engine/test_execute_engine_compile.py) 与 [test/execute_engine/test_execute_engine_private_helpers.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/test/execute_engine/test_execute_engine_private_helpers.py) 直连的 `default_compiler / build_compile_command / build_compile_unit / compile_source / needs_entry_shim / build_entry_shim_source / target_includes` 仍全部有对应 spec 定义。
Diff 反推审查：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include:/home/lfr/kernelcode_generate pytest -q test/execute_engine test/include -ra` -> `107 passed`
- `rg -n "\\.linear_offset\\(|\\.at\\(" test/include/api/test_memory.py` -> 无命中
- `git diff --check` -> 通过
合同验收：未执行 `expectation`。本轮仍只复核实现 / spec / pytest 的公开 API 边界，`expectation` 继续只作合同验收资产单列，不计入 `Diff 反推审查`。
自检：
- 已按最新口径再次检查“新增未在 spec 明确定义的公开接口 / 跨文件调用非公开 API / 测试直连非 API 接口 / 文件级 API 列表是否与实现一致”。
- 当前 residual diff 未命中上述硬阻断项。
- `execute_engine` 与 `include` 本轮改动文件的文件级 `API 列表`、class API 简表、spec API 列表与公开测试入口已对齐。
可改进点：
- 本轮 residual diff 内未再发现可直接执行的一线改进点。
结论：通过。S4 当前 residual diff 已把 `include/api/Memory` 的 API 简表、spec API 列表与公开测试入口收口到一致状态，`execute_engine / include` 本轮公开边界未见回退，可进入 merge。

---

时间：2026-04-26 22:55 +0800
经办人：李白
任务：T-20260426-b41011d8 / S4 merge
任务目标：将 S4 已通过复审的 `execute_engine / include` residual diff 合入主线，并完成同步确认与任务收口。
执行前阅读记录：
- 已读 [TODO.md](/home/lfr/kernelcode_generate/TODO.md) 当前任务行，确认 `T-20260426-b41011d8` 当前类型为 `merge`，目标是收口 `include/api/Memory`、`execute_engine / include` 的 residual diff。
- 已读 [ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/repo_conformance_refactor_green_plan.md) 的 `S4` 阶段定义，确认当前边界仍是 `execute_engine / include`，不得扩展到 `S5-S7`。
- 已核对当前任务记录中已有 build / review 结论，确认记录已包含 `执行前阅读记录`、`最小功能闭环`、`自检`、`Diff 反推自测` 与 `Diff 反推审查`，且 `expectation` 未被计入 diff 反推测试。
- 已在任务 worktree 内执行 `timeout 60 git fetch origin`；当前 `HEAD` 与 `origin/main` 同步到 `1477e823977b720e92b297400eb279e796b08271`，本轮无需额外重放。
真实收口过程：
- 复核本轮实际提交面，只包含 `kernel_gen/execute_engine/**`、`include/api/**`、`include/npu_demo/**`、[spec/include/api/Memory.md](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/spec/include/api/Memory.md)、[test/execute_engine/test_execute_engine_compile.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/test/execute_engine/test_execute_engine_compile.py)、[test/execute_engine/test_execute_engine_private_helpers.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/test/execute_engine/test_execute_engine_private_helpers.py)、[test/include/api/test_memory.py](/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include/test/include/api/test_memory.py) 以及本任务记录。
- 复核当前 diff 未混入 `expectation`、`.skills` 或其他超出 `S4` 范围的路径。
- 维持 build/review 已确认的边界：`include/api/Memory` 的 API 简表、spec API 列表与公开测试入口一致；`execute_engine` 公开 API 清单、helper 边界与 `test/execute_engine` 公开入口不回退。
验证：
- `git -C /home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include diff --check` -> 通过
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260426-repo-conformance-s4-exec-include:/home/lfr/kernelcode_generate pytest -q test/execute_engine test/include -ra` -> `107 passed`
Diff 反推自测：
- 本轮 merge 未新增业务改动，只合入已审 residual diff；因此沿用 build / review 已反推出的公开入口回归 [`test/execute_engine`](../../../../../../../test/execute_engine) 与 [`test/include`](../../../../../../../test/include) 作为最小验证面。
- `expectation` 不涉及本任务，也未计入 diff 反推测试。
结论：当前 worktree 已在最新 `origin/main` 基线上完成 `S4` residual diff 收口，可直接提交、推送、执行 `-done`，再按主仓同步规则尝试 fast-forward 主仓；若主仓被现有本地状态挡住，仅记录阻塞，不覆盖。
