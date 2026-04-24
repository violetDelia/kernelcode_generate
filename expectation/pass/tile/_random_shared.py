"""tile expectation shared random/IR helpers.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 为 `expectation.pass.tile` 家族提供共享的 dtype、space 与 memory IR 文本生成逻辑。
- 统一返回固定的 rank-1 / rank-2 / rank-3 静态/动态维度对，避免各 case 各自维护同一组维度文本。
- 统一提供 arithmetic / boolean / float 的文本常量，便于 analysis、elewise 与 reduce 目录入口复用。
- 该 helper 只负责 expectation 文本拼接，不参与实际 IR 构造与 lowering 逻辑。

使用示例:
- `from expectation.pass.tile._random_shared import ARITH_DTYPE, FLOAT_DTYPE, memory_ir, random_rank2_static_dynamic`
- `m, n, sym_m, sym_n = random_rank2_static_dynamic()`
- `memory_ir([m, n], ARITH_DTYPE)`
- `from expectation.pass.tile._random_shared import FLOAT_DTYPE_IR, random_rank3_static_dynamic`
- `memory_ir([m, k, n], FLOAT_DTYPE_IR)`

关联文件:
- spec: [`spec/pass/lowering/tile_reduce.md`](../../../spec/pass/lowering/tile_reduce.md)
- test: [`test/tools/test_expectation_case_runner.py`](../../../test/tools/test_expectation_case_runner.py)
- 功能实现: [`expectation/pass/tile/_random_shared.py`](./_random_shared.py)
"""

from __future__ import annotations

from collections.abc import Sequence

ARITH_DTYPE = "i32"
ARITH_DTYPE_IR = "i32"
BOOL_DTYPE = "i1"
BOOL_DTYPE_IR = "i1"
FLOAT_DTYPE = "f32"
FLOAT_DTYPE_IR = "f32"
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


def random_rank1_static_dynamic() -> tuple[int, str]:
    """返回 tile expectation 需要的固定 rank-1 静态/动态维度。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 为 `dma.broadcast` / `kernel.binary_elewise` 的 rank-1 case 提供固定维度。
    - 该 helper 并不真正随机，返回值固定以保持 expectation 文本稳定。

    使用示例:
    - `STATIC_P, SYM_P = random_rank1_static_dynamic()`

    关联文件:
    - spec: [`spec/pass/lowering/tile_reduce.md`](../../../spec/pass/lowering/tile_reduce.md)
    - test: [`test/tools/test_expectation_case_runner.py`](../../../test/tools/test_expectation_case_runner.py)
    - 功能实现: [`expectation/pass/tile/_random_shared.py`](./_random_shared.py)
    """

    return 4, "P"


def random_rank2_static_dynamic() -> tuple[int, int, str, str]:
    """返回 tile expectation 需要的固定 rank-2 静态/动态维度。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 为 `dma.broadcast`、`kernel.binary_elewise`、compare 类 case 提供固定二维维度。
    - 该 helper 并不真正随机，返回值固定以保持 expectation 文本稳定。

    使用示例:
    - `STATIC_M, STATIC_N, SYM_M, SYM_N = random_rank2_static_dynamic()`

    关联文件:
    - spec: [`spec/pass/lowering/tile_reduce.md`](../../../spec/pass/lowering/tile_reduce.md)
    - test: [`test/tools/test_expectation_case_runner.py`](../../../test/tools/test_expectation_case_runner.py)
    - 功能实现: [`expectation/pass/tile/_random_shared.py`](./_random_shared.py)
    """

    return 4, 8, "M", "N"


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


def random_compare_kinds() -> tuple[str, str, str, str]:
    """返回 tile compare expectation 需要的固定 kind 顺序。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 为 `kernel.binary_elewise` 的 compare 类 case 提供稳定 kind。
    - kind 顺序与 expectation case 的静态 / 动态 / rank-1 / rank-1 动态映射一致。

    使用示例:
    - `R2_STATIC_KIND, R2_DYNAMIC_KIND, R1_STATIC_KIND, R1_DYNAMIC_KIND = random_compare_kinds()`

    关联文件:
    - spec: [`spec/pass/lowering/tile_reduce.md`](../../../spec/pass/lowering/tile_reduce.md)
    - test: [`test/tools/test_expectation_case_runner.py`](../../../test/tools/test_expectation_case_runner.py)
    - 功能实现: [`expectation/pass/tile/_random_shared.py`](./_random_shared.py)
    """

    return "eq", "ne", "gt", "ge"


def random_element_binary_kinds() -> tuple[str, str, str, str]:
    """返回 tile elementwise binary expectation 需要的固定 kind 顺序。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 为 `kernel.binary_elewise` 的 elementwise binary case 提供稳定 kind。
    - kind 顺序与 expectation case 的静态 / 动态 / rank-1 / rank-1 动态映射一致。

    使用示例:
    - `R2_STATIC_KIND, R2_DYNAMIC_KIND, R1_STATIC_KIND, R1_DYNAMIC_KIND = random_element_binary_kinds()`

    关联文件:
    - spec: [`spec/pass/lowering/tile_reduce.md`](../../../spec/pass/lowering/tile_reduce.md)
    - test: [`test/tools/test_expectation_case_runner.py`](../../../test/tools/test_expectation_case_runner.py)
    - 功能实现: [`expectation/pass/tile/_random_shared.py`](./_random_shared.py)
    """

    return "add", "sub", "mul", "div"


__all__ = [
    "ARITH_DTYPE",
    "ARITH_DTYPE_IR",
    "BOOL_DTYPE",
    "BOOL_DTYPE_IR",
    "FLOAT_DTYPE",
    "FLOAT_DTYPE_IR",
    "SPACE_ATTR",
    "memory_ir",
    "random_compare_kinds",
    "random_element_binary_kinds",
    "random_rank1_static_dynamic",
    "random_rank2_static_dynamic",
    "random_rank3_static_dynamic",
]
