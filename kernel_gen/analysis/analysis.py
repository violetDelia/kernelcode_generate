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

from collections.abc import Iterable as IterableABC
from dataclasses import dataclass
from typing import Iterable, Sequence
import warnings

import sympy as sp
from xdsl.dialects import arith, func
from xdsl.dialects.builtin import (
    ArrayAttr,
    BFloat16Type,
    Float16Type,
    Float32Type,
    Float64Type,
    IntAttr,
    IntegerType,
    StringAttr,
)
from xdsl.ir import Attribute, Operation, SSAValue

from kernel_gen.dialect.dma import DmaAllocOp, DmaCopyOp, DmaDesliceOp, DmaFreeOp, DmaLoadOp, DmaSliceOp, DmaStoreOp
from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim


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


@dataclass(frozen=True)
class KernelOpCost:
    """单个 kernel op 的成本统计。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 保存 op 顺序索引、名称与 compute/read/write 统计。

    使用示例:
    - KernelOpCost(0, "nn.add", sp.Symbol("A"), sp.Symbol("B"), sp.Symbol("C"))

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    op_index: int
    op_name: str
    compute: sp.Basic
    read_bytes: sp.Basic
    write_bytes: sp.Basic


@dataclass(frozen=True)
class ValueTraffic:
    """单个 SSA value 的流量统计。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 使用稳定 value_key 记录读写流量。

    使用示例:
    - ValueTraffic("arg0", sp.Integer(0), sp.Integer(16))

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    value_key: str
    read_bytes: sp.Basic
    write_bytes: sp.Basic


@dataclass(frozen=True)
class AnalyzeKernelSummary:
    """kernel 分析汇总结构。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 汇总函数名、逐 op 成本与逐 value 流量。

    使用示例:
    - summary = AnalyzeKernelSummary("main", [], [], sp.Integer(0), sp.Integer(0), sp.Integer(0))

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """

    func_name: str
    op_costs: Sequence[KernelOpCost]
    value_traffic: Sequence[ValueTraffic]
    total_compute: sp.Basic
    total_read_bytes: sp.Basic
    total_write_bytes: sp.Basic


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


def _normalize_dtype_overrides(
    dtype_size_overrides: dict[str, int] | None,
) -> dict[str, int]:
    """规范化 dtype 覆盖表。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 将 key 统一为小写。
    - 校验 value 为正整数。

    使用示例:
    - overrides = _normalize_dtype_overrides({"F32": 4})

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    normalized: dict[str, int] = {}
    if dtype_size_overrides is None:
        return normalized
    for key, value in dtype_size_overrides.items():
        if not isinstance(value, int) or value <= 0:
            raise AnalysisError(f"dtype_size_overrides[{key}] must be positive int")
        normalized[str(key).lower()] = value
    return normalized


def _element_size(element_type: Attribute, dtype_size_overrides: dict[str, int]) -> int | None:
    """获取元素类型字节大小。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 先读取 dtype_size_overrides 覆盖。
    - 支持 i1/i8/i16/i32/i64 与 f16/bf16/f32/f64。

    使用示例:
    - size = _element_size(f32, {"f32": 4})

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    key = str(element_type).lower()
    if key in dtype_size_overrides:
        return dtype_size_overrides[key]
    if isinstance(element_type, IntegerType):
        width = int(element_type.width.data)
        if width in {1, 8}:
            return 1
        if width == 16:
            return 2
        if width == 32:
            return 4
        if width == 64:
            return 8
        return None
    if isinstance(element_type, (Float16Type, BFloat16Type)):
        return 2
    if isinstance(element_type, Float32Type):
        return 4
    if isinstance(element_type, Float64Type):
        return 8
    return None


