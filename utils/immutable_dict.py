"""ImmutableDict implementation.

创建者: 大哥大
最后一次更改: 大哥大

功能说明:
- 提供不可覆盖/不可删除键的字典类型 `ImmutableDict`。

使用示例:
- d = ImmutableDict()
- d["a"] = 1

关联文件:
- spec: spec/utils/immutable_dict.md
- test: test/utils/test_immutable_dict.py
- 功能实现: utils/immutable_dict.py
"""

from __future__ import annotations


class ImmutableDict(dict):
    """不可覆盖/不可删除键的字典。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.key_set: set = set()

    def __setitem__(self, key, value):
        if key in self.key_set:
            raise KeyError("Key already exists!")
        super().__setitem__(key, value)
        self.key_set.add(key)

    def __delitem__(self, key):
        raise KeyError("Key can not be deleted!")

    def pop(self, key, default=None):  # pylint: disable=unused-argument
        raise KeyError("Key can not be deleted!")

    def clear(self):
        raise Exception("Key can not be deleted!")

    def clear_all(self):
        super().clear()
        self.key_set.clear()
