"""pass pattern public API and documentation tests.


功能说明:
- 锁定 `kernel_gen/passes/**` 下公开 `RewritePattern` class 的 canonical module path。
- 机械检查公开 getter 返回顺序和目标 spec 的 MLIR before / after 文档。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- `pytest -q --cov=kernel_gen.passes --cov-branch --cov-report=term-missing test/passes/test_pattern_public_api_docs.py`

使用示例:
- pytest -q test/passes/test_pattern_public_api_docs.py

关联文件:
- Spec 文档: ARCHITECTURE/plan/pass_pattern_public_api_refactor_green_plan.md
- 测试文件: test/passes/test_pattern_public_api_docs.py
"""

from __future__ import annotations

import ast
import importlib
import inspect
import re
from dataclasses import dataclass
from pathlib import Path

from xdsl.dialects.builtin import ModuleOp
from xdsl.pattern_rewriter import RewritePattern


@dataclass(frozen=True)
class _PatternModuleCase:
    module_name: str
    spec_path: str
    pattern_names: tuple[str, ...]
    getter_name: str | None = None
    getter_args_kind: str = "none"
    old_private_names: tuple[str, ...] = ()
    reject_patterns: tuple[str, ...] = ()
    implementation_module_name: str | None = None


_PATTERN_MODULE_CASES = (
    _PatternModuleCase(
        "kernel_gen.passes.arch_parallelize",
        "spec/pass/arch_parallelize.md",
        ("_ArchParallelizeFuncPattern",),
        implementation_module_name="kernel_gen.passes.arch_parallelize.arch_parallelize",
    ),
    _PatternModuleCase(
        "kernel_gen.passes.hoist_dma_alias_ops",
        "spec/pass/hoist_dma_alias_ops.md",
        ("DmaAliasThroughWriteNoReadPattern", "DmaAliasHoistPattern"),
        "get_hoist_dma_alias_ops_pass_patterns",
        "module",
        (
            "_DmaViewDesliceGroupingPattern",
            "_DmaReshapeThroughFillPattern",
            "DmaViewDesliceGroupingPattern",
            "DmaReshapeThroughFillPattern",
        ),
    ),
    _PatternModuleCase(
        "kernel_gen.passes.outline_device_kernel",
        "spec/pass/outline_device_kernel.md",
        ("OutlineDeviceKernelFuncPattern",),
        "get_outline_device_kernel_pass_patterns",
        "candidates",
        ("_OutlineDeviceKernelFuncPattern",),
    ),
    _PatternModuleCase(
        "kernel_gen.passes.symbol_buffer_hoist",
        "spec/pass/symbol_buffer_hoist.md",
        (
            "DmaAllocInSymbolForHoistPattern",
            "DmaViewInSymbolForHoistPattern",
            "DmaReshapeInSymbolForHoistPattern",
            "DmaSubviewInSymbolForHoistPattern",
        ),
        "get_symbol_buffer_hoist_patterns",
        "none",
        (
            "_DmaViewInSymbolForHoistPattern",
            "_DmaReshapeInSymbolForHoistPattern",
            "_DmaSubviewInSymbolForHoistPattern",
        ),
    ),
    _PatternModuleCase(
        "kernel_gen.passes.symbol_loop_hoist",
        "spec/pass/symbol_loop_hoist.md",
        (
            "SymbolConstHoistPattern",
            "TunerParamHoistPattern",
            "SymbolGetDimHoistPattern",
            "SymbolGetStrideHoistPattern",
            "SymbolAddHoistPattern",
            "SymbolSubHoistPattern",
            "SymbolMulHoistPattern",
            "SymbolDivHoistPattern",
            "SymbolFloorDivHoistPattern",
            "SymbolMinHoistPattern",
            "SymbolMaxHoistPattern",
            "ArithConstantHoistPattern",
            "MemoryGetDataHoistPattern",
            "SymbolCastHoistPattern",
            "SymbolNeHoistPattern",
        ),
        "get_symbol_loop_hoist_patterns",
    ),
    _PatternModuleCase(
        "kernel_gen.passes.buffer_results_to_out_params",
        "spec/pass/buffer_results_to_out_params.md",
        ("BufferResultsToOutParamsCallPattern", "BufferResultsToOutParamsFuncPattern"),
        "get_buffer_results_to_out_params_pass_patterns",
        "targets",
    ),
    _PatternModuleCase(
        "kernel_gen.passes.decompass",
        "spec/pass/decompass.md",
        ("NnSoftmaxDecompPattern",),
        "get_decompass_pass_patterns",
    ),
    _PatternModuleCase(
        "kernel_gen.passes.tile.analysis",
        "spec/pass/tile/analysis.md",
        ("TileAnalysisBinaryPattern", "TileAnalysisBroadcastPattern", "TileAnalysisMatmulPattern"),
        "get_tile_analysis_pass_patterns",
    ),
    _PatternModuleCase(
        "kernel_gen.passes.tile.elewise",
        "spec/pass/tile/elewise.md",
        ("TileElewiseBinaryPattern", "TileElewiseBroadcastPattern", "TileElewiseMatmulPattern"),
        "get_tile_elewise_pass_patterns",
    ),
    _PatternModuleCase(
        "kernel_gen.passes.tile.reduce",
        "spec/pass/tile/reduce.md",
        ("TileReduceMatmulPattern",),
        "get_tile_reduce_pass_patterns",
    ),
    _PatternModuleCase(
        "kernel_gen.passes.lowering.nn_lowering.nn_lowering",
        "spec/pass/lowering/nn_lowering/spec.md",
        ("RejectUnsupportedNnOpPattern",),
        "nn_lowering_patterns",
        "none",
        ("_RejectUnsupportedNnOpPattern",),
        ("RejectUnsupportedNnOpPattern",),
    ),
    _PatternModuleCase(
        "kernel_gen.passes.lowering.nn_lowering.element_binary_lowering",
        "spec/pass/lowering/nn_lowering/element_binary_lowering.md",
        (
            "LowerNnAddPattern",
            "LowerNnSubPattern",
            "LowerNnMulPattern",
            "LowerNnDivPattern",
            "LowerNnTrueDivPattern",
            "LowerNnEqPattern",
            "LowerNnNePattern",
            "LowerNnLtPattern",
            "LowerNnLePattern",
            "LowerNnGtPattern",
            "LowerNnGePattern",
        ),
        "element_binary_patterns",
        "none",
        (
            "_LowerNnAddPattern",
            "_LowerNnSubPattern",
            "_LowerNnMulPattern",
            "_LowerNnDivPattern",
            "_LowerNnTrueDivPattern",
            "_LowerNnEqPattern",
            "_LowerNnNePattern",
            "_LowerNnLtPattern",
            "_LowerNnLePattern",
            "_LowerNnGtPattern",
            "_LowerNnGePattern",
        ),
    ),
    _PatternModuleCase(
        "kernel_gen.passes.lowering.nn_lowering.select_cast_lowering",
        "spec/pass/lowering/nn_lowering/select_cast_lowering.md",
        ("LowerSelectPattern", "LowerCastPattern", "LowerExpPattern"),
        "select_cast_patterns",
        "none",
        ("_LowerSelectPattern", "_LowerCastPattern", "_LowerExpPattern"),
    ),
    _PatternModuleCase(
        "kernel_gen.passes.lowering.nn_lowering.dma_structured_lowering",
        "spec/pass/lowering/nn_lowering/dma_structured_lowering.md",
        ("LowerNnBroadcastPattern", "LowerNnTransposePattern"),
        "dma_structured_patterns",
        "none",
        ("_LowerNnBroadcastPattern", "_LowerNnTransposePattern"),
    ),
    _PatternModuleCase(
        "kernel_gen.passes.lowering.nn_lowering.matmul_img2col_lowering",
        "spec/pass/lowering/nn_lowering/matmul_img2col_lowering.md",
        ("LowerNnMatmulPattern", "LowerNnImg2col1dPattern", "LowerNnImg2col2dPattern"),
        "matmul_img2col_patterns",
        "none",
        ("_LowerNnMatmulPattern", "_LowerNnImg2col1dPattern", "_LowerNnImg2col2dPattern"),
    ),
    _PatternModuleCase(
        "kernel_gen.passes.lowering.nn_lowering.reduce_softmax_lowering",
        "spec/pass/lowering/nn_lowering/reduce_softmax_lowering.md",
        (
            "LowerNnReduceSumPattern",
            "LowerNnReduceMinPattern",
            "LowerNnReduceMaxPattern",
            "RejectNnSoftmaxPattern",
        ),
        "reduce_softmax_patterns",
        "none",
        (
            "_LowerNnReduceSumPattern",
            "_LowerNnReduceMinPattern",
            "_LowerNnReduceMaxPattern",
            "_RejectNnSoftmaxPattern",
        ),
        ("RejectNnSoftmaxPattern",),
    ),
)

