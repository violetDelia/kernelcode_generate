# python_coverage_omit.md

## 功能简介

- 记录 `script/check_python_coverage.py` 在全量与 scoped gate 中统一使用的 coverage omit 清单。
- 既覆盖纯转发 / 薄包装文件，也覆盖“只通过包根公开 API 验证行为”的内部实现拆分文件。
- 该清单只定义 coverage gate 排除范围，不改变公开 API、pytest 边界或合同验收入口。

## API 列表

- `coverage omit 清单`
- `选择标准`
- `排除边界`

## 文档信息

- 创建者：`金铲铲大作战`
- 最后一次更改：`金铲铲大作战`
- `spec`：[`spec/script/python_coverage_omit.md`](../../spec/script/python_coverage_omit.md)
- `spec`：[`spec/script/python_coverage_check.md`](../../spec/script/python_coverage_check.md)
- `功能实现`：[`script/check_python_coverage.py`](../../script/check_python_coverage.py)
- `test`：[`test/script/test_python_coverage_omit.py`](../../test/script/test_python_coverage_omit.py)

## 选择标准

- 文件只包含模块 docstring、注释、`import` / `from ... import ...`、`__all__`、类型检查保护导入、简单别名绑定，或仅承载“由包根公开 API 调度的内部拆分逻辑”。
- 若文件本身未在对应 `spec` 和文件级 `API 列表` 中声明为公开 API，且行为只通过包根公开入口验收，则可列入 omit。
- 只要文件本身承载独立公开 API、稳定 CLI 入口、公开错误类型、注册副作用、对外可直接 import 的契约，或其公开行为需单独计入 coverage，则不得列入 omit。

## Omit 清单

