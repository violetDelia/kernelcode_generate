# [immutable-file]
"""default lowering pipeline expectation。

创建者: 大闸蟹
最后一次更改: 守护最好的爱莉希雅

功能说明:
- 验证公开 `build_default_lowering_pipeline()` 会固定执行 `DecompassPass -> NnLoweringPass -> BufferResultsToOutParamsPass -> LowerDmaMemoryHierarchyPass`。
- 验证这条 pipeline 对 raw `nn.add` memory-return 函数的黑盒效果：最终产物使用前置 out 参数，并收口为 `dma.slice / kernel.binary_elewise / dma.deslice` 链。
- 验证非法 `nn.softmax(axis 越界)` 会在 `decompass` 阶段显式失败。

使用示例:
- `PYTHONPATH=. python expectation/pass/pipeline/default_lowering.py`

关联文件:
- spec: [`spec/pass/pass_manager.md`](spec/pass/pass_manager.md)
- spec: [`spec/pass/pipeline/default_lowering.md`](spec/pass/pipeline/default_lowering.md)
- test: [`test/pass/test_pass_manager.py`](test/pass/test_pass_manager.py)
- test: [`test/pass/test_pipeline_default_lowering.py`](test/pass/test_pipeline_default_lowering.py)
- 功能实现: [`kernel_gen/passes/pass_manager.py`](kernel_gen/passes/pass_manager.py)
- 功能实现: [`kernel_gen/passes/pipeline/default_lowering.py`](kernel_gen/passes/pipeline/default_lowering.py)
"""

from __future__ import annotations

from contextlib import contextmanager
import importlib
from pathlib import Path
import sys

import pytest
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, FunctionType, IntAttr, ModuleOp, f32
from xdsl.ir import Block, Region

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.case_runner import raise_if_failures, run_case
from kernel_gen.dialect.dma import DmaDesliceOp, DmaSliceOp
from kernel_gen.dialect.nn import NnAddOp, NnMemorySpaceAttr, NnMemoryType, NnSoftmaxOp
from kernel_gen.dialect.kernel import KernelBinaryElewiseOp
from kernel_gen.passes.decompass import DecompassError
from kernel_gen.passes.lowering import BufferResultsToOutParamsError
from kernel_gen.passes.pass_manager import PassManager

try:
    from kernel_gen.passes.pipeline import build_default_lowering_pipeline
except ImportError:
    from kernel_gen.passes.pass_manager import (
        build_default_lowering_pass_manager as build_default_lowering_pipeline,
    )
from kernel_gen.target import registry as target_registry


def _make_memory_type() -> NnMemoryType:
    """构造 pipeline expectation 用的 `nn.memory` 类型。

    创建者: 大闸蟹
    最后一次更改: 大闸蟹

    功能说明:
    - 为默认 lowering pipeline expectation 统一生成 `[2, 2] / f32 / global` 的 memory 类型。

    使用示例:
    - `mem = _make_memory_type()`

    关联文件:
    - spec: [`spec/pass/pass_manager.md`](spec/pass/pass_manager.md)
    - test: [`test/pass/test_pass_manager.py`](test/pass/test_pass_manager.py)
    - 功能实现: [`expectation/pass/pipeline/default_lowering.py`](expectation/pass/pipeline/default_lowering.py)
    """

    return NnMemoryType(
        ArrayAttr([IntAttr(2), IntAttr(2)]),
        ArrayAttr([IntAttr(2), IntAttr(1)]),
        f32,
        NnMemorySpaceAttr.from_name("global"),
    )


