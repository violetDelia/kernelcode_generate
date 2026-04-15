"""DSL mlir_gen expectation 目录入口。

创建者: 大闸蟹
最后一次更改: 小李飞刀

功能说明:
- 运行当前 `expectation/dsl/mlir_gen` 目录下已纳入本轮交付范围的 expectation 入口。
- 聚合顶层脚本与 `dialect/nn`、`dialect/symbol` family 入口，作为 `python -m expectation.dsl.mlir_gen` 的统一黑盒入口。
- 每个子入口单独执行并汇总失败，便于直接定位具体脚本或 family。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen`

关联文件:
- spec: [`spec/dsl/mlir_gen.md`](spec/dsl/mlir_gen.md)
- spec: [`spec/tools/mlir_gen_compare.md`](spec/tools/mlir_gen_compare.md)
- test: [`test/dsl/test_mlir_gen.py`](test/dsl/test_mlir_gen.py)
- test: [`test/tools/test_mlir_gen_compare.py`](test/tools/test_mlir_gen_compare.py)
- 功能实现: [`expectation/dsl/mlir_gen/__main__.py`](expectation/dsl/mlir_gen/__main__.py)
- 功能实现: [`kernel_gen/dsl/mlir_gen/__init__.py`](kernel_gen/dsl/mlir_gen/__init__.py)
"""

from __future__ import annotations

from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

REPO_ROOT = CURRENT_DIR.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.case_runner import raise_if_failures, run_case

try:
    from .import_bound_helper import main as import_bound_helper_main
    from .return_type_from_body_not_signature import main as return_type_main
    from .dialect.nn.__main__ import main as nn_main
    from .dialect.symbol.__main__ import main as symbol_main
except ImportError:
    from import_bound_helper import main as import_bound_helper_main
    from return_type_from_body_not_signature import main as return_type_main
    from dialect.nn.__main__ import main as nn_main
    from dialect.symbol.__main__ import main as symbol_main


def main() -> None:
    """运行 dsl mlir_gen 根目录 expectation 聚合入口。

    创建者: 大闸蟹
    最后一次更改: 小李飞刀

    功能说明:
    - 顺序执行 `import_bound_helper`、`return_type_from_body_not_signature`、`dialect.nn` 与 `dialect.symbol`。
    - 通过 `run_case(...)` 汇总各子入口异常，再由 `raise_if_failures(...)` 输出统一失败摘要。

    使用示例:
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen`

    关联文件:
    - spec: [`spec/dsl/mlir_gen.md`](spec/dsl/mlir_gen.md)
    - test: [`test/dsl/test_mlir_gen.py`](test/dsl/test_mlir_gen.py)
    - 功能实现: [`expectation/dsl/mlir_gen/__main__.py`](expectation/dsl/mlir_gen/__main__.py)
    - 功能实现: [`expectation/utils/case_runner.py`](expectation/utils/case_runner.py)
    """

    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "top.import_bound_helper", import_bound_helper_main)
    run_case(failures, "top.return_type_from_body_not_signature", return_type_main)
    run_case(failures, "dialect.nn", nn_main)
    run_case(failures, "dialect.symbol", symbol_main)
    raise_if_failures("dsl mlir_gen package expectation", failures)


if __name__ == "__main__":
    main()
