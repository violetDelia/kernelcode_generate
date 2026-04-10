"""mlir_gen compare tests.

创建者: 睡觉小分队
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 compare_mlir_file(...) 的 True/False 路径与非法文本返回 False 的行为。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- pytest -q --cov=kernel_gen.tools.mlir_gen_compare --cov-branch --cov-report=term-missing test/tools/test_mlir_gen_compare.py

使用示例:
- pytest -q test/tools/test_mlir_gen_compare.py

关联文件:
- 功能实现: kernel_gen/tools/mlir_gen_compare.py
- Spec 文档: spec/tools/mlir_gen_compare.md
- 测试文件: test/tools/test_mlir_gen_compare.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xdsl.parser import Parser

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.tools import mlir_gen_compare as compare_module

_SIMPLE_MODULE_TEXT = """builtin.module {
  func.func @main() {
    func.return
  }
}
"""


def _dummy_kernel() -> None:
    """占位 kernel，用于 compare_mlir_file 测试。

    创建者: 睡觉小分队
    最后一次更改: 金铲铲大作战

    功能说明:
    - 作为 compare_mlir_file 的入参占位，便于测试走通比较逻辑。

    使用示例:
    - compare_mlir_file(_dummy_kernel, None, None, path)

    关联文件:
    - spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
    - test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
    """

    return None


def _stub_mlir_gen(*_args: object, **_kwargs: object) -> object:
    """生成用于测试的固定 builtin.module。

    创建者: 睡觉小分队
    最后一次更改: 金铲铲大作战

    功能说明:
    - 返回固定 builtin.module，便于验证 compare_mlir_file 的比较逻辑。

    使用示例:
    - module = _stub_mlir_gen(_dummy_kernel)

    关联文件:
    - spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
    - test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
    """

    ctx = compare_module._build_default_context()
    return Parser(ctx, _SIMPLE_MODULE_TEXT).parse_module()


# TC-MLIR-GEN-COMPARE-001
# 创建者: 睡觉小分队
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 对齐 compare_mlir_file 的一致性比较路径。
# 测试目的: 验证 compare_mlir_file 在预期一致时返回 True。
# 使用示例: pytest -q test/tools/test_mlir_gen_compare.py -k test_compare_mlir_file_true
# 对应功能实现文件路径: kernel_gen/tools/mlir_gen_compare.py
# 对应 spec 文件路径: spec/tools/mlir_gen_compare.md
# 对应测试文件路径: test/tools/test_mlir_gen_compare.py
def test_compare_mlir_file_true(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    expected_path = tmp_path / "expected.mlir"
    expected_path.write_text(_SIMPLE_MODULE_TEXT, encoding="utf-8")
    monkeypatch.setattr(compare_module, "_load_mlir_gen", lambda: _stub_mlir_gen)

    ok = compare_module.compare_mlir_file(
        fn=_dummy_kernel,
        runtime_args=None,
        config=None,
        mlir_file=str(expected_path),
    )

    assert ok is True


# TC-MLIR-GEN-COMPARE-002
# 创建者: 睡觉小分队
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 对齐 compare_mlir_file 的不一致返回路径。
# 测试目的: 验证 compare_mlir_file 在预期不一致时返回 False。
# 使用示例: pytest -q test/tools/test_mlir_gen_compare.py -k test_compare_mlir_file_returns_false_on_mismatch
# 对应功能实现文件路径: kernel_gen/tools/mlir_gen_compare.py
# 对应 spec 文件路径: spec/tools/mlir_gen_compare.md
# 对应测试文件路径: test/tools/test_mlir_gen_compare.py
def test_compare_mlir_file_returns_false_on_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected_path = tmp_path / "expected.mlir"
    expected_path.write_text(
        _SIMPLE_MODULE_TEXT.replace("@main", "@other"), encoding="utf-8"
    )
    monkeypatch.setattr(compare_module, "_load_mlir_gen", lambda: _stub_mlir_gen)

    ok = compare_module.compare_mlir_file(
        fn=_dummy_kernel,
        runtime_args=(),
        config=None,
        mlir_file=str(expected_path),
    )

    assert ok is False


# TC-MLIR-GEN-COMPARE-003
# 创建者: 睡觉小分队
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 对齐 compare_mlir_file 的非法文本返回路径。
# 测试目的: 验证 compare_mlir_file 在非法文本时返回 False。
# 使用示例: pytest -q test/tools/test_mlir_gen_compare.py -k test_compare_mlir_file_returns_false_on_invalid_text
# 对应功能实现文件路径: kernel_gen/tools/mlir_gen_compare.py
# 对应 spec 文件路径: spec/tools/mlir_gen_compare.md
# 对应测试文件路径: test/tools/test_mlir_gen_compare.py
def test_compare_mlir_file_returns_false_on_invalid_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected_path = tmp_path / "invalid.mlir"
    expected_path.write_text("invalid mlir", encoding="utf-8")
    monkeypatch.setattr(compare_module, "_load_mlir_gen", lambda: _stub_mlir_gen)

    ok = compare_module.compare_mlir_file(
        fn=_dummy_kernel,
        runtime_args=None,
        config=None,
        mlir_file=str(expected_path),
    )

    assert ok is False
