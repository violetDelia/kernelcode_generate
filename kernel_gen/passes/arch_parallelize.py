"""arch-parallelize pass.


功能说明:
- 提供 standalone IR-level `arch-parallelize` pass。
- 遍历 `builtin.module` 中所有非声明 `func.func`，对未带 block 并行语义的函数执行 block 级分发。
- 当前只支持 `parallel_level="block"`：单顶层 `symbol.for` 改写为 block-strided loop；无顶层 loop 时用 block0 guard 包裹原 body。

API 列表:
- `class ArchParallelizePass(target: str = "npu_demo", parallel_level: str = "block")`
- `ArchParallelizePass.from_options(options: dict[str, str]) -> ArchParallelizePass`
- `ArchParallelizePass.apply(ctx: Context, module: ModuleOp) -> None`

使用示例:
- from xdsl.context import Context
- from kernel_gen.passes.arch_parallelize import ArchParallelizePass
- ArchParallelizePass(target="npu_demo").apply(Context(), module)

关联文件:
- spec: spec/pass/arch_parallelize.md
- test: test/passes/test_arch_parallelize.py
- 功能实现: kernel_gen/passes/arch_parallelize.py
"""

from __future__ import annotations

from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects import func, scf
from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import Attribute, Block, Operation, SSAValue
from xdsl.utils.exceptions import VerifyException

from kernel_gen.dialect.arch import ArchGetBlockIdOp, ArchGetBlockNumOp
from kernel_gen.dialect.symbol import (
    SymbolAddOp,
    SymbolConstOp,
    SymbolDivOp,
    SymbolFloorDivOp,
    SymbolForOp,
    SymbolGetDimOp,
    SymbolGetStrideOp,
    SymbolIterType,
    SymbolMaxOp,
    SymbolMinOp,
    SymbolMulOp,
    SymbolNeOp,
    SymbolSubOp,
    SymbolValueType,
)
from kernel_gen.passes.common import ensure_builtin_module, raise_pass_contract_error
from kernel_gen.passes.pass_manager import Pass
from kernel_gen.target import registry as target_registry

_VALID_OPTIONS = {"target", "parallel_level"}
_SYMBOL_SETUP_OPS = (
    SymbolConstOp,
    SymbolAddOp,
    SymbolSubOp,
    SymbolMulOp,
    SymbolDivOp,
    SymbolFloorDivOp,
    SymbolMinOp,
    SymbolMaxOp,
    SymbolGetDimOp,
    SymbolGetStrideOp,
)
_UNKNOWN_SYMBOL_EXPR = "?"


@dataclass(frozen=True)
class _LoopShape:
    """当前文件内的顶层 loop 分析结果。

    功能说明:
    - 保存 `ArchParallelizePass` 对单个函数 body 的最小分类结果。
    - 仅供本文件内部使用，不作为公开 API。

    使用示例:
    - shape = _LoopShape("no_loop")
    """

    kind: str
    outer_loop: SymbolForOp | None = None


def _fail(detail: str) -> None:
    """抛出 arch-parallelize pass 合同错误。

    功能说明:
    - 统一稳定错误前缀为 `ArchParallelizePassError`。

    使用示例:
    - _fail("unsupported loop structure")
    """

    raise_pass_contract_error("ArchParallelizePassError", detail)


def _validate_options(target: str, parallel_level: str) -> None:
    """校验 pass 构造参数。

    功能说明:
    - `target` 必须是非空字符串。
    - 当前只接受 `parallel_level="block"`。

    使用示例:
    - _validate_options("npu_demo", "block")
    """

    if not isinstance(target, str) or target.strip() == "":
        _fail("target must be non-empty string")
    if parallel_level != "block":
        if parallel_level == "block_thread":
            _fail("parallel_level block_thread is not supported yet")
        _fail("unsupported parallel_level")


def _validate_target_and_get_block_num(target: str) -> int:
    """校验 target 支持 block 并行并读取静态 block_num。

    功能说明:
    - 通过公开 target registry 查询 `arch.get_block_id` 支持性与 `block_num` 硬件字段。

    使用示例:
    - block_num = _validate_target_and_get_block_num("npu_demo")
    """

    try:
        has_block_id = target_registry.is_arch_op_supported(target, "arch.get_block_id")
        block_num = target_registry.get_target_hardware(target, "block_num")
    except ValueError:
        _fail("target not registered")
    if not has_block_id:
        _fail("target does not support arch.get_block_id")
    if not isinstance(block_num, int) or isinstance(block_num, bool) or block_num <= 0:
        _fail("target block_num must be positive integer")
    return block_num


