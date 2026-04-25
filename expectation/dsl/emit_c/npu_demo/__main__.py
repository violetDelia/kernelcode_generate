"""emit_c npu_demo expectation 目录入口。

创建者: 金铲铲大作战
最后一次更改: 朽木露琪亚

功能说明:
- 运行 `expectation/dsl/emit_c/npu_demo` 目录下当前 tracked 的全部 expectation。
- 当前真实目录集合只包含 `cost/`，因此目录入口只聚合 `cost` 子目录。
- 作为 `python -m expectation.dsl.emit_c.npu_demo` 的统一入口。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -m expectation.dsl.emit_c.npu_demo`

关联文件:
- spec: [`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
- test: [`test/dsl/test_emit_c.py`](test/dsl/test_emit_c.py)
- 功能实现: [`expectation/dsl/emit_c/npu_demo/__main__.py`](expectation/dsl/emit_c/npu_demo/__main__.py)
"""

from importlib import import_module


def _load_cost_main() -> object:
    """加载当前目录入口对应的 `cost` runner。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 包上下文可用时优先走 sibling package import。
    - 当前目录入口只承接 `cost/` 子目录，不再依赖缺失的 `header/kernel/dma/symbol`。

    使用示例:
    - `cost_main = _load_cost_main()`

    关联文件:
    - spec: [`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)
    - test: [`test/tools/test_emitc_case_runner.py`](test/tools/test_emitc_case_runner.py)
    - 功能实现: [`expectation/dsl/emit_c/npu_demo/__main__.py`](expectation/dsl/emit_c/npu_demo/__main__.py)
    """

    if __package__:
        from .cost.__main__ import main as module_main
        return module_main
    return import_module("expectation.dsl.emit_c.npu_demo.cost.__main__").main


cost_main = _load_cost_main()


def main() -> None:
    """运行 npu_demo emit_c expectation 聚合入口。

    创建者: 金铲铲大作战
    最后一次更改: 朽木露琪亚

    功能说明:
    - 当前只运行实际存在的 `cost/` 子目录 expectation。
    - 不再依赖缺失的 `header/kernel/dma/symbol` 子目录。

    使用示例:
    - `main()`

    关联文件:
    - spec: [`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)
    - test: [`test/dsl/test_emit_c.py`](test/dsl/test_emit_c.py)
    - 功能实现: [`expectation/dsl/emit_c/npu_demo/__main__.py`](expectation/dsl/emit_c/npu_demo/__main__.py)
    """

    cost_main()


if __name__ == "__main__":
    main()
