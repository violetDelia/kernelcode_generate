"""pass common helpers.


功能说明:
- 提供 `kernel_gen.passes` 共享的 pass 合同校验 helper。
- 提供 pass 级公共校验 helper，避免在多个 pass 中重复定义模块类型校验、统一报错入口和新生成 op verifier 包装逻辑。

API 列表:
- `ensure_builtin_module(module: ModuleOp) -> ModuleOp`
- `raise_pass_contract_error(keyword: str, detail: str) -> None`
- `verify_generated_ops(ops: Sequence[Operation]) -> None`

使用示例:
- from kernel_gen.passes.common import ensure_builtin_module, raise_pass_contract_error, verify_generated_ops
- module = ensure_builtin_module(module)
- raise_pass_contract_error("UnsupportedOp", "unsupported op custom.foo")
- verify_generated_ops([new_op])

关联文件:
- spec: spec/pass/decompass.md
- spec: spec/pass/buffer_results_to_out_params.md
- test: test/passes/decompass/test_softmax.py
- test: test/passes/test_buffer_results_to_out_params.py
- 功能实现: kernel_gen/passes/common.py
"""

from __future__ import annotations
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError

from collections.abc import Sequence

from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import Operation
from xdsl.utils.exceptions import VerifyException




def ensure_builtin_module(module: ModuleOp) -> ModuleOp:
    """校验 pass 输入必须是 `builtin.module`。


    功能说明:
    - 为 pass 入口提供统一的 `ModuleOp` 类型校验。
    - 失败时抛出 `KernelCodeError(module="pass", message="module must be builtin.module")`。

    使用示例:
    - module = ensure_builtin_module(module)

    关联文件:
    - spec: spec/pass/decompass.md
    - spec: spec/pass/buffer_results_to_out_params.md
    - test: test/passes/decompass/test_softmax.py
    - test: test/passes/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/common.py
    """

    if not isinstance(module, ModuleOp):
        raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, "module must be builtin.module")
    return module


def raise_pass_contract_error(keyword: str, detail: str) -> None:
    """抛出统一格式的 pass 合同错误。


    功能说明:
    - 为需要 `Keyword: detail` 失败文本的 pass 提供统一构造入口。
    - 避免各 pass 再复制粘贴自定义 `_raise_*_error(...)` helper。

    使用示例:
    - raise_pass_contract_error("TilePassUnsupportedOp", "unsupported tile op")

    关联文件:
    - spec: spec/pass/tile/README.md
    - test: test/passes/tile/test_package.py
    - 功能实现: kernel_gen/passes/common.py
    """

    raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, f"{keyword}: {detail}")


def verify_generated_ops(ops: Sequence[Operation]) -> None:
    """逐个调用 verifier 校验新生成 op。


    功能说明:
    - 把方言 verifier 抛出的 `VerifyException` 统一包装成 `KernelCodeError`。
    - 适合在 pass pattern 中对新生成 op 做局部合同校验。

    使用示例:
    - verify_generated_ops([max_op, exp_op, div_op])

    关联文件:
    - spec: spec/pass/decompass.md
    - spec: spec/pass/buffer_results_to_out_params.md
    - test: test/passes/decompass/test_softmax.py
    - test: test/passes/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/common.py
    """

    for op in ops:
        try:
            op.verify()
        except VerifyException as exc:
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.PASS, str(exc)) from exc


__all__ = [
    "ensure_builtin_module",
    "raise_pass_contract_error",
    "verify_generated_ops",
]
