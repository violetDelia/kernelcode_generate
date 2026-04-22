"""attach-arch-information pass tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 kernel_gen/passes/attach_arch_information.py 的 launch extent 回写与校验行为。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- `pytest -q test/pass/test_attach_arch_information.py`

使用示例:
- pytest -q test/pass/test_attach_arch_information.py

关联文件:
- 功能实现: kernel_gen/passes/attach_arch_information.py
- Spec 文档: spec/pass/attach_arch_information.md
- 测试文件: test/pass/test_attach_arch_information.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xdsl.dialects import func
from xdsl.dialects.builtin import FunctionType, IntAttr, ModuleOp
from xdsl.ir import Block, Region

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.passes.attach_arch_information import (
    AttachArchInformationError,
    AttachArchInformationPass,
)


def _make_empty_func_module() -> ModuleOp:
    """构造一个最小可 attach 的 module。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 单个入口 `func.func`，便于验证 pass 会从 target registry 写回 launch extent。

    使用示例:
    - module = _make_empty_func_module()

    关联文件:
    - spec: [spec/pass/attach_arch_information.md](../../../spec/pass/attach_arch_information.md)
    - test: [test/pass/test_attach_arch_information.py](../../../test/pass/test_attach_arch_information.py)
    - 功能实现: [kernel_gen/passes/attach_arch_information.py](../../../kernel_gen/passes/attach_arch_information.py)
    """

    block = Block()
    block.add_op(func.ReturnOp())
    func_op = func.FuncOp("launch_kernel", FunctionType.from_lists([], []), Region(block))
    return ModuleOp([func_op])


def _make_multi_func_module() -> ModuleOp:
    """构造一个含多个非 declaration `func.func` 的 module。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 便于验证 attach pass 会在入口不唯一时显式失败，而不是静默选择首个函数。

    使用示例:
    - module = _make_multi_func_module()

    关联文件:
    - spec: [spec/pass/attach_arch_information.md](../../../spec/pass/attach_arch_information.md)
    - test: [test/pass/test_attach_arch_information.py](../../../test/pass/test_attach_arch_information.py)
    - 功能实现: [kernel_gen/passes/attach_arch_information.py](../../../kernel_gen/passes/attach_arch_information.py)
    """

    block_1 = Block()
    block_1.add_op(func.ReturnOp())
    block_2 = Block()
    block_2.add_op(func.ReturnOp())
    entry_func = func.FuncOp("launch_kernel", FunctionType.from_lists([], []), Region(block_1))
    helper_func = func.FuncOp("launch_kernel_helper", FunctionType.from_lists([], []), Region(block_2))
    return ModuleOp([entry_func, helper_func])


def test_attach_arch_information_writes_registry_launch_extents() -> None:
    module = _make_empty_func_module()
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))

    AttachArchInformationPass.from_options({"target": "npu_demo"}).run(module)

    assert func_op.attributes["launch_block"] == IntAttr(1)
    assert func_op.attributes["launch_thread"] == IntAttr(1)
    assert func_op.attributes["launch_subthread"] == IntAttr(1)
    assert func_op.attributes["shared_memory_size"] == IntAttr(0)


def test_attach_arch_information_rejects_partial_launch_attrs() -> None:
    module = _make_empty_func_module()
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    func_op.attributes["launch_block"] = IntAttr(1)

    with pytest.raises(
        AttachArchInformationError,
        match=r"^AttachArchInformationError: function launch_kernel must define launch_block, launch_thread, launch_subthread, and shared_memory_size together$",
    ):
        AttachArchInformationPass(target="npu_demo").run(module)


def test_attach_arch_information_rejects_multiple_entry_funcs() -> None:
    module = _make_multi_func_module()

    with pytest.raises(
        AttachArchInformationError,
        match=r"^AttachArchInformationError: module must contain exactly one non-declaration func\.func$",
    ):
        AttachArchInformationPass(target="npu_demo").run(module)
