# T-20260524-53daf9ec arch-parallelize-package-func-pattern-refactor

时间：2026-05-24 15:12 +0800
经办人：小李飞刀
任务：T-20260524-53daf9ec / arch-parallelize-package-func-pattern-refactor / execute
任务目标：按主仓只读计划书把 `arch-parallelize` 从单文件迁移为 package，并新增公开 `FuncOp` root rewrite pattern `_ArchParallelizeFuncPattern(block_num: int)`；保持 `ArchParallelizePass` 公开 API、registry 名称和稳定错误文本不变；只读验收 `expectation.pass.arch_parallelize`。
执行前阅读记录：
- 已读个人提示词 `agents/codex-multi-agents/agents/小李飞刀/小李飞刀.prompt.md`、根 `AGENTS.md`、`agents/standard/任务记录约定.md`、`agents/standard/实现文件规范.md`。
- 已读主仓只读计划书 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/arch_parallelize_package_func_pattern_refactor_green_plan.md`，核对 S1-S5：包结构迁移、FuncOp pattern 化、spec/test 同步、只读合同验收与敏感目录门禁、任务记录同批。
- 已核对 TODO：本任务 `T-20260524-53daf9ec` 为小李飞刀 execute/进行中；并发 `T-20260524-93f9f2ca` 只涉及 `codex-multi-agents` 脚本/提示词/标准/spec/test，与本任务 `kernel_gen/passes/registry.py`、`kernel_gen/pipeline/npu_demo_lowering.py`、`test/passes/**` 面无路径交集。
- 已核对 worktree：`/home/lfr/kernelcode_generate/wt-20260524-arch-parallelize-package-func-pattern-refactor`，branch=`task/arch-parallelize-package-func-pattern-refactor`，`HEAD=origin/main=7cba6cf66f7966e24949a141dd6f30c15a9f8bc2`，`HEAD...origin/main=0/0`。
改动：
- 已在任务 worktree 内迁移 `kernel_gen/passes/arch_parallelize.py` 到 `kernel_gen/passes/arch_parallelize/arch_parallelize.py`，新增 package root `kernel_gen/passes/arch_parallelize/__init__.py`。
- 已新增公开 `_ArchParallelizeFuncPattern(block_num: int)`，仅通过 `kernel_gen.passes.arch_parallelize` package root 暴露；未加入 `kernel_gen.passes` 顶层 re-export。
- `ArchParallelizePass.apply(...)` 已改为校验后通过 `PatternRewriteWalker(GreedyRewritePatternApplier(..., dce_enabled=False), apply_recursively=False)` 驱动 pattern；loop 替换使用 `PatternRewriter.replace_op(...)`，避免绕过 xDSL worklist。
- 已同步 `spec/pass/arch_parallelize.md`、`kernel_gen/passes/__init__.py` 文件级说明、`test/passes/test_arch_parallelize.py`、`test/passes/test_pattern_public_api_docs.py`、`test/passes/test_registry.py`。
- 启动时曾误将同类补丁落到主仓 `/home/lfr/kernelcode_generate` 的 `kernel_gen/passes/arch_parallelize*` 与 `kernel_gen/passes/__init__.py` 路径；已仅对这些误改路径执行反向补丁和删除我新建的未跟踪目录，复核主仓对应路径 `git status --short -- kernel_gen/passes/__init__.py kernel_gen/passes/arch_parallelize.py kernel_gen/passes/arch_parallelize` 为空，未继续在主仓写任务 diff。
最小功能闭环：
- package shape：旧单文件退场，新 package root 与内部实现文件存在。
- public import：`kernel_gen.passes.arch_parallelize.__all__ == ["ArchParallelizePass", "_ArchParallelizeFuncPattern"]`；`ArchParallelizePass.__module__` 与 `_ArchParallelizeFuncPattern.__module__` 均为 `kernel_gen.passes.arch_parallelize`。
- pattern driver：公开 pattern root 为 `func.FuncOp`，`match_and_rewrite(op: func.FuncOp, rewriter: PatternRewriter) -> None`；pass apply 使用 xDSL pattern walker。
验证：
- `python3 -m py_compile kernel_gen/passes/arch_parallelize/arch_parallelize.py kernel_gen/passes/arch_parallelize/__init__.py test/passes/test_arch_parallelize.py test/passes/test_pattern_public_api_docs.py test/passes/test_registry.py`：exit=0。
- `pytest -q test/passes/test_pattern_public_api_docs.py`：exit=0，`4 passed`，锁定 public module / implementation module 分离、pattern API 列表和文档 token。
- `pytest -q test/passes/test_registry.py -k arch_parallelize`：exit=0，`1 passed, 57 deselected`，锁定 registry 构造与 canonical module path。
- `pytest -q test/passes/test_arch_parallelize.py`：初跑暴露 walker worklist 未同步旧 loop detach；修为 `PatternRewriter.replace_op(...)` 后 exit=0，`21 passed`。
- `pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k arch_parallelize`：初跑同上，修复后 exit=0，`3 passed, 7 deselected`。
Diff 反推自测：
- 实际改动 `kernel_gen/passes/arch_parallelize/**`：反推 `test/passes/test_arch_parallelize.py`、`test/passes/pipeline/test_npu_demo_lowering.py -k arch_parallelize`、py_compile。
- 实际改动 `kernel_gen/passes/__init__.py`、package root import：反推 `test/passes/test_arch_parallelize.py` package shape case、`test/passes/test_registry.py -k arch_parallelize`。
- 实际改动 `test/passes/test_pattern_public_api_docs.py` 与 `spec/pass/arch_parallelize.md`：反推 `pytest -q test/passes/test_pattern_public_api_docs.py`。
自检：
- 目前未修改 `expectation/`、`.skills/`、`agents/standard/`；最终仍需跑敏感目录门禁。
- 新增公开 `_ArchParallelizeFuncPattern` 有计划书用户确认来源；未新增其它公开 API、registry option 或稳定错误文本。
- 跨文件调用只走公开 API；实现未新增 ctx 能力探测；当前文件内新增 helper / pattern 均有功能说明与使用示例。
- 还需继续执行 compileall、只读 expectation 合同验收、pipeline expectation 既有失败隔离、静态扫描、`git diff --check` 和最终任务记录补齐。
结论：实现与核心 diff pytest 已初步闭合，继续补全计划验收与门禁。

时间：2026-05-24 15:16 +0800
经办人：小李飞刀
任务：T-20260524-53daf9ec / arch-parallelize-package-func-pattern-refactor / execute
任务目标：完成计划级 execute 的规格、实现、测试和只读合同验收闭环，准备流转 review。
改动摘要：
- 功能实现：删除旧路径 `kernel_gen/passes/arch_parallelize.py`，新增 `kernel_gen/passes/arch_parallelize/__init__.py` 与 `kernel_gen/passes/arch_parallelize/arch_parallelize.py`；package root 公开 `ArchParallelizePass` 与 `_ArchParallelizeFuncPattern`，并规范化二者 `__module__` 为 `kernel_gen.passes.arch_parallelize`。
- Pattern 化：新增 `_ArchParallelizeFuncPattern(block_num: int)`，`match_and_rewrite(op: func.FuncOp, rewriter: PatternRewriter) -> None`；`ArchParallelizePass.apply(...)` 使用 `PatternRewriteWalker` / `GreedyRewritePatternApplier` 驱动，`apply_recursively=False` 限定为 module 顶层 FuncOp root；loop 替换使用 `PatternRewriter.replace_op(...)` 同步 xDSL worklist。
- spec：`spec/pass/arch_parallelize.md` 增加 `_ArchParallelizeFuncPattern` API、参数说明、package root canonical public path、内部实现路径非外部 caller path、IR before/after 与 no-loop `scf.if` 合同说明。
- pytest：`test/passes/test_arch_parallelize.py` 新增 package shape、顶层不 re-export、pattern AST gate；`test/passes/test_pattern_public_api_docs.py` 支持 public module / implementation module 分离并锁定 `_ArchParallelizeFuncPattern` token；`test/passes/test_registry.py` 补 registry 构造返回 class identity 与 package `__all__`。
- 任务记录：新增本记录，和实现/spec/test 同批进入候选 diff。
候选 diff 文件列表：
- `kernel_gen/passes/__init__.py`
- `kernel_gen/passes/arch_parallelize.py`（删除）
- `kernel_gen/passes/arch_parallelize/__init__.py`（新增）
- `kernel_gen/passes/arch_parallelize/arch_parallelize.py`（新增）
- `spec/pass/arch_parallelize.md`
- `test/passes/test_arch_parallelize.py`
- `test/passes/test_pattern_public_api_docs.py`
- `test/passes/test_registry.py`
- `agents/codex-multi-agents/log/task_records/2026/24/20260524-arch-parallelize-package-func-pattern-refactor.md`
验证：
- `python3 -m py_compile kernel_gen/passes/arch_parallelize/arch_parallelize.py kernel_gen/passes/arch_parallelize/__init__.py test/passes/test_arch_parallelize.py test/passes/test_pattern_public_api_docs.py test/passes/test_registry.py`：exit=0。
- `python3 -m compileall -q kernel_gen/passes/arch_parallelize kernel_gen/passes/__init__.py kernel_gen/passes/registry.py kernel_gen/pipeline/npu_demo_lowering.py test/passes/test_arch_parallelize.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_pattern_public_api_docs.py`：exit=0，覆盖新 package、旧公开 re-export、registry、pipeline 与相关测试文件。
- `python3 - <<'PY' ... package/import proof ... PY`：exit=0，证明旧 `kernel_gen/passes/arch_parallelize.py` 不存在；新 `__init__.py` / `arch_parallelize.py` 存在；`kernel_gen.passes.arch_parallelize.__file__` 指向任务 worktree package root；package `__all__ == ["ArchParallelizePass", "_ArchParallelizeFuncPattern"]`；顶层 `kernel_gen.passes` 不含 `_ArchParallelizeFuncPattern`；registry 构造对象 class 与 package root `ArchParallelizePass` 为同一对象。
- `python3 - <<'PY' ... static boundary scan ... PY`：exit=0，证明 `registry.py` / `npu_demo_lowering.py` / `kernel_gen/passes/__init__.py` / 公开测试不直接 import 内部实现模块；实现中无 `hasattr(ctx` / `getattr(ctx` / `callable(getattr(ctx`；无非装饰器嵌套函数。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-arch-parallelize-package-func-pattern-refactor:/home/lfr/kernelcode_generate python3 - <<'PY' ... import proof ... PY`：exit=0，证明 `expectation.pass.arch_parallelize.__main__` 来自主仓 `/home/lfr/kernelcode_generate/expectation/pass/arch_parallelize/__main__.py`，`kernel_gen.passes.arch_parallelize` 来自任务 worktree `/home/lfr/kernelcode_generate/wt-20260524-arch-parallelize-package-func-pattern-refactor/kernel_gen/passes/arch_parallelize/__init__.py`。
- `pytest -q test/passes/test_arch_parallelize.py`：exit=0，`21 passed`，覆盖行为回归、package shape、public pattern API 和 AST gate。
- `pytest -q test/passes/test_registry.py -k arch_parallelize`：exit=0，`1 passed, 57 deselected`，覆盖 registry 构造与 canonical module path。
- `pytest -q test/passes/pipeline/test_npu_demo_lowering.py -k arch_parallelize`：exit=0，`3 passed, 7 deselected`，覆盖 pipeline 中 arch-parallelize 行为。
- `pytest -q test/passes/test_pattern_public_api_docs.py`：exit=0，`4 passed`，覆盖 spec / 实现 doc / API 列表 / token 合同。
- `pytest -q test/passes/test_arch_parallelize.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_pattern_public_api_docs.py`：exit=0，`93 passed`，完整关联 pytest 文件组合通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-arch-parallelize-package-func-pattern-refactor:/home/lfr/kernelcode_generate python3 -m expectation.pass.arch_parallelize`：exit=0；输出 4 个 arch_parallelize case 均通过，合同真源为主仓只读 expectation。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-arch-parallelize-package-func-pattern-refactor:/home/lfr/kernelcode_generate python3 -m expectation.pass.pipeline.npu_demo_lowering`：exit=1；失败为计划标注的 latest-main 既有 pipeline order 合同红灯：actual 含 `dma-alias-to-reinterpret`、`kernel-pattern-attach`、`transform-apply`，expected 仍含旧 `lower-dma-memory-hierarchy`，失败 case 为 `pass-pipeline-npu_demo_lowering-order-1`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate python3 -m expectation.pass.pipeline.npu_demo_lowering`：exit=1；主仓同命令同签名失败，证明该红灯非本候选 diff 新增，不作为本计划通过项或阻断项。
- `git diff --check`：exit=0。
- `git diff --name-only -- expectation .skills agents/standard`：exit=0，空输出。
- `git diff --cached --name-only -- expectation .skills agents/standard`：exit=0，空输出。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`：exit=0，空输出。
- `test ! -f kernel_gen/passes/arch_parallelize.py && test -f kernel_gen/passes/arch_parallelize/__init__.py && test -f kernel_gen/passes/arch_parallelize/arch_parallelize.py`：exit=0。
- `rg -n "from kernel_gen\\.passes\\.arch_parallelize\\.arch_parallelize|import kernel_gen\\.passes\\.arch_parallelize\\.arch_parallelize" kernel_gen spec test || true`：exit=0，空输出。
- `rg -n "hasattr\\(ctx|getattr\\(ctx|callable\\(getattr\\(ctx" kernel_gen/passes/arch_parallelize || true`：exit=0，空输出。
- `python3 - <<'PY' ... nested def scan ... PY`：exit=0，`nested def scan ok`。
Diff 反推自测：
- `kernel_gen/passes/arch_parallelize/**`：通过 `test/passes/test_arch_parallelize.py`、`test/passes/pipeline/test_npu_demo_lowering.py -k arch_parallelize`、compileall、主仓只读 `expectation.pass.arch_parallelize` 验证行为、pipeline 接入与合同不回退。
- `kernel_gen/passes/__init__.py`：通过 package/import proof、`test/passes/test_arch_parallelize.py` package shape case、`test/passes/test_registry.py -k arch_parallelize` 验证顶层仍只 re-export `ArchParallelizePass` 且不暴露 `_ArchParallelizeFuncPattern`。
- `spec/pass/arch_parallelize.md`：通过 `test/passes/test_pattern_public_api_docs.py` 验证 API 列表、实现 doc 与 spec 文档 token 对齐。
- `test/passes/test_arch_parallelize.py`、`test/passes/test_pattern_public_api_docs.py`、`test/passes/test_registry.py`：通过完整关联 pytest 文件组合验证新增测试自身有效并与既有测试兼容。
自检：
- 接口：仅新增用户确认的公开 `_ArchParallelizeFuncPattern(block_num: int)`；未新增 pass 名、registry option、pattern getter或 `kernel_gen.passes` 顶层 re-export；`ArchParallelizePass` 签名与稳定错误文本保持不变。
- 边界：package root 为 canonical public path；内部实现模块只作为实现源码承载，公开测试不作为外部 caller 直连内部路径。
- 异常：target / parallel_level / block_num / loop 结构失败仍走原稳定错误；verify 失败仍包装 `ArchParallelizePassVerifierError`。
- 兼容性：`from kernel_gen.passes import ArchParallelizePass`、`from kernel_gen.passes.arch_parallelize import ArchParallelizePass`、registry 构造均保持。
- 实现遗漏：计划 S1-S5 已覆盖；pipeline expectation 只按计划做既有失败隔离，未越权修改 expectation。
- 冗余与复用：删除旧 `_iter_non_declaration_funcs` 遍历 helper，避免与 pattern walker 重复；未新增无意义 wrapper。
- 注释准确性：新增 package root与 pattern class / method 均补功能说明、API 列表或使用示例；spec 对 `scf.if` 说明限定为 no-loop 边界，不把 loop 改写误写成必然含 `scf.if`。
- 函数粒度：保留现有当前文件内 helper；跨文件只调用公开 API；未使用 ctx 能力探测；无非装饰器嵌套函数。
- 输入输出校验：`block_num` 仍在 `ArchParallelizePass.apply(...)` 通过 target registry 校验为正整数；pattern 不新增独立错误文本。
- 资源 / 并发 / 性能：pattern walker 限定 `apply_recursively=False`，避免递归遍历被本 pattern 替换的 loop body；loop 替换走 xDSL rewriter，worklist 与 IR 生命周期一致。
- 测试有效性：初跑 pytest 捕获了绕过 rewriter 的 detached loop 问题，修复后相关行为测试通过，说明新增/既有测试能发现真实回归。
结论：execute 已完成。候选 diff 不包含 `expectation/`、`.skills/`、`agents/standard/`；`expectation.pass.arch_parallelize` 只读必过合同通过；`expectation.pass.pipeline.npu_demo_lowering` 为主仓同签名既有失败隔离项。按流程流转 review。

时间：2026-05-24 15:28 +0800
经办人：提莫炖蘑菇
任务：T-20260524-53daf9ec / arch-parallelize-package-func-pattern-refactor / review
任务目标：审查 `arch-parallelize` package 化与公开 `_ArchParallelizeFuncPattern(block_num: int)` FuncOp root pattern 重构，核对公开 API、package/import matrix、spec/test、Diff 反推自测、只读 `expectation.pass.arch_parallelize` 合同验收、pipeline expectation 既有失败隔离和敏感目录门禁。
最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260524-arch-parallelize-package-func-pattern-refactor`
- review 前执行 `git fetch origin`；初始 `HEAD=7cba6cf66f7966e24949a141dd6f30c15a9f8bc2`，`origin/main=d8930c7663c87ea9ed1286b3e21a3413fa270c70`，`merge-base=7cba6cf66f7966e24949a141dd6f30c15a9f8bc2`。
- `git diff --name-only HEAD..origin/main` 仅命中 agents 标准/提示词、codex-multi-agents 脚本/spec/test 与另一任务记录；与本任务候选 diff 的 `kernel_gen/passes/arch_parallelize*`、`spec/pass/arch_parallelize.md`、`test/passes/*`、本任务记录无路径重叠。
- 已执行 `git merge --no-edit origin/main`，fast-forward 到 `d8930c7663c87ea9ed1286b3e21a3413fa270c70`，未覆盖任务 diff。
审查范围：
- 主仓只读计划书：`/home/lfr/kernelcode_generate/ARCHITECTURE/plan/arch_parallelize_package_func_pattern_refactor_green_plan.md`。
- 被审 diff：`kernel_gen/passes/__init__.py`、删除 `kernel_gen/passes/arch_parallelize.py`、新增 `kernel_gen/passes/arch_parallelize/__init__.py`、新增 `kernel_gen/passes/arch_parallelize/arch_parallelize.py`、`spec/pass/arch_parallelize.md`、`test/passes/test_arch_parallelize.py`、`test/passes/test_pattern_public_api_docs.py`、`test/passes/test_registry.py`、本任务记录。
- 执行记录核对：执行人已写执行前阅读、最小功能闭环、自检、Diff 反推自测、只读合同验收、pipeline 既有失败隔离和敏感目录门禁。
真实审查：
- 公开 API：新增 `_ArchParallelizeFuncPattern(block_num: int)` 已在计划书用户决策记录中明确确认；`ArchParallelizePass(target: str = "npu_demo", parallel_level: str = "block")`、`from_options`、`apply`、pass name、registry option 和稳定错误文本未扩大。
- package/import matrix：旧 `kernel_gen/passes/arch_parallelize.py` 已删除；`kernel_gen.passes.arch_parallelize` package root `__all__ == ["ArchParallelizePass", "_ArchParallelizeFuncPattern"]`；`kernel_gen.passes` 顶层未 re-export `_ArchParallelizeFuncPattern`；`ArchParallelizePass.__module__` 与 `_ArchParallelizeFuncPattern.__module__` 均为 `kernel_gen.passes.arch_parallelize`。
- 实现边界：`_ArchParallelizeFuncPattern.match_and_rewrite(op: func.FuncOp, rewriter: PatternRewriter) -> None` 以 `func.FuncOp` 为 root，`ArchParallelizePass.apply(...)` 只做 module / target / option 校验并通过 `PatternRewriteWalker` 驱动；新增 helper 均在同一实现文件内，未发现跨文件非公开 API 使用。
- 测试边界：公开行为测试通过 package root、顶层公开 re-export 或 registry 观察行为；内部实现路径只用于计划允许的文档/source gate，不作为外部 caller 公开入口。
- 只读合同：`expectation.pass.arch_parallelize` 使用主仓 expectation 入口与任务 worktree `kernel_gen` 导入边界，退出码 0；未修改 expectation。
- pipeline expectation：`expectation.pass.pipeline.npu_demo_lowering` 在候选与主仓同样 exit=1，失败 case 与 actual/expected pipeline order 签名一致，符合计划中 latest-main 既有失败隔离口径，不作为本任务阻断或通过项。
Diff 反推审查：
- `kernel_gen/passes/arch_parallelize/**`：复跑 `test/passes/test_arch_parallelize.py`、关联 pipeline pytest、compileall 与 `expectation.pass.arch_parallelize`，覆盖 package 化、pattern walker、loop rewrite、block0 guard 与合同不回退。
- `kernel_gen/passes/__init__.py`：通过 import proof、`test_arch_parallelize` package shape case 与 `test_registry.py` registry case 验证顶层只保持 `ArchParallelizePass` 公开，不暴露 `_ArchParallelizeFuncPattern`。
- `spec/pass/arch_parallelize.md` 与 `test/passes/test_pattern_public_api_docs.py`：复跑 public API docs pytest，覆盖 API 列表、实现文件说明、class docstring IR token 与 public/implementation module 分离。
- `test/passes/test_registry.py`：复跑关联组合 pytest，覆盖 registry 构造返回 class identity 与 canonical module path。
验证：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile kernel_gen/passes/arch_parallelize/arch_parallelize.py kernel_gen/passes/arch_parallelize/__init__.py test/passes/test_arch_parallelize.py test/passes/test_pattern_public_api_docs.py test/passes/test_registry.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 python3 -m compileall -q kernel_gen/passes/arch_parallelize kernel_gen/passes/__init__.py kernel_gen/passes/registry.py kernel_gen/pipeline/npu_demo_lowering.py test/passes/test_arch_parallelize.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_pattern_public_api_docs.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_arch_parallelize.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_pattern_public_api_docs.py`：exit=0，`93 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-arch-parallelize-package-func-pattern-refactor:/home/lfr/kernelcode_generate python3 -m expectation.pass.arch_parallelize`：exit=0，4 个 arch_parallelize case 输出通过。
- import proof 脚本：exit=0；`expectation.pass.arch_parallelize.__main__` 来自主仓 `/home/lfr/kernelcode_generate/expectation/pass/arch_parallelize/__main__.py`，`kernel_gen.passes.arch_parallelize` 来自任务 worktree package root，旧单文件不存在，新实现文件存在。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-arch-parallelize-package-func-pattern-refactor:/home/lfr/kernelcode_generate python3 -m expectation.pass.pipeline.npu_demo_lowering`：exit=1，同签名 pipeline order 既有失败。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate python3 -m expectation.pass.pipeline.npu_demo_lowering`：exit=1，同签名 pipeline order 既有失败。
- `git diff --check && git diff --cached --check`：exit=0。
- `git diff --name-only -- expectation .skills agents/standard`：exit=0，空输出。
- `git diff --cached --name-only -- expectation .skills agents/standard`：exit=0，空输出。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`：exit=0，空输出。
- 静态边界核验：实现文件 AST gate 通过，未发现实现侧跨文件私有 import、ctx/context 能力探测、`callable(getattr(...))`、非装饰器嵌套函数或 `object` 签名；`rg` 未发现 `from/import kernel_gen.passes.arch_parallelize.arch_parallelize` 或 `kernel_gen.passes._ArchParallelizeFuncPattern` 公开误用。
findings：
- 无阻断项。
残余风险：
- `test/passes/test_registry.py` 全文件宽扫存在历史嵌套函数命中，但该命中不在本任务改动 hunk；本轮按候选 diff 与新增实现文件核验，未发现新增非装饰器嵌套函数。
- `expectation.pass.pipeline.npu_demo_lowering` 仍为主仓同签名旧 pipeline order 红灯；计划已定义为既有失败隔离项，非本任务阻断。
自检：
- 已读取个人提示词、根 `AGENTS.md`、`agents/standard/*.md`、主仓只读计划书、任务记录和实际 diff。
- 已同步 latest main 并确认无覆盖任务 diff 风险。
- 已按实际 diff 反推复跑 pytest / py_compile / compileall / 只读 expectation / 静态扫描 / 敏感目录门禁。
- 已核对公开 API 用户确认、跨文件非公开 API、测试直连非 API、ctx 能力探测、`object` 签名、嵌套函数和 `expectation/.skills/agents/standard` 禁止修改面。
结论：通过。该任务为计划级 execute 落地后的 review，按当前角色提示词应进入 `archive_acceptance / 计划书入档验收` 或由管理员接续该阶段，不得直接进入 merge。

时间：2026-05-24 15:39 +0800
经办人：不要啊教练
任务：T-20260524-53daf9ec / arch-parallelize-package-func-pattern-refactor / archive_acceptance
任务目标：核对 arch-parallelize package 化与公开 `_ArchParallelizeFuncPattern(block_num: int)` 计划级任务记录、只读 `expectation.pass.arch_parallelize` 合同验收、pipeline expectation 既有失败隔离、敏感目录空 diff 与可归档性。
最新同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260524-arch-parallelize-package-func-pattern-refactor`
- `git fetch origin --prune` 后：`HEAD=d8930c7663c87ea9ed1286b3e21a3413fa270c70`，`origin/main=d8930c7663c87ea9ed1286b3e21a3413fa270c70`，`merge-base=d8930c7663c87ea9ed1286b3e21a3413fa270c70`，`HEAD...origin/main=0/0`。
- 任务 worktree 内计划书缺失；本轮按任务说明只读引用主仓计划书 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/arch_parallelize_package_func_pattern_refactor_green_plan.md`，`sha256=c92d1ce488eefa04bc7fed50e3f29254aacdbb5b71dcd489752a6cb2dac68d61`。
审查范围：
- 候选 tracked diff：`kernel_gen/passes/__init__.py`、删除 `kernel_gen/passes/arch_parallelize.py`、`spec/pass/arch_parallelize.md`、`test/passes/test_arch_parallelize.py`、`test/passes/test_pattern_public_api_docs.py`、`test/passes/test_registry.py`。
- 候选 untracked：`kernel_gen/passes/arch_parallelize/__init__.py`、`kernel_gen/passes/arch_parallelize/arch_parallelize.py`、本任务记录。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`ARCHITECTURE/plan/`、`TODO.md`、`DONE.md`、缓存与其它 worktree 不纳入候选范围。
任务记录闭环核对：
- execute 记录包含执行前阅读、最小功能闭环、候选 diff 文件列表、Diff 反推自测、自检、主仓只读 `expectation.pass.arch_parallelize` 合同验收、`expectation.pass.pipeline.npu_demo_lowering` 既有失败隔离和敏感目录门禁。
- review 记录包含最新同步现场、真实审查、Diff 反推审查、验证命令、findings、自检和结论；结论为通过并进入 `archive_acceptance / 计划书入档验收`，未直接进入 merge。
真实入档验收：
- 计划 S1/S2/S3：旧单文件 `kernel_gen/passes/arch_parallelize.py` 已删除；新 package root 与内部实现文件存在；`kernel_gen.passes.arch_parallelize.__all__ == ["ArchParallelizePass", "_ArchParallelizeFuncPattern"]`；`ArchParallelizePass.__module__` 与 `_ArchParallelizeFuncPattern.__module__` 均为 `kernel_gen.passes.arch_parallelize`；`kernel_gen.passes` 顶层未导出 `_ArchParallelizeFuncPattern`。
- 公开 API：新增 `_ArchParallelizeFuncPattern(block_num: int)` 有计划用户确认来源；`ArchParallelizePass(target: str = "npu_demo", parallel_level: str = "block")`、`from_options`、`apply`、pass name、registry option 和稳定错误文本未扩大。
- 实现边界：`_ArchParallelizeFuncPattern.match_and_rewrite(op: func.FuncOp, rewriter: PatternRewriter) -> None` 为 FuncOp root pattern；`ArchParallelizePass.apply(...)` 通过 `PatternRewriteWalker` 驱动；未发现新增跨文件非公开 API、ctx 能力探测、`object` 签名或非装饰器嵌套函数。
- 测试边界：公开行为通过 package root、顶层公开 re-export 或 registry 观察；内部实现模块仅用于计划允许的 source/doc gate，不作为外部 caller import 示例。
Diff 反推审查：
- `kernel_gen/passes/arch_parallelize/**` 与旧文件删除：复跑 compileall、关联 pytest 和主仓只读 `expectation.pass.arch_parallelize`，覆盖 package shape、pattern walker、loop rewrite、block0 guard 与合同不回退。
- `kernel_gen/passes/__init__.py`：通过 import proof 与关联 pytest 验证顶层只保留 `ArchParallelizePass`，不暴露 `_ArchParallelizeFuncPattern`。
- `spec/pass/arch_parallelize.md` 与 `test/passes/test_pattern_public_api_docs.py`：关联 pytest 覆盖 API 列表、spec token、实现 doc 和 public/implementation module 分离。
- `test/passes/test_arch_parallelize.py`、`test/passes/test_registry.py`：关联 pytest 覆盖 package public API shape、AST gate、registry 构造与 canonical module path。
验证：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m compileall -q kernel_gen/passes/arch_parallelize kernel_gen/passes/__init__.py kernel_gen/passes/registry.py kernel_gen/pipeline/npu_demo_lowering.py test/passes/test_arch_parallelize.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_pattern_public_api_docs.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_arch_parallelize.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_pattern_public_api_docs.py`：exit=0，`93 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-arch-parallelize-package-func-pattern-refactor:/home/lfr/kernelcode_generate python3 -m expectation.pass.arch_parallelize`：exit=0，4 个 arch_parallelize case 均通过；合同真源为主仓只读 expectation。
- import proof：exit=0；`expectation.pass.arch_parallelize.__main__` 来自主仓 `/home/lfr/kernelcode_generate/expectation/pass/arch_parallelize/__main__.py`；`kernel_gen.passes.arch_parallelize` 来自任务 worktree package root；旧单文件不存在，新实现文件存在；顶层不导出 `_ArchParallelizeFuncPattern`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-arch-parallelize-package-func-pattern-refactor:/home/lfr/kernelcode_generate python3 -m expectation.pass.pipeline.npu_demo_lowering`：exit=1。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate python3 -m expectation.pass.pipeline.npu_demo_lowering`：exit=1。
- pipeline expectation 候选与主仓失败签名一致：`pass-pipeline-npu_demo_lowering-order-1`，actual 含 `dma-alias-to-reinterpret`、`kernel-pattern-attach`、`transform-apply`，expected 仍含旧 `lower-dma-memory-hierarchy`；按计划作为 latest-main 既有失败隔离项，不作为本任务阻断或通过项。
- 候选范围脚本：tracked/untracked 文件列表与预期完全一致，且不含 `expectation/`、`.skills/`、`agents/standard/`、`ARCHITECTURE/plan/`、`TODO.md`、`DONE.md`。
- `git diff --check`：exit=0。
- `git diff --cached --check`：exit=0。
- `git diff --name-only -- expectation .skills agents/standard`：exit=0，空输出。
- `git diff --cached --name-only -- expectation .skills agents/standard`：exit=0，空输出。
- `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard`：exit=0，空输出。
- 静态扫描：新增实现文件 AST 非装饰器嵌套函数扫描通过；`rg` 未命中 `hasattr(ctx`、`getattr(ctx`、`callable(getattr(ctx`、`: object` / `-> object`、内部实现模块公开导入或 `kernel_gen.passes._ArchParallelizeFuncPattern` 误用。
findings：
- 无阻断项。
可归档性与 merge 前交接：
- 可进入 merge 的候选范围仅限上述实现/spec/test/任务记录文件；merge 需把 untracked 新 package 文件与任务记录同批纳入。
- 不得纳入 ignored `__pycache__` / `.pytest_cache`、`expectation/`、`.skills/`、`agents/standard/`、主仓计划书、`TODO.md`、`DONE.md` 或其它 worktree 状态文件。
- `expectation.pass.pipeline.npu_demo_lowering` 的 exit=1 只能按计划记录为 latest-main 同签名既有失败隔离项；merge 不得修改或合入 expectation。
自检：
- 已重新读取角色提示词、根 `AGENTS.md` 与相关标准；已基于 latest `origin/main` 核对当前任务 worktree。
- 已读取主仓只读计划书、任务记录和实际 diff；已按计划 S1-S5 核对任务记录闭环、合同验收、pipeline 隔离、敏感目录空 diff 和可归档性。
- 已复跑 Diff 反推 pytest、compileall、主仓只读 expectation、pipeline 隔离命令、diff check、敏感目录门禁和静态扫描。
- 未修改实现、spec、测试、计划书、`expectation/`、`.skills/`、`agents/standard/` 或任务状态文件；本次只追加 archive_acceptance 记录。
结论：通过。`T-20260524-53daf9ec` archive_acceptance / 计划书入档验收已闭合，可按 `execute -> review -> archive_acceptance -> merge` 流转到 merge；不直接合并。

时间：2026-05-24 15:44 CST
经办人：李白
任务：T-20260524-53daf9ec / arch-parallelize-package-func-pattern-refactor / merge
任务目标：合入已通过 `archive_acceptance / 计划书入档验收` 的 arch-parallelize package 化、公开 `_ArchParallelizeFuncPattern(block_num: int)`、spec/test 与任务记录；不纳入 `expectation/`、`.skills/`、`agents/standard/`、主仓计划书、`TODO.md`、`DONE.md`、cache 或其它 worktree。
合并前阅读与同步：
- 已重新读取主仓 `AGENTS.md`、`agents/codex-multi-agents/agents/李白/李白.prompt.md`、`agents/standard/合并规范.md`、本 worktree `agents/standard/任务记录约定.md` 与 `agents/standard/expectation任务规则.md`。
- 已读取本任务 execute、review、archive_acceptance 记录；archive_acceptance 结论为通过，最小阻断项无。
- `git fetch --prune origin` 后主仓 `/home/lfr/kernelcode_generate` 为 `HEAD=origin/main=d8930c7663c87ea9ed1286b3e21a3413fa270c70`，任务 worktree `/home/lfr/kernelcode_generate/wt-20260524-arch-parallelize-package-func-pattern-refactor` 为 `HEAD=origin/main=merge-base=d8930c7663c87ea9ed1286b3e21a3413fa270c70`。
- 计划书只读引用主仓 `ARCHITECTURE/plan/arch_parallelize_package_func_pattern_refactor_green_plan.md`，sha256=`c92d1ce488eefa04bc7fed50e3f29254aacdbb5b71dcd489752a6cb2dac68d61`；本轮不合入计划书。
候选范围：
- tracked：`kernel_gen/passes/__init__.py`、删除 `kernel_gen/passes/arch_parallelize.py`、`spec/pass/arch_parallelize.md`、`test/passes/test_arch_parallelize.py`、`test/passes/test_pattern_public_api_docs.py`、`test/passes/test_registry.py`。
- untracked 必须同批纳入：`kernel_gen/passes/arch_parallelize/__init__.py`、`kernel_gen/passes/arch_parallelize/arch_parallelize.py`、`agents/codex-multi-agents/log/task_records/2026/24/20260524-arch-parallelize-package-func-pattern-refactor.md`。
- 禁止范围核对：`git diff --name-only -- expectation .skills agents/standard ARCHITECTURE/plan TODO.md DONE.md` 与 cached 同命令均为空；`git status --short --ignored --untracked-files=all -- expectation .skills agents/standard ARCHITECTURE/plan TODO.md DONE.md` 为空。
验证：
- `PYTHONDONTWRITEBYTECODE=1 python3 -m compileall -q kernel_gen/passes/arch_parallelize kernel_gen/passes/__init__.py kernel_gen/passes/registry.py kernel_gen/pipeline/npu_demo_lowering.py test/passes/test_arch_parallelize.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_pattern_public_api_docs.py`：exit=0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_arch_parallelize.py test/passes/test_registry.py test/passes/pipeline/test_npu_demo_lowering.py test/passes/test_pattern_public_api_docs.py`：exit=0，`93 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-arch-parallelize-package-func-pattern-refactor:/home/lfr/kernelcode_generate python3 -m expectation.pass.arch_parallelize`：exit=0，4 个 arch_parallelize case 均通过；合同真源为主仓只读 `expectation/`。
- import proof：前两次手写验证脚本分别因 Python `pass` 关键字导入写法和误用不存在的 `registry.create_pass` 失败，均为验证脚本错误，非候选代码失败；纠正为 `importlib.import_module(...)` 与公开 `registry.build_registered_pass(...)` 后 exit=0，输出 `import proof ok`，确认 expectation 入口来自主仓、`kernel_gen.passes.arch_parallelize` 来自任务 worktree package root、旧单文件不存在、package `__all__` 为 `["ArchParallelizePass", "_ArchParallelizeFuncPattern"]`、顶层 `kernel_gen.passes` 不导出 `_ArchParallelizeFuncPattern`、registry 构造返回 package root `ArchParallelizePass`。
- `test ! -f kernel_gen/passes/arch_parallelize.py && test -f kernel_gen/passes/arch_parallelize/__init__.py && test -f kernel_gen/passes/arch_parallelize/arch_parallelize.py`：exit=0，输出 `package-shape-ok`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260524-arch-parallelize-package-func-pattern-refactor:/home/lfr/kernelcode_generate python3 -m expectation.pass.pipeline.npu_demo_lowering`：exit=1。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate python3 -m expectation.pass.pipeline.npu_demo_lowering`：exit=1。
- pipeline expectation 候选与主仓失败签名一致：`pass-pipeline-npu_demo_lowering-order-1`，actual 含 `dma-alias-to-reinterpret`、`kernel-pattern-attach`、`transform-apply`，expected 仍含旧 `lower-dma-memory-hierarchy`；按计划与 archive_acceptance 记录作为 latest-main 既有失败隔离项，不作为本任务阻断或通过项，不修改 expectation。
- `python3` AST 嵌套函数扫描：exit=0，输出 `nested def scan ok`。
- `rg` 静态边界扫描未命中 `hasattr(ctx`、`getattr(ctx`、`callable(getattr(ctx`、`: object` / `-> object`、内部实现模块公开导入或 `kernel_gen.passes._ArchParallelizeFuncPattern` 误用。
- `git diff --check && git diff --cached --check`：exit=0。
- 运行验证产生的 `.pytest_cache` / `__pycache__` 已清理，清理后 `git status --short --branch --untracked-files=all` 仍只显示本任务允许候选文件。
冲突处理：无冲突；latest main 已在 review/archive_acceptance 阶段同步，本次 merge 前再次确认主仓与任务 worktree 同基线。
敏感文件核对：未修改、未 stage、未合入 `expectation/`、`.skills/`、`agents/standard/`、`ARCHITECTURE/plan/`、`TODO.md`、`DONE.md` 或 cache；`expectation.pass.arch_parallelize` 只读运行并单列为合同验收。
剩余风险：`expectation.pass.pipeline.npu_demo_lowering` 仍为主仓同签名既有 pipeline order 红灯，按计划记录为隔离项，不写作通过，不作为本轮阻断。
结论：merge 前核对通过；下一步仅按上述允许范围 stage、提交，快进合入主仓，push 后执行 `-done` 并清理完成 worktree/branch。
