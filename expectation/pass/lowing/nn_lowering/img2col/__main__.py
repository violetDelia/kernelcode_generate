"""pass nn_lowering img2col family expectation 入口。
[immutable-file]


创建者: 大闸蟹
最后一次更改: 大闸蟹

功能说明:
- 运行 ircheck 版 `img2col` 整族 expectation。

使用示例:
- `python expectation/pass/lowing/nn_lowering/img2col`

关联文件:
- spec: [`spec/pass/lowering/nn_lowering.md`](spec/pass/lowering/nn_lowering.md)
- spec: [`spec/tools/ircheck.md`](spec/tools/ircheck.md)
- test: [`test/pass/test_lowering_nn_to_kernel.py`](test/pass/test_lowering_nn_to_kernel.py)
- 功能实现: [`expectation/pass/lowing/nn_lowering/img2col/_shared.py`](expectation/pass/lowing/nn_lowering/img2col/_shared.py)
"""

# Case 列表:
# - Case-img2col1d: 正例：nn.img2col1d 静态/符号维度输入应 lower 为 dma.alloc + kernel.img2col1d + func.return。
# - Case-img2col2d: 正例：nn.img2col2d 静态/符号维度输入应 lower 为 dma.alloc + kernel.img2col2d + func.return。

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
