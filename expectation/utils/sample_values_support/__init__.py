"""Expectation sample-value support package.

创建者: 守护最好的爱莉希雅
最后一次更改: 守护最好的爱莉希雅

功能说明:
- 为 `expectation.utils.sample_values` 提供拆分后的实现模块。
- 按职责拆分随机源、标量采样、类型/空间采样，便于后续继续扩共享 helper。

使用示例:
- `from expectation.utils.sample_values_support.scalars import get_random_alpha_string`
- `from expectation.utils.sample_values_support.types import get_random_memory_space`

关联文件:
- spec: [`agents/standard/测试文件约定.md`](agents/standard/测试文件约定.md)
- test: [`test/tools/test_sample_values.py`](test/tools/test_sample_values.py)
- 功能实现: [`expectation/utils/sample_values.py`](expectation/utils/sample_values.py)
- 功能实现: [`expectation/utils/sample_values_support/__init__.py`](expectation/utils/sample_values_support/__init__.py)
"""
