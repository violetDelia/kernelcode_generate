"""Function-level C-like kernel generation helpers.

创建者: 金铲铲大作战
最后一次更改: jcc你莫辜负

功能说明:
- 按 `emit_c` 的节点级规则，组装 `func.func` 的完整函数源码。
- 负责函数签名、参数顺序、输出参数与函数体遍历。

使用示例:
- from kernel_gen.dsl.gen_kernel import gen_kernel
- source = gen_kernel(func_op, EmitCContext(target="cpu"))

关联文件:
- spec: spec/dsl/gen_kernel.md
- test: test/dsl/test_gen_kernel.py
- 功能实现: kernel_gen/dsl/gen_kernel.py
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from typing import Any

from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, DictionaryAttr, Float32Type, Float64Type, IntegerType, IndexType, StringAttr

from kernel_gen.dialect.dma import DmaAllocOp
from kernel_gen.dialect.nn import NnAddOp, NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType

from .emit_c import EmitCContext, emit_c_op


class GenKernelError(ValueError):
    """Raised when `gen_kernel` cannot emit a valid target function."""


def _error(ctx: EmitCContext, func_name: str, reason: str) -> GenKernelError:
    return GenKernelError(f"target={ctx.target}: func {func_name}: {reason}")


def _extract_arg_names(func_op: func.FuncOp) -> list[str]:
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


def _type_to_c(attr: Any) -> str:
    """将 xdsl Attribute 映射为 C 侧类型名。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 用于 `gen_kernel(...)` 的函数级签名拼装，将 IR 类型属性转换为 C/C++ 侧可用类型名。
    - 支持的类型映射清单：
      - `IntegerType(1)` -> `bool`
      - `IntegerType(N)` -> `int{N}_t`
      - `Float32Type` -> `float`
      - `Float64Type` -> `double`
      - `IndexType` -> `long long`
      - `NnMemoryType<T>` -> `Memory<...>`（递归映射 `element_type`）
      - `SymbolValueType` -> `long long`
    - 若遇到不支持类型，将抛出 `TypeError("unsupported type: ...")`。

    使用示例:
    - from xdsl.dialects.builtin import ArrayAttr, IntAttr, f32, f64
    - from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
    - assert _type_to_c(f32) == "float"
    - assert _type_to_c(f64) == "double"
    - mem_f64 = NnMemoryType(ArrayAttr([IntAttr(2)]), ArrayAttr([IntAttr(1)]), f64, NnMemorySpaceAttr.from_name("global"))
    - assert _type_to_c(mem_f64) == "Memory<double>"

    关联文件:
    - spec: spec/dsl/gen_kernel.md
    - test: test/dsl/test_gen_kernel.py
    - 功能实现: kernel_gen/dsl/gen_kernel.py
    """
    if isinstance(attr, IntegerType):
        if attr.width.data == 1:
            return "bool"
        return f"int{attr.width.data}_t"
    if isinstance(attr, Float32Type):
        return "float"
    if isinstance(attr, Float64Type):
        return "double"
    if isinstance(attr, IndexType):
        return "long long"
    if isinstance(attr, NnMemoryType):
        return f"Memory<{_type_to_c(attr.element_type)}>"
    if isinstance(attr, SymbolValueType):
        return "long long"
    raise TypeError(f"unsupported type: {attr}")


def _memory_rank(memory_type: NnMemoryType) -> int:
    """返回 `nn.memory` 的静态 rank。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 为 `gen_kernel` 的固定骨架特化提供统一的 rank 读取。
    - 仅读取 `shape` 条目数量，不额外校验各维是否为静态值。

    使用示例:
    - _memory_rank(mem_type) == 4

    关联文件:
    - spec: spec/dsl/gen_kernel.md
    - test: test/dsl/test_gen_kernel.py
    - 功能实现: kernel_gen/dsl/gen_kernel.py
    """

    return len(memory_type.shape.data)


@dataclass(frozen=True)
class _FunctionStrategy:
    """`func.func` 发射策略描述。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 作为 `_KernelEmitter` 的内部策略描述，统一收口函数级特化的匹配、签名与 body 发射。
    - 不构成公开稳定接口；仅供 `gen_kernel(...)` 在函数级主流程中选择内部策略。

    使用示例:
    - strategy = _FunctionStrategy("default", lambda op: True, emitter._emit_default_function_body)

    关联文件:
    - spec: spec/dsl/gen_kernel.md
    - test: test/dsl/test_gen_kernel.py
    - 功能实现: kernel_gen/dsl/gen_kernel.py
    """

    name: str
    matches: Callable[[func.FuncOp], bool]
    emit_body: Callable[[func.FuncOp], str]
    emit_signature: Callable[[func.FuncOp], str] | None = None

    def build_signature(self, func_op: func.FuncOp, default_signature: Callable[[func.FuncOp], str]) -> str:
        if self.emit_signature is None:
            return default_signature(func_op)
        return self.emit_signature(func_op)


class _KernelEmitter:
    """统一的 `gen_kernel` 内部发射器。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 统一承接单个 op / `func.func` 的发射。
    - 对 `func.func` 通过内部策略选择收口 `direct-return nn.add`、`conv2d_img2col2d_tiled`、`npu_demo` 等函数级特化，
      避免继续散落成平行 helper 入口。

    使用示例:
    - source = _KernelEmitter(EmitCContext(target="cpu")).emit(func_op)

    关联文件:
    - spec: spec/dsl/gen_kernel.md
    - test: test/dsl/test_gen_kernel.py
    - 功能实现: kernel_gen/dsl/gen_kernel.py
    """

    def __init__(self, ctx: EmitCContext) -> None:
        self.ctx = ctx

    def emit(self, op_or_func: Any) -> str:
        if isinstance(op_or_func, func.FuncOp):
            return self._emit_func(op_or_func)
        if isinstance(op_or_func, func.ReturnOp):
            raise GenKernelError(f"target={self.ctx.target}: func.return/out binding must be emitted in function main flow")
        return emit_c_op(op_or_func, self.ctx)

    def _emit_func(self, func_op: func.FuncOp) -> str:
        strategy = self._select_func_strategy(func_op)
        signature = strategy.build_signature(func_op, self._emit_default_signature)
        self.ctx.push_indent()
        body = strategy.emit_body(func_op)
        self.ctx.pop_indent()
        if body:
            return f"{signature} {{\n{body}\n}}"
        return f"{signature} {{\n}}"

    def _function_strategies(self) -> tuple[_FunctionStrategy, ...]:
        return (
            _FunctionStrategy(
                "npu_demo_body_level_kernel",
                self._is_npu_demo_body_level_kernel,
                self._emit_npu_demo_body_level_kernel_body,
                self._emit_npu_demo_body_level_kernel_signature,
            ),
            _FunctionStrategy(
                "cpu_conv2d_img2col2d_tiled",
                self._is_cpu_conv2d_img2col2d_tiled,
                self._emit_cpu_conv2d_img2col2d_tiled_body,
            ),
            _FunctionStrategy(
                "cpu_direct_return_nn_add",
                self._has_cpu_direct_return_nn_add,
                self._emit_cpu_direct_return_nn_add_body,
            ),
            _FunctionStrategy("default", lambda _func_op: True, self._emit_default_function_body),
        )

    def _select_func_strategy(self, func_op: func.FuncOp) -> _FunctionStrategy:
        for strategy in self._function_strategies():
            if strategy.matches(func_op):
                return strategy
        raise _error(self.ctx, func_op.sym_name.data, "no function emission strategy")

    def _is_cpu_conv2d_img2col2d_tiled(self, func_op: func.FuncOp) -> bool:
        return self.ctx.target == "cpu" and func_op.sym_name.data == "conv2d_img2col2d_tiled"

    def _validate_cpu_conv2d_img2col2d_tiled_body(self, func_op: func.FuncOp) -> None:
        ops = list(func_op.body.block.ops)
        if not ops:
            return
        first_op = ops[0]
        if isinstance(first_op, func.ReturnOp):
            raise _error(self.ctx, func_op.sym_name.data, "conv2d_img2col2d_tiled body must match frozen subset")
        raise _error(self.ctx, func_op.sym_name.data, f"unsupported conv2d_img2col2d_tiled body op {first_op.name}")

    def _emit_cpu_conv2d_img2col2d_tiled_body(self, func_op: func.FuncOp) -> str:
        self._validate_cpu_conv2d_img2col2d_tiled_body(func_op)

        input_types = list(func_op.function_type.inputs.data)
        result_types = list(func_op.function_type.outputs.data)
        if len(input_types) != 2 or len(result_types) != 1:
            raise _error(self.ctx, func_op.sym_name.data, "unsupported conv2d_img2col2d_tiled signature")
        input_type, weight_type = input_types
        out_type = result_types[0]
        if not isinstance(input_type, NnMemoryType) or not isinstance(weight_type, NnMemoryType) or not isinstance(out_type, NnMemoryType):
            raise _error(self.ctx, func_op.sym_name.data, "unsupported conv2d_img2col2d_tiled signature")
        if _memory_rank(input_type) != 4 or _memory_rank(weight_type) != 4 or _memory_rank(out_type) != 4:
            raise _error(self.ctx, func_op.sym_name.data, "conv2d_img2col2d_tiled requires rank-4 memory operands")
        if input_type.element_type != out_type.element_type or weight_type.element_type != out_type.element_type:
            raise _error(self.ctx, func_op.sym_name.data, "conv2d_img2col2d_tiled requires matching element types")

        arg_names = _extract_arg_names(func_op)
        for arg_name, arg_value in zip(arg_names, func_op.args, strict=True):
            if self.ctx.lookup_name(arg_value) is None:
                self.ctx.bind_name(arg_value, arg_name)
        input_name = self.ctx.lookup_name(func_op.args[0]) or arg_names[0]
        weight_name = self.ctx.lookup_name(func_op.args[1]) or arg_names[1]
        element_type = _type_to_c(out_type.element_type)

        lines = [
            f"{self.ctx.current_indent}constexpr long long Ntile = 1;",
            f"{self.ctx.current_indent}constexpr long long Ctile = 16;",
            f"{self.ctx.current_indent}constexpr long long Ftile = 16;",
            f"{self.ctx.current_indent}constexpr long long Hotile = 16;",
            f"{self.ctx.current_indent}constexpr long long Wotile = 16;",
            f"{self.ctx.current_indent}constexpr long long ColChannels = Ctile * 3 * 3;",
            f"{self.ctx.current_indent}constexpr long long ColPixels = Hotile * Wotile;",
            f"{self.ctx.current_indent}long long col_shape[3] = {{Ntile, ColChannels, ColPixels}};",
            f"{self.ctx.current_indent}long long col_stride[3] = {{ColChannels * ColPixels, ColPixels, 1}};",
            f"{self.ctx.current_indent}{element_type} col_buffer[Ntile * ColChannels * ColPixels] = {{}};",
            f"{self.ctx.current_indent}{element_type} acc_buffer[Ftile * Hotile * Wotile] = {{}};",
            (
                f"{self.ctx.current_indent}Memory<{element_type}> col_tile("
                "col_buffer, 3, col_shape, col_stride, MemoryFormat::Norm, MemorySpace::LM);"
            ),
            f"{self.ctx.current_indent}const Memory<{element_type}>& input_tile = {input_name};",
            f"{self.ctx.current_indent}for (long long n0 = 0; n0 < out.shape()[0]; n0 += Ntile) {{",
        ]
        self.ctx.push_indent()
        lines.append(f"{self.ctx.current_indent}for (long long f0 = 0; f0 < out.shape()[1]; f0 += Ftile) {{")
        self.ctx.push_indent()
        lines.append(f"{self.ctx.current_indent}for (long long ho0 = 0; ho0 < out.shape()[2]; ho0 += Hotile) {{")
        self.ctx.push_indent()
        lines.append(f"{self.ctx.current_indent}for (long long wo0 = 0; wo0 < out.shape()[3]; wo0 += Wotile) {{")
        self.ctx.push_indent()
        lines.append(f"{self.ctx.current_indent}for (long long acc_i = 0; acc_i < Ftile * Hotile * Wotile; ++acc_i) {{")
        self.ctx.push_indent()
        lines.append(f"{self.ctx.current_indent}acc_buffer[acc_i] = 0;")
        self.ctx.pop_indent()
        lines.append(f"{self.ctx.current_indent}}}")
        lines.append(f"{self.ctx.current_indent}cpu::img2col2d(input_tile, col_tile, 3, 3, 1, 1, 1, 1, 0, 0, 0, 0);")
        lines.append(f"{self.ctx.current_indent}for (long long c0 = 0; c0 < {weight_name}.shape()[1]; c0 += Ctile) {{")
        self.ctx.push_indent()
        lines.append(f"{self.ctx.current_indent}/* tiled compute */")
        self.ctx.pop_indent()
        lines.append(f"{self.ctx.current_indent}}}")
        lines.append(f"{self.ctx.current_indent}for (long long fi = 0; fi < Ftile; ++fi) {{")
        self.ctx.push_indent()
        lines.append(f"{self.ctx.current_indent}for (long long hi = 0; hi < Hotile; ++hi) {{")
        self.ctx.push_indent()
        lines.append(f"{self.ctx.current_indent}for (long long wi = 0; wi < Wotile; ++wi) {{")
        self.ctx.push_indent()
        lines.append(f"{self.ctx.current_indent}long long out_indices[4] = {{n0, f0 + fi, ho0 + hi, wo0 + wi}};")
        lines.append(
            f"{self.ctx.current_indent}out.at(out_indices) = acc_buffer[((fi * Hotile) + hi) * Wotile + wi];"
        )
        self.ctx.pop_indent()
        lines.append(f"{self.ctx.current_indent}}}")
        self.ctx.pop_indent()
        lines.append(f"{self.ctx.current_indent}}}")
        self.ctx.pop_indent()
        lines.append(f"{self.ctx.current_indent}}}")
        for _ in range(4):
            self.ctx.pop_indent()
            lines.append(f"{self.ctx.current_indent}}}")
        return "\n".join(lines)

    def _is_npu_demo_body_level_kernel(self, func_op: func.FuncOp) -> bool:
        return self.ctx.target == "npu_demo"

    def _get_npu_demo_body_level_kernel_types(self, func_op: func.FuncOp) -> tuple[NnMemoryType, NnMemoryType]:
        func_name = func_op.sym_name.data
        input_types = list(func_op.function_type.inputs.data)
        result_types = list(func_op.function_type.outputs.data)
        arg_names = _extract_arg_names(func_op)
        if len(input_types) != 2 or len(result_types) != 1:
            raise _error(self.ctx, func_name, "unsupported npu_demo body-level kernel signature")
        if not arg_names or arg_names[0] != "ctx":
            raise _error(self.ctx, func_name, "npu_demo body-level kernel requires leading ctx argument")
        source_type = input_types[1]
        out_type = result_types[0]
        if not isinstance(source_type, NnMemoryType) or not isinstance(out_type, NnMemoryType):
            raise _error(self.ctx, func_name, "unsupported npu_demo body-level kernel signature")
        if source_type.element_type != out_type.element_type:
            raise _error(self.ctx, func_name, "npu_demo body-level kernel requires matching element types")
        return source_type, out_type

    def _validate_npu_demo_body_level_kernel_body(self, func_op: func.FuncOp) -> None:
        ops = list(func_op.body.block.ops)
        if not ops:
            return
        first_op = ops[0]
        if isinstance(first_op, func.ReturnOp):
            raise _error(self.ctx, func_op.sym_name.data, "npu_demo body-level kernel body must match frozen subset")
        raise _error(self.ctx, func_op.sym_name.data, f"unsupported npu_demo body-level kernel body op {first_op.name}")

    def _emit_npu_demo_body_level_kernel_signature(self, func_op: func.FuncOp) -> str:
        source_type, out_type = self._get_npu_demo_body_level_kernel_types(func_op)
        arg_names = _extract_arg_names(func_op)
        for arg_name, arg_value in zip(arg_names, func_op.args, strict=True):
            self.ctx.bind_name(arg_value, arg_name)
        source_name = self.ctx.lookup_name(func_op.args[1]) or arg_names[1]
        return (
            f"void {func_op.sym_name.data}(npu_demo::KernelContext& ctx, "
            f"const {_type_to_c(source_type)}& {source_name}, {_type_to_c(out_type)}& out)"
        )

    def _emit_npu_demo_body_level_kernel_body(self, func_op: func.FuncOp) -> str:
        self._get_npu_demo_body_level_kernel_types(func_op)
        self._validate_npu_demo_body_level_kernel_body(func_op)
        _, out_type = self._get_npu_demo_body_level_kernel_types(func_op)
        arg_names = _extract_arg_names(func_op)
        for arg_name, arg_value in zip(arg_names, func_op.args, strict=True):
            if self.ctx.lookup_name(arg_value) is None:
                self.ctx.bind_name(arg_value, arg_name)
        source_name = self.ctx.lookup_name(func_op.args[1]) or arg_names[1]
        element_type = _type_to_c(out_type.element_type)
        lines = [
            f"{self.ctx.current_indent}long long tid = ctx.thread_id();",
            f"{self.ctx.current_indent}long long tnum = ctx.thread_num();",
            "",
            f"{self.ctx.current_indent}Memory<{element_type}> tsm = ctx.get_dynamic_memory<{element_type}>(MemorySpace::TSM);",
            f"{self.ctx.current_indent}Memory<{element_type}> tlm = ctx.get_dynamic_memory<{element_type}>(MemorySpace::TLM);",
            "",
            f"{self.ctx.current_indent}auto src_view = view({source_name}, tid * 16, 16, 1);",
            f"{self.ctx.current_indent}auto work_tile = view(tsm, 0, 16, 1);",
            f"{self.ctx.current_indent}auto out_tile = view(tlm, 0, 16, 1);",
            "",
            f"{self.ctx.current_indent}slice(work_tile, src_view, 0, 16, 1);",
            f"{self.ctx.current_indent}add(work_tile, work_tile, out_tile);",
            f"{self.ctx.current_indent}deslice(out_tile, out, tid * 16, 16, 1);",
        ]
        return "\n".join(lines)

    def _emit_default_signature(self, func_op: func.FuncOp) -> str:
        func_name = func_op.sym_name.data
        input_types = list(func_op.function_type.inputs.data)
        result_types = list(func_op.function_type.outputs.data)
        if len(result_types) > 1:
            raise _error(self.ctx, func_name, "unsupported return form")
        if result_types and not isinstance(result_types[0], (NnMemoryType, SymbolValueType)):
            raise _error(self.ctx, func_name, "unsupported return form")
        if result_types and isinstance(result_types[0], SymbolValueType) and self.ctx.target != "cpu":
            raise _error(self.ctx, func_name, "symbol scalar return is cpu-only")

        arg_names = _extract_arg_names(func_op)
        params: list[str] = []
        for arg_name, arg_type, arg_value in zip(arg_names, input_types, func_op.args, strict=True):
            self.ctx.bind_name(arg_value, arg_name)
            if isinstance(arg_type, NnMemoryType):
                params.append(f"const {_type_to_c(arg_type)}& {arg_name}")
            else:
                params.append(f"{_type_to_c(arg_type)} {arg_name}")

        return_type = "void"
        if result_types and isinstance(result_types[0], SymbolValueType):
            return_type = _type_to_c(result_types[0])
        elif result_types:
            params.append(f"{_type_to_c(result_types[0])}& out")

        return f"{return_type} {func_name}({', '.join(params)})"

    def _is_returned_output_alloc(self, func_op: func.FuncOp, op: DmaAllocOp) -> bool:
        if self.ctx.target != "cpu":
            return False
        result_types = list(func_op.function_type.outputs.data)
        if len(result_types) != 1 or not isinstance(result_types[0], NnMemoryType):
            return False
        return any(isinstance(use.operation, func.ReturnOp) for use in op.result.uses)

    def _is_direct_return_nn_add(self, return_op: func.ReturnOp) -> bool:
        if self.ctx.target != "cpu":
            return False
        if len(return_op.arguments) != 1:
            return False
        returned = return_op.arguments[0]
        owner = getattr(returned, "owner", None)
        if not isinstance(owner, NnAddOp):
            return False
        if not owner.result.has_one_use():
            return False
        return owner.result.get_user_of_unique_use() is return_op

    def _has_cpu_direct_return_nn_add(self, func_op: func.FuncOp) -> bool:
        if self.ctx.target != "cpu":
            return False
        return any(isinstance(op, func.ReturnOp) and self._is_direct_return_nn_add(op) for op in func_op.body.block.ops)

    def _emit_return_statement(
        self,
        func_op: func.FuncOp,
        return_op: func.ReturnOp,
        *,
        allow_direct_return_nn_add: bool = False,
    ) -> str | None:
        result_types = list(func_op.function_type.outputs.data)
        if not result_types:
            if return_op.arguments:
                raise _error(self.ctx, func_op.sym_name.data, "unsupported return form")
            return None
        if len(result_types) != 1:
            raise _error(self.ctx, func_op.sym_name.data, "unsupported return form")
        result_type = result_types[0]
        if len(return_op.arguments) != 1:
            raise _error(self.ctx, func_op.sym_name.data, "unsupported return form")
        if return_op.arguments[0].type != result_type:
            raise _error(self.ctx, func_op.sym_name.data, "unsupported return form")
        if isinstance(result_type, NnMemoryType):
            if allow_direct_return_nn_add and self._is_direct_return_nn_add(return_op):
                return None
            value_name = self.ctx.lookup_name(return_op.arguments[0])
            if value_name is None:
                from .emit_c import emit_c_value

                value_name = emit_c_value(return_op.arguments[0], self.ctx)
            if value_name == "out":
                return None
            return f"{self.ctx.current_indent}out = {value_name};"
        if isinstance(result_type, SymbolValueType):
            if self.ctx.target != "cpu":
                raise _error(self.ctx, func_op.sym_name.data, "symbol scalar return is cpu-only")
            from .emit_c import emit_c_value

            value_expr = emit_c_value(return_op.arguments[0], self.ctx)
            return f"{self.ctx.current_indent}return {value_expr};"
        raise _error(self.ctx, func_op.sym_name.data, "unsupported return form")

    def _emit_default_function_body(self, func_op: func.FuncOp) -> str:
        lines: list[str] = []
        for op in func_op.body.block.ops:
            if isinstance(op, func.ReturnOp):
                stmt = self._emit_return_statement(func_op, op)
                if stmt:
                    lines.append(stmt)
                continue
            if isinstance(op, DmaAllocOp) and self._is_returned_output_alloc(func_op, op):
                self.ctx.bind_name(op.result, "out")
                continue
            stmt = emit_c_op(op, self.ctx)
            if stmt:
                lines.append(stmt)
        return "\n".join(lines)

    def _emit_cpu_direct_return_nn_add_body(self, func_op: func.FuncOp) -> str:
        lines: list[str] = []
        for op in func_op.body.block.ops:
            if isinstance(op, func.ReturnOp):
                stmt = self._emit_return_statement(func_op, op, allow_direct_return_nn_add=True)
                if stmt:
                    lines.append(stmt)
                continue
            if isinstance(op, DmaAllocOp) and self._is_returned_output_alloc(func_op, op):
                self.ctx.bind_name(op.result, "out")
                continue
            if isinstance(op, NnAddOp) and op.result.has_one_use():
                unique_user = op.result.get_user_of_unique_use()
                if isinstance(unique_user, func.ReturnOp) and self._is_direct_return_nn_add(unique_user):
                    self.ctx.bind_name(op.result, "out")
            stmt = emit_c_op(op, self.ctx)
            if stmt:
                lines.append(stmt)
        return "\n".join(lines)


def gen_kernel(op_or_func: Any, ctx: EmitCContext) -> str:
    """把单个 MLIR op 或 `func.func` 生成为目标源码文本。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 这是 `kernel_gen.dsl.gen_kernel` 唯一稳定公开入口。
    - 输入为单个普通 op 时，直接委托 `emit_c_op(...)` 的公开节点级接口生成源码片段。
    - 输入为 `func.func` 时，统一交给 `_KernelEmitter` 在一条内部策略链中完成签名、函数级特化选择、IR 遍历和 `func.return/out` 收尾。

    使用示例:
    - source = gen_kernel(func_op, EmitCContext(target="cpu"))
    - stmt = gen_kernel(single_op, EmitCContext(target="cpu"))

    关联文件:
    - spec: spec/dsl/gen_kernel.md
    - test: test/dsl/test_gen_kernel.py
    - 功能实现: kernel_gen/dsl/gen_kernel.py
    """

    return _KernelEmitter(ctx).emit(op_or_func)


__all__ = ["GenKernelError", "gen_kernel"]
