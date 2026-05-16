"""DSL AST mlir_gen public contract tests.


功能说明:
- 直接通过 `mlir_gen(...)` 公开入口覆盖签名、解析环境、module 装配与集成行为。
- 测试文件名对应 `kernel_gen/dsl/ast/mlir_gen.py`，不再按已删除的内部 builder 拆分目录。
- 不使用 `_root_func`、函数级 builder 或解析环境 helper 这类非公开入口。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- pytest -q --cov=kernel_gen.dsl.ast.mlir_gen --cov-branch --cov-report=term-missing test/dsl/ast/test_mlir_gen.py

使用示例:
- pytest -q test/dsl/ast/test_mlir_gen.py

关联文件:
- 功能实现: kernel_gen/dsl/ast/mlir_gen.py
- Spec 文档: spec/dsl/ast/mlir_gen.md
- 测试文件: test/dsl/ast/test_mlir_gen.py
"""

from __future__ import annotations

import pytest
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, ModuleOp, i8

from kernel_gen.core.config import reset_config
from kernel_gen.core.context import build_default_context
from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.dma import DmaAllocOp, DmaBroadcastOp, DmaCopyOp, DmaDesliceOp, DmaFillOp, DmaFreeOp, DmaReshapeOp, DmaSliceOp
from kernel_gen.dialect.kernel import KernelBinaryElewiseOp, KernelImg2col1dOp, KernelImg2col2dOp, KernelMatmulOp
from kernel_gen.dialect.nn import NnAddOp, NnMatmulOp, NnMemorySpaceAttr, NnMemoryType, NnSoftmaxOp
from kernel_gen.dialect.symbol import SymbolExprAttr, SymbolForOp, SymbolGetDimOp, SymbolMaxOp, SymbolMinOp, SymbolMulOp, SymbolValueType
from kernel_gen.dsl import parse_function
from kernel_gen.dsl.ast import ModuleAST
from kernel_gen.dsl.ast.mlir_gen import mlir_gen
from kernel_gen.operation import copy as dma_copy
from kernel_gen.operation import free as dma_free
from kernel_gen.operation.arch import (
    get_block_id,
    get_block_num,
    get_dynamic_memory,
    get_subthread_id,
    get_subthread_num,
    get_thread_id,
    get_thread_num,
    launch_kernel,
)
from kernel_gen.operation import kernel as kernel_ops
from kernel_gen.operation.dma import alloc, cast as dma_cast, deslice, fill, flatten, load, reshape, slice, store, view
from kernel_gen.operation.nn import (
    add,
    broadcast,
    broadcast_to,
    conv,
    eq,
    exp,
    fc,
    floordiv,
    ge,
    gt,
    hard_sigmoid,
    img2col1d,
    img2col2d,
    le,
    leaky_relu,
    lt,
    matmul,
    mul,
    ne,
    reduce_max,
    reduce_min,
    reduce_sum,
    relu,
    sigmoid,
    softmax,
    sub,
    tanh,
    transpose,
    truediv,
)
from kernel_gen.operation.scf import loop
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType


@pytest.fixture(autouse=True)
def _reset_core_config() -> None:
    """重置进程级配置，避免 mlir_gen 测试之间串状态。"""
    reset_config()
    yield
    reset_config()


def _tensor_arg(
    shape: list[int | str],
    dtype: NumericType = NumericType.Float32,
    *,
    space: MemorySpace = MemorySpace.GM,
) -> Memory:
    """构造 Memory 测试入参。


    功能说明:
    - 简化 `mlir_gen(...)` 的 runtime_args 构造。

    使用示例:
    - arg = _tensor_arg([2, 2])

    关联文件:
    - spec: [spec/dsl/ast/mlir_gen.md](spec/dsl/ast/mlir_gen.md)
    - test: [test/dsl/ast/test_mlir_gen.py](test/dsl/ast/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/ast/mlir_gen.py](kernel_gen/dsl/ast/mlir_gen.py)
    """

    return Memory(shape, dtype, space=space)


def _memory_symbol_expr_attr(value: int | str) -> SymbolExprAttr:
    """构造测试用 symbol 表达 attr。


    功能说明:
    - 为 `_memory_type(...)` 提供模块级 helper，避免测试函数内嵌套函数。

    使用示例:
    - attr = _memory_symbol_expr_attr("M + 1")
    """

    return SymbolExprAttr.from_expr(str(value))


def _memory_type(
    shape: list[int | str],
    stride: list[int | str],
    *,
    space: str = "global",
) -> NnMemoryType:
    """构造测试用 `NnMemoryType`。


    功能说明:
    - 为 module 级测试提供公开结果类型对比对象。

    使用示例:
    - mem_type = _memory_type([2, 4], [4, 1])

    关联文件:
    - spec: [spec/dsl/ast/mlir_gen.md](spec/dsl/ast/mlir_gen.md)
    - test: [test/dsl/ast/test_mlir_gen.py](test/dsl/ast/test_mlir_gen.py)
    - 功能实现: [kernel_gen/dsl/ast/mlir_gen.py](kernel_gen/dsl/ast/mlir_gen.py)
    """

    return NnMemoryType(
        ArrayAttr([_memory_symbol_expr_attr(dim) for dim in shape]),
        ArrayAttr([_memory_symbol_expr_attr(dim) for dim in stride]),
        i8,
        NnMemorySpaceAttr.from_name(space),
    )


def _symbol_min_iter_kernel(out: Memory, src: Memory, tile_n: SymbolDim) -> None:
    """提供模块级 DSL kernel，避免测试函数内定义非装饰器嵌套函数。"""

    n_size = src.shape.get_shape()[0]
    for index in loop(0, n_size, tile_n):
        offset = index * 1
        cur_n = min(tile_n, n_size - index)
        tile_buf = slice(src, [offset], [cur_n], [1], MemorySpace.TSM)
        deslice(out, tile_buf, [offset], [cur_n], [1])


def _symbol_min_dynamic_expr_kernel(lhs: SymbolDim, rhs: SymbolDim) -> int:
    """提供动态 symbol.min 复合 operand DSL kernel。"""

    return min(lhs + 1, rhs - 2)


def _symbol_max_dynamic_expr_kernel(lhs: SymbolDim, rhs: SymbolDim) -> int:
    """提供动态 symbol.max 复合 operand DSL kernel。"""

    return max(lhs + 1, rhs - 2)


