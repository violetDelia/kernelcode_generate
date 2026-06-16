"""cuda-sm89-lowering pipeline.


功能说明:
- 提供 `cuda-sm89-lowering` pipeline 的 builder。
- 固定 CUDA SM89 首版 lowering 顺序，复用通用 NN / tile / tuning / outline 能力。
- 明确不接入 `MemoryPoolPass(rewrite=True)`，避免把 TLM fragment 语义改写为动态 byte pool。
- 显式使用 `SymbolHoistPipelinePass(cse=False, canonicalize=False)`，保留 CUDA 既有外置 cleanup。
- 通过 registry 装饰器完成 pipeline 注册。

API 列表:
- `build_cuda_sm89_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager`

使用示例:
- from kernel_gen.pipeline import build_cuda_sm89_lowering_pipeline
- pm = build_cuda_sm89_lowering_pipeline({"target": "cuda_sm89"})
- lowered = pm.run(module)

关联文件:
- spec: [spec/pass/pipeline/cuda_sm89_lowering.md](spec/pass/pipeline/cuda_sm89_lowering.md)
- test: [test/passes/pipeline/test_cuda_sm89_lowering.py](test/passes/pipeline/test_cuda_sm89_lowering.py)
- 功能实现: [kernel_gen/pipeline/cuda_sm89_lowering.py](kernel_gen/pipeline/cuda_sm89_lowering.py)
"""

from __future__ import annotations

from xdsl.context import Context
from xdsl.dialects import func
from xdsl.dialects.builtin import ModuleOp, StringAttr
from xdsl.transforms.canonicalize import CanonicalizePass
from xdsl.transforms.common_subexpression_elimination import CommonSubexpressionElimination

from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError
from kernel_gen.passes.arch.arch_parallelize import ArchParallelizePass
from kernel_gen.passes.arch.attach_arch_information import AttachArchInformationPass
from kernel_gen.passes.decompass import DecompassPass
from kernel_gen.passes.hoist import SymbolHoistPipelinePass
from kernel_gen.passes.inline import InlinePass
from kernel_gen.passes.kernel.kernel_aggregate import KernelAggregatePass
from kernel_gen.passes.kernel.kernel_decompose import KernelDecomposePass
from kernel_gen.passes.lowering import NnLoweringPass
from kernel_gen.passes.memory.memory_plan import MemoryPlanPass
from kernel_gen.passes.tuning.outline_device_kernel import OutlineDeviceKernelPass
from kernel_gen.passes.pass_manager import Pass, PassManager
from kernel_gen.passes.producer_consumer_analysis import ProducerConsumerAnalysisPass
from kernel_gen.passes.registry import register_pipeline
from kernel_gen.passes.template_name.infer import TemplateNameInferPass
from kernel_gen.passes.tile.analysis import TileAnalysisPass
from kernel_gen.passes.tuning import KernelPatternAttachPass
from kernel_gen.passes.tuning import TransformApplyPass


class _CudaSm89ArchParallelizePass(Pass):
    """CUDA pipeline 内部 arch mapping 适配层。


    功能说明:
    - 优先调用公开 `ArchParallelizePass.apply(...)`，保持可支持 IR 的 CUDA block mapping。
    - 对 9 个 demo 中暂不被 standalone arch pass 支持的复杂 pattern region 保守 no-op，后续 generated source 仍按 CUDA target 生成具体 kernel。
    - 不改变 standalone `ArchParallelizePass` 的公开失败合同。

    使用示例:
    - pm.add_pass(_CudaSm89ArchParallelizePass("cuda_sm89"))
    """

    name = "arch-parallelize"

    def __init__(self, target: str) -> None:
        """初始化 CUDA arch mapping 适配层。


        功能说明:
        - 创建内部公开 pass 实例并固定 `parallel_level="block"`。
        - 该 wrapper 仅服务 `cuda-sm89-lowering` pipeline，不注册为独立公开 pass。

        使用示例:
        - arch_pass = _CudaSm89ArchParallelizePass("cuda_sm89")
        """

        super().__init__()
        self.delegate = ArchParallelizePass(target=target, parallel_level="block")

    def apply(self, ctx: Context, module: ModuleOp) -> None:
        """执行 CUDA arch mapping 或保守 no-op。


        功能说明:
        - 调用公开 `ArchParallelizePass.apply(...)` 处理可映射 IR。
        - 仅当 standalone pass 报 `unsupported loop structure` 时保守跳过，避免 9 个现有 demo 在 CUDA SourceBundle fallback 前被 pipeline 阻断。
        - 其它错误继续抛出，避免吞掉真实合同失败。

        使用示例:
        - arch_pass.apply(ctx, module)
        """

        try:
            self.delegate.apply(ctx, module)
        except KernelCodeError as exc:
            if "ArchParallelizePassError: unsupported loop structure" not in str(exc):
                raise


