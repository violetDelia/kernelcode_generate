"""dsl_run tool entry.


功能说明:
- 提供 `dsl_run(func, real_args, pipeline)` 的一体化入口。
- 负责把 DSL 函数解析为 module，按指定 pipeline 做 lowering，再生成源码并交给执行引擎真实编译/执行。
- 只承载公开合同，不把内部 parse / pass / emit / execute 细节暴露为外部依赖。
- 不向 DSL 函数隐式注入 operation helper；kernel 体使用的 helper 必须由调用方显式 import 或闭包绑定。
- `dump_dir` 与 runtime `trance` 诊断开关统一从 `kernel_gen.core.config` 读取，不作为 `dsl_run(...)` 入参。
- IR dump 文件默认使用 `kernel_gen.core.print.print_operation_with_aliases(...)` 的 alias 文本。
- kernel 级 dump 目录派生和工具层诊断文本写出统一委托 `kernel_gen.core.tools.dump_dir.DumpDirWriter`。
- `dsl_run(...)` 的 runtime trance 落盘只生成 block trace 文件；`dsl_cost_run(...)` 始终保留 stdout-only trance 诊断。

API 列表:
- `DslRunResult(func_op: func.FuncOp, module: ModuleOp, source: str, compiled_kernel: CompiledKernel, execute_result: ExecuteResult, runtime_args: tuple[RuntimeRealArg, ...])`
- `dsl_run(func_obj: Callable[..., DslFunctionReturn], real_args: tuple[RuntimeRealArg, ...] | list[RuntimeRealArg], pipeline: str | PassManager) -> DslRunResult`
- `dsl_cost_run(func_obj: Callable[..., DslFunctionReturn], real_args: tuple[RuntimeRealArg, ...] | list[RuntimeRealArg], pipeline: str | PassManager, cost_kind: str) -> int`

使用示例:
- from kernel_gen.tools.dsl_run import dsl_run
- result = dsl_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering")
- assert result.execute_result.ok is True
- from kernel_gen.tools.dsl_run import dsl_cost_run
- cost = dsl_cost_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering", "VECTOR1")

关联文件:
- spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
- test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
- 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
import inspect
import json
import re
from typing import Protocol, TypeAlias

from xdsl.dialects import func
from xdsl.dialects.builtin import ModuleOp

from kernel_gen.core.config import get_target, restore_config, set_codegen_mode, set_dump_dir, snapshot_config
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.core.tools.dump_dir import DumpDirWriter
from kernel_gen.dialect.arch import ArchLaunchOp
from kernel_gen.dsl.gen_kernel import EmitCContext, gen_kernel
from kernel_gen.dsl.ast.mlir_gen import mlir_gen
from kernel_gen.execute_engine import CompiledKernel, ExecuteResult, ExecutionEngine
from kernel_gen.execute_engine.runtime_args import RuntimeMemoryArgInfo, RuntimeScalarArgInfo, describe_runtime_arg
from kernel_gen.passes.pass_manager import PassManager
from kernel_gen.passes.registry import build_registered_pipeline, load_builtin_passes
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim
from kernel_gen.symbol_variable.type import NumericType

RETURN_VALUE_ERROR = "DslRunReturnValueUnsupported: dsl_run only supports functions without DSL return values"
PIPELINE_NAME_ERROR = "DslRunUnknownPipeline: unknown pipeline 'missing-pipeline'"
PIPELINE_TYPE_ERROR = "DslRunInvalidPipeline: pipeline must be str or PassManager"
REAL_ARG_TYPE_ERROR = "DslRunUnsupportedRealArg: real_args only supports torch.Tensor, numpy.ndarray, integer scalar, float scalar and None for memory"
TENSOR_ARG_TYPE_ERROR = "DslRunUnsupportedRealArg: real_args only supports torch.Tensor and numpy.ndarray"
TILE_VALUE_ERROR = "DslRunInvalidTileValue: tile runtime scalar must be positive int"
ARITY_ERROR = "DslRunArityMismatch: real_args count does not match function signature"
NPU_DEMO_WRAPPER_ERROR = "DslRunInternalError: lowered npu_demo module must contain exactly one wrapper func with arch.launch"
VALID_DSL_COST_KINDS = ("DMA1", "DMA2", "DMA3", "DMA4", "MAC", "VECTOR1", "VECTOR2")
DSL_COST_KIND_ERROR = "DslCostRunInvalidCostKind: cost_kind must be one of ['DMA1', 'DMA2', 'DMA3', 'DMA4', 'MAC', 'VECTOR1', 'VECTOR2']"
DSL_COST_TARGET_ERROR = "DslCostRunInvalidTarget: dsl_cost_run only supports target 'npu_demo'"
DSL_COST_OUTPUT_ERROR = "DslCostRunExecutionFailed: cost summary capture failed"


class _StringLike(Protocol):
    """运行时 dtype 的最小字符串化协议。"""

    def __str__(self) -> str:
        """返回 dtype 文本。"""


class TensorRuntimeArg(Protocol):
    """`dsl_run(...)` 支持的真实运行时数组参数协议。"""

    shape: Iterable[int]
    dtype: _StringLike


RuntimeRealArg: TypeAlias = "TensorRuntimeArg | int | float | None"
DslFunctionReturn: TypeAlias = "Memory | SymbolDim | int | float | bool | str | None"


def _sanitize_dump_component(value: str) -> str:
    """把 dump 路径片段规整为安全文件名。


    功能说明:
    - 保留常见可读字符，其他字符替换为 `_`。
    - 用于 kernel 子目录名，避免函数名中的特殊字符影响落盘。

    使用示例:
    - _sanitize_dump_component("add_kernel")

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return safe_name or "kernel"


