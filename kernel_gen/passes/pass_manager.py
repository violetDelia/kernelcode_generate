"""Pass manager API.

创建者: 李白
最后一次更改: 朽木露琪亚

功能说明:
- 定义 Pass 与 PassManager 的基础行为。
- 为 lowering 场景提供推荐的 pass 链路构造入口。

使用示例:
- import importlib
- pass_module = importlib.import_module("kernel_gen.passes.pass_manager")
- Pass, PassManager = pass_module.Pass, pass_module.PassManager
- pm = PassManager(name="opt")
- pm.add_pass(MyPass())
- result = pm.run(ir)
- lowering_pm = build_default_lowering_pass_manager()
- lowered = lowering_pm.run(module)

关联文件:
- spec: spec/pass/pass_manager.md
- test: test/pass/test_pass_manager.py
- 功能实现: kernel_gen/passes/pass_manager.py
"""

from __future__ import annotations

from collections.abc import Sequence


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
    - spec: spec/pass/pass_manager.md
    - test: test/pass/test_pass_manager.py
    - 功能实现: kernel_gen/passes/pass_manager.py
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
        - spec: spec/pass/pass_manager.md
        - test: test/pass/test_pass_manager.py
        - 功能实现: kernel_gen/passes/pass_manager.py
        """
        raise NotImplementedError("Pass.run must be implemented")


def _is_pass_like(obj: object) -> bool:
    if not hasattr(obj, "run") or not callable(getattr(obj, "run")):
        return False
    if not hasattr(obj, "name"):
        return False
    return isinstance(getattr(obj, "name"), str)


def build_default_lowering_pass_manager(name: str | None = "lowering") -> "PassManager":
    """构造默认 lowering pass 链路。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 固定注册 `LowerNnToKernelPass -> BufferResultsToOutParamsPass` 顺序。
    - 为推荐调用链与黑盒测试提供统一入口，避免各处手工拼装顺序漂移。

    使用示例:
    - pm = build_default_lowering_pass_manager()
    - module = pm.run(module)

    关联文件:
    - spec: spec/pass/pass_manager.md
    - test: test/pass/test_pass_manager.py
    - 功能实现: kernel_gen/passes/pass_manager.py
    """

    from .lowering import BufferResultsToOutParamsPass, LowerNnToKernelPass

    pm = PassManager(name=name)
    pm.add_pass(LowerNnToKernelPass())
    pm.add_pass(BufferResultsToOutParamsPass())
    return pm


class PassManager:
    """Pass 管理器。

    创建者: 李白
    最后一次更改: 朽木露琪亚

    功能说明:
    - 按顺序执行 Pass 列表。

    使用示例:
    - pm = PassManager(name="opt")
    - pm.add_pass(MyPass())
    - result = pm.run(ir)

    关联文件:
    - spec: spec/pass/pass_manager.md
    - test: test/pass/test_pass_manager.py
    - 功能实现: kernel_gen/passes/pass_manager.py
    """

    def __init__(self: "PassManager", name: str | None = None) -> None:
        self.name = name
        self._passes: list[Pass] = []

    def add_pass(self: "PassManager", pass_obj: Pass) -> None:
        """注册单个 Pass。

        创建者: 李白
        最后一次更改: 李白

        功能说明:
        - 追加到 Pass 列表。

        使用示例:
        - pm.add_pass(MyPass())

        关联文件:
        - spec: spec/pass/pass_manager.md
        - test: test/pass/test_pass_manager.py
        - 功能实现: kernel_gen/passes/pass_manager.py
        """
        if not _is_pass_like(pass_obj):
            raise TypeError("pass_obj must provide name(str) and run(target)")
        self._passes.append(pass_obj)

    def extend(self: "PassManager", passes: Sequence[Pass]) -> None:
        """批量注册 Pass。

        创建者: 李白
        最后一次更改: 李白

        功能说明:
        - 依序追加到 Pass 列表。

        使用示例:
        - pm.extend([PassA(), PassB()])

        关联文件:
        - spec: spec/pass/pass_manager.md
        - test: test/pass/test_pass_manager.py
        - 功能实现: kernel_gen/passes/pass_manager.py
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
        - 逐个调用 Pass.run。

        使用示例:
        - result = pm.run(ir)

        关联文件:
        - spec: spec/pass/pass_manager.md
        - test: test/pass/test_pass_manager.py
        - 功能实现: kernel_gen/passes/pass_manager.py
        """
        pass_names = [item.name for item in self._passes]
        if "kernel-split" in pass_names:
            kernel_split_index = pass_names.index("kernel-split")
            if "buffer-results-to-out-params" in pass_names:
                buffer_index = pass_names.index("buffer-results-to-out-params")
                if kernel_split_index < buffer_index:
                    raise ValueError(
                        "KernelSplitOrderError: kernel-split must run after buffer-results-to-out-params"
                    )
            if "lower-dma-memory-hierarchy" in pass_names:
                dma_hierarchy_index = pass_names.index("lower-dma-memory-hierarchy")
                if kernel_split_index > dma_hierarchy_index:
                    raise ValueError(
                        "KernelSplitOrderError: kernel-split must run before lower-dma-memory-hierarchy"
                    )

        result = target
        seen_names: list[str] = []
        for item in self._passes:
            if item.name == "buffer-results-to-out-params" and "lower-nn-to-kernel" not in seen_names:
                raise ValueError(
                    "buffer-results-to-out-params requires lowered IR after lower-nn-to-kernel"
                )
            result = item.run(result)
            seen_names.append(item.name)
        return result


__all__ = ["Pass", "PassManager", "build_default_lowering_pass_manager"]
