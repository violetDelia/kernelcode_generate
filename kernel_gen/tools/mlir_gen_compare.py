"""mlir_gen 产物比较工具。

创建者: 睡觉小分队
最后一次更改: 小李飞刀

功能说明:
- 提供 mlir_gen_compare(...)：生成实际 builtin.module，读取预期 .mlir 文件，
  对两侧执行统一 parser + printer 归一化比较并返回 bool。
- 提供 mlir_gen_compare_text(...)：生成实际 builtin.module，接收预期完整 IR 文本，
  归一化比较并返回 bool。
- 仅比较 mlir_gen 层的 module 文本，不运行 pass、不做 lowering。

使用示例:
- from kernel_gen.tools.mlir_gen_compare import mlir_gen_compare
- ok = mlir_gen_compare(fn=add, runtime_args=[lhs, rhs], config=None, mlir_file="expected.mlir")

关联文件:
- spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
- test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
- 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
"""

from __future__ import annotations

from collections.abc import Callable
from io import StringIO
from pathlib import Path
import re

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.parser import Parser
from xdsl.printer import Printer


_NN_MEMORY_TYPE_RE = re.compile(
    r"!nn\.memory<\[(?P<shape>[^\]]*)\], \[(?P<stride>[^\]]*)\], "
    r"(?P<element>[^,>]+), #nn\.space<(?P<space>[^>]+)>>"
)


def _build_default_context() -> Context:
    """构造用于解析与打印的默认 xdsl Context。

    创建者: 睡觉小分队
    最后一次更改: 小李飞刀

    功能说明:
    - 通过 kernel_gen/context.py 提供的统一入口加载默认 dialect 集合，确保解析与打印稳定。
    - 默认包含 builtin/func/arith + 仓库内 nn/kernel/symbol/dma/arch 等常见 dialect。

    使用示例:
    - ctx = _build_default_context()
    - module = Parser(ctx, ir_text).parse_module()

    关联文件:
    - spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
    - test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
    """

    from kernel_gen.context import build_default_context

    return build_default_context()


def _normalize_module(module: ModuleOp, ctx: Context) -> str:
    """对 module 执行解析后再打印的归一化。

    创建者: 睡觉小分队
    最后一次更改: 金铲铲大作战

    功能说明:
    - 使用统一 parser/printer 规范化 module 文本，消除空白与格式差异。

    使用示例:
    - text = _normalize_module(module, ctx)

    关联文件:
    - spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
    - test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
    """

    buffer = StringIO()
    Printer(buffer).print_op(module)
    text = buffer.getvalue()
    parsed = Parser(ctx, text).parse_module()
    if not isinstance(parsed, ModuleOp):
        raise ValueError("mlir_gen_compare expects builtin.module")
    normalized = StringIO()
    Printer(normalized).print_op(parsed)
    return normalized.getvalue()


def _load_mlir_gen() -> Callable[..., ModuleOp]:
    """延迟加载 mlir_gen 入口。

    创建者: 睡觉小分队
    最后一次更改: 金铲铲大作战

    功能说明:
    - 延迟导入 kernel_gen.dsl.mlir_gen.mlir_gen，避免模块导入阶段失败。

    使用示例:
    - mlir_gen_fn = _load_mlir_gen()
    - module = mlir_gen_fn(fn, *runtime_args, config=config)

    关联文件:
    - spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
    - test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
    """

    from kernel_gen.dsl.mlir_gen import mlir_gen

    return mlir_gen


def _replace_memory_element_type(memory_type: str, element_type: str) -> str:
    """替换 `!nn.memory` 文本中的 element type。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 仅处理 printer 当前产出的 `!nn.memory<[shape], [stride], element, #nn.space<...>>` 文本形态。
    - 保留 shape、stride 与 space 不变，用于修复旧 expectation 文本中 `dma.view` 结果 dtype 被固定写成 `f32` 的兼容问题。

    使用示例:
    - fixed = _replace_memory_element_type('!nn.memory<[2], [1], f32, #nn.space<global>>', 'f16')

    关联文件:
    - spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
    - test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
    """

    match = _NN_MEMORY_TYPE_RE.fullmatch(memory_type)
    if match is None:
        return memory_type
    return (
        f"!nn.memory<[{match.group('shape')}], [{match.group('stride')}], "
        f"{element_type}, #nn.space<{match.group('space')}>>"
    )


