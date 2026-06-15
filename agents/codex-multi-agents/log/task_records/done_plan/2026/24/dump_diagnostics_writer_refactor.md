# dump_dir diagnostics writer refactor 计划书 Draft 3-R5-R1

## 文档信息

- 计划用途：把当前分散在 `PassManager`、`dsl_run`、`ircheck`、`gen_kernel`、emit backend 与 execute_engine builtin strategy 中的 dump / diagnostics 生成物写出和 dump 派生路径分配能力收敛到 `kernel_gen/core/tools/dump_dir/`，减少重复路径处理、换行处理、IR 格式化和安全写入逻辑。
- 当前状态：Draft 3-R5-R1，已吸收两路 subagent strict review 对 API 确认、依赖硬门禁、S5 范围、任务卡、敏感门禁，以及 Draft 3 / Draft 3-R2 / Draft 3-R3 / Draft 3-R4 复审对 builtin/cuda_sm86 写出路径、suffix 安全、计划文件 hash 门禁、S6 `dsl_cost_run` 全链路验收覆盖、`spec/tools/dsl_cost_run.md` 同步和 spec-only 验收可信度的最小需改项；DU1 已获用户确认，DU2 已按用户“dump 统一管理所有生成物”确认纳入全部当前 Python 侧 dump 生成物写出 / 路径分配；Kierkegaard / Ptolemy 两路 Draft 3-R5 strict review 均已通过且无阻断、无最小需改项、无待确认项；`守护最好的爱莉希雅` 已在 `talk.log:11923` 对 Draft 3-R5-R1 执行守护最终检验并通过，允许管理员创建唯一计划级 `execute`。
- 用户确认来源：
  - 2026-06-07 用户指出：dump 文件虽然打印 pass 名字，但没有打印 pass 选项，因此很难判断 IR 是否正确。
  - 2026-06-07 用户要求先查看整体代码结构并列出可重构点。
  - 2026-06-07 用户要求展开“统一 dump / diagnostics 写出层”，并要求给出当前代码现状、代码示例和预期改法。
  - 2026-06-07 用户认为草稿暴露接口偏多，要求接口更少。
  - 2026-06-07 用户确认实现文件落点为 `core/tools/dump_dir`。
- 2026-06-07 用户确认“按照计划书的流程进行推进”。
- 2026-06-07 用户回复“可以 2 我没理解”，按上下文记录为 DU1 `DumpDirWriter` 完整 API 可接受；当时 DU2 仍需解释。
- 2026-06-07 用户明确：“我觉得应该由dump 统一管理所有的生成物”，按上下文记录为 DU2 选择纳入 `gen_kernel` / SourceBundle / emit backend source artifact 迁移。
- 2026-06-07 用户再次强调：“我觉得应该由dump 统一管理所有的生成物”，按上下文记录为 DU2-R2：本计划完成态必须覆盖所有当前 Python 侧 dump 生成物写出与 dump 派生路径分配，不允许只迁移 MLIR dump。
- 计划文件位置：`ARCHITECTURE/plan/dump_diagnostics_writer_refactor.md`。
- 主仓 index 边界：当前计划草案不长期暂存到主仓 index；如守护最终检验需要 index/blob 证据，应按管理员口径使用独立计划 / 守护 worktree 或短生命周期证据，不把主仓 index 当作长期计划暂存区。

## 用户确认项

### DU1：是否确认 `DumpDirWriter` 完整 API

结论：已确认。

确认来源：2026-06-07 用户回复“可以 2 我没理解”，其中“可以”按上下文对应 DU1。

请用户确认是否允许本计划新增以下仓库内部共享 API：

```python
from kernel_gen.core.tools.dump_dir import DumpDirWriter

@dataclass(frozen=True)
class DumpDirWriter:
    root: Path

    @classmethod
    def from_config(cls) -> "DumpDirWriter | None":
        ...

    def child(self, name: str, fallback: str = "dump") -> "DumpDirWriter":
        ...

    def write(self, name: str, content: ModuleOp | Operation | str, *, marker: str | None = None) -> Path:
        ...

    def write_stage(
        self,
        index: int,
        name: str,
        content: ModuleOp | Operation | str,
        *,
        marker: str | None = None,
        suffix: str = ".mlir",
        fallback: str = "stage",
    ) -> Path:
        ...
```

- 推荐结论：确认。
- 原因：这是最小可复用面；不暴露 sanitize、文本写出、IR 格式化或 pass 专用 helper。
- 若后续用户撤回确认：计划需退回重新设计 API，不得下发。

### DU2：S5 是否纳入所有 dump 生成物迁移

结论：已确认纳入，不排除。

确认来源：2026-06-07 用户两次明确“我觉得应该由dump 统一管理所有的生成物”。

本计划纳入：

- `gen_kernel(...)` 的 `source.cpp` 写出。
- SourceBundle artifact 写出，例如 `kernel.cu`、`include/kernel.h`。
- emit backend / dummy compile strategy 的 `source.cpp`、SourceBundle artifact 与当前文本型 compile product 写出。
- execute engine builtin strategy 的工作目录生成物路径与当前 Python 主动写出的文本 / dry-run 占位产物，包括 `kernel.cpp`、dry-run `libkernel.so`、CUDA SM86 SourceBundle `.cu/.cuh` artifact 和 `source.cpp` aggregate。
- `dsl_run(...)` 与 `dsl_cost_run(...)` 写出的 kernel 级 dump、`source.cpp` 和 `99-cost-source.cpp`。
- `ircheck -irdump` 写出的 `.irdump/<case>/` input、step、失败前 IR 与 emitc `.c`。
- runtime trance 的 `dump_dir/<kernel>/trance` 路径分配。

边界：

- SourceBundle 解析仍由领域模块负责，dump writer 统一管理最终落盘、父目录创建、换行补齐、安全相对路径和 symlink 逃逸拒绝。
- `DumpDirWriter.write(name, ...)` 的 `name` 允许安全相对路径，如 `include/kernel.h`；必须拒绝绝对路径、`.`、`..`、空 segment、反斜杠、NUL 与已存在 symlink 逃逸。
- `dsl_cost_run(...)` 的 `99-cost-source.cpp` 也属于 dump 生成物，必须纳入 `DumpDirWriter`。
- runtime trance 的 `dump_dir/<kernel>/trance` 目录路径也属于 dump 派生路径分配，必须通过 `DumpDirWriter.child(...).child("trance")` 或等价 writer 语义生成。
- 凡调用方本身没有写文件、只是把真实编译器输出路径传给外部命令，也必须由 `DumpDirWriter` 统一分配该输出路径；真实二进制字节仍由外部命令写入。
- 本轮不新增 bytes / binary writer API；当前迁移范围内的生成物按现有文本写出和路径分配语义收敛。真实编译器产出的二进制仍由编译命令写入 `DumpDirWriter` 管理 / 分配的输出路径；若 execute 发现必须让 dump writer 直接写 bytes 才能完成迁移，必须暂停并回报用户确认。

