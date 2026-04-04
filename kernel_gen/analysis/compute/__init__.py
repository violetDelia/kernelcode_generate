"""Compute analysis classification helpers.

创建者: jcc你莫辜负
最后一次更改: jcc你莫辜负

功能说明:
- 定义 A2 计算主线使用的 `ComputeKind` 枚举。
- 提供 compute analyzer 的注册装饰器与迭代入口。
- 统一导出 kernel/nn 计算分类分析入口，供 `analysis.py` 做分发。

使用示例:
- from kernel_gen.analysis.compute import ComputeKind
- assert ComputeKind.SCALAR.value == "scalar"

关联文件:
- spec: spec/analysis/analysis_engine.md
- test: test/analysis/test_analysis.py
- 功能实现: kernel_gen/analysis/compute/__init__.py
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from xdsl.ir import Operation

    from kernel_gen.analysis.analysis import AnalysisConfig, _AnalyzedOp


class ComputeKind(str, Enum):
    """统一计算分类枚举。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 收口 `analysis` 主线的正式计算分类。
    - 当前固定公开 `SCALAR / VECTOR / TENSOR / MATH` 四类。

    使用示例:
    - kind = ComputeKind.VECTOR
    - assert kind.value == "vector"

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/compute/__init__.py
    """

    SCALAR = "scalar"
    VECTOR = "vector"
    TENSOR = "tensor"
    MATH = "math"


ComputeAnalyzer = Callable[["Operation", "AnalysisConfig"], "_AnalyzedOp | None"]
_DEFAULT_COMPUTE_ANALYZERS: list[ComputeAnalyzer] = []
_CUSTOM_COMPUTE_ANALYZERS: list[ComputeAnalyzer] = []
_COMPUTE_OP_ANALYZERS: dict[str, ComputeAnalyzer] = {}
_DEFAULT_REGISTERED = False


def _register_analyzer(func: ComputeAnalyzer, registry: list[ComputeAnalyzer]) -> ComputeAnalyzer:
    """向指定 registry 注册 analyzer。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 在目标 registry 中去重注册 analyzer。
    - 用于默认与自定义注册入口的内部复用。

    使用示例:
    - _register_analyzer(analyze_fn, _CUSTOM_COMPUTE_ANALYZERS)

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/compute/__init__.py
    """
    if func not in registry:
        registry.append(func)
    return func


def register_compute_analyzer(func: ComputeAnalyzer) -> ComputeAnalyzer:
    """注册 compute analyzer。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 将 analyzer 追加到 compute registry。
    - 保持注册顺序用于稳定遍历。

    使用示例:
    - @register_compute_analyzer
      def analyze(op, config): ...

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/compute/__init__.py
    """
    return _register_analyzer(func, _CUSTOM_COMPUTE_ANALYZERS)


def _normalize_op_keys(ops: object) -> tuple[str, ...]:
    """归一化 op 注册键。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持 str / op.name / tuple/list/set。
    - 返回标准化后的 op 名称列表。

    使用示例:
    - _normalize_op_keys(nn.add)
    - _normalize_op_keys((nn.add, nn.sub))

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/compute/__init__.py
    """
    if isinstance(ops, (tuple, list, set)):
        items: Iterable[object] = ops
    else:
        items = (ops,)
    keys: list[str] = []
    for item in items:
        if isinstance(item, str):
            keys.append(item)
            continue
        op_name = getattr(item, "name", None)
        if isinstance(op_name, str):
            keys.append(op_name)
            continue
        raise TypeError(f"unsupported op key: {item!r}")
    if not keys:
        raise ValueError("register_compute requires at least one op key")
    return tuple(keys)


def register_compute(ops: object) -> Callable[[ComputeAnalyzer], ComputeAnalyzer]:
    """按 op 名称注册 compute analyzer。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 支持单 op 与 tuple/list/set 形式的 op 注册。
    - 同一 op 重复注册时抛错，避免多重命中歧义。

    使用示例:
    - @register_compute(nn.add)
      def analyze_add(op, config): ...
    - @register_compute((nn.add, nn.sub))
      def analyze_add_sub(op, config): ...

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/compute/__init__.py
    """
    op_keys = _normalize_op_keys(ops)

    def decorator(func: ComputeAnalyzer) -> ComputeAnalyzer:
        for key in op_keys:
            existing = _COMPUTE_OP_ANALYZERS.get(key)
            if existing is not None and existing is not func:
                raise ValueError(f"compute analyzer already registered for op: {key}")
            _COMPUTE_OP_ANALYZERS[key] = func
        return func

    return decorator


def _ensure_default_analyzers_registered() -> None:
    """确保默认 compute analyzers 已注册。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 延迟导入避免 analysis/compute 循环依赖。
    - 确保 kernel/nn 分析入口已注册。

    使用示例:
    - _ensure_default_analyzers_registered()

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/compute/__init__.py
    """
    global _DEFAULT_REGISTERED
    if _DEFAULT_REGISTERED:
        return
    from kernel_gen.analysis.compute.kernel import analyze_scalar_kernel_op
    from kernel_gen.analysis.compute.nn import analyze_nn_elementwise_op, analyze_nn_matmul_ir_op

    _register_analyzer(analyze_scalar_kernel_op, _DEFAULT_COMPUTE_ANALYZERS)
    _register_analyzer(analyze_nn_elementwise_op, _DEFAULT_COMPUTE_ANALYZERS)
    _register_analyzer(analyze_nn_matmul_ir_op, _DEFAULT_COMPUTE_ANALYZERS)
    globals()["analyze_scalar_kernel_op"] = analyze_scalar_kernel_op
    globals()["analyze_nn_elementwise_op"] = analyze_nn_elementwise_op
    globals()["analyze_nn_matmul_ir_op"] = analyze_nn_matmul_ir_op
    _DEFAULT_REGISTERED = True


def _iter_unique_analyzers(analyzers: Iterable[ComputeAnalyzer]) -> Iterator[ComputeAnalyzer]:
    """去重迭代 analyzer 列表。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 保持注册顺序，移除重复 analyzer 引用。

    使用示例:
    - list(_iter_unique_analyzers([a, a, b]))

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/compute/__init__.py
    """
    seen: set[ComputeAnalyzer] = set()
    for analyzer in analyzers:
        if analyzer in seen:
            continue
        seen.add(analyzer)
        yield analyzer


def iter_compute_analyzers() -> tuple[ComputeAnalyzer, ...]:
    """获取当前注册的 compute analyzers。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 返回 registry 中的 analyzer 列表副本。

    使用示例:
    - for analyzer in iter_compute_analyzers(): ...

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/compute/__init__.py
    """
    _ensure_default_analyzers_registered()
    return tuple(_DEFAULT_COMPUTE_ANALYZERS + _CUSTOM_COMPUTE_ANALYZERS)


def iter_compute_analyzers_for_op(op: "Operation") -> tuple[ComputeAnalyzer, ...]:
    """按 op 返回适用的 compute analyzers。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 优先返回 op 定向注册的 analyzer。
    - 追加默认 + 自定义通用 analyzer，允许多命中合并。

    使用示例:
    - for analyzer in iter_compute_analyzers_for_op(op): ...

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/compute/__init__.py
    """
    _ensure_default_analyzers_registered()
    op_name = getattr(op, "name", None)
    analyzers: list[ComputeAnalyzer] = []
    if isinstance(op_name, str):
        analyzer = _COMPUTE_OP_ANALYZERS.get(op_name)
        if analyzer is not None:
            analyzers.append(analyzer)
    analyzers.extend(_DEFAULT_COMPUTE_ANALYZERS)
    analyzers.extend(_CUSTOM_COMPUTE_ANALYZERS)
    return tuple(_iter_unique_analyzers(analyzers))


def __getattr__(name: str) -> object:
    """懒加载 compute analyzers。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 仅在访问 analyzer 名称时触发延迟导入。

    使用示例:
    - from kernel_gen.analysis.compute import analyze_nn_matmul_ir_op

    关联文件:
    - spec: spec/analysis/analysis_engine.md
    - test: test/analysis/test_analysis.py
    - 功能实现: kernel_gen/analysis/compute/__init__.py
    """
    if name in {"analyze_scalar_kernel_op", "analyze_nn_elementwise_op", "analyze_nn_matmul_ir_op"}:
        _ensure_default_analyzers_registered()
        return globals()[name]
    raise AttributeError(name)


__all__ = [
    "ComputeKind",
    "ComputeAnalyzer",
    "register_compute_analyzer",
    "register_compute",
    "iter_compute_analyzers",
    "iter_compute_analyzers_for_op",
    "analyze_scalar_kernel_op",
    "analyze_nn_elementwise_op",
    "analyze_nn_matmul_ir_op",
]
