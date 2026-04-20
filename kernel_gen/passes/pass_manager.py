"""Pass manager API.

创建者: 李白
最后一次更改: 朽木露琪亚

功能说明:
- 定义 Pass / ModulePass 与 PassManager 的基础行为。
- 提供 `build_default_lowering_pass_manager` 兼容入口，内部委派到 pipeline builder。

使用示例:
- import importlib
- pass_module = importlib.import_module("kernel_gen.passes.pass_manager")
- Pass, PassManager = pass_module.Pass, pass_module.PassManager
- pm = PassManager(name="opt")
- pm.add_pass(MyPass())
- result = pm.run(ir)
- pm = build_default_lowering_pass_manager()

关联文件:
- spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
- test: [test/pass/test_pass_manager.py](test/pass/test_pass_manager.py)
- 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
"""

from __future__ import annotations

from collections.abc import Sequence

from xdsl.context import Context
from xdsl.passes import ModulePass


class Pass:
    """Pass 抽象基类。

    创建者: 李白
    最后一次更改: 李白

    功能说明:
    - 提供最小的 Pass 接口规范。

    使用示例:
    - class MyPass(Pass):
          name = "my-pass"
          def run(self, target):
              return target

    关联文件:
    - spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
    - test: [test/pass/test_pass_manager.py](test/pass/test_pass_manager.py)
    - 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
    """

    name = "pass"

    def run(self: "Pass", target: object) -> object:  # pragma: no cover - abstract hook
        """执行 Pass。

        创建者: 李白
        最后一次更改: 李白

        功能说明:
        - 处理输入并返回输出。

        使用示例:
        - return target

        关联文件:
        - spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
        - test: [test/pass/test_pass_manager.py](test/pass/test_pass_manager.py)
        - 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
        """
        raise NotImplementedError("Pass.run must be implemented")


def _is_pass_like(obj: object) -> bool:
    """判断对象是否满足 Pass / ModulePass 最小协议。

    创建者: 小李飞刀
    最后一次更改: 朽木露琪亚

    功能说明:
    - Legacy `Pass` 必须包含 `run` 可调用属性。
    - xdsl `ModulePass` 必须包含 `apply` 可调用属性。
    - 必须包含字符串类型的 `name` 属性。

    使用示例:
    - if _is_pass_like(pass_obj): pm.add_pass(pass_obj)

    关联文件:
    - spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
    - test: [test/pass/test_pass_manager.py](test/pass/test_pass_manager.py)
    - 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
    """

    if not hasattr(obj, "name"):
        return False
    if isinstance(obj, ModulePass):
        return callable(getattr(obj, "apply", None)) and isinstance(getattr(obj, "name"), str)
    if isinstance(obj, Pass):
        return callable(getattr(obj, "run", None)) and isinstance(getattr(obj, "name"), str)
    return False