def _symbol_max_static_fold_kernel() -> int:
    """提供静态 max 折叠 DSL kernel。"""

    return max(2, 5)


def _symbol_max_bad_arity_kernel(lhs: SymbolDim) -> int:
    """提供 max arity 错误 DSL kernel。"""

    return max(lhs)


def _symbol_max_non_value_arg_kernel(lhs: SymbolDim) -> int:
    """提供 max 非 ValueAST 参数错误 DSL kernel。"""

    return max([lhs], lhs)


def _symbol_max_non_symbol_arg_kernel(lhs: SymbolDim) -> int:
    """提供 max 非 symbol 参数错误 DSL kernel。"""

    return max(1.5, lhs)


def _unknown_symbol_name_kernel() -> int:
    """提供未知名称错误 DSL kernel。"""

    return UNKNOWN_SYMBOL_FOR_TEST


def public_nn_activation_reduce_kernel(x: Memory) -> None:
    relu(x)
    sigmoid(x)
    tanh(x)
    exp(x)
    leaky_relu(x, alpha=0.25)
    hard_sigmoid(x, alpha=0.2, beta=0.5)
    reduce_sum(x, axis=1, keepdim=True)
    reduce_min(x, axis=0, keepdim=False)
    reduce_max(x)
    softmax(x, axis=-1)


def public_nn_arithmetic_compare_kernel(lhs: Memory, rhs: Memory, scalar: int) -> None:
    add(lhs, rhs)
    sub(lhs, scalar)
    mul(scalar, lhs)
    truediv(lhs, rhs)
    floordiv(lhs, 2)
    eq(lhs, rhs)
    ne(lhs, rhs)
    lt(lhs, rhs)
    le(lhs, rhs)
    gt(lhs, rhs)
    ge(lhs, rhs)


def public_nn_broadcast_kernel(src: Memory, target: Memory, shape_dim: int) -> None:
    broadcast(src, target)
    broadcast_to(src, [shape_dim, 3], MemorySpace.GM)
    transpose(target, [1, 0])


def public_nn_structured_kernel(
    mat_lhs: Memory,
    mat_rhs: Memory,
    fc_weight: Memory,
    img1d: Memory,
    img2d: Memory,
    conv_input: Memory,
    conv_weight: Memory,
) -> None:
    matmul(mat_lhs, mat_rhs)
    fc(mat_lhs, fc_weight)
    img2col1d(img1d, kw=3, sw=1, dw=1, pl=1, pr=1)
    img2col2d(img2d, kh=3, kw=3, sh=1, sw=1, dh=1, dw=1, ph=1, pw=1, pl=1, pr=1)
    conv(conv_input, conv_weight, sh=1, sw=1, dh=1, dw=1, ph=1, pw=1, pl=1, pr=1)


def public_dma_helper_chain_kernel(x: Memory, y: Memory, n: int) -> None:
    local = alloc([n, 4], NumericType.Float32, MemorySpace.SM)
    fill(local, "inf")
    copied = dma_copy(x, MemorySpace.SM)
    loaded = load(x, [0, 0], [n, 4], [1, 1], MemorySpace.SM)
    slice(x, [0, 0], [n, 4], [1, 1], MemorySpace.SM)
    view(x, [0, 0], [n, 4], [1, 1])
    reshape(loaded, [n * 4])
    flatten(x)
    dma_cast(copied, NumericType.Float16, MemorySpace.SM)
    store(y, local, [0, 0], [n, 4], [1, 1])
    deslice(y, local, [0, 0], [n, 4], [1, 1])


def public_arch_launched_body(x: Memory) -> None:
    get_block_num()
    get_thread_num()
    get_subthread_num()


def public_arch_helper_kernel(x: Memory) -> None:
    get_block_id()
    get_block_num()
    get_thread_id()
    get_thread_num()
    get_subthread_id()
    get_subthread_num()
    get_dynamic_memory(MemorySpace.SM)
    get_dynamic_memory(MemorySpace.LM)
    launch_kernel[1, 2, 3, 0](public_arch_launched_body, x)


def public_kernel_out_first_helper_kernel(
    ele_out: Memory,
    ele_lhs: Memory,
    ele_rhs: Memory,
    mat_out: Memory,
    mat_lhs: Memory,
    mat_rhs: Memory,
    img1_out: Memory,
    img1_in: Memory,
    img2_out: Memory,
    img2_in: Memory,
    k: SymbolDim,
    kh: SymbolDim,
    kw: SymbolDim,
) -> None:
    """提供 kernel out-first helper DSL kernel。"""

    kernel_ops.add(ele_out, ele_lhs, ele_rhs)
    kernel_ops.binary_elewise(ele_out, ele_lhs, ele_rhs, kind=kernel_ops.KernelBinaryElewiseKind.SUB)
    kernel_ops.matmul(mat_out, mat_lhs, mat_rhs)
    kernel_ops.img2col1d(img1_out, img1_in, k)
    kernel_ops.img2col2d(img2_out, img2_in, kh=kh, kw=kw, ph=1, pw=1, pl=1, pr=1)


def public_memory_get_shape_direct_kernel(out: Memory, src: Memory) -> None:
    """提供 Memory.get_shape 解包和索引 DSL kernel。"""

    rows, cols = src.get_shape()
    row_again = src.get_shape()[0]
    tile = slice(src, [0, 0], [row_again, cols], [1, 1], MemorySpace.TSM)
    deslice(out, tile, [0, 0], [rows, cols], [1, 1])


