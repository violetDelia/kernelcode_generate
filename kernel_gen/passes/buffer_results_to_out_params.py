"""buffer-results-to-out-params lowering pass.

创建者: 朽木露琪亚
最后一次更改: jcc你莫辜负

功能说明:
- 将 `func.func` 中所有 `memory` 返回值改写为最前置 out 参数。
- 同步改写模块内可解析 `func.call`，把 caller 侧旧 memory result SSA 收口为显式 out 实参。
- 当前覆盖单个 `memory` 返回、多 `memory` 返回和 `memory + scalar` 混合返回；external declaration 仍显式失败。

使用示例:
- from kernel_gen.passes.buffer_results_to_out_params import BufferResultsToOutParamsPass
- module = BufferResultsToOutParamsPass().run(module)

关联文件:
- spec: spec/pass/lowering/buffer_results_to_out_params.md
- test: test/pass/test_buffer_results_to_out_params.py
- 功能实现: kernel_gen/passes/buffer_results_to_out_params.py
"""

from __future__ import annotations

from dataclasses import dataclass

from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, DictionaryAttr, ModuleOp, StringAttr
from xdsl.ir import Attribute, Block, BlockArgument, Operation, SSAValue

from kernel_gen.dialect.dma import DmaAllocOp
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.passes.pass_manager import Pass


class BufferResultsToOutParamsError(ValueError):
    """buffer-results-to-out-params pass 的显式错误。

    创建者: 朽木露琪亚
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一承载 external declaration、半改半留和当前骨架未覆盖场景的错误。

    使用示例:
    - raise BufferResultsToOutParamsError("external declaration is not supported")

    关联文件:
    - spec: spec/pass/lowering/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/buffer_results_to_out_params.py
    """


@dataclass(frozen=True)
class _OutputSignature:
    """封装函数输出的 memory/scalar 结果分解信息。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 统一收敛 `memory` 与 `scalar` 输出索引划分。
    - 便于在校验、callsite 改写与 callee 改写间共享同一拆分逻辑。

    使用示例:
    - signature = _output_signature(func_op)

    关联文件:
    - spec: spec/pass/lowering/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/buffer_results_to_out_params.py
    """

    output_types: list[Attribute]
    memory_indices: list[int]
    scalar_indices: list[int]


@dataclass(frozen=True)
class _RewriteTarget:
    """记录待改写函数的输入/输出签名信息。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 把 `func.func` 与其输出拆分签名绑定，避免后续重复推导。
    - 保证 callsite 改写与 callee 改写基于同一套输出索引。

    使用示例:
    - target = _build_rewrite_target(func_op)

    关联文件:
    - spec: spec/pass/lowering/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/buffer_results_to_out_params.py
    """

    func_op: func.FuncOp
    input_types: list[Attribute]
    output_signature: _OutputSignature


def _output_signature(func_op: func.FuncOp) -> _OutputSignature:
    """拆分 `func.func` 的输出类型为 memory/scalar 索引列表。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 固化 `function_type.outputs` 的结构化拆分逻辑。
    - 供校验、callsite 改写与 callee 改写复用。

    使用示例:
    - signature = _output_signature(func_op)

    关联文件:
    - spec: spec/pass/lowering/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/buffer_results_to_out_params.py
    """

    output_types = list(func_op.function_type.outputs.data)
    memory_indices = [
        index for index, output_type in enumerate(output_types) if isinstance(output_type, NnMemoryType)
    ]
    scalar_indices = [index for index in range(len(output_types)) if index not in memory_indices]
    return _OutputSignature(output_types, memory_indices, scalar_indices)


def _memory_output_indices(func_op: func.FuncOp) -> list[int]:
    """收集函数输出中的 memory result 索引。

    创建者: 朽木露琪亚
    最后一次更改: jcc你莫辜负

    功能说明:
    - 逐项检查 `function_type.outputs`。
    - 返回其中 `NnMemoryType` 的位置索引。

    使用示例:
    - indices = _memory_output_indices(func_op)

    关联文件:
    - spec: spec/pass/lowering/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/buffer_results_to_out_params.py
    """

    return _output_signature(func_op).memory_indices