def _resolve_dump_kernel_writer(
    func_obj: Callable[..., DslFunctionReturn],
) -> DumpDirWriter | None:
    """从公开 config 解析 `dsl_run(...)` 的 kernel 级 dump writer。


    功能说明:
    - `DumpDirWriter.from_config() is None` 时禁用落盘。
    - 非空时在根目录下按 DSL 函数名创建子目录，匹配 `dir/kernelname/...` 结构。

    使用示例:
    - dump_writer = _resolve_dump_kernel_writer(add_kernel)

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """
    writer = DumpDirWriter.from_config()
    if writer is None:
        return None
    kernel_name = getattr(func_obj, "__name__", "kernel")
    if not isinstance(kernel_name, str) or not kernel_name:
        kernel_name = "kernel"
    return writer.child(kernel_name, fallback="kernel")


def _normalize_real_args(real_args: tuple[RuntimeRealArg, ...] | list[RuntimeRealArg]) -> tuple[RuntimeRealArg, ...]:
    """把 `real_args` 规整为 tuple，方便后续统一校验与执行。


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
    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, "DslRunInvalidRealArgs: real_args must be tuple or list")


def _build_dsl_runtime_args(
    runtime_args: tuple[RuntimeRealArg, ...],
    parameters: tuple[inspect.Parameter, ...],
) -> tuple[tuple[Memory | int | float, ...], tuple[RuntimeRealArg, ...]]:
    """把真实运行时参数转换为 DSL 参数与 execute 参数。


    功能说明:
    - 通过 execute_engine 文件级 API `describe_runtime_arg(...)` 获得基础分类结果。
    - `mlir_gen(...)` 使用 `Memory` 或规整后的 scalar，执行阶段保留真实 memory 对象与规整 scalar。
    - `Tensor[...]` 注解仅用于 scalar 拒绝与 runtime `None` 的 nominal `Memory` 构造。

    使用示例:
    - dsl_args, execute_args = _build_dsl_runtime_args((out, lhs, rhs), parameters)

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    dsl_args: list[Memory | int | float] = []
    execute_args: list[RuntimeRealArg] = []
    dtype_aliases = {
        "f16": "float16",
        "bf16": "bf16",
        "f32": "float32",
        "f64": "float64",
        "i8": "int8",
        "i16": "int16",
        "i32": "int32",
        "i64": "int64",
        "ui8": "uint8",
        "ui16": "uint16",
        "ui32": "uint32",
        "ui64": "uint64",
    }
    for parameter, arg in zip(parameters, runtime_args, strict=True):
        annotation = parameter.annotation
        if annotation is inspect.Parameter.empty:
            annotation_text = ""
        elif isinstance(annotation, str):
            annotation_text = annotation.strip()
        else:
            annotation_text = getattr(annotation, "__name__", str(annotation)).strip()
        if len(annotation_text) >= 2 and annotation_text[0] == annotation_text[-1] and annotation_text[0] in {"'", '"'}:
            annotation_text = annotation_text[1:-1].strip()
        expects_tensor = annotation_text.startswith("Tensor[")
        if arg is None:
            if not expects_tensor or not annotation_text.endswith("]"):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, REAL_ARG_TYPE_ERROR)
            parts = [item.strip() for item in annotation_text[len("Tensor[") : -1].split(",")]
            if len(parts) < 2 or not parts[0]:
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, REAL_ARG_TYPE_ERROR)
            try:
                dtype = NumericType(dtype_aliases.get(parts[0], parts[0]))
            except ValueError as exc:
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, REAL_ARG_TYPE_ERROR) from exc
            shape: list[int | str] = []
            for dim in parts[1:]:
                if not dim:
                    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, REAL_ARG_TYPE_ERROR)
                shape.append(int(dim) if dim.isdecimal() else dim)
            dsl_args.append(Memory(shape, dtype))
            execute_args.append(None)
            continue
        info = describe_runtime_arg(arg)
        if info is None:
            module_name = getattr(arg.__class__, "__module__", "") or ""
            class_name = getattr(arg.__class__, "__name__", "")
            is_bool_scalar = isinstance(arg, bool) or (module_name.startswith("numpy") and class_name in {"bool", "bool_"})
            is_memory_like = module_name.startswith(("torch", "numpy")) and hasattr(arg, "shape") and hasattr(arg, "dtype")
            if parameter.name.startswith("tile_") and is_bool_scalar:
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, TILE_VALUE_ERROR)
            if expects_tensor and not is_memory_like:
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, TENSOR_ARG_TYPE_ERROR)
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, REAL_ARG_TYPE_ERROR)
        if isinstance(info, RuntimeScalarArgInfo):
            if parameter.name.startswith("tile_") and (info.kind != "int" or info.value <= 0):
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, TILE_VALUE_ERROR)
            if expects_tensor:
                raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, TENSOR_ARG_TYPE_ERROR)
            scalar_value = int(info.value) if info.kind == "int" else float(info.value)
            dsl_args.append(scalar_value)
            execute_args.append(scalar_value)
            continue
        if isinstance(info, RuntimeMemoryArgInfo):
            dsl_args.append(Memory(info.shape, info.dtype, stride=info.stride))
            execute_args.append(arg)
            continue
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, REAL_ARG_TYPE_ERROR)
    return tuple(dsl_args), tuple(execute_args)


