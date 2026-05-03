"""Pass registry API.


功能说明:
- 提供 pass / pipeline 的进程内注册表，统一“名字 -> 构造器”的解析入口。
- 为工具层（如 ircheck）提供稳定名称解析能力，避免依赖具体 Python import path。
- 文件内 helper 收口为 `_register_registry_entry`、`_build_registered_pass_instance`、
  `_build_registered_pipeline_manager`、`_pipeline_accepts_options`、`_normalize_options`、
  `_split_fold_option` 与 `_reset_registry_for_test`；这些 helper 仅供本文件内部复用，不属于公开接口。

API 列表:
- `register_pass(pass_cls: type[PassType]) -> type[PassType]`
- `register_pipeline(name: str) -> Callable[[Callable[..., PassManager]], Callable[..., PassManager]]`
- `build_registered_pass(name: str, options: dict[str, str] | None = None) -> XdslModulePass`
- `build_registered_pipeline(name: str, options: dict[str, str] | None = None) -> PassManager`
- `load_builtin_passes() -> None`
- `list_registered_passes() -> list[str]`
- `list_registered_pipelines() -> list[str]`

使用示例:
- from kernel_gen.passes.registry import load_builtin_passes, build_registered_pass
- load_builtin_passes()
- pass_obj = build_registered_pass("no-op")

关联文件:
- spec: [spec/pass/registry.md](spec/pass/registry.md)
- test: [test/passes/test_registry.py](test/passes/test_registry.py)
- 功能实现: [kernel_gen/passes/registry.py](kernel_gen/passes/registry.py)
"""

from __future__ import annotations
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError

from collections.abc import Callable
import inspect
from typing import TypeVar

from .pass_manager import Pass, PassManager
from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.passes import ModulePass as XdslModulePass

PassType = TypeVar("PassType", bound=XdslModulePass)
RegistryEntryType = TypeVar("RegistryEntryType")

_PASS_REGISTRY: dict[str, type[XdslModulePass]] = {}
_PIPELINE_REGISTRY: dict[str, Callable[..., PassManager]] = {}
_BUILTINS_LOADED = False


class _NoOpPass(Pass):
    """内置 no-op pass。


    功能说明:
    - 作为 pass registry smoke test 与 no-op pipeline 的最小 pass。

    使用示例:
    - _NoOpPass().apply(Context(), module)

    关联文件:
    - spec: spec/pass/registry.md
    - test: test/passes/test_registry.py
    - 功能实现: kernel_gen/passes/registry.py
    """

    name = "no-op"

    def apply(self: "_NoOpPass", ctx: Context, module: ModuleOp) -> None:
        _ = ctx
        _ = module


def _build_no_op_pipeline() -> PassManager:
    """构造内置 no-op pipeline。


    功能说明:
    - 保持 registry 内置 pipeline 构造逻辑在当前文件顶层 helper 中。

    使用示例:
    - pm = _build_no_op_pipeline()

    关联文件:
    - spec: spec/pass/registry.md
    - test: test/passes/test_registry.py
    - 功能实现: kernel_gen/passes/registry.py
    """

    pm = PassManager(name="no-op-pipeline")
    pm.add_pass(_NoOpPass())
    return pm


def _set_pass_fold_option(pass_obj: XdslModulePass, fold: bool) -> None:
    """设置 pass 实例的通用 fold 开关。


    功能说明:
    - 统一处理 `ModulePass` 的属性写入。
    - 仅供 registry 在解析通用 `fold` 选项后设置实例状态。

    使用示例:
    - _set_pass_fold_option(pass_obj, False)

    关联文件:
    - spec: [spec/pass/registry.md](spec/pass/registry.md)
    - test: [test/passes/test_registry.py](test/passes/test_registry.py)
    - 功能实现: [kernel_gen/passes/registry.py](kernel_gen/passes/registry.py)
    """

    pass_obj.fold = bool(fold)


def _parse_bool_option(name: str, value: str) -> bool:
    """解析 registry bool 选项。


    功能说明:
    - 接受常见 true/false 文本。
    - 非法文本按 pass option error 处理，保持 registry 错误归属稳定。

    使用示例:
    - enabled = _parse_bool_option("fold", "false")

    关联文件:
    - spec: [spec/pass/registry.md](spec/pass/registry.md)
    - test: [test/passes/test_registry.py](test/passes/test_registry.py)
    - 功能实现: [kernel_gen/passes/registry.py](kernel_gen/passes/registry.py)
    """

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"PassRegistryError: option '{name}' expects bool")


