"""DSL nn family expectation 目录入口。

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 运行当前 `expectation/dsl/mlir_gen/dialect/nn` 目录下已存在的 expectation 入口。
- 聚合 `broadcast`、`broadcast_to`、`conv`、`fc`、`img2col`、`matmul`、`reduce` 与 `softmax` expectation，作为 `python -m expectation.dsl.mlir_gen.dialect.nn` 的统一黑盒入口。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn`

关联文件:
- spec: [`spec/dsl/mlir_gen.md`](spec/dsl/mlir_gen.md)
- spec: [`spec/dialect/nn.md`](spec/dialect/nn.md)
- test: [`test/dsl/test_mlir_gen.py`](test/dsl/test_mlir_gen.py)
- test: [`test/tools/test_mlir_gen_compare.py`](test/tools/test_mlir_gen_compare.py)
- 功能实现: [`expectation/dsl/mlir_gen/dialect/nn/__main__.py`](expectation/dsl/mlir_gen/dialect/nn/__main__.py)
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
    from .broadcast import main as broadcast_main
    from .broadcast_to import main as broadcast_to_main
    from .conv import main as conv_main
    from .fc import main as fc_main
    from .img2col1d import main as img2col1d_main
    from .img2col2d import main as img2col2d_main
    from .matmul import main as matmul_main
    from .reduce.reduce_max import main as reduce_max_main
    from .reduce.reduce_min import main as reduce_min_main
    from .reduce.reduce_sum import main as reduce_sum_main
    from .softmax import main as softmax_main
except ImportError:
    from broadcast import main as broadcast_main
    from broadcast_to import main as broadcast_to_main
    from conv import main as conv_main
    from fc import main as fc_main
    from img2col1d import main as img2col1d_main
    from img2col2d import main as img2col2d_main
    from matmul import main as matmul_main
    from reduce.reduce_max import main as reduce_max_main
    from reduce.reduce_min import main as reduce_min_main
    from reduce.reduce_sum import main as reduce_sum_main
    from softmax import main as softmax_main


def main() -> None:
    """运行 nn family expectation 聚合入口。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 顺序执行 `broadcast`、`broadcast_to`、`conv`、`fc`、`img2col1d`、`img2col2d`、`matmul`、`reduce_*` 与 `softmax`。
    - 汇总 nn family 目录下各子 expectation 的失败信息，保证 `python -m` 入口输出稳定。

    使用示例:
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn`

    关联文件:
    - spec: [`spec/dsl/mlir_gen.md`](spec/dsl/mlir_gen.md)
    - test: [`test/dsl/test_mlir_gen.py`](test/dsl/test_mlir_gen.py)
    - 功能实现: [`expectation/dsl/mlir_gen/dialect/nn/__main__.py`](expectation/dsl/mlir_gen/dialect/nn/__main__.py)
    - 功能实现: [`expectation/utils/case_runner.py`](expectation/utils/case_runner.py)
    """

    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "dialect.nn.broadcast", broadcast_main)
    run_case(failures, "dialect.nn.broadcast_to", broadcast_to_main)
    run_case(failures, "dialect.nn.conv", conv_main)
    run_case(failures, "dialect.nn.fc", fc_main)
    run_case(failures, "dialect.nn.img2col1d", img2col1d_main)
    run_case(failures, "dialect.nn.img2col2d", img2col2d_main)
    run_case(failures, "dialect.nn.matmul", matmul_main)
    run_case(failures, "dialect.nn.reduce_max", reduce_max_main)
    run_case(failures, "dialect.nn.reduce_min", reduce_min_main)
    run_case(failures, "dialect.nn.reduce_sum", reduce_sum_main)
    run_case(failures, "dialect.nn.softmax", softmax_main)
    raise_if_failures("dsl mlir_gen nn family expectation", failures)


if __name__ == "__main__":
    main()
