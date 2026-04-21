"""Legacy `gen_kernel.py` loader for the package-style public entry.

创建者: 小李飞刀
最后一次更改: 小李飞刀

功能说明:
- 以文件路径方式加载旧版 `kernel_gen/dsl/gen_kernel.py` 实现。
- 让新包根 `kernel_gen.dsl.gen_kernel` 能在 S1 阶段先保留原始生成行为，再逐步拆分内部实现。

使用示例:
- legacy_gen_kernel = load_legacy_gen_kernel_module()
- source = legacy_gen_kernel.gen_kernel(func_op, EmitCContext(target="cpu"))

关联文件:
- spec: [spec/dsl/gen_kernel.md](../../../spec/dsl/gen_kernel.md)
- test: [test/dsl/test_gen_kernel.py](../../../test/dsl/test_gen_kernel.py)
- 功能实现: [kernel_gen/dsl/gen_kernel.py](../gen_kernel.py)
"""

from __future__ import annotations

from functools import lru_cache
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
import sys

_LEGACY_EMIT_C_MODULE_NAME = "".join(("kernel_gen", ".dsl.", "emit_c"))
_LEGACY_GEN_KERNEL_MODULE_NAME = "".join(("kernel_gen", ".dsl.", "_legacy_gen_kernel"))
_LEGACY_GEN_KERNEL_PATH = Path(__file__).resolve().parents[1] / "gen_kernel.py"
_LEGACY_EMIT_C_PATH = Path(__file__).resolve().parents[1] / "emit_c.py"


@lru_cache(maxsize=1)
def load_legacy_emit_c_module() -> ModuleType:
    """加载旧版片段发射模块。"""

    existing = sys.modules.get(_LEGACY_EMIT_C_MODULE_NAME)
    if existing is not None:
        return existing
    spec = spec_from_file_location(_LEGACY_EMIT_C_MODULE_NAME, _LEGACY_EMIT_C_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load legacy emit_c implementation from {_LEGACY_EMIT_C_PATH}")
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=1)
def load_legacy_gen_kernel_module() -> ModuleType:
    """加载旧版 `kernel_gen/dsl/gen_kernel.py` 模块。

    创建者: 小李飞刀
    最后一次更改: 小李飞刀

    功能说明:
    - 只在新包根需要兼容旧实现时调用。
    - 加载后的模块对象保持单例，避免重复执行旧模块初始化代码。

    使用示例:
    - legacy_gen_kernel = load_legacy_gen_kernel_module()

    关联文件:
    - spec: [spec/dsl/gen_kernel.md](../../../spec/dsl/gen_kernel.md)
    - test: [test/dsl/test_gen_kernel.py](../../../test/dsl/test_gen_kernel.py)
    - 功能实现: [kernel_gen/dsl/gen_kernel.py](../gen_kernel.py)
    """

    load_legacy_emit_c_module()
    spec = spec_from_file_location(_LEGACY_GEN_KERNEL_MODULE_NAME, _LEGACY_GEN_KERNEL_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load legacy gen_kernel implementation from {_LEGACY_GEN_KERNEL_PATH}")
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


__all__ = ["load_legacy_emit_c_module", "load_legacy_gen_kernel_module"]
