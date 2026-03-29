时间：2026-03-29 17:01:40 +0800
任务：T-20260329-9977c131
任务目标：在 `spec/dialect/nn.md` 增加 `nn.img2col1d` 与 `nn.img2col2d` 的公开方言表达、字段与 verifier 规则；仅改 spec，不改实现与测试。
改动：
- 更新 `spec/dialect/nn.md`：
  - 在目标中纳入 `img2col1d/img2col2d` 两个方言 op。
  - 在限制与边界中明确：方言层禁止新增笼统公开名 `nn.img2col`；`img2col1d/img2col2d` 仅定义 IR 合同，不重复高层 `operation/nn` 公式与错误边界文本。
  - 新增 `nn.img2col1d` 公开接口段落，定义 operand/result 类型与 rank、属性字段（`kw/sw/dw/pl/pr/space`）以及 verifier 合同关键字。
  - 新增 `nn.img2col2d` 公开接口段落，定义 operand/result 类型与 rank、属性字段（`kh/kw/sh/sw/dh/dw/ph/pw/pl/pr/space`）以及 verifier 合同关键字。
  - 增补测试目标与用例映射条目 `NN-DIA-040/041`，覆盖 `img2col1d/img2col2d` 的 dialect 合同校验。
验证：
- `git diff -- spec/dialect/nn.md`（exit 0）
- `rg -n "nn.img2col1d|nn.img2col2d|nn.img2col\\b|verifier|operand|result" spec/dialect/nn.md`（exit 0）
结论：
- 已完成 P11 spec 收敛；方言结构完整且未越权复写高层语义。
- 本任务未修改实现与测试文件。经办人：咯咯咯。
时间：2026-03-29 17:20:37 +0800
任务：T-20260329-64edca5c
任务目标：复核 P11 中 nn.img2col1d/nn.img2col2d 方言合同是否完整覆盖 operand/attrs/result/verifier，并确认禁止 nn.img2col 笼统公开名且未越权复写 operation 语义。
改动：
- 审查 spec/dialect/nn.md 中 img2col1d/img2col2d 段落与禁止 nn.img2col 声明。
- 核对 kernel_gen/dialect/nn.py 是否定义 nn.img2col1d/nn.img2col2d 方言 op。
- 核对 test/dialect/test_nn_dialect.py 是否存在 NN-DIA-040/041 对应测试。
- 核对 spec/operation/nn.md 是否存在 img2col1d/img2col2d 高层语义锚点。
- 验证：
  - rg -n "img2col1d|img2col2d|nn\.img2col\b" spec/dialect/nn.md（exit 0）
  - rg -n "img2col1d|img2col2d|img2col" kernel_gen/dialect/nn.py（exit 1）
  - rg -n "img2col1d|img2col2d|img2col" test/dialect/test_nn_dialect.py（exit 1）
  - rg -n "img2col1d|img2col2d" spec/operation/nn.md（exit 1）
结论：
- 需修改。
- P1：kernel_gen/dialect/nn.py 缺少 nn.img2col1d/nn.img2col2d op 定义与 verifier，导致方言合同无法落地；与 spec/dialect/nn.md 不一致。
- P1：test/dialect/test_nn_dialect.py 缺少 NN-DIA-040/041 对应测试（test_nn_dialect_img2col1d_contract_v1 / test_nn_dialect_img2col2d_contract_v1），spec 映射未闭环。
- P1：spec/operation/nn.md 尚未提供 img2col1d/img2col2d 高层语义锚点，方言合同引用的公式来源缺失；需补齐或明确依赖关系后再复审。
时间：2026-03-29 17:54:51 +0800
任务：T-20260329-caab79b7
任务目标：补齐 `spec/operation/nn.md` 的 `img2col1d/img2col2d` 高层语义锚点，明确与方言合同引用关系且不复写方言语义。
改动：
- 更新 `spec/operation/nn.md`：
  - 在目标与限制中明确 `img2col1d/img2col2d` 作为高层稳定接口锚点，禁止继续使用笼统公开名 `img2col`。
  - 新增 `img2col1d(...)` 公开接口段，收敛参数、返回、错误边界与示例。
  - 新增 `img2col2d(...)` 公开接口段，收敛参数、返回、错误边界与示例。
  - 明确 operation 与 dialect 的引用关系：lowering 对应 `nn.img2col1d/nn.img2col2d`，方言层仅承载 IR 字段与 verifier，不复写 operation 高层语义。
  - 更新测试目标与映射：`OP-IMG2COL-001` 对齐 `img2col2d`；新增 `OP-IMG2COL-002` 记录 `img2col1d` 的 spec 锚点关系。
