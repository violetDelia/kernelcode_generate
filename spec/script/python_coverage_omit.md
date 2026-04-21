# python_coverage_omit.md

## 功能简介

- 记录 S1/S7 统一使用的 `coverage omit` 清单。
- 只收录 `kernel_gen` 内纯转发 / 薄包装文件。
- 该清单用于解释为什么某些文件不进入 line / branch 阈值统计。

## 文档信息

- 创建者：`金铲铲大作战`
- 最后一次更改：`金铲铲大作战`
- `spec`：[`spec/script/python_coverage_omit.md`](../../spec/script/python_coverage_omit.md)
- `spec`：[`spec/script/python_coverage_check.md`](../../spec/script/python_coverage_check.md)
- `功能实现`：[`script/check_python_coverage.py`](../../script/check_python_coverage.py)
- `test`：[`test/script/test_python_coverage_omit.py`](../../test/script/test_python_coverage_omit.py)

## 选择标准

- 文件只包含模块 docstring、注释、`import` / `from ... import ...`、`__all__`、类型检查保护导入或简单别名绑定。
- 文件不包含分支、循环、异常处理、函数/类实现、注册副作用、路径解析、IR 构造、字符串生成、环境读取、IO、warning 过滤或业务判断。
- 只要文件中出现上述非平凡逻辑，就不得列入 omit。

## Omit 清单

| 路径 | 排除理由 | 覆盖率影响 |
| --- | --- | --- |
| `kernel_gen/common/__init__.py` | 仅导出 `_ERROR_TEMPLATE`，无分支或业务逻辑 | 仅保留导出胶水，不计入 line / branch 阈值 |
| `kernel_gen/dsl/__init__.py` | 仅汇总 DSL 公开入口，无实现逻辑 | 仅保留导出胶水，不计入 line / branch 阈值 |
| `kernel_gen/dsl/ast/__init__.py` | 仅转发 AST 公开接口 | 仅保留导出胶水，不计入 line / branch 阈值 |
| `kernel_gen/dsl/mlir_gen/__init__.py` | 仅汇总 mlir_gen 公开入口 | 仅保留导出胶水，不计入 line / branch 阈值 |
| `kernel_gen/execute_engine/__init__.py` | 仅转发执行引擎公开入口 | 仅保留导出胶水，不计入 line / branch 阈值 |
| `kernel_gen/operation/__init__.py` | 仅汇总 operation 公开入口 | 仅保留导出胶水，不计入 line / branch 阈值 |
| `kernel_gen/passes/__init__.py` | 仅转发 pass 公共入口，无独立算法实现 | 仅保留导出胶水，不计入 line / branch 阈值 |
| `kernel_gen/passes/analysis/__init__.py` | 仅转发 analysis pass 公开入口 | 仅保留导出胶水，不计入 line / branch 阈值 |
| `kernel_gen/passes/pipeline/__init__.py` | 仅汇总 pipeline builder 入口 | 仅保留导出胶水，不计入 line / branch 阈值 |
| `kernel_gen/passes/tuning/__init__.py` | 仅转发 tuning pass 入口 | 仅保留导出胶水，不计入 line / branch 阈值 |
| `kernel_gen/passes/lowering/nn_lowering/__init__.py` | 仅转发 `NnLoweringPass` 入口 | 仅保留导出胶水，不计入 line / branch 阈值 |
| `kernel_gen/symbol_variable/__init__.py` | 仅汇总 symbol_variable 公开入口 | 仅保留导出胶水，不计入 line / branch 阈值 |
| `kernel_gen/tools/__init__.py` | 仅转发工具入口，无独立业务逻辑 | 仅保留导出胶水，不计入 line / branch 阈值 |

## 排除边界

- `kernel_gen/__init__.py` 不在 omit 清单内，因为它包含惰性导出分发逻辑。
- `kernel_gen/dialect/__init__.py` 不在 omit 清单内，因为它包含惰性导入与缓存逻辑。
- `kernel_gen/dsl/gen_kernel/__init__.py` 不在 omit 清单内，因为它包含兼容包装与发射分发逻辑。
- `kernel_gen/dsl/gen_kernel/emit_c/__init__.py` 不在 omit 清单内，因为它包含注册、副作用与旧实现回退逻辑。
- `kernel_gen/passes/lowering/__init__.py` 不在 omit 清单内，因为它包含兼容 alias 与 `sys.modules` 注册。
- `kernel_gen/dsl/mlir_gen/emit/__init__.py` 不在 omit 清单内，因为它包含 `memory_type_from_memory` 的函数实现。

## 使用方式

- 在 S1 阶段用作“薄包装不计入 coverage 阈值”的人工审计清单。
- 在 S7 / 终验阶段按本清单复核 coverage 输出与阈值计算范围。
