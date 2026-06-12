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
- `KernelEmitter.emit_func(self, func_op: func.FuncOp) -> str`

使用示例:
- from kernel_gen.dsl.gen_kernel import gen_kernel
- source = gen_kernel(func_op, EmitCContext())

关联文件:
- spec: spec/dsl/gen_kernel/kernel_emitter.md
- test: test/dsl/gen_kernel/test_gen_kernel.py
- 功能实现: kernel_gen/dsl/gen_kernel/kernel_emitter.py
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
    IntAttr,
    IntegerAttr,
    Signedness,
    ModuleOp,
    StringAttr,
    SymbolRefAttr,
)
from xdsl.ir import Operation, Region, SSAValue

from kernel_gen.dialect.arch import ArchBarrierOp, ArchGetDynamicMemoryOp, ArchGetThreadIdOp, ArchGetThreadNumOp, ArchLaunchOp
from kernel_gen.dialect.dma import DmaCastOp, DmaReshapeOp, DmaViewOp
from kernel_gen.dialect.memory import MemoryGetDataOp
from kernel_gen.dialect.nn import NnAddOp, NnMemorySpaceAttr, NnMemoryType, copy_memory_type
from kernel_gen.dialect.symbol import SymbolAddOp, SymbolCastOp, SymbolConstOp, SymbolEqOp, SymbolNeOp, SymbolValueType
from kernel_gen.core.config import get_codegen_mode, restore_config, set_target, snapshot_config
from kernel_gen.target import registry as target_registry

from .emit import emit_c_op, emit_c_value
from .emit_context import EmitCContext


