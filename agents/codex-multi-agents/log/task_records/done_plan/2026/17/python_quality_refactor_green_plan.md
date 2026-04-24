# python_quality_refactor_green_plan.md

## 文档信息

- 创建者：`守护最好的爱莉希雅`
- 最后一次更改：`守护最好的爱莉希雅`
- 目标 `spec`：[`spec`](../../spec)
- 目标 `API`：[`kernel_gen`](../../kernel_gen) 公开 Python API、[`script/check_python_coverage.py`](../../script/check_python_coverage.py)
- 目标 `test`：[`test`](../../test)
- 目标 `验收入口`：[`test`](../../test)、[`script/check_python_coverage.py`](../../script/check_python_coverage.py)、终验 [`expectation`](../../expectation)
- 目标 `功能实现`：[`kernel_gen`](../../kernel_gen)、[`script`](../../script)

## 任务清单

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| S1：质量基线与门禁收口 | 无 | `wt-20260422-python-quality-s1-baseline` | `agents/codex-multi-agents/log/task_records/2026/17/20260422-python-quality-s1-baseline.md` |
| S2：基础模型切片质量收口 | S1 | `wt-20260422-python-quality-s2-core` | `agents/codex-multi-agents/log/task_records/2026/17/20260422-python-quality-s2-core.md` |
| S3：DSL / codegen / tools 切片质量收口 | S1 | `wt-20260422-python-quality-s3-dsl-tools` | `agents/codex-multi-agents/log/task_records/2026/17/20260422-python-quality-s3-dsl-tools.md` |
| S4：pass / pipeline 切片质量收口 | S1 | `wt-20260422-python-quality-s4-pass` | `agents/codex-multi-agents/log/task_records/2026/17/20260422-python-quality-s4-pass.md` |
| S5：execute / target / include 边界质量收口 | S1 | `wt-20260422-python-quality-s5-exec-target` | `agents/codex-multi-agents/log/task_records/2026/17/20260422-python-quality-s5-exec-target.md` |
| S6：测试去冗余与覆盖率基线交接 | S2、S3、S4、S5 | `wt-20260422-python-quality-s6-tests-coverage` | `agents/codex-multi-agents/log/task_records/2026/17/20260422-python-quality-s6-tests-coverage.md` |
| S6A：emit core.py 覆盖补齐 | S6 | `wt-20260423-python-quality-s6-core-emit` | `agents/codex-multi-agents/log/task_records/2026/17/20260423-python-quality-s6-core-emit.md` |
| S6B：parser.py + tile.py 基线交接 | S6 | `wt-20260423-python-quality-s6-parser-tile` | `agents/codex-multi-agents/log/task_records/2026/17/20260423-python-quality-s6-parser-tile.md` |
| S6B1：parser.py 解析覆盖补齐 | S6B | `wt-20260423-python-quality-s6-parser` | `agents/codex-multi-agents/log/task_records/2026/17/20260423-python-quality-s6-parser.md` |
| S6B2：tile.py 下沉覆盖补齐 | S6B | `wt-20260423-python-quality-s6-tile` | `agents/codex-multi-agents/log/task_records/2026/17/20260423-python-quality-s6-tile.md` |
| S6C：nn_lowering + analysis 覆盖补齐 | S6 | `wt-20260423-python-quality-s6-nn-analysis` | `agents/codex-multi-agents/log/task_records/2026/17/20260423-python-quality-s6-nn-analysis.md` |
| S7：终验修复与归档前复核 | S6A、S6B1、S6B2、S6C | `wt-20260422-python-quality-s7-final` | `agents/codex-multi-agents/log/task_records/2026/17/20260422-python-quality-s7-final.md` |

## 任务创建记录

- S1：`T-20260422-854cafe4`
- S2：`T-20260422-74f2d7ef`，依赖 `T-20260422-854cafe4`
- S3：`T-20260422-5331e29a`，依赖 `T-20260422-854cafe4`
- S4：`T-20260422-10958bce`，依赖 `T-20260422-854cafe4`
- S5：`T-20260422-c00469b9`，依赖 `T-20260422-854cafe4`
- S6：`T-20260422-10ac0fa3`，依赖 `T-20260422-74f2d7ef`、`T-20260422-5331e29a`、`T-20260422-10958bce`、`T-20260422-c00469b9`；当前按执行侧回报收束为基线与交接任务，不再继续扩大到全部核心模块。
- S6A：`T-20260423-936c8ee9`，依赖 `T-20260422-10ac0fa3`，指派 `jcc你莫辜负`，任务目标为 `kernel_gen/dsl/mlir_gen/emit/core.py` 的 emit / 解析覆盖补齐。
- S6B：`T-20260423-bc786e6c`，依赖 `T-20260422-10ac0fa3`，指派 `金铲铲大作战`，已暂停为 parser/tile 初始补测与拆分交接记录，不再继续扩大范围。
- S6B1：待创建，依赖 `T-20260423-bc786e6c`，建议任务目标为 `kernel_gen/dsl/ast/parser.py` 的解析主链、异常路径与调用绑定覆盖补齐。
- S6B2：待创建，依赖 `T-20260423-bc786e6c`，建议任务目标为 `kernel_gen/passes/lowering/tile.py` 的 plan / rewrite / analysis 清理边界覆盖补齐。
- S6C：`T-20260423-32986537`，依赖 `T-20260422-10ac0fa3`，当前待分发，任务目标为 `kernel_gen/passes/lowering/nn_lowering/*` 与 `kernel_gen/analysis/*` 的 lowering / 分析覆盖补齐。
- S7：`T-20260422-fa911126`，原依赖 `T-20260422-10ac0fa3`；需等 S6A、S6B1、S6B2、S6C 完成后再恢复推进，并由管理员更新依赖关系。

## 评审摘要

- 评审结论：`大闸蟹：通过`
- 评审人：`守护最好的爱莉希雅`、`大闸蟹`
- 结论摘要：`大闸蟹复评：通过。S1 已改为只生成 coverage/S1/coverage.json、验证 check_python_coverage.py 的 passing / line_fail / branch_fail fixture 并记录 baseline，不再前置最终 line>=95 / branch>=60；S6/S7 再收全量阈值。S1-S7 依赖顺序、spec/pytest 自足、实现去 expectation 依赖、IR 测试迁入 tool/pytest、pass 优先 xDSL 原生 rewrite、自检与审查要求均可执行。`

## 终验 / 复验 / 修复复核记录

- 结论人：`大闸蟹`
- 结论：`通过`
- 验证基线：`主目录 /home/lfr/kernelcode_generate 已先执行 git fetch --prune；当前主目录 HEAD 与 FETCH_HEAD 中的 origin/main 一致，基线 commit 为 7dc36033f4c877eb24450f3435e98e6c9a0f12d1。`
- 执行目录：`/home/lfr/kernelcode_generate`
- 合同验收摘要：`本轮按当前规则只执行与本计划相关的 expectation 合同验收：1）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.execute_engine.npu_demo，exit 0；2）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.tile，exit 0；3）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.tile.analysis，exit 0；4）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.lowing.nn_lowering，exit 0；5）PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.mlir_gen.dialect.nn.softmax，exit 0。`
- 最小阻断项或通过摘要：`按用户与管理员最新口径，related_expectation_modules.txt 不再作为本次归档阻断；本次已将正文中的相关 expectation 入口直接收口为固定列表。最新主线现场中，这 5 条相关 expectation 均通过，当前未再发现新的最小阻断项。`
- 是否已创建修复任务：`否`
- 修复任务创建人：`不适用`
- 另一位架构师补充重点：`守护最好的爱莉希雅 已给出通过结论；本次大闸蟹复验与其一致。`

- 结论人：`守护最好的爱莉希雅`
- 结论：`通过`
- 验证基线：`main@7dc36033f4c877eb24450f3435e98e6c9a0f12d1`（`HEAD == origin/main`）
- 执行目录：`/home/lfr/kernelcode_generate`
- 合同验收摘要：`本轮先在主目录执行 git fetch --prune；当前主目录只有未跟踪 worktree 目录与临时备份文件，不影响首轮验收，因此直接使用主目录执行相关 expectation。实际复跑 5 个与本计划最相关的入口：expectation.execute_engine.npu_demo、expectation.pass.tile、expectation.pass.tile.analysis、expectation.pass.lowing.nn_lowering、expectation.dsl.mlir_gen.dialect.nn.softmax，以上 5 项当前均 exit 0。`
- 最小阻断项或通过摘要：`按用户最新确认，这份计划直接收口归档。相关 expectation 入口已在最新主线现场复跑通过；related_expectation_modules.txt 相关正文整理项不再作为本次归档阻断。`
- 是否已创建修复任务：`否`
- 修复任务创建人：`不适用`
- 另一位架构师补充重点：`按用户要求直接收口归档。`

