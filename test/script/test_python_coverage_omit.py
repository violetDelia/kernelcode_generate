"""python_coverage_omit.md tests.


功能说明:
- 校验 coverage omit 清单只收录纯转发 / 薄包装模块，并排除带有实际逻辑的入口。

关联文件:
- Spec 文档: [spec/script/python_coverage_omit.md](../../spec/script/python_coverage_omit.md)
- 功能实现: [script/check_python_coverage.py](../../script/check_python_coverage.py)
- 测试文件: [test/script/test_python_coverage_omit.py](test/script/test_python_coverage_omit.py)

使用示例:
- pytest -q test/script/test_python_coverage_omit.py
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
OMIT_MANIFEST = REPO_ROOT / "spec/script/python_coverage_omit.md"

pytestmark = pytest.mark.infra


def _manifest_text() -> str:
    """读取 coverage omit 清单文本。


    功能说明:
    - 将文档读取封装为统一入口。
    - 供清单存在性和路径命中断言复用。

    使用示例:
    - text = _manifest_text()

    关联文件:
    - Spec 文档: [spec/script/python_coverage_omit.md](../../spec/script/python_coverage_omit.md)
    - 功能实现: [script/check_python_coverage.py](../../script/check_python_coverage.py)
    - 测试文件: [test/script/test_python_coverage_omit.py](test/script/test_python_coverage_omit.py)
    """

    return OMIT_MANIFEST.read_text(encoding="utf-8")


def test_python_coverage_omit_manifest_exists_and_lists_forwarding_modules() -> None:
    """TC-COM-001: omit 清单必须存在并列出纯转发模块。"""

    text = _manifest_text()
    assert "kernel_gen/dsl/__init__.py" in text
    assert "kernel_gen/dsl/gen_kernel/emit/cpu/__init__.py" in text
    assert "kernel_gen/dsl/gen_kernel/emit/npu_demo/name.py" in text
    assert "kernel_gen/dsl/gen_kernel/emit/npu_demo/symbol/cast.py" in text
    assert "kernel_gen/dsl/gen_kernel/emit/npu_demo/symbol/const.py" in text
    assert "kernel_gen/dsl/gen_kernel/emit/npu_demo/symbol/for_loop.py" in text
    assert "kernel_gen/execute_engine/__init__.py" in text
    assert "kernel_gen/operation/__init__.py" in text
    assert "kernel_gen/operation/nn/common.py" in text
    assert "kernel_gen/passes/pipeline/__init__.py" in text
    assert "kernel_gen/symbol_variable/__init__.py" in text


def test_python_coverage_omit_manifest_excludes_logic_modules() -> None:
    """TC-COM-002: 含有逻辑或兼容副作用的入口不得加入 omit 清单。"""

    text = _manifest_text()
    assert "| `kernel_gen/core/contracts.py` |" not in text
    assert "| `kernel_gen/__init__.py` |" not in text
    assert "| `kernel_gen/dialect/__init__.py` |" not in text
    assert "| `kernel_gen/dsl/gen_kernel/__init__.py` |" not in text
    assert "| `kernel_gen/dsl/gen_kernel/emit/__init__.py` |" not in text
    assert "| `kernel_gen/passes/lowering/__init__.py` |" not in text
    assert "| `kernel_gen/dsl/ast/emit_context.py` |" not in text
    assert "| `kernel_gen/dsl/ast/emit_nn.py` |" not in text
    assert "| `kernel_gen/dsl/mlir_gen.py` |" not in text
