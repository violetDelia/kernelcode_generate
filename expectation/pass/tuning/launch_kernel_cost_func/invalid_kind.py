"""launch-kernel-cost-func invalid-kind expectation.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 验证非法 `kind` 会触发稳定错误短语。
- 锁定失败路径不会静默退化成默认 `all`。

使用示例:
- `PYTHONPATH=. python expectation/pass/tuning/launch_kernel_cost_func/invalid_kind.py`

关联文件:
- spec: [spec/pass/tuning/launch_kernel_cost_func.md](../../../../spec/pass/tuning/launch_kernel_cost_func.md)
- test: [test/pass/test_launch_kernel_cost_func.py](../../../../test/pass/test_launch_kernel_cost_func.py)
- 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](../../../../kernel_gen/passes/tuning/launch_kernel_cost_func.py)
"""

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "kernel_gen").exists())
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.passes.tuning.launch_kernel_cost_func import LaunchKernelCostFuncError, LaunchKernelCostFuncPass


def _print_case_ir(case_name: str, case_desc: str, text: str, *, title: str) -> None:
    """按统一注释格式打印单个 case 文本。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 打印 `[CASE-x]` 短标题与 `# CASE-x` 注释头。
    - 让失败路径 expectation 不依赖外部共享 helper。

    使用示例:
    - _print_case_ir("CASE-1", "非法 kind 输入", case_text, title="输入")

    关联文件:
    - spec: [spec/pass/tuning/launch_kernel_cost_func.md](../../../../spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [test/pass/test_launch_kernel_cost_func.py](../../../../test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](../../../../kernel_gen/passes/tuning/launch_kernel_cost_func.py)
    """

    print(f"[{case_name}] {case_desc}")
    print(f"# {case_name} {title}：{case_desc}")
    print(text.strip())


def main() -> None:
    """运行非法 `kind` expectation。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 覆盖 `kind=\"invalid\"` 的稳定失败路径。

    使用示例:
    - main()

    关联文件:
    - spec: [spec/pass/tuning/launch_kernel_cost_func.md](../../../../spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [test/pass/test_launch_kernel_cost_func.py](../../../../test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](../../../../kernel_gen/passes/tuning/launch_kernel_cost_func.py)
    """

    case_text = "LaunchKernelCostFuncPass(kind='invalid')"
    _print_case_ir("CASE-1", "非法 kind 输入", case_text, title="输入")
    try:
        LaunchKernelCostFuncPass(kind="invalid")
    except LaunchKernelCostFuncError as exc:
        assert str(exc) == "LaunchKernelCostFuncError: kind must be one of compute, move, all"
    else:  # pragma: no cover - expectation 失败时直接抛错即可
        raise AssertionError("expected invalid kind failure")


if __name__ == "__main__":
    main()
