"""kernel_gen package public import tests.

功能说明:
- 覆盖 `kernel_gen` 包根的公开导入行为。
- 锁定禁写 bytecode 场景下的 pycache 读取隔离，避免 full expectation 子进程读取既有
  `__pycache__` 或共享父进程自动 prefix 后出现随机解释器崩溃。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/test_kernel_gen_package.py`

关联文件:
- spec: ARCHITECTURE/plan/full_expectation_runner_stability_green_plan.md
- test: test/test_kernel_gen_package.py
- 功能实现: kernel_gen/__init__.py
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_kernel_gen_import(env_overrides: dict[str, str | None]) -> subprocess.CompletedProcess[str]:
    """在隔离子进程中导入 `kernel_gen` 并输出 pycache 配置。

    功能说明:
    - 通过公开包导入路径验证 `kernel_gen` 的 import-time 行为。
    - `None` 值表示从子进程环境中删除对应变量。

    使用示例:
    - result = _run_kernel_gen_import({"PYTHONDONTWRITEBYTECODE": "1"})
    """

    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    for key, value in env_overrides.items():
        if value is None:
            env.pop(key, None)
            continue
        env[key] = value
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "import os, sys, kernel_gen; print(os.environ.get('PYTHONPYCACHEPREFIX', '')); print(sys.pycache_prefix or '')",
        ],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_kernel_gen_import_isolates_pycache_when_bytecode_is_disabled() -> None:
    """验证禁写 bytecode 的公开包导入会安装进程唯一 pycache prefix。

    功能说明:
    - `PYTHONDONTWRITEBYTECODE=1` 是 full expectation 固定命令的一部分。
    - 未显式设置 `PYTHONPYCACHEPREFIX` 时，包导入应为当前进程和后续子进程安装隔离前缀。

    使用示例:
    - `pytest -q test/test_kernel_gen_package.py -k isolates_pycache`
    """

    result = _run_kernel_gen_import(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPYCACHEPREFIX": None,
        }
    )

    assert result.returncode == 0, result.stderr
    env_prefix, sys_prefix = result.stdout.strip().splitlines()
    assert env_prefix.startswith("/tmp/kernelcode_generate_pycache_")
    assert sys_prefix == env_prefix


def test_kernel_gen_import_respects_explicit_pycache_prefix() -> None:
    """验证调用方显式设置的 pycache prefix 不会被覆盖。

    功能说明:
    - 公开 Python 环境变量 `PYTHONPYCACHEPREFIX` 由调用方控制。
    - `kernel_gen` 只在缺省时安装隔离前缀，避免覆盖外部运行环境。

    使用示例:
    - `pytest -q test/test_kernel_gen_package.py -k respects_explicit`
    """

    explicit_prefix = "/tmp/kernelcode_generate_explicit_pycache"
    result = _run_kernel_gen_import(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPYCACHEPREFIX": explicit_prefix,
        }
    )

    assert result.returncode == 0, result.stderr
    env_prefix, sys_prefix = result.stdout.strip().splitlines()
    assert env_prefix == explicit_prefix
    assert sys_prefix == explicit_prefix


def test_kernel_gen_import_replaces_inherited_managed_pycache_prefix() -> None:
    """验证继承的项目自动 pycache prefix 会按当前进程重分配。

    功能说明:
    - full expectation 根 runner 会先导入 `kernel_gen`，再把环境传给 case 子进程。
    - 子进程继承父进程 `/tmp/kernelcode_generate_pycache_<pid>` 时，公开包导入应替换为当前进程
      独立前缀，避免多个 case 子进程共享父进程自动 prefix。

    使用示例:
    - `pytest -q test/test_kernel_gen_package.py -k replaces_inherited`
    """

    inherited_prefix = "/tmp/kernelcode_generate_pycache_1"
    result = _run_kernel_gen_import(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPYCACHEPREFIX": inherited_prefix,
        }
    )

    assert result.returncode == 0, result.stderr
    env_prefix, sys_prefix = result.stdout.strip().splitlines()
    assert env_prefix.startswith("/tmp/kernelcode_generate_pycache_")
    assert env_prefix != inherited_prefix
    assert sys_prefix == env_prefix
