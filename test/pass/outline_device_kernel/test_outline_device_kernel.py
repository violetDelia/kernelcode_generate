"""outline-device-kernel pass tests.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 覆盖 `OutlineDeviceKernelPass` 的公开 outline 合同。
- 锁定 wrapper/device 双函数形状、显式失败路径与未标记函数保持原样的边界。
- 锁定只读合同仍可通过 lowering 兼容路径导入 outline-device-kernel 入口。

使用示例:
- pytest -q test/pass/outline_device_kernel/test_outline_device_kernel.py

关联文件:
- spec: [spec/pass/outline_device_kernel.md](spec/pass/outline_device_kernel.md)
- test: [test/pass/outline_device_kernel/test_outline_device_kernel.py](test/pass/outline_device_kernel/test_outline_device_kernel.py)
- 功能实现: [kernel_gen/passes/outline_device_kernel.py](kernel_gen/passes/outline_device_kernel.py)
"""

from __future__ import annotations

import importlib
from io import StringIO
from pathlib import Path
import sys

import pytest
from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import ModuleOp
from xdsl.dialects.test import Test
from xdsl.parser import Parser
from xdsl.printer import Printer
from xdsl.passes import ModulePass

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.context import build_default_context
from kernel_gen.passes import PassContractError
from kernel_gen.passes.outline_device_kernel import OutlineDeviceKernelPass


def _build_context() -> Context:
    """构造用于 outline-device-kernel 测试的解析上下文。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 复用仓库默认 dialect 上下文。
    - 额外加载 `test` dialect，便于在 device body 中放置稳定的占位 op。

    使用示例:
    - ctx = _build_context()

    关联文件:
    - spec: [spec/pass/outline_device_kernel.md](spec/pass/outline_device_kernel.md)
    - test: [test/pass/outline_device_kernel/test_outline_device_kernel.py](test/pass/outline_device_kernel/test_outline_device_kernel.py)
    - 功能实现: [kernel_gen/passes/outline_device_kernel.py](kernel_gen/passes/outline_device_kernel.py)
    """

    ctx = build_default_context()
    ctx.load_dialect(Test)
    return ctx


def _parse_module(text: str) -> ModuleOp:
    """把测试 IR 文本解析为 `ModuleOp`。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 为 outline-device-kernel 成功路径与失败路径提供统一的 module 构造入口。

    使用示例:
    - module = _parse_module("builtin.module { func.func @main() { func.return } }")

    关联文件:
    - spec: [spec/pass/outline_device_kernel.md](spec/pass/outline_device_kernel.md)
    - test: [test/pass/outline_device_kernel/test_outline_device_kernel.py](test/pass/outline_device_kernel/test_outline_device_kernel.py)
    - 功能实现: [kernel_gen/passes/outline_device_kernel.py](kernel_gen/passes/outline_device_kernel.py)
    """

    return Parser(_build_context(), text).parse_module()


def _print_ir(module: ModuleOp) -> str:
    """打印 module 为稳定文本。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 使用显式 `Printer` 获取断言友好的 IR 文本。

    使用示例:
    - text = _print_ir(module)

    关联文件:
    - spec: [spec/pass/outline_device_kernel.md](spec/pass/outline_device_kernel.md)
    - test: [test/pass/outline_device_kernel/test_outline_device_kernel.py](test/pass/outline_device_kernel/test_outline_device_kernel.py)
    - 功能实现: [kernel_gen/passes/outline_device_kernel.py](kernel_gen/passes/outline_device_kernel.py)
    """

    stream = StringIO()
    Printer(stream=stream).print_op(module)
    return stream.getvalue()


# TC-ODK-001
# 创建者: 朽木露琪亚
# 最后一次更改: 金铲铲大作战
# 功能说明: 锁定公开 pass 名称，供 registry 与 standalone 构造共同复用。
# 使用示例: pytest -q test/pass/outline_device_kernel/test_outline_device_kernel.py -k test_outline_device_kernel_pass_registry_name
# 对应功能实现文件路径: kernel_gen/passes/outline_device_kernel.py
# 对应 spec 文件路径: spec/pass/outline_device_kernel.md
# 对应测试文件路径: test/pass/outline_device_kernel/test_outline_device_kernel.py
def test_outline_device_kernel_pass_registry_name() -> None:
    assert OutlineDeviceKernelPass.name == "outline-device-kernel"