## 与现有任务关系

- `T-20260607-2b00a1ea / pass_dump_xdsl_pipeline_spec_options` 当前仍在 `execute / 进行中`，其目标是让 pass dump marker 使用 xDSL `pipeline_pass_spec(include_default=True)` 并完成 pass dataclass 参数模型迁移。
- 本计划不重复承担 pass option 打印语义，不重新决策 `fold`、`None` option、registry spelling 或 pass dataclass 迁移。
- `T-20260607-2b00a1ea` 未归档 / 未合并前，本计划不得并行 execute；管理员不得仅通过“列依赖”绕过该前置。该任务归档并同步 latest main 后，本计划 execute 才能开始。
- 本计划可在 pass option 语义完成后做写出层收敛：`PassManager` 仍负责生成 pass marker，`dump_dir` writer 只负责安全路径、文件名、文本 / IR 写出和目录组织。

## 当前代码现状

### config 只保存 dump 根目录

`kernel_gen.core.config` 当前公开 API 只设置 / 读取 `dump_dir`，不定义 dump 目录结构、文件名、写入换行、IR 格式化或 marker 规则。

```python
def set_dump_dir(value: str | Path | None) -> None:
    ...


def get_dump_dir() -> Path | None:
    ...
```

相关文件：

- `spec/core/config.md`
- `kernel_gen/core/config.py`
- `test/core/test_config.py`

### PassManager 自己写 pass IR dump

当前 `PassManager.run(...)` 直接读取 `get_dump_dir()`，自己完成初始 IR 与逐 pass IR dump。

```python
dump_path = get_dump_dir()
if dump_path is not None:
    _write_dump_file(dump_path / "01-first-ir.mlir", _format_dump_ir(result))

for index, item in enumerate(self._passes, start=2):
    item.apply(ctx, result)
    if _pass_fold_enabled(item):
        _fold_module(ctx, result)
    if dump_path is not None:
        pass_name = getattr(item, "name", "pass")
        safe_name = _sanitize_dump_name(pass_name)
        dump_text = f"{pass_name}\n{_format_dump_ir(result)}"
        _write_dump_file(dump_path / f"{index:02d}-{safe_name}.mlir", dump_text)
```

现状问题：

- `_sanitize_dump_name`、`_write_dump_file`、`_format_dump_ir` 只服务 dump 写出，却挤在 pass 管理器中。
- pass 文件名、文本换行、父目录创建、alias IR 打印和 marker 拼接都在 `pass_manager.py` 内部维护。
- `pass_dump_xdsl_pipeline_spec_options` 会改变 marker 内容，本计划必须复用该口径，不再另造 pass 打印协议。

相关文件：

- `spec/pass/pass_manager.md`
- `kernel_gen/passes/pass_manager.py`
- `test/passes/test_pass_manager.py`

### dsl_run 自己写 kernel 级 dump

当前 `dsl_run` 在 `dump_dir/<kernel name>/` 下写入初始 IR、pass dump 和最终源码。自定义 pipeline fallback 也自己写 `01-first-ir.mlir` 与 `02-pipeline.mlir`。

```python
dump_dir = get_dump_dir()
if dump_dir is None:
    return None
kernel_name = getattr(func_obj, "__name__", "kernel")
return dump_dir / _sanitize_dump_component(kernel_name)
```

```python
_write_dump_file(dump_dir / "01-first-ir.mlir", print_operation_with_aliases(module))
output = pipeline.run(module)
_write_dump_file(
    dump_dir / "02-pipeline.mlir",
    f"{pipeline_name}\n{print_operation_with_aliases(output)}",
)
```

现状问题：

- `dsl_run.py` 也定义 `_sanitize_dump_component` 与 `_write_dump_file`。
- kernel 子目录 sanitize 与 pass dump 文件名 sanitize 是同一类规则，当前重复维护。
- 自定义 pipeline fallback 仍需要保留，但底层写出逻辑不应重复。

相关文件：

- `spec/tools/dsl_run.md`
- `kernel_gen/tools/dsl_run.py`
- `test/tools/test_dsl_run.py`

### ircheck 自己写 .irdump

当前 `ircheck` 在 `.irdump/<case>/` 下写 input、step、失败前 IR 和 emitc 目标产物。

```python
_write_irdump_file(dump_dir / "00-input.mlir", input_dump_ir)
_write_irdump_file(
    dump_dir / f"{index:02d}-{step.kind}-{step.name}.mlir",
    actual_dump_ir,
)
_write_irdump_file(
    dump_dir / f"{index:02d}-before-failed-{step.kind}-{step.name}.mlir",
    last_success_dump_ir,
)
```

现状问题：

- `_write_irdump_file` 与其它 `_write_dump_file` 基本重复。
- `.irdump` 目录结构应保留，但底层写文本行为可以复用。

相关文件：

- `spec/tools/ircheck.md`
- `kernel_gen/tools/ircheck.py`
- `test/tools/test_ircheck_cli.py`
- `test/tools/test_ircheck_runner.py`

### gen_kernel / emit backend / execute_engine 自己写 source artifact

当前 `gen_kernel` 在 `dump_dir` 非空时写 `source.cpp`，SourceBundle 场景还会展开 artifact；部分 emit backend 也按 `dump_dir/compile/...` 写 compile product；execute_engine builtin strategy 还会在工作目录下写 shared compile unit、dry-run 占位产物、CUDA SourceBundle artifact，并分配 runtime trance 目录路径。

现状问题：

- 文本落盘逻辑与 dump writer 属于同一类能力。
- SourceBundle 路径安全校验是高风险逻辑，第一阶段不得顺手重写或弱化。
- 工作目录产物和 runtime trance 虽不全是 `.mlir` 文本，但属于 dump 派生生成物 / 路径分配，必须纳入统一管理边界。

相关文件：

- `spec/dsl/gen_kernel/gen_kernel.md`
- `spec/dsl/gen_kernel/source_bundle.md`
- `kernel_gen/dsl/gen_kernel/gen_kernel.py`
- `kernel_gen/dsl/gen_kernel/emit/dummy_generic/__init__.py`
- `kernel_gen/execute_engine/builtin_strategy/common.py`
- `kernel_gen/execute_engine/builtin_strategy/cuda_sm86.py`
- `test/dsl/gen_kernel/test_gen_kernel.py`
- `test/dsl/gen_kernel/test_source_bundle.py`
- `test/execute_engine/test_builtin_strategy.py`
- `test/execute_engine/test_cuda_sm86_strategy.py`

