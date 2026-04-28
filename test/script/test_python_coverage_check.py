"""check_python_coverage.py tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 `script/check_python_coverage.py` 的阈值通过、line 失败、branch 失败、缺字段和模块过滤路径。

关联文件:
- 功能实现: [script/check_python_coverage.py](../../script/check_python_coverage.py)
- Spec 文档: [spec/script/python_coverage_check.md](../../spec/script/python_coverage_check.md)
- 测试文件: [test/script/test_python_coverage_check.py](test/script/test_python_coverage_check.py)

使用示例:
- pytest -q test/script/test_python_coverage_check.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from script.check_python_coverage import main

REPO_ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.infra


def _fixture_root() -> Path:
    """返回当前测试现场可读的 coverage fixture 根目录。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 优先使用当前 `REPO_ROOT/test/fixtures/coverage`。
    - 当测试运行在独立 worktree 且 fixture 只存在于主仓时，回退到父目录同名路径。
    - 避免 coverage CLI 测试依赖“每个 worktree 都复制一份 fixture JSON”。

    使用示例:
    - root = _fixture_root()

    关联文件:
    - 功能实现: [script/check_python_coverage.py](../../script/check_python_coverage.py)
    - Spec 文档: [spec/script/python_coverage_check.md](../../spec/script/python_coverage_check.md)
    - 测试文件: [test/script/test_python_coverage_check.py](test_python_coverage_check.py)
    """

    repo_candidate = REPO_ROOT / "test/fixtures/coverage"
    if repo_candidate.is_dir():
        return repo_candidate
    parent_candidate = REPO_ROOT.parent / "test/fixtures/coverage"
    if parent_candidate.is_dir():
        return parent_candidate
    return repo_candidate


def _fixture(name: str) -> Path:
    """返回 coverage fixture 文件路径。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一定位 `test/fixtures/coverage/` 下的 synthetic coverage JSON。
    - 让各个测试用例共享同一套 fixture 目录布局。

    使用示例:
    - path = _fixture("pass.json")

    关联文件:
    - 功能实现: [script/check_python_coverage.py](../../script/check_python_coverage.py)
    - Spec 文档: [spec/script/python_coverage_check.md](../../spec/script/python_coverage_check.md)
    - 测试文件: [test/script/test_python_coverage_check.py](test/script/test_python_coverage_check.py)
    """

    return _fixture_root() / name


def _run_check(argv: list[str]) -> tuple[int, str, str]:
    """直接调用 CLI 入口并返回退出码、stdout 与 stderr。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 避免 subprocess 的额外开销，直接验证 `main()` 的返回约定。
    - 便于用例稳定断言成功与失败输出。

    使用示例:
    - code, stdout, stderr = _run_check([...])

    关联文件:
    - 功能实现: [script/check_python_coverage.py](../../script/check_python_coverage.py)
    - Spec 文档: [spec/script/python_coverage_check.md](../../spec/script/python_coverage_check.md)
    - 测试文件: [test/script/test_python_coverage_check.py](test/script/test_python_coverage_check.py)
    """

    from io import StringIO
    import contextlib

    stdout = StringIO()
    stderr = StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def test_check_python_coverage_accepts_passing_report() -> None:
    """TC-CPY-001: passing coverage report should satisfy global thresholds."""

    code, stdout, stderr = _run_check(
        [
            "--coverage-json",
            str(_fixture("pass.json")),
            "--line-min",
            "98",
            "--branch-min",
            "70",
        ]
    )
    assert code == 0
    assert "coverage ok:" in stdout
    assert "line=98.00%" in stdout
    assert "branch=70.00%" in stdout
    assert stderr == ""


def test_check_python_coverage_supports_include_module_filter() -> None:
    """TC-CPY-002: include-module should scope the report to matching kernel_gen paths."""

    code, stdout, stderr = _run_check(
        [
            "--coverage-json",
            str(_fixture("module_filter_pass.json")),
            "--include-module",
            "kernel_gen.passes",
            "--line-min",
            "98",
            "--branch-min",
            "70",
        ]
    )
    assert code == 0
    assert "scope=kernel_gen/passes" in stdout
    assert "line=100.00%" in stdout
    assert stderr == ""


def test_check_python_coverage_supports_file_level_include_module_filter(tmp_path: Path) -> None:
    """TC-CPY-002B: include-module should also match a specific file-level module path."""

    report = {
        "totals": {
            "covered_lines": 0,
            "num_statements": 0,
            "covered_branches": 0,
            "num_branches": 0,
        },
        "files": {
            "kernel_gen/passes/tile/analysis.py": {
                "summary": {
                    "covered_lines": 5,
                    "num_statements": 5,
                    "covered_branches": 2,
                    "num_branches": 2,
                }
            }
        },
    }
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    code, stdout, stderr = _run_check(
        [
            "--coverage-json",
            str(report_path),
            "--include-module",
            "kernel_gen.passes.tile.analysis",
            "--line-min",
            "98",
            "--branch-min",
            "70",
        ]
    )
    assert code == 0
    assert "scope=kernel_gen/passes/tile/analysis (1 file(s))" in stdout
    assert "line=100.00%" in stdout
    assert stderr == ""


def test_check_python_coverage_supports_exact_repo_file_module_fixture() -> None:
    """TC-CPY-002C: include-module should accept an exact repo file module path."""

    code, stdout, stderr = _run_check(
        [
            "--coverage-json",
            str(_fixture("core_module_filter_pass.json")),
            "--include-module",
            "kernel_gen.dsl.mlir_gen.emit.core",
            "--line-min",
            "98",
            "--branch-min",
            "70",
        ]
    )
    assert code == 0
    assert "scope=kernel_gen/dsl/mlir_gen/emit/core (1 file(s))" in stdout
    assert "line=100.00%" in stdout
    assert stderr == ""


def test_check_python_coverage_rejects_line_threshold() -> None:
    """TC-CPY-003: line coverage below threshold must fail."""

    code, stdout, stderr = _run_check(
        [
            "--coverage-json",
            str(_fixture("line_fail.json")),
            "--line-min",
            "98",
            "--branch-min",
            "70",
        ]
    )
    assert code == 1
    assert stdout == ""
    assert "line coverage 90.00% < 98.00%" in stderr


def test_check_python_coverage_rejects_branch_threshold() -> None:
    """TC-CPY-004: branch coverage below threshold must fail."""

    code, stdout, stderr = _run_check(
        [
            "--coverage-json",
            str(_fixture("branch_fail.json")),
            "--line-min",
            "98",
            "--branch-min",
            "70",
        ]
    )
    assert code == 1
    assert stdout == ""
    assert "branch coverage 55.00% < 70.00%" in stderr


def test_check_python_coverage_rejects_missing_fields() -> None:
    """TC-CPY-005: incomplete coverage JSON must fail explicitly."""

    code, stdout, stderr = _run_check(
        [
            "--coverage-json",
            str(_fixture("missing_fields.json")),
            "--line-min",
            "98",
            "--branch-min",
            "70",
        ]
    )
    assert code == 1
    assert stdout == ""
    assert "missing" in stderr
