"""ExecutionEngine compiler implementation.


功能说明:
- 承接执行引擎公开请求、结果、kernel、engine、strategy registry 与运行期 ABI。
- 内置 target include、entry shim、编译单元与真实编译支持委托 `target_support.py`，本文件只负责把 target support artifact 装配为 `CompiledKernel`。
- `kernel_gen.execute_engine` 包入口继续重导出执行引擎公开 API，不新增 `target_support` 包根导出。
- 当公开 core config 的 `trance_enabled` 开启时，编译期宏由 target support 模块注入，执行期仍按本文件 ABI 加载入口。

API 列表:
- `class CompileRequest(source: str, target: str, function: str, entry_point: str = "kg_execute_entry", compiler: str | None = None, compiler_flags: tuple[str, ...] = ("-std=c++17",), link_flags: tuple[str, ...] = ())`
- `class ExecuteRequest(args: tuple[RuntimeInput, ...], entry_point: str | None = None, capture_function_output: bool = False, stream: None = None)`
- `class ExecuteResult(ok: bool, status_code: int, failure_phrase: str | None, compile_stdout: str = "", compile_stderr: str = "", run_stdout: str = "", run_stderr: str = "", elapsed_ms: float = 0.0)`
- `class CompiledKernel(target: str, soname_path: str, function: str, entry_point: str, compile_stdout: str = "", compile_stderr: str = "")`
- `CompiledKernel.close() -> None`
- `CompiledKernel.execute(args: tuple[RuntimeInput, ...] | None = None, *, request: ExecuteRequest | None = None, entry_point: str | None = None, capture_function_output: bool = False, stream: None = None) -> ExecuteResult`
- `class CompileStrategy(Protocol)`
- `CompileStrategy.compile(self, request: CompileRequest) -> CompiledKernel`
- `register_compile_strategy(target: str, strategy: CompileStrategy, *, override: bool = False) -> None`
- `get_compile_strategy(target: str) -> CompileStrategy`
- `class ExecutionEngine(target: str, compiler: str | None = None, compiler_flags: tuple[str, ...] = ("-std=c++17",), link_flags: tuple[str, ...] = ())`
- `ExecutionEngine.compile(source: str | None = None, function: str | None = None, *, request: CompileRequest | None = None, entry_point: str = "kg_execute_entry") -> CompiledKernel`

helper 清单:
- 私有 helper 仅限本文件内部使用，不作为跨文件调用边界。

使用示例:
- from kernel_gen.execute_engine import ExecutionEngine, ExecuteRequest
- engine = ExecutionEngine(target="cpu")
- kernel = engine.compile(source="int main(){}", function="cpu::add")
- result = kernel.execute(request=ExecuteRequest(args=(1, 2.0)))

关联文件:
- spec: spec/execute_engine/execute_engine.md
- spec: spec/execute_engine/execute_engine_api.md
- spec: spec/execute_engine/execute_engine_target.md
- test: test/execute_engine/test_contract.py
- test: test/execute_engine/test_compile.py
- test: test/execute_engine/test_target_support.py
- test: test/execute_engine/test_invoke.py
- 功能实现: kernel_gen/execute_engine/compiler.py
- 功能实现: kernel_gen/execute_engine/target_support.py
"""

from __future__ import annotations

from collections.abc import Iterable
import ctypes
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
import re
from typing import Callable, Literal, Protocol, TypeAlias, runtime_checkable

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.target import registry as target_registry


@dataclass(frozen=True)
class _AllowAbsentMemoryArg:
    """allow-absent memory runtime 参数元数据。

    功能说明:
    - 承载生成源码注释中的 runtime 参数索引、nominal dtype 与 nominal rank。
    - 只服务当前执行引擎文件内的 entry shim 和 ABI 封送逻辑。

    使用示例:
    - metadata = _AllowAbsentMemoryArg(index=3, dtype="float", rank=1)
    """

    index: int
    dtype: str
    rank: int


def _allow_absent_memory_arg_map(metadata: tuple[_AllowAbsentMemoryArg, ...]) -> dict[int, _AllowAbsentMemoryArg]:
    """把 allow-absent metadata 转成按 runtime index 查询的字典。

    功能说明:
    - 统一 entry shim 与 Python ABI 封送路径的查询口径。

    使用示例:
    - metadata_map = _allow_absent_memory_arg_map(metadata)
    """

    return {item.index: item for item in metadata}


def _dtype_code_from_name(dtype: str | None) -> int:
    """把运行时 dtype 文本映射为 C ABI dtype code。

    功能说明:
    - 仅为 template shim 分支选择提供最小 dtype 编码。
    - 未识别 dtype 返回 0，C shim 会拒绝需要 template 实例化的调用。

    使用示例:
    - code = _dtype_code_from_name("float32")
    """

    if dtype is None:
        return 0
    normalized = dtype.strip().lower().replace(" ", "")
    if normalized in {"float", "float32", "f32"}:
        return 1
    if normalized in {"double", "float64", "f64"}:
        return 2
    if normalized in {"int", "int32", "int32_t", "i32"}:
        return 3
    if normalized in {"longlong", "longlongint", "int64", "int64_t", "i64"}:
        return 4
    return 0


