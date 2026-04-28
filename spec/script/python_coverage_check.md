# python_coverage_check.md

## 功能简介

- 定义 `script/check_python_coverage.py` 的公开合同。
- 读取 `coverage.py` 生成的 JSON 报告，检查 Python 项目的 line / branch 覆盖率阈值。
- 支持按 `kernel_gen` 模块前缀做阶段内 scoped 验收，不把合同验收资产、`test/`、`spec/` 计入本轮阈值。

## API 列表

- `CoverageCheckError(message: str)`
- `check_coverage(report_path: Path, line_min: float, branch_min: float, include_modules: list[str]) -> dict[str, Any]`
- `main(argv: list[str] | None = None) -> int`

## 文档信息

- 创建者：`金铲铲大作战`
- 最后一次更改：`朽木露琪亚`
- `spec`：[`spec/script/python_coverage_check.md`](../../spec/script/python_coverage_check.md)
- `spec`：[`spec/script/python_coverage_omit.md`](../../spec/script/python_coverage_omit.md)
- `功能实现`：[`script/check_python_coverage.py`](../../script/check_python_coverage.py)
- `test`：[`test/script/test_python_coverage_check.py`](../../test/script/test_python_coverage_check.py)

## 依赖

- coverage 入口：[`coverage json`](https://coverage.readthedocs.io/)
- 任务计划：[`ARCHITECTURE/plan/python_spec_impl_test_refactor_green_plan.md`](../../ARCHITECTURE/plan/python_spec_impl_test_refactor_green_plan.md)

## 目标

- 为 S1 / S7 提供稳定的覆盖率阈值检查入口。
- 允许阶段内按 `--include-module` 只检查指定 `kernel_gen` 模块前缀或单文件模块路径。
- 对缺失或损坏的 coverage JSON 明确失败，不把不完整报告误判为通过。

## 限制与边界

- 仅处理 `coverage.py` JSON 报告，不负责生成覆盖率数据。
- 不读取合同验收资产目录，也不把合同验收资产纳入覆盖率目标。
- 不替代 `pytest`，只负责 coverage 阈值校验。

## helper 清单

- `_build_parser()`
- `_load_report(path: Path)`
- `_normalize_module_prefix(module: str)`
- `_path_matches_module(path: str, module: str)`
- `_require_int(value: Any, field: str, scope: str)`
- `_summary_metrics(summary: Any, scope: str)`
- `_select_scope(report: dict[str, Any], include_modules: list[str])`
- `_percentage(covered: int, total: int)`
- `_format_summary(scope: str, line_pct: float, branch_pct: float)`
- `_validate_thresholds(line_pct: float, branch_pct: float, line_min: float, branch_min: float)`

## 测试

- 测试文件：[`test/script/test_python_coverage_check.py`](../../test/script/test_python_coverage_check.py)
- 执行命令：

```bash
pytest -q test/script/test_python_coverage_check.py
```

- 功能与用例清单：
  - 阈值通过。
  - line 不足。
  - branch 不足。
  - JSON 缺字段。
  - `--include-module` 只检查指定模块前缀。
  - `--include-module` 支持单文件模块路径，例如 `kernel_gen.tools.dsl_run`。
