"""DSL AST package facade.

创建者: 小李飞刀
最后一次更改: 榕

功能说明:
- 聚合 AST 节点与解析入口，提供稳定的 `kernel_gen.dsl.ast` 导入路径。
- 只做导出，不在本文件内实现节点定义或解析逻辑。

API 列表:
- `parse_function(fn: object) -> FunctionAST`
- `FunctionAST` / `BlockAST` / `ForAST` / `IfAST`
- `TensorAST` / `ScalarArgAST` / `PtrArgAST` / `VarAST` / `ConstAST`
- `Diagnostic` / `SourceLocation`
- 其余公开 AST 节点类由 `kernel_gen.dsl.ast.nodes` 定义并经本包根导出。

使用示例:
- from kernel_gen.dsl.ast import FunctionAST, parse_function
- func_ast = parse_function(kernel)

关联文件:
- spec: spec/dsl/ast/__init__.md
- test: test/dsl/ast/test_parser.py
- 功能实现: kernel_gen/dsl/ast/__init__.py
"""

from __future__ import annotations

from .nodes import (
    ArchBarrierAST,
    ArchGetDynamicMemoryAST,
    ArchLaunchKernelAST,
    ArchQueryAST,
    BinaryExprAST,
    BlockAST,
    CompareExprAST,
    ConstAST,
    ConvAST,
    Diagnostic,
    DmaAllocAST,
    DmaCastAST,
    DmaCopyAST,
    DmaFlattenAST,
    DmaFreeAST,
    DmaReshapeAST,
    DmaViewAST,
    FCAST,
    ForAST,
    FunctionAST,
    IfAST,
    Img2ColAST,
    LoadAST,
    MatmulAST,
    ModuleAST,
    NnBroadcastAST,
    NnBroadcastToAST,
    NnReduceAST,
    NnSoftmaxAST,
    NnTransposeAST,
    NnUnaryAST,
    PtrArgAST,
    PythonCalleeCallAST,
    ScalarArgAST,
    SourceLocation,
    StoreAST,
    SymbolToFloatAST,
    TensorAST,
    TensorAxisAccessAST,
    VarAST,
)
from .parser import parse_function

__all__ = [
    "ArchBarrierAST",
    "ArchGetDynamicMemoryAST",
    "ArchLaunchKernelAST",
    "ArchQueryAST",
    "BinaryExprAST",
    "BlockAST",
    "CompareExprAST",
    "ConstAST",
    "ConvAST",
    "Diagnostic",
    "DmaAllocAST",
    "DmaCastAST",
    "DmaCopyAST",
    "DmaFlattenAST",
    "DmaFreeAST",
    "DmaReshapeAST",
    "DmaViewAST",
    "FCAST",
    "ForAST",
    "FunctionAST",
    "IfAST",
    "Img2ColAST",
    "LoadAST",
    "MatmulAST",
    "ModuleAST",
    "NnBroadcastAST",
    "NnBroadcastToAST",
    "NnReduceAST",
    "NnSoftmaxAST",
    "NnTransposeAST",
    "NnUnaryAST",
    "PtrArgAST",
    "PythonCalleeCallAST",
    "ScalarArgAST",
    "SourceLocation",
    "StoreAST",
    "SymbolToFloatAST",
    "TensorAST",
    "TensorAxisAccessAST",
    "VarAST",
    "parse_function",
]
