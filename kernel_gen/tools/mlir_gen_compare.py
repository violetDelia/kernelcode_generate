"""mlir_gen 产物比较工具。

创建者: 睡觉小分队
最后一次更改: 金铲铲大作战

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
from xdsl.dialects.builtin import Builtin, ModuleOp
from xdsl.dialects.func import Func
from xdsl.parser import Parser
from xdsl.printer import Printer

from kernel_gen.dialect.kernel import Kernel
from kernel_gen.dialect.nn import Nn


def _build_default_context() -> Context:
    """构造用于解析与打印的默认 xdsl Context。

    创建者: 睡觉小分队
    最后一次更改: 金铲铲大作战

    功能说明:
    - 加载 builtin/func 及仓库内轻量 dialect（nn/kernel），用于 module 解析与打印。

    使用示例:
    - ctx = _build_default_context()
    - module = Parser(ctx, ir_text).parse_module()

    关联文件:
    - spec: [spec/tools/mlir_gen_compare.md](spec/tools/mlir_gen_compare.md)
    - test: [test/tools/test_mlir_gen_compare.py](test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/tools/mlir_gen_compare.py](kernel_gen/tools/mlir_gen_compare.py)
    """

    ctx = Context()
    ctx.load_dialect(Builtin)
    ctx.load_dialect(Func)
    ctx.load_dialect(Nn)
    ctx.load_dialect(Kernel)
    return ctx


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
    最后一次更改: 金铲铲大作战

    功能说明:
    - 生成实际 builtin.module，并与预期 mlir_file 做规范化文本比较。
    - 读取失败、解析失败或非 builtin.module 时返回 False。

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
        raise TypeError("mlir_gen must return builtin.module")

    try:
        expected_text = Path(mlir_file).read_text(encoding="utf-8")
    except OSError:
        return False

    ctx = _build_default_context()
    try:
        expected_module = Parser(ctx, expected_text).parse_module()
    except Exception:
        return False
    if not isinstance(expected_module, ModuleOp):
        return False

    actual_norm = _normalize_module(actual_module, ctx)
    expected_norm = _normalize_module(expected_module, ctx)
    return actual_norm == expected_norm
