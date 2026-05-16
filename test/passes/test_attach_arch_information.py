"""attach-arch-information pass tests.


功能说明:
- 覆盖 kernel_gen/passes/attach_arch_information.py 的 launch extent 回写与校验行为。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- `pytest -q test/passes/test_attach_arch_information.py`

使用示例:
- pytest -q test/passes/test_attach_arch_information.py

关联文件:
- 功能实现: kernel_gen/passes/attach_arch_information.py
- Spec 文档: spec/pass/attach_arch_information.md
- 测试文件: test/passes/test_attach_arch_information.py
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import FunctionType, IntAttr, ModuleOp, StringAttr
from xdsl.ir import Block, Region

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.arch import ArchGetDynamicMemoryOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolExprAttr
from kernel_gen.passes.attach_arch_information import AttachArchInformationPass
from kernel_gen.target.registry import TargetSpec, register_target


def _register_attach_target(name: str, hardware: dict[str, int], supports_launch: bool = True) -> None:
    """注册 attach pass 边界测试使用的公开 target。"""

    register_target(
        TargetSpec(
            name=name,
            arch_supported_ops={"arch.launch"} if supports_launch else set(),
            arch_unsupported_ops=set(),
            hardware=hardware,
        )
    )


def _make_empty_func_module() -> ModuleOp:
    """构造一个最小可 attach 的 module。


    功能说明:
    - 单个入口 `func.func`，便于验证 pass 会从 target registry 写回 launch extent。

    使用示例:
    - module = _make_empty_func_module()

    关联文件:
    - spec: [spec/pass/attach_arch_information.md](../../../spec/pass/attach_arch_information.md)
    - test: [test/passes/test_attach_arch_information.py](../../../test/passes/test_attach_arch_information.py)
    - 功能实现: [kernel_gen/passes/attach_arch_information.py](../../../kernel_gen/passes/attach_arch_information.py)
    """

    block = Block()
    block.add_op(func.ReturnOp())
    func_op = func.FuncOp("launch_kernel", FunctionType.from_lists([], []), Region(block))
    return ModuleOp([func_op])


def _make_multi_func_module() -> ModuleOp:
    """构造一个含多个非 declaration `func.func` 的 module。


    功能说明:
    - 便于验证 attach pass 会在入口不唯一时显式失败，而不是静默选择首个函数。

    使用示例:
    - module = _make_multi_func_module()

    关联文件:
    - spec: [spec/pass/attach_arch_information.md](../../../spec/pass/attach_arch_information.md)
    - test: [test/passes/test_attach_arch_information.py](../../../test/passes/test_attach_arch_information.py)
    - 功能实现: [kernel_gen/passes/attach_arch_information.py](../../../kernel_gen/passes/attach_arch_information.py)
    """

    block_1 = Block()
    block_1.add_op(func.ReturnOp())
    block_2 = Block()
    block_2.add_op(func.ReturnOp())
    entry_func = func.FuncOp("launch_kernel", FunctionType.from_lists([], []), Region(block_1))
    helper_func = func.FuncOp("launch_kernel_helper", FunctionType.from_lists([], []), Region(block_2))
    return ModuleOp([entry_func, helper_func])


def _make_dynamic_memory_module(spaces: tuple[str, ...]) -> ModuleOp:
    """构造含 arch.get_dynamic_memory 的最小 module。

    功能说明:
    - 为 attach pass 容量特化测试提供 target memory 查询 op。

    使用示例:
    - module = _make_dynamic_memory_module(("tsm", "tlm1"))

    关联文件:
    - spec: [spec/pass/attach_arch_information.md](../../../spec/pass/attach_arch_information.md)
    - test: [test/passes/test_attach_arch_information.py](../../../test/passes/test_attach_arch_information.py)
    - 功能实现: [kernel_gen/passes/attach_arch_information.py](../../../kernel_gen/passes/attach_arch_information.py)
    """

    block = Block()
    for space in spaces:
        block.add_op(ArchGetDynamicMemoryOp(NnMemorySpaceAttr.from_name(space)))
    block.add_op(func.ReturnOp())
    func_op = func.FuncOp("launch_kernel", FunctionType.from_lists([], []), Region(block))
    return ModuleOp([func_op])


def test_public_import_path_exposes_attach_arch_information_pass_only() -> None:
    package_module = importlib.import_module("kernel_gen.passes")
    attach_module = importlib.import_module("kernel_gen.passes.attach_arch_information")

    assert package_module.AttachArchInformationPass is AttachArchInformationPass
    assert not hasattr(package_module, "AttachArchInformationError")
    assert not hasattr(attach_module, "AttachArchInformationError")


def test_attach_arch_information_writes_registry_launch_extents() -> None:
    module = _make_empty_func_module()
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))

    AttachArchInformationPass.from_options({"target": "npu_demo"}).apply(Context(), module)
    result = module

    assert result is module
    assert func_op.attributes["launch_block"] == IntAttr(1)
    assert func_op.attributes["launch_thread"] == IntAttr(1)
    assert func_op.attributes["launch_subthread"] == IntAttr(1)
    assert func_op.attributes["shared_memory_size"] == IntAttr(0)


def test_attach_arch_information_specializes_npu_demo_dynamic_memory_capacity() -> None:
    module = _make_dynamic_memory_module(("shared", "tsm", "tlm1", "tlm2", "tlm3"))

    AttachArchInformationPass.from_options({"target": "npu_demo"}).apply(Context(), module)

    expected = {
        "shared": "SM_SIZE",
        "tsm": "2097152",
        "tlm1": "524288",
        "tlm2": "1048576",
        "tlm3": "1048576",
    }
    dynamic_ops = [op for op in module.walk() if isinstance(op, ArchGetDynamicMemoryOp)]
    assert len(dynamic_ops) == len(expected)
    for op in dynamic_ops:
        memory_type = op.result.type
        assert isinstance(memory_type, NnMemoryType)
        space_name = op.memory_space.space.data
        assert memory_type.shape.data[0] == SymbolExprAttr.from_expr(expected[space_name])


def test_attach_arch_information_rejects_partial_launch_attrs() -> None:
    module = _make_empty_func_module()
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    func_op.attributes["launch_block"] = IntAttr(1)

    with pytest.raises(
        KernelCodeError,
        match=r"^AttachArchInformationError: function launch_kernel must define launch_block, launch_thread, launch_subthread, and shared_memory_size together$",
    ):
        AttachArchInformationPass(target="npu_demo").apply(Context(), module)


def test_attach_arch_information_rejects_multiple_entry_funcs() -> None:
    module = _make_multi_func_module()

    with pytest.raises(
        KernelCodeError,
        match=r"^AttachArchInformationError: module must contain exactly one non-declaration func\.func$",
    ):
        AttachArchInformationPass(target="npu_demo").apply(Context(), module)


def test_attach_arch_information_rejects_invalid_public_options() -> None:
    with pytest.raises(KernelCodeError, match=r"^AttachArchInformationError: unknown option\(s\): extra$"):
        AttachArchInformationPass.from_options({"target": "npu_demo", "extra": "1"})

    with pytest.raises(KernelCodeError, match=r"^AttachArchInformationError: target must be non-empty string$"):
        AttachArchInformationPass.from_options({"target": ""})


def test_attach_arch_information_rejects_non_module_input() -> None:
    block = Block()
    block.add_op(func.ReturnOp())
    func_op = func.FuncOp("launch_kernel", FunctionType.from_lists([], []), Region(block))

    with pytest.raises(KernelCodeError, match=r"^AttachArchInformationError: module must be builtin\.module$"):
        AttachArchInformationPass(target="npu_demo").apply(Context(), func_op)


def test_attach_arch_information_rejects_target_registry_boundaries() -> None:
    module = _make_empty_func_module()
    _register_attach_target(
        "attach_no_launch",
        {"block_num": 1, "thread_num": 1, "subthread_num": 1, "sm_memory_size": 0},
        supports_launch=False,
    )
    with pytest.raises(KernelCodeError, match=r"^AttachArchInformationError: target attach_no_launch does not support arch\.launch$"):
        AttachArchInformationPass(target="attach_no_launch").apply(Context(), module)

    _register_attach_target(
        "attach_missing_thread",
        {"block_num": 1, "subthread_num": 1, "sm_memory_size": 0},
    )
    with pytest.raises(KernelCodeError, match=r"^AttachArchInformationError: target attach_missing_thread is missing launch extent$"):
        AttachArchInformationPass(target="attach_missing_thread").apply(Context(), _make_empty_func_module())

    _register_attach_target(
        "attach_zero_block",
        {"block_num": 0, "thread_num": 1, "subthread_num": 1, "sm_memory_size": 0},
    )
    with pytest.raises(KernelCodeError, match=r"^AttachArchInformationError: function attach_zero_block launch_block must be > 0$"):
        AttachArchInformationPass(target="attach_zero_block").apply(Context(), _make_empty_func_module())

    _register_attach_target(
        "attach_missing_sm",
        {"block_num": 1, "thread_num": 1, "subthread_num": 1},
    )
    with pytest.raises(KernelCodeError, match=r"^AttachArchInformationError: target attach_missing_sm is missing launch extent$"):
        AttachArchInformationPass(target="attach_missing_sm").apply(Context(), _make_empty_func_module())

    _register_attach_target(
        "attach_negative_sm",
        {"block_num": 1, "thread_num": 1, "subthread_num": 1, "sm_memory_size": -1},
    )
    with pytest.raises(KernelCodeError, match=r"^AttachArchInformationError: function attach_negative_sm shared_memory_size must be >= 0$"):
        AttachArchInformationPass(target="attach_negative_sm").apply(Context(), _make_empty_func_module())


def test_attach_arch_information_accepts_existing_int_like_attrs() -> None:
    module = _make_empty_func_module()
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    func_op.attributes["launch_block"] = StringAttr("1")
    func_op.attributes["launch_thread"] = StringAttr("1")
    func_op.attributes["launch_subthread"] = StringAttr("1")
    func_op.attributes["shared_memory_size"] = StringAttr("0")

    AttachArchInformationPass(target="npu_demo").apply(Context(), module)

    assert func_op.attributes["launch_block"] == StringAttr("1")
    assert func_op.attributes["launch_thread"] == StringAttr("1")
    assert func_op.attributes["launch_subthread"] == StringAttr("1")
    assert func_op.attributes["shared_memory_size"] == StringAttr("0")


def test_attach_arch_information_rejects_existing_attr_mismatch() -> None:
    module = _make_empty_func_module()
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    func_op.attributes["launch_block"] = IntAttr(1)
    func_op.attributes["launch_thread"] = IntAttr(2)
    func_op.attributes["launch_subthread"] = IntAttr(1)
    func_op.attributes["shared_memory_size"] = IntAttr(0)

    with pytest.raises(KernelCodeError, match=r"^AttachArchInformationError: function launch_kernel launch extents must match target npu_demo$"):
        AttachArchInformationPass(target="npu_demo").apply(Context(), module)