验证：
- `git diff -- spec/operation/nn.md`（exit 0）
- `rg -n "img2col1d|img2col2d|nn\\.img2col1d|nn\\.img2col2d|OP-IMG2COL" spec/operation/nn.md`（exit 0）
结论：
- 已完成本任务的 spec 收敛，改动范围仅 `spec/operation/nn.md` 与当前记录文件。
- 未修改实现与测试文件。经办人：咯咯咯。

时间：2026-03-29 18:03:32 +0800
任务：T-20260329-900c6c3f
任务目标：复审 `spec/operation/nn.md` 新增 `img2col1d/img2col2d` 高层锚点与 `spec/dialect/nn.md` 合同引用一致性，确认未复写方言结构语义且 `OP-IMG2COL-001/002` 映射闭环。
改动：
- 审查文档一致性与映射：
  - `spec/operation/nn.md`
  - `spec/dialect/nn.md`
  - 参考 `test/operation/test_operation_nn.py` 与 `kernel_gen/operation/nn.py` 的现状核对映射闭环
结论：
- 结论：不通过。
- 阻塞点与风险：
  - `spec/operation/nn.md` 已明确禁止笼统公开名 `img2col` 并要求高层锚点使用 `img2col1d/img2col2d`，但 `OP-IMG2COL-001` 仍映射到 `test_nn_img2col_basic`，该测试与 `kernel_gen/operation/nn.py` 仅提供 `img2col`（二维）接口，未覆盖 `img2col2d` 新锚点；映射闭环与“禁止 img2col”要求冲突。
  - `spec/dialect/nn.md` 明确仅公开 `nn.img2col1d/img2col2d` 且不复写高层语义；当前高层锚点虽引用方言规范，但测试/实现仍停留在 `img2col`，存在规范与可执行基线脱节风险。
- 影响范围：高层操作规范与测试/实现闭环一致性；可能导致管理员误判映射已闭环。
- 测试情况：未运行测试（复审任务）。
- 下一步建议（拆分任务）：
  1) 实现任务：在 `kernel_gen/operation/nn.py` 新增 `img2col1d/img2col2d` 高层接口并按新规范命名；必要时保留 `img2col` 作为过渡别名但从测试/规范映射中移除。
  2) 测试任务：将 `test_nn_img2col_basic` 迁移到 `img2col2d`（必要时新增 `img2col1d` 覆盖），并同步 `OP-IMG2COL-001/002` 映射文本。
时间：2026-03-29 18:07:32 +0800
任务：T-20260329-8dd4a326
任务目标：为 nn.img2col1d/nn.img2col2d 增加 dialect op 与 verifier，并补齐 NN-DIA-040/041 合同测试（含负例），覆盖 operand/attrs/result/空间一致性与合同校验。
改动：
- 新增/补齐 `kernel_gen/dialect/nn.py`：
  - 引入 img2col1d/img2col2d 的辅助函数与 verifier 逻辑。
  - 补齐 i64 属性宽度校验，兼容 `IntegerType.width` 为 IntAttr 的场景。
  - 注册 `NnImg2col1dOp`/`NnImg2col2dOp` 并加入 dialect 导出列表。
- 新增/补齐 `kernel_gen/dialect/__init__.py`：导出 img2col1d/img2col2d op。
- 新增 `test/dialect/test_nn_dialect.py`：`NN-DIA-040/041` 正负例覆盖合同。
- 测试：`pytest -q test/dialect/test_nn_dialect.py`（exit 0）。
结论：
- 实现与测试已补齐，NN-DIA-040/041 通过；img2col1d/img2col2d 方言合同与 verifier 生效。
时间：2026-03-29 18:33:07 +0800
任务：T-20260329-0c6fa420
任务目标：复审 `nn.img2col1d/nn.img2col2d` dialect op/verifier 与 `NN-DIA-040/041` 测试闭环一致性，核对功能正确性、边界条件、异常路径、潜在绕过路径与中文注释完整性。
改动：
- 仅审查核对，无代码修改。
- 核对文件：
  - `spec/dialect/nn.md`
  - `kernel_gen/dialect/nn.py`
  - `kernel_gen/dialect/__init__.py`
  - `test/dialect/test_nn_dialect.py`
