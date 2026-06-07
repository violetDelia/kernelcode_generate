"""Private API boundary conformance tests.

功能说明:
- 扫描全仓 tracked Python 文件，禁止跨文件导入或访问单下划线私有 API。

API 列表:
- 无业务公开 API；本文件只提供 pytest 测试入口。

使用示例:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py`

关联文件:
- spec: AGENTS.md
- plan: ARCHITECTURE/plan/private_api_boundary_static_gate_green_plan.md
"""

from __future__ import annotations

import ast
import difflib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PrivateApiViolation:
    """Describes one cross-file private API boundary violation."""

    path: str
    line: int
    kind: str
    source: str
    private_name: str

    def render(self: "PrivateApiViolation") -> str:
        """Render a stable failure line.

        功能说明:
        - 生成稳定、可排序、可定位的测试失败文本。

        使用示例:
        - PrivateApiViolation("a.py", 1, "import", "pkg._impl", "_impl").render()
        """

        return f"{self.path}:{self.line}: {self.kind}: {self.source}: {self.private_name}"


@dataclass(frozen=True)
class PrivateCallableShapeViolation:
    """Describes one private callable shape violation in the current diff."""

    path: str
    line: int
    callable_name: str
    reason: str

    def render(self: "PrivateCallableShapeViolation") -> str:
        """Render a stable private callable shape failure line.

        功能说明:
        - 生成可排序、可定位的本轮 private callable 五行与调用链失败文本。

        使用示例:
        - PrivateCallableShapeViolation("a.py", 1, "_h", "under 5 effective lines").render()
        """

        return f"{self.path}:{self.line}: {self.callable_name}: {self.reason}"


@dataclass(frozen=True)
class ModuleHelperPrefixViolation:
    """Describes one changed module-level helper missing a private prefix."""

    path: str
    line: int
    function_name: str

    def render(self: "ModuleHelperPrefixViolation") -> str:
        """Render a stable module helper prefix failure line.

        功能说明:
        - 生成可排序、可定位的本轮模块级 helper 前缀失败文本。

        使用示例:
        - ModuleHelperPrefixViolation("a.py", 1, "helper").render()
        """

        return f"{self.path}:{self.line}: {self.function_name} must be `_name` or listed as public API"