def _split_fold_option(options: dict[str, str]) -> tuple[dict[str, str], bool | None]:
    """从 pass options 中拆出通用 `fold` 选项。


    功能说明:
    - `fold` 是所有 pass 的通用 registry 选项，默认由 pass 构造器自身决定。
    - 剩余 options 继续交给 pass 自有 `from_options` 处理。

    使用示例:
    - pass_options, fold = _split_fold_option({"fold": "false"})

    关联文件:
    - spec: [spec/pass/registry.md](spec/pass/registry.md)
    - test: [test/passes/test_registry.py](test/passes/test_registry.py)
    - 功能实现: [kernel_gen/passes/registry.py](kernel_gen/passes/registry.py)
    """

    pass_options = dict(options)
    if "fold" not in pass_options:
        return pass_options, None
    return pass_options, _parse_bool_option("fold", pass_options.pop("fold"))




def _register_registry_entry(
    registry: dict[str, RegistryEntryType], name: str, value: RegistryEntryType, kind: str
) -> None:
    """把单个注册项写入 registry 并保留重复名失败语义。


    功能说明:
    - 统一 pass / pipeline 的同名重复注册检查。
    - 失败时保留稳定错误短语，供 pytest 与 expectation 机械匹配。

    使用示例:
    - _register_registry_entry(_PASS_REGISTRY, "no-op", NoOpPass, "pass")

    关联文件:
    - spec: [spec/pass/registry.md](spec/pass/registry.md)
    - test: [test/passes/test_registry.py](test/passes/test_registry.py)
    - 功能实现: [kernel_gen/passes/registry.py](kernel_gen/passes/registry.py)
    """

    if name in registry:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"PassRegistryError: {kind} '{name}' is already registered")
    registry[name] = value


def _build_registered_pass_instance(
    name: str,
    pass_cls: type[XdslModulePass],
    options: dict[str, str],
    passthrough_errors: tuple[type[BaseException], ...] = (),
) -> XdslModulePass:
    """根据注册的 pass 类构造实例，并统一错误转换。


    功能说明:
    - 将 pass 无参构造与 `from_options(options)` 两条入口的错误转换收口到单一 helper。
    - `passthrough_errors` 用于保留特定 pass 的原生异常，不被 registry 吞掉。

    使用示例:
    - _build_registered_pass_instance("no-op", NoOpPass, {})

    关联文件:
    - spec: [spec/pass/registry.md](spec/pass/registry.md)
    - test: [test/passes/test_registry.py](test/passes/test_registry.py)
    - 功能实现: [kernel_gen/passes/registry.py](kernel_gen/passes/registry.py)
    """

    pass_options, fold = _split_fold_option(options)
    if pass_options:
        from_options = getattr(pass_cls, "from_options", None)
        if not callable(from_options):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"PassRegistryError: pass '{name}' does not accept options")
        try:
            pass_obj = from_options(pass_options)
        except Exception as exc:  # pragma: no cover - exception detail not stable
            if passthrough_errors and isinstance(exc, passthrough_errors):
                raise
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"PassRegistryError: pass '{name}' option error") from exc
        if not isinstance(pass_obj, XdslModulePass):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"PassRegistryError: pass '{name}' option error")
        if fold is not None:
            _set_pass_fold_option(pass_obj, fold)
        return pass_obj
    try:
        if fold is None:
            return pass_cls()
        try:
            pass_obj = pass_cls(fold=fold)  # type: ignore[call-arg]
        except TypeError:
            pass_obj = pass_cls()
            _set_pass_fold_option(pass_obj, fold)
        return pass_obj
    except Exception as exc:  # pragma: no cover - exception detail not stable
        if passthrough_errors and isinstance(exc, passthrough_errors):
            raise
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"PassRegistryError: pass '{name}' is not constructible") from exc


