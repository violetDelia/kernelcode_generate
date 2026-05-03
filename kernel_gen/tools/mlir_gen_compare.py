"""mlir_gen 产物比较工具。


功能说明:
- 提供 mlir_gen_compare(...)：生成实际 builtin.module，读取预期 .mlir 文件，
  对两侧执行统一 parser + printer 归一化比较并返回 bool。
- 提供 mlir_gen_compare_text(...)：生成实际 builtin.module，接收预期完整 IR 文本，
  归一化比较并返回 bool。
- 仅比较 mlir_gen 层的 module 文本，不运行 pass、不做 lowering。
- 当生成文本包含 `!nn.memory<...>` 里的 `//` 符号表达式时，绕过 xdsl parser
  对 `//` 注释的误切分，改用当前工具内的空白归一化文本比较。

API 列表:
- mlir_gen_compare(fn: Callable[..., DslFunctionReturn], runtime_args: tuple[DslRuntimeArg, ...] | list[DslRuntimeArg] | None, mlir_file: str) -> bool
- mlir_gen_compare_text(fn: Callable[..., DslFunctionReturn], runtime_args: tuple[DslRuntimeArg, ...] | list[DslRuntimeArg] | None, mlir_text: str) -> bool
- compare_mlir_file(fn: Callable[..., DslFunctionReturn], runtime_args: tuple[DslRuntimeArg, ...] | list[DslRuntimeArg] | None, mlir_file: str) -> bool

使用示例:
- from kernel_gen.tools.mlir_gen_compare import mlir_gen_compare
- ok = mlir_gen_compare(fn=add, runtime_args=[lhs, rhs], mlir_file="expected.mlir")

关联文件:
- spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
- test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
- 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
"""

from __future__ import annotations

from collections.abc import Callable
from io import StringIO
from pathlib import Path
from typing import TypeAlias

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import Operation
from xdsl.parser import Parser
from xdsl.printer import Printer

import kernel_gen.dsl.ast.mlir_gen as mlir_gen_module
from kernel_gen.core.context import build_default_context
from kernel_gen.symbol_variable.memory import Memory
from kernel_gen.symbol_variable.symbol_dim import SymbolDim

DslRuntimeArg: TypeAlias = "Memory | SymbolDim | int | float | bool | str"
DslFunctionReturn: TypeAlias = "DslRuntimeArg | None"


def _render_operation_text(value: Operation) -> str:
    """把 operation 渲染为稳定文本。


    功能说明:
    - 使用统一 printer 将 operation 打印为文本。
    - 去掉尾部空白，便于在当前文件内做稳定字符串比较。

    使用示例:
    - text = _render_operation_text(module)

    关联文件:
    - spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
    - test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
    """

    stream = StringIO()
    Printer(stream=stream).print_op(value)
    return stream.getvalue().rstrip()


def _build_compare_context() -> Context:
    """构造当前文件内使用的最小比较 Context。


    功能说明:
    - 复用 `kernel_gen.core.context.build_default_context()` 的默认 dialect 集合。
    - 避免本工具维护第二套 dialect 注册列表。

    使用示例:
    - ctx = _build_compare_context()

    关联文件:
    - spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
    - test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
    """

    return build_default_context()

def _normalize_module_text(module: ModuleOp, ctx: Context) -> str:
    """对 builtin.module 做当前文件内的解析后归一化。


    功能说明:
    - 先把 module 打印成文本，再用当前文件内 Context 解析回 builtin.module。
    - 重新打印解析结果，去除 printer 差异与尾部空白。
    - 若解析结果不是 builtin.module，则抛出稳定 ValueError。

    使用示例:
    - text = _normalize_module_text(module, ctx)

    关联文件:
    - spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
    - test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
    """

    text = _render_operation_text(module)
    parsed = Parser(ctx, text).parse_module()
    if not isinstance(parsed, ModuleOp):
        raise ValueError("mlir_gen_compare expects builtin.module")
    return _render_operation_text(parsed)


def _requires_raw_memory_expression_compare(actual_text: str, expected_text: str) -> bool:
    """判断是否需要使用当前文件内的 memory 表达式文本兜底比较。

    创建者: 榕
    最后一次更改: 榕

    功能说明:
    - `//` 在 MLIR 词法层是注释起始，`!nn.memory` 的生成文本可能仍需要保留
      `SymbolDim.__floordiv__` 的公开 `//` 表达式。
    - 仅在两侧文本涉及 `!nn.memory` 且任一侧含 `//` 时启用兜底，普通文本继续走
      parser + printer 归一化。

    使用示例:
    - if _requires_raw_memory_expression_compare(actual, expected): ...

    关联文件:
    - spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
    - test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
    """

    return _memory_type_text_contains_floor_div(actual_text) or _memory_type_text_contains_floor_div(expected_text)


def _memory_type_text_contains_floor_div(text: str) -> bool:
    """判断 `!nn.memory<...>` 类型正文内是否含 `//`。

    创建者: 大闸蟹
    最后一次更改: 2026-05-02

    功能说明:
    - 只检查 memory type 尖括号内部，避免把 expected 文件头部 `//` 注释误判为 floor-div 表达式。
    - 支持 memory type 内部嵌套 `#nn.space<...>` 这类尖括号文本。

    使用示例:
    - if _memory_type_text_contains_floor_div(module_text): ...

    关联文件:
    - spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
    - test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
    """

    marker = "!nn.memory<"
    search_from = 0
    while True:
        start = text.find(marker, search_from)
        if start < 0:
            return False
        index = start + len(marker)
        depth = 1
        while index < len(text) and depth > 0:
            char = text[index]
            if char == "<":
                depth += 1
            elif char == ">":
                depth -= 1
            if depth > 0 and text.startswith("//", index):
                return True
            index += 1
        search_from = index


