@神秘人向@睡觉小分队发起会话: 请汇报 T-20260402-672630ea 当前进展与是否存在阻塞；继续按 E2 边界仅修改 spec/dialect/symbol.md，不提前进入 E3/E4。
时间：2026-04-02 03:07:55 +0800
任务：T-20260402-672630ea
任务目标：在 `spec/dialect/symbol.md` 冻结 `gt/le/lt/ne` 与 `symbol.to_float` 的 dialect 合同；仅修改该 spec 文件，不改 DSL、实现、测试或 expectation。
改动：
- 核对任务前置：
  - `worktree=/home/lfr/kernelcode_generate/wt-20260402-expectation-e2` 可访问。
  - 当前无阻塞；已按要求向管理员同步“已开始、无阻塞、继续按 E2 边界执行”。
- 更新 `spec/dialect/symbol.md`：
  - 在 `目标` 中新增 `symbol.gt` / `symbol.le` / `symbol.lt` / `symbol.ne` 与 `symbol.to_float` 的冻结口径，明确上游 `a > b`、`a <= b`、`a < b`、`a != b` 与 `float(n)` 进入 `symbol dialect` 后的稳定目标 op。
  - 在 `限制与边界` 中把 `symbol.ne` / `symbol.lt` / `symbol.le` / `symbol.gt` 收敛为同一 compare family，统一为二元 `!symbol.int<"...">, !symbol.int<"..."> -> i1` 合同，避免拆成互不一致的规则。
  - 在比较 op 小节中补充 DSL 主链映射说明与示例，显式覆盖 `symbol.ne`、`symbol.lt`、`symbol.le`、`symbol.gt`，并写明 `Unsupported symbol compare op` 不再是这四个 op 的长期合理边界。
  - 在 `symbol.to_float` 小节中补充 DSL 主链映射说明，明确 `float(n)` / `float(symbol.int)` 进入 `symbol dialect` 后的稳定落点为 `symbol.to_float`。
- 自检：
  - `rg -n "symbol.gt|symbol.le|symbol.lt|symbol.ne|symbol.to_float" spec/dialect/symbol.md`（exit 0）
  - `git diff --check -- spec/dialect/symbol.md`（exit 0）
结论：
- 已完成本任务要求，变更范围仅 `wt-20260402-expectation-e2/spec/dialect/symbol.md` 与本记录文件。
- 测试情况：本任务为 spec 阶段，未运行 `pytest`；已完成关键词校验与 diff 格式校验。
- 下一步建议：创建唯一后续实现任务，在同一 `worktree` 中按当前 dialect 合同收口 `symbol` compare family 与 `symbol.to_float` 的实现、DSL lowering 与测试，再决定是否进入 E3/E4。
时间：2026-04-02 04:20:16 +0800
任务：T-20260402-4c4008c2
任务目标：审查 `spec/dialect/symbol.md` 是否与 `ARCHITECTURE/plan/expectation_dsl_mlir_dma_symbol_closure_plan.md` 的 `E2` 目标、边界、注意事项、验证命令、验收标准一致；重点检查 `symbol.gt/le/lt/ne` compare family 与 `symbol.to_float` 已冻结为稳定 dialect 合同，且当前表述未越界到 `E3/E4`、实现、测试或 expectation 回归。
改动：
- 只读审查范围：
  - `spec/dialect/symbol.md`
  - `test/dialect/test_symbol_dialect.py`
  - `expectation/dsl/mlir_gen/dialect/symbol/{gt,le,lt,ne,to_float}.py`
  - `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/expectation_dsl_mlir_dma_symbol_closure_plan.md`
