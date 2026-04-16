"""outline-device-kernel multi-function expectation.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 验证未标记函数保持原样，只有显式 launch attrs 的函数会被 outline。
- 锁定模块内函数顺序为 `helper -> wrapper -> device`。

使用示例:
- `PYTHONPATH=. python expectation/pass/lowing/outline_device_kernel/multi_function.py`

关联文件:
- spec: [spec/pass/lowering/outline_device_kernel.md](../../../../spec/pass/lowering/outline_device_kernel.md)
- test: [test/pass/test_outline_device_kernel.py](../../../../test/pass/test_outline_device_kernel.py)
- 功能实现: [kernel_gen/passes/lowering/outline_device_kernel.py](../../../../kernel_gen/passes/lowering/outline_device_kernel.py)
"""

from __future__ import annotations

from pathlib import Path
import sys

from xdsl.dialects import func
from xdsl.dialects.builtin import ModuleOp
from xdsl.dialects.test import Test
from xdsl.parser import Parser

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "kernel_gen").exists())
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.context import build_default_context
from kernel_gen.passes.lowering.outline_device_kernel import OutlineDeviceKernelPass

_INPUT_IR = """
builtin.module {
  func.func @helper(%arg0 : !nn.memory<[4], [1], f32, #nn.space<global>>) {
    "test.op"(%arg0) : (!nn.memory<[4], [1], f32, #nn.space<global>>) -> ()
    func.return
  }
  func.func @kernel(%arg0 : !nn.memory<[4], [1], f32, #nn.space<global>>) attributes {
    launch_block = 1 : i64,
    launch_thread = 2 : i64,
    launch_subthread = 1 : i64
  } {
    "test.op"(%arg0) : (!nn.memory<[4], [1], f32, #nn.space<global>>) -> ()
    func.return
  }
}
"""


def _parse_module(text: str) -> ModuleOp:
    """解析多函数 expectation 的输入 module。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 复用默认上下文并额外加载 `test` dialect。

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


def main() -> None:
    """运行多函数 success path expectation。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 验证 `helper` 保持不变。
    - 验证 `kernel` 就地改写为 wrapper，并新增 `kernel_device`。

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
    assert [op.sym_name.data for op in funcs] == ["helper", "kernel", "kernel_device"]
    assert list(funcs[0].body.block.ops)[0].name == "test.op"
    assert list(funcs[1].body.block.ops)[3].name == "arch.launch"
    assert list(funcs[2].body.block.ops)[0].name == "test.op"

    print(module)


if __name__ == "__main__":
    main()
