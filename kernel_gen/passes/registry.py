"""Pass registry API.

创建者: 小李飞刀
最后一次更改: 朽木露琪亚

功能说明:
- 提供 pass / pipeline 的进程内注册表，统一“名字 -> 构造器”的解析入口。
- 支持 legacy `Pass` 与 xdsl `ModulePass` 的统一注册与构造。
- 为工具层（如 ircheck）提供稳定名称解析能力，避免依赖具体 Python import path。

使用示例:
- from kernel_gen.passes.registry import load_builtin_passes, build_registered_pass
- load_builtin_passes()
- pass_obj = build_registered_pass("no-op")

关联文件:
- spec: [spec/pass/registry.md](spec/pass/registry.md)
- test: [test/pass/test_pass_registry.py](test/pass/test_pass_registry.py)
- 功能实现: [kernel_gen/passes/registry.py](kernel_gen/passes/registry.py)
"""

from __future__ import annotations

from collections.abc import Callable
import inspect
from typing import TypeVar

from xdsl.passes import ModulePass

from .pass_manager import Pass, PassManager

PassType = TypeVar("PassType")

_PASS_REGISTRY: dict[str, type[Pass] | type[ModulePass]] = {}
_PIPELINE_REGISTRY: dict[str, Callable[..., PassManager]] = {}
_BUILTINS_LOADED = False


class PassRegistryError(RuntimeError):
    """Pass registry 预期失败异常。

    创建者: 睡觉小分队
    最后一次更改: 朽木露琪亚

    功能说明:
    - 表示 pass / pipeline 注册与查询阶段的可预期失败。
    - `str(e)` 必须以 `spec/pass/registry.md` 列出的错误短语之一开头，便于测试做机械匹配。

    使用示例:
    - raise PassRegistryError("PassRegistryError: unknown pass 'tile'")

    关联文件:
    - spec: [spec/pass/registry.md](spec/pass/registry.md)
    - test: [test/pass/test_pass_registry.py](test/pass/test_pass_registry.py)
    - 功能实现: [kernel_gen/passes/registry.py](kernel_gen/passes/registry.py)
    """


def register_pass(pass_cls: type[PassType]) -> type[PassType]:
    """注册公开 pass 类。

    创建者: 睡觉小分队
    最后一次更改: 朽木露琪亚

    功能说明:
    - 装饰器：注册一个公开 pass 类（`Pass` 或 `ModulePass` 子类），使用 `pass_cls.name` 作为 key。
    - 同一名字在进程内必须唯一；重复注册立即失败。

    使用示例:
    - @register_pass
      class TilePass(Pass):
          name = "tile"
          def run(self, module): return module

    关联文件:
    - spec: [spec/pass/registry.md](spec/pass/registry.md)
    - test: [test/pass/test_pass_registry.py](test/pass/test_pass_registry.py)
    - 功能实现: [kernel_gen/passes/registry.py](kernel_gen/passes/registry.py)
    """

    if not isinstance(pass_cls, type) or not (issubclass(pass_cls, Pass) or issubclass(pass_cls, ModulePass)):
        raise PassRegistryError("PassRegistryError: register_pass expects Pass subclass")
    pass_name = getattr(pass_cls, "name", None)
    if not isinstance(pass_name, str) or not pass_name.strip():
        raise PassRegistryError("PassRegistryError: pass name must be non-empty string")
    if pass_name in _PASS_REGISTRY:
        raise PassRegistryError(f"PassRegistryError: pass '{pass_name}' is already registered")
    _PASS_REGISTRY[pass_name] = pass_cls
    return pass_cls


