"""transform-apply pass.

功能说明:
- 读取 pattern 函数上的 `kernel.transform_pipeline` 字符串并按顺序应用公开 pass / pipeline。
- 仅改写带该 attr 的目标函数，成功后删除 attr；其它函数保持不变。
- 任一步失败时保持原 module 零改动。

API 列表:
- `class TransformApplyPass(fold: bool = True)`
- `TransformApplyPass.from_options(options: dict[str, str]) -> TransformApplyPass`
- `TransformApplyPass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from kernel_gen.passes.tuning import TransformApplyPass
- TransformApplyPass().apply(Context(), module)

关联文件:
- spec: spec/pass/tuning/transform_apply.md
- test: test/passes/tuning/test_transform_apply.py
- 功能实现: kernel_gen/passes/tuning/transform_apply.py
"""

from __future__ import annotations

from dataclasses import dataclass
import shlex

from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import ModuleOp, StringAttr
from xdsl.passes import ModulePass as XdslModulePass
from xdsl.transforms.canonicalize import CanonicalizePass

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.passes.common import ensure_builtin_module
from kernel_gen.passes.pass_manager import Pass, PassManager
from kernel_gen.passes.registry import build_registered_pass, build_registered_pipeline, load_builtin_passes

_TRANSFORM_ATTR = "kernel.transform_pipeline"


def _apply_transform_pipeline_to_module(ctx: Context, module: ModuleOp) -> None:
    """在 module clone 上执行所有 transform pipeline 并原子提交。

    功能说明:
    - 该 helper 将 target 收集、pipeline 字符串解析、step 构造、step 执行和成功提交收敛到单一当前文件私有入口。
    - 不调用其它私有 callable，避免 rehome 后的新 canonical module 暴露私有 helper 链式依赖。

    使用示例:
    - _apply_transform_pipeline_to_module(Context(), module)
    """

    module = ensure_builtin_module(module)
    targets: list[func.FuncOp] = []
    for func_op in (op for op in module.ops if isinstance(op, func.FuncOp)):
        attr = func_op.attributes.get(_TRANSFORM_ATTR)
        if attr is None:
            continue
        if not isinstance(attr, StringAttr) or not attr.data.strip():
            raise KernelCodeError(
                ErrorKind.CONTRACT,
                ErrorModule.PASS,
                "transform-apply kernel.transform_pipeline must be non-empty string attr",
            )
        targets.append(func_op)
    if not targets:
        return

    working = module.clone()
    target_names = {target.sym_name.data for target in targets}
    for target in [op for op in working.ops if isinstance(op, func.FuncOp) and op.sym_name.data in target_names]:
        attr = target.attributes.get(_TRANSFORM_ATTR)
        if not isinstance(attr, StringAttr):
            raise KernelCodeError(
                ErrorKind.CONTRACT,
                ErrorModule.PASS,
                "transform-apply kernel.transform_pipeline must be non-empty string attr",
            )
        try:
            tokens = shlex.split(attr.data)
        except ValueError as exc:
            raise KernelCodeError(
                ErrorKind.CONTRACT,
                ErrorModule.PASS,
                "transform-apply pipeline syntax invalid pipeline string",
            ) from exc
        if not tokens or len(tokens) % 2 != 0:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "transform-apply pipeline syntax invalid pipeline string")

        steps: list[tuple[str, str, dict[str, str]]] = []
        token_index = 0
        while token_index < len(tokens):
            flag = tokens[token_index]
            value = tokens[token_index + 1]
            if flag not in {"--pass", "--pipeline"}:
                raise KernelCodeError(
                    ErrorKind.CONTRACT,
                    ErrorModule.PASS,
                    "transform-apply pipeline syntax invalid pipeline string",
                )
            if "{" not in value and "}" not in value:
                if not value:
                    raise KernelCodeError(
                        ErrorKind.CONTRACT,
                        ErrorModule.PASS,
                        "transform-apply pipeline syntax invalid pipeline step",
                    )
                name = value
                options: dict[str, str] = {}
            else:
                if "={" not in value or not value.endswith("}"):
                    raise KernelCodeError(
                        ErrorKind.CONTRACT,
                        ErrorModule.PASS,
                        "transform-apply pipeline syntax invalid pipeline step",
                    )
                name, option_block = value.split("={", 1)
                option_text = option_block[:-1]
                if not name or not option_text:
                    raise KernelCodeError(
                        ErrorKind.CONTRACT,
                        ErrorModule.PASS,
                        "transform-apply pipeline syntax invalid pipeline step",
                    )
                option_items: list[str] = []
                depth = 0
                in_string = False
                escaped = False
                start = 0
                for index, char in enumerate(option_text):
                    if escaped:
                        escaped = False
                        continue
                    if char == "\\":
                        escaped = True
                        continue
                    if char == '"':
                        in_string = not in_string
                        continue
                    if in_string:
                        continue
                    if char in "{[(":
                        depth += 1
                        continue
                    if char in "}])":
                        depth -= 1
                        if depth < 0:
                            raise KernelCodeError(
                                ErrorKind.CONTRACT,
                                ErrorModule.PASS,
                                "transform-apply pipeline syntax invalid pipeline step",
                            )
                        continue
                    if char == "," and depth == 0:
                        option_items.append(option_text[start:index])
                        start = index + 1
                if in_string or depth != 0:
                    raise KernelCodeError(
                        ErrorKind.CONTRACT,
                        ErrorModule.PASS,
                        "transform-apply pipeline syntax invalid pipeline step",
                    )
                option_items.append(option_text[start:])
                options = {}
                for item in option_items:
                    if "=" not in item:
                        raise KernelCodeError(
                            ErrorKind.CONTRACT,
                            ErrorModule.PASS,
                            "transform-apply pipeline syntax invalid pipeline step",
                        )
                    key, raw_value = item.split("=", 1)
                    key = key.strip()
                    raw_value = raw_value.strip()
                    if not key or not raw_value or key in options:
                        raise KernelCodeError(
                            ErrorKind.CONTRACT,
                            ErrorModule.PASS,
                            "transform-apply pipeline syntax invalid pipeline step",
                        )
                    options[key] = raw_value
            steps.append(("pass" if flag == "--pass" else "pipeline", name, options))
            token_index += 2

        temp_func = target.clone()
        temp_module = ModuleOp([temp_func])
        for kind, name, options in steps:
            try:
                if kind == "pass" and name == "canonicalize":
                    if options:
                        raise KernelCodeError(
                            ErrorKind.CONTRACT,
                            ErrorModule.PASS,
                            "transform-apply canonicalize options unsupported",
                        )
                    step_obj: XdslModulePass | PassManager = CanonicalizePass()
                else:
                    load_builtin_passes()
                    if kind == "pass":
                        step_obj = build_registered_pass(name, options)
                    else:
                        step_obj = build_registered_pipeline(name, options)
            except KernelCodeError as exc:
                raise KernelCodeError(
                    ErrorKind.CONTRACT,
                    ErrorModule.PASS,
                    f"transform-apply step {kind} '{name}' failed: {exc}",
                ) from exc
            try:
                if isinstance(step_obj, PassManager):
                    step_obj.run(temp_module)
                else:
                    step_obj.apply(ctx, temp_module)
            except Exception as exc:
                raise KernelCodeError(
                    ErrorKind.CONTRACT,
                    ErrorModule.PASS,
                    f"transform-apply step {kind} '{name}' failed: {exc}",
                ) from exc

        candidates = [op for op in temp_module.ops if isinstance(op, func.FuncOp) and op.sym_name.data == target.sym_name.data]
        if len(candidates) != 1:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "transform-apply target func must survive transform")
        transformed = candidates[0]
        transformed.detach()
        transformed.attributes.pop(_TRANSFORM_ATTR, None)
        parent_block = target.parent_block()
        if parent_block is None:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "transform-apply target func parent block missing")
        parent_block.insert_op_before(transformed, target)
        parent_block.erase_op(target)

    target_block = module.body.block
    for op in list(target_block.ops):
        target_block.erase_op(op)
    for op in list(working.body.block.ops):
        op.detach()
        target_block.add_op(op)


