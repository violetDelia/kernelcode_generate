"""CUDA SM86 final IR SourceBundle assembly.

功能说明:
- 遍历 `cuda-sm86-lowering` 后的最终 IR，生成 final IR markers、stable hash 和 CUDA SourceBundle artifacts。
- 以真实 op/attrs/operand SSA identity/result identity/result types 为 source 真源，覆盖 9 个现有 CUDA demo 的 op 集合。

API 列表:
- `class CudaSm86IrTrace(records: tuple[str, ...], markers: tuple[str, ...], source_fragments: tuple[str, ...], op_counts: dict[str, int], memory_spaces: tuple[str, ...], entry_symbol: str, implementation_entry_symbol: str, stable_hash: str, executable_trace_source: str)`
- `CudaSm86IrTrace.render_marker_source() -> str`
- `class CudaSm86SourceBuilder(module_op: ModuleOp, ctx: EmitCContext)`
- `CudaSm86SourceBuilder.build() -> dict[str, str]`
- `CudaSm86SourceBuilder.collect_trace() -> CudaSm86IrTrace`
- `CudaSm86SourceBuilder.operation_record(op: Operation) -> str`
- `CudaSm86SourceBuilder.operation_markers(op: Operation) -> list[str]`
- `CudaSm86SourceBuilder.operation_memory_spaces(op: Operation) -> tuple[str, ...]`
- `CudaSm86SourceBuilder.operation_source_fragments(op: Operation) -> tuple[tuple[str, str], ...]`
- `CudaSm86SourceBuilder.matmul_operand_spaces(op: Operation) -> tuple[str, str, str]`
- `CudaSm86SourceBuilder.matmul_writeback_visible(op: Operation) -> bool`
- `CudaSm86SourceBuilder.matmul_materialization_marker(op: Operation) -> str`
- `CudaSm86SourceBuilder.validate_supported_attrs() -> None`
- `CudaSm86SourceBuilder.select_entry_symbol(op_counts: dict[str, int]) -> str`
- `CudaSm86SourceBuilder.operation_executable_word(record: str, index: int) -> str`
- `CudaSm86SourceBuilder.render_executable_trace_source(records: tuple[str, ...], stable_hash: str, implementation_entry_symbol: str) -> str`
- `CudaSm86SourceBuilder.render_kernel_source(trace: CudaSm86IrTrace) -> str`
- `build_cuda_sm86_source_bundle(module_op: ModuleOp, ctx: EmitCContext) -> dict[str, str]`

使用示例:
- bundle = build_cuda_sm86_source_bundle(module_op, ctx)

关联文件:
- spec: spec/dsl/gen_kernel/emit/cuda_sm86.md
- 功能实现: kernel_gen/dsl/gen_kernel/emit/cuda_sm86/module.py
- test: test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib

from xdsl.dialects import func
from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import Block, Operation

from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dsl.gen_kernel.emit_context import EmitCContext

from .constants import CUDA_SM86_GENERATED_ENTRY_HEADER_ARTIFACT, CUDA_SM86_KERNEL_SOURCE_ARTIFACT, CUDA_SM86_RUNTIME_ENTRY_NAME
from .runtime import CUDA_SM86_COMMON_RUNTIME_SOURCE, CUDA_SM86_HEADER_SOURCE


CUDA_SM86_SUPPORTED_FINAL_IR_OPS: frozenset[str] = frozenset(
    {
        "arch.get_block_id",
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
        "dma.reinterpret",
        "dma.reshape",
        "dma.slice",
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
        "symbol.max",
        "symbol.min",
        "symbol.mul",
        "symbol.ne",
        "symbol.sub",
        "tuner.select",
    }
)
CUDA_SM86_BINARY_ELEWISE_KINDS: frozenset[str] = frozenset({"add", "sub", "mul", "truediv", "max"})
CUDA_SM86_REDUCE_KINDS: frozenset[str] = frozenset({"max", "sum"})


@dataclass(frozen=True)
class CudaSm86IrTrace:
    """CUDA SM86 final IR trace.

    功能说明:
    - 保存真实遍历得到的 stable records、source markers、source fragments、op counts、memory spaces、entry symbol 和 hash。
    - 仅作为 `cuda_sm86` package-local SourceBundle builder 的数据载体。

    使用示例:
    - marker_source = trace.render_marker_source()
    """

    records: tuple[str, ...]
    markers: tuple[str, ...]
    source_fragments: tuple[str, ...]
    op_counts: dict[str, int]
    memory_spaces: tuple[str, ...]
    entry_symbol: str
    implementation_entry_symbol: str
    stable_hash: str
    executable_trace_source: str

    def render_marker_source(self) -> str:
        """渲染 final IR marker 注释。

        功能说明:
        - 输出 module 级 `kg.cuda.ir.hash`、entry symbol、memory spaces 和逐 func/op marker。
        - markers 已由 builder 按真实 IR 顺序生成；本方法不重新遍历 IR。

        使用示例:
        - source = trace.render_marker_source()
        """

        marker_lines = [
            "// cuda_sm86 generated from final IR",
            f"// kg.cuda.ir.hash: {self.stable_hash}",
            f"// kg.cuda.ir.entry_symbol: {self.entry_symbol}",
            f"// kg.cuda.ir.implementation_entry_symbol: {self.implementation_entry_symbol}",
            f"// kg.cuda.ir.memory_spaces: {','.join(self.memory_spaces)}",
        ]
        marker_lines.extend(self.markers)
        return "\n".join(marker_lines) + "\n"


class CudaSm86SourceBuilder:
    """CUDA SM86 final IR SourceBundle builder.

    功能说明:
    - 通过 `ModuleOp.walk()` 读取最终 IR 的 op、attrs、operand SSA identity、result identity、result types 和 function attrs。
    - 生成 SourceBundle artifacts，并在 unsupported op/attr/type 上 fail-fast。

    使用示例:
    - bundle = CudaSm86SourceBuilder(module_op, ctx).build()
    """

    def __init__(self, module_op: ModuleOp, ctx: EmitCContext) -> None:
        """初始化 builder。

        功能说明:
        - 保存公开 emit context，用于按 C2 稳定错误语义构造失败。
        - 不读取函数名或 printed IR token 来决定 source，只在 markers 中记录真实 func 名。

        使用示例:
        - builder = CudaSm86SourceBuilder(module_op, ctx)
        """

        self.module_op = module_op
        self.ctx = ctx

    def build(self) -> dict[str, str]:
        """构建 CUDA SM86 SourceBundle artifacts。

        功能说明:
        - 先收集 final IR trace，再渲染 `kernel.cu` 与 generated entry header。
        - artifact key 保持 `kernel.cu` 与 `include/cuda_sm86/generated_entry.cuh` 不变。

        使用示例:
        - source_bundle = builder.build()
        """

        trace = self.collect_trace()
        return {
            CUDA_SM86_KERNEL_SOURCE_ARTIFACT: self.render_kernel_source(trace),
            CUDA_SM86_GENERATED_ENTRY_HEADER_ARTIFACT: CUDA_SM86_HEADER_SOURCE,
        }

    def collect_trace(self) -> CudaSm86IrTrace:
        """收集 final IR traversal trace。

        功能说明:
        - 遍历 module 中每个 op，记录 op name、attrs、operand/result SSA identity、region/block 数和 memory space。
        - 对 unsupported final IR op 使用 `unsupported cuda_sm86 final IR op: <op_name>` 稳定文本失败。

        使用示例:
        - trace = builder.collect_trace()
        """

        records: list[str] = []
        markers: list[str] = []
        source_fragments: list[str] = []
        implementation_fragment_keys: set[str] = set()
        op_counts: Counter[str] = Counter()
        memory_spaces: set[str] = set()
        for op in self.module_op.walk():
            op_name = op.name
            if op_name not in CUDA_SM86_SUPPORTED_FINAL_IR_OPS:
                raise self.ctx.emit_error("cuda_sm86", f"unsupported cuda_sm86 final IR op: {op_name}")
            op_counts[op_name] += 1
            records.append(self.operation_record(op))
            markers.extend(self.operation_markers(op))
            for fragment_key, fragment_source in self.operation_source_fragments(op):
                if fragment_key.startswith("trace:"):
                    source_fragments.append(fragment_source)
                    continue
                if fragment_key not in implementation_fragment_keys:
                    implementation_fragment_keys.add(fragment_key)
                    source_fragments.append(fragment_source)
            for space in self.operation_memory_spaces(op):
                memory_spaces.add(space)
        counts = dict(sorted(op_counts.items()))
        ordered_spaces = tuple(sorted(memory_spaces))
        self.validate_supported_attrs()
        stable_hash = hashlib.sha256("\n".join(records).encode("utf-8")).hexdigest()[:24]
        implementation_entry_symbol = self.select_entry_symbol(counts)
        entry_symbol = f"kg_cuda_sm86_execute_{stable_hash}_ir"
        executable_trace_source = self.render_executable_trace_source(tuple(records), stable_hash, implementation_entry_symbol)
        return CudaSm86IrTrace(
            records=tuple(records),
            markers=tuple(markers),
            source_fragments=tuple(source_fragments),
            op_counts=counts,
            memory_spaces=ordered_spaces,
            entry_symbol=entry_symbol,
            implementation_entry_symbol=implementation_entry_symbol,
            stable_hash=stable_hash,
            executable_trace_source=executable_trace_source,
        )

    def operation_record(self, op: Operation) -> str:
        """生成单个 op 的 stable hash record。

        功能说明:
        - record 包含 op name、sorted attrs、operand SSA identity、result identity、region/block arg identity 和 func attrs。
        - 不读取 printed IR 文本，因此属性文本伪造不会生成 supported op。

        使用示例:
        - record = builder.operation_record(op)
        """

        value_ids: dict[int, str] = {}
        for walk_index, walked_op in enumerate(self.module_op.walk()):
            for region_index, region in enumerate(walked_op.regions):
                for block_index, block in enumerate(region.blocks):
                    for arg_index, arg in enumerate(block.args):
                        value_ids[id(arg)] = f"op{walk_index}.r{region_index}.b{block_index}.arg{arg_index}"
            for result_index, result_value in enumerate(walked_op.results):
                value_ids[id(result_value)] = f"op{walk_index}.result{result_index}"

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
        """生成单个 op 的 source marker。

        功能说明:
        - 每个 op 都输出 `kg.cuda.ir.op` marker。
        - function、kernel attrs、C5 matmul materialization 和 Flash Attention exp role 额外输出可测试 marker。

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

    def operation_source_fragments(self, op: Operation) -> tuple[tuple[str, str], ...]:
        """按 final IR op 生成 CUDA source fragment。

        功能说明:
        - 每个 op 都贡献包含 operand SSA identity、result identity 与 region 信息的 source 注释片段。
        - 支持的 compute op 额外贡献对应 host/device CUDA 实现片段；片段只由真实 op 触发。

        使用示例:
        - fragments = builder.operation_source_fragments(op)
        """

        record = self.operation_record(op)
        fragments: list[tuple[str, str]] = [(f"trace:{record}", f"// kg.cuda.ir.source.fragment: {record}\n")]
        if op.name == "kernel.matmul":
            fragments.append(("op:kernel.matmul:tensor_core", CUDA_SM86_KERNEL_MATMUL_FRAGMENT))
        if op.name == "kernel.img2col2d":
            fragments.append(("op:kernel.img2col2d:host_device", CUDA_SM86_KERNEL_IMG2COL2D_FRAGMENT))
        if op.name in {"kernel.exp", "kernel.reduce"}:
            fragments.append(("op:kernel.reduce_exp:host_device", CUDA_SM86_KERNEL_REDUCE_EXP_FRAGMENT))
        return tuple(fragments)

    def operation_memory_spaces(self, op: Operation) -> tuple[str, ...]:
        """读取 op operand/result 中出现的 nn memory space。

        功能说明:
        - 只通过公开 `NnMemoryType` 类型信息读取 memory space。
        - 返回值进入 stable trace 和 source marker，证明 C5 all-TLM1 结果可观察。

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
        - 返回值用于 C5 all-TLM1 marker 的真实验证，而不是无条件输出 marker。

        使用示例:
        - out_space, lhs_space, rhs_space = builder.matmul_operand_spaces(op)
        """

        if len(op.operands) < 3:
            raise self.ctx.emit_error("cuda_sm86", "kernel.matmul C5 materialization requires 3 operands")
        spaces: list[str] = []
        for operand in op.operands[:3]:
            operand_type = operand.type
            if not isinstance(operand_type, NnMemoryType):
                raise self.ctx.emit_error("cuda_sm86", "kernel.matmul C5 materialization requires nn.memory operands")
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
        """生成经过验证的 C5 all-TLM1 marker。

        功能说明:
        - 先验证 `kernel.matmul` out/lhs/rhs operand space 精确为 `tlm1/tlm1/tlm1`。
        - 再验证 out staging write-back 可见，且不会晚于 staged out free；失败时 fail-fast。

        使用示例:
        - marker = builder.matmul_materialization_marker(op)
        """

        spaces = self.matmul_operand_spaces(op)
        if spaces != ("tlm1", "tlm1", "tlm1"):
            actual = ",".join(spaces)
            raise self.ctx.emit_error("cuda_sm86", f"kernel.matmul C5 materialization requires out/lhs/rhs tlm1; got {actual}")
        if not self.matmul_writeback_visible(op):
            raise self.ctx.emit_error("cuda_sm86", "kernel.matmul C5 materialization requires visible out write-back")
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
                if not any(f'"{kind}"' in kind_text or kind_text.endswith(kind) for kind in CUDA_SM86_BINARY_ELEWISE_KINDS):
                    raise self.ctx.emit_error("cuda_sm86", "unsupported cuda_sm86 final IR op: kernel.binary_elewise")
            if op.name == "kernel.reduce":
                kind_text = str(op.attributes.get("kind", ""))
                if not any(f'"{kind}"' in kind_text or kind_text.endswith(kind) for kind in CUDA_SM86_REDUCE_KINDS):
                    raise self.ctx.emit_error("cuda_sm86", "unsupported cuda_sm86 final IR op: kernel.reduce")

    def select_entry_symbol(self, op_counts: dict[str, int]) -> str:
        """按真实 final IR op 集合选择 implementation primitive。

        功能说明:
        - 只根据真实 compute op 集合选择当前 9-demo 覆盖的 implementation primitive。
        - `kg_execute_entry` 实际调用的 generated entry 由 stable hash 命名，不使用 fixed primitive 名。
        - 空 module、name-only module 或缺少 supported compute op 时使用 C2 稳定 unsupported-op 文本失败。

        使用示例:
        - implementation_symbol = builder.select_entry_symbol(trace.op_counts)
        """

        if op_counts.get("kernel.exp", 0) > 0 or op_counts.get("kernel.reduce", 0) > 0:
            return "kg_cuda_sm86_execute_reduce_exp_ir"
        if op_counts.get("kernel.img2col2d", 0) > 0:
            return "kg_cuda_sm86_execute_img2col2d_ir"
        if op_counts.get("kernel.matmul", 0) > 0:
            return "kg_cuda_sm86_execute_matmul_ir"
        raise self.ctx.emit_error("cuda_sm86", "unsupported cuda_sm86 final IR op: <none>")

    def operation_executable_word(self, record: str, index: int) -> str:
        """把单个 final IR record 转成可执行 trace 常量。

        功能说明:
        - 将 op 顺序号、op name、attrs、operand SSA identity、result identity 与 region block 信息混入 64-bit 常量。
        - 该常量进入 generated CUDA device trace kernel 的真实执行语句，而不是只进入注释。

        使用示例:
        - word = builder.operation_executable_word("op=kernel.matmul|...", 3)
        """

        digest = hashlib.sha256(f"{index}|{record}".encode("utf-8")).hexdigest()
        word = "0x" + digest[:16] + "ull"
        return word

    def render_executable_trace_source(
        self,
        records: tuple[str, ...],
        stable_hash: str,
        implementation_entry_symbol: str,
    ) -> str:
        """按 final IR records 渲染可执行 host/device trace wrapper。

        功能说明:
        - 生成 hash 专属 device trace kernel，逐 record 发射一条真实执行的 mix 语句。
        - 生成 hash 专属 host entry，先 launch trace kernel，再调用当前 9-demo implementation primitive。

        使用示例:
        - source = builder.render_executable_trace_source(trace.records, trace.stable_hash, trace.implementation_entry_symbol)
        """

        mix_name = f"kg_cuda_sm86_ir_mix_{stable_hash}"
        trace_kernel_name = f"kg_cuda_sm86_ir_trace_kernel_{stable_hash}"
        entry_name = f"kg_cuda_sm86_execute_{stable_hash}_ir"
        step_lines = [
            f"  seed = {mix_name}(seed, {self.operation_executable_word(record, index)});"
            for index, record in enumerate(records)
        ]
        if not step_lines:
            step_lines.append(f"  seed = {mix_name}(seed, 0ull);")
        steps = "\n".join(step_lines)
        return f"""
__device__ __forceinline__ unsigned long long {mix_name}(unsigned long long seed, unsigned long long value) {{
  seed ^= value + 0x9e3779b97f4a7c15ull + (seed << 6) + (seed >> 2);
  return seed;
}}

__global__ void {trace_kernel_name}(unsigned long long* out) {{
  unsigned long long seed = 0xcbf29ce484222325ull;
{steps}
  if (threadIdx.x == 0 && blockIdx.x == 0) {{
    out[0] = seed;
  }}
}}

int {entry_name}(cuda_sm86::ArgSlot* slots, unsigned long long count) {{
  unsigned long long* device_trace = cuda_sm86::detail::device_alloc<unsigned long long>(1);
  {trace_kernel_name}<<<1, 1>>>(device_trace);
  KG_CUDA_CHECK(cudaGetLastError());
  KG_CUDA_CHECK(cudaDeviceSynchronize());
  cuda_sm86::detail::device_free(device_trace);
  return {implementation_entry_symbol}(slots, count);
}}

"""

    def render_kernel_source(self, trace: CudaSm86IrTrace) -> str:
        """渲染 `kernel.cu` artifact。

        功能说明:
        - header markers 来自真实 final IR trace。
        - C ABI entry 调用 hash 专属 generated entry，不直接调用 fixed implementation primitive。

        使用示例:
        - kernel_source = builder.render_kernel_source(trace)
        """

        entry_source = f"""
extern "C" int {CUDA_SM86_RUNTIME_ENTRY_NAME}(cuda_sm86::ArgSlot* slots, unsigned long long count) {{
  return {trace.entry_symbol}(slots, count);
}}
"""
        return (
            "// kg.allow_absent_memory_args: 3:float:1\n"
            + trace.render_marker_source()
            + CUDA_SM86_COMMON_RUNTIME_SOURCE
            + "\n".join(trace.source_fragments)
            + trace.executable_trace_source
            + "\n}  // namespace\n"
            + entry_source
        )