def register_pipeline(name: str) -> Callable[[Callable[..., PassManager]], Callable[..., PassManager]]:
    """注册公开 pipeline builder。

    创建者: 睡觉小分队
    最后一次更改: 金铲铲大作战

    功能说明:
    - 装饰器工厂：注册一个公开 pipeline builder，使用 `name` 作为 key。
    - 同一名字在进程内必须唯一；重复注册立即失败。
    - builder 可选接受 `options` 参数，用于带选项的 pipeline 构造入口。

    使用示例:
    - @register_pipeline("default-lowering")
      def build_default_lowering() -> PassManager:
          return PassManager(name="lowering")

    关联文件:
    - spec: [spec/pass/registry.md](spec/pass/registry.md)
    - test: [test/pass/test_pass_registry.py](test/pass/test_pass_registry.py)
    - 功能实现: [kernel_gen/passes/registry.py](kernel_gen/passes/registry.py)
    """

    if not isinstance(name, str) or not name.strip():
        raise PassRegistryError("PassRegistryError: pipeline name must be non-empty string")
    if name in _PIPELINE_REGISTRY:
        raise PassRegistryError(f"PassRegistryError: pipeline '{name}' is already registered")

    def _decorator(builder: Callable[..., PassManager]) -> Callable[..., PassManager]:
        if not callable(builder):
            raise PassRegistryError("PassRegistryError: register_pipeline expects callable builder")
        _PIPELINE_REGISTRY[name] = builder
        return builder

    return _decorator


def _normalize_options(options: dict[str, str] | None) -> dict[str, str]:
    """规整 build_registered_* 的 options 参数。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 将 None 规整为空字典。
    - 复制输入，避免调用方侧的可变状态影响后续处理。

    使用示例:
    - opts = _normalize_options(None)
    - opts = _normalize_options({"mode": "fast"})

    关联文件:
    - spec: [spec/pass/registry.md](spec/pass/registry.md)
    - test: [test/pass/test_pass_registry.py](test/pass/test_pass_registry.py)
    - 功能实现: [kernel_gen/passes/registry.py](kernel_gen/passes/registry.py)
    """

    if options is None:
        return {}
    return dict(options)


def _pipeline_accepts_options(builder: Callable[..., PassManager]) -> bool:
    """判断 pipeline builder 是否接收 options 参数。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 基于函数签名判断是否支持单个 options 参数。
    - 若含 *args/**kwargs 则视为支持。

    使用示例:
    - if _pipeline_accepts_options(builder): ...

    关联文件:
    - spec: [spec/pass/registry.md](spec/pass/registry.md)
    - test: [test/pass/test_pass_registry.py](test/pass/test_pass_registry.py)
    - 功能实现: [kernel_gen/passes/registry.py](kernel_gen/passes/registry.py)
    """

    signature = inspect.signature(builder)
    params = list(signature.parameters.values())
    if not params:
        return False
    for param in params:
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            return True
    return len(params) == 1


def build_registered_pass(name: str, options: dict[str, str] | None = None) -> Pass | ModulePass:
    """根据名称构造 pass 实例。

    创建者: 睡觉小分队
    最后一次更改: 金铲铲大作战

    功能说明:
    - 根据 pass name 构造并返回 pass 实例。
    - 迁移期允许返回 legacy `Pass` 或 xdsl `ModulePass`，由注册的类决定。
    - 若提供 options，则要求 pass_cls 提供 `from_options(options)` 构造入口。
    - options 为空时沿用“无参构造”规则；不可构造时报稳定错误短语。

    使用示例:
    - load_builtin_passes()
    - pass_obj = build_registered_pass("tile")
    - pass_obj = build_registered_pass("tile", {"analysis-only": "true"})

    关联文件:
    - spec: [spec/pass/registry.md](spec/pass/registry.md)
    - test: [test/pass/test_pass_registry.py](test/pass/test_pass_registry.py)
    - 功能实现: [kernel_gen/passes/registry.py](kernel_gen/passes/registry.py)
    """

    if name not in _PASS_REGISTRY:
        raise PassRegistryError(f"PassRegistryError: unknown pass '{name}'")
    pass_cls = _PASS_REGISTRY[name]
    normalized_options = _normalize_options(options)
    if normalized_options:
        from_options = getattr(pass_cls, "from_options", None)
        if not callable(from_options):
            raise PassRegistryError(f"PassRegistryError: pass '{name}' does not accept options")
        try:
            pass_obj = from_options(normalized_options)
        except Exception as exc:  # pragma: no cover - exception detail not stable
            if name == "launch-kernel-cost-func":
                from kernel_gen.passes.tuning.launch_kernel_cost_func import (
                    LaunchKernelCostFuncError,
                )

                if isinstance(exc, LaunchKernelCostFuncError):
                    raise
            raise PassRegistryError(f"PassRegistryError: pass '{name}' option error") from exc
        if not isinstance(pass_obj, (Pass, ModulePass)):
            raise PassRegistryError(f"PassRegistryError: pass '{name}' option error")
        return pass_obj
    try:
        return pass_cls()
    except Exception as exc:  # pragma: no cover - exception detail not stable
        raise PassRegistryError(f"PassRegistryError: pass '{name}' is not constructible") from exc


