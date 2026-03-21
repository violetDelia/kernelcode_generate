"""pass_manager tests.

创建者: 李白
最后一次更改: 李白

功能说明:
- 覆盖 kernel_gen/pass/pass_manager.py 的 Pass 管理行为。

使用示例:
- pytest -q test/pass/test_pass_manager.py

关联文件:
- 功能实现: kernel_gen/pass/pass_manager.py
- Spec 文档: spec/pass/pass_manager.md
- 测试文件: test/pass/test_pass_manager.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import importlib
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

pass_module = importlib.import_module("kernel_gen.pass.pass_manager")
Pass = pass_module.Pass
PassManager = pass_module.PassManager


# TC-PASS-001
# 创建者: 李白
# 最后一次更改: 李白
# 最近一次运行测试时间: 2026-03-21 22:02:06 +0800
# 最近一次运行成功时间: 2026-03-21 22:02:06 +0800
# 功能说明: 验证单 Pass 正常执行。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_pass_manager_single_pass
# 对应功能实现文件路径: kernel_gen/pass/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
def test_pass_manager_single_pass() -> None:
    class AddOnePass(Pass):
        name = "add-one"

        def run(self, target):
            return target + 1

    pm = PassManager(name="opt")
    pm.add_pass(AddOnePass())
    assert pm.run(1) == 2


# TC-PASS-002
# 创建者: 李白
# 最后一次更改: 李白
# 最近一次运行测试时间: 2026-03-21 22:02:06 +0800
# 最近一次运行成功时间: 2026-03-21 22:02:06 +0800
# 功能说明: 验证多 Pass 顺序执行。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_pass_manager_multiple_passes_order
# 对应功能实现文件路径: kernel_gen/pass/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
def test_pass_manager_multiple_passes_order() -> None:
    class AddOnePass(Pass):
        name = "add-one"

        def run(self, target):
            return target + 1

    class TimesTwoPass(Pass):
        name = "times-two"

        def run(self, target):
            return target * 2

    pm = PassManager()
    pm.extend([AddOnePass(), TimesTwoPass()])
    assert pm.run(2) == 6


# TC-PASS-003
# 创建者: 李白
# 最后一次更改: 李白
# 最近一次运行测试时间: 2026-03-21 22:02:06 +0800
# 最近一次运行成功时间: 2026-03-21 22:02:06 +0800
# 功能说明: 验证空管理器返回原输入。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_pass_manager_empty_returns_input
# 对应功能实现文件路径: kernel_gen/pass/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
def test_pass_manager_empty_returns_input() -> None:
    pm = PassManager()
    data = {"key": "value"}
    assert pm.run(data) is data


# TC-PASS-004
# 创建者: 李白
# 最后一次更改: 李白
# 最近一次运行测试时间: 2026-03-21 22:02:06 +0800
# 最近一次运行成功时间: 2026-03-21 22:02:06 +0800
# 功能说明: 验证非法 Pass 类型报错。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_pass_manager_invalid_pass_type
# 对应功能实现文件路径: kernel_gen/pass/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
def test_pass_manager_invalid_pass_type() -> None:
    pm = PassManager()
    with pytest.raises(TypeError):
        pm.add_pass("not-a-pass")  # type: ignore[arg-type]

    with pytest.raises(TypeError):
        pm.extend([object()])  # type: ignore[arg-type]

    class BadNamePass(Pass):
        name = 123

        def run(self, target):
            return target

    with pytest.raises(TypeError):
        pm.add_pass(BadNamePass())


# TC-PASS-005
# 创建者: 李白
# 最后一次更改: 李白
# 最近一次运行测试时间: 2026-03-21 22:02:06 +0800
# 最近一次运行成功时间: 2026-03-21 22:02:06 +0800
# 功能说明: 验证 Pass 异常向上抛出。
# 使用示例: pytest -q test/pass/test_pass_manager.py -k test_pass_manager_exception_propagation
# 对应功能实现文件路径: kernel_gen/pass/pass_manager.py
# 对应 spec 文件路径: spec/pass/pass_manager.md
# 对应测试文件路径: test/pass/test_pass_manager.py
def test_pass_manager_exception_propagation() -> None:
    class FailPass(Pass):
        name = "fail-pass"

        def run(self, target):
            raise ValueError("boom")

    pm = PassManager()
    pm.add_pass(FailPass())
    with pytest.raises(ValueError):
        _ = pm.run(1)