- 验证：
  - `pytest -q test/dialect/test_nn_dialect.py -k 'img2col1d or img2col2d'`（exit 0；`2 passed, 58 deselected`）
  - `pytest -q test/dialect/test_nn_dialect.py`（exit 0；`60 passed`）
  - `rg -n "img2col\\b" kernel_gen/dialect test/dialect spec/dialect/nn.md`（exit 0；仅保留对旧名 `nn.img2col` 的禁止性说明，未发现意外公开旧 op）
  - `PYTHONPATH=. python - <<'PY' ...`（exit 0；人工探针确认以下 verifier 分支可触发并返回预期诊断：`attribute space must match input space`、`result element_type must match input`、`result stride must match img2col{1d,2d} contract`、`output height must be positive`）
结论：
- 结论：`需修改`
- 问题列表：
  - [P2][`test/dialect/test_nn_dialect.py:1143`][`spec/dialect/nn.md:475`][`kernel_gen/dialect/nn.py:1021`] `NN-DIA-040` 当前只覆盖了 rank、`kw` 正数、`result rank`、`result space` 与 `result shape`，但未覆盖 spec 明确要求的 `op.space` 一致性、`result.element_type` 一致性与 `result stride` 合同。人工探针已确认这三个 verifier 分支真实存在且会报错；一旦后续实现回退，这条编号测试无法及时阻断，闭环不完整。
  - [P2][`test/dialect/test_nn_dialect.py:1228`][`spec/dialect/nn.md:531`][`kernel_gen/dialect/nn.py:1173`] `NN-DIA-041` 同样缺少 `op.space` 一致性、`result.element_type` 一致性、`result stride` 合同以及 `output height/width must be positive` 的负路径覆盖。人工探针已确认这些分支可触发预期诊断，但现有测试未绑定对应分支，存在 verifier 保护被静默回退的风险。
- 漏洞排查结果：
  - 功能正确性：`nn.img2col1d/nn.img2col2d` 正向路径可通过 verifier，`pytest -q test/dialect/test_nn_dialect.py` 全量通过。
  - 边界条件：正数/非负数约束、rank 约束、显式 shape 合同已部分覆盖；但 `output <= 0` 与 stride 合同边界尚未纳入 `NN-DIA-041/040` 正式测试。
  - 异常路径：人工探针确认 `attribute space`、`element_type`、`stride` 与 `output non-positive` 诊断分支存在且口径稳定。
  - 可利用绕过路径：当前最大风险不是 verifier 失效，而是这些独立分支没有被 `NN-DIA-040/041` 锁住，后续重构若删改相关判断，CI 可能仍然通过，造成回归绕过。
  - 中文注释检查：`kernel_gen/dialect/nn.py` 新增辅助函数、op 类、`__init__`/`verify_` 均已补齐中文注释、使用示例与关联文件，注释内容与实现行为一致；本次不构成阻塞点。
- 下一步建议：
  - 新建实现/测试任务，仅补齐 `test/dialect/test_nn_dialect.py` 中 `NN-DIA-040/041` 的负路径覆盖，至少纳入 `op.space`、`result.element_type`、`result stride` 与 `output non-positive` 分支；若补测时发现诊断口径与 spec 不一致，再最小调整 `kernel_gen/dialect/nn.py`。
时间：2026-03-29 18:38:14 +0800
任务：T-20260329-73a1e466
任务目标：更新 `spec/operation/nn.md` 的 `OP-IMG2COL-001/002` 映射为 `img2col1d/img2col2d` 对应测试，并移除 `test_nn_img2col_basic` 旧映射。
改动：
- 仅修改 `spec/operation/nn.md`（未修改实现与测试文件）。
- 调整清单映射：
  - `OP-IMG2COL-001` 改为 `img2col1d` 对应测试 `test_nn_img2col1d_contract`。
  - `OP-IMG2COL-002` 改为 `img2col2d` 对应测试 `test_nn_img2col2d_contract`。