## 目标 spec

- 新增：`spec/core/tools/dump_dir.md`
- 更新：
  - `spec/pass/pass_manager.md`
  - `spec/tools/dsl_run.md`
  - `spec/tools/dsl_cost_run.md`
  - `spec/tools/ircheck.md`
- 若 latest main 已包含 pass dump xDSL marker spec，execute 只补充“dump_dir writer 为底层写出真源”的实现归属说明，不回退或重复改写 pass option 语义。
- 本计划更新 `spec/dsl/gen_kernel/gen_kernel.md`、`spec/dsl/gen_kernel/source_bundle.md` 与必要 emit backend / strategy spec，说明所有当前文本型 dump 生成物最终落盘统一通过 `DumpDirWriter`。
- 本计划同步更新 `spec/execute_engine/strategy.md` 与 `spec/execute_engine/execute_engine_target.md`，说明内置 strategy 的工作目录、SourceBundle artifact、compile unit source 与 dry-run 占位产物由 `DumpDirWriter` 统一管理路径和 Python 侧文本写出。
- 本计划同步更新 `spec/tools/dsl_run.md` 与 `spec/tools/dsl_cost_run.md` 中 `dsl_cost_run(...)` 的 `99-cost-source.cpp` 写出归属，以及 `spec/execute_engine/execute_engine_target.md` 中 runtime trance `KG_TRANCE_DIR_PATH` 的路径分配归属。

## 公开 API / 行为设计

### 新增仓库内部共享 API

按用户“接口更少”的意见，本计划只新增一个跨文件共享入口，canonical import path 为：

```python
from kernel_gen.core.tools.dump_dir import DumpDirWriter
```

API 形态：

```python
@dataclass(frozen=True)
class DumpDirWriter:
    root: Path

    @classmethod
    def from_config(cls) -> "DumpDirWriter | None":
        ...

    def child(self, name: str, fallback: str = "dump") -> "DumpDirWriter":
        ...

    def write(self, name: str, content: ModuleOp | Operation | str, *, marker: str | None = None) -> Path:
        ...

    def write_stage(
        self,
        index: int,
        name: str,
        content: ModuleOp | Operation | str,
        *,
        marker: str | None = None,
        suffix: str = ".mlir",
        fallback: str = "stage",
    ) -> Path:
        ...
```

接口收缩原则：

- 不暴露 `sanitize_dump_component(...)`。
- 不暴露 `write_text_artifact(...)`。
- 不暴露 `format_ir_dump(...)`。
- 不暴露 `pass_dump_label(...)` 或 `write_pass(...)`。
- pass marker 由 `PassManager` 使用 xDSL public API 生成后传入 `DumpDirWriter.write_stage(..., marker=...)`。
- 所有 sanitize、父目录创建、换行补齐、alias IR 格式化均为 `writer.py` 内部实现细节。

### 行为保持

- 不改 `kernel_gen.core.config.set_dump_dir/get_dump_dir` 签名、错误语义或公开配置规则。
- 不改现有 dump 文件名：
  - `01-first-ir.mlir`
  - `NN-<pass-name>.mlir`
  - `02-pipeline.mlir`
  - `.irdump/<case>/00-input.mlir`
  - `.irdump/<case>/NN-<kind>-<name>.mlir`
  - `.irdump/<case>/NN-before-failed-<kind>-<name>.mlir`
  - `source.cpp`
  - `99-cost-source.cpp`
- 不把 pass option 写入文件名。
- `ModuleOp | Operation` dump 正文继续使用 `kernel_gen.core.print.print_operation_with_aliases(...)`。
- 字符串内容保持原文本，仅补齐末尾换行。
- `child(name, fallback=...)` 使用与当前 sanitize 等价的安全文件名片段规则：只保留字母、数字、点、下划线和短横线，其它字符改为 `_`；空值使用 fallback。
- `write(name, ...)` 的 `name` 支持安全相对文件路径，用于 SourceBundle artifact，例如 `kernel.cu`、`include/kernel.h`；它必须拒绝绝对路径、`.`、`..`、空 segment、反斜杠、NUL 和已存在 symlink 逃逸。
- `write_stage(index, name, ...)` 的 `name` 仍按单个文件名片段 sanitize，不支持路径分隔符；stage 文件名必须保持 `{index:02d}-{safe-name}{suffix}`。
- `write_stage(..., suffix=...)` 的 `suffix` 只允许安全扩展名：必须以 `.` 开头，不得为空，不得包含 `/`、反斜杠、NUL、`.` / `..` 路径片段或其它路径分隔语义；非法值必须稳定失败并由调用方按所属公开错误语义处理。
- `DumpDirWriter` 直接 API 对非法 `name`、非法 `suffix`、非法 `index`、非法 `content` 或 symlink escape 抛 `ValueError`；本计划不承诺 `ValueError` 的稳定错误文本，测试不得匹配完整错误字符串。
- 现有公开入口已有稳定 `KernelCodeError` 文本时，调用方必须捕获 `ValueError` 并映射回所属模块当前公开错误语义，例如 SourceBundle path escape 仍报 `source_bundle_path_escape`。

## 非目标

- 不新增、修改、删除 `expectation/`。
- 不改变 pass 顺序、pipeline 行为、IR rewrite 行为、EmitC 语义或源码生成结果。
- 不重新设计 pass option 打印；该语义归 `pass_dump_xdsl_pipeline_spec_options`。
- 不新增 CLI 参数或 `config` 公开选项。
- 不把 `DumpDirWriter` 设计成通用日志系统、事件系统或 tracing 框架。
- 不把 SourceBundle 解析协议迁入 dump writer；解析 marker、重复 path、malformed bundle 仍由 SourceBundle 所属模块负责。
- 不新增 bytes / binary writer API；如执行发现真实二进制产物必须纳入，需要暂停并取得用户确认。
- 不把 `.irdump` 迁入 `kernel_gen.core.config.dump_dir`；`ircheck -irdump` 仍按现有 CLI 行为落到 `.irdump/<case>/`。

## 禁止修改面

- `expectation/`
- `.skills/`
- `agents/standard/`
- `AGENTS.md`
- `TODO.md`
- `DONE.md`
- `plan/1.md`
- 本计划文件 `ARCHITECTURE/plan/dump_diagnostics_writer_refactor.md`

执行人、review 和终验必须把本计划文件当作只读合同输入；由于 `ARCHITECTURE/plan/` 当前可能被 `.gitignore` 忽略，不能只用 `git diff -- <plan>` 判断未改，必须使用管理员下发时提供的计划 sha256 或守护 worktree 证据进行 hash 校验。

## 方案比较与选型

### 方案 A：继续让每个模块自己写

