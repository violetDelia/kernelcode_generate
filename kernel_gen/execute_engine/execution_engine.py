"""ExecutionEngine skeleton (P0).

创建者: 朽木露琪亚
最后一次更改: jcc你莫辜负

功能说明:
- 提供 `ExecutionEngine.compile(...).execute(...)` 的最小壳层，以便在不实现真实编译/调用的前提下固定：
  - 公开 API 的命名与字段形态；
  - 7 个公共失败短语（failure_phrase）的固定集合；
  - `stream` 与 `capture_function_output` 在 P0 的禁用行为；
  - 直接使用 RuntimeArg（torch/numpy/int/float）输入的调用路径。

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

from dataclasses import dataclass
from pathlib import Path
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
        raise ExecutionEngineError(
            FAILURE_COMPILE_FAILED,
            "compiler is empty",
        )
    return compiler


class ExecutionEngineError(RuntimeError):
    """对外可机械匹配的执行引擎错误。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 用固定 `failure_phrase` 承载失败原因，确保测试稳定匹配。

    使用示例:
    - raise ExecutionEngineError(FAILURE_SOURCE_EMPTY_OR_INVALID, "source is empty")

    关联文件:
    - spec: spec/execute_engine/execute_engine.md
    - test: test/execute_engine/test_execute_engine_contract.py
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    """

    def __init__(self, failure_phrase: str, detail: str = "") -> None:
        if failure_phrase not in FAILURE_PHRASES:
            raise ValueError(f"unknown failure_phrase: {failure_phrase}")
        super().__init__(f"{failure_phrase}: {detail}" if detail else failure_phrase)
        self.failure_phrase = failure_phrase


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
            return tuple(int(dim) for dim in stride)
        except TypeError:
            return None
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
                raise ExecutionEngineError(
                    FAILURE_RUNTIME_THROW_OR_ABORT,
                    f"memory arg is not contiguous at position {idx}",
                )
            dtype = _normalize_dtype(getattr(arg, "dtype", None))
            shape = _normalize_shape(arg)
            if dtype is None or shape is None:
                raise ExecutionEngineError(
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
        raise ExecutionEngineError(
            FAILURE_RUNTIME_THROW_OR_ABORT,
            f"unsupported RuntimeArg at position {idx}",
        )
    return tuple(slots)


def _load_entry_point(soname_path: str, entry_point: str) -> Callable[[tuple[KgArgSlot, ...]], int]:
    """加载 entry point 并返回可调用对象（P0/S3 占位）。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 以 soname_path + entry_point 的最小约束模拟动态加载。
    - 当前仅验证 soname_path 存在，返回固定成功占位函数。

    使用示例:
    - invoke = _load_entry_point("libkernel.so", "kg_execute_entry")
    - assert invoke(()) == 0

    关联文件:
    - spec: spec/execute_engine/execute_engine.md
    - test: test/execute_engine/test_execute_engine_invoke.py
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    """

    if not isinstance(soname_path, str) or not soname_path:
        raise ExecutionEngineError(
            FAILURE_RUNTIME_THROW_OR_ABORT,
            "soname_path is empty",
        )
    if not Path(soname_path).is_file():
        raise ExecutionEngineError(
            FAILURE_RUNTIME_THROW_OR_ABORT,
            "soname_path is missing",
        )

    def _invoke(_slots: tuple[KgArgSlot, ...]) -> int:
        return 0

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
    """编译产物的只读描述（P0）。"""

    target: str
    soname_path: str
    function: str
    entry_point: str
    compile_stdout: str = ""
    compile_stderr: str = ""

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
            raise ExecutionEngineError(
                FAILURE_STREAM_NOT_SUPPORTED,
                "ExecuteRequest.stream is not supported in P0",
            )
        if capture_function_output:
            raise ExecutionEngineError(
                FAILURE_FUNCTION_OUTPUT_CAPTURE_NOT_SUPPORTED,
                "ExecuteRequest.capture_function_output is not supported in P0",
            )

        if args is None:
            raise ExecutionEngineError(
                FAILURE_RUNTIME_THROW_OR_ABORT,
                "args must be provided",
            )
        if not isinstance(args, tuple):
            raise ExecutionEngineError(
                FAILURE_RUNTIME_THROW_OR_ABORT,
                "args must be a tuple",
            )
        ordered_slots = _build_arg_slots(args)

        resolved_entry = self.entry_point if entry_point is None else entry_point
        if not isinstance(resolved_entry, str) or not resolved_entry.strip():
            raise ExecutionEngineError(
                FAILURE_SYMBOL_RESOLVE_FAILED,
                "entry_point is empty",
            )
        if resolved_entry != self.entry_point:
            raise ExecutionEngineError(
                FAILURE_SYMBOL_RESOLVE_FAILED,
                "entry_point mismatch",
            )

        invoke_entry = _load_entry_point(self.soname_path, resolved_entry)
        status_code = invoke_entry(ordered_slots)
        if status_code != 0:
            raise ExecutionEngineError(
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
        - S2 默认以 dry-run 方式生成编译命令与占位产物，不执行真实编译。
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
            raise ExecutionEngineError(
                FAILURE_TARGET_HEADER_MISMATCH,
                f"unsupported target: {target}",
            )
        if source is None or not isinstance(source, str) or not source.strip():
            raise ExecutionEngineError(
                FAILURE_SOURCE_EMPTY_OR_INVALID,
                "source is empty",
            )
        include_family = _source_include_family(source)
        if include_family == "mixed":
            raise ExecutionEngineError(
                FAILURE_TARGET_HEADER_MISMATCH,
                "source includes mixed target include families",
            )
        if include_family is not None and include_family != target:
            raise ExecutionEngineError(
                FAILURE_TARGET_HEADER_MISMATCH,
                f"source include family mismatch: source={include_family}, target={target}",
            )
        if "#error" in source:
            raise ExecutionEngineError(
                FAILURE_COMPILE_FAILED,
                "source contains #error directive",
            )
        if function is None or not isinstance(function, str) or not function.strip():
            raise ExecutionEngineError(
                FAILURE_SYMBOL_RESOLVE_FAILED,
                "function is empty",
            )
        if not isinstance(entry_point, str) or not entry_point.strip():
            raise ExecutionEngineError(
                FAILURE_SYMBOL_RESOLVE_FAILED,
                "entry_point is empty",
            )

        target_headers = target_includes(target)
        if not target_headers:
            raise ExecutionEngineError(
                FAILURE_TARGET_HEADER_MISMATCH,
                f"unsupported target: {target}",
            )
        shim_source = ""
        if needs_entry_shim(source, entry_point):
            shim_source = build_entry_shim_source(
                function=function,
                entry_point=entry_point,
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
            dry_run=True,
        )
        if artifacts.return_code != 0:
            raise ExecutionEngineError(
                FAILURE_COMPILE_FAILED,
                f"compiler returned non-zero ({artifacts.return_code})",
            )
        if not Path(artifacts.soname_path).exists():
            raise ExecutionEngineError(
                FAILURE_COMPILE_FAILED,
                "compile output is missing",
            )

        return CompiledKernel(
            target=target,
            soname_path=artifacts.soname_path,
            function=function,
            entry_point=entry_point,
            compile_stdout=artifacts.stdout,
            compile_stderr=artifacts.stderr,
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
    "ExecutionEngineError",
]
