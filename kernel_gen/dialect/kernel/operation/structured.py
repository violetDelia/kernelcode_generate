"""kernel structured operations.

功能说明:
- 定义 kernel.matmul、kernel.matmul_fusion、kernel.img2col1d 与 kernel.img2col2d op。

API 列表:
- `class KernelMatmulOp(out: SSAValue | Operation, lhs: SSAValue | Operation, rhs: SSAValue | Operation, space: NnMemorySpaceAttr, *, acc: bool | int | IntegerAttr | IntAttr = False)`
- `class KernelMatmulFusionOp(out: SSAValue | Operation, lhs: SSAValue | Operation, rhs: SSAValue | Operation, acc: SSAValue | Operation, *, space: NnMemorySpaceAttr, fusion_list: str | StringAttr = "")`
- `class KernelImg2col1dOp(...)`
- `class KernelImg2col2dOp(...)`

使用示例:
- `from kernel_gen.dialect.kernel.operation import ...`

关联文件:
- spec: spec/dialect/kernel.md
- test: test/dialect/kernel/
- 功能实现: kernel_gen/dialect/kernel/operation/structured.py
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from kernel_gen.core.contracts import collect_int_dims, build_contiguous_stride, verify_i64_attr_range, verify_memory_type
from kernel_gen.core.error import ERROR_ACTION, ERROR_ACTUAL, ERROR_TEMPLATE, ErrorKind, ErrorModule, KernelCodeError, kernel_code_error
from xdsl.dialects.arith import ConstantOp
from xdsl.dialects.builtin import (
    BFloat16Type,
    Float16Type,
    Float32Type,
    Float64Type,
    IntAttr,
    IntegerAttr,
    IntegerType,
    StringAttr,
    i1,
)
from xdsl.ir import Attribute, Dialect, Operation, SSAValue
from xdsl.irdl import IRDLOperation, attr_def, irdl_op_definition, operand_def, opt_attr_def, traits_def
from xdsl.traits import EffectInstance, MemoryEffect, MemoryEffectKind
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolExprAttr, SymbolValueType

# Localized helpers from retired package-internal modules.

_ERROR_SCENE = "dialect.kernel verifier"

class _KernelBinaryMemoryEffect(MemoryEffect):
    """二元 kernel op 的 out 写与 lhs/rhs 读 effect trait。"""

    @classmethod
    def get_effects(cls, op: Operation) -> set[EffectInstance]:
        """返回二元 kernel op 的 MemoryEffect 集合。


        功能说明:
        - 使用 IRDL 命名字段绑定 effect value，避免构造函数参数顺序变化导致读写误绑。
        - `out` 产生 WRITE effect，`lhs/rhs` 产生 READ effect。

        使用示例:
        - effects = _KernelBinaryMemoryEffect.get_effects(op)

        关联文件:
        - spec: spec/dialect/kernel.md
        - test: test/dialect/kernel/test_kernel.py
        - 功能实现: kernel_gen/dialect/kernel/
        """

        return {
            EffectInstance(MemoryEffectKind.WRITE, SSAValue.get(op.out)),  # type: ignore[attr-defined]
            EffectInstance(MemoryEffectKind.READ, SSAValue.get(op.lhs)),  # type: ignore[attr-defined]
            EffectInstance(MemoryEffectKind.READ, SSAValue.get(op.rhs)),  # type: ignore[attr-defined]
        }


class _KernelMatmulAccRules:
    """kernel.matmul acc 的当前文件规则容器。"""

    @staticmethod
    def error() -> KernelCodeError:
        """构造 kernel.matmul acc 公开错误。

        功能说明:
        - 保持 `kernel.matmul acc must be bool/i1` 稳定错误短语。

        使用示例:
        - raise _KERNEL_MATMUL_ACC.error()
        """

        return kernel_code_error(
            ErrorKind.VERIFY,
            ErrorModule.DIALECT,
            ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected="kernel.matmul acc must be bool/i1",
                actual=ERROR_ACTUAL,
                action=ERROR_ACTION,
            ),
        )

    @staticmethod
    def verify_attr(attr: IntegerAttr | None) -> bool:
        """校验并读取 kernel.matmul acc attr。

        功能说明:
        - 缺失 attr 等价于 `false`。
        - 只接受 i1 IntegerAttr；true 可按 xDSL i1 的 `-1` 或显式 `1` 表达。

        使用示例:
        - enabled = _KERNEL_MATMUL_ACC.verify_attr(op.acc)
        """

        if attr is None:
            return False
        if not isinstance(attr, IntegerAttr) or attr.type != i1:
            raise _KERNEL_MATMUL_ACC.error()
        value = int(attr.value.data)
        if value not in {-1, 0, 1}:
            raise _KERNEL_MATMUL_ACC.error()
        return value != 0

    @staticmethod
    def normalize_attr(value: bool | int | IntegerAttr | IntAttr) -> IntegerAttr | None:
        """规整公开 constructor 的 acc 输入。

        功能说明:
        - `False/0` 规整为缺失 attr，匹配 IR attr missing == false 合同。
        - 显式 `IntegerAttr` 保留原 attr，允许 pass 输出 `acc = false` 稳定文本。
        - `IntAttr(True/False)` 与 `IntAttr(1/0)` 按公开 bool/int 合同接受。

        使用示例:
        - attr = _KERNEL_MATMUL_ACC.normalize_attr(True)
        """

        if isinstance(value, bool):
            return IntegerAttr.from_bool(value) if value else None
        if isinstance(value, int):
            if value not in {0, 1}:
                raise _KERNEL_MATMUL_ACC.error()
            return IntegerAttr.from_bool(bool(value)) if value else None
        if isinstance(value, IntAttr):
            raw = int(value.data)
            if raw not in {-1, 0, 1}:
                raise _KERNEL_MATMUL_ACC.error()
            return IntegerAttr.from_bool(raw != 0) if raw != 0 else None
        if isinstance(value, IntegerAttr):
            _KERNEL_MATMUL_ACC.verify_attr(value)
            return value
        raise _KERNEL_MATMUL_ACC.error()


_KERNEL_MATMUL_ACC = _KernelMatmulAccRules()


def _normalize_matmul_fusion_list_attr(value: str | StringAttr) -> StringAttr | None:
    """规整 kernel.matmul_fusion fusion_list attr。

    功能说明:
    - 公开 constructor 只接受 `str` 或 `StringAttr`。
    - 空字符串等价缺省 attr，保留旧 IR 兼容。
    - 非字符串输入以稳定 `kernel.matmul_fusion fusion_list must be string` 短语失败。

    使用示例:
    - attr = _normalize_matmul_fusion_list_attr("kernel.matmul,kernel.binary_elewise.add")
    """

    message = ERROR_TEMPLATE.format(
        scene=_ERROR_SCENE,
        expected="kernel.matmul_fusion fusion_list must be string",
        actual=ERROR_ACTUAL,
        action=ERROR_ACTION,
    )
    if isinstance(value, str):
        if value == "":
            return None
        return StringAttr(value)
    if isinstance(value, StringAttr):
        if value.data == "":
            return None
        return value
    raise KernelCodeError(
        ErrorKind.VERIFY,
        ErrorModule.DIALECT,
        message,
    )


class _KernelMatmulMemoryEffect(MemoryEffect):
    """kernel.matmul 的 attr-aware MemoryEffect trait。"""

    @classmethod
    def get_effects(cls, op: Operation) -> set[EffectInstance]:
        """返回 kernel.matmul 的 MemoryEffect 集合。

        功能说明:
        - `acc=false` 或缺失 attr 时 out 仅 WRITE，lhs/rhs READ。
        - `acc=true` 时 out 额外 READ，表示累加读取旧值后写回。

        使用示例:
        - effects = _KernelMatmulMemoryEffect.get_effects(op)
        """

        effects = {
            EffectInstance(MemoryEffectKind.WRITE, SSAValue.get(op.out)),  # type: ignore[attr-defined]
            EffectInstance(MemoryEffectKind.READ, SSAValue.get(op.lhs)),  # type: ignore[attr-defined]
            EffectInstance(MemoryEffectKind.READ, SSAValue.get(op.rhs)),  # type: ignore[attr-defined]
        }
        if _KERNEL_MATMUL_ACC.verify_attr(op.acc):  # type: ignore[attr-defined]
            effects.add(EffectInstance(MemoryEffectKind.READ, SSAValue.get(op.out)))  # type: ignore[attr-defined]
        return effects


class _KernelUnaryMemoryEffect(MemoryEffect):
    """一输入一输出 kernel op 的 out 写与 input 读 effect trait。"""

    @classmethod
    def get_effects(cls, op: Operation) -> set[EffectInstance]:
        """返回一输入一输出 kernel op 的 MemoryEffect 集合。


        功能说明:
        - 使用 IRDL 命名字段绑定 effect value，避免 `KernelExpOp(input_value, out, ...)`
          等构造函数参数顺序与 op 字段顺序不一致时读写误绑。
        - `out` 产生 WRITE effect，`input` 产生 READ effect。

        使用示例:
        - effects = _KernelUnaryMemoryEffect.get_effects(op)

        关联文件:
        - spec: spec/dialect/kernel.md
        - test: test/dialect/kernel/test_kernel.py
        - 功能实现: kernel_gen/dialect/kernel/
        """

        return {
            EffectInstance(MemoryEffectKind.WRITE, SSAValue.get(op.out)),  # type: ignore[attr-defined]
            EffectInstance(MemoryEffectKind.READ, SSAValue.get(op.input)),  # type: ignore[attr-defined]
        }

class _KernelMatmulFusionMemoryEffect(MemoryEffect):
    """matmul_fusion 的 MemoryEffect trait。

    功能说明:
    - 暴露 out 的 READ/WRITE 与 lhs/rhs 的 READ，匹配 acc=true 时的累加语义。

    使用示例:
    - effects = _KernelMatmulFusionMemoryEffect.get_effects(op)
    """

    @classmethod
    def get_effects(cls, op: Operation) -> set[EffectInstance]:
        """返回 kernel.matmul_fusion 的 MemoryEffect 集合。

        功能说明:
        - `out` 在 acc=true 分支需要读取旧值并写回新值，因此暴露 READ 和 WRITE。
        - `lhs/rhs` 只读；`acc` 是标量控制 operand，不暴露 memory effect。

        使用示例:
        - effects = _KernelMatmulFusionMemoryEffect.get_effects(op)

        关联文件:
        - spec: spec/dialect/kernel.md
        - test: test/dialect/kernel/test_kernel.py
        - 功能实现: kernel_gen/dialect/kernel/
        """

        return {
            EffectInstance(MemoryEffectKind.READ, SSAValue.get(op.out)),  # type: ignore[attr-defined]
            EffectInstance(MemoryEffectKind.WRITE, SSAValue.get(op.out)),  # type: ignore[attr-defined]
            EffectInstance(MemoryEffectKind.READ, SSAValue.get(op.lhs)),  # type: ignore[attr-defined]
            EffectInstance(MemoryEffectKind.READ, SSAValue.get(op.rhs)),  # type: ignore[attr-defined]
        }

def _verify_element_type_match(types: Iterable[NnMemoryType], message: str) -> None:
    """校验 element_type 一致性。


    功能说明:
    - 要求所有类型的 element_type 相同。

    使用示例:
    - _verify_element_type_match([lhs_type, rhs_type, out_type], "...")

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    types = list(types)
    if not types:
        return
    base_type = types[0].element_type
    for other in types[1:]:
        if other.element_type != base_type:
            raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected=message,
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )

