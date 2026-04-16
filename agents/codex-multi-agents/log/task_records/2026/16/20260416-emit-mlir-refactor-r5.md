时间：2026-04-16 22:55 +0800
经办人：小李飞刀
任务：T-20260416-8680d55f
任务目标：修复 `expectation/utils/compare.py` 对已删除 `kernel_gen.dsl.emit_mlir` 的断链依赖，并将 `spec/dsl/mlir_gen.md` 的公开合同收口为 `kernel_gen.dsl.mlir_gen.emit` 唯一入口
改动：
- 按当前 [`TODO.md`](../../../../../../TODO.md) 补建 `worktree=/home/lfr/kernelcode_generate/wt-20260416-emit-mlir-refactor-r5`，直接从 `origin/main` 创建 `T-20260416-8680d55f`，避免在落后本地 `main` 的旧基线上复现。
- 新增 [`expectation/utils/compare.py`](../../../../../../expectation/utils/compare.py)，恢复旧的 expectation 比较 helper 入口 `assert_static_symbol_int(...)`、`assert_dynamic_symbol_int(...)`、`assert_memory(...)`，但内部不再依赖已删除的 `kernel_gen.dsl.emit_mlir`，统一改为复用 [`kernel_gen/dsl/mlir_gen/emit/core.py`](../../../../../../kernel_gen/dsl/mlir_gen/emit/core.py) 的 `_memory_to_nn_type(...)`。
- 更新 [`spec/dsl/mlir_gen.md`](../../../../../../spec/dsl/mlir_gen.md) 的公开合同描述，删除“`kernel_gen.dsl.emit_mlir` 与 `kernel_gen.dsl.mlir_gen.emit` 并列作为公开入口”的旧口径，收口为后者是唯一公开入口；同时去掉对已删除 `emit_mlir.py` facade 职责的长期合同描述。
- 本轮未扩到其他 `expectation`、`spec`、`kernel_gen` 或 `test` 文件；当前写集只包含任务点名的 [`expectation/utils/compare.py`](../../../../../../expectation/utils/compare.py) 与 [`spec/dsl/mlir_gen.md`](../../../../../../spec/dsl/mlir_gen.md)。
验证：
- `python - <<'PY' ...`（workdir=`/home/lfr/kernelcode_generate/wt-20260416-emit-mlir-refactor-r5`）-> `compare helpers ok`，确认 `from expectation.utils.compare import ...` 可用，且 `assert_static_symbol_int(...)`、`assert_dynamic_symbol_int(...)`、`assert_memory(...)` 在当前 emit 子系统下均可正常断言。
- `rg -n "kernel_gen\\.dsl\\.emit_mlir|共享入口|并列入口合同" spec/dsl/mlir_gen.md expectation/utils/compare.py`（workdir=`/home/lfr/kernelcode_generate/wt-20260416-emit-mlir-refactor-r5`）-> 仅命中“旧入口不再保留”为负向说明的文本，不再存在实际依赖 `kernel_gen.dsl.emit_mlir` 的代码导入。
- `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_emit_mlir.py test/dsl/test_ast.py test/dsl/test_ast_visitor.py test/dsl/test_mlir_gen.py test/dsl/mlir_gen/emit`（workdir=`/home/lfr/kernelcode_generate/wt-20260416-emit-mlir-refactor-r5`）-> `505 passed, 1 warning in 2.66s`
- `git -C /home/lfr/kernelcode_generate/wt-20260416-emit-mlir-refactor-r5 check-ignore -v expectation/utils/compare.py` -> `.gitignore:17:/expectation/ expectation/utils/compare.py`，确认 `compare.py` 当前仍是 ignored 路径，需下游按 worktree 实际文件复核。
- `git -C /home/lfr/kernelcode_generate/wt-20260416-emit-mlir-refactor-r5 ls-files expectation/utils/compare.py spec/dsl/mlir_gen.md` -> 仅列出 `spec/dsl/mlir_gen.md`，确认 [`expectation/utils/compare.py`](../../../../../../expectation/utils/compare.py) 尚未进入 tracked 集合。
结论：当前 build 已完成。`expectation/utils/compare.py` 已恢复为兼容 helper，且不再依赖已删除的 `kernel_gen.dsl.emit_mlir`；`spec/dsl/mlir_gen.md` 的公开入口合同已收口为 `kernel_gen.dsl.mlir_gen.emit`。下一步按流程续到下游 `review`，复核点应聚焦于：1）helper 兼容路径是否足够最小；2）`spec` 是否只保留单一公开入口；3）ignored 的 `expectation/utils/compare.py` 是否按当前协作规则处理。

