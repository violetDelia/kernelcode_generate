"""DSL AST package facade tests.


功能说明:
- 覆盖 `kernel_gen.dsl.ast` 包根公开 API。
- 测试结构对应 `spec/dsl/ast/__init__.md` 与 `kernel_gen/dsl/ast/__init__.py`。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- `pytest -q --cov=kernel_gen.dsl.ast --cov-branch --cov-report=term-missing test/dsl/ast/test_package.py`

使用示例:
- `pytest -q test/dsl/ast/test_package.py`

关联文件:
- 功能实现: `kernel_gen/dsl/ast/__init__.py`
- Spec 文档: `spec/dsl/ast/__init__.md`
- 测试文件: `test/dsl/ast/test_package.py`
"""

from __future__ import annotations

import importlib


def test_ast_package_exports_only_current_public_nodes() -> None:
    """包根导出当前公开节点，不继续暴露旧中间节点或非公开 helper。"""

    facade = importlib.import_module("kernel_gen.dsl.ast")
    expected_public = (
        "AttrAST",
        "IntTypeAttrAST",
        "FloatTypeAttrAST",
        "BoolTypeAttrAST",
        "MemorySpaceAttrAST",
        "MemoryAST",
        "SymbolDimAST",
        "ConstValueAST",
        "BoolValueAST",
        "SymbolListAST",
        "BoundExprAST",
        "CallAST",
        "DmaBroadcastAST",
        "DmaFillAST",
        "DmaLoadAST",
        "DmaSliceAST",
        "DmaStoreAST",
        "DmaDesliceAST",
        "NnAddAST",
        "NnReduceAST",
        "ArchGetThreadNumAST",
        "KernelBinaryElewiseAST",
        "KernelAddAST",
        "KernelExpAST",
        "KernelReduceAST",
        "KernelMatmulAST",
        "KernelImg2Col2dAST",
        "parse_function",
        "DslAstVisitor",
    )

    for name in expected_public:
        assert hasattr(facade, name)
        assert name in facade.__all__
    for name in (
        "LoadAST",
        "StoreAST",
        "build_func_op",
        "build_func_op_from_ast",
        "parse_function_with_env",
        "parse",
        "TensorAST",
        "ScalarArgAST",
        "ConstAST",
        "BinaryExprAST",
        "CompareExprAST",
        "ShapeListAST",
        "DTypeAttrAST",
        "MemoryAttrAST",
    ):
        assert not hasattr(facade, name)
        assert name not in facade.__all__