_IMPLEMENTATION_DOC_TOKENS = {
    "_ArchParallelizeFuncPattern": ("func.func", "symbol.for", "arch.get_block_id", "scf.if"),
    "DmaAliasThroughWriteNoReadPattern": (
        "MemoryEffectKind.WRITE",
        "dma.broadcast",
        "dma.reshape",
        "dma.view",
        "dma.reinterpret",
    ),
    "DmaAliasHoistPattern": ("dma.view", "dma.reshape", "dma.reinterpret", "symbol.for"),
    "OutlineDeviceKernelFuncPattern": ("func.func", "arch.launch"),
    "DmaAllocInSymbolForHoistPattern": ("dma.alloc", "dma.free"),
    "DmaViewInSymbolForHoistPattern": ("dma.view",),
    "DmaReshapeInSymbolForHoistPattern": ("dma.reshape",),
    "DmaSubviewInSymbolForHoistPattern": ("dma.subview",),
    "SymbolConstHoistPattern": ("symbol.const",),
    "TunerParamHoistPattern": ("tuner.param",),
    "SymbolGetDimHoistPattern": ("symbol.get_dim",),
    "SymbolGetStrideHoistPattern": ("symbol.get_stride",),
    "SymbolAddHoistPattern": ("symbol.add",),
    "SymbolSubHoistPattern": ("symbol.sub",),
    "SymbolMulHoistPattern": ("symbol.mul",),
    "SymbolDivHoistPattern": ("symbol.div",),
    "SymbolFloorDivHoistPattern": ("symbol.floordiv",),
    "SymbolMinHoistPattern": ("symbol.min",),
    "SymbolMaxHoistPattern": ("symbol.max",),
    "ArithConstantHoistPattern": ("arith.constant", "symbol.for"),
    "MemoryGetDataHoistPattern": ("memory.get_data", "symbol.for"),
    "SymbolCastHoistPattern": ("symbol.cast", "symbol.for"),
    "SymbolNeHoistPattern": ("symbol.ne", "symbol.for"),
    "BufferResultsToOutParamsCallPattern": ("func.call",),
    "BufferResultsToOutParamsFuncPattern": ("func.func", "func.return"),
    "NnSoftmaxDecompPattern": ("nn.softmax", "nn.reduce_max", "nn.truediv"),
    "TileAnalysisBinaryPattern": ("kernel.binary_elewise", "tile.analysis"),
    "TileAnalysisBroadcastPattern": ("dma.broadcast", "tile.analysis"),
    "TileAnalysisMatmulPattern": ("kernel.matmul", "tile.analysis"),
    "TileElewiseBinaryPattern": ("kernel.binary_elewise", "symbol.for"),
    "TileElewiseBroadcastPattern": ("dma.broadcast", "symbol.for"),
    "TileElewiseMatmulPattern": ("kernel.matmul", "symbol.for"),
    "TileReduceMatmulPattern": ("kernel.matmul", "symbol.for"),
    "RejectUnsupportedNnOpPattern": ("nn.", "unknown op"),
    "LowerNnAddPattern": ("nn.add", 'kind="add"'),
    "LowerNnSubPattern": ("nn.sub", 'kind="sub"'),
    "LowerNnMulPattern": ("nn.mul", 'kind="mul"'),
    "LowerNnDivPattern": ("nn.div", 'kind="div"'),
    "LowerNnTrueDivPattern": ("nn.truediv", 'kind="div"'),
    "LowerNnEqPattern": ("nn.eq", 'kind="eq"'),
    "LowerNnNePattern": ("nn.ne", 'kind="ne"'),
    "LowerNnLtPattern": ("nn.lt", 'kind="lt"'),
    "LowerNnLePattern": ("nn.le", 'kind="le"'),
    "LowerNnGtPattern": ("nn.gt", 'kind="gt"'),
    "LowerNnGePattern": ("nn.ge", 'kind="ge"'),
    "LowerSelectPattern": ("nn.select", "kernel.select"),
    "LowerCastPattern": ("nn.cast", "dma.cast"),
    "LowerExpPattern": ("nn.exp", "kernel.exp"),
    "LowerNnBroadcastPattern": ("nn.broadcast", "dma.broadcast"),
    "LowerNnTransposePattern": ("nn.transpose", "dma.transpose"),
    "LowerNnMatmulPattern": ("nn.matmul", "kernel.matmul"),
    "LowerNnImg2col1dPattern": ("nn.img2col1d", "kernel.img2col1d"),
    "LowerNnImg2col2dPattern": ("nn.img2col2d", "kernel.img2col2d"),
    "LowerNnReduceSumPattern": ("nn.reduce_sum", 'kind="sum"'),
    "LowerNnReduceMinPattern": ("nn.reduce_min", 'kind="min"'),
    "LowerNnReduceMaxPattern": ("nn.reduce_max", 'kind="max"'),
    "RejectNnSoftmaxPattern": ("nn.softmax", "nn.softmax must be decomposed before lower-nn"),
}