def _build_registered_pipeline_manager(
    name: str, builder: Callable[..., PassManager], options: dict[str, str]
) -> PassManager:
    """根据注册的 pipeline builder 构造 PassManager，并统一错误转换。


    功能说明:
    - 将 pipeline 无参构造、options 传参与返回值校验收口到单一 helper。
    - 保留 registry 层稳定错误短语，不改变公开 pipeline 入口兼容边界。

    使用示例:
    - pm = _build_registered_pipeline_manager("default-lowering", build_default_lowering_pipeline, {})

    关联文件:
    - spec: [spec/pass/registry.md](spec/pass/registry.md)
    - test: [test/passes/test_registry.py](test/passes/test_registry.py)
    - 功能实现: [kernel_gen/passes/registry.py](kernel_gen/passes/registry.py)
    """

    if options:
        if not _pipeline_accepts_options(builder):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"PassRegistryError: pipeline '{name}' does not accept options")
        try:
            pm = builder(options)
        except Exception as exc:  # pragma: no cover - builder error path not deterministic
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"PassRegistryError: pipeline '{name}' option error") from exc
    else:
        try:
            pm = builder()
        except Exception as exc:  # pragma: no cover - builder error path not deterministic
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, 
                f"PassRegistryError: pipeline '{name}' did not return PassManager"
            ) from exc
    if not isinstance(pm, PassManager):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"PassRegistryError: pipeline '{name}' did not return PassManager")
    return pm


def register_pass(pass_cls: type[PassType]) -> type[PassType]:
    """注册公开 pass 类。


    功能说明:
    - 装饰器：注册一个公开 pass 类（`ModulePass` 子类），使用 `pass_cls.name` 作为 key。
    - 同一名字在进程内必须唯一；重复注册立即失败。

    使用示例:
    - @register_pass
      class TileReducePass(Pass):
          name = "tile-reduce"
          def apply(self, ctx, module): pass

    关联文件:
    - spec: [spec/pass/registry.md](spec/pass/registry.md)
    - test: [test/passes/test_registry.py](test/passes/test_registry.py)
    - 功能实现: [kernel_gen/passes/registry.py](kernel_gen/passes/registry.py)
    """

    if not isinstance(pass_cls, type) or not issubclass(pass_cls, XdslModulePass):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "PassRegistryError: register_pass expects ModulePass subclass")
    pass_name = getattr(pass_cls, "name", None)
    if not isinstance(pass_name, str) or not pass_name.strip():
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "PassRegistryError: pass name must be non-empty string")
    _register_registry_entry(_PASS_REGISTRY, pass_name, pass_cls, "pass")
    return pass_cls


def register_pipeline(name: str) -> Callable[[Callable[..., PassManager]], Callable[..., PassManager]]:
    """注册公开 pipeline builder。


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
    - test: [test/passes/test_registry.py](test/passes/test_registry.py)
    - 功能实现: [kernel_gen/passes/registry.py](kernel_gen/passes/registry.py)
    """

    if not isinstance(name, str) or not name.strip():
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "PassRegistryError: pipeline name must be non-empty string")
    if name in _PIPELINE_REGISTRY:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"PassRegistryError: pipeline '{name}' is already registered")

    def _decorator(builder: Callable[..., PassManager]) -> Callable[..., PassManager]:
        if not callable(builder):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "PassRegistryError: register_pipeline expects callable builder")
        _register_registry_entry(_PIPELINE_REGISTRY, name, builder, "pipeline")
        return builder

    return _decorator


def _normalize_options(options: dict[str, str] | None) -> dict[str, str]:
    """规整 build_registered_* 的 options 参数。


    功能说明:
    - 将 None 规整为空字典。
    - 复制输入，避免调用方侧的可变状态影响后续处理。

    使用示例:
    - opts = _normalize_options(None)
    - opts = _normalize_options({"mode": "fast"})

    关联文件:
    - spec: [spec/pass/registry.md](spec/pass/registry.md)
    - test: [test/passes/test_registry.py](test/passes/test_registry.py)
    - 功能实现: [kernel_gen/passes/registry.py](kernel_gen/passes/registry.py)
    """

    if options is None:
        return {}
    return dict(options)


