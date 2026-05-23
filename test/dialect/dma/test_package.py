"""dma dialect package root tests.

功能说明:
- 验证 `kernel_gen.dialect.dma` root API exact set、Dialect 注册顺序和 package-internal 模块边界。

使用示例:
- `pytest -q test/dialect/dma/test_package.py`

关联文件:
- spec: spec/dialect/dma.md
- 功能实现: kernel_gen/dialect/dma/
- 测试文件: test/dialect/dma/test_package.py
"""

from __future__ import annotations

import ast
import importlib
import inspect
from pathlib import Path
from types import ModuleType

import pytest
from xdsl.traits import HasCanonicalizationPatternsTrait, MemoryEffect

import kernel_gen.dialect as dialect_root
from kernel_gen.dialect import dma


EXPECTED_ROOT_EXPORTS = [
    "Dma",
    "DmaAllocOp",
    "DmaFillOp",
    "DmaFreeOp",
    "DmaCopyOp",
    "DmaBroadcastOp",
    "DmaTransposeOp",
    "DmaLoadOp",
    "DmaStoreOp",
    "DmaSliceOp",
    "DmaDesliceOp",
    "DmaSubviewOp",
    "DmaViewOp",
    "DmaReshapeOp",
    "DmaCastOp",
    "DmaRingType",
    "DmaMakeRingOp",
    "DmaCurrentRingOp",
    "DmaAdvanceRingOp",
]

EXPECTED_OPERATION_ORDER = [
    "DmaAllocOp",
    "DmaFillOp",
    "DmaFreeOp",
    "DmaCopyOp",
    "DmaBroadcastOp",
    "DmaTransposeOp",
    "DmaLoadOp",
    "DmaStoreOp",
    "DmaSliceOp",
    "DmaDesliceOp",
    "DmaSubviewOp",
    "DmaViewOp",
    "DmaReshapeOp",
    "DmaCastOp",
    "DmaMakeRingOp",
    "DmaCurrentRingOp",
    "DmaAdvanceRingOp",
]

EXPECTED_COMMON_EXPORTS = [
    "verify_symbol_expr_attr",
    "verify_memory_type",
    "verify_memory_operand",
    "verify_fill_value_operand",
    "verify_fill_target_element_type",
    "verify_fill_value_matches_target",
    "operand_int_value",
    "verify_symbol_int_operands",
    "verify_symbol_index_operands",
    "verify_rank_match",
    "symbol_expr_attr_from_expr",
    "dim_expr_text",
    "static_int_from_expr_text",
    "static_int_from_dim",
    "verify_operands_match_layout",
    "parse_symbolic_expr_text",
    "verify_dynamic_shape_matches_result",
    "verify_broadcast_compat",
    "dims_equal",
    "verify_transpose_perm",
    "verify_transpose_layout",
    "verify_unit_stride_operands",
    "element_byte_size",
    "is_i8_byte_pool",
    "linear_max_index",
    "maybe_numel",
    "verify_static_view_bounds",
    "parenthesize_symbol_expr",
    "symbol_expr_product",
    "default_contiguous_stride",
    "parse_symbolic_dim_attr",
    "parse_symbol_value_expr",
    "stride_attrs_equal",
    "verify_view_result_stride",
    "is_contiguous",
    "verify_default_contiguous_stride",
    "symbol_int_expr_text",
    "verify_positive_static_operand",
]

EXPECTED_EFFECT_EXPORTS = [
    "memory_effect",
    "DmaAllocMemoryEffect",
    "DmaTargetWriteEffect",
    "DmaFreeMemoryEffect",
    "DmaTargetSourceEffect",
    "DmaBroadcastMemoryEffect",
]

EXPECTED_CANONICALIZATION_EXPORTS = [
    "DmaFillCanonicalizationTrait",
    "DmaViewCanonicalizationTrait",
    "DmaReshapeCanonicalizationTrait",
]