def _verify_matmul_shape(
    lhs_shape: Sequence[Attribute],
    rhs_shape: Sequence[Attribute],
    out_shape: Sequence[Attribute],
) -> None:
    """校验 kernel.matmul 的形状约束。


    功能说明:
    - 要求 lhs/rhs/out 皆为 rank-2。
    - 要求 `lhs=[M, K]`、`rhs=[K, N]`、`out=[M, N]` 机械一致。

    使用示例:
    - _verify_matmul_shape(lhs.shape.data, rhs.shape.data, out.shape.data)

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    lhs_shape = list(lhs_shape)
    rhs_shape = list(rhs_shape)
    out_shape = list(out_shape)
    if len(lhs_shape) != 2 or len(rhs_shape) != 2 or len(out_shape) != 2:
        raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
            ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected="kernel.matmul requires rank-2 memory types",
                actual=ERROR_ACTUAL,
                action=ERROR_ACTION,
            )
        )
    if lhs_shape[1] != rhs_shape[0]:
        raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
            ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected="kernel.matmul contracting dimensions must match",
                actual=ERROR_ACTUAL,
                action=ERROR_ACTION,
            )
        )
    if out_shape[0] != lhs_shape[0] or out_shape[1] != rhs_shape[1]:
        raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
            ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected="kernel.matmul result shape must match lhs/rhs",
                actual=ERROR_ACTUAL,
                action=ERROR_ACTION,
            )
        )

def _verify_matmul_fusion_shape(
    lhs_shape: Sequence[Attribute],
    rhs_shape: Sequence[Attribute],
    out_shape: Sequence[Attribute],
) -> None:
    """校验 kernel.matmul_fusion 的形状约束。

    功能说明:
    - 要求 lhs/rhs/out 皆为 rank-2。
    - 要求 `lhs=[M, K]`、`rhs=[K, N]`、`out=[M, N]` 机械一致。
    - 使用 matmul_fusion 专属稳定错误短语，避免与旧 kernel.matmul 合同混淆。

    使用示例:
    - _verify_matmul_fusion_shape(lhs.shape.data, rhs.shape.data, out.shape.data)

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    lhs_shape = list(lhs_shape)
    rhs_shape = list(rhs_shape)
    out_shape = list(out_shape)
    if len(lhs_shape) != 2 or len(rhs_shape) != 2 or len(out_shape) != 2:
        raise VerifyException(
            ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected="kernel.matmul_fusion requires rank-2 memory types",
                actual=ERROR_ACTUAL,
                action=ERROR_ACTION,
            )
        )
    if lhs_shape[1] != rhs_shape[0]:
        raise VerifyException(
            ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected="kernel.matmul_fusion contracting dimensions must match",
                actual=ERROR_ACTUAL,
                action=ERROR_ACTION,
            )
        )
    if out_shape[0] != lhs_shape[0] or out_shape[1] != rhs_shape[1]:
        raise VerifyException(
            ERROR_TEMPLATE.format(
                scene=_ERROR_SCENE,
                expected="kernel.matmul_fusion result shape must match lhs/rhs",
                actual=ERROR_ACTUAL,
                action=ERROR_ACTION,
            )
        )

