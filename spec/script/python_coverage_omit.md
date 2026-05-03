# python_coverage_omit.md

## 功能简介

- 记录 `script/check_python_coverage.py` 在全量与 scoped gate 中统一使用的 coverage omit 清单。
- 既覆盖纯转发 / 薄包装文件，也覆盖“只通过包根公开 API 验证行为”的内部实现拆分文件。
- 该清单只定义 coverage gate 排除范围，不改变公开 API、pytest 边界或合同验收入口。

## API 列表

- `coverage_omit.paths: tuple[str, ...]`
- `coverage_omit.selection_rules: tuple[str, ...]`
- `coverage_omit.exclusion_rules: tuple[str, ...]`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/script/python_coverage_omit.md`](../../spec/script/python_coverage_omit.md)
- `功能实现`：[`script/check_python_coverage.py`](../../script/check_python_coverage.py)
- `test`：[`test/script/test_python_coverage_omit.py`](../../test/script/test_python_coverage_omit.py)

## 依赖

- [`spec/script/python_coverage_check.md`](../../spec/script/python_coverage_check.md)：coverage gate 工具入口合同。

## API详细说明

### `coverage_omit.paths: tuple[str, ...]`

- api：`coverage_omit.paths: tuple[str, ...]`
- 参数：无。
- 返回值：`tuple[str, ...]`，列出 coverage gate 排除的仓库相对路径。
- 使用示例：

  ```bash
  PYTHONPATH=. python3 script/check_python_coverage.py --module kernel_gen
  ```
- 功能说明：定义 `script/check_python_coverage.py` 在全量与 scoped gate 中统一应用的 omit 路径集合。
- 注意事项：路径必须是仓库相对路径；列入 omit 的文件不得承载独立公开 API、稳定 CLI 入口、公开错误类型或需要单独计入 coverage 的对外行为；清单如下。

| 路径 | 排除理由 | 覆盖率影响 |
| --- | --- | --- |
| `kernel_gen/dsl/__init__.py` | 仅汇总 DSL 公开入口 | 不计入 line / branch 阈值 |
| `kernel_gen/dsl/ast/__init__.py` | 仅转发 AST 公开接口 | 不计入 line / branch 阈值 |
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

### `coverage_omit.selection_rules: tuple[str, ...]`

- api：`coverage_omit.selection_rules: tuple[str, ...]`
- 参数：无。
- 返回值：`tuple[str, ...]`，列出路径可进入 omit 清单的稳定选择规则。
- 使用示例：

  ```bash
  PYTHONPATH=. python3 script/check_python_coverage.py --module kernel_gen --include-module kernel_gen.dsl
  ```
- 功能说明：定义新增 omit 项必须满足的选择条件。
- 注意事项：文件只包含模块 docstring、注释、`import` / `from ... import ...`、`__all__`、类型检查保护导入、简单别名绑定，或仅承载由包根公开 API 调度的内部拆分逻辑时，才可列入 omit；若文件本身未在对应 `spec` 和文件级 `API 列表` 中声明为公开 API，且行为只通过包根公开入口验收，也可列入 omit。

### `coverage_omit.exclusion_rules: tuple[str, ...]`

- api：`coverage_omit.exclusion_rules: tuple[str, ...]`
- 参数：无。
- 返回值：`tuple[str, ...]`，列出不得进入 omit 清单的稳定排除条件。
- 使用示例：

  ```bash
  PYTHONPATH=. python3 script/check_python_coverage.py --module kernel_gen
  ```
- 功能说明：定义 coverage omit 清单的排除边界。
- 注意事项：承载独立公开 API、稳定 CLI 入口、公开错误类型、注册副作用、对外可直接 import 契约，或其公开行为需单独计入 coverage 的文件，不得列入 omit；`kernel_gen/__init__.py`、`kernel_gen/dialect/__init__.py`、`kernel_gen/dsl/gen_kernel/__init__.py`、`kernel_gen/dsl/gen_kernel/emit/__init__.py`、`kernel_gen/passes/lowering/__init__.py` 与 `kernel_gen/dsl/ast/mlir_gen.py` 不在 omit 清单内；已删除的 `kernel_gen/dsl/ast/emit_context.py` 与 `kernel_gen/dsl/ast/emit_nn.py` 不得作为 omit 清单项。

## 额外补充

### 使用方式

- 本文件作为内部拆分文件不计入 coverage gate 的公开合同真源。
- `script/check_python_coverage.py` 必须先应用本清单，再汇总全量 `kernel_gen` 或 `--include-module` 范围。

## 测试

- 测试文件：`test/script/test_python_coverage_omit.py`
- 执行命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/script/test_python_coverage_omit.py`

### 测试目标

- 验证 coverage omit 清单与 `script/check_python_coverage.py` 的公开排除行为一致。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-SCRIPT-PYTHON-COVERAGE-OMIT-001 | 公开入口 | 清单中路径被 coverage gate 排除。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `PCO-001`。 | 公开入口在“清单中路径被 coverage gate 排除。”场景下可导入、构造、注册或按名称发现。 | `PCO-001` |
| TC-SCRIPT-PYTHON-COVERAGE-OMIT-002 | 公开入口 | 未列入清单且承载公开入口的文件继续计入 coverage gate。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `PCO-002`。 | 公开入口在“未列入清单且承载公开入口的文件继续计入 coverage gate。”场景下可导入、构造、注册或按名称发现。 | `PCO-002` |
| TC-SCRIPT-PYTHON-COVERAGE-OMIT-003 | 公开入口 | 已删除文件不得继续作为 omit 清单项。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `PCO-003`。 | 公开入口在“已删除文件不得继续作为 omit 清单项。”场景下可导入、构造、注册或按名称发现。 | `PCO-003` |
