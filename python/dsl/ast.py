"""DSL AST definitions.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 定义 DSL 前端使用的 AST 节点数据结构。

使用示例:
- from python.dsl.ast import FunctionAST, BlockAST
- FunctionAST(name="kernel", inputs=[], outputs=[], body=BlockAST([]))

关联文件:
- spec: spec/dsl/ast.md
- test: test/dsl/test_ast_visitor.py
- 功能实现: python/dsl/ast.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class SourceLocation:
    """源码位置信息。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 记录 AST 节点在源码中的行列位置。

    使用示例:
    - SourceLocation(line=1, column=0)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: python/dsl/ast.py
    """

    line: int
    column: int


@dataclass(frozen=True)
class Diagnostic:
    """前端诊断信息。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 记录错误消息与对应的源码位置信息。

    使用示例:
    - Diagnostic(message="Unsupported syntax", location=SourceLocation(3, 4))

    关联文件:
    - spec: spec/dsl/ast_visitor.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: python/dsl/ast.py
    """

    message: str
    location: SourceLocation | None = None


@dataclass(frozen=True)
class ModuleAST:
    """DSL 模块节点。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 聚合多个 `FunctionAST` 作为 DSL 模块入口。

    使用示例:
    - ModuleAST(functions=[FunctionAST(name="kernel", inputs=[], outputs=[], body=BlockAST([]))])

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: python/dsl/ast.py
    """

    functions: list[FunctionAST]


@dataclass(frozen=True)
class TensorAST:
    """张量参数节点。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 表示函数签名中的张量输入。

    使用示例:
    - TensorAST(name="A", memory=memory)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: python/dsl/ast.py
    """

    name: str
    memory: object
    location: SourceLocation | None = None


@dataclass(frozen=True)
class ScalarArgAST:
    """标量参数节点。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 表示函数签名中的标量输入。

    使用示例:
    - ScalarArgAST(name="n", value_type=int)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: python/dsl/ast.py
    """

    name: str
    value_type: type
    location: SourceLocation | None = None


@dataclass(frozen=True)
class VarAST:
    """变量节点。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 表示循环变量或中间变量。

    使用示例:
    - VarAST(name="i")

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: python/dsl/ast.py
    """

    name: str
    location: SourceLocation | None = None


@dataclass(frozen=True)
class BlockAST:
    """语句块节点。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 有序保存 AST 语句节点。

    使用示例:
    - BlockAST(statements=[])

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: python/dsl/ast.py
    """

    statements: list[object]
    location: SourceLocation | None = None


@dataclass(frozen=True)
class ForAST:
    """循环节点。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 表示 DSL 中的 for 循环结构。

    使用示例:
    - ForAST(var=VarAST("i"), start=ConstAST(0), end=ConstAST(10), body=BlockAST([]))

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: python/dsl/ast.py
    """

    var: VarAST
    start: object
    end: object
    body: BlockAST
    location: SourceLocation | None = None


@dataclass(frozen=True)
class StoreAST:
    """存储节点。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 描述向张量写入的语义。

    使用示例:
    - StoreAST(tensor=TensorAST("A", memory), offset=ConstAST(0), stride=None, value=ConstAST(1))

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: python/dsl/ast.py
    """

    tensor: TensorAST
    offset: object
    stride: object | None
    value: object
    location: SourceLocation | None = None


@dataclass(frozen=True)
class LoadAST:
    """读取节点。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 描述从张量读取的语义。

    使用示例:
    - LoadAST(tensor=TensorAST("A", memory), offset=ConstAST(0), stride=None)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: python/dsl/ast.py
    """

    tensor: TensorAST
    offset: object
    stride: object | None
    location: SourceLocation | None = None


@dataclass(frozen=True)
class BinaryExprAST:
    """二元表达式节点。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 表示逐元素算术表达式。

    使用示例:
    - BinaryExprAST(op="add", lhs=VarAST("x"), rhs=VarAST("y"))

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: python/dsl/ast.py
    """

    op: str
    lhs: object
    rhs: object
    location: SourceLocation | None = None


@dataclass(frozen=True)
class CompareExprAST:
    """比较表达式节点。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 表示逐元素比较表达式。

    使用示例:
    - CompareExprAST(op="eq", lhs=VarAST("x"), rhs=VarAST("y"))

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: python/dsl/ast.py
    """

    op: str
    lhs: object
    rhs: object
    location: SourceLocation | None = None


@dataclass(frozen=True)
class ConstAST:
    """常量节点。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 表示常量值。

    使用示例:
    - ConstAST(value=1)

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: python/dsl/ast.py
    """

    value: object
    location: SourceLocation | None = None


@dataclass(frozen=True)
class FunctionAST:
    """函数节点。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 表示可 lowering 的 DSL 函数入口。

    使用示例:
    - FunctionAST(name="kernel", inputs=[], outputs=[], body=BlockAST([]))

    关联文件:
    - spec: spec/dsl/ast.md
    - test: test/dsl/test_ast_visitor.py
    - 功能实现: python/dsl/ast.py
    """

    name: str
    inputs: list[TensorAST | ScalarArgAST]
    outputs: list[TensorAST | ScalarArgAST]
    body: BlockAST
    location: SourceLocation | None = None
    source: str | None = None
    py_ast: object | None = None
    diagnostics: list[Diagnostic] = field(default_factory=list)

    def iter_inputs(self) -> Iterable[TensorAST | ScalarArgAST]:
        """迭代输入参数。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 提供输入参数的统一迭代入口。

        使用示例:
        - list(func_ast.iter_inputs())

        关联文件:
        - spec: spec/dsl/ast.md
        - test: test/dsl/test_ast_visitor.py
        - 功能实现: python/dsl/ast.py
        """

        return iter(self.inputs)
