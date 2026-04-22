"""inline pass.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 在 `builtin.module` 内把可内联的本地 `func.call` 展平到调用点。
- 首版固定支持单 block helper `func.func`，并在内联完成后清理失效的 private helper。
- 不承担通用跨 module inline，也不处理外部声明或复杂 CFG。

使用示例:
- from xdsl.context import Context
- from kernel_gen.passes.inline import InlinePass
- module = InlinePass().run(module)
- InlinePass().apply(Context(), module)

关联文件:
- spec: [spec/pass/inline.md](../../spec/pass/inline.md)
- test: [test/pass/test_inline.py](../../test/pass/test_inline.py)
- 功能实现: [kernel_gen/passes/inline.py](../../kernel_gen/passes/inline.py)
"""

from __future__ import annotations

from collections.abc import Iterable

from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import Block, Operation, SSAValue
from xdsl.passes import ModulePass

from kernel_gen.passes.pass_manager import Pass


class InlineError(ValueError):
    """inline pass 的稳定错误类型。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一承载 inline 过程中的显式失败路径。
    - 保持错误前缀稳定，便于测试与 expectation 做机械匹配。

    使用示例:
    - raise InlineError("InlineError: module must be builtin.module")

    关联文件:
    - spec: [spec/pass/inline.md](../../spec/pass/inline.md)
    - test: [test/pass/test_inline.py](../../test/pass/test_inline.py)
    - 功能实现: [kernel_gen/passes/inline.py](../../kernel_gen/passes/inline.py)
    """


def _clone_op_into_block(
    op: Operation,
    target_block: Block,
    anchor_op: Operation,
    value_mapper: dict[SSAValue, SSAValue],
) -> Operation:
    """把源 op 克隆到目标 block，并同步 SSA 映射。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 复用 xdsl `Operation.clone(...)` 把 helper op 复制到调用点前。
    - 使用 `Block.insert_ops_before(...)` 保证克隆后的相对顺序稳定。
    - 更新源结果到新结果的映射，供后续 operands 重写使用。

    使用示例:
    - cloned = _clone_op_into_block(op, block, value_mapper)

    关联文件:
    - spec: [spec/pass/inline.md](../../spec/pass/inline.md)
    - test: [test/pass/test_inline.py](../../test/pass/test_inline.py)
    - 功能实现: [kernel_gen/passes/inline.py](../../kernel_gen/passes/inline.py)
    """

    cloned = op.clone(value_mapper=value_mapper)
    target_block.insert_ops_before([cloned], anchor_op)
    for source_result, cloned_result in zip(op.results, cloned.results, strict=True):
        value_mapper[source_result] = cloned_result
    return cloned


def _is_inlineable_func(func_op: func.FuncOp) -> bool:
    """判断 `func.func` 是否属于可内联的本地 helper。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅接受非 declaration、单 block、以 `func.return` 结尾的 helper。
    - 该条件足以覆盖当前 `npu-demo-lowering` 的模块内 helper 展平需求。

    使用示例:
    - if _is_inlineable_func(helper_func): ...

    关联文件:
    - spec: [spec/pass/inline.md](../../spec/pass/inline.md)
    - test: [test/pass/test_inline.py](../../test/pass/test_inline.py)
    - 功能实现: [kernel_gen/passes/inline.py](../../kernel_gen/passes/inline.py)
    """

    if getattr(func_op, "is_declaration", False):
        return False
    blocks = tuple(func_op.body.blocks)
    if len(blocks) != 1:
        return False
    return_op = func_op.get_return_op()
    if return_op is None:
        return False
    return blocks[0].last_op is return_op


def _collect_inlineable_funcs(module: ModuleOp) -> dict[str, func.FuncOp]:
    """收集 module 内可内联的本地 `func.func`。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 以顶层 `func.func` 为范围，筛出符合 `_is_inlineable_func` 条件的 helper。
    - 返回值按 symbol 名字索引，便于 inline 时快速查询。

    使用示例:
    - inlineable = _collect_inlineable_funcs(module)

    关联文件:
    - spec: [spec/pass/inline.md](../../spec/pass/inline.md)
    - test: [test/pass/test_inline.py](../../test/pass/test_inline.py)
    - 功能实现: [kernel_gen/passes/inline.py](../../kernel_gen/passes/inline.py)
    """

    inlineable: dict[str, func.FuncOp] = {}
    for op in module.ops:
        if isinstance(op, func.FuncOp) and _is_inlineable_func(op):
            inlineable[op.sym_name.data] = op
    return inlineable


def _remove_dead_private_helpers(
    module: ModuleOp,
    entry_func_name: str | None,
    remaining_call_targets: Iterable[str],
) -> None:
    """清理已失效的 private helper `func.func`。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅移除 `private` 且不再被 `func.call` 引用的 helper。
    - 保留入口函数，避免误删当前 pipeline 的公开入口。

    使用示例:
    - _remove_dead_private_helpers(module, "main", {"foo"})

    关联文件:
    - spec: [spec/pass/inline.md](../../spec/pass/inline.md)
    - test: [test/pass/test_inline.py](../../test/pass/test_inline.py)
    - 功能实现: [kernel_gen/passes/inline.py](../../kernel_gen/passes/inline.py)
    """

    remaining_targets = set(remaining_call_targets)
    for op in list(module.ops):
        if not isinstance(op, func.FuncOp):
            continue
        if entry_func_name is not None and op.sym_name.data == entry_func_name:
            continue
        visibility = getattr(op, "sym_visibility", None)
        if getattr(visibility, "data", None) != "private":
            continue
        if op.sym_name.data in remaining_targets:
            continue
        op.detach()


