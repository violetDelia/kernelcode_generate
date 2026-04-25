# 20260425-tuner-cost-emitc-include-repair-s5

- 任务 ID：`T-20260425-179e2ee1`
- 创建者：`守护最好的爱莉希雅`
- 最后修改人：`睡觉小分队`
- 关联计划：[tuner_cost_emitc_include_green_plan.md](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/tuner_cost_emitc_include_green_plan.md)
- 相关 `spec`：[spec/dsl/emit_c.md](/home/lfr/kernelcode_generate/spec/dsl/emit_c.md)
- 相关 `test`：[test/dsl/test_emit_c.py](/home/lfr/kernelcode_generate/test/dsl/test_emit_c.py)
- 相关实现：[expectation/dsl/emit_c/npu_demo/__main__.py](/home/lfr/kernelcode_generate/expectation/dsl/emit_c/npu_demo/__main__.py)

## 任务目标

- 只处理 `expectation/dsl/emit_c/npu_demo` 目录入口与当前真实文件集合的对齐。
- 当前真实集合仅包含 `__main__.py` 与 `cost/`；目录入口不得再依赖缺失的 `header/kernel/dma/symbol` 子模块。
- 同步收口与该入口直接关联的实现、`spec`、`test` 说明。

## 执行前阅读记录

- 已读根目录 [AGENTS.md](/home/lfr/kernelcode_generate/AGENTS.md)。
- 已读计划正文 [tuner_cost_emitc_include_green_plan.md](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/tuner_cost_emitc_include_green_plan.md) 中 `0d3eb0c` 复验段。
- 已核对最新基线 `origin/main@0d3eb0ce01f47d25adedc85ec2fc75842c0005e5` 下 `expectation/dsl/emit_c/npu_demo/` 的实际文件集合。

## 最小功能闭环

- 让 `python3 -m expectation.dsl.emit_c.npu_demo` 能在当前真实目录结构下直接运行。
- 目录入口只聚合当前实际存在的合同资产。
- 不修改任何 `[immutable-file]`。

## 边界

- 不得改动任何 `[immutable-file]`。
- 不得扩写无关 `expectation` 目录。
- 只处理 `expectation/dsl/emit_c/npu_demo` 目录入口及其直接关联的实现、`spec`、`test` 收口。

## 自检

- 本轮仅完成任务创建与边界写入，未改实现、测试或合同资产。
- 任务目标、约束和最小闭环已写清，可直接进入执行。

## Diff 反推自测

- 本轮仅为任务创建，暂无实现 diff，未运行测试。

---

