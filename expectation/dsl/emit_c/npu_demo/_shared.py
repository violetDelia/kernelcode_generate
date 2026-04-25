"""emit_c npu_demo expectation 共享 helper。

创建者: 朽木露琪亚
最后一次更改: 朽木露琪亚

功能说明:
- 为 `expectation.dsl.emit_c.npu_demo` 当前 tracked 目录入口提供共享辅助逻辑。
- 暴露 `discover_and_run_modules(...)`，用于 `cost/` 目录自动发现并串行运行 case。
- 暴露 `run_emitc_case(...)`，复用 `kernel_gen.tools.emitc_case_runner` 的通用能力，避免重复维护 IR 解析与源码断言。

使用示例:
- `discover_and_run_modules(CURRENT_DIR, "expectation.dsl.emit_c.npu_demo.cost")`
- `run_emitc_case(case_text, source_path="...", expected_snippets=["foo"])`

关联文件:
- spec: [spec/dsl/emit_c.md](spec/dsl/emit_c.md)
- test: [test/tools/test_emitc_case_runner.py](test/tools/test_emitc_case_runner.py)
- 功能实现: [expectation/dsl/emit_c/npu_demo/_shared.py](expectation/dsl/emit_c/npu_demo/_shared.py)
- 功能实现: [kernel_gen/tools/emitc_case_runner.py](kernel_gen/tools/emitc_case_runner.py)
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path

from kernel_gen.tools.emitc_case_runner import run_emitc_case


def discover_and_run_modules(current_dir: Path, package_name: str) -> None:
    """自动发现并串行运行当前目录下的 expectation 子模块。

    创建者: 朽木露琪亚
    最后一次更改: 朽木露琪亚

    功能说明:
    - 发现当前目录下全部非 `__main__.py`、非 `_*.py` 的 Python case 文件。
    - 按文件名排序后依次导入 `<package_name>.<stem>` 并执行其 `main()`。
    - 缺少 `main()` 时显式报错，避免目录入口静默跳过 case。

    使用示例:
    - `discover_and_run_modules(CURRENT_DIR, "expectation.dsl.emit_c.npu_demo.cost")`

    关联文件:
    - spec: [spec/dsl/emit_c.md](spec/dsl/emit_c.md)
    - test: [test/tools/test_emitc_case_runner.py](test/tools/test_emitc_case_runner.py)
    - 功能实现: [expectation/dsl/emit_c/npu_demo/_shared.py](expectation/dsl/emit_c/npu_demo/_shared.py)
    """

    if not current_dir.is_dir():
        raise ValueError(f"current_dir must be directory, got {current_dir}")
    if not package_name:
        raise ValueError("package_name must be non-empty")

    for path in sorted(current_dir.glob("*.py")):
        if path.name == "__main__.py" or path.stem.startswith("_"):
            continue
        module = import_module(f"{package_name}.{path.stem}")
        module_main = getattr(module, "main", None)
        if not callable(module_main):
            raise AttributeError(f"{package_name}.{path.stem} must define callable main()")
        print(f"[RUN] {path.stem}")
        module_main()


__all__ = [
    "discover_and_run_modules",
    "run_emitc_case",
]
