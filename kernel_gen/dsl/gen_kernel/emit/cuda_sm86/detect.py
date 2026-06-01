"""CUDA SM86 lowered IR family detection.

功能说明:
- 从真实 lowered IR 的每个 `kernel.*` op emit 结果和函数 memory rank pattern 识别 CUDA SM86 kernel family。
- 对 unknown / unsupported / name-only module 保持稳定失败，不使用 entry name 或 printed IR token。

API 列表:
- class CudaSm86KernelFamily(str, Enum)
- class CudaSm86ModuleSummary(family: CudaSm86KernelFamily, matmul_count: int, img2col_count: int, exp_count: int, reduce_count: int, binary_count: int, launch_count: int, memory_rank_patterns: frozenset[tuple[int, ...]])
- `detect_cuda_sm86_kernel_family(module_op: ModuleOp, ctx: EmitCContext) -> CudaSm86KernelFamily`
- `summarize_cuda_sm86_module(module_op: ModuleOp, ctx: EmitCContext) -> CudaSm86ModuleSummary`

使用示例:
- summary = summarize_cuda_sm86_module(module_op, ctx)

关联文件:
- spec: spec/dsl/gen_kernel/emit/cuda_sm86.md
- 功能实现: kernel_gen/dsl/gen_kernel/emit/cuda_sm86/module.py
- test: test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from xdsl.dialects import func
from xdsl.dialects.builtin import ModuleOp

from kernel_gen.dsl.gen_kernel.emit_context import EmitCContext

from .constants import (
    CUDA_SM86_KERNEL_OP_BINARY_ELEWISE,
    CUDA_SM86_KERNEL_OP_EXP,
    CUDA_SM86_KERNEL_OP_IMG2COL2D,
    CUDA_SM86_KERNEL_OP_MATMUL,
    CUDA_SM86_KERNEL_OP_REDUCE,
)


class CudaSm86KernelFamily(str, Enum):
    """CUDA SM86 generated source family.

    功能说明:
    - 枚举当前 CUDA SM86 backend 支持的三类 generated source family。
    - enum value 直接写入 generated source marker，保持既有 source 合同。

    使用示例:
    - family = CudaSm86KernelFamily.MATMUL
    """

    MATMUL = "matmul"
    CONV2D = "conv2d"
    FLASH_ATTENTION = "flash_attention"


@dataclass(frozen=True)
class CudaSm86ModuleSummary:
    """CUDA SM86 lowered IR 摘要。

    功能说明:
    - 记录 family 判定和 generated source header 需要的 lowered op 计数。
    - 只作为 `cuda_sm86` package 内部文件级 API 使用，不进入包外公开 API。

    使用示例:
    - selected = summary.family.value
    """

    family: CudaSm86KernelFamily
    matmul_count: int
    img2col_count: int
    exp_count: int
    reduce_count: int
    binary_count: int
    launch_count: int
    memory_rank_patterns: frozenset[tuple[int, ...]]


def detect_cuda_sm86_kernel_family(module_op: ModuleOp, ctx: EmitCContext) -> CudaSm86KernelFamily:
    """识别 CUDA SM86 kernel family。

    功能说明:
    - 通过 `summarize_cuda_sm86_module(...)` 复用同一 IR-only 判定规则。
    - unknown / unsupported / name-only 输入沿用 `ctx.emit_error(...)` 稳定失败。

    使用示例:
    - family = detect_cuda_sm86_kernel_family(module_op, ctx)
    """

    summary = summarize_cuda_sm86_module(module_op, ctx)
    return summary.family


def summarize_cuda_sm86_module(module_op: ModuleOp, ctx: EmitCContext) -> CudaSm86ModuleSummary:
    """汇总 lowered IR 并判定 CUDA SM86 source family。

    功能说明:
    - 只遍历真实 kernel op 并调用对应 op emit，不读取函数名、注释或 printed IR 字符串。
    - 发现不支持的 `kernel.*` op family 或无法唯一选择 family 时抛出稳定 `cuda_sm86` emit error。

    使用示例:
    - summary = summarize_cuda_sm86_module(module_op, EmitCContext())
    """

    supported_kernel_ops = {
        CUDA_SM86_KERNEL_OP_BINARY_ELEWISE,
        CUDA_SM86_KERNEL_OP_EXP,
        CUDA_SM86_KERNEL_OP_IMG2COL2D,
        CUDA_SM86_KERNEL_OP_MATMUL,
        CUDA_SM86_KERNEL_OP_REDUCE,
    }
    emitted_kernel_ops: list[str] = []
    unsupported_kernel_ops: set[str] = set()
    for op in module_op.walk():
        op_name = op.name
        if not op_name.startswith("kernel."):
            continue
        if op_name not in supported_kernel_ops:
            unsupported_kernel_ops.add(op_name)
            continue
        emitted_token = ctx.dispatch_op(op)
        if emitted_token is None:
            raise ctx.emit_error("cuda_sm86", f"unsupported kernel op family: {op_name}")
        emitted_kernel_ops.append(emitted_token)
    if unsupported_kernel_ops:
        unsupported_text = ", ".join(sorted(unsupported_kernel_ops))
        raise ctx.emit_error("cuda_sm86", f"unsupported kernel op family: {unsupported_text}")
    unexpected_tokens = sorted(set(emitted_kernel_ops) - supported_kernel_ops)
    if unexpected_tokens:
        unexpected_text = ", ".join(unexpected_tokens)
        raise ctx.emit_error("cuda_sm86", f"unsupported kernel op emit: {unexpected_text}")

    op_names = [op.name for op in module_op.walk()]
    matmul_count = emitted_kernel_ops.count(CUDA_SM86_KERNEL_OP_MATMUL)
    img2col_count = emitted_kernel_ops.count(CUDA_SM86_KERNEL_OP_IMG2COL2D)
    exp_count = emitted_kernel_ops.count(CUDA_SM86_KERNEL_OP_EXP)
    reduce_count = emitted_kernel_ops.count(CUDA_SM86_KERNEL_OP_REDUCE)
    binary_count = emitted_kernel_ops.count(CUDA_SM86_KERNEL_OP_BINARY_ELEWISE)
    launch_count = sum(1 for op_name in op_names if op_name == "arch.launch")
    memory_rank_patterns: set[tuple[int, ...]] = set()
    for op in module_op.ops:
        if not isinstance(op, func.FuncOp):
            continue
        input_ranks: list[int] = []
        for input_type in op.function_type.inputs:
            input_text = str(input_type)
            memory_start = input_text.find("!nn.memory<[")
            if memory_start < 0:
                continue
            shape_start = memory_start + len("!nn.memory<[")
            shape_end = input_text.find("], [", shape_start)
            if shape_end < 0:
                continue
            shape_text = input_text[shape_start:shape_end].strip()
            input_ranks.append(0 if not shape_text else shape_text.count("#symbol.expr<"))
        if input_ranks:
            memory_rank_patterns.add(tuple(input_ranks))

    has_kernel_launch = matmul_count > 0 and launch_count > 0
    candidate_families: list[CudaSm86KernelFamily] = []
    if has_kernel_launch and exp_count > 0 and reduce_count > 0 and (4, 4, 4, 4) in memory_rank_patterns:
        candidate_families.append(CudaSm86KernelFamily.FLASH_ATTENTION)
    if has_kernel_launch and exp_count == 0 and img2col_count > 0 and binary_count >= 4 and (4, 4, 4, 1) in memory_rank_patterns:
        candidate_families.append(CudaSm86KernelFamily.CONV2D)
    if has_kernel_launch and exp_count == 0 and img2col_count == 0 and reduce_count == 0 and (2, 2, 2, 1) in memory_rank_patterns:
        candidate_families.append(CudaSm86KernelFamily.MATMUL)
    if len(candidate_families) != 1:
        raise ctx.emit_error("cuda_sm86", "unsupported kernel family")

    family = candidate_families[0]
    return CudaSm86ModuleSummary(
        family=family,
        matmul_count=matmul_count,
        img2col_count=img2col_count,
        exp_count=exp_count,
        reduce_count=reduce_count,
        binary_count=binary_count,
        launch_count=launch_count,
        memory_rank_patterns=frozenset(memory_rank_patterns),
    )
