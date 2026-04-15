"""SCF operation API.

创建者: 摸鱼小分队
最后一次更改: 小李飞刀

功能说明:
- 提供 operation 层的 loop 语义入口，支持整数或符号范围的迭代描述。

使用示例:
- from kernel_gen.operation.scf import loop
- for i in loop(0, 4, 1):
    pass

关联文件:
- spec: spec/operation/scf.md
- test: test/operation/test_operation_scf.py
- 功能实现: kernel_gen/operation/scf.py
"""

from __future__ import annotations

from kernel_gen.common.errors import _ERROR_TEMPLATE
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

_ERROR_ACTION = "请按接口约束传参"

class LoopRange:
    """符号范围迭代对象。

    创建者: 摸鱼小分队
    最后一次更改: 金铲铲大作战

    功能说明:
    - 保存 start/end/step 的符号范围表达，供 DSL 侧读取。
    - 在无法推导真实迭代次数时，保留 trip_count 供上层约束迭代次数。

    使用示例:
    - loop_range = LoopRange(SymbolDim("M"), SymbolDim("N"), SymbolDim("S"), trip_count=3)

    关联文件:
    - spec: spec/operation/scf.md
    - test: test/operation/test_operation_scf.py
    - 功能实现: kernel_gen/operation/scf.py
    """

    def __init__(
        self,
        start: int | SymbolDim,
        end: int | SymbolDim,
        step: int | SymbolDim,
        trip_count: int | SymbolDim = 1,
    ) -> None:
        """初始化 LoopRange。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 保存 start/end/step/trip_count，供 DSL 循环解析使用。
        - 当 step 为字面量 0 时立即拒绝，避免生成非法循环。

        使用示例:
        - LoopRange(0, 8, 2)

        关联文件:
        - spec: spec/operation/scf.md
        - test: test/operation/test_operation_scf.py
        - 功能实现: kernel_gen/operation/scf.py
        """

        if isinstance(step, int) and step == 0:
            raise ValueError("step must not be 0")
        self._start = start
        self._end = end
        self._step = step
        self._trip_count = trip_count

    @property
    def start(self) -> int | SymbolDim:
        """返回符号范围的起始值。

        创建者: 摸鱼小分队
        最后一次更改: 摸鱼小分队

        功能说明:
        - 只读访问 start。

        使用示例:
        - loop_range.start

        关联文件:
        - spec: spec/operation/scf.md
        - test: test/operation/test_operation_scf.py
        - 功能实现: kernel_gen/operation/scf.py
        """
        return self._start

    @property
    def end(self) -> int | SymbolDim:
        """返回符号范围的结束值。

        创建者: 摸鱼小分队
        最后一次更改: 摸鱼小分队

        功能说明:
        - 只读访问 end。

        使用示例:
        - loop_range.end

        关联文件:
        - spec: spec/operation/scf.md
        - test: test/operation/test_operation_scf.py
        - 功能实现: kernel_gen/operation/scf.py
        """
        return self._end

    @property
    def step(self) -> int | SymbolDim:
        """返回符号范围的步长。

        创建者: 摸鱼小分队
        最后一次更改: 摸鱼小分队

        功能说明:
        - 只读访问 step。

        使用示例:
        - loop_range.step

        关联文件:
        - spec: spec/operation/scf.md
        - test: test/operation/test_operation_scf.py
        - 功能实现: kernel_gen/operation/scf.py
        """
        return self._step

    @property
    def trip_count(self) -> int | SymbolDim:
        """返回符号范围的迭代次数约束。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 只读访问 trip_count。

        使用示例:
        - loop_range.trip_count

        关联文件:
        - spec: spec/operation/scf.md
        - test: test/operation/test_operation_scf.py
        - 功能实现: kernel_gen/operation/scf.py
        """
        return self._trip_count

    def __iter__(self):
        """提供迭代接口。

        创建者: 摸鱼小分队
        最后一次更改: 摸鱼小分队

        功能说明:
        - 保持对象可迭代，但符号范围不在运行期展开。

        使用示例:
        - iter(loop_range)

        关联文件:
        - spec: spec/operation/scf.md
        - test: test/operation/test_operation_scf.py
        - 功能实现: kernel_gen/operation/scf.py
        """
        return iter(())


def _ensure_loop_operand(value: object, name: str) -> int | SymbolDim:
    """校验 loop 的参数类型。

    创建者: 摸鱼小分队
    最后一次更改: 摸鱼小分队

    功能说明:
    - 仅允许 int 或 SymbolDim 输入。

    使用示例:
    - _ensure_loop_operand(1, "start")

    关联文件:
    - spec: spec/operation/scf.md
    - test: test/operation/test_operation_scf.py
    - 功能实现: kernel_gen/operation/scf.py
    """
    if isinstance(value, bool) or not isinstance(value, (int, SymbolDim)):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="scf.loop 参数校验",
                expected=f"{name} must be int or SymbolDim",
                actual=type(value).__name__,
                action=_ERROR_ACTION,
            )
        )
    return value


def _normalize_trip_count(value: object) -> int | SymbolDim:
    """校验并归一化 trip_count。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 允许 int 或 SymbolDim；None 会归一化为 1。
    - 若为 int，必须 > 0。

    使用示例:
    - _normalize_trip_count(3)

    关联文件:
    - spec: spec/operation/scf.md
    - test: test/operation/test_operation_scf.py
    - 功能实现: kernel_gen/operation/scf.py
    """
    if value is None:
        value = 1
    if isinstance(value, bool) or not isinstance(value, (int, SymbolDim)):
        raise TypeError(
            _ERROR_TEMPLATE.format(
                scene="scf.loop 参数校验",
                expected="trip_count must be int or SymbolDim",
                actual=type(value).__name__,
                action=_ERROR_ACTION,
            )
        )
    if isinstance(value, int) and value <= 0:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="scf.loop 参数校验",
                expected="trip_count must be > 0",
                actual=str(value),
                action=_ERROR_ACTION,
            )
        )
    return value


def _is_symbolic(value: int | SymbolDim) -> bool:
    """判断输入是否为 SymbolDim。

    创建者: 摸鱼小分队
    最后一次更改: 摸鱼小分队

    功能说明:
    - SymbolDim 返回 True，否则 False。

    使用示例:
    - _is_symbolic(SymbolDim("N"))

    关联文件:
    - spec: spec/operation/scf.md
    - test: test/operation/test_operation_scf.py
    - 功能实现: kernel_gen/operation/scf.py
    """
    return isinstance(value, SymbolDim)


def loop(start: object, end: object, step: object, trip_count: object = 1):
    """创建 loop 迭代范围。

    创建者: 摸鱼小分队
    最后一次更改: 金铲铲大作战

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
    - test: test/operation/test_operation_scf.py
    - 功能实现: kernel_gen/operation/scf.py
    """
    start_value = _ensure_loop_operand(start, "start")
    end_value = _ensure_loop_operand(end, "end")
    step_value = _ensure_loop_operand(step, "step")
    trip_count_value = _normalize_trip_count(trip_count)
    if step_value == 0:
        raise ValueError(
            _ERROR_TEMPLATE.format(
                scene="scf.loop 参数校验",
                expected="step must not be 0",
                actual=str(step),
                action=_ERROR_ACTION,
            )
        )
    if not (_is_symbolic(start_value) or _is_symbolic(end_value) or _is_symbolic(step_value)):
        return range(start_value, end_value, step_value)
    return LoopRange(start_value, end_value, step_value, trip_count_value)


__all__ = ["LoopRange", "loop"]
