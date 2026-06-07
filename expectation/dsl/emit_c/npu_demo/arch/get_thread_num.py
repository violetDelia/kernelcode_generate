"""emit_c npu_demo arch expectation：get_thread_num。

创建者: OpenAI Codex
最后一次更改: OpenAI Codex

功能说明:
- 锁定 `arch.get_thread_num` 在 `npu_demo` 下应发射为 `thread_num()` 的公开源码口径。
- 覆盖节点级成功路径，不残留原始 dialect op 文本。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/emit_c/npu_demo/arch/get_thread_num.py`

关联文件:
- spec: [`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)
- spec: [`spec/dialect/arch.md`](spec/dialect/arch.md)
- test: [`test/dsl/test_emit_c.py`](test/dsl/test_emit_c.py)
- 功能实现: [`kernel_gen/dsl/gen_kernel/emit/npu_demo/arch/get_thread_num.py`](kernel_gen/dsl/gen_kernel/emit/npu_demo/arch/get_thread_num.py)
- 功能实现: [`expectation/dsl/emit_c/npu_demo/arch/get_thread_num.py`](expectation/dsl/emit_c/npu_demo/arch/get_thread_num.py)
"""

# Case 列表:
# - emit_c-npu_demo-arch-get_thread_num-1: `arch.get_thread_num` 在 context-first launch body 中参与后续 `symbol.mul` 时，应先发射为 `thread_num()` 对应的 `S_INT` 局部值。

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "kernel_gen").exists())
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.case_runner import print_case_input_ir, raise_if_failures, run_case
from kernel_gen.tools.emitc_case_runner import run_emitc_case
from kernel_gen.target import registry as target_registry


def _build_case_arch_get_thread_num() -> str:
    """构造 `arch.get_thread_num` 的 npu_demo emit_c expectation IR。"""
    block_extent = target_registry.get_target_hardware("npu_demo", "block_num")
    thread_extent = target_registry.get_target_hardware("npu_demo", "thread_num")
    subthread_extent = target_registry.get_target_hardware("npu_demo", "subthread_num")
    shared_memory_size = target_registry.get_target_hardware("npu_demo", "sm_memory_size")
    mem_type = "!nn.memory<[#C4], [#C1], i8, #nn.space<global>>"
    return f"""// COMPILE_ARGS: --pass no-op
// CASE: `arch.get_thread_num` 在完整 launch module 的 context-first body 中参与 `symbol.mul` 时，应先发射为 `thread_num()`。
// CHECK: static void arch_get_thread_num_body(npu_demo::KernelContext& ctx, Memory<GM, int8_t>& [[ARG0:{{val}}]], Memory<GM, int8_t>& [[ARG1:{{val}}]], Memory<GM, int8_t>& [[ARG2:{{val}}]])
// CHECK: S_INT
// CHECK: npu_demo::thread_num()
// CHECK: * 2
// CHECK: void arch_get_thread_num_wrapper(Memory<MemorySpace::GM, int8_t>& [[WRAP0:{{val}}]], Memory<MemorySpace::GM, int8_t>& [[WRAP1:{{val}}]], Memory<MemorySpace::GM, int8_t>& [[WRAP2:{{val}}]]) {{
// CHECK: npu_demo::KernelContext ctx;
// CHECK: npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}, arch_get_thread_num_body>(ctx, [[WRAP0]], [[WRAP1]], [[WRAP2]]);
// CHECK-NOT: template <typename Context>
// CHECK-NOT: static void arch_get_thread_num_body(Context& ctx
// CHECK-NOT: npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}, arch_get_thread_num_body<npu_demo::KernelContext>>(ctx,
// CHECK-NOT: ctx.thread_num()
// CHECK-NOT: npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}>(arch_get_thread_num_body,
// CHECK-NOT: npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}>(ctx, arch_get_thread_num_body<npu_demo::KernelContext>,
// CHECK-NOT: npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}>(arch_get_thread_num_body<npu_demo::KernelContext>, ctx,

#C1 = #symbol.expr<1>
#C2 = #symbol.expr<2>
#C4 = #symbol.expr<4>
#S_thread_num = #symbol.expr<thread_num>
#S1 = #symbol.expr<2*thread_num>
builtin.module {{
  func.func @arch_get_thread_num_body(%0 : {mem_type}, %1 : {mem_type}, %2 : {mem_type}) {{
    %3 = arch.get_thread_num : !symbol.int<#S_thread_num>
    %4 = symbol.const 2 : !symbol.int<#C2>
    %5 = "symbol.mul"(%3, %4) : (!symbol.int<#S_thread_num>, !symbol.int<#C2>) -> !symbol.int<#S1>
    func.return
  }}

  func.func @arch_get_thread_num_wrapper(%0 : {mem_type}, %1 : {mem_type}, %2 : {mem_type}) {{
    %3 = symbol.const {block_extent} : !symbol.int<#symbol.expr<{block_extent}>>
    %4 = symbol.const {thread_extent} : !symbol.int<#symbol.expr<{thread_extent}>>
    %5 = symbol.const {subthread_extent} : !symbol.int<#symbol.expr<{subthread_extent}>>
    %6 = symbol.const {shared_memory_size} : !symbol.int<#symbol.expr<{shared_memory_size}>>
    arch.launch<%3, %4, %5, %6>(@arch_get_thread_num_body, %0, %1, %2) : ({mem_type}, {mem_type}, {mem_type}) -> ()
    func.return
  }}
}}"""


