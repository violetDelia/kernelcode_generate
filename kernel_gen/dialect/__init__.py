"""Dialect package entry.


功能说明:
- 暴露 nn 与 arch dialect 的 type、attr 与 op 定义，供包级导入复用。
- 采用惰性导入避免在仅使用 `kernel_gen.dialect.*` 子模块时无条件加载全部 dialect，
  以降低重依赖导入带来的不稳定性。

API 列表:
- `Arch`
- `class ArchGetBlockIdOp(result_type: Attribute | None = None)`
- `class ArchGetBlockNumOp(result_type: Attribute | None = None)`
- `class ArchGetThreadIdOp(result_type: Attribute | None = None)`
- `class ArchGetThreadNumOp(result_type: Attribute | None = None)`
- `class ArchGetSubthreadIdOp(result_type: Attribute | None = None)`
- `class ArchGetSubthreadNumOp(result_type: Attribute | None = None)`
- `class ArchGetDynamicMemoryOp(memory_space: NnMemorySpaceAttr, result_type: Attribute | None = None)`
- `class ArchLaunchKernelOp(callee: str | Attribute, block: SSAValue | Operation, thread: SSAValue | Operation, subthread: SSAValue | Operation, shared_memory_size: SSAValue | Operation, args: Sequence[SSAValue | Operation] = ())`
- `Nn`
- `class NnAddOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnBroadcastOp(input_value: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnSubOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnMulOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnTrueDivOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnEqOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnNeOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnLtOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnLeOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnGtOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnGeOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnMatmulOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnImg2col1dOp(input_value: SSAValue, result_type: NnMemoryType, kw: SSAValue, sw: SSAValue, dw: SSAValue, pl: SSAValue, pr: SSAValue, space: NnMemorySpaceAttr)`
- `class NnImg2col2dOp(input_value: SSAValue, result_type: NnMemoryType, kh: SSAValue, kw: SSAValue, sh: SSAValue, sw: SSAValue, dh: SSAValue, dw: SSAValue, ph: SSAValue, pw: SSAValue, pl: SSAValue, pr: SSAValue, space: NnMemorySpaceAttr)`
- `class NnMemorySpaceAttr(space: StringAttr)`
- `class NnMemoryType(shape: ArrayAttr[SymbolExprAttr], stride: ArrayAttr[SymbolExprAttr], element_type: Attribute, space: NnMemorySpaceAttr)`

使用示例:
- from kernel_gen.dialect import Arch, ArchLaunchKernelOp, Nn, NnAddOp, NnMemoryType

关联文件:
- spec: spec/dialect/arch.md
- test: test/dialect/test_arch.py
- 功能实现: kernel_gen/dialect/__init__.py
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

__all__ = [
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


if TYPE_CHECKING:  # pragma: no cover
    from .arch import (  # noqa: F401
        Arch,
        ArchGetBlockIdOp,
        ArchGetBlockNumOp,
        ArchGetDynamicMemoryOp,
        ArchGetSubthreadIdOp,
        ArchGetSubthreadNumOp,
        ArchGetThreadIdOp,
        ArchGetThreadNumOp,
        ArchLaunchKernelOp,
    )
    from .nn import (  # noqa: F401
        Nn,
        NnAddOp,
        NnBroadcastOp,
        NnEqOp,
        NnGeOp,
        NnGtOp,
        NnImg2col1dOp,
        NnImg2col2dOp,
        NnLeOp,
        NnLtOp,
        NnMatmulOp,
        NnMemorySpaceAttr,
        NnMemoryType,
        NnMulOp,
        NnNeOp,
        NnSubOp,
        NnTrueDivOp,
    )


_LAZY_EXPORT_MODULE: dict[str, str] = {
    "Arch": ".arch",
    "ArchGetBlockIdOp": ".arch",
    "ArchGetBlockNumOp": ".arch",
    "ArchGetThreadIdOp": ".arch",
    "ArchGetThreadNumOp": ".arch",
    "ArchGetSubthreadIdOp": ".arch",
    "ArchGetSubthreadNumOp": ".arch",
    "ArchGetDynamicMemoryOp": ".arch",
    "ArchLaunchKernelOp": ".arch",
    "Nn": ".nn",
    "NnAddOp": ".nn",
    "NnBroadcastOp": ".nn",
    "NnSubOp": ".nn",
    "NnMulOp": ".nn",
    "NnTrueDivOp": ".nn",
    "NnEqOp": ".nn",
    "NnNeOp": ".nn",
    "NnLtOp": ".nn",
    "NnLeOp": ".nn",
    "NnGtOp": ".nn",
    "NnGeOp": ".nn",
    "NnMatmulOp": ".nn",
    "NnImg2col1dOp": ".nn",
    "NnImg2col2dOp": ".nn",
    "NnMemorySpaceAttr": ".nn",
    "NnMemoryType": ".nn",
}


def __getattr__(name: str) -> Any:
    """按需加载 dialect 导出。


    功能说明:
    - 避免包初始化时导入 `arch/nn`，仅在实际访问导出符号时再加载对应模块。

    使用示例:
    - from kernel_gen.dialect import NnMemoryType
    - assert NnMemoryType.__name__ == "NnMemoryType"

    关联文件:
    - spec: spec/tools/ircheck.md
    - test: test/tools/test_ircheck_runner.py
    - 功能实现: kernel_gen/dialect/__init__.py
    """

    module_name = _LAZY_EXPORT_MODULE.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name, __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """让 `dir(kernel_gen.dialect)` 包含惰性导出符号。"""

    return sorted(set(globals().keys()) | set(_LAZY_EXPORT_MODULE.keys()))
