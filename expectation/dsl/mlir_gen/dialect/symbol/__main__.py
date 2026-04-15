"""DSL symbol family expectation 目录入口。

创建者: 守护最好的爱莉希雅
最后一次更改: 小李飞刀

功能说明:
- 运行当前 `expectation/dsl/mlir_gen/dialect/symbol` 目录下已纳入本轮交付范围的 expectation 入口。
- 聚合 `symbol.add` 与 `symbol.for` expectation，作为 `python -m expectation.dsl.mlir_gen.dialect.symbol` 的统一黑盒入口。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.symbol`

关联文件:
- spec: [`spec/dsl/mlir_gen.md`](spec/dsl/mlir_gen.md)
- spec: [`spec/dialect/symbol.md`](spec/dialect/symbol.md)
- test: [`test/dsl/test_mlir_gen.py`](test/dsl/test_mlir_gen.py)
- test: [`test/tools/test_mlir_gen_compare.py`](test/tools/test_mlir_gen_compare.py)
- 功能实现: [`expectation/dsl/mlir_gen/dialect/symbol/__main__.py`](expectation/dsl/mlir_gen/dialect/symbol/__main__.py)
- 功能实现: [`kernel_gen/dsl/mlir_gen/__init__.py`](kernel_gen/dsl/mlir_gen/__init__.py)
"""

from __future__ import annotations

from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.case_runner import raise_if_failures, run_case

try:
    from .element_binary.add import main as symbol_add_main
    from .for_loop import main as for_loop_main
except ImportError:
    from element_binary.add import main as symbol_add_main
    from for_loop import main as for_loop_main


def main() -> None:
    """运行 symbol family expectation 聚合入口。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 小李飞刀

    功能说明:
    - 顺序执行 `symbol.add` 与 `symbol.for` 两个已纳入公开合同的 expectation 入口。
    - 统一汇总 symbol family 下的 case 失败信息，便于目录级复测直接定位子入口。

    使用示例:
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.symbol`

    关联文件:
    - spec: [`spec/dsl/mlir_gen.md`](spec/dsl/mlir_gen.md)
    - test: [`test/dsl/test_mlir_gen.py`](test/dsl/test_mlir_gen.py)
    - 功能实现: [`expectation/dsl/mlir_gen/dialect/symbol/__main__.py`](expectation/dsl/mlir_gen/dialect/symbol/__main__.py)
    - 功能实现: [`expectation/utils/case_runner.py`](expectation/utils/case_runner.py)
    """

    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "dialect.symbol.element_binary.add", symbol_add_main)
    run_case(failures, "dialect.symbol.for_loop", for_loop_main)
    raise_if_failures("dsl mlir_gen symbol family expectation", failures)


if __name__ == "__main__":
    main()
