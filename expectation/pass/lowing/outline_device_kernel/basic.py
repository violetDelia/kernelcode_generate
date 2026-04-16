"""outline-device-kernel basic expectation.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 验证单个带 launch attrs 的函数会被 outline 成 `wrapper + device` 双函数。
- 锁定 wrapper 中 `symbol.const + arch.launch + func.return` 的最小 IR 形状。

使用示例:
- `PYTHONPATH=. python expectation/pass/lowing/outline_device_kernel/basic.py`

关联文件:
- spec: [spec/pass/lowering/outline_device_kernel.md](../../../../spec/pass/lowering/outline_device_kernel.md)
- test: [test/pass/test_outline_device_kernel.py](../../../../test/pass/test_outline_device_kernel.py)
- 功能实现: [kernel_gen/passes/lowering/outline_device_kernel.py](../../../../kernel_gen/passes/lowering/outline_device_kernel.py)
"""

from __future__ import annotations

from io import StringIO
from pathlib import Path
import sys

from xdsl.dialects import func
from xdsl.dialects.builtin import ModuleOp
from xdsl.dialects.test import Test
from xdsl.parser import Parser
from xdsl.printer import Printer

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "kernel_gen").exists())
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.context import build_default_context
from kernel_gen.passes.lowering.outline_device_kernel import OutlineDeviceKernelPass

_INPUT_IR = """
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


def _parse_module(text: str) -> ModuleOp:
    """解析 expectation 里的测试 module 文本。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 构造加载默认 dialect 与 `test` dialect 的上下文。
    - 返回供 pass 直接运行的 `ModuleOp`。

    使用示例:
    - module = _parse_module(_INPUT_IR)

    关联文件:
    - spec: [spec/pass/lowering/outline_device_kernel.md](../../../../spec/pass/lowering/outline_device_kernel.md)
    - test: [test/pass/test_outline_device_kernel.py](../../../../test/pass/test_outline_device_kernel.py)
    - 功能实现: [kernel_gen/passes/lowering/outline_device_kernel.py](../../../../kernel_gen/passes/lowering/outline_device_kernel.py)
    """

    ctx = build_default_context()
    ctx.load_dialect(Test)
    return Parser(ctx, text).parse_module()


def _print_module(module: ModuleOp) -> str:
    """打印 module 为断言友好的稳定文本。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 使用显式 `Printer` 获取完整 module 文本。

    使用示例:
    - text = _print_module(module)

    关联文件:
    - spec: [spec/pass/lowering/outline_device_kernel.md](../../../../spec/pass/lowering/outline_device_kernel.md)
    - test: [test/pass/test_outline_device_kernel.py](../../../../test/pass/test_outline_device_kernel.py)
    - 功能实现: [kernel_gen/passes/lowering/outline_device_kernel.py](../../../../kernel_gen/passes/lowering/outline_device_kernel.py)
    """

    stream = StringIO()
    Printer(stream=stream).print_op(module)
    return stream.getvalue()


def main() -> None:
    """运行单函数 outline 成功路径 expectation。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 验证 wrapper/device 双函数命名与 `shared_memory_size` 落点。
    - 验证 wrapper 中只保留三条 `symbol.const`、单个 `arch.launch` 与 `func.return`。

    使用示例:
    - main()

    关联文件:
    - spec: [spec/pass/lowering/outline_device_kernel.md](../../../../spec/pass/lowering/outline_device_kernel.md)
    - test: [test/pass/test_outline_device_kernel.py](../../../../test/pass/test_outline_device_kernel.py)
    - 功能实现: [kernel_gen/passes/lowering/outline_device_kernel.py](../../../../kernel_gen/passes/lowering/outline_device_kernel.py)
    """

    module = _parse_module(_INPUT_IR)
    OutlineDeviceKernelPass().run(module)
    module.verify()
    funcs = [op for op in module.ops if isinstance(op, func.FuncOp)]
    assert [op.sym_name.data for op in funcs] == ["kernel", "kernel_device"]

    wrapper, device = funcs
    wrapper_ops = list(wrapper.body.block.ops)
    assert [op.name for op in wrapper_ops] == [
        "symbol.const",
        "symbol.const",
        "symbol.const",
        "arch.launch",
        "func.return",
    ]
    assert "shared_memory_size" not in wrapper.attributes
    assert "shared_memory_size" in device.attributes
    assert list(device.body.block.ops)[0].name == "test.op"

    printed = _print_module(module)
    print(printed)
    assert "@kernel_device" in printed
    assert "arch.launch<" in printed
    assert 'symbol.const 4 : !symbol.int<"4">' in printed


if __name__ == "__main__":
    main()
