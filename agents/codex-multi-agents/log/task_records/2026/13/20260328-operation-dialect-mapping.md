时间：2026-03-28
任务：T-20260328-f4f2a657
任务目标：补齐 operation API 到 dialect op 映射表，限定 spec/dialect/{nn,dma,arch}.md 对照 spec/operation/*.md。
改动：
- 更新 spec/dialect/nn.md：补充 operation→dialect 映射表，更新最后一次更改。
- 更新 spec/dialect/dma.md：补充 operation→dialect 映射表，修正分层约束与依赖描述，更新最后一次更改。
- 更新 spec/dialect/arch.md：补充 operation→dialect 映射表。
结论：已完成 spec 收敛，未执行测试。经办人：摸鱼小分队。

时间：2026-03-28 18:54:32 +0800
任务：T-20260328-db049b71
任务目标：复审 operation->dialect 映射表与 spec/operation、实现、测试闭环一致性，关注公开 API 覆盖与不支持项原因。
改动：
- 对照 spec/dialect/{nn,dma,arch}.md 与 spec/operation/{nn,dma,arch}.md，核对 kernel_gen/dialect/{nn,dma,arch}.py 与 test/dialect/*.py。
- 额外核对 kernel_gen/operation/dma.py 与 test/operation/test_operation_dma.py 的 view/stride 语义。
- 发现 dma.view 未建模 offset 导致映射缺口；operation/dma 支持非单位 stride，但 dialect 仅支持 stride=1，映射未注明限制。
- 运行 pytest -q test/dialect/test_dma_dialect.py -k dma_view（exit 0）。
结论：需修改。

时间：2026-03-28 19:45:00 +0800
任务：T-20260328-fe135cf8
任务目标：仅收敛 dma.view 的实现/测试闭环，补齐 offsets operand 与静态边界校验，不改 spec。
改动：
- 更新 kernel_gen/dialect/dma.py：
  - 为 DmaViewOp 新增 offsets variadic operand。
  - 新增 _verify_static_view_bounds，用于静态可判定场景执行 `offset + (size - 1) * stride < dim` 校验。
  - 在 verifier 中补齐 offsets 类型/非负/rank 检查，并保留既有 shape/stride/result 布局校验。
  - 保持旧版 `DmaViewOp(source, shape, stride, result_type)` 构造可用，空 offsets 按全零兼容。
- 更新 test/dialect/test_dma_dialect.py：
  - 将 dma.view 直接构造调用切到显式 offsets 版本。
  - 新增 offsets 长度不匹配、负 offset、静态越界三类负路径覆盖。
  - 调整 dynamic parse/print round-trip 中的 view 构造，保证与新 verifier 约束一致。
验证：
- python -m compileall kernel_gen/dialect/dma.py test/dialect/test_dma_dialect.py（exit 0）
- pytest -q test/dialect/test_dma_dialect.py -k dma_view（exit 0，4 passed）
- pytest -q test/dialect/test_dma_dialect.py（exit 0，27 passed）
结论：实现/测试阶段完成，可释放同一 worktree 供后续 spec 任务 T-20260328-d25b4a69 使用。经办人：朽木露琪亚。
- 时间：`2026-03-28 19:40:31 +0800`
- 任务：`T-20260328-d25b4a69`
- 经办人：`摸鱼小分队`
- 任务目标：补齐 `dma.view` offsets 语义与 operation->dialect 边界说明，明确 offset 校验与测试映射。
- 改动：
  - `spec/dialect/dma.md`：补充 `dma.view` 的 `offsets` operand 语义、边界校验规则与 verifier 约束；更新 operation->dialect 映射说明；补齐测试目标与 TC-DMA-019A 映射到 `test_dma_view_rejects_invalid_offsets_or_bounds`。
- 结论：已完成 spec 收敛；未执行测试。

时间：2026-03-28 19:47:58 +0800
任务：T-20260328-4a17005b
任务目标：核对 dma.view offsets 实现与测试是否已对齐最新 spec/dialect/dma.md，并复跑相关 verifier/test。
改动：
- 复核 `spec/dialect/dma.md`：最新规范已要求 `dma.view` 必须显式提供 `offsets/shape/stride` operand，且 `offsets` 数量必须与 rank 一致、值必须非负，并在静态可判定时执行越界检查。
- 复核 `kernel_gen/dialect/dma.py`：`DmaViewOp.__init__` 仍兼容旧版 `DmaViewOp(source, shape, stride, result_type)` 调用，自动生成空 `offsets`；`verify_` 仅在 `offsets` 非空时执行 rank 校验，导致缺失 offsets 不会报错。
- 复核 `test/dialect/test_dma_dialect.py`：现有 `TC-DMA-019/019A` 仅覆盖 offsets 长度不匹配、负 offsets、静态越界等路径，未覆盖“完全缺失 offsets”负路径。
- 验证：
  - `pytest -q test/dialect/test_dma_dialect.py -k dma_view`（exit 0，`4 passed, 23 deselected`）
  - `pytest -q test/dialect/test_dma_dialect.py`（exit 0，`27 passed`）
  - 运行最小复现：
    `python - <<'PY' ... DmaViewOp(source, make_symbol([2, 4]), make_symbol([1, 1]), result_type).verify() ... PY`
    结果为 `VERIFY_OK`（exit 0），证明缺失 `offsets` 的旧版四参调用仍可通过 verifier。
- 问题列表：
  - `[P1] kernel_gen/dialect/dma.py::DmaViewOp.__init__/verify_`
    - 现象：实现仍接受空 `offsets` segment，与最新 spec 中“offsets 必须显式提供且数量与 rank 一致”的要求冲突。
    - 风险：输入校验可被绕过，`operation/dma view(offset,size,stride)` 到 dialect 的映射边界未真正收紧；旧调用路径会被 silently 接受，导致 spec/实现/测试三者不一致。
    - 建议：后续实现任务中移除或拒绝旧版四参兼容路径，并新增“缺失 offsets 必须报错”的负向测试。
- 漏洞排查结果：
  - 输入校验绕过：发现问题。空 `offsets` 可绕过必填约束。
  - 类型/形状绕过：未发现新增问题；现有 `shape/stride/result` 校验仍在。
  - 边界越界：已存在静态边界检查，但空 `offsets` 路径会退化为全零默认值，不符合最新 spec 口径。
  - 错误处理缺失：发现问题。缺少“offsets 缺失”报错路径。
  - 状态污染：未发现。
  - 资源释放问题：不涉及。
- 改进建议：
  - 新建实现任务，收紧 `DmaViewOp` 的 `offsets` 必填约束，并在 `test/dialect/test_dma_dialect.py` 中补齐“缺失 offsets”负路径验证。
结论：需修改。经办人：朽木露琪亚。

时间：2026-03-28 19:55:00 +0800
任务：T-20260328-f27992e4
任务目标：收紧 dma.view offsets 必填约束，拒绝空 offsets 兼容路径，并补齐缺失 offsets 的负路径测试。
改动：
- 更新 `kernel_gen/dialect/dma.py`：
  - 将 `DmaViewOp.__init__` 收紧为仅接受显式 `source, offsets, shape, stride, result_type` 五参形式，移除旧版四参兼容路径。
  - `dma.view` verifier 改为无条件校验 `offsets` 长度与 rank 一致。
  - `_verify_static_view_bounds` 不再对空 `offsets` 做全零兼容，边界检查完全依赖显式传入的 offsets operand。
- 更新 `kernel_gen/dsl/emit_mlir.py`：
  - 将 `DmaViewAST` lowering 改为显式 lowering `expr.offset`，并以 `DmaViewOp(source, offsets, shape, stride, result_type)` 形式发射，避免 dialect 收紧后出现 DSL 回归。
- 更新 `test/dialect/test_dma_dialect.py`：
  - 在 `test_dma_view_rejects_invalid_offsets_or_bounds` 中新增“空 offsets 显式传入时 verifier 报错”负路径。
  - 新增“旧版四参构造调用直接触发 TypeError”检查，锁定兼容路径已被移除。
- 验证：
  - `python -m compileall kernel_gen/dialect/dma.py kernel_gen/dsl/emit_mlir.py test/dialect/test_dma_dialect.py`（exit 0）
  - `pytest -q test/dialect/test_dma_dialect.py -k dma_view`（exit 0，`4 passed, 23 deselected`）
  - `pytest -q test/dialect/test_dma_dialect.py`（exit 0，`27 passed`）
  - `pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_dma_view_lowering`（exit 0，`1 passed, 50 deselected`）
  - `pytest -q test/dsl/test_mlir_gen.py -k test_build_func_op_supports_dma_helper_calls`（exit 0，`1 passed, 99 deselected`）
  - 最小复现：空 offsets 触发 `offsets length must match rank`，旧版四参调用触发 `missing 1 required positional argument: 'result_type'`（exit 0）
结论：实现完成，可进入审查阶段。经办人：朽木露琪亚。
- 验证：未执行（本阶段仅 spec 修正）。

时间：2026-03-28 20:07:25 +0800
任务：T-20260328-2342246b
任务目标：复审 dma.view offsets 必填约束与 DSL lowering 联动修复。
审查范围：spec/dialect/dma.md、kernel_gen/dialect/dma.py、kernel_gen/dsl/emit_mlir.py、test/dialect/test_dma_dialect.py、test/dsl/test_emit_mlir.py。
问题列表：
- [P1] kernel_gen/dsl/emit_mlir.py（DmaViewAST lowering）
  - 现象：lowering 生成 dma.view 时使用 `_build_index_operands_from_layout(result_type.stride, ...)`，完全忽略 DSL `view(..., stride=...)` 参数；推导 result_type 也按 `size` 默认连续 stride，而不是来自 `expr.stride`。
  - 影响：DSL view 的 stride 语义被丢弃，无法表达非连续视图；`dma.view` 的 stride operand 与调用方传入不一致，静态边界校验基于错误 stride 可能放过越界或误报；与 spec/operation/dma.md 中 “view 的 stride 用于保留 subview 范围信息” 冲突。
  - 建议：在 type inference 和 lowering 中使用 `expr.stride` 生成 result_type.stride 与 dma.view 的 stride operand；确保 `offset/size/stride` 三者一致传递。
- [P2] test/dsl/test_emit_mlir.py::test_emit_mlir_dma_view_lowering
  - 现象：仅断言结果 shape，未验证 offsets/stride operand 是否按 DSL 参数传递。
  - 影响：上述 stride 语义丢失无法被测试捕获，易回归。
  - 建议：补充断言 `dma.view` 的 offsets/shape/stride operand 与 DSL 输入一致，至少覆盖非默认 stride 的用例。
漏洞与风险排查：
- 功能正确性：发现问题（DSL view stride 被忽略）。
- 边界条件：offsets 长度/负值/静态越界已覆盖；stride 丢失导致边界校验语义失真。
- 异常路径：DmaViewOp 相关 verifier 覆盖完整；DSL path 缺少对 stride 的显式校验。
- 可利用绕过路径：stride 被强制改为默认连续，可绕过调用方显式 stride 约束。
- 回归风险：中高，现有测试不足以捕获 stride 语义丢失。
- 可维护性：建议在 emit_mlir 中明确注释 view stride 的传递规则，并在测试中锁定。
验证：
- pytest -q test/dialect/test_dma_dialect.py -k dma_view（exit 0）
- pytest -q test/dsl/test_emit_mlir.py -k dma_view（exit 0）
结论：需修改。

时间：2026-03-28 20:23:36 +0800
任务：T-20260328-2078ba72
任务目标：修复 DmaViewAST lowering 的 stride 传递，确保 dma.view stride operand 与 result_type.stride 来自 expr.stride，并补强 test_emit_mlir_dma_view_lowering 的 offsets/stride 断言。
改动：
- 更新 kernel_gen/dsl/emit_mlir.py：DmaViewAST 类型推导使用 expr.stride 生成 result_type.stride。
- 更新 test/dsl/test_emit_mlir.py：在 test_emit_mlir_dma_view_lowering 中改为非默认 stride 场景，并新增 offsets/stride 常量断言与结果 stride 校验。
结论：pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_dma_view_lowering（exit=0）。
时间: 2026-03-28 20:46:00 +0800
任务: T-20260328-6cc45f75
任务目标: 收敛 operation/dma 非单位 stride 策略，明确与 dma dialect 的一致口径与限制。
改动:
- 经办人: 摸鱼小分队
- 更新 spec/operation/dma.md：明确 load/slice/store/deslice 允许非单位 stride 但进入方言层必须拒绝非单位 stride。
- 更新 spec/dialect/dma.md：补充 operation 层非单位 stride 与方言仅支持单位步长的差异与原因说明。
结论: 已完成（未执行测试）。
时间：2026-03-28 20:29:30 +0800
任务：T-20260328-2b436199
任务目标：复核 DmaViewAST lowering 的 stride/offset 传递与 test_emit_mlir_dma_view_lowering 的非默认 stride 断言是否闭环。
改动：
- 仅审查与核对，无代码修改。
- 核对文件：kernel_gen/dsl/emit_mlir.py、test/dsl/test_emit_mlir.py、spec/dsl/emit_mlir.md。
- 执行测试：pytest -q test/dsl/test_emit_mlir.py -k test_emit_mlir_dma_view_lowering（exit=0）。
结论：通过。
- 问题列表：无。
- 漏洞排查结果：
  - 输入校验绕过：未发现。
  - 类型/形状绕过：未发现。
  - 边界越界：未发现。
  - 错误处理缺失：未发现。
  - 状态污染：未发现。
  - 资源释放问题：未发现。
- 改进建议：未发现额外改进点。
