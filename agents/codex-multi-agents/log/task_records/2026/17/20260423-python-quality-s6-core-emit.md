# T-20260423-936c8ee9 / S6A

## 任务信息
- 任务状态: `build`
- 计划书: [`ARCHITECTURE/plan/python_quality_refactor_green_plan.md`](../../../../../../../ARCHITECTURE/plan/python_quality_refactor_green_plan.md)
- worktree: [`wt-20260423-python-quality-s6-core-emit`](../../../../../../../wt-20260423-python-quality-s6-core-emit)

## 执行前阅读记录
- 已读 `TODO.md` 中 `T-20260423-936c8ee9` 任务行，确认本轮只处理 `kernel_gen/dsl/mlir_gen/emit/core.py` 的 emit / 解析独立覆盖收口。
- 已读 [`ARCHITECTURE/plan/python_quality_refactor_green_plan.md`](../../../../../../../ARCHITECTURE/plan/python_quality_refactor_green_plan.md) 的 S6A 正文、全局完成态 / 验收设计，以及 S1 baseline / S6 tests coverage 前序记录。
- 已复核前序 S6 tests coverage 记录，确认 S6 已拆成 S6A / S6B1 / S6B2 / S6C，小切片收口优先，不再把 scope 扩成全局 coverage 新设计。

## 最小功能闭环
- `kernel_gen/dsl/mlir_gen/emit/core.py` 的剩余成功 / 失败分支通过 `test/dsl/mlir_gen/emit/test_core.py` 补齐，覆盖 `NnBroadcastAST` / `NnBroadcastToAST` / `DmaAllocAST` / `DmaCopyAST` / `DmaCastAST` / `MatmulAST` 等路径。
- `script/check_python_coverage.py` 的 `--include-module kernel_gen.dsl.mlir_gen.emit.core` 过滤补齐了 `.py` 后缀路径匹配，避免 core.py 统计被路径格式挡住。
- `test/dsl/test_gen_kernel.py` 的 legacy-first import 顺序兼容测试补了 coverage 子进程环境隔离，避免测量环境干扰模块单例判定。
- `expectation` 只作为合同验收资产单列，不进入本轮 diff-driven 测试。

## 改动
- [`script/check_python_coverage.py`](../../../../../../../script/check_python_coverage.py): `_path_matches_module(...)` 增加 `.py` 后缀剥离匹配，确保 `kernel_gen.dsl.mlir_gen.emit.core` 能命中 `core.py`。
- [`test/script/test_python_coverage_check.py`](../../../../../../../test/script/test_python_coverage_check.py): 新增 include-module 过滤回归，覆盖 `.py` 后缀模块路径。
- [`test/fixtures/coverage/core_module_filter_pass.json`](../../../../../../../test/fixtures/coverage/core_module_filter_pass.json): 新增 module filter 通过样例。
- [`test/dsl/mlir_gen/emit/test_core.py`](../../../../../../../test/dsl/mlir_gen/emit/test_core.py): 增补 `CORE-014` / `CORE-020` 分支覆盖，并把临时 AST 改成命名变量，避免 `id()` 复用污染后续 `emit_mlir` 断言。
- [`test/dsl/test_gen_kernel.py`](../../../../../../../test/dsl/test_gen_kernel.py): legacy-first import 顺序子进程测试清理 `COVERAGE*` / `COV_CORE*` 环境变量，避免 coverage 注入干扰模块单例校验。

## 验证
- `pytest -q test/dsl/mlir_gen/emit/test_core.py` -> `21 passed`
- `pytest -q test/script/test_python_coverage_check.py` -> `6 passed`
- `COVERAGE_FILE=.coverage.s6a coverage run --branch --source=kernel_gen -m pytest -q test/dsl/test_emit_mlir.py test/dsl/mlir_gen/emit test/dsl/test_gen_kernel.py` -> `191 passed`
- `COVERAGE_FILE=.coverage.s6a coverage json -o coverage/S6A/coverage.json` -> 通过
- `COVERAGE_FILE=.coverage.s6a python3 script/check_python_coverage.py --coverage-json coverage/S6A/coverage.json --include-module kernel_gen.dsl.mlir_gen.emit.core --line-min 95 --branch-min 60` -> `coverage ok: scope=kernel_gen/dsl/mlir_gen/emit/core (1 file(s)); line=95.47% >= 95.00%; branch=91.59% >= 60.00%`
- `git diff --check` -> 通过

## Diff 反推自测
- 按实际 diff 回推的测试入口为 `test/dsl/mlir_gen/emit/test_core.py`、`test/script/test_python_coverage_check.py` 与 `test/dsl/test_gen_kernel.py`，均已在本轮验证通过。
- 覆盖率门禁按实际 diff 回推到 `core.py` 的 scoped coverage，`include-module` 路径过滤也有对应 fixture 回归，不再依赖 expectation 资产替代测试。

