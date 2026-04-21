"""tile-reduce expectation package entry.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 运行 `tile-reduce` 目录下的 matmul 与 fc expectation。
- 目录入口固定服务于 `python -m expectation.pass.tile.reduce`。

使用示例:
- `PYTHONPATH=/path/to/worktree:/home/lfr/kernelcode_generate python -m expectation.pass.tile.reduce`

关联文件:
- spec: [`spec/pass/lowering/tile_reduce.md`](spec/pass/lowering/tile_reduce.md)
- test: [`test/pass/test_lowering_tile_reduce.py`](test/pass/test_lowering_tile_reduce.py)
- 功能实现: [`expectation/pass/tile/reduce/matmul.py`](expectation/pass/tile/reduce/matmul.py)
- 功能实现: [`expectation/pass/tile/reduce/fc.py`](expectation/pass/tile/reduce/fc.py)
"""

from __future__ import annotations

from pathlib import Path
import sys

if __package__:
    from .fc import main as fc_main
    from .matmul import main as matmul_main
else:
    CURRENT_DIR = Path(__file__).resolve().parent
    if str(CURRENT_DIR) not in sys.path:
        sys.path.insert(0, str(CURRENT_DIR))
    from fc import main as fc_main
    from matmul import main as matmul_main


def main() -> None:
    """运行 tile-reduce 的目录级 expectation。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 先验证 out-first `kernel.matmul` 的 reduce 改写。
    - 再验证 fc 组合链路中的 reduce 改写与目录入口串联。

    使用示例:
    - `main()`

    关联文件:
    - spec: [`spec/pass/lowering/tile_reduce.md`](spec/pass/lowering/tile_reduce.md)
    - test: [`test/pass/test_lowering_tile_reduce.py`](test/pass/test_lowering_tile_reduce.py)
    - 功能实现: [`expectation/pass/tile/reduce/__main__.py`](expectation/pass/tile/reduce/__main__.py)
    """

    matmul_main()
    fc_main()


if __name__ == "__main__":
    main()
