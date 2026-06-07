"""Dump directory writer public entry.


功能说明:
- 提供 `DumpDirWriter` 作为 Python 侧诊断文本产物的统一写出入口。
- 包根只公开计划定义的 writer 类，不额外转发内部 helper。

API 列表:
- `class DumpDirWriter(root: Path)`
- `DumpDirWriter.from_config() -> DumpDirWriter | None`
- `DumpDirWriter.child(self: DumpDirWriter, name: str, fallback: str = "dump") -> DumpDirWriter`
- `DumpDirWriter.write(self: DumpDirWriter, name: str, content: ModuleOp | Operation | str, *, marker: str | None = None) -> Path`
- `DumpDirWriter.write_stage(self: DumpDirWriter, index: int, name: str, content: ModuleOp | Operation | str, *, marker: str | None = None, suffix: str = ".mlir", fallback: str = "stage") -> Path`

使用示例:
- writer = DumpDirWriter(Path("dump"))
- writer.write("source.cpp", "int main() {}")

关联文件:
- spec: [spec/core/tools/dump_dir.md](../../../../spec/core/tools/dump_dir.md)
- test: [test/core/test_dump_dir_writer.py](../../../../test/core/test_dump_dir_writer.py)
- 功能实现: [kernel_gen/core/tools/dump_dir/writer.py](writer.py)
"""

from __future__ import annotations

from .writer import DumpDirWriter

__all__ = ["DumpDirWriter"]