def test_mlir_gen_requires_runtime_args() -> None:
    """TC-MLIR-GEN-FUNC-001: 运行时参数缺失时必须报错。"""

    def kernel(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
        return x

    with pytest.raises(KernelCodeError) as excinfo:
        mlir_gen(kernel)
    assert "mlir_gen requires explicit runtime args for kernel: expected 1, got 0" in str(excinfo.value)


def test_mlir_gen_returns_module_with_root_func() -> None:
    """TC-MLIR-GEN-FUNC-002: `mlir_gen(...)` 返回 module，首个 op 是 root func。"""

    def identity(x: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return x

    module = mlir_gen(identity, _tensor_arg([2, 2]))

    assert isinstance(module, ModuleOp)
    root_op = list(module.body.block.ops)[0]
    assert isinstance(root_op, func.FuncOp)
    assert root_op.sym_name.data == "identity"


def test_mlir_gen_reports_reduce_max_axis_out_of_range() -> None:
    """TC-MLIR-GEN-FUNC-003: reduce_max 轴越界必须报错。"""

    def kernel(x: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2]":
        return reduce_max(x, axis=3)

    with pytest.raises(KernelCodeError, match=r"reduce_max axis must be within \[-2, 1\]"):
        mlir_gen(kernel, _tensor_arg([2, 2]))


def test_mlir_gen_accepts_runtime_driven_memory_placeholder_annotation() -> None:
    """TC-MLIR-GEN-FUNC-004: 裸 Memory 注解由 runtime arg 驱动签名。"""

    runtime_arg = _tensor_arg([2, 4])

    def kernel(x: Memory) -> "Tensor[f32, 2, 4]":
        return x

    module = mlir_gen(kernel, runtime_arg)
    root_op = list(module.body.block.ops)[0]
    assert isinstance(root_op, func.FuncOp)
    block_args = tuple(root_op.body.block.args)

    assert len(block_args) == 1
    assert isinstance(block_args[0].type, NnMemoryType)
    assert block_args[0].type.shape == _memory_type([2, 4], [4, 1]).shape


def test_mlir_gen_accepts_runtime_driven_symbol_placeholder_annotation() -> None:
    """TC-MLIR-GEN-FUNC-005: 裸 SymbolDim 注解由 runtime arg 驱动签名。"""

    runtime_arg = SymbolDim("N")

    def kernel(n: SymbolDim) -> int:
        return n

    module = mlir_gen(kernel, runtime_arg)
    root_op = list(module.body.block.ops)[0]
    assert isinstance(root_op, func.FuncOp)
    block_args = tuple(root_op.body.block.args)

    assert len(block_args) == 1
    assert block_args[0].type == SymbolValueType.from_expr("N")
    assert root_op.function_type.outputs.data[0] == SymbolValueType.from_expr("N")


def test_mlir_gen_supports_kernel_contract_metadata_assert_and_shape_unpack() -> None:
    """TC-MLIR-GEN-FUNC-006: shape unpack 与 assert metadata 不阻断 module 生成。"""

    lhs = Memory(["B", "K"], NumericType.Float32)
    rhs = Memory(["B", "K"], NumericType.Float32)
    tile = SymbolDim("BR")

    def kernel(x: Memory, y: Memory, step: SymbolDim) -> int:
        assert x.dtype == y.dtype
        B, K = x.shape.get_shape()
        for _b in loop(0, B, step):
            tile_buf = alloc([1, K], x.dtype, MemorySpace.TSM)
            fill(tile_buf, 0)
        return K

    module = mlir_gen(kernel, lhs, rhs, tile)
    root_op = list(module.body.block.ops)[0]
    assert isinstance(root_op, func.FuncOp)
    body_ops = list(root_op.body.block.ops)

    assert any(isinstance(op, SymbolGetDimOp) for op in body_ops)
    assert any(isinstance(op, func.ReturnOp) for op in body_ops)


def test_mlir_gen_supports_kernel_contract_loop_local_rebinding() -> None:
    """TC-MLIR-GEN-FUNC-007: 循环内 memory/helper 重绑定保持在 symbol.for 内。"""

    q = Memory(["M", "N"], NumericType.Float32)
    out = Memory(["M", "N"], NumericType.Float32)
    tile = SymbolDim("TILE")

    def kernel(x: Memory, y: Memory, step: SymbolDim) -> None:
        M, N = x.shape.get_shape()
        acc = alloc([step, N], x.dtype, MemorySpace.TSM)
        fill(acc, 0)
        for m0 in loop(0, M, step):
            tile_buf = slice(x, [m0, 0], [step, N], [1, 1], MemorySpace.TSM)
            acc = add(acc, tile_buf)
        out_tile = reshape(acc, [step, N])
        deslice(y, out_tile, [0, 0], [step, N], [1, 1])

    module = mlir_gen(kernel, q, out, tile)
    assert isinstance(module, ModuleOp)
    module_text = str(module)

    assert "symbol.for" in module_text
    assert '"dma.slice"' in module_text
    assert '"nn.add"' in module_text
    assert '"dma.reshape"' in module_text
    assert '"dma.deslice"' in module_text


def test_mlir_gen_lowers_symbol_min_and_iter_arithmetic() -> None:
    """TC-MLIR-GEN-SYM-MIN-001: DSL min 与 loop 迭代变量算术生成 symbol dialect。"""

    source = Memory([6], NumericType.Int32)
    output = Memory([6], NumericType.Int32)
    tile = SymbolDim("TILE_N")

    module = mlir_gen(_symbol_min_iter_kernel, output, source, tile)
    module_text = str(module)

    assert "symbol.min" in module_text
    assert "symbol.mul" in module_text
    assert "iter<0,6,TILE_N>" in module_text
    assert "!symbol.int<#symbol.expr<?>>" not in module_text
    assert "N - " + "f0" not in module_text
    assert "2 - " + "f0" not in module_text
    root_op = list(module.body.block.ops)[0]
    assert isinstance(root_op, func.FuncOp)
    assert any(isinstance(op, SymbolForOp) for op in root_op.body.block.ops)
    loop_op = next(op for op in root_op.body.block.ops if isinstance(op, SymbolForOp))
    assert any(isinstance(op, SymbolMinOp) for op in loop_op.body.block.ops)
    assert any(isinstance(op, SymbolMulOp) for op in loop_op.body.block.ops)


def test_mlir_gen_materializes_symbol_min_operand_consts_before_arithmetic() -> None:
    """TC-MLIR-GEN-SYM-MIN-002: 复合 operand 的常量先于二元算术发射。"""

    module = mlir_gen(_symbol_min_dynamic_expr_kernel, SymbolDim("W"), SymbolDim("HBOGU"))
    module_text = str(module)

    const_one_index = module_text.index("symbol.const 1")
    const_two_index = module_text.index("symbol.const 2")
    add_index = module_text.index("symbol.add")
    sub_index = module_text.index("symbol.sub")
    min_index = module_text.index("symbol.min")

    assert const_one_index < const_two_index < add_index < sub_index < min_index


def test_mlir_gen_lowers_symbol_max_and_materializes_operand_consts() -> None:
    """TC-MLIR-GEN-SYM-MAX-001: DSL max 生成 symbol.max 并稳定常量顺序。"""

    module = mlir_gen(_symbol_max_dynamic_expr_kernel, SymbolDim("W"), SymbolDim("HBOGU"))
    module_text = str(module)

    const_one_index = module_text.index("symbol.const 1")
    const_two_index = module_text.index("symbol.const 2")
    add_index = module_text.index("symbol.add")
    sub_index = module_text.index("symbol.sub")
    max_index = module_text.index("symbol.max")

    assert const_one_index < const_two_index < add_index < sub_index < max_index
    root_op = list(module.body.block.ops)[0]
    assert isinstance(root_op, func.FuncOp)
    assert any(isinstance(op, SymbolMaxOp) for op in root_op.body.block.ops)


def test_mlir_gen_folds_static_symbol_max() -> None:
    """TC-MLIR-GEN-SYM-MAX-002: 静态 max 通过公开 DSL 入口折叠为常量。"""

    module = mlir_gen(_symbol_max_static_fold_kernel)

    assert "symbol.const 5" in str(module)


@pytest.mark.parametrize(
    ("kernel", "message"),
    [
        (_symbol_max_bad_arity_kernel, "Unsupported max arity"),
        (_symbol_max_non_value_arg_kernel, "max arguments must be symbol values"),
        (_symbol_max_non_symbol_arg_kernel, "max arguments must be symbol values"),
    ],
)
def test_mlir_gen_rejects_invalid_symbol_max_calls(kernel, message: str) -> None:
    """TC-MLIR-GEN-SYM-MAX-003: 非公开 max 输入域稳定失败。"""

    with pytest.raises(KernelCodeError, match=message):
        mlir_gen(kernel, SymbolDim("N"))


def test_mlir_gen_rejects_unknown_name() -> None:
    """TC-MLIR-GEN-NAME-001: 未知名称经公开 mlir_gen 入口稳定失败。"""

    with pytest.raises(KernelCodeError, match="Unknown name"):
        mlir_gen(_unknown_symbol_name_kernel)


def test_mlir_gen_uses_runtime_args_for_symbol_signature() -> None:
    """TC-MLIR-GEN-SIG-001: SymbolDim runtime arg 生成 symbol 签名。"""

    def only_symbol(expr: int) -> int:
        return expr

    module = mlir_gen(only_symbol, SymbolDim("expr"))
    assert isinstance(module, ModuleOp)
    root_op = list(module.body.block.ops)[0]
    assert isinstance(root_op, func.FuncOp)

    assert list(root_op.function_type.inputs) == [SymbolValueType.from_expr("expr")]
    assert list(root_op.function_type.outputs) == [SymbolValueType.from_expr("expr")]


def test_mlir_gen_supports_multiple_return_values() -> None:
    """TC-MLIR-GEN-SIG-001B: tuple return 生成多 result func.return。"""

    lhs = SymbolDim("lhs")
    rhs = SymbolDim("rhs")

    def pair(left: int, right: int) -> tuple[int, int]:
        return left, right

    module = mlir_gen(pair, lhs, rhs)
    root_op = list(module.body.block.ops)[0]
    assert isinstance(root_op, func.FuncOp)
    return_op = list(root_op.body.block.ops)[-1]

    assert list(root_op.function_type.outputs) == [
        SymbolValueType.from_expr("lhs"),
        SymbolValueType.from_expr("rhs"),
    ]
    assert isinstance(return_op, func.ReturnOp)
    assert len(return_op.arguments) == 2


def test_mlir_gen_supports_dma_alloc_helper_with_symbol_shape_args() -> None:
    """TC-MLIR-GEN-SIG-002: alloc-only kernel 保持符号签名与结果 shape。"""

    symbol_lhs = SymbolDim("M")
    symbol_rhs = SymbolDim("N")
    lhs_expr = str(symbol_lhs.get_symbol())
    rhs_expr = str(symbol_rhs.get_symbol())

    def alloc_kernel(rank1: int, rank2: int) -> "Tensor[f32, M, N]":
        return alloc([rank1, rank2], NumericType.Float32, MemorySpace.SM)

    module = mlir_gen(alloc_kernel, symbol_lhs, symbol_rhs)
    root_op = list(module.body.block.ops)[0]
    assert isinstance(root_op, func.FuncOp)
    alloc_ops = [op for op in root_op.body.block.ops if isinstance(op, DmaAllocOp)]

    assert list(root_op.function_type.inputs) == [
        SymbolValueType.from_expr(lhs_expr),
        SymbolValueType.from_expr(rhs_expr),
    ]
    assert len(alloc_ops) == 1
    assert [attr.expr.data for attr in alloc_ops[0].result.type.shape.data] == [lhs_expr, rhs_expr]
    assert list(root_op.function_type.outputs) == [alloc_ops[0].result.type]


def test_mlir_gen_rejects_dma_alloc_helper_with_non_contiguous_stride() -> None:
    """TC-MLIR-GEN-SIG-003: alloc-only kernel 仍拒绝非连续 stride。"""

    def alloc_kernel(rank1: int, rank2: int, stride1: int, stride2: int) -> "Tensor[f32, 2, 3]":
        return alloc(
            [rank1, rank2],
            NumericType.Float32,
            MemorySpace.SM,
            stride=[stride1, stride2],
        )

    with pytest.raises(KernelCodeError, match="dma.alloc only supports contiguous stride"):
        mlir_gen(alloc_kernel, 2, 3, 3, 2)


def test_mlir_gen_mixed_dtype_return_annotation_uses_body_result_type() -> None:
    """TC-MLIR-GEN-SIG-004: 返回类型按 body 实际结果推导，不受 annotation 改写。"""

    def mul_mixed_invalid(
        lhs: "Tensor[f32, 2, 2]",
        rhs: "Tensor[i32, 2, 2]",
    ) -> "Tensor[f16, 2, 2]":
        return lhs * rhs

    module = mlir_gen(
        mul_mixed_invalid,
        _tensor_arg([2, 2], NumericType.Float32),
        _tensor_arg([2, 2], NumericType.Int32),
    )
    root_op = list(module.body.block.ops)[0]
    assert isinstance(root_op, func.FuncOp)
    result_type = list(root_op.function_type.outputs)[0]
    assert isinstance(result_type, NnMemoryType)
    assert result_type.element_type == list(root_op.function_type.inputs)[0].element_type


def test_mlir_gen_supports_flatten_return_annotation() -> None:
    """TC-MLIR-GEN-SIG-005: flatten 返回 shape 按一维 numel 归一。"""

    from kernel_gen.operation.dma import flatten

    def flatten_kernel(src: "Tensor[f32, 4, 4]") -> "Tensor[f32, 16]":
        return flatten(src)

    module = mlir_gen(flatten_kernel, _tensor_arg([4, 4]))
    root_op = list(module.body.block.ops)[0]
    assert isinstance(root_op, func.FuncOp)
    result_type = list(root_op.function_type.outputs)[0]

    assert [attr.expr.data for attr in result_type.shape.data] == ["16"]
    assert [attr.expr.data for attr in result_type.stride.data] == ["1"]


def test_mlir_gen_matches_public_parse_function() -> None:
    """TC-MLIR-GEN-INT-001: public parse_function 与 mlir_gen 入口保持函数名和基本 op 一致。"""

    def add_kernel(x: "Tensor[f32, 2, 2]", y: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return x + y

    lhs = _tensor_arg([2, 2])
    rhs = _tensor_arg([2, 2])
    func_ast = parse_function(add_kernel, lhs, rhs)

    module = mlir_gen(add_kernel, lhs, rhs)
    func_ops = [op for op in module.ops if isinstance(op, func.FuncOp)]

    assert func_ast.name == "add_kernel"
    assert len(func_ops) == 1
    assert any(isinstance(op, NnAddOp) for op in func_ops[0].body.block.ops)


def test_mlir_gen_lowers_public_tensor_axis_access() -> None:
    """TC-MLIR-GEN-INT-002: public tensor axis 访问下沉为 symbol.get_dim。"""

    def shape_axis(x: "Tensor[f32, 4, 8]") -> int:
        return x.get_shape()[1]

    module = mlir_gen(shape_axis, _tensor_arg([4, 8]))
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))

    get_dim_ops = [op for op in func_op.body.block.ops if isinstance(op, SymbolGetDimOp)]
    assert len(get_dim_ops) == 1
    assert get_dim_ops[0].axis.data == 1


def test_mlir_gen_lowers_public_dma_helpers() -> None:
    """TC-MLIR-GEN-INT-003: public dma copy/free helper 下沉为 DMA op。"""

    def dma_kernel(src: "Tensor[f32, 2, 2]") -> None:
        local = dma_copy(src, MemorySpace.SM)
        dma_free(local)

    module = mlir_gen(dma_kernel, _tensor_arg([2, 2]))
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))

    body_ops = list(func_op.body.block.ops)
    assert any(isinstance(op, DmaCopyOp) for op in body_ops)
    assert any(isinstance(op, DmaFreeOp) for op in body_ops)
    assert isinstance(body_ops[-1], func.ReturnOp)


