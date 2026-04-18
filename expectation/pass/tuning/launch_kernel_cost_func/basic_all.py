"""launch-kernel-cost-func basic-all expectation.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 验证 `kind=\"all\"` 时会为单个 device callee 生成唯一 cost function。
- 锁定 `tuner.cost` metadata、`symbol.for` carried `f64` 与单个 `f64` 汇总返回的最小 IR 形状。

使用示例:
- `PYTHONPATH=. python expectation/pass/tuning/launch_kernel_cost_func/basic_all.py`

关联文件:
- spec: [spec/pass/tuning/launch_kernel_cost_func.md](../../../../spec/pass/tuning/launch_kernel_cost_func.md)
- test: [test/pass/test_launch_kernel_cost_func.py](../../../../test/pass/test_launch_kernel_cost_func.py)
- 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](../../../../kernel_gen/passes/tuning/launch_kernel_cost_func.py)
"""

from __future__ import annotations

from io import StringIO
from pathlib import Path
import sys

from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, Float32Type, IntAttr, ModuleOp, StringAttr
from xdsl.ir import Block, Region
from xdsl.printer import Printer

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "kernel_gen").exists())
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kernel_gen.dialect.arch import ArchBarrierOp, ArchLaunchOp, ArchScopeAttr, ArchVisibilityAttr
from kernel_gen.dialect.kernel import KernelAddOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolConstOp, SymbolForOp, SymbolIterType, SymbolValueType
from kernel_gen.passes.tuning.launch_kernel_cost_func import LaunchKernelCostFuncPass


def _print_case_ir(case_name: str, case_desc: str, text: str, *, title: str) -> None:
    """按统一注释格式打印单个 case 的文本 IR。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 打印 `[CASE-x]` 短标题与 `# CASE-x` 注释头。
    - 让 expectation 在缺少共享 helper 时仍输出稳定可读正文。

    使用示例:
    - _print_case_ir("CASE-1", "成功结果", printed, title="实际 IR")

    关联文件:
    - spec: [spec/pass/tuning/launch_kernel_cost_func.md](../../../../spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [test/pass/test_launch_kernel_cost_func.py](../../../../test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](../../../../kernel_gen/passes/tuning/launch_kernel_cost_func.py)
    """

    print(f"[{case_name}] {case_desc}")
    print(f"# {case_name} {title}：{case_desc}")
    print(text.strip())


def _make_memory_type(space: str = "global") -> NnMemoryType:
    """构造用于 expectation 的合法 `nn.memory` 类型。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 生成固定二维 `f32` memory type，供 wrapper/device 参数与 `kernel.add` 复用。

    使用示例:
    - memory_type = _make_memory_type()

    关联文件:
    - spec: [spec/pass/tuning/launch_kernel_cost_func.md](../../../../spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [test/pass/test_launch_kernel_cost_func.py](../../../../test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](../../../../kernel_gen/passes/tuning/launch_kernel_cost_func.py)
    """

    return NnMemoryType(
        ArrayAttr([IntAttr(4), IntAttr(4)]),
        ArrayAttr([IntAttr(4), IntAttr(1)]),
        Float32Type(),
        NnMemorySpaceAttr(StringAttr(space)),
    )


def _make_barrier_visibility() -> ArrayAttr:
    """构造 `arch.barrier` 需要的 visibility 列表。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 统一生成 `[#arch.visibility<tsm>, #arch.visibility<tlm>]`。

    使用示例:
    - visibility = _make_barrier_visibility()

    关联文件:
    - spec: [spec/pass/tuning/launch_kernel_cost_func.md](../../../../spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [test/pass/test_launch_kernel_cost_func.py](../../../../test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](../../../../kernel_gen/passes/tuning/launch_kernel_cost_func.py)
    """

    return ArrayAttr(
        [ArchVisibilityAttr.from_name("tsm"), ArchVisibilityAttr.from_name("tlm")]
    )


