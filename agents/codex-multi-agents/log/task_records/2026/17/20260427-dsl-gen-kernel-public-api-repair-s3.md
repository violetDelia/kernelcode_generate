# 20260427-dsl-gen-kernel-public-api-repair-s3

- 时间：`2026-04-27 02:22:37 +0800`
- 经办人：`守护最好的爱莉希雅`
- 任务号：`T-20260427-107cf710`

## 任务目标

- 删除或改写 `test/dsl/ast/test_visitor_integration.py` 与 `test/dsl/ast/test_package.py` 对 `kernel_gen.dsl.mlir_gen` 非公开 `_build_signature_types` 的跨文件导入，让正文当前保留的 `pytest` 合同验收资产只验证公开 `API`，并跑通正文保留的合同验收命令；不改 `expectation`。

## 目标模块范围

- `test/dsl/ast/test_visitor_integration.py`
- `test/dsl/ast/test_package.py`
- `test/dsl/mlir_gen/**`
- `test/dsl/gen_kernel/**`
- `test/tools/test_dsl_run.py`
- `test/tools/test_mlir_gen_compare.py`
- `test/tools/test_ircheck_runner.py`
- `kernel_gen/dsl/mlir_gen/**`
- `kernel_gen/dsl/gen_kernel/**`
- `kernel_gen/tools/dsl_run.py`
- `kernel_gen/tools/mlir_gen_compare.py`
- `kernel_gen/tools/ircheck.py`
- `spec/dsl/mlir_gen.md`
- `spec/dsl/gen_kernel/gen_kernel.md`

## 禁止修改面

- `expectation/**`
- `execute_engine/**`
- 与本专题无直接关系的其他计划资产、归档记录或共享规则文件

## 记录要求

- 执行记录必须包含真实自检与 `Diff 反推自测`。
- 测试只验证公开 `API`；若仍需跨文件调用非公开 helper，必须停下并回报，不得自行扩写兼容出口。

## Build

- 时间：`2026-04-27 03:13:00 +0800`
- 经办人：`金铲铲大作战`

### 执行前阅读记录

- 已重读本记录、`TODO.md` 中 `T-20260427-107cf710` 的真实 `worktree` 条目，以及 `AGENTS.md` / 当前角色提示词中的实现与测试边界。
- 已确认本轮只收：
  - `test/dsl/ast/test_visitor_integration.py`
  - `test/dsl/ast/test_package.py`
  中对 `kernel_gen.dsl.mlir_gen` 非公开 `_build_signature_types` 的跨文件导入；不改 `expectation`，不扩到 parse-env / return-type 私有 helper 体系。

### 最小功能闭环

- 从 `test_package.py` 移除未使用的 `_build_signature_types` 导入。
- 将 `test_visitor_integration.py` 中基于 `_build_signature_types(...)` 的签名断言改为基于公开 `build_func_op_from_ast(...)` 的黑盒断言，验证 symbol 标量 `runtime_args` 会生成 `SymbolValueType` 输入与同型输出。
- 不扩写新的公开接口，不新增跨文件私有 helper 调用。

### 改动文件

- [`test/dsl/ast/test_package.py`](../../../../../../test/dsl/ast/test_package.py)
- [`test/dsl/ast/test_visitor_integration.py`](../../../../../../test/dsl/ast/test_visitor_integration.py)

### Diff 反推自测

- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/ast/test_visitor_integration.py /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/ast/test_package.py`
  - `exit code 0`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3:/home/lfr/kernelcode_generate python3 - <<'PY' ... build_func_op_from_ast(func_ast, runtime_args=[SymbolDim('S')]) ... PY`
  - `exit code 0`
  - 结果：`public build_func_op_from_ast symbol signature ok`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/mlir_gen/test_function_builder.py -k 'symbol or runtime' -ra`
  - `exit code 0`
  - 结果：`1 passed, 3 deselected, 1 warning`
- `git -C /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3 diff --check`
  - `exit code 0`
- `_build_signature_types` 残留扫描：
  - `rg -n "_build_signature_types" test/dsl/ast/test_visitor_integration.py test/dsl/ast/test_package.py`
  - 结果：无命中

### 未执行项与原因

- 未直接执行 `pytest -q test/dsl/ast/test_visitor_integration.py test/dsl/ast/test_package.py`
  - 原因：这两份文件当前仍保留对 `kernel_gen.dsl.mlir_gen` 其他既有私有 helper 的 package-root 导入：
    - `_parse_function_with_env`
    - `_is_symbol_scalar_function`
    - `_symbol_expr_from_runtime_arg`
    - `_validate_return_type`
  - 它们不属于本轮“只收 `_build_signature_types`”的指令范围；本轮只证明修改后的用例已经转为通过公开 `build_func_op_from_ast(...)` 观察行为。

### 真实自检

- 只改了当前任务点名的两个测试文件，没有改 `expectation`、实现文件或 `spec`。
- 修改后不再通过 `_build_signature_types(...)` 观察签名细节，改为只通过公开 `build_func_op_from_ast(...)` 验证 symbol 标量签名行为。
- 没有新增新的公开接口，也没有通过包装、别名或反射方式引入新的跨文件私有 API 使用。
- `test_package.py` 中对 `_build_signature_types` 仅为残留导入，本轮已清掉。
- 本轮仍存在同文件内其他 mlir_gen 私有 helper 依赖，但这部分超出当前任务指令范围，已在“未执行项与原因”中单列。

### 合同验收

- 本轮未执行 `expectation`
- 原因：任务明确要求不改 `expectation`，且 `expectation` 只作为合同验收资产单列，不计入本轮 `Diff 反推自测`

## Merge

- 时间：`2026-04-27 18:45:00 +0800`
- 经办人：`李白`

### 执行前阅读记录

- 已重读 [`TODO.md`](../../../../../../TODO.md) 中 `T-20260427-107cf710` 条目、计划书 [`dsl_gen_kernel_mlir_gen_public_api_green_plan.md`](../../../../../../ARCHITECTURE/plan/dsl_gen_kernel_mlir_gen_public_api_green_plan.md) 的 `R1` 阶段，以及本记录内各轮 `Build / Review / Review 终审`。
- 已确认审查记录覆盖 `Diff 反推审查`，执行记录覆盖 `执行前阅读记录`、`最小功能闭环`、`自检` 与 `Diff 反推自测`。
- 已确认本轮 residual diff 只涉及：
  - [`kernel_gen/dsl/mlir_gen/emit/call_nn.py`](../../../../../../kernel_gen/dsl/mlir_gen/emit/call_nn.py)
  - [`test/dsl/ast/test_package.py`](../../../../../../test/dsl/ast/test_package.py)
  - [`test/dsl/ast/test_visitor_integration.py`](../../../../../../test/dsl/ast/test_visitor_integration.py)
  - [`test/dsl/mlir_gen/emit/test_call_nn.py`](../../../../../../test/dsl/mlir_gen/emit/test_call_nn.py)
  - 当前任务记录
- 本轮不涉及 `expectation`，也不接受任何非公开 `API` 回退。

### 最小功能闭环

- 在当前 worktree 内执行 `timeout 60 git fetch origin`。
- 将这组 residual diff 重放到最新 `origin/main`。
- 只保留已通过审查的公开边界收口与当前 merge 记录，不混入其他链路改动。

### 收口结果

- 已在当前 worktree 执行 `timeout 60 git fetch origin`，并把 residual diff 从旧基线 `1782921c` 重放到最新 `origin/main@c497af17`。
- 重放过程无冲突；最终待提交面仍只包含：
  - [`kernel_gen/dsl/mlir_gen/emit/call_nn.py`](../../../../../../kernel_gen/dsl/mlir_gen/emit/call_nn.py)
  - [`test/dsl/ast/test_package.py`](../../../../../../test/dsl/ast/test_package.py)
  - [`test/dsl/ast/test_visitor_integration.py`](../../../../../../test/dsl/ast/test_visitor_integration.py)
  - [`test/dsl/mlir_gen/emit/test_call_nn.py`](../../../../../../test/dsl/mlir_gen/emit/test_call_nn.py)
  - 当前任务记录
- 最小验证：
  - `python3 -m py_compile ...call_nn.py ...test_package.py ...test_visitor_integration.py ...test_call_nn.py`
    - 结果：通过
  - `git diff --check`
    - 结果：通过

## Build 复修

- 时间：`2026-04-27 17:42:00 +0800`
- 经办人：`金铲铲大作战`

### 执行前阅读记录

- 已重读本记录上一轮 `Build 复修`、最新 `Review` 退回项，以及当前 worktree residual diff。
- 本轮只收 [`kernel_gen/dsl/mlir_gen/emit/call_nn.py`](../../../../../../kernel_gen/dsl/mlir_gen/emit/call_nn.py) 的文件级 `API 列表` 口径。
- 不改 `expectation`，不扩修 `call_nn.py` 的实现逻辑与函数级私有 helper。

### 最小功能闭环

- 把 [`call_nn.py`](../../../../../../kernel_gen/dsl/mlir_gen/emit/call_nn.py) 文件头 `API 列表` 从错误声明的
  - `infer_nn_type(...)`
  - `emit_nn_call(...)`
  收回到当前 spec 已承接的公开入口
  - `emit_mlir(node, ctx)`
- 保持前一轮已收好的 [`test/dsl/mlir_gen/emit/test_call_nn.py`](../../../../../../test/dsl/mlir_gen/emit/test_call_nn.py) 公开测试边界与 AST 公开回归不回退。

### 改动文件

- [`kernel_gen/dsl/mlir_gen/emit/call_nn.py`](../../../../../../kernel_gen/dsl/mlir_gen/emit/call_nn.py)

### Diff 反推自测

- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/kernel_gen/dsl/mlir_gen/emit/call_nn.py`
  - `exit code 0`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/mlir_gen/emit/test_call_nn.py -ra`
  - `5 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/ast/test_package.py /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/ast/test_visitor_integration.py -ra`
  - `215 passed, 1 warning`
- `rg -n "^API 列表:|infer_nn_type\\(|emit_nn_call\\(|emit_mlir\\(node, ctx\\)" /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/kernel_gen/dsl/mlir_gen/emit/call_nn.py`
  - 结果：顶部 `API 列表` 现为 `无（当前文件不单独承载公开 API；公开入口见 emit_mlir(node, ctx)）`
  - 说明：`infer_nn_type(...)` / `emit_nn_call(...)` 只剩实现内部定义与函数注释，不再出现在文件级公开 `API` 索引里
- `git -C /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3 diff --check`
  - `exit code 0`

### 真实自检

- 本轮没有新增公开接口，也没有改 `call_nn.py` 的实现行为。
- 文件级 `API 列表` 已与当前 spec 承接面一致，不再把 `infer_nn_type(...)` / `emit_nn_call(...)` 自我声明为公开接口。
- 前一轮已收好的 `emit` 包根公开测试边界没有回退。

### 合同验收

- 本轮未执行 `expectation`
- 原因：任务明确要求不改 `expectation`，且 `expectation` 只作为合同验收资产单列，不计入本轮 `Diff 反推自测`

## Build 复修

- 时间：`2026-04-27 17:25:00 +0800`
- 经办人：`金铲铲大作战`

### 执行前阅读记录

- 已重读本记录上一轮 `Build 复修`、最新 `Review` 退回项，以及当前 worktree 的真实 residual diff。
- 本轮只收 [`test/dsl/mlir_gen/emit/test_call_nn.py`](../../../../../../test/dsl/mlir_gen/emit/test_call_nn.py) 里的剩余公开测试边界问题：
  - 去掉 `emit.context.LoweringError`
  - 去掉 `emit.call_nn.emit_nn_call`
  - 去掉 `call_nn_module._private_helper(...)` 白盒覆盖
- 不改 `expectation`，不扩到 `emit` 其他 family 测试。

### 最小功能闭环

- 把 [`test_call_nn.py`](../../../../../../test/dsl/mlir_gen/emit/test_call_nn.py) 从 helper 级白盒测试收成只走公开 `EmitContext(...)` / `emit_mlir(...)` 的黑盒冒烟集。
- 保持上轮已收口的：
  - [`test/dsl/ast/test_package.py`](../../../../../../test/dsl/ast/test_package.py)
  - [`test/dsl/ast/test_visitor_integration.py`](../../../../../../test/dsl/ast/test_visitor_integration.py)
  公开回归不回退。

### 改动文件

- [`test/dsl/mlir_gen/emit/test_call_nn.py`](../../../../../../test/dsl/mlir_gen/emit/test_call_nn.py)

### Diff 反推自测

- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/mlir_gen/emit/test_call_nn.py`
  - `exit code 0`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/mlir_gen/emit/test_call_nn.py -ra`
  - `5 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/ast/test_package.py /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/ast/test_visitor_integration.py -ra`
  - `215 passed, 1 warning`
- 私有导入/调用残留扫描：
  - `rg -n "^from kernel_gen\\.dsl\\.mlir_gen\\.emit\\.context import|^from kernel_gen\\.dsl\\.mlir_gen\\.emit\\.call_nn import|^import importlib$|call_nn_module|ctx\\._set_cache\\(|emit_nn_call\\(" /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/mlir_gen/emit/test_call_nn.py`
  - 结果：无命中
- `git -C /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3 diff --check`
  - `exit code 0`

### 真实自检

- 本轮没有新增任何公开接口，也没有把 `emit.call_nn` / `emit.context` 子模块重新抬成公开入口。
- [`test_call_nn.py`](../../../../../../test/dsl/mlir_gen/emit/test_call_nn.py) 现在只通过公开：
  - `EmitContext(...)`
  - `emit_mlir(...)`
  观察 nn elementwise 行为。
- 测试文件内保留的 `_expr_key(...)`、`_memory_type(...)`、`_build_emit_context(...)` 都是当前文件内 helper，没有跨文件直连非公开 API。
- 上轮已收口的 AST 公开回归没有回退。

### 合同验收

- 本轮未执行 `expectation`
- 原因：任务明确要求不改 `expectation`，且 `expectation` 只作为合同验收资产单列，不计入本轮 `Diff 反推自测`

## Build 复修

- 时间：`2026-04-27 16:22:00 +0800`
- 经办人：`金铲铲大作战`

### 执行前阅读记录

- 已重读本记录最新 `Review` 退回项、`TODO.md` 中 `T-20260427-107cf710` 当前条目，以及当前 worktree residual diff。
- 本轮只收 [`test/dsl/mlir_gen/emit/test_call_nn.py`](../../../../../../test/dsl/mlir_gen/emit/test_call_nn.py) 对 `emit.core._expr_key` 的跨文件非公开导入，不扩修其他 `mlir_gen` 测试边界。

### 最小功能闭环

- 去掉 [`test_call_nn.py`](../../../../../../test/dsl/mlir_gen/emit/test_call_nn.py) 对 `kernel_gen.dsl.mlir_gen.emit.core._expr_key` 的导入。
- 在当前测试文件内用本地 helper 复用 `id(expr)` 作为 `EmitContext.types/cache` 键，避免跨文件直连私有 helper。
- 复跑 `test_call_nn.py` 与上一轮已收口的两份公开 AST 测试，确认边界不回退。

### 改动文件

- [`test/dsl/mlir_gen/emit/test_call_nn.py`](../../../../../../test/dsl/mlir_gen/emit/test_call_nn.py)

### Diff 反推自测

- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/mlir_gen/emit/test_call_nn.py`
  - `exit code 0`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/mlir_gen/emit/test_call_nn.py -ra`
  - `exit code 0`
  - 结果：`15 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/ast/test_package.py /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/ast/test_visitor_integration.py -ra`
  - `exit code 0`
  - 结果：`215 passed, 1 warning`
- 非公开导入残留扫描：
  - `rg -n "from kernel_gen\\.dsl\\.mlir_gen\\.emit\\.core import _expr_key|emit\\.core.*_expr_key" /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/mlir_gen/emit/test_call_nn.py`
  - 结果：无命中

### 真实自检

- 这轮没有新增任何 spec 未定义的公开接口，也没有把测试边界重新拉回 `emit.core` 私有 helper。
- `test_call_nn.py` 现在只在当前文件内使用 `_expr_key(...)` helper，满足“测试不得跨文件直连非公开 API”的 build 规则。
- 直接受影响的 `test_call_nn.py` 与上一轮两份公开 AST 回归都已通过，没有回退已经收口的公开测试行为。

### 合同验收

- 本轮未执行 `expectation`
- 原因：任务明确要求不改 `expectation`，且 `expectation` 只作为合同验收资产单列，不计入本轮 `Diff 反推自测`

## Build 复修

- 时间：`2026-04-27 16:02:00 +0800`
- 经办人：`金铲铲大作战`

### 执行前阅读记录

- 已重读本记录最新 `Review` 退回项、`TODO.md` 中 `T-20260427-107cf710` 当前条目，以及当前 worktree 的 residual diff。
- 本轮只收 [`kernel_gen/dsl/mlir_gen/emit/call_nn.py`](../../../../../../kernel_gen/dsl/mlir_gen/emit/call_nn.py) 中仍跨文件依赖 `.core` 下划线 helper 的实现公开边界，不扩修无关 `expectation`。

### 最小功能闭环

- 去掉 [`call_nn.py`](../../../../../../kernel_gen/dsl/mlir_gen/emit/call_nn.py) 对 `.core` 私有 helper 的跨文件导入。
- 把 `call_nn.py` 当前真正需要的最小类型推导 / memory 转换 / 常量构造逻辑收回当前文件内 helper。
- 复跑直接受影响的 `call_nn` lowering 测试，以及上一轮已收口的两份公开 AST 测试，确认不回退。

### 改动文件

- [`kernel_gen/dsl/mlir_gen/emit/call_nn.py`](../../../../../../kernel_gen/dsl/mlir_gen/emit/call_nn.py)

### Diff 反推自测

- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/kernel_gen/dsl/mlir_gen/emit/call_nn.py`
  - `exit code 0`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/mlir_gen/emit/test_call_nn.py -ra`
  - `exit code 0`
  - 结果：`15 passed, 1 warning`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/ast/test_package.py /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/ast/test_visitor_integration.py -ra`
  - `exit code 0`
  - 结果：`215 passed, 1 warning`
