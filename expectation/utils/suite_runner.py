"""expectation 递归 case 发现与运行工具。

创建者: Codex
最后修改人: Codex

功能说明:
- 提供 `run_discovered_expectation_suite(...)`，用于从任意 expectation 包目录递归发现并运行
  子目录中的全部 case。
- case 判定规则固定为：普通 `.py` 文件、文件名不以 `_` 开头、不是 `__main__.py`/`__init__.py`、
  不在 `expectation/utils` 工具目录下、且模块内存在无参 `main()`。
- 已有子目录是否维护手写 `__main__.py` 不影响根入口；递归 runner 直接运行实际 case 模块，避免
  子目录聚合入口遗漏新 case。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation`

关联文件:
- spec: [`AGENTS.md`](../../AGENTS.md)
- test: [`expectation/__main__.py`](../__main__.py)
- 功能实现: [`expectation/utils/suite_runner.py`](suite_runner.py)
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from expectation.utils.case_runner import raise_if_failures, run_case


def _is_case_path(root_dir: Path, path: Path) -> bool:
    """判断一个 Python 文件路径是否可能属于可自动运行的 expectation case。

    创建者: Codex
    最后修改人: Codex

    功能说明:
    - 排除 `__main__.py`、`__init__.py`、私有 helper、`__pycache__` 与 `utils` 工具目录。
    - 只做路径级过滤；是否真的可运行由 `discover_case_modules(...)` 检查 `main()` 定义。

    使用示例:
    - `_is_case_path(Path("expectation"), Path("expectation/tools/dsl_run/add.py"))`

    关联文件:
    - spec: [`AGENTS.md`](../../AGENTS.md)
    - test: [`expectation/__main__.py`](../__main__.py)
    - 功能实现: [`expectation/utils/suite_runner.py`](suite_runner.py)
    """

    if path.name in {"__main__.py", "__init__.py"} or path.name.startswith("_"):
        return False
    rel_parts = path.relative_to(root_dir).parts
    if "__pycache__" in rel_parts:
        return False
    return not rel_parts or rel_parts[0] != "utils"


def _module_name_for_path(root_package: str, root_dir: Path, path: Path) -> str:
    """把 case 文件路径转换为可导入的模块名。

    创建者: Codex
    最后修改人: Codex

    功能说明:
    - 基于 `root_package` 与相对路径生成稳定模块名。
    - 该函数只处理已经通过 `_is_case_path(...)` 的 `.py` 文件。

    使用示例:
    - `_module_name_for_path("expectation", Path("expectation"), Path("expectation/tools/dsl_run/add.py"))`

    关联文件:
    - spec: [`AGENTS.md`](../../AGENTS.md)
    - test: [`expectation/__main__.py`](../__main__.py)
    - 功能实现: [`expectation/utils/suite_runner.py`](suite_runner.py)
    """

    rel_path = path.relative_to(root_dir).with_suffix("")
    return ".".join((root_package, *rel_path.parts))


def discover_case_modules(root_package: str, package_file: str | Path) -> list[str]:
    """递归发现指定 expectation 包目录下的全部 case 模块名。

    创建者: Codex
    最后修改人: Codex

    功能说明:
    - 从 `package_file` 所在目录递归扫描 `.py` 文件。
    - 返回值按路径排序，保证重复运行顺序稳定。
    - 只返回路径层面可能是 case、且文件内定义 `main()` 的模块。

    使用示例:
    - `modules = discover_case_modules("expectation", "expectation/__main__.py")`

    关联文件:
    - spec: [`AGENTS.md`](../../AGENTS.md)
    - test: [`expectation/__main__.py`](../__main__.py)
    - 功能实现: [`expectation/utils/suite_runner.py`](suite_runner.py)
    """

    root_dir = Path(package_file).resolve().parent
    modules: list[str] = []
    for path in sorted(root_dir.rglob("*.py")):
        if _is_case_path(root_dir, path) and "def main(" in path.read_text(encoding="utf-8"):
            modules.append(_module_name_for_path(root_package, root_dir, path))
    return modules


def _repo_root_for_package(root_dir: Path) -> Path:
    """返回 expectation 包所在仓库根目录。

    创建者: Codex
    最后修改人: Codex

    功能说明:
    - 根 runner 使用 `python -m <case_module>` 子进程执行 case，需要把仓库根目录放入
      `PYTHONPATH`。
    - `root_dir` 是 `expectation` 包目录，因此其父目录就是仓库根目录。

    使用示例:
    - `_repo_root_for_package(Path("expectation"))`

    关联文件:
    - spec: [`AGENTS.md`](../../AGENTS.md)
    - test: [`expectation/__main__.py`](../__main__.py)
    - 功能实现: [`expectation/utils/suite_runner.py`](suite_runner.py)
    """

    return root_dir.parent


def _subprocess_env(repo_root: Path) -> dict[str, str]:
    """构造运行单个 case 子进程使用的环境变量。

    创建者: Codex
    最后修改人: Codex

    功能说明:
    - 保留调用方现有环境。
    - 将仓库根目录前置到 `PYTHONPATH`，保证子进程可以稳定导入 `expectation` 与
      `kernel_gen`。
    - 默认启用 `PYTHONDONTWRITEBYTECODE=1`，避免全量 expectation 运行生成 `__pycache__`。

    使用示例:
    - `env = _subprocess_env(Path("/repo"))`

    关联文件:
    - spec: [`AGENTS.md`](../../AGENTS.md)
    - test: [`expectation/__main__.py`](../__main__.py)
    - 功能实现: [`expectation/utils/suite_runner.py`](suite_runner.py)
    """

    env = os.environ.copy()
    old_pythonpath = env.get("PYTHONPATH")
    pythonpath_entries = [str(repo_root)]
    if old_pythonpath:
        pythonpath_entries.append(old_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    return env


def _run_case_module(module_name: str, repo_root: Path) -> None:
    """在独立 Python 子进程中运行单个 case 模块。

    创建者: Codex
    最后修改人: Codex

    功能说明:
    - 使用 `python -m <module_name>` 运行实际 case，避免 194 个 case 在同一解释器中复用
      全局模块缓存、随机 helper 或 C 扩展导入状态。
    - 子进程 stdout/stderr 会原样转发到当前进程，便于定位失败 case。
    - 非零退出码会抛出 `AssertionError`，再由 `run_case(...)` 汇总到全量失败列表。

    使用示例:
    - `_run_case_module("expectation.tools.dsl_run.add", Path("/repo"))`

    关联文件:
    - spec: [`AGENTS.md`](../../AGENTS.md)
    - test: [`expectation/__main__.py`](../__main__.py)
    - 功能实现: [`expectation/utils/suite_runner.py`](suite_runner.py)
    """

    completed = subprocess.run(
        [sys.executable, "-m", module_name],
        cwd=repo_root,
        env=_subprocess_env(repo_root),
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    if completed.returncode != 0:
        raise AssertionError(
            f"{module_name} exited with status {completed.returncode}"
        )


def run_discovered_expectation_suite(root_package: str, package_file: str | Path, suite_name: str) -> None:
    """运行指定 expectation 包目录下递归发现的全部 case。

    创建者: Codex
    最后修改人: Codex

    功能说明:
    - 递归发现 case 模块后逐个执行 `main()`。
    - 使用现有 `run_case(...)`/`raise_if_failures(...)` 汇总失败，保持 expectation 失败格式一致。

    使用示例:
    - `run_discovered_expectation_suite("expectation", __file__, "expectation")`

    关联文件:
    - spec: [`AGENTS.md`](../../AGENTS.md)
    - test: [`expectation/__main__.py`](../__main__.py)
    - 功能实现: [`expectation/utils/suite_runner.py`](suite_runner.py)
    """

    root_dir = Path(package_file).resolve().parent
    repo_root = _repo_root_for_package(root_dir)
    failures: list[tuple[str, BaseException]] = []
    module_names = discover_case_modules(root_package, package_file)
    for module_name in module_names:
        run_case(
            failures,
            module_name,
            lambda module_name=module_name: _run_case_module(module_name, repo_root),
        )
    raise_if_failures(f"{suite_name} expectation suite", failures)
