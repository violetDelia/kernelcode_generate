"""mlir_gen 产物比较工具。

创建者: 睡觉小分队
最后一次更改: 榕

功能说明:
- 提供 mlir_gen_compare(...)：生成实际 builtin.module，读取预期 .mlir 文件，
  对两侧执行统一 parser + printer 归一化比较并返回 bool。
- 提供 mlir_gen_compare_text(...)：生成实际 builtin.module，接收预期完整 IR 文本，
  归一化比较并返回 bool。
- 仅比较 mlir_gen 层的 module 文本，不运行 pass、不做 lowering。

API 列表:
- mlir_gen_compare(fn: Callable[..., object], runtime_args: tuple[object, ...] | list[object] | None, mlir_file: str) -> bool
- mlir_gen_compare_text(fn: Callable[..., object], runtime_args: tuple[object, ...] | list[object] | None, mlir_text: str) -> bool
- compare_mlir_file(fn: Callable[..., object], runtime_args: tuple[object, ...] | list[object] | None, mlir_file: str) -> bool

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

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import Operation
from xdsl.parser import Parser
from xdsl.printer import Printer

import kernel_gen.dsl.mlir_gen as mlir_gen_module
from kernel_gen.core.context import build_default_context


def _render_operation_text(value: Operation) -> str:
    """把 operation 渲染为稳定文本。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

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

    创建者: 金铲铲大作战
    最后一次更改: 榕

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

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

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


def _mlir_gen_compare_expected_text(
    fn: Callable[..., object],
    runtime_args: tuple[object, ...] | list[object] | None,
    expected_text: str,
) -> bool:
    """比较 mlir_gen(...) 结果与预期 module 文本。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 金铲铲大作战

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
    fn: Callable[..., object],
    runtime_args: tuple[object, ...] | list[object] | None,
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
    fn: Callable[..., object],
    runtime_args: tuple[object, ...] | list[object] | None,
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
    fn: Callable[..., object],
    runtime_args: tuple[object, ...] | list[object] | None,
    mlir_file: str,
) -> bool:
    """兼容旧接口 compare_mlir_file(...)，等价于 mlir_gen_compare(...)。

    创建者: 睡觉小分队
    最后一次更改: 小李飞刀

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
