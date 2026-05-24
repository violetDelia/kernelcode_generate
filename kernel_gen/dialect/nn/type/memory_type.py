"""nn memory type.

功能说明:
- 承载 nn dialect package 拆分后的 nn memory type 实现。

API 列表:
- `class NnMemoryType(shape: ArrayAttr[SymbolExprAttr], stride: ArrayAttr[SymbolExprAttr], element_type: Attribute, space: NnMemorySpaceAttr, template_name: StringAttr | str | None = None)`
- `copy_memory_type(memory_type: NnMemoryType, *, shape: ArrayAttr[SymbolExprAttr] | None = None, stride: ArrayAttr[SymbolExprAttr] | None = None, element_type: Attribute | None = None, space: NnMemorySpaceAttr | None = None) -> NnMemoryType`
- `copy_memory_type_with_template_name(memory_type: NnMemoryType, template_name: str | StringAttr, *, shape: ArrayAttr[SymbolExprAttr] | None = None, stride: ArrayAttr[SymbolExprAttr] | None = None, element_type: Attribute | None = None, space: NnMemorySpaceAttr | None = None) -> NnMemoryType`

使用示例:
- from kernel_gen.dialect.nn import NnMemoryType

关联文件:
- spec: spec/dialect/nn.md
- test: test/dialect/nn/test_type.py
- 功能实现: kernel_gen/dialect/nn/type/memory_type.py
"""

from __future__ import annotations

import re

from kernel_gen.dialect.nn.attr.space_attr import NnMemorySpaceAttr
from xdsl.dialects.builtin import ArrayAttr, StringAttr
from xdsl.ir import Attribute, ParametrizedAttribute, TypeAttribute
from xdsl.irdl import irdl_attr_definition, param_def
from xdsl.parser import AttrParser
from xdsl.printer import Printer

from kernel_gen.core.contracts import raise_verify_error as core_raise_verify_error
from kernel_gen.core.error import ERROR_ACTION, ERROR_ACTUAL, ERROR_TEMPLATE, ErrorKind, ErrorModule, kernel_code_error


# Localized helpers from retired package-internal modules.

_ERROR_SCENE = "dialect.nn verifier"


_TEMPLATE_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