- 私有边界扫描：
  - `rg -n "from \\.core|_const_symbol_int|_expect_memory_value|_infer_broadcast_memory_type|_infer_expr_type|_lower_expr|_memory_to_nn_type|_memory_type_from_parts|_nn_memory_type_to_memory|_resolve_nn_arith_element_type|_resolve_runtime_scalar_value" /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/kernel_gen/dsl/mlir_gen/emit/call_nn.py`
  - 结果：仅命中当前文件内 helper 定义与本文件内使用，无 `.core` 跨文件导入
- `git -C /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3 diff --check`
  - `exit code 0`

### 真实自检

- 这轮没有新增 spec 未定义的公开接口，只把 `call_nn.py` 仍依赖 `.core` 下划线 helper 的逻辑收回当前文件内 helper，符合“只允许当前文件内 helper”的 build 规则。
- 当前文件现在只保留公开依赖：`EmitContext`、`LoweringError`、`emit_mlir(...)`、`memory_type_from_memory(...)`；不再跨文件调用 `.core` 非公开 API。
- 直接受影响的 `call_nn` 测试与上一轮两份公开 AST 测试都已回归通过，没有把“只走公开 API”的测试边界回退。

### 合同验收

- 本轮未执行 `expectation`
- 原因：任务明确要求不改 `expectation`，且 `expectation` 只作为合同验收资产单列，不计入本轮 `Diff 反推自测`

## Review

- 时间：`2026-04-27 16:20:00 +0800`
- 审查人：`提莫炖蘑菇`

### 执行前阅读记录

- 已重读 `TODO.md` 中 `T-20260427-107cf710` 的任务行、计划书 [`ARCHITECTURE/plan/dsl_gen_kernel_mlir_gen_public_api_green_plan.md`](../../../../../../ARCHITECTURE/plan/dsl_gen_kernel_mlir_gen_public_api_green_plan.md)、本任务记录，以及当前 worktree 的实际 residual diff。
- 已按最新审查规则复核：
  - 当前 diff 是否还存在跨文件非公开 `API` 使用
  - 公开测试是否仍直连非 `API` 接口
  - 被改实现文件的文件级 `API` 列表是否与实现一致

### 问题列表