def _is_predicate_type(element_type: Attribute) -> bool:
    """判断 element_type 是否为 i1 predicate。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - IntegerType 且 width=1 时返回 True。

    使用示例:
    - _is_predicate_type(i1)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    return isinstance(element_type, IntegerType) and int(element_type.width.data) == 1


def _dim_to_expr(dim: Attribute) -> sp.Basic | None:
    """将维度 attribute 转为 sympy 表达式。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - IntAttr 转 Integer。
    - StringAttr 数字转 Integer，其它转 SymbolDim。
    - 空字符串或 '?' 返回 None。

    使用示例:
    - expr = _dim_to_expr(StringAttr("N"))

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    if isinstance(dim, IntAttr):
        return sp.Integer(dim.data)
    if isinstance(dim, StringAttr):
        raw = dim.data.strip()
        if raw == "" or raw == "?":
            return None
        if raw.isdigit():
            return sp.Integer(int(raw))
        return SymbolDim(raw).get_symbol()
    return None


def _numel_from_shape(shape: ArrayAttr) -> sp.Basic | None:
    """基于 shape 计算元素数量。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 按维度依次相乘生成表达式。

    使用示例:
    - numel = _numel_from_shape(mem_type.shape)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    expr = sp.Integer(1)
    for dim in shape.data:
        dim_expr = _dim_to_expr(dim)
        if dim_expr is None:
            return None
        expr = expr * dim_expr
    return expr


def _numel_from_mem_type(mem_type: NnMemoryType) -> sp.Basic | None:
    """计算 nn.memory 的元素数量。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 使用 shape 维度乘积作为元素总数。

    使用示例:
    - numel = _numel_from_mem_type(mem_type)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    return _numel_from_shape(mem_type.shape)


def _symbol_value_to_expr(value: SSAValue) -> sp.Basic | None:
    """将 `!symbol.int` SSA value 转为 sympy 表达式。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 静态整数返回 Integer。
    - 符号表达式返回对应 SymbolDim 符号。

    使用示例:
    - expr = _symbol_value_to_expr(op.sizes[0])

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    if not isinstance(value.type, SymbolValueType):
        return None
    return _to_symbol(value.type.get_value())


def _numel_from_symbol_values(values: Sequence[SSAValue]) -> sp.Basic | None:
    """将 `!symbol.int` operand 列表转为元素总数表达式。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 逐项转换为 sympy 表达式并相乘。
    - 任一 operand 不是 `!symbol.int` 时返回 None。

    使用示例:
    - numel = _numel_from_symbol_values(op.sizes)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    expr = sp.Integer(1)
    for value in values:
        dim_expr = _symbol_value_to_expr(value)
        if dim_expr is None:
            return None
        expr = expr * dim_expr
    return expr


def _should_ignore_kernel_op(op: Operation) -> bool:
    """判断是否忽略 kernel 分析 op。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - func.return 与 arith.constant 默认忽略。

    使用示例:
    - if _should_ignore_kernel_op(op): ...

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    if isinstance(op, func.ReturnOp):
        return True
    if isinstance(op, arith.ConstantOp):
        return True
    return False


def _warn_skip_kernel_op(op: Operation, reason: str) -> None:
    """输出跳过 op 的告警。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 使用 warnings.warn 提示未知 op 被跳过。

    使用示例:
    - _warn_skip_kernel_op(op, "unsupported op")

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    warnings.warn(f"analysis_kernel skip {op.name}: {reason}", UserWarning)


def _iter_block_ops(ops: Iterable[Operation]) -> Iterable[Operation]:
    """递归遍历 block 内 ops。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 逐 op 遍历并展开其 region 内嵌套 block。

    使用示例:
    - for op in _iter_block_ops(block.ops): ...

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    for op in ops:
        yield op
        for region in op.regions:
            for block in region.blocks:
                yield from _iter_block_ops(block.ops)


def _iter_func_ops(func_op: func.FuncOp) -> Iterable[Operation]:
    """遍历 func.func 内所有 ops。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 对 func.body 中所有 block 进行递归遍历。

    使用示例:
    - for op in _iter_func_ops(func_op): ...

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    for block in func_op.body.blocks:
        yield from _iter_block_ops(block.ops)


