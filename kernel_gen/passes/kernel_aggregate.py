"""kernel aggregate pass.

功能说明:
- 提供 `kernel-aggregate` pass，把可证明的 matmul+add 临时累加形态聚合为 `kernel.matmul_fusion`。

API 列表:
- `class KernelAggregatePass(matmul_acc: bool = False, fold: bool = True)`
- `KernelAggregatePass.from_options(options: dict[str, str]) -> KernelAggregatePass`
- `KernelAggregatePass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from kernel_gen.passes.kernel_aggregate import KernelAggregatePass
- KernelAggregatePass(matmul_acc=True).apply(Context(), module)
- KernelAggregatePass.from_options({"matmul-acc": "true"})

关联文件:
- spec: spec/pass/kernel_aggregate.md
- test: test/passes/test_kernel_aggregate.py
- 功能实现: kernel_gen/passes/kernel_aggregate.py
"""

from __future__ import annotations

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp, i1
from xdsl.ir import Attribute, Block, Operation, SSAValue

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dialect.dma import DmaAllocOp, DmaFreeOp
from kernel_gen.dialect.kernel import KernelBinaryElewiseOp, KernelMatmulFusionOp, KernelMatmulOp
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolExprAttr, SymbolForOp, SymbolNeOp
from kernel_gen.passes.common import ensure_builtin_module, verify_generated_ops
from kernel_gen.passes.pass_manager import Pass


def _kernel_aggregate_error(message: str) -> KernelCodeError:
    """构造 kernel-aggregate pass 错误。

    功能说明:
    - 统一 pass 内稳定错误短语前缀，便于 spec、pytest 与 expectation 机械匹配。

    使用示例:
    - raise _kernel_aggregate_error("matmul acc iterator")
    """

    detail = message.strip()
    if not detail:
        detail = "unknown error"
    full_message = f"kernel-aggregate {detail}"
    error = KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, full_message)
    return error


def _parse_matmul_acc_option(value: str) -> bool:
    """解析 `matmul-acc` bool option。

    功能说明:
    - 接受 true/false/1/0/yes/no/on/off。
    - 非法文本使用 `kernel-aggregate options` 稳定短语失败。

    使用示例:
    - enabled = _parse_matmul_acc_option("true")
    """

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    message = "options matmul-acc expects bool"
    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"kernel-aggregate {message}")


def _ancestor_op_in_block(op: Operation, block: Block) -> Operation | None:
    """查找 `op` 在目标 block 中的直接祖先 op。

    功能说明:
    - 支持 tmp alloc/free 在外层 owner block、matmul/add 在内层 loop block 的证明场景。
    - 返回值用于比较 alloc、owner loop、free 在同一 owner block 内的顺序。

    使用示例:
    - anchor = _ancestor_op_in_block(matmul, alloc_block)
    """

    current: Operation | None = op
    while current is not None:
        parent_block = current.parent_block()
        if parent_block is block:
            return current
        current = current.parent_op()
    return None


