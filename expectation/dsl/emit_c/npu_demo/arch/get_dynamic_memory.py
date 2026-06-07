"""emit_c npu_demo arch expectation：get_dynamic_memory。

创建者: OpenAI Codex
最后一次更改: OpenAI Codex

功能说明:
- 锁定 `arch.get_dynamic_memory` 在 `npu_demo` 下应发射为 `get_dynamic_memory<Space>()` 的公开源码口径。
- 覆盖当前 emitter 已支持的片上动态内存空间，不残留原始 dialect op 文本。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/emit_c/npu_demo/arch/get_dynamic_memory.py`

关联文件:
- spec: [`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)
- spec: [`spec/dialect/arch.md`](spec/dialect/arch.md)
- test: [`test/dsl/test_emit_c.py`](test/dsl/test_emit_c.py)
- 功能实现: [`kernel_gen/dsl/gen_kernel/emit/npu_demo/arch/get_dynamic_memory.py`](kernel_gen/dsl/gen_kernel/emit/npu_demo/arch/get_dynamic_memory.py)
- 功能实现: [`expectation/dsl/emit_c/npu_demo/arch/get_dynamic_memory.py`](expectation/dsl/emit_c/npu_demo/arch/get_dynamic_memory.py)
"""

# Case 列表:
# - emit_c-npu_demo-arch-get_dynamic_memory-1: `arch.get_dynamic_memory` 在 context-first launch body 中参与 `dma.copy` 时，应生成 `get_dynamic_memory<Space>()`，并通过公开 `slice(ctx, ...)` 搬运接口消费真实 `Memory` 视图。

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "kernel_gen").exists())
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.case_runner import print_case_input_ir, raise_if_failures, run_case
from expectation.utils.emitc import cpp_space_name
from expectation.utils.random import get_random_onchip_memory_space
from expectation.utils.random_utils import memory_space_ir_name
from kernel_gen.target import registry as target_registry
from kernel_gen.symbol_variable.memory import MemorySpace
from kernel_gen.tools.emitc_case_runner import run_emitc_case


def _build_case_arch_get_dynamic_memory() -> tuple[str, str]:
    """构造 `arch.get_dynamic_memory` 的 npu_demo emit_c expectation IR。"""
    space = get_random_onchip_memory_space(
        exclude=(MemorySpace.SM, MemorySpace.LM),
    )
    block_extent = target_registry.get_target_hardware("npu_demo", "block_num")
    thread_extent = target_registry.get_target_hardware("npu_demo", "thread_num")
    subthread_extent = target_registry.get_target_hardware("npu_demo", "subthread_num")
    shared_memory_size = target_registry.get_target_hardware("npu_demo", "sm_memory_size")
    space_ir = memory_space_ir_name(space)
    space_cpp = cpp_space_name(space)
    src_mem_type = f"!nn.memory<[#S_Q], [#C1], i8, #nn.space<{space_ir}>>"
    gm_mem_type = "!nn.memory<[#S_Q], [#C1], i8, #nn.space<global>>"
    case_text = f"""// COMPILE_ARGS: --pass no-op
// CASE: `arch.get_dynamic_memory` 在完整 launch module 的 context-first body 中参与 `dma.copy` 时，应发射为 `get_dynamic_memory<Space>()`，并通过公开 `slice(ctx, ...)` 搬运接口消费真实 Memory 视图。
// CHECK: static void arch_get_dynamic_memory_body(npu_demo::KernelContext& ctx, Memory<GM, int8_t>& [[LHS_BODY:{{val}}]], Memory<GM, int8_t>& [[RHS_BODY:{{val}}]], Memory<GM, int8_t>& [[DST_BODY:{{val}}]])
// CHECK-NEXT:     Memory<{space_cpp}, int8_t> [[SRC:{{val}}]] = npu_demo::get_dynamic_memory<{space_cpp}>();
// CHECK-NEXT:     slice(ctx, [[DST_BODY]] /*dst*/, [[SRC]] /*source*/, {{0}} /*offset*/, {{[[DST_BODY]].get_shape(0)}} /*size*/, {{1}} /*stride*/);
// CHECK-NEXT: }}
// CHECK: void arch_get_dynamic_memory_wrapper(Memory<MemorySpace::GM, int8_t>& [[LHS:{{val}}]], Memory<MemorySpace::GM, int8_t>& [[RHS:{{val}}]], Memory<MemorySpace::GM, int8_t>& [[DST:{{val}}]]) {{
// CHECK: npu_demo::KernelContext ctx;
// CHECK: npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}, arch_get_dynamic_memory_body>(ctx, [[LHS]], [[RHS]], [[DST]]);
// CHECK-NEXT: }}
// CHECK-NOT: template <typename Context>
// CHECK-NOT: static void arch_get_dynamic_memory_body(Context& ctx
// CHECK-NOT: npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}, arch_get_dynamic_memory_body<npu_demo::KernelContext>>(ctx,
// CHECK-NOT: ctx.get_dynamic_memory
// CHECK-NOT: ctx.template get_dynamic_memory
// CHECK-NOT: npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}>(arch_get_dynamic_memory_body,
// CHECK-NOT: npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}>(ctx, arch_get_dynamic_memory_body<npu_demo::KernelContext>,
// CHECK-NOT: npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}>(arch_get_dynamic_memory_body<npu_demo::KernelContext>, ctx,

#S_Q = #symbol.expr<?>
#C1 = #symbol.expr<1>
builtin.module {{
  func.func @arch_get_dynamic_memory_body(%0 : {gm_mem_type}, %1 : {gm_mem_type}, %2 : {gm_mem_type}) {{
    %3 = arch.get_dynamic_memory #nn.space<{space_ir}> : {src_mem_type}
    "dma.copy"(%2, %3) : ({gm_mem_type}, {src_mem_type}) -> ()
    func.return
  }}

  func.func @arch_get_dynamic_memory_wrapper(%0 : {gm_mem_type}, %1 : {gm_mem_type}, %2 : {gm_mem_type}) {{
    %3 = symbol.const {block_extent} : !symbol.int<#symbol.expr<{block_extent}>>
    %4 = symbol.const {thread_extent} : !symbol.int<#symbol.expr<{thread_extent}>>
    %5 = symbol.const {subthread_extent} : !symbol.int<#symbol.expr<{subthread_extent}>>
    %6 = symbol.const {shared_memory_size} : !symbol.int<#symbol.expr<{shared_memory_size}>>
    arch.launch<%3, %4, %5, %6>(@arch_get_dynamic_memory_body, %0, %1, %2) : ({gm_mem_type}, {gm_mem_type}, {gm_mem_type}) -> ()
    func.return
  }}
}}"""
    return case_text, space_cpp


