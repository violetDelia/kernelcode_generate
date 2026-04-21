"""tile expectation package entry.

创建者: 金铲铲大作战
最后一次更改: 大闸蟹

功能说明:
- 顺序运行当前存在的 `tile-elewise`、`tile-reduce` 目录级 expectation。
- `tile-analysis` 已不再作为有效目录级合同入口，聚合入口不得引用已删除资产。
- 子目录按当前 worktree 动态发现，避免某个专题目录已删除时聚合入口仍静态导入失败。

使用示例:
- `PYTHONPATH=/path/to/worktree:/home/lfr/kernelcode_generate python -m expectation.pass.tile`

关联文件:
- spec: [`spec/pass/lowering/tile.md`](spec/pass/lowering/tile.md)
- test: [`test/pass/test_lowering_tile_reduce.py`](test/pass/test_lowering_tile_reduce.py)
- 功能实现: [`expectation/pass/tile/elewise/__main__.py`](expectation/pass/tile/elewise/__main__.py)
- 功能实现: [`expectation/pass/tile/reduce/__main__.py`](expectation/pass/tile/reduce/__main__.py)
"""

from __future__ import annotations

from importlib import import_module
from importlib.util import find_spec
from pathlib import Path
import sys
from typing import Callable


VALID_SUBSUITES = ("elewise", "reduce")

if not __package__:
    REPO_ROOT = Path(__file__).resolve().parents[3]
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))


def _subsuite_module_name(subsuite: str) -> str:
    """返回当前执行模式下的子目录入口模块名。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - `python -m expectation.pass.tile` 时生成完整包名。
    - 直接运行本文件时也生成完整包名，保证子目录相对导入可用。

    使用示例:
    - `_subsuite_module_name("reduce")`

    关联文件:
    - spec: [`spec/pass/lowering/tile.md`](spec/pass/lowering/tile.md)
    - test: [`test/pass/test_lowering_tile_reduce.py`](test/pass/test_lowering_tile_reduce.py)
    - 功能实现: [`expectation/pass/tile/__main__.py`](expectation/pass/tile/__main__.py)
    """

    if __package__:
        return f"{__package__}.{subsuite}.__main__"
    return f"expectation.pass.tile.{subsuite}.__main__"


def _load_existing_subsuite_main(subsuite: str) -> Callable[[], None] | None:
    """加载存在的 tile 子目录入口。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 只尝试加载 `VALID_SUBSUITES` 中仍存在的目录入口。
    - 子目录不存在时返回 `None`，避免已删除专题继续阻断聚合入口。

    使用示例:
    - `main_fn = _load_existing_subsuite_main("reduce")`

    关联文件:
    - spec: [`spec/pass/lowering/tile.md`](spec/pass/lowering/tile.md)
    - test: [`test/pass/test_lowering_tile_reduce.py`](test/pass/test_lowering_tile_reduce.py)
    - 功能实现: [`expectation/pass/tile/__main__.py`](expectation/pass/tile/__main__.py)
    """

    module_name = _subsuite_module_name(subsuite)
    try:
        spec = find_spec(module_name)
    except ModuleNotFoundError:
        return None
    if spec is None:
        return None
    return import_module(module_name).main


def main() -> None:
    """运行 tile family 的目录级 expectation。

    创建者: 金铲铲大作战
    最后一次更改: 大闸蟹

    功能说明:
    - 依次执行当前存在的 elewise、reduce 子目录入口。
    - 不引用已删除的 tile-analysis 目录级合同入口。
    - 任一子入口失败时直接抛出原始失败，便于任务记录复现。

    使用示例:
    - `main()`

    关联文件:
    - spec: [`spec/pass/lowering/tile.md`](spec/pass/lowering/tile.md)
    - test: [`test/pass/test_lowering_tile_reduce.py`](test/pass/test_lowering_tile_reduce.py)
    - 功能实现: [`expectation/pass/tile/__main__.py`](expectation/pass/tile/__main__.py)
    """

    loaded: list[tuple[str, Callable[[], None]]] = []
    for subsuite in VALID_SUBSUITES:
        main_fn = _load_existing_subsuite_main(subsuite)
        if main_fn is not None:
            loaded.append((subsuite, main_fn))

    if not loaded:
        raise RuntimeError("no tile expectation subsuite found")

    for _, main_fn in loaded:
        main_fn()


if __name__ == "__main__":
    main()
