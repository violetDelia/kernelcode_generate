"""nn_lowering 公共辅助函数。

创建者: 小李飞刀
最后一次更改: 金铲铲大作战

功能说明:
- 提供 nn_lowering pass 的公共校验与辅助构造入口。
- 统一 nn op 的空间、名称、结果数量与 operand 计数检查。

使用示例:
- from kernel_gen.passes.lowering.nn_lowering.nn_lowering_utility import ensure_space_attr
- space = ensure_space_attr(op)

关联文件:
- spec: spec/pass/lowering/nn_lowering/spec.md
- test: test/pass/nn_lowering/public_name.py
- 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering_utility.py
"""

from __future__ import annotations

from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import Operation

from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from .nn_lowering import NnLoweringError


def ensure_module_op(module: Operation) -> ModuleOp:
    """校验 module 是否为 builtin.module 并确保 ops 可遍历。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 用于 nn_lowering pass 的统一入口校验。

    使用示例:
    - module_op = ensure_module_op(module)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/pass/nn_lowering/public_name.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering_utility.py
    """

    if not isinstance(module, ModuleOp):
        raise NnLoweringError("module must be builtin.module")
    try:
        iter(module.ops)
    except TypeError as exc:
        raise NnLoweringError("module ops must be iterable") from exc
    return module


def ensure_space_attr(op: Operation) -> NnMemorySpaceAttr:
    """获取并校验 nn op 的 space attribute。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 统一 `nn` op 的空间属性校验逻辑。

    使用示例:
    - space = ensure_space_attr(op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/pass/nn_lowering/public_name.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering_utility.py
    """

    space = op.attributes.get("space")
    if not isinstance(space, NnMemorySpaceAttr):
        raise NnLoweringError("nn op must provide nn.space attribute")
    return space


def ensure_single_result(op: Operation) -> NnMemoryType:
    """校验 nn op 仅有单个结果且类型为 nn.memory。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 要求结果数量为 1。
    - 要求结果类型为 NnMemoryType。

    使用示例:
    - result_type = ensure_single_result(op)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/pass/nn_lowering/public_name.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering_utility.py
    """

    if len(op.results) != 1:
        raise NnLoweringError("nn op must have exactly one result")
    result_type = op.results[0].type
    if not isinstance(result_type, NnMemoryType):
        raise NnLoweringError("nn op result must be nn.memory")
    return result_type


def ensure_operand_count(op: Operation, expected: int) -> None:
    """校验 nn op 的 operand 数量。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - operand 数量不匹配时直接抛错。

    使用示例:
    - ensure_operand_count(op, 2)

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/pass/nn_lowering/public_name.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering_utility.py
    """

    if len(op.operands) != expected:
        raise NnLoweringError(
            f"nn op {op.name} expects {expected} operands, got {len(op.operands)}"
        )


def ensure_expected_op_name(op: Operation, expected: str) -> None:
    """校验具体 pattern 命中的 op 名称未被篡改。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 单 op pattern 先按具体 Python 类型命中。
    - 此处只校验实例名称与该类型公开名称一致，避免被改名的 nn op 绕过未知 op 错误路径。

    使用示例:
    - ensure_expected_op_name(op, "nn.add")

    关联文件:
    - spec: spec/pass/lowering/nn_lowering/spec.md
    - test: test/pass/nn_lowering/test_lowering_nn_lowering.py
    - 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering_utility.py
    """

    if op.name != expected:
        raise NnLoweringError(f"unknown op: {op.name}")


__all__ = [
    "NnLoweringError",
    "ensure_expected_op_name",
    "ensure_module_op",
    "ensure_space_attr",
    "ensure_single_result",
    "ensure_operand_count",
]
