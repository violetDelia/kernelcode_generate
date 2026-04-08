"""nn_to_kernel softmax expectation.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 覆盖 residual `nn.softmax` 直接进入 `LowerNnToKernelPass` 的固定失败短语。
- 同时覆盖两条入口：
  - 直接构造 dialect `nn.softmax` op。
  - 通过 `build_func_op` + operation 层 `softmax(...)` helper 生成 raw `nn.softmax`。

使用示例:
- `PYTHONPATH=. python expectation/pass/lowing/nn_to_kernel/softmax.py`

关联文件:
- spec: [`spec/operation/nn.md`](spec/operation/nn.md)
- spec: [`spec/pass/lowering/nn_to_kernel.md`](spec/pass/lowering/nn_to_kernel.md)
- test: [`test/pass/test_lowering_nn_to_kernel.py`](test/pass/test_lowering_nn_to_kernel.py)
- test: [`test/pass/test_pass_manager.py`](test/pass/test_pass_manager.py)
- 功能实现: [`kernel_gen/passes/lowering/nn_to_kernel.py`](kernel_gen/passes/lowering/nn_to_kernel.py)
"""

from __future__ import annotations

import sys
from pathlib import Path
from collections.abc import Callable

import pytest
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntAttr, ModuleOp, Region, f32
from xdsl.ir import Attribute, Block, Operation

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType, NnSoftmaxOp
from kernel_gen.dsl.mlir_gen import build_func_op
from kernel_gen.operation.nn import softmax
from kernel_gen.passes.lowering.nn_to_kernel import LowerNnToKernelError, LowerNnToKernelPass
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.type import NumericType

_EXPECTED_ERROR = "LowerNnToKernelError: residual nn.softmax must be decomposed before lower-nn-to-kernel"


def _make_space(space: str = "global") -> NnMemorySpaceAttr:
    """构造 `nn.space` attribute。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 为 softmax expectation 统一生成 `NnMemorySpaceAttr`。

    使用示例:
    - `_make_space("global")`

    关联文件:
    - spec: spec/operation/nn.md
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    return NnMemorySpaceAttr.from_name(space)


def _make_memory_type(
    shape: tuple[int, ...] = (2, 3),
    stride: tuple[int, ...] = (3, 1),
    element_type: Attribute = f32,
    space: str = "global",
) -> NnMemoryType:
    """构造默认 `nn.memory` 类型。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 生成用于 `nn.softmax` expectation 的 memory type。

    使用示例:
    - `_make_memory_type()`

    关联文件:
    - spec: spec/operation/nn.md
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    return NnMemoryType(
        ArrayAttr([IntAttr(value) for value in shape]),
        ArrayAttr([IntAttr(value) for value in stride]),
        element_type,
        _make_space(space),
    )


def _tensor_arg(shape: list[int | str], dtype: NumericType = NumericType.Float32) -> Memory:
    """构造 operation 层 `build_func_op` 参数对象。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 将 `shape/dtype` 转为 `Memory`，用于 `build_func_op` 生成 IR。

    使用示例:
    - `_tensor_arg([2, 3], NumericType.Float32)`

    关联文件:
    - spec: spec/operation/nn.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/dsl/mlir_gen.py
    """

    return Memory(shape, dtype)


def _build_module(
    arg_types: list[Attribute],
    result_type: NnMemoryType,
    op_builder: Callable[[Block], list[Operation]],
) -> ModuleOp:
    """构造包含单个 func 的 module。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 按顺序插入 ops 并追加 `func.return`。

    使用示例:
    - module = _build_module([input_type], result_type, lambda block: [nn_op])

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    block = Block(arg_types=arg_types)
    ops = op_builder(block)
    if not ops:
        raise ValueError("op_builder must return at least one operation")
    for op in ops:
        block.add_op(op)
    block.add_op(func.ReturnOp(ops[-1].results[0]))
    func_type = FunctionType.from_lists(arg_types, [result_type])
    func_op = func.FuncOp("main", func_type, Region(block))
    return ModuleOp([func_op])


def _assert_softmax_error(exc: BaseException) -> None:
    """断言 residual softmax 的固定失败短语。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 校验错误类型与错误短语，避免误吞其他异常路径。

    使用示例:
    - _assert_softmax_error(exc)

    关联文件:
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    assert isinstance(exc, LowerNnToKernelError)
    assert f"{type(exc).__name__}: {exc}" == _EXPECTED_ERROR


def main() -> None:
    """运行 expectation 用例集合。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - CASE-1：dialect 侧直接构造 `nn.softmax`，验证固定失败短语。
    - CASE-2：operation helper 侧生成 raw `nn.softmax`，验证固定失败短语。

    使用示例:
    - `PYTHONPATH=. python expectation/pass/lowing/nn_to_kernel/softmax.py`

    关联文件:
    - spec: spec/operation/nn.md
    - spec: spec/pass/lowering/nn_to_kernel.md
    - test: test/pass/test_lowering_nn_to_kernel.py
    - 功能实现: kernel_gen/passes/lowering/nn_to_kernel.py
    """

    print("[CASE-1] residual nn.softmax 直接进入 LowerNnToKernelPass 必须拒绝。")
    input_type = _make_memory_type()
    result_type = _make_memory_type()
    space = _make_space("global")
    module = _build_module(
        [input_type],
        result_type,
        lambda block: [NnSoftmaxOp(block.args[0], result_type, axis=1, space=space)],
    )
    print("[BEFORE]")
    print(module)
    with pytest.raises(LowerNnToKernelError) as err:
        LowerNnToKernelPass().run(module)
    _assert_softmax_error(err.value)
    print(_EXPECTED_ERROR)

    print("[CASE-2] public chain 生成 raw nn.softmax 后必须拒绝。")

    def softmax_direct(value: "Tensor[f32, 2, 3]") -> "Tensor[f32, 2, 3]":
        return softmax(value)

    module = ModuleOp([build_func_op(softmax_direct, _tensor_arg([2, 3], NumericType.Float32))])
    raw_ir = str(module)
    assert "nn.softmax" in raw_ir
    print("[BEFORE]")
    print(raw_ir)
    with pytest.raises(LowerNnToKernelError) as err:
        LowerNnToKernelPass().run(module)
    _assert_softmax_error(err.value)
    print(_EXPECTED_ERROR)


if __name__ == "__main__":
    main()
