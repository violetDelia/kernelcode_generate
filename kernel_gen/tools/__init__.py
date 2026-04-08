"""tools package.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 暴露面向脚本与测试的轻量工具模块（例如 ircheck）。

使用示例:
- from kernel_gen.tools.ircheck import run_ircheck_text
- result = run_ircheck_text(\"\"\"// COMPILE_ARGS: --pass no-op
// CHECK: builtin.module

builtin.module {}
\"\"\")
- assert result.ok is True

关联文件:
- spec: [spec/tools/ircheck.md](spec/tools/ircheck.md)
- test: [test/tools/test_ircheck_runner.py](test/tools/test_ircheck_runner.py)
- 功能实现: [kernel_gen/tools/ircheck.py](kernel_gen/tools/ircheck.py)
"""

__all__ = []

