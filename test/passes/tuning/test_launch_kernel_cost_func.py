"""launch-kernel-cost-func pass tests.


功能说明:
- 覆盖 `LaunchKernelCostFuncPass` 的成功路径、共享 callee 去重与显式失败边界。
- 锁定 `tuner.cost` metadata、`symbol.for` carried `!symbol.int` 与 `symbol.add` 累计链，以及 registry 名称合同。

使用示例:
- pytest -q test/passes/tuning/test_launch_kernel_cost_func.py

关联文件:
- spec: [spec/pass/tuning/launch_kernel_cost_func.md](spec/pass/tuning/launch_kernel_cost_func.md)
- test: [test/passes/tuning/test_launch_kernel_cost_func.py](test/passes/tuning/test_launch_kernel_cost_func.py)
- 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](kernel_gen/passes/tuning/launch_kernel_cost_func.py)
"""

from __future__ import annotations

from io import StringIO
import sys
from pathlib import Path

import pytest
from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, Float32Type, IntAttr, IntegerAttr, ModuleOp, StringAttr, i32
from xdsl.ir import Attribute, Region, SSAValue
from xdsl.irdl import IRDLOperation, attr_def, irdl_op_definition, operand_def, result_def
from xdsl.dialects.builtin import SymbolRefAttr
from xdsl.printer import Printer
from xdsl.utils.exceptions import VerifyException

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.arch import ArchGetDynamicMemoryOp, ArchLaunchOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolConstOp, SymbolExprAttr, SymbolForOp, SymbolIterType, SymbolValueType
from kernel_gen.passes.registry import build_registered_pass, load_builtin_passes
from kernel_gen.passes.tuning.launch_kernel_cost_func import LaunchKernelCostFuncPass


@irdl_op_definition
class UnsupportedOp(IRDLOperation):
    """测试专用的非支持 op。"""

    name = "test.unsupported"
    result = result_def(i32)

    def __init__(self: "UnsupportedOp") -> None:
        super().__init__(result_types=[i32])


@irdl_op_definition
class DmaViewOp(IRDLOperation):
    """测试专用的 helper `dma.view`。"""

    name = "dma.view"
    source = operand_def(Attribute)
    result = result_def(Attribute)

    def __init__(self: "DmaViewOp", source: SSAValue, result_type: Attribute) -> None:
        super().__init__(operands=[source], result_types=[result_type])


@irdl_op_definition
class DmaReshapeOp(IRDLOperation):
    """测试专用的 helper `dma.reshape`。"""

    name = "dma.reshape"
    source = operand_def(Attribute)
    result = result_def(Attribute)

    def __init__(self: "DmaReshapeOp", source: SSAValue, result_type: Attribute) -> None:
        super().__init__(operands=[source], result_types=[result_type])


@irdl_op_definition
class DmaSubviewOp(IRDLOperation):
    """测试专用的 helper `dma.subview`。"""

    name = "dma.subview"
    source = operand_def(Attribute)
    result = result_def(Attribute)

    def __init__(self: "DmaSubviewOp", source: SSAValue, result_type: Attribute) -> None:
        super().__init__(operands=[source], result_types=[result_type])


@irdl_op_definition
class DmaCopyOp(IRDLOperation):
    """测试专用的 `dma.copy`。"""

    name = "dma.copy"
    dst = operand_def(Attribute)
    src = operand_def(Attribute)

    def __init__(self: "DmaCopyOp", dst: SSAValue, src: SSAValue) -> None:
        super().__init__(operands=[dst, src])


@irdl_op_definition
class KernelAddOp(IRDLOperation):
    """测试专用的 `kernel.add`。"""

    name = "kernel.add"
    out = operand_def(Attribute)
    lhs = operand_def(Attribute)
    rhs = operand_def(Attribute)
    space = attr_def(Attribute)

    def __init__(
        self: "KernelAddOp",
        out: SSAValue,
        lhs: SSAValue,
        rhs: SSAValue,
        *,
        space: Attribute,
    ) -> None:
        super().__init__(operands=[out, lhs, rhs], attributes={"space": space})