时间：2026-04-16 22:58 +0800
经办人：提莫炖蘑菇
任务：T-20260416-8680d55f
任务目标：复核 `expectation/utils/compare.py` 是否已改为仅依赖 `kernel_gen.dsl.mlir_gen.emit`，以及 `spec/dsl/mlir_gen.md` 是否已收口为单一公开入口
改动：
- 问题列表：
  - 文件/接口：[`expectation/utils/compare.py`](../../../../../../expectation/utils/compare.py)
  - 现象：当前实现仍直接导入 `from kernel_gen.dsl.mlir_gen.emit.core import _memory_to_nn_type`，并在文档与实现中显式引用 `kernel_gen.dsl.mlir_gen.emit.core._memory_to_nn_type(...)`。但 [`kernel_gen/dsl/mlir_gen/emit/__init__.py`](../../../../../../kernel_gen/dsl/mlir_gen/emit/__init__.py) 已明确“包根仅暴露 `EmitContext` 与 `emit_mlir`”；因此 `compare.py` 仍在依赖 `emit` 子系统内部子模块与私有 helper，而不是任务目标要求的 `kernel_gen.dsl.mlir_gen.emit` 单一公开入口。
  - 风险：当前任务目标要求“`compare.py` 仅依赖 `kernel_gen.dsl.mlir_gen.emit`，且 `spec` 已收口为单一公开入口”。若继续保留对 `.core._memory_to_nn_type` 的直接依赖，`compare.py` 仍绑定内部实现细节；后续只要 `core.py` 私有 helper 重排、改名或移动，就会再次造成 expectation helper 断链，同时与 `spec/dsl/mlir_gen.md` 的“唯一公开入口”口径不一致。
  - 建议：回到 `build`，把 `compare.py` 改为只依赖 `kernel_gen.dsl.mlir_gen.emit` 包根可见的稳定入口；若当前包根缺少满足 `assert_memory(...)` 所需的稳定 helper，则应先在 `emit` 包根提供最小公开入口，再让 `compare.py` 通过该入口工作，而不是继续直连 `.core` 私有实现。
  - 优先级：P1
- 其余核对结果：
  - [`spec/dsl/mlir_gen.md`](../../../../../../spec/dsl/mlir_gen.md) 本轮新增口径已把 node-level lowering 子系统收口为 `kernel_gen.dsl.mlir_gen.emit` 唯一公开入口，并删除 `kernel_gen.dsl.emit_mlir` 的并列入口合同；`spec` 侧未发现额外必须修改项。
- 漏洞排查结果：
  - 输入校验绕过：未发现新增问题；`compare.py` 本轮改动不涉及外部输入解析分支。
  - 类型/形状绕过：未发现新增问题；build 记录中的 smoke 校验与 DSL 总体验收仍通过。
  - 边界越界：存在问题；`compare.py` 仍越过 `emit` 包根，直接依赖内部 `.core` 私有 helper。
  - 错误处理缺失：未发现新增问题；当前问题在于公开入口边界不一致，而非异常路径丢失。
  - 状态污染：未发现问题；当前 worktree 仅有 [`spec/dsl/mlir_gen.md`](../../../../../../spec/dsl/mlir_gen.md) tracked 改动、记录文件与 ignored 的 [`expectation/utils/compare.py`](../../../../../../expectation/utils/compare.py)。
  - 资源释放问题：未发现问题；本轮仅执行只读核对与最小复测。
