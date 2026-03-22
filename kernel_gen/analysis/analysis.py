"""Analysis utilities for computation and data movement.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 基于 Memory 形状统计逐元素/比较/broadcast/matmul 的计算量与搬运量。
- 支持函数级聚合，区分中间结果是否物化。

覆盖率信息:
- 当前覆盖率: `100%` (`kernel_gen/analysis/analysis.py`，2026-03-22 15:24:43 +0800)。
- 对应覆盖率命令: coverage run -m pytest -q test/analysis/test_analysis.py && coverage report --include=kernel_gen/analysis/analysis.py -m

使用示例:
- from kernel_gen.analysis.analysis import analyze_add, analyze_function, MemoryRef, Operation
- result = analyze_add(lhs, rhs, out)
- summary = analyze_function([Operation("add", [MemoryRef("A", lhs), MemoryRef("B", rhs)], MemoryRef("C", out))])

关联文件:
- spec: spec/analysis/analysis_kernel.md
- test: test/analysis/test_analysis.py
- 功能实现: kernel_gen/analysis/analysis.py
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import sympy as sp

from kernel_gen.symbol_variable.memory import Memory


class AnalysisError(ValueError):
    """分析阶段错误。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 用于在分析阶段报告 shape 或规则不满足的错误。

    使用示例:
    - raise AnalysisError("Shape mismatch")

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """


@dataclass(frozen=True)
class OpStats:
    """算子级统计结果。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 保存计算量、读字节与写字节的符号表达式。

    使用示例:
    - stats = OpStats(sp.Integer(1), sp.Integer(4), sp.Integer(2))

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    compute: sp.Basic
    read_bytes: sp.Basic
    write_bytes: sp.Basic

    def __add__(self, other: "OpStats") -> "OpStats":
        """合并两个统计结果。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 累加计算量、读字节与写字节。

        使用示例:
        - total = stats1 + stats2

        关联文件:
        - spec: spec/analysis/analysis_kernel.md
        - test: test/analysis/test_analysis.py
        - 功能实现: kernel_gen/analysis/analysis.py
        """
        if not isinstance(other, OpStats):
            return NotImplemented
        return OpStats(
            self.compute + other.compute,
            self.read_bytes + other.read_bytes,
            self.write_bytes + other.write_bytes,
        )


@dataclass(frozen=True)
class MemoryRef:
    """具名 Memory 引用。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 绑定名称与 Memory 对象，用于函数级分析。

    使用示例:
    - MemoryRef("A", Memory(["A", "B"], NumericType.Float32))

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    name: str
    memory: Memory


@dataclass(frozen=True)
class Operation:
    """函数级算子描述。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 描述算子名称、输入、输出与是否物化。

    使用示例:
    - Operation("add", [MemoryRef("A", lhs)], MemoryRef("C", out))

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    op: str
    inputs: Sequence[MemoryRef]
    output: MemoryRef
    materialize: bool = True


@dataclass(frozen=True)
class AnalysisSummary:
    """函数级分析聚合结果。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 汇总算子统计与总计结果。

    使用示例:
    - summary = AnalysisSummary([stats], stats)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    ops: Sequence[OpStats]
    total: OpStats


def _to_symbol(value: int | str) -> sp.Basic:
    """将维度值转换为 sympy 表达式。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - int 转为 Integer，str 转为 Symbol。

    使用示例:
    - _to_symbol("N")

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    if isinstance(value, int):
        return sp.Integer(value)
    if isinstance(value, str):
        return sp.Symbol(value)
    raise AnalysisError(f"Unsupported dimension: {value!r}")


