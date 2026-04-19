"""launch-kernel-cost-func tuning pass.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 为 module 中被 `arch.launch` 引用的 device function 生成 sibling cost function。
- 在 cost function 中保留 `symbol.for` 结构，复制必要的 helper op，并为 `dma/kernel/arch` op 生成 `tuner.cost` 与 `f64` 累计链。
- 保持原 host wrapper 与原 device function 不变。

使用示例:
- from kernel_gen.passes.tuning.launch_kernel_cost_func import LaunchKernelCostFuncPass
- module = LaunchKernelCostFuncPass(kind="all").run(module)

关联文件:
- spec: [spec/pass/tuning/launch_kernel_cost_func.md](spec/pass/tuning/launch_kernel_cost_func.md)
- test: [test/pass/test_launch_kernel_cost_func.py](test/pass/test_launch_kernel_cost_func.py)
- 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](kernel_gen/passes/tuning/launch_kernel_cost_func.py)
"""

from __future__ import annotations

from collections.abc import Sequence

from xdsl.dialects import arith, func
from xdsl.dialects.builtin import FloatAttr, ModuleOp, StringAttr, SymbolRefAttr, f64
from xdsl.ir import Block, Operation, Region, SSAValue

from kernel_gen.dialect.arch import ArchLaunchOp
from kernel_gen.dialect.symbol import SymbolForOp, SymbolYieldOp
from kernel_gen.dialect.tuner import TunerCostOp
from kernel_gen.passes.pass_manager import Pass

_VALID_COST_KINDS = ("compute", "move", "all")
_RESERVED_METADATA_ATTRS = ("kind", "cost_kind", "op_name", "device_func")
_SUPPORTED_PREFIX_TO_KIND = {
    "dma.": "move",
    "kernel.": "compute",
    "arch.": "move",
}


class LaunchKernelCostFuncError(ValueError):
    """launch-kernel-cost-func pass 的稳定错误类型。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 承载当前 pass 的稳定失败路径。
    - 为非法 `kind`、callee 缺失、重名 cost function、metadata attr 冲突与非支持 op 等边界提供统一错误类型。

    使用示例:
    - raise LaunchKernelCostFuncError("LaunchKernelCostFuncError: kind must be one of compute, move, all")

    关联文件:
    - spec: [spec/pass/tuning/launch_kernel_cost_func.md](spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [test/pass/test_launch_kernel_cost_func.py](test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](kernel_gen/passes/tuning/launch_kernel_cost_func.py)
    """


def _normalize_cost_kind(kind: str) -> str:
    """规整并校验 pass `kind` 参数。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 只接受 `compute`、`move`、`all` 三种公开值。
    - 失败时抛出稳定错误短语，便于 registry 与 pytest 做机械匹配。

    使用示例:
    - cost_kind = _normalize_cost_kind("all")

    关联文件:
    - spec: [spec/pass/tuning/launch_kernel_cost_func.md](spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [test/pass/test_launch_kernel_cost_func.py](test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](kernel_gen/passes/tuning/launch_kernel_cost_func.py)
    """

    if kind not in _VALID_COST_KINDS:
        raise LaunchKernelCostFuncError(
            "LaunchKernelCostFuncError: kind must be one of compute, move, all"
        )
    return kind


def _cost_function_name(cost_kind: str, device_func_name: str) -> str:
    """返回公开 cost function 名称。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 固定命名规则为 `@_cost_<cost_kind>_<device_func_name>` 对应的 symbol 名。

    使用示例:
    - name = _cost_function_name("all", "_device_kernel")

    关联文件:
    - spec: [spec/pass/tuning/launch_kernel_cost_func.md](spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [test/pass/test_launch_kernel_cost_func.py](test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](kernel_gen/passes/tuning/launch_kernel_cost_func.py)
    """

    return f"_cost_{cost_kind}_{device_func_name}"


def _clone_op_into_block(
    op: Operation,
    target_block: Block,
    value_mapper: dict[SSAValue, SSAValue],
) -> Operation:
    """把源 op 克隆到目标 block，并同步 SSA 映射。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 复用 xdsl `Operation.clone(...)` 把 helper op 或带结果的受支持 op 复制到 cost function。
    - 更新源结果到新结果的映射，供后续 operands 重写使用。

    使用示例:
    - cloned = _clone_op_into_block(op, block, value_mapper)

    关联文件:
    - spec: [spec/pass/tuning/launch_kernel_cost_func.md](spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [test/pass/test_launch_kernel_cost_func.py](test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](kernel_gen/passes/tuning/launch_kernel_cost_func.py)
    """

    cloned = op.clone(value_mapper=value_mapper)
    target_block.add_op(cloned)
    for source_result, cloned_result in zip(op.results, cloned.results, strict=True):
        value_mapper[source_result] = cloned_result
    return cloned