_TARGET_HEADER_MISMATCH = "target_header_mismatch"
_SOURCE_EMPTY_OR_INVALID = "source_empty_or_invalid"
_COMPILE_FAILED = "compile_failed"
_TEMPLATE_INSTANCE_REQUIRED = "template_instance_required"
_SYMBOL_RESOLVE_FAILED = "symbol_resolve_failed"
_RUNTIME_THROW_OR_ABORT = "runtime_throw_or_abort"
_STREAM_NOT_SUPPORTED = "stream_not_supported"
_FUNCTION_OUTPUT_CAPTURE_NOT_SUPPORTED = "function_output_capture_not_supported"
_EXECUTION_UNSUPPORTED = "execution_unsupported"

_KNOWN_ERROR_PHRASES: frozenset[str] = frozenset(
    {
        _TARGET_HEADER_MISMATCH,
        _SOURCE_EMPTY_OR_INVALID,
        _COMPILE_FAILED,
        _TEMPLATE_INSTANCE_REQUIRED,
        _SYMBOL_RESOLVE_FAILED,
        _RUNTIME_THROW_OR_ABORT,
        _STREAM_NOT_SUPPORTED,
        _FUNCTION_OUTPUT_CAPTURE_NOT_SUPPORTED,
        _EXECUTION_UNSUPPORTED,
    }
)


class _StringValue(Protocol):
    """可稳定转为字符串的运行期值。"""

    def __str__(self) -> str:
        """返回字符串表示。"""


class _MemoryRuntimeInput(Protocol):
    """执行引擎支持的最小 memory runtime 参数协议。"""

    shape: Iterable[int]
    dtype: _StringValue


RuntimeInput: TypeAlias = "_MemoryRuntimeInput | int | float | None"
_RuntimeInputValue: TypeAlias = "RuntimeInput | _StringValue | None"


class _LoadedEntrySymbol(Protocol):
    """ctypes 动态库入口 symbol 的最小调用协议。"""

    argtypes: list[type]
    restype: type[ctypes.c_int]

    def __call__(self, slots: ctypes.Array, count: ctypes.c_ulonglong) -> int:
        """调用 C ABI entry symbol。"""


def _execution_engine_error(failure_phrase: str, detail: str = "") -> KernelCodeError:
    """构造执行引擎统一错误对象。

    创建者: OpenAI Codex
    最后一次更改: 大闸蟹

    功能说明:
    - 用 `KernelCodeError` 承载 execute_engine 的固定 `failure_phrase`。
    - 不通过 `KernelCodeError` 构造参数传递 metadata；固定短语由本 helper 在对象创建后写入。

    使用示例:
    - err = _execution_engine_error(_COMPILE_FAILED, "compiler is empty")
    - assert err.module() == "execute_engine"

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_contract.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    if failure_phrase not in _KNOWN_ERROR_PHRASES:
        raise KernelCodeError(
            ErrorKind.CONTRACT,
            ErrorModule.EXECUTE_ENGINE,
            f"unknown failure phrase: {failure_phrase}",
        )
    message = failure_phrase if not detail else f"{failure_phrase}: {detail}"
    error = KernelCodeError(
        ErrorKind.CONTRACT,
        ErrorModule.EXECUTE_ENGINE,
        message,
    )
    error.failure_phrase = failure_phrase
    return error


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

    args: tuple[RuntimeInput, ...]
    entry_point: str | None = None
    capture_function_output: bool = False
    stream: None = None


@dataclass(frozen=True)
class _ArgSlot:
    """entry shim 绑定槽位（P0/S3）。


    功能说明:
    - 承载 entry shim 的按位参数信息，用于在 Python 侧完成 P0/S3 的顺序绑定校验。
    - 仅用于参数绑定与校验，不承担执行结果与内存拷贝。

    使用示例:
    - slot = _ArgSlot(position=0, kind="memory", dtype="float32", shape=(2, 2), stride=None, value=tensor)

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    position: int
    kind: Literal["memory", "int", "float"]
    dtype: str | None
    dtype_code: int
    shape: tuple[int, ...] | None
    stride: tuple[int, ...] | None
    value: RuntimeInput


