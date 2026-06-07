"""emit_c npu_demo arch expectation：launch。

创建者: OpenAI Codex
最后一次更改: OpenAI Codex

功能说明:
- 锁定 `arch.launch` wrapper module 在 `target=npu_demo` 下应发射为 `npu_demo::launch<..., body>(ctx, ...)` 的公开源码口径。
- 覆盖 body 前置声明、body 签名与 wrapper 参数透传的完整成功路径。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/emit_c/npu_demo/arch/launch.py`

关联文件:
- spec: [`spec/dsl/gen_kernel/emit.md`](spec/dsl/gen_kernel/emit.md)
- spec: [`spec/dsl/gen_kernel/emit/npu_demo.md`](spec/dsl/gen_kernel/emit/npu_demo.md)
- spec: [`spec/dialect/arch.md`](spec/dialect/arch.md)
- test: [`test/dsl/test_emit_c.py`](test/dsl/test_emit_c.py)
- 功能实现: [`kernel_gen/dsl/gen_kernel/kernel_emitter.py`](kernel_gen/dsl/gen_kernel/kernel_emitter.py)
- 功能实现: [`expectation/dsl/emit_c/npu_demo/arch/launch.py`](expectation/dsl/emit_c/npu_demo/arch/launch.py)
"""

# Case 列表:
# - emit_c-npu_demo-arch-launch-1: `arch.launch` wrapper module 应生成普通 `npu_demo::KernelContext& ctx` 的 `static` body 前置声明、可写 out 参数签名，以及 `npu_demo::launch<..., body>(ctx, args...)` 调用。

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "kernel_gen").exists())
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.case_runner import print_case_input_ir, raise_if_failures, run_case
from kernel_gen.target import registry as target_registry
from kernel_gen.tools.emitc_case_runner import run_emitc_case


def _build_case_arch_launch() -> str:
    """构造 `arch.launch` wrapper module 的 npu_demo emit_c expectation IR。"""

    block_extent = target_registry.get_target_hardware("npu_demo", "block_num")
    thread_extent = target_registry.get_target_hardware("npu_demo", "thread_num")
    subthread_extent = target_registry.get_target_hardware("npu_demo", "subthread_num")
    shared_memory_size = target_registry.get_target_hardware("npu_demo", "sm_memory_size")
    mem_type = "!nn.memory<[#C4], [#C1], i8, #nn.space<global>>"
    return f"""// COMPILE_ARGS: --pass no-op
// CASE: `arch.launch` wrapper module 应生成 Context-first static body 前置声明、可写 out 参数签名、公开 `slice(ctx, ...)` 搬运调用与 `npu_demo::launch<..., body>(ctx, args...)` 调用。
// CHECK: static void arch_launch_body(npu_demo::KernelContext& ctx, Memory<GM, int8_t>& [[ARG0:{{val}}]], Memory<GM, int8_t>& [[ARG1:{{val}}]], Memory<GM, int8_t>& [[ARG2:{{val}}]]);
// CHECK: static void arch_launch_body(npu_demo::KernelContext& ctx, Memory<GM, int8_t>& [[ARG0_DEF:{{val}}]], Memory<GM, int8_t>& [[ARG1_DEF:{{val}}]], Memory<GM, int8_t>& [[ARG2_DEF:{{val}}]]) {{
// CHECK-NEXT: slice(ctx, [[ARG2_DEF]] /*dst*/, [[ARG0_DEF]] /*source*/, {{0}} /*offset*/, {{[[ARG2_DEF]].get_shape(0)}} /*size*/, {{1}} /*stride*/);
// CHECK-NEXT: }}
// CHECK: void arch_launch_wrapper(Memory<MemorySpace::GM, int8_t>& [[WRAP0:{{val}}]], Memory<MemorySpace::GM, int8_t>& [[WRAP1:{{val}}]], Memory<MemorySpace::GM, int8_t>& [[WRAP2:{{val}}]]) {{
// CHECK-NEXT:     npu_demo::KernelContext ctx;
// CHECK-NEXT:     npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}, arch_launch_body>(ctx, [[WRAP0]], [[WRAP1]], [[WRAP2]]);
// CHECK-NEXT: }}
// CHECK-NOT: template <typename Context>
// CHECK-NOT: static void arch_launch_body(Context& ctx
// CHECK-NOT: npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}, arch_launch_body<npu_demo::KernelContext>>(ctx,

#C4 = #symbol.expr<4>
#C1 = #symbol.expr<1>
#C_BLOCK = #symbol.expr<{block_extent}>
#C_THREAD = #symbol.expr<{thread_extent}>
#C_SUBTHREAD = #symbol.expr<{subthread_extent}>
#C_SHARED_MEMORY = #symbol.expr<{shared_memory_size}>

builtin.module {{
  func.func @arch_launch_body(%0 : {mem_type}, %1 : {mem_type}, %2 : {mem_type}) {{
    "dma.copy"(%2, %0) : ({mem_type}, {mem_type}) -> ()
    func.return
  }}

  func.func @arch_launch_wrapper(%0 : {mem_type}, %1 : {mem_type}, %2 : {mem_type}) {{
    %3 = symbol.const {block_extent} : !symbol.int<#C_BLOCK>
    %4 = symbol.const {thread_extent} : !symbol.int<#C_THREAD>
    %5 = symbol.const {subthread_extent} : !symbol.int<#C_SUBTHREAD>
    %6 = symbol.const {shared_memory_size} : !symbol.int<#C_SHARED_MEMORY>
    arch.launch<%3, %4, %5, %6>(@arch_launch_body, %0, %1, %2) : ({mem_type}, {mem_type}, {mem_type}) -> ()
    func.return
  }}
}}"""