EXPECTED_COMMON_SIGNATURES = {
    "verify_symbol_expr_attr": "(value: 'Attribute', field_name: 'str') -> 'SymbolExprAttr'",
    "verify_memory_type": "(value: 'Attribute', field_name: 'str') -> 'NnMemoryType'",
    "verify_memory_operand": "(value: 'SSAValue', field_name: 'str') -> 'NnMemoryType'",
    "verify_fill_value_operand": "(value: 'SSAValue', field_name: 'str') -> 'SSAValue'",
    "verify_fill_target_element_type": "(element_type: 'Attribute') -> 'None'",
    "verify_fill_value_matches_target": "(value_type: 'Attribute', target_element_type: 'Attribute') -> 'None'",
    "operand_int_value": "(value: 'SSAValue') -> 'int | None'",
    "verify_symbol_int_operands": "(values: 'Sequence[SSAValue]', field_name: 'str', *, min_value: 'int') -> 'Sequence[SSAValue]'",
    "verify_symbol_index_operands": "(values: 'Sequence[SSAValue]', field_name: 'str', *, min_value: 'int') -> 'Sequence[SSAValue]'",
    "verify_rank_match": "(values: 'Sequence[SSAValue]', rank: 'int', field_name: 'str') -> 'None'",
    "symbol_expr_attr_from_expr": "(expr: 'str') -> 'SymbolExprAttr'",
    "dim_expr_text": "(dim: 'Attribute') -> 'str'",
    "static_int_from_expr_text": "(expr: 'str') -> 'int | None'",
    "static_int_from_dim": "(dim: 'Attribute') -> 'int | None'",
    "verify_operands_match_layout": "(values: 'Sequence[SSAValue]', layout: 'ArrayAttr[Attribute]', message: 'str') -> 'None'",
    "parse_symbolic_expr_text": "(text: 'str') -> 'sp.Basic | None'",
    "verify_dynamic_shape_matches_result": "(values: 'Sequence[SSAValue]', result_shape: 'ArrayAttr[Attribute]', field_name: 'str') -> 'None'",
    "verify_broadcast_compat": "(source_shape: 'ArrayAttr[Attribute]', target_shape: 'ArrayAttr[Attribute]') -> 'None'",
    "dims_equal": "(lhs: 'Attribute', rhs: 'Attribute') -> 'bool'",
    "verify_transpose_perm": "(perm: 'ArrayAttr', rank: 'int') -> 'list[int]'",
    "verify_transpose_layout": "(source_type: 'NnMemoryType', target_type: 'NnMemoryType', perm_values: 'Sequence[int]') -> 'None'",
    "verify_unit_stride_operands": "(strides: 'Sequence[SSAValue]') -> 'None'",
    "element_byte_size": "(element_type: 'Attribute') -> 'int | None'",
    "is_i8_byte_pool": "(memory_type: 'NnMemoryType') -> 'bool'",
    "linear_max_index": "(offsets: 'Sequence[SSAValue]', shape: 'Sequence[SSAValue]', stride: 'Sequence[SSAValue]') -> 'int | None'",
    "maybe_numel": "(shape: 'ArrayAttr[Attribute]') -> 'int | None'",
    "verify_static_view_bounds": "(source_shape: 'ArrayAttr[Attribute]', source_stride: 'ArrayAttr[Attribute]', offsets: 'Sequence[SSAValue]', shape: 'Sequence[SSAValue]', stride: 'Sequence[SSAValue]') -> 'None'",
    "parenthesize_symbol_expr": "(expr: 'str') -> 'str'",
    "symbol_expr_product": "(lhs: 'str', rhs: 'str') -> 'str'",
    "default_contiguous_stride": "(shape: 'ArrayAttr[Attribute]') -> 'list[Attribute]'",
    "parse_symbolic_dim_attr": "(value: 'Attribute') -> 'sp.Basic | None'",
    "parse_symbol_value_expr": "(value: 'SSAValue') -> 'sp.Basic | None'",
    "stride_attrs_equal": "(lhs: 'Attribute', rhs: 'Attribute') -> 'bool'",
    "verify_view_result_stride": "(source_stride: 'ArrayAttr[Attribute]', stride: 'Sequence[SSAValue]', result_stride: 'ArrayAttr[Attribute]') -> 'None'",
    "is_contiguous": "(memory_type: 'NnMemoryType') -> 'bool'",
    "verify_default_contiguous_stride": "(memory_type: 'NnMemoryType', message: 'str') -> 'None'",
    "symbol_int_expr_text": "(value: 'SSAValue', field_name: 'str') -> 'str'",
    "verify_positive_static_operand": "(value: 'SSAValue', field_name: 'str') -> 'int | None'",
}

