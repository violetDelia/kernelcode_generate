- 时间：`2026-03-29 16:57:58 +0800`
- 任务：`T-20260329-e9212574`
- 任务目标：在 `spec/operation/nn.md` 将笼统 `img2col` 拆分为 `img2col1d` / `img2col2d` 高层公开契约，明确输出形状、参数校验、dtype/space/format/stride 继承规则与错误边界，并显式禁止继续扩展 `img2col(...)` 公开名。
- 改动：
  - 仅修改 `spec/operation/nn.md`。
  - 在“功能简介/目标/限制与边界”补入 `img2col1d` 与 `img2col2d`，并新增 `img2col` 为 forbidden public name 的约束。
  - 新增公开接口：
    - `img2col1d(value, kw, sw=1, dw=1, pl=0, pr=0)`：定义输入 `rank-3 Memory[N,C,W]`、输出 `Memory[N,C*Kw,Wo]`、`Wo` 公式、结果 `dtype/space/format` 继承与默认连续 `stride`、以及 `reject` 边界。
    - `img2col2d(value, kh, kw, sh=1, sw=1, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)`：定义输入 `rank-4 Memory[N,C,H,W]`、输出 `Memory[N,C*Kh*Kw,Ho*Wo]`、`Ho/Wo` 公式、结果 `dtype/space/format` 继承与默认连续 `stride`、以及 `reject` 边界。
  - 更新测试目标与功能清单：移除笼统 `img2col` 描述，拆分为 `img2col1d`/`img2col2d` 与 forbidden 名称约束条目。
  - 执行验证命令：
    - `git diff -- spec/operation/nn.md`
    - `rg -n "img2col1d|img2col2d|img2col\\b|rank|stride|forbidden" spec/operation/nn.md`
  - 未修改实现与测试代码。
- 结论：`已完成`。`spec/operation/nn.md` 已形成 `img2col1d/img2col2d` 双契约并显式禁止笼统 `img2col` 公开名，满足当前 spec 阶段要求；后续进入复审阶段。
时间：2026-03-29 17:13:49 +0800
任务：T-20260329-878a69fa
任务目标：复审 spec/operation/nn.md 中 img2col1d/img2col2d 拆分契约，核对输入 rank、输出形状公式、dtype/space/format/stride 规则、reject 边界与 forbidden public name(img2col) 是否完整一致。
审查范围：
- spec/operation/nn.md
- test/operation/test_operation_nn.py（核对映射/用例一致性）
问题列表：
- [P1] spec/operation/nn.md:959-961 与 test/operation/test_operation_nn.py:970-1003
  - 现象：spec 将 OP-IMG2COL-001/002/003 映射到 test_nn_img2col_basic，但该测试仅调用旧的 img2col(...)，未覆盖 img2col1d/img2col2d 拆分语义，也未验证“forbidden public name(img2col)”被拒绝，反而依赖 img2col 成功路径。
  - 风险：spec 声称的拆分契约与 forbidden name 无法被现有测试闭环，回归时会出现“spec 已拆分但实现仍保留 img2col”的隐蔽不一致；管理员无法根据映射判断该规则是否已落地。
  - 建议：新增/替换测试覆盖 img2col1d/img2col2d 正向与负向，并增加 img2col 禁止使用的断言；或调整 spec 映射与测试编号，确保映射可追溯且不再依赖 img2col 成功路径。
- [P2] spec/operation/nn.md:765、819
  - 现象：img2col1d/img2col2d 规定 out.format 继承 value.format，但 out.stride 固定为连续行主序默认步幅。
  - 风险：当输入 format 非 Norm 时，输出 format/stride 可能自相矛盾，导致下游依据 format 推断布局时产生错误（潜在布局误解/越界风险）。
  - 建议：明确 out.format 是否应固定为 Farmat.Norm（与默认 stride 一致），或补充约束说明 format 可与 stride 解耦且下游不得依赖 format 推断布局。