时间：2026-04-25 04:31 +0800
经办人：睡觉小分队
任务：T-20260425-179e2ee1
任务目标：核对 `expectation/dsl/emit_c/npu_demo` 目录入口与当前真实文件集合是否存在可由 `spec` 侧直接收口的差异，并在角色边界内处理。
执行前阅读记录：已读 `/home/lfr/kernelcode_generate/TODO.md` 当前任务行、根目录 `AGENTS.md`、`agents/codex-multi-agents/agents/睡觉小分队/睡觉小分队.prompt.md`、当前任务预建记录、共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/tuner_cost_emitc_include_green_plan.md` 的 `0d3eb0c` 复验段与修复任务段、`wt-20260425-tuner-cost-emitc-include-repair-s5/spec/dsl/emit_c.md`、`wt-20260425-tuner-cost-emitc-include-repair-s5/test/dsl/test_emit_c.py`，并核对 `wt-20260425-tuner-cost-emitc-include-repair-s5/expectation/dsl/emit_c/npu_demo` 的真实文件集合仅为 `__main__.py` 与 `cost/`。
最小功能闭环：确认当前阻断点是否存在可由 `spec` 角色处理的文字差异；若实际阻断仅在 `expectation` 目录入口实现本体，则写阻塞记录并回报管理员重派。
改动：
- 未修改任何 `spec`、实现、测试或 `expectation` 文件。
- 更新当前任务记录，写明本轮核对结果：计划正文、`spec` 与测试口径已和“真实文件集合只有 `__main__.py` 与 `cost/`”一致；当前未收口点只在 `expectation/dsl/emit_c/npu_demo/__main__.py` 与 `expectation/dsl/emit_c/npu_demo/cost/__main__.py` / `cost/*.py` 仍依赖缺失的 `header/kernel/dma/symbol/_shared`。
验证：
- `find /home/lfr/kernelcode_generate/wt-20260425-tuner-cost-emitc-include-repair-s5/expectation/dsl/emit_c/npu_demo -maxdepth 2 -type f | sort`：当前真实文件集合仅命中 `__main__.py`、`cost/__main__.py`、`cost/dma_copy.py`、`cost/kernel_binary_add.py`、`cost/kernel_matmul.py`。
- `cd /home/lfr/kernelcode_generate/wt-20260425-tuner-cost-emitc-include-repair-s5 && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo`：失败，`ModuleNotFoundError: No module named 'expectation.dsl.emit_c.npu_demo.header'`。
- `cd /home/lfr/kernelcode_generate/wt-20260425-tuner-cost-emitc-include-repair-s5 && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.cost`：失败，`ModuleNotFoundError: No module named 'expectation.dsl.emit_c.npu_demo._shared'`。
- `rg -n "from \\.header|from \\.kernel|from \\.dma|from \\.symbol|from expectation\\.dsl\\.emit_c\\.npu_demo\\._shared|from \\.\\._shared" expectation/dsl/emit_c/npu_demo -g '*.py'`：确认当前未收口点全部位于 `expectation` 目录入口及其辅助引用。
Diff 反推自测：本轮未产生可提交 diff。按任务目标反推后，唯一需要改动的文件是 `expectation/dsl/emit_c/npu_demo/__main__.py` 与 `expectation/dsl/emit_c/npu_demo/_shared.py` / `cost/*.py` 这一组 `expectation` 实现文件；它们不属于 `spec` 角色可改范围，也不属于本轮可由纯文本 `spec` 收口解决的问题。
合同验收（如适用）：已按计划正文当前目录入口要求尝试运行 `python3 -m expectation.dsl.emit_c.npu_demo` 与 `python3 -m expectation.dsl.emit_c.npu_demo.cost`，两者均因目录入口实现仍引用缺失模块而失败；这是当前阻塞证据，不计入 `Diff 反推自测`。
自检：已读任务行、计划复验段、相关 `spec/test/实现` 与当前目录真实文件集合；未越权修改实现、测试、`expectation` 或任何 `[immutable-file]`；当前计划正文和 `spec/test` 已与真实文件集合一致，没有可继续由 `spec` 侧收口的直接差异；唯一缺口在 `expectation` 目录入口实现本体，超出当前角色权限。
结论：当前任务阻塞。阻塞原因不是 `spec` 文案，而是 `expectation/dsl/emit_c/npu_demo` 目录入口与 `cost/` 子目录仍依赖缺失模块，需改 `expectation` 实现文件；已按流程回报管理员，请求重派到可处理 `expectation`/实现的角色或明确授权。

---

时间：2026-04-25 08:45 +0800
经办人：朽木露琪亚
任务：T-20260425-179e2ee1
任务目标：按当前真实文件集合收口 `expectation/dsl/emit_c/npu_demo` 目录入口，只保留 `cost/` 聚合链路，并补齐直接关联的实现、`spec` 与 `pytest` 自测。
执行前阅读记录：
- 已读 [/home/lfr/kernelcode_generate/TODO.md](/home/lfr/kernelcode_generate/TODO.md) 当前任务行，确认本轮为 `build`，边界限定在 `expectation/dsl/emit_c/npu_demo` 目录入口与直接关联的实现/spec/test。
- 已读 [AGENTS.md](/home/lfr/kernelcode_generate/AGENTS.md)、[/home/lfr/kernelcode_generate/agents/codex-multi-agents/agents/朽木露琪亚/朽木露琪亚.prompt.md](/home/lfr/kernelcode_generate/agents/codex-multi-agents/agents/朽木露琪亚/朽木露琪亚.prompt.md)、[tuner_cost_emitc_include_green_plan.md](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/tuner_cost_emitc_include_green_plan.md) 与本任务前序记录。
- 已核对当前真实文件集合仅包含 `expectation/dsl/emit_c/npu_demo/__main__.py`、`cost/__main__.py` 与 `cost/{dma_copy,kernel_binary_add,kernel_matmul}.py`，不存在 `header/kernel/dma/symbol` 子目录。
最小功能闭环：
- `python3 -m expectation.dsl.emit_c.npu_demo` 与 `python3 -m expectation.dsl.emit_c.npu_demo.cost` 在当前真实目录结构下都能运行通过。
- 目录入口不再依赖缺失的 `header/kernel/dma/symbol/_shared`。
- 新增的通用 helper 能被非 expectation 的 `pytest` 直接覆盖，避免把目录入口合同验收混充为 `Diff 反推自测`。
改动：
- 新增 [kernel_gen/tools/emitc_case_runner.py](/home/lfr/kernelcode_generate/wt-20260425-tuner-cost-emitc-include-repair-s5/kernel_gen/tools/emitc_case_runner.py)，统一承接 `emit_c` expectation 的 IR 解析、`EmitCContext(target="npu_demo")` 构造、源码片段断言与 `COMPILE_ARGS` 校验。
- 新增 [expectation/dsl/emit_c/npu_demo/_shared.py](/home/lfr/kernelcode_generate/wt-20260425-tuner-cost-emitc-include-repair-s5/expectation/dsl/emit_c/npu_demo/_shared.py)，把目录自动发现执行与 `run_emitc_case(...)` 复用统一到当前 `npu_demo` 目录入口。
- 修改 [expectation/dsl/emit_c/npu_demo/__main__.py](/home/lfr/kernelcode_generate/wt-20260425-tuner-cost-emitc-include-repair-s5/expectation/dsl/emit_c/npu_demo/__main__.py)，仅聚合当前真实存在的 `cost/` 子目录，不再硬依赖缺失的 `header/kernel/dma/symbol`。
- 修改 [expectation/dsl/emit_c/npu_demo/cost/__main__.py](/home/lfr/kernelcode_generate/wt-20260425-tuner-cost-emitc-include-repair-s5/expectation/dsl/emit_c/npu_demo/cost/__main__.py)，改为通过 sibling/absolute import 加载共享 runner，不再依赖旧的 `_shared` 路径或临时 `sys.path` 注入。
- 修改 [spec/dsl/emit_c.md](/home/lfr/kernelcode_generate/wt-20260425-tuner-cost-emitc-include-repair-s5/spec/dsl/emit_c.md)，补充当前 `npu_demo` 目录入口只允许聚合当前 tracked 子目录、不得硬依赖缺失 `header/kernel/dma/symbol` 的说明。
- 新增 [test/tools/test_emitc_case_runner.py](/home/lfr/kernelcode_generate/wt-20260425-tuner-cost-emitc-include-repair-s5/test/tools/test_emitc_case_runner.py)，用 `pytest` 锁定 helper 的正常 lowering 行为与非法 `COMPILE_ARGS` 拒绝逻辑。
验证：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_emitc_case_runner.py test/dsl/test_emit_c.py -k 'emitc_case_runner or npu_demo_tuner_cost' -ra`
  - `7 passed, 40 deselected, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo`
  - 通过，顺序执行 `dma_copy`、`kernel_binary_add`、`kernel_matmul`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.cost`
  - 通过，顺序执行 `dma_copy`、`kernel_binary_add`、`kernel_matmul`
- `python3 -m py_compile expectation/dsl/emit_c/npu_demo/__main__.py expectation/dsl/emit_c/npu_demo/_shared.py expectation/dsl/emit_c/npu_demo/cost/__main__.py kernel_gen/tools/emitc_case_runner.py test/tools/test_emitc_case_runner.py`
  - 通过
- `git diff --check`
  - 通过
Diff 反推自测：
- 依据实际 diff，非 expectation 测试口径只覆盖新增工具 helper 与直接关联的 `emit_c` 行为，执行：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_emitc_case_runner.py test/dsl/test_emit_c.py -k 'emitc_case_runner or npu_demo_tuner_cost' -ra`
- 未把 `python3 -m expectation.dsl.emit_c.npu_demo*` 计入 `Diff 反推自测`。
合同验收（如适用）：
- 已单列运行 `python3 -m expectation.dsl.emit_c.npu_demo` 与 `python3 -m expectation.dsl.emit_c.npu_demo.cost`，确认目录入口与 `cost/` 子目录在当前真实文件集合下可直接运行。
- 该合同验收结果不替代 `Diff 反推自测`。
自检：
- API/入口：`npu_demo` 目录入口已与真实文件集合一致，聚合边界明确，只承接 `cost/`。
- 边界/异常：helper 显式拒绝非 `--pass no-op` 的 `COMPILE_ARGS`，`source_path`/`expected_snippets`/`op_name` 输入为空时会直接报错。
- 复用/函数粒度：把 IR 解析与源码断言沉到 `kernel_gen.tools.emitc_case_runner`，避免 `cost/*.py` 与目录入口重复维护。
- 维护性：`cost/__main__.py` 改成 package/absolute import 双路径，避免继续依赖旧目录结构与临时 `sys.path` 注入。
- 冗余：本轮未改动 `basic_all.py` 等无关 expectation 资产；只处理当前 blocker 涉及的入口与 helper。
- 测试有效性：`pytest` 直接覆盖新 helper 的成功/失败路径，目录入口合同验收单列执行，没有混入 `Diff 反推自测`。
结论：任务目标已完成，可以按 `TODO` 续到 `review`。

---

时间：2026-04-25 08:34 +0800
经办人：提莫炖蘑菇
任务：T-20260425-179e2ee1
阶段：review
执行前阅读记录：
- 已读 [`TODO.md`](../../../../../../TODO.md) 当前任务行、当前任务记录、计划正文 [`tuner_cost_emitc_include_green_plan.md`](../../../../../../../ARCHITECTURE/plan/tuner_cost_emitc_include_green_plan.md) 中 `0d3eb0c` 复验段、当前 diff 文件 [`kernel_gen/tools/emitc_case_runner.py`](../../../../../../../kernel_gen/tools/emitc_case_runner.py)、[`expectation/dsl/emit_c/npu_demo/__main__.py`](../../../../../../../expectation/dsl/emit_c/npu_demo/__main__.py)、[`expectation/dsl/emit_c/npu_demo/_shared.py`](../../../../../../../expectation/dsl/emit_c/npu_demo/_shared.py)、[`expectation/dsl/emit_c/npu_demo/cost/__main__.py`](../../../../../../../expectation/dsl/emit_c/npu_demo/cost/__main__.py)、[`spec/dsl/emit_c.md`](../../../../../../../spec/dsl/emit_c.md)、[`test/tools/test_emitc_case_runner.py`](../../../../../../../test/tools/test_emitc_case_runner.py)。
真实审查：
- 当前 residual diff 只涉及 `expectation/dsl/emit_c/npu_demo` 目录入口、共享 helper [`kernel_gen/tools/emitc_case_runner.py`](../../../../../../../kernel_gen/tools/emitc_case_runner.py)、对应 `spec` 与新增 `pytest`，边界与任务记录一致。
- [`expectation/dsl/emit_c/npu_demo/__main__.py`](../../../../../../../expectation/dsl/emit_c/npu_demo/__main__.py) 已收口为只聚合当前真实存在的 `cost/` 子目录，不再依赖缺失的 `header/kernel/dma/symbol`。
- [`expectation/dsl/emit_c/npu_demo/cost/__main__.py`](../../../../../../../expectation/dsl/emit_c/npu_demo/cost/__main__.py) 与 [`expectation/dsl/emit_c/npu_demo/_shared.py`](../../../../../../../expectation/dsl/emit_c/npu_demo/_shared.py) 已把目录发现与 case 运行逻辑收口到相对导入优先 + 绝对 fallback，不再依赖旧目录结构。
- [`kernel_gen/tools/emitc_case_runner.py`](../../../../../../../kernel_gen/tools/emitc_case_runner.py) 把 IR 解析、`EmitCContext(target=\"npu_demo\")` 构造和片段断言沉到工具层，且新增 [`test/tools/test_emitc_case_runner.py`](../../../../../../../test/tools/test_emitc_case_runner.py) 直接覆盖正常路径与非法 `COMPILE_ARGS` 拒绝路径，没有把 expectation 目录入口混充为 diff 反推测试。
- 当前切片内未再发现可直接执行的一线问题；剩余单条 warning 仍是 xDSL 上游 `irdl_options list` 弃用告警，不属于本仓本轮 diff。
Diff 反推审查：
- `cd /home/lfr/kernelcode_generate/wt-20260425-tuner-cost-emitc-include-repair-s5 && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_emitc_case_runner.py test/dsl/test_emit_c.py -k 'emitc_case_runner or npu_demo_tuner_cost' -ra` -> `7 passed, 40 deselected, 1 warning`
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260425-tuner-cost-emitc-include-repair-s5/expectation/dsl/emit_c/npu_demo/__main__.py /home/lfr/kernelcode_generate/wt-20260425-tuner-cost-emitc-include-repair-s5/expectation/dsl/emit_c/npu_demo/_shared.py /home/lfr/kernelcode_generate/wt-20260425-tuner-cost-emitc-include-repair-s5/expectation/dsl/emit_c/npu_demo/cost/__main__.py /home/lfr/kernelcode_generate/wt-20260425-tuner-cost-emitc-include-repair-s5/kernel_gen/tools/emitc_case_runner.py /home/lfr/kernelcode_generate/wt-20260425-tuner-cost-emitc-include-repair-s5/test/tools/test_emitc_case_runner.py` -> 通过
- `git -C /home/lfr/kernelcode_generate/wt-20260425-tuner-cost-emitc-include-repair-s5 diff --check` -> 通过
合同验收（如适用）：
- `cd /home/lfr/kernelcode_generate/wt-20260425-tuner-cost-emitc-include-repair-s5 && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo` -> 通过
- `cd /home/lfr/kernelcode_generate/wt-20260425-tuner-cost-emitc-include-repair-s5 && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.cost` -> 通过
- 上述 expectation 结果只单列为合同验收资产，不计入 `Diff 反推审查`。
自检：
- 已按当前 review 口径核对任务行、计划复验段、前序 build 记录与实际 diff 文件。
- 已确认 diff 反推测试使用的是 `pytest` 与 `py_compile`，没有把 expectation 入口当作替代测试。
- 已确认当前切片内没有遗漏的导入边界、目录聚合或 helper 覆盖缺口。
可改进点：
- 无。当前 review 范围内没有可直接执行的一线问题。
结论：`通过`。`expectation/dsl/emit_c/npu_demo` 目录入口、共享 helper、直接关联的 `spec/test` 与当前真实文件集合已收口一致。

---

时间：2026-04-25 22:02 +0800
经办人：李白
任务：T-20260425-179e2ee1
任务目标：按当前 worktree 收口 `npu_demo emit_c expectation` 目录入口、共享 helper、直接关联 `spec/test` 的 residual diff，并完成 merge / push / `-done`。
改动：
- 已核对当前 residual diff 只涉及：
  - [expectation/dsl/emit_c/npu_demo/__main__.py](/home/lfr/kernelcode_generate/wt-20260425-tuner-cost-emitc-include-repair-s5/expectation/dsl/emit_c/npu_demo/__main__.py)
  - [expectation/dsl/emit_c/npu_demo/_shared.py](/home/lfr/kernelcode_generate/wt-20260425-tuner-cost-emitc-include-repair-s5/expectation/dsl/emit_c/npu_demo/_shared.py)
  - [expectation/dsl/emit_c/npu_demo/cost/__main__.py](/home/lfr/kernelcode_generate/wt-20260425-tuner-cost-emitc-include-repair-s5/expectation/dsl/emit_c/npu_demo/cost/__main__.py)
  - [kernel_gen/tools/emitc_case_runner.py](/home/lfr/kernelcode_generate/wt-20260425-tuner-cost-emitc-include-repair-s5/kernel_gen/tools/emitc_case_runner.py)
  - [spec/dsl/emit_c.md](/home/lfr/kernelcode_generate/wt-20260425-tuner-cost-emitc-include-repair-s5/spec/dsl/emit_c.md)
  - [test/tools/test_emitc_case_runner.py](/home/lfr/kernelcode_generate/wt-20260425-tuner-cost-emitc-include-repair-s5/test/tools/test_emitc_case_runner.py)
  - 本任务记录文件
- 当前 worktree `HEAD` 与 `origin/main` 同为 `0d3eb0ce`，本轮 merge 只需要提交该 residual diff，不涉及额外重放或冲突处理。
验证：
- `cd /home/lfr/kernelcode_generate/wt-20260425-tuner-cost-emitc-include-repair-s5 && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_emitc_case_runner.py test/dsl/test_emit_c.py -k 'emitc_case_runner or npu_demo_tuner_cost' -ra`
  - 结果：`7 passed, 40 deselected, 1 warning`
- `cd /home/lfr/kernelcode_generate/wt-20260425-tuner-cost-emitc-include-repair-s5 && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo`
  - 结果：通过，顺序执行 `dma_copy / kernel_binary_add / kernel_matmul`
- `cd /home/lfr/kernelcode_generate/wt-20260425-tuner-cost-emitc-include-repair-s5 && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.cost`
  - 结果：通过，顺序执行 `dma_copy / kernel_binary_add / kernel_matmul`
- `cd /home/lfr/kernelcode_generate/wt-20260425-tuner-cost-emitc-include-repair-s5 && python3 -m py_compile expectation/dsl/emit_c/npu_demo/__main__.py expectation/dsl/emit_c/npu_demo/_shared.py expectation/dsl/emit_c/npu_demo/cost/__main__.py kernel_gen/tools/emitc_case_runner.py test/tools/test_emitc_case_runner.py`
  - 结果：通过
- `git -C /home/lfr/kernelcode_generate/wt-20260425-tuner-cost-emitc-include-repair-s5 diff --check`
  - 结果：通过
结论：merge 前验证已完成，可以继续执行提交、推送、`-done` 与管理员回报。
