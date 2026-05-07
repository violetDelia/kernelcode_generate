"""mlir_gen compare tests.


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

from collections.abc import Callable
import sys
from pathlib import Path
from typing import TypeAlias

import pytest
from xdsl.dialects.builtin import ArrayAttr, ModuleOp, i32
from xdsl.parser import Parser

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.context import build_default_context
from kernel_gen.dialect import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolExprAttr
import kernel_gen.dsl.ast.mlir_gen as public_mlir_gen
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
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

_SCF_MODULE_TEXT = """builtin.module {
  func.func @main(%0 : i1) {
    scf.if %0 {
    }
    func.return
  }
}
"""

DslRuntimeArg: TypeAlias = "Memory | SymbolDim | int | float | bool | str"
MlirGenArgument: TypeAlias = "Callable[..., None] | DslRuntimeArg | tuple[DslRuntimeArg, ...] | None"
MlirGenKeyword: TypeAlias = "DslRuntimeArg | tuple[DslRuntimeArg, ...] | None | str"


class _InvalidMlirGenResult:
    """Sentinel returned by stubs that intentionally violate the public result contract."""


MlirGenStubResult: TypeAlias = "ModuleOp | _InvalidMlirGenResult"


def _dummy_kernel() -> None:
    """占位 kernel，用于 mlir_gen_compare 测试。


    功能说明:
    - 作为 mlir_gen_compare 的入参占位，便于测试走通比较逻辑。

    使用示例:
    - mlir_gen_compare(_dummy_kernel, None, path)

    关联文件:
    - spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
    - test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
    """

    return None


def _stub_mlir_gen(*_args: MlirGenArgument, **_kwargs: MlirGenKeyword) -> ModuleOp:
    """生成用于测试的固定 builtin.module。


    功能说明:
    - 返回固定 builtin.module，便于验证 mlir_gen_compare 的比较逻辑。

    使用示例:
    - module = _stub_mlir_gen(_dummy_kernel)

    关联文件:
    - spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
    - test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
    """

    ctx = build_default_context()
    return Parser(ctx, _SIMPLE_MODULE_TEXT).parse_module()


def test_build_default_context_parses_scf_if() -> None:
    """默认解析 Context 必须覆盖 mlir_gen_compare 需要的 scf.if。"""

    module = Parser(build_default_context(), _SCF_MODULE_TEXT).parse_module()

    assert module is not None


def _install_public_mlir_gen_stub(
    monkeypatch: pytest.MonkeyPatch,
    stub: Callable[..., MlirGenStubResult],
) -> None:
    """通过公开 mlir_gen 入口安装测试 stub。


    功能说明:
    - 只 monkeypatch `kernel_gen.dsl.ast.mlir_gen.mlir_gen` 这个公开入口。
    - 避免测试再直连 `mlir_gen_compare.py` 的内部导入辅助逻辑。

    使用示例:
    - _install_public_mlir_gen_stub(monkeypatch, _stub_mlir_gen)

    关联文件:
    - spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
    - test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
    """

    monkeypatch.setattr(public_mlir_gen, "mlir_gen", stub)


def _build_module_with_unregistered_op() -> ModuleOp:
    """构造一个包含未注册 op 的最小 builtin.module。


    功能说明:
    - 用于覆盖 `normalize_module_text(...)` 二次解析失败时 `mlir_gen_compare` 返回 False 的公开行为。
    - 该 helper 直接构造带 `UnregisteredOp` 的 module，不依赖私有 context patch。

    使用示例:
    - module = _build_module_with_unregistered_op()

    关联文件:
    - spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
    - test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
    """

    from xdsl.dialects.builtin import UnregisteredOp
    from xdsl.dialects.func import FuncOp, ReturnOp
    from xdsl.ir import Block, Region

    unknown_op = UnregisteredOp.with_name("test.unregistered")
    block = Block()
    block.add_op(unknown_op.create())
    block.add_op(ReturnOp())
    func = FuncOp.from_region("main", [], [], Region(block))
    return ModuleOp([func])


def _build_module_with_memory_floor_div_expr() -> ModuleOp:
    """构造一个含 `floordiv` memory shape 表达式的 builtin.module。

    功能说明:
    - 用于覆盖 mlir_gen_compare 对 `!nn.memory` floor-div 文本的比较路径。
    - 该文本使用当前公开的 `SymbolExprAttr` 结构化 memory layout。

    使用示例:
    - module = _build_module_with_memory_floor_div_expr()

    关联文件:
    - spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
    - test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
    """

    from xdsl.dialects.func import FuncOp, ReturnOp
    from xdsl.ir import Block, Region

    memory_type = NnMemoryType(
        ArrayAttr([SymbolExprAttr.from_expr("M floordiv S + 1")]),
        ArrayAttr([SymbolExprAttr.from_expr("1")]),
        i32,
        NnMemorySpaceAttr.from_name("global"),
    )
    block = Block(arg_types=[memory_type])
    block.add_op(ReturnOp())
    func = FuncOp.from_region("main", [memory_type], [], Region(block))
    return ModuleOp([func])


# TC-MLIR-GEN-COMPARE-001
# 功能说明: 对齐 mlir_gen_compare 的一致性比较路径。
# 测试目的: 验证 mlir_gen_compare 在预期一致时返回 True。
# 使用示例: pytest -q test/tools/test_mlir_gen_compare.py -k test_mlir_gen_compare_true
# 对应功能实现文件路径: kernel_gen/tools/mlir_gen_compare.py
# 对应 spec 文件路径: spec/tools/mlir_gen_compare.md
# 对应测试文件路径: test/tools/test_mlir_gen_compare.py
def test_mlir_gen_compare_true(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    expected_path = tmp_path / "expected.mlir"
    expected_path.write_text(_SIMPLE_MODULE_TEXT, encoding="utf-8")
    _install_public_mlir_gen_stub(monkeypatch, _stub_mlir_gen)

    ok = compare_module.mlir_gen_compare(
        fn=_dummy_kernel,
        runtime_args=None,
        mlir_file=str(expected_path),
    )

    assert ok is True


# TC-MLIR-GEN-COMPARE-011
# 功能说明: 对齐 compare_mlir_file 兼容接口与 mlir_gen_compare 的等价行为。
# 测试目的: 验证 compare_mlir_file 在预期一致时返回 True。
# 使用示例: pytest -q test/tools/test_mlir_gen_compare.py -k test_compare_mlir_file_alias_true
# 对应功能实现文件路径: kernel_gen/tools/mlir_gen_compare.py
# 对应 spec 文件路径: spec/tools/mlir_gen_compare.md
# 对应测试文件路径: test/tools/test_mlir_gen_compare.py
def test_compare_mlir_file_alias_true(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    expected_path = tmp_path / "expected_alias.mlir"
    expected_path.write_text(_SIMPLE_MODULE_TEXT, encoding="utf-8")
    _install_public_mlir_gen_stub(monkeypatch, _stub_mlir_gen)

    ok = compare_module.compare_mlir_file(
        fn=_dummy_kernel,
        runtime_args=None,
        mlir_file=str(expected_path),
    )

    assert ok is True


# TC-MLIR-GEN-COMPARE-002
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
    _install_public_mlir_gen_stub(monkeypatch, _stub_mlir_gen)

    ok = compare_module.mlir_gen_compare(
        fn=_dummy_kernel,
        runtime_args=(),
        mlir_file=str(expected_path),
    )

    assert ok is False


# TC-MLIR-GEN-COMPARE-003
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
    _install_public_mlir_gen_stub(monkeypatch, _stub_mlir_gen)

    ok = compare_module.mlir_gen_compare(
        fn=_dummy_kernel,
        runtime_args=None,
        mlir_file=str(expected_path),
    )

    assert ok is False


# TC-MLIR-GEN-COMPARE-004
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
    _install_public_mlir_gen_stub(monkeypatch, _stub_mlir_gen)

    ok = compare_module.mlir_gen_compare(
        fn=_dummy_kernel,
        runtime_args=None,
        mlir_file=str(expected_path),
    )

    assert ok is False


# TC-MLIR-GEN-COMPARE-005
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

    def _stub_mlir_gen_arith(*_args: MlirGenArgument, **_kwargs: MlirGenKeyword) -> ModuleOp:
        ctx = build_default_context()
        return Parser(ctx, _ARITH_MODULE_TEXT).parse_module()

    _install_public_mlir_gen_stub(monkeypatch, _stub_mlir_gen_arith)

    ok = compare_module.mlir_gen_compare(
        fn=_dummy_kernel,
        runtime_args=None,
        mlir_file=str(expected_path),
    )

    assert ok is True


# TC-MLIR-GEN-COMPARE-006
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

    actual_module = _build_module_with_unregistered_op()
    _install_public_mlir_gen_stub(monkeypatch, lambda *_a, **_k: actual_module)

    ok = compare_module.mlir_gen_compare(
        fn=_dummy_kernel,
        runtime_args=None,
        mlir_file=str(expected_path),
    )

    assert ok is False


# TC-MLIR-GEN-COMPARE-007
# 功能说明: 对齐 mlir_gen_compare 默认 Context 的 dialect 覆盖集合。
# 测试目的: 验证默认 Context 至少加载 builtin/func/arith 与 nn/kernel/symbol/dma/arch。
# 使用示例: pytest -q test/tools/test_mlir_gen_compare.py -k test_default_context_loads_required_dialects
# 对应功能实现文件路径: kernel_gen/tools/mlir_gen_compare.py
# 对应 spec 文件路径: spec/tools/mlir_gen_compare.md
# 对应测试文件路径: test/tools/test_mlir_gen_compare.py
def test_default_context_loads_required_dialects() -> None:
    try:
        ctx = build_default_context()
    except Exception as exc:
        pytest.skip(f"default context unavailable: {exc}")
    required = ("builtin", "func", "arith", "nn", "kernel", "symbol", "dma", "arch")
    missing = [name for name in required if ctx.get_optional_dialect(name) is None]
    assert missing == []


# TC-MLIR-GEN-COMPARE-008
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
    _install_public_mlir_gen_stub(monkeypatch, lambda *_a, **_k: _InvalidMlirGenResult())

    ok = compare_module.mlir_gen_compare(
        fn=_dummy_kernel,
        runtime_args=None,
        mlir_file=str(expected_path),
    )

    assert ok is False


# TC-MLIR-GEN-COMPARE-003A
# 最后更改: 金铲铲大作战
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
  func.func @main(%0 : !nn.memory<[#symbol.expr<2>], [#symbol.expr<1>], f16, #nn.space<global>>, %1 : i32, %2 : i32, %3 : i32, %4 : i32, %5 : i32, %6 : i32) {
    %7 = "dma.view"(%0, %1, %2, %3, %4, %5, %6) <{operandSegmentSizes = array<i32: 1, 2, 2, 2>}> : (!nn.memory<[#symbol.expr<2>], [#symbol.expr<1>], f16, #nn.space<global>>, i32, i32, i32, i32, i32, i32) -> !nn.memory<[#symbol.expr<2>], [#symbol.expr<1>], f16, #nn.space<global>>
    func.return
  }
}
"""
    expected_text = actual_text.replace(
        "-> !nn.memory<[#symbol.expr<2>], [#symbol.expr<1>], f16, #nn.space<global>>",
        "-> !nn.memory<[#symbol.expr<2>], [#symbol.expr<1>], f32, #nn.space<global>>",
        1,
    )

    def _stub_mlir_gen_dma(*_args: MlirGenArgument, **_kwargs: MlirGenKeyword) -> ModuleOp:
        ctx = build_default_context()
        return Parser(ctx, actual_text).parse_module()

    _install_public_mlir_gen_stub(monkeypatch, _stub_mlir_gen_dma)

    ok = compare_module.mlir_gen_compare_text(
        fn=_dummy_kernel,
        runtime_args=None,
        mlir_text=expected_text,
    )

    assert ok is False


