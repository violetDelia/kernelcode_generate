"""`target=npu_demo` 的 type / space 注册入口。


功能说明:
- 通过 side effect import 注册 `npu_demo` 的 type / space 到 C 文本映射。

API 列表:
- 无公开 API。

使用示例:
- `from kernel_gen.dsl.gen_kernel.emit.npu_demo import type as _type`

关联文件:
- spec: [`spec/dsl/gen_kernel/emit.md`](../../../../../../spec/dsl/gen_kernel/emit.md)
- test: [`test/dsl/gen_kernel/emit/test_package.py`](../../../../../../test/dsl/gen_kernel/emit/test_package.py)
- 功能实现: [`kernel_gen/dsl/gen_kernel/emit/npu_demo/type/__init__.py`](../../../../../kernel_gen/dsl/gen_kernel/emit/npu_demo/type/__init__.py)
"""

from . import space as _space  # noqa: F401
from . import type as _type  # noqa: F401

__all__: list[str] = []