def _iter_non_declaration_funcs(module: ModuleOp) -> list[func.FuncOp]:
    """列出 module 中所有非声明 `func.func`。

    功能说明:
    - 只遍历 module 顶层 op，声明函数跳过。

    使用示例:
    - funcs = _iter_non_declaration_funcs(module)
    """

    return [op for op in module.ops if isinstance(op, func.FuncOp) and not op.is_declaration]


def _has_existing_block_parallel_ops(func_op: func.FuncOp) -> bool:
    """判断函数是否已包含 block 相关 arch op。

    功能说明:
    - 发现 `arch.get_block_id` 或 `arch.get_block_num` 时，当前函数直接跳过。

    使用示例:
    - if _has_existing_block_parallel_ops(func_op): return
    """

    return any(isinstance(op, (ArchGetBlockIdOp, ArchGetBlockNumOp)) for op in func_op.walk())


def _get_single_entry_block(func_op: func.FuncOp) -> Block:
    """校验并返回单块函数体。

    功能说明:
    - 拒绝有返回值函数和 multi-block 函数体。

    使用示例:
    - block = _get_single_entry_block(func_op)
    """

    if tuple(func_op.function_type.outputs.data):
        _fail("function return values are not supported")
    blocks = tuple(func_op.body.blocks)
    if len(blocks) != 1:
        _fail("multi-block func body is not supported")
    return blocks[0]


def _split_body_and_return(entry_block: Block) -> tuple[list[Operation], func.ReturnOp]:
    """拆分函数 body op 与末尾 `func.return`。

    功能说明:
    - 要求函数体以无 operand 的 `func.return` 结束。

    使用示例:
    - body_ops, return_op = _split_body_and_return(block)
    """

    ops = list(entry_block.ops)
    if not ops or not isinstance(ops[-1], func.ReturnOp):
        _fail("unsupported loop structure")
    return_op = ops[-1]
    if tuple(return_op.arguments):
        _fail("function return values are not supported")
    return ops[:-1], return_op


def _analyze_loop_shape(body_ops: list[Operation]) -> _LoopShape:
    """分析函数顶层 loop 结构。

    功能说明:
    - 无顶层 loop 时返回 `no_loop`。
    - 一个顶层 `symbol.for` 且同级仅包含 loop 前纯 symbol setup 时返回可改写结果。
    - 多个顶层 `symbol.for` 或 loop 同级出现不可判 op 时返回 unsupported。

    使用示例:
    - shape = _analyze_loop_shape(body_ops)
    """

    top_level_loops = [op for op in body_ops if isinstance(op, SymbolForOp)]
    if not top_level_loops:
        return _LoopShape("no_loop")
    if len(top_level_loops) > 1:
        return _LoopShape("multiple_top_level_loops")
    outer_loop = top_level_loops[0]
    outer_index = body_ops.index(outer_loop)
    for index, op in enumerate(body_ops):
        if op is outer_loop:
            continue
        if index > outer_index or not _is_allowed_symbol_setup_op(op):
            return _LoopShape("unsupported")
    if not _can_transform_loop_nest(outer_loop):
        return _LoopShape("loop_carried")
    return _LoopShape("transformable_loop_nest", outer_loop)


def _is_allowed_symbol_setup_op(op: Operation) -> bool:
    """判断顶层 op 是否为唯一 loop 前的纯 symbol setup。

    功能说明:
    - 只放行公开 symbol dialect 的无副作用边界构造 op。

    使用示例:
    - if _is_allowed_symbol_setup_op(op): ...
    """

    return isinstance(op, _SYMBOL_SETUP_OPS)


def _can_transform_loop_nest(outer_loop: SymbolForOp) -> bool:
    """判断顶层 `symbol.for` 是否可按 block 分片。

    功能说明:
    - 当前仅支持无 carried-value 的单块 `symbol.for`，且 start/end/step 均为 `!symbol.int`。

    使用示例:
    - if _can_transform_loop_nest(loop): ...
    """

    if outer_loop.init is not None or outer_loop.result is not None:
        return False
    blocks = tuple(outer_loop.body.blocks)
    if len(blocks) != 1:
        return False
    if len(blocks[0].args) != 1:
        return False
    for value in (outer_loop.start, outer_loop.end, outer_loop.step):
        if not isinstance(SSAValue.get(value).type, SymbolValueType):
            return False
    return True


