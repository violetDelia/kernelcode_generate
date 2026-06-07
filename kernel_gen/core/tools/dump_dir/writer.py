"""Dump directory writer implementation.


功能说明:
- 集中管理 Python 侧诊断 dump 文本产物的目录派生、文件名规整、文本格式化和写出。
- 只写入 UTF-8 文本；不提供 bytes、binary、路径分配或散装 sanitize/write_text API。
- 使用 `kernel_gen.core.print.print_operation_with_aliases(...)` 渲染 xDSL operation，保持现有 IR dump alias 文本。
- 写出相对路径时拒绝绝对路径、空 segment、`.`、`..`、反斜杠、NUL 与已存在 symlink 逃逸。

API 列表:
- `class DumpDirWriter(root: Path)`
- `DumpDirWriter.from_config() -> DumpDirWriter | None`
- `DumpDirWriter.child(self: DumpDirWriter, name: str, fallback: str = "dump") -> DumpDirWriter`
- `DumpDirWriter.write(self: DumpDirWriter, name: str, content: ModuleOp | Operation | str, *, marker: str | None = None) -> Path`
- `DumpDirWriter.write_stage(self: DumpDirWriter, index: int, name: str, content: ModuleOp | Operation | str, *, marker: str | None = None, suffix: str = ".mlir", fallback: str = "stage") -> Path`

使用示例:
- writer = DumpDirWriter(Path("dump/kernel"))
- writer.write("01-first-ir.mlir", module_op)
- writer.write_stage(2, "tile-analysis", module_op, marker="tile-analysis{fold=true}")

关联文件:
- spec: [spec/core/tools/dump_dir.md](../../../../spec/core/tools/dump_dir.md)
- test: [test/core/test_dump_dir_writer.py](../../../../test/core/test_dump_dir_writer.py)
- 功能实现: [kernel_gen/core/tools/dump_dir/writer.py](writer.py)
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re

from xdsl.dialects.builtin import ModuleOp
from xdsl.ir import Operation

from kernel_gen.core.config import get_dump_dir
from kernel_gen.core.print import print_operation_with_aliases

DumpContent = ModuleOp | Operation | str
_SAFE_COMPONENT_PATTERN = re.compile(r"[^A-Za-z0-9_.-]+")


@dataclass(frozen=True)
class DumpDirWriter:
    """诊断 dump 文本写出器。


    功能说明:
    - 保存一个 dump 根目录，并提供有限的目录派生和文本写出方法。
    - 不改变全局配置，不持有打开文件句柄。

    使用示例:
    - writer = DumpDirWriter(Path("dump"))
    - writer.write("source.cpp", "int main() {}")
    """

    root: Path

    def __post_init__(self: "DumpDirWriter") -> None:
        """规整根目录类型。


        功能说明:
        - 将传入 root 转为 `Path`，便于调用方传入 PathLike 对象时保持同一内部表示。

        使用示例:
        - writer = DumpDirWriter(Path("dump"))
        """

        object.__setattr__(self, "root", Path(self.root))

    @classmethod
    def from_config(cls: type["DumpDirWriter"]) -> "DumpDirWriter | None":
        """从公开 core config 构造 writer。


        功能说明:
        - `get_dump_dir() is None` 时返回 `None`，表示诊断落盘关闭。
        - 非空时返回以当前 dump 目录为根的 writer。

        使用示例:
        - writer = DumpDirWriter.from_config()
        """

        dump_dir = get_dump_dir()
        if dump_dir is None:
            return None
        return cls(dump_dir)

    def child(self: "DumpDirWriter", name: str, fallback: str = "dump") -> "DumpDirWriter":
        """派生一个安全子目录 writer。


        功能说明:
        - 对单个路径片段做文件名规整，不接受多级路径、`.` 或 `..`。
        - 用于 kernel 名、pass 名等展示性目录分配。

        使用示例:
        - kernel_writer = writer.child("add_kernel", fallback="kernel")
        """

        if not isinstance(name, str) or not isinstance(fallback, str):
            raise ValueError("dump path component must be str")
        fallback_name = _SAFE_COMPONENT_PATTERN.sub("_", fallback.strip()) or "dump"
        if fallback_name in {".", ".."}:
            fallback_name = "dump"
        safe_name = _SAFE_COMPONENT_PATTERN.sub("_", name.strip()) or fallback_name
        if safe_name in {".", ".."}:
            safe_name = fallback_name
        root_path = Path(self.root)
        child_root = root_path / safe_name
        root_resolved = root_path.resolve(strict=False)
        child_resolved = child_root.resolve(strict=False)
        if os.path.commonpath((str(root_resolved), str(child_resolved))) != str(root_resolved):
            raise ValueError("dump child path escapes root")
        return DumpDirWriter(child_root)

    def write(
        self: "DumpDirWriter",
        name: str,
        content: DumpContent,
        *,
        marker: str | None = None,
    ) -> Path:
        """写入单个文本 dump 文件。


        功能说明:
        - `name` 必须是安全相对路径，可包含 POSIX 子目录。
        - 自动创建父目录，内容统一以换行结束。
        - 返回实际写入路径。

        使用示例:
        - path = writer.write("source.cpp", source)
        """

        if not isinstance(name, str):
            raise ValueError("dump path must be str")
        if not name or name.startswith("/") or "\\" in name or "\x00" in name:
            raise ValueError("dump path must be a safe relative path")
        relative_path = Path(name)
        if relative_path.is_absolute():
            raise ValueError("dump path must be a safe relative path")
        parts = tuple(name.split("/"))
        if any(part in {"", ".", ".."} for part in parts):
            raise ValueError("dump path must be a safe relative path")

        root_path = Path(self.root)
        target = root_path.joinpath(*parts)
        root_resolved = root_path.resolve(strict=False)
        target_resolved = target.resolve(strict=False)
        if os.path.commonpath((str(root_resolved), str(target_resolved))) != str(root_resolved):
            raise ValueError("dump path escapes root")

        if isinstance(content, str):
            body = content
        elif isinstance(content, (ModuleOp, Operation)):
            body = print_operation_with_aliases(content).rstrip()
        else:
            raise ValueError("dump content must be str or xDSL operation")
        if marker is not None:
            if not isinstance(marker, str):
                raise ValueError("dump marker must be str or None")
            body = f"{marker}\n{body}"
        text = body if body.endswith("\n") else f"{body}\n"

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def write_stage(
        self: "DumpDirWriter",
        index: int,
        name: str,
        content: DumpContent,
        *,
        marker: str | None = None,
        suffix: str = ".mlir",
        fallback: str = "stage",
    ) -> Path:
        """按 `NN-name.suffix` 形式写入阶段 dump。


        功能说明:
        - 对展示性阶段名做文件名规整，保持 pass/pipeline dump 文件名稳定。
        - marker 仍通过 `write(...)` 写入第一行，不参与文件名。

        使用示例:
        - path = writer.write_stage(2, "canonicalize", module_op, marker="canonicalize")
        """

        if not isinstance(index, int) or isinstance(index, bool) or index < 0:
            raise ValueError("dump stage index must be a non-negative int")
        if (
            not isinstance(suffix, str)
            or not suffix.startswith(".")
            or suffix in {".", ".."}
            or "/" in suffix
            or "\\" in suffix
            or "\x00" in suffix
        ):
            raise ValueError("dump stage suffix must be a safe extension")
        if not isinstance(name, str) or not isinstance(fallback, str):
            raise ValueError("dump path component must be str")
        fallback_name = _SAFE_COMPONENT_PATTERN.sub("_", fallback.strip()) or "dump"
        safe_name = _SAFE_COMPONENT_PATTERN.sub("_", name.strip()) or fallback_name
        return self.write(f"{index:02d}-{safe_name}{suffix}", content, marker=marker)


__all__ = ["DumpDirWriter"]
