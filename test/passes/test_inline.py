"""inline pass tests.


功能说明:
- 覆盖 kernel_gen/passes/inline.py 的 helper 内联与 private helper 清理行为。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- `pytest -q test/passes/test_inline.py`

使用示例:
- pytest -q test/passes/test_inline.py

关联文件:
- 功能实现: kernel_gen/passes/inline.py
- Spec 文档: spec/pass/inline.md
- 测试文件: test/passes/test_inline.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xdsl.context import Context
from xdsl.dialects import arith, func
from xdsl.dialects.builtin import FunctionType, IntegerAttr, ModuleOp, i32
from xdsl.ir import Block, Region

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.error import KernelCodeError
from kernel_gen.passes.inline import InlinePass


def _make_private_inline_module() -> ModuleOp:
    """构造一个可被 inline 展平的最小 module。


    功能说明:
    - helper 先做一次加法，再返回结果，便于验证 inline 会真实克隆 helper op。
    - caller 通过 `func.call` 引用 helper，便于验证 call 会被展平并删除。

    使用示例:
    - module = _make_private_inline_module()

    关联文件:
    - spec: [spec/pass/inline.md](../../../spec/pass/inline.md)
    - test: [test/passes/test_inline.py](../../../test/passes/test_inline.py)
    - 功能实现: [kernel_gen/passes/inline.py](../../../kernel_gen/passes/inline.py)
    """

    helper_block = Block(arg_types=[i32])
    const_one = arith.ConstantOp(IntegerAttr(1, i32))
    add_one = arith.AddiOp(helper_block.args[0], const_one.result)
    helper_block.add_ops([const_one, add_one, func.ReturnOp(add_one.result)])
    helper = func.FuncOp(
        "helper",
        FunctionType.from_lists([i32], [i32]),
        Region(helper_block),
        visibility="private",
    )

    caller_block = Block(arg_types=[i32])
    call_op = func.CallOp("helper", [caller_block.args[0]], [i32])
    caller_block.add_ops([call_op, func.ReturnOp(call_op.results[0])])
    caller = func.FuncOp(
        "caller",
        FunctionType.from_lists([i32], [i32]),
        Region(caller_block),
    )

    return ModuleOp([helper, caller])


def test_inline_expands_private_helper_and_cleans_dead_helper() -> None:
    module = _make_private_inline_module()

    InlinePass().apply(Context(), module)

    funcs = [op for op in module.ops if isinstance(op, func.FuncOp)]
    assert [func_op.sym_name.data for func_op in funcs] == ["caller"]

    caller = funcs[0]
    caller_ops = list(caller.body.block.ops)
    assert not any(isinstance(op, func.CallOp) for op in caller_ops)
    assert any(isinstance(op, arith.ConstantOp) for op in caller_ops)
    assert any(isinstance(op, arith.AddiOp) for op in caller_ops)
    assert isinstance(caller_ops[-1], func.ReturnOp)


def test_inline_rejects_non_module() -> None:
    with pytest.raises(KernelCodeError, match=r"^InlineError: module must be builtin.module$"):
        InlinePass().apply(Context(), object())  # type: ignore[arg-type]
