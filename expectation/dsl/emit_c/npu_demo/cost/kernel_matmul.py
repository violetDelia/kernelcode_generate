"""emit_c npu_demo cost expectation：kernel.matmul。

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 验证 `tuner.cost(op_name="kernel.matmul")` 在 `target="npu_demo"` 下应发射为 `cost::matmul`。
- 锁定 memory kind 会映射到 `cost::CostKind::Memory`。
- 只冻结节点级 helper 调用，不引入额外 wrapper 语义。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.emit_c.npu_demo.cost.kernel_matmul`

关联文件:
- spec: [`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)
- spec: [`spec/include/api/cost/Kernel.md`](spec/include/api/cost/Kernel.md)
- test: [`test/dsl/test_emit_c.py`](test/dsl/test_emit_c.py)
- 功能实现: [`expectation/dsl/emit_c/npu_demo/cost/kernel_matmul.py`](expectation/dsl/emit_c/npu_demo/cost/kernel_matmul.py)
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

MEM_TYPE = "!nn.memory<[2, 2], [2, 1], f32, #nn.space<global>>"
CASE_TEXT = f"""// COMPILE_ARGS: --pass no-op
// CHECK: void cost_matmul_case(

builtin.module {{
  func.func @cost_matmul_case(
    %0 : {MEM_TYPE},
    %1 : {MEM_TYPE},
    %2 : {MEM_TYPE}
  ) {{
    %3 = tuner.cost(%0, %1, %2) {{cost_kind = "memory", op_name = "kernel.matmul"}} : ({MEM_TYPE}, {MEM_TYPE}, {MEM_TYPE}) -> !symbol.int<"LOCAL">
    func.return
  }}
}}"""


def main() -> None:
    """运行 `kernel.matmul` 的 npu_demo cost emit_c expectation。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 运行单条静态 shape `kernel.matmul` cost case。
    - 断言 `tuner.cost` 已被 `cost::matmul` 替换，且 `memory` kind 已落到模板参数。

    使用示例:
    - `main()`

    关联文件:
    - spec: [`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)
    - test: [`test/dsl/test_emit_c.py`](test/dsl/test_emit_c.py)
    - 功能实现: [`expectation/dsl/emit_c/npu_demo/cost/kernel_matmul.py`](expectation/dsl/emit_c/npu_demo/cost/kernel_matmul.py)
    """

    failures: list[tuple[str, BaseException]] = []
    run_case(
        failures,
        "CASE-kernel-matmul-cost-memory",
        lambda: run_emitc_case(
            CASE_TEXT,
            source_path="expectation/dsl/emit_c/npu_demo/cost/kernel_matmul.py",
            op_name="tuner.cost.kernel.matmul",
            expected_snippets=[
                '#include "include/npu_demo/npu_demo.h"',
                "S_INT cost0 = cost::matmul<GM, GM, GM, float, float, float, cost::CostKind::Memory>(arg0 /*out*/, arg1 /*lhs*/, arg2 /*rhs*/);",
            ],
            forbidden_snippets=[
                "tuner.cost(",
                '"kernel.matmul"',
            ],
        ),
    )
    raise_if_failures("emit_c npu_demo cost kernel.matmul expectation", failures)


if __name__ == "__main__":
    main()
