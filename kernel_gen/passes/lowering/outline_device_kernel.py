"""outline-device-kernel lowering pass.

创建者: 朽木露琪亚
最后一次更改: 金铲铲大作战

功能说明:
- 为带显式 launch 属性的 `func.func` 执行 host-launch outline。
- 把原函数改写为只包含 `symbol.const + arch.launch + func.return` 的 host wrapper。
- 把原函数体搬移到新的 `@<name>_device`，并只在 device 侧保留 `shared_memory_size`。

使用示例:
- from xdsl.dialects.builtin import ModuleOp
- from kernel_gen.passes.lowering.outline_device_kernel import OutlineDeviceKernelPass
- module = ModuleOp([])
- assert OutlineDeviceKernelPass().run(module) is module

关联文件:
- spec: [spec/pass/lowering/outline_device_kernel.md](spec/pass/lowering/outline_device_kernel.md)
- test: [test/pass/test_outline_device_kernel.py](test/pass/test_outline_device_kernel.py)
- 功能实现: [kernel_gen/passes/lowering/outline_device_kernel.py](kernel_gen/passes/lowering/outline_device_kernel.py)
"""

from __future__ import annotations

from dataclasses import dataclass

from xdsl.dialects import func
from xdsl.dialects.builtin import IntAttr, IntegerAttr, ModuleOp, StringAttr
from xdsl.ir import Attribute, Block, Region

from kernel_gen.dialect.arch import ArchLaunchOp
from kernel_gen.dialect.symbol import SymbolConstOp
from kernel_gen.passes.pass_manager import Pass

_LAUNCH_ATTRS = ("launch_block", "launch_thread", "launch_subthread")


class OutlineDeviceKernelError(ValueError):
    """outline-device-kernel pass 的稳定错误类型。

    创建者: 朽木露琪亚
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一承载 outline 过程中的显式失败路径。
    - 保持错误前缀稳定，便于测试与 expectation 做机械匹配。

    使用示例:
    - raise OutlineDeviceKernelError("OutlineDeviceKernelError: module must be builtin.module")

    关联文件:
    - spec: [spec/pass/lowering/outline_device_kernel.md](spec/pass/lowering/outline_device_kernel.md)
    - test: [test/pass/test_outline_device_kernel.py](test/pass/test_outline_device_kernel.py)
    - 功能实现: [kernel_gen/passes/lowering/outline_device_kernel.py](kernel_gen/passes/lowering/outline_device_kernel.py)
    """


@dataclass(frozen=True)
class _OutlineCandidate:
    """记录待 outline 的函数与已规整的 launch extent。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 在正式改写前固定函数对象、device 名称与三层 launch extent。
    - 让校验与改写分离，避免失败路径产生半改写状态。

    使用示例:
    - candidate = _OutlineCandidate(func_op=func_op, device_name="kernel_device", block=1, thread=4, subthread=1)

    关联文件:
    - spec: [spec/pass/lowering/outline_device_kernel.md](spec/pass/lowering/outline_device_kernel.md)
    - test: [test/pass/test_outline_device_kernel.py](test/pass/test_outline_device_kernel.py)
    - 功能实现: [kernel_gen/passes/lowering/outline_device_kernel.py](kernel_gen/passes/lowering/outline_device_kernel.py)
    """

    func_op: func.FuncOp
    device_name: str
    block: int
    thread: int
    subthread: int


def _normalize_positive_int_attr(attr_name: str, attr: Attribute, func_name: str) -> int:
    """把函数属性规整为正整数 launch extent。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 `IntAttr`、`IntegerAttr` 与可转整数的 `StringAttr`。
    - 对非整数或非正数语义抛出稳定错误短语。

    使用示例:
    - value = _normalize_positive_int_attr("launch_thread", IntAttr(4), "kernel")

    关联文件:
    - spec: [spec/pass/lowering/outline_device_kernel.md](spec/pass/lowering/outline_device_kernel.md)
    - test: [test/pass/test_outline_device_kernel.py](test/pass/test_outline_device_kernel.py)
    - 功能实现: [kernel_gen/passes/lowering/outline_device_kernel.py](kernel_gen/passes/lowering/outline_device_kernel.py)
    """

    if isinstance(attr, IntAttr):
        value = attr.data
    elif isinstance(attr, IntegerAttr):
        value = attr.value.data
    elif isinstance(attr, StringAttr):
        try:
            value = int(attr.data)
        except ValueError as exc:
            raise OutlineDeviceKernelError(
                f"OutlineDeviceKernelError: function {func_name} {attr_name} must be int-like attribute"
            ) from exc
    else:
        raise OutlineDeviceKernelError(
            f"OutlineDeviceKernelError: function {func_name} {attr_name} must be int-like attribute"
        )
    if value <= 0:
        raise OutlineDeviceKernelError(
            f"OutlineDeviceKernelError: function {func_name} {attr_name} must be > 0"
        )
    return value


