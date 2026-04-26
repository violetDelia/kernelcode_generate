"""attach-arch-information pass.

创建者: 金铲铲大作战
最后一次更改: OpenAI Codex

功能说明:
- 为 `builtin.module` 中的入口 `func.func` 补齐 `launch_block / launch_thread / launch_subthread / shared_memory_size`。
- extent 统一从 target registry 读取，当前 `npu_demo` 口径为 `1/1/1/0`。
- 不承担 outline 逻辑，仅负责把 IR 级 launch 信息补齐到后续 `outline-device-kernel` 可消费的状态。

使用示例:
- from kernel_gen.passes.attach_arch_information import AttachArchInformationPass
- module = AttachArchInformationPass(target="npu_demo").run(module)
- AttachArchInformationPass().apply(Context(), module)

关联文件:
- spec: [spec/pass/attach_arch_information.md](../../spec/pass/attach_arch_information.md)
- test: [test/pass/test_attach_arch_information.py](../../test/pass/test_attach_arch_information.py)
- 功能实现: [kernel_gen/passes/attach_arch_information.py](../../kernel_gen/passes/attach_arch_information.py)
"""

from __future__ import annotations

from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import IntAttr, IntegerAttr, ModuleOp, StringAttr
from xdsl.passes import ModulePass

from kernel_gen.passes.common import PassContractError
from kernel_gen.passes.pass_manager import Pass
from kernel_gen.target import registry as target_registry


