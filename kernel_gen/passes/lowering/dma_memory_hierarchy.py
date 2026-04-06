"""dma-memory-hierarchy lowering pass.

创建者: 朽木露琪亚
最后一次更改: jcc你莫辜负

功能说明:
- 实现 `lower-dma-memory-hierarchy` pass，将仍停留在 `GM` 的 `kernel.*` 计算显式改写为
  `GM -> SM -> LM` 的读路径与 `LM -> SM -> GM` 的写路径。
- 本 pass 新增的 hierarchy 搬运统一使用 `dma.slice / dma.deslice` 表达，不引入
  `dma.copy/load/store` 作为新增主语义。
- 强制处理后的 `kernel.*` operand/out 仅使用 `LM` space，并同步刷新 op 的 `space` 属性为 `local`。

使用示例:
- from kernel_gen.passes.lowering.dma_memory_hierarchy import LowerDmaMemoryHierarchyPass
- module = LowerDmaMemoryHierarchyPass().run(module)

关联文件:
- spec: spec/pass/lowering/dma_memory_hierarchy.md
- test: test/pass/test_dma_memory_hierarchy.py
- 功能实现: kernel_gen/passes/lowering/dma_memory_hierarchy.py
"""

from __future__ import annotations

from xdsl.dialects import arith
from xdsl.dialects.builtin import (
    IntAttr,
    IntegerAttr,
    ModuleOp,
    UnrealizedConversionCastOp,
    i32,
)
from xdsl.ir import Block, Operation, SSAValue

from kernel_gen.dialect.dma import DmaAllocOp, DmaDesliceOp, DmaSliceOp, DmaViewOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolGetDimOp, SymbolValueType
from kernel_gen.passes.pass_manager import Pass
from kernel_gen.target import registry as target_registry


class LowerDmaMemoryHierarchyError(ValueError):
    """dma-memory-hierarchy lowering 过程的显式错误。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 用于在 pass 执行过程中中断并返回明确错误信息。

    使用示例:
    - raise LowerDmaMemoryHierarchyError("target does not support SM/LM")

    关联文件:
    - spec: spec/pass/lowering/dma_memory_hierarchy.md
    - test: test/pass/test_dma_memory_hierarchy.py
    - 功能实现: kernel_gen/passes/lowering/dma_memory_hierarchy.py
    """


def _require_sm_lm_support() -> None:
    """校验当前 target 支持 SM/LM，否则显式失败。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 读取当前 target 的 `sm_memory_size` 与 `lm_memory_size`。
    - 任一为 `None/<=0` 则视作不支持，抛出包含 `SM/LM` 关键字的错误。

    使用示例:
    - _require_sm_lm_support()

    关联文件:
    - spec: spec/pass/lowering/dma_memory_hierarchy.md
    - test: test/pass/test_dma_memory_hierarchy.py
    - 功能实现: kernel_gen/passes/lowering/dma_memory_hierarchy.py
    """

    sm_size = target_registry.get_current_target_hardware("sm_memory_size")
    lm_size = target_registry.get_current_target_hardware("lm_memory_size")
    if sm_size is None or lm_size is None:
        raise LowerDmaMemoryHierarchyError(
            "target must be selected and provide SM/LM hardware size for lower-dma-memory-hierarchy"
        )
    if sm_size <= 0 or lm_size <= 0:
        raise LowerDmaMemoryHierarchyError(
            "target does not support SM/LM for lower-dma-memory-hierarchy"
        )


def _memory_space(value_type: NnMemoryType) -> str:
    """读取 nn.memory 的 space 名称。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 返回 `global/shared/local/tsm/tlm` 中的字符串。

    使用示例:
    - space = _memory_space(SSAValue.get(op.operands[0]).type)

    关联文件:
    - spec: spec/pass/lowering/dma_memory_hierarchy.md
    - test: test/pass/test_dma_memory_hierarchy.py
    - 功能实现: kernel_gen/passes/lowering/dma_memory_hierarchy.py
    """

    return value_type.space.space.data


