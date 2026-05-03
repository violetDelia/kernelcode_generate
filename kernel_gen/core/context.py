"""kernel_gen IR parsing Context helpers.


功能说明:
- 提供仓库内统一的 xdsl Context 构造函数，用于“解析 + 打印”类工具的默认上下文。
- 默认加载基础 dialect（builtin/func/arith/scf）以及仓库内常用 dialect（nn/kernel/symbol/dma/arch）。
- 该模块只负责“dialect 注册/加载”，不负责 pass 执行，也不负责对 IR 做任何变换。

API 列表:
- `build_default_context() -> xdsl.context.Context`

使用示例:
- from xdsl.parser import Parser
- from kernel_gen.core.context import build_default_context
- ctx = build_default_context()
- module = Parser(ctx, "builtin.module { func.func @main() { func.return } }").parse_module()

关联文件:
- spec:
  - [spec/core/context.md](spec/core/context.md)
  - [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
  - [spec/tools/ircheck.md](spec/tools/ircheck.md)
- test:
  - [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
- 功能实现:
  - [kernel_gen/core/context.py](kernel_gen/core/context.py)
"""

from __future__ import annotations

import os

from xdsl.context import Context as XdslContext


def build_default_context() -> XdslContext:
    """构造用于 IR 解析与打印的默认 xdsl Context。


    功能说明:
    - 加载基础 dialect：builtin/func/arith/scf。
    - 加载仓库常用 dialect：nn/kernel/symbol/dma/arch。
    - 目标是让工具在默认环境下可解析常见的 module 文本，避免“未注册 dialect”导致的解析失败。

    使用示例:
    - ctx = build_default_context()
    - module = Parser(ctx, ir_text).parse_module()

    关联文件:
    - spec:
      - [spec/core/context.md](spec/core/context.md)
      - [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
      - [spec/tools/ircheck.md](spec/tools/ircheck.md)
    - test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/core/context.py](kernel_gen/core/context.py)
    """

    os.environ.setdefault("SYMPY_GMPY", "0")

    from xdsl.dialects.arith import Arith
    from xdsl.dialects.builtin import Builtin
    from xdsl.dialects.func import Func
    from xdsl.dialects.scf import Scf

    from kernel_gen.dialect.arch import Arch
    from kernel_gen.dialect.dma import Dma
    from kernel_gen.dialect.kernel import Kernel
    from kernel_gen.dialect.nn import Nn
    from kernel_gen.dialect.symbol import Symbol
    from kernel_gen.dialect.tuner import Tuner

    ctx = XdslContext()
    ctx.load_dialect(Builtin)
    ctx.load_dialect(Func)
    ctx.load_dialect(Arith)
    ctx.load_dialect(Scf)
    ctx.load_dialect(Nn)
    ctx.load_dialect(Kernel)
    ctx.load_dialect(Symbol)
    ctx.load_dialect(Tuner)
    ctx.load_dialect(Dma)
    ctx.load_dialect(Arch)
    return ctx


__all__ = [
    "build_default_context",
]