def _sum_expr(items: Iterable[sp.Basic]) -> sp.Basic:
    """求和 sympy 表达式列表。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 逐项累加并返回求和结果。

    使用示例:
    - total = _sum_expr([expr_a, expr_b])

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    total = sp.Integer(0)
    for item in items:
        total = total + item
    return total


def _record_value_read(
    value: SSAValue,
    amount: sp.Basic,
    value_keys: dict[SSAValue, str],
    traffic_map: dict[str, list[sp.Basic]],
) -> None:
    """记录 value 的读流量。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 若 value 未登记稳定 key，则忽略记录。

    使用示例:
    - _record_value_read(arg0, bytes_expr, value_keys, traffic_map)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    key = value_keys.get(value)
    if key is None:
        return
    traffic = traffic_map.setdefault(key, [sp.Integer(0), sp.Integer(0)])
    traffic[0] = traffic[0] + amount


def _record_value_write(
    value: SSAValue,
    amount: sp.Basic,
    value_keys: dict[SSAValue, str],
    traffic_map: dict[str, list[sp.Basic]],
) -> None:
    """记录 value 的写流量。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 若 value 未登记稳定 key，则忽略记录。

    使用示例:
    - _record_value_write(result, bytes_expr, value_keys, traffic_map)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    key = value_keys.get(value)
    if key is None:
        return
    traffic = traffic_map.setdefault(key, [sp.Integer(0), sp.Integer(0)])
    traffic[1] = traffic[1] + amount


def _register_op_results(
    op: Operation,
    op_index: int,
    write_bytes: sp.Basic,
    value_keys: dict[SSAValue, str],
    traffic_map: dict[str, list[sp.Basic]],
) -> None:
    """为 op 结果注册稳定 key，并记录写流量。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 统一生成 `op{idx}.result{n}` 形式的 value key。
    - 将写流量累计到结果 value。

    使用示例:
    - _register_op_results(op, 0, bytes_expr, value_keys, traffic_map)

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    for result_index, result_value in enumerate(op.results):
        key = f"op{op_index}.result{result_index}"
        value_keys[result_value] = key
        traffic_map.setdefault(key, [sp.Integer(0), sp.Integer(0)])
        _record_value_write(result_value, write_bytes, value_keys, traffic_map)


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


