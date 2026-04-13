"""mlir_gen compare tests.

创建者: 睡觉小分队
最后一次更改: jcc你莫辜负

功能说明:
- 覆盖 mlir_gen_compare(...) / mlir_gen_compare_text(...) / compare_mlir_file(...) 的 True/False 路径与非法文本返回 False 的行为。

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

from kernel_gen.dsl.ast import AstParseError
from kernel_gen.dsl.ast_visitor import AstVisitorError
from kernel_gen.tools import mlir_gen_compare as compare_module

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

    ctx = compare_module._build_default_context()
    return Parser(ctx, _SIMPLE_MODULE_TEXT).parse_module()


def _build_min_context() -> object:
    """构造最小可用 Context，避免导入可选依赖失败。

    创建者: 睡觉小分队
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅加载 builtin/func/arith/nn/kernel，满足 mlir_gen_compare 的解析/打印路径。

    使用示例:
    - monkeypatch.setattr(compare_module, "_build_default_context", _build_min_context)

    关联文件:
    - spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
    - test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
    """

    from xdsl.context import Context
    from xdsl.dialects.arith import Arith
    from xdsl.dialects.builtin import Builtin
    from xdsl.dialects.func import Func

    from kernel_gen.dialect.kernel import Kernel
    from kernel_gen.dialect.nn import Nn

    ctx = Context()
    ctx.load_dialect(Builtin)
    ctx.load_dialect(Func)
    ctx.load_dialect(Arith)
    ctx.load_dialect(Nn)
    ctx.load_dialect(Kernel)
    return ctx


def _build_module_with_arith_constant() -> object:
    """构造一个包含 arith.constant 的最小 builtin.module。

    创建者: 睡觉小分队
    最后一次更改: 小李飞刀

    功能说明:
    - 用于覆盖 mlir_gen_compare 在 actual/expected 含 arith dialect op 时的比较路径。
    - 该 helper 直接用 xdsl op 构造 module，不依赖 Context 解析，便于模拟“Context 未加载 arith”场景。

    使用示例:
    - module = _build_module_with_arith_constant()

    关联文件:
    - spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
    - test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
    """

    from xdsl.dialects.arith import ConstantOp
    from xdsl.dialects.builtin import ModuleOp
    from xdsl.dialects.func import FuncOp, ReturnOp
    from xdsl.ir import Block, Region

    block = Block()
    block.add_op(ConstantOp.from_int_and_width(0, 32))
    block.add_op(ReturnOp())
    func = FuncOp.from_region("main", [], [], Region(block))
    return ModuleOp([func])


_LEGACY_SYMBOL_FOR_TEXT = """builtin.module {
  func.func @main(%arg0 : !nn.memory<[8], [1], f32, #nn.space<global>>) {
    %c0 = symbol.const 0 : !symbol.int<"0">
    %c8 = symbol.const 8 : !symbol.int<"8">
    %c2 = symbol.const 2 : !symbol.int<"2">
    symbol.for %i = %c0 to %c8 step %c2 : !symbol.int<"0">, !symbol.int<"8">, !symbol.int<"2"> {
      %tile = "dma.load"(%arg0, %i, %c2, %c2) <{operandSegmentSizes = array<i32: 1, 1, 1, 1>}> {space = #nn.space<global>} : (!nn.memory<[8], [1], f32, #nn.space<global>>, !symbol.int<"index">, !symbol.int<"2">, !symbol.int<"2">) -> !nn.memory<[8], [1], f32, #nn.space<global>>
    }
    func.return
  }
}
"""


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
    monkeypatch.setattr(compare_module, "_load_mlir_gen", lambda: _stub_mlir_gen)
    monkeypatch.setattr(compare_module, "_build_default_context", _build_min_context)

    ok = compare_module.mlir_gen_compare(
        fn=_dummy_kernel,
        runtime_args=None,
        config=None,
        mlir_file=str(expected_path),
    )

    assert ok is True


# TC-MLIR-GEN-COMPARE-011
# 创建者: 睡觉小分队
# 最后一次更改: 小李飞刀
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
    monkeypatch.setattr(compare_module, "_load_mlir_gen", lambda: _stub_mlir_gen)
    monkeypatch.setattr(compare_module, "_build_default_context", _build_min_context)

    ok = compare_module.compare_mlir_file(
        fn=_dummy_kernel,
        runtime_args=None,
        config=None,
        mlir_file=str(expected_path),
    )

    assert ok is True


# TC-MLIR-GEN-COMPARE-012
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 对齐 compare 对前端 lowering 值域错误的异常保留语义。
# 测试目的: 验证 compare 会将 launch_kernel 非法 extent 继续暴露为 AstVisitorError。
# 使用示例: pytest -q test/tools/test_mlir_gen_compare.py -k test_mlir_gen_compare_text_preserves_launch_kernel_lowering_error
# 对应功能实现文件路径: kernel_gen/tools/mlir_gen_compare.py
# 对应 spec 文件路径: spec/tools/mlir_gen_compare.md
# 对应测试文件路径: test/tools/test_mlir_gen_compare.py
def test_mlir_gen_compare_text_preserves_launch_kernel_lowering_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_ast_visitor_error(*_args: object, **_kwargs: object) -> object:
        raise AstVisitorError("launch_kernel thread must be > 0")

    monkeypatch.setattr(compare_module, "_load_mlir_gen", lambda: _raise_ast_visitor_error)

    with pytest.raises(AstVisitorError, match="launch_kernel thread must be > 0"):
        compare_module.mlir_gen_compare_text(
            fn=_dummy_kernel,
            runtime_args=(),
            config=None,
            mlir_text=_SIMPLE_MODULE_TEXT,
        )


# TC-MLIR-GEN-COMPARE-013
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 对齐 compare 对 mlir_gen 原始类型错误的透传语义。
# 测试目的: 验证 compare 遇到 symbol.compare 的输入类型错误时直接透传 AstVisitorError。
# 使用示例: pytest -q test/tools/test_mlir_gen_compare.py -k test_mlir_gen_compare_text_propagates_ast_visitor_type_error
# 对应功能实现文件路径: kernel_gen/tools/mlir_gen_compare.py
# 对应 spec 文件路径: spec/tools/mlir_gen_compare.md
# 对应测试文件路径: test/tools/test_mlir_gen_compare.py
def test_mlir_gen_compare_text_propagates_ast_visitor_type_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_ast_visitor_error(*_args: object, **_kwargs: object) -> object:
        raise AstVisitorError("Unsupported comparison type")

    monkeypatch.setattr(compare_module, "_load_mlir_gen", lambda: _raise_ast_visitor_error)

    with pytest.raises(AstVisitorError, match="Unsupported comparison type"):
        compare_module.mlir_gen_compare_text(
            fn=_dummy_kernel,
            runtime_args=(),
            config=None,
            mlir_text=_SIMPLE_MODULE_TEXT,
        )


# TC-MLIR-GEN-COMPARE-013A
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 对齐 compare 对 mlir_gen 原始 parse 错误的透传语义。
# 测试目的: 验证 compare 不会把 `Missing annotation` 改写成其他异常类型或消息。
# 使用示例: pytest -q test/tools/test_mlir_gen_compare.py -k test_mlir_gen_compare_text_propagates_missing_annotation_parse_error
# 对应功能实现文件路径: kernel_gen/tools/mlir_gen_compare.py
# 对应 spec 文件路径: spec/tools/mlir_gen_compare.md
# 对应测试文件路径: test/tools/test_mlir_gen_compare.py
def test_mlir_gen_compare_text_propagates_missing_annotation_parse_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_ast_parse_error(*_args: object, **_kwargs: object) -> object:
        raise AstParseError("Missing annotation", [])

    monkeypatch.setattr(compare_module, "_load_mlir_gen", lambda: _raise_ast_parse_error)

    with pytest.raises(AstParseError, match="Missing annotation"):
        compare_module.mlir_gen_compare_text(
            fn=_dummy_kernel,
            runtime_args=(1.25,),
            config=None,
            mlir_text=_SIMPLE_MODULE_TEXT,
        )


# TC-MLIR-GEN-COMPARE-014
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 对齐 compare 对零步长 parse 失败的原始异常透传语义。
# 测试目的: 验证 compare 会直接透传 LoopRange 零步长产生的 AstParseError。
# 使用示例: pytest -q test/tools/test_mlir_gen_compare.py -k test_mlir_gen_compare_text_propagates_zero_step_parse_error
# 对应功能实现文件路径: kernel_gen/tools/mlir_gen_compare.py
# 对应 spec 文件路径: spec/tools/mlir_gen_compare.md
# 对应测试文件路径: test/tools/test_mlir_gen_compare.py
def test_mlir_gen_compare_text_propagates_zero_step_parse_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_ast_parse_error(*_args: object, **_kwargs: object) -> object:
        raise AstParseError("step must not be 0", [])

    monkeypatch.setattr(compare_module, "_load_mlir_gen", lambda: _raise_ast_parse_error)

    with pytest.raises(AstParseError, match="step must not be 0"):
        compare_module.mlir_gen_compare_text(
            fn=_dummy_kernel,
            runtime_args=(),
            config=None,
            mlir_text=_SIMPLE_MODULE_TEXT,
        )


# TC-MLIR-GEN-COMPARE-015
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 对齐 compare 对旧零步长 lowering 文案的原始异常透传语义。
# 测试目的: 验证 compare 遇到既有 AstVisitorError 时保留原始异常类型与消息。
# 使用示例: pytest -q test/tools/test_mlir_gen_compare.py -k test_mlir_gen_compare_text_propagates_existing_zero_step_ast_visitor_error
# 对应功能实现文件路径: kernel_gen/tools/mlir_gen_compare.py
# 对应 spec 文件路径: spec/tools/mlir_gen_compare.md
# 对应测试文件路径: test/tools/test_mlir_gen_compare.py
def test_mlir_gen_compare_text_propagates_existing_zero_step_ast_visitor_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_ast_visitor_error(*_args: object, **_kwargs: object) -> object:
        raise AstVisitorError("for range step must not be zero")

    monkeypatch.setattr(compare_module, "_load_mlir_gen", lambda: _raise_ast_visitor_error)

    with pytest.raises(AstVisitorError, match="for range step must not be zero"):
        compare_module.mlir_gen_compare_text(
            fn=_dummy_kernel,
            runtime_args=(),
            config=None,
            mlir_text=_SIMPLE_MODULE_TEXT,
        )


# TC-MLIR-GEN-COMPARE-015A
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 对齐 compare 对 helper 直接抛 ValueError 的原始异常透传语义。
# 测试目的: 验证 compare 不会把裸 `step must not be 0` 改写为其他异常。
# 使用示例: pytest -q test/tools/test_mlir_gen_compare.py -k test_mlir_gen_compare_text_propagates_raw_zero_step_value_error
# 对应功能实现文件路径: kernel_gen/tools/mlir_gen_compare.py
# 对应 spec 文件路径: spec/tools/mlir_gen_compare.md
# 对应测试文件路径: test/tools/test_mlir_gen_compare.py
def test_mlir_gen_compare_text_propagates_raw_zero_step_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_value_error(*_args: object, **_kwargs: object) -> object:
        raise ValueError("step must not be 0")

    monkeypatch.setattr(compare_module, "_load_mlir_gen", lambda: _raise_value_error)

    with pytest.raises(ValueError, match="step must not be 0"):
        compare_module.mlir_gen_compare_text(
            fn=_dummy_kernel,
            runtime_args=(),
            config=None,
            mlir_text=_SIMPLE_MODULE_TEXT,
        )


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
    monkeypatch.setattr(compare_module, "_load_mlir_gen", lambda: _stub_mlir_gen)
    monkeypatch.setattr(compare_module, "_build_default_context", _build_min_context)

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
    monkeypatch.setattr(compare_module, "_load_mlir_gen", lambda: _stub_mlir_gen)
    monkeypatch.setattr(compare_module, "_build_default_context", _build_min_context)

    ok = compare_module.mlir_gen_compare(
        fn=_dummy_kernel,
        runtime_args=None,
        config=None,
        mlir_file=str(expected_path),
    )

    assert ok is False


# TC-MLIR-GEN-COMPARE-012
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 对齐 legacy symbol.for expectation 文本到当前 dialect 语法。
# 测试目的: 验证 compare 工具会为旧 `symbol.for` 头部补齐 iter attr，并把 `!symbol.int<"index">` 改写为对应 `!symbol.iter<...>`。
# 使用示例: pytest -q test/tools/test_mlir_gen_compare.py -k test_rewrite_legacy_symbol_for_expected_text
# 对应功能实现文件路径: kernel_gen/tools/mlir_gen_compare.py
# 对应 spec 文件路径: spec/tools/mlir_gen_compare.md
# 对应测试文件路径: test/tools/test_mlir_gen_compare.py
def test_rewrite_legacy_symbol_for_expected_text() -> None:
    rewritten = compare_module._rewrite_legacy_symbol_for_expected_text(_LEGACY_SYMBOL_FOR_TEXT)

    assert '{iter = #symbol.iter<start = "0", end = "8", step = "2">} {' in rewritten
    assert '!symbol.iter<start = "0", end = "8", step = "2">' in rewritten
    assert '!symbol.int<"index">' not in rewritten


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
    monkeypatch.setattr(compare_module, "_load_mlir_gen", lambda: _stub_mlir_gen)
    monkeypatch.setattr(compare_module, "_build_default_context", _build_min_context)

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
        ctx = compare_module._build_default_context()
        return Parser(ctx, _ARITH_MODULE_TEXT).parse_module()

    monkeypatch.setattr(compare_module, "_load_mlir_gen", lambda: _stub_mlir_gen_arith)
    monkeypatch.setattr(compare_module, "_build_default_context", _build_min_context)

    ok = compare_module.mlir_gen_compare(
        fn=_dummy_kernel,
        runtime_args=None,
        config=None,
        mlir_file=str(expected_path),
    )

    assert ok is True


# TC-MLIR-GEN-COMPARE-006
# 创建者: 睡觉小分队
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 对齐 mlir_gen_compare 的“归一化二次解析失败 -> False”兜底行为。
# 测试目的: 验证当默认 Context 未加载 arith 时，normalize 过程解析失败不应抛异常，应返回 False。
# 使用示例: pytest -q test/tools/test_mlir_gen_compare.py -k test_mlir_gen_compare_returns_false_on_normalize_parse_error
# 对应功能实现文件路径: kernel_gen/tools/mlir_gen_compare.py
# 对应 spec 文件路径: spec/tools/mlir_gen_compare.md
# 对应测试文件路径: test/tools/test_mlir_gen_compare.py
def test_mlir_gen_compare_returns_false_on_normalize_parse_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected_path = tmp_path / "expected_simple.mlir"
    expected_path.write_text(_SIMPLE_MODULE_TEXT, encoding="utf-8")

    actual_module = _build_module_with_arith_constant()
    monkeypatch.setattr(compare_module, "_load_mlir_gen", lambda: lambda *_a, **_k: actual_module)

    def _ctx_without_arith() -> object:
        from xdsl.context import Context
        from xdsl.dialects.builtin import Builtin
        from xdsl.dialects.func import Func

        from kernel_gen.dialect.kernel import Kernel
        from kernel_gen.dialect.nn import Nn

        ctx = Context()
        ctx.load_dialect(Builtin)
        ctx.load_dialect(Func)
        ctx.load_dialect(Nn)
        ctx.load_dialect(Kernel)
        return ctx

    monkeypatch.setattr(compare_module, "_build_default_context", _ctx_without_arith)

    ok = compare_module.mlir_gen_compare(
        fn=_dummy_kernel,
        runtime_args=None,
        config=None,
        mlir_file=str(expected_path),
    )

    assert ok is False


# TC-MLIR-GEN-COMPARE-007
# 创建者: 睡觉小分队
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 功能说明: 对齐 mlir_gen_compare 默认 Context 的 dialect 覆盖集合。
# 测试目的: 验证默认 Context 至少加载 builtin/func/arith 与 nn/kernel/symbol/dma/arch。
# 使用示例: pytest -q test/tools/test_mlir_gen_compare.py -k test_default_context_loads_required_dialects
# 对应功能实现文件路径: kernel_gen/tools/mlir_gen_compare.py
# 对应 spec 文件路径: spec/tools/mlir_gen_compare.md
# 对应测试文件路径: test/tools/test_mlir_gen_compare.py
def test_default_context_loads_required_dialects() -> None:
    try:
        ctx = compare_module._build_default_context()
    except Exception as exc:
        pytest.skip(f"default context unavailable: {exc}")
    required = ("builtin", "func", "arith", "nn", "kernel", "symbol", "dma", "arch")
    missing = [name for name in required if ctx.get_optional_dialect(name) is None]
    assert missing == []


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
    monkeypatch.setattr(
        compare_module, "_load_mlir_gen", lambda: (lambda *_a, **_k: object())
    )
    monkeypatch.setattr(compare_module, "_build_default_context", _build_min_context)

    ok = compare_module.mlir_gen_compare(
        fn=_dummy_kernel,
        runtime_args=None,
        config=None,
        mlir_file=str(expected_path),
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
    monkeypatch.setattr(compare_module, "_load_mlir_gen", lambda: _stub_mlir_gen)
    monkeypatch.setattr(compare_module, "_build_default_context", _build_min_context)

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
    monkeypatch.setattr(compare_module, "_load_mlir_gen", lambda: _stub_mlir_gen)
    monkeypatch.setattr(compare_module, "_build_default_context", _build_min_context)

    ok = compare_module.mlir_gen_compare_text(
        fn=_dummy_kernel,
        runtime_args=None,
        config=None,
        mlir_text="invalid mlir",
    )

    assert ok is False