# TC-ODK-001A
# 创建者: OpenAI Codex
# 最后一次更改: 朽木露琪亚
# 功能说明: 锁定当前文件只公开 `OutlineDeviceKernelPass`，不再暴露内部 pattern helper。
# 使用示例: pytest -q test/pass/outline_device_kernel/test_outline_device_kernel.py -k test_outline_device_kernel_public_entry_hides_internal_pattern_helpers
# 对应功能实现文件路径: kernel_gen/passes/outline_device_kernel.py
# 对应 spec 文件路径: spec/pass/outline_device_kernel.md
# 对应测试文件路径: test/pass/outline_device_kernel/test_outline_device_kernel.py
def test_outline_device_kernel_public_entry_hides_internal_pattern_helpers() -> None:
    direct_module = importlib.import_module("kernel_gen.passes.outline_device_kernel")

    assert direct_module.OutlineDeviceKernelPass is OutlineDeviceKernelPass
    with pytest.raises(AttributeError):
        getattr(direct_module, "OutlineDeviceKernelFuncPattern")
    with pytest.raises(AttributeError):
        getattr(direct_module, "get_outline_device_kernel_pass_patterns")


# TC-ODK-002
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 功能说明: 锁定 lowering 兼容导入仍映射到迁移后的唯一实现模块。
# 使用示例: pytest -q test/pass/outline_device_kernel/test_outline_device_kernel.py -k test_outline_device_kernel_lowering_compat_import_matches_rehome_entry
# 对应功能实现文件路径: kernel_gen/passes/outline_device_kernel.py
# 对应 spec 文件路径: spec/pass/outline_device_kernel.md
# 对应测试文件路径: test/pass/outline_device_kernel/test_outline_device_kernel.py
def test_outline_device_kernel_lowering_compat_import_matches_rehome_entry() -> None:
    compat_module = importlib.import_module("kernel_gen.passes.lowering.outline_device_kernel")
    direct_module = importlib.import_module("kernel_gen.passes.outline_device_kernel")
    package_module = importlib.import_module("kernel_gen.passes")

    assert compat_module is direct_module
    assert compat_module.OutlineDeviceKernelPass is OutlineDeviceKernelPass
    with pytest.raises(AttributeError):
        getattr(compat_module, "OutlineDeviceKernelFuncPattern")
    with pytest.raises(AttributeError):
        getattr(compat_module, "get_outline_device_kernel_pass_patterns")
    assert package_module.OutlineDeviceKernelPass is OutlineDeviceKernelPass


# TC-ODK-003
# 创建者: 朽木露琪亚
# 最后一次更改: 金铲铲大作战
# 功能说明: 锁定非 builtin.module 输入时报稳定错误类型与短语。
# 使用示例: pytest -q test/pass/outline_device_kernel/test_outline_device_kernel.py -k test_outline_device_kernel_non_module_input_raises_stable_error
# 对应功能实现文件路径: kernel_gen/passes/outline_device_kernel.py
# 对应 spec 文件路径: spec/pass/outline_device_kernel.md
# 对应测试文件路径: test/pass/outline_device_kernel/test_outline_device_kernel.py
def test_outline_device_kernel_non_module_input_raises_stable_error() -> None:
    with pytest.raises(
        PassContractError,
        match=r"^module must be builtin\.module$",
    ):
        OutlineDeviceKernelPass().run(object())


# TC-ODK-004
# 创建者: 朽木露琪亚
# 最后一次更改: 金铲铲大作战
# 功能说明: 锁定空 module 直接返回同一对象，不引入额外改写副作用。
# 使用示例: pytest -q test/pass/outline_device_kernel/test_outline_device_kernel.py -k test_outline_device_kernel_empty_module_returns_same_object
# 对应功能实现文件路径: kernel_gen/passes/outline_device_kernel.py
# 对应 spec 文件路径: spec/pass/outline_device_kernel.md
# 对应测试文件路径: test/pass/outline_device_kernel/test_outline_device_kernel.py
def test_outline_device_kernel_empty_module_returns_same_object() -> None:
    module = ModuleOp([])

    result = OutlineDeviceKernelPass().run(module)

    assert result is module
    assert list(module.ops) == []