def _print_dim_list(printer: Printer, dims: ArrayAttr[Attribute]) -> None:
    """打印 shape 或 stride 维度列表。


    功能说明:
    - 按 `[d0, d1, ...]` 文本格式输出维度。

    使用示例:
    - _print_dim_list(printer, dims)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    printer.print_string("[")
    for index, dim in enumerate(dims.data):
        if index:
            printer.print_string(", ")
        if not _NN_MEMORY_TYPE.is_symbol_expr_attr(dim):
            core_raise_verify_error(_ERROR_SCENE, "dimension list only supports SymbolExprAttr")
        printer.print_attribute(dim)
    printer.print_string("]")

def _verify_dim_entry(dim: Attribute, field_name: str) -> None:
    """校验单个维度条目合法性。


    功能说明:
    - 仅接受 `SymbolExprAttr`。
    - 若表达式可静态判定为整数，则 shape/stride 维度必须非负。

    使用示例:
    - _verify_dim_entry(SymbolExprAttr.from_expr(\"N\"), \"shape\")

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    if not _NN_MEMORY_TYPE.is_symbol_expr_attr(dim):
        core_raise_verify_error(_ERROR_SCENE, f"{field_name} dimensions must be SymbolExprAttr")
    dim.verify()
    value = _NN_MEMORY_TYPE.static_int_from_dim(dim)
    if value is not None and value < 0:
        core_raise_verify_error(_ERROR_SCENE, f"{field_name} dimensions must be non-negative")

class _NnMemoryTypeRules:
    """当前文件内的局部 verifier 规则容器。

    功能说明:
    - 合并本文件重复使用的局部规则，避免多个 private helper 互相调用。
    - 该容器不导出，不作为跨文件公开 API。

    使用示例:
    - _NN_MEMORY_TYPE.symbol_expr_attr_from_expr(...)
    """

    @staticmethod
    def symbol_expr_attr_from_expr(expr: str) -> Attribute:
        """构造公开 SymbolExprAttr。

        功能说明:
        - 延迟导入 `SymbolExprAttr`，避免 nn/symbol 模块初始化互相依赖。

        使用示例:
        - _NN_MEMORY_TYPE.symbol_expr_attr_from_expr("N")

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        from kernel_gen.dialect.symbol import SymbolExprAttr

        return SymbolExprAttr.from_expr(expr)

    @staticmethod
    def is_symbol_expr_attr(attr: Attribute) -> bool:
        """判断属性是否是公开 SymbolExprAttr。

        功能说明:
        - 通过延迟导入的公开 class 判断 memory shape/stride 条目。

        使用示例:
        - _NN_MEMORY_TYPE.is_symbol_expr_attr(SymbolExprAttr.from_expr("N"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        from kernel_gen.dialect.symbol import SymbolExprAttr

        return isinstance(attr, SymbolExprAttr)

    @staticmethod
    def dim_expr_text(dim: Attribute) -> str:
        """读取 SymbolExprAttr 的规范表达式文本。

        功能说明:
        - 统一 shape/stride 的比较、静态求值和 stride 推导入口。

        使用示例:
        - _NN_MEMORY_TYPE.dim_expr_text(SymbolExprAttr.from_expr("N + 1"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        if not _NN_MEMORY_TYPE.is_symbol_expr_attr(dim):
            core_raise_verify_error(_ERROR_SCENE, "dimension entries must be SymbolExprAttr")
        dim.verify()
        return dim.expr.data

    @staticmethod
    def static_int_from_expr_text(expr: str) -> int | None:
        """尝试从规范表达式文本提取静态整数。

        功能说明:
        - 仅识别十进制整数字面量，动态表达式返回 None。

        使用示例:
        - _NN_MEMORY_TYPE.static_int_from_expr_text("4")

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        signless = expr[1:] if expr.startswith("-") else expr
        if signless.isdecimal():
            return int(expr)
        return None

    @staticmethod
    def static_int_from_dim(dim: Attribute) -> int | None:
        """尝试从 SymbolExprAttr 维度提取静态整数。

        功能说明:
        - 对 `#symbol.expr<4>` 返回 4；动态维度返回 None。

        使用示例:
        - _NN_MEMORY_TYPE.static_int_from_dim(SymbolExprAttr.from_expr("4"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        return _NN_MEMORY_TYPE.static_int_from_expr_text(_NN_MEMORY_TYPE.dim_expr_text(dim))

    def _normalize_template_name_attr(template_name: StringAttr | str | None) -> StringAttr:
        """规整 memory template name 参数。

        功能说明:
        - `None` 规整为空 `StringAttr`，表示 memory type 未携带 template name。
        - `str` 与 `StringAttr` 是唯一公开输入形态。

        使用示例:
        - attr = _normalize_template_name_attr("T1")

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        if template_name is None:
            return StringAttr("")
        if isinstance(template_name, StringAttr):
            return template_name
        if isinstance(template_name, str):
            return StringAttr(template_name)
        raise TypeError("template_name must be str, StringAttr or None")

    @staticmethod
    def verify_template_name_text(template_name: str) -> None:
        """校验 memory template name 文本。

        功能说明:
        - 空字符串表示未携带 template name。
        - 非空 template name 必须是 C identifier 风格名称，拒绝数字开头、空格与尖括号文本。

        使用示例:
        - _NN_MEMORY_TYPE.verify_template_name_text("T1")

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        if template_name == "":
            return
        if _TEMPLATE_NAME_PATTERN.fullmatch(template_name) is None:
            core_raise_verify_error(_ERROR_SCENE, "nn memory template_name must be an identifier")

_NN_MEMORY_TYPE = _NnMemoryTypeRules()

def _normalize_template_name_attr(template_name: StringAttr | str | None) -> StringAttr:
    """规整 memory template name 参数。

    功能说明:
    - `None` 规整为空 `StringAttr`，表示 memory type 未携带 template name。
    - `str` 与 `StringAttr` 是唯一公开输入形态。

    使用示例:
    - attr = _normalize_template_name_attr("T1")
    """

    if template_name is None:
        normalized = StringAttr("")
    elif isinstance(template_name, StringAttr):
        normalized = template_name
    elif isinstance(template_name, str):
        normalized = StringAttr(template_name)
    else:
        raise TypeError("template_name must be str, StringAttr or None")
    _NN_MEMORY_TYPE.verify_template_name_text(normalized.data)
    return normalized

@irdl_attr_definition
class NnMemoryType(ParametrizedAttribute, TypeAttribute):
    """NN memory type。


    功能说明:
    - 建模 `shape`、`stride`、`element_type`、`space` 与可选 `template_name`。

    使用示例:
    - NnMemoryType(ArrayAttr([SymbolExprAttr.from_expr(\"4\")]), ArrayAttr([SymbolExprAttr.from_expr(\"1\")]), IntegerType(32), NnMemorySpaceAttr.from_name(\"global\"), template_name=\"T1\")

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    name = "nn.memory"

    shape: ArrayAttr[Attribute] = param_def(ArrayAttr[Attribute])
    stride: ArrayAttr[Attribute] = param_def(ArrayAttr[Attribute])
    element_type: Attribute = param_def(Attribute)
    space: NnMemorySpaceAttr = param_def(NnMemorySpaceAttr)
    template_name: StringAttr = param_def(StringAttr)

    def __init__(
        self,
        shape: ArrayAttr[SymbolExprAttr],
        stride: ArrayAttr[SymbolExprAttr],
        element_type: Attribute,
        space: NnMemorySpaceAttr,
        template_name: StringAttr | str | None = None,
    ) -> None:
        """初始化 memory type。

        功能说明:
        - 保留四参数构造兼容，默认不携带 template name。
        - 第五参数写入公开 `template_name` 字段，供后续 template-name infer 与 EmitC 使用。

        使用示例:
        - NnMemoryType(shape, stride, i32, NnMemorySpaceAttr.from_name("global"), template_name="T1")
        """

        super().__init__(shape, stride, element_type, space, _normalize_template_name_attr(template_name))

    @classmethod
    def parse_parameters(cls, parser: AttrParser) -> Sequence[Attribute]:
        """解析 memory type 参数。

        功能说明:
        - 解析 `!nn.memory<[#symbol.expr<N>], [#symbol.expr<1>], i32, #nn.space<global>, template = T1>`。
        - shape/stride 必须是 `ArrayAttr[SymbolExprAttr]`，不兼容旧 bare string 或 IntAttr 写法。
        - `template = T1` 可省略，省略时 memory type 不携带 template name。

        使用示例:
        - Parser(ctx, "!nn.memory<[#symbol.expr<N>], [#symbol.expr<1>], i32, #nn.space<global>, template = T1>").parse_attribute()
        """

        parser.parse_punctuation("<", "Expected '<' for nn memory type.")
        shape = parser.parse_attribute()
        parser.parse_punctuation(",", "Expected ',' after nn memory shape.")
        stride = parser.parse_attribute()
        parser.parse_punctuation(",", "Expected ',' after nn memory stride.")
        element_type = parser.parse_attribute()
        parser.parse_punctuation(",", "Expected ',' after nn memory element type.")
        space = parser.parse_attribute()
        template_name = StringAttr("")
        if parser.parse_optional_punctuation(",") is not None:
            keyword = parser.parse_identifier("Expected 'template' memory option.")
            if keyword != "template":
                parser.raise_error("nn memory type only accepts template option")
            parser.parse_punctuation("=", "Expected '=' after nn memory template option.")
            template_name = StringAttr(parser.parse_identifier("Expected nn memory template name."))
        parser.parse_punctuation(">", "Expected '>' for nn memory type.")
        if not isinstance(shape, ArrayAttr):
            parser.raise_error("nn memory shape must be ArrayAttr[SymbolExprAttr]")
        if not isinstance(stride, ArrayAttr):
            parser.raise_error("nn memory stride must be ArrayAttr[SymbolExprAttr]")
        if not isinstance(space, NnMemorySpaceAttr):
            parser.raise_error("nn memory type space must be #nn.space<...>")
        return (shape, stride, element_type, space, template_name)

    def print_parameters(self, printer: Printer) -> None:
        """打印 memory type 参数。

        功能说明:
        - 输出结构化 `SymbolExprAttr` shape/stride 列表。

        使用示例:
        - printer.print_attribute(memory_type)
        """

        printer.print_string("<")
        _print_dim_list(printer, self.shape)
        printer.print_string(", ")
        _print_dim_list(printer, self.stride)
        printer.print_string(", ")
        printer.print_attribute(self.element_type)
        printer.print_string(", ")
        printer.print_attribute(self.space)
        template_name = self.template_name.data
        if template_name:
            printer.print_string(", template = ")
            printer.print_string(template_name)
        printer.print_string(">")

    def verify(self) -> None:
        """校验 memory type。

        功能说明:
        - 要求 shape/stride rank 一致。
        - 要求 shape/stride 每个条目均为 `SymbolExprAttr`。
        - 要求 template name 为空或合法 identifier。

        使用示例:
        - memory_type.verify()
        """

        self.space.verify()
        if len(self.shape.data) != len(self.stride.data):
            core_raise_verify_error(_ERROR_SCENE, "nn memory shape and stride rank must match")

        for dim in self.shape.data:
            _verify_dim_entry(dim, "shape")
        for dim in self.stride.data:
            _verify_dim_entry(dim, "stride")
        _NN_MEMORY_TYPE.verify_template_name_text(self.template_name.data)

def copy_memory_type(
    memory_type: NnMemoryType,
    *,
    shape: ArrayAttr[SymbolExprAttr] | None = None,
    stride: ArrayAttr[SymbolExprAttr] | None = None,
    element_type: Attribute | None = None,
    space: NnMemorySpaceAttr | None = None,
) -> NnMemoryType:
    """复制 memory type 并清除 template name。

    功能说明:
    - 用于创建 layout/dtype/space 派生类型时明确退场 template name，避免跨新 buffer 泄漏。
    - 未传入的字段沿用原 memory type。

    使用示例:
    - new_type = copy_memory_type(old_type, space=NnMemorySpaceAttr.from_name("shared"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    memory_type.verify()
    result = NnMemoryType(
        memory_type.shape if shape is None else shape,
        memory_type.stride if stride is None else stride,
        memory_type.element_type if element_type is None else element_type,
        memory_type.space if space is None else space,
    )
    result.verify()
    return result

def copy_memory_type_with_template_name(
    memory_type: NnMemoryType,
    template_name: str | StringAttr,
    *,
    shape: ArrayAttr[SymbolExprAttr] | None = None,
    stride: ArrayAttr[SymbolExprAttr] | None = None,
    element_type: Attribute | None = None,
    space: NnMemorySpaceAttr | None = None,
) -> NnMemoryType:
    """复制 memory type 并写入 template name。

    功能说明:
    - 用于 `TemplateNameInferPass` 把推导结果写回 `NnMemoryType`。
    - 非法 template name 按 dialect verifier 合同失败。

    使用示例:
    - new_type = copy_memory_type_with_template_name(old_type, "T1")

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    memory_type.verify()
    result = NnMemoryType(
        memory_type.shape if shape is None else shape,
        memory_type.stride if stride is None else stride,
        memory_type.element_type if element_type is None else element_type,
        memory_type.space if space is None else space,
        template_name=template_name,
    )
    result.verify()
    return result

__all__ = ["NnMemoryType", "copy_memory_type", "copy_memory_type_with_template_name"]
