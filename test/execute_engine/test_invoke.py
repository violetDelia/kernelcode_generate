"""execute_engine invoke contract tests (P0 skeleton).


功能说明:
- 验证 `CompiledKernel.execute(...)` 的输入校验、参数绑定与失败短语合同（P0/S3）。
- 本阶段不要求真实运行，只固定：
  - runtime_throw_or_abort：参数形态错误/类型不匹配；
  - symbol_resolve_failed：entry_point 为空或不匹配；
  - ExecuteRequest 的字段覆盖优先级。

使用示例:
- pytest -q test/execute_engine/test_invoke.py

当前覆盖率信息:
- `kernel_gen.execute_engine.compiler`：`82%`（Stmts=134 Miss=17 Branch=40 BrPart=15；最近一次统计：2026-04-07 02:12:00 +0800）。

覆盖率命令:
- `pytest -q --cov=kernel_gen.execute_engine.compiler --cov-branch --cov-report=term-missing test/execute_engine/test_invoke.py`

关联文件:
- 功能实现: kernel_gen/execute_engine/compiler.py
- Spec 文档: spec/execute_engine/execute_engine.md
- Spec 文档: spec/execute_engine/execute_engine_api.md
- 测试文件: test/execute_engine/test_invoke.py
"""

from __future__ import annotations

import random
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.error import KernelCodeError
from kernel_gen.execute_engine import (
    CompiledKernel,
    ExecuteRequest,
    ExecutionEngine,
)


def _compile_minimal_kernel() -> CompiledKernel:
    """编译最小可执行 kernel（P0）。


    功能说明:
    - 为 invoke 侧测试提供稳定 `CompiledKernel` 实例，避免在每个 case 里重复样板代码。
    - 本阶段不要求真实编译，返回值来自 `ExecutionEngine.compile` 的骨架产物。

    使用示例:
    - kernel = _compile_minimal_kernel()
    - _ = kernel.execute(args=())

    关联文件:
    - spec: spec/execute_engine/execute_engine.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    engine = ExecutionEngine(target="cpu")
    return engine.compile(source="int main(){}", function="cpu::add")


class _DTypeToken:
    """最小 dtype 字符串化占位（S6）。


    功能说明:
    - 提供非 str dtype 对象，验证公开 execute 入口接受可字符串化 dtype 表达。

    使用示例:
    - token = _DTypeToken("torch.float32")

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    def __init__(self, text: str) -> None:
        self.text = text

    def __str__(self) -> str:
        """返回 dtype 文本。


        功能说明:
        - 为公开 runtime memory 参数的 dtype 归一化提供可字符串化对象。

        使用示例:
        - assert str(_DTypeToken("float32")) == "float32"

        关联文件:
        - spec: spec/execute_engine/execute_engine_api.md
        - test: test/execute_engine/test_invoke.py
        - 功能实现: kernel_gen/execute_engine/compiler.py
        """

        return self.text


class _NumpyFlags:
    """最小 numpy flags 对象占位（S6）。


    功能说明:
    - 提供 `flags.c_contiguous` 访问形态，验证公开 execute 入口对 numpy 风格 flags 的边界处理。

    使用示例:
    - flags = _NumpyFlags(c_contiguous=True)

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    def __init__(self, *, c_contiguous: bool) -> None:
        self.c_contiguous = c_contiguous


class _FakeTorchTensor:
    """最小 torch 张量占位（P0/S3）。


    功能说明:
    - 提供 shape/dtype/stride/is_contiguous 的最小接口，避免测试依赖真实 torch。
    - 仅用于 runtime arg 路径校验，不承载真实数据。

    使用示例:
    - tensor = _FakeTorchTensor(shape=(2, 2), dtype="torch.float32")

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    __module__ = "torch"

    def __init__(
        self,
        *,
        shape: tuple[int, ...] | int,
        dtype: str | None | _DTypeToken,
        stride: tuple[int, ...] | None = None,
        contiguous: bool = True,
        data_ptr: int = 4096,
    ) -> None:
        self.shape = shape
        self.dtype = dtype
        self._stride = stride
        self._contiguous = contiguous
        self._data_ptr = data_ptr

    def stride(self) -> tuple[int, ...] | None:
        """返回 stride 信息。


        功能说明:
        - 提供 stride 读取接口，供 runtime arg 校验使用。

        使用示例:
        - tensor = _FakeTorchTensor(shape=(1,), dtype="float32", stride=(1,))
        - assert tensor.stride() == (1,)

        关联文件:
        - spec: spec/execute_engine/execute_engine_api.md
        - test: test/execute_engine/test_invoke.py
        - 功能实现: kernel_gen/execute_engine/compiler.py
        """

        return self._stride

    def is_contiguous(self) -> bool:
        """返回是否连续布局。


        功能说明:
        - 提供连续布局标记，供 runtime arg 校验使用。

        使用示例:
        - tensor = _FakeTorchTensor(shape=(1,), dtype="float32", contiguous=True)
        - assert tensor.is_contiguous() is True

        关联文件:
        - spec: spec/execute_engine/execute_engine_api.md
        - test: test/execute_engine/test_invoke.py
        - 功能实现: kernel_gen/execute_engine/compiler.py
        """

        return self._contiguous

    def data_ptr(self) -> int:
        """返回底层数据指针占位地址。


        功能说明:
        - 为公开 `CompiledKernel.execute(...)` 的真实 shared object 调用路径提供 torch 风格数据指针。

        使用示例:
        - assert _FakeTorchTensor(shape=(1,), dtype="float32").data_ptr() > 0

        关联文件:
        - spec: spec/execute_engine/execute_engine_api.md
        - test: test/execute_engine/test_invoke.py
        - 功能实现: kernel_gen/execute_engine/compiler.py
        """

        return self._data_ptr


