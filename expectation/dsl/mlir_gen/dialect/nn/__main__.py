"""DSL nn family expectation 目录入口。

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 运行 `expectation/dsl/mlir_gen/dialect/nn` 目录下的全部 expectation 入口。
- 聚合 nn family 子目录与根目录脚本，作为 `python -m expectation.dsl.mlir_gen.dialect.nn` 的统一黑盒入口。

使用示例:
- `PYTHONPATH=. python -m expectation.dsl.mlir_gen.dialect.nn`

关联文件:
- spec: [`spec/dsl/mlir_gen.md`](spec/dsl/mlir_gen.md)
- spec: [`spec/dialect/nn.md`](spec/dialect/nn.md)
- test: [`test/dsl/test_mlir_gen.py`](test/dsl/test_mlir_gen.py)
- test: [`test/tools/test_mlir_gen_compare.py`](test/tools/test_mlir_gen_compare.py)
- 功能实现: [`kernel_gen/dsl/mlir_gen.py`](kernel_gen/dsl/mlir_gen.py)
- 功能实现: [`kernel_gen/tools/mlir_gen_compare.py`](kernel_gen/tools/mlir_gen_compare.py)
"""

from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

try:
    from .broadcast import main as broadcast_main
    from .broadcast_to import main as broadcast_to_main
    from .conv import main as conv_main
    from .element_binary.__main__ import main as element_binary_main
    from .element_compare.__main__ import main as element_compare_main
    from .element_unary.__main__ import main as element_unary_main
    from .fc import main as fc_main
    from .img2col1d import main as img2col1d_main
    from .img2col2d import main as img2col2d_main
    from .matmul import main as matmul_main
    from .reduce.__main__ import main as reduce_main
    from .softmax import main as softmax_main
except ImportError:
    from broadcast import main as broadcast_main
    from broadcast_to import main as broadcast_to_main
    from conv import main as conv_main
    from element_binary.__main__ import main as element_binary_main
    from element_compare.__main__ import main as element_compare_main
    from element_unary.__main__ import main as element_unary_main
    from fc import main as fc_main
    from img2col1d import main as img2col1d_main
    from img2col2d import main as img2col2d_main
    from matmul import main as matmul_main
    from reduce.__main__ import main as reduce_main
    from softmax import main as softmax_main


def main() -> None:
    broadcast_main()
    broadcast_to_main()
    conv_main()
    element_binary_main()
    element_compare_main()
    element_unary_main()
    fc_main()
    img2col1d_main()
    img2col2d_main()
    matmul_main()
    reduce_main()
    softmax_main()


if __name__ == "__main__":
    main()
