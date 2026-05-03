"""SCF operation API.


功能说明:
- 提供 operation 层的 loop 语义入口，支持整数或符号范围的迭代描述。

API 列表:
- `class LoopRange(start: int | SymbolDim, end: int | SymbolDim, step: int | SymbolDim, trip_count: int | SymbolDim | None = 1)`
- `LoopRange.start -> int | SymbolDim`
- `LoopRange.end -> int | SymbolDim`
- `LoopRange.step -> int | SymbolDim`
- `LoopRange.trip_count -> int | SymbolDim`
- `loop(start: int | SymbolDim, end: int | SymbolDim, step: int | SymbolDim, trip_count: int | SymbolDim | None = 1) -> range | LoopRange`

使用示例:
- from kernel_gen.operation.scf import loop
- for i in loop(0, 4, 1):
    pass

关联文件:
- spec: spec/operation/scf.md
- test: test/operation/test_scf.py
- 功能实现: kernel_gen/operation/scf.py
"""

from __future__ import annotations

from collections.abc import Iterator

from kernel_gen.core.error import (
    ERROR_ACTION,
    ERROR_TEMPLATE,
    ErrorKind,
    ErrorModule,
    kernel_code_error,
)
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

LoopOperand = int | SymbolDim
TripCountInput = int | SymbolDim | None


class LoopRange:
    """符号范围迭代对象。


    功能说明:
    - 保存 start/end/step 的符号范围表达，供 DSL 侧读取。
    - 在无法推导真实迭代次数时，保留 trip_count 供上层约束迭代次数。

    使用示例:
    - loop_range = LoopRange(SymbolDim("M"), SymbolDim("N"), SymbolDim("S"), trip_count=3)

    关联文件:
    - spec: spec/operation/scf.md
    - test: test/operation/test_scf.py
    - 功能实现: kernel_gen/operation/scf.py
    """

    def __init__(
        self,
        start: int | SymbolDim,
        end: int | SymbolDim,
        step: int | SymbolDim,
        trip_count: int | SymbolDim | None = 1,
    ) -> None:
        """初始化 LoopRange。


        功能说明:
        - 保存 start/end/step/trip_count，供 DSL 循环解析使用。
        - 当 step 为字面量 0 时立即拒绝，避免生成非法循环。

        使用示例:
        - LoopRange(0, 8, 2)

        关联文件:
        - spec: spec/operation/scf.md
        - test: test/operation/test_scf.py
        - 功能实现: kernel_gen/operation/scf.py
        """

        start_value, end_value, step_value, trip_count_value = _normalize_loop_inputs(
            start, end, step, trip_count
        )
        self._start = start_value
        self._end = end_value
        self._step = step_value
        self._trip_count = trip_count_value

    @property
    def start(self) -> int | SymbolDim:
        """返回符号范围的起始值。


        功能说明:
        - 只读访问 start。

        使用示例:
        - loop_range.start

        关联文件:
        - spec: spec/operation/scf.md
        - test: test/operation/test_scf.py
        - 功能实现: kernel_gen/operation/scf.py
        """
        return self._start

    @property
    def end(self) -> int | SymbolDim:
        """返回符号范围的结束值。


        功能说明:
        - 只读访问 end。

        使用示例:
        - loop_range.end

        关联文件:
        - spec: spec/operation/scf.md
        - test: test/operation/test_scf.py
        - 功能实现: kernel_gen/operation/scf.py
        """
        return self._end

    @property
    def step(self) -> int | SymbolDim:
        """返回符号范围的步长。


        功能说明:
        - 只读访问 step。

        使用示例:
        - loop_range.step

        关联文件:
        - spec: spec/operation/scf.md
        - test: test/operation/test_scf.py
        - 功能实现: kernel_gen/operation/scf.py
        """
        return self._step

    @property
    def trip_count(self) -> int | SymbolDim:
        """返回符号范围的迭代次数约束。


        功能说明:
        - 只读访问 trip_count。

        使用示例:
        - loop_range.trip_count

        关联文件:
        - spec: spec/operation/scf.md
        - test: test/operation/test_scf.py
        - 功能实现: kernel_gen/operation/scf.py
        """
        return self._trip_count

    def __iter__(self) -> Iterator[LoopOperand]:
        """提供迭代接口。


        功能说明:
        - 在符号边界未知时，按 `trip_count` 有限生成 `start + step * i` 序列。
        - 仅在 operation/Python helper 层提供该序列语义，不影响 lowering 合同。

        使用示例:
        - iter(loop_range)

        关联文件:
        - spec: spec/operation/scf.md
        - test: test/operation/test_scf.py
        - 功能实现: kernel_gen/operation/scf.py
        """
        return _iter_symbolic_sequence(self._start, self._step, self._trip_count)


def _ensure_loop_operand(value: LoopOperand, name: str) -> LoopOperand:
    """校验 loop 的参数类型。


    功能说明:
    - 仅允许 int 或 SymbolDim 输入。

    使用示例:
    - _ensure_loop_operand(1, "start")

    关联文件:
    - spec: spec/operation/scf.md
    - test: test/operation/test_scf.py
    - 功能实现: kernel_gen/operation/scf.py
    """
    if isinstance(value, bool) or not isinstance(value, (int, SymbolDim)):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="scf.loop 参数校验",
                expected=f"{name} must be int or SymbolDim",
                actual=type(value).__name__,
                action=ERROR_ACTION,
            )
        )
    return value


