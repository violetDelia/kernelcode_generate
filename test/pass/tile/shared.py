"""tile public test shared builders.

创建者: OpenAI Codex
最后一次更改: OpenAI Codex

功能说明:
- 为 `tile` family 的公开测试提供最小 IR builder 与 op 收集 helper。
- 只构造公开 pattern/pass 所需的最小 `builtin.module` 输入，不引入对内部 helper 的测试依赖。

使用示例:
- module = build_elementwise_module()
- ops = collect_ops(module)

关联文件:
- spec: [spec/pass/tile/README.md](../../../spec/pass/tile/README.md)
- test: [test/pass/tile/test_analysis.py](../../../test/pass/tile/test_analysis.py)
- test: [test/pass/tile/test_elewise.py](../../../test/pass/tile/test_elewise.py)
- test: [test/pass/tile/test_reduce.py](../../../test/pass/tile/test_reduce.py)
"""

from __future__ import annotations

from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntAttr, ModuleOp, StringAttr, i32
from xdsl.ir import Block, Operation, Region

from kernel_gen.dialect.dma import DmaAllocOp, DmaBroadcastOp
from kernel_gen.dialect.kernel import KernelBinaryElewiseOp, KernelMatmulOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType


def make_memory_type(shape_names: list[str]) -> NnMemoryType:
    """构造最小测试用 `nn.memory` 类型。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 使用字符串维度构造稳定可读的 `nn.memory` 类型。
    - 为 tile public API 测试提供统一的 shape/stride 约定。

    使用示例:
    - mem_type = make_memory_type(["M", "N"])

    关联文件:
    - spec: [spec/pass/tile/README.md](../../../spec/pass/tile/README.md)
    - test: [test/pass/tile/test_analysis.py](../../../test/pass/tile/test_analysis.py)
    - 功能实现: [test/pass/tile/shared.py](../../../test/pass/tile/shared.py)
    """

    shape = ArrayAttr([StringAttr(name) for name in shape_names])
    stride = ArrayAttr([StringAttr(f"S{axis}") for axis in range(len(shape_names))])
    return NnMemoryType(shape, stride, i32, NnMemorySpaceAttr.from_name("global"))


def build_elementwise_module(kind: str = "add") -> ModuleOp:
    """构造单 `kernel.binary_elewise` 模块。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 生成 `out/lhs/rhs` 都是 `rank-2` memory 的最小 elementwise IR。
    - 供 `tile-analysis` 与 `tile-elewise` 的公开 pattern/pass 测试复用。

    使用示例:
    - module = build_elementwise_module("mul")

    关联文件:
    - spec: [spec/pass/tile/elewise.md](../../../spec/pass/tile/elewise.md)
    - test: [test/pass/tile/test_elewise.py](../../../test/pass/tile/test_elewise.py)
    - 功能实现: [test/pass/tile/shared.py](../../../test/pass/tile/shared.py)
    """

    mem_type = make_memory_type(["M", "N"])
    block = Block(arg_types=[mem_type, mem_type, mem_type])
    space = NnMemorySpaceAttr.from_name("global")
    block.add_ops(
        [
            KernelBinaryElewiseOp(block.args[2], block.args[0], block.args[1], kind=kind, space=space),
            func.ReturnOp(),
        ]
    )
    func_op = func.FuncOp(
        f"tile_{kind}",
        FunctionType.from_lists([mem_type, mem_type, mem_type], []),
        Region(block),
    )
    return ModuleOp([func_op])


def build_broadcast_module() -> ModuleOp:
    """构造单 `dma.broadcast` 模块。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 生成 target 为 `rank-2`、source 为 `rank-1` 的最小 broadcast IR。
    - 供 `tile-analysis` 与 `tile-elewise` 的公开 pattern/pass 测试复用。

    使用示例:
    - module = build_broadcast_module()

    关联文件:
    - spec: [spec/pass/tile/analysis.md](../../../spec/pass/tile/analysis.md)
    - test: [test/pass/tile/test_analysis.py](../../../test/pass/tile/test_analysis.py)
    - 功能实现: [test/pass/tile/shared.py](../../../test/pass/tile/shared.py)
    """

    target_type = make_memory_type(["M", "N"])
    source_type = make_memory_type(["N"])
    block = Block(arg_types=[target_type, source_type])
    block.add_ops([DmaBroadcastOp(block.args[0], block.args[1]), func.ReturnOp()])
    func_op = func.FuncOp(
        "tile_broadcast",
        FunctionType.from_lists([target_type, source_type], []),
        Region(block),
    )
    return ModuleOp([func_op])


