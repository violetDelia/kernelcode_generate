"""DSL AST arch node definitions.


功能说明:
- 定义 arch helper 对应的 AST 节点，节点只保存 DSL 语义数据，不执行 lowering。

API 列表:
- `ArchQueryAST(location: SourceLocation | None = None)`
- `ArchGetBlockIdAST(location: SourceLocation | None = None)` / `ArchGetBlockNumAST(...)` / `ArchGetSubthreadIdAST(...)` / `ArchGetSubthreadNumAST(...)` / `ArchGetThreadIdAST(...)` / `ArchGetThreadNumAST(...)`
- `ArchGetDynamicMemoryAST(space: MemorySpaceAttrAST, location: SourceLocation | None = None)`
- `ArchBarrierAST(visibility: list[PythonObjectAttrAST], scope: PythonObjectAttrAST, location: SourceLocation | None = None)`
- `ArchLaunchKernelAST(callee: PythonObjectAttrAST, block: SymbolDimAST | ConstValueAST, thread: SymbolDimAST | ConstValueAST, subthread: SymbolDimAST | ConstValueAST, args: list[ValueAST] = field(default_factory=list), shared_memory_size: SymbolDimAST | ConstValueAST = ..., location: SourceLocation | None = None)`

使用示例:
- from kernel_gen.dsl.ast.nodes.arch import ArchGetThreadIdAST
- node = ArchGetThreadIdAST()

关联文件:
- spec: spec/dsl/ast/nodes/arch.md
- test: test/dsl/ast/nodes/test_arch.py
- 功能实现: kernel_gen/dsl/ast/nodes/arch.py
"""

from __future__ import annotations

from dataclasses import dataclass, field

from xdsl.context import Context
from xdsl.dialects.builtin import ArrayAttr, IntAttr, StringAttr, i8
from xdsl.ir import Attribute, Block, Operation, SSAValue
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dialect.arch import (
    ArchBarrierOp,
    ArchGetBlockIdOp,
    ArchGetBlockNumOp,
    ArchGetDynamicMemoryOp,
    ArchGetSubthreadIdOp,
    ArchGetSubthreadNumOp,
    ArchGetThreadIdOp,
    ArchGetThreadNumOp,
    ArchLaunchKernelOp,
    ArchScopeAttr,
    ArchVisibilityAttr,
)
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.operation.arch import BarrierScope, BarrierVisibility
from kernel_gen.symbol_variable.memory import MemorySpace
from .attr import EmitMlirResult, MemorySpaceAttrAST, PythonObjectAttrAST, SourceLocation
from .basic import StatementAST, ValueAST
from .symbol import ConstValueAST, SymbolDimAST


@dataclass
class ArchQueryAST(ValueAST):
    """arch 查询表达式节点。


    功能说明:
    - 表示 DSL 中最小 `arch` 查询调用基类。
    - 具体查询必须由专用子类表达，不能通过字符串字段分派。

    使用示例:
    - ArchGetBlockIdAST()
    - ArchGetThreadNumAST()

    关联文件:
    - spec: spec/dsl/ast/__init__.md
    - test: test/dsl/ast/test_mlir_gen.py
    - 功能实现: kernel_gen/dsl/ast/nodes/
    """

    location: SourceLocation | None = None

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将 arch 查询节点发射为对应查询 op。"""

        assert isinstance(ctx, Context)
        assert block is None or isinstance(block, Block)
        raise KernelCodeError(
            ErrorKind.CONTRACT,
            ErrorModule.MLIR_GEN,
            "ArchQueryAST base class cannot emit MLIR",
        )


@dataclass
class ArchGetBlockIdAST(ArchQueryAST):
    """get_block_id helper 专用注册节点。"""

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将 get_block_id 节点发射为 `arch.get_block_id`。"""

        assert isinstance(ctx, Context)
        assert block is None or isinstance(block, Block)
        return ArchGetBlockIdOp()


@dataclass
class ArchGetBlockNumAST(ArchQueryAST):
    """get_block_num helper 专用注册节点。"""

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将 get_block_num 节点发射为 `arch.get_block_num`。"""

        assert isinstance(ctx, Context)
        assert block is None or isinstance(block, Block)
        return ArchGetBlockNumOp()


@dataclass
class ArchGetSubthreadIdAST(ArchQueryAST):
    """get_subthread_id helper 专用注册节点。"""

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将 get_subthread_id 节点发射为 `arch.get_subthread_id`。"""

        assert isinstance(ctx, Context)
        assert block is None or isinstance(block, Block)
        return ArchGetSubthreadIdOp()


