"""nn -> kernel lowering pass.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 将 nn dialect 的逐元素 op lower 为 kernel dialect op。
- 当结果无法复用已有输出时，为结果插入 dma.alloc。

使用示例:
- from kernel_gen.pass.lowing.nn_to_kernel import LowerNnToKernelPass
- module = LowerNnToKernelPass().run(module)

关联文件:
- spec: spec/pass/lowing/nn_to_kernel.md
- test: test/pass/test_lowing_nn_to_kernel.py
- 功能实现: kernel_gen/pass/lowing/nn_to_kernel.py
"""

from __future__ import annotations

from collections.abc import Iterable

from xdsl.dialects import func
from xdsl.ir import Block, Operation, Region, SSAValue
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.dma import DmaAllocOp
from kernel_gen.dialect.kernel import (
    KernelAddOp,
    KernelCastOp,
    KernelDivOp,
    KernelEqOp,
    KernelGtOp,
    KernelLtOp,
    KernelMulOp,
    KernelSelectOp,
    KernelSubOp,
)
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from ..pass_manager import Pass


class LowerNnToKernelError(ValueError):
    """nn -> kernel lowering 过程的显式错误。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 用于在 lowering 阶段中断执行并返回明确错误信息。

    使用示例:
    - raise LowerNnToKernelError("Unsupported nn op")

    关联文件:
    - spec: spec/pass/lowing/nn_to_kernel.md
    - test: test/pass/test_lowing_nn_to_kernel.py
    - 功能实现: kernel_gen/pass/lowing/nn_to_kernel.py
    """


_SUPPORTED_BINARY = {
    "nn.add": KernelAddOp,
    "nn.sub": KernelSubOp,
    "nn.mul": KernelMulOp,
    "nn.div": KernelDivOp,
    "nn.eq": KernelEqOp,
    "nn.lt": KernelLtOp,
    "nn.gt": KernelGtOp,
}


def _ensure_space_attr(op: Operation) -> NnMemorySpaceAttr:
    """获取并校验 nn op 的 space attribute。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 确认 op.attributes["space"] 为 NnMemorySpaceAttr。

    使用示例:
    - space = _ensure_space_attr(op)

    关联文件:
    - spec: spec/pass/lowing/nn_to_kernel.md
    - test: test/pass/test_lowing_nn_to_kernel.py
    - 功能实现: kernel_gen/pass/lowing/nn_to_kernel.py
    """

    space = op.attributes.get("space")
    if not isinstance(space, NnMemorySpaceAttr):
        raise LowerNnToKernelError("nn op must provide nn.space attribute")
    return space


def _ensure_single_result(op: Operation) -> NnMemoryType:
    """校验 nn op 仅有单个结果且类型为 nn.memory。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 要求结果数量为 1。
    - 要求结果类型为 NnMemoryType。

    使用示例:
    - result_type = _ensure_single_result(op)

    关联文件:
    - spec: spec/pass/lowing/nn_to_kernel.md
    - test: test/pass/test_lowing_nn_to_kernel.py
    - 功能实现: kernel_gen/pass/lowing/nn_to_kernel.py
    """

    if len(op.results) != 1:
        raise LowerNnToKernelError("nn op must have exactly one result")
    result_type = op.results[0].type
    if not isinstance(result_type, NnMemoryType):
        raise LowerNnToKernelError("nn op result must be nn.memory")
    return result_type


def _ensure_operand_count(op: Operation, expected: int) -> None:
    """校验 nn op 的 operand 数量。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - operand 数量不匹配时直接抛错。

    使用示例:
    - _ensure_operand_count(op, 2)

    关联文件:
    - spec: spec/pass/lowing/nn_to_kernel.md
    - test: test/pass/test_lowing_nn_to_kernel.py
    - 功能实现: kernel_gen/pass/lowing/nn_to_kernel.py
    """

    if len(op.operands) != expected:
        raise LowerNnToKernelError(
            f"nn op {op.name} expects {expected} operands, got {len(op.operands)}"
        )


def _build_kernel_op(
    op: Operation,
    out_value: SSAValue,
    space: NnMemorySpaceAttr,
) -> Operation:
    """构造 kernel dialect op。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 根据 nn op 名称映射 kernel op。
    - 处理二元/选择/类型转换三类 op。

    使用示例:
    - kernel_op = _build_kernel_op(op, alloc.results[0], space)

    关联文件:
    - spec: spec/pass/lowing/nn_to_kernel.md
    - test: test/pass/test_lowing_nn_to_kernel.py
    - 功能实现: kernel_gen/pass/lowing/nn_to_kernel.py
    """

    if op.name in _SUPPORTED_BINARY:
        _ensure_operand_count(op, 2)
        kernel_cls = _SUPPORTED_BINARY[op.name]
        return kernel_cls(op.operands[0], op.operands[1], out_value, space)

    if op.name == "nn.select":
        _ensure_operand_count(op, 3)
        return KernelSelectOp(op.operands[0], op.operands[1], op.operands[2], out_value, space)

    if op.name == "nn.cast":
        _ensure_operand_count(op, 1)
        return KernelCastOp(op.operands[0], out_value, space)

    raise LowerNnToKernelError(f"Unsupported nn op: {op.name}")


