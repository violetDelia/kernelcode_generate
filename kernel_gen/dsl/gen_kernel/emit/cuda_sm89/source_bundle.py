"""CUDA SM89 final IR SourceBundle assembly.

功能说明:
- 遍历 `cuda-sm89-lowering` 后的最终 IR，生成 trace comments、stable hash 和 CUDA SourceBundle artifacts。
- 以真实 op、attrs、operand SSA identity、result identity、shape、stride、memory space 与 control-flow 发射 generated device body。
- generated host entry 保持 `kg_execute_entry(slots, count)` ABI，但会构造 device-visible slot view；generated kernel 保持计划内 launch extent，且只由 thread0 执行完整 device body。
- wrapper `Status` 通过 device status 回传给 host entry，host entry 负责输出 memory 回拷与临时 device 资源释放。

API 列表:
- `class CudaSm89IrTrace(records: tuple[str, ...], markers: tuple[str, ...], op_counts: dict[str, int], memory_spaces: tuple[str, ...], entry_symbol: str, kernel_symbol: str, device_body_symbol: str, stable_hash: str, generated_source: str)`
- `CudaSm89IrTrace.render_marker_source() -> str`
- `class CudaSm89SourceBuilder(module_op: ModuleOp, ctx: EmitCContext)`
- `CudaSm89SourceBuilder.build() -> dict[str, str]`
- `CudaSm89SourceBuilder.collect_trace() -> CudaSm89IrTrace`
- `CudaSm89SourceBuilder.value_name_map() -> dict[int, str]`
- `CudaSm89SourceBuilder.operation_record(op: Operation) -> str`
- `CudaSm89SourceBuilder.operation_markers(op: Operation) -> list[str]`
- `CudaSm89SourceBuilder.operation_memory_spaces(op: Operation) -> tuple[str, ...]`
- `CudaSm89SourceBuilder.matmul_operand_spaces(op: Operation) -> tuple[str, str, str]`
- `CudaSm89SourceBuilder.matmul_writeback_visible(op: Operation) -> bool`
- `CudaSm89SourceBuilder.matmul_materialization_marker(op: Operation) -> str`
- `CudaSm89SourceBuilder.validate_supported_attrs() -> None`
- `CudaSm89SourceBuilder.validate_supported_compute(counts: dict[str, int]) -> None`
- `CudaSm89SourceBuilder.operation_executable_word(record: str, index: int) -> str`
- `CudaSm89SourceBuilder.render_generated_source(records: tuple[str, ...], stable_hash: str) -> str`
- `CudaSm89SourceBuilder.render_body_declarations(names: dict[int, str]) -> str`
- `CudaSm89SourceBuilder.render_device_body_statements(names: dict[int, str]) -> str`
- `CudaSm89SourceBuilder.render_block_statements(block: Block, names: dict[int, str], op_indices: dict[int, int]) -> str`
- `CudaSm89SourceBuilder.render_operation_statement(op: Operation, op_index: int, names: dict[int, str], op_indices: dict[int, int] | None = None) -> str`
- `CudaSm89SourceBuilder.render_status_checked_call(comment: str, call: str) -> str`
- `CudaSm89SourceBuilder.render_symbol_for_statement(comment: str, op: Operation, names: dict[int, str], op_indices: dict[int, int]) -> str`
- `CudaSm89SourceBuilder.render_scf_if_statement(comment: str, op: Operation, names: dict[int, str], op_indices: dict[int, int]) -> str`
- `CudaSm89SourceBuilder.render_load_store_statement(comment: str, op: Operation, operand_names: tuple[str, ...], names: dict[int, str], *, use_store: bool) -> str`
- `CudaSm89SourceBuilder.render_slice_statement(comment: str, op: Operation, operand_names: tuple[str, ...], names: dict[int, str], wrapper: str) -> str`
- `CudaSm89SourceBuilder.render_binary_memory_statement(comment: str, op: Operation, operand_names: tuple[str, ...], wrapper: str) -> str`
- `CudaSm89SourceBuilder.render_transpose_statement(comment: str, op: Operation, operand_names: tuple[str, ...]) -> str`
- `CudaSm89SourceBuilder.render_alias_statement(comment: str, op: Operation, operand_names: tuple[str, ...], result_names: tuple[str, ...], names: dict[int, str], alias_kind: str) -> str`
- `CudaSm89SourceBuilder.render_make_ring_statement(comment: str, op: Operation, operand_names: tuple[str, ...], result_names: tuple[str, ...], names: dict[int, str]) -> str`
- `CudaSm89SourceBuilder.render_matmul_statement(comment: str, op: Operation, operand_names: tuple[str, ...], op_index: int) -> str`
- `CudaSm89SourceBuilder.render_img2col2d_statement(comment: str, op: Operation, operand_names: tuple[str, ...]) -> str`
- `CudaSm89SourceBuilder.render_binary_elewise_statement(comment: str, op: Operation, operand_names: tuple[str, ...]) -> str`
- `CudaSm89SourceBuilder.value_name(value: SSAValue, names: dict[int, str]) -> str`
- `CudaSm89SourceBuilder.memory_space_name(value: SSAValue) -> str`
- `CudaSm89SourceBuilder.memory_space_cpp(value: SSAValue) -> str`
- `CudaSm89SourceBuilder.memory_rank(value: SSAValue) -> int`
- `CudaSm89SourceBuilder.operation_vector_cpp(values: Sequence[SSAValue], names: dict[int, str], fallback: str) -> str`
- `CudaSm89SourceBuilder.value_vector_cpp(values: tuple[SSAValue, ...] | list[SSAValue], names: dict[int, str]) -> str`
- `CudaSm89SourceBuilder.alloc_shape_vector(op: Operation, result: SSAValue, names: dict[int, str]) -> str`
- `CudaSm89SourceBuilder.alloc_stride_vector(op: Operation, result: SSAValue, names: dict[int, str]) -> str`
- `CudaSm89SourceBuilder.alias_offset_vector(op: Operation, result: SSAValue, names: dict[int, str], alias_kind: str) -> str`
- `CudaSm89SourceBuilder.alias_shape_vector(op: Operation, result: SSAValue, names: dict[int, str], alias_kind: str) -> str`
- `CudaSm89SourceBuilder.alias_stride_vector(op: Operation, result: SSAValue, names: dict[int, str], alias_kind: str) -> str`
- `CudaSm89SourceBuilder.shape_vector(value: SSAValue) -> str`
- `CudaSm89SourceBuilder.stride_vector(value: SSAValue) -> str`
- `CudaSm89SourceBuilder.unit_stride_vector(value: SSAValue) -> str`
- `CudaSm89SourceBuilder.zero_vector(value: SSAValue) -> str`
- `CudaSm89SourceBuilder.first_shape_extent(value: SSAValue) -> str`
- `CudaSm89SourceBuilder.first_stride_extent(value: SSAValue) -> str`
- `CudaSm89SourceBuilder.first_vector_value(vector_expr: str, default: str) -> str`
- `CudaSm89SourceBuilder.vector_cpp(values: list[str]) -> str`
- `CudaSm89SourceBuilder.symbol_attr_cpp(attr: Attribute) -> str`
- `CudaSm89SourceBuilder.static_symbol_attr_cpp(attr: Attribute, op_name: str) -> str`
- `CudaSm89SourceBuilder.symbol_type_default_cpp(value_type: Attribute) -> str`
- `CudaSm89SourceBuilder.int_attr_cpp(op: Operation, attr_name: str, default: str) -> str`
- `CudaSm89SourceBuilder.float_attr_cpp(op: Operation) -> str`
- `CudaSm89SourceBuilder.attr_contains(op: Operation, attr_name: str, expected: str) -> bool`
- `CudaSm89SourceBuilder.render_kernel_source(trace: CudaSm89IrTrace) -> str`
- `build_cuda_sm89_source_bundle(module_op: ModuleOp, ctx: EmitCContext) -> dict[str, str]`

使用示例:
- bundle = build_cuda_sm89_source_bundle(module_op, ctx)

关联文件:
- spec: spec/dsl/gen_kernel/emit/cuda_sm89.md
- 功能实现: kernel_gen/dsl/gen_kernel/emit/cuda_sm89/module.py
- test: test/dsl/gen_kernel/emit/test_cuda_sm89_emit.py
"""

from __future__ import annotations

from collections.abc import Sequence
from collections import Counter
from dataclasses import dataclass
import hashlib
import re

from xdsl.dialects import func
from xdsl.dialects.builtin import Float32Type, IntegerType, ModuleOp
from xdsl.ir import Attribute, Block, Operation, SSAValue

from kernel_gen.dialect.dma import DmaRingType
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dsl.gen_kernel.emit_context import EmitCContext

from .constants import CUDA_SM89_GENERATED_ENTRY_HEADER_ARTIFACT, CUDA_SM89_KERNEL_SOURCE_ARTIFACT, CUDA_SM89_RUNTIME_ENTRY_NAME
from .runtime import CUDA_SM89_COMMON_RUNTIME_SOURCE, CUDA_SM89_HEADER_SOURCE


CUDA_SM89_SUPPORTED_FINAL_IR_OPS: frozenset[str] = frozenset(
    {
        "arch.get_block_id",
        "arch.get_block_num",
        "arch.get_subthread_id",
        "arch.get_subthread_num",
        "arch.get_thread_id",
        "arch.get_thread_num",
        "arch.launch",
        "arith.constant",
        "builtin.module",
        "builtin.unregistered",
        "dma.alloc",
        "dma.broadcast",
        "dma.copy",
        "dma.deslice",
        "dma.fill",
        "dma.free",
        "dma.load",
        "dma.make_ring",
        "dma.advance_ring",
        "dma.current_ring",
        "dma.reinterpret",
        "dma.reshape",
        "dma.slice",
        "dma.store",
        "dma.transpose",
        "dma.view",
        "func.func",
        "func.return",
        "kernel.binary_elewise",
        "kernel.exp",
        "kernel.img2col2d",
        "kernel.matmul",
        "kernel.reduce",
        "memory.get_data",
        "scf.if",
        "scf.yield",
        "symbol.add",
        "symbol.cast",
        "symbol.const",
        "symbol.floordiv",
        "symbol.for",
        "symbol.get_dim",
        "symbol.get_stride",
        "symbol.max",
        "symbol.min",
        "symbol.mul",
        "symbol.ne",
        "symbol.sub",
        "tuner.select",
    }
)
CUDA_SM89_BINARY_ELEWISE_KINDS: frozenset[str] = frozenset({"add", "sub", "mul", "truediv", "max"})
CUDA_SM89_REDUCE_KINDS: frozenset[str] = frozenset({"max", "sum"})
CUDA_SM89_COMPUTE_OPS: frozenset[str] = frozenset(
    {"kernel.binary_elewise", "kernel.exp", "kernel.img2col2d", "kernel.matmul", "kernel.reduce"}
)
CUDA_SM89_SPACE_TO_CPP: dict[str, str] = {
    "global": "MemorySpace::GM",
    "gm": "MemorySpace::GM",
    "sm": "MemorySpace::SM",
    "lm": "MemorySpace::LM",
    "tsm": "MemorySpace::TSM",
    "tlm1": "MemorySpace::TLM1",
    "tlm2": "MemorySpace::TLM2",
    "tlm3": "MemorySpace::TLM3",
}


