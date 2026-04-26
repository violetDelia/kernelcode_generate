"""nn_lowering asset case collection tests.

创建者: jcc你莫辜负
最后一次更改: 金铲铲大作战

功能说明:
- 将 `test/pass/nn_lowering/` 下仍以资产形态存放的 nn_lowering case 收口为 collectable pytest。
- 直接复用现有 case 函数，避免重复搬运断言，同时让 `pytest -q test/pass` 能实际执行这些回归。
- 已经是 `test_*.py` 的 collectable 公开测试文件不再通过本文件跨文件复用测试函数。
- collectable 公开入口当前只桥接可直接通过的非 `test_*.py` 资产 case；`img2col1d/2d accepts_noncanonical_symbol_names` 继续留在各自资产文件单独维护，不计入本入口。

使用示例:
- pytest -q test/pass/nn_lowering/test_nn_lowering_asset_cases.py
- pytest -q test/pass/nn_lowering

关联文件:
- 功能实现: [kernel_gen/passes/lowering/nn_lowering/nn_lowering.py](kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
- 功能实现: [kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py](kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py)
- 功能实现: [kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py](kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py)
- 功能实现: [kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py](kernel_gen/passes/lowering/nn_lowering/element_binary_lowering.py)
- 功能实现: [kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py](kernel_gen/passes/lowering/nn_lowering/reduce_softmax_lowering.py)
- Spec 文档: [spec/pass/lowering/nn_lowering/spec.md](spec/pass/lowering/nn_lowering/spec.md)
- 测试文件: [test/pass/nn_lowering/test_nn_lowering_asset_cases.py](test/pass/nn_lowering/test_nn_lowering_asset_cases.py)
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from . import cast as cast_cases
from . import element_binary_add as element_binary_add_cases
from . import element_binary_div as element_binary_div_cases
from . import element_binary_mul as element_binary_mul_cases
from . import element_binary_sub as element_binary_sub_cases
from . import element_binary_truediv as element_binary_truediv_cases
from . import element_compare_eq as element_compare_eq_cases
from . import element_compare_ge as element_compare_ge_cases
from . import element_compare_gt as element_compare_gt_cases
from . import element_compare_le as element_compare_le_cases
from . import element_compare_lt as element_compare_lt_cases
from . import element_compare_ne as element_compare_ne_cases
from . import exp as exp_cases
from . import img2col1d as img2col1d_cases
from . import img2col2d as img2col2d_cases
from . import matmul as matmul_cases
from . import select as select_cases

ASSET_CASES: list[tuple[str, Callable[[], None]]] = [
    ("cast::test_lower_cast_bfloat16_to_dma_cast", cast_cases.test_lower_cast_bfloat16_to_dma_cast),
    ("cast::test_lower_cast_to_dma_cast", cast_cases.test_lower_cast_to_dma_cast),
    ("element_binary_add::test_lower_add_mixed_scalar_uses_dma_fill", element_binary_add_cases.test_lower_add_mixed_scalar_uses_dma_fill),
    ("element_binary_add::test_lower_add_to_kernel_binary_elewise", element_binary_add_cases.test_lower_add_to_kernel_binary_elewise),
    ("element_binary_div::test_lower_div_to_kernel_binary_elewise", element_binary_div_cases.test_lower_div_to_kernel_binary_elewise),
    ("element_binary_mul::test_lower_mul_to_kernel_binary_elewise", element_binary_mul_cases.test_lower_mul_to_kernel_binary_elewise),
    ("element_binary_sub::test_lower_sub_to_kernel_binary_elewise", element_binary_sub_cases.test_lower_sub_to_kernel_binary_elewise),
    ("element_binary_truediv::test_lower_truediv_to_kernel_binary_elewise", element_binary_truediv_cases.test_lower_truediv_to_kernel_binary_elewise),
    ("element_compare_eq::test_lower_eq_mixed_compare_to_kernel_binary_elewise", element_compare_eq_cases.test_lower_eq_mixed_compare_to_kernel_binary_elewise),
    ("element_compare_ge::test_lower_ge_to_kernel_binary_elewise", element_compare_ge_cases.test_lower_ge_to_kernel_binary_elewise),
    ("element_compare_gt::test_lower_gt_to_kernel_binary_elewise", element_compare_gt_cases.test_lower_gt_to_kernel_binary_elewise),
    ("element_compare_le::test_lower_le_to_kernel_binary_elewise", element_compare_le_cases.test_lower_le_to_kernel_binary_elewise),
    ("element_compare_lt::test_lower_lt_to_kernel_binary_elewise", element_compare_lt_cases.test_lower_lt_to_kernel_binary_elewise),
    ("element_compare_ne::test_lower_ne_to_kernel_binary_elewise", element_compare_ne_cases.test_lower_ne_to_kernel_binary_elewise),
    ("exp::test_nn_lowering_exp_dynamic", exp_cases.test_nn_lowering_exp_dynamic),
    ("exp::test_nn_lowering_exp_shape_mismatch", exp_cases.test_nn_lowering_exp_shape_mismatch),
    ("exp::test_nn_lowering_exp_static", exp_cases.test_nn_lowering_exp_static),
    ("img2col1d::test_nn_lowering_img2col1d_target", img2col1d_cases.test_nn_lowering_img2col1d_target),
    ("img2col2d::test_nn_lowering_img2col2d_target", img2col2d_cases.test_nn_lowering_img2col2d_target),
    ("matmul::test_nn_lowering_matmul_inside_symbol_for", matmul_cases.test_nn_lowering_matmul_inside_symbol_for),
    ("matmul::test_nn_lowering_matmul_target", matmul_cases.test_nn_lowering_matmul_target),
    ("select::test_lower_select_to_kernel_select", select_cases.test_lower_select_to_kernel_select),
]


@pytest.mark.parametrize("case_name, case_fn", ASSET_CASES, ids=[case[0] for case in ASSET_CASES])
def test_nn_lowering_asset_case(case_name: str, case_fn: Callable[[], None]) -> None:
    """执行 nn_lowering 资产 case。

    创建者: jcc你莫辜负
    最后一次更改: 金铲铲大作战

    功能说明:
    - 让当前可直接通过的非 `test_*.py` nn_lowering 资产回归变成真正可收集的 pytest。
    - 每个 case 仍然保留独立断言，只是统一挂接到 collectable 入口。
    - 已知仍需单独维护的 `img2col1d/2d accepts_noncanonical_symbol_names` 不纳入本入口。

    使用示例:
    - pytest -q test/pass/nn_lowering/test_nn_lowering_asset_cases.py -k element_binary_add

    关联文件:
    - spec: [spec/pass/lowering/nn_lowering/spec.md](spec/pass/lowering/nn_lowering/spec.md)
    - test: [test/pass/nn_lowering/test_nn_lowering_asset_cases.py](test/pass/nn_lowering/test_nn_lowering_asset_cases.py)
    - 功能实现: [kernel_gen/passes/lowering/nn_lowering/nn_lowering.py](kernel_gen/passes/lowering/nn_lowering/nn_lowering.py)
    """

    _ = case_name
    case_fn()
