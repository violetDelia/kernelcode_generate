时间：2026-03-29 17:18:09 +0800
任务：T-20260329-c0025bb8
任务目标：在 `spec/include/cpu/cpu.md` 为 W0 P16 补齐 `cpu::img2col1d(...)` / `cpu::img2col2d(...)` 的 CPU include 层公开接口契约，严格保留计划书要求的目标、边界、注意事项、依赖、验证命令与验收标准，仅修改该 spec 文件。
改动：
- 新建记录文件并核对任务前置：
  - `worktree=/home/lfr/kernelcode_generate/wt-20260329-p16-cpu-api` 可访问。
  - 指定记录文件原先不存在，已按约定创建目录。
  - 主仓 `DONE.md` 已记录 `T-20260329-e9212574`（W0 P10 spec）于 `2026-03-29 16:59:26 +0800` 完成，可按“与 P10 最终文本一致”的口径验收本任务。
- 更新 `spec/include/cpu/cpu.md`：
  - 在模块简介、目标、限制与边界中补充 `img2col1d/img2col2d` CPU 叶子接口定位，明确其仅服务 CPU emitter，禁止反向约束 AST / `nn dialect` / `build_func_op(...)` / pass。
  - 新增 `cpu::img2col1d(value, out, kw, sw, dw, pl, pr)` 公开接口契约，写明固定签名、输入/输出 rank、`Wo` 公式、`shape-formula-check`、`stride-consistency-check` 与 reject 边界。
  - 新增 `cpu::img2col2d(value, out, kh, kw, sh, sw, dh, dw, ph, pw, pl, pr)` 公开接口契约，写明固定签名、输入/输出 rank、`Ho/Wo` 公式、`shape-formula-check`、`stride-consistency-check` 与 reject 边界。
  - 新增 `额外补充` 段，完整保留计划书 P16 要求的 `目标 / 边界 / 注意事项 / 依赖 / 验证命令 / 验收标准`，并把 `describe_cpu_api_contract(...)` 标注为验收辅助伪名、不得实现为产品接口。
- 自检：
  - `git diff --check -- spec/include/cpu/cpu.md`（exit 0）
结论：
- 结论：已完成 P16 spec 收敛，变更范围仅 `spec/include/cpu/cpu.md`。
- 测试情况：本任务为 spec 阶段，无自动化测试命令；按计划书要求采用人工验收口径。
- 下一步建议：创建实现/测试后续任务，基于本文接口契约在 `include/cpu/Nn.h` 与对应测试中补齐 `cpu::img2col1d/img2col2d` 的实现与验证。

时间：2026-03-29 17:32:32 +0800
任务：T-20260329-5aebee9c
任务目标：基于 `spec/include/cpu/cpu.md` 的 P16 契约，在 `include/cpu/Nn.h` 与 `test/include/cpu/test_nn.py` 补齐 `cpu::img2col1d/cpu::img2col2d` 的公开实现与验证，覆盖固定签名、rank/shape/stride 前置条件、禁止笼统 `cpu::img2col` 公开名，并与上游 `img2col1d/img2col2d` 命名保持一致。
改动：
- 更新 `include/cpu/Nn.h`：
  - 为 `detail` 命名空间中的辅助函数补齐中文注释，满足“所有函数必须有注释”的新规。
  - 新增 `contract_or_trap`、`has_contiguous_rank`、`compute_img2col1d_output_width`、`verify_img2col1d_contract`、`compute_img2col2d_output_extent`、`verify_img2col2d_contract` 等内部辅助函数，用于固定 rank/shape/stride 与参数前置条件检查。
  - 新增公开函数 `cpu::img2col1d(const cpu::Memory<float>&, cpu::Memory<float>&, ...)` 与 `cpu::img2col2d(const cpu::Memory<float>&, cpu::Memory<float>&, ...)`，按 P16 契约实现固定 `float` 签名，并在 padding 越界时写入 `0.0f`。
