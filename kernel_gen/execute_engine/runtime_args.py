"""execute_engine runtime argument ABI support.


功能说明:
- 承接 `CompiledKernel.execute(...)` 的运行时参数封装、ABI slot 构造、动态库 entry 调用和受限文本输出捕获调用。
- 仅供 `compiler.py` 通过文件级 API 调用，不进入 `kernel_gen.execute_engine` 包根公开 API。
- 使用 execute_engine 已定义 failure phrase，保持 runtime 参数错误和 symbol 解析错误语义不变。

API 列表:
- `class RuntimeScalarArgInfo(kind: Literal["int", "float"], value: int | float)`
- `class RuntimeMemoryArgInfo(kind: Literal["memory"], dtype: NumericType, shape: tuple[int, ...], stride: tuple[int, ...] | None, is_contiguous: bool)`
- `RuntimeArgInfo: TypeAlias = RuntimeScalarArgInfo | RuntimeMemoryArgInfo`
- `describe_runtime_arg(value: object) -> RuntimeArgInfo | None`
- `class AllowAbsentMemoryArg(index: int, dtype: str, rank: int)`
- `RuntimeInput: TypeAlias`
- `invoke_compiled_kernel(soname_path: str, entry_point: str, args: tuple[RuntimeInput, ...], allow_absent_memory_args: tuple[AllowAbsentMemoryArg, ...]) -> int`
- `invoke_compiled_kernel_capture_output(soname_path: str, entry_point: str, args: tuple[RuntimeInput, ...], allow_absent_memory_args: tuple[AllowAbsentMemoryArg, ...], output_capacity: int = 4096) -> tuple[int, str]`

helper 清单:
- 本文件内部 helper 不进入 `__all__`，只服务 `invoke_compiled_kernel(...)` 与 `invoke_compiled_kernel_capture_output(...)` 的 ABI 封送。

使用示例:
- from kernel_gen.execute_engine.runtime_args import describe_runtime_arg, invoke_compiled_kernel, invoke_compiled_kernel_capture_output
- info = describe_runtime_arg(1.5)
- status = invoke_compiled_kernel("libkernel.so", "kg_execute_entry", (1, 2.0), ())
- status, text = invoke_compiled_kernel_capture_output("libkernel.so", "kg_execute_entry", (), ())

关联文件:
- spec: spec/execute_engine/execute_engine_api.md
- spec: spec/execute_engine/execute_engine_target.md
- test: test/execute_engine/test_invoke.py
- 功能实现: kernel_gen/execute_engine/compiler.py
"""

from __future__ import annotations

from collections.abc import Iterable
import ctypes
from dataclasses import dataclass
from functools import partial
from numbers import Integral, Real
from pathlib import Path
from typing import Callable, Literal, Protocol, TypeAlias

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.symbol_variable.type import NumericType


_RUNTIME_THROW_OR_ABORT = "runtime_throw_or_abort"
_SYMBOL_RESOLVE_FAILED = "symbol_resolve_failed"
_RUNTIME_KNOWN_ERROR_PHRASES: frozenset[str] = frozenset(
    {
        _RUNTIME_THROW_OR_ABORT,
        _SYMBOL_RESOLVE_FAILED,
    }
)
_RUNTIME_NUMERIC_TYPE_BY_DTYPE: dict[str, NumericType] = {
    "int8": NumericType.Int8,
    "i8": NumericType.Int8,
    "int16": NumericType.Int16,
    "i16": NumericType.Int16,
    "int": NumericType.Int32,
    "int32": NumericType.Int32,
    "int32_t": NumericType.Int32,
    "i32": NumericType.Int32,
    "longlong": NumericType.Int64,
    "longlongint": NumericType.Int64,
    "int64": NumericType.Int64,
    "int64_t": NumericType.Int64,
    "i64": NumericType.Int64,
    "uint8": NumericType.Uint8,
    "ui8": NumericType.Uint8,
    "uint16": NumericType.Uint16,
    "ui16": NumericType.Uint16,
    "uint32": NumericType.Uint32,
    "uint32_t": NumericType.Uint32,
    "ui32": NumericType.Uint32,
    "uint64": NumericType.Uint64,
    "uint64_t": NumericType.Uint64,
    "ui64": NumericType.Uint64,
    "float16": NumericType.Float16,
    "f16": NumericType.Float16,
    "half": NumericType.Float16,
    "bfloat16": NumericType.BFloat16,
    "bf16": NumericType.BFloat16,
    "float": NumericType.Float32,
    "float32": NumericType.Float32,
    "f32": NumericType.Float32,
    "double": NumericType.Float64,
    "float64": NumericType.Float64,
    "f64": NumericType.Float64,
    "bool": NumericType.Bool,
}
_RUNTIME_DTYPE_CODE_BY_DTYPE: dict[str, int] = {
    "float": 1,
    "float32": 1,
    "f32": 1,
    "double": 2,
    "float64": 2,
    "f64": 2,
    "int": 3,
    "int32": 3,
    "int32_t": 3,
    "i32": 3,
    "longlong": 4,
    "longlongint": 4,
    "int64": 4,
    "int64_t": 4,
    "i64": 4,
}


