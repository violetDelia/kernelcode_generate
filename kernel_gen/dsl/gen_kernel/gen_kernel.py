"""`gen_kernel(...)` 公开模块入口。


功能说明:
- 提供 `gen_kernel(obj, ctx)` 的稳定公开入口。
- 提供 `dsl_gen_kernel(fn, *runtime_args, ctx)` 的 callable 公开入口。
- 单个非函数 op 继续直接委托给本模块绑定的 `emit_c_op(...)`。
- 函数 / module 输入统一委托给公开 `emit_c(...)` 生成完整源码。
- `kernel_gen.core.config.dump_dir` 非空时统一写出最终 `source.cpp`；SourceBundle 还会展开 artifact 文件。
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
import os
from pathlib import Path
from typing import NoReturn, TypeAlias

from xdsl.dialects import func
from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import Operation

from kernel_gen.core.config import get_dump_dir
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.dsl.ast.mlir_gen import mlir_gen
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

from .emit import emit_c, emit_c_op
from .emit_context import EmitCContext

GenKernelInput: TypeAlias = "Operation | ModuleOp"
DslRuntimeArg: TypeAlias = "Memory | SymbolDim | int | float | bool | str"
DslFunctionReturn: TypeAlias = "DslRuntimeArg | None"
_BUNDLE_MARKER_PREFIX = "// __KG_BUNDLE_FILE__:"


def _gen_kernel_error(message: str) -> KernelCodeError:
    """构造 gen_kernel 稳定合同错误。


    功能说明:
    - 将 SourceBundle dump 解析和写出错误统一归入 gen_kernel 合同错误。
    - 仅供本文件内部使用。

    使用示例:
    - raise _gen_kernel_error("source_bundle_malformed")
    """

    return KernelCodeError(ErrorKind.CONTRACT, ErrorModule.GEN_KERNEL, message)


def _validate_bundle_path(path: str, seen_paths: set[str]) -> None:
    """校验 SourceBundle artifact 相对路径。


    功能说明:
    - 只接受 POSIX 风格安全相对路径。
    - 拒绝绝对路径、`.`、`..`、空 segment、反斜杠、NUL 与重复 path。

    使用示例:
    - _validate_bundle_path("include/kernel.h", set())
    """

    if (
        not path
        or path.startswith("/")
        or path in {".", ".."}
        or "\\" in path
        or "\x00" in path
        or path in seen_paths
    ):
        raise _gen_kernel_error("source_bundle_malformed")
    if any(part in {"", ".", ".."} for part in path.split("/")):
        raise _gen_kernel_error("source_bundle_malformed")
    seen_paths.add(path)


def _parse_source_bundle(source: str) -> dict[str, str] | None:
    """解析 SourceBundle aggregate string。


    功能说明:
    - 仅当第一行完整以 marker 开始时进入 bundle 解析。
    - 返回 artifact 路径到内容的映射；普通源码返回 `None`。

    使用示例:
    - artifacts = _parse_source_bundle(source)
    """

    lines = source.splitlines()
    if not lines or not lines[0].startswith(_BUNDLE_MARKER_PREFIX):
        return None
    artifacts: dict[str, list[str]] = {}
    seen_paths: set[str] = set()
    current_path: str | None = None
    for line in lines:
        if line.startswith(_BUNDLE_MARKER_PREFIX):
            path = line[len(_BUNDLE_MARKER_PREFIX):]
            _validate_bundle_path(path, seen_paths)
            artifacts[path] = []
            current_path = path
            continue
        if current_path is None:
            raise _gen_kernel_error("source_bundle_malformed")
        artifacts[current_path].append(line)
    return {path: "\n".join(content) for path, content in artifacts.items()}


def _safe_artifact_path(dump_dir: Path, artifact_path: str) -> Path:
    """把 artifact 相对路径解析到 dump 目录下。


    功能说明:
    - 使用 `Path.resolve(strict=False)` 识别已存在 symlink 逃逸。
    - 写出路径必须保持在 dump 根目录内。

    使用示例:
    - output_path = _safe_artifact_path(Path("dump"), "kernel.cpp")
    """

    root = dump_dir.resolve()
    output_path = (dump_dir / artifact_path).resolve(strict=False)
    if os.path.commonpath((str(root), str(output_path))) != str(root):
        raise _gen_kernel_error("source_bundle_path_escape")
    return output_path


def _write_source_dump(source: str, dump_dir: Path) -> None:
    """按普通源码或 SourceBundle 写出 dump 文件。


    功能说明:
    - 始终写出兼容 `source.cpp`，内容为公开返回源码。
    - 若源码是 SourceBundle aggregate string，额外展开每个 artifact 到对应安全相对路径。

    使用示例:
    - _write_source_dump(source, Path("dump"))
    """

    dump_dir.mkdir(parents=True, exist_ok=True)
    text = source if source.endswith("\n") else f"{source}\n"
    (dump_dir / "source.cpp").write_text(text, encoding="utf-8")
    artifacts = _parse_source_bundle(source)
    if artifacts is None:
        return
    for artifact_path, content in artifacts.items():
        output_path = _safe_artifact_path(dump_dir, artifact_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_text = content if content.endswith("\n") else f"{content}\n"
        output_path.write_text(artifact_text, encoding="utf-8")


def _emit_func_with_kernel_emitter(func_op: func.FuncOp, ctx: EmitCContext) -> str:
    """通过公开 `KernelEmitter` 发射单个函数。


    功能说明:
    - 保持 `gen_kernel(...)` 对 `func.func` 的既有函数级发射行为。
    - 使用本文件绑定的 `emit_c_op(...)`，让公开测试可以观察单 op 委托路径。

    使用示例:
    - source = _emit_func_with_kernel_emitter(func_op, EmitCContext())
    """

    from .kernel_emitter import KernelEmitter

    emitter = KernelEmitter(ctx, emit_op=emit_c_op)
    source = emitter.emit_func(func_op)
    include = emitter.emit_include()
    if include:
        if source:
            return include + source
        return include.rstrip()
    return source


def gen_kernel(obj: GenKernelInput, ctx: EmitCContext) -> str:
    """生成单个 op 或完整函数/module 的目标源码。


    功能说明:
    - 单个非函数 op 委托 `emit_c_op(...)`。
    - `func.func` 通过公开 `KernelEmitter` 发射；`builtin.module` 委托 `emit_c(...)` 的 backend handler。
    - 保持返回值为完整源码字符串。
    - 当公开 `dump_dir` 非空时，同步把最终源码写入 `dump_dir/source.cpp`。

    使用示例:
    - source = gen_kernel(func_op, EmitCContext())
    """

    if isinstance(obj, Operation) and not isinstance(obj, (func.FuncOp, ModuleOp)):
        result = emit_c_op(obj, ctx)
    elif isinstance(obj, func.FuncOp):
        result = _emit_func_with_kernel_emitter(obj, ctx)
    else:
        result = emit_c(obj, ctx)
    dump_dir = get_dump_dir()
    if dump_dir is not None:
        _write_source_dump(result, dump_dir)
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
