"""`target=npu_demo` 的按 dialect 注册 emitter 入口。


功能说明:
- 聚合 `arch/dma/kernel/nn/symbol/tuner/type` 各子目录注册的 emitter。
- 只通过注册体系为根级 `emit` 分发层提供 `npu_demo` target 的 op/value 发射实现。

API 列表:
- 无公开 API。

使用示例:
- `from kernel_gen.dsl.gen_kernel.emit import emit_c`
- `source = emit_c(op, ctx)`

关联文件:
- spec: [`spec/dsl/gen_kernel/emit.md`](spec/dsl/gen_kernel/emit.md)
- test: [`test/dsl/gen_kernel/emit/test_package.py`](test/dsl/gen_kernel/emit/test_package.py)
- 功能实现: [`kernel_gen/dsl/gen_kernel/emit/npu_demo/__init__.py`](kernel_gen/dsl/gen_kernel/emit/npu_demo/__init__.py)
"""

from __future__ import annotations
from . import arch as _arch  # noqa: F401
from . import dma as _dma  # noqa: F401
from . import include as _include  # noqa: F401
from . import kernel as _kernel  # noqa: F401
from . import name as _name  # noqa: F401
from . import nn as _nn  # noqa: F401
from . import symbol as _symbol  # noqa: F401
from . import tuner as _tuner  # noqa: F401
from . import type as _type  # noqa: F401

__all__: list[str] = []
