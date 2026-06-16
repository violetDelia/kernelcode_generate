"""CUDA SM89 include structure tests.

功能说明:
- 覆盖 `include/cuda_sm89/cuda_sm89.cuh` 的 npu_demo 风格聚合顺序。
- 锁定 CUDA SM89 backend 只提供 Core / Memory / Dma / Kernel / Arch 分层，不聚合 Trance / cost 或旧 CUDA include。

使用示例:
- pytest -q test/include/cuda_sm89/test_public_namespace.py

关联文件:
- spec: spec/include/cuda_sm89/cuda_sm89.md
- 功能实现: include/cuda_sm89/cuda_sm89.cuh
- 功能实现: include/cuda_sm89/Arch.h
"""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
CUDA_INCLUDE_DIR = REPO_ROOT / "include" / "cuda_sm89"
CUDA_AGGREGATE = CUDA_INCLUDE_DIR / "cuda_sm89.cuh"
LEGACY_CUDA_TARGET_TOKEN = "cuda_sm" + "86"


def _include_lines(path: Path) -> list[str]:
    """读取 header 中的 include 行。

    功能说明:
    - 只解析 `#include "..."` 文本行，供 aggregate exact order 测试使用。
    - 不解析系统 include 或条件编译分支，避免测试依赖 C++ 预处理器。

    使用示例:
    - lines = _include_lines(CUDA_AGGREGATE)
    """

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    includes: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#include "):
            includes.append(stripped)
    return includes


def test_cuda_sm89_aggregate_header_uses_exact_npu_demo_style_order() -> None:
    """验证 CUDA SM89 aggregate header 的 exact include 顺序。

    功能说明:
    - 锁定先 api 层、后 backend 层的 Core / Memory / Dma / Kernel / Arch 顺序。
    - 防止误聚合 Trance / cost 或旧 CUDA include。

    使用示例:
    - pytest -q test/include/cuda_sm89/test_public_namespace.py -k exact_npu_demo_style_order
    """

    assert _include_lines(CUDA_AGGREGATE) == [
        '#include "include/api/Core.h"',
        '#include "include/api/Memory.h"',
        '#include "include/api/Dma.h"',
        '#include "include/api/Kernel.h"',
        '#include "include/api/Arch.h"',
        '#include "include/cuda_sm89/Core.h"',
        '#include "include/cuda_sm89/Memory.h"',
        '#include "include/cuda_sm89/Dma.h"',
        '#include "include/cuda_sm89/Kernel.h"',
        '#include "include/cuda_sm89/Arch.h"',
    ]
    aggregate_text = CUDA_AGGREGATE.read_text(encoding="utf-8")
    assert "Trance.h" not in aggregate_text
    assert "cost/" not in aggregate_text
    assert LEGACY_CUDA_TARGET_TOKEN not in aggregate_text


def test_cuda_sm89_backend_headers_exist_with_file_level_docs() -> None:
    """验证 CUDA SM89 backend 分层 header 均存在且带 API 列表。

    功能说明:
    - 锁定 Core / Memory / Dma / Kernel / Arch 五个 backend header 文件。
    - 文件级说明必须包含 `功能说明` 与 `API 列表`，满足实现文件规范。

    使用示例:
    - pytest -q test/include/cuda_sm89/test_public_namespace.py -k backend_headers_exist
    """

    for header_name in ("Core.h", "Memory.h", "Dma.h", "Kernel.h", "Arch.h"):
        header_path = CUDA_INCLUDE_DIR / header_name
        assert header_path.is_file(), header_name
        header_text = header_path.read_text(encoding="utf-8")
        assert "功能说明:" in header_text
        assert "API 列表:" in header_text
    arch_text = (CUDA_INCLUDE_DIR / "Arch.h").read_text(encoding="utf-8")
    assert "namespace cuda_sm89" in arch_text
    assert LEGACY_CUDA_TARGET_TOKEN not in arch_text


def test_cuda_sm89_backend_headers_have_substantive_layering() -> None:
    """验证 CUDA SM89 backend header 不回退到 monolithic Arch.h。

    功能说明:
    - 锁定 Core / Memory / Dma / Kernel / Arch 分层各自承接的主体实现。
    - 防止 Core / Memory / Dma / Kernel 退化为空包装并把实现重新集中到 Arch.h。

    使用示例:
    - pytest -q test/include/cuda_sm89/test_public_namespace.py -k substantive_layering
    """

    core_text = (CUDA_INCLUDE_DIR / "Core.h").read_text(encoding="utf-8")
    memory_text = (CUDA_INCLUDE_DIR / "Memory.h").read_text(encoding="utf-8")
    dma_text = (CUDA_INCLUDE_DIR / "Dma.h").read_text(encoding="utf-8")
    kernel_text = (CUDA_INCLUDE_DIR / "Kernel.h").read_text(encoding="utf-8")
    arch_text = (CUDA_INCLUDE_DIR / "Arch.h").read_text(encoding="utf-8")

    assert "struct ArgSlot" in core_text
    assert "class KernelContext" in core_text
    assert "Vector::Vector" in core_text
    assert "MemoryDescriptor" in memory_text
    assert "memory_from_slot" in memory_text
    assert "alloc_device_array" in memory_text
    assert "class DmaRing" in dma_text
    assert "copy_from_source_window" in dma_text
    assert "broadcast_memory" in dma_text
    assert "tensor_core_matmul_path" in kernel_text
    assert "matmul_memory" in kernel_text
    assert "img2col2d_memory" in kernel_text
    assert "device_alloc" in arch_text
    assert "Status launch" in arch_text
    assert "class DmaRing" not in arch_text
    assert "matmul_memory" not in arch_text
    assert "MemoryDescriptor" not in arch_text
    assert "由同一 aggregate 后续的 `Arch.h` 承接" not in core_text + memory_text + dma_text + kernel_text
    assert len(arch_text.splitlines()) < 350
