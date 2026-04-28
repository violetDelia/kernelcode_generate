"""inline pass.

创建者: 金铲铲大作战
最后一次更改: 大闸蟹

功能说明:
- 在 `builtin.module` 内把可内联的本地 `func.call` 展平到调用点。
- 首版固定支持单 block helper `func.func`，并在内联完成后清理失效的 private helper。
- 不承担通用跨 module inline，也不处理外部声明或复杂 CFG。

使用示例:
- from xdsl.context import Context
- from kernel_gen.passes.inline import InlinePass
- module = InlinePass().run(module)

关联文件:
- spec: [spec/pass/inline.md](../../spec/pass/inline.md)
- test: [test/pass/test_inline.py](../../test/pass/test_inline.py)
- 功能实现: [kernel_gen/passes/inline.py](../../kernel_gen/passes/inline.py)
"""

from __future__ import annotations

from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import SSAValue
from xdsl.passes import ModulePass

from kernel_gen.passes.common import raise_pass_contract_error
from kernel_gen.passes.pass_manager import Pass


class InlinePass(Pass, ModulePass):
    """inline pass。

    创建者: 金铲铲大作战
    最后一次更改: 大闸蟹

    功能说明:
    - 固定公开名称为 `inline`。
    - 对本地可内联 helper 执行模块内展平，并清理失效的 private helper。
    - 兼容 `PassManager` 与 xdsl `ModulePass` 协议执行入口。

    使用示例:
    - from kernel_gen.passes.inline import InlinePass
    - module = InlinePass().run(module)
    - module = InlinePass().run(module)

    关联文件:
    - spec: [spec/pass/inline.md](../../spec/pass/inline.md)
    - test: [test/pass/test_inline.py](../../test/pass/test_inline.py)
    - 功能实现: [kernel_gen/passes/inline.py](../../kernel_gen/passes/inline.py)
    """

    name = "inline"

    def apply(self: "InlinePass", ctx: Context, module: ModuleOp) -> None:
        """执行 inline pass。

        创建者: 金铲铲大作战
        最后一次更改: 大闸蟹

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

        _ = ctx
        if not isinstance(module, ModuleOp):
            raise_pass_contract_error("InlineError", "module must be builtin.module")

        funcs = [op for op in module.ops if isinstance(op, func.FuncOp)]
        if not funcs:
            return

        public_funcs = [
            op
            for op in funcs
            if getattr(op, "sym_visibility", None) is None
            or getattr(op.sym_visibility, "data", None) != "private"
        ]
        entry_func_name = (public_funcs[0] if public_funcs else funcs[0]).sym_name.data

        changed = True
        while changed:
            changed = False
            inlineable_funcs: dict[str, func.FuncOp] = {}
            for op in module.ops:
                if not isinstance(op, func.FuncOp):
                    continue
                if getattr(op, "is_declaration", False):
                    continue
                blocks = tuple(op.body.blocks)
                if len(blocks) != 1:
                    continue
                return_op = op.get_return_op()
                if return_op is None or blocks[0].last_op is not return_op:
                    continue
                inlineable_funcs[op.sym_name.data] = op
            if not inlineable_funcs:
                break

            for caller in [op for op in module.ops if isinstance(op, func.FuncOp)]:
                if getattr(caller, "is_declaration", False):
                    continue
                caller_block = caller.body.block
                for call_op in list(caller_block.ops):
                    if not isinstance(call_op, func.CallOp):
                        continue
                    callee_name = call_op.callee.root_reference.data
                    callee = inlineable_funcs.get(callee_name)
                    if callee is None or callee_name == caller.sym_name.data:
                        continue

                    callee_block = callee.body.block
                    return_op = callee.get_return_op()
                    if return_op is None or callee_block.last_op is not return_op:
                        raise_pass_contract_error(
                            "InlineError",
                            f"callee '{callee_name}' must be a single-block func.func",
                        )
                    if len(callee_block.args) != len(call_op.arguments):
                        raise_pass_contract_error(
                            "InlineError",
                            f"func.call arity mismatch for '{callee_name}'",
                        )
                    if len(call_op.results) != len(return_op.arguments):
                        raise_pass_contract_error(
                            "InlineError",
                            f"func.call result arity mismatch for '{callee_name}'",
                        )

                    value_mapper: dict[SSAValue, SSAValue] = {
                        callee_arg: SSAValue.get(call_arg)
                        for callee_arg, call_arg in zip(
                            callee_block.args, call_op.arguments, strict=True
                        )
                    }
                    for callee_op in callee_block.ops:
                        if callee_op is return_op:
                            continue
                        cloned = callee_op.clone(value_mapper=value_mapper)
                        caller_block.insert_ops_before([cloned], call_op)
                        for source_result, cloned_result in zip(
                            callee_op.results, cloned.results, strict=True
                        ):
                            value_mapper[source_result] = cloned_result
                    for call_result, return_value in zip(
                        call_op.results, return_op.arguments, strict=True
                    ):
                        mapped_return = value_mapper.get(
                            SSAValue.get(return_value), SSAValue.get(return_value)
                        )
                        call_result.replace_all_uses_with(mapped_return)
                    call_op.detach()
                    changed = True

        final_inlineable_names: set[str] = set()
        for op in module.ops:
            if not isinstance(op, func.FuncOp):
                continue
            if getattr(op, "is_declaration", False):
                continue
            blocks = tuple(op.body.blocks)
            if len(blocks) != 1:
                continue
            return_op = op.get_return_op()
            if return_op is None or blocks[0].last_op is not return_op:
                continue
            final_inlineable_names.add(op.sym_name.data)

        remaining_inlineable_calls = [
            call
            for call in module.walk()
            if isinstance(call, func.CallOp)
            and call.callee.root_reference.data in final_inlineable_names
        ]
        if remaining_inlineable_calls:
            raise_pass_contract_error("InlineError", "unresolved func.call remains after inline")

        remaining_targets = {
            call.callee.root_reference.data
            for call in module.walk()
            if isinstance(call, func.CallOp)
        }
        for op in list(module.ops):
            if not isinstance(op, func.FuncOp):
                continue
            if op.sym_name.data == entry_func_name:
                continue
            visibility = getattr(op, "sym_visibility", None)
            if getattr(visibility, "data", None) != "private":
                continue
            if op.sym_name.data in remaining_targets:
                continue
            op.detach()

    def run(self: "InlinePass", module: ModuleOp) -> ModuleOp:
        """兼容旧 Pass 接口的执行入口。

        创建者: 金铲铲大作战
        最后一次更改: 大闸蟹

        功能说明:
        - 保持旧 `run(module)` 调用方可继续工作。
        - 内部直接复用 `apply(Context(), module)`。

        使用示例:
        - module = InlinePass().run(module)

        关联文件:
        - spec: [spec/pass/inline.md](../../spec/pass/inline.md)
        - test: [test/pass/test_inline.py](../../test/pass/test_inline.py)
        - 功能实现: [kernel_gen/passes/inline.py](../../kernel_gen/passes/inline.py)
        """

        if not isinstance(module, ModuleOp):
            raise_pass_contract_error("InlineError", "module must be builtin.module")
        self.apply(Context(), module)
        return module


__all__ = ["InlinePass"]
