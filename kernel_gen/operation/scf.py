"""SCF operation API.

创建者: 摸鱼小分队
最后一次更改: 摸鱼小分队

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

from kernel_gen.symbol_variable.symbol_dim import SymbolDim


class LoopRange:
    """符号范围迭代对象。

    创建者: 摸鱼小分队
    最后一次更改: 摸鱼小分队

    功能说明:
    - 保存 start/end/step 的符号范围表达，供 DSL 侧读取。

    使用示例:
    - loop_range = LoopRange(SymbolDim("M"), SymbolDim("N"), SymbolDim("S"))

    关联文件:
    - spec: spec/operation/scf.md
    - test: test/operation/test_operation_scf.py
    - 功能实现: kernel_gen/operation/scf.py
    """

    def __init__(self, start: int | SymbolDim, end: int | SymbolDim, step: int | SymbolDim) -> None:
        self._start = start
        self._end = end
        self._step = step

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
    if not isinstance(value, (int, SymbolDim)):
        raise TypeError(f"{name} must be int or SymbolDim")
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


def loop(start: object, end: object, step: object):
    """创建 loop 迭代范围。

    创建者: 摸鱼小分队
    最后一次更改: 摸鱼小分队

    功能说明:
    - 纯整数输入时返回 range(start, end, step)。
    - 含 SymbolDim 输入时返回 LoopRange，保留 start/end/step。

    使用示例:
    - for i in loop(0, 4, 1):
        pass

    关联文件:
    - spec: spec/operation/scf.md
    - test: test/operation/test_operation_scf.py
    - 功能实现: kernel_gen/operation/scf.py
    """
    start_value = _ensure_loop_operand(start, "start")
    end_value = _ensure_loop_operand(end, "end")
    step_value = _ensure_loop_operand(step, "step")
    if step_value == 0:
        raise ValueError("step must not be 0")
    if not (_is_symbolic(start_value) or _is_symbolic(end_value) or _is_symbolic(step_value)):
        return range(start_value, end_value, step_value)
    return LoopRange(start_value, end_value, step_value)


__all__ = ["LoopRange", "loop"]