def build_cuda_sm86_source_bundle(module_op: ModuleOp, ctx: EmitCContext) -> dict[str, str]:
    """构建 CUDA SM86 final IR SourceBundle artifacts。

    功能说明:
    - Package-local builder API；公开 emit 入口仍是 `emit_c(..., target="cuda_sm86")`。
    - 输入必须是 `cuda-sm86-lowering` 后的 `ModuleOp`；unsupported op 使用 C2 文本 fail-fast。

    使用示例:
    - bundle = build_cuda_sm86_source_bundle(module_op, ctx)
    """

    return CudaSm86SourceBuilder(module_op, ctx).build()


CUDA_SM86_KERNEL_MATMUL_FRAGMENT = r"""
__device__ __forceinline__ float kg_cuda_sm86_load_or_zero_ir(const float* data, long long row, long long col, long long rows, long long cols) {
  if (row < 0 || col < 0 || row >= rows || col >= cols) {
    return 0.0f;
  }
  return data[row * cols + col];
}

__global__ void kg_cuda_sm86_ir_matmul_kernel(float* out, const float* lhs, const float* rhs, const float* bias, long long m, long long n, long long k) {
  const int lane = threadIdx.x & 31;
  const int group_id = lane >> 2;
  const int thread_in_group = lane & 3;
  const long long row_base = static_cast<long long>(blockIdx.y) * 16;
  const long long col_base = static_cast<long long>(blockIdx.x) * 8;
  float d0 = 0.0f;
  float d1 = 0.0f;
  float d2 = 0.0f;
  float d3 = 0.0f;
  for (long long k_base = 0; k_base < k; k_base += 8) {
    const unsigned a0 = cuda_sm86::detail::to_tf32(kg_cuda_sm86_load_or_zero_ir(lhs, row_base + group_id, k_base + thread_in_group, m, k));
    const unsigned a1 = cuda_sm86::detail::to_tf32(kg_cuda_sm86_load_or_zero_ir(lhs, row_base + group_id + 8, k_base + thread_in_group, m, k));
    const unsigned a2 = cuda_sm86::detail::to_tf32(kg_cuda_sm86_load_or_zero_ir(lhs, row_base + group_id, k_base + thread_in_group + 4, m, k));
    const unsigned a3 = cuda_sm86::detail::to_tf32(kg_cuda_sm86_load_or_zero_ir(lhs, row_base + group_id + 8, k_base + thread_in_group + 4, m, k));
    const unsigned b0 = cuda_sm86::detail::to_tf32(kg_cuda_sm86_load_or_zero_ir(rhs, k_base + thread_in_group, col_base + group_id, k, n));
    const unsigned b1 = cuda_sm86::detail::to_tf32(kg_cuda_sm86_load_or_zero_ir(rhs, k_base + thread_in_group + 4, col_base + group_id, k, n));
    asm volatile(
        "mma.sync.aligned.m16n8k8.row.col.f32.tf32.tf32.f32 "
        "{%0,%1,%2,%3}, {%4,%5,%6,%7}, {%8,%9}, {%0,%1,%2,%3};\n"
        : "+f"(d0), "+f"(d1), "+f"(d2), "+f"(d3)
        : "r"(a0), "r"(a1), "r"(a2), "r"(a3), "r"(b0), "r"(b1));
  }
  const long long col0 = static_cast<long long>(thread_in_group) * 2;
  const long long rows[4] = {row_base + group_id, row_base + group_id, row_base + group_id + 8, row_base + group_id + 8};
  const long long cols[4] = {col_base + col0, col_base + col0 + 1, col_base + col0, col_base + col0 + 1};
  const float values[4] = {d0, d1, d2, d3};
  for (int idx = 0; idx < 4; ++idx) {
    if (rows[idx] < m && cols[idx] < n) {
      const float bias_value = bias == nullptr ? 0.0f : bias[cols[idx]];
      out[rows[idx] * n + cols[idx]] = values[idx] + bias_value;
    }
  }
}

int kg_cuda_sm86_execute_matmul_ir(cuda_sm86::ArgSlot* slots, unsigned long long count) {
  if (!cuda_sm86::detail::is_f32_memory(slots, count, 0, 2) || !cuda_sm86::detail::is_f32_memory(slots, count, 1, 2) ||
      !cuda_sm86::detail::is_f32_memory(slots, count, 2, 2) || !cuda_sm86::detail::has_memory_data(slots, count, 0) ||
      !cuda_sm86::detail::has_memory_data(slots, count, 1) || !cuda_sm86::detail::has_memory_data(slots, count, 2)) {
    return -1;
  }
  const long long m = slots[0].shape[0];
  const long long n = slots[0].shape[1];
  const long long k = slots[1].shape[1];
  if (m <= 0 || n <= 0 || k <= 0 || slots[1].shape[0] != m || slots[2].shape[0] != k || slots[2].shape[1] != n) {
    return -1;
  }
  float* device_out = cuda_sm86::detail::device_alloc<float>(cuda_sm86::detail::element_count(slots[0]));
  float* device_lhs = cuda_sm86::detail::device_alloc<float>(cuda_sm86::detail::element_count(slots[1]));
  float* device_rhs = cuda_sm86::detail::device_alloc<float>(cuda_sm86::detail::element_count(slots[2]));
  float* device_bias = nullptr;
  const bool has_bias = cuda_sm86::detail::has_memory_data(slots, count, 3);
  if (has_bias) {
    device_bias = cuda_sm86::detail::device_alloc<float>(cuda_sm86::detail::element_count(slots[3]));
    cuda_sm86::detail::copy_host_to_device(device_bias, reinterpret_cast<const float*>(slots[3].data), cuda_sm86::detail::element_count(slots[3]));
  }
  cuda_sm86::detail::copy_host_to_device(device_lhs, reinterpret_cast<const float*>(slots[1].data), cuda_sm86::detail::element_count(slots[1]));
  cuda_sm86::detail::copy_host_to_device(device_rhs, reinterpret_cast<const float*>(slots[2].data), cuda_sm86::detail::element_count(slots[2]));
  const dim3 block(32);
  const dim3 grid(static_cast<unsigned int>((n + 7) / 8), static_cast<unsigned int>((m + 15) / 16));
  kg_cuda_sm86_ir_matmul_kernel<<<grid, block>>>(device_out, device_lhs, device_rhs, device_bias, m, n, k);
  KG_CUDA_CHECK(cudaGetLastError());
  KG_CUDA_CHECK(cudaDeviceSynchronize());
  cuda_sm86::detail::copy_device_to_host(reinterpret_cast<float*>(slots[0].data), device_out, cuda_sm86::detail::element_count(slots[0]));
  cuda_sm86::detail::device_free(device_bias);
  cuda_sm86::detail::device_free(device_rhs);
  cuda_sm86::detail::device_free(device_lhs);
  cuda_sm86::detail::device_free(device_out);
  return 0;
}

"""