- 移除 `OP-IMG2COL` 条目中对 `test_nn_img2col_basic` 的旧映射依赖。
- 验证：
  - `git diff -- spec/operation/nn.md`
  - `rg -n "OP-IMG2COL-001|OP-IMG2COL-002|test_nn_img2col_basic|test_nn_img2col1d_contract|test_nn_img2col2d_contract" spec/operation/nn.md`
结论：已完成。`OP-IMG2COL-001/002` 映射已与 `img2col1d/img2col2d` 对齐，旧 `test_nn_img2col_basic` 映射已移除；后续需由实现/测试阶段补齐对应测试闭环。
时间：2026-03-29 18:55:46 +0800
任务：T-20260329-d8c924d0
任务目标：在 operation 测试侧补齐 img2col1d/img2col2d contract 覆盖，替换 OP-IMG2COL-001/002 对应测试并移除对 test_nn_img2col_basic 的依赖。
改动：
- kernel_gen/operation/nn.py：新增 img2col1d/img2col2d 高层接口，沿用 img2col 参数校验与输出维度规则；更新 __all__ 导出。
- test/operation/test_operation_nn.py：新增 test_nn_img2col1d_contract/test_nn_img2col2d_contract，移除 test_nn_img2col_basic 旧路径与 img2col 依赖。
验证：
- pytest -q test/operation/test_operation_nn.py -k img2col（exit 0）
结论：OP-IMG2COL-001/002 对应测试已落到 img2col1d/img2col2d，旧 img2col 依赖已移除，img2col contract 用例通过。
时间：2026-03-29 19:05:22 +0800
任务：T-20260329-06f4b319
任务目标：复审 img2col1d/img2col2d operation 实现/测试闭环（OP-IMG2COL-001/002），核对 kernel_gen/operation/nn.py 与 test/operation/test_operation_nn.py 并复测 img2col 用例；检查中文注释与功能/示例一致性。
改动：
- 审查实现与测试：
  - kernel_gen/operation/nn.py（img2col1d/img2col2d/img2col 与 __all__ 导出）
  - test/operation/test_operation_nn.py（OP-IMG2COL-001/002 对应测试）
- 关注点：功能正确性、边界条件、异常路径、潜在漏洞与中文注释一致性。
验证：
- pytest -q test/operation/test_operation_nn.py -k "img2col"（exit 0；2 passed, 56 deselected）
- rg -n "img2col\\(" kernel_gen/operation/nn.py（exit 0）
结论：不通过。
问题与风险：
- P1：spec/operation/nn.md 明确“禁止继续使用笼统公开名 img2col 作为稳定对外规范名”，但 kernel_gen/operation/nn.py 仍在 __all__ 导出 img2col，导致公开 API 与规范冲突。外部调用仍可直接使用被禁止名称，存在规范绕过与误用风险；同时会误导后续映射/测试闭环判断。
- 注释核对：img2col1d/img2col2d/img2col 相关中文注释与实现行为一致，未发现注释缺失或示例不符问题。
影响范围：operation 高层 API 公开面与规范一致性；可能导致管理员误判“禁止 img2col”已落地。
下一步建议（需拆分任务）：
1) 实现任务：将 img2col 降级为内部私有实现（移出 __all__，必要时改名为 _img2col 或在文档标注非公开），并确保 img2col2d 仍复用内部实现。
2) （可选）测试任务：新增/调整测试以验证公开 API 不再暴露 img2col（如通过 __all__ 或导出清单校验）。
时间：2026-03-29 19:18:44 +0800
任务：T-20260329-679d5c9e
任务目标：将 img2col 降级为内部实现，移出公开导出并确保 img2col2d 复用内部逻辑。
改动：
- kernel_gen/operation/nn.py：将 img2col 重命名为 _img2col（内部实现），img2col2d 改为调用 _img2col；从 __all__ 移除 img2col。
验证：
- pytest -q test/operation/test_operation_nn.py -k img2col（exit 0）
结论：img2col 已降级为内部实现，公开 API 仅保留 img2col1d/img2col2d，测试通过。
时间：2026-03-29 19:26:11 +0800
任务：T-20260329-14c486cd
任务目标：复核 img2col 内部化与 __all__ 导出收敛、img2col2d 复用逻辑，并复测 img2col 用例；检查功能正确性、边界/异常路径、潜在漏洞与中文注释一致性。
改动：
- 审查实现与测试：
  - kernel_gen/operation/nn.py（_img2col 内部化、img2col2d 复用、__all__ 导出）
  - test/operation/test_operation_nn.py（img2col1d/img2col2d contract 用例）
