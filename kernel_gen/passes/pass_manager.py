"""Pass manager API.


功能说明:
- 定义 Pass 与 PassManager 的基础行为。
- 固定 `kernel_gen.passes.pass_manager` 只承载 Pass 抽象与 PassManager，不再承载默认 pipeline builder。
- 当前文件不额外公开 helper；内部状态仅通过 `Pass` / `PassManager` 两个公开入口对外生效。
- `PassManager.run(...)` 通过 `DumpDirWriter.from_config()` 读取诊断产物落盘开关，不改变 pass 执行语义。
- pass 后 dump 第一行使用 xDSL `pipeline_pass_spec(include_default=True)`，稳定包含 pass 公开配置。
- dump IR 正文默认使用 `kernel_gen.core.print.print_operation_with_aliases(...)` 的 alias 文本。
- pass 实例默认 `fold=True`；管理器在每个 pass 后对 `ModuleOp` 执行一次 folding + DCE sweep。

API 列表:
- `class Pass(fold: bool = True)`
- `class PassManager(name: str | None = None)`
- `PassManager.add_pass(self: PassManager, pass_obj: XdslModulePass) -> None`
- `PassManager.extend(self: PassManager, passes: Sequence[XdslModulePass]) -> None`
- `PassManager.run(self: PassManager, target: ModuleOp) -> ModuleOp`

使用示例:
- import importlib
- pass_module = importlib.import_module("kernel_gen.passes.pass_manager")
- Pass, PassManager = pass_module.Pass, pass_module.PassManager
- pm = PassManager(name="opt")
- pm.add_pass(MyPass())
- result = pm.run(module)

关联文件:
- spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
- test: [test/passes/test_pass_manager.py](test/passes/test_pass_manager.py)
- 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
"""

from __future__ import annotations

from collections.abc import Sequence

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.passes import ModulePass as XdslModulePass
from xdsl.pattern_rewriter import GreedyRewritePatternApplier, PatternRewriteWalker

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.core.tools.dump_dir import DumpDirWriter


class Pass(XdslModulePass):
    """Pass 抽象基类。


    功能说明:
    - 提供 pass 通用 fold 开关。
    - 具体 pass 必须直接实现 xdsl `ModulePass.apply(ctx, module)`，不再提供 `run(...)` 兼容入口。

    使用示例:
    - class MyPass(Pass):
          name = "my-pass"
          def apply(self, ctx, module):
              pass

    关联文件:
    - spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
    - test: [test/passes/test_pass_manager.py](test/passes/test_pass_manager.py)
    - 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
    """

    name = "pass"

    def __init__(self: "Pass", fold: bool = True) -> None:
        """初始化 Pass 公共选项。


        功能说明:
        - 记录是否允许 pass 后执行 folding + DCE sweep；默认开启。
        - 该选项不改变具体 pass 的业务重写规则，只控制通用清理 sweep。

        使用示例:
        - pass_obj = MyPass()
        - pass_obj = MyPass(fold=False)

        关联文件:
        - spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
        - test: [test/passes/test_pass_manager.py](test/passes/test_pass_manager.py)
        - 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
        """

        self.fold = bool(fold)


def _load_fold_dialects(ctx: Context) -> None:
    """加载当前仓库 folding 需要的 dialect。


    功能说明:
    - 当前仓库只有 `symbol.*` 实现 `HasFolderInterface`，folding 物化常量时需要 `Symbol` dialect。
    - 该 helper 仅服务本文件内部 fold sweep，不对外作为公开 API 暴露。

    使用示例:
    - _load_fold_dialects(ctx)

    关联文件:
    - spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
    - test: [test/passes/test_pass_manager.py](test/passes/test_pass_manager.py)
    - 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
    """

    from kernel_gen.dialect.symbol import Symbol

    if ctx.get_optional_dialect(Symbol.name) is None:
        ctx.load_dialect(Symbol)


def _fold_module(ctx: Context, module: ModuleOp) -> None:
    """对 module 执行一次 folding + DCE sweep。


    功能说明:
    - 使用空 pattern 列表，启用 `GreedyRewritePatternApplier` 的 folding 与 DCE 分支。
    - DCE 仅删除 xdsl 认定为无副作用且无使用者的 op，不承担 CSE 或业务重写。

    使用示例:
    - _fold_module(ctx, module)

    关联文件:
    - spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
    - test: [test/passes/test_pass_manager.py](test/passes/test_pass_manager.py)
    - 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
    """

    _load_fold_dialects(ctx)
    PatternRewriteWalker(
        GreedyRewritePatternApplier(
            [],
            ctx=ctx,
            folding_enabled=True,
            dce_enabled=True,
        )
    ).rewrite_module(module)