class _CudaSm89KernelPatternAttachPass(Pass):
    """CUDA pipeline 内部 matmul pattern 适配层。


    功能说明:
    - 复用公开 `KernelPatternAttachPass.apply(...)` 生成 dispatcher 和 pattern 函数。
    - 仅在 `cuda-sm89-lowering` pipeline 内把 pattern 函数的 transform rule 收口为 C5 确认的
      `matmul{["tlm1", "tlm1", "tlm1"]}`。
    - 不改变 standalone `KernelPatternAttachPass` 的公开合同或 registry options。

    使用示例:
    - pm.add_pass(_CudaSm89KernelPatternAttachPass())
    """

    name = "kernel-pattern-attach"

    def __init__(self) -> None:
        """初始化 CUDA pattern 适配层。


        功能说明:
        - 创建公开 `KernelPatternAttachPass` delegate。
        - 固定 CUDA all-TLM1 transform rule，不新增 pipeline option。

        使用示例:
        - pass_obj = _CudaSm89KernelPatternAttachPass()
        """

        super().__init__()
        self.delegate = KernelPatternAttachPass()

    def apply(self, ctx: Context, module: ModuleOp) -> None:
        """执行 CUDA pattern attach 并改写 transform rule。


        功能说明:
        - 先调用公开 delegate 生成 pattern 函数。
        - 对生成的 `kernel.transform_pipeline` 统一写入 C5 all-TLM1 rule，确保后续
          `TransformApplyPass` 消费时 out/lhs/rhs 三个 memory operand 都 materialize 到 `tlm1`。

        使用示例:
        - pass_obj.apply(Context(), module)
        """

        if not any(isinstance(op, func.FuncOp) for op in module.ops):
            return
        self.delegate.apply(ctx, module)
        c5_pipeline = '--pass "lower-dma-memory-hierarchy={fold=true,apply_op=matmul{[\\"tlm1\\", \\"tlm1\\", \\"tlm1\\"]}}" --pass canonicalize'
        for op in module.ops:
            if not isinstance(op, func.FuncOp):
                continue
            if "kernel.pattern_id" not in op.attributes:
                continue
            op.attributes["kernel.transform_pipeline"] = StringAttr(c5_pipeline)


@register_pipeline("cuda-sm89-lowering")
def build_cuda_sm89_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager:
    """构造 cuda-sm89-lowering pipeline。


    功能说明:
    - 返回 `PassManager(name="cuda-sm89-lowering")`。
    - 仅接受 `target` 选项，默认且唯一合法值为 `cuda_sm89`。
    - pass 顺序在第二段 symbol hoist 后执行 kernel aggregate / decompose，并在 producer-consumer 后直接进入
      `ArchParallelizePass(target="cuda_sm89", parallel_level="block")` 与 `AttachArchInformationPass`。
    - 不接入 `MemoryPoolPass(rewrite=True)`，保证 TLM1/TLM2/TLM3 不被改写成
      `arch.get_dynamic_memory + dma.reinterpret` byte pool 形态。
    - 三段 `symbol-hoist-pipeline` 显式关闭 pass-local `cse` / `canonicalize`，继续依赖外置 cleanup。

    使用示例:
    - pm = build_cuda_sm89_lowering_pipeline()
    - pm = build_cuda_sm89_lowering_pipeline({"target": "cuda_sm89"})
    """

    normalized_options = {} if options is None else dict(options)
    unknown = sorted(set(normalized_options) - {"target"})
    if unknown:
        raise KernelCodeError(
            ErrorKind.CONTRACT,
            ErrorModule.PIPELINE,
            f"cuda-sm89-lowering only accepts target option; got {', '.join(unknown)}",
        )
    target = normalized_options.get("target", "cuda_sm89")
    if target != "cuda_sm89":
        raise KernelCodeError(
            ErrorKind.CONTRACT,
            ErrorModule.PIPELINE,
            "cuda-sm89-lowering target must be cuda_sm89",
        )

    pm = PassManager(name="cuda-sm89-lowering")
    pm.add_pass(InlinePass())
    pm.add_pass(CommonSubexpressionElimination())
    pm.add_pass(CanonicalizePass())
    pm.add_pass(DecompassPass())
    pm.add_pass(NnLoweringPass())
    pm.add_pass(MemoryPlanPass(insert_free=True, reuse=True, fold=False))
    pm.add_pass(SymbolHoistPipelinePass(cse=False, canonicalize=False))
    pm.add_pass(CommonSubexpressionElimination())
    pm.add_pass(CanonicalizePass())
    pm.add_pass(TileAnalysisPass())
    pm.add_pass(_CudaSm89KernelPatternAttachPass())
    pm.add_pass(TransformApplyPass())
    pm.add_pass(MemoryPlanPass(insert_free=True, reuse=True, fold=False))
    pm.add_pass(SymbolHoistPipelinePass(cse=False, canonicalize=False))
    pm.add_pass(CommonSubexpressionElimination())
    pm.add_pass(CanonicalizePass())
    pm.add_pass(KernelAggregatePass(matmul_acc=True))
    pm.add_pass(KernelDecomposePass())
    pm.add_pass(MemoryPlanPass(insert_free=True, reuse=True, fold=False))
    pm.add_pass(SymbolHoistPipelinePass(cse=False, canonicalize=False))
    pm.add_pass(CommonSubexpressionElimination())
    pm.add_pass(CanonicalizePass())
    pm.add_pass(ProducerConsumerAnalysisPass())
    pm.add_pass(CanonicalizePass())
    pm.add_pass(_CudaSm89ArchParallelizePass(target=target))
    pm.add_pass(AttachArchInformationPass(target=target))
    pm.add_pass(OutlineDeviceKernelPass())
    pm.add_pass(TemplateNameInferPass())
    return pm
