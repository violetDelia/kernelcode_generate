"""ExecutionEngine skeleton (P0).

创建者: 朽木露琪亚
最后一次更改: jcc你莫辜负

功能说明:
- 提供 `ExecutionEngine.compile(...).execute(...)` 的最小壳层，以便在不实现真实编译/调用的前提下固定：
  - 公开 API 的命名与字段形态；
  - 7 个公共失败短语（failure_phrase）的固定集合；
  - `stream` 与 `capture_function_output` 在 P0 的禁用行为；
  - 直接使用 RuntimeArg（torch/numpy/int/float）输入的调用路径。

API 列表:
- `FAILURE_TARGET_HEADER_MISMATCH: str`
- `FAILURE_SOURCE_EMPTY_OR_INVALID: str`
- `FAILURE_COMPILE_FAILED: str`
- `FAILURE_SYMBOL_RESOLVE_FAILED: str`
- `FAILURE_RUNTIME_THROW_OR_ABORT: str`
- `FAILURE_STREAM_NOT_SUPPORTED: str`
- `FAILURE_FUNCTION_OUTPUT_CAPTURE_NOT_SUPPORTED: str`
- `FAILURE_PHRASES: frozenset[str]`
- `TargetName = Literal["cpu", "npu_demo"]`
- `class CompileRequest(source: str, target: str, function: str, entry_point: str = "kg_execute_entry", compiler: str | None = None, compiler_flags: tuple[str, ...] = ("-std=c++17",), link_flags: tuple[str, ...] = ())`
- `class ExecuteRequest(args: tuple[RuntimeArg, ...], entry_point: str | None = None, capture_function_output: bool = False, stream: object | None = None)`
- `RuntimeArg = Any`
- `class KgArgSlot(position: int, kind: Literal["memory", "int", "float"], dtype: str | None, shape: tuple[int, ...] | None, stride: tuple[int, ...] | None, value: object)`
- `class ExecuteResult(ok: bool, status_code: int, failure_phrase: str | None, compile_stdout: str = "", compile_stderr: str = "", run_stdout: str = "", run_stderr: str = "", elapsed_ms: float = 0.0)`
- `class CompiledKernel(target: str, soname_path: str, function: str, entry_point: str, compile_stdout: str = "", compile_stderr: str = "")`
- `CompiledKernel.close() -> None`
- `CompiledKernel.execute(args: tuple[RuntimeArg, ...] | None = None, *, request: ExecuteRequest | None = None, entry_point: str | None = None, capture_function_output: bool = False, stream: object | None = None) -> ExecuteResult`
- `class ExecutionEngine(target: str, compiler: str | None = None, compiler_flags: tuple[str, ...] = ("-std=c++17",), link_flags: tuple[str, ...] = ())`
- `ExecutionEngine.compile(source: str | None = None, function: str | None = None, *, request: CompileRequest | None = None, entry_point: str = "kg_execute_entry") -> CompiledKernel`

helper 清单:
- `_source_include_family(source: str) -> str | None`
- `_inject_npu_demo_namespace_aliases(source: str) -> str`
- `_ensure_compiler_flags(flags: tuple[str, ...]) -> tuple[str, ...]`
- `_resolve_compiler_name(compiler: str | None) -> str`
- `_normalize_dtype(value: object) -> str | None`
- `_normalize_shape(value: object) -> tuple[int, ...] | None`
- `_normalize_stride(value: object) -> tuple[int, ...] | None`
- `_runtime_module_name(value: object) -> str`
- `_is_torch_tensor(value: object) -> bool`
- `_is_numpy_array(value: object) -> bool`
- `_is_runtime_int(value: object) -> bool`
- `_is_runtime_float(value: object) -> bool`
- `_is_memory_runtime_arg(value: object) -> bool`
- `_is_contiguous_memory(value: object) -> bool`
- `_build_arg_slots(args: tuple[RuntimeArg, ...]) -> tuple[KgArgSlot, ...]`
- `_contiguous_stride(shape: tuple[int, ...]) -> tuple[int, ...]`
- `_runtime_data_pointer(value: object) -> int`
- `_marshal_slots_for_abi(ordered_slots: tuple[KgArgSlot, ...]) -> tuple[object, ...]`
- `_load_entry_point(soname_path: str, entry_point: str) -> Callable[[tuple[KgArgSlot, ...]], int]`

使用示例:
- from kernel_gen.execute_engine import ExecutionEngine, ExecuteRequest
- engine = ExecutionEngine(target="cpu")
- kernel = engine.compile(source="int main(){}", function="cpu::add")
- result = kernel.execute(request=ExecuteRequest(args=(1, 2.0)))
- assert result.ok is True

关联文件:
- spec: spec/execute_engine/execute_engine.md
- spec: spec/execute_engine/execute_engine_api.md
- spec: spec/execute_engine/execute_engine_target.md
- test: test/execute_engine/test_execute_engine_contract.py
- 功能实现: kernel_gen/execute_engine/execution_engine.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any, Callable, Literal, TypeAlias

from kernel_gen.execute_engine.compiler import (
    build_compile_unit,
    compile_source,
    default_compiler,
)
from kernel_gen.execute_engine.entry_shim_builder import (
    build_entry_shim_source,
    needs_entry_shim,
)
from kernel_gen.execute_engine.target_registry import target_includes
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError

FAILURE_TARGET_HEADER_MISMATCH = "target_header_mismatch"
FAILURE_SOURCE_EMPTY_OR_INVALID = "source_empty_or_invalid"
FAILURE_COMPILE_FAILED = "compile_failed"
FAILURE_SYMBOL_RESOLVE_FAILED = "symbol_resolve_failed"
FAILURE_RUNTIME_THROW_OR_ABORT = "runtime_throw_or_abort"
FAILURE_STREAM_NOT_SUPPORTED = "stream_not_supported"
FAILURE_FUNCTION_OUTPUT_CAPTURE_NOT_SUPPORTED = "function_output_capture_not_supported"

FAILURE_PHRASES: frozenset[str] = frozenset(
    {
        FAILURE_TARGET_HEADER_MISMATCH,
        FAILURE_SOURCE_EMPTY_OR_INVALID,
        FAILURE_COMPILE_FAILED,
        FAILURE_SYMBOL_RESOLVE_FAILED,
        FAILURE_RUNTIME_THROW_OR_ABORT,
        FAILURE_STREAM_NOT_SUPPORTED,
        FAILURE_FUNCTION_OUTPUT_CAPTURE_NOT_SUPPORTED,
    }
)

TargetName: TypeAlias = Literal["cpu", "npu_demo"]


def _execution_engine_error(failure_phrase: str, detail: str = "") -> KernelCodeError:
    """构造执行引擎统一错误对象。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 用 `KernelCodeError` 承载 execute_engine 的固定 `failure_phrase`。
    - 保留 `failure_phrase` metadata，兼容现有调用方按短语分类处理失败。

    使用示例:
    - err = _execution_engine_error(FAILURE_COMPILE_FAILED, "compiler is empty")
    - assert err.module() == "execute_engine"

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_execute_engine_contract.py
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    """

    if failure_phrase not in FAILURE_PHRASES:
        raise KernelCodeError(
            ErrorKind.CONTRACT,
            ErrorModule.EXECUTE_ENGINE,
            f"unknown failure phrase: {failure_phrase}",
        )
    message = failure_phrase if not detail else f"{failure_phrase}: {detail}"
    return KernelCodeError(
        ErrorKind.CONTRACT,
        ErrorModule.EXECUTE_ENGINE,
        message,
        failure_phrase=failure_phrase,
        detail=detail,
    )


def _source_include_family(source: str) -> str | None:
    """从 source 粗略推断 include family。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 用于在不执行真实编译的前提下，对 `target` 与源码 include family 的一致性进行最小校验。
    - 只识别仓库内约定路径片段：`include/cpu/` 与 `include/npu_demo/`。

    使用示例:
    - assert _source_include_family('#include \"include/cpu/Memory.h\"') == \"cpu\"

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_execute_engine_compile.py
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    """

    has_cpu = "include/cpu/" in source
    has_npu = "include/npu_demo/" in source
    if has_cpu and has_npu:
        return "mixed"
    if has_cpu:
        return "cpu"
    if has_npu:
        return "npu_demo"
    return None


def _inject_npu_demo_namespace_aliases(source: str) -> str:
    """为 `npu_demo::foo` 生成最小命名空间别名，兼容全局实现。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 识别源码中的 `npu_demo::` 调用，并注入 `namespace npu_demo { using ::foo; }` 别名。
    - 解决 `emit_c` 使用命名空间调用、但头文件只提供全局符号时的真实编译失败。

    使用示例:
    - _inject_npu_demo_namespace_aliases('#include "include/npu_demo/npu_demo.h"\\nvoid f(){ npu_demo::add(a,b,c); }')

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_execute_engine_compile.py
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    """

    symbols = sorted(set(re.findall(r"npu_demo::([A-Za-z_]\w*)\s*\(", source)))
    if not symbols:
        return source
    alias_lines = ["namespace npu_demo {"]
    alias_lines.extend(f"using ::{symbol};" for symbol in symbols)
    alias_lines.append("}")
    alias_block = "\n".join(alias_lines) + "\n"
    include_match = re.match(r"((?:\s*#include[^\n]*\n)+)", source)
    if include_match is not None:
        return f"{source[:include_match.end()]}\n{alias_block}{source[include_match.end():]}"
    return f"{alias_block}\n{source}"


REPO_ROOT = Path(__file__).resolve().parents[2]


def _ensure_compiler_flags(flags: tuple[str, ...]) -> tuple[str, ...]:
    """确保编译 flags 包含 -std=c++17 基线。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 若调用方未提供 `-std=c++17`，则按基线规则补齐。
    - 其余 flags 保持原有顺序。

    使用示例:
    - assert _ensure_compiler_flags(("-O2",)) == ("-std=c++17", "-O2")

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_execute_engine_compile.py
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    """

    if "-std=c++17" in flags:
        return flags
    return ("-std=c++17", *flags)


def _resolve_compiler_name(compiler: str | None) -> str:
    """解析编译器名称（P0/S2）。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 当 compiler 为空时回退到默认编译器。
    - 若 compiler 为空字符串或非字符串，则视为无效输入。

    使用示例:
    - assert _resolve_compiler_name(None) == "g++"

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_execute_engine_compile.py
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    """

    if compiler is None:
        return default_compiler()
    if not isinstance(compiler, str) or not compiler.strip():
        raise _execution_engine_error(
            FAILURE_COMPILE_FAILED,
            "compiler is empty",
        )
    return compiler




@dataclass(frozen=True)
class CompileRequest:
    """编译请求模型（P0）。"""

    source: str
    target: str
    function: str
    entry_point: str = "kg_execute_entry"
    compiler: str | None = None
    compiler_flags: tuple[str, ...] = ("-std=c++17",)
    link_flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExecuteRequest:
    """执行请求模型（P0）。"""

    args: tuple["RuntimeArg", ...]
    entry_point: str | None = None
    capture_function_output: bool = False
    stream: object | None = None


RuntimeArg: TypeAlias = Any


@dataclass(frozen=True)
class KgArgSlot:
    """entry shim 绑定槽位（P0/S3）。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 承载 entry shim 的按位参数信息，用于在 Python 侧完成 P0/S3 的顺序绑定校验。
    - 仅用于参数绑定与校验，不承担执行结果与内存拷贝。

    使用示例:
    - slot = KgArgSlot(position=0, kind="memory", dtype="float32", shape=(2, 2), stride=None, value=tensor)

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_execute_engine_invoke.py
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    """

    position: int
    kind: Literal["memory", "int", "float"]
    dtype: str | None
    shape: tuple[int, ...] | None
    stride: tuple[int, ...] | None
    value: object


def _normalize_dtype(value: object) -> str | None:
    """规范化 dtype 表达。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 统一 dtype 的字符串格式，支持 str、numpy/torch 的 dtype 对象。
    - 仅做最小规范化（去除 torch. 前缀），不做类型映射。

    使用示例:
    - assert _normalize_dtype("float32") == "float32"

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_execute_engine_invoke.py
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    """

    if value is None:
        return None
    if isinstance(value, str):
        dtype_str = value
    else:
        dtype_str = str(value)
    dtype_str = dtype_str.strip()
    if not dtype_str:
        return None
    if dtype_str.startswith("torch."):
        dtype_str = dtype_str.split(".", 1)[1]
    return dtype_str


def _normalize_shape(value: object) -> tuple[int, ...] | None:
    """规范化 shape 表达。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 统一 shape 为 tuple[int, ...]，用于 RuntimeArg 的 memory 校验。
    - shape 不可解析时返回 None。

    使用示例:
    - assert _normalize_shape(type("T", (), {"shape": (2, 3)})()) == (2, 3)

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_execute_engine_invoke.py
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    """

    if value is None or not hasattr(value, "shape"):
        return None
    try:
        return tuple(int(dim) for dim in getattr(value, "shape"))
    except TypeError:
        return None


def _normalize_stride(value: object) -> tuple[int, ...] | None:
    """规范化 stride 表达。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 统一 stride 为 tuple[int, ...]，用于 RuntimeArg 的 memory 校验与记录。
    - stride 不可解析时返回 None。

    使用示例:
    - assert _normalize_stride(type("T", (), {"stride": lambda self: (1, 2)})()) == (1, 2)

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_execute_engine_invoke.py
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    """

    if value is None:
        return None
    if hasattr(value, "stride"):
        stride_attr = getattr(value, "stride")
        stride = stride_attr() if callable(stride_attr) else stride_attr
        try:
            return tuple(int(dim) for dim in stride)
        except TypeError:
            return None
    if hasattr(value, "strides"):
        stride = getattr(value, "strides")
        try:
            stride_tuple = tuple(int(dim) for dim in stride)
        except TypeError:
            return None
        if _is_numpy_array(value):
            itemsize = getattr(value, "itemsize", None)
            if not isinstance(itemsize, int) or itemsize <= 0:
                return None
            if any(dim % itemsize != 0 for dim in stride_tuple):
                return None
            return tuple(int(dim // itemsize) for dim in stride_tuple)
        return stride_tuple
    return None


def _runtime_module_name(value: object) -> str:
    """提取 RuntimeArg 的模块前缀。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 为 torch/numpy 类型识别提供最小、无需导入依赖的判断依据。
    - 返回空字符串表示无法识别模块信息。

    使用示例:
    - assert _runtime_module_name(type("T", (), {"__module__": "torch"})()) == "torch"

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_execute_engine_invoke.py
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    """

    module_name = getattr(value.__class__, "__module__", "")
    return module_name or ""


def _is_torch_tensor(value: object) -> bool:
    """判断是否为 torch 张量类 RuntimeArg。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 基于 __module__ 前缀做轻量识别，避免直接导入 torch 依赖。
    - 仅用于 RuntimeArg 类型判定，不做数据合法性校验。

    使用示例:
    - assert _is_torch_tensor(type("T", (), {"__module__": "torch"})()) is True

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_execute_engine_invoke.py
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    """

    return _runtime_module_name(value).startswith("torch")


def _is_numpy_array(value: object) -> bool:
    """判断是否为 numpy 数组类 RuntimeArg。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 基于 __module__ 前缀做轻量识别，避免直接导入 numpy 依赖。
    - 仅用于 RuntimeArg 类型判定，不做数据合法性校验。

    使用示例:
    - assert _is_numpy_array(type("T", (), {"__module__": "numpy"})()) is True

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_execute_engine_invoke.py
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    """

    return _runtime_module_name(value).startswith("numpy")


def _is_runtime_int(value: object) -> bool:
    """判断是否为合法 int RuntimeArg（排除 bool）。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 允许 int 作为 RuntimeArg 的标量输入。
    - 显式排除 bool，避免把布尔值误判为整数。

    使用示例:
    - assert _is_runtime_int(3) is True
    - assert _is_runtime_int(True) is False

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_execute_engine_invoke.py
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    """

    return isinstance(value, int) and not isinstance(value, bool)


def _is_runtime_float(value: object) -> bool:
    """判断是否为合法 float RuntimeArg（排除 bool）。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 允许 float 作为 RuntimeArg 的标量输入。
    - 显式排除 bool，确保失败路径可控。

    使用示例:
    - assert _is_runtime_float(1.25) is True
    - assert _is_runtime_float(False) is False

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_execute_engine_invoke.py
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    """

    return isinstance(value, float) and not isinstance(value, bool)


def _is_memory_runtime_arg(value: object) -> bool:
    """判断是否为 memory RuntimeArg（torch/numpy）。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 仅当对象符合 torch/numpy 模块前缀且包含 shape/dtype 字段时视为 memory 参数。
    - 不对 shape/dtype 的合法性做复杂推断，留给后续校验逻辑处理。

    使用示例:
    - value = type("T", (), {"__module__": "torch", "shape": (1,), "dtype": "float32"})()
    - assert _is_memory_runtime_arg(value) is True

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_execute_engine_invoke.py
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    """

    if not (_is_torch_tensor(value) or _is_numpy_array(value)):
        return False
    return hasattr(value, "shape") and hasattr(value, "dtype")


def _is_contiguous_memory(value: object) -> bool:
    """判断 memory RuntimeArg 是否为连续布局。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - torch 路径优先使用 is_contiguous() 结果。
    - numpy 路径优先读取 flags["C_CONTIGUOUS"] 或 flags.c_contiguous。
    - 缺少相关信息时默认视为连续布局。

    使用示例:
    - value = type("T", (), {"__module__": "torch", "shape": (1,), "dtype": "float32", "is_contiguous": lambda self: True})()
    - assert _is_contiguous_memory(value) is True

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_execute_engine_invoke.py
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    """

    if hasattr(value, "is_contiguous"):
        try:
            return bool(value.is_contiguous())
        except Exception:
            return False
    if hasattr(value, "flags"):
        flags = value.flags
        if isinstance(flags, dict) and "C_CONTIGUOUS" in flags:
            return bool(flags["C_CONTIGUOUS"])
        if hasattr(flags, "c_contiguous"):
            return bool(flags.c_contiguous)
    return True


def _build_arg_slots(args: tuple[RuntimeArg, ...]) -> tuple[KgArgSlot, ...]:
    """按顺序构建 entry shim 参数槽位。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 校验 RuntimeArg 的类型与最小 memory 约束（shape/dtype/连续性）。
    - 失败时抛出 runtime_throw_or_abort，保证失败短语稳定。

    使用示例:
    - slots = _build_arg_slots((1, 2.0))

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_execute_engine_invoke.py
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    """

    slots: list[KgArgSlot] = []
    for idx, arg in enumerate(args):
        if _is_runtime_int(arg):
            slots.append(
                KgArgSlot(
                    position=idx,
                    kind="int",
                    dtype="int",
                    shape=None,
                    stride=None,
                    value=arg,
                )
            )
            continue
        if _is_runtime_float(arg):
            slots.append(
                KgArgSlot(
                    position=idx,
                    kind="float",
                    dtype="float",
                    shape=None,
                    stride=None,
                    value=arg,
                )
            )
            continue
        if _is_memory_runtime_arg(arg):
            if not _is_contiguous_memory(arg):
                raise _execution_engine_error(
                    FAILURE_RUNTIME_THROW_OR_ABORT,
                    f"memory arg is not contiguous at position {idx}",
                )
            dtype = _normalize_dtype(getattr(arg, "dtype", None))
            shape = _normalize_shape(arg)
            if dtype is None or shape is None:
                raise _execution_engine_error(
                    FAILURE_RUNTIME_THROW_OR_ABORT,
                    f"memory arg missing dtype/shape at position {idx}",
                )
            slots.append(
                KgArgSlot(
                    position=idx,
                    kind="memory",
                    dtype=dtype,
                    shape=shape,
                    stride=_normalize_stride(arg),
                    value=arg,
                )
            )
            continue
        raise _execution_engine_error(
            FAILURE_RUNTIME_THROW_OR_ABORT,
            f"unsupported RuntimeArg at position {idx}",
        )
    return tuple(slots)


def _contiguous_stride(shape: tuple[int, ...]) -> tuple[int, ...]:
    """按 shape 生成连续布局 stride（元素步长）。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 当运行时参数未显式提供 stride 时，生成行主序连续 stride。
    - 用于 memory 参数 ABI 封送前的兜底补全。

    使用示例:
    - _contiguous_stride((2, 3)) == (3, 1)

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_execute_engine_invoke.py
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    """

    if not shape:
        return ()
    stride = [1 for _ in shape]
    for idx in range(len(shape) - 2, -1, -1):
        stride[idx] = stride[idx + 1] * int(shape[idx + 1])
    return tuple(stride)


def _runtime_data_pointer(value: object) -> int:
    """读取 RuntimeArg 底层数据指针地址。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 对 `torch.Tensor` 使用 `data_ptr()`，对 `numpy.ndarray` 使用 `ctypes.data`。
    - 不支持的对象触发 `runtime_throw_or_abort`。

    使用示例:
    - _runtime_data_pointer(torch.zeros((2,), dtype=torch.int32))

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_execute_engine_invoke.py
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    """

    if _is_torch_tensor(value) and hasattr(value, "data_ptr"):
        data_ptr = value.data_ptr()
        return int(data_ptr)
    if _is_numpy_array(value) and hasattr(value, "ctypes"):
        return int(value.ctypes.data)
    raise _execution_engine_error(
        FAILURE_RUNTIME_THROW_OR_ABORT,
        "memory arg data pointer is unavailable",
    )


def _marshal_slots_for_abi(
    ordered_slots: tuple[KgArgSlot, ...],
) -> tuple[object, type[object], tuple[object, ...]]:
    """把 Python `KgArgSlot` 转为 C ABI 可调用结构。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 将 memory/int/float 三类运行参数封送为 `KgArgSlot` C 结构数组。
    - 返回 keepalive 对象集合，保证 shape/stride 缓冲区在调用期间有效。

    使用示例:
    - _marshal_slots_for_abi(_build_arg_slots((1, 2.0)))

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_execute_engine_invoke.py
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    """

    import ctypes

    class _CKgArgSlot(ctypes.Structure):
        _fields_ = [
            ("kind", ctypes.c_int),
            ("data", ctypes.c_void_p),
            ("shape", ctypes.POINTER(ctypes.c_longlong)),
            ("stride", ctypes.POINTER(ctypes.c_longlong)),
            ("rank", ctypes.c_ulonglong),
            ("int_value", ctypes.c_longlong),
            ("float_value", ctypes.c_double),
        ]

    c_slots: list[_CKgArgSlot] = []
    keepalive: list[object] = []
    for slot in ordered_slots:
        if slot.kind == "memory":
            if slot.shape is None:
                raise _execution_engine_error(
                    FAILURE_RUNTIME_THROW_OR_ABORT,
                    f"memory shape missing at position {slot.position}",
                )
            stride = slot.stride if slot.stride is not None else _contiguous_stride(slot.shape)
            if len(stride) != len(slot.shape):
                raise _execution_engine_error(
                    FAILURE_RUNTIME_THROW_OR_ABORT,
                    f"memory stride rank mismatch at position {slot.position}",
                )
            shape_buffer_type = ctypes.c_longlong * len(slot.shape)
            stride_buffer_type = ctypes.c_longlong * len(stride)
            shape_buffer = shape_buffer_type(*slot.shape)
            stride_buffer = stride_buffer_type(*stride)
            keepalive.extend([shape_buffer, stride_buffer])
            c_slots.append(
                _CKgArgSlot(
                    kind=1,
                    data=ctypes.c_void_p(_runtime_data_pointer(slot.value)),
                    shape=ctypes.cast(shape_buffer, ctypes.POINTER(ctypes.c_longlong)),
                    stride=ctypes.cast(stride_buffer, ctypes.POINTER(ctypes.c_longlong)),
                    rank=ctypes.c_ulonglong(len(slot.shape)),
                    int_value=ctypes.c_longlong(0),
                    float_value=ctypes.c_double(0.0),
                )
            )
            continue
        if slot.kind == "int":
            c_slots.append(
                _CKgArgSlot(
                    kind=2,
                    data=ctypes.c_void_p(0),
                    shape=ctypes.POINTER(ctypes.c_longlong)(),
                    stride=ctypes.POINTER(ctypes.c_longlong)(),
                    rank=ctypes.c_ulonglong(0),
                    int_value=ctypes.c_longlong(int(slot.value)),
                    float_value=ctypes.c_double(0.0),
                )
            )
            continue
        if slot.kind == "float":
            c_slots.append(
                _CKgArgSlot(
                    kind=3,
                    data=ctypes.c_void_p(0),
                    shape=ctypes.POINTER(ctypes.c_longlong)(),
                    stride=ctypes.POINTER(ctypes.c_longlong)(),
                    rank=ctypes.c_ulonglong(0),
                    int_value=ctypes.c_longlong(0),
                    float_value=ctypes.c_double(float(slot.value)),
                )
            )
            continue
        raise _execution_engine_error(
            FAILURE_RUNTIME_THROW_OR_ABORT,
            f"unsupported slot kind at position {slot.position}",
        )
    slot_array_type = _CKgArgSlot * len(c_slots)
    slot_array = slot_array_type(*c_slots)
    keepalive.append(slot_array)
    return (slot_array, _CKgArgSlot, tuple(keepalive))


def _load_entry_point(soname_path: str, entry_point: str) -> Callable[[tuple[KgArgSlot, ...]], int]:
    """加载 entry point 并返回可调用对象（P0/S3）。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 对真实 `.so` 执行动态加载，并把 Python 槽位转换为 C ABI 参数后调用入口。
    - 对 dry-run 生成的空产物，保留历史占位成功行为，避免破坏骨架测试。

    使用示例:
    - invoke = _load_entry_point("libkernel.so", "kg_execute_entry")
    - assert invoke(()) == 0

    关联文件:
    - spec: spec/execute_engine/execute_engine.md
    - test: test/execute_engine/test_execute_engine_invoke.py
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    """

    if not isinstance(soname_path, str) or not soname_path:
        raise _execution_engine_error(
            FAILURE_RUNTIME_THROW_OR_ABORT,
            "soname_path is empty",
        )
    soname = Path(soname_path)
    if not soname.is_file():
        raise _execution_engine_error(
            FAILURE_RUNTIME_THROW_OR_ABORT,
            "soname_path is missing",
        )
    if soname.stat().st_size == 0:
        def _invoke_placeholder(_slots: tuple[KgArgSlot, ...]) -> int:
            return 0

        return _invoke_placeholder

    import ctypes
    try:
        library = ctypes.CDLL(str(soname))
    except OSError as exc:
        raise _execution_engine_error(
            FAILURE_SYMBOL_RESOLVE_FAILED,
            f"unable to load shared object: {exc}",
        ) from exc
    try:
        symbol = getattr(library, entry_point)
    except AttributeError as exc:
        raise _execution_engine_error(
            FAILURE_SYMBOL_RESOLVE_FAILED,
            f"entry_point '{entry_point}' is missing",
        ) from exc

    def _invoke(ordered_slots: tuple[KgArgSlot, ...]) -> int:
        slot_array, slot_struct, keepalive = _marshal_slots_for_abi(ordered_slots)
        symbol.argtypes = [ctypes.POINTER(slot_struct), ctypes.c_ulonglong]
        symbol.restype = ctypes.c_int
        result = int(symbol(slot_array, ctypes.c_ulonglong(len(ordered_slots))))
        _ = keepalive
        return result

    return _invoke


@dataclass(frozen=True)
class ExecuteResult:
    """执行引擎对外结果模型（P0）。"""

    ok: bool
    status_code: int
    failure_phrase: str | None
    compile_stdout: str = ""
    compile_stderr: str = ""
    run_stdout: str = ""
    run_stderr: str = ""
    elapsed_ms: float = 0.0


@dataclass(frozen=True)
class CompiledKernel:
    """编译产物的只读描述（P0）。

    创建者: 朽木露琪亚
    最后一次更改: 金铲铲大作战

    功能说明:
    - 承载已编译产物的目标、共享库路径与入口名。
    - 若底层编译使用了内部临时工作目录，可通过 `close()` 显式释放；析构时也会兜底释放。

    使用示例:
    - kernel = engine.compile(source="int main(){}", function="cpu::add")
    - kernel.close()

    关联文件:
    - spec: spec/execute_engine/execute_engine.md
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_execute_engine_compile.py
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    """

    target: str
    soname_path: str
    function: str
    entry_point: str
    compile_stdout: str = ""
    compile_stderr: str = ""
    _cleanup: Callable[[], None] | None = field(default=None, repr=False, compare=False)

    def close(self) -> None:
        """释放编译产物关联的内部临时工作区。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 当 `compile()` 使用内部临时目录时，显式删除该目录，避免临时文件长期残留。
        - 重复调用是安全的，已关闭时不再重复释放。

        使用示例:
        - kernel = engine.compile(source="int main(){}", function="cpu::add")
        - kernel.close()

        关联文件:
        - spec: spec/execute_engine/execute_engine.md
        - spec: spec/execute_engine/execute_engine_api.md
        - test: test/execute_engine/test_execute_engine_compile.py
        - 功能实现: kernel_gen/execute_engine/execution_engine.py
        """

        cleanup = self._cleanup
        if cleanup is None:
            return
        object.__setattr__(self, "_cleanup", None)
        cleanup()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    def execute(
        self,
        args: tuple[RuntimeArg, ...] | None = None,
        *,
        request: ExecuteRequest | None = None,
        entry_point: str | None = None,
        capture_function_output: bool = False,
        stream: object | None = None,
    ) -> ExecuteResult:
        """执行已编译 kernel（骨架版本）。

        创建者: 朽木露琪亚
        最后一次更改: jcc你莫辜负

        功能说明:
        - S3 补齐调用路径：参数绑定、entry shim 协议、动态加载与执行返回。
        - 保持 `stream` / `capture_function_output` 的禁用行为与失败短语。
        - 成功时返回 `ok=True/status_code=0/failure_phrase=None` 并带回编译 stdout/stderr。

        使用示例:
        - result = kernel.execute(args=(1, 2.0))

        关联文件:
        - spec: spec/execute_engine/execute_engine.md
        - test: test/execute_engine/test_execute_engine_contract.py
        - 功能实现: kernel_gen/execute_engine/execution_engine.py
        """

        if request is not None:
            args = request.args
            entry_point = request.entry_point if entry_point is None else entry_point
            capture_function_output = request.capture_function_output
            stream = request.stream

        if stream is not None:
            raise _execution_engine_error(
                FAILURE_STREAM_NOT_SUPPORTED,
                "ExecuteRequest.stream is not supported in P0",
            )
        if capture_function_output:
            raise _execution_engine_error(
                FAILURE_FUNCTION_OUTPUT_CAPTURE_NOT_SUPPORTED,
                "ExecuteRequest.capture_function_output is not supported in P0",
            )

        if args is None:
            raise _execution_engine_error(
                FAILURE_RUNTIME_THROW_OR_ABORT,
                "args must be provided",
            )
        if not isinstance(args, tuple):
            raise _execution_engine_error(
                FAILURE_RUNTIME_THROW_OR_ABORT,
                "args must be a tuple",
            )
        ordered_slots = _build_arg_slots(args)

        resolved_entry = self.entry_point if entry_point is None else entry_point
        if not isinstance(resolved_entry, str) or not resolved_entry.strip():
            raise _execution_engine_error(
                FAILURE_SYMBOL_RESOLVE_FAILED,
                "entry_point is empty",
            )
        if resolved_entry != self.entry_point:
            raise _execution_engine_error(
                FAILURE_SYMBOL_RESOLVE_FAILED,
                "entry_point mismatch",
            )

        invoke_entry = _load_entry_point(self.soname_path, resolved_entry)
        status_code = invoke_entry(ordered_slots)
        if status_code != 0:
            raise _execution_engine_error(
                FAILURE_RUNTIME_THROW_OR_ABORT,
                f"entry_point returned non-zero ({status_code})",
            )

        return ExecuteResult(
            ok=True,
            status_code=0,
            failure_phrase=None,
            compile_stdout=self.compile_stdout,
            compile_stderr=self.compile_stderr,
        )


@dataclass(frozen=True)
class ExecutionEngine:
    """执行引擎入口（骨架版本，P0）。"""

    target: str
    compiler: str | None = None
    compiler_flags: tuple[str, ...] = ("-std=c++17",)
    link_flags: tuple[str, ...] = ()

    def compile(
        self,
        source: str | None = None,
        function: str | None = None,
        *,
        request: CompileRequest | None = None,
        entry_point: str = "kg_execute_entry",
    ) -> CompiledKernel:
        """编译 C++ 源码并返回 `CompiledKernel`（骨架版本）。

        创建者: 朽木露琪亚
        最后一次更改: jcc你莫辜负

        功能说明:
        - S2 阶段固定编译路径拼装：target include 选择 -> entry shim -> 编译命令生成 -> CompiledKernel。
        - `target=cpu` 保持 dry-run；`target=npu_demo` 走真实编译，支持下游合同验收的真实执行。
        - 编译失败时会先回收内部临时工作区，再抛出 `compile_failed`。
        - 保持公共失败短语：
          - `target_header_mismatch`
          - `source_empty_or_invalid`
          - `compile_failed`
          - `symbol_resolve_failed`

        使用示例:
        - kernel = ExecutionEngine(target="cpu").compile(source="...", function="cpu::add")

        关联文件:
        - spec: spec/execute_engine/execute_engine.md
        - spec: spec/execute_engine/execute_engine_target.md
        - test: test/execute_engine/test_execute_engine_compile.py
        - 功能实现: kernel_gen/execute_engine/execution_engine.py
        """

        if request is not None:
            source = request.source
            function = request.function
            entry_point = request.entry_point
            target = request.target
            compiler = _resolve_compiler_name(request.compiler)
            compiler_flags = _ensure_compiler_flags(request.compiler_flags)
            link_flags = request.link_flags
        else:
            target = self.target
            compiler = _resolve_compiler_name(self.compiler)
            compiler_flags = _ensure_compiler_flags(self.compiler_flags)
            link_flags = self.link_flags

        if target not in ("cpu", "npu_demo"):
            raise _execution_engine_error(
                FAILURE_TARGET_HEADER_MISMATCH,
                f"unsupported target: {target}",
            )
        if source is None or not isinstance(source, str) or not source.strip():
            raise _execution_engine_error(
                FAILURE_SOURCE_EMPTY_OR_INVALID,
                "source is empty",
            )
        include_family = _source_include_family(source)
        if include_family == "mixed":
            raise _execution_engine_error(
                FAILURE_TARGET_HEADER_MISMATCH,
                "source includes mixed target include families",
            )
        if include_family is not None and include_family != target:
            raise _execution_engine_error(
                FAILURE_TARGET_HEADER_MISMATCH,
                f"source include family mismatch: source={include_family}, target={target}",
            )
        if "#error" in source:
            raise _execution_engine_error(
                FAILURE_COMPILE_FAILED,
                "source contains #error directive",
            )
        if function is None or not isinstance(function, str) or not function.strip():
            raise _execution_engine_error(
                FAILURE_SYMBOL_RESOLVE_FAILED,
                "function is empty",
            )
        if not isinstance(entry_point, str) or not entry_point.strip():
            raise _execution_engine_error(
                FAILURE_SYMBOL_RESOLVE_FAILED,
                "entry_point is empty",
            )

        target_headers = target_includes(target)
        if not target_headers:
            raise _execution_engine_error(
                FAILURE_TARGET_HEADER_MISMATCH,
                f"unsupported target: {target}",
            )
        shim_source = ""
        if needs_entry_shim(source, entry_point):
            shim_source = build_entry_shim_source(
                function=function,
                entry_point=entry_point,
                source=source,
            )
        compile_unit = build_compile_unit(
            source=source,
            target_includes=target_headers,
            entry_shim_source=shim_source,
        )
        artifacts = compile_source(
            source=compile_unit,
            compiler=compiler,
            compiler_flags=compiler_flags,
            link_flags=link_flags,
            include_dirs=(str(REPO_ROOT),),
            dry_run=(target == "cpu"),
        )
        try:
            if artifacts.return_code != 0:
                raise _execution_engine_error(
                    FAILURE_COMPILE_FAILED,
                    f"compiler returned non-zero ({artifacts.return_code})",
                )
            if not Path(artifacts.soname_path).exists():
                raise _execution_engine_error(
                    FAILURE_COMPILE_FAILED,
                    "compile output is missing",
                )
        except Exception:
            if artifacts._cleanup is not None:
                try:
                    artifacts._cleanup()
                except Exception:
                    pass
            raise

        return CompiledKernel(
            target=target,
            soname_path=artifacts.soname_path,
            function=function,
            entry_point=entry_point,
            compile_stdout=artifacts.stdout,
            compile_stderr=artifacts.stderr,
            _cleanup=artifacts._cleanup,
        )


__all__ = [
    "FAILURE_TARGET_HEADER_MISMATCH",
    "FAILURE_SOURCE_EMPTY_OR_INVALID",
    "FAILURE_COMPILE_FAILED",
    "FAILURE_SYMBOL_RESOLVE_FAILED",
    "FAILURE_RUNTIME_THROW_OR_ABORT",
    "FAILURE_STREAM_NOT_SUPPORTED",
    "FAILURE_FUNCTION_OUTPUT_CAPTURE_NOT_SUPPORTED",
    "FAILURE_PHRASES",
    "RuntimeArg",
    "CompiledKernel",
    "CompileRequest",
    "ExecuteRequest",
    "ExecuteResult",
    "ExecutionEngine",
]