def _case_arch_get_thread_num() -> None:
    """运行 `arch.get_thread_num` 的 npu_demo emit_c 合同。"""

    block_extent = target_registry.get_target_hardware("npu_demo", "block_num")
    thread_extent = target_registry.get_target_hardware("npu_demo", "thread_num")
    subthread_extent = target_registry.get_target_hardware("npu_demo", "subthread_num")
    shared_memory_size = target_registry.get_target_hardware("npu_demo", "sm_memory_size")
    case_text = _build_case_arch_get_thread_num()
    print_case_input_ir(
        "emit_c-npu_demo-arch-get_thread_num-1",
        case_text,
        fallback="arch.get_thread_num 在完整 launch module 的 body 中参与 symbol.mul 时应先 materialize 为 S_INT 局部值并调用 thread_num()。",
    )
    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/arch/get_thread_num.py",
        op_name="arch.get_thread_num",
        expected_snippets=[
            "static void arch_get_thread_num_body(npu_demo::KernelContext& ctx, Memory<GM, int8_t>&",
            "S_INT",
            "npu_demo::thread_num()",
            "npu_demo::KernelContext ctx;",
            "npu_demo::launch<",
            ", arch_get_thread_num_body>(ctx,",
        ],
        forbidden_snippets=[
            "arch.get_thread_num",
            "template <typename Context>",
            "static void arch_get_thread_num_body(Context& ctx",
            "ctx.thread_num()",
            ", arch_get_thread_num_body<npu_demo::KernelContext>>(ctx,",
            (
                f"npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}>"
                "(arch_get_thread_num_body,"
            ),
            (
                f"npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}>"
                "(ctx, arch_get_thread_num_body<npu_demo::KernelContext>,"
            ),
            (
                f"npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}>"
                "(arch_get_thread_num_body<npu_demo::KernelContext>, ctx,"
            ),
            (
                f"npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}>"
                "(ctx, arch_get_thread_num_body,"
            ),
            (
                f"npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}>"
                "(arch_get_thread_num_body, ctx,"
            ),
        ],
    )


def main() -> None:
    """运行 `arch.get_thread_num` 的 emit_c expectation。"""

    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "emit_c-npu_demo-arch-get_thread_num-1", _case_arch_get_thread_num)
    raise_if_failures("emit_c npu_demo arch get_thread_num expectation", failures)


if __name__ == "__main__":
    main()