## 合同验收
- expectation 未作为本轮 diff-driven 测试使用，保持单列；本轮未额外运行 expectation 合同验收。

## 自检
- 已读完整 S6A 阶段、全局完成态 / 验收设计、S1 baseline 与前序 S6 tests coverage 记录；未越权扩大到 S6B / S6C。
- 变更只落在当前 worktree；主仓未新增本轮改动。
- `test_core.py` 的临时 AST 命名化是为了解决 `id()` 复用导致的 cache 键污染，不是为了放宽断言；新增断言仍能在实现回退时失败。
- `test_gen_kernel.py` 的环境清理只针对 coverage 注入变量，不改变公开行为；其目的是让模块单例测试在测量环境下仍然稳定。
- `script/check_python_coverage.py` 的 `.py` 后缀匹配属于路径归一化修正，和 gate 语义一致。
- 代码质量检查矩阵已覆盖 API、边界、异常、复用、函数粒度、可维护性、冗余与测试有效性；未见当前切片内已知 bug / 逻辑问题 / 潜在漏洞。

## 结论
- 通过；当前 S6A build 已完成，任务记录已写回 worktree。请按流程执行 `-next` 并回报管理员。

时间：2026-04-23 04:20 +0800
经办人：提莫炖蘑菇
任务：T-20260423-936c8ee9
任务目标：复核 `ARCHITECTURE/plan/python_quality_refactor_green_plan.md` 的 S6A，按实际 diff 做 `Diff 反推审查`，核对 `emit/core.py` 相关覆盖、coverage 过滤修正与 `expectation` 单列口径。
执行前阅读记录：已读 `TODO.md` 中 `T-20260423-936c8ee9` 任务行、计划书 `python_quality_refactor_green_plan.md` 的 S6A 正文、全局完成态 / 验收设计、S1 baseline / S6 tests coverage 前序记录，以及 build 记录里关于 `script/check_python_coverage.py`、`test/script/test_python_coverage_check.py`、`test/dsl/mlir_gen/emit/test_core.py`、`test/dsl/test_gen_kernel.py`、`test/fixtures/coverage/core_module_filter_pass.json` 的实际改动与自检摘要。
最小功能闭环：补齐 `kernel_gen/dsl/mlir_gen/emit/core.py` 相关 helper / 错误 / lowering 变体覆盖，并把 `script/check_python_coverage.py` 的 `--include-module kernel_gen.dsl.mlir_gen.emit.core` 路径过滤修正到能识别 `.py` 后缀模块文件，保证 scoped coverage 门禁可以稳定落到 core.py。
改动：
- 更新 [`script/check_python_coverage.py`](../../../../../../../script/check_python_coverage.py)，为 `_path_matches_module(...)` 增加 `.py` 后缀剥离匹配，避免 `kernel_gen.dsl.mlir_gen.emit.core` 的 scoped coverage 被 `core.py` 路径格式挡住。
- 更新 [`test/script/test_python_coverage_check.py`](../../../../../../../test/script/test_python_coverage_check.py)，新增 include-module 过滤的 `.py` 后缀路径回归。
- 新增 [`test/fixtures/coverage/core_module_filter_pass.json`](../../../../../../../test/fixtures/coverage/core_module_filter_pass.json)，提供 module filter 通过样例。
- 新增 [`test/dsl/mlir_gen/emit/test_core.py`](../../../../../../../test/dsl/mlir_gen/emit/test_core.py)，补齐 `EmitContext` 校验、dtype 映射、shape / stride / launch extent / index value / lowering 边界与部分 lowering 变体覆盖。
- 更新 [`test/dsl/test_gen_kernel.py`](../../../../../../../test/dsl/test_gen_kernel.py)，清理子进程中的 `COVERAGE*` / `COV_CORE*` 环境变量，避免 coverage 注入干扰 legacy-first 模块单例测试。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-python-quality-s6-core-emit:/home/lfr/kernelcode_generate python3 -m pytest -q test/dsl/mlir_gen/emit/test_core.py test/script/test_python_coverage_check.py test/dsl/test_gen_kernel.py` -> `92 passed, 15 warnings`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-python-quality-s6-core-emit:/home/lfr/kernelcode_generate coverage run --branch --source=kernel_gen -m pytest -q test/dsl/test_emit_mlir.py test/dsl/mlir_gen/emit test/dsl/test_gen_kernel.py` -> `191 passed, 15 warnings`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-python-quality-s6-core-emit:/home/lfr/kernelcode_generate coverage json -o coverage/S6A/coverage.json` -> 通过
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260423-python-quality-s6-core-emit:/home/lfr/kernelcode_generate python3 script/check_python_coverage.py --coverage-json coverage/S6A/coverage.json --include-module kernel_gen.dsl.mlir_gen.emit.core --line-min 95 --branch-min 60` -> `coverage ok: scope=kernel_gen/dsl/mlir_gen/emit/core (1 file(s)); line=95.47% >= 95.00%; branch=91.59% >= 60.00%`
- `git diff --check` -> 通过
Diff 反推审查：按实际 diff 复核 `script/check_python_coverage.py` 的 `.py` 后缀模块前缀归一化、`test/script/test_python_coverage_check.py` 的 include-module 过滤回归、`test/dsl/mlir_gen/emit/test_core.py` 的 emit core helper / edge-case 覆盖，以及 `test/dsl/test_gen_kernel.py` 的子进程覆盖环境隔离；确认这些测试在实现回退时会直接失败，且 `expectation` 没有被拿来替代本轮 diff-driven 测试。
合同验收（如适用）：未执行。本轮为 review，`expectation` 仍只作为合同验收资产单列，不替代对应测试。
自检：已核对 build 记录、自测口径与当前实际 diff；`test_core.py` 针对 emit core helper 与错误边界的断言能在实现坏掉时失败；`test_python_coverage_check.py` 的 fixture 直接锁定 `.py` 后缀路径的 include-module 行为；`test_gen_kernel.py` 的环境清理仅影响子进程 coverage 注入，不改变公开行为；`git diff --check` 通过，未见新增语法/空白问题。
代码质量矩阵审查：
- API：`script/check_python_coverage.py` 的公开 CLI 参数保持不变，仍是 `--coverage-json`、`--line-min`、`--branch-min`、`--include-module`。
- 边界：新增路径归一化修正不会扩大匹配到无关文件，include-module 仍按模块前缀判断。
- 错误模型：覆盖率检查失败仍然通过 `CoverageCheckError` / CLI 非零退出暴露。
- 模块边界：产品测试未引入 expectation 依赖，coverage 工具仍留在脚本层。
- 依赖方向：`test/`、`script/` 未新增对 `expectation` 的运行时 import / 调用。
- 复用：`test_core.py` 复用 helper 构造 emit 上下文和 memory/type 样例，减少重复搭建。
- 函数粒度：新增私测 helper 保持在测试文件内，未抽成多余公共层。
- 可读性：新测试命名和注释直接说明覆盖意图与回归点。
- 注释示例：新增测试文件和脚本函数都已补创建者、使用示例、关联文件链接。
- 兼容债：`.py` 后缀兼容属于必要路径归一化，不是历史 alias 或临时特判。
- 测试质量：新增回归能直接锁住路径过滤与 emit core 边界，不是只为 coverage 计数。
- 可演进性：后续若继续扩展 emit core 覆盖，当前 fixture / helper 可复用到更多变体。
可改进点：`test/dsl/mlir_gen/emit/test_core.py` 当前仍较长，后续若继续往里加 helper，建议按 lowerer 子域再拆更细一点；另外 `test/dsl/test_gen_kernel.py` 的 coverage 环境清理逻辑可以后续抽一个共享测试 helper，减少同类子进程测试的重复代码。
结论：通过。S6A 的 coverage 路径过滤修正、emit core helper 覆盖和子进程环境隔离都成立，`expectation` 仍只作为合同验收资产单列，没有替代对应测试，当前 review 无新增阻断项。