class _KernelStructuredRules:
    """当前文件内的局部结构化 kernel 规则容器。

    功能说明:
    - 收纳 img2col verifier 需要复用的静态 operand 解析逻辑。
    - 该容器只在当前文件内使用，不作为跨文件公开 API。

    使用示例:
    - _KERNEL_STRUCTURED.static_int_from_operand(op.k)
    """

    @staticmethod
    def static_int_from_operand(operand: SSAValue) -> int | None:
        """尝试从 operand 提取静态整数值。


        功能说明:
        - 支持 `arith.constant`/`symbol.const` 以及单层 `builtin.unrealized_conversion_cast`。
        - block argument 没有定义 op，直接返回 None。
        - 无法解析时返回 None。

        使用示例:
        - value = _KERNEL_STRUCTURED.static_int_from_operand(op.k)

        关联文件:
        - spec: spec/dialect/kernel.md
        - test: test/dialect/kernel/test_kernel.py
        - 功能实现: kernel_gen/dialect/kernel/
        """

        current = operand
        while True:
            owner = current.owner
            if owner is None or not isinstance(owner, Operation):
                return None
            owner_name = owner.name
            if owner_name == "arith.constant":
                value_attr = owner.value if isinstance(owner, ConstantOp) else owner.attributes.get("value")
                if isinstance(value_attr, IntegerAttr):
                    return int(value_attr.value.data)
                if isinstance(value_attr, IntAttr):
                    return int(value_attr.data)
                return None
            if owner_name == "symbol.const":
                value_attr = owner.attributes.get("value")
                if isinstance(value_attr, IntAttr):
                    return int(value_attr.data)
                return None
            if owner_name != "builtin.unrealized_conversion_cast" or not owner.operands:
                return None
            current = owner.operands[0]

