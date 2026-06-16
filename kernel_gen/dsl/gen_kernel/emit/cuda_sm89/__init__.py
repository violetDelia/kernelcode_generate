"""CUDA SM89 emit package registration.

功能说明:
- 聚合 CUDA SM89 target include、kernel op 和 `ModuleOp` backend 注册模块。
- 保持 `target="cuda_sm89"` 通过 emit registry 自动加载，不暴露包外 helper。

API 列表:
- 无公开 API；本包只通过 emit registry 自动加载。

使用示例:
- from kernel_gen.dsl.gen_kernel import emit_c
- source = emit_c(module, EmitCContext())

关联文件:
- spec: spec/dsl/gen_kernel/emit/cuda_sm89.md
- 功能实现: kernel_gen/dsl/gen_kernel/emit/cuda_sm89/include.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/cuda_sm89/kernel/__init__.py
- test: test/dsl/gen_kernel/emit/test_cuda_sm89_emit.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/cuda_sm89/module.py
"""

from __future__ import annotations

from . import include as _include  # noqa: F401
from . import kernel as _kernel  # noqa: F401
from . import module as _module  # noqa: F401

__all__: list[str] = []
