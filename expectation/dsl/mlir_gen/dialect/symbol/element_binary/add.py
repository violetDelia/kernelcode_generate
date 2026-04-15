"""symbol.add expectation.

创建者: 大闸蟹
最后一次更改: 小李飞刀

功能说明:
- 使用 `mlir_gen_compare_text(...)` 直接比较完整 `builtin.module`。
- 锁定 `lhs + rhs` 的目标公开合同：应生成显式 `symbol.add`。

使用示例:
- `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py`

关联文件:
- spec: [`spec/dsl/mlir_gen.md`](spec/dsl/mlir_gen.md)
- spec: [`spec/dialect/symbol.md`](spec/dialect/symbol.md)
- spec: [`spec/tools/mlir_gen_compare.md`](spec/tools/mlir_gen_compare.md)
- test: [`test/dsl/test_mlir_gen.py`](test/dsl/test_mlir_gen.py)
- test: [`test/tools/test_mlir_gen_compare.py`](test/tools/test_mlir_gen_compare.py)
- 功能实现: [`kernel_gen/dsl/mlir_gen/__init__.py`](kernel_gen/dsl/mlir_gen/__init__.py)
- 功能实现: [`kernel_gen/tools/mlir_gen_compare.py`](kernel_gen/tools/mlir_gen_compare.py)
"""

# Case 列表:
# - CASE-1: symbol const 正向例子：静态整数应在函数体内 materialize 为 `symbol.const`，再生成显式 `symbol.add`。
# - CASE-2: symbol 正向例子：`lhs + rhs` 的符号输入应生成显式 `symbol.add`。
# - CASE-3: symbol.to_float 正向例子：`float(lhs + rhs)` 应先生成 `symbol.add`，再生成显式 `symbol.to_float`。

from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) in sys.path:
    sys.path.remove(str(CURRENT_DIR))

REPO_ROOT = Path(__file__).resolve().parents[6]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.case_runner import raise_if_failures, run_case
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.tools.mlir_gen_compare import mlir_gen_compare_text

# CASE-1 IR：symbol const 正向例子：静态整数应在函数体内 materialize 为 `symbol.const`，再生成显式 `symbol.add`。
CASE_1_IR = """builtin.module {
  func.func @add_case_1() -> !symbol.int<"9"> {
    %0 = symbol.const 4 : !symbol.int<"4">
    %1 = symbol.const 5 : !symbol.int<"5">
    %2 = symbol.add %0, %1 : !symbol.int<"4">, !symbol.int<"5"> -> !symbol.int<"9">
    func.return %2 : !symbol.int<"9">
  }
}"""

CASE_1_RUNTIME_ARGS = ()


# add_case_1
# 创建者: 大闸蟹
# 最后一次更改: 小李飞刀
# 功能说明:
# - 提供 `4 + 5` 的最小 DSL 函数体，验证静态整数会先 materialize 为 `symbol.const`，再生成 `symbol.add`。
# 使用示例:
# - `mlir_gen_compare_text(fn=add_case_1, runtime_args=CASE_1_RUNTIME_ARGS, config=None, mlir_text=CASE_1_IR)`
# 关联文件:
# - spec: [`spec/dsl/mlir_gen.md`](spec/dsl/mlir_gen.md)
# - test: [`test/dsl/test_mlir_gen.py`](test/dsl/test_mlir_gen.py)
# - 功能实现: [`expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py`](expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py)
# - 功能实现: [`kernel_gen/dsl/mlir_gen/__init__.py`](kernel_gen/dsl/mlir_gen/__init__.py)
def add_case_1():
    return 4 + 5


# CASE-2 IR：symbol 正向例子：`lhs + rhs` 的符号输入应生成显式 `symbol.add`。
CASE_2_IR = """builtin.module {
  func.func @add_case_2(%0 : !symbol.int<"M">, %1 : !symbol.int<"N">) -> !symbol.int<"M + N"> {
    %2 = symbol.add %0, %1 : !symbol.int<"M">, !symbol.int<"N"> -> !symbol.int<"M + N">
    func.return %2 : !symbol.int<"M + N">
  }
}"""

CASE_2_RUNTIME_ARGS = (SymbolDim("M"), SymbolDim("N"))


# add_case_2
# 创建者: 大闸蟹
# 最后一次更改: 小李飞刀
# 功能说明:
# - 提供 `lhs + rhs` 的最小 DSL 函数体，验证两个符号输入会直接 lowering 为显式 `symbol.add`。
# 使用示例:
# - `mlir_gen_compare_text(fn=add_case_2, runtime_args=CASE_2_RUNTIME_ARGS, config=None, mlir_text=CASE_2_IR)`
# 关联文件:
# - spec: [`spec/dialect/symbol.md`](spec/dialect/symbol.md)
# - test: [`test/dsl/test_mlir_gen.py`](test/dsl/test_mlir_gen.py)
# - 功能实现: [`expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py`](expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py)
# - 功能实现: [`kernel_gen/dsl/mlir_gen/__init__.py`](kernel_gen/dsl/mlir_gen/__init__.py)
def add_case_2(lhs, rhs):
    return lhs + rhs


# CASE-3 IR：symbol.to_float 正向例子：`float(lhs + rhs)` 应先生成 `symbol.add`，再生成显式 `symbol.to_float`。
CASE_3_IR = """builtin.module {
  func.func @add_case_3(%0 : !symbol.int<"M">, %1 : !symbol.int<"N">) -> f32 {
    %2 = symbol.add %0, %1 : !symbol.int<"M">, !symbol.int<"N"> -> !symbol.int<"M + N">
    %3 = symbol.to_float %2 : !symbol.int<"M + N"> -> f32
    func.return %3 : f32
  }
}"""