_KERNEL_STRUCTURED = _KernelStructuredRules()

def _verify_img2col_param_operands(
    operands: Sequence[SSAValue],
    *,
    allow_zero: bool,
    type_error_phrase: str,
    value_error_phrase: str,
) -> list[int | None]:
    """校验 img2col 参数 operand 类型并提取静态值。


    功能说明:
    - 要求每个 operand 为 IntegerType 或 symbol.int。
    - 若可解析出静态整数值，则校验正数/非负数约束。
    - 解析失败则返回 None，供上层决定是否跳过形状合同校验。

    使用示例:
    - values = _verify_img2col_param_operands([op.k, op.s], allow_zero=False, type_error_phrase="kernel.img2col1d k/s must be integer or symbol", value_error_phrase="kernel.img2col1d k/s must be positive")

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    values: list[int | None] = []
    for operand in operands:
        if not (isinstance(operand.type, SymbolValueType) or isinstance(operand.type, IntegerType)):
            raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected=type_error_phrase,
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        static_value = _KERNEL_STRUCTURED.static_int_from_operand(operand)
        if static_value is not None:
            if allow_zero:
                if static_value < 0:
                    raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
                        ERROR_TEMPLATE.format(
                            scene=_ERROR_SCENE,
                            expected=value_error_phrase,
                            actual=ERROR_ACTUAL,
                            action=ERROR_ACTION,
                        )
                    )
            elif static_value <= 0:
                raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
                    ERROR_TEMPLATE.format(
                        scene=_ERROR_SCENE,
                        expected=value_error_phrase,
                        actual=ERROR_ACTUAL,
                        action=ERROR_ACTION,
                    )
                )
        values.append(static_value)
    return values

def _img2col_output_dim(size: int, kernel: int, stride: int, dilation: int, pad_before: int, pad_after: int) -> int:
    """根据 img2col 参数计算单轴输出尺寸。


    功能说明:
    - 计算 `floor((size + pad_before + pad_after - dilation * (kernel - 1) - 1) / stride) + 1`。
    - 由 `kernel.img2col1d/img2col2d` 的 verifier 复用。

    使用示例:
    - _img2col_output_dim(5, 3, 1, 1, 0, 0)

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    effective_kernel = dilation * (kernel - 1) + 1
    padded_size = size + pad_before + pad_after
    valid_extent = padded_size - effective_kernel
    stride_steps = valid_extent // stride
    return stride_steps + 1

def _static_int_from_dim(dim: Attribute) -> int | None:
    """从结构化维度提取静态整数。


    功能说明:
    - 仅接受 `SymbolExprAttr` 表达的静态整数。
    - 动态符号、`?` 或非结构化属性返回 None。

    使用示例:
    - _static_int_from_dim(SymbolExprAttr.from_expr("4"))

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    if not isinstance(dim, SymbolExprAttr):
        return None
    try:
        return int(dim.expr.data)
    except ValueError:
        return None

class _BaseKernelBinaryOp(IRDLOperation):
    """内部兼容用的旧二元 op 基类。"""

    out = operand_def(NnMemoryType)
    lhs = operand_def(NnMemoryType)
    rhs = operand_def(NnMemoryType)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        out: SSAValue | Operation,
        lhs: SSAValue | Operation,
        rhs: SSAValue | Operation,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化二元 op。

        功能说明:
        - 按旧二元 kernel op 的 operand 顺序保存 out/lhs/rhs 与 space 属性。

        使用示例:
        - _BaseKernelBinaryOp(out, lhs, rhs, space)
        """

        super().__init__(operands=[out, lhs, rhs], attributes={"space": space})