def _section_text(text: str, start_marker: str, next_marker: str) -> str:
    """截取文档中两个标题 / 小节标记之间的文本。"""

    start = text.find(start_marker)
    assert start >= 0, f"missing section marker {start_marker!r}"
    end = text.find(next_marker, start + len(start_marker))
    assert end >= 0, f"missing next marker {next_marker!r}"
    return text[start:end]


def _module_source_and_doc(module_name: str) -> tuple[str, str]:
    """读取 module 源码与文件级 docstring。"""

    module = importlib.import_module(module_name)
    source_path = inspect.getsourcefile(module)
    assert source_path is not None, f"{module_name}: missing source file"
    source_text = Path(source_path).read_text(encoding="utf-8")
    module_doc = ast.get_docstring(ast.parse(source_text)) or ""
    return source_text, module_doc


def _annotation_text(annotation: ast.expr | None) -> str:
    """把源码注解 AST 还原为 API 列表使用的短签名文本。"""

    assert annotation is not None, "public pattern method annotations must be explicit"
    if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
        return annotation.value
    return ast.unparse(annotation)


def _pattern_method_signature(source_text: str, pattern_name: str) -> str:
    """从实现源码中提取公开 pattern 的 `match_and_rewrite(...)` 签名。"""

    module_ast = ast.parse(source_text)
    for node in module_ast.body:
        if not isinstance(node, ast.ClassDef) or node.name != pattern_name:
            continue
        for class_item in node.body:
            if not isinstance(class_item, ast.FunctionDef) or class_item.name != "match_and_rewrite":
                continue
            args = list(class_item.args.posonlyargs) + list(class_item.args.args)
            args_by_name = {arg.arg: arg for arg in args}
            op_arg = args_by_name["op"]
            rewriter_arg = args_by_name["rewriter"]
            return_annotation = _annotation_text(class_item.returns)
            return (
                f"{pattern_name}.match_and_rewrite("
                f"op: {_annotation_text(op_arg.annotation)}, "
                f"rewriter: {_annotation_text(rewriter_arg.annotation)}) -> {return_annotation}"
            )
    raise AssertionError(f"{pattern_name}: missing match_and_rewrite source definition")


