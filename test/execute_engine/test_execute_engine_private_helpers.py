"""execute_engine private helper coverage tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 execute_engine / entry_shim_builder / compiler 的私有 helper 边界与失败分支。
- 这些测试直接反推当前 diff 的实际行为，用于把 S5 execute / target scoped coverage 收口。

使用示例:
- pytest -q test/execute_engine/test_execute_engine_private_helpers.py

关联文件:
- 功能实现: kernel_gen/execute_engine/execution_engine.py
- 功能实现: kernel_gen/execute_engine/compiler.py
- 功能实现: kernel_gen/execute_engine/entry_shim_builder.py
- Spec 文档: spec/execute_engine/execute_engine.md
- Spec 文档: spec/execute_engine/execute_engine_target.md
- 测试文件: test/execute_engine/test_execute_engine_private_helpers.py
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from kernel_gen.execute_engine import (
    FAILURE_COMPILE_FAILED,
    FAILURE_RUNTIME_THROW_OR_ABORT,
    FAILURE_SYMBOL_RESOLVE_FAILED,
    FAILURE_TARGET_HEADER_MISMATCH,
    ExecutionEngine,
    ExecutionEngineError,
)
from kernel_gen.execute_engine.compiler import (
    CompileArtifacts,
    build_compile_command,
    build_compile_unit,
    compile_source,
)
from kernel_gen.execute_engine.entry_shim_builder import (
    _build_runtime_entry_shim_source,
    _extract_param_specs,
    _parse_param_spec,
    _split_params,
    build_entry_shim_source,
    needs_entry_shim,
)
from kernel_gen.execute_engine.execution_engine import (
    KgArgSlot,
    _build_arg_slots,
    _contiguous_stride,
    _inject_npu_demo_namespace_aliases,
    _is_contiguous_memory,
    _is_memory_runtime_arg,
    _is_numpy_array,
    _is_runtime_float,
    _is_runtime_int,
    _is_torch_tensor,
    _load_entry_point,
    _marshal_slots_for_abi,
    _normalize_dtype,
    _normalize_shape,
    _normalize_stride,
    _resolve_compiler_name,
    _runtime_data_pointer,
    _runtime_module_name,
    _source_include_family,
)


class _FakeTorchTensor:
    """最小 torch RuntimeArg 占位。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 提供 shape / dtype / stride / contiguous / data_ptr 的最小接口。
    - 仅用于 helper 级行为回归，不依赖真实 torch。

    使用示例:
    - value = _FakeTorchTensor(shape=(2, 2), dtype="torch.float32")

    关联文件:
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    - 测试文件: test/execute_engine/test_execute_engine_private_helpers.py
    """

    __module__ = "torch"

    def __init__(
        self,
        *,
        shape: tuple[int, ...] = (2, 2),
        dtype: str = "torch.float32",
        stride: tuple[int, ...] | None = None,
        contiguous: bool = True,
        data_ptr: int = 1234,
    ) -> None:
        self.shape = shape
        self.dtype = dtype
        self._stride = stride
        self._contiguous = contiguous
        self._data_ptr = data_ptr

    def stride(self) -> tuple[int, ...] | None:
        return self._stride

    def is_contiguous(self) -> bool:
        return self._contiguous

    def data_ptr(self) -> int:
        return self._data_ptr


class _FakeNumpyArray:
    """最小 numpy RuntimeArg 占位。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 提供 shape / dtype / strides / flags / ctypes 的最小接口。
    - 仅用于 helper 级行为回归，不依赖真实 numpy。

    使用示例:
    - value = _FakeNumpyArray(shape=(2, 2), dtype="float32")

    关联文件:
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    - 测试文件: test/execute_engine/test_execute_engine_private_helpers.py
    """

    __module__ = "numpy"

    def __init__(
        self,
        *,
        shape: tuple[int, ...] = (2, 2),
        dtype: str = "float32",
        strides: tuple[int, ...] | None = None,
        itemsize: int = 4,
        contiguous: bool = True,
        data_ptr: int = 5678,
    ) -> None:
        self.shape = shape
        self.dtype = dtype
        self.strides = strides
        self.itemsize = itemsize
        self.flags = {"C_CONTIGUOUS": contiguous}
        self.ctypes = SimpleNamespace(data=data_ptr)


def _build_test_shared_library(tmp_path: Path, symbol_name: str = "kg_execute_entry") -> Path:
    """构建一个最小共享库用于 `_load_entry_point` 真实加载验证。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 通过本地 g++ 生成最小 `.so`，用于验证动态加载和符号解析路径。

    使用示例:
    - so_path = _build_test_shared_library(tmp_path)

    关联文件:
    - 功能实现: kernel_gen/execute_engine/execution_engine.py
    - 测试文件: test/execute_engine/test_execute_engine_private_helpers.py
    """

    tmp_path.mkdir(parents=True, exist_ok=True)
    source_path = tmp_path / "shim.cc"
    so_path = tmp_path / "libshim.so"
    source_path.write_text(
        f"""
        struct KgArgSlot;
        extern "C" int {symbol_name}(const KgArgSlot*, unsigned long long) {{
          return 0;
        }}
        """,
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            "g++",
            "-shared",
            "-fPIC",
            "-std=c++17",
            "-x",
            "c++",
            str(source_path),
            "-o",
            str(so_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(f"g++ shared library build failed: {result.stderr}")
    return so_path


def test_execute_engine_private_helpers_include_family_and_aliases() -> None:
    """覆盖 include family 识别与 npu_demo 命名空间别名注入。

    创建者: 金铲铲大作战
    最后更改: 金铲铲大作战

    测试目的:
    - 验证 cpu / npu_demo / mixed / none 四类 include family 和 namespace alias 注入行为。

    对应功能实现文件路径: kernel_gen/execute_engine/execution_engine.py
    对应 spec 文件路径: spec/execute_engine/execute_engine_target.md
    对应测试文件路径: test/execute_engine/test_execute_engine_private_helpers.py
    """

    assert _source_include_family('#include "include/cpu/Memory.h"\n') == "cpu"
    assert _source_include_family('#include "include/npu_demo/npu_demo.h"\n') == "npu_demo"
    assert _source_include_family(
        '#include "include/cpu/Memory.h"\n#include "include/npu_demo/npu_demo.h"\n'
    ) == "mixed"
    assert _source_include_family("int main(){}") is None

    source = '#include "include/npu_demo/npu_demo.h"\nvoid f(){ npu_demo::add(a, b, c); }'
    injected = _inject_npu_demo_namespace_aliases(source)
    assert "namespace npu_demo {" in injected
    assert "using ::add;" in injected
    assert injected.index("namespace npu_demo {") > injected.index('#include "include/npu_demo/npu_demo.h"')
    assert _inject_npu_demo_namespace_aliases("void f(){ npu_demo::add(a, b, c); }").startswith(
        "namespace npu_demo {"
    )
    assert _inject_npu_demo_namespace_aliases("void f(){ add(a, b, c); }") == "void f(){ add(a, b, c); }"


def test_execute_engine_private_helpers_misc_failure_and_fallback_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """覆盖执行引擎的额外失败与 fallback 分支。

    创建者: 金铲铲大作战
    最后更改: 金铲铲大作战

    测试目的:
    - 验证 compiler 名称、dtype / stride / contiguous / slot / load entry point 的额外边界分支。

    对应功能实现文件路径: kernel_gen/execute_engine/execution_engine.py
    对应 spec 文件路径: spec/execute_engine/execute_engine_api.md
    对应测试文件路径: test/execute_engine/test_execute_engine_private_helpers.py
    """

    assert _inject_npu_demo_namespace_aliases("int main(){}") == "int main(){}"

    with pytest.raises(ExecutionEngineError) as exc:
        _resolve_compiler_name("")
    assert exc.value.failure_phrase == FAILURE_COMPILE_FAILED
    with pytest.raises(ExecutionEngineError) as exc:
        _resolve_compiler_name(123)  # type: ignore[arg-type]
    assert exc.value.failure_phrase == FAILURE_COMPILE_FAILED

    with pytest.raises(ValueError):
        ExecutionEngineError("bogus")

    dtype_like = type("DTypeLike", (), {"__str__": lambda self: "torch.int16"})()
    assert _normalize_dtype(dtype_like) == "int16"
    assert _normalize_stride(None) is None
    assert _normalize_stride(SimpleNamespace(stride=(4, 2))) == (4, 2)

    failing_contiguous = type(
        "FailingContiguousTensor",
        (),
        {
            "__module__": "torch",
            "shape": (1,),
            "dtype": "float32",
            "is_contiguous": lambda self: (_ for _ in ()).throw(RuntimeError("bad")),
        },
    )()
    assert _is_contiguous_memory(failing_contiguous) is False

    with pytest.raises(ExecutionEngineError) as exc:
        _build_arg_slots((object(),))
    assert exc.value.failure_phrase == FAILURE_RUNTIME_THROW_OR_ABORT

    with pytest.raises(ExecutionEngineError) as exc:
        _marshal_slots_for_abi(
            (
                KgArgSlot(
                    position=0,
                    kind="memory",
                    dtype="float32",
                    shape=(2, 2),
                    stride=(1, 1),
                    value=_FakeTorchTensor(),
                ),
                KgArgSlot(
                    position=1,
                    kind="bogus",  # type: ignore[arg-type]
                    dtype=None,
                    shape=None,
                    stride=None,
                    value=None,
                ),
            )
        )
    assert exc.value.failure_phrase == FAILURE_RUNTIME_THROW_OR_ABORT

    with pytest.raises(ExecutionEngineError) as exc:
        _load_entry_point(123, "kg_execute_entry")  # type: ignore[arg-type]
    assert exc.value.failure_phrase == FAILURE_RUNTIME_THROW_OR_ABORT

    import ctypes

    def _raise_oserror(*args, **kwargs):  # noqa: ANN001
        raise OSError("missing shared object")

    monkeypatch.setattr(ctypes, "CDLL", _raise_oserror)
    with pytest.raises(ExecutionEngineError) as exc:
        _load_entry_point(str(_build_test_shared_library(tmp_path / "lib", "kg_execute_entry")), "kg_execute_entry")
    assert exc.value.failure_phrase == FAILURE_SYMBOL_RESOLVE_FAILED


def test_execute_engine_private_helpers_dtype_shape_stride_runtime_checks() -> None:
    """覆盖 dtype / shape / stride / runtime 类型识别 helper。

    创建者: 金铲铲大作战
    最后更改: 金铲铲大作战

    测试目的:
    - 验证 normalize / runtime 判定 helper 的常规与异常分支。

    对应功能实现文件路径: kernel_gen/execute_engine/execution_engine.py
    对应 spec 文件路径: spec/execute_engine/execute_engine_api.md
    对应测试文件路径: test/execute_engine/test_execute_engine_private_helpers.py
    """

    assert _normalize_dtype(None) is None
    assert _normalize_dtype("torch.float32") == "float32"
    assert _normalize_dtype("  float64  ") == "float64"

    shape_like = SimpleNamespace(shape=[2, 3])
    assert _normalize_shape(shape_like) == (2, 3)
    assert _normalize_shape(SimpleNamespace(shape=object())) is None
    assert _normalize_shape(None) is None

    torch_stride = SimpleNamespace(stride=lambda: (3, 1))
    assert _normalize_stride(torch_stride) == (3, 1)
    numpy_stride = _FakeNumpyArray(strides=(8, 4), itemsize=4)
    assert _normalize_stride(numpy_stride) == (2, 1)
    assert _normalize_stride(_FakeNumpyArray(strides=(10, 4), itemsize=4)) is None
    assert _normalize_stride(_FakeNumpyArray(strides=(8, 4), itemsize=0)) is None
    assert _normalize_stride(SimpleNamespace()) is None

    assert _runtime_module_name(_FakeTorchTensor()) == "torch"
    assert _runtime_module_name(_FakeNumpyArray()) == "numpy"
    assert _is_torch_tensor(_FakeTorchTensor()) is True
    assert _is_numpy_array(_FakeNumpyArray()) is True
    assert _is_runtime_int(3) is True
    assert _is_runtime_int(True) is False
    assert _is_runtime_float(1.25) is True
    assert _is_runtime_float(False) is False

    assert _is_memory_runtime_arg(_FakeTorchTensor()) is True
    runtime_like = type(
        "RuntimeLikeTensor",
        (),
        {"__module__": "torch", "shape": (1,), "dtype": "float32"},
    )()
    assert _is_memory_runtime_arg(runtime_like) is True
    missing_dtype_like = type("RuntimeLikeTensorMissingDtype", (), {"__module__": "torch", "shape": (1,)})()
    assert _is_memory_runtime_arg(missing_dtype_like) is False

    assert _is_contiguous_memory(_FakeTorchTensor(contiguous=True)) is True
    assert _is_contiguous_memory(_FakeTorchTensor(contiguous=False)) is False
    assert _is_contiguous_memory(SimpleNamespace(flags={"C_CONTIGUOUS": False})) is False
    assert _is_contiguous_memory(SimpleNamespace(flags=SimpleNamespace(c_contiguous=True))) is True
    assert _is_contiguous_memory(SimpleNamespace()) is True


def test_execute_engine_private_helpers_contiguous_stride_and_runtime_pointer() -> None:
    """覆盖连续 stride 与原始数据指针读取 helper。

    创建者: 金铲铲大作战
    最后更改: 金铲铲大作战

    测试目的:
    - 验证连续 stride 生成与 torch / numpy / 非法 RuntimeArg 指针读取分支。

    对应功能实现文件路径: kernel_gen/execute_engine/execution_engine.py
    对应 spec 文件路径: spec/execute_engine/execute_engine_api.md
    对应测试文件路径: test/execute_engine/test_execute_engine_private_helpers.py
    """

    assert _contiguous_stride(()) == ()
    assert _contiguous_stride((2, 3, 4)) == (12, 4, 1)
    assert _runtime_data_pointer(_FakeTorchTensor(data_ptr=12345)) == 12345
    assert _runtime_data_pointer(_FakeNumpyArray(data_ptr=67890)) == 67890
    with pytest.raises(ExecutionEngineError) as exc:
        _runtime_data_pointer(SimpleNamespace())
    assert exc.value.failure_phrase == FAILURE_RUNTIME_THROW_OR_ABORT


def test_execute_engine_private_helpers_arg_slots_and_abi_marshalling() -> None:
    """覆盖 RuntimeArg 槽位构建与 ABI 封送 helper。

    创建者: 金铲铲大作战
    最后更改: 金铲铲大作战

    测试目的:
    - 验证 memory/int/float 三类 slot 的封送路径与失败分支。

    对应功能实现文件路径: kernel_gen/execute_engine/execution_engine.py
    对应 spec 文件路径: spec/execute_engine/execute_engine_api.md
    对应测试文件路径: test/execute_engine/test_execute_engine_private_helpers.py
    """

    slots = _build_arg_slots((_FakeTorchTensor(), 7, 1.25))
    assert [slot.kind for slot in slots] == ["memory", "int", "float"]
    assert slots[0].dtype == "float32"
    assert slots[0].shape == (2, 2)
    assert slots[0].stride == (1, 2) or slots[0].stride == (2, 1) or slots[0].stride is None
    with pytest.raises(ExecutionEngineError) as exc:
        _build_arg_slots((_FakeTorchTensor(contiguous=False),))
    assert exc.value.failure_phrase == FAILURE_RUNTIME_THROW_OR_ABORT
    with pytest.raises(ExecutionEngineError) as exc:
        _build_arg_slots((SimpleNamespace(__module__="torch", shape=(1,)),))
    assert exc.value.failure_phrase == FAILURE_RUNTIME_THROW_OR_ABORT

    slot_array, slot_struct, keepalive = _marshal_slots_for_abi(slots)
    assert len(keepalive) >= 1
    assert slot_array[0].kind == 1
    assert slot_array[1].kind == 2
    assert slot_array[2].kind == 3
    assert slot_struct.__name__ == "_CKgArgSlot"

    with pytest.raises(ExecutionEngineError) as exc:
        _marshal_slots_for_abi((KgArgSlot(position=0, kind="memory", dtype="float32", shape=None, stride=None, value=_FakeTorchTensor()),))
    assert exc.value.failure_phrase == FAILURE_RUNTIME_THROW_OR_ABORT

    with pytest.raises(ExecutionEngineError) as exc:
        _marshal_slots_for_abi((KgArgSlot(position=0, kind="memory", dtype="float32", shape=(2, 2), stride=(1,), value=_FakeTorchTensor()),))
    assert exc.value.failure_phrase == FAILURE_RUNTIME_THROW_OR_ABORT


def test_execute_engine_private_helpers_entry_shim_building() -> None:
    """覆盖 entry shim 解析、生成和 fallback 逻辑。

    创建者: 金铲铲大作战
    最后更改: 金铲铲大作战

    测试目的:
    - 验证复杂参数切分、参数解析、runtime shim 生成与 placeholder shim 分支。

    对应功能实现文件路径: kernel_gen/execute_engine/entry_shim_builder.py
    对应 spec 文件路径: spec/execute_engine/execute_engine_target.md
    对应测试文件路径: test/execute_engine/test_execute_engine_private_helpers.py
    """

    assert _split_params("") == ()
    assert _split_params("int a, float b") == ("int a", "float b")
    assert _split_params("Memory<GM, int32_t>& out, std::array<int, 2> a[2]") == (
        "Memory<GM, int32_t>& out",
        "std::array<int, 2> a[2]",
    )

    spec = _parse_param_spec("const Memory<GM, int32_t>& lhs")
    assert spec is not None
    assert spec.kind == "memory"
    assert spec.ctype == "int32_t"
    assert spec.memory_space == "GM"
    spec = _parse_param_spec("long long value")
    assert spec is not None
    assert spec.kind == "int"
    assert spec.ctype == "long long"
    spec = _parse_param_spec("double value")
    assert spec is not None
    assert spec.kind == "float"
    assert spec.ctype == "double"
    spec = _parse_param_spec("KernelContext & ctx")
    assert spec is not None
    assert spec.kind == "kernel_context"
    assert spec.ctype == "npu_demo::KernelContext"
    assert _parse_param_spec("std::string name") is None

    source = """
    void add_kernel(const Memory<GM, int32_t>& out, int lhs, double rhs) {
      (void)out; (void)lhs; (void)rhs;
    }
    void add_kernel_short(const Memory<GM, int32_t>& out) {
      (void)out;
    }
    """
    extracted = _extract_param_specs(source, "add_kernel")
    assert extracted is not None
    assert [spec.kind for spec in extracted] == ["memory", "int", "float"]
    assert _extract_param_specs(source, "add_kernel_short") is not None
    assert _extract_param_specs("void add_kernel(std::string name) {}", "add_kernel") is None

    runtime_shim = _build_runtime_entry_shim_source(
        function="add_kernel",
        entry_point="kg_execute_entry",
        params=(
            SimpleNamespace(kind="kernel_context", ctype="npu_demo::KernelContext", memory_space=None),
            SimpleNamespace(kind="memory", ctype="int32_t", memory_space="GM"),
            SimpleNamespace(kind="int", ctype="int64_t", memory_space=None),
            SimpleNamespace(kind="float", ctype="double", memory_space=None),
        ),
    )
    assert "npu_demo::KernelContext ctx;" in runtime_shim
    assert "Memory<GM, int32_t> arg0" in runtime_shim
    assert "int64_t arg1" in runtime_shim
    assert "double arg2" in runtime_shim
    assert "return 0;" in runtime_shim

    assert needs_entry_shim(None, "kg_execute_entry") is True
    assert needs_entry_shim("extern \"C\" int kg_execute_entry(const void*, unsigned long long) { return 0; }", "kg_execute_entry") is False
    assert needs_entry_shim("int add(){}", "kg_execute_entry") is True

    runtime_source = build_entry_shim_source(
        function="add_kernel",
        entry_point="kg_execute_entry",
        source="void add_kernel(const Memory<GM, int32_t>& out, int lhs, double rhs) { }",
    )
    assert "Memory<GM, int32_t>" in runtime_source
    assert "extern \"C\" int kg_execute_entry" in runtime_source
    placeholder = build_entry_shim_source(function="add_kernel", entry_point="kg_execute_entry", source="void add_kernel(std::string name) {}")
    assert "entry shim placeholder" in placeholder


def test_execute_engine_private_helpers_compile_source_and_command_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """覆盖 compile 命令、dry-run、实跑与异常 cleanup 分支。

    创建者: 金铲铲大作战
    最后更改: 金铲铲大作战

    测试目的:
    - 验证 compiler helper 的 include / link flags、dry-run、subprocess 路径与异常清理。

    对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
    对应 spec 文件路径: spec/execute_engine/execute_engine_target.md
    对应测试文件路径: test/execute_engine/test_execute_engine_private_helpers.py
    """

    command = build_compile_command(
        compiler="clang++",
        source_path="kernel.cpp",
        output_path="libkernel.so",
        compiler_flags=("-O2",),
        link_flags=("-lm",),
        include_dirs=(".",),
    )
    assert command[:4] == ("clang++", "-shared", "-fPIC", "-O2")
    assert "-I." in command
    assert command[-3:-1] == ("-o", "libkernel.so")
    assert command[-1] == "-lm"

    unit = build_compile_unit(
        source='#include "include/cpu/Memory.h"\nint main(){}',
        target_includes=('#include "include/cpu/Memory.h"', '#include "include/cpu/Nn.h"'),
        entry_shim_source="// shim",
    )
    assert unit.count('#include "include/cpu/Memory.h"') == 1
    assert '#include "include/cpu/Nn.h"' in unit
    assert unit.strip().endswith("// shim")

    artifacts = compile_source(
        source="int main(){}",
        compiler="g++",
        compiler_flags=("-std=c++17",),
        link_flags=(),
        include_dirs=(),
        work_dir=tmp_path / "dry",
        dry_run=True,
    )
    try:
        assert artifacts.return_code == 0
        assert Path(artifacts.soname_path).is_file()
        assert artifacts._cleanup is None
    finally:
        if artifacts._cleanup is not None:
            artifacts._cleanup()

    fake_result = SimpleNamespace(stdout="ok", stderr="", returncode=0)
    run_calls: list[list[str]] = []

    def _fake_run(cmd, capture_output, text, check):  # noqa: ANN001
        run_calls.append(list(cmd))
        return fake_result

    monkeypatch.setattr(subprocess, "run", _fake_run)
    artifacts = compile_source(
        source="int main(){}",
        compiler="g++",
        compiler_flags=("-std=c++17",),
        link_flags=(),
        include_dirs=(),
        work_dir=tmp_path / "real",
        dry_run=False,
    )
    try:
        assert run_calls and run_calls[0][0] == "g++"
        assert artifacts.stdout == "ok"
        assert artifacts.return_code == 0
    finally:
        if artifacts._cleanup is not None:
            artifacts._cleanup()

    failing_dir = tmp_path / "explode"
    failing_dir.mkdir()
    monkeypatch.setattr("kernel_gen.execute_engine.compiler.tempfile.mkdtemp", lambda prefix: str(failing_dir))
    monkeypatch.setattr("kernel_gen.execute_engine.compiler.build_compile_command", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(RuntimeError):
        compile_source(
            source="int main(){}",
            compiler="g++",
            compiler_flags=(),
            link_flags=(),
            include_dirs=(),
            dry_run=True,
        )
    assert not failing_dir.exists()


def test_execute_engine_private_helpers_load_entry_point_paths(tmp_path: Path) -> None:
    """覆盖 entry point 加载的 placeholder / missing / real / missing symbol 路径。

    创建者: 金铲铲大作战
    最后更改: 金铲铲大作战

    测试目的:
    - 验证 `_load_entry_point` 对空产物、缺失文件、缺失符号和真实共享库的处理。

    对应功能实现文件路径: kernel_gen/execute_engine/execution_engine.py
    对应 spec 文件路径: spec/execute_engine/execute_engine_api.md
    对应测试文件路径: test/execute_engine/test_execute_engine_private_helpers.py
    """

    missing_path = tmp_path / "missing.so"
    with pytest.raises(ExecutionEngineError) as exc:
        _load_entry_point(str(missing_path), "kg_execute_entry")
    assert exc.value.failure_phrase == FAILURE_RUNTIME_THROW_OR_ABORT

    empty_path = tmp_path / "empty.so"
    empty_path.write_text("", encoding="utf-8")
    placeholder = _load_entry_point(str(empty_path), "kg_execute_entry")
    assert placeholder(()) == 0

    so_path = _build_test_shared_library(tmp_path, "kg_execute_entry")
    invoke = _load_entry_point(str(so_path), "kg_execute_entry")
    assert invoke(()) == 0

    so_missing_symbol = _build_test_shared_library(tmp_path / "alt", "different_entry")
    with pytest.raises(ExecutionEngineError) as exc:
        _load_entry_point(str(so_missing_symbol), "kg_execute_entry")
    assert exc.value.failure_phrase == FAILURE_SYMBOL_RESOLVE_FAILED


def test_execute_engine_private_helpers_compile_error_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """覆盖 compile 失败 / 缺失输出 / target include 缺失 / shim 跳过分支。

    创建者: 金铲铲大作战
    最后更改: 金铲铲大作战

    测试目的:
    - 验证 `ExecutionEngine.compile` 的边界分支与临时工作区清理。

    对应功能实现文件路径: kernel_gen/execute_engine/execution_engine.py
    对应 spec 文件路径: spec/execute_engine/execute_engine_target.md
    对应测试文件路径: test/execute_engine/test_execute_engine_private_helpers.py
    """

    engine = ExecutionEngine(target="cpu")
    monkeypatch.setattr(
        "kernel_gen.execute_engine.execution_engine.target_includes",
        lambda target: (),
    )
    with pytest.raises(ExecutionEngineError) as exc:
        engine.compile(source="int main(){}", function="cpu::add")
    assert exc.value.failure_phrase == FAILURE_TARGET_HEADER_MISMATCH

    monkeypatch.setattr(
        "kernel_gen.execute_engine.execution_engine.target_includes",
        lambda target: ('#include "include/cpu/Memory.h"',),
    )
    build_source = 'extern "C" int kg_execute_entry(const void*, unsigned long long) { return 0; }'
    called: list[str] = []

    def _fake_build_entry_shim_source(**kwargs):  # noqa: ANN001
        called.append("called")
        return "// should not be used"

    monkeypatch.setattr(
        "kernel_gen.execute_engine.execution_engine.build_entry_shim_source",
        _fake_build_entry_shim_source,
    )
    kernel = engine.compile(source=build_source, function="cpu::add")
    try:
        assert called == []
    finally:
        kernel.close()

    temp_dir = tmp_path / "missing_output"
    temp_dir.mkdir()
    fake_artifacts = CompileArtifacts(
        soname_path=str(temp_dir / "libkernel.so"),
        source_path=str(temp_dir / "kernel.cpp"),
        command=("g++",),
        stdout="",
        stderr="",
        return_code=0,
        _cleanup=lambda: shutil.rmtree(temp_dir, ignore_errors=True),
    )
    monkeypatch.setattr(
        "kernel_gen.execute_engine.execution_engine.compile_source",
        lambda **kwargs: fake_artifacts,
    )
    with pytest.raises(ExecutionEngineError) as exc:
        engine.compile(source="int main(){}", function="cpu::add")
    assert exc.value.failure_phrase == FAILURE_COMPILE_FAILED
    assert not temp_dir.exists()