| 路径 | 排除理由 | 覆盖率影响 |
| --- | --- | --- |
| `kernel_gen/common/__init__.py` | 仅导出 `_ERROR_TEMPLATE`，无独立公开逻辑 | 不计入 line / branch 阈值 |
| `kernel_gen/dsl/__init__.py` | 仅汇总 DSL 公开入口 | 不计入 line / branch 阈值 |
| `kernel_gen/dsl/ast/__init__.py` | 仅转发 AST 公开接口 | 不计入 line / branch 阈值 |
| `kernel_gen/dsl/mlir_gen/__init__.py` | 仅汇总 mlir_gen 公开入口 | 不计入 line / branch 阈值 |
| `kernel_gen/dsl/mlir_gen/parse_env.py` | 仅为 `build_func_op(...)` / `mlir_gen(...)` 提供内部解析环境辅助逻辑 | 不计入 line / branch 阈值 |
| `kernel_gen/dsl/mlir_gen/signature.py` | 仅为 `build_func_op(...)` / `mlir_gen(...)` 提供内部签名辅助逻辑 | 不计入 line / branch 阈值 |
| `kernel_gen/dsl/mlir_gen/emit/call_arch.py` | `emit_mlir(...)` 的 arch family 内部拆分实现 | 不计入 line / branch 阈值 |
| `kernel_gen/dsl/mlir_gen/emit/call_dma.py` | `emit_mlir(...)` 的 dma family 内部拆分实现 | 不计入 line / branch 阈值 |
| `kernel_gen/dsl/mlir_gen/emit/call_nn.py` | `emit_mlir(...)` 的 nn family 内部拆分实现 | 不计入 line / branch 阈值 |
| `kernel_gen/dsl/mlir_gen/emit/call_symbol.py` | `emit_mlir(...)` 的 symbol family 内部拆分实现 | 不计入 line / branch 阈值 |
| `kernel_gen/dsl/mlir_gen/emit/core.py` | `kernel_gen.dsl.mlir_gen.emit` 包根公开 facade 背后的内部 lowering 拆分实现 | 不计入 line / branch 阈值 |
| `kernel_gen/dsl/mlir_gen/emit/control_flow.py` | `emit_mlir(...)` 的 control-flow 内部拆分实现 | 不计入 line / branch 阈值 |
| `kernel_gen/dsl/mlir_gen/emit/shape_utils.py` | `emit_mlir(...)` 共享的 shape/index 内部辅助逻辑 | 不计入 line / branch 阈值 |
| `kernel_gen/dsl/mlir_gen/emit/type_utils.py` | `emit_mlir(...)` 共享的类型推导内部辅助逻辑 | 不计入 line / branch 阈值 |
| `kernel_gen/dsl/mlir_gen/emit/value.py` | `emit_mlir(...)` 共享的 value 内部辅助逻辑 | 不计入 line / branch 阈值 |
| `kernel_gen/dsl/mlir_gen/function_builder.py` | `kernel_gen.dsl.mlir_gen` 包根公开 `build_func_op(...)` / `build_func_op_from_ast(...)` 的内部实现拆分 | 不计入 line / branch 阈值 |
| `kernel_gen/dsl/mlir_gen/module_builder.py` | `kernel_gen.dsl.mlir_gen` 包根公开 `MlirGenModuleError(...)` / `mlir_gen(...)` 的内部实现拆分 | 不计入 line / branch 阈值 |
| `kernel_gen/execute_engine/__init__.py` | 仅转发执行引擎公开入口 | 不计入 line / branch 阈值 |
| `kernel_gen/operation/__init__.py` | 仅汇总 operation 公开入口 | 不计入 line / branch 阈值 |
| `kernel_gen/operation/nn/common.py` | `kernel_gen.operation.nn` 各公开 helper 共享的内部校验与类型辅助逻辑 | 不计入 line / branch 阈值 |
| `kernel_gen/passes/__init__.py` | 仅转发 pass 公共入口，无独立算法实现 | 不计入 line / branch 阈值 |
| `kernel_gen/passes/analysis/__init__.py` | 仅转发 analysis pass 公开入口 | 不计入 line / branch 阈值 |
| `kernel_gen/passes/pipeline/__init__.py` | 仅汇总 pipeline builder 入口 | 不计入 line / branch 阈值 |
| `kernel_gen/passes/tuning/__init__.py` | 仅转发 tuning pass 入口 | 不计入 line / branch 阈值 |
| `kernel_gen/passes/lowering/nn_lowering/__init__.py` | 仅转发 `NnLoweringPass` 入口 | 不计入 line / branch 阈值 |
| `kernel_gen/symbol_variable/__init__.py` | 仅汇总 symbol_variable 公开入口 | 不计入 line / branch 阈值 |
| `kernel_gen/tools/__init__.py` | 仅转发工具入口，无独立业务逻辑 | 不计入 line / branch 阈值 |
| `kernel_gen/dsl/gen_kernel/emit/cpu/__init__.py` | 仅承载 CPU target 私有 emit 注册实现 | 不计入 line / branch 阈值 |
| `kernel_gen/dsl/gen_kernel/emit/npu_demo/name.py` | 仅承载 npu_demo target 私有命名注册实现 | 不计入 line / branch 阈值 |
| `kernel_gen/dsl/gen_kernel/emit/npu_demo/symbol/cast.py` | 仅承载 npu_demo target 私有 `symbol.cast` 注册实现 | 不计入 line / branch 阈值 |
| `kernel_gen/dsl/gen_kernel/emit/npu_demo/symbol/const.py` | 仅承载 npu_demo target 私有 `symbol.const` 注册实现 | 不计入 line / branch 阈值 |
| `kernel_gen/dsl/gen_kernel/emit/npu_demo/symbol/for_loop.py` | 仅承载 npu_demo target 私有 `symbol.for` 注册实现 | 不计入 line / branch 阈值 |

## 排除边界

- `kernel_gen/__init__.py` 不在 omit 清单内，因为它承载惰性导出分发逻辑。
- `kernel_gen/dialect/__init__.py` 不在 omit 清单内，因为它承载惰性导入与缓存逻辑。
- `kernel_gen/dsl/gen_kernel/__init__.py` 不在 omit 清单内，因为它承载兼容包装与发射分发逻辑。
- `kernel_gen/dsl/gen_kernel/emit/__init__.py` 不在 omit 清单内，因为它承载 target 分发与公开 emit 合同。
- `kernel_gen/passes/lowering/__init__.py` 不在 omit 清单内，因为它承载兼容 alias 与 `sys.modules` 注册。
- `kernel_gen/dsl/mlir_gen/emit/__init__.py` 不在 omit 清单内，因为它承载 `EmitContext(...)`、`emit_mlir(...)` 与 `memory_type_from_memory(...)` 公开入口。

## 使用方式

- 在 S6 阶段用作 “内部拆分文件不计入 coverage gate” 的公开合同真源。
- 在 `script/check_python_coverage.py` 中先应用本清单，再汇总全量 `kernel_gen` 或 `--include-module` 范围。
