"""buffer-results-to-out-params lowering pass.

创建者: 朽木露琪亚
最后一次更改: jcc你莫辜负

功能说明:
- 将 `func.func` 中所有 `memory` 返回值改写为最前置 out 参数。
- 同步改写模块内可解析 `func.call`，把 caller 侧旧 memory result SSA 收口为显式 out 实参。
- 当前覆盖单个 `memory` 返回、多 `memory` 返回和 `memory + scalar` 混合返回；external declaration 仍显式失败。

使用示例:
- from xdsl.context import Context
- from kernel_gen.passes.buffer_results_to_out_params import BufferResultsToOutParamsPass
- BufferResultsToOutParamsPass().apply(Context(), module)

关联文件:
- spec: spec/pass/buffer_results_to_out_params.md
- test: test/pass/test_buffer_results_to_out_params.py
- 功能实现: kernel_gen/passes/buffer_results_to_out_params.py
"""

from __future__ import annotations
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError

from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, DictionaryAttr, ModuleOp, StringAttr
from xdsl.ir import Attribute, Block, BlockArgument, Operation, SSAValue
from xdsl.passes import ModulePass
from xdsl.pattern_rewriter import (
    GreedyRewritePatternApplier,
    PatternRewriter,
    PatternRewriteWalker,
    RewritePattern,
    op_type_rewrite_pattern,
)
from xdsl.rewriter import InsertPoint

from kernel_gen.dialect.dma import DmaAllocOp, DmaDesliceOp
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import Symbol
from kernel_gen.passes.common import ensure_builtin_module


@dataclass(frozen=True)
class OutputSignature:
    """封装函数输出的 memory/scalar 结果分解信息。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 统一收敛 `memory` 与 `scalar` 输出索引划分。
    - 便于在校验、callsite 改写与 callee 改写间共享同一拆分逻辑。

    使用示例:
    - signature = OutputSignature([memory_type], [0], [])

    关联文件:
    - spec: spec/pass/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/buffer_results_to_out_params.py
    """

    output_types: list[Attribute]
    memory_indices: list[int]
    scalar_indices: list[int]


@dataclass(frozen=True)
class RewriteTarget:
    """记录待改写函数的输入/输出签名信息。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 把 `func.func` 与其输出拆分签名绑定，避免后续重复推导。
    - 保证 callsite 改写与 callee 改写基于同一套输出索引。

    使用示例:
    - target = RewriteTarget(func_op, list(func_op.function_type.inputs.data), signature)

    关联文件:
    - spec: spec/pass/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/buffer_results_to_out_params.py
    """

    func_op: func.FuncOp
    input_types: list[Attribute]
    output_signature: OutputSignature


@dataclass(frozen=True)
class BufferResultsToOutParamsCallPattern(RewritePattern):
    """按 `func.call` 重写 buffer-results-to-out-params。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅处理模块内命中的旧 `memory result` callsite。
    - 通过 pattern rewrite 将 caller 侧显式 out buffer 与新 `func.call` 一并插入。

    使用示例:
    - pattern = BufferResultsToOutParamsCallPattern(targets)

    关联文件:
    - spec: spec/pass/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/buffer_results_to_out_params.py
    """

    targets: dict[str, RewriteTarget]

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: func.CallOp, rewriter: PatternRewriter, /) -> None:
        callee_name = op.callee.root_reference.data
        target = self.targets.get(callee_name)
        if target is None:
            return
        if not any(isinstance(result.type, NnMemoryType) for result in op.results):
            return
        memory_indices = target.output_signature.memory_indices
        output_types = target.output_signature.output_types
        if len(op.arguments) != len(target.input_types) or len(op.results) != len(output_types):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, 
                f"half-rewritten ABI is not supported: callsite for {callee_name} does not match callee signature"
            )
        out_allocs: list[DmaAllocOp] = []
        for result_index in memory_indices:
            result_type = op.results[result_index].type
            if not isinstance(result_type, NnMemoryType):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, 
                    "half-rewritten ABI is not supported: "
                    f"callsite for {callee_name} expects memory result at index {result_index}"
                )
            out_allocs.append(DmaAllocOp([], result_type))
        scalar_indices = target.output_signature.scalar_indices
        new_call = func.CallOp(
            callee_name,
            [*(alloc.result for alloc in out_allocs), *op.arguments],
            [output_types[index] for index in scalar_indices],
        )
        memory_index_set = set(memory_indices)
        scalar_results = iter(new_call.results)
        new_results: list[SSAValue] = []
        for result_index in range(len(output_types)):
            if result_index in memory_index_set:
                new_results.append(out_allocs[memory_indices.index(result_index)].result)
            else:
                new_results.append(next(scalar_results))
        rewriter.replace_matched_op([*out_allocs, new_call], new_results)


