"""outline-device-kernel pass.


功能说明:
- 作为 `ModulePass` 为带显式 launch 属性的 `func.func` 执行 host-launch outline。
- 把原函数改写为只包含 `symbol.const + arch.launch + func.return` 的 host wrapper。
- 把原函数体搬移到新的 `@<name>_device`，并只在 device 侧保留 `shared_memory_size`。
- 对 host dispatcher 内的 `tuner.launch`，直接改写为指向 pattern device 函数的
  `arch.launch`，并移除原 pattern wrapper。

API 列表:
- `class OutlineDeviceKernelFuncPattern(candidates: dict[str, tuple[int, int, int, int]])`
- `OutlineDeviceKernelFuncPattern.match_and_rewrite(op: func.FuncOp, rewriter: PatternRewriter) -> None`
- `get_outline_device_kernel_pass_patterns(candidates: dict[str, tuple[int, int, int, int]]) -> list[RewritePattern]`
- `class OutlineDeviceKernelPass(fold: bool = True)`
- `OutlineDeviceKernelPass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from xdsl.context import Context
- from xdsl.dialects.builtin import ModuleOp
- from kernel_gen.passes.tuning.outline_device_kernel import OutlineDeviceKernelPass
- module = ModuleOp([])
- OutlineDeviceKernelPass(fold=True).apply(Context(), module)

关联文件:
- spec: [spec/pass/tuning/outline_device_kernel.md](spec/pass/tuning/outline_device_kernel.md)
- test: [test/passes/tuning/test_outline_device_kernel.py](test/passes/tuning/test_outline_device_kernel.py)
- 功能实现: [kernel_gen/passes/tuning/outline_device_kernel.py](kernel_gen/passes/tuning/outline_device_kernel.py)
"""

from __future__ import annotations
from dataclasses import dataclass

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError

from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import IntAttr, IntegerAttr, ModuleOp, StringAttr
from xdsl.ir import Block, Region, SSAValue
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
from kernel_gen.dialect.symbol import Symbol, SymbolConstOp
from kernel_gen.dialect.tuner import TunerLaunchOp
from kernel_gen.passes.common import (
    ensure_builtin_module,
    verify_generated_ops,
)


