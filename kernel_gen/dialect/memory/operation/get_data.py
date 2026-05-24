"""memory get_data operation.

功能说明:
- 定义 memory.get_data op。

API 列表:
- `class MemoryGetDataOp(source: SSAValue | Operation, result_type: Attribute | None = None)`

使用示例:
- `from kernel_gen.dialect.memory.operation import ...`

关联文件:
- spec: spec/dialect/memory.md
- test: test/dialect/memory/
- 功能实现: kernel_gen/dialect/memory/operation/get_data.py
"""

from __future__ import annotations

from kernel_gen.core.error import ErrorKind, ErrorModule, kernel_code_error
from xdsl.ir import Attribute, Dialect, Operation, SSAValue
from xdsl.irdl import IRDLOperation, irdl_op_definition, operand_def, result_def, traits_def
from xdsl.parser import AttrParser
from xdsl.printer import Printer
from xdsl.traits import Pure

from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolPtrType


def _infer_memory_get_data_result_type(source: SSAValue | Operation) -> SymbolPtrType:
    """推导 memory.get_data 结果类型。

    功能说明:
    - 从 `NnMemoryType` 读取 element dtype 与 template name。
    - 非 memory source 在构造阶段直接失败，避免生成不可验证 op。

    使用示例:
    - result_type = _infer_memory_get_data_result_type(memory_value)
    """

    source_type = SSAValue.get(source).type
    if not isinstance(source_type, NnMemoryType):
        raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT, "memory.get_data source must be !nn.memory")
    source_type.verify()
    return SymbolPtrType(source_type.element_type, source_type.template_name)

@irdl_op_definition
class MemoryGetDataOp(IRDLOperation):
    """获取 memory backing data 指针。"""

    name = "memory.get_data"
    traits = traits_def(Pure())

    source = operand_def(Attribute)
    result = result_def(Attribute)

    def __init__(
        self: "MemoryGetDataOp",
        source: SSAValue | Operation,
        result_type: Attribute | None = None,
    ) -> None:
        """初始化 memory.get_data。

        功能说明:
        - 设置一个 `!nn.memory` source 与一个 `!symbol.ptr` result。
        - 未传 result_type 时从 source memory type 推导 element dtype 与 template name。

        使用示例:
        - MemoryGetDataOp(memory_value)
        """

        super().__init__(operands=[source], result_types=[result_type or _infer_memory_get_data_result_type(source)])

    def verify_(self: "MemoryGetDataOp") -> None:
        """校验 memory.get_data source/result 合同。

        功能说明:
        - source 必须是 `NnMemoryType`。
        - result 必须是 `SymbolPtrType`，且 dtype/template 与 source memory 一致。

        使用示例:
        - MemoryGetDataOp(memory_value).verify_()
        """

        source_type = SSAValue.get(self.source).type
        if not isinstance(source_type, NnMemoryType):
            raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT, "memory.get_data source must be !nn.memory")
        source_type.verify()
        result_type = self.result.type
        if not isinstance(result_type, SymbolPtrType):
            raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT, "memory.get_data result type must be !symbol.ptr")
        if result_type.dtype != source_type.element_type:
            raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT, "memory.get_data ptr dtype must match memory element_type")
        if result_type.template_name.data != source_type.template_name.data:
            raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT, "memory.get_data ptr template_name must match memory template_name")

    def print(self: "MemoryGetDataOp", printer: Printer) -> None:
        """打印 memory.get_data 自定义文本语法。

        功能说明:
        - 输出 `%ptr = memory.get_data %mem : <memory-type> -> <ptr-type>`。

        使用示例:
        - printer.print_op(op)
        """

        printer.print_string(" ")
        printer.print_ssa_value(self.source)
        printer.print_string(" : ")
        printer.print_attribute(SSAValue.get(self.source).type)
        printer.print_string(" -> ")
        printer.print_attribute(self.result.type)

    @classmethod
    def parse(cls: type["MemoryGetDataOp"], parser: AttrParser) -> "MemoryGetDataOp":
        """解析 memory.get_data 自定义文本语法。

        功能说明:
        - 解析 source operand、source type 与 result ptr type。

        使用示例:
        - Parser(ctx, "%0 = memory.get_data %arg : ...").parse_module()
        """

        unresolved_source = parser.parse_unresolved_operand()
        parser.parse_characters(":", f" in {cls.name}")
        source_type = parser.parse_type()
        parser.parse_characters("->", f" in {cls.name}")
        result_type = parser.parse_type()
        if not isinstance(result_type, SymbolPtrType):
            parser.raise_error("memory.get_data result type must be !symbol.ptr<...>")
        source = parser.resolve_operand(unresolved_source, source_type)
        return cls(source, result_type)

__all__ = ["MemoryGetDataOp", "_infer_memory_get_data_result_type"]
