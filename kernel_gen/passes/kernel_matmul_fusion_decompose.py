"""kernel matmul fusion decompose pass.

功能说明:
- 提供 `kernel-matmul-fusion-decompose` pass，把中间 `kernel.matmul_fusion` 拆回已有可 emit IR。

API 列表:
- `class KernelMatmulFusionDecomposePass(fold: bool = True)`
- `KernelMatmulFusionDecomposePass.from_options(options: dict[str, str]) -> KernelMatmulFusionDecomposePass`
- `KernelMatmulFusionDecomposePass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from kernel_gen.passes.kernel_matmul_fusion_decompose import KernelMatmulFusionDecomposePass
- KernelMatmulFusionDecomposePass().apply(Context(), module)
- KernelMatmulFusionDecomposePass.from_options({})

关联文件:
- spec: spec/pass/kernel_matmul_fusion_decompose.md
- test: test/passes/test_kernel_matmul_fusion_decompose.py
- 功能实现: kernel_gen/passes/kernel_matmul_fusion_decompose.py
"""

from __future__ import annotations

from xdsl.context import Context
from xdsl.dialects import scf
from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import Block, Region, SSAValue

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dialect.dma import DmaAllocOp, DmaFreeOp
from kernel_gen.dialect.kernel import KernelBinaryElewiseOp, KernelMatmulFusionOp, KernelMatmulOp
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolExprAttr, SymbolGetDimOp
from kernel_gen.passes.common import ensure_builtin_module, verify_generated_ops
from kernel_gen.passes.pass_manager import Pass


def _kernel_matmul_fusion_decompose_error(message: str) -> KernelCodeError:
    """构造 kernel-matmul-fusion-decompose 错误。

    功能说明:
    - 统一 pass 内稳定错误短语前缀，便于 spec、pytest 与 expectation 机械匹配。

    使用示例:
    - raise _kernel_matmul_fusion_decompose_error("tmp type")
    """

    detail = message.strip()
    if not detail:
        detail = "unknown error"
    full_message = f"kernel-matmul-fusion-decompose {detail}"
    error = KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, full_message)
    return error


class KernelMatmulFusionDecomposePass(Pass):
    """分解 kernel.matmul_fusion 的公开 pass。

    功能说明:
    - 将每个 `kernel.matmul_fusion(out,lhs,rhs,acc)` 分解成 `scf.if %acc` 双分支。
    - true 分支重新分配与 out 完全同 type 的 tmp，执行 matmul+add+free。
    - false 分支直接执行覆盖写 `kernel.matmul(out,lhs,rhs)`。

    使用示例:
    - KernelMatmulFusionDecomposePass().apply(Context(), module)
    """

    name = "kernel-matmul-fusion-decompose"

    def __init__(self, fold: bool = True) -> None:
        """初始化 matmul fusion 分解 pass。

        功能说明:
        - 只记录通用 fold 开关；本 pass 不接受自定义 option。

        使用示例:
        - KernelMatmulFusionDecomposePass()
        """

        super().__init__(fold=fold)

    @classmethod
    def from_options(cls, options: dict[str, str]) -> "KernelMatmulFusionDecomposePass":
        """从 registry options 构造 pass。

        功能说明:
        - 第一版不接受自定义 option。
        - unknown option 稳定失败，错误短语包含 `kernel-matmul-fusion-decompose options`。

        使用示例:
        - KernelMatmulFusionDecomposePass.from_options({})
        """

        if options:
            names = ", ".join(sorted(options))
            raise KernelCodeError(
                ErrorKind.CONTRACT,
                ErrorModule.PASS,
                f"kernel-matmul-fusion-decompose options unknown: {names}",
            )
        return cls()

    def apply(self, ctx: Context, module: ModuleOp) -> None:
        """执行 kernel.matmul_fusion 分解。

        功能说明:
        - 遍历 builtin.module 中的 fusion op。
        - 在 fusion 前插入必要 `symbol.get_dim` 与 `scf.if`，再删除原 fusion op。

        使用示例:
        - KernelMatmulFusionDecomposePass().apply(Context(), module)
        """

        _ = ctx
        ensure_builtin_module(module)
        for fusion in list(module.walk()):
            if not isinstance(fusion, KernelMatmulFusionOp):
                continue
            block = fusion.parent_block()
            if block is None:
                continue
            out_type = SSAValue.get(fusion.out).type
            if not isinstance(out_type, NnMemoryType):
                raise _kernel_matmul_fusion_decompose_error("tmp type")
            get_dims: list[SymbolGetDimOp] = []
            dynamic_shape: list[SSAValue] = []
            for axis, dim in enumerate(out_type.shape.data):
                is_static = False
                if isinstance(dim, SymbolExprAttr):
                    try:
                        int(dim.expr.data)
                        is_static = True
                    except ValueError:
                        is_static = False
                if not is_static:
                    get_dim = SymbolGetDimOp(fusion.out, axis)
                    get_dims.append(get_dim)
                    dynamic_shape.append(get_dim.result)
            tmp = DmaAllocOp(dynamic_shape, out_type)
            then_matmul = KernelMatmulOp(tmp.result, fusion.lhs, fusion.rhs, fusion.space)
            then_add = KernelBinaryElewiseOp(fusion.out, fusion.out, tmp.result, kind="add", space=fusion.space)
            then_free = DmaFreeOp(tmp.result)
            then_block = Block()
            then_block.add_ops([tmp, then_matmul, then_add, then_free, scf.YieldOp()])
            else_matmul = KernelMatmulOp(fusion.out, fusion.lhs, fusion.rhs, fusion.space)
            else_block = Block()
            else_block.add_ops([else_matmul, scf.YieldOp()])
            if_op = scf.IfOp(fusion.acc, [], Region(then_block), Region(else_block))
            try:
                verify_generated_ops([*get_dims, tmp, then_matmul, then_add, then_free, else_matmul, if_op])
            except KernelCodeError as exc:
                raise _kernel_matmul_fusion_decompose_error("tmp type") from exc
            block.insert_ops_before([*get_dims, if_op], fusion)
            block.erase_op(fusion)


__all__ = ["KernelMatmulFusionDecomposePass"]