def _with_space(value_type: NnMemoryType, space: str) -> NnMemoryType:
    """构造同 shape/stride/element_type、不同 space 的 nn.memory type。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 用于为 staging buffer 生成 `SM/LM` 空间的类型。

    使用示例:
    - lm_type = _with_space(gm_type, "local")

    关联文件:
    - spec: spec/pass/lowering/dma_memory_hierarchy.md
    - test: test/pass/test_dma_memory_hierarchy.py
    - 功能实现: kernel_gen/passes/lowering/dma_memory_hierarchy.py
    """

    return NnMemoryType(
        value_type.shape,
        value_type.stride,
        value_type.element_type,
        NnMemorySpaceAttr.from_name(space),
    )


def _const_symbol_int(value: int) -> tuple[arith.ConstantOp, UnrealizedConversionCastOp]:
    """构造 `!symbol.int<\"value\">` 常量的 IR op 对。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 先创建 i32 常量，再用 `builtin.unrealized_conversion_cast` 转成 `!symbol.int<\"expr\">`。
    - 返回两条 op，调用者决定插入到 block 中的位置。

    使用示例:
    - const_i32, cast = _const_symbol_int(1)
    - block.insert_ops_before([const_i32, cast], anchor_op)
    - one = cast.results[0]

    关联文件:
    - spec: spec/pass/lowering/dma_memory_hierarchy.md
    - test: test/pass/test_dma_memory_hierarchy.py
    - 功能实现: kernel_gen/passes/lowering/dma_memory_hierarchy.py
    """

    const = arith.ConstantOp(IntegerAttr(value, i32))
    result_type = SymbolValueType.from_expr(str(value))
    cast = UnrealizedConversionCastOp(operands=[const.result], result_types=[result_type])
    return const, cast


def _build_full_window_operands(
    source: SSAValue,
    *,
    rank: int,
    zero: SSAValue,
    one: SSAValue,
) -> tuple[list[Operation], list[SSAValue], list[SSAValue], list[SSAValue]]:
    """为整块窗口搬运构造 offsets/sizes/strides operand。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - offsets: 全 0
    - strides: 全 1
    - sizes: 通过 `symbol.get_dim(source, axis)` 从 source 的 shape 中读取，保证与静态 shape 对齐，
      且当 source 存在匿名动态值 `?` 时 verifier 会显式失败。

    使用示例:
    - ops, offsets, sizes, strides = _build_full_window_operands(gm, rank=2, zero=zero, one=one)

    关联文件:
    - spec: spec/pass/lowering/dma_memory_hierarchy.md
    - test: test/pass/test_dma_memory_hierarchy.py
    - 功能实现: kernel_gen/passes/lowering/dma_memory_hierarchy.py
    """

    ops: list[Operation] = []
    sizes: list[SSAValue] = []
    for axis in range(rank):
        get_dim = SymbolGetDimOp(source, IntAttr(axis))
        ops.append(get_dim)
        sizes.append(get_dim.result)
    offsets = [zero] * rank
    strides = [one] * rank
    return ops, offsets, sizes, strides


def _resolve_window_operands(
    value: SSAValue,
    *,
    rank: int,
    zero: SSAValue,
    one: SSAValue,
) -> tuple[list[Operation], SSAValue, list[SSAValue], list[SSAValue], list[SSAValue]]:
    """解析 GM 侧窗口参数与基准 source/target。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 若 operand 来自 `dma.view`，保留其 offsets/shape 作为 window 参数，并将 base 设为 view.source。
    - `dma.slice/dma.deslice` 当前仅支持单位 stride；因此即使 `dma.view` 自身记录了非单位窗口 stride，hierarchy 新路径也只继承原窗口的 offsets/shape，并统一把 stride 规范化为 unit stride。
    - 非 window 情况下回退为 full window：offsets=0、sizes=shape、strides=1。

    使用示例:
    - ops, base, offsets, sizes, strides = _resolve_window_operands(gm, rank=2, zero=zero, one=one)

    关联文件:
    - spec: spec/pass/lowering/dma_memory_hierarchy.md
    - test: test/pass/test_dma_memory_hierarchy.py
    - 功能实现: kernel_gen/passes/lowering/dma_memory_hierarchy.py
    """

    owner = getattr(value, "owner", None)
    if isinstance(owner, DmaViewOp):
        offsets = list(owner.offsets)
        sizes = list(owner.shape)
        if len(offsets) != rank or len(sizes) != rank:
            raise LowerDmaMemoryHierarchyError("dma.view window rank mismatch for lower-dma-memory-hierarchy")
        return [], SSAValue.get(owner.source), offsets, sizes, [one] * rank
    ops, offsets, sizes, strides = _build_full_window_operands(
        value, rank=rank, zero=zero, one=one
    )
    return ops, value, offsets, sizes, strides