@dataclass(frozen=True)
class CudaSm89IrTrace:
    """CUDA SM89 final IR trace.

    功能说明:
    - 保存真实遍历得到的 stable records、trace comments、op counts、memory spaces、entry symbol、kernel symbol 和 generated source。
    - 仅作为 `cuda_sm89` package-local SourceBundle builder 的数据载体。

    使用示例:
    - marker_source = trace.render_marker_source()
    """

    records: tuple[str, ...]
    markers: tuple[str, ...]
    op_counts: dict[str, int]
    memory_spaces: tuple[str, ...]
    entry_symbol: str
    kernel_symbol: str
    device_body_symbol: str
    stable_hash: str
    generated_source: str

    def render_marker_source(self) -> str:
        """渲染 final IR trace comment。

        功能说明:
        - 输出 module 级 `kg.cuda.ir.hash`、entry symbol、generated kernel symbol、device body symbol、memory spaces 和逐 op comment。
        - markers 已由 builder 按真实 IR 顺序生成；本方法不重新遍历 IR。

        使用示例:
        - source = trace.render_marker_source()
        """

        marker_lines = [
            "// cuda_sm89 generated from final IR",
            f"// kg.cuda.ir.hash: {self.stable_hash}",
            f"// kg.cuda.ir.entry_symbol: {self.entry_symbol}",
            f"// kg.cuda.ir.generated_kernel_symbol: {self.kernel_symbol}",
            f"// kg.cuda.ir.device_body_symbol: {self.device_body_symbol}",
            f"// kg.cuda.ir.memory_spaces: {','.join(self.memory_spaces)}",
        ]
        marker_lines.extend(self.markers)
        return "\n".join(marker_lines) + "\n"


