"""launch-kernel-cost-func expectation runner.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 汇总 `launch-kernel-cost-func` 的公开 expectation 子资产。
- 依次运行 `basic_all.py`、`shared_callee_once.py` 与 `invalid_kind.py`，冻结目录级入口合同。

使用示例:
- `PYTHONPATH=. python expectation/pass/tuning/launch_kernel_cost_func`

关联文件:
- spec: [spec/pass/tuning/launch_kernel_cost_func.md](../../../../spec/pass/tuning/launch_kernel_cost_func.md)
- test: [test/pass/test_launch_kernel_cost_func.py](../../../../test/pass/test_launch_kernel_cost_func.py)
- 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](../../../../kernel_gen/passes/tuning/launch_kernel_cost_func.py)
"""

from __future__ import annotations

from pathlib import Path
import sys

RUNNER_DIR = Path(__file__).resolve().parent
if str(RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(RUNNER_DIR))

import basic_all
import invalid_kind
import shared_callee_once


def main() -> None:
    """运行 launch-kernel-cost-func 目录级 expectation。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 串行运行三个 expectation 子入口。
    - 若任一子入口失败，则直接向上抛错，便于脚本与 CI 按 exit code 判定。

    使用示例:
    - main()

    关联文件:
    - spec: [spec/pass/tuning/launch_kernel_cost_func.md](../../../../spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [test/pass/test_launch_kernel_cost_func.py](../../../../test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](../../../../kernel_gen/passes/tuning/launch_kernel_cost_func.py)
    """

    print("[RUN] basic_all")
    basic_all.main()
    print("[RUN] shared_callee_once")
    shared_callee_once.main()
    print("[RUN] invalid_kind")
    invalid_kind.main()
    print("[OK] launch-kernel-cost-func expectation passed")


if __name__ == "__main__":
    main()
