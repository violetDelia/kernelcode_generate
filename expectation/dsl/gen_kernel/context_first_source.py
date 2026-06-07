"""npu_demo context-first generated source expectation.

功能说明:
- 锁定 `target=npu_demo` 的 launch body 生成 context-first 源码。
- 要求 device body 通过 `npu_demo::KernelContext& ctx` 承接 kernel 上下文，
  业务模板只保留 dtype 参数，并通过 `op<...>(ctx, args...)` 调用 Kernel helper；
  DMA helper 保持既有无显式模板时只前置 `ctx` 的形态。
- 本文件是合同资产；execute 阶段只读运行，不得在任务候选 diff 中修改。

API 列表:
- `main() -> None`

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.gen_kernel.context_first_source`

关联文件:
- spec: [`spec/dsl/gen_kernel/gen_kernel.md`](../../../spec/dsl/gen_kernel/gen_kernel.md)
- spec: [`spec/dsl/gen_kernel/kernel_emitter.md`](../../../spec/dsl/gen_kernel/kernel_emitter.md)
- spec: [`spec/dsl/gen_kernel/emit/npu_demo.md`](../../../spec/dsl/gen_kernel/emit/npu_demo.md)
- spec: [`spec/include/api/Dma.md`](../../../spec/include/api/Dma.md)
- spec: [`spec/include/api/Kernel.md`](../../../spec/include/api/Kernel.md)
- 功能实现: [`kernel_gen/dsl/gen_kernel/kernel_emitter.py`](../../../kernel_gen/dsl/gen_kernel/kernel_emitter.py)
- 功能实现: [`kernel_gen/dsl/gen_kernel/emit/npu_demo`](../../../kernel_gen/dsl/gen_kernel/emit/npu_demo)
"""

# Case 列表:
# - dsl-gen_kernel-context_first-launch_body-1:
#   正例：launch body 生成普通 `npu_demo::KernelContext& ctx` body，
#   wrapper 物化 `npu_demo::KernelContext ctx` 并传给 launch，body 内 DMA helper 使用 `op(ctx, args...)`。
# - dsl-gen_kernel-context_first-template_kernel_op-1:
#   正例：带 memory template_name 的 launch body 必须只保留 dtype 模板参数，
#   wrapper 物化 `npu_demo::KernelContext ctx` 并传给 launch，Kernel helper 使用 `op<...>(ctx, args...)`。
# - dsl-gen_kernel-context_first-arch_ops-1:
#   正例：launch body 仍生成 `npu_demo::KernelContext& ctx` 首参并通过 context-first launch 调用，
#   但 arch 查询、动态内存和 barrier 保持既有 free helper 口径。

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "kernel_gen").exists())
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from expectation.utils.case_runner import print_case_input_ir, raise_if_failures, run_case
from kernel_gen.tools.emitc_case_runner import run_emitc_case

_MEM1_GM_F32 = "!nn.memory<[#C4], [#C1], f32, #nn.space<global>>"
_MEM1_GM_F32_TDATA = "!nn.memory<[#C4], [#C1], f32, #nn.space<global>, template = TData>"
_MEM1_TSM_I8 = "!nn.memory<[#symbol.expr<TSM_SIZE>], [#C1], i8, #nn.space<tsm>>"


