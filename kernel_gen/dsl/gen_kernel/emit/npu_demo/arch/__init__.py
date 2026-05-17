"""npu_demo arch emit backend package.

功能说明:
- 导入 npu_demo target 下 arch op 的 emit 注册实现。
- 包导入本身只触发注册副作用，不提供额外公开 API。

API 列表:
- 无（仅 target 私有注册实现）

使用示例:
- import kernel_gen.dsl.gen_kernel.emit.npu_demo.arch

关联文件:
- spec: spec/dsl/gen_kernel/emit/npu_demo/arch/__init__.md
- test: test/dsl/gen_kernel/emit/test_package.py
- 功能实现: kernel_gen/dsl/gen_kernel/emit/npu_demo/arch/__init__.py
"""

from . import get_block_id, get_dynamic_memory, get_thread_id, get_thread_num  # noqa: F401
