"""emit_c npu_demo expectation 目录入口。

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 运行 `expectation/dsl/emit_c/npu_demo` 目录下的全部 expectation。
- 先运行独立的生成源码头部 expectation，再聚合 `kernel/`、`dma/`、`cost/` 与 `symbol/` 子目录。
- 作为 `python -m expectation.dsl.emit_c.npu_demo` 的统一入口。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.emit_c.npu_demo`

关联文件:
- spec: [`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
- test: [`test/dsl/test_emit_c.py`](test/dsl/test_emit_c.py)
- 功能实现: [`expectation/dsl/emit_c/npu_demo/__main__.py`](expectation/dsl/emit_c/npu_demo/__main__.py)
"""

from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

try:
    from .header import main as header_main
    from .kernel.__main__ import main as kernel_main
    from .dma.__main__ import main as dma_main
    from .cost.__main__ import main as cost_main
    from .symbol.__main__ import main as symbol_main
except ImportError:
    from header import main as header_main
    from kernel.__main__ import main as kernel_main
    from dma.__main__ import main as dma_main
    from cost.__main__ import main as cost_main
    from symbol.__main__ import main as symbol_main


def main() -> None:
    """运行 npu_demo emit_c expectation 聚合入口。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 先运行独立 header case，避免每个 op case 重复检查生成源码头部。
    - 再运行 kernel/dma/cost/symbol 四个子目录的 expectation。

    使用示例:
    - `main()`

    关联文件:
    - spec: [`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)
    - test: [`test/dsl/test_emit_c.py`](test/dsl/test_emit_c.py)
    - 功能实现: [`expectation/dsl/emit_c/npu_demo/__main__.py`](expectation/dsl/emit_c/npu_demo/__main__.py)
    """

    header_main()
    kernel_main()
    dma_main()
    cost_main()
    symbol_main()


if __name__ == "__main__":
    main()