@irdl_op_definition
class KernelReduceOp(IRDLOperation):
    """测试专用的 `kernel.reduce`。"""

    name = "kernel.reduce"
    out = operand_def(Attribute)
    input = operand_def(Attribute)
    kind = attr_def(Attribute)
    axis = attr_def(Attribute)
    space = attr_def(Attribute)

    def __init__(
        self: "KernelReduceOp",
        out: SSAValue,
        input: SSAValue,
        *,
        kind: Attribute,
        axis: Attribute,
        space: Attribute,
    ) -> None:
        super().__init__(
            operands=[out, input],
            attributes={"kind": kind, "axis": axis, "space": space},
        )


def _print_ir(module: ModuleOp) -> str:
    """打印 module 为稳定文本。


    功能说明:
    - 为断言 `tuner.cost`、`symbol.for` 与命名规则提供稳定输出。

    使用示例:
    - text = _print_ir(module)

    关联文件:
    - spec: [spec/pass/tuning/launch_kernel_cost_func.md](spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [test/passes/tuning/test_launch_kernel_cost_func.py](test/passes/tuning/test_launch_kernel_cost_func.py)
    - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](kernel_gen/passes/tuning/launch_kernel_cost_func.py)
    """

    stream = StringIO()
    Printer(stream=stream).print_op(module)
    return stream.getvalue()


def _make_memory_type(space: str = "global") -> NnMemoryType:
    """构造用于 pass 测试的合法 `nn.memory` 类型。


    功能说明:
    - 生成固定二维 `f32` memory type，供 wrapper/device 参数与 `dma.copy`、`kernel.add` 复用。

    使用示例:
    - memory_type = _make_memory_type()

    关联文件:
    - spec: [spec/pass/tuning/launch_kernel_cost_func.md](spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [test/passes/tuning/test_launch_kernel_cost_func.py](test/passes/tuning/test_launch_kernel_cost_func.py)
    - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](kernel_gen/passes/tuning/launch_kernel_cost_func.py)
    """

    return NnMemoryType(
        ArrayAttr([SymbolExprAttr.from_expr("4"), SymbolExprAttr.from_expr("4")]),
        ArrayAttr([SymbolExprAttr.from_expr("4"), SymbolExprAttr.from_expr("1")]),
        Float32Type(),
        NnMemorySpaceAttr(StringAttr(space)),
    )