def _is_skip_op(op: Operation) -> bool:
    """判断 op 是否属于“复制但不生成 tuner.cost”的 helper 集合。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - `arith.constant`、非循环结构的 `symbol.*` 与 `func.return` 仅作为 cost function 的辅助结构。
    - `symbol.for` 单独走专门改写逻辑，不在这里处理。

    使用示例:
    - if _is_skip_op(op): ...

    关联文件:
    - spec: [spec/pass/tuning/launch_kernel_cost_func.md](spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [test/pass/test_launch_kernel_cost_func.py](test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](kernel_gen/passes/tuning/launch_kernel_cost_func.py)
    """

    if isinstance(op, func.ReturnOp):
        return True
    if op.name == "arith.constant":
        return True
    if op.name.startswith("symbol.") and not isinstance(op, SymbolForOp):
        return True
    return False


def _classify_supported_op(op: Operation) -> str | None:
    """返回受支持成本 op 的公开 `kind`。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 把 `dma.*`、`kernel.*`、`arch.*` 映射为 `move / compute / move`。
    - 其余 op 返回 `None`，由调用方决定是 helper 还是显式失败。

    使用示例:
    - kind = _classify_supported_op(op)

    关联文件:
    - spec: [spec/pass/tuning/launch_kernel_cost_func.md](spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [test/pass/test_launch_kernel_cost_func.py](test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](kernel_gen/passes/tuning/launch_kernel_cost_func.py)
    """

    for prefix, kind in _SUPPORTED_PREFIX_TO_KIND.items():
        if op.name.startswith(prefix):
            return kind
    return None


def _mapped_operands(
    operands: Sequence[SSAValue],
    value_mapper: dict[SSAValue, SSAValue],
) -> list[SSAValue]:
    """按当前 SSA 映射重写 op operands。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 把源 device function 中的 SSA 使用点映射到 cost function 内的新定义。

    使用示例:
    - operands = _mapped_operands(op.operands, value_mapper)

    关联文件:
    - spec: [spec/pass/tuning/launch_kernel_cost_func.md](spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [test/pass/test_launch_kernel_cost_func.py](test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](kernel_gen/passes/tuning/launch_kernel_cost_func.py)
    """

    return [value_mapper.get(operand, operand) for operand in operands]


def _build_cost_node(
    op: Operation,
    value_mapper: dict[SSAValue, SSAValue],
    device_func_name: str,
    cost_kind: str,
) -> TunerCostOp:
    """为单个源 op 构造 `tuner.cost(...)->f64`。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 透传原 op operands。
    - 平铺保留原 op attrs，并补齐 `kind/cost_kind/op_name/device_func`。
    - 在 metadata attr 冲突时显式失败。

    使用示例:
    - cost_op = _build_cost_node(op, value_mapper, "_device_kernel", "all")

    关联文件:
    - spec: [spec/pass/tuning/launch_kernel_cost_func.md](spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [test/pass/test_launch_kernel_cost_func.py](test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](kernel_gen/passes/tuning/launch_kernel_cost_func.py)
    """

    op_kind = _classify_supported_op(op)
    assert op_kind is not None
    extra_attrs = dict(op.attributes)
    if op.name == "kernel.binary_elewise" and "kind" in extra_attrs:
        extra_attrs["kernel_kind"] = extra_attrs.pop("kind")
    for attr_name in _RESERVED_METADATA_ATTRS:
        if attr_name in extra_attrs:
            raise LaunchKernelCostFuncError(
                "LaunchKernelCostFuncError: "
                f"op '{op.name}' in device function '{device_func_name}' already defines reserved attr '{attr_name}'"
            )
    return TunerCostOp(
        _mapped_operands(op.operands, value_mapper),
        kind=StringAttr(op_kind),
        cost_kind=StringAttr(cost_kind),
        op_name=StringAttr(op.name),
        device_func=SymbolRefAttr(device_func_name),
        extra_attrs=extra_attrs,
    )