## S6 执行侧回报与后续拆分口径

- 回报来源：`T-20260422-10ac0fa3` / `wt-20260422-python-quality-s6-tests-coverage`
- 当前结论：同意按执行侧建议调整后续口径；当前 S6 只保留已完成的 pytest 修复、coverage baseline、缺口归因和交接记录，不再继续扩大到全部核心模块。
- 当前数据：全量 `pytest -q test` 已通过；`kernel_gen` coverage 仍约为 line `86.34%`、branch `74.12%`；核心模块 scope 约为 line `85.56%`、branch `69.02%`。
- 拆分理由：剩余缺口横跨 `emit/core.py`、`parser.py`、`tile.py`、`nn_lowering/*`、`analysis/*`，继续放在单个 S6 内会导致任务过大、审查困难，也不利于执行人按 diff 做真实自检。
- 新口径：S6A 与 S6C 保持不变；S6B 已暂停为交接记录，并继续拆成 S6B1 / S6B2 两个 build 切片；S6B1 与 S6B2 均依赖 S6B，可并行推进；S7 必须等待 S6A、S6B1、S6B2、S6C 完成后再做最终汇总。
- 管理员推进状态：`T-20260422-10ac0fa3` 已暂停扩范围；S6A=`T-20260423-936c8ee9`，S6B=`T-20260423-bc786e6c` 已暂停为 parser/tile 交接，S6C=`T-20260423-32986537`；S6B1 / S6B2 待创建；S7 继续等待后续切片完成后恢复。
- 不变目标：最终仍要求 `kernel_gen/**/*.py` coverage line `>=95%`、branch `>=60%`；`expectation` 仍只作为合同验收资产，不计入 diff 反推测试。

## 计划目标

- 检查并修正 `spec` 是否合理：公开 API、边界、异常、兼容性、非目标和示例必须清晰可执行。
- 去除普通 pytest 对 `expectation` 的质量依赖：pytest 直接断言行为、错误、边界和回归；`test/`、`kernel_gen/`、`script/` 中不得 import、调用或特判 expectation。
- 去除 `kernel_gen` 实现对 `expectation` 路径、旧文本或不可改 case 的特殊分支依赖。
- 去除冗余实现代码，抽取可复用逻辑；同时避免无意义的一两行小函数和过大的万能函数。
- 建立可维护性检查口径：API 一致、错误模型统一、依赖方向清晰、函数职责单一、注释示例准确、命名清楚、复杂度可控、无兼容债和临时分支。
- 合并同类型重复测试，保留代表性主路径、边界、异常、回归和兼容性测试。
- 最终 `kernel_gen/**/*.py` 覆盖率达到 line `>=95%`、branch `>=60%`。
- IR 文本测试随 tool 公开，不再以独立 asset 形态发布；pass、mlir_gen、codegen 等 IR 测试使用 tool 驱动的 case 化形式，归到 `spec/tools/*`、`kernel_gen/tools/*`、`test/tools/*` 或调用这些 tool 的 pytest。

## 输入摘要

- 目标：重新开始一份质量重构计划，避免旧计划阶段设计不清、执行人不知道如何做、终验后仍反复失败。
- 不做什么：不再把 expectation 当作普通测试替代；不做纯 spec-only 任务；不为提高覆盖率保留无意义测试或硬凑断言。
- 当前痛点：spec、test、实现之间存在重复和口径漂移；部分实现为了 expectation 旧文本特殊兼容；测试数量多但质量不均；coverage 目标没有稳定闭环；代码结构中仍可能存在职责混杂、错误模型分散、注释过时、兼容债残留和重复 helper。
- 完成后最想看到：spec 可读、pytest 自足、实现干净、重复测试减少、coverage 达标，终验运行与本轮改动有关的 expectation 合同验收证明公开合同没有被破坏。

## 当前基线

- 当前公开合同：`spec/` 覆盖 analysis、dialect、dsl、execute_engine、operation、pass、symbol_variable、tools 等主题，但本轮尚未逐项验证接口是否合理、是否重复、是否能直接指导实现。
- 当前公开 API：`kernel_gen/` 下已有 dialect、operation、dsl、passes、execute_engine、target、tools 等包；`script/check_python_coverage.py` 已提供 coverage JSON 阈值检查入口。
- 当前实现入口：核心实现集中在 [`kernel_gen`](../../kernel_gen)，coverage 工具在 [`script/check_python_coverage.py`](../../script/check_python_coverage.py)。
- 当前测试与验收入口：`test/` 下已有大量 pytest；`expectation/` 下有合同验收入口；终验规则要求架构师运行与本轮改动有关的 expectation。
- 当前缺口或失败点：
  - `kernel_gen` 中仍能扫描到 expectation 路径或 expectation 专用兼容逻辑，例如 [`kernel_gen/tools/ircheck.py`](../../kernel_gen/tools/ircheck.py)、[`kernel_gen/tools/mlir_gen_compare.py`](../../kernel_gen/tools/mlir_gen_compare.py)、[`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py)、[`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py) 等。
  - `test/tools/test_expectation_case_runner.py` 直接测试 `expectation.utils.case_runner`，与“test/kernel_gen/script 不得出现 expectation 相关代码”的新口径冲突，应从 `test/` 产品测试树移除或迁到 expectation 自身入口。
  - `test/pass/nn_lowering/element_binary_*`、`element_compare_*` 等同类型文件存在明显可参数化合并空间。
  - coverage 相关 spec 和脚本已存在，但最终全仓 `kernel_gen` line `95` / branch `60` 还需要以统一命令收口。

## 方案比较与选型

- 不采用方案：继续沿用旧计划，将 spec、test、implementation、expectation 混在一个大任务里推进。
- 不采用原因：执行人只知道“让计划过”，不知道每个阶段的最小质量闭环；容易继续依赖 expectation，导致 pytest 和实现本身质量不够。
- 不采用方案：只追 coverage 数字。
- 不采用原因：会鼓励无意义测试、重复断言和覆盖率游戏，不能解决 spec 不合理、实现冗余、维护性差的问题。
- 采用方案：按质量切片推进，每个切片同时检查 spec、pytest、实现和 coverage；expectation 只保留为终验合同资产。
- 最小公开接口：`pytest` 直接验证产品行为；`coverage run --branch --source=kernel_gen -m pytest -q test` 生成覆盖率；`script/check_python_coverage.py` 检查 line / branch 阈值。

## 代码质量检查矩阵

- API 质量：公开入口命名、参数顺序、返回值、默认值、异常类型和错误文本必须一致；同类功能不得有多套近似入口。
- 边界质量：每个公开 API 都要明确非法输入、空输入、动态符号、维度/类型不匹配、环境依赖缺失和 no-op 行为。
- 错误模型：同类错误使用同类异常和稳定错误前缀；不得散落裸 `ValueError` / `RuntimeError`，除非 spec 已说明。
- 模块边界：高层模块不得反向依赖低层测试工具或合同目录；公共 helper 放在稳定模块，私有 helper 不泄漏成外部 API。
- 依赖方向：`kernel_gen` 不依赖 `expectation`，产品 pytest 不依赖 `expectation`，tool pytest 可以复用 `kernel_gen.tools` 公开 helper。
- 代码复用：重复的 shape/stride/type 校验、IR 文本运行、错误构造、case 驱动逻辑应收成共享 helper；但不得抽成没有语义的一两行 wrapper。
- pass 实现风格：pass 优先使用 xDSL / MLIR 风格基础设施，如 `ModulePass`、`RewritePattern`、`op_type_rewrite_pattern`、`PatternRewriteWalker` 和 xDSL 原生 IR 遍历 / rewrite API；不得为了统一外观再包一层厚 pass framework 或自建重复 rewrite 调度器。
- 函数粒度：过大函数要按职责拆分；一两行函数只有在命名表达稳定概念、复用价值明确或隔离外部依赖时才允许。
- 可读性：命名必须表达业务语义；复杂条件要拆成可读的局部变量或 helper；避免魔法常量、隐式全局状态和跨函数副作用。
- 注释与示例：新增或修改函数的中文注释、功能说明、使用示例、关联 `spec/test/功能实现` 链接必须与实现同步；过时注释视为缺陷。
- 兼容债：临时兼容分支、旧路径 alias、旧文本 normalize、历史 case 特判必须有去留结论；保留项必须有 spec 合同和测试。
- 测试质量：测试断言必须能在实现坏掉时失败；删除重复测试前必须说明保留的等价覆盖；不得为了 coverage 写无意义测试。
- 可演进性：新 helper、case runner、工具入口要能被下一类同族功能复用；不能只服务当前单个 case。

