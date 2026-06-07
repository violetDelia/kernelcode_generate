"""KernelCodeError static gate tests.


功能说明:
- 锁定 passes / pipeline / tools 公开边界不再暴露裸 `ValueError`、`TypeError`、
  `Exception` 或 `VerifyException`。
- 锁定本轮改动测试不再用旧异常类型断言迁移路径。

使用示例:
- PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_kernel_code_error_static_gate.py

关联文件:
- 计划书: ARCHITECTURE/plan/kernel_code_error_exception_unification_green_plan.md
- 任务记录: agents/codex-multi-agents/log/task_records/2026/23/20260523-kernel-code-error-exception-unification.md
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_TARGETS = (
    REPO_ROOT / "kernel_gen/passes",
    REPO_ROOT / "kernel_gen/pipeline",
    REPO_ROOT / "kernel_gen/tools",
)
TEST_TARGETS = ("test/passes", "test/tools", "test/passes/pipeline")
BARE_EXCEPTIONS = {"Exception", "ValueError", "TypeError", "VerifyException"}
KERNEL_ERROR_CALLS = {"KernelCodeError", "kernel_code_error"}

PROTOCOL_RAISES: dict[tuple[str, str, str], str] = {
    ("kernel_gen/tools/__init__.py", "__getattr__", "AttributeError"):
        "Python module attribute protocol; not a tool runner failure",
    ("kernel_gen/tools/ircheck.py", "<module>", "SystemExit"):
        "Python CLI exit protocol; main() return code is the public CLI contract",
}

PRODUCTION_ALLOWLIST: dict[tuple[str, str, str], str] = {
    ("kernel_gen/passes/lowering/nn_lowering/matmul_img2col_lowering.py", "_coerce_symbol_expr_operand", "ValueError"):
        "numeric parse fallback to SymbolDim; no public exception crosses boundary",
    ("kernel_gen/passes/memory/memory_pool.py", "_safe_simplify_expr", "Exception"):
        "SymPy conservative simplify fallback returns original expression",
    ("kernel_gen/passes/kernel/kernel_decompose.py", "loop_body_before_fusion_blocks_initial_fill", "ValueError"):
        "index lookup miss conservatively blocks fill deletion",
    ("kernel_gen/passes/memory/memory_plan.py", "_apply_auto_pad", "TypeError"):
        "auto-pad candidate construction failure skips unsupported rewrite",
    ("kernel_gen/passes/memory/memory_plan.py", "_apply_auto_pad", "ValueError"):
        "auto-pad candidate construction failure skips unsupported rewrite",
    ("kernel_gen/passes/registry.py", "_build_registered_pass_instance", "TypeError"):
        "constructor fold keyword fallback; no public TypeError crosses boundary",
    ("kernel_gen/tools/ircheck.py", "_normalize_symbol_expr_match", "Exception"):
        "best-effort matcher canonicalization fallback returns original regex",
    ("kernel_gen/tools/ircheck.py", "run_ircheck_file", "Exception"):
        "parse/read failure maps to IrcheckResult exit_code=2",
    ("kernel_gen/tools/ircheck.py", "run_ircheck_text", "Exception"):
        "parse failure maps to IrcheckResult exit_code=2",
    ("kernel_gen/tools/ircheck.py", "_run_ircheck_case", "Exception"):
        "parse/print/compile/emitc failures map to IrcheckResult exit_code=2",
    ("kernel_gen/tools/mlir_gen_compare.py", "_mlir_gen_compare_expected_text", "Exception"):
        "invalid expected/normalization comparison returns False",
}


def _relative_path(path: Path) -> str:
    """返回仓库相对 POSIX 路径。

    功能说明:
    - 将绝对路径规整为 allowlist 使用的稳定路径。

    使用示例:
    - rel = _relative_path(path)
    """

    return path.relative_to(REPO_ROOT).as_posix()


def _attach_parents(tree: ast.AST) -> None:
    """为 AST 节点挂载父节点引用。

    功能说明:
    - 支持从 raise / except 节点反查所在函数名。

    使用示例:
    - _attach_parents(tree)
    """

    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            setattr(child, "_parent", parent)


def _enclosing_function(node: ast.AST) -> str:
    """返回节点所在函数名。

    功能说明:
    - 模块顶层节点返回 `<module>`。

    使用示例:
    - function = _enclosing_function(node)
    """

    current = getattr(node, "_parent", None)
    while current is not None:
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return current.name
        current = getattr(current, "_parent", None)
    return "<module>"


def _exception_names(node: ast.AST) -> list[str]:
    """展开 except 捕获的异常名。

    功能说明:
    - 支持 `except E`、`except module.E` 与 tuple 捕获。

    使用示例:
    - names = _exception_names(handler.type)
    """

    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.Attribute):
        return [node.attr]
    if isinstance(node, ast.Tuple):
        names: list[str] = []
        for element in node.elts:
            names.extend(_exception_names(element))
        return names
    return []


def _raised_name(exc: ast.AST) -> str | None:
    """返回 raise 表达式构造的异常名。

    功能说明:
    - 支持 `raise E(...)`、`raise module.E(...)` 与 `raise E`。

    使用示例:
    - name = _raised_name(node.exc)
    """

    if isinstance(exc, ast.Call):
        return _call_name(exc)
    if isinstance(exc, ast.Name):
        return exc.id
    return None


def _annotation_is_kernel_code_error(annotation: ast.AST | None) -> bool:
    """判断返回注解是否为 KernelCodeError。

    功能说明:
    - 支持直接名、属性名与字符串注解。

    使用示例:
    - ok = _annotation_is_kernel_code_error(function.returns)
    """

    if annotation is None:
        return False
    if isinstance(annotation, ast.Name):
        return annotation.id == "KernelCodeError"
    if isinstance(annotation, ast.Attribute):
        return annotation.attr == "KernelCodeError"
    if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
        return annotation.value == "KernelCodeError"
    return False


def _call_name(call: ast.Call) -> str | None:
    """返回调用表达式的函数名。

    功能说明:
    - 支持 `fn(...)` 与 `module.fn(...)`。

    使用示例:
    - name = _call_name(call)
    """

    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _helper_body_returns_kernel_code_error(
    name: str,
    helpers: dict[str, ast.FunctionDef | ast.AsyncFunctionDef],
    visiting: set[str],
) -> bool:
    """校验本地 helper 是否只构造 KernelCodeError。

    功能说明:
    - helper 必须标注 `-> KernelCodeError`，且 return / raise 只能构造 KCE 或调用已校验 helper。

    使用示例:
    - ok = _helper_body_returns_kernel_code_error("_fail", helpers, set())
    """

    helper = helpers.get(name)
    if helper is None or name in visiting:
        return False
    if not _annotation_is_kernel_code_error(helper.returns):
        return False
    visiting.add(name)
    ok = True
    for child in ast.walk(helper):
        if isinstance(child, ast.Return) and child.value is not None:
            if not _expression_builds_kernel_code_error(child.value, helpers, visiting):
                ok = False
                break
        if isinstance(child, ast.Raise) and child.exc is not None:
            if not _expression_builds_kernel_code_error(child.exc, helpers, visiting):
                ok = False
                break
    visiting.remove(name)
    return ok


def _expression_builds_kernel_code_error(
    expr: ast.AST,
    helpers: dict[str, ast.FunctionDef | ast.AsyncFunctionDef],
    visiting: set[str],
) -> bool:
    """判断表达式是否构造 KernelCodeError。

    功能说明:
    - 允许直接 `KernelCodeError(...)` / `kernel_code_error(...)` 或通过本地已校验 helper 构造。

    使用示例:
    - ok = _expression_builds_kernel_code_error(node.exc, helpers, set())
    """

    if isinstance(expr, ast.Call):
        name = _call_name(expr)
        if name in KERNEL_ERROR_CALLS:
            return True
        if isinstance(expr.func, ast.Name):
            return _helper_body_returns_kernel_code_error(expr.func.id, helpers, visiting)
    return False


def _handler_converts_to_kernel_code_error(
    handler: ast.ExceptHandler,
    helpers: dict[str, ast.FunctionDef | ast.AsyncFunctionDef],
) -> bool:
    """判断 except handler 是否转换为 KernelCodeError。

    功能说明:
    - handler 内必须至少存在一个显式 `raise`。
    - 每个显式 `raise` 都必须构造 `KernelCodeError` 或调用已校验 helper。
    - bare `raise`、`raise exc` 和旧异常分支都不能被同一 handler 内其它 KCE 分支掩盖。

    使用示例:
    - ok = _handler_converts_to_kernel_code_error(handler, helpers)
    """

    raises = [
        child
        for child in ast.walk(ast.Module(body=handler.body, type_ignores=[]))
        if isinstance(child, ast.Raise)
    ]
    if not raises:
        return False
    return all(
        child.exc is not None and _expression_builds_kernel_code_error(child.exc, helpers, set())
        for child in raises
    )


def _python_files(roots: tuple[Path, ...]) -> list[Path]:
    """列出目标目录下 Python 文件。

    功能说明:
    - 只返回存在目录内的 `.py` 文件。

    使用示例:
    - paths = _python_files(PRODUCTION_TARGETS)
    """

    paths: list[Path] = []
    for root in roots:
        if root.exists():
            paths.extend(root.rglob("*.py"))
    return sorted(paths)


def test_production_kernel_code_error_static_gate() -> None:
    """验证生产目标目录异常口径。

    功能说明:
    - 裸异常 raise 必须迁移；裸异常 except 必须转换为 KCE 或进入 allowlist。

    使用示例:
    - pytest -q test/tools/test_kernel_code_error_static_gate.py -k production
    """

    bad: list[tuple[str, int, str, str]] = []
    seen_allowlist_keys: set[tuple[str, str, str]] = set()
    for path in _python_files(PRODUCTION_TARGETS):
        rel_path = _relative_path(path)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel_path)
        _attach_parents(tree)
        helpers = {
            node.name: node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Raise) and node.exc is not None:
                function = _enclosing_function(node)
                name = _raised_name(node.exc)
                if name is not None and (rel_path, function, name) in PROTOCOL_RAISES:
                    continue
                if name in BARE_EXCEPTIONS:
                    bad.append((rel_path, node.lineno, f"raise {name}", "bare public exception"))
                    continue
                if isinstance(node.exc, ast.Call):
                    if not _expression_builds_kernel_code_error(node.exc, helpers, set()):
                        bad.append(
                            (
                                rel_path,
                                node.lineno,
                                f"raise {_call_name(node.exc)}",
                                "helper must build KernelCodeError directly or via validated local helper",
                            )
                        )
            if isinstance(node, ast.ExceptHandler) and node.type is not None:
                for name in _exception_names(node.type):
                    if name not in BARE_EXCEPTIONS:
                        continue
                    key = (rel_path, _enclosing_function(node), name)
                    if _handler_converts_to_kernel_code_error(node, helpers):
                        continue
                    if key in PRODUCTION_ALLOWLIST:
                        seen_allowlist_keys.add(key)
                        continue
                    bad.append((rel_path, node.lineno, f"except {name}", "missing KCE conversion or allowlist"))

    for path, function, exception in sorted(set(PRODUCTION_ALLOWLIST) - seen_allowlist_keys):
        bad.append((path, 0, f"allowlist {function}:{exception}", "entry does not match AST handler"))

    assert bad == []


def _changed_test_paths() -> list[Path]:
    """返回本轮改动测试文件。

    功能说明:
    - 同时纳入 staged、unstaged 与未跟踪测试文件，避免候选测试 diff 漏扫。

    使用示例:
    - paths = _changed_test_paths()
    """

    diff_commands = (
        ["git", "diff", "--name-only", "--", *TEST_TARGETS],
        ["git", "diff", "--cached", "--name-only", "--", *TEST_TARGETS],
        ["git", "diff", "--name-only", "HEAD", "--", *TEST_TARGETS],
    )
    diff_names: set[str] = set()
    for command in diff_commands:
        diff_result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        diff_names.update(diff_result.stdout.splitlines())
    untracked_result = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "--", *TEST_TARGETS],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    names = diff_names | set(untracked_result.stdout.splitlines())
    return sorted(REPO_ROOT / name for name in names if name.endswith(".py") and (REPO_ROOT / name).exists())


def test_handler_gate_rejects_mixed_kernel_code_error_and_bare_raise() -> None:
    """验证 handler 内混合 KCE 与旧异常分支不会假绿。

    功能说明:
    - 旧门禁只要看到任一 `KernelCodeError` 分支就放行；本用例锁定 bare raise 仍会失败。

    使用示例:
    - pytest -q test/tools/test_kernel_code_error_static_gate.py -k mixed_kernel_code_error
    """

    tree = ast.parse(
        """
