"""Entry shim builder skeleton for ExecutionEngine (P0).

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 本模块为后续阶段预留 “entry shim 生成” 的实现落点。
- S1 阶段仅要求骨架与失败短语合同冻结，不实现真实的 shim 输出。

使用示例:
- from kernel_gen.execute_engine.entry_shim_builder import build_entry_shim_source
- src = build_entry_shim_source(function="cpu::add", entry_point="kg_execute_entry")

关联文件:
- spec: spec/execute_engine/execute_engine_target.md
- test: test/execute_engine/test_execute_engine_contract.py
- 功能实现: kernel_gen/execute_engine/entry_shim_builder.py
"""

from __future__ import annotations


def build_entry_shim_source(*, function: str, entry_point: str) -> str:
    """构造最小 entry shim 源码片段（占位）。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - S1 阶段用于让目录骨架与文档引用自洽：返回一个可读的占位源码片段。
    - 不生成真实可编译 shim；后续阶段可在同函数内逐步替换为真实实现。

    使用示例:
    - src = build_entry_shim_source(function="cpu::add", entry_point="kg_execute_entry")

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_execute_engine_contract.py
    - 功能实现: kernel_gen/execute_engine/entry_shim_builder.py
    """

    return f"// entry shim placeholder for {function} as {entry_point}\n"


__all__ = ["build_entry_shim_source"]
