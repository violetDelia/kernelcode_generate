"""outline-device-kernel pass.

创建者: 朽木露琪亚
最后一次更改: OpenAI Codex

功能说明:
- 作为 `ModulePass` 为带显式 launch 属性的 `func.func` 执行 host-launch outline。
- 把原函数改写为只包含 `symbol.const + arch.launch + func.return` 的 host wrapper。
- 把原函数体搬移到新的 `@<name>_device`，并只在 device 侧保留 `shared_memory_size`。

使用示例:
- from xdsl.context import Context
- from xdsl.dialects.builtin import ModuleOp
- from kernel_gen.passes.outline_device_kernel import OutlineDeviceKernelPass
- module = ModuleOp([])
- OutlineDeviceKernelPass().apply(Context(), module)
- # 兼容旧调用方仍可使用 OutlineDeviceKernelPass().run(module)

关联文件:
- spec: [spec/pass/outline_device_kernel.md](spec/pass/outline_device_kernel.md)
- test: [test/pass/outline_device_kernel/test_outline_device_kernel.py](test/pass/outline_device_kernel/test_outline_device_kernel.py)
- 功能实现: [kernel_gen/passes/outline_device_kernel.py](kernel_gen/passes/outline_device_kernel.py)
"""

from __future__ import annotations

from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import IntAttr, IntegerAttr, ModuleOp, StringAttr
from xdsl.ir import Block, Region
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import (
    GreedyRewritePatternApplier,
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)
from xdsl.rewriter import InsertPoint

from kernel_gen.dialect.arch import ArchLaunchOp
from kernel_gen.dialect.symbol import SymbolConstOp
from kernel_gen.passes.common import (
    PassContractError,
    ensure_builtin_module,
    verify_generated_ops,
)


class OutlineDeviceKernelFuncPattern(RewritePattern):
    """按单个 `func.func` 执行 outline-device-kernel 改写。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 一个 `func.func` 对应一个 pattern。
    - 仅处理候选集合中带显式 launch attrs 的函数。

    使用示例:
    - pattern = OutlineDeviceKernelFuncPattern(candidates)

    关联文件:
    - spec: [spec/pass/outline_device_kernel.md](spec/pass/outline_device_kernel.md)
    - test: [test/pass/outline_device_kernel/test_outline_device_kernel.py](test/pass/outline_device_kernel/test_outline_device_kernel.py)
    - 功能实现: [kernel_gen/passes/outline_device_kernel.py](kernel_gen/passes/outline_device_kernel.py)
    """

    LAUNCH_ATTRS = ("launch_block", "launch_thread", "launch_subthread")

    def __init__(self, candidates: dict[str, tuple[int, int, int, int]]):
        self._candidates = candidates

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: func.FuncOp, rewriter: PatternRewriter, /) -> None:
        candidate = self._candidates.get(op.sym_name.data)
        if candidate is None:
            return
        if not any(name in op.attributes for name in self.LAUNCH_ATTRS):
            return
        block, thread, subthread, shared_memory_size = candidate
        input_types = list(op.function_type.inputs.data)
        output_types = list(op.function_type.outputs.data)
        original_attrs = dict(op.attributes)
        device_name = f"{op.sym_name.data}_device"
        device_region = Region()
        op.body.move_blocks(device_region)

        device_func = func.FuncOp(
            device_name,
            (input_types, output_types),
            device_region,
            visibility=getattr(op, "sym_visibility", None),
            arg_attrs=op.arg_attrs,
            res_attrs=op.res_attrs,
        )
        device_func.attributes.update(
            {
                name: attr
                for name, attr in original_attrs.items()
                if name not in self.LAUNCH_ATTRS
            }
        )
        op.attributes.clear()
        op.attributes.update(
            {
                name: attr
                for name, attr in original_attrs.items()
                if name not in self.LAUNCH_ATTRS and name != "shared_memory_size"
            }
        )
        wrapper_block = Block(arg_types=input_types)
        block_const = SymbolConstOp(block)
        thread_const = SymbolConstOp(thread)
        subthread_const = SymbolConstOp(subthread)
        shared_memory_size_const = SymbolConstOp(shared_memory_size)
        launch = ArchLaunchOp(
            device_name,
            block_const.result,
            thread_const.result,
            subthread_const.result,
            shared_memory_size_const.result,
            tuple(wrapper_block.args),
        )
        wrapper_block.add_ops(
            [
                block_const,
                thread_const,
                subthread_const,
                shared_memory_size_const,
                launch,
                func.ReturnOp(),
            ]
        )
        op.body.add_block(wrapper_block)

        rewriter.insert_op(device_func, InsertPoint.after(rewriter.current_operation))
        verify_generated_ops([op, device_func])
        rewriter.notify_op_modified(op)