- 更新 `test/include/cpu/test_nn.py`：
  - 新增 `_compile_expect_failure(...)` 与 `_compile_and_run_expect_failure(...)` 测试辅助函数，并补齐中文文档注释。
  - 新增 `INC-NN-013..018`，覆盖 `img2col1d/img2col2d` 的固定签名、成功路径、rank 前置条件、shape 前置条件、stride 前置条件，以及禁止公开 `cpu::img2col` 名称的编译失败路径。
- 自检：
  - `pytest -q test/include/cpu/test_nn.py` -> `18 passed in 1.61s`
  - `git diff --check -- include/cpu/Nn.h test/include/cpu/test_nn.py`（exit 0）
结论：
- 结论：已完成 `cpu::img2col1d/img2col2d` 的 CPU include 层实现与测试补齐，未修改 spec 文件。
- 测试情况：`pytest -q test/include/cpu/test_nn.py` 通过；新增测试已覆盖固定签名、rank/shape/stride 前置条件与禁止笼统公开名。
- 下一步建议：创建审查任务，重点核对 `float` 固定签名、前置条件 trap 顺序，以及新增测试是否完整映射 P16 契约。

时间：2026-03-29 17:53:33 +0800
任务：T-20260329-99a73e51
任务目标：审查 `cpu::img2col1d/img2col2d` 的固定 `float` 签名、rank/shape/stride 契约 trap 与禁止 `cpu::img2col` 公开名测试，核对功能正确性、边界条件、异常路径、潜在漏洞，并检查函数中文注释与功能/示例一致性。
改动：
- 审查实现/文档/测试一致性：
  - `include/cpu/Nn.h`
  - `spec/include/cpu/cpu.md`
  - `test/include/cpu/test_nn.py`
- 复核固定签名、契约 trap 与禁止公开名测试覆盖。
结论：
- 结论：不通过。
- 阻塞点与风险：
  - `include/cpu/Nn.h` 中 `verify_img2col2d_contract(...)` 与 `img2col2d(...)` 的中文注释使用示例参数数量与真实签名不一致（示例给出 12 个标量参数，实际仅 10 个），违反“函数注释与功能/示例一致”的新规，容易误导调用方与验收核对。
  - `spec/include/cpu/cpu.md` 的 `cpu::img2col2d<float>(...)` 使用示例同样给出 12 个标量参数，与固定签名不一致，影响契约文档可信度与审核一致性。
- 影响范围：文档/注释层面的 API 使用示例；不直接影响运行时，但会误导实现与测试基线。
- 测试情况：未运行测试（审查任务）。
- 下一步建议：
  - 拆分修复任务：
    1) 修正 `spec/include/cpu/cpu.md` 的 `img2col2d` 使用示例参数数量与签名一致。
    2) 修正 `include/cpu/Nn.h` 中 `verify_img2col2d_contract` 与 `img2col2d` 注释使用示例的参数数量与签名一致。
  - 修复后重新复审。

时间：2026-03-29 18:01:29 +0800
任务：T-20260329-d48dede9
任务目标：修正 `spec/include/cpu/cpu.md` 中 `cpu::img2col2d<float>(...)` 使用示例参数数量为固定签名 10 参数，保持 P16 契约文本一致。
改动：
- 更新 `spec/include/cpu/cpu.md`（仅 spec）：
  - 在 `cpu::img2col2d` 参数说明中新增固定签名约束：除 `value/out` 外必须且仅允许 10 个 `long long` 标量参数（`kh/kw/sh/sw/dh/dw/ph/pw/pl/pr`）。
  - 在 `cpu::img2col2d<float>(...)` 示例后新增口径注释，明确示例对应固定签名“value/out + 10 个标量参数”。
  - 在注意事项中新增规则，禁止把 `value/out` 后的参数个数扩展为非 10 个，避免示例与签名再次漂移。
验证：
- `git diff -- spec/include/cpu/cpu.md`（exit 0）
- `rg -n "img2col2d<float>|10 个 long long|固定签名|kh/kw/sh/sw/dh/dw/ph/pw/pl/pr" spec/include/cpu/cpu.md`（exit 0）
结论：
- 已完成本任务要求，变更仅在 `spec/include/cpu/cpu.md` 与本记录文件。
- 未修改实现与测试文件。经办人：咯咯咯。

