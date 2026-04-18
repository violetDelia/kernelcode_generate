"""launch-kernel-cost-func shared-callee-once expectation.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 验证多个 wrapper 指向同一个 device callee 时，同一 `cost_kind` 下只生成一份 cost function。
- 锁定模块内函数顺序与共享 callee 去重合同。

使用示例:
- `PYTHONPATH=. python expectation/pass/tuning/launch_kernel_cost_func/shared_callee_once.py`

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

from kernel_gen.dialect.arch import ArchLaunchOp
from kernel_gen.dialect.kernel import KernelAddOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolConstOp, SymbolValueType
from kernel_gen.passes.tuning.launch_kernel_cost_func import LaunchKernelCostFuncPass


def _print_case_ir(case_name: str, case_desc: str, text: str, *, title: str) -> None:
    """按统一注释格式打印单个 case 的文本 IR。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 打印 `[CASE-x]` 短标题与 `# CASE-x` 注释头。
    - 让 expectation 在缺少共享 helper 时仍输出稳定可读正文。

    使用示例:
    - _print_case_ir("CASE-1", "共享 callee 去重结果", printed, title="实际 IR")

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


def _print_module(module: ModuleOp) -> str:
    """打印 module 为稳定 IR 文本。

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


def _build_module() -> ModuleOp:
    """构造共享 callee 的多 wrapper module。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 生成两个 wrapper，共享同一个 `_device_kernel`。
    - device body 使用最小 `kernel.add`，足以触发单份 cost function 生成。

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

    wrapper_1 = Block(arg_types=arg_types)
    wrapper_2 = Block(arg_types=arg_types)
    device_block = Block(arg_types=arg_types)

    for block in (wrapper_1, wrapper_2):
        launch_block = SymbolConstOp(1)
        launch_thread = SymbolConstOp(1)
        launch_subthread = SymbolConstOp(1)
        block.add_ops(
            [
                launch_block,
                launch_thread,
                launch_subthread,
                ArchLaunchOp(
                    "_device_kernel",
                    launch_block.result,
                    launch_thread.result,
                    launch_subthread.result,
                    tuple(block.args),
                ),
                func.ReturnOp(),
            ]
        )

    kernel_add = KernelAddOp(
        device_block.args[0],
        device_block.args[1],
        device_block.args[2],
        NnMemorySpaceAttr(StringAttr("global")),
    )
    device_block.add_ops([kernel_add, func.ReturnOp()])

    return ModuleOp(
        [
            func.FuncOp("wrapper_0", (arg_types, []), Region(wrapper_1)),
            func.FuncOp("wrapper_1", (arg_types, []), Region(wrapper_2)),
            func.FuncOp("_device_kernel", (arg_types, []), Region(device_block)),
        ]
    )


def main() -> None:
    """运行共享 callee 去重 expectation。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 验证两个 wrapper 共用同一 device callee 时，只生成一份 `_cost_all__device_kernel`。

    使用示例:
    - main()

    关联文件:
    - spec: [spec/pass/tuning/launch_kernel_cost_func.md](../../../../spec/pass/tuning/launch_kernel_cost_func.md)
    - test: [test/pass/test_launch_kernel_cost_func.py](../../../../test/pass/test_launch_kernel_cost_func.py)
    - 功能实现: [kernel_gen/passes/tuning/launch_kernel_cost_func.py](../../../../kernel_gen/passes/tuning/launch_kernel_cost_func.py)
    """

    module = _build_module()
    _print_case_ir("CASE-1", "共享 callee 输入 module", _print_module(module), title="输入 IR")

    LaunchKernelCostFuncPass(kind="all").run(module)
    module.verify()

    printed = _print_module(module)
    _print_case_ir("CASE-1", "共享 callee 去重结果", printed, title="实际 IR")

    func_names = [op.sym_name.data for op in module.ops if isinstance(op, func.FuncOp)]
    assert func_names == ["wrapper_0", "wrapper_1", "_device_kernel", "_cost_all__device_kernel"]
    assert printed.count("func.func @_cost_all__device_kernel") == 1
    assert printed.count("arch.launch") == 2


if __name__ == "__main__":
    main()