class PassManager:
    """Pass 管理器。

    创建者: 李白
    最后一次更改: 朽木露琪亚

    功能说明:
    - 按顺序执行 Pass 列表。
    - 迁移期同时兼容 legacy `Pass.run(target)` 与 xdsl `ModulePass.apply(ctx, module)`。

    使用示例:
    - pm = PassManager(name="opt")
    - pm.add_pass(MyPass())
    - result = pm.run(ir)

    关联文件:
    - spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
    - test: [test/pass/test_pass_manager.py](test/pass/test_pass_manager.py)
    - 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
    """

    def __init__(self: "PassManager", name: str | None = None) -> None:
        """初始化 PassManager。

        创建者: 小李飞刀
        最后一次更改: 朽木露琪亚

        功能说明:
        - 设置管理器名称并初始化 Pass 列表。

        使用示例:
        - pm = PassManager(name="opt")

        关联文件:
        - spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
        - test: [test/pass/test_pass_manager.py](test/pass/test_pass_manager.py)
        - 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
        """

        self.name = name
        self._passes: list[Pass | ModulePass] = []

    def add_pass(self: "PassManager", pass_obj: Pass | ModulePass) -> None:
        """注册单个 Pass。

        创建者: 李白
        最后一次更改: 朽木露琪亚

        功能说明:
        - 追加到 Pass 列表，兼容 legacy `Pass` 与 xdsl `ModulePass`。

        使用示例:
        - pm.add_pass(MyPass())

        关联文件:
        - spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
        - test: [test/pass/test_pass_manager.py](test/pass/test_pass_manager.py)
        - 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
        """
        if not _is_pass_like(pass_obj):
            raise TypeError("pass_obj must provide name(str) and run(target)")
        self._passes.append(pass_obj)

    def extend(self: "PassManager", passes: Sequence[Pass | ModulePass]) -> None:
        """批量注册 Pass。

        创建者: 李白
        最后一次更改: 朽木露琪亚

        功能说明:
        - 依序追加到 Pass 列表，兼容 legacy `Pass` 与 xdsl `ModulePass`。

        使用示例:
        - pm.extend([PassA(), PassB()])

        关联文件:
        - spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
        - test: [test/pass/test_pass_manager.py](test/pass/test_pass_manager.py)
        - 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
        """
        for item in passes:
            if not _is_pass_like(item):
                raise TypeError("passes must contain Pass items")
            self._passes.append(item)

    def run(self: "PassManager", target: object) -> object:
        """依序执行 Pass。

        创建者: 李白
        最后一次更改: 朽木露琪亚

        功能说明:
        - 逐个调用 `Pass.run` 或 `ModulePass.apply(ctx, module)`。

        使用示例:
        - result = pm.run(ir)

        关联文件:
        - spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
        - test: [test/pass/test_pass_manager.py](test/pass/test_pass_manager.py)
        - 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
        """
        pass_names = [item.name for item in self._passes]
        if "symbol-loop-hoist" in pass_names:
            hoist_index = pass_names.index("symbol-loop-hoist")
            if "tile" not in pass_names:
                raise ValueError(
                    "SymbolLoopHoistRequiresSymbolFor: symbol-loop-hoist requires tile to materialize symbol.for"
                )
            tile_index = pass_names.index("tile")
            if hoist_index < tile_index:
                raise ValueError(
                    "SymbolLoopHoistRequiresSymbolFor: symbol-loop-hoist must run after tile"
                )
            if "lower-dma-memory-hierarchy" in pass_names:
                dma_index = pass_names.index("lower-dma-memory-hierarchy")
                if hoist_index > dma_index:
                    raise ValueError(
                        "SymbolLoopHoistRequiresSymbolFor: symbol-loop-hoist must run before lower-dma-memory-hierarchy"
                    )
        if "lower-dma-memory-hierarchy" in pass_names:
            dma_index = pass_names.index("lower-dma-memory-hierarchy")
            if "buffer-results-to-out-params" not in pass_names:
                raise ValueError(
                    "DmaMemoryHierarchyOrderError: lower-dma-memory-hierarchy requires buffer-results-to-out-params"
                )
            buffer_index = pass_names.index("buffer-results-to-out-params")
            if dma_index < buffer_index:
                raise ValueError(
                    "DmaMemoryHierarchyOrderError: lower-dma-memory-hierarchy must run after buffer-results-to-out-params"
                )
        if "tile" in pass_names:
            tile_index = pass_names.index("tile")
            if "buffer-results-to-out-params" in pass_names:
                buffer_index = pass_names.index("buffer-results-to-out-params")
                if tile_index < buffer_index:
                    raise ValueError(
                        "TilePassOrderError: tile must run after buffer-results-to-out-params"
                    )
            if "lower-dma-memory-hierarchy" in pass_names:
                dma_hierarchy_index = pass_names.index("lower-dma-memory-hierarchy")
                if tile_index > dma_hierarchy_index:
                    raise ValueError(
                        "TilePassOrderError: tile must run before lower-dma-memory-hierarchy"
                    )

        result = target
        seen_set: set[str] = set()
        ctx: Context | None = None
        lowering_names = {"lower-nn", "lower-nn-to-kernel"}
        for item in self._passes:
            if item.name == "buffer-results-to-out-params" and lowering_names.isdisjoint(seen_set):
                raise ValueError(
                    "buffer-results-to-out-params requires lowered IR after lower-nn or lower-nn-to-kernel"
                )
            if isinstance(item, ModulePass):
                if ctx is None:
                    ctx = Context()
                item.apply(ctx, result)
            else:
                result = item.run(result)
            seen_set.add(item.name)
        return result


def build_default_lowering_pass_manager() -> "PassManager":
    """兼容入口：构造默认 lowering PassManager。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 兼容旧入口 `build_default_lowering_pass_manager()`。
    - 实际委派给 `kernel_gen.passes.pipeline.build_default_lowering_pipeline()`。

    使用示例:
    - pm = build_default_lowering_pass_manager()
    - lowered = pm.run(module)

    关联文件:
    - spec: [spec/pass/pipeline/default_lowering.md](spec/pass/pipeline/default_lowering.md)
    - test: [test/pass/test_pipeline_default_lowering.py](test/pass/test_pipeline_default_lowering.py)
    - 功能实现: [kernel_gen/passes/pipeline/default_lowering.py](kernel_gen/passes/pipeline/default_lowering.py)
    """

    from kernel_gen.passes.pipeline import build_default_lowering_pipeline

    return build_default_lowering_pipeline()


__all__ = ["Pass", "PassManager", "build_default_lowering_pass_manager"]
