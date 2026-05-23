"""attach-arch-information pass.


功能说明:
- 为 `builtin.module` 中可执行 device/pattern `func.func` 补齐 `launch_block / launch_thread / launch_subthread / shared_memory_size`。
- 带 `entry_point` 的 host dispatcher 必须跳过，避免 host 被误当作 device kernel。
- extent 统一从 target registry 读取，当前 `npu_demo` 口径为 `2/1/1/0`。
- 不承担 outline 逻辑，仅负责把 IR 级 launch 信息补齐到后续 `outline-device-kernel` 可消费的状态。

API 列表:
- `class AttachArchInformationPass(target: str = "npu_demo", fold: bool = True)`
- `AttachArchInformationPass.from_options(options: dict[str, str]) -> AttachArchInformationPass`
- `AttachArchInformationPass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from kernel_gen.passes.attach_arch_information import AttachArchInformationPass
- AttachArchInformationPass(target="npu_demo").apply(Context(), module)

关联文件:
- spec: [spec/pass/attach_arch_information.md](../../spec/pass/attach_arch_information.md)
- test: [test/passes/test_attach_arch_information.py](../../test/passes/test_attach_arch_information.py)
- 功能实现: [kernel_gen/passes/attach_arch_information.py](../../kernel_gen/passes/attach_arch_information.py)
"""

from __future__ import annotations
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError

from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, IntAttr, IntegerAttr, ModuleOp, StringAttr
from xdsl.ir import Block

from kernel_gen.dialect.arch import ArchGetDynamicMemoryOp
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolExprAttr
from kernel_gen.passes.pass_manager import Pass
from kernel_gen.target import registry as target_registry

_DYNAMIC_MEMORY_CAPACITY_KEYS = {
    "tsm": "tsm_memory_size",
    "tlm1": "tlm1_memory_size",
    "tlm2": "tlm2_memory_size",
    "tlm3": "tlm3_memory_size",
}


