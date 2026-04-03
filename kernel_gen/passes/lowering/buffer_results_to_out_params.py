"""buffer-results-to-out-params lowering pass.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 将 `func.func` 中单个 `memory` 返回值改写为最前置 out 参数。
- 为当前最小骨架明确写死 external declaration 与未同步 callsite 的失败边界。

使用示例:
- from kernel_gen.passes.lowering.buffer_results_to_out_params import BufferResultsToOutParamsPass
- module = BufferResultsToOutParamsPass().run(module)

关联文件:
- spec: spec/pass/lowering/buffer_results_to_out_params.md
- test: test/pass/test_buffer_results_to_out_params.py
- 功能实现: kernel_gen/passes/lowering/buffer_results_to_out_params.py
"""

from __future__ import annotations

from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, DictionaryAttr, ModuleOp, StringAttr
from xdsl.ir import Block, BlockArgument, Operation, SSAValue

from kernel_gen.dialect.dma import DmaAllocOp
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.passes.pass_manager import Pass


class BufferResultsToOutParamsError(ValueError):
    """buffer-results-to-out-params pass 的显式错误。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 统一承载 external declaration、半改半留和当前骨架未覆盖场景的错误。

    使用示例:
    - raise BufferResultsToOutParamsError("external declaration is not supported")

    关联文件:
    - spec: spec/pass/lowering/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/lowering/buffer_results_to_out_params.py
    """


def _memory_output_indices(func_op: func.FuncOp) -> list[int]:
    """收集函数输出中的 memory result 索引。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 逐项检查 `function_type.outputs`。
    - 返回其中 `NnMemoryType` 的位置索引。

    使用示例:
    - indices = _memory_output_indices(func_op)

    关联文件:
    - spec: spec/pass/lowering/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/lowering/buffer_results_to_out_params.py
    """

    return [
        index
        for index, output_type in enumerate(func_op.function_type.outputs.data)
        if isinstance(output_type, NnMemoryType)
    ]


def _rebuild_arg_attrs(func_op: func.FuncOp, prepended: int) -> ArrayAttr[DictionaryAttr]:
    """为前置 out 参数重建 `arg_attrs`。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 新前置参数名固定为 `arg0`、`arg1`。
    - 原有参数属性按顺序整体后移；缺失属性时补空字典。

    使用示例:
    - attrs = _rebuild_arg_attrs(func_op, 1)

    关联文件:
    - spec: spec/pass/lowering/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/lowering/buffer_results_to_out_params.py
    """

    existing = list(func_op.arg_attrs.data) if func_op.arg_attrs is not None else []
    total_old_args = len(func_op.function_type.inputs.data)
    while len(existing) < total_old_args:
        existing.append(DictionaryAttr({}))
    prepended_attrs = [
        DictionaryAttr({"name": StringAttr(f"arg{index}")}) for index in range(prepended)
    ]
    return ArrayAttr([*prepended_attrs, *existing])


def _validate_candidate(func_op: func.FuncOp) -> None:
    """校验当前最小骨架可安全改写的函数范围。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - external declaration 直接失败。
    - 本轮只接受单 block、单 `memory` 返回、且无混合返回。

    使用示例:
    - _validate_candidate(func_op)

    关联文件:
    - spec: spec/pass/lowering/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/lowering/buffer_results_to_out_params.py
    """

    memory_indices = _memory_output_indices(func_op)
    if not memory_indices:
        return
    first_block = func_op.body.blocks.first
    is_external_like = func_op.is_declaration or (
        first_block is not None and tuple(first_block.ops) == ()
    )
    if is_external_like:
        raise BufferResultsToOutParamsError("external declaration is not supported")
    if len(memory_indices) != 1 or len(func_op.function_type.outputs.data) != 1:
        raise BufferResultsToOutParamsError(
            "multiple or mixed memory results are not supported in the minimal skeleton"
        )
    if len(tuple(func_op.body.blocks)) != 1:
        raise BufferResultsToOutParamsError("only single-block functions are supported")
    return_op = func_op.get_return_op()
    if return_op is None or len(return_op.arguments) != 1:
        raise BufferResultsToOutParamsError(
            "single memory result rewrite requires exactly one return operand"
        )


