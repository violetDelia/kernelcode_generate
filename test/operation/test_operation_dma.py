"""dma facade smoke tests.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 保留 `test_operation_dma.py` 作为 dma helper 的兼容冒烟入口。
- 具体 alloc/lifecycle 与 transfer/view 用例已拆分到独立 family 文件。

使用示例:
- pytest -q test/operation/test_operation_dma.py

关联文件:
- 功能实现: kernel_gen/operation/dma.py
- Spec 文档: spec/operation/dma.md
- 测试文件: test/operation/test_operation_dma.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.operation.dma import alloc, copy, view
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.type import NumericType


# TC-OP-DMA-FACADE-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-16 01:06:00 +0800
# 最近一次运行成功时间: 2026-04-16 01:06:00 +0800
# 测试目的: 验证 dma smoke 入口仍可直接调用 alloc/copy。
# 使用示例: pytest -q test/operation/test_operation_dma.py -k test_dma_facade_alloc_copy_smoke
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma.py
def test_dma_facade_alloc_copy_smoke() -> None:
    source = alloc([2, 2], NumericType.Float32)
    copied = copy(source, MemorySpace.SM)
    assert source.get_shape() == [2, 2]
    assert copied.space is MemorySpace.SM


# TC-OP-DMA-FACADE-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-16 01:06:00 +0800
# 最近一次运行成功时间: 2026-04-16 01:06:00 +0800
# 测试目的: 验证 dma smoke 入口仍可直接调用 view。
# 使用示例: pytest -q test/operation/test_operation_dma.py -k test_dma_facade_view_smoke
# 对应功能实现文件路径: kernel_gen/operation/dma.py
# 对应 spec 文件路径: spec/operation/dma.md
# 对应测试文件路径: test/operation/test_operation_dma.py
def test_dma_facade_view_smoke() -> None:
    result = view(Memory([4, 4], NumericType.Float32), offset=[0, 0], size=[2, 2], stride=[1, 1])
    assert result.get_shape() == [2, 2]

