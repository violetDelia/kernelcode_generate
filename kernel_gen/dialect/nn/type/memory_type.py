"""nn memory type.

功能说明:
- 承载 nn dialect package 拆分后的 nn memory type 实现。

API 列表:
- `class NnMemoryType(shape: ArrayAttr[SymbolExprAttr], stride: ArrayAttr[SymbolExprAttr], element_type: Attribute, space: NnMemorySpaceAttr, template_name: StringAttr | str | None = None, *, external_attrs: DictionaryAttr | dict[str, Attribute] | None = None)`
- `NnMemoryType.external_attrs -> DictionaryAttr`
- `NnMemoryType.template_name -> StringAttr`
- `copy_memory_type(memory_type: NnMemoryType, *, shape: ArrayAttr[SymbolExprAttr] | None = None, stride: ArrayAttr[SymbolExprAttr] | None = None, element_type: Attribute | None = None, space: NnMemorySpaceAttr | None = None) -> NnMemoryType`
- `copy_memory_type_with_template_name(memory_type: NnMemoryType, template_name: str | StringAttr, *, shape: ArrayAttr[SymbolExprAttr] | None = None, stride: ArrayAttr[SymbolExprAttr] | None = None, element_type: Attribute | None = None, space: NnMemorySpaceAttr | None = None) -> NnMemoryType`
- `copy_memory_type_with_external_attr(memory_type: NnMemoryType, key: str, value: Attribute) -> NnMemoryType`

使用示例:
- from kernel_gen.dialect.nn import NnMemoryType

关联文件:
- spec: spec/dialect/nn.md
- test: test/dialect/nn/test_type.py
- 功能实现: kernel_gen/dialect/nn/type/memory_type.py
"""

from __future__ import annotations

from collections.abc import Sequence
import re

from kernel_gen.dialect.nn.attr.space_attr import NnMemorySpaceAttr
from xdsl.dialects.builtin import ArrayAttr, DictionaryAttr, StringAttr
from xdsl.ir import Attribute, ParametrizedAttribute, TypeAttribute
from xdsl.irdl import irdl_attr_definition, param_def
from xdsl.parser import AttrParser
from xdsl.printer import Printer
from xdsl.utils.exceptions import ParseError

from kernel_gen.core.contracts import raise_verify_error as core_raise_verify_error

# Localized helpers from retired package-internal modules.

_ERROR_SCENE = "dialect.nn verifier"


