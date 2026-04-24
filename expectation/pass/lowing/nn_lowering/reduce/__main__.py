"""pass nn_lowering reduce family expectation 入口。
[immutable-file]


创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 运行 ircheck 版 `reduce` 整族 expectation。

使用示例:
- `python expectation/pass/lowing/nn_lowering/reduce`

关联文件:
- spec: [`spec/pass/lowering/nn_lowering.md`](spec/pass/lowering/nn_lowering.md)
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
- test: [`test/pass/nn_lowering/reduce_sum.py`](test/pass/nn_lowering/reduce_sum.py)
- test: [`test/pass/nn_lowering/reduce_min.py`](test/pass/nn_lowering/reduce_min.py)
- test: [`test/pass/nn_lowering/reduce_max.py`](test/pass/nn_lowering/reduce_max.py)
- 功能实现: [`expectation/pass/lowing/nn_lowering/reduce/_shared.py`](expectation/pass/lowing/nn_lowering/reduce/_shared.py)
"""

# Case 列表:
# - case-reduce-sum-static: 正例：静态 nn.reduce_sum 输入应 lower 为 dma.alloc + kernel.reduce(kind=sum) + func.return。
# - case-reduce-sum-symbol: 正例：符号维度 nn.reduce_sum 输入应 lower 为 dma.alloc + kernel.reduce(kind=sum) + func.return。
# - case-reduce-min-static: 正例：静态 nn.reduce_min 输入应 lower 为 dma.alloc + kernel.reduce(kind=min) + func.return。
# - case-reduce-min-symbol: 正例：符号维度 nn.reduce_min 输入应 lower 为 dma.alloc + kernel.reduce(kind=min) + func.return。
# - case-reduce-min-symbol-dim: 正例：reduce 维度为符号时 nn.reduce_min 仍应 lower 为 dma.alloc + kernel.reduce(kind=min) + func.return。
# - case-reduce-max-static: 正例：静态 nn.reduce_max 输入应 lower 为 dma.alloc + kernel.reduce(kind=max) + func.return。
# - case-reduce-max-symbol: 正例：符号维度 nn.reduce_max 输入应 lower 为 dma.alloc + kernel.reduce(kind=max) + func.return。

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
