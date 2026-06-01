# CUDA SM86 Emit Package Structure Refactor Green Plan

## 文档信息
- 状态：Codex subagent strict review 已收敛 / 守护最终检验通过 / 可下发唯一计划级 execute。
- 用户确认来源：
  - 用户指出 `kernel_gen/dsl/gen_kernel/emit/cuda_sm86` 当前结构“不对”，应当“跟其他 target 差不多”。
  - 用户确认需要出计划书，并按最新计划流程推进。
  - execute 返工中用户进一步确认：`cuda_sm86` 结构应与 `npu_demo` 一样，一个 `kernel.*` op 对应一个 emit，并且需要添加对应 target include。
  - execute 返工中用户进一步确认：`include/cuda_sm86` 应根据 IR 表达涉及的 API 设计，不保留固定业务 kernel entry / fallback。
- 计划任务名：`cuda-sm86-emit-package-structure-refactor`
- 任务类型：唯一计划级 `execute`
- 流转：`execute -> review -> archive_acceptance -> merge/归档`
- 任务记录建议：`agents/codex-multi-agents/log/task_records/2026/<dd>/<date>-cuda-sm86-emit-package-structure-refactor.md`
- 计划文件跟踪要求：`ARCHITECTURE/plan/` 当前被 `.gitignore` 忽略；本计划进入下发 / merge 前必须用 `git add -f ARCHITECTURE/plan/cuda_sm86_emit_package_structure_refactor_green_plan.md` 纳入候选，并在任务记录中写入 `git ls-files --error-unmatch ARCHITECTURE/plan/cuda_sm86_emit_package_structure_refactor_green_plan.md` 通过结果。

## 计划级任务

| 计划任务 | 任务类型 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `cuda-sm86-emit-package-structure-refactor` | `execute` | `wt-20260601-cuda-sm86-emit-package-structure-refactor` | `agents/codex-multi-agents/log/task_records/2026/<dd>/<date>-cuda-sm86-emit-package-structure-refactor.md` |

任务目标：按本计划将 `kernel_gen/dsl/gen_kernel/emit/cuda_sm86/` 从单文件 backend 重构为类似 `npu_demo` target 的分层 emit package，保持公开入口、CUDA 生成行为、9 demo runtime gate 和现有测试合同不变；同步 spec/test/文件级说明，删除 root `__init__.py` 中的大段源码模板和业务 kernel 逻辑。

## 计划目标
- 让 `cuda_sm86` emit backend 的代码组织对齐现有 target 结构，尤其是 `npu_demo`：
  - package root 只做 backend 聚合注册。
  - 具体 include、per-kernel-op emit、runtime、source bundle、detect/name 等逻辑拆到子模块。
  - 业务 kernel 源码生成不继续堆在 `cuda_sm86/__init__.py`。
- 保持包外 Python 公开 API 不变，并按用户确认把 CUDA include 收口为 arch 第一版分层：
  - 仍通过 `emit_c_include_impl(target="cuda_sm86")` 与 `emit_c_impl(..., target="cuda_sm86")` 被 emit registry 自动加载。
  - 不新增包外公开 import path。
  - `include/cuda_sm86/cuda_sm86.cuh` 作为 aggregate header，只聚合 `include/api/Arch.h` 和 `include/cuda_sm86/Arch.h`。
  - `include/cuda_sm86/Arch.h` 作为 CUDA 后端实现层，承接 generated source 真实使用的 IR slot/memory/scalar/copy/tf32 helper。
  - 不改变 `ExecutionEngine(target="cuda_sm86")`、`cuda-sm86-lowering`、SourceBundle、slot C ABI 或稳定错误语义。
- 保持当前 CUDA SM86 功能行为不变：
  - matmul / conv2d / flash_attention 三类现有 demo 仍由 lowered IR family 选择对应 generated source。
  - unsupported / unknown / name-only module 仍稳定失败。
  - `include/cuda_sm86/cuda_sm86.cuh` 仍是 generic aggregate include，不回退到固定 kernel include。

## 非目标
- 不重写 CUDA kernel 数值算法。
- 不扩大到任意 DSL kernel 支持。
- 不新增 `cuda_sm86` 公开 emitter API、公开 helper 或 package root re-export。
- 不修改 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。
- 不改变 `cuda-sm86-lowering` pipeline 顺序。
- 不在 `include/cuda_sm86/cuda_sm86.cuh` 中加入固定业务 kernel entry、host wrapper 或 family fallback。
- 不恢复 `launch_matmul_entry`、固定 `matmul_f32_kernel` 或任何 include 具体 kernel API。

## 当前基线
- 主仓当前 HEAD 与 `origin/main` 对齐到 `a8e1fcd7`。
- 当前 `kernel_gen/dsl/gen_kernel/emit/cuda_sm86/` 只有：
  - `__init__.py`，约 500 行。
- 当前 `__init__.py` 同时承担：
  - `@emit_c_impl(ModuleOp, target="cuda_sm86")` 注册入口。
  - lowered IR family 检测。
  - common CUDA runtime source 模板。
  - matmul CUDA source 模板。
  - conv2d CUDA source 模板。
  - flash_attention CUDA source 模板。
  - `kg_execute_entry(...)` wrapper source。
  - SourceBundle dict 拼装。
- 现有 `npu_demo` target 结构是 package 聚合模式：
  - `npu_demo/__init__.py` 只导入 `arch/control_flow/dma/kernel/memory/nn/symbol/tuner/type` 等子模块。
  - 具体 dialect/op family emitter 分散在 `npu_demo/dma/*.py`、`npu_demo/kernel/*.py`、`npu_demo/symbol/*.py` 等文件。
