"""dsl_run tool entry.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 提供 `dsl_run(func, real_args, pipeline, emitcconfig)` 的一体化入口。
- 负责把 DSL 函数解析为 module，按指定 pipeline 做 lowering，再生成源码并交给执行引擎真实编译/执行。
- 只承载公开合同，不把内部 parse / pass / emit / execute 细节暴露为外部依赖。

使用示例:
- from kernel_gen.tools.dsl_run import dsl_run
- result = dsl_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering", EmitCContext(target="npu_demo"))
- assert result.execute_result.ok is True

关联文件:
- spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
- test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
- 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
import inspect
from typing import Any

from xdsl.dialects import func
from xdsl.dialects.builtin import ModuleOp

from kernel_gen.dsl.gen_kernel import EmitCContext, gen_kernel
from kernel_gen.dsl.mlir_gen import mlir_gen
from kernel_gen.execute_engine import CompiledKernel, ExecuteResult, ExecutionEngine
from kernel_gen.operation import loop as _operation_loop
from kernel_gen.operation import alloc as _operation_alloc
from kernel_gen.operation import add as _operation_add
from kernel_gen.operation import cast as _operation_cast
from kernel_gen.operation import copy as _operation_copy
from kernel_gen.operation import deslice as _operation_deslice
from kernel_gen.operation import eq as _operation_eq
from kernel_gen.operation import free as _operation_free
from kernel_gen.operation import ge as _operation_ge
from kernel_gen.operation import gt as _operation_gt
from kernel_gen.operation import le as _operation_le
from kernel_gen.operation import load as _operation_load
from kernel_gen.operation import lt as _operation_lt
from kernel_gen.operation import matmul as _operation_matmul
from kernel_gen.operation import mul as _operation_mul
from kernel_gen.operation import ne as _operation_ne
from kernel_gen.operation import reshape as _operation_reshape
from kernel_gen.operation import slice as _operation_slice
from kernel_gen.operation import store as _operation_store
from kernel_gen.operation import sub as _operation_sub
from kernel_gen.operation import truediv as _operation_truediv
from kernel_gen.operation import view as _operation_view
from kernel_gen.operation.arch import (
    BarrierScope,
    BarrierVisibility,
    barrier as _arch_barrier,
    get_block_id as _arch_get_block_id,
    get_block_num as _arch_get_block_num,
    get_dynamic_memory as _arch_get_dynamic_memory,
    get_subthread_id as _arch_get_subthread_id,
    get_subthread_num as _arch_get_subthread_num,
    get_thread_id as _arch_get_thread_id,
    get_thread_num as _arch_get_thread_num,
    launch_kernel as _arch_launch_kernel,
)
from kernel_gen.operation.nn import (
    add as _nn_add,
    broadcast as _nn_broadcast,
    broadcast_to as _nn_broadcast_to,
    conv as _nn_conv,
    eq as _nn_eq,
    exp as _nn_exp,
    fc as _nn_fc,
    floordiv as _nn_floordiv,
    ge as _nn_ge,
    gt as _nn_gt,
    hard_sigmoid as _nn_hard_sigmoid,
    le as _nn_le,
    leaky_relu as _nn_leaky_relu,
    lt as _nn_lt,
    matmul as _nn_matmul,
    mul as _nn_mul,
    ne as _nn_ne,
    reduce_max as _nn_reduce_max,
    reduce_min as _nn_reduce_min,
    reduce_sum as _nn_reduce_sum,
    relu as _nn_relu,
    sigmoid as _nn_sigmoid,
    softmax as _nn_softmax,
    sub as _nn_sub,
    tanh as _nn_tanh,
    transpose as _nn_transpose,
    truediv as _nn_truediv,
    img2col1d as _nn_img2col1d,
    img2col2d as _nn_img2col2d,
)
from kernel_gen.passes.pass_manager import PassManager
from kernel_gen.passes.registry import PassRegistryError, build_registered_pipeline, load_builtin_passes
from kernel_gen.symbol_variable.memory import Memory, MemorySpace
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import Farmat, NumericType

DslRunError = ValueError

RETURN_VALUE_ERROR = "DslRunReturnValueUnsupported: dsl_run only supports functions without DSL return values"
EMITCCONFIG_ERROR = "DslRunInvalidEmitCContext: emitcconfig must be EmitCContext"
PIPELINE_NAME_ERROR = "DslRunUnknownPipeline: unknown pipeline 'missing-pipeline'"
PIPELINE_TYPE_ERROR = "DslRunInvalidPipeline: pipeline must be str or PassManager"
REAL_ARG_TYPE_ERROR = "DslRunUnsupportedRealArg: real_args only supports torch.Tensor and numpy.ndarray"
ARITY_ERROR = "DslRunArityMismatch: real_args count does not match function signature"
NPU_DEMO_WRAPPER_ERROR = "DslRunInternalError: lowered npu_demo module must contain exactly one wrapper func with arch.launch"


def _runtime_module_name(value: object) -> str:
    """提取运行时对象的模块名，用于轻量类型判断。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 复用 `__module__` 前缀判断 `torch.Tensor` 与 `numpy.ndarray`。
    - 不直接导入 torch/numpy，以免工具导入时引入不必要的依赖耦合。

    使用示例:
    - _runtime_module_name(torch.tensor([1]))

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    return getattr(value.__class__, "__module__", "") or ""