class _CArgSlot(ctypes.Structure):
    """entry shim C ABI 槽位结构。

    功能说明:
    - 固定 Python 侧与 C++ entry shim 共用的参数槽位内存布局。
    - 顶层定义避免运行时封送逻辑在函数内部创建嵌套类。

    使用示例:
    - slot = _CArgSlot(kind=2, data=None, shape=None, stride=None, rank=0, dtype_code=0, int_value=1, float_value=0.0)
    """

    _fields_ = [
        ("kind", ctypes.c_int),
        ("data", ctypes.c_void_p),
        ("shape", ctypes.POINTER(ctypes.c_longlong)),
        ("stride", ctypes.POINTER(ctypes.c_longlong)),
        ("rank", ctypes.c_ulonglong),
        ("dtype_code", ctypes.c_int),
        ("int_value", ctypes.c_longlong),
        ("float_value", ctypes.c_double),
    ]


def _normalize_dtype(value: _StringValue | None) -> str | None:
    """规范化 dtype 表达。


    功能说明:
    - 统一 dtype 的字符串格式，支持 str、numpy/torch 的 dtype 对象。
    - 仅做最小规范化（去除 torch. 前缀），不做类型映射。

    使用示例:
    - assert _normalize_dtype("float32") == "float32"

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
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


def _normalize_shape(value: _MemoryRuntimeInput | None) -> tuple[int, ...] | None:
    """规范化 shape 表达。


    功能说明:
    - 统一 shape 为 tuple[int, ...]，用于 运行时参数的 memory 校验。
    - shape 不可解析时返回 None。

    使用示例:
    - assert _normalize_shape(type("T", (), {"shape": (2, 3)})()) == (2, 3)

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    if value is None or not hasattr(value, "shape"):
        return None
    try:
        return tuple(int(dim) for dim in getattr(value, "shape"))
    except TypeError:
        return None


def _normalize_stride(value: _MemoryRuntimeInput | None) -> tuple[int, ...] | None:
    """规范化 stride 表达。


    功能说明:
    - 统一 stride 为 tuple[int, ...]，用于 运行时参数的 memory 校验与记录。
    - stride 不可解析时返回 None。

    使用示例:
    - assert _normalize_stride(type("T", (), {"stride": lambda self: (1, 2)})()) == (1, 2)

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
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


def _runtime_module_name(value: _RuntimeInputValue) -> str:
    """提取 运行时参数的模块前缀。


    功能说明:
    - 为 torch/numpy 类型识别提供最小、无需导入依赖的判断依据。
    - 返回空字符串表示无法识别模块信息。

    使用示例:
    - assert _runtime_module_name(type("T", (), {"__module__": "torch"})()) == "torch"

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    module_name = getattr(value.__class__, "__module__", "")
    return module_name or ""


def _is_torch_tensor(value: _RuntimeInputValue) -> bool:
    """判断是否为 torch 张量类 _RuntimeInput。


    功能说明:
    - 基于 __module__ 前缀做轻量识别，避免直接导入 torch 依赖。
    - 仅用于 运行时参数类型判定，不做数据合法性校验。

    使用示例:
    - assert _is_torch_tensor(type("T", (), {"__module__": "torch"})()) is True

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    return _runtime_module_name(value).startswith("torch")


def _is_numpy_array(value: _RuntimeInputValue) -> bool:
    """判断是否为 numpy 数组类 _RuntimeInput。


    功能说明:
    - 基于 __module__ 前缀做轻量识别，避免直接导入 numpy 依赖。
    - 仅用于 运行时参数类型判定，不做数据合法性校验。

    使用示例:
    - assert _is_numpy_array(type("T", (), {"__module__": "numpy"})()) is True

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    return _runtime_module_name(value).startswith("numpy")


def _is_runtime_int(value: _RuntimeInputValue) -> bool:
    """判断是否为合法 int _RuntimeInput（排除 bool）。


    功能说明:
    - 允许 int 作为 运行时参数的标量输入。
    - 显式排除 bool，避免把布尔值误判为整数。

    使用示例:
    - assert _is_runtime_int(3) is True
    - assert _is_runtime_int(True) is False

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    return isinstance(value, int) and not isinstance(value, bool)


def _is_runtime_float(value: _RuntimeInputValue) -> bool:
    """判断是否为合法 float _RuntimeInput（排除 bool）。


    功能说明:
    - 允许 float 作为 运行时参数的标量输入。
    - 显式排除 bool，确保失败路径可控。

    使用示例:
    - assert _is_runtime_float(1.25) is True
    - assert _is_runtime_float(False) is False

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    return isinstance(value, float) and not isinstance(value, bool)


