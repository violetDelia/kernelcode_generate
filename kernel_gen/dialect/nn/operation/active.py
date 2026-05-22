"""nn active and unary operations.

功能说明:
- 承载 nn dialect package 拆分后的 nn active and unary operations 实现。

API 列表:
- `class NnReluOp(input_value: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnSigmoidOp(input_value: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnTanhOp(input_value: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnLeakyReluOp(input_value: SSAValue, alpha: SSAValue | None, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnHardSigmoidOp(input_value: SSAValue, alpha: SSAValue | None, beta: SSAValue | None, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnSoftmaxOp(input_value: SSAValue, result_type: NnMemoryType, axis: int | IntegerAttr, space: NnMemorySpaceAttr)`
- `class NnExpOp(input_value: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`

使用示例:
- from kernel_gen.dialect.nn import NnReluOp

关联文件:
- spec: spec/dialect/nn.md
- test: test/dialect/nn/test_operation_active.py
- 功能实现: kernel_gen/dialect/nn/operation/active.py
"""

from __future__ import annotations

from kernel_gen.dialect.nn.attr.space_attr import NnMemorySpaceAttr
from kernel_gen.dialect.nn.common import (
    is_float_element_type,
    is_symbol_int_type,
    normalize_i64_attr,
    raise_verify_error,
    verify_i64_attr,
    verify_memory_type,
)
from kernel_gen.dialect.nn.type.memory_type import NnMemoryType
from xdsl.dialects.builtin import BFloat16Type, Float16Type, Float32Type, Float64Type, IntAttr, IntegerAttr, IntegerType
from xdsl.ir import Attribute, Operation, SSAValue
from xdsl.irdl import IRDLOperation, SameVariadicOperandSize, attr_def, irdl_op_definition, operand_def, opt_operand_def, result_def

def _verify_exp_op(op: "NnExpOp") -> None:
    """校验 nn.exp 的结构化合同。


    功能说明:
    - 校验 operand/result 必须是 nn.memory 且输入为浮点类型。
    - 校验 shape/stride/element_type/space 一致性。

    使用示例:
    - _verify_exp_op(op)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    input_type = op.input.type
    result_type = op.result.type
    if not isinstance(input_type, NnMemoryType) or not isinstance(result_type, NnMemoryType):
        raise_verify_error("operand-must-be-nn-memory")
    input_type.verify()
    result_type.verify()

    if not is_float_element_type(input_type.element_type):
        raise_verify_error("operand-element-type-must-be-float")

    if input_type.shape != result_type.shape or input_type.stride != result_type.stride:
        raise_verify_error("result-shape-stride-must-match-input")

    if input_type.element_type != result_type.element_type:
        raise_verify_error("result-element-type-must-match-input")

    op.space.verify()
    if input_type.space.space.data != result_type.space.space.data:
        raise_verify_error("result-space-must-match-input-and-attr")
    if input_type.space.space.data != op.space.space.data:
        raise_verify_error("result-space-must-match-input-and-attr")

def _verify_unary_float_op(
    input_type: NnMemoryType,
    result_type: NnMemoryType,
    space: NnMemorySpaceAttr,
) -> None:
    """校验逐元素浮点 unary op 的公共合同。


    功能说明:
    - 统一校验 `relu/sigmoid/tanh/exp` 这类浮点 unary op 的输入、输出与 memory space 约束。
    - 作为 `NnReluOp`、`NnSigmoidOp`、`NnTanhOp`、`NnExpOp` verifier 共享的底层 helper。

    使用示例:
    - _verify_unary_float_op(input_type, result_type, op.space)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    input_type.verify()
    result_type.verify()

    if not is_float_element_type(input_type.element_type):
        raise_verify_error("operand-element-type-must-be-float")

    if input_type.shape != result_type.shape or input_type.stride != result_type.stride:
        raise_verify_error("result-shape-stride-must-match-input")

    if input_type.element_type != result_type.element_type:
        raise_verify_error("result-element-type-must-match-input")

    space.verify()
    if input_type.space.space.data != result_type.space.space.data:
        raise_verify_error("result-space-must-match-input-and-attr")
    if input_type.space.space.data != space.space.data:
        raise_verify_error("result-space-must-match-input-and-attr")