def _is_torch_tensor(value: object) -> bool:
    """判断是否为 `torch.Tensor`。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 仅按模块名前缀做轻量识别，配合执行引擎的运行时参数判定口径。

    使用示例:
    - assert _is_torch_tensor(torch.tensor([1])) is True

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    return _runtime_module_name(value).startswith("torch")


def _is_numpy_array(value: object) -> bool:
    """判断是否为 `numpy.ndarray`。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 仅按模块名前缀做轻量识别，避免在工具导入阶段强依赖 numpy 具体类。

    使用示例:
    - assert _is_numpy_array(np.array([1])) is True

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    return _runtime_module_name(value).startswith("numpy")


def _build_dsl_globals_table(fn: Callable[..., object]) -> dict[str, object]:
    """为 DSL 函数解析补齐最小 helper globals。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 把 `kernel_gen.operation`、`kernel_gen.operation.arch`、`kernel_gen.operation.nn` 等 helper 以名称方式注入。
    - 仅填充当前函数全局命名空间里缺失的名称，避免覆盖调用方已有绑定。
    - 这一步专门收口 expectation 里未显式 import 的 `store(...)` / `barrier(...)` / `launch_kernel(...)` 等 helper。

    使用示例:
    - globals_table = _build_dsl_globals_table(add_kernel)

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    helper_globals: dict[str, object] = {}
    fn_globals = getattr(fn, "__globals__", {}) or {}
    helper_modules = (
        ("operation", __import__("kernel_gen.operation", fromlist=["*"])),
        ("arch", __import__("kernel_gen.operation.arch", fromlist=["*"])),
        ("nn", __import__("kernel_gen.operation.nn", fromlist=["*"])),
        ("dma", __import__("kernel_gen.operation.dma", fromlist=["*"])),
        ("scf", __import__("kernel_gen.operation.scf", fromlist=["*"])),
    )
    for alias, module in helper_modules:
        if alias not in fn_globals:
            helper_globals[alias] = module
        public_names = getattr(module, "__all__", None)
        if not public_names:
            public_names = [name for name in dir(module) if not name.startswith("_")]
        for name in public_names:
            if not isinstance(name, str) or name in fn_globals or name in helper_globals:
                continue
            helper_globals[name] = getattr(module, name)
    helper_globals.setdefault("Memory", Memory)
    helper_globals.setdefault("MemorySpace", MemorySpace)
    helper_globals.setdefault("NumericType", NumericType)
    helper_globals.setdefault("SymbolDim", SymbolDim)
    helper_globals.setdefault("Farmat", Farmat)
    helper_globals.setdefault("BarrierVisibility", BarrierVisibility)
    helper_globals.setdefault("BarrierScope", BarrierScope)
    helper_globals.setdefault("loop", _operation_loop)
    helper_globals.setdefault("floordiv", _nn_floordiv)
    return helper_globals


def _normalize_real_args(real_args: tuple[object, ...] | list[object]) -> tuple[object, ...]:
    """把 `real_args` 规整为 tuple，方便后续统一校验与执行。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 允许调用方传入 tuple 或 list。
    - 其余类型一律视为非法容器，避免把字符串、数组对象误当成参数序列。

    使用示例:
    - runtime_args = _normalize_real_args([out, lhs, rhs])

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    if isinstance(real_args, tuple):
        return real_args
    if isinstance(real_args, list):
        return tuple(real_args)
    raise DslRunError("DslRunInvalidRealArgs: real_args must be tuple or list")