## IR 测试发布口径

- IR 文本测试不再作为独立 asset 清单或 expectation asset 发布。
- IR 测试随 tool 公开：tool 合同写在 [`spec/tools`](../../spec/tools)，实现入口在 [`kernel_gen/tools`](../../kernel_gen/tools)，pytest 入口在 [`test/tools`](../../test/tools)。
- [`expectation/tools`](../../expectation/tools) 中已有的 `ircheck`、`mlir_gen_compare`、`dsl_run` 等工具用作迁移参考和合同对齐来源；可复用能力应提升到 `kernel_gen.tools` 或 `test/tools`，不得让 `kernel_gen`、产品 pytest 或脚本运行时直接依赖 `expectation.tools`。
- pass、mlir_gen、codegen 中需要验证 IR 文本时，应通过 pytest 调用对应 tool 或共享 helper；测试形式可以像 `expectation/tools` 一样按 case 组织，但 case 归属 tool / pytest，不另建 asset 形态。
- 计划书模板中的“验收资产”在本计划内按“验收入口 / 验收命令”理解；不得据此新建 IR asset 目录或把 IR case 搬到 expectation。

## 公开 API 设计

- 公开入口：`kernel_gen` Python API、`script/check_python_coverage.py`
- 参数顺序：coverage 检查保持 `--coverage-json`、`--line-min`、`--branch-min`、可选 `--include-module`
- 参数类型：`Path`、`float`、`list[str]`
- 返回值：coverage 检查成功返回 exit `0`；失败返回非零并打印明确原因

```bash
mkdir -p coverage/final
coverage erase
coverage run --branch --source=kernel_gen -m pytest -q test
coverage json -o coverage/final/coverage.json
python3 script/check_python_coverage.py \
  --coverage-json coverage/final/coverage.json \
  --line-min 95 \
  --branch-min 60
```

产品测试和实现代码不得这样写：

```python
from expectation.some_case import run

def test_product_behavior():
    run()
```

产品测试应直接断言公开行为：

```python
def test_pass_rejects_invalid_input():
    with pytest.raises(ValueError, match="target must"):
        run_pass_on(invalid_ir)
```

实现不得这样写：

```python
if "expectation/dsl/emit_c" in source_path:
    return old_expected_text(text)
```

实现应提供一般语义规则，由 `pytest` 和 `expectation` 分别验证同一公开输出。

## 完成态定义

- `spec` 与实现、pytest 的公开行为一致；每个被改 API 都有清晰参数、返回、异常、边界、兼容性和示例。
- 普通产品 pytest 不再以运行 expectation 作为质量替代；`test/`、`kernel_gen/`、`script/` 中不允许出现 expectation 相关 import、调用、路径特判或兼容代码。
- `kernel_gen` 实现不再针对 `expectation/` 路径、旧 case 名或不可改文本做特殊分支。
- 同类型重复测试被合并为参数化测试或共享 fixture，删除的测试不会减少主路径、边界、异常和回归覆盖。
- 冗余实现被抽取或删除；复用逻辑有清晰职责，不引入过大 helper 或无意义小函数。
- 代码质量检查矩阵中的 API、边界、错误、模块依赖、复用、函数粒度、注释示例、兼容债和测试质量均有任务记录证据。
- `kernel_gen/**/*.py` 覆盖率 line `>=95%`、branch `>=60%`，薄包装 omit 清单最小且有理由。
- 终验全量 `pytest`、coverage gate、与本轮改动有关的 `expectation` 合同验收都通过。

## 验收设计

- 验收入口：[`test`](../../test)、[`script/check_python_coverage.py`](../../script/check_python_coverage.py)、终验 [`expectation`](../../expectation)
- 输入样例：全量仓库 Python 测试和合同资产
- 锁定输出：
  - `pytest -q test` 通过。
  - coverage gate 输出 `coverage ok`，line `>=95.00%`，branch `>=60.00%`。
  - 与本轮改动有关的 `expectation` 模块逐项通过，作为终验合同检查。
  - `rg -n "from expectation|import expectation|expectation\\." kernel_gen test script` 不命中；没有任何例外白名单。
  - `rg -n "expectation/" kernel_gen` 不命中行为分支；文档注释如保留，必须不是运行时条件或旧文本兼容依据。
  - IR 文本检查通过 `test/tools` 或调用 `kernel_gen.tools` 的 pytest 承接，不以独立 asset 形态承接。
  - 每个阶段任务日志都包含 `代码质量检查矩阵` 的自检摘要；审查记录必须逐项确认，不接受只写 coverage 或 pytest 通过。
- 必过命令：

```bash
pytest -q test
mkdir -p coverage/final
coverage erase
coverage run --branch --source=kernel_gen -m pytest -q test
coverage json -o coverage/final/coverage.json
python3 script/check_python_coverage.py --coverage-json coverage/final/coverage.json --line-min 95 --branch-min 60
python3 -m expectation.execute_engine.npu_demo
python3 -m expectation.pass.tile
python3 -m expectation.pass.tile.analysis
python3 -m expectation.pass.lowing.nn_lowering
python3 -m expectation.dsl.mlir_gen.dialect.nn.softmax
rg -n "from expectation|import expectation|expectation\\." kernel_gen test script
rg -n "expectation/" kernel_gen
```

- Diff 反推验证：执行与审查阶段必须按实际改动文件补跑对应测试；计划命令只是最低集合；`expectation` 合同验收单列，不算 diff 反推测试。
- 终验 expectation：架构师终验 / 复验 / 终验修复复核时必须在最新同步现场运行与本轮改动有关的 expectation 合同验收；只有用户明确要求时才运行全量 expectation。
- 审查门禁：每个 review 任务必须在审查记录中单列 `代码质量矩阵审查`，逐项覆盖 API、边界、错误模型、模块边界、依赖方向、复用、函数粒度、可读性、注释示例、兼容债、测试质量和可演进性；缺任一项且无有效说明时不得通过。
- 审查门禁：若只写“pytest 通过 / coverage 达标 / expectation 通过”，未评估代码规范质量和可维护性，结论必须为 `需修改`。

## 阶段拆分

### S1：质量基线与门禁收口

#### 上下文摘要

- 本阶段先把质量目标变成可执行门禁，避免后续阶段只靠主观判断“代码更好了”。

#### 阶段目标

- 建立 spec/test/实现/expectation 依赖基线、重复测试清单、coverage baseline 和最终门禁命令。

#### 非目标

- 不批量重构业务实现。
- 不删除测试，只标记重复测试候选和质量风险。

#### 目标 spec / API

- [`spec/script/python_coverage_check.md`](../../spec/script/python_coverage_check.md)
- [`spec/script/python_coverage_omit.md`](../../spec/script/python_coverage_omit.md)
- 公开 API：`script/check_python_coverage.py`

#### 禁止修改面 / 合同真源

- 禁止修改面：`expectation/` 不是本阶段修改目标。
- 合同真源：`spec/script/python_coverage_check.md`、`spec/script/python_coverage_omit.md`

#### 最小功能闭环

- coverage gate 能在当前仓库生成 `coverage/S1/coverage.json`，并能用测试 fixture 验证 `script/check_python_coverage.py` 对通过、line 失败、branch 失败三类输入的判断。
- S1 只记录当前 baseline，不要求全仓已经达到 line `>=95%`、branch `>=60%`；最终阈值只在 S6 / S7 强制。
- 任务记录写清四张清单：spec 风险、重复测试候选、实现对 expectation 的依赖候选、`expectation/tools` 可迁移能力清单。

#### 执行步骤