# TC-ODK-004A
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 功能说明: 验证 OutlineDeviceKernelPass 作为 ModulePass 可直接通过 apply(ctx, module) 执行。
# 使用示例: pytest -q test/pass/outline_device_kernel/test_outline_device_kernel.py -k test_outline_device_kernel_apply_behaves_like_module_pass
# 对应功能实现文件路径: kernel_gen/passes/outline_device_kernel.py
# 对应 spec 文件路径: spec/pass/outline_device_kernel.md
# 对应测试文件路径: test/pass/outline_device_kernel/test_outline_device_kernel.py
def test_outline_device_kernel_apply_behaves_like_module_pass() -> None:
    module = _parse_module(_BASIC_MODULE)
    pass_obj = OutlineDeviceKernelPass()
    ctx = Context()

    assert isinstance(pass_obj, ModulePass)

    result = pass_obj.apply(ctx, module)

    assert result is None
    module.verify()


_BASIC_MODULE = """
builtin.module {
  func.func @kernel(
    %lhs : !nn.memory<[4], [1], f32, #nn.space<global>>,
    %rhs : !nn.memory<[4], [1], f32, #nn.space<global>>,
    %out : !nn.memory<[4], [1], f32, #nn.space<global>>
  ) attributes {
    launch_block = 1 : i64,
    launch_thread = 4 : i64,
    launch_subthread = 1 : i64,
    shared_memory_size = 0 : i64
  } {
    "test.op"(%lhs, %rhs, %out) : (!nn.memory<[4], [1], f32, #nn.space<global>>, !nn.memory<[4], [1], f32, #nn.space<global>>, !nn.memory<[4], [1], f32, #nn.space<global>>) -> ()
    func.return
  }
}
"""


# TC-ODK-005
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 outline 成功时生成 `wrapper + device` 双函数，且 `shared_memory_size` 仅保留在 device 上。
# 使用示例: pytest -q test/pass/outline_device_kernel/test_outline_device_kernel.py -k test_outline_device_kernel_outlines_single_function
# 对应功能实现文件路径: kernel_gen/passes/outline_device_kernel.py
# 对应 spec 文件路径: spec/pass/outline_device_kernel.md
# 对应测试文件路径: test/pass/outline_device_kernel/test_outline_device_kernel.py
def test_outline_device_kernel_outlines_single_function() -> None:
    module = _parse_module(_BASIC_MODULE)

    OutlineDeviceKernelPass().run(module)
    module.verify()

    funcs = [op for op in module.ops if isinstance(op, func.FuncOp)]
    assert [op.sym_name.data for op in funcs] == ["kernel", "kernel_device"]

    wrapper, device = funcs
    assert "launch_block" not in wrapper.attributes
    assert "launch_thread" not in wrapper.attributes
    assert "launch_subthread" not in wrapper.attributes
    assert "shared_memory_size" not in wrapper.attributes
    assert device.attributes["shared_memory_size"] == _parse_module(
        "builtin.module { func.func @x() attributes { shared_memory_size = 0 : i64 } { func.return } }"
    ).ops.first.attributes["shared_memory_size"]

    wrapper_ops = list(wrapper.body.block.ops)
    assert [op.name for op in wrapper_ops] == [
        "symbol.const",
        "symbol.const",
        "symbol.const",
        "symbol.const",
        "arch.launch",
        "func.return",
    ]
    assert list(device.body.block.ops)[0].name == "test.op"

    printed = _print_ir(module)
    assert "@kernel_device" in printed
    assert 'symbol.const 4 : !symbol.int<"4">' in printed
    assert 'symbol.const 0 : !symbol.int<"0">' in printed
    assert "arch.launch<" in printed
    assert "shared_memory_size = 0 : i64" in printed