def _rewrite_block(
    source_block: Block,
    target_block: Block,
    value_mapper: dict[SSAValue, SSAValue],
    acc_value: SSAValue,
    *,
    device_func_name: str,
    cost_kind: str,
) -> SSAValue:
    """把源 block 改写到 cost function block，并返回最新累计值。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 复制 helper op。
    - 为受支持 op 生成 `tuner.cost + arith.addf`。
    - 为 `symbol.for` 递归生成 carried `f64` 累计结构。

    使用示例:
    - acc = _rewrite_block(src_block, dst_block, value_mapper, zero.result, device_func_name="_device_kernel", cost_kind="all")

    关联文件:
    - spec: [spec/pass/tuning/launch_kernel_cost_func.md](spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [test/pass/test_launch_kernel_cost_func.py](test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](kernel_gen/passes/tuning/launch_kernel_cost_func.py)
    """

    for op in source_block.ops:
        if isinstance(op, SymbolForOp):
            if op.init is not None or op.result is not None:
                raise LaunchKernelCostFuncError(
                    "LaunchKernelCostFuncError: source symbol.for must not already carry f64 result"
                )
            inner_source_block = op.body.block
            inner_block = Block(arg_types=[inner_source_block.args[0].type, f64])
            inner_mapper = dict(value_mapper)
            inner_mapper[inner_source_block.args[0]] = inner_block.args[0]
            loop_op = SymbolForOp(
                value_mapper.get(op.start, op.start),
                value_mapper.get(op.end, op.end),
                value_mapper.get(op.step, op.step),
                Region(inner_block),
                iter_attr=op.iter_attr,
                init=acc_value,
            )
            target_block.add_op(loop_op)
            loop_acc = _rewrite_block(
                inner_source_block,
                inner_block,
                inner_mapper,
                inner_block.args[1],
                device_func_name=device_func_name,
                cost_kind=cost_kind,
            )
            inner_block.add_op(SymbolYieldOp(loop_acc))
            assert loop_op.result is not None
            acc_value = loop_op.result
            continue
        if _is_skip_op(op):
            if not isinstance(op, func.ReturnOp):
                _clone_op_into_block(op, target_block, value_mapper)
            continue
        if _classify_supported_op(op) is None:
            raise LaunchKernelCostFuncError(
                f"LaunchKernelCostFuncError: unsupported op '{op.name}' in device function '{device_func_name}'"
            )
        if len(op.results) != 0:
            _clone_op_into_block(op, target_block, value_mapper)
        cost_op = _build_cost_node(op, value_mapper, device_func_name, cost_kind)
        target_block.add_op(cost_op)
        add_op = arith.AddfOp(acc_value, cost_op.result, result_type=f64)
        target_block.add_op(add_op)
        acc_value = add_op.result
    return acc_value


def _build_cost_function(device_func: func.FuncOp, cost_kind: str) -> func.FuncOp:
    """从单个 device function 生成 cost function。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 复制 device 参数列表。
    - 以 `arith.constant 0.0 : f64` 作为累计初值。
    - 调用 `_rewrite_block(...)` 重建 body，并以单个 `f64` 返回总成本。

    使用示例:
    - cost_func = _build_cost_function(device_func, "all")

    关联文件:
    - spec: [spec/pass/tuning/launch_kernel_cost_func.md](spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [test/pass/test_launch_kernel_cost_func.py](test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](kernel_gen/passes/tuning/launch_kernel_cost_func.py)
    """

    source_blocks = list(device_func.body.blocks)
    if len(source_blocks) != 1:
        raise LaunchKernelCostFuncError(
            f"LaunchKernelCostFuncError: device function '{device_func.sym_name.data}' must contain single block"
        )
    input_types = list(device_func.function_type.inputs.data)
    cost_block = Block(arg_types=input_types)
    zero = arith.ConstantOp(FloatAttr(0.0, f64))
    cost_block.add_op(zero)
    value_mapper = {
        source_arg: cost_arg
        for source_arg, cost_arg in zip(source_blocks[0].args, cost_block.args, strict=True)
    }
    acc_value = _rewrite_block(
        source_blocks[0],
        cost_block,
        value_mapper,
        zero.result,
        device_func_name=device_func.sym_name.data,
        cost_kind=cost_kind,
    )
    cost_block.add_op(func.ReturnOp(acc_value))
    return func.FuncOp(
        _cost_function_name(cost_kind, device_func.sym_name.data),
        (input_types, [f64]),
        Region(cost_block),
        visibility=getattr(device_func, "sym_visibility", None),
        arg_attrs=device_func.arg_attrs,
    )


def _collect_device_functions(module: ModuleOp) -> list[func.FuncOp]:
    """按首次出现顺序收集被 `arch.launch` 调用的 device function。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 解析 `arch.launch` 的 callee symbol。
    - 同一 device callee 只保留一份，满足共享 callee 去重合同。

    使用示例:
    - devices = _collect_device_functions(module)

    关联文件:
    - spec: [spec/pass/tuning/launch_kernel_cost_func.md](spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [test/pass/test_launch_kernel_cost_func.py](test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](kernel_gen/passes/tuning/launch_kernel_cost_func.py)
    """

    func_by_name = {op.sym_name.data: op for op in module.ops if isinstance(op, func.FuncOp)}
    ordered_devices: list[func.FuncOp] = []
    seen: set[str] = set()
    for op in module.walk():
        if not isinstance(op, ArchLaunchOp):
            continue
        callee_name = op.callee.root_reference.data
        device_func = func_by_name.get(callee_name)
        if device_func is None:
            raise LaunchKernelCostFuncError(
                f"LaunchKernelCostFuncError: arch.launch callee '{callee_name}' not found"
            )
        if callee_name in seen:
            continue
        seen.add(callee_name)
        ordered_devices.append(device_func)
    return ordered_devices