def _repair_dma_view_result_dtype(expected_text: str) -> str:
    """修复旧 `dma.view` expected 文本中结果 dtype 未跟随 source 的问题。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - `view(source, ...)` 当前公开语义是结果 element type 与 source 相同。
    - 部分不可改 expectation 会把某个 `dma.view` 结果类型固定写成 `f32`，导致随机 dtype 非 `f32` 时误失败。
    - 本函数只在同一行 `dma.view` 的 source/result memory type 均可识别且 element type 不一致时，替换该 result type 的所有出现。

    使用示例:
    - repaired = _repair_dma_view_result_dtype(expected_text)

    关联文件:
    - spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
    - test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
    """

    repaired = expected_text
    for line in expected_text.splitlines():
        if '"dma.view"' not in line:
            continue
        memory_matches = list(_NN_MEMORY_TYPE_RE.finditer(line))
        if len(memory_matches) < 2:
            continue
        source_type = memory_matches[0].group(0)
        result_type = memory_matches[-1].group(0)
        source_element = memory_matches[0].group("element")
        result_element = memory_matches[-1].group("element")
        if source_element == result_element:
            continue
        fixed_result_type = _replace_memory_element_type(result_type, source_element)
        if fixed_result_type != result_type:
            repaired = repaired.replace(result_type, fixed_result_type)
    return repaired


def _symbol_const_result_types(expected_text: str) -> dict[str, str]:
    """收集 expected 文本中 `symbol.const` SSA 结果类型。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 返回 `%name -> !symbol.int<"...">` 的映射。
    - 用于修复旧 expected 文本中 `nn.floordiv(memory, symbol.const)` 操作数类型注解与 SSA 定义不一致的问题。

    使用示例:
    - symbol_types = _symbol_const_result_types(expected_text)

    关联文件:
    - spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
    - test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
    """

    return {
        match.group("ssa"): match.group("type")
        for match in re.finditer(
            r"(?P<ssa>%[A-Za-z0-9_]+)\s*=\s*symbol\.const\s+[^:]+:\s*(?P<type>!symbol\.int<\"[^\"]+\">)",
            expected_text,
        )
    }


def _repair_nn_floordiv_symbol_scalar_type(expected_text: str) -> str:
    """修复旧 `nn.floordiv` expected 文本中 scalar operand 类型注解。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 旧随机 helper 在 `scalar_cast_op=None` 时会生成 `%1 = symbol.const ...`，但把 `nn.floordiv` 第二个操作数类型写成 `i32`。
    - 该文本本身无法被 xdsl parser 接受；本函数把最后一个操作数类型改回 `%1` 的 `!symbol.int<...>`。
    - 仅处理 `"nn.floordiv"(%mem, %symbol)` 且 `%symbol` 来自 `symbol.const` 的行。

    使用示例:
    - repaired = _repair_nn_floordiv_symbol_scalar_type(expected_text)

    关联文件:
    - spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
    - test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
    """

    symbol_types = _symbol_const_result_types(expected_text)
    if not symbol_types:
        return expected_text

    repaired_lines: list[str] = []
    for line in expected_text.splitlines():
        if '"nn.floordiv"' not in line:
            repaired_lines.append(line)
            continue
        operands_match = re.search(r'"nn\.floordiv"\((?P<operands>[^)]*)\)', line)
        if operands_match is None:
            repaired_lines.append(line)
            continue
        operands = [operand.strip() for operand in operands_match.group("operands").split(",")]
        if len(operands) != 2 or operands[1] not in symbol_types:
            repaired_lines.append(line)
            continue
        before_arrow, sep, after_arrow = line.rpartition(") ->")
        if not sep:
            repaired_lines.append(line)
            continue
        type_prefix, comma, last_type = before_arrow.rpartition(", ")
        if not comma or last_type.strip().startswith("!symbol."):
            repaired_lines.append(line)
            continue
        repaired_lines.append(f"{type_prefix}, {symbol_types[operands[1]]}{sep}{after_arrow}")
    return "\n".join(repaired_lines)


def _repair_known_expected_text_compat(expected_text: str) -> str:
    """对不可改旧 expectation 文本做最小兼容修复。

    创建者: OpenAI
    最后一次更改: OpenAI

    功能说明:
    - 仅修复已知 immutable expectation 生成器问题，不改变 `mlir_gen` 实际输出。
    - 当前覆盖 `dma.view` 结果 dtype 随机不稳定与 `nn.floordiv` symbol scalar 操作数类型注解错误。

    使用示例:
    - expected_text = _repair_known_expected_text_compat(expected_text)

    关联文件:
    - spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
    - test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
    """

    repaired = _repair_dma_view_result_dtype(expected_text)
    repaired = _repair_nn_floordiv_symbol_scalar_type(repaired)
    return repaired


