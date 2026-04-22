"""Function-level C-like kernel generation helpers.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

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
import re
from typing import Callable
from typing import Any

from xdsl.dialects import func
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
from xdsl.ir import BlockArgument, Operation, SSAValue

from kernel_gen.dialect.arch import ArchBarrierOp, ArchGetDynamicMemoryOp, ArchGetThreadIdOp, ArchGetThreadNumOp, ArchLaunchOp
from kernel_gen.dialect.dma import DmaAllocOp, DmaBroadcastOp, DmaCastOp, DmaCopyOp, DmaDesliceOp, DmaFillOp, DmaLoadOp, DmaReshapeOp, DmaSliceOp, DmaStoreOp, DmaTransposeOp, DmaViewOp
from kernel_gen.dialect.nn import NnAddOp, NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolConstOp, SymbolValueType
from kernel_gen.target import registry as target_registry

from .emit_c import EmitCContext, emit_c_op, emit_c_value


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


def _is_tile_codegen_function(func_op: func.FuncOp) -> bool:
    ops = _walk_ops(func_op)
    return any(
        (
            op.name == "tuner.param"
            and op.results
            and isinstance(op.results[0].type, SymbolValueType)
        )
        or "tile.analysis" in op.attributes
        or "tile.tile_exprs" in op.attributes
        for op in ops
    )


def _validate_tile_codegen_contract(func_op: func.FuncOp, ctx: EmitCContext) -> None:
    """校验 tile after-IR 单函数 codegen 前置条件。

    创建者: 小李飞刀
    最后一次更改: 金铲铲大作战

    功能说明:
    - tile after-IR 只接受 `target=cpu`。
    - 必须保留显式 `symbol.for`，并通过 `tuner.param : !symbol.int<"...">` 绑定 tile 因子。
    - 不允许回退到 `kernel_split.*` / `tile.step_value` / `tile.symbol_literal` 旧桥接口径。

    使用示例:
    - _validate_tile_codegen_contract(func_op, EmitCContext(target="cpu"))

    关联文件:
    - spec: [spec/dsl/gen_kernel.md](spec/dsl/gen_kernel.md)
    - test: [test/dsl/test_gen_kernel.py](test/dsl/test_gen_kernel.py)
    - 功能实现: [kernel_gen/dsl/gen_kernel.py](kernel_gen/dsl/gen_kernel.py)
    """

    func_name = func_op.sym_name.data
    if ctx.target != "cpu":
        raise _error(ctx, func_name, "TileCodegenMalformed: tile codegen is cpu-only")

    ops = list(func_op.body.block.ops)
    if not any(op.name == "symbol.for" for op in ops):
        raise _error(ctx, func_name, "TileCodegenMalformed: missing explicit tile loop (symbol.for)")
    if not any(op.name == "tuner.param" and op.results and isinstance(op.results[0].type, SymbolValueType) for op in ops):
        raise _error(ctx, func_name, "TileCodegenMalformed: missing tuner.param")
    if any(op.name in {"kernel_split.tile_value", "tile.step_value", "kernel_split.symbol_literal", "tile.symbol_literal"} for op in ops):
        raise _error(ctx, func_name, "TileCodegenMalformed: legacy bridge ops are not allowed")
    if any(item.name == "func.call" for item in _walk_ops(func_op)):
        raise _error(ctx, func_name, "TileCodegenUnexpectedHelperFunction: func.call is not allowed in tile codegen")


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


def _block_arg_index(value: object) -> int | None:
    if isinstance(value, BlockArgument):
        return value.index
    return None


def _kernel_out_operand(value_op: Operation) -> SSAValue | None:
    """返回 codegen 视角下的 kernel 输出 operand。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 当前公开 kernel 合同统一把第一个 `nn.memory` operand 视作 out。
    - 对只读 expectation 中遗留的 `kernel.binary_elewise(lhs, rhs, out)` 文本，
      按 block argument 位置做最小规整，继续把真正的 out 识别为最前置参数。

    使用示例:
    - out_value = _kernel_out_operand(op)

    关联文件:
    - spec: spec/dsl/gen_kernel.md
    - test: test/dsl/test_gen_kernel.py
    - 功能实现: kernel_gen/dsl/gen_kernel.py
    """

    candidate_arity = {
        "kernel.binary_elewise": 3,
        "kernel.matmul": 3,
        "kernel.exp": 2,
        "kernel.reduce": 2,
        "kernel.reduce_min": 2,
        "kernel.img2col1d": 2,
        "kernel.img2col2d": 2,
        "kernel.select": 4,
    }.get(value_op.name)
    if candidate_arity is None or len(value_op.operands) < candidate_arity:
        if not value_op.operands:
            return None
        candidate = SSAValue.get(value_op.operands[0])
        return candidate if isinstance(candidate.type, NnMemoryType) else None

    candidates = [SSAValue.get(value_op.operands[index]) for index in range(candidate_arity)]
    if not all(isinstance(candidate.type, NnMemoryType) for candidate in candidates):
        return None

    block_arg_indices = [_block_arg_index(candidate) for candidate in candidates]
    if all(index is not None for index in block_arg_indices):
        min_index = min(block_arg_indices)
        min_pos = block_arg_indices.index(min_index)
        return candidates[min_pos]
    return candidates[0]


def _leading_out_param_count_from_body(func_op: func.FuncOp) -> int:
    """从函数体推断前置 out 参数个数。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅在函数没有 `memory return`、也没有 rewrite 后显式 `arg0/arg1/...` 标记时启用。
    - 逐个检查最前面连续的 memory 参数，若它们作为 kernel/dma 写路径的 target/out 出现，则视为 out 参数。

    使用示例:
    - count = _leading_out_param_count_from_body(func_op)

    关联文件:
    - spec: spec/dsl/gen_kernel.md
    - test: test/dsl/test_gen_kernel.py
    - 功能实现: kernel_gen/dsl/gen_kernel.py
    """

    out_args: set[SSAValue] = set()
    for op in _walk_ops(func_op):
        if op.name.startswith("kernel."):
            out_value = _kernel_out_operand(op)
            if out_value is not None:
                out_args.add(out_value)
        elif isinstance(op, DmaDesliceOp):
            out_args.add(SSAValue.get(op.target))

    count = 0
    for arg in func_op.args:
        if not isinstance(arg.type, NnMemoryType):
            break
        if arg not in out_args:
            break
        count += 1
    return count


def _memory_space_to_c(space_attr: NnMemorySpaceAttr) -> str:
    """将 `nn.space` 映射为 `MemorySpace::<space>` 模板参数文本。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 为 `Memory<Space, T>` 类型生成固定的 space 模板参数。
    - 仅接受 `global/shared/local/tsm/tlm1/tlm2/tlm3`，其余值显式失败。

    使用示例:
    - space = _memory_space_to_c(NnMemorySpaceAttr.from_name("global"))
    - assert space == "MemorySpace::GM"

    关联文件:
    - spec: spec/dsl/gen_kernel.md
    - test: test/dsl/test_gen_kernel.py
    - 功能实现: kernel_gen/dsl/gen_kernel.py
    """

    space = space_attr.space.data
    mapping = {
        "global": "MemorySpace::GM",
        "shared": "MemorySpace::SM",
        "local": "MemorySpace::LM",
        "tsm": "MemorySpace::TSM",
        "tlm1": "MemorySpace::TLM1",
        "tlm2": "MemorySpace::TLM2",
        "tlm3": "MemorySpace::TLM3",
    }
    if space not in mapping:
        raise TypeError(f"unsupported nn memory space: {space}")
    return mapping[space]


def _memory_space_to_c_for_target(space_attr: NnMemorySpaceAttr, target: str) -> str:
    """将 `nn.space` 映射为目标侧的模板参数文本。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - `target=npu_demo` 时输出 `GM/SM/LM/TSM/TLM1/TLM2/TLM3`，匹配 npu_demo helper 口径。
    - 其他 target 维持 `MemorySpace::GM/SM/LM/TSM/TLM1/TLM2/TLM3` 形式。
    - 非法 space 必须显式失败。

    使用示例:
    - _memory_space_to_c_for_target(NnMemorySpaceAttr.from_name("global"), "npu_demo") == "GM"

    关联文件:
    - spec: spec/dsl/gen_kernel.md
    - test: test/dsl/test_gen_kernel.py
    - 功能实现: kernel_gen/dsl/gen_kernel.py
    """

    space = space_attr.space.data
    if target == "npu_demo":
        mapping = {
            "global": "GM",
            "shared": "SM",
            "local": "LM",
            "tsm": "TSM",
            "tlm1": "TLM1",
            "tlm2": "TLM2",
            "tlm3": "TLM3",
        }
    else:
        mapping = {
            "global": "MemorySpace::GM",
            "shared": "MemorySpace::SM",
            "local": "MemorySpace::LM",
            "tsm": "MemorySpace::TSM",
            "tlm1": "MemorySpace::TLM1",
            "tlm2": "MemorySpace::TLM2",
            "tlm3": "MemorySpace::TLM3",
        }
    if space not in mapping:
        raise TypeError(f"unsupported nn memory space: {space}")
    return mapping[space]


def _type_to_c(attr: Any) -> str:
    """将 xdsl Attribute 映射为 C 侧类型名。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 用于 `gen_kernel(...)` 的函数级签名拼装，将 IR 类型属性转换为 C/C++ 侧可用类型名。
    - 支持的类型映射清单：
      - `IntegerType(1)` -> `bool`
      - `IntegerType(N)` -> `int{N}_t` / `uint{N}_t`
      - `Float32Type` -> `float`
      - `Float64Type` -> `double`
      - `IndexType` -> `long long`
      - `NnMemoryType<T>` -> `Memory<Space, T>`（递归映射 `element_type`）
      - `SymbolValueType` -> `long long`
    - 若遇到不支持类型，将抛出 `TypeError("unsupported type: ...")`。

    使用示例:
    - from xdsl.dialects.builtin import ArrayAttr, IntAttr, f32, f64
    - from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
    - assert _type_to_c(f32) == "float"
    - assert _type_to_c(f64) == "double"
    - mem_f64 = NnMemoryType(ArrayAttr([IntAttr(2)]), ArrayAttr([IntAttr(1)]), f64, NnMemorySpaceAttr.from_name("global"))
    - assert _type_to_c(mem_f64) == "Memory<MemorySpace::GM, double>"

    关联文件:
    - spec: spec/dsl/gen_kernel.md
    - test: test/dsl/test_gen_kernel.py
    - 功能实现: kernel_gen/dsl/gen_kernel.py
    """
    if isinstance(attr, IntegerType):
        if attr.width.data == 1:
            return "bool"
        prefix = "uint" if attr.signedness.data == Signedness.UNSIGNED else "int"
        return f"{prefix}{attr.width.data}_t"
    if isinstance(attr, Float32Type):
        return "float"
    if isinstance(attr, Float16Type):
        return "half"
    if isinstance(attr, BFloat16Type):
        return "bfloat16_t"
    if isinstance(attr, Float64Type):
        return "double"
    if isinstance(attr, IndexType):
        return "long long"
    if isinstance(attr, NnMemoryType):
        return f"Memory<{_memory_space_to_c(attr.space)}, {_type_to_c(attr.element_type)}>"
    if isinstance(attr, SymbolValueType):
        return "long long"
    raise TypeError(f"unsupported type: {attr}")


def _type_to_c_for_target(attr: Any, target: str) -> str:
    """将 xdsl Attribute 映射为目标侧的 C 类型名。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 与 `_type_to_c` 保持同样的覆盖范围，但根据 `target` 切换 memory space 文本形式。
    - `target=npu_demo` 时输出 `Memory<GM, T>` 风格。
    - 其他 target 保持 `Memory<MemorySpace::GM, T>` 风格。

    使用示例:
    - _type_to_c_for_target(f32, "cpu") == "float"
    - _type_to_c_for_target(NnMemoryType(...), "npu_demo")  # -> "Memory<GM, ...>"

    关联文件:
    - spec: spec/dsl/gen_kernel.md
    - test: test/dsl/test_gen_kernel.py
    - 功能实现: kernel_gen/dsl/gen_kernel.py
    """

    if isinstance(attr, IntegerType):
        if attr.width.data == 1:
            return "bool"
        prefix = "uint" if attr.signedness.data == Signedness.UNSIGNED else "int"
        return f"{prefix}{attr.width.data}_t"
    if isinstance(attr, Float32Type):
        return "float"
    if isinstance(attr, Float16Type):
        return "half"
    if isinstance(attr, BFloat16Type):
        return "bfloat16_t"
    if isinstance(attr, Float64Type):
        return "double"
    if isinstance(attr, IndexType):
        return "long long"
    if isinstance(attr, NnMemoryType):
        space = _memory_space_to_c_for_target(attr.space, target)
        return f"Memory<{space}, {_type_to_c_for_target(attr.element_type, target)}>"
    if isinstance(attr, SymbolValueType):
        return "S_INT" if target == "npu_demo" else "long long"
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

    def _type_to_c(self, attr: Any) -> str:
        """按当前 target 生成类型名。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 统一收口 `_type_to_c_for_target`，避免在多处重复判断 target。
        - 仅影响 `gen_kernel` 的函数级签名与辅助输出。

        使用示例:
        - c_type = self._type_to_c(mem_type)

        关联文件:
        - spec: spec/dsl/gen_kernel.md
        - test: test/dsl/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel.py
        """

        return _type_to_c_for_target(attr, self.ctx.target)

    def _normalize_cpu_memory_stmt(self, stmt: str) -> str:
        """规范化 CPU 侧 `Memory<T>` 生成语句为模板化 `Memory<MemorySpace::GM, T>` 形式。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 把 `emit_c` 输出的 `Memory<T>` 类型声明改写为 `Memory<MemorySpace::GM, T>`。
        - 清理 `Memory(..., MemorySpace::GM)` 的构造参数尾项，避免冗余实参导致编译失败。

        使用示例:
        - stmt = self._normalize_cpu_memory_stmt(stmt)

        关联文件:
        - spec: spec/dsl/gen_kernel.md
        - test: test/dsl/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel.py
        """

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

    def emit(self, op_or_func: Any) -> str:
        if isinstance(op_or_func, ModuleOp):
            return self._emit_module(op_or_func)
        if isinstance(op_or_func, func.FuncOp):
            return self._emit_func(op_or_func)
        if isinstance(op_or_func, func.ReturnOp):
            raise GenKernelError(f"target={self.ctx.target}: func.return/out binding must be emitted in function main flow")
        return emit_c_op(op_or_func, self.ctx)

    def _emit_module(self, module_op: ModuleOp) -> str:
        """发射 `target=npu_demo` 的受控 `builtin.module` 双函数源码。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 仅对 `target="npu_demo"` 放行受控 `builtin.module` 子集。
        - 允许 module 携带 helper `func.func`，并按 module 中的出现顺序输出源码。
        - wrapper 仍必须能被唯一 `arch.launch` 识别，body / wrapper 之外的 helper 继续走通用函数发射。

        使用示例:
        - source = _KernelEmitter(EmitCContext(target="npu_demo")).emit(module_op)

        关联文件:
        - spec: spec/dsl/gen_kernel.md
        - test: test/dsl/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel.py
        """

        if self.ctx.target != "npu_demo":
            raise GenKernelError(f"target={self.ctx.target}: func <module>: builtin.module is only supported for target=npu_demo")

        plain_func = self._get_npu_demo_plain_func(module_op)
        if plain_func is not None:
            return self._emit_func(plain_func)

        body_func, wrapper_func = self._classify_npu_demo_launch_module(module_op)
        emitted: list[str] = [self._emit_npu_demo_launch_body_declaration(body_func)]
        for top_op in module_op.ops:
            if not isinstance(top_op, func.FuncOp):
                raise _error(self.ctx, "<module>", "npu_demo launch module must contain only func.func")
            if top_op is body_func:
                emitted.append(self._emit_npu_demo_launch_body_function(body_func))
                continue
            if top_op is wrapper_func:
                emitted.append(self._emit_npu_demo_launch_wrapper_function(wrapper_func, body_func))
                continue
            emitted.append(self._emit_func(top_op))
        return "\n\n".join(emitted)

    def _get_npu_demo_plain_func(self, module_op: ModuleOp) -> func.FuncOp | None:
        """识别单函数 `npu_demo` module 的普通 emit_c 子集。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 允许 `builtin.module` 只包含一个 `func.func`，且该函数不是 `arch.launch` 双函数 module。
        - 单函数 body 必须至少包含一个非 `func.return` 的语义 op，避免把空 module 误当成成功输入。
        - 该分支复用普通 `_emit_func(...)` 路径，不影响既有 `launch body + wrapper` 约束。

        使用示例:
        - func_op = self._get_npu_demo_plain_func(module_op)

        关联文件:
        - spec: spec/dsl/gen_kernel.md
        - test: test/dsl/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel.py
        """

        top_ops = list(module_op.ops)
        if any(not isinstance(top_op, func.FuncOp) for top_op in top_ops):
            return None
        func_ops = [top_op for top_op in top_ops if isinstance(top_op, func.FuncOp)]
        if len(func_ops) != 1:
            return None
        func_op = func_ops[0]
        filtered_ops = self._filtered_npu_demo_launch_ops(func_op)
        if not filtered_ops:
            return None
        if len(filtered_ops) != len(list(func_op.body.block.ops)):
            return None
        if not isinstance(filtered_ops[-1], func.ReturnOp):
            return None
        if any(isinstance(op, ArchLaunchOp) for op in filtered_ops):
            return None
        if all(isinstance(op, func.ReturnOp) for op in filtered_ops):
            return None
        return func_op

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
        """生成 `conv2d_img2col2d_tiled(...)` 的固定 CPU 函数体骨架。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 输出冻结的 tile 常量、局部 `col_buffer/acc_buffer`、`cpu::img2col2d(...)` 以及写回 `out` 的固定循环骨架。
        - 仅允许 rank-4 memory 输入/输出，且 element type 必须一致。

        使用示例:
        - body = self._emit_cpu_conv2d_img2col2d_tiled_body(func_op)

        关联文件:
        - spec: spec/dsl/gen_kernel.md
        - test: test/dsl/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel.py
        """

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
        element_type = self._type_to_c(out_type.element_type)
        input_c_type = self._type_to_c(input_type)

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
                f"{self.ctx.current_indent}Memory<MemorySpace::GM, {element_type}> col_tile("
                "col_buffer, 3, col_shape, col_stride, MemoryFormat::Norm);"
            ),
            f"{self.ctx.current_indent}const {input_c_type}& input_tile = {input_name};",
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
            f"const {self._type_to_c(input_type)}& {input_name}, "
            f"const {self._type_to_c(weight_type)}& {weight_name}, "
            f"{self._type_to_c(out_type)}& out)"
        )

    def _is_npu_demo_body_level_kernel(self, func_op: func.FuncOp) -> bool:
        if self.ctx.target != "npu_demo":
            return False
        arg_names = _extract_arg_names(func_op)
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

    def _npu_demo_module_funcs(self, module_op: ModuleOp) -> list[func.FuncOp]:
        """提取并校验 npu_demo module 的顶层 `func.func` 列表。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - `target="npu_demo"` 的 module 子集只允许顶层 `func.func`。
        - 允许额外的 helper `func.func`，但不允许混入其他顶层 op。

        使用示例:
        - func_ops = self._npu_demo_module_funcs(module_op)

        关联文件:
        - spec: spec/dsl/gen_kernel.md
        - test: test/dsl/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel.py
        """

        top_ops = list(module_op.ops)
        if any(not isinstance(top_op, func.FuncOp) for top_op in top_ops):
            raise _error(self.ctx, "<module>", "npu_demo launch module must contain only func.func")
        return [top_op for top_op in top_ops if isinstance(top_op, func.FuncOp)]

    def _is_npu_demo_launch_helper_op(self, op: Operation) -> bool:
        """判断 body/wrapper 中可忽略的符号辅助 op。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 允许测试/expectation 为 view/launch 维度准备辅助 `!symbol.int` 值。
        - 也允许 `outline-device-kernel` 注入的 `symbol.const` 辅助 op，避免 wrapper 的 launch 元数据被误计入语义体。
        - 这些 op 不参与 `gen_kernel(target="npu_demo")` 的固定骨架输出与序列判定。

        使用示例:
        - if self._is_npu_demo_launch_helper_op(op): ...

        关联文件:
        - spec: spec/dsl/gen_kernel.md
        - test: test/dsl/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel.py
        """

        return op.name == "test.fake_symbol_value" or isinstance(op, SymbolConstOp)

    def _filtered_npu_demo_launch_ops(self, func_op: func.FuncOp) -> list[Operation]:
        """返回 npu_demo launch 子集的有效语义 op 序列。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 过滤辅助 `!symbol.int` 产生 op，仅保留 wrapper/body 的冻结语义骨架。
        - 供 module 分类与固定序列校验复用。

        使用示例:
        - ops = self._filtered_npu_demo_launch_ops(func_op)

        关联文件:
        - spec: spec/dsl/gen_kernel.md
        - test: test/dsl/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel.py
        """

        return [op for op in func_op.body.block.ops if not self._is_npu_demo_launch_helper_op(op)]

    def _launch_callee_name(self, launch_op: ArchLaunchOp, wrapper_name: str) -> str:
        """解析 wrapper `arch.launch` 的 body callee 名称。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 仅接受扁平 `@symbol` 形式的 callee。
        - 出错时复用稳定短语，便于后续审查与 expectation 机械判断。

        使用示例:
        - callee_name = self._launch_callee_name(launch_op, wrapper_func.sym_name.data)

        关联文件:
        - spec: spec/dsl/gen_kernel.md
        - test: test/dsl/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel.py
        """

        callee = launch_op.callee
        if not isinstance(callee, SymbolRefAttr):
            raise _error(self.ctx, wrapper_name, "npu_demo launch wrapper must use flat @callee")
        if len(callee.nested_references.data) != 0 or not callee.root_reference.data:
            raise _error(self.ctx, wrapper_name, "npu_demo launch wrapper must use flat @callee")
        return callee.root_reference.data

    def _static_launch_extent(self, launch_op: ArchLaunchOp, field_name: str, wrapper_name: str) -> int:
        """读取 launch 的静态 extent，并显式拒绝非静态或非法值。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - `npu_demo` wrapper 只接受静态整数 extent。
        - 非 `!symbol.int` 或无法求值为整数时必须 fail-fast。

        使用示例:
        - thread_extent = self._static_launch_extent(launch_op, "thread", wrapper_name)

        关联文件:
        - spec: spec/dsl/gen_kernel.md
        - test: test/dsl/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel.py
        """

        operand = getattr(launch_op, field_name)
        operand_type = operand.type
        if not isinstance(operand_type, SymbolValueType):
            raise _error(self.ctx, wrapper_name, f"npu_demo launch wrapper {field_name} must be !symbol.int")
        value = operand_type.get_value()
        if not isinstance(value, int):
            raise _error(self.ctx, wrapper_name, f"npu_demo launch wrapper {field_name} must be static integer")
        return value

    def _expected_npu_demo_launch_extents(self) -> tuple[int, int, int]:
        """读取当前 target 的 launch extent 期望值。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 从 target registry 读取 `block_num/thread_num/subthread_num`。
        - 作为 `npu_demo` wrapper 的唯一标准 extents 来源。

        使用示例:
        - expected = self._expected_npu_demo_launch_extents()

        关联文件:
        - spec: spec/dsl/gen_kernel.md
        - test: test/dsl/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel.py
        """

        extents: list[int] = []
        for hw_key in ("block_num", "thread_num", "subthread_num"):
            value = target_registry.get_target_hardware(self.ctx.target, hw_key)
            if value is None:
                raise _error(self.ctx, "<module>", f"npu_demo target missing {hw_key}")
            extents.append(value)
        return extents[0], extents[1], extents[2]

    def _launch_extents_from_wrapper(self, launch_op: ArchLaunchOp, wrapper_name: str) -> tuple[int, int, int]:
        """读取 wrapper 内 `arch.launch` 的静态 extent。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 仅接受静态 `!symbol.int` extent。
        - 供 wrapper 校验与源码发射复用，避免硬编码 launch 模板参数。

        使用示例:
        - actual = self._launch_extents_from_wrapper(launch_op, "add_barrier")

        关联文件:
        - spec: spec/dsl/gen_kernel.md
        - test: test/dsl/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel.py
        """

        return (
            self._static_launch_extent(launch_op, "block", wrapper_name),
            self._static_launch_extent(launch_op, "thread", wrapper_name),
            self._static_launch_extent(launch_op, "subthread", wrapper_name),
        )

    def _classify_npu_demo_launch_module(self, module_op: ModuleOp) -> tuple[func.FuncOp, func.FuncOp]:
        """识别受控 module 中的 body / wrapper 函数。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 以唯一 `arch.launch` 所在函数识别 wrapper，并校验其 callee 对应唯一 body。
        - module 可以额外携带不含 `arch.launch` 的 helper `func.func`，但 wrapper 仍必须唯一。

        使用示例:
        - body_func, wrapper_func = self._classify_npu_demo_launch_module(module_op)

        关联文件:
        - spec: spec/dsl/gen_kernel.md
        - test: test/dsl/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel.py
        """

        func_ops = self._npu_demo_module_funcs(module_op)
        wrapper_candidates = [
            func_op
            for func_op in func_ops
            if any(isinstance(op, ArchLaunchOp) for op in self._filtered_npu_demo_launch_ops(func_op))
        ]
        if len(wrapper_candidates) != 1:
            raise _error(self.ctx, "<module>", "npu_demo launch module must contain exactly one wrapper func with arch.launch")

        wrapper_func = wrapper_candidates[0]
        wrapper_ops = self._filtered_npu_demo_launch_ops(wrapper_func)
        if len(wrapper_ops) != 2 or not isinstance(wrapper_ops[0], ArchLaunchOp) or not isinstance(wrapper_ops[1], func.ReturnOp):
            raise _error(self.ctx, wrapper_func.sym_name.data, "npu_demo launch wrapper must contain arch.launch followed by func.return")

        callee_name = self._launch_callee_name(wrapper_ops[0], wrapper_func.sym_name.data)
        body_func = next((func_op for func_op in func_ops if func_op.sym_name.data == callee_name), None)
        if body_func is None or body_func is wrapper_func:
            raise _error(self.ctx, wrapper_func.sym_name.data, f"npu_demo launch wrapper references missing body {callee_name}")
        return body_func, wrapper_func

    def _validate_npu_demo_launch_body_signature(
        self, func_op: func.FuncOp
    ) -> tuple[list[NnMemoryType], int]:
        """校验 body 函数签名。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - body 既兼容 `ctx + lhs + rhs + out` 的四参数、零返回形式，也兼容 outline 后的
          `lhs + rhs + out` 三参数、零返回形式。
        - 三个 memory 参数必须 element type 一致。

        使用示例:
        - body_input_types, arg_offset = self._validate_npu_demo_launch_body_signature(body_func)

        关联文件:
        - spec: spec/dsl/gen_kernel.md
        - test: test/dsl/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel.py
        """

        func_name = func_op.sym_name.data
        input_types = list(func_op.function_type.inputs.data)
        result_types = list(func_op.function_type.outputs.data)
        arg_names = _extract_arg_names(func_op)
        if result_types:
            raise _error(self.ctx, func_name, "unsupported npu_demo launch body signature")
        if len(input_types) not in {3, 4}:
            raise _error(self.ctx, func_name, "unsupported npu_demo launch body signature")

        body_arg_offset = 0
        if len(input_types) == 4:
            if not arg_names or arg_names[0] != "ctx":
                raise _error(self.ctx, func_name, "npu_demo launch body requires leading ctx argument")
            body_arg_offset = 1

        body_input_types = input_types[body_arg_offset:]
        if len(body_input_types) != 3:
            raise _error(self.ctx, func_name, "unsupported npu_demo launch body signature")
        if any(not isinstance(arg_type, NnMemoryType) for arg_type in body_input_types):
            raise _error(self.ctx, func_name, "unsupported npu_demo launch body signature")
        lhs_type, rhs_type, out_type = body_input_types
        if lhs_type.element_type != rhs_type.element_type or lhs_type.element_type != out_type.element_type:
            raise _error(self.ctx, func_name, "npu_demo launch body requires matching element types")
        return list(body_input_types), body_arg_offset

    def _validate_npu_demo_launch_wrapper_signature(
        self,
        wrapper_func: func.FuncOp,
        body_func: func.FuncOp,
    ) -> tuple[list[NnMemoryType], int]:
        """校验 wrapper 函数签名与 launch 参数透传关系。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - wrapper 必须是 `lhs + rhs + out` 的三参数、零返回形式。
        - `arch.launch` 的 args 必须按原顺序透传 wrapper 参数，extent 由静态 launch 值与 target registry 一致性共同约束。

        使用示例:
        - lhs_type, rhs_type, out_type = self._validate_npu_demo_launch_wrapper_signature(wrapper, body)

        关联文件:
        - spec: spec/dsl/gen_kernel.md
        - test: test/dsl/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel.py
        """

        body_input_types, body_arg_offset = self._validate_npu_demo_launch_body_signature(body_func)
        func_name = wrapper_func.sym_name.data
        input_types = list(wrapper_func.function_type.inputs.data)
        result_types = list(wrapper_func.function_type.outputs.data)
        wrapper_ops = self._filtered_npu_demo_launch_ops(wrapper_func)
        launch_op = wrapper_ops[0]
        if len(input_types) != 3 or result_types:
            raise _error(self.ctx, func_name, "unsupported npu_demo launch wrapper signature")
        if input_types != body_input_types:
            raise _error(self.ctx, func_name, "npu_demo launch wrapper signature must match body inputs")

        expected_block, expected_thread, expected_subthread = self._expected_npu_demo_launch_extents()
        actual_block, actual_thread, actual_subthread = self._launch_extents_from_wrapper(launch_op, func_name)
        if (actual_block, actual_thread, actual_subthread) != (
            expected_block,
            expected_thread,
            expected_subthread,
        ):
            raise _error(
                self.ctx,
                func_name,
                "npu_demo launch wrapper must use npu_demo::launch<"
                f"{expected_block}, {expected_thread}, {expected_subthread}>; "
                f"got block={actual_block}, thread={actual_thread}, subthread={actual_subthread}",
            )

        if len(launch_op.args) != len(wrapper_func.args):
            raise _error(self.ctx, func_name, "npu_demo launch wrapper args must forward wrapper signature")
        for wrapper_arg, launch_arg in zip(wrapper_func.args, launch_op.args, strict=True):
            if wrapper_arg is not launch_arg:
                raise _error(self.ctx, func_name, "npu_demo launch wrapper args must forward wrapper signature")
        return body_input_types, body_arg_offset

    def _emit_npu_demo_generic_launch_body_function(
        self,
        func_op: func.FuncOp,
        body_input_types: list[NnMemoryType],
        body_arg_offset: int,
    ) -> str:
        """生成 outline 后 `npu_demo` launch body 的通用函数体。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 按 IR 顺序逐个委托普通 op 到 `emit_c_op(...)`，保留 `arch.barrier` 的显式格式化。
        - 兼容 outline 后去掉 `ctx` 形参的 body，同时对旧 helper 形式保持同一套写法。
        - `func.return` 统一走 `_emit_return_statement(...)`，避免把 void body 误落成显式 return 值。

        使用示例:
        - body = self._emit_npu_demo_generic_launch_body_function(func_op, body_input_types, body_arg_offset)

        关联文件:
        - spec: spec/dsl/gen_kernel.md
        - test: test/dsl/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel.py
        """

        func_name = func_op.sym_name.data
        arg_names = _extract_arg_names(func_op)
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
                    raise _error(self.ctx, func_name, "unsupported npu_demo launch body helper op")
                expr = op.results[0].type.expr.expr.data
                expr = expr.replace("thread_num", "ctx.thread_num()")
                expr = expr.replace("thread_id", "ctx.thread_id()")
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
            stmt = emit_c_op(op, self.ctx)
            if stmt:
                lines.append(stmt)
            if len(op.results) == 1 and isinstance(op.results[0].type, NnMemoryType):
                bound_name = self.ctx.lookup_name(op.results[0])
                if bound_name is not None:
                    last_memory_result_name = bound_name
        body = "\n".join(lines)
        if body:
            return f"{signature} {{\n{body}\n}}"
        return f"{signature} {{\n}}"

    def _format_npu_demo_barrier_stmt(self, barrier_op: ArchBarrierOp, func_name: str) -> str:
        """把 `arch.barrier` 格式化为 `KernelContext::barrier(...)` 语句。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 显式收口为
          `ctx.barrier({BarrierVisibility::TSM, BarrierVisibility::TLM}, BarrierScope::BLOCK);`
        - 非 block 或缺失 `[tsm, tlm]` 时稳定失败，防止回退到旧接口。

        使用示例:
        - stmt = self._format_npu_demo_barrier_stmt(barrier_op, "add_barrier_body")

        关联文件:
        - spec: spec/dsl/gen_kernel.md
        - test: test/dsl/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel.py
        """

        if barrier_op.scope.scope.data != "block":
            raise _error(self.ctx, func_name, "npu_demo barrier scope must be block")
        spaces = []
        for entry in barrier_op.visibility.data:
            visibility_attr = getattr(entry, "visibility", None)
            if visibility_attr is None:
                raise _error(self.ctx, func_name, "npu_demo barrier visibility must be [tsm, tlm]")
            spaces.append(visibility_attr.data)
        if spaces != ["tsm", "tlm"]:
            raise _error(self.ctx, func_name, "npu_demo barrier visibility must be [tsm, tlm]")
        return (
            f"{self.ctx.current_indent}ctx.barrier("
            "{BarrierVisibility::TSM, BarrierVisibility::TLM}, BarrierScope::BLOCK);"
        )

    def _emit_npu_demo_launch_body_function(self, func_op: func.FuncOp) -> str:
        """生成 npu_demo launch body 函数源码。

        创建者: 小李飞刀
        最后一次更改: jcc你莫辜负

        功能说明:
        - 输出 `static` body 签名，并按 lowered IR 的实际 op 顺序逐条发射源码。
        - 允许 body 中保留 `arch.barrier`、`dma.alloc`、`dma.view`、`dma.slice`、`dma.deslice` 等公开合同。
        - 不再依赖冻结 add/barrier 子集，body 形态由唯一 wrapper + lowered IR 共同决定。

        使用示例:
        - source = self._emit_npu_demo_launch_body_function(body_func)

        关联文件:
        - spec: spec/dsl/gen_kernel.md
        - test: test/dsl/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel.py
        """

        body_input_types, body_arg_offset = self._validate_npu_demo_launch_body_signature(func_op)
        return self._emit_npu_demo_generic_launch_body_function(func_op, body_input_types, body_arg_offset)

    def _emit_npu_demo_launch_body_declaration(self, func_op: func.FuncOp) -> str:
        """生成 npu_demo launch body 的前置声明。

        创建者: jcc你莫辜负
        最后一次更改: jcc你莫辜负

        功能说明:
        - 为 `npu_demo` launch module 提供与定义完全一致的 body 前置声明。
        - 解决 outline 后 wrapper 先于 body 出现时的函数可见性问题，避免 wrapper 调用未声明的 body。

        使用示例:
        - decl = self._emit_npu_demo_launch_body_declaration(body_func)

        关联文件:
        - spec: spec/dsl/gen_kernel.md
        - test: test/dsl/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel.py
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

        创建者: jcc你莫辜负
        最后一次更改: jcc你莫辜负

        功能说明:
        - 统一构造 `static void <body>(npu_demo::KernelContext& ctx, ...)` 的签名。
        - 供 body 定义与前置声明共享，避免两处拼接逻辑不一致。

        使用示例:
        - signature = self._emit_npu_demo_launch_body_signature(func_op, body_input_types, body_arg_offset)

        关联文件:
        - spec: spec/dsl/gen_kernel.md
        - test: test/dsl/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel.py
        """

        func_name = func_op.sym_name.data
        arg_names = _extract_arg_names(func_op)
        body_arg_names = arg_names[body_arg_offset:]
        mutable_memory_args = self._mutable_memory_arg_indices(func_op)
        params: list[str] = [f"npu_demo::KernelContext& ctx"]
        for arg_index, (arg_name, arg_type) in enumerate(zip(body_arg_names, body_input_types, strict=True), start=body_arg_offset):
            if not isinstance(arg_type, NnMemoryType):
                raise _error(self.ctx, func_name, "unsupported npu_demo launch body signature")
            qualifier = "" if arg_index in mutable_memory_args else "const "
            params.append(f"{qualifier}{self._type_to_c(arg_type)}& {arg_name}")
        return f"static void {func_name}({', '.join(params)})"

    def _emit_npu_demo_launch_wrapper_function(self, wrapper_func: func.FuncOp, body_func: func.FuncOp) -> str:
        """生成 npu_demo wrapper 函数源码。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - wrapper 负责把 `lhs/rhs/out` 原样透传给 `npu_demo::launch<block, thread, subthread>(body, ...)`。
        - 不生成 `KernelContext` 参数，也不引入旧同步接口。

        使用示例:
        - source = self._emit_npu_demo_launch_wrapper_function(wrapper_func, body_func)

        关联文件:
        - spec: spec/dsl/gen_kernel.md
        - test: test/dsl/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel.py
        """

        body_input_types, body_arg_offset = self._validate_npu_demo_launch_wrapper_signature(wrapper_func, body_func)
        arg_names = _extract_arg_names(wrapper_func)
        launch_op = self._filtered_npu_demo_launch_ops(wrapper_func)[0]
        block_extent, thread_extent, subthread_extent = self._launch_extents_from_wrapper(
            launch_op,
            wrapper_func.sym_name.data,
        )
        mutable_memory_args = self._mutable_memory_arg_indices(body_func)
        params = []
        for index, (arg_name, arg_type) in enumerate(zip(arg_names, wrapper_func.function_type.inputs.data, strict=True)):
            if not isinstance(arg_type, NnMemoryType):
                raise _error(self.ctx, wrapper_func.sym_name.data, "unsupported npu_demo launch wrapper signature")
            body_arg_index = body_arg_offset + index
            qualifier = "" if body_arg_index in mutable_memory_args else "const "
            params.append(f"{qualifier}{_type_to_c(arg_type)}& {arg_name}")
        signature = f"void {wrapper_func.sym_name.data}({', '.join(params)})"
        self.ctx.push_indent()
        call_args = ", ".join(arg_names)
        body = (
            f"{self.ctx.current_indent}npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}>({body_func.sym_name.data}, {call_args});"
            if call_args
            else f"{self.ctx.current_indent}npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}>({body_func.sym_name.data});"
        )
        self.ctx.pop_indent()
        return f"{signature} {{\n{body}\n}}"

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
        """生成 npu_demo body-level kernel 的固定函数体骨架。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 输出 `thread_id/thread_num -> get_dynamic_memory -> view/slice/add/deslice` 的受控顺序。
        - 仅接受冻结子集，遇到非法 body 结构时必须显式失败。

        使用示例:
        - body = self._emit_npu_demo_body_level_kernel_body(func_op)

        关联文件:
        - spec: spec/dsl/gen_kernel.md
        - test: test/dsl/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel.py
        """

        self._get_npu_demo_body_level_kernel_types(func_op)
        self._validate_npu_demo_body_level_kernel_body(func_op)
        _, out_type = self._get_npu_demo_body_level_kernel_types(func_op)
        arg_names = _extract_arg_names(func_op)
        for arg_name, arg_value in zip(arg_names, func_op.args, strict=True):
            if self.ctx.lookup_name(arg_value) is None:
                self.ctx.bind_name(arg_value, arg_name)
        source_name = self.ctx.lookup_name(func_op.args[1]) or arg_names[1]
        element_type = self._type_to_c(out_type.element_type)
        lines = [
            f"{self.ctx.current_indent}long long tid = ctx.thread_id();",
            f"{self.ctx.current_indent}long long tnum = ctx.thread_num();",
            "",
            (
                f"{self.ctx.current_indent}Memory<MemorySpace::TSM, {element_type}> tsm = "
                f"ctx.get_dynamic_memory<MemorySpace::TSM, {element_type}>();"
            ),
            (
                f"{self.ctx.current_indent}Memory<MemorySpace::TLM1, {element_type}> tlm = "
                f"ctx.get_dynamic_memory<MemorySpace::TLM1, {element_type}>();"
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
            self._type_to_c(result_type)

        mutable_memory_args = self._mutable_memory_arg_indices(func_op)
        arg_names = _extract_arg_names(func_op)
        leading_out_params = _leading_rewritten_out_param_count(func_op)
        if mutable_memory_args:
            contiguous_mutable_prefix = 0
            while (
                contiguous_mutable_prefix < leading_out_params
                and contiguous_mutable_prefix in mutable_memory_args
            ):
                contiguous_mutable_prefix += 1
            leading_out_params = contiguous_mutable_prefix
        params: list[str] = []
        for index, (arg_name, arg_type, arg_value) in enumerate(zip(arg_names, input_types, func_op.args, strict=True)):
            self.ctx.bind_name(arg_value, arg_name)
            if isinstance(arg_type, NnMemoryType):
                if index < leading_out_params or index in mutable_memory_args:
                    params.append(f"{self._type_to_c(arg_type)}& {arg_name}")
                else:
                    params.append(f"const {self._type_to_c(arg_type)}& {arg_name}")
            else:
                params.append(f"{self._type_to_c(arg_type)} {arg_name}")

        return_type = "void"
        if result_types:
            return_type = self._type_to_c(result_types[0])

        return f"{return_type} {func_name}({', '.join(params)})"

    def _mutable_memory_arg_indices(self, func_op: func.FuncOp) -> set[int]:
        """推断普通函数签名里需要可写引用的 memory 参数位置。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 递归扫描当前函数里已知的写入类 op，把其 `target/out` 所对应的 block argument 记为可写参数。
        - 覆盖 `symbol.for` / `scf.for` region 内的 `dma.store`，避免把循环内写回的 out 参数误生成 `const&`。
        - 供 `npu_demo` 单函数 module 的默认签名复用，避免把 `dst` 一律误生成为 `const&`。

        使用示例:
        - mutable = self._mutable_memory_arg_indices(func_op)

        关联文件:
        - spec: spec/dsl/gen_kernel.md
        - test: test/dsl/test_gen_kernel.py
        - 功能实现: kernel_gen/dsl/gen_kernel.py
        """

        arg_to_index = {arg: index for index, arg in enumerate(func_op.args)}
        mutable: set[int] = set()
        for op in _walk_ops(func_op):
            for value in self._mutable_memory_operands(op):
                if isinstance(value, BlockArgument) and value in arg_to_index:
                    mutable.add(arg_to_index[value])
        return mutable

    def _mutable_memory_operands(self, op: Operation) -> tuple[BlockArgument, ...]:
        """返回当前 op 中会被写入的 block argument operand。"""

        candidates: list[object] = []
        if op.name.startswith("kernel."):
            out_value = _kernel_out_operand(op)
            if out_value is not None:
                candidates.append(out_value)
        if isinstance(op, (DmaBroadcastOp, DmaCastOp, DmaCopyOp, DmaFillOp, DmaLoadOp, DmaSliceOp, DmaTransposeOp)):
            if not isinstance(op, DmaCastOp) or len(op.operands) == 2:
                candidates.append(op.target)
        if isinstance(op, (DmaDesliceOp, DmaStoreOp)):
            candidates.append(op.target)
        mutable_args: list[BlockArgument] = []
        for candidate in candidates:
            if isinstance(candidate, BlockArgument):
                mutable_args.append(candidate)
        return tuple(mutable_args)

    def _is_returned_output_alloc(self, func_op: func.FuncOp, op: DmaAllocOp) -> bool:
        if self.ctx.target != "cpu":
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

        创建者: 朽木露琪亚
        最后一次更改: 朽木露琪亚

        功能说明:
        - lowering 链路中会残留少量 `unrealized_conversion_cast`，主要用于把常量包装成 `!symbol.int`。
        - 这类 op 在源码生成阶段不需要独立语句，只需把结果别名回其唯一输入表达式。

        使用示例:
        - if self._bind_transparent_unrealized_conversion_cast(op): continue

        关联文件:
        - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
        - test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
        - 功能实现: [kernel_gen/dsl/gen_kernel.py](kernel_gen/dsl/gen_kernel.py)
        """

        if op.name != "builtin.unrealized_conversion_cast":
            return False
        if len(op.operands) != 1 or len(op.results) != 1:
            raise _error(self.ctx, op.name, "unrealized_conversion_cast must have exactly one operand and one result")
        self.ctx.bind_name(op.results[0], emit_c_value(op.operands[0], self.ctx))
        return True

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
        is_tile_codegen = _is_tile_codegen_function(func_op)
        if is_tile_codegen:
            _validate_tile_codegen_contract(func_op, self.ctx)

        tile_var_by_expr: dict[str, str] = {}
        emitted_tile_exprs: set[str] = set()

        def _tile_var_name(dim_name: str) -> str:
            return dim_name.strip().lower()

        lines: list[str] = []
        for op in func_op.body.block.ops:
            if op.name in {"kernel_split.symbol_literal", "tile.symbol_literal", "kernel_split.tile_value", "tile.step_value"}:
                raise _error(
                    self.ctx,
                    func_op.sym_name.data,
                    "TileCodegenMalformed: legacy bridge ops are not allowed",
                )

            if op.name == "tuner.param":
                if not op.results:
                    raise _error(self.ctx, func_op.sym_name.data, "TileCodegenMalformed: tuner.param must have a result")
                result_type = op.results[0].type
                if isinstance(result_type, SymbolValueType):
                    expr_name = result_type.expr.expr.data
                    var_name = tile_var_by_expr.setdefault(expr_name, _tile_var_name(expr_name))
                    self.ctx.bind_name(op.results[0], var_name)
                    if expr_name not in emitted_tile_exprs:
                        lines.append(f'{self.ctx.current_indent}long long {var_name} = tuner_param("{expr_name}");')
                        emitted_tile_exprs.add(expr_name)
                    continue
                raise _error(self.ctx, func_op.sym_name.data, "TileCodegenMalformed: tuner.param result must be !symbol.int")

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
            self._bind_rewritten_out_result(func_op, op)
            stmt = emit_c_op(op, self.ctx)
            if stmt and self.ctx.target == "cpu":
                stmt = self._normalize_cpu_memory_stmt(stmt)
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
            if self._bind_transparent_unrealized_conversion_cast(op):
                continue
            if isinstance(op, NnAddOp) and op.result.has_one_use():
                unique_user = op.result.get_user_of_unique_use()
                if isinstance(unique_user, func.ReturnOp) and self._is_direct_return_nn_add(unique_user):
                    self.ctx.bind_name(op.result, "out")
            self._bind_rewritten_out_result(func_op, op)
            stmt = emit_c_op(op, self.ctx)
            if stmt and self.ctx.target == "cpu":
                stmt = self._normalize_cpu_memory_stmt(stmt)
            if stmt:
                lines.append(stmt)
        return "\n".join(lines)