@dataclass(frozen=True)
class TransformApplyPass(Pass):
    """应用 `kernel.transform_pipeline` 的 ModulePass。

    功能说明:
    - 固定公开 pass 名称为 `transform-apply`。
    - 无专属 options；失败时不修改原 module。

    使用示例:
    - TransformApplyPass().apply(Context(), module)

    关联文件:
    - spec: spec/pass/tuning/transform_apply.md
    - test: test/passes/tuning/test_transform_apply.py
    - 功能实现: kernel_gen/passes/tuning/transform_apply.py
    """

    name = "transform-apply"
    fold: bool = True

    @classmethod
    def from_options(cls: type["TransformApplyPass"], options: dict[str, str]) -> "TransformApplyPass":
        """从 registry options 构造 pass。

        功能说明:
        - 当前不接受专属 options；未知 option 稳定失败。

        使用示例:
        - TransformApplyPass.from_options({})
        """

        if options:
            unknown = ", ".join(sorted(options))
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"transform-apply options unknown: {unknown}")
        return cls()

    def apply(self: "TransformApplyPass", ctx: Context, module: ModuleOp) -> None:
        """执行 transform-apply。

        功能说明:
        - 先在 clone 上完成所有 target 改写，成功后整体替换原 module。
        - 任一 target pipeline 失败时原 module 保持不变。

        使用示例:
        - TransformApplyPass().apply(Context(), module)
        """

        _apply_transform_pipeline_to_module(ctx, module)


__all__ = ["TransformApplyPass"]