def _build_launch_kernel_module(
    *,
    duplicate_launch: bool = False,
    conflict_attr: bool = False,
    reduce_kind_op: bool = False,
    unsupported_op: bool = False,
    missing_callee: bool = False,
    preexisting_cost_func: bool = False,
) -> ModuleOp:
    """构造含 `arch.launch -> device` 关系的最小 module。


    功能说明:
    - 生成一个 wrapper 与一个 device function。
    - device body 内包含 `symbol.for`、`arch.get_dynamic_memory`、`dma.view`、`dma.subview`、`dma.reshape`、`dma.copy` 与 `kernel.add`，用于覆盖 helper 保留与成本节点生成合同。
    - 可选生成共享 callee 的第二个 wrapper，或为目标 op 注入保留 metadata attr 冲突。

    使用示例:
    - module = _build_launch_kernel_module()

    关联文件:
    - spec: [spec/pass/tuning/launch_kernel_cost_func.md](spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [test/passes/tuning/test_launch_kernel_cost_func.py](test/passes/tuning/test_launch_kernel_cost_func.py)
    - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](kernel_gen/passes/tuning/launch_kernel_cost_func.py)
    """

    memory_type = _make_memory_type()
    symbol_m = SymbolValueType.from_expr("M")
    arg_types = [memory_type, memory_type, memory_type, symbol_m]

    wrapper_block = func.Block(arg_types=arg_types) if hasattr(func, "Block") else None
    if wrapper_block is None:
        from xdsl.ir import Block as _Block

        wrapper_block = _Block(arg_types=arg_types)
        extra_wrapper_block = _Block(arg_types=arg_types)
        device_block = _Block(arg_types=arg_types)
        loop_block = _Block(arg_types=[SymbolIterType.from_bounds("0", "M", "1")])
    else:
        extra_wrapper_block = func.Block(arg_types=arg_types)
        device_block = func.Block(arg_types=arg_types)
        loop_block = func.Block(arg_types=[SymbolIterType.from_bounds("0", "M", "1")])

    launch_block = SymbolConstOp(1)
    launch_thread = SymbolConstOp(1)
    launch_subthread = SymbolConstOp(1)
    launch_shared_memory = SymbolConstOp(0)
    launch_op = ArchLaunchOp(
        "_device_kernel",
        launch_block.result,
        launch_thread.result,
        launch_subthread.result,
        launch_shared_memory.result,
        tuple(wrapper_block.args),
    )
    if missing_callee:
        launch_op.attributes["callee"] = SymbolRefAttr("missing_kernel")
    wrapper_block.add_ops(
        [launch_block, launch_thread, launch_subthread, launch_shared_memory, launch_op, func.ReturnOp()]
    )

    extra_launch_block = SymbolConstOp(1)
    extra_launch_thread = SymbolConstOp(1)
    extra_launch_subthread = SymbolConstOp(1)
    extra_launch_shared_memory = SymbolConstOp(0)
    extra_wrapper_block.add_ops(
        [
            extra_launch_block,
            extra_launch_thread,
            extra_launch_subthread,
            extra_launch_shared_memory,
            ArchLaunchOp(
                "_device_kernel",
                extra_launch_block.result,
                extra_launch_thread.result,
                extra_launch_subthread.result,
                extra_launch_shared_memory.result,
                tuple(extra_wrapper_block.args),
            ),
            func.ReturnOp(),
        ]
    )

    start = SymbolConstOp(0)
    step = SymbolConstOp(1)
    dynamic_memory = ArchGetDynamicMemoryOp(NnMemorySpaceAttr(StringAttr("shared")))
    view = DmaViewOp(device_block.args[0], memory_type)
    subview = DmaSubviewOp(view.result, memory_type)
    reshape = DmaReshapeOp(device_block.args[1], memory_type)
    dma_copy = DmaCopyOp(device_block.args[2], subview.result)
    kernel_add = KernelAddOp(
        device_block.args[2],
        device_block.args[0],
        device_block.args[1],
        space=NnMemorySpaceAttr(StringAttr("global")),
    )
    kernel_reduce = KernelReduceOp(
        device_block.args[2],
        device_block.args[0],
        kind=StringAttr("max"),
        axis=IntegerAttr(1, i32),
        space=NnMemorySpaceAttr(StringAttr("global")),
    )
    if conflict_attr:
        kernel_add.attributes["cost_kind"] = StringAttr("VECTOR1")
    loop_block.add_op(dynamic_memory)
    loop_block.add_op(view)
    loop_block.add_op(subview)
    loop_block.add_op(reshape)
    loop_block.add_op(dma_copy)
    if unsupported_op:
        loop_block.add_op(UnsupportedOp())
    loop_block.add_op(kernel_add)
    if reduce_kind_op:
        loop_block.add_op(kernel_reduce)
    loop = SymbolForOp(
        start.result,
        device_block.args[3],
        step.result,
        loop_block,
    )
    device_block.add_ops([start, step, loop, func.ReturnOp()])

    wrapper = func.FuncOp("wrapper", (arg_types, []), func.Region(wrapper_block) if hasattr(func, "Region") else Region(wrapper_block))
    device = func.FuncOp("_device_kernel", (arg_types, []), func.Region(device_block) if hasattr(func, "Region") else Region(device_block))

    ops: list = [wrapper]
    if duplicate_launch:
        extra_wrapper = func.FuncOp(
            "wrapper_2",
            (arg_types, []),
            func.Region(extra_wrapper_block) if hasattr(func, "Region") else Region(extra_wrapper_block),
        )
        ops.append(extra_wrapper)
    ops.append(device)
    if preexisting_cost_func:
        ops.append(func.FuncOp("_cost_DMA1__device_kernel", ([], [])))
    module = ModuleOp(ops)
    return module


