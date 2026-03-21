"""pass package.

创建者: 李白
最后一次更改: 李白

功能说明:
- 暴露 Pass 管理相关实现。

使用示例:
- import importlib
- pass_module = importlib.import_module("kernel_gen.pass.pass_manager")
- Pass, PassManager = pass_module.Pass, pass_module.PassManager

关联文件:
- spec: spec/pass/pass_manager.md
- test: test/pass/test_pass_manager.py
- 功能实现: kernel_gen/pass/pass_manager.py
"""

from .pass_manager import Pass, PassManager

__all__ = ["Pass", "PassManager"]