def test_mlir_gen_reports_public_broadcast_mismatch() -> None:
    """TC-MLIR-GEN-INT-004: public broadcast mismatch 报稳定错误文本。"""

    def add_kernel(x: "Tensor[f32, A, B]", y: "Tensor[f32, A, C]") -> "Tensor[f32, A, B]":
        return x + y

    with pytest.raises(KernelCodeError, match="Implicit broadcast dimension mismatch") as exc_info:
        mlir_gen(add_kernel, _tensor_arg(["A", "B"]), _tensor_arg(["A", "C"]))

    assert exc_info.value.message() == "Implicit broadcast dimension mismatch"


def test_mlir_gen_lowers_public_dma_fill_helper() -> None:
    """TC-MLIR-GEN-INT-005: public dma alloc/fill helper 下沉为 DMA fill。"""

    def init_kernel() -> None:
        scratch = alloc([2, 2], NumericType.Float32)
        fill(scratch, "-inf")

    module = mlir_gen(init_kernel)
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))

    body_ops = list(func_op.body.block.ops)
    assert any(isinstance(op, DmaFillOp) for op in body_ops)
    assert not any(isinstance(op, DmaBroadcastOp) for op in body_ops)
    assert isinstance(body_ops[-1], func.ReturnOp)


def test_module_ast_emit_mlir_matches_mlir_gen_entry() -> None:
    """TC-MLIR-GEN-INT-006: AST 公开 emit 结果与 mlir_gen 入口一致。"""

    def identity(x: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return x

    memory = _tensor_arg([2, 2])
    from_module_ast = ModuleAST([parse_function(identity, memory)]).emit_mlir(build_default_context(), None)
    from_public_entry = mlir_gen(identity, memory)

    assert str(from_module_ast) == str(from_public_entry)


def test_mlir_gen_emits_python_callee_call() -> None:
    """TC-MLIR-GEN-MOD-001: mlir_gen 把合法 Python callee 下沉为 func.call。"""

    def helper(x: "Tensor[f32, 4]") -> None:
        x + x

    def main(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
        helper(x)
        return x

    module = mlir_gen(main, Memory([4], NumericType.Float32))
    func_ops = [op for op in module.ops if isinstance(op, func.FuncOp)]
    call_ops = [op for op in func_ops[0].body.block.ops if isinstance(op, func.CallOp)]

    assert [op.sym_name.data for op in func_ops] == ["main", "helper"]
    assert len(call_ops) == 1
    assert call_ops[0].callee.string_value() == "helper"


def test_mlir_gen_emits_supported_closure_callee() -> None:
    """TC-MLIR-GEN-MOD-002: closure callee 内部全是支持操作时可下沉。"""

    def _make_closure():
        captured = 1

        def helper(x: "Tensor[f32, 4]") -> None:
            x + captured

        return helper

    closure = _make_closure()

    def main(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
        closure(x)
        return x

    module = mlir_gen(main, Memory([4], NumericType.Float32))
    func_ops = [op for op in module.ops if isinstance(op, func.FuncOp)]

    assert [op.sym_name.data for op in func_ops] == ["main", "helper"]
    assert "func.call @helper" in str(module)


def test_mlir_gen_rejects_invalid_dynamic_memory_in_root() -> None:
    """TC-MLIR-GEN-MOD-003: root 中非法 dynamic memory 报公开错误。"""

    def bad_root() -> "Tensor[i8, ?]":
        return get_dynamic_memory(MemorySpace.GM)

    with pytest.raises(KernelCodeError, match="get_dynamic_memory space must be on-chip MemorySpace"):
        mlir_gen(bad_root)


def test_mlir_gen_reuses_repeated_python_callee_call() -> None:
    """TC-MLIR-GEN-MOD-004: 重复 Python callee 调用只生成一个 callee func。"""

    def helper(x: "Tensor[f32, 4]") -> None:
        x + x

    def main(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
        helper(x)
        helper(x)
        return x

    module = mlir_gen(main, Memory([4], NumericType.Float32))
    func_ops = [op for op in module.ops if isinstance(op, func.FuncOp)]
    call_ops = [op for op in func_ops[0].body.block.ops if isinstance(op, func.CallOp)]

    assert [op.sym_name.data for op in func_ops] == ["main", "helper"]
    assert len(call_ops) == 2


def test_mlir_gen_binds_python_callee_argument_from_dsl_node() -> None:
    """TC-MLIR-GEN-MOD-004B: Python callee 参数绑定 caller 侧 DSLNode，不反推 runtime object。"""

    def helper(tile: Memory) -> None:
        fill(tile, 0)

    def main(x: Memory) -> Memory:
        tile = slice(x, [0], [2], [1], MemorySpace.TSM)
        helper(tile)
        return x

    module = mlir_gen(main, Memory([4], NumericType.Float32))
    func_ops = [op for op in module.ops if isinstance(op, func.FuncOp)]
    call_ops = [op for op in func_ops[0].body.block.ops if isinstance(op, func.CallOp)]
    helper_op = func_ops[1]

    assert [op.sym_name.data for op in func_ops] == ["main", "helper"]
    assert len(call_ops) == 1
    assert call_ops[0].callee.string_value() == "helper"
    assert len(helper_op.body.block.args) == 1
    assert isinstance(helper_op.body.block.args[0].type, NnMemoryType)
    assert str(helper_op.body.block.args[0].type.space) == "#nn.space<tsm>"


def test_mlir_gen_emits_transitive_python_callees_in_first_use_order() -> None:
    """TC-MLIR-GEN-MOD-005: 传递 callee 按首次使用 DFS 顺序追加到 module。"""

    def leaf(x: "Tensor[f32, 4]") -> None:
        x + x

    def mid(x: "Tensor[f32, 4]") -> None:
        leaf(x)

    def root(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
        mid(x)
        leaf(x)
        return x

    module = mlir_gen(root, Memory([4], NumericType.Float32))
    func_ops = [op for op in module.ops if isinstance(op, func.FuncOp)]

    assert [op.sym_name.data for op in func_ops] == ["root", "mid", "leaf"]


def test_mlir_gen_rejects_recursive_python_callee() -> None:
    """TC-MLIR-GEN-MOD-006: 递归 Python callee 在解析阶段稳定失败。"""

    def helper(x: "Tensor[f32, 4]") -> None:
        helper(x)

    def main(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
        helper(x)
        return x

    with pytest.raises(KernelCodeError, match="Recursive Python callee is unsupported"):
        mlir_gen(main, Memory([4], NumericType.Float32))


def test_mlir_gen_rejects_python_callee_result_assignment() -> None:
    """TC-MLIR-GEN-MOD-007: Python callee 调用不能作为值赋给变量。"""

    def helper(x: "Tensor[f32, 4]") -> None:
        x + x

    def main(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
        y = helper(x)
        return x

    with pytest.raises(KernelCodeError, match="Python callee return value is unsupported"):
        mlir_gen(main, Memory([4], NumericType.Float32))


def test_mlir_gen_rejects_python_callee_value_return() -> None:
    """TC-MLIR-GEN-MOD-008: Python callee 有返回值时不能下沉为 func.call。"""

    def helper(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
        return x

    def main(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
        helper(x)
        return x

    with pytest.raises(KernelCodeError, match="Python callee return value is unsupported"):
        mlir_gen(main, Memory([4], NumericType.Float32))


def test_mlir_gen_rejects_python_callee_in_value_contexts() -> None:
    """TC-MLIR-GEN-MOD-009: helper(...) 不得泄漏进任何值上下文。"""

    def helper(x: "Tensor[f32, 4]") -> None:
        x + x

    def call_in_if(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
        if helper(x):
            return x
        return x

    def call_in_argument(x: "Tensor[f32, 4]") -> "Tensor[f32, 4]":
        add(helper(x), x)
        return x

    def call_in_tuple_return(x: "Tensor[f32, 4]") -> tuple[Memory, Memory]:
        return x, helper(x)

    for fn in (call_in_if, call_in_argument, call_in_tuple_return):
        with pytest.raises(KernelCodeError, match="Python callee return value is unsupported"):
            mlir_gen(fn, Memory([4], NumericType.Float32))


def test_mlir_gen_uses_runtime_args_over_shadowed_parse_env_names() -> None:
    """TC-MLIR-GEN-PARSE-001: runtime_args 是公开签名真源。"""

    runtime_expr = SymbolDim("runtime")

    def only_symbol(runtime: int) -> int:
        return runtime

    module = mlir_gen(only_symbol, runtime_expr)
    assert isinstance(module, ModuleOp)
    root_op = list(module.body.block.ops)[0]
    assert isinstance(root_op, func.FuncOp)
    assert list(root_op.function_type.inputs) == [SymbolValueType.from_expr("runtime")]
    assert list(root_op.function_type.outputs) == [SymbolValueType.from_expr("runtime")]


def test_mlir_gen_globals_cannot_replace_runtime_args() -> None:
    """TC-MLIR-GEN-PARSE-002: 旧 `globals` 公开参数已删除。"""

    expr = SymbolDim("expr")

    def only_symbol(expr: int) -> int:
        return expr

    with pytest.raises(TypeError, match="unexpected keyword argument 'globals'"):
        mlir_gen(only_symbol, **{"globals": {"expr": expr}})


def test_mlir_gen_rejects_builtins_external_value_reference() -> None:
    """TC-MLIR-GEN-PARSE-003: 旧 `builtins` 公开参数已删除。"""

    def use_builtin_value() -> int:
        return BUILTIN_EXTERNAL_VALUE

    with pytest.raises(TypeError, match="unexpected keyword argument 'builtins'"):
        mlir_gen(use_builtin_value, **{"builtins": {"BUILTIN_EXTERNAL_VALUE": 13}})


def test_module_ast_emit_mlir_requires_context() -> None:
    """TC-MLIR-GEN-AST-001: ModuleAST.emit_mlir 必须显式传入 Context。"""

    def add_kernel(x: "Tensor[f32, 2, 2]", y: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return x + y

    module_ast = ModuleAST([parse_function(add_kernel, _tensor_arg([2, 2]), _tensor_arg([2, 2]))])

    with pytest.raises(TypeError):
        module_ast.emit_mlir()


def test_module_ast_emit_mlir_returns_module_op() -> None:
    """TC-MLIR-GEN-AST-002: ModuleAST.emit_mlir 返回 ModuleOp。"""

    def add_kernel(x: "Tensor[f32, 2, 2]", y: "Tensor[f32, 2, 2]") -> "Tensor[f32, 2, 2]":
        return x + y

    ctx = build_default_context()
    module_ast = ModuleAST([parse_function(add_kernel, _tensor_arg([2, 2]), _tensor_arg([2, 2]))])
    module = module_ast.emit_mlir(ctx, None)

    assert isinstance(module, ModuleOp)
    assert any(isinstance(op, func.FuncOp) for op in module.ops)


def test_mlir_gen_lowers_nn_matmul_public_helper() -> None:
    """TC-MLIR-GEN-AST-003: public matmul helper 下沉为 nn.matmul。"""

    def matmul_kernel(lhs: "Tensor[f32, 2, 3]", rhs: "Tensor[f32, 3, 4]") -> "Tensor[f32, 2, 4]":
        return matmul(lhs, rhs)

    module = mlir_gen(matmul_kernel, _tensor_arg([2, 3]), _tensor_arg([3, 4]))
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))

    matmul_ops = [op for op in func_op.body.block.ops if isinstance(op, NnMatmulOp)]
    assert len(matmul_ops) == 1
    assert matmul_ops[0].result.type.shape.data[0].expr.data == "2"
    assert matmul_ops[0].result.type.shape.data[1].expr.data == "4"


def test_mlir_gen_lowers_nn_activation_reduce_public_helpers() -> None:
    """TC-MLIR-GEN-AST-008: activation / reduce helper 通过公开入口生成 NN op。"""

    module = mlir_gen(public_nn_activation_reduce_kernel, Memory([2, 3], NumericType.Float32))
    module_text = str(module)

    for op_name in (
        "nn.relu",
        "nn.sigmoid",
        "nn.tanh",
        "nn.exp",
        "nn.leaky_relu",
        "nn.hard_sigmoid",
        "nn.reduce_sum",
        "nn.reduce_min",
        "nn.reduce_max",
        "nn.softmax",
    ):
        assert op_name in module_text


def test_mlir_gen_lowers_nn_arithmetic_compare_public_helpers() -> None:
    """TC-MLIR-GEN-AST-009: arithmetic / compare helper 通过公开入口生成 NN op。"""

    module = mlir_gen(
        public_nn_arithmetic_compare_kernel,
        Memory([2, 3], NumericType.Float32),
        Memory([2, 3], NumericType.Float32),
        SymbolDim("SCALAR"),
    )
    module_text = str(module)

    for op_name in (
        "nn.add",
        "nn.sub",
        "nn.mul",
        "nn.truediv",
        "nn.floordiv",
        "nn.eq",
        "nn.ne",
        "nn.lt",
        "nn.le",
        "nn.gt",
        "nn.ge",
    ):
        assert op_name in module_text


def test_mlir_gen_lowers_nn_broadcast_and_structured_public_helpers() -> None:
    """TC-MLIR-GEN-AST-010: broadcast 与 structured helper 通过公开入口生成稳定 op 链。"""

    broadcast_module = mlir_gen(
        public_nn_broadcast_kernel,
        Memory([1, 3], NumericType.Float32),
        Memory([2, 3], NumericType.Float32),
        SymbolDim("M"),
    )
    structured_module = mlir_gen(
        public_nn_structured_kernel,
        Memory([2, 3], NumericType.Float32),
        Memory([3, 4], NumericType.Float32),
        Memory([5, 3], NumericType.Float32),
        Memory([1, 3, 8], NumericType.Float32),
        Memory([1, 3, 8, 8], NumericType.Float32),
        Memory([1, 3, 8, 8], NumericType.Float32),
        Memory([4, 3, 3, 3], NumericType.Float32),
    )
    module_text = f"{broadcast_module}\n{structured_module}"

    assert module_text.count("nn.broadcast") >= 2
    assert "nn.transpose" in module_text
    assert module_text.count("nn.matmul") >= 3
    assert "nn.img2col1d" in module_text
    assert "nn.img2col2d" in module_text
    assert module_text.count("dma.reshape") >= 3


def test_mlir_gen_lowers_dma_and_arch_public_helper_chains() -> None:
    """TC-MLIR-GEN-AST-011: DMA 与 arch helper 链通过公开入口生成对应 dialect op。"""

    dma_module = mlir_gen(
        public_dma_helper_chain_kernel,
        Memory([8, 4], NumericType.Float32),
        Memory([8, 4], NumericType.Float32),
        SymbolDim("N"),
    )
    arch_module = mlir_gen(public_arch_helper_kernel, Memory([4], NumericType.Float32))
    module_text = f"{dma_module}\n{arch_module}"

    for op_name in (
        "dma.alloc",
        "dma.fill",
        "dma.copy",
        "dma.slice",
        "dma.view",
        "dma.reshape",
        "dma.cast",
        "dma.store",
        "dma.deslice",
        "arch.get_block_id",
        "arch.get_block_num",
        "arch.get_thread_id",
        "arch.get_thread_num",
        "arch.get_subthread_id",
        "arch.get_subthread_num",
        "arch.get_dynamic_memory",
        "arch.launch",
    ):
        assert op_name in module_text


def test_mlir_gen_lowers_kernel_out_first_public_helpers() -> None:
    """TC-DSL-AST-MLIR-GEN-047: kernel out-first helper 下沉为 kernel dialect op。"""

    module = mlir_gen(
        public_kernel_out_first_helper_kernel,
        Memory([2, 4], NumericType.Float32),
        Memory([2, 4], NumericType.Float32),
        Memory([2, 4], NumericType.Float32),
        Memory([2, 4], NumericType.Float32),
        Memory([2, 3], NumericType.Float32, space=MemorySpace.TLM1),
        Memory([3, 4], NumericType.Float32, space=MemorySpace.TLM2),
        Memory([1, 2, "KERNEL_W", "9 - KERNEL_W"], NumericType.Float32),
        Memory([1, 2, 8], NumericType.Float32),
        Memory([1, 2, "KH", "KW", "11 - KH", "11 - KW"], NumericType.Float32),
        Memory([1, 2, 8, 8], NumericType.Float32),
        SymbolDim("KERNEL_W"),
        SymbolDim("KH"),
        SymbolDim("KW"),
    )
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    ops = list(func_op.body.block.ops)
    module_text = str(module)

    assert sum(isinstance(op, KernelBinaryElewiseOp) for op in ops) == 2
    assert any(isinstance(op, KernelMatmulOp) for op in ops)
    assert any(isinstance(op, KernelImg2col1dOp) for op in ops)
    assert any(isinstance(op, KernelImg2col2dOp) for op in ops)
    assert '"kernel.binary_elewise"' in module_text
    assert '"kernel.add"' not in module_text


def test_mlir_gen_lowers_memory_get_shape_unpack_and_index() -> None:
    """TC-DSL-AST-MLIR-GEN-048: Memory.get_shape 解包与索引 lower 为 shape 读取。"""

    module = mlir_gen(
        public_memory_get_shape_direct_kernel,
        Memory(["M", "N"], NumericType.Float32),
        Memory(["M", "N"], NumericType.Float32),
    )
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    ops = list(func_op.body.block.ops)
    module_text = str(module)

    assert sum(isinstance(op, SymbolGetDimOp) for op in ops) >= 2
    assert '"dma.slice"' in module_text
    assert '"dma.deslice"' in module_text
    assert "get_shape(" not in module_text


def test_mlir_gen_reuses_bound_memory_expr_with_symbol_axis_arithmetic() -> None:
    """TC-MLIR-GEN-AST-003A: memory 表达式赋值后复用 SSA，不重复展开右侧计算。"""

    def conv_like_kernel(
        out: "Tensor[f32, 1, 4, 14, 14]",
        input_tensor: "Tensor[f32, 1, 32, 16, 16]",
        weight: "Tensor[f32, 4, 32, 3, 3]",
    ) -> None:
        h_size = input_tensor.shape.get_shape()[2]
        kh_size = weight.shape.get_shape()[2]
        ho_size = h_size - kh_size + 1
        input_h_tile = (ho_size - 1) + kh_size
        input_tile = slice(
            input_tensor,
            [0, 0, 0, 0],
            [1, 32, input_h_tile, input_h_tile],
            [1, 1, 1, 1],
            MemorySpace.TSM,
        )
        weight_tile = slice(
            weight,
            [0, 0, 0, 0],
            [4, 32, kh_size, kh_size],
            [1, 1, 1, 1],
            MemorySpace.TSM,
        )
        col = img2col2d(input_tile, kh=kh_size, kw=kh_size)
        col2 = reshape(col, [288, ho_size * ho_size])
        weight2 = reshape(weight_tile, [4, 288])
        out2 = matmul(weight2, col2)
        out_tile = reshape(out2, [1, 4, ho_size, ho_size])
        deslice(out, out_tile, [0, 0, 0, 0], [1, 4, ho_size, ho_size], [1, 1, 1, 1])

    module = mlir_gen(
        conv_like_kernel,
        _tensor_arg([1, 4, 14, 14]),
        _tensor_arg([1, 32, 16, 16]),
        _tensor_arg([4, 32, 3, 3]),
    )
    module_text = str(module)

    assert module_text.count('"nn.img2col2d"') == 1
    assert module_text.count('"nn.matmul"') == 1
    assert module_text.count('"dma.slice"') == 2


def test_parse_function_public_error_path_stays_ast_parse_error() -> None:
    """TC-MLIR-GEN-AST-004: parse_function 公开错误路径保持 KernelCodeError。"""

    def bad(x):
        return x

    with pytest.raises(KernelCodeError):
        parse_function(bad)


def test_mlir_gen_lowers_symbolic_loop_and_dma_chain() -> None:
    """TC-MLIR-GEN-AST-005: symbol loop 与 DMA helper 链通过公开入口生成。"""

    source = Memory(["M", "N"], NumericType.Float32)
    target = Memory(["M", "N"], NumericType.Float32)
    tile = SymbolDim("TILE")

    def tiled_add(x: Memory, out: Memory, step: SymbolDim) -> None:
        rows, cols = x.shape.get_shape()
        scratch = alloc([step, cols], x.dtype, MemorySpace.TSM)
        for row in loop(0, rows, step):
            tile_x = slice(x, [row, 0], [step, cols], [1, 1], MemorySpace.TSM)
            tile_out = add(tile_x, scratch)
            reshaped = reshape(tile_out, [step, cols])
            deslice(out, reshaped, [row, 0], [step, cols], [1, 1])

    module = mlir_gen(tiled_add, source, target, tile)
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    ops = list(func_op.body.block.ops)
    module_text = str(module)

    assert any(isinstance(op, SymbolGetDimOp) for op in ops)
    assert any(isinstance(op, DmaAllocOp) for op in ops)
    assert "symbol.for" in module_text
    assert '"dma.slice"' in module_text
    assert '"nn.add"' in module_text
    assert '"dma.reshape"' in module_text
    assert '"dma.deslice"' in module_text
    assert SymbolForOp.__name__
    assert DmaSliceOp.__name__
    assert DmaReshapeOp.__name__
    assert DmaDesliceOp.__name__


def test_mlir_gen_normalizes_softmax_default_axis_to_last_dimension() -> None:
    """TC-MLIR-GEN-AST-006: softmax 默认 axis 归一到最后一维。"""

    source = Memory([2, 3], NumericType.Float32, space=MemorySpace.GM)

    def softmax_kernel(src: "Tensor[f32, 2, 3]") -> "Tensor[f32, 2, 3]":
        return softmax(src)

    module = mlir_gen(softmax_kernel, source)
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    softmax_ops = [op for op in func_op.body.block.ops if isinstance(op, NnSoftmaxOp)]
    return_ops = [op for op in func_op.body.block.ops if isinstance(op, func.ReturnOp)]

    assert len(softmax_ops) == 1
    assert len(return_ops) == 1
    assert softmax_ops[0].axis.value.data == 1
    assert return_ops[0].arguments[0].type == softmax_ops[0].result.type


def test_mlir_gen_normalizes_softmax_negative_axis_to_positive_axis() -> None:
    """TC-MLIR-GEN-AST-007: softmax 负 axis 归一为正 axis。"""

    source = Memory([2, 3, 4], NumericType.Float32, space=MemorySpace.GM)

    def softmax_kernel(src: "Tensor[f32, 2, 3, 4]") -> "Tensor[f32, 2, 3, 4]":
        return softmax(src, axis=-1)

    module = mlir_gen(softmax_kernel, source)
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    softmax_ops = [op for op in func_op.body.block.ops if isinstance(op, NnSoftmaxOp)]

    assert len(softmax_ops) == 1
    assert softmax_ops[0].axis.value.data == 2
