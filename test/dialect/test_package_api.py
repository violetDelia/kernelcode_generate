"""package api tests for kernel_gen.dialect.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 kernel_gen.dialect 包入口的懒加载导出、__all__ 与 import * 边界。

使用示例:
- pytest -q test/dialect/test_package_api.py

关联文件:
- 功能实现: kernel_gen/dialect/__init__.py
- Spec 文档: spec/dialect/arch.md
- Spec 文档: spec/dialect/nn.md
- Spec 文档: spec/dialect/dma.md
- Spec 文档: spec/dialect/symbol.md
- Spec 文档: spec/dialect/tuner.md
- 测试文件: test/dialect/test_package_api.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def test_dialect_package_exports_are_lazy_and_stable() -> None:
    import kernel_gen.dialect as package_module

    assert type(package_module.Arch).__name__ == "Dialect"
    assert type(package_module.Nn).__name__ == "Dialect"
    assert package_module.Arch.name == "arch"
    assert package_module.Nn.name == "nn"
    assert package_module.NnMemoryType.__name__ == "NnMemoryType"

    assert package_module.__all__ == [
        "Arch",
        "ArchGetBlockIdOp",
        "ArchGetBlockNumOp",
        "ArchGetThreadIdOp",
        "ArchGetThreadNumOp",
        "ArchGetSubthreadIdOp",
        "ArchGetSubthreadNumOp",
        "ArchGetDynamicMemoryOp",
        "ArchLaunchKernelOp",
        "Nn",
        "NnAddOp",
        "NnBroadcastOp",
        "NnSubOp",
        "NnMulOp",
        "NnTrueDivOp",
        "NnEqOp",
        "NnNeOp",
        "NnLtOp",
        "NnLeOp",
        "NnGtOp",
        "NnGeOp",
        "NnMatmulOp",
        "NnImg2col1dOp",
        "NnImg2col2dOp",
        "NnMemorySpaceAttr",
        "NnMemoryType",
    ]

    assert "Arch" in dir(package_module)
    assert "NnMemoryType" in dir(package_module)


def test_dialect_package_import_star_exports_only_public_names() -> None:
    namespace: dict[str, object] = {}

    exec("from kernel_gen.dialect import *", {}, namespace)

    assert sorted(namespace) == [
        "Arch",
        "ArchGetBlockIdOp",
        "ArchGetBlockNumOp",
        "ArchGetDynamicMemoryOp",
        "ArchGetSubthreadIdOp",
        "ArchGetSubthreadNumOp",
        "ArchGetThreadIdOp",
        "ArchGetThreadNumOp",
        "ArchLaunchKernelOp",
        "Nn",
        "NnAddOp",
        "NnBroadcastOp",
        "NnEqOp",
        "NnGeOp",
        "NnGtOp",
        "NnImg2col1dOp",
        "NnImg2col2dOp",
        "NnLeOp",
        "NnLtOp",
        "NnMatmulOp",
        "NnMemorySpaceAttr",
        "NnMemoryType",
        "NnMulOp",
        "NnNeOp",
        "NnSubOp",
        "NnTrueDivOp",
    ]
