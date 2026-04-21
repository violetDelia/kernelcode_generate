"""tile-reduce expectation package.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 标记当前 worktree 的 `expectation.pass.tile.reduce` 为优先包。
- 避免目录入口继续加载主仓中的旧 reduce expectation。

使用示例:
- `PYTHONPATH=/path/to/worktree:/home/lfr/kernelcode_generate python -m expectation.pass.tile.reduce`

关联文件:
- spec: [`spec/pass/lowering/tile_reduce.md`](spec/pass/lowering/tile_reduce.md)
- test: [`test/pass/test_lowering_tile_reduce.py`](test/pass/test_lowering_tile_reduce.py)
- 功能实现: [`expectation/pass/tile/reduce/__main__.py`](expectation/pass/tile/reduce/__main__.py)
"""
