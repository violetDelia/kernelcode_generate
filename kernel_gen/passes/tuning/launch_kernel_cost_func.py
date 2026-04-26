"""launch-kernel-cost-func tuning pass.

创建者: 小李飞刀
最后一次更改: OpenAI Codex

功能说明:
- 为 module 中被 `arch.launch` 引用的 device function 生成 sibling cost function。
- 在 cost function 中保留 `symbol.for` 结构，复制必要 helper op，并为 `dma/kernel/arch` op 生成 `tuner.cost` 与 `symbol.add` 累计链。
- 保持原 host wrapper 与原 device function 不变；当前文件不公开 helper 函数或 helper 类，重写细节只属于 `LaunchKernelCostFuncPass.run(...)` 内部实现。

使用示例:
- from kernel_gen.passes.tuning.launch_kernel_cost_func import LaunchKernelCostFuncPass
- module = LaunchKernelCostFuncPass(cost_kind="compute|latency|bandwidth").run(module)

关联文件:
- spec: [spec/pass/tuning/launch_kernel_cost_func.md](../../../spec/pass/tuning/launch_kernel_cost_func.md)
- test: [test/pass/test_launch_kernel_cost_func.py](../../../test/pass/test_launch_kernel_cost_func.py)
- 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](../../../kernel_gen/passes/tuning/launch_kernel_cost_func.py)
"""

from __future__ import annotations

from xdsl.dialects import func
from xdsl.dialects.builtin import ModuleOp, StringAttr
from xdsl.ir import Block, Region, SSAValue

from kernel_gen.dialect.arch import ArchLaunchOp
from kernel_gen.dialect.symbol import SymbolAddOp, SymbolConstOp, SymbolForOp, SymbolYieldOp
from kernel_gen.dialect.tuner import TunerCostOp
from kernel_gen.passes.common import raise_pass_contract_error, verify_generated_ops
from kernel_gen.passes.pass_manager import Pass

RESERVED_METADATA_ATTRS = ("kind", "cost_kind", "op_name", "device_func")
SUPPORTED_COST_PREFIXES = ("dma.", "kernel.", "arch.")
HELPER_OP_NAMES = ("dma.view", "dma.reshape")
INVALID_COST_KIND_DETAIL = "cost_kind must be a non-empty '|' separated list of unique kind names"


