"""emit_c npu_demo cost expectation：dma.copy。

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 验证 `tuner.cost(op_name="dma.copy")` 在 `target="npu_demo"` 下应发射为 `cost::copy`。
- 锁定 compute kind 的 C++ helper 模板参数与 `target/source` 注释口径。
- 该 expectation 只覆盖节点级 cost helper 发射，不覆盖 pass 生成逻辑。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.emit_c.npu_demo.cost.dma_copy`

关联文件:
- spec: [`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)
- spec: [`spec/include/api/cost/Dma.md`](spec/include/api/cost/Dma.md)
- test: [`test/dsl/test_emit_c.py`](test/dsl/test_emit_c.py)
- 功能实现: [`expectation/dsl/emit_c/npu_demo/cost/dma_copy.py`](expectation/dsl/emit_c/npu_demo/cost/dma_copy.py)
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
// CHECK: void cost_copy_case(

builtin.module {{
  func.func @cost_copy_case(
    %0 : {MEM_TYPE},
    %1 : {MEM_TYPE}
  ) {{
    %2 = tuner.cost(%0, %1) {{cost_kind = "compute", op_name = "dma.copy"}} : ({MEM_TYPE}, {MEM_TYPE}) -> !symbol.int<"LOCAL">
    func.return
  }}
}}"""


def main() -> None:
    """运行 `dma.copy` 的 npu_demo cost emit_c expectation。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 运行单条静态 shape `dma.copy` cost case。
    - 断言 `tuner.cost` 已被 `cost::copy` 替换，且参数仍保持 `target/source` 顺序。

    使用示例:
    - `main()`

    关联文件:
    - spec: [`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)
    - test: [`test/dsl/test_emit_c.py`](test/dsl/test_emit_c.py)
    - 功能实现: [`expectation/dsl/emit_c/npu_demo/cost/dma_copy.py`](expectation/dsl/emit_c/npu_demo/cost/dma_copy.py)
    """

    failures: list[tuple[str, BaseException]] = []
    run_case(
        failures,
        "CASE-dma-copy-cost-compute",
        lambda: run_emitc_case(
            CASE_TEXT,
            source_path="expectation/dsl/emit_c/npu_demo/cost/dma_copy.py",
            op_name="tuner.cost.dma.copy",
            expected_snippets=[
                '#include "include/npu_demo/npu_demo.h"',
                "S_INT cost0 = cost::copy<GM, GM, float, cost::CostKind::Compute>(arg0 /*target*/, arg1 /*source*/);",
            ],
            forbidden_snippets=[
                "tuner.cost(",
                '"dma.copy"',
            ],
        ),
    )
    raise_if_failures("emit_c npu_demo cost dma.copy expectation", failures)


if __name__ == "__main__":
    main()