def _collect_outline_candidate(
    func_op: func.FuncOp,
    existing_names: set[str],
) -> _OutlineCandidate | None:
    """收集单个 `func.func` 的 outline 候选信息。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 只对显式出现 launch 属性的函数做校验与候选收集。
    - 锁定零返回、完整属性组与 `_device` 命名冲突等公开边界。

    使用示例:
    - candidate = _collect_outline_candidate(func_op, {"kernel", "helper"})

    关联文件:
    - spec: [spec/pass/lowering/outline_device_kernel.md](spec/pass/lowering/outline_device_kernel.md)
    - test: [test/pass/test_outline_device_kernel.py](test/pass/test_outline_device_kernel.py)
    - 功能实现: [kernel_gen/passes/lowering/outline_device_kernel.py](kernel_gen/passes/lowering/outline_device_kernel.py)
    """

    present_attrs = [name for name in _LAUNCH_ATTRS if name in func_op.attributes]
    if not present_attrs:
        return None
    func_name = func_op.sym_name.data
    if len(present_attrs) != len(_LAUNCH_ATTRS):
        raise OutlineDeviceKernelError(
            "OutlineDeviceKernelError: function "
            f"{func_name} must define launch_block, launch_thread, and launch_subthread together"
        )
    if len(func_op.function_type.outputs.data) != 0:
        raise OutlineDeviceKernelError(f"OutlineDeviceKernelError: function {func_name} must have zero results")
    if not any(True for _ in func_op.body.blocks):
        raise OutlineDeviceKernelError(f"OutlineDeviceKernelError: function {func_name} must contain a body")

    device_name = f"{func_name}_device"
    if device_name in existing_names:
        raise OutlineDeviceKernelError(
            f"OutlineDeviceKernelError: outlined device function '{device_name}' already exists"
        )

    return _OutlineCandidate(
        func_op=func_op,
        device_name=device_name,
        block=_normalize_positive_int_attr("launch_block", func_op.attributes["launch_block"], func_name),
        thread=_normalize_positive_int_attr("launch_thread", func_op.attributes["launch_thread"], func_name),
        subthread=_normalize_positive_int_attr("launch_subthread", func_op.attributes["launch_subthread"], func_name),
    )


def _build_wrapper_attrs(attributes: dict[str, Attribute]) -> dict[str, Attribute]:
    """生成 wrapper 保留的函数属性字典。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 移除三项 launch trigger attrs。
    - 同时移除 `shared_memory_size`，把该 metadata 仅保留在 device function。

    使用示例:
    - wrapper_attrs = _build_wrapper_attrs(dict(func_op.attributes))

    关联文件:
    - spec: [spec/pass/lowering/outline_device_kernel.md](spec/pass/lowering/outline_device_kernel.md)
    - test: [test/pass/test_outline_device_kernel.py](test/pass/test_outline_device_kernel.py)
    - 功能实现: [kernel_gen/passes/lowering/outline_device_kernel.py](kernel_gen/passes/lowering/outline_device_kernel.py)
    """

    return {
        name: attr
        for name, attr in attributes.items()
        if name not in _LAUNCH_ATTRS and name != "shared_memory_size"
    }


def _build_device_attrs(attributes: dict[str, Attribute]) -> dict[str, Attribute]:
    """生成 device function 保留的函数属性字典。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 只移除三项 launch trigger attrs。
    - 保留 `shared_memory_size` 以及其他原函数元数据。

    使用示例:
    - device_attrs = _build_device_attrs(dict(func_op.attributes))

    关联文件:
    - spec: [spec/pass/lowering/outline_device_kernel.md](spec/pass/lowering/outline_device_kernel.md)
    - test: [test/pass/test_outline_device_kernel.py](test/pass/test_outline_device_kernel.py)
    - 功能实现: [kernel_gen/passes/lowering/outline_device_kernel.py](kernel_gen/passes/lowering/outline_device_kernel.py)
    """

    return {name: attr for name, attr in attributes.items() if name not in _LAUNCH_ATTRS}