class LaunchKernelCostFuncPass(Pass):
    """launch-kernel-cost-func pass。

    创建者: 小李飞刀
    最后一次更改: OpenAI Codex

    功能说明:
    - 固定公开名称为 `launch-kernel-cost-func`。
    - 从 `arch.launch -> device func` 关系生成 sibling cost function。
    - `cost_kind` 接受任意非空、`|` 分隔且去重后的 kind 名列表。

    使用示例:
    - from kernel_gen.passes.tuning.launch_kernel_cost_func import LaunchKernelCostFuncPass
    - module = LaunchKernelCostFuncPass(cost_kind="compute|memory|latency").run(module)

    关联文件:
    - spec: [spec/pass/tuning/launch_kernel_cost_func.md](../../../spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [test/pass/test_launch_kernel_cost_func.py](../../../test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](../../../kernel_gen/passes/tuning/launch_kernel_cost_func.py)
    """

    name = "launch-kernel-cost-func"

    def __init__(self: "LaunchKernelCostFuncPass", cost_kind: str = "compute") -> None:
        """初始化 pass 选项。

        创建者: 小李飞刀
        最后一次更改: OpenAI Codex

        功能说明:
        - 记录公开 `cost_kind` 字符串。
        - 规整并缓存内部执行所需的 kind 列表顺序。

        使用示例:
        - pass_obj = LaunchKernelCostFuncPass(cost_kind="compute|memory|latency")

        关联文件:
        - spec: [spec/pass/tuning/launch_kernel_cost_func.md](../../../spec/pass/tuning/launch_kernel_cost_func.md)
        - test: [test/pass/test_launch_kernel_cost_func.py](../../../test/pass/test_launch_kernel_cost_func.py)
        - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](../../../kernel_gen/passes/tuning/launch_kernel_cost_func.py)
        """

        if not cost_kind:
            raise_pass_contract_error("LaunchKernelCostFuncError", INVALID_COST_KIND_DETAIL)
        raw_kinds = [kind.strip() for kind in cost_kind.split("|")]
        if any(kind == "" for kind in raw_kinds):
            raise_pass_contract_error("LaunchKernelCostFuncError", INVALID_COST_KIND_DETAIL)
        normalized_kinds: list[str] = []
        seen_kinds: set[str] = set()
        for kind in raw_kinds:
            if kind in seen_kinds:
                raise_pass_contract_error("LaunchKernelCostFuncError", INVALID_COST_KIND_DETAIL)
            seen_kinds.add(kind)
            normalized_kinds.append(kind)
        self.cost_kind = "|".join(normalized_kinds)
        self._cost_kinds = tuple(normalized_kinds)

    @classmethod
    def from_options(
        cls: type["LaunchKernelCostFuncPass"], options: dict[str, str]
    ) -> "LaunchKernelCostFuncPass":
        """从 registry options 构造 pass。

        创建者: 小李飞刀
        最后一次更改: OpenAI Codex

        功能说明:
        - 支持 `{"cost_kind": "compute|memory|latency"}` 形式的 registry 入口。
        - 拒绝未知选项，避免静默吞参。

        使用示例:
        - pass_obj = LaunchKernelCostFuncPass.from_options({"cost_kind": "compute|memory|latency"})

        关联文件:
        - spec: [spec/pass/tuning/launch_kernel_cost_func.md](../../../spec/pass/tuning/launch_kernel_cost_func.md)
        - test: [test/pass/test_launch_kernel_cost_func.py](../../../test/pass/test_launch_kernel_cost_func.py)
        - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](../../../kernel_gen/passes/tuning/launch_kernel_cost_func.py)
        """

        unknown = sorted(set(options) - {"cost_kind"})
        if unknown:
            raise_pass_contract_error(
                "LaunchKernelCostFuncError",
                f"unknown option(s): {', '.join(unknown)}",
            )
        return cls(cost_kind=options.get("cost_kind", "compute"))

    def run(self: "LaunchKernelCostFuncPass", module: object) -> ModuleOp:
        """执行 launch-kernel-cost-func pass。

        创建者: 小李飞刀
        最后一次更改: OpenAI Codex

        功能说明:
        - 校验 module 输入与 `arch.launch -> device func` 关系。
        - 为每个 unique device callee 和每个请求的 `cost_kind` 生成 sibling cost function。
        - 若发现非法 `cost_kind`、callee 缺失、metadata attr 冲突、非支持 op 或重名 cost function，显式失败。

        使用示例:
        - module = LaunchKernelCostFuncPass(cost_kind="compute|memory").run(module)

        关联文件:
        - spec: [spec/pass/tuning/launch_kernel_cost_func.md](../../../spec/pass/tuning/launch_kernel_cost_func.md)
        - test: [test/pass/test_launch_kernel_cost_func.py](../../../test/pass/test_launch_kernel_cost_func.py)
        - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](../../../kernel_gen/passes/tuning/launch_kernel_cost_func.py)
        """

        if not isinstance(module, ModuleOp):
            raise_pass_contract_error("LaunchKernelCostFuncError", "module must be builtin.module")

        func_by_name = {
            op.sym_name.data: op for op in module.ops if isinstance(op, func.FuncOp)
        }
        device_funcs: list[func.FuncOp] = []
        seen_device_names: set[str] = set()
        for op in module.walk():
            if not isinstance(op, ArchLaunchOp):
                continue
            callee_name = op.callee.root_reference.data
            device_func = func_by_name.get(callee_name)
            if device_func is None:
                raise_pass_contract_error(
                    "LaunchKernelCostFuncError",
                    f"arch.launch callee '{callee_name}' not found",
                )
            if callee_name in seen_device_names:
                continue
            seen_device_names.add(callee_name)
            device_funcs.append(device_func)
        if not device_funcs:
            return module

        existing_names = {
            op.sym_name.data for op in module.ops if isinstance(op, func.FuncOp)
        }
        for device_func in device_funcs:
            for cost_kind in self._cost_kinds:
                cost_name = f"_cost_{cost_kind}_{device_func.sym_name.data}"
                if cost_name in existing_names:
                    raise_pass_contract_error(
                        "LaunchKernelCostFuncError",
                        f"cost function '{cost_name}' already exists",
                    )
                existing_names.add(cost_name)

        for device_func in device_funcs:
            source_blocks = list(device_func.body.blocks)
            if len(source_blocks) != 1:
                raise_pass_contract_error(
                    "LaunchKernelCostFuncError",
                    f"device function '{device_func.sym_name.data}' must contain single block",
                )

            anchor = device_func
            input_types = list(device_func.function_type.inputs.data)
            for cost_kind in self._cost_kinds:
                cost_block = Block(arg_types=input_types)
                zero = SymbolConstOp(0)
                cost_block.add_op(zero)

                frames: list[dict[str, object]] = [
                    {
                        "source_block": source_blocks[0],
                        "target_block": cost_block,
                        "ops": list(source_blocks[0].ops),
                        "index": 0,
                        "value_mapper": {
                            source_arg: cost_arg
                            for source_arg, cost_arg in zip(
                                source_blocks[0].args,
                                cost_block.args,
                                strict=True,
                            )
                        },
                        "acc_value": zero.result,
                        "loop_op": None,
                    }
                ]
                final_acc_value: SSAValue = zero.result

                while frames:
                    frame = frames[-1]
                    ops = frame["ops"]
                    index = frame["index"]
                    assert isinstance(ops, list)
                    assert isinstance(index, int)
                    if index >= len(ops):
                        finished = frames.pop()
                        finished_target_block = finished["target_block"]
                        finished_acc_value = finished["acc_value"]
                        assert isinstance(finished_target_block, Block)
                        assert isinstance(finished_acc_value, SSAValue)
                        if not frames:
                            final_acc_value = finished_acc_value
                            break
                        finished_target_block.add_op(SymbolYieldOp(finished_acc_value))
                        parent = frames[-1]
                        loop_op = finished["loop_op"]
                        assert isinstance(loop_op, SymbolForOp)
                        assert loop_op.result is not None
                        parent["acc_value"] = loop_op.result
                        continue

                    op = ops[index]
                    frame["index"] = index + 1
                    target_block = frame["target_block"]
                    value_mapper = frame["value_mapper"]
                    acc_value = frame["acc_value"]
                    assert isinstance(target_block, Block)
                    assert isinstance(value_mapper, dict)
                    assert isinstance(acc_value, SSAValue)

                    if isinstance(op, SymbolForOp):
                        if op.init is not None or op.result is not None:
                            raise_pass_contract_error(
                                "LaunchKernelCostFuncError",
                                "source symbol.for must not already carry loop-carried result",
                            )
                        inner_source_block = op.body.block
                        inner_block = Block(
                            arg_types=[inner_source_block.args[0].type, acc_value.type]
                        )
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
                        frames.append(
                            {
                                "source_block": inner_source_block,
                                "target_block": inner_block,
                                "ops": list(inner_source_block.ops),
                                "index": 0,
                                "value_mapper": inner_mapper,
                                "acc_value": inner_block.args[1],
                                "loop_op": loop_op,
                            }
                        )
                        continue

                    op_name = op.name
                    if op_name == "builtin.unregistered":
                        op_name_attr = op.attributes.get("op_name__")
                        if isinstance(op_name_attr, StringAttr):
                            op_name = op_name_attr.data

                    is_skip_op = (
                        isinstance(op, func.ReturnOp)
                        or op_name == "arith.constant"
                        or op_name in HELPER_OP_NAMES
                        or (op_name.startswith("symbol.") and not isinstance(op, SymbolForOp))
                    )
                    if is_skip_op:
                        if not isinstance(op, func.ReturnOp):
                            cloned = op.clone(value_mapper=value_mapper)
                            target_block.add_op(cloned)
                            for source_result, cloned_result in zip(
                                op.results,
                                cloned.results,
                                strict=True,
                            ):
                                value_mapper[source_result] = cloned_result
                        continue

                    if not any(
                        op_name.startswith(prefix) for prefix in SUPPORTED_COST_PREFIXES
                    ):
                        raise_pass_contract_error(
                            "LaunchKernelCostFuncError",
                            f"unsupported op '{op_name}' in device function '{device_func.sym_name.data}'",
                        )

                    if len(op.results) != 0:
                        cloned = op.clone(value_mapper=value_mapper)
                        target_block.add_op(cloned)
                        for source_result, cloned_result in zip(
                            op.results,
                            cloned.results,
                            strict=True,
                        ):
                            value_mapper[source_result] = cloned_result

                    extra_attrs = dict(op.attributes)
                    extra_attrs.pop("op_name__", None)
                    if op_name == "kernel.binary_elewise" and "kind" in extra_attrs:
                        extra_attrs["kernel_kind"] = extra_attrs.pop("kind")
                    for attr_name in RESERVED_METADATA_ATTRS:
                        if attr_name in extra_attrs:
                            raise_pass_contract_error(
                                "LaunchKernelCostFuncError",
                                (
                                    f"op '{op_name}' in device function "
                                    f"'{device_func.sym_name.data}' already defines reserved attr '{attr_name}'"
                                ),
                            )

                    cost_op = TunerCostOp(
                        [value_mapper.get(operand, operand) for operand in op.operands],
                        cost_kind=StringAttr(cost_kind),
                        op_name=StringAttr(op_name),
                        extra_attrs=extra_attrs,
                    )
                    target_block.add_op(cost_op)
                    add_op = SymbolAddOp(
                        acc_value,
                        cost_op.result,
                        result_type=acc_value.type,
                    )
                    target_block.add_op(add_op)
                    frame["acc_value"] = add_op.result

                cost_block.add_op(func.ReturnOp(final_acc_value))
                cost_func = func.FuncOp(
                    f"_cost_{cost_kind}_{device_func.sym_name.data}",
                    (input_types, [final_acc_value.type]),
                    Region(cost_block),
                    visibility=getattr(device_func, "sym_visibility", None),
                    arg_attrs=device_func.arg_attrs,
                )
                verify_generated_ops([cost_func])
                module.body.block.insert_op_after(cost_func, anchor)
                anchor = cost_func

        return module


__all__ = ["LaunchKernelCostFuncPass"]