- 优点：局部改动最少。
- 问题：重复的写文件、sanitize、换行、IR 格式化继续存在；后续 dump marker 或路径安全修复仍要多点修改。
- 结论：不采用。

### 方案 B：暴露多个工具函数

- 做法：暴露 `sanitize_dump_component`、`write_text_artifact`、`format_ir_dump`、`write_pass_dump` 等函数。
- 优点：每个能力可单独测试。
- 问题：接口偏多，调用方容易绕开统一入口继续拼装；用户已明确希望接口更少。
- 结论：不采用。

### 方案 C：只暴露 `DumpDirWriter`

- 做法：把目录、文件、stage、文本 / IR 写出收在一个小类里，调用方只依赖该类的公开方法。
- 优点：接口少；路径与写出规则单点收敛；pass marker 仍留在 `PassManager`，避免 dump_dir 层知道 pass 业务。
- 风险：`write_stage(...)` 需要同时覆盖 pass dump 与 ircheck step dump，参数必须保持简单，避免演变成过宽工具 API。
- 本计划采用：方案 C。

## 完成态定义

- `kernel_gen/core/tools/dump_dir/` 存在并有文件级说明、API 列表、使用示例与关联文件。
- `DumpDirWriter` 是该目录唯一跨文件共享入口。
- `PassManager` 不再定义自己的 `_sanitize_dump_name`、`_write_dump_file`、`_format_dump_ir`。
- `dsl_run` 不再定义自己的 `_write_dump_file`；kernel 子目录使用 `DumpDirWriter.child(...)`。
- `dsl_cost_run(...)` 的 `99-cost-source.cpp` 由 `DumpDirWriter.write(...)` 写出，文件名和目录结构保持不变。
- `ircheck` 不再定义自己的 `_write_irdump_file`；`.irdump` 文件结构保持不变。
- 第一阶段迁移 `gen_kernel` / SourceBundle / emit backend / execute_engine builtin strategy 当前 Python 侧 dump 生成物写出与路径分配；SourceBundle path 解析保留在所属模块，最终文件落盘由 `DumpDirWriter.write(...)` 管理，且路径逃逸测试通过。
- `gen_kernel` 的 `source.cpp`、SourceBundle artifact、dummy backend `source.cpp` / build artifact、builtin strategy `kernel.cpp`、dry-run `libkernel.so`、CUDA SM86 `source/source.cpp` aggregate 与 `.cu/.cuh` artifact 均通过 `DumpDirWriter` 管理最终落盘或输出路径分配。
- runtime trance 的 `KG_TRANCE_DIR_PATH` 由 `DumpDirWriter` 派生 `dump_dir/<kernel>/trance` 路径，现有环境变量文本和目录结构保持。
- 真实编译器产出的二进制仍由编译命令写入，但输出路径必须由 `DumpDirWriter` 分配；本计划不新增 bytes / binary writer API。
- `expectation/` 无 diff。
- 现有 dump 文件名与目录结构兼容，pytest 锁定。

## 计划级任务

- 计划级任务目标：新增 `kernel_gen.core.tools.dump_dir.DumpDirWriter` 作为唯一内部共享 dump_dir writer，并迁移 PassManager、dsl_run、dsl_cost_run、ircheck、gen_kernel、SourceBundle、emit backend 与 execute_engine builtin strategy 当前 Python 侧 dump 生成物写出 / dump 派生路径分配逻辑；在不改变现有 dump 文件名、目录结构、pipeline 行为、SourceBundle 安全语义、runtime trance 路径文本和 expectation 资产的前提下，完成 spec、实现、pytest 与减法检查闭环。
- 任务类型：`execute`。
- 固定流转：`execute -> review -> archive_acceptance / 计划书入档验收 -> merge/归档`。
- 下发前置：已满足。Kierkegaard / Ptolemy 两路 Draft 3-R5 strict review 均通过且无阻断、无最小需改项、无待确认项；`守护最好的爱莉希雅` 已在 `talk.log:11923` 对 Draft 3-R5-R1 执行守护最终检验并通过；管理员允许创建唯一计划级 execute。
- 依赖：`T-20260607-2b00a1ea / pass_dump_xdsl_pipeline_spec_options` 必须已归档 / 合并，且本计划 execute 已同步该 latest main；该任务未完成时不得并行执行本计划。

| 计划任务 | 任务类型 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `dump-diagnostics-writer-refactor` | `execute` | 管理员下发的新独立 worktree | `agents/codex-multi-agents/log/task_records/2026/<week>/YYYYMMDD-dump-diagnostics-writer-refactor.md` |

## 计划内小任务

### S1：新增 dump_dir writer spec 与实现

- 为什么做：先建立单一写出入口，避免迁移时各模块继续复制小 helper。
- 做什么：新增 `spec/core/tools/dump_dir.md`、`kernel_gen/core/tools/__init__.py`、`kernel_gen/core/tools/dump_dir/__init__.py`、`kernel_gen/core/tools/dump_dir/writer.py`。
- 不做什么：不新增 CLI/config 参数；不暴露多个函数。
- 怎么验收：`DumpDirWriter` 公开 API、文件级说明与测试一致。
- 卡住问谁：`DumpDirWriter` 签名、默认值或是否继续收口接口存在争议时问用户；实现文件规范冲突问架构师。
- 合同验收：无必过 expectation；`expectation/` 不得有 diff。

详细执行：

1. 写 `spec/core/tools/dump_dir.md`，只列 `DumpDirWriter` 与 4 个公开方法。
2. 新增 `kernel_gen/core/tools/` 包文件；`kernel_gen.core.tools` 不重导出 dump_dir API。
3. 新增 `kernel_gen/core/tools/dump_dir/__init__.py`，只导出 `DumpDirWriter`。
4. 新增 `writer.py`，内部 helper 保持私有，不跨文件调用。
5. `writer.py` 文件级说明必须包含 `功能说明 / API 列表 / 使用示例 / 关联文件`。
6. 测试必须覆盖非法相对路径与非法 `write_stage(..., suffix=...)`，包括绝对路径、`..`、空 segment、反斜杠、NUL、无点 suffix、包含路径分隔的 suffix。