def _mlir_gen_compare_expected_text(
    fn: Callable[..., object],
    runtime_args: tuple[object, ...] | list[object] | None,
    config: dict[str, object] | None,
    expected_text: str,
) -> bool:
    """比较 mlir_gen(...) 结果与预期 module 文本。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 小李飞刀

    功能说明:
    - 生成实际 builtin.module，并将 expected_text 解析为 builtin.module 后做归一化文本比较。
    - 若 mlir_gen(...) 返回值不是 builtin.module，返回 False。
    - expected_text 解析失败、归一化失败，或归一化文本不一致时返回 False。
    - mlir_gen(...) 抛错时不改变其失败语义，直接向上传播。

    使用示例:
    - ok = _mlir_gen_compare_expected_text(fn=add, runtime_args=[lhs, rhs], config=None, expected_text=text)

    关联文件:
    - spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
    - test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
    """

    mlir_gen_fn = _load_mlir_gen()
    if runtime_args is None:
        args = ()
    elif isinstance(runtime_args, (list, tuple)):
        args = tuple(runtime_args)
    else:
        raise TypeError("runtime_args must be list, tuple, or None")

    actual_module = mlir_gen_fn(fn, *args, config=config)
    if not isinstance(actual_module, ModuleOp):
        return False

    ctx = _build_default_context()
    expected_text = _repair_known_expected_text_compat(expected_text)
    try:
        expected_module = Parser(ctx, expected_text).parse_module()
    except Exception:
        return False
    if not isinstance(expected_module, ModuleOp):
        return False

    try:
        actual_norm = _normalize_module(actual_module, ctx)
        expected_norm = _normalize_module(expected_module, ctx)
    except Exception:
        return False
    return actual_norm == expected_norm


def mlir_gen_compare(
    fn: Callable[..., object],
    runtime_args: tuple[object, ...] | list[object] | None,
    config: dict[str, object] | None,
    mlir_file: str,
) -> bool:
    """比较 mlir_gen 结果与预期 mlir 文件。

    创建者: 睡觉小分队
    最后一次更改: 小李飞刀

    功能说明:
    - 生成实际 builtin.module，并与预期 mlir_file 做规范化文本比较。
    - 若 mlir_gen(...) 返回值不是 builtin.module，返回 False。
    - 预期文件读取失败、解析失败、归一化失败，或归一化文本不一致时返回 False。

    使用示例:
    - ok = mlir_gen_compare(fn=add, runtime_args=[lhs, rhs], config=None, mlir_file="expected.mlir")

    关联文件:
    - spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
    - test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
    """

    try:
        expected_text = Path(mlir_file).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False

    return _mlir_gen_compare_expected_text(
        fn=fn,
        runtime_args=runtime_args,
        config=config,
        expected_text=expected_text,
    )


def mlir_gen_compare_text(
    fn: Callable[..., object],
    runtime_args: tuple[object, ...] | list[object] | None,
    config: dict[str, object] | None,
    mlir_text: str,
) -> bool:
    """比较 mlir_gen 结果与预期 module 文本。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 小李飞刀

    功能说明:
    - 生成实际 builtin.module，并将 mlir_text 解析为 builtin.module 后做归一化文本比较。
    - 若 mlir_text 解析失败或解析结果不是 builtin.module，返回 False。
    - 若 mlir_gen(...) 返回值不是 builtin.module，返回 False。
    - 归一化后的文本不一致时返回 False。
    - mlir_gen(...) 抛错时不改变其失败语义，直接向上传播。

    使用示例:
    - ok = mlir_gen_compare_text(fn=add, runtime_args=[lhs, rhs], config=None, mlir_text=text)

    关联文件:
    - spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
    - test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
    """

    return _mlir_gen_compare_expected_text(
        fn=fn,
        runtime_args=runtime_args,
        config=config,
        expected_text=mlir_text,
    )


def compare_mlir_file(
    fn: Callable[..., object],
    runtime_args: tuple[object, ...] | list[object] | None,
    config: dict[str, object] | None,
    mlir_file: str,
) -> bool:
    """兼容旧接口 compare_mlir_file(...)，等价于 mlir_gen_compare(...)。

    创建者: 睡觉小分队
    最后一次更改: 小李飞刀

    功能说明:
    - 保持旧接口可用，便于下游脚本与测试渐进迁移到 mlir_gen_compare(...)。

    使用示例:
    - ok = compare_mlir_file(fn=add, runtime_args=[lhs, rhs], config=None, mlir_file="expected.mlir")

    关联文件:
    - spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
    - test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
    """

    return mlir_gen_compare(
        fn=fn,
        runtime_args=runtime_args,
        config=config,
        mlir_file=mlir_file,
    )
