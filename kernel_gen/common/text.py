"""Common text helpers for kernel_gen.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 提供 kernel_gen 内部可复用的 IR 文本渲染、module 归一化与源码分段拼接辅助。
- 该模块只封装通用文本处理，不改变 DSL / tools / execute_engine 的公开合同。

使用示例:
- from kernel_gen.common.text import join_text_sections, normalize_module_text
- text = join_text_sections("#include <a>", "int main() {}")
- normalized = normalize_module_text(module, ctx)

关联文件:
- spec:
  - [spec/tools/mlir_gen_compare.md](../../spec/tools/mlir_gen_compare.md)
  - [spec/tools/ircheck.md](../../spec/tools/ircheck.md)
  - [spec/execute_engine/execute_engine_target.md](../../spec/execute_engine/execute_engine_target.md)
- test:
  - [test/tools/test_mlir_gen_compare.py](../../test/tools/test_mlir_gen_compare.py)
  - [test/tools/test_ircheck_runner.py](../../test/tools/test_ircheck_runner.py)
  - [test/execute_engine/test_execute_engine_compile.py](../../test/execute_engine/test_execute_engine_compile.py)
- 功能实现: [kernel_gen/common/text.py](kernel_gen/common/text.py)
"""

from __future__ import annotations

from io import StringIO

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import Operation
from xdsl.parser import Parser
from xdsl.printer import Printer

__all__ = [
    "join_text_sections",
    "normalize_module_text",
    "render_operation_text",
]


def render_operation_text(value: Operation) -> str:
    """把 xDSL operation 渲染为稳定文本。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 使用统一 printer 将 operation 打印为文本。
    - 去掉尾部空白，便于 FileCheck 风格逐行比较。

    使用示例:
    - text = render_operation_text(module)

    关联文件:
    - spec:
      - [spec/tools/ircheck.md](../../spec/tools/ircheck.md)
      - [spec/tools/mlir_gen_compare.md](../../spec/tools/mlir_gen_compare.md)
    - test:
      - [test/tools/test_ircheck_runner.py](../../test/tools/test_ircheck_runner.py)
      - [test/tools/test_mlir_gen_compare.py](../../test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/common/text.py](kernel_gen/common/text.py)
    """

    stream = StringIO()
    Printer(stream=stream).print_op(value)
    return stream.getvalue().rstrip()


def normalize_module_text(module: ModuleOp, ctx: Context) -> str:
    """对 module 执行解析后再打印的归一化。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 先把 module 打印成文本，再用统一 Context 解析回 builtin.module。
    - 重新打印解析结果，去除空白与 parser/printer 差异。
    - 若解析结果不是 builtin.module，则抛出稳定 ValueError。

    使用示例:
    - text = normalize_module_text(module, ctx)

    关联文件:
    - spec:
      - [spec/tools/mlir_gen_compare.md](../../spec/tools/mlir_gen_compare.md)
    - test:
      - [test/tools/test_mlir_gen_compare.py](../../test/tools/test_mlir_gen_compare.py)
    - 功能实现: [kernel_gen/common/text.py](kernel_gen/common/text.py)
    """

    text = render_operation_text(module)
    parsed = Parser(ctx, text).parse_module()
    if not isinstance(parsed, ModuleOp):
        raise ValueError("mlir_gen_compare expects builtin.module")
    return render_operation_text(parsed)


def join_text_sections(*sections: str) -> str:
    """把多段文本按空行拼接为单个源码片段。

    创建者: 金铲铲大作战
    最后一次更改: 金铲铲大作战

    功能说明:
    - 过滤空字符串段，并统一去掉每段尾部空白。
    - 以空行分隔段落，保持源码片段的稳定换行口径。
    - 结果始终以单个换行结束，便于写文件与做文本比较。

    使用示例:
    - source = join_text_sections("#include <a>", "int main() {}")

    关联文件:
    - spec:
      - [spec/execute_engine/execute_engine_target.md](../../spec/execute_engine/execute_engine_target.md)
      - [spec/tools/mlir_gen_compare.md](../../spec/tools/mlir_gen_compare.md)
      - [spec/tools/ircheck.md](../../spec/tools/ircheck.md)
    - test:
      - [test/execute_engine/test_execute_engine_compile.py](../../test/execute_engine/test_execute_engine_compile.py)
      - [test/tools/test_mlir_gen_compare.py](../../test/tools/test_mlir_gen_compare.py)
      - [test/tools/test_ircheck_runner.py](../../test/tools/test_ircheck_runner.py)
    - 功能实现: [kernel_gen/common/text.py](kernel_gen/common/text.py)
    """

    normalized_sections = tuple(section.rstrip() for section in sections if section)
    if not normalized_sections:
        return "\n"
    return "\n\n".join(normalized_sections).rstrip() + "\n"