1. 读取本计划全局完成态、验收设计、coverage spec、pytest 配置和现有 coverage 工具。
2. 运行当前 baseline：`pytest -q test`、coverage JSON，并记录当前 line / branch 数值。
3. 用 `rg` 生成 expectation 依赖清单、重复测试候选清单、coverage omit 候选清单。
4. 修正 coverage 工具或测试中阻碍基线生成的最小问题。
5. 盘点 `expectation/tools/{ircheck,mlir_gen_compare,dsl_run}` 中可复用的 case runner、文本比较、错误汇总和命令行行为，标出应迁入或对齐到 `kernel_gen.tools` / `test/tools` 的能力。
6. 在任务日志写明后续 S2-S6 每个切片必须处理的最小清单。
7. 建立每个切片的代码质量风险清单：API 不一致、错误模型分散、重复 helper、过大函数、无意义小函数、过时注释、兼容债和依赖反向。

#### 预期示例代码

```bash
coverage run --branch --source=kernel_gen -m pytest -q test
coverage json -o coverage/S1/coverage.json
pytest -q test/script/test_python_coverage_check.py test/script/test_python_coverage_omit.py
```

#### 预期输出

```text
coverage baseline recorded: coverage/S1/coverage.json
coverage checker fixtures passed: passing / line_fail / branch_fail
```

#### 目标验收入口

- `pytest -q test/script/test_python_coverage_check.py test/script/test_python_coverage_omit.py`
- `coverage/S1/coverage.json` 不进入 git 跟踪，只作为任务记录证据。
- IR 测试清单只记录 tool pytest 入口，不记录独立 asset。

#### 验收必过项目

- `pytest -q test/script/test_python_coverage_check.py test/script/test_python_coverage_omit.py`
- `rg -n "from expectation|import expectation|expectation\\." kernel_gen test script`
- `rg -n "expectation/" kernel_gen`
- `补充要求：执行人与审查人按实际 diff 反推测试，并在任务日志写明 Diff 反推自测 / Diff 反推审查；expectation 合同验收单列`

#### 记录要求

- `执行前阅读记录：TODO 任务行、计划书 S1、全局完成态/验收设计、coverage spec、pytest 配置、前序记录`
- `最小功能闭环：写清 coverage baseline、依赖清单、重复测试候选、expectation/tools 可迁移能力和未覆盖原因`
- `自检：禁止只写“已自检/无问题”；必须写实际检查结论，并引用代码质量检查矩阵中的风险清单`

#### 任务新建建议

- `任务类型：build`
- `任务目标：建立 Python 质量重构 baseline、coverage 门禁和去 expectation 依赖清单`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260422-python-quality-s1-baseline.md`

### S2：基础模型切片质量收口

#### 上下文摘要

- 基础模型包括 common、symbol_variable、dialect、operation，是后续 DSL、pass 和 execute_engine 的底层语义来源。

#### 阶段目标

- 对基础模型切片同步收口 spec 合理性、直接 pytest、实现复用和局部 coverage。

#### 非目标

- 不处理 DSL/codegen、passes、execute_engine 的专项逻辑。
- 不新增 expectation 合同，除非发现公开合同完全缺失并由架构师另行确认。

#### 目标 spec / API

- [`spec/common`](../../spec/common)
- [`spec/symbol_variable`](../../spec/symbol_variable)
- [`spec/dialect`](../../spec/dialect)
- [`spec/operation`](../../spec/operation)
- 公开 API：`kernel_gen.common`、`kernel_gen.symbol_variable`、`kernel_gen.dialect`、`kernel_gen.operation`

#### 禁止修改面 / 合同真源

- 禁止修改面：不得修改 `expectation/` 来让本阶段通过。
- 合同真源：`spec > pytest > 当前实现`；expectation 仅由架构师终验运行，不进入实现或 pytest 代码。

#### 最小功能闭环

- 每个被改 API 的 spec、pytest、实现必须一起闭环。
- 重复测试合并后仍保留主路径、边界、异常、回归和动态/静态代表例。
- 同类基础模型的类型校验、错误构造、shape/stride 处理和 symbol 处理必须统一，不能各文件各写一套。

#### 执行步骤

1. 按模块检查 spec 是否能解释当前公开 API、异常和边界。
2. 将同类 operation/dialect/symbol tests 改为参数化或共享 fixture，删除纯重复 case。
3. 抽取基础模型中重复的类型校验、shape/stride 校验、错误文本构造和转换逻辑。
4. 补齐局部 coverage 缺口，优先补边界和异常测试，不写无意义覆盖率测试。
5. 检查公开类型和 helper 的命名、注释、示例、异常类型、返回值是否一致；发现兼容债必须给去留结论。

#### 预期示例代码

```python
@pytest.mark.parametrize("op_name, lhs, rhs, expected", CASES)
def test_elementwise_contract(op_name, lhs, rhs, expected):
    assert run_elementwise(op_name, lhs, rhs) == expected
```

#### 预期输出

```text
基础模型 pytest 直接断言公开行为，无需 import expectation。
```

#### 目标验收入口

- `pytest -q test/common test/symbol_variable test/dialect test/operation`
- `coverage` scoped to `kernel_gen.common`、`kernel_gen.symbol_variable`、`kernel_gen.dialect`、`kernel_gen.operation`

#### 验收必过项目

- `pytest -q test/common test/symbol_variable test/dialect test/operation`
- `coverage run --branch --source=kernel_gen.common,kernel_gen.symbol_variable,kernel_gen.dialect,kernel_gen.operation -m pytest -q test/common test/symbol_variable test/dialect test/operation`
- `coverage json -o coverage/S2/coverage.json`
- `python3 script/check_python_coverage.py --coverage-json coverage/S2/coverage.json --include-module kernel_gen.common --include-module kernel_gen.symbol_variable --include-module kernel_gen.dialect --include-module kernel_gen.operation --line-min 95 --branch-min 60`

#### 记录要求

- `执行前阅读记录：TODO 任务行、计划书 S2、全局完成态/验收设计、相关 spec/test/实现、S1 baseline`
- `最小功能闭环：列出每个被改 API 的 spec、pytest、实现和 coverage 证据`
- `自检：重点写 API 合理性、重复测试删除理由、实现复用、函数粒度、错误模型、注释示例、边界和异常是否覆盖`

#### 任务新建建议

- `任务类型：build`
- `任务目标：收口 common / symbol_variable / dialect / operation 的 spec、pytest、实现复用和 scoped coverage`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260422-python-quality-s2-core.md`

### S3：DSL / codegen / tools 切片质量收口

#### 上下文摘要

- DSL、MLIR 生成、C++ 发射、gen_kernel 和 tools 当前最容易混入文本兼容和 expectation 专用逻辑。

#### 阶段目标

- 去除 DSL/codegen/tools 对 expectation 路径或旧文本的运行时特殊分支，用一般语义和直接 pytest 锁定输出。

#### 非目标

- 不重写公开 DSL 语言设计。
- 不为旧 expectation 文本保留实现侧特殊兼容；若合同冲突，由 spec/expectation 合同另行裁定。

#### 目标 spec / API

- [`spec/dsl`](../../spec/dsl)
- [`spec/tools`](../../spec/tools)
- 公开 API：`kernel_gen.dsl`、`kernel_gen.tools`

#### 禁止修改面 / 合同真源

- 禁止修改面：不得通过修改 `expectation/` 或新增 expectation-specific branch 让旧文本通过。
- 合同真源：`spec > pytest > 当前实现`；expectation 仅由架构师终验运行，不进入实现或 pytest 代码。

#### 最小功能闭环

- `kernel_gen/dsl` 与 `kernel_gen/tools` 不再根据 `source_path` 中的 `expectation/` 做输出修正。
- pytest 直接断言 emit/mlir/gen_kernel/tools 输出。
- 文本规范化、case 运行、错误汇总和 compare 逻辑优先参考 `expectation/tools` 的成熟行为，并归到 `kernel_gen.tools` 的公开 helper 或 `test/tools` 的测试 helper，避免各 DSL/pass 测试复制。

#### 执行步骤

1. 读取 S1 中 DSL/tools 的 expectation 依赖清单。
2. 读取 S1 中 `expectation/tools` 可迁移能力清单，将稳定的 `ircheck`、`mlir_gen_compare`、`dsl_run` 行为提升到 `kernel_gen.tools` / `test/tools`，保留行为语义但去掉 expectation 路径依赖。
3. 将 `ircheck`、`mlir_gen_compare`、`emit_c`、`gen_kernel` 中的 expectation 专用修正替换为一般规则或删除。
4. 对文本输出新增直接 pytest，断言真实公开输出，而不是断言为某个 expectation 临时规整结果。
5. 合并同类 DSL/codegen 文本测试，保留静态/动态/错误/兼容代表例。
6. 检查文本生成函数是否过大、兼容分支是否无 spec、错误路径是否散落；需要拆分时按 emit/format/validate 三类职责拆。

