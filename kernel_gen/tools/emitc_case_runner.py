"""emit_c expectation helper runner.

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 为 `expectation/dsl/emit_c/**` 提供可复用的“文本 IR -> emit_c 源码 -> 片段断言”执行 helper。
- 让 expectation 侧不再自行维护解析 `builtin.module`、构造 `EmitCContext` 与源码片段断言逻辑。
- 该 helper 承接 `emit_c` 合同验收，并支持 expectation 头部声明的最小 pass 预处理集合。

API 列表:
- `run_emitc_case(case_text: str, *, source_path: str, op_name: str | None = None, expected_snippets: list[str], forbidden_snippets: list[str] | None = None) -> str`

使用示例:
- `source = run_emitc_case(case_text, source_path="inline", expected_snippets=["foo"], forbidden_snippets=["bar"])`

关联文件:
- spec: [spec/tools/emitc_case_runner.md](spec/tools/emitc_case_runner.md)
- test: [test/tools/test_emitc_case_runner.py](test/tools/test_emitc_case_runner.py)
- 功能实现: [kernel_gen/tools/emitc_case_runner.py](kernel_gen/tools/emitc_case_runner.py)
"""

from __future__ import annotations

from xdsl.parser import Parser

from kernel_gen.core.context import build_default_context
from kernel_gen.core.config import restore_config, set_target, snapshot_config
from kernel_gen.dsl.gen_kernel import EmitCContext, emit_c
from kernel_gen.passes.buffer_results_to_out_params import BufferResultsToOutParamsPass


def _extract_compile_args(case_text: str) -> str | None:
    """提取 case 头部中的 `COMPILE_ARGS` 文本。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 扫描 expectation case 头部的注释行。
    - 找到 `// COMPILE_ARGS:` 后返回对应参数文本。
    - 未声明时返回 `None`。

    使用示例:
    - `_extract_compile_args("// COMPILE_ARGS: --pass no-op\\n...")`

    关联文件:
    - spec: [spec/tools/emitc_case_runner.md](spec/tools/emitc_case_runner.md)
    - test: [test/tools/test_emitc_case_runner.py](test/tools/test_emitc_case_runner.py)
    - 功能实现: [kernel_gen/tools/emitc_case_runner.py](kernel_gen/tools/emitc_case_runner.py)
    """

    for raw_line in case_text.splitlines():
        line = raw_line.strip()
        if line.startswith("// COMPILE_ARGS:"):
            return line.removeprefix("// COMPILE_ARGS:").strip()
        if line and not line.startswith("//"):
            break
    return None


def _extract_input_ir(case_text: str) -> str:
    """从 expectation case 文本中剥离注释头，返回可解析的 IR 正文。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 去掉 case 头部中的 `COMPILE_ARGS` / `CHECK` 注释。
    - 保留真正的 `builtin.module` 文本与其中的空行。
    - 若提取后为空，则显式报错。

    使用示例:
    - `input_ir = _extract_input_ir(case_text)`

    关联文件:
    - spec: [spec/tools/emitc_case_runner.md](spec/tools/emitc_case_runner.md)
    - test: [test/tools/test_emitc_case_runner.py](test/tools/test_emitc_case_runner.py)
    - 功能实现: [kernel_gen/tools/emitc_case_runner.py](kernel_gen/tools/emitc_case_runner.py)
    """

    lines = [line for line in case_text.splitlines() if not line.lstrip().startswith("//")]
    input_ir = "\n".join(lines).strip()
    if not input_ir:
        raise ValueError("emit_c expectation case must contain input IR")
    return input_ir


def _apply_compile_args(module, *, compile_args: str | None, ctx) -> None:
    """按 expectation 头部的 `COMPILE_ARGS` 对输入 module 运行最小预处理。

    创建者: OpenAI Codex
    最后一次更改: OpenAI Codex

    功能说明:
    - 当前显式支持 `None` / `--pass no-op` / `--pass buffer-results-to-out-params`。
    - `buffer-results-to-out-params` 会在 `emit_c(...)` 前原地改写 `builtin.module`。
    - 其余参数串一律拒绝，避免 helper 偷偷扩成通用 pipeline runner。

    使用示例:
    - `_apply_compile_args(module, compile_args="--pass buffer-results-to-out-params", ctx=ctx)`

    关联文件:
    - spec: [spec/tools/emitc_case_runner.md](spec/tools/emitc_case_runner.md)
    - test: [test/tools/test_emitc_case_runner.py](test/tools/test_emitc_case_runner.py)
    - 功能实现: [kernel_gen/tools/emitc_case_runner.py](kernel_gen/tools/emitc_case_runner.py)
    """

    if compile_args in (None, "--pass no-op"):
        return
    if compile_args == "--pass buffer-results-to-out-params":
        BufferResultsToOutParamsPass().apply(ctx, module)
        return
    raise ValueError(
        "emit_c expectation only supports '// COMPILE_ARGS: --pass no-op' or "
        f"'// COMPILE_ARGS: --pass buffer-results-to-out-params', got {compile_args!r}"
    )


def run_emitc_case(
    case_text: str,
    *,
    source_path: str,
    op_name: str | None = None,
    expected_snippets: list[str],
    forbidden_snippets: list[str] | None = None,
) -> str:
    """执行单条 emit_c expectation case，并校验源码片段。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 解析带注释头的 expectation case 文本。
    - 当前接受未声明 `COMPILE_ARGS`、`// COMPILE_ARGS: --pass no-op` 与
      `// COMPILE_ARGS: --pass buffer-results-to-out-params`。
    - 对解析得到的 `builtin.module` 设置 `target="npu_demo"` 后执行 `emit_c(module, EmitCContext())`，再按给定片段做包含/排除断言。

    使用示例:
    - `run_emitc_case(case_text, source_path="inline", op_name="tuner.cost.kernel.add", expected_snippets=["cost::add"], forbidden_snippets=["tuner.cost("])`

    关联文件:
    - spec: [spec/tools/emitc_case_runner.md](spec/tools/emitc_case_runner.md)
    - test: [test/tools/test_emitc_case_runner.py](test/tools/test_emitc_case_runner.py)
    - 功能实现: [kernel_gen/tools/emitc_case_runner.py](kernel_gen/tools/emitc_case_runner.py)
    """

    if not source_path:
        raise ValueError("source_path must be non-empty")
    if op_name is not None and not op_name:
        raise ValueError("op_name must be non-empty when provided")
    if not expected_snippets and not (forbidden_snippets or []):
        raise ValueError("expected_snippets and forbidden_snippets cannot both be empty")

    compile_args = _extract_compile_args(case_text)
    input_ir = _extract_input_ir(case_text)
    ctx = build_default_context()
    module = Parser(ctx, input_ir).parse_module()
    _apply_compile_args(module, compile_args=compile_args, ctx=ctx)
    snapshot = snapshot_config()
    try:
        set_target("npu_demo")
        source = emit_c(module, EmitCContext())
    finally:
        restore_config(snapshot)

    for snippet in expected_snippets:
        assert snippet in source, (
            f"{source_path}{f' ({op_name})' if op_name else ''}: expected snippet not found: {snippet!r}\n"
            f"--- actual source ---\n{source}"
        )
    for snippet in forbidden_snippets or []:
        assert snippet not in source, (
            f"{source_path}{f' ({op_name})' if op_name else ''}: forbidden snippet found: {snippet!r}\n"
            f"--- actual source ---\n{source}"
        )

    return source


__all__ = [
    "run_emitc_case",
]
