"""Emit 类型工具。

创建者: jcc你莫辜负
最后一次更改: jcc你莫辜负

功能说明:
- 提供类型推导与 memory type 组装的共享工具。
- 供 emit 共享层与测试用例复用。

API 列表:
- `infer_expr_type(expr: object, type_map: dict[int, object]) -> object`
- `memory_type_from_parts(shape: Sequence[Attribute], stride: Sequence[Attribute], element_type: Attribute, space: NnMemorySpaceAttr) -> NnMemoryType`

helper 清单:
- `_expr_key(expr: object) -> int`

使用示例:
- result_type = infer_expr_type(expr, type_map)

关联文件:
- spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
- test: [test/dsl/mlir_gen/emit/test_type_utils.py](test/dsl/mlir_gen/emit/test_type_utils.py)
- 功能实现: [kernel_gen/dsl/mlir_gen/emit/type_utils.py](kernel_gen/dsl/mlir_gen/emit/type_utils.py)
"""

from __future__ import annotations

from typing import Sequence

from xdsl.dialects.builtin import ArrayAttr, f32, i1, i32
from xdsl.ir import Attribute

from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dsl.ast import ConstAST



class LoweringError(ValueError):
    """当前文件内使用的类型推导失败错误。"""

    def __init__(self, message: str, location: object | None = None) -> None:
        super().__init__(message)
        self.location = location


def _expr_key(expr: object) -> int:
    """返回与 emit family 其余模块一致的表达式缓存 key。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 对公开 `type_utils` 保持与 emit family 其余缓存约定一致。
    - 当前公开约定只依赖对象同一性，不额外暴露 `.core` 私有 helper。

    使用示例:
    - key = _expr_key(expr)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/mlir_gen/emit/test_type_utils.py](test/dsl/mlir_gen/emit/test_type_utils.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/type_utils.py](kernel_gen/dsl/mlir_gen/emit/type_utils.py)
    """

    return id(expr)


def infer_expr_type(expr: object, type_map: dict[int, object]) -> object:
    """推导表达式的结果类型。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 复用 emit 内部类型推导逻辑，避免重复实现。
    - 仅暴露最小接口，避免扩展到 family 语义。

    参数说明:
    - expr: 待推导的 AST 表达式。
    - type_map: 已知表达式类型映射。

    返回说明:
    - 返回推导得到的类型对象。

    使用示例:
    - inferred = infer_expr_type(ConstAST(1), {})

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/mlir_gen/emit/test_type_utils.py](test/dsl/mlir_gen/emit/test_type_utils.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/type_utils.py](kernel_gen/dsl/mlir_gen/emit/type_utils.py)
    """
    expr_key = _expr_key(expr)
    if expr_key in type_map:
        return type_map[expr_key]
    if isinstance(expr, ConstAST):
        if isinstance(expr.value, bool):
            return i1
        if isinstance(expr.value, int):
            return i32
        if isinstance(expr.value, float):
            return f32
        raise LoweringError("Unsupported constant type", location=expr.location)
    raise LoweringError("Unsupported expression for infer_expr_type helper")


def memory_type_from_parts(
    shape: Sequence[Attribute],
    stride: Sequence[Attribute],
    element_type: Attribute,
    space: NnMemorySpaceAttr,
) -> NnMemoryType:
    """组装 `NnMemoryType`。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 将 shape/stride/element_type/space 封装为标准 memory type。
    - 复用 emit 内部构造逻辑，保持结果一致。

    参数说明:
    - shape: shape 属性序列。
    - stride: stride 属性序列。
    - element_type: 元素类型。
    - space: memory space 属性。

    返回说明:
    - 返回 NnMemoryType 实例。

    使用示例:
    - mem_type = memory_type_from_parts(shape, stride, f32, space)

    关联文件:
    - spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
    - test: [test/dsl/mlir_gen/emit/test_type_utils.py](test/dsl/mlir_gen/emit/test_type_utils.py)
    - 功能实现: [kernel_gen/dsl/mlir_gen/emit/type_utils.py](kernel_gen/dsl/mlir_gen/emit/type_utils.py)
    """
    return NnMemoryType(ArrayAttr(list(shape)), ArrayAttr(list(stride)), element_type, space)
