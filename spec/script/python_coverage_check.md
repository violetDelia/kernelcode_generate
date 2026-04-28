# python_coverage_check.md

## 功能简介

- 定义 [`script/check_python_coverage.py`](../../script/check_python_coverage.py) 的公开合同。
- 读取 `coverage.py` 生成的 JSON 报告，检查 Python 项目的 line / branch 覆盖率阈值。
- 支持按 `kernel_gen` 模块前缀做阶段内 scoped 验收，并在 `files` 级汇总前先应用 [`python_coverage_omit.md`](../../spec/script/python_coverage_omit.md) 的排除清单。

## API 列表

- `CoverageCheckError(message: str)`
- `check_coverage(report_path: Path, line_min: float, branch_min: float, include_modules: list[str]) -> dict[str, Any]`
- `main(argv: list[str] | None = None) -> int`

## 文档信息

- 创建者：`金铲铲大作战`
- 最后一次更改：`金铲铲大作战`
- `spec`：[`spec/script/python_coverage_check.md`](../../spec/script/python_coverage_check.md)
- `spec`：[`spec/script/python_coverage_omit.md`](../../spec/script/python_coverage_omit.md)
- `功能实现`：[`script/check_python_coverage.py`](../../script/check_python_coverage.py)
- `test`：[`test/script/test_python_coverage_check.py`](../../test/script/test_python_coverage_check.py)

## 目标

- 为 coverage gate 提供稳定的 line / branch 阈值检查入口。
- 允许阶段内按 `--include-module` 只检查指定 `kernel_gen` 模块前缀或单文件模块路径。
- 对缺失、损坏或字段不完整的 coverage JSON 明确失败，不把不完整报告误判为通过。

## 限制与边界

- 仅处理 `coverage.py` JSON 报告，不负责生成覆盖率数据。
- 不修改 omit 清单；只读取 [`python_coverage_omit.md`](../../spec/script/python_coverage_omit.md) 作为阈值排除合同。
- 不替代 `pytest`，只负责 coverage 阈值校验。

## 公开合同

### `CoverageCheckError(message: str)`

- 覆盖率阈值检查失败或输入数据不合法时抛出的异常。

### `check_coverage(report_path: Path, line_min: float, branch_min: float, include_modules: list[str]) -> dict[str, Any]`

- 读取 coverage JSON，计算 line / branch 覆盖率。
- 当报告包含 `files` 时，先应用 omit 清单，再做 `--include-module` 过滤，最后按剩余文件汇总覆盖率。
- 仅当报告缺少 `files` 且未请求 `--include-module` 时，才回退读取 `totals`。
- 返回值固定包含：
  - `scope`
  - `covered_lines`
  - `num_statements`
  - `line_percent`
  - `covered_branches`
  - `num_branches`
  - `branch_percent`

### `main(argv: list[str] | None = None) -> int`

- 公开 CLI 入口。
- 成功返回 `0` 并打印 `coverage ok: ...` 摘要。
- 失败返回非 `0` 并向标准错误打印 `coverage check failed: ...`。

## 参数与输出

- `--coverage-json(Path)`：coverage JSON 路径。
- `--line-min(float)`：最小 line coverage 百分比。
- `--branch-min(float)`：最小 branch coverage 百分比。
- `--include-module(list[str])`：可重复指定的模块前缀；当报告包含 `files` 时，先排除 omit 清单，再从剩余文件中筛选匹配项。
  - 支持精确到单文件模块路径，例如 `kernel_gen.passes.example`。
  - 若精确模块路径命中的文件已列入 [`python_coverage_omit.md`](../../spec/script/python_coverage_omit.md)，则该 scoped gate 直接失败，不回退到 omit 前的原始统计。
## helper 清单

- `_build_parser() -> argparse.ArgumentParser`
- `_load_report(path: Path) -> dict[str, Any]`
- `_normalize_module_prefix(module: str) -> str`
- `_normalize_repo_path(path: str) -> str`
- `_omit_manifest_path() -> Path`
- `_load_omit_paths(path: Path) -> set[str]`
- `_path_matches_module(path: str, module: str) -> bool`
- `_require_int(value: Any, field: str, scope: str) -> int`
- `_summary_metrics(summary: Any, scope: str) -> dict[str, int]`
- `_aggregate_metrics(items: list[dict[str, int]]) -> dict[str, int]`
- `_collect_file_metrics(files: dict[str, Any], include_modules: list[str], omit_paths: set[str]) -> tuple[list[dict[str, int]], list[str]]`
- `_select_metrics(report: dict[str, Any], include_modules: list[str]) -> tuple[dict[str, int], str]`
- `_coverage_percent(covered: int, total: int) -> float`

## 使用示例

```bash
python3 script/check_python_coverage.py \
  --coverage-json coverage/S6/coverage.json \
  --line-min 98 \
  --branch-min 70
```

```bash
python3 script/check_python_coverage.py \
  --coverage-json coverage/S6/coverage.json \
  --include-module kernel_gen.tools \
  --line-min 98 \
  --branch-min 70
```

## 测试

- 测试文件：[`test/script/test_python_coverage_check.py`](../../test/script/test_python_coverage_check.py)
- 执行命令：

```bash
pytest -q test/script/test_python_coverage_check.py
```

- 公开回归目标：
  - 全量 gate 通过 / 失败。
  - `--include-module` scoped gate。
  - 精确 repo file module 路径在非 omit 文件上可正常通过。
  - 精确 repo file module 路径命中 omit 文件时显式失败。
  - omit 清单先于全量聚合生效。
  - omit 清单先于 scoped 模块过滤生效。
