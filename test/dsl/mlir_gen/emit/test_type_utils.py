"""Emit type utils tests.

创建者: jcc你莫辜负
最后一次更改: jcc你莫辜负

功能说明:
- 覆盖类型推导与 memory type 组装的最小行为。

使用示例:
- pytest -q test/dsl/mlir_gen/emit/test_type_utils.py

覆盖率信息:
- 覆盖率命令: coverage run -m pytest -q test/dsl/mlir_gen/emit/test_type_utils.py && coverage report --include=kernel_gen/dsl/mlir_gen/emit/type_utils.py -m
- 覆盖率结果: 未统计（待补充）
- 达标线: 90%

关联文件:
- 功能实现: kernel_gen/dsl/mlir_gen/emit/type_utils.py
- Spec 文档: spec/dsl/emit_mlir.md
- 测试文件: test/dsl/mlir_gen/emit/test_type_utils.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from xdsl.dialects.builtin import ArrayAttr, IntAttr, f32, i32

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dsl.ast import ConstAST
from kernel_gen.dsl.mlir_gen.emit.type_utils import infer_expr_type, memory_type_from_parts


# EMIT-TYPE-001
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-13 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-13 00:00:00 +0800
# 功能说明: 验证 memory_type_from_parts 的最小组装行为。
# 测试目的: 锁定 NnMemoryType 的 shape/stride/element/space 组合结果。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_type_utils.py -k test_memory_type_from_parts
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/type_utils.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_type_utils.py
def test_memory_type_from_parts() -> None:
    shape = [IntAttr(2), IntAttr(3)]
    stride = [IntAttr(3), IntAttr(1)]
    space = NnMemorySpaceAttr.from_name("global")

    result = memory_type_from_parts(shape, stride, f32, space)

    if not isinstance(result, NnMemoryType):
        raise AssertionError("expected NnMemoryType result")
    if list(result.shape.data) != shape:
        raise AssertionError("shape mismatch")
    if list(result.stride.data) != stride:
        raise AssertionError("stride mismatch")
    if result.element_type != f32:
        raise AssertionError("element_type mismatch")


# EMIT-TYPE-002
# 创建者: jcc你莫辜负
# 最后一次更改: jcc你莫辜负
# 最近一次运行测试时间: 2026-04-13 00:00:00 +0800
# 最近一次运行成功时间: 2026-04-13 00:00:00 +0800
# 功能说明: 验证 infer_expr_type 对常量类型推导。
# 测试目的: 锁定 int 常量推导为 i32。
# 使用示例: pytest -q test/dsl/mlir_gen/emit/test_type_utils.py -k test_infer_expr_type_const
# 对应功能实现文件路径: kernel_gen/dsl/mlir_gen/emit/type_utils.py
# 对应 spec 文件路径: spec/dsl/emit_mlir.md
# 对应测试文件路径: test/dsl/mlir_gen/emit/test_type_utils.py
def test_infer_expr_type_const() -> None:
    result = infer_expr_type(ConstAST(1), {})
    if result != i32:
        raise AssertionError("expected i32 for int constant")
