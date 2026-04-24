"""pass nn_lowering element_binary family expectation 入口。
[immutable-file]


创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 运行 ircheck 版 `element_binary` 整族 expectation。

使用示例:
- `python expectation/pass/lowing/nn_lowering/element_binary`

关联文件:
- spec: [`spec/pass/lowering/nn_lowering.md`](spec/pass/lowering/nn_lowering.md)
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
- test: [`test/pass/test_lowering_nn_to_kernel.py`](test/pass/test_lowering_nn_to_kernel.py)
- 功能实现: [`expectation/pass/lowing/nn_lowering/element_binary/_shared.py`](expectation/pass/lowing/nn_lowering/element_binary/_shared.py)
"""

# Case 列表:
# - Case-add: 正例：nn.add 静态/符号维度输入应 lower 为 dma.alloc + kernel.binary_elewise(kind=add) + func.return。
# - Case-sub: 正例：nn.sub 静态/符号维度输入应 lower 为 dma.alloc + kernel.binary_elewise(kind=sub) + func.return。
# - Case-mul: 正例：nn.mul 静态/符号维度输入应 lower 为 dma.alloc + kernel.binary_elewise(kind=mul) + func.return。
# - Case-div: 正例：nn.div 静态/符号维度输入应 lower 为 dma.alloc + kernel.binary_elewise(kind=div) + func.return。
# - Case-truediv: 正例：nn.truediv 静态/符号维度输入应 lower 为 dma.alloc + kernel.binary_elewise(kind=div) + func.return。

try:
    from ._shared import main
except ImportError:
    from pathlib import Path
    import sys

    CURRENT_DIR = Path(__file__).resolve().parent
    if str(CURRENT_DIR) not in sys.path:
        sys.path.insert(0, str(CURRENT_DIR))

    from _shared import main


if __name__ == "__main__":
    main()
