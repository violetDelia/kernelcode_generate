"""outline-device-kernel invalid-attr expectation.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 验证不完整 launch attrs 与非正 launch extent 会触发稳定错误短语。
- 锁定失败路径不会静默跳过或退化成 no-op。

使用示例:
- `PYTHONPATH=. python expectation/pass/lowing/outline_device_kernel/invalid_attr.py`

关联文件:
- spec: [spec/pass/lowering/outline_device_kernel.md](../../../../spec/pass/lowering/outline_device_kernel.md)
- test: [test/pass/test_outline_device_kernel.py](../../../../test/pass/test_outline_device_kernel.py)
- 功能实现: [kernel_gen/passes/lowering/outline_device_kernel.py](../../../../kernel_gen/passes/lowering/outline_device_kernel.py)
"""

from __future__ import annotations

from pathlib import Path
import sys

from xdsl.dialects.builtin import ModuleOp
from xdsl.parser import Parser

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "kernel_gen").exists())
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.context import build_default_context
from kernel_gen.passes.lowering.outline_device_kernel import (
    OutlineDeviceKernelError,
    OutlineDeviceKernelPass,
)


def _parse_module(text: str) -> ModuleOp:
    """解析失败路径 expectation 的输入 module。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 为错误路径 expectation 提供统一的 parser 入口。

    使用示例:
    - module = _parse_module("builtin.module { func.func @main() { func.return } }")

    关联文件:
    - spec: [spec/pass/lowering/outline_device_kernel.md](../../../../spec/pass/lowering/outline_device_kernel.md)
    - test: [test/pass/test_outline_device_kernel.py](../../../../test/pass/test_outline_device_kernel.py)
    - 功能实现: [kernel_gen/passes/lowering/outline_device_kernel.py](../../../../kernel_gen/passes/lowering/outline_device_kernel.py)
    """

    return Parser(build_default_context(), text).parse_module()


def _expect_failure(text: str, expected: str) -> None:
    """验证 outline-device-kernel 对给定输入抛出稳定错误。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 运行 pass。
    - 比较异常文本是否与公开合同完全一致。

    使用示例:
    - _expect_failure(INPUT, "OutlineDeviceKernelError: ...")

    关联文件:
    - spec: [spec/pass/lowering/outline_device_kernel.md](../../../../spec/pass/lowering/outline_device_kernel.md)
    - test: [test/pass/test_outline_device_kernel.py](../../../../test/pass/test_outline_device_kernel.py)
    - 功能实现: [kernel_gen/passes/lowering/outline_device_kernel.py](../../../../kernel_gen/passes/lowering/outline_device_kernel.py)
    """

    try:
        OutlineDeviceKernelPass().run(_parse_module(text))
    except OutlineDeviceKernelError as exc:
        assert str(exc) == expected
    else:  # pragma: no cover - expectation 失败时直接抛错即可
        raise AssertionError(f"expected failure: {expected}")


def main() -> None:
    """运行 invalid attr expectation。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 覆盖“缺少 launch_subthread”与“launch_thread=0”两条失败路径。

    使用示例:
    - main()

    关联文件:
    - spec: [spec/pass/lowering/outline_device_kernel.md](../../../../spec/pass/lowering/outline_device_kernel.md)
    - test: [test/pass/test_outline_device_kernel.py](../../../../test/pass/test_outline_device_kernel.py)
    - 功能实现: [kernel_gen/passes/lowering/outline_device_kernel.py](../../../../kernel_gen/passes/lowering/outline_device_kernel.py)
    """

    print("[CASE-1] partial launch attrs")
    _expect_failure(
        """
builtin.module {
  func.func @kernel() attributes {
    launch_block = 1 : i64,
    launch_thread = 4 : i64
  } {
    func.return
  }
}
""",
        "OutlineDeviceKernelError: function kernel must define launch_block, launch_thread, and launch_subthread together",
    )

    print("[CASE-2] non-positive launch extent")
    _expect_failure(
        """
builtin.module {
  func.func @kernel() attributes {
    launch_block = 1 : i64,
    launch_thread = 0 : i64,
    launch_subthread = 1 : i64
  } {
    func.return
  }
}
""",
        "OutlineDeviceKernelError: function kernel launch_thread must be > 0",
    )


if __name__ == "__main__":
    main()
