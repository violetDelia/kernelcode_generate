"""tile expectation package entry.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 顺序运行 `tile-analysis`、`tile-elewise`、`tile-reduce` 三组目录级 expectation。
- 作为 S4 worktree-first 覆盖入口，保证 `python -m expectation.pass.tile`
  先命中当前 worktree 中修正后的 reduce 证据。

使用示例:
- `PYTHONPATH=/path/to/worktree:/home/lfr/kernelcode_generate python -m expectation.pass.tile`

关联文件:
- spec: [`spec/pass/lowering/tile.md`](spec/pass/lowering/tile.md)
- test: [`test/pass/test_lowering_tile_reduce.py`](test/pass/test_lowering_tile_reduce.py)
- 功能实现: [`expectation/pass/tile/reduce/__main__.py`](expectation/pass/tile/reduce/__main__.py)
"""

from __future__ import annotations

from pathlib import Path
import sys

if __package__:
    from .analysis.__main__ import main as analysis_main
    from .elewise.__main__ import main as elewise_main
    from .reduce.__main__ import main as reduce_main
else:
    CURRENT_DIR = Path(__file__).resolve().parent
    if str(CURRENT_DIR) not in sys.path:
        sys.path.insert(0, str(CURRENT_DIR))
    from analysis.__main__ import main as analysis_main
    from elewise.__main__ import main as elewise_main
    from reduce.__main__ import main as reduce_main


def main() -> None:
    """运行 tile family 的目录级 expectation。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 依次执行 analysis、elewise、reduce 三个子目录入口。
    - 任一子入口失败时直接抛出原始失败，便于任务记录复现。

    使用示例:
    - `main()`

    关联文件:
    - spec: [`spec/pass/lowering/tile.md`](spec/pass/lowering/tile.md)
    - test: [`test/pass/test_lowering_tile_reduce.py`](test/pass/test_lowering_tile_reduce.py)
    - 功能实现: [`expectation/pass/tile/__main__.py`](expectation/pass/tile/__main__.py)
    """

    analysis_main()
    elewise_main()
    reduce_main()


if __name__ == "__main__":
    main()
