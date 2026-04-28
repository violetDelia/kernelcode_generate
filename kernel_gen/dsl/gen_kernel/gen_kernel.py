"""`gen_kernel(...)` 公开模块入口。

创建者: 小李飞刀
最后一次更改: 金铲铲大作战

功能说明:
- 提供 `gen_kernel(obj, ctx)` 的稳定公开入口。
- 提供 `dsl_gen_kernel(fn, *runtime_args, ctx)` 的 callable 公开入口。
- 单个非函数 op 继续直接委托给本模块绑定的 `emit_c_op(...)`。
- 函数 / module 输入统一委托给内部 `KernelEmitter` 生成完整源码。
- `kernel_gen.core.config.dump_dir` 非空时统一写出最终 `source.cpp`。
- 内部函数级 kernel emitter 实现位于 `kernel_emitter.py`，本文件只承载公开 API。

API 列表:
- `gen_kernel(obj: object, ctx: EmitCContext) -> str`
- `dsl_gen_kernel(fn: Callable[..., object], *runtime_args: object, ctx: EmitCContext) -> str`

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
from kernel_gen.core.config import get_dump_dir
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError

from collections.abc import Callable

from xdsl.dialects import func
from xdsl.dialects.builtin import ModuleOp

from kernel_gen.dsl.mlir_gen import mlir_gen

from . import kernel_emitter as _kernel_emitter
from .emit import emit_c_op
from .emit_context import EmitCContext


def _write_source_dump(source: str) -> None:
    """按公开 `dump_dir` 配置写出源码诊断文件。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - `kernel_gen.core.config.get_dump_dir()` 非空时写入 `source.cpp`。
    - 该 helper 只属于当前文件内部实现，避免工具层重复写源码 dump。
    - 写入行为不改变 `gen_kernel(...)` 的返回值。

    使用示例:
    - _write_source_dump(source)
    """

    dump_dir = get_dump_dir()
    if dump_dir is None:
        return
    dump_dir.mkdir(parents=True, exist_ok=True)
    text = source if source.endswith("\n") else f"{source}\n"
    (dump_dir / "source.cpp").write_text(text, encoding="utf-8")


def gen_kernel(obj: object, ctx: EmitCContext) -> str:
    """生成单个 op 或完整函数/module 的目标源码。

    创建者: 小李飞刀
    最后一次更改: 大闸蟹

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
    _write_source_dump(result)
    return result


def _resolve_root_func(module: ModuleOp, fn_name: str) -> func.FuncOp:
    """从 `mlir_gen(...)` 结果里定位 callable 对应的根函数。
    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 优先按 callable 的 `__name__` 精确匹配 `func.func`。
    - 若 module 中只有一个 `func.func`，则直接把它视作根函数。
    - 若找不到公开根函数，统一抛 `KernelCodeError`，避免 `dsl_gen_kernel(...)` 静默选错 callee。

    使用示例:
    - module = mlir_gen(add_scalar, 1, 2)
    - root_func = _resolve_root_func(module, "add_scalar")

    关联文件:
    - spec: [spec/dsl/gen_kernel/gen_kernel.md](../../../../spec/dsl/gen_kernel/gen_kernel.md)
    - test: [test/dsl/gen_kernel/test_gen_kernel.py](../../../../test/dsl/gen_kernel/test_gen_kernel.py)
    - 功能实现: [kernel_gen/dsl/gen_kernel/gen_kernel.py](.)
    """

    func_ops = [op for op in module.body.block.ops if isinstance(op, func.FuncOp)]
    for func_op in func_ops:
        if func_op.sym_name.data == fn_name:
            return func_op
    if len(func_ops) == 1:
        return func_ops[0]
    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.GEN_KERNEL, f"dsl_gen_kernel({fn_name}): root func not found")


def dsl_gen_kernel(
    fn: Callable[..., object],
    *runtime_args: object,
    ctx: EmitCContext,
) -> str:
    """通过公开 `mlir_gen(...) + gen_kernel(...)` 链路生成 callable 源码。
    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

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
    root_func = _resolve_root_func(module, getattr(fn, "__name__", "<anonymous>"))
    return gen_kernel(root_func, ctx)


def __getattr__(name: str) -> object:
    if name in {"gen_signature", "gen_body"}:
        raise AttributeError(f"{name} is no longer a public entry; use gen_kernel(...) instead")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["dsl_gen_kernel", "gen_kernel"]
