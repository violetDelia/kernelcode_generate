# context.md

## 功能简介

定义仓库统一的 xDSL `Context` 构造入口，用于 IR 文本解析、打印类工具以及需要默认 dialect 注册的 MLIR 生成入口。

## API 列表

- `build_default_context() -> xdsl.context.Context`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/core/context.md`](../../spec/core/context.md)
- `test`：[`test/tools/test_mlir_gen_compare.py`](../../test/tools/test_mlir_gen_compare.py)
- `功能实现`：[`kernel_gen/core/context.py`](../../kernel_gen/core/context.py)

## 依赖

- `xdsl.context.Context`：承载 dialect 注册集合。
- `xdsl.dialects.builtin.Builtin`
- `xdsl.dialects.func.Func`
- `xdsl.dialects.arith.Arith`
- `xdsl.dialects.scf.Scf`
- `kernel_gen.dialect.nn.Nn`
- `kernel_gen.dialect.kernel.Kernel`
- `kernel_gen.dialect.symbol.Symbol`
- `kernel_gen.dialect.tuner.Tuner`
- `kernel_gen.dialect.dma.Dma`
- `kernel_gen.dialect.arch.Arch`

## API详细说明

### `build_default_context() -> xdsl.context.Context`

- api：`build_default_context() -> xdsl.context.Context`
- 参数：无。
- 返回值：`xdsl.context.Context`。
- 使用示例：

  ```python
  from xdsl.parser import Parser
  from kernel_gen.core.context import build_default_context

  ctx = build_default_context()
  module = Parser(ctx, "builtin.module { func.func @main() { func.return } }").parse_module()
  ```
- 功能说明：构建 `default_context`。
- 注意事项：默认加载基础 dialect `builtin/func/arith/scf` 和仓库常用 dialect `nn/kernel/symbol/tuner/dma/arch`；本接口只负责 dialect 注册，不运行 pass、不做 lowering、不修复非法 IR；需要解析 `scf.if`、`symbol.for`、`dma.*`、`arch.*` 等项目内常见 IR 的工具应复用本接口，不得维护第二套默认 dialect 注册列表；`kernel_gen.core.context` 是公开导入路径，旧 `kernel_gen.context` 不作为当前公开入口；`Context` 类型来自 `xdsl.context.Context`，本模块不重新导出 `Context`。

## 测试

- 测试文件：
  - `test/tools/test_ircheck_runner.py`
  - `test/tools/test_mlir_gen_compare.py`
- 执行命令：
  - `pytest -q test/tools/test_mlir_gen_compare.py`
  - `pytest -q test/tools/test_ircheck_runner.py`

### 测试目标

- 验证 `core/context` 的公开 API、边界与错误语义。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-CORE-CONTEXT-001 | pass 改写 | run ircheck text pass ok | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_run_ircheck_text_pass_ok`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“run ircheck text pass ok”场景。 | `test_run_ircheck_text_pass_ok` |
| TC-CORE-CONTEXT-002 | pass 改写 | run ircheck text module pass ok | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_run_ircheck_text_module_pass_ok`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“run ircheck text module pass ok”场景。 | `test_run_ircheck_text_module_pass_ok` |
| TC-CORE-CONTEXT-003 | pass 改写 | run ircheck text pass ok with arch dialect | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_run_ircheck_text_pass_ok_with_arch_dialect`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“run ircheck text pass ok with arch dialect”场景。 | `test_run_ircheck_text_pass_ok_with_arch_dialect` |
| TC-CORE-CONTEXT-004 | 生成/编译 | run ircheck text unsupported compile args | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_run_ircheck_text_unsupported_compile_args`。 | 生成源码、IR 文本或编译结果体现“run ircheck text unsupported compile args”场景。 | `test_run_ircheck_text_unsupported_compile_args` |
| TC-CORE-CONTEXT-005 | 边界/异常 | run ircheck text parse error maps to exit code 2 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_parse_error_maps_to_exit_code_2`。 | “run ircheck text parse error maps to exit code 2”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_parse_error_maps_to_exit_code_2` |
| TC-CORE-CONTEXT-006 | 执行结果 | run ircheck text check not found | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_run_ircheck_text_check_not_found`。 | 命令返回码、输出、执行结果或状态变更体现“run ircheck text check not found”场景。 | `test_run_ircheck_text_check_not_found` |
| TC-CORE-CONTEXT-007 | 边界/异常 | run ircheck text check next failure | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_check_next_failure`。 | “run ircheck text check next failure”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_check_next_failure` |
| TC-CORE-CONTEXT-008 | 生成/编译 | run ircheck text emitc npu demo single symbol func | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_run_ircheck_text_emitc_npu_demo_single_symbol_func`。 | 生成源码、IR 文本或编译结果体现“run ircheck text emitc npu demo single symbol func”场景。 | `test_run_ircheck_text_emitc_npu_demo_single_symbol_func` |
| TC-CORE-CONTEXT-009 | 边界/异常 | run ircheck text check not failure between positives | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_check_not_failure_between_positives`。 | “run ircheck text check not failure between positives”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_check_not_failure_between_positives` |
| TC-CORE-CONTEXT-010 | pass 改写 | run ircheck text pass with options | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_run_ircheck_text_pass_with_options`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“run ircheck text pass with options”场景。 | `test_run_ircheck_text_pass_with_options` |
| TC-CORE-CONTEXT-011 | 边界/异常 | run ircheck text unquoted options rejected | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_unquoted_options_rejected`。 | “run ircheck text unquoted options rejected”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_unquoted_options_rejected` |
| TC-CORE-CONTEXT-012 | 生成/编译 | run ircheck text emitc cpu success | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_run_ircheck_text_emitc_cpu_success`。 | 生成源码、IR 文本或编译结果体现“run ircheck text emitc cpu success”场景。 | `test_run_ircheck_text_emitc_cpu_success` |
| TC-CORE-CONTEXT-013 | 边界/异常 | run ircheck text emitc npu demo failure keeps IR | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_emitc_npu_demo_failure_keeps_ir`。 | “run ircheck text emitc npu demo failure keeps IR”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_emitc_npu_demo_failure_keeps_ir` |
| TC-CORE-CONTEXT-014 | 生成/编译 | run ircheck text emitc npu demo plain DMA alloc success | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_run_ircheck_text_emitc_npu_demo_plain_dma_alloc_success`。 | 生成源码、IR 文本或编译结果体现“run ircheck text emitc npu demo plain DMA alloc success”场景。 | `test_run_ircheck_text_emitc_npu_demo_plain_dma_alloc_success` |
| TC-CORE-CONTEXT-015 | 边界/异常 | run ircheck text emitc invalid target | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_emitc_invalid_target`。 | “run ircheck text emitc invalid target”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_emitc_invalid_target` |
| TC-CORE-CONTEXT-016 | 边界/异常 | run ircheck text invalid options syntax | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_invalid_options_syntax`。 | “run ircheck text invalid options syntax”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_invalid_options_syntax` |
| TC-CORE-CONTEXT-017 | pass 改写 | run ircheck text pipeline with options | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_run_ircheck_text_pipeline_with_options`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“run ircheck text pipeline with options”场景。 | `test_run_ircheck_text_pipeline_with_options` |
| TC-CORE-CONTEXT-018 | pass 改写 | run ircheck text pipeline ok | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_run_ircheck_text_pipeline_ok`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“run ircheck text pipeline ok”场景。 | `test_run_ircheck_text_pipeline_ok` |
| TC-CORE-CONTEXT-019 | 执行结果 | run ircheck text multi case ok | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_run_ircheck_text_multi_case_ok`。 | 命令返回码、输出、执行结果或状态变更体现“run ircheck text multi case ok”场景。 | `test_run_ircheck_text_multi_case_ok` |
| TC-CORE-CONTEXT-020 | 边界/异常 | run ircheck text multi case failfast marks case index | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_multi_case_failfast_marks_case_index`。 | “run ircheck text multi case failfast marks case index”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_multi_case_failfast_marks_case_index` |
| TC-CORE-CONTEXT-021 | pass 改写 | run ircheck text pass with options ok | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_run_ircheck_text_pass_with_options_ok`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“run ircheck text pass with options ok”场景。 | `test_run_ircheck_text_pass_with_options_ok` |
| TC-CORE-CONTEXT-022 | pass 改写 | run ircheck text pipeline with options ok | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_run_ircheck_text_pipeline_with_options_ok`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“run ircheck text pipeline with options ok”场景。 | `test_run_ircheck_text_pipeline_with_options_ok` |
| TC-CORE-CONTEXT-023 | 边界/异常 | run ircheck text rejects invalid option syntax | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_rejects_invalid_option_syntax`。 | “run ircheck text rejects invalid option syntax”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_rejects_invalid_option_syntax` |
| TC-CORE-CONTEXT-024 | 边界/异常 | run ircheck text rejects unquoted pass options | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_rejects_unquoted_pass_options`。 | “run ircheck text rejects unquoted pass options”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_rejects_unquoted_pass_options` |
| TC-CORE-CONTEXT-025 | 边界/异常 | run ircheck text rejects unquoted pipeline options | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_rejects_unquoted_pipeline_options`。 | “run ircheck text rejects unquoted pipeline options”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_rejects_unquoted_pipeline_options` |
| TC-CORE-CONTEXT-026 | pass 改写 | run ircheck text multi pass sequence | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_run_ircheck_text_multi_pass_sequence`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“run ircheck text multi pass sequence”场景。 | `test_run_ircheck_text_multi_pass_sequence` |
| TC-CORE-CONTEXT-027 | 边界/异常 | run ircheck text failing step reports actual IR | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_failing_step_reports_actual_ir`。 | “run ircheck text failing step reports actual IR”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_failing_step_reports_actual_ir` |
| TC-CORE-CONTEXT-028 | 执行结果 | run ircheck text variable success | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_run_ircheck_text_variable_success`。 | 命令返回码、输出、执行结果或状态变更体现“run ircheck text variable success”场景。 | `test_run_ircheck_text_variable_success` |
| TC-CORE-CONTEXT-029 | 边界/异常 | run ircheck text invalid variable regex maps to exit code 2 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_invalid_variable_regex_maps_to_exit_code_2`。 | “run ircheck text invalid variable regex maps to exit code 2”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_invalid_variable_regex_maps_to_exit_code_2` |
| TC-CORE-CONTEXT-030 | 执行结果 | run ircheck text unclosed escaped variable maps to exit code 2 | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_run_ircheck_text_unclosed_escaped_variable_maps_to_exit_code_2`。 | 命令返回码、输出、执行结果或状态变更体现“run ircheck text unclosed escaped variable maps to exit code 2”场景。 | `test_run_ircheck_text_unclosed_escaped_variable_maps_to_exit_code_2` |
| TC-CORE-CONTEXT-031 | 执行结果 | run ircheck text escaped double brackets literal ok | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_run_ircheck_text_escaped_double_brackets_literal_ok`。 | 命令返回码、输出、执行结果或状态变更体现“run ircheck text escaped double brackets literal ok”场景。 | `test_run_ircheck_text_escaped_double_brackets_literal_ok` |
| TC-CORE-CONTEXT-032 | 执行结果 | run ircheck text escaped double open brackets prefix ok | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_run_ircheck_text_escaped_double_open_brackets_prefix_ok`。 | 命令返回码、输出、执行结果或状态变更体现“run ircheck text escaped double open brackets prefix ok”场景。 | `test_run_ircheck_text_escaped_double_open_brackets_prefix_ok` |
| TC-CORE-CONTEXT-033 | 执行结果 | run ircheck text check not define variable maps to exit code 2 | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_run_ircheck_text_check_not_define_variable_maps_to_exit_code_2`。 | 命令返回码、输出、执行结果或状态变更体现“run ircheck text check not define variable maps to exit code 2”场景。 | `test_run_ircheck_text_check_not_define_variable_maps_to_exit_code_2` |
| TC-CORE-CONTEXT-034 | 执行结果 | run ircheck text variables are case local | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_run_ircheck_text_variables_are_case_local`。 | 命令返回码、输出、执行结果或状态变更体现“run ircheck text variables are case local”场景。 | `test_run_ircheck_text_variables_are_case_local` |
| TC-CORE-CONTEXT-035 | 执行结果 | run ircheck text reg alias matches ssa ids | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_run_ircheck_text_reg_alias_matches_ssa_ids`。 | 命令返回码、输出、执行结果或状态变更体现“run ircheck text reg alias matches ssa ids”场景。 | `test_run_ircheck_text_reg_alias_matches_ssa_ids` |
| TC-CORE-CONTEXT-036 | 执行结果 | run ircheck text val alias matches identifiers | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_run_ircheck_text_val_alias_matches_identifiers`。 | 命令返回码、输出、执行结果或状态变更体现“run ircheck text val alias matches identifiers”场景。 | `test_run_ircheck_text_val_alias_matches_identifiers` |
| TC-CORE-CONTEXT-037 | 执行结果 | run ircheck text numeric ssa signature keeps colon tight | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_run_ircheck_text_numeric_ssa_signature_keeps_colon_tight`。 | 命令返回码、输出、执行结果或状态变更体现“run ircheck text numeric ssa signature keeps colon tight”场景。 | `test_run_ircheck_text_numeric_ssa_signature_keeps_colon_tight` |
| TC-CORE-CONTEXT-038 | 生成/编译 | run ircheck text emitc cpu matches generated source | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_run_ircheck_text_emitc_cpu_matches_generated_source`。 | 生成源码、IR 文本或编译结果体现“run ircheck text emitc cpu matches generated source”场景。 | `test_run_ircheck_text_emitc_cpu_matches_generated_source` |
| TC-CORE-CONTEXT-039 | 边界/异常 | run ircheck text emitc cpu match failure reports generated source | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_emitc_cpu_match_failure_reports_generated_source`。 | “run ircheck text emitc cpu match failure reports generated source”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_emitc_cpu_match_failure_reports_generated_source` |
| TC-CORE-CONTEXT-040 | 边界/异常 | run ircheck text emitc npu demo maps generation failure | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_run_ircheck_text_emitc_npu_demo_maps_generation_failure`。 | “run ircheck text emitc npu demo maps generation failure”场景按公开错误语义失败或被拒绝。 | `test_run_ircheck_text_emitc_npu_demo_maps_generation_failure` |
| TC-CORE-CONTEXT-041 | 解析/打印 | build default context parses scf if | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_build_default_context_parses_scf_if`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_build_default_context_parses_scf_if` |
| TC-CORE-CONTEXT-042 | 公开入口 | MLIR gen compare true | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_mlir_gen_compare_true`。 | 公开入口在“MLIR gen compare true”场景下可导入、构造、注册或按名称发现。 | `test_mlir_gen_compare_true` |
| TC-CORE-CONTEXT-043 | 公开入口 | compare MLIR file alias true | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_compare_mlir_file_alias_true`。 | 公开入口在“compare MLIR file alias true”场景下可导入、构造、注册或按名称发现。 | `test_compare_mlir_file_alias_true` |
| TC-CORE-CONTEXT-044 | 边界/异常 | MLIR gen compare returns false on mismatch | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_mlir_gen_compare_returns_false_on_mismatch`。 | “MLIR gen compare returns false on mismatch”场景按公开错误语义失败或被拒绝。 | `test_mlir_gen_compare_returns_false_on_mismatch` |
| TC-CORE-CONTEXT-045 | 边界/异常 | MLIR gen compare returns false on invalid text | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_mlir_gen_compare_returns_false_on_invalid_text`。 | “MLIR gen compare returns false on invalid text”场景按公开错误语义失败或被拒绝。 | `test_mlir_gen_compare_returns_false_on_invalid_text` |
| TC-CORE-CONTEXT-046 | 解析/打印 | MLIR gen compare returns false on non utf8 text | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_mlir_gen_compare_returns_false_on_non_utf8_text`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_mlir_gen_compare_returns_false_on_non_utf8_text` |
| TC-CORE-CONTEXT-047 | 公开入口 | MLIR gen compare true with arith | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_mlir_gen_compare_true_with_arith`。 | 公开入口在“MLIR gen compare true with arith”场景下可导入、构造、注册或按名称发现。 | `test_mlir_gen_compare_true_with_arith` |
| TC-CORE-CONTEXT-048 | 边界/异常 | MLIR gen compare returns false on normalize parse error | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_mlir_gen_compare_returns_false_on_normalize_parse_error`。 | “MLIR gen compare returns false on normalize parse error”场景按公开错误语义失败或被拒绝。 | `test_mlir_gen_compare_returns_false_on_normalize_parse_error` |
| TC-CORE-CONTEXT-049 | 解析/打印 | default context loads required dialects | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_default_context_loads_required_dialects`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_default_context_loads_required_dialects` |
| TC-CORE-CONTEXT-050 | 公开入口 | MLIR gen compare returns false when actual not module | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_mlir_gen_compare_returns_false_when_actual_not_module`。 | 公开入口在“MLIR gen compare returns false when actual not module”场景下可导入、构造、注册或按名称发现。 | `test_mlir_gen_compare_returns_false_when_actual_not_module` |
| TC-CORE-CONTEXT-051 | 执行结果 | MLIR gen compare does not repair legacy DMA view result dtype | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_mlir_gen_compare_does_not_repair_legacy_dma_view_result_dtype`。 | 命令返回码、输出、执行结果或状态变更体现“MLIR gen compare does not repair legacy DMA view result dtype”场景。 | `test_mlir_gen_compare_does_not_repair_legacy_dma_view_result_dtype` |
| TC-CORE-CONTEXT-052 | 内存/DMA | MLIR gen compare text handles memory floor div expr | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_mlir_gen_compare_text_handles_memory_floor_div_expr`。 | 内存类型、布局、搬运结果或 verifier 行为体现“MLIR gen compare text handles memory floor div expr”场景。 | `test_mlir_gen_compare_text_handles_memory_floor_div_expr` |
| TC-CORE-CONTEXT-053 | 边界/异常 | MLIR gen compare text rejects memory floor div mismatch | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_mlir_gen_compare_text_rejects_memory_floor_div_mismatch`。 | “MLIR gen compare text rejects memory floor div mismatch”场景按公开错误语义失败或被拒绝。 | `test_mlir_gen_compare_text_rejects_memory_floor_div_mismatch` |
| TC-CORE-CONTEXT-054 | 解析/打印 | MLIR gen compare text true | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_mlir_gen_compare_text_true`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_mlir_gen_compare_text_true` |
| TC-CORE-CONTEXT-055 | 内存/DMA | MLIR gen compare text ignores line comment slashes for memory types | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_mlir_gen_compare_text_ignores_line_comment_slashes_for_memory_types`。 | 内存类型、布局、搬运结果或 verifier 行为体现“MLIR gen compare text ignores line comment slashes for memory types”场景。 | `test_mlir_gen_compare_text_ignores_line_comment_slashes_for_memory_types` |
| TC-CORE-CONTEXT-056 | 边界/异常 | MLIR gen compare text returns false on invalid text | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_mlir_gen_compare_text_returns_false_on_invalid_text`。 | “MLIR gen compare text returns false on invalid text”场景按公开错误语义失败或被拒绝。 | `test_mlir_gen_compare_text_returns_false_on_invalid_text` |