def _build_module() -> ModuleOp:
    """构造单 wrapper + 单 device 的最小 module。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - device body 内包含 `symbol.for`、`arch.barrier` 与 `kernel.add`。
    - 供 expectation 锁定 `move + compute` 双类别成本节点与循环累计语义。

    使用示例:
    - module = _build_module()

    关联文件:
    - spec: [spec/pass/tuning/launch_kernel_cost_func.md](../../../../spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [test/pass/test_launch_kernel_cost_func.py](../../../../test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](../../../../kernel_gen/passes/tuning/launch_kernel_cost_func.py)
    """

    memory_type = _make_memory_type()
    symbol_m = SymbolValueType.from_expr("M")
    arg_types = [memory_type, memory_type, memory_type, symbol_m]

    wrapper_block = Block(arg_types=arg_types)
    device_block = Block(arg_types=arg_types)
    loop_block = Block(arg_types=[SymbolIterType.from_bounds("0", "M", "1")])

    launch_block = SymbolConstOp(1)
    launch_thread = SymbolConstOp(1)
    launch_subthread = SymbolConstOp(1)
    launch_op = ArchLaunchOp(
        "_device_kernel",
        launch_block.result,
        launch_thread.result,
        launch_subthread.result,
        tuple(wrapper_block.args),
    )
    wrapper_block.add_ops([launch_block, launch_thread, launch_subthread, launch_op, func.ReturnOp()])

    start = SymbolConstOp(0)
    step = SymbolConstOp(1)
    barrier = ArchBarrierOp(ArchScopeAttr.from_name("block"), _make_barrier_visibility())
    kernel_add = KernelAddOp(
        device_block.args[0],
        device_block.args[1],
        device_block.args[2],
        NnMemorySpaceAttr(StringAttr("global")),
    )
    loop_block.add_op(barrier)
    loop_block.add_op(kernel_add)
    loop = SymbolForOp(
        start.result,
        device_block.args[3],
        step.result,
        Region(loop_block),
    )
    device_block.add_ops([start, step, loop, func.ReturnOp()])

    return ModuleOp(
        [
            func.FuncOp("wrapper", (arg_types, []), Region(wrapper_block)),
            func.FuncOp("_device_kernel", (arg_types, []), Region(device_block)),
        ]
    )


def _print_module(module: ModuleOp) -> str:
    """打印 module 为断言友好的稳定文本。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 使用显式 `Printer` 获取完整 module 文本。

    使用示例:
    - text = _print_module(module)

    关联文件:
    - spec: [spec/pass/tuning/launch_kernel_cost_func.md](../../../../spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [test/pass/test_launch_kernel_cost_func.py](../../../../test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](../../../../kernel_gen/passes/tuning/launch_kernel_cost_func.py)
    """

    stream = StringIO()
    Printer(stream=stream).print_op(module)
    return stream.getvalue()


def main() -> None:
    """运行 `kind=\"all\"` 成功路径 expectation。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 验证唯一 cost function 命名、`tuner.cost` metadata、`symbol.for` carried `f64` 与 `func.return` 总值返回。

    使用示例:
    - main()

    关联文件:
    - spec: [spec/pass/tuning/launch_kernel_cost_func.md](../../../../spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [test/pass/test_launch_kernel_cost_func.py](../../../../test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](../../../../kernel_gen/passes/tuning/launch_kernel_cost_func.py)
    """

    module = _build_module()
    _print_case_ir("CASE-1", "kind=all 输入 module", _print_module(module), title="输入 IR")

    LaunchKernelCostFuncPass(kind="all").run(module)
    module.verify()

    printed = _print_module(module)
    _print_case_ir("CASE-1", "kind=all 成功结果", printed, title="实际 IR")

    func_names = [op.sym_name.data for op in module.ops if isinstance(op, func.FuncOp)]
    assert func_names == ["wrapper", "_device_kernel", "_cost_all__device_kernel"]
    assert "func.func @_cost_all__device_kernel" in printed
    assert 'kind = "move"' in printed
    assert 'kind = "compute"' in printed
    assert 'cost_kind = "all"' in printed
    assert 'op_name = "arch.barrier"' in printed
    assert 'op_name = "kernel.add"' in printed
    assert "symbol.for" in printed
    assert "symbol.yield" in printed
    assert "arith.addf" in printed
    assert "func.return" in printed
    assert "-> f64" in printed


if __name__ == "__main__":
    main()
