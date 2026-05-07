"""Pass manager API.


功能说明:
- 定义 Pass 与 PassManager 的基础行为。
- 固定 `kernel_gen.passes.pass_manager` 只承载 Pass 抽象与 PassManager，不再承载默认 pipeline builder。
- 当前文件不额外公开 helper；内部状态仅通过 `Pass` / `PassManager` 两个公开入口对外生效。
- `PassManager.run(...)` 从 `kernel_gen.core.config.get_dump_dir()` 读取诊断产物落盘开关，不改变 pass 执行语义。
- dump IR 默认使用 `kernel_gen.core.print.print_operation_with_aliases(...)` 的 alias 文本。
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
from pathlib import Path
import re

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import Operation
from xdsl.passes import ModulePass as XdslModulePass
from xdsl.pattern_rewriter import GreedyRewritePatternApplier, PatternRewriteWalker

from kernel_gen.core.config import get_dump_dir
from kernel_gen.core.print import print_operation_with_aliases


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


def _sanitize_dump_name(value: str) -> str:
    """把 pass 名称规整为安全文件名片段。


    功能说明:
    - 保留字母、数字、点、下划线与短横线。
    - 其他字符统一替换为 `_`，避免 dump 文件名依赖 shell 或文件系统特殊字符。

    使用示例:
    - _sanitize_dump_name("tile-elewise")

    关联文件:
    - spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
    - test: [test/passes/test_pass_manager.py](test/passes/test_pass_manager.py)
    - 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
    """
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return safe_name or "pass"


def _write_dump_file(path: Path, content: str) -> None:
    """写入单个 dump 文件。


    功能说明:
    - 自动创建父目录。
    - 保证文件以换行结尾，方便后续命令行查看和机械 diff。

    使用示例:
    - _write_dump_file(Path("dump/01-first-ir.mlir"), str(module))

    关联文件:
    - spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
    - test: [test/passes/test_pass_manager.py](test/passes/test_pass_manager.py)
    - 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    text = content if content.endswith("\n") else f"{content}\n"
    path.write_text(text, encoding="utf-8")


def _format_dump_ir(target: ModuleOp | Operation | str) -> str:
    """把当前 pass 结果格式化为 dump 文本。


    功能说明:
    - 对 xDSL operation 使用公开 alias printer，保证诊断 dump 默认是 alias IR。
    - 字符串输入保持原样，用于已经格式化好的错误或测试文本。

    使用示例:
    - _format_dump_ir(module)

    关联文件:
    - spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
    - test: [test/passes/test_pass_manager.py](test/passes/test_pass_manager.py)
    - 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
    """
    if isinstance(target, str):
        return target
    return print_operation_with_aliases(target).rstrip()


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
            raise TypeError("pass_obj must be ModulePass with stable name(str)")
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
                raise TypeError("passes must contain ModulePass items with stable name(str)")
            self._passes.append(item)

    def run(self: "PassManager", target: ModuleOp) -> ModuleOp:
        """依序执行 Pass。


        功能说明:
        - 逐个调用 `ModulePass.apply(ctx, module)`。
        - 只接受 `builtin.module`，不再兼容任意对象 passthrough 或单 pass `run(...)`。
        - `kernel_gen.core.config.dump_dir` 非空时写入初始 IR 与每个 pass 后的 IR，便于定位 pipeline 中间态。

        使用示例:
        - result = pm.run(module)

        关联文件:
        - spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
        - test: [test/passes/test_pass_manager.py](test/passes/test_pass_manager.py)
        - 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
        """
        if not isinstance(target, ModuleOp):
            raise TypeError("PassManager.run target must be builtin.module")
        result = target
        ctx = Context()
        dump_path = get_dump_dir()
        if dump_path is not None:
            _write_dump_file(dump_path / "01-first-ir.mlir", _format_dump_ir(result))
        for index, item in enumerate(self._passes, start=2):
            item.apply(ctx, result)
            if _pass_fold_enabled(item):
                _fold_module(ctx, result)
            if dump_path is not None:
                pass_name = getattr(item, "name", "pass")
                safe_name = _sanitize_dump_name(pass_name)
                dump_text = f"{pass_name}\n{_format_dump_ir(result)}"
                _write_dump_file(dump_path / f"{index:02d}-{safe_name}.mlir", dump_text)
        return result


__all__ = ["Pass", "PassManager"]