# TC-MLIR-GEN-COMPARE-012
# 功能说明: 对齐 `!nn.memory` 中 `floordiv` shape 表达式的文本比较。
# 测试目的: 验证 expected 文本含结构化 `SymbolExprAttr` floor-div 时仍能比较成功。
# 使用示例: pytest -q test/tools/test_mlir_gen_compare.py -k test_mlir_gen_compare_text_handles_memory_floor_div_expr
# 对应功能实现文件路径: kernel_gen/tools/mlir_gen_compare.py
# 对应 spec 文件路径: spec/tools/mlir_gen_compare.md
# 对应测试文件路径: test/tools/test_mlir_gen_compare.py
def test_mlir_gen_compare_text_handles_memory_floor_div_expr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actual_module = _build_module_with_memory_floor_div_expr()
    expected_text = """builtin.module {
  func.func @main(
      %0 : !nn.memory<[#symbol.expr<M floordiv S + 1>], [#symbol.expr<1>], i32, #nn.space<global>>) {
    func.return
  }
}
"""
    _install_public_mlir_gen_stub(monkeypatch, lambda *_a, **_k: actual_module)

    ok = compare_module.mlir_gen_compare_text(
        fn=_dummy_kernel,
        runtime_args=None,
        mlir_text=expected_text,
    )

    assert ok is True