1. [`kernel_gen/dsl/mlir_gen/emit/call_nn.py`](../../../../../../kernel_gen/dsl/mlir_gen/emit/call_nn.py) 当前 residual diff 仍跨文件依赖 `.core` 下划线 helper，命中“实现不得跨文件使用非公开 API”规则。
   - 位置：[`kernel_gen/dsl/mlir_gen/emit/call_nn.py:80`](../../../../../../kernel_gen/dsl/mlir_gen/emit/call_nn.py#L80) 到 [`kernel_gen/dsl/mlir_gen/emit/call_nn.py:92`](../../../../../../kernel_gen/dsl/mlir_gen/emit/call_nn.py#L92)
   - 现状：`call_nn.py` 仍直接导入 `_LoweringError`、`_const_symbol_int`、`_expect_memory_value`、`_expr_key`、`_infer_broadcast_memory_type`、`_infer_expr_type`、`_lower_expr`、`_memory_to_nn_type`、`_memory_type_from_parts`、`_nn_memory_type_to_memory`、`_resolve_nn_arith_element_type`、`_resolve_runtime_scalar_value`。
   - 影响：虽然 `test/dsl/ast/test_package.py` 与 `test/dsl/ast/test_visitor_integration.py` 已经不再直连 `mlir_gen` 包根私有 helper 与 `emit.core` 私有 helper，但本轮 residual diff 自己仍包含 1 个被修改的实现文件继续跨文件消费非公开 helper，所以当前任务还不能给 `通过`。

### 真实审查

- `test/dsl/ast/test_package.py` 与 `test/dsl/ast/test_visitor_integration.py` 这轮已经去掉了 review 退回时点名的两类私有导入：
  - 不再从 `kernel_gen.dsl.mlir_gen` 包根导入私有 helper
  - 不再从 `kernel_gen.dsl.mlir_gen.emit.core` 导入下划线 helper
- `parse_function_with_env(...)` 现在通过 [`kernel_gen.dsl.ast.parser`](../../../../../../kernel_gen/dsl/ast/parser.py) 模块导入；对应 [`spec/dsl/ast/parser.md`](../../../../../../spec/dsl/ast/parser.md) 已把它定义为 parser 模块级公开入口，所以这部分不构成非公开 `API` 直连。
- 当前剩余问题只在 `call_nn.py`。该文件本轮不仅更新了文件头与 `API 列表`，还改了错误收口逻辑，因此它属于本轮必须一起复核的实现文件，不能跳过其中的非公开依赖。

### Diff 反推审查

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/ast/test_package.py /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/ast/test_visitor_integration.py /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/mlir_gen/emit/test_call_nn.py -ra`
  - 结果：`230 passed, 1 warning`
- `rg -n "from \\.core import|_LoweringError|_infer_expr_type as _emit_infer_expr_type|_lower_expr as _emit_lower_expr" kernel_gen/dsl/mlir_gen/emit/call_nn.py`
  - 结果：命中 [`kernel_gen/dsl/mlir_gen/emit/call_nn.py:80`](../../../../../../kernel_gen/dsl/mlir_gen/emit/call_nn.py#L80) 到 [`kernel_gen/dsl/mlir_gen/emit/call_nn.py:92`](../../../../../../kernel_gen/dsl/mlir_gen/emit/call_nn.py#L92) 的跨文件下划线 helper 导入
- `git -C /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3 diff --check`
  - 结果：通过

### 合同验收

- 未执行 `expectation`
- 原因：任务边界是公开 `pytest` 与实现公开边界收口，`expectation` 继续只作合同验收资产单列

### 审查结论

- `需修改`
- 这轮测试文件里的私有导入问题已经收口，但当前 residual diff 还包含 [`kernel_gen/dsl/mlir_gen/emit/call_nn.py`](../../../../../../kernel_gen/dsl/mlir_gen/emit/call_nn.py) 对 `.core` 下划线 helper 的跨文件依赖。先把这部分实现边界一起收口，再回到 review。

## Build 续修

- 时间：`2026-04-27 16:05:00 +0800`
- 经办人：`金铲铲大作战`

### 执行前阅读记录

- 已复核上一轮 `199 passed, 16 failed` 的真实失败栈，确认私有导入问题已清空，剩余只落在两条公开口径漂移：
  - `MGEN-026B` 的 `dma.alloc` mixed symbol+const 场景测试构造过度依赖 return 注解解析
  - `MGEN-014` 的 implicit broadcast mismatch 没有回到公开 `AstVisitorError` 链路
- 本轮继续只围绕当前任务点名的两份公开测试收口，并保持 `expectation` 不变。

### 最小功能闭环

- 将 `test_build_func_op_supports_dma_alloc_helper_with_symbol_plus_const_shape_args(...)` 改为只通过公开 `build_func_op(...)` 验证：
  - 输入 `!symbol.int<"...">`
  - `dma.alloc` 结果 `shape`
  不再把 mixed symbol+const 场景绑死在 return 注解解析上。
- 对 `kernel_gen.dsl.mlir_gen.emit.call_nn` 做最小公开实现修复：
  - binary implicit-broadcast 失败时把底层 `ValueError` 收回当前 lowering 错误链
  - 让 `build_func_op(...)` 最终继续对外表现为 `AstVisitorError`
  - 同步补齐该实现文件的文件级 `API 列表`

### 改动文件

- [`test/dsl/ast/test_visitor_integration.py`](../../../../../../test/dsl/ast/test_visitor_integration.py)
- [`kernel_gen/dsl/mlir_gen/emit/call_nn.py`](../../../../../../kernel_gen/dsl/mlir_gen/emit/call_nn.py)

### Diff 反推自测

- 私有导入残留扫描：
  - `rg -n "kernel_gen\\.dsl\\.mlir_gen\\._|emit\\.core import _|_build_signature_types|_infer_expr_type|_lower_expr|_expect_memory_value" test/dsl/ast/test_package.py test/dsl/ast/test_visitor_integration.py`
  - 结果：无命中
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/kernel_gen/dsl/mlir_gen/emit/call_nn.py /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/ast/test_package.py /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/ast/test_visitor_integration.py`
  - `exit code 0`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/ast/test_package.py /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/ast/test_visitor_integration.py -ra`
  - `exit code 0`
  - 结果：`215 passed, 1 warning`
- `git -C /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3 diff --check`
  - `exit code 0`

### 真实自检

- 这轮没有回退“只走公开 API”的测试边界；两份公开测试不再跨文件导入 `kernel_gen.dsl.mlir_gen` 包根私有 helper，也不再导入 `emit.core` 下划线 helper。
- `call_nn.py` 的改动只是在当前文件内把底层 `ValueError` 收敛回已有 lowering 错误链，没有新增 spec 未定义的公开接口，也没有新增跨文件非公开 API 调用。
- `MGEN-026B` 的测试现在直接锁公开 `build_func_op(...)` 对输入类型与 `dma.alloc` 结果 shape 的行为，覆盖目标比依赖 return 注解解析更稳定，且不缩小 spec 约束。

### 合同验收

- 本轮未执行 `expectation`
- 原因：任务明确要求不改 `expectation`，且 `expectation` 只作为合同验收资产单列，不计入本轮 `Diff 反推自测`

## Review

- 时间：`2026-04-27 03:28:00 +0800`
- 审查人：`不要啊教练`

### 执行前阅读记录

- 已重读 `TODO.md` 中 `T-20260427-107cf710` 的任务行、计划书 [`ARCHITECTURE/plan/dsl_gen_kernel_mlir_gen_public_api_green_plan.md`](../../../../../../ARCHITECTURE/plan/dsl_gen_kernel_mlir_gen_public_api_green_plan.md)、本任务记录，以及当前 worktree 的实际 diff。
- 已按最新审查规则复核：是否仍跨文件使用非公开 `API`、测试是否仍直连非 `API` 接口、执行人是否完成当前 diff 对应测试。

### 问题列表

1. `test/dsl/ast/test_visitor_integration.py` 与 `test/dsl/ast/test_package.py` 仍直接从 `kernel_gen.dsl.mlir_gen` 包根导入非公开 helper，当前任务目标没有闭合。

## Review

- 时间：`2026-04-27 16:32:00 +0800`
- 审查人：`提莫炖蘑菇`

### 执行前阅读记录

- 已重读 `TODO.md` 中 `T-20260427-107cf710` 当前条目、计划书 [`ARCHITECTURE/plan/dsl_gen_kernel_mlir_gen_public_api_green_plan.md`](../../../../../../ARCHITECTURE/plan/dsl_gen_kernel_mlir_gen_public_api_green_plan.md) 与本任务记录。
- 已按当前审查规则重新核对：
  - `call_nn.py` 当前 residual diff 是否仍跨文件调用非公开 API
  - 公开 pytest 证据链是否仍直连非 API 接口
  - 被改实现文件的文件级 `API` 列表是否收口

### 问题列表

1. 作为本轮公开证据链的一部分，[`test/dsl/mlir_gen/emit/test_call_nn.py`](../../../../../../test/dsl/mlir_gen/emit/test_call_nn.py) 仍直接导入 [`kernel_gen.dsl.mlir_gen.emit.core._expr_key`](../../../../../../kernel_gen/dsl/mlir_gen/emit/core.py)。
   - 位置：[`test/dsl/mlir_gen/emit/test_call_nn.py:44`](../../../../../../test/dsl/mlir_gen/emit/test_call_nn.py#L44)
   - 使用：[`test/dsl/mlir_gen/emit/test_call_nn.py:68`](../../../../../../test/dsl/mlir_gen/emit/test_call_nn.py#L68) 及后续多处继续把 `_expr_key(...)` 当稳定入口使用。
   - 影响：虽然 [`kernel_gen/dsl/mlir_gen/emit/call_nn.py`](../../../../../../kernel_gen/dsl/mlir_gen/emit/call_nn.py) 已清掉对 `.core` 私有 helper 的跨文件依赖，且 [`test/dsl/ast/test_package.py`](../../../../../../test/dsl/ast/test_package.py) / [`test/dsl/ast/test_visitor_integration.py`](../../../../../../test/dsl/ast/test_visitor_integration.py) 已退出对 `mlir_gen` 包根与 `emit.core` 私有 helper 的直连，但当前公开 pytest 证据本身仍命中“测试不得跨文件直连非公开 API”硬规则。

### 真实审查

- 当前 residual diff 只剩：
  - [`kernel_gen/dsl/mlir_gen/emit/call_nn.py`](../../../../../../kernel_gen/dsl/mlir_gen/emit/call_nn.py)
  - [`test/dsl/ast/test_package.py`](../../../../../../test/dsl/ast/test_package.py)
  - [`test/dsl/ast/test_visitor_integration.py`](../../../../../../test/dsl/ast/test_visitor_integration.py)
- 这三处本身已经收口：
  - `call_nn.py` 不再从 `.core` 导入下划线 helper
  - `test_package.py` / `test_visitor_integration.py` 不再直连 `mlir_gen` 包根私有 helper，也不再直连 `emit.core` 私有 helper
  - `parse_function_with_env(...)` 现在通过 [`kernel_gen.dsl.ast.parser`](../../../../../../kernel_gen/dsl/ast/parser.py) 模块入口使用；该入口已在 [`spec/dsl/ast/parser.md`](../../../../../../spec/dsl/ast/parser.md) 定义为公开 API
- 但本轮 build 自己用来证明“公开 pytest 回归通过”的 [`test/dsl/mlir_gen/emit/test_call_nn.py`](../../../../../../test/dsl/mlir_gen/emit/test_call_nn.py) 仍跨文件直连 [`emit.core`](../../../../../../kernel_gen/dsl/mlir_gen/emit/core.py) 私有 helper，所以当前 review 仍不能给 `通过`。

### Diff 反推审查

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/ast/test_package.py /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/ast/test_visitor_integration.py /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/mlir_gen/emit/test_call_nn.py -ra`
  - 结果：`230 passed, 1 warning`
- `rg -n "from kernel_gen\\.dsl\\.mlir_gen\\.emit\\.core import _expr_key|_expr_key\\(" /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/mlir_gen/emit/test_call_nn.py`
  - 结果：命中 [`test/dsl/mlir_gen/emit/test_call_nn.py:44`](../../../../../../test/dsl/mlir_gen/emit/test_call_nn.py#L44) 及后续多处 `_expr_key(...)` 使用
- `git -C /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3 diff --check`
  - 结果：通过

### 合同验收

- 未执行 `expectation`
- 原因：本轮任务边界是公开 `pytest` 与实现公开边界收口，`expectation` 继续只作合同验收资产单列

### 审查结论

- `需修改`
- 这轮 residual diff 自身已经清掉 [`call_nn.py`](../../../../../../kernel_gen/dsl/mlir_gen/emit/call_nn.py) 对 `.core` 私有 helper 的依赖，但作为公开证据链的 [`test_call_nn.py`](../../../../../../test/dsl/mlir_gen/emit/test_call_nn.py) 还在直连 [`emit.core._expr_key`](../../../../../../kernel_gen/dsl/mlir_gen/emit/core.py)。先把这条测试边界也收口，再回到 review。

## Review 续审

- 时间：`2026-04-27 16:41:00 +0800`
- 审查人：`提莫炖蘑菇`

### 执行前阅读记录

- 已重读 `TODO.md` 中 `T-20260427-107cf710` 当前条目、计划书 [`ARCHITECTURE/plan/dsl_gen_kernel_mlir_gen_public_api_green_plan.md`](../../../../../../ARCHITECTURE/plan/dsl_gen_kernel_mlir_gen_public_api_green_plan.md) 与本任务记录。
- 已按最新规则继续核对：
  - `test_call_nn.py` 是否已去除对 `emit.core._expr_key` 的直连
  - 当前公开 pytest 是否仍直连 `spec` 未定义的接口
  - 被改实现文件的文件级 `API` 列表与 `spec` 是否一致

### 问题列表

1. [`test/dsl/mlir_gen/emit/test_call_nn.py`](../../../../../../test/dsl/mlir_gen/emit/test_call_nn.py) 虽然已经去掉 [`emit.core._expr_key`](../../../../../../kernel_gen/dsl/mlir_gen/emit/core.py) 直连，但仍继续跨文件直连未在 `spec` 定义为公开 `API` 的模块级接口：
   - [`test/dsl/mlir_gen/emit/test_call_nn.py:45`](../../../../../../test/dsl/mlir_gen/emit/test_call_nn.py#L45) `from kernel_gen.dsl.mlir_gen.emit.context import LoweringError`
   - [`test/dsl/mlir_gen/emit/test_call_nn.py:46`](../../../../../../test/dsl/mlir_gen/emit/test_call_nn.py#L46) `from kernel_gen.dsl.mlir_gen.emit.call_nn import emit_nn_call`
   - [`test/dsl/mlir_gen/emit/test_call_nn.py:51`](../../../../../../test/dsl/mlir_gen/emit/test_call_nn.py#L51) 仍把 `kernel_gen.dsl.mlir_gen.emit.call_nn` 当稳定模块入口导入
2. 当前 `spec` 公开面没有承接上述接口：
   - [`spec/dsl/emit_mlir.md`](../../../../../../spec/dsl/emit_mlir.md) 顶部 `API 列表` 只定义 `EmitContext(...)` 与 `emit_mlir(...)`
   - [`spec/dsl/mlir_gen.md`](../../../../../../spec/dsl/mlir_gen.md) 只把 `call_nn.py` 写为 nn elementwise 规则归属文件，没有把 `emit_nn_call(...)` / `infer_nn_type(...)` / `LoweringError` 定义为公开 `API`
3. [`kernel_gen/dsl/mlir_gen/emit/call_nn.py`](../../../../../../kernel_gen/dsl/mlir_gen/emit/call_nn.py) 文件头 `API 列表` 当前把 `infer_nn_type(...)` / `emit_nn_call(...)` 写成公开接口，但 `spec` 未同步承接；按现行规则，这类接口不能仅靠实现文件头自我公开。

### 真实审查

- 当前 residual diff 的上一轮阻断已经消除：
  - [`test_call_nn.py`](../../../../../../test/dsl/mlir_gen/emit/test_call_nn.py) 不再导入 `emit.core._expr_key`
  - 现在改为同文件内定义 `_expr_key(...)`，这一点本身没有问题
- 但本轮“公开 pytest 回归”仍不干净，因为同一测试文件继续直接依赖：
  - [`emit.context.LoweringError`](../../../../../../kernel_gen/dsl/mlir_gen/emit/context.py)
  - [`emit.call_nn.emit_nn_call`](../../../../../../kernel_gen/dsl/mlir_gen/emit/call_nn.py)
- 这两条在当前 `spec` 里都不是公开 `API`。因此即使测试全绿，也不能把它当公开边界已经收口的证据。

### Diff 反推审查

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/ast/test_package.py /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/ast/test_visitor_integration.py /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/mlir_gen/emit/test_call_nn.py -ra`
  - 结果：`230 passed, 1 warning`
- `rg -n "from kernel_gen\\.dsl\\.mlir_gen\\.emit\\.context import LoweringError|from kernel_gen\\.dsl\\.mlir_gen\\.emit\\.call_nn import emit_nn_call|importlib\\.import_module\\(\\\"kernel_gen\\.dsl\\.mlir_gen\\.emit\\.call_nn\\\"\\)" /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/mlir_gen/emit/test_call_nn.py`
  - 结果：命中 [`test_call_nn.py:45`](../../../../../../test/dsl/mlir_gen/emit/test_call_nn.py#L45)、[`test_call_nn.py:46`](../../../../../../test/dsl/mlir_gen/emit/test_call_nn.py#L46)、[`test_call_nn.py:51`](../../../../../../test/dsl/mlir_gen/emit/test_call_nn.py#L51)
- `git -C /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3 diff --check`
  - 结果：通过

### 合同验收

- 未执行 `expectation`
- 原因：本轮任务边界仍是公开 `pytest` 与实现公开边界收口，`expectation` 继续只作合同验收资产单列

### 审查结论

- `需修改`
- `_expr_key` 这条私有直连已经修掉，但 `test_call_nn.py` 现在仍把 `emit_nn_call(...)`、`LoweringError` 和 `emit.call_nn` 模块本身当公开接口直连；而当前 `spec` 没有把它们定义为公开 `API`，所以这轮还不能通过。

## Review 再审

- 时间：`2026-04-27 16:47:00 +0800`
- 审查人：`提莫炖蘑菇`

### 执行前阅读记录

- 已重读 `TODO.md` 中 `T-20260427-107cf710` 当前条目、计划书 [`ARCHITECTURE/plan/dsl_gen_kernel_mlir_gen_public_api_green_plan.md`](../../../../../../ARCHITECTURE/plan/dsl_gen_kernel_mlir_gen_public_api_green_plan.md) 与本任务记录。
- 已按最新规则继续核对：
  - `test_call_nn.py` 是否已经收回到 `emit` 包根公开入口
  - `call_nn.py` 文件级 `API` 列表是否与 `spec` 承接一致
  - 公开 pytest 证据链是否还存在跨文件非公开 `API` 使用

### 问题列表

1. [`test/dsl/mlir_gen/emit/test_call_nn.py`](../../../../../../test/dsl/mlir_gen/emit/test_call_nn.py) 当前已经只通过 [`kernel_gen.dsl.mlir_gen.emit`](../../../../../../kernel_gen/dsl/mlir_gen/emit/__init__.py) 包根公开入口验证行为，不再直连 `emit.core` / `emit.context` / `emit.call_nn`。
   - 这条上一轮阻断已经消除。
2. 当前剩余阻断落在实现文件自身的公开索引与 `spec` 分叉：
   - [`kernel_gen/dsl/mlir_gen/emit/call_nn.py`](../../../../../../kernel_gen/dsl/mlir_gen/emit/call_nn.py) 顶部 `API 列表` 仍把 `infer_nn_type(...)` 与 `emit_nn_call(...)` 写成公开 `API`
   - 但 [`spec/dsl/emit_mlir.md`](../../../../../../spec/dsl/emit_mlir.md) 顶部 `API 列表` 只承接 `EmitContext(...)` 与 `emit_mlir(...)`
   - [`spec/dsl/mlir_gen.md`](../../../../../../spec/dsl/mlir_gen.md) 只把 `call_nn.py` 写为 nn elementwise 规则归属文件，没有把 `infer_nn_type(...)` / `emit_nn_call(...)` 定义为公开合同
3. 按现行审查规则，build 改动实现文件时，文件级 `API` 列表必须与 `spec` 一致；不能只靠实现文件头把接口自我公开。

### 真实审查

- 当前公开测试边界已经收口：
  - [`test_call_nn.py`](../../../../../../test/dsl/mlir_gen/emit/test_call_nn.py) 现在只导入 `EmitContext` 与 `emit_mlir`
  - 同文件内部自定义 `_expr_key(...)` / `_memory_type(...)` / `_build_emit_context(...)`，不再跨文件直连 `emit.core` / `emit.context` / `emit.call_nn` 的非公开 helper
- 当前不能通过的原因只剩 1 处：
  - [`call_nn.py`](../../../../../../kernel_gen/dsl/mlir_gen/emit/call_nn.py) 文件头把 `infer_nn_type(...)` / `emit_nn_call(...)` 列成公开接口，但 `spec` 没同步承接
- 这属于当前 residual diff 内可直接继续收口的问题，所以仍应退回 `build`

### Diff 反推审查

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/ast/test_package.py /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/ast/test_visitor_integration.py /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/mlir_gen/emit/test_call_nn.py -ra`
  - 结果：`220 passed, 1 warning`
- `rg -n "emit_nn_call|infer_nn_type|API 列表" /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/kernel_gen/dsl/mlir_gen/emit/call_nn.py /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/spec/dsl/emit_mlir.md /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/spec/dsl/mlir_gen.md`
  - 结果：命中 [`call_nn.py`](../../../../../../kernel_gen/dsl/mlir_gen/emit/call_nn.py) 顶部 `API 列表` 的 `infer_nn_type(...)` / `emit_nn_call(...)`，但 `spec` 顶部公开 `API` 列表未承接这两条
- `git -C /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3 diff --check`
  - 结果：通过

### 合同验收

- 未执行 `expectation`
- 原因：本轮任务边界仍是公开 `pytest` 与实现公开边界收口，`expectation` 继续只作合同验收资产单列

### 审查结论

- `需修改`
- 公开 pytest 边界已经收口，但 [`call_nn.py`](../../../../../../kernel_gen/dsl/mlir_gen/emit/call_nn.py) 文件头仍把 `spec` 未承接的 `infer_nn_type(...)` / `emit_nn_call(...)` 写成公开接口；先把实现文件级 `API` 索引与 `spec` 对齐，再回到 review。

## Review 终审

- 时间：`2026-04-27 16:55:00 +0800`
- 审查人：`提莫炖蘑菇`

### 执行前阅读记录

- 已重读 `TODO.md` 中 `T-20260427-107cf710` 当前条目、计划书 [`ARCHITECTURE/plan/dsl_gen_kernel_mlir_gen_public_api_green_plan.md`](../../../../../../ARCHITECTURE/plan/dsl_gen_kernel_mlir_gen_public_api_green_plan.md) 与本任务记录。
- 已按当前审查规则继续核对：
  - `test_call_nn.py` 是否已经完全收回到 `emit` 包根公开入口
  - [`call_nn.py`](../../../../../../kernel_gen/dsl/mlir_gen/emit/call_nn.py) 文件级 `API` 列表是否已经与 `spec` 对齐
  - 当前 residual diff 是否还存在跨文件非公开 `API` 使用

### 真实审查

- 当前 residual diff 仍只包含：
  - [`kernel_gen/dsl/mlir_gen/emit/call_nn.py`](../../../../../../kernel_gen/dsl/mlir_gen/emit/call_nn.py)
  - [`test/dsl/ast/test_package.py`](../../../../../../test/dsl/ast/test_package.py)
  - [`test/dsl/ast/test_visitor_integration.py`](../../../../../../test/dsl/ast/test_visitor_integration.py)
  - [`test/dsl/mlir_gen/emit/test_call_nn.py`](../../../../../../test/dsl/mlir_gen/emit/test_call_nn.py)
- 这轮已确认收口：
  - [`test_call_nn.py`](../../../../../../test/dsl/mlir_gen/emit/test_call_nn.py) 只通过 [`kernel_gen.dsl.mlir_gen.emit`](../../../../../../kernel_gen/dsl/mlir_gen/emit/__init__.py) 包根公开入口使用 `EmitContext` / `emit_mlir`
  - 不再直连 `emit.core`、`emit.context`、`emit.call_nn` 的未公开入口
  - [`call_nn.py`](../../../../../../kernel_gen/dsl/mlir_gen/emit/call_nn.py) 顶部 `API 列表` 已收口为“无（当前文件不单独承载公开 API；公开入口见 `emit_mlir(node, ctx)`）”
  - 该写法现在与 [`spec/dsl/emit_mlir.md`](../../../../../../spec/dsl/emit_mlir.md) 顶部 `API 列表` 一致，不再额外自我公开 `infer_nn_type(...)` / `emit_nn_call(...)`
- 继续确认未回退：
  - [`test_package.py`](../../../../../../test/dsl/ast/test_package.py) / [`test_visitor_integration.py`](../../../../../../test/dsl/ast/test_visitor_integration.py) 仍只通过公开或已定义模块级接口观察行为
  - `parse_function_with_env(...)` 继续通过 [`kernel_gen.dsl.ast.parser`](../../../../../../kernel_gen/dsl/ast/parser.py) 模块入口使用，未回退到 `mlir_gen` 包根私有 helper

### Diff 反推审查

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/ast/test_package.py /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/ast/test_visitor_integration.py /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/mlir_gen/emit/test_call_nn.py -ra`
  - 结果：`220 passed, 1 warning`
- `rg -n "from kernel_gen\\.dsl\\.mlir_gen\\.emit\\.core import|from kernel_gen\\.dsl\\.mlir_gen\\.emit\\.context import|from kernel_gen\\.dsl\\.mlir_gen\\.emit\\.call_nn import|importlib\\.import_module\\(\\\"kernel_gen\\.dsl\\.mlir_gen\\.emit\\.call_nn\\\"\\)" /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/mlir_gen/emit/test_call_nn.py`
  - 结果：无命中
- `git -C /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3 diff --check`
  - 结果：通过

### 合同验收

- 未执行 `expectation`
- 原因：本轮任务边界仍是公开 `pytest` 与实现公开边界收口，`expectation` 继续只作合同验收资产单列

### 审查结论

- `通过`
- 当前 residual diff 内没有再发现可直接执行的一线改进项；`call_nn.py` 文件级 `API` 列表、`test_call_nn.py` 公开入口边界与对应 `spec` 已完成收口，可以推进到 `merge`
   - 位置：[`test/dsl/ast/test_visitor_integration.py:166`](../../../../../../test/dsl/ast/test_visitor_integration.py) 到 [`test/dsl/ast/test_visitor_integration.py:170`](../../../../../../test/dsl/ast/test_visitor_integration.py)、[`test/dsl/ast/test_package.py:139`](../../../../../../test/dsl/ast/test_package.py) 到 [`test/dsl/ast/test_package.py:143`](../../../../../../test/dsl/ast/test_package.py)
   - 现状：虽然 `_build_signature_types` 已移除，但 `_is_symbol_scalar_function`、`_parse_function_with_env`、`_symbol_expr_from_runtime_arg`、`_validate_return_type` 仍被这两份测试跨文件导入。
   - 合同依据：[`spec/dsl/mlir_gen.md:59`](../../../../../../spec/dsl/mlir_gen.md#L59) 到 [`spec/dsl/mlir_gen.md:60`](../../../../../../spec/dsl/mlir_gen.md#L60) 已明确这些名称不是包根公开 `API`，目录外测试不得跨文件导入。
   - 现场结果：直接执行 `pytest -q test/dsl/ast/test_visitor_integration.py test/dsl/ast/test_package.py -ra` 在收集阶段失败，`ImportError` 指向 `_is_symbol_scalar_function`。

2. 两份被改测试文件仍直接导入 `kernel_gen.dsl.mlir_gen.emit.core` 的下划线 helper，公开测试边界依然未收口。
   - 位置：[`test/dsl/ast/test_visitor_integration.py:137`](../../../../../../test/dsl/ast/test_visitor_integration.py) 到 [`test/dsl/ast/test_visitor_integration.py:164`](../../../../../../test/dsl/ast/test_visitor_integration.py)、[`test/dsl/ast/test_package.py:110`](../../../../../../test/dsl/ast/test_package.py) 到 [`test/dsl/ast/test_package.py:137`](../../../../../../test/dsl/ast/test_package.py)
   - 合同依据：[`kernel_gen/dsl/mlir_gen/emit/__init__.py`](../../../../../../kernel_gen/dsl/mlir_gen/emit/__init__.py) 的文件级 `API 列表` 与 `__all__` 只公开 `EmitContext`、`emit_mlir`、`memory_type_from_memory`；`emit.core` 下划线 helper 不属于公开 `API`。
   - 说明：本轮任务虽然点名 `_build_signature_types`，但按当前审查规则，当前文件之外的非公开 `API` 使用不能因“本轮只收其中一项”而放行。

### Diff 反推审查

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/ast/test_visitor_integration.py /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/ast/test_package.py -ra`
  - 结果：`2 errors during collection`
  - 关键报错：`ImportError: cannot import name '_is_symbol_scalar_function' from 'kernel_gen.dsl.mlir_gen'`
- `rg -n "from kernel_gen\.dsl\.mlir_gen import|from kernel_gen\.dsl\.mlir_gen\.emit\.core import" test/dsl/ast/test_visitor_integration.py test/dsl/ast/test_package.py`
  - 结果：命中上述两组非公开导入位置。
- `git -C /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3 diff --check`
  - 结果：通过。

### 合同验收

- 未执行 `expectation`。
- 原因：本轮任务边界与计划正文都明确为 `pytest` 公开边界收口，`expectation` 继续只作合同验收资产单列。

### 审查结论

- `需修改`
- 当前返修只去掉了 `_build_signature_types`，但这两份测试仍跨文件导入 `kernel_gen.dsl.mlir_gen` 包根和 `emit.core` 的非公开 helper，且被改测试本身仍无法通过公开入口收集与执行。应先把这两类非公开导入一起收掉，再回到 review。

## Build 复修

- 时间：`2026-04-27 15:35:00 +0800`
- 经办人：`金铲铲大作战`

### 执行前阅读记录

- 已重读本记录的 `Review` 退回项、`TODO.md` 中 `T-20260427-107cf710` 当前条目，以及当前 worktree 里的真实 diff。
- 本轮只收：
  - `test/dsl/ast/test_package.py`
  - `test/dsl/ast/test_visitor_integration.py`
  中剩余的 `kernel_gen.dsl.mlir_gen` 包根私有 helper 与 `emit.core` 私有 helper 导入。
- 不改 `expectation`，不扩修 `test_visitor_integration.py` 里和当前私有导入清理无关的其他公开行为漂移。

### 最小功能闭环

- 清掉两份测试里剩余的 `kernel_gen.dsl.mlir_gen` 包根私有 helper 与 `emit.core` 私有 helper 依赖。
- 将直接受影响的断言改成只通过公开：
  - `kernel_gen.dsl.mlir_gen.build_func_op(...)`
  - `kernel_gen.dsl.mlir_gen.build_func_op_from_ast(...)`
  - `kernel_gen.dsl.mlir_gen.emit.EmitContext`
  - `kernel_gen.dsl.mlir_gen.emit.emit_mlir(...)`
  - `kernel_gen.dsl.mlir_gen.emit.memory_type_from_memory(...)`
  观察行为。
- 用真实 `pytest` 复跑两份公开测试，并把范围外失败单列。

### 改动文件

- [`test/dsl/ast/test_package.py`](../../../../../../test/dsl/ast/test_package.py)
- [`test/dsl/ast/test_visitor_integration.py`](../../../../../../test/dsl/ast/test_visitor_integration.py)

### Diff 反推自测

- 私有导入残留扫描：
  - `rg -n "from kernel_gen\\.dsl\\.mlir_gen import _|from kernel_gen\\.dsl\\.mlir_gen\\.emit\\.core import|import kernel_gen\\.dsl\\.mlir_gen as mlir_gen_module" test/dsl/ast/test_package.py test/dsl/ast/test_visitor_integration.py`
  - 结果：无命中
- `python3 -m py_compile /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/ast/test_package.py /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/ast/test_visitor_integration.py`
  - `exit code 0`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3:/home/lfr/kernelcode_generate pytest -q /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/ast/test_package.py /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/test/dsl/ast/test_visitor_integration.py -ra`
  - `exit code 1`
  - 结果：`199 passed, 16 failed, 1 warning`
  - 失败集中在 [`test/dsl/ast/test_visitor_integration.py`](../../../../../../test/dsl/ast/test_visitor_integration.py)，不再包含“私有导入导致 collect 失败”：
    - `build_func_op(..., globals=.../builtins=...)` 旧公开口径残留
    - arch query `-> int` 返回注解与当前 `build_func_op_from_ast(...)` 行为不一致
    - `Implicit broadcast dimension mismatch` 当前由 `kernel_gen.operation.nn` 直接抛 `ValueError`
- `git -C /home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3 diff --check`
  - `exit code 0`

### 真实自检

- 这轮 review 点名的两类私有导入已经全部清掉；当前两份测试不再跨文件导入 `kernel_gen.dsl.mlir_gen` 包根私有 helper，也不再导入 `emit.core` 下划线 helper。
- 我没有新增公开接口，也没有通过别名、反射或包装方式绕过当前“只走公开 API”的规则。
- 两份公开测试现在可以真实 collect 并执行；整文件 `pytest` 剩余 16 个失败都落在既有公开行为/旧测试口径漂移，不再是这轮私有导入边界问题。
- 本轮没有扩修 `test_visitor_integration.py` 里 `globals/builtins`、arch query、broadcast mismatch` 这三组现存公开测试问题；若要继续收整文件全绿，需要单独开范围。

### 合同验收

- 本轮未执行 `expectation`
- 原因：任务明确要求不改 `expectation`，且 `expectation` 只作为合同验收资产单列，不计入本轮 `Diff 反推自测`