class _RaisingContiguousTorchTensor(_FakeTorchTensor):
    """is_contiguous 读取失败的 torch 张量占位（S6）。


    功能说明:
    - 验证公开 execute 入口在 memory 连续性无法确认时返回固定失败短语。

    使用示例:
    - tensor = _RaisingContiguousTorchTensor(shape=(1,), dtype="float32")

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    def is_contiguous(self) -> bool:
        """模拟连续性查询失败。


        功能说明:
        - 通过公开 execute 入口触发 runtime memory 连续性拒绝路径。

        使用示例:
        - with pytest.raises(RuntimeError): _RaisingContiguousTorchTensor(shape=(1,), dtype="float32").is_contiguous()

        关联文件:
        - spec: spec/execute_engine/execute_engine_api.md
        - test: test/execute_engine/test_invoke.py
        - 功能实现: kernel_gen/execute_engine/compiler.py
        """

        raise RuntimeError("contiguous flag unavailable")


class _FakeNumpyArray:
    """最小 numpy 数组占位（P0/S3）。


    功能说明:
    - 提供 shape/dtype/strides/flags 的最小接口，避免测试依赖真实 numpy。
    - 仅用于 runtime arg 路径校验，不承载真实数据。

    使用示例:
    - array = _FakeNumpyArray(shape=(2, 2), dtype="float32")

    关联文件:
    - spec: spec/execute_engine/execute_engine_api.md
    - test: test/execute_engine/test_invoke.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    __module__ = "numpy"

    def __init__(
        self,
        *,
        shape: tuple[int, ...],
        dtype: str,
        strides: tuple[int, ...] | None = None,
        contiguous: bool = True,
        itemsize: int = 4,
        data: int = 8192,
        flags: dict[str, bool] | _NumpyFlags | None = None,
        with_ctypes: bool = True,
    ) -> None:
        self.shape = shape
        self.dtype = dtype
        self.strides = strides
        self.flags = {"C_CONTIGUOUS": contiguous} if flags is None else flags
        self.itemsize = itemsize
        if with_ctypes:
            self.ctypes = SimpleNamespace(data=data)


_REAL_ENTRY_RUNTIME_ARG_CASES = tuple(
    random.Random(20260505).sample(
        [
            (
                "torch-default-stride-with-scalars",
                (
                    _FakeTorchTensor(shape=(2, 3), dtype="torch.float32", stride=None, data_ptr=4096),
                    7,
                    1.25,
                ),
            ),
            (
                "numpy-byte-stride-with-scalars",
                (
                    _FakeNumpyArray(shape=(2, 3), dtype="float32", strides=(12, 4), itemsize=4, data=8192),
                    9,
                    2.5,
                ),
            ),
            (
                "mixed-memory-int-float",
                (
                    _FakeTorchTensor(shape=(1, 4), dtype="torch.int32", stride=(4, 1), data_ptr=12288),
                    _FakeNumpyArray(shape=(1, 4), dtype="int32", strides=(16, 4), itemsize=4, data=16384),
                    11,
                    3.5,
                ),
            ),
        ],
        3,
    )
)


# EE-S1-I-001
# 测试目的: 验证 ExecuteRequest 路径下 args 能正常传入且成功返回 ok=True。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_api.md
# 对应测试文件路径: test/execute_engine/test_invoke.py
def test_execute_engine_invoke_ok_via_request_args() -> None:
    kernel = _compile_minimal_kernel()
    result = kernel.execute(request=ExecuteRequest(args=()))
    assert result.ok is True
    assert result.failure_phrase is None