- 复核命令：
  - `git -C /home/lfr/kernelcode_generate/wt-20260402-expectation-e2 diff -- spec/dialect/symbol.md`（exit 0）
  - `sed -n '210,320p' /home/lfr/kernelcode_generate/ARCHITECTURE/plan/expectation_dsl_mlir_dma_symbol_closure_plan.md`（exit 0）
  - `nl -ba /home/lfr/kernelcode_generate/wt-20260402-expectation-e2/spec/dialect/symbol.md | sed -n '320,440p;548,612p'`（exit 0）
  - `rg -n "symbol.gt|symbol.le|symbol.lt|symbol.ne|symbol.to_float|Unsupported symbol compare op|Unsupported annotation|float\\(n\\)|float\\(symbol.int\\)|expectation|emit_mlir|mlir_gen|ast" /home/lfr/kernelcode_generate/wt-20260402-expectation-e2/spec/dialect/symbol.md /home/lfr/kernelcode_generate/wt-20260402-expectation-e2/test/dialect/test_symbol_dialect.py /home/lfr/kernelcode_generate/expectation/dsl/mlir_gen/dialect/symbol/gt.py /home/lfr/kernelcode_generate/expectation/dsl/mlir_gen/dialect/symbol/le.py /home/lfr/kernelcode_generate/expectation/dsl/mlir_gen/dialect/symbol/lt.py /home/lfr/kernelcode_generate/expectation/dsl/mlir_gen/dialect/symbol/ne.py /home/lfr/kernelcode_generate/expectation/dsl/mlir_gen/dialect/symbol/to_float.py`（exit 0）
  - `rg -n "build_func_op|emit_mlir|mlir_gen|AST|annotation|Unsupported annotation|expectation through|return annotation|float return|compare family" /home/lfr/kernelcode_generate/wt-20260402-expectation-e2/spec/dialect/symbol.md`（exit 0；仅命中 compare family 文案）
- 审查结果：
  - `spec/dialect/symbol.md:31`、`:57`、`:333-358`、`:402-427` 已把 `symbol.ne` / `symbol.lt` / `symbol.le` / `symbol.gt` compare family 与 `symbol.to_float` 冻结为稳定 dialect 合同，满足 `E2` 目标与“compare family 一次写清、to_float 同时写清”的注意事项。
  - `spec/dialect/symbol.md:358` 明确 `Unsupported symbol compare op` 不再是这四个 compare op 的长期合理边界，符合 plan 的错误示例收口要求。
  - `spec/dialect/symbol.md` 当前只写 dialect 层签名、verifier、parse/print、DSL 主链目标 op 示例，没有扩展到 `E3` 的 `-> float` 返回注解合法性、`E4` 的 DSL-to-dialect lowering 细节、实现、测试或 expectation 回归流程；`rg` 对 `annotation` / `emit_mlir` / `mlir_gen` / `AST` 的命中仅剩 compare family 文案，未发现越界表述。
  - `test/dialect/test_symbol_dialect.py:536-551`、`:584-706` 已具备 compare family 与 `symbol.to_float` 的 dialect 级 verifier/parse-print 测试基础；`expectation/dsl/mlir_gen/dialect/symbol/{gt,le,lt,ne,to_float}.py` 文件也已存在，和 plan 的验收标准指向一致。
漏洞/歧义排查：
- 输入校验绕过：compare family 仍统一要求 `!symbol.int<"...">, !symbol.int<"..."> -> i1`，`symbol.to_float` 仍统一要求 `!symbol.int<"..."> -> f32`，未放开输入域。
- 类型/形状绕过：未发现把 compare family 拆成不一致签名或把 `to_float` 放宽到 `f64/bf16` 等越界类型。
- 边界越界：未引入 `E3/E4` 范围内的 AST 注解、emit_mlir 或 build_func_op 细节。
- 错误处理缺失：非法操作数类型、非法结果类型与 parse/print 边界仍在 spec 中明确。
- 状态污染：未发现。
- 资源释放问题：不涉及。
结论：
- 通过。
- 未发现额外改进点。
- 测试情况：本次为审查阶段，未运行 `pytest` 或 expectation；证据来自 plan/spec/test/expectation 的静态对照与行号复核。
- 下一步建议：按计划进入 `E3` spec 任务，仅修改 `spec/dsl/ast.md`，冻结 `-> float` 返回注解与 `float(symbol.int)` 的 AST 入口合同。