def _build_context_first_launch_case() -> str:
    """构造 npu_demo context-first launch body generated source 合同 case。"""

    return f"""// COMPILE_ARGS: --pass no-op
// CASE: 正例：npu_demo launch body 必须显式接收 npu_demo::KernelContext& ctx，并通过 op(ctx, ...) 调用 helper。
// CHECK: static void context_first_body(npu_demo::KernelContext& ctx, Memory<GM, float>& lhs, Memory<GM, float>& rhs, Memory<GM, float>& out)
// CHECK: slice(ctx, out /*dst*/, lhs /*source*/, {{0}} /*offset*/, {{out.get_shape(0)}} /*size*/, {{1}} /*stride*/);
// CHECK: npu_demo::KernelContext ctx;
// CHECK: npu_demo::launch<2, 1, 1, 0, context_first_body>(ctx, lhs, rhs, out);
// CHECK-NOT: template <typename Context>
// CHECK-NOT: static void context_first_body(Context& ctx
// CHECK-NOT: static void context_first_body(Memory<GM, float>& lhs
// CHECK-NOT: slice(out /*dst*/, lhs /*source*/
// CHECK-NOT: npu_demo::launch<2, 1, 1, 0>(context_first_body, lhs, rhs, out);
// CHECK-NOT: npu_demo::launch<2, 1, 1, 0, context_first_body<npu_demo::KernelContext>>(ctx, lhs, rhs, out);
// CHECK-NOT: npu_demo::launch<2, 1, 1, 0>(ctx, context_first_body<npu_demo::KernelContext>, lhs, rhs, out);
// CHECK-NOT: npu_demo::launch<2, 1, 1, 0>(context_first_body<npu_demo::KernelContext>, ctx, lhs, rhs, out);

#C0 = #symbol.expr<0>
#C1 = #symbol.expr<1>
#C2 = #symbol.expr<2>
#C4 = #symbol.expr<4>
builtin.module {{
  func.func @context_first_body(
    %ctx : index {{name = "ctx"}},
    %lhs : {_MEM1_GM_F32} {{name = "lhs"}},
    %rhs : {_MEM1_GM_F32} {{name = "rhs"}},
    %out : {_MEM1_GM_F32} {{name = "out"}}
  ) {{
    "dma.copy"(%out, %lhs) : ({_MEM1_GM_F32}, {_MEM1_GM_F32}) -> ()
    func.return
  }}
  func.func @context_first(
    %lhs : {_MEM1_GM_F32} {{name = "lhs"}},
    %rhs : {_MEM1_GM_F32} {{name = "rhs"}},
    %out : {_MEM1_GM_F32} {{name = "out"}}
  ) {{
    %b = symbol.const 2 : !symbol.int<#C2>
    %t = symbol.const 1 : !symbol.int<#C1>
    %s = symbol.const 1 : !symbol.int<#C1>
    %m = symbol.const 0 : !symbol.int<#C0>
    arch.launch<%b, %t, %s, %m>(@context_first_body, %lhs, %rhs, %out) : ({_MEM1_GM_F32}, {_MEM1_GM_F32}, {_MEM1_GM_F32}) -> ()
    func.return
  }}
}}"""


def _case_context_first_launch_body() -> None:
    """运行 npu_demo context-first launch body generated source 合同。"""

    case_text = _build_context_first_launch_case()
    print_case_input_ir(
        "dsl-gen_kernel-context_first-launch_body-1",
        case_text,
        fallback="npu_demo launch body 必须显式接收 npu_demo::KernelContext& ctx，并通过 op(ctx, ...) 调用 helper。",
    )
    run_emitc_case(
        case_text,
        source_path="expectation/dsl/gen_kernel/context_first_source.py#launch-body",
        op_name="npu_demo.context_first_launch_body",
        expected_snippets=[
            "static void context_first_body(npu_demo::KernelContext& ctx, Memory<GM, float>& lhs, Memory<GM, float>& rhs, Memory<GM, float>& out)",
            "slice(ctx, out /*dst*/, lhs /*source*/, {0} /*offset*/, {out.get_shape(0)} /*size*/, {1} /*stride*/);",
            "npu_demo::KernelContext ctx;",
            "npu_demo::launch<2, 1, 1, 0, context_first_body>(ctx, lhs, rhs, out);",
        ],
        forbidden_snippets=[
            "template <typename Context>",
            "static void context_first_body(Context& ctx",
            "static void context_first_body(Memory<GM, float>& lhs",
            "slice(out /*dst*/, lhs /*source*/",
            "Vector(", "static_cast<long long>",
            "npu_demo::launch<2, 1, 1, 0>(context_first_body, lhs, rhs, out);",
            "npu_demo::launch<2, 1, 1, 0, context_first_body<npu_demo::KernelContext>>(ctx, lhs, rhs, out);",
            "npu_demo::launch<2, 1, 1, 0>(ctx, context_first_body<npu_demo::KernelContext>, lhs, rhs, out);",
            "npu_demo::launch<2, 1, 1, 0>(context_first_body<npu_demo::KernelContext>, ctx, lhs, rhs, out);",
        ],
    )