def _is_memory_runtime_arg(value: _RuntimeInputValue) -> bool:
    """判断是否为 memory 运行时参数（torch/numpy）。


    功能说明:
    - 仅当对象符合 torch/numpy 模块前缀且包含 shape/dtype 字段时视为 memory 参数。
    - 不对 shape/dtype 的合法性做复杂推断，留给后续校验逻辑处理。

    使用示例:
    - value = type("T", (), {"__module__": "torch", "shape": (1,), "dtype": "float32"})()
    - assert _is_memory_runtime_arg(value) is True

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    if not (_is_torch_tensor(value) or _is_numpy_array(value)):
        return False
    return hasattr(value, "shape") and hasattr(value, "dtype")


def _is_contiguous_memory(value: _MemoryRuntimeInput) -> bool:
    """判断 memory 运行时参数 是否为连续布局。


    功能说明:
    - torch 路径优先使用 is_contiguous() 结果。
    - numpy 路径优先读取 flags["C_CONTIGUOUS"] 或 flags.c_contiguous。
    - 缺少相关信息时默认视为连续布局。

    使用示例:
    - value = type("T", (), {"__module__": "torch", "shape": (1,), "dtype": "float32", "is_contiguous": lambda self: True})()
    - assert _is_contiguous_memory(value) is True

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
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


def _build_arg_slots(
    args: tuple[RuntimeInput, ...],
    allow_absent_memory_args: tuple[_AllowAbsentMemoryArg, ...] = (),
) -> tuple[_ArgSlot, ...]:
    """按顺序构建 entry shim 参数槽位。


    功能说明:
    - 校验 _RuntimeInput 的类型与最小 memory 约束（shape/dtype/连续性）。
    - 仅当源码 metadata 声明对应索引为 allow-absent memory 时接受 `None`。
    - 失败时抛出 runtime_throw_or_abort，保证失败短语稳定。

    使用示例:
    - slots = _build_arg_slots((1, 2.0))

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    slots: list[_ArgSlot] = []
    allow_absent_map = _allow_absent_memory_arg_map(allow_absent_memory_args)
    for idx, arg in enumerate(args):
        if arg is None:
            metadata = allow_absent_map.get(idx)
            if metadata is None:
                raise _execution_engine_error(
                    _RUNTIME_THROW_OR_ABORT,
                    f"None runtime arg requires allow-absent memory metadata at position {idx}",
                )
            slots.append(
                _ArgSlot(
                    position=idx,
                    kind="memory",
                    dtype=metadata.dtype,
                    dtype_code=_dtype_code_from_name(metadata.dtype),
                    shape=(0,),
                    stride=(1,),
                    value=None,
                )
            )
            continue
        if _is_runtime_int(arg):
            slots.append(
                _ArgSlot(
                    position=idx,
                    kind="int",
                    dtype="int",
                    dtype_code=0,
                    shape=None,
                    stride=None,
                    value=arg,
                )
            )
            continue
        if _is_runtime_float(arg):
            slots.append(
                _ArgSlot(
                    position=idx,
                    kind="float",
                    dtype="float",
                    dtype_code=0,
                    shape=None,
                    stride=None,
                    value=arg,
                )
            )
            continue
        if _is_memory_runtime_arg(arg):
            if not _is_contiguous_memory(arg):
                raise _execution_engine_error(
                    _RUNTIME_THROW_OR_ABORT,
                    f"memory arg is not contiguous at position {idx}",
                )
            dtype = _normalize_dtype(getattr(arg, "dtype", None))
            shape = _normalize_shape(arg)
            if dtype is None or shape is None:
                raise _execution_engine_error(
                    _RUNTIME_THROW_OR_ABORT,
                    f"memory arg missing dtype/shape at position {idx}",
                )
            slots.append(
                _ArgSlot(
                    position=idx,
                    kind="memory",
                    dtype=dtype,
                    dtype_code=_dtype_code_from_name(dtype),
                    shape=shape,
                    stride=_normalize_stride(arg),
                    value=arg,
                )
            )
            continue
        raise _execution_engine_error(
            _RUNTIME_THROW_OR_ABORT,
            f"unsupported runtime arg at position {idx}",
        )
    return tuple(slots)


def _contiguous_stride(shape: tuple[int, ...]) -> tuple[int, ...]:
    """按 shape 生成连续布局 stride（元素步长）。


    功能说明:
    - 当运行时参数未显式提供 stride 时，生成行主序连续 stride。
    - 用于 memory 参数 ABI 封送前的兜底补全。

    使用示例:
    - _contiguous_stride((2, 3)) == (3, 1)

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    if not shape:
        return ()
    stride = [1 for _ in shape]
    for idx in range(len(shape) - 2, -1, -1):
        stride[idx] = stride[idx + 1] * int(shape[idx + 1])
    return tuple(stride)