# EE-S1-I-002
# 测试目的: 验证 args 未提供时触发 runtime_throw_or_abort。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine.md
# 对应测试文件路径: test/execute_engine/test_invoke.py
def test_execute_engine_invoke_runtime_throw_or_abort_on_args_none() -> None:
    kernel = _compile_minimal_kernel()
    with pytest.raises(KernelCodeError) as exc:
        kernel.execute()
    assert exc.value.failure_phrase == "runtime_throw_or_abort"


# EE-S1-I-003
# 测试目的: 验证 args 非 tuple 时触发 runtime_throw_or_abort。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine.md
# 对应测试文件路径: test/execute_engine/test_invoke.py
def test_execute_engine_invoke_runtime_throw_or_abort_on_args_not_tuple() -> None:
    kernel = _compile_minimal_kernel()
    with pytest.raises(KernelCodeError) as exc:
        kernel.execute(args=[])  # type: ignore[arg-type]
    assert exc.value.failure_phrase == "runtime_throw_or_abort"


# EE-S1-I-004
# 测试目的: 验证 args 元素不属于已支持 runtime arg 时触发 runtime_throw_or_abort。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine.md
# 对应测试文件路径: test/execute_engine/test_invoke.py
def test_execute_engine_invoke_runtime_throw_or_abort_on_unsupported_runtime_arg() -> None:
    kernel = _compile_minimal_kernel()
    with pytest.raises(KernelCodeError) as exc:
        kernel.execute(args=(True,))  # type: ignore[arg-type]
    assert exc.value.failure_phrase == "runtime_throw_or_abort"


# EE-S1-I-005
# 测试目的: 验证 entry_point 为空时触发 symbol_resolve_failed。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_api.md
# 对应测试文件路径: test/execute_engine/test_invoke.py
def test_execute_engine_invoke_symbol_resolve_failed_on_empty_entry_point() -> None:
    kernel = _compile_minimal_kernel()
    with pytest.raises(KernelCodeError) as exc:
        kernel.execute(request=ExecuteRequest(args=(), entry_point=" "))
    assert exc.value.failure_phrase == "symbol_resolve_failed"


# EE-S3-I-001
# 功能说明: 覆盖 torch/numpy/int/float 运行参数的顺序绑定与执行成功口径。
# 使用示例: pytest -q test/execute_engine/test_invoke.py -k "S3-I-001"
# 测试目的: 验证运行参数绑定成功时返回 ok=True 且 compile stdout/stderr 透传。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_api.md
# 对应测试文件路径: test/execute_engine/test_invoke.py
def test_execute_engine_invoke_ok_with_memory_int_float_args() -> None:
    kernel = _compile_minimal_kernel()
    out = _FakeTorchTensor(shape=(2, 2), dtype="torch.float32")
    rhs = _FakeNumpyArray(shape=(2, 2), dtype="float32")
    result = kernel.execute(args=(out, rhs, 7, 1.25))
    assert result.ok is True
    assert result.status_code == 0
    assert result.failure_phrase is None
    assert result.compile_stdout == kernel.compile_stdout
    assert result.compile_stderr == kernel.compile_stderr


# EE-S3-I-002
# 功能说明: 覆盖 entry_point 不匹配时的固定失败短语。
# 使用示例: pytest -q test/execute_engine/test_invoke.py -k "S3-I-002"
# 测试目的: 验证 entry_point 与编译产物不一致时返回 symbol_resolve_failed。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_api.md
# 对应测试文件路径: test/execute_engine/test_invoke.py
def test_execute_engine_invoke_symbol_resolve_failed_on_entry_point_mismatch() -> None:
    kernel = _compile_minimal_kernel()
    with pytest.raises(KernelCodeError) as exc:
        kernel.execute(args=(), entry_point="kg_execute_entry_v2")
    assert exc.value.failure_phrase == "symbol_resolve_failed"


# EE-S3-I-003
# 功能说明: 覆盖 memory 参数非连续布局的拒绝路径。
# 使用示例: pytest -q test/execute_engine/test_invoke.py -k "S3-I-003"
# 测试目的: 验证 memory 参数不可连续时返回 runtime_throw_or_abort。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_api.md
# 对应测试文件路径: test/execute_engine/test_invoke.py
def test_execute_engine_invoke_runtime_throw_or_abort_on_memory_not_contiguous() -> None:
    kernel = _compile_minimal_kernel()
    value = _FakeTorchTensor(shape=(2, 2), dtype="float32", contiguous=False)
    with pytest.raises(KernelCodeError) as exc:
        kernel.execute(args=(value,))
    assert exc.value.failure_phrase == "runtime_throw_or_abort"