def _product(values: Iterable[int | str]) -> sp.Basic:
    """将维度列表转换为乘积表达式。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 按顺序累乘维度表达式。

    使用示例:
    - _product([\"A\", \"B\"])

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    result: sp.Basic = sp.Integer(1)
    for value in values:
        result *= _to_symbol(value)
    return result


def _size_symbol(value: int | None, fallback: str) -> sp.Basic:
    """解析 dtype 或 predicate size。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 缺失时返回符号占位（S/P）。

    使用示例:
    - _size_symbol(None, \"S\")

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    if value is None:
        return sp.Symbol(fallback)
    return sp.Integer(value)


def _ensure_same_shape(lhs: Memory, rhs: Memory, message: str) -> None:
    """校验两份 Memory 形状完全一致。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 若形状不一致则抛出 AnalysisError。

    使用示例:
    - _ensure_same_shape(lhs, rhs, \"Shape mismatch\")

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    if lhs.shape.get_values() != rhs.shape.get_values():
        raise AnalysisError(message)


def _element_count(memory: Memory) -> sp.Basic:
    """计算 Memory 的元素数量表达式。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 将 Memory.shape 转换为乘积表达式。

    使用示例:
    - _element_count(Memory([\"A\", \"B\"], dtype))

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    return _product(memory.shape.get_values())


def _ensure_broadcastable(input_mem: Memory, output_mem: Memory) -> None:
    """校验 broadcast 形状规则。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 输出 rank 不小于输入 rank。
    - 尾维对齐，维度相等或输入维为 1。

    使用示例:
    - _ensure_broadcastable(inp, out)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    input_shape = input_mem.shape.get_values()
    output_shape = output_mem.shape.get_values()
    if len(output_shape) < len(input_shape):
        raise AnalysisError("Broadcast output rank must be >= input rank")
    offset = len(output_shape) - len(input_shape)
    for idx, in_dim in enumerate(input_shape):
        out_dim = output_shape[offset + idx]
        if in_dim == out_dim:
            continue
        if isinstance(in_dim, int) and in_dim == 1:
            continue
        raise AnalysisError("Broadcast dimension mismatch")


def _ensure_matmul_shape(lhs: Memory, rhs: Memory, out: Memory) -> None:
    """校验 matmul 形状规则。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅支持 rank-2。
    - inner 维度相等，输出匹配 [M, N]。

    使用示例:
    - _ensure_matmul_shape(lhs, rhs, out)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    lhs_shape = lhs.shape.get_values()
    rhs_shape = rhs.shape.get_values()
    out_shape = out.shape.get_values()
    if len(lhs_shape) != 2 or len(rhs_shape) != 2 or len(out_shape) != 2:
        raise AnalysisError("Matmul requires rank-2 tensors")
    if lhs_shape[1] != rhs_shape[0]:
        raise AnalysisError("Matmul inner dimension mismatch")
    if out_shape[0] != lhs_shape[0] or out_shape[1] != rhs_shape[1]:
        raise AnalysisError("Matmul output shape mismatch")


def analyze_elementwise(
    lhs: Memory,
    rhs: Memory | int,
    out: Memory,
    *,
    dtype_size: int | None = None,
    predicate_size: int | None = None,
    op_kind: str = "arith",
    read_mask: Sequence[bool] | None = None,
    write_output: bool = True,
) -> OpStats:
    """分析逐元素算术或比较算子的统计量。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 逐元素算术与比较遵循形状完全一致约束。
    - 比较输出写入使用 predicate_size。

    使用示例:
    - analyze_elementwise(lhs, rhs, out, op_kind="arith")

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    if isinstance(rhs, Memory):
        _ensure_same_shape(lhs, rhs, "Elementwise input shape mismatch")
    _ensure_same_shape(lhs, out, "Elementwise output shape mismatch")

    element_count = _element_count(out)
    compute = element_count
    dtype_expr = _size_symbol(dtype_size, "S")
    pred_expr = _size_symbol(predicate_size, "P")

    if read_mask is None:
        read_mask = [True, True] if isinstance(rhs, Memory) else [True]
    else:
        expected_len = 2 if isinstance(rhs, Memory) else 1
        if len(read_mask) != expected_len:
            raise AnalysisError("read_mask length mismatch")

    read_bytes = sp.Integer(0)
    if read_mask[0]:
        read_bytes += element_count * dtype_expr
    if isinstance(rhs, Memory) and read_mask[1]:
        read_bytes += element_count * dtype_expr

    if op_kind == "compare":
        write_bytes = element_count * pred_expr if write_output else sp.Integer(0)
    else:
        write_bytes = element_count * dtype_expr if write_output else sp.Integer(0)
    return OpStats(compute, read_bytes, write_bytes)


def analyze_broadcast(
    input_mem: Memory,
    output_mem: Memory,
    *,
    dtype_size: int | None = None,
    read_mask: Sequence[bool] | None = None,
    write_output: bool = True,
) -> OpStats:
    """分析 broadcast 的统计量。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 校验尾维对齐与 singleton 维扩张规则。
    - 基线统计按物化输出计写。

    使用示例:
    - analyze_broadcast(inp, out)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    _ensure_broadcastable(input_mem, output_mem)
    dtype_expr = _size_symbol(dtype_size, "S")
    input_count = _element_count(input_mem)
    output_count = _element_count(output_mem)
    if read_mask is None:
        read_mask = [True]
    elif len(read_mask) != 1:
        raise AnalysisError("read_mask length mismatch")
    read_bytes = input_count * dtype_expr if read_mask[0] else sp.Integer(0)
    write_bytes = output_count * dtype_expr if write_output else sp.Integer(0)
    return OpStats(sp.Integer(0), read_bytes, write_bytes)


def analyze_matmul(
    lhs: Memory,
    rhs: Memory,
    out: Memory,
    *,
    dtype_size: int | None = None,
    read_mask: Sequence[bool] | None = None,
    write_output: bool = True,
) -> OpStats:
    """分析 matmul 的统计量。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 校验二维收缩规则。
    - 统计 2*M*N*K 计算量。

    使用示例:
    - analyze_matmul(lhs, rhs, out)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    _ensure_matmul_shape(lhs, rhs, out)
    dtype_expr = _size_symbol(dtype_size, "S")
    m, k = lhs.shape.get_values()
    _, n = rhs.shape.get_values()
    m_expr = _to_symbol(m)
    n_expr = _to_symbol(n)
    k_expr = _to_symbol(k)
    compute = sp.Integer(2) * m_expr * n_expr * k_expr
    if read_mask is None:
        read_mask = [True, True]
    elif len(read_mask) != 2:
        raise AnalysisError("read_mask length mismatch")
    read_bytes = sp.Integer(0)
    if read_mask[0]:
        read_bytes += _to_symbol(m) * _to_symbol(k) * dtype_expr
    if read_mask[1]:
        read_bytes += _to_symbol(k) * _to_symbol(n) * dtype_expr
    write_bytes = m_expr * n_expr * dtype_expr if write_output else sp.Integer(0)
    return OpStats(compute, read_bytes, write_bytes)


def analyze_function(
    ops: Sequence[Operation],
    *,
    dtype_size: int | None = None,
    predicate_size: int | None = None,
) -> AnalysisSummary:
    """按函数级算子序列聚合统计结果。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 逐算子统计并累加，区分中间结果是否物化。

    使用示例:
    - summary = analyze_function([op1, op2])

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    produced: dict[str, bool] = {}
    stats_list: list[OpStats] = []
    total = OpStats(sp.Integer(0), sp.Integer(0), sp.Integer(0))

    for op in ops:
        if op.op in {"add", "sub", "mul", "truediv", "eq", "ne", "lt", "le", "gt", "ge", "matmul"}:
            expected_inputs = 2
        elif op.op == "broadcast":
            expected_inputs = 1
        else:
            expected_inputs = None

        if expected_inputs is None:
            raise AnalysisError(f"Unsupported op for analysis: {op.op}")
        if len(op.inputs) != expected_inputs:
            raise AnalysisError("Operation inputs length mismatch")

        read_mask: list[bool] = []
        for ref in op.inputs:
            if ref.name in produced and not produced[ref.name]:
                read_mask.append(False)
            else:
                read_mask.append(True)

        write_output = op.materialize
        op_name = op.op
        if op_name in {"add", "sub", "mul", "truediv"}:
            stats = analyze_elementwise(
                op.inputs[0].memory,
                op.inputs[1].memory,
                op.output.memory,
                dtype_size=dtype_size,
                op_kind="arith",
                read_mask=read_mask,
                write_output=write_output,
            )
        elif op_name in {"eq", "ne", "lt", "le", "gt", "ge"}:
            stats = analyze_elementwise(
                op.inputs[0].memory,
                op.inputs[1].memory,
                op.output.memory,
                dtype_size=dtype_size,
                predicate_size=predicate_size,
                op_kind="compare",
                read_mask=read_mask,
                write_output=write_output,
            )
        elif op_name == "broadcast":
            stats = analyze_broadcast(
                op.inputs[0].memory,
                op.output.memory,
                dtype_size=dtype_size,
                read_mask=read_mask,
                write_output=write_output,
            )
        elif op_name == "matmul":
            stats = analyze_matmul(
                op.inputs[0].memory,
                op.inputs[1].memory,
                op.output.memory,
                dtype_size=dtype_size,
                read_mask=read_mask,
                write_output=write_output,
            )

        stats_list.append(stats)
        total = total + stats
        produced[op.output.name] = op.materialize

    return AnalysisSummary(stats_list, total)


def analyze_add(lhs: Memory, rhs: Memory, out: Memory, *, dtype_size: int | None = None) -> OpStats:
    """分析 add 的统计量。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 逐元素算术统计，形状必须一致。

    使用示例:
    - analyze_add(lhs, rhs, out)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    return analyze_elementwise(lhs, rhs, out, dtype_size=dtype_size)


def analyze_eq(
    lhs: Memory,
    rhs: Memory,
    out: Memory,
    *,
    dtype_size: int | None = None,
    predicate_size: int | None = None,
) -> OpStats:
    """分析 eq 的统计量。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 逐元素比较统计，形状必须一致。

    使用示例:
    - analyze_eq(lhs, rhs, out)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    return analyze_elementwise(
        lhs,
        rhs,
        out,
        dtype_size=dtype_size,
        predicate_size=predicate_size,
        op_kind="compare",
    )


def analyze_broadcast_op(
    input_mem: Memory,
    output_mem: Memory,
    *,
    dtype_size: int | None = None,
) -> OpStats:
    """分析 broadcast 的统计量。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统计显式 broadcast 的读写量。

    使用示例:
    - analyze_broadcast_op(inp, out)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    return analyze_broadcast(input_mem, output_mem, dtype_size=dtype_size)


def analyze_matmul_op(
    lhs: Memory,
    rhs: Memory,
    out: Memory,
    *,
    dtype_size: int | None = None,
) -> OpStats:
    """分析 matmul 的统计量。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统计 matmul 的计算量与读写量。

    使用示例:
    - analyze_matmul_op(lhs, rhs, out)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    return analyze_matmul(lhs, rhs, out, dtype_size=dtype_size)
