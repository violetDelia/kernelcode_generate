"""pass common helpers.

创建者: 守护最好的爱莉希雅
最后一次更改: 守护最好的爱莉希雅

功能说明:
- 提供 `kernel_gen.passes` 共享的显式错误类型。
- 提供 pass 级公共校验 helper，避免在多个 pass 中重复定义模块类型校验、统一报错入口和新生成 op verifier 包装逻辑。

使用示例:
- from kernel_gen.passes.common import PassContractError, ensure_builtin_module, raise_pass_contract_error, verify_generated_ops
- module = ensure_builtin_module(module)
- raise_pass_contract_error("UnsupportedOp", "unsupported op custom.foo")
- verify_generated_ops([new_op])

关联文件:
- spec: spec/pass/decompass.md
- spec: spec/pass/buffer_results_to_out_params.md
- test: test/pass/decompass/test_softmax.py
- test: test/pass/test_buffer_results_to_out_params.py
- 功能实现: kernel_gen/passes/common.py
"""

from __future__ import annotations

from collections.abc import Sequence

from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import Operation
from xdsl.utils.exceptions import VerifyException


class PassContractError(ValueError):
    """`kernel_gen.passes` 共享的显式错误。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 统一承载 pass 公开失败边界，避免每个 pass 再定义独立错误类。
    - 保持错误类型稳定，便于测试、spec 与只读 expectation 通过兼容别名继续引用。

    使用示例:
    - raise PassContractError("module must be builtin.module")

    关联文件:
    - spec: spec/pass/decompass.md
    - spec: spec/pass/buffer_results_to_out_params.md
    - test: test/pass/decompass/test_softmax.py
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/common.py
    """


def ensure_builtin_module(module: object) -> ModuleOp:
    """校验 pass 输入必须是 `builtin.module`。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 为 pass 入口提供统一的 `ModuleOp` 类型校验。
    - 失败时抛出 `PassContractError("module must be builtin.module")`。

    使用示例:
    - module = ensure_builtin_module(module)

    关联文件:
    - spec: spec/pass/decompass.md
    - spec: spec/pass/buffer_results_to_out_params.md
    - test: test/pass/decompass/test_softmax.py
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/common.py
    """

    if not isinstance(module, ModuleOp):
        raise PassContractError("module must be builtin.module")
    return module


def raise_pass_contract_error(keyword: str, detail: str) -> None:
    """抛出统一格式的 pass 合同错误。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 为需要 `Keyword: detail` 失败文本的 pass 提供统一构造入口。
    - 避免各 pass 再复制粘贴自定义 `_raise_*_error(...)` helper。

    使用示例:
    - raise_pass_contract_error("TilePassUnsupportedOp", "unsupported tile op")

    关联文件:
    - spec: spec/pass/tile/README.md
    - test: test/pass/tile/test_package.py
    - 功能实现: kernel_gen/passes/common.py
    """

    raise PassContractError(f"{keyword}: {detail}")


def verify_generated_ops(ops: Sequence[Operation]) -> None:
    """逐个调用 verifier 校验新生成 op。

    创建者: 守护最好的爱莉希雅
    最后一次更改: 守护最好的爱莉希雅

    功能说明:
    - 把方言 verifier 抛出的 `VerifyException` 统一包装成 `PassContractError`。
    - 适合在 pass pattern 中对新生成 op 做局部合同校验。

    使用示例:
    - verify_generated_ops([max_op, exp_op, div_op])

    关联文件:
    - spec: spec/pass/decompass.md
    - spec: spec/pass/buffer_results_to_out_params.md
    - test: test/pass/decompass/test_softmax.py
    - test: test/pass/test_buffer_results_to_out_params.py
    - 功能实现: kernel_gen/passes/common.py
    """

    for op in ops:
        try:
            op.verify()
        except VerifyException as exc:
            raise PassContractError(str(exc)) from exc


__all__ = [
    "PassContractError",
    "ensure_builtin_module",
    "raise_pass_contract_error",
    "verify_generated_ops",
]