class LaunchKernelCostFuncPass(Pass):
    """launch-kernel-cost-func pass。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 固定公开名称为 `launch-kernel-cost-func`。
    - 从 `arch.launch -> device func` 关系生成 sibling cost function。
    - 不改写原 host wrapper 与原 device function。

    使用示例:
    - module = LaunchKernelCostFuncPass(kind="all").run(module)

    关联文件:
    - spec: [spec/pass/tuning/launch_kernel_cost_func.md](spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [test/pass/test_launch_kernel_cost_func.py](test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](kernel_gen/passes/tuning/launch_kernel_cost_func.py)
    """

    name = "launch-kernel-cost-func"

    def __init__(self: "LaunchKernelCostFuncPass", kind: str = "all") -> None:
        """初始化 pass 选项。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 记录当前 cost function 的统计视角。

        使用示例:
        - pass_obj = LaunchKernelCostFuncPass(kind="move")

        关联文件:
        - spec: [spec/pass/tuning/launch_kernel_cost_func.md](spec/pass/tuning/launch_kernel_cost_func.md)
        - test: [test/pass/test_launch_kernel_cost_func.py](test/pass/test_launch_kernel_cost_func.py)
        - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](kernel_gen/passes/tuning/launch_kernel_cost_func.py)
        """

        self.kind = _normalize_cost_kind(kind)

    @classmethod
    def from_options(
        cls: type["LaunchKernelCostFuncPass"], options: dict[str, str]
    ) -> "LaunchKernelCostFuncPass":
        """从 registry options 构造 pass。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 支持 `{"kind": "compute|move|all"}` 形式的 registry 入口。
        - 拒绝未知选项，避免静默吞参。

        使用示例:
        - pass_obj = LaunchKernelCostFuncPass.from_options({"kind": "all"})

        关联文件:
        - spec: [spec/pass/tuning/launch_kernel_cost_func.md](spec/pass/tuning/launch_kernel_cost_func.md)
        - test: [test/pass/test_launch_kernel_cost_func.py](test/pass/test_launch_kernel_cost_func.py)
        - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](kernel_gen/passes/tuning/launch_kernel_cost_func.py)
        """

        unknown = sorted(set(options) - {"kind"})
        if unknown:
            raise LaunchKernelCostFuncError(
                f"LaunchKernelCostFuncError: unknown option(s): {', '.join(unknown)}"
            )
        return cls(kind=options.get("kind", "all"))

    def run(self: "LaunchKernelCostFuncPass", module: object) -> ModuleOp:
        """执行 launch-kernel-cost-func pass。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - 校验 module 输入与 `kind`。
        - 收集 unique device callee 并插入对应 cost function。
        - 若发现重名 cost function，显式失败并保持 module 原样。

        使用示例:
        - module = LaunchKernelCostFuncPass(kind="all").run(module)

        关联文件:
        - spec: [spec/pass/tuning/launch_kernel_cost_func.md](spec/pass/tuning/launch_kernel_cost_func.md)
        - test: [test/pass/test_launch_kernel_cost_func.py](test/pass/test_launch_kernel_cost_func.py)
        - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](kernel_gen/passes/tuning/launch_kernel_cost_func.py)
        """

        if not isinstance(module, ModuleOp):
            raise LaunchKernelCostFuncError("LaunchKernelCostFuncError: module must be builtin.module")
        device_funcs = _collect_device_functions(module)
        if not device_funcs:
            return module
        existing_names = {op.sym_name.data for op in module.ops if isinstance(op, func.FuncOp)}
        for device_func in device_funcs:
            cost_name = _cost_function_name(self.kind, device_func.sym_name.data)
            if cost_name in existing_names:
                raise LaunchKernelCostFuncError(
                    f"LaunchKernelCostFuncError: cost function '{cost_name}' already exists"
                )
            existing_names.add(cost_name)
        for device_func in device_funcs:
            cost_func = _build_cost_function(device_func, self.kind)
            module.body.block.insert_op_after(cost_func, device_func)
        return module


__all__ = ["LaunchKernelCostFuncError", "LaunchKernelCostFuncPass"]