_ERROR_SCENE = "dialect.kernel verifier"

@irdl_op_definition
class KernelMatmulOp(_BaseKernelBinaryOp):
    """kernel.matmul。


    功能说明:
    - 结构化矩阵乘 op，输入输出均为 nn.memory。
    - verifier 强制二维输入、shape 机械一致及 element_type 对齐。
    - 允许 out/lhs/rhs 使用不同合法 memory space，`space` attribute 只校验自身合法性。

    使用示例:
    - KernelMatmulOp(out, lhs, rhs, _make_space("global"))

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    name = "kernel.matmul"
    traits = traits_def(_KernelMatmulMemoryEffect())

    acc = opt_attr_def(IntegerAttr)

    def __init__(
        self,
        out: SSAValue | Operation,
        lhs: SSAValue | Operation,
        rhs: SSAValue | Operation,
        space: NnMemorySpaceAttr,
        *,
        acc: bool | int | IntegerAttr | IntAttr = False,
    ) -> None:
        """初始化 kernel.matmul。

        功能说明:
        - 按 out/lhs/rhs/space 公开顺序构造 op。
        - `acc=True` 写入 i1 attr；`acc=False` 省略 attr，保持 IR 缺省 false 合同。

        使用示例:
        - KernelMatmulOp(out, lhs, rhs, space, acc=True)
        """

        attributes: dict[str, Attribute] = {"space": space}
        acc_attr = _KERNEL_MATMUL_ACC.normalize_attr(acc)
        if acc_attr is not None:
            attributes["acc"] = acc_attr
        IRDLOperation.__init__(self, operands=[out, lhs, rhs], attributes=attributes)

    def verify_(self) -> None:
        """校验 kernel.matmul operand 与输出约束。

        功能说明:
        - 校验矩阵乘法 shape 合同、element type 一致性与 space 属性合法性。

        使用示例:
        - KernelMatmulOp(out, lhs, rhs, space).verify()
        """

        lhs_type = verify_memory_type(self.lhs.type, "lhs", scene=_ERROR_SCENE)
        rhs_type = verify_memory_type(self.rhs.type, "rhs", scene=_ERROR_SCENE)
        out_type = verify_memory_type(self.out.type, "out", scene=_ERROR_SCENE)
        self.space.verify()
        _KERNEL_MATMUL_ACC.verify_attr(self.acc)
        _verify_matmul_shape(lhs_type.shape.data, rhs_type.shape.data, out_type.shape.data)
        _verify_element_type_match(
            [lhs_type, rhs_type, out_type],
            "kernel.matmul element_type must match across operands",
        )


@irdl_op_definition
class KernelMatmulFusionOp(IRDLOperation):
    """kernel.matmul_fusion。

    功能说明:
    - 结构化矩阵乘累加中间 op，输入输出均为 nn.memory，acc 为 i1 标量。
    - `acc=false` 表示覆盖写 out，`acc=true` 表示累加写 out。
    - `fusion_list` 是字符串 metadata，不改变 verifier、effect 或分解语义。
    - 本 op 只作为 npu-demo lowering 中间 IR，进入 source/emit 前必须由分解 pass 拆回既有 op。

    使用示例:
    - KernelMatmulFusionOp(out, lhs, rhs, acc, space=_make_space("tsm"), fusion_list="kernel.matmul,kernel.binary_elewise.add")

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    name = "kernel.matmul_fusion"
    traits = traits_def(_KernelMatmulFusionMemoryEffect())

    out = operand_def(NnMemoryType)
    lhs = operand_def(NnMemoryType)
    rhs = operand_def(NnMemoryType)
    acc = operand_def(Attribute)
    space = attr_def(NnMemorySpaceAttr)
    fusion_list = opt_attr_def(Attribute)

    def __init__(
        self,
        out: SSAValue | Operation,
        lhs: SSAValue | Operation,
        rhs: SSAValue | Operation,
        acc: SSAValue | Operation,
        *,
        space: NnMemorySpaceAttr,
        fusion_list: str | StringAttr = "",
    ) -> None:
        """初始化 kernel.matmul_fusion op。

        功能说明:
        - 按公开 `out/lhs/rhs/acc` operand 顺序保存四个 operand 与 space 属性。
        - `fusion_list` 默认空字符串；非空字符串作为 metadata attr 保留。
        - 不生成 SSA result，结果通过 out memory 写回。

        使用示例:
        - KernelMatmulFusionOp(out, lhs, rhs, acc, space=space, fusion_list="kernel.matmul,kernel.binary_elewise.add")

        关联文件:
        - spec: spec/dialect/kernel.md
        - test: test/dialect/kernel/test_kernel.py
        - 功能实现: kernel_gen/dialect/kernel/
        """

        attributes: dict[str, Attribute] = {"space": space}
        fusion_list_attr = _normalize_matmul_fusion_list_attr(fusion_list)
        if fusion_list_attr is not None:
            attributes["fusion_list"] = fusion_list_attr
        super().__init__(operands=[out, lhs, rhs, acc], attributes=attributes)

    def verify_(self) -> None:
        """校验 kernel.matmul_fusion operand 与输出约束。

        功能说明:
        - 校验矩阵乘法 shape 合同、element type 一致性、acc=i1、space 与 fusion_list 属性合法性。
        - 错误短语固定为 `kernel.matmul_fusion ...`，供公开 expectation 和 pytest 匹配。

        使用示例:
        - KernelMatmulFusionOp(out, lhs, rhs, acc, space=space).verify_()

        关联文件:
        - spec: spec/dialect/kernel.md
        - test: test/dialect/kernel/test_kernel.py
        - 功能实现: kernel_gen/dialect/kernel/
        """

        lhs_type = verify_memory_type(self.lhs.type, "lhs", scene=_ERROR_SCENE)
        rhs_type = verify_memory_type(self.rhs.type, "rhs", scene=_ERROR_SCENE)
        out_type = verify_memory_type(self.out.type, "out", scene=_ERROR_SCENE)
        self.space.verify()
        fusion_attr = self.attributes.get("fusion_list")
        if fusion_attr is not None and not isinstance(fusion_attr, StringAttr):
            raise KernelCodeError(
                ErrorKind.VERIFY,
                ErrorModule.DIALECT,
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.matmul_fusion fusion_list must be string",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                ),
            )
        if SSAValue.get(self.acc).type != i1:
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.matmul_fusion acc must be i1",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        _verify_matmul_fusion_shape(lhs_type.shape.data, rhs_type.shape.data, out_type.shape.data)
        if lhs_type.element_type != rhs_type.element_type or lhs_type.element_type != out_type.element_type:
            raise VerifyException(
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.matmul_fusion element_type must match across operands",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )


@irdl_op_definition
class KernelImg2col1dOp(IRDLOperation):
    """kernel.img2col1d。


    功能说明:
    - 定义一维 img2col 的 kernel 目标 op。
    - verifier 校验输入输出 rank、窗口参数 operand、结构化结果 shape/stride 与空间一致性。

    使用示例:
    - KernelImg2col1dOp(inp, out, k_value, s_value, d_value, p_left_value, p_right_value, space=_make_space("global"))

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    name = "kernel.img2col1d"
    traits = traits_def(_KernelUnaryMemoryEffect())

    out = operand_def(NnMemoryType)
    input = operand_def(NnMemoryType)
    k = operand_def(Attribute)
    s = operand_def(Attribute)
    d = operand_def(Attribute)
    p_left = operand_def(Attribute)
    p_right = operand_def(Attribute)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        out: SSAValue | Operation,
        input_value: SSAValue | Operation,
        k: SSAValue | Operation,
        s: SSAValue | Operation,
        d: SSAValue | Operation,
        p_left: SSAValue | Operation,
        p_right: SSAValue | Operation,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 img2col1d op。


        功能说明:
        - 绑定输入/输出 operand 与窗口参数 operand。

        使用示例:
        - KernelImg2col1dOp(inp, out, k_value, s_value, d_value, p_left_value, p_right_value, _make_space("global"))

        关联文件:
        - spec: spec/dialect/kernel.md
        - test: test/dialect/kernel/test_kernel.py
        - 功能实现: kernel_gen/dialect/kernel/
        """

        super().__init__(
            operands=[out, input_value, k, s, d, p_left, p_right],
            attributes={"space": space},
        )

    def verify_(self) -> None:
        """校验 kernel.img2col1d 合同。


        功能说明:
        - 校验输入输出 rank、元素类型、空间、窗口参数 operand 与结构化结果布局。

        使用示例:
        - KernelImg2col1dOp(...).verify_()

        关联文件:
        - spec: spec/dialect/kernel.md
        - test: test/dialect/kernel/test_kernel.py
        - 功能实现: kernel_gen/dialect/kernel/
        """

        input_type = verify_memory_type(self.input.type, "input", scene=_ERROR_SCENE)
        out_type = verify_memory_type(self.out.type, "out", scene=_ERROR_SCENE)
        self.space.verify()

        if len(input_type.shape.data) != 3:
            raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col1d requires rank-3 input",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        if len(out_type.shape.data) != 4:
            raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col1d requires rank-4 result",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        if input_type.space.space.data != self.space.space.data:
            raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col1d attribute space must match input space",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        if out_type.space.space.data != self.space.space.data:
            raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col1d attribute space must match result space",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        if out_type.element_type != input_type.element_type:
            raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col1d result element_type must match input",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )

        k_value, s_value, d_value = _verify_img2col_param_operands(
            [self.k, self.s, self.d],
            allow_zero=False,
            type_error_phrase="kernel.img2col1d k/s/d must be integer or symbol",
            value_error_phrase="kernel.img2col1d k/s/d must be positive",
        )
        p_left_value, p_right_value = _verify_img2col_param_operands(
            [self.p_left, self.p_right],
            allow_zero=True,
            type_error_phrase="kernel.img2col1d p_left/p_right must be integer or symbol",
            value_error_phrase="kernel.img2col1d p_left/p_right must be non-negative",
        )

        input_shape = list(input_type.shape.data)
        out_shape = list(out_type.shape.data)
        if k_value is not None:
            if _static_int_from_dim(out_shape[2]) != k_value:
                raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
                    ERROR_TEMPLATE.format(
                        scene=_ERROR_SCENE,
                        expected="kernel.img2col1d result shape/stride must match img2col1d contract",
                        actual=ERROR_ACTUAL,
                        action=ERROR_ACTION,
                    )
                )

        input_dims = collect_int_dims(input_shape)
        input_strides = collect_int_dims(input_type.stride.data)
        if input_dims is not None and input_strides is not None:
            if input_strides != build_contiguous_stride(input_dims):
                raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
                    ERROR_TEMPLATE.format(
                        scene=_ERROR_SCENE,
                        expected="kernel.img2col1d input layout must be contiguous",
                        actual=ERROR_ACTUAL,
                        action=ERROR_ACTION,
                    )
                )

        out_dims = collect_int_dims(out_shape)
        out_strides = collect_int_dims(out_type.stride.data)
        if input_dims is None or out_dims is None or out_strides is None:
            return
        if any(value is None for value in (k_value, s_value, d_value, p_left_value, p_right_value)):
            return

        n_dim, c_dim, w_dim = input_dims
        w_out_dim = _img2col_output_dim(w_dim, k_value, s_value, d_value, p_left_value, p_right_value)
        expected_shape = [n_dim, c_dim, k_value, w_out_dim]
        expected_stride = build_contiguous_stride(expected_shape)
        if w_out_dim < 1 or out_dims != expected_shape or out_strides != expected_stride:
            raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col1d result shape/stride must match img2col1d contract",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )


@irdl_op_definition
class KernelImg2col2dOp(IRDLOperation):
    """kernel.img2col2d。


    功能说明:
    - 定义二维 img2col 的 kernel 目标 op。
    - verifier 校验输入输出 rank、窗口参数 operand、结构化结果 shape/stride 与空间一致性。

    使用示例:
    - KernelImg2col2dOp(inp, out, kh_value, kw_value, sh_value, sw_value, dh_value, dw_value, ph_value, pw_value, pl_value, pr_value, space=_make_space("global"))

    关联文件:
    - spec: spec/dialect/kernel.md
    - test: test/dialect/kernel/test_kernel.py
    - 功能实现: kernel_gen/dialect/kernel/
    """

    name = "kernel.img2col2d"
    traits = traits_def(_KernelUnaryMemoryEffect())

    out = operand_def(NnMemoryType)
    input = operand_def(NnMemoryType)
    kh = operand_def(Attribute)
    kw = operand_def(Attribute)
    sh = operand_def(Attribute)
    sw = operand_def(Attribute)
    dh = operand_def(Attribute)
    dw = operand_def(Attribute)
    ph = operand_def(Attribute)
    pw = operand_def(Attribute)
    pl = operand_def(Attribute)
    pr = operand_def(Attribute)
    space = attr_def(NnMemorySpaceAttr)

    def __init__(
        self,
        out: SSAValue | Operation,
        input_value: SSAValue | Operation,
        kh: SSAValue | Operation,
        kw: SSAValue | Operation,
        sh: SSAValue | Operation,
        sw: SSAValue | Operation,
        dh: SSAValue | Operation,
        dw: SSAValue | Operation,
        ph: SSAValue | Operation,
        pw: SSAValue | Operation,
        pl: SSAValue | Operation,
        pr: SSAValue | Operation,
        space: NnMemorySpaceAttr,
    ) -> None:
        """初始化 img2col2d op。


        功能说明:
        - 绑定输入/输出 operand 与窗口参数 operand。

        使用示例:
        - KernelImg2col2dOp(inp, out, kh_value, kw_value, sh_value, sw_value, dh_value, dw_value, ph_value, pw_value, pl_value, pr_value, _make_space("global"))

        关联文件:
        - spec: spec/dialect/kernel.md
        - test: test/dialect/kernel/test_kernel.py
        - 功能实现: kernel_gen/dialect/kernel/
        """

        super().__init__(
            operands=[out, input_value, kh, kw, sh, sw, dh, dw, ph, pw, pl, pr],
            attributes={"space": space},
        )

    def verify_(self) -> None:
        """校验 kernel.img2col2d 合同。


        功能说明:
        - 校验输入输出 rank、元素类型、空间、窗口参数 operand 与结构化结果布局。

        使用示例:
        - KernelImg2col2dOp(...).verify_()

        关联文件:
        - spec: spec/dialect/kernel.md
        - test: test/dialect/kernel/test_kernel.py
        - 功能实现: kernel_gen/dialect/kernel/
        """

        input_type = verify_memory_type(self.input.type, "input", scene=_ERROR_SCENE)
        out_type = verify_memory_type(self.out.type, "out", scene=_ERROR_SCENE)
        self.space.verify()

        if len(input_type.shape.data) != 4:
            raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col2d requires rank-4 input",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        if len(out_type.shape.data) != 6:
            raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col2d requires rank-6 result",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        if input_type.space.space.data != self.space.space.data:
            raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col2d attribute space must match input space",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        if out_type.space.space.data != self.space.space.data:
            raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col2d attribute space must match result space",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )
        if out_type.element_type != input_type.element_type:
            raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col2d result element_type must match input",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )

        kh_value, kw_value, sh_value, sw_value, dh_value, dw_value = _verify_img2col_param_operands(
            [self.kh, self.kw, self.sh, self.sw, self.dh, self.dw],
            allow_zero=False,
            type_error_phrase="kernel.img2col2d kh/kw/sh/sw/dh/dw must be integer or symbol",
            value_error_phrase="kernel.img2col2d kh/kw/sh/sw/dh/dw must be positive",
        )
        ph_value, pw_value, pl_value, pr_value = _verify_img2col_param_operands(
            [self.ph, self.pw, self.pl, self.pr],
            allow_zero=True,
            type_error_phrase="kernel.img2col2d ph/pw/pl/pr must be integer or symbol",
            value_error_phrase="kernel.img2col2d ph/pw/pl/pr must be non-negative",
        )

        input_shape = list(input_type.shape.data)
        out_shape = list(out_type.shape.data)
        if kh_value is not None:
            if _static_int_from_dim(out_shape[2]) != kh_value:
                raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
                    ERROR_TEMPLATE.format(
                        scene=_ERROR_SCENE,
                        expected="kernel.img2col2d result shape/stride must match img2col2d contract",
                        actual=ERROR_ACTUAL,
                        action=ERROR_ACTION,
                    )
                )
        if kw_value is not None:
            if _static_int_from_dim(out_shape[3]) != kw_value:
                raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
                    ERROR_TEMPLATE.format(
                        scene=_ERROR_SCENE,
                        expected="kernel.img2col2d result shape/stride must match img2col2d contract",
                        actual=ERROR_ACTUAL,
                        action=ERROR_ACTION,
                    )
                )

        input_dims = collect_int_dims(input_shape)
        input_strides = collect_int_dims(input_type.stride.data)
        if input_dims is not None and input_strides is not None:
            if input_strides != build_contiguous_stride(input_dims):
                raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
                    ERROR_TEMPLATE.format(
                        scene=_ERROR_SCENE,
                        expected="kernel.img2col2d input layout must be contiguous",
                        actual=ERROR_ACTUAL,
                        action=ERROR_ACTION,
                    )
                )

        out_dims = collect_int_dims(out_shape)
        out_strides = collect_int_dims(out_type.stride.data)
        if input_dims is None or out_dims is None or out_strides is None:
            return
        if any(
            value is None
            for value in (
                kh_value,
                kw_value,
                sh_value,
                sw_value,
                dh_value,
                dw_value,
                ph_value,
                pw_value,
                pl_value,
                pr_value,
            )
        ):
            return

        n_dim, c_dim, h_dim, w_dim = input_dims
        oh_dim = _img2col_output_dim(h_dim, kh_value, sh_value, dh_value, ph_value, pw_value)
        ow_dim = _img2col_output_dim(w_dim, kw_value, sw_value, dw_value, pl_value, pr_value)
        expected_shape = [n_dim, c_dim, kh_value, kw_value, oh_dim, ow_dim]
        expected_stride = build_contiguous_stride(expected_shape)
        if oh_dim < 1 or ow_dim < 1 or out_dims != expected_shape or out_strides != expected_stride:
            raise kernel_code_error(ErrorKind.VERIFY, ErrorModule.DIALECT,
                ERROR_TEMPLATE.format(
                    scene=_ERROR_SCENE,
                    expected="kernel.img2col2d result shape/stride must match img2col2d contract",
                    actual=ERROR_ACTUAL,
                    action=ERROR_ACTION,
                )
            )

__all__ = [
    "KernelMatmulOp",
    "KernelMatmulFusionOp",
    "KernelImg2col1dOp",
    "KernelImg2col2dOp",
]