def _resolve_pipeline(pipeline: str | PassManager) -> PassManager:
    """把 pipeline 参数解析为 PassManager。


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
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, PIPELINE_TYPE_ERROR)
    load_builtin_passes()
    try:
        return build_registered_pipeline(pipeline)
    except KernelCodeError as exc:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, f"DslRunUnknownPipeline: unknown pipeline '{pipeline}'") from exc


def _run_pipeline_with_optional_dump(
    pipeline: PassManager,
    module: ModuleOp,
    dump_writer: DumpDirWriter | None,
) -> ModuleOp:
    """执行 pipeline，并在可用时写入 pass IR dump。


    功能说明:
    - 标准 `PassManager` 由自身写入 `01-first-ir.mlir` 和逐 pass IR。
    - 覆盖 `run(module)` 的自定义 pipeline 不强制改签名，只写入 alias 初始 IR 与 alias pipeline 后 IR。

    使用示例:
    - lowered = _run_pipeline_with_optional_dump(pm, module, dump_writer)

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """
    if dump_writer is None:
        return pipeline.run(module)
    if type(pipeline).run is PassManager.run:
        snapshot = snapshot_config()
        try:
            set_dump_dir(dump_writer.root)
            return pipeline.run(module)
        finally:
            restore_config(snapshot)
    dump_writer.write("01-first-ir.mlir", module)
    output = pipeline.run(module)
    pipeline_name = getattr(pipeline, "name", "pipeline")
    if not isinstance(pipeline_name, str) or not pipeline_name:
        pipeline_name = "pipeline"
    dump_writer.write("02-pipeline.mlir", output, marker=pipeline_name)
    return output


def _emitc_target_name(emit_context: EmitCContext) -> str:
    """读取当前公开 target 名称。


    功能说明:
    - 统一从 `kernel_gen.core.config.get_target()` 读取目标名。
    - `emit_context` 参数保留为调用链上下文标记，不访问其内部 target 状态。

    使用示例:
    - target = _emitc_target_name(EmitCContext())

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    try:
        target = get_target()
    except KernelCodeError as exc:
        raise KernelCodeError(
            ErrorKind.CONTRACT,
            ErrorModule.TOOLS,
            "DslRunInvalidTarget: core config target must be non-empty str",
        ) from exc
    if not isinstance(target, str) or not target:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, "DslRunInvalidTarget: core config target must be non-empty str")
    return target


