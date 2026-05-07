"""npu_demo add+barrier e2e public test assets.

创建者: 大闸蟹
最后一次更改: 2026-05-02
功能说明:
- 为 `test/e2e/test_npu_demo_add_barrier.py` 提供公开的 module builder、context builder 与编译运行 helper。
- 避免 e2e 测试跨文件加载 `test_*.py` 并直连私有测试 helper。
API 列表:
- `make_npu_demo_context() -> EmitCContext`
- `build_npu_demo_add_barrier_module(*, body_name: str = "add_barrier_body", wrapper_name: str = "add_barrier", callee_name: str | None = None, callee_attr: SymbolRefAttr | None = None, block_extent_expr: str = "1", thread_extent_expr: str = "1", subthread_extent_expr: str = "1", shared_memory_size_expr: str = "0", barrier_scope: str = "block", barrier_visibility_names: tuple[str, ...] = ("tsm", "tlm"), tlm_space: str = "tlm1", emit_wrapper_return: bool = True, include_body: bool = True, include_wrapper: bool = True, top_level_extra_ops: tuple[Operation, ...] = ()) -> ModuleOp`
- `compile_and_run_npu_demo_add_barrier_source(source: str, *, prove_barrier_runtime: bool) -> None`
使用示例:
- module = build_npu_demo_add_barrier_module()
- source = gen_kernel(module, make_npu_demo_context())
- compile_and_run_npu_demo_add_barrier_source(source, prove_barrier_runtime=True)
关联文件:
- 功能实现: kernel_gen/dsl/gen_kernel/gen_kernel.py
- Spec 文档: spec/dsl/gen_kernel/gen_kernel.md
- 测试文件: test/e2e/test_npu_demo_add_barrier.py
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile

from xdsl.dialects import func
from xdsl.dialects.builtin import ArrayAttr, DictionaryAttr, FunctionType, IndexType, IntAttr, ModuleOp, StringAttr, SymbolRefAttr, f32
from xdsl.ir import Attribute, Block, Operation, Region, SSAValue
from xdsl.irdl import IRDLOperation, irdl_op_definition, result_def

from kernel_gen.core.config import set_target
from kernel_gen.dialect.arch import (
    ArchBarrierOp,
    ArchGetDynamicMemoryOp,
    ArchGetThreadIdOp,
    ArchGetThreadNumOp,
    ArchLaunchOp,
    ArchScopeAttr,
    ArchVisibilityAttr,
)
from kernel_gen.dialect.dma import DmaDesliceOp, DmaSliceOp, DmaViewOp
from kernel_gen.dialect.kernel import KernelBinaryElewiseOp
from kernel_gen.dialect.nn import NnMemorySpaceAttr, NnMemoryType
from kernel_gen.dialect.symbol import SymbolExprAttr
from kernel_gen.dialect.symbol import SymbolValueType
from kernel_gen.dsl.gen_kernel import EmitCContext


REPO_ROOT = Path(__file__).resolve().parents[2]


@irdl_op_definition
class _FakeSymbolValueOp(IRDLOperation):
    """创建测试用 `!symbol.int<"...">` 值。

    创建者: 大闸蟹
    最后一次更改: 2026-05-02
    功能说明:
    - 在 e2e 资产内构造受控 symbol value，用于表达 thread offset、size 与 stride。
    使用示例:
    - op = _FakeSymbolValueOp("thread_id * 16")
    """

    name = "test.fake_symbol_value"
    result = result_def(SymbolValueType)

    def __init__(self, expr: str) -> None:
        super().__init__(result_types=[SymbolValueType.from_expr(expr)])


def make_npu_demo_context() -> EmitCContext:
    """创建 npu_demo target 的 EmitCContext。

    创建者: 大闸蟹
    最后一次更改: 2026-05-02
    功能说明:
    - 设置全局 target 为 `npu_demo`，并返回一次发射使用的上下文对象。
    使用示例:
    - ctx = make_npu_demo_context()
    """

    set_target("npu_demo")
    return EmitCContext()


def _make_memory_type(shape: list[int], stride: list[int], element_type: Attribute = f32, space: str = "global") -> NnMemoryType:
    """创建测试用 nn.memory 类型。

    创建者: 大闸蟹
    最后一次更改: 2026-05-02
    功能说明:
    - 把 shape、stride、element type 与 memory space 组合为受控 `NnMemoryType`。
    使用示例:
    - mem = _make_memory_type([64], [1], element_type=f32)
    """

    return NnMemoryType(
        ArrayAttr([SymbolExprAttr.from_expr(str(dim)) for dim in shape]),
        ArrayAttr([SymbolExprAttr.from_expr(str(dim)) for dim in stride]),
        element_type,
        NnMemorySpaceAttr.from_name(space),
    )


def _arg_attrs(*names: str) -> ArrayAttr[DictionaryAttr]:
    """创建测试函数参数名属性。

    创建者: 大闸蟹
    最后一次更改: 2026-05-02
    功能说明:
    - 为构造 `func.func` 时的参数名提供 `arg_attrs`。
    使用示例:
    - attrs = _arg_attrs("lhs", "rhs", "out")
    """

    return ArrayAttr([DictionaryAttr({"name": StringAttr(name)}) for name in names])


def _func(name: str, input_types: list[Attribute], result_types: list[Attribute], block: Block, arg_names: tuple[str, ...]) -> func.FuncOp:
    """创建带参数名属性的 func.FuncOp。

    创建者: 大闸蟹
    最后一次更改: 2026-05-02
    功能说明:
    - 统一 e2e 资产内函数构造逻辑，避免测试正文复制 IR 组装细节。
    使用示例:
    - fn = _func("add_barrier", [mem], [], block, ("lhs",))
    """

    func_type = FunctionType.from_lists(input_types, result_types)
    return func.FuncOp(name, func_type, Region(block), arg_attrs=_arg_attrs(*arg_names))


def build_npu_demo_add_barrier_module(
    *,
    body_name: str = "add_barrier_body",
    wrapper_name: str = "add_barrier",
    callee_name: str | None = None,
    callee_attr: SymbolRefAttr | None = None,
    block_extent_expr: str = "1",
    thread_extent_expr: str = "1",
    subthread_extent_expr: str = "1",
    shared_memory_size_expr: str = "0",
    barrier_scope: str = "block",
    barrier_visibility_names: tuple[str, ...] = ("tsm", "tlm"),
    tlm_space: str = "tlm1",
    emit_wrapper_return: bool = True,
    include_body: bool = True,
    include_wrapper: bool = True,
    top_level_extra_ops: tuple[Operation, ...] = (),
) -> ModuleOp:
    """构造 `npu_demo` launch wrapper/body 受控 module。

    创建者: 大闸蟹
    最后一次更改: 2026-05-02
    功能说明:
    - 生成 `body + wrapper` 双函数 module，覆盖 `gen_kernel(target="npu_demo")` 的 e2e 正向链路。
    - body 固定包含 `thread/view/slice/barrier/add/deslice` 骨架。
    使用示例:
    - module = build_npu_demo_add_barrier_module()
    """

    gm_type = _make_memory_type([64], [1], element_type=f32)
    tsm_buffer_type = _make_memory_type([128], [1], element_type=f32, space="tsm")
    tlm_buffer_type = _make_memory_type([64], [1], element_type=f32, space=tlm_space)
    tsm_tile_type = _make_memory_type([16], [1], element_type=f32, space="tsm")
    gm_tile_type = _make_memory_type([16], [1], element_type=f32, space="global")
    barrier_visibility = ArrayAttr([ArchVisibilityAttr.from_name(space_name) for space_name in barrier_visibility_names])

    body_block = Block(arg_types=[IndexType(), gm_type, gm_type, gm_type])
    thread_offset = _FakeSymbolValueOp("thread_id * 16")
    rhs_offset = _FakeSymbolValueOp("64 + thread_id * 16")
    zero = _FakeSymbolValueOp("0")
    size = _FakeSymbolValueOp("16")
    stride = _FakeSymbolValueOp("1")
    tid = ArchGetThreadIdOp()
    tnum = ArchGetThreadNumOp()
    tsm = ArchGetDynamicMemoryOp(NnMemorySpaceAttr.from_name("tsm"), tsm_buffer_type)
    tlm = ArchGetDynamicMemoryOp(NnMemorySpaceAttr.from_name(tlm_space), tlm_buffer_type)
    lhs_gm = DmaViewOp(body_block.args[1], [thread_offset.result], [size.result], [stride.result], gm_tile_type)
    rhs_gm = DmaViewOp(body_block.args[2], [thread_offset.result], [size.result], [stride.result], gm_tile_type)
    lhs_tsm = DmaViewOp(tsm.result, [thread_offset.result], [size.result], [stride.result], tsm_tile_type)
    rhs_tsm = DmaViewOp(tsm.result, [rhs_offset.result], [size.result], [stride.result], tsm_tile_type)
    out_tsm = DmaViewOp(tsm.result, [thread_offset.result], [size.result], [stride.result], tsm_tile_type)
    lhs_slice = DmaSliceOp(lhs_tsm.result, lhs_gm.result, [zero.result], [size.result], [stride.result])
    rhs_slice = DmaSliceOp(rhs_tsm.result, rhs_gm.result, [zero.result], [size.result], [stride.result])
    barrier0 = ArchBarrierOp(ArchScopeAttr.from_name(barrier_scope), barrier_visibility)
    add = KernelBinaryElewiseOp(
        out_tsm.result,
        lhs_tsm.result,
        rhs_tsm.result,
        kind="add",
        space=NnMemorySpaceAttr.from_name("tsm"),
    )
    barrier1 = ArchBarrierOp(ArchScopeAttr.from_name(barrier_scope), barrier_visibility)
    deslice = DmaDesliceOp(body_block.args[3], out_tsm.result, [thread_offset.result], [size.result], [stride.result], gm_type)
    body_block.add_ops(
        [
            thread_offset,
            rhs_offset,
            zero,
            size,
            stride,
            tid,
            tnum,
            tsm,
            tlm,
            lhs_gm,
            rhs_gm,
            lhs_tsm,
            rhs_tsm,
            out_tsm,
            lhs_slice,
            rhs_slice,
            barrier0,
            add,
            barrier1,
            deslice,
            func.ReturnOp(),
        ]
    )
    body_func = _func(body_name, [IndexType(), gm_type, gm_type, gm_type], [], body_block, ("ctx", "lhs", "rhs", "out"))

    wrapper_block = Block(arg_types=[gm_type, gm_type, gm_type])
    block_extent = _FakeSymbolValueOp(block_extent_expr)
    thread_extent = _FakeSymbolValueOp(thread_extent_expr)
    subthread_extent = _FakeSymbolValueOp(subthread_extent_expr)
    shared_memory_size = _FakeSymbolValueOp(shared_memory_size_expr)
    launch = ArchLaunchOp(
        callee_attr or SymbolRefAttr(callee_name or body_name),
        block_extent.result,
        thread_extent.result,
        subthread_extent.result,
        shared_memory_size.result,
        (wrapper_block.args[0], wrapper_block.args[1], wrapper_block.args[2]),
    )
    wrapper_ops: list[Operation] = [block_extent, thread_extent, subthread_extent, shared_memory_size, launch]
    if emit_wrapper_return:
        wrapper_ops.append(func.ReturnOp())
    wrapper_block.add_ops(wrapper_ops)
    wrapper_func = _func(wrapper_name, [gm_type, gm_type, gm_type], [], wrapper_block, ("lhs", "rhs", "out"))
    top_level_ops: list[Operation] = []
    if include_body:
        top_level_ops.append(body_func)
    if include_wrapper:
        top_level_ops.append(wrapper_func)
    top_level_ops.extend(top_level_extra_ops)
    return ModuleOp(top_level_ops)


def _run_local_compile_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    """执行本 e2e 资产使用的本地编译命令。

    创建者: 大闸蟹
    最后一次更改: 2026-05-02
    功能说明:
    - 固定 `subprocess.run` 参数并对 GCC 内部错误执行一次重试。
    使用示例:
    - result = _run_local_compile_command(["g++", "--version"])
    """

    compile_result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    if compile_result.returncode == 0:
        return compile_result
    if "internal compiler error:" not in compile_result.stderr:
        return compile_result
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )


def compile_and_run_npu_demo_add_barrier_source(source: str, *, prove_barrier_runtime: bool) -> None:
    """编译并运行 `npu_demo add+barrier` 生成源码。

    创建者: 大闸蟹
    最后一次更改: 2026-05-02
    功能说明:
    - 把 `gen_kernel(target="npu_demo")` 生成的双函数源码拼接到最小可执行程序中。
    - 可选追加“线程 0 故意慢一步”的 barrier 探针，证明其他线程不会越过同一次 launch 的共享 barrier。
    使用示例:
    - compile_and_run_npu_demo_add_barrier_source(source, prove_barrier_runtime=True)
    """

    barrier_probe = ""
    barrier_assert = ""
    if prove_barrier_runtime:
        barrier_probe = r"""
