"""mlir_gen 产物比较工具。

创建者: 睡觉小分队
最后一次更改: 小李飞刀

功能说明:
- 提供 compare_mlir_file(...)：生成实际 builtin.module，读取预期 .mlir 文件，
  对两侧执行统一 parser + printer 归一化比较并返回 bool。
- 仅比较 mlir_gen 层的 module 文本，不运行 pass、不做 lowering。

使用示例:
- from kernel_gen.tools.mlir_gen_compare import compare_mlir_file
- ok = compare_mlir_file(fn=add, runtime_args=[lhs, rhs], config=None, mlir_file="expected.mlir")

关联文件:
- spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
- test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
- 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
"""

from __future__ import annotations

from collections.abc import Callable
from io import StringIO
from pathlib import Path

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.parser import Parser
from xdsl.printer import Printer


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


def compare_mlir_file(
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
    - ok = compare_mlir_file(fn=add, runtime_args=[lhs, rhs], config=None, mlir_file="expected.mlir")

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

    try:
        expected_text = Path(mlir_file).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False

    ctx = _build_default_context()
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
