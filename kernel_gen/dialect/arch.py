"""Arch dialect definitions.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 定义 arch dialect 的执行维度查询、动态片上内存入口与 kernel 启动描述 op。
- 复用 symbol dialect 的 `!symbol.int<"expr">` 与 nn dialect 的 `nn.memory/#nn.space`。

使用示例:
- from kernel_gen.dialect.arch import Arch, ArchGetBlockIdOp, ArchLaunchKernelOp

关联文件:
- spec: spec/dialect/arch.md
- test: test/dialect/test_arch_dialect.py
- 功能实现: kernel_gen/dialect/arch.py
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import ClassVar

from xdsl.dialects.builtin import ArrayAttr, IntAttr, StringAttr, i8
from xdsl.ir import Attribute, Dialect, Operation, SSAValue
from xdsl.irdl import IRDLOperation, attr_def, irdl_op_definition, operand_def, result_def
from xdsl.parser import AttrParser
from xdsl.printer import Printer
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType

_DYNAMIC_MEMORY_SPACES = {"shared", "local", "tsm", "tlm"}


def _verify_symbol_int_operand(value: SSAValue, field_name: str, op_name: str) -> SymbolValueType:
    """校验单个启动维度 operand 为 `!symbol.int<\"expr\">`。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 统一校验 `arch.launch_kernel` 的维度输入类型。

    使用示例:
    - _verify_symbol_int_operand(op.block, "block", "arch.launch_kernel")

    关联文件:
    - spec: spec/dialect/arch.md
    - test: test/dialect/test_arch_dialect.py
    - 功能实现: kernel_gen/dialect/arch.py
    """

    if not isinstance(value.type, SymbolValueType):
        raise VerifyException(f"{op_name} {field_name} must have type !symbol.int<\"expr\">")
    value.type.verify()
    return value.type


def _verify_positive_static_symbol(operand_type: SymbolValueType, field_name: str, op_name: str) -> None:
    """校验可静态求值的 symbol.int 启动维度为正整数。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 对字面量整数表达式执行 `> 0` 约束。
    - 对无法静态求值的符号表达式保持放行。

    使用示例:
    - _verify_positive_static_symbol(SymbolValueType.from_expr("8"), "block", "arch.launch_kernel")

    关联文件:
    - spec: spec/dialect/arch.md
    - test: test/dialect/test_arch_dialect.py
    - 功能实现: kernel_gen/dialect/arch.py
    """

    static_value = operand_type.get_value()
    if isinstance(static_value, int) and static_value <= 0:
        raise VerifyException(f"{op_name} {field_name} must be > 0 when statically known")


def _dynamic_memory_result_type(space: NnMemorySpaceAttr) -> NnMemoryType:
    """构造动态 memory 入口的固定结果类型。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 返回 `!nn.memory<[?], [1], i8, #nn.space<space>>`。

    使用示例:
    - _dynamic_memory_result_type(NnMemorySpaceAttr.from_name("shared"))

    关联文件:
    - spec: spec/dialect/arch.md
    - test: test/dialect/test_arch_dialect.py
    - 功能实现: kernel_gen/dialect/arch.py
    """

    return NnMemoryType(
        ArrayAttr([StringAttr("?")]),
        ArrayAttr([IntAttr(1)]),
        i8,
        space,
    )


class _BaseArchIndexQueryOp(IRDLOperation):
    """固定返回指定 symbol.int 类型的 arch 查询 op 基类。"""

    result = result_def(SymbolValueType)

    RESULT_EXPR: ClassVar[str]

    def __init__(
        self: "_BaseArchIndexQueryOp",
        result_type: Attribute | None = None,
    ) -> None:
        """初始化固定结果类型的 arch 查询 op。

        创建者: 朽木露琪亚
        最后一次更改: 朽木露琪亚

        功能说明:
        - 支持默认构造固定结果类型，也支持 parser 注入显式结果类型后由 verifier 校验。

        使用示例:
        - ArchGetBlockIdOp()

        关联文件:
        - spec: spec/dialect/arch.md
        - test: test/dialect/test_arch_dialect.py
        - 功能实现: kernel_gen/dialect/arch.py
        """

        super().__init__(result_types=[result_type or SymbolValueType.from_expr(self.RESULT_EXPR)])

    def verify_(self: "_BaseArchIndexQueryOp") -> None:
        """校验固定结果类型查询 op。"""

        expected = SymbolValueType.from_expr(self.RESULT_EXPR)
        if self.result.type != expected:
            raise VerifyException(f"{self.name} result type must be !symbol.int<\"{self.RESULT_EXPR}\">")

    def print(self: "_BaseArchIndexQueryOp", printer: Printer) -> None:
        """打印固定结果类型查询 op 自定义文本语法。"""

        printer.print_string(" : ")
        printer.print_attribute(self.result.type)

    @classmethod
    def parse(cls: type["_BaseArchIndexQueryOp"], parser: AttrParser) -> "_BaseArchIndexQueryOp":
        """解析固定结果类型查询 op 自定义文本语法。"""

        parser.parse_characters(":", f" in {cls.name}")
        return cls(parser.parse_type())


@irdl_op_definition
class ArchGetBlockIdOp(_BaseArchIndexQueryOp):
    """返回当前 block 的执行索引。"""

    name = "arch.get_block_id"
    RESULT_EXPR: ClassVar[str] = "block_id"


@irdl_op_definition
class ArchGetBlockNumOp(_BaseArchIndexQueryOp):
    """返回当前 launch 的 block 数量。"""

    name = "arch.get_block_num"
    RESULT_EXPR: ClassVar[str] = "block_num"


@irdl_op_definition
class ArchGetThreadIdOp(_BaseArchIndexQueryOp):
    """返回当前 block 内 thread 执行索引。"""

    name = "arch.get_thread_id"
    RESULT_EXPR: ClassVar[str] = "thread_id"


@irdl_op_definition
class ArchGetThreadNumOp(_BaseArchIndexQueryOp):
    """返回当前 block 内 thread 数量。"""

    name = "arch.get_thread_num"
    RESULT_EXPR: ClassVar[str] = "thread_num"


@irdl_op_definition
class ArchGetSubthreadIdOp(_BaseArchIndexQueryOp):
    """返回当前 thread 内 subthread 执行索引。"""

    name = "arch.get_subthread_id"
    RESULT_EXPR: ClassVar[str] = "subthread_id"


@irdl_op_definition
class ArchGetSubthreadNumOp(_BaseArchIndexQueryOp):
    """返回当前 thread 内 subthread 数量。"""

    name = "arch.get_subthread_num"
    RESULT_EXPR: ClassVar[str] = "subthread_num"


@irdl_op_definition
class ArchGetDynamicMemoryOp(IRDLOperation):
    """获取指定片上 memory space 的动态字节缓冲入口。"""

    name = "arch.get_dynamic_memory"

    memory_space = attr_def(NnMemorySpaceAttr)
    result = result_def(NnMemoryType)

    def __init__(
        self: "ArchGetDynamicMemoryOp",
        memory_space: NnMemorySpaceAttr,
        result_type: Attribute | None = None,
    ) -> None:
        """初始化 arch.get_dynamic_memory。

        创建者: 朽木露琪亚
        最后一次更改: 朽木露琪亚

        功能说明:
        - 记录 memory space，并默认推导固定结果类型。

        使用示例:
        - ArchGetDynamicMemoryOp(NnMemorySpaceAttr.from_name("shared"))

        关联文件:
        - spec: spec/dialect/arch.md
        - test: test/dialect/test_arch_dialect.py
        - 功能实现: kernel_gen/dialect/arch.py
        """

        super().__init__(
            result_types=[result_type or _dynamic_memory_result_type(memory_space)],
            attributes={"memory_space": memory_space},
        )

    def verify_(self: "ArchGetDynamicMemoryOp") -> None:
        """校验动态 memory 入口 op。"""

        self.memory_space.verify()
        space_name = self.memory_space.space.data
        if space_name not in _DYNAMIC_MEMORY_SPACES:
            raise VerifyException("arch.get_dynamic_memory memory_space must be shared/local/tsm/tlm")

        if not isinstance(self.result.type, NnMemoryType):
            raise VerifyException("arch.get_dynamic_memory result type must be nn.memory")

        result_type = self.result.type
        result_type.verify()

        if len(result_type.shape.data) != 1:
            raise VerifyException("arch.get_dynamic_memory result must be 1-D")
        if len(result_type.stride.data) != 1:
            raise VerifyException("arch.get_dynamic_memory result stride rank must be 1")
        if result_type.shape.data[0] != StringAttr("?"):
            raise VerifyException("arch.get_dynamic_memory result shape must be [?]")
        if result_type.stride.data[0] != IntAttr(1):
            raise VerifyException("arch.get_dynamic_memory result stride must be [1]")
        if result_type.element_type != i8:
            raise VerifyException("arch.get_dynamic_memory result element type must be i8")
        if result_type.space != self.memory_space:
            raise VerifyException("arch.get_dynamic_memory result space must match memory_space")

    def print(self: "ArchGetDynamicMemoryOp", printer: Printer) -> None:
        """打印 arch.get_dynamic_memory 自定义文本语法。"""

        printer.print_string(" ")
        printer.print_attribute(self.memory_space)
        printer.print_string(" : ")
        printer.print_attribute(self.result.type)

    @classmethod
    def parse(cls: type["ArchGetDynamicMemoryOp"], parser: AttrParser) -> "ArchGetDynamicMemoryOp":
        """解析 arch.get_dynamic_memory 自定义文本语法。"""

        memory_space = parser.parse_attribute()
        if not isinstance(memory_space, NnMemorySpaceAttr):
            raise VerifyException("arch.get_dynamic_memory memory_space must be #nn.space<...>")
        parser.parse_characters(":", f" in {cls.name}")
        return cls(memory_space, parser.parse_type())


@irdl_op_definition
class ArchLaunchKernelOp(IRDLOperation):
    """描述一次三层执行维度的 kernel 启动请求。"""

    name = "arch.launch_kernel"

    block = operand_def(Attribute)
    thread = operand_def(Attribute)
    subthread = operand_def(Attribute)
    kernel_name = attr_def(StringAttr)

    def __init__(
        self: "ArchLaunchKernelOp",
        kernel_name: str | StringAttr,
        block: SSAValue | Operation,
        thread: SSAValue | Operation,
        subthread: SSAValue | Operation,
    ) -> None:
        """初始化 arch.launch_kernel。

        创建者: 朽木露琪亚
        最后一次更改: 朽木露琪亚

        功能说明:
        - 记录 kernel 名称与 block/thread/subthread 三层启动维度。

        使用示例:
        - ArchLaunchKernelOp("my_kernel", block, thread, subthread)

        关联文件:
        - spec: spec/dialect/arch.md
        - test: test/dialect/test_arch_dialect.py
        - 功能实现: kernel_gen/dialect/arch.py
        """

        name_attr = kernel_name if isinstance(kernel_name, StringAttr) else StringAttr(kernel_name)
        super().__init__(
            operands=[block, thread, subthread],
            attributes={"kernel_name": name_attr},
        )

    def verify_(self: "ArchLaunchKernelOp") -> None:
        """校验 arch.launch_kernel 输入约束。"""

        if not self.kernel_name.data:
            raise VerifyException("arch.launch_kernel kernel name must not be empty")

        for field_name in ("block", "thread", "subthread"):
            operand_value = SSAValue.get(getattr(self, field_name))
            operand_type = _verify_symbol_int_operand(operand_value, field_name, self.name)
            _verify_positive_static_symbol(operand_type, field_name, self.name)

    def print(self: "ArchLaunchKernelOp", printer: Printer) -> None:
        """打印 arch.launch_kernel 自定义文本语法。"""

        printer.print_string(" ")
        printer.print_string_literal(self.kernel_name.data)
        printer.print_string(", ")
        printer.print_ssa_value(self.block)
        printer.print_string(", ")
        printer.print_ssa_value(self.thread)
        printer.print_string(", ")
        printer.print_ssa_value(self.subthread)
        printer.print_string(" : ")
        printer.print_attribute(SSAValue.get(self.block).type)
        printer.print_string(", ")
        printer.print_attribute(SSAValue.get(self.thread).type)
        printer.print_string(", ")
        printer.print_attribute(SSAValue.get(self.subthread).type)

    @classmethod
    def parse(cls: type["ArchLaunchKernelOp"], parser: AttrParser) -> "ArchLaunchKernelOp":
        """解析 arch.launch_kernel 自定义文本语法。"""

        kernel_name = parser.parse_str_literal("Expected launch kernel name.")
        parser.parse_characters(",", f" in {cls.name}")
        unresolved_block = parser.parse_unresolved_operand()
        parser.parse_characters(",", f" in {cls.name}")
        unresolved_thread = parser.parse_unresolved_operand()
        parser.parse_characters(",", f" in {cls.name}")
        unresolved_subthread = parser.parse_unresolved_operand()
        parser.parse_characters(":", f" in {cls.name}")
        block_type = parser.parse_type()
        parser.parse_characters(",", f" in {cls.name} type list")
        thread_type = parser.parse_type()
        parser.parse_characters(",", f" in {cls.name} type list")
        subthread_type = parser.parse_type()
        block = parser.resolve_operand(unresolved_block, block_type)
        thread = parser.resolve_operand(unresolved_thread, thread_type)
        subthread = parser.resolve_operand(unresolved_subthread, subthread_type)
        return cls(kernel_name, block, thread, subthread)


Arch = Dialect(
    "arch",
    [
        ArchGetBlockIdOp,
        ArchGetBlockNumOp,
        ArchGetThreadIdOp,
        ArchGetThreadNumOp,
        ArchGetSubthreadIdOp,
        ArchGetSubthreadNumOp,
        ArchGetDynamicMemoryOp,
        ArchLaunchKernelOp,
    ],
    [],
)

__all__ = [
    "Arch",
    "ArchGetBlockIdOp",
    "ArchGetBlockNumOp",
    "ArchGetThreadIdOp",
    "ArchGetThreadNumOp",
    "ArchGetSubthreadIdOp",
    "ArchGetSubthreadNumOp",
    "ArchGetDynamicMemoryOp",
    "ArchLaunchKernelOp",
]