_NPU_DEMO_LAUNCH_SCALAR_TYPES = (
    SymbolValueType,
    Float16Type,
    BFloat16Type,
    Float32Type,
    Float64Type,
)




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

    def _template_names_from_types(self, types: list[Any]) -> list[str]:
        """收集函数签名中的 memory template name。

        功能说明:
        - 按签名出现顺序去重，生成 C++ template 参数列表。
        - 仅消费 `NnMemoryType.template_name`，未命名 memory 不参与模板头生成。

        使用示例:
        - names = self._template_names_from_types(input_types)

        关联文件:
        - spec: spec/dsl/gen_kernel/gen_kernel.md
        - test: test/dsl/gen_kernel/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel/gen_kernel.py
        """

        names: list[str] = []
        for attr in types:
            if not isinstance(attr, NnMemoryType):
                continue
            attr.verify()
            template_name = attr.template_name.data
            if template_name and template_name not in names:
                names.append(template_name)
        return names

    def _template_prefix_from_types(self, types: list[Any]) -> str:
        """生成函数模板头文本。

        功能说明:
        - 对含 template-name memory 的函数生成 `template <typename ...>` 前缀。
        - 无 template name 时返回空字符串。

        使用示例:
        - prefix = self._template_prefix_from_types(input_types)

        关联文件:
        - spec: spec/dsl/gen_kernel/gen_kernel.md
        - test: test/dsl/gen_kernel/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel/gen_kernel.py
        """

        names = self._template_names_from_types(types)
        if not names:
            return ""
        params = ", ".join(f"typename {name}" for name in names)
        return f"template <{params}>\n"

    def _template_call_name(self, func_name: str, types: list[Any]) -> str:
        """生成带模板实参的函数名。

        功能说明:
        - wrapper 调用 device body 时只显式传递业务 template 参数。
        - 无业务 template name 时返回裸函数名，避免把 context 类型混入 launch name。

        使用示例:
        - callee = self._template_call_name("body", input_types)

        关联文件:
        - spec: spec/dsl/gen_kernel/gen_kernel.md
        - test: test/dsl/gen_kernel/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel/gen_kernel.py
        """

        names: list[str] = []
        for attr in types:
            if not isinstance(attr, NnMemoryType):
                continue
            attr.verify()
            template_name = attr.template_name.data
            if template_name and template_name not in names:
                names.append(template_name)
        if not names:
            return func_name
        template_args = ", ".join(names)
        return f"{func_name}<{template_args}>"

    def _template_instance_seed_fragment(self, text: str) -> str:
        """把函数名或 template name 转成 C++ alias 片段。

        功能说明:
        - 仅供当前文件生成内部 template dtype seed alias 使用。
        - 将非标识符字符替换为 `_`，避免 IR symbol 名称直接进入 C++ alias 时破坏源码。

        使用示例:
        - fragment = self._template_instance_seed_fragment("kernel.device")
        """

        fragment = re.sub(r"[^0-9A-Za-z_]", "_", text)
        if not fragment:
            return "_"
        if fragment[0].isdigit():
            return f"_{fragment}"
        return fragment

    def _template_instance_seed_lines_from_types(self, func_name: str, types: list[Any]) -> list[str]:
        """生成 generated source 的 template dtype seed alias。

        功能说明:
        - 对带 `NnMemoryType.template_name` 的 memory 参数输出内部 `using` alias。
        - alias 只记录生成源码已知的 concrete element dtype，供 execute_engine compile shim 做唯一模板实例化。
        - 不生成 `kg_execute_entry`、dispatcher 或运行时 dtype 组合。

        使用示例:
        - seed_lines = self._template_instance_seed_lines_from_types("kernel", input_types)
        """

        lines: list[str] = []
        seen: set[str] = set()
        func_fragment = self._template_instance_seed_fragment(func_name)
        for attr in types:
            if not isinstance(attr, NnMemoryType):
                continue
            attr.verify()
            template_name = attr.template_name.data
            if not template_name or template_name in seen:
                continue
            seen.add(template_name)
            template_fragment = self._template_instance_seed_fragment(template_name)
            space_text = self.emit_attr(attr.space)
            element_type_text = self._type_to_c(attr.element_type)
            memory_type_text = self._normalize_memory_stmt(f"Memory<{space_text}, {element_type_text}>")
            lines.append(
                f"using __kernel_gen_template_instance_seed_{func_fragment}__{template_fragment} = {memory_type_text};"
            )
        return lines

    def _allow_absent_memory_metadata_comment(self, func_op: func.FuncOp, *, body_arg_offset: int = 0) -> str:
        """生成 allow-absent memory 参数 metadata 注释。

        功能说明:
        - 扫描函数体中直接查询 `memory.get_data` 的 block argument。
        - 将对应 runtime 参数索引、element dtype 与 rank 写成执行引擎可解析的源码注释。

        使用示例:
        - comment = self._allow_absent_memory_metadata_comment(func_op)
        """

        input_types = list(func_op.function_type.inputs.data)
        metadata: dict[int, tuple[str, int]] = {}
        allow_absent_args: set[SSAValue] = set()
        for op in self._walk_ops(func_op):
            if not isinstance(op, MemoryGetDataOp):
                continue
            for arg_index, arg_value in enumerate(func_op.args):
                if op.source is not arg_value:
                    continue
                runtime_index = arg_index - body_arg_offset
                if runtime_index < 0:
                    continue
                arg_type = input_types[arg_index]
                if not isinstance(arg_type, NnMemoryType):
                    continue
                arg_type.verify()
                dtype = self._type_to_c(arg_type.element_type)
                metadata[runtime_index] = (dtype, len(arg_type.shape.data))
                allow_absent_args.add(arg_value)
        if not metadata:
            return ""
        self._validate_allow_absent_memory_data_uses(func_op, allow_absent_args)
        items = ";".join(f"{index}:{dtype}:{rank}" for index, (dtype, rank) in sorted(metadata.items()))
        return f"// kg.allow_absent_memory_args: {items}"

    def _is_zero_symbol_const_value(self, value: SSAValue) -> bool:
        """判断 SSA value 是否来自 `symbol.const 0`。

        功能说明:
        - allow-absent guard 只承认 `cast(memory.get_data(mem)) == 0` 或 `!= 0`。
        - 仅检查公开 op/result 关系，不依赖跨文件私有 helper。

        使用示例:
        - if self._is_zero_symbol_const_value(compare.rhs): ...
        """

        owner = SSAValue.get(value).owner
        if not isinstance(owner, SymbolConstOp):
            return False
        return owner.value.data == 0

    def _memory_arg_from_casted_get_data_value(self, value: SSAValue) -> SSAValue | None:
        """从 `symbol.cast(memory.get_data(arg))` 取回 memory arg。

        功能说明:
        - 返回值只用于识别 allow-absent present guard。
        - 形态不匹配时返回 `None`，调用方继续按普通未保护 data-use 处理。

        使用示例:
        - memory_arg = self._memory_arg_from_casted_get_data_value(compare.lhs)
        """

        cast_owner = SSAValue.get(value).owner
        if not isinstance(cast_owner, SymbolCastOp):
            return None
        get_data_owner = SSAValue.get(cast_owner.source).owner
        if not isinstance(get_data_owner, MemoryGetDataOp):
            return None
        return SSAValue.get(get_data_owner.source)

    def _present_guard_from_condition(self, condition: SSAValue) -> tuple[SSAValue, bool] | None:
        """识别 memory None compare 对应的 present 分支。

        功能说明:
        - `symbol.ne(cast(get_data(mem)), 0)` 表示 true region 是 present。
        - `symbol.eq(cast(get_data(mem)), 0)` 表示 false region 是 present。

        使用示例:
        - guard = self._present_guard_from_condition(if_op.cond)
        """

        owner = SSAValue.get(condition).owner
        if not isinstance(owner, (SymbolEqOp, SymbolNeOp)):
            return None
        lhs_memory = self._memory_arg_from_casted_get_data_value(owner.lhs)
        rhs_memory = self._memory_arg_from_casted_get_data_value(owner.rhs)
        if lhs_memory is not None and self._is_zero_symbol_const_value(owner.rhs):
            return (lhs_memory, isinstance(owner, SymbolNeOp))
        if rhs_memory is not None and self._is_zero_symbol_const_value(owner.lhs):
            return (rhs_memory, isinstance(owner, SymbolNeOp))
        return None

    def _present_regions_by_memory_arg(self, func_op: func.FuncOp) -> dict[SSAValue, tuple[Region, ...]]:
        """收集每个 allow-absent memory arg 的 present region。

        功能说明:
        - 仅承认 DSL lowering 生成的 pointer compare guard。
        - nested region 自动通过 region ancestor 检查继承 present guard。

        使用示例:
        - regions = self._present_regions_by_memory_arg(func_op)
        """

        func_args = set(func_op.args)
        regions: dict[SSAValue, list[Region]] = {}
        for op in self._walk_ops(func_op):
            if not isinstance(op, scf.IfOp):
                continue
            guard = self._present_guard_from_condition(op.cond)
            if guard is None:
                continue
            memory_arg, true_region_is_present = guard
            if memory_arg not in func_args:
                continue
            present_region = op.true_region if true_region_is_present else op.false_region
            regions.setdefault(memory_arg, []).append(present_region)
        return {memory_arg: tuple(items) for memory_arg, items in regions.items()}

    def _op_is_nested_in_region(self, op: Operation, region: Region) -> bool:
        """判断 op 是否位于指定 region 内部。

        功能说明:
        - 沿 parent_region 链向外查找，覆盖 present region 内的嵌套 loop / if。
        - 用于 allow-absent memory data-use 支配检查。

        使用示例:
        - assert self._op_is_nested_in_region(inner_op, if_op.true_region)
        """

        current_region = op.parent_region()
        while current_region is not None:
            if current_region is region:
                return True
            parent_op = current_region.parent_op()
            if parent_op is None:
                return False
            current_region = parent_op.parent_region()
        return False

    def _memory_arg_operand_uses(self, func_op: func.FuncOp, memory_arg: SSAValue) -> tuple[Operation, ...]:
        """列出指定 memory arg 的真实 data-use op。

        功能说明:
        - `memory.get_data` 是 presence query，不算 data-use。
        - 其它直接消费该 memory arg 的 op 均必须位于 present guard 内。

        使用示例:
        - uses = self._memory_arg_operand_uses(func_op, arg)
        """

        uses: list[Operation] = []
        for op in self._walk_ops(func_op):
            if isinstance(op, MemoryGetDataOp):
                continue
            if any(SSAValue.get(operand) is memory_arg for operand in op.operands):
                uses.append(op)
        return tuple(uses)

    def _validate_allow_absent_memory_data_uses(self, func_op: func.FuncOp, allow_absent_args: set[SSAValue]) -> None:
        """校验 allow-absent memory 的 data-use 均受 non-null 分支保护。

        功能说明:
        - guard 外、absent 分支、sibling block 或 guard 之后继续使用 absent memory 时稳定失败。
        - 错误关键词固定包含 `absent memory data-use must be guarded by non-null pointer branch`。

        使用示例:
        - self._validate_allow_absent_memory_data_uses(func_op, allow_absent_args)
        """

        present_regions = self._present_regions_by_memory_arg(func_op)
        for memory_arg in allow_absent_args:
            regions = present_regions.get(memory_arg, ())
            for use_op in self._memory_arg_operand_uses(func_op, memory_arg):
                if any(self._op_is_nested_in_region(use_op, region) for region in regions):
                    continue
                raise self._error(
                    func_op.sym_name.data,
                    "absent memory data-use must be guarded by non-null pointer branch",
                )

    def _prepend_template_instance_seed_lines(self, func_op: func.FuncOp, source: str) -> str:
        """在函数源码前补 generated template dtype seed alias。

        功能说明:
        - 仅当函数签名携带 template-name memory 时生成内部 alias。
        - seed alias 位于函数声明 / 定义前，不改变函数公开签名和调用 ABI。

        使用示例:
        - source = self._prepend_template_instance_seed_lines(func_op, source)
        """

        input_types = list(func_op.function_type.inputs.data)
        result_types = list(func_op.function_type.outputs.data)
        seed_lines = self._template_instance_seed_lines_from_types(func_op.sym_name.data, [*input_types, *result_types])
        if not seed_lines:
            return source
        return "\n".join([*seed_lines, source])

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
        """按输入类型发射源码文本。


        功能说明:
        - `ModuleOp` 走当前文件内 module 组织逻辑。
        - `func.FuncOp`、单 op、SSA value 和 attribute 继续走既有公开分发入口。

        使用示例:
        - source = self.emit(func_op)
        """

        if isinstance(op_or_func, ModuleOp):
            if not self.ctx.is_target("npu_demo"):
                raise self.ctx.emit_error("builtin.module is only supported for target=npu_demo", "")
            plain_func = self._get_npu_demo_plain_func(op_or_func)
            if plain_func is not None:
                return self.emit_func(plain_func)

            dispatcher_func = self._get_npu_demo_entry_dispatcher_func(op_or_func)
            if dispatcher_func is not None:
                funcs = self._module_funcs(op_or_func)
                callee_names: set[str] = set()
                for op in self._walk_ops(dispatcher_func):
                    if isinstance(op, ArchLaunchOp):
                        callee_names.add(self._launch_callee_name(op, dispatcher_func.sym_name.data))
                emitted_sources: list[str] = []
                for func_op in funcs:
                    if func_op is dispatcher_func:
                        continue
                    if func_op.sym_name.data in callee_names:
                        func_name = func_op.sym_name.data
                        input_types = list(func_op.function_type.inputs.data)
                        result_types = list(func_op.function_type.outputs.data)
                        if result_types:
                            raise self._error(func_name, "npu_demo entry dispatcher launch body must not return values")
                        arg_names = self._arg_names(func_op)
                        params: list[str] = ["npu_demo::KernelContext& ctx"]
                        for arg_name, arg_type, arg_value in zip(arg_names, input_types, func_op.args, strict=True):
                            self.ctx.bind_name(arg_value, arg_name)
                            if isinstance(arg_type, NnMemoryType):
                                params.append(f"{self._type_to_c(arg_type)}& {arg_name}")
                                continue
                            params.append(f"{self._type_to_c(arg_type)} {arg_name}")
                        template_prefix = self._template_prefix_from_types(input_types)
                        signature = f"{template_prefix}void {func_name}({', '.join(params)})"
                        self.ctx.push_indent()
                        body = self._emit_default_function_body(func_op)
                        self.ctx.pop_indent()
                        if body:
                            source = self._prepend_template_instance_seed_lines(func_op, f"{signature} {{\n{body}\n}}")
                        else:
                            source = self._prepend_template_instance_seed_lines(func_op, f"{signature} {{\n}}")
                        metadata_comment = self._allow_absent_memory_metadata_comment(func_op)
                        if metadata_comment:
                            emitted_sources.append(f"{metadata_comment}\n{source}")
                        else:
                            emitted_sources.append(source)
                        continue
                    emitted_sources.append(self.emit_func(func_op))
                emitted_sources.append(self.emit_func(dispatcher_func))
                return "\n\n".join(emitted_sources)

            body_func, wrapper_func = self._classify_npu_demo_launch_module(op_or_func)
            codegen_mode = get_codegen_mode()
            body_input_types, body_arg_offset = self._validate_npu_demo_launch_body_signature(body_func)
            body_arg_names = self._arg_names(body_func)[body_arg_offset:]
            body_context_type = "Context" if codegen_mode == "cost" else "npu_demo::KernelContext"
            body_params: list[str] = [f"{body_context_type}& ctx"]
            for arg_name, arg_type in zip(body_arg_names, body_input_types, strict=True):
                if isinstance(arg_type, NnMemoryType):
                    body_params.append(f"{self._type_to_c(arg_type)}& {arg_name}")
                    continue
                if isinstance(arg_type, _NPU_DEMO_LAUNCH_SCALAR_TYPES):
                    body_params.append(f"{self._type_to_c(arg_type)} {arg_name}")
                    continue
            if len(body_params) != len(body_input_types) + 1:
                raise self._error(body_func.sym_name.data, "unsupported npu_demo launch body signature")
            if codegen_mode == "cost":
                body_template_names = self._template_names_from_types(body_input_types)
                if "Context" not in body_template_names:
                    body_template_names.append("Context")
                body_template_prefix = f"template <{', '.join(f'typename {name}' for name in body_template_names)}>\n"
            else:
                body_template_prefix = self._template_prefix_from_types(body_input_types)
            body_signature = f"{body_template_prefix}static void {body_func.sym_name.data}({', '.join(body_params)})"

            emitted: list[str] = [self._prepend_template_instance_seed_lines(body_func, f"{body_signature};")]
            for top_op in op_or_func.ops:
                if top_op is body_func:
                    arg_names = self._arg_names(body_func)
                    for arg_name, arg_value in zip(arg_names, body_func.args, strict=True):
                        self.ctx.bind_name(arg_value, arg_name)
                    self.ctx.push_indent()
                    lines: list[str] = []
                    last_memory_result_name: str | None = None
                    for op in body_func.body.block.ops:
                        if self._bind_transparent_unrealized_conversion_cast(op):
                            continue
                        if op.name == "test.fake_symbol_value":
                            if not op.results or not isinstance(op.results[0].type, SymbolValueType):
                                raise self._error(body_func.sym_name.data, "unsupported npu_demo launch body helper op")
                            expr = op.results[0].type.expr.expr.data
                            expr = expr.replace("thread_num", "npu_demo::thread_num()")
                            expr = expr.replace("thread_id", "npu_demo::thread_id()")
                            self.ctx.bind_name(op.results[0], expr)
                            continue
                        if isinstance(op, func.ReturnOp):
                            self._emit_return_statement(body_func, op)
                            continue
                        if isinstance(op, ArchBarrierOp):
                            lines.append(self._format_npu_demo_barrier_stmt(op, body_func.sym_name.data))
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
                            stmt = self._normalize_npu_demo_stmt(stmt, check_status=codegen_mode == "cost")
                            lines.append(stmt)
                        if len(op.results) == 1 and isinstance(op.results[0].type, NnMemoryType):
                            bound_name = self.ctx.lookup_name(op.results[0])
                            if bound_name is not None:
                                last_memory_result_name = bound_name
                    body = "\n".join(lines)
                    self.ctx.pop_indent()
                    if body:
                        source = self._prepend_template_instance_seed_lines(
                            body_func,
                            f"{body_signature} {{\n{body}\n}}",
                        )
                    else:
                        source = self._prepend_template_instance_seed_lines(body_func, f"{body_signature} {{\n}}")
                    emitted.append(source)
                    continue
                if top_op is wrapper_func:
                    wrapper_body_input_types, wrapper_body_arg_offset = self._validate_npu_demo_launch_wrapper_signature(
                        wrapper_func,
                        body_func,
                    )
                    arg_names = self._arg_names(wrapper_func)
                    launch_op = self._filtered_launch_ops(wrapper_func)[0]
                    block_extent, thread_extent, subthread_extent, shared_memory_size_extent = (
                        self._launch_extents_from_wrapper(launch_op, wrapper_func.sym_name.data)
                    )
                    params: list[str] = []
                    for arg_name, arg_type in zip(arg_names, wrapper_func.function_type.inputs.data, strict=True):
                        if isinstance(arg_type, NnMemoryType):
                            params.append(self._normalize_memory_stmt(f"{self._type_to_c(arg_type)}& {arg_name}"))
                            continue
                        if isinstance(arg_type, _NPU_DEMO_LAUNCH_SCALAR_TYPES):
                            params.append(f"{self._signature_type_to_c(arg_type)} {arg_name}")
                            continue
                    if len(params) != len(wrapper_func.function_type.inputs.data):
                        raise self._error(wrapper_func.sym_name.data, "unsupported npu_demo launch wrapper signature")
                    template_prefix = self._template_prefix_from_types(list(wrapper_func.function_type.inputs.data))
                    wrapper_name = wrapper_func.sym_name.data
                    if codegen_mode == "cost":
                        wrapper_name = f"{wrapper_name}_cost"
                        params.append("std::string& __kg_cost_summary")
                    signature = f"{template_prefix}void {wrapper_name}({', '.join(params)})"
                    self.ctx.push_indent()
                    extent_lines: list[str] = []
                    for extent in (block_extent, thread_extent, subthread_extent, shared_memory_size_extent):
                        extent_name = self.ctx.allocate_name("c_")
                        extent_lines.append(f"{self.ctx.current_indent}constexpr S_INT {extent_name} = {extent};")
                    call_args = ", ".join(arg_names)
                    body_callee = self._template_call_name(body_func.sym_name.data, wrapper_body_input_types)
                    if codegen_mode == "cost":
                        if body_callee == body_func.sym_name.data:
                            body_callee = f"{body_callee}<npu_demo::CostContext>"
                        else:
                            body_callee = f"{body_callee[:-1]}, npu_demo::CostContext>"
                    if codegen_mode == "cost":
                        context_line = f"{self.ctx.current_indent}npu_demo::CostContext ctx;"
                    else:
                        context_line = f"{self.ctx.current_indent}npu_demo::KernelContext ctx;"
                    launch_call = (
                        f"npu_demo::launch<"
                        f"{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size_extent}, "
                        f"{body_callee}>(ctx, {call_args})"
                        if call_args
                        else f"npu_demo::launch<"
                        f"{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size_extent}, "
                        f"{body_callee}>(ctx)"
                    )
                    if codegen_mode == "cost":
                        launch_lines = [
                            f"{self.ctx.current_indent}Status __kg_cost_status = {launch_call};",
                            f"{self.ctx.current_indent}if (__kg_cost_status != StatusCode::kOk) {{",
                            f'{self.ctx.current_indent}    throw std::runtime_error("kg_cost_unsupported");',
                            f"{self.ctx.current_indent}}}",
                        ]
                    else:
                        launch_lines = [f"{self.ctx.current_indent}{launch_call};"]
                    body_lines = [*extent_lines, context_line, *launch_lines]
                    if codegen_mode == "cost":
                        body_lines.append(
                            f"{self.ctx.current_indent}__kg_cost_summary = npu_demo::format_cost_summary(ctx.summary());"
                        )
                    body = "\n".join(body_lines)
                    self.ctx.pop_indent()
                    source = self._prepend_template_instance_seed_lines(wrapper_func, f"{signature} {{\n{body}\n}}")
                    metadata_comment = self._allow_absent_memory_metadata_comment(
                        body_func,
                        body_arg_offset=wrapper_body_arg_offset,
                    )
                    if metadata_comment:
                        emitted.append(f"{metadata_comment}\n{source}")
                    else:
                        emitted.append(source)
                    continue
                emitted.append(self.emit_func(top_op))
            return "\n\n".join(emitted)
        if isinstance(op_or_func, func.FuncOp):
            return self.emit_func(op_or_func)
        if isinstance(op_or_func, SSAValue):
            return self.emit_value(op_or_func)
        if isinstance(op_or_func, func.ReturnOp):
            raise self.ctx.emit_error("func.return/out binding must be emitted in function main flow", "")
        if isinstance(op_or_func, Operation):
            return self.emit_op(op_or_func)
        return self.emit_attr(op_or_func)

    def _module_funcs(self, module_op: ModuleOp) -> list[func.FuncOp]:
        top_ops = list(module_op.ops)
        if any(not isinstance(top_op, func.FuncOp) for top_op in top_ops):
            raise self._error("<module>", "npu_demo launch module must contain only func.func")
        return [top_op for top_op in top_ops if isinstance(top_op, func.FuncOp)]

    def _is_launch_helper_op(self, op: Operation) -> bool:
        return op.name == "test.fake_symbol_value" or isinstance(op, SymbolConstOp)

    def _filtered_launch_ops(self, func_op: func.FuncOp) -> list[Operation]:
        return [op for op in func_op.body.block.ops if not self._is_launch_helper_op(op)]

    def _normalize_npu_demo_stmt(self, stmt: str, *, check_status: bool = False) -> str:
        """归一化 npu_demo 函数体内的公开 helper 调用文本。


        功能说明:
        - 将未限定的线程 / 动态内存 helper 补成 `npu_demo::` 命名空间调用。
        - 不再把成员式 `.view<...>({...})` brace-list 形态改写回 `Vector{...}`。
        - `check_status=True` 时，将返回 `Status` 且首参为 `ctx` 的 npu_demo helper 调用包成 fail-fast 检查。

        使用示例:
        - stmt = self._normalize_npu_demo_stmt(stmt, check_status=True)

        关联文件:
        - spec: spec/dsl/gen_kernel/gen_kernel.md
        - test: test/dsl/gen_kernel/emit/test_package.py
        - 功能实现: kernel_gen/dsl/gen_kernel/gen_kernel.py
        """

        stmt = re.sub(r"(?<![\\w:])thread_id\\(\\)", "npu_demo::thread_id()", stmt)
        stmt = re.sub(r"(?<![\\w:])thread_num\\(\\)", "npu_demo::thread_num()", stmt)
        stmt = re.sub(r"(?<![\\w:])get_dynamic_memory<", "npu_demo::get_dynamic_memory<", stmt)
        if check_status:
            status_helpers = (
                "fill",
                "slice",
                "deslice",
                "store",
                "load",
                "transpose",
                "broadcast",
                "add",
                "sub",
                "mul",
                "truediv",
                "min",
                "max",
                "eq",
                "ne",
                "lt",
                "le",
                "gt",
                "ge",
                "exp",
                "select",
                "reduce_sum",
                "reduce_min",
                "reduce_max",
                "matmul",
                "img2col1d",
                "img2col2d",
            )
            helper_pattern = "|".join(status_helpers)
            stripped = stmt.strip()
            match = re.match(
                rf"^(?P<call>(?:npu_demo::)?(?:{helper_pattern})(?:<[^;]+>)?\s*\(\s*ctx\b.*\))\s*;$",
                stripped,
            )
            if match is not None:
                indent = stmt[: len(stmt) - len(stmt.lstrip())]
                call = match.group("call")
                return "\n".join(
                    (
                        f"{indent}if ({call} != StatusCode::kOk) {{",
                        f'{indent}    throw std::runtime_error("kg_cost_unsupported");',
                        f"{indent}}}",
                    )
                )
        return stmt

    def _get_npu_demo_plain_func(self, module_op: ModuleOp) -> func.FuncOp | None:
        """识别单函数 `npu_demo` module 的普通 emit_c 子集。


        功能说明:
        - 允许 `builtin.module` 只包含一个 `func.func`，且该函数不是 `arch.launch` 双函数 module。
        - 单函数 body 允许 `func.return` 或 `symbol.const + func.return` 这类纯头部/常量 smoke case。
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
            helper_ops = [op for op in raw_ops if self._is_launch_helper_op(op)]
            if any(not isinstance(op, SymbolConstOp) for op in helper_ops):
                return None
            return func_op
        return func_op

    def _get_npu_demo_entry_dispatcher_func(self, module_op: ModuleOp) -> func.FuncOp | None:
        """识别 npu_demo entry_point dispatcher module。

        功能说明:
        - 多函数 module 中恰好一个 `entry_point` host 时，按 dispatcher + device funcs 发射。
        - device/helper 函数先输出，entry dispatcher 最后输出，避免 C++ 调用缺少声明。

        使用示例:
        - dispatcher = self._get_npu_demo_entry_dispatcher_func(module_op)

        关联文件:
        - spec: spec/dsl/gen_kernel/gen_kernel.md
        - test: test/dsl/gen_kernel/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel/gen_kernel.py
        """

        funcs = self._module_funcs(module_op)
        if len(funcs) < 2:
            return None
        dispatcher_funcs = [func_op for func_op in funcs if "entry_point" in func_op.attributes]
        if len(dispatcher_funcs) != 1:
            return None
        dispatcher = dispatcher_funcs[0]
        if not any(isinstance(op, ArchLaunchOp) for op in self._walk_ops(dispatcher)):
            return None
        return dispatcher

    def emit_func(self, func_op: func.FuncOp) -> str:
        body_arg_offset = 0
        if self._is_npu_demo_body_level_kernel(func_op):
            source_type, out_type = self._get_npu_demo_body_level_kernel_types(func_op)
            arg_names = self._arg_names(func_op)
            for arg_name, arg_value in zip(arg_names, func_op.args, strict=True):
                self.ctx.bind_name(arg_value, arg_name)
            source_name = self.ctx.lookup_name(func_op.args[1]) or arg_names[1]
            source_type_text = self._normalize_memory_stmt(f"{self._type_to_c(source_type)}& {source_name}")
            out_type_text = self._normalize_memory_stmt(f"{self._type_to_c(out_type)}& out")
            template_prefix = self._template_prefix_from_types([source_type, out_type])
            signature = (
                f"{template_prefix}void {func_op.sym_name.data}"
                f"(npu_demo::KernelContext& ctx, {source_type_text}, {out_type_text})"
            )
            self.ctx.push_indent()
            self._validate_npu_demo_body_level_kernel_body(func_op)
            element_type = self._type_to_c(out_type.element_type)
            source_view_accessor = "template view" if source_type.template_name.data else "view"
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
                f"{self.ctx.current_indent}auto src_view = {source_name}.{source_view_accessor}<{element_type}>"
                f"({{tid * 16}} /*offset*/, {{16}} /*size*/, {{1}} /*stride*/);",
                f"{self.ctx.current_indent}auto work_tile = tsm.view<{element_type}>"
                f"({{0}} /*offset*/, {{16}} /*size*/, {{1}} /*stride*/);",
                f"{self.ctx.current_indent}auto out_tile = tsm.view<{element_type}>"
                f"({{0}} /*offset*/, {{16}} /*size*/, {{1}} /*stride*/);",
                "",
                f"{self.ctx.current_indent}slice(ctx, work_tile, src_view, {{0}} /*offset*/, "
                f"{{16}} /*size*/, {{1}} /*stride*/);",
                f"{self.ctx.current_indent}add<MemorySpace::TSM, {element_type}, {element_type}>"
                f"(ctx, out_tile, work_tile, work_tile);",
                f"{self.ctx.current_indent}deslice(ctx, out, out_tile, {{tid * 16}} /*offset*/, "
                f"{{16}} /*size*/, {{1}} /*stride*/);",
            ]
            body = "\n".join(lines)
            self.ctx.pop_indent()
            body_arg_offset = 1
        else:
            include_context = False
            context_arg_offset = 0
            if self.ctx.is_target("npu_demo"):
                include_context = not any(isinstance(op, ArchLaunchOp) for op in self._walk_ops(func_op))
            if include_context:
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
                    if isinstance(result_type, SymbolValueType) and not (
                        self.ctx.is_target("cpu") or self.ctx.is_target("npu_demo")
                    ):
                        raise self._error(func_name, "symbol scalar return is only supported on cpu and npu_demo")
                    self._type_to_c(result_type)
                arg_names = self._arg_names(func_op)
                if input_types and arg_names and arg_names[0] == "ctx":
                    context_arg_offset = 1
                params: list[str] = []
                if context_arg_offset == 0:
                    params.append("Context& ctx")
                for index, (arg_name, arg_type, arg_value) in enumerate(
                    zip(arg_names, input_types, func_op.args, strict=True)
                ):
                    self.ctx.bind_name(arg_value, arg_name)
                    if context_arg_offset == 1 and index == 0:
                        params.append("Context& ctx")
                        continue
                    if isinstance(arg_type, NnMemoryType):
                        params.append(f"{self._type_to_c(arg_type)}& {arg_name}")
                    else:
                        params.append(f"{self._type_to_c(arg_type)} {arg_name}")
                return_type = "void"
                if result_types:
                    return_type = self._type_to_c(result_types[0])
                template_names = self._template_names_from_types([*input_types[context_arg_offset:], *result_types])
                if "Context" not in template_names:
                    template_names.append("Context")
                template_prefix = f"template <{', '.join(f'typename {name}' for name in template_names)}>\n"
                signature = f"{template_prefix}{return_type} {func_name}({', '.join(params)})"
            else:
                signature = self._emit_default_signature(func_op)
            self.ctx.push_indent()
            body = self._emit_default_function_body(func_op)
            self.ctx.pop_indent()
            body_arg_offset = context_arg_offset
        if body:
            source = self._prepend_template_instance_seed_lines(func_op, f"{signature} {{\n{body}\n}}")
        else:
            source = self._prepend_template_instance_seed_lines(func_op, f"{signature} {{\n}}")
        metadata_comment = self._allow_absent_memory_metadata_comment(func_op, body_arg_offset=body_arg_offset)
        if metadata_comment:
            return f"{metadata_comment}\n{source}"
        return source

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
        - memory 参数后允许继续携带零个或多个 `!symbol.int` tile / shape 参数或普通整数 / 浮点标量参数。
        - memory 参数必须 element type 一致，尾部公开标量参数必须保持为已支持的 scalar type。

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
        arg_names: list[str] = []
        attrs = func_op.arg_attrs
        if isinstance(attrs, ArrayAttr):
            for index, attr in enumerate(attrs.data):
                if isinstance(attr, DictionaryAttr):
                    name_attr = attr.data.get("name")
                    if isinstance(name_attr, StringAttr) and name_attr.data:
                        arg_names.append(name_attr.data)
                        continue
                arg_names.append(f"arg{index}")
        subject = f"func {func_name}"
        if result_types:
            raise self.ctx.emit_error(subject, "unsupported npu_demo launch body signature")
        if len(input_types) < 3:
            raise self.ctx.emit_error(subject, "unsupported npu_demo launch body signature")

        body_arg_offset = 0
        if len(input_types) >= 4 and arg_names and arg_names[0] == "ctx":
            body_arg_offset = 1

        body_input_types = input_types[body_arg_offset:]
        memory_input_types: list[NnMemoryType] = []
        symbol_start = len(body_input_types)
        for index, arg_type in enumerate(body_input_types):
            if isinstance(arg_type, NnMemoryType):
                memory_input_types.append(arg_type)
                continue
            symbol_start = index
            break
        scalar_input_types = body_input_types[symbol_start:]
        if len(memory_input_types) < 3:
            raise self.ctx.emit_error(subject, "unsupported npu_demo launch body signature")
        if any(not isinstance(arg_type, _NPU_DEMO_LAUNCH_SCALAR_TYPES) for arg_type in scalar_input_types):
            raise self.ctx.emit_error(subject, "unsupported npu_demo launch body signature")
        first_memory_type = memory_input_types[0]
        if any(arg_type.element_type != first_memory_type.element_type for arg_type in memory_input_types[1:]):
            raise self.ctx.emit_error(subject, "npu_demo launch body requires matching element types")
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
        if not self._same_launch_signature_without_template_names(input_types, body_input_types):
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

    def _same_launch_signature_without_template_names(self, lhs_types: list[Any], rhs_types: list[Any]) -> bool:
        """比较 launch wrapper/body 的基础签名。

        功能说明:
        - `template_name` 是 EmitC annotation，不参与 wrapper 与 body 的基础 ABI 匹配。
        - memory 参数比较前用公开 `copy_memory_type(...)` 清除 template name，其它参数按原类型比较。

        使用示例:
        - if self._same_launch_signature_without_template_names(wrapper_types, body_types): ...
        """

        if len(lhs_types) != len(rhs_types):
            return False
        for lhs_type, rhs_type in zip(lhs_types, rhs_types, strict=True):
            if isinstance(lhs_type, NnMemoryType) and isinstance(rhs_type, NnMemoryType):
                if copy_memory_type(lhs_type) != copy_memory_type(rhs_type):
                    return False
                continue
            if lhs_type != rhs_type:
                return False
        return True

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

        template_prefix = self._template_prefix_from_types([*input_types, *result_types])
        return f"{template_prefix}{return_type} {func_name}({', '.join(params)})"

    def _bind_rewritten_out_result(self, func_op: func.FuncOp, op: Operation) -> None:
        """把 rewrite 后仍保留 memory result 的 DMA op 绑定到首个 out 参数。


        功能说明:
        - 仅对无返回值且首参为 `nn.memory` 的 out-param 函数生效。
        - `npu_demo` 默认函数中的 `dma.cast` 仍可别名到 out 参数，保证 buffer-results case 不生成未声明局部名。
        - `npu_demo` device body 中的 `dma.view` / `dma.reshape` 是局部 tile 视图，不能别名到 out 参数名。
        - sibling cost function 会返回 `!symbol.int`，首参不是 out-param，不能把局部 DMA 结果绑定成 `arg0`。

        使用示例:
        - self._bind_rewritten_out_result(func_op, op)
        """

        if self.ctx.is_target("npu_demo") and not isinstance(op, DmaCastOp):
            return
        if not func_op.args or not op.results or len(op.results) != 1:
            return
        if list(func_op.function_type.outputs.data):
            return
        if not isinstance(func_op.args[0].type, NnMemoryType):
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

    def _emit_generic_symbol_const(self, op: Operation) -> str | None:
        """发射 generic 形式的 `symbol.const`。

        功能说明:
        - `kernel-pattern-attach` 为匹配公开 IR 合同会生成 generic `"symbol.const"()`。
        - `npu_demo` final host 允许 xDSL `builtin.unregistered` + `op_name__="symbol.const"` 形态。
        - 这里按公开 attr/result 形态绑定为 `S_INT` 局部变量，避免后续 `symbol.eq` 取值失败。

        使用示例:
        - stmt = self._emit_generic_symbol_const(op)
        """

        if isinstance(op, SymbolConstOp) or self._generic_symbol_op_name(op) != "symbol.const":
            return None
        if len(op.results) != 1:
            raise self._error(op.name, "generic symbol.const must have one result")
        value_attr = op.attributes.get("value")
        if isinstance(value_attr, IntAttr):
            value = value_attr.data
        elif isinstance(value_attr, IntegerAttr):
            value = value_attr.value.data
        else:
            raise self._error(op.name, "generic symbol.const value must be int attr")
        name = self.ctx.create_or_get_name(op.results[0])
        return f"{self.ctx.current_indent}S_INT {name} = {value};"

    def _generic_symbol_op_name(self, op: Operation) -> str | None:
        """识别当前允许的 generic symbol op 名称。

        功能说明:
        - 保留既有未注册 `symbol.const` / `symbol.eq` 形态支持。
        - 仅在 `target="npu_demo"` 时额外承接 `builtin.unregistered` + `op_name__` 为
          `"symbol.const"` / `"symbol.eq"` 的 final host 形态。
        - 其它 `builtin.unregistered` op 返回 `None`，继续按公开 unsupported 路径失败。

        使用示例:
        - if self._generic_symbol_op_name(op) == "symbol.eq": ...
        """

        if op.name in {"symbol.const", "symbol.eq"}:
            return op.name
        if not self.ctx.is_target("npu_demo") or op.name != "builtin.unregistered":
            return None
        op_name_attr = op.attributes.get("op_name__")
        if isinstance(op_name_attr, StringAttr) and op_name_attr.data in {"symbol.const", "symbol.eq"}:
            return op_name_attr.data
        return None

    def _emit_generic_symbol_eq(self, op: Operation) -> str | None:
        """发射 generic 形式的 `symbol.eq`。

        功能说明:
        - `kernel-pattern-attach` 输出 generic `"symbol.eq"` 以保持 IR 合同文本。
        - `npu_demo` final host 允许 xDSL `builtin.unregistered` + `op_name__="symbol.eq"` 形态。
        - 源码生成阶段仍按公开 operands/result type 生成布尔局部变量。

        使用示例:
        - stmt = self._emit_generic_symbol_eq(op)
        """

        if isinstance(op, SymbolEqOp) or self._generic_symbol_op_name(op) != "symbol.eq":
            return None
        if len(op.operands) != 2 or len(op.results) != 1:
            raise self._error(op.name, "generic symbol.eq must have two operands and one result")
        lhs_expr = emit_c_value(op.operands[0], self.ctx)
        rhs_expr = emit_c_value(op.operands[1], self.ctx)
        result_type = self._type_to_c(op.results[0].type)
        result_name = self.ctx.create_or_get_name(op.results[0])
        return f"{self.ctx.current_indent}{result_type} {result_name} = ({lhs_expr} == {rhs_expr});"

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
        result_type = result_types[0]
        if len(return_op.arguments) != 1:
            raise self._error(func_op.sym_name.data, "unsupported return form")
        if return_op.arguments[0].type != result_type:
            raise self._error(func_op.sym_name.data, "unsupported return form")
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
            total_stmt = self._emit_npu_demo_return_symbol_assignment(op)
            if total_stmt is not None:
                lines.append(total_stmt)
                continue
            generic_symbol_const_stmt = self._emit_generic_symbol_const(op)
            if generic_symbol_const_stmt is not None:
                lines.append(generic_symbol_const_stmt)
                continue
            generic_symbol_eq_stmt = self._emit_generic_symbol_eq(op)
            if generic_symbol_eq_stmt is not None:
                lines.append(generic_symbol_eq_stmt)
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
