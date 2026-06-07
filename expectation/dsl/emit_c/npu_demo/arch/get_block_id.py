"""emit_c npu_demo arch expectation：get_block_id。

创建者: OpenAI Codex
最后一次更改: OpenAI Codex

功能说明:
- 锁定 `arch.get_block_id` 在 `npu_demo` 下应发射为 `block_id()` 的公开源码口径。
- 覆盖节点级成功路径，不残留原始 dialect op 文本。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/dsl/emit_c/npu_demo/arch/get_block_id.py`

关联文件:
- spec: [`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)
- spec: [`spec/dialect/arch.md`](spec/dialect/arch.md)
- test: [`test/dsl/test_emit_c.py`](test/dsl/test_emit_c.py)
- 功能实现: [`kernel_gen/dsl/gen_kernel/emit/npu_demo/arch/get_block_id.py`](kernel_gen/dsl/gen_kernel/emit/npu_demo/arch/get_block_id.py)
- 功能实现: [`expectation/dsl/emit_c/npu_demo/arch/get_block_id.py`](expectation/dsl/emit_c/npu_demo/arch/get_block_id.py)
"""

# Case 列表:
# - emit_c-npu_demo-arch-get_block_id-1: `arch.get_block_id` 在 context-first launch body 中参与后续 `symbol.add` 时，应先发射为 `block_id()` 对应的 `S_INT` 局部值。

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "kernel_gen").exists())
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.case_runner import print_case_input_ir, raise_if_failures, run_case
from kernel_gen.tools.emitc_case_runner import run_emitc_case
from kernel_gen.target import registry as target_registry


def _build_case_arch_get_block_id() -> str:
    """构造 `arch.get_block_id` 的 npu_demo emit_c expectation IR。"""
    block_extent = target_registry.get_target_hardware("npu_demo", "block_num")
    thread_extent = target_registry.get_target_hardware("npu_demo", "thread_num")
    subthread_extent = target_registry.get_target_hardware("npu_demo", "subthread_num")
    shared_memory_size = target_registry.get_target_hardware("npu_demo", "sm_memory_size")
    mem_type = "!nn.memory<[#C4], [#C1], i8, #nn.space<global>>"
    return f"""// COMPILE_ARGS: --pass no-op
// CASE: `arch.get_block_id` 在完整 launch module 的 context-first body 中参与 `symbol.add` 时，应先发射为 `block_id()`。
// CHECK: static void arch_get_block_id_body(npu_demo::KernelContext& ctx, Memory<GM, int8_t>& [[ARG0:{{val}}]], Memory<GM, int8_t>& [[ARG1:{{val}}]], Memory<GM, int8_t>& [[ARG2:{{val}}]])
// CHECK: S_INT
// CHECK: npu_demo::block_id()
// CHECK: + 1
// CHECK: void arch_get_block_id_wrapper(Memory<MemorySpace::GM, int8_t>& [[WRAP0:{{val}}]], Memory<MemorySpace::GM, int8_t>& [[WRAP1:{{val}}]], Memory<MemorySpace::GM, int8_t>& [[WRAP2:{{val}}]]) {{
// CHECK: npu_demo::KernelContext ctx;
// CHECK: npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}, arch_get_block_id_body>(ctx, [[WRAP0]], [[WRAP1]], [[WRAP2]]);
// CHECK-NOT: template <typename Context>
// CHECK-NOT: static void arch_get_block_id_body(Context& ctx
// CHECK-NOT: npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}, arch_get_block_id_body<npu_demo::KernelContext>>(ctx,
// CHECK-NOT: ctx.block_id()
// CHECK-NOT: npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}>(arch_get_block_id_body,
// CHECK-NOT: npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}>(ctx, arch_get_block_id_body<npu_demo::KernelContext>,
// CHECK-NOT: npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}>(arch_get_block_id_body<npu_demo::KernelContext>, ctx,

#C1 = #symbol.expr<1>
#C4 = #symbol.expr<4>
#S_block_id = #symbol.expr<block_id>
#S1 = #symbol.expr<block_id + 1>
builtin.module {{
  func.func @arch_get_block_id_body(%0 : {mem_type}, %1 : {mem_type}, %2 : {mem_type}) {{
    %3 = arch.get_block_id : !symbol.int<#S_block_id>
    %4 = symbol.const 1 : !symbol.int<#C1>
    %5 = "symbol.add"(%3, %4) : (!symbol.int<#S_block_id>, !symbol.int<#C1>) -> !symbol.int<#S1>
    func.return
  }}

  func.func @arch_get_block_id_wrapper(%0 : {mem_type}, %1 : {mem_type}, %2 : {mem_type}) {{
    %3 = symbol.const {block_extent} : !symbol.int<#symbol.expr<{block_extent}>>
    %4 = symbol.const {thread_extent} : !symbol.int<#symbol.expr<{thread_extent}>>
    %5 = symbol.const {subthread_extent} : !symbol.int<#symbol.expr<{subthread_extent}>>
    %6 = symbol.const {shared_memory_size} : !symbol.int<#symbol.expr<{shared_memory_size}>>
    arch.launch<%3, %4, %5, %6>(@arch_get_block_id_body, %0, %1, %2) : ({mem_type}, {mem_type}, {mem_type}) -> ()
    func.return
  }}
}}"""