def _resolve_pipeline(pipeline: str | PassManager) -> PassManager:
    """把 pipeline 参数解析为 PassManager。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 接受已构造好的 `PassManager`，直接复用。
    - 接受字符串 pipeline 名称时，先加载内置注册，再按注册名构造。
    - 未知 pipeline 名称统一收口为稳定错误短语。

    使用示例:
    - pm = _resolve_pipeline("npu-demo-lowering")

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    if isinstance(pipeline, PassManager):
        return pipeline
    if not isinstance(pipeline, str):
        raise DslRunError(PIPELINE_TYPE_ERROR)
    load_builtin_passes()
    try:
        return build_registered_pipeline(pipeline)
    except PassRegistryError as exc:
        raise DslRunError(f"DslRunUnknownPipeline: unknown pipeline '{pipeline}'") from exc


def _find_first_func(module: ModuleOp) -> func.FuncOp:
    """从 module 中找出首个 `func.func`。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 作为 `dsl_run(...)` 的默认入口函数选择策略。
    - `mlir_gen(...)` 的 root func 会被优先返回，因此这一步只负责把 module 里的第一条函数 op 拿出来。

    使用示例:
    - func_op = _find_first_func(module)

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    for op in module.ops:
        if isinstance(op, func.FuncOp):
            return op
    raise DslRunError("DslRunInternalError: lowered module does not contain func.func")


def _find_func_by_sym_name(module: ModuleOp, sym_name: str) -> func.FuncOp:
    """按符号名在 lowered module 中查找 `func.func`。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 用于 npu_demo outline wrapper 场景，把 `arch.launch` 指向的 device body 精确找回。
    - 若 module 中不存在对应符号名的函数，则抛出统一内部错误，避免悄悄回退到错误的 IR 视图。

    使用示例:
    - body_func = _find_func_by_sym_name(module, "matmul_kernel_device")

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    for op in module.ops:
        if isinstance(op, func.FuncOp) and op.sym_name.data == sym_name:
            return op
    raise DslRunError(f"DslRunInternalError: lowered module does not contain func.func @{sym_name}")


def _select_source_and_entry(module: ModuleOp, emitcconfig: EmitCContext) -> tuple[str, str, func.FuncOp]:
    """根据 lowered module 选择源码生成入口与执行入口名。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 单函数 module 时，直接按该函数生成源码并以该函数名作为执行入口。
    - `npu_demo` 的 wrapper module 若存在唯一带 `arch.launch` 的 wrapper，则按 module 级别生成源码，
      但返回 wrapper 所指向的 body func 作为 `DslRunResult.func_op` 与执行入口，确保结果对象和真实 lowering IR 对齐。
    - `npu_demo` 若 wrapper 候选不存在或不唯一，则显式失败，不退回到首个普通 `func.func`。
    - 其余 target 退回到首个 `func.func` 的源码生成入口，保证常见单函数和 expectation 场景稳定可执行。

    使用示例:
    - source, entry_name, func_op = _select_source_and_entry(module, EmitCContext(target="npu_demo"))

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    func_ops = [op for op in module.ops if isinstance(op, func.FuncOp)]
    root_func = _find_first_func(module)
    if emitcconfig.target == "npu_demo":
        wrapper_candidates = [
            func_op
            for func_op in func_ops
            if any(item.name == "arch.launch" for item in func_op.body.block.ops)
        ]
        if len(wrapper_candidates) != 1:
            raise DslRunError(NPU_DEMO_WRAPPER_ERROR)
        wrapper_func = wrapper_candidates[0]
        wrapper_launch = next(item for item in wrapper_func.body.block.ops if item.name == "arch.launch")
        body_func = _find_func_by_sym_name(module, wrapper_launch.callee.root_reference.data)
        return gen_kernel(module, emitcconfig), body_func.sym_name.data, body_func
    try:
        return gen_kernel(root_func, emitcconfig), root_func.sym_name.data, root_func
    except Exception:
        raise