# TC-LKCF-001
# 功能说明: 锁定公开 pass 名称。
# 使用示例: pytest -q test/passes/tuning/test_launch_kernel_cost_func.py -k test_launch_kernel_cost_func_pass_registry_name
# 对应功能实现文件路径: kernel_gen/passes/tuning/launch_kernel_cost_func.py
# 对应 spec 文件路径: spec/pass/tuning/launch_kernel_cost_func.md
# 对应测试文件路径: test/passes/tuning/test_launch_kernel_cost_func.py
def test_launch_kernel_cost_func_pass_registry_name() -> None:
    assert LaunchKernelCostFuncPass.name == "launch-kernel-cost-func"


# TC-LKCF-001A
# 功能说明: 验证默认 `cost_kind` 固定为七类公开成本 kind。
# 使用示例: pytest -q test/passes/tuning/test_launch_kernel_cost_func.py -k test_launch_kernel_cost_func_default_kind_is_dma_mac
# 对应功能实现文件路径: kernel_gen/passes/tuning/launch_kernel_cost_func.py
# 对应 spec 文件路径: spec/pass/tuning/launch_kernel_cost_func.md
# 对应测试文件路径: test/passes/tuning/test_launch_kernel_cost_func.py
def test_launch_kernel_cost_func_default_kind_is_full_npu_demo_cost_set() -> None:
    module = _build_launch_kernel_module()

    pass_obj = LaunchKernelCostFuncPass()
    pass_obj.apply(Context(), module)
    module.verify()

    assert pass_obj.cost_kind == "DMA1|DMA2|DMA3|DMA4|MAC|VECTOR1|VECTOR2"
    funcs = [op.sym_name.data for op in module.ops if isinstance(op, func.FuncOp)]
    assert funcs == [
        "wrapper",
        "_device_kernel",
        "_cost_DMA1__device_kernel",
        "_cost_DMA2__device_kernel",
        "_cost_DMA3__device_kernel",
        "_cost_DMA4__device_kernel",
        "_cost_MAC__device_kernel",
        "_cost_VECTOR1__device_kernel",
        "_cost_VECTOR2__device_kernel",
    ]
    printed = _print_ir(module)
    for kind in ("DMA1", "DMA2", "DMA3", "DMA4", "MAC", "VECTOR1", "VECTOR2"):
        assert printed.count(f'cost_kind = "{kind}"') == 2


