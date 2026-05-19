"""npu_demo DMA EmitC 注册聚合。

功能说明:
- 导入并注册 target=`npu_demo` 的 DMA op EmitC 发射实现。
- 本文件不提供跨文件公开 API；调用方必须通过 emit registry 与 `emit_c_op(...)` 公开入口调度。

API 列表:
- 无公开 API。

使用示例:
- from kernel_gen.dsl.gen_kernel.emit import emit_c_op
- source = emit_c_op(op, ctx)

关联文件:
- spec: spec/dsl/gen_kernel/emit/npu_demo/dma/__init__.md
- test: test/dsl/gen_kernel/emit/test_package.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/dma/__init__.py
"""

from . import alloc, broadcast, cast, copy, deslice, fill, free, load, reshape, ring, slice, store, transpose, view  # noqa: F401