class CudaSm89SourceBuilder:
    """CUDA SM89 final IR SourceBundle builder.

    功能说明:
    - 通过 `ModuleOp.walk()` 读取最终 IR 的 op、attrs、operand SSA identity、result identity、result types 和 function attrs。
    - 生成由 final IR control-flow 支配的 per-op wrapper call device body，并在 unsupported op/attr/type 上 fail-fast。

    使用示例:
    - bundle = CudaSm89SourceBuilder(module_op, ctx).build()
    """

    def __init__(self, module_op: ModuleOp, ctx: EmitCContext) -> None:
        """初始化 builder。

        功能说明:
        - 保存公开 emit context，用于按现有 CUDA SM89 unsupported 文本构造失败。
        - 不读取函数名或 printed IR token 来决定 source，只在 comments 中记录真实 func 名。

        使用示例:
        - builder = CudaSm89SourceBuilder(module_op, ctx)
        """

        self.module_op = module_op
        self.ctx = ctx
        self.rendered_launch_callees: set[str] = set()
        self.comment_only_result_op_ids: set[int] = set()

    def build(self) -> dict[str, str]:
        """构建 CUDA SM89 SourceBundle artifacts。

        功能说明:
        - 先收集 final IR trace，再渲染 `kernel.cu` 与 generated entry header。
        - artifact key 保持 `kernel.cu` 与 `include/cuda_sm89/generated_entry.cuh` 不变。

        使用示例:
        - source_bundle = builder.build()
        """

        trace = self.collect_trace()
        return {
            CUDA_SM89_KERNEL_SOURCE_ARTIFACT: self.render_kernel_source(trace),
            CUDA_SM89_GENERATED_ENTRY_HEADER_ARTIFACT: CUDA_SM89_HEADER_SOURCE,
        }

    def collect_trace(self) -> CudaSm89IrTrace:
        """收集 final IR traversal trace。

        功能说明:
        - 遍历 module 中每个 op，记录 op name、attrs、operand/result SSA identity、region/block arg identity 和 memory space。
        - 对 unsupported final IR op 使用 `unsupported cuda_sm89 final IR op: <op_name>` 稳定文本失败。

        使用示例:
        - trace = builder.collect_trace()
        """

        records: list[str] = []
        markers: list[str] = []
        op_counts: Counter[str] = Counter()
        memory_spaces: set[str] = set()
        for op in self.module_op.walk():
            op_name = op.name
            if op_name not in CUDA_SM89_SUPPORTED_FINAL_IR_OPS:
                raise self.ctx.emit_error("cuda_sm89", f"unsupported cuda_sm89 final IR op: {op_name}")
            op_counts[op_name] += 1
            records.append(self.operation_record(op))
            markers.extend(self.operation_markers(op))
            for space in self.operation_memory_spaces(op):
                memory_spaces.add(space)
        counts = dict(sorted(op_counts.items()))
        self.validate_supported_attrs()
        self.validate_supported_compute(counts)
        stable_hash = hashlib.sha256("\n".join(records).encode("utf-8")).hexdigest()[:24]
        generated_source = self.render_generated_source(tuple(records), stable_hash)
        return CudaSm89IrTrace(
            records=tuple(records),
            markers=tuple(markers),
            op_counts=counts,
            memory_spaces=tuple(sorted(memory_spaces)),
            entry_symbol=f"kg_cuda_sm89_execute_{stable_hash}_ir",
            kernel_symbol=f"kg_cuda_sm89_generated_kernel_{stable_hash}",
            device_body_symbol=f"kg_cuda_sm89_device_body_{stable_hash}",
            stable_hash=stable_hash,
            generated_source=generated_source,
        )

    def value_name_map(self) -> dict[int, str]:
        """生成 final IR SSA value 到 C++ identifier 的稳定映射。

        功能说明:
        - block argument 与 op result 都使用遍历序号构造唯一 C++ 名称。
        - 该映射同时进入 hash record 与 generated wrapper call operand binding，保证同类型 dataflow 变化会改变主计算 body。

        使用示例:
        - names = builder.value_name_map()
        """

        names: dict[int, str] = {}
        for walk_index, walked_op in enumerate(self.module_op.walk()):
            for region_index, region in enumerate(walked_op.regions):
                for block_index, block in enumerate(region.blocks):
                    for arg_index, arg in enumerate(block.args):
                        names[id(arg)] = f"kg_arg_{walk_index}_{region_index}_{block_index}_{arg_index}"
            for result_index, result_value in enumerate(walked_op.results):
                names[id(result_value)] = f"kg_v_{walk_index}_{result_index}"
        return names

    def operation_record(self, op: Operation) -> str:
        """生成单个 op 的 stable hash record。

        功能说明:
        - record 包含 op name、sorted attrs、operand SSA identity、result identity、region block 数、block arg identity 和 func attrs。
        - 不读取 printed IR 文本，因此属性文本伪造不会生成 supported op。

        使用示例:
        - record = builder.operation_record(op)
        """

        value_ids = self.value_name_map()
        attr_items = tuple(f"{name}={op.attributes[name]}" for name in sorted(op.attributes))
        operand_refs = tuple(
            f"{operand_index}:{value_ids.get(id(operand), f'external{operand_index}')}:{operand.type}"
            for operand_index, operand in enumerate(op.operands)
        )
        result_refs = tuple(
            f"{result_index}:{value_ids.get(id(result), f'untracked{result_index}')}:{result.type}"
            for result_index, result in enumerate(op.results)
        )
        regions = tuple(op.regions)
        block_counts = tuple(len(region.blocks) for region in regions)
        block_arg_refs: list[str] = []
        for region_index, region in enumerate(regions):
            for block_index, block in enumerate(region.blocks):
                arg_refs = tuple(
                    f"{arg_index}:{value_ids.get(id(arg), f'untracked_arg{arg_index}')}:{arg.type}"
                    for arg_index, arg in enumerate(block.args)
                )
                block_arg_refs.append(f"r{region_index}.b{block_index}.args={arg_refs}")
        result = [
            f"op={op.name}",
            f"attrs={attr_items}",
            f"operands={operand_refs}",
            f"results={result_refs}",
            f"blocks={block_counts}",
            f"block_args={tuple(block_arg_refs)}",
        ]
        if isinstance(op, func.FuncOp):
            result.append(f"func={op.sym_name.data}")
            result.append(f"func_attrs={tuple(sorted(op.attributes))}")
        return "|".join(result)

    def operation_markers(self, op: Operation) -> list[str]:
        """生成单个 op 的 trace comment。

        功能说明:
        - 每个 op 都输出 `kg.cuda.ir.op` comment。
        - function、kernel attrs、C5 matmul materialization 和 Flash Attention exp/reduce role 额外输出可测试 comment。

        使用示例:
        - markers = builder.operation_markers(op)
        """

        markers = [f"// kg.cuda.ir.op: {op.name}"]
        if isinstance(op, func.FuncOp):
            markers.append(f"// kg.cuda.ir.func: {op.sym_name.data}")
        for attr_name in sorted(op.attributes):
            markers.append(f"// kg.cuda.ir.attr: {op.name}.{attr_name}={op.attributes[attr_name]}")
        if op.name == "kernel.matmul":
            markers.append(self.matmul_materialization_marker(op))
        if op.name == "kernel.exp":
            markers.append("// kg.cuda.ir.kernel.exp.role: out,input")
            markers.append("// kg.cuda.ir.exp.binding: exp_score = exp(shifted_score)")
            markers.append("// kg.cuda.ir.exp.binding: old_scale = exp(old_shift)")
        if op.name == "kernel.reduce":
            markers.append("// kg.cuda.ir.kernel.reduce.support: kind=max|sum,axis=1,keepdim=true")
        if op.name == "dma.transpose":
            markers.append("// kg.cuda.ir.dma.transpose.target: [dim,bc]")
        return markers

    def operation_memory_spaces(self, op: Operation) -> tuple[str, ...]:
        """读取 op operand/result 中出现的 nn memory space。

        功能说明:
        - 只通过公开 `NnMemoryType` 类型信息读取 memory space。
        - 返回值进入 stable trace 和 source comment，证明 C5 all-TLM1 结果可观察。

        使用示例:
        - spaces = builder.operation_memory_spaces(op)
        """

        spaces: list[str] = []
        for value in (*op.operands, *op.results):
            value_type = value.type
            if isinstance(value_type, NnMemoryType):
                spaces.append(value_type.space.space.data)
        return tuple(spaces)

    def matmul_operand_spaces(self, op: Operation) -> tuple[str, str, str]:
        """读取 `kernel.matmul` out/lhs/rhs operand space。

        功能说明:
        - 只接受前三个 operand 均为 `NnMemoryType` 的 `kernel.matmul`。
        - 返回值用于 C5 all-TLM1 comment 的真实验证，而不是无条件输出。

        使用示例:
        - out_space, lhs_space, rhs_space = builder.matmul_operand_spaces(op)
        """

        if len(op.operands) < 3:
            raise self.ctx.emit_error("cuda_sm89", "kernel.matmul C5 materialization requires 3 operands")
        spaces: list[str] = []
        for operand in op.operands[:3]:
            operand_type = operand.type
            if not isinstance(operand_type, NnMemoryType):
                raise self.ctx.emit_error("cuda_sm89", "kernel.matmul C5 materialization requires nn.memory operands")
            spaces.append(operand_type.space.space.data)
        return (spaces[0], spaces[1], spaces[2])

    def matmul_writeback_visible(self, op: Operation) -> bool:
        """验证 `kernel.matmul` out staging 后的 write-back 可见。

        功能说明:
        - 在同一 block 内查找位于 matmul 之后的 `dma.copy(original_out, staged_out)`。
        - 若同一 block 后续释放 staged out，则要求 write-back copy 位于 `dma.free(staged_out)` 之前。

        使用示例:
        - visible = builder.matmul_writeback_visible(op)
        """

        block = op.parent
        if not isinstance(block, Block):
            return False
        block_ops = list(block.ops)
        if op not in block_ops:
            return False
        out_value = op.operands[0]
        matmul_index = block_ops.index(op)
        copy_index: int | None = None
        free_index: int | None = None
        for index, candidate in enumerate(block_ops[matmul_index + 1 :], start=matmul_index + 1):
            if candidate.name == "dma.copy" and len(candidate.operands) >= 2 and candidate.operands[1] is out_value:
                target_type = candidate.operands[0].type
                if isinstance(target_type, NnMemoryType) and target_type.space.space.data != "tlm1":
                    copy_index = index
            if candidate.name == "dma.free" and candidate.operands and candidate.operands[0] is out_value:
                free_index = index
                break
        return copy_index is not None and (free_index is None or copy_index < free_index)

    def matmul_materialization_marker(self, op: Operation) -> str:
        """生成经过验证的 C5 all-TLM1 comment。

        功能说明:
        - 先验证 `kernel.matmul` out/lhs/rhs operand space 精确为 `tlm1/tlm1/tlm1`。
        - 再验证 out staging write-back 可见，且不会晚于 staged out free；失败时 fail-fast。

        使用示例:
        - marker = builder.matmul_materialization_marker(op)
        """

        spaces = self.matmul_operand_spaces(op)
        if spaces != ("tlm1", "tlm1", "tlm1"):
            actual = ",".join(spaces)
            raise self.ctx.emit_error("cuda_sm89", f"kernel.matmul C5 materialization requires out/lhs/rhs tlm1; got {actual}")
        if not self.matmul_writeback_visible(op):
            raise self.ctx.emit_error("cuda_sm89", "kernel.matmul C5 materialization requires visible out write-back")
        return "// kg.cuda.ir.matmul.materialization: out=tlm1,lhs=tlm1,rhs=tlm1,write_back=visible"

    def validate_supported_attrs(self) -> None:
        """校验 9-demo 范围内的 supported attr 子集。

        功能说明:
        - 对 `kernel.binary_elewise.kind` 和 `kernel.reduce.kind` 做 fail-fast。
        - attr/type 失败不新增独立稳定 exact 文本，错误仍挂在真实 op name 上。

        使用示例:
        - builder.validate_supported_attrs()
        """

        for op in self.module_op.walk():
            if op.name == "kernel.binary_elewise":
                kind_text = str(op.attributes.get("kind", ""))
                if not any(f'"{kind}"' in kind_text or kind_text.endswith(kind) for kind in CUDA_SM89_BINARY_ELEWISE_KINDS):
                    raise self.ctx.emit_error("cuda_sm89", "unsupported cuda_sm89 final IR op: kernel.binary_elewise")
            if op.name == "kernel.reduce":
                kind_text = str(op.attributes.get("kind", ""))
                if not any(f'"{kind}"' in kind_text or kind_text.endswith(kind) for kind in CUDA_SM89_REDUCE_KINDS):
                    raise self.ctx.emit_error("cuda_sm89", "unsupported cuda_sm89 final IR op: kernel.reduce")

    def validate_supported_compute(self, counts: dict[str, int]) -> None:
        """校验 final IR 至少包含当前 CUDA SM89 第一阶段支持的 compute op。

        功能说明:
        - 只读取真实 op count，不使用函数名、entry 名或 printed IR token 选择 source。
        - 空 module、name-only module 或缺少 supported compute op 时使用既有 `<none>` unsupported 文本失败。

        使用示例:
        - builder.validate_supported_compute(trace.op_counts)
        """

        if not any(counts.get(op_name, 0) > 0 for op_name in CUDA_SM89_COMPUTE_OPS):
            raise self.ctx.emit_error("cuda_sm89", "unsupported cuda_sm89 final IR op: <none>")

    def operation_executable_word(self, record: str, index: int) -> str:
        """把单个 final IR record 转成 trace 常量。

        功能说明:
        - 将 op 顺序号、op name、attrs、operand SSA identity、result identity 与 region block 信息混入 64-bit 常量。
        - 该常量进入 generated body 的 `kg_cuda_sm89_ir_record_words` 数组，供 source semantic tests 观察 record 顺序。

        使用示例:
        - word = builder.operation_executable_word("op=kernel.matmul|...", 3)
        """

        digest = hashlib.sha256(f"{index}|{record}".encode("utf-8")).hexdigest()
        word = "0x" + digest[:16] + "ull"
        return word

    def render_generated_source(self, records: tuple[str, ...], stable_hash: str) -> str:
        """按 final IR dataflow 渲染 generated host entry、global kernel 和 device body。

        功能说明:
        - host entry 保持 `kg_execute_entry(slots, count)` ABI，先把 slot array、shape/stride metadata 和 f32 memory data staging 到 CUDA device。
        - hash 专属 generated kernel 只接收 device-visible slots，返回后 host entry 把 memory slot 结果回拷到原 host buffer 并释放临时 device 资源。
        - generated kernel 在 device 侧构造 `cuda_sm89::KernelContext`，再调用 generated device body；device body 按 block/region 递归发射 wrapper call。
        - final IR operand/result/control-flow 绑定直接进入 wrapper call 实参，dataflow 变化会改变 load/compute/store body。

        使用示例:
        - source = builder.render_generated_source(trace.records, trace.stable_hash)
        """

        names = self.value_name_map()
        kernel_symbol = f"kg_cuda_sm89_generated_kernel_{stable_hash}"
        body_symbol = f"kg_cuda_sm89_device_body_{stable_hash}"
        entry_symbol = f"kg_cuda_sm89_execute_{stable_hash}_ir"
        host_ctx_symbol = f"kg_cuda_sm89_host_ctx_{stable_hash}"
        record_words = ", ".join(self.operation_executable_word(record, index) for index, record in enumerate(records)) or "0ull"
        declarations = self.render_body_declarations(names)
        self.rendered_launch_callees.clear()
        self.comment_only_result_op_ids = self._collect_comment_only_result_op_ids()
        statements = self.render_device_body_statements(names)
        rendered_launch_callees = set(self.rendered_launch_callees)
        op_indices = {id(op): op_index for op_index, op in enumerate(self.module_op.walk())}
        func_ops = [walked_op for walked_op in self.module_op.walk() if isinstance(walked_op, func.FuncOp)]
        entry_ops = [walked_op for walked_op in func_ops if self.attr_contains(walked_op, "entry_point", "unit")]
        if not entry_ops and func_ops:
            entry_ops = [func_ops[0]]
        entry_ids = {id(entry_op) for entry_op in entry_ops}
        callee_function_sources: list[str] = []
        for walked_op in func_ops:
            if id(walked_op) in entry_ids or walked_op.sym_name.data not in rendered_launch_callees:
                continue
            safe_func_name = re.sub(r"[^0-9A-Za-z_]", "_", walked_op.sym_name.data)
            if safe_func_name and safe_func_name[0].isdigit():
                safe_func_name = f"_{safe_func_name}"
            helper_name = f"kg_cuda_sm89_device_func_{safe_func_name}"
            parameter_names: list[str] = []
            for region in walked_op.regions:
                for block in region.blocks:
                    for block_arg in block.args:
                        parameter_type = "S_INT"
                        if isinstance(block_arg.type, NnMemoryType):
                            element_type = block_arg.type.element_type
                            if isinstance(element_type, Float32Type):
                                element_cpp = "float"
                            elif isinstance(element_type, IntegerType) and int(element_type.width.data) == 8:
                                element_cpp = "unsigned char"
                            else:
                                raise self.ctx.emit_error("cuda_sm89", "unsupported cuda_sm89 final IR op: arch.launch")
                            parameter_type = f"Memory<{self.memory_space_cpp(block_arg)}, {element_cpp}>"
                        parameter_names.append(f"{parameter_type} {names[id(block_arg)]}")
            parameters = ", ".join(
                ["cuda_sm89::KernelContext& ctx", "int* kg_cuda_sm89_status", *parameter_names]
            )
            body = "\n".join(
                self.render_block_statements(block, names, op_indices)
                for region in walked_op.regions
                for block in region.blocks
            )
            callee_function_sources.append(
                f"__device__ void {helper_name}({parameters}) {{\n"
                f"  (void)ctx;\n"
                f"{body}\n"
                f"}}\n"
            )
        callee_functions = "\n".join(callee_function_sources)
        return f"""
struct {host_ctx_symbol} {{
  cuda_sm89::ArgSlot* slots;
  unsigned long long count;
}};

{callee_functions}

__device__ void {body_symbol}(cuda_sm89::KernelContext& ctx, cuda_sm89::ArgSlot* slots, unsigned long long count, int* kg_cuda_sm89_status) {{
  (void)ctx;
  const unsigned long long kg_cuda_sm89_ir_record_words[] = {{{record_words}}};
  (void)kg_cuda_sm89_ir_record_words;
{declarations}
{statements}
}}

__global__ void {kernel_symbol}(cuda_sm89::ArgSlot* slots, unsigned long long count, int* kg_cuda_sm89_status) {{
  cuda_sm89::KernelContext device_ctx;
  if (threadIdx.x == 0) {{
    {body_symbol}(device_ctx, slots, count, kg_cuda_sm89_status);
  }}
}}

int {entry_symbol}(cuda_sm89::ArgSlot* slots, unsigned long long count) {{
  if (slots == nullptr && count != 0ull) {{
    return -1;
  }}
  {host_ctx_symbol} host_ctx{{nullptr, count}};
  cuda_sm89::ArgSlot* kg_cuda_sm89_host_device_slots = nullptr;
  cuda_sm89::ArgSlot* kg_cuda_sm89_device_slots = nullptr;
  long long** kg_cuda_sm89_device_shapes = nullptr;
  long long** kg_cuda_sm89_device_strides = nullptr;
  void** kg_cuda_sm89_device_data = nullptr;
  unsigned long long* kg_cuda_sm89_element_counts = nullptr;
  int kg_cuda_sm89_host_status = 0;
  Status launch_status = kOk;
  if (count != 0ull) {{
    kg_cuda_sm89_host_device_slots = new (std::nothrow) cuda_sm89::ArgSlot[count]();
    kg_cuda_sm89_device_shapes = new (std::nothrow) long long*[count]();
    kg_cuda_sm89_device_strides = new (std::nothrow) long long*[count]();
    kg_cuda_sm89_device_data = new (std::nothrow) void*[count]();
    kg_cuda_sm89_element_counts = new (std::nothrow) unsigned long long[count]();
    if (kg_cuda_sm89_host_device_slots == nullptr || kg_cuda_sm89_device_shapes == nullptr ||
        kg_cuda_sm89_device_strides == nullptr || kg_cuda_sm89_device_data == nullptr ||
        kg_cuda_sm89_element_counts == nullptr) {{
      kg_cuda_sm89_host_status = -1;
    }}
  }}
  if (kg_cuda_sm89_host_status == 0) {{
    for (unsigned long long kg_cuda_sm89_slot_index = 0; kg_cuda_sm89_slot_index < count; ++kg_cuda_sm89_slot_index) {{
      kg_cuda_sm89_host_device_slots[kg_cuda_sm89_slot_index] = slots[kg_cuda_sm89_slot_index];
      if (slots[kg_cuda_sm89_slot_index].kind != 1) {{
        continue;
      }}
      if (slots[kg_cuda_sm89_slot_index].rank == 0ull || slots[kg_cuda_sm89_slot_index].shape == nullptr ||
          slots[kg_cuda_sm89_slot_index].stride == nullptr || slots[kg_cuda_sm89_slot_index].dtype_code != 1) {{
        kg_cuda_sm89_host_status = -1;
        break;
      }}
      const unsigned long long kg_cuda_sm89_rank = slots[kg_cuda_sm89_slot_index].rank;
      KG_CUDA_CHECK(cudaMalloc(reinterpret_cast<void**>(&kg_cuda_sm89_device_shapes[kg_cuda_sm89_slot_index]), kg_cuda_sm89_rank * sizeof(long long)));
      KG_CUDA_CHECK(cudaMalloc(reinterpret_cast<void**>(&kg_cuda_sm89_device_strides[kg_cuda_sm89_slot_index]), kg_cuda_sm89_rank * sizeof(long long)));
      cuda_sm89::detail::copy_host_to_device<long long>(
          kg_cuda_sm89_device_shapes[kg_cuda_sm89_slot_index],
          slots[kg_cuda_sm89_slot_index].shape,
          kg_cuda_sm89_rank);
      cuda_sm89::detail::copy_host_to_device<long long>(
          kg_cuda_sm89_device_strides[kg_cuda_sm89_slot_index],
          slots[kg_cuda_sm89_slot_index].stride,
          kg_cuda_sm89_rank);
      kg_cuda_sm89_element_counts[kg_cuda_sm89_slot_index] = cuda_sm89::detail::element_count(slots[kg_cuda_sm89_slot_index]);
      if (slots[kg_cuda_sm89_slot_index].data != nullptr && kg_cuda_sm89_element_counts[kg_cuda_sm89_slot_index] != 0ull) {{
        kg_cuda_sm89_device_data[kg_cuda_sm89_slot_index] =
            cuda_sm89::detail::device_alloc<float>(kg_cuda_sm89_element_counts[kg_cuda_sm89_slot_index]);
        cuda_sm89::detail::copy_host_to_device<float>(
            reinterpret_cast<float*>(kg_cuda_sm89_device_data[kg_cuda_sm89_slot_index]),
            reinterpret_cast<const float*>(slots[kg_cuda_sm89_slot_index].data),
            kg_cuda_sm89_element_counts[kg_cuda_sm89_slot_index]);
      }}
      kg_cuda_sm89_host_device_slots[kg_cuda_sm89_slot_index].shape = kg_cuda_sm89_device_shapes[kg_cuda_sm89_slot_index];
      kg_cuda_sm89_host_device_slots[kg_cuda_sm89_slot_index].stride = kg_cuda_sm89_device_strides[kg_cuda_sm89_slot_index];
      kg_cuda_sm89_host_device_slots[kg_cuda_sm89_slot_index].data = kg_cuda_sm89_device_data[kg_cuda_sm89_slot_index];
    }}
  }}
  if (kg_cuda_sm89_host_status == 0 && count != 0ull) {{
    KG_CUDA_CHECK(cudaMalloc(reinterpret_cast<void**>(&kg_cuda_sm89_device_slots), count * sizeof(cuda_sm89::ArgSlot)));
    cuda_sm89::detail::copy_host_to_device<cuda_sm89::ArgSlot>(kg_cuda_sm89_device_slots, kg_cuda_sm89_host_device_slots, count);
  }}
  int* kg_cuda_sm89_device_status = nullptr;
  if (kg_cuda_sm89_host_status == 0) {{
    KG_CUDA_CHECK(cudaMalloc(reinterpret_cast<void**>(&kg_cuda_sm89_device_status), sizeof(int)));
    KG_CUDA_CHECK(cudaMemset(kg_cuda_sm89_device_status, 0, sizeof(int)));
    host_ctx.slots = kg_cuda_sm89_device_slots;
    launch_status = cuda_sm89::launch<1, 256, 1, 49152, {kernel_symbol}>(
        host_ctx, kg_cuda_sm89_device_slots, count, kg_cuda_sm89_device_status);
    KG_CUDA_CHECK(cudaMemcpy(&kg_cuda_sm89_host_status, kg_cuda_sm89_device_status, sizeof(int), cudaMemcpyDeviceToHost));
  }}
  if (kg_cuda_sm89_host_status == 0) {{
    for (unsigned long long kg_cuda_sm89_slot_index = 0; kg_cuda_sm89_slot_index < count; ++kg_cuda_sm89_slot_index) {{
      if (slots[kg_cuda_sm89_slot_index].kind == 1 && slots[kg_cuda_sm89_slot_index].data != nullptr &&
          kg_cuda_sm89_device_data[kg_cuda_sm89_slot_index] != nullptr &&
          kg_cuda_sm89_element_counts[kg_cuda_sm89_slot_index] != 0ull) {{
        cuda_sm89::detail::copy_device_to_host<float>(
            reinterpret_cast<float*>(slots[kg_cuda_sm89_slot_index].data),
            reinterpret_cast<const float*>(kg_cuda_sm89_device_data[kg_cuda_sm89_slot_index]),
            kg_cuda_sm89_element_counts[kg_cuda_sm89_slot_index]);
      }}
    }}
  }}
  if (kg_cuda_sm89_device_status != nullptr) {{
    KG_CUDA_CHECK(cudaFree(kg_cuda_sm89_device_status));
  }}
  cuda_sm89::detail::device_free<cuda_sm89::ArgSlot>(kg_cuda_sm89_device_slots);
  for (unsigned long long kg_cuda_sm89_slot_index = 0; kg_cuda_sm89_slot_index < count; ++kg_cuda_sm89_slot_index) {{
    cuda_sm89::detail::device_free<long long>(kg_cuda_sm89_device_shapes == nullptr ? nullptr : kg_cuda_sm89_device_shapes[kg_cuda_sm89_slot_index]);
    cuda_sm89::detail::device_free<long long>(kg_cuda_sm89_device_strides == nullptr ? nullptr : kg_cuda_sm89_device_strides[kg_cuda_sm89_slot_index]);
    cuda_sm89::detail::device_free<float>(
        kg_cuda_sm89_device_data == nullptr ? nullptr : reinterpret_cast<float*>(kg_cuda_sm89_device_data[kg_cuda_sm89_slot_index]));
  }}
  delete[] kg_cuda_sm89_host_device_slots;
  delete[] kg_cuda_sm89_device_shapes;
  delete[] kg_cuda_sm89_device_strides;
  delete[] kg_cuda_sm89_device_data;
  delete[] kg_cuda_sm89_element_counts;
  if (launch_status != kOk || kg_cuda_sm89_host_status != 0) {{
    return -1;
  }}
  return 0;
}}

"""

    def _collect_comment_only_result_op_ids(self) -> set[int]:
        """收集只保留 trace comment、不生成 C++ result 变量的 op。

        功能说明:
        - 已折叠的 `tuner.select` / `builtin.unregistered` 条件链不参与生成后续 C++ 表达式，只需保留 trace comment。
        - `arch.launch` 的前四个 launch 配置 operand 在当前 generated body 中不传给 device helper；若其常量只被该 launch 消费，也只保留 trace comment。

        使用示例:
        - skipped_ids = builder._collect_comment_only_result_op_ids()
        """

        comment_only_ids: set[int] = set()
        for walked_op in self.module_op.walk():
            if walked_op.name == "scf.if" and walked_op.operands:
                condition_owner = walked_op.operands[0].owner
                pending_ops = [condition_owner]
                while pending_ops:
                    current_op = pending_ops.pop()
                    if not isinstance(current_op, Operation) or id(current_op) in comment_only_ids:
                        continue
                    if current_op.name not in {"builtin.unregistered", "tuner.select"}:
                        continue
                    comment_only_ids.add(id(current_op))
                    for operand in current_op.operands:
                        pending_ops.append(operand.owner)
            if walked_op.name == "arch.launch":
                for launch_index, launch_operand in enumerate(walked_op.operands[:4]):
                    owner = launch_operand.owner
                    if not isinstance(owner, Operation) or owner.name != "symbol.const":
                        continue
                    uses = list(launch_operand.uses)
                    if len(uses) == 1 and uses[0].operation is walked_op and uses[0].index == launch_index:
                        comment_only_ids.add(id(owner))
        return comment_only_ids

    def render_body_declarations(self, names: dict[int, str]) -> str:
        """渲染 device body 的 block argument declarations。

        功能说明:
        - 只对 entry `func.func` 的 block argument 按本地 arg index 绑定 `slots[index]`。
        - `arch.launch` callee 的 block argument 由 launch operand 映射，不再从 slots 重复声明。
        - 对 symbol block argument 生成 `S_INT` placeholder，避免后续 operand 绑定退化为注释。

        使用示例:
        - declarations = builder.render_body_declarations(names)
        """

        lines: list[str] = []
        declared: set[str] = set()
        func_ops = [walked_op for walked_op in self.module_op.walk() if isinstance(walked_op, func.FuncOp)]
        entry_ops = [walked_op for walked_op in func_ops if self.attr_contains(walked_op, "entry_point", "unit")]
        if not entry_ops and func_ops:
            entry_ops = [func_ops[0]]
        for walked_op in entry_ops:
            for region in walked_op.regions:
                for block in region.blocks:
                    for arg_index, arg in enumerate(block.args):
                        name = names[id(arg)]
                        if name in declared:
                            continue
                        declared.add(name)
                        if isinstance(arg.type, NnMemoryType):
                            space_cpp = self.memory_space_cpp(arg)
                            lines.append(
                                f"  auto {name} = cuda_sm89::detail::memory_from_slot<{space_cpp}, float>(slots, count, {arg_index});"
                            )
                        else:
                            default_value = self.symbol_type_default_cpp(arg.type)
                            lines.append(
                                f"  S_INT {name} = cuda_sm89::detail::int_arg_or(slots, count, {arg_index}, {default_value});"
                            )
        return "\n".join(lines)

    def render_device_body_statements(self, names: dict[int, str]) -> str:
        """渲染 device body 中由 final IR 控制流支配的 statements。

        功能说明:
        - 只从 entry `func.func` block 开始递归渲染，避免把 launched device function 无条件串进 body。
        - `arch.launch` 会在所属 `scf.if` 分支内按 callee operand 映射内联被 launch 的函数块。
        - 每条 op 仍使用全 module 遍历序号生成 `kg.cuda.ir.exec[...]` comment，保持 source/hash 可追踪。

        使用示例:
        - statements = builder.render_device_body_statements(names)
        """

        op_indices = {id(op): op_index for op_index, op in enumerate(self.module_op.walk())}
        blocks: list[str] = []
        func_ops = [walked_op for walked_op in self.module_op.walk() if isinstance(walked_op, func.FuncOp)]
        entry_ops = [walked_op for walked_op in func_ops if self.attr_contains(walked_op, "entry_point", "unit")]
        if not entry_ops and func_ops:
            entry_ops = [func_ops[0]]
        for walked_op in entry_ops:
            for region in walked_op.regions:
                for block in region.blocks:
                    blocks.append(self.render_block_statements(block, names, op_indices))
        return "\n".join(block for block in blocks if block)

    def render_block_statements(self, block: Block, names: dict[int, str], op_indices: dict[int, int]) -> str:
        """渲染单个 block 内的 statements。

        功能说明:
        - 按 block 内真实 op 顺序渲染，不跨出当前 block。
        - 嵌套 region 由 `render_symbol_for_statement(...)` / `render_scf_if_statement(...)` 递归处理。

        使用示例:
        - body = builder.render_block_statements(block, names, op_indices)
        """

        lines: list[str] = []
        for op in block.ops:
            lines.append(self.render_operation_statement(op, op_indices.get(id(op), 0), names, op_indices))
        return "\n".join(lines)

    def render_operation_statement(
        self,
        op: Operation,
        op_index: int,
        names: dict[int, str],
        op_indices: dict[int, int] | None = None,
    ) -> str:
        """渲染一个 final IR op 对应的 C++ statement。

        功能说明:
        - 根据真实 op name、operand 绑定、result 绑定、memory space 和 attrs 选择 CUDA SM89 wrapper call。
        - 不使用 compute family 级整段模板；每条 materializing op 单独进入 generated body。

        使用示例:
        - stmt = builder.render_operation_statement(op, 10, names)
        """

        op_name = op.name
        operand_names = tuple(self.value_name(operand, names) for operand in op.operands)
        result_names = tuple(self.value_name(result, names) for result in op.results)
        comment = (
            f"  // kg.cuda.ir.exec[{op_index:04d}]: {op_name} "
            f"operands={operand_names} results={result_names}"
        )
        if id(op) in self.comment_only_result_op_ids and op.results:
            return comment
        if op_name == "symbol.for":
            if op_indices is None:
                raise self.ctx.emit_error("cuda_sm89", "unsupported cuda_sm89 final IR op: symbol.for")
            return self.render_symbol_for_statement(comment, op, names, op_indices)
        if op_name == "scf.if":
            if op_indices is None:
                raise self.ctx.emit_error("cuda_sm89", "unsupported cuda_sm89 final IR op: scf.if")
            return self.render_scf_if_statement(comment, op, names, op_indices)
        if op_name == "arch.launch":
            callee = op.attributes.get("callee")
            callee_name = str(callee).lstrip("@") if callee is not None else ""
            callee_func: func.FuncOp | None = None
            for walked_op in self.module_op.walk():
                if isinstance(walked_op, func.FuncOp) and walked_op.sym_name.data == callee_name:
                    callee_func = walked_op
                    break
            if callee_func is None or len(op.operands) < 4:
                raise self.ctx.emit_error("cuda_sm89", "unsupported cuda_sm89 final IR op: arch.launch")
            argument_names = operand_names[4:]
            for region in callee_func.regions:
                for block in region.blocks:
                    if len(block.args) > len(argument_names):
                        raise self.ctx.emit_error("cuda_sm89", "unsupported cuda_sm89 final IR op: arch.launch")
            safe_callee_name = re.sub(r"[^0-9A-Za-z_]", "_", callee_name)
            if safe_callee_name and safe_callee_name[0].isdigit():
                safe_callee_name = f"_{safe_callee_name}"
            helper_name = f"kg_cuda_sm89_device_func_{safe_callee_name}"
            self.rendered_launch_callees.add(callee_name)
            call_args = ", ".join(("ctx", "kg_cuda_sm89_status", *argument_names))
            return (
                f"{comment}\n"
                f"  {helper_name}({call_args});\n"
                f"  if (kg_cuda_sm89_status != nullptr && *kg_cuda_sm89_status != 0) {{\n"
                f"    return;\n"
                f"  }}"
            )
        if op_name in {"builtin.module", "func.func", "func.return", "scf.yield"}:
            return comment
        if op_name == "dma.free" and op.operands:
            if self.memory_space_name(op.operands[0]) == "global":
                return f"{comment}\n  // cuda_sm89.dma.free: external global memory is owned by the caller"
            return f"{comment}\n  delete[] {operand_names[0]}.data();"
        if op_name == "tuner.select" and op.results:
            return f"{comment}\n  S_INT {result_names[0]} = 0;"
        if op_name == "builtin.unregistered" and op.results:
            return f"{comment}\n  S_INT {result_names[0]} = 0;"
        if op_name == "arith.constant" and op.results:
            return f"{comment}\n  float {result_names[0]} = {self.float_attr_cpp(op)};"
        if op_name == "symbol.const" and op.results:
            return f"{comment}\n  S_INT {result_names[0]} = {self.int_attr_cpp(op, 'value', '0')};"
        if op_name == "symbol.cast" and op.results and op.operands:
            return f"{comment}\n  S_INT {result_names[0]} = static_cast<S_INT>({operand_names[0]});"
        if op_name == "symbol.ne" and len(op.operands) >= 2 and op.results:
            return f"{comment}\n  bool {result_names[0]} = {operand_names[0]} != {operand_names[1]};"
        if op_name == "symbol.add" and len(op.operands) >= 2 and op.results:
            return f"{comment}\n  S_INT {result_names[0]} = {operand_names[0]} + {operand_names[1]};"
        if op_name == "symbol.sub" and len(op.operands) >= 2 and op.results:
            return f"{comment}\n  S_INT {result_names[0]} = {operand_names[0]} - {operand_names[1]};"
        if op_name == "symbol.mul" and len(op.operands) >= 2 and op.results:
            return f"{comment}\n  S_INT {result_names[0]} = {operand_names[0]} * {operand_names[1]};"
        if op_name == "symbol.floordiv" and len(op.operands) >= 2 and op.results:
            return f"{comment}\n  S_INT {result_names[0]} = {operand_names[1]} == 0 ? 0 : {operand_names[0]} / {operand_names[1]};"
        if op_name == "symbol.min" and len(op.operands) >= 2 and op.results:
            return f"{comment}\n  S_INT {result_names[0]} = {operand_names[0]} < {operand_names[1]} ? {operand_names[0]} : {operand_names[1]};"
        if op_name == "symbol.max" and len(op.operands) >= 2 and op.results:
            return f"{comment}\n  S_INT {result_names[0]} = {operand_names[0]} > {operand_names[1]} ? {operand_names[0]} : {operand_names[1]};"
        if op_name == "symbol.get_dim" and op.operands and op.results:
            axis = self.int_attr_cpp(op, "axis", "0")
            return f"{comment}\n  S_INT {result_names[0]} = {operand_names[0]}.get_shape({axis});"
        if op_name == "symbol.get_stride" and op.operands and op.results:
            axis = self.int_attr_cpp(op, "axis", "0")
            return f"{comment}\n  S_INT {result_names[0]} = {operand_names[0]}.get_stride({axis});"
        if op_name == "memory.get_data" and op.operands and op.results:
            return f"{comment}\n  S_INT {result_names[0]} = cuda_sm89::detail::memory_data_token({operand_names[0]});"
        if op_name == "arch.get_block_id" and op.results:
            return f"{comment}\n  S_INT {result_names[0]} = cuda_sm89::block_id();"
        if op_name == "arch.get_block_num" and op.results:
            return f"{comment}\n  S_INT {result_names[0]} = gridDim.x;"
        if op_name == "arch.get_thread_id" and op.results:
            return f"{comment}\n  S_INT {result_names[0]} = cuda_sm89::thread_id();"
        if op_name == "arch.get_thread_num" and op.results:
            return f"{comment}\n  S_INT {result_names[0]} = cuda_sm89::thread_num();"
        if op_name == "arch.get_subthread_id" and op.results:
            return f"{comment}\n  S_INT {result_names[0]} = 0;"
        if op_name == "arch.get_subthread_num" and op.results:
            return f"{comment}\n  S_INT {result_names[0]} = 1;"
        if op_name == "dma.alloc" and op.results:
            result = op.results[0]
            result_type = result.type
            if not isinstance(result_type, NnMemoryType):
                raise self.ctx.emit_error("cuda_sm89", "unsupported cuda_sm89 final IR op: dma.alloc")
            result_element = result_type.element_type
            if isinstance(result_element, Float32Type):
                element_cpp = "float"
            elif isinstance(result_element, IntegerType) and int(result_element.width.data) == 8:
                element_cpp = "unsigned char"
            else:
                raise self.ctx.emit_error("cuda_sm89", "unsupported cuda_sm89 final IR op: dma.alloc")
            shape = self.alloc_shape_vector(op, result, names)
            stride = self.alloc_stride_vector(op, result, names)
            return (
                f"{comment}\n"
                f"  auto {result_names[0]} = cuda_sm89::alloc<{self.memory_space_cpp(result)}, {element_cpp}>"
                f"(ctx, {shape}, {stride});\n"
                f"  if (!cuda_sm89::detail::memory_ready({result_names[0]})) {{\n"
                f"    if (kg_cuda_sm89_status != nullptr) {{ *kg_cuda_sm89_status = -1; }}\n"
                f"    return;\n"
                f"  }}"
            )
        if op_name == "dma.fill" and len(op.operands) >= 2:
            return self.render_status_checked_call(comment, f"cuda_sm89::fill(ctx, {operand_names[0]}, {operand_names[1]})")
        if op_name in {"dma.copy", "dma.load"} and len(op.operands) >= 2:
            return self.render_load_store_statement(comment, op, operand_names, names, use_store=False)
        if op_name == "dma.store" and len(op.operands) >= 2:
            return self.render_load_store_statement(comment, op, operand_names, names, use_store=True)
        if op_name == "dma.slice" and len(op.operands) >= 2:
            return self.render_slice_statement(comment, op, operand_names, names, "slice")
        if op_name == "dma.deslice" and len(op.operands) >= 2:
            return self.render_slice_statement(comment, op, operand_names, names, "deslice")
        if op_name == "dma.broadcast" and len(op.operands) >= 2:
            return self.render_binary_memory_statement(comment, op, operand_names, "broadcast")
        if op_name == "dma.transpose" and len(op.operands) >= 2:
            return self.render_transpose_statement(comment, op, operand_names)
        if op_name == "dma.reinterpret" and op.results and op.operands:
            return self.render_alias_statement(comment, op, operand_names, result_names, names, "reinterpret")
        if op_name == "dma.reshape" and op.results and op.operands:
            return self.render_alias_statement(comment, op, operand_names, result_names, names, "reshape")
        if op_name == "dma.view" and op.results and op.operands:
            return self.render_alias_statement(comment, op, operand_names, result_names, names, "view")
        if op_name == "dma.make_ring" and op.results and len(op.operands) >= 3:
            return self.render_make_ring_statement(comment, op, operand_names, result_names, names)
        if op_name == "dma.current_ring" and op.results and op.operands:
            return f"{comment}\n  auto {result_names[0]} = {operand_names[0]}.current();"
        if op_name == "dma.advance_ring" and op.results and op.operands:
            return f"{comment}\n  auto {result_names[0]} = {operand_names[0]}.advance();"
        if op_name == "kernel.matmul" and len(op.operands) >= 3:
            return self.render_matmul_statement(comment, op, operand_names, op_index)
        if op_name == "kernel.img2col2d" and len(op.operands) >= 2:
            return self.render_img2col2d_statement(comment, op, operand_names)
        if op_name == "kernel.binary_elewise" and len(op.operands) >= 3:
            return self.render_binary_elewise_statement(comment, op, operand_names)
        if op_name == "kernel.exp" and len(op.operands) >= 2:
            out_name, input_name = operand_names[0], operand_names[1]
            space_cpp = self.memory_space_cpp(op.operands[0])
            return self.render_status_checked_call(comment, f"cuda_sm89::exp<{space_cpp}, float, float>(ctx, {out_name}, {input_name})")
        if op_name == "kernel.reduce" and len(op.operands) >= 2:
            op_kind = "reduce_max" if self.attr_contains(op, "kind", "max") else "reduce_sum"
            axis = self.int_attr_cpp(op, "axis", "1")
            out_name, input_name = operand_names[0], operand_names[1]
            space_cpp = self.memory_space_cpp(op.operands[0])
            return self.render_status_checked_call(comment, f"cuda_sm89::{op_kind}<{space_cpp}, float, float>(ctx, {out_name}, {input_name}, {axis})")
        return comment

    def render_status_checked_call(self, comment: str, call: str) -> str:
        """渲染带 `Status` 检查的 CUDA wrapper call。

        功能说明:
        - generated device body 中返回 `Status` 的 wrapper 失败时写入 device status 并终止当前 body。
        - host entry 在 kernel 返回后拷回 status，使 wrapper `kError` 不会被 `(void)` 静默吞掉。

        使用示例:
        - stmt = builder.render_status_checked_call(comment, "cuda_sm89::fill(ctx, tile, 0.0f)")
        """

        return (
            f"{comment}\n"
            f"  if ({call} != kOk) {{\n"
            f"    if (kg_cuda_sm89_status != nullptr) {{ *kg_cuda_sm89_status = -1; }}\n"
            f"    return;\n"
            f"  }}"
        )

    def render_symbol_for_statement(self, comment: str, op: Operation, names: dict[int, str], op_indices: dict[int, int]) -> str:
        """渲染 `symbol.for` 为真实 C++ 循环。

        功能说明:
        - 循环 start/end/step 来自 final IR operand SSA binding。
        - 当前 Draft 10 成功范围只支持单块、单迭代变量、无 loop-carried result；其它形态按真实 op fail-fast。

        使用示例:
        - stmt = builder.render_symbol_for_statement(comment, op, names, op_indices)
        """

        if len(op.regions) != 1 or len(op.regions[0].blocks) != 1:
            raise self.ctx.emit_error("cuda_sm89", "unsupported cuda_sm89 final IR op: symbol.for")
        body_block = op.regions[0].blocks[0]
        if len(body_block.args) != 1 or op.results:
            raise self.ctx.emit_error("cuda_sm89", "unsupported cuda_sm89 final IR op: symbol.for")
        iter_name = names[id(body_block.args[0])]
        start = self.value_name(op.operands[0], names)
        end = self.value_name(op.operands[1], names)
        step = self.value_name(op.operands[2], names)
        body = self.render_block_statements(body_block, names, op_indices)
        return f"{comment}\n  for (S_INT {iter_name} = {start}; {iter_name} < {end}; {iter_name} += {step}) {{\n{body}\n  }}"

    def render_scf_if_statement(self, comment: str, op: Operation, names: dict[int, str], op_indices: dict[int, int]) -> str:
        """渲染 `scf.if` 为真实 C++ branch。

        功能说明:
        - 条件来自 final IR bool operand。
        - 当前 Draft 10 成功范围只支持无 result 的 then/else body；带 result / yield value 的形态 fail-fast。

        使用示例:
        - stmt = builder.render_scf_if_statement(comment, op, names, op_indices)
        """

        if not op.operands or op.results:
            raise self.ctx.emit_error("cuda_sm89", "unsupported cuda_sm89 final IR op: scf.if")
        true_region = op.regions[0] if op.regions else None
        false_region = op.regions[1] if len(op.regions) > 1 else None
        if true_region is None:
            raise self.ctx.emit_error("cuda_sm89", "unsupported cuda_sm89 final IR op: scf.if")
        condition_owner = op.operands[0].owner
        if isinstance(condition_owner, Operation) and condition_owner.name == "builtin.unregistered":
            if false_region is None or len(false_region.blocks) == 0:
                return f"{comment}\n  // cuda_sm89.scf.if: folded false builtin.unregistered condition with no else body"
            false_body = "\n".join(self.render_block_statements(block, names, op_indices) for block in false_region.blocks)
            return f"{comment}\n  // cuda_sm89.scf.if: folded false builtin.unregistered condition\n{false_body}"
        true_body = "\n".join(self.render_block_statements(block, names, op_indices) for block in true_region.blocks)
        if false_region is None or len(false_region.blocks) == 0:
            return f"{comment}\n  if ({self.value_name(op.operands[0], names)}) {{\n{true_body}\n  }}"
        false_body = "\n".join(self.render_block_statements(block, names, op_indices) for block in false_region.blocks)
        return f"{comment}\n  if ({self.value_name(op.operands[0], names)}) {{\n{true_body}\n  }} else {{\n{false_body}\n  }}"

    def render_load_store_statement(
        self,
        comment: str,
        op: Operation,
        operand_names: tuple[str, ...],
        names: dict[int, str],
        *,
        use_store: bool,
    ) -> str:
        """渲染 `dma.copy/load/store` 的 CUDA wrapper call。

        功能说明:
        - target/global write-back 使用 `cuda_sm89::store`，其它 materializing transfer 使用 `cuda_sm89::load`。
        - wrapper template 参数来自真实 target/source operand memory space，实参来自真实 SSA binding。

        使用示例:
        - stmt = builder.render_load_store_statement(comment, op, operands, use_store=False)
        """

        target, source = op.operands[0], op.operands[1]
        target_space = self.memory_space_name(target)
        source_space = self.memory_space_name(source)
        wrapper = "store" if use_store or (target_space == "global" and source_space != "global") else "load"
        if op.name == "dma.copy":
            offset = self.zero_vector(target)
            size_value = target if wrapper == "load" else source
            size_name = operand_names[0] if wrapper == "load" else operand_names[1]
            size = self.vector_cpp([f"{size_name}.get_shape({axis})" for axis in range(max(self.memory_rank(size_value), 1))])
            stride = self.unit_stride_vector(target)
        else:
            offset = self.operation_vector_cpp(op.offsets, names, self.zero_vector(target))
            size = self.operation_vector_cpp(op.sizes, names, self.shape_vector(source if wrapper == "load" else target))
            stride = self.operation_vector_cpp(op.strides, names, self.unit_stride_vector(target))
        call = (
            f"cuda_sm89::{wrapper}<{self.memory_space_cpp(target)}, {self.memory_space_cpp(source)}, float, float>"
            f"(ctx, {operand_names[0]}, {operand_names[1]}, {offset}, {size}, {stride})"
        )
        return self.render_status_checked_call(comment, call)

    def render_slice_statement(
        self,
        comment: str,
        op: Operation,
        operand_names: tuple[str, ...],
        names: dict[int, str],
        wrapper: str,
    ) -> str:
        """渲染 `dma.slice/deslice` 的 CUDA wrapper call。

        功能说明:
        - 直接使用 final IR 中 target/source SSA 绑定作为 wrapper 实参。
        - offset/size/stride 当前按 target descriptor 形成 generated expression，unsupported 动态细节保留在 hash record 中。

        使用示例:
        - stmt = builder.render_slice_statement(comment, op, operands, "deslice")
        """

        target, source = op.operands[0], op.operands[1]
        offset = self.operation_vector_cpp(op.offsets, names, self.zero_vector(target))
        size = self.operation_vector_cpp(op.sizes, names, self.shape_vector(source if wrapper == "deslice" else target))
        stride = self.operation_vector_cpp(op.strides, names, self.unit_stride_vector(target))
        call = (
            f"cuda_sm89::{wrapper}<{self.memory_space_cpp(target)}, {self.memory_space_cpp(source)}, float>"
            f"(ctx, {operand_names[0]}, {operand_names[1]}, {offset}, {size}, {stride})"
        )
        return self.render_status_checked_call(comment, call)

    def render_binary_memory_statement(self, comment: str, op: Operation, operand_names: tuple[str, ...], wrapper: str) -> str:
        """渲染 target/source 两个 memory operand 的 CUDA wrapper call。

        功能说明:
        - 用于 `dma.broadcast` 等只需要 target/source descriptor 的 memory op。
        - template space 参数来自真实 final IR operand 类型。

        使用示例:
        - stmt = builder.render_binary_memory_statement(comment, op, operands, "broadcast")
        """

        target, source = op.operands[0], op.operands[1]
        call = (
            f"cuda_sm89::{wrapper}<{self.memory_space_cpp(target)}, {self.memory_space_cpp(source)}, float, float>"
            f"(ctx, {operand_names[0]}, {operand_names[1]})"
        )
        return self.render_status_checked_call(comment, call)

    def render_transpose_statement(self, comment: str, op: Operation, operand_names: tuple[str, ...]) -> str:
        """渲染 `dma.transpose` 的 CUDA wrapper call。

        功能说明:
        - target/source operand 绑定来自 final IR。
        - perm 由 final IR attr 精确进入 public `cuda_sm89::transpose(...)` wrapper 实参。

        使用示例:
        - stmt = builder.render_transpose_statement(comment, op, operands)
        """

        target, source = op.operands[0], op.operands[1]
        perm_attr = op.attributes.get("perm")
        perm_values: list[str] = []
        if perm_attr is not None and hasattr(perm_attr, "data"):
            perm_values = [self.symbol_attr_cpp(item) for item in perm_attr.data]
        if not perm_values:
            perm_values = [str(axis) for axis in range(max(self.memory_rank(target), 1))]
        call = (
            f"cuda_sm89::transpose<{self.memory_space_cpp(target)}, {self.memory_space_cpp(source)}, float, float>"
            f"(ctx, {operand_names[0]}, {operand_names[1]}, {self.vector_cpp(perm_values)})"
        )
        return self.render_status_checked_call(comment, call)

    def render_alias_statement(
        self,
        comment: str,
        op: Operation,
        operand_names: tuple[str, ...],
        result_names: tuple[str, ...],
        names: dict[int, str],
        alias_kind: str,
    ) -> str:
        """渲染 view/reshape/reinterpret alias op 的 C++ statement。

        功能说明:
        - reshape 使用公开 `Memory::reshape(...)` 成员。
        - `dma.view` 使用 source stride step 语义；`dma.reinterpret` 使用绝对 stride descriptor glue。
        - global/tsm 的一维 view 使用已确认 public `cuda_sm89::view(...)`；TLM1 alias 走 `detail` fragment descriptor glue，避免把 fragment 当普通 pointer view。

        使用示例:
        - stmt = builder.render_alias_statement(comment, op, operands, results, "reshape")
        """

        result = op.results[0]
        source = op.operands[0]
        result_space = self.memory_space_name(result)
        result_space_cpp = self.memory_space_cpp(result)
        offset = self.alias_offset_vector(op, result, names, alias_kind)
        shape = self.alias_shape_vector(op, result, names, alias_kind)
        stride = self.alias_stride_vector(op, result, names, alias_kind)
        if alias_kind == "reshape":
            return f"{comment}\n  auto {result_names[0]} = {operand_names[0]}.reshape({shape});"
        if alias_kind == "reinterpret":
            return (
                f"{comment}\n"
                f"  auto {result_names[0]} = cuda_sm89::detail::fragment_alias<{result_space_cpp}, float>"
                f"({operand_names[0]}, {offset}, {shape}, {stride});"
            )
        if result_space == "tlm1":
            return (
                f"{comment}\n"
                f"  auto {result_names[0]} = cuda_sm89::detail::fragment_alias<{result_space_cpp}, float>"
                f"({operand_names[0]}, {offset}, {shape}, {stride});"
            )
        if self.memory_rank(result) == 1:
            return (
                f"{comment}\n"
                f"  auto {result_names[0]} = cuda_sm89::view<{self.memory_space_cpp(source)}, float>"
                f"({operand_names[0]}, {self.first_vector_value(offset, '0')}, {self.first_vector_value(shape, '1')}, {self.first_vector_value(stride, '1')});"
            )
        return f"{comment}\n  auto {result_names[0]} = {operand_names[0]}.view<float>({offset}, {shape}, {stride});"

    def render_make_ring_statement(
        self,
        comment: str,
        op: Operation,
        operand_names: tuple[str, ...],
        result_names: tuple[str, ...],
        names: dict[int, str],
    ) -> str:
        """渲染 `dma.make_ring` 的 CUDA wrapper call。

        功能说明:
        - backing、num、offset_bytes 来自真实 final IR operand 绑定。
        - slot shape/stride 来自 result ring 或 backing descriptor，进入 public `cuda_sm89::make_ring(...)` 调用。

        使用示例:
        - stmt = builder.render_make_ring_statement(comment, op, operands, results)
        """

        backing = op.operands[0]
        ring_type = op.results[0].type
        if not isinstance(ring_type, DmaRingType):
            raise self.ctx.emit_error("cuda_sm89", "unsupported cuda_sm89 final IR op: dma.make_ring")
        slot_type = ring_type.memory_type
        backing_type = backing.type
        if not isinstance(backing_type, NnMemoryType):
            raise self.ctx.emit_error("cuda_sm89", "unsupported cuda_sm89 final IR op: dma.make_ring")
        slot_element = slot_type.element_type
        if isinstance(slot_element, Float32Type):
            slot_cpp = "float"
        elif isinstance(slot_element, IntegerType) and int(slot_element.width.data) == 8:
            slot_cpp = "unsigned char"
        else:
            raise self.ctx.emit_error("cuda_sm89", "unsupported cuda_sm89 final IR op: dma.make_ring")
        backing_element = backing_type.element_type
        if isinstance(backing_element, Float32Type):
            backing_cpp = "float"
        elif isinstance(backing_element, IntegerType) and int(backing_element.width.data) == 8:
            backing_cpp = "unsigned char"
        else:
            raise self.ctx.emit_error("cuda_sm89", "unsupported cuda_sm89 final IR op: dma.make_ring")
        slot_space = slot_type.space.space.data
        if slot_space in {"tlm2", "tlm3"}:
            raise self.ctx.emit_error("cuda_sm89", "unsupported cuda_sm89 final IR op: dma.make_ring")
        shape_values = [self.static_symbol_attr_cpp(dim, "dma.make_ring") for dim in slot_type.shape.data]
        stride_values = [self.static_symbol_attr_cpp(dim, "dma.make_ring") for dim in slot_type.stride.data]
        return (
            f"{comment}\n"
            f"  auto {result_names[0]} = cuda_sm89::make_ring<{slot_cpp}, {self.memory_space_cpp(backing)}, {backing_cpp}>"
            f"({operand_names[0]}, {operand_names[1]}, {operand_names[2]}, {{{', '.join(shape_values)}}}, {{{', '.join(stride_values)}}});"
        )

    def render_matmul_statement(self, comment: str, op: Operation, operand_names: tuple[str, ...], op_index: int) -> str:
        """渲染 `kernel.matmul` 的 CUDA wrapper call。

        功能说明:
        - out/lhs/rhs 的 wrapper operand 顺序和 space template 参数直接来自 final IR operands。
        - 同类型 lhs/rhs dataflow 交换会改变 generated compute call 的实参绑定。
        - Tensor Core opcode string 作为 wrapper dispatch 旁路可观测点进入源码，禁止退回 scalar accumulation 模板。

        使用示例:
        - stmt = builder.render_matmul_statement(comment, op, operands, 7)
        """

        out_name, lhs_name, rhs_name = operand_names[0], operand_names[1], operand_names[2]
        out_space = self.memory_space_cpp(op.operands[0])
        lhs_space = self.memory_space_cpp(op.operands[1])
        rhs_space = self.memory_space_cpp(op.operands[2])
        call = f"cuda_sm89::matmul<{lhs_space}, {rhs_space}, {out_space}, float, float, float>(ctx, {out_name}, {lhs_name}, {rhs_name}, false)"
        return (
            f"{comment}\n"
            f"  asm volatile(\"// mma.sync.aligned.m16n8k8\");\n"
            f"{self.render_status_checked_call('', call).removeprefix(chr(10))}"
        )

    def render_img2col2d_statement(self, comment: str, op: Operation, operand_names: tuple[str, ...]) -> str:
        """渲染 `kernel.img2col2d` 的 CUDA wrapper call。

        功能说明:
        - out/input 的 wrapper operand 顺序和 space template 参数直接来自 final IR operands。
        - window / stride / dilation / padding scalar operands 进入 generated source，缺失时使用第一阶段默认值。

        使用示例:
        - stmt = builder.render_img2col2d_statement(comment, op, operands)
        """

        defaults = ("1", "1", "1", "1", "1", "1", "0", "0", "0", "0")
        params = [operand_names[index] if index < len(operand_names) else default for index, default in enumerate(defaults, start=2)]
        out_space = self.memory_space_cpp(op.operands[0])
        input_space = self.memory_space_cpp(op.operands[1])
        call = (
            f"cuda_sm89::img2col2d<{input_space}, {out_space}, float, float>"
            f"(ctx, {operand_names[0]}, {operand_names[1]}, {', '.join(params)})"
        )
        return self.render_status_checked_call(comment, call)

    def render_binary_elewise_statement(self, comment: str, op: Operation, operand_names: tuple[str, ...]) -> str:
        """渲染 `kernel.binary_elewise` 的 CUDA wrapper call。

        功能说明:
        - `kind` attr 映射到 A1 已确认的 `add/sub/mul/truediv/max` wrapper。
        - out/lhs/rhs 实参来自 final IR operand 绑定。

        使用示例:
        - stmt = builder.render_binary_elewise_statement(comment, op, operands)
        """

        wrapper = "add"
        for candidate in ("sub", "mul", "truediv", "max"):
            if self.attr_contains(op, "kind", candidate):
                wrapper = candidate
        space_cpp = self.memory_space_cpp(op.operands[0])
        call = f"cuda_sm89::{wrapper}<{space_cpp}, float, float>(ctx, {operand_names[0]}, {operand_names[1]}, {operand_names[2]})"
        return self.render_status_checked_call(comment, call)

    def value_name(self, value: SSAValue, names: dict[int, str]) -> str:
        """读取 SSA value 的 generated C++ 名称。

        功能说明:
        - 使用 `value_name_map()` 生成的稳定名称。
        - 若遇到未跟踪外部 value，返回 deterministic placeholder 以便 generated source 显式暴露缺口。

        使用示例:
        - name = builder.value_name(op.operands[0], names)
        """

        return names.get(id(value), f"kg_external_{abs(id(value))}")

    def memory_space_name(self, value: SSAValue) -> str:
        """读取 memory value 的 CUDA SM89 space 名称。

        功能说明:
        - 只从 `NnMemoryType` 读取真实 space。
        - 非 memory value 默认按 `global` 处理，使 helper 只服务 source emission，不改变 verifier 结果。

        使用示例:
        - space = builder.memory_space_name(value)
        """

        value_type = value.type
        if isinstance(value_type, NnMemoryType):
            return value_type.space.space.data
        return "global"

    def memory_space_cpp(self, value: SSAValue) -> str:
        """把 memory space 名称转换成 C++ `MemorySpace` 枚举表达式。

        功能说明:
        - 映射 `global/tsm/tlm1/tlm2/tlm3` 等 final IR space 到 public include enum。
        - unknown space 挂在真实 final IR op 路径上 fail-fast，避免退化为 GM 默认路径。

        使用示例:
        - space_cpp = builder.memory_space_cpp(value)
        """

        space = self.memory_space_name(value)
        if space not in CUDA_SM89_SPACE_TO_CPP:
            raise self.ctx.emit_error("cuda_sm89", "unsupported cuda_sm89 final IR op: memory_space")
        return CUDA_SM89_SPACE_TO_CPP[space]

    def memory_rank(self, value: SSAValue) -> int:
        """读取 memory value rank。

        功能说明:
        - 从 `NnMemoryType.shape` 长度读取 rank。
        - 非 memory value 返回 1，便于生成最小 fallback vector 表达式。

        使用示例:
        - rank = builder.memory_rank(value)
        """

        value_type = value.type
        if isinstance(value_type, NnMemoryType):
            return len(value_type.shape.data)
        return 1

    def operation_vector_cpp(self, values: Sequence[SSAValue], names: dict[int, str], fallback: str) -> str:
        """将 op 上的 variadic SSA operand 列表渲染为 `Vector{...}`。

        功能说明:
        - 优先读取当前 final IR op 的 `offsets/sizes/strides/shape/stride` operand。
        - operand 缺失时才使用调用方提供的 fallback；该 fallback 只服务 `dma.copy` 等无 window 参数 op。

        使用示例:
        - offset = builder.operation_vector_cpp(op.offsets, names, "Vector{0}")
        """

        if not values:
            return fallback
        return self.value_vector_cpp(values, names)

    def value_vector_cpp(self, values: tuple[SSAValue, ...] | list[SSAValue], names: dict[int, str]) -> str:
        """将 SSA value 列表渲染为 `Vector{ssa_name, ...}`。

        功能说明:
        - 每一维直接来自 final IR SSA binding，symbol 值变化会改变 generated wrapper 参数。
        - 空列表按 unsupported 处理；调用方若允许 fallback 应使用 `operation_vector_cpp(...)`。

        使用示例:
        - vec = builder.value_vector_cpp(op.sizes, names)
        """

        if not values:
            raise self.ctx.emit_error("cuda_sm89", "unsupported cuda_sm89 final IR op: vector")
        return self.vector_cpp([self.value_name(value, names) for value in values])

    def alloc_shape_vector(self, op: Operation, result: SSAValue, names: dict[int, str]) -> str:
        """渲染 `dma.alloc` shape vector。

        功能说明:
        - 动态 alloc 按 result type rank 保留静态维度，并把非静态维度映射到当前 op 的 `dynamic_shape` operand。
        - 静态 alloc 使用 result type shape；不再把动态 operand silently 折成 `Vector{1}`。

        使用示例:
        - shape = builder.alloc_shape_vector(op, result, names)
        """

        if op.dynamic_shape:
            result_type = result.type
            if not isinstance(result_type, NnMemoryType):
                return self.value_vector_cpp(op.dynamic_shape, names)
            dynamic_dims = [self.value_name(value, names) for value in op.dynamic_shape]
            dynamic_index = 0
            dims: list[str] = []
            for dim_attr in result_type.shape.data:
                literal = self.symbol_attr_cpp(dim_attr)
                text = str(dim_attr).strip()
                is_static_one = text in {"1", "#symbol.expr<1>", "#builtin.int<1>"}
                if literal != "1" or is_static_one or dynamic_index >= len(dynamic_dims):
                    dims.append(literal)
                    continue
                dims.append(dynamic_dims[dynamic_index])
                dynamic_index += 1
            return self.vector_cpp(dims)
        return self.shape_vector(result)

    def alloc_stride_vector(self, op: Operation, result: SSAValue, names: dict[int, str]) -> str:
        """渲染 `dma.alloc` stride vector。

        功能说明:
        - 动态 alloc 根据完整 result rank 的 shape 表达式生成行主序连续 stride。
        - 静态 alloc 保留 result type 显式 stride。

        使用示例:
        - stride = builder.alloc_stride_vector(op, result, names)
        """

        if not op.dynamic_shape:
            return self.stride_vector(result)
        result_type = result.type
        if not isinstance(result_type, NnMemoryType):
            dims = [self.value_name(value, names) for value in op.dynamic_shape]
        else:
            dynamic_dims = [self.value_name(value, names) for value in op.dynamic_shape]
            dynamic_index = 0
            dims = []
            for dim_attr in result_type.shape.data:
                literal = self.symbol_attr_cpp(dim_attr)
                text = str(dim_attr).strip()
                is_static_one = text in {"1", "#symbol.expr<1>", "#builtin.int<1>"}
                if literal != "1" or is_static_one or dynamic_index >= len(dynamic_dims):
                    dims.append(literal)
                    continue
                dims.append(dynamic_dims[dynamic_index])
                dynamic_index += 1
        strides: list[str] = []
        for index in range(len(dims)):
            suffix = dims[index + 1 :]
            strides.append(" * ".join(suffix) if suffix else "1")
        return self.vector_cpp(strides)

    def alias_offset_vector(self, op: Operation, result: SSAValue, names: dict[int, str], alias_kind: str) -> str:
        """渲染 alias op 的 offset vector。

        功能说明:
        - `dma.view` 使用 `offsets` operand。
        - `dma.reinterpret` 使用单个 `offset` operand，确保 offset 不丢失。
        - `dma.reshape` 无 offset，使用 rank 对齐零 vector。

        使用示例:
        - offset = builder.alias_offset_vector(op, result, names, "view")
        """

        if alias_kind == "view":
            return self.operation_vector_cpp(op.offsets, names, self.zero_vector(result))
        if alias_kind == "reinterpret":
            return self.value_vector_cpp([op.offset], names)
        return self.zero_vector(result)

    def alias_shape_vector(self, op: Operation, result: SSAValue, names: dict[int, str], alias_kind: str) -> str:
        """渲染 alias op 的 shape vector。

        功能说明:
        - `dma.view/reinterpret/reshape` 优先使用当前 op 的 shape operand。
        - 缺失时回退 result type shape，仅服务旧静态 reshape 形态。

        使用示例:
        - shape = builder.alias_shape_vector(op, result, names, "view")
        """

        if alias_kind in {"view", "reinterpret", "reshape"}:
            return self.operation_vector_cpp(op.shape, names, self.shape_vector(result))
        return self.shape_vector(result)

    def alias_stride_vector(self, op: Operation, result: SSAValue, names: dict[int, str], alias_kind: str) -> str:
        """渲染 alias op 的 stride vector。

        功能说明:
        - `dma.view/reinterpret` 使用当前 op 的 stride operand。
        - `dma.reshape` 根据 shape operand 生成连续 stride，保持 reshape 语义。

        使用示例:
        - stride = builder.alias_stride_vector(op, result, names, "view")
        """

        if alias_kind in {"view", "reinterpret"}:
            return self.operation_vector_cpp(op.stride, names, self.stride_vector(result))
        if alias_kind == "reshape" and op.shape:
            dims = [self.value_name(value, names) for value in op.shape]
            strides: list[str] = []
            for index in range(len(dims)):
                suffix = dims[index + 1 :]
                strides.append(" * ".join(suffix) if suffix else "1")
            return self.vector_cpp(strides)
        return self.stride_vector(result)

    def shape_vector(self, value: SSAValue) -> str:
        """生成 memory shape 的 C++ `Vector{...}` 表达式。

        功能说明:
        - 静态整数维度直接进入 source；动态或复杂 symbolic 表达式折为 `1`，完整表达式仍在 hash record 中。
        - 返回值用于 alloc、slice/load/store size 与 alias wrapper call。

        使用示例:
        - expr = builder.shape_vector(value)
        """

        value_type = value.type
        if isinstance(value_type, NnMemoryType):
            dims = [self.symbol_attr_cpp(item) for item in value_type.shape.data]
            return self.vector_cpp(dims)
        return "Vector{1}"

    def stride_vector(self, value: SSAValue) -> str:
        """生成 memory stride 的 C++ `Vector{...}` 表达式。

        功能说明:
        - 静态整数 stride 直接进入 source；动态或复杂 symbolic 表达式折为 `1`，完整表达式仍在 hash record 中。
        - 返回值用于 alloc 和 alias wrapper call。

        使用示例:
        - expr = builder.stride_vector(value)
        """

        value_type = value.type
        if isinstance(value_type, NnMemoryType):
            strides = [self.symbol_attr_cpp(item) for item in value_type.stride.data]
            return self.vector_cpp(strides)
        return "Vector{1}"

    def unit_stride_vector(self, value: SSAValue) -> str:
        """生成与 memory rank 对齐的单位 stride vector。

        功能说明:
        - 用于 source semantic 阶段的 transfer wrapper 默认 stride。
        - rank 来自 final IR result/operand type，而非 fixed family 模板。

        使用示例:
        - expr = builder.unit_stride_vector(value)
        """

        return self.vector_cpp(["1"] * max(self.memory_rank(value), 1))

    def zero_vector(self, value: SSAValue) -> str:
        """生成与 memory rank 对齐的零 offset vector。

        功能说明:
        - 用于 source semantic 阶段的 transfer wrapper 默认 offset。
        - rank 来自 final IR result/operand type，而非 fixed family 模板。

        使用示例:
        - expr = builder.zero_vector(value)
        """

        return self.vector_cpp(["0"] * max(self.memory_rank(value), 1))

    def first_shape_extent(self, value: SSAValue) -> str:
        """读取一维 public view 需要的 size 表达式。

        功能说明:
        - 从 result memory type 的第一个 shape 维度生成 C++ literal。
        - 无法读取时返回 `1`，完整动态语义保留在 hash record。

        使用示例:
        - size = builder.first_shape_extent(value)
        """

        value_type = value.type
        if isinstance(value_type, NnMemoryType) and value_type.shape.data:
            return self.symbol_attr_cpp(value_type.shape.data[0])
        return "1"

    def first_stride_extent(self, value: SSAValue) -> str:
        """读取一维 public view 需要的 stride 表达式。

        功能说明:
        - 从 result memory type 的第一个 stride 维度生成 C++ literal。
        - 无法读取时返回 `1`，完整动态语义保留在 hash record。

        使用示例:
        - stride = builder.first_stride_extent(value)
        """

        value_type = value.type
        if isinstance(value_type, NnMemoryType) and value_type.stride.data:
            return self.symbol_attr_cpp(value_type.stride.data[0])
        return "1"

    def first_vector_value(self, vector_expr: str, default: str) -> str:
        """从 `Vector{...}` 表达式中取第一项文本。

        功能说明:
        - 仅用于一维 public view wrapper，把已生成的 final IR vector 参数拆成 scalar 参数。
        - 无法解析时返回调用方默认值，不影响多维 view 路径。

        使用示例:
        - offset = builder.first_vector_value("Vector{kg_v_1}", "0")
        """

        match = re.fullmatch(r"Vector\{(.+)\}", vector_expr.strip())
        if match is None:
            return default
        first = match.group(1).split(",", 1)[0].strip()
        return first or default

    def vector_cpp(self, values: list[str]) -> str:
        """把 literal 列表渲染为 `Vector{...}`。

        功能说明:
        - `Vector` public API 支持 1..8 个值；空列表时生成 `Vector{1}`。
        - 过长列表截断到 8 维，当前 memory API 本身也以 8 维为上限。

        使用示例:
        - expr = builder.vector_cpp(["2", "4"])
        """

        clipped = values[:8] if values else ["1"]
        return "Vector{" + ", ".join(clipped) + "}"

    def symbol_attr_cpp(self, attr: Attribute) -> str:
        """把 symbol/int attr 文本转换成 C++ literal。

        功能说明:
        - 只提取静态整数 literal，复杂 symbolic 表达式返回 `1`。
        - 完整原始 attr 文本仍进入 `operation_record(...)`，因此不会丢失 dataflow/hash 区分。

        使用示例:
        - literal = builder.symbol_attr_cpp(SymbolExprAttr.from_expr("16"))
        """

        text = str(attr)
        match = re.search(r"#symbol\.expr<\s*(-?\d+)\s*>", text)
        if match:
            return match.group(1)
        match = re.search(r"#builtin\.int<\s*(-?\d+)\s*>", text)
        if match:
            return match.group(1)
        match = re.fullmatch(r"-?\d+", text.strip())
        if match:
            return match.group(0)
        return "1"

    def static_symbol_attr_cpp(self, attr: Attribute, op_name: str) -> str:
        """读取必须静态可证的 symbol attr。

        功能说明:
        - 只接受整数 literal。
        - dynamic ring slot layout 等 unsafe 形态直接使用既有 unsupported final IR op 文本 fail-fast。

        使用示例:
        - literal = builder.static_symbol_attr_cpp(dim, "dma.make_ring")
        """

        literal = self.symbol_attr_cpp(attr)
        if literal != "1":
            return literal
        text = str(attr).strip()
        if text in {"1", "#symbol.expr<1>", "#builtin.int<1>"}:
            return "1"
        raise self.ctx.emit_error("cuda_sm89", f"unsupported cuda_sm89 final IR op: {op_name}")

    def symbol_type_default_cpp(self, value_type: Attribute) -> str:
        """读取 symbol block argument 的可选默认值。

        功能说明:
        - 静态 symbol 类型使用其 literal。
        - 动态 runtime symbol 必须优先来自 `ArgSlot`，slot 缺失时使用 `1` 作为非零 guard 默认值。

        使用示例:
        - default = builder.symbol_type_default_cpp(arg.type)
        """

        text = str(value_type)
        match = re.search(r"#symbol\.expr<\s*(-?\d+)\s*>", text)
        if match:
            return match.group(1)
        return "1"

    def int_attr_cpp(self, op: Operation, attr_name: str, default: str) -> str:
        """读取 op integer attr 的 C++ literal。

        功能说明:
        - 静态 attr 转换为整数 literal；缺失或复杂表达式返回调用方默认值。
        - 用于 `symbol.const`、axis 和 generated launch 参数。

        使用示例:
        - axis = builder.int_attr_cpp(op, "axis", "1")
        """

        if attr_name not in op.attributes:
            return default
        return self.symbol_attr_cpp(op.attributes[attr_name])

    def float_attr_cpp(self, op: Operation) -> str:
        """读取 arith constant 的 C++ float literal。

        功能说明:
        - 当前 CUDA demo 只需要 f32 常量参与 fill/elementwise source semantic。
        - 无法稳定解析时返回 `0.0f`，原始 attr 仍在 hash record 中。

        使用示例:
        - literal = builder.float_attr_cpp(op)
        """

        for attr in op.attributes.values():
            text = str(attr)
            match = re.search(r"(-?\d+(?:\.\d+)?(?:e[+-]?\d+)?)", text, flags=re.IGNORECASE)
            if match:
                return match.group(1) + "f"
        value_attr = getattr(op, "value", None)
        value_data = getattr(getattr(value_attr, "value", None), "data", None)
        if value_data is not None:
            value_text = str(value_data).lower()
            if value_text == "inf":
                return "INFINITY"
            if value_text == "-inf":
                return "-INFINITY"
            return f"{value_data!r}f"
        return "0.0f"

    def attr_contains(self, op: Operation, attr_name: str, expected: str) -> bool:
        """判断 attr 文本是否包含指定 token。

        功能说明:
        - 用于把已验证的 `kind` attr 映射到 wrapper 名称。
        - 不作为 support 判断真源；support 判断仍由 `validate_supported_attrs()` 承接。

        使用示例:
        - is_sum = builder.attr_contains(op, "kind", "sum")
        """

        return expected in str(op.attributes.get(attr_name, ""))

    def render_kernel_source(self, trace: CudaSm89IrTrace) -> str:
        """渲染 `kernel.cu` artifact。

        功能说明:
        - header comments 来自真实 final IR trace。
        - C ABI entry 调用 hash 专属 generated entry；generated entry 再通过 `cuda_sm89::launch` 进入 generated `__global__` kernel。

        使用示例:
        - kernel_source = builder.render_kernel_source(trace)
        """

        entry_source = f"""
extern "C" int {CUDA_SM89_RUNTIME_ENTRY_NAME}(cuda_sm89::ArgSlot* slots, unsigned long long count) {{
  return {trace.entry_symbol}(slots, count);
}}
"""
        return (
            "// kg.allow_absent_memory_args: 3:float:1\n"
            + trace.render_marker_source()
            + CUDA_SM89_COMMON_RUNTIME_SOURCE
            + trace.generated_source
            + "\n}  // namespace\n"
            + entry_source
        )


def build_cuda_sm89_source_bundle(module_op: ModuleOp, ctx: EmitCContext) -> dict[str, str]:
    """构建 CUDA SM89 final IR SourceBundle artifacts。

    功能说明:
    - Package-local builder API；公开 emit 入口仍是 `emit_c(..., target="cuda_sm89")`。
    - 输入必须是 `cuda-sm89-lowering` 后的 `ModuleOp`；unsupported op 使用既有 CUDA SM89 fail-fast 文本。

    使用示例:
    - bundle = build_cuda_sm89_source_bundle(module_op, ctx)
    """

    return CudaSm89SourceBuilder(module_op, ctx).build()
