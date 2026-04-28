"""Pass manager API.

创建者: 李白
最后一次更改: 大闸蟹

功能说明:
- 定义 Pass 与 PassManager 的基础行为。
- 固定 `kernel_gen.passes.pass_manager` 只承载 Pass 抽象与 PassManager，不再承载默认 pipeline builder。
- 当前文件不额外公开 helper；内部状态仅通过 `Pass` / `PassManager` 两个公开入口对外生效。
- `PassManager.run(...)` 从 `kernel_gen.core.config.get_dump_dir()` 读取诊断产物落盘开关，不改变 pass 执行语义。
- pass 实例默认 `fold=True`；管理器在每个 pass 后对 `ModuleOp` 执行一次仅 folding、不做 DCE 的 fold sweep。

API 列表:
- `class Pass(fold: bool = True)`
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
from pathlib import Path
import re

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.passes import ModulePass as XdslModulePass
from xdsl.pattern_rewriter import GreedyRewritePatternApplier, PatternRewriteWalker

from kernel_gen.core.config import get_dump_dir


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

    def __init__(self: "Pass", fold: bool = True) -> None:
        """初始化 Pass 公共选项。

        创建者: 大闸蟹
        最后一次更改: 大闸蟹

        功能说明:
        - 记录是否允许 pass 后执行 folding；默认开启。
        - 该选项不改变具体 pass 的业务重写规则，只控制通用 symbol folding sweep。

        使用示例:
        - pass_obj = MyPass()
        - pass_obj = MyPass(fold=False)

        关联文件:
        - spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
        - test: [test/pass/test_pass_manager.py](test/pass/test_pass_manager.py)
        - 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
        """

        self.fold = bool(fold)

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

        result = self.run(op)
        if _pass_fold_enabled(self) and isinstance(result, ModuleOp):
            _fold_module(ctx, result)


def _sanitize_dump_name(value: str) -> str:
    """把 pass 名称规整为安全文件名片段。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 保留字母、数字、点、下划线与短横线。
    - 其他字符统一替换为 `_`，避免 dump 文件名依赖 shell 或文件系统特殊字符。

    使用示例:
    - _sanitize_dump_name("tile-elewise")

    关联文件:
    - spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
    - test: [test/pass/test_pass_manager.py](test/pass/test_pass_manager.py)
    - 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
    """
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return safe_name or "pass"


def _write_dump_file(path: Path, content: str) -> None:
    """写入单个 dump 文件。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 自动创建父目录。
    - 保证文件以换行结尾，方便后续命令行查看和机械 diff。

    使用示例:
    - _write_dump_file(Path("dump/01-first-ir.mlir"), str(module))

    关联文件:
    - spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
    - test: [test/pass/test_pass_manager.py](test/pass/test_pass_manager.py)
    - 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    text = content if content.endswith("\n") else f"{content}\n"
    path.write_text(text, encoding="utf-8")


def _format_dump_ir(target: object) -> str:
    """把当前 pass 结果格式化为 dump 文本。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 优先复用对象自身 `str(...)` 表示。
    - 不在 dump 路径引入额外 IR parser/printer 依赖，避免诊断功能改变业务路径。

    使用示例:
    - _format_dump_ir(module)

    关联文件:
    - spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
    - test: [test/pass/test_pass_manager.py](test/pass/test_pass_manager.py)
    - 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
    """
    return str(target)


def _load_fold_dialects(ctx: Context) -> None:
    """加载当前仓库 folding 需要的 dialect。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 当前仓库只有 `symbol.*` 实现 `HasFolderInterface`，folding 物化常量时需要 `Symbol` dialect。
    - 该 helper 仅服务本文件内部 fold sweep，不对外作为公开 API 暴露。

    使用示例:
    - _load_fold_dialects(ctx)

    关联文件:
    - spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
    - test: [test/pass/test_pass_manager.py](test/pass/test_pass_manager.py)
    - 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
    """

    from kernel_gen.dialect.symbol import Symbol

    if ctx.get_optional_dialect(Symbol.name) is None:
        ctx.load_dialect(Symbol)


def _fold_module(ctx: Context, module: ModuleOp) -> None:
    """对 module 执行一次仅 folding 的 sweep。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 使用空 pattern 列表，只启用 `GreedyRewritePatternApplier` 的 folding 分支。
    - 显式关闭 DCE，避免通用 fold 开关额外删除 IR 节点。

    使用示例:
    - _fold_module(ctx, module)

    关联文件:
    - spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
    - test: [test/pass/test_pass_manager.py](test/pass/test_pass_manager.py)
    - 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
    """

    _load_fold_dialects(ctx)
    PatternRewriteWalker(
        GreedyRewritePatternApplier(
            [],
            ctx=ctx,
            folding_enabled=True,
            dce_enabled=False,
        )
    ).rewrite_module(module)


def _pass_fold_enabled(pass_obj: XdslModulePass) -> bool:
    """读取 pass 的 folding 开关。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 未声明 `fold` 的第三方 `ModulePass` 按默认开启处理。
    - 只有显式 `fold=False` 时关闭 fold sweep。

    使用示例:
    - if _pass_fold_enabled(pass_obj): ...

    关联文件:
    - spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
    - test: [test/pass/test_pass_manager.py](test/pass/test_pass_manager.py)
    - 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
    """

    return getattr(pass_obj, "fold", True) is not False


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
        最后一次更改: 大闸蟹

        功能说明:
        - 逐个调用 Pass.run。
        - `kernel_gen.core.config.dump_dir` 非空时写入初始 IR 与每个 pass 后的 IR，便于定位 pipeline 中间态。

        使用示例:
        - result = pm.run(ir)

        关联文件:
        - spec: [spec/pass/pass_manager.md](spec/pass/pass_manager.md)
        - test: [test/pass/test_pass_manager.py](test/pass/test_pass_manager.py)
        - 功能实现: [kernel_gen/passes/pass_manager.py](kernel_gen/passes/pass_manager.py)
        """
        result = target
        ctx = Context()
        dump_path = get_dump_dir()
        if dump_path is not None:
            _write_dump_file(dump_path / "01-first-ir.mlir", _format_dump_ir(result))
        for index, item in enumerate(self._passes, start=2):
            if isinstance(item, Pass):
                result = item.run(result)
            else:
                item.apply(ctx, result)  # type: ignore[arg-type]
            if _pass_fold_enabled(item) and isinstance(result, ModuleOp):
                _fold_module(ctx, result)
            if dump_path is not None:
                pass_name = getattr(item, "name", "pass")
                safe_name = _sanitize_dump_name(pass_name)
                dump_text = f"{pass_name}\n{_format_dump_ir(result)}"
                _write_dump_file(dump_path / f"{index:02d}-{safe_name}.mlir", dump_text)
        return result


__all__ = ["Pass", "PassManager"]