# TC-ODK-006
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证未标记函数保持原样，标记函数在模块内就地扩成 wrapper + device。
# 使用示例: pytest -q test/pass/outline_device_kernel/test_outline_device_kernel.py -k test_outline_device_kernel_leaves_unmarked_function_unchanged
# 对应功能实现文件路径: kernel_gen/passes/outline_device_kernel.py
# 对应 spec 文件路径: spec/pass/outline_device_kernel.md
# 对应测试文件路径: test/pass/outline_device_kernel/test_outline_device_kernel.py
def test_outline_device_kernel_leaves_unmarked_function_unchanged() -> None:
    module = _parse_module(
        """
builtin.module {
  func.func @helper(%arg0 : !nn.memory<[4], [1], f32, #nn.space<global>>) {
    "test.op"(%arg0) : (!nn.memory<[4], [1], f32, #nn.space<global>>) -> ()
    func.return
  }
  func.func @kernel(%arg0 : !nn.memory<[4], [1], f32, #nn.space<global>>) attributes {
    launch_block = 1 : i64,
    launch_thread = 2 : i64,
    launch_subthread = 1 : i64,
    shared_memory_size = 0 : i64
  } {
    "test.op"(%arg0) : (!nn.memory<[4], [1], f32, #nn.space<global>>) -> ()
    func.return
  }
}
"""
    )

    OutlineDeviceKernelPass().run(module)

    funcs = [op for op in module.ops if isinstance(op, func.FuncOp)]
    assert [op.sym_name.data for op in funcs] == ["helper", "kernel", "kernel_device"]
    helper = funcs[0]
    assert list(helper.body.block.ops)[0].name == "test.op"
    assert "launch_block" not in helper.attributes


# TC-ODK-007
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证只出现部分 launch attrs 时显式失败。
# 使用示例: pytest -q test/pass/outline_device_kernel/test_outline_device_kernel.py -k test_outline_device_kernel_rejects_partial_launch_attrs
# 对应功能实现文件路径: kernel_gen/passes/outline_device_kernel.py
# 对应 spec 文件路径: spec/pass/outline_device_kernel.md
# 对应测试文件路径: test/pass/outline_device_kernel/test_outline_device_kernel.py
def test_outline_device_kernel_rejects_partial_launch_attrs() -> None:
    module = _parse_module(
        """
builtin.module {
  func.func @kernel() attributes {
    launch_block = 1 : i64,
    launch_thread = 4 : i64
  } {
    func.return
  }
}
"""
    )

    with pytest.raises(
        PassContractError,
        match=(
            r"^function kernel must define "
            r"launch_block, launch_thread, and launch_subthread together$"
        ),
    ):
        OutlineDeviceKernelPass().run(module)


# TC-ODK-008
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证非正 launch extent 显式失败并给出稳定短语。
# 使用示例: pytest -q test/pass/outline_device_kernel/test_outline_device_kernel.py -k test_outline_device_kernel_rejects_non_positive_launch_extent
# 对应功能实现文件路径: kernel_gen/passes/outline_device_kernel.py
# 对应 spec 文件路径: spec/pass/outline_device_kernel.md
# 对应测试文件路径: test/pass/outline_device_kernel/test_outline_device_kernel.py
def test_outline_device_kernel_rejects_non_positive_launch_extent() -> None:
    module = _parse_module(
        """
builtin.module {
  func.func @kernel() attributes {
    launch_block = 1 : i64,
    launch_thread = 0 : i64,
    launch_subthread = 1 : i64,
    shared_memory_size = 0 : i64
  } {
    func.return
  }
}
"""
    )

    with pytest.raises(
        PassContractError,
        match=r"^function kernel launch_thread must be > 0$",
    ):
        OutlineDeviceKernelPass().run(module)


