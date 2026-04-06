"""Target registry skeleton for ExecutionEngine (P0).

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 本模块为后续阶段预留 target->include 映射的实现落点。
- S1 阶段仅冻结 target 名称与 include family 的合同文本与测试入口。

使用示例:
- from kernel_gen.execute_engine.target_registry import target_includes
- assert "include/npu_demo/npu_demo.h" in target_includes("npu_demo")[0]

关联文件:
- spec: spec/execute_engine/execute_engine_target.md
- test: test/execute_engine/test_execute_engine_contract.py
- 功能实现: kernel_gen/execute_engine/target_registry.py
"""

from __future__ import annotations


def target_includes(target: str) -> tuple[str, ...]:
    """返回 target 对应的 include set（P0 合同）。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 返回执行引擎 P0 的 target->include family 映射，用于后续阶段把 include 注入到编译单元中。
    - S1 阶段只保证映射规则存在且可被测试机械检查，不负责解析源码中的 include。

    使用示例:
    - assert target_includes("npu_demo") == ('#include "include/npu_demo/npu_demo.h"',)
    - assert '#include "include/cpu/Memory.h"' in target_includes("cpu")

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_execute_engine_contract.py
    - 功能实现: kernel_gen/execute_engine/target_registry.py
    """

    if target == "npu_demo":
        return ('#include "include/npu_demo/npu_demo.h"',)
    if target == "cpu":
        return (
            '#include "include/cpu/Memory.h"',
            '#include "include/cpu/Nn.h"',
        )
    return ()


__all__ = ["target_includes"]