def _build_context_first_template_kernel_case() -> str:
    """构造带 dtype template 与 kernel helper 的 context-first generated source 合同 case。"""

    return f"""// COMPILE_ARGS: --pass no-op
// CASE: 正例：memory template_name 场景只保留 dtype 模板 body，并通过 add<...>(ctx, ...) 调用 Kernel helper。
// CHECK: template <typename TData>
// CHECK: static void templated_body(npu_demo::KernelContext& ctx, Memory<GM, TData>& lhs, Memory<GM, TData>& rhs, Memory<GM, TData>& out)
// CHECK: add<GM, TData, TData>(ctx, out /*out*/, lhs /*lhs*/, rhs /*rhs*/);
// CHECK: npu_demo::KernelContext ctx;
// CHECK: npu_demo::launch<2, 1, 1, 0, templated_body<TData>>(ctx, lhs, rhs, out);
// CHECK-NOT: template <typename Context, typename TData>
// CHECK-NOT: template <typename TData, typename Context>
// CHECK-NOT: static void templated_body(Context& ctx
// CHECK-NOT: static void templated_body(Memory<GM, TData>& lhs
// CHECK-NOT: add<GM, TData, TData>(out /*out*/, lhs /*lhs*/, rhs /*rhs*/);
// CHECK-NOT: npu_demo::launch<2, 1, 1, 0>(templated_body<TData>, lhs, rhs, out);
// CHECK-NOT: npu_demo::launch<2, 1, 1, 0, templated_body<TData, npu_demo::KernelContext>>(ctx, lhs, rhs, out);
// CHECK-NOT: npu_demo::launch<2, 1, 1, 0>(ctx, templated_body<TData, npu_demo::KernelContext>, lhs, rhs, out);
// CHECK-NOT: npu_demo::launch<2, 1, 1, 0>(templated_body<TData, npu_demo::KernelContext>, ctx, lhs, rhs, out);

#C0 = #symbol.expr<0>
#C1 = #symbol.expr<1>
#C2 = #symbol.expr<2>
#C4 = #symbol.expr<4>
builtin.module {{
  func.func @templated_body(
    %ctx : index {{name = "ctx"}},
    %lhs : {_MEM1_GM_F32_TDATA} {{name = "lhs"}},
    %rhs : {_MEM1_GM_F32_TDATA} {{name = "rhs"}},
    %out : {_MEM1_GM_F32_TDATA} {{name = "out"}}
  ) {{
    "kernel.binary_elewise"(%out, %lhs, %rhs) {{kind = "add", space = #nn.space<global>}} : ({_MEM1_GM_F32_TDATA}, {_MEM1_GM_F32_TDATA}, {_MEM1_GM_F32_TDATA}) -> ()
    func.return
  }}
  func.func @templated_kernel(
    %lhs : {_MEM1_GM_F32_TDATA} {{name = "lhs"}},
    %rhs : {_MEM1_GM_F32_TDATA} {{name = "rhs"}},
    %out : {_MEM1_GM_F32_TDATA} {{name = "out"}}
  ) {{
    %b = symbol.const 2 : !symbol.int<#C2>
    %t = symbol.const 1 : !symbol.int<#C1>
    %s = symbol.const 1 : !symbol.int<#C1>
    %m = symbol.const 0 : !symbol.int<#C0>
    arch.launch<%b, %t, %s, %m>(@templated_body, %lhs, %rhs, %out) : ({_MEM1_GM_F32_TDATA}, {_MEM1_GM_F32_TDATA}, {_MEM1_GM_F32_TDATA}) -> ()
    func.return
  }}
}}"""


