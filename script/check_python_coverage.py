#!/usr/bin/env python3
"""Python coverage threshold check CLI.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 读取 `coverage.py` 生成的 JSON 报告。
- 按全量 `kernel_gen` 或指定模块前缀检查 line / branch 覆盖率阈值。
- 为 `repo_conformance_refactor` 主线提供可脚本化、可测试的覆盖率阈值检查入口。

API 列表:
- `CoverageCheckError(message: str)`
- `check_coverage(report_path: Path, line_min: float, branch_min: float, include_modules: list[str]) -> dict[str, Any]`
- `main(argv: list[str] | None = None) -> int`

helper 清单:
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

使用示例:
- python3 script/check_python_coverage.py --coverage-json coverage/S2/coverage.json --line-min 98 --branch-min 70
- python3 script/check_python_coverage.py --coverage-json coverage/S2/coverage.json --include-module kernel_gen.tools --line-min 98 --branch-min 70

关联文件:
- spec: [spec/script/python_coverage_check.md](../spec/script/python_coverage_check.md)
- spec: [spec/script/python_coverage_omit.md](../spec/script/python_coverage_omit.md)
- test: [test/script/test_python_coverage_check.py](../test/script/test_python_coverage_check.py)
- test: [test/script/test_python_coverage_omit.py](../test/script/test_python_coverage_omit.py)
- 功能实现: [script/check_python_coverage.py](check_python_coverage.py)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any


class CoverageCheckError(RuntimeError):
    """coverage 阈值检查失败或输入数据不合法时抛出的异常。"""


def _build_parser() -> argparse.ArgumentParser:
    """构造覆盖率检查命令行解析器。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 固定公开参数 `--coverage-json`、`--line-min`、`--branch-min`、`--include-module`。
    - 支持按模块前缀重复指定 `--include-module`。

    使用示例:
    - parser = _build_parser()
    - args = parser.parse_args(["--coverage-json", "coverage.json", "--line-min", "98", "--branch-min", "70"])

    关联文件:
    - spec: [spec/script/python_coverage_check.md](../spec/script/python_coverage_check.md)
    - test: [test/script/test_python_coverage_check.py](../test/script/test_python_coverage_check.py)
    - 功能实现: [script/check_python_coverage.py](check_python_coverage.py)
    """

    parser = argparse.ArgumentParser(description="Check kernel_gen coverage thresholds.")
    parser.add_argument("--coverage-json", type=Path, required=True, help="coverage.py JSON report path")
    parser.add_argument("--line-min", type=float, required=True, help="minimum line coverage percentage")
    parser.add_argument("--branch-min", type=float, required=True, help="minimum branch coverage percentage")
    parser.add_argument(
        "--include-module",
        action="append",
        default=[],
        help="optional python module prefix to scope the check; may be repeated",
    )
    return parser


def _load_report(path: Path) -> dict[str, Any]:
    """读取并解析 coverage JSON 报告。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 校验报告文件存在且为合法 JSON。
    - 统一将解析失败转换为 `CoverageCheckError`，便于命令行返回一致错误码。

    使用示例:
    - report = _load_report(Path("coverage/S1/coverage.json"))

    关联文件:
    - spec: [spec/script/python_coverage_check.md](../spec/script/python_coverage_check.md)
    - test: [test/script/test_python_coverage_check.py](../test/script/test_python_coverage_check.py)
    - 功能实现: [script/check_python_coverage.py](check_python_coverage.py)
    """

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:  # pragma: no cover - 由 CLI / 集成测试覆盖
        raise CoverageCheckError(f"failed to read coverage JSON: {path}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CoverageCheckError(f"invalid coverage JSON: {path}") from exc
    if not isinstance(data, dict):
        raise CoverageCheckError("coverage JSON root must be an object")
    return data


def _normalize_module_prefix(module: str) -> str:
    """把模块名归一化为适合路径前缀匹配的形式。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 接受 `kernel_gen.passes` 与 `kernel_gen/passes` 两种写法。
    - 去掉可能附带的 `.py` 后缀，确保路径匹配稳定。

    使用示例:
    - _normalize_module_prefix("kernel_gen.passes") == "kernel_gen/passes"
    - _normalize_module_prefix("kernel_gen/passes/__init__.py") == "kernel_gen/passes"

    关联文件:
    - spec: [spec/script/python_coverage_check.md](../spec/script/python_coverage_check.md)
    - test: [test/script/test_python_coverage_check.py](../test/script/test_python_coverage_check.py)
    - 功能实现: [script/check_python_coverage.py](check_python_coverage.py)
    """

    normalized = module.strip().replace("\\", "/").replace(".", "/")
    if normalized.endswith(".py"):
        normalized = normalized[:-3]
    return normalized.strip("/")


def _normalize_repo_path(path: str) -> str:
    """把 coverage JSON 路径归一化为仓内 `kernel_gen/...` 相对路径。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一处理 coverage JSON 中的绝对路径、相对路径与 Windows 风格路径。
    - 若路径中包含 `kernel_gen/` 段，则截取该段开始的仓内相对路径。

    使用示例:
    - _normalize_repo_path("/tmp/wt/kernel_gen/tools/dsl_run.py") == "kernel_gen/tools/dsl_run.py"

    关联文件:
    - spec: [spec/script/python_coverage_check.md](../spec/script/python_coverage_check.md)
    - test: [test/script/test_python_coverage_check.py](../test/script/test_python_coverage_check.py)
    - 功能实现: [script/check_python_coverage.py](check_python_coverage.py)
    """

    normalized = path.replace("\\", "/").strip()
    match = re.search(r"(^|/)(kernel_gen/.+)$", normalized)
    if match is not None:
        return match.group(2)
    return normalized.lstrip("./")


def _omit_manifest_path() -> Path:
    """返回 coverage omit 清单路径。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 固定定位当前仓库的 `spec/script/python_coverage_omit.md`。
    - 供覆盖率阈值检查与测试共享同一份 omit 合同真源。

    使用示例:
    - path = _omit_manifest_path()

    关联文件:
    - spec: [spec/script/python_coverage_omit.md](../spec/script/python_coverage_omit.md)
    - test: [test/script/test_python_coverage_omit.py](../test/script/test_python_coverage_omit.py)
    - 功能实现: [script/check_python_coverage.py](check_python_coverage.py)
    """

    return Path(__file__).resolve().parents[1] / "spec/script/python_coverage_omit.md"


def _load_omit_paths(path: Path) -> set[str]:
    """从 omit 清单解析需要排除的仓内文件路径。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 只解析 markdown 表格中的 ``kernel_gen/...`` 路径。
    - 当 omit 清单缺失或为空时返回空集合，保持 CLI 可独立运行。

    使用示例:
    - omit_paths = _load_omit_paths(_omit_manifest_path())

    关联文件:
    - spec: [spec/script/python_coverage_omit.md](../spec/script/python_coverage_omit.md)
    - test: [test/script/test_python_coverage_omit.py](../test/script/test_python_coverage_omit.py)
    - 功能实现: [script/check_python_coverage.py](check_python_coverage.py)
    """

    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return set()
    omit_paths: set[str] = set()
    for match in re.finditer(r"\|\s*`([^`]+)`\s*\|", text):
        candidate = _normalize_repo_path(match.group(1))
        if candidate.startswith("kernel_gen/"):
            omit_paths.add(candidate)
    return omit_paths


def _path_matches_module(path: str, module: str) -> bool:
    """判断 coverage 文件路径是否属于指定模块前缀。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 使用路径段前缀匹配，而不是文本子串匹配，避免误命中同名目录。
    - 同时兼容绝对路径与相对路径格式。

    使用示例:
    - _path_matches_module("kernel_gen/passes/foo.py", "kernel_gen.passes")

    关联文件:
    - spec: [spec/script/python_coverage_check.md](../spec/script/python_coverage_check.md)
    - test: [test/script/test_python_coverage_check.py](../test/script/test_python_coverage_check.py)
    - 功能实现: [script/check_python_coverage.py](check_python_coverage.py)
    """

    prefix = _normalize_module_prefix(module)
    if not prefix:
        return False
    normalized_path = _normalize_repo_path(path)
    normalized_parts = [part for part in PurePosixPath(normalized_path).parts if part not in {"", "/"}]
    prefix_parts = prefix.split("/")
    if len(normalized_parts) < len(prefix_parts):
        return False
    for index in range(len(normalized_parts) - len(prefix_parts) + 1):
        matched = True
        for offset, prefix_part in enumerate(prefix_parts):
            path_part = normalized_parts[index + offset]
            if path_part == prefix_part:
                continue
            if offset == len(prefix_parts) - 1 and path_part == f"{prefix_part}.py":
                continue
            matched = False
            break
        if matched:
            return True
    return False


def _require_int(value: Any, field: str, scope: str) -> int:
    """把 coverage 数值字段强制转换为整数。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - coverage JSON 的计数值应为整数；缺失或非法值直接视为输入异常。
    - 避免在阈值计算时悄悄吞掉错误字段。

    使用示例:
    - _require_int(12, "num_statements", "totals")

    关联文件:
    - spec: [spec/script/python_coverage_check.md](../spec/script/python_coverage_check.md)
    - test: [test/script/test_python_coverage_check.py](../test/script/test_python_coverage_check.py)
    - 功能实现: [script/check_python_coverage.py](check_python_coverage.py)
    """

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CoverageCheckError(f"coverage JSON missing {field} in {scope}")
    if int(value) != value:
        raise CoverageCheckError(f"coverage JSON field {field} in {scope} must be integral")
    return int(value)


def _summary_metrics(summary: Any, scope: str) -> dict[str, int]:
    """把 coverage summary 转换为统一的计数指标。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 提取 line / branch 计算所需的四个计数值。
    - 当某个字段缺失时抛出 `CoverageCheckError`，避免把不完整报告误判为通过。

    使用示例:
    - metrics = _summary_metrics(report["totals"], "totals")

    关联文件:
    - spec: [spec/script/python_coverage_check.md](../spec/script/python_coverage_check.md)
    - test: [test/script/test_python_coverage_check.py](../test/script/test_python_coverage_check.py)
    - 功能实现: [script/check_python_coverage.py](check_python_coverage.py)
    """

    if not isinstance(summary, dict):
        raise CoverageCheckError(f"coverage JSON missing summary for {scope}")
    covered_lines = _require_int(summary.get("covered_lines"), "covered_lines", scope)
    num_statements = _require_int(summary.get("num_statements"), "num_statements", scope)
    covered_branches = _require_int(summary.get("covered_branches"), "covered_branches", scope)
    num_branches = _require_int(summary.get("num_branches"), "num_branches", scope)
    return {
        "covered_lines": covered_lines,
        "num_statements": num_statements,
        "covered_branches": covered_branches,
        "num_branches": num_branches,
    }


def _aggregate_metrics(items: list[dict[str, int]]) -> dict[str, int]:
    """把多个模块的 summary 指标汇总为一个总计。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 对 `--include-module` 命中的多个文件做加总。
    - 保留 line / branch 计数的可加性，供阈值计算使用。

    使用示例:
    - totals = _aggregate_metrics([metrics_a, metrics_b])

    关联文件:
    - spec: [spec/script/python_coverage_check.md](../spec/script/python_coverage_check.md)
    - test: [test/script/test_python_coverage_check.py](../test/script/test_python_coverage_check.py)
    - 功能实现: [script/check_python_coverage.py](check_python_coverage.py)
    """

    return {
        "covered_lines": sum(item["covered_lines"] for item in items),
        "num_statements": sum(item["num_statements"] for item in items),
        "covered_branches": sum(item["covered_branches"] for item in items),
        "num_branches": sum(item["num_branches"] for item in items),
    }


def _collect_file_metrics(
    files: dict[str, Any],
    include_modules: list[str],
    omit_paths: set[str],
) -> tuple[list[dict[str, int]], list[str]]:
    """收集未命中 omit 的文件 summary，并按模块前缀过滤。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 先按 omit 清单排除内部拆分或薄包装文件。
    - 再按 `--include-module` 过滤剩余 coverage 文件。

    使用示例:
    - metrics, matched_files = _collect_file_metrics(files, ["kernel_gen.tools"], omit_paths)

    关联文件:
    - spec: [spec/script/python_coverage_check.md](../spec/script/python_coverage_check.md)
    - spec: [spec/script/python_coverage_omit.md](../spec/script/python_coverage_omit.md)
    - test: [test/script/test_python_coverage_check.py](../test/script/test_python_coverage_check.py)
    - 功能实现: [script/check_python_coverage.py](check_python_coverage.py)
    """

    normalized_modules = [_normalize_module_prefix(module) for module in include_modules]
    metrics: list[dict[str, int]] = []
    matched_files: list[str] = []
    for path, data in files.items():
        normalized_path = _normalize_repo_path(path)
        if not normalized_path.startswith("kernel_gen/"):
            continue
        if normalized_path in omit_paths:
            continue
        if normalized_modules and not any(_path_matches_module(normalized_path, module) for module in normalized_modules):
            continue
        metrics.append(_summary_metrics((data or {}).get("summary"), normalized_path))
        matched_files.append(normalized_path)
    return metrics, matched_files


def _select_metrics(report: dict[str, Any], include_modules: list[str]) -> tuple[dict[str, int], str]:
    """从 coverage 报告中选择需要检查的 metrics。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 优先按 `files` 聚合覆盖率，并先应用 omit 清单再做模块过滤。
    - 仅当报告缺少 `files` 且未请求 `--include-module` 时，才回退读取 `totals`。

    使用示例:
    - metrics, scope = _select_metrics(report, ["kernel_gen.passes"])

    关联文件:
    - spec: [spec/script/python_coverage_check.md](../spec/script/python_coverage_check.md)
    - test: [test/script/test_python_coverage_check.py](../test/script/test_python_coverage_check.py)
    - 功能实现: [script/check_python_coverage.py](check_python_coverage.py)
    """

    files = report.get("files")
    omit_paths = _load_omit_paths(_omit_manifest_path())
    if isinstance(files, dict):
        metrics, matched_files = _collect_file_metrics(files, include_modules, omit_paths)
        if not metrics:
            if include_modules:
                raise CoverageCheckError(
                    "coverage JSON does not contain non-omitted files for include-module scope: "
                    + ", ".join(sorted(set(include_modules)))
                )
            raise CoverageCheckError("coverage JSON does not contain non-omitted kernel_gen files")
        if not include_modules:
            return _aggregate_metrics(metrics), "totals"
        normalized_modules = sorted(set(_normalize_module_prefix(module) for module in include_modules))
        scope = ", ".join(normalized_modules)
        return _aggregate_metrics(metrics), f"{scope} ({len(matched_files)} file(s))"
    if include_modules:
        raise CoverageCheckError("coverage JSON missing files for --include-module filtering")
    totals = report.get("totals")
    return _summary_metrics(totals, "totals"), "totals"


def _coverage_percent(covered: int, total: int) -> float:
    """根据分子分母计算覆盖率百分比。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 当总量为 0 时按 100% 处理，和 coverage.py 的零分母语义保持一致。

    使用示例:
    - _coverage_percent(95, 100) == 95.0

    关联文件:
    - spec: [spec/script/python_coverage_check.md](../spec/script/python_coverage_check.md)
    - test: [test/script/test_python_coverage_check.py](../test/script/test_python_coverage_check.py)
    - 功能实现: [script/check_python_coverage.py](check_python_coverage.py)
    """

    if total == 0:
        return 100.0
    return covered * 100.0 / total


def check_coverage(report_path: Path, line_min: float, branch_min: float, include_modules: list[str]) -> dict[str, Any]:
    """检查 coverage JSON 是否满足给定阈值。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 读取 coverage 报告并计算 line / branch 覆盖率。
    - 返回可用于日志或测试断言的摘要字典。

    使用示例:
    - summary = check_coverage(Path("coverage.json"), 95, 60, ["kernel_gen.passes"])

    关联文件:
    - spec: [spec/script/python_coverage_check.md](../spec/script/python_coverage_check.md)
    - test: [test/script/test_python_coverage_check.py](../test/script/test_python_coverage_check.py)
    - 功能实现: [script/check_python_coverage.py](check_python_coverage.py)
    """

    report = _load_report(report_path)
    metrics, scope = _select_metrics(report, include_modules)
    line_percent = _coverage_percent(metrics["covered_lines"], metrics["num_statements"])
    branch_percent = _coverage_percent(metrics["covered_branches"], metrics["num_branches"])
    failures: list[str] = []
    if line_percent < line_min:
        failures.append(f"line coverage {line_percent:.2f}% < {line_min:.2f}%")
    if branch_percent < branch_min:
        failures.append(f"branch coverage {branch_percent:.2f}% < {branch_min:.2f}%")
    if failures:
        raise CoverageCheckError(f"{scope}: " + "; ".join(failures))
    return {
        "scope": scope,
        "covered_lines": metrics["covered_lines"],
        "num_statements": metrics["num_statements"],
        "line_percent": line_percent,
        "covered_branches": metrics["covered_branches"],
        "num_branches": metrics["num_branches"],
        "branch_percent": branch_percent,
    }


def main(argv: list[str] | None = None) -> int:
    """命令行入口。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 解析 CLI 参数，执行覆盖率检查并返回进程退出码。
    - 成功时打印简短摘要；失败时把原因写入标准错误。

    使用示例:
    - raise SystemExit(main(["--coverage-json", "coverage.json", "--line-min", "95", "--branch-min", "60"]))

    关联文件:
    - spec: [spec/script/python_coverage_check.md](../spec/script/python_coverage_check.md)
    - test: [test/script/test_python_coverage_check.py](../test/script/test_python_coverage_check.py)
    - 功能实现: [script/check_python_coverage.py](check_python_coverage.py)
    """

    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        summary = check_coverage(
            report_path=args.coverage_json,
            line_min=args.line_min,
            branch_min=args.branch_min,
            include_modules=list(args.include_module),
        )
    except CoverageCheckError as exc:
        print(f"coverage check failed: {exc}", file=sys.stderr)
        return 1
    print(
        "coverage ok: "
        f"scope={summary['scope']}; "
        f"line={summary['line_percent']:.2f}% >= {args.line_min:.2f}%; "
        f"branch={summary['branch_percent']:.2f}% >= {args.branch_min:.2f}%"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