def _getter_args(kind: str) -> tuple[object, ...]:
    """构造 getter 测试所需公开参数。"""

    if kind == "module":
        return (ModuleOp([]),)
    if kind == "candidates":
        return ({},)
    if kind == "targets":
        return ({},)
    return ()


def test_pass_pattern_public_api_imports_and_getter_order() -> None:
    """验证 pattern 公开路径、`__all__` 与 getter 顺序。"""

    for case in _PATTERN_MODULE_CASES:
        module = importlib.import_module(case.module_name)
        exported = set(getattr(module, "__all__", ()))
        for pattern_name in case.pattern_names:
            pattern_cls = getattr(module, pattern_name)
            assert issubclass(pattern_cls, RewritePattern)
            assert pattern_name in exported
            assert pattern_cls.__module__ == case.module_name
        for old_name in case.old_private_names:
            assert not hasattr(module, old_name), f"{case.module_name}.{old_name} must stay private-name-free"
        if case.getter_name is None:
            continue
        getter = getattr(module, case.getter_name)
        assert case.getter_name in exported
        patterns = getter(*_getter_args(case.getter_args_kind))
        if case.getter_name == "nn_lowering_patterns":
            assert type(patterns[-1]).__name__ == "RejectUnsupportedNnOpPattern"
            continue
        actual_pattern_names = [type(pattern).__name__ for pattern in patterns]
        public_pattern_names = [name for name in actual_pattern_names if not name.startswith("_")]
        assert public_pattern_names == list(case.pattern_names)
        fresh_patterns = getter(*_getter_args(case.getter_args_kind))
        assert patterns is not fresh_patterns
        assert all(left is not right for left, right in zip(patterns, fresh_patterns, strict=True))


