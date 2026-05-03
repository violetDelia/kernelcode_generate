# python_coverage_check.md

## 功能简介

- 定义 [`script/check_python_coverage.py`](../../script/check_python_coverage.py) 的公开合同。
- 读取 `coverage.py` 生成的 JSON 报告，检查 Python 项目的 line / branch 覆盖率阈值。
- 支持按 `kernel_gen` 模块前缀做阶段内 scoped 验收，并在 `files` 级汇总前先应用 [`python_coverage_omit.md`](../../spec/script/python_coverage_omit.md) 的排除清单。

## API 列表

- `class CoverageCheckError(message: str)`
- `check_coverage(report_path: Path, line_min: float, branch_min: float, include_modules: list[str]) -> dict[str, JsonValue]`
- `main(argv: list[str] | None = None) -> int`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/script/python_coverage_check.md`](../../spec/script/python_coverage_check.md)
- `spec`：[`spec/script/python_coverage_omit.md`](../../spec/script/python_coverage_omit.md)
- `功能实现`：[`script/check_python_coverage.py`](../../script/check_python_coverage.py)
- `test`：[`test/script/test_python_coverage_check.py`](../../test/script/test_python_coverage_check.py)

## 依赖

- 无额外 spec 依赖。

## 目标

- 为 coverage gate 提供稳定的 line / branch 阈值检查入口。
- 允许阶段内按 `--include-module` 只检查指定 `kernel_gen` 模块前缀或单文件模块路径。
- 对缺失、损坏或字段不完整的 coverage JSON 明确失败，不把不完整报告误判为通过。

## 术语

- `JsonValue`：`coverage.py` JSON 报告中的公开 JSON 值，取值范围为 `str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]`。

## API详细说明

### `class CoverageCheckError(message: str)`

- api：`class CoverageCheckError(message: str)`
- 参数：
  - `message`：诊断或错误消息文本，用于构造稳定错误或校验输出；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`CoverageCheckError` 实例。
- 使用示例：

  ```python
  from script.check_python_coverage import CoverageCheckError

  error = CoverageCheckError("coverage JSON root must be an object")
  ```
- 功能说明：表示覆盖率阈值检查失败或输入数据不合法。
- 注意事项：`check_coverage(...)` 和 `main(...)` 的公开失败均通过该异常或其 CLI 错误文本表达；实例内部状态不作为公开可变入口。

### `check_coverage(report_path: Path, line_min: float, branch_min: float, include_modules: list[str]) -> dict[str, JsonValue]`

- api：`check_coverage(report_path: Path, line_min: float, branch_min: float, include_modules: list[str]) -> dict[str, JsonValue]`
- 参数：
  - `report_path`：`coverage.py` JSON 报告路径；类型 `Path`；无默认值，调用方必须显式提供；不允许 `None`；文件必须可读取且 JSON 根节点必须是对象。
  - `line_min`：最小 line coverage 百分比；类型 `float`；无默认值，调用方必须显式提供；不允许 `None`。
  - `branch_min`：最小 branch coverage 百分比；类型 `float`；无默认值，调用方必须显式提供；不允许 `None`。
  - `include_modules`：可重复指定的模块前缀或单文件模块路径；类型 `list[str]`；无默认值，调用方必须显式提供；空列表表示检查全量可统计文件。
- 返回值：`dict[str, JsonValue]`。
- 使用示例：

  ```python
  from pathlib import Path

  from script.check_python_coverage import check_coverage

  summary = check_coverage(
      report_path=Path("coverage/S6/coverage.json"),
      line_min=98,
      branch_min=70,
      include_modules=["kernel_gen.tools"],
  )
  ```
- 功能说明：读取 coverage JSON，计算 line / branch 覆盖率并校验阈值。
- 注意事项：返回值固定包含 `scope`、`covered_lines`、`num_statements`、`line_percent`、`covered_branches`、`num_branches`、`branch_percent`；当报告包含 `files` 时，先应用 omit 清单，再做 `include_modules` 过滤，最后按剩余文件汇总覆盖率；仅当报告缺少 `files` 且未请求 `include_modules` 时，才回退读取 `totals`；阈值不满足、报告损坏、精确模块路径命中 omit 文件或字段不完整时抛出 `CoverageCheckError`。

### `main(argv: list[str] | None = None) -> int`

- api：`main(argv: list[str] | None = None) -> int`
- 参数：
  - `argv`：命令行参数列表；类型 `list[str] | None`；默认值 `None`；`None` 表示读取进程命令行参数；列表内容必须符合公开 CLI 参数。
- 返回值：`int`，表示进程退出码。
- 使用示例：

  ```python
  from script.check_python_coverage import main

  result = main([
      "--coverage-json",
      "coverage/S6/coverage.json",
      "--line-min",
      "98",
      "--branch-min",
      "70",
  ])
  ```
- 功能说明：公开 CLI 入口，解析参数后执行覆盖率检查。
- 注意事项：支持 `--coverage-json`、`--line-min`、`--branch-min`、`--include-module`；成功返回 `0` 并打印 `coverage ok: ...` 摘要；失败返回非 `0` 并向标准错误打印 `coverage check failed: ...`。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 仅处理 `coverage.py` JSON 报告，不负责生成覆盖率数据。
- 不修改 omit 清单；只读取 [`python_coverage_omit.md`](../../spec/script/python_coverage_omit.md) 作为阈值排除合同。
- 不替代 `pytest`，只负责 coverage 阈值校验。

### 参数与输出

- `--coverage-json(Path)`：coverage JSON 路径。
- `--line-min(float)`：最小 line coverage 百分比。
- `--branch-min(float)`：最小 branch coverage 百分比。
- `--include-module(list[str])`：可重复指定的模块前缀；当报告包含 `files` 时，先排除 omit 清单，再从剩余文件中筛选匹配项。
  - 支持精确到单文件模块路径，例如 `kernel_gen.passes.example`。
  - 若精确模块路径命中的文件已列入 [`python_coverage_omit.md`](../../spec/script/python_coverage_omit.md)，则该 scoped gate 直接失败，不回退到 omit 前的原始统计。
### helper 清单

- `_build_parser() -> argparse.ArgumentParser`
- `_load_report(path: Path) -> dict[str, JsonValue]`
- `_normalize_module_prefix(module: str) -> str`
- `_normalize_repo_path(path: str) -> str`
- `_omit_manifest_path() -> Path`
- `_load_omit_paths(path: Path) -> set[str]`
- `_path_matches_module(path: str, module: str) -> bool`
- `_require_int(value: JsonValue, field: str, scope: str) -> int`
- `_summary_metrics(summary: JsonValue, scope: str) -> dict[str, int]`
- `_aggregate_metrics(items: list[dict[str, int]]) -> dict[str, int]`
- `_collect_file_metrics(files: dict[str, JsonValue], include_modules: list[str], omit_paths: set[str]) -> tuple[list[dict[str, int]], list[str]]`
- `_select_metrics(report: dict[str, JsonValue], include_modules: list[str]) -> tuple[dict[str, int], str]`
- `_coverage_percent(covered: int, total: int) -> float`

### 使用示例

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

- 测试文件：`test/script/test_python_coverage_check.py`
- 执行命令：`bash
pytest -q test/script/test_python_coverage_check.py
`

### 测试目标

- 验证 `script/python_coverage_check` 的公开 API、边界与错误语义。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-SCRIPT-PYTHON-COVERAGE-CHECK-001 | pass 改写 | check python coverage accepts passing report | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_check_python_coverage_accepts_passing_report`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“check python coverage accepts passing report”场景。 | `test_check_python_coverage_accepts_passing_report` |
| TC-SCRIPT-PYTHON-COVERAGE-CHECK-002 | 公开入口 | check python coverage supports include module filter | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_check_python_coverage_supports_include_module_filter`。 | 公开入口在“check python coverage supports include module filter”场景下可导入、构造、注册或按名称发现。 | `test_check_python_coverage_supports_include_module_filter` |
| TC-SCRIPT-PYTHON-COVERAGE-CHECK-003 | 公开入口 | check python coverage supports file level include module filter | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_check_python_coverage_supports_file_level_include_module_filter`。 | 公开入口在“check python coverage supports file level include module filter”场景下可导入、构造、注册或按名称发现。 | `test_check_python_coverage_supports_file_level_include_module_filter` |
| TC-SCRIPT-PYTHON-COVERAGE-CHECK-004 | 公开入口 | check python coverage supports exact repo file module fixture | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_check_python_coverage_supports_exact_repo_file_module_fixture`。 | 公开入口在“check python coverage supports exact repo file module fixture”场景下可导入、构造、注册或按名称发现。 | `test_check_python_coverage_supports_exact_repo_file_module_fixture` |
| TC-SCRIPT-PYTHON-COVERAGE-CHECK-005 | 边界/异常 | check python coverage rejects exact repo file module when file is omitted | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_check_python_coverage_rejects_exact_repo_file_module_when_file_is_omitted`。 | “check python coverage rejects exact repo file module when file is omitted”场景按公开错误语义失败或被拒绝。 | `test_check_python_coverage_rejects_exact_repo_file_module_when_file_is_omitted` |
| TC-SCRIPT-PYTHON-COVERAGE-CHECK-006 | 公开入口 | check python coverage omits internal split files from global gate | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_check_python_coverage_omits_internal_split_files_from_global_gate`。 | 公开入口在“check python coverage omits internal split files from global gate”场景下可导入、构造、注册或按名称发现。 | `test_check_python_coverage_omits_internal_split_files_from_global_gate` |
| TC-SCRIPT-PYTHON-COVERAGE-CHECK-007 | 公开入口 | check python coverage applies omit before include module filter | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_check_python_coverage_applies_omit_before_include_module_filter`。 | 公开入口在“check python coverage applies omit before include module filter”场景下可导入、构造、注册或按名称发现。 | `test_check_python_coverage_applies_omit_before_include_module_filter` |
| TC-SCRIPT-PYTHON-COVERAGE-CHECK-008 | 边界/异常 | check python coverage rejects line threshold | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_check_python_coverage_rejects_line_threshold`。 | “check python coverage rejects line threshold”场景按公开错误语义失败或被拒绝。 | `test_check_python_coverage_rejects_line_threshold` |
| TC-SCRIPT-PYTHON-COVERAGE-CHECK-009 | 边界/异常 | check python coverage rejects branch threshold | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_check_python_coverage_rejects_branch_threshold`。 | “check python coverage rejects branch threshold”场景按公开错误语义失败或被拒绝。 | `test_check_python_coverage_rejects_branch_threshold` |
| TC-SCRIPT-PYTHON-COVERAGE-CHECK-010 | 边界/异常 | check python coverage rejects missing fields | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_check_python_coverage_rejects_missing_fields`。 | “check python coverage rejects missing fields”场景按公开错误语义失败或被拒绝。 | `test_check_python_coverage_rejects_missing_fields` |