def build_registered_pipeline(name: str, options: dict[str, str] | None = None) -> PassManager:
    """根据名称构造 pipeline 对应的 PassManager。

    创建者: 睡觉小分队
    最后一次更改: 金铲铲大作战

    功能说明:
    - 根据 pipeline name 调用 builder 构造并返回 `PassManager`。
    - 若提供 options，则要求 builder 接受 `options` 参数。
    - builder 返回值必须为 `PassManager`；否则报告稳定错误短语。

    使用示例:
    - load_builtin_passes()
    - pm = build_registered_pipeline("no-op-pipeline")
    - pm = build_registered_pipeline("default-lowering", {"analysis-only": "true"})
    - lowered = pm.run(module)

    关联文件:
    - spec: [spec/pass/registry.md](spec/pass/registry.md)
    - test: [test/pass/test_pass_registry.py](test/pass/test_pass_registry.py)
    - 功能实现: [kernel_gen/passes/registry.py](kernel_gen/passes/registry.py)
    """

    if name not in _PIPELINE_REGISTRY:
        raise PassRegistryError(f"PassRegistryError: unknown pipeline '{name}'")
    builder = _PIPELINE_REGISTRY[name]
    normalized_options = _normalize_options(options)
    if normalized_options:
        if not _pipeline_accepts_options(builder):
            raise PassRegistryError(f"PassRegistryError: pipeline '{name}' does not accept options")
        try:
            pm = builder(normalized_options)
        except Exception as exc:  # pragma: no cover - builder error path not deterministic
            raise PassRegistryError(f"PassRegistryError: pipeline '{name}' option error") from exc
    else:
        try:
            pm = builder()
        except Exception as exc:  # pragma: no cover - builder error path not deterministic
            raise PassRegistryError(
                f"PassRegistryError: pipeline '{name}' did not return PassManager"
            ) from exc
    if not isinstance(pm, PassManager):
        raise PassRegistryError(f"PassRegistryError: pipeline '{name}' did not return PassManager")
    return pm