class _StringValue(Protocol):
    """可稳定转为字符串的运行期值。"""

    def __str__(self) -> str:
        """返回字符串表示。"""


class _MemoryRuntimeInput(Protocol):
    """执行引擎支持的最小 memory runtime 参数协议。"""

    shape: Iterable[int]
    dtype: _StringValue


RuntimeInput: TypeAlias = _MemoryRuntimeInput | Integral | Real | None
_RuntimeInputValue: TypeAlias = RuntimeInput | _StringValue | None


class _LoadedEntrySymbol(Protocol):
    """ctypes 动态库入口 symbol 的最小调用协议。"""

    argtypes: list[type]
    restype: type[ctypes.c_int]

    def __call__(self, slots: ctypes.Array, count: ctypes.c_ulonglong) -> int:
        """调用 C ABI entry symbol。"""


@dataclass(frozen=True)
class RuntimeScalarArgInfo:
    """runtime scalar 参数描述。

    功能说明:
    - 描述 Python / numpy integer 或 floating scalar 的基础分类结果。
    - `value` 已规整为 Python `int` 或 `float`，可直接进入 DSL binding 与 ABI slot。

    使用示例:
    - info = RuntimeScalarArgInfo(kind="int", value=4)
    """

    kind: Literal["int", "float"]
    value: int | float


@dataclass(frozen=True)
class RuntimeMemoryArgInfo:
    """runtime memory 参数描述。

    功能说明:
    - 描述 torch / numpy memory 参数的 dtype、shape、元素 stride 与连续性事实。
    - `dtype` 使用公开 `NumericType`，不把字符串 dtype 作为公开真源。

    使用示例:
    - info = RuntimeMemoryArgInfo(kind="memory", dtype=NumericType.Float32, shape=(2, 2), stride=(2, 1), is_contiguous=True)
    """

    kind: Literal["memory"]
    dtype: NumericType
    shape: tuple[int, ...]
    stride: tuple[int, ...] | None
    is_contiguous: bool


RuntimeArgInfo: TypeAlias = RuntimeScalarArgInfo | RuntimeMemoryArgInfo


@dataclass(frozen=True)
class AllowAbsentMemoryArg:
    """allow-absent memory runtime 参数元数据。

    功能说明:
    - 承载生成源码注释中的 runtime 参数索引、nominal dtype 与 nominal rank。
    - 只服务 `CompiledKernel.execute(...)` 的 ABI 封送逻辑。

    使用示例:
    - metadata = AllowAbsentMemoryArg(index=3, dtype="float", rank=1)
    """

    index: int
    dtype: str
    rank: int