def _runtime_data_pointer(value: _MemoryRuntimeInput) -> int:
    """读取运行时参数底层数据指针地址。


    功能说明:
    - 对 `torch.Tensor` 使用 `data_ptr()`，对 `numpy.ndarray` 使用 `ctypes.data`。
    - 不支持的对象触发 `runtime_throw_or_abort`。

    使用示例:
    - _runtime_data_pointer(torch.zeros((2,), dtype=torch.int32))

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    if _is_torch_tensor(value) and hasattr(value, "data_ptr"):
        data_ptr = value.data_ptr()
        return int(data_ptr)
    if _is_numpy_array(value) and hasattr(value, "ctypes"):
        return int(value.ctypes.data)
    raise _execution_engine_error(
        _RUNTIME_THROW_OR_ABORT,
        "memory arg data pointer is unavailable",
    )


def _marshal_slots_for_abi(
    ordered_slots: tuple[_ArgSlot, ...],
) -> tuple[ctypes.Array, type[ctypes.Structure], tuple[ctypes.Array, ...]]:
    """把 Python `_ArgSlot` 转为 C ABI 可调用结构。


    功能说明:
    - 将 memory/int/float 三类运行参数封送为 `_ArgSlot` C 结构数组。
    - 返回 keepalive 对象集合，保证 shape/stride 缓冲区在调用期间有效。

    使用示例:
    - _marshal_slots_for_abi(_build_arg_slots((1, 2.0)))

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    c_slots: list[_CArgSlot] = []
    keepalive: list[ctypes.Array] = []
    for slot in ordered_slots:
        if slot.kind == "memory":
            if slot.shape is None:
                raise _execution_engine_error(
                    _RUNTIME_THROW_OR_ABORT,
                    f"memory shape missing at position {slot.position}",
                )
            stride = slot.stride if slot.stride is not None else _contiguous_stride(slot.shape)
            if len(stride) != len(slot.shape):
                raise _execution_engine_error(
                    _RUNTIME_THROW_OR_ABORT,
                    f"memory stride rank mismatch at position {slot.position}",
                )
            shape_buffer_type = ctypes.c_longlong * len(slot.shape)
            stride_buffer_type = ctypes.c_longlong * len(stride)
            shape_buffer = shape_buffer_type(*slot.shape)
            stride_buffer = stride_buffer_type(*stride)
            keepalive.extend([shape_buffer, stride_buffer])
            data_pointer = 0 if slot.value is None else _runtime_data_pointer(slot.value)
            c_slots.append(
                _CArgSlot(
                    kind=1,
                    data=ctypes.c_void_p(data_pointer),
                    shape=ctypes.cast(shape_buffer, ctypes.POINTER(ctypes.c_longlong)),
                    stride=ctypes.cast(stride_buffer, ctypes.POINTER(ctypes.c_longlong)),
                    rank=ctypes.c_ulonglong(len(slot.shape)),
                    dtype_code=ctypes.c_int(slot.dtype_code),
                    int_value=ctypes.c_longlong(0),
                    float_value=ctypes.c_double(0.0),
                )
            )
            continue
        if slot.kind == "int":
            c_slots.append(
                _CArgSlot(
                    kind=2,
                    data=ctypes.c_void_p(0),
                    shape=ctypes.POINTER(ctypes.c_longlong)(),
                    stride=ctypes.POINTER(ctypes.c_longlong)(),
                    rank=ctypes.c_ulonglong(0),
                    dtype_code=ctypes.c_int(0),
                    int_value=ctypes.c_longlong(int(slot.value)),
                    float_value=ctypes.c_double(0.0),
                )
            )
            continue
        if slot.kind == "float":
            c_slots.append(
                _CArgSlot(
                    kind=3,
                    data=ctypes.c_void_p(0),
                    shape=ctypes.POINTER(ctypes.c_longlong)(),
                    stride=ctypes.POINTER(ctypes.c_longlong)(),
                    rank=ctypes.c_ulonglong(0),
                    dtype_code=ctypes.c_int(0),
                    int_value=ctypes.c_longlong(0),
                    float_value=ctypes.c_double(float(slot.value)),
                )
            )
            continue
        raise _execution_engine_error(
            _RUNTIME_THROW_OR_ABORT,
            f"unsupported slot kind at position {slot.position}",
        )
    slot_array_type = _CArgSlot * len(c_slots)
    slot_array = slot_array_type(*c_slots)
    keepalive.append(slot_array)
    return (slot_array, _CArgSlot, tuple(keepalive))


def _invoke_placeholder_entry(_slots: tuple[_ArgSlot, ...]) -> int:
    """执行 dry-run 空产物占位入口。


    功能说明:
    - 保持空 `.so` 产物的历史成功行为。

    使用示例:
    - _invoke_placeholder_entry(())

    关联文件:
    - spec: spec/execute_engine/execute_engine.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    return 0


def _invoke_loaded_entry_symbol(
    ordered_slots: tuple[_ArgSlot, ...],
    *,
    symbol: _LoadedEntrySymbol,
) -> int:
    """调用已解析出的 C ABI entry symbol。


    功能说明:
    - 将 Python 参数槽位封送为 `_ArgSlot` 数组。
    - 调用 `ctypes` symbol 并返回整数状态码。

    使用示例:
    - invoke = partial(_invoke_loaded_entry_symbol, symbol=symbol)
    - invoke(())

    关联文件:
    - spec: spec/execute_engine/execute_engine.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    slot_array, slot_struct, keepalive = _marshal_slots_for_abi(ordered_slots)
    symbol.argtypes = [ctypes.POINTER(slot_struct), ctypes.c_ulonglong]
    symbol.restype = ctypes.c_int
    result = int(symbol(slot_array, ctypes.c_ulonglong(len(ordered_slots))))
    _ = keepalive
    return result