def _has_leading_out_params(func_op: func.FuncOp, memory_count: int) -> bool:
    """判断函数签名是否已出现 rewrite 后的前置 out 参数形态。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅当存在 `arg0/arg1/...` 命名的前置参数且类型为 `nn.memory` 时视作 out 参数。
    - 用于识别“已插入 out 参数但仍保留 memory return”的半改写 ABI。

    使用示例:
    - if _has_leading_out_params(func_op, 1): ...

    关联文件:
    - spec: spec/pass/lowering/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/buffer_results_to_out_params.py
    """

    return memory_count > 0 and _leading_out_param_count(func_op) >= memory_count


def _leading_out_param_count(func_op: func.FuncOp) -> int:
    """统计函数签名前缀中连续的 out 参数个数。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 识别形如 `arg0/arg1/...` 的连续前置 `nn.memory` 参数前缀。
    - 供半改写 ABI 检测与 callsite 校验共享，避免重复解析参数名规则。

    使用示例:
    - leading_count = _leading_out_param_count(func_op)

    关联文件:
    - spec: spec/pass/lowering/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/buffer_results_to_out_params.py
    """

    if func_op.arg_attrs is None:
        return 0
    input_types = list(func_op.function_type.inputs.data)
    attrs = list(func_op.arg_attrs.data)
    if len(attrs) < len(input_types):
        return 0
    leading_count = 0
    for index, input_type in enumerate(input_types):
        name_attr = attrs[index].data.get("name")
        if not isinstance(input_type, NnMemoryType):
            break
        if not isinstance(name_attr, StringAttr) or name_attr.data != f"arg{index}":
            break
        leading_count += 1
    return leading_count


def _raise_half_rewritten(detail: str) -> None:
    """抛出半改写 ABI 的统一错误。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一补齐包含 `half-rewritten` 关键字的错误信息。
    - 避免不同分支在半改写场景下抛出不一致消息。

    使用示例:
    - _raise_half_rewritten("callsite does not match callee signature")

    关联文件:
    - spec: spec/pass/lowering/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/buffer_results_to_out_params.py
    """

    raise BufferResultsToOutParamsError(f"half-rewritten ABI is not supported: {detail}")


def _rebuild_arg_attrs(func_op: func.FuncOp, prepended: int) -> ArrayAttr[DictionaryAttr]:
    """为前置 out 参数重建 `arg_attrs`。

    创建者: 朽木露琪亚
    最后一次更改: 金铲铲大作战

    功能说明:
    - 新前置参数名固定为 `arg0`、`arg1`。
    - 原有参数属性按顺序整体后移；缺失属性时补空字典。

    使用示例:
    - attrs = _rebuild_arg_attrs(func_op, 1)

    关联文件:
    - spec: spec/pass/lowering/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/buffer_results_to_out_params.py
    """

    existing = list(func_op.arg_attrs.data) if func_op.arg_attrs is not None else []
    total_old_args = len(func_op.function_type.inputs.data)
    while len(existing) < total_old_args:
        existing.append(DictionaryAttr({}))
    prepended_attrs = [
        DictionaryAttr({"name": StringAttr(f"arg{index}")}) for index in range(prepended)
    ]
    return ArrayAttr([*prepended_attrs, *existing])


def _validate_candidate(func_op: func.FuncOp, signature: _OutputSignature) -> None:
    """校验当前最小骨架可安全改写的函数范围。

    创建者: 朽木露琪亚
    最后一次更改: jcc你莫辜负

    功能说明:
    - external declaration 直接失败。
    - 本轮只接受单 block，且 `func.return` 参数个数必须与 `function_type.outputs` 一致。
    - 多个 `memory` 返回与 `memory + scalar` 混合返回都在当前范围内。

    使用示例:
    - signature = _output_signature(func_op)
    - _validate_candidate(func_op, signature)

    关联文件:
    - spec: spec/pass/lowering/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/buffer_results_to_out_params.py
    """

    memory_indices = signature.memory_indices
    if not memory_indices:
        return
    if _has_leading_out_params(func_op, len(memory_indices)):
        _raise_half_rewritten(
            f"function {func_op.sym_name.data} already has leading out params but still returns memory"
        )
    first_block = func_op.body.blocks.first
    is_external_like = func_op.is_declaration or (
        first_block is not None and tuple(first_block.ops) == ()
    )
    if is_external_like:
        raise BufferResultsToOutParamsError("external declaration is not supported")
    if len(tuple(func_op.body.blocks)) != 1:
        raise BufferResultsToOutParamsError("only single-block functions are supported")
    return_op = func_op.get_return_op()
    if return_op is None or len(return_op.arguments) != len(func_op.function_type.outputs.data):
        raise BufferResultsToOutParamsError(
            "return operand count must match function outputs for buffer-results-to-out-params"
        )