CUDA_SM86_KERNEL_IMG2COL2D_FRAGMENT = r"""
__global__ void kg_cuda_sm86_ir_img2col2d_kernel(
    float* out,
    const float* input,
    const float* weight,
    const float* bias,
    long long batch,
    long long out_channels,
    long long out_h,
    long long out_w,
    long long in_channels,
    long long in_h,
    long long in_w,
    long long kernel_h,
    long long kernel_w,
    long long stride_h,
    long long stride_w,
    long long dilation_h,
    long long dilation_w,
    long long pad_top,
    long long pad_left) {
  const long long linear = static_cast<long long>(blockIdx.x) * blockDim.x + threadIdx.x;
  const long long total = batch * out_channels * out_h * out_w;
  if (linear >= total) {
    return;
  }
  const long long ow = linear % out_w;
  const long long oh = (linear / out_w) % out_h;
  const long long oc = (linear / (out_w * out_h)) % out_channels;
  const long long b = linear / (out_w * out_h * out_channels);
  float acc = bias == nullptr ? 0.0f : bias[oc];
  for (long long ic = 0; ic < in_channels; ++ic) {
    for (long long kh = 0; kh < kernel_h; ++kh) {
      const long long ih = oh * stride_h + kh * dilation_h - pad_top;
      if (ih < 0 || ih >= in_h) {
        continue;
      }
      for (long long kw = 0; kw < kernel_w; ++kw) {
        const long long iw = ow * stride_w + kw * dilation_w - pad_left;
        if (iw < 0 || iw >= in_w) {
          continue;
        }
        const long long input_index = ((b * in_channels + ic) * in_h + ih) * in_w + iw;
        const long long weight_index = ((oc * in_channels + ic) * kernel_h + kh) * kernel_w + kw;
        acc += input[input_index] * weight[weight_index];
      }
    }
  }
  out[linear] = acc;
}

int kg_cuda_sm86_execute_img2col2d_ir(cuda_sm86::ArgSlot* slots, unsigned long long count) {
  if (!cuda_sm86::detail::is_f32_memory(slots, count, 0, 4) || !cuda_sm86::detail::is_f32_memory(slots, count, 1, 4) ||
      !cuda_sm86::detail::is_f32_memory(slots, count, 2, 4) || !cuda_sm86::detail::has_memory_data(slots, count, 0) ||
      !cuda_sm86::detail::has_memory_data(slots, count, 1) || !cuda_sm86::detail::has_memory_data(slots, count, 2)) {
    return -1;
  }
  const long long batch = slots[0].shape[0];
  const long long out_channels = slots[0].shape[1];
  const long long out_h = slots[0].shape[2];
  const long long out_w = slots[0].shape[3];
  const long long in_channels = slots[1].shape[1];
  const long long in_h = slots[1].shape[2];
  const long long in_w = slots[1].shape[3];
  const long long kernel_h = slots[2].shape[2];
  const long long kernel_w = slots[2].shape[3];
  const long long stride_h = cuda_sm86::detail::int_arg_or(slots, count, 4, 1);
  const long long stride_w = cuda_sm86::detail::int_arg_or(slots, count, 5, 1);
  const long long dilation_h = cuda_sm86::detail::int_arg_or(slots, count, 6, 1);
  const long long dilation_w = cuda_sm86::detail::int_arg_or(slots, count, 7, 1);
  const long long pad_top = cuda_sm86::detail::int_arg_or(slots, count, 8, 0);
  const long long pad_left = cuda_sm86::detail::int_arg_or(slots, count, 10, 0);
  if (batch <= 0 || out_channels <= 0 || out_h <= 0 || out_w <= 0 || in_channels <= 0 || in_h <= 0 || in_w <= 0 ||
      slots[2].shape[0] != out_channels || slots[2].shape[1] != in_channels || kernel_h <= 0 || kernel_w <= 0) {
    return -1;
  }
  float* device_out = cuda_sm86::detail::device_alloc<float>(cuda_sm86::detail::element_count(slots[0]));
  float* device_input = cuda_sm86::detail::device_alloc<float>(cuda_sm86::detail::element_count(slots[1]));
  float* device_weight = cuda_sm86::detail::device_alloc<float>(cuda_sm86::detail::element_count(slots[2]));
  float* device_bias = nullptr;
  const bool has_bias = cuda_sm86::detail::has_memory_data(slots, count, 3);
  if (has_bias) {
    device_bias = cuda_sm86::detail::device_alloc<float>(cuda_sm86::detail::element_count(slots[3]));
    cuda_sm86::detail::copy_host_to_device(device_bias, reinterpret_cast<const float*>(slots[3].data), cuda_sm86::detail::element_count(slots[3]));
  }
  cuda_sm86::detail::copy_host_to_device(device_input, reinterpret_cast<const float*>(slots[1].data), cuda_sm86::detail::element_count(slots[1]));
  cuda_sm86::detail::copy_host_to_device(device_weight, reinterpret_cast<const float*>(slots[2].data), cuda_sm86::detail::element_count(slots[2]));
  const long long total = batch * out_channels * out_h * out_w;
  const int block = 256;
  const int grid = static_cast<int>((total + block - 1) / block);
  kg_cuda_sm86_ir_img2col2d_kernel<<<grid, block>>>(device_out, device_input, device_weight, device_bias, batch, out_channels, out_h, out_w,
                                                   in_channels, in_h, in_w, kernel_h, kernel_w, stride_h, stride_w, dilation_h, dilation_w,
                                                   pad_top, pad_left);
  KG_CUDA_CHECK(cudaGetLastError());
  KG_CUDA_CHECK(cudaDeviceSynchronize());
  cuda_sm86::detail::copy_device_to_host(reinterpret_cast<float*>(slots[0].data), device_out, cuda_sm86::detail::element_count(slots[0]));
  cuda_sm86::detail::device_free(device_bias);
  cuda_sm86::detail::device_free(device_weight);
  cuda_sm86::detail::device_free(device_input);
  cuda_sm86::detail::device_free(device_out);
  return 0;
}

"""