def _verify_activation_scalar_operand(value: SSAValue, field_name: str) -> None:
    """校验激活函数额外标量参数类型。


    功能说明:
    - 校验 `leaky_relu` / `hard_sigmoid` 的附加标量参数只能是整数或浮点标量。
    - 明确拒绝 `nn.memory` 与 `symbol.int` 作为激活系数输入，避免 verifier 接受未公开的参数形态。

    使用示例:
    - _verify_activation_scalar_operand(op.alpha, "alpha")

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    attr = value.type
    if isinstance(attr, NnMemoryType) or is_symbol_int_type(attr):
        raise_verify_error(f"{field_name} must be int or float scalar")
    if not isinstance(attr, (IntegerType, Float16Type, BFloat16Type, Float32Type, Float64Type)):
        raise_verify_error(f"{field_name} must be int or float scalar")

def _verify_softmax_op(op: "NnSoftmaxOp") -> None:
    """校验 nn.softmax 的结构化合同。


    功能说明:
    - 校验 operand/result 必须是 nn.memory，且 rank/axis 合法。
    - 校验 shape/stride/element_type/space 与 op 属性一致性。

    使用示例:
    - _verify_softmax_op(op)

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    input_type = op.input.type
    result_type = op.result.type
    if not isinstance(input_type, NnMemoryType) or not isinstance(result_type, NnMemoryType):
        raise_verify_error("operand-and-result-must-be-nn-memory")
    input_type.verify()
    result_type.verify()

    rank = len(input_type.shape.data)
    if rank <= 0:
        raise_verify_error("input-rank-must-be-positive")
    axis_value = verify_i64_attr(op.axis, "axis")
    if axis_value < -rank or axis_value >= rank:
        raise_verify_error("axis-must-be-in-range")

    op.space.verify()
    if input_type.space.space.data != result_type.space.space.data:
        raise_verify_error("result-space-must-match-input-and-attr")
    if input_type.space.space.data != op.space.space.data:
        raise_verify_error("result-space-must-match-input-and-attr")

    if input_type.shape != result_type.shape:
        raise_verify_error("result-shape-must-match-input")
    if input_type.stride != result_type.stride:
        raise_verify_error("result-stride-must-match-input")

    if input_type.element_type != result_type.element_type or not is_float_element_type(input_type.element_type):
        raise_verify_error("result-element-type-must-match-input-and-be-float")

@irdl_op_definition
class NnSoftmaxOp(IRDLOperation):
    """nn.softmax。


    功能说明:
    - 定义 nn.softmax 方言 op 与 verifier 约束。

    使用示例:
    - NnSoftmaxOp(inp, result_type, axis=-1, space=NnMemorySpaceAttr.from_name("global"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    name = "nn.softmax"

    input = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)
    axis = attr_def(IntegerAttr)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        input_value: SSAValue | Operation,
        result_type: NnMemoryType,
        axis: int | IntegerAttr | IntAttr,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 softmax op。


        功能说明:
        - 绑定输入、结果类型、axis 与 space 属性。
        - axis 会规整为 i64 IntegerAttr 以便 verifier 校验。

        使用示例:
        - NnSoftmaxOp(inp, result_type, axis=-1, space=NnMemorySpaceAttr.from_name("global"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """
        axis_attr = normalize_i64_attr(axis, "axis")
        super().__init__(
            operands=[input_value],
            result_types=[result_type],
            attributes={"axis": axis_attr, "space": space},
        )

    def verify_(self) -> None:
        """校验 nn.softmax 的 verifier 合同。


        功能说明:
        - 调用统一的 softmax 合同校验逻辑。

        使用示例:
        - NnSoftmaxOp(inp, result_type, axis=-1, space=NnMemorySpaceAttr.from_name("global")).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """
        _verify_softmax_op(self)

