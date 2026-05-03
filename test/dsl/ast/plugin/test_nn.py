"""DSL AST NN plugin tests.


功能说明:
- 覆盖 `kernel_gen.dsl.ast.plugin.nn` 注册后的 NN helper 解析行为。
- 测试结构对应 `spec/dsl/ast/plugin/nn.md` 与 `kernel_gen/dsl/ast/plugin/nn.py`。

使用示例:
- pytest -q test/dsl/ast/plugin/test_nn.py

关联文件:
- 功能实现: kernel_gen/dsl/ast/plugin/nn.py
- Spec 文档: spec/dsl/ast/plugin/nn.md
- 测试文件: test/dsl/ast/plugin/test_nn.py
"""

from __future__ import annotations

import random

import pytest

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dsl.ast import (
    ConvAST,
    FCAST,
    MatmulAST,
    NnAddAST,
    NnBroadcastAST,
    NnBroadcastToAST,
    NnEqAST,
    NnExpAST,
    NnGeAST,
    NnGtAST,
    NnHardSigmoidAST,
    NnImg2Col1dAST,
    NnImg2Col2dAST,
    NnLeAST,
    NnLeakyReluAST,
    NnLtAST,
    NnMulAST,
    NnNeAST,
    NnReduceMaxAST,
    NnReduceMinAST,
    NnReduceSumAST,
    NnReluAST,
    NnSigmoidAST,
    NnSoftmaxAST,
    NnSubAST,
    NnTanhAST,
    NnTransposeAST,
    NnTrueDivAST,
    ReturnAST,
    parse_function,
)
from kernel_gen.operation.nn import (
    add,
    broadcast,
    broadcast_to,
    conv,
    eq,
    exp,
    fc,
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
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.symbol_variable.type import NumericType


def _nn_relu_kernel(x, y):
    return relu(x)


def _nn_sigmoid_kernel(x, y):
    return sigmoid(x)


def _nn_tanh_kernel(x, y):
    return tanh(x)


def _nn_exp_kernel(x, y):
    return exp(x)


def _nn_leaky_relu_kernel(x, y):
    return leaky_relu(x, alpha=0.125)


def _nn_hard_sigmoid_kernel(x, y):
    return hard_sigmoid(x, 0.2, 0.5)


def _nn_add_kernel(x, y):
    return add(x, y)


def _nn_sub_kernel(x, y):
    return sub(x, y)


def _nn_mul_kernel(x, y):
    return mul(x, y)


def _nn_truediv_kernel(x, y):
    return truediv(x, y)


def _nn_eq_kernel(x, y):
    return eq(x, y)


def _nn_ne_kernel(x, y):
    return ne(x, y)


def _nn_lt_kernel(x, y):
    return lt(x, y)


def _nn_le_kernel(x, y):
    return le(x, y)


def _nn_gt_kernel(x, y):
    return gt(x, y)


def _nn_ge_kernel(x, y):
    return ge(x, y)


def _nn_reduce_sum_kernel(x, y):
    return reduce_sum(x, axis=1, keepdim=True)


def _nn_reduce_min_kernel(x, y):
    return reduce_min(x, 0, False)


def _nn_reduce_max_kernel(x, y):
    return reduce_max(x, axis=[0, 1], keepdim=False)


def _nn_softmax_kernel(x, y):
    return softmax(x, axis=1)


def _nn_broadcast_kernel(x, y):
    return broadcast(x, y)


def _nn_broadcast_to_kernel(x, y):
    return broadcast_to(x, [4, 3], MemorySpace.SM)


def _nn_transpose_kernel(x, y):
    return transpose(x, [1, 0])


def _nn_matmul_kernel(x, y):
    return matmul(x, y, memoryspace=MemorySpace.LM)


def _nn_fc_kernel(x, y):
    return fc(x, y)


def _nn_conv_kernel(x, y):
    return conv(x, y, sh=2, sw=1, ph=1, pw=1)


def _nn_img2col1d_kernel(x, y):
    return img2col1d(x, kw=3, sw=1, dw=1, pl=1, pr=1)


def _nn_img2col2d_kernel(x, y):
    return img2col2d(x, kh=3, kw=3, sh=1, sw=1, dh=1, dw=1, ph=1, pw=1, pl=1, pr=1)


def _nn_bad_arithmetic_kernel(x, y):
    return add(x)


def _nn_bad_sub_kernel(x, y):
    return sub(x)


def _nn_bad_mul_kernel(x, y):
    return mul(x)


def _nn_bad_truediv_kernel(x, y):
    return truediv(x)


def _nn_bad_eq_kernel(x, y):
    return eq(x)


def _nn_bad_ne_kernel(x, y):
    return ne(x)


def _nn_bad_lt_kernel(x, y):
    return lt(x)


def _nn_bad_le_kernel(x, y):
    return le(x)


def _nn_bad_gt_kernel(x, y):
    return gt(x)


def _nn_bad_ge_kernel(x, y):
    return ge(x)


def _nn_bad_unary_kernel(x, y):
    return relu(x, y)


def _nn_bad_sigmoid_kernel(x, y):
    return sigmoid(x, y)


def _nn_bad_tanh_kernel(x, y):
    return tanh(x, y)


def _nn_bad_exp_kernel(x, y):
    return exp(x, y)


def _nn_bad_leaky_relu_kernel(x, y):
    return leaky_relu(x)


def _nn_bad_hard_sigmoid_kernel(x, y):
    return hard_sigmoid(x, alpha=0.2)


def _nn_bad_reduce_sum_kernel(x, y):
    return reduce_sum(x, axis=1, keepdim=True, mode="bad")


def _nn_bad_reduce_min_kernel(x, y):
    return reduce_min()


def _nn_bad_reduce_max_kernel(x, y):
    return reduce_max(x, 0, False, "bad")


def _nn_bad_softmax_kernel(x, y):
    return softmax(x, axis=1, mode="bad")


def _nn_bad_broadcast_to_arity_kernel(x, y):
    return broadcast_to(x)


def _nn_bad_broadcast_space_kernel(x, y):
    return broadcast_to(x, [4, 3], "SM")


def _nn_bad_transpose_kernel(x, y):
    return transpose(x)


def _nn_bad_transpose_duplicate_perm_kernel(x, y):
    return transpose(x, [1, 0], perm=[0, 1])


def _nn_bad_matmul_arity_kernel(x, y):
    return matmul(x)


def _nn_bad_matmul_space_kernel(x, y):
    return matmul(x, y, memoryspace="SM")


def _nn_bad_conv_arity_kernel(x, y):
    return conv(x, y, groups=1)


def _nn_bad_img2col1d_arity_kernel(x, y):
    return img2col1d()


def _nn_bad_img2col2d_arity_kernel(x, y):
    return img2col2d()


_NN_INVALID_CASES = tuple(
    random.Random(20260505).sample(
        [
            (_nn_bad_arithmetic_kernel, "Unsupported nn arithmetic arity"),
            (_nn_bad_sub_kernel, "Unsupported nn arithmetic arity"),
            (_nn_bad_mul_kernel, "Unsupported nn arithmetic arity"),
            (_nn_bad_truediv_kernel, "Unsupported nn arithmetic arity"),
            (_nn_bad_eq_kernel, "Unsupported nn arithmetic arity"),
            (_nn_bad_ne_kernel, "Unsupported nn arithmetic arity"),
            (_nn_bad_lt_kernel, "Unsupported nn arithmetic arity"),
            (_nn_bad_le_kernel, "Unsupported nn arithmetic arity"),
            (_nn_bad_gt_kernel, "Unsupported nn arithmetic arity"),
            (_nn_bad_ge_kernel, "Unsupported nn arithmetic arity"),
            (_nn_bad_unary_kernel, "Unsupported relu arity"),
            (_nn_bad_sigmoid_kernel, "Unsupported sigmoid arity"),
            (_nn_bad_tanh_kernel, "Unsupported tanh arity"),
            (_nn_bad_exp_kernel, "Unsupported exp arity"),
            (_nn_bad_leaky_relu_kernel, "Unsupported leaky_relu arity"),
            (_nn_bad_hard_sigmoid_kernel, "Unsupported hard_sigmoid arity"),
            (_nn_bad_reduce_sum_kernel, "Unsupported reduce_sum arity"),
            (_nn_bad_reduce_min_kernel, "Unsupported reduce_min arity"),
            (_nn_bad_reduce_max_kernel, "Unsupported reduce_max arity"),
            (_nn_bad_softmax_kernel, "Unsupported softmax arity"),
            (_nn_bad_broadcast_to_arity_kernel, "Unsupported broadcast_to arity"),
            (_nn_bad_broadcast_space_kernel, "broadcast_to space must be MemorySpace"),
            (_nn_bad_transpose_kernel, "transpose perm is required"),
            (_nn_bad_transpose_duplicate_perm_kernel, "Unsupported transpose arity"),
            (_nn_bad_matmul_arity_kernel, "Unsupported matmul arity"),
            (_nn_bad_matmul_space_kernel, "matmul memoryspace must be MemorySpace"),
            (_nn_bad_conv_arity_kernel, "Unsupported conv arity"),
            (_nn_bad_img2col1d_arity_kernel, "Unsupported img2col1d arity"),
            (_nn_bad_img2col2d_arity_kernel, "Unsupported img2col2d arity"),
        ],
        29,
    )
)


_NN_RETURN_CASES = tuple(
    random.Random(20260503).sample(
        [
            (_nn_relu_kernel, NnReluAST),
            (_nn_sigmoid_kernel, NnSigmoidAST),
            (_nn_tanh_kernel, NnTanhAST),
            (_nn_exp_kernel, NnExpAST),
            (_nn_leaky_relu_kernel, NnLeakyReluAST),
            (_nn_hard_sigmoid_kernel, NnHardSigmoidAST),
            (_nn_add_kernel, NnAddAST),
            (_nn_sub_kernel, NnSubAST),
            (_nn_mul_kernel, NnMulAST),
            (_nn_truediv_kernel, NnTrueDivAST),
            (_nn_eq_kernel, NnEqAST),
            (_nn_ne_kernel, NnNeAST),
            (_nn_lt_kernel, NnLtAST),
            (_nn_le_kernel, NnLeAST),
            (_nn_gt_kernel, NnGtAST),
            (_nn_ge_kernel, NnGeAST),
            (_nn_reduce_sum_kernel, NnReduceSumAST),
            (_nn_reduce_min_kernel, NnReduceMinAST),
            (_nn_reduce_max_kernel, NnReduceMaxAST),
            (_nn_softmax_kernel, NnSoftmaxAST),
            (_nn_broadcast_kernel, NnBroadcastAST),
            (_nn_broadcast_to_kernel, NnBroadcastToAST),
            (_nn_transpose_kernel, NnTransposeAST),
            (_nn_matmul_kernel, MatmulAST),
            (_nn_fc_kernel, FCAST),
            (_nn_conv_kernel, ConvAST),
            (_nn_img2col1d_kernel, NnImg2Col1dAST),
            (_nn_img2col2d_kernel, NnImg2Col2dAST),
        ],
        28,
    )
)


def _nn_return_values(kernel):
    """通过公开 parse_function 读取 NN helper 的返回 AST 值。"""

    lhs = Memory([4, 3], NumericType.Float32)
    rhs = Memory([4, 3], NumericType.Float32)
    func_ast = parse_function(kernel, lhs, rhs)
    return_nodes = [node for node in func_ast.body.statements if isinstance(node, ReturnAST)]
    assert len(return_nodes) == 1
    return return_nodes[0].values


def test_nn_helper_call_uses_registered_specific_ast_node() -> None:
    """解析 NN helper 调用入口并生成相应 AST。"""

    memory = Memory([1], NumericType.Float32)

    func_ast = parse_function(_nn_relu_kernel, memory, memory)

    return_nodes = [node for node in func_ast.body.statements if isinstance(node, ReturnAST)]
    assert len(return_nodes) == 1
    assert any(isinstance(value, NnReluAST) for value in return_nodes[0].values)


@pytest.mark.parametrize(("kernel", "expected_type"), _NN_RETURN_CASES)
def test_nn_public_helpers_parse_parameterized_return_nodes(kernel, expected_type: type) -> None:
    """确定性随机遍历 NN 公开 helper，锁定 registry 到具体 AST 的映射。"""

    values = _nn_return_values(kernel)

    assert any(isinstance(value, expected_type) for value in values)


@pytest.mark.parametrize(("kernel", "match"), _NN_INVALID_CASES)
def test_nn_public_helpers_reject_invalid_contracts(kernel, match: str) -> None:
    """NN plugin 对公开 helper 参数矩阵保持稳定 KernelCodeError。"""

    lhs = Memory([4, 3], NumericType.Float32)
    rhs = Memory([4, 3], NumericType.Float32)

    with pytest.raises(KernelCodeError, match=match):
        parse_function(kernel, lhs, rhs)
