"""mlir_gen compare tests.

创建者: 睡觉小分队
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 mlir_gen_compare(...) / mlir_gen_compare_text(...) / compare_mlir_file(...) 的 True/False 路径与非法文本返回 False 的行为。

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

from kernel_gen.dsl import mlir_gen as mlir_gen_package

_SIMPLE_MODULE_TEXT = """builtin.module {
  func.func @main() {
    func.return
  }
}
"""

_ARITH_MODULE_TEXT = """builtin.module {
  func.func @main() {
    %0 = arith.constant 0 : i32
    func.return
  }
}
"""


def _dummy_kernel() -> None:
    """占位 kernel，用于 mlir_gen_compare 测试。

    创建者: 睡觉小分队
    最后一次更改: 金铲铲大作战

    功能说明:
    - 作为 mlir_gen_compare 的入参占位，便于测试走通比较逻辑。

    使用示例:
    - mlir_gen_compare(_dummy_kernel, None, None, path)

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
    - 返回固定 builtin.module，便于验证 mlir_gen_compare 的比较逻辑。

    使用示例:
    - module = _stub_mlir_gen(_dummy_kernel)

    关联文件:
    - spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
    - test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
    """

    ctx = _build_min_context()
    return Parser(ctx, _SIMPLE_MODULE_TEXT).parse_module()


def _build_min_context() -> object:
    """构造最小可用 Context，避免导入可选依赖失败。

    创建者: 睡觉小分队
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅加载 builtin/func/arith/nn/kernel，满足 mlir_gen_compare 的解析/打印路径。

    使用示例:
    - ctx = _build_min_context()

    关联文件:
    - spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
    - test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
    """

    from xdsl.context import Context
    from xdsl.dialects.arith import Arith
    from xdsl.dialects.builtin import Builtin
    from xdsl.dialects.func import Func

    from kernel_gen.dialect.dma import Dma
    from kernel_gen.dialect.kernel import Kernel
    from kernel_gen.dialect.nn import Nn

    ctx = Context()
    ctx.load_dialect(Builtin)
    ctx.load_dialect(Func)
    ctx.load_dialect(Arith)
    ctx.load_dialect(Nn)
    ctx.load_dialect(Dma)
    ctx.load_dialect(Kernel)
    return ctx


# TC-MLIR-GEN-COMPARE-001
# 创建者: 睡觉小分队
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 对齐 mlir_gen_compare 的一致性比较路径。
# 测试目的: 验证 mlir_gen_compare 在预期一致时返回 True。
# 使用示例: pytest -q test/tools/test_mlir_gen_compare.py -k test_mlir_gen_compare_true
# 对应功能实现文件路径: kernel_gen/tools/mlir_gen_compare.py
# 对应 spec 文件路径: spec/tools/mlir_gen_compare.md
# 对应测试文件路径: test/tools/test_mlir_gen_compare.py
def test_mlir_gen_compare_true(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    expected_path = tmp_path / "expected.mlir"
    expected_path.write_text(_SIMPLE_MODULE_TEXT, encoding="utf-8")
    monkeypatch.setattr(mlir_gen_package, "mlir_gen", _stub_mlir_gen)

    ok = compare_module.mlir_gen_compare(
        fn=_dummy_kernel,
        runtime_args=None,
        config=None,
        mlir_file=str(expected_path),
    )

    assert ok is True


# TC-MLIR-GEN-COMPARE-011
# 创建者: 睡觉小分队
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 对齐 compare_mlir_file 兼容接口与 mlir_gen_compare 的等价行为。
# 测试目的: 验证 compare_mlir_file 在预期一致时返回 True。
# 使用示例: pytest -q test/tools/test_mlir_gen_compare.py -k test_compare_mlir_file_alias_true
# 对应功能实现文件路径: kernel_gen/tools/mlir_gen_compare.py
# 对应 spec 文件路径: spec/tools/mlir_gen_compare.md
# 对应测试文件路径: test/tools/test_mlir_gen_compare.py
def test_compare_mlir_file_alias_true(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    expected_path = tmp_path / "expected_alias.mlir"
    expected_path.write_text(_SIMPLE_MODULE_TEXT, encoding="utf-8")
    monkeypatch.setattr(mlir_gen_package, "mlir_gen", _stub_mlir_gen)

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
# 功能说明: 对齐 mlir_gen_compare 的不一致返回路径。
# 测试目的: 验证 mlir_gen_compare 在预期不一致时返回 False。
# 使用示例: pytest -q test/tools/test_mlir_gen_compare.py -k test_mlir_gen_compare_returns_false_on_mismatch
# 对应功能实现文件路径: kernel_gen/tools/mlir_gen_compare.py
# 对应 spec 文件路径: spec/tools/mlir_gen_compare.md
# 对应测试文件路径: test/tools/test_mlir_gen_compare.py
def test_mlir_gen_compare_returns_false_on_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected_path = tmp_path / "expected.mlir"
    expected_path.write_text(
        _SIMPLE_MODULE_TEXT.replace("@main", "@other"), encoding="utf-8"
    )
    monkeypatch.setattr(mlir_gen_package, "mlir_gen", _stub_mlir_gen)

    ok = compare_module.mlir_gen_compare(
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
# 功能说明: 对齐 mlir_gen_compare 的非法文本返回路径。
# 测试目的: 验证 mlir_gen_compare 在非法文本时返回 False。
# 使用示例: pytest -q test/tools/test_mlir_gen_compare.py -k test_mlir_gen_compare_returns_false_on_invalid_text
# 对应功能实现文件路径: kernel_gen/tools/mlir_gen_compare.py
# 对应 spec 文件路径: spec/tools/mlir_gen_compare.md
# 对应测试文件路径: test/tools/test_mlir_gen_compare.py
def test_mlir_gen_compare_returns_false_on_invalid_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected_path = tmp_path / "invalid.mlir"
    expected_path.write_text("invalid mlir", encoding="utf-8")
    monkeypatch.setattr(mlir_gen_package, "mlir_gen", _stub_mlir_gen)

    ok = compare_module.mlir_gen_compare(
        fn=_dummy_kernel,
        runtime_args=None,
        config=None,
        mlir_file=str(expected_path),
    )

    assert ok is False


# TC-MLIR-GEN-COMPARE-004
# 创建者: 睡觉小分队
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 对齐 mlir_gen_compare 读取非 UTF-8 文本时返回 False 的分支。
# 测试目的: 验证遇到 UnicodeError 时 mlir_gen_compare 返回 False（不抛异常）。
# 使用示例: pytest -q test/tools/test_mlir_gen_compare.py -k test_mlir_gen_compare_returns_false_on_non_utf8_text
# 对应功能实现文件路径: kernel_gen/tools/mlir_gen_compare.py
# 对应 spec 文件路径: spec/tools/mlir_gen_compare.md
# 对应测试文件路径: test/tools/test_mlir_gen_compare.py
def test_mlir_gen_compare_returns_false_on_non_utf8_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected_path = tmp_path / "non_utf8.mlir"
    expected_path.write_bytes(b"\xff\xfe\xfa")
    monkeypatch.setattr(mlir_gen_package, "mlir_gen", _stub_mlir_gen)

    ok = compare_module.mlir_gen_compare(
        fn=_dummy_kernel,
        runtime_args=None,
        config=None,
        mlir_file=str(expected_path),
    )

    assert ok is False


# TC-MLIR-GEN-COMPARE-005
# 创建者: 睡觉小分队
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 对齐 mlir_gen_compare 的 arith dialect 场景解析与归一化比较。
# 测试目的: 验证 mlir_gen_compare 在 actual/expected 含 arith.constant 时返回 True（不抛 ParseError）。
# 使用示例: pytest -q test/tools/test_mlir_gen_compare.py -k test_mlir_gen_compare_true_with_arith
# 对应功能实现文件路径: kernel_gen/tools/mlir_gen_compare.py
# 对应 spec 文件路径: spec/tools/mlir_gen_compare.md
# 对应测试文件路径: test/tools/test_mlir_gen_compare.py
def test_mlir_gen_compare_true_with_arith(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected_path = tmp_path / "expected_arith.mlir"
    expected_path.write_text(_ARITH_MODULE_TEXT, encoding="utf-8")

    def _stub_mlir_gen_arith(*_args: object, **_kwargs: object) -> object:
        ctx = _build_min_context()
        return Parser(ctx, _ARITH_MODULE_TEXT).parse_module()

    monkeypatch.setattr(mlir_gen_package, "mlir_gen", _stub_mlir_gen_arith)

    ok = compare_module.mlir_gen_compare(
        fn=_dummy_kernel,
        runtime_args=None,
        config=None,
        mlir_file=str(expected_path),
    )

    assert ok is True


# TC-MLIR-GEN-COMPARE-008
# 创建者: 睡觉小分队
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 对齐 mlir_gen_compare 在 actual 非 builtin.module 时的返回语义。
# 测试目的: 验证当 mlir_gen(...) 返回值不是 builtin.module 时，mlir_gen_compare 返回 False（不抛 TypeError）。
# 使用示例: pytest -q test/tools/test_mlir_gen_compare.py -k test_mlir_gen_compare_returns_false_when_actual_not_module
# 对应功能实现文件路径: kernel_gen/tools/mlir_gen_compare.py
# 对应 spec 文件路径: spec/tools/mlir_gen_compare.md
# 对应测试文件路径: test/tools/test_mlir_gen_compare.py
def test_mlir_gen_compare_returns_false_when_actual_not_module(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected_path = tmp_path / "expected.mlir"
    expected_path.write_text(_SIMPLE_MODULE_TEXT, encoding="utf-8")
    monkeypatch.setattr(mlir_gen_package, "mlir_gen", lambda *_a, **_k: object())

    ok = compare_module.mlir_gen_compare(
        fn=_dummy_kernel,
        runtime_args=None,
        config=None,
        mlir_file=str(expected_path),
    )

    assert ok is False


# TC-MLIR-GEN-COMPARE-003A
# 创建者: 金铲铲大作战
# 最后更改: 金铲铲大作战
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 验证 mlir_gen_compare 不再对旧 expectation 中的 dma.view 结果 dtype 做兼容修补。
# 测试目的: 锁定 expected 文本若仍保留旧 f32 结果类型，会直接比较失败。
# 使用示例: pytest -q test/tools/test_mlir_gen_compare.py -k test_mlir_gen_compare_does_not_repair_legacy_dma_view_result_dtype
# 对应功能实现文件路径: kernel_gen/tools/mlir_gen_compare.py
# 对应 spec 文件路径: spec/tools/mlir_gen_compare.md
# 对应测试文件路径: test/tools/test_mlir_gen_compare.py
def test_mlir_gen_compare_does_not_repair_legacy_dma_view_result_dtype(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actual_text = """builtin.module {
  func.func @main(%0 : !nn.memory<[2], [1], f16, #nn.space<global>>, %1 : i32, %2 : i32, %3 : i32, %4 : i32, %5 : i32, %6 : i32) {
    %7 = "dma.view"(%0, %1, %2, %3, %4, %5, %6) <{operandSegmentSizes = array<i32: 1, 2, 2, 2>}> : (!nn.memory<[2], [1], f16, #nn.space<global>>, i32, i32, i32, i32, i32, i32) -> !nn.memory<[2], [1], f16, #nn.space<global>>
    func.return
  }
}
"""
    expected_text = actual_text.replace(
        "-> !nn.memory<[2], [1], f16, #nn.space<global>>",
        "-> !nn.memory<[2], [1], f32, #nn.space<global>>",
        1,
    )

    def _stub_mlir_gen_dma(*_args: object, **_kwargs: object) -> object:
        ctx = _build_min_context()
        return Parser(ctx, actual_text).parse_module()

    monkeypatch.setattr(mlir_gen_package, "mlir_gen", _stub_mlir_gen_dma)

    ok = compare_module.mlir_gen_compare_text(
        fn=_dummy_kernel,
        runtime_args=None,
        config=None,
        mlir_text=expected_text,
    )

    assert ok is False


# TC-MLIR-GEN-COMPARE-009
# 创建者: 守护最好的爱莉希雅
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 对齐 mlir_gen_compare_text 的一致性比较路径。
# 测试目的: 验证 mlir_gen_compare_text 在预期一致时返回 True。
# 使用示例: pytest -q test/tools/test_mlir_gen_compare.py -k test_mlir_gen_compare_text_true
# 对应功能实现文件路径: kernel_gen/tools/mlir_gen_compare.py
# 对应 spec 文件路径: spec/tools/mlir_gen_compare.md
# 对应测试文件路径: test/tools/test_mlir_gen_compare.py
def test_mlir_gen_compare_text_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mlir_gen_package, "mlir_gen", _stub_mlir_gen)

    ok = compare_module.mlir_gen_compare_text(
        fn=_dummy_kernel,
        runtime_args=None,
        config=None,
        mlir_text=_SIMPLE_MODULE_TEXT,
    )

    assert ok is True


# TC-MLIR-GEN-COMPARE-010
# 创建者: 守护最好的爱莉希雅
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 对齐 mlir_gen_compare_text 的非法文本返回路径。
# 测试目的: 验证 mlir_gen_compare_text 在非法文本时返回 False（不抛 ParseError）。
# 使用示例: pytest -q test/tools/test_mlir_gen_compare.py -k test_mlir_gen_compare_text_returns_false_on_invalid_text
# 对应功能实现文件路径: kernel_gen/tools/mlir_gen_compare.py
# 对应 spec 文件路径: spec/tools/mlir_gen_compare.md
# 对应测试文件路径: test/tools/test_mlir_gen_compare.py
def test_mlir_gen_compare_text_returns_false_on_invalid_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(mlir_gen_package, "mlir_gen", _stub_mlir_gen)

    ok = compare_module.mlir_gen_compare_text(
        fn=_dummy_kernel,
        runtime_args=None,
        config=None,
        mlir_text="invalid mlir",
    )

    assert ok is False
