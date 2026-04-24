"""Expectation sample-value helpers.

创建者: 大闸蟹
最后一次更改: 榕

功能说明:
- 为 expectation 脚本提供统一的随机样本生成 facade，避免各 family 重复维护整数、字符串、`NumericType` 与 `MemorySpace` 取样逻辑。
- 当前文件保留稳定导入路径，实际实现拆分到 `expectation/utils/sample_values_support/` 目录。
- 除原有单值采样外，新增批量采样与片上空间采样入口，便于后续继续扩公共 helper。

使用示例:
- `from expectation.utils.sample_values import get_random_int`
- `from expectation.utils.sample_values import get_random_alpha_strings`
- `from expectation.utils.sample_values import get_random_memory_spaces`
- `value = get_random_int()`
- `symbols = get_random_alpha_strings(3, max_length=6, unique=True, uppercase=True)`
- `spaces = get_random_memory_spaces(2, unique=True)`
- `onchip = get_random_onchip_memory_space()`

关联文件:
- spec: [`agents/standard/测试文件约定.md`](agents/standard/测试文件约定.md)
- test: [`test/tools/test_sample_values.py`](test/tools/test_sample_values.py)
- 功能实现: [`expectation/utils/sample_values.py`](expectation/utils/sample_values.py)
- 功能实现: [`expectation/utils/sample_values_support/scalars.py`](expectation/utils/sample_values_support/scalars.py)
- 功能实现: [`expectation/utils/sample_values_support/types.py`](expectation/utils/sample_values_support/types.py)
"""

from __future__ import annotations

from expectation.utils.sample_values_support.scalars import (
    get_random_alpha_string,
    get_random_alpha_strings,
    get_random_int,
    get_random_ints,
    get_random_non_zero_int,
    get_random_non_zero_ints,
)
from expectation.utils.sample_values_support.types import (
    get_random_arithmetic_numeric_type,
    get_random_arithmetic_numeric_types,
    get_random_float_numeric_type,
    get_random_float_numeric_types,
    get_random_memory_space,
    get_random_memory_spaces,
    get_random_non_float_numeric_type,
    get_random_non_float_numeric_types,
    get_random_numeric_type,
    get_random_numeric_types,
    get_random_onchip_memory_space,
    get_random_onchip_memory_spaces,
    random_dma_space,
)


__all__ = [
    "get_random_alpha_string",
    "get_random_alpha_strings",
    "get_random_arithmetic_numeric_type",
    "get_random_arithmetic_numeric_types",
    "get_random_int",
    "get_random_ints",
    "get_random_float_numeric_type",
    "get_random_float_numeric_types",
    "get_random_memory_space",
    "get_random_memory_spaces",
    "get_random_non_zero_int",
    "get_random_non_zero_ints",
    "get_random_non_float_numeric_type",
    "get_random_non_float_numeric_types",
    "get_random_numeric_type",
    "get_random_numeric_types",
    "get_random_onchip_memory_space",
    "get_random_onchip_memory_spaces",
    "random_dma_space",
]