def _normalize_trip_count(value: TripCountInput) -> LoopOperand:
    """校验并归一化 trip_count。


    功能说明:
    - 允许 int 或 SymbolDim；None 会归一化为 1。
    - 若为 int，必须 > 0。

    使用示例:
    - _normalize_trip_count(3)

    关联文件:
    - spec: spec/operation/scf.md
    - test: test/operation/test_scf.py
    - 功能实现: kernel_gen/operation/scf.py
    """
    if value is None:
        value = 1
    if isinstance(value, bool) or not isinstance(value, (int, SymbolDim)):
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="scf.loop 参数校验",
                expected="trip_count must be int or SymbolDim",
                actual=type(value).__name__,
                action=ERROR_ACTION,
            )
        )
    if isinstance(value, int) and value <= 0:
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="scf.loop 参数校验",
                expected="trip_count must be > 0",
                actual=str(value),
                action=ERROR_ACTION,
            )
        )
    return value


def _normalize_loop_inputs(
    start: LoopOperand,
    end: LoopOperand,
    step: LoopOperand,
    trip_count: TripCountInput,
) -> tuple[LoopOperand, LoopOperand, LoopOperand, LoopOperand]:
    """统一收口 loop/LoopRange 两条入口的输入校验与归一化。


    功能说明:
    - 让 `LoopRange(...)` 与 `loop(...)` 共享同一组参数校验。
    - 统一处理 `bool` 拒绝、`trip_count=None -> 1` 与 `step == 0` 错误。

    使用示例:
    - start_value, end_value, step_value, trip_count_value = _normalize_loop_inputs(0, 4, 1, None)

    关联文件:
    - spec: spec/operation/scf.md
    - test: test/operation/test_scf.py
    - 功能实现: kernel_gen/operation/scf.py
    """

    start_value = _ensure_loop_operand(start, "start")
    end_value = _ensure_loop_operand(end, "end")
    step_value = _ensure_loop_operand(step, "step")
    trip_count_value = _normalize_trip_count(trip_count)
    if step_value == 0:
        raise kernel_code_error(ErrorKind.CONTRACT, ErrorModule.OPERATION,
            ERROR_TEMPLATE.format(
                scene="scf.loop 参数校验",
                expected="step must not be 0",
                actual=str(step),
                action=ERROR_ACTION,
            )
        )
    return start_value, end_value, step_value, trip_count_value


def _iter_symbolic_sequence(
    start: LoopOperand,
    step: LoopOperand,
    trip_count: LoopOperand,
) -> Iterator[LoopOperand]:
    """按 `trip_count` 有限生成符号 loop 的运行期序列。


    功能说明:
    - 当 `trip_count` 为整数时，生成 `start + step * i` 的有限序列。
    - 当 `trip_count` 为 `SymbolDim` 时，当前保持最小保守策略，只产出首项，避免在运行期出现无限展开。

    使用示例:
    - list(_iter_symbolic_sequence(1, 2, 3)) == [1, 3, 5]

    关联文件:
    - spec: spec/operation/scf.md
    - test: test/operation/test_scf.py
    - 功能实现: kernel_gen/operation/scf.py
    """

    if isinstance(trip_count, SymbolDim):
        return iter((start,))

    values: list[int | SymbolDim] = []
    current: int | SymbolDim = start
    for _ in range(trip_count):
        values.append(current)
        current = current + step
    return iter(values)


def _is_symbolic(value: LoopOperand) -> bool:
    """判断输入是否为 SymbolDim。


    功能说明:
    - SymbolDim 返回 True，否则 False。

    使用示例:
    - _is_symbolic(SymbolDim("N"))

    关联文件:
    - spec: spec/operation/scf.md
    - test: test/operation/test_scf.py
    - 功能实现: kernel_gen/operation/scf.py
    """
    return isinstance(value, SymbolDim)


def loop(
    start: LoopOperand,
    end: LoopOperand,
    step: LoopOperand,
    trip_count: TripCountInput = 1,
) -> range | LoopRange:
    """创建 loop 迭代范围。


    功能说明:
    - 纯整数输入时返回 range(start, end, step)。
    - 含 SymbolDim 输入时返回 LoopRange，保留 start/end/step/trip_count。

    使用示例:
    - for i in loop(0, 4, 1):
        pass
    - for i in loop(SymbolDim("M"), SymbolDim("N"), SymbolDim("S"), trip_count=3):
        pass

    关联文件:
    - spec: spec/operation/scf.md
    - test: test/operation/test_scf.py
    - 功能实现: kernel_gen/operation/scf.py
    """
    start_value, end_value, step_value, trip_count_value = _normalize_loop_inputs(
        start, end, step, trip_count
    )
    if not (_is_symbolic(start_value) or _is_symbolic(end_value) or _is_symbolic(step_value)):
        return range(start_value, end_value, step_value)
    return LoopRange(start_value, end_value, step_value, trip_count_value)


__all__ = ["LoopRange", "loop"]
