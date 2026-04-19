"""launch-kernel-cost-func pass tests.

创建者: 小李飞刀
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 `LaunchKernelCostFuncPass` 的成功路径、共享 callee 去重与显式失败边界。
- 锁定 `tuner.cost` metadata、`symbol.for` carried `f64` 累计与 registry 名称合同。

使用示例:
- pytest -q test/pass/test_launch_kernel_cost_func.py

关联文件:
- spec: [spec/pass/tuning/launch_kernel_cost_func.md](spec/pass/tuning/launch_kernel_cost_func.md)
- test: [test/pass/test_launch_kernel_cost_func.py](test/pass/test_launch_kernel_cost_func.py)
- 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](kernel_gen/passes/tuning/launch_kernel_cost_func.py)
"""

from __future__ import annotations

from io import StringIO
import sys
from pathlib import Path

import pytest
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, Float32Type, IntAttr, ModuleOp, StringAttr, i32
from xdsl.irdl import IRDLOperation, irdl_op_definition, result_def
from xdsl.dialects.builtin import SymbolRefAttr
from xdsl.printer import Printer
from xdsl.utils.exceptions import VerifyException

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.arch import ArchBarrierOp, ArchLaunchOp, ArchScopeAttr, ArchVisibilityAttr
from kernel_gen.dialect.kernel import KernelAddOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolConstOp, SymbolForOp, SymbolIterType, SymbolValueType
from kernel_gen.passes.registry import build_registered_pass, load_builtin_passes
from kernel_gen.passes.tuning.launch_kernel_cost_func import (
    LaunchKernelCostFuncError,
    LaunchKernelCostFuncPass,
)


@irdl_op_definition
class UnsupportedOp(IRDLOperation):
    """测试专用的非支持 op。"""

    name = "test.unsupported"
    result = result_def(i32)

    def __init__(self: "UnsupportedOp") -> None:
        super().__init__(result_types=[i32])


def _print_ir(module: ModuleOp) -> str:
    """打印 module 为稳定文本。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 为断言 `tuner.cost`、`symbol.for` 与命名规则提供稳定输出。

    使用示例:
    - text = _print_ir(module)

    关联文件:
    - spec: [spec/pass/tuning/launch_kernel_cost_func.md](spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [test/pass/test_launch_kernel_cost_func.py](test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](kernel_gen/passes/tuning/launch_kernel_cost_func.py)
    """

    stream = StringIO()
    Printer(stream=stream).print_op(module)
    return stream.getvalue()


def _make_memory_type(space: str = "global") -> NnMemoryType:
    """构造用于 pass 测试的合法 `nn.memory` 类型。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 生成固定二维 `f32` memory type，供 wrapper/device 参数与 `kernel.add` 复用。

    使用示例:
    - memory_type = _make_memory_type()

    关联文件:
    - spec: [spec/pass/tuning/launch_kernel_cost_func.md](spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [test/pass/test_launch_kernel_cost_func.py](test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](kernel_gen/passes/tuning/launch_kernel_cost_func.py)
    """

    return NnMemoryType(
        ArrayAttr([IntAttr(4), IntAttr(4)]),
        ArrayAttr([IntAttr(4), IntAttr(1)]),
        Float32Type(),
        NnMemorySpaceAttr(StringAttr(space)),
    )


def _make_barrier_visibility() -> ArrayAttr:
    """构造 `arch.barrier` 需要的 visibility 列表。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 统一生成 `[#arch.visibility<tsm>, #arch.visibility<tlm>]`。

    使用示例:
    - visibility = _make_barrier_visibility()

    关联文件:
    - spec: [spec/pass/tuning/launch_kernel_cost_func.md](spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [test/pass/test_launch_kernel_cost_func.py](test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](kernel_gen/passes/tuning/launch_kernel_cost_func.py)
    """

    return ArrayAttr(
        [ArchVisibilityAttr.from_name("tsm"), ArchVisibilityAttr.from_name("tlm")]
    )


