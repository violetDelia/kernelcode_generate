"""Expectation random/sample text helpers.

创建者: Codex
最后一次更改: Codex

功能说明:
- 提供 `expectation` 公共复用的随机维度、随机符号名、`MemorySpace` 映射、`!nn.memory` 文本构造与文本替换辅助。
- 将原先挂在 `expectation/dsl/mlir_gen/_random_utils.py` 下的通用逻辑上移到 `expectation/utils`，便于 DSL expectation 之外的目录直接复用。
- 保持现有 DSL/operation expectation 所需 helper 行为不变，同时为后续共享工具提供统一入口。

使用示例:
- `from expectation.utils.random_utils import random_static_dims, random_symbol_names`
- `dims = random_static_dims(2, min_value=2, max_value=16)`
- `symbols = random_symbol_names(2)`
- `memory_ir = nn_memory_type_ir((4, "N"), "f32", MemorySpace.GM)`
- `stride = contiguous_stride_tokens((4, "N"))`

关联文件:
- spec: [`spec/tools/expectation_random_utils.md`](../../spec/tools/expectation_random_utils.md)
- test: [`test/tools/test_expectation_random_utils.py`](../../test/tools/test_expectation_random_utils.py)
- 功能实现: [`expectation/utils/random_utils.py`](random_utils.py)
- 功能实现: [`expectation/dsl/mlir_gen/_random_utils.py`](../dsl/mlir_gen/_random_utils.py)
"""

from __future__ import annotations

import linecache
import re
from collections.abc import Sequence

from expectation.utils.sample_values import (
    get_random_alpha_strings,
    get_random_memory_space,
    get_random_memory_spaces,
    get_random_non_zero_ints,
    get_random_onchip_memory_space,
)
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.symbol_shape import SymbolShape
from kernel_gen.symbol_variable.type import NumericType

DimToken = int | str

_SPACE_TO_IR_NAME = {
    MemorySpace.GM: "global",
    MemorySpace.SM: "shared",
    MemorySpace.LM: "local",
    MemorySpace.TSM: "tsm",
    MemorySpace.TLM1: "tlm1",
    MemorySpace.TLM2: "tlm2",
    MemorySpace.TLM3: "tlm3",
}

_SPACE_TO_SIZE_SYMBOL = {
    MemorySpace.SM: "SM_SIZE",
    MemorySpace.LM: "LM_SIZE",
    MemorySpace.TSM: "TSM_SIZE",
    MemorySpace.TLM1: "TLM1_SIZE",
    MemorySpace.TLM2: "TLM2_SIZE",
    MemorySpace.TLM3: "TLM3_SIZE",
}

_DTYPE_TO_IR_NAME = {
    NumericType.Int8: "i8",
    NumericType.Int16: "i16",
    NumericType.Int32: "i32",
    NumericType.Int64: "i64",
    NumericType.Uint8: "ui8",
    NumericType.Uint16: "ui16",
    NumericType.Uint32: "ui32",
    NumericType.Uint64: "ui64",
    NumericType.Float16: "f16",
    NumericType.BFloat16: "bf16",
    NumericType.Float32: "f32",
    NumericType.Float64: "f64",
    NumericType.Bool: "i1",
}


def random_static_dims(
    count: int,
    *,
    min_value: int = 2,
    max_value: int = 16,
    unique: bool = False,
) -> tuple[int, ...]:
    """返回指定数量的随机正静态维度。

    创建者: Codex
    最后一次更改: Codex

    功能说明:
    - 基于 `expectation.utils.sample_values.get_random_non_zero_ints(...)` 生成静态正整数维度。
    - 适用于 expectation 中的随机 shape / tile / stride 长度样本。

    使用示例:
    - `m, n = random_static_dims(2)`
    - `dims = random_static_dims(3, min_value=1, max_value=8, unique=True)`

    关联文件:
    - spec: [`spec/tools/expectation_random_utils.md`](../../spec/tools/expectation_random_utils.md)
    - test: [`test/tools/test_expectation_random_utils.py`](../../test/tools/test_expectation_random_utils.py)
    - 功能实现: [`expectation/utils/random_utils.py`](random_utils.py)
    """

    return get_random_non_zero_ints(
        count,
        min_value=min_value,
        max_value=max_value,
        unique=unique,
    )


