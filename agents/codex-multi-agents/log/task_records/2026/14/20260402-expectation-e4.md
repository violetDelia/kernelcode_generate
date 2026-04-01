时间：2026-04-02 05:42:18 +0800
任务：T-20260402-00430a68
任务目标：按 `ARCHITECTURE/plan/expectation_dsl_mlir_dma_symbol_closure_plan.md` 的 `E4`，仅修改 `spec/dsl/emit_mlir.md`，冻结 `dma.view`、symbol compare family 与 `symbol.to_float` 的 lowering 合同。
改动：
- 核对任务前置：
  - `worktree=/home/lfr/kernelcode_generate/wt-20260402-expectation-e4` 可访问。
  - 当前无其他由睡觉小分队进行中的任务，已按要求向管理员同步“已开始、无阻塞、仅修改 spec/dsl/emit_mlir.md”。
- 更新 `spec/dsl/emit_mlir.md`：
  - 在 `额外补充` 中把 symbol compare family 从“仅支持 `eq/ge`，其余 unsupported”收敛为完整的一一映射：`a == b -> symbol.eq`、`a != b -> symbol.ne`、`a < b -> symbol.lt`、`a <= b -> symbol.le`、`a > b -> symbol.gt`、`a >= b -> symbol.ge`，结果类型统一为 `i1`。
  - 明确 symbol compare family 的失败边界：当比较尝试进入 symbol 路径但任一操作数不是 `!symbol.int<"...">` 时，必须报具体的 operand 类型错误，不再把 `Unsupported symbol compare op` 作为 `ne/lt/le/gt` 的长期合理边界。
  - 在 DMA helper lowering 约束中收口 `view(...) -> dma.view` 的一一映射，并补充具体失败边界：source 非 `nn.memory` 或 DMA 参数不合法时，应报 `view(...)` lowering 错误，而不是 generic unsupported。
  - 新增 `float(symbol.int)` lowering 口径：`float(n) -> symbol.to_float`，结果类型固定为 `f32`；source 非 `!symbol.int<"...">` 时必须报具体的 source 类型错误，不再沿用笼统 `Unsupported annotation` / generic unsupported 表述。
  - 在“节点映射示例”中补齐 `CompareExprAST(eq/ne/lt/le/gt/ge)` 的 symbol 路径一一映射、`CallAST(view)` -> `dma.view` 和 `CallAST(float(symbol.int))` -> `symbol.to_float`。
  - 在测试清单中：
    - 强化 `EMIT-018` 为 `dma.view` 的 expectation-aligned lowering 合同；
    - 将 `EMIT-024` 改为 compare family 一一映射，并把尚未落地的 `gt/le/lt/ne` 测试名标为下游待补测试映射；
    - 新增 `EMIT-036`，冻结 `symbol.to_float` lowering 合同，并标注下游待补测试映射 `test_emit_mlir_lowers_symbol_to_float`。
- 自检：
  - `rg -n "dma.view|symbol.gt|symbol.le|symbol.lt|symbol.ne|symbol.to_float" spec/dsl/emit_mlir.md`（exit 0）
  - `git diff --check -- spec/dsl/emit_mlir.md`（exit 0）
结论：
- 已完成本任务要求，变更范围仅 `wt-20260402-expectation-e4/spec/dsl/emit_mlir.md` 与本记录文件。
- 测试情况：本任务为 spec 阶段，未运行 `pytest`；已完成关键词校验与 diff 格式校验。
- 下一步建议：创建唯一后续实现任务，在同一 `worktree` 中对齐 `kernel_gen/dsl/emit_mlir.py`、`test/dsl/test_emit_mlir.py` 与 `test/dsl/test_ast_visitor.py`，按当前 `E4` spec 收口 `dma.view`、symbol compare family 与 `symbol.to_float` 的 lowering 行为。
时间：2026-04-02 05:31:21 +0800
任务：T-20260402-434dd2d5
任务目标：审查 `spec/dsl/emit_mlir.md` 是否与 `ARCHITECTURE/plan/expectation_dsl_mlir_dma_symbol_closure_plan.md` 的 `E4` 目标、边界、注意事项、验证命令、验收标准一致；重点检查 `dma.view`、symbol compare family 与 `symbol.to_float` 的 DSL->dialect 一一映射与具体失败边界是否已写清，且未越界到 AST/mlir_gen、实现或测试。
改动：
- 只读审查范围：
  - `spec/dsl/emit_mlir.md`
  - `test/dsl/test_emit_mlir.py`
  - `test/dsl/test_ast_visitor.py`
  - `expectation/dsl/mlir_gen/dialect/dma/view`
  - `expectation/dsl/mlir_gen/dialect/symbol/{gt,le,lt,ne,to_float}.py`
  - `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/expectation_dsl_mlir_dma_symbol_closure_plan.md`
- 复核命令：
  - `git -C /home/lfr/kernelcode_generate/wt-20260402-expectation-e4 diff -- spec/dsl/emit_mlir.md`（exit 0）
  - `sed -n '1,360p' /home/lfr/kernelcode_generate/wt-20260402-expectation-e4/spec/dsl/emit_mlir.md`（exit 0）
  - `rg -n "dma.view|symbol.gt|symbol.le|symbol.lt|symbol.ne|symbol.to_float|Unsupported symbol compare op|Unsupported annotation|unsupported|view\\(|float\\(|CompareExprAST|build_func_op|mlir_gen|AST|下游待补|test_emit_mlir_lowers_symbol_gt|test_emit_mlir_lowers_symbol_le|test_emit_mlir_lowers_symbol_lt|test_emit_mlir_lowers_symbol_ne|test_emit_mlir_lowers_symbol_to_float|EMIT-018|EMIT-024|EMIT-036" ...`（exit 0）
  - `sed -n '220,270p' /home/lfr/kernelcode_generate/wt-20260402-expectation-e4/spec/dsl/emit_mlir.md`（exit 0）