def _case_arch_launch() -> None:
    """运行 `arch.launch` wrapper module 的 npu_demo emit_c 合同。"""

    block_extent = target_registry.get_target_hardware("npu_demo", "block_num")
    thread_extent = target_registry.get_target_hardware("npu_demo", "thread_num")
    subthread_extent = target_registry.get_target_hardware("npu_demo", "subthread_num")
    shared_memory_size = target_registry.get_target_hardware("npu_demo", "sm_memory_size")
    case_text = _build_case_arch_launch()
    print_case_input_ir(
        "emit_c-npu_demo-arch-launch-1",
        case_text,
        fallback="arch.launch wrapper module 应生成 Context-first static body 前置声明、可写 out 参数签名与 npu_demo::launch<..., body>(ctx, args...) 调用。",
    )
    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/arch/launch.py",
        op_name="arch.launch",
        expected_snippets=[
            "static void arch_launch_body(npu_demo::KernelContext& ctx, Memory<GM, int8_t>&",
            "slice(ctx,",
            " /*dst*/, ",
            " /*source*/, ",
            "{",
            "/*offset*/",
            "/*size*/",
            "/*stride*/",
            "void arch_launch_wrapper(",
            "npu_demo::KernelContext ctx;",
            "npu_demo::launch<",
            ", arch_launch_body>(ctx,",
        ],
        forbidden_snippets=[
            "arch.launch",
            "static void arch_launch_body(Memory<GM, int8_t>&",
            "template <typename Context>",
            "static void arch_launch_body(Context& ctx",
            ", arch_launch_body<npu_demo::KernelContext>>(ctx,",
            "Vector(", "static_cast<long long>",
            (
                f"npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}>"
                "(arch_launch_body,"
            ),
            (
                f"npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}>"
                "(ctx, arch_launch_body<npu_demo::KernelContext>,"
            ),
            (
                f"npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}>"
                "(arch_launch_body<npu_demo::KernelContext>, ctx,"
            ),
            (
                f"npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}>"
                "(ctx, arch_launch_body,"
            ),
            (
                f"npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}>"
                "(arch_launch_body, ctx,"
            ),
        ],
    )


def main() -> None:
    """运行 `arch.launch` 的 emit_c expectation。"""

    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "emit_c-npu_demo-arch-launch-1", _case_arch_launch)
    raise_if_failures("emit_c npu_demo arch launch expectation", failures)


if __name__ == "__main__":
    main()