def _case_context_first_template_kernel_op() -> None:
    """运行 dtype template 与 Kernel helper context-first generated source 合同。"""

    case_text = _build_context_first_template_kernel_case()
    print_case_input_ir(
        "dsl-gen_kernel-context_first-template_kernel_op-1",
        case_text,
        fallback="带 template_name 的 npu_demo body 必须只生成业务模板参数，并通过 add<...>(ctx, ...) 调用 Kernel helper。",
    )
    run_emitc_case(
        case_text,
        source_path="expectation/dsl/gen_kernel/context_first_source.py#template-kernel-op",
        op_name="npu_demo.context_first_template_kernel_op",
        expected_snippets=[
            "template <typename TData>\nstatic void templated_body(npu_demo::KernelContext& ctx, Memory<GM, TData>& lhs, Memory<GM, TData>& rhs, Memory<GM, TData>& out)",
            "add<GM, TData, TData>(ctx, out /*out*/, lhs /*lhs*/, rhs /*rhs*/);",
            "npu_demo::KernelContext ctx;",
            "npu_demo::launch<2, 1, 1, 0, templated_body<TData>>(ctx, lhs, rhs, out);",
        ],
        forbidden_snippets=[
            "template <typename Context, typename TData>",
            "template <typename TData, typename Context>",
            "static void templated_body(Context& ctx",
            "static void templated_body(Memory<GM, TData>& lhs",
            "add<GM, TData, TData>(out /*out*/, lhs /*lhs*/, rhs /*rhs*/);",
            "npu_demo::launch<2, 1, 1, 0>(templated_body<TData>, lhs, rhs, out);",
            "npu_demo::launch<2, 1, 1, 0, templated_body<TData, npu_demo::KernelContext>>(ctx, lhs, rhs, out);",
            "npu_demo::launch<2, 1, 1, 0>(ctx, templated_body<TData, npu_demo::KernelContext>, lhs, rhs, out);",
            "npu_demo::launch<2, 1, 1, 0>(templated_body<TData, npu_demo::KernelContext>, ctx, lhs, rhs, out);",
        ],
    )


def _build_context_first_arch_ops_case() -> str:
    """构造 arch 查询、动态内存和 barrier 的 context-first generated source 合同 case。"""

    return f"""// COMPILE_ARGS: --pass no-op
// CASE: 正例：launch body 内 arch ops 保持既有 free helper 口径，但 body / launch 必须 context-first。
// CHECK: static void arch_ops_body(npu_demo::KernelContext& ctx, Memory<GM, float>& lhs, Memory<GM, float>& rhs, Memory<GM, float>& out)
// CHECK: S_INT v0 = npu_demo::thread_id();
// CHECK: S_INT v1 = npu_demo::thread_num();
// CHECK: Memory<TSM, int8_t> v2 = npu_demo::get_dynamic_memory<TSM>();
// CHECK: npu_demo::barrier({{BarrierVisibility::TSM, BarrierVisibility::TLM}}, BarrierScope::BLOCK);
// CHECK: npu_demo::KernelContext ctx;
// CHECK: npu_demo::launch<2, 1, 1, 0, arch_ops_body>(ctx, lhs, rhs, out);
// CHECK-NOT: template <typename Context>
// CHECK-NOT: static void arch_ops_body(Context& ctx
// CHECK-NOT: ctx.block_id()
// CHECK-NOT: ctx.block_num()
// CHECK-NOT: ctx.thread_id()
// CHECK-NOT: ctx.thread_num()
// CHECK-NOT: ctx.subthread_id()
// CHECK-NOT: ctx.subthread_num()
// CHECK-NOT: ctx.template get_dynamic_memory<TSM, int8_t>()
// CHECK-NOT: ctx.get_dynamic_memory
// CHECK-NOT: ctx.barrier(
// CHECK-NOT: npu_demo::launch<2, 1, 1, 0, arch_ops_body<npu_demo::KernelContext>>(ctx, lhs, rhs, out);
// CHECK-NOT: npu_demo::launch<2, 1, 1, 0>(ctx, arch_ops_body<npu_demo::KernelContext>, lhs, rhs, out);
// CHECK-NOT: npu_demo::launch<2, 1, 1, 0>(arch_ops_body<npu_demo::KernelContext>, ctx, lhs, rhs, out);

#C0 = #symbol.expr<0>
#C1 = #symbol.expr<1>
#C2 = #symbol.expr<2>
#C4 = #symbol.expr<4>
builtin.module {{
  func.func @arch_ops_body(
    %ctx : index {{name = "ctx"}},
    %lhs : {_MEM1_GM_F32} {{name = "lhs"}},
    %rhs : {_MEM1_GM_F32} {{name = "rhs"}},
    %out : {_MEM1_GM_F32} {{name = "out"}}
  ) {{
    %tid = arch.get_thread_id : !symbol.int<#symbol.expr<thread_id>>
    %tnum = arch.get_thread_num : !symbol.int<#symbol.expr<thread_num>>
    %tsm = arch.get_dynamic_memory #nn.space<tsm> : {_MEM1_TSM_I8}
    arch.barrier {{scope = #arch.scope<block>, visibility = [#arch.visibility<tsm>, #arch.visibility<tlm>]}}
    func.return
  }}
  func.func @arch_ops_kernel(
    %lhs : {_MEM1_GM_F32} {{name = "lhs"}},
    %rhs : {_MEM1_GM_F32} {{name = "rhs"}},
    %out : {_MEM1_GM_F32} {{name = "out"}}
  ) {{
    %b = symbol.const 2 : !symbol.int<#C2>
    %t = symbol.const 1 : !symbol.int<#C1>
    %s = symbol.const 1 : !symbol.int<#C1>
    %m = symbol.const 0 : !symbol.int<#C0>
    arch.launch<%b, %t, %s, %m>(@arch_ops_body, %lhs, %rhs, %out) : ({_MEM1_GM_F32}, {_MEM1_GM_F32}, {_MEM1_GM_F32}) -> ()
    func.return
  }}
}}"""


