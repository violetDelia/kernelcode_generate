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
import re
from typing import Protocol, TypeAlias

from xdsl.dialects import func
from xdsl.dialects.builtin import ModuleOp

from kernel_gen.core.config import get_target, restore_config, set_dump_dir, snapshot_config
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
VALID_DSL_COST_KINDS = ("DMA", "MAC", "DMA1", "DMA2", "DMA3", "DMA4", "VECTOR1", "VECTOR2")
DMA_DSL_COST_KINDS = ("DMA", "DMA1", "DMA2", "DMA3", "DMA4")
DSL_COST_KIND_ERROR = "DslCostRunInvalidCostKind: cost_kind must be one of ['DMA', 'MAC']"
DSL_COST_TARGET_ERROR = "DslCostRunInvalidTarget: dsl_cost_run only supports target 'npu_demo'"
DSL_COST_OUTPUT_ERROR = "DslCostRunExecutionFailed: cost wrapper execution failed"
DMA_COST_RAW_HELPER_SOURCE = r"""
template <typename T>
S_INT kg_cost_dma_raw_bytes_for_elements(S_INT elements) {
    if (elements <= 0) {
        return 0;
    }
    return elements * static_cast<S_INT>(sizeof(T));
}

S_INT kg_cost_dma_raw_vector_element_count(const Vector& size) {
    S_INT count = 1;
    for (unsigned long long i = 0; i < size.size(); ++i) {
        count *= size[i];
    }
    return count;
}

template <MemorySpace Space>
constexpr bool kg_cost_dma_is_gm_space() {
    return Space == GM;
}

template <MemorySpace Space>
constexpr bool kg_cost_dma_is_tsm_space() {
    return Space == TSM;
}

template <MemorySpace Space>
constexpr bool kg_cost_dma_is_tlm_space() {
    return Space == TLM1 || Space == TLM2 || Space == TLM3;
}

template <MemorySpace Space>
constexpr bool kg_cost_dma_is_tsm_or_tlm_space() {
    return kg_cost_dma_is_tsm_space<Space>() || kg_cost_dma_is_tlm_space<Space>();
}

template <MemorySpace TargetSpace, MemorySpace SourceSpace, cost::CostKind Kind>
constexpr bool kg_cost_dma_matches_kind() {
    if constexpr (Kind == cost::CostKind::DMA1) {
        return kg_cost_dma_is_gm_space<SourceSpace>() && kg_cost_dma_is_tsm_or_tlm_space<TargetSpace>();
    }
    if constexpr (Kind == cost::CostKind::DMA2) {
        return kg_cost_dma_is_tsm_or_tlm_space<SourceSpace>() && kg_cost_dma_is_gm_space<TargetSpace>();
    }
    if constexpr (Kind == cost::CostKind::DMA3) {
        return kg_cost_dma_is_tsm_space<SourceSpace>() && kg_cost_dma_is_tlm_space<TargetSpace>();
    }
    if constexpr (Kind == cost::CostKind::DMA4) {
        return kg_cost_dma_is_tsm_space<SourceSpace>() && kg_cost_dma_is_tsm_space<TargetSpace>();
    }
    return false;
}

template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, cost::CostKind Kind>
S_INT kg_cost_dma_bytes_copy(const Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source) {
    (void)source;
    if constexpr (kg_cost_dma_matches_kind<TargetSpace, SourceSpace, Kind>()) {
        return kg_cost_dma_raw_bytes_for_elements<T>(target.element_count());
    }
    return 0;
}

template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, cost::CostKind Kind>
S_INT kg_cost_dma_bytes_slice(
    const Memory<TargetSpace, T>& target,
    const Memory<SourceSpace, T>& source,
    const Vector& offset,
    const Vector& size,
    const Vector& stride) {
    (void)target;
    (void)source;
    (void)offset;
    (void)stride;
    if constexpr (kg_cost_dma_matches_kind<TargetSpace, SourceSpace, Kind>()) {
        return kg_cost_dma_raw_bytes_for_elements<T>(kg_cost_dma_raw_vector_element_count(size));
    }
    return 0;
}

template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, cost::CostKind Kind>
S_INT kg_cost_dma_bytes_deslice(
    const Memory<TargetSpace, T>& target,
    const Memory<SourceSpace, T>& source,
    const Vector& offset,
    const Vector& size,
    const Vector& stride) {
    (void)target;
    (void)source;
    (void)offset;
    (void)stride;
    if constexpr (kg_cost_dma_matches_kind<TargetSpace, SourceSpace, Kind>()) {
        return kg_cost_dma_raw_bytes_for_elements<T>(kg_cost_dma_raw_vector_element_count(size));
    }
    return 0;
}

template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType, cost::CostKind Kind>
S_INT kg_cost_dma_bytes_img2col1d(
    const Memory<OutputSpace, OutType>& out,
    const Memory<InputSpace, InType>& input,
    long long k,
    long long s,
    long long d,
    long long p_left,
    long long p_right) {
    (void)input;
    (void)k;
    (void)s;
    (void)d;
    (void)p_left;
    (void)p_right;
    if constexpr (Kind == cost::CostKind::DMA3) {
        return kg_cost_dma_raw_bytes_for_elements<OutType>(out.element_count());
    }
    return 0;
}

template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType, cost::CostKind Kind>
S_INT kg_cost_dma_bytes_img2col2d(
    const Memory<OutputSpace, OutType>& out,
    const Memory<InputSpace, InType>& input,
    long long kh,
    long long kw,
    long long sh,
    long long sw,
    long long dh,
    long long dw,
    long long ph,
    long long pw,
    long long pl,
    long long pr) {
    (void)input;
    (void)kh;
    (void)kw;
    (void)sh;
    (void)sw;
    (void)dh;
    (void)dw;
    (void)ph;
    (void)pw;
    (void)pl;
    (void)pr;
    if constexpr (Kind == cost::CostKind::DMA3) {
        return kg_cost_dma_raw_bytes_for_elements<OutType>(out.element_count());
    }
    return 0;
}
"""


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
    - 接受 npu_demo 七类 kind，并兼容历史 `DMA/MAC` 工具合同。
    - 仍拒绝组合字符串，避免 `dsl_cost_run(...)` 一次请求多个 sibling。

    使用示例:
    - _validate_dsl_cost_kind("VECTOR1")

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_cost_run.py](test/tools/test_dsl_cost_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    if cost_kind not in VALID_DSL_COST_KINDS:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, DSL_COST_KIND_ERROR)