# TC-ODK-009
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 `shared_memory_size` 不是 int-like attr 时显式失败。
# 使用示例: pytest -q test/pass/outline_device_kernel/test_outline_device_kernel.py -k test_outline_device_kernel_rejects_non_int_like_shared_memory_size
# 对应功能实现文件路径: kernel_gen/passes/outline_device_kernel.py
# 对应 spec 文件路径: spec/pass/outline_device_kernel.md
# 对应测试文件路径: test/pass/outline_device_kernel/test_outline_device_kernel.py
def test_outline_device_kernel_rejects_non_int_like_shared_memory_size() -> None:
    module = _parse_module(
        """
builtin.module {
  func.func @kernel() attributes {
    launch_block = 1 : i64,
    launch_thread = 1 : i64,
    launch_subthread = 1 : i64,
    shared_memory_size = "bad"
  } {
    func.return
  }
}
"""
    )

    with pytest.raises(
        PassContractError,
        match=r"^function kernel shared_memory_size must be int-like attribute$",
    ):
        OutlineDeviceKernelPass().run(module)


# TC-ODK-010
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 `shared_memory_size` 为负值时显式失败。
# 使用示例: pytest -q test/pass/outline_device_kernel/test_outline_device_kernel.py -k test_outline_device_kernel_rejects_negative_shared_memory_size
# 对应功能实现文件路径: kernel_gen/passes/outline_device_kernel.py
# 对应 spec 文件路径: spec/pass/outline_device_kernel.md
# 对应测试文件路径: test/pass/outline_device_kernel/test_outline_device_kernel.py
def test_outline_device_kernel_rejects_negative_shared_memory_size() -> None:
    module = _parse_module(
        """
builtin.module {
  func.func @kernel() attributes {
    launch_block = 1 : i64,
    launch_thread = 1 : i64,
    launch_subthread = 1 : i64,
    shared_memory_size = -1 : i64
  } {
    func.return
  }
}
"""
    )

    with pytest.raises(
        PassContractError,
        match=r"^function kernel shared_memory_size must be >= 0$",
    ):
        OutlineDeviceKernelPass().run(module)


# TC-ODK-011
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证非零返回函数不会被隐式改写 ABI，而是显式失败。
# 使用示例: pytest -q test/pass/outline_device_kernel/test_outline_device_kernel.py -k test_outline_device_kernel_rejects_non_zero_result_function
# 对应功能实现文件路径: kernel_gen/passes/outline_device_kernel.py
# 对应 spec 文件路径: spec/pass/outline_device_kernel.md
# 对应测试文件路径: test/pass/outline_device_kernel/test_outline_device_kernel.py
def test_outline_device_kernel_rejects_non_zero_result_function() -> None:
    module = _parse_module(
        """
builtin.module {
  func.func @kernel() -> i32 attributes {
    launch_block = 1 : i64,
    launch_thread = 1 : i64,
    launch_subthread = 1 : i64,
    shared_memory_size = 0 : i64
  } {
    %0 = "test.op"() : () -> i32
    func.return %0 : i32
  }
}
"""
    )

    with pytest.raises(
        PassContractError,
        match=r"^function kernel must have zero results$",
    ):
        OutlineDeviceKernelPass().run(module)


# TC-ODK-012
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 功能说明: 验证 `_device` 命名冲突会在改写前显式失败。
# 使用示例: pytest -q test/pass/outline_device_kernel/test_outline_device_kernel.py -k test_outline_device_kernel_rejects_existing_device_name_conflict
# 对应功能实现文件路径: kernel_gen/passes/outline_device_kernel.py
# 对应 spec 文件路径: spec/pass/outline_device_kernel.md
# 对应测试文件路径: test/pass/outline_device_kernel/test_outline_device_kernel.py
def test_outline_device_kernel_rejects_existing_device_name_conflict() -> None:
    module = _parse_module(
        """
builtin.module {
  func.func @kernel() attributes {
    launch_block = 1 : i64,
    launch_thread = 1 : i64,
    launch_subthread = 1 : i64,
    shared_memory_size = 0 : i64
  } {
    func.return
  }
  func.func @kernel_device() {
    func.return
  }
}
"""
    )

    with pytest.raises(
        PassContractError,
        match=r"^outlined device function 'kernel_device' already exists$",
    ):
        OutlineDeviceKernelPass().run(module)
