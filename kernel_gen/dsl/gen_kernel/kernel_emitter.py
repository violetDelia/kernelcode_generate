"""Function-level C-like kernel generation helpers.


功能说明:
- 按 `emit_c` 的节点级规则，组装 `func.func` 的完整函数源码。
- 负责函数签名、参数顺序、输出参数与函数体遍历。

API 列表:
- `class KernelEmitter(ctx: EmitCContext, emit_op: Callable[[Operation, EmitCContext], str] = emit_c_op)`
- `KernelEmitter.emit_include(self) -> str`
- `KernelEmitter.emit_type(self, attr: Any) -> str`
- `KernelEmitter.emit_attr(self, attr: Any) -> str`
- `KernelEmitter.emit_value(self, value: SSAValue) -> str`
- `KernelEmitter.emit_op(self, op: Operation) -> str`
- `KernelEmitter.emit(self, op_or_func: Any) -> str`
- `KernelEmitter.emit_module(self, module_op: ModuleOp) -> str`
- `KernelEmitter.emit_func(self, func_op: func.FuncOp) -> str`

使用示例:
- from kernel_gen.dsl.gen_kernel import gen_kernel
- source = gen_kernel(func_op, EmitCContext())

关联文件:
- spec: spec/dsl/gen_kernel/gen_kernel.md
- test: test/dsl/gen_kernel/test_gen_kernel.py
- 功能实现: kernel_gen/dsl/gen_kernel/gen_kernel.py
"""

from __future__ import annotations
from kernel_gen.core.error import KernelCodeError

from typing import Any
from typing import Callable
import re

from xdsl.dialects import func, scf
from xdsl.dialects.builtin import (
    ArrayAttr,
    BFloat16Type,
    DictionaryAttr,
    Float16Type,
    Float32Type,
    Float64Type,
    IntegerType,
    IndexType,
    Signedness,
    ModuleOp,
    StringAttr,
    SymbolRefAttr,
)
from xdsl.ir import Operation, SSAValue

from kernel_gen.dialect.arch import ArchBarrierOp, ArchGetDynamicMemoryOp, ArchGetThreadIdOp, ArchGetThreadNumOp, ArchLaunchOp
from kernel_gen.dialect.dma import DmaAllocOp, DmaCastOp, DmaReshapeOp, DmaViewOp
from kernel_gen.dialect.nn import NnAddOp, NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolAddOp, SymbolConstOp, SymbolValueType
from kernel_gen.core.config import restore_config, set_target, snapshot_config
from kernel_gen.target import registry as target_registry

from .emit import emit_c_op, emit_c_value
from .emit_context import EmitCContext