from kernel_gen.core.error import ErrorKind, ErrorModule, KernelCodeError

def public_entry():
    try:
        work()
    except Exception:
        if should_wrap():
            raise KernelCodeError(ErrorKind.CONTRACT, ErrorModule.TOOLS, "wrapped")
        raise
"""
    )
    _attach_parents(tree)
    helpers = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    handler = next(node for node in ast.walk(tree) if isinstance(node, ast.ExceptHandler))

    assert _handler_converts_to_kernel_code_error(handler, helpers) is False


def _exception_name(expr: ast.AST) -> str | None:
    """返回 pytest.raises 参数异常名。

    功能说明:
    - 支持直接名与属性名。

    使用示例:
    - name = _exception_name(node.args[0])
    """

    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Attribute):
        return expr.attr
    return None


def test_changed_tests_assert_kernel_code_error_for_migrated_paths() -> None:
    """验证本轮改动测试不继续断言旧异常类型。

    功能说明:
    - 改动测试中的 `pytest.raises(ValueError/TypeError/Exception/VerifyException)` 必须迁移或显式说明。

    使用示例:
    - pytest -q test/tools/test_kernel_code_error_static_gate.py -k changed_tests
    """

    bad: list[tuple[str, int, str]] = []
    for path in _changed_test_paths():
        rel_path = _relative_path(path)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel_path)
        _attach_parents(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr != "raises":
                continue
            if not (isinstance(node.func.value, ast.Name) and node.func.value.id == "pytest"):
                continue
            if not node.args:
                continue
            exc_name = _exception_name(node.args[0])
            if exc_name in BARE_EXCEPTIONS:
                bad.append((rel_path, node.lineno, f"pytest.raises({exc_name})"))

    assert bad == []