EXPECTED_EFFECT_SIGNATURES = {
    "memory_effect": "(kind: 'MemoryEffectKind', value: 'SSAValue') -> 'EffectInstance'",
    "DmaAllocMemoryEffect.get_effects": "(op: 'Operation') -> 'set[EffectInstance]'",
    "DmaTargetWriteEffect.get_effects": "(op: 'Operation') -> 'set[EffectInstance]'",
    "DmaFreeMemoryEffect.get_effects": "(op: 'Operation') -> 'set[EffectInstance]'",
    "DmaTargetSourceEffect.get_effects": "(op: 'Operation') -> 'set[EffectInstance]'",
    "DmaBroadcastMemoryEffect.get_effects": "(op: 'Operation') -> 'set[EffectInstance]'",
}

EXPECTED_CANONICALIZATION_SIGNATURES = {
    "DmaFillCanonicalizationTrait.get_canonicalization_patterns": "() -> 'tuple[RewritePattern, ...]'",
    "DmaViewCanonicalizationTrait.get_canonicalization_patterns": "() -> 'tuple[RewritePattern, ...]'",
    "DmaReshapeCanonicalizationTrait.get_canonicalization_patterns": "() -> 'tuple[RewritePattern, ...]'",
}

DMA_ROOT_MODULE = "kernel_gen.dialect.dma"
INTERNAL_MODULES = {
    f"{DMA_ROOT_MODULE}.common",
    f"{DMA_ROOT_MODULE}.effect",
    f"{DMA_ROOT_MODULE}.canonicalization",
}
INTERNAL_SHORT_MODULES = {"common", "effect", "canonicalization"}
IMPORTLIB_INTERNAL_TARGETS = tuple(sorted(INTERNAL_MODULES))

