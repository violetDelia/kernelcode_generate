"""kernel-pattern-attach pass.

功能说明:
- 在唯一 `entry_point` host 中识别一个或多个 out/lhs/rhs 均为 TSM 的 `kernel.matmul`。
- 生成两个 pattern 函数，并把 host 改写为 `tuner.select + scf.if + tuner.launch` dispatcher。
- 没有合格 TSM matmul 时保持 no-op；entry 调 helper 或 pattern 名称冲突时 fail-fast。

API 列表:
- `class KernelPatternAttachPass(fold: bool = True)`
- `KernelPatternAttachPass.from_options(options: dict[str, str]) -> KernelPatternAttachPass`
- `KernelPatternAttachPass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from kernel_gen.passes.kernel_pattern_attach import KernelPatternAttachPass
- KernelPatternAttachPass().apply(Context(), module)

关联文件:
- spec: spec/pass/kernel_pattern_attach.md
- test: test/passes/test_kernel_pattern_attach.py
- 功能实现: kernel_gen/passes/kernel_pattern_attach.py
"""

from __future__ import annotations

from xdsl.context import Context
from xdsl.dialects import func, scf
from xdsl.dialects.builtin import IntAttr, ModuleOp, StringAttr, UnregisteredOp, i1
from xdsl.ir import Attribute, Block, Operation, Region, SSAValue

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dialect.kernel import KernelMatmulOp
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.dialect.tuner import TunerLaunchOp, TunerSelectOp
from kernel_gen.passes.common import ensure_builtin_module, verify_generated_ops
from kernel_gen.passes.pass_manager import Pass

_PATTERN_PIPELINES = (
    '--pass "lower-dma-memory-hierarchy={fold=true,apply_op=matmul{[\\"\\", \\"tlm1\\", \\"tlm2\\"]}}" --pass canonicalize',
    '--pass "lower-dma-memory-hierarchy={fold=true,apply_op=matmul{[\\"\\", \\"tlm2\\", \\"tlm1\\"]}}" --pass canonicalize',
)


def _kernel_pattern_error(message: str) -> KernelCodeError:
    """构造 kernel-pattern-attach 错误。

    功能说明:
    - 统一 pass 失败短语，便于 expectation 与 pytest 机械匹配。

    使用示例:
    - raise _kernel_pattern_error("entry_point must be exactly one")
    """

    return KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"kernel-pattern-attach {message}")


def _is_tsm_memory(value_type: Attribute) -> bool:
    """判断 SSA type 是否为 TSM memory。

    功能说明:
    - 只接受 `NnMemoryType` 且 `space` 为 `tsm`。

    使用示例:
    - if _is_tsm_memory(op.out.type): ...
    """

    return isinstance(value_type, NnMemoryType) and value_type.space.space.data == "tsm"


def _is_eligible_tsm_matmul(op: Operation) -> bool:
    """判断 kernel.matmul 是否满足本轮 patternize 条件。

    功能说明:
    - 仅当 op 是 `KernelMatmulOp`，且 out/lhs/rhs 三个 memory 均为 TSM 时返回 True。

    使用示例:
    - eligible = _is_eligible_tsm_matmul(op)
    """

    if not isinstance(op, KernelMatmulOp):
        return False
    return _is_tsm_memory(op.out.type) and _is_tsm_memory(op.lhs.type) and _is_tsm_memory(op.rhs.type)


def _module_funcs(module: ModuleOp) -> tuple[func.FuncOp, ...]:
    """返回 module 顶层 func.func。

    功能说明:
    - 只读取顶层 operation，不把嵌套 region 中的函数误当作 module symbol。

    使用示例:
    - funcs = _module_funcs(module)
    """

    return tuple(op for op in module.ops if isinstance(op, func.FuncOp))


def _entry_point_func(module: ModuleOp) -> func.FuncOp:
    """读取唯一 entry_point 函数。

    功能说明:
    - 没有或多个 `entry_point` 都稳定失败。

    使用示例:
    - entry = _entry_point_func(module)
    """

    entries = [op for op in _module_funcs(module) if "entry_point" in op.attributes]
    if len(entries) != 1:
        raise _kernel_pattern_error("entry_point must be exactly one")
    return entries[0]


