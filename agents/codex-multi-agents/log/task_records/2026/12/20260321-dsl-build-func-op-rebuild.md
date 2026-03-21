# 2026-03-21 T-20260321-0db3806a

- 结论：`需修改`
- 复审目标：复审 `spec/dsl/{ast,ast_visitor,emit_mlir,mlir_gen}.md` 与 `test/dsl/test_ast_visitor.py`、`expectation/dsl/build_func_op.py` 的测试闭环；重点核对 AST/AV/EMIT/MGEN 用例编号映射完整性、`AV-002`/`EMIT-002`/`EMIT-003`/`MGEN-003` 新增闭环是否成立，以及是否仍存在 spec 无测试映射或测试无 spec 映射。
- worktree：`/home/lfr/kernelcode_generate/wt-20260321-dsl-build-func-op-rebuild`
- 已确认项：
  - `pytest -q test/dsl/test_ast_visitor.py`：通过，`38 passed`。
  - `python expectation/dsl/build_func_op.py`：通过。
  - `AV-002`、`EMIT-002`、`EMIT-003`、`MGEN-003` 对应测试当前均存在且可运行通过。
- 必改问题：
  - `spec/dsl/ast.md` 的测试闭环不完整。当前测试章节只列 `AST-001..003`，但真实测试还存在 `AST-001A`、`AST-001B`，以及一组实际归属 AST 解析边界的异常用例，例如 [`test/dsl/test_ast_visitor.py`](../../../../../../../test/dsl/test_ast_visitor.py#L517) 的未知名称诊断、[`test/dsl/test_ast_visitor.py`](../../../../../../../test/dsl/test_ast_visitor.py#L567) 的非法返回注解、[`test/dsl/test_ast_visitor.py`](../../../../../../../test/dsl/test_ast_visitor.py#L626) 的缺失 `return`、[`test/dsl/test_ast_visitor.py`](../../../../../../../test/dsl/test_ast_visitor.py#L666) 的缺少 Tensor 维度；这些能力在 [`spec/dsl/ast.md`](../../../../../../../spec/dsl/ast.md#L40) 的公开接口与解析边界中已有体现，但测试章节未建立正式映射。建议把 AST 解析入口、反向依赖约束与解析错误路径单独收敛为 AST 编号，避免继续混挂在 `AV-003*`。
  - `spec/dsl/ast_visitor.md` 的编号空间已失真。当前测试章节只定义 `AV-001..003`，但测试文件里同名空间还包含 `AV-003A/B/C/E/F/G/H/I/J/L/M/R` 等多组用例，其中部分实际归属 `ast.py` 或 `mlir_gen.py`，例如 [`test/dsl/test_ast_visitor.py`](../../../../../../../test/dsl/test_ast_visitor.py#L491) 的标量签名 lowering、[`test/dsl/test_ast_visitor.py`](../../../../../../../test/dsl/test_ast_visitor.py#L517) 的未知名称诊断、[`test/dsl/test_ast_visitor.py`](../../../../../../../test/dsl/test_ast_visitor.py#L607) 的常量 lowering 失败、[`test/dsl/test_ast_visitor.py`](../../../../../../../test/dsl/test_ast_visitor.py#L713) 的 `LoadAST` 路径。现状会让 `AV-*` 同时代表 visitor、parse、func 生成与 emit 语义，无法支撑“编号 -> spec 职责 -> 真实测试”一一对应。建议将 `AV-*` 收敛为纯 visitor 职责，其他测试回归所属 spec。
  - `spec/dsl/emit_mlir.md` 的测试映射缺少当前已存在的正式能力覆盖。该文件测试章节只列 `EMIT-001..003`，但真实测试还包含 [`test/dsl/test_ast_visitor.py`](../../../../../../../test/dsl/test_ast_visitor.py#L345) 的 `EMIT-004`，用于覆盖 `emit_mlir(node, ctx)` 通过符号表直接解析 `TensorAST` 输入的行为；而 [`spec/dsl/emit_mlir.md`](../../../../../../../spec/dsl/emit_mlir.md#L68) 的公开接口明确将 `emit_mlir(node, ctx)` 定义为通用节点发射入口。建议补上 `EMIT-004` 或重命名归并到现有条目，避免“测试有 spec 外编号”的闭环缺口。
  - `spec/dsl/mlir_gen.md` 与真实测试之间仍存在未映射项和边界冲突。该文件测试章节只列 `MGEN-001..003`，但测试文件还存在 [`test/dsl/test_ast_visitor.py`](../../../../../../../test/dsl/test_ast_visitor.py#L145) 的 `MGEN-004` 与 [`test/dsl/test_ast_visitor.py`](../../../../../../../test/dsl/test_ast_visitor.py#L169) 的 `MGEN-005`。这两项分别检查 module wrapper 与打印文本中出现 `func.func`/`nn.add`，而 [`spec/dsl/mlir_gen.md`](../../../../../../../spec/dsl/mlir_gen.md#L30) 又明确“不生成 module，不负责文本打印”。建议二选一：要么把这两项改成 expectation/helper 层校验，不占用 `MGEN-*` 正式编号；要么在 spec 测试章节中明确其为“上层包装/文本辅助断言，不属于 mlir_gen 公开能力”。
  - `expectation/dsl/build_func_op.py` 当前只验证 [`expectation/dsl/build_func_op.py`](../../../../../../../expectation/dsl/build_func_op.py#L12) 的 `build_func_op(add)` 返回 `FuncOp`，不能作为四份 spec 公开能力闭环的充分证据。即使配合 `38 passed`，也只能说明现有测试集可运行通过，不能证明 AST 解析边界、visitor 分发边界、emit 入口边界与 mlir_gen 公共职责已被完整映射。建议后续复审仍以 spec <-> test 编号一一对应为准，不把 expectation 单脚本通过当作闭环完成。
- 影响范围：
  - 当前 DSL 四份 spec 的测试章节仍无法准确回答“哪些公开能力已有正式测试、哪些异常路径已被真实用例覆盖、哪些测试其实跨层归属错误”。
  - 若直接按现状进入后续链路，管理员无法基于 spec 精确派生实现/补测任务，也无法判断新增用例应归 AST、visitor、emit 还是 mlir_gen。
- 建议改法：
  - 先做一次纯 spec 收敛任务，只改 `spec/dsl/{ast,ast_visitor,emit_mlir,mlir_gen}.md` 的测试章节与用例归属，不改实现。
  - 为四份 spec 建立不重叠的编号空间，并把当前 `test/dsl/test_ast_visitor.py` 中所有 `AST-*`/`AV-*`/`EMIT-*`/`MGEN-*` 用例逐一归位；凡是不属于对应 spec 公开能力的测试，要么改编号，要么在 spec 中明确为“辅助断言/间接验证”。
  - 单独补一轮“spec 无测试映射 / 测试无 spec 映射”清单，直到四份 spec 与当前测试集实现双向闭环后再复审。
- 下一步建议：派发 DSL spec 测试映射收敛任务，优先修正 `ast.md`、`ast_visitor.md`、`emit_mlir.md`、`mlir_gen.md` 的测试章节和编号归属，再进入下一轮复审。

# 2026-03-21 T-20260321-88b1a52a

- 任务目标：补齐 DSL 四份 spec 的测试闭环，完善 `test/dsl/test_ast_visitor.py` 映射与用例覆盖。
- worktree：`/home/lfr/kernelcode_generate/wt-20260321-dsl-build-func-op-rebuild`
- 实际变更：
  - `test/dsl/test_ast_visitor.py`：校准 AST/AV/EMIT/MGEN 用例编号映射，新增 AST Visitor 复用、emit_mlir 比较/不支持节点、mlir_gen 返回类型对齐测试，并更新对应注释。
- 测试结果：
  - `pytest -q test/dsl/test_ast_visitor.py`：通过，`38 passed`。
  - `python expectation/dsl/build_func_op.py`：通过。
- 变更文件：
  - `test/dsl/test_ast_visitor.py`
- 阻塞：无。
- 下一步建议：申请复审，核对四份 spec 与测试映射闭环是否满足最新规范。

# 2026-03-21 T-20260321-62fa1a69

- 任务目标：修复 DSL build_func_op 链路中索引/stride 错误路径的 location 透传，并补回归测试。
- worktree：`/home/lfr/kernelcode_generate/wt-20260321-dsl-build-func-op-rebuild`
- 实际变更：
  - `kernel_gen/dsl/emit_mlir.py`：为 `_build_index_attrs` / `_build_stride_attrs` 增加 `location` 透传，确保 `Index rank mismatch` 与 `Only unit stride is supported` 抛出可定位错误。
  - `test/dsl/test_ast_visitor.py`：补充 index rank mismatch 回归用例，并增强 stride 非 1 的定位断言。
- 测试结果：
  - `pytest -q test/dsl/test_ast_visitor.py`：通过，`32 passed`。
  - `python expectation/dsl/build_func_op.py`：通过。
- 变更文件：
  - `kernel_gen/dsl/emit_mlir.py`
  - `test/dsl/test_ast_visitor.py`
- 阻塞：无。
- 下一步建议：申请复审任务，核对 location 透传与新增回归是否满足 spec/dsl/ast_visitor.md。

# 2026-03-21 T-20260321-c146cd00

- 结论：`通过`
- 复审目标：核对 `kernel_gen/dsl/emit_mlir.py` 的 `location` 透传修复、`test/dsl/test_ast_visitor.py` 回归覆盖，以及 `build_func_op` 链路与 `spec/dsl/{ast,ast_visitor,emit_mlir,mlir_gen}.md` 一致性。
- worktree：`/home/lfr/kernelcode_generate/wt-20260321-dsl-build-func-op-rebuild`
- 复审结果：
  - `kernel_gen/dsl/emit_mlir.py` 中 `_build_index_attrs(...)` 已新增 `location` 参数，并在 `Index rank mismatch` 路径使用调用方传入位置。
  - `kernel_gen/dsl/emit_mlir.py` 中 `_build_stride_attrs(...)` 已新增 `location` 参数，并在 `Only unit stride is supported` 路径透传 AST 节点位置。
  - `LoadAST` / `StoreAST` 调用上述辅助函数时已统一传入 `node.location`，`AstVisitorError.location` 不再在这两类错误路径丢失。
  - `test/dsl/test_ast_visitor.py` 已补覆盖：
    - 非 unit stride 报错保留位置；
    - index rank mismatch 报错保留位置。
  - `expectation/dsl/build_func_op.py` 仍可直接运行通过。
  - 结合现有 `kernel_gen/dsl/{ast,mlir_gen,__init__}.py`，当前 `build_func_op -> build_func_op_from_ast -> AstVisitor -> emit_mlir` 链路与现有 spec 一致，公开导出边界未见新增漂移。
- 验证结果：
  - `python expectation/dsl/build_func_op.py`：通过
  - `pytest -q test/dsl/test_ast_visitor.py`：通过，`32 passed`
- 本轮未发现新的需修改项，可进入后续链路。

# 2026-03-21 T-20260321-0f0eabad

- 结论：`需修改`
- 审查目标：复审 DSL `build_func_op` 链路，核对 `expectation/dsl/build_func_op.py`、`kernel_gen/dsl/{ast,mlir_gen,emit_mlir,__init__}.py` 与 `spec/dsl/{ast,ast_visitor,emit_mlir,mlir_gen}.md` 一致性。
- worktree：`/home/lfr/kernelcode_generate/wt-20260321-dsl-build-func-op-rebuild`
- 已确认项：
  - `python expectation/dsl/build_func_op.py` 可直接运行通过。
  - `pytest -q test/dsl/test_ast_visitor.py` 通过，结果 `31 passed`。
  - `build_func_op -> build_func_op_from_ast -> AstVisitor.visit_function -> emit_mlir` 主调用链与 spec 目标基本一致。
  - `kernel_gen/dsl/ast.py` 未出现 `ast` 反向依赖 visitor 的方向错误。
- 必改问题：
  - `kernel_gen/dsl/emit_mlir.py:203`：`_build_stride_attrs(...)` 在 stride 非全 1 时直接抛出 `_LoweringError("Only unit stride is supported", location=None)`，导致 `build_func_op(_from_ast)` 最终抛出的 `AstVisitorError.location` 为 `None`，不满足 `spec/dsl/ast_visitor.md` 中“错误必须携带可定位诊断信息”的要求。复现：构造带 `SourceLocation` 的 `LoadAST(..., stride=ConstAST(2, location=loc), location=loc)`，`build_func_op_from_ast(...)` 抛出的 `AstVisitorError.location` 为 `None`。
  - `kernel_gen/dsl/emit_mlir.py:190`：`_build_index_attrs(...)` 在 `list/tuple` 长度与 rank 不一致时，用 `getattr(value, "location", None)` 读取位置；但 `value` 为 Python `list/tuple` 时天然没有 `location`，会再次丢失 AST 节点位置，导致 `Index rank mismatch` 也无法回传到 `AstVisitorError.location`。复现：构造带 `SourceLocation` 的 `LoadAST(..., offset=[ConstAST(0, location=loc)], location=loc)`，异常 `location` 仍为 `None`。
- 影响范围：
  - 当前 `AstVisitorError.location` 只在部分错误路径收敛，`build_func_op` 链路对索引/stride 相关错误的定位信息不完整。
  - 这会影响上层按 spec 进行可定位报错，也削弱 `emit_mlir` / `AstVisitor` 的职责边界一致性验证。
- 建议改法：
  - 在 `kernel_gen/dsl/emit_mlir.py` 中为 `_build_index_attrs(...)`、`_build_stride_attrs(...)` 增加显式 `location` 参数，或由调用方传入当前 AST 节点的 `location`。
  - `emit_mlir(...)` 处理 `LoadAST` / `StoreAST` / 其他索引相关节点时，应统一把 `node.location` 传入上述辅助函数，确保 `_LoweringError.location -> AstVisitorError.location` 全链路一致。
- 建议下一步：申请一个实现改进任务，仅修复 `emit_mlir` 索引/stride 错误路径的位置透传，并补一组针对 `AstVisitorError.location` 的回归测试后再复审。

# 2026-03-21 T-20260321-ab6f0a26

- 任务目标：按 DSL spec 收敛实现/测试，补齐 AST 解析入口与 MLIR 生成链路，确保 expectation/dsl/build_func_op.py 可直接运行通过。
- worktree：`/home/lfr/kernelcode_generate/wt-20260321-dsl-build-func-op-rebuild`
- 实际变更：
  - `kernel_gen/dsl/ast.py`：补齐 `parse_function` 与解析逻辑，新增 `AstParseError` 并保证诊断位置信息。
  - `kernel_gen/dsl/mlir_gen.py`：统一通过 `parse_function` 驱动构建，补齐解析错误包装与位置透传。
  - `kernel_gen/dsl/emit_mlir.py`：广播 stride 收敛为默认连续 stride，补齐 dtype 错误定位。
  - `kernel_gen/dsl/__init__.py`：收敛公开导出，仅暴露 spec 定义的 DSL 入口。
  - `expectation/dsl/build_func_op.py`：补齐运行环境路径，确保脚本可直接运行。
- 测试结果：
  - `pytest -q test/dsl/test_ast_visitor.py`：通过，`31 passed`。
  - `python expectation/dsl/build_func_op.py`：通过。
- 变更文件：
  - `kernel_gen/dsl/ast.py`
  - `kernel_gen/dsl/mlir_gen.py`
  - `kernel_gen/dsl/emit_mlir.py`
  - `kernel_gen/dsl/__init__.py`
  - `expectation/dsl/build_func_op.py`
- 阻塞：无。
- 下一步建议：申请审查任务，核对 AST 解析入口、公开导出与广播/返回类型约束是否与 spec/测试闭环一致。

# 2026-03-21 T-20260321-c1f13efe

- 任务目标：按复审结论收敛 `spec/dsl/{ast,ast_visitor,emit_mlir,mlir_gen}.md` 的测试编号与归属，补齐 AST-001A/001B、EMIT-004、并收敛 MGEN-004/005 边界冲突，建立 spec <-> test 一一映射。
- worktree：`/home/lfr/kernelcode_generate/wt-20260321-dsl-build-func-op-rebuild`
- 实际变更：
  - `spec/dsl/ast.md`：补齐 AST-001A/001B 与解析边界用例映射，明确测试函数名。
  - `spec/dsl/ast_visitor.md`：收敛为仅 visitor 责任的 AV-001..003 映射。
  - `spec/dsl/emit_mlir.md`：补 EMIT-004，并新增 Load/Store/ForAST 等发射路径映射。
  - `spec/dsl/mlir_gen.md`：补齐 MGEN-004/005 并注明测试封装边界，新增隐式 broadcast/返回类型/SSA 等映射。
- 测试：未运行（仅 spec 收敛）。
- 变更文件：
  - `spec/dsl/ast.md`
  - `spec/dsl/ast_visitor.md`
  - `spec/dsl/emit_mlir.md`
  - `spec/dsl/mlir_gen.md`
- 阻塞：无。
- 下一步建议：发起复审核对 spec <-> test 编号闭环与边界口径。

# 2026-03-21 T-20260321-4bcbc419

- 结论：`需修改`
- 复审目标：核对 `spec/dsl/{ast,ast_visitor,emit_mlir,mlir_gen}.md` 与 `test/dsl/test_ast_visitor.py`、`expectation/dsl/build_func_op.py` 的测试编号与映射闭环，重点确认 AST-001A/001B、EMIT-004、MGEN-004/005 的边界与职责归属。
- worktree：`/home/lfr/kernelcode_generate/wt-20260321-dsl-build-func-op-rebuild`
- 已确认项：
  - AST-001A/AST-001B 与 `test_parse_function_entry` / `test_parse_function_does_not_depend_on_ast_visitor_entry` 对齐，解析入口职责清晰。
  - EMIT-004 与 `test_emit_mlir_tensor_uses_symbol_table` 对齐，`emit_mlir` 负责符号表解析一致。
  - MGEN-004/MGEN-005 与 `test_visit_to_nn_ir_builds_module` / `test_emit_mlir_output` 对齐，且已在 spec 中注明“测试辅助封装/打印”的边界说明。
  - `expectation/dsl/build_func_op.py` 仅验证 `build_func_op` 返回 `FuncOp`，与 `mlir_gen` 入口语义一致，但不影响编号闭环结论。
- 必改问题：
  - `spec/dsl/ast.md` 的 AST-004..009 与 `test/dsl/test_ast_visitor.py` 中对应测试的编号不一致：例如 `test_globals_and_builtins_annotation_entry`、`test_unknown_name_reports_diagnostics`、`test_invalid_return_annotation_reports_diagnostics`、`test_missing_return_reports_diagnostics`、`test_missing_tensor_dimensions_reports_diagnostics` 在测试文件里仍标注为 `AV-003A/AV-003C/AV-003E/AV-003H/AV-003J`，导致“AST-* 编号 <-> 测试编号”闭环断裂。应统一：要么把测试编号改为 `AST-004..009`，要么回收 spec 编号并调整映射表。
  - `spec/dsl/emit_mlir.md` 的 EMIT-005..010 映射到 `test_load_ast_lowering_rejected`、`test_store_ast_lowering_rejected`、`test_load_ast_lowering_raises_lowering_error`、`test_load_ast_index_rank_mismatch_reports_location`、`test_store_ast_lowering_raises_lowering_error`、`test_for_ast_lowering_emits_loads`，但测试文件当前编号仍是 `AV-003L/M/L-A/M/R`，编号空间不一致。需统一编号与归属。
  - `spec/dsl/mlir_gen.md` 的 MGEN-006..014（标量参数、返回注解错误、常量 lowering、返回类型不匹配、SSA 顺序、隐式 broadcast 等）对应的测试在文件中仍标为 `AV-003B/F/G/I/K/N/O/P/Q`，且部分测试注释仍指向 `spec/dsl/lowering.md`，与当前 `mlir_gen.md` 映射冲突。需同步测试编号与 `对应 spec 文件路径`。
- 影响范围：
  - 当前 DSL 四份 spec 的测试编号与测试文件注释编号未闭环，无法做到“编号 -> spec 职责 -> 真实测试”一一对应。
- 建议改法：
  - 发起测试映射清理任务，仅更新 `test/dsl/test_ast_visitor.py` 的用例编号与 `对应 spec 文件路径`，对齐 `spec/dsl/{ast,emit_mlir,mlir_gen}.md` 的编号与映射表；或反向调整 spec 编号，二选一收敛。
  - 收敛 `AV-*` 编号为仅覆盖 visitor 责任，其他测试编号回归 AST/EMIT/MGEN 体系。
- 测试结果：未执行（按要求仅复审）。
- 阻塞：无。
- 下一步建议：派发“测试编号映射收敛”任务，修正测试编号与 spec 映射后再复审。

# 2026-03-21 T-20260321-ab151d53

- 任务目标：修正 `test/dsl/test_ast_visitor.py` 编号注释与 spec 映射，确保 AST/AV/EMIT/MGEN 编号与 `spec/dsl/{ast,ast_visitor,emit_mlir,mlir_gen}.md` 一致，移除 `spec/dsl/lowering.md` 引用。
- worktree：`/home/lfr/kernelcode_generate/wt-20260321-dsl-build-func-op-rebuild`
- 实际变更：
  - `test/dsl/test_ast_visitor.py`：
    - AST 解析边界用例编号改为 AST-004..009；
    - emit 用例编号改为 EMIT-005..010；
    - mlir_gen 用例编号改为 MGEN-006..014；
    - 修正 spec 路径引用，移除 `spec/dsl/lowering.md`。
- 测试：未运行（仅注释与映射调整）。
- 变更文件：
  - `test/dsl/test_ast_visitor.py`
- 阻塞：无。
- 下一步建议：申请复审核对 spec <-> test 编号闭环。

# 2026-03-21 T-20260321-d86c8d7c

- 结论：`通过`
- 复审目标：复审 DSL spec/test 闭环，核对 AST-004..009、EMIT-005..010、MGEN-006..014 与 spec 一一匹配，并确认无 spec/dsl/lowering.md 残留引用。
- worktree：`/home/lfr/kernelcode_generate/wt-20260321-dsl-build-func-op-rebuild`
- 复审结果：
  - `spec/dsl/ast.md` 中 AST-004..009 与 `test_globals_and_builtins_annotation_entry`、`test_unknown_name_reports_diagnostics`、`test_invalid_return_annotation_reports_diagnostics`、`test_missing_return_reports_diagnostics`、`test_missing_tensor_dimensions_reports_diagnostics`、`test_unsupported_syntax_reports_diagnostics` 一一对应。
  - `spec/dsl/emit_mlir.md` 中 EMIT-005..010 与 `test_load_ast_lowering_rejected`、`test_store_ast_lowering_rejected`、`test_load_ast_lowering_raises_lowering_error`、`test_load_ast_index_rank_mismatch_reports_location`、`test_store_ast_lowering_raises_lowering_error`、`test_for_ast_lowering_emits_loads` 一一对应。
  - `spec/dsl/mlir_gen.md` 中 MGEN-006..014 与 `test_scalar_arg_lowering_in_signature`、`test_invalid_tensor_return_annotation_reports_diagnostics`、`test_constant_lowering_reports_diagnostics`、`test_return_type_mismatch_reports_diagnostics`、`test_multi_statement_ssa_order_and_reuse`、`test_tensor_binary_implicit_broadcast_lowering`、`test_tensor_binary_prepend_broadcast_lowering`、`test_compare_implicit_broadcast_lowering`、`test_tensor_binary_implicit_broadcast_mismatch_reports_diagnostics` 一一对应。
  - `spec/dsl/ast*.md`、`spec/dsl/emit_mlir.md`、`spec/dsl/mlir_gen.md` 与 `test/dsl/test_ast_visitor.py`、`expectation/dsl/build_func_op.py` 未发现 `spec/dsl/lowering.md` 引用残留。
- 测试结果：未执行（按任务要求仅复审）。
- 下一步建议：进入合并整理阶段（如需）。