_TEMPLATE_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_EXTERNAL_ATTR_KEY_PATTERN = _TEMPLATE_NAME_PATTERN
_TEMPLATE_NAME_KEY = "template_name"

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

    @staticmethod
    def verify_external_attr_key(key: str) -> None:
        """校验 external_attrs key。

        功能说明:
        - external attr key 必须是稳定 identifier。
        - `template_name` 作为保留 key 由专门规则继续校验 value 类型和值。

        使用示例:
        - _NN_MEMORY_TYPE.verify_external_attr_key("template_name")
        """

        if _EXTERNAL_ATTR_KEY_PATTERN.fullmatch(key) is None:
            core_raise_verify_error(_ERROR_SCENE, "nn memory external_attrs key must be an identifier")

    @staticmethod
    def dictionary_from_external_attrs(external_attrs: DictionaryAttr | dict[str, Attribute] | None) -> DictionaryAttr:
        """规整 external_attrs 输入。

        功能说明:
        - `None` 规整为空 `DictionaryAttr`。
        - Python dict 与 `DictionaryAttr` 是公开输入形态，key 按字典序 canonicalize。

        使用示例:
        - attrs = _NN_MEMORY_TYPE.dictionary_from_external_attrs({"template_name": StringAttr("T1")})
        """

        if external_attrs is None:
            raw_items: dict[str, Attribute] = {}
        elif isinstance(external_attrs, DictionaryAttr):
            raw_items = dict(external_attrs.data)
        elif isinstance(external_attrs, dict):
            raw_items = dict(external_attrs)
        else:
            raise TypeError("external_attrs must be DictionaryAttr, dict[str, Attribute] or None")
        normalized: dict[str, Attribute] = {}
        for key, value in raw_items.items():
            _NN_MEMORY_TYPE.verify_external_attr_key(key)
            if key == _TEMPLATE_NAME_KEY:
                if not isinstance(value, StringAttr):
                    core_raise_verify_error(_ERROR_SCENE, "nn memory external_attrs template_name must be StringAttr")
                _NN_MEMORY_TYPE.verify_template_name_text(value.data)
                if value.data == "":
                    continue
            normalized[key] = value
        return DictionaryAttr({key: normalized[key] for key in sorted(normalized)})

    @staticmethod
    def merge_template_name_into_external_attrs(
        template_name: StringAttr | str | None,
        external_attrs: DictionaryAttr | dict[str, Attribute] | None,
    ) -> DictionaryAttr:
        """把旧 template_name 参数并入 external_attrs。

        功能说明:
        - 保留旧 Python `template_name=` 构造兼容。
        - `template_name` 与 `external_attrs["template_name"]` 同值时合并，异值时稳定失败。

        使用示例:
        - attrs = _NN_MEMORY_TYPE.merge_template_name_into_external_attrs("T1", None)
        """

        attrs = dict(_NN_MEMORY_TYPE.dictionary_from_external_attrs(external_attrs).data)
        normalized_template = _normalize_template_name_attr(template_name)
        if normalized_template.data == "":
            return DictionaryAttr({key: attrs[key] for key in sorted(attrs)})
        existing = attrs.get(_TEMPLATE_NAME_KEY)
        if existing is not None:
            if not isinstance(existing, StringAttr):
                core_raise_verify_error(_ERROR_SCENE, "nn memory external_attrs template_name must be StringAttr")
            if existing.data != normalized_template.data:
                core_raise_verify_error(_ERROR_SCENE, "nn memory external_attrs template_name conflicts with template_name")
        attrs[_TEMPLATE_NAME_KEY] = normalized_template
        return DictionaryAttr({key: attrs[key] for key in sorted(attrs)})

    @staticmethod
    def external_attrs_without_template_name(external_attrs: DictionaryAttr) -> DictionaryAttr:
        """删除 external_attrs 中的 template_name。

        功能说明:
        - `copy_memory_type(...)` 用该规则清除模板注解。
        - 其它 external attrs 保持不变，避免丢失真实 memory 合同属性。

        使用示例:
        - attrs = _NN_MEMORY_TYPE.external_attrs_without_template_name(memory_type.external_attrs)
        """

        attrs = {key: value for key, value in external_attrs.data.items() if key != _TEMPLATE_NAME_KEY}
        return DictionaryAttr({key: attrs[key] for key in sorted(attrs)})

    @staticmethod
    def external_attrs_with_attr(external_attrs: DictionaryAttr, key: str, value: Attribute) -> DictionaryAttr:
        """返回写入单个 external attr 后的新容器。

        功能说明:
        - clone helper 通过该方法实现单 key 覆盖。
        - `template_name` key 仍按保留 key 的类型和值规则校验。

        使用示例:
        - attrs = _NN_MEMORY_TYPE.external_attrs_with_attr(memory_type.external_attrs, "layout", StringAttr("x"))
        """

        _NN_MEMORY_TYPE.verify_external_attr_key(key)
        attrs = dict(external_attrs.data)
        attrs[key] = value
        return _NN_MEMORY_TYPE.dictionary_from_external_attrs(attrs)

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
    - 建模 `shape`、`stride`、`element_type`、`space` 与通用 `external_attrs`。
    - `template_name` 作为 `external_attrs["template_name"]` 的兼容 property 暴露。

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
    external_attrs: DictionaryAttr = param_def(DictionaryAttr)

    def __init__(
        self,
        shape: ArrayAttr[SymbolExprAttr],
        stride: ArrayAttr[SymbolExprAttr],
        element_type: Attribute,
        space: NnMemorySpaceAttr,
        template_name: StringAttr | str | None = None,
        *,
        external_attrs: DictionaryAttr | dict[str, Attribute] | None = None,
    ) -> None:
        """初始化 memory type。

        功能说明:
        - 保留四参数构造兼容，默认不携带 template name。
        - 旧 `template_name` 参数会 canonicalize 到 `external_attrs["template_name"]`。
        - `external_attrs` 承载除 template-name 之外的通用 memory 合同属性。

        使用示例:
        - NnMemoryType(shape, stride, i32, NnMemorySpaceAttr.from_name("global"), template_name="T1")
        """

        super().__init__(
            shape,
            stride,
            element_type,
            space,
            _NN_MEMORY_TYPE.merge_template_name_into_external_attrs(template_name, external_attrs),
        )

    @property
    def template_name(self) -> StringAttr:
        """读取兼容 template name。

        功能说明:
        - 从 `external_attrs["template_name"]` 读取 template 名称。
        - 未携带 template name 时返回空 `StringAttr("")`，保持旧调用方 `.template_name.data` 行为。

        使用示例:
        - name = memory_type.template_name.data
        """

        value = self.external_attrs.data.get(_TEMPLATE_NAME_KEY)
        if value is None:
            return StringAttr("")
        if not isinstance(value, StringAttr):
            core_raise_verify_error(_ERROR_SCENE, "nn memory external_attrs template_name must be StringAttr")
        return value

    @classmethod
    def parse_parameters(cls, parser: AttrParser) -> Sequence[Attribute]:
        """解析 memory type 参数。

        功能说明:
        - 解析 `!nn.memory<[#symbol.expr<N>], [#symbol.expr<1>], i32, #nn.space<global>, external_attrs = {template_name = "T1"}>`。
        - 兼容 legacy `template = T1` 输入并转换为 `external_attrs["template_name"]`。
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
        external_attrs: DictionaryAttr | None = None
        while parser.parse_optional_punctuation(",") is not None:
            keyword = parser.parse_identifier("Expected nn memory option.")
            parser.parse_punctuation("=", "Expected '=' after nn memory option.")
            if keyword == "template":
                template_name = StringAttr(parser.parse_identifier("Expected nn memory template name."))
                continue
            if keyword == "external_attrs":
                try:
                    parsed_attrs = parser.parse_optional_dictionary_attr_dict()
                except ParseError:
                    parser.raise_error("nn memory external_attrs keys must be unique")
                if parsed_attrs is None:
                    parser.raise_error("Expected nn memory external_attrs dictionary.")
                if external_attrs is not None:
                    parser.raise_error("nn memory external_attrs keys must be unique")
                external_attrs = DictionaryAttr(parsed_attrs)
                continue
            parser.raise_error("nn memory type only accepts template or external_attrs option")
        parser.parse_punctuation(">", "Expected '>' for nn memory type.")
        if not isinstance(shape, ArrayAttr):
            parser.raise_error("nn memory shape must be ArrayAttr[SymbolExprAttr]")
        if not isinstance(stride, ArrayAttr):
            parser.raise_error("nn memory stride must be ArrayAttr[SymbolExprAttr]")
        if not isinstance(space, NnMemorySpaceAttr):
            parser.raise_error("nn memory type space must be #nn.space<...>")
        return (
            shape,
            stride,
            element_type,
            space,
            _NN_MEMORY_TYPE.merge_template_name_into_external_attrs(template_name, external_attrs),
        )

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
        if self.external_attrs.data:
            printer.print_string(", external_attrs = {")
            for index, key in enumerate(sorted(self.external_attrs.data)):
                if index:
                    printer.print_string(", ")
                printer.print_string(key)
                printer.print_string(" = ")
                printer.print_attribute(self.external_attrs.data[key])
            printer.print_string("}")
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
        _NN_MEMORY_TYPE.dictionary_from_external_attrs(self.external_attrs)

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
        external_attrs=_NN_MEMORY_TYPE.external_attrs_without_template_name(memory_type.external_attrs),
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
        external_attrs=_NN_MEMORY_TYPE.external_attrs_with_attr(
            memory_type.external_attrs,
            _TEMPLATE_NAME_KEY,
            _normalize_template_name_attr(template_name),
        ),
    )
    result.verify()
    return result

def copy_memory_type_with_external_attr(memory_type: NnMemoryType, key: str, value: Attribute) -> NnMemoryType:
    """复制 memory type 并写入单个 external attr。

    功能说明:
    - clone 原 memory type 并覆盖指定 `external_attrs` key。
    - 不原地修改原对象；shape/stride/element_type/space 均保持不变。

    使用示例:
    - new_type = copy_memory_type_with_external_attr(old_type, "sdnn_layout", StringAttr("mac_banked"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    memory_type.verify()
    result = NnMemoryType(
        memory_type.shape,
        memory_type.stride,
        memory_type.element_type,
        memory_type.space,
        external_attrs=_NN_MEMORY_TYPE.external_attrs_with_attr(memory_type.external_attrs, key, value),
    )
    result.verify()
    return result

__all__ = [
    "NnMemoryType",
    "copy_memory_type",
    "copy_memory_type_with_template_name",
    "copy_memory_type_with_external_attr",
]