def _case_arch_get_block_id() -> None:
    """运行 `arch.get_block_id` 的 npu_demo emit_c 合同。"""

    block_extent = target_registry.get_target_hardware("npu_demo", "block_num")
    thread_extent = target_registry.get_target_hardware("npu_demo", "thread_num")
    subthread_extent = target_registry.get_target_hardware("npu_demo", "subthread_num")
    shared_memory_size = target_registry.get_target_hardware("npu_demo", "sm_memory_size")
    case_text = _build_case_arch_get_block_id()
    print_case_input_ir(
        "emit_c-npu_demo-arch-get_block_id-1",
        case_text,
        fallback="arch.get_block_id 在完整 launch module 的 body 中参与 symbol.add 时应先 materialize 为 S_INT 局部值并调用 block_id()。",
    )
    run_emitc_case(
        case_text,
        source_path="expectation/dsl/emit_c/npu_demo/arch/get_block_id.py",
        op_name="arch.get_block_id",
        expected_snippets=[
            "static void arch_get_block_id_body(npu_demo::KernelContext& ctx, Memory<GM, int8_t>&",
            "S_INT",
            "npu_demo::block_id()",
            "npu_demo::KernelContext ctx;",
            "npu_demo::launch<",
            ", arch_get_block_id_body>(ctx,",
        ],
        forbidden_snippets=[
            "arch.get_block_id",
            "template <typename Context>",
            "static void arch_get_block_id_body(Context& ctx",
            "ctx.block_id()",
            ", arch_get_block_id_body<npu_demo::KernelContext>>(ctx,",
            (
                f"npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}>"
                "(arch_get_block_id_body,"
            ),
            (
                f"npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}>"
                "(ctx, arch_get_block_id_body<npu_demo::KernelContext>,"
            ),
            (
                f"npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}>"
                "(arch_get_block_id_body<npu_demo::KernelContext>, ctx,"
            ),
            (
                f"npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}>"
                "(ctx, arch_get_block_id_body,"
            ),
            (
                f"npu_demo::launch<{block_extent}, {thread_extent}, {subthread_extent}, {shared_memory_size}>"
                "(arch_get_block_id_body, ctx,"
            ),
        ],
    )


def main() -> None:
    """运行 `arch.get_block_id` 的 emit_c expectation。"""

    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "emit_c-npu_demo-arch-get_block_id-1", _case_arch_get_block_id)
    raise_if_failures("emit_c npu_demo arch get_block_id expectation", failures)


if __name__ == "__main__":
    main()