漏洞与风险排查：
- 功能正确性：发现问题（测试映射与禁用 img2col 规则不一致）。
- 边界条件：发现问题（forbidden public name 未有对应拒绝测试）。
- 异常路径：img2col1d/img2col2d 的参数 reject 已在 spec 写明，但当前测试未覆盖；需补测。
- 潜在漏洞：format/stride 不一致可能引发下游布局误判。
结论：需修改。
验证：未执行测试（本次为 spec 复审）。
- 时间：`2026-03-29 17:30:41 +0800`
- 任务：`T-20260329-0f06a95f`
- 任务目标：澄清 `img2col1d/img2col2d` 输出 `format/stride` 规则，调整 `OP-IMG2COL-001/002/003` 映射口径，确保不再依赖 `img2col(...)` 成功路径。
- 改动：
  - 仅修改 `spec/operation/nn.md`。
  - 将 `img2col1d` 返回约束从 `out.format == value.format` 收敛为 `out.format == Farmat.Norm`，并与默认连续行主序 `out.stride` 规则保持一致。
  - 将 `img2col2d` 返回约束从 `out.format == value.format` 收敛为 `out.format == Farmat.Norm`，并与默认连续行主序 `out.stride` 规则保持一致。
  - 更新“测试目标”中 `img2col` 相关条目，明确 `img2col1d/img2col2d` 需验证 `format=Farmat.Norm + 默认 stride`，且 forbidden public name 校验不依赖 `img2col(...)` 成功路径。
  - 调整映射清单：
    - `OP-IMG2COL-001 -> test_nn_img2col1d_contract`
    - `OP-IMG2COL-002 -> test_nn_img2col2d_contract`
    - `OP-IMG2COL-003 -> test_nn_img2col_forbidden_public_name`
  - 执行验证：
    - `git diff -- spec/operation/nn.md`
    - `rg -n "img2col1d|img2col2d|img2col\\b|format|stride|OP-IMG2COL|test_nn_img2col_basic|forbidden" spec/operation/nn.md`
- 结论：`已完成`。`img2col1d/img2col2d` 的输出布局规则已去歧义，`OP-IMG2COL-001/002/003` 映射已与旧 `img2col` 成功路径解耦；后续需进入实现/测试阶段补齐对应测试函数并验证链路闭环。
- 时间：`2026-03-29 17:50:04 +0800`
- 任务：`T-20260329-e6a6d3a9`
- 任务目标：按 OP-IMG2COL-001/002/003 补齐 img2col1d/img2col2d 合约测试与 forbidden public name 校验，移除 legacy img2col 成功路径依赖并与 spec format/stride 口径一致。
- 改动：
  - `kernel_gen/operation/nn.py`：新增 `img2col1d`/`img2col2d` 实现与中文注释；将 `img2col` 设为 forbidden public name 并抛出统一错误；更新 `__all__` 去除 `img2col`、加入 `img2col1d/img2col2d`。
  - `test/operation/test_operation_nn.py`：新增 `test_nn_img2col1d_contract`、`test_nn_img2col2d_contract`、`test_nn_img2col_forbidden_public_name`，不再依赖 legacy img2col 成功路径；补齐 format=Farmat.Norm 与默认 stride 断言。
- 测试：
  - `pytest -q test/operation/test_operation_nn.py -k img2col`（exit 0；3 passed, 56 deselected）
- 结论：`已完成`，进入复审。
- 时间：`2026-03-29 18:09:41 +0800`
- 任务：`T-20260329-e6e76f9b`
- 任务目标：复核 img2col1d/2d 合同补齐与禁止 img2col 公开名用例，核对 spec/实现/测试一致；检查边界/异常/潜在漏洞，并确认函数中文注释与功能/示例一致。
- 改动：
  - 审查范围：`spec/operation/nn.md`、`kernel_gen/operation/nn.py`、`test/operation/test_operation_nn.py`。
  - 复测命令：`pytest -q test/operation/test_operation_nn.py -k "img2col"`（exit 0；3 passed, 56 deselected）。
- 结论：通过。
  - 功能正确性：img2col1d/img2col2d 输出形状、dtype/space/format/stride 与公式推导一致；img2col 禁用入口抛错且不出现在 `__all__`。
  - 边界条件：正/非负参数校验与输出非正宽高拒绝路径覆盖到位。
  - 异常路径：非 Memory、rank 不匹配、非法参数类型/取值均有显式报错。
  - 可利用绕过路径：未发现可绕过禁用 img2col 或参数校验的路径。
  - 回归风险：未见新增回归风险点。
  - 漏洞排查：未发现越界/类型绕过/错误处理缺失等风险。
  - 可维护性改进建议：无（现有注释与示例匹配，结构清晰）。