@dataclass(frozen=True)
class _ArgSlot:
    """entry shim 绑定槽位。

    功能说明:
    - 承载 entry shim 的按位参数信息，用于在 Python 侧完成顺序绑定校验。
    - 仅用于参数绑定与校验，不承担执行结果与内存拷贝。

    使用示例:
    - slot = _ArgSlot(position=0, kind="memory", dtype="float32", dtype_code=1, shape=(2, 2), stride=None, value=None)
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


class _RuntimeArgSupport:
    """当前文件内部实现容器，不进入文件级 API 或包根 `__all__`。"""

    @staticmethod
    def runtime_args_error(failure_phrase: str, detail: str = "") -> KernelCodeError:
        """构造运行时参数路径的 execute_engine 错误对象。

        功能说明:
        - 使用 execute_engine 已公开 failure phrase，避免 runtime_args 自造同义错误文本。
        - 在错误对象上写入 `failure_phrase`，保持 `CompiledKernel.execute(...)` 的观测行为。

        使用示例:
        - err = _RuntimeArgSupport.runtime_args_error("runtime_throw_or_abort", "args must be a tuple")
        """

        if failure_phrase not in _RUNTIME_KNOWN_ERROR_PHRASES:
            raise KernelCodeError(
                ErrorKind.CONTRACT,
                ErrorModule.EXECUTE_ENGINE,
                f"unknown failure phrase: {failure_phrase}",
            )
        message = failure_phrase if not detail else f"{failure_phrase}: {detail}"
        error = KernelCodeError(ErrorKind.CONTRACT, ErrorModule.EXECUTE_ENGINE, message)
        error.failure_phrase = failure_phrase
        return error


    @staticmethod
    def allow_absent_memory_arg_map(metadata: tuple[AllowAbsentMemoryArg, ...]) -> dict[int, AllowAbsentMemoryArg]:
        """把 allow-absent metadata 转成按 runtime index 查询的字典。

        功能说明:
        - 统一 ABI 封送路径对 allow-absent memory 参数的查询口径。
        - 后出现的同 index 元数据覆盖前值，匹配编译阶段排序后的唯一化结果。

        使用示例:
        - metadata_map = _RuntimeArgSupport.allow_absent_memory_arg_map((AllowAbsentMemoryArg(0, "float", 1),))
        """

        return {item.index: item for item in metadata}


    @staticmethod
    def dtype_code_from_name(dtype: str | None) -> int:
        """把运行时 dtype 文本映射为 C ABI dtype code。

        功能说明:
        - 为 template shim 分支选择提供最小 dtype 编码。
        - 未识别 dtype 返回 0，C shim 会拒绝需要 template 实例化的调用。

        使用示例:
        - code = _RuntimeArgSupport.dtype_code_from_name("float32")
        """

        if dtype is None:
            return 0
        normalized = dtype.strip().lower()
        if normalized.startswith("torch."):
            normalized = normalized.split(".", 1)[1]
        normalized = normalized.replace(" ", "")
        return _RUNTIME_DTYPE_CODE_BY_DTYPE.get(normalized, 0)


    @staticmethod
    def normalize_dtype(value: _StringValue | None) -> str | None:
        """规范化 dtype 表达。

        功能说明:
        - 统一 dtype 的字符串格式，支持 str、numpy/torch 的 dtype 对象。
        - 仅做最小规范化（去除 torch. 前缀），不做类型映射。

        使用示例:
        - assert _RuntimeArgSupport.normalize_dtype("float32") == "float32"
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


    @staticmethod
    def normalize_shape(value: _MemoryRuntimeInput | None) -> tuple[int, ...] | None:
        """规范化 shape 表达。

        功能说明:
        - 统一 shape 为 tuple[int, ...]，用于运行时参数的 memory 校验。
        - shape 不可解析时返回 None，由调用路径转成公开 runtime failure。

        使用示例:
        - assert _RuntimeArgSupport.normalize_shape(type("T", (), {"shape": (2, 3)})()) == (2, 3)
        """

        if value is None or not hasattr(value, "shape"):
            return None
        try:
            return tuple(int(dim) for dim in getattr(value, "shape"))
        except (TypeError, ValueError):
            return None


    @staticmethod
    def runtime_module_name(value: _RuntimeInputValue) -> str:
        """提取运行时参数的模块前缀。

        功能说明:
        - 为 torch/numpy 类型识别提供最小、无需导入依赖的判断依据。
        - 返回空字符串表示无法识别模块信息。

        使用示例:
        - assert _RuntimeArgSupport.runtime_module_name(type("T", (), {"__module__": "torch"})()) == "torch"
        """

        module_name = getattr(value.__class__, "__module__", "")
        return module_name or ""


    @staticmethod
    def is_torch_tensor(value: _RuntimeInputValue) -> bool:
        """判断是否为 torch 张量类 RuntimeInput。

        功能说明:
        - 基于 __module__ 前缀做轻量识别，避免直接导入 torch 依赖。
        - 仅用于运行时参数类型判定，不做数据合法性校验。

        使用示例:
        - assert _RuntimeArgSupport.is_torch_tensor(type("T", (), {"__module__": "torch"})()) is True
        """

        return _RuntimeArgSupport.runtime_module_name(value).startswith("torch")


    @staticmethod
    def is_numpy_array(value: _RuntimeInputValue) -> bool:
        """判断是否为 numpy 数组类 RuntimeInput。

        功能说明:
        - 基于 __module__ 前缀做轻量识别，避免直接导入 numpy 依赖。
        - 仅用于运行时参数类型判定，不做数据合法性校验。

        使用示例:
        - assert _RuntimeArgSupport.is_numpy_array(type("T", (), {"__module__": "numpy"})()) is True
        """

        return _RuntimeArgSupport.runtime_module_name(value).startswith("numpy")


    @staticmethod
    def normalize_stride(value: _MemoryRuntimeInput | None) -> tuple[int, ...] | None:
        """规范化 stride 表达。

        功能说明:
        - 统一 stride 为 tuple[int, ...]，用于运行时参数的 memory 校验与记录。
        - numpy byte stride 会按 itemsize 转成元素 stride，无法解析时返回 None。

        使用示例:
        - assert _RuntimeArgSupport.normalize_stride(type("T", (), {"stride": lambda self: (1, 2)})()) == (1, 2)
        """

        if value is None:
            return None
        if hasattr(value, "stride"):
            stride_attr = getattr(value, "stride")
            stride = stride_attr() if callable(stride_attr) else stride_attr
            try:
                return tuple(int(dim) for dim in stride)
            except (TypeError, ValueError):
                return None
        if hasattr(value, "strides"):
            stride = getattr(value, "strides")
            try:
                stride_tuple = tuple(int(dim) for dim in stride)
            except (TypeError, ValueError):
                return None
            if _RuntimeArgSupport.is_numpy_array(value):
                itemsize = getattr(value, "itemsize", None)
                if not isinstance(itemsize, int) or itemsize <= 0:
                    return None
                if any(dim % itemsize != 0 for dim in stride_tuple):
                    return None
                return tuple(int(dim // itemsize) for dim in stride_tuple)
            return stride_tuple
        return None


    @staticmethod
    def is_memory_runtime_arg(value: _RuntimeInputValue) -> bool:
        """判断是否为 memory 运行时参数（torch/numpy）。

        功能说明:
        - 仅当对象符合 torch/numpy 模块前缀且包含 shape/dtype 字段时视为 memory 参数。
        - 不对 shape/dtype 的合法性做复杂推断，留给后续校验逻辑处理。

        使用示例:
        - value = type("T", (), {"__module__": "torch", "shape": (1,), "dtype": "float32"})()
        - assert _RuntimeArgSupport.is_memory_runtime_arg(value) is True
        """

        if not (_RuntimeArgSupport.is_torch_tensor(value) or _RuntimeArgSupport.is_numpy_array(value)):
            return False
        return hasattr(value, "shape") and hasattr(value, "dtype")


    @staticmethod
    def is_contiguous_memory(value: _MemoryRuntimeInput) -> bool:
        """判断 memory 运行时参数是否为连续布局。

        功能说明:
        - torch 路径优先使用 is_contiguous() 结果。
        - numpy 路径优先读取 flags["C_CONTIGUOUS"] 或 flags.c_contiguous。
        - 缺少相关信息时默认视为连续布局。

        使用示例:
        - value = type("T", (), {"__module__": "torch", "shape": (1,), "dtype": "float32", "is_contiguous": lambda self: True})()
        - assert _RuntimeArgSupport.is_contiguous_memory(value) is True
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


    @staticmethod
    def build_arg_slots(
        args: tuple[RuntimeInput, ...],
        allow_absent_memory_args: tuple[AllowAbsentMemoryArg, ...] = (),
    ) -> tuple[_ArgSlot, ...]:
        """按顺序构建 entry shim 参数槽位。

        功能说明:
        - 校验 RuntimeInput 的类型与最小 memory 约束（shape/dtype/连续性）。
        - 仅当源码 metadata 声明对应索引为 allow-absent memory 时接受 `None`。
        - 失败时抛出 runtime_throw_or_abort，保证失败短语稳定。

        使用示例:
        - slots = _RuntimeArgSupport.build_arg_slots((1, 2.0))
        """

        slots: list[_ArgSlot] = []
        allow_absent_map = _RuntimeArgSupport.allow_absent_memory_arg_map(allow_absent_memory_args)
        for idx, arg in enumerate(args):
            if arg is None:
                metadata = allow_absent_map.get(idx)
                if metadata is None:
                    raise _RuntimeArgSupport.runtime_args_error(
                        _RUNTIME_THROW_OR_ABORT,
                        f"None runtime arg requires allow-absent memory metadata at position {idx}",
                    )
                slots.append(
                    _ArgSlot(
                        position=idx,
                        kind="memory",
                        dtype=metadata.dtype,
                        dtype_code=_RuntimeArgSupport.dtype_code_from_name(metadata.dtype),
                        shape=(0,),
                        stride=(1,),
                        value=None,
                    )
                )
                continue
            info = describe_runtime_arg(arg)
            if isinstance(info, RuntimeScalarArgInfo):
                slots.append(
                    _ArgSlot(
                        position=idx,
                        kind=info.kind,
                        dtype=info.kind,
                        dtype_code=0,
                        shape=None,
                        stride=None,
                        value=info.value,
                    )
                )
                continue
            if isinstance(info, RuntimeMemoryArgInfo):
                if not info.is_contiguous:
                    raise _RuntimeArgSupport.runtime_args_error(_RUNTIME_THROW_OR_ABORT, f"memory arg is not contiguous at position {idx}")
                slots.append(
                    _ArgSlot(
                        position=idx,
                        kind="memory",
                        dtype=info.dtype.value,
                        dtype_code=_RuntimeArgSupport.dtype_code_from_name(info.dtype.value),
                        shape=info.shape,
                        stride=info.stride,
                        value=arg,
                    )
                )
                continue
            raise _RuntimeArgSupport.runtime_args_error(_RUNTIME_THROW_OR_ABORT, f"unsupported runtime arg at position {idx}")
        return tuple(slots)


    @staticmethod
    def contiguous_stride(shape: tuple[int, ...]) -> tuple[int, ...]:
        """按 shape 生成连续布局 stride（元素步长）。

        功能说明:
        - 当运行时参数未显式提供 stride 时，生成行主序连续 stride。
        - 用于 memory 参数 ABI 封送前的兜底补全。

        使用示例:
        - _RuntimeArgSupport.contiguous_stride((2, 3)) == (3, 1)
        """

        if not shape:
            return ()
        stride = [1 for _ in shape]
        for idx in range(len(shape) - 2, -1, -1):
            stride[idx] = stride[idx + 1] * int(shape[idx + 1])
        return tuple(stride)


    @staticmethod
    def runtime_data_pointer(value: _MemoryRuntimeInput) -> int:
        """读取运行时参数底层数据指针地址。

        功能说明:
        - 对 `torch.Tensor` 使用 `data_ptr()`，对 `numpy.ndarray` 使用 `ctypes.data`。
        - 不支持的对象触发 `runtime_throw_or_abort`。

        使用示例:
        - pointer = _RuntimeArgSupport.runtime_data_pointer(torch.zeros((2,), dtype=torch.int32))
        """

        if _RuntimeArgSupport.is_torch_tensor(value) and hasattr(value, "data_ptr"):
            data_ptr = value.data_ptr()
            return int(data_ptr)
        if _RuntimeArgSupport.is_numpy_array(value) and hasattr(value, "ctypes"):
            return int(value.ctypes.data)
        raise _RuntimeArgSupport.runtime_args_error(_RUNTIME_THROW_OR_ABORT, "memory arg data pointer is unavailable")


    @staticmethod
    def marshal_slots_for_abi(
        ordered_slots: tuple[_ArgSlot, ...],
    ) -> tuple[ctypes.Array, type[ctypes.Structure], tuple[ctypes.Array, ...]]:
        """把 Python `ArgSlot` 转为 C ABI 可调用结构。

        功能说明:
        - 将 memory/int/float 三类运行参数封送为 C 结构数组。
        - 返回 keepalive 对象集合，保证 shape/stride 缓冲区在调用期间有效。

        使用示例:
        - _RuntimeArgSupport.marshal_slots_for_abi(_RuntimeArgSupport.build_arg_slots((1, 2.0)))
        """

        c_slots: list[_CArgSlot] = []
        keepalive: list[ctypes.Array] = []
        for slot in ordered_slots:
            if slot.kind == "memory":
                if slot.shape is None:
                    raise _RuntimeArgSupport.runtime_args_error(_RUNTIME_THROW_OR_ABORT, f"memory shape missing at position {slot.position}")
                stride = slot.stride if slot.stride is not None else _RuntimeArgSupport.contiguous_stride(slot.shape)
                if len(stride) != len(slot.shape):
                    raise _RuntimeArgSupport.runtime_args_error(_RUNTIME_THROW_OR_ABORT, f"memory stride rank mismatch at position {slot.position}")
                shape_buffer_type = ctypes.c_longlong * len(slot.shape)
                stride_buffer_type = ctypes.c_longlong * len(stride)
                shape_buffer = shape_buffer_type(*slot.shape)
                stride_buffer = stride_buffer_type(*stride)
                keepalive.extend([shape_buffer, stride_buffer])
                data_pointer = 0 if slot.value is None else _RuntimeArgSupport.runtime_data_pointer(slot.value)
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
            raise _RuntimeArgSupport.runtime_args_error(_RUNTIME_THROW_OR_ABORT, f"unsupported slot kind at position {slot.position}")
        slot_array_type = _CArgSlot * len(c_slots)
        slot_array = slot_array_type(*c_slots)
        keepalive.append(slot_array)
        return (slot_array, _CArgSlot, tuple(keepalive))


    @staticmethod
    def invoke_placeholder_entry(_slots: tuple[_ArgSlot, ...]) -> int:
        """执行 dry-run 空产物占位入口。

        功能说明:
        - 保持空 `.so` 产物的历史成功行为。
        - 只由 `_RuntimeArgSupport.load_entry_point(...)` 在检测到空产物时返回。

        使用示例:
        - _RuntimeArgSupport.invoke_placeholder_entry(())
        """

        return 0


    @staticmethod
    def invoke_loaded_entry_symbol(
        ordered_slots: tuple[_ArgSlot, ...],
        *,
        symbol: _LoadedEntrySymbol,
    ) -> int:
        """调用已解析出的 C ABI entry symbol。

        功能说明:
        - 将 Python 参数槽位封送为 C ABI 数组。
        - 调用 `ctypes` symbol 并返回整数状态码。

        使用示例:
        - invoke = partial(_RuntimeArgSupport.invoke_loaded_entry_symbol, symbol=symbol)
        - invoke(())
        """

        slot_array, slot_struct, keepalive = _RuntimeArgSupport.marshal_slots_for_abi(ordered_slots)
        symbol.argtypes = [ctypes.POINTER(slot_struct), ctypes.c_ulonglong]
        symbol.restype = ctypes.c_int
        result = int(symbol(slot_array, ctypes.c_ulonglong(len(ordered_slots))))
        _ = keepalive
        return result


    @staticmethod
    def load_entry_point(soname_path: str, entry_point: str) -> Callable[[tuple[_ArgSlot, ...]], int]:
        """加载 entry point 并返回可调用对象。

        功能说明:
        - 对真实 `.so` 执行动态加载，并把 Python 槽位转换为 C ABI 参数后调用入口。
        - 对 dry-run 生成的空产物或空白占位产物，保留历史占位成功行为，避免破坏骨架测试。

        使用示例:
        - invoke = _RuntimeArgSupport.load_entry_point("libkernel.so", "kg_execute_entry")
        - assert invoke(()) == 0
        """

        if not isinstance(soname_path, str) or not soname_path:
            raise _RuntimeArgSupport.runtime_args_error(_RUNTIME_THROW_OR_ABORT, "soname_path is empty")
        soname = Path(soname_path)
        if not soname.is_file():
            raise _RuntimeArgSupport.runtime_args_error(_RUNTIME_THROW_OR_ABORT, "soname_path is missing")
        if soname.stat().st_size == 0:
            return _RuntimeArgSupport.invoke_placeholder_entry
        if soname.stat().st_size <= 8:
            try:
                if not soname.read_bytes().strip():
                    return _RuntimeArgSupport.invoke_placeholder_entry
            except OSError:
                pass

        try:
            library = ctypes.CDLL(str(soname))
        except OSError as exc:
            raise _RuntimeArgSupport.runtime_args_error(_SYMBOL_RESOLVE_FAILED, f"unable to load shared object: {exc}") from exc
        try:
            symbol = getattr(library, entry_point)
        except AttributeError as exc:
            raise _RuntimeArgSupport.runtime_args_error(_SYMBOL_RESOLVE_FAILED, f"entry_point '{entry_point}' is missing") from exc
        return partial(_RuntimeArgSupport.invoke_loaded_entry_symbol, symbol=symbol)


def describe_runtime_arg(value: object) -> RuntimeArgInfo | None:
    """描述单个真实 runtime 参数的基础分类结果。

    功能说明:
    - 将 Python / numpy integer scalar 规整为 Python `int`，floating scalar 规整为 Python `float`。
    - 将 torch / numpy memory 参数描述为 `RuntimeMemoryArgInfo`，dtype 使用公开 `NumericType`。
    - 对 `None`、bool / numpy bool scalar、unsupported dtype 或非法 memory metadata 返回 `None`。

    使用示例:
    - info = describe_runtime_arg(4)
    - assert info == RuntimeScalarArgInfo(kind="int", value=4)
    """

    dtype_value = getattr(value, "dtype", None)
    dtype_text = getattr(dtype_value, "name", None)
    if not isinstance(dtype_text, str) or not dtype_text:
        dtype_text = _RuntimeArgSupport.normalize_dtype(dtype_value)
    if dtype_text is not None:
        normalized_dtype = dtype_text.strip().lower()
        if normalized_dtype.startswith("torch."):
            normalized_dtype = normalized_dtype.split(".", 1)[1]
        normalized_dtype = normalized_dtype.replace(" ", "")
    else:
        normalized_dtype = ""
    module_name = _RuntimeArgSupport.runtime_module_name(value)
    class_name = getattr(value.__class__, "__name__", "")
    is_numpy_bool_scalar = module_name.startswith("numpy") and class_name in {"bool", "bool_"}
    if value is None or isinstance(value, bool) or is_numpy_bool_scalar:
        return None
    if isinstance(value, Integral):
        return RuntimeScalarArgInfo(kind="int", value=int(value))
    if isinstance(value, Real) and (isinstance(value, float) or module_name.startswith("numpy")):
        return RuntimeScalarArgInfo(kind="float", value=float(value))
    if not _RuntimeArgSupport.is_memory_runtime_arg(value):
        return None
    dtype = _RUNTIME_NUMERIC_TYPE_BY_DTYPE.get(normalized_dtype)
    shape = _RuntimeArgSupport.normalize_shape(value)
    if dtype is None or shape is None:
        return None
    return RuntimeMemoryArgInfo(
        kind="memory",
        dtype=dtype,
        shape=shape,
        stride=_RuntimeArgSupport.normalize_stride(value),
        is_contiguous=_RuntimeArgSupport.is_contiguous_memory(value),
    )


def invoke_compiled_kernel(
    soname_path: str,
    entry_point: str,
    args: tuple[RuntimeInput, ...],
    allow_absent_memory_args: tuple[AllowAbsentMemoryArg, ...],
) -> int:
    """按 execute_engine C ABI 调用已编译 kernel。

    功能说明:
    - 统一执行运行时参数封送、动态库加载、entry symbol 解析和入口调用。
    - 返回原始 entry status code；非零 status 的公开失败映射由 `CompiledKernel.execute(...)` 完成。

    使用示例:
    - status = invoke_compiled_kernel("libkernel.so", "kg_execute_entry", (), ())
    """

    ordered_slots = _RuntimeArgSupport.build_arg_slots(args, allow_absent_memory_args)
    invoke_entry = _RuntimeArgSupport.load_entry_point(soname_path, entry_point)
    return invoke_entry(ordered_slots)


def invoke_compiled_kernel_capture_output(
    soname_path: str,
    entry_point: str,
    args: tuple[RuntimeInput, ...],
    allow_absent_memory_args: tuple[AllowAbsentMemoryArg, ...],
    output_capacity: int = 4096,
) -> tuple[int, str]:
    """按 execute_engine C ABI 调用已编译 kernel 的输出捕获 companion。

    功能说明:
    - 复用普通执行入口的运行时参数封送。
    - companion symbol 固定为 `<entry_point>_capture`，返回原始 status 与 UTF-8 文本。
    - 输出容量非法、溢出或非 UTF-8 时按 `runtime_throw_or_abort` 失败。

    使用示例:
    - status, text = invoke_compiled_kernel_capture_output("libkernel.so", "kg_execute_entry", (), ())
    """

    if not isinstance(output_capacity, int) or output_capacity <= 0:
        raise _RuntimeArgSupport.runtime_args_error(_RUNTIME_THROW_OR_ABORT, "output_capacity must be positive")
    ordered_slots = _RuntimeArgSupport.build_arg_slots(args, allow_absent_memory_args)
    if not isinstance(soname_path, str) or not soname_path:
        raise _RuntimeArgSupport.runtime_args_error(_RUNTIME_THROW_OR_ABORT, "soname_path is empty")
    soname = Path(soname_path)
    companion_entry_point = f"{entry_point}_capture"
    if not soname.is_file():
        raise _RuntimeArgSupport.runtime_args_error(_RUNTIME_THROW_OR_ABORT, "soname_path is missing")
    if soname.stat().st_size == 0:
        raise _RuntimeArgSupport.runtime_args_error(_SYMBOL_RESOLVE_FAILED, f"entry_point '{companion_entry_point}' is missing")
    if soname.stat().st_size <= 8:
        try:
            if not soname.read_bytes().strip():
                raise _RuntimeArgSupport.runtime_args_error(_SYMBOL_RESOLVE_FAILED, f"entry_point '{companion_entry_point}' is missing")
        except OSError:
            pass
    try:
        library = ctypes.CDLL(str(soname))
    except OSError as exc:
        raise _RuntimeArgSupport.runtime_args_error(_SYMBOL_RESOLVE_FAILED, f"unable to load shared object: {exc}") from exc
    try:
        symbol = getattr(library, companion_entry_point)
    except AttributeError as exc:
        raise _RuntimeArgSupport.runtime_args_error(_SYMBOL_RESOLVE_FAILED, f"entry_point '{companion_entry_point}' is missing") from exc

    slot_array, slot_struct, keepalive = _RuntimeArgSupport.marshal_slots_for_abi(ordered_slots)
    output_buffer = ctypes.create_string_buffer(output_capacity)
    output_size = ctypes.c_ulonglong(0)
    symbol.argtypes = [
        ctypes.POINTER(slot_struct),
        ctypes.c_ulonglong,
        ctypes.POINTER(ctypes.c_char),
        ctypes.c_ulonglong,
        ctypes.POINTER(ctypes.c_ulonglong),
    ]
    symbol.restype = ctypes.c_int
    result = int(
        symbol(
            slot_array,
            ctypes.c_ulonglong(len(ordered_slots)),
            output_buffer,
            ctypes.c_ulonglong(output_capacity),
            ctypes.byref(output_size),
        )
    )
    _ = keepalive
    if result != 0:
        return result, ""
    text_size = int(output_size.value)
    if text_size >= output_capacity:
        raise _RuntimeArgSupport.runtime_args_error(_RUNTIME_THROW_OR_ABORT, "capture output is invalid")
    try:
        text = bytes(output_buffer.raw[:text_size]).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise _RuntimeArgSupport.runtime_args_error(_RUNTIME_THROW_OR_ABORT, "capture output is invalid") from exc
    return result, text


__all__ = [
    "RuntimeScalarArgInfo",
    "RuntimeMemoryArgInfo",
    "RuntimeArgInfo",
    "describe_runtime_arg",
    "AllowAbsentMemoryArg",
    "RuntimeInput",
    "invoke_compiled_kernel",
    "invoke_compiled_kernel_capture_output",
]
