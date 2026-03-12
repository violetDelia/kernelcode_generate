"""Generate getter/setter helpers.

创建者: 大哥大
最后一次更改: 大哥大

功能说明:
- 为类生成 get_xxx / set_xxx 方法。

使用示例:
- @generate_get_set({"_x": "x"})
- class Foo: ...

关联文件:
- spec: spec/utils/generate_get_set.md
- test: test/utils/test_generate_get_set.py
- 功能实现: utils/generate_get_set.py
"""

from __future__ import annotations

from enum import Enum
from typing import Callable, Dict


class GENERATE_GET_SET(Enum):
    NOT_GENERATE = 0
    PLACE_HOLDER = 1


def generate_get_set(
    map: Dict[str, str],
    specified_get: Dict[str, Callable | None] | None = None,
    specified_set: Dict[str, Callable | None] | None = None,
):
    """返回类装饰器，按 map 生成 getter/setter。"""

    specified_get = specified_get or {}
    specified_set = specified_set or {}

    def decorator(cls):
        assert isinstance(cls, type)

        for private_name, public_name in map.items():
            get_name = f"get_{public_name}"
            set_name = f"set_{public_name}"

            get_key = private_name if private_name in specified_get else public_name
            if get_key in specified_get:
                getter = specified_get[get_key]
                if getter is not None:
                    setattr(cls, get_name, getter)
            else:
                def _getter(self, _p=private_name):
                    return getattr(self, _p)

                setattr(cls, get_name, _getter)

            set_key = private_name if private_name in specified_set else public_name
            if set_key in specified_set:
                setter = specified_set[set_key]
                if setter is not None:
                    setattr(cls, set_name, setter)
            else:
                def _setter(self, value, _p=private_name):
                    old_value = getattr(self, _p)
                    if not isinstance(value, type(old_value)):
                        raise TypeError("Type not match")
                    setattr(self, _p, value)

                setattr(cls, set_name, _setter)

        return cls

    return decorator