#### 预期示例代码

```python
def test_ircheck_does_not_normalize_for_expectation_path():
    assert normalize_ir(actual, source_path="any/path.py") == normalize_ir(actual)
```

#### 预期输出

```text
rg -n "expectation/" kernel_gen/dsl kernel_gen/tools
# 不命中运行时行为分支
```

#### 目标验收入口

- `pytest -q test/dsl test/tools`
- `rg -n "expectation/" kernel_gen/dsl kernel_gen/tools`
- IR 文本测试随 [`test/tools`](../../test/tools) 和调用 tool 的 DSL pytest 发布，不新增 asset。

#### 验收必过项目

- `pytest -q test/dsl test/tools`
- `coverage run --branch --source=kernel_gen.dsl,kernel_gen.tools -m pytest -q test/dsl test/tools`
- `coverage json -o coverage/S3/coverage.json`
- `python3 script/check_python_coverage.py --coverage-json coverage/S3/coverage.json --include-module kernel_gen.dsl --include-module kernel_gen.tools --line-min 95 --branch-min 60`
- `rg -n "expectation/" kernel_gen/dsl kernel_gen/tools`

#### 记录要求

- `执行前阅读记录：TODO 任务行、计划书 S3、全局完成态/验收设计、S1 baseline、相关 DSL/tools spec/test/实现`
- `最小功能闭环：写清每个移除的 expectation 特殊分支、替代的一般规则和对应 pytest`
- `自检：重点写文本输出是否一般化、测试断言是否有效、是否还有旧路径兼容残留、tool helper 是否可复用、文本生成函数职责是否清晰`

#### 任务新建建议

- `任务类型：build`
- `任务目标：收口 DSL/codegen/tools 的直接 pytest、去 expectation 特殊分支和 scoped coverage`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260422-python-quality-s3-dsl-tools.md`

### S4：pass / pipeline 切片质量收口

#### 上下文摘要

- pass/pipeline 测试容易出现同类型 IR case 重复，也容易把 expectation 当作 pass 正确性的主要证据。

#### 阶段目标

- pass/pipeline 的 spec、pytest、实现复用和 coverage 自足；重复 IR 测试合并，expectation 仅终验。
- pass/pipeline 的 IR 文本测试通过工具化 pytest 承接，不以 asset 形态承接。

#### 非目标

- 不改变 pass 公开名和 pipeline 公开入口，除非 spec 明确存在冗余或不合理入口并经用户确认。

#### 目标 spec / API

- [`spec/pass`](../../spec/pass)
- 公开 API：`kernel_gen.passes`

#### 禁止修改面 / 合同真源

- 禁止修改面：不得修改 `expectation/pass` 来掩盖 pass 实现问题。
- 合同真源：`spec > pytest > 当前实现`；expectation 仅由架构师终验运行，不进入实现或 pytest 代码。

#### 最小功能闭环

- 每个 pass 至少有直接 pytest 覆盖主路径、无效输入、边界行为和一个回归 case。
- 同类 IR case 用 helper 或参数化合并，不保留只改 SSA 名称或无实质差异的重复测试。
- IR 文本断言优先复用从 `expectation/tools/ircheck` 对齐而来的 `kernel_gen.tools.ircheck` 或同类 tool helper；不得新建独立 IR asset。
- pass 改写逻辑优先落到 xDSL 原生 `RewritePattern` / `op_type_rewrite_pattern` / `PatternRewriteWalker` 体系；只有候选收集、错误构造、公共校验这类稳定职责才抽 helper，禁止把 xDSL rewrite 再包成难以审查的项目私有框架。
- pass pattern、候选收集、rewrite、验证和错误构造职责应分开；不得把所有逻辑堆进一个巨大 `apply` / `run` 函数。

#### 执行步骤

1. 按 pass 检查 spec 是否描述入口、前置条件、输出 IR、错误和 no-op 行为。
2. 合并重复 IR 测试，保留机械可判的差异维度；IR case 以 tool 驱动的 pytest 形式组织。
3. 优先用 `expectation/tools/ircheck` 已验证过的 CHECK / CHECK-NEXT / 变量捕获语义作为工具行为参考，并在 `kernel_gen.tools.ircheck` / `test/tools` 中承接。
4. 抽取 pass 中重复遍历、匹配、错误构造和 IR 文本处理逻辑。
5. 检查 pass 是否能直接用 xDSL 的 `ModulePass`、pattern rewrite 和 IR 遍历设施表达；能用原生设施表达的逻辑不得新增私有调度包装。
6. 补齐 pass/pipeline scoped coverage。
7. 检查每个 pass 的 no-op、非法输入、多函数、多结果、动态符号、旧路径 alias、registry / pipeline 注册和错误模型。

#### 预期示例代码

```python
@pytest.mark.parametrize("case", PASS_CASES, ids=lambda case: case.name)
def test_pass_contract(case):
    assert run_pass(case.input_ir) == case.expected_ir
```

#### 预期输出

```text
pass pytest 直接验证 IR 输出和错误，不通过 expectation 包装间接验证。
```

#### 目标验收入口

- `pytest -q test/pass`
- `coverage` scoped to `kernel_gen.passes`
- IR case 随 pass pytest 或 tool pytest 发布，不使用 asset 形式。

#### 验收必过项目

- `pytest -q test/pass`
- `coverage run --branch --source=kernel_gen.passes -m pytest -q test/pass`
- `coverage json -o coverage/S4/coverage.json`
- `python3 script/check_python_coverage.py --coverage-json coverage/S4/coverage.json --include-module kernel_gen.passes --line-min 95 --branch-min 60`
- `rg -n "from expectation|import expectation|expectation\\." test/pass kernel_gen/passes script`
- `S4 补充口径：若 pass / pipeline 结构、pytest 自足、IR tool 化、重复测试合并与 branch 覆盖率已收口，但 line 覆盖率距离 95% 仍需跨 pass family 大范围补齐，则 S4 不继续扩大任务范围；执行人必须把当前 line / branch 数值、未覆盖文件摘要和“未由本阶段 diff 引入回退”的判断写入记录，剩余 line 缺口转入 S6 全局覆盖率收口。`

#### 记录要求

- `执行前阅读记录：TODO 任务行、计划书 S4、全局完成态/验收设计、S1 baseline、相关 pass spec/test/实现`
- `最小功能闭环：写清每个 pass 的直接 pytest、重复测试删除理由、实现复用和 coverage 证据`
- `自检：重点写 xDSL 原生 rewrite 使用情况、是否存在过厚私有包装、no-op、非法输入、多函数、多结果、动态符号、旧路径残留、注册一致性、pass 函数粒度和错误模型是否覆盖`
- `覆盖率缺口记录：若 S4 按补充口径转入后续切片，必须写清 S6 需要继续处理 kernel_gen.passes line 覆盖率，不能把该缺口写成已解决。`

#### 任务新建建议

- `任务类型：build`
- `任务目标：收口 pass/pipeline 的直接 pytest、测试去冗余、实现复用和 scoped coverage`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260422-python-quality-s4-pass.md`

### S5：execute / target / include 边界质量收口

#### 上下文摘要

- execute_engine、target 和 include 相关链路涉及真实编译、目标文件和 C++ 头文件，不能只靠 Python coverage 数字判断质量。

#### 阶段目标

- 收口 execute/target/include 的 spec、pytest、错误处理、环境依赖和非 Python 覆盖率例外。

#### 非目标

- 不把 C++ 头文件纳入 `kernel_gen/**/*.py` coverage 阈值。
- 不用 expectation 端到端 case 替代 execute_engine 的 Python pytest。

#### 目标 spec / API

- [`spec/execute_engine`](../../spec/execute_engine)
- [`spec/target`](../../spec/target)
- [`spec/include`](../../spec/include)
- 公开 API：`kernel_gen.execute_engine`、`kernel_gen.target`

#### 禁止修改面 / 合同真源

- 禁止修改面：不得通过跳过真实失败来伪造通过；环境依赖缺失必须写成 pytest skip 或明确错误。
- 合同真源：`spec > pytest > 当前实现`；expectation 仅由架构师终验运行，不进入 execute/target/include pytest 或实现代码。

#### 最小功能闭环

- execute/target 的 Python 行为有直接 pytest。
- include/C++ 路径有可运行编译或文本验证，且说明为什么不计入 Python coverage。
- 环境依赖、target 注册、资源生命周期、编译缓存、错误恢复和临时文件清理必须有明确行为。

