# [immutable-file]
"""`buffer_results_to_out_params` 失败边界 expectation。

创建者: 守护最好的爱莉希雅
最后一次更改: 守护最好的爱莉希雅

功能说明:
- 使用 Python 级 expectation 锁定 `BufferResultsToOutParamsPass` 的显式失败边界。
- 覆盖 external declaration、multi-block、half-rewritten callsite mismatch 三类
  当前 spec 已公开承认的拒绝场景。

使用示例:
- `PYTHONPATH=. python expectation/pass/buffer_results_to_out_params/reject_cases.py`

关联文件:
- spec: [`spec/pass/lowering/buffer_results_to_out_params.md`](../../../spec/pass/lowering/buffer_results_to_out_params.md)
- test: [`test/pass/test_buffer_results_to_out_params.py`](../../../test/pass/test_buffer_results_to_out_params.py)
- 功能实现: [`expectation/pass/buffer_results_to_out_params/reject_cases.py`](../../../expectation/pass/buffer_results_to_out_params/reject_cases.py)
- 功能实现: [`kernel_gen/passes/lowering/buffer_results_to_out_params.py`](../../../kernel_gen/passes/lowering/buffer_results_to_out_params.py)
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest
from xdsl.dialects import func
from xdsl.dialects.builtin import FunctionType, ModuleOp
from xdsl.ir import Block, Region
from xdsl.parser import Parser

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from _shared import (
    print_case_actual_ir,
    random_dynamic_memory_spec,
    random_scalar_type_ir,
    random_static_memory_spec,
)
from expectation.utils.case_runner import raise_if_failures, run_case
from kernel_gen.context import build_default_context
from kernel_gen.passes.lowering.buffer_results_to_out_params import (
    BufferResultsToOutParamsError,
    BufferResultsToOutParamsPass,
)
from kernel_gen.tools.ircheck import run_ircheck_text


def _parse_module(text: str):
    """用仓库默认 dialect 上下文解析 IR 文本。"""

    return Parser(build_default_context(), text).parse_module()


def _case_1() -> None:
    """失败例：external declaration 必须显式拒绝。"""

    src = random_static_memory_spec("src")
    module = _parse_module(
        f"""
builtin.module {{
  func.func @external_memory_result(%0 : {src.type_ir} {{name = "src"}}) -> ({src.type_ir})
}}
"""
    )
    with pytest.raises(BufferResultsToOutParamsError, match="external declaration"):
        BufferResultsToOutParamsPass().run(module)


def _case_2() -> None:
    """失败例：multi-block function 必须显式拒绝。"""

    src = random_static_memory_spec("src")
    parsed = _parse_module(
        f"builtin.module {{ func.func @dummy(%0 : {src.type_ir} {{name = \"src\"}}) -> ({src.type_ir}) {{ func.return %0 : {src.type_ir} }} }}"
    )
    mem_type = parsed.ops.first.function_type.inputs.data[0]
    block0 = Block(arg_types=[mem_type])
    block0.add_op(func.ReturnOp(block0.args[0]))
    block1 = Block()
    func_op = func.FuncOp(
        "multi_block",
        FunctionType.from_lists([mem_type], [mem_type]),
        Region([block0, block1]),
        arg_attrs=parsed.ops.first.arg_attrs,
    )
    module = ModuleOp([func_op])
    with pytest.raises(BufferResultsToOutParamsError, match="single-block"):
        BufferResultsToOutParamsPass().run(module)


def _case_3() -> None:
    """失败例：half-rewritten callsite mismatch 必须显式拒绝。"""

    src = random_dynamic_memory_spec("src")
    module = _parse_module(
        f"""
builtin.module {{
  func.func @rewritten_callee(%0 : {src.type_ir} {{name = "arg0"}}, %1 : {src.type_ir} {{name = "src"}}) {{
    func.return
  }}
  func.func @caller(%0 : {src.type_ir} {{name = "src"}}) {{
    %1 = func.call @rewritten_callee(%0) : ({src.type_ir}) -> ({src.type_ir})
    func.return
  }}
}}
"""
    )
    with pytest.raises(BufferResultsToOutParamsError, match="half-rewritten"):
        BufferResultsToOutParamsPass().run(module)


def _case_4() -> None:
    """失败例：return arity mismatch 必须显式拒绝。"""

    src = random_static_memory_spec("src")
    module = _parse_module(
        f"""