@irdl_op_definition
class NnReluOp(IRDLOperation):
    """nn.relu。"""

    name = "nn.relu"

    input = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(self, input_value: SSAValue | Operation, result_type: NnMemoryType, space: NnMemorySpaceAttr) -> None:
        """初始化 nn.relu op。

        功能说明:
        - 绑定输入 memory、结果 memory type 和执行 space 属性。
        - 构造阶段不执行 verifier，保持 xDSL op 构造语义。

        使用示例:
        - NnReluOp(inp, result_type, NnMemorySpaceAttr.from_name("global"))
        """
        super().__init__(operands=[input_value], result_types=[result_type], attributes={"space": space})

    def verify_(self) -> None:
        """校验 nn.relu 的 memory 与 dtype 合同。

        功能说明:
        - 校验 input/result 均为 `NnMemoryType`。
        - 校验 shape/stride/space/element_type 满足 unary float op 约束。

        使用示例:
        - NnReluOp(inp, result_type, space).verify_()
        """
        input_type = verify_memory_type(self.input.type, "input")
        result_type = verify_memory_type(self.result.type, "result")
        _verify_unary_float_op(input_type, result_type, self.space)

@irdl_op_definition
class NnSigmoidOp(IRDLOperation):
    """nn.sigmoid。"""

    name = "nn.sigmoid"

    input = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(self, input_value: SSAValue | Operation, result_type: NnMemoryType, space: NnMemorySpaceAttr) -> None:
        """初始化 nn.sigmoid op。

        功能说明:
        - 绑定输入 memory、结果 memory type 和执行 space 属性。
        - 构造阶段只描述 IR operands/results，不改变 verifier 合同。

        使用示例:
        - NnSigmoidOp(inp, result_type, NnMemorySpaceAttr.from_name("global"))
        """
        super().__init__(operands=[input_value], result_types=[result_type], attributes={"space": space})

    def verify_(self) -> None:
        """校验 nn.sigmoid 的 memory 与 dtype 合同。

        功能说明:
        - 校验 input/result 均为 `NnMemoryType`。
        - 校验 shape/stride/space/element_type 满足 unary float op 约束。

        使用示例:
        - NnSigmoidOp(inp, result_type, space).verify_()
        """
        input_type = verify_memory_type(self.input.type, "input")
        result_type = verify_memory_type(self.result.type, "result")
        _verify_unary_float_op(input_type, result_type, self.space)

@irdl_op_definition
class NnTanhOp(IRDLOperation):
    """nn.tanh。"""

    name = "nn.tanh"

    input = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(self, input_value: SSAValue | Operation, result_type: NnMemoryType, space: NnMemorySpaceAttr) -> None:
        """初始化 nn.tanh op。

        功能说明:
        - 绑定输入 memory、结果 memory type 和执行 space 属性。
        - 保持与 relu/sigmoid 相同的 unary activation 构造边界。

        使用示例:
        - NnTanhOp(inp, result_type, NnMemorySpaceAttr.from_name("global"))
        """
        super().__init__(operands=[input_value], result_types=[result_type], attributes={"space": space})

    def verify_(self) -> None:
        """校验 nn.tanh 的 memory 与 dtype 合同。

        功能说明:
        - 校验 input/result 均为 `NnMemoryType`。
        - 校验 shape/stride/space/element_type 满足 unary float op 约束。

        使用示例:
        - NnTanhOp(inp, result_type, space).verify_()
        """
        input_type = verify_memory_type(self.input.type, "input")
        result_type = verify_memory_type(self.result.type, "result")
        _verify_unary_float_op(input_type, result_type, self.space)