class KernelAggregatePass(Pass):
    """聚合 matmul 累加形态的公开 pass。

    功能说明:
    - `matmul_acc=True` 时匹配同 block 相邻 `kernel.matmul(tmp,lhs,rhs)` 与
      `kernel.binary_elewise(out,out,tmp){kind="add"}`。
    - tmp alloc/free 可位于同 block 或包住目标 loop 的祖先 owner block。
    - 生成 `symbol.ne(k_iter,k_start)` 与 `kernel.matmul_fusion(out,lhs,rhs,acc)`，
      并删除原 tmp alloc/free、matmul 与 add。
    - 无法证明 tmp 生命周期、extra use 或 K/reduce iterator 时按计划 no-op 或 fail-fast。

    使用示例:
    - KernelAggregatePass(matmul_acc=True).apply(Context(), module)
    """

    name = "kernel-aggregate"

    def __init__(self, matmul_acc: bool = False, fold: bool = True) -> None:
        """初始化 kernel-aggregate pass。

        功能说明:
        - 记录是否启用 matmul 累加聚合。
        - `fold` 仅承接通用 PassManager 清理开关，不新增 pass 专属 option。

        使用示例:
        - KernelAggregatePass(matmul_acc=True)
        """

        super().__init__(fold=fold)
        self.matmul_acc = bool(matmul_acc)

    @classmethod
    def from_options(cls, options: dict[str, str]) -> "KernelAggregatePass":
        """从 registry options 构造 pass。

        功能说明:
        - 仅接受 `matmul-acc`。
        - unknown option 或非法 bool 均报告 `kernel-aggregate options...` 稳定短语。

        使用示例:
        - KernelAggregatePass.from_options({"matmul-acc": "true"})
        """

        unknown = sorted(set(options) - {"matmul-acc"})
        if unknown:
            names = ", ".join(unknown)
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"kernel-aggregate options unknown: {names}")
        value = options.get("matmul-acc", "false")
        matmul_acc = _parse_matmul_acc_option(value)
        return cls(matmul_acc=matmul_acc)

    def apply(self, ctx: Context, module: ModuleOp) -> None:
        """执行 kernel aggregate 重写。

        功能说明:
        - 遍历 builtin.module 中的 `kernel.matmul`。
        - 只重写同 block 相邻、tmp 生命周期唯一、K/reduce iterator 可唯一定位的公开形态。
        - tmp alloc/free 位于祖先 owner block 时，必须按 owner 顺序证明 alloc < owner loop < free。

        使用示例:
        - KernelAggregatePass(matmul_acc=True).apply(Context(), module)
        """

        _ = ctx
        ensure_builtin_module(module)
        if not self.matmul_acc:
            return
        rewritten_tmps: set[SSAValue] = set()
        for matmul in list(module.walk()):
            if not isinstance(matmul, KernelMatmulOp):
                continue
            block = matmul.parent_block()
            if block is None:
                continue
            block_ops = list(block.ops)
            matmul_index = block_ops.index(matmul)
            if matmul_index + 1 >= len(block_ops):
                continue
            add = block_ops[matmul_index + 1]
            if not isinstance(add, KernelBinaryElewiseOp) or add.kind.data != "add":
                continue
            tmp = SSAValue.get(matmul.out)
            out = SSAValue.get(add.out)
            if tmp in rewritten_tmps:
                raise _kernel_aggregate_error("ambiguous matmul fusion")
            if SSAValue.get(add.lhs) is not out or SSAValue.get(add.rhs) is not tmp:
                continue
            alloc = tmp.owner if isinstance(tmp.owner, DmaAllocOp) else None
            if alloc is None:
                continue
            alloc_block = alloc.parent_block()
            if alloc_block is None:
                continue
            uses = list(tmp.uses)
            free_ops = [use.operation for use in uses if isinstance(use.operation, DmaFreeOp)]
            expected_ops = {alloc, matmul, add, *free_ops}
            if len(free_ops) != 1 or any(use.operation not in expected_ops for use in uses):
                continue
            free = free_ops[0]
            if free.parent_block() is not alloc_block:
                continue
            owner_anchor = _ancestor_op_in_block(matmul, alloc_block)
            if owner_anchor is None:
                continue
            owner_ops = list(alloc_block.ops)
            alloc_index = owner_ops.index(alloc)
            anchor_index = owner_ops.index(owner_anchor)
            free_index = owner_ops.index(free)
            if not (alloc_index < anchor_index < free_index):
                continue
            lhs_type = SSAValue.get(matmul.lhs).type
            rhs_type = SSAValue.get(matmul.rhs).type
            if not isinstance(lhs_type, NnMemoryType) or not isinstance(rhs_type, NnMemoryType):
                continue
            contracting_dim = lhs_type.shape.data[1] if len(lhs_type.shape.data) == 2 else None
            if contracting_dim is None or contracting_dim != rhs_type.shape.data[0]:
                continue
            candidates: list[SymbolForOp] = []
            parent = matmul.parent_op()
            while parent is not None:
                if isinstance(parent, SymbolForOp):
                    iter_attr = parent.iter_attr
                    dim_text = contracting_dim.expr.data if isinstance(contracting_dim, SymbolExprAttr) else ""
                    step_text = iter_attr.step.expr.data
                    if contracting_dim == iter_attr.step or step_text == dim_text:
                        candidates.append(parent)
                parent = parent.parent_op()
            if len(candidates) != 1:
                raise _kernel_aggregate_error("matmul acc iterator")
            owner_loop = candidates[0]
            if not any(True for _ in owner_loop.body.blocks):
                raise _kernel_aggregate_error("matmul acc iterator")
            iter_value = owner_loop.body.block.args[0]
            acc = SymbolNeOp(iter_value, owner_loop.start, i1)
            fusion = KernelMatmulFusionOp(out, matmul.lhs, matmul.rhs, acc.result, space=matmul.space)
            verify_generated_ops([acc, fusion])
            block.insert_ops_before([acc, fusion], matmul)
            block.erase_op(add)
            block.erase_op(matmul)
            alloc_block.erase_op(free)
            alloc_block.erase_op(alloc)
            rewritten_tmps.add(tmp)


__all__ = ["KernelAggregatePass"]
