"""nn dialect registration for EmitC op emission.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 把 `nn` 相关的节点级发射挂到 `emit_c` 注册表。
- 当前阶段先保持旧输出一致，再继续迁移函数级策略。

使用示例:
- import kernel_gen.dsl.gen_kernel.emit_c.nn  # 触发注册

关联文件:
- spec: [spec/dsl/emit_c.md](../../../../spec/dsl/emit_c.md)
- test: [test/dsl/test_emit_c.py](../../../../test/dsl/test_emit_c.py)
- 功能实现: [kernel_gen/dsl/gen_kernel/emit_c/](.)
"""

from __future__ import annotations

from kernel_gen.dialect.nn import NnAddOp, NnImg2col2dOp

from .._legacy import load_legacy_emit_c_module
from .register import emit_c_impl

_legacy_emit_c = load_legacy_emit_c_module()


@emit_c_impl(NnAddOp, NnImg2col2dOp)
def _emit_nn_op(op, ctx) -> str:
    return _legacy_emit_c.emit_c_op(op, ctx)


__all__: list[str] = []
