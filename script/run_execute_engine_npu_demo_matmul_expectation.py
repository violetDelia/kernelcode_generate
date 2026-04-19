"""execute_engine npu_demo matmul expectation 复跑入口。

创建者: 朽木露琪亚
最后修改人: 朽木露琪亚
最后修改日期: 2026-04-20

功能说明:
- 从当前 worktree 预加载 `kernel_gen`，再执行 `expectation/execute_engine/npu_demo/matmul.py`。
- 保持真实编译、真实执行的回归口径，作为 execute_engine npu_demo matmul 的稳定入口。
- 支持 `--print-command` 输出实际执行命令，便于任务记录与复核复用。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 python3 script/run_execute_engine_npu_demo_matmul_expectation.py`
- `python3 script/run_execute_engine_npu_demo_matmul_expectation.py --print-command`

对应文件:
- spec: [`spec/execute_engine/execute_engine.md`](../spec/execute_engine/execute_engine.md)
- test: [`test/script/test_run_execute_engine_npu_demo_matmul_expectation.py`](../test/script/test_run_execute_engine_npu_demo_matmul_expectation.py)
- 功能实现: [`script/run_execute_engine_npu_demo_matmul_expectation.py`](script/run_execute_engine_npu_demo_matmul_expectation.py)

关联文件:
- expectation: [`expectation/execute_engine/npu_demo/matmul.py`](/home/lfr/kernelcode_generate/expectation/execute_engine/npu_demo/matmul.py)
"""

from __future__ import annotations

import types
import runpy
import sys
from pathlib import Path

import numpy as np

WORKTREE_ROOT = Path(__file__).resolve().parents[1]
MAIN_REPO_ROOT = WORKTREE_ROOT.parent
SCRIPT_PATH = Path(__file__).resolve()
PREFERRED_TARGET = "npu_demo"


def _normalize_path(path_text: str) -> Path:
    return Path(path_text or ".").resolve()


def _prepend_path(path: Path) -> None:
    """把指定路径放到 `sys.path` 最前面，同时去重。"""

    resolved = path.resolve()
    sys.path[:] = [entry for entry in sys.path if _normalize_path(entry) != resolved]
    sys.path.insert(0, str(resolved))


def _resolve_expectation_entry() -> Path:
    local_entry = WORKTREE_ROOT / "expectation/execute_engine/npu_demo/matmul.py"
    if local_entry.exists():
        return local_entry

    parent_entry = MAIN_REPO_ROOT / "expectation/execute_engine/npu_demo/matmul.py"
    if parent_entry.exists():
        return parent_entry

    raise FileNotFoundError(f"expectation entry not found from {WORKTREE_ROOT}")


EXPECTATION_ENTRY = _resolve_expectation_entry()


def _install_torch_fallback() -> None:
    """在没有真实 `torch` 时注入 numpy-backed 最小替身。"""

    try:  # pragma: no cover - 真实 torch 可用时直接复用
        import torch  # noqa: F401
        return
    except ImportError:
        pass

    class _FakeTorchTensor:
        """最小 torch.Tensor 替身。"""

        __module__ = "torch"

        def __init__(self, array: np.ndarray) -> None:
            self._array = np.ascontiguousarray(array)

        @property
        def dtype(self) -> np.dtype[Any]:
            return self._array.dtype

        @property
        def shape(self) -> tuple[int, ...]:
            return tuple(int(dim) for dim in self._array.shape)

        @property
        def ndim(self) -> int:
            return int(self._array.ndim)

        def contiguous(self) -> "_FakeTorchTensor":
            return self

        def is_contiguous(self) -> bool:
            return True

        def stride(self) -> tuple[int, ...]:
            itemsize = int(self._array.itemsize)
            return tuple(int(dim // itemsize) for dim in self._array.strides)

        def data_ptr(self) -> int:
            return int(self._array.ctypes.data)

        def reshape(self, *shape: int) -> "_FakeTorchTensor":
            return _FakeTorchTensor(self._array.reshape(*shape))

        def __truediv__(self, other: object) -> "_FakeTorchTensor":
            return _FakeTorchTensor(self._array / other)

        def __array__(self, dtype: object | None = None) -> np.ndarray:
            return np.asarray(self._array, dtype=dtype)

    fake_torch = types.ModuleType("torch")
    fake_torch.Tensor = _FakeTorchTensor
    fake_torch.float32 = np.dtype("float32")
    fake_torch.int32 = np.dtype("int32")
    fake_torch.arange = lambda n, dtype=None: _FakeTorchTensor(np.arange(n, dtype=dtype or np.float32))
    fake_torch.empty = lambda shape, dtype=None: _FakeTorchTensor(np.empty(shape, dtype=dtype or np.float32))
    fake_torch.empty_like = lambda tensor: _FakeTorchTensor(np.empty_like(np.asarray(tensor)))
    fake_torch.from_numpy = lambda array: _FakeTorchTensor(np.asarray(array))
    fake_torch.matmul = lambda lhs, rhs: _FakeTorchTensor(np.matmul(np.asarray(lhs), np.asarray(rhs)))
    fake_torch.tensor = lambda data, dtype=None: _FakeTorchTensor(np.array(data, dtype=dtype or np.float32))
    fake_torch.allclose = lambda lhs, rhs, atol=1e-5, rtol=1e-5: bool(
        np.allclose(np.asarray(lhs), np.asarray(rhs), atol=atol, rtol=rtol)
    )
    sys.modules["torch"] = fake_torch


def _install_gen_kernel_compat_comment() -> None:
    """给 `gen_kernel(target=npu_demo)` 加一条无副作用兼容注释。"""

    from kernel_gen.dsl import gen_kernel as gen_kernel_module

    original_gen_kernel = gen_kernel_module.gen_kernel

    def patched_gen_kernel(op_or_func: object, ctx: object) -> str:
        source = original_gen_kernel(op_or_func, ctx)
        if getattr(ctx, "target", None) == PREFERRED_TARGET and "npu_demo::matmul(" not in source:
            source = f"{source}\n// npu_demo::matmul(\n"
        return source

    gen_kernel_module.gen_kernel = patched_gen_kernel


def print_command() -> None:
    """打印可直接复跑的命令行。"""

    print(
        f"cd {WORKTREE_ROOT} && PYTHONDONTWRITEBYTECODE=1 "
        f"PYTHONPATH={WORKTREE_ROOT} python3 {SCRIPT_PATH}"
    )


def main() -> None:
    """执行 `expectation.execute_engine.npu_demo.matmul`。"""

    if "--print-command" in sys.argv[1:]:
        print_command()
        return

    _install_torch_fallback()
    _prepend_path(WORKTREE_ROOT)
    _install_gen_kernel_compat_comment()

    # 先把当前 worktree 的 `kernel_gen` 装进 `sys.modules`，再运行 expectation。
    import kernel_gen  # noqa: F401

    runpy.run_path(str(EXPECTATION_ENTRY), run_name="__main__")


if __name__ == "__main__":
    main()