- 当前 CUDA SM86 spec 已明确：
  - `kernel_gen.dsl.gen_kernel.emit.cuda_sm86` backend 不新增独立公开 API。
  - `ModuleOp` 发射入口由 `emit_c_impl(..., target="cuda_sm86")` 注册合同承接。
  - generated source 承载具体 kernel，include 仅提供 generic runtime/ABI/helper。
- 当前缺口：
  - `cuda_sm86` backend 结构与其它 target 不一致。
  - root `__init__.py` 职责过大，维护和 review 成本高。
  - CUDA source 模板、family detection、SourceBundle 拼装没有明确模块边界。

## 方案比较与选型
- 不采用方案 A：保持单文件 `cuda_sm86/__init__.py`，只补注释。
  - 原因：与其它 target 结构不一致，继续放大 root 文件职责，后续新增 op family 会越来越难审查。
- 不采用方案 B：完全照搬 `npu_demo` 的每个 dialect/op 子目录，立即补齐 `dma/symbol/type/arch` 全套 emitter。
  - 原因：CUDA SM86 当前不是逐 op emit 完整 backend，现阶段只应先按真实职责拆分，不为未实现能力制造空模块。
- 不采用方案 C：把 CUDA source 模板移到 include 或 execute_engine。
  - 原因：具体 kernel 仍应由 `cuda_sm86` emit generated SourceBundle 承载；include 和 compile strategy 不应承担业务 kernel 生成。
- 采用方案：按当前 CUDA emit 真实职责做最小结构重构。
  - package root `__init__.py` 类似 `npu_demo/__init__.py`，只导入子模块触发注册。
  - `module.py` 承接 `ModuleOp` 注册入口与顶层分发。
  - `detect.py` 承接 lowered IR family 检测和 unsupported 稳定失败辅助。
  - `source_bundle.py` 承接 SourceBundle artifact 名称和 bundle 拼装。
  - `runtime.py` 承接 generated source 内部 common runtime source 片段。
  - `kernel/{binary_elewise,exp,img2col2d,matmul,reduce}.py` 承接对应 `kernel.*` op emit 注册；matmul / conv2d / flash_attention 的 generated source 由这些 op 文件中的 package-local source builder 承接。
  - 共享常量固定放在 `constants.py`，不新增包外公开 API。

## 公开 API 设计

### 功能简介
- 本计划是 backend 结构重构，并按用户确认把 `include/cuda_sm86` 收口为 arch 第一版分层：aggregate header + CUDA 后端实现层。
- `cuda_sm86` target backend 仍由 emit registry 自动加载；包外 Python 用户仍只通过 `emit_c_include_impl(...)` / `emit_c_impl(..., target="cuda_sm86")` 的既有 registry 路径触达。

### API 列表
- 保持不变：`emit_c_impl(ModuleOp, target="cuda_sm86")` 注册入口。
- 保持不变：每个支持的 `kernel.*` op 通过 `emit_c_impl(Kernel*Op, target="cuda_sm86")` 注册，不作为包外 direct-call API。
- 新增并确认：`emit_c_include_impl(target="cuda_sm86")` 注册入口。
- 保持不变：`emit_c_impl(...)`、`emit_c(...)`、`gen_kernel(...)` 等公开调用链。
- 补齐：`include/cuda_sm86/cuda_sm86.cuh` 公开 API 仅包含 `namespace cuda_sm86` 与 `struct cuda_sm86::ArgSlot` backend ABI，并聚合 `include/api/Arch.h` 与 `include/cuda_sm86/Arch.h`。
- 补齐：`include/cuda_sm86/Arch.h` 是 CUDA 后端实现层，`cuda_sm86::detail::*` 与 `KG_CUDA_CHECK` 只允许 generated source 使用，不进入跨 target 公开 API。
- 保持不变：`ExecutionEngine(target="cuda_sm86", ...)` 使用方式。
- 包外公开 API 不变；下列名称是本计划为完成 package 分层而定义的 `cuda_sm86` package-local 文件级 API。
- package-local 文件级 API 只允许 `kernel_gen/dsl/gen_kernel/emit/cuda_sm86/` 包内按本计划依赖方向跨文件调用，必须写入对应实现文件的文件级 `API 列表`；它们不进入 `cuda_sm86.__all__`、不进入 `cuda_sm86.kernel.__all__`、不写入包外 public path matrix、不允许测试或包外代码 direct import / call。
- 用户确认来源：用户要求 `cuda_sm86` emit 结构“跟其他 target 差不多”，并在 execute 返工中明确“一个 kernel op 对应一个 emit”“同时需要添加对应 include”“include/cuda_sm86 应该根据 IR 的表达进行 API 涉及”。
- package-local 文件级 API exact set：
  - `CUDA_SM86_TARGET_NAME: str = "cuda_sm86"`
  - `CUDA_SM86_KERNEL_SOURCE_ARTIFACT: str = "kernel.cu"`
  - `CUDA_SM86_GENERATED_ENTRY_HEADER_ARTIFACT: str = "include/cuda_sm86/generated_entry.cuh"`
  - `CUDA_SM86_RUNTIME_ENTRY_NAME: str = "kg_execute_entry"`
  - `CUDA_SM86_KERNEL_OP_BINARY_ELEWISE: str = "kernel.binary_elewise"`
  - `CUDA_SM86_KERNEL_OP_EXP: str = "kernel.exp"`
  - `CUDA_SM86_KERNEL_OP_IMG2COL2D: str = "kernel.img2col2d"`
  - `CUDA_SM86_KERNEL_OP_MATMUL: str = "kernel.matmul"`
  - `CUDA_SM86_KERNEL_OP_REDUCE: str = "kernel.reduce"`
  - `class CudaSm86KernelFamily(str, Enum)`
  - `@dataclass(frozen=True) class CudaSm86ModuleSummary`
  - `detect_cuda_sm86_kernel_family(module_op: ModuleOp, ctx: EmitCContext) -> CudaSm86KernelFamily`
  - `summarize_cuda_sm86_module(module_op: ModuleOp, ctx: EmitCContext) -> CudaSm86ModuleSummary`
  - `build_cuda_sm86_source_bundle(summary: CudaSm86ModuleSummary) -> dict[str, str]`
  - `emit_matmul_source(summary: CudaSm86ModuleSummary) -> str`
  - `emit_conv2d_source(summary: CudaSm86ModuleSummary) -> str`
  - `emit_flash_attention_source(summary: CudaSm86ModuleSummary) -> str`
