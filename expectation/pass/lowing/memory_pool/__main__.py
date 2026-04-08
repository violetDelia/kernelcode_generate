"""memory_pool expectation 目录入口。

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 作为 expectation/pass/lowing/memory_pool 的目录级入口。
- 顺序运行 summary 与 loop_reuse 覆盖摘要与循环复用场景。

使用示例:
- PYTHONPATH=. python -m expectation.pass.lowing.memory_pool

关联文件:
- spec: [`spec/pass/lowering/memory_pool.md`](spec/pass/lowering/memory_pool.md)
- test: [`test/pass/test_memory_pool.py`](test/pass/test_memory_pool.py)
- 功能实现: [`kernel_gen/passes/lowering/memory_pool.py`](kernel_gen/passes/lowering/memory_pool.py)
"""

from __future__ import annotations

import runpy


def main() -> None:
    """运行 memory_pool expectation 入口。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 顺序执行 summary 与 loop_reuse 两个脚本。

    使用示例:
    - main()

    关联文件:
    - spec: [`spec/pass/lowering/memory_pool.md`](spec/pass/lowering/memory_pool.md)
    - test: [`test/pass/test_memory_pool.py`](test/pass/test_memory_pool.py)
    - 功能实现: [`kernel_gen/passes/lowering/memory_pool.py`](kernel_gen/passes/lowering/memory_pool.py)
    """

    runpy.run_module("expectation.pass.lowing.memory_pool.summary", run_name="__main__")
    runpy.run_module("expectation.pass.lowing.memory_pool.loop_reuse", run_name="__main__")


if __name__ == "__main__":
    main()