- 改进建议：未发现额外改进点；上述 P1 已是必须修改项。
验证：
- `git -C /home/lfr/kernelcode_generate/wt-20260416-emit-mlir-refactor-r5 rev-parse --short HEAD && git -C /home/lfr/kernelcode_generate/wt-20260416-emit-mlir-refactor-r5 rev-parse --short origin/main && git -C /home/lfr/kernelcode_generate/wt-20260416-emit-mlir-refactor-r5 rev-list --left-right --count HEAD...origin/main` -> `bb89467`、`bb89467`、`0 0`
- `git -C /home/lfr/kernelcode_generate/wt-20260416-emit-mlir-refactor-r5 status --short --ignored=matching` -> tracked 改动仅 [`spec/dsl/mlir_gen.md`](../../../../../../spec/dsl/mlir_gen.md)，ignored 改动包含 [`expectation/utils/compare.py`](../../../../../../expectation/utils/compare.py)
- `python - <<'PY' ...`（AST 解析 import 语句）-> [`expectation/utils/compare.py`](../../../../../../expectation/utils/compare.py) 现有导入列表包含 `from kernel_gen.dsl.mlir_gen.emit.core import _memory_to_nn_type`
- `sed -n '1,260p' /home/lfr/kernelcode_generate/wt-20260416-emit-mlir-refactor-r5/expectation/utils/compare.py` -> 文件头与 `assert_memory(...)` 文档明确写出 `kernel_gen.dsl.mlir_gen.emit.core._memory_to_nn_type(...)`
- `sed -n '1,220p' /home/lfr/kernelcode_generate/wt-20260416-emit-mlir-refactor-r5/kernel_gen/dsl/mlir_gen/emit/__init__.py` -> 包根明确写“仅暴露 `EmitContext` 与 `emit_mlir`”
- `rg -n "kernel_gen\\.dsl\\.emit_mlir|kernel_gen\\.dsl\\.mlir_gen\\.emit|_memory_to_nn_type|from kernel_gen\\.dsl\\.mlir_gen\\.emit\\.core" /home/lfr/kernelcode_generate/wt-20260416-emit-mlir-refactor-r5/expectation/utils/compare.py /home/lfr/kernelcode_generate/wt-20260416-emit-mlir-refactor-r5/spec/dsl/mlir_gen.md /home/lfr/kernelcode_generate/wt-20260416-emit-mlir-refactor-r5/kernel_gen/dsl/mlir_gen/emit` -> `spec/dsl/mlir_gen.md` 已仅保留 `kernel_gen.dsl.mlir_gen.emit` 公开入口说明；[`expectation/utils/compare.py`](../../../../../../expectation/utils/compare.py) 仍命中 `from kernel_gen.dsl.mlir_gen.emit.core import _memory_to_nn_type`
- `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_emit_mlir.py test/dsl/test_ast.py test/dsl/test_ast_visitor.py test/dsl/test_mlir_gen.py test/dsl/mlir_gen/emit`（workdir=`/home/lfr/kernelcode_generate/wt-20260416-emit-mlir-refactor-r5`）-> `505 passed, 1 warning in 2.66s`
结论：需修改。当前 `spec/dsl/mlir_gen.md` 已基本收口为 `kernel_gen.dsl.mlir_gen.emit` 单一公开入口，但 [`expectation/utils/compare.py`](../../../../../../expectation/utils/compare.py) 仍直接依赖 `kernel_gen.dsl.mlir_gen.emit.core._memory_to_nn_type`，没有满足“仅依赖 `kernel_gen.dsl.mlir_gen.emit`”这一任务目标。下一步应续回 `build`，先把 `compare.py` 改成经由 `emit` 包根可见的稳定入口工作，再回到 review。