def _lower_nn_op(op: Operation, block: Block) -> None:
    """将单个 nn op lower 为 kernel op。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 为结果插入 dma.alloc。
    - 用 kernel op 替换 nn op，并替换所有使用者。

    使用示例:
    - _lower_nn_op(op, block)

    关联文件:
    - spec: spec/pass/lowing/nn_to_kernel.md
    - test: test/pass/test_lowing_nn_to_kernel.py
    - 功能实现: kernel_gen/pass/lowing/nn_to_kernel.py
    """

    result_type = _ensure_single_result(op)
    space = _ensure_space_attr(op)

    alloc = DmaAllocOp([], result_type)
    kernel_op = _build_kernel_op(op, alloc.result, space)

    try:
        kernel_op.verify()
    except VerifyException as exc:
        raise LowerNnToKernelError(str(exc)) from exc

    block.insert_ops_before([alloc, kernel_op], op)
    op.results[0].replace_by(alloc.result)
    block.erase_op(op)


def _lower_block(block: Block) -> None:
    """对单个 block 执行 nn -> kernel lowering。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 按顺序 lower block 内出现的 nn op。

    使用示例:
    - _lower_block(block)

    关联文件:
    - spec: spec/pass/lowing/nn_to_kernel.md
    - test: test/pass/test_lowing_nn_to_kernel.py
    - 功能实现: kernel_gen/pass/lowing/nn_to_kernel.py
    """

    ops = list(block.ops)
    for op in ops:
        for region in op.regions:
            _lower_region(region)
        if op.name.startswith("nn."):
            _lower_nn_op(op, block)


def _lower_region(region: Region) -> None:
    """对 region 内的所有 block 执行 lowering。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 遍历 region 的每个 block 并执行 lowering。

    使用示例:
    - _lower_region(region)

    关联文件:
    - spec: spec/pass/lowing/nn_to_kernel.md
    - test: test/pass/test_lowing_nn_to_kernel.py
    - 功能实现: kernel_gen/pass/lowing/nn_to_kernel.py
    """

    for block in region.blocks:
        _lower_block(block)


def _lower_module(module: Operation) -> None:
    """在 module 中执行 nn -> kernel lowering。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅对 func.func 进行 lowering。

    使用示例:
    - _lower_module(module)

    关联文件:
    - spec: spec/pass/lowing/nn_to_kernel.md
    - test: test/pass/test_lowing_nn_to_kernel.py
    - 功能实现: kernel_gen/pass/lowing/nn_to_kernel.py
    """

    for op in module.ops:
        if isinstance(op, func.FuncOp):
            _lower_region(op.body)


def _iter_ops(module: Operation) -> Iterable[Operation]:
    """遍历 module 内全部 op。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 递归遍历 module 内所有 op。

    使用示例:
    - for op in _iter_ops(module):
          ...

    关联文件:
    - spec: spec/pass/lowing/nn_to_kernel.md
    - test: test/pass/test_lowing_nn_to_kernel.py
    - 功能实现: kernel_gen/pass/lowing/nn_to_kernel.py
    """

    stack: list[Operation] = list(module.ops)
    while stack:
        op = stack.pop()
        yield op
        for region in op.regions:
            for block in region.blocks:
                stack.extend(reversed(list(block.ops)))


def _ensure_no_nn_ops(module: Operation) -> None:
    """确保 module 内不残留 nn op。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 遍历 module，若发现 nn op 则抛错。

    使用示例:
    - _ensure_no_nn_ops(module)

    关联文件:
    - spec: spec/pass/lowing/nn_to_kernel.md
    - test: test/pass/test_lowing_nn_to_kernel.py
    - 功能实现: kernel_gen/pass/lowing/nn_to_kernel.py
    """

    for op in _iter_ops(module):
        if op.name.startswith("nn."):
            raise LowerNnToKernelError(f"nn op remains after lowering: {op.name}")


class LowerNnToKernelPass(Pass):
    """nn -> kernel lowering pass。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 执行 nn dialect 到 kernel dialect 的 lowering。

    使用示例:
    - module = LowerNnToKernelPass().run(module)

    关联文件:
    - spec: spec/pass/lowing/nn_to_kernel.md
    - test: test/pass/test_lowing_nn_to_kernel.py
    - 功能实现: kernel_gen/pass/lowing/nn_to_kernel.py
    """

    name = "lower-nn-to-kernel"

    def run(self, module: Operation):
        """执行 pass。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 将 module 内 nn op lower 为 kernel op。

        使用示例:
        - LowerNnToKernelPass().run(module)

        关联文件:
        - spec: spec/pass/lowing/nn_to_kernel.md
        - test: test/pass/test_lowing_nn_to_kernel.py
        - 功能实现: kernel_gen/pass/lowing/nn_to_kernel.py
        """

        _lower_module(module)
        _ensure_no_nn_ops(module)
        return module


__all__ = ["LowerNnToKernelPass", "LowerNnToKernelError"]