def _find_first_func(module: ModuleOp) -> func.FuncOp:
    """从 module 中找出首个 `func.func`。


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
    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, "DslRunInternalError: lowered module does not contain func.func")


def _find_func_by_sym_name(module: ModuleOp, sym_name: str) -> func.FuncOp:
    """按符号名在 lowered module 中查找 `func.func`。


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
    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, f"DslRunInternalError: lowered module does not contain func.func @{sym_name}")


def _arch_launch_ops_in_func(func_op: func.FuncOp) -> tuple[ArchLaunchOp, ...]:
    """收集函数体内的 `arch.launch`。

    功能说明:
    - 支持 `entry_point` dispatcher 中 `scf.if` 分支嵌套 launch 的形态。
    - 只使用公开 `ArchLaunchOp` 类型和 xDSL walk 入口，不读取 pass 内部 helper。

    使用示例:
    - launches = _arch_launch_ops_in_func(wrapper_func)

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    return tuple(op for op in func_op.walk() if isinstance(op, ArchLaunchOp))


def _select_source_and_entry(module: ModuleOp, emit_context: EmitCContext) -> tuple[str, str, func.FuncOp]:
    """根据 lowered module 选择源码生成入口与执行入口名。


    功能说明:
    - 单函数 module 时，直接按该函数生成源码并以该函数名作为执行入口。
    - `npu_demo` 的 wrapper module 若存在唯一带 `arch.launch` 的 wrapper，则按 module 级别生成源码，
      使用 wrapper 作为真实执行入口，并返回 wrapper 所指向的 body func 作为 `DslRunResult.func_op`
      供调用方观察真实 lowered kernel body。
    - `arch.launch` 可以位于 wrapper 顶层，也可以位于 `entry_point` dispatcher 的控制流分支内。
    - `npu_demo` 若 wrapper 候选不存在或不唯一，则显式失败，不退回到首个普通 `func.func`。
    - 其余 target 退回到首个 `func.func` 的源码生成入口，保证常见单函数和 expectation 场景稳定可执行。

    使用示例:
    - source, entry_name, func_op = _select_source_and_entry(module, EmitCContext())

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    func_ops = [op for op in module.ops if isinstance(op, func.FuncOp)]
    root_func = _find_first_func(module)
    if _emitc_target_name(emit_context) == "npu_demo":
        wrapper_launches = [(func_op, _arch_launch_ops_in_func(func_op)) for func_op in func_ops]
        wrapper_candidates = [(func_op, launches) for func_op, launches in wrapper_launches if launches]
        if len(wrapper_candidates) != 1:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, NPU_DEMO_WRAPPER_ERROR)
        wrapper_func, launches = wrapper_candidates[0]
        wrapper_launch = launches[0]
        body_func = _find_func_by_sym_name(module, wrapper_launch.callee.root_reference.data)
        return gen_kernel(module, emit_context), wrapper_func.sym_name.data, body_func
    return gen_kernel(root_func, emit_context), root_func.sym_name.data, root_func