def _pipeline_accepts_options(builder: Callable[..., PassManager]) -> bool:
    """判断 pipeline builder 是否接收 options 参数。


    功能说明:
    - 基于函数签名判断是否支持单个 options 参数。
    - 若含 *args/**kwargs 则视为支持。

    使用示例:
    - if _pipeline_accepts_options(builder): ...

    关联文件:
    - spec: [spec/pass/registry.md](spec/pass/registry.md)
    - test: [test/passes/test_registry.py](test/passes/test_registry.py)
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


def build_registered_pass(name: str, options: dict[str, str] | None = None) -> XdslModulePass:
    """根据名称构造 pass 实例。


    功能说明:
    - 根据 pass name 构造并返回 pass 实例。
    - 若提供 options，则要求 pass_cls 提供 `from_options(options)` 构造入口。
    - options 为空时沿用“无参构造”规则；不可构造时报稳定错误短语。

    使用示例:
    - load_builtin_passes()
    - pass_obj = build_registered_pass("tile-analysis")
    - pass_obj = build_registered_pass("tile-reduce")

    关联文件:
    - spec: [spec/pass/registry.md](spec/pass/registry.md)
    - test: [test/passes/test_registry.py](test/passes/test_registry.py)
    - 功能实现: [kernel_gen/passes/registry.py](kernel_gen/passes/registry.py)
    """

    if name not in _PASS_REGISTRY:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"PassRegistryError: unknown pass '{name}'")
    pass_cls = _PASS_REGISTRY[name]
    normalized_options = _normalize_options(options)
    passthrough_errors: tuple[type[BaseException], ...] = ()
    if name == "launch-kernel-cost-func":
        passthrough_errors = (KernelCodeError,)
    return _build_registered_pass_instance(
        name,
        pass_cls,
        normalized_options,
        passthrough_errors=passthrough_errors,
    )


def build_registered_pipeline(name: str, options: dict[str, str] | None = None) -> PassManager:
    """根据名称构造 pipeline 对应的 PassManager。


    功能说明:
    - 根据 pipeline name 调用 builder 构造并返回 `PassManager`。
    - 若提供 options，则要求 builder 接受 `options` 参数。
    - builder 返回值必须为 `PassManager`；否则报告稳定错误短语。

    使用示例:
    - load_builtin_passes()
    - pm = build_registered_pipeline("no-op-pipeline")
    - pm = build_registered_pipeline("npu-demo-lowering")
    - pm = build_registered_pipeline("default-lowering", {"analysis-only": "true"})
    - lowered = pm.run(module)

    关联文件:
    - spec: [spec/pass/registry.md](spec/pass/registry.md)
    - test: [test/passes/test_registry.py](test/passes/test_registry.py)
    - 功能实现: [kernel_gen/passes/registry.py](kernel_gen/passes/registry.py)
    """

    if name not in _PIPELINE_REGISTRY:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"PassRegistryError: unknown pipeline '{name}'")
    builder = _PIPELINE_REGISTRY[name]
    normalized_options = _normalize_options(options)
    return _build_registered_pipeline_manager(name, builder, normalized_options)


def load_builtin_passes() -> None:
    """加载仓库内置 pass / pipeline。


    功能说明:
    - 主动加载仓库内置 pass / pipeline，使装饰器注册与显式注册生效。
    - 满足幂等性：重复调用不会重复注册或造成副作用。
    - 当前内置 pipeline 包含 `default-lowering` 与 `npu-demo-lowering`。

    使用示例:
    - load_builtin_passes()
    - names = list_registered_passes()

    关联文件:
    - spec: [spec/pass/registry.md](spec/pass/registry.md)
    - test: [test/passes/test_registry.py](test/passes/test_registry.py)
    - 功能实现: [kernel_gen/passes/registry.py](kernel_gen/passes/registry.py)
    """

    global _BUILTINS_LOADED
    if _BUILTINS_LOADED:
        return

    if _NoOpPass.name not in _PASS_REGISTRY:
        register_pass(_NoOpPass)
    if "no-op-pipeline" not in _PIPELINE_REGISTRY:
        register_pipeline("no-op-pipeline")(_build_no_op_pipeline)

    from kernel_gen.passes.buffer_results_to_out_params import BufferResultsToOutParamsPass
    from kernel_gen.passes.attach_arch_information import AttachArchInformationPass
    from kernel_gen.passes.decompass import DecompassPass
    from kernel_gen.passes.inline import InlinePass
    from kernel_gen.passes.dma_memory_hierarchy import LowerDmaMemoryHierarchyPass
    from kernel_gen.passes.memory_pool import MemoryPoolPass
    from kernel_gen.passes.lowering.nn_lowering import NnLoweringPass
    from kernel_gen.passes.outline_device_kernel import OutlineDeviceKernelPass
    from kernel_gen.passes.symbol_buffer_hoist import SymbolBufferHoistPass
    from kernel_gen.passes.symbol_loop_hoist import SymbolLoopHoistPass
    from kernel_gen.passes.tile.analysis import TileAnalysisPass
    from kernel_gen.passes.tile.elewise import TileElewisePass
    from kernel_gen.passes.tile.reduce import TileReducePass
    from kernel_gen.passes.tuning import LaunchKernelCostFuncPass

    for pass_cls in (
        InlinePass,
        DecompassPass,
        NnLoweringPass,
        BufferResultsToOutParamsPass,
        LowerDmaMemoryHierarchyPass,
        OutlineDeviceKernelPass,
        SymbolBufferHoistPass,
        AttachArchInformationPass,
        TileAnalysisPass,
        TileElewisePass,
        TileReducePass,
        SymbolLoopHoistPass,
        MemoryPoolPass,
        LaunchKernelCostFuncPass,
    ):
        pass_name = getattr(pass_cls, "name", None)
        if isinstance(pass_name, str) and pass_name in _PASS_REGISTRY:
            continue
        register_pass(pass_cls)

    from kernel_gen.passes.pipeline import (
        build_default_lowering_pipeline,
        build_npu_demo_lowering_pipeline,
    )

    if "default-lowering" not in _PIPELINE_REGISTRY:
        register_pipeline("default-lowering")(build_default_lowering_pipeline)
    if "npu-demo-lowering" not in _PIPELINE_REGISTRY:
        register_pipeline("npu-demo-lowering")(build_npu_demo_lowering_pipeline)

    _BUILTINS_LOADED = True


def list_registered_passes() -> list[str]:
    """列出当前已注册 pass 名称。


    功能说明:
    - 返回当前已注册 pass 名称列表。
    - 返回值顺序必须可预测，便于测试断言；按字典序排序。

    使用示例:
    - load_builtin_passes()
    - assert "no-op" in list_registered_passes()

    关联文件:
    - spec: [spec/pass/registry.md](spec/pass/registry.md)
    - test: [test/passes/test_registry.py](test/passes/test_registry.py)
    - 功能实现: [kernel_gen/passes/registry.py](kernel_gen/passes/registry.py)
    """

    return sorted(_PASS_REGISTRY.keys())


def list_registered_pipelines() -> list[str]:
    """列出当前已注册 pipeline 名称。


    功能说明:
    - 返回当前已注册 pipeline 名称列表。
    - 返回值顺序必须可预测，便于测试断言；按字典序排序。

    使用示例:
    - load_builtin_passes()
    - assert "no-op-pipeline" in list_registered_pipelines()

    关联文件:
    - spec: [spec/pass/registry.md](spec/pass/registry.md)
    - test: [test/passes/test_registry.py](test/passes/test_registry.py)
    - 功能实现: [kernel_gen/passes/registry.py](kernel_gen/passes/registry.py)
    """

    return sorted(_PIPELINE_REGISTRY.keys())


def _reset_registry_for_test() -> None:
    """清空注册表状态，仅用于测试隔离。


    功能说明:
    - 清空 pass / pipeline registry，并重置内置加载标记。
    - 仅用于测试，避免不同测试用例之间的全局状态相互影响。

    使用示例:
    - from kernel_gen.passes import registry
    - registry._reset_registry_for_test()

    关联文件:
    - spec: [spec/pass/registry.md](spec/pass/registry.md)
    - test: [test/passes/test_registry.py](test/passes/test_registry.py)
    - 功能实现: [kernel_gen/passes/registry.py](kernel_gen/passes/registry.py)
    """

    global _BUILTINS_LOADED
    _PASS_REGISTRY.clear()
    _PIPELINE_REGISTRY.clear()
    _BUILTINS_LOADED = False


__all__ = [
    "register_pass",
    "register_pipeline",
    "build_registered_pass",
    "build_registered_pipeline",
    "load_builtin_passes",
    "list_registered_passes",
    "list_registered_pipelines",
]
