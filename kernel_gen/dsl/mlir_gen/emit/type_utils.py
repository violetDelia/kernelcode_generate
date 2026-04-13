"""Emit 类型工具。

创建者: jcc你莫辜负
最后一次更改: jcc你莫辜负

功能说明:
- 提供类型推导与 memory type 组装的共享工具。
- 供 emit 共享层与测试用例复用。

使用示例:
- result_type = infer_expr_type(expr, type_map)

关联文件:
- spec: [spec/dsl/emit_mlir.md](spec/dsl/emit_mlir.md)
- test: [test/dsl/mlir_gen/emit/test_type_utils.py](test/dsl/mlir_gen/emit/test_type_utils.py)
- 功能实现: [kernel_gen/dsl/mlir_gen/emit/type_utils.py](kernel_gen/dsl/mlir_gen/emit/type_utils.py)
"""

from __future__ import annotations

from typing import Sequence

from xdsl.ir import Attribute

from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dsl.emit_mlir import _infer_expr_type, _memory_type_from_parts


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
    return _infer_expr_type(expr, type_map)


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
    return _memory_type_from_parts(shape, stride, element_type, space)
