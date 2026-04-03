"""func_cost analysis pass.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 复用 `analysis(func_op, AnalysisConfig, otherargs)` 对 module 内每个 `func.func` 统计 compute/read/write。
- 提供 pass 级汇总查询与可选 `analysis.*` 属性回写。

使用示例:
- from kernel_gen.passes.analysis.func_cost import AnalyzeFuncCostPass
- module = AnalyzeFuncCostPass(attach_attrs=True).run(module)

关联文件:
- spec: spec/pass/analysis/func_cost.md
- test: test/pass/test_analysis_func_cost.py
- 功能实现: kernel_gen/passes/analysis/func_cost.py
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
import warnings

import sympy as sp
from xdsl.dialects import func
from xdsl.dialects.builtin import ModuleOp

from kernel_gen.analysis.analysis import (
    AnalysisConfig,
    AnalysisError,
    AnalysisResult,
    KernelOpCost,
    ValueTraffic,
    analysis,
)
from kernel_gen.passes.pass_manager import Pass


class FuncCostAnalysisError(ValueError):
    """func_cost pass 的显式错误。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 包装统一 analysis 主入口或 pass 入参校验阶段的错误。

    使用示例:
    - raise FuncCostAnalysisError("module must be builtin.module")

    关联文件:
    - spec: spec/pass/analysis/func_cost.md
    - test: test/pass/test_analysis_func_cost.py
    - 功能实现: kernel_gen/passes/analysis/func_cost.py
    """


OpCost = KernelOpCost


@dataclass(frozen=True)
class FuncCostSummary:
    """func_cost 的函数级汇总结果。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 暴露逐 op 成本、value_traffic 与总量。
    - 兼容旧接口 `summary.ops`。

    使用示例:
    - summary = pass_obj.get_summary("main")

    关联文件:
    - spec: spec/pass/analysis/func_cost.md
    - test: test/pass/test_analysis_func_cost.py
    - 功能实现: kernel_gen/passes/analysis/func_cost.py
    """

    func_name: str
    op_costs: Sequence[KernelOpCost]
    value_traffic: Sequence[ValueTraffic]
    total_compute: sp.Basic
    total_read_bytes: sp.Basic
    total_write_bytes: sp.Basic

    @property
    def ops(self) -> Sequence[KernelOpCost]:
        """兼容旧测试使用的 `summary.ops` 访问方式。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 返回与 `op_costs` 相同的逐 op 统计列表。

        使用示例:
        - first = summary.ops[0]

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        return self.op_costs


def _rewrite_kernel_warning(message: str) -> str:
    """将 `analysis_kernel` 告警前缀改写为 `func_cost`。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅替换当前链路需要的 `analysis_kernel skip` 前缀。

    使用示例:
    - text = _rewrite_kernel_warning("analysis_kernel skip test.unknown: unsupported op")

    关联文件:
    - spec: spec/pass/analysis/func_cost.md
    - test: test/pass/test_analysis_func_cost.py
    - 功能实现: kernel_gen/passes/analysis/func_cost.py
    """

    if message.startswith("analysis_kernel skip "):
        return "func_cost skip " + message[len("analysis_kernel skip ") :]
    return message


def _reemit_kernel_warnings(caught: Sequence[warnings.WarningMessage]) -> None:
    """转发 `analyze_kernel(...)` 产生的告警。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 保留告警类别。
    - 将 `analysis_kernel skip` 前缀改写为 `func_cost skip`。

    使用示例:
    - _reemit_kernel_warnings(caught)

    关联文件:
    - spec: spec/pass/analysis/func_cost.md
    - test: test/pass/test_analysis_func_cost.py
    - 功能实现: kernel_gen/passes/analysis/func_cost.py
    """

    for item in caught:
        warnings.warn(_rewrite_kernel_warning(str(item.message)), item.category)


def _to_func_cost_summary(summary: AnalysisResult) -> FuncCostSummary:
    """将 `AnalysisResult` 适配为 pass 侧 summary。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 直接复用统一入口产出的 op_costs/value_traffic 与 derived alias 总量。
    - 不重新计算统计公式。

    使用示例:
    - pass_summary = _to_func_cost_summary(result)

    关联文件:
    - spec: spec/pass/analysis/func_cost.md
    - test: test/pass/test_analysis_func_cost.py
    - 功能实现: kernel_gen/passes/analysis/func_cost.py
    """

    return FuncCostSummary(
        func_name=summary.func_name or "",
        op_costs=summary.op_costs,
        value_traffic=summary.value_traffic,
        total_compute=summary.total_compute,
        total_read_bytes=summary.total_read_bytes,
        total_write_bytes=summary.total_write_bytes,
    )


