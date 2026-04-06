"""Compiler hook skeleton for ExecutionEngine (P0).

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 本模块为后续阶段预留“编译命令生成/执行”的实现落点。
- S1 阶段仅要求目录骨架与文档引用自洽，不要求真实调用。

使用示例:
- from kernel_gen.execute_engine.compiler import default_compiler
- assert default_compiler() == "g++"

关联文件:
- spec: spec/execute_engine/execute_engine_target.md
- test: test/execute_engine/test_execute_engine_contract.py
- 功能实现: kernel_gen/execute_engine/compiler.py
"""

from __future__ import annotations


def default_compiler() -> str:
    """返回 P0 默认编译器名。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 以固定值返回执行引擎 P0 的默认编译器名，用于生成可复现的编译命令骨架。

    使用示例:
    - assert default_compiler() == "g++"

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_execute_engine_contract.py
    - 功能实现: kernel_gen/execute_engine/compiler.py
    """

    return "g++"


__all__ = ["default_compiler"]
