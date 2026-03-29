"""func_cost analysis pass.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 统计 func.func 内计算量与访存量，支持符号维度表达式。
- 输出逐 op 与函数级汇总结果。
- 可选将统计结果回写到 func.func attributes。

使用示例:
- from kernel_gen.passes.analysis.func_cost import AnalyzeFuncCostPass
- summary_pass = AnalyzeFuncCostPass(attach_attrs=True)
- summary_pass.run(module)
- summary = summary_pass.get_summary("main")

关联文件:
- spec: spec/pass/analysis/func_cost.md
- test: test/pass/test_analysis_func_cost.py
- 功能实现: kernel_gen/passes/analysis/func_cost.py
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
import re
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

from kernel_gen.dialect.nn import NnMemoryType
from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.passes.pass_manager import Pass


_SUPPORTED_NN_ELEMENTWISE = {
    "nn.add",
    "nn.sub",
    "nn.mul",
    "nn.truediv",
    "nn.eq",
    "nn.ne",
    "nn.lt",
    "nn.le",
    "nn.gt",
    "nn.ge",
}

_SUPPORTED_KERNEL_ELEMENTWISE = {
    "kernel.add",
    "kernel.sub",
    "kernel.mul",
    "kernel.div",
    "kernel.eq",
    "kernel.lt",
    "kernel.gt",
}

_SUPPORTED_DMA = {
    "dma.copy",
    "dma.load",
    "dma.store",
    "dma.slice",
    "dma.deslice",
    "dma.view",
    "dma.reshape",
    "dma.flatten",
    "dma.cast",
    "dma.alloc",
    "dma.free",
}

_COMPARE_OPS = {
    "nn.eq",
    "nn.ne",
    "nn.lt",
    "nn.le",
    "nn.gt",
    "nn.ge",
    "kernel.eq",
    "kernel.lt",
    "kernel.gt",
}


class FuncCostAnalysisError(ValueError):
    """func_cost 分析错误。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 分析失败时的统一异常类型。

    使用示例:
    - raise FuncCostAnalysisError("unsupported op: foo.bar")

    关联文件:
    - spec: spec/pass/analysis/func_cost.md
    - test: test/pass/test_analysis_func_cost.py
    - 功能实现: kernel_gen/passes/analysis/func_cost.py
    """


def _ensure_module_iterable(module: Operation) -> None:
    """校验 module 为 builtin.module 且可遍历。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - module 需为 builtin.module。
    - module.ops 必须可迭代。

    使用示例:
    - _ensure_module_iterable(module)

    关联文件:
    - spec: spec/pass/analysis/func_cost.md
    - test: test/pass/test_analysis_func_cost.py
    - 功能实现: kernel_gen/passes/analysis/func_cost.py
    """

    if not isinstance(module, Operation) or module.name != "builtin.module":
        raise FuncCostAnalysisError("module must be builtin.module")
    try:
        iter(module.ops)
    except Exception as exc:
        raise FuncCostAnalysisError("module ops must be iterable") from exc


@dataclass(frozen=True)
class OpCost:
    """单个 op 的成本统计。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 保存 op 的 compute/read/write 表达式。

    使用示例:
    - OpCost("nn.add", compute=A * B, read_bytes=A * B * 4, write_bytes=A * B * 4)

    关联文件:
    - spec: spec/pass/analysis/func_cost.md
    - test: test/pass/test_analysis_func_cost.py
    - 功能实现: kernel_gen/passes/analysis/func_cost.py
    """

    op_name: str
    compute: sp.Basic
    read_bytes: sp.Basic
    write_bytes: sp.Basic


@dataclass(frozen=True)
class FuncCostSummary:
    """函数级统计汇总。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 汇总函数内所有 op 的 compute/read/write 统计。

    使用示例:
    - summary = pass_obj.get_summary("main")

    关联文件:
    - spec: spec/pass/analysis/func_cost.md
    - test: test/pass/test_analysis_func_cost.py
    - 功能实现: kernel_gen/passes/analysis/func_cost.py
    """

    func_name: str
    ops: list[OpCost]
    total_compute: sp.Basic
    total_read_bytes: sp.Basic
    total_write_bytes: sp.Basic


class AnalyzeFuncCostPass(Pass):
    """func_cost 分析 pass。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 扫描 module 内 func.func，统计 compute/read/write。

    使用示例:
    - AnalyzeFuncCostPass(attach_attrs=True).run(module)

    关联文件:
    - spec: spec/pass/analysis/func_cost.md
    - test: test/pass/test_analysis_func_cost.py
    - 功能实现: kernel_gen/passes/analysis/func_cost.py
    """

    name = "analysis-func-cost"

    def __init__(
        self,
        predicate_size: int = 1,
        attach_attrs: bool = False,
        dtype_size_overrides: dict[str, int] | None = None,
    ) -> None:
        """初始化 func_cost pass。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 记录 predicate_size、attach_attrs 与 dtype 覆盖表。

        使用示例:
        - AnalyzeFuncCostPass(predicate_size=2, attach_attrs=True)

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        if predicate_size <= 0:
            raise FuncCostAnalysisError("predicate_size must be positive")
        if dtype_size_overrides is not None:
            for key, value in dtype_size_overrides.items():
                if not isinstance(value, int) or value <= 0:
                    raise FuncCostAnalysisError(
                        f"dtype_size_overrides[{key}] must be positive int"
                    )

        self.predicate_size = predicate_size
        self.attach_attrs = attach_attrs
        self.dtype_size_overrides = {
            key.lower(): value for key, value in (dtype_size_overrides or {}).items()
        }
        self._summaries: dict[str, FuncCostSummary] = {}

    def run(self, module: Operation) -> Operation:
        """执行 func_cost 分析。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 遍历 module 内 func.func 并记录统计结果。

        使用示例:
        - AnalyzeFuncCostPass().run(module)

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        self._summaries = {}
        try:
            _ensure_module_iterable(module)
            for op in module.ops:
                if isinstance(op, func.FuncOp):
                    summary = self._analyze_func(op)
                    self._summaries[summary.func_name] = summary
                    if self.attach_attrs:
                        self._attach_summary_attrs(op, summary)
        except FuncCostAnalysisError:
            raise
        except Exception as exc:
            raise FuncCostAnalysisError(f"func_cost analysis failed: {exc}") from exc
        return module

    def get_summary(self, func_name: str) -> FuncCostSummary:
        """获取指定函数的统计结果。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 返回 func_name 对应的 FuncCostSummary。

        使用示例:
        - summary = pass_obj.get_summary("main")

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        if func_name not in self._summaries:
            raise FuncCostAnalysisError(f"func {func_name} not analyzed")
        return self._summaries[func_name]

    def all_summaries(self) -> list[FuncCostSummary]:
        """返回全部函数的统计结果。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 按记录顺序返回所有 FuncCostSummary。

        使用示例:
        - summaries = pass_obj.all_summaries()

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        return list(self._summaries.values())

    def _attach_summary_attrs(self, func_op: func.FuncOp, summary: FuncCostSummary) -> None:
        """将统计结果写回 func.func 属性。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 写入 analysis.compute/read_bytes/write_bytes 字符串属性。

        使用示例:
        - self._attach_summary_attrs(func_op, summary)

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        func_op.attributes["analysis.compute"] = StringAttr(str(summary.total_compute))
        func_op.attributes["analysis.read_bytes"] = StringAttr(str(summary.total_read_bytes))
        func_op.attributes["analysis.write_bytes"] = StringAttr(str(summary.total_write_bytes))

    def _analyze_func(self, func_op: func.FuncOp) -> FuncCostSummary:
        """分析单个 func.func。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 遍历函数内所有 op 并汇总成本。

        使用示例:
        - summary = self._analyze_func(func_op)

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        ops: list[OpCost] = []
        for op in self._iter_func_ops(func_op):
            if self._should_ignore_op(op):
                continue
            op_cost = self._analyze_op(op)
            if op_cost is not None:
                ops.append(op_cost)

        total_compute = self._sum_expr([item.compute for item in ops])
        total_read_bytes = self._sum_expr([item.read_bytes for item in ops])
        total_write_bytes = self._sum_expr([item.write_bytes for item in ops])
        return FuncCostSummary(
            func_name=func_op.sym_name.data,
            ops=ops,
            total_compute=total_compute,
            total_read_bytes=total_read_bytes,
            total_write_bytes=total_write_bytes,
        )

    def _iter_func_ops(self, func_op: func.FuncOp) -> Iterator[Operation]:
        """按顺序遍历 func.func 内全部 op。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 深度优先遍历函数 body 及嵌套 region。

        使用示例:
        - for op in self._iter_func_ops(func_op):
              ...

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        for block in func_op.body.blocks:
            yield from self._iter_block_ops(block.ops)

    def _iter_block_ops(self, ops: Iterable[Operation]) -> Iterator[Operation]:
        """递归遍历 block 内 op 列表。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 先返回当前 op，再递归遍历其 region。

        使用示例:
        - list(self._iter_block_ops(block.ops))

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        for op in ops:
            yield op
            for region in op.regions:
                for block in region.blocks:
                    yield from self._iter_block_ops(block.ops)

    def _should_ignore_op(self, op: Operation) -> bool:
        """判断是否忽略当前 op。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - func.return 与 arith.constant 默认不计入成本。

        使用示例:
        - if self._should_ignore_op(op):
              return

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        if isinstance(op, func.ReturnOp):
            return True
        if isinstance(op, arith.ConstantOp):
            return True
        return False

    def _warn_skip(self, op: Operation, reason: str) -> None:
        """记录跳过 op 的告警信息。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 使用 warnings.warn 输出跳过原因。

        使用示例:
        - self._warn_skip(op, "unsupported op")

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        warnings.warn(f"func_cost skip {op.name}: {reason}", UserWarning)

    def _sum_expr(self, items: Iterable[sp.Basic]) -> sp.Basic:
        """求和表达式列表。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 使用 sympy 表达式合并求和。

        使用示例:
        - total = self._sum_expr([expr_a, expr_b])

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        total = sp.Integer(0)
        for item in items:
            total = total + item
        return total

    def _analyze_op(self, op: Operation) -> OpCost | None:
        """分析单个 op 的成本。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 根据 op 类型计算 compute/read/write。

        使用示例:
        - op_cost = self._analyze_op(op)

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        name = op.name
        if name in _SUPPORTED_NN_ELEMENTWISE:
            return self._analyze_elementwise(op, is_kernel=False)
        if name == "nn.matmul":
            return self._analyze_matmul(op)
        if name == "nn.broadcast":
            return self._analyze_broadcast(op)
        if name in _SUPPORTED_KERNEL_ELEMENTWISE:
            return self._analyze_elementwise(op, is_kernel=True)
        if name == "kernel.select":
            return self._analyze_kernel_select(op)
        if name == "kernel.cast":
            return self._analyze_kernel_cast(op)
        if name in _SUPPORTED_DMA:
            return self._analyze_dma(op)

        self._warn_skip(op, "unsupported op")
        return None

    def _analyze_elementwise(self, op: Operation, is_kernel: bool) -> OpCost | None:
        """统计逐元素 op 成本。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - compute 按输出 numel 计。
        - read/write 统计读写的 memory 元素字节数。

        使用示例:
        - self._analyze_elementwise(op, is_kernel=False)

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        output_type = self._get_output_mem_type(op, is_kernel=is_kernel)
        if output_type is None:
            self._warn_skip(op, "missing output memory type")
            return None

        numel = self._numel_from_type(output_type)
        if numel is None:
            self._warn_skip(op, "unsupported output shape")
            return None

        compute = numel
        read_bytes = self._read_bytes_from_operands(self._read_operands_for_op(op))
        if read_bytes is None:
            self._warn_skip(op, "unsupported operand dtype or shape")
            return None

        write_bytes = self._write_bytes_from_output(op, output_type)
        if write_bytes is None:
            self._warn_skip(op, "unsupported output dtype")
            return None

        return OpCost(op.name, compute=compute, read_bytes=read_bytes, write_bytes=write_bytes)

    def _analyze_matmul(self, op: Operation) -> OpCost | None:
        """统计 nn.matmul 成本。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - compute=2*M*N*K。
        - read/write 按 lhs/rhs/result 统计。

        使用示例:
        - self._analyze_matmul(op)

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        if len(op.operands) < 2:
            self._warn_skip(op, "matmul requires lhs/rhs operands")
            return None

        lhs_type = self._get_mem_type(op.operands[0])
        rhs_type = self._get_mem_type(op.operands[1])
        out_type = self._get_output_mem_type(op, is_kernel=False)
        if lhs_type is None or rhs_type is None or out_type is None:
            self._warn_skip(op, "matmul operand/output type missing")
            return None

        lhs_shape = lhs_type.shape
        rhs_shape = rhs_type.shape
        if len(lhs_shape.data) < 2 or len(rhs_shape.data) < 2:
            self._warn_skip(op, "matmul requires rank-2 operands")
            return None

        lhs_m = self._dim_to_expr(lhs_shape.data[0])
        lhs_k = self._dim_to_expr(lhs_shape.data[1])
        rhs_k = self._dim_to_expr(rhs_shape.data[0])
        rhs_n = self._dim_to_expr(rhs_shape.data[1])
        if None in (lhs_m, lhs_k, rhs_k, rhs_n):
            self._warn_skip(op, "matmul dimension parse failed")
            return None

        compute = sp.Integer(2) * lhs_m * rhs_n * lhs_k
        read_bytes = self._read_bytes_from_operands(self._read_operands_for_op(op))
        if read_bytes is None:
            self._warn_skip(op, "matmul operand dtype unsupported")
            return None
        write_bytes = self._write_bytes_from_output(op, out_type)
        if write_bytes is None:
            self._warn_skip(op, "matmul output dtype unsupported")
            return None

        return OpCost(op.name, compute=compute, read_bytes=read_bytes, write_bytes=write_bytes)

    def _analyze_broadcast(self, op: Operation) -> OpCost | None:
        """统计 nn.broadcast 成本。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - compute=0，read/write 统计输入与输出。

        使用示例:
        - self._analyze_broadcast(op)

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        output_type = self._get_output_mem_type(op, is_kernel=False)
        if output_type is None:
            self._warn_skip(op, "broadcast output type missing")
            return None

        read_bytes = self._read_bytes_from_operands(self._read_operands_for_op(op))
        if read_bytes is None:
            self._warn_skip(op, "broadcast operand dtype unsupported")
            return None

        write_bytes = self._write_bytes_from_output(op, output_type)
        if write_bytes is None:
            self._warn_skip(op, "broadcast output dtype unsupported")
            return None

        return OpCost(op.name, compute=sp.Integer(0), read_bytes=read_bytes, write_bytes=write_bytes)

    def _analyze_kernel_select(self, op: Operation) -> OpCost | None:
        """统计 kernel.select 成本。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - compute 按输出 numel 计。
        - read 统计 cond/lhs/rhs，write 统计 out。

        使用示例:
        - self._analyze_kernel_select(op)

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        output_type = self._get_output_mem_type(op, is_kernel=True)
        if output_type is None:
            self._warn_skip(op, "kernel.select output type missing")
            return None

        numel = self._numel_from_type(output_type)
        if numel is None:
            self._warn_skip(op, "kernel.select output shape unsupported")
            return None

        read_bytes = self._read_bytes_from_operands(self._read_operands_for_op(op))
        if read_bytes is None:
            self._warn_skip(op, "kernel.select operand dtype unsupported")
            return None

        write_bytes = self._write_bytes_from_output(op, output_type)
        if write_bytes is None:
            self._warn_skip(op, "kernel.select output dtype unsupported")
            return None

        return OpCost(op.name, compute=numel, read_bytes=read_bytes, write_bytes=write_bytes)

    def _analyze_kernel_cast(self, op: Operation) -> OpCost | None:
        """统计 kernel.cast 成本。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - compute 按输出 numel 计。
        - read/write 按 input/out 统计。

        使用示例:
        - self._analyze_kernel_cast(op)

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        output_type = self._get_output_mem_type(op, is_kernel=True)
        if output_type is None:
            self._warn_skip(op, "kernel.cast output type missing")
            return None

        numel = self._numel_from_type(output_type)
        if numel is None:
            self._warn_skip(op, "kernel.cast output shape unsupported")
            return None

        read_bytes = self._read_bytes_from_operands(self._read_operands_for_op(op))
        if read_bytes is None:
            self._warn_skip(op, "kernel.cast operand dtype unsupported")
            return None

        write_bytes = self._write_bytes_from_output(op, output_type)
        if write_bytes is None:
            self._warn_skip(op, "kernel.cast output dtype unsupported")
            return None

        return OpCost(op.name, compute=numel, read_bytes=read_bytes, write_bytes=write_bytes)

    def _analyze_dma(self, op: Operation) -> OpCost | None:
        """统计 DMA op 成本。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - copy/load/store/slice/deslice/view/reshape/flatten 按搬运统计。
        - cast compute=numel(output)。
        - alloc/free 计 0。

        使用示例:
        - self._analyze_dma(op)

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        if op.name in {"dma.alloc", "dma.free"}:
            return OpCost(op.name, compute=sp.Integer(0), read_bytes=sp.Integer(0), write_bytes=sp.Integer(0))

        output_type = self._get_dma_output_type(op)
        if output_type is None:
            self._warn_skip(op, "dma output type missing")
            return None

        read_bytes = self._read_bytes_from_operands(self._read_operands_for_op(op))
        if read_bytes is None:
            self._warn_skip(op, "dma operand dtype unsupported")
            return None

        write_bytes = self._write_bytes_from_output(op, output_type)
        if write_bytes is None:
            self._warn_skip(op, "dma output dtype unsupported")
            return None

        sizes_operands = self._get_dma_sizes_operands(op)
        if sizes_operands is not None:
            sizes_numel = self._numel_from_symbol_operands(sizes_operands)
            if sizes_numel is None:
                self._warn_skip(op, "dma sizes unsupported")
                return None
            elem_size = self._element_size(output_type.element_type)
            if elem_size is None:
                self._warn_skip(op, "dma output dtype unsupported")
                return None
            sizes_bytes = sizes_numel * elem_size
            if op.name in {"dma.load", "dma.slice"}:
                read_bytes = sizes_bytes
                write_bytes = sizes_bytes
            elif op.name in {"dma.store", "dma.deslice"}:
                write_bytes = sizes_bytes

        if op.name == "dma.cast":
            compute = self._numel_from_type(output_type)
            if compute is None:
                self._warn_skip(op, "dma.cast output shape unsupported")
                return None
        else:
            compute = sp.Integer(0)

        return OpCost(op.name, compute=compute, read_bytes=read_bytes, write_bytes=write_bytes)

    def _get_dma_sizes_operands(self, op: Operation) -> list[SSAValue] | None:
        """获取 DMA op 的 sizes operands。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 仅 dma.load/slice/store/deslice 包含 sizes。

        使用示例:
        - sizes = self._get_dma_sizes_operands(op)

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        if op.name in {"dma.load", "dma.slice", "dma.store", "dma.deslice"}:
            sizes = getattr(op, "sizes", None)
            if sizes is None:
                return None
            return list(sizes)
        return None

    def _get_dma_output_type(self, op: Operation) -> NnMemoryType | None:
        """获取 DMA op 的输出内存类型。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - copy 使用 target 作为输出。
        - store 使用 target（第 2 个 operand）作为输出。
        - load/slice/deslice/view/reshape/flatten/cast 使用 result。

        使用示例:
        - output_type = self._get_dma_output_type(op)

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        if op.name == "dma.copy":
            if not op.operands:
                return None
            return self._get_mem_type(op.operands[-1])
        if op.name == "dma.store":
            if len(op.operands) < 2:
                return None
            return self._get_mem_type(op.operands[1])
        if op.results:
            return self._get_mem_type(op.results[0])
        return None

    def _get_output_mem_type(self, op: Operation, is_kernel: bool) -> NnMemoryType | None:
        """获取 op 输出的 nn.memory 类型。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - nn/dma 使用结果类型，kernel 使用 out operand。

        使用示例:
        - mem_type = self._get_output_mem_type(op, is_kernel=False)

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        if is_kernel:
            if not op.operands:
                return None
            return self._get_mem_type(op.operands[-1])
        if op.results:
            return self._get_mem_type(op.results[0])
        return None

    def _read_bytes_from_operands(self, operands: Iterable[SSAValue]) -> sp.Basic | None:
        """统计 operands 的读取字节数。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 仅统计 nn.memory operand；标量常量不计读。

        使用示例:
        - read_bytes = self._read_bytes_from_operands(op.operands)

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        total = sp.Integer(0)
        for operand in operands:
            mem_type = self._get_mem_type(operand)
            if mem_type is None:
                continue
            numel = self._numel_from_type(mem_type)
            if numel is None:
                return None
            elem_size = self._element_size(mem_type.element_type)
            if elem_size is None:
                return None
            total = total + numel * elem_size
        return total

    def _read_operands_for_op(self, op: Operation) -> list[SSAValue]:
        """获取 op 对应的读取 operands。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 根据 op 类型过滤掉写入目标 operand。

        使用示例:
        - operands = self._read_operands_for_op(op)

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        name = op.name
        if name in _SUPPORTED_NN_ELEMENTWISE:
            return list(op.operands)
        if name == "nn.matmul":
            return list(op.operands[:2])
        if name == "nn.broadcast":
            return list(op.operands[:1])
        if name in _SUPPORTED_KERNEL_ELEMENTWISE:
            return list(op.operands[:-1])
        if name == "kernel.select":
            return list(op.operands[:3])
        if name == "kernel.cast":
            return list(op.operands[:1])
        if name in {
            "dma.copy",
            "dma.load",
            "dma.store",
            "dma.slice",
            "dma.deslice",
            "dma.view",
            "dma.reshape",
            "dma.flatten",
            "dma.cast",
        }:
            return list(op.operands[:1])
        return []

    def _write_bytes_from_output(self, op: Operation, mem_type: NnMemoryType) -> sp.Basic | None:
        """统计 output 的写入字节数。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 若 compare op 输出为 i1，使用 predicate_size。

        使用示例:
        - write_bytes = self._write_bytes_from_output(op, mem_type)

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        numel = self._numel_from_type(mem_type)
        if numel is None:
            return None

        if op.name in _COMPARE_OPS and self._is_predicate_type(mem_type.element_type):
            elem_size = self.predicate_size
        else:
            elem_size = self._element_size(mem_type.element_type)
            if elem_size is None:
                return None

        return numel * elem_size

    def _get_mem_type(self, value: SSAValue) -> NnMemoryType | None:
        """获取 SSAValue 的 nn.memory 类型。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 非 nn.memory 的 value 返回 None。

        使用示例:
        - mem_type = self._get_mem_type(op.operands[0])

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        if not isinstance(value.type, NnMemoryType):
            return None
        return value.type

    def _numel_from_type(self, mem_type: NnMemoryType) -> sp.Basic | None:
        """计算 nn.memory 的元素数量。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 将 shape 转换为 sympy 乘积表达式。

        使用示例:
        - numel = self._numel_from_type(mem_type)

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        return self._numel_from_shape(mem_type.shape)

    def _numel_from_shape(self, shape: ArrayAttr) -> sp.Basic | None:
        """基于 shape 计算元素总数。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 逐维相乘生成符号表达式。

        使用示例:
        - numel = self._numel_from_shape(mem_type.shape)

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        expr = sp.Integer(1)
        for dim in shape.data:
            dim_expr = self._dim_to_expr(dim)
            if dim_expr is None:
                return None
            expr = expr * dim_expr
        return expr

    def _numel_from_symbol_operands(self, operands: Iterable[SSAValue]) -> sp.Basic | None:
        """基于 SymbolValueType operands 计算元素数量。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 将 SymbolValueType operands 转换为 sympy 表达式并求乘积。

        使用示例:
        - numel = self._numel_from_symbol_operands(op.sizes)

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        expr = sp.Integer(1)
        for operand in operands:
            dim_expr = self._symbol_operand_to_expr(operand)
            if dim_expr is None:
                return None
            expr = expr * dim_expr
        return expr

    def _symbol_operand_to_expr(self, operand: SSAValue) -> sp.Basic | None:
        """将 SymbolValueType operand 转为 sympy 表达式。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 对非 SymbolValueType 的 operand 返回 None。

        使用示例:
        - expr = self._symbol_operand_to_expr(op.sizes[0])

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        if not isinstance(operand.type, SymbolValueType):
            return None
        return self._symbol_value_to_expr(operand.type)

    def _symbol_value_to_expr(self, value: SymbolValueType) -> sp.Basic | None:
        """将 SymbolValueType 转为 sympy 表达式。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 常量直接转为 sympy.Integer。
        - 符号表达式走解析器。

        使用示例:
        - expr = self._symbol_value_to_expr(SymbolValueType.from_expr("N + 1"))

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        raw_value = value.get_value()
        if isinstance(raw_value, int):
            return sp.Integer(raw_value)
        return self._parse_symbol_expr(raw_value)

    def _parse_symbol_expr(self, expr: str) -> sp.Basic | None:
        """解析符号表达式字符串为 sympy 表达式。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 基于 symbol 名称构造 sympy locals 并调用 sympify。

        使用示例:
        - expr = self._parse_symbol_expr("M * N")

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        normalized = expr.strip()
        if not normalized:
            return None
        symbol_names = {
            name for name in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", normalized) if name != "floor"
        }
        locals_map = {name: SymbolDim(name).get_symbol() for name in symbol_names}
        locals_map["floor"] = sp.floor
        try:
            return sp.sympify(normalized, locals=locals_map, evaluate=False)
        except (sp.SympifyError, TypeError, ValueError):
            return None

    def _dim_to_expr(self, dim: Attribute) -> sp.Basic | None:
        """将单个维度转换为 sympy 表达式。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - IntAttr 直接转为 Integer。
        - StringAttr 数字字符串转为 Integer，否则转为 SymbolDim。

        使用示例:
        - expr = self._dim_to_expr(StringAttr("M"))

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
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

    def _element_size(self, element_type: Attribute) -> int | None:
        """获取元素类型的字节大小。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 支持 i1/i8/i16/i32/i64 与 f16/bf16/f32/f64。
        - 支持 dtype_size_overrides 覆盖。

        使用示例:
        - size = self._element_size(i32)

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        key = str(element_type).lower()
        if key in self.dtype_size_overrides:
            return self.dtype_size_overrides[key]

        if isinstance(element_type, IntegerType):
            width = int(element_type.width.data)
            if width == 1:
                return 1
            if width == 8:
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

    def _is_predicate_type(self, element_type: Attribute) -> bool:
        """判断是否为 i1 predicate 类型。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - IntegerType 且宽度为 1 时返回 True。

        使用示例:
        - self._is_predicate_type(i1)

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        return isinstance(element_type, IntegerType) and int(element_type.width.data) == 1


__all__ = [
    "AnalyzeFuncCostPass",
    "FuncCostAnalysisError",
    "FuncCostSummary",
    "OpCost",
]