def test_pass_pattern_docs_have_mlir_before_after_contracts() -> None:
    """验证目标 spec 为每个公开 pattern 写出 MLIR before/after 或 reject 合同。"""

    repo_root = Path(__file__).resolve().parents[2]
    for case in _PATTERN_MODULE_CASES:
        spec_text = (repo_root / case.spec_path).read_text(encoding="utf-8")
        for pattern_name in case.pattern_names:
            windows = [spec_text[match.start() : match.start() + 3000] for match in re.finditer(pattern_name, spec_text)]
            assert windows, f"{case.spec_path}: missing {pattern_name}"
            for token in _IMPLEMENTATION_DOC_TOKENS[pattern_name]:
                assert any(token in window for window in windows), (
                    f"{case.spec_path}: {pattern_name} missing pattern-specific token {token!r}"
                )
            if pattern_name in case.reject_patterns:
                assert any("before" in window and "```mlir" in window and "公开错误文本" in window for window in windows), (
                    f"{case.spec_path}: {pattern_name} missing reject before mlir or public error text"
                )
            else:
                assert any(
                    "before" in window and "after" in window and window.count("```mlir") >= 2
                    for window in windows
                ), f"{case.spec_path}: {pattern_name} missing before/after mlir blocks"


def test_pass_pattern_api_lists_include_public_methods() -> None:
    """验证 spec API 与实现文件级 API 列表列出公开 pattern 方法签名。"""

    repo_root = Path(__file__).resolve().parents[2]
    for case in _PATTERN_MODULE_CASES:
        implementation_module_name = case.implementation_module_name or case.module_name
        source_text, module_doc = _module_source_and_doc(implementation_module_name)
        spec_text = (repo_root / case.spec_path).read_text(encoding="utf-8")
        spec_api_list = _section_text(spec_text, "## API 列表", "## 文档信息")
        module_api_list = _section_text(module_doc, "API 列表:", "使用示例:")
        for pattern_name in case.pattern_names:
            class_api = f"class {pattern_name}("
            signature = _pattern_method_signature(source_text, pattern_name)
            assert class_api in spec_api_list, f"{case.spec_path}: missing {class_api}"
            assert signature in spec_api_list, f"{case.spec_path}: missing {signature}"
            assert class_api in module_api_list, f"{case.module_name}: missing {class_api}"
            assert signature in module_api_list, f"{implementation_module_name}: missing {signature}"


def test_pass_pattern_implementation_docstrings_have_ir_contracts() -> None:
    """验证实现侧 pattern class docstring 也写出 IR before/after 或 reject 合同。"""

    for case in _PATTERN_MODULE_CASES:
        implementation_module_name = case.implementation_module_name or case.module_name
        module = importlib.import_module(implementation_module_name)
        for pattern_name in case.pattern_names:
            pattern_cls = getattr(module, pattern_name)
            doc = inspect.getdoc(pattern_cls) or ""
            assert "IR before:" in doc, f"{implementation_module_name}.{pattern_name}: missing IR before"
            for token in _IMPLEMENTATION_DOC_TOKENS[pattern_name]:
                assert token in doc, f"{implementation_module_name}.{pattern_name}: missing doc token {token!r}"
            if pattern_name in case.reject_patterns:
                assert "公开错误文本" in doc, f"{implementation_module_name}.{pattern_name}: missing public error text"
                assert doc.count("```mlir") >= 1, f"{implementation_module_name}.{pattern_name}: missing reject mlir block"
                continue
            assert "IR after:" in doc, f"{implementation_module_name}.{pattern_name}: missing IR after"
            assert doc.count("```mlir") >= 2, f"{implementation_module_name}.{pattern_name}: missing before/after mlir blocks"