static void slow_barrier_probe(
    npu_demo::KernelContext& ctx,
    std::atomic<long long>* entered,
    long long* after_values) {
    const long long tid = ctx.thread_id();
    if (tid == 0) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    entered->fetch_add(1);
    ctx.barrier({BarrierVisibility::TSM, BarrierVisibility::TLM}, BarrierScope::BLOCK);
    after_values[tid] = entered->load();
}
"""
        barrier_assert = r"""
    std::atomic<long long> entered(0);
    long long after_values[4] = {-1, -1, -1, -1};
    if (npu_demo::launch<1, 4, 1, 0>(slow_barrier_probe, &entered, after_values) != StatusCode::kOk) {
        return fail(4);
    }
    for (long long i = 0; i < 4; ++i) {
        if (after_values[i] != 4) {
            return fail(5);
        }
    }
"""

    cpp_source = f"""
#include <atomic>
#include <chrono>
#include <thread>

{source}

static int fail(int code) {{ return code; }}
{barrier_probe}

int main() {{
    float lhs_data[64];
    float rhs_data[64];
    float out_data[64] = {{0}};
    long long shape[1] = {{64}};
    long long stride[1] = {{1}};
    for (int i = 0; i < 64; ++i) {{
        lhs_data[i] = static_cast<float>(i + 1);
        rhs_data[i] = static_cast<float>(100 + i);
    }}

    Memory<MemorySpace::GM, float> lhs(lhs_data, shape, stride, 1, MemoryFormat::Norm);
    Memory<MemorySpace::GM, float> rhs(rhs_data, shape, stride, 1, MemoryFormat::Norm);
    Memory<MemorySpace::GM, float> out(out_data, shape, stride, 1, MemoryFormat::Norm);
    auto generated_entry = &add_barrier;
    auto generated_body = &add_barrier_body;
    if (generated_entry == nullptr || generated_body == nullptr) {{
        return fail(1);
    }}
    if (lhs.rank() == 0) {{
        generated_entry(lhs, rhs, out);
        return fail(2);
    }}
{barrier_assert}
    return 0;
}}
"""

    if shutil.which("g++") is None:
        raise AssertionError("g++ not found in PATH; please install g++ to reproduce this test")

    gpp_version = subprocess.run(
        ["g++", "--version"],
        check=False,
        capture_output=True,
        text=True,
    )
    gpp_version_text = gpp_version.stdout.strip() or gpp_version.stderr.strip()

    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / "gen_kernel_npu_demo_add_barrier.cpp"
        binary_path = Path(tmpdir) / "gen_kernel_npu_demo_add_barrier"
        source_path.write_text(cpp_source, encoding="utf-8")

        compile_cmd = [
            "g++",
            "-std=c++17",
            "-pthread",
            "-I",
            str(REPO_ROOT),
            str(source_path),
            "-o",
            str(binary_path),
        ]

        compile_result = _run_local_compile_command(compile_cmd)
        if compile_result.returncode != 0:
            fallback_cmd = [*compile_cmd, "-latomic"]
            fallback_result = _run_local_compile_command(fallback_cmd)
            if fallback_result.returncode != 0:
                raise AssertionError(
                    "g++ compile failed:\n"
                    f"command:\n{' '.join(compile_cmd)}\n"
                    f"fallback:\n{' '.join(fallback_cmd)}\n"
                    f"g++ version:\n{gpp_version_text}\n"
                    f"stdout:\n{compile_result.stdout}\n"
                    f"stderr:\n{compile_result.stderr}\n"
                    f"fallback stdout:\n{fallback_result.stdout}\n"
                    f"fallback stderr:\n{fallback_result.stderr}"
                )

        run_result = subprocess.run(
            [str(binary_path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=5.0,
        )
        if run_result.returncode != 0:
            raise AssertionError(
                "compiled program failed:\n"
                f"returncode:\n{run_result.returncode}\n"
                f"stdout:\n{run_result.stdout}\n"
                f"stderr:\n{run_result.stderr}"
            )