@dataclass
class ArchGetSubthreadNumAST(ArchQueryAST):
    """get_subthread_num helper 专用注册节点。"""

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将 get_subthread_num 节点发射为 `arch.get_subthread_num`。"""

        assert isinstance(ctx, Context)
        assert block is None or isinstance(block, Block)
        return ArchGetSubthreadNumOp()


@dataclass
class ArchGetThreadIdAST(ArchQueryAST):
    """get_thread_id helper 专用注册节点。"""

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将 get_thread_id 节点发射为 `arch.get_thread_id`。"""

        assert isinstance(ctx, Context)
        assert block is None or isinstance(block, Block)
        return ArchGetThreadIdOp()


@dataclass
class ArchGetThreadNumAST(ArchQueryAST):
    """get_thread_num helper 专用注册节点。"""

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将 get_thread_num 节点发射为 `arch.get_thread_num`。"""

        assert isinstance(ctx, Context)
        assert block is None or isinstance(block, Block)
        return ArchGetThreadNumOp()

@dataclass
class ArchGetDynamicMemoryAST(ValueAST):
    """arch 动态内存入口表达式节点。


    功能说明:
    - 表示 `get_dynamic_memory(space)` 的调用节点。
    - 仅允许片上空间 `SM/LM/TSM/TLM1/TLM2/TLM3`。

    使用示例:
    - ArchGetDynamicMemoryAST(space=MemorySpace.SM)

    关联文件:
    - spec: spec/dsl/ast/__init__.md
    - test: test/dsl/ast/test_mlir_gen.py
    - 功能实现: kernel_gen/dsl/ast/nodes/
    """

    space: MemorySpaceAttrAST
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.space, MemorySpaceAttrAST):
            self.space = MemorySpaceAttrAST(self.space, self.location)

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将动态内存查询节点发射为 `arch.get_dynamic_memory`。"""

        assert isinstance(ctx, Context)
        assert block is None or isinstance(block, Block)
        space = self.space.space
        space_attr = self.space.emit_mlir(ctx, None)
        if not isinstance(space_attr, NnMemorySpaceAttr):
            raise KernelCodeError(ErrorKind.INTERNAL, ErrorModule.MLIR_GEN, "dynamic memory space attr emit must return NnMemorySpaceAttr")
        if space is MemorySpace.SM:
            size_symbol = "SM_SIZE"
        elif space is MemorySpace.LM:
            size_symbol = "LM_SIZE"
        elif space is MemorySpace.TSM:
            size_symbol = "TSM_SIZE"
        elif space is MemorySpace.TLM1:
            size_symbol = "TLM1_SIZE"
        elif space is MemorySpace.TLM2:
            size_symbol = "TLM2_SIZE"
        elif space is MemorySpace.TLM3:
            size_symbol = "TLM3_SIZE"
        else:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "get_dynamic_memory space must be on-chip MemorySpace")
        return ArchGetDynamicMemoryOp(
            space_attr,
            NnMemoryType(ArrayAttr([StringAttr(size_symbol)]), ArrayAttr([IntAttr(1)]), i8, space_attr),
        )