验收：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/core/test_dump_dir_writer.py
```

### S2：迁移 PassManager dump 写出

- 为什么做：PassManager 是用户最直接观察 pass dump marker 的入口。
- 做什么：使用 `DumpDirWriter.from_config()` 与 `write/write_stage` 替换本地 `_sanitize_dump_name/_write_dump_file/_format_dump_ir`。
- 不做什么：不改变 pass option marker 口径；不改 pass 文件名。
- 怎么验收：PassManager dump pytest 通过，旧 helper 扫描无残留定义。
- 卡住问谁：pass marker 内容、xDSL `pipeline_pass_spec` 输出或 pass-dump 任务基线存在冲突时问架构师 / 用户，不由 execute 决策。
- 合同验收：无必过 expectation；`expectation/` 不得有 diff。

详细执行：

1. `PassManager.run(...)` 中从 `DumpDirWriter.from_config()` 获取 writer。
2. 初始 IR 使用 `writer.write("01-first-ir.mlir", result)`。
3. pass 后 marker 使用 latest main 已确认口径：

   ```python
   marker = str(item.pipeline_pass_spec(include_default=True))
   writer.write_stage(index, pass_name, result, marker=marker, fallback="pass")
   ```

4. 删除 `pass_manager.py` 中被替代的 dump 私有 helper。
5. 更新 `spec/pass/pass_manager.md` 与文件级说明，说明 dump 底层写出归 `DumpDirWriter`。

验收：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_pass_manager.py -k dump
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_pass_manager.py
```

### S3：迁移 dsl_run dump 写出

- 为什么做：`dsl_run` 是 kernel 级 dump 目录组织入口，当前和 PassManager 重复写文件。
- 做什么：用 `DumpDirWriter.child(kernel_name, fallback="kernel")` 组织 kernel 子目录，工具层 fallback 和 `dsl_cost_run(...)` 的 `99-cost-source.cpp` 都用 `write(...)`。
- 不做什么：不改变 `dump_dir/<kernel name>/` 结构；不改变 `source.cpp` 与 `99-cost-source.cpp` 文件名；不改变 source.cpp 由 `gen_kernel(...)` 写出的公开行为。
- 怎么验收：dsl_run dump、空 dump_dir、空函数名 fallback、自定义 pipeline fallback、dsl_cost_run dump 测试通过。
- 卡住问谁：kernel 子目录命名、fallback 名称、`dsl_cost_run` 写出归属存在公开行为冲突时问用户。
- 合同验收：无必过 expectation；`expectation/` 不得有 diff。

详细执行：

1. 删除或替换 `dsl_run.py` 中的 `_write_dump_file`。
2. `dsl_run` kernel dump 目录由 `DumpDirWriter.from_config().child(...)` 生成。
3. 标准 `PassManager` 仍通过临时 `set_dump_dir(dump_kernel_dir)` 复用 PassManager dump。
4. 覆盖 `run(module)` 的自定义 pipeline fallback 使用 `writer.write("01-first-ir.mlir", module)` 与 `writer.write("02-pipeline.mlir", output, marker=pipeline_name)`。
5. `dsl_cost_run(...)` 的 `99-cost-source.cpp` 使用同一 kernel writer 写出，文件名和现有写出路径保持不变。
6. 更新 `spec/tools/dsl_run.md` 与 `spec/tools/dsl_cost_run.md` 中 `dsl_cost_run(...)` 诊断源码写出归属说明，明确 `99-cost-source.cpp` 文件名 / 公开行为不变，最终写出由 `DumpDirWriter` 管理。

验收：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py -k "dump_dir or custom_pipeline_dump or empty_function_name"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_cost_run.py
rg -n "99-cost-source.cpp|DumpDirWriter|dump_dir" spec/tools/dsl_cost_run.md
```

### S4：迁移 ircheck .irdump 写出

- 为什么做：`ircheck` 有同类写文件 helper，适合迁移到底层 writer，但 `.irdump` CLI 语义必须保持。
- 做什么：在 `_run_ircheck_case(...)` 中把 `Path | None` dump_dir 转成 `DumpDirWriter | None`，用 `write(...)` 写 input、step、失败前 IR 与 emitc `.c`。
- 不做什么：不改变 `-irdump` 参数、不改变 `.irdump/<case>/` 根目录选择、不改变 compile step 语义。
- 怎么验收：ircheck CLI / runner dump 相关测试通过。
- 卡住问谁：`.irdump` 根目录、case 命名、失败前 dump 文件名或 emitc `.c` 写出语义出现冲突时问用户。
- 合同验收：无必过 expectation；`expectation/` 不得有 diff。

详细执行：

1. 用 `DumpDirWriter(dump_dir)` 替换 `_write_irdump_file(...)` 调用。
2. 删除 `_write_irdump_file(...)`。
3. 保留所有现有文件名格式。
4. 更新 `spec/tools/ircheck.md` 的实现归属说明。

验收：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_ircheck_cli.py test/tools/test_ircheck_runner.py
```

### S5：迁移 Source artifact、compile unit 与 compile product 写出

- 为什么做：用户明确要求 dump 统一管理所有生成物；源码 artifact 与工具 IR dump 一样属于 `dump_dir` 生成物。
- 做什么：迁移 `gen_kernel` 的 `source.cpp`、SourceBundle artifact、dummy backend compile source/build 文本产物、builtin strategy shared compile unit、CUDA SM86 SourceBundle 写盘和 dry-run 占位产物到 `DumpDirWriter.write(...)` 或 `DumpDirWriter` 管理的安全路径。
- 不做什么：不重写 SourceBundle aggregate 解析协议；不改变 malformed bundle 错误语义；不新增 bytes / binary writer API。
- 怎么验收：`source.cpp`、SourceBundle artifact、symlink/path escape 拒绝、dummy compile source/build 产物、builtin `kernel.cpp/libkernel.so`、CUDA `.cu/.cuh` artifact 与 `nvcc` 命令测试通过，路径结构保持。
- 卡住问谁：若 execute 发现必须新增 bytes writer、改变 SourceBundle 解析错误文本或改变 artifact path 语义，暂停并问用户。
- 合同验收：无必过 expectation；`expectation/` 不得有 diff。

详细执行：