def _build_rewrite_target(func_op: func.FuncOp) -> _RewriteTarget | None:
    """构建待改写函数的统一签名信息。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 在生成 target 前完成候选校验，保证后续改写逻辑前置失败。
    - 仅当函数存在 memory 返回值时返回目标信息。

    使用示例:
    - target = _build_rewrite_target(func_op)

    关联文件:
    - spec: spec/pass/lowering/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/buffer_results_to_out_params.py
    """

    signature = _output_signature(func_op)
    if not signature.memory_indices:
        return None
    _validate_candidate(func_op, signature)
    return _RewriteTarget(func_op, list(func_op.function_type.inputs.data), signature)


def _collect_rewrite_targets(module: ModuleOp) -> dict[str, _RewriteTarget]:
    """收集需要改写的函数，并提前做边界校验。

    创建者: 朽木露琪亚
    最后一次更改: jcc你莫辜负

    功能说明:
    - 只收集存在 `memory` 返回值的 `func.func`。
    - 在真正改写前先执行候选校验，确保模块级原子失败。

    使用示例:
    - targets = _collect_rewrite_targets(module)

    关联文件:
    - spec: spec/pass/lowering/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/buffer_results_to_out_params.py
    """

    targets: dict[str, _RewriteTarget] = {}
    for op in module.ops:
        if not isinstance(op, func.FuncOp):
            continue
        target = _build_rewrite_target(op)
        if target is None:
            continue
        targets[op.sym_name.data] = target
    return targets


def _collect_target_calls(module: ModuleOp, targets: dict[str, _RewriteTarget]) -> list[func.CallOp]:
    """收集调用待改写函数的 `func.call`。

    创建者: 朽木露琪亚
    最后一次更改: jcc你莫辜负

    功能说明:
    - 只处理模块内可解析的 `func.call`。
    - 返回所有调用待改写 callee 的调用点，交由后续统一同步改写。

    使用示例:
    - calls = _collect_target_calls(module, targets)

    关联文件:
    - spec: spec/pass/lowering/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/buffer_results_to_out_params.py
    """

    if not targets:
        return []
    target_names = set(targets)
    calls: list[func.CallOp] = []
    for op in module.walk():
        if not isinstance(op, func.CallOp):
            continue
        callee = op.callee.root_reference.data
        if callee in target_names:
            calls.append(op)
    return calls


def _callsite_involves_memory_rewrite(call_op: func.CallOp, callee: func.FuncOp) -> bool:
    """判断 local callsite 是否落在 memory-return 改写责任范围内。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 把“caller/callee 是否涉及旧 memory-return ABI 或新 out-param ABI”收口成统一判定。
    - 仅对与本 pass 责任相关的 callsite mismatch 抛出 `half-rewritten`，避免越界拒绝纯标量调用。

    使用示例:
    - if _callsite_involves_memory_rewrite(call_op, callee): ...

    关联文件:
    - spec: spec/pass/lowering/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/buffer_results_to_out_params.py
    """

    callsite_has_memory_results = any(
        isinstance(result.type, NnMemoryType) for result in call_op.results
    )
    callee_signature = _output_signature(callee)
    return (
        callsite_has_memory_results
        or bool(callee_signature.memory_indices)
        or _leading_out_param_count(callee) > 0
    )