时间：2026-03-29 18:04:54 +0800
任务：T-20260329-7f0eef2b
任务目标：复审 `spec/include/cpu/cpu.md` 中 `cpu::img2col2d<float>(...)` 示例与固定签名是否一致，并确认 P16 契约文本与 `include/cpu/Nn.h` 注释口径无漂移。
改动：
- 仅审查核对，无代码修改。
- 核对文件：
  - `spec/include/cpu/cpu.md`
  - `include/cpu/Nn.h`
  - `test/include/cpu/test_nn.py`
- 复测与复现：
  - `pytest -q test/include/cpu/test_nn.py -k "img2col2d and (success_and_signature or contract_violation_traps)"`（exit 0；`2 passed, 16 deselected`）
  - 以最小 C++ 片段复现 `cpu::img2col2d<float>(...)` 示例：`g++ -std=c++17 -I. -c <tmp>.cc`（exit 1；关键报错：`error: expected primary-expression before ‘float’`）
  - 以最小 C++ 片段复现头文件真实调用 `cpu::img2col2d(...)`：`g++ -std=c++17 -I. -c <tmp>.cc`（exit 0）
- 审查结论所依据的关键位置：
  - `spec/include/cpu/cpu.md:839`：示例仍写作 `cpu::img2col2d<float>(...)`
  - `spec/include/cpu/cpu.md:846`：固定签名文本为非模板 `void cpu::img2col2d(const cpu::Memory<float>& value, cpu::Memory<float>& out, ...)`
  - `include/cpu/Nn.h:623`、`include/cpu/Nn.h:633`：头文件注释示例与真实定义均为非模板 `cpu::img2col2d(...)`
  - `spec/include/cpu/cpu.md:792`：同文件 `cpu::img2col1d<float>(...)` 也存在同类模板示例漂移
结论：
- 结论：`需修改`
- 问题列表：
  - [P1][`spec/include/cpu/cpu.md:839`] `cpu::img2col2d<float>(...)` 示例与固定签名、头文件注释和真实声明不一致。`include/cpu/Nn.h` 的公开接口是非模板函数 `void img2col2d(...)`，按 spec 示例字面复制会直接编译失败。风险：调用方依据 spec 抄写示例会得到不可用代码，且会误判该接口是模板函数，破坏 P16 “固定签名”契约的可信度。
  - [P1][`spec/include/cpu/cpu.md:792`] `cpu::img2col1d<float>(...)` 存在同类示例漂移。虽然本次任务点名 `img2col2d`，但 P16 契约文本要求 `img2col1d/img2col2d` 作为稳定 CPU 公开接口成组冻结；若只修 2D、不修 1D，同类错误仍会留在同一文档中，后续复审无法判定整段契约口径稳定。
- 漏洞排查结果：
  - 功能正确性：`include/cpu/Nn.h` 中 `img2col2d(...)` 真实固定签名与实现一致，目标子测通过。
  - 边界条件：`img2col2d` 的 shape/rank 契约失败路径测试仍通过，未见边界校验回退。
  - 异常路径：CPU include 层采用 `contract_or_trap`，当前复测未见错误路径缺失。
  - 可利用绕过路径：未发现输入校验绕过、越界写入、状态污染或资源释放问题；本次问题集中在 spec 示例失真。
  - 注释一致性：`include/cpu/Nn.h` 当前中文注释存在、且 `img2col2d` 注释示例与真实签名一致；漂移集中在 `spec/include/cpu/cpu.md` 示例文本。
- 改进建议：
  - 新建一个仅修改 `spec/include/cpu/cpu.md` 的 spec 任务，统一去掉 `cpu::img2col1d<float>(...)` / `cpu::img2col2d<float>(...)` 示例中的模板实参，改为与 `include/cpu/Nn.h` 固定非模板签名一致的调用形式；修复前不得判定通过。