def random_symbol_names(
    count: int,
    *,
    max_length: int = 6,
) -> tuple[str, ...]:
    """返回指定数量、互不重复的随机大写符号名。

    创建者: Codex
    最后一次更改: Codex

    功能说明:
    - 统一生成大写、去重的符号名字面量，适配 expectation 中的符号维度和符号参数。

    使用示例:
    - `sym_m, sym_n = random_symbol_names(2)`

    关联文件:
    - spec: [`spec/tools/expectation_random_utils.md`](../../spec/tools/expectation_random_utils.md)
    - test: [`test/tools/test_expectation_random_utils.py`](../../test/tools/test_expectation_random_utils.py)
    - 功能实现: [`expectation/utils/random_utils.py`](random_utils.py)
    """

    return get_random_alpha_strings(
        count,
        max_length=max_length,
        unique=True,
        uppercase=True,
    )


def random_memory_space(
    candidates: Sequence[MemorySpace] | None = None,
) -> MemorySpace:
    """从候选集合中返回一个随机 `MemorySpace`。

    创建者: Codex
    最后一次更改: Codex

    功能说明:
    - 对 `expectation.utils.sample_values.get_random_memory_space(...)` 的轻量封装。

    使用示例:
    - `space = random_memory_space()`
    - `space = random_memory_space((MemorySpace.GM, MemorySpace.SM))`

    关联文件:
    - spec: [`spec/tools/expectation_random_utils.md`](../../spec/tools/expectation_random_utils.md)
    - test: [`test/tools/test_expectation_random_utils.py`](../../test/tools/test_expectation_random_utils.py)
    - 功能实现: [`expectation/utils/random_utils.py`](random_utils.py)
    """

    return get_random_memory_space(candidates)


def random_memory_spaces(
    count: int,
    *,
    candidates: Sequence[MemorySpace] | None = None,
    unique: bool = False,
) -> tuple[MemorySpace, ...]:
    """从候选集合中返回指定数量的随机 `MemorySpace`。

    创建者: Codex
    最后一次更改: Codex

    功能说明:
    - 批量生成随机 `MemorySpace`，适合需要多组空间组合的 expectation。

    使用示例:
    - `spaces = random_memory_spaces(2, unique=True)`

    关联文件:
    - spec: [`spec/tools/expectation_random_utils.md`](../../spec/tools/expectation_random_utils.md)
    - test: [`test/tools/test_expectation_random_utils.py`](../../test/tools/test_expectation_random_utils.py)
    - 功能实现: [`expectation/utils/random_utils.py`](random_utils.py)
    """

    return get_random_memory_spaces(count, candidates, unique=unique)


def random_onchip_space() -> MemorySpace:
    """返回一个随机片上 `MemorySpace`。

    创建者: Codex
    最后一次更改: Codex

    功能说明:
    - 仅从片上空间集合中采样，用于动态 memory 容量、片上 buffer 等 expectation。

    使用示例:
    - `space = random_onchip_space()`

    关联文件:
    - spec: [`spec/tools/expectation_random_utils.md`](../../spec/tools/expectation_random_utils.md)
    - test: [`test/tools/test_expectation_random_utils.py`](../../test/tools/test_expectation_random_utils.py)
    - 功能实现: [`expectation/utils/random_utils.py`](random_utils.py)
    """

    return get_random_onchip_memory_space()


def memory_space_ir_name(space: MemorySpace) -> str:
    """返回 `MemorySpace` 对应的 `#nn.space<...>` 文本名。"""

    return _SPACE_TO_IR_NAME[space]


def format_dim_token(token: DimToken) -> str:
    """返回单个维度 token 的 IR 文本。"""

    return str(token)


def symbol_dim_token(value: SymbolDim | DimToken) -> DimToken:
    """将 `SymbolDim/int/str` 统一转为 expectation 可用的维度 token。"""

    if isinstance(value, SymbolDim):
        normalized = value.get_value()
        if isinstance(normalized, int | str):
            return normalized
        return str(normalized)
    return value


def shape_tokens(shape: Sequence[SymbolDim | DimToken] | SymbolShape) -> tuple[DimToken, ...]:
    """将 `SymbolShape` 或维度序列规范化为 token 元组。"""

    if isinstance(shape, SymbolShape):
        return tuple(symbol_dim_token(value) for value in shape.get_values())
    return tuple(symbol_dim_token(value) for value in shape)


def format_dim_list(tokens: Sequence[DimToken]) -> str:
    """返回 `[d0, d1, ...]` 维度列表的内部文本。"""

    return ", ".join(format_dim_token(token) for token in tokens)