def _entry_body_ops(entry_func: func.FuncOp) -> tuple[Operation, ...]:
    """校验并返回 entry 顶层 body ops。

    功能说明:
    - 本轮只支持单 block `func.func` entry。

    使用示例:
    - ops = _entry_body_ops(entry_func)
    """

    if entry_func.is_declaration or not any(True for _ in entry_func.body.blocks):
        raise _kernel_pattern_error("entry_point body must be present")
    if len(entry_func.body.blocks) != 1:
        raise _kernel_pattern_error("entry_point body must be single block")
    return tuple(entry_func.body.block.ops)


def _eligible_matmul_ops(entry_func: func.FuncOp) -> tuple[KernelMatmulOp, ...]:
    """收集 entry 中合格 TSM matmul。

    功能说明:
    - entry 任意嵌套 region 中包含 `func.call` 时 fail-fast。
    - entry 任意嵌套 region 中的合格 TSM `kernel.matmul` 都会参与 patternize 判定。
    - 合格 matmul 可以为一个或多个；pattern 复制完整 entry body，所有合格 matmul 都进入两个 pattern body。

    使用示例:
    - eligible = _eligible_matmul_ops(entry_func)
    """

    _entry_body_ops(entry_func)
    if any(isinstance(op, func.CallOp) for op in entry_func.walk()):
        raise _kernel_pattern_error("entry_point func.call unsupported")
    return tuple(op for op in entry_func.walk() if _is_eligible_tsm_matmul(op))


def _clone_pattern_func(entry_func: func.FuncOp, pattern_name: str, pattern_id: int, pipeline: str) -> func.FuncOp:
    """克隆 entry body 为 pattern 函数。

    功能说明:
    - 移除 `entry_point`，追加 `kernel.pattern_id` 与 `kernel.transform_pipeline` attrs。

    使用示例:
    - pattern = _clone_pattern_func(entry, "entry_pattern0", 0, pipeline)
    """

    pattern_func = entry_func.clone()
    pattern_func.sym_name = StringAttr(pattern_name)
    pattern_func.attributes.pop("entry_point", None)
    pattern_func.attributes["kernel.pattern_id"] = IntAttr(pattern_id)
    pattern_func.attributes["kernel.transform_pipeline"] = StringAttr(pipeline)
    return pattern_func


def _launch_branch(callee: str, args: tuple[SSAValue, ...], arg_types: tuple[Attribute, ...]) -> Region:
    """构造单个 `tuner.launch + scf.yield` 分支。

    功能说明:
    - args 来自 host wrapper block arguments，按原顺序透传给 pattern 函数。

    使用示例:
    - region = _launch_branch("entry_pattern0", tuple(block.args), tuple(input_types))
    """

    _ = arg_types
    block = Block()
    block.add_op(TunerLaunchOp(callee, args))
    block.add_op(scf.YieldOp())
    return Region(block)


def _build_host_dispatcher(entry_func: func.FuncOp, pattern_names: tuple[str, str]) -> func.FuncOp:
    """构造替换 entry 的 host dispatcher。

    功能说明:
    - 保持函数名、签名和原 attributes。
    - body 固定为 `tuner.select -> symbol.const 0 -> symbol.eq -> scf.if -> func.return`。
    - pattern 引用只存在于 `tuner.select.patterns`，不得生成 `tuner.pattern_ref` IR op。

    使用示例:
    - dispatcher = _build_host_dispatcher(entry_func, ("entry_pattern0", "entry_pattern1"))
    """

    input_types = list(entry_func.function_type.inputs.data)
    output_types = list(entry_func.function_type.outputs.data)
    if output_types:
        raise _kernel_pattern_error("entry_point dispatcher must have zero results")
    block = Block(arg_types=input_types)
    for new_arg, old_arg in zip(block.args, entry_func.args, strict=True):
        new_arg.name_hint = old_arg.name_hint
    select = TunerSelectOp(pattern_names)
    generic_symbol_const = UnregisteredOp.with_name("symbol.const")
    zero = generic_symbol_const.create(
        attributes={"value": IntAttr(0)},
        result_types=[SymbolValueType.from_expr("0")],
    )
    generic_symbol_eq = UnregisteredOp.with_name("symbol.eq")
    compare = generic_symbol_eq.create(
        operands=[select.result, zero.results[0]],
        result_types=[i1],
    )
    launch_args = tuple(block.args)
    if_op = scf.IfOp(
        compare.results[0],
        [],
        _launch_branch(pattern_names[0], launch_args, tuple(input_types)),
        _launch_branch(pattern_names[1], launch_args, tuple(input_types)),
    )
    block.add_ops([select, zero, compare, if_op, func.ReturnOp()])
    dispatcher = func.FuncOp(
        entry_func.sym_name.data,
        (input_types, output_types),
        Region(block),
        visibility=entry_func.sym_visibility,
        arg_attrs=entry_func.arg_attrs,
        res_attrs=entry_func.res_attrs,
    )
    dispatcher.attributes.update(dict(entry_func.attributes))
    verify_generated_ops([select, zero, compare, if_op, dispatcher])
    return dispatcher