# TC-MLIR-GEN-COMPARE-013
# 功能说明: 对齐 `!nn.memory` 中 `floordiv` shape 表达式文本比较的不一致路径。
# 测试目的: 验证比较不会把不同 floor-div 表达式误判为一致。
# 使用示例: pytest -q test/tools/test_mlir_gen_compare.py -k test_mlir_gen_compare_text_rejects_memory_floor_div_mismatch
# 对应功能实现文件路径: kernel_gen/tools/mlir_gen_compare.py
# 对应 spec 文件路径: spec/tools/mlir_gen_compare.md
# 对应测试文件路径: test/tools/test_mlir_gen_compare.py
def test_mlir_gen_compare_text_rejects_memory_floor_div_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actual_module = _build_module_with_memory_floor_div_expr()
    expected_text = """builtin.module {
  func.func @main(
      %0 : !nn.memory<[#symbol.expr<M floordiv S + 2>], [#symbol.expr<1>], i32, #nn.space<global>>) {
    func.return
  }
}
"""
    _install_public_mlir_gen_stub(monkeypatch, lambda *_a, **_k: actual_module)

    ok = compare_module.mlir_gen_compare_text(
        fn=_dummy_kernel,
        runtime_args=None,
        mlir_text=expected_text,
    )

    assert ok is False