- execute 必须按上述 exact 名称落地，写入对应文件级 `API 列表`；除上述列表和依赖方向外，不得新增其它跨文件 package-local API。测试仍不得 direct import / call 这些 package-local API，只能通过公开 emit / gen_kernel / ExecutionEngine 路径观察。
- `CudaSm86KernelFamily` exact members：
  - `MATMUL = "matmul"`
  - `CONV2D = "conv2d"`
  - `FLASH_ATTENTION = "flash_attention"`
- `CudaSm86ModuleSummary` exact fields：
  - `family: CudaSm86KernelFamily`
  - `matmul_count: int`
  - `img2col_count: int`
  - `exp_count: int`
  - `reduce_count: int`
  - `binary_count: int`
  - `launch_count: int`
  - `memory_rank_patterns: frozenset[tuple[int, ...]]`
- SourceBundle artifact key 合同保持不变：
  - `kernel.cu`，由 `CUDA_SM86_KERNEL_SOURCE_ARTIFACT` 承接。
  - `include/cuda_sm86/generated_entry.cuh`，由 `CUDA_SM86_GENERATED_ENTRY_HEADER_ARTIFACT` 承接。
- `include.py` / `kernel/*.py` 中 `_emit_cuda_sm86_*` 函数只作为 registry decorator entry 存在，不进入包外公开 API，不允许测试或包外 direct import / call。
- `constants.py` 只允许承载上述 exact string constants；不得放 CUDA source 大字符串、handler、family detection 或 SourceBundle 拼装逻辑。
- 允许依赖方向：
  - `__init__.py -> include.py, kernel/__init__.py, module.py`
  - `constants.py` 不导入任何 `cuda_sm86` 包内模块。
  - `module.py -> constants.py, detect.py, source_bundle.py`
  - `source_bundle.py -> constants.py, detect.py, runtime.py, kernel.matmul, kernel.img2col2d, kernel.reduce`
  - `include.py -> constants.py`
  - `runtime.py -> constants.py`
  - `kernel/{binary_elewise,exp}.py -> constants.py`
  - `kernel/{img2col2d,matmul,reduce}.py -> constants.py, detect.py`
  - `detect.py -> constants.py`；不得导入 `module.py`、`source_bundle.py` 或 `kernel/*`
  - `kernel/*` 不得导入 `module.py`、`detect.py`、`source_bundle.py` 或其它 `kernel/*`
  - `runtime.py` 不得导入 `module.py`、`detect.py`、`source_bundle.py` 或 `kernel/*`
  - `cuda_sm86.__all__` 与 `cuda_sm86.kernel.__all__` 必须为空列表，不 re-export package-internal 对象。

### 稳定错误语义
- 保持不变：
  - unknown / unsupported module 仍通过 `ctx.emit_error("cuda_sm86", "unsupported kernel family")` 或已有详细文本失败。
  - unsupported kernel op family 仍使用已有 `unsupported kernel op family: ...` 口径。
- 禁止新增因重构产生的新公开错误短语，除非先回用户确认。

## 目标结构

```text
kernel_gen/dsl/gen_kernel/emit/cuda_sm86/
  __init__.py
  constants.py
  detect.py
  include.py
  module.py
  runtime.py
  source_bundle.py
  kernel/
    __init__.py
    binary_elewise.py
    exp.py
    img2col2d.py
    matmul.py
    reduce.py
```

结构约束：
- `__init__.py`：
  - 只导入 `include`、`kernel`、`module` 触发注册。
  - `__all__: list[str] = []`。
  - 不保留 CUDA source 大字符串、不保留 family detection、不保留 SourceBundle 拼装。
- `include.py`：
  - 唯一承接 `@emit_c_include_impl(target="cuda_sm86")`。
  - include 文本只包含 `include/cuda_sm86/cuda_sm86.cuh` 与 generated entry header。
- `module.py`：
  - 唯一承接 `@emit_c_impl(ModuleOp, target="cuda_sm86")`。
  - 调用本 package 内部文件级 API 完成 detection 和 SourceBundle 生成。
  - 不直接包含三类 kernel 的大段 C++ source。
- `detect.py`：
  - 只从 lowered IR 实际 `kernel.*` op emit token 和函数类型摘要判断 family。
  - 不使用 entry name substring、函数名注释或 unknown fallback。
- `kernel/*.py`：
  - 每个文件只承接一个真实 `kernel.*` op emit 注册。
  - `kernel.img2col2d` 文件可承接 conv2d generated source，`kernel.reduce` 文件可承接 flash_attention generated source；不得新增 `kernel/conv2d.py` 或 `kernel/flash_attention.py` 伪 op 文件。
  - 不能导入其它 `kernel/_private` helper；跨文件共享逻辑只能使用本计划 `package-local 文件级 API exact set` 或同文件 helper，并列入文件级说明。若需要新增 exact set 之外的跨文件 API，必须转用户待确认。
  - `kernel/__init__.py` 只导入 op emitter 文件触发注册，保留空 `__all__`，不 re-export。