def _symbol_expr(value: SSAValue | Operation | Attribute) -> str:
    """提取 symbol.int 的公开表达式文本。

    功能说明:
    - 无法证明是 `SymbolValueType` 时返回 `?`，用于保持改写保守可验证。

    使用示例:
    - expr = _symbol_expr(loop.start)
    """

    if isinstance(value, Attribute):
        value_type = value
    else:
        value_type = SSAValue.get(value).type
    if isinstance(value_type, SymbolValueType):
        return value_type.expr.expr.data
    return _UNKNOWN_SYMBOL_EXPR


def _symbol_type_for_binary(lhs: SSAValue | Operation, op: str, rhs: SSAValue | Operation) -> SymbolValueType:
    """为新建 symbol 二元 op 构造结果类型。

    功能说明:
    - 复用 `SymbolValueType.from_expr(...)` 的公开 canonical 规则。

    使用示例:
    - result_type = _symbol_type_for_binary(lhs, "*", rhs)
    """

    return SymbolValueType.from_expr(f"{_symbol_expr(lhs)} {op} {_symbol_expr(rhs)}")


def _loop_iter_type(start: SSAValue | Operation, end: SSAValue | Operation, step: SSAValue | Operation) -> SymbolIterType:
    """根据 loop 三个边界值构造 block argument 类型。

    功能说明:
    - 保证新 loop 的 `iter` 属性和 induction variable 类型与新边界一致。

    使用示例:
    - iter_type = _loop_iter_type(new_start.result, old_end, new_step.result)
    """

    return SymbolIterType.from_bounds(_symbol_expr(start), _symbol_expr(end), _symbol_expr(step))


def _clone_loop_body_with_iter_type(old_loop: SymbolForOp, iter_type: SymbolIterType) -> Block:
    """克隆 loop body 并替换 induction variable 类型。

    功能说明:
    - 不直接修改 xDSL `BlockArgument` 内部字段；通过新建 block 与公开 clone 入口保持 SSA 映射。

    使用示例:
    - new_block = _clone_loop_body_with_iter_type(loop, iter_type)
    """

    old_block = tuple(old_loop.body.blocks)[0]
    new_block = Block(arg_types=[iter_type])
    value_mapper: dict[SSAValue, SSAValue] = {old_block.args[0]: new_block.args[0]}
    for old_op in old_block.ops:
        cloned = old_op.clone(value_mapper=value_mapper)
        new_block.add_op(cloned)
        for old_result, new_result in zip(old_op.results, cloned.results, strict=True):
            value_mapper[old_result] = new_result
    return new_block


def _rewrite_outer_loop_for_blocks(outer_loop: SymbolForOp, block_num: int) -> None:
    """把唯一顶层 `symbol.for` 改写为 block-strided loop。

    功能说明:
    - 在旧 loop 前插入 `arch.get_block_id`、静态 `symbol.const block_num` 与新边界计算。
    - 用克隆出的新 loop 替换旧 loop，内层 loop 和普通 body op 保持在新 loop body 内。

    使用示例:
    - _rewrite_outer_loop_for_blocks(loop, 1)
    """

    parent_block = outer_loop.parent_block()
    if parent_block is None:
        _fail("unsupported loop structure")
    old_start = SSAValue.get(outer_loop.start)
    old_end = SSAValue.get(outer_loop.end)
    old_step = SSAValue.get(outer_loop.step)
    block_id = ArchGetBlockIdOp()
    block_count = SymbolConstOp(block_num)
    block_offset = SymbolMulOp(
        block_id.result,
        old_step,
        _symbol_type_for_binary(block_id.result, "*", old_step),
    )
    new_start = SymbolAddOp(
        old_start,
        block_offset.result,
        _symbol_type_for_binary(old_start, "+", block_offset.result),
    )
    new_step = SymbolMulOp(
        old_step,
        block_count.result,
        _symbol_type_for_binary(old_step, "*", block_count.result),
    )
    new_block = _clone_loop_body_with_iter_type(
        outer_loop,
        _loop_iter_type(new_start.result, old_end, new_step.result),
    )
    new_loop = SymbolForOp(new_start.result, old_end, new_step.result, new_block)
    parent_block.insert_ops_before(
        [block_id, block_count, block_offset, new_start, new_step, new_loop],
        outer_loop,
    )
    outer_loop.detach()