# TC-LKCF-002
# 功能说明: 验证 `cost_kind=VECTOR1` 成功路径会新增 cost function，并生成 `tuner.cost + symbol.add` 累计链。
# 使用示例: pytest -q test/passes/tuning/test_launch_kernel_cost_func.py -k test_launch_kernel_cost_func_builds_cost_function_for_vector1_kind
# 对应功能实现文件路径: kernel_gen/passes/tuning/launch_kernel_cost_func.py
# 对应 spec 文件路径: spec/pass/tuning/launch_kernel_cost_func.md
# 对应测试文件路径: test/passes/tuning/test_launch_kernel_cost_func.py
def test_launch_kernel_cost_func_builds_cost_function_for_vector1_kind() -> None:
    module = _build_launch_kernel_module()

    LaunchKernelCostFuncPass(cost_kind="VECTOR1").apply(Context(), module)
    module.verify()

    funcs = [op for op in module.ops if isinstance(op, func.FuncOp)]
    assert [op.sym_name.data for op in funcs] == ["wrapper", "_device_kernel", "_cost_VECTOR1__device_kernel"]

    printed = _print_ir(module)
    assert "@_cost_VECTOR1__device_kernel" in printed
    assert printed.count('cost_kind = "VECTOR1"') == 2
    assert 'op_name = "dma.copy"' in printed
    assert 'op_name = "kernel.add"' in printed
    assert "symbol.for" in printed
    assert "iter_args(" in printed
    assert "symbol.yield" in printed
    assert "symbol.add" in printed
    assert "arch.get_dynamic_memory" in printed
    assert '"dma.view"' in printed
    assert '"dma.subview"' in printed
    assert '"dma.reshape"' in printed
    assert 'op_name = "arch.get_dynamic_memory"' not in printed
    assert 'op_name = "dma.view"' not in printed
    assert 'op_name = "dma.subview"' not in printed
    assert 'op_name = "dma.reshape"' not in printed
    assert ' kind = "VECTOR1"' not in printed
    assert printed.count("tuner.cost") == 2


# TC-LKCF-002A
# 功能说明: 验证 `kernel.reduce.kind` 作为业务属性会被转成 `kernel_kind`，不与 cost metadata 冲突。
# 使用示例: pytest -q test/passes/tuning/test_launch_kernel_cost_func.py -k test_launch_kernel_cost_func_preserves_kernel_reduce_kind_as_kernel_kind
# 对应功能实现文件路径: kernel_gen/passes/tuning/launch_kernel_cost_func.py
# 对应 spec 文件路径: spec/pass/tuning/launch_kernel_cost_func.md
# 对应测试文件路径: test/passes/tuning/test_launch_kernel_cost_func.py
def test_launch_kernel_cost_func_preserves_kernel_reduce_kind_as_kernel_kind() -> None:
    module = _build_launch_kernel_module(reduce_kind_op=True)

    LaunchKernelCostFuncPass(cost_kind="MAC").apply(Context(), module)
    module.verify()

    printed = _print_ir(module)
    assert 'op_name = "kernel.reduce"' in printed
    assert 'kernel_kind = "max"' in printed
    assert "reserved attr" not in printed


# TC-LKCF-003
# 功能说明: 验证 `cost_kind=DMA1` 不裁剪成本节点，仅切换 metadata 值。
# 使用示例: pytest -q test/passes/tuning/test_launch_kernel_cost_func.py -k test_launch_kernel_cost_func_dma1_keeps_all_cost_nodes
# 对应功能实现文件路径: kernel_gen/passes/tuning/launch_kernel_cost_func.py
# 对应 spec 文件路径: spec/pass/tuning/launch_kernel_cost_func.md
# 对应测试文件路径: test/passes/tuning/test_launch_kernel_cost_func.py
def test_launch_kernel_cost_func_dma1_keeps_all_cost_nodes() -> None:
    module = _build_launch_kernel_module()

    LaunchKernelCostFuncPass(cost_kind="DMA1").apply(Context(), module)

    printed = _print_ir(module)
    assert "@_cost_DMA1__device_kernel" in printed
    assert printed.count('cost_kind = "DMA1"') == 2
    assert 'op_name = "dma.copy"' in printed
    assert 'op_name = "kernel.add"' in printed