class AttachArchInformationPass(Pass):
    """attach-arch-information pass。


    功能说明:
    - 固定公开名称为 `attach-arch-information`。
    - 为入口 `func.func` 从 target registry 补齐 launch extent 与 `shared_memory_size`。
    - 公开执行入口固定为 xdsl `ModulePass.apply(ctx, module)`。

    使用示例:
    - from kernel_gen.passes.attach_arch_information import AttachArchInformationPass
    - AttachArchInformationPass(target="npu_demo").apply(Context(), module)
    - AttachArchInformationPass.from_options({"target": "npu_demo"})

    关联文件:
    - spec: [spec/pass/attach_arch_information.md](../../spec/pass/attach_arch_information.md)
    - test: [test/passes/test_attach_arch_information.py](../../test/passes/test_attach_arch_information.py)
    - 功能实现: [kernel_gen/passes/attach_arch_information.py](../../kernel_gen/passes/attach_arch_information.py)
    """

    name = "attach-arch-information"

    def __init__(self: "AttachArchInformationPass", target: str = "npu_demo", fold: bool = True) -> None:
        """初始化 attach-arch-information pass。


        功能说明:
        - 记录当前 attach 的 target 名称。
        - 默认 target 为 `npu_demo`，与当前主线 pytest / pipeline 口径对齐。
        - `fold` 默认开启，由 PassManager 在 pass 后执行通用 folding sweep。

        使用示例:
        - pass_obj = AttachArchInformationPass()
        - pass_obj = AttachArchInformationPass(target="npu_demo")
        - pass_obj = AttachArchInformationPass(fold=False)

        关联文件:
        - spec: [spec/pass/attach_arch_information.md](../../spec/pass/attach_arch_information.md)
        - test: [test/passes/test_attach_arch_information.py](../../test/passes/test_attach_arch_information.py)
        - 功能实现: [kernel_gen/passes/attach_arch_information.py](../../kernel_gen/passes/attach_arch_information.py)
        """

        super().__init__(fold=fold)
        self.target = target

    @classmethod
    def from_options(
        cls: type["AttachArchInformationPass"], options: dict[str, str]
    ) -> "AttachArchInformationPass":
        """从 registry options 构造 pass。


        功能说明:
        - 支持 `{"target": "npu_demo"}` 形式的 registry 入口。
        - 拒绝未知选项与空 target，避免静默吞参。

        使用示例:
        - pass_obj = AttachArchInformationPass.from_options({"target": "npu_demo"})

        关联文件:
        - spec: [spec/pass/attach_arch_information.md](../../spec/pass/attach_arch_information.md)
        - test: [test/passes/test_attach_arch_information.py](../../test/passes/test_attach_arch_information.py)
        - 功能实现: [kernel_gen/passes/attach_arch_information.py](../../kernel_gen/passes/attach_arch_information.py)
        """

        unknown = sorted(set(options) - {"target"})
        if unknown:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, 
                f"AttachArchInformationError: unknown option(s): {', '.join(unknown)}"
            )
        target = options.get("target", "npu_demo")
        if not isinstance(target, str) or not target.strip():
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "AttachArchInformationError: target must be non-empty string")
        return cls(target=target)

    def _specialized_dynamic_memory_type(
        self: "AttachArchInformationPass",
        op: ArchGetDynamicMemoryOp,
    ) -> NnMemoryType | None:
        """构造 target 容量特化后的 dynamic memory result type。

        功能说明:
        - 仅对 `tsm/tlm1/tlm2/tlm3` 查询 target registry 容量并生成静态字节数 shape。
        - `shared/local` 保持 named-capacity 形态，不在本轮特化。

        使用示例:
        - result_type = self._specialized_dynamic_memory_type(op)

        关联文件:
        - spec: [spec/pass/attach_arch_information.md](../../spec/pass/attach_arch_information.md)
        - test: [test/passes/test_attach_arch_information.py](../../test/passes/test_attach_arch_information.py)
        - 功能实现: [kernel_gen/passes/attach_arch_information.py](../../kernel_gen/passes/attach_arch_information.py)
        """

        space_name = op.memory_space.space.data
        hardware_key = _DYNAMIC_MEMORY_CAPACITY_KEYS.get(space_name)
        if hardware_key is None:
            return None
        capacity = target_registry.get_target_hardware(self.target, hardware_key)
        if capacity is None:
            raise KernelCodeError(
                ErrorKind.CONTRACT,
                ErrorModule.PASS,
                f"AttachArchInformationError: target {self.target} is missing {hardware_key}",
            )
        if capacity <= 0:
            raise KernelCodeError(
                ErrorKind.CONTRACT,
                ErrorModule.PASS,
                f"AttachArchInformationError: target {self.target} {hardware_key} must be > 0",
            )
        current_type = op.result.type
        if not isinstance(current_type, NnMemoryType):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "AttachArchInformationError: arch.get_dynamic_memory result must be nn.memory")
        return NnMemoryType(
            ArrayAttr([SymbolExprAttr.from_expr(str(capacity))]),
            current_type.stride,
            current_type.element_type,
            current_type.space,
        )

    def _specialize_dynamic_memory_ops(self: "AttachArchInformationPass", module: ModuleOp) -> None:
        """特化 module 中 dynamic memory 查询的 target 容量。

        功能说明:
        - 替换 `arch.get_dynamic_memory` op 的 result type，不修改其它 op 语义。
        - 使用公开 block 插入、SSA use 替换与 erase 操作保持用户链路不丢失。

        使用示例:
        - self._specialize_dynamic_memory_ops(module)

        关联文件:
        - spec: [spec/pass/attach_arch_information.md](../../spec/pass/attach_arch_information.md)
        - test: [test/passes/test_attach_arch_information.py](../../test/passes/test_attach_arch_information.py)
        - 功能实现: [kernel_gen/passes/attach_arch_information.py](../../kernel_gen/passes/attach_arch_information.py)
        """

        for op in [candidate for candidate in module.walk() if isinstance(candidate, ArchGetDynamicMemoryOp)]:
            result_type = self._specialized_dynamic_memory_type(op)
            if result_type is None or result_type == op.result.type:
                continue
            parent_block = op.parent_block()
            if not isinstance(parent_block, Block):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "AttachArchInformationError: arch.get_dynamic_memory must be attached to a block")
            replacement = ArchGetDynamicMemoryOp(op.memory_space, result_type)
            parent_block.insert_op_before(replacement, op)
            op.result.replace_all_uses_with(replacement.result)
            parent_block.erase_op(op)

    def _attach_launch_attrs(
        self: "AttachArchInformationPass",
        func_op: func.FuncOp,
        expected_values: dict[str, int],
        all_launch_attr_names: tuple[str, ...],
    ) -> None:
        """为单个目标函数补齐或校验 launch attrs。

        功能说明:
        - 已携带 launch attrs 的函数必须四个字段齐全并与 target 一致。
        - 未携带时写入 target registry 提供的静态 extent。

        使用示例:
        - self._attach_launch_attrs(func_op, expected_values, all_launch_attr_names)

        关联文件:
        - spec: [spec/pass/attach_arch_information.md](../../spec/pass/attach_arch_information.md)
        - test: [test/passes/test_attach_arch_information.py](../../test/passes/test_attach_arch_information.py)
        - 功能实现: [kernel_gen/passes/attach_arch_information.py](../../kernel_gen/passes/attach_arch_information.py)
        """

        present = [name for name in all_launch_attr_names if name in func_op.attributes]
        if present:
            if len(present) != len(all_launch_attr_names):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS,
                    "AttachArchInformationError: function "
                    f"{func_op.sym_name.data} must define launch_block, launch_thread, "
                    "launch_subthread, and shared_memory_size together"
                )
            current_values: dict[str, int] = {}
            for attr_name in all_launch_attr_names:
                attr = func_op.attributes[attr_name]
                if isinstance(attr, IntAttr):
                    current_values[attr_name] = attr.data
                    continue
                if isinstance(attr, IntegerAttr):
                    current_values[attr_name] = attr.value.data
                    continue
                if isinstance(attr, StringAttr):
                    try:
                        current_values[attr_name] = int(attr.data)
                    except ValueError as exc:  # pragma: no cover - defensive branch
                        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS,
                            "AttachArchInformationError: function "
                            f"{func_op.sym_name.data} {attr_name} must be int-like attribute"
                        ) from exc
                    continue
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS,
                    "AttachArchInformationError: function "
                    f"{func_op.sym_name.data} {attr_name} must be int-like attribute"
                )
            if tuple(current_values[name] for name in all_launch_attr_names) != tuple(
                expected_values[name] for name in all_launch_attr_names
            ):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS,
                    "AttachArchInformationError: function "
                    f"{func_op.sym_name.data} launch extents must match target {self.target}"
                )
            return

        for attr_name in all_launch_attr_names:
            func_op.attributes[attr_name] = IntAttr(expected_values[attr_name])

    def _target_funcs(self: "AttachArchInformationPass", funcs: list[func.FuncOp]) -> list[func.FuncOp]:
        """选择本轮需要写入 launch attrs 的函数。

        功能说明:
        - 含 pattern/device 函数时，只选择 pattern/device 函数并跳过 `entry_point` host dispatcher。
        - 无 pattern/device 函数时，单个 `entry_point` 函数仍作为普通 kernel 入口 attach。
        - 没有 `entry_point` 时保留旧合同：唯一非 declaration 函数即为目标函数。

        使用示例:
        - candidates = self._target_funcs(funcs)

        关联文件:
        - spec: [spec/pass/attach_arch_information.md](../../spec/pass/attach_arch_information.md)
        - test: [test/passes/test_attach_arch_information.py](../../test/passes/test_attach_arch_information.py)
        - 功能实现: [kernel_gen/passes/attach_arch_information.py](../../kernel_gen/passes/attach_arch_information.py)
        """

        entry_funcs = [func_op for func_op in funcs if "entry_point" in func_op.attributes]
        if entry_funcs:
            pattern_funcs = [
                func_op
                for func_op in funcs
                if "entry_point" not in func_op.attributes
                and (
                    "kernel.transform_pipeline" in func_op.attributes
                    or "kernel.pattern_id" in func_op.attributes
                )
            ]
            if pattern_funcs:
                return pattern_funcs
            if len(entry_funcs) != 1 or len(funcs) != 1:
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS,
                    "AttachArchInformationError: module must contain exactly one entry_point func.func without pattern funcs"
                )
            return entry_funcs
        if len(funcs) != 1:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS,
                "AttachArchInformationError: module must contain exactly one non-declaration func.func"
            )
        return funcs

    def _apply_to_module(self: "AttachArchInformationPass", module: ModuleOp) -> None:
        """执行当前文件内的 attach 主逻辑。


        功能说明:
        - 统一承载 xdsl `apply(ctx, module)` 的业务步骤。
        - 不把当前文件内的属性检查与写回流程暴露成跨文件调用入口。

        使用示例:
        - pass_obj._apply_to_module(module)

        关联文件:
        - spec: [spec/pass/attach_arch_information.md](../../spec/pass/attach_arch_information.md)
        - test: [test/passes/test_attach_arch_information.py](../../test/passes/test_attach_arch_information.py)
        - 功能实现: [kernel_gen/passes/attach_arch_information.py](../../kernel_gen/passes/attach_arch_information.py)
        """

        if not isinstance(module, ModuleOp):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "AttachArchInformationError: module must be builtin.module")

        funcs = [
            op
            for op in module.ops
            if isinstance(op, func.FuncOp) and not op.is_declaration
        ]
        target_funcs = self._target_funcs(funcs)
        launch_attr_names = ("launch_block", "launch_thread", "launch_subthread")
        all_launch_attr_names = launch_attr_names + ("shared_memory_size",)

        if not target_registry.is_arch_op_supported(self.target, "arch.launch"):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, 
                f"AttachArchInformationError: target {self.target} does not support arch.launch"
            )

        expected_values: dict[str, int] = {}
        for hw_key, attr_name in zip(
            ("block_num", "thread_num", "subthread_num"), launch_attr_names, strict=True
        ):
            extent = target_registry.get_target_hardware(self.target, hw_key)
            if extent is None:
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, 
                    f"AttachArchInformationError: target {self.target} is missing launch extent"
                )
            if extent <= 0:
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, 
                    f"AttachArchInformationError: function {self.target} {attr_name} must be > 0"
                )
            expected_values[attr_name] = extent

        shared_memory_size = target_registry.get_target_hardware(self.target, "sm_memory_size")
        if shared_memory_size is None:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, 
                f"AttachArchInformationError: target {self.target} is missing launch extent"
            )
        if shared_memory_size < 0:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, 
                "AttachArchInformationError: function "
                f"{self.target} shared_memory_size must be >= 0"
            )
        expected_values["shared_memory_size"] = shared_memory_size

        for func_op in target_funcs:
            self._attach_launch_attrs(func_op, expected_values, all_launch_attr_names)
        self._specialize_dynamic_memory_ops(module)

    def apply(self: "AttachArchInformationPass", ctx: Context, module: ModuleOp) -> None:
        """满足 xdsl `ModulePass` 协议的 hook。


        功能说明:
        - 保留给 xdsl `ModulePass` 协议消费。
        - 不再提供单 pass `run(module)` 兼容入口。

        使用示例:
        - AttachArchInformationPass(target="npu_demo").apply(Context(), module)

        关联文件:
        - spec: [spec/pass/attach_arch_information.md](../../spec/pass/attach_arch_information.md)
        - test: [test/passes/test_attach_arch_information.py](../../test/passes/test_attach_arch_information.py)
        - 功能实现: [kernel_gen/passes/attach_arch_information.py](../../kernel_gen/passes/attach_arch_information.py)
        """

        _ = ctx
        self._apply_to_module(module)
__all__ = ["AttachArchInformationPass"]