时间：2026-03-29 18:09:42 +0800
任务：T-20260329-ea17e760
任务目标：修正 include/cpu/Nn.h 中 verify_img2col2d_contract/img2col2d 中文注释示例参数数量为固定签名 10 参数，保持注释与实现一致。
改动：
- 更新 include/cpu/Nn.h 注释使用示例：
  - verify_img2col2d_contract 示例改为显式列出 10 个标量参数名（kh/kw/sh/sw/dh/dw/ph/pw/pl/pr）。
  - img2col2d 示例改为显式列出 10 个标量参数名（kh/kw/sh/sw/dh/dw/ph/pw/pl/pr）。
验证：未执行测试（仅注释更新）。
结论：已完成。

时间：2026-03-29 18:13:38 +0800
任务：T-20260329-a8b6451b
任务目标：修正 `spec/include/cpu/cpu.md` 中 `cpu::img2col1d/img2col2d` 使用示例调用口径，移除无效模板实参 `<float>`，与 `include/cpu/Nn.h` 固定非模板签名和 `test/include/cpu/test_nn.py` 调用一致。
改动：
- 仅修改 `spec/include/cpu/cpu.md`：
  - 将 `cpu::img2col1d<float>(...)` 示例改为 `cpu::img2col1d(...)`。
  - 将 `cpu::img2col2d<float>(...)` 示例改为 `cpu::img2col2d(...)`。
- 未修改实现与测试文件。
验证：
- `git diff -- spec/include/cpu/cpu.md`（exit 0）
- `rg -n "img2col1d<|img2col2d<|cpu::img2col1d\\(|cpu::img2col2d\\(" spec/include/cpu/cpu.md`（exit 0；仅保留非模板调用与签名文本）
结论：
- 已完成本任务要求，spec 示例调用已与 `include/cpu/Nn.h` 固定非模板签名、`test/include/cpu/test_nn.py` 调用口径一致。
- 经办人：咯咯咯。
- 时间：`2026-03-29 18:18:52 +0800`
- 任务：`T-20260329-bf66ee12`
- 任务目标：核对 spec/include/cpu/cpu.md 中 cpu::img2col1d/img2col2d 示例调用已移除 <float>，并与 include/cpu/Nn.h 固定非模板签名、test/include/cpu/test_nn.py 当前调用口径一致；检查边界/异常/潜在漏洞与中文注释一致性。
- 改动：
  - 审查范围：`spec/include/cpu/cpu.md`、`include/cpu/Nn.h`、`test/include/cpu/test_nn.py`。
  - 未执行测试（本次为复审一致性核对）。
- 结论：通过。
  - 功能正确性：spec 示例与 Nn.h 非模板签名一致（均为 `cpu::img2col1d/2d(...)`，无 `<float>`）。
  - 边界条件/异常路径：spec 前置条件与 Nn.h `verify_img2col1d/2d_contract` 保持一致，测试用例覆盖签名与契约失败路径。
  - 潜在漏洞/绕过：未发现通过模板或签名漂移绕过稳定接口约束的路径。
  - 中文注释：img2col1d/img2col2d 注释为中文且与功能/示例一致。
  - 可维护性建议：无。
- 时间：`2026-03-29 18:28:38 +0800`
- 任务：`T-20260329-9db512df`
- 任务目标：核对 include/cpu/Nn.h 中 img2col2d/verify_img2col2d_contract 注释示例参数数量与固定签名一致，并检查中文注释一致性与潜在风险。
- 改动：
  - 审查范围：`include/cpu/Nn.h`（img2col2d、verify_img2col2d_contract 及其注释示例）。
  - 未执行测试（本次为注释示例与签名一致性复审）。
- 结论：通过。
  - 功能正确性：注释示例均为 value/out + 10 个 long long 参数，与固定签名一致。
  - 边界条件/异常路径：契约校验函数仍覆盖参数正负、rank/shape/stride 前置条件，未见与注释示例不一致导致误用的风险。
  - 潜在漏洞/绕过：未发现通过示例误导导致越权调用或签名漂移的路径。
  - 中文注释：img2col2d/verify_img2col2d_contract 注释为中文且与功能/示例一致，函数注释齐备。
  - 可维护性建议：无。