def _validate_dsl_cost_kind(cost_kind: str) -> None:
    """校验 `dsl_cost_run(...)` 的公开 cost kind。


    功能说明:
    - 只接受 npu_demo 七类 exact kind。
    - 拒绝历史 `"DMA"` 聚合 kind 和任意组合字符串。

    使用示例:
    - _validate_dsl_cost_kind("VECTOR1")

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_cost_run.py](test/tools/test_dsl_cost_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    if cost_kind not in VALID_DSL_COST_KINDS:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, DSL_COST_KIND_ERROR)


def _select_cost_source_and_entry(
    module: ModuleOp,
    emit_context: EmitCContext,
) -> tuple[str, str, func.FuncOp]:
    """根据 lowered module 选择 cost 源码与执行入口。


    功能说明:
    - 复用 `npu_demo` wrapper/body 公开选择规则。
    - cost mode 下执行入口固定为 `<wrapper>_cost`，body func 仍作为调用方观察的 lowered kernel body。

    使用示例:
    - source, entry_name, func_op = _select_cost_source_and_entry(module, EmitCContext())

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_cost_run.py](test/tools/test_dsl_cost_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    try:
        target = get_target()
    except KernelCodeError as exc:
        raise KernelCodeError(
            ErrorKind.CONTRACT,
            ErrorModule.TOOLS,
            "DslRunInvalidTarget: core config target must be non-empty str",
        ) from exc
    if target != "npu_demo":
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, DSL_COST_TARGET_ERROR)
    func_ops = [op for op in module.ops if isinstance(op, func.FuncOp)]
    wrapper_launches = [
        (func_op, tuple(op for op in func_op.walk() if isinstance(op, ArchLaunchOp)))
        for func_op in func_ops
    ]
    wrapper_candidates = [(func_op, launches) for func_op, launches in wrapper_launches if launches]
    if len(wrapper_candidates) != 1:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, NPU_DEMO_WRAPPER_ERROR)
    wrapper_func, launches = wrapper_candidates[0]
    body_name = launches[0].callee.root_reference.data
    for body_func in func_ops:
        if body_func.sym_name.data == body_name:
            return gen_kernel(module, emit_context), f"{wrapper_func.sym_name.data}_cost", body_func
    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, f"DslRunInternalError: lowered module does not contain func.func @{body_name}")