class OutlineDeviceKernelFuncPattern(RewritePattern):
    """按单个 `func.func` 执行 outline-device-kernel 改写。


    功能说明:
    - 一个 `func.func` 对应一个 pattern。
    - 仅处理候选集合中带显式 launch attrs 的函数。
    - IR 变换：带 launch attr 的 `func.func @k` 变为 host wrapper `@k` 与 device func `@k_device`。
    - no-op：函数不在候选集合或缺少 launch attr 时保持原 IR。
    - IR before:
      ```mlir
      func.func @k(%arg0: value) attributes {launch_block = 1 : i64, launch_thread = 2 : i64, launch_subthread = 1 : i64} {
        "test.op"() : () -> ()
        func.return
      }
      ```
    - IR after:
      ```mlir
      func.func @k(%arg0: value) {
        %b = "symbol.const"() {value = 1 : i64} : () -> !symbol.int<"1">
        %t = "symbol.const"() {value = 2 : i64} : () -> !symbol.int<"2">
        %s = "symbol.const"() {value = 1 : i64} : () -> !symbol.int<"1">
        %m = "symbol.const"() {value = 0 : i64} : () -> !symbol.int<"0">
        "arch.launch"(%b, %t, %s, %m, %arg0) {callee = @k_device} : (...) -> ()
        func.return
      }
      func.func @k_device(%arg0: value) {
        "test.op"() : () -> ()
        func.return
      }
      ```
    - no-op unchanged after：函数不在 candidates 或缺少完整 launch attrs 时，上述 before IR 保持不变。

    使用示例:
    - pattern = OutlineDeviceKernelFuncPattern(candidates)

    关联文件:
    - spec: [spec/pass/tuning/outline_device_kernel.md](spec/pass/tuning/outline_device_kernel.md)
    - test: [test/passes/tuning/test_outline_device_kernel.py](test/passes/tuning/test_outline_device_kernel.py)
    - 功能实现: [kernel_gen/passes/tuning/outline_device_kernel.py](kernel_gen/passes/tuning/outline_device_kernel.py)
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
            visibility=op.sym_visibility,
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
    """返回 `outline-device-kernel` pass 的公开 pattern 列表。


    功能说明:
    - 每次调用返回新的 `OutlineDeviceKernelFuncPattern` 实例。
    - 当前固定只返回 `OutlineDeviceKernelFuncPattern`，顺序即为 pass 执行顺序。

    使用示例:
    - patterns = get_outline_device_kernel_pass_patterns(candidates)

    关联文件:
    - spec: [spec/pass/tuning/outline_device_kernel.md](spec/pass/tuning/outline_device_kernel.md)
    - test: [test/passes/tuning/test_outline_device_kernel.py](test/passes/tuning/test_outline_device_kernel.py)
    - 功能实现: [kernel_gen/passes/tuning/outline_device_kernel.py](kernel_gen/passes/tuning/outline_device_kernel.py)
    """

    return [OutlineDeviceKernelFuncPattern(candidates)]


@dataclass(frozen=True)
class OutlineDeviceKernelPass(ModulePass):
    """outline-device-kernel pass。


    功能说明:
    - 固定公开名称为 `outline-device-kernel`。
    - 作为 `ModulePass` 由 `apply(ctx, module)` 执行。
    - 保持未标记函数原样不变，且不并入默认 pipeline。

    使用示例:
    - from xdsl.context import Context
    - from xdsl.dialects.builtin import ModuleOp
    - module = ModuleOp([])
    - OutlineDeviceKernelPass(fold=True).apply(Context(), module)

    关联文件:
    - spec: [spec/pass/tuning/outline_device_kernel.md](spec/pass/tuning/outline_device_kernel.md)
    - test: [test/passes/tuning/test_outline_device_kernel.py](test/passes/tuning/test_outline_device_kernel.py)
    - 功能实现: [kernel_gen/passes/tuning/outline_device_kernel.py](kernel_gen/passes/tuning/outline_device_kernel.py)
    """

    name = "outline-device-kernel"
    fold: bool = True

    def __init__(self: "OutlineDeviceKernelPass", fold: bool = True) -> None:
        """初始化 outline-device-kernel pass 公共选项。


        功能说明:
        - 记录 `fold` 开关，默认允许 pass 内 pattern walker 执行 folding。

        使用示例:
        - pass_obj = OutlineDeviceKernelPass(fold=True)
        - pass_obj = OutlineDeviceKernelPass(fold=False)

        关联文件:
        - spec: [spec/pass/tuning/outline_device_kernel.md](spec/pass/tuning/outline_device_kernel.md)
        - test: [test/passes/tuning/test_outline_device_kernel.py](test/passes/tuning/test_outline_device_kernel.py)
        - 功能实现: [kernel_gen/passes/tuning/outline_device_kernel.py](kernel_gen/passes/tuning/outline_device_kernel.py)
        """

        object.__setattr__(self, "fold", bool(fold))

    def _make_device_func(self, func_op: func.FuncOp) -> func.FuncOp:
        """把候选函数体移动到 `<name>_device` 函数。

        功能说明:
        - 复用原函数签名、参数属性、结果属性与非 launch attrs。
        - 供普通 wrapper outline 与 tuner dispatcher outline 两条路径共享。

        使用示例:
        - device_func = self._make_device_func(pattern_func)

        关联文件:
        - spec: [spec/pass/tuning/outline_device_kernel.md](spec/pass/tuning/outline_device_kernel.md)
        - test: [test/passes/tuning/test_outline_device_kernel.py](test/passes/tuning/test_outline_device_kernel.py)
        - 功能实现: [kernel_gen/passes/tuning/outline_device_kernel.py](kernel_gen/passes/tuning/outline_device_kernel.py)
        """

        input_types = list(func_op.function_type.inputs.data)
        output_types = list(func_op.function_type.outputs.data)
        original_attrs = dict(func_op.attributes)
        device_region = Region()
        func_op.body.move_blocks(device_region)
        device_func = func.FuncOp(
            f"{func_op.sym_name.data}_device",
            (input_types, output_types),
            device_region,
            visibility=func_op.sym_visibility,
            arg_attrs=func_op.arg_attrs,
            res_attrs=func_op.res_attrs,
        )
        device_func.attributes.update(
            {
                name: attr
                for name, attr in original_attrs.items()
                if name not in OutlineDeviceKernelFuncPattern.LAUNCH_ATTRS
            }
        )
        return device_func

    def _rewrite_tuner_launches(
        self,
        module: ModuleOp,
        candidates: dict[str, tuple[int, int, int, int]],
    ) -> None:
        """把 host dispatcher 内的 tuner.launch 改写为 arch.launch。

        功能说明:
        - 每个 `tuner.launch(@pattern, args...)` 使用对应 `@pattern_device` 作为 callee。
        - 四个 extent 在 launch 所在 block 内就地物化为 `symbol.const`，保证 SSA 支配关系。

        使用示例:
        - self._rewrite_tuner_launches(module, candidates)

        关联文件:
        - spec: [spec/pass/tuning/outline_device_kernel.md](spec/pass/tuning/outline_device_kernel.md)
        - test: [test/passes/tuning/test_outline_device_kernel.py](test/passes/tuning/test_outline_device_kernel.py)
        - 功能实现: [kernel_gen/passes/tuning/outline_device_kernel.py](kernel_gen/passes/tuning/outline_device_kernel.py)
        """

        for launch_op in [op for op in module.walk() if isinstance(op, TunerLaunchOp)]:
            callee_name = launch_op.callee.root_reference.data
            candidate = candidates.get(callee_name)
            if candidate is None:
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"tuner.launch callee '{callee_name}' is not outline candidate")
            parent_block = launch_op.parent_block()
            if not isinstance(parent_block, Block):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "tuner.launch must be attached to a block")
            block_extent, thread_extent, subthread_extent, shared_memory_size_extent = candidate
            block_const = SymbolConstOp(block_extent)
            thread_const = SymbolConstOp(thread_extent)
            subthread_const = SymbolConstOp(subthread_extent)
            shared_memory_size_const = SymbolConstOp(shared_memory_size_extent)
            for const_op in (block_const, thread_const, subthread_const, shared_memory_size_const):
                parent_block.insert_op_before(const_op, launch_op)
            arch_launch = ArchLaunchOp(
                f"{callee_name}_device",
                block_const.result,
                thread_const.result,
                subthread_const.result,
                shared_memory_size_const.result,
                tuple(SSAValue.get(arg) for arg in launch_op.args),
            )
            parent_block.insert_op_before(arch_launch, launch_op)
            parent_block.erase_op(launch_op)
            verify_generated_ops([block_const, thread_const, subthread_const, shared_memory_size_const, arch_launch])

    def _outline_tuner_launch_patterns(
        self,
        module: ModuleOp,
        candidates: dict[str, tuple[int, int, int, int]],
    ) -> None:
        """执行 pattern dispatcher outline。

        功能说明:
        - 先把所有 `tuner.launch` 改写为 `arch.launch @pattern_device`。
        - 再把被 launch 的 pattern 函数替换为对应 device 函数，避免保留裸 pattern wrapper。

        使用示例:
        - self._outline_tuner_launch_patterns(module, candidates)

        关联文件:
        - spec: [spec/pass/tuning/outline_device_kernel.md](spec/pass/tuning/outline_device_kernel.md)
        - test: [test/passes/tuning/test_outline_device_kernel.py](test/passes/tuning/test_outline_device_kernel.py)
        - 功能实现: [kernel_gen/passes/tuning/outline_device_kernel.py](kernel_gen/passes/tuning/outline_device_kernel.py)
        """

        self._rewrite_tuner_launches(module, candidates)
        launched = {op.callee.root_reference.data for op in module.walk() if isinstance(op, ArchLaunchOp)}
        pattern_names = {name for name in candidates if f"{name}_device" in launched}
        for func_op in [op for op in module.ops if isinstance(op, func.FuncOp) and op.sym_name.data in pattern_names]:
            parent_block = func_op.parent_block()
            if not isinstance(parent_block, Block):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "outline candidate must be attached to a block")
            device_func = self._make_device_func(func_op)
            parent_block.insert_op_after(device_func, func_op)
            parent_block.erase_op(func_op)
            verify_generated_ops([device_func])

    def apply(self, ctx: Context, module: ModuleOp) -> None:
        """执行 outline-device-kernel ModulePass。


        功能说明:
        - 仅接受 `builtin.module` 作为 ModulePass 输入。
        - 先收集并校验所有待 outline 函数，再统一执行改写。

        使用示例:
        - from xdsl.context import Context
        - from xdsl.dialects.builtin import ModuleOp
        - module = ModuleOp([])
        - OutlineDeviceKernelPass(fold=True).apply(Context(), module)

        关联文件:
        - spec: [spec/pass/tuning/outline_device_kernel.md](spec/pass/tuning/outline_device_kernel.md)
        - test: [test/passes/tuning/test_outline_device_kernel.py](test/passes/tuning/test_outline_device_kernel.py)
        - 功能实现: [kernel_gen/passes/tuning/outline_device_kernel.py](kernel_gen/passes/tuning/outline_device_kernel.py)
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
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS,
                    "function "
                    f"{func_name} must define launch_block, launch_thread, and launch_subthread together"
                )
            if len(op.function_type.outputs.data) != 0:
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"function {func_name} must have zero results")
            if not any(True for _ in op.body.blocks):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"function {func_name} must contain a body")

            values: list[int] = []
            for attr_name in OutlineDeviceKernelFuncPattern.LAUNCH_ATTRS + ("shared_memory_size",):
                attr = op.attributes.get(attr_name)
                if attr is None:
                    if attr_name == "shared_memory_size":
                        values.append(0)
                        continue
                    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS,
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
                        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS,
                            f"function {func_name} {attr_name} must be int-like attribute"
                        ) from exc
                else:
                    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS,
                        f"function {func_name} {attr_name} must be int-like attribute"
                    )
                if attr_name == "shared_memory_size":
                    if value < 0:
                        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS,
                            f"function {func_name} {attr_name} must be >= 0"
                        )
                elif value <= 0:
                    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"function {func_name} {attr_name} must be > 0")
                values.append(value)

            device_name = f"{func_name}_device"
            if device_name in existing_names:
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"outlined device function '{device_name}' already exists")
            candidates[func_name] = (values[0], values[1], values[2], values[3])
        if not candidates:
            return
        if ctx.get_optional_dialect(Symbol.name) is None:
            ctx.load_dialect(Symbol)
        if any(isinstance(op, TunerLaunchOp) for op in module.walk()):
            self._outline_tuner_launch_patterns(module, candidates)
            return
        PatternRewriteWalker(
            GreedyRewritePatternApplier(
                [*get_outline_device_kernel_pass_patterns(candidates)],
                ctx=ctx,
                folding_enabled=self.fold,
                dce_enabled=False,
            )
        ).rewrite_module(module)

__all__ = [
    "OutlineDeviceKernelFuncPattern",
    "get_outline_device_kernel_pass_patterns",
    "OutlineDeviceKernelPass",
]