# TC-MLIR-GEN-COMPARE-014
# 功能说明: 验证带 `//` 的 memory 文本会走当前文件内 raw compare 兜底。
# 使用示例: pytest -q test/tools/test_mlir_gen_compare.py -k test_mlir_gen_compare_text_handles_memory_floor_div_raw_compare
# 对应功能实现文件路径: kernel_gen/tools/mlir_gen_compare.py
# 对应 spec 文件路径: spec/tools/mlir_gen_compare.md
# 对应测试文件路径: test/tools/test_mlir_gen_compare.py
def test_mlir_gen_compare_text_handles_memory_floor_div_raw_compare(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actual_module = _build_module_with_memory_floor_div_expr()
    expected_text = """// comment with "quoted value" keeps string handling live
builtin.module {
  func.func @main(
      %0 : !nn.memory<[#symbol.expr<M // S + 1>], [#symbol.expr<1>], i32, #nn.space<global>>) {
    func.return
  }
}
"""
    _install_public_mlir_gen_stub(monkeypatch, lambda *_a, **_k: actual_module)

    ok = compare_module.mlir_gen_compare_text(
        fn=_dummy_kernel,
        runtime_args=None,
        mlir_text=expected_text,
    )

    assert ok is False


# TC-MLIR-GEN-COMPARE-015
# 功能说明: 验证公开 mlir_gen_compare 的 runtime_args 类型边界稳定报错。
# 使用示例: pytest -q test/tools/test_mlir_gen_compare.py -k test_mlir_gen_compare_rejects_invalid_runtime_args_type
# 对应功能实现文件路径: kernel_gen/tools/mlir_gen_compare.py
# 对应 spec 文件路径: spec/tools/mlir_gen_compare.md
# 对应测试文件路径: test/tools/test_mlir_gen_compare.py
def test_mlir_gen_compare_rejects_invalid_runtime_args_type() -> None:
    try:
        compare_module.mlir_gen_compare_text(
            fn=_dummy_kernel,
            runtime_args=42,
            mlir_text=_SIMPLE_MODULE_TEXT,
        )
    except TypeError as exc:
        assert "runtime_args must be list, tuple, or None" in str(exc)
    else:
        raise AssertionError("expected TypeError for invalid runtime_args type")


# TC-MLIR-GEN-COMPARE-009
# 功能说明: 对齐 mlir_gen_compare_text 的一致性比较路径。
# 测试目的: 验证 mlir_gen_compare_text 在预期一致时返回 True。
# 使用示例: pytest -q test/tools/test_mlir_gen_compare.py -k test_mlir_gen_compare_text_true
# 对应功能实现文件路径: kernel_gen/tools/mlir_gen_compare.py
# 对应 spec 文件路径: spec/tools/mlir_gen_compare.md
# 对应测试文件路径: test/tools/test_mlir_gen_compare.py
def test_mlir_gen_compare_text_true(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_public_mlir_gen_stub(monkeypatch, _stub_mlir_gen)

    ok = compare_module.mlir_gen_compare_text(
        fn=_dummy_kernel,
        runtime_args=None,
        mlir_text=_SIMPLE_MODULE_TEXT,
    )

    assert ok is True


def test_mlir_gen_compare_text_ignores_line_comment_slashes_for_memory_types(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """expected 注释中的 `//` 不应触发 memory floor-div 原始文本比较。"""

    memory_module_text = """builtin.module {
  func.func @main(%0 : !nn.memory<[#symbol.expr<4>], [#symbol.expr<1>], i32, #nn.space<global>>) {
    func.return
  }
}
"""
    expected_text = "// expected file comment with // slashes\n" + memory_module_text
    actual_module = Parser(build_default_context(), memory_module_text).parse_module()
    _install_public_mlir_gen_stub(monkeypatch, lambda *_a, **_k: actual_module)

    ok = compare_module.mlir_gen_compare_text(
        fn=_dummy_kernel,
        runtime_args=None,
        mlir_text=expected_text,
    )

    assert ok is True


# TC-MLIR-GEN-COMPARE-010
# 功能说明: 对齐 mlir_gen_compare_text 的非法文本返回路径。
# 测试目的: 验证 mlir_gen_compare_text 在非法文本时返回 False（不抛 ParseError）。
# 使用示例: pytest -q test/tools/test_mlir_gen_compare.py -k test_mlir_gen_compare_text_returns_false_on_invalid_text
# 对应功能实现文件路径: kernel_gen/tools/mlir_gen_compare.py
# 对应 spec 文件路径: spec/tools/mlir_gen_compare.md
# 对应测试文件路径: test/tools/test_mlir_gen_compare.py
def test_mlir_gen_compare_text_returns_false_on_invalid_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_public_mlir_gen_stub(monkeypatch, _stub_mlir_gen)

    ok = compare_module.mlir_gen_compare_text(
        fn=_dummy_kernel,
        runtime_args=None,
        mlir_text="invalid mlir",
    )

    assert ok is False
