"""`buffer_results_to_out_params` expectation 共享随机辅助。

创建者: 守护最好的爱莉希雅
最后一次更改: 守护最好的爱莉希雅

功能说明:
- 为 `expectation/pass/buffer_results_to_out_params` 下的 expectation 提供统一的随机
  `shape/type/space` 构造与 IR 文本辅助。
- 复用仓库已有随机 helper，并保持当前 pass 关注的合同面：模块级原子改写、
  caller/callee 同步改写、memory result 前置为 out 参数。

使用示例:
- `from expectation.pass.buffer_results_to_out_params._shared import random_static_memory_spec`
- `src = random_static_memory_spec("src")`
- `dynamic = random_dynamic_memory_spec("lhs")`

关联文件:
- spec: [`spec/pass/lowering/buffer_results_to_out_params.md`](../../../spec/pass/lowering/buffer_results_to_out_params.md)
- spec: [`spec/tools/ircheck.md`](../../../spec/tools/ircheck.md)
- test: [`test/pass/test_buffer_results_to_out_params.py`](../../../test/pass/test_buffer_results_to_out_params.py)
- 功能实现: [`expectation/pass/buffer_results_to_out_params/_shared.py`](../../../expectation/pass/buffer_results_to_out_params/_shared.py)
- 功能实现: [`kernel_gen/passes/lowering/buffer_results_to_out_params.py`](../../../kernel_gen/passes/lowering/buffer_results_to_out_params.py)
"""

from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
import random

from expectation.utils.random_utils import (
    contiguous_stride_tokens,
    nn_memory_type_ir,
    numeric_type_ir,
    random_memory_space,
    random_static_dims,
    random_symbol_names,
)
from expectation.utils.sample_values import get_random_arithmetic_numeric_type
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.symbol_variable.type import NumericType
from xdsl.ir import Operation
from xdsl.printer import Printer

DimToken = int | str
_SCALAR_TYPE_POOL = ("i32", "f32")


@dataclass(frozen=True)
class MemorySpec:
    """封装单个随机 `!nn.memory<...>` expectation 片段。"""

    shape: tuple[DimToken, ...]
    dtype: NumericType
    space: MemorySpace
    arg_name: str

    @property
    def strides(self) -> tuple[str, ...]:
        """返回当前 shape 对应的连续 stride 文本。"""

        return contiguous_stride_tokens(self.shape)

    @property
    def type_ir(self) -> str:
        """返回当前 memory 的完整 `!nn.memory<...>` 文本。"""

        return nn_memory_type_ir(
            self.shape,
            numeric_type_ir(self.dtype),
            self.space,
            strides=self.strides,
        )


def render_case_ir(operation_or_text: Operation | str) -> str:
    """把 operation 或文本渲染成稳定 IR 字符串。"""

    if isinstance(operation_or_text, str):
        return operation_or_text.strip()

    stream = StringIO()
    Printer(stream=stream).print_op(operation_or_text)
    return stream.getvalue().rstrip()


def extract_case_desc(case_text: str, fallback: str) -> str:
    """从 `CASE_TEXT` 头部提取 `// CASE:` 描述。"""

    for line in case_text.splitlines():
        if line.startswith("// CASE:"):
            return line.split("// CASE:", 1)[1].strip()
    return fallback


def print_case_actual_ir(
    case_name: str,
    case_text: str,
    actual_ir: str,
    *,
    fallback: str,
) -> str:
    """打印 `ircheck` case 的实际输出 IR。"""

    desc = extract_case_desc(case_text, fallback)
    rendered = render_case_ir(actual_ir)
    print(f"[{case_name}] {desc}")
    return rendered


def random_static_memory_spec(arg_name: str, *, rank: int = 2) -> MemorySpec:
    """返回随机静态 shape/type/space 的 `MemorySpec`。"""

    return MemorySpec(
        shape=tuple(random_static_dims(rank, min_value=2, max_value=9)),
        dtype=get_random_arithmetic_numeric_type(),
        space=random_memory_space(),
        arg_name=arg_name,
    )


def random_dynamic_memory_spec(arg_name: str, *, rank: int = 2) -> MemorySpec:
    """返回随机动态符号 shape/type/space 的 `MemorySpec`。"""

    return MemorySpec(
        shape=tuple(random_symbol_names(rank)),
        dtype=get_random_arithmetic_numeric_type(),
        space=random_memory_space(),
        arg_name=arg_name,
    )


def random_scalar_type_ir() -> str:
    """返回一个随机标量 IR type。"""

    return random.choice(_SCALAR_TYPE_POOL)


def random_rank(*, min_rank: int = 1, max_rank: int = 3) -> int:
    """返回一个随机 rank。"""

    return random.randint(min_rank, max_rank)


def scalar_constant_literal(type_ir: str) -> str:
    """返回与标量类型匹配的 `arith.constant` 字面量。"""

    if type_ir == "i1":
        return "true"
    if type_ir.startswith("f"):
        return "1.000000e+00"
    return "1"


__all__ = [
    "MemorySpec",
    "extract_case_desc",
    "print_case_actual_ir",
    "random_dynamic_memory_spec",
    "random_rank",
    "random_scalar_type_ir",
    "random_static_memory_spec",
    "render_case_ir",
    "scalar_constant_literal",
]