@dataclass(frozen=True)
class BufferResultsToOutParamsFuncPattern(RewritePattern):
    """按 `func.func` 重写 buffer-results-to-out-params。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 将命中的 memory 返回函数改写为前置 out 参数。
    - 只处理候选集合中仍保留 memory 输出的函数。

    使用示例:
    - pattern = BufferResultsToOutParamsFuncPattern(targets)

    关联文件:
    - spec: spec/pass/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/buffer_results_to_out_params.py
    """

    targets: dict[str, RewriteTarget]

    @op_type_rewrite_pattern
    def match_and_rewrite(self, op: func.FuncOp, rewriter: PatternRewriter, /) -> None:
        target = self.targets.get(op.sym_name.data)
        if target is None or not target.output_signature.memory_indices:
            return
        if list(op.function_type.inputs.data) != target.input_types:
            return
        if list(op.function_type.outputs.data) != target.output_signature.output_types:
            return
        block = op.body.blocks.first
        if block is None:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "function body is empty")
        output_types = target.output_signature.output_types
        memory_indices = target.output_signature.memory_indices
        return_op = op.get_return_op()
        if return_op is None or len(return_op.arguments) != len(output_types):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, 
                "return operand count must match function outputs for buffer-results-to-out-params"
            )
        new_out_args: list[BlockArgument] = []
        for insert_index, memory_output_index in enumerate(memory_indices):
            memory_type = output_types[memory_output_index]
            if not isinstance(memory_type, NnMemoryType):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "memory output index must point to nn.memory")
            new_out_args.append(rewriter.insert_block_argument(block, insert_index, memory_type))
        existing = list(op.arg_attrs.data) if op.arg_attrs is not None else []
        total_old_args = len(op.function_type.inputs.data)
        while len(existing) < total_old_args:
            existing.append(DictionaryAttr({}))
        prepended_attrs = [
            DictionaryAttr({"name": StringAttr(f"arg{index}")}) for index in range(len(new_out_args))
        ]
        op.properties["arg_attrs"] = ArrayAttr([*prepended_attrs, *existing])
        scalar_return_values = [
            return_op.arguments[index] for index in target.output_signature.scalar_indices
        ]
        memory_return_values = [return_op.arguments[index] for index in memory_indices]
        for new_out_arg, return_value in zip(new_out_args, memory_return_values, strict=True):
            owner = getattr(return_value, "owner", None)
            if isinstance(owner, DmaDesliceOp) and owner.result == return_value:
                owner.operands[0] = new_out_arg
                rewriter.notify_op_modified(owner)
            rewriter.replace_all_uses_with(return_value, new_out_arg)
        rewriter.erase_op(return_op)
        rewriter.insert_op(func.ReturnOp(*scalar_return_values), InsertPoint.at_end(block))
        for return_value in memory_return_values:
            owner = getattr(return_value, "owner", None)
            if isinstance(owner, DmaAllocOp) and all(result.first_use is None for result in owner.results):
                rewriter.erase_op(owner)
        op.update_function_type()
        rewriter.notify_op_modified(op)