def _replace_entry_with_patterns(module: ModuleOp, entry_func: func.FuncOp) -> None:
    """将 entry 替换为 dispatcher 并插入两个 pattern func。

    功能说明:
    - 先检查待生成 pattern 名称冲突。
    - 以原 entry 的 module 位置作为插入锚点，保持输出顺序稳定。

    使用示例:
    - _replace_entry_with_patterns(module, entry_func)
    """

    existing_names = {op.sym_name.data for op in _module_funcs(module)}
    entry_name = entry_func.sym_name.data
    pattern_names = (f"{entry_name}_pattern0", f"{entry_name}_pattern1")
    if any(name in existing_names for name in pattern_names):
        raise _kernel_pattern_error("pattern name collision")
    dispatcher = _build_host_dispatcher(entry_func, pattern_names)
    patterns = tuple(
        _clone_pattern_func(entry_func, pattern_name, index, pipeline)
        for index, (pattern_name, pipeline) in enumerate(zip(pattern_names, _PATTERN_PIPELINES, strict=True))
    )
    parent_block = entry_func.parent_block()
    if parent_block is None:
        raise _kernel_pattern_error("entry_point parent block missing")
    parent_block.insert_op_before(dispatcher, entry_func)
    insert_after = dispatcher
    for pattern in patterns:
        parent_block.insert_op_after(pattern, insert_after)
        insert_after = pattern
    parent_block.erase_op(entry_func)


class KernelPatternAttachPass(Pass):
    """生成 pattern dispatcher 的 ModulePass。

    功能说明:
    - 固定公开 pass 名称为 `kernel-pattern-attach`。
    - 无专属 options；由 `apply(ctx, module)` 原地改写 module。

    使用示例:
    - KernelPatternAttachPass().apply(Context(), module)

    关联文件:
    - spec: spec/pass/kernel_pattern_attach.md
    - test: test/passes/test_kernel_pattern_attach.py
    - 功能实现: kernel_gen/passes/kernel_pattern_attach.py
    """

    name = "kernel-pattern-attach"

    @classmethod
    def from_options(cls: type["KernelPatternAttachPass"], options: dict[str, str]) -> "KernelPatternAttachPass":
        """从 registry options 构造 pass。

        功能说明:
        - 当前不接受专属 options；未知 option 稳定失败。

        使用示例:
        - KernelPatternAttachPass.from_options({})
        """

        if options:
            unknown = ", ".join(sorted(options))
            raise _kernel_pattern_error(f"options unknown: {unknown}")
        return cls()

    def apply(self: "KernelPatternAttachPass", ctx: Context, module: ModuleOp) -> None:
        """执行 kernel-pattern-attach。

        功能说明:
        - 校验唯一 entry_point。
        - 无合格 TSM matmul 时 no-op；有一个或多个合格 matmul 时生成 dispatcher 和 pattern funcs。

        使用示例:
        - KernelPatternAttachPass().apply(Context(), module)
        """

        _ = ctx
        module = ensure_builtin_module(module)
        entry_func = _entry_point_func(module)
        eligible = _eligible_matmul_ops(entry_func)
        if not eligible:
            return
        _replace_entry_with_patterns(module, entry_func)


__all__ = ["KernelPatternAttachPass"]