1. 更新 `spec/dsl/gen_kernel/gen_kernel.md`、`spec/dsl/gen_kernel/source_bundle.md`、`spec/execute_engine/strategy.md` 与 `spec/execute_engine/execute_engine_target.md`，说明 `dump_dir` 和 builtin strategy work dir 下当前生成物最终落盘 / 路径分配由 `DumpDirWriter` 管理。
2. 在 `gen_kernel.py` 中保留 SourceBundle marker 解析和 malformed path 校验职责，但把 `source.cpp` 与 artifact 文件最终写出改为 `DumpDirWriter.write(...)`。
3. `DumpDirWriter.write(...)` 必须对 artifact 相对路径做安全解析，拒绝绝对路径、`.`、`..`、空 segment、反斜杠、NUL 与已存在 symlink 逃逸；错误必须由调用方映射为当前公开错误语义，不得泄漏内部异常文本。
4. 在 dummy backend compile strategy 中，用 `DumpDirWriter` 管理 `source_root/source.cpp`、SourceBundle artifact 和当前文本型 build artifact；保留 `dump_dir/compile/dummy_generic/<function>/source` 与 `build` 目录结构。
5. 在 `kernel_gen/execute_engine/builtin_strategy/common.py` 中，用 `DumpDirWriter` 管理 `kernel.cpp` 写出、dry-run `libkernel.so` 占位写出和 work dir 下安全路径分配；真实编译器输出仍由命令写入 writer 分配的 `libkernel.so` 路径。
6. 在 `kernel_gen/execute_engine/builtin_strategy/common.py` 中，runtime trance 的 `KG_TRANCE_DIR_PATH` 必须通过 `DumpDirWriter.from_config().child(kernel_name, fallback="kernel").child("trance")` 或等价 writer 语义生成，保持 `dump_dir/<kernel>/trance` 文本不变。
7. 在 `kernel_gen/execute_engine/builtin_strategy/cuda_sm86.py` 中，用 `DumpDirWriter` 管理 `source/source.cpp` aggregate、`.cu/.cuh` SourceBundle artifact 和 `libkernel.so` 输出路径；保留 SourceBundle marker 解析和 `source_bundle_malformed` 错误语义。
8. 删除或替换被 `DumpDirWriter` 覆盖的 `_safe_artifact_path` / `_safe_output_path` / `_write_source_dump` / `_write_source_product` / CUDA strategy path escape 写文件逻辑；如保留解析 helper，任务记录必须写清保留依据。
9. 补测试锁定普通源码、SourceBundle artifact、symlink escape、dummy compile source/build 产物、builtin `kernel.cpp/libkernel.so`、runtime trance `KG_TRANCE_DIR_PATH`、CUDA SourceBundle 写盘和 `nvcc` 命令路径均保持。

验收：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/test_gen_kernel.py test/dsl/gen_kernel/test_source_bundle.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py -k dump
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_compile_strategy.py -k dummy
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_builtin_strategy.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_cuda_sm86_strategy.py -k source_bundle
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_builtin_strategy.py -k trance
```

### S6：减法检查与全链路验证

- 为什么做：本计划价值在减少重复，不允许只加新 writer 而保留旧 helper。
- 做什么：扫描被替代 helper、执行 diff 反推 pytest、记录 expectation scope。
- 不做什么：不把 expectation 当作 diff 反推测试。
- 怎么验收：旧 helper 扫描、pytest、compileall、diff check、敏感禁止面检查均通过，任务记录完整。
- 卡住问谁：扫描命中无法判断是否属于本轮残留时问架构师；敏感面出现 diff 时按权限暂停回报管理员 / 用户。
- 合同验收：无必过 expectation；`expectation/` 不得有 diff。

详细执行：

1. 扫描旧 helper 和直接文本落盘残留：

   ```bash
   rg "_write_dump_file|_write_irdump_file|_write_source_dump|_write_source_product|_sanitize_dump_name|_sanitize_dump_component|_format_dump_ir|_safe_artifact_path|_safe_output_path|write_text\\(" kernel_gen
   ```

2. `source_bundle_path_escape` 是既有公开错误语义，不列入删除扫描；必须另行用测试确认该错误码仍由所属模块对外抛出，不泄漏 `DumpDirWriter` 的 `ValueError` 文本。
3. 对 `ircheck._render_operation_dump_text` 写保留依据或迁移依据；若未迁移，说明它是 ircheck 语义渲染 helper，不属于通用文本写出 helper。
4. 对 SourceBundle 解析 helper 写保留依据；解析协议可保留在领域模块，最终落盘与 path escape 防护必须收敛到 `DumpDirWriter`。
5. 扫描跨文件 private helper 调用，确保调用方只使用 `DumpDirWriter` 公开方法。
6. 跑 diff 反推 pytest。
7. 写任务记录：
   - 执行前阅读记录
   - 最小功能闭环
   - Diff 反推自测
   - 减法检查
   - expectation 合同验收口径

验收：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/core/test_config.py test/core/test_dump_dir_writer.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_pass_manager.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_cost_run.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_ircheck_cli.py test/tools/test_ircheck_runner.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/test_gen_kernel.py test/dsl/gen_kernel/test_source_bundle.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_compile_strategy.py -k dummy
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_builtin_strategy.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_cuda_sm86_strategy.py -k source_bundle
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m compileall kernel_gen/core/tools kernel_gen/passes/pass_manager.py kernel_gen/tools/dsl_run.py kernel_gen/tools/ircheck.py kernel_gen/dsl/gen_kernel/gen_kernel.py kernel_gen/dsl/gen_kernel/emit/dummy_generic/__init__.py kernel_gen/execute_engine/builtin_strategy/common.py kernel_gen/execute_engine/builtin_strategy/cuda_sm86.py
git diff --check
git diff -- expectation/ .skills/ agents/standard/ AGENTS.md TODO.md DONE.md plan/1.md
git status --short --untracked-files=all -- expectation/ .skills/ agents/standard/ AGENTS.md TODO.md DONE.md plan/1.md
sha256sum ARCHITECTURE/plan/dump_diagnostics_writer_refactor.md
```

计划文件 hash 门禁：

- 管理员下发 execute 时必须提供本计划 sha256。
- execute / review / 终验必须核对 `sha256sum ARCHITECTURE/plan/dump_diagnostics_writer_refactor.md` 与下发 sha256 一致。
- 若计划文件 hash 不一致，必须暂停并回报管理员 / 架构师，不得继续执行。

## expectation 口径

- 本计划不新增、修改、删除 `expectation/`。
- 本计划无默认必过 expectation。
- 若 execute 发现必须新增或修改 expectation，必须暂停并回报管理员转用户 / 架构确认。
- 若 review 需要额外运行 expectation，只能作为只读补充证据，不能替代 diff 反推 pytest。

## Review 必查项