def _load_entry_point(soname_path: str, entry_point: str) -> Callable[[tuple[_ArgSlot, ...]], int]:
    """加载 entry point 并返回可调用对象（P0/S3）。


    功能说明:
    - 对真实 `.so` 执行动态加载，并把 Python 槽位转换为 C ABI 参数后调用入口。
    - 对 dry-run 生成的空产物，保留历史占位成功行为，避免破坏骨架测试。

    使用示例:
    - invoke = _load_entry_point("libkernel.so", "kg_execute_entry")
    - assert invoke(()) == 0

    关联文件:
    - spec: spec/execute_engine/execute_engine.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    if not isinstance(soname_path, str) or not soname_path:
        raise _execution_engine_error(
            _RUNTIME_THROW_OR_ABORT,
            "soname_path is empty",
        )
    soname = Path(soname_path)
    if not soname.is_file():
        raise _execution_engine_error(
            _RUNTIME_THROW_OR_ABORT,
            "soname_path is missing",
        )
    if soname.stat().st_size == 0:
        return _invoke_placeholder_entry

    try:
        library = ctypes.CDLL(str(soname))
    except OSError as exc:
        raise _execution_engine_error(
            _SYMBOL_RESOLVE_FAILED,
            f"unable to load shared object: {exc}",
        ) from exc
    try:
        symbol = getattr(library, entry_point)
    except AttributeError as exc:
        raise _execution_engine_error(
            _SYMBOL_RESOLVE_FAILED,
            f"entry_point '{entry_point}' is missing",
        ) from exc

    return partial(_invoke_loaded_entry_symbol, symbol=symbol)


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


    功能说明:
    - 承载已编译产物的目标、共享库路径与入口名。
    - 若底层编译使用了内部临时工作目录，可通过 `close()` 显式释放；析构时也会兜底释放。

    使用示例:
    - kernel = engine.compile(source="int main(){}", function="cpu::add")
    - kernel.close()

    关联文件:
    - spec: spec/execute_engine/execute_engine.md
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_compile.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    target: str
    soname_path: str
    function: str
    entry_point: str
    compile_stdout: str = ""
    compile_stderr: str = ""
    allow_absent_memory_args: tuple[_AllowAbsentMemoryArg, ...] = field(default_factory=tuple, repr=False, compare=False)
    _cleanup: Callable[[], None] | None = field(default=None, repr=False, compare=False)
    _cleanup_state: list[Callable[[], None] | None] = field(default_factory=list, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        """初始化关闭状态。


        功能说明:
        - 保持 `CompiledKernel` 对外 frozen，同时用私有可变状态记录 cleanup 是否已消费。

        使用示例:
        - kernel = engine.compile(source="int main(){}", function="cpu::add")
        - kernel.close()

        关联文件:
        - spec: spec/execute_engine/execute_engine.md
        - test: test/execute_engine/test_compile.py
        - 功能实现: kernel_gen/execute_engine/compiler.py
        """

        self._cleanup_state.append(self._cleanup)

    def close(self) -> None:
        """释放编译产物关联的内部临时工作区。


        功能说明:
        - 当 `compile()` 使用内部临时目录时，显式删除该目录，避免临时文件长期残留。
        - 重复调用是安全的，已关闭时不再重复释放。

        使用示例:
        - kernel = engine.compile(source="int main(){}", function="cpu::add")
        - kernel.close()

        关联文件:
        - spec: spec/execute_engine/execute_engine.md
        - spec: spec/execute_engine/execute_engine_api.md
        - test: test/execute_engine/test_compile.py
        - 功能实现: kernel_gen/execute_engine/compiler.py
        """

        cleanup = self._cleanup_state[0] if self._cleanup_state else None
        if cleanup is None:
            return
        self._cleanup_state[0] = None
        cleanup()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    def execute(
        self,
        args: tuple[RuntimeInput, ...] | None = None,
        *,
        request: ExecuteRequest | None = None,
        entry_point: str | None = None,
        capture_function_output: bool = False,
        stream: None = None,
    ) -> ExecuteResult:
        """执行已编译 kernel（骨架版本）。


        功能说明:
        - S3 补齐调用路径：参数绑定、entry shim 协议、动态加载与执行返回。
        - 保持 `stream` / `capture_function_output` 的禁用行为与失败短语。
        - 成功时返回 `ok=True/status_code=0/failure_phrase=None` 并带回编译 stdout/stderr。

        使用示例:
        - result = kernel.execute(args=(1, 2.0))

        关联文件:
        - spec: spec/execute_engine/execute_engine.md
        - test: test/execute_engine/test_contract.py
        - 功能实现: kernel_gen/execute_engine/compiler.py
        """

        if request is not None:
            args = request.args
            entry_point = request.entry_point if entry_point is None else entry_point
            capture_function_output = request.capture_function_output
            stream = request.stream

        if stream is not None:
            raise _execution_engine_error(
                _STREAM_NOT_SUPPORTED,
                "ExecuteRequest.stream is not supported in P0",
            )
        if capture_function_output:
            raise _execution_engine_error(
                _FUNCTION_OUTPUT_CAPTURE_NOT_SUPPORTED,
                "ExecuteRequest.capture_function_output is not supported in P0",
            )
        if self.target not in ("cpu", "npu_demo"):
            raise _execution_engine_error(
                _EXECUTION_UNSUPPORTED,
                "compiled target does not expose runtime execution",
            )

        if args is None:
            raise _execution_engine_error(
                _RUNTIME_THROW_OR_ABORT,
                "args must be provided",
            )
        if not isinstance(args, tuple):
            raise _execution_engine_error(
                _RUNTIME_THROW_OR_ABORT,
                "args must be a tuple",
            )
        ordered_slots = _build_arg_slots(args, self.allow_absent_memory_args)

        resolved_entry = self.entry_point if entry_point is None else entry_point
        if not isinstance(resolved_entry, str) or not resolved_entry.strip():
            raise _execution_engine_error(
                _SYMBOL_RESOLVE_FAILED,
                "entry_point is empty",
            )
        if resolved_entry != self.entry_point:
            raise _execution_engine_error(
                _SYMBOL_RESOLVE_FAILED,
                "entry_point mismatch",
            )

        invoke_entry = _load_entry_point(self.soname_path, resolved_entry)
        status_code = invoke_entry(ordered_slots)
        if status_code != 0:
            raise _execution_engine_error(
                _RUNTIME_THROW_OR_ABORT,
                f"entry_point returned non-zero ({status_code})",
            )

        return ExecuteResult(
            ok=True,
            status_code=0,
            failure_phrase=None,
            compile_stdout=self.compile_stdout,
            compile_stderr=self.compile_stderr,
        )


@runtime_checkable
class CompileStrategy(Protocol):
    """编译策略公开协议。


    功能说明:
    - 第三方 backend 通过该协议接入 `ExecutionEngine.compile(...)`。
    - 策略只接收已归一化的 `CompileRequest`，返回 `CompiledKernel`。

    使用示例:
    - class MyStrategy:
    -     def compile(self, request: CompileRequest) -> CompiledKernel:
    -         ...
    """

    def compile(self, request: CompileRequest) -> CompiledKernel:
        """执行 target 专属编译。


        功能说明:
        - 使用 `CompileRequest` 中的 source、target、function、entry_point 和编译选项生成 `CompiledKernel`。
        - 失败必须抛出带稳定 failure_phrase 的 `KernelCodeError`。

        使用示例:
        - kernel = strategy.compile(request)
        """


_COMPILE_STRATEGIES: dict[str, CompileStrategy] = {}
_TARGET_NAME_PATTERN = re.compile(r"^[a-z0-9_]+$")


def _validate_strategy_target(target: str) -> None:
    """校验 compile strategy target。


    功能说明:
    - target 名必须满足 `[a-z0-9_]+`。
    - target 必须已通过公开 target registry 注册。

    使用示例:
    - _validate_strategy_target("cpu")
    """

    if not isinstance(target, str) or not _TARGET_NAME_PATTERN.fullmatch(target):
        raise _execution_engine_error(_TARGET_HEADER_MISMATCH, "invalid target name")
    try:
        target_registry.get_target_hardware(target, "__compile_strategy_probe__")
    except ValueError as exc:
        raise _execution_engine_error(_TARGET_HEADER_MISMATCH, f"target not registered: {target}") from exc


def register_compile_strategy(target: str, strategy: CompileStrategy, *, override: bool = False) -> None:
    """注册 target 对应的编译策略。


    功能说明:
    - `target` 必须是已注册 target。
    - 默认拒绝重复注册；`override=True` 时显式覆盖。
    - strategy 必须提供 `compile(request: CompileRequest) -> CompiledKernel` 方法。

    使用示例:
    - register_compile_strategy("cpu", strategy, override=True)
    """

    _validate_strategy_target(target)
    if not isinstance(strategy, CompileStrategy):
        raise _execution_engine_error(_COMPILE_FAILED, "compile strategy must define compile")
    if target in _COMPILE_STRATEGIES and not override:
        raise _execution_engine_error(_COMPILE_FAILED, f"duplicate compile strategy: {target}")
    _COMPILE_STRATEGIES[target] = strategy


def get_compile_strategy(target: str) -> CompileStrategy:
    """读取 target 对应编译策略。


    功能说明:
    - target 必须是已注册 target。
    - 未注册 strategy 不回退到 `cpu` 或 `npu_demo`，稳定失败为 `target_header_mismatch`。

    使用示例:
    - strategy = get_compile_strategy("cpu")
    """

    _validate_strategy_target(target)
    strategy = _COMPILE_STRATEGIES.get(target)
    if strategy is None:
        raise _execution_engine_error(_TARGET_HEADER_MISMATCH, f"missing compile strategy: {target}")
    return strategy


from kernel_gen.execute_engine.target_support import (
    BuiltinTargetSupportArtifacts,
    build_builtin_target_support_artifacts,
)


def _allow_absent_memory_args_from_specs(
    specs: tuple[tuple[int, str, int], ...],
) -> tuple[_AllowAbsentMemoryArg, ...]:
    """把 target support 的纯元数据转成执行期 allow-absent memory 描述。

    功能说明:
    - 保持 `target_support.py` 不依赖本文件私有运行期结构。
    - 仅在内置 strategy 装配 `CompiledKernel` 前做字段转换。

    使用示例:
    - metadata = _allow_absent_memory_args_from_specs(((1, "float", 2),))
    """

    return tuple(_AllowAbsentMemoryArg(index=index, dtype=dtype, rank=rank) for index, dtype, rank in specs)


def _compiled_kernel_from_builtin_artifacts(
    request: CompileRequest,
    artifacts: BuiltinTargetSupportArtifacts,
) -> CompiledKernel:
    """把内置 target 编译 artifact 装配为公开 kernel 描述。

    功能说明:
    - 统一 `BuiltinTargetSupportArtifacts` 到 `CompiledKernel` 的字段映射。
    - 保持 target support 模块只暴露标准库字段，不承接执行期对象构造。

    使用示例:
    - kernel = _compiled_kernel_from_builtin_artifacts(request, artifacts)
    """

    return CompiledKernel(
        target=request.target,
        soname_path=artifacts.soname_path,
        function=request.function,
        entry_point=request.entry_point,
        compile_stdout=artifacts.stdout,
        compile_stderr=artifacts.stderr,
        allow_absent_memory_args=_allow_absent_memory_args_from_specs(artifacts.allow_absent_memory_arg_specs),
        _cleanup=artifacts.cleanup,
    )


def _compile_with_builtin_strategy(request: CompileRequest) -> CompiledKernel:
    """执行内置 CPU/npu_demo 编译策略。


    功能说明:
    - 委托 `target_support.py` 生成 include、shim、编译命令与产物。
    - 在本文件内把 artifact 转换为 `CompiledKernel`，保持公开入口和运行期私有结构不外泄。

    使用示例:
    - kernel = _compile_with_builtin_strategy(request)
    """

    artifacts = build_builtin_target_support_artifacts(request)
    return _compiled_kernel_from_builtin_artifacts(request, artifacts)


class _BuiltinCompileStrategy:
    """内置 CPU/npu_demo 编译策略。"""

    def compile(self, request: CompileRequest) -> CompiledKernel:
        """编译内置 target source。


        功能说明:
        - 委托 `_compile_with_builtin_strategy(...)` 保持原 CPU/npu_demo 行为。
        - 本类只作为 registry 中的 strategy 实例使用。

        使用示例:
        - kernel = _BuiltinCompileStrategy().compile(request)
        """

        return _compile_with_builtin_strategy(request)


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


        功能说明:
        - S2 阶段固定编译路径拼装：target include 选择 -> entry shim -> 编译命令生成 -> CompiledKernel。
        - `target=cpu` 保持 dry-run；`target=npu_demo` 走真实编译，支持下游合同验收的真实执行。
        - 编译失败时会先回收内部临时工作区，再抛出 `compile_failed`。
        - 当 `request` 显式提供时，`source` 与 `function` 必须同时为 `None`；否则按公开输入冲突失败。
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
        - test: test/execute_engine/test_compile.py
        - 功能实现: kernel_gen/execute_engine/compiler.py
        """

        if request is not None:
            if source is not None or function is not None:
                raise _execution_engine_error(_SOURCE_EMPTY_OR_INVALID, "request cannot be combined with source or function")
            target = request.target
            compile_request = request
        else:
            target = self.target
            compile_request = CompileRequest(
                source=source,
                target=target,
                function=function,
                entry_point=entry_point,
                compiler=self.compiler,
                compiler_flags=self.compiler_flags,
                link_flags=self.link_flags,
            )
        strategy = get_compile_strategy(target)
        return strategy.compile(compile_request)


__all__ = [
    "CompileStrategy",
    "CompiledKernel",
    "CompileRequest",
    "ExecuteRequest",
    "ExecuteResult",
    "ExecutionEngine",
    "get_compile_strategy",
    "register_compile_strategy",
]


register_compile_strategy("cpu", _BuiltinCompileStrategy(), override=True)
register_compile_strategy("npu_demo", _BuiltinCompileStrategy(), override=True)