ALLOWED_INTERNAL_IMPORTS = {
    "kernel_gen/dialect/dma/canonicalization.py": {
        f"{DMA_ROOT_MODULE}.common": {
            "dim_expr_text",
            "operand_int_value",
            "symbol_int_expr_text",
            "verify_memory_type",
        }
    },
    "kernel_gen/dialect/dma/operation/alias.py": {
        f"{DMA_ROOT_MODULE}.common": {
            "element_byte_size",
            "is_contiguous",
            "is_i8_byte_pool",
            "linear_max_index",
            "maybe_numel",
            "operand_int_value",
            "verify_default_contiguous_stride",
            "verify_memory_type",
            "verify_operands_match_layout",
            "verify_rank_match",
            "verify_static_view_bounds",
            "verify_symbol_index_operands",
            "verify_symbol_int_operands",
            "verify_view_result_stride",
        },
        f"{DMA_ROOT_MODULE}.canonicalization": {
            "DmaReshapeCanonicalizationTrait",
            "DmaViewCanonicalizationTrait",
        },
    },
    "kernel_gen/dialect/dma/operation/lifecycle.py": {
        f"{DMA_ROOT_MODULE}.common": {
            "verify_dynamic_shape_matches_result",
            "verify_fill_target_element_type",
            "verify_fill_value_matches_target",
            "verify_fill_value_operand",
            "verify_memory_operand",
            "verify_memory_type",
            "verify_symbol_int_operands",
        },
        f"{DMA_ROOT_MODULE}.effect": {
            "DmaAllocMemoryEffect",
            "DmaFreeMemoryEffect",
            "DmaTargetWriteEffect",
        },
        f"{DMA_ROOT_MODULE}.canonicalization": {"DmaFillCanonicalizationTrait"},
    },
    "kernel_gen/dialect/dma/operation/ring.py": {
        f"{DMA_ROOT_MODULE}.common": {
            "is_i8_byte_pool",
            "maybe_numel",
            "symbol_int_expr_text",
            "verify_memory_operand",
            "verify_positive_static_operand",
        }
    },
    "kernel_gen/dialect/dma/operation/slice.py": {
        f"{DMA_ROOT_MODULE}.common": {
            "verify_memory_type",
            "verify_operands_match_layout",
            "verify_rank_match",
            "verify_symbol_index_operands",
            "verify_symbol_int_operands",
            "verify_unit_stride_operands",
        },
        f"{DMA_ROOT_MODULE}.effect": {"DmaTargetSourceEffect"},
    },
    "kernel_gen/dialect/dma/operation/transfer.py": {
        f"{DMA_ROOT_MODULE}.common": {
            "verify_broadcast_compat",
            "verify_memory_type",
            "verify_transpose_layout",
            "verify_transpose_perm",
        },
        f"{DMA_ROOT_MODULE}.effect": {
            "DmaBroadcastMemoryEffect",
            "DmaTargetSourceEffect",
        },
    },
    "kernel_gen/dialect/dma/type/ring_type.py": {
        f"{DMA_ROOT_MODULE}.common": {"static_int_from_dim", "verify_symbol_expr_attr"}
    },
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _relative_path(path: Path, root: Path) -> str:
    if not path.is_relative_to(root):
        return path.as_posix()
    return path.relative_to(root).as_posix()


def _module_name_for_package_file(path: Path, root: Path) -> str:
    relative = path.relative_to(root).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _resolve_import_from_module(path: Path, root: Path, node: ast.ImportFrom) -> str:
    if node.level == 0:
        return node.module or ""
    if not path.is_relative_to(root):
        return node.module or ""
    module_name = _module_name_for_package_file(path, root)
    current_package = module_name if path.name == "__init__.py" else module_name.rsplit(".", 1)[0]
    package_parts = current_package.split(".")
    base_parts = package_parts[: len(package_parts) - node.level + 1]
    base_module = ".".join(base_parts)
    if node.module:
        return f"{base_module}.{node.module}"
    return base_module


def _parse_python_file(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _load_dma_internal_modules() -> dict[str, ModuleType]:
    return {
        "canonicalization": importlib.import_module("kernel_gen.dialect.dma.canonicalization"),
        "common": importlib.import_module("kernel_gen.dialect.dma.common"),
        "effect": importlib.import_module("kernel_gen.dialect.dma.effect"),
    }


def _is_importlib_import_module_call(node: ast.Call) -> bool:
    return (
        isinstance(node.func, ast.Attribute)
        and node.func.attr == "import_module"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "importlib"
    )


def _string_literal_arg(node: ast.Call) -> str | None:
    if not node.args:
        return None
    value = node.args[0]
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return value.value
    return None


def _append_import_boundary_failures(path: Path, root: Path, failures: list[str]) -> None:
    relative_path = _relative_path(path, root)
    tree = _parse_python_file(path)
    is_dma_package_file = relative_path.startswith("kernel_gen/dialect/dma/")
    is_test_package = relative_path == "test/dialect/dma/test_package.py"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_module = alias.name
                if imported_module in INTERNAL_MODULES or any(
                    imported_module.startswith(f"{module_name}.") for module_name in INTERNAL_MODULES
                ):
                    failures.append(f"{relative_path}:{node.lineno} imports internal module object {imported_module}")

        if isinstance(node, ast.ImportFrom):
            imported_from = _resolve_import_from_module(path, root, node)
            imported_names = {alias.name for alias in node.names}
            if imported_from == DMA_ROOT_MODULE and imported_names & INTERNAL_SHORT_MODULES:
                failures.append(
                    f"{relative_path}:{node.lineno} imports internal module via dma root "
                    f"{sorted(imported_names & INTERNAL_SHORT_MODULES)}"
                )
            if imported_from.startswith(f"{DMA_ROOT_MODULE}.") and any(
                name == "*" or name.startswith("_") for name in imported_names
            ):
                failures.append(f"{relative_path}:{node.lineno} imports private/star name from {imported_from}")
            if imported_from in INTERNAL_MODULES:
                if not is_dma_package_file:
                    failures.append(f"{relative_path}:{node.lineno} imports package-internal helper from {imported_from}")
                    continue
                allowed_names = ALLOWED_INTERNAL_IMPORTS.get(relative_path, {}).get(imported_from)
                if allowed_names is None:
                    failures.append(f"{relative_path}:{node.lineno} imports disallowed internal module {imported_from}")
                    continue
                unexpected_names = imported_names - allowed_names
                missing_names = allowed_names - imported_names
                if unexpected_names or missing_names:
                    failures.append(
                        f"{relative_path}:{node.lineno} imports {imported_from} names mismatch: "
                        f"unexpected={sorted(unexpected_names)}, missing={sorted(missing_names)}"
                    )

        if isinstance(node, ast.Call) and _is_importlib_import_module_call(node):
            target = _string_literal_arg(node)
            if target in INTERNAL_MODULES:
                if not is_test_package:
                    failures.append(f"{relative_path}:{node.lineno} importlib loads internal module {target}")
                continue
            if isinstance(target, str) and target.startswith(f"{DMA_ROOT_MODULE}."):
                failures.append(f"{relative_path}:{node.lineno} importlib loads non-whitelisted dma submodule {target}")

        if is_test_package and isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id in INTERNAL_SHORT_MODULES:
                failures.append(f"{relative_path}:{node.lineno} calls internal helper via {node.func.value.id}.{node.func.attr}")


def _expectation_dma_files(root: Path) -> list[Path]:
    candidates = [
        root / "expectation/dialect/dma",
        root.parent / "expectation/dialect/dma",
    ]
    files: list[Path] = []
    for candidate in candidates:
        if candidate.is_dir():
            files.extend(sorted(candidate.rglob("*.py")))
    return files


def test_dma_package_root_exact_exports_and_dialect_order() -> None:
    """验证 dma package root 公开导出与 Dialect 注册顺序。"""

    assert dma.__all__ == EXPECTED_ROOT_EXPORTS
    assert [op.__name__ for op in dma.Dma.operations] == EXPECTED_OPERATION_ORDER
    assert [attr.__name__ for attr in dma.Dma.attributes] == ["DmaRingType"]
    for name in EXPECTED_ROOT_EXPORTS:
        assert getattr(dma, name).__name__ == name
    assert all(name not in dialect_root.__all__ for name in EXPECTED_ROOT_EXPORTS)
    with pytest.raises(ImportError):
        exec("from kernel_gen.dialect import Dma", {})
    with pytest.raises(ImportError):
        exec("from kernel_gen.dialect import DmaAllocOp", {})


def test_dma_package_internal_modules_are_not_root_exports() -> None:
    """验证 package-internal helper 模块不经 root API 外泄。"""

    modules = _load_dma_internal_modules()
    common = modules["common"]
    effect = modules["effect"]
    canonicalization = modules["canonicalization"]

    assert common.__all__ == EXPECTED_COMMON_EXPORTS
    assert effect.__all__ == EXPECTED_EFFECT_EXPORTS
    assert canonicalization.__all__ == EXPECTED_CANONICALIZATION_EXPORTS
    for name in EXPECTED_COMMON_EXPORTS + EXPECTED_EFFECT_EXPORTS + EXPECTED_CANONICALIZATION_EXPORTS:
        assert name not in dma.__all__


def test_dma_package_internal_helper_signatures_are_stable() -> None:
    """验证 package-internal helper 结构签名，防止拆分后边界漂移。"""

    modules = _load_dma_internal_modules()
    common = modules["common"]
    effect = modules["effect"]
    canonicalization = modules["canonicalization"]

    common_signatures = {name: str(inspect.signature(getattr(common, name))) for name in common.__all__}
    assert common_signatures == EXPECTED_COMMON_SIGNATURES

    effect_signatures = {"memory_effect": str(inspect.signature(effect.memory_effect))}
    for class_name in EXPECTED_EFFECT_EXPORTS[1:]:
        trait_class = getattr(effect, class_name)
        assert issubclass(trait_class, MemoryEffect)
        effect_signatures[f"{class_name}.get_effects"] = str(inspect.signature(trait_class.get_effects))
    assert effect_signatures == EXPECTED_EFFECT_SIGNATURES

    canonicalization_signatures = {}
    for class_name in EXPECTED_CANONICALIZATION_EXPORTS:
        trait_class = getattr(canonicalization, class_name)
        assert issubclass(trait_class, HasCanonicalizationPatternsTrait)
        canonicalization_signatures[f"{class_name}.get_canonicalization_patterns"] = str(
            inspect.signature(trait_class.get_canonicalization_patterns)
        )
    assert canonicalization_signatures == EXPECTED_CANONICALIZATION_SIGNATURES


def test_dma_package_internal_import_boundaries_are_ast_gated() -> None:
    """用持久 AST gate 锁定 package-internal helper 导入边界。"""

    root = _repo_root()
    files = sorted((root / "kernel_gen").rglob("*.py"))
    files.extend(sorted((root / "test").rglob("*.py")))
    files.extend(_expectation_dma_files(root))

    failures: list[str] = []
    for path in files:
        _append_import_boundary_failures(path, root, failures)

    test_package_tree = _parse_python_file(Path(__file__).resolve())
    importlib_targets = [
        _string_literal_arg(node)
        for node in ast.walk(test_package_tree)
        if isinstance(node, ast.Call) and _is_importlib_import_module_call(node)
    ]
    assert sorted(importlib_targets) == list(IMPORTLIB_INTERNAL_TARGETS)
    assert failures == []