def _rewrite_no_loop_as_block0_only(entry_block: Block, body_ops: list[Operation], return_op: func.ReturnOp) -> None:
    """把无 loop 函数 body 包裹为 block0-only guard。

    功能说明:
    - 非 block0 分支只执行空 `scf.yield`。
    - block0 分支执行原 body，`func.return` 保持在 `scf.if` 外。

    使用示例:
    - _rewrite_no_loop_as_block0_only(block, body_ops, return_op)
    """

    block_id = ArchGetBlockIdOp()
    zero = SymbolConstOp(0)
    is_not_block0 = SymbolNeOp(block_id.result, zero.result)
    true_block = Block()
    true_block.add_op(scf.YieldOp())
    false_block = Block()
    for op in body_ops:
        op.detach()
        false_block.add_op(op)
    false_block.add_op(scf.YieldOp())
    if_op = scf.IfOp(is_not_block0.result, [], [true_block], [false_block])
    entry_block.insert_ops_before([block_id, zero, is_not_block0, if_op], return_op)


def _rewrite_func(func_op: func.FuncOp, block_num: int) -> None:
    """处理单个非声明函数。

    功能说明:
    - 已有 block 并行 op 时跳过。
    - 否则按 loop 结构选择 block-strided rewrite、block0 guard 或稳定失败。

    使用示例:
    - _rewrite_func(func_op, block_num)
    """

    if _has_existing_block_parallel_ops(func_op):
        return
    entry_block = _get_single_entry_block(func_op)
    body_ops, return_op = _split_body_and_return(entry_block)
    loop_shape = _analyze_loop_shape(body_ops)
    if loop_shape.kind == "no_loop":
        _rewrite_no_loop_as_block0_only(entry_block, body_ops, return_op)
        return
    if loop_shape.kind == "transformable_loop_nest" and loop_shape.outer_loop is not None:
        _rewrite_outer_loop_for_blocks(loop_shape.outer_loop, block_num)
        return
    if loop_shape.kind == "multiple_top_level_loops":
        _fail("multiple top-level symbol.for loops are not supported")
    if loop_shape.kind == "loop_carried":
        _fail("loop-carried symbol.for is not supported")
    _fail("unsupported loop structure")


class ArchParallelizePass(Pass):
    """arch-parallelize pass。

    功能说明:
    - 公开 pass 名称为 `arch-parallelize`。
    - 按 target registry 静态 `block_num` 物化 block 分片 IR。
    - 本轮只实现 block 级 standalone IR pass，不接入默认 pipeline。

    使用示例:
    - ArchParallelizePass(target="npu_demo", parallel_level="block").apply(Context(), module)
    """

    name = "arch-parallelize"

    def __init__(self, target: str = "npu_demo", parallel_level: str = "block") -> None:
        """初始化 pass 参数。

        功能说明:
        - 保存目标 target 名称与并行层级。

        使用示例:
        - pass_obj = ArchParallelizePass("npu_demo", "block")
        """

        self.target = target
        self.parallel_level = parallel_level

    @classmethod
    def from_options(cls, options: dict[str, str]) -> "ArchParallelizePass":
        """从 registry options 构造 `ArchParallelizePass`。

        功能说明:
        - 只接受 `target` 与 `parallel_level` 两个 pass 专属 option。
        - 未提供时使用公开默认值。

        使用示例:
        - ArchParallelizePass.from_options({"target": "npu_demo", "parallel_level": "block"})
        """

        unknown_options = sorted(set(options) - _VALID_OPTIONS)
        if unknown_options:
            _fail("unknown option(s): " + ", ".join(unknown_options))
        return cls(
            target=options.get("target", "npu_demo"),
            parallel_level=options.get("parallel_level", "block"),
        )

    def apply(self, ctx: Context, module: ModuleOp) -> None:
        """执行 arch-parallelize pass。

        功能说明:
        - 校验参数与 target 后，遍历所有非声明函数并独立处理。
        - 最终运行 `module.verify()`，失败时转成稳定 pass 错误。

        使用示例:
        - ArchParallelizePass().apply(Context(), module)
        """

        _ = ctx
        ensure_builtin_module(module)
        _validate_options(self.target, self.parallel_level)
        block_num = _validate_target_and_get_block_num(self.target)
        for func_op in _iter_non_declaration_funcs(module):
            _rewrite_func(func_op, block_num)
        try:
            module.verify()
        except VerifyException as exc:
            raise_pass_contract_error("ArchParallelizePassVerifierError", str(exc))


__all__ = ["ArchParallelizePass"]