def get_outline_device_kernel_pass_patterns(
    candidates: dict[str, tuple[int, int, int, int]],
) -> list[RewritePattern]:
    """返回 `outline-device-kernel` pass 使用的公开 pattern 列表。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 为外部测试、组合 pass 与公开 API 提供稳定的 pattern 构造入口。
    - 当前固定只返回 `OutlineDeviceKernelFuncPattern`，顺序即为 pass 执行顺序。

    使用示例:
    - patterns = get_outline_device_kernel_pass_patterns(candidates)
    - walker = PatternRewriteWalker(GreedyRewritePatternApplier(patterns, ctx=ctx))

    关联文件:
    - spec: [spec/pass/outline_device_kernel.md](spec/pass/outline_device_kernel.md)
    - test: [test/pass/outline_device_kernel/test_outline_device_kernel.py](test/pass/outline_device_kernel/test_outline_device_kernel.py)
    - 功能实现: [kernel_gen/passes/outline_device_kernel.py](kernel_gen/passes/outline_device_kernel.py)
    """

    return [OutlineDeviceKernelFuncPattern(candidates)]


class OutlineDeviceKernelPass(ModulePass):
    """outline-device-kernel pass。

    创建者: 朽木露琪亚
    最后一次更改: OpenAI Codex

    功能说明:
    - 固定公开名称为 `outline-device-kernel`。
    - 作为 `ModulePass` 由 `apply(ctx, module)` 执行。
    - 保持未标记函数原样不变，且不并入默认 pipeline。

    使用示例:
    - from xdsl.context import Context
    - from xdsl.dialects.builtin import ModuleOp
    - module = ModuleOp([])
    - OutlineDeviceKernelPass().apply(Context(), module)

    关联文件:
    - spec: [spec/pass/outline_device_kernel.md](spec/pass/outline_device_kernel.md)
    - test: [test/pass/outline_device_kernel/test_outline_device_kernel.py](test/pass/outline_device_kernel/test_outline_device_kernel.py)
    - 功能实现: [kernel_gen/passes/outline_device_kernel.py](kernel_gen/passes/outline_device_kernel.py)
    """

    name = "outline-device-kernel"

    def apply(self, ctx: Context, module: ModuleOp) -> None:
        """执行 outline-device-kernel ModulePass。

        创建者: 朽木露琪亚
        最后一次更改: OpenAI Codex

        功能说明:
        - 仅接受 `builtin.module` 作为 ModulePass 输入。
        - 先收集并校验所有待 outline 函数，再统一执行改写。

        使用示例:
        - from xdsl.context import Context
        - from xdsl.dialects.builtin import ModuleOp
        - module = ModuleOp([])
        - OutlineDeviceKernelPass().apply(Context(), module)

        关联文件:
        - spec: [spec/pass/outline_device_kernel.md](spec/pass/outline_device_kernel.md)
        - test: [test/pass/outline_device_kernel/test_outline_device_kernel.py](test/pass/outline_device_kernel/test_outline_device_kernel.py)
        - 功能实现: [kernel_gen/passes/outline_device_kernel.py](kernel_gen/passes/outline_device_kernel.py)
        """

        module = ensure_builtin_module(module)
        if not any(True for _ in module.ops):
            return
        candidates: dict[str, tuple[int, int, int, int]] = {}
        existing_names = {op.sym_name.data for op in module.ops if isinstance(op, func.FuncOp)}
        for op in module.ops:
            if not isinstance(op, func.FuncOp):
                continue
            present_attrs = [
                name
                for name in OutlineDeviceKernelFuncPattern.LAUNCH_ATTRS
                if name in op.attributes
            ]
            if not present_attrs:
                continue
            func_name = op.sym_name.data
            if len(present_attrs) != len(OutlineDeviceKernelFuncPattern.LAUNCH_ATTRS):
                raise PassContractError(
                    "function "
                    f"{func_name} must define launch_block, launch_thread, and launch_subthread together"
                )
            if len(op.function_type.outputs.data) != 0:
                raise PassContractError(f"function {func_name} must have zero results")
            if not any(True for _ in op.body.blocks):
                raise PassContractError(f"function {func_name} must contain a body")

            values: list[int] = []
            for attr_name in OutlineDeviceKernelFuncPattern.LAUNCH_ATTRS + ("shared_memory_size",):
                attr = op.attributes.get(attr_name)
                if attr is None:
                    if attr_name == "shared_memory_size":
                        values.append(0)
                        continue
                    raise PassContractError(
                        "function "
                        f"{func_name} must define launch_block, launch_thread, and launch_subthread together"
                    )
                if isinstance(attr, IntAttr):
                    value = attr.data
                elif isinstance(attr, IntegerAttr):
                    value = attr.value.data
                elif isinstance(attr, StringAttr):
                    try:
                        value = int(attr.data)
                    except ValueError as exc:
                        raise PassContractError(
                            f"function {func_name} {attr_name} must be int-like attribute"
                        ) from exc
                else:
                    raise PassContractError(
                        f"function {func_name} {attr_name} must be int-like attribute"
                    )
                if attr_name == "shared_memory_size":
                    if value < 0:
                        raise PassContractError(
                            f"function {func_name} {attr_name} must be >= 0"
                        )
                elif value <= 0:
                    raise PassContractError(f"function {func_name} {attr_name} must be > 0")
                values.append(value)

            device_name = f"{func_name}_device"
            if device_name in existing_names:
                raise PassContractError(f"outlined device function '{device_name}' already exists")
            candidates[func_name] = (values[0], values[1], values[2], values[3])
        if not candidates:
            return
        PatternRewriteWalker(
            GreedyRewritePatternApplier(
                [*get_outline_device_kernel_pass_patterns(candidates)],
                ctx=ctx,
                dce_enabled=False,
            )
        ).rewrite_module(module)

    def run(self, module: object) -> ModuleOp:
        """兼容旧 Pass 接口的执行入口。

        创建者: 朽木露琪亚
        最后一次更改: OpenAI Codex

        功能说明:
        - 保持旧 `run(module)` 调用方可继续工作。
        - 内部直接复用 `apply(Context(), module)`。

        使用示例:
        - from xdsl.dialects.builtin import ModuleOp
        - module = OutlineDeviceKernelPass().run(ModuleOp([]))

        关联文件:
        - spec: [spec/pass/outline_device_kernel.md](spec/pass/outline_device_kernel.md)
        - test: [test/pass/outline_device_kernel/test_outline_device_kernel.py](test/pass/outline_device_kernel/test_outline_device_kernel.py)
        - 功能实现: [kernel_gen/passes/outline_device_kernel.py](kernel_gen/passes/outline_device_kernel.py)
        """

        self.apply(Context(), module)  # type: ignore[arg-type]
        return module  # type: ignore[return-value]


__all__ = [
    "OutlineDeviceKernelFuncPattern",
    "OutlineDeviceKernelPass",
    "get_outline_device_kernel_pass_patterns",
]