def _validate_local_callsites(
    module: ModuleOp,
    targets: dict[str, _RewriteTarget],
) -> None:
    """在改写前校验模块内 local callsite 不存在半改写 ABI。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 对模块内可解析 `func.call` 统一校验 caller/callee 的参数个数与返回个数。
    - 若 callsite 已落入本 pass 的 memory-return/out-param 责任范围，但 caller/callee 口径不一致，则显式抛出 `half-rewritten`。

    使用示例:
    - _validate_local_callsites(module, targets)

    关联文件:
    - spec: spec/pass/lowering/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/buffer_results_to_out_params.py
    """

    local_funcs = {
        op.sym_name.data: op for op in module.ops if isinstance(op, func.FuncOp)
    }
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
        if target is not None or _callsite_involves_memory_rewrite(op, callee):
            _raise_half_rewritten(f"callsite for {callee_name} does not match callee signature")


def _rewrite_callsite(call_op: func.CallOp, targets: dict[str, _RewriteTarget]) -> None:
    """把调用待改写 callee 的 `func.call` 改成显式 out-arg 形式。

    创建者: 朽木露琪亚
    最后一次更改: jcc你莫辜负

    功能说明:
    - 在旧 `func.call` 前为每个 `memory` result 插入 `dma.alloc`，caller 侧显式提供多个 out buffer。
    - 新 `func.call` 的参数顺序固定为：所有 out 实参在前，原始输入参数整体后移。
    - 旧 memory call result SSA 全量替换为 caller 侧显式 out buffer；非 memory result 继续作为新的 `func.call` 返回值保留。

    使用示例:
    - _rewrite_callsite(call_op, targets)

    关联文件:
    - spec: spec/pass/lowering/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/buffer_results_to_out_params.py
    """

    callee_name = call_op.callee.root_reference.data
    target = targets.get(callee_name)
    if target is None:
        return
    memory_indices = target.output_signature.memory_indices
    output_types = target.output_signature.output_types
    if len(call_op.arguments) != len(target.input_types) or len(call_op.results) != len(output_types):
        _raise_half_rewritten(f"callsite for {callee_name} does not match callee signature")
    block = call_op.parent
    if not isinstance(block, Block):
        raise BufferResultsToOutParamsError("callsite rewrite requires call op to live in a block")

    out_allocs: list[DmaAllocOp] = []
    for result_index in memory_indices:
        result_type = call_op.results[result_index].type
        if not isinstance(result_type, NnMemoryType):
            _raise_half_rewritten(
                f"callsite for {callee_name} expects memory result at index {result_index}"
            )
        out_allocs.append(DmaAllocOp([], result_type))

    scalar_indices = target.output_signature.scalar_indices
    new_call = func.CallOp(
        callee_name,
        [*(alloc.result for alloc in out_allocs), *call_op.arguments],
        [output_types[index] for index in scalar_indices],
    )
    block.insert_ops_before([*out_allocs, new_call], call_op)

    for alloc, result_index in zip(out_allocs, memory_indices, strict=True):
        call_op.results[result_index].replace_by(alloc.result)
    for new_result, result_index in zip(new_call.results, scalar_indices, strict=True):
        call_op.results[result_index].replace_by(new_result)
    block.erase_op(call_op)


def _rewrite_callsites(module: ModuleOp, targets: dict[str, _RewriteTarget]) -> None:
    """同步改写所有调用待改写函数的 `func.call`。

    创建者: 朽木露琪亚
    最后一次更改: jcc你莫辜负

    功能说明:
    - 统一处理模块内 caller/callee，避免只改 `func.func` 而遗漏调用点。
    - 当前只覆盖模块内可解析的 `func.call`，允许 mixed/multi 返回同步改写。

    使用示例:
    - _rewrite_callsites(module, targets)

    关联文件:
    - spec: spec/pass/lowering/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/buffer_results_to_out_params.py
    """

    for call_op in list(_collect_target_calls(module, targets)):
        _rewrite_callsite(call_op, targets)


def _erase_dead_result_owner(value: SSAValue, block: Block) -> None:
    """删除替换后已无用途的临时结果定义。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 当前仅删除已无用途的 `dma.alloc`。
    - 避免保留仅为旧 return 服务的死临时 buffer。

    使用示例:
    - _erase_dead_result_owner(return_value, block)

    关联文件:
    - spec: spec/pass/lowering/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/buffer_results_to_out_params.py
    """

    owner = getattr(value, "owner", None)
    if isinstance(owner, DmaAllocOp) and owner.parent is block and all(
        result.first_use is None for result in owner.results
    ):
        block.erase_op(owner)


