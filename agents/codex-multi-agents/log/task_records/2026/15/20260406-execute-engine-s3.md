时间：2026-04-07 00:08:10 +0800
经办人：咯咯咯
任务：T-20260406-56e3e942（emit_c_cpp_execution_engine_green_plan-S3-spec）
任务目标：补齐 `spec/execute_engine/execute_engine_target.md`，收口 target 选择、include 注入、`entry shim`、`entry_point` 与 `ordered_args` 合同，并写清默认值与失败短语触发条件。
改动：
- 新增 `spec/execute_engine/execute_engine_target.md`，按 `spec` 结构写清 `target=cpu/npu_demo` 的 include 注入映射、默认 `compiler=g++`、默认 `compiler_flags=("-std=c++17",)`、`link_flags=()`、`entry_point=kg_execute_entry` 与 `entry shim` 的 C ABI 签名。
- 在文档中冻结 `ordered_args[i] -> 第 i 个函数形参` 的绑定规则，并将 `MemoryArg / IntArg / FloatArg` 与 `KgArgSlot` 的对应关系写成机械合同。
- 明确失败短语触发：`target_header_mismatch`（target/include family 不一致）、`compile_failed`（编译器启动或编译产物生成失败）、`symbol_resolve_failed`（导出入口无法解析）、`runtime_throw_or_abort`（参数槽数量或顺序不匹配导致执行失败）。
- 只读查阅清单+目的：
  - `ARCHITECTURE/plan/emit_c_cpp_execution_engine_green_plan.md`：作为 `S3` 的主口径来源，提取 `target -> include` 映射、`entry shim` C ABI 签名、`ordered_args` 顺序示例、默认 `entry_point` 与默认编译器/flags。
  - `spec/execute_engine/execute_engine.md`：对齐总览文档中的 `entry_point`、失败短语与 `P0` 边界。
  - `spec/execute_engine/execute_engine_api.md`：对齐 `CompileRequest / ExecuteRequest / CompiledKernel` 的默认值与字段语义。
  - 已按管理员授权尝试定位 `kernel_gen/execute_engine/*` 与 `test/execute_engine/*` 只读文件，但当前 worktree 中未落地对应路径，因此未读取实现/测试源码，改以计划书口径定稿。
结论：
- 已完成 `S3` spec 收口：新增 target/include/entry shim 独立文档，并与 `execute_engine.md`、`execute_engine_api.md` 的 `entry_point` 与失败短语口径保持一致。
- 本次仅修改 `spec/execute_engine/execute_engine_target.md` 与本记录文件，未修改实现/测试。
- 未运行测试；本任务为 spec-only，记录中已给出下游应覆盖的测试目标。

- 时间: 2026-04-07 00:14:11 +0800
- 经办人: 提莫炖蘑菇
- 任务: T-20260407-5ee991b4（emit_c_cpp_execution_engine_green_plan-S3-审查）
- 任务目标: 审查 execute_engine_target.md 中 target/include 映射、编译器默认值/flags 追加规则、entry_point/entry shim/ordered_args 合同与失败短语触发是否与 S1/S2 spec 与计划书一致。

## 改动
- spec/execute_engine/execute_engine_target.md
  - 新增 S3 target/include/entry shim 规则文档，定义 target 映射、默认编译器/flags、entry_point 与 ordered_args 绑定规则。

## 结论
- 通过：execute_engine_target.md 与 execute_engine.md/execute_engine_api.md 及计划书 S3 口径一致；target/include、compiler 默认值与 flags 追加、entry_point/entry shim/ordered_args 规则与失败短语触发无冲突。

## 问题清单
- 无。

## 风险
- 未发现新增风险；失败短语与触发条件未出现漂移或空洞。

## 漏洞排查结果
- 核对 target/include 回退禁止、entry_point 解析与 ordered_args 绑定路径，未发现绕过或 silent fallback 风险。

## 验证命令
- 无（spec-only 审查）。

## 关键输出
- 无。

## 下一步建议
- 进入合并收口。
