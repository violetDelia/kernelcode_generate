# core/tools/dump_dir

## 功能简介

- 定义 Python 侧诊断 dump 文本产物的统一写出器。
- `DumpDirWriter` 只负责 dump 根目录派生、安全相对路径校验、文本格式化与 UTF-8 写出。
- 不提供 bytes/binary 写入能力，不公开 sanitize、write_text、format、pass_label 或按路径裸分配的散装 API。
- xDSL `ModuleOp | Operation` 内容必须使用 `kernel_gen.core.print.print_operation_with_aliases(...)` 的 alias 文本写入。

## API 列表

- `class DumpDirWriter(root: Path)`
- `DumpDirWriter.from_config() -> DumpDirWriter | None`
- `DumpDirWriter.child(self: DumpDirWriter, name: str, fallback: str = "dump") -> DumpDirWriter`
- `DumpDirWriter.write(self: DumpDirWriter, name: str, content: ModuleOp | Operation | str, *, marker: str | None = None) -> Path`
- `DumpDirWriter.write_stage(self: DumpDirWriter, index: int, name: str, content: ModuleOp | Operation | str, *, marker: str | None = None, suffix: str = ".mlir", fallback: str = "stage") -> Path`

## 文档信息

- 创建者：`咯咯咯`
- 最后一次更改：`咯咯咯`
- `spec`：[`spec/core/tools/dump_dir.md`](dump_dir.md)
- `test`：[`test/core/test_dump_dir_writer.py`](../../../test/core/test_dump_dir_writer.py)
- `功能实现`：[`kernel_gen/core/tools/dump_dir/writer.py`](../../../kernel_gen/core/tools/dump_dir/writer.py)

## 依赖

- [`spec/core/config.md`](../config.md)：`DumpDirWriter.from_config()` 的 dump 根目录来源。
- [`spec/core/print.md`](../print.md)：xDSL operation dump 的 alias IR 文本来源。

## API详细说明

### `class DumpDirWriter(root: Path)`

- api：`class DumpDirWriter(root: Path)`
- 参数：
  - `root`：dump 根目录；类型 `Path`；无默认值，调用方必须显式提供。
- 返回值：构造成功后返回 writer 实例。
- 使用示例：

  ```python
  from pathlib import Path
  from kernel_gen.core.tools.dump_dir import DumpDirWriter

  writer = DumpDirWriter(Path("dump/kernel"))
  ```
- 功能说明：保存一个 dump 根目录，并基于该根目录派生子目录或写入文本文件。
- 注意事项：该类不修改全局配置；不提供二进制写入接口；写入操作必须通过本文件列出的公开方法完成。

### `DumpDirWriter.from_config() -> DumpDirWriter | None`

- api：`DumpDirWriter.from_config() -> DumpDirWriter | None`
- 参数：无。
- 返回值：`DumpDirWriter | None`。
- 使用示例：

  ```python
  writer = DumpDirWriter.from_config()
  if writer is not None:
      writer.write("source.cpp", source)
  ```
- 功能说明：从 `kernel_gen.core.config.get_dump_dir()` 读取当前 dump 根目录；未启用 dump 时返回 `None`。
- 注意事项：只读取公开 config API，不修改配置。

### `DumpDirWriter.child(self: DumpDirWriter, name: str, fallback: str = "dump") -> DumpDirWriter`

- api：`DumpDirWriter.child(self: DumpDirWriter, name: str, fallback: str = "dump") -> DumpDirWriter`
- 参数：
  - `name`：展示性子目录名；类型 `str`；无默认值。
  - `fallback`：`name` 规整为空时使用的替代名；类型 `str`；默认值 `"dump"`。
- 返回值：以 `root/<safe-name>` 为根目录的新 `DumpDirWriter`；规整结果为 `.` / `..` 时使用安全 fallback。
- 使用示例：

  ```python
  kernel_writer = writer.child("add_kernel", fallback="kernel")
  ```
- 功能说明：把单个展示性名称规整为安全路径片段，并派生子 writer。
- 注意事项：该方法只处理单级目录名；多级 artifact 路径应交给 `write(...)` 的安全相对路径校验；派生目录不得通过 `.`、`..` 或已存在 symlink 逃逸当前 root。

### `DumpDirWriter.write(self: DumpDirWriter, name: str, content: ModuleOp | Operation | str, *, marker: str | None = None) -> Path`

