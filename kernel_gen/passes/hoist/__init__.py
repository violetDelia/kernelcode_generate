"""hoist pass package.

功能说明:
- 承载 hoist pass 真实实现，包括 alias 归一、symbol loop hoist、dma alias hoist 和组合 pipeline pass。
- `kernel_gen.passes.hoist.*` 是 hoist pass 的唯一模块真源；旧根模块路径不保留兼容 shim。

API 列表:
- `class DmaAliasToReinterpretPass(fold: bool = True)`
- `get_dma_alias_to_reinterpret_patterns() -> list[RewritePattern]`
- `class SymbolLoopHoistPass(fold: bool = True)`
- `class SymbolMinHoistPattern()`
- `class SymbolMaxHoistPattern()`
- `get_symbol_loop_hoist_patterns() -> list[RewritePattern]`
- `class DmaAliasThroughWriteNoReadPattern(module: ModuleOp)`
- `class DmaAliasHoistPattern(module: ModuleOp)`
- `get_hoist_dma_alias_ops_pass_patterns(module: ModuleOp) -> list[RewritePattern]`
- `class HoistDmaAliasOpsPass(fold: bool = True)`
- `class DmaAllocInSymbolForHoistPattern()`
- `class DmaViewInSymbolForHoistPattern()`
- `class DmaReshapeInSymbolForHoistPattern()`
- `class DmaSubviewInSymbolForHoistPattern()`
- `get_symbol_buffer_hoist_patterns() -> list[RewritePattern]`
- `class SymbolBufferHoistPass(fold: bool = True)`
- `class SymbolHoistPipelinePass(fold: bool = True, cse: bool = True, canonicalize: bool = True)`
- `SymbolHoistPipelinePass.from_options(options: dict[str, str]) -> SymbolHoistPipelinePass`

使用示例:
- from kernel_gen.passes.hoist import SymbolHoistPipelinePass
- pass_obj = SymbolHoistPipelinePass(cse=True, canonicalize=True)

关联文件:
- spec: spec/pass/symbol_hoist_pipeline.md
- test: test/passes/test_symbol_hoist_pipeline.py
- 功能实现: kernel_gen/passes/hoist/symbol_hoist_pipeline.py
"""

from __future__ import annotations

from kernel_gen.passes.hoist.dma_alias_ops import (
    DmaAliasHoistPattern,
    DmaAliasThroughWriteNoReadPattern,
    HoistDmaAliasOpsPass,
    get_hoist_dma_alias_ops_pass_patterns,
)
from kernel_gen.passes.hoist.dma_alias_to_reinterpret import (
    DmaAliasToReinterpretPass,
    get_dma_alias_to_reinterpret_patterns,
)
from kernel_gen.passes.hoist.symbol_buffer_hoist import (
    DmaAllocInSymbolForHoistPattern,
    DmaReshapeInSymbolForHoistPattern,
    DmaSubviewInSymbolForHoistPattern,
    DmaViewInSymbolForHoistPattern,
    SymbolBufferHoistPass,
    get_symbol_buffer_hoist_patterns,
)
from kernel_gen.passes.hoist.symbol_hoist_pipeline import SymbolHoistPipelinePass
from kernel_gen.passes.hoist.symbol_loop_hoist import (
    SymbolLoopHoistPass,
    SymbolMaxHoistPattern,
    SymbolMinHoistPattern,
    get_symbol_loop_hoist_patterns,
)

__all__ = [
    "DmaAliasToReinterpretPass",
    "get_dma_alias_to_reinterpret_patterns",
    "SymbolLoopHoistPass",
    "SymbolMinHoistPattern",
    "SymbolMaxHoistPattern",
    "get_symbol_loop_hoist_patterns",
    "DmaAliasThroughWriteNoReadPattern",
    "DmaAliasHoistPattern",
    "get_hoist_dma_alias_ops_pass_patterns",
    "HoistDmaAliasOpsPass",
    "DmaAllocInSymbolForHoistPattern",
    "DmaViewInSymbolForHoistPattern",
    "DmaReshapeInSymbolForHoistPattern",
    "DmaSubviewInSymbolForHoistPattern",
    "get_symbol_buffer_hoist_patterns",
    "SymbolBufferHoistPass",
    "SymbolHoistPipelinePass",
]