def load_builtin_passes() -> None:
    """加载仓库内置 pass / pipeline。

    创建者: 睡觉小分队
    最后一次更改: 朽木露琪亚

    功能说明:
    - 主动加载仓库内置 pass / pipeline，使装饰器注册与显式注册生效。
    - 满足幂等性：重复调用不会重复注册或造成副作用。

    使用示例:
    - load_builtin_passes()
    - names = list_registered_passes()

    关联文件:
    - spec: [spec/pass/registry.md](spec/pass/registry.md)
    - test: [test/pass/test_pass_registry.py](test/pass/test_pass_registry.py)
    - 功能实现: [kernel_gen/passes/registry.py](kernel_gen/passes/registry.py)
    """

    global _BUILTINS_LOADED
    if _BUILTINS_LOADED:
        return

    class NoOpPass(Pass):
        name = "no-op"

        def run(self: "NoOpPass", target: object) -> object:
            return target

    def _build_no_op_pipeline() -> PassManager:
        pm = PassManager(name="no-op-pipeline")
        pm.add_pass(NoOpPass())
        return pm

    if NoOpPass.name not in _PASS_REGISTRY:
        register_pass(NoOpPass)
    if "no-op-pipeline" not in _PIPELINE_REGISTRY:
        register_pipeline("no-op-pipeline")(_build_no_op_pipeline)

    from kernel_gen.passes.analysis.func_cost import AnalyzeFuncCostPass
    from kernel_gen.passes.buffer_results_to_out_params import BufferResultsToOutParamsPass
    from kernel_gen.passes.decompass import DecompassPass
    from kernel_gen.passes.lowering.dma_memory_hierarchy import LowerDmaMemoryHierarchyPass
    from kernel_gen.passes.lowering.memory_pool import MemoryPoolPass
    from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass
    from kernel_gen.passes.outline_device_kernel import OutlineDeviceKernelPass
    from kernel_gen.passes.symbol_loop_hoist import SymbolLoopHoistPass
    from kernel_gen.passes.lowering.tile import TileAnalysisPass, TilePass
    from kernel_gen.passes.tuning import LaunchKernelCostFuncPass

    for pass_cls in (
        AnalyzeFuncCostPass,
        DecompassPass,
        NnLoweringPass,
        BufferResultsToOutParamsPass,
        LowerDmaMemoryHierarchyPass,
        OutlineDeviceKernelPass,
        TilePass,
        TileAnalysisPass,
        SymbolLoopHoistPass,
        MemoryPoolPass,
        LaunchKernelCostFuncPass,
    ):
        pass_name = getattr(pass_cls, "name", None)
        if isinstance(pass_name, str) and pass_name in _PASS_REGISTRY:
            continue
        register_pass(pass_cls)

    from kernel_gen.passes.pipeline import build_default_lowering_pipeline

    if "default-lowering" not in _PIPELINE_REGISTRY:
        register_pipeline("default-lowering")(build_default_lowering_pipeline)

    _BUILTINS_LOADED = True


def list_registered_passes() -> list[str]:
    """列出当前已注册 pass 名称。

    创建者: 睡觉小分队
    最后一次更改: 小李飞刀

    功能说明:
    - 返回当前已注册 pass 名称列表。
    - 返回值顺序必须可预测，便于测试断言；按字典序排序。

    使用示例:
    - load_builtin_passes()
    - assert "no-op" in list_registered_passes()

    关联文件:
    - spec: [spec/pass/registry.md](spec/pass/registry.md)
    - test: [test/pass/test_pass_registry.py](test/pass/test_pass_registry.py)
    - 功能实现: [kernel_gen/passes/registry.py](kernel_gen/passes/registry.py)
    """

    return sorted(_PASS_REGISTRY.keys())


def list_registered_pipelines() -> list[str]:
    """列出当前已注册 pipeline 名称。

    创建者: 睡觉小分队
    最后一次更改: 小李飞刀

    功能说明:
    - 返回当前已注册 pipeline 名称列表。
    - 返回值顺序必须可预测，便于测试断言；按字典序排序。

    使用示例:
    - load_builtin_passes()
    - assert "no-op-pipeline" in list_registered_pipelines()

    关联文件:
    - spec: [spec/pass/registry.md](spec/pass/registry.md)
    - test: [test/pass/test_pass_registry.py](test/pass/test_pass_registry.py)
    - 功能实现: [kernel_gen/passes/registry.py](kernel_gen/passes/registry.py)
    """

    return sorted(_PIPELINE_REGISTRY.keys())


def _reset_registry_for_test() -> None:
    """清空注册表状态，仅用于测试隔离。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 清空 pass / pipeline registry，并重置内置加载标记。
    - 仅用于测试，避免不同测试用例之间的全局状态相互影响。

    使用示例:
    - from kernel_gen.passes import registry
    - registry._reset_registry_for_test()

    关联文件:
    - spec: [spec/pass/registry.md](spec/pass/registry.md)
    - test: [test/pass/test_pass_registry.py](test/pass/test_pass_registry.py)
    - 功能实现: [kernel_gen/passes/registry.py](kernel_gen/passes/registry.py)
    """

    global _BUILTINS_LOADED
    _PASS_REGISTRY.clear()
    _PIPELINE_REGISTRY.clear()
    _BUILTINS_LOADED = False


__all__ = [
    "PassRegistryError",
    "register_pass",
    "register_pipeline",
    "build_registered_pass",
    "build_registered_pipeline",
    "load_builtin_passes",
    "list_registered_passes",
    "list_registered_pipelines",
]
