"""Symbol-variable add-scalar expectation.

创建者: 榕
最后一次更改: 榕

功能说明:
- 验证两个整型标量做加法时，Python 侧结果与预期一致。

使用示例:
- python expectation/symbol_variable/add_scalar.py

关联文件:
- spec: spec/symbol_variable/symbol_dim.md
- test: test/symbol_variable/test_symbol_dim.py
- 功能实现: kernel_gen/symbol_variable/symbol_dim.py
"""

import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

lhs = random.randint(-1024, 1024)
rhs = random.randint(-1024, 1024)


def add(a, b):
    result = a + b
    return result


expected = lhs + rhs
out = add(lhs, rhs)

assert out == expected
