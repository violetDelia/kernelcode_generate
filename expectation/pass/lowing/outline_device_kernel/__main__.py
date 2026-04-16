"""outline-device-kernel expectation runner.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 汇总 `outline-device-kernel` 的公开 expectation 子资产。
- 依次运行 `basic.py`、`multi_function.py` 与 `invalid_attr.py`，冻结目录级入口合同。

使用示例:
- `PYTHONPATH=. python expectation/pass/lowing/outline_device_kernel`

关联文件:
- spec: [spec/pass/lowering/outline_device_kernel.md](../../../../spec/pass/lowering/outline_device_kernel.md)
- test: [test/pass/test_outline_device_kernel.py](../../../../test/pass/test_outline_device_kernel.py)
- 功能实现: [kernel_gen/passes/lowering/outline_device_kernel.py](../../../../kernel_gen/passes/lowering/outline_device_kernel.py)
"""

from __future__ import annotations

from pathlib import Path
import sys

RUNNER_DIR = Path(__file__).resolve().parent
if str(RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(RUNNER_DIR))

import basic
import invalid_attr
import multi_function


def main() -> None:
    """运行 outline-device-kernel 目录级 expectation。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 串行运行三个 expectation 子入口。
    - 若任一子入口失败，则直接向上抛错，便于脚本与 CI 按 exit code 判定。

    使用示例:
    - main()

    关联文件:
    - spec: [spec/pass/lowering/outline_device_kernel.md](../../../../spec/pass/lowering/outline_device_kernel.md)
    - test: [test/pass/test_outline_device_kernel.py](../../../../test/pass/test_outline_device_kernel.py)
    - 功能实现: [kernel_gen/passes/lowering/outline_device_kernel.py](../../../../kernel_gen/passes/lowering/outline_device_kernel.py)
    """

    print("[RUN] basic")
    basic.main()
    print("[RUN] multi_function")
    multi_function.main()
    print("[RUN] invalid_attr")
    invalid_attr.main()
    print("[OK] outline-device-kernel expectation passed")


if __name__ == "__main__":
    main()
