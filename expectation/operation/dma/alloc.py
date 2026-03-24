"""DMA alloc expectation.

创建者: 榕
最后一次更改: 榕

功能说明:
- 验证 dma.alloc 返回指定 shape、dtype、space 的 Memory。
- 验证 alloc 在默认参数下生成默认 `space/stride`。
- 验证 alloc 的 `dtype/space/stride` 边界。

使用示例:
- python expectation/operation/dma/alloc.py

关联文件:
- spec: spec/operation/dma.md
- test: test/operation/test_operation_dma.py
- 功能实现: kernel_gen/operation/dma.py
"""

from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
# 直接执行 expectation 脚本时，先移除脚本所在目录，避免同目录文件名污染导入链。
sys.path = [
    search_path
    for search_path in sys.path
    if Path(search_path or ".").resolve() != SCRIPT_DIR
]

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest

from kernel_gen.operation.dma import alloc
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.type import NumericType
from expectation.utils.random import get_random_alpha_string

# alloc 应返回指定 shape、dtype、space 的 Memory。
s1 = get_random_alpha_string()
s2 = get_random_alpha_string()

buf = alloc([s1, s2], NumericType.Float32, space=MemorySpace.SM)

assert isinstance(buf, Memory)
assert buf.get_shape() == [s1, s2]
assert buf.get_type() is NumericType.Float32
assert buf.get_space() is MemorySpace.SM
assert buf.get_stride()[0].get_value() == s2
assert buf.get_stride()[1] == 1

# 默认参数下，应使用 GM 和默认连续 stride。
default_buf = alloc([2, 4], NumericType.Int32)

assert isinstance(default_buf, Memory)
assert default_buf.get_shape() == [2, 4]
assert default_buf.get_type() is NumericType.Int32
assert default_buf.get_space() is MemorySpace.GM
assert default_buf.get_stride() == [4, 1]

# 显式传入 stride 时，应按传入值构造。
manual_stride_buf = alloc([s1, s2], NumericType.Float16, space=MemorySpace.LM, stride=[1, 1])

assert manual_stride_buf.get_shape() == [s1, s2]
assert manual_stride_buf.get_type() is NumericType.Float16
assert manual_stride_buf.get_space() is MemorySpace.LM
assert manual_stride_buf.get_stride() == [1, 1]

# dtype 不是 NumericType 时，应显式报错。
with pytest.raises(TypeError):
    alloc([2, 4], "float32")

# space 不是 MemorySpace 时，应显式报错。
with pytest.raises(TypeError):
    alloc([2, 4], NumericType.Float32, space="SM")

# 非法 shape 输入应显式报错。
with pytest.raises(ValueError):
    alloc("2x4", NumericType.Float32)

# stride 的 rank 与 shape 不一致时，应显式报错。
with pytest.raises(ValueError):
    alloc([2, 4], NumericType.Float32, stride=[1])