def build_matmul_module() -> ModuleOp:
    """构造单 `kernel.matmul` 模块。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 生成 `lhs[M,K] / rhs[K,N] / out[M,N]` 的最小 matmul IR。
    - 供 `tile-analysis`、`tile-elewise`、`tile-reduce` 的公开测试复用。

    使用示例:
    - module = build_matmul_module()

    关联文件:
    - spec: [spec/pass/tile/reduce.md](../../../spec/pass/tile/reduce.md)
    - test: [test/pass/tile/test_reduce.py](../../../test/pass/tile/test_reduce.py)
    - 功能实现: [test/pass/tile/shared.py](../../../test/pass/tile/shared.py)
    """

    lhs_type = make_memory_type(["M", "K"])
    rhs_type = make_memory_type(["K", "N"])
    out_type = make_memory_type(["M", "N"])
    block = Block(arg_types=[lhs_type, rhs_type, out_type])
    space = NnMemorySpaceAttr.from_name("global")
    block.add_ops([KernelMatmulOp(block.args[2], block.args[0], block.args[1], space), func.ReturnOp()])
    func_op = func.FuncOp(
        "tile_matmul",
        FunctionType.from_lists([lhs_type, rhs_type, out_type], []),
        Region(block),
    )
    return ModuleOp([func_op])


def build_fc_chain_module() -> ModuleOp:
    """构造 `broadcast -> matmul -> add` 组合链路模块。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 用于验证 `tile-reduce` 只为 `matmul` reduce 计划建参。
    - 保持中间 `matmul` 输出先落到 `dma.alloc`，满足当前 pass 真实输入形态。

    使用示例:
    - module = build_fc_chain_module()

    关联文件:
    - spec: [spec/pass/tile/reduce.md](../../../spec/pass/tile/reduce.md)
    - test: [test/pass/tile/test_reduce.py](../../../test/pass/tile/test_reduce.py)
    - 功能实现: [test/pass/tile/shared.py](../../../test/pass/tile/shared.py)
    """

    out_type = make_memory_type(["M", "N"])
    x_type = make_memory_type(["M", "K"])
    weight_type = make_memory_type(["K", "N"])
    bias_type = make_memory_type(["N"])
    block = Block(arg_types=[out_type, x_type, weight_type, bias_type])
    space = NnMemorySpaceAttr.from_name("global")
    bias_alloc = DmaAllocOp([], out_type)
    matmul_alloc = DmaAllocOp([], out_type)
    block.add_ops(
        [
            bias_alloc,
            matmul_alloc,
            DmaBroadcastOp(bias_alloc.result, block.args[3]),
            KernelMatmulOp(matmul_alloc.result, block.args[1], block.args[2], space),
            KernelBinaryElewiseOp(block.args[0], matmul_alloc.result, bias_alloc.result, kind="add", space=space),
            func.ReturnOp(),
        ]
    )
    func_op = func.FuncOp(
        "tile_fc_chain",
        FunctionType.from_lists([out_type, x_type, weight_type, bias_type], []),
        Region(block),
    )
    return ModuleOp([func_op])


def collect_ops(root: object) -> list[Operation]:
    """递归收集模块内的所有 op。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 为公开 pass 测试提供统一的 loop/view/kernel 计数入口。
    - 避免测试文件重复实现 IR 遍历细节。

    使用示例:
    - ops = collect_ops(module)

    关联文件:
    - spec: [spec/pass/tile/README.md](../../../spec/pass/tile/README.md)
    - test: [test/pass/tile/test_elewise.py](../../../test/pass/tile/test_elewise.py)
    - 功能实现: [test/pass/tile/shared.py](../../../test/pass/tile/shared.py)
    """

    collected: list[Operation] = []

    def visit(op: Operation) -> None:
        collected.append(op)
        for region in op.regions:
            for block in region.blocks:
                for inner in block.ops:
                    visit(inner)

    if isinstance(root, ModuleOp):
        for op in root.ops:
            visit(op)
    elif isinstance(root, Operation):
        visit(root)
    return collected