class InlinePass(Pass, ModulePass):
    """inline pass。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 固定公开名称为 `inline`。
    - 对本地可内联 helper 执行模块内展平，并清理失效的 private helper。
    - 兼容 `PassManager` 与 xdsl `ModulePass` 两套执行入口。

    使用示例:
    - from kernel_gen.passes.inline import InlinePass
    - module = InlinePass().run(module)
    - InlinePass().apply(Context(), module)

    关联文件:
    - spec: [spec/pass/inline.md](../../spec/pass/inline.md)
    - test: [test/pass/test_inline.py](../../test/pass/test_inline.py)
    - 功能实现: [kernel_gen/passes/inline.py](../../kernel_gen/passes/inline.py)
    """

    name = "inline"

    def apply(self: "InlinePass", ctx: Context, module: ModuleOp) -> None:
        """执行 inline pass。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 只接受 `builtin.module` 输入。
        - 逐轮把本地 `func.call` 展平到调用点，并更新 SSA 映射。
        - 若仍残留可内联 local call，则显式失败。

        使用示例:
        - InlinePass().apply(Context(), module)

        关联文件:
        - spec: [spec/pass/inline.md](../../spec/pass/inline.md)
        - test: [test/pass/test_inline.py](../../test/pass/test_inline.py)
        - 功能实现: [kernel_gen/passes/inline.py](../../kernel_gen/passes/inline.py)
        """

        del ctx
        if not isinstance(module, ModuleOp):
            raise InlineError("InlineError: module must be builtin.module")
        funcs = [op for op in module.ops if isinstance(op, func.FuncOp)]
        if not funcs:
            return
        public_funcs = [op for op in funcs if getattr(op, "sym_visibility", None) is None or getattr(op.sym_visibility, "data", None) != "private"]
        entry_func_name = (public_funcs[0] if public_funcs else funcs[0]).sym_name.data
        changed = True
        while changed:
            changed = False
            inlineable_funcs = _collect_inlineable_funcs(module)
            if not inlineable_funcs:
                break
            for caller in [op for op in module.ops if isinstance(op, func.FuncOp)]:
                if getattr(caller, "is_declaration", False):
                    continue
                caller_block = caller.body.block
                for op in list(caller_block.ops):
                    if not isinstance(op, func.CallOp):
                        continue
                    callee_name = op.callee.root_reference.data
                    callee = inlineable_funcs.get(callee_name)
                    if callee is None or callee_name == caller.sym_name.data:
                        continue
                    callee_block = callee.body.block
                    return_op = callee.get_return_op()
                    if return_op is None or callee_block.last_op is not return_op:
                        raise InlineError(
                            f"InlineError: callee '{callee_name}' must be a single-block func.func"
                        )
                    if len(callee_block.args) != len(op.arguments):
                        raise InlineError(
                            f"InlineError: func.call arity mismatch for '{callee_name}'"
                        )
                    if len(op.results) != len(return_op.arguments):
                        raise InlineError(
                            f"InlineError: func.call result arity mismatch for '{callee_name}'"
                        )
                    value_mapper: dict[SSAValue, SSAValue] = {
                        callee_arg: SSAValue.get(call_arg)
                        for callee_arg, call_arg in zip(callee_block.args, op.arguments, strict=True)
                    }
                    for callee_op in callee_block.ops:
                        if callee_op is return_op:
                            continue
                        _clone_op_into_block(callee_op, caller_block, op, value_mapper)
                    for call_result, return_value in zip(op.results, return_op.arguments, strict=True):
                        mapped_return = value_mapper.get(SSAValue.get(return_value), SSAValue.get(return_value))
                        call_result.replace_all_uses_with(mapped_return)
                    op.detach()
                    changed = True
            if changed:
                continue
        remaining_inlineable_calls = [
            call
            for call in module.walk()
            if isinstance(call, func.CallOp) and call.callee.root_reference.data in inlineable_funcs
        ]
        if remaining_inlineable_calls:
            raise InlineError("InlineError: unresolved func.call remains after inline")
        remaining_targets = {
            call.callee.root_reference.data for call in module.walk() if isinstance(call, func.CallOp)
        }
        _remove_dead_private_helpers(module, entry_func_name, remaining_targets)

    def run(self: "InlinePass", module: object) -> ModuleOp:
        """兼容旧 Pass 接口的执行入口。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 保持旧 `run(module)` 调用方可继续工作。

        使用示例:
        - module = InlinePass().run(module)

        关联文件:
        - spec: [spec/pass/inline.md](../../spec/pass/inline.md)
        - test: [test/pass/test_inline.py](../../test/pass/test_inline.py)
        - 功能实现: [kernel_gen/passes/inline.py](../../kernel_gen/passes/inline.py)
        """

        if not isinstance(module, ModuleOp):
            raise InlineError("InlineError: module must be builtin.module")
        self.apply(Context(), module)
        return module


__all__ = ["InlineError", "InlinePass"]
