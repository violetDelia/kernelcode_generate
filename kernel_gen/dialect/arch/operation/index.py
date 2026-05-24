"""arch index query operations.

功能说明:
- 定义 block/thread/subthread id/num query op。

API 列表:
- `class ArchGetBlockIdOp(result_type: Attribute | None = None)`
- `class ArchGetBlockNumOp(result_type: Attribute | None = None)`
- `class ArchGetThreadIdOp(result_type: Attribute | None = None)`
- `class ArchGetThreadNumOp(result_type: Attribute | None = None)`
- `class ArchGetSubthreadIdOp(result_type: Attribute | None = None)`
- `class ArchGetSubthreadNumOp(result_type: Attribute | None = None)`

使用示例:
- `from kernel_gen.dialect.arch.operation import ...`

关联文件:
- spec: spec/dialect/arch.md
- test: test/dialect/arch/
- 功能实现: kernel_gen/dialect/arch/operation/index.py
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import ClassVar

from kernel_gen.core.error import ERROR_ACTION, ERROR_ACTUAL, ERROR_TEMPLATE, ErrorKind, ErrorModule, kernel_code_error
from xdsl.dialects.builtin import ArrayAttr, IntAttr, StringAttr, SymbolRefAttr, i8
from xdsl.ir import Attribute, Dialect, Operation, ParametrizedAttribute, SSAValue, TypeAttribute
from xdsl.irdl import (
    AttrSizedOperandSegments,
    IRDLOperation,
    attr_def,
    irdl_attr_definition,
    irdl_op_definition,
    operand_def,
    param_def,
    result_def,
    var_operand_def,
)
from xdsl.parser import AttrParser
from xdsl.printer import Printer

from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolExprAttr, SymbolValueType
from kernel_gen.target import registry

from kernel_gen.target import registry as target_registry

# Localized helpers from retired package-internal modules.

_ERROR_SCENE = "dialect.arch verifier"

def _verify_target_registry_support(op_name: str) -> None:
    """按当前 target registry 配置校验 arch op 支持性。


    功能说明:
    - 在启用 target registry 校验时，检查 arch op 是否被当前 target 支持。

    使用示例:
    - _verify_target_registry_support("arch.get_thread_id")

    关联文件:
    - spec: spec/target/registry.md
    - test: test/dialect/arch/test_arch.py
    - 功能实现: kernel_gen/dialect/arch/
    """

    current_target = target_registry.get_current_target()
    if current_target is None:
        return
    try:
        if not target_registry.is_arch_op_supported(current_target, op_name):
            raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected=f"{op_name} is not supported by target {current_target}",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
    except ValueError as exc:
        raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
            ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected=str(exc),
                actual=ERROR_ACTUAL,
                action=ERROR_ACTION,
            )
        ) from exc



_ERROR_SCENE = "dialect.arch verifier"

class _BaseArchIndexQueryOp(IRDLOperation):
    """固定返回指定 symbol.int 类型的 arch 查询 op 基类。"""

    result = result_def(SymbolValueType)

    RESULT_EXPR: ClassVar[str]

    def __init__(
        self: "_BaseArchIndexQueryOp",
        result_type: Attribute | None = None,
    ) -> None:
        """初始化固定结果类型的 arch 查询 op。


        功能说明:
        - 支持默认构造固定结果类型，也支持 parser 注入显式结果类型后由 verifier 校验。

        使用示例:
        - ArchGetBlockIdOp()

        关联文件:
        - spec: spec/dialect/arch.md
        - test: test/dialect/arch/test_arch.py
        - 功能实现: kernel_gen/dialect/arch/
        """

        super().__init__(result_types=[result_type or SymbolValueType.from_expr(self.RESULT_EXPR)])

    def verify_(self: "_BaseArchIndexQueryOp") -> None:
        """校验固定结果类型查询 op。


        功能说明:
        - 校验固定结果类型并在启用 target registry 时执行支持性检查。

        使用示例:
        - ArchGetBlockIdOp().verify()

        关联文件:
        - spec: spec/dialect/arch.md
        - test: test/dialect/arch/test_arch.py
        - 功能实现: kernel_gen/dialect/arch/
        """

        expected = SymbolValueType.from_expr(self.RESULT_EXPR)
        if self.result.type != expected:
            raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected=f"{self.name} result type must be !symbol.int<#symbol.expr<{self.RESULT_EXPR}>>",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        _verify_target_registry_support(self.name)

    def print(self: "_BaseArchIndexQueryOp", printer: Printer) -> None:
        """打印固定结果类型查询 op 自定义文本语法。

        功能说明:
        - 输出 `arch.get_*` 查询 op 的显式结果类型。

        使用示例:
        - ArchGetBlockIdOp().print(printer)
        """

        printer.print_string(" : ")
        printer.print_attribute(self.result.type)

    @classmethod
    def parse(cls: type["_BaseArchIndexQueryOp"], parser: AttrParser) -> "_BaseArchIndexQueryOp":
        """解析固定结果类型查询 op 自定义文本语法。

        功能说明:
        - 读取冒号后的 symbol.int 结果类型并构造具体查询 op。

        使用示例:
        - ArchGetThreadIdOp.parse(parser)
        """

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

__all__ = ["ArchGetBlockIdOp", "ArchGetBlockNumOp", "ArchGetThreadIdOp", "ArchGetThreadNumOp", "ArchGetSubthreadIdOp", "ArchGetSubthreadNumOp"]