@dataclass(frozen=True)
class DslRunResult:
    """`dsl_run(...)` 的一次执行结果。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 记录 lowered module、选中的 `func.func`、生成源码、编译产物与执行结果。
    - `runtime_args` 保留为 tuple，便于下游机械比较和再次调用执行引擎。

    使用示例:
    - result = dsl_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering", EmitCContext(target="npu_demo"))
    - assert result.execute_result.ok is True

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    func_op: func.FuncOp
    module: ModuleOp
    source: str
    compiled_kernel: CompiledKernel
    execute_result: ExecuteResult
    runtime_args: tuple[object, ...]


def dsl_run(
    func_obj: Callable[..., object],
    real_args: tuple[object, ...] | list[object],
    pipeline: str | PassManager,
    emitcconfig: EmitCContext | object | None,
) -> DslRunResult:
    """把 DSL 函数按指定 pipeline 真实 lowering 并执行。

    创建者: 朽木露琪亚
    最后更改: 朽木露琪亚

    功能说明:
    - 先校验 `emitcconfig`，再解析 pipeline 与 `real_args`。
    - 通过 `mlir_gen(...)` 生成 `builtin.module`，拒绝带 DSL 返回值的函数。
    - 按 pipeline 对 module 做 lowering，使用 `gen_kernel(...)` 生成目标源码，再交给 `ExecutionEngine` 真实编译与执行。
    - 结果以 `DslRunResult` 返回，外部可以继续读取 `func_op/module/source/compiled_kernel/execute_result/runtime_args`。

    使用示例:
    - result = dsl_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering", EmitCContext(target="npu_demo"))
    - assert result.execute_result.ok is True

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    if not isinstance(emitcconfig, EmitCContext):
        raise DslRunError(EMITCCONFIG_ERROR)

    resolved_pipeline = _resolve_pipeline(pipeline)
    runtime_args = _normalize_real_args(real_args)

    positional_params = [
        param
        for param in inspect.signature(func_obj).parameters.values()
        if param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    if len(runtime_args) != len(positional_params):
        raise DslRunError(ARITY_ERROR)
    for arg in runtime_args:
        if not (_is_torch_tensor(arg) or _is_numpy_array(arg)):
            raise DslRunError(REAL_ARG_TYPE_ERROR)

    globals_table = _build_dsl_globals_table(func_obj)
    module = mlir_gen(func_obj, *runtime_args, globals=globals_table, config={"reject_external_values": True, "allow_python_callee_calls": True})
    if not isinstance(module, ModuleOp):
        raise DslRunError("DslRunInternalError: mlir_gen must return builtin.module")

    root_func = _find_first_func(module)
    if root_func.function_type.outputs.data:
        raise DslRunError(RETURN_VALUE_ERROR)

    lowered_module = resolved_pipeline.run(module)
    if not isinstance(lowered_module, ModuleOp):
        raise DslRunError("DslRunInternalError: pipeline must return builtin.module")

    source, entry_name, func_op = _select_source_and_entry(lowered_module, emitcconfig)
    engine = ExecutionEngine(target=emitcconfig.target)
    compiled_kernel = engine.compile(source=source, function=entry_name)
    execute_result = compiled_kernel.execute(args=runtime_args)
    return DslRunResult(
        func_op=func_op,
        module=lowered_module,
        source=source,
        compiled_kernel=compiled_kernel,
        execute_result=execute_result,
        runtime_args=runtime_args,
    )


__all__ = [
    "DslRunError",
    "DslRunResult",
    "dsl_run",
]
