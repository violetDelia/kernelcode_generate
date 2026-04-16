# 20260416-emit-mlir-refactor-r6

## 2026-04-16 23:31 +0800 守护最好的爱莉希雅

- 事项：补齐 [`T-20260416-3537457d`](/home/lfr/kernelcode_generate/TODO.md) 的当前任务号授权口径，供管理员按唯一文本分发。
- 当前口径：
  - [`T-20260416-3537457d`](/home/lfr/kernelcode_generate/TODO.md) 虽为 `build`，但任务目标直接包含 [`expectation/utils/compare.py`](/home/lfr/kernelcode_generate/expectation/utils/compare.py)，因此需要当前任务号的一次性 expectation 例外授权。
  - 现明确授权：若 [`T-20260416-3537457d`](/home/lfr/kernelcode_generate/TODO.md) 由 `build` 角色承接，则该任务号下被分发的 `build` 执行人可直接修改 [`expectation/utils/compare.py`](/home/lfr/kernelcode_generate/expectation/utils/compare.py) 与 [`spec/dsl/mlir_gen.md`](/home/lfr/kernelcode_generate/spec/dsl/mlir_gen.md)。
  - 本授权仅适用于当前任务号 [`T-20260416-3537457d`](/home/lfr/kernelcode_generate/TODO.md)；上一轮 [`T-20260416-8680d55f`](/home/lfr/kernelcode_generate/DONE.md) 的授权文本不沿用，后续若再新建任务，也需由架构师重新写明。
  - 精确写集仅限：
    - [`expectation/utils/compare.py`](/home/lfr/kernelcode_generate/expectation/utils/compare.py)
    - [`spec/dsl/mlir_gen.md`](/home/lfr/kernelcode_generate/spec/dsl/mlir_gen.md)
  - 不得扩到任何其他 `expectation`、其他 `spec`、任何实现文件、测试文件、[`.gitignore`](/home/lfr/kernelcode_generate/.gitignore)、`agents` 文档或其他 ignored 路径。
- 验收命令：
  - `PYTHONDONTWRITEBYTECODE=1 python - <<'PY'`
    `import importlib`
    `importlib.import_module("expectation.utils.compare")`
    `print("OK")`
    `PY`
  - `rg -n "kernel_gen\\.dsl\\.emit_mlir" expectation/utils/compare.py spec/dsl/mlir_gen.md`
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/dsl/test_emit_mlir.py test/dsl/test_ast.py test/dsl/test_ast_visitor.py test/dsl/test_mlir_gen.py test/dsl/mlir_gen/emit`
- 结论：
  - 管理员可按当前任务号直接分发，不需要再等待补充授权。
  - 本轮只推进 [`T-20260416-3537457d`](/home/lfr/kernelcode_generate/TODO.md)，不改派、不并行补建同范围任务。
