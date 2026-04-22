"""requirements.txt tests.

创建者: 金铲铲大作战
最后一次更改: 小李飞刀

功能说明:
- 校验仓库根目录 `requirements.txt` 的说明头、依赖顺序与固定版本。

关联文件:
- 功能实现: requirements.txt
- Spec 文档: spec/script/pytest_config.md
- Spec 文档: spec/execute_engine/execute_engine_api.md
- 测试文件: test/script/test_requirements_txt.py

使用示例:
- pytest -q test/script/test_requirements_txt.py

覆盖率信息:
- `requirements.txt` 为文本依赖清单，按当前规则豁免 Python 模块覆盖率统计。

覆盖率命令:
- 豁免：`requirements.txt` 为文本依赖清单，不适用 Python 模块覆盖率统计。
- 功能校验命令：`pytest -q test/script/test_requirements_txt.py`
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
REQUIREMENTS_TXT = REPO_ROOT / "requirements.txt"
EXPECTED_REQUIREMENTS = [
    "numpy==2.4.4",
    "pytest==9.0.2",
    "pytest-cov==7.1.0",
    "sympy==1.14.0",
    "torch==2.11.0",
    "xdsl==0.62.1",
]

pytestmark = pytest.mark.infra


def _read_requirements_text() -> str:
    """读取仓库根目录 `requirements.txt`。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一封装 `requirements.txt` 的文本读取入口。
    - 供依赖顺序、固定版本与说明头断言复用。

    使用示例:
    - text = _read_requirements_text()

    关联文件:
    - 功能实现: [requirements.txt](requirements.txt)
    - Spec 文档: [spec/script/pytest_config.md](spec/script/pytest_config.md)
    - 测试文件: [test/script/test_requirements_txt.py](test/script/test_requirements_txt.py)
    """
    return REQUIREMENTS_TXT.read_text(encoding="utf-8")


def _read_execute_engine_api_spec() -> str:
    """读取 execute_engine 公开接口文档。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 统一封装 `spec/execute_engine/execute_engine_api.md` 的文本读取入口。
    - 供依赖清单与公开接口口径一致性断言复用。

    使用示例:
    - text = _read_execute_engine_api_spec()

    关联文件:
    - 功能实现: [requirements.txt](requirements.txt)
    - Spec 文档: [spec/execute_engine/execute_engine_api.md](spec/execute_engine/execute_engine_api.md)
    - 测试文件: [test/script/test_requirements_txt.py](test/script/test_requirements_txt.py)
    """
    return (REPO_ROOT / "spec/execute_engine/execute_engine_api.md").read_text(encoding="utf-8")


def _package_lines() -> list[str]:
    """提取 `requirements.txt` 中的实际依赖行。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 过滤空行与注释行，只保留 `package==version` 形式的依赖项。
    - 保持文件中的声明顺序，便于做稳定列表断言。

    使用示例:
    - lines = _package_lines()

    关联文件:
    - 功能实现: [requirements.txt](requirements.txt)
    - Spec 文档: [spec/execute_engine/execute_engine_api.md](spec/execute_engine/execute_engine_api.md)
    - 测试文件: [test/script/test_requirements_txt.py](test/script/test_requirements_txt.py)
    """
    return [
        line.strip()
        for line in _read_requirements_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


# TC-REQ-001
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-18 16:00:00 +0800
# 最近一次运行成功时间: 2026-04-18 16:00:00 +0800
# 测试目的: 验证 requirements.txt 包含功能说明、使用示例与关联文件头注释。
# 对应功能实现文件路径: requirements.txt
# 对应 spec 文件路径: spec/script/pytest_config.md
# 对应测试文件路径: test/script/test_requirements_txt.py
def test_requirements_txt_has_documentation_header() -> None:
    text = _read_requirements_text()
    assert "# 功能说明:" in text
    assert "# 使用示例:" in text
    assert "# 关联文件:" in text
    assert "`torch.Tensor`" in text
    assert "`numpy.ndarray`" in text
    assert "# - spec: `spec/script/pytest_config.md`" in text
    assert "# - spec: `spec/execute_engine/execute_engine_api.md`" in text
    assert "# - test: `test/script/test_requirements_txt.py`" in text
    assert "# - 功能实现: `requirements.txt`" in text


# TC-REQ-002
# 创建者: 金铲铲大作战
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-18 16:00:00 +0800
# 最近一次运行成功时间: 2026-04-18 16:00:00 +0800
# 测试目的: 验证 requirements.txt 的依赖顺序与固定版本符合当前收口结果。
# 对应功能实现文件路径: requirements.txt
# 对应 spec 文件路径: spec/execute_engine/execute_engine_api.md
# 对应测试文件路径: test/script/test_requirements_txt.py
def test_requirements_txt_pins_expected_dependencies() -> None:
    assert REQUIREMENTS_TXT.exists()
    assert _package_lines() == EXPECTED_REQUIREMENTS


# TC-REQ-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-18 16:00:00 +0800
# 最近一次运行成功时间: 2026-04-18 16:00:00 +0800
# 测试目的: 验证 requirements.txt 覆盖 execute_engine 公开内存参数文档提到的 numpy/torch 依赖。
# 对应功能实现文件路径: requirements.txt
# 对应 spec 文件路径: spec/execute_engine/execute_engine_api.md
# 对应测试文件路径: test/script/test_requirements_txt.py
def test_requirements_txt_covers_execute_engine_memory_arg_dependencies() -> None:
    requirements = _package_lines()
    spec_text = _read_execute_engine_api_spec()

    assert "torch.Tensor" in spec_text
    assert "numpy.ndarray" in spec_text
    assert "torch.zeros((2, 3))" in spec_text
    assert any(line.startswith("torch==") for line in requirements)
    assert any(line.startswith("numpy==") for line in requirements)