class KernelEmitter:
    """统一的 `gen_kernel` 内部发射器。


    功能说明:
    - 统一承接单个 op / `func.func` 的发射。
    - 对 `func.func` 通过内部策略选择收口 `npu_demo` 等函数级特化，
      避免继续散落成平行 helper 入口。

    使用示例:
        - source = KernelEmitter(EmitCContext()).emit(func_op)

    关联文件:
    - spec: spec/dsl/gen_kernel/gen_kernel.md
    - test: test/dsl/gen_kernel/test_gen_kernel.py
    - 功能实现: kernel_gen/dsl/gen_kernel/gen_kernel.py
    """

    def __init__(
        self,
        ctx: EmitCContext,
        *,
        emit_op: Callable[[Operation, EmitCContext], str] = emit_c_op,
    ) -> None:
        self.ctx = ctx
        self._emit_op_impl = emit_op


    def _normalize_memory_stmt(self, stmt: str) -> str:
        if not stmt or "Memory<" not in stmt:
            return stmt
        normalized = stmt
        normalized = re.sub(
            r"Memory<\s*MemorySpace::(\w+)\s*,\s*(?:cpu::)?\1\s*,",
            r"Memory<MemorySpace::\1,",
            normalized,
        )
        normalized = re.sub(
            r"Memory<\s*(?:cpu::)?(GM|TSM|TLM1|TLM2|TLM3|LM|SM)\s*,",
            r"Memory<MemorySpace::\1,",
            normalized,
        )
        normalized = re.sub(r"Memory<\s*(?!MemorySpace::)([^>]+)\s*>", r"Memory<MemorySpace::GM, \1>", normalized)
        normalized = re.sub(r",\s*MemorySpace::GM\s*\)", ")", normalized)
        normalized = re.sub(
            r"(Memory<[^>]+>\s+\w+\()\s*([^,]+),\s*([A-Za-z_][A-Za-z0-9_]*)_shape,\s*([A-Za-z_][A-Za-z0-9_]*)_stride,\s*([0-9]+),\s*([^)]+)\)",
            r"\1\2, \5, \3_shape, \4_stride, \6)",
            normalized,
        )
        return normalized

    def _walk_ops(self, op: Operation) -> list[Operation]:
        items: list[Operation] = [op]
        for region in op.regions:
            for block in region.blocks:
                for inner in block.ops:
                    items.extend(self._walk_ops(inner))
        return items

    def _is_tile_codegen_function(self, func_op: func.FuncOp) -> bool:
        has_symbol_tuner = any(
            (
                op.name == "tuner.param"
                and op.results
                and isinstance(op.results[0].type, SymbolValueType)
            )
            for op in self._walk_ops(func_op)
        )
        if has_symbol_tuner:
            return True
        if not self.ctx.is_target("cpu"):
            return False
        return any(
            "tile.analysis" in op.attributes or "tile.tile_exprs" in op.attributes
            for op in self._walk_ops(func_op)
        )

    def _validate_tile_codegen_contract(self, func_op: func.FuncOp) -> None:
        func_name = func_op.sym_name.data
        if not self.ctx.is_target("cpu"):
            raise self._error(func_name, "TileCodegenMalformed: tile codegen is cpu-only")

        ops = list(func_op.body.block.ops)
        if not any(op.name == "symbol.for" for op in ops):
            raise self._error(func_name, "TileCodegenMalformed: missing explicit tile loop (symbol.for)")
        if not any(op.name == "tuner.param" and op.results and isinstance(op.results[0].type, SymbolValueType) for op in ops):
            raise self._error(func_name, "TileCodegenMalformed: missing tuner.param")
        if any(op.name in {"kernel_split.tile_value", "tile.step_value", "kernel_split.symbol_literal", "tile.symbol_literal"} for op in ops):
            raise self._error(func_name, "TileCodegenMalformed: legacy bridge ops are not allowed")
        if any(item.name == "func.call" for item in self._walk_ops(func_op)):
            raise self._error(func_name, "TileCodegenUnexpectedHelperFunction: func.call is not allowed in tile codegen")

    def _leading_rewritten_out_param_count(self, func_op: func.FuncOp) -> int:
        input_types = list(func_op.function_type.inputs.data)
        attrs = func_op.arg_attrs
        count = 0
        for index, arg_type in enumerate(input_types):
            if not isinstance(arg_type, NnMemoryType):
                break
            if not isinstance(attrs, ArrayAttr):
                break
            if index >= len(attrs.data):
                break
            attr = attrs.data[index]
            if not isinstance(attr, DictionaryAttr):
                break
            name_attr = attr.data.get("name")
            if not isinstance(name_attr, StringAttr) or name_attr.data != f"arg{index}":
                break
            count += 1
        return count

    def emit_include(self) -> str:
        """返回当前 target 需要的源码前导。


        功能说明:
        - 统一收口 `gen_kernel(...)` / `emit_c(...)` 的 target 级 `#include` 与 `using namespace` 文本。
        - 避免在公开入口和函数级桥接层重复硬编码同一份前导。

        使用示例:
        - prelude = self.emit_include()

        关联文件:
        - spec: spec/dsl/gen_kernel/gen_kernel.md
        - test: test/dsl/gen_kernel/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel/gen_kernel.py
        """

        return self.ctx.dispatch_include()

    def _type_to_c(self, attr: Any) -> str:
        """按当前 target 生成类型名。


        功能说明:
        - 统一收口 `EmitCContext.dispatch_type(...)`，避免在多处重复判断 target。
        - 仅影响 `gen_kernel` 的函数级签名与辅助输出。

        使用示例:
        - c_type = self._type_to_c(mem_type)

        关联文件:
        - spec: spec/dsl/gen_kernel/gen_kernel.md
        - test: test/dsl/gen_kernel/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel/gen_kernel.py
        """

        return self.ctx.dispatch_type(attr)

    def emit_type(self, attr: Any) -> str:
        return self.ctx.dispatch_type(attr)

    def emit_attr(self, attr: Any) -> str:
        emitted = self.ctx.dispatch_attr(attr)
        if emitted is None:
            raise self.ctx.emit_error(f"attr {attr}", "unsupported attr")
        return emitted

    def emit_value(self, value: SSAValue) -> str:
        return emit_c_value(value, self.ctx)

    def emit_op(self, op: Operation) -> str:
        return self._emit_op_impl(op, self.ctx)

    def _signature_type_to_c(self, attr: Any) -> str:
        snapshot = snapshot_config()
        try:
            set_target("cpu")
            return EmitCContext().dispatch_type(attr)
        finally:
            restore_config(snapshot)

    def _error(self, func_name: str, reason: str) -> KernelCodeError:
        return self.ctx.emit_error(f"func {func_name}", reason)

    def _arg_names(self, func_op: func.FuncOp) -> list[str]:
        names: list[str] = []
        attrs = func_op.arg_attrs
        if isinstance(attrs, ArrayAttr):
            for index, attr in enumerate(attrs.data):
                if isinstance(attr, DictionaryAttr):
                    name_attr = attr.data.get("name")
                    if isinstance(name_attr, StringAttr) and name_attr.data:
                        names.append(name_attr.data)
                        continue
                names.append(f"arg{index}")
            return names
        return [f"arg{index}" for index, _ in enumerate(func_op.args)]

    def emit(self, op_or_func: Any) -> str:
        if isinstance(op_or_func, ModuleOp):
            return self.emit_module(op_or_func)
        if isinstance(op_or_func, func.FuncOp):
            return self.emit_func(op_or_func)
        if isinstance(op_or_func, SSAValue):
            return self.emit_value(op_or_func)
        if isinstance(op_or_func, func.ReturnOp):
            raise self.ctx.emit_error("func.return/out binding must be emitted in function main flow", "")
        if isinstance(op_or_func, Operation):
            return self.emit_op(op_or_func)
        return self.emit_attr(op_or_func)

    def emit_module(self, module_op: ModuleOp) -> str:
        """发射 `target=npu_demo` 的受控 `builtin.module` 双函数源码。


        功能说明:
        - 仅对 `target="npu_demo"` 放行受控 `builtin.module` 子集。
        - 允许 module 携带 helper `func.func`，并按 module 中的出现顺序输出源码。
        - wrapper 仍必须能被唯一 `arch.launch` 识别，body / wrapper 之外的 helper 继续走通用函数发射。

        使用示例:
        - source = KernelEmitter(EmitCContext()).emit(module_op)

        关联文件:
        - spec: spec/dsl/gen_kernel/gen_kernel.md
        - test: test/dsl/gen_kernel/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel/gen_kernel.py
        """

        if not self.ctx.is_target("npu_demo"):
            raise self._error("<module>", "builtin.module is only supported for target=npu_demo")

        plain_func = self._get_npu_demo_plain_func(module_op)
        if plain_func is not None:
            return self.emit_func(plain_func)

        body_func, wrapper_func = self._classify_npu_demo_launch_module(module_op)
        emitted: list[str] = [self._emit_npu_demo_launch_body_declaration(body_func)]
        for top_op in module_op.ops:
            if not isinstance(top_op, func.FuncOp):
                raise self._error("<module>", "npu_demo launch module must contain only func.func")
            if top_op is body_func:
                emitted.append(self._emit_npu_demo_launch_body_function(body_func))
                continue
            if top_op is wrapper_func:
                emitted.append(self._emit_npu_demo_launch_wrapper_function(wrapper_func, body_func))
                continue
            emitted.append(self.emit_func(top_op))
        return "\n\n".join(emitted)

    def _module_funcs(self, module_op: ModuleOp) -> list[func.FuncOp]:
        top_ops = list(module_op.ops)
        if any(not isinstance(top_op, func.FuncOp) for top_op in top_ops):
            raise self._error("<module>", "npu_demo launch module must contain only func.func")
        return [top_op for top_op in top_ops if isinstance(top_op, func.FuncOp)]

    def _is_launch_helper_op(self, op: Operation) -> bool:
        return op.name == "test.fake_symbol_value" or isinstance(op, SymbolConstOp)

    def _filtered_launch_ops(self, func_op: func.FuncOp) -> list[Operation]:
        return [op for op in func_op.body.block.ops if not self._is_launch_helper_op(op)]

    def _normalize_npu_demo_stmt(self, stmt: str) -> str:
        stmt = re.sub(r"(?<![\\w:])thread_id\\(\\)", "npu_demo::thread_id()", stmt)
        stmt = re.sub(r"(?<![\\w:])thread_num\\(\\)", "npu_demo::thread_num()", stmt)
        stmt = re.sub(r"(?<![\\w:])get_dynamic_memory<", "npu_demo::get_dynamic_memory<", stmt)
        if ".view<" in stmt:
            stmt = stmt.replace("({", "(Vector{").replace(", {", ", Vector{")
        return stmt

    def _get_npu_demo_plain_func(self, module_op: ModuleOp) -> func.FuncOp | None:
        """识别单函数 `npu_demo` module 的普通 emit_c 子集。


        功能说明:
        - 允许 `builtin.module` 只包含一个 `func.func`，且该函数不是 `arch.launch` 双函数 module。
        - 单函数 body 必须至少包含一个非 `func.return` 的语义 op，避免把空 module 误当成成功输入。
        - 该分支复用普通 `emit_func(...)` 路径，不影响既有 `launch body + wrapper` 约束。

        使用示例:
        - func_op = self._get_npu_demo_plain_func(module_op)

        关联文件:
        - spec: spec/dsl/gen_kernel/gen_kernel.md
        - test: test/dsl/gen_kernel/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel/gen_kernel.py
        """

        top_ops = list(module_op.ops)
        if any(not isinstance(top_op, func.FuncOp) for top_op in top_ops):
            return None
        func_ops = [top_op for top_op in top_ops if isinstance(top_op, func.FuncOp)]
        if len(func_ops) != 1:
            return None
        func_op = func_ops[0]
        raw_ops = list(func_op.body.block.ops)
        filtered_ops = self._filtered_launch_ops(func_op)
        if not filtered_ops:
            return None
        if not isinstance(filtered_ops[-1], func.ReturnOp):
            return None
        if any(isinstance(op, ArchLaunchOp) for op in filtered_ops):
            return None
        if any(
            isinstance(op, (ArchGetThreadIdOp, ArchGetThreadNumOp, ArchGetDynamicMemoryOp, ArchBarrierOp))
            for op in filtered_ops
        ):
            return None
        if all(isinstance(op, func.ReturnOp) for op in filtered_ops):
            if any(self._is_launch_helper_op(op) for op in raw_ops):
                return None
            return func_op
        if all(self._is_launch_helper_op(op) or isinstance(op, func.ReturnOp) for op in filtered_ops):
            return None
        return func_op

    def emit_func(self, func_op: func.FuncOp) -> str:
        if self._is_npu_demo_body_level_kernel(func_op):
            signature = self._emit_npu_demo_body_level_kernel_signature(func_op)
            self.ctx.push_indent()
            body = self._emit_npu_demo_body_level_kernel_body(func_op)
            self.ctx.pop_indent()
        else:
            signature = self._emit_default_signature(func_op)
            self.ctx.push_indent()
            body = self._emit_default_function_body(func_op)
            self.ctx.pop_indent()
        if body:
            return f"{signature} {{\n{body}\n}}"
        return f"{signature} {{\n}}"

    def _is_npu_demo_body_level_kernel(self, func_op: func.FuncOp) -> bool:
        if not self.ctx.is_target("npu_demo"):
            return False
        arg_names = self._arg_names(func_op)
        input_types = list(func_op.function_type.inputs.data)
        result_types = list(func_op.function_type.outputs.data)
        if len(input_types) != 2 or len(result_types) != 1:
            return False
        if not arg_names or arg_names[0] != "ctx":
            return False
        if not isinstance(input_types[1], NnMemoryType) or not isinstance(result_types[0], NnMemoryType):
            return False
        if input_types[1].element_type != result_types[0].element_type:
            return False
        return True

    def _classify_npu_demo_launch_module(self, module_op: ModuleOp) -> tuple[func.FuncOp, func.FuncOp]:
        func_ops = self._module_funcs(module_op)
        wrapper_candidates = [
            func_op
            for func_op in func_ops
            if any(isinstance(op, ArchLaunchOp) for op in self._filtered_launch_ops(func_op))
        ]
        if len(wrapper_candidates) != 1:
            raise self._error(
                "<module>",
                "npu_demo launch module must contain exactly one wrapper func with arch.launch",
            )

        wrapper_func = wrapper_candidates[0]
        wrapper_ops = self._filtered_launch_ops(wrapper_func)
        if len(wrapper_ops) != 2 or not isinstance(wrapper_ops[0], ArchLaunchOp) or not isinstance(wrapper_ops[1], func.ReturnOp):
            raise self._error(
                wrapper_func.sym_name.data,
                "npu_demo launch wrapper must contain arch.launch followed by func.return",
            )

        callee_name = self._launch_callee_name(wrapper_ops[0], wrapper_func.sym_name.data)
        body_func = next((func_op for func_op in func_ops if func_op.sym_name.data == callee_name), None)
        if body_func is None or body_func is wrapper_func:
            raise self._error(
                wrapper_func.sym_name.data,
                f"npu_demo launch wrapper references missing body {callee_name}",
            )
        return body_func, wrapper_func

    def _launch_callee_name(self, launch_op: Any, wrapper_name: str) -> str:
        callee = launch_op.callee
        if not isinstance(callee, SymbolRefAttr):
            raise self._error(wrapper_name, "npu_demo launch wrapper must use flat @callee")
        if len(callee.nested_references.data) != 0 or not callee.root_reference.data:
            raise self._error(wrapper_name, "npu_demo launch wrapper must use flat @callee")
        return callee.root_reference.data

    def _static_launch_extent(self, launch_op: Any, field_name: str, wrapper_name: str) -> int:
        operand = getattr(launch_op, field_name)
        operand_type = operand.type
        if not isinstance(operand_type, SymbolValueType):
            raise self._error(wrapper_name, f"npu_demo launch wrapper {field_name} must be !symbol.int")
        value = operand_type.get_value()
        if not isinstance(value, int):
            raise self._error(wrapper_name, f"npu_demo launch wrapper {field_name} must be static integer")
        return value

    def _expected_npu_demo_launch_extents(self) -> tuple[int, int, int, int]:
        extents: list[int] = []
        for hw_key in ("block_num", "thread_num", "subthread_num", "sm_memory_size"):
            value = target_registry.get_target_hardware("npu_demo", hw_key)
            if value is None:
                raise self._error("<module>", f"npu_demo target missing {hw_key}")
            extents.append(value)
        return extents[0], extents[1], extents[2], extents[3]

    def _launch_extents_from_wrapper(self, launch_op: Any, wrapper_name: str) -> tuple[int, int, int, int]:
        return (
            self._static_launch_extent(launch_op, "block", wrapper_name),
            self._static_launch_extent(launch_op, "thread", wrapper_name),
            self._static_launch_extent(launch_op, "subthread", wrapper_name),
            self._static_launch_extent(launch_op, "shared_memory_size", wrapper_name),
        )

    def _validate_npu_demo_launch_body_signature(
        self, func_op: func.FuncOp
    ) -> tuple[list[Any], int]:
        """校验 body 函数签名。


        功能说明:
        - body 兼容可选 `ctx` 参数、至少三个连续 memory 参数、零返回形式。
        - memory 参数后允许继续携带零个或多个 `!symbol.int` tile / shape 参数。
        - memory 参数必须 element type 一致，尾部公开标量参数必须保持 `SymbolValueType`。

        使用示例:
        - body_input_types, arg_offset = self._validate_npu_demo_launch_body_signature(body_func)

        关联文件:
        - spec: spec/dsl/gen_kernel/gen_kernel.md
        - test: test/dsl/gen_kernel/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel/gen_kernel.py
        """

        func_name = func_op.sym_name.data
        input_types = list(func_op.function_type.inputs.data)
        result_types = list(func_op.function_type.outputs.data)
        arg_names = self._arg_names(func_op)
        if result_types:
            raise self._error(func_name, "unsupported npu_demo launch body signature")
        if len(input_types) < 3:
            raise self._error(func_name, "unsupported npu_demo launch body signature")

        body_arg_offset = 0
        if len(input_types) >= 4 and arg_names and arg_names[0] == "ctx":
            if not arg_names or arg_names[0] != "ctx":
                raise self._error(func_name, "npu_demo launch body requires leading ctx argument")
            body_arg_offset = 1

        body_input_types = input_types[body_arg_offset:]
        if len(body_input_types) < 3:
            raise self._error(func_name, "unsupported npu_demo launch body signature")

        memory_input_types: list[NnMemoryType] = []
        symbol_start = len(body_input_types)
        for index, arg_type in enumerate(body_input_types):
            if isinstance(arg_type, NnMemoryType):
                memory_input_types.append(arg_type)
                continue
            symbol_start = index
            break
        symbol_input_types = body_input_types[symbol_start:]
        if len(memory_input_types) < 3:
            raise self._error(func_name, "unsupported npu_demo launch body signature")
        if any(not isinstance(arg_type, SymbolValueType) for arg_type in symbol_input_types):
            raise self._error(func_name, "unsupported npu_demo launch body signature")
        first_memory_type = memory_input_types[0]
        if any(arg_type.element_type != first_memory_type.element_type for arg_type in memory_input_types[1:]):
            raise self._error(func_name, "npu_demo launch body requires matching element types")
        return list(body_input_types), body_arg_offset

    def _validate_npu_demo_launch_wrapper_signature(
        self,
        wrapper_func: func.FuncOp,
        body_func: func.FuncOp,
    ) -> tuple[list[NnMemoryType], int]:
        """校验 wrapper 函数签名与 launch 参数透传关系。


        功能说明:
        - wrapper 必须与 body 的非 ctx 参数完全一致，并保持零返回形式。
        - `arch.launch` 的 args 必须按原顺序透传 wrapper 参数，extent 由静态 launch 值与 target registry 一致性共同约束。

        使用示例:
        - lhs_type, rhs_type, out_type = self._validate_npu_demo_launch_wrapper_signature(wrapper, body)

        关联文件:
        - spec: spec/dsl/gen_kernel/gen_kernel.md
        - test: test/dsl/gen_kernel/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel/gen_kernel.py
        """

        body_input_types, body_arg_offset = self._validate_npu_demo_launch_body_signature(body_func)
        func_name = wrapper_func.sym_name.data
        input_types = list(wrapper_func.function_type.inputs.data)
        result_types = list(wrapper_func.function_type.outputs.data)
        wrapper_ops = self._filtered_launch_ops(wrapper_func)
        launch_op = wrapper_ops[0]
        if len(input_types) != len(body_input_types) or result_types:
            raise self._error(func_name, "unsupported npu_demo launch wrapper signature")
        if input_types != body_input_types:
            raise self._error(func_name, "npu_demo launch wrapper signature must match body inputs")

        expected_block, expected_thread, expected_subthread, expected_shared_memory_size = self._expected_npu_demo_launch_extents()
        actual_block, actual_thread, actual_subthread, actual_shared_memory_size = self._launch_extents_from_wrapper(
            launch_op,
            func_name,
        )
        if (actual_block, actual_thread, actual_subthread, actual_shared_memory_size) != (
            expected_block,
            expected_thread,
            expected_subthread,
            expected_shared_memory_size,
        ):
            raise self._error(
                func_name,
                "npu_demo launch wrapper must use npu_demo::launch<"
                f"{expected_block}, {expected_thread}, {expected_subthread}, {expected_shared_memory_size}>; "
                f"got block={actual_block}, thread={actual_thread}, subthread={actual_subthread}, "
                f"shared_memory_size={actual_shared_memory_size}",
            )

        if len(launch_op.args) != len(wrapper_func.args):
            raise self._error(func_name, "npu_demo launch wrapper args must forward wrapper signature")
        for wrapper_arg, launch_arg in zip(wrapper_func.args, launch_op.args, strict=True):
            if wrapper_arg is not launch_arg:
                raise self._error(func_name, "npu_demo launch wrapper args must forward wrapper signature")
        return body_input_types, body_arg_offset

    def _emit_npu_demo_launch_body_function(self, func_op: func.FuncOp) -> str:
        """生成 npu_demo launch body 函数源码。


        功能说明:
        - 输出 `static` body 签名，并按 lowered IR 的实际 op 顺序逐条发射源码。
        - 允许 body 中保留 `arch.barrier`、`dma.alloc`、`dma.view`、`dma.slice`、`dma.deslice` 等公开合同。
        - 不再依赖冻结 add/barrier 子集，body 形态由唯一 wrapper + lowered IR 共同决定。

        使用示例:
        - source = self._emit_npu_demo_launch_body_function(body_func)

        关联文件:
        - spec: spec/dsl/gen_kernel/gen_kernel.md
        - test: test/dsl/gen_kernel/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel/gen_kernel.py
        """

        body_input_types, body_arg_offset = self._validate_npu_demo_launch_body_signature(func_op)
        func_name = func_op.sym_name.data
        arg_names = self._arg_names(func_op)
        for arg_name, arg_value in zip(arg_names, func_op.args, strict=True):
            self.ctx.bind_name(arg_value, arg_name)

        signature = self._emit_npu_demo_launch_body_signature(func_op, body_input_types, body_arg_offset)

        lines: list[str] = []
        last_memory_result_name: str | None = None
        for op in func_op.body.block.ops:
            if self._bind_transparent_unrealized_conversion_cast(op):
                continue
            if op.name == "test.fake_symbol_value":
                if not op.results or not isinstance(op.results[0].type, SymbolValueType):
                    raise self._error(func_name, "unsupported npu_demo launch body helper op")
                expr = op.results[0].type.expr.expr.data
                expr = expr.replace("thread_num", "npu_demo::thread_num()")
                expr = expr.replace("thread_id", "npu_demo::thread_id()")
                self.ctx.bind_name(op.results[0], expr)
                continue
            if isinstance(op, func.ReturnOp):
                stmt = self._emit_return_statement(func_op, op)
                if stmt:
                    lines.append(stmt)
                continue
            if isinstance(op, ArchBarrierOp):
                lines.append(self._format_npu_demo_barrier_stmt(op, func_name))
                continue
            if (
                op.name in {
                    "nn.add",
                    "kernel.matmul",
                    "kernel.binary_elewise",
                    "kernel.exp",
                    "kernel.reduce",
                    "kernel.reduce_min",
                    "kernel.img2col1d",
                    "kernel.img2col2d",
                    "kernel.select",
                }
                and len(op.results) == 1
                and isinstance(op.results[0].type, NnMemoryType)
                and self.ctx.lookup_name(op.results[0]) is None
                and last_memory_result_name is not None
            ):
                self.ctx.bind_name(op.results[0], last_memory_result_name)
            stmt = self.emit_op(op)
            if stmt:
                stmt = self._normalize_npu_demo_stmt(stmt)
                lines.append(stmt)
            if len(op.results) == 1 and isinstance(op.results[0].type, NnMemoryType):
                bound_name = self.ctx.lookup_name(op.results[0])
                if bound_name is not None:
                    last_memory_result_name = bound_name
        body = "\n".join(lines)
        if body:
            return f"{signature} {{\n{body}\n}}"
        return f"{signature} {{\n}}"

    def _emit_npu_demo_launch_body_declaration(self, func_op: func.FuncOp) -> str:
        """生成 npu_demo launch body 的前置声明。


        功能说明:
        - 为 `npu_demo` launch module 提供与定义完全一致的 body 前置声明。
        - 解决 outline 后 wrapper 先于 body 出现时的函数可见性问题，避免 wrapper 调用未声明的 body。

        使用示例:
        - decl = self._emit_npu_demo_launch_body_declaration(body_func)

        关联文件:
        - spec: spec/dsl/gen_kernel/gen_kernel.md
        - test: test/dsl/gen_kernel/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel/gen_kernel.py
        """

        body_input_types, body_arg_offset = self._validate_npu_demo_launch_body_signature(func_op)
        return f"{self._emit_npu_demo_launch_body_signature(func_op, body_input_types, body_arg_offset)};"

    def _emit_npu_demo_launch_body_signature(
        self,
        func_op: func.FuncOp,
        body_input_types: list[NnMemoryType],
        body_arg_offset: int,
    ) -> str:
        """生成 npu_demo launch body 的函数签名。


        功能说明:
        - 统一构造不显式暴露 `KernelContext` 的 `static void <body>(...)` 签名。
        - 供 body 定义与前置声明共享，避免两处拼接逻辑不一致。
        - 三个 memory 参数后允许继续透传 `SymbolValueType` 参数，保持 tile / shape 公开链路。

        使用示例:
        - signature = self._emit_npu_demo_launch_body_signature(func_op, body_input_types, body_arg_offset)

        关联文件:
        - spec: spec/dsl/gen_kernel/gen_kernel.md
        - test: test/dsl/gen_kernel/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel/gen_kernel.py
        """

        func_name = func_op.sym_name.data
        arg_names = self._arg_names(func_op)
        body_arg_names = arg_names[body_arg_offset:]
        params: list[str] = []
        for arg_name, arg_type in zip(body_arg_names, body_input_types, strict=True):
            if isinstance(arg_type, NnMemoryType):
                params.append(f"{self._type_to_c(arg_type)}& {arg_name}")
                continue
            if isinstance(arg_type, SymbolValueType):
                params.append(f"{self._type_to_c(arg_type)} {arg_name}")
                continue
            raise self._error(func_name, "unsupported npu_demo launch body signature")
        return f"static void {func_name}({', '.join(params)})"

    def _emit_npu_demo_launch_wrapper_function(self, wrapper_func: func.FuncOp, body_func: func.FuncOp) -> str:
        """生成 npu_demo wrapper 函数源码。


        功能说明:
        - wrapper 负责把 `lhs/rhs/out` 与 trailing `!symbol.int` 参数原样透传给
          `npu_demo::launch<block, thread, subthread, shared_memory_size>(body, ...)`。
        - launch extent 对应 wrapper IR 中的独立 `symbol.const`，源码中用独立
          `constexpr S_INT` 名称承接，避免 wrapper 发射阶段把常量折成模板字面量。
        - wrapper 与 body 均不显式暴露 `KernelContext` 参数，body 通过 npu_demo free helper 读取活动上下文。

        使用示例:
        - source = self._emit_npu_demo_launch_wrapper_function(wrapper_func, body_func)

        关联文件:
        - spec: spec/dsl/gen_kernel/gen_kernel.md
        - test: test/dsl/gen_kernel/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel/gen_kernel.py
        """

        self._validate_npu_demo_launch_wrapper_signature(wrapper_func, body_func)
        arg_names = self._arg_names(wrapper_func)
        launch_op = self._filtered_launch_ops(wrapper_func)[0]
        block_extent, thread_extent, subthread_extent, shared_memory_size_extent = self._launch_extents_from_wrapper(
            launch_op,
            wrapper_func.sym_name.data,
        )
        params: list[str] = []
        for index, (arg_name, arg_type) in enumerate(zip(arg_names, wrapper_func.function_type.inputs.data, strict=True)):
            if isinstance(arg_type, NnMemoryType):
                params.append(f"{self._signature_type_to_c(arg_type)}& {arg_name}")
                continue
            if isinstance(arg_type, SymbolValueType):
                params.append(f"{self._signature_type_to_c(arg_type)} {arg_name}")
                continue
            raise self._error(wrapper_func.sym_name.data, "unsupported npu_demo launch wrapper signature")
        signature = f"void {wrapper_func.sym_name.data}({', '.join(params)})"
        self.ctx.push_indent()
        extent_names: list[str] = []
        extent_lines: list[str] = []
        for extent in (block_extent, thread_extent, subthread_extent, shared_memory_size_extent):
            extent_name = self.ctx.allocate_name("c_")
            extent_names.append(extent_name)
            extent_lines.append(f"{self.ctx.current_indent}constexpr S_INT {extent_name} = {extent};")
        block_name, thread_name, subthread_name, shared_memory_size_name = extent_names
        call_args = ", ".join(arg_names)
        launch_line = (
            f"{self.ctx.current_indent}npu_demo::launch<{block_name}, {thread_name}, {subthread_name}, {shared_memory_size_name}>({body_func.sym_name.data}, {call_args});"
            if call_args
            else f"{self.ctx.current_indent}npu_demo::launch<{block_name}, {thread_name}, {subthread_name}, {shared_memory_size_name}>({body_func.sym_name.data});"
        )
        body = "\n".join([*extent_lines, launch_line])
        self.ctx.pop_indent()
        return f"{signature} {{\n{body}\n}}"

    def _get_npu_demo_body_level_kernel_types(self, func_op: func.FuncOp) -> tuple[NnMemoryType, NnMemoryType]:
        func_name = func_op.sym_name.data
        input_types = list(func_op.function_type.inputs.data)
        result_types = list(func_op.function_type.outputs.data)
        arg_names = self._arg_names(func_op)
        if len(input_types) != 2 or len(result_types) != 1:
            raise self._error(func_name, "unsupported npu_demo body-level kernel signature")
        if not arg_names or arg_names[0] != "ctx":
            raise self._error(func_name, "npu_demo body-level kernel requires leading ctx argument")
        source_type = input_types[1]
        out_type = result_types[0]
        if not isinstance(source_type, NnMemoryType) or not isinstance(out_type, NnMemoryType):
            raise self._error(func_name, "unsupported npu_demo body-level kernel signature")
        if source_type.element_type != out_type.element_type:
            raise self._error(func_name, "npu_demo body-level kernel requires matching element types")
        return source_type, out_type

    def _validate_npu_demo_body_level_kernel_body(self, func_op: func.FuncOp) -> None:
        ops = list(func_op.body.block.ops)
        if not ops:
            return
        first_op = ops[0]
        if isinstance(first_op, func.ReturnOp):
            raise self._error(func_op.sym_name.data, "npu_demo body-level kernel body must match frozen subset")
        raise self._error(
            func_op.sym_name.data,
            f"unsupported npu_demo body-level kernel body op {first_op.name}",
        )

    def _emit_npu_demo_body_level_kernel_signature(self, func_op: func.FuncOp) -> str:
        source_type, out_type = self._get_npu_demo_body_level_kernel_types(func_op)
        arg_names = self._arg_names(func_op)
        for arg_name, arg_value in zip(arg_names, func_op.args, strict=True):
            self.ctx.bind_name(arg_value, arg_name)
        source_name = self.ctx.lookup_name(func_op.args[1]) or arg_names[1]
        return (
            f"void {func_op.sym_name.data}({self._signature_type_to_c(source_type)}& {source_name}, "
            f"{self._signature_type_to_c(out_type)}& out)"
        )

    def _emit_npu_demo_body_level_kernel_body(self, func_op: func.FuncOp) -> str:
        """生成 npu_demo body-level kernel 的固定函数体骨架。


        功能说明:
        - 输出 `thread_id/thread_num -> get_dynamic_memory -> view/slice/add/deslice` 的受控顺序。
        - 仅接受冻结子集，遇到非法 body 结构时必须显式失败。

        使用示例:
        - body = self._emit_npu_demo_body_level_kernel_body(func_op)

        关联文件:
        - spec: spec/dsl/gen_kernel/gen_kernel.md
        - test: test/dsl/gen_kernel/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel/gen_kernel.py
        """

        self._get_npu_demo_body_level_kernel_types(func_op)
        self._validate_npu_demo_body_level_kernel_body(func_op)
        _, out_type = self._get_npu_demo_body_level_kernel_types(func_op)
        arg_names = self._arg_names(func_op)
        for arg_name, arg_value in zip(arg_names, func_op.args, strict=True):
            if self.ctx.lookup_name(arg_value) is None:
                self.ctx.bind_name(arg_value, arg_name)
        source_name = self.ctx.lookup_name(func_op.args[1]) or arg_names[1]
        element_type = self._type_to_c(out_type.element_type)
        lines = [
            f"{self.ctx.current_indent}S_INT tid = npu_demo::thread_id();",
            f"{self.ctx.current_indent}S_INT tnum = npu_demo::thread_num();",
            "",
            (
                f"{self.ctx.current_indent}Memory<MemorySpace::TSM, {element_type}> tsm = "
                f"npu_demo::get_dynamic_memory<MemorySpace::TSM>();"
            ),
            (
                f"{self.ctx.current_indent}Memory<MemorySpace::TLM1, {element_type}> tlm = "
                f"npu_demo::get_dynamic_memory<MemorySpace::TLM1>();"
            ),
            "",
            f"{self.ctx.current_indent}auto src_view = view({source_name}, tid * 16, 16, 1);",
            f"{self.ctx.current_indent}auto work_tile = view(tsm, 0, 16, 1);",
            f"{self.ctx.current_indent}auto out_tile = view(tsm, 0, 16, 1);",
            "",
            f"{self.ctx.current_indent}slice(work_tile, src_view, 0, 16, 1);",
            f"{self.ctx.current_indent}add<MemorySpace::TSM, {element_type}, {element_type}>"
            f"(out_tile, work_tile, work_tile);",
            f"{self.ctx.current_indent}deslice(out, out_tile, tid * 16, 16, 1);",
        ]
        return "\n".join(lines)

    def _format_npu_demo_barrier_stmt(self, barrier_op: ArchBarrierOp, func_name: str) -> str:
        if barrier_op.scope.scope.data != "block":
            raise self._error(func_name, "npu_demo barrier scope must be block")
        spaces = []
        for entry in barrier_op.visibility.data:
            visibility_attr = getattr(entry, "visibility", None)
            if visibility_attr is None:
                raise self._error(func_name, "npu_demo barrier visibility must be [tsm, tlm]")
            spaces.append(visibility_attr.data)
        if spaces != ["tsm", "tlm"]:
            raise self._error(func_name, "npu_demo barrier visibility must be [tsm, tlm]")
        return (
            f"{self.ctx.current_indent}npu_demo::barrier("
            "{BarrierVisibility::TSM, BarrierVisibility::TLM}, BarrierScope::BLOCK);"
        )

    def _emit_default_signature(self, func_op: func.FuncOp) -> str:
        """生成默认 rewrite-after-IR 函数签名。


        功能说明:
        - 默认 CPU/通用路径只消费已经过 `BufferResultsToOutParamsPass` 的 IR。
        - 所有 `Memory` 参数统一生成为非 const 引用，避免在源码签名层按读写语义拆分两套 ABI。
        - 若函数仍保留旧 `memory return` ABI，则显式报错，阻止后端继续隐式推导 `out`。

        使用示例:
        - signature = self._emit_default_signature(func_op)

        关联文件:
        - spec: spec/dsl/gen_kernel/gen_kernel.md
        - test: test/dsl/gen_kernel/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel/gen_kernel.py
        """
        func_name = func_op.sym_name.data
        input_types = list(func_op.function_type.inputs.data)
        result_types = list(func_op.function_type.outputs.data)
        if len(result_types) > 1:
            raise self._error(func_name, "unsupported return form")
        if result_types and isinstance(result_types[0], NnMemoryType):
            raise self._error(
                func_name,
                "legacy memory return ABI is not supported; run BufferResultsToOutParamsPass first",
            )
        if result_types:
            result_type = result_types[0]
            if isinstance(result_type, SymbolValueType) and not (self.ctx.is_target("cpu") or self.ctx.is_target("npu_demo")):
                raise self._error(func_name, "symbol scalar return is only supported on cpu and npu_demo")
            self._type_to_c(result_type)

        arg_names = self._arg_names(func_op)
        params: list[str] = []
        for index, (arg_name, arg_type, arg_value) in enumerate(zip(arg_names, input_types, func_op.args, strict=True)):
            self.ctx.bind_name(arg_value, arg_name)
            if isinstance(arg_type, NnMemoryType):
                params.append(f"{self._type_to_c(arg_type)}& {arg_name}")
            else:
                params.append(f"{self._type_to_c(arg_type)} {arg_name}")

        return_type = "void"
        if result_types:
            return_type = self._type_to_c(result_types[0])

        return f"{return_type} {func_name}({', '.join(params)})"

    def _is_returned_output_alloc(self, func_op: func.FuncOp, op: DmaAllocOp) -> bool:
        if not self.ctx.is_target("cpu"):
            return False
        result_types = list(func_op.function_type.outputs.data)
        if len(result_types) != 1 or not isinstance(result_types[0], NnMemoryType):
            return False
        return any(isinstance(use.operation, func.ReturnOp) for use in op.result.uses)

    def _bind_rewritten_out_result(self, func_op: func.FuncOp, op: Operation) -> None:
        """把 rewrite 后仍保留 memory result 的 DMA op 绑定到首个 out 参数。"""

        if not func_op.args or not op.results or len(op.results) != 1:
            return
        if not isinstance(op, (DmaCastOp, DmaViewOp, DmaReshapeOp)):
            return
        result = op.results[0]
        if not isinstance(result.type, NnMemoryType):
            return
        out_name = self.ctx.lookup_name(func_op.args[0])
        if out_name is None:
            return
        self.ctx.bind_name(result, out_name)

    def _bind_transparent_unrealized_conversion_cast(self, op: Operation) -> bool:
        """透明绑定单层 `builtin.unrealized_conversion_cast`。


        功能说明:
        - lowering 链路中会残留少量 `unrealized_conversion_cast`，主要用于把常量包装成 `!symbol.int`。
        - 这类 op 在源码生成阶段不需要独立语句，只需把结果别名回其唯一输入表达式。

        使用示例:
        - if self._bind_transparent_unrealized_conversion_cast(op): continue

        关联文件:
        - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
        - test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
        - 功能实现: [kernel_gen/dsl/gen_kernel/gen_kernel.py](kernel_gen/dsl/gen_kernel/gen_kernel.py)
        """

        if op.name != "builtin.unrealized_conversion_cast":
            return False
        if len(op.operands) != 1 or len(op.results) != 1:
            raise self._error(op.name, "unrealized_conversion_cast must have exactly one operand and one result")
        self.ctx.bind_name(op.results[0], emit_c_value(op.operands[0], self.ctx))
        return True

    def _emit_npu_demo_return_symbol_assignment(self, op: Operation) -> str | None:
        """为 `npu_demo` 的 `%total` 累计值生成稳定赋值语句。


        功能说明:
        - sibling cost function 会把 `%total : !symbol.int` 作为最终返回值。
        - 这里绕过 `emit_c_op(symbol.add, ...)` 的默认 `vN` 命名，直接生成
          `S_INT total = (...);`，并为后续 `func.return` 绑定稳定右值名。
        - 仅在 `target="npu_demo"`、`symbol.add` 结果表达式名为 `total` 且被
          `func.return` 消费时生效，不影响 `tuner.cost -> costN` 的既有命名合同。

        使用示例:
        - stmt = self._emit_npu_demo_return_symbol_assignment(op)

        关联文件:
        - spec: spec/dsl/gen_kernel/gen_kernel.md
        - test: test/dsl/gen_kernel/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel/gen_kernel.py
        """

        if not self.ctx.is_target("npu_demo"):
            return None
        if not isinstance(op, SymbolAddOp) or len(op.results) != 1:
            return None
        result = op.results[0]
        if self.ctx.lookup_name(result) is not None or not isinstance(result.type, SymbolValueType):
            return None
        if result.type.expr.expr.data.strip().lower() != "total":
            return None
        if not any(isinstance(use.operation, func.ReturnOp) for use in result.uses):
            return None
        lhs_expr = emit_c_value(op.operands[0], self.ctx)
        rhs_expr = emit_c_value(op.operands[1], self.ctx)
        self.ctx.bind_name(result, "total")
        return f"{self.ctx.current_indent}S_INT total = ({lhs_expr} + {rhs_expr});"

    def _emit_return_statement(
        self,
        func_op: func.FuncOp,
        return_op: func.ReturnOp,
        *,
        allow_direct_return_nn_add: bool = False,
    ) -> str | None:
        """生成默认路径下的 `func.return` 收尾语句。


        功能说明:
        - rewrite-after-IR 默认路径只允许无返回或单一非 `Memory` 标量返回。
        - 若 `func.return` 仍返回 `Memory`，说明 IR 还保留旧 ABI，必须显式失败。
        - `allow_direct_return_nn_add` 仅为兼容旧调用点保留的内部参数；当前默认路径不会靠它放行旧 `memory return`。

        使用示例:
        - stmt = self._emit_return_statement(func_op, return_op)

        关联文件:
        - spec: spec/dsl/gen_kernel/gen_kernel.md
        - test: test/dsl/gen_kernel/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel/gen_kernel.py
        """
        result_types = list(func_op.function_type.outputs.data)
        if not result_types:
            if return_op.arguments:
                raise self._error(func_op.sym_name.data, "unsupported return form")
            return None
        if len(result_types) != 1:
            raise self._error(func_op.sym_name.data, "unsupported return form")
        result_type = result_types[0]
        if len(return_op.arguments) != 1:
            raise self._error(func_op.sym_name.data, "unsupported return form")
        if return_op.arguments[0].type != result_type:
            raise self._error(func_op.sym_name.data, "unsupported return form")
        if isinstance(result_type, NnMemoryType):
            raise self._error(
                func_op.sym_name.data,
                "legacy memory return ABI is not supported; run BufferResultsToOutParamsPass first",
            )
        if isinstance(result_type, SymbolValueType) and not (self.ctx.is_target("cpu") or self.ctx.is_target("npu_demo")):
            raise self._error(
                func_op.sym_name.data,
                "symbol scalar return is only supported on cpu and npu_demo",
            )
        value_expr = emit_c_value(return_op.arguments[0], self.ctx)
        return f"{self.ctx.current_indent}return {value_expr};"

    def _emit_default_function_body(self, func_op: func.FuncOp) -> str:
        """生成默认 rewrite-after-IR 函数体。


        功能说明:
        - 按 IR 顺序逐个委托普通 op 到 `emit_c_op(...)`。
        - `func.return` 统一走 `emit_return_statement(...)` 收尾，不再从旧 `memory return` 形态隐式补 `out`。
        - 仅保留既有 `dma.alloc`/`out` 绑定清理逻辑，避免对 rewrite 后 ABI 额外引入新的函数级特例。

        使用示例:
        - body = self._emit_default_function_body(func_op)

        关联文件:
        - spec: spec/dsl/gen_kernel/gen_kernel.md
        - test: test/dsl/gen_kernel/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel/gen_kernel.py
        """
        is_tile_codegen = self._is_tile_codegen_function(func_op)
        if is_tile_codegen:
            self._validate_tile_codegen_contract(func_op)

        tile_var_by_expr: dict[str, str] = {}
        emitted_tile_exprs: set[str] = set()

        lines: list[str] = []
        for op in func_op.body.block.ops:
            if op.name in {"kernel_split.symbol_literal", "tile.symbol_literal", "kernel_split.tile_value", "tile.step_value"}:
                raise self._error(
                    func_op.sym_name.data,
                    "TileCodegenMalformed: legacy bridge ops are not allowed",
                )

            if op.name == "tuner.param":
                if not op.results:
                    raise self._error(func_op.sym_name.data, "TileCodegenMalformed: tuner.param must have a result")
                result_type = op.results[0].type
                if isinstance(result_type, SymbolValueType):
                    expr_name = result_type.expr.expr.data
                    var_name = tile_var_by_expr.setdefault(expr_name, expr_name.strip().lower())
                    self.ctx.bind_name(op.results[0], var_name)
                    if expr_name not in emitted_tile_exprs:
                        lines.append(f'{self.ctx.current_indent}long long {var_name} = tuner_param("{expr_name}");')
                        emitted_tile_exprs.add(expr_name)
                    continue
                raise self._error(func_op.sym_name.data, "TileCodegenMalformed: tuner.param result must be !symbol.int")

            if isinstance(op, func.ReturnOp):
                stmt = self._emit_return_statement(func_op, op)
                if stmt:
                    lines.append(stmt)
                continue
            if self._bind_transparent_unrealized_conversion_cast(op):
                continue
            if isinstance(op, DmaAllocOp) and self._is_returned_output_alloc(func_op, op):
                self.ctx.bind_name(op.result, "out")
                continue
            total_stmt = self._emit_npu_demo_return_symbol_assignment(op)
            if total_stmt is not None:
                lines.append(total_stmt)
                continue
            self._bind_rewritten_out_result(func_op, op)
            stmt = self.emit_op(op)
            if stmt and self.ctx.is_target("cpu"):
                stmt = self._normalize_memory_stmt(stmt)
            if stmt:
                lines.append(stmt)
        return "\n".join(lines)

def __getattr__(name: str) -> Any:
    """拒绝回流的 legacy 双接口公开访问。


    功能说明:
    - 对历史 `gen_signature` / `gen_body` 名称给出统一的缺失语义，避免其被误当成公开稳定入口回流。
    - 不影响模块内部私有 helper 的实现组织；仅用于模块级公开访问边界。

    使用示例:
    - getattr(gen_kernel_module, "gen_signature")  # raises AttributeError

    关联文件:
    - spec: spec/dsl/gen_kernel/gen_kernel.md
    - test: test/dsl/gen_kernel/test_gen_kernel.py
    - 功能实现: kernel_gen/dsl/gen_kernel/gen_kernel.py
    """

    if name in {"gen_signature", "gen_body"}:
        raise AttributeError(f"{name} is no longer a public entry; use gen_kernel(...) instead")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["KernelEmitter"]