def _parse_cost_summary_value(summary_text: str, cost_kind: str) -> int:
    """解析 cost summary string 并返回指定 kind。


    功能说明:
    - summary string 必须是固定七键 JSON object。
    - 缺 key、空文本、非整数值或额外/缺失 key 均按 `DslCostRunExecutionFailed` 失败。

    使用示例:
    - value = _parse_cost_summary_value('{"DMA1":0,"DMA2":0,"DMA3":0,"DMA4":0,"MAC":0,"VECTOR1":128,"VECTOR2":0}', "VECTOR1")

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_cost_run.py](test/tools/test_dsl_cost_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    if not isinstance(summary_text, str) or not summary_text:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, DSL_COST_OUTPUT_ERROR)
    try:
        parsed = json.loads(summary_text)
    except json.JSONDecodeError as exc:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, DSL_COST_OUTPUT_ERROR) from exc
    if not isinstance(parsed, dict) or set(parsed.keys()) != set(VALID_DSL_COST_KINDS):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, DSL_COST_OUTPUT_ERROR)
    value = parsed.get(cost_kind)
    if isinstance(value, bool) or not isinstance(value, int):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, DSL_COST_OUTPUT_ERROR)
    return int(value)


@dataclass(frozen=True)
class DslRunResult:
    """`dsl_run(...)` 的一次执行结果。


    功能说明:
    - 记录 lowered module、选中的 `func.func`、生成源码、编译产物与执行结果。
    - `runtime_args` 保留为 tuple，便于下游机械比较和再次调用执行引擎。

    使用示例:
    - result = dsl_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering")
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
    runtime_args: tuple[RuntimeRealArg, ...]