@dataclass
class ArchBarrierAST(StatementAST):
    """arch barrier 语句节点。


    功能说明:
    - 表示 `barrier(visibility=[...], scope=BarrierScope.THREAD)` 的同步语句。
    - 仅保存 visibility / scope 两个显式字段，具体 verifier 细节交由 lowering 负责。

    使用示例:
    - ArchBarrierAST(
    -     visibility=[_KG_OPERATION_ARCH.BarrierVisibility.TSM, _KG_OPERATION_ARCH.BarrierVisibility.TLM],
    -     scope=_KG_OPERATION_ARCH.BarrierScope.THREAD,
    - )

    关联文件:
    - spec: spec/dsl/ast/__init__.md
    - test: test/dsl/ast/nodes/test_arch.py
    - 功能实现: kernel_gen/dsl/ast/nodes/
    """

    visibility: list[PythonObjectAttrAST]
    scope: PythonObjectAttrAST
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        self.visibility = [item if isinstance(item, PythonObjectAttrAST) else PythonObjectAttrAST(item, self.location) for item in self.visibility]
        if not isinstance(self.scope, PythonObjectAttrAST):
            self.scope = PythonObjectAttrAST(self.scope, self.location)

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将 barrier 节点发射为 `arch.barrier`。"""

        assert isinstance(ctx, Context)
        assert block is None or isinstance(block, Block)
        scope = self.scope.attr
        if not isinstance(scope, BarrierScope):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "barrier scope must be BarrierScope")
        visibility_values: list[BarrierVisibility] = []
        for item in self.visibility:
            value = item.attr
            if not isinstance(value, BarrierVisibility):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "barrier visibility must be BarrierVisibility")
            visibility_values.append(value)
        return ArchBarrierOp(
            ArchScopeAttr.from_name(scope.value),
            ArrayAttr([ArchVisibilityAttr.from_name(item.value) for item in visibility_values]),
        )

@dataclass
class ArchLaunchKernelAST(StatementAST):
    """arch 启动描述语句节点。


    功能说明:
    - 表示 `launch_kernel[block, thread, subthread, shared_memory_size](callee, *args)` 的启动描述。
    - 仅校验 callee symbol ref 与四字段 launch ABI 的基础约束，不承担 lowering 细节。

    使用示例:
    - ArchLaunchKernelAST(
    -     callee="kernel_body",
    -     block=SymbolDimAST("block"),
    -     thread=ConstValueAST(128),
    -     subthread=ConstValueAST(4),
    -     args=[memory],
    -     shared_memory_size=ConstValueAST(0),
    - )

    关联文件:
    - spec: spec/dsl/ast/__init__.md
    - test: test/dsl/ast/nodes/test_arch.py
    - 功能实现: kernel_gen/dsl/ast/nodes/
    """

    callee: PythonObjectAttrAST
    block: SymbolDimAST | ConstValueAST
    thread: SymbolDimAST | ConstValueAST
    subthread: SymbolDimAST | ConstValueAST
    args: list[ValueAST] = field(default_factory=list)
    shared_memory_size: SymbolDimAST | ConstValueAST = field(default_factory=lambda: ConstValueAST(0))
    location: SourceLocation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.callee, PythonObjectAttrAST):
            self.callee = PythonObjectAttrAST(self.callee, self.location)
        if not isinstance(self.block, (SymbolDimAST, ConstValueAST)):
            self.block = ConstValueAST(self.block, location=self.location)
        if not isinstance(self.thread, (SymbolDimAST, ConstValueAST)):
            self.thread = ConstValueAST(self.thread, location=self.location)
        if not isinstance(self.subthread, (SymbolDimAST, ConstValueAST)):
            self.subthread = ConstValueAST(self.subthread, location=self.location)
        if not isinstance(self.shared_memory_size, (SymbolDimAST, ConstValueAST)):
            self.shared_memory_size = ConstValueAST(self.shared_memory_size, location=self.location)
        self.args = [arg if isinstance(arg, ValueAST) else ConstValueAST(arg, location=self.location) for arg in self.args]

    def emit_mlir(self, ctx: Context, block: Block | None = None) -> EmitMlirResult:
        """将 launch_kernel 节点发射为 `arch.launch`。"""

        assert isinstance(ctx, Context)
        assert isinstance(block, Block)
        block_extent = self.block.emit_mlir(ctx, block)
        if isinstance(block_extent, Operation):
            block.add_op(block_extent)
            block_extent = block_extent.results[0]
        thread_extent = self.thread.emit_mlir(ctx, block)
        if isinstance(thread_extent, Operation):
            block.add_op(thread_extent)
            thread_extent = thread_extent.results[0]
        subthread_extent = self.subthread.emit_mlir(ctx, block)
        if isinstance(subthread_extent, Operation):
            block.add_op(subthread_extent)
            subthread_extent = subthread_extent.results[0]
        shared_memory_size = self.shared_memory_size.emit_mlir(ctx, block)
        if isinstance(shared_memory_size, Operation):
            block.add_op(shared_memory_size)
            shared_memory_size = shared_memory_size.results[0]
        launch_args: list[SSAValue] = []
        for arg in self.args:
            emitted_arg = arg.emit_mlir(ctx, block)
            if isinstance(emitted_arg, Operation):
                block.add_op(emitted_arg)
                emitted_arg = emitted_arg.results[0]
            if not isinstance(emitted_arg, SSAValue):
                raise KernelCodeError(
                    ErrorKind.CONTRACT,
                    ErrorModule.MLIR_GEN,
                    "launch_kernel arg must lower to SSA value",
                )
            launch_args.append(emitted_arg)
        if not isinstance(block_extent, SSAValue):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "launch_kernel block must lower to SSA value")
        if not isinstance(thread_extent, SSAValue):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "launch_kernel thread must lower to SSA value")
        if not isinstance(subthread_extent, SSAValue):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "launch_kernel subthread must lower to SSA value")
        if not isinstance(shared_memory_size, SSAValue):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.MLIR_GEN, "launch_kernel shared_memory_size must lower to SSA value")
        return ArchLaunchKernelOp(
            str(self.callee.attr),
            block_extent,
            thread_extent,
            subthread_extent,
            shared_memory_size,
            launch_args,
        )