def _strip_mlir_whitespace_outside_strings(text: str) -> str:
    """移除 MLIR 文本中字符串外的空白。

    创建者: 榕
    最后一次更改: 榕

    功能说明:
    - 用于 parser 无法消费 `//` memory 表达式时的窄口径比较兜底。
    - 保留双引号字符串内部空白与转义字符，避免改写 `!symbol.int<"...">` 等文本值。

    使用示例:
    - normalized = _strip_mlir_whitespace_outside_strings(text)

    关联文件:
    - spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
    - test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
    """

    result: list[str] = []
    in_string = False
    escaped = False
    for char in text.strip():
        if in_string:
            result.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            result.append(char)
        elif not char.isspace():
            result.append(char)
    return "".join(result)


def _mlir_gen_compare_expected_text(
    fn: Callable[..., DslFunctionReturn],
    runtime_args: tuple[DslRuntimeArg, ...] | list[DslRuntimeArg] | None,
    expected_text: str,
) -> bool:
    """比较 mlir_gen(...) 结果与预期 module 文本。


    功能说明:
    - 生成实际 builtin.module，并将 expected_text 解析为 builtin.module 后做归一化文本比较。
    - 若 mlir_gen(...) 返回值不是 builtin.module，返回 False。
    - expected_text 解析失败、归一化失败，或归一化文本不一致时返回 False。
    - mlir_gen(...) 抛错时不改变其失败语义，直接向上传播。

    使用示例:
    - ok = _mlir_gen_compare_expected_text(fn=add, runtime_args=[lhs, rhs], expected_text=text)

    关联文件:
    - spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
    - test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
    """

    if runtime_args is None:
        args = ()
    elif isinstance(runtime_args, (list, tuple)):
        args = tuple(runtime_args)
    else:
        raise TypeError("runtime_args must be list, tuple, or None")

    actual_module = mlir_gen_module.mlir_gen(fn, *args)
    if not isinstance(actual_module, ModuleOp):
        return False
    actual_text = _render_operation_text(actual_module)
    if _requires_raw_memory_expression_compare(actual_text, expected_text):
        return _strip_mlir_whitespace_outside_strings(
            actual_text
        ) == _strip_mlir_whitespace_outside_strings(expected_text)

    ctx = _build_compare_context()
    try:
        expected_module = Parser(ctx, expected_text).parse_module()
    except Exception:
        return False
    if not isinstance(expected_module, ModuleOp):
        return False

    try:
        actual_norm = _normalize_module_text(actual_module, ctx)
        expected_norm = _normalize_module_text(expected_module, ctx)
    except Exception:
        return False
    return actual_norm == expected_norm


def mlir_gen_compare(
    fn: Callable[..., DslFunctionReturn],
    runtime_args: tuple[DslRuntimeArg, ...] | list[DslRuntimeArg] | None,
    mlir_file: str,
) -> bool:
    """比较 mlir_gen 结果与预期 mlir 文件。


    功能说明:
    - 生成实际 builtin.module，并与预期 mlir_file 做规范化文本比较。
    - 若 mlir_gen(...) 返回值不是 builtin.module，返回 False。
    - 预期文件读取失败、解析失败、归一化失败，或归一化文本不一致时返回 False。

    使用示例:
    - ok = mlir_gen_compare(fn=add, runtime_args=[lhs, rhs], mlir_file="expected.mlir")

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
        expected_text=expected_text,
    )


def mlir_gen_compare_text(
    fn: Callable[..., DslFunctionReturn],
    runtime_args: tuple[DslRuntimeArg, ...] | list[DslRuntimeArg] | None,
    mlir_text: str,
) -> bool:
    """比较 mlir_gen 结果与预期 module 文本。


    功能说明:
    - 生成实际 builtin.module，并将 mlir_text 解析为 builtin.module 后做归一化文本比较。
    - 若 mlir_text 解析失败或解析结果不是 builtin.module，返回 False。
    - 若 mlir_gen(...) 返回值不是 builtin.module，返回 False。
    - 归一化后的文本不一致时返回 False。
    - mlir_gen(...) 抛错时不改变其失败语义，直接向上传播。

    使用示例:
    - ok = mlir_gen_compare_text(fn=add, runtime_args=[lhs, rhs], mlir_text=text)

    关联文件:
    - spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
    - test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
    """

    return _mlir_gen_compare_expected_text(
        fn=fn,
        runtime_args=runtime_args,
        expected_text=mlir_text,
    )


def compare_mlir_file(
    fn: Callable[..., DslFunctionReturn],
    runtime_args: tuple[DslRuntimeArg, ...] | list[DslRuntimeArg] | None,
    mlir_file: str,
) -> bool:
    """兼容旧接口 compare_mlir_file(...)，等价于 mlir_gen_compare(...)。


    功能说明:
    - 保持旧接口可用，便于下游脚本与测试渐进迁移到 mlir_gen_compare(...)。

    使用示例:
    - ok = compare_mlir_file(fn=add, runtime_args=[lhs, rhs], mlir_file="expected.mlir")

    关联文件:
    - spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
    - test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
    """

    return mlir_gen_compare(
        fn=fn,
        runtime_args=runtime_args,
        mlir_file=mlir_file,
    )