- api：`DumpDirWriter.write(self: DumpDirWriter, name: str, content: ModuleOp | Operation | str, *, marker: str | None = None) -> Path`
- 参数：
  - `name`：相对 dump 根目录的文件路径；类型 `str`；无默认值。
  - `content`：待写入文本或 xDSL operation；类型 `ModuleOp | Operation | str`；无默认值。
  - `marker`：可选首行 marker；类型 `str | None`；默认值 `None`。
- 返回值：实际写入的 `Path`。
- 使用示例：

  ```python
  path = writer.write("source.cpp", "int main() {}")
  ```
- 功能说明：写入 UTF-8 文本文件，自动创建父目录，内容保证以换行结束。
- 注意事项：`name` 必须是安全相对路径；拒绝绝对路径、空 segment、`.`、`..`、反斜杠、NUL 与已存在 symlink 逃逸。

### `DumpDirWriter.write_stage(self: DumpDirWriter, index: int, name: str, content: ModuleOp | Operation | str, *, marker: str | None = None, suffix: str = ".mlir", fallback: str = "stage") -> Path`

- api：`DumpDirWriter.write_stage(self: DumpDirWriter, index: int, name: str, content: ModuleOp | Operation | str, *, marker: str | None = None, suffix: str = ".mlir", fallback: str = "stage") -> Path`
- 参数：
  - `index`：阶段序号；类型 `int`；无默认值。
  - `name`：展示性阶段名；类型 `str`；无默认值。
  - `content`：待写入文本或 xDSL operation；类型 `ModuleOp | Operation | str`；无默认值。
  - `marker`：可选首行 marker；类型 `str | None`；默认值 `None`。
  - `suffix`：文件后缀；类型 `str`；默认值 `".mlir"`。
  - `fallback`：阶段名规整为空时使用的替代名；类型 `str`；默认值 `"stage"`。
- 返回值：实际写入的 `Path`。
- 使用示例：

  ```python
  writer.write_stage(2, "canonicalize", module, marker="canonicalize")
  ```
- 功能说明：按 `NN-<safe-name><suffix>` 生成阶段 dump 文件名，并委托 `write(...)` 完成写出。
- 注意事项：`suffix` 必须是以 `.` 开头的单个文件名片段；`marker` 只进入文件内容第一行，不参与文件名。

## 测试矩阵

| ID | 类型 | 场景 | 准备 | 步骤 | 期望 | 覆盖测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-CORE-DUMP-DIR-001 | 配置 | from_config | 设置/清空 `dump_dir`。 | 调用 `DumpDirWriter.from_config()`。 | 关闭时返回 `None`，开启时 root 与配置一致。 | `test_dump_dir_writer_from_config` |
| TC-CORE-DUMP-DIR-002 | 写出 | 文本和阶段 dump | 创建临时 dump 根目录。 | 调用 `write(...)` 与 `write_stage(...)`。 | 文件名、首行 marker 与最终换行稳定。 | `test_dump_dir_writer_writes_text_and_stage_marker` |
| TC-CORE-DUMP-DIR-003 | 写出 | xDSL operation | 构造 `ModuleOp`。 | 调用 `write(...)`。 | 写入 alias IR 文本。 | `test_dump_dir_writer_writes_operation_alias_text` |
| TC-CORE-DUMP-DIR-004 | 边界 | 非安全路径 | 准备非法相对路径与 symlink 逃逸。 | 调用 `write(...)`。 | 稳定抛出 `ValueError` 且不写出逃逸文件。 | `test_dump_dir_writer_rejects_unsafe_paths` / `test_dump_dir_writer_rejects_symlink_escape` |
| TC-CORE-DUMP-DIR-005 | 边界 | child 派生安全 | 准备 `child(".")`、`child("..")`、`fallback=".."` 与 child symlink 逃逸。 | 调用 `child(...)` 后写出或直接派生。 | `.` / `..` 回退到 root 内安全目录，symlink 逃逸稳定抛出 `ValueError`。 | `test_dump_dir_writer_child_dot_segments_fall_back_inside_root` / `test_dump_dir_writer_child_rejects_symlink_escape` |
| TC-CORE-DUMP-DIR-006 | 边界 | 非法 stage 参数 | 准备非法 index/suffix。 | 调用 `write_stage(...)`。 | 稳定抛出 `ValueError`。 | `test_dump_dir_writer_rejects_invalid_stage_index` / `test_dump_dir_writer_rejects_invalid_stage_suffix` |