@irdl_op_definition
class NnLeakyReluOp(IRDLOperation):
    """nn.leaky_relu。"""

    name = "nn.leaky_relu"

    input = operand_def(NnMemoryType)
    alpha = opt_operand_def(Attribute)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        input_value: SSAValue | Operation,
        alpha: SSAValue | Operation | None,
        result_type: NnMemoryType,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 nn.leaky_relu op。

        功能说明:
        - 绑定输入 memory、可选 alpha 标量、结果 memory type 和执行 space 属性。
        - `alpha is None` 时写入空 optional operand segment，保持 IR segment 合同。

        使用示例:
        - NnLeakyReluOp(inp, alpha, result_type, NnMemorySpaceAttr.from_name("global"))
        """
        super().__init__(
            operands=[input_value, [] if alpha is None else [alpha]],
            result_types=[result_type],
            attributes={"space": space},
        )

    def verify_(self) -> None:
        """校验 nn.leaky_relu 的 memory、dtype 与 alpha 合同。

        功能说明:
        - 校验 input/result 满足 unary float op 的 shape/stride/space/element_type 约束。
        - 当 alpha 存在时，校验其为允许的 activation scalar operand。

        使用示例:
        - NnLeakyReluOp(inp, alpha, result_type, space).verify_()
        """
        input_type = verify_memory_type(self.input.type, "input")
        result_type = verify_memory_type(self.result.type, "result")
        _verify_unary_float_op(input_type, result_type, self.space)
        if self.alpha is not None:
            _verify_activation_scalar_operand(SSAValue.get(self.alpha), "alpha")

@irdl_op_definition
class NnHardSigmoidOp(IRDLOperation):
    """nn.hard_sigmoid。"""

    name = "nn.hard_sigmoid"
    irdl_options = (SameVariadicOperandSize(),)

    input = operand_def(NnMemoryType)
    alpha = opt_operand_def(Attribute)
    beta = opt_operand_def(Attribute)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        input_value: SSAValue | Operation,
        alpha: SSAValue | Operation | None,
        beta: SSAValue | Operation | None,
        result_type: NnMemoryType,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 nn.hard_sigmoid op。

        功能说明:
        - 绑定输入 memory、可选 alpha/beta 标量、结果 memory type 和执行 space 属性。
        - 可选标量使用 SameVariadicOperandSize 约束保持 operand segment 一致。

        使用示例:
        - NnHardSigmoidOp(inp, alpha, beta, result_type, NnMemorySpaceAttr.from_name("global"))
        """
        super().__init__(
            operands=[
                input_value,
                [] if alpha is None else [alpha],
                [] if beta is None else [beta],
            ],
            result_types=[result_type],
            attributes={"space": space},
        )

    def verify_(self) -> None:
        """校验 nn.hard_sigmoid 的 memory、dtype 与 scalar 合同。

        功能说明:
        - 校验 input/result 满足 unary float op 的 shape/stride/space/element_type 约束。
        - 当 alpha 或 beta 存在时，分别校验其为允许的 activation scalar operand。

        使用示例:
        - NnHardSigmoidOp(inp, alpha, beta, result_type, space).verify_()
        """
        input_type = verify_memory_type(self.input.type, "input")
        result_type = verify_memory_type(self.result.type, "result")
        _verify_unary_float_op(input_type, result_type, self.space)
        if self.alpha is not None:
            _verify_activation_scalar_operand(SSAValue.get(self.alpha), "alpha")
        if self.beta is not None:
            _verify_activation_scalar_operand(SSAValue.get(self.beta), "beta")

@irdl_op_definition
class NnExpOp(IRDLOperation):
    """nn.exp。


    功能说明:
    - 定义 nn.exp 方言 op 与 verifier 约束。

    使用示例:
    - NnExpOp(inp, result_type, NnMemorySpaceAttr.from_name("global"))

    关联文件:
    - spec: spec/dialect/nn.md
    - test: test/dialect/nn/
    - 功能实现: kernel_gen/dialect/nn/
    """

    name = "nn.exp"

    input = operand_def(NnMemoryType)
    result = result_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        input_value: SSAValue | Operation,
        result_type: NnMemoryType,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 exp op。


        功能说明:
        - 绑定输入、结果类型与 space 属性。

        使用示例:
        - NnExpOp(inp, result_type, NnMemorySpaceAttr.from_name("global"))

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """

        super().__init__(
            operands=[input_value],
            result_types=[result_type],
            attributes={"space": space},
        )

    def verify_(self) -> None:
        """校验 nn.exp verifier 合同。


        功能说明:
        - 调用统一的 nn.exp 合同校验逻辑。

        使用示例:
        - NnExpOp(inp, result_type, NnMemorySpaceAttr.from_name("global")).verify_()

        关联文件:
        - spec: spec/dialect/nn.md
        - test: test/dialect/nn/
        - 功能实现: kernel_gen/dialect/nn/
        """
        _verify_exp_op(self)

__all__ = ["NnReluOp", "NnSigmoidOp", "NnTanhOp", "NnLeakyReluOp", "NnHardSigmoidOp", "NnSoftmaxOp", "NnExpOp"]
