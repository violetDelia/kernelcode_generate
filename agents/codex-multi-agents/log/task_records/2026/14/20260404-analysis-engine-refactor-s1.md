
时间：2026-04-04 23:11:20 +0800
经办人：金铲铲大作战
任务：T-20260404-44d4afcf
任务目标：建立 compute/memory 注册与统一 orchestrator，移除 analysis.py 硬编码分发列表。
改动：
- kernel_gen/analysis/compute/__init__.py：新增 compute registry/装饰器与懒加载注册默认 analyzers。
- kernel_gen/analysis/memory/__init__.py：新增 memory registry/装饰器与 DMA analyzer 适配入口。
- kernel_gen/analysis/analysis.py：通过 registry 汇聚 compute/memory analyzer，允许同一 op 命中两类；新增结果合并与 memory 结果归一化。
测试：
- pytest -q test/analysis/test_analysis.py test/pass/test_analysis_func_cost.py test/pass/test_pass_manager.py（exit=0）
结论：S1 registry/orchestrator 骨架完成，gate 通过。

时间：2026-04-04 22:45:30 +0800
经办人：提莫炖蘑菇
任务：T-20260404-b67dba97
任务目标：复审 analysis_engine_refactor_green S1 骨架（registry+orchestrator）是否满足范围/验收/门禁；重点核对 registry API 稳定性、compute+memory 同时命中、未注册 fallback 行为、以及 AnalyzeFuncCostPass 下游不引入第二套公式主线。
改动：无（复审）
证据：
- diff 范围（应仅含允许文件 + 记录）：
  - cd /home/lfr/kernelcode_generate && git diff --name-only
    - kernel_gen/analysis/analysis.py
    - kernel_gen/analysis/compute/__init__.py
    - kernel_gen/analysis/memory/__init__.py
- gate 复跑（exit=0）：
  - cd /home/lfr/kernelcode_generate && pytest -q test/analysis/test_analysis.py test/pass/test_analysis_func_cost.py test/pass/test_pass_manager.py（exit=0，70 passed）

问题列表：
- P1｜compute registry 默认 analyzer 注册逻辑不稳：用户先注册会阻断默认 analyzers
  - 位置：kernel_gen/analysis/compute/__init__.py（`_ensure_default_analyzers_registered` 以 `_COMPUTE_ANALYZERS` 是否为空作为“默认已注册”判定）
  - 现象：若外部在首次调用 `iter_compute_analyzers()` 前先调用 `register_compute_analyzer(custom)`，则 `_COMPUTE_ANALYZERS` 非空，默认 analyzers 永远不会注册，导致大量 op 直接进入 “unsupported op” warning/skip。
  - 风险：违反“compute analyzer 可独立注册/查询”直觉预期；也会让下游（analysis(...) / AnalyzeFuncCostPass）在扩展场景出现不可预期的大面积 fallback（skip+warning）。
  - 建议：将“默认 analyzers 是否已注册”的判断与 `_COMPUTE_ANALYZERS` 解耦（例如独立 boolean 标记），并确保默认 analyzers 只注册一次且不会因自定义注册而缺失；同时明确自定义 analyzer 与默认 analyzer 的顺序规则（避免无意改变优先级）。
- P1｜registry 装饰器 API 未覆盖“tuple/single op”口径（与复审关注点不符）
  - 位置：kernel_gen/analysis/compute/__init__.py、kernel_gen/analysis/memory/__init__.py（当前装饰器仅支持 `@register_*_analyzer` 直接注册函数，不支持显式声明“该 analyzer 负责哪些 op”）
  - 风险：无法从注册层面保证“同一 op 只命中一个 compute analyzer”（避免重复计数），也不利于稳定查询/覆盖（尤其在 analyzer 数量增长后）。
  - 建议：若目标是“按 op 映射注册”，需将 decorator 形态升级为 `@register_xxx_analyzer(op_name | (op1,op2,...))`，并提供查询 API；若坚持“函数自判定”模式，则需在 spec/注释中明确“重复命中策略/冲突策略”，并补测覆盖。
- P2｜工作区存在与本任务无关的未跟踪目录（仅提示风险）
  - 现象：`git status` 可见未跟踪 `wt-20260404-exp-frontend-semantic-s1/`（不在本任务 diff 中）。
  - 风险：若后续合并/打包流程误包含未跟踪目录，会污染提交；建议合并前显式确认仅提交允许文件。