## Merge 收口

- `时间`：`2026-04-23 07:41:01 +0800`
- `经办人`：`李白`
- `任务`：`T-20260423-936c8ee9（merge）`
- `执行前阅读记录`：再次核对 `TODO.md` 中的任务行、`ARCHITECTURE/plan/python_quality_refactor_green_plan.md` 的 S6A 正文、全局完成态/验收设计，以及本轮 build / review 记录中的真实 diff、自检与 `Diff 反推审查` 结论。
- `收口过程`：在最新主线基线上复核本轮工作树差异，确认本轮仅包含 `script/check_python_coverage.py`、`test/script/test_python_coverage_check.py`、`test/dsl/mlir_gen/emit/test_core.py`、`test/dsl/test_gen_kernel.py`、`test/fixtures/coverage/core_module_filter_pass.json` 与任务记录文件；`expectation` 仍保持为合同验收资产单列，没有进入 diff-driven 测试，也没有替代改动文件对应 pytest。
- `本轮范围`：`script/check_python_coverage.py`、`test/script/test_python_coverage_check.py`、`test/dsl/mlir_gen/emit/test_core.py`、`test/dsl/test_gen_kernel.py`、`test/fixtures/coverage/core_module_filter_pass.json`、`agents/codex-multi-agents/log/task_records/2026/17/20260423-python-quality-s6-core-emit.md`
- `真实结果`：本轮收口已对齐到真实 diff 与真实 pytest / review 证据，任务状态接下来可以切到完成列并按流程同步。