CASE_3_RUNTIME_ARGS = (SymbolDim("M"), SymbolDim("N"))


# add_case_3
# 创建者: 大闸蟹
# 最后一次更改: 小李飞刀
# 功能说明:
# - 提供 `float(lhs + rhs)` 的最小 DSL 函数体，验证先生成 `symbol.add`，再生成 `symbol.to_float`。
# 使用示例:
# - `mlir_gen_compare_text(fn=add_case_3, runtime_args=CASE_3_RUNTIME_ARGS, config=None, mlir_text=CASE_3_IR)`
# 关联文件:
# - spec: [`spec/dialect/symbol.md`](spec/dialect/symbol.md)
# - test: [`test/dsl/test_mlir_gen.py`](test/dsl/test_mlir_gen.py)
# - 功能实现: [`expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py`](expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py)
# - 功能实现: [`kernel_gen/dsl/mlir_gen/__init__.py`](kernel_gen/dsl/mlir_gen/__init__.py)
def add_case_3(lhs, rhs):
    return float(lhs + rhs)


def _case_1_true() -> None:
    """断言静态整数相加样例符合 `symbol.const + symbol.add` 合同。

    创建者: 大闸蟹
    最后一次更改: 小李飞刀

    功能说明:
    - 打印 CASE-1 说明并调用 `mlir_gen_compare_text(...)` 校验静态整数样例的完整 IR 文本。

    使用示例:
    - `_case_1_true()`

    关联文件:
    - spec: [`spec/tools/mlir_gen_compare.md`](spec/tools/mlir_gen_compare.md)
    - test: [`test/tools/test_mlir_gen_compare.py`](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [`expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py`](expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py)
    - 功能实现: [`kernel_gen/tools/mlir_gen_compare.py`](kernel_gen/tools/mlir_gen_compare.py)
    """

    print("[CASE-1] symbol const 正向例子：4 + 5 应在函数体内 materialize 为 symbol.const，并生成 symbol.add")
    ok = mlir_gen_compare_text(fn=add_case_1, runtime_args=CASE_1_RUNTIME_ARGS, config=None, mlir_text=CASE_1_IR)
    assert ok is True


def _case_2_true() -> None:
    """断言符号整数相加样例符合 `symbol.add` 合同。

    创建者: 大闸蟹
    最后一次更改: 小李飞刀

    功能说明:
    - 打印 CASE-2 说明并校验 `lhs + rhs` 会生成显式 `symbol.add`。

    使用示例:
    - `_case_2_true()`

    关联文件:
    - spec: [`spec/tools/mlir_gen_compare.md`](spec/tools/mlir_gen_compare.md)
    - test: [`test/tools/test_mlir_gen_compare.py`](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [`expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py`](expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py)
    - 功能实现: [`kernel_gen/tools/mlir_gen_compare.py`](kernel_gen/tools/mlir_gen_compare.py)
    """

    print("[CASE-2] symbol 正向例子：lhs + rhs -> symbol.add")
    ok = mlir_gen_compare_text(fn=add_case_2, runtime_args=CASE_2_RUNTIME_ARGS, config=None, mlir_text=CASE_2_IR)
    assert ok is True


def _case_3_true() -> None:
    """断言符号相加转 float 样例符合 `symbol.add + symbol.to_float` 合同。

    创建者: 大闸蟹
    最后一次更改: 小李飞刀

    功能说明:
    - 打印 CASE-3 说明并校验 `float(lhs + rhs)` 的完整 IR 文本。

    使用示例:
    - `_case_3_true()`

    关联文件:
    - spec: [`spec/tools/mlir_gen_compare.md`](spec/tools/mlir_gen_compare.md)
    - test: [`test/tools/test_mlir_gen_compare.py`](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [`expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py`](expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py)
    - 功能实现: [`kernel_gen/tools/mlir_gen_compare.py`](kernel_gen/tools/mlir_gen_compare.py)
    """

    print("[CASE-3] symbol.to_float 正向例子：float(lhs + rhs) -> symbol.add + symbol.to_float")
    ok = mlir_gen_compare_text(fn=add_case_3, runtime_args=CASE_3_RUNTIME_ARGS, config=None, mlir_text=CASE_3_IR)
    assert ok is True


def main() -> None:
    """运行 `symbol.add` expectation 的全部公开 case。

    创建者: 大闸蟹
    最后一次更改: 小李飞刀

    功能说明:
    - 顺序执行静态整数、符号整数、`symbol.to_float` 三个正向合同样例。
    - 汇总失败 case，并以统一错误消息暴露给目录入口。

    使用示例:
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py`

    关联文件:
    - spec: [`spec/dialect/symbol.md`](spec/dialect/symbol.md)
    - test: [`test/dsl/test_mlir_gen.py`](test/dsl/test_mlir_gen.py)
    - 功能实现: [`expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py`](expectation/dsl/mlir_gen/dialect/symbol/element_binary/add.py)
    - 功能实现: [`expectation/utils/case_runner.py`](expectation/utils/case_runner.py)
    """

    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-1", _case_1_true)
    run_case(failures, "CASE-2", _case_2_true)
    run_case(failures, "CASE-3", _case_3_true)
    raise_if_failures("dsl mlir_gen symbol.add expectation", failures)


if __name__ == "__main__":
    main()
