"""tile elewise expectation 目录入口。

创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 运行 `tile/elewise` 目录下的 expectation。
- 当前覆盖 `dma.broadcast`、`kernel.binary_elewise`、compare 类
  `kernel.binary_elewise`，以及带 `tile.analysis` 的 `kernel.matmul` / `fc`
  在 `tile-elewise` 下只切分 `elewise` 轴的行为。

使用示例:
- `PYTHONPATH=. python -m expectation.pass.tile.elewise`

关联文件:
- spec: [`spec/pass/lowering/tile.md`](spec/pass/lowering/tile.md)
- test: [`test/pass/test_lowering_tile.py`](test/pass/test_lowering_tile.py)
- 功能实现: [`expectation/pass/tile/elewise/broadcast.py`](expectation/pass/tile/elewise/broadcast.py)
- 功能实现: [`expectation/pass/tile/elewise/element_binary.py`](expectation/pass/tile/elewise/element_binary.py)
- 功能实现: [`expectation/pass/tile/elewise/element_compare.py`](expectation/pass/tile/elewise/element_compare.py)
- 功能实现: [`expectation/pass/tile/elewise/matmul.py`](expectation/pass/tile/elewise/matmul.py)
- 功能实现: [`expectation/pass/tile/elewise/fc.py`](expectation/pass/tile/elewise/fc.py)
"""

from pathlib import Path
import sys

if __package__:
    from .broadcast import main as broadcast_main
    from .element_binary import main as element_binary_main
    from .element_compare import main as element_compare_main
    from .fc import main as fc_main
    from .matmul import main as matmul_main
else:
    CURRENT_DIR = Path(__file__).resolve().parent
    if str(CURRENT_DIR) not in sys.path:
        sys.path.insert(0, str(CURRENT_DIR))
    from broadcast import main as broadcast_main
    from element_binary import main as element_binary_main
    from element_compare import main as element_compare_main
    from fc import main as fc_main
    from matmul import main as matmul_main


def main() -> None:
    broadcast_main()
    element_binary_main()
    element_compare_main()
    matmul_main()
    fc_main()


if __name__ == "__main__":
    main()
