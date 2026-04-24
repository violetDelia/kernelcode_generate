"""pass nn_lowering expectation 目录入口。
[immutable-file]


创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 运行 `expectation/pass/lowing/nn_lowering` 目录下的全部 expectation 入口。
- 聚合单文件 expectation 与 family 子目录入口，作为 `python -m expectation.pass.lowing.nn_lowering` 的统一黑盒入口。
- 每个子入口单独执行并汇总失败，便于直接定位到具体 family 或单个 op。

使用示例:
- `PYTHONPATH=. python -m expectation.pass.lowing.nn_lowering`

关联文件:
- spec: [`spec/pass/lowering/nn_lowering.md`](spec/pass/lowering/nn_lowering.md)
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
- test: [`test/pass/nn_lowering`](test/pass/nn_lowering)
- 功能实现: [`expectation/pass/lowing/nn_lowering/__main__.py`](expectation/pass/lowing/nn_lowering/__main__.py)
- 功能实现: [`kernel_gen/passes/lowering/nn_lowering`](kernel_gen/passes/lowering/nn_lowering)
"""

from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

REPO_ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "expectation").exists() and (parent / "kernel_gen").exists()
)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.case_runner import raise_if_failures, run_case

try:
    from .broadcast import main as broadcast_main
    from .cast import main as cast_main
    from .element_binary.__main__ import main as element_binary_main
    from .element_compare import main as element_compare_main
    from .exp import main as exp_main
    from .img2col.__main__ import main as img2col_main
    from .matmul import main as matmul_main
    from .reduce.__main__ import main as reduce_main
    from .select import main as select_main
    from .transpose import main as transpose_main
except ImportError:
    def _load_from_path(module_name: str, file_path: Path):
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module

    broadcast_main = _load_from_path("nn_lowering_broadcast", CURRENT_DIR / "broadcast.py").main
    cast_main = _load_from_path("nn_lowering_cast", CURRENT_DIR / "cast.py").main
    element_binary_main = _load_from_path(
        "nn_lowering_element_binary_main",
        CURRENT_DIR / "element_binary" / "__main__.py",
    ).main
    element_compare_main = _load_from_path(
        "nn_lowering_element_compare",
        CURRENT_DIR / "element_compare.py",
    ).main
    exp_main = _load_from_path("nn_lowering_exp", CURRENT_DIR / "exp.py").main
    img2col_main = _load_from_path(
        "nn_lowering_img2col_main",
        CURRENT_DIR / "img2col" / "__main__.py",
    ).main
    matmul_main = _load_from_path("nn_lowering_matmul", CURRENT_DIR / "matmul.py").main
    reduce_main = _load_from_path(
        "nn_lowering_reduce_main",
        CURRENT_DIR / "reduce" / "__main__.py",
    ).main
    select_main = _load_from_path("nn_lowering_select", CURRENT_DIR / "select.py").main
    transpose_main = _load_from_path("nn_lowering_transpose", CURRENT_DIR / "transpose.py").main


def main() -> None:
    failures: list[tuple[str, BaseException]] = []

    run_case(failures, "broadcast", broadcast_main)
    run_case(failures, "cast", cast_main)
    run_case(failures, "element_binary", element_binary_main)
    run_case(failures, "element_compare", element_compare_main)
    run_case(failures, "exp", exp_main)
    run_case(failures, "img2col", img2col_main)
    run_case(failures, "matmul", matmul_main)
    run_case(failures, "reduce", reduce_main)
    run_case(failures, "select", select_main)
    run_case(failures, "transpose", transpose_main)

    raise_if_failures("pass nn_lowering expectation package", failures)


if __name__ == "__main__":
    main()