def symbol_int_type_ir(token: DimToken) -> str:
    """返回 `!symbol.int<"...">` 文本。"""

    return f'!symbol.int<"{format_dim_token(token)}">'


def nn_memory_type_ir(
    dims: Sequence[DimToken],
    dtype_ir: str,
    space: MemorySpace,
    *,
    strides: Sequence[DimToken] | None = None,
) -> str:
    """返回 `!nn.memory<...>` 文本。"""

    stride_tokens = tuple(strides) if strides is not None else contiguous_stride_tokens(dims)
    return (
        f"!nn.memory<[{format_dim_list(dims)}], "
        f"[{format_dim_list(stride_tokens)}], "
        f"{dtype_ir}, #nn.space<{memory_space_ir_name(space)}>>"
    )


def numeric_type_ir(dtype: NumericType) -> str:
    """返回 `NumericType` 对应的 IR element type 文本。"""

    return _DTYPE_TO_IR_NAME[dtype]


def memory_type_from_memory(memory: Memory) -> str:
    """根据 `Memory` 对象返回对应的 `!nn.memory<...>` 文本。"""

    return nn_memory_type_ir(
        shape_tokens(memory.shape),
        numeric_type_ir(memory.dtype),
        memory.space,
        strides=shape_tokens(memory.stride),
    )


def contiguous_memory_type_from_memory(memory: Memory) -> str:
    """根据 `Memory` 的 shape/dtype/space 生成连续布局 `!nn.memory<...>` 文本。"""

    dims = shape_tokens(memory.shape)
    return nn_memory_type_ir(
        dims,
        numeric_type_ir(memory.dtype),
        memory.space,
    )


def dynamic_memory_size_symbol(space: MemorySpace) -> str:
    """返回 `arch.get_dynamic_memory` 对应的静态容量符号名。"""

    return _SPACE_TO_SIZE_SYMBOL[space]


def contiguous_stride_tokens(dims: Sequence[DimToken]) -> tuple[str, ...]:
    """按行主序返回 shape 对应的 stride token 文本。"""

    if not dims:
        raise ValueError("dims must not be empty")

    result: list[str] = []
    for index in range(len(dims)):
        suffix = dims[index + 1 :]
        if not suffix:
            result.append("1")
            continue
        constant = 1
        symbols: list[str] = []
        for value in suffix:
            if isinstance(value, int):
                constant *= value
            else:
                symbol_text = str(value)
                if re.fullmatch(r"-?[A-Za-z_][A-Za-z0-9_]*|-?[0-9]+", symbol_text):
                    symbols.append(symbol_text)
                else:
                    symbols.append(f"({symbol_text})")
        symbols.sort(key=lambda item: (item.startswith("("), item))
        factors: list[str] = []
        if constant != 1 or not symbols:
            factors.append(str(constant))
        factors.extend(symbols)
        result.append("*".join(factors))
    return tuple(result)


def replace_exact_tokens(text: str, replacements: dict[str, str]) -> str:
    """按字面量顺序替换文本片段。"""

    for old, new in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        text = text.replace(old, new)
    return text


def replace_word_tokens(text: str, replacements: dict[str, str]) -> str:
    """按标识符边界替换单词级 token，避免误伤更长标识符。"""

    for old, new in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        pattern = rf"(?<![A-Za-z0-9_]){re.escape(old)}(?![A-Za-z0-9_])"
        text = re.sub(pattern, new, text)
    return text


def build_runtime_function(function_name: str, source: str):
    """动态构造可被 `inspect.getsource(...)` 读取的 Python 函数。"""

    filename = f"<expectation:{function_name}>"
    if not source.endswith("\n"):
        source = f"{source}\n"
    linecache.cache[filename] = (len(source), None, source.splitlines(True), filename)
    namespace: dict[str, object] = {}
    exec(compile(source, filename, "exec"), namespace)
    return namespace[function_name]


__all__ = [
    "DimToken",
    "build_runtime_function",
    "contiguous_memory_type_from_memory",
    "contiguous_stride_tokens",
    "dynamic_memory_size_symbol",
    "format_dim_list",
    "format_dim_token",
    "memory_space_ir_name",
    "memory_type_from_memory",
    "nn_memory_type_ir",
    "numeric_type_ir",
    "random_memory_space",
    "random_memory_spaces",
    "random_onchip_space",
    "random_static_dims",
    "random_symbol_names",
    "replace_exact_tokens",
    "replace_word_tokens",
    "shape_tokens",
    "symbol_dim_token",
    "symbol_int_type_ir",
]