def _case_context_first_arch_ops() -> None:
    """运行 arch ops context-first generated source 合同。"""

    case_text = _build_context_first_arch_ops_case()
    print_case_input_ir(
        "dsl-gen_kernel-context_first-arch_ops-1",
        case_text,
        fallback="npu_demo launch body 内 arch 查询、动态内存和 barrier 保持 free helper 口径，但 body / launch 必须 context-first。",
    )
    run_emitc_case(
        case_text,
        source_path="expectation/dsl/gen_kernel/context_first_source.py#arch-ops",
        op_name="npu_demo.context_first_arch_ops",
        expected_snippets=[
            "static void arch_ops_body(npu_demo::KernelContext& ctx, Memory<GM, float>& lhs, Memory<GM, float>& rhs, Memory<GM, float>& out)",
            "S_INT v0 = npu_demo::thread_id();",
            "S_INT v1 = npu_demo::thread_num();",
            "Memory<TSM, int8_t> v2 = npu_demo::get_dynamic_memory<TSM>();",
            "npu_demo::barrier({BarrierVisibility::TSM, BarrierVisibility::TLM}, BarrierScope::BLOCK);",
            "npu_demo::KernelContext ctx;",
            "npu_demo::launch<2, 1, 1, 0, arch_ops_body>(ctx, lhs, rhs, out);",
        ],
        forbidden_snippets=[
            "template <typename Context>",
            "static void arch_ops_body(Context& ctx",
            "npu_demo::launch<2, 1, 1, 0, arch_ops_body<npu_demo::KernelContext>>(ctx, lhs, rhs, out);",
            "ctx.block_id()",
            "ctx.block_num()",
            "ctx.thread_id()",
            "ctx.thread_num()",
            "ctx.subthread_id()",
            "ctx.subthread_num()",
            "ctx.template get_dynamic_memory<TSM, int8_t>()",
            "ctx.get_dynamic_memory",
            "ctx.barrier(",
            "npu_demo::launch<2, 1, 1, 0>(arch_ops_body<npu_demo::KernelContext>, lhs, rhs, out);",
            "npu_demo::launch<2, 1, 1, 0>(ctx, arch_ops_body<npu_demo::KernelContext>, lhs, rhs, out);",
            "npu_demo::launch<2, 1, 1, 0>(arch_ops_body<npu_demo::KernelContext>, ctx, lhs, rhs, out);",
        ],
    )


def main() -> None:
    """运行 npu_demo context-first generated source expectation。"""

    failures: list[tuple[str, BaseException]] = []
    run_case(failures, "dsl-gen_kernel-context_first-launch_body-1", _case_context_first_launch_body)
    run_case(failures, "dsl-gen_kernel-context_first-template_kernel_op-1", _case_context_first_template_kernel_op)
    run_case(failures, "dsl-gen_kernel-context_first-arch_ops-1", _case_context_first_arch_ops)
    raise_if_failures("npu_demo context-first generated source expectation", failures)


if __name__ == "__main__":
    main()