def _rewrite_memory_results_to_out_params(target: _RewriteTarget) -> None:
    """将函数返回中的所有 `memory` 结果改写为最前置 out 参数。

    创建者: 朽木露琪亚
    最后一次更改: jcc你莫辜负

    功能说明:
    - 在 block 最前按原 memory result 顺序插入 `arg0 / arg1 / ...`。
    - 将原 memory 返回值在函数体内的使用替换为新 out 参数。
    - `func.return` 仅保留非 memory 返回值；若无 scalar 返回则改为空 return。
    - 刷新函数签名，使 `function_type.outputs` 只保留原 scalar 返回。

    使用示例:
    - _rewrite_memory_results_to_out_params(func_op)

    关联文件:
    - spec: spec/pass/lowering/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/buffer_results_to_out_params.py
    """

    func_op = target.func_op
    block = func_op.body.blocks.first
    if block is None:
        raise BufferResultsToOutParamsError("function body is empty")
    output_types = target.output_signature.output_types
    memory_indices = target.output_signature.memory_indices
    return_op = func_op.get_return_op()
    if return_op is None or len(return_op.arguments) != len(output_types):
        raise BufferResultsToOutParamsError(
            "return operand count must match function outputs for buffer-results-to-out-params"
        )

    new_out_args: list[BlockArgument] = []
    for insert_index, memory_output_index in enumerate(memory_indices):
        memory_type = output_types[memory_output_index]
        if not isinstance(memory_type, NnMemoryType):
            raise BufferResultsToOutParamsError("memory output index must point to nn.memory")
        new_out_args.append(block.insert_arg(memory_type, insert_index))

    func_op.properties["arg_attrs"] = _rebuild_arg_attrs(func_op, len(new_out_args))

    scalar_return_values = [return_op.arguments[index] for index in target.output_signature.scalar_indices]
    memory_return_values = [return_op.arguments[index] for index in memory_indices]
    for new_out_arg, return_value in zip(new_out_args, memory_return_values, strict=True):
        return_value.replace_by(new_out_arg)
    block.erase_op(return_op)
    block.add_op(func.ReturnOp(*scalar_return_values))
    for return_value in memory_return_values:
        _erase_dead_result_owner(return_value, block)
    func_op.update_function_type()


class BufferResultsToOutParamsPass(Pass):
    """将 `memory` 返回值改写为最前置 out 参数的 lowering pass。

    创建者: 朽木露琪亚
    最后一次更改: jcc你莫辜负

    功能说明:
    - 在模块级先做候选校验。
    - 当前实现执行“模块内可解析 callsite 同步改写 + 多 memory results / mixed returns -> 前置 out 参数”改写。
    - memory 返回会按原顺序前置为 `arg0 / arg1 / ...`，scalar 返回继续保留在 `func.return`。

    使用示例:
    - module = BufferResultsToOutParamsPass().run(module)

    关联文件:
    - spec: spec/pass/lowering/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/buffer_results_to_out_params.py
    """

    name = "buffer-results-to-out-params"

    def run(self, module: ModuleOp) -> ModuleOp:
        """执行最小骨架改写。

        创建者: 朽木露琪亚
        最后一次更改: jcc你莫辜负

        功能说明:
        - 先收集并校验候选函数。
        - 先同步改写 caller 侧 `func.call`，再改写 callee 返回合同。

        使用示例:
        - module = BufferResultsToOutParamsPass().run(module)

        关联文件:
        - spec: spec/pass/lowering/buffer_results_to_out_params.md
        - test: test/pass/test_buffer_results_to_out_params.py
        - 功能实现: kernel_gen/passes/buffer_results_to_out_params.py
        """

        if not isinstance(module, ModuleOp):
            raise BufferResultsToOutParamsError("module must be builtin.module")
        targets = _collect_rewrite_targets(module)
        _validate_local_callsites(module, targets)
        _rewrite_callsites(module, targets)
        for target in targets.values():
            _rewrite_memory_results_to_out_params(target)
        return module


__all__ = ["BufferResultsToOutParamsError", "BufferResultsToOutParamsPass"]