def analyze_kernel(
    func_op: func.FuncOp,
    args: Iterable[object] | None = None,
    *,
    predicate_size: int = 1,
    dtype_size_overrides: dict[str, int] | None = None,
    attach_attrs: bool = False,
) -> AnalyzeKernelSummary:
    """分析单个 func.func 的 compute/read/write 与 value_traffic。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 以 func.FuncOp 为输入，输出逐 op 统计与稳定 value_traffic。
    - 未知 op 执行 skip + warning，不计入总量。

    使用示例:
    - summary = analyze_kernel(func_op, dtype_size_overrides={"f32": 4})

    关联文件:
    - spec: spec/analysis/analysis_kernel.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/analysis.py
    """
    if not isinstance(func_op, func.FuncOp):
        raise AnalysisError("func_op must be func.FuncOp")
    if not isinstance(predicate_size, int) or predicate_size <= 0:
        raise AnalysisError("predicate_size must be positive")

    overrides = _normalize_dtype_overrides(dtype_size_overrides)

    if args is not None and not isinstance(args, IterableABC):
        raise AnalysisError("args must be iterable")
    arg_list = list(args) if args is not None else None
    func_args = list(func_op.body.blocks[0].args)
    if arg_list is not None and len(arg_list) != len(func_args):
        raise AnalysisError("args length mismatch")

    value_keys: dict[SSAValue, str] = {}
    traffic_map: dict[str, list[sp.Basic]] = {}
    for index, arg in enumerate(func_args):
        key = f"arg{index}"
        value_keys[arg] = key
        traffic_map[key] = [sp.Integer(0), sp.Integer(0)]

    op_costs: list[KernelOpCost] = []

    for op in _iter_func_ops(func_op):
        if _should_ignore_kernel_op(op):
            continue

        op_name = op.name
        if op_name in {"nn.add", "nn.sub", "nn.mul", "nn.truediv", "nn.eq", "nn.ne", "nn.lt", "nn.le", "nn.gt", "nn.ge"}:
            if len(op.operands) < 2 or len(op.results) != 1:
                raise AnalysisError("nn elementwise op must have 2 operands and 1 result")
            lhs = op.operands[0]
            rhs = op.operands[1]
            result = op.results[0]
            if not isinstance(result.type, NnMemoryType):
                raise AnalysisError("nn op result must be nn.memory")
            result_type = result.type
            numel = _numel_from_mem_type(result_type)
            if numel is None:
                raise AnalysisError("result shape must be supported")

            lhs_mem = isinstance(lhs.type, NnMemoryType)
            rhs_mem = isinstance(rhs.type, NnMemoryType)
            if not lhs_mem and not rhs_mem:
                raise AnalysisError("at least one nn.memory operand required")

            read_bytes_list: list[sp.Basic] = []
            if lhs_mem:
                lhs_type = lhs.type
                if lhs_type.shape != result_type.shape:
                    raise AnalysisError("result shape must match memory operand")
                lhs_size = _element_size(lhs_type.element_type, overrides)
                if lhs_size is None:
                    raise AnalysisError("operand dtype unsupported")
                lhs_bytes = numel * sp.Integer(lhs_size)
                read_bytes_list.append(lhs_bytes)
                _record_value_read(lhs, lhs_bytes, value_keys, traffic_map)
            if rhs_mem:
                rhs_type = rhs.type
                if rhs_type.shape != result_type.shape:
                    raise AnalysisError("result shape must match memory operand")
                rhs_size = _element_size(rhs_type.element_type, overrides)
                if rhs_size is None:
                    raise AnalysisError("operand dtype unsupported")
                rhs_bytes = numel * sp.Integer(rhs_size)
                read_bytes_list.append(rhs_bytes)
                _record_value_read(rhs, rhs_bytes, value_keys, traffic_map)

            if op_name in {"nn.eq", "nn.ne", "nn.lt", "nn.le", "nn.gt", "nn.ge"}:
                if not _is_predicate_type(result_type.element_type):
                    raise AnalysisError("compare result element_type must be i1")
                write_bytes = numel * sp.Integer(predicate_size)
            else:
                out_size = _element_size(result_type.element_type, overrides)
                if out_size is None:
                    raise AnalysisError("result dtype unsupported")
                write_bytes = numel * sp.Integer(out_size)

            op_index = len(op_costs)
            _register_op_results(op, op_index, write_bytes, value_keys, traffic_map)

            op_costs.append(
                KernelOpCost(
                    op_index=op_index,
                    op_name=op_name,
                    compute=numel,
                    read_bytes=_sum_expr(read_bytes_list),
                    write_bytes=write_bytes,
                )
            )
            continue

        if op_name == "nn.matmul":
            if len(op.operands) < 2 or len(op.results) != 1:
                raise AnalysisError("nn.matmul must have 2 operands and 1 result")
            lhs = op.operands[0]
            rhs = op.operands[1]
            result = op.results[0]
            if not isinstance(lhs.type, NnMemoryType) or not isinstance(rhs.type, NnMemoryType):
                raise AnalysisError("nn.matmul operands must be nn.memory")
            if not isinstance(result.type, NnMemoryType):
                raise AnalysisError("nn.matmul result must be nn.memory")
            lhs_type = lhs.type
            rhs_type = rhs.type
            result_type = result.type
            if len(lhs_type.shape.data) != 2 or len(rhs_type.shape.data) != 2 or len(result_type.shape.data) != 2:
                raise AnalysisError("nn.matmul requires rank-2 tensors")

            m_dim = _dim_to_expr(lhs_type.shape.data[0])
            k_dim = _dim_to_expr(lhs_type.shape.data[1])
            rhs_k_dim = _dim_to_expr(rhs_type.shape.data[0])
            n_dim = _dim_to_expr(rhs_type.shape.data[1])
            out_m_dim = _dim_to_expr(result_type.shape.data[0])
            out_n_dim = _dim_to_expr(result_type.shape.data[1])
            if None in {m_dim, k_dim, rhs_k_dim, n_dim, out_m_dim, out_n_dim}:
                raise AnalysisError("nn.matmul shape unsupported")
            if k_dim != rhs_k_dim:
                raise AnalysisError("nn.matmul inner dimension mismatch")
            if out_m_dim != m_dim or out_n_dim != n_dim:
                raise AnalysisError("nn.matmul output shape mismatch")

            elem_size = _element_size(lhs_type.element_type, overrides)
            if elem_size is None:
                raise AnalysisError("nn.matmul operand dtype unsupported")
            if lhs_type.element_type != rhs_type.element_type or lhs_type.element_type != result_type.element_type:
                raise AnalysisError("nn.matmul operand/result element_type must match")
            elem_size_expr = sp.Integer(elem_size)
            compute = sp.Integer(2) * m_dim * n_dim * k_dim
            read_bytes = (m_dim * k_dim + k_dim * n_dim) * elem_size_expr
            write_bytes = m_dim * n_dim * elem_size_expr

            _record_value_read(lhs, m_dim * k_dim * elem_size_expr, value_keys, traffic_map)
            _record_value_read(rhs, k_dim * n_dim * elem_size_expr, value_keys, traffic_map)

            op_index = len(op_costs)
            _register_op_results(op, op_index, write_bytes, value_keys, traffic_map)

            op_costs.append(
                KernelOpCost(
                    op_index=op_index,
                    op_name=op_name,
                    compute=compute,
                    read_bytes=read_bytes,
                    write_bytes=write_bytes,
                )
            )
            continue

        if isinstance(op, DmaCopyOp):
            source = op.source
            target = op.target
            if not isinstance(source.type, NnMemoryType) or not isinstance(target.type, NnMemoryType):
                raise AnalysisError("dma.copy source/target must be nn.memory")
            numel = _numel_from_mem_type(source.type)
            if numel is None:
                raise AnalysisError("dma.copy shape unsupported")
            elem_size = _element_size(source.type.element_type, overrides)
            if elem_size is None:
                raise AnalysisError("dma.copy dtype unsupported")
            bytes_expr = numel * sp.Integer(elem_size)

            _record_value_read(source, bytes_expr, value_keys, traffic_map)
            _record_value_write(target, bytes_expr, value_keys, traffic_map)

            op_costs.append(
                KernelOpCost(
                    op_index=len(op_costs),
                    op_name=op_name,
                    compute=sp.Integer(0),
                    read_bytes=bytes_expr,
                    write_bytes=bytes_expr,
                )
            )
            continue

        if isinstance(op, DmaLoadOp):
            if len(op.operands) < 1 or len(op.results) != 1:
                raise AnalysisError("dma.load must have 1 result")
            source = op.operands[0]
            result = op.results[0]
            if not isinstance(source.type, NnMemoryType):
                raise AnalysisError("dma.load source must be nn.memory")
            if not isinstance(result.type, NnMemoryType):
                raise AnalysisError("dma.load result must be nn.memory")
            result_type = result.type
            numel = _numel_from_mem_type(result_type)
            if numel is None:
                raise AnalysisError("dma.load result shape unsupported")
            elem_size = _element_size(result_type.element_type, overrides)
            if elem_size is None:
                raise AnalysisError("dma.load result dtype unsupported")
            bytes_expr = numel * sp.Integer(elem_size)

            _record_value_read(source, bytes_expr, value_keys, traffic_map)
            op_index = len(op_costs)
            _register_op_results(op, op_index, bytes_expr, value_keys, traffic_map)

            op_costs.append(
                KernelOpCost(
                    op_index=op_index,
                    op_name=op_name,
                    compute=sp.Integer(0),
                    read_bytes=bytes_expr,
                    write_bytes=bytes_expr,
                )
            )
            continue

        if isinstance(op, DmaStoreOp):
            source = op.source
            target = op.target
            if not isinstance(source.type, NnMemoryType) or not isinstance(target.type, NnMemoryType):
                raise AnalysisError("dma.store source/target must be nn.memory")
            numel = _numel_from_symbol_values(op.sizes)
            if numel is None:
                numel = _numel_from_mem_type(source.type)
            if numel is None:
                raise AnalysisError("dma.store sizes unsupported")
            elem_size = _element_size(source.type.element_type, overrides)
            if elem_size is None:
                raise AnalysisError("dma.store dtype unsupported")
            bytes_expr = numel * sp.Integer(elem_size)

            _record_value_read(source, bytes_expr, value_keys, traffic_map)
            _record_value_write(target, bytes_expr, value_keys, traffic_map)

            op_costs.append(
                KernelOpCost(
                    op_index=len(op_costs),
                    op_name=op_name,
                    compute=sp.Integer(0),
                    read_bytes=bytes_expr,
                    write_bytes=bytes_expr,
                )
            )
            continue

        if isinstance(op, DmaSliceOp):
            source = op.source
            target = op.target
            if not isinstance(source.type, NnMemoryType) or not isinstance(target.type, NnMemoryType):
                raise AnalysisError("dma.slice source/target must be nn.memory")
            numel = _numel_from_symbol_values(op.sizes)
            if numel is None:
                numel = _numel_from_mem_type(target.type)
            if numel is None:
                raise AnalysisError("dma.slice sizes unsupported")
            elem_size = _element_size(source.type.element_type, overrides)
            if elem_size is None:
                raise AnalysisError("dma.slice dtype unsupported")
            bytes_expr = numel * sp.Integer(elem_size)

            _record_value_read(source, bytes_expr, value_keys, traffic_map)
            _record_value_write(target, bytes_expr, value_keys, traffic_map)

            op_costs.append(
                KernelOpCost(
                    op_index=len(op_costs),
                    op_name=op_name,
                    compute=sp.Integer(0),
                    read_bytes=bytes_expr,
                    write_bytes=bytes_expr,
                )
            )
            continue

        if isinstance(op, DmaDesliceOp):
            source = op.source
            if not isinstance(source.type, NnMemoryType):
                raise AnalysisError("dma.deslice source must be nn.memory")
            if len(op.results) != 1 or not isinstance(op.result.type, NnMemoryType):
                raise AnalysisError("dma.deslice result must be nn.memory")
            numel = _numel_from_symbol_values(op.sizes)
            if numel is None:
                numel = _numel_from_mem_type(source.type)
            if numel is None:
                raise AnalysisError("dma.deslice sizes unsupported")
            elem_size = _element_size(source.type.element_type, overrides)
            if elem_size is None:
                raise AnalysisError("dma.deslice dtype unsupported")
            bytes_expr = numel * sp.Integer(elem_size)

            _record_value_read(source, bytes_expr, value_keys, traffic_map)
            op_index = len(op_costs)
            _register_op_results(op, op_index, bytes_expr, value_keys, traffic_map)

            op_costs.append(
                KernelOpCost(
                    op_index=op_index,
                    op_name=op_name,
                    compute=sp.Integer(0),
                    read_bytes=bytes_expr,
                    write_bytes=bytes_expr,
                )
            )
            continue

        if isinstance(op, (DmaAllocOp, DmaFreeOp)):
            op_index = len(op_costs)
            if len(op.results) > 0:
                _register_op_results(op, op_index, sp.Integer(0), value_keys, traffic_map)
            op_costs.append(
                KernelOpCost(
                    op_index=op_index,
                    op_name=op_name,
                    compute=sp.Integer(0),
                    read_bytes=sp.Integer(0),
                    write_bytes=sp.Integer(0),
                )
            )
            continue

        _warn_skip_kernel_op(op, "unsupported op")

    total_compute = _sum_expr([item.compute for item in op_costs])
    total_read_bytes = _sum_expr([item.read_bytes for item in op_costs])
    total_write_bytes = _sum_expr([item.write_bytes for item in op_costs])

    if attach_attrs:
        func_op.attributes["analysis.compute"] = StringAttr(str(total_compute))
        func_op.attributes["analysis.read_bytes"] = StringAttr(str(total_read_bytes))
        func_op.attributes["analysis.write_bytes"] = StringAttr(str(total_write_bytes))

    value_traffic = [
        ValueTraffic(key, values[0], values[1]) for key, values in traffic_map.items()
    ]
    return AnalyzeKernelSummary(
        func_name=func_op.sym_name.data,
        op_costs=op_costs,
        value_traffic=value_traffic,
        total_compute=total_compute,
        total_read_bytes=total_read_bytes,
        total_write_bytes=total_write_bytes,
    )


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