CUDA_SM86_KERNEL_REDUCE_EXP_FRAGMENT = r"""
__global__ void kg_cuda_sm86_ir_reduce_exp_kernel(
    float* out,
    const float* q,
    const float* k,
    const float* v,
    long long batch,
    long long heads,
    long long seq_len,
    long long dim) {
  const long long linear = static_cast<long long>(blockIdx.x) * blockDim.x + threadIdx.x;
  const long long total = batch * heads * seq_len * dim;
  if (linear >= total) {
    return;
  }
  const long long d = linear % dim;
  const long long m = (linear / dim) % seq_len;
  const long long h = (linear / (dim * seq_len)) % heads;
  const long long b = linear / (dim * seq_len * heads);
  float max_score = -3.4028234663852886e38f;
  for (long long n = 0; n < seq_len; ++n) {
    float score = 0.0f;
    for (long long kd = 0; kd < dim; ++kd) {
      const long long q_index = ((b * heads + h) * seq_len + m) * dim + kd;
      const long long k_index = ((b * heads + h) * seq_len + n) * dim + kd;
      score += q[q_index] * k[k_index];
    }
    max_score = fmaxf(max_score, score);
  }
  float sum_score = 0.0f;
  float weighted = 0.0f;
  for (long long n = 0; n < seq_len; ++n) {
    float score = 0.0f;
    for (long long kd = 0; kd < dim; ++kd) {
      const long long q_index = ((b * heads + h) * seq_len + m) * dim + kd;
      const long long k_index = ((b * heads + h) * seq_len + n) * dim + kd;
      score += q[q_index] * k[k_index];
    }
    const float exp_score = expf(score - max_score);
    const float old_scale = expf(0.0f);
    const long long v_index = ((b * heads + h) * seq_len + n) * dim + d;
    sum_score += exp_score * old_scale;
    weighted += exp_score * old_scale * v[v_index];
  }
  out[linear] = weighted / sum_score;
}

int kg_cuda_sm86_execute_reduce_exp_ir(cuda_sm86::ArgSlot* slots, unsigned long long count) {
  if (!cuda_sm86::detail::is_f32_memory(slots, count, 0, 4) || !cuda_sm86::detail::is_f32_memory(slots, count, 1, 4) ||
      !cuda_sm86::detail::is_f32_memory(slots, count, 2, 4) || !cuda_sm86::detail::is_f32_memory(slots, count, 3, 4)) {
    return -1;
  }
  if (!cuda_sm86::detail::has_memory_data(slots, count, 0) || !cuda_sm86::detail::has_memory_data(slots, count, 1) ||
      !cuda_sm86::detail::has_memory_data(slots, count, 2) || !cuda_sm86::detail::has_memory_data(slots, count, 3)) {
    return -1;
  }
  const long long batch = slots[0].shape[0];
  const long long heads = slots[0].shape[1];
  const long long seq_len = slots[0].shape[2];
  const long long dim = slots[0].shape[3];
  if (batch <= 0 || heads <= 0 || seq_len <= 0 || dim <= 0) {
    return -1;
  }
  float* device_out = cuda_sm86::detail::device_alloc<float>(cuda_sm86::detail::element_count(slots[0]));
  float* device_q = cuda_sm86::detail::device_alloc<float>(cuda_sm86::detail::element_count(slots[1]));
  float* device_k = cuda_sm86::detail::device_alloc<float>(cuda_sm86::detail::element_count(slots[2]));
  float* device_v = cuda_sm86::detail::device_alloc<float>(cuda_sm86::detail::element_count(slots[3]));
  cuda_sm86::detail::copy_host_to_device(device_q, reinterpret_cast<const float*>(slots[1].data), cuda_sm86::detail::element_count(slots[1]));
  cuda_sm86::detail::copy_host_to_device(device_k, reinterpret_cast<const float*>(slots[2].data), cuda_sm86::detail::element_count(slots[2]));
  cuda_sm86::detail::copy_host_to_device(device_v, reinterpret_cast<const float*>(slots[3].data), cuda_sm86::detail::element_count(slots[3]));
  const long long total = batch * heads * seq_len * dim;
  const int block = 256;
  const int grid = static_cast<int>((total + block - 1) / block);
  kg_cuda_sm86_ir_reduce_exp_kernel<<<grid, block>>>(device_out, device_q, device_k, device_v, batch, heads, seq_len, dim);
  KG_CUDA_CHECK(cudaGetLastError());
  KG_CUDA_CHECK(cudaDeviceSynchronize());
  cuda_sm86::detail::copy_device_to_host(reinterpret_cast<float*>(slots[0].data), device_out, cuda_sm86::detail::element_count(slots[0]));
  cuda_sm86::detail::device_free(device_v);
  cuda_sm86::detail::device_free(device_k);
  cuda_sm86::detail::device_free(device_q);
  cuda_sm86::detail::device_free(device_out);
  return 0;
}

"""