- 审查结果：
  - `spec/dsl/emit_mlir.md:129-136`、`:162` 已把 symbol compare family 的 DSL 写法到 `symbol.eq/ne/lt/le/gt/ge` 的一一映射写清，结果类型统一为 `i1`，符合 `E4` 目标与注意事项。
  - `spec/dsl/emit_mlir.md:146`、`:165-167` 已把 `view(...) -> dma.view` 与 `float(symbol.int) -> symbol.to_float` 的 DSL->dialect 一一映射写清；`spec/dsl/emit_mlir.md:152` 明确 `symbol.to_float` 结果类型固定为 `f32`。
  - `spec/dsl/emit_mlir.md:136`、`:146`、`:152` 已将失败边界从笼统 `unsupported` 收敛为具体错误类别：symbol compare operand 类型错误、`view(...)` lowering 错误、`symbol.to_float` source 类型错误。
  - `spec/dsl/emit_mlir.md` 当前仍停留在 emit_mlir 合同层，没有越界冻结 `E3` 的 AST 返回注解规则、`E5` 的 `build_func_op` 返回装配或实现/回归流程；虽然文件自然使用 AST 节点名描述输入，但未改写 AST 合法性本身，也未引入 `mlir_gen` 函数级返回语义。
  - `spec/dsl/emit_mlir.md:239-244` 与 `:259` 已把 `gt/le/lt/ne` 和 `symbol.to_float` 的专项测试名收口为下游待补测试映射，而不是当前已闭环映射；现有 `expectation` 文件与 `test/dialect/test_symbol_dialect.py` 的存在说明验收方向一致。
- 漏洞/歧义排查：
  - 输入校验绕过：compare family 与 `symbol.to_float` 仍限定在 `!symbol.int` 路径，未放开到范围外类型。
  - 类型/形状绕过：`dma.view`、compare family 与 `symbol.to_float` 的结果类型/路径口径已明确，未见新的歧义。
  - 边界越界：未越界写到 AST 返回注解、`build_func_op` 返回装配或实现细节。
  - 错误处理缺失：笼统 `unsupported` 已从本轮重点路径上移除，失败边界较完整。
  - 状态污染：未发现。
  - 资源释放问题：不涉及。
结论：
- 通过。
- 未发现额外改进点。
- 测试情况：本次为审查阶段，未运行 `pytest` 或 expectation；证据来自 plan/spec/test/expectation 的静态对照与 grep/行号复核。
- 下一步建议：按计划进入 `E5` spec 任务，仅修改 `spec/dsl/mlir_gen.md`，冻结 `build_func_op` 的函数级返回装配合同。
时间：2026-04-02 05:48:00 +0800
任务：T-20260402-c2033b74
任务目标：将 `wt-20260402-expectation-e4` 中已通过审查的 `E4` spec 成果按最小范围合入主分支，仅包含 `spec/dsl/emit_mlir.md` 与同链路记录文件；完成单次同步、cleanup 与状态封板。
改动：
- 核对合并边界：`TODO.md` 中当前 `worktree=wt-20260402-expectation-e4` 仅存在本任务 `T-20260402-c2033b74`；`git -C wt-20260402-expectation-e4 status --short` 仅见 `spec/dsl/emit_mlir.md` 变更，未发现范围外业务文件。
- 复核主分支差异：`git diff --name-only 9f46e8a..HEAD -- spec/dsl/emit_mlir.md` 无输出，确认自 `wt-20260402-expectation-e4` 基线以来主仓未再修改该文件，因此本次无需人工冲突合并。
- 将 `wt-20260402-expectation-e4/spec/dsl/emit_mlir.md` 与同链路记录同步到主分支工作目录，复核 `git diff --check -- spec/dsl/emit_mlir.md agents/codex-multi-agents/log/task_records/2026/14/20260402-expectation-e4.md` 通过。
- 在主分支生成合并提交 `726bcb5`（`T-20260402-c2033b74-merge-expectation-e4`），提交内容仅包含 `spec/dsl/emit_mlir.md` 与 `agents/codex-multi-agents/log/task_records/2026/14/20260402-expectation-e4.md`。
- 执行 cleanup：`git worktree remove --force wt-20260402-expectation-e4` 与 `git branch -D wt-20260402-expectation-e4`（均 exit 0）；清理后 `git worktree list --porcelain` 不再包含 `wt-20260402-expectation-e4`，其余现存 worktree 保持原样未触碰。
- 未新增本轮测试；本次合并直接引用链路内最近一次审查结论，证据来自 `ARCHITECTURE/plan/expectation_dsl_mlir_dma_symbol_closure_plan.md`、`spec/dsl/emit_mlir.md`、`test/dsl/test_emit_mlir.py`、`test/dsl/test_ast_visitor.py` 与 expectation 文件的静态对照。
结论：
- 完成。`E4` spec 已按限定范围合入主分支，对应 worktree/branch 已清理，无范围外文件混入。
- 本任务未扩到 `spec/dsl/mlir_gen.md`、实现、测试或 expectation；下一步建议由管理员按计划单独创建后续任务。
