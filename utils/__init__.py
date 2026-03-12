"""utils package exports.

创建者: 大哥大
最后一次更改: 大哥大

功能说明:
- 导出 ImmutableDict、has_callable、get_py_file_vars、generate_get_set。

使用示例:
- from utils import ImmutableDict, has_callable

关联文件:
- spec: spec/utils/__init__.md
- test: test/utils/test_utils_init.py
- 功能实现: utils/__init__.py
"""

from .immutable_dict import ImmutableDict
from .module_query import get_py_file_vars, has_callable
from .generate_get_set import generate_get_set

__all__ = ["ImmutableDict", "has_callable", "get_py_file_vars", "generate_get_set"]
