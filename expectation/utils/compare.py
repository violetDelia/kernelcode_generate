"""Expectation comparison helpers.

创建者: 朽木露琪亚
最后一次更改: 小李飞刀

功能说明:
- 为 expectation 脚本提供统一的断言辅助，减少重复样板代码并提升错误可读性：
  - `symbol.int`：静态整数值与动态符号表达式的断言。
  - `Memory`（operation 层）：shape/dtype/space/format/stride 的一致性断言。
  - IR `nn.memory` 类型：IR `NnMemoryType` 与 `Memory` 描述的一致性断言。
- stride 断言支持两种口径：
  - `mode="exact"`：严格比较 `SymbolDim` 的底层 sympy 表达式。
  - `mode="value"`：仅比较 `SymbolDim.get_value()` 文本。
- 兼容旧的 `expectation.utils.compare` 导入路径，但内部改为复用当前 `kernel_gen.dsl.mlir_gen.emit.core` 中的有效 memory type 转换实现，不再依赖已删除的旧 facade。

使用示例:
- assert_static_symbol_int(value.type, 3)
- assert_dynamic_symbol_int(value.type, SymbolDim("N") + SymbolDim("1"))
- assert_memory_metadata_equal(out, expected, stride_mode="value")
- assert_memory(value.type, memory)
- assert_single_return_memory(func_op, expected)
- assert_single_return_void(func_op)

关联文件:
- spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
- test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
- 功能实现: [expectation/utils/compare.py](expectation/utils/compare.py)
"""

from __future__ import annotations

from collections.abc import Sequence

from xdsl.dialects.builtin import i1
from xdsl.dialects.func import FuncOp, ReturnOp

from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.dsl.mlir_gen.emit.core import _memory_to_nn_type
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim


def assert_static_symbol_int(value_type: object, expected_value: int | float) -> None:
    """断言 `symbol.int` 类型表示静态整数值。"""

    assert isinstance(value_type, SymbolValueType)
    normalized = int(expected_value) if isinstance(expected_value, float) and expected_value.is_integer() else expected_value
    assert not value_type.is_symbol()
    assert value_type.get_value() == normalized
    assert value_type == SymbolValueType.from_expr(str(normalized))


def assert_dynamic_symbol_int(value_type: object, expected_expr: SymbolDim | str) -> None:
    """断言 `symbol.int` 类型表示动态符号表达式。"""

    assert isinstance(value_type, SymbolValueType)
    assert value_type.is_symbol()
    expected_text = str(expected_expr.get_value()) if isinstance(expected_expr, SymbolDim) else expected_expr
    assert value_type.get_value() == expected_text
    assert value_type == SymbolValueType.from_expr(expected_text)


def assert_memory(value_type: object, expected_memory: Memory) -> None:
    """断言 IR `nn.memory` 类型与 Memory 描述一致。

    创建者: 朽木露琪亚
    最后一次更改: 小李飞刀

    功能说明:
    - 校验 expectation 中的 `Memory` 描述与 lowering 后的 `NnMemoryType` 一致。
    - 兼容旧 helper 入口，但实际类型转换统一复用 `kernel_gen.dsl.mlir_gen.emit.core._memory_to_nn_type(...)`。

    参数说明:
    - `value_type`: IR 中的类型对象，应为 `NnMemoryType`。
    - `expected_memory`: 期望的 `Memory` 描述对象。

    使用示例:
    - `assert_memory(return_op.arguments[0].type, expected_memory)`

    关联文件:
    - spec: [spec/dsl/mlir_gen.md](spec/dsl/mlir_gen.md)
    - test: [test/dsl/test_emit_mlir.py](test/dsl/test_emit_mlir.py)
    - 功能实现: [expectation/utils/compare.py](expectation/utils/compare.py)
    """

    assert isinstance(expected_memory, Memory)
    assert isinstance(value_type, NnMemoryType)
    expected_type = _memory_to_nn_type(expected_memory)
    assert value_type == expected_type


