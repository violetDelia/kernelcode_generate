"""emit_c npu_demo cost expectation：kernel.add。

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 验证 `tuner.cost(op_name="kernel.add")` 在 `target="npu_demo"` 下应发射为 `cost::add`。
- 锁定结果变量为 `S_INT cost0`，并允许后续 `symbol.add` 复用该结果。
- 只冻结节点级 cost helper 源码，不扩到 scalar return ABI。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.emit_c.npu_demo.cost.kernel_binary_add`

关联文件:
- spec: [`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)
- spec: [`spec/pass/tuning/launch_kernel_cost_func.md`](spec/pass/tuning/launch_kernel_cost_func.md)
- test: [`test/dsl/test_emit_c.py`](test/dsl/test_emit_c.py)
- 功能实现: [`expectation/dsl/emit_c/npu_demo/cost/kernel_binary_add.py`](expectation/dsl/emit_c/npu_demo/cost/kernel_binary_add.py)
- 功能实现: [`kernel_gen/dsl/emit_c.py`](kernel_gen/dsl/emit_c.py)
"""

from __future__ import annotations

from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "kernel_gen").exists())
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(CURRENT_DIR) in sys.path:
    sys.path.remove(str(CURRENT_DIR))

from expectation.dsl.emit_c.npu_demo._shared import run_emitc_case
from expectation.utils.case_runner import raise_if_failures, run_case

MEM_TYPE = "!nn.memory<[4], [1], f32, #nn.space<global>>"
CASE_TEXT = f"""// COMPILE_ARGS: --pass no-op
// CHECK: void cost_add_case(

builtin.module {{
  func.func @cost_add_case(
    %0 : {MEM_TYPE},
    %1 : {MEM_TYPE},
    %2 : {MEM_TYPE}
  ) {{
    %3 = tuner.cost(%0, %1, %2) {{space = #nn.space<global>, cost_kind = "compute", op_name = "kernel.add"}} : ({MEM_TYPE}, {MEM_TYPE}, {MEM_TYPE}) -> !symbol.int<"LOCAL">
    %4 = symbol.add %3, %3 : !symbol.int<"LOCAL">, !symbol.int<"LOCAL"> -> !symbol.int<"LOCAL">
    func.return
  }}
}}"""


def main() -> None:
    """运行 `kernel.add` 的 npu_demo cost emit_c expectation。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 运行单条静态 shape `kernel.add` cost case。
    - 断言 `tuner.cost` 已被 `cost::add` 替换，且 `symbol.add` 复用 `cost0`。

    使用示例:
    - `main()`

    关联文件:
    - spec: [`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)
    - test: [`test/dsl/test_emit_c.py`](test/dsl/test_emit_c.py)
    - 功能实现: [`expectation/dsl/emit_c/npu_demo/cost/kernel_binary_add.py`](expectation/dsl/emit_c/npu_demo/cost/kernel_binary_add.py)
    """

    failures: list[tuple[str, BaseException]] = []
    run_case(
        failures,
        "CASE-kernel-add-cost-compute",
        lambda: run_emitc_case(
            CASE_TEXT,
            source_path="expectation/dsl/emit_c/npu_demo/cost/kernel_binary_add.py",
            op_name="tuner.cost.kernel.add",
            expected_snippets=[
                '#include "include/npu_demo/npu_demo.h"',
                "S_INT cost0 = cost::add<GM, float, float, cost::CostKind::Compute>(arg0 /*out*/, arg1 /*lhs*/, arg2 /*rhs*/);",
                "S_INT v0 = (cost0 + cost0);",
            ],
            forbidden_snippets=[
                "tuner.cost(",
                '"kernel.add"',
            ],
        ),
    )
    raise_if_failures("emit_c npu_demo cost kernel.add expectation", failures)


if __name__ == "__main__":
    main()