def _ensure_static_rank(memory_type: NnMemoryType, context: str) -> int:
    """确保 nn.memory 的 rank 可确定，返回 rank。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 目前 rank 由 shape 列表长度决定；这里同步触发类型校验并返回 rank。

    使用示例:
    - rank = _ensure_static_rank(mem_type, "kernel operand")

    关联文件:
    - spec: spec/pass/lowering/dma_memory_hierarchy.md
    - test: test/pass/test_dma_memory_hierarchy.py
    - 功能实现: kernel_gen/passes/lowering/dma_memory_hierarchy.py
    """

    memory_type.verify()
    rank = len(memory_type.shape.data)
    if rank <= 0:
        raise LowerDmaMemoryHierarchyError(f"{context} rank must be >= 1")
    return rank


def _is_kernel_op(op: Operation) -> bool:
    """判断 op 是否为 kernel dialect op。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 当前以 `op.name.startswith(\"kernel.\")` 判定。

    使用示例:
    - if _is_kernel_op(op): ...

    关联文件:
    - spec: spec/pass/lowering/dma_memory_hierarchy.md
    - test: test/pass/test_dma_memory_hierarchy.py
    - 功能实现: kernel_gen/passes/lowering/dma_memory_hierarchy.py
    """

    return op.name.startswith("kernel.")


def _lower_gm_operand_to_lm(
    operand: SSAValue,
    operand_type: NnMemoryType,
    *,
    block: Block,
    anchor_op: Operation,
    zero: SSAValue,
    one: SSAValue,
) -> tuple[list[Operation], SSAValue]:
    """将单个 GM operand 改写为 GM->SM->LM 并返回 LM buffer。

    创建者: 朽木露琪亚
    最后一次更改: jcc你莫辜负

    功能说明:
    - 为 operand 分配 SM/LM staging buffer，并插入两段 `dma.slice`：
      `GM -> SM`（保留 full/window offsets/sizes，strides 仍为 unit stride）与
      `SM -> LM`（zero offsets + unit strides）。
    - 返回需要插入到 `anchor_op` 之前的 ops 列表与最终 LM buffer SSA value。

    使用示例:
    - ops, lm = _lower_gm_operand_to_lm(gm, gm_type, block=block, anchor_op=kernel_op, zero=zero, one=one)
    - block.insert_ops_before(ops, kernel_op)

    关联文件:
    - spec: spec/pass/lowering/dma_memory_hierarchy.md
    - test: test/pass/test_dma_memory_hierarchy.py
    - 功能实现: kernel_gen/passes/lowering/dma_memory_hierarchy.py
    """

    rank = _ensure_static_rank(operand_type, "kernel operand")
    sm_type = _with_space(operand_type, "shared")
    lm_type = _with_space(operand_type, "local")
    window_ops, window_source, window_offsets, window_sizes, window_strides = _resolve_window_operands(
        operand, rank=rank, zero=zero, one=one
    )
    alloc_sm = DmaAllocOp(window_sizes, sm_type)
    alloc_lm = DmaAllocOp(window_sizes, lm_type)
    slice_gm_to_sm = DmaSliceOp(
        alloc_sm.result, window_source, window_offsets, window_sizes, window_strides
    )
    zero_offsets = [zero] * rank
    unit_strides = [one] * rank
    slice_sm_to_lm = DmaSliceOp(alloc_lm.result, alloc_sm.result, zero_offsets, window_sizes, unit_strides)
    ops: list[Operation] = [*window_ops, alloc_sm, alloc_lm, slice_gm_to_sm, slice_sm_to_lm]
    return ops, alloc_lm.result


