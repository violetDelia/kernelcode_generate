"""tile pass public tests package.


功能说明:
- 承接 `kernel_gen.passes.tile` family 的公开 API 测试。
- 只覆盖 package/registry/pattern/pass 的公开合同，不再测试 `contract`、`rewrite` 等非公开 helper。

使用示例:
- pytest -q test/passes/tile

关联文件:
- spec: [spec/pass/tile/README.md](../../../spec/pass/tile/README.md)
- test: [test/passes/tile/test_package.py](../../../test/passes/tile/test_package.py)
- test: [test/passes/tile/test_analysis.py](../../../test/passes/tile/test_analysis.py)
- test: [test/passes/tile/test_elewise.py](../../../test/passes/tile/test_elewise.py)
- test: [test/passes/tile/test_reduce.py](../../../test/passes/tile/test_reduce.py)
"""