class _PrivateApiBoundaryHelpers:
    """Private helper container for this repo conformance test module."""

    @staticmethod
    def repo_root() -> Path:
        """Return the repository root used by this pytest process."""

        output = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True)
        return Path(output.strip())

    @staticmethod
    def tracked_python_files(root: Path) -> list[Path]:
        """List tracked Python files."""

        output = subprocess.check_output(["git", "ls-files", "*.py"], cwd=root, text=True)
        return [root / line for line in output.splitlines() if line and (root / line).exists()]

    @staticmethod
    def current_diff_python_files(root: Path) -> list[Path]:
        """List Python files touched by the current working diff."""

        changed = subprocess.check_output(["git", "diff", "--name-only", "HEAD"], cwd=root, text=True)
        untracked = subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard"], cwd=root, text=True)
        candidates = {line for line in changed.splitlines() if line.endswith(".py")}
        candidates.update(line for line in untracked.splitlines() if line.endswith(".py"))
        return sorted(root / line for line in candidates if (root / line).exists())

    @staticmethod
    def changed_lines_for_path(root: Path, path: Path) -> set[int]:
        """Return one-based changed lines for a Python file in the current diff."""

        relative_path = path.relative_to(root).as_posix()
        untracked = subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard", "--", relative_path],
            cwd=root,
            text=True,
        )
        if untracked.strip():
            return set(range(1, len(path.read_text(encoding="utf-8").splitlines()) + 1))
        copy_sources = _PrivateApiBoundaryHelpers.current_diff_copy_sources(root)
        if relative_path in copy_sources:
            old_text = subprocess.check_output(
                ["git", "show", f"HEAD:{copy_sources[relative_path]}"],
                cwd=root,
                text=True,
            )
            return _PrivateApiBoundaryHelpers.changed_lines_between_texts(
                old_text,
                path.read_text(encoding="utf-8"),
            )
        diff = subprocess.check_output(["git", "diff", "-U0", "HEAD", "--", relative_path], cwd=root, text=True)
        changed_lines: set[int] = set()
        for line in diff.splitlines():
            if not line.startswith("@@"):
                continue
            header = line.split("@@", maxsplit=2)[1].strip()
            new_range = header.split()[1]
            start_text, _, count_text = new_range.removeprefix("+").partition(",")
            start = int(start_text)
            count = int(count_text or "1")
            changed_lines.update(range(start, start + count))
        return changed_lines

    @staticmethod
    def current_diff_copy_sources(root: Path) -> dict[str, str]:
        """Return destination->source paths for copied or renamed files."""

        output = subprocess.check_output(
            [
                "git",
                "diff",
                "--find-copies-harder",
                "--find-renames=20%",
                "--name-status",
                "HEAD",
            ],
            cwd=root,
            text=True,
        )
        sources: dict[str, str] = {}
        for line in output.splitlines():
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            status, source, destination = parts
            if status.startswith(("C", "R")) and destination.endswith(".py"):
                sources[destination] = source
        return sources

    @staticmethod
    def changed_lines_between_texts(old_text: str, new_text: str) -> set[int]:
        """Return one-based changed lines in new_text compared with old_text."""

        old_lines = [line.rstrip() for line in old_text.splitlines()]
        new_lines = [line.rstrip() for line in new_text.splitlines()]
        changed: set[int] = set()
        matcher = difflib.SequenceMatcher(a=old_lines, b=new_lines, autojunk=False)
        for tag, _old_start, _old_end, new_start, new_end in matcher.get_opcodes():
            if tag == "equal":
                continue
            changed.update(range(new_start + 1, new_end + 1))
        return changed

    @staticmethod
    def is_private_segment(segment: str) -> bool:
        """Return whether a name segment is a single-underscore private name."""

        return segment.startswith("_") and not (segment.startswith("__") and segment.endswith("__"))

    @staticmethod
    def is_private_callable_name(name: str) -> bool:
        """Return whether a callable name is single-underscore private."""

        return _PrivateApiBoundaryHelpers.is_private_segment(name)

    @staticmethod
    def function_effective_code_lines(node: ast.FunctionDef | ast.AsyncFunctionDef, source_lines: list[str]) -> int:
        """Count physical effective code lines inside a function body."""

        body = list(node.body)
        if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant):
            if isinstance(body[0].value.value, str):
                body = body[1:]
        effective_lines: set[int] = set()
        ignored_lines = {"(", ")", "[", "]", "{", "}", ","}
        for statement in body:
            start = getattr(statement, "lineno", 0)
            end = getattr(statement, "end_lineno", start)
            for line_number in range(start, end + 1):
                if line_number < 1 or line_number > len(source_lines):
                    continue
                stripped = source_lines[line_number - 1].strip()
                if stripped and not stripped.startswith("#") and stripped not in ignored_lines:
                    effective_lines.add(line_number)
        return len(effective_lines)

    @staticmethod
    def called_private_callable_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[tuple[int, str]]:
        """Collect private callable names called inside a function body."""

        calls: list[tuple[int, str]] = []
        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue
            name: str | None = None
            if isinstance(child.func, ast.Name):
                name = child.func.id
            elif isinstance(child.func, ast.Attribute):
                name = child.func.attr
            if name is not None and _PrivateApiBoundaryHelpers.is_private_callable_name(name):
                calls.append((getattr(child, "lineno", 0), name))
        return calls

    @staticmethod
    def changed_private_callables(
        tree: ast.AST,
        changed_lines: set[int],
        source_lines: list[str],
    ) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
        """Return private callables whose definition overlaps current changed lines."""

        callables: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            if not _PrivateApiBoundaryHelpers.is_private_callable_name(node.name):
                continue
            function_lines = _PrivateApiBoundaryHelpers.function_effective_line_numbers(node, source_lines)
            function_lines.add(node.lineno)
            if function_lines & changed_lines:
                callables.append(node)
        return callables

    @staticmethod
    def function_effective_line_numbers(
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        source_lines: list[str],
    ) -> set[int]:
        """Return physical effective code lines inside a function body."""

        body = list(node.body)
        if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant):
            if isinstance(body[0].value.value, str):
                body = body[1:]
        effective_lines: set[int] = set()
        ignored_lines = {"(", ")", "[", "]", "{", "}", ","}
        for statement in body:
            start = getattr(statement, "lineno", 0)
            end = getattr(statement, "end_lineno", start)
            for line_number in range(start, end + 1):
                if line_number < 1 or line_number > len(source_lines):
                    continue
                stripped = source_lines[line_number - 1].strip()
                if stripped and not stripped.startswith("#") and stripped not in ignored_lines:
                    effective_lines.add(line_number)
        return effective_lines

    @staticmethod
    def scan_current_diff_private_callable_shapes(root: Path) -> list[PrivateCallableShapeViolation]:
        """Scan changed Python files for private callable shape violations."""

        violations: list[PrivateCallableShapeViolation] = []
        for path in _PrivateApiBoundaryHelpers.current_diff_python_files(root):
            relative_path = path.relative_to(root).as_posix()
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=path.as_posix())
            changed_lines = _PrivateApiBoundaryHelpers.changed_lines_for_path(root, path)
            source_lines = source.splitlines()
            for node in _PrivateApiBoundaryHelpers.changed_private_callables(tree, changed_lines, source_lines):
                effective_lines = _PrivateApiBoundaryHelpers.function_effective_code_lines(node, source_lines)
                if effective_lines < 5:
                    reason = f"under 5 effective code lines ({effective_lines})"
                    violations.append(PrivateCallableShapeViolation(relative_path, node.lineno, node.name, reason))
                for call_line, private_name in _PrivateApiBoundaryHelpers.called_private_callable_names(node):
                    reason = f"calls private callable {private_name}"
                    violations.append(PrivateCallableShapeViolation(relative_path, call_line, node.name, reason))
        return sorted(violations, key=lambda item: item.render())

    @staticmethod
    def module_docstring_public_api_names(tree: ast.AST) -> set[str]:
        """Return public function names listed in a module docstring API list."""

        docstring = ast.get_docstring(tree) or ""
        return set(re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)\s*\(", docstring))

    @staticmethod
    def changed_module_level_functions(
        tree: ast.AST,
        changed_lines: set[int],
    ) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
        """Return module-level functions whose definition overlaps current changed lines."""

        functions: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            function_lines = set(range(node.lineno, getattr(node, "end_lineno", node.lineno) + 1))
            if function_lines & changed_lines:
                functions.append(node)
        return functions

    @staticmethod
    def scan_current_diff_module_helper_prefixes(root: Path) -> list[ModuleHelperPrefixViolation]:
        """Scan all changed Python files for module-level helper prefix violations."""

        violations: list[ModuleHelperPrefixViolation] = []
        for path in _PrivateApiBoundaryHelpers.current_diff_python_files(root):
            relative_path = path.relative_to(root).as_posix()
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=path.as_posix())
            public_api_names = _PrivateApiBoundaryHelpers.module_docstring_public_api_names(tree)
            changed_lines = _PrivateApiBoundaryHelpers.changed_lines_for_path(root, path)
            for node in _PrivateApiBoundaryHelpers.changed_module_level_functions(tree, changed_lines):
                if node.name.startswith("_") or node.name.startswith("test") or node.name in public_api_names:
                    continue
                violations.append(ModuleHelperPrefixViolation(relative_path, node.lineno, node.name))
        return sorted(violations, key=lambda item: item.render())

    @staticmethod
    def private_segments(dotted_name: str) -> list[str]:
        """Return private segments from a dotted module or attribute path."""

        return [
            segment
            for segment in dotted_name.split(".")
            if _PrivateApiBoundaryHelpers.is_private_segment(segment)
        ]

    @staticmethod
    def attribute_chain(node: ast.AST) -> list[str] | None:
        """Return a left-to-right attribute chain for `ast.Attribute`."""

        parts: list[str] = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
            return list(reversed(parts))
        return None

    @staticmethod
    def collect_module_alias_roots(tree: ast.AST) -> set[str]:
        """Collect names that statically refer to imported modules or module-like imports."""

        roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    roots.add(alias.asname or alias.name.split(".", maxsplit=1)[0])
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    roots.add(alias.asname or alias.name)
        return roots

    @staticmethod
    def scan_tree(path: Path, repo_root: Path, tree: ast.AST) -> list[PrivateApiViolation]:
        """Scan one parsed module for cross-file private API usage."""

        relative_path = path.relative_to(repo_root).as_posix()
        violations: list[PrivateApiViolation] = []
        module_alias_roots = _PrivateApiBoundaryHelpers.collect_module_alias_roots(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for private_name in _PrivateApiBoundaryHelpers.private_segments(alias.name):
                        violations.append(
                            PrivateApiViolation(
                                relative_path,
                                node.lineno,
                                "private module import",
                                alias.name,
                                private_name,
                            )
                        )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for private_name in _PrivateApiBoundaryHelpers.private_segments(module):
                    violations.append(
                        PrivateApiViolation(relative_path, node.lineno, "private module import", module, private_name)
                    )
                for alias in node.names:
                    if _PrivateApiBoundaryHelpers.is_private_segment(alias.name):
                        source = f"{module}.{alias.name}" if module else alias.name
                        violations.append(
                            PrivateApiViolation(relative_path, node.lineno, "private name import", source, alias.name)
                        )
            elif isinstance(node, ast.Attribute):
                chain = _PrivateApiBoundaryHelpers.attribute_chain(node)
                if chain is None or chain[0] not in module_alias_roots:
                    continue
                for private_name in [
                    segment for segment in chain[1:] if _PrivateApiBoundaryHelpers.is_private_segment(segment)
                ]:
                    violations.append(
                        PrivateApiViolation(
                            relative_path,
                            node.lineno,
                            "module alias private attr",
                            ".".join(chain),
                            private_name,
                        )
                    )
        return violations

    @staticmethod
    def scan_private_api_boundaries(root: Path) -> list[PrivateApiViolation]:
        """Scan all tracked Python files for private API boundary violations."""

        violations: list[PrivateApiViolation] = []
        for path in _PrivateApiBoundaryHelpers.tracked_python_files(root):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
            except SyntaxError as exc:
                violations.append(
                    PrivateApiViolation(
                        path.relative_to(root).as_posix(),
                        exc.lineno or 0,
                        "syntax error",
                        exc.msg,
                        "syntax-error",
                    )
                )
                continue
            violations.extend(_PrivateApiBoundaryHelpers.scan_tree(path, root, tree))
        return sorted(violations, key=lambda item: item.render())


def testtracked_python_files_do_not_cross_private_api_boundaries() -> None:
    """Assert tracked Python files do not cross private API boundaries.

    功能说明:
    - 锁定 `AGENTS.md` 约束：当前文件之外不得导入或访问单下划线私有 API。
    - 同文件 `_helper`、类内 `_method` 与 `self._state` 不属于跨文件 API，本测试不禁止。

    使用示例:
    - pytest.main(["test/repo_conformance/test_private_api_boundaries.py"])
    """

    root = _PrivateApiBoundaryHelpers.repo_root()
    violations = _PrivateApiBoundaryHelpers.scan_private_api_boundaries(root)
    assert not violations, "cross-file private API violations:\n" + "\n".join(
        violation.render() for violation in violations
    )


def testcurrent_diff_private_callables_are_not_shallow_or_chained() -> None:
    """Assert changed private callables satisfy current repository shape rules.

    功能说明:
    - 锁定本轮新增/改动 private callable 不少于五行有效代码。
    - 锁定 private callable 不能调用 private callable。

    使用示例:
    - pytest.main(["test/repo_conformance/test_private_api_boundaries.py"])
    """

    root = _PrivateApiBoundaryHelpers.repo_root()
    violations = _PrivateApiBoundaryHelpers.scan_current_diff_private_callable_shapes(root)
    assert not violations, "current diff private callable shape violations:\n" + "\n".join(
        violation.render() for violation in violations
    )


def testcurrent_diff_module_helpers_use_private_prefix_or_public_api() -> None:
    """Assert changed module-level helpers use `_name` unless listed public.

    功能说明:
    - 锁定当前 diff 中未列 API 的本地 helper 不得以公开形态落在模块顶层。
    - 已列入文件级 API 列表的公开函数不受本规则约束。

    使用示例:
    - pytest.main(["test/repo_conformance/test_private_api_boundaries.py"])
    """

    root = _PrivateApiBoundaryHelpers.repo_root()
    violations = _PrivateApiBoundaryHelpers.scan_current_diff_module_helper_prefixes(root)
    assert not violations, "current diff module helper prefix violations:\n" + "\n".join(
        violation.render() for violation in violations
    )


def testcuda_sm86_final_ir_builder_stays_package_local_by_text() -> None:
    """Assert CUDA SM86 final IR builder is not re-exported.

    功能说明:
    - 只读取 CUDA emit package 文件和 AST，不 import / direct call package-local helper。
    - 锁定 final IR SourceBundle builder 存在、root `__all__` 为空、旧 source-selection helper 文件退场。

    使用示例:
    - pytest.main(["test/repo_conformance/test_private_api_boundaries.py", "-k", "cuda_sm86_final_ir_builder"])
    """

    root = _PrivateApiBoundaryHelpers.repo_root()
    package_root = root / "kernel_gen" / "dsl" / "gen_kernel" / "emit" / "cuda_sm86"
    source_bundle_tree = ast.parse((package_root / "source_bundle.py").read_text(encoding="utf-8"))
    public_classes = {node.name for node in ast.walk(source_bundle_tree) if isinstance(node, ast.ClassDef)}
    public_functions = {node.name for node in ast.walk(source_bundle_tree) if isinstance(node, ast.FunctionDef)}
    old_tokens = (
        "CudaSm86" + "ModuleSummary",
        "detect_cuda_sm86_" + "kernel_family",
        "summarize_cuda_sm86_" + "module",
        "emit_" + "matmul_source",
        "emit_" + "conv2d_source",
        "emit_" + "flash_attention_source",
    )

    assert "CudaSm86SourceBuilder" in public_classes
    assert "CudaSm86IrTrace" in public_classes
    assert "build_cuda_sm86_source_bundle" in public_functions
    assert not (package_root / "detect.py").exists()
    init_text = (package_root / "__init__.py").read_text(encoding="utf-8")
    assert "__all__: list[str] = []" in init_text
    for path in package_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in old_tokens:
            assert token not in text, (path, token)