builtin.module {{
  func.func @return_mismatch(%0 : {src.type_ir} {{name = "src"}}) -> ({src.type_ir}) {{
    func.return
  }}
}}
"""
    )
    with pytest.raises(BufferResultsToOutParamsError, match="return operand count"):
        BufferResultsToOutParamsPass().run(module)


def _case_5() -> None:
    """失败例：caller/callee 结果类型同 arity 不同类型时必须显式拒绝。"""

    src = random_dynamic_memory_spec("src")
    scalar_type = random_scalar_type_ir()
    wrong_scalar_type = "f32" if scalar_type == "i32" else "i32"
    scalar_literal = "1" if scalar_type == "i32" else "1.000000e+00"
    module = _parse_module(
        f"""
builtin.module {{
  func.func @reduce(%0 : {src.type_ir} {{name = "src"}}) -> ({src.type_ir}, {scalar_type}) {{
    %1 = arith.constant {scalar_literal} : {scalar_type}
    func.return %0, %1 : {src.type_ir}, {scalar_type}
  }}
  func.func @caller(%0 : {src.type_ir} {{name = "src"}}) {{
    %1, %2 = func.call @reduce(%0) : ({src.type_ir}) -> ({src.type_ir}, {wrong_scalar_type})
    func.return
  }}
}}
"""
    )
    with pytest.raises(BufferResultsToOutParamsError, match="half-rewritten"):
        BufferResultsToOutParamsPass().run(module)


CASE6_MEM = random_dynamic_memory_spec("src")
CASE7_MEM = random_static_memory_spec("src")


CASE_TEXT_HALF_REWRITTEN = f"""// COMPILE_ARGS: --pass buffer-results-to-out-params
// CASE: case-half-rewritten-ircheck: callee 已是 out-param ABI，但 caller 仍消费旧 memory result 时必须失败。

builtin.module {{
  func.func @rewritten_callee(%0 : {CASE6_MEM.type_ir} {{name = "arg0"}}, %1 : {CASE6_MEM.type_ir} {{name = "src"}}) {{
    func.return
  }}
  func.func @caller(%0 : {CASE6_MEM.type_ir} {{name = "src"}}) {{
    %1 = func.call @rewritten_callee(%0) : ({CASE6_MEM.type_ir}) -> ({CASE6_MEM.type_ir})
    func.return
  }}
}}
"""


CASE_TEXT_EXTERNAL_DECL = f"""// COMPILE_ARGS: --pass buffer-results-to-out-params
// CASE: case-external-declaration-ircheck: external declaration 含 memory result 时必须失败。

builtin.module {{
  func.func @external_memory_result(%0 : {CASE7_MEM.type_ir} {{name = "src"}}) -> ({CASE7_MEM.type_ir})
}}
"""


def _case_6() -> None:
    """失败例：half-rewritten 的文本输入必须报错。"""

    result = run_ircheck_text(
        CASE_TEXT_HALF_REWRITTEN,
        source_path="expectation/pass/buffer_results_to_out_params/reject_cases.py:case-6",
    )
    assert result.ok is False, "half-rewritten input should fail"
    assert result.message is not None and "half-rewritten" in result.message
    print_case_actual_ir("CASE-6", CASE_TEXT_HALF_REWRITTEN, result.message, fallback="half rewritten reject")


def _case_7() -> None:
    """失败例：external declaration 的文本输入必须报错。"""

    result = run_ircheck_text(
        CASE_TEXT_EXTERNAL_DECL,
        source_path="expectation/pass/buffer_results_to_out_params/reject_cases.py:case-7",
    )
    assert result.ok is False, "external declaration input should fail"
    assert result.message is not None and "external declaration" in result.message
    print_case_actual_ir("CASE-7", CASE_TEXT_EXTERNAL_DECL, result.message, fallback="external declaration reject")


def main() -> None:
    """运行失败边界 expectation。"""

    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "CASE-1", _case_1)
    run_case(failures, "CASE-2", _case_2)
    run_case(failures, "CASE-3", _case_3)
    run_case(failures, "CASE-4", _case_4)
    run_case(failures, "CASE-5", _case_5)
    run_case(failures, "CASE-6", _case_6)
    run_case(failures, "CASE-7", _case_7)
    raise_if_failures("buffer_results_to_out_params reject expectation", failures)


if __name__ == "__main__":
    main()