def assert_single_return_memory(func_op: object, expected: Memory) -> ReturnOp:
    """断言 `FuncOp` 只有一个 `return`，且返回值类型与期望 `Memory` 一致。

    功能说明:
    - 统一 DSL expectation 中常见的“只关心返回类型合同”的断言样板。
    - 对外仅锁定 `ReturnOp` 的返回 `!nn.memory` 类型是否满足 `expected`。

    使用示例:
    - func_op = build_func_op(kernel, src)
    - assert_single_return_memory(func_op, expected)
    """

    assert isinstance(func_op, FuncOp), f"func_op must be FuncOp, got {type(func_op)!r}"
    returns = [op for op in func_op.body.block.ops if isinstance(op, ReturnOp)]
    assert len(returns) == 1, f"expected exactly 1 ReturnOp, got {len(returns)}"
    assert_memory(returns[0].arguments[0].type, expected)
    return returns[0]


def assert_single_return_symbol_int(func_op: object, expected: int | float | SymbolDim | str) -> ReturnOp:
    """断言 `FuncOp` 只有一个 `return`，且返回值类型为符合期望的 `symbol.int`。

    功能说明:
    - 用于 DSL `symbol.*` expectation 的统一断言：
      - `expected` 为 `int/float`（且可规整为 int）时，断言返回 `SymbolValueType` 为静态值。
      - `expected` 为 `SymbolDim/str` 时，断言返回 `SymbolValueType` 为动态符号表达式。

    使用示例:
    - func_op = build_func_op(add, 3, 4)
    - assert_single_return_symbol_int(func_op, 7)
    - func_op = build_func_op(add, SymbolDim("N"), 4)
    - assert_single_return_symbol_int(func_op, SymbolDim("N") + 4)
    """

    assert isinstance(func_op, FuncOp), f"func_op must be FuncOp, got {type(func_op)!r}"
    returns = [op for op in func_op.body.block.ops if isinstance(op, ReturnOp)]
    assert len(returns) == 1, f"expected exactly 1 ReturnOp, got {len(returns)}"

    value_type = returns[0].arguments[0].type
    if isinstance(expected, SymbolDim):
        assert_dynamic_symbol_int(value_type, expected)
    elif isinstance(expected, str):
        assert_dynamic_symbol_int(value_type, expected)
    else:
        assert_static_symbol_int(value_type, expected)
    return returns[0]


def assert_single_return_i1(func_op: object) -> ReturnOp:
    """断言 `FuncOp` 只有一个 `return`，且返回值类型为 `i1`。"""

    assert isinstance(func_op, FuncOp), f"func_op must be FuncOp, got {type(func_op)!r}"
    returns = [op for op in func_op.body.block.ops if isinstance(op, ReturnOp)]
    assert len(returns) == 1, f"expected exactly 1 ReturnOp, got {len(returns)}"
    assert returns[0].arguments[0].type == i1
    return returns[0]


def assert_single_return_void(func_op: object) -> ReturnOp:
    """断言 `FuncOp` 只有一个 `return`，且该 return 不携带任何返回值。

    功能说明:
    - 用于 DSL expectation 中常见的“store/deslice/free 这类 void 函数体”的统一断言样板。

    使用示例:
    - func_op = build_func_op(store_kernel, tile, target)
    - assert_single_return_void(func_op)
    """

    assert isinstance(func_op, FuncOp), f"func_op must be FuncOp, got {type(func_op)!r}"
    returns = [op for op in func_op.body.block.ops if isinstance(op, ReturnOp)]
    assert len(returns) == 1, f"expected exactly 1 ReturnOp, got {len(returns)}"
    assert len(returns[0].arguments) == 0, f"expected void return, got {len(returns[0].arguments)} values"
    return returns[0]


def symbol_value(value: object) -> object:
    """将 `SymbolDim` 规整为可比较的对外值。

    功能说明:
    - 对 `SymbolDim` 返回 `get_value()`（可能是 int/float/str）。
    - 其他类型原样返回。

    使用示例:
    - symbol_value(SymbolDim("N") * 4)
    - symbol_value(16)
    """

    if isinstance(value, SymbolDim):
        return value.get_value()
    return value


def symbol_debug(value: object) -> str:
    """将 `SymbolDim` 规整为便于诊断的调试字符串。

    功能说明:
    - 对 `SymbolDim` 输出 `sympy` 表达式类型与文本，便于区分：
      - `Mul(6*X)` vs `Symbol(6*X)` 这类“看起来一样但语义不同”的情况。
    - 其他类型输出 `type(value).__name__(value)`。

    使用示例:
    - symbol_debug(SymbolDim("N") * 4)
    """

    if isinstance(value, SymbolDim):
        sym = value.get_symbol()
        return f"{type(sym).__name__}({sym})"
    return f"{type(value).__name__}({value})"


