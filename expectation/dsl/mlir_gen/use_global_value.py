"""DSL reject-global-value expectation.
[immutable-file]
创建者: 榕
最后一次更改: 榕

功能说明:
- 验证 `build_func_op` 不允许函数体直接引用外部定义的值。
- 验证外部值不会被当作函数局部输入或合法常量参与 lowering。
- 验证该场景会返回明确的拒绝信息。

使用示例:
- python expectation/dsl/mlir_gen/use_global_value.py

关联文件:
- spec: spec/dsl/mlir_gen.md
- test: test/dsl/test_ast_visitor.py
- 功能实现: kernel_gen/dsl/mlir_gen.py
"""

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.random import get_random_int
from kernel_gen.dsl.ast_visitor import AstVisitorError
from kernel_gen.dsl.mlir_gen import build_func_op
GLOBAL_VALUE = get_random_int()


def use_global_value() -> int:
    return GLOBAL_VALUE


try:
    build_func_op(use_global_value)
except AstVisitorError as exc:
    assert "cannot use external value inside function body" in str(exc)
else:
    raise AssertionError("build_func_op should reject external values captured from outer scope")