def _lower_gm_out_to_lm_with_writeback(
    out: SSAValue,
    out_type: NnMemoryType,
    *,
    block: Block,
    anchor_op: Operation,
    zero: SSAValue,
    one: SSAValue,
) -> tuple[list[Operation], list[Operation], SSAValue]:
    """将 GM out operand 改写为 LM out，并构造 LM->SM->GM 写回链路。

    创建者: 朽木露琪亚
    最后一次更改: jcc你莫辜负

    功能说明:
    - 在 `anchor_op` 前插入 SM/LM alloc（out staging）。
    - 在 `anchor_op` 后插入两段 `dma.deslice`：`LM -> SM` 与 `SM -> GM`。
      第二段 deslice 的 source 使用第一段 deslice 的 result，匹配 `dma.deslice` 返回“更新后 target”的语义。
    - `LM -> SM` 使用 zero offsets + unit strides；`SM -> GM` 保留 full/window offsets/sizes，
      但回写 strides 仍统一使用 unit stride。
    - 返回：需插入到 `anchor_op` 前的 ops、需插入到 `anchor_op` 后的 ops、以及 LM out SSA value。

    使用示例:
    - pre_ops, post_ops, lm_out = _lower_gm_out_to_lm_with_writeback(gm_out, gm_type, block=block, anchor_op=kernel_op, zero=zero, one=one)
    - block.insert_ops_before(pre_ops, kernel_op)
    - block.insert_ops_after(post_ops, kernel_op)

    关联文件:
    - spec: spec/pass/lowering/dma_memory_hierarchy.md
    - test: test/pass/test_dma_memory_hierarchy.py
    - 功能实现: kernel_gen/passes/lowering/dma_memory_hierarchy.py
    """

    rank = _ensure_static_rank(out_type, "kernel out")
    sm_type = _with_space(out_type, "shared")
    lm_type = _with_space(out_type, "local")
    window_ops, window_target, window_offsets, window_sizes, window_strides = _resolve_window_operands(
        out, rank=rank, zero=zero, one=one
    )
    if not isinstance(window_target.type, NnMemoryType):
        raise LowerDmaMemoryHierarchyError("window target must be nn.memory")
    alloc_sm = DmaAllocOp(window_sizes, sm_type)
    alloc_lm = DmaAllocOp(window_sizes, lm_type)
    pre_ops: list[Operation] = [*window_ops, alloc_sm, alloc_lm]

    zero_offsets = [zero] * rank
    unit_strides = [one] * rank
    deslice_lm_to_sm = DmaDesliceOp(
        alloc_lm.result,
        alloc_sm.result,
        zero_offsets,
        window_sizes,
        unit_strides,
        sm_type,
    )
    deslice_sm_to_gm = DmaDesliceOp(
        deslice_lm_to_sm.result,
        window_target,
        window_offsets,
        window_sizes,
        window_strides,
        window_target.type,
    )
    post_ops: list[Operation] = [deslice_lm_to_sm, deslice_sm_to_gm]
    return pre_ops, post_ops, alloc_lm.result


