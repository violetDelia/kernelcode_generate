"""CUDA SM89 final IR kernel op registration package.

功能说明:
- 聚合 CUDA SM89 `kernel.*` op emit 注册模块。
- 不聚合或 re-export package-local emitter 对象，测试也不得直连本包内部模块。

API 列表:
- 无公开 API。

使用示例:
- source = emit_c(module, EmitCContext())

关联文件:
- spec: spec/dsl/gen_kernel/emit/cuda_sm89.md
- 功能实现: kernel_gen/dsl/gen_kernel/emit/cuda_sm89/source_bundle.py
"""

from __future__ import annotations

from . import binary_elewise as _binary_elewise  # noqa: F401
from . import exp as _exp  # noqa: F401
from . import img2col2d as _img2col2d  # noqa: F401
from . import matmul as _matmul  # noqa: F401
from . import reduce as _reduce  # noqa: F401

__all__: list[str] = []