def _ensure_default_lowering_target_registered() -> str:
    """注册 default lowering expectation 使用的临时 target。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 为 `LowerDmaMemoryHierarchyPass` 提供最小可用的 `SM/LM` 容量配置。
    - 仅用于 expectation 黑盒验证，不改变正式 target 合同。

    使用示例:
    - `target_name = _ensure_default_lowering_target_registered()`

    关联文件:
    - spec: [`spec/pass/pipeline/default_lowering.md`](spec/pass/pipeline/default_lowering.md)
    - test: [`test/pass/test_pipeline_default_lowering.py`](test/pass/test_pipeline_default_lowering.py)
    - 功能实现: [`expectation/pass/pipeline/default_lowering.py`](expectation/pass/pipeline/default_lowering.py)
    """

    name = "expect_default_lowering_pipeline"
    spec = target_registry.TargetSpec(
        name=name,
        arch_supported_ops=None,
        arch_unsupported_ops=set(),
        hardware={
            "thread_num": 1,
            "block_num": 1,
            "subthread_num": 1,
            "sm_memory_size": 1024,
            "lm_memory_size": 1024,
            "tsm_memory_size": 0,
            "tlm1_memory_size": 0,
            "tlm2_memory_size": 0,
            "tlm3_memory_size": 0,
        },
    )
    try:
        target_registry.register_target(spec)
    except ValueError as exc:
        if "target already registered" not in str(exc):
            raise
    return name


@contextmanager
def _use_default_lowering_target():
    """在 expectation 运行期间设置临时 target。"""

    previous_target = target_registry._get_current_target()
    target_name = _ensure_default_lowering_target_registered()
    target_registry._set_current_target(target_name)
    try:
        yield
    finally:
        target_registry._set_current_target(previous_target)


def _case_0() -> None:
    print("[CASE-0] 失败边界：pass 顺序错误时必须显式失败。")
    lowering_module = importlib.import_module("kernel_gen.passes.lowering")
    nn_lowering_pass = lowering_module.NnLoweringPass
    buffer_results_to_out_params_pass = lowering_module.BufferResultsToOutParamsPass
    misordered = PassManager(name="misordered")
    misordered.add_pass(buffer_results_to_out_params_pass())
    misordered.add_pass(nn_lowering_pass())
    with pytest.raises(
        ValueError,
        match="buffer-results-to-out-params requires lowered IR after lower-nn or lower-nn-to-kernel",
    ):
        misordered.run("bad")  # type: ignore[arg-type]


def _case_1() -> None:
    print("[CASE-1] 默认 lowering pipeline 顺序固定为 DecompassPass -> NnLoweringPass -> BufferResultsToOutParamsPass -> LowerDmaMemoryHierarchyPass。")
    lowering_module = importlib.import_module("kernel_gen.passes.lowering")
    decompass_module = importlib.import_module("kernel_gen.passes.decompass")
    decompass_pass = decompass_module.DecompassPass
    nn_lowering_pass = lowering_module.NnLoweringPass
    buffer_results_to_out_params_pass = lowering_module.BufferResultsToOutParamsPass
    lower_dma_memory_hierarchy_pass = lowering_module.LowerDmaMemoryHierarchyPass
    order: list[str] = []
    original_decompass = decompass_pass.run
    original_lower = nn_lowering_pass.run
    original_buffer = buffer_results_to_out_params_pass.run
    original_dma = lower_dma_memory_hierarchy_pass.run

    def _record_decompass(self: object, target: object) -> object:
        order.append("DecompassPass")
        return original_decompass(self, target)

    def _record_lower(self: object, target: object) -> object:
        order.append("NnLoweringPass")
        return original_lower(self, target)

    def _record_buffer(self: object, target: object) -> object:
        order.append("buffer-results-to-out-params")
        return original_buffer(self, target)

    def _record_dma(self: object, target: object) -> object:
        order.append("lower-dma-memory-hierarchy")
        return original_dma(self, target)

    decompass_pass.run = _record_decompass
    nn_lowering_pass.run = _record_lower
    buffer_results_to_out_params_pass.run = _record_buffer
    lower_dma_memory_hierarchy_pass.run = _record_dma
    try:
        mem = _make_memory_type()
        block = Block(arg_types=[mem, mem])
        add_op = NnAddOp(block.args[0], block.args[1], mem, NnMemorySpaceAttr.from_name("global"))
        block.add_ops([add_op, func.ReturnOp(add_op.result)])
        func_op = func.FuncOp("add_direct", ([mem, mem], [mem]), Region(block))
        module = ModuleOp([func_op])
        pm = build_default_lowering_pipeline()
        pm.run(module)
    finally:
        decompass_pass.run = original_decompass
        nn_lowering_pass.run = original_lower
        buffer_results_to_out_params_pass.run = original_buffer
        lower_dma_memory_hierarchy_pass.run = original_dma

    assert order == [
        "DecompassPass",
        "NnLoweringPass",
        "buffer-results-to-out-params",
        "lower-dma-memory-hierarchy",
    ]