class AttachArchInformationPass(Pass, ModulePass):
    """attach-arch-information pass。

    创建者: 金铲铲大作战
    最后一次更改: OpenAI Codex

    功能说明:
    - 固定公开名称为 `attach-arch-information`。
    - 为入口 `func.func` 从 target registry 补齐 launch extent 与 `shared_memory_size`。
    - 兼容 `PassManager` 与 xdsl `ModulePass` 两套执行入口。

    使用示例:
    - from kernel_gen.passes.attach_arch_information import AttachArchInformationPass
    - module = AttachArchInformationPass(target="npu_demo").run(module)
    - AttachArchInformationPass.from_options({"target": "npu_demo"})

    关联文件:
    - spec: [spec/pass/attach_arch_information.md](../../spec/pass/attach_arch_information.md)
    - test: [test/pass/test_attach_arch_information.py](../../test/pass/test_attach_arch_information.py)
    - 功能实现: [kernel_gen/passes/attach_arch_information.py](../../kernel_gen/passes/attach_arch_information.py)
    """

    name = "attach-arch-information"

    def __init__(self: "AttachArchInformationPass", target: str = "npu_demo") -> None:
        """初始化 attach-arch-information pass。

        创建者: 金铲铲大作战
        最后一次更改: OpenAI Codex

        功能说明:
        - 记录当前 attach 的 target 名称。
        - 默认 target 为 `npu_demo`，与当前主线 pytest / pipeline 口径对齐。

        使用示例:
        - pass_obj = AttachArchInformationPass()
        - pass_obj = AttachArchInformationPass(target="npu_demo")

        关联文件:
        - spec: [spec/pass/attach_arch_information.md](../../spec/pass/attach_arch_information.md)
        - test: [test/pass/test_attach_arch_information.py](../../test/pass/test_attach_arch_information.py)
        - 功能实现: [kernel_gen/passes/attach_arch_information.py](../../kernel_gen/passes/attach_arch_information.py)
        """

        self.target = target

    @classmethod
    def from_options(
        cls: type["AttachArchInformationPass"], options: dict[str, str]
    ) -> "AttachArchInformationPass":
        """从 registry options 构造 pass。

        创建者: 金铲铲大作战
        最后一次更改: OpenAI Codex

        功能说明:
        - 支持 `{"target": "npu_demo"}` 形式的 registry 入口。
        - 拒绝未知选项与空 target，避免静默吞参。

        使用示例:
        - pass_obj = AttachArchInformationPass.from_options({"target": "npu_demo"})

        关联文件:
        - spec: [spec/pass/attach_arch_information.md](../../spec/pass/attach_arch_information.md)
        - test: [test/pass/test_attach_arch_information.py](../../test/pass/test_attach_arch_information.py)
        - 功能实现: [kernel_gen/passes/attach_arch_information.py](../../kernel_gen/passes/attach_arch_information.py)
        """

        unknown = sorted(set(options) - {"target"})
        if unknown:
            raise PassContractError(
                f"AttachArchInformationError: unknown option(s): {', '.join(unknown)}"
            )
        target = options.get("target", "npu_demo")
        if not isinstance(target, str) or not target.strip():
            raise PassContractError("AttachArchInformationError: target must be non-empty string")
        return cls(target=target)

    def apply(self: "AttachArchInformationPass", ctx: Context, module: ModuleOp) -> None:
        """执行 attach-arch-information pass。

        创建者: 金铲铲大作战
        最后一次更改: OpenAI Codex

        功能说明:
        - 只接受 `builtin.module` 输入。
        - 只对模块入口 `func.func` 写回四段 launch extent。
        - 若已有 launch 属性，则必须与 target registry 一致。

        使用示例:
        - AttachArchInformationPass(target="npu_demo").apply(Context(), module)

        关联文件:
        - spec: [spec/pass/attach_arch_information.md](../../spec/pass/attach_arch_information.md)
        - test: [test/pass/test_attach_arch_information.py](../../test/pass/test_attach_arch_information.py)
        - 功能实现: [kernel_gen/passes/attach_arch_information.py](../../kernel_gen/passes/attach_arch_information.py)
        """

        del ctx
        if not isinstance(module, ModuleOp):
            raise PassContractError("AttachArchInformationError: module must be builtin.module")

        entry_funcs = [
            op
            for op in module.ops
            if isinstance(op, func.FuncOp) and not getattr(op, "is_declaration", False)
        ]
        if len(entry_funcs) != 1:
            raise PassContractError(
                "AttachArchInformationError: module must contain exactly one non-declaration func.func"
            )
        entry_func = entry_funcs[0]
        launch_attr_names = ("launch_block", "launch_thread", "launch_subthread")
        all_launch_attr_names = launch_attr_names + ("shared_memory_size",)

        if not target_registry.is_arch_op_supported(self.target, "arch.launch"):
            raise PassContractError(
                f"AttachArchInformationError: target {self.target} does not support arch.launch"
            )

        expected_values: dict[str, int] = {}
        for hw_key, attr_name in zip(
            ("block_num", "thread_num", "subthread_num"), launch_attr_names, strict=True
        ):
            extent = target_registry.get_target_hardware(self.target, hw_key)
            if extent is None:
                raise PassContractError(
                    f"AttachArchInformationError: target {self.target} is missing launch extent"
                )
            if extent <= 0:
                raise PassContractError(
                    f"AttachArchInformationError: function {self.target} {attr_name} must be > 0"
                )
            expected_values[attr_name] = extent

        shared_memory_size = target_registry.get_target_hardware(self.target, "sm_memory_size")
        if shared_memory_size is None:
            raise PassContractError(
                f"AttachArchInformationError: target {self.target} is missing launch extent"
            )
        if shared_memory_size < 0:
            raise PassContractError(
                "AttachArchInformationError: function "
                f"{self.target} shared_memory_size must be >= 0"
            )
        expected_values["shared_memory_size"] = shared_memory_size

        present = [name for name in all_launch_attr_names if name in entry_func.attributes]
        if present:
            if len(present) != len(all_launch_attr_names):
                raise PassContractError(
                    "AttachArchInformationError: function "
                    f"{entry_func.sym_name.data} must define launch_block, launch_thread, "
                    "launch_subthread, and shared_memory_size together"
                )
            current_values: dict[str, int] = {}
            for attr_name in all_launch_attr_names:
                attr = entry_func.attributes[attr_name]
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
                        raise PassContractError(
                            "AttachArchInformationError: function "
                            f"{entry_func.sym_name.data} {attr_name} must be int-like attribute"
                        ) from exc
                    continue
                raise PassContractError(
                    "AttachArchInformationError: function "
                    f"{entry_func.sym_name.data} {attr_name} must be int-like attribute"
                )
            if tuple(current_values[name] for name in all_launch_attr_names) != tuple(
                expected_values[name] for name in all_launch_attr_names
            ):
                raise PassContractError(
                    "AttachArchInformationError: function "
                    f"{entry_func.sym_name.data} launch extents must match target {self.target}"
                )
            return

        entry_func.attributes["launch_block"] = IntAttr(expected_values["launch_block"])
        entry_func.attributes["launch_thread"] = IntAttr(expected_values["launch_thread"])
        entry_func.attributes["launch_subthread"] = IntAttr(expected_values["launch_subthread"])
        entry_func.attributes["shared_memory_size"] = IntAttr(expected_values["shared_memory_size"])

    def run(self: "AttachArchInformationPass", module: object) -> ModuleOp:
        """兼容 `PassManager` 的 `run(module)` 执行入口。

        创建者: 金铲铲大作战
        最后一次更改: OpenAI Codex

        功能说明:
        - 保持 `Pass` 风格调用方可继续工作。
        - 内部直接复用 `apply()`，不额外暴露模块级 helper。

        使用示例:
        - module = AttachArchInformationPass().run(module)

        关联文件:
        - spec: [spec/pass/attach_arch_information.md](../../spec/pass/attach_arch_information.md)
        - test: [test/pass/test_attach_arch_information.py](../../test/pass/test_attach_arch_information.py)
        - 功能实现: [kernel_gen/passes/attach_arch_information.py](../../kernel_gen/passes/attach_arch_information.py)
        """

        if not isinstance(module, ModuleOp):
            raise PassContractError("AttachArchInformationError: module must be builtin.module")
        self.apply(Context(), module)
        return module


__all__ = ["AttachArchInformationPass"]
