"""pass package.


功能说明:
- 暴露 Pass 管理相关实现。
- 暴露 `inline` 的公开入口。
- 暴露 `attach-arch-information` 的公开入口。
- 暴露 `buffer-results-to-out-params` 的公开入口。
- 暴露 `decompass` 专题 pass 的根路径入口。
- 暴露 `outline-device-kernel` 的公开入口。
- 暴露 `symbol-buffer-hoist` 的公开入口与 pattern API。
- 暴露 `symbol-loop-hoist` 专题 pass 的根路径入口。
- 暴露 `template-name-infer` 的公开入口。
- 暴露 `tile-analysis` 的公开入口与 pattern API。
- 暴露 `tile-elewise` 的公开入口与 pattern API。
- 暴露 `tile-reduce` 的公开入口与 pattern API。

API 列表:
- `class Pass()`
- `class PassManager(name: str | None = None)`
- `PassManager.add_pass(self: PassManager, pass_obj: XdslModulePass) -> None`
- `PassManager.extend(self: PassManager, passes: Sequence[XdslModulePass]) -> None`
- `PassManager.run(self: PassManager, target: ModuleOp) -> ModuleOp`
- `class InlinePass()`
- `class AttachArchInformationPass(target: str = "npu_demo")`
- `class BufferResultsToOutParamsPass()`
- `class BufferResultsToOutParamsCallPattern(targets: dict[str, RewriteTarget])`
- `class BufferResultsToOutParamsFuncPattern(targets: dict[str, RewriteTarget])`
- `get_buffer_results_to_out_params_pass_patterns(targets: dict[str, RewriteTarget]) -> list[RewritePattern]`
- `class DecompassPass()`
- `class NnSoftmaxDecompPattern()`
- `get_decompass_pass_patterns() -> list[RewritePattern]`
- `class OutlineDeviceKernelPass()`
- `class DmaAllocInSymbolForHoistPattern()`
- `get_symbol_buffer_hoist_patterns() -> list[RewritePattern]`
- `class SymbolBufferHoistPass()`
- `class TileAnalysisBinaryPattern()`
- `class TileAnalysisBroadcastPattern()`
- `class TileAnalysisMatmulPattern()`
- `class TileAnalysisPass()`
- `get_tile_analysis_pass_patterns() -> list[RewritePattern]`
- `class TileElewiseBinaryPattern()`
- `class TileElewiseBroadcastPattern()`
- `class TileElewiseMatmulPattern()`
- `class TileElewisePass()`
- `get_tile_elewise_pass_patterns() -> list[RewritePattern]`
- `class TileReduceMatmulPattern()`
- `class TileReducePass()`
- `get_tile_reduce_pass_patterns() -> list[RewritePattern]`
- `class SymbolLoopHoistPass()`
- `class TemplateNameInferPass(fold: bool = True)`

使用示例:
- import importlib
- pass_module = importlib.import_module("kernel_gen.passes.pass_manager")
- Pass, PassManager = pass_module.Pass, pass_module.PassManager
- from kernel_gen.passes import BufferResultsToOutParamsPass, DecompassPass
- buffer_pass = BufferResultsToOutParamsPass()
- decompass_pass = DecompassPass()
- from kernel_gen.passes import InlinePass
- inline_pass = InlinePass()
- from kernel_gen.passes import AttachArchInformationPass
- attach_pass = AttachArchInformationPass(target="npu_demo")
- from kernel_gen.passes import OutlineDeviceKernelPass
- outline_pass = OutlineDeviceKernelPass()
- from kernel_gen.passes import DmaAllocInSymbolForHoistPattern, SymbolBufferHoistPass
- symbol_buffer_patterns = get_symbol_buffer_hoist_patterns()
- symbol_buffer_pass = SymbolBufferHoistPass()
- from kernel_gen.passes import TileAnalysisPass, TileAnalysisBinaryPattern
- tile_analysis_pass = TileAnalysisPass()
- from kernel_gen.passes import TileElewisePass, TileReducePass
- tile_elewise_pass = TileElewisePass()
- tile_reduce_pass = TileReducePass()
- from kernel_gen.passes import SymbolLoopHoistPass
- hoist_pass = SymbolLoopHoistPass()
- from kernel_gen.passes import TemplateNameInferPass
- infer_pass = TemplateNameInferPass()

关联文件:
- spec:
  - spec/pass/pass_manager.md
  - spec/pass/decompass.md
  - spec/pass/buffer_results_to_out_params.md
  - spec/pass/inline.md
  - spec/pass/attach_arch_information.md
  - spec/pass/outline_device_kernel.md
  - spec/pass/symbol_loop_hoist.md
- test:
  - test/passes/test_pass_manager.py
  - test/passes/test_inline.py
  - test/passes/test_attach_arch_information.py
  - test/passes/test_buffer_results_to_out_params.py
  - test/passes/decompass/test_softmax.py
  - test/passes/test_outline_device_kernel.py
- test/passes/tile/test_analysis.py
- test/passes/tile/test_elewise.py
- test/passes/tile/test_reduce.py
- test/passes/test_symbol_loop_hoist.py
- 功能实现:
  - kernel_gen/passes/pass_manager.py
  - kernel_gen/passes/common.py
  - kernel_gen/passes/inline.py
  - kernel_gen/passes/attach_arch_information.py
  - kernel_gen/passes/buffer_results_to_out_params.py
  - kernel_gen/passes/decompass.py
- kernel_gen/passes/outline_device_kernel.py
- kernel_gen/passes/symbol_buffer_hoist.py
- kernel_gen/passes/template_name_infer.py
  - kernel_gen/passes/tile/analysis.py
  - kernel_gen/passes/tile/elewise.py
  - kernel_gen/passes/tile/reduce.py
- kernel_gen/passes/symbol_loop_hoist.py
"""

