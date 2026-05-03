"""`gen_kernel(...)` 公开模块入口。


功能说明:
- 提供 `gen_kernel(obj, ctx)` 的稳定公开入口。
- 提供 `dsl_gen_kernel(fn, *runtime_args, ctx)` 的 callable 公开入口。
- 单个非函数 op 继续直接委托给本模块绑定的 `emit_c_op(...)`。
- 函数 / module 输入统一委托给内部 `KernelEmitter` 生成完整源码。
- `kernel_gen.core.config.dump_dir` 非空时统一写出最终 `source.cpp`。
- 内部函数级 kernel emitter 实现位于 `kernel_emitter.py`，本文件只承载公开 API。

API 列表:
- `gen_kernel(obj: GenKernelInput, ctx: EmitCContext) -> str`
- `dsl_gen_kernel(fn: Callable[..., DslFunctionReturn], *runtime_args: DslRuntimeArg, ctx: EmitCContext) -> str`

使用示例:
- from kernel_gen.dsl.gen_kernel import EmitCContext, gen_kernel
- from kernel_gen.core.config import set_target
- set_target("npu_demo")
- source = gen_kernel(func_op, EmitCContext())

关联文件:
- spec: [spec/dsl/gen_kernel/gen_kernel.md](../../../../spec/dsl/gen_kernel/gen_kernel.md)
- spec: [spec/dsl/gen_kernel/emit.md](../../../../spec/dsl/gen_kernel/emit.md)
- test: [test/dsl/gen_kernel/test_gen_kernel.py](../../../../test/dsl/gen_kernel/test_gen_kernel.py)
- 功能实现: [kernel_gen/dsl/gen_kernel/gen_kernel.py](.)
- 功能实现: [kernel_gen/dsl/gen_kernel/kernel_emitter.py](kernel_emitter.py)
"""

from __future__ import annotations
from collections.abc import Callable
from typing import NoReturn, TypeAlias

from xdsl.dialects import func
from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import Operation

from kernel_gen.core.config import get_dump_dir
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dsl.ast.mlir_gen import mlir_gen
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

from . import kernel_emitter as _kernel_emitter
from .emit import emit_c_op
from .emit_context import EmitCContext

GenKernelInput: TypeAlias = "Operation | ModuleOp"
DslRuntimeArg: TypeAlias = "Memory | SymbolDim | int | float | bool | str"
DslFunctionReturn: TypeAlias = "DslRuntimeArg | None"


def gen_kernel(obj: GenKernelInput, ctx: EmitCContext) -> str:
    """生成单个 op 或完整函数/module 的目标源码。


    功能说明:
    - 通过内部 `KernelEmitter` 发射 op、`func.func` 或受控 `builtin.module`。
    - 保持返回值为完整源码字符串。
    - 当公开 `dump_dir` 非空时，同步把最终源码写入 `dump_dir/source.cpp`。

    使用示例:
    - source = gen_kernel(func_op, EmitCContext())
    """

    emitter = _kernel_emitter.KernelEmitter(ctx, emit_op=emit_c_op)
    source = emitter.emit(obj)
    include = emitter.emit_include()
    if include:
        if source:
            result = include + source
        else:
            result = include.rstrip()
    else:
        result = source
    dump_dir = get_dump_dir()
    if dump_dir is not None:
        dump_dir.mkdir(parents=True, exist_ok=True)
        text = result if result.endswith("\n") else f"{result}\n"
        (dump_dir / "source.cpp").write_text(text, encoding="utf-8")
    return result


def dsl_gen_kernel(
    fn: Callable[..., DslFunctionReturn],
    *runtime_args: DslRuntimeArg,
    ctx: EmitCContext,
) -> str:
    """通过公开 `mlir_gen(...) + gen_kernel(...)` 链路生成 callable 源码。

    功能说明:
    - 只接受 Python DSL callable 及其运行时参数。
    - 先通过公开 `mlir_gen(...)` 生成 `builtin.module`，再选择 callable 对应的根 `func.func` 走公开 `gen_kernel(...)`。
    - 不在本文件外额外直连 parser、module-builder 或 kernel emitter 私有 helper。

    使用示例:
    - source = dsl_gen_kernel(add_scalar, 1, 2, ctx=EmitCContext())

    关联文件:
    - spec: [spec/dsl/gen_kernel/gen_kernel.md](../../../../spec/dsl/gen_kernel/gen_kernel.md)
    - test: [test/dsl/gen_kernel/test_gen_kernel.py](../../../../test/dsl/gen_kernel/test_gen_kernel.py)
    - 功能实现: [kernel_gen/dsl/gen_kernel/gen_kernel.py](.)
    """

    module = mlir_gen(fn, *runtime_args)
    fn_name = getattr(fn, "__name__", "<anonymous>")
    func_ops = [op for op in module.body.block.ops if isinstance(op, func.FuncOp)]
    root_func = next((func_op for func_op in func_ops if func_op.sym_name.data == fn_name), None)
    if root_func is None and len(func_ops) == 1:
        root_func = func_ops[0]
    if root_func is None:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.GEN_KERNEL, f"dsl_gen_kernel({fn_name}): root func not found")
    return gen_kernel(root_func, ctx)


def __getattr__(name: str) -> NoReturn:
    if name in {"gen_signature", "gen_body"}:
        raise AttributeError(f"{name} is no longer a public entry; use gen_kernel(...) instead")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["dsl_gen_kernel", "gen_kernel"]
