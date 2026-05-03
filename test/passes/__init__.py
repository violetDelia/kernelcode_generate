"""pass 测试包入口。


功能说明:
- 提供 pass 相关测试的包入口，避免测试模块名冲突。

使用示例:
- pytest -q test/passes/lowering/nn_lowering/test_select.py

关联文件:
- spec: spec/pass/lowering/nn_lowering/spec.md
- test: test/passes/lowering/nn_lowering/test_select.py
- 功能实现: kernel_gen/passes/lowering/nn_lowering/select_cast_lowering.py
"""
