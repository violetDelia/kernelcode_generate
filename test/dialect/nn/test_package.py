"""nn dialect package root tests.

功能说明:
- 验证 nn dialect package 拆分后对应 family 的公开行为不变。

使用示例:
- pytest -q test/dialect/nn/test_package.py

关联文件:
- 功能实现: kernel_gen/dialect/nn/
- Spec 文档: spec/dialect/nn.md
- 测试文件: test/dialect/nn/test_package.py
"""

from __future__ import annotations

import importlib
from pathlib import Path

from kernel_gen.dialect.nn import Nn, NnAddOp, NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect import Nn as PackageNn, NnAddOp as PackageNnAddOp

EXPECTED_NN_ALL = {
    "Nn",
    "NnAddOp",
    "NnSubOp",
    "NnMulOp",
    "NnDivOp",
    "NnTrueDivOp",
    "NnFloorDivOp",
    "NnEqOp",
    "NnNeOp",
    "NnLtOp",
    "NnLeOp",
    "NnGtOp",
    "NnGeOp",
    "NnSelectOp",
    "NnCastOp",
    "NnBroadcastOp",
    "NnTransposeOp",
    "NnReluOp",
    "NnSigmoidOp",
    "NnTanhOp",
    "NnLeakyReluOp",
    "NnHardSigmoidOp",
    "NnSoftmaxOp",
    "NnExpOp",
    "NnReduceSumOp",
    "NnReduceMinOp",
    "NnReduceMaxOp",
    "NnImg2col1dOp",
    "NnImg2col2dOp",
    "NnMatmulOp",
    "NnMemorySpaceAttr",
    "NnMemoryType",
    "copy_memory_type",
    "copy_memory_type_with_template_name",
}

EXPECTED_DIALECT_NN_SUBSET = {
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
    "copy_memory_type",
    "copy_memory_type_with_template_name",
}

EXPECTED_OPS = [
    "NnAddOp",
    "NnSubOp",
    "NnMulOp",
    "NnDivOp",
    "NnTrueDivOp",
    "NnFloorDivOp",
    "NnEqOp",
    "NnNeOp",
    "NnLtOp",
    "NnLeOp",
    "NnGtOp",
    "NnGeOp",
    "NnSelectOp",
    "NnCastOp",
    "NnBroadcastOp",
    "NnTransposeOp",
    "NnReluOp",
    "NnSigmoidOp",
    "NnTanhOp",
    "NnLeakyReluOp",
    "NnHardSigmoidOp",
    "NnSoftmaxOp",
    "NnExpOp",
    "NnReduceSumOp",
    "NnReduceMinOp",
    "NnReduceMaxOp",
    "NnImg2col1dOp",
    "NnImg2col2dOp",
    "NnMatmulOp",
]


def test_package_root_and_submodule_imports() -> None:
    required = [
        "kernel_gen.dialect.nn",
        "kernel_gen.dialect.nn.attr.space_attr",
        "kernel_gen.dialect.nn.type.memory_type",
        "kernel_gen.dialect.nn.operation.binary",
        "kernel_gen.dialect.nn.operation.elewise",
        "kernel_gen.dialect.nn.operation.active",
        "kernel_gen.dialect.nn.operation.reduce",
        "kernel_gen.dialect.nn.operation.structured",
    ]
    for name in required:
        importlib.import_module(name)
    assert Nn is PackageNn
    assert NnAddOp is PackageNnAddOp
    assert NnMemorySpaceAttr.__name__ == "NnMemorySpaceAttr"
    assert NnMemoryType.__name__ == "NnMemoryType"


def test_nn_package_root_exact_exports_and_registration_order() -> None:
    nn_module = importlib.import_module("kernel_gen.dialect.nn")
    assert set(nn_module.__all__) == EXPECTED_NN_ALL
    assert [op.__name__ for op in Nn.operations] == EXPECTED_OPS
    assert [attr.__name__ for attr in Nn.attributes] == ["NnMemorySpaceAttr", "NnMemoryType"]


def test_dialect_package_exact_nn_subset_identity() -> None:
    dialect_module = importlib.import_module("kernel_gen.dialect")
    nn_module = importlib.import_module("kernel_gen.dialect.nn")
    assert EXPECTED_DIALECT_NN_SUBSET <= set(dialect_module.__all__)
    for name in EXPECTED_DIALECT_NN_SUBSET:
        assert getattr(dialect_module, name) is getattr(nn_module, name)


def test_old_nn_single_file_and_old_test_entry_are_removed() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    assert not (repo_root / "kernel_gen/dialect" / "nn.py").exists()
    assert (repo_root / "kernel_gen/dialect/nn").is_dir()
    assert not (repo_root / "test/dialect" / "test_nn.py").exists()
    assert (repo_root / "test/dialect/nn").is_dir()