#### 执行步骤

1. 检查 execute/target/include spec 是否写清环境依赖、错误、target 注册和 C++ 头文件边界。
2. 将过去只靠端到端 expectation 看到的 Python 行为补成直接 pytest；新增 pytest 不得 import 或调用 expectation。
3. 清理重复的 target/include 测试，保留 API、错误、编译、命名空间和资源生命周期代表例。
4. 补齐 execute/target scoped coverage，C++ 头文件按 spec 记录为非 Python coverage 例外。
5. 检查真实编译路径是否有清晰错误模型和资源清理；环境依赖缺失只能显式 skip 或明确失败，不能吞错。

#### 预期示例代码

```python
def test_execute_engine_reports_missing_target():
    with pytest.raises(TargetError, match="unknown target"):
        compile_for_target("missing-target", source)
```

#### 预期输出

```text
execute_engine pytest 直接覆盖错误和成功路径；expectation 只做端到端合同补充。
```

#### 目标验收入口

- `pytest -q test/execute_engine test/target test/include`
- `coverage` scoped to `kernel_gen.execute_engine`、`kernel_gen.target`

#### 验收必过项目

- `pytest -q test/execute_engine test/target test/include`
- `coverage run --branch --source=kernel_gen.execute_engine,kernel_gen.target -m pytest -q test/execute_engine test/target`
- `coverage json -o coverage/S5/coverage.json`
- `python3 script/check_python_coverage.py --coverage-json coverage/S5/coverage.json --include-module kernel_gen.execute_engine --include-module kernel_gen.target --line-min 95 --branch-min 60`

#### 记录要求

- `执行前阅读记录：TODO 任务行、计划书 S5、全局完成态/验收设计、S1 baseline、相关 execute/target/include spec/test/实现`
- `最小功能闭环：写清 Python 直接 pytest、C++ 例外验证、环境依赖和 coverage 证据`
- `自检：重点写错误处理、资源生命周期、target 兼容性、环境依赖、临时文件清理、编译失败恢复和测试断言有效性`

#### 任务新建建议

- `任务类型：build`
- `任务目标：收口 execute/target/include 的直接 pytest、环境边界和 scoped coverage`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260422-python-quality-s5-exec-target.md`

### S6：测试去冗余与覆盖率基线交接

#### 上下文摘要

- S2-S5 分切片收口后，需要全局检查是否还有重复测试、实现冗余、coverage 例外过宽和 expectation 依赖残留。
- 执行侧已继续扩展到多个核心模块，但剩余覆盖缺口横跨多个逻辑族；本阶段改为基线与交接，不再无限扩大范围。

#### 阶段目标

- 完成当前可安全收口的测试修复、重复测试整理、coverage baseline 生成和缺口归因。
- 明确后续 S6A / S6B1 / S6B2 / S6C 覆盖补齐切片，并把 S7 调整为等待这些切片完成后再推进。

#### 非目标

- 不为覆盖率删除有价值的边界测试。
- 不通过扩大 omit 清单、`pragma: no cover` 或跳过测试来达标。
- 不在单个 S6 任务内继续扩到所有剩余核心模块。

#### 目标 spec / API

- [`spec/script/python_coverage_check.md`](../../spec/script/python_coverage_check.md)
- [`spec/script/python_coverage_omit.md`](../../spec/script/python_coverage_omit.md)
- 公开 API：全量 `kernel_gen/**/*.py` coverage 阈值检查

#### 禁止修改面 / 合同真源

- 禁止修改面：不得修改 `expectation/`；不得将有逻辑的 `kernel_gen` 文件加入 omit。
- 合同真源：`pytest coverage 阈值检查 > spec/script/python_coverage_omit.md > 当前实现`

#### 最小功能闭环

- 重复测试合并有清单、有删除理由、有保留覆盖说明。
- 全量 pytest 主链路通过。
- `coverage/S6/coverage.json` 已生成，且覆盖缺口按模块归因。
- 未达最终 line `95` / branch `60` 的原因必须写清，并拆给 S6A / S6B1 / S6B2 / S6C，不得隐藏成“后续再看”。

#### 执行步骤

1. 对全量 `test/` 做重复测试审计：同输入同断言、只改名字、同 IR 等价文本、同错误路径重复。
2. 将同类型测试合并为参数化 case 或 shared helper。
3. 删除冗余测试并在任务记录中列出删除理由和保留的等价覆盖。
4. 复核 `pragma: no cover` 和 omit 清单，禁止扩大到有业务逻辑文件。
5. 跑全量 pytest 和 coverage 阈值检查，记录当前结果。
6. 复核 `kernel_gen` 中过大函数、无意义小函数、重复 helper、过时注释、散落错误文本、反向依赖和兼容债残留。
7. 复核从 `expectation/tools` 迁移或对齐出的工具能力是否已由 `test/tools` 覆盖，且 `kernel_gen` / `test` / `script` 中没有直接 import `expectation.tools`。
8. 若最终 coverage 仍未达标，停止继续扩大 S6，将缺口拆到 S6A / S6B1 / S6B2 / S6C。

#### 预期示例代码

```python
CASES = [
    Case("static", input_ir=..., expected_ir=...),
    Case("dynamic", input_ir=..., expected_ir=...),
    Case("invalid", input_ir=..., error="..."),
]
```

#### 预期输出

```text
pytest passed
coverage baseline recorded
remaining coverage slices listed
```

#### 目标验收入口

- `pytest -q test`
- `coverage/S6/coverage.json`
- `script/check_python_coverage.py`

#### 验收必过项目

- `pytest -q test`
- `coverage erase`
- `coverage run --branch --source=kernel_gen -m pytest -q test`
- `coverage json -o coverage/S6/coverage.json`
- `rg -n "from expectation|import expectation|expectation\\." kernel_gen test script`
- `rg -n "expectation/" kernel_gen`

#### 必须记录的未完成项

- `python3 script/check_python_coverage.py --coverage-json coverage/S6/coverage.json --line-min 95 --branch-min 60` 的实际结果。
- 若仍未通过，记录 line / branch 数值、主要文件族、已补测试、未补原因和 S6A / S6B1 / S6B2 / S6C 交接边界。

#### 记录要求

- `执行前阅读记录：TODO 任务行、计划书 S6、全局完成态/验收设计、S1-S5 记录`
- `最小功能闭环：写清删除/合并测试清单、保留覆盖、coverage 结果和残留风险`
- `自检：重点写覆盖率不是靠 skip/omit/pragma 凑出来，测试断言仍有效，重复测试已合并而非漏测，代码质量矩阵无未记录缺口`

#### 任务新建建议

- `任务类型：build`
- `任务目标：全局测试去冗余、生成 coverage baseline、归因剩余缺口并交接 S6A/S6B/S6C`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260422-python-quality-s6-tests-coverage.md`

### S6A：emit core.py 覆盖补齐

#### 上下文摘要

- S6 已证明 `kernel_gen/dsl/mlir_gen/emit/core.py` 是剩余覆盖缺口的主要来源之一；该文件负责 DSL 到 MLIR 的核心 emit / 解析路径，适合单独补齐。

#### 阶段目标

- 为 [`kernel_gen/dsl/mlir_gen/emit/core.py`](../../kernel_gen/dsl/mlir_gen/emit/core.py) 补齐可维护的 pytest 覆盖，覆盖主路径、错误路径、默认值规范化、类型/shape/space 映射和 helper 分支。

#### 非目标

- 不改公开 MLIR 语义，除非先同步 spec 与现有 pytest。
- 不把 `expectation` case 直接接入 pytest。
- 不顺手重构 parser、tile、nn_lowering 或 analysis。

#### 目标 spec / API

