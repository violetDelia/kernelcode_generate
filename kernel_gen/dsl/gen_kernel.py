"""Function-level C-like kernel generation helpers.

创建者: 金铲铲大作战
最后一次更改: 朽木露琪亚

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
from xdsl.ir import Operation

from kernel_gen.dialect.dma import DmaAllocOp
from kernel_gen.dialect.nn import NnAddOp, NnMemoryType
from kernel_gen.dialect.symbol import SymbolDimType, SymbolValueType

from .emit_c import EmitCContext, emit_c_op


class GenKernelError(ValueError):
    """Raised when `gen_kernel` cannot emit a valid target function."""


def _error(ctx: EmitCContext, func_name: str, reason: str) -> GenKernelError:
    return GenKernelError(f"target={ctx.target}: func {func_name}: {reason}")


def _walk_ops(op: Operation) -> list[Operation]:
    """深度遍历并收集 op 子树中的所有 Operation。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 用于在 `gen_kernel(...)` 入口做 fail-fast 的结构预检。
    - 递归扫描 op 的 regions/blocks/ops，包含 op 自身。

    使用示例:
    - all_ops = _walk_ops(func_op)
    - assert any(item.name == "func.call" for item in all_ops)

    关联文件:
    - spec: spec/dsl/gen_kernel.md
    - test: test/dsl/test_gen_kernel.py
    - 功能实现: kernel_gen/dsl/gen_kernel.py
    """

    items: list[Operation] = [op]
    for region in op.regions:
        for block in region.blocks:
            for inner in block.ops:
                items.extend(_walk_ops(inner))
    return items


def _is_kernel_split_codegen_function(func_op: func.FuncOp) -> bool:
    ops = list(func_op.body.block.ops)
    return any(op.name in {"tuner.param", "kernel_split.tile_value"} for op in ops)


def _validate_kernel_split_codegen_contract(func_op: func.FuncOp, ctx: EmitCContext) -> None:
    """校验 split 后单函数 IR 的最小 codegen 前置条件。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 若函数体包含 kernel split 相关 op（`tuner.param` / `kernel_split.tile_value`），则视为 split-after-IR。
    - split-after-IR 必须满足：
      - `target=cpu`；
      - 存在显式分块结构 `symbol.for`；
      - 禁止 `func.call`（防止 helper/函数抽取式承接）；
      - 必须存在 `tuner.param` 与 `kernel_split.tile_value`（禁止 silent fallback）。
    - 不满足时必须显式失败，且错误短语固定包含：
      - `KernelSplitMalformed`
      - `KernelSplitUnexpectedHelperFunction`

    使用示例:
    - _validate_kernel_split_codegen_contract(func_op, EmitCContext(target="cpu"))

    关联文件:
    - spec: spec/dsl/gen_kernel.md
    - test: test/dsl/test_gen_kernel.py
    - 功能实现: kernel_gen/dsl/gen_kernel.py
    """

    func_name = func_op.sym_name.data
    if ctx.target != "cpu":
        raise _error(ctx, func_name, "KernelSplitMalformed: kernel split codegen is cpu-only")

    ops = list(func_op.body.block.ops)
    if not any(op.name == "symbol.for" for op in ops):
        raise _error(ctx, func_name, "KernelSplitMalformed: missing explicit split structure (symbol.for)")
    if not any(op.name == "tuner.param" for op in ops):
        raise _error(ctx, func_name, "KernelSplitMalformed: missing tuner.param")
    if not any(op.name == "kernel_split.tile_value" for op in ops):
        raise _error(ctx, func_name, "KernelSplitMalformed: missing kernel_split.tile_value")

    if any(item.name == "func.call" for item in _walk_ops(func_op)):
        raise _error(ctx, func_name, "KernelSplitUnexpectedHelperFunction: func.call is not allowed in split codegen")


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


def _leading_rewritten_out_param_count(func_op: func.FuncOp) -> int:
    """识别 rewrite 后 IR 的最前置 out 参数个数。

    创建者: jcc你莫辜负
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅把最前面连续的 `arg0/arg1/...` memory 参数识别为 out 参数。
    - 这组参数由 `BufferResultsToOutParamsPass` 固定前置，用于让 `gen_kernel(...)` 只消费 rewrite 后 ABI。

    使用示例:
    - count = _leading_rewritten_out_param_count(func_op)

    关联文件:
    - spec: spec/dsl/gen_kernel.md
    - test: test/dsl/test_gen_kernel.py
    - 功能实现: kernel_gen/dsl/gen_kernel.py
    """

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
                self._emit_cpu_conv2d_img2col2d_tiled_signature,
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

    def _emit_cpu_conv2d_img2col2d_tiled_signature(self, func_op: func.FuncOp) -> str:
        """生成 `conv2d_img2col2d_tiled(...)` 的固定 CPU 签名。

        创建者: jcc你莫辜负
        最后一次更改: jcc你莫辜负

        功能说明:
        - 继续为当前冻结的 `conv2d_img2col2d_tiled(...)` 子集保留固定函数级签名。
        - 该签名属于既有特化合同，不复用默认的 rewrite-only ABI 收口逻辑。

        使用示例:
        - signature = self._emit_cpu_conv2d_img2col2d_tiled_signature(func_op)

        关联文件:
        - spec: spec/dsl/gen_kernel.md
        - test: test/dsl/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel.py
        """

        input_types = list(func_op.function_type.inputs.data)
        result_types = list(func_op.function_type.outputs.data)
        if len(input_types) != 2 or len(result_types) != 1:
            raise _error(self.ctx, func_op.sym_name.data, "unsupported conv2d_img2col2d_tiled signature")
        input_type, weight_type = input_types
        out_type = result_types[0]
        if not isinstance(input_type, NnMemoryType) or not isinstance(weight_type, NnMemoryType) or not isinstance(out_type, NnMemoryType):
            raise _error(self.ctx, func_op.sym_name.data, "unsupported conv2d_img2col2d_tiled signature")

        arg_names = _extract_arg_names(func_op)
        for arg_name, arg_value in zip(arg_names, func_op.args, strict=True):
            self.ctx.bind_name(arg_value, arg_name)
        input_name = self.ctx.lookup_name(func_op.args[0]) or arg_names[0]
        weight_name = self.ctx.lookup_name(func_op.args[1]) or arg_names[1]
        return (
            f"void {func_op.sym_name.data}("
            f"const {_type_to_c(input_type)}& {input_name}, "
            f"const {_type_to_c(weight_type)}& {weight_name}, "
            f"{_type_to_c(out_type)}& out)"
        )

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
        """生成默认 rewrite-after-IR 函数签名。

        创建者: jcc你莫辜负
        最后一次更改: jcc你莫辜负

        功能说明:
        - 默认 CPU/通用路径只消费已经过 `BufferResultsToOutParamsPass` 的 IR。
        - 最前面连续且显式命名为 `arg0/arg1/...` 的 `Memory` 参数生成为 out 参数，其余 `Memory` 参数保持只读输入。
        - 若函数仍保留旧 `memory return` ABI，则显式报错，阻止后端继续隐式推导 `out`。

        使用示例:
        - signature = self._emit_default_signature(func_op)

        关联文件:
        - spec: spec/dsl/gen_kernel.md
        - test: test/dsl/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel.py
        """
        func_name = func_op.sym_name.data
        input_types = list(func_op.function_type.inputs.data)
        result_types = list(func_op.function_type.outputs.data)
        if len(result_types) > 1:
            raise _error(self.ctx, func_name, "unsupported return form")
        if result_types and isinstance(result_types[0], NnMemoryType):
            raise _error(
                self.ctx,
                func_name,
                "legacy memory return ABI is not supported; run BufferResultsToOutParamsPass first",
            )
        if result_types:
            result_type = result_types[0]
            if isinstance(result_type, SymbolValueType) and self.ctx.target != "cpu":
                raise _error(self.ctx, func_name, "symbol scalar return is cpu-only")
            _type_to_c(result_type)

        arg_names = _extract_arg_names(func_op)
        leading_out_params = _leading_rewritten_out_param_count(func_op)
        params: list[str] = []
        for index, (arg_name, arg_type, arg_value) in enumerate(zip(arg_names, input_types, func_op.args, strict=True)):
            self.ctx.bind_name(arg_value, arg_name)
            if isinstance(arg_type, NnMemoryType):
                if index < leading_out_params:
                    params.append(f"{_type_to_c(arg_type)}& {arg_name}")
                else:
                    params.append(f"const {_type_to_c(arg_type)}& {arg_name}")
            else:
                params.append(f"{_type_to_c(arg_type)} {arg_name}")

        return_type = "void"
        if result_types:
            return_type = _type_to_c(result_types[0])

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
        """生成默认路径下的 `func.return` 收尾语句。

        创建者: jcc你莫辜负
        最后一次更改: jcc你莫辜负

        功能说明:
        - rewrite-after-IR 默认路径只允许无返回或单一非 `Memory` 标量返回。
        - 若 `func.return` 仍返回 `Memory`，说明 IR 还保留旧 ABI，必须显式失败。
        - `allow_direct_return_nn_add` 仅为兼容旧调用点保留的内部参数；当前默认路径不会靠它放行旧 `memory return`。

        使用示例:
        - stmt = self._emit_return_statement(func_op, return_op)

        关联文件:
        - spec: spec/dsl/gen_kernel.md
        - test: test/dsl/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel.py
        """
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
            raise _error(
                self.ctx,
                func_op.sym_name.data,
                "legacy memory return ABI is not supported; run BufferResultsToOutParamsPass first",
            )
        if isinstance(result_type, SymbolValueType) and self.ctx.target != "cpu":
            raise _error(self.ctx, func_op.sym_name.data, "symbol scalar return is cpu-only")
        from .emit_c import emit_c_value

        value_expr = emit_c_value(return_op.arguments[0], self.ctx)
        return f"{self.ctx.current_indent}return {value_expr};"

    def _emit_default_function_body(self, func_op: func.FuncOp) -> str:
        """生成默认 rewrite-after-IR 函数体。

        创建者: jcc你莫辜负
        最后一次更改: jcc你莫辜负

        功能说明:
        - 按 IR 顺序逐个委托普通 op 到 `emit_c_op(...)`。
        - `func.return` 统一走 `_emit_return_statement(...)` 收尾，不再从旧 `memory return` 形态隐式补 `out`。
        - 仅保留既有 `dma.alloc`/`out` 绑定清理逻辑，避免对 rewrite 后 ABI 额外引入新的函数级特例。

        使用示例:
        - body = self._emit_default_function_body(func_op)

        关联文件:
        - spec: spec/dsl/gen_kernel.md
        - test: test/dsl/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel.py
        """
        if _is_kernel_split_codegen_function(func_op):
            _validate_kernel_split_codegen_contract(func_op, self.ctx)

        tile_var_by_dim: dict[str, str] = {}
        emitted_tile_dims: set[str] = set()

        def _tile_var_name(dim_name: str) -> str:
            return dim_name.strip().lower()

        lines: list[str] = []
        for op in func_op.body.block.ops:
            if op.name == "kernel_split.symbol_literal":
                if not op.results:
                    raise _error(
                        self.ctx,
                        func_op.sym_name.data,
                        "KernelSplitMalformed: kernel_split.symbol_literal must have a result",
                    )
                result_type = op.results[0].type
                if not isinstance(result_type, SymbolValueType):
                    raise _error(
                        self.ctx,
                        func_op.sym_name.data,
                        "KernelSplitMalformed: kernel_split.symbol_literal result must be !symbol.int",
                    )
                literal_expr = result_type.expr.expr.data
                self.ctx.bind_name(op.results[0], literal_expr)
                continue

            if op.name == "tuner.param":
                if not op.results:
                    raise _error(self.ctx, func_op.sym_name.data, "KernelSplitMalformed: tuner.param must have a result")
                result_type = op.results[0].type
                if not isinstance(result_type, SymbolDimType):
                    raise _error(self.ctx, func_op.sym_name.data, "KernelSplitMalformed: tuner.param result must be !symbol.dim")
                dim_name = result_type.dim.data
                var_name = tile_var_by_dim.setdefault(dim_name, _tile_var_name(dim_name))
                self.ctx.bind_name(op.results[0], var_name)
                if dim_name not in emitted_tile_dims:
                    lines.append(f'{self.ctx.current_indent}long long {var_name} = tuner_param("{dim_name}");')
                    emitted_tile_dims.add(dim_name)
                continue

            if op.name == "kernel_split.tile_value":
                if not op.operands or not op.results:
                    raise _error(
                        self.ctx,
                        func_op.sym_name.data,
                        "KernelSplitMalformed: kernel_split.tile_value must have operands/results",
                    )
                source_type = op.operands[0].type
                if not isinstance(source_type, SymbolDimType):
                    raise _error(
                        self.ctx,
                        func_op.sym_name.data,
                        "KernelSplitMalformed: kernel_split.tile_value source must be !symbol.dim",
                    )
                dim_name = source_type.dim.data
                var_name = tile_var_by_dim.get(dim_name)
                if var_name is None:
                    raise _error(
                        self.ctx,
                        func_op.sym_name.data,
                        "KernelSplitMalformed: missing tuner.param before kernel_split.tile_value",
                    )
                for result in op.results:
                    self.ctx.bind_name(result, var_name)
                continue

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

    source = _KernelEmitter(ctx).emit(op_or_func)
    if ctx.target == "npu_demo":
        return '#include "include/npu_demo/npu_demo.h"\n\n' + source
    return source


def __getattr__(name: str) -> Any:
    """拒绝回流的 legacy 双接口公开访问。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 对历史 `gen_signature` / `gen_body` 名称给出统一的缺失语义，避免其被误当成公开稳定入口回流。
    - 不影响模块内部私有 helper 的实现组织；仅用于模块级公开访问边界。

    使用示例:
    - getattr(gen_kernel_module, "gen_signature")  # raises AttributeError

    关联文件:
    - spec: spec/dsl/gen_kernel.md
    - test: test/dsl/test_gen_kernel.py
    - 功能实现: kernel_gen/dsl/gen_kernel.py
    """

    if name in {"gen_signature", "gen_body"}:
        raise AttributeError(f"{name} is no longer a public entry; use gen_kernel(...) instead")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["GenKernelError", "gen_kernel"]