# EE-S3-I-004
# 功能说明: 覆盖 memory 参数 dtype 缺失的拒绝路径。
# 使用示例: pytest -q test/execute_engine/test_invoke.py -k "S3-I-004"
# 测试目的: 验证 memory 参数 dtype 为空时返回 runtime_throw_or_abort。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_api.md
# 对应测试文件路径: test/execute_engine/test_invoke.py
def test_execute_engine_invoke_runtime_throw_or_abort_on_memory_dtype_missing() -> None:
    kernel = _compile_minimal_kernel()
    value = _FakeTorchTensor(shape=(2, 2), dtype="")
    with pytest.raises(KernelCodeError) as exc:
        kernel.execute(args=(value,))
    assert exc.value.failure_phrase == "runtime_throw_or_abort"


# EE-S3-I-005
# 功能说明: 覆盖真实 shared object 入口对公开 runtime arg 矩阵的绑定与执行成功口径。
# 使用示例: pytest -q test/execute_engine/test_invoke.py -k "S3-I-005"
# 测试目的: 验证 torch/numpy/int/float 组合参数经过公开 execute 入口传入真实 `kg_execute_entry`。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_api.md
# 对应测试文件路径: test/execute_engine/test_invoke.py
@pytest.mark.parametrize(("case_id", "args"), _REAL_ENTRY_RUNTIME_ARG_CASES)
def test_execute_engine_invoke_real_entry_runtime_arg_matrix(
    case_id: str,
    args: tuple,
) -> None:
    source = (
        'extern "C" int kg_execute_entry(const void*, unsigned long long arg_count) {'
        " return arg_count > 0 ? 0 : -1;"
        "}\n"
        "int add(){ return 0; }"
    )
    kernel = ExecutionEngine(target="npu_demo").compile(source=source, function="add")
    try:
        result = kernel.execute(args=args)

        assert case_id
        assert result.ok is True
        assert result.status_code == 0
        assert result.failure_phrase is None
    finally:
        kernel.close()


# EE-S3-I-006
# 功能说明: 覆盖真实 shared object 入口返回非零状态时的公开失败短语。
# 使用示例: pytest -q test/execute_engine/test_invoke.py -k "S3-I-006"
# 测试目的: 验证运行时入口返回非零时统一映射到 runtime_throw_or_abort。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_api.md
# 对应测试文件路径: test/execute_engine/test_invoke.py
def test_execute_engine_invoke_real_entry_nonzero_status_uses_runtime_failure() -> None:
    source = (
        'extern "C" int kg_execute_entry(const void*, unsigned long long arg_count) {'
        " return arg_count == 2 ? 0 : -7;"
        "}\n"
        "int add(){ return 0; }"
    )
    kernel = ExecutionEngine(target="npu_demo").compile(source=source, function="add")
    try:
        with pytest.raises(KernelCodeError) as exc:
            kernel.execute(args=(1,))

        assert exc.value.failure_phrase == "runtime_throw_or_abort"
    finally:
        kernel.close()


# EE-S3-I-007
# 功能说明: 覆盖公开 CompiledKernel 对共享库路径/符号加载失败的错误语义。
# 使用示例: pytest -q test/execute_engine/test_invoke.py -k "S3-I-007"
# 测试目的: 验证缺失路径、空路径与非法 shared object 均经公开 execute 入口返回固定失败短语。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_api.md
# 对应测试文件路径: test/execute_engine/test_invoke.py
def test_execute_engine_invoke_public_soname_load_failure_matrix(tmp_path: Path) -> None:
    runtime_failure_cases = (
        ("empty-path", ""),
        ("missing-path", str(tmp_path / "missing.so")),
    )
    for case_id, soname_path in runtime_failure_cases:
        kernel = CompiledKernel(
            target="npu_demo",
            soname_path=soname_path,
            function="add",
            entry_point="kg_execute_entry",
        )
        with pytest.raises(KernelCodeError) as exc:
            kernel.execute(args=())

        assert case_id
        assert exc.value.failure_phrase == "runtime_throw_or_abort"

    invalid_shared_object = tmp_path / "invalid.so"
    invalid_shared_object.write_text("not a shared object", encoding="utf-8")
    kernel = CompiledKernel(
        target="npu_demo",
        soname_path=str(invalid_shared_object),
        function="add",
        entry_point="kg_execute_entry",
    )
    with pytest.raises(KernelCodeError) as exc:
        kernel.execute(args=())

    assert exc.value.failure_phrase == "symbol_resolve_failed"


