"""nn_lowering test memory type builders.


功能说明:
- 为 nn_lowering 测试构造符合公开 `NnMemoryType` 合同的 `SymbolExprAttr` 维度。
- 避免测试继续把旧 `IntAttr` / `StringAttr` 直接作为 memory shape/stride 传入。

使用示例:
- mem_type = memory_type([4, "N"], ["N", 1], f32, NnMemorySpaceAttr.from_name("global"))

关联文件:
- spec: spec/dialect/nn.md
- test: test/passes/lowering/nn_lowering/test_asset_cases.py
- 功能实现: kernel_gen/dialect/nn.py
"""

from __future__ import annotations

from collections.abc import Sequence

from xdsl.dialects.builtin import ArrayAttr
from xdsl.ir import Attribute

from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolExprAttr


def symbol_expr(value: int | str | SymbolExprAttr) -> SymbolExprAttr:
    """构造公开 `SymbolExprAttr`。


    功能说明:
    - 将测试输入中的 int/str 统一转为公开 memory 维度属性。

    使用示例:
    - dim = symbol_expr("N")

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/passes/lowering/nn_lowering/test_asset_cases.py
    - 功能实现: kernel_gen/dialect/symbol.py
    """

    if isinstance(value, SymbolExprAttr):
        return value
    return SymbolExprAttr.from_expr(str(value))


def symbol_array(values: Sequence[int | str | SymbolExprAttr]) -> ArrayAttr[Attribute]:
    """构造 `SymbolExprAttr` 数组。


    功能说明:
    - 用于 `NnMemoryType.shape` 和 `NnMemoryType.stride` 参数。

    使用示例:
    - dims = symbol_array([4, "N"])

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/passes/lowering/nn_lowering/test_asset_cases.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    return ArrayAttr([symbol_expr(value) for value in values])


def memory_type(
    shape: Sequence[int | str | SymbolExprAttr],
    stride: Sequence[int | str | SymbolExprAttr],
    element_type: Attribute,
    space: NnMemorySpaceAttr,
) -> NnMemoryType:
    """构造符合公开合同的 `NnMemoryType`。


    功能说明:
    - 只接受可转换为 `SymbolExprAttr` 的 shape/stride 维度输入。
    - 保持测试关注 lowering 行为，而不是重复书写 `#symbol.expr<...>` 样板。

    使用示例:
    - mem = memory_type([4, 8], [8, 1], element_type, space)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/passes/lowering/nn_lowering/test_asset_cases.py
    - 功能实现: kernel_gen/dialect/nn.py
    """

    return NnMemoryType(symbol_array(shape), symbol_array(stride), element_type, space)