- `DumpDirWriter` 是否确实是唯一跨文件共享入口，未暴露散装函数。
- `kernel_gen.core.tools.dump_dir` API 列表是否只包含计划确认的类与方法。
- `PassManager` 是否仍由 xDSL public API 生成 pass marker，dump_dir writer 不知道 pass 业务。
- dump 文件名与目录结构是否完全兼容。
- `dsl_run` 标准 pipeline 与自定义 pipeline fallback 均通过公开行为测试。
- `ircheck -irdump` 路径结构和失败前 dump 文件名是否保持。
- `gen_kernel` / SourceBundle / emit backend source artifact / execute_engine builtin strategy 生成物是否已通过 `DumpDirWriter` 管理最终落盘或路径分配。
- SourceBundle malformed path、symlink escape 和当前公开错误语义是否保持。
- `write_stage(..., suffix=...)` 是否有非法 suffix 测试和稳定失败语义。
- 是否删除被替代旧 helper，保留项是否有明确依据。
- `dsl_run._sanitize_dump_component` 是否已删除或有计划内保留依据。
- `ircheck._render_operation_dump_text` 是否有明确保留依据，未被误当作通用写文件 helper 删除。
- SourceBundle 解析 helper 是否只保留解析职责，没有继续承载最终落盘 / path escape 防护重复逻辑。
- builtin strategy shared `kernel.cpp/libkernel.so` 与 CUDA SM86 `.cu/.cuh/source.cpp` 写出是否纳入 S5/S6 验收。
- 测试是否只使用公开 API，不直连私有 helper。
- 敏感禁止面门禁是否通过。
- `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`plan/1.md` 无 diff，本计划文件 hash 未变化。

## 迭代审阅记录

### Draft 1 本地整理

- 时间：2026-06-07
- 处理人：大闸蟹
- 输入：
  - 用户要求查看当前代码现状、代码示例和预期改法。
  - 用户要求接口减少。
  - 用户确认落点为 `core/tools/dump_dir`。
- 主线处理：
  - 将草稿从多个散装函数收缩为 `DumpDirWriter` 一个内部共享入口。
  - 删除 `write_pass(...)` 设计，避免 dump_dir 层承载 pass 业务。
  - 明确与 `pass_dump_xdsl_pipeline_spec_options` 的依赖和边界。
  - 明确本计划不修改 expectation。
- 历史状态：
  - Draft 1 已完成两路 subagent strict review。
  - 已根据 review 结果修订为 Draft 3。
  - Draft 3 已进入后续复审，并在 Draft 3-R1 / Draft 3-R2 中继续收口用户“dump 统一管理所有生成物”口径。

### subagent strict review 收敛结论

### Draft 1 subagent strict review

- 时间：2026-06-07
- Kierkegaard：结论=不通过。
  - 最小需改项 1：`DumpDirWriter` 属于跨文件共享 API，完整签名和默认值需要用户确认，或必须列为待确认项。
  - 最小需改项 2：与 `T-20260607-2b00a1ea / pass_dump_xdsl_pipeline_spec_options` 的依赖必须写成归档 / 合并 / 同步 latest main 后才允许 execute，不得并行。
  - 最小需改项 3：减法扫描需覆盖 `dsl_run._sanitize_dump_component`，并补敏感禁止面状态门禁。
- Ptolemy：结论=最小需改项。
  - 最小需改项 1：`DumpDirWriter` 完整 API 签名需要用户确认。
  - 最小需改项 2：S5 不能让 execute 现场判断是否迁移 `gen_kernel` / SourceBundle，必须二选一写死。
  - 最小需改项 3：S1-S6 需补齐任务卡短口径、合同验收和敏感门禁。
- 主线处理：
  - 已新增 DU1，并在用户回复“可以”后记录为确认 `DumpDirWriter` 完整 API。
  - 已新增 DU2，并在用户明确“dump 统一管理所有生成物”后改为纳入 `gen_kernel` / SourceBundle / emit backend source artifact。
  - 已把 pass-dump 依赖改为归档 / 合并 / 同步 latest main 后才允许 execute。
  - 已将 S5 收口为 Source artifact 与 compile product 写出迁移，并补路径安全验收。
  - 已补 S1-S6 的 `卡住问谁` 与 `合同验收`。
  - 已补旧 helper 扫描和敏感禁止面门禁。
- 历史状态：
  - DU1/DU2 均已确认。
  - Draft 3 已进入后续复审。

### subagent strict review 收敛结论

- Kierkegaard：Draft 1 不通过，待 Draft 3 复审。
- Ptolemy：Draft 1 最小需改项，待 Draft 3 复审。
- 收敛结论：已收敛；Draft 3 复审中发现 source artifact 范围仍需补齐 execute_engine builtin/cuda_sm86、suffix 安全约束和计划文件 hash 门禁，Draft 3-R2 复审中发现 S6 总体验收漏 `dsl_cost_run`，Draft 3-R3 复审中发现漏同步 `spec/tools/dsl_cost_run.md`，Draft 3-R4 复审中发现 S3 spec 检查存在计划文件命中导致的假阳性，均已按用户“dump 统一管理所有生成物”口径继续修订；Draft 3-R5 经 Kierkegaard / Ptolemy 两路 strict review 均通过，无阻断、无最小需改项、无待确认项。

### Draft 3-R1 修订

- 时间：2026-06-07
- 触发来源：
  - 用户再次确认“应该由 dump 统一管理所有的生成物”。
  - Kierkegaard Draft 3 复审指出：S5 漏掉 `kernel_gen/execute_engine/builtin_strategy/common.py` 与 `cuda_sm86.py` 写出路径；`write_stage(..., suffix=...)` 安全语义未约束；敏感门禁缺本计划文件 hash 校验。
- 主线处理：
  - DU2 范围扩展为所有当前 Python 侧写出 / 路径分配生成物，包括 `kernel.cpp`、dry-run `libkernel.so`、CUDA SM86 SourceBundle `.cu/.cuh` artifact、`source.cpp` aggregate。
  - `write_stage(..., suffix=...)` 增加安全扩展名约束和测试要求。
  - S5 纳入 `kernel_gen/execute_engine/builtin_strategy/common.py`、`kernel_gen/execute_engine/builtin_strategy/cuda_sm86.py`、`spec/execute_engine/strategy.md`、`spec/execute_engine/execute_engine_target.md`、`test/execute_engine/test_builtin_strategy.py`、`test/execute_engine/test_cuda_sm86_strategy.py`。
  - S6 增加 source/product/path escape 扫描、builtin/cuda pytest、compileall 范围和计划文件 sha256 门禁。
  - 新增“禁止修改面”章节，明确本计划文件只读。
- 当时状态：
  - Draft 3-R5 已完成 Kierkegaard / Ptolemy 两路 subagent strict review，均通过。
  - 当时尚未请求守护最终检验；后续已由 `守护最好的爱莉希雅` 在 `talk.log:11923` 完成守护最终检验并通过。

### Draft 3-R2 修订

- 时间：2026-06-07
- 触发来源：
  - 用户再次强调“我觉得应该由dump 统一管理所有的生成物”。
- 主线处理：
  - 将计划用途从 MLIR / diagnostics 文本写出扩展为 dump 生成物写出与 dump 派生路径分配统一管理。
  - DU2 明确覆盖 `dsl_run`、`dsl_cost_run`、`ircheck`、`gen_kernel`、SourceBundle、dummy backend、execute_engine builtin strategy、CUDA SM86 artifact、dry-run `libkernel.so`、真实编译器输出路径分配和 runtime trance 路径分配。
  - 完成态和计划级任务目标同步写明所有当前 Python 侧 dump 生成物写出 / dump 派生路径分配均归 `DumpDirWriter` 管理。
  - S6 减法扫描移除 `source_bundle_path_escape`，避免误导 execute 删除既有公开错误码；改为要求用测试确认错误码仍由所属模块对外抛出，且不泄漏 `DumpDirWriter.ValueError` 文本。
- 当前状态：
  - Draft 3-R2 已完成 Kierkegaard 复审；Kierkegaard 发现 S6 总体验收漏 `test/tools/test_dsl_cost_run.py`，已在 Draft 3-R3 修复。

### Draft 3-R3 修订

- 时间：2026-06-07
- 触发来源：
  - Kierkegaard Draft 3-R2 strict review 最小需改项：S6 计划级全链路 pytest 漏 `test/tools/test_dsl_cost_run.py`，与 `dsl_cost_run(...)` / `99-cost-source.cpp` 纳入 dump 生成物范围冲突。
- 主线处理：
  - S6 总体验收命令加入 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_cost_run.py`。
  - 未改变公开 API、expectation 授权、用户确认、依赖前置或禁止修改面。
