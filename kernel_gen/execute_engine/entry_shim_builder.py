"""Entry shim builder for ExecutionEngine (P0/S2).

创建者: 朽木露琪亚
最后一次更改: jcc你莫辜负

功能说明:
- 提供最小 entry shim 生成与检测逻辑，用于 S2 编译路径的可复现拼装。
- 仅负责入口名与参数签名骨架，不实现真实参数绑定。

使用示例:
- from kernel_gen.execute_engine.entry_shim_builder import build_entry_shim_source, needs_entry_shim
- src = build_entry_shim_source(function="cpu::add", entry_point="kg_execute_entry")
- assert needs_entry_shim("int main(){}", "kg_execute_entry") is True

关联文件:
- spec: spec/execute_engine/execute_engine_target.md
- test: test/execute_engine/test_execute_engine_compile.py
- 功能实现: kernel_gen/execute_engine/entry_shim_builder.py
"""

from __future__ import annotations

import re


def needs_entry_shim(source: str, entry_point: str) -> bool:
    """判断是否需要生成 entry shim。

    创建者: jcc你莫辜负
    最后一次更改: jcc你莫辜负

    功能说明:
    - 当源码未显式提供 `extern "C"` 且同名入口时，返回 True。
    - 用于避免重复生成已存在的稳定入口。

    使用示例:
    - assert needs_entry_shim('extern "C" int kg_execute_entry(...) { return 0; }', "kg_execute_entry") is False

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_execute_engine_compile.py
    - 功能实现: kernel_gen/execute_engine/entry_shim_builder.py
    """

    if not isinstance(source, str) or not isinstance(entry_point, str):
        return True
    pattern = rf'extern\s+"C"\s+[^;{{]*\b{re.escape(entry_point)}\b'
    return re.search(pattern, source) is None


def build_entry_shim_source(*, function: str, entry_point: str) -> str:
    """构造最小 entry shim 源码片段（占位）。

    创建者: 朽木露琪亚
    最后一次更改: jcc你莫辜负

    功能说明:
    - S2 阶段用于生成可被编译器接受的最小入口骨架。
    - 不负责参数绑定与真实调用，仅提供稳定入口签名与返回值占位。

    使用示例:
    - src = build_entry_shim_source(function="cpu::add", entry_point="kg_execute_entry")

    关联文件:
    - spec: spec/execute_engine/execute_engine_target.md
    - test: test/execute_engine/test_execute_engine_compile.py
    - 功能实现: kernel_gen/execute_engine/entry_shim_builder.py
    """

    return (
        f"// entry shim placeholder for {function} as {entry_point}\n"
        "struct KgArgSlot;\n"
        f'extern "C" int {entry_point}(const KgArgSlot* ordered_args, unsigned long long arg_count) {{\n'
        "  (void)ordered_args;\n"
        "  (void)arg_count;\n"
        "  return 0;\n"
        "}\n"
    )


__all__ = ["build_entry_shim_source", "needs_entry_shim"]