class LowerDmaMemoryHierarchyPass(Pass):
    """将 kernel/dma IR 显式改写为 GM/SM/LM hierarchy 路径的 lowering pass。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 为 `kernel.*` operand/out 中仍在 `GM` 的 buffer 插入 staging：
      - 读路径：`GM -> SM -> LM`（`dma.slice`）
      - 写路径：`LM -> SM -> GM`（`dma.deslice`）
    - 强制 `kernel.*` 仅在 `LM` 上计算，并把 op 的 `space` 属性设置为 `#nn.space<local>`。

    使用示例:
    - module = LowerDmaMemoryHierarchyPass().run(module)

    关联文件:
    - spec: spec/pass/lowering/dma_memory_hierarchy.md
    - test: test/pass/test_dma_memory_hierarchy.py
    - 功能实现: kernel_gen/passes/lowering/dma_memory_hierarchy.py
    """

    name = "lower-dma-memory-hierarchy"

    def run(self, module: ModuleOp) -> ModuleOp:
        """执行 dma-memory-hierarchy lowering。

        创建者: 朽木露琪亚
        最后一次更改: jcc你莫辜负

        功能说明:
        - 遍历 module 内所有 `kernel.*` op，在其所在 block 内插入 `dma.alloc/slice/deslice`。
        - 遇到目标不支持 SM/LM 或输入不满足边界时显式失败。

        使用示例:
        - module = LowerDmaMemoryHierarchyPass().run(module)

        关联文件:
        - spec: spec/pass/lowering/dma_memory_hierarchy.md
        - test: test/pass/test_dma_memory_hierarchy.py
        - 功能实现: kernel_gen/passes/lowering/dma_memory_hierarchy.py
        """

        if not isinstance(module, ModuleOp):
            raise LowerDmaMemoryHierarchyError("module must be builtin.module")
        _require_sm_lm_support()
        if any(op.name.startswith("nn.") for op in module.walk()):
            raise LowerDmaMemoryHierarchyError(
                "lower-dma-memory-hierarchy input must not contain nn.* ops"
            )

        kernel_ops = [op for op in module.walk() if _is_kernel_op(op)]
        for op in kernel_ops:
            block = op.parent
            if not isinstance(block, Block):
                raise LowerDmaMemoryHierarchyError("kernel op must live in a block")
            if not op.operands:
                continue

            # kernel dialect 约定：最后一个 nn.memory operand 为 out。
            out_index = len(op.operands) - 1
            out_value = SSAValue.get(op.operands[out_index])
            out_type = out_value.type
            if not isinstance(out_type, NnMemoryType):
                raise LowerDmaMemoryHierarchyError("kernel out operand must be nn.memory")

            # 预检：只允许 GM/LM space，且仅当存在 GM 时才插入 staging op。
            gm_input_indices: list[int] = []
            for idx in range(out_index):
                operand_value = SSAValue.get(op.operands[idx])
                operand_type = operand_value.type
                if not isinstance(operand_type, NnMemoryType):
                    continue
                space = _memory_space(operand_type)
                if space == "global":
                    gm_input_indices.append(idx)
                elif space == "local":
                    continue
                else:
                    raise LowerDmaMemoryHierarchyError(
                        f"kernel operand space must be GM or LM, got {space}"
                    )

            out_space = _memory_space(out_type)
            if out_space not in {"global", "local"}:
                raise LowerDmaMemoryHierarchyError(
                    f"kernel out space must be GM or LM, got {out_space}"
                )

            needs_staging = bool(gm_input_indices) or out_space == "global"
            if not needs_staging:
                op.attributes["space"] = NnMemorySpaceAttr.from_name("local")
                continue

            zero_const, zero_cast = _const_symbol_int(0)
            one_const, one_cast = _const_symbol_int(1)
            block.insert_ops_before([zero_const, zero_cast, one_const, one_cast], op)
            zero = zero_cast.results[0]
            one = one_cast.results[0]

            # 1) 先处理读 operand：所有非 out 的 nn.memory operand 必须最终成为 LM。
            for idx in gm_input_indices:
                operand_value = SSAValue.get(op.operands[idx])
                operand_type = operand_value.type
                assert isinstance(operand_type, NnMemoryType)
                pre_ops, lowered = _lower_gm_operand_to_lm(
                    operand_value,
                    operand_type,
                    block=block,
                    anchor_op=op,
                    zero=zero,
                    one=one,
                )
                block.insert_ops_before(pre_ops, op)
                op.operands[idx] = lowered

            # 2) 处理 out：GM -> LM + 写回；LM-only 则不插入 staging。
            if out_space == "local":
                pass
            elif out_space == "global":
                pre_ops, post_ops, lowered_out = _lower_gm_out_to_lm_with_writeback(
                    out_value,
                    out_type,
                    block=block,
                    anchor_op=op,
                    zero=zero,
                    one=one,
                )
                block.insert_ops_before(pre_ops, op)
                op.operands[out_index] = lowered_out
                block.insert_ops_after(post_ops, op)
            else:
                raise LowerDmaMemoryHierarchyError(
                    f"kernel out space must be GM or LM, got {out_space}"
                )

            op.attributes["space"] = NnMemorySpaceAttr.from_name("local")

        return module


__all__ = ["LowerDmaMemoryHierarchyError", "LowerDmaMemoryHierarchyPass"]