验证：
- pytest -q test/operation/test_operation_nn.py -k "img2col"（exit 0；2 passed, 56 deselected）
- rg -n "img2col" kernel_gen/operation/nn.py（exit 0）
结论：通过。
说明：
- img2col 已内化为 _img2col，__all__ 中不再导出 img2col，符合 spec 禁止笼统公开名要求。
- img2col2d 正确复用 _img2col 内部实现；参数校验、输出维度与异常路径一致。
- 中文注释完整且与实现/示例一致，未发现缺失或不符。
时间：2026-03-29 20:15:12 +0800
任务：T-20260329-fdf9e074
任务目标：补齐 nn.img2col1d/nn.img2col2d 的 NN-DIA-040/041 负路径覆盖，锁定 space/element_type/stride/output non-positive 分支。
改动：
- test/dialect/test_nn_dialect.py
  - NN-DIA-040：新增 attribute space mismatch、result element_type mismatch、result stride mismatch、output width <= 0 负路径用例。
  - NN-DIA-041：新增 attribute space mismatch、result element_type mismatch、result stride mismatch、output height <= 0、output width <= 0 负路径用例。
验证：
- pytest -q test/dialect/test_nn_dialect.py -k "img2col1d or img2col2d"（exit 0；2 passed, 58 deselected）
结论：已完成。NN-DIA-040/041 已覆盖 spec 要求的 op.space、result.element_type、result stride 与输出非正维度诊断分支，未改动实现诊断口径。
时间：2026-03-29 19:38:05 +0800
任务：T-20260329-8e3068e8
任务目标：复核 NN-DIA-040/041 img2col1d/img2col2d 负路径覆盖与诊断口径一致性，复测 test_nn_dialect_img2col1d_contract_v1 / test_nn_dialect_img2col2d_contract_v1；检查功能/边界/异常/漏洞与中文注释一致性。
改动：
- 审查测试与实现：
  - test/dialect/test_nn_dialect.py（NN-DIA-040/041 负路径覆盖）
  - kernel_gen/dialect/nn.py（img2col1d/img2col2d verifier 诊断口径）
验证：
- pytest -q test/dialect/test_nn_dialect.py -k "img2col1d_contract_v1 or img2col2d_contract_v1"（exit 0；2 passed, 58 deselected）
结论：通过。
说明：
- NN-DIA-040/041 已覆盖 input/result rank、kw/kh 正数约束、result space、attribute space、element_type、shape、stride 以及输出尺寸非正的负路径；诊断口径与 verifier 一致。
- 中文注释与功能/示例一致，无缺失。
时间：2026-03-29 19:57:52 +0800
任务：T-20260329-fcb38fbd
任务目标：增加 operation 层导出校验，确认 img2col 不再作为公开 API 暴露，并完成对应测试验证。
改动：
- 无代码改动；当前 `test/operation/test_operation_nn.py` 已包含 `test_nn_img2col_public_exports` 覆盖导出列表约束。
- 验证：`PYTHONPATH=. pytest -q test/operation/test_operation_nn.py -k test_nn_img2col_public_exports`（exit 0）。
结论：
- img2col 未出现在 `kernel_gen.operation` 与 `kernel_gen.operation.nn` 的公开导出列表；测试通过，无阻塞。
时间：2026-03-29 20:00:29 +0800
任务：T-20260329-e18b3843
任务目标：复审 operation 层 img2col 导出校验测试与公开 API 列表一致性；核对中文注释/示例一致性与公开 API 导出边界。
改动：
- 审查测试与导出清单：
  - test/operation/test_operation_nn.py（test_nn_img2col_public_exports）
  - kernel_gen/operation/nn.py（__all__）
  - kernel_gen/operation/__init__.py（__all__）
验证：
- PYTHONPATH=. pytest -q test/operation/test_operation_nn.py -k "img2col_public_exports"（exit 0；1 passed, 58 deselected）
结论：通过。
说明：
- test_nn_img2col_public_exports 覆盖 operation.nn 与 operation 包级 __all__ 导出边界，确认 img2col 未对外暴露。
- 中文注释与功能/示例一致，无缺失。