# TC-LKCF-002B
# 功能说明: 验证公开多值列表会按顺序新增对应数量的 cost function。
# 使用示例: pytest -q test/passes/tuning/test_launch_kernel_cost_func.py -k test_launch_kernel_cost_func_builds_cost_functions_for_multi_kind_order
# 对应功能实现文件路径: kernel_gen/passes/tuning/launch_kernel_cost_func.py
# 对应 spec 文件路径: spec/pass/tuning/launch_kernel_cost_func.md
# 对应测试文件路径: test/passes/tuning/test_launch_kernel_cost_func.py
def test_launch_kernel_cost_func_builds_cost_functions_for_multi_kind_order() -> None:
    module = _build_launch_kernel_module()

    LaunchKernelCostFuncPass(cost_kind="DMA1|MAC|VECTOR1").apply(Context(), module)
    module.verify()

    funcs = [op for op in module.ops if isinstance(op, func.FuncOp)]
    assert [op.sym_name.data for op in funcs] == [
        "wrapper",
        "_device_kernel",
        "_cost_DMA1__device_kernel",
        "_cost_MAC__device_kernel",
        "_cost_VECTOR1__device_kernel",
    ]

    printed = _print_ir(module)
    for kind in ("DMA1", "MAC", "VECTOR1"):
        assert printed.count(f'cost_kind = "{kind}"') == 2
        assert f'_cost_{kind}__device_kernel' in printed
    assert printed.count("tuner.cost") == 6
    assert "{kind =" not in printed


# TC-LKCF-004
# 功能说明: 验证共享 callee 时同一 `cost_kind` 仅生成一份 cost function。
# 使用示例: pytest -q test/passes/tuning/test_launch_kernel_cost_func.py -k test_launch_kernel_cost_func_shared_callee_once
# 对应功能实现文件路径: kernel_gen/passes/tuning/launch_kernel_cost_func.py
# 对应 spec 文件路径: spec/pass/tuning/launch_kernel_cost_func.md
# 对应测试文件路径: test/passes/tuning/test_launch_kernel_cost_func.py
def test_launch_kernel_cost_func_shared_callee_once() -> None:
    module = _build_launch_kernel_module(duplicate_launch=True)

    LaunchKernelCostFuncPass(cost_kind="DMA1").apply(Context(), module)

    funcs = [op.sym_name.data for op in module.ops if isinstance(op, func.FuncOp)]
    assert funcs == ["wrapper", "wrapper_2", "_device_kernel", "_cost_DMA1__device_kernel"]


# TC-LKCF-005A
# 功能说明: 验证非法 `cost_kind` 报稳定错误短语。
# 使用示例: pytest -q test/passes/tuning/test_launch_kernel_cost_func.py -k test_launch_kernel_cost_func_rejects_invalid_cost_kind
# 对应功能实现文件路径: kernel_gen/passes/tuning/launch_kernel_cost_func.py
# 对应 spec 文件路径: spec/pass/tuning/launch_kernel_cost_func.md
# 对应测试文件路径: test/passes/tuning/test_launch_kernel_cost_func.py
@pytest.mark.parametrize(
    "cost_kind",
    [
        "",
        "   ",
        "DMA1||MAC",
        "DMA1| VECTOR1 |DMA1",
        "compute",
        "DMA|MAC",
    ],
)
def test_launch_kernel_cost_func_rejects_invalid_cost_kind(cost_kind: str) -> None:
    with pytest.raises(
        KernelCodeError,
        match=r"^LaunchKernelCostFuncError: cost_kind must be '\|' separated names from \[DMA1,DMA2,DMA3,DMA4,MAC,VECTOR1,VECTOR2\]$",
    ):
        LaunchKernelCostFuncPass(cost_kind=cost_kind)


# TC-LKCF-005B
# 功能说明: 验证 registry 构造 launch-kernel-cost-func 时不会吞掉非法 `cost_kind` 的业务错误。
# 使用示例: pytest -q test/passes/tuning/test_launch_kernel_cost_func.py -k test_launch_kernel_cost_func_rejects_invalid_cost_kind_via_registry
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/passes/tuning/test_launch_kernel_cost_func.py
def test_launch_kernel_cost_func_rejects_invalid_cost_kind_via_registry() -> None:
    load_builtin_passes()

    with pytest.raises(
        KernelCodeError,
        match=r"^LaunchKernelCostFuncError: cost_kind must be '\|' separated names from \[DMA1,DMA2,DMA3,DMA4,MAC,VECTOR1,VECTOR2\]$",
    ):
        build_registered_pass("launch-kernel-cost-func", {"cost_kind": "DMA1|VECTOR1|DMA1"})