- [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
- [`kernel_gen/dsl/mlir_gen/emit/core.py`](../../kernel_gen/dsl/mlir_gen/emit/core.py)
- 相关 pytest：[`test/dsl`](../../test/dsl)

#### 最小功能闭环

- `core.py` 的新增测试直接断言公开行为或稳定错误，不依赖文本旧 case 特判。
- scoped coverage 对 `kernel_gen.dsl.mlir_gen.emit.core` 达到 line `95` / branch `60`。
- 任务记录包含 build 自检和 Diff 反推自测。

#### 验收必过项目

- `pytest -q test/dsl/test_emit_mlir.py test/dsl/mlir_gen/emit test/dsl/test_gen_kernel.py`
- `coverage erase`
- `coverage run --branch --source=kernel_gen -m pytest -q test/dsl/test_emit_mlir.py test/dsl/mlir_gen/emit test/dsl/test_gen_kernel.py`
- `coverage json -o coverage/S6A/coverage.json`
- `python3 script/check_python_coverage.py --coverage-json coverage/S6A/coverage.json --include-module kernel_gen.dsl.mlir_gen.emit.core --line-min 95 --branch-min 60`

#### 记录要求

- `执行前阅读记录：TODO 任务行、计划书 S6A、S6 记录、相关 DSL spec/test/实现`
- `自检：重点写 emit 入口、错误模型、默认值、符号/类型映射、测试断言有效性、是否存在冗余 helper`
- `Diff 反推自测：按实际 diff 补跑对应 pytest 与 scoped coverage`

#### 任务新建建议

- `任务类型：build`
- `任务目标：补齐 core.py emit / 解析覆盖，保持公开 MLIR 语义不变`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260423-python-quality-s6-core-emit.md`

### S6B：parser.py + tile.py 基线交接

#### 上下文摘要

- S6B 已完成 parser / tile 初始补测和真实覆盖差距记录，但两类文件职责差异较大，后续不再由同一任务继续扩范围。

#### 阶段目标

- 保留 `T-20260423-bc786e6c` 已完成的自检、Diff 反推自测和覆盖差距记录。
- 将 parser 与 tile 后续工作拆成 S6B1 / S6B2，不在 S6B 内继续新增实现或测试。

#### 非目标

- 不继续扩大 S6B 的实现范围。
- 不修改 `expectation/`。

#### 目标 spec / API

- [`spec/dsl`](../../spec/dsl)
- [`spec/pass`](../../spec/pass)
- S6B 任务记录：[`wt-20260423-python-quality-s6-parser-tile/agents/codex-multi-agents/log/task_records/2026/17/20260423-python-quality-s6-parser-tile.md`](../../wt-20260423-python-quality-s6-parser-tile/agents/codex-multi-agents/log/task_records/2026/17/20260423-python-quality-s6-parser-tile.md)

#### 最小功能闭环

- S6B 记录写清 parser 当前 statement coverage `48%`、tile 当前 statement coverage `85%`、已补测试和剩余缺口。
- S6B1 / S6B2 任务边界已经写入计划书，管理员可直接分发。
- `expectation` 仍只作为合同验收资产单列。

#### 验收必过项目

- `T-20260423-bc786e6c` 保持暂停状态，不再继续扩大范围。
- S6B1 与 S6B2 建任务后分别按独立阶段验收。

#### 记录要求

- `执行前阅读记录：TODO 任务行、计划书 S6B、S6 记录、T-20260423-bc786e6c 任务记录`
- `自检：重点写为何拆分、已完成内容、剩余缺口和后续任务边界是否清楚`

#### 任务新建建议

- `任务类型：build`
- `任务目标：作为 parser/tile 初始补测与拆分交接记录，不再继续扩大范围`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260423-python-quality-s6-parser-tile.md`

### S6B1：parser.py 解析覆盖补齐

#### 上下文摘要

- `kernel_gen/dsl/ast/parser.py` 当前 coverage 仍明显不足，S6B 记录显示 statement coverage 约 `48%`；该文件只收 DSL AST 解析，不应与 tile pass 混在同一任务内继续扩范围。

#### 阶段目标

- 为 [`kernel_gen/dsl/ast/parser.py`](../../kernel_gen/dsl/ast/parser.py) 补齐解析主链、异常路径、调用绑定、function / stmt 解析和边界输入的直接 pytest 覆盖。

#### 非目标

- 不修改 tile pass。
- 不改公开 DSL 语法语义，除非同步 spec 与测试。
- 不接入 `expectation`。

#### 目标 spec / API

- [`spec/dsl`](../../spec/dsl)
- [`kernel_gen/dsl/ast/parser.py`](../../kernel_gen/dsl/ast/parser.py)
- 相关 pytest：[`test/dsl/ast`](../../test/dsl/ast)

#### 最小功能闭环

- parser 主路径、非法语法、空输入、重复结构、未知节点、调用绑定、function / stmt 解析都有直接 pytest。
- scoped coverage 对 `kernel_gen.dsl.ast.parser` 达到 line `95` / branch `60`。
- 若 parser 仍过大，任务记录只能建议后续再拆 call 解析与 function / stmt 解析，不得在本任务内继续扩大到 tile。

#### 验收必过项目

- `pytest -q test/dsl/ast`
- `coverage erase`
- `coverage run --branch --source=kernel_gen -m pytest -q test/dsl/ast`
- `coverage json -o coverage/S6B1/coverage.json`
- `python3 script/check_python_coverage.py --coverage-json coverage/S6B1/coverage.json --include-module kernel_gen.dsl.ast.parser --line-min 95 --branch-min 60`

#### 记录要求

- `执行前阅读记录：TODO 任务行、计划书 S6B1、S6B 记录、相关 DSL spec/test/实现`
- `自检：重点写语法边界、异常文本、调用绑定、测试有效性、重复测试合并和可维护性`
- `Diff 反推自测：按实际 diff 补跑对应 pytest 与 scoped coverage`

#### 任务新建建议

- `任务类型：build`
- `任务目标：补齐 parser.py 解析主链、异常路径与调用绑定覆盖`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260423-python-quality-s6-parser.md`

### S6B2：tile.py 下沉覆盖补齐

#### 上下文摘要

- `kernel_gen/passes/lowering/tile.py` 当前已具备部分 helper 测试，但 S6B 记录显示 statement coverage 约 `85%`；剩余缺口集中在 plan / rewrite / analysis 清理和边界路径。

#### 阶段目标

- 为 [`kernel_gen/passes/lowering/tile.py`](../../kernel_gen/passes/lowering/tile.py) 补齐 pass 主链、plan 构造、rewrite、analysis 清理、no-op、非法输入和 symbol/view 边界的直接 pytest 覆盖。

#### 非目标

- 不修改 DSL AST parser。
- 不扩展 tile pass 公开语义。
- 不新增 pass 包装层；pass 仍优先使用 xDSL 原生 rewrite / IR 遍历能力。

#### 目标 spec / API

- [`spec/pass`](../../spec/pass)
- [`kernel_gen/passes/lowering/tile.py`](../../kernel_gen/passes/lowering/tile.py)
- 相关 pytest：[`test/pass`](../../test/pass)

#### 最小功能闭环

- tile pass 主路径、失败路径、no-op、analysis 清理、symbol/view 与 compare 兼容边界都有直接 pytest。
- scoped coverage 对 `kernel_gen.passes.lowering.tile` 达到 line `95` / branch `60`。
- 任务记录写清是否存在过大函数、重复 helper、过时注释或可复用边界。

#### 验收必过项目

- `pytest -q test/pass/test_lowering_tile.py test/pass/test_lowering_tile_analysis.py test/pass/test_lowering_tile_elewise.py test/pass/test_lowering_tile_reduce.py`
- `coverage erase`
- `coverage run --branch --source=kernel_gen -m pytest -q test/pass/test_lowering_tile.py test/pass/test_lowering_tile_analysis.py test/pass/test_lowering_tile_elewise.py test/pass/test_lowering_tile_reduce.py`
- `coverage json -o coverage/S6B2/coverage.json`
- `python3 script/check_python_coverage.py --coverage-json coverage/S6B2/coverage.json --include-module kernel_gen.passes.lowering.tile --line-min 95 --branch-min 60`

#### 记录要求

- `执行前阅读记录：TODO 任务行、计划书 S6B2、S6B 记录、相关 tile spec/test/实现`
- `自检：重点写 plan / rewrite / analysis 清理、no-op、xDSL 原生能力复用、测试是否重复和维护性`
- `Diff 反推自测：按实际 diff 补跑对应 pytest 与 scoped coverage`

#### 任务新建建议

- `任务类型：build`
- `任务目标：补齐 tile.py 的 plan / rewrite / analysis 清理与边界路径覆盖`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260423-python-quality-s6-tile.md`

### S6C：nn_lowering + analysis 覆盖补齐

#### 上下文摘要

- S6 已定位 `nn_lowering/*` 与 `analysis/*` 仍有成片覆盖缺口；这些模块涉及 lowering 规则、分析结果和错误边界，适合单独收口。

#### 阶段目标

- 为 [`kernel_gen/passes/lowering/nn_lowering`](../../kernel_gen/passes/lowering/nn_lowering) 与 [`kernel_gen/analysis`](../../kernel_gen/analysis) 补齐 pytest 覆盖。
- 覆盖 element、select、reduce、img2col、broadcast、softmax 默认轴、DMA/Kernel 读写分析、非法输入和 no-op。

#### 非目标

- 不扩展 nn op 语义。
- 不改公开 pass 名。
- 不把 analysis 结果改成兼容旧测试的临时格式。

#### 目标 spec / API

- [`spec/pass/lowering`](../../spec/pass/lowering)
- [`spec/analysis`](../../spec/analysis)
- 相关 pytest：[`test/pass/nn_lowering`](../../test/pass/nn_lowering)、[`test/analysis`](../../test/analysis)

#### 最小功能闭环

- lowering 与 analysis 的主路径、失败路径和边界路径有直接 pytest。
- scoped coverage 对 `kernel_gen.passes.lowering.nn_lowering` 与 `kernel_gen.analysis` 达到 line `95` / branch `60`。
- 所有新增测试都能从公开 spec 或稳定内部 helper 语义解释，不依赖 expectation。

#### 验收必过项目

- `pytest -q test/pass/nn_lowering test/analysis`
- `coverage erase`
- `coverage run --branch --source=kernel_gen -m pytest -q test/pass/nn_lowering test/analysis`
- `coverage json -o coverage/S6C/coverage.json`
- `python3 script/check_python_coverage.py --coverage-json coverage/S6C/coverage.json --include-module kernel_gen.passes.lowering.nn_lowering --include-module kernel_gen.analysis --line-min 95 --branch-min 60`

#### 记录要求

- `执行前阅读记录：TODO 任务行、计划书 S6C、S6 记录、相关 nn_lowering/analysis spec/test/实现`
- `自检：重点写 lowering 规则边界、错误模型、分析结果完整性、重复测试合并、helper 复用和维护性`
- `Diff 反推自测：按实际 diff 补跑对应 pytest 与 scoped coverage`

#### 任务新建建议

- `任务类型：build`
- `任务目标：补齐 nn_lowering 与 analysis 的 lowering / 分析覆盖`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260423-python-quality-s6-nn-analysis.md`

### S7：终验修复与归档前复核

#### 上下文摘要

- S6A / S6B1 / S6B2 / S6C 完成后，本阶段只处理终验发现的最小阻断，不再扩大范围做新设计。

#### 阶段目标

- 在最新同步现场跑全量 pytest、coverage gate、与本轮改动有关的 expectation 合同验收，并修复最小阻断项。

#### 非目标

- 不重开新范围。
- 不为了无关 expectation 修改已经确认合理的 pytest 或实现语义；若合同冲突，回到架构师裁定。

#### 目标 spec / API

- 全量 `spec/`
- 全量 `kernel_gen/`
- 全量 `test/`

#### 禁止修改面 / 合同真源

- 禁止修改面：不得修改 `expectation/`，除非用户另行明确授权。
- 合同真源：`spec + pytest + coverage gate + expectation terminal contract`

#### 最小功能闭环

- 最新同步现场通过全量 pytest、coverage gate 和相关 expectation 合同验收。
- 计划正文写回终验结论、验证基线、执行目录和必要摘要。

#### 执行步骤

1. 开始前 `git fetch` 并确认主目录或替代 worktree 对齐最新 `origin/main`。
2. 运行全量 pytest、coverage 阈值检查，以及本计划当前固定的相关 expectation 合同验收：`expectation.execute_engine.npu_demo`、`expectation.pass.tile`、`expectation.pass.tile.analysis`、`expectation.pass.lowing.nn_lowering`、`expectation.dsl.mlir_gen.dialect.nn.softmax`。
3. 若失败，只围绕最小阻断项修复。
4. 写回计划终验记录。

#### 预期示例代码

```bash
git fetch origin
pytest -q test
coverage erase
coverage run --branch --source=kernel_gen -m pytest -q test
coverage json -o coverage/S7/coverage.json
python3 script/check_python_coverage.py --coverage-json coverage/S7/coverage.json --line-min 95 --branch-min 60
python3 -m expectation.execute_engine.npu_demo
python3 -m expectation.pass.tile
python3 -m expectation.pass.tile.analysis
python3 -m expectation.pass.lowing.nn_lowering
python3 -m expectation.dsl.mlir_gen.dialect.nn.softmax
```

#### 预期输出

```text
pytest passed
coverage ok
expectation passed
```

#### 目标验收入口

- 全量 `pytest`
- 全量 coverage gate
- 与本轮改动有关的 `expectation` 合同验收

#### 验收必过项目

- `pytest -q test`
- `coverage run --branch --source=kernel_gen -m pytest -q test`
- `coverage json -o coverage/S7/coverage.json`
- `python3 script/check_python_coverage.py --coverage-json coverage/S7/coverage.json --line-min 95 --branch-min 60`
- `python3 -m expectation.execute_engine.npu_demo`
- `python3 -m expectation.pass.tile`
- `python3 -m expectation.pass.tile.analysis`
- `python3 -m expectation.pass.lowing.nn_lowering`
- `python3 -m expectation.dsl.mlir_gen.dialect.nn.softmax`

#### 记录要求

- `执行前阅读记录：TODO 任务行、计划书 S7、全局完成态/验收设计、S1-S6C 记录`
- `最小功能闭环：写清最新同步现场、验证基线、通过摘要或最小阻断项`
- `自检：重点写是否仍有已知 bug、逻辑问题、未覆盖边界、潜在漏洞、维护性缺口、兼容债或环境例外`

#### 任务新建建议

- `任务类型：build`
- `任务目标：完成 Python 质量重构终验修复与归档前验证`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260422-python-quality-s7-final.md`

## 待确认项

- 当前无待确认项。
- 已确认：coverage 范围只统计 `kernel_gen/**/*.py`。
- 已确认：`kernel_gen/`、`test/`、`script/` 不允许出现任何与 expectation 相关的实现、测试代码、import、调用、路径特判或兼容逻辑。
- 已确认：pass、mlir_gen、codegen 等 IR 测试使用 tool 驱动的 case 化形式；形式上可以像 expectation case 一样组织，但归属 tool / pytest，不使用 asset 形态，也不放入 expectation。

## 用户确认与协同约束

- `用户确认状态：已确认`
- `未确认事项：无`
- `用户确认结论：coverage 只统计 kernel_gen；不得有任何 expectation 相关实现/代码；IR 测试随 tool 以 case 化形式测试，不使用 asset 形态`
- `未确认前处理要求：不适用`
- `若用户要求至少询问 3 人：当前未要求`
- `询问记录 1：无`
- `询问记录 2：无`
- `询问记录 3：无`

## 计划书自检

- 通用自检：已读计划书标准和模板；未越权修改实现/test/expectation；本轮只新增计划书；计划命令只是最低集合，执行与审查仍需 diff 反推测试。
- spec 自检：计划要求每个被改 API 同步检查参数、返回、异常、边界、兼容性、示例和非目标；没有把 spec 写成纯说明文。
- build 自检：计划要求每个阶段同步检查实现遗漏、冗余、复用、注释准确性、函数粒度、模块边界、依赖方向、错误模型、资源/错误/性能/兼容性和测试断言有效性。
- review 自检：计划要求审查不接受空泛自检，必须找特殊情况、内容完整性、冗余、维护性、扩展性、可读性和所有可改进点。
- 计划书自检：示例、API、边界、依赖、非目标、验收入口和用户确认项已写清；IR 测试已按用户口径改为随 tool case 化测试、不使用 asset 形式；执行人读单个 Sx 可判断目标、非目标、步骤、验收和记录要求；当前无待确认项。

## 参考资料

- [`agents/standard/计划书标准.md`](../../agents/standard/计划书标准.md)：计划结构、阶段自包含、终验和 diff 反推要求。
- [`agents/standard/协作执行通用规则.md`](../../agents/standard/协作执行通用规则.md)：执行前阅读、自检、diff 反推和终验规则。
- [`agents/standard/审查规范.md`](../../agents/standard/审查规范.md)：审查必须覆盖自检、维护性、测试有效性和所有可改进点。
- [`spec/script/python_coverage_check.md`](../../spec/script/python_coverage_check.md)：coverage 阈值检查公开合同。
- [`spec/script/python_coverage_omit.md`](../../spec/script/python_coverage_omit.md)：薄包装 omit 清单边界。
