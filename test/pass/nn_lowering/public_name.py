"""nn_lowering public API tests.

创建者: 小李飞刀
最后一次更改: 金铲铲大作战

功能说明:
- 验证 NnLoweringPass 的公开名称与导出路径。

使用示例:
- pytest -q test/pass/nn_lowering/public_name.py

关联文件:
- 功能实现: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
- Spec 文档: spec/pass/lowering/nn_lowering.md
- 测试文件: test/pass/nn_lowering/public_name.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.passes import lowering as lowering_pkg
from kernel_gen.passes.lowering import NnLoweringError, NnLoweringPass


# TC-PASS-NNL-001
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-11 21:10:00 +0800
# 最近一次运行成功时间: 2026-04-11 21:10:00 +0800
# 测试目的: 验证 NnLoweringPass 使用新的公开名字。
# 使用示例: pytest -q test/pass/nn_lowering/public_name.py -k test_nn_lowering_pass_public_name
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/nn_lowering.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/public_name.py
def test_nn_lowering_pass_public_name() -> None:
    assert NnLoweringPass().name == "lower-nn"


# TC-PASS-NNL-002
# 创建者: 小李飞刀
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-12 17:40:00 +0800
# 最近一次运行成功时间: 2026-04-12 17:40:00 +0800
# 测试目的: 验证 nn_lowering 公共导出只保留唯一入口与错误类型。
# 使用示例: pytest -q test/pass/nn_lowering/public_name.py -k test_nn_lowering_pass_public_exports
# 对应功能实现文件路径: kernel_gen/passes/lowering/nn_lowering/__init__.py
# 对应 spec 文件路径: spec/pass/lowering/nn_lowering.md
# 对应测试文件路径: test/pass/nn_lowering/public_name.py
def test_nn_lowering_pass_public_exports() -> None:
    assert NnLoweringPass is not None
    assert NnLoweringError is not None
    assert "LowerNnToKernelPass" not in getattr(lowering_pkg, "__all__", [])
    assert not hasattr(lowering_pkg, "LowerNnToKernelPass")
