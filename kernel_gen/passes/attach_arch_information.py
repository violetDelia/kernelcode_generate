"""attach-arch-information pass.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 为 `builtin.module` 中的入口 `func.func` 补齐 `launch_block / launch_thread / launch_subthread`。
- extent 统一从 target registry 读取，当前 `npu_demo` 口径为 `1/1/1`。
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
from xdsl.ir import Attribute
from xdsl.passes import ModulePass

from kernel_gen.passes.pass_manager import Pass
from kernel_gen.target import registry as target_registry

_LAUNCH_ATTRS = ("launch_block", "launch_thread", "launch_subthread")
_LAUNCH_SHARED_MEMORY_ATTR = "shared_memory_size"
_LAUNCH_ATTR_NAMES = _LAUNCH_ATTRS + (_LAUNCH_SHARED_MEMORY_ATTR,)
_TARGET_HW_KEYS = ("block_num", "thread_num", "subthread_num", "sm_memory_size")


class AttachArchInformationError(ValueError):
    """attach-arch-information pass 的稳定错误类型。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一承载 attach 阶段的显式失败路径。
    - 保持错误前缀稳定，便于测试与 expectation 做机械匹配。

    使用示例:
    - raise AttachArchInformationError("AttachArchInformationError: module must be builtin.module")

    关联文件:
    - spec: [spec/pass/attach_arch_information.md](../../spec/pass/attach_arch_information.md)
    - test: [test/pass/test_attach_arch_information.py](../../test/pass/test_attach_arch_information.py)
    - 功能实现: [kernel_gen/passes/attach_arch_information.py](../../kernel_gen/passes/attach_arch_information.py)
    """


def _extract_int_like_attr(attr_name: str, attr: Attribute, func_name: str) -> int:
    """把属性规整为 Python 整数。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 `IntAttr`、`IntegerAttr` 与可转整数的 `StringAttr`。
    - 对非整数语义统一抛出稳定错误短语。

    使用示例:
    - value = _extract_int_like_attr("launch_thread", IntAttr(4), "kernel")

    关联文件:
    - spec: [spec/pass/attach_arch_information.md](../../spec/pass/attach_arch_information.md)
    - test: [test/pass/test_attach_arch_information.py](../../test/pass/test_attach_arch_information.py)
    - 功能实现: [kernel_gen/passes/attach_arch_information.py](../../kernel_gen/passes/attach_arch_information.py)
    """

    if isinstance(attr, IntAttr):
        return attr.data
    if isinstance(attr, IntegerAttr):
        return attr.value.data
    if isinstance(attr, StringAttr):
        try:
            return int(attr.data)
        except ValueError as exc:  # pragma: no cover - defensive branch
            raise AttachArchInformationError(
                f"AttachArchInformationError: function {func_name} {attr_name} must be int-like attribute"
            ) from exc
    raise AttachArchInformationError(
        f"AttachArchInformationError: function {func_name} {attr_name} must be int-like attribute"
    )


def _normalize_positive_int_attr(attr_name: str, attr: Attribute, func_name: str) -> int:
    """把属性规整为正整数 launch extent。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 复用 int-like 提取逻辑，校验 launch extent 必须大于 `0`。
    - 对非整数或非正数语义抛出稳定错误短语。

    使用示例:
    - value = _normalize_positive_int_attr("launch_thread", IntAttr(4), "kernel")

    关联文件:
    - spec: [spec/pass/attach_arch_information.md](../../spec/pass/attach_arch_information.md)
    - test: [test/pass/test_attach_arch_information.py](../../test/pass/test_attach_arch_information.py)
    - 功能实现: [kernel_gen/passes/attach_arch_information.py](../../kernel_gen/passes/attach_arch_information.py)
    """

    value = _extract_int_like_attr(attr_name, attr, func_name)
    if value <= 0:
        raise AttachArchInformationError(
            f"AttachArchInformationError: function {func_name} {attr_name} must be > 0"
        )
    return value


def _normalize_non_negative_int_attr(attr_name: str, attr: Attribute, func_name: str) -> int:
    """把属性规整为非负整数 metadata。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 复用 int-like 提取逻辑，校验 metadata 必须大于等于 `0`。
    - 供 `shared_memory_size` 这类 metadata 在 attach 阶段统一校验。

    使用示例:
    - value = _normalize_non_negative_int_attr("shared_memory_size", IntAttr(0), "kernel")

    关联文件:
    - spec: [spec/pass/attach_arch_information.md](../../spec/pass/attach_arch_information.md)
    - test: [test/pass/test_attach_arch_information.py](../../test/pass/test_attach_arch_information.py)
    - 功能实现: [kernel_gen/passes/attach_arch_information.py](../../kernel_gen/passes/attach_arch_information.py)
    """

    value = _extract_int_like_attr(attr_name, attr, func_name)
    if value < 0:
        raise AttachArchInformationError(
            f"AttachArchInformationError: function {func_name} {attr_name} must be >= 0"
        )
    return value


def _target_launch_extents(target: str) -> tuple[int, int, int, int]:
    """读取 target 对应的 launch extent。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 从 target registry 读取 `block_num / thread_num / subthread_num / sm_memory_size`。
    - 同时校验 `arch.launch` 是否对当前 target 公开可用。

    使用示例:
    - block, thread, subthread, shared_memory_size = _target_launch_extents("npu_demo")

    关联文件:
    - spec: [spec/pass/attach_arch_information.md](../../spec/pass/attach_arch_information.md)
    - test: [test/pass/test_attach_arch_information.py](../../test/pass/test_attach_arch_information.py)
    - 功能实现: [kernel_gen/passes/attach_arch_information.py](../../kernel_gen/passes/attach_arch_information.py)
    """

    if not target_registry.is_arch_op_supported(target, "arch.launch"):
        raise AttachArchInformationError(
            f"AttachArchInformationError: target {target} does not support arch.launch"
        )
    extents: list[int] = []
    for hw_key, attr_name in zip(_TARGET_HW_KEYS[:-1], _LAUNCH_ATTRS, strict=True):
        extent = target_registry.get_target_hardware(target, hw_key)
        if extent is None:
            raise AttachArchInformationError(
                f"AttachArchInformationError: target {target} is missing launch extent"
            )
        extents.append(_normalize_positive_int_attr(attr_name, IntAttr(extent), target))
    shared_memory_size = target_registry.get_target_hardware(target, _TARGET_HW_KEYS[-1])
    if shared_memory_size is None:
        raise AttachArchInformationError(
            f"AttachArchInformationError: target {target} is missing launch extent"
        )
    extents.append(
        _normalize_non_negative_int_attr(_LAUNCH_SHARED_MEMORY_ATTR, IntAttr(shared_memory_size), target)
    )
    return extents[0], extents[1], extents[2], extents[3]


def _select_entry_func(module: ModuleOp) -> func.FuncOp:
    """选择 attach 需要补齐 launch extent 的入口函数。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 取 module 顶层唯一的非 declaration `func.func` 作为入口。
    - 若 module 中非 declaration `func.func` 数量不是 1，显式失败，不得静默选择首个函数。
    - 与 `dsl_run` / `outline-device-kernel` 的单入口默认路径对齐。

    使用示例:
    - entry = _select_entry_func(module)

    关联文件:
    - spec: [spec/pass/attach_arch_information.md](../../spec/pass/attach_arch_information.md)
    - test: [test/pass/test_attach_arch_information.py](../../test/pass/test_attach_arch_information.py)
    - 功能实现: [kernel_gen/passes/attach_arch_information.py](../../kernel_gen/passes/attach_arch_information.py)
    """

    entry_funcs = [
        op
        for op in module.ops
        if isinstance(op, func.FuncOp) and not getattr(op, "is_declaration", False)
    ]
    if len(entry_funcs) != 1:
        raise AttachArchInformationError(
            "AttachArchInformationError: module must contain exactly one non-declaration func.func"
        )
    return entry_funcs[0]


def _validate_existing_launch_attrs(func_op: func.FuncOp, target_name: str) -> bool:
    """校验已有 launch 属性是否与 target 口径一致。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 若四项 launch 属性部分存在，显式失败。
    - 若四项 launch 属性全部存在，则必须与 target registry 的 extent 完全一致。
    - 返回 `True` 表示属性已存在且可直接复用，无需再写回。

    使用示例:
    - if _validate_existing_launch_attrs(func_op, "npu_demo"): ...

    关联文件:
    - spec: [spec/pass/attach_arch_information.md](../../spec/pass/attach_arch_information.md)
    - test: [test/pass/test_attach_arch_information.py](../../test/pass/test_attach_arch_information.py)
    - 功能实现: [kernel_gen/passes/attach_arch_information.py](../../kernel_gen/passes/attach_arch_information.py)
    """

    present = [name for name in _LAUNCH_ATTR_NAMES if name in func_op.attributes]
    if not present:
        return False
    func_name = func_op.sym_name.data
    if len(present) != len(_LAUNCH_ATTR_NAMES):
        raise AttachArchInformationError(
            "AttachArchInformationError: function "
            f"{func_name} must define launch_block, launch_thread, launch_subthread, and shared_memory_size together"
        )
    expected_block, expected_thread, expected_subthread, expected_shared_memory_size = _target_launch_extents(
        target_name
    )
    current = (
        _extract_int_like_attr("launch_block", func_op.attributes["launch_block"], func_name),
        _extract_int_like_attr("launch_thread", func_op.attributes["launch_thread"], func_name),
        _extract_int_like_attr("launch_subthread", func_op.attributes["launch_subthread"], func_name),
        _extract_int_like_attr(
            _LAUNCH_SHARED_MEMORY_ATTR,
            func_op.attributes[_LAUNCH_SHARED_MEMORY_ATTR],
            func_name,
        ),
    )
    if current != (expected_block, expected_thread, expected_subthread, expected_shared_memory_size):
        raise AttachArchInformationError(
            f"AttachArchInformationError: function {func_name} launch extents must match target {target_name}"
        )
    return True


class AttachArchInformationPass(Pass, ModulePass):
    """attach-arch-information pass。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 固定公开名称为 `attach-arch-information`。
        - 为入口 `func.func` 从 target registry 补齐 launch extent 与 shared_memory_size。
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
        最后一次更改: 金铲铲大作战

        功能说明:
        - 记录当前 attach 的 target 名称。
        - 默认 target 为 `npu_demo`，与当前主线 expectation / pytest 口径对齐。

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
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 `{"target": "npu_demo"}` 形式的 registry 入口。
        - 拒绝未知选项，避免静默吞参。

        使用示例:
        - pass_obj = AttachArchInformationPass.from_options({"target": "npu_demo"})

        关联文件:
        - spec: [spec/pass/attach_arch_information.md](../../spec/pass/attach_arch_information.md)
        - test: [test/pass/test_attach_arch_information.py](../../test/pass/test_attach_arch_information.py)
        - 功能实现: [kernel_gen/passes/attach_arch_information.py](../../kernel_gen/passes/attach_arch_information.py)
        """

        unknown = sorted(set(options) - {"target"})
        if unknown:
            raise AttachArchInformationError(
                f"AttachArchInformationError: unknown option(s): {', '.join(unknown)}"
            )
        target = options.get("target", "npu_demo")
        if not isinstance(target, str) or not target.strip():
            raise AttachArchInformationError(
                "AttachArchInformationError: target must be non-empty string"
            )
        return cls(target=target)

    def apply(self: "AttachArchInformationPass", ctx: Context, module: ModuleOp) -> None:
        """执行 attach-arch-information pass。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

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
            raise AttachArchInformationError("AttachArchInformationError: module must be builtin.module")
        entry_func = _select_entry_func(module)
        if _validate_existing_launch_attrs(entry_func, self.target):
            return
        block, thread, subthread, shared_memory_size = _target_launch_extents(self.target)
        entry_func.attributes["launch_block"] = IntAttr(block)
        entry_func.attributes["launch_thread"] = IntAttr(thread)
        entry_func.attributes["launch_subthread"] = IntAttr(subthread)
        entry_func.attributes[_LAUNCH_SHARED_MEMORY_ATTR] = IntAttr(shared_memory_size)

    def run(self: "AttachArchInformationPass", module: object) -> ModuleOp:
        """兼容旧 Pass 接口的执行入口。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 保持旧 `run(module)` 调用方可继续工作。

        使用示例:
        - module = AttachArchInformationPass().run(module)

        关联文件:
        - spec: [spec/pass/attach_arch_information.md](../../spec/pass/attach_arch_information.md)
        - test: [test/pass/test_attach_arch_information.py](../../test/pass/test_attach_arch_information.py)
        - 功能实现: [kernel_gen/passes/attach_arch_information.py](../../kernel_gen/passes/attach_arch_information.py)
        """

        if not isinstance(module, ModuleOp):
            raise AttachArchInformationError("AttachArchInformationError: module must be builtin.module")
        self.apply(Context(), module)
        return module


__all__ = ["AttachArchInformationError", "AttachArchInformationPass"]