def dsl_run(
    func_obj: Callable[..., DslFunctionReturn],
    real_args: tuple[RuntimeRealArg, ...] | list[RuntimeRealArg],
    pipeline: str | PassManager,
) -> DslRunResult:
    """把 DSL 函数按指定 pipeline 真实 lowering 并执行。


    功能说明:
    - 先解析全局公开 target 配置、pipeline 与 `real_args`。
    - 通过 `mlir_gen(...)` 生成 `builtin.module`，拒绝带 DSL 返回值的函数。
    - 不补写 `func_obj.__globals__`；kernel 体缺少显式导入的 helper 时由 DSL parser 报错。
    - 按 pipeline 对 module 做 lowering，使用 `gen_kernel(...)` 生成目标源码，再交给 `ExecutionEngine` 真实编译与执行。
    - `kernel_gen.core.config.dump_dir` 非空时按 `dump_dir/<kernel name>/` 写入初始 IR、每个 pass 后 IR 与最终源码。
    - 结果以 `DslRunResult` 返回，外部可以继续读取 `func_op/module/source/compiled_kernel/execute_result/runtime_args`。

    使用示例:
    - result = dsl_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering")
    - set_dump_dir("dump"); result = dsl_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering")
    - assert result.execute_result.ok is True

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_run.py](test/tools/test_dsl_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    if not isinstance(get_target(), str) or not get_target():
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, "DslRunInvalidTarget: core config target must be non-empty str")
    emit_context = EmitCContext()
    resolved_pipeline = _resolve_pipeline(pipeline)
    runtime_args = _normalize_real_args(real_args)
    dump_kernel_writer = _resolve_dump_kernel_writer(func_obj)

    positional_params = [
        param
        for param in inspect.signature(func_obj).parameters.values()
        if param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    if len(runtime_args) != len(positional_params):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, ARITY_ERROR)
    dsl_args, execute_args = _build_dsl_runtime_args(runtime_args, tuple(positional_params))

    module = mlir_gen(func_obj, *dsl_args)
    if not isinstance(module, ModuleOp):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, "DslRunInternalError: mlir_gen must return builtin.module")

    root_func = _find_first_func(module)
    if root_func.function_type.outputs.data:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, RETURN_VALUE_ERROR)

    lowered_module = _run_pipeline_with_optional_dump(resolved_pipeline, module, dump_kernel_writer)
    if not isinstance(lowered_module, ModuleOp):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, "DslRunInternalError: pipeline must return builtin.module")

    source_snapshot = snapshot_config()
    try:
        set_codegen_mode("norm")
        if dump_kernel_writer is not None:
            set_dump_dir(dump_kernel_writer.root)
        source, entry_name, func_op = _select_source_and_entry(lowered_module, emit_context)
        if dump_kernel_writer is not None:
            set_dump_dir(dump_kernel_writer.root.parent)
        engine = ExecutionEngine(target=_emitc_target_name(emit_context))
        compiled_kernel = engine.compile(source=source, function=entry_name)
    finally:
        restore_config(source_snapshot)
    execute_result = compiled_kernel.execute(args=execute_args)
    return DslRunResult(
        func_op=func_op,
        module=lowered_module,
        source=source,
        compiled_kernel=compiled_kernel,
        execute_result=execute_result,
        runtime_args=execute_args,
    )


def dsl_cost_run(
    func_obj: Callable[..., DslFunctionReturn],
    real_args: tuple[RuntimeRealArg, ...] | list[RuntimeRealArg],
    pipeline: str | PassManager,
    cost_kind: str,
) -> int:
    """把 DSL 函数 lowering 到 npu_demo cost function 并返回真实 cost。


    功能说明:
    - 公开入口固定要求调用方显式传入 `cost_kind`，不设置默认值。
    - 只接受 `DMA1/DMA2/DMA3/DMA4/MAC/VECTOR1/VECTOR2` 七类 kind。
    - 复用 `dsl_run(...)` 的真实参数校验、DSL 解析、pipeline lowering、npu_demo wrapper/body 选择与执行引擎编译执行。
    - 通过 execute_engine 限定 capture ABI 读取 generated cost host 的 summary string，再解析出指定 kind。

    使用示例:
    - cost = dsl_cost_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering", "VECTOR1")
    - assert isinstance(cost, int)

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_cost_run.py](test/tools/test_dsl_cost_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    _validate_dsl_cost_kind(cost_kind)
    if not isinstance(get_target(), str) or not get_target():
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, "DslRunInvalidTarget: core config target must be non-empty str")
    emit_context = EmitCContext()
    if _emitc_target_name(emit_context) != "npu_demo":
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, DSL_COST_TARGET_ERROR)
    resolved_pipeline = _resolve_pipeline(pipeline)
    runtime_args = _normalize_real_args(real_args)
    dump_kernel_writer = _resolve_dump_kernel_writer(func_obj)

    positional_params = [
        param
        for param in inspect.signature(func_obj).parameters.values()
        if param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    if len(runtime_args) != len(positional_params):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, ARITY_ERROR)
    dsl_args, execute_args = _build_dsl_runtime_args(runtime_args, tuple(positional_params))

    module = mlir_gen(func_obj, *dsl_args)
    if not isinstance(module, ModuleOp):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, "DslRunInternalError: mlir_gen must return builtin.module")

    root_func = _find_first_func(module)
    if root_func.function_type.outputs.data:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, RETURN_VALUE_ERROR)

    lowered_module = _run_pipeline_with_optional_dump(resolved_pipeline, module, dump_kernel_writer)
    if not isinstance(lowered_module, ModuleOp):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, "DslRunInternalError: pipeline must return builtin.module")

    source_snapshot = snapshot_config()
    try:
        set_codegen_mode("cost")
        set_dump_dir(None)
        cost_source, cost_entry_name, _ = _select_cost_source_and_entry(lowered_module, emit_context)
        if dump_kernel_writer is not None:
            dump_kernel_writer.write("99-cost-source.cpp", cost_source)
        engine = ExecutionEngine(target=_emitc_target_name(emit_context))
        compiled_kernel = engine.compile(source=cost_source, function=cost_entry_name)
    finally:
        restore_config(source_snapshot)

    try:
        execute_result = compiled_kernel.execute(args=execute_args, capture_function_output=True)
    except KernelCodeError as exc:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, DSL_COST_OUTPUT_ERROR) from exc
    if not execute_result.ok:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, DSL_COST_OUTPUT_ERROR)
    return _parse_cost_summary_value(execute_result.run_stdout, cost_kind)


__all__ = [
    "DslRunResult",
    "dsl_cost_run",
    "dsl_run",
]