def _collect_rewrite_targets(module: ModuleOp) -> dict[str, func.FuncOp]:
    """收集需要改写的函数，并提前做边界校验。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 只收集存在 `memory` 返回值的 `func.func`。
    - 在真正改写前先执行候选校验，确保模块级原子失败。

    使用示例:
    - targets = _collect_rewrite_targets(module)

    关联文件:
    - spec: spec/pass/lowering/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/lowering/buffer_results_to_out_params.py
    """

    targets: dict[str, func.FuncOp] = {}
    for op in module.ops:
        if not isinstance(op, func.FuncOp):
            continue
        if not _memory_output_indices(op):
            continue
        _validate_candidate(op)
        targets[op.sym_name.data] = op
    return targets


def _ensure_no_unsupported_calls(module: ModuleOp, targets: dict[str, func.FuncOp]) -> None:
    """在未实现 callsite 同步改写前，拒绝半改半留场景。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 若模块内存在调用待改写函数的 `func.call`，直接失败。
    - 保证当前最小骨架不会只改 `func.func` 签名而遗漏调用点。

    使用示例:
    - _ensure_no_unsupported_calls(module, targets)

    关联文件:
    - spec: spec/pass/lowering/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/lowering/buffer_results_to_out_params.py
    """

    if not targets:
        return
    target_names = set(targets)
    for op in module.walk():
        if not isinstance(op, func.CallOp):
            continue
        callee = op.callee.root_reference.data
        if callee in target_names:
            raise BufferResultsToOutParamsError(
                f"callsite rewrite is not implemented yet for callee {callee}"
            )


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
    - 功能实现: kernel_gen/passes/lowering/buffer_results_to_out_params.py
    """

    owner = getattr(value, "owner", None)
    if isinstance(owner, DmaAllocOp) and owner.parent is block and all(
        result.first_use is None for result in owner.results
    ):
        block.erase_op(owner)


def _rewrite_single_memory_result(func_op: func.FuncOp) -> None:
    """将单个 `memory` 返回值改写为最前置 out 参数。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 在 block 最前插入新参数 `arg0`。
    - 将原返回值在函数体内的使用替换为新 out 参数。
    - 清空 `func.return`，并刷新函数签名。

    使用示例:
    - _rewrite_single_memory_result(func_op)

    关联文件:
    - spec: spec/pass/lowering/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/lowering/buffer_results_to_out_params.py
    """

    block = func_op.body.blocks.first
    if block is None:
        raise BufferResultsToOutParamsError("function body is empty")
    return_op = func_op.get_return_op()
    if return_op is None or len(return_op.arguments) != 1:
        raise BufferResultsToOutParamsError(
            "single memory result rewrite requires exactly one return operand"
        )
    return_value = return_op.arguments[0]
    result_type = return_value.type
    if not isinstance(result_type, NnMemoryType):
        raise BufferResultsToOutParamsError("single result must be memory")

    new_out_arg: BlockArgument = block.insert_arg(result_type, 0)
    func_op.properties["arg_attrs"] = _rebuild_arg_attrs(func_op, 1)
    return_value.replace_by(new_out_arg)
    block.erase_op(return_op)
    block.add_op(func.ReturnOp())
    _erase_dead_result_owner(return_value, block)
    func_op.update_function_type()


class BufferResultsToOutParamsPass(Pass):
    """将 `memory` 返回值改写为最前置 out 参数的 lowering pass。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 在模块级先做候选校验与 callsite 边界检查。
    - 当前最小骨架只执行“单个 memory 返回值 -> arg0”改写。

    使用示例:
    - module = BufferResultsToOutParamsPass().run(module)

    关联文件:
    - spec: spec/pass/lowering/buffer_results_to_out_params.md
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/lowering/buffer_results_to_out_params.py
    """

    name = "buffer-results-to-out-params"

    def run(self, module: ModuleOp) -> ModuleOp:
        """执行最小骨架改写。

        创建者: 朽木露琪亚
        最后一次更改: 朽木露琪亚

        功能说明:
        - 先收集并校验候选函数。
        - 在确认没有 callsite 半改半留风险后再改写。

        使用示例:
        - module = BufferResultsToOutParamsPass().run(module)

        关联文件:
        - spec: spec/pass/lowering/buffer_results_to_out_params.md
        - test: test/pass/test_buffer_results_to_out_params.py
        - 功能实现: kernel_gen/passes/lowering/buffer_results_to_out_params.py
        """

        if not isinstance(module, ModuleOp):
            raise BufferResultsToOutParamsError("module must be builtin.module")
        targets = _collect_rewrite_targets(module)
        _ensure_no_unsupported_calls(module, targets)
        for func_op in targets.values():
            _rewrite_single_memory_result(func_op)
        return module


__all__ = ["BufferResultsToOutParamsError", "BufferResultsToOutParamsPass"]
