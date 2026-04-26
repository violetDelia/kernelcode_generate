"""Pass manager API.

创建者: 李白
最后一次更改: 小李飞刀

功能说明:
- 定义 Pass 与 PassManager 的基础行为。
- 固定 `kernel_gen.passes.pass_manager` 只承载 Pass 抽象与 PassManager，不再承载默认 pipeline builder。
- 当前文件不额外公开 helper；内部状态仅通过 `Pass` / `PassManager` 两个公开入口对外生效。

API 列表:
- `class Pass()`
- `Pass.run(self: Pass, target: object) -> object`
- `Pass.apply(self: Pass, ctx: Context, op: ModuleOp) -> None`
- `class PassManager(name: str | None = None)`
- `PassManager.add_pass(self: PassManager, pass_obj: XdslModulePass) -> None`
- `PassManager.extend(self: PassManager, passes: Sequence[XdslModulePass]) -> None`
- `PassManager.run(self: PassManager, target: object) -> object`

使用示例:
- import importlib
- pass_module = importlib.import_module("kernel_gen.passes.pass_manager")
- Pass, PassManager = pass_module.Pass, pass_module.PassManager
- pm = PassManager(name="opt")
- pm.add_pass(MyPass())
- result = pm.run(ir)

关联文件:
- spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
- test: [test/pass/test_pass_manager.py](test/pass/test_pass_manager.py)
- 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
"""

from __future__ import annotations

from collections.abc import Sequence

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.passes import ModulePass as XdslModulePass


class Pass(XdslModulePass):
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

    def apply(self: "Pass", ctx: Context, op: ModuleOp) -> None:
        """满足 xdsl `ModulePass` 接口。

        创建者: 小李飞刀
        最后一次更改: 小李飞刀

        功能说明:
        - `Pass` 的公开主入口固定为 `run(target)`。
        - `apply(ctx, module)` 只负责把 xdsl `ModulePass` 调用桥接到同一公开 `run(...)` 入口。

        使用示例:
        - pass_obj.apply(ctx, module)

        关联文件:
        - spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
        - test: [test/pass/test_pass_manager.py](test/pass/test_pass_manager.py)
        - 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
        """

        _ = ctx
        self.run(op)


class PassManager:
    """Pass 管理器。

    创建者: 李白
    最后一次更改: 小李飞刀

    功能说明:
    - 按顺序执行 Pass 列表。

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
        最后一次更改: 小李飞刀

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
        self._passes: list[XdslModulePass] = []

    def add_pass(self: "PassManager", pass_obj: XdslModulePass) -> None:
        """注册单个 Pass。

        创建者: 李白
        最后一次更改: 李白

        功能说明:
        - 追加到 Pass 列表。

        使用示例:
        - pm.add_pass(MyPass())

        关联文件:
        - spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
        - test: [test/pass/test_pass_manager.py](test/pass/test_pass_manager.py)
        - 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
        """
        if not isinstance(pass_obj, XdslModulePass) or not isinstance(getattr(pass_obj, "name", None), str):
            raise TypeError("pass_obj must be ModulePass with stable name(str)")
        self._passes.append(pass_obj)

    def extend(self: "PassManager", passes: Sequence[XdslModulePass]) -> None:
        """批量注册 Pass。

        创建者: 李白
        最后一次更改: 李白

        功能说明:
        - 依序追加到 Pass 列表。

        使用示例:
        - pm.extend([PassA(), PassB()])

        关联文件:
        - spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
        - test: [test/pass/test_pass_manager.py](test/pass/test_pass_manager.py)
        - 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
        """
        for item in passes:
            if not isinstance(item, XdslModulePass) or not isinstance(getattr(item, "name", None), str):
                raise TypeError("passes must contain ModulePass items with stable name(str)")
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
        - spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
        - test: [test/pass/test_pass_manager.py](test/pass/test_pass_manager.py)
        - 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
        """
        result = target
        ctx = Context()
        for item in self._passes:
            if isinstance(item, Pass):
                result = item.run(result)
            else:
                item.apply(ctx, result)  # type: ignore[arg-type]
        return result


__all__ = ["Pass", "PassManager"]
