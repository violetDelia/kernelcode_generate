"""tile expectation shared random/IR helpers.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 为 `expectation.pass.tile` 下的 reduce case 提供共享的 dtype、space 与 memory IR 文本生成逻辑。
- 统一返回固定的 rank-3 静态/动态维度对，避免各 case 各自维护同一组维度文本。
- 该 helper 只负责 expectation 文本拼接，不参与实际 IR 构造与 lowering 逻辑。

使用示例:
- `from expectation.pass.tile._random_shared import FLOAT_DTYPE, SPACE_ATTR, memory_ir, random_rank3_static_dynamic`
- `m, k, n, sym_m, sym_k, sym_n = random_rank3_static_dynamic()`
- `memory_ir([m, n], FLOAT_DTYPE)`

关联文件:
- spec: [`spec/pass/lowering/tile_reduce.md`](../../../spec/pass/lowering/tile_reduce.md)
- test: [`test/tools/test_expectation_case_runner.py`](../../../test/tools/test_expectation_case_runner.py)
- 功能实现: [`expectation/pass/tile/_random_shared.py`](./_random_shared.py)
"""

from __future__ import annotations

from collections.abc import Sequence

FLOAT_DTYPE = "f32"
SPACE_ATTR = "#nn.space<global>"


def _dim_text(dim: int | str) -> str:
    """把 shape 维度统一转成 expectation IR 文本。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - `int` 直接转成十进制文本。
    - `str` 维度名原样透传，供符号维度 expectation 文本复用。

    使用示例:
    - `_dim_text(4) -> "4"`
    - `_dim_text("M") -> "M"`

    关联文件:
    - spec: [`spec/pass/lowering/tile_reduce.md`](../../../spec/pass/lowering/tile_reduce.md)
    - test: [`test/tools/test_expectation_case_runner.py`](../../../test/tools/test_expectation_case_runner.py)
    - 功能实现: [`expectation/pass/tile/_random_shared.py`](./_random_shared.py)
    """

    return str(dim)


def _mul_text(lhs: str, rhs: str) -> str:
    """把两个 expectation 维度文本拼成乘积表达式。

    创建者: 金铲铲大作战
    最后更改: 金铲铲大作战

    功能说明:
    - 约定 `1` 为乘法幺元，便于构造最后一维 stride。
    - 其他组合使用 `*` 串联，保持 stable 文本输出。

    使用示例:
    - `_mul_text("K", "N") -> "K*N"`

    关联文件:
    - spec: [`spec/pass/lowering/tile_reduce.md`](../../../spec/pass/lowering/tile_reduce.md)
    - test: [`test/tools/test_expectation_case_runner.py`](../../../test/tools/test_expectation_case_runner.py)
    - 功能实现: [`expectation/pass/tile/_random_shared.py`](./_random_shared.py)
    """

    if lhs == "1":
        return rhs
    if rhs == "1":
        return lhs
    return f"{lhs}*{rhs}"


def _contiguous_strides(shape: Sequence[int | str]) -> list[str]:
    """根据 row-major 语义计算 contiguous stride 文本。

    创建者: 金铲铲大作战
    最后更改: 金铲铲大作战

    功能说明:
    - 从最右侧维度开始向左累乘，得到与 expectation 当前 IR 文本一致的 stride 表达。
    - 该函数只处理 expectation case 所需的 rank-1/rank-2/rank-3 文本，不承担实际运行时校验。

    使用示例:
    - `_contiguous_strides([4, 8]) -> ["8", "1"]`
    - `_contiguous_strides(["M", "N"]) -> ["N", "1"]`

    关联文件:
    - spec: [`spec/pass/lowering/tile_reduce.md`](../../../spec/pass/lowering/tile_reduce.md)
    - test: [`test/tools/test_expectation_case_runner.py`](../../../test/tools/test_expectation_case_runner.py)
    - 功能实现: [`expectation/pass/tile/_random_shared.py`](./_random_shared.py)
    """

    dims = [_dim_text(dim) for dim in shape]
    if not dims:
        return []

    strides = ["1"] * len(dims)
    running = "1"
    for index in range(len(dims) - 1, -1, -1):
        strides[index] = running
        running = _mul_text(dims[index], running)
    return strides


def memory_ir(shape: Sequence[int | str], dtype: str) -> str:
    """生成 expectation case 使用的 `!nn.memory<...>` 文本。

    创建者: 金铲铲大作战
    最后更改: 金铲铲大作战

    功能说明:
    - 把 shape 和 row-major stride 统一格式化成 `!nn.memory<[...], [...], dtype, #nn.space<global>>`。
    - 仅用于 expectation 文本拼接，不参与 IR 构造或 verifier。

    使用示例:
    - `memory_ir([4, 8], FLOAT_DTYPE)`
    - `memory_ir(["M", "N"], FLOAT_DTYPE)`

    关联文件:
    - spec: [`spec/pass/lowering/tile_reduce.md`](../../../spec/pass/lowering/tile_reduce.md)
    - test: [`test/tools/test_expectation_case_runner.py`](../../../test/tools/test_expectation_case_runner.py)
    - 功能实现: [`expectation/pass/tile/_random_shared.py`](./_random_shared.py)
    """

    shape_text = ", ".join(_dim_text(dim) for dim in shape)
    stride_text = ", ".join(_contiguous_strides(shape))
    return f"!nn.memory<[{shape_text}], [{stride_text}], {dtype}, {SPACE_ATTR}>"


def random_rank3_static_dynamic() -> tuple[int, int, int, str, str, str]:
    """返回 tile reduce expectation 需要的固定 rank-3 静态/动态维度。

    创建者: 金铲铲大作战
    最后更改: 金铲铲大作战

    功能说明:
    - 为 matmul / fc 两类 expectation case 统一提供静态三元组与符号三元组。
    - 该 helper 并不真正随机，返回值固定以保持 expectation 文本稳定。

    使用示例:
    - `STATIC_M, STATIC_K, STATIC_N, SYM_M, SYM_K, SYM_N = random_rank3_static_dynamic()`

    关联文件:
    - spec: [`spec/pass/lowering/tile_reduce.md`](../../../spec/pass/lowering/tile_reduce.md)
    - test: [`test/tools/test_expectation_case_runner.py`](../../../test/tools/test_expectation_case_runner.py)
    - 功能实现: [`expectation/pass/tile/_random_shared.py`](./_random_shared.py)
    """

    return 4, 8, 16, "M", "K", "N"


__all__ = [
    "FLOAT_DTYPE",
    "SPACE_ATTR",
    "memory_ir",
    "random_rank3_static_dynamic",
]