class BufferResultsToOutParamsPass(ModulePass):
    """将 `memory` 返回值改写为最前置 out 参数的 lowering pass。

    创建者: 朽木露琪亚
    最后一次更改: jcc你莫辜负

    功能说明:
    - 在模块级先做候选校验。
    - 当前实现执行“模块内可解析 callsite 同步改写 + 多 memory results / mixed returns -> 前置 out 参数”改写。
    - memory 返回会按原顺序前置为 `arg0 / arg1 / ...`，scalar 返回继续保留在 `func.return`。

    使用示例:
    - from xdsl.context import Context
    - BufferResultsToOutParamsPass().apply(Context(), module)

    关联文件:
    - spec: spec/pass/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/buffer_results_to_out_params.py
    """

    name = "buffer-results-to-out-params"

    def __init__(self: "BufferResultsToOutParamsPass", fold: bool = True) -> None:
        """初始化 buffer-results-to-out-params pass 公共选项。

        创建者: 大闸蟹
        最后一次更改: 大闸蟹

        功能说明:
        - 记录 `fold` 开关，默认允许 pass 内 pattern walker 执行 folding。

        使用示例:
        - pass_obj = BufferResultsToOutParamsPass()
        - pass_obj = BufferResultsToOutParamsPass(fold=False)

        关联文件:
        - spec: spec/pass/buffer_results_to_out_params.md
        - test: test/pass/test_buffer_results_to_out_params.py
        - 功能实现: kernel_gen/passes/buffer_results_to_out_params.py
        """

        object.__setattr__(self, "fold", bool(fold))

    def apply(self, ctx: Context, module: ModuleOp) -> None:
        """执行最小骨架改写。

        创建者: 朽木露琪亚
        最后一次更改: jcc你莫辜负

        功能说明:
        - 先收集并校验候选函数。
        - 先同步改写 caller 侧 `func.call`，再改写 callee 返回合同。

        使用示例:
        - BufferResultsToOutParamsPass().apply(Context(), module)

        关联文件:
        - spec: spec/pass/buffer_results_to_out_params.md
        - test: test/pass/test_buffer_results_to_out_params.py
        - 功能实现: kernel_gen/passes/buffer_results_to_out_params.py
        """

        ensure_builtin_module(module)
        targets: dict[str, RewriteTarget] = {}
        local_funcs = {
            op.sym_name.data: op for op in module.ops if isinstance(op, func.FuncOp)
        }
        for op in module.ops:
            if not isinstance(op, func.FuncOp):
                continue
            output_types = list(op.function_type.outputs.data)
            memory_indices = [
                index
                for index, output_type in enumerate(output_types)
                if isinstance(output_type, NnMemoryType)
            ]
            if not memory_indices:
                continue
            scalar_indices = [
                index for index in range(len(output_types)) if index not in memory_indices
            ]
            if op.arg_attrs is not None:
                input_types = list(op.function_type.inputs.data)
                attrs = list(op.arg_attrs.data)
                if len(attrs) >= len(input_types):
                    leading_out_count = 0
                    for index, input_type in enumerate(input_types):
                        name_attr = attrs[index].data.get("name")
                        if not isinstance(input_type, NnMemoryType):
                            break
                        if not isinstance(name_attr, StringAttr) or name_attr.data != f"arg{index}":
                            break
                        leading_out_count += 1
                    if leading_out_count >= len(memory_indices):
                        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, 
                            "half-rewritten ABI is not supported: "
                            f"function {op.sym_name.data} already has leading out params but still returns memory"
                        )
            first_block = op.body.blocks.first
            is_external_like = op.is_declaration or (first_block is not None and tuple(first_block.ops) == ())
            if is_external_like:
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "external declaration is not supported")
            if len(tuple(op.body.blocks)) != 1:
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "only single-block functions are supported")
            return_op = op.get_return_op()
            if return_op is None or len(return_op.arguments) != len(output_types):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, 
                    "return operand count must match function outputs for buffer-results-to-out-params"
                )
            targets[op.sym_name.data] = RewriteTarget(
                op,
                list(op.function_type.inputs.data),
                OutputSignature(output_types, memory_indices, scalar_indices),
            )
        for op in module.walk():
            if not isinstance(op, func.CallOp):
                continue
            callee_name = op.callee.root_reference.data
            callee = local_funcs.get(callee_name)
            if callee is None:
                continue
            target = targets.get(callee_name)
            expected_inputs = (
                target.input_types if target is not None else list(callee.function_type.inputs.data)
            )
            expected_outputs = (
                target.output_signature.output_types
                if target is not None
                else list(callee.function_type.outputs.data)
            )
            actual_inputs = [argument.type for argument in op.arguments]
            actual_outputs = [result.type for result in op.results]
            if actual_inputs == expected_inputs and actual_outputs == expected_outputs:
                continue
            if target is not None or any(isinstance(result.type, NnMemoryType) for result in op.results):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, 
                    f"half-rewritten ABI is not supported: callsite for {callee_name} does not match callee signature"
                )
        if ctx.get_optional_dialect(Symbol.name) is None:
            ctx.load_dialect(Symbol)
        PatternRewriteWalker(
            GreedyRewritePatternApplier(
                get_buffer_results_to_out_params_pass_patterns(targets),
                ctx=ctx,
                folding_enabled=self.fold,
                dce_enabled=False,
            )
        ).rewrite_module(module)

    def run(self, module: ModuleOp) -> ModuleOp:
        """兼容旧 `run()` 入口。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 过渡期保留旧调用方式，内部复用 `apply()`。

        使用示例:
        - module = BufferResultsToOutParamsPass().run(module)

        关联文件:
        - spec: spec/pass/buffer_results_to_out_params.md
        - test: test/pass/test_buffer_results_to_out_params.py
        - 功能实现: kernel_gen/passes/buffer_results_to_out_params.py
        """

        self.apply(Context(), module)
        return module


def get_buffer_results_to_out_params_pass_patterns(
    targets: dict[str, RewriteTarget],
) -> list[RewritePattern]:
    """返回 `buffer-results-to-out-params` pass 使用的公开 pattern 列表。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 为外部测试、组合 pass 和公开 API 提供稳定的 pattern 构造入口。
    - 保持 `func.call` 与 `func.func` 两段改写的 pattern 装配顺序稳定。

    使用示例:
    - patterns = get_buffer_results_to_out_params_pass_patterns(targets)
    - walker = PatternRewriteWalker(GreedyRewritePatternApplier(patterns, ctx=ctx))

    关联文件:
    - spec: spec/pass/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/buffer_results_to_out_params.py
    """

    return [
        BufferResultsToOutParamsCallPattern(targets),
        BufferResultsToOutParamsFuncPattern(targets),
    ]


__all__ = [
    "BufferResultsToOutParamsPass",
    "BufferResultsToOutParamsCallPattern",
    "BufferResultsToOutParamsFuncPattern",
    "get_buffer_results_to_out_params_pass_patterns",
]
