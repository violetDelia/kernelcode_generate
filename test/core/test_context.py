"""core context tests.


功能说明:
- 覆盖 `build_default_context()` 的公开 dialect 加载合同。

使用示例:
- pytest -q test/core/test_context.py

关联文件:
- 功能实现: kernel_gen/core/context.py
- Spec 文档: spec/core/context.md
- 测试文件: test/core/test_context.py
"""

from __future__ import annotations

from xdsl.parser import Parser

from kernel_gen.core.context import build_default_context


def test_default_context_loads_memory_dialect() -> None:
    """默认 Context 加载 memory dialect 并可解析 `memory.get_data`。"""

    ctx = build_default_context()

    assert ctx.get_optional_dialect("memory") is not None
    module = Parser(
        ctx,
        """
builtin.module {
  func.func @get_data(%mem: !nn.memory<[#symbol.expr<N>], [#symbol.expr<1>], f32, #nn.space<global>, template = T_bias>) {
    %ptr = memory.get_data %mem : !nn.memory<[#symbol.expr<N>], [#symbol.expr<1>], f32, #nn.space<global>, template = T_bias> -> !symbol.ptr<f32, template = T_bias>
    func.return
  }
}
""",
    ).parse_module()
    module.verify()