def _pass_fold_enabled(pass_obj: XdslModulePass) -> bool:
    """读取 pass 的 folding + DCE 开关。


    功能说明:
    - 未声明 `fold` 的第三方 `ModulePass` 按默认开启处理。
    - 只有显式 `fold=False` 时关闭 pass 后 folding + DCE sweep。

    使用示例:
    - if _pass_fold_enabled(pass_obj): ...

    关联文件:
    - spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
    - test: [test/passes/test_pass_manager.py](test/passes/test_pass_manager.py)
    - 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
    """

    return getattr(pass_obj, "fold", True) is not False


class PassManager:
    """Pass 管理器。


    功能说明:
    - 按顺序执行 Pass 列表。
    - 只接受 `builtin.module`，并通过每个 pass 的 `apply(ctx, module)` 原地改写。

    使用示例:
    - pm = PassManager(name="opt")
    - pm.add_pass(MyPass())
    - result = pm.run(module)

    关联文件:
    - spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
    - test: [test/passes/test_pass_manager.py](test/passes/test_pass_manager.py)
    - 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
    """

    def __init__(self: "PassManager", name: str | None = None) -> None:
        """初始化 PassManager。


        功能说明:
        - 设置管理器名称并初始化 Pass 列表。

        使用示例:
        - pm = PassManager(name="opt")

        关联文件:
        - spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
        - test: [test/passes/test_pass_manager.py](test/passes/test_pass_manager.py)
        - 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
        """

        self.name = name
        self._passes: list[XdslModulePass] = []

    def add_pass(self: "PassManager", pass_obj: XdslModulePass) -> None:
        """注册单个 Pass。


        功能说明:
        - 追加到 Pass 列表。

        使用示例:
        - pm.add_pass(MyPass())

        关联文件:
        - spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
        - test: [test/passes/test_pass_manager.py](test/passes/test_pass_manager.py)
        - 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
        """
        if not isinstance(pass_obj, XdslModulePass) or not isinstance(getattr(pass_obj, "name", None), str):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "pass_obj must be ModulePass with stable name(str)")
        self._passes.append(pass_obj)

    def extend(self: "PassManager", passes: Sequence[XdslModulePass]) -> None:
        """批量注册 Pass。


        功能说明:
        - 依序追加到 Pass 列表。

        使用示例:
        - pm.extend([PassA(), PassB()])

        关联文件:
        - spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
        - test: [test/passes/test_pass_manager.py](test/passes/test_pass_manager.py)
        - 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
        """
        for item in passes:
            if not isinstance(item, XdslModulePass) or not isinstance(getattr(item, "name", None), str):
                raise KernelCodeError(
                    ErrorKind.CONTRACT,
                    ErrorModule.PASS,
                    "passes must contain ModulePass items with stable name(str)",
                )
            self._passes.append(item)

    def run(self: "PassManager", target: ModuleOp) -> ModuleOp:
        """依序执行 Pass。


        功能说明:
        - 逐个调用 `ModulePass.apply(ctx, module)`。
        - 只接受 `builtin.module`，不再兼容任意对象 passthrough 或单 pass `run(...)`。
        - `kernel_gen.core.config.dump_dir` 非空时写入初始 IR 与每个 pass 后的 IR，便于定位 pipeline 中间态。
        - 每个 pass dump 的第一行使用 xDSL pass spec，并包含默认 option；dump 文件名仍只使用 pass name。

        使用示例:
        - result = pm.run(module)

        关联文件:
        - spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
        - test: [test/passes/test_pass_manager.py](test/passes/test_pass_manager.py)
        - 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
        """
        if not isinstance(target, ModuleOp):
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "PassManager.run target must be builtin.module")
        result = target
        ctx = Context()
        dump_writer = DumpDirWriter.from_config()
        if dump_writer is not None:
            dump_writer.write("01-first-ir.mlir", result)
        for index, item in enumerate(self._passes, start=2):
            try:
                item.apply(ctx, result)
            except KernelCodeError:
                raise
            except Exception as exc:
                pass_name = getattr(item, "name", "pass")
                raise KernelCodeError(
                    ErrorKind.INTERNAL,
                    ErrorModule.PASS,
                    f"PassManager.run pass '{pass_name}' failed: {exc}",
                ) from exc
            if _pass_fold_enabled(item):
                _fold_module(ctx, result)
            if dump_writer is not None:
                pass_name = getattr(item, "name", "pass")
                dump_marker = str(item.pipeline_pass_spec(include_default=True))
                dump_writer.write_stage(index, pass_name, result, marker=dump_marker, fallback="pass")
        return result


__all__ = ["Pass", "PassManager"]
