"""cuda_sm86 target registry tests.


功能说明:
- 通过公开 target registry API 验证 `cuda_sm86` 内置 target 可查询。
- 锁定 CUDA SM86 首版只复用既有 hardware 字段，不新增 compute capability 字段。

使用示例:
- pytest -q test/target/test_cuda_sm86_registry.py

关联文件:
- 功能实现: kernel_gen/target/registry.py
- Spec 文档: spec/target/registry.md
- 测试文件: test/target/test_cuda_sm86_registry.py
"""

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.target import registry as target_registry


def test_cuda_sm86_target_is_registered_with_sm86_hardware_contract() -> None:
    """验证 cuda_sm86 target 的公开硬件与 arch 能力合同。

    功能说明:
    - 只通过 `get_target_hardware(...)` 与 `is_arch_op_supported(...)` 查询公开 target registry。
    - 锁定 `thread_num/block_num/subthread_num/tsm/tlm*` 字段和 `arch.launch` 支持边界。

    使用示例:
    - pytest -q test/target/test_cuda_sm86_registry.py -k sm86_hardware_contract
    """

    assert target_registry.get_target_hardware("cuda_sm86", "thread_num") == 256
    assert target_registry.get_target_hardware("cuda_sm86", "block_num") == 1
    assert target_registry.get_target_hardware("cuda_sm86", "subthread_num") == 32
    assert target_registry.get_target_hardware("cuda_sm86", "tsm_memory_size") == 49152
    assert target_registry.get_target_hardware("cuda_sm86", "tlm1_memory_size") == 0
    assert target_registry.is_arch_op_supported("cuda_sm86", "arch.get_thread_id") is True
    assert target_registry.is_arch_op_supported("cuda_sm86", "arch.launch") is True
    assert target_registry.is_arch_op_supported("cuda_sm86", "arch.launch_kernel") is False


def test_cuda_sm86_target_loads_from_public_targets_directory() -> None:
    """验证公开目录加载入口能读取 cuda_sm86 target。

    功能说明:
    - 使用 `load_targets(...)` 读取仓库 target 目录。
    - 证明 `cuda_sm86` 与 `npu_demo` 一样来自文件化 target 真源。

    使用示例:
    - pytest -q test/target/test_cuda_sm86_registry.py -k public_targets_directory
    """

    loaded = target_registry.load_targets(Path("kernel_gen/target/targets"))

    assert "cuda_sm86" in loaded
    assert loaded["cuda_sm86"].hardware["thread_num"] == 256
