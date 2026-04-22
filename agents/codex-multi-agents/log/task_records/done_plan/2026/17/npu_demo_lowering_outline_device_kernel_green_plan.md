# npu_demo_lowering_outline_device_kernel_green_plan.md

## 文档信息

- 创建者：`Codex`
- 最后一次更改：`大闸蟹`
- 最近一次更新时间：`2026-04-22 00:00:00 +0800`
- 目标 `spec`：
  - [`spec/target/registry.md`](../../spec/target/registry.md)
  - [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
  - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
  - [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
  - [`spec/pass/inline.md`](../../spec/pass/inline.md)（新增或补齐）
  - [`spec/pass/attach_arch_information.md`](../../spec/pass/attach_arch_information.md)（新增）
  - [`spec/pass/outline_device_kernel.md`](../../spec/pass/outline_device_kernel.md)
  - [`spec/pass/pipeline/npu_demo_lowering.md`](../../spec/pass/pipeline/npu_demo_lowering.md)
  - [`spec/tools/dsl_run.md`](../../spec/tools/dsl_run.md)
- 目标 `API`：
  - [`kernel_gen/target/registry.py`](../../kernel_gen/target/registry.py)
  - [`kernel_gen/target/targets`](../../kernel_gen/target/targets)
  - [`kernel_gen/dsl/mlir_gen/emit/core.py`](../../kernel_gen/dsl/mlir_gen/emit/core.py)
  - [`kernel_gen/passes/inline.py`](../../kernel_gen/passes/inline.py)（新增或补齐）
  - [`kernel_gen/passes/attach_arch_information.py`](../../kernel_gen/passes/attach_arch_information.py)（新增）
  - [`kernel_gen/passes/outline_device_kernel.py`](../../kernel_gen/passes/outline_device_kernel.py)
  - [`kernel_gen/passes/pipeline/npu_demo_lowering.py`](../../kernel_gen/passes/pipeline/npu_demo_lowering.py)
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
  - [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)
  - [`kernel_gen/tools/dsl_run.py`](../../kernel_gen/tools/dsl_run.py)
- 目标 `test`：
  - [`test/target/test_target_registry.py`](../../test/target/test_target_registry.py)
  - [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py)
  - [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py)
  - [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)
  - [`test/pass/test_pipeline_npu_demo_lowering.py`](../../test/pass/test_pipeline_npu_demo_lowering.py)
  - [`test/pass/outline_device_kernel/test_outline_device_kernel.py`](../../test/pass/outline_device_kernel/test_outline_device_kernel.py)
  - [`test/tools/test_dsl_run.py`](../../test/tools/test_dsl_run.py)
- 目标 `验收资产`：
  - [`expectation/pass/outline_device_kernel`](../../expectation/pass/outline_device_kernel)
  - [`expectation/tools/dsl_run`](../../expectation/tools/dsl_run)
  - [`expectation/execute_engine/npu_demo/default`](../../expectation/execute_engine/npu_demo/default)
- 目标 `功能实现`：
  - [`kernel_gen/target/registry.py`](../../kernel_gen/target/registry.py)
  - [`kernel_gen/target/targets`](../../kernel_gen/target/targets)
  - [`kernel_gen/dsl/mlir_gen/emit/core.py`](../../kernel_gen/dsl/mlir_gen/emit/core.py)
  - [`kernel_gen/passes/inline.py`](../../kernel_gen/passes/inline.py)
  - [`kernel_gen/passes/attach_arch_information.py`](../../kernel_gen/passes/attach_arch_information.py)
  - [`kernel_gen/passes/outline_device_kernel.py`](../../kernel_gen/passes/outline_device_kernel.py)
  - [`kernel_gen/passes/pipeline/npu_demo_lowering.py`](../../kernel_gen/passes/pipeline/npu_demo_lowering.py)
  - [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)
  - [`kernel_gen/tools/dsl_run.py`](../../kernel_gen/tools/dsl_run.py)

## 任务清单

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `S1 = T-20260422-2185fc33` | 无 | `wt-20260422-npu-demo-lowering-outline-s1` | `agents/codex-multi-agents/log/task_records/2026/17/20260422-npu-demo-lowering-outline-s1.md` |
| `S2 = T-20260422-ee586cde` | `S1` | `wt-20260422-npu-demo-lowering-outline-s2` | `agents/codex-multi-agents/log/task_records/2026/17/20260422-npu-demo-lowering-outline-s2.md` |
| `S3 = T-20260422-2d1fa768` | `S2` | `wt-20260422-npu-demo-lowering-outline-s3` | `agents/codex-multi-agents/log/task_records/2026/17/20260422-npu-demo-lowering-outline-s3.md` |
| `S4 终验修复 = T-20260422-bd36a572` | `S3` | `wt-20260422-npu-demo-lowering-outline-final-repair` | `agents/codex-multi-agents/log/task_records/2026/17/20260422-npu-demo-lowering-outline-final-repair.md` |

## 评审摘要

- 评审结论：`通过`
- 评审人：`守护最好的爱莉希雅 / 大闸蟹 / 提莫炖蘑菇 / 不要啊教练`
- 结论摘要：`守护最好的爱莉希雅已通过；大闸蟹复评通过；提莫炖蘑菇指出的 only-kernel=true 表述歧义已统一为不公开支持且传入稳定失败；不要啊教练从 fail-fast 边界给出通过。当前协同记录已补齐，默认 npu-demo-lowering 覆盖 execute_engine/default、npu_demo.txt 唯一 target 数据源、S1/S2/S3 拆分与依赖均可执行，可进入任务创建。`

## 终验 / 复验 / 修复复核记录

- 结论人：`不适用`
- 结论：`尚未进入终验`
- 验证基线：`终验时以对应任务 worktree 根目录为执行目录，并设置 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate；若任务已合并，以最新主线提交为验证基线。`
- 最小阻断项或通过摘要：`不适用`
- 是否已创建修复任务：`不适用`
- 修复任务创建人：`不适用`
- 另一位架构师补充重点：`不适用`

### 大闸蟹最终验收复核（2026-04-22）

- 结论人：`大闸蟹`
- 结论：`不通过`
- 验证基线：`origin/main@e83e8aece39d768ccb52e0142e5b2891d651d49b`
- 执行目录：`/home/lfr/kernelcode_generate`
- 主目录同步检查：`已在 /home/lfr/kernelcode_generate 执行 git fetch --prune；主目录 HEAD 与 origin/main 均为 e83e8aece39d768ccb52e0142e5b2891d651d49b，tracked 文件已处于最新主线现场，仅存在无关未跟踪 worktree 目录，因此直接在主目录执行终验。`
- 全量 expectation 合同验收摘要：`find expectation -name __main__.py 发现 42 个入口；expectation 根递归入口 discover_case_modules 发现 194 个实际 case 模块；已执行 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation，退出码 1，全量合同验收失败。`
- 最小阻断项：`全量 expectation 本轮失败 7 个模块：expectation.dsl.mlir_gen.dialect.dma.copy exited 1；expectation.dsl.mlir_gen.dialect.nn.element_unary.tanh exited -11；expectation.execute_engine.npu_demo.default.add/matmul/mul/sub 均 exited 1；expectation.tools.dsl_run.add exited 1。npu_demo execute/dsl_run 失败的直接编译错误已复现为生成源码中 host wrapper 调用 add_kernel_device 时该 device 函数尚未声明，g++ 报 add_kernel_device was not declared in this scope；同类 wrapper/device 顺序问题会阻断 add/mul/sub/matmul 正向执行链。`
- 是否满足归档前置条件：`否`
- 归档处理：`不推进归档；按管理员规则由守护最好的爱莉希雅建立唯一修复任务。`

### 当前唯一最终验收修复任务（2026-04-22）

- 任务号：`T-20260422-bd36a572`
- worktree：`wt-20260422-npu-demo-lowering-outline-final-repair`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/17/20260422-npu-demo-lowering-outline-final-repair.md`
- 任务类型：`build`
- 创建原因：`最新主线 origin/main@e83e8aece39d768ccb52e0142e5b2891d651d49b 最终验收不通过，全量 expectation 合同验收存在 npu_demo lowering / codegen / dsl_run 相关失败。`
- 最小修复目标：`收口全量 expectation 合同验收失败，包括 expectation.dsl.mlir_gen.dialect.dma.copy、expectation.dsl.mlir_gen.dialect.nn.element_unary.tanh exit=-11、expectation.execute_engine.npu_demo.default add/matmul/mul/sub、expectation.tools.dsl_run.add。重点修复 npu_demo execute/dsl_run 生成 C++ host wrapper 先调用 add_kernel_device，但 device 函数无前置声明且定义在后导致编译失败的问题。`
- 记录要求：`build 记录必须包含 Diff 反推自测；review 记录必须包含 Diff 反推审查；expectation 作为合同验收资产单列，不得替代 diff 反推测试。`
- 任务依赖说明：`S3 已完成并进入 DONE，任务脚本不接受 DONE 任务作为 TODO 依赖项，因此 TODO 中依赖列为空；本计划正文明确记录该任务是 S3 终验后的当前唯一修复任务。`

## 输入摘要

- 目标：`npu-demo-lowering` 默认生成并执行 npu demo launch wrapper；launch extent 当前固定使用 `npu_demo.txt` 中的 `1, 1, 1`，但必须走 target registry 查询链路，不能写死在 pass 或 codegen 中。
- 不做：不公开支持 `only-kernel=true`；传入该 option 必须稳定失败；不保留绕开 IR outline 的公开 pipeline 选项；不让 `gen_kernel` 继续使用 add/barrier 冻结骨架或针对某个 case 的特殊 emitter。
- 当前痛点：target 注册里存在 Python 内置 `npu_demo` 固定模板；`gen_kernel` 仍有 `npu_demo::launch<1, 4, 1>` 和 add/barrier 受控子集特化；`dsl_run` 的 npu_demo wrapper 识别过窄，容易 fallback 到首函数。
- 完成后最想看到的例子：`dsl_run(..., "npu-demo-lowering", EmitCContext(target="npu_demo"))` 经过 `inline -> decompass -> lower-nn -> symbol-loop-hoist -> attach-arch-information -> outline-device-kernel`，生成 wrapper 调用 `npu_demo::launch<1, 1, 1>(device, ...)`，并真实编译执行。

## 计划目标

- 启用 target registry + `npu_demo.txt`：npu demo 的 arch 能力和硬件参数从 target 文件加载，当前 `block_num/thread_num/subthread_num` 写成 `1/1/1`，后续只改 target 文件或 target 查询策略即可恢复真实硬件值。
- 新增或补齐 `attach-arch-information` pass：它只负责从 target 查询 launch extent 并附着 `launch_block / launch_thread / launch_subthread`，不做 outline、不猜测 target、不写死 `1/1/1`。
- 收口 `npu-demo-lowering` 默认 pipeline：固定执行 `inline -> decompass -> lower-nn -> symbol-loop-hoist -> attach-arch-information -> outline-device-kernel`，不再公开支持 `only-kernel=true`，传入该 option 必须稳定失败。
- 泛化 `gen_kernel` 的 launch module codegen：根据 IR 中的 `arch.launch` 和 target registry 生成源码，删除 frozen add+barrier 骨架、`launch<1,4,1>` 限制和只支持 `lhs/rhs/out` 的签名限制。
- 泛化 `dsl_run` 入口选择：npu demo module 以唯一 `arch.launch` wrapper 作为入口；存在 helper 函数时也能工作；wrapper codegen 失败必须失败，不能 fallback 到首个普通函数。
- 保留 `i64` 修复作为前置闭环：execute expectation 随机 dtype 可以包含 `i64`，不能通过缩小随机池绕过。

## 当前基线

- 当前公开合同：`expectation/pass/outline_device_kernel` 锁定 standalone outline pass 消费显式 launch attrs；`expectation/tools/dsl_run` 和 `expectation/execute_engine/npu_demo/default` 锁定 npu demo 正向执行链路。
- 当前公开 API：`build_npu_demo_lowering_pipeline()` 目前只构造 `DecompassPass -> NnLoweringPass -> SymbolLoopHoistPass`；`dsl_run` 接受 pipeline 名或 `PassManager`；target registry 支持 `load_targets(Path(...))` 和 `get_target_hardware(target, key)`。
- 当前实现入口：`kernel_gen/target/registry.py` 仍硬编码 `_DEFAULT_NPU_DEMO_*` 并在 import 时注册；`kernel_gen/dsl/gen_kernel.py` 中存在 `npu_demo::launch<1, 4, 1>`、add+barrier 固定 body、三参数 wrapper 校验；`kernel_gen/tools/dsl_run.py` 只在 `len(func_ops) == 2` 时尝试 wrapper module codegen。
- 当前测试与验收资产：`test/target/test_target_registry.py` 覆盖 target registry；`test/pass/test_pipeline_npu_demo_lowering.py` 覆盖 pipeline 顺序；`test/dsl/test_gen_kernel.py` 和 `test/tools/test_dsl_run.py` 覆盖源码生成与工具执行；execute expectation 的正向主链在 `expectation/execute_engine/npu_demo/default`。
- 当前缺口或失败点：target 数据源分叉；launch extent 写死在 codegen；codegen 对 npu demo launch 只支持历史 add/barrier 子集；`dsl_run` 入口选择依赖函数数量；`only-kernel` 方案与当前用户口径冲突；`i64` 链路仍需要修复。

## 合同真源顺序

- `expectation/execute_engine/npu_demo/default > spec/tools/dsl_run.md + spec/pass/pipeline/npu_demo_lowering.md + spec/dsl/gen_kernel.md > test/tools/test_dsl_run.py + test/dsl/test_gen_kernel.py > 当前实现`
- `expectation/pass/outline_device_kernel > spec/pass/outline_device_kernel.md + spec/pass/attach_arch_information.md > test/pass/outline_device_kernel/test_outline_device_kernel.py + test/pass/test_pipeline_npu_demo_lowering.py > 当前实现`
- `spec/target/registry.md + kernel_gen/target/targets/npu_demo.txt > test/target/test_target_registry.py > kernel_gen/target/registry.py`
- `expectation/execute_engine/npu_demo/default > spec/dsl/emit_mlir.md + spec/dsl/mlir_gen.md > test/dsl/test_emit_mlir.py + test/dsl/test_mlir_gen.py > 当前实现`

## 方案比较与选型

- 不采用方案：继续在 registry.py 内置 `_DEFAULT_NPU_DEMO_HARDWARE` 和 `_DEFAULT_NPU_DEMO_SUPPORTED_OPS`。
- 不采用原因：target 信息会散落在 Python 常量、spec、codegen 和 expectation 中；后续改真实硬件值时必须多点修改，违背“从 target 获取”的要求。
- 采用方案：target 文件是 npu demo target 的真源；registry import 时只能加载 target 文件或提供显式加载入口，不再把 npu demo 硬件值写在代码实现里。
- 最小公开接口：`load_targets(Path("kernel_gen/target/targets"))` 后，`get_target_hardware("npu_demo", "thread_num") == 1`。

- 不采用方案：保留 `only-kernel=true`，由 dsl_run 在运行时合成 wrapper。
- 不采用原因：用户已取消该 option；同时 kernel-only 运行要正确模拟 `KernelContext`，最终仍需要 launch wrapper，保留公开开关只会制造两套入口合同。
- 采用方案：默认 `npu-demo-lowering` 一条路生成 IR host wrapper + device body；旧 `kernel_only` expectation 不再作为 `npu-demo-lowering` 正向必过合同。
- 最小公开接口：`build_registered_pipeline("npu-demo-lowering")` 无 `only-kernel` 公开选项；传入 `only-kernel` 必须报未知 option。

- 不采用方案：在 `gen_kernel` 里保留 add/barrier 特化 emitter，并在特殊 case 上拼出固定源码。
- 不采用原因：这会让源码输出绑定某个测试骨架，`slice/store/add`、`for` 循环、matmul、更多 arch op 都无法按 IR 自然扩展。
- 采用方案：`gen_kernel` 对 launch module 使用通用函数 emitter；device C++ 函数注入 `npu_demo::KernelContext& ctx`，body 仍按 IR op 逐条发射。
- 最小公开接口：任意唯一 `arch.launch` wrapper module 可生成 `npu_demo::launch<B, T, S>(device, ...)`，其中 `B/T/S` 来自 `arch.launch` op。

- 不采用方案：`dsl_run` 只在 module 恰好两个函数时识别 wrapper。
- 不采用原因：一旦 inline 未消除 helper、后续引入库函数或有多个 private helper，函数数量就不再等于 2；此时 fallback 到首函数会执行错误入口。
- 采用方案：按唯一 `arch.launch` wrapper 选择入口；helper 函数数量不参与入口判断。
- 最小公开接口：存在唯一 `arch.launch` wrapper 时，`DslRunResult.entry_name` 必须等于 wrapper `sym_name`。

## 公开 API 设计

### Target Txt 与 Registry

- 公开入口：`kernel_gen.target.registry.load_targets(directory)`、`get_target_hardware(target, key)`、`is_arch_op_supported(target, op_name)`。
- 参数顺序：`directory`；`target, key`；`target, op_name`。
- 参数类型：`Path`；`str, str`；`str, str`。
- 返回值：`dict[str, TargetSpec]`、`int | None`、`bool`。
- 文件合同：npu demo target 文件固定为 `kernel_gen/target/targets/npu_demo.txt`；`block_num/thread_num/subthread_num` 当前都为 `1`；所有容量、arch 支持矩阵也写在该文件中。

```txt
name=npu_demo
arch.supported_ops=arch.get_block_id,arch.get_block_num,arch.get_thread_id,arch.get_thread_num,arch.get_subthread_id,arch.get_subthread_num,arch.get_dynamic_memory,arch.barrier,arch.launch
arch.unsupported_ops=arch.launch_kernel
hw.block_num=1
hw.thread_num=1
hw.subthread_num=1
hw.sm_memory_size=0
hw.lm_memory_size=0
hw.tsm_memory_size=24576
hw.tlm1_memory_size=1024
hw.tlm2_memory_size=512
hw.tlm3_memory_size=512
```

```python
from pathlib import Path
from kernel_gen.target import registry

registry.load_targets(Path("kernel_gen/target/targets"))
assert registry.get_target_hardware("npu_demo", "block_num") == 1
assert registry.get_target_hardware("npu_demo", "thread_num") == 1
assert registry.get_target_hardware("npu_demo", "subthread_num") == 1
```

### `AttachArchInformationPass`

- 公开入口：`AttachArchInformationPass(target: str | None = None)`。
- pass registry 名称：`attach-arch-information`。
- 参数顺序：`target`。
- 参数类型：`str | None`。
- 返回值：`None`，原地修改 module。
- 默认值：`target is None` 时使用 npu demo pipeline 传入的 target；若 pipeline 未传 target，则使用 npu demo target 名称。
- 行为边界：只给唯一 root `func.func` 附着 `launch_block / launch_thread / launch_subthread`；三项值来自 target registry；当前 `npu_demo.txt` 中三项为 `1/1/1`。
- 失败边界：target 未注册、硬件字段缺失、root 函数不唯一、已有部分 launch attrs、已有完整 attrs 但与 target 值冲突，都必须稳定失败。

```python
from kernel_gen.passes.attach_arch_information import AttachArchInformationPass

AttachArchInformationPass(target="npu_demo").apply(ctx, module)
```

预期 IR 形态：

```mlir
func.func @add_kernel(%arg0: !nn.memory<...>, %arg1: !nn.memory<...>, %arg2: !nn.memory<...>)
    attributes {launch_block = 1 : i64, launch_thread = 1 : i64, launch_subthread = 1 : i64} {
  ...
}
```

### `build_npu_demo_lowering_pipeline`

- 公开入口：`build_npu_demo_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager`。
- registry 名称：`npu-demo-lowering`。
- 参数顺序：`options`。
- 参数类型：`dict[str, str] | None`。
- 返回值：`PassManager`。
- 默认顺序：`inline -> decompass -> lower-nn -> symbol-loop-hoist -> attach-arch-information -> outline-device-kernel`。
- option 合同：P0 只公开 `target=<target-name>`；`only-kernel`、`launch_block`、`launch_thread`、`launch_subthread` 都不是公开 option。
- MLIR 风格工具入口：命令行和 ircheck 侧应支持 `npu-demo-lowering{target=npu_demo}` 这种 braces option 形式；Python 侧仍可使用 `build_registered_pipeline("npu-demo-lowering", {"target": "npu_demo"})`。

```python
from kernel_gen.passes.registry import build_registered_pipeline

pm = build_registered_pipeline("npu-demo-lowering")
# inline -> decompass -> lower-nn -> symbol-loop-hoist
# -> attach-arch-information -> outline-device-kernel

pm = build_registered_pipeline(
    "npu-demo-lowering",
    {"target": "npu_demo"},
)
```

### `gen_kernel` Launch Module

- 公开入口：`gen_kernel(module, EmitCContext(target="npu_demo"))`。
- 参数顺序：`module, ctx`。
- 参数类型：`ModuleOp | FuncOp, EmitCContext`。
- 返回值：`str`。
- launch module 行为：发现唯一 host wrapper + `arch.launch` 时，按 `arch.launch` 的 block/thread/subthread 生成 `npu_demo::launch<B, T, S>`。
- target 查询行为：codegen 只查询 target 是否支持必要 `arch.*` 能力和必要硬件字段；不把 npu demo 硬件值写成 Python 常量。
- C++ ABI 行为：IR device function 签名保持原 args；npu demo C++ device function 首参由 codegen 注入 `npu_demo::KernelContext& ctx`。
- 删除边界：删除或废弃 `_emit_npu_demo_launch_body_function` 中 frozen add+barrier 骨架、`_validate_npu_demo_launch_wrapper_signature` 的三参数限制、`npu_demo::launch<1, 4, 1>` 硬编码。

```cpp
static void add_kernel_device(npu_demo::KernelContext& ctx, /* original args */) {
  /* generic emitted body from lowered IR */
}

void add_kernel(/* original args */) {
  npu_demo::launch<1, 1, 1>(add_kernel_device, /* original args */);
}
```

### `dsl_run` Entry Selection

- 公开入口：`dsl_run(fn, args, pipeline, emitcconfig)`。
- 参数顺序：沿用现有 `dsl_run`。
- 参数类型：`Callable, tuple, str | PassManager, EmitCContext`。
- 返回值：`DslRunResult`。
- 入口规则：如果 lowered module 中存在唯一包含 `arch.launch` 的 wrapper，则生成整个 module 的源码，并以 wrapper `sym_name` 作为执行入口。
- helper 规则：module 中允许存在任意数量不含 `arch.launch` 的 private/helper `func.func`；这些函数不能影响 wrapper 入口选择。
- fail-fast 规则：存在唯一 wrapper 时，`gen_kernel(module, ctx)` 失败必须直接抛错，不能 fallback 到 `_find_first_func`。

为什么这里必须改：

```text
旧规则：emitcconfig.target == "npu_demo" && len(func_ops) == 2 才走 wrapper。
问题：inline/helper/库函数引入后，合法 module 可能有 3 个或更多 func。
风险：旧规则会 fallback 到第一个 func，导致真实执行入口不是 host launch wrapper，KernelContext、thread id、barrier、dynamic memory 都可能不符合 npu demo 运行逻辑。
新规则：入口由唯一 arch.launch wrapper 决定，不由函数数量决定。
```

```python
from kernel_gen.dsl.gen_kernel import EmitCContext
from kernel_gen.tools.dsl_run import dsl_run

result = dsl_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering", EmitCContext(target="npu_demo"))
assert result.entry_name == "add_kernel"
assert "npu_demo::launch<1, 1, 1>" in result.source
```

### `i64` DSL/MLIR

- 公开入口：`NumericType.Int64`、`Tensor[i64, ...]`。
- 参数顺序：沿用现有 DSL tensor annotation 和 `Memory(..., NumericType.Int64)`。
- 参数类型：`NumericType.Int64`。
- 返回值：MLIR memory element type 为 `i64`。

```python
from kernel_gen.dsl import mlir_gen
from kernel_gen.symbol_variable import Memory, NumericType

def add_i64_kernel(
    out: "Tensor[i64, 8]",
    lhs: "Tensor[i64, 8]",
    rhs: "Tensor[i64, 8]",
) -> None:
    store(lhs + rhs, out, [0], [8], [1])

module = mlir_gen(
    add_i64_kernel,
    Memory([8], NumericType.Int64),
    Memory([8], NumericType.Int64),
    Memory([8], NumericType.Int64),
)
assert "i64" in str(module)
```

## 完成态定义

- target registry 不再通过 Python 内置 `_DEFAULT_NPU_DEMO_*` 作为 npu demo 真源；npu demo arch 能力和硬件参数从 `kernel_gen/target/targets/npu_demo.txt` 加载。
- 当前 npu demo target 的 launch extent 查询结果是 `block=1, thread=1, subthread=1`；`attach-arch-information` 和 `gen_kernel` 都通过 target/IR 查询得到这些值，不写死。
- `npu-demo-lowering` 默认 after-IR 包含 host wrapper + device function，wrapper 内含唯一 `arch.launch`。
- `build_registered_pipeline("npu-demo-lowering", {"only-kernel": "true"})` 或 CLI `npu-demo-lowering{only-kernel=true}` 稳定失败。
- `gen_kernel` 对 npu demo launch module 不再限定 add/barrier 固定骨架、不再限定三参数 `lhs/rhs/out`、不再生成 `launch<1,4,1>`。
- `dsl_run(..., "npu-demo-lowering", EmitCContext(target="npu_demo"))` 选择 wrapper 入口真实编译执行，不允许只 lower、只出源码、dry-run 或 fallback 到首个普通函数。
- execute expectation 的 add/sub/mul/matmul 默认链路支持随机 shape 和随机 dtype；`i64` 能进入 MLIR/codegen，不通过缩小随机池绕过。
- `default-lowering` builder 和 standalone `outline-device-kernel` pass 入口保持公开兼容。

## 验收设计

- 命令执行约定：所有命令均从对应 `<worktree>` 根目录执行；`PYTHONPATH` 固定为 `<worktree>:/home/lfr/kernelcode_generate`。
- 验收资产状态：
  - `test/target/test_target_registry.py`：锁定 npu demo target 从 txt 加载、文件值为 `1/1/1`、硬编码默认模板不再是 npu demo 真源。
  - `test/dsl/test_emit_mlir.py` 与 `test/dsl/test_mlir_gen.py`：锁定 `i64` dtype emit 和 roundtrip。
  - `test/pass/test_pipeline_npu_demo_lowering.py`：锁定 pipeline 顺序、MLIR-style option parse、`only-kernel` 拒绝、target lookup。
  - `expectation/pass/outline_device_kernel`：继续锁定 standalone outline pass 消费显式 attrs 的 IR 行为。
  - `test/dsl/test_gen_kernel.py`：锁定 generic `arch.launch` extents、ctx 注入、删除 frozen add/barrier 特化。
  - `test/tools/test_dsl_run.py`：锁定 wrapper entry selection 不 silent fallback。
  - `expectation/execute_engine/npu_demo/default`：锁定 default pipeline 的 add/sub/mul/matmul 真实执行。
- 最终必过命令：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate python3 -m expectation.pass.outline_device_kernel
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate python3 -m expectation.tools.dsl_run
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate python3 -m expectation.execute_engine.npu_demo.default
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate pytest -q test/target/test_target_registry.py test/dsl/test_emit_mlir.py test/dsl/test_mlir_gen.py test/pass/test_pipeline_npu_demo_lowering.py test/pass/outline_device_kernel/test_outline_device_kernel.py test/dsl/test_gen_kernel.py test/tools/test_dsl_run.py
```

- Diff 反推验证：执行人与审查人必须按实际 diff 补跑对应 pytest 或可执行脚本，并在任务日志写明 `Diff 反推自测` / `Diff 反推审查`；`expectation` 合同验收单列，不算 diff 反推测试。
- 终验 expectation：架构师终验、复验或终验修复复核时必须在最新同步现场运行全量 `expectation` 合同验收；未运行或失败时不得给通过结论，除非用户明确确认环境依赖例外。

## 阶段拆分

### S1：收口 npu_demo.txt 与 i64 前置链路

#### 阶段目标

- 让 npu demo target 信息从 `kernel_gen/target/targets/npu_demo.txt` 加载，当前 launch extent 查询为 `1/1/1`；同时修复 `i64` DSL/MLIR 前置链路。

#### 目标 spec / API

- `spec/target/registry.md`
- `spec/dsl/emit_mlir.md`
- `spec/dsl/mlir_gen.md`
- 公开 API：`load_targets(...)`、`get_target_hardware(...)`、`is_arch_op_supported(...)`、`NumericType.Int64`、`Tensor[i64, ...]`

#### 禁止修改面 / 合同真源

- 禁止修改面：不修改 `.skills`；不修改 `[immutable]` 或 `[immutable-file]` 内容；不缩小 execute expectation 的随机 dtype 池绕过 `i64`。
- 合同真源：`spec/target/registry.md + kernel_gen/target/targets/npu_demo.txt > test/target/test_target_registry.py > 当前实现`；`expectation/execute_engine/npu_demo/default > spec/dsl/emit_mlir.md + spec/dsl/mlir_gen.md > test/dsl/test_emit_mlir.py + test/dsl/test_mlir_gen.py > 当前实现`。

#### 预期示例代码

```python
from pathlib import Path
from kernel_gen.target import registry

registry.load_targets(Path("kernel_gen/target/targets"))
assert registry.get_target_hardware("npu_demo", "block_num") == 1
assert registry.get_target_hardware("npu_demo", "thread_num") == 1
assert registry.get_target_hardware("npu_demo", "subthread_num") == 1
```

#### 预期输出

```text
target hardware: block_num=1, thread_num=1, subthread_num=1
MLIR dtype: i64
```

#### 目标验收资产

- `test/target/test_target_registry.py`：锁定 `npu_demo.txt` 加载与硬件字段。
- `test/dsl/test_emit_mlir.py`：锁定 `_dtype_to_xdsl(NumericType.Int64)` 输出 `i64`。
- `test/dsl/test_mlir_gen.py`：锁定 `Tensor[i64, ...]` 函数签名和 memory type。

#### 验收必过项目

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate pytest -q test/target/test_target_registry.py test/dsl/test_emit_mlir.py test/dsl/test_mlir_gen.py`
- `补充要求：执行人与审查人按实际 diff 反推测试，并在任务日志写明 Diff 反推自测 / Diff 反推审查；expectation 合同验收单列`

#### 任务新建建议

- `任务类型：build`
- `任务目标：同链补 spec / 实现 / pytest，使 npu demo target 从 txt 加载且当前 launch extent 为 1/1/1，并修复 i64 DSL/MLIR 前置链路。`
- `记录文件：wt-<date>-npu-demo-lowering-outline-s1/agents/logs/T-<id>.md`

### S2：默认 npu-demo-lowering 生成 IR launch wrapper

#### 阶段目标

- 收口默认 pipeline：通过 `attach-arch-information` 查询 target 并附着 attrs，再由 `outline-device-kernel` 生成 host wrapper + device function。

#### 目标 spec / API

- `spec/pass/inline.md`
- `spec/pass/attach_arch_information.md`
- `spec/pass/outline_device_kernel.md`
- `spec/pass/pipeline/npu_demo_lowering.md`
- 公开 API：`InlinePass`、`AttachArchInformationPass`、`build_npu_demo_lowering_pipeline()`、`build_registered_pipeline("npu-demo-lowering")`

#### 禁止修改面 / 合同真源

- 禁止修改面：不修改 `.skills`；不修改 `[immutable]` 或 `[immutable-file]` 内容；不修改 `default-lowering` builder；不删除 standalone `outline-device-kernel` pass；不让 `outline-device-kernel` IR device function 签名新增 ctx；不新增或保留 `only-kernel` 公开 option。
- 合同真源：`expectation/pass/outline_device_kernel > spec/pass/attach_arch_information.md + spec/pass/pipeline/npu_demo_lowering.md > test/pass/test_pipeline_npu_demo_lowering.py + test/pass/outline_device_kernel/test_outline_device_kernel.py > 当前实现`。

#### 预期示例代码

```python
from kernel_gen.passes.registry import build_registered_pipeline

pm = build_registered_pipeline("npu-demo-lowering", {"target": "npu_demo"})
module = pm.run(module)
```

#### 预期输出

```mlir
func.func @add_kernel(...) {
  %block = arith.constant 1 : index
  %thread = arith.constant 1 : index
  %subthread = arith.constant 1 : index
  arch.launch @add_kernel_device blocks(%block) threads(%thread) subthreads(%subthread) (...)
  func.return
}

func.func private @add_kernel_device(...) {
  ...
}
```

#### 目标验收资产

- `expectation/pass/outline_device_kernel`：显式 attrs 的 outline IR 行为继续通过，device IR signature 不新增 ctx。
- `test/pass/test_pipeline_npu_demo_lowering.py`：pipeline 顺序、target option、MLIR-style option parse、`only-kernel` 拒绝、target lookup。
- `test/pass/outline_device_kernel/test_outline_device_kernel.py`：standalone outline pass 行为不回归。

#### 验收必过项目

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate python3 -m expectation.pass.outline_device_kernel`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate pytest -q test/pass/test_pipeline_npu_demo_lowering.py test/pass/outline_device_kernel/test_outline_device_kernel.py`
- `补充要求：执行人与审查人按实际 diff 反推测试，并在任务日志写明 Diff 反推自测 / Diff 反推审查；expectation 合同验收单列`

#### 任务新建建议

- `任务类型：build`
- `任务目标：同链补 spec / 实现 / pytest，使 npu-demo-lowering 默认通过 target 查询附着 launch attrs 并生成 IR host wrapper；拒绝 only-kernel option。`
- `记录文件：wt-<date>-npu-demo-lowering-outline-s2/agents/logs/T-<id>.md`

### S3：泛化 npu demo codegen 与 dsl_run 执行入口

#### 阶段目标

- 删除 npu demo frozen add/barrier 特化 emitter，按通用 `arch.launch` module 生成源码；让 `dsl_run` 以唯一 launch wrapper 为执行入口真实编译执行。

#### 目标 spec / API

- `spec/dsl/gen_kernel.md`
- `spec/tools/dsl_run.md`
- 公开 API：`gen_kernel(..., EmitCContext(target="npu_demo"))`、`dsl_run(..., "npu-demo-lowering", EmitCContext(target="npu_demo"))`

#### 禁止修改面 / 合同真源

- 禁止修改面：不修改 `.skills`；不修改 `[immutable]` 或 `[immutable-file]` 内容；不通过恢复 add/barrier 特化来让单 case 通过；不让 `dsl_run` 在 wrapper codegen 失败时 fallback 首函数；不保留 `npu_demo::launch<1,4,1>` 硬编码。
- 合同真源：`expectation/execute_engine/npu_demo/default > spec/tools/dsl_run.md + spec/dsl/gen_kernel.md > test/tools/test_dsl_run.py + test/dsl/test_gen_kernel.py > 当前实现`。

#### 预期示例代码

```python
from kernel_gen.dsl.gen_kernel import EmitCContext
from kernel_gen.tools.dsl_run import dsl_run

result = dsl_run(add_kernel, (out, lhs, rhs), "npu-demo-lowering", EmitCContext(target="npu_demo"))
```

#### 预期输出

```cpp
static void add_kernel_device(npu_demo::KernelContext& ctx, /* original args */) {
  /* generic emitted body from lowered IR */
}

void add_kernel(/* original args */) {
  npu_demo::launch<1, 1, 1>(add_kernel_device, /* original args */);
}
```

#### 目标验收资产

- `test/dsl/test_gen_kernel.py`：generic `arch.launch` extents、ctx C++ 注入、module codegen fail-fast、删除 frozen add/barrier 特化。
- `test/tools/test_dsl_run.py`：存在唯一 `arch.launch` wrapper 时，entry_name 为 wrapper；helper 函数数量不影响入口；module codegen 失败不能 fallback。
- `expectation/tools/dsl_run`：继续锁定 dsl_run 正向与反向工具合同。
- `expectation/execute_engine/npu_demo/default`：add/sub/mul/matmul 通过 default wrapper pipeline 真实执行。

#### 验收必过项目

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate python3 -m expectation.tools.dsl_run`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate python3 -m expectation.execute_engine.npu_demo.default`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<worktree>:/home/lfr/kernelcode_generate pytest -q test/dsl/test_gen_kernel.py test/tools/test_dsl_run.py`
- `补充要求：执行人与审查人按实际 diff 反推测试，并在任务日志写明 Diff 反推自测 / Diff 反推审查；expectation 合同验收单列`

#### 任务新建建议

- `任务类型：build`
- `任务目标：同链补 spec / 实现 / pytest / expectation 适配，使 npu demo gen_kernel 按通用 arch.launch module 生成 launch<1,1,1> wrapper，并让 dsl_run 选择 wrapper 真实执行。`
- `记录文件：wt-<date>-npu-demo-lowering-outline-s3/agents/logs/T-<id>.md`

## 待确认项

- 暂无。用户已确认 target 文件名与公开 target 名均使用 `npu_demo`，文件固定为 `kernel_gen/target/targets/npu_demo.txt`。

## 用户确认与协同约束

- 用户确认状态：`已确认`
- 未确认事项：`暂无`
- 用户确认结论：`已确认当前 launch extent 用 1/1/1；extent 必须从 target registry + npu_demo.txt 获取；不公开支持 only-kernel=true，传入该 option 必须稳定失败；pipeline option 风格尽量贴近 MLIR；查询 target 的地方不应写特殊骨架；gen_kernel 的 npu_demo 特化 emitter 应删除；target 数据应从 kernel_gen/target/targets/npu_demo.txt 加载，不写在代码实现里。`
- 未确认前处理要求：`无待确认项；但旧三方评审已失效，必须完成新计划复评后再创建任务。`
- 协同约束：`用户此前要求架构师询问团队其他人并整合观点；本轮因需求变更，旧三方通过结论作废，需要按新计划至少完成三方复评后再推进任务创建。`
- 询问记录 1：`守护最好的爱莉希雅 / 通过：最新正文已清空 kernel_gen.dsl.emit_c 导入残留，S1/S2/S3 拆分、npu_demo.txt target 真源、extent=1/1/1 经 registry 查询、删除 gen_kernel add/barrier 特化、dsl_run 按唯一 arch.launch wrapper 选入口均清楚且机械可判。`
- 询问记录 2：`大闸蟹 / 复评通过：协同记录已补齐；only-kernel=true 已统一为不公开支持且传入稳定失败；默认 npu-demo-lowering 覆盖 execute_engine/default、npu_demo.txt 唯一 target 数据源、S1/S2/S3 拆分与依赖均清楚，可进入任务创建。`
- 询问记录 3：`提莫炖蘑菇 / 复评通过：only-kernel=true 口径已统一为不公开支持且传入稳定失败；npu_demo.txt 唯一 target 数据源、gen_kernel 删除旧特化边界、dsl_run fail-fast 主线清楚。`
- 询问记录 4：`不要啊教练 / 通过：only-kernel=true 拒绝、target 未注册 / 硬件字段缺失 / root 函数不唯一 / partial attrs / target 值冲突、dsl_run 禁止 fallback 的失败边界均已写成机械可判合同。`

## 参考资料

- [`agents/standard/计划书标准.md`](../../agents/standard/计划书标准.md)
- [`agents/standard/计划书模板.md`](../../agents/standard/计划书模板.md)
- [`spec/target/registry.md`](../../spec/target/registry.md)
- [`kernel_gen/target/registry.py`](../../kernel_gen/target/registry.py)
- [`kernel_gen/passes/pipeline/npu_demo_lowering.py`](../../kernel_gen/passes/pipeline/npu_demo_lowering.py)
- [`kernel_gen/passes/outline_device_kernel.py`](../../kernel_gen/passes/outline_device_kernel.py)
- [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)
- [`kernel_gen/tools/dsl_run.py`](../../kernel_gen/tools/dsl_run.py)
