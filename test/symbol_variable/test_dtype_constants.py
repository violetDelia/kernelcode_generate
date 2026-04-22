"""dtype_constants tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 dtype 常量集合内容与一致性约束。

使用示例:
- pytest -q test/symbol_variable/test_dtype_constants.py

关联文件:
- 功能实现: kernel_gen/symbol_variable/dtype_constants.py
- Spec 文档: spec/symbol_variable/dtype_constants.md
- 测试文件: test/symbol_variable/test_dtype_constants.py
"""

from __future__ import annotations


# DC-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 验证 FLOAT_DTYPES 集合内容正确。
# 使用示例: pytest -q test/symbol_variable/test_dtype_constants.py -k test_float_dtypes
# 对应功能实现文件路径: kernel_gen/symbol_variable/dtype_constants.py
# 对应 spec 文件路径: spec/symbol_variable/dtype_constants.md
# 对应测试文件路径: test/symbol_variable/test_dtype_constants.py
def test_float_dtypes() -> None:
    from kernel_gen.symbol_variable.dtype_constants import FLOAT_DTYPES
    from kernel_gen.symbol_variable.type import NumericType

    expected = {
        NumericType.Float16,
        NumericType.BFloat16,
        NumericType.Float32,
        NumericType.Float64,
    }
    assert FLOAT_DTYPES == expected


# DC-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 验证 INT_DTYPES 集合内容正确。
# 使用示例: pytest -q test/symbol_variable/test_dtype_constants.py -k test_int_dtypes
# 对应功能实现文件路径: kernel_gen/symbol_variable/dtype_constants.py
# 对应 spec 文件路径: spec/symbol_variable/dtype_constants.md
# 对应测试文件路径: test/symbol_variable/test_dtype_constants.py
def test_int_dtypes() -> None:
    from kernel_gen.symbol_variable.dtype_constants import INT_DTYPES
    from kernel_gen.symbol_variable.type import NumericType

    expected = {
        NumericType.Int8,
        NumericType.Int16,
        NumericType.Int32,
        NumericType.Int64,
        NumericType.Uint8,
        NumericType.Uint16,
        NumericType.Uint32,
        NumericType.Uint64,
    }
    assert INT_DTYPES == expected


# DC-003
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 验证 NN_FLOAT_DTYPES 与 FLOAT_DTYPES 保持一致。
# 使用示例: pytest -q test/symbol_variable/test_dtype_constants.py -k test_nn_float_matches_float
# 对应功能实现文件路径: kernel_gen/symbol_variable/dtype_constants.py
# 对应 spec 文件路径: spec/symbol_variable/dtype_constants.md
# 对应测试文件路径: test/symbol_variable/test_dtype_constants.py
def test_nn_float_matches_float() -> None:
    from kernel_gen.symbol_variable.dtype_constants import FLOAT_DTYPES, NN_FLOAT_DTYPES

    assert NN_FLOAT_DTYPES == FLOAT_DTYPES


# DC-004
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 验证 arithmetic dtype 顺序与 rank 映射一致。
# 使用示例: pytest -q test/symbol_variable/test_dtype_constants.py -k test_arithmetic_dtype_order_and_rank
# 对应功能实现文件路径: kernel_gen/symbol_variable/dtype_constants.py
# 对应 spec 文件路径: spec/symbol_variable/dtype_constants.md
# 对应测试文件路径: test/symbol_variable/test_dtype_constants.py
def test_arithmetic_dtype_order_and_rank() -> None:
    from kernel_gen.symbol_variable.dtype_constants import ARITHMETIC_DTYPE_ORDER, ARITHMETIC_DTYPE_RANK
    from kernel_gen.symbol_variable.type import NumericType

    expected_order = (
        NumericType.Int8,
        NumericType.Uint8,
        NumericType.Int16,
        NumericType.Uint16,
        NumericType.Int32,
        NumericType.Uint32,
        NumericType.Int64,
        NumericType.Uint64,
        NumericType.Float16,
        NumericType.BFloat16,
        NumericType.Float32,
        NumericType.Float64,
    )
    assert ARITHMETIC_DTYPE_ORDER == expected_order
    assert {dtype: index for index, dtype in enumerate(expected_order)} == ARITHMETIC_DTYPE_RANK