def gen_kernel(op_or_func: Any, ctx: EmitCContext) -> str:
    """把单个 MLIR op、`func.func` 或受控 `builtin.module` 生成为目标源码文本。

    创建者: 金铲铲大作战
    最后一次更改: jcc你莫辜负

    功能说明:
    - 这是 `kernel_gen.dsl.gen_kernel` 唯一稳定公开入口。
    - 输入为单个普通 op 时，直接委托 `emit_c_op(...)` 的公开节点级接口生成源码片段。
    - 输入为 `func.func` 时，统一交给 `_KernelEmitter` 在一条内部策略链中完成签名、函数级特化选择、IR 遍历和 `func.return/out` 收尾。
    - 当 `target="npu_demo"` 且输入为受控 `builtin.module` 子集时，输出双函数源码（body + wrapper）。

    使用示例:
    - source = gen_kernel(func_op, EmitCContext(target="cpu"))
    - stmt = gen_kernel(single_op, EmitCContext(target="cpu"))

    关联文件:
    - spec: spec/dsl/gen_kernel.md
    - test: test/dsl/test_gen_kernel.py
    - 功能实现: kernel_gen/dsl/gen_kernel.py
    """

    emit_ctx = ctx
    if ctx.target == "npu_demo":
        emit_ctx = EmitCContext(
            target=ctx.target,
            indent="    ",
            naming=ctx.naming,
            type_converter=ctx.type_converter,
            config=dict(ctx.config or {}),
        )
    source = _KernelEmitter(emit_ctx).emit(op_or_func)
    if ctx.target == "npu_demo":
        prelude = '#include "include/npu_demo/npu_demo.h"\nusing namespace npu_demo;\n\n'
        return prelude + source
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