class AnalyzeFuncCostPass(Pass):
    """对 module 内每个 `func.func` 运行 func_cost 分析。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 逐函数调用 `analysis(func_op, AnalysisConfig, otherargs)`。
    - 将结果缓存在 pass 实例内，供 `get_summary()` 查询。

    使用示例:
    - pass_obj = AnalyzeFuncCostPass(attach_attrs=True)
    - module = pass_obj.run(module)

    关联文件:
    - spec: spec/pass/analysis/func_cost.md
    - test: test/pass/test_analysis_func_cost.py
    - 功能实现: kernel_gen/passes/analysis/func_cost.py
    """

    name = "analyze-func-cost"

    def __init__(
        self,
        *,
        predicate_size: int = 1,
        attach_attrs: bool = False,
        dtype_size_overrides: dict[str, int] | None = None,
        args: Mapping[str, Iterable[object]] | Iterable[object] | None = None,
    ) -> None:
        """初始化 func_cost pass。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 保存统一入口所需的透传参数。
        - 初始化摘要缓存。

        使用示例:
        - AnalyzeFuncCostPass(predicate_size=2, attach_attrs=True)

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        self.predicate_size = predicate_size
        self.attach_attrs = attach_attrs
        self.dtype_size_overrides = dtype_size_overrides
        self.args = args
        self._summaries: dict[str, FuncCostSummary] = {}

    def _resolve_args(self, func_op: func.FuncOp) -> list[object] | None:
        """解析当前函数要传给统一入口的 `otherargs`。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - `None` 直接返回 `None`。
        - `Mapping` 模式按函数名取值。
        - 非映射模式将整份 iterable 透传给当前函数。

        使用示例:
        - args = self._resolve_args(func_op)

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        if self.args is None:
            return None
        raw_args: object
        if isinstance(self.args, Mapping):
            func_name = func_op.sym_name.data
            if func_name not in self.args:
                raise FuncCostAnalysisError(f"args missing for func {func_name}")
            raw_args = self.args[func_name]
        else:
            raw_args = self.args
        if not isinstance(raw_args, Iterable):
            raise FuncCostAnalysisError("args must be iterable")
        return list(raw_args)

    def get_summary(self, func_name: str) -> FuncCostSummary:
        """读取单个函数的分析汇总。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 按函数名返回最近一次 `run()` 生成的 summary。

        使用示例:
        - summary = pass_obj.get_summary("main")

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        try:
            return self._summaries[func_name]
        except KeyError as exc:
            raise FuncCostAnalysisError(f"summary not found for func {func_name}") from exc

    def all_summaries(self) -> dict[str, FuncCostSummary]:
        """返回当前 pass 缓存的全部函数汇总。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 复制返回内部缓存，避免调用方原地修改。

        使用示例:
        - summaries = pass_obj.all_summaries()

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        return dict(self._summaries)

    def run(self, module: ModuleOp) -> ModuleOp:
        """执行 func_cost 分析。

        创建者: 金铲铲大作战
        最后一次更改: 金铲铲大作战

        功能说明:
        - 依次分析 module 内每个 `func.func`。
        - 返回输入 module，不引入第二套统计公式。

        使用示例:
        - module = AnalyzeFuncCostPass().run(module)

        关联文件:
        - spec: spec/pass/analysis/func_cost.md
        - test: test/pass/test_analysis_func_cost.py
        - 功能实现: kernel_gen/passes/analysis/func_cost.py
        """

        if not isinstance(module, ModuleOp):
            raise FuncCostAnalysisError("module must be builtin.module")

        self._summaries = {}
        for op in module.ops:
            if not isinstance(op, func.FuncOp):
                continue
            func_args = self._resolve_args(op)
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                try:
                    result = analysis(
                        op,
                        AnalysisConfig(
                            enable_compute=True,
                            enable_memory=True,
                            write_op_attrs=False,
                            write_func_attrs=self.attach_attrs,
                            predicate_size=self.predicate_size,
                            dtype_size_overrides=self.dtype_size_overrides,
                            otherargs=func_args,
                        ),
                        func_args,
                    )
                except AnalysisError as exc:
                    raise FuncCostAnalysisError(str(exc)) from exc
            _reemit_kernel_warnings(caught)
            summary = _to_func_cost_summary(result)
            self._summaries[summary.func_name] = summary
        return module


__all__ = [
    "AnalyzeFuncCostPass",
    "FuncCostAnalysisError",
    "FuncCostSummary",
    "OpCost",
]
