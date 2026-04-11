"""DSL AST facade.

创建者: 小李飞刀
最后一次更改: 朽木露琪亚

功能说明:
- 提供 facade 导入路径，聚合 AST 节点与解析入口。
- 保持 `kernel_gen.dsl.ast` 的历史导入方式不变。

使用示例:
- from kernel_gen.dsl.ast import FunctionAST, parse_function
- func_ast = parse_function(kernel)

关联文件:
- spec: spec/dsl/ast.md
- test: test/dsl/test_ast.py
- 功能实现: kernel_gen/dsl/ast.py
"""

from __future__ import annotations

from .ast_nodes import (
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
from .ast_parser import AstParseError, _ParseFailure, _parse_function_impl, parse_function

__all__ = [
    "ArchBarrierAST",
    "ArchGetDynamicMemoryAST",
    "ArchLaunchKernelAST",
    "ArchQueryAST",
    "AstParseError",
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
    "_ParseFailure",
    "_parse_function_impl",
    "parse_function",
]