# EE-S3-I-008
# 功能说明: 覆盖公开 execute 入口的 memory 参数 dtype/shape/stride/flags 边界矩阵。
# 使用示例: pytest -q test/execute_engine/test_invoke.py -k "memory_metadata_matrix"
# 测试目的: 验证 runtime memory 参数只通过公开 `CompiledKernel.execute(...)` 完成校验。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_api.md
# 对应测试文件路径: test/execute_engine/test_invoke.py
def test_execute_engine_invoke_public_memory_metadata_matrix() -> None:
    kernel = _compile_minimal_kernel()
    ok_cases = (
        ("dtype-object", _FakeTorchTensor(shape=(1,), dtype=_DTypeToken("torch.float32"))),
        ("stride-unavailable", _FakeTorchTensor(shape=(1,), dtype="float32", stride=None)),
        ("numpy-stride-itemsize-unavailable", _FakeNumpyArray(shape=(2,), dtype="float32", strides=(4,), itemsize=0)),
        ("numpy-byte-stride-not-divisible", _FakeNumpyArray(shape=(2,), dtype="float32", strides=(6,), itemsize=4)),
        ("numpy-flags-object-contiguous", _FakeNumpyArray(shape=(2,), dtype="float32", flags=_NumpyFlags(c_contiguous=True))),
    )
    for case_id, value in ok_cases:
        result = kernel.execute(args=(value,))

        assert case_id
        assert result.ok is True
        assert result.failure_phrase is None

    error_cases = (
        ("dtype-none", _FakeTorchTensor(shape=(1,), dtype=None)),
        ("shape-not-iterable", _FakeTorchTensor(shape=3, dtype="float32")),
        ("contiguous-raises", _RaisingContiguousTorchTensor(shape=(1,), dtype="float32")),
        ("numpy-flags-object-not-contiguous", _FakeNumpyArray(shape=(2,), dtype="float32", flags=_NumpyFlags(c_contiguous=False))),
    )
    for case_id, value in error_cases:
        with pytest.raises(KernelCodeError) as exc:
            kernel.execute(args=(value,))

        assert case_id
        assert exc.value.failure_phrase == "runtime_throw_or_abort"


# EE-S3-I-009
# 功能说明: 覆盖真实 shared object 调用时 memory 数据指针缺失的公开失败语义。
# 使用示例: pytest -q test/execute_engine/test_invoke.py -k "missing_memory_data_pointer"
# 测试目的: 验证真实 entry 调用前的 ABI 封送不会吞掉 memory 数据指针错误。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_api.md
# 对应测试文件路径: test/execute_engine/test_invoke.py
def test_execute_engine_invoke_real_entry_rejects_missing_memory_data_pointer() -> None:
    source = (
        'extern "C" int kg_execute_entry(const void*, unsigned long long) { return 0; }\n'
        "int add(){ return 0; }"
    )
    kernel = ExecutionEngine(target="npu_demo").compile(source=source, function="add")
    value = _FakeNumpyArray(shape=(2,), dtype="float32", with_ctypes=False)
    try:
        with pytest.raises(KernelCodeError) as exc:
            kernel.execute(args=(value,))

        assert exc.value.failure_phrase == "runtime_throw_or_abort"
    finally:
        kernel.close()


# EE-S3-I-010
# 功能说明: 覆盖真实 shared object 存在但入口符号缺失的公开失败语义。
# 使用示例: pytest -q test/execute_engine/test_invoke.py -k "missing_exported_entry_symbol"
# 测试目的: 验证公开 `CompiledKernel(...)` 指向缺失 entry 时返回 `symbol_resolve_failed`。
# 对应功能实现文件路径: kernel_gen/execute_engine/compiler.py
# 对应 spec 文件路径: spec/execute_engine/execute_engine_api.md
# 对应测试文件路径: test/execute_engine/test_invoke.py
def test_execute_engine_invoke_real_entry_missing_exported_symbol() -> None:
    source = (
        'extern "C" int kg_execute_entry(const void*, unsigned long long) { return 0; }\n'
        "int add(){ return 0; }"
    )
    kernel = ExecutionEngine(target="npu_demo").compile(source=source, function="add")
    try:
        missing_entry_kernel = CompiledKernel(
            target=kernel.target,
            soname_path=kernel.soname_path,
            function=kernel.function,
            entry_point="missing_entry",
            compile_stdout=kernel.compile_stdout,
            compile_stderr=kernel.compile_stderr,
        )
        with pytest.raises(KernelCodeError) as exc:
            missing_entry_kernel.execute(args=())

        assert exc.value.failure_phrase == "symbol_resolve_failed"
    finally:
        kernel.close()
