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
- from kernel_gen.passes.transform_apply import TransformApplyPass
- TransformApplyPass().apply(Context(), module)

关联文件:
- spec: spec/pass/transform_apply.md
- test: test/passes/test_transform_apply.py
- 功能实现: kernel_gen/passes/transform_apply.py
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


@dataclass(frozen=True)
class _TransformStep:
    """单个 transform step。"""

    kind: str
    name: str
    options: dict[str, str]


def _transform_apply_error(message: str) -> KernelCodeError:
    """构造 transform-apply 错误。

    功能说明:
    - 固定错误前缀，便于 expectation 和 pytest 匹配。

    使用示例:
    - raise _transform_apply_error("unknown pass")
    """

    return KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"transform-apply {message}")


def _transform_pipeline_syntax_error(message: str) -> KernelCodeError:
    """构造 transform pipeline 语法错误。

    功能说明:
    - 统一非法 `kernel.transform_pipeline` 字符串的公开错误短语。
    - 保证所有语法类失败都包含 `transform-apply pipeline syntax` 前缀。

    使用示例:
    - raise _transform_pipeline_syntax_error("invalid pipeline string")
    """

    return _transform_apply_error(f"pipeline syntax {message}")


def _parse_name_options(value: str) -> tuple[str, dict[str, str]]:
    """解析 `<name>` 或 `<name={k=v}>`。

    功能说明:
    - 与 ircheck 公开文本口径保持一致，但实现留在当前文件内，不调用工具私有 helper。

    使用示例:
    - name, options = _parse_name_options("tile={fold=false}")
    """

    if "{" not in value and "}" not in value:
        if not value:
            raise _transform_pipeline_syntax_error("invalid pipeline step")
        return value, {}
    if "={" not in value or not value.endswith("}"):
        raise _transform_pipeline_syntax_error("invalid pipeline step")
    name, option_block = value.split("={", 1)
    if not name:
        raise _transform_pipeline_syntax_error("invalid pipeline step")
    option_text = option_block[:-1]
    if not option_text:
        raise _transform_pipeline_syntax_error("invalid pipeline step")
    options: dict[str, str] = {}
    for item in _split_top_level_commas(option_text):
        if "=" not in item:
            raise _transform_pipeline_syntax_error("invalid pipeline step")
        key, raw_value = item.split("=", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if not key or not raw_value or key in options:
            raise _transform_pipeline_syntax_error("invalid pipeline step")
        options[key] = raw_value
    return name, options


def _split_top_level_commas(text: str) -> tuple[str, ...]:
    """按顶层逗号拆分 option 字符串。

    功能说明:
    - `apply_op=matmul{["", "tlm1", "tlm2"]}` 内部包含逗号，不能用普通 split。
    - 仅在当前文件解析公开 transform pipeline 字符串时使用。

    使用示例:
    - items = _split_top_level_commas('fold=true,apply_op=matmul{["", "tlm1", "tlm2"]}')
    """

    items: list[str] = []
    depth = 0
    in_string = False
    escaped = False
    start = 0
    for index, char in enumerate(text):
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
                raise _transform_pipeline_syntax_error("invalid pipeline step")
            continue
        if char == "," and depth == 0:
            items.append(text[start:index])
            start = index + 1
    if in_string or depth != 0:
        raise _transform_pipeline_syntax_error("invalid pipeline step")
    items.append(text[start:])
    return tuple(items)


def _parse_transform_pipeline(text: str) -> tuple[_TransformStep, ...]:
    """解析 transform pipeline 字符串。

    功能说明:
    - 支持 `--pass <name>` 与 `--pipeline <name>`，并允许 quoted option block。

    使用示例:
    - steps = _parse_transform_pipeline('--pass "lower={fold=false}" --pass canonicalize')
    """

    try:
        tokens = shlex.split(text)
    except ValueError as exc:
        raise _transform_pipeline_syntax_error("invalid pipeline string") from exc
    if not tokens or len(tokens) % 2 != 0:
        raise _transform_pipeline_syntax_error("invalid pipeline string")
    steps: list[_TransformStep] = []
    index = 0
    while index < len(tokens):
        flag = tokens[index]
        value = tokens[index + 1]
        if flag not in {"--pass", "--pipeline"}:
            raise _transform_pipeline_syntax_error("invalid pipeline string")
        name, options = _parse_name_options(value)
        kind = "pass" if flag == "--pass" else "pipeline"
        steps.append(_TransformStep(kind, name, options))
        index += 2
    return tuple(steps)


def _step_pass(step: _TransformStep) -> XdslModulePass | PassManager:
    """构造单个 transform step 对应执行对象。

    功能说明:
    - `canonicalize` 是 transform-apply 专属内置 resolver，不注册到全局 registry。
    - 其它 pass / pipeline 通过公开 registry 构造。

    使用示例:
    - step_obj = _step_pass(_TransformStep("pass", "canonicalize", {}))
    """

    if step.kind == "pass" and step.name == "canonicalize":
        if step.options:
            raise _transform_apply_error("canonicalize options unsupported")
        return CanonicalizePass()
    load_builtin_passes()
    if step.kind == "pass":
        return build_registered_pass(step.name, step.options)
    return build_registered_pipeline(step.name, step.options)


def _run_step(ctx: Context, module: ModuleOp, step: _TransformStep) -> None:
    """执行单个 transform step。

    功能说明:
    - pass 使用 xDSL `apply(ctx, module)`；pipeline 使用公开 `PassManager.run(module)`。
    - step 构造或执行失败均归一为 `transform-apply` pass 错误，避免泄漏下游异常类型。

    使用示例:
    - _run_step(ctx, temp_module, step)
    """

    try:
        step_obj = _step_pass(step)
    except KernelCodeError as exc:
        raise _transform_apply_error(f"step {step.kind} '{step.name}' failed: {exc}") from exc
    try:
        if isinstance(step_obj, PassManager):
            step_obj.run(module)
            return
        step_obj.apply(ctx, module)
    except Exception as exc:
        raise _transform_apply_error(f"step {step.kind} '{step.name}' failed: {exc}") from exc


def _funcs(module: ModuleOp) -> tuple[func.FuncOp, ...]:
    """返回 module 顶层函数。

    功能说明:
    - 只遍历 module 顶层，避免嵌套 region 干扰 transform target 选择。

    使用示例:
    - funcs = _funcs(module)
    """

    return tuple(op for op in module.ops if isinstance(op, func.FuncOp))


def _target_funcs(module: ModuleOp) -> tuple[func.FuncOp, ...]:
    """收集带 transform attr 的目标函数。

    功能说明:
    - 目标函数必须携带 `kernel.transform_pipeline = StringAttr`。

    使用示例:
    - targets = _target_funcs(module)
    """

    targets: list[func.FuncOp] = []
    for func_op in _funcs(module):
        attr = func_op.attributes.get(_TRANSFORM_ATTR)
        if attr is None:
            continue
        if not isinstance(attr, StringAttr) or not attr.data.strip():
            raise _transform_apply_error("kernel.transform_pipeline must be non-empty string attr")
        targets.append(func_op)
    return tuple(targets)


def _replace_func(target: func.FuncOp, replacement: func.FuncOp) -> None:
    """用 replacement 替换 target。

    功能说明:
    - 替换发生在同一个 module 顶层 block 内，保持其它函数相对顺序不变。

    使用示例:
    - _replace_func(old_func, new_func)
    """

    parent_block = target.parent_block()
    if parent_block is None:
        raise _transform_apply_error("target func parent block missing")
    parent_block.insert_op_before(replacement, target)
    parent_block.erase_op(target)


def _apply_pipeline_to_func(ctx: Context, target: func.FuncOp) -> func.FuncOp:
    """对单个目标函数应用 pipeline。

    功能说明:
    - 用只含目标函数 clone 的临时 module 执行 transform，避免污染其它 pattern 或 host。
    - 成功后删除 `kernel.transform_pipeline` attr 并返回新的目标函数。

    使用示例:
    - transformed = _apply_pipeline_to_func(ctx, target)
    """

    attr = target.attributes.get(_TRANSFORM_ATTR)
    if not isinstance(attr, StringAttr):
        raise _transform_apply_error("kernel.transform_pipeline must be non-empty string attr")
    steps = _parse_transform_pipeline(attr.data)
    temp_func = target.clone()
    temp_module = ModuleOp([temp_func])
    for step in steps:
        _run_step(ctx, temp_module, step)
    candidates = [op for op in temp_module.ops if isinstance(op, func.FuncOp) and op.sym_name.data == target.sym_name.data]
    if len(candidates) != 1:
        raise _transform_apply_error("target func must survive transform")
    transformed = candidates[0]
    transformed.detach()
    transformed.attributes.pop(_TRANSFORM_ATTR, None)
    return transformed


def _replace_module_ops(target: ModuleOp, source: ModuleOp) -> None:
    """把 source module 顶层 ops 移动到 target。

    功能说明:
    - 用于 transform 成功后的原子提交；失败路径不调用，因此原 module 保持零改动。

    使用示例:
    - _replace_module_ops(module, working_clone)
    """

    block = target.body.block
    for op in list(block.ops):
        block.erase_op(op)
    for op in list(source.body.block.ops):
        op.detach()
        block.add_op(op)


class TransformApplyPass(Pass):
    """应用 `kernel.transform_pipeline` 的 ModulePass。

    功能说明:
    - 固定公开 pass 名称为 `transform-apply`。
    - 无专属 options；失败时不修改原 module。

    使用示例:
    - TransformApplyPass().apply(Context(), module)

    关联文件:
    - spec: spec/pass/transform_apply.md
    - test: test/passes/test_transform_apply.py
    - 功能实现: kernel_gen/passes/transform_apply.py
    """

    name = "transform-apply"

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
            raise _transform_apply_error(f"options unknown: {unknown}")
        return cls()

    def apply(self: "TransformApplyPass", ctx: Context, module: ModuleOp) -> None:
        """执行 transform-apply。

        功能说明:
        - 先在 clone 上完成所有 target 改写，成功后整体替换原 module。
        - 任一 target pipeline 失败时原 module 保持不变。

        使用示例:
        - TransformApplyPass().apply(Context(), module)
        """

        module = ensure_builtin_module(module)
        targets = _target_funcs(module)
        if not targets:
            return
        working = module.clone()
        target_names = {target.sym_name.data for target in targets}
        for target in [func_op for func_op in _funcs(working) if func_op.sym_name.data in target_names]:
            transformed = _apply_pipeline_to_func(ctx, target)
            _replace_func(target, transformed)
        _replace_module_ops(module, working)


__all__ = ["TransformApplyPass"]
