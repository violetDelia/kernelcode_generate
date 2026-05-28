"""template-name infer pass tests.


功能说明:
- 覆盖 `TemplateNameGraph`、constraint registry 与 `TemplateNameInferPass` 的公开合同。

使用示例:
- pytest -q test/passes/test_template_name_infer.py

关联文件:
- 功能实现: kernel_gen/passes/template_name/graph.py
- 功能实现: kernel_gen/passes/template_name/constraints.py
- 功能实现: kernel_gen/passes/template_name/infer.py
- Spec 文档: spec/pass/template_name_infer.md
- 测试文件: test/passes/test_template_name_infer.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, DictionaryAttr, FunctionType, ModuleOp, StringAttr, UnitAttr, i32, i8
from xdsl.ir import Block, Region

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.core.error import KernelCodeError
from kernel_gen.dialect.arch import ArchLaunchOp
from kernel_gen.dialect.dma import DmaCopyOp, DmaViewOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolConstOp, SymbolExprAttr
from kernel_gen.passes.registry import build_registered_pass, load_builtin_passes
from kernel_gen.passes.template_name.graph import Same, TemplateNameGraph, TemplateNameValue
from kernel_gen.passes.template_name.infer import TemplateNameInferPass


def _memory_type(template_name: str | None = None, external_attrs: DictionaryAttr | None = None) -> NnMemoryType:
    """构造测试用公开 memory type。"""

    return NnMemoryType(
        ArrayAttr([SymbolExprAttr.from_expr("M")]),
        ArrayAttr([SymbolExprAttr.from_expr("1")]),
        i32,
        NnMemorySpaceAttr.from_name("global"),
        template_name=template_name,
        external_attrs=external_attrs,
    )


def _byte_pool_type() -> NnMemoryType:
    """构造一维 i8 byte backing pool memory type。"""

    return NnMemoryType(
        ArrayAttr([SymbolExprAttr.from_expr("BYTES")]),
        ArrayAttr([SymbolExprAttr.from_expr("1")]),
        i8,
        NnMemorySpaceAttr.from_name("tsm"),
    )


def _typed_tsm_type() -> NnMemoryType:
    """构造 byte pool view 产出的 typed memory type。"""

    return NnMemoryType(
        ArrayAttr([SymbolExprAttr.from_expr("M")]),
        ArrayAttr([SymbolExprAttr.from_expr("1")]),
        i32,
        NnMemorySpaceAttr.from_name("tsm"),
    )


def _copy_module(lhs_type: NnMemoryType, rhs_type: NnMemoryType) -> tuple[ModuleOp, func.FuncOp]:
    """构造包含 dma.copy 的测试 module。"""

    block = Block(arg_types=[lhs_type, rhs_type])
    copy_op = DmaCopyOp(block.args[0], block.args[1])
    block.add_ops([copy_op, func.ReturnOp()])
    func_op = func.FuncOp("copy_kernel", FunctionType.from_lists([lhs_type, rhs_type], []), Region(block))
    return ModuleOp([func_op]), func_op


def _empty_func_op(
    name: str,
    arg_types: tuple[NnMemoryType, ...],
    *,
    entry_point: bool = False,
    transform_pipeline: str | None = None,
) -> func.FuncOp:
    """构造 template-name-infer 测试用空函数。

    功能说明:
    - 通过公开 `func.FuncOp` 和 attributes 构造 host / pattern 函数。

    使用示例:
    - func_op = _empty_func_op("kernel", (_memory_type(),), entry_point=True)
    """

    block = Block(arg_types=arg_types)
    block.add_ops([func.ReturnOp()])
    func_op = func.FuncOp(name, FunctionType.from_lists(arg_types, []), Region(block))
    if entry_point:
        func_op.attributes["entry_point"] = UnitAttr()
    if transform_pipeline is not None:
        func_op.attributes["kernel.transform_pipeline"] = StringAttr(transform_pipeline)
    return func_op


def test_template_name_graph_solves_same_constraint() -> None:
    """验证图求解会把 Same 约束合并为同一 template name。"""

    module, func_op = _copy_module(_memory_type(), _memory_type())
    value0 = TemplateNameValue(func_op.args[0], func_op, "block_arg", 0)
    value1 = TemplateNameValue(func_op.args[1], func_op, "block_arg", 1)
    graph = TemplateNameGraph()
    graph.add_signature_seed(value0)
    graph.add_constraint(Same(value0, value1))
    solution = graph.solve()
    assert solution.name_of(func_op.args[0]) == "T1"
    assert solution.name_of(func_op.args[1]) == "T1"
    assert module is not None


def test_template_name_infer_pass_writes_function_arg_types() -> None:
    """验证 pass 按 dma.copy 约束写回函数参数 template_name。"""

    module, func_op = _copy_module(_memory_type(), _memory_type())
    TemplateNameInferPass().apply(Context(), module)
    assert func_op.args[0].type.template_name.data == "T1"
    assert func_op.args[1].type.template_name.data == "T1"
    assert func_op.function_type.inputs.data[0].template_name.data == "T1"
    assert func_op.function_type.inputs.data[1].template_name.data == "T1"


def test_template_name_infer_preserves_external_attrs_when_writing_names() -> None:
    """验证 pass 写入 template_name 时保留其它 external_attrs。"""

    module, func_op = _copy_module(
        _memory_type(external_attrs=DictionaryAttr({"layout": StringAttr("mac_banked")})),
        _memory_type(),
    )

    TemplateNameInferPass().apply(Context(), module)

    first_type = func_op.args[0].type
    assert isinstance(first_type, NnMemoryType)
    assert first_type.template_name.data == "T1"
    assert first_type.external_attrs.data["layout"] == StringAttr("mac_banked")


def test_template_name_infer_rejects_conflicting_explicit_names() -> None:
    """验证同一等价类内显式 template name 冲突会失败。"""

    module, _func_op = _copy_module(_memory_type("T1"), _memory_type("T2"))
    with pytest.raises(KernelCodeError, match="conflicting template_name"):
        TemplateNameInferPass().apply(Context(), module)


def test_template_name_infer_registered_as_builtin_pass() -> None:
    """验证 registry 可按公开名称构造 template-name-infer pass。"""

    load_builtin_passes()
    pass_obj = build_registered_pass("template-name-infer")
    assert isinstance(pass_obj, TemplateNameInferPass)


def test_template_name_infer_links_arch_launch_wrapper_and_device_args() -> None:
    """验证 arch.launch wrapper 与 device memory 参数共享模板名。"""

    memory_type = _memory_type()

    wrapper_block = Block(arg_types=[memory_type, memory_type, memory_type])
    block = SymbolConstOp(1)
    thread = SymbolConstOp(1)
    subthread = SymbolConstOp(1)
    shared = SymbolConstOp(0)
    launch = ArchLaunchOp(
        "launch_kernel_device",
        block.result,
        thread.result,
        subthread.result,
        shared.result,
        tuple(wrapper_block.args),
    )
    wrapper_block.add_ops([block, thread, subthread, shared, launch, func.ReturnOp()])
    wrapper = func.FuncOp(
        "launch_kernel",
        FunctionType.from_lists([memory_type, memory_type, memory_type], []),
        Region(wrapper_block),
    )

    device_block = Block(arg_types=[memory_type, memory_type, memory_type])
    device_block.add_ops(
        [
            DmaCopyOp(device_block.args[0], device_block.args[1]),
            DmaCopyOp(device_block.args[0], device_block.args[2]),
            func.ReturnOp(),
        ]
    )
    device = func.FuncOp(
        "launch_kernel_device",
        FunctionType.from_lists([memory_type, memory_type, memory_type], []),
        Region(device_block),
    )
    module = ModuleOp([wrapper, device])

    TemplateNameInferPass().apply(Context(), module)

    assert [arg.type.template_name.data for arg in wrapper.args] == ["T1", "T1", "T1"]
    assert [arg.type.template_name.data for arg in device.args] == ["T1", "T1", "T1"]


def test_template_name_infer_links_entry_point_host_pattern_args() -> None:
    """验证 entry_point host 同位置参数模板名传播到 pattern 函数。"""

    host = _empty_func_op("entry_point_template_host", (_memory_type(), _memory_type()), entry_point=True)
    pattern0 = _empty_func_op(
        "entry_point_template_host_pattern0",
        (_memory_type(), _memory_type()),
        transform_pipeline="COMPILE_ARGS: --pass lower-dma-memory-hierarchy",
    )
    pattern1 = _empty_func_op(
        "entry_point_template_host_pattern1",
        (_memory_type(), _memory_type()),
        transform_pipeline="COMPILE_ARGS: --pass lower-dma-memory-hierarchy",
    )
    module = ModuleOp([host, pattern0, pattern1])

    TemplateNameInferPass().apply(Context(), module)

    assert [arg.type.template_name.data for arg in host.args] == ["T1", "T2"]
    assert [arg.type.template_name.data for arg in pattern0.args] == ["T1", "T2"]
    assert [arg.type.template_name.data for arg in pattern1.args] == ["T1", "T2"]


def test_template_name_infer_links_entry_point_direct_func_call_args() -> None:
    """验证 entry_point host 直接调用 helper 时同位置 memory 参数共享模板名。"""

    memory0 = _memory_type()
    memory1 = _memory_type()
    host_block = Block(arg_types=[memory0, memory1])
    call = func.CallOp("entry_helper", tuple(host_block.args), [])
    host_block.add_ops([call, func.ReturnOp()])
    host = func.FuncOp(
        "entry",
        FunctionType.from_lists([memory0, memory1], []),
        Region(host_block),
    )
    host.attributes["entry_point"] = UnitAttr()
    helper_block = Block(arg_types=[_memory_type(), _memory_type()])
    helper_block.add_op(func.ReturnOp())
    helper = func.FuncOp(
        "entry_helper",
        FunctionType.from_lists([_memory_type(), _memory_type()], []),
        Region(helper_block),
    )
    module = ModuleOp([host, helper])

    TemplateNameInferPass().apply(Context(), module)

    assert [arg.type.template_name.data for arg in host.args] == ["T1", "T2"]
    assert [arg.type.template_name.data for arg in helper.args] == ["T1", "T2"]


def test_template_name_infer_rejects_entry_point_direct_func_call_conflict() -> None:
    """验证 entry_point direct call 的 callee 显式模板冲突稳定失败。"""

    host_block = Block(arg_types=[_memory_type("T1")])
    call = func.CallOp("entry_helper", tuple(host_block.args), [])
    host_block.add_ops([call, func.ReturnOp()])
    host = func.FuncOp("entry", FunctionType.from_lists([_memory_type("T1")], []), Region(host_block))
    host.attributes["entry_point"] = UnitAttr()
    helper_block = Block(arg_types=[_memory_type("T2")])
    helper_block.add_op(func.ReturnOp())
    helper = func.FuncOp("entry_helper", FunctionType.from_lists([_memory_type("T2")], []), Region(helper_block))
    module = ModuleOp([host, helper])

    with pytest.raises(KernelCodeError, match="entry_point func.call conflict"):
        TemplateNameInferPass().apply(Context(), module)


def test_template_name_infer_rejects_entry_point_pattern_arg_mismatch() -> None:
    """验证 entry_point pattern 参数数量不一致时稳定失败。"""

    host = _empty_func_op("entry_point_template_host", (_memory_type(), _memory_type()), entry_point=True)
    pattern = _empty_func_op(
        "entry_point_template_host_pattern0",
        (_memory_type(),),
        transform_pipeline="COMPILE_ARGS: --pass lower-dma-memory-hierarchy",
    )
    module = ModuleOp([host, pattern])

    with pytest.raises(KernelCodeError, match="entry_point pattern arg count must match host args"):
        TemplateNameInferPass().apply(Context(), module)


def test_template_name_infer_keeps_byte_pool_view_family_independent() -> None:
    """验证 byte backing pool 不会把多个 typed view 合并到同一 template family。"""

    byte_pool_type = _byte_pool_type()
    typed_type = _typed_tsm_type()
    block = Block(arg_types=[byte_pool_type, typed_type])
    offset = SymbolConstOp(0)
    shape = SymbolConstOp(1)
    stride = SymbolConstOp(1)
    view = DmaViewOp(block.args[0], [offset.result], [shape.result], [stride.result], typed_type)
    copy = DmaCopyOp(block.args[1], view.result)
    block.add_ops([offset, shape, stride, view, copy, func.ReturnOp()])
    func_op = func.FuncOp(
        "byte_pool_view_kernel",
        FunctionType.from_lists([byte_pool_type, typed_type], []),
        Region(block),
    )
    module = ModuleOp([func_op])

    TemplateNameInferPass().apply(Context(), module)

    assert func_op.args[0].type.template_name.data == "T1"
    assert func_op.args[1].type.template_name.data == "T2"
    assert view.result.type.template_name.data == "T2"