def symbol_list_values(values: Sequence[object]) -> list[object]:
    """将序列中的 `SymbolDim` 转换为 `get_value()`，用于 value 口径断言。"""

    return [symbol_value(item) for item in values]


def symbol_list_debug(values: Sequence[object]) -> list[str]:
    """将序列转换为 debug 文本列表，用于失败时输出诊断信息。"""

    return [symbol_debug(item) for item in values]


def assert_symbolic_list_equal(
    actual: Sequence[object],
    expected: Sequence[object],
    *,
    mode: str = "exact",
    context: str = "",
) -> None:
    """断言两个符号序列在指定口径下等价。

    参数:
    - actual: 实际序列（如 Memory.get_stride())。
    - expected: 期望序列。
    - mode:
      - "exact": 严格比较 `SymbolDim` 的底层 sympy 表达式（list equality）。
      - "value": 仅比较 `SymbolDim.get_value()` 序列化值。
    - context: 失败时附带的上下文信息（建议包含 op 名称或字段名）。

    使用示例:
    - assert_symbolic_list_equal(out.get_stride(), expected.get_stride(), mode="value", context="softmax stride")
    """

    if mode not in {"exact", "value"}:
        raise ValueError(f"mode must be 'exact' or 'value', got {mode!r}")

    actual_list = list(actual)
    expected_list = list(expected)
    if mode == "exact":
        if actual_list != expected_list:
            raise AssertionError(
                f"{context} expected={expected_list} actual={actual_list}; "
                f"expected_sym={symbol_list_debug(expected_list)} actual_sym={symbol_list_debug(actual_list)}"
            )
        return

    actual_values = symbol_list_values(actual_list)
    expected_values = symbol_list_values(expected_list)
    if actual_values != expected_values:
        raise AssertionError(
            f"{context} expected={expected_values} actual={actual_values}; "
            f"expected_sym={symbol_list_debug(expected_list)} actual_sym={symbol_list_debug(actual_list)}"
        )


def assert_memory_metadata_equal(
    actual: Memory,
    expected: Memory,
    *,
    stride_mode: str = "exact",
    context: str = "",
    check_shape: bool = True,
    check_dtype: bool = True,
    check_space: bool = True,
    check_format: bool = True,
    check_stride: bool = True,
) -> None:
    """断言两个 `Memory` 的公开元信息一致。

    功能说明:
    - 可按需比较 shape/dtype/space/format/stride，并按 `stride_mode` 比较 stride。
    - 默认 `stride_mode="exact"` 可用于锁定 stride 符号表达式结构变化。

    使用示例:
    - expected = Memory([m, n], NumericType.Float32, space=MemorySpace.GM)
    - assert_memory_metadata_equal(out, expected, stride_mode="value", context="nn.add result")
    - assert_memory_metadata_equal(out, expected, check_space=False, context="nn.add layout fallback")
    """

    assert isinstance(actual, Memory), f"{context} actual must be Memory, got {type(actual)!r}"
    assert isinstance(expected, Memory), f"{context} expected must be Memory, got {type(expected)!r}"

    if check_shape:
        assert actual.get_shape() == expected.get_shape(), (
            f"{context} shape mismatch: expected={expected.get_shape()} actual={actual.get_shape()}"
        )
    if check_dtype:
        assert actual.get_type() is expected.get_type(), (
            f"{context} dtype mismatch: expected={expected.get_type()} actual={actual.get_type()}"
        )
    if check_space:
        assert actual.get_space() is expected.get_space(), (
            f"{context} space mismatch: expected={expected.get_space()} actual={actual.get_space()}"
        )
    if check_format:
        assert actual.get_format() is expected.get_format(), (
            f"{context} format mismatch: expected={expected.get_format()} actual={actual.get_format()}"
        )
    if check_stride:
        assert_symbolic_list_equal(
            actual.get_stride(),
            expected.get_stride(),
            mode=stride_mode,
            context=f"{context} stride",
        )


__all__ = [
    "assert_dynamic_symbol_int",
    "assert_memory",
    "assert_memory_metadata_equal",
    "assert_single_return_memory",
    "assert_single_return_i1",
    "assert_single_return_void",
    "assert_single_return_symbol_int",
    "assert_static_symbol_int",
    "assert_symbolic_list_equal",
    "symbol_debug",
    "symbol_list_debug",
    "symbol_list_values",
    "symbol_value",
]