def _find_cost_func_by_sym_name(module: ModuleOp, sym_name: str) -> func.FuncOp:
    """按公开 cost function 符号名查找 `func.func`。


    功能说明:
    - `dsl_cost_run(...)` 需要 pipeline 生成 `_cost_<kind>_<device>` sibling 函数。
    - 缺失时返回稳定合同错误，避免后续源码 wrapper 指向不存在入口。

    使用示例:
    - cost_func = _find_cost_func_by_sym_name(module, "_cost_VECTOR1_add_kernel_device")

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_cost_run.py](test/tools/test_dsl_cost_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    for op in module.ops:
        if isinstance(op, func.FuncOp) and op.sym_name.data == sym_name:
            return op
    match = re.match(r"^_cost_([^_]+)_", sym_name)
    kind_text = match.group(1) if match is not None else ""
    if kind_text:
        message = f"DslCostRunMissingCostFunction: lowered module does not contain _cost_{kind_text}_ sibling function"
    else:
        message = f"DslCostRunMissingCostFunction: cost function '{sym_name}' not found"
    raise KernelCodeError(
        ErrorKind.CONTRACT,
        ErrorModule.TOOLS,
        message,
    )


def _split_cpp_params(params_text: str) -> tuple[str, ...]:
    """按 C++ 函数形参顶层逗号切分参数。


    功能说明:
    - 忽略模板参数、括号与数组维度内部的逗号。
    - 仅服务 `dsl_cost_run(...)` 当前文件内生成的 cost 捕获 wrapper，不外露为工具 API。

    使用示例:
    - params = _split_cpp_params("Memory<GM, float>& out, Memory<GM, float>& lhs")

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_cost_run.py](test/tools/test_dsl_cost_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    if not params_text.strip():
        return ()
    parts: list[str] = []
    current: list[str] = []
    angle_depth = 0
    paren_depth = 0
    bracket_depth = 0
    for ch in params_text:
        if ch == "<":
            angle_depth += 1
        elif ch == ">":
            angle_depth = max(0, angle_depth - 1)
        elif ch == "(":
            paren_depth += 1
        elif ch == ")":
            paren_depth = max(0, paren_depth - 1)
        elif ch == "[":
            bracket_depth += 1
        elif ch == "]":
            bracket_depth = max(0, bracket_depth - 1)
        if ch == "," and angle_depth == 0 and paren_depth == 0 and bracket_depth == 0:
            item = "".join(current).strip()
            if item:
                parts.append(item)
            current = []
            continue
        current.append(ch)
    item = "".join(current).strip()
    if item:
        parts.append(item)
    return tuple(parts)


def _cpp_param_name(param_text: str) -> str:
    """提取 C++ 函数形参名。


    功能说明:
    - 从 `Memory<GM, float>& out` 这类参数文本中取出末尾变量名。
    - 解析失败时抛出 `DslCostRunInvalidSource`，防止生成错误 wrapper。

    使用示例:
    - name = _cpp_param_name("Memory<GM, float>& out")

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_cost_run.py](test/tools/test_dsl_cost_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    match = re.search(r"([A-Za-z_]\w*)\s*(?:\[[^\]]*\])?\s*$", param_text.strip())
    if match is None:
        raise KernelCodeError(
            ErrorKind.CONTRACT,
            ErrorModule.TOOLS,
            f"DslCostRunInvalidSource: cannot parse parameter name from '{param_text}'",
        )
    return match.group(1)


def _nearest_template_header(source: str, function_start: int) -> str:
    """读取函数声明前紧邻的 C++ template header。


    功能说明:
    - cost sibling 在 template-name-infer 后可能是 `template <typename Tn>` 函数。
    - 捕获 wrapper 必须复用同一个 template header，才能由执行引擎按真实 runtime dtype 实例化。
    - 非 templated cost function 返回空字符串。

    使用示例:
    - header = _nearest_template_header(source, match.start())

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_cost_run.py](test/tools/test_dsl_cost_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    prefix = source[:function_start].rstrip()
    match = re.search(r"(template\s*<[^>]+>)\s*$", prefix)
    return "" if match is None else f"{match.group(1)}\n"


def _insert_dma_cost_raw_helpers(source: str) -> str:
    """向生成源码插入 `dsl_cost_run(...)` 专用 DMA raw-bytes helper。


    功能说明:
    - helper 只存在于本次生成源码中，用于 DMA kind 把匹配 helper 的返回值改为 raw bytes。
    - 不依赖 `include/npu_demo/cost/detail`，也不把 DMA 聚合状态写成 include 公开或非公开跨文件 hook。

    使用示例:
    - source = _insert_dma_cost_raw_helpers(source)

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_cost_run.py](test/tools/test_dsl_cost_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    marker = "using namespace npu_demo;\n"
    if marker not in source:
        raise KernelCodeError(
            ErrorKind.CONTRACT,
            ErrorModule.TOOLS,
            "DslCostRunInvalidSource: generated npu_demo source is missing namespace import",
        )
    return source.replace(marker, f"{marker}\n{DMA_COST_RAW_HELPER_SOURCE.strip()}\n\n", 1)


def _rewrite_dma_cost_helpers_to_raw_bytes(source: str) -> str:
    """把 DMA cost sibling 中的公开 cost helper 调用改写为 raw-bytes helper。


    功能说明:
    - `include/npu_demo/cost` 公开 helper 保持节点级 `ceil(bytes / 64)` 语义。
    - `dsl_cost_run(...)` 的 DMA 聚合合同要求同一 cost function 内先加总 raw bytes，再统一取整。
    - 因此只在当前生成源码中重写成本 sibling 的 DMA/Img2Col 成本 helper 调用，不修改 include 公开 API。

    使用示例:
    - source = _rewrite_dma_cost_helpers_to_raw_bytes(source)

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_cost_run.py](test/tools/test_dsl_cost_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    rewritten = source
    replacements = (
        ("cost::copy<", "kg_cost_dma_bytes_copy<"),
        ("cost::slice<", "kg_cost_dma_bytes_slice<"),
        ("cost::deslice<", "kg_cost_dma_bytes_deslice<"),
        ("cost::img2col1d<", "kg_cost_dma_bytes_img2col1d<"),
        ("cost::img2col2d<", "kg_cost_dma_bytes_img2col2d<"),
    )
    for old, new in replacements:
        rewritten = rewritten.replace(old, new)
    return _insert_dma_cost_raw_helpers(rewritten)


def _append_cost_capture_wrapper(source: str, cost_entry_name: str, cost_kind: str) -> tuple[str, str]:
    """为 cost 函数源码追加可执行捕获 wrapper。


    功能说明:
    - 当前执行引擎公开 `execute(...)` 只返回执行状态，不捕获 C++ 函数返回值。
    - 这里在生成源码末尾追加 `void` wrapper，把 `S_INT` cost 返回值写入额外 `Memory<GM, S_INT>&` 输出参数。
    - DMA kind 先在当前生成源码中把匹配 cost helper 改写为 raw bytes helper，再由 wrapper 返回 `ceil(total_bytes/64)`。
    - wrapper 只在当前文件内部为 `dsl_cost_run(...)` 服务，不新增执行引擎公开 API。

    使用示例:
    - wrapped_source, wrapper_name = _append_cost_capture_wrapper(source, "_cost_VECTOR1_add", "VECTOR1")

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_cost_run.py](test/tools/test_dsl_cost_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    pattern = re.compile(rf"\bS_INT\s+{re.escape(cost_entry_name)}\s*\((?P<params>.*?)\)\s*\{{", re.DOTALL)
    match = pattern.search(source)
    if match is None:
        raise KernelCodeError(
            ErrorKind.CONTRACT,
            ErrorModule.TOOLS,
            f"DslCostRunMissingCostFunction: cost function '{cost_entry_name}' not found in generated source",
        )
    params = _split_cpp_params(match.group("params"))
    template_header = _nearest_template_header(source, match.start())
    param_names = tuple(_cpp_param_name(param) for param in params)
    wrapper_name = f"_kg_capture_{_sanitize_dump_component(cost_entry_name)}"
    params_text = ", ".join((*params, "Memory<GM, S_INT>& __kg_cost_output"))
    call_args = ", ".join(param_names)
    call_text = f"{cost_entry_name}({call_args})" if call_args else f"{cost_entry_name}()"
    if cost_kind in DMA_DSL_COST_KINDS:
        source = _rewrite_dma_cost_helpers_to_raw_bytes(source)
        body = (
            f"    S_INT __kg_total_dma_bytes = {call_text};\n"
            "    S_INT __kg_cost_result = __kg_total_dma_bytes <= 0 ? 0 : ((__kg_total_dma_bytes + 63) / 64);\n"
        )
    else:
        body = (
            f"    S_INT __kg_cost_result = static_cast<S_INT>({call_text});\n"
        )
    suffix = (
        "\n"
        f"{template_header}"
        f"void {wrapper_name}({params_text}) {{\n"
        f"{body}"
        "#ifdef TRANCE\n"
        "    kernelcode::trance::print_return_i64(kernelcode::trance::current_sink(), __kg_cost_result);\n"
        "#endif\n"
        "    __kg_cost_output.data()[0] = __kg_cost_result;\n"
        "}\n"
    )
    return source.rstrip() + "\n" + suffix, wrapper_name


def _select_source_and_cost_entry(
    module: ModuleOp,
    emit_context: EmitCContext,
    cost_kind: str,
) -> tuple[str, str, func.FuncOp]:
    """根据 lowered module 选择 cost 源码与执行入口。


    功能说明:
    - 复用 `npu_demo` wrapper/body 公开选择规则，找到 device body 后拼出 sibling cost 函数名。
    - 只支持 `target="npu_demo"`，其他 target 直接按公开错误失败。

    使用示例:
    - source, entry_name, func_op = _select_source_and_cost_entry(module, EmitCContext(), "VECTOR1")

    关联文件:
    - spec: [spec/tools/dsl_run.md](spec/tools/dsl_run.md)
    - test: [test/tools/test_dsl_cost_run.py](test/tools/test_dsl_cost_run.py)
    - 功能实现: [kernel_gen/tools/dsl_run.py](kernel_gen/tools/dsl_run.py)
    """

    if _emitc_target_name(emit_context) != "npu_demo":
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, DSL_COST_TARGET_ERROR)
    func_ops = [op for op in module.ops if isinstance(op, func.FuncOp)]
    wrapper_candidates = [
        func_op
        for func_op in func_ops
        if any(item.name == "arch.launch" for item in func_op.body.block.ops)
    ]
    if len(wrapper_candidates) != 1:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, NPU_DEMO_WRAPPER_ERROR)
    wrapper_func = wrapper_candidates[0]
    wrapper_launch = next(item for item in wrapper_func.body.block.ops if item.name == "arch.launch")
    body_entry_name = wrapper_launch.callee.root_reference.data
    cost_entry_name = f"_cost_{cost_kind}_{body_entry_name}"
    cost_func = _find_cost_func_by_sym_name(module, cost_entry_name)
    return gen_kernel(module, emit_context), cost_entry_name, cost_func


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
    - 通过当前文件内生成的捕获 wrapper 读取 cost 函数 `S_INT` 返回值，不改执行引擎公开 API。

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
        if dump_kernel_writer is not None:
            set_dump_dir(dump_kernel_writer.root)
        source, cost_entry_name, _ = _select_source_and_cost_entry(lowered_module, emit_context, cost_kind)
        cost_source, wrapper_name = _append_cost_capture_wrapper(source, cost_entry_name, cost_kind)
        if dump_kernel_writer is not None:
            dump_kernel_writer.write("99-cost-source.cpp", cost_source)
            set_dump_dir(None)
        engine = ExecutionEngine(target=_emitc_target_name(emit_context))
        compiled_kernel = engine.compile(source=cost_source, function=wrapper_name)
    finally:
        restore_config(source_snapshot)

    import numpy

    cost_output = numpy.zeros((1,), dtype=numpy.int64)
    execute_result = compiled_kernel.execute(args=(*execute_args, cost_output))
    if not execute_result.ok:
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, DSL_COST_OUTPUT_ERROR)
    return int(cost_output[0])


__all__ = [
    "DslRunResult",
    "dsl_cost_run",
    "dsl_run",
]