def _build_wrapper_block(candidate: _OutlineCandidate) -> Block:
    """构造 host wrapper 的唯一 entry block。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 以原参数类型生成新 block 参数。
    - 固定插入 `symbol.const` 三元组、单个 `arch.launch` 与空 `func.return`。

    使用示例:
    - block = _build_wrapper_block(candidate)

    关联文件:
    - spec: [spec/pass/lowering/outline_device_kernel.md](spec/pass/lowering/outline_device_kernel.md)
    - test: [test/pass/test_outline_device_kernel.py](test/pass/test_outline_device_kernel.py)
    - 功能实现: [kernel_gen/passes/lowering/outline_device_kernel.py](kernel_gen/passes/lowering/outline_device_kernel.py)
    """

    input_types = list(candidate.func_op.function_type.inputs.data)
    wrapper_block = Block(arg_types=input_types)
    block_const = SymbolConstOp(candidate.block)
    thread_const = SymbolConstOp(candidate.thread)
    subthread_const = SymbolConstOp(candidate.subthread)
    launch = ArchLaunchOp(
        candidate.device_name,
        block_const.result,
        thread_const.result,
        subthread_const.result,
        tuple(wrapper_block.args),
    )
    wrapper_block.add_ops([block_const, thread_const, subthread_const, launch, func.ReturnOp()])
    return wrapper_block


def _outline_function(module: ModuleOp, candidate: _OutlineCandidate) -> None:
    """把单个候选函数改写为 `wrapper + device body`。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 把原函数体 region 搬移到新的 `@<name>_device`。
    - 原函数本身改写为 host wrapper，并在模块中紧随其后插入 device function。

    使用示例:
    - _outline_function(module, candidate)

    关联文件:
    - spec: [spec/pass/lowering/outline_device_kernel.md](spec/pass/lowering/outline_device_kernel.md)
    - test: [test/pass/test_outline_device_kernel.py](test/pass/test_outline_device_kernel.py)
    - 功能实现: [kernel_gen/passes/lowering/outline_device_kernel.py](kernel_gen/passes/lowering/outline_device_kernel.py)
    """

    func_op = candidate.func_op
    input_types = list(func_op.function_type.inputs.data)
    output_types = list(func_op.function_type.outputs.data)
    original_attrs = dict(func_op.attributes)
    device_region = Region()
    func_op.body.move_blocks(device_region)

    device_func = func.FuncOp(
        candidate.device_name,
        (input_types, output_types),
        device_region,
        visibility=getattr(func_op, "sym_visibility", None),
        arg_attrs=func_op.arg_attrs,
        res_attrs=func_op.res_attrs,
    )
    device_func.attributes.update(_build_device_attrs(original_attrs))

    func_op.attributes.clear()
    func_op.attributes.update(_build_wrapper_attrs(original_attrs))
    func_op.body.add_block(_build_wrapper_block(candidate))
    module.body.block.insert_op_after(device_func, func_op)


class OutlineDeviceKernelPass(Pass):
    """outline-device-kernel pass。

    创建者: 朽木露琪亚
    最后一次更改: 金铲铲大作战

    功能说明:
    - 固定公开名称为 `outline-device-kernel`。
    - 对带显式 launch 属性的零返回函数执行 host-launch outline。
    - 保持未标记函数原样不变，且不并入默认 pipeline。

    使用示例:
    - module = OutlineDeviceKernelPass().run(ModuleOp([]))

    关联文件:
    - spec: [spec/pass/lowering/outline_device_kernel.md](spec/pass/lowering/outline_device_kernel.md)
    - test: [test/pass/test_outline_device_kernel.py](test/pass/test_outline_device_kernel.py)
    - 功能实现: [kernel_gen/passes/lowering/outline_device_kernel.py](kernel_gen/passes/lowering/outline_device_kernel.py)
    """

    name = "outline-device-kernel"

    def run(self: "OutlineDeviceKernelPass", module: object) -> ModuleOp:
        """执行 outline-device-kernel pass。

        创建者: 朽木露琪亚
        最后一次更改: 金铲铲大作战

        功能说明:
        - 仅接受 `builtin.module` 作为 pass 输入。
        - 先收集并校验所有待 outline 函数，再统一执行改写。

        使用示例:
        - module = ModuleOp([])
        - same_module = OutlineDeviceKernelPass().run(module)

        关联文件:
        - spec: [spec/pass/lowering/outline_device_kernel.md](spec/pass/lowering/outline_device_kernel.md)
        - test: [test/pass/test_outline_device_kernel.py](test/pass/test_outline_device_kernel.py)
        - 功能实现: [kernel_gen/passes/lowering/outline_device_kernel.py](kernel_gen/passes/lowering/outline_device_kernel.py)
        """

        if not isinstance(module, ModuleOp):
            raise OutlineDeviceKernelError("OutlineDeviceKernelError: module must be builtin.module")
        if not any(True for _ in module.ops):
            return module
        existing_names = {op.sym_name.data for op in module.ops if isinstance(op, func.FuncOp)}
        candidates: list[_OutlineCandidate] = []
        for op in module.ops:
            if not isinstance(op, func.FuncOp):
                continue
            candidate = _collect_outline_candidate(op, existing_names)
            if candidate is not None:
                candidates.append(candidate)
        for candidate in candidates:
            _outline_function(module, candidate)
        return module


__all__ = ["OutlineDeviceKernelError", "OutlineDeviceKernelPass"]