- `runtime.py` / `source_bundle.py`：
  - 承接 generated source 内部 namespace/header source 和 SourceBundle artifact 拼装。
  - generated source 通过 `include/cuda_sm86/cuda_sm86.cuh` 聚合的 `include/cuda_sm86/Arch.h` 使用 `cuda_sm86::detail::*` 后端 helper。
- `source/`：
  - 不存在；不得新增 `cuda_sm86/source/` 目录。

## 完成态定义
- `kernel_gen/dsl/gen_kernel/emit/cuda_sm86/__init__.py` 变为聚合入口，结构类似 `npu_demo/__init__.py`。
- root `__init__.py` 不再包含：
  - `_COMMON_CUDA_RUNTIME_SOURCE`
  - `_MATMUL_CUDA_SOURCE`
  - `_CONV2D_CUDA_SOURCE`
  - `_FLASH_ATTENTION_CUDA_SOURCE`
  - lowered IR family detection 细节
  - SourceBundle dict 拼装
- `cuda_sm86/module.py` 是唯一 `ModuleOp` handler 真源。
- 每个支持的真实 `kernel.*` op 都有对应 emit 注册；三类 generated source 不落在伪 op 文件中。
- `include/cuda_sm86/cuda_sm86.cuh` 是 aggregate header；`include/cuda_sm86/Arch.h` 承接 generated IR 所需 backend helper；两者均不暴露固定业务 kernel entry。
- 现有 CUDA emit / compile / runtime 行为不回退：
  - 9 demo CUDA runtime gate 仍按计划运行；若环境缺 `nvcc`，按现有 CUDA 计划环境阻塞规则记录，不得写通过。
  - 非 CUDA pytest 保持通过。
  - unknown / name-only / unsupported 负例仍通过。
- 文件级说明和 API 列表符合实现文件规范。
- 候选 diff 中 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md` 为空。

## 验收设计

### Diff 反推测试
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_package.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_cuda_sm86_strategy.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/cuda/test_cuda_sm86_kernel_demos_runtime.py -m cuda -rs`
- CUDA runtime gate 机械口径：
  - CUDA 环境存在时必须 9 demo 全部 `passed`。
  - 若出现 `skipped`、缺 `nvcc`、缺 CUDA device 或环境不满足，则本计划 execute 视为环境阻塞，不得进入 review；除非管理员 / 架构师单独记录环境裁定。
  - 任务记录必须摘录 `-rs` 摘要中的 passed / skipped 数量和 skip reason。

### 结构验收
- `test -f kernel_gen/dsl/gen_kernel/emit/cuda_sm86/module.py`
- `test -f kernel_gen/dsl/gen_kernel/emit/cuda_sm86/constants.py`
- `test -f kernel_gen/dsl/gen_kernel/emit/cuda_sm86/detect.py`
- `test -f kernel_gen/dsl/gen_kernel/emit/cuda_sm86/include.py`
- `test -f kernel_gen/dsl/gen_kernel/emit/cuda_sm86/source_bundle.py`
- `test -f kernel_gen/dsl/gen_kernel/emit/cuda_sm86/runtime.py`
- `test -f kernel_gen/dsl/gen_kernel/emit/cuda_sm86/kernel/binary_elewise.py`
- `test -f kernel_gen/dsl/gen_kernel/emit/cuda_sm86/kernel/exp.py`
- `test -f kernel_gen/dsl/gen_kernel/emit/cuda_sm86/kernel/img2col2d.py`
- `test -f kernel_gen/dsl/gen_kernel/emit/cuda_sm86/kernel/matmul.py`
- `test -f kernel_gen/dsl/gen_kernel/emit/cuda_sm86/kernel/reduce.py`
- `test ! -d kernel_gen/dsl/gen_kernel/emit/cuda_sm86/source`
- 可执行结构 gate：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 - <<'PY'
from __future__ import annotations
import ast
from pathlib import Path

root = Path("kernel_gen/dsl/gen_kernel/emit/cuda_sm86")
assert not (root / "source").exists()
init_text = (root / "__init__.py").read_text()
for token in (
    "_COMMON_CUDA_RUNTIME_SOURCE",
    "_MATMUL_CUDA_SOURCE",
    "_CONV2D_CUDA_SOURCE",
    "_FLASH_ATTENTION_CUDA_SOURCE",
    "kg_cuda_sm86_run_",
    "mma.sync",
    "__global__",
    "@emit_c_impl",
):
    assert token not in init_text, token

def decorator_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = decorator_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, ast.Call):
        return decorator_name(node.func)
    return ""