# TC-LKCF-006
# 功能说明: 验证原 op metadata attr 与 pass-owned attr 冲突时显式失败。
# 使用示例: pytest -q test/passes/tuning/test_launch_kernel_cost_func.py -k test_launch_kernel_cost_func_rejects_metadata_attr_conflict
# 对应功能实现文件路径: kernel_gen/passes/tuning/launch_kernel_cost_func.py
# 对应 spec 文件路径: spec/pass/tuning/launch_kernel_cost_func.md
# 对应测试文件路径: test/passes/tuning/test_launch_kernel_cost_func.py
def test_launch_kernel_cost_func_rejects_metadata_attr_conflict() -> None:
    module = _build_launch_kernel_module(conflict_attr=True)

    with pytest.raises(
        KernelCodeError,
        match=r"reserved attr 'cost_kind'$",
    ):
        LaunchKernelCostFuncPass(cost_kind="VECTOR1").apply(Context(), module)


# TC-LKCF-007
# 功能说明: 验证 device callee 缺失时显式失败，不 silent skip。
# 使用示例: pytest -q test/passes/tuning/test_launch_kernel_cost_func.py -k test_launch_kernel_cost_func_rejects_missing_callee
# 对应功能实现文件路径: kernel_gen/passes/tuning/launch_kernel_cost_func.py
# 对应 spec 文件路径: spec/pass/tuning/launch_kernel_cost_func.md
# 对应测试文件路径: test/passes/tuning/test_launch_kernel_cost_func.py
def test_launch_kernel_cost_func_rejects_missing_callee() -> None:
    module = _build_launch_kernel_module(missing_callee=True)

    with pytest.raises(
        KernelCodeError,
        match=r"arch\.launch callee 'missing_kernel' not found",
    ):
        LaunchKernelCostFuncPass(cost_kind="VECTOR1").apply(Context(), module)


# TC-LKCF-008
# 功能说明: 验证非支持 op 会触发显式失败，而不是静默跳过。
# 使用示例: pytest -q test/passes/tuning/test_launch_kernel_cost_func.py -k test_launch_kernel_cost_func_rejects_unsupported_op
# 对应功能实现文件路径: kernel_gen/passes/tuning/launch_kernel_cost_func.py
# 对应 spec 文件路径: spec/pass/tuning/launch_kernel_cost_func.md
# 对应测试文件路径: test/passes/tuning/test_launch_kernel_cost_func.py
def test_launch_kernel_cost_func_rejects_unsupported_op() -> None:
    module = _build_launch_kernel_module(unsupported_op=True)

    with pytest.raises(
        KernelCodeError,
        match=r"unsupported op 'test\.unsupported' in device function '_device_kernel'",
    ):
        LaunchKernelCostFuncPass(cost_kind="VECTOR1").apply(Context(), module)


# TC-LKCF-009
# 功能说明: 验证预存同名 cost function 会显式失败，不覆盖已有定义。
# 使用示例: pytest -q test/passes/tuning/test_launch_kernel_cost_func.py -k test_launch_kernel_cost_func_rejects_existing_cost_func
# 对应功能实现文件路径: kernel_gen/passes/tuning/launch_kernel_cost_func.py
# 对应 spec 文件路径: spec/pass/tuning/launch_kernel_cost_func.md
# 对应测试文件路径: test/passes/tuning/test_launch_kernel_cost_func.py
def test_launch_kernel_cost_func_rejects_existing_cost_func() -> None:
    module = _build_launch_kernel_module(preexisting_cost_func=True)

    with pytest.raises(
        KernelCodeError,
        match=r"cost function '_cost_DMA1__device_kernel' already exists",
    ):
        LaunchKernelCostFuncPass(cost_kind="DMA1").apply(Context(), module)