时间：2026-04-16 23:04 +0800
经办人：小李飞刀
任务：T-20260416-8680d55f
任务目标：修复 `expectation/utils/compare.py` 对 `kernel_gen.dsl.mlir_gen.emit.core._memory_to_nn_type` 的内部依赖，改为仅通过 `kernel_gen.dsl.mlir_gen.emit` 包根稳定入口完成 helper 行为
改动：
- 在 [`kernel_gen/dsl/mlir_gen/emit/__init__.py`](../../../../../../kernel_gen/dsl/mlir_gen/emit/__init__.py) 新增包根稳定 helper `memory_type_from_memory(memory)`，把 expectation/tooling 需要的 `Memory -> NnMemoryType` 转换能力收口到 `kernel_gen.dsl.mlir_gen.emit` 公开集合，避免继续直连 `.core` 私有实现。
- 更新 [`expectation/utils/compare.py`](../../../../../../expectation/utils/compare.py)，把 `assert_memory(...)` 从 `kernel_gen.dsl.mlir_gen.emit.core._memory_to_nn_type` 改为复用 `kernel_gen.dsl.mlir_gen.emit.memory_type_from_memory(...)`；文件说明同步改为“仅依赖包根稳定入口”。
- 补充 [`test/dsl/mlir_gen/emit/test_dispatch.py`](../../../../../../test/dsl/mlir_gen/emit/test_dispatch.py)，锁定 `emit` 包根当前稳定公开集合为 `EmitContext`、`emit_mlir`、`memory_type_from_memory`，并新增包根 helper 直接回归，确认其生成的 memory type shape / element type 与当前 lowering 一致。
- 细化 [`spec/dsl/mlir_gen.md`](../../../../../../spec/dsl/mlir_gen.md) 相关公开合同：`kernel_gen.dsl.mlir_gen.emit` 是 node-level lowering 的唯一公开入口；expectation/tooling 复用 helper 时也只能经由该包根 API，不得直连内部子模块。
验证：
- `python - <<'PY' ...`（workdir=`/home/lfr/kernelcode_generate/wt-20260416-emit-mlir-refactor-r5`）-> `compare helper ok`，确认 `from expectation.utils.compare import assert_memory` 与 `from kernel_gen.dsl.mlir_gen.emit import memory_type_from_memory` 在当前实现下可联合工作。
- `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/mlir_gen/emit/test_dispatch.py`（workdir=`/home/lfr/kernelcode_generate/wt-20260416-emit-mlir-refactor-r5`）-> `4 passed in 0.29s`
- `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_emit_mlir.py test/dsl/test_ast.py test/dsl/test_ast_visitor.py test/dsl/test_mlir_gen.py test/dsl/mlir_gen/emit`（workdir=`/home/lfr/kernelcode_generate/wt-20260416-emit-mlir-refactor-r5`）-> `506 passed, 1 warning in 2.22s`
- `git -C /home/lfr/kernelcode_generate/wt-20260416-emit-mlir-refactor-r5 status --short --ignored=matching` -> tracked 改动为 [`kernel_gen/dsl/mlir_gen/emit/__init__.py`](../../../../../../kernel_gen/dsl/mlir_gen/emit/__init__.py)、[`spec/dsl/mlir_gen.md`](../../../../../../spec/dsl/mlir_gen.md)、[`test/dsl/mlir_gen/emit/test_dispatch.py`](../../../../../../test/dsl/mlir_gen/emit/test_dispatch.py)，ignored 改动仍包含 [`expectation/utils/compare.py`](../../../../../../expectation/utils/compare.py)
结论：review 退回项已收口。`expectation/utils/compare.py` 现在只依赖 `kernel_gen.dsl.mlir_gen.emit` 包根稳定入口，不再直连 `.core` 私有 helper；`spec/dsl/mlir_gen.md` 的单一公开入口口径保持不回退；新增包根 helper 回归与 DSL 组合验收均通过。下一步按流程续到下游 `review`。