def _case_arch_get_dynamic_memory() -> None:
    """运行 `arch.get_dynamic_memory` 的 npu_demo emit_c 合同。"""

    block_extent = target_registry.get_target_hardware("npu_demo", "block_num")
    thread_extent = target_registry.get_target_hardware("npu_demo", "thread_num")
    subthread_extent = target_registry.get_target_hardware("npu_demo", "subthread_num")
    shared_memory_size = target_registry.get_target_hardware("npu_demo", "sm_memory_size")
    case_text, space_cpp = _build_case_arch_get_dynamic_memory()
    print_case_input_ir(
        "emit_c-npu_demo-arch-get_dynamic_memory-1",
        case_text,
        fallback="arch.get_dynamic_memory 在完整 launch module 的 context-first body 中参与 dma.copy 时应生成 npu_demo::get_dynamic_memory<Space>()，并通过公开 slice(ctx, ...) 搬运接口消费 Memory 视图。",
    )
    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/arch/get_dynamic_memory.py",
        op_name="arch.get_dynamic_memory",
        expected_snippets=[
            "static void arch_get_dynamic_memory_body(npu_demo::KernelContext& ctx, Memory<GM, int8_t>&",
            f"Memory<{space_cpp}, int8_t>",
            f"npu_demo::get_dynamic_memory<{space_cpp}>()",
            "slice(ctx,",
            " /*dst*/, ",
            " /*source*/, ",
            "{",
            "/*offset*/",
            "/*size*/",
            "/*stride*/",
            "npu_demo::KernelContext ctx;",
            "npu_demo::launch<",
            ", arch_get_dynamic_memory_body>(ctx,",
        ],
        forbidden_snippets=[
            "arch.get_dynamic_memory",
            "template <typename Context>",
            "static void arch_get_dynamic_memory_body(Context& ctx",
            "ctx.get_dynamic_memory",
            "ctx.template get_dynamic_memory",
            ", arch_get_dynamic_memory_body<npu_demo::KernelContext>>(ctx,",
            "Vector(", "static_cast<long long>",
            (
                f"npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}>"
                "(arch_get_dynamic_memory_body,"
            ),
            (
                f"npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}>"
                "(ctx, arch_get_dynamic_memory_body<npu_demo::KernelContext>,"
            ),
            (
                f"npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}>"
                "(arch_get_dynamic_memory_body<npu_demo::KernelContext>, ctx,"
            ),
            (
                f"npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}>"
                "(ctx, arch_get_dynamic_memory_body,"
            ),
            (
                f"npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}>"
                "(arch_get_dynamic_memory_body, ctx,"
            ),
        ],
    )


def main() -> None:
    """运行 `arch.get_dynamic_memory` 的 emit_c expectation。"""

    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "emit_c-npu_demo-arch-get_dynamic_memory-1", _case_arch_get_dynamic_memory)
    raise_if_failures("emit_c npu_demo arch get_dynamic_memory expectation", failures)


if __name__ == "__main__":
    main()