漏洞排查结果（6 类）：
- 输入校验绕过：本次为 orchestrator/registry 变更，主要风险在“注册缺失导致 silent skip”；当前 `analysis(...)` 未命中 analyzer 会 warning+skip（结论：存在配置/扩展场景风险，需修正注册逻辑）。
- 类型/形状绕过：不涉及 dtype/shape 推导（结论：不适用）。
- 边界越界：不涉及数组访问（结论：不适用）。
- 错误处理缺失：DMA analyzer 仍保持 ValueError→AnalysisError 的硬错误语义；未命中 analyzer 路径为 warning+skip（结论：行为清晰，但需限定 skip 适用范围并避免“因注册缺失导致误 skip”）。
- 状态污染：registry 为模块级全局列表，存在“导入顺序/提前注册改变默认注册行为”的状态风险（结论：需修正）。
- 资源释放问题：不涉及外部资源（结论：不适用）。

改进建议：无（除上述必须修改项外未发现额外改进点）
结论：需修改（P1：compute registry 默认注册与装饰器口径不满足稳定性预期）

时间：2026-04-04 23:59:10 +0800
经办人：金铲铲大作战
任务：T-20260404-80b85158
任务目标：修复 compute/memory registry 稳定性与装饰器 API。
改动：
- kernel_gen/analysis/compute/__init__.py：拆分默认/自定义 registry，默认 analyzers 与外部注册解耦；新增 register_compute 支持单 op / tuple op 注册，重复 op 注册直接报错；新增按 op 过滤的 iter_compute_analyzers_for_op。
- kernel_gen/analysis/memory/__init__.py：新增 memory registry 对应装饰器与按 op 过滤迭代；默认 DMA analyzer 通过 _ensure_default_analyzers_registered 稳定注册。
- kernel_gen/analysis/analysis.py：改用 iter_compute_analyzers_for_op / iter_memory_analyzers_for_op。
策略说明：
- 默认 analyzers 始终注册（与外部注册顺序无关），顺序固定为“默认在前，自定义在后”。
- op 映射注册重复时直接 ValueError；op 映射 analyzer 与通用 analyzer 可同时命中，同名 analyzer 在同一轮次去重后合并统计。
测试：
- pytest -q test/analysis/test_analysis.py test/pass/test_analysis_func_cost.py test/pass/test_pass_manager.py（exit=0）
结论：registry 稳定性与装饰器 API 对齐，gate 通过。

时间：2026-04-05 00:05:12 +0800
经办人：金铲铲大作战
补充：清理 iter_compute_analyzers 内重复 _ensure_default_analyzers_registered 调用；复跑 gate。
测试：
- pytest -q test/analysis/test_analysis.py test/pass/test_analysis_func_cost.py test/pass/test_pass_manager.py（exit=0）

时间：2026-04-05 00:12:40 +0800
经办人：提莫炖蘑菇
任务：T-20260404-25e76f7a
任务目标：复审 analysis_engine_refactor_green S1 修复（registry 默认注册稳定 + register_compute/register_memory 支持 op/tuple + 冲突策略），并复跑 gate。
改动：无（复审）
证据：
- diff 范围（仅允许 analysis.py + compute/__init__.py + memory/__init__.py + 记录）：
  - cd /home/lfr/kernelcode_generate && git diff --name-only
    - kernel_gen/analysis/analysis.py
    - kernel_gen/analysis/compute/__init__.py
    - kernel_gen/analysis/memory/__init__.py
- gate 复跑（exit=0）：
  - cd /home/lfr/kernelcode_generate && pytest -q test/analysis/test_analysis.py test/pass/test_analysis_func_cost.py test/pass/test_pass_manager.py
    - 70 passed in 0.64s

复审要点核对：
- 默认 analyzers 注册稳定性：compute/memory 均以 `_DEFAULT_REGISTERED` 独立布尔标记控制默认注册；`iter_*`/`iter_*_for_op` 会先 `_ensure_default_analyzers_registered()`，因此“先自定义注册”不会阻断默认 analyzers。
- API 覆盖：`register_compute/register_memory` 通过 `_normalize_op_keys` 支持 `str` 与 `op.name`（对象带 name 属性）以及 `tuple/list/set`；装饰器形态与显式函数接口一致。
- 重复注册冲突策略：同一 op 再注册不同 analyzer 直接 `ValueError("compute/memory analyzer already registered for op: <op>")`，错误口径稳定。
- compute+memory 同时命中：`analysis._analyze_ir_op` 先迭代 compute，再迭代 memory；命中结果进入同一 `analyzed_ops`，最终 `_merge_analyzed_ops` 汇总；`iter_*_for_op` 内部 `_iter_unique_analyzers` 去重避免同一 analyzer 被重复执行导致 silently drop/重复计数。
- 下游行为：gate 覆盖 `analysis(...)`、`AnalyzeFuncCostPass` 与 pass manager（70 passed），未观察到回退到第二套公式主线。

结论：通过