emit_files = []
include_files = []
for path in root.rglob("*.py"):
    text = path.read_text()
    tree = ast.parse(text, filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                if decorator_name(decorator).endswith("emit_c_impl"):
                    emit_files.append(path.as_posix())
                if decorator_name(decorator).endswith("emit_c_include_impl"):
                    include_files.append(path.as_posix())
assert emit_files == [
    "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/kernel/binary_elewise.py",
    "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/kernel/exp.py",
    "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/kernel/img2col2d.py",
    "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/kernel/matmul.py",
    "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/kernel/reduce.py",
    "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/module.py",
], emit_files
assert include_files == ["kernel_gen/dsl/gen_kernel/emit/cuda_sm86/include.py"], include_files

def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            prefix = "." * node.level
            if node.module:
                base = prefix + node.module
                parts = base.split(".")
                if len(parts) >= 3 and parts[-2] == "kernel":
                    modules.add(base)
                else:
                    modules.add(base)
            else:
                for alias in node.names:
                    modules.add(prefix + alias.name)
    return modules

detect_imports = imported_modules(root / "detect.py")
for forbidden in ("module", "source_bundle", "kernel", ".module", ".source_bundle", ".kernel"):
    assert forbidden not in detect_imports, (forbidden, detect_imports)

runtime_imports = imported_modules(root / "runtime.py")
for forbidden in ("module", "detect", "source_bundle", "kernel", ".module", ".detect", ".source_bundle", ".kernel"):
    assert forbidden not in runtime_imports, (forbidden, runtime_imports)

allowed_imports = {
    "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/__init__.py": {".include", ".kernel", ".module"},
    "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/constants.py": set(),
    "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/module.py": {".constants", ".detect", ".source_bundle"},
    "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/source_bundle.py": {".constants", ".detect", ".runtime", ".kernel.matmul", ".kernel.img2col2d", ".kernel.reduce"},
    "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/detect.py": {".constants"},
    "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/include.py": {".constants"},
    "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/runtime.py": {".constants"},
    "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/kernel/__init__.py": {".binary_elewise", ".exp", ".img2col2d", ".matmul", ".reduce"},
    "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/kernel/binary_elewise.py": {"..constants"},
    "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/kernel/exp.py": {"..constants"},
    "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/kernel/img2col2d.py": {"..constants", "..detect"},
    "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/kernel/matmul.py": {"..constants", "..detect"},
    "kernel_gen/dsl/gen_kernel/emit/cuda_sm86/kernel/reduce.py": {"..constants", "..detect"},
}
for rel, allowed in allowed_imports.items():
    path = Path(rel)
    imports = {
        item for item in imported_modules(path)
        if item.startswith(".") or item.startswith("kernel_gen.dsl.gen_kernel.emit.cuda_sm86")
    }
    assert imports <= allowed, (rel, imports, allowed)

for package_init in (root / "__init__.py", root / "kernel" / "__init__.py"):
    tree = ast.parse(package_init.read_text(), filename=str(package_init))
    exports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets):
            exports.append(node.value)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "__all__":
            exports.append(node.value)
    assert exports, f"missing __all__: {package_init}"
    assert isinstance(exports[-1], ast.List) and not exports[-1].elts, f"__all__ must be empty list: {package_init}"

test_root = Path("test")
internal_prefix = "kernel_gen.dsl.gen_kernel.emit.cuda_sm86"
internal_children = {"constants", "detect", "module", "runtime", "source_bundle", "kernel"}
for test_file in test_root.rglob("*.py"):
    tree = ast.parse(test_file.read_text(), filename=str(test_file))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for module in imported_modules(test_file):
                assert not module.startswith("kernel_gen.dsl.gen_kernel.emit.cuda_sm86."), (test_file, module)
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.startswith(internal_prefix + "."):
                raise AssertionError((test_file, module))
            if module == internal_prefix:
                for alias in node.names:
                    assert alias.name not in internal_children, (test_file, module, alias.name)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            forbidden = "kernel_gen.dsl.gen_kernel.emit.cuda_sm86."
            assert forbidden not in node.value, (test_file, node.value)
