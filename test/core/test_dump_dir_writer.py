"""DumpDirWriter tests.


功能说明:
- 覆盖 `kernel_gen.core.tools.dump_dir.DumpDirWriter` 的公开构造、配置读取、文本写出、阶段文件名和安全路径拒绝行为。

使用示例:
- pytest -q test/core/test_dump_dir_writer.py

关联文件:
- spec: [spec/core/tools/dump_dir.md](../../spec/core/tools/dump_dir.md)
- 功能实现: [kernel_gen/core/tools/dump_dir/writer.py](../../kernel_gen/core/tools/dump_dir/writer.py)
- test: [test/core/test_dump_dir_writer.py](test_dump_dir_writer.py)
"""

from __future__ import annotations

from pathlib import Path

import pytest
from xdsl.dialects.builtin import ModuleOp

from kernel_gen.core.config import reset_config, set_dump_dir
from kernel_gen.core.tools.dump_dir import DumpDirWriter


@pytest.fixture(autouse=True)
def _isolated_config() -> None:
    """隔离 core config。


    功能说明:
    - 每个用例前后重置公开配置，避免 dump_dir 串扰。

    使用示例:
    - pytest 自动应用。
    """

    reset_config()
    try:
        yield
    finally:
        reset_config()


def test_dump_dir_writer_from_config(tmp_path: Path) -> None:
    set_dump_dir(None)
    assert DumpDirWriter.from_config() is None

    set_dump_dir(tmp_path)
    writer = DumpDirWriter.from_config()

    assert writer is not None
    assert writer.root == tmp_path


def test_dump_dir_writer_writes_text_and_stage_marker(tmp_path: Path) -> None:
    writer = DumpDirWriter(tmp_path).child("bad name!", fallback="kernel")

    text_path = writer.write("source.cpp", "int main() {}")
    stage_path = writer.write_stage(2, "tile analysis", "builtin.module {}", marker="tile-analysis{fold=true}")

    assert text_path == tmp_path / "bad_name_" / "source.cpp"
    assert text_path.read_text(encoding="utf-8") == "int main() {}\n"
    assert stage_path == tmp_path / "bad_name_" / "02-tile_analysis.mlir"
    assert stage_path.read_text(encoding="utf-8") == "tile-analysis{fold=true}\nbuiltin.module {}\n"


def test_dump_dir_writer_writes_operation_alias_text(tmp_path: Path) -> None:
    writer = DumpDirWriter(tmp_path)

    path = writer.write("module.mlir", ModuleOp([]))

    text = path.read_text(encoding="utf-8")
    assert "builtin.module" in text
    assert text.endswith("\n")


@pytest.mark.parametrize(
    ("name", "fallback", "expected_dir"),
    (
        (".", "kernel", "kernel"),
        ("..", "kernel", "kernel"),
        ("", "..", "dump"),
        ("..", "..", "dump"),
    ),
)
def test_dump_dir_writer_child_dot_segments_fall_back_inside_root(
    name: str,
    fallback: str,
    expected_dir: str,
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    writer = DumpDirWriter(root).child(name, fallback=fallback)

    path = writer.write("safe.txt", "x")

    assert writer.root == root / expected_dir
    assert path == root / expected_dir / "safe.txt"
    assert path.read_text(encoding="utf-8") == "x\n"
    assert not (tmp_path / "safe.txt").exists()


def test_dump_dir_writer_child_rejects_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / "escape").symlink_to(outside, target_is_directory=True)
    writer = DumpDirWriter(root)

    with pytest.raises(ValueError):
        writer.child("escape")

    assert not (outside / "safe.txt").exists()


def test_dump_dir_writer_rejects_invalid_content(tmp_path: Path) -> None:
    writer = DumpDirWriter(tmp_path)

    with pytest.raises(ValueError):
        writer.write("bad.txt", object())  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "name",
    (
        "",
        "/abs.cpp",
        "a//b.cpp",
        "a/./b.cpp",
        "a/../b.cpp",
        ".",
        "..",
        "bad\\path.cpp",
        "bad\x00path.cpp",
    ),
)
def test_dump_dir_writer_rejects_unsafe_paths(name: str, tmp_path: Path) -> None:
    writer = DumpDirWriter(tmp_path)

    with pytest.raises(ValueError):
        writer.write(name, "x")


def test_dump_dir_writer_rejects_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / "escape").symlink_to(outside, target_is_directory=True)
    writer = DumpDirWriter(root)

    with pytest.raises(ValueError):
        writer.write("escape/file.cpp", "x")

    assert not (outside / "file.cpp").exists()


@pytest.mark.parametrize("index", (-1, True, 1.5))
def test_dump_dir_writer_rejects_invalid_stage_index(index: object, tmp_path: Path) -> None:
    writer = DumpDirWriter(tmp_path)

    with pytest.raises(ValueError):
        writer.write_stage(index, "stage", "x")  # type: ignore[arg-type]


@pytest.mark.parametrize("suffix", ("", ".", "..", "mlir", "bad/name", "bad\\name", "bad\x00name"))
def test_dump_dir_writer_rejects_invalid_stage_suffix(suffix: str, tmp_path: Path) -> None:
    writer = DumpDirWriter(tmp_path)

    with pytest.raises(ValueError):
        writer.write_stage(1, "stage", "x", suffix=suffix)
