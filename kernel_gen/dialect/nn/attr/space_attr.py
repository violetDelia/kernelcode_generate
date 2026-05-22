"""nn memory space attribute.

功能说明:
- 承载 nn dialect package 拆分后的 nn memory space attribute 实现。

API 列表:
- `class NnMemorySpaceAttr(space: StringAttr)`

使用示例:
- from kernel_gen.dialect.nn import NnMemorySpaceAttr

关联文件:
- spec: spec/dialect/nn.md
- test: test/dialect/nn/test_attr.py
- 功能实现: kernel_gen/dialect/nn/attr/space_attr.py
"""

from __future__ import annotations

from kernel_gen.dialect.nn.common import raise_verify_error
from xdsl.dialects.builtin import StringAttr
from xdsl.irdl import irdl_attr_definition, param_def
from xdsl.ir import ParametrizedAttribute
from xdsl.parser import AttrParser
from xdsl.printer import Printer

_VALID_SPACES = {"global", "shared", "local", "tsm", "tlm1", "tlm2", "tlm3"}

@irdl_attr_definition
class NnMemorySpaceAttr(ParametrizedAttribute):
    """NN memory space attribute。


    功能说明:
    - 显式建模 `global`、`shared`、`local`、`tsm`、`tlm1`、`tlm2`、`tlm3` 七种 memory space。

    使用示例:
    - NnMemorySpaceAttr(StringAttr(\"global\"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    name = "nn.space"

    space: StringAttr = param_def(StringAttr)

    @classmethod
    def parse_parameters(cls, parser: AttrParser) -> Sequence[Attribute]:
        """解析 space attribute 参数。

        功能说明:
        - 解析 `#nn.space<...>` 尖括号内的 memory space 文本。
        - 只负责构造参数 tuple，space 名称合法性由 `verify()` 统一校验。

        使用示例:
        - NnMemorySpaceAttr.parse_parameters(parser)
        """

        parser.parse_punctuation("<", "Expected '<' for nn space attribute.")
        space = StringAttr(parser.parse_identifier("Expected nn memory space identifier."))
        parser.parse_punctuation(">", "Expected '>' for nn space attribute.")
        return (space,)

    def print_parameters(self, printer: Printer) -> None:
        """打印 space attribute 参数。

        功能说明:
        - 按 `#nn.space<...>` 的参数格式输出当前 memory space 名称。
        - 不修改属性内容，也不在打印阶段重复执行 verifier。

        使用示例:
        - NnMemorySpaceAttr.from_name("global").print_parameters(printer)
        """

        printer.print_string("<")
        printer.print_string(self.space.data)
        printer.print_string(">")

    def verify(self) -> None:
        """校验 space attribute。

        功能说明:
        - 校验 memory space 名称属于 nn dialect 支持的固定集合。
        - 非法名称使用统一 nn verifier 错误模板抛出。

        使用示例:
        - NnMemorySpaceAttr.from_name("global").verify()
        """

        if self.space.data not in _VALID_SPACES:
            raise_verify_error("nn space must be one of global/shared/local/tsm/tlm1/tlm2/tlm3")

    @classmethod
    def from_name(cls, space: str) -> "NnMemorySpaceAttr":
        """从字符串构造 space attribute。


        功能说明:
        - 简化 `global/shared/local/tsm/tlm1/tlm2/tlm3` 的构造。

        使用示例:
        - NnMemorySpaceAttr.from_name(\"global\")

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        return cls(StringAttr(space))

__all__ = ["NnMemorySpaceAttr"]