from .buffer_results_to_out_params import (
    BufferResultsToOutParamsPass,
    BufferResultsToOutParamsCallPattern,
    BufferResultsToOutParamsFuncPattern,
    get_buffer_results_to_out_params_pass_patterns,
)
from .attach_arch_information import AttachArchInformationPass
from .decompass import (
    DecompassPass,
    NnSoftmaxDecompPattern,
    get_decompass_pass_patterns,
)
from .inline import InlinePass
from .outline_device_kernel import OutlineDeviceKernelPass
from .symbol_buffer_hoist import (
    DmaAllocInSymbolForHoistPattern,
    SymbolBufferHoistPass,
    get_symbol_buffer_hoist_patterns,
)
from .tile.analysis import (
    TileAnalysisBinaryPattern,
    TileAnalysisBroadcastPattern,
    TileAnalysisMatmulPattern,
    TileAnalysisPass,
    get_tile_analysis_pass_patterns,
)
from .tile.elewise import (
    TileElewiseBinaryPattern,
    TileElewiseBroadcastPattern,
    TileElewiseMatmulPattern,
    TileElewisePass,
    get_tile_elewise_pass_patterns,
)
from .tile.reduce import TileReducePass
from .tile.reduce import TileReduceMatmulPattern, get_tile_reduce_pass_patterns
from .pass_manager import Pass, PassManager
from .symbol_loop_hoist import SymbolLoopHoistPass
from .template_name_infer import TemplateNameInferPass

__all__ = [
    "Pass",
    "PassManager",
    "InlinePass",
    "AttachArchInformationPass",
    "BufferResultsToOutParamsPass",
    "BufferResultsToOutParamsCallPattern",
    "BufferResultsToOutParamsFuncPattern",
    "get_buffer_results_to_out_params_pass_patterns",
    "DecompassPass",
    "NnSoftmaxDecompPattern",
    "get_decompass_pass_patterns",
    "OutlineDeviceKernelPass",
    "DmaAllocInSymbolForHoistPattern",
    "get_symbol_buffer_hoist_patterns",
    "SymbolBufferHoistPass",
    "TileAnalysisBinaryPattern",
    "TileAnalysisBroadcastPattern",
    "TileAnalysisMatmulPattern",
    "TileAnalysisPass",
    "get_tile_analysis_pass_patterns",
    "TileElewiseBinaryPattern",
    "TileElewiseBroadcastPattern",
    "TileElewiseMatmulPattern",
    "TileElewisePass",
    "get_tile_elewise_pass_patterns",
    "TileReduceMatmulPattern",
    "TileReducePass",
    "get_tile_reduce_pass_patterns",
    "SymbolLoopHoistPass",
    "TemplateNameInferPass",
]