时间：2026-04-16 23:06 +0800
经办人：提莫炖蘑菇
任务：T-20260416-8680d55f
任务目标：审查 expectation compare helper 已切到 emit 包根稳定入口、spec 单一公开入口口径与对应回归结果
改动：
- 问题列表：未发现必须修改项。
- 复核结论：
  - [`expectation/utils/compare.py`](../../../../../../expectation/utils/compare.py) 当前导入已收口为 `from kernel_gen.dsl.mlir_gen.emit import memory_type_from_memory`，不再直连 `kernel_gen.dsl.mlir_gen.emit.core` 或已删除的 `kernel_gen.dsl.emit_mlir`。
  - [`kernel_gen/dsl/mlir_gen/emit/__init__.py`](../../../../../../kernel_gen/dsl/mlir_gen/emit/__init__.py) 已把 `memory_type_from_memory(...)` 纳入包根公开集合，且 `__all__` 现为 `["EmitContext", "emit_mlir", "memory_type_from_memory"]`；公开面与“expectation/tooling 只能经由包根 API 访问稳定 helper”的新口径一致。
  - [`spec/dsl/mlir_gen.md`](../../../../../../spec/dsl/mlir_gen.md) 已把 node-level lowering 子系统收口为 `kernel_gen.dsl.mlir_gen.emit` 唯一公开入口，并明确 expectation/tooling 不得直连内部子模块；未见旧 `kernel_gen.dsl.emit_mlir` 并列入口合同回退。
- 漏洞排查结果：
  - 输入校验绕过：未发现问题；本轮调整不改变外部输入解析与校验路径。
  - 类型/形状绕过：未发现问题；`memory_type_from_memory(...)` 回归与 DSL 总体验收均通过。
  - 边界越界：未发现问题；`compare.py` 已不再越过包根访问 `.core` 私有 helper。
  - 错误处理缺失：未发现问题；本轮未削弱现有异常路径，新增 helper 只暴露最小 `Memory -> NnMemoryType` 能力。
  - 状态污染：未发现问题；tracked 改动限制在 [`kernel_gen/dsl/mlir_gen/emit/__init__.py`](../../../../../../kernel_gen/dsl/mlir_gen/emit/__init__.py)、[`spec/dsl/mlir_gen.md`](../../../../../../spec/dsl/mlir_gen.md)、[`test/dsl/mlir_gen/emit/test_dispatch.py`](../../../../../../test/dsl/mlir_gen/emit/test_dispatch.py)，ignored 改动限制在 [`expectation/utils/compare.py`](../../../../../../expectation/utils/compare.py)。
  - 资源释放问题：未发现问题；本轮仅新增稳定 helper 并复跑回归。
