"""Ptr implementation.


功能说明:
- 定义 Python 上层 `Ptr` 类型对象，只承载 pointee dtype。
- 提供 `Ptr(dtype)`、公开字段 `ptr.dtype` 与稳定 `repr(ptr)` 文本。

API 列表:
- `class Ptr(dtype: Attribute)`
- `Ptr.__repr__(self) -> str`

使用示例:
- from kernel_gen.symbol_variable.ptr import Ptr
- from xdsl.dialects.builtin import f32
- ptr = Ptr(f32)
- assert ptr.dtype is f32
- assert repr(ptr) == "Ptr(f32)"

关联文件:
- spec: spec/symbol_variable/ptr.md
- test: test/symbol_variable/test_ptr.py
- 功能实现: kernel_gen/symbol_variable/ptr.py
"""

from __future__ import annotations

from xdsl.ir import Attribute


class Ptr:
    """公开的 pointee dtype 承载对象。


    功能说明:
    - 表示“指向某个 element dtype 的指针类型对象”。
    - 仅公开 `dtype` 与 `repr(...)`，不承载名字、shape、stride 或地址值。

    使用示例:
    - from kernel_gen.symbol_variable.ptr import Ptr
    - from xdsl.dialects.builtin import f32
    - ptr = Ptr(f32)

    关联文件:
    - spec: spec/symbol_variable/ptr.md
    - test: test/symbol_variable/test_ptr.py
    - 功能实现: kernel_gen/symbol_variable/ptr.py
    """

    _ARITY_ERROR_MESSAGE = "Ptr requires exactly one dtype"

    def __init__(self: "Ptr", *dtype: Attribute) -> None:
        """初始化 `Ptr(dtype)`。


        功能说明:
        - 仅接受一个 dtype 参数。
        - 参数数量非法时抛出带固定消息的 `TypeError`。

        使用示例:
        - from xdsl.dialects.builtin import f32
        - Ptr(f32)

        关联文件:
        - spec: spec/symbol_variable/ptr.md
        - test: test/symbol_variable/test_ptr.py
        - 功能实现: kernel_gen/symbol_variable/ptr.py
        """

        if len(dtype) != 1:
            raise TypeError(self._ARITY_ERROR_MESSAGE)
        self.dtype = dtype[0]

    def __repr__(self: "Ptr") -> str:
        """返回稳定公开文本。


        功能说明:
        - 以 `Ptr(<dtype>)` 形式渲染 pointee dtype。
        - 使用 `str(dtype)` 保持 `f32` 等 xDSL 类型文本稳定。

        使用示例:
        - from xdsl.dialects.builtin import f32
        - repr(Ptr(f32))

        关联文件:
        - spec: spec/symbol_variable/ptr.md
        - test: test/symbol_variable/test_ptr.py
        - 功能实现: kernel_gen/symbol_variable/ptr.py
        """

        return f"Ptr({self.dtype})"


__all__ = ["Ptr"]