def _case_2() -> None:
    print("[CASE-2] 默认 lowering pipeline 黑盒效果：memory return 改写为前置 out 参数，并经 dma memory hierarchy 收口为 slice/kernel.binary_elewise/deslice 链。")
    mem = _make_memory_type()
    block = Block(arg_types=[mem, mem])
    add_op = NnAddOp(block.args[0], block.args[1], mem, NnMemorySpaceAttr.from_name("global"))
    block.add_ops([add_op, func.ReturnOp(add_op.result)])
    func_op = func.FuncOp("add_direct", ([mem, mem], [mem]), Region(block))
    module = ModuleOp([func_op])
    pm = build_default_lowering_pipeline()
    pm.run(module)
    print("[AFTER]")
    print(module)
    func_op = next(op for op in module.ops if isinstance(op, func.FuncOp))
    body_ops = list(func_op.body.block.ops)
    kernel_binary = next(op for op in body_ops if isinstance(op, KernelBinaryElewiseOp))
    slices = [op for op in body_ops if isinstance(op, DmaSliceOp)]
    deslices = [op for op in body_ops if isinstance(op, DmaDesliceOp)]
    return_op = next(op for op in body_ops if isinstance(op, func.ReturnOp))
    assert not any(isinstance(op, NnAddOp) for op in body_ops), "lowering 后不应残留 nn.add"
    assert len(list(func_op.function_type.inputs)) == 3
    assert list(func_op.function_type.outputs) == []
    assert func_op.arg_attrs.data[0].data["name"].data == "arg0"
    assert len(slices) >= 2
    assert len(deslices) >= 1
    assert kernel_binary.attributes["space"] == NnMemorySpaceAttr.from_name("local")
    assert getattr(kernel_binary.attributes["kind"], "data", None) == "add"
    assert len(return_op.arguments) == 0


def _case_3() -> None:
    print("[CASE-3] 失败边界：非法 nn.softmax axis 必须在 decompass 阶段显式失败。")
    mem = _make_memory_type()
    space = NnMemorySpaceAttr.from_name("global")
    softmax_block = Block(arg_types=[mem])
    softmax_op = NnSoftmaxOp(softmax_block.args[0], mem, axis=2, space=space)
    softmax_block.add_ops([softmax_op, func.ReturnOp(softmax_op.result)])
    softmax_func = func.FuncOp(
        "softmax_direct",
        FunctionType.from_lists([mem], [mem]),
        Region(softmax_block),
    )
    softmax_module = ModuleOp([softmax_func])
    print("[BEFORE]")
    print(softmax_module)
    pm = build_default_lowering_pipeline()
    try:
        pm.run(softmax_module)
    except DecompassError as exc:
        print(f"[EXPECTED-FAILURE] {type(exc).__name__}: {exc}")
        assert "normalized axis out of range" in str(exc)
    else:
        raise AssertionError("out-of-range axis must be rejected before lowering continues")


def _case_4() -> None:
    print("[CASE-4] 失败边界：external declaration 的 memory-return 必须显式失败。")
    mem = _make_memory_type()
    external_func = func.FuncOp("external_memory_result", FunctionType.from_lists([mem], [mem]))
    external_module = ModuleOp([external_func])
    print("[BEFORE]")
    print(external_module)
    pm = build_default_lowering_pipeline()
    with pytest.raises(BufferResultsToOutParamsError, match="external declaration"):
        pm.run(external_module)
    print("[EXPECTED-FAILURE] BufferResultsToOutParamsError: external declaration")


def main() -> None:
    failures: list[tuple[str, BaseException]] = []
    with _use_default_lowering_target():
        run_case(failures, "CASE-0", _case_0)
        run_case(failures, "CASE-1", _case_1)
        run_case(failures, "CASE-2", _case_2)
        run_case(failures, "CASE-3", _case_3)
        run_case(failures, "CASE-4", _case_4)
    raise_if_failures("default lowering pipeline expectation", failures)


if __name__ == "__main__":
    main()
