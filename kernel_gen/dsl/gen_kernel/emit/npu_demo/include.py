"""`target=npu_demo` 的源码前导注册。"""

from __future__ import annotations

from ..register import emit_c_include_impl


@emit_c_include_impl(target="npu_demo")
def _emit_npu_demo_include(_ctx) -> str:
    return '#include "include/npu_demo/npu_demo.h"\nusing namespace npu_demo;\n\n'

