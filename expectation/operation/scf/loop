"""SCF loop expectation.
[immutable-file]
创建者: 榕
最后一次更改: 榕

功能说明:
- 验证 scf.loop 在整数和符号输入下的目标行为。

使用示例:
- python expectation/operation/scf/loop.py

关联文件:
- spec: spec/operation/scf.md
- test: test/operation/test_operation_scf.py
- 功能实现: kernel_gen/operation/scf.py
"""

from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) in sys.path:
    sys.path.remove(str(CURRENT_DIR))

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.operation.scf import LoopRange, loop
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from expectation.utils.random import get_random_alpha_string

# 纯整数输入应保持与 range 一致的半开区间语义。
assert list(loop(0, 4, 1)) == [0, 1, 2, 3]

# 含 SymbolDim 输入时应返回保留边界信息的 LoopRange。
s1 = get_random_alpha_string()
s2 = get_random_alpha_string()
s3 = get_random_alpha_string()

start = SymbolDim(s1)
end = SymbolDim(s2)
step = SymbolDim(s3)
loop_range = loop(start, end, step)

assert isinstance(loop_range, LoopRange)
assert loop_range.start is start
assert loop_range.end is end
assert loop_range.step is step