- 当前状态：
  - Draft 3-R3 已完成 Ptolemy 复审；Ptolemy 发现目标 spec / S3 漏 `spec/tools/dsl_cost_run.md`，已在 Draft 3-R4 修复。

### Draft 3-R4 修订

- 时间：2026-06-07
- 触发来源：
  - Ptolemy Draft 3-R3 strict review 最小需改项：仓库存在独立公开 spec `spec/tools/dsl_cost_run.md`，但计划只要求更新 `spec/tools/dsl_run.md` 中 `dsl_cost_run(...)` / `99-cost-source.cpp` 归属。
- 主线处理：
  - 目标 spec 增加 `spec/tools/dsl_cost_run.md`。
  - S3 执行步骤要求同步更新 `spec/tools/dsl_run.md` 与 `spec/tools/dsl_cost_run.md`，明确 `99-cost-source.cpp` 文件名 / 公开行为不变，最终写出由 `DumpDirWriter` 管理。
  - S3 验收增加 `rg -n "99-cost-source.cpp|DumpDirWriter|dump_dir" spec/tools/dsl_cost_run.md ARCHITECTURE/plan/dump_diagnostics_writer_refactor.md`。
  - 未改变公开 API、expectation 授权、用户确认、依赖前置或禁止修改面。
- 当前状态：
  - Draft 3-R4 已完成 Ptolemy 复审；Ptolemy 发现 S3 spec 检查同时扫描计划文件会导致假阳性，已在 Draft 3-R5 修复。

### Draft 3-R5 修订

- 时间：2026-06-07
- 触发来源：
  - Ptolemy Draft 3-R4 strict review 最小需改项：S3 新增 `rg` 验收同时扫描 `spec/tools/dsl_cost_run.md` 和计划文件，即使 spec 未更新也会因计划文件命中而返回成功。
- 主线处理：
  - S3 验收改为 spec-only：`rg -n "99-cost-source.cpp|DumpDirWriter|dump_dir" spec/tools/dsl_cost_run.md`。
  - 未改变公开 API、expectation 授权、用户确认、依赖前置或禁止修改面。
- 当前状态：
  - Draft 3-R5 已完成 Kierkegaard / Ptolemy 两路 subagent strict review，均通过。

### Draft 3-R5 strict review 收敛

- 时间：2026-06-07
- 标准包：
  - 根 `AGENTS.md`。
  - `agents/standard/计划书标准.md`。
  - `agents/standard/审查规范.md`。
  - `agents/standard/任务记录约定.md`。
  - Draft 3-R5 全文，sha256=`c06e294f554245079e777265984033dedf397542d9ea7e1fa8cf87cfdf2f55a3`。
  - 用户确认：`DumpDirWriter` 完整 API、落点 `core/tools/dump_dir`、接口更少、`dump` 统一管理所有生成物、按计划书流程推进。
  - 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、`plan/1.md`、本计划文件。
  - 必过验收命令：以 S1-S6 当前正文为准；本计划无必过 `expectation`，`expectation/` 不得有 diff。
- Kierkegaard / `019e9e16-782d-7451-a288-17ebffc15b4d`：
  - 结论：通过。
  - 阻断项：无。
  - 最小需改项：无。
  - 待确认项：无。
  - 关键证据：sha256=`c06e294f554245079e777265984033dedf397542d9ea7e1fa8cf87cfdf2f55a3`；`git diff --check -- ARCHITECTURE/plan/dump_diagnostics_writer_refactor.md` 通过；S3 spec-only 验收已改为 `rg -n "99-cost-source.cpp|DumpDirWriter|dump_dir" spec/tools/dsl_cost_run.md`；`spec/tools/dsl_cost_run.md` 已在目标 spec 与 S3 执行步骤中；S6 覆盖 `test/tools/test_dsl_cost_run.py`；未破坏公开 API、expectation 授权、用户确认、依赖前置、禁止修改面或任务边界。
- Ptolemy / `019e9e16-c5ff-7a42-b1c8-ab46d15020c1`：
  - 结论：通过。
  - 阻断项：无。
  - 最小需改项：无。
  - 待确认项：无。
  - 关键证据：sha256=`c06e294f554245079e777265984033dedf397542d9ea7e1fa8cf87cfdf2f55a3`；`git diff --check -- ARCHITECTURE/plan/dump_diagnostics_writer_refactor.md` 通过；S3 验收已为 spec-only，避免计划文件命中导致假阳性；未破坏公开 API、expectation 授权、用户确认、依赖前置或禁止修改面。
- 收敛结论：
  - 已发起的 Kierkegaard / Ptolemy 两路 strict review 均通过。
  - 当前剩余阻断项：无。
  - 当前剩余最小需改项：无。
  - 当前剩余待确认项：无。
  - 本 Draft 3-R5-R1 仅写回 strict review 通过记录，不改变公开 API、验收资产、任务范围、expectation 授权或用户确认。

### 守护最终检验

- 时间：2026-06-07。
- 检验对象：`守护最好的爱莉希雅`。
- 回执来源：`agents/codex-multi-agents/log/talk.log:11923`。
- 守护对象：`ARCHITECTURE/plan/dump_diagnostics_writer_refactor.md` Draft 3-R5-R1，guard worktree 为 `/home/lfr/kernelcode_generate/wt-20260607-dump-diagnostics-writer-refactor-guard`。
- 守护对象 sha256：`0b86b47b8f4f3919258d67ddb0a310ae02c0d7cde1c76b877764756e9a57d862`。
- 结论：通过。
- 阻断项：无。
- 最小需改项：无。
- 待确认项：无。
- 守护结论：允许通知管理员创建唯一计划级 `execute`；不得创建第二个计划级任务；实际 execute 必须使用 latest main 中已合入的 `pass_dump_xdsl_pipeline_spec_options` 结果。