def _build_launch_kernel_module(
    *,
    duplicate_launch: bool = False,
    conflict_attr: bool = False,
    unsupported_op: bool = False,
    missing_callee: bool = False,
    preexisting_cost_func: bool = False,
) -> ModuleOp:
    """构造含 `arch.launch -> device` 关系的最小 module。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 生成一个 wrapper 与一个 device function。
    - device body 内包含 `symbol.for`、`arch.barrier` 与 `kernel.add`，用于覆盖 move/compute 双类别成本节点。
    - 可选生成共享 callee 的第二个 wrapper，或为 `kernel.add` 注入保留 metadata attr 冲突。

    使用示例:
    - module = _build_launch_kernel_module()

    关联文件:
    - spec: [spec/pass/tuning/launch_kernel_cost_func.md](spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [test/pass/test_launch_kernel_cost_func.py](test/pass/test_launch_kernel_cost_func.py)
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
    launch_op = ArchLaunchOp(
        "_device_kernel",
        launch_block.result,
        launch_thread.result,
        launch_subthread.result,
        tuple(wrapper_block.args),
    )
    if missing_callee:
        launch_op.attributes["callee"] = SymbolRefAttr("missing_kernel")
    wrapper_block.add_ops([launch_block, launch_thread, launch_subthread, launch_op, func.ReturnOp()])

    extra_launch_block = SymbolConstOp(1)
    extra_launch_thread = SymbolConstOp(1)
    extra_launch_subthread = SymbolConstOp(1)
    extra_wrapper_block.add_ops(
        [
            extra_launch_block,
            extra_launch_thread,
            extra_launch_subthread,
            ArchLaunchOp(
                "_device_kernel",
                extra_launch_block.result,
                extra_launch_thread.result,
                extra_launch_subthread.result,
                tuple(extra_wrapper_block.args),
            ),
            func.ReturnOp(),
        ]
    )

    start = SymbolConstOp(0)
    step = SymbolConstOp(1)
    barrier = ArchBarrierOp(ArchScopeAttr.from_name("block"), _make_barrier_visibility())
    kernel_add = KernelAddOp(
        device_block.args[2],
        device_block.args[0],
        device_block.args[1],
        NnMemorySpaceAttr(StringAttr("global")),
    )
    if conflict_attr:
        kernel_add.attributes["kind"] = StringAttr("move")
    loop_block.add_op(barrier)
    if unsupported_op:
        loop_block.add_op(UnsupportedOp())
    loop_block.add_op(kernel_add)
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
        ops.append(func.FuncOp("_cost_all__device_kernel", ([], [])))
    module = ModuleOp(ops)
    return module


# TC-LKCF-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-18 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-18 00:00:00 +0800
# 功能说明: 锁定公开 pass 名称。
# 使用示例: pytest -q test/pass/test_launch_kernel_cost_func.py -k test_launch_kernel_cost_func_pass_registry_name
# 对应功能实现文件路径: kernel_gen/passes/tuning/launch_kernel_cost_func.py
# 对应 spec 文件路径: spec/pass/tuning/launch_kernel_cost_func.md
# 对应测试文件路径: test/pass/test_launch_kernel_cost_func.py
def test_launch_kernel_cost_func_pass_registry_name() -> None:
    assert LaunchKernelCostFuncPass.name == "launch-kernel-cost-func"


# TC-LKCF-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-18 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-18 00:00:00 +0800
# 功能说明: 验证 `kind="all"` 成功路径会新增 cost function，并在循环内生成 `tuner.cost + arith.addf` 累计链。
# 使用示例: pytest -q test/pass/test_launch_kernel_cost_func.py -k test_launch_kernel_cost_func_builds_cost_function_for_all_kind
# 对应功能实现文件路径: kernel_gen/passes/tuning/launch_kernel_cost_func.py
# 对应 spec 文件路径: spec/pass/tuning/launch_kernel_cost_func.md
# 对应测试文件路径: test/pass/test_launch_kernel_cost_func.py
def test_launch_kernel_cost_func_builds_cost_function_for_all_kind() -> None:
    module = _build_launch_kernel_module()

    LaunchKernelCostFuncPass(kind="all").run(module)
    module.verify()

    funcs = [op for op in module.ops if isinstance(op, func.FuncOp)]
    assert [op.sym_name.data for op in funcs] == ["wrapper", "_device_kernel", "_cost_all__device_kernel"]

    printed = _print_ir(module)
    assert "@_cost_all__device_kernel" in printed
    assert 'cost_kind = "all"' in printed
    assert 'op_name = "arch.barrier"' in printed
    assert 'op_name = "kernel.add"' in printed
    assert "symbol.for" in printed
    assert "iter_args(" in printed
    assert "symbol.yield" in printed
    assert "arith.addf" in printed
    assert printed.count("tuner.cost") == 2


# TC-LKCF-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-18 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-18 00:00:00 +0800
# 功能说明: 验证 `kind="compute"` 不裁掉 move 节点，只改 `cost_kind`。
# 使用示例: pytest -q test/pass/test_launch_kernel_cost_func.py -k test_launch_kernel_cost_func_compute_keeps_move_nodes
# 对应功能实现文件路径: kernel_gen/passes/tuning/launch_kernel_cost_func.py
# 对应 spec 文件路径: spec/pass/tuning/launch_kernel_cost_func.md
# 对应测试文件路径: test/pass/test_launch_kernel_cost_func.py
def test_launch_kernel_cost_func_compute_keeps_move_nodes() -> None:
    module = _build_launch_kernel_module()

    LaunchKernelCostFuncPass(kind="compute").run(module)

    printed = _print_ir(module)
    assert "@_cost_compute__device_kernel" in printed
    assert printed.count('cost_kind = "compute"') == 2
    assert 'kind = "move"' in printed
    assert 'kind = "compute"' in printed


# TC-LKCF-003A
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-18 02:00:00 +0800
# 最近一次运行成功时间: 2026-04-18 02:00:00 +0800
# 功能说明: 验证 `kind="move"` 成功路径会保留 compute 节点，只把 `cost_kind` 收口为 move。
# 使用示例: pytest -q test/pass/test_launch_kernel_cost_func.py -k test_launch_kernel_cost_func_move_keeps_compute_nodes
# 对应功能实现文件路径: kernel_gen/passes/tuning/launch_kernel_cost_func.py
# 对应 spec 文件路径: spec/pass/tuning/launch_kernel_cost_func.md
# 对应测试文件路径: test/pass/test_launch_kernel_cost_func.py
def test_launch_kernel_cost_func_move_keeps_compute_nodes() -> None:
    module = _build_launch_kernel_module()

    LaunchKernelCostFuncPass(kind="move").run(module)

    printed = _print_ir(module)
    assert "@_cost_move__device_kernel" in printed
    assert printed.count('cost_kind = "move"') == 2
    assert 'kind = "move"' in printed
    assert 'kind = "compute"' in printed


# TC-LKCF-004
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-18 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-18 00:00:00 +0800
# 功能说明: 验证共享 callee 时同一 `cost_kind` 仅生成一份 cost function。
# 使用示例: pytest -q test/pass/test_launch_kernel_cost_func.py -k test_launch_kernel_cost_func_shared_callee_once
# 对应功能实现文件路径: kernel_gen/passes/tuning/launch_kernel_cost_func.py
# 对应 spec 文件路径: spec/pass/tuning/launch_kernel_cost_func.md
# 对应测试文件路径: test/pass/test_launch_kernel_cost_func.py
def test_launch_kernel_cost_func_shared_callee_once() -> None:
    module = _build_launch_kernel_module(duplicate_launch=True)

    LaunchKernelCostFuncPass(kind="all").run(module)

    funcs = [op.sym_name.data for op in module.ops if isinstance(op, func.FuncOp)]
    assert funcs == ["wrapper", "wrapper_2", "_device_kernel", "_cost_all__device_kernel"]


# TC-LKCF-005A
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-18 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-18 00:00:00 +0800
# 功能说明: 验证非法 `kind` 报稳定错误短语。
# 使用示例: pytest -q test/pass/test_launch_kernel_cost_func.py -k test_launch_kernel_cost_func_rejects_invalid_kind
# 对应功能实现文件路径: kernel_gen/passes/tuning/launch_kernel_cost_func.py
# 对应 spec 文件路径: spec/pass/tuning/launch_kernel_cost_func.md
# 对应测试文件路径: test/pass/test_launch_kernel_cost_func.py
def test_launch_kernel_cost_func_rejects_invalid_kind() -> None:
    with pytest.raises(
        LaunchKernelCostFuncError,
        match=r"^LaunchKernelCostFuncError: kind must be one of compute, move, all$",
    ):
        LaunchKernelCostFuncPass(kind="invalid")


# TC-LKCF-005B
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-18 02:00:00 +0800
# 最近一次运行成功时间: 2026-04-18 02:00:00 +0800
# 功能说明: 验证 registry 构造 launch-kernel-cost-func 时不会吞掉非法 `kind` 的业务错误。
# 使用示例: pytest -q test/pass/test_launch_kernel_cost_func.py -k test_launch_kernel_cost_func_rejects_invalid_kind_via_registry
# 对应功能实现文件路径: kernel_gen/passes/registry.py
# 对应 spec 文件路径: spec/pass/registry.md
# 对应测试文件路径: test/pass/test_launch_kernel_cost_func.py
def test_launch_kernel_cost_func_rejects_invalid_kind_via_registry() -> None:
    load_builtin_passes()

    with pytest.raises(
        LaunchKernelCostFuncError,
        match=r"^LaunchKernelCostFuncError: kind must be one of compute, move, all$",
    ):
        build_registered_pass("launch-kernel-cost-func", {"kind": "invalid"})


# TC-LKCF-006
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-18 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-18 00:00:00 +0800
# 功能说明: 验证原 op metadata attr 与 pass-owned attr 冲突时显式失败。
# 使用示例: pytest -q test/pass/test_launch_kernel_cost_func.py -k test_launch_kernel_cost_func_rejects_metadata_attr_conflict
# 对应功能实现文件路径: kernel_gen/passes/tuning/launch_kernel_cost_func.py
# 对应 spec 文件路径: spec/pass/tuning/launch_kernel_cost_func.md
# 对应测试文件路径: test/pass/test_launch_kernel_cost_func.py
def test_launch_kernel_cost_func_rejects_metadata_attr_conflict() -> None:
    module = _build_launch_kernel_module(conflict_attr=True)

    with pytest.raises(
        LaunchKernelCostFuncError,
        match=r"reserved attr 'kind'$",
    ):
        LaunchKernelCostFuncPass(kind="all").run(module)


# TC-LKCF-007
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-18 02:00:00 +0800
# 最近一次运行成功时间: 2026-04-18 02:00:00 +0800
# 功能说明: 验证 device callee 缺失时显式失败，不 silent skip。
# 使用示例: pytest -q test/pass/test_launch_kernel_cost_func.py -k test_launch_kernel_cost_func_rejects_missing_callee
# 对应功能实现文件路径: kernel_gen/passes/tuning/launch_kernel_cost_func.py
# 对应 spec 文件路径: spec/pass/tuning/launch_kernel_cost_func.md
# 对应测试文件路径: test/pass/test_launch_kernel_cost_func.py
def test_launch_kernel_cost_func_rejects_missing_callee() -> None:
    module = _build_launch_kernel_module(missing_callee=True)

    with pytest.raises(
        LaunchKernelCostFuncError,
        match=r"arch\.launch callee 'missing_kernel' not found",
    ):
        LaunchKernelCostFuncPass(kind="all").run(module)


# TC-LKCF-008
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-18 02:00:00 +0800
# 最近一次运行成功时间: 2026-04-18 02:00:00 +0800
# 功能说明: 验证非支持 op 会触发显式失败，而不是静默跳过。
# 使用示例: pytest -q test/pass/test_launch_kernel_cost_func.py -k test_launch_kernel_cost_func_rejects_unsupported_op
# 对应功能实现文件路径: kernel_gen/passes/tuning/launch_kernel_cost_func.py
# 对应 spec 文件路径: spec/pass/tuning/launch_kernel_cost_func.md
# 对应测试文件路径: test/pass/test_launch_kernel_cost_func.py
def test_launch_kernel_cost_func_rejects_unsupported_op() -> None:
    module = _build_launch_kernel_module(unsupported_op=True)

    with pytest.raises(
        LaunchKernelCostFuncError,
        match=r"unsupported op 'test\.unsupported' in device function '_device_kernel'",
    ):
        LaunchKernelCostFuncPass(kind="all").run(module)


# TC-LKCF-009
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-18 02:00:00 +0800
# 最近一次运行成功时间: 2026-04-18 02:00:00 +0800
# 功能说明: 验证预存同名 cost function 会显式失败，不覆盖已有定义。
# 使用示例: pytest -q test/pass/test_launch_kernel_cost_func.py -k test_launch_kernel_cost_func_rejects_existing_cost_func
# 对应功能实现文件路径: kernel_gen/passes/tuning/launch_kernel_cost_func.py
# 对应 spec 文件路径: spec/pass/tuning/launch_kernel_cost_func.md
# 对应测试文件路径: test/pass/test_launch_kernel_cost_func.py
def test_launch_kernel_cost_func_rejects_existing_cost_func() -> None:
    module = _build_launch_kernel_module(preexisting_cost_func=True)

    with pytest.raises(
        LaunchKernelCostFuncError,
        match=r"cost function '_cost_all__device_kernel' already exists",
    ):
        LaunchKernelCostFuncPass(kind="all").run(module)