- 改进建议：未发现额外改进点。
验证：
- `git -C /home/lfr/kernelcode_generate/wt-20260416-emit-mlir-refactor-r5 rev-parse --short HEAD && git -C /home/lfr/kernelcode_generate/wt-20260416-emit-mlir-refactor-r5 rev-parse --short origin/main && git -C /home/lfr/kernelcode_generate/wt-20260416-emit-mlir-refactor-r5 rev-list --left-right --count HEAD...origin/main` -> `bb89467`、`bb89467`、`0 0`
- `git -C /home/lfr/kernelcode_generate/wt-20260416-emit-mlir-refactor-r5 status --short --ignored=matching` -> tracked 改动为 `kernel_gen/dsl/mlir_gen/emit/__init__.py`、`spec/dsl/mlir_gen.md`、`test/dsl/mlir_gen/emit/test_dispatch.py`；ignored 改动包含 `expectation/utils/compare.py`
- `python - <<'PY' ...`（导入与 smoke）-> `compare helper ok`，确认 `from expectation.utils.compare import ...` 与 `from kernel_gen.dsl.mlir_gen.emit import memory_type_from_memory` 在当前实现下可联合工作
- `python - <<'PY' ...`（AST 解析 import 语句）-> [`expectation/utils/compare.py`](../../../../../../expectation/utils/compare.py) 当前导入列表仅包含 `from kernel_gen.dsl.mlir_gen.emit import memory_type_from_memory`，未再出现 `.core`
- `rg -n "kernel_gen\\.dsl\\.emit_mlir|from kernel_gen\\.dsl\\.mlir_gen\\.emit\\.core|emit\\.core" /home/lfr/kernelcode_generate/wt-20260416-emit-mlir-refactor-r5/expectation/utils/compare.py /home/lfr/kernelcode_generate/wt-20260416-emit-mlir-refactor-r5/spec/dsl/mlir_gen.md` -> 仅保留“旧入口不再保留 / 不得直连内部子模块”的负向说明
- `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/mlir_gen/emit/test_dispatch.py`（workdir=`/home/lfr/kernelcode_generate/wt-20260416-emit-mlir-refactor-r5`）-> `4 passed in 0.27s`
- `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_emit_mlir.py test/dsl/test_ast.py test/dsl/test_ast_visitor.py test/dsl/test_mlir_gen.py test/dsl/mlir_gen/emit`（workdir=`/home/lfr/kernelcode_generate/wt-20260416-emit-mlir-refactor-r5`）-> `506 passed, 1 warning in 2.12s`
结论：通过。`expectation/utils/compare.py` 已切到 `kernel_gen.dsl.mlir_gen.emit` 包根稳定入口，`spec/dsl/mlir_gen.md` 的单一公开入口口径未回退，新增包根 helper 回归与 DSL 组合验收均通过。下一步按当前口径续到 `merge`，再由管理员推进。

时间：2026-04-16 23:08 +0800
经办人：李白
任务：T-20260416-8680d55f
任务目标：合并已通过审查的 expectation compare helper emit 包根稳定入口与 spec 单一公开入口收口结果
改动：
- 在指定 worktree `/home/lfr/kernelcode_generate/wt-20260416-emit-mlir-refactor-r5` 核对当前分支 `T-20260416-8680d55f`，确认当前待合入的 tracked 写集为 `kernel_gen/dsl/mlir_gen/emit/__init__.py`、`spec/dsl/mlir_gen.md`、`test/dsl/mlir_gen/emit/test_dispatch.py`，以及当前任务记录文件。
- 当前 worktree 与 `origin/main` 已对齐；`HEAD..origin/main` 与 `origin/main...HEAD` 均不含其他链路业务差异，本轮无需先同步主分支历史。
- `expectation/utils/compare.py` 仍为 `.gitignore` 覆盖的 ignored 本地文件；本轮不修改 `.gitignore`，也不把该 ignored 文件纳入提交，交付范围保持为已审查的 tracked 写集与当前任务记录文件。
验证：
- `git status --short --ignored=matching` -> tracked 写集仅为 `kernel_gen/dsl/mlir_gen/emit/__init__.py`、`spec/dsl/mlir_gen.md`、`test/dsl/mlir_gen/emit/test_dispatch.py`，当前任务记录文件未跟踪；`expectation/utils/compare.py` 为 ignored。
- `git rev-list --left-right --count HEAD...origin/main` -> `0 0`
- `git diff --name-status origin/main...HEAD` -> 仅命中上述 3 个 tracked 目标文件。
- `git check-ignore -v expectation/utils/compare.py` -> `.gitignore:17:/expectation/`
结论：合并准备完成；下一步在当前 worktree 内只提交 3 个 tracked 目标文件与当前任务记录文件，推送 `origin/main` 后执行当前 merge 任务 `-done` 并回报管理员。
