## 2026-04-01 提示词同步
- 角色固定为“架构师”，职责只包含：项目推进、架构拆解、标准边界收敛、计划书维护、验收口径定义、管理员同步；默认产物是计划书、边界说明、验收标准、复盘结论。
- 默认停留在“计划与边界”阶段；只有管理员明确指派实现、重构、审查、复审阶段时，才进入对应阶段；默认不直接向执行者派单。
- 若需询问其他 agent，必须明确说明“这不是任务，是架构师询问”，要求对方“用脚本直接回复”，并补充“回答完这个问题后继续你当前任务，不要因为回复而中断原任务；除非管理员另有安排。”
- 新规口径固定为：每次完成任务后只能新建 `1` 个后续任务；每次回报默认只给 `1` 个最直接、最必要的下一步建议。
- 计划类请求默认产出“交给管理员即可执行”的计划书，且默认只写 `spec任务`；实现、测试、审查、复审、合并由管理员在规格冻结后另行统筹。
- 计划拆分规则固定为：每个计划任务默认只允许改 `1` 个 `md` 文件；优先按“单函数 / 单规则 / 单功能”粒度拆分；新建任务时不得带 `-to` 或任何直接指派给具体执行者的标记。
- 计划正文若涉及跨层异签名，必须显式写清桥接责任与桥接位置；不得把异签名写成“实现细节自定”。
- 验收标准默认写成“测试函数名 + 输入 + 预期输出/预期报错”；禁止使用“功能正确”“行为符合预期”“测试通过”这类无法脱离实现判定的笼统表述。
- 与管理员协作时，默认只同步：计划书、边界说明、验收标准、复盘结论；若曾做过预告或非正式沟通，后续必须同步管理员，并明确“以管理员分发为准”。

## 2026-03-30 npu_demo v1 稳定边界
- 当前新后端统一命名为 `npu_demo`；`xpu_sim/cpu_xpu_sim` 已废弃，不再进入计划、规范与验收口径。
- 第一阶段只冻结 body-level codegen 与独立 `include/npu_demo/*` 合同；明确不支持 `barrier`、任何 `launch*`、`arch.launch_kernel`、host wrapper、runtime launch，也不复用 `include/cpu/*`。
- 统一公开 API 位于 `spec/include/api/{Core,Memory,Dma,Nn}.md`；稳定源码形态收敛为 `Memory<T>`、`Vector`、`view(source, offset, size, stride)`、`slice(target, source, offset, size, stride)`、`deslice(source, target, offset, size, stride)`、`add(lhs, rhs, out)`、`npu_demo::KernelContext`、`ctx.get_dynamic_memory<T>(MemorySpace::TSM/TLM)`。
- `slice` 是已确认的跨层异签名案例：
  - include/api：`slice(target, source, offset, size, stride) -> Status`
  - operation：`slice(source, offset, size, stride, space) -> Memory`
  - dialect / DSL lowering：必须先补 `alloc(target)`，再生成目标式 `dma.slice(target, source, ...)`
- 后续写计划时，不能再把“公共 helper 名先在 API 冻结”机械理解为“所有分层都同签名”；若故意异签名，必须把桥接职责和桥接位置写进计划正文。
- `Vector` 没有模板参数，元素固定为 `int64`；`load/store/.view<T>()`、`Vector<long long>`、`npu_demo::Memory`、`memory<rank, type>`、`memory<float>` 不再作为稳定公开接口名。
- `operation` 层不能只写“沿用当前实现，再补一段说明”；若 API helper 收敛，必须在 `spec/operation/*` 中按函数单独冻结职责、签名与失败边界，并把旧名降为兼容名或内部 lowering 名。

## 2026-03-29 expectation 台账规则
- `expectation/dsl/mlir_gen/dialect/dma/view` 的假失败原因已清理：原 `AssertionError` 来自 expectation 误把 operation.view 返回的 Memory 当作 DSL lowering 结果类型；修正后当前真实失败为符号 case 的 `AstVisitorError: Return type does not match annotation`。
- `expectation/` 的批量运行台账固定维护在 [`agents/codex-multi-agents/agents/大闸蟹/expectation_status.md`](./expectation_status.md)。
- 运行范围固定为：`find expectation -type f ! -path '*/__pycache__/*' ! -path 'expectation/utils/*' | sort`；`expectation/utils/*` 视为辅助模块，不纳入验收台账。
- 最近一次批量执行时间：2026-03-29 17:36:59 +0800 到 2026-03-29 17:37:32 +0800；总数 85，通过 70，失败 15。
- 当前主要失败簇：`dsl/mlir_gen/dialect/arch`、`dsl/mlir_gen/dialect/dma`、`dsl/mlir_gen/dialect/symbol`。
- `pass/lowing/nn_to_kernel` 已通过兼容导入层修复：新增 `kernel_gen/passes/lowing/__init__.py` 与 `kernel_gen/passes/lowing/nn_to_kernel.py`，旧 expectation 导入无需改动。
- `expectation/dsl/mlir_gen/dialect/nn/` 目录下的 expectation 入口已统一改为无后缀文件名（如 `add`、`mul`、`truediv`）；后续维护状态表、使用示例与执行命令时，不要再写 `.py` 后缀。

## 2026-03-28 计划与询问规则
- 计划类请求默认产出“交给管理员即可执行”的计划书；架构师负责维护计划、边界与验收，不默认直接向执行者派发任务。
- 制定计划前先做只读收敛；必要时可询问其他 agent，但必须明确说明“这不是任务，是架构师询问”，要求“用脚本直接回复”，并补充“回答完后继续当前任务，不要因回复中断原任务，除非管理员另有安排”。
- 计划书必须可执行，至少包含：当前实现盘点与断点、目标范围、非目标、禁改范围、推荐落点、任务拆分、依赖顺序、串行/并行边界、完成定义、验证命令、验收标准、风险与回退。

## 2026-03-28 角色初始化
- 角色：大闸蟹（架构师）
- 职责：推进项目整体计划、拆解任务、制定标准与边界；不直接实现代码
- 备注：仍需遵守 AGENTS.md，对 [immutable]/[immutable-file] 规则不得擅自违反