PY
```

### 静态边界
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/dsl/gen_kernel/emit/cuda_sm86/*.py kernel_gen/dsl/gen_kernel/emit/cuda_sm86/kernel/*.py`
- `git diff --check`
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md` 预期无输出。
- `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md` 预期无输出。
- ignored / untracked 敏感资产不要求主仓基线为空；execute 开始前必须记录基线快照：
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md > /tmp/cuda_sm86_emit_sensitive.before`
- execute / review / archive_acceptance 结束前必须复跑并与基线一致：
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md > /tmp/cuda_sm86_emit_sensitive.after`
  - `diff -u /tmp/cuda_sm86_emit_sensitive.before /tmp/cuda_sm86_emit_sensitive.after`
- 若基线快照与结束快照不同，必须分类说明；未经用户 / 架构授权不得把差异写入候选。
- 计划文件跟踪验收：
  - `git ls-files --error-unmatch ARCHITECTURE/plan/cuda_sm86_emit_package_structure_refactor_green_plan.md`
- 扫描本轮新增 / 修改文件：
  - 禁止 `hasattr/getattr/callable(getattr)` ctx 能力探测。
  - 禁止非装饰器场景嵌套函数。
  - 禁止测试直连 `cuda_sm86` package 内部非公开 helper。
  - 新增 / 修改 private callable 必须满足 5 行有效代码，不得 private 调 private。

### 合同验收
- 本计划不列 `expectation/` 为必过合同验收资产。
- 不修改、不复制、不新增 `expectation/`。

## 计划内小任务

### S1. 固定重构 spec 与文件级说明
- 为什么做：先让执行人知道本轮按用户最新口径对齐 `npu_demo` 风格，同时补齐 include 的 IR API 合同。
- 做什么：更新 `spec/dsl/gen_kernel/emit/cuda_sm86.md` 与 `spec/include/cuda_sm86/cuda_sm86.md`，写清 package root 聚合、`include.py`、`module.py` handler 真源、per-kernel-op emit 子模块、SourceBundle 结构不变，以及 `cuda_sm86.cuh` aggregate / `Arch.h` 后端实现层边界。
- 不做什么：不改 CUDA kernel 算法，不扩大支持范围，不改 expectation。
- 怎么验收：spec 中有目标结构、非目标、包外 Python API 不变说明和 include 分层 API 列表；`git diff --check` 通过。
- 卡住问谁：公开 API 或支持范围问用户；结构边界问架构师；流程状态问管理员。

详细字段：
- 模块范围：`spec/dsl/gen_kernel/emit/cuda_sm86.md`、`spec/include/cuda_sm86/cuda_sm86.md`、必要的 test docstring。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`TODO.md`、`DONE.md`。
- 合同真源：本计划 > `spec/dsl/gen_kernel/emit/cuda_sm86.md` > pytest > 当前实现。
- 执行步骤：
  - 将 spec 中当前单文件 backend 描述改为 package backend 描述。
  - 补目标结构表。
  - 写明 `cuda_sm86/__init__.py` 不承载业务逻辑。
  - 写明 `include/cuda_sm86/cuda_sm86.cuh` 只做 aggregate，`include/cuda_sm86/Arch.h` 承接 IR emit 真实依赖的 backend helper，不承接固定业务 kernel entry。
- 验收与记录：
  - 记录包外 Python API 未变，include 分层边界变更有用户确认来源。
  - 记录无 expectation 改动。

### S2. 拆分 `cuda_sm86` emit package
- 为什么做：消除 root `__init__.py` 过大和职责混杂，让结构对齐其它 target。
- 做什么：把当前 root 文件中的 detection、SourceBundle、runtime、per-kernel-op emit 和三类 generated source 移到目标子模块。
- 不做什么：不改变 generated source 行为和稳定错误语义。
- 怎么验收：结构验收命令通过；`__init__.py` 不再包含 source 大模板或 handler。
- 卡住问谁：拆分后发现需要新增公开 API 时问用户；具体模块边界问架构师。

详细字段：
- 模块范围：`kernel_gen/dsl/gen_kernel/emit/cuda_sm86/**`。
- 最小闭环：
  - `emit_c_impl(ModuleOp, target="cuda_sm86")` 仍能自动加载。
  - 三类 demo source 生成结果保持语义一致。
  - unknown / unsupported 负例保持失败。
- 执行步骤：
  - 将 `__init__.py` 改为聚合导入。
  - 新建 `module.py` 并迁移 handler。
  - 新建 `detect.py` 并迁移 family 检测。
  - 按 exact fields 实现 `CudaSm86KernelFamily` 与 `CudaSm86ModuleSummary`，并只在 package 内部使用。
  - 新建 `source_bundle.py` 和 `runtime.py`。
  - 新建 `include.py` 注册 target include。
  - 新建 `kernel/` package 及 `binary_elewise.py`、`exp.py`、`img2col2d.py`、`matmul.py`、`reduce.py` 五个真实 op emit 文件；不得新建 `source/` 目录。
  - 删除 root 中旧大字符串和直接拼装逻辑。
- 验收与记录：
  - 记录删掉的 root 旧逻辑。
  - 记录各新文件职责。

### S3. 更新 pytest 覆盖结构和行为不变
- 为什么做：证明这次是结构重构，不是功能偷换。
- 做什么：补 / 更新 `test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py`，同时锁结构和行为。
- 不做什么：测试不得 direct call 非公开 helper；只能通过公开 emit / gen_kernel / ExecutionEngine 路径验证。
- 怎么验收：CUDA emit pytest、package pytest、compile strategy pytest 通过；CUDA runtime gate 必须真实运行 9 demo 并通过。若 skipped、缺 `nvcc` 或缺 CUDA device，则本计划 execute 视为环境阻塞，不得进入 review；除非管理员 / 架构师单独记录环境裁定。
- 卡住问谁：测试必须直连内部 helper 才能写时问架构师；CUDA 环境缺失问管理员。

详细字段：
- 测试范围：
  - root `__init__.py` 结构负例。
  - `module.py` handler 唯一性。
  - `include.py` include 注册唯一性。
  - `kernel/*.py` 每个真实 op 对应一个 emit。
  - `target="cuda_sm86"` 自动加载不回退。
  - lowered IR family source 差异仍存在。
  - unknown / name-only module 稳定失败。
- 禁止测试导入 / 调用：
  - `kernel_gen.dsl.gen_kernel.emit.cuda_sm86.module`
  - `kernel_gen.dsl.gen_kernel.emit.cuda_sm86.detect`
  - `kernel_gen.dsl.gen_kernel.emit.cuda_sm86.source_bundle`
  - `kernel_gen.dsl.gen_kernel.emit.cuda_sm86.runtime`
  - `kernel_gen.dsl.gen_kernel.emit.cuda_sm86.kernel.*`
- 测试必须通过公开 `emit_c` / `gen_kernel` / `ExecutionEngine` 路径观察行为。
- 验收命令：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_package.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_cuda_sm86_strategy.py`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/cuda/test_cuda_sm86_kernel_demos_runtime.py -m cuda -rs`
  - 任务记录必须摘录 CUDA runtime gate 的 passed / skipped 数量；若 skipped、缺 `nvcc` 或缺 device，则按环境阻塞处理，不得写成通过。

### S4. Diff 反推、静态边界和敏感目录门禁
- 为什么做：防止重构中引入跨文件私有调用、ctx 能力探测、嵌套函数或未授权敏感目录改动。
- 做什么：按实际 diff 反推 pytest / py_compile / static scan / sensitive gate。
- 不做什么：不把 CUDA runtime skip 写成通过；不把 expectation 作为替代测试。
- 怎么验收：计划列命令和 diff 反推命令均记录 exit code；敏感目录空 diff。
- 卡住问谁：环境缺 `nvcc` 问管理员或架构师裁定；发现现有测试不足问 review。

详细字段：
- 必跑：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/dsl/gen_kernel/emit/cuda_sm86/*.py kernel_gen/dsl/gen_kernel/emit/cuda_sm86/kernel/*.py`
  - `git diff --check`
  - `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`
  - `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`
  - 执行前后分别保存 `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md` 快照，并用 `diff -u` 证明一致；不得要求 ignored 基线为空。
  - `git ls-files --error-unmatch ARCHITECTURE/plan/cuda_sm86_emit_package_structure_refactor_green_plan.md`
  - 本计划 `验收设计` 中列出的 pytest。
- 静态扫描：
  - 扫描本轮新增 / 修改文件的 `hasattr/getattr/callable(getattr)`。
  - 扫描嵌套 `def`。
  - 扫描 `object` 参数注解。
  - 扫描测试 direct import / call `cuda_sm86` package 内部 helper。

## 迭代审阅记录

### Draft 0：架构主线草案
- 标准包：根 `AGENTS.md`、`agents/standard/计划书标准.md`、`agents/standard/审查规范.md`、当前 `cuda_sm86` 单文件实现、`npu_demo` target package 结构、当前计划全文。
- 严格通过口径：
  - 必须对齐“像其它 target”结构，不允许继续单文件堆模板。
  - 初版不得新增公开 API 或 expectation；execute 返工中用户已单独确认 `include/cuda_sm86` 按 IR 表达涉及 API，并进一步要求按 arch 第一版分层收口。
  - 必须证明行为不变和结构真的迁出 root `__init__.py`。
  - 仍有可维护性、测试有效性或边界完整性问题不得通过。
- 主线处理：
  - 已将目标结构写为 `module/detect/source_bundle/runtime/kernel/*`。
  - 已将 `__init__.py` 收窄为聚合入口。
  - 初版已写明 no public API change、no expectation、no include API change；execute 返工中用户确认后改为包外 Python API 不变、include 按 arch 第一版分层并由后端实现层承接 IR 真实依赖。
- 状态：等待 Codex subagent strict review。

### subagent strict review 收敛
- 已发起对象：
  - Codex subagent `Parfit`：只读复核计划流程、旧 tmux 角色互评残留、结构/API/验收边界。
  - Codex subagent `Franklin`：只读复核工程可执行性、结构 AST gate、CUDA runtime hard gate、gitignored plan 风险。
  - Codex subagent `Faraday`：只读复核架构/API 边界、package-internal API、unknown/name-only failure 与 9 demo gate。
- 第一轮回执：
  - `Parfit`：最小需改项。
  - `Franklin`：最小需改项。
  - `Faraday`：最小需改项。
- `Parfit` 问题与主线处理：
  - 问题：计划仍残留旧 tmux 角色互评 / 等待回执表述，且守护最终检验未发起。处理：已写明旧 tmux 角色请求只作历史背景，不作为 active gate；active gate 为 Codex subagent strict review 持续收敛，守护最终检验仍未发起且通过前不得下发。
  - 问题：package-local 文件级 API 允许跨文件调用但又声明公开 API 不变，边界不清。处理：已明确这些名称是用户“跟其它 target 差不多”结构授权下的 package-local 文件级 API exact set，只允许 `cuda_sm86` 包内按依赖方向调用，写入文件级 API 列表，不进入包外公开 API / `__all__` / public path matrix，测试不得直连。
  - 问题：结构 gate 使用全文禁词检查依赖，易误伤 / 漏检。处理：已改为 AST import graph 检查，并补 decorator name / attribute 双识别和测试文件内部 helper direct import / string path gate。
  - 问题：S3 CUDA runtime gate 弱于全局 hard gate。处理：已同步 S3，明确 skipped、缺 `nvcc`、缺 device 均为环境阻塞，不得进入 review，除非管理员 / 架构师裁定。
- `Parfit` 第二轮问题与主线处理：
  - 问题：目标结构仍有“非公开文件级 API”措辞，与 package-local exact set 冲突。处理：已改为跨文件共享逻辑只能使用本计划 exact set 或同文件 helper；新增 exact set 之外跨文件 API 必须转用户待确认。
  - 问题：`constants.py` 固定为目标结构但缺存在性 gate 和依赖规则。处理：已补 `test -f constants.py`，将 `.constants` / `..constants` 纳入允许依赖方向，并固定 `constants.py` 只承载四个 exact string constants。
  - 问题：S3 验收命令未列 CUDA runtime pytest。处理：已补 `test/cuda/test_cuda_sm86_kernel_demos_runtime.py -m cuda -rs`，并要求记录 passed / skipped 数量和环境阻塞口径。
- `Parfit` 第三轮问题与主线处理：
  - 问题：正文允许依赖方向未同步 `constants.py`，但 AST gate 允许 `.constants` / `..constants`。处理：已在正文补齐 `constants.py`、`module.py`、`source_bundle.py`、`runtime.py`、`kernel/*.py` 的 exact 依赖规则，与 AST gate 保持一致。
  - 问题：正文仍写 root `__init__.py` 必要时可导入 `kernel` package，但 AST gate 只允许 `.module`。处理：已删除该表述，固定 root `__init__.py` 只导入 `module`。
  - 问题：测试直连内部模块 gate 漏掉 `from kernel_gen.dsl.gen_kernel.emit.cuda_sm86 import detect/module/...`。处理：已在 AST gate 中展开 `ImportFrom` alias，禁止测试从 `cuda_sm86` root 导入 `constants/detect/module/runtime/source_bundle/kernel`。
- `Franklin` 问题与主线处理：
  - 问题：计划文件在 ignored `ARCHITECTURE/plan/` 下，可能不进入可追踪 diff / commit。处理：已补计划文件跟踪要求，进入下发 / merge 前必须 `git add -f` 并用 `git ls-files --error-unmatch` 验收。
  - 问题：敏感目录 `git status --ignored` 在干净基线下会有 ignored 噪声，要求空输出不可复跑。处理：已改为 tracked / cached diff 必须空；ignored / untracked 采用 execute 前后基线快照一致性门禁。
  - 问题：package-internal API 分类与 AGENTS 边界冲突。处理：同 Parfit 第 2 项，收口为 package-local 文件级 API exact set，不作为包外公开 API，禁止测试 / 包外直连。
  - 问题：结构 AST gate 脆弱、`constants.py` 可选性不清。处理：已固定 `constants.py` 为必建共享常量模块，并改 AST gate 为 import graph / decorator / test path 检查。
  - 问题：计划流程尚未收敛。处理：保持不可下发，等待所有 Codex subagent 无阻断后再请求守护最终检验。
- `Franklin` 第二轮问题与主线处理：
  - 问题：`constants.py` 已固定为目标结构和共享常量模块，但结构验收和 AST allowed imports 未覆盖。处理：已补 `test -f constants.py`，并在 AST gate 中加入 `constants.py: set()`，允许需要共享常量的包内模块导入 `.constants` / `..constants`，同时 `constants.py` 不反向导入包内模块；`constants.py` exact set 固定为 target/source artifact/header artifact/runtime entry 四个字符串常量。
- `Faraday` 问题与主线处理：
  - 问题：结构 / API 边界 gate 仍不可靠，依赖检查应覆盖全部文件并支持 `__all__: list[str] = []`。处理：已改为 AST import-edge gate，覆盖 `detect.py`、`runtime.py`、`source_bundle.py`、`kernel/*.py` 的允许依赖方向；decorator 支持 `Name` / `Attribute`；`__all__` 同时支持 `Assign` / `AnnAssign`，并断言值是真正空 list。
  - 问题：subagent 收敛尚未完成。处理：保持不可下发；本轮修订后必须基于最新文本发起下一轮 Codex subagent strict review，全部无阻断后才请求守护最终检验。
- `Faraday` 第二轮问题与主线处理：
  - 问题：`constants.py` 必建但缺结构验收和允许依赖方向。处理：同 Franklin 第二轮，已补 `test -f constants.py`、`.constants` / `..constants` 依赖规则和 exact constants API set。
- `Faraday` 第三轮问题与主线处理：
  - 问题：`constants.py` 可跨文件导入，但 package-local exact set 未包含常量名。处理：已将 `CUDA_SM86_TARGET_NAME`、`CUDA_SM86_KERNEL_SOURCE_ARTIFACT`、`CUDA_SM86_GENERATED_ENTRY_HEADER_ARTIFACT`、`CUDA_SM86_RUNTIME_ENTRY_NAME` 写入 exact set，并禁止 `constants.py` 放大段源码模板、handler、family detection 或 SourceBundle 拼装逻辑。
- 最后一轮 Codex subagent strict review 结论：
  - `Parfit`：通过。
  - `Franklin`：通过。
  - `Faraday`：通过。
  - 收敛状态：所有已发起 Codex subagent strict review 均无阻断、无最小需改项、无待确认项。
- 旧流程纠偏记录：
  - 早期曾误用 tmux 角色 `提莫炖蘑菇` / `金铲铲大作战` / `小李飞刀` 做互评请求；该路径不作为本计划 active gate。
  - 已将 active gate 收回到 Codex subagent strict review 持续收敛；tmux 角色回包最多作为历史背景，不替代 Codex subagent 审阅和守护最终检验。
- 当前状态：Codex subagent strict review 已收敛；等待 `守护最好的爱莉希雅` 守护最终检验。
- 下发条件：所有已发起或计划要求的 Codex subagent strict review 均无阻断、无最小需改项、无待确认项，并由 `守护最好的爱莉希雅` 守护最终检验通过。

### 守护最终检验
- 结论人：`守护最好的爱莉希雅`
- 状态：通过，可下发。
- 只读核对结论：
  - 流程已按最新 `AGENTS.md` 收口：Codex subagent strict review 持续收敛，`Parfit` / `Franklin` / `Faraday` 最后一轮均通过；守护最终检验是当前 active gate。
  - `cuda_sm86` 目标结构清楚：`module.py` / `detect.py` / `source_bundle.py` / `runtime.py` / `kernel/{matmul,conv2d,flash_attention}.py` / `constants.py` 边界明确。
  - package-local exact API、依赖方向、`__all__` 为空、测试不得直连内部 helper 的门禁可执行。
  - CUDA runtime gate 明确：`skipped`、缺 `nvcc`、缺 CUDA device 都是环境阻塞，不得写成通过。
  - 禁止修改面清楚：`expectation/.skills/agents/standard/AGENTS.md/TODO.md/DONE.md` 空 diff；计划文件因 `ARCHITECTURE/plan/` 被 ignore，已写 `git add -f` 与 `git ls-files --error-unmatch` 跟踪要求。
- 最小阻断项：无。

## 计划书入档验收 / 复验 / 修复复核记录
- 结论人：待定。
- 验证基线：待 execute 后记录。
- 执行目录：待 execute worktree。
- 合同验收摘要：本计划无必过 `expectation`。
- 最小阻断项或通过摘要：待定。

## 待确认项
- 当前无用户待确认项。
- 若 subagent review 认为以下任一项会改变公开 API 或完成态，必须转为用户待确认：
  - 是否允许新增 `cuda_sm86` 包外公开 helper。
  - 是否允许新增 include/api 层跨 target 公开 API。
  - 是否允许改变 unknown / unsupported 稳定错误文本。
  - 是否允许缩小 9 demo runtime gate。

## 用户确认与协同约束
- 用户确认方向：`cuda_sm86` emit 结构应跟其它 target 类似。
- 本计划只做结构重构，不改变 CUDA 后端公开行为。
- 下发前必须完成 Codex subagent strict review 持续收敛和守护最终检验。
- execute 候选 diff 中 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md` 必须为空。
