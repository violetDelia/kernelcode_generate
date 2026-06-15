# CUDA SM86 Final IR Emit Backend Green Plan

## 文档信息
- 状态：Draft 9 已收敛 / 用户确认项 C1-C5 已收口 / Codex subagent strict review 已通过 / 守护最终检验已通过 / 可通知管理员下发唯一计划级 `execute`。
- 目标 `spec`：
  - `spec/dsl/gen_kernel/emit.md`
  - `spec/dsl/gen_kernel/emit/cuda_sm86.md`
  - `spec/include/cuda_sm86/cuda_sm86.md`
  - `spec/pass/pipeline/cuda_sm86_lowering.md`
  - `spec/pass/kernel_pattern_attach.md`
  - `spec/pass/lowering/dma_memory_hierarchy/spec.md`
- 公开 `API` 快速索引：见 `公开 API 设计 / API 列表`；本计划保持 `emit_c`、`gen_kernel`、`emit_c_impl(target="cuda_sm86")`、`emit_c_include_impl(target="cuda_sm86")`、`ExecutionEngine(target="cuda_sm86")`、SourceBundle artifact、`kg_execute_entry` C ABI 与 `cuda_sm86::ArgSlot` ABI 不变。
- 测试入口快速索引：见 `验收设计 / Diff 反推测试`，重点入口包括 CUDA emit pytest、SourceBundle pytest、CUDA lowering pipeline pytest、ExecutionEngine strategy pytest、9 demo CUDA runtime gate 和 private API boundary pytest。
- 验收资产快速索引：本计划不列 `expectation/` 为必过合同验收资产；合同验收字段均写为无必过 `expectation`，执行 / 审查按 diff 反推 pytest、CUDA runtime gate、静态扫描和敏感目录门禁验收。
- 实现入口快速索引：`kernel_gen/dsl/gen_kernel/emit/cuda_sm86/**`、`include/cuda_sm86/cuda_sm86.cuh`、`include/cuda_sm86/Arch.h`、`kernel_gen/pipeline/cuda_sm86_lowering.py`、`kernel_gen/passes/tuning/kernel_pattern_attach.py`、`kernel_gen/passes/tuning/dma_memory_hierarchy.py`。
- 用户确认来源：
  - 用户反馈“之前的 cuda 后端不是很满意”。
  - 用户明确指出 emit 实现和 include 实现都不能和 DSL 最终 IR 很好结合。
  - 用户要求按最新计划书规范推进，除守护最终检验外，只问 Codex subagent。
  - 2026-06-03 用户要求：计划书必须按 `agents/standard/计划书标准.md` 补齐每个小任务卡的预期形态、正例和反例。
  - 2026-06-03 用户确认：可以删除 / 替换当前 CUDA emit package-local family-source exact set。
  - 2026-06-03 用户确认：可以新增 final IR unsupported-op 稳定错误文本，采用计划推荐口径。
  - 2026-06-03 用户确认：本计划完成态只覆盖 9 个现有 demo final IR op 集合，不承诺任意 CUDA SM86 DSL kernel。
  - 2026-06-03 用户确认：维持当前 `cuda-sm86-lowering` no-memory-pool pipeline，不改成 memory-pool / `arch.get_dynamic_memory` byte-pool final IR。
  - 2026-06-03 用户确认：CUDA target 下 DMA hierarchy matmul transform 规则应为 `matmul{["tlm1", "tlm1", "tlm1"]}`。
  - 2026-06-03 用户指出：Draft 8 虽已通过技术收敛，但计划书没有按 `agents/standard/计划书标准.md` 的格式写足内容；每个小任务卡必须写清 `预期形态 / 正例 / 反例`。因此 Draft 8 的“可下发”状态失效，当前进入 Draft 9 格式与内容返工。
- 计划任务名：`cuda-sm86-final-ir-emit-backend`
- 任务类型：唯一计划级 `execute`
- 流转：`execute -> review -> archive_acceptance -> merge/归档`
- 任务记录建议：`agents/codex-multi-agents/log/task_records/2026/<dd>/<date>-cuda-sm86-final-ir-emit-backend.md`
- 计划文件跟踪要求：`ARCHITECTURE/plan/` 当前被 `.gitignore` 忽略；本计划进入下发 / merge 前必须用 `git add -f ARCHITECTURE/plan/cuda_sm86_final_ir_emit_backend_green_plan.md` 纳入候选，并在任务记录中写入 `git ls-files --error-unmatch ARCHITECTURE/plan/cuda_sm86_final_ir_emit_backend_green_plan.md` 通过结果。

## 计划级任务

| 计划任务 | 任务类型 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `cuda-sm86-final-ir-emit-backend` | `execute` | `wt-20260602-cuda-sm86-final-ir-emit-backend` | `agents/codex-multi-agents/log/task_records/2026/<dd>/<date>-cuda-sm86-final-ir-emit-backend.md` |

任务目标：重构 `target="cuda_sm86"` 的 emit/include 后端，使 generated CUDA source 以 `cuda-sm86-lowering` 后的最终 IR 为真源逐 op / region 生成，而不是通过 `CudaSm86ModuleSummary` 猜测 matmul / conv2d / flash_attention family 后拼接硬编码整 kernel source；同步 spec、pytest、include helper 边界和 CUDA runtime gate，跑通 9 个现有 kernel demo。

## 计划目标
- CUDA 后端的 generated source 必须由最终 IR 驱动：
  - host entry func 的 `tuner.select`、`scf.if`、`arch.launch` 生成 host dispatcher。
  - device func 按当前 `cuda-sm86-lowering` 公开顺序输出的 final IR 逐 op / region 生成 CUDA C++ / CUDA kernel code；当前默认不引入 `MemoryPoolPass`，因此首版必须覆盖 `dma.alloc/free`、`dma.reinterpret/view/slice/deslice/copy/fill/broadcast/reshape/transpose` 等现有 op，而不是假设 `arch.get_dynamic_memory` byte-pool 形态。
  - CUDA target 下 pattern transform 的 DMA hierarchy matmul rule 必须按用户确认项 C5 使用 `matmul{["tlm1", "tlm1", "tlm1"]}`，即 `kernel.matmul(out, lhs, rhs)` 三个 memory operand 均 materialize 到 `tlm1`；不得继续使用当前 `tlm1/tlm2` 或 `tlm2/tlm1` 双 pattern 作为 CUDA 完成态。
  - `kernel.matmul`、`kernel.binary_elewise`、`kernel.exp`、`kernel.reduce`、`kernel.img2col2d` 的输出必须由 IR op 出现与 operand 决定，不由函数名、summary family 或 printed IR token 决定。
- CUDA include 实现层必须服务最终 IR 语义：
  - `include/cuda_sm86/cuda_sm86.cuh` 仍是 aggregate header。
  - `include/cuda_sm86/Arch.h` 提供 generated source 可用的 backend implementation primitives，例如 memory descriptor、slot decode、scratch arena、view / reinterpret、copy / fill / broadcast、CUDA error check、TF32 / matmul helper。
  - 这些 helper 位于 `cuda_sm86::detail`，不进入跨 target 公开 API；测试不得 direct call。
- 保持包外公开入口不变：
  - `emit_c_impl(..., target="cuda_sm86")` / `emit_c_include_impl(target="cuda_sm86")` 注册入口不变。
  - `ExecutionEngine(target="cuda_sm86")` 使用方式不变。
  - `gen_kernel(...)` / SourceBundle aggregate 格式不变。
- 删除当前方向上的错位逻辑：
  - 不再把 `CudaSm86KernelFamily` / `CudaSm86ModuleSummary` 作为 source family 选择真源；删除或替换当前 spec 中记录的 package-local exact set 已由用户确认项 C1 收口。
  - 不再把 `detect_cuda_sm86_kernel_family(...)` / `summarize_cuda_sm86_module(...)` 这种 family detector 作为生成真源；删除公开 spec 记录的 exact 名称已由用户确认项 C1 收口。
  - 不再把 `emit_matmul_source(...)`、`emit_conv2d_source(...)`、`emit_flash_attention_source(...)` 这种整 kernel source 入口作为当前生成真源；删除公开 spec 记录的 exact 名称已由用户确认项 C1 收口。
  - 不再出现 `kg_cuda_sm86_selected_kernel_kind`、`kg_cuda_sm86_run_matmul`、`kg_cuda_sm86_run_conv2d`、`kg_cuda_sm86_run_flash_attention` 这种 family runner。

## 非目标
- 不新增或删除包外 Python 公开 API。
- 不新增跨 target include/api 公开接口。
- 不修改 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。
- 默认不改变 `cuda-sm86-lowering` pipeline 顺序，不接入 `MemoryPoolPass`；C5 只确认 CUDA target-specific DMA hierarchy matmul transform rule 从当前 `tlm1/tlm2` 双 pattern 改为 `matmul{["tlm1", "tlm1", "tlm1"]}`，不等同于 memory-pool / `arch.get_dynamic_memory` byte-pool 方向。
- 不做性能优化作为通过条件；第一版以 IR 语义正确和 9 demo 运行通过为目标。
- 不支持任意未在 9 demo 最终 IR 中出现的 op；遇到未知或未覆盖 op 必须稳定 fail-fast，不得 fallback 到硬编码 family source。

## 当前基线
- 当前 `cuda_sm86` emit package 已经拆成：
  - `__init__.py`
  - `include.py`
  - `constants.py`
  - `module.py`
  - `detect.py`
  - `source_bundle.py`
  - `runtime.py`
  - `kernel/{binary_elewise,exp,img2col2d,matmul,reduce}.py`
- 当前问题不在目录是否存在，而在设计真源：
  - `kernel/*.py` 多数只返回 `"kernel.matmul"` / `"kernel.exp"` 等 token，不发射最终 IR op 语义。
  - `detect.py` 统计 op token 和 memory rank pattern，猜测 `matmul` / `conv2d` / `flash_attention` family。
  - `source_bundle.py` 根据 family 选择 `emit_matmul_source(...)` / `emit_conv2d_source(...)` / `emit_flash_attention_source(...)`。
  - 这些 source 是固定整 kernel / runner，不遍历最终 IR 的 host/device func、region、op、operand、memory view 链。
- 当前 include 层：
  - `include/cuda_sm86/cuda_sm86.cuh` 只聚合 `include/api/Arch.h` 与 `include/cuda_sm86/Arch.h`。
  - `include/cuda_sm86/Arch.h` 只有 `ArgSlot`、slot guard、host/device copy、device alloc/free、TF32 helper。
  - 缺少能直接承接最终 IR memory descriptor、scratch arena、view / reinterpret、copy / fill / broadcast、device kernel launch 的系统性 primitive。
- 当前 `cuda-sm86-lowering` 公开合同见 `spec/pass/pipeline/cuda_sm86_lowering.md`：不包含 `MemoryPoolPass`，不得默认把 TLM fragment 改写为 `arch.get_dynamic_memory + dma.reinterpret` byte pool 形态。
- 2026-06-03 只读 inventory：通过公开 `mlir_gen(...) -> build_cuda_sm86_lowering_pipeline().run(...)` 对 9 个 runtime demo 生成 final IR，当前 op 集合为：
  - host/control：`builtin.module`、`func.func`、`func.return`、`scf.if`、`scf.yield`、`tuner.select`。
  - arch：`arch.launch`、`arch.get_block_id`。
  - scalar/symbol：`arith.constant`、`builtin.unregistered(op_name__="symbol.const")`、`builtin.unregistered(op_name__="symbol.eq")`、`symbol.const`、`symbol.add`、`symbol.sub`、`symbol.mul`、`symbol.floordiv`、`symbol.min`、`symbol.max`、`symbol.ne`、`symbol.for`、`symbol.get_dim`、`symbol.cast`、`memory.get_data`。
  - dma/memory：`dma.alloc`、`dma.free`、`dma.reinterpret`、`dma.view`、`dma.slice`、`dma.deslice`、`dma.copy`、`dma.fill`、`dma.broadcast`、`dma.reshape`、`dma.transpose`.
  - kernel：`kernel.matmul`、`kernel.binary_elewise`、`kernel.exp`、`kernel.reduce`、`kernel.img2col2d`。
- 9 demo final IR 的计数摘要：
  - all cases 合计：`dma.alloc/free` 各 246、`dma.reinterpret` 96、`dma.deslice` 90、`kernel.binary_elewise` 66、`kernel.matmul` 24、`kernel.exp` 12、`kernel.reduce` 12、`kernel.img2col2d` 6、`arch.launch` 18。
  - matmul 三例出现 `arch.get_block_id`、`memory.get_data`、`symbol.ne`、`dma.broadcast/copy/deslice/reinterpret`、`kernel.matmul`、`kernel.binary_elewise`。
  - conv2d 三例额外出现 `dma.slice`、`dma.transpose`、`dma.view`、`symbol.max`、`symbol.floordiv`、`kernel.img2col2d`。
  - flash_attention 三例额外出现 `dma.reshape`、`kernel.exp`、`kernel.reduce(kind="max"|"sum", keepdim=true, axis=1)`。
- 9 demo current final IR 的关键 attr inventory：
  - `arch.launch.callee` 指向对应 `*_pattern0_device` / `*_pattern1_device` device func。
  - `tuner.select.patterns` 固定列出每个 demo 的 `pattern0` / `pattern1` host pattern。
  - `symbol.for.iter` 包含 start/end/step 的 `#symbol.iter<...>` 表达式。
  - `dma.transpose.perm` 当前出现 `[#builtin.int<1>, #builtin.int<0>]` 与 `[#builtin.int<1>, #builtin.int<0>, #builtin.int<2>, #builtin.int<3>]`。
  - `kernel.binary_elewise.kind` 当前出现 `add`、`sub`、`mul`、`truediv`、`max`；`min` 不在 9 demo inventory 中，首版应按 unsupported kind 处理。
  - `kernel.reduce` 当前只出现 `axis=1 : i64`、`keepdim=true`、`kind="max"|"sum"`。
  - producer/consumer/tile 类 attrs 包括 `producer`、`consumer`、`loop_body_productor`、`loop_body_consumer`、`if_branch_productor`、`if_branch_consumer`、`after_loop_productor`、`after_loop_consumer`、`after_if_consumer` 等；首版必须把这些 attrs 纳入 stable traversal hash 和 marker，可作为 dependency 诊断元数据，但不得用它们替代 SSA operand dataflow。
- 当前缺口：
  - 草案原本引用 `arch.get_dynamic_memory` 作为 final IR 主路径，与当前公开 pipeline 和现场 inventory 不一致。
  - 当前 spec 已把 family source 与 package-local exact set 写成合同；替换这些合同需要用户确认或明确保留兼容语义。

## 方案比较与选型
- 不采用方案 A：继续保留 family summary + hardcoded source，只补 include helper。
  - 原因：emit 仍不读最终 IR op 语义，DSL / pipeline 改动无法自然反映到 CUDA source。
- 不采用方案 B：只把现有 hardcoded source 拆到更多文件。
  - 原因：目录更细不会解决 family guessing 和 IR 脱节。
- 不采用方案 C：把所有 CUDA 业务 kernel 放进 include。
  - 原因：include 应该承接 backend primitives，业务 source 应由最终 IR generated SourceBundle 局部生成。
- 不采用方案 D：执行中顺手把 `cuda-sm86-lowering` 改成 memory-pool / `arch.get_dynamic_memory` byte-pool 形态。
  - 原因：pipeline 顺序是公开合同；当前用户只确认 emit/include 要围绕最终 IR 重新设计，没有确认调整 pipeline 公开顺序。
- 采用方案：最终 IR 驱动的 CUDA emit backend。
  - `module.py` 遍历 `ModuleOp` 中的 entry func、device func 和 region，生成 SourceBundle，并以当前 no-memory-pool final IR op inventory 为第一版覆盖范围。
  - target-specific op emit 按最终 IR op 发射片段，不再返回 family token。
  - include 提供 generated source 需要的 `cuda_sm86::detail` primitives，作为实现层 helper，不扩大包外公开 API。

## 公开 API 设计

### 功能简介
- 本计划不新增包外 Python 公开 API。
- 本计划不新增跨 target include/api 公开接口。
- 本计划会调整 `spec/dsl/gen_kernel/emit/cuda_sm86.md` 与 `spec/include/cuda_sm86/cuda_sm86.md` 中 CUDA backend 的公开可观测合同：从 family source 合同改为 final-IR-driven generated source 合同。

### API 列表
- 保持不变：`emit_c(obj: SSAValue | Operation | func.FuncOp | ModuleOp, ctx: EmitCContext) -> str`
- 保持不变：`gen_kernel(obj: Operation | func.FuncOp | ModuleOp, ctx: EmitCContext) -> str`
- 保持不变：`emit_c_impl(ModuleOp, target="cuda_sm86")` registry handler 入口，不作为包外 direct-call API。
- 保持不变：`emit_c_include_impl(target="cuda_sm86")` registry handler 入口，不作为包外 direct-call API。
- 保持不变：`class ExecutionEngine(target: str, compiler: str | None = None, compiler_flags: tuple[str, ...] = ("-std=c++17",), link_flags: tuple[str, ...] = ())`
- 保持不变：`ExecutionEngine.compile(source: str | None = None, function: str | None = None, *, request: CompileRequest | None = None, entry_point: str = "kg_execute_entry") -> CompiledKernel`
- 保持不变：`CompiledKernel.execute(args: tuple[RuntimeInput, ...] | None = None, *, request: ExecuteRequest | None = None, entry_point: str | None = None, capture_function_output: bool = False, stream: None = None) -> ExecuteResult`
- 保持不变：SourceBundle artifact key：
  - `kernel.cu`
  - `include/cuda_sm86/generated_entry.cuh`
- 保持不变：SourceBundle aggregate marker 格式为 `// __KG_BUNDLE_FILE__:<relative/path>`；artifact path 必须保持安全相对路径；`dump_dir` 非空时仍写出 aggregate `source.cpp` 与上述 artifacts。
- 保持不变：`extern "C" int kg_execute_entry(cuda_sm86::ArgSlot *slots, unsigned long long count)` C ABI。
- 保持不变：包外 include API：
  - `namespace cuda_sm86`
  - `struct cuda_sm86::ArgSlot`
  - `ArgSlot` 字段与顺序保持：`int kind; void *data; long long *shape; long long *stride; unsigned long long rank; int dtype_code; long long int_value; double float_value;`。
- 保持不变：`target="cuda_sm86"` 编译失败短语仍使用 `compile_failed`，`nvcc` 缺失 / 非零文本仍包含 `nvcc failed` 或 `compiler not found` 摘要。
- 保持不变：`target="cuda_sm86"` 的 target/include family mismatch 仍以 `target_header_mismatch` 失败，不新增 failure phrase。
- 保持不变：`target="cuda_sm86"` 非空 stream 仍以 `stream_not_supported` 失败，文本包含 `cuda_sm86 does not support non-None stream`。
- 保持不变：CUDA runtime 错误仍收敛到 `runtime_throw_or_abort`，detail 文本包含 `cuda_runtime_failed`。
- `cuda_sm86::detail::*` 是 generated source 专用 backend implementation helper，不进入包外公开 API；测试不得 direct call。
- 已确认：删除或替换当前 `spec/dsl/gen_kernel/emit/cuda_sm86.md` 记录的 package-local exact set，包括 `CudaSm86KernelFamily`、`CudaSm86ModuleSummary`、`detect_cuda_sm86_kernel_family(...)`、`summarize_cuda_sm86_module(...)`、`build_cuda_sm86_source_bundle(summary)`、`emit_matmul_source(summary)`、`emit_conv2d_source(summary)`、`emit_flash_attention_source(summary)`。
- 已确认：新增 final IR unsupported-op 稳定错误文本，采用 `unsupported cuda_sm86 final IR op: <op_name>`；unsupported attr/type 也必须 fail-fast，但不得新增独立稳定 exact 文本，除非另行取得用户确认。

### package-local 文件级 API 边界
- execute 可以在 `kernel_gen/dsl/gen_kernel/emit/cuda_sm86/` 包内新增 package-local 文件级 API，前提是：
  - 写入对应文件的文件级 `API 列表`。
  - 不进入 `cuda_sm86.__all__` 或 `cuda_sm86.kernel.__all__`。
  - 不进入包外 public path matrix。
  - 测试不得 direct import / direct call。
  - 只能在 `cuda_sm86` package 内部按 spec 依赖方向使用。
- 推荐最小内部结构：
  - `module.py`：唯一 `ModuleOp` SourceBundle handler。
  - `ir_context.py` 或同等文件：承接 SSA value -> C++ identifier、memory descriptor、symbol expr、region scope、artifact builder 状态；文件名由 execute 在不新增包外 API 的前提下按实现需要确定。
  - `host.py`：host entry / `tuner.select` / `arch.launch` emission。
  - `device.py`：device func / `__global__` kernel body emission。
  - `memory.py`：memory descriptor / slot / scratch arena source helpers。
  - `control_flow.py`：`scf.if` / `symbol.for` emission.
  - `arch.py`：`arch.get_*` / `arch.launch` emission.
  - `dma/*.py`：`dma.alloc/free/reinterpret/view/slice/deslice/copy/fill/broadcast/reshape/transpose` first-version coverage.
  - `kernel/*.py`：`kernel.matmul`、`kernel.binary_elewise`、`kernel.exp`、`kernel.reduce`、`kernel.img2col2d` final IR op emission.
  - `source_bundle.py`：artifact assembly only.
  - `runtime.py`：generated runtime source fragments only.
- 若执行发现必须新增包外 API、公开 include helper、脚本参数、pipeline option 或稳定错误文本，必须暂停并回用户确认。

### Final IR emission rules

| 范围 | 输入 / attrs / region | SSA/env 绑定 | C++ 片段类别 | unsupported 规则 |
| --- | --- | --- | --- | --- |
| `ModuleOp` / `func.func` | host func 使用 `entry_point=unit`；device func 使用 `kernel.pattern_id` 和 `shared_memory_size` | 函数参数按顺序绑定到 `ArgSlot` 或 device kernel 参数；block argument 生成稳定局部名 | SourceBundle root、host entry、device kernel 声明 | 缺 host entry、未知 function attr 或无法解析参数类型时报 C2 错误 |
| SSA result / block arg | 每个 op result、region block arg、`scf.yield` value | 按真实遍历顺序生成确定性 identifier；region yield 写回 parent scope 的命名 slot | 局部变量声明 / 表达式绑定 | 结果数量、yield 数量或类型不匹配时报 C2 错误 |
| `tuner.select` | `patterns=[@pattern0, @pattern1, ...]` | pattern symbol 解析到 host/device func map | host dispatcher pattern table；后续 `scf.if` / `arch.launch` 只引用已解析 pattern | pattern 缺失、重复或不是 func symbol 报 C2 错误 |
| `scf.if` / `scf.yield` | condition operand；then/else regions；yield operands | condition 发射为 bool expr；yield 绑定到 parent scope | `if (...) { ... } else { ... }` 和 region scoped statements | 缺 else、yield 数量不一致或 yield 类型不支持时报 C2 错误 |
| `symbol.for` | `iter=#symbol.iter<start,end,step>`；body region | loop iv 绑定为整数局部名；body 内 SSA 使用嵌套 scope | `for (long long iv = start; iv < end; iv += step)` | start/end/step 无法转为整数表达式或 step 非正时报 C2 错误 |
| `arch.launch` | 文本形态为 `arch.launch<block, thread, subthread, shared_memory_size>(@callee, args...)`；四个 extent operand 与 args 均来自 SSA | `block/thread/subthread/shared_memory_size` 先按 symbol expr 解析为 launch extent；callee 解析为 `__global__` device kernel；`args...` 按 device func 参数顺序绑定；op 无 result | CUDA kernel launch 维度、shared memory size 和 `KG_CUDA_CHECK` | callee 缺失、extent 无法解析为当前支持的整数表达式、extent 静态非法、参数数量/类型不匹配或未知 launch attr 报 C2 错误 |
| `arch.get_block_id` | 无额外 attr | result 绑定到 `blockIdx.x` 表达式 | device integer expression | 仅支持当前 9 demo 所需 block axis；其它 axis 报 C2 错误 |
| `arith.constant` / `symbol.*` / `builtin.unregistered` | `symbol.const.value`、`symbol.for.iter`、`symbol.get_dim.axis`、`builtin.unregistered.op_name__` | 结果绑定为整数 / 指针 / bool 表达式；`builtin.unregistered` 仅归一化 `symbol.const` 与 `symbol.eq` | C++ scalar expression | 未列 symbol op、未知 builtin unregistered `op_name__`、未知 dtype 报 C2 错误 |
| `memory.get_data` | memory operand | result 绑定到 memory descriptor data pointer | pointer expression | 非 memory descriptor 输入报 C2 错误 |
| `dma.alloc/free` | `alloc(dynamic_shape...)` 的 result memory type 承载 shape/stride/space/dtype，dynamic_shape operand 只覆盖公开 verifier 允许的动态 shape；`free(source)` 读取 source descriptor；producer attrs 只作 hash/marker 与诊断元数据 | alloc 生成 temporary memory descriptor；free 标记释放对应 descriptor | `cuda_sm86::detail` allocation/free helper 调用 | 非当前 space/dtype/rank、dynamic_shape 与 result type 不匹配或 free 非 alloc descriptor 报 C2 错误 |
| `dma.reinterpret/view/reshape` | `reinterpret(source, offset, shape..., stride...)`；`view(source, offsets..., shape..., stride...)`；`reshape(source, shape...)`；result type 提供目标 descriptor 类型 | result 绑定为 alias descriptor，不复制数据；offsets/shape/stride 均按 SSA symbol expr 解析，且必须与 result type 对齐 | descriptor alias / transform helper 调用 | 未支持 rank/space/dtype、layout operand 与 result type 不一致或 alias 越界时报 C2 错误 |
| `dma.slice/deslice/transpose` | `slice/deslice(target, source, offsets..., sizes..., strides...)`；`transpose(target, source, perm)` | target/source descriptor 按 SSA dataflow 读取；op 无 result；`slice` 将 source 窗口写入 target，`deslice` 将 source 写回 target 窗口，`transpose` 按 perm 物化写入 target；`transpose.perm` 仅支持当前 inventory 两种 perm | detail slice/deslice/transpose materialization helper 调用 | 非单位 strides、未支持 perm/rank/space/dtype、target/source shape 不兼容或越界时报 C2 错误 |
| `dma.copy/fill/broadcast` | source/dest descriptor、scalar fill value、producer/consumer attrs | operand descriptor 按 SSA dataflow 读取；producer/consumer attrs 只进 hash/marker 和诊断元数据 | detail copy/fill/broadcast helper 调用 | dtype/rank/shape 不兼容或未知 attr 影响语义时报 C2 错误 |
| `kernel.matmul` | operands 为 `out, lhs, rhs`，可带第四个动态 `acc: i1` operand；attrs 为 `space` 与可选静态 `acc` i1 attr；`acc` 不是 descriptor | output descriptor 写入 `out`；`acc=false` 覆盖写，`acc=true` 或动态 acc 读取旧 out 后累加写；可用 Tensor Core 或可验证 CUDA matmul path | matmul helper / inline device loop | 非 f32、rank 不匹配、动态/静态 acc 同时存在、acc 非 i1 或当前 9 demo 外 attr 报 C2 错误 |
| `kernel.binary_elewise` | operands 为 `out, lhs, rhs`；attrs 为 `kind` 与 `space` | 支持 `add/sub/mul/truediv/max`；`min` 当前不在 9 demo，按 unsupported | elementwise helper / inline device loop | kind 不在 `add/sub/mul/truediv/max`、space/type/layout 不匹配报 C2 错误 |
| `kernel.exp` | final IR / IRDL named operands 为 `out, input`；公开 constructor 可保持 `KernelExpOp(input_value, out, space)`；attr 为 `space` | out descriptor 写入 `exp(input)` 结果，发射器必须按 named operand 绑定，不能按 constructor 参数顺序反置 | exp helper / inline device loop | 非 f32、rank 不匹配、space/type/layout 不匹配或 out/input 角色无法判定时报 C2 错误 |
| `kernel.reduce` | operands 为 `out, input`；attrs 为 `axis=1`、`keepdim=true`、`kind=max|sum` 与 `space` | out descriptor 写入 reduce 结果 | reduce helper / inline device loop | axis/keepdim/kind 不等于当前 inventory、或 space/type/layout 不匹配报 C2 错误 |
| `kernel.img2col2d` | operands 为 `out, input, kh, kw, sh, sw, dh, dw, ph, pw, pl, pr`；attr 为 `space`；无 weight descriptor | out descriptor 写入结构化 img2col 结果；窗口参数按 SSA symbol / constant operand 解析 | img2col helper / inline device loop | 当前 9 demo 外窗口参数形态、rank、space、dtype 或 output shape/stride 合同不匹配时报 C2 错误 |

补充规则：
- producer/consumer/tile attrs 必须进入 `kg.cuda.ir.hash` 与 marker，方便证明 traversal 真实读取 attrs；但 runtime 语义以 SSA operand dataflow 和 op attrs 为真源，不得只根据 producer/consumer 编号生成硬编码 family source。
- 每个 row 的 unsupported 文本均使用用户确认项 C2 的前缀；具体 `<op_name>` 必须来自真实 op name，不能来自 printed IR spoof 字符串。

### Flash Attention required API matrix

本节专门补足 3 个 `kernel/flash_attention` demo 所需的 CUDA 后端 API 面；这些 API 面仍属于 `cuda_sm86` package-local emitter 或 generated `cuda_sm86::detail` helper，不新增包外 Python API、不新增跨 target include API，测试不得 direct call。

| FA 需求层 | 必须覆盖的 package-local / detail API 面 | 对应 final IR / DSL 来源 | 验收重点 |
| --- | --- | --- | --- |
| entry / slot decode | `out/q/k/v` memory slot decode；`br/bc` runtime `SymbolDim` / int slot decode；shape/stride/rank/dtype/space descriptor 构造 | FA 三例公开签名：`out, q, k, v`，动态 tile 例额外 `br, bc`；`memory.get_data`、`symbol.get_dim` | `ArgSlot` ABI 不变；dynamic input/tile 不能被硬编码成 static shape/tile |
| symbol scalar API | `symbol.const/add/sub/mul/floordiv/min/max/ne/cast/get_dim`、`arith.constant`、`builtin.unregistered(symbol.const|symbol.eq)` 到 C++ 标量表达式；`symbol.for` loop iv / start / end / step | `unit_tile = br - br + 1`、`cur_br = min(br, seq_len - m0)`、`cur_bc = min(bc, seq_len - n0)`、四层 `b/h/m/n` loop | dynamic shape/tile 下表达式仍来自 SSA / symbol expr；不能按 demo 名称写死 |
| launch / control API | `tuner.select` pattern table、`scf.if/yield`、`arch.launch<block, thread, subthread, shared_memory_size>(@callee, args...)` | FA runtime gate 走 host dispatcher -> device pattern；每个 pattern 发射 device kernel | `arch.launch` 四个 extent operand 必须进入 launch 维度 / shared memory；pattern 选择不能退回 family runner |
| scratch memory API | TSM/TLM1 f32 temporary descriptor；`dma.alloc/free`；`dma.fill` 支持 `0` 与 `-inf`；lifetime 成对记录；TLM2/TLM3 仍是通用 dialect 合法 space，但不作为 C5 下 CUDA 9 demo 完成态必需 descriptor | `q_full_4d/k_full_4d/v_full_4d`、`m_state/sum_state/weighted`、`matmul_score/score_tile/tile_max/m_next/shifted_score/exp_score/tile_sum/old_shift/old_scale/scaled_sum/sum_next/partial/scaled_weighted/weighted_next/sum_full/output_tile`、memory hierarchy 后的 matmul out/lhs/rhs TLM1 temporaries | 固定上界 scratch `[br, bc]`、`[dim, bc]`、`[br, unit_tile]`、`[br, dim]`、`[1,1,br,dim]`、`[1,1,bc,dim]` 必须可构造；tail 只靠 view/deslice 表达；C5 matmul pattern 的 `out/lhs/rhs -> tlm1` descriptor 必须支持并保持后续 dataflow 可见 |
| alias / layout API | `dma.view` window descriptor；`dma.reshape` 4D<->2D alias；`dma.reinterpret` hierarchy alias；`dma.copy` hierarchy materialization；`dma.transpose` target/source materialization；`dma.deslice` tail/full write-back；`dma.broadcast` row vector materialization | Q/K/V tile 读取：`view + deslice + reshape`；K 转置到 `[dim, bc]`；memory hierarchy 用 `reinterpret/copy` 将 matmul out/lhs/rhs 布局化到 `tlm1`；`m_next/old_scale/sum_state` broadcast 到 `[br,bc]` 或 `[br,dim]`；output `view + reshape + deslice` 写回 | `view/reshape/reinterpret` 是 alias result；`copy/transpose/deslice/broadcast` 是写入型 materialization；不得混成同一 alias 规则；若 out operand 被 materialize 到 TLM1，execute 必须保证 matmul 写入对后续 consumer 或必要 write-back 可见，不得只 free 掉 TLM1 临时 |
| score matmul API | `kernel.matmul(out, lhs, rhs, space, acc?)` f32 rank-2 path | `matmul_score = q_full @ k_transposed`；`partial = exp_score @ v_full` | 两个 matmul 都必须从 IR operand 生成，不能用 `kg_cuda_sm86_run_flash_attention` 固定 source |
| online softmax API | `kernel.reduce(kind=max, axis=1, keepdim=true)`；`kernel.reduce(kind=sum, axis=1, keepdim=true)`；`kernel.binary_elewise(kind=max|sub|mul|add|truediv)`；`kernel.exp(out, input)` named-operand binding | `tile_max`、`m_next`、`shifted_score`、`exp_score = exp(shifted_score)`、`tile_sum`、`old_shift`、`old_scale = exp(old_shift)`、`scaled_sum`、`sum_next`、`scaled_weighted`、`weighted_next`、`output_tile` | 必须覆盖 row-wise max/sum、max-shift exp、running sum/weighted update 和最终 divide；必须测试 `kernel.exp` out/input 未反置；`nn.softmax` 或整 kernel flash source 不得出现 |
| state update API | full descriptor write-back via `dma.deslice` for `m_state`、`sum_state`、`weighted`；final output tail write-back to `out` | inner loop 末尾 `deslice(m_state, m_next)`、`deslice(sum_state, sum_next)`、`deslice(weighted, weighted_next)`；outer loop 末尾 `deslice(out, o_4d, ...)` | state update 必须是 target/source write，不得只更新本地变量或丢弃 descriptor dataflow |
| traversal proof API | FA-specific `kg.cuda.ir.op` markers 与 stable hash components 覆盖上述 op/attrs/operand types；producer/consumer/tile attrs 进入 hash/marker | 三个 FA case current final IR，尤其 `dma.reshape`、`kernel.exp`、`kernel.reduce(max|sum)`、`dma.broadcast` | 每个 FA case 至少断言 case-specific marker set；hash 随 FA op sequence / attrs 变化 |

FA 负面约束：
- 不新增 `emit_flash_attention_source(...)`、`kg_cuda_sm86_run_flash_attention` 或任何按函数名选择整 kernel source 的 API。
- 不把 online softmax 合成单个未定义 `kernel.flash_attention` / `kernel.softmax` API；当前只覆盖 9 demo final IR 中已出现的基础 op 组合。
- 若 execute 发现 FA final IR 额外出现当前 matrix 未列出的 op、attr、dtype、space、rank 或 reduce axis，必须先更新 inventory / spec / tests；涉及公开 API、pipeline 顺序或稳定错误文本时回用户确认。

## 完成态定义
- `target="cuda_sm86"` 的 `ModuleOp` handler 不再通过 `CudaSm86ModuleSummary` 选择整 kernel source。
- `detect.py` 的 family detector 逻辑删除或降级为 final IR validation，不再作为 source selection 真源。
- `kernel/*.py` 的 emit handler 不再只返回 token；必须发射对应 final IR op 的 CUDA source fragment，或在未覆盖 op 上稳定 fail-fast。
- generated `kernel.cu` 必须包含 final IR op markers，用于证明 source 来自 IR traversal，例如：
  - `// kg.cuda.ir.func: <func_name>`
  - `// kg.cuda.ir.op: arch.launch`
  - `// kg.cuda.ir.op: dma.reinterpret`
  - `// kg.cuda.ir.op: dma.copy`
  - `// kg.cuda.ir.op: kernel.matmul`
- generated `kernel.cu` 必须包含稳定 traversal 摘要，例如 `// kg.cuda.ir.hash: <stable>`；摘要必须由真实遍历得到的 func/op/attrs/operand types 顺序计算，重复生成一致，插入或删除支持 op 会变化，函数名或 printed string spoof 不得影响摘要。
- final IR emission 必须定义 SSA value 环境、symbol expr 到 C++ 表达式、memory descriptor / space 映射、region scope、`scf.if` / `scf.yield`、`symbol.for`、`tuner.select` pattern 选择、`arch.launch` extent / callee / 参数绑定和 op attrs 的生成规则；不得只生成 marker 后继续调用 family source。
- generated source 不得包含：
  - `kg_cuda_sm86_selected_kernel_kind`
  - `kg_cuda_sm86_run_matmul`
  - `kg_cuda_sm86_run_conv2d`
  - `kg_cuda_sm86_run_flash_attention`
  - `emit_matmul_source`
  - `emit_conv2d_source`
  - `emit_flash_attention_source`
- `include/cuda_sm86/Arch.h` 承接 final IR 所需 backend primitives：
  - `ArgSlot` 保持 ABI 不变。
  - `cuda_sm86::detail` 内可新增 / 重构 memory descriptor、scratch arena、view / reinterpret、copy / fill / broadcast、matmul / elewise / reduce / exp helper。
  - helper 不进入 `API 列表` 的包外公开 API，只能列入 helper 清单或后端实现层说明。
- 9 个现有 kernel demo 在有 CUDA 环境时必须 runtime 通过；缺 `nvcc` / 缺 CUDA device / skipped 不是通过，按环境阻塞记录。
- 若 execute 发现 9 demo final IR 出现当前 inventory 未列出的 op、attr、region 或 memory type，必须先更新 op inventory、spec 和测试；若新增公开错误文本、pipeline 顺序或包外 API，必须暂停并回用户确认。

## 验收设计

### Diff 反推测试
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py -k cuda_sm86_ir_hash`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py -k cuda_sm86_ir_hash`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_package.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/test_source_bundle.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_cuda_sm86_lowering.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_cuda_sm86_strategy.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/cuda/test_cuda_sm86_kernel_demos_runtime.py -m cuda -rs`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/repo_conformance/test_private_api_boundaries.py`

### CUDA runtime gate
- CUDA 环境存在时 9 个现有 kernel demo 必须全部 `passed`。
- 若出现 `skipped`、缺 `nvcc`、缺 CUDA device 或环境不满足，则本计划 execute 视为环境阻塞，不得进入 review；除非管理员 / 架构师单独记录环境裁定。
- 任务记录必须摘录 `-rs` 摘要中的 passed / skipped 数量和 skip reason。

### 结构 / 行为门禁
- generated source 必须包含 final IR markers，且 marker 来自真实 IR traversal。
- generated source 不得出现 family runner / selected kind 旧合同。
- 测试必须覆盖：
  - 输入含不同最终 IR op sequence 时，generated source marker 和 emitted source 变化。
  - 删除或插入一个支持的 final IR op 后，`kg.cuda.ir.hash` 和 source 对应变化；不得只按 family 不变而 source 不变。
  - 同一 final IR 重复生成 `kg.cuda.ir.hash` 一致；不同 Python hash seed 下仍一致。
  - 9 个 demo 每个 case 都断言至少一个 case-specific op marker 集合，而不是只抽查三类 family。
  - unknown final IR op 稳定 fail-fast。
  - name-only module、printed string token spoof 仍失败。
- 静态扫描：
  - `rg -n "CudaSm86KernelFamily|CudaSm86ModuleSummary|detect_cuda_sm86_kernel_family|summarize_cuda_sm86_module|emit_matmul_source|emit_conv2d_source|emit_flash_attention_source|kg_cuda_sm86_selected_kernel_kind|kg_cuda_sm86_run_matmul|kg_cuda_sm86_run_conv2d|kg_cuda_sm86_run_flash_attention|按 lowered IR family|kernel family" kernel_gen/dsl/gen_kernel/emit/cuda_sm86 spec/dsl/gen_kernel/emit.md spec/dsl/gen_kernel/emit/cuda_sm86.md test`
  - 预期：除本计划用户确认记录、历史任务记录或负例断言外，候选实现 / 当前 spec / 当前 pytest 中不出现旧合同作为当前真源。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m py_compile kernel_gen/dsl/gen_kernel/emit/cuda_sm86/*.py kernel_gen/dsl/gen_kernel/emit/cuda_sm86/**/*.py`
- `git diff --check`

### 敏感目录门禁
- `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md` 预期无输出。
- `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md` 预期无输出。
- ignored / untracked 敏感资产不要求主仓基线为空；execute 开始前必须记录基线快照：
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md > /tmp/cuda_sm86_final_ir_sensitive.before`
- execute / review / archive_acceptance 结束前必须复跑并与基线一致：
  - `git status --short --ignored --untracked-files=all -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md > /tmp/cuda_sm86_final_ir_sensitive.after`
  - `diff -u /tmp/cuda_sm86_final_ir_sensitive.before /tmp/cuda_sm86_final_ir_sensitive.after`
- 若基线快照与结束快照不同，必须分类说明；未经用户 / 架构授权不得把差异写入候选。

### 合同验收
- 本计划不列 `expectation/` 为必过合同验收资产。
- 不修改、不复制、不新增 `expectation/`。

## 计划内小任务

### S0. 固定 9 demo final IR inventory 与确认门禁
- 为什么做：final IR emit 的第一版覆盖范围必须来自当前公开 lowering 输出，不能按旧 family source 或过期 dump 猜测。
- 做什么：execute 开工后用公开 `mlir_gen(...) -> build_cuda_sm86_lowering_pipeline().run(...)` 重新生成 9 demo final IR inventory，并与本计划清单比对。
- 不做什么：不修改 pipeline 顺序、不接入 `MemoryPoolPass`、不修改 expectation、不把新 op 自动扩大为已确认范围；但必须按 C5 调整 CUDA target-specific DMA hierarchy matmul transform rule。
- 怎么验收：任务记录列出 9 demo op/attr/region 清单；若有新增 op/attr/region，先更新 spec/test/计划记录，涉及公开 API 或 pipeline 顺序时回用户确认。
- 卡住问谁：pipeline 顺序或 9 demo 范围问用户；inventory 与当前 spec 冲突问架构师。

详细字段：
- 上下文：本计划只覆盖 9 个现有 demo 的 current final IR；C5 已确认 CUDA target 的 matmul hierarchy rule 必须是 `matmul{["tlm1", "tlm1", "tlm1"]}`。
- 目标：重新生成并记录 9 demo final IR inventory，确认 op/attr/region/function attr 与 C5 hierarchy rule 都进入后续实现与测试真源。
- 非目标：不扩大 demo 范围，不把 inventory 差异自动当成已确认新范围，不把 runtime demo 缺 CUDA 环境解释成通过。
- 预期形态：任务记录必须有一张 9 demo 清单，逐 case 写 `func`、device pattern、op set、关键 attr、memory space、`kernel.matmul(out,lhs,rhs)` hierarchy rule 和差异结论。
- 正例：
  - `flash_attention/inputs_static_tile_static.py` inventory 记录包含 `dma.copy/reinterpret/transpose/broadcast`、`kernel.matmul` 两类调用点、`kernel.exp(out,input)` 和 C5 `matmul{["tlm1","tlm1","tlm1"]}`。
  - `matmul/inputs_dynamic_tile_dynamic.py` inventory 记录动态 symbol 维度来源、`arch.launch` extent 和 final IR op 顺序。
- 反例：
  - 只写“9 demo 已生成”但不列 op/attr/region 清单。
  - 继续把 CUDA hierarchy 记录为 `matmul{["", "tlm1", "tlm2"]}` 或 `matmul{["", "tlm2", "tlm1"]}`。
  - 因某个 demo 出现新 op 就直接扩展范围，而没有更新 spec/test/计划并按公开 API 影响回用户确认。
- 模块范围：`test/cuda/test_cuda_sm86_kernel_demos_runtime.py`、`kernel_gen/pipeline/cuda_sm86_lowering.py`、`spec/pass/pipeline/cuda_sm86_lowering.md`、任务记录。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。
- 合同真源：用户确认 > 本计划用户确认项 > `spec/pass/pipeline/cuda_sm86_lowering.md` > 公开 runtime pytest > 当前实现。
- 最小闭环：9 demo final IR inventory 证明当前不含 `MemoryPoolPass` / `arch.get_dynamic_memory` 主路径，且列出所有必须覆盖 op。
- 当前必过合同验收：无 `expectation`；本任务只做 inventory、文本记录和 pytest / 脚本核对。
- 执行步骤：
  1. 对 9 demo 逐个运行公开 lowering，记录 op name、关键 attr、region 数量和 function attrs。
  2. 比对本计划 inventory，确认无遗漏或写出遗漏项。
  3. 按 C5 把 CUDA target-specific matmul transform rule 收口到 `matmul{["tlm1", "tlm1", "tlm1"]}`；若 execute 发现必须新增 pipeline option、改变 pipeline 顺序或缩小 9 demo，暂停并回用户确认。
- 验收与记录：任务记录必须包含 inventory 摘要、差异处理和是否触发用户确认。
- 合同验收：本任务无必过 `expectation`。

### S1. 重写 CUDA emit / include spec 到 final IR 真源
- 为什么做：当前 spec 仍承认 family source / selected family 思路，和用户目标冲突。
- 做什么：更新 `spec/dsl/gen_kernel/emit.md`、`spec/dsl/gen_kernel/emit/cuda_sm86.md` 与 `spec/include/cuda_sm86/cuda_sm86.md`，把 CUDA backend 合同改为 final-IR-driven generated source。
- 不做什么：不新增包外 API，不修改 expectation；不得超出用户确认项 C1/C2 的 API 与错误语义范围。
- 怎么验收：spec 删除 family source 当前真源，写清 final IR hash/markers、unsupported op fail-fast、include detail primitive 边界，并同步 `test/repo_conformance` 反射口径。
- 卡住问谁：公开 API、package-local exact set 删除或稳定错误文本问用户；验收口径问架构师。

详细字段：
- 上下文：当前公开 emit / include spec 仍保留 family source 方案和旧 package-local exact set；C1/C2/C5 已确认需要替换为 final IR source 与 CUDA all-TLM1 matmul rule。
- 目标：把 CUDA emit / include spec 改成可执行合同，明确公开 API 不变、package-local exact set 删除、C5 hierarchy rule 和 unsupported final IR 错误语义。
- 非目标：不把 `cuda_sm86::detail`、package-local Python helper 或新的 pipeline option 写成包外公开 API；不修改 `expectation/`。
- 预期形态：spec 必须先给功能简介和紧跟其后的 `API 列表`，再列公开 API 保持项、删除项、package-local 边界、C5 rule、错误文本和测试映射。
- 正例：
  - `spec/dsl/gen_kernel/emit/cuda_sm86.md` 写明 `emit_c_impl(ModuleOp, target="cuda_sm86")` 仍返回 SourceBundle aggregate，source 来自 final IR traversal。
  - CUDA spec 写明 `unsupported cuda_sm86 final IR op: <op_name>` 是稳定错误前缀，`matmul{["tlm1","tlm1","tlm1"]}` 是 CUDA target 完成态。
  - repo conformance 测试只允许公开入口和确认后的 package-local exact set，不再要求 `CudaSm86ModuleSummary`。
- 反例：
  - spec 继续说“按 matmul/conv2d/flash_attention family 选择 source”。
  - 把 `cuda_sm86::detail::copy(...)` 或 package-local builder helper 加进包外 API。
  - 删除新的公开名称或改变稳定错误文本但没有用户确认来源。
- 模块范围：`spec/dsl/gen_kernel/emit.md`、`spec/dsl/gen_kernel/emit/cuda_sm86.md`、`spec/include/cuda_sm86/cuda_sm86.md`、`test/repo_conformance/test_private_api_boundaries.py`。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。
- 合同真源：用户确认 > 本计划 > spec > pytest > 当前实现。
- 最小闭环：公开 spec 不再要求 generated source 按 matmul / conv2d / flash_attention family 选择整 kernel source；`cuda_sm86::detail` 仍不进入包外 API。
- 当前必过合同验收：无 `expectation`；本任务验收依赖 spec 文本核对、repo conformance 和 emit/include pytest。
- 执行步骤：
  1. 删除或改写 `spec/dsl/gen_kernel/emit.md` 与 CUDA spec 中“按 lowered IR family 选择 source”的当前合同。
  2. 写入 final IR traversal、stable hash、op marker、unsupported op、SourceBundle artifact 和 include detail 边界。
  3. 按用户确认项 C1 更新 package-local exact set；若执行发现还需删除其它 spec/API 名称，必须回用户确认。
  4. 更新 repo conformance 测试，避免它继续反射旧 package-local exact set。
- 验收与记录：记录公开 API 变化来源、旧合同删除点和 expectation 未修改。
- 合同验收：本任务无必过 `expectation`。

### S2. 将 `ModuleOp` handler 改为 final IR SourceBundle builder
- 为什么做：`module.py -> detect.py -> source_bundle.py` 当前通过 family summary 选整 kernel source，不能反映最终 IR。
- 做什么：重构 `module.py` 和 package-local builder，遍历 host entry func、device funcs、regions、ops、operands 与 attrs，生成 `kernel.cu` / generated header SourceBundle。
- 不做什么：不靠函数名、printed IR token、memory rank pattern 或 family enum 选择整 kernel source。
- 怎么验收：source 中出现每个 final IR func/op marker和 `kg.cuda.ir.hash`；旧 family runner / selected kind 文本不存在；hash 对重复生成稳定。
- 卡住问谁：需要新增包外 API 或稳定错误文本问用户；final IR traversal 规则争议问架构师。

详细字段：
- 上下文：当前 CUDA `ModuleOp` handler 经 family detector / summary 拼接整 kernel source，无法证明生成内容来自 final IR op/attr/region traversal。
- 目标：建立 package-local final IR SourceBundle builder，使 host entry、device funcs、regions、operands、attrs 和 C5 hierarchy rule 都进入 source 与 stable hash。
- 非目标：不按 demo 文件名、函数名、printed IR 字符串、memory rank pattern 或 old family enum 选择 source。
- 预期形态：builder 输出包含 `kernel.cu` 和 generated header artifact；每个 func/op 有 `kg.cuda.ir.op` marker，module 级有稳定 `kg.cuda.ir.hash`，SourceBundle artifact key 与 ExecutionEngine 入口保持不变。
- 正例：
  - 同一 final IR 在重复运行、`PYTHONHASHSEED=0` 和 `PYTHONHASHSEED=1` 下生成相同 `kg.cuda.ir.hash`。
  - 删除一个支持的 final IR op 后，marker/hash/source 都发生对应变化。
  - `arch.launch<block, thread, subthread, shared_memory_size>(@callee, args...)` 生成 CUDA launch，并绑定 device func 参数。
- 反例：
  - source 里只出现 `kg_cuda_sm86_selected_kernel_kind = "flash_attention"`，没有真实 op marker。
  - name-only module 或 printed string token spoof 也能生成 matmul source。
  - C5 只写进注释或 marker，SourceBundle builder 实际仍走旧 family source。
- 模块范围：`kernel_gen/dsl/gen_kernel/emit/cuda_sm86/**`。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。
- 合同真源：本计划用户确认项收口 > `spec/dsl/gen_kernel/emit/cuda_sm86.md` > pytest > 当前实现。
- 最小闭环：
  - host `entry_point` func -> `kg_execute_entry(cuda_sm86::ArgSlot *slots, unsigned long long count)`。
  - `tuner.select` / `scf.if` / `arch.launch` -> host dispatcher 和 CUDA kernel launch。
  - device funcs -> `__global__` kernels。
  - SourceBundle artifact keys 不变。
- 当前必过合同验收：无 `expectation`；本任务验收依赖 emit pytest、SourceBundle pytest、hash 稳定测试和静态扫描。
- 执行步骤：
  1. 建立 package-local emit state：SSA value env、symbol expression env、memory descriptor table、region scope stack、artifact writer、stable traversal digest。
  2. 遍历 `ModuleOp`、host entry、device funcs 和 regions，按 op dispatcher 生成 source 片段。
  3. 生成 final IR markers 和 stable hash。
  4. 删除或替换 family summary/source selection。
  5. 对 unsupported op/attr/type fail-fast；公开稳定错误文本只使用用户确认项 C2 的 unsupported-op 口径，attr/type 不新增独立稳定 exact 文本。
- 验收与记录：`test_cuda_sm86_emit.py` 新增 IR-driven source、hash 稳定、name/string spoof、unsupported op 测试；静态扫描旧 family source token 不存在。
- 合同验收：本任务无必过 `expectation`。

### S3. 补齐 CUDA `cuda_sm86::detail` backend primitives
- 为什么做：最终 IR emit 需要统一 memory/view/copy/fill/broadcast/launch primitive；当前 include helper 只覆盖 slot/copy/alloc 的一小部分。
- 做什么：在 `include/cuda_sm86/Arch.h` 中整理 generated source 专用 primitives，并同步文件级说明和 spec。
- 不做什么：不把 helper 写入包外 `API 列表`，不允许测试 direct call `cuda_sm86::detail::*`。
- 怎么验收：generated source 通过 detail primitive 承接 final IR memory/dma/kernel op；include API 列表仍只有 `namespace cuda_sm86` 和 `ArgSlot`。
- 卡住问谁：如果某 helper 必须公开到 include API，问用户。

详细字段：
- 上下文：final IR emit 需要 generated CUDA source 能表达 memory descriptor、DMA materialization、kernel math 和 launch primitives，但这些 helper 不能变成跨 target include API。
- 目标：补齐 `cuda_sm86::detail` backend primitives，让 generated source 能实现 S4 op handlers 和 C5 all-TLM1 matmul dataflow。
- 非目标：不让测试 direct call `cuda_sm86::detail`，不把 detail helper 加入 include public API，不把 helper 做成跨 target 通用 API。
- 预期形态：`include/cuda_sm86/cuda_sm86.cuh` 仍只聚合 header；`include/cuda_sm86/Arch.h` 中 detail helper 支撑 descriptor、copy/fill/broadcast、view/reinterpret/reshape、matmul/elewise/exp/reduce/img2col 和 CUDA error check。
- 正例：
  - generated source 通过 `cuda_sm86::detail` 构造 global slot descriptor、TLM1 temporary descriptor，并执行 `dma.copy` / `kernel.matmul` / write-back。
  - public include API 仍只暴露 `namespace cuda_sm86`、`ArgSlot` 和既有 C ABI 所需结构。
  - helper 能表达 `out_tlm1` 写入后 copy-back 或 consumer-visible dataflow。
- 反例：
  - 测试直接 include 并调用 `cuda_sm86::detail::matmul(...)` 作为公开 API。
  - 把 `cuda_sm86::detail` helper 写进跨 target `include/api/Arch.h`。
  - 为了跑通当前 demo，把 all-TLM1 temporary 写成固定全局数组或硬编码 shape。
- 模块范围：`include/cuda_sm86/cuda_sm86.cuh`、`include/cuda_sm86/Arch.h`、对应 spec/test。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。
- 合同真源：`spec/include/cuda_sm86/cuda_sm86.md` > CUDA emit spec > runtime pytest > 当前实现。
- 最小闭环：generated source 可以通过 `cuda_sm86::detail` 构造 global/temporary memory descriptor，完成 alloc/free、view/reinterpret/slice/transpose、copy/fill/broadcast、matmul/elewise/exp/reduce/img2col first-version runtime。
- first-version primitive 覆盖：
  - slot -> global memory descriptor。
  - device temporary allocation / free descriptor。
  - reinterpret / view / reshape descriptor alias construction。
  - slice / deslice / transpose materialization helper。
  - fill / copy / broadcast。
  - binary add / sub / mul / truediv / max、exp、reduce max/sum；`min` 不在 9 demo inventory 中，首版按 unsupported kind 处理。
  - matmul tile helper，保留 Tensor Core 或可验证 CUDA matmul path。
- 当前必过合同验收：无 `expectation`；本任务验收依赖 include/source compile、CUDA runtime gate、private API boundary test。
- 执行步骤：
  1. 保持 `cuda_sm86.cuh` 只聚合 `include/api/Arch.h` 和 `include/cuda_sm86/Arch.h`。
  2. 在 `Arch.h` 后端实现层补足 generated source 所需 detail helper。
  3. generated source 只通过 detail helper 使用这些能力。
  4. 同步文件级 API 列表，避免把 detail helper 写成包外公开 API。
- 验收与记录：include aggregate 不承载业务 kernel entry；`cuda_sm86::detail` 不进入 public API block；CUDA compile/runtime tests 通过。
- 合同验收：本任务无必过 `expectation`。

### S4. 按 final IR op/attr/region 补 target-specific emit handlers
- 为什么做：当前 `kernel/*.py` handler 返回 token，无法生成对应 op source。
- 做什么：为 9 demo current final IR inventory 中的 op、attrs 和 regions 补 CUDA emit handler 或 package-local emitter。
- 不做什么：不支持计划外 op；未知 op 必须 fail-fast；不为未出现 op 做投机泛化。
- 怎么验收：每个被覆盖 op 都能在 generated source 中看到 marker 和对应代码；source/hash 随 IR op sequence 变化。
- 卡住问谁：需要覆盖新 op 或扩大 demo 范围问用户；实现边界问架构师。

详细字段：
- 上下文：当前 `kernel_gen/dsl/gen_kernel/emit/cuda_sm86/kernel/*.py` 多数 handler 只返回 op token 或服务旧 family source；S2 的 SourceBundle builder 需要每个 final IR op handler 能按 operands、attrs、region 和 SSA dataflow 生成实际 CUDA 片段。
- 目标：为 S0 inventory 中的 host/control、arch、symbol、dma、memory 和 kernel op 补 target-specific emitter，使每个支持 op 都能产出 marker、hash 组件和语义对应的 CUDA source。
- 非目标：不为 9 demo 以外 op、kind、dtype、rank、space 或 region 形态做投机支持；不把 unsupported op 静默降级成 marker-only；不通过 old family source 兜底。
- 预期形态：每个支持 op handler 都写清 operands、results、attrs、region/yield 规则、SSA/env 绑定、生成 C++ 片段类别和 unsupported 边界；`kernel.matmul(out,lhs,rhs)` 在 CUDA target 下按 C5 处理 out/lhs/rhs 全 `tlm1` materialization，并保证 out 后续 consumer 或 write-back 可见。
- 正例：
  - `kernel.exp` handler 按 final IR named operands `out,input` 绑定，generated source 能证明 `exp_score = exp(shifted_score)` 与 `old_scale = exp(old_shift)` 未反置。
  - `dma.reinterpret/view/reshape` handler 生成 alias descriptor；`dma.copy/deslice/transpose/broadcast` handler 生成 materialization 写入，二者不混用。
  - `kernel.matmul(out_tlm1,lhs_tlm1,rhs_tlm1)` 写入 `out_tlm1` 后，后续 op 读取 `out_tlm1`，或在必要位置 copy / deslice 回原 out descriptor。
- 反例：
  - handler 只返回 `"kernel.matmul"` 或 `"kernel.exp"` marker，没有 operands / attrs 驱动的 CUDA source。
  - 继续把 matmul 完成态写成 `matmul{["", "tlm1", "tlm2"]}`、`matmul{["", "tlm2", "tlm1"]}` 或 `matmul{["tlm", "tlm", "tlm"]}`。
  - 生成 `copy(out -> out_tlm1) + matmul(out_tlm1, ...) + free(out_tlm1)` 后，后续 consumer 仍读旧 out，导致结果丢失。
- 模块范围：`kernel_gen/dsl/gen_kernel/emit/cuda_sm86/**`、相关 CUDA emit tests。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。
- 合同真源：S0 inventory > CUDA emit spec > pytest > 当前实现。
- 首批 op 覆盖：
  - host/control：`func.func`、`func.return`、`scf.if`、`scf.yield`、`tuner.select`。
  - arch：`arch.launch`、`arch.get_block_id`。
  - scalar/symbol：`arith.constant`、`builtin.unregistered(op_name__="symbol.const")`、`builtin.unregistered(op_name__="symbol.eq")`、`symbol.const`、`symbol.add/sub/mul/floordiv/min/max/ne`、`symbol.for`、`symbol.get_dim`、`symbol.cast`、`memory.get_data`。
  - dma：`dma.alloc/free/reinterpret/view/slice/deslice/copy/fill/broadcast/reshape/transpose`。
  - kernel：`kernel.matmul`、`kernel.binary_elewise(kind="add"|"sub"|"mul"|"truediv"|"max")`、`kernel.exp`、`kernel.reduce(kind="max"|"sum", keepdim=true, axis=1)`、`kernel.img2col2d`。
- 每类 op 必须写明：输入 operands、输出 values、关键 attrs、region/yield 规则、生成 C++ 片段类别、unsupported kind/attr 错误文本。
- 最小闭环：一个 9 demo final IR 可以从 host dispatcher 进入 device kernel，并通过上述 op handlers 完成 symbol/control/dma/kernel source 生成；遇到未覆盖 op 使用 C2 稳定错误文本 fail-fast。
- 当前必过合同验收：无 `expectation`；本任务验收依赖 emit pytest、CUDA runtime gate、hash/marker 断言和旧 family token 静态扫描。
- 执行步骤：
  1. 为 host/control/arch 建 dispatcher 和 region emission。
  2. 为 symbol/arith/builtin.unregistered 建表达式 emission 与稳定归一化。
  3. 为 dma/memory 建 descriptor emission。
  4. 为 kernel op 建 runtime helper 调用或 inline kernel body emission。
  5. 为每个 unsupported op/attr/type 加公开路径负例测试。
- 验收与记录：9 demo final IR source markers 覆盖上述 op 子集；未覆盖 op 的错误文本按 C2 确认口径稳定。
- 合同验收：本任务无必过 `expectation`。

### S5. 更新测试、CUDA runtime gate 和静态扫描
- 为什么做：旧测试主要证明三类 hardcoded source 不同；新测试必须证明 source 来自 final IR。
- 做什么：重写 / 补充 CUDA emit tests、include tests、pipeline/runtime tests 和 repo conformance tests。
- 不做什么：不把 expectation 当 diff 反推测试；不让测试 direct import/call package-local helper 或 `cuda_sm86::detail`。
- 怎么验收：计划列命令、diff 反推命令、静态扫描、repo conformance 和 CUDA runtime gate 全部记录 exit code。
- 卡住问谁：缺 CUDA 环境问管理员；现有测试无法表达最终 IR 时问架构师。

详细字段：
- 上下文：旧测试主要证明 matmul / conv2d / flash_attention 三类 hardcoded source 彼此不同，不能证明 generated source 来自 final IR traversal、SSA dataflow 或 C5 all-TLM1 matmul rule。
- 目标：用 pytest、CUDA runtime gate、hash 稳定性测试、SourceBundle 回归、private API boundary 和静态扫描证明 S1-S4 的新合同真实落地。
- 非目标：不把 `expectation/` 当 diff 反推测试；不通过 direct call package-local helper 或 `cuda_sm86::detail` 绕过公开入口；不把 CUDA 环境缺失记为通过。
- 预期形态：测试矩阵按 case 断言 markers/hash/source/runtime 行为，能区分真实 final IR op/attr/dataflow 变化；任务记录写清每条命令 exit code、CUDA passed/skipped 摘要、静态扫描命中分类和敏感目录快照。
- 正例：
  - 同一 final IR 在重复运行、`PYTHONHASHSEED=0` 和 `PYTHONHASHSEED=1` 下 `kg.cuda.ir.hash` 一致；删除或插入支持 op 后 hash/source 变化。
  - FA 三个 demo 的测试断言 `dma.reinterpret/copy/transpose/broadcast`、`kernel.reduce(max|sum)`、`kernel.exp(out,input)`、C5 `out/lhs/rhs -> tlm1` materialization 和 final output write-back。
  - 静态扫描证明候选实现 / 当前 spec / 当前 pytest 不再把 `CudaSm86ModuleSummary`、`emit_flash_attention_source` 或 `kg_cuda_sm86_run_flash_attention` 当当前真源。
- 反例：
  - 测试只断言 source 中出现 `// kg.cuda.ir.op: kernel.matmul`，但实现仍调用 family runner。
  - CUDA runtime test 因缺 `nvcc` 或缺 device skipped，却在任务记录写成通过。
  - repo conformance 继续要求旧 package-local exact set，或测试直接 import 新 package-local builder helper。
- 模块范围：`test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py`、`test/cuda/test_cuda_sm86_kernel_demos_runtime.py`、`test/execute_engine/test_cuda_sm86_strategy.py`、`test/repo_conformance/test_private_api_boundaries.py`、相关 spec。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。
- 合同真源：本计划验收设计 > pytest > CUDA runtime gate > 当前实现。
- 测试目标：
  - SourceBundle artifact 不变。
  - SourceBundle aggregate marker、`source.cpp` dump 和 artifact 写盘合同不变。
  - final IR markers 和 stable hash 存在且来自 traversal。
  - Flash Attention 三个 demo 的 marker / hash 覆盖 `dma.alloc/free/fill/view/deslice/reshape/reinterpret/copy/transpose/broadcast`、`tsm/tlm1` descriptor、C5 `matmul{["tlm1","tlm1","tlm1"]}` out/lhs/rhs materialization、`[dim,bc]` K-transpose target、`kernel.matmul` 两类调用点、`kernel.reduce(max|sum, axis=1, keepdim=true)`、`kernel.binary_elewise(max|sub|mul|add|truediv)`、`kernel.exp(out,input)` 与 final output write-back。
  - Flash Attention emit pytest 必须断言 `exp_score = exp(shifted_score)` 与 `old_scale = exp(old_shift)` 的 generated source / operand-role marker 不反置；不得只检查 `kernel.exp` marker 存在。
  - source 不含旧 family runner / selected kind。
  - 9 demo runtime 通过。
  - unknown final IR op/attr/type fail-fast。
  - `target="cuda_sm86"` 拒绝 target/include family mismatch 时继续返回 `failure_phrase == "target_header_mismatch"`。
  - include detail helper 不作为 public API。
- 最小闭环：至少能证明 SourceBundle artifact 合同不变、final IR traversal/hash 真实、旧 family source 被移除、C5 dataflow 可见、9 demo runtime 通过或明确环境阻塞。
- 当前必过合同验收：无 `expectation`；本任务只运行 pytest、CUDA runtime gate、静态扫描和敏感目录门禁。
- 执行步骤：
  1. 更新 emit pytest，覆盖 per-case marker/hash、重复生成稳定、`PYTHONHASHSEED=0` 与 `PYTHONHASHSEED=1` 跨 seed 稳定；可用 pytest 命令或测试内部 subprocess 比较同一 final IR 的 `kg.cuda.ir.hash`。
  2. 更新 runtime pytest，保持 9 demo hard gate。
  3. 更新 SourceBundle / execute_engine strategy pytest，确认 aggregate marker、`source.cpp` dump、artifact 写盘、CUDA include 和 failure phrase 不变；`test_cuda_sm86_compile_rejects_target_header_mismatch` 必须继续断言 `failure_phrase == "target_header_mismatch"`。
  4. 更新 repo conformance，移除旧 package-local exact set 反射或按用户确认改成新 exact set。
  5. 运行验收设计全部命令和敏感目录门禁。
- 验收与记录：任务记录写清 diff 反推自测、CUDA passed/skipped 摘要、静态扫描命中分类和敏感目录前后快照。
- 合同验收：本任务无必过 `expectation`。

## 迭代审阅记录

### Draft 0：架构主线草案
- 标准包：根 `AGENTS.md`、`agents/standard/计划书标准.md`、`agents/standard/审查规范.md`、用户最新反馈、当前 `cuda_sm86` emit/include 实现、`npu_demo` emit 逐 op 结构、当前计划全文。
- 严格通过口径：
  - 必须解决 CUDA emit/include 与最终 IR 脱节问题。
  - 不得继续把 family summary / hardcoded source 作为当前目标。
  - 不得新增未确认包外公开 API。
  - 9 demo runtime gate 与 CUDA 环境阻塞口径必须清楚。
  - 任何可维护性、测试有效性、边界完整性问题都不得通过。
- 主线处理：
  - 已把目标从 package structure refactor 改为 final-IR-driven backend。
  - 已明确删除 family source 真源。
  - 已写明 include detail primitive 边界。
- 状态：已进入 Codex subagent strict review 第 1 轮；结论不通过。

### Draft 1：subagent 第 1 轮返工草案
- 标准包：根 `AGENTS.md`、`agents/standard/计划书标准.md`、`agents/standard/审查规范.md`、`agents/standard/spec文件规范.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`、当前计划全文、当前 CUDA emit/include spec 与实现、`test/cuda/test_cuda_sm86_kernel_demos_runtime.py`、`test/repo_conformance/test_private_api_boundaries.py`、上一轮草案状态。
- 严格通过口径：
  - 无阻断、无最小需改项、无待确认项才可通过。
  - 不得越权新增、删除或重命名公开 API、package-local exact set、include ABI、slot ABI、pipeline 顺序或稳定错误文本。
  - final IR emit 必须定义到可执行的 op/attr/region/SSA/memory emission 规则。
  - 9 demo runtime gate 必须由 current final IR inventory 反推，不得只验证 family source 差异。
  - 测试必须证明 source 来自真实 traversal，不能只断言 marker。
- 已发起审阅任务：
  - `Descartes`（agent id `019e8ae7-7305-7893-84ef-b4941662e60b`）：API / 边界 / 流程严格审阅。
  - `Parfit`（agent id `019e8ae8-31e8-70e0-be72-eff9ef51bc02`）：实现可落地性 / 测试有效性 / 风险严格审阅。
- subagent 发现问题摘要：
  - `Descartes`：不通过。当前草案删除或替换 `spec/dsl/gen_kernel/emit/cuda_sm86.md` 中已记录的 package-local exact set，且未列为用户确认；总 spec `spec/dsl/gen_kernel/emit.md` 仍保留 family source 合同；API 列表省略签名、slot ABI、`kg_execute_entry` 和稳定 failure phrase；9 demo op inventory 不完整；验收遗漏 `test/repo_conformance/test_private_api_boundaries.py`；小任务卡缺少标准字段。
  - `Parfit`：不通过。草案把 `arch.get_dynamic_memory` 作为 final IR 主路径，但当前 `cuda-sm86-lowering` 公开合同不含 `MemoryPoolPass`；S2/S4 未定义 SSA value 环境、symbol expr、memory descriptor、region scope、`scf.if/yield`、`tuner.select`、`arch.launch` 绑定等可执行规则；首批 op 缺 `dma.alloc/free/slice/transpose`、`scf.yield`、`arith.constant`、`symbol.max` 和 `builtin.unregistered` 归一化；测试不足以证明 traversal source。
- 主线处理：
  - 已把计划状态改为第 1 轮不通过 / 主线返工中 / 不可下发。
  - 已把默认方案收口为“不改 `cuda-sm86-lowering` pipeline，覆盖当前 no-memory-pool final IR”，并把 pipeline memory-pool 方向列为用户已否定的备选。
  - 已用公开 lowering 路径提取 9 demo current final IR inventory，并写入当前基线与 S4。
  - 已补 `spec/dsl/gen_kernel/emit.md`、`test/repo_conformance/test_private_api_boundaries.py`、stable hash、per-case traversal marker、固定 hash seed 等验收要求。
  - 已把 package-local exact set 删除、unsupported-op 稳定错误文本、9 demo 范围和 pipeline 调整转为用户确认项。
  - 已补齐 S0-S5 小任务卡的禁止修改面、合同真源、最小闭环、执行步骤、验收记录与合同验收字段。
- 用户确认项收口：
  - C1-C4 已由用户在 2026-06-03 确认。
  - 当前已发起第 2 轮 Codex subagent strict review，基于用户确认后的最新计划文本继续收敛。
- Draft 1 当时状态：进入第 2 轮审阅；第 2 轮无阻断、无最小需改项、无待确认项前，不得进入守护最终检验。

### Draft 2：subagent 第 2 轮返工草案
- 标准包：根 `AGENTS.md`、`agents/standard/计划书标准.md`、`agents/standard/审查规范.md`、`agents/standard/spec文件规范.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`、当前计划全文、用户确认 C1-C4、第一轮问题处理摘要、当前 CUDA emit/include spec 与实现、CUDA runtime test 和 repo conformance test。
- 严格通过口径：
  - C1-C4 用户确认必须写入计划，且不得产生新的待用户确认项。
  - API/ABI 矩阵必须机械锁定 SourceBundle、`ArgSlot`、`kg_execute_entry` 与 ExecutionEngine failure phrase。
  - S2/S4 必须给出可直接执行的 final IR emission rules，不能只写“execute 定义”。
  - 9 demo inventory 必须与当前 no-memory-pool final IR 一致，尤其是 binary elewise kind 与关键 attrs。
  - hash seed、SourceBundle dump、CUDA runtime、repo conformance 必须进入验收。
- 已发起审阅任务：
  - `Carver`（agent id `019e8b19-b016-7dc1-b8bc-68eb7cc247a7`）：API / 边界 / 流程第二轮复审。
  - `Faraday`（agent id `019e8b19-ee23-7551-9f63-8e9e064aef4e`）：实现 / 测试第二轮复审；该 subagent 流断开，未形成有效结论。
  - `Planck`（agent id `019e8b1b-0b25-70d0-b579-5b9ca36b6a08`）：实现 / 测试第二轮补发复审。
- subagent 发现问题摘要：
  - `Carver`：不通过。SourceBundle 只列 artifact key，缺 aggregate marker `// __KG_BUNDLE_FILE__:<relative/path>`、`source.cpp` dump 行为和 `test/dsl/gen_kernel/test_source_bundle.py` 回归；`ArgSlot` 缺精确字段类型。
  - `Planck`：不通过。S2/S4 仍缺可落地 emission rules 表；9 demo attr inventory 中 `kernel.binary_elewise.kind` 写错，当前为 `add/sub/mul/truediv/max`，不是 `add/sub/min/max`；hash seed 验收缺 `PYTHONHASHSEED=0/1` 或等价 subprocess 门禁。
- 主线处理：
  - 已在 API 列表补 SourceBundle aggregate marker、`source.cpp` dump 与 artifact 写盘不变合同。
  - 已在 API 列表补 `ArgSlot` 精确字段类型与顺序：`int kind; void *data; long long *shape; long long *stride; unsigned long long rank; int dtype_code; long long int_value; double float_value;`。
  - 已新增 `test/dsl/gen_kernel/test_source_bundle.py` Diff 反推测试命令，并在 S5 写明 SourceBundle aggregate / dump / artifact 合同。
  - 已新增 `Final IR emission rules` 表，覆盖 host/control/arch/symbol/dma/kernel op 的输入、attrs、SSA/env、C++ 片段类别和 unsupported 规则。
  - 已修正 binary elewise kind inventory 和 primitive 覆盖为 `add/sub/mul/truediv/max`，并写明 `min` 不在 9 demo 中、首版 unsupported。
  - 已新增 `PYTHONHASHSEED=0` 与 `PYTHONHASHSEED=1` 的 IR hash pytest 门禁。
- Draft 2 当时状态：第 2 轮不通过项已主线返工；随后进入第 3 轮 Codex subagent strict review。下一轮无阻断、无最小需改项、无待确认项前，不得进入守护最终检验。

### Draft 3：subagent 第 3 轮返工草案
- 标准包：根 `AGENTS.md`、`agents/standard/计划书标准.md`、`agents/standard/审查规范.md`、`agents/standard/spec文件规范.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`、当前计划全文、用户确认 C1-C4、第二轮问题处理摘要、`spec/execute_engine/execute_engine_target.md`、`test/execute_engine/test_cuda_sm86_strategy.py`、`spec/dialect/arch.md`、`spec/dialect/dma.md`、`spec/dialect/kernel.md`、当前 CUDA emit/include spec 与实现。
- 严格通过口径：
  - API/ABI/failure phrase 矩阵必须覆盖当前 `target="cuda_sm86"` 公开执行引擎合同，不得遗漏现有稳定 failure phrase。
  - Final IR emission rules 必须按公开 dialect 签名机械书写，不能把 result alias op 与 target/source write op 混组。
  - `arch.launch` 必须显式消费四个 extent operand，不得只描述 callee 与 kernel args。
  - `kernel.matmul` 与 `kernel.img2col2d` 必须对齐公开 op operand/attr 签名，不得引入不存在的 descriptor 或 attr。
  - 无阻断、无最小需改项、无待确认项才可进入守护最终检验。
- 已发起审阅任务：
  - `Aristotle`（agent id `019e8b23-decb-7b81-813c-fea187aae553`）：API / 边界 / 流程第三轮复审。
  - `Newton`（agent id `019e8b24-206e-7d60-8ca8-04a38afcddd3`）：实现 / 测试第三轮复审。
- subagent 发现问题摘要：
  - API / 流程复审：不通过。`公开 API 设计` 漏写 `target_header_mismatch`，虽然 `spec/execute_engine/execute_engine_target.md` 与 `test_cuda_sm86_compile_rejects_target_header_mismatch` 已把 CUDA header family mismatch 锁定为该 failure phrase。
  - 实现 / 测试复审：不通过。`Final IR emission rules` 仍有三处不机械：把 `dma.slice/deslice/transpose` 和 `dma.reinterpret/view/reshape` 混成 alias result；`arch.launch` 漏写 `block/thread/subthread/shared_memory_size` 四个 extent operand；`kernel.img2col2d` 写成 input/weight/out descriptors 与 stride/dilation/padding/tile attrs，且 `kernel.matmul.acc` 未说明为静态 attr 或动态 i1 operand。
- 主线处理：
  - 已在 API 列表补 `target="cuda_sm86"` target/include family mismatch 仍以 `target_header_mismatch` 失败，并在 S5 写明 `test_cuda_sm86_compile_rejects_target_header_mismatch` 必须断言该 failure phrase。
  - 已把 `arch.launch` emission rule 改为公开文本签名 `arch.launch<block, thread, subthread, shared_memory_size>(@callee, args...)`，并明确四个 extent operand 的 symbol expr 解析、CUDA launch 维度 / shared memory 生成和 fail-fast 边界。
  - 已把 DMA emission rule 拆成 `dma.reinterpret/view/reshape` alias result 与 `dma.slice/deslice/transpose` target/source 写入两组，并写明 offsets/sizes/strides/perm、target 写入语义和 unsupported 边界。
  - 已把 `kernel.matmul` 改成 operands `out, lhs, rhs` 加可选动态 `acc:i1` operand、`space` 与可选静态 `acc` attr；明确 `acc` 不是 descriptor。
  - 已把 `kernel.img2col2d` 改成 operands `out, input, kh, kw, sh, sw, dh, dw, ph, pw, pl, pr` 与 attr `space`，并移除不存在的 weight descriptor / tile attrs 表述。
- Draft 3 当时状态：第 3 轮不通过项已主线返工；随后进入第 4 轮 Codex subagent strict review。第 4 轮无阻断、无最小需改项、无待确认项前，不得进入守护最终检验。

### Draft 4：subagent 第 4 轮通过草案
- 标准包：根 `AGENTS.md`、`agents/standard/计划书标准.md`、`agents/standard/审查规范.md`、`agents/standard/spec文件规范.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`、当前计划全文、用户确认 C1-C4、第 1-3 轮问题与主线处理记录、`spec/execute_engine/execute_engine_target.md`、`test/execute_engine/test_cuda_sm86_strategy.py`、`spec/dsl/gen_kernel/emit.md`、`spec/dsl/gen_kernel/emit/cuda_sm86.md`、`spec/include/cuda_sm86/cuda_sm86.md`、`spec/dialect/arch.md`、`spec/dialect/dma.md`、`spec/dialect/kernel.md`、相关 dialect 实现与 CUDA emit/runtime/source bundle/private API 测试。
- 严格通过口径：
  - 无阻断、无最小需改项、无待用户确认项才可通过。
  - API/ABI/failure phrase 矩阵必须覆盖 `compile_failed`、`target_header_mismatch`、`stream_not_supported`、`runtime_throw_or_abort/cuda_runtime_failed`。
  - Final IR emission rules 必须按公开 dialect 签名机械书写，特别是 `arch.launch` extent、DMA alias/write 分组、`kernel.matmul.acc` 与 `kernel.img2col2d` operands/attr。
  - 测试门禁必须覆盖 traversal/hash、SourceBundle、header mismatch failure phrase、CUDA 9 demo runtime gate 和 private API 边界。
- 已发起审阅任务：
  - `Aristotle`（agent id `019e8b23-decb-7b81-813c-fea187aae553`）：API / 边界 / 流程第四轮复审。
  - `Newton`（agent id `019e8b24-206e-7d60-8ca8-04a38afcddd3`）：实现 / 测试第四轮复审。
- subagent 收敛结论：
  - `Aristotle`：通过。阻断项：无；最小需改项：无；待用户确认项：无。核对确认 SourceBundle artifact/marker/dump、`ArgSlot`、`kg_execute_entry`、ExecutionEngine failure phrase 和 S5 `target_header_mismatch` 门禁已锁定。
  - `Newton`：通过。阻断项：无；最小需改项：无；待用户确认项：无。核对确认 `arch.launch` extent、DMA alias/write 分组、`kernel.matmul` / `kernel.img2col2d` / `binary_elewise` / `exp` / `reduce` operands 与 attrs、测试门禁均对齐公开真源。
- 主线处理：
  - 已按非阻断建议把 S3 primitive 覆盖中的 `slice/deslice/transpose descriptor construction` 改为 `slice/deslice/transpose materialization helper`，与 `Final IR emission rules` 中 target/source 写入型 op 口径一致。
- 最终同步确认：
  - `Newton` 确认上述 S3 小修订只对齐措辞，不改变第 4 轮通过结论；阻断项、最小需改项、待用户确认项仍为无。
  - `Aristotle` 确认上述 S3 小修订不改变 API、ABI、failure phrase、用户确认项或下发门禁；第 4 轮通过结论保持。
- Draft 4 当时状态：Codex subagent strict review 已收敛到无阻断、无最小需改项、无待确认项；随后用户指出 Flash Attention 所需 API 面尚未说完整，主线进入 Draft 5 补强。守护最终检验通过前，不得下发 execute。

### Draft 5：Flash Attention API matrix 补强草案
- 标准包：根 `AGENTS.md`、`agents/standard/计划书标准.md`、`agents/standard/审查规范.md`、`agents/standard/spec文件规范.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`、当前计划全文、用户反馈“FA 需要的 API 很多，你没说完”、用户确认 C1-C4、第 1-4 轮问题与主线处理记录、`kernel/flash_attention/inputs_static_tile_static.py`、`kernel/flash_attention/inputs_static_tile_dynamic.py`、`kernel/flash_attention/inputs_dynamic_tile_dynamic.py`、`test/kernel/test_flash_attention_symbolic_memory_genkernel.py`、`test/cuda/test_cuda_sm86_kernel_demos_runtime.py`、相关 dialect/spec/emit/include 文件。
- 严格通过口径：
  - 无阻断、无最小需改项、无待用户确认项才可通过。
  - FA API matrix 必须覆盖 online softmax attention 所需 entry/slot、symbol scalar、launch/control、scratch、alias/layout、score matmul、online softmax、state update 和 traversal proof API 面。
  - 不得借 FA 补强新增包外 Python API、跨 target include API、pipeline 顺序或新的稳定错误文本。
  - 不得把 FA 收口成 `kernel.flash_attention`、`kernel.softmax`、`emit_flash_attention_source(...)` 或 `kg_cuda_sm86_run_flash_attention` 这类整 kernel / family API。
  - S5 测试目标必须能证明三个 FA demo 的 marker / hash 覆盖 matrix 中的关键 op 组合。
- 主线处理：
  - 已新增 `Flash Attention required API matrix`，按 FA 需求层列出 package-local / detail API 面、对应 final IR / DSL 来源和验收重点。
  - Draft 5 初版已在 S5 测试目标中要求三个 FA demo 的 marker / hash 覆盖 `dma.alloc/free/fill/view/deslice/reshape/transpose/broadcast`、两类 `kernel.matmul` 调用点、`kernel.reduce(max|sum)`、`kernel.binary_elewise(max|sub|mul|add|truediv)`、`kernel.exp` 和 final output write-back；第 5 轮复审后已在下方 Draft 6 返工记录补齐 `dma.copy/reinterpret`、`tlm1/tlm2`、`[dim,bc]` 与 `kernel.exp(out,input)`。
  - 已保持 FA 补强不新增包外公开 API、不新增跨 target include API、不新增稳定错误文本。
- subagent 第 5 轮发现问题摘要：
  - `Aristotle`：通过。阻断项：无；最小需改项：无；待用户确认项：无。
  - `Newton`：不通过。阻断项包括：`kernel.exp` row 写成 `input,out`，与 IRDL named operands `out,input` 和 FA DSL `kernel.exp(exp_score, shifted_score)` 不一致；FA matrix / S5 漏掉当前 FA final IR 的 `dma.copy`、`dma.reinterpret`、`tlm1/tlm2` temporary descriptor 和 K transpose `[dim,bc]` memory hierarchy 覆盖。
- 第 5 轮主线返工：
  - 已修正 `kernel.exp` row：final IR / IRDL named operands 必须按 `out,input` 绑定，同时说明公开 constructor 可保持 `KernelExpOp(input_value, out, space)`，发射器不得按 constructor 参数顺序反置。
  - 已把 FA matrix 的 scratch / alias-layout / online-softmax 行扩展到 `dma.copy`、`dma.reinterpret`、`tsm/tlm1/tlm2` descriptor、K transpose `[dim,bc]` target 和 `kernel.exp(out,input)` operand-role 断言。
  - 已把 S5 测试目标扩展到 `dma.reinterpret/copy`、`tsm/tlm1/tlm2`、`[dim,bc]`、`kernel.exp(out,input)`，并要求断言 `exp_score = exp(shifted_score)`、`old_scale = exp(old_shift)` 不反置。
  - 以上修订仍在 C3/C4 已确认的 9 demo current final IR 范围内，不新增包外 API、pipeline 顺序或稳定错误文本。
- Draft 5 当时状态：第 5 轮不通过项已主线返工；随后进入第 6 轮 Codex subagent strict review。第 6 轮无阻断、无最小需改项、无待确认项前，不得进入守护最终检验。

### Draft 6：subagent 第 6 轮通过草案
- 标准包：根 `AGENTS.md`、`agents/standard/计划书标准.md`、`agents/standard/审查规范.md`、`agents/standard/spec文件规范.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`、当前计划全文、用户反馈“FA 需要的 API 很多，你没说完”、第 5 轮不通过结论与主线返工、用户确认 C1-C4、`kernel_gen/dialect/kernel/operation/unary.py`、`kernel/flash_attention/inputs_static_tile_static.py`、`kernel/flash_attention/inputs_static_tile_dynamic.py`、`kernel/flash_attention/inputs_dynamic_tile_dynamic.py`、`test/kernel/test_flash_attention_symbolic_memory_genkernel.py`、`test/cuda/test_cuda_sm86_kernel_demos_runtime.py`、相关 dialect/spec/emit/include 文件。
- 严格通过口径：
  - 无阻断、无最小需改项、无待用户确认项才可通过。
  - `kernel.exp` 必须按 IRDL / generic final IR named operands `out,input` 绑定，且不改变公开 constructor。
  - FA matrix / S5 必须覆盖 `dma.copy`、`dma.reinterpret`、`tsm/tlm1/tlm2` descriptor、K transpose `[dim,bc]` target 和 `kernel.exp(out,input)` 角色断言。
  - 返工不得新增包外 API、pipeline 顺序、稳定错误文本或整 kernel / family API。
- 已发起审阅任务：
  - `Aristotle`（agent id `019e8b23-decb-7b81-813c-fea187aae553`）：API / 边界 / 流程第六轮复审。
  - `Newton`（agent id `019e8b24-206e-7d60-8ca8-04a38afcddd3`）：Flash Attention 实现 / 测试第六轮复审。
- subagent 收敛结论：
  - `Aristotle`：通过。阻断项：无；最小需改项：无；待用户确认项：无。核对确认 Draft 6 未新增包外 API、跨 target include API、pipeline 顺序、稳定错误文本或未确认 public API；`kernel.exp` 修正不改变公开 constructor。
  - `Newton`：通过。阻断项：无；最小需改项：无；待用户确认项：无。核对确认第 5 轮指出的 `kernel.exp` 角色反置风险、`dma.copy/reinterpret`、`tlm1/tlm2`、`[dim,bc]` 与 FA marker/hash 覆盖均已收口。
- 最终同步确认：
  - `Newton` 确认 Draft 5 初版覆盖清单的历史措辞澄清不改变第 6 轮通过结论；阻断项、最小需改项、待确认项仍为无。
  - `Aristotle` 确认上述历史措辞澄清不改变第 6 轮 API / 边界 / 流程通过结论；阻断项、最小需改项、待确认项仍为无。
- 当前状态：Codex subagent strict review 已再次收敛到无阻断、无最小需改项、无待确认项；下一步必须由 `守护最好的爱莉希雅` 执行守护最终检验。守护最终检验通过前，不得下发 execute。

### Draft 7：`tlm1/tlm2` 口径事实复核草案
- 标准包：根 `AGENTS.md`、`agents/standard/计划书标准.md`、`agents/standard/审查规范.md`、`agents/standard/spec文件规范.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`、当前计划全文、用户反馈“CUDA pipeline 没有 TLM1 / TLM2 的区别，它们其实是同一个 tlm；KernelPatternAttachPass apply matmul op 时都是给 tlm”、用户确认 C1-C4、Draft 6 收敛记录、`kernel_gen/passes/tuning/kernel_pattern_attach.py`、`spec/pass/kernel_pattern_attach.md`、`kernel_gen/passes/tuning/dma_memory_hierarchy.py`、`spec/pass/lowering/dma_memory_hierarchy/spec.md`、`spec/pass/pipeline/cuda_sm86_lowering.md`、`spec/dialect/nn.md`、`spec/dialect/arch.md`、`spec/symbol_variable/memory.md`、`spec/target/registry.md`、`test/passes/test_kernel_pattern_attach.py`、`test/passes/test_dma_memory_hierarchy.py`、`test/symbol_variable/test_memory.py`。
- 严格通过口径：
  - 无阻断、无最小需改项、无待用户确认项才可通过。
  - 必须核清 `tlm` 是 `arch.barrier` visibility 聚合域，还是 `nn.memory` / DMA hierarchy 的真实 memory space。
  - 若当前 CUDA final IR / pass 真源使用 `#nn.space<tlm1|tlm2>`，计划正文和 S5 测试目标必须继续保留 `tsm/tlm1/tlm2` descriptor 覆盖。
  - 若审查发现必须改成旧 `tlm` memory space，则属于公开 memory space / pass 规则 /测试合同变更，必须列为待用户确认项，不得在本计划直接实现或下发。
- 主线事实核对：
  - `KernelPatternAttachPass` 的 `_PATTERN_PIPELINES` 当前固定为 `matmul{["", "tlm1", "tlm2"]}` 与 `matmul{["", "tlm2", "tlm1"]}` 两条 transform pipeline。
  - `LowerDmaMemoryHierarchyPass` 的 `apply_op` 规则目标集合为 `shared/local/tsm/tlm1/tlm2/tlm3`；规则列表按 `kernel.matmul` 的 `out/lhs/rhs` operand 映射，旧 `tlm` 不在该 memory space 集合内。
  - `spec/symbol_variable/memory.md` / `test/symbol_variable/test_memory.py` 锁定公开 TLM 空间拆分为 `TLM1/TLM2/TLM3`，且旧 `MemorySpace.TLM` 不再对外暴露。
  - `cuda_sm86` target registry 中 `tlm1/tlm2/tlm3_memory_size=0` 表示 CUDA 不通过 registry 暴露 TLM dynamic byte-pool 容量；不表示 DMA hierarchy 合并为单一 `tlm` memory space。
  - `arch.barrier` 的 `#arch.visibility<tlm>` 是 barrier 可见域聚合名，与 `#nn.space<tlm1|tlm2|tlm3>` descriptor space 不是同一 API 面。
- 自检：
  - 已运行 `pytest -q test/passes/test_kernel_pattern_attach.py test/passes/test_dma_memory_hierarchy.py test/symbol_variable/test_memory.py -k 'pattern_attach or apply_op_matmul_copies_lhs_rhs or tlm123_spaces'`，结果 `7 passed, 31 deselected, 1 warning`。
- 主线处理：
  - 不修改 `Flash Attention required API matrix` 与 S5 测试目标中的 `tsm/tlm1/tlm2` descriptor 覆盖。
  - 将用户反馈收口为事实复核项：当前仓库公开真源仍要求 `tlm1/tlm2` mixed-space matmul descriptor；把计划改成统一 `tlm` 会冲突公开 memory space / DMA hierarchy 合同。
- 已发起审阅任务：
  - `Beauvoir`（agent id `019e8da5-fd52-79c2-bd26-e9277ec6ca00`）：API / 边界 / 流程第七轮复审。
  - `Volta`（agent id `019e8da6-3f8e-7f40-a454-05f780daaa51`）：Flash Attention 实现 / 测试第七轮复审。
- subagent 收敛结论：
  - `Beauvoir`：通过。阻断项：无；最小需改项：无；待用户确认项：无。核对确认 `KernelPatternAttachPass` 与 `spec/pass/kernel_pattern_attach.md` 固定 `tlm1/tlm2` 与 `tlm2/tlm1` 两条 pattern，`LowerDmaMemoryHierarchyPass` / `nn` memory space 合同不含旧 `tlm`，`arch.barrier` 的 `#arch.visibility<tlm>` 不是 `#nn.space<tlm>`。
  - `Volta`：通过。阻断项：无；最小需改项：无；待用户确认项：无。核对确认 FA matrix / S5 保留 `tsm/tlm1/tlm2` descriptor 覆盖正确，且第 5/6 轮已收口的 `dma.copy/reinterpret`、K transpose `[dim,bc]`、两类 `kernel.matmul`、`kernel.exp(out,input)` 均未遗漏。
- 当前状态：第 7 轮 Codex subagent strict review 与守护最终检验曾通过；随后用户新增 C5，Draft 7 下发状态被覆盖，必须进入 Draft 8 重新收敛。

### Draft 8：CUDA `matmul{["tlm1","tlm1","tlm1"]}` 规则确认草案
- 标准包：根 `AGENTS.md`、`agents/standard/计划书标准.md`、`agents/standard/审查规范.md`、`agents/standard/spec文件规范.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`、当前计划全文、用户确认 C1-C5、Draft 7 subagent / 守护结论、用户最新确认“cuda 的 target 下，应该是 matmul{[\"tlm1\", \"tlm1\", \"tlm1\"]}”、`kernel_gen/pipeline/cuda_sm86_lowering.py`、`kernel_gen/passes/tuning/kernel_pattern_attach.py`、`kernel_gen/passes/tuning/dma_memory_hierarchy.py`、`spec/pass/kernel_pattern_attach.md`、`spec/pass/lowering/dma_memory_hierarchy/spec.md`、`spec/pass/pipeline/cuda_sm86_lowering.md`、`test/passes/test_kernel_pattern_attach.py`、`test/passes/test_dma_memory_hierarchy.py`、`test/passes/pipeline/test_cuda_sm86_lowering.py`、FA 三个 demo 与 CUDA emit/runtime tests。
- 严格通过口径：
  - 无阻断、无最小需改项、无待用户确认项才可通过。
  - C5 必须覆盖 CUDA target-specific DMA hierarchy matmul transform rule：完成态不得再使用 `matmul{["", "tlm1", "tlm2"]}` / `matmul{["", "tlm2", "tlm1"]}` 作为 CUDA target 的 pattern pipeline。
  - C5 不改变 C4：仍不接入 `MemoryPoolPass`，不把 CUDA final IR 改成 `arch.get_dynamic_memory` byte-pool 形态，不改变 `cuda-sm86-lowering` pass 顺序。
  - 若实现需要新增公开 `KernelPatternAttachPass` 参数、pipeline option、稳定错误文本或包外 API，必须列为待用户确认项；若可通过 CUDA pipeline 内部 wrapper / package-local implementation 收口且不改变公开入口，则不得扩大 API 面。
  - `matmul{["tlm1", "tlm1", "tlm1"]}` 对应 `kernel.matmul(out, lhs, rhs)` 三个 operand；execute 必须证明 out operand materialize 到 TLM1 后后续 consumer / write-back 仍语义可见，不能只复制到 TLM1 后在 matmul 后 free 掉导致数据丢失。
  - FA matrix / S5 必须从 `tsm/tlm1/tlm2` 覆盖更新为 `tsm/tlm1` 加 C5 out/lhs/rhs TLM1 materialization；不得继续把 TLM2 当作 CUDA 9 demo 完成态必需 descriptor。
- 主线处理：
  - 已把计划目标新增 C5：CUDA target 下 pattern transform 的 DMA hierarchy matmul rule 使用 `matmul{["tlm1", "tlm1", "tlm1"]}`。
  - 已把非目标从“不修改 pipeline”修正为“不修改 pipeline 顺序、不接入 `MemoryPoolPass`；但必须按 C5 调整 CUDA target-specific DMA hierarchy matmul transform rule”。
  - 已把 FA matrix / S5 测试目标中的 `tsm/tlm1/tlm2` descriptor 覆盖改为 `tsm/tlm1` descriptor + C5 out/lhs/rhs materialization 覆盖，并补充 out materialization 后 dataflow / write-back 必须可见。
  - Draft 7 的 `tlm1/tlm2` 事实复核仍是历史真源核对记录，但其“可下发”状态已被 C5 覆盖，不再作为当前下发依据。
- 自检：
  - 已运行 `rg -n "Draft 8|C5|matmul\\{\\[\\\"tlm1\\\", \\\"tlm1\\\", \\\"tlm1\\\"\\]|tsm/tlm1 descriptor|守护最终检验需重跑|不可下发" ARCHITECTURE/plan/cuda_sm86_final_ir_emit_backend_green_plan.md`，确认当前状态、C5、FA/S5 与重跑守护状态已写入。
  - 已运行 `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md` 与 `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`，均无输出。
  - 本轮只改计划文本，未运行未来实现 pytest；`matmul{["tlm1","tlm1","tlm1"]}` 相关 pytest 需由 execute 按 C5 新增 / 更新后运行。
- 已发起审阅任务：
  - `Mendel`（agent id `019e8dbe-3941-7c60-8ce7-fb95f2d48d1c`）：API / pipeline / 边界第八轮复审。
  - `Hubble`（agent id `019e8dbe-8202-7eb1-aede-01a5d26dd189`）：实现 / 测试 / dataflow 第八轮复审。
- subagent 收敛结论：
  - `Mendel`：通过。阻断项：无；最小需改项：无；待用户确认项：无。核对确认 C5 已写入目标 / 非目标，未变成 memory-pool / byte-pool 方向，未改变 pipeline 顺序；当前 `KernelPatternAttachPass` / spec 仍是旧双 pattern，Draft 8 已把 CUDA target-specific 完成态列为 execute 必改项。
  - `Hubble`：通过。阻断项：无；最小需改项：无；待用户确认项：无。核对确认 FA matrix / S5 已改为 `tsm/tlm1` + C5 out/lhs/rhs TLM1 materialization；当前 `_apply_matmul_rule` out target 只 copy/free、不写回的 dataflow 风险已被 Draft 8 锁为 execute 必做测试与实现项，无需新增用户决策。
- Draft 8 历史状态：第 8 轮 Codex subagent strict review 与守护最终检验曾收敛到无阻断、无最小需改项、无待确认项。
- 当前覆盖状态：随后用户指出计划书未按 `agents/standard/计划书标准.md` 写足小任务卡内容，要求每张小任务卡补齐 `预期形态 / 正例 / 反例`；因此 Draft 8 的“可下发”结论失效，当前进入 Draft 9 重新收敛。

### Draft 9：计划书标准格式返工草案
- 标准包：根 `AGENTS.md`、`agents/standard/计划书标准.md`、`agents/standard/审查规范.md`、`agents/standard/spec文件规范.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`、当前计划全文、用户最新反馈“计划书没有按照计划书标准的格式写，内容太少，每个小任务需要写清预期形态 / 正例 / 反例”、用户确认 C1-C5、Draft 8 技术收敛记录、当前禁止修改面、当前验收设计与无必过 `expectation` 口径。
- 严格通过口径：
  - 无阻断、无最小需改项、无待用户确认项才可通过。
  - 计划书必须满足 `agents/standard/计划书标准.md` 的必备结构，尤其是每张小任务卡都必须自包含，并写清 `为什么做 / 做什么 / 不做什么 / 怎么验收 / 卡住问谁` 与详细字段。
  - S0-S5 每张小任务卡必须都有 `上下文 / 目标 / 非目标 / 预期形态 / 正例 / 反例 / 模块范围 / 禁止修改面 / 合同真源 / 最小闭环 / 当前必过合同验收 / 执行步骤 / 验收与记录 / 合同验收`，短口径与详细字段不得冲突。
  - Draft 9 只做计划书格式与内容返工；不得改变 C1-C5 用户确认项、不得新增公开 API、不得修改 `expectation/`、不得下发 execute。
  - C5 必须继续锁定 CUDA target 下 `matmul{["tlm1", "tlm1", "tlm1"]}`，并保留 out materialize 到 TLM1 后 consumer / write-back 可见性要求。
- 主线处理：
  - 已在文档信息中说明 Draft 8 “可下发”状态因用户新增格式要求失效，当前 Draft 9 不可下发。
  - 已在文档信息中补齐目标 `spec`、公开 `API`、测试入口、验收资产和实现入口快速索引。
  - 已检查 S0-S3 已具备 `预期形态 / 正例 / 反例` 与当前必过合同验收字段。
  - 已补齐 S4 的上下文、目标、非目标、预期形态、正例、反例、最小闭环和当前必过合同验收；反例明确禁止旧双 pattern、统一 `tlm` memory space 和 `copy + matmul + free(out_tlm1) + 后续仍读旧 out` 数据流丢失形态。
  - 已补齐 S5 的上下文、目标、非目标、预期形态、正例、反例、最小闭环和当前必过合同验收；验收继续区分 diff 反推测试、CUDA runtime gate、静态扫描、敏感目录门禁和无必过 `expectation`。
  - 已按 API 复审收口 C2：仅 `unsupported cuda_sm86 final IR op: <op_name>` 是用户确认的稳定 exact 文本；unsupported attr/type 仍必须 fail-fast，但不得新增独立稳定 exact 文本，除非另行取得用户确认。
  - 已保留 Draft 0-Draft 8 为历史记录，不把旧通过结论作为当前下发依据。
- 已发起审阅任务：
  - `Boole`（agent id `019e8dd1-0fde-79c1-83a3-d2a34eafd563`）：API / 边界 / 公开合同第九轮复审。
  - `Gibbs`（agent id `019e8dd1-6341-7720-80b0-88de95c392ca`）：实现 / 测试 / dataflow 第九轮复审。
- subagent 第一组发现问题摘要：
  - `Boole`：最小需改项。问题 1：计划把 unsupported attr/type 写成独立稳定 exact 文本，但用户确认 C2 只锁定 `unsupported cuda_sm86 final IR op: <op_name>`；问题 2：`文档信息` 未按计划书标准快速列出目标 `spec`、公开 API、测试、验收资产和实现入口。
  - `Gibbs`：通过。阻断项：无；最小需改项：无；待用户确认项：无。核对确认 S0-S5 字段、C5 all-TLM1、out_tlm1 consumer/write-back 可见性、禁止旧双 pattern / 统一 `tlm` 反例、FA operand role、SourceBundle/hash、CUDA runtime gate、private API boundary 和敏感目录门禁均已覆盖。
- 第一组主线处理：
  - 已补齐 `文档信息` 五类快速索引。
  - 已删除 attr/type 独立稳定 exact 文本；C2 保留为 unsupported-op 稳定文本，attr/type 只作为必须 fail-fast 的非新增稳定错误语义。
- 自检：
  - 已运行 `rg -n "unsupported cuda_sm86 final IR (attr|type)" ARCHITECTURE/plan/cuda_sm86_final_ir_emit_backend_green_plan.md`，结果无命中。
  - 已运行 S0-S5 字段机械检查，结果 `S0-S5 missing: none`。
  - 已运行 `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md` 与 `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`，均无输出。
- 补审收敛结论：
  - `Boole`：通过。阻断项：无；最小需改项：无；待用户确认项：无。核对确认文档信息快速索引已补齐，attr/type 独立稳定 exact 文本已移除，C2 只保留已确认 unsupported-op 稳定文本，S0-S5 字段完整，Draft 8 历史通过不作为当前下发依据。
  - `Gibbs`：通过。阻断项：无；最小需改项：无；待用户确认项：无。核对确认最新修订未破坏 S4/S5、C5 all-TLM1、out_tlm1 consumer/write-back、FA operand role、hash/runtime/private API boundary 和敏感目录门禁。
- 当前状态：Draft 9 Codex subagent strict review 已收敛到无阻断、无最小需改项、无待确认项；`守护最好的爱莉希雅` 守护最终检验已通过，可通知管理员下发唯一计划级 `execute`。

### subagent strict review 收敛
- 已发起对象：`Descartes`、`Parfit`、`Carver`、`Faraday`、`Planck`、`Aristotle`、`Newton`、`Beauvoir`、`Volta`、`Mendel`、`Hubble`。
- 第 1 轮最终状态：两项均不通过；当前主线已按问题返工，且 C1-C4 已由用户确认。
- 第 2 轮最终状态：`Carver`、`Planck` 均不通过；`Faraday` 流断开，已由 `Planck` 补发同责审阅；当前主线已按第 2 轮问题返工。
- 第 3 轮最终状态：`Aristotle`、`Newton` 均不通过；当前主线已按第 3 轮问题返工。
- 第 4 轮最终状态：`Aristotle`、`Newton` 均通过；阻断项、最小需改项、待用户确认项均为无。
- 第 5 轮最终状态：`Aristotle` 通过；`Newton` 不通过；当前主线已按第 5 轮问题返工。
- 第 6 轮最终状态：`Aristotle`、`Newton` 均通过；阻断项、最小需改项、待用户确认项均为无。
- 第 7 轮最终状态：`Beauvoir`、`Volta` 均通过；阻断项、最小需改项、待用户确认项均为无。
- 第 8 轮最终状态：`Mendel`、`Hubble` 均通过；阻断项、最小需改项、待用户确认项均为无。
- 第 9 轮最终状态：`Boole`、`Gibbs` 均通过；阻断项、最小需改项、待用户确认项均为无。第一组中 `Boole` 提出的两项最小需改已主线修订并补审通过。
- 当前状态：Draft 9 Codex subagent strict review 已重新收敛；`守护最好的爱莉希雅` 守护最终检验已通过。
- 下发条件：已满足；所有已发起或计划要求的 Codex subagent strict review 均无阻断、无最小需改项、无待确认项，并由 `守护最好的爱莉希雅` 守护最终检验通过。

### 守护最终检验
- 结论人：`守护最好的爱莉希雅`
- 状态：Draft 9 通过，agent id `019e8dd8-6477-75f0-a3b1-7efd58483a37`；Draft 8 守护通过记录保留为历史，agent id `019e8dc1-b3f6-7702-817f-abb39fbf1dca`。
- 阻断项：无。
- 最小需改项：无。
- 待用户确认项：无。C5 的 out materialize 到 TLM1 后 dataflow / write-back 不是新决策项，已收成 execute 必须满足的机械语义约束。
- 已运行检查：
  - 已读取根 `AGENTS.md`、`agents/standard/计划书标准.md`、`agents/standard/审查规范.md`、`agents/standard/spec文件规范.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md` 和当前计划全文。
  - 已核对 `文档信息` 包含目标 `spec`、公开 `API`、测试入口、验收资产和实现入口快速索引。
  - 已核对 S0-S5 机械字段检查结果为 `missing: none`。
  - 已核对 `rg -n "unsupported cuda_sm86 final IR (attr|type)" ARCHITECTURE/plan/cuda_sm86_final_ir_emit_backend_green_plan.md` 无命中；attr/type 只保留 fail-fast 且不得新增独立 stable exact text 的口径。
  - 已核对 C5 active 完成态保持 `matmul{["tlm1", "tlm1", "tlm1"]}`；旧双 pattern 和 `["tlm","tlm","tlm"]` 只出现在历史事实或反例 / 禁止项中。
  - 已核对 Draft 9 收敛记录：`Boole`、`Gibbs` 均补审通过，无阻断、无最小需改项、无待确认项。
  - `git diff --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：无输出。
  - `git diff --cached --name-only -- expectation .skills agents/standard AGENTS.md TODO.md DONE.md`：无输出。
  - `expectation/`：未运行；计划正文明确本计划不列 `expectation/` 为必过合同验收资产，且 S0-S5 均写明无必过 `expectation`。
- 守护依据：
  - 根规范要求 subagent 持续收敛、用户确认公开 API / 稳定错误语义，且守护最终检验通过后才允许管理员下发。
  - 计划状态与 C1-C5 用户确认已写入；C5 保持 C4，不接 `MemoryPoolPass`、不改 `arch.get_dynamic_memory` byte-pool、不改变 pipeline 顺序。
  - Draft 9 已写入 CUDA target 完成态 `matmul{["tlm1", "tlm1", "tlm1"]}`，对应 `kernel.matmul(out, lhs, rhs)` 三个 memory operand。
  - FA matrix / S5 已改为 `tsm/tlm1` + C5 out/lhs/rhs TLM1 materialization，并要求 final output write-back。
  - Draft 9 明确旧 `tlm1/tlm2` 双 pattern 不能作为 CUDA 完成态，当前旧实现 / spec 被列为 execute 必改项。
  - out dataflow 风险已锁定：当前 `_apply_matmul_rule` 只 copy/free，Draft 9 要求 execute 证明 consumer / write-back 可见。
  - subagent 收敛记录完整到 Draft 9：`Boole`、`Gibbs` 均补审通过，无阻断、无最小需改项、无待用户确认项。
  - 守护结论：允许通知管理员下发唯一计划级 `execute`。

## 计划书入档验收 / 复验 / 修复复核记录
- 结论人：待定。
- 验证基线：待 execute 后记录。
- 执行目录：待 execute worktree。
- 合同验收摘要：本计划无必过 `expectation`。
- 最小阻断项或通过摘要：待定。

## 用户已确认项
- C1. 已确认：删除 / 替换当前 CUDA emit package-local exact set。
  - 当前 spec 已记录：`CudaSm86KernelFamily`、`CudaSm86ModuleSummary`、`detect_cuda_sm86_kernel_family(...)`、`summarize_cuda_sm86_module(...)`、`build_cuda_sm86_source_bundle(summary)`、`emit_matmul_source(summary)`、`emit_conv2d_source(summary)`、`emit_flash_attention_source(summary)`。
  - 用户确认：2026-06-03 用户答复“可以”。
  - 影响：execute 可以把这些 family-source API 替换为 final IR traversal package-local API；不进入包外 `__all__`，测试不得 direct call。
- C2. 已确认：新增 final IR unsupported-op 稳定错误语义。
  - 用户确认：2026-06-03 用户答复“是的”。
  - 确认口径：`unsupported cuda_sm86 final IR op: <op_name>`；unsupported attr/type 也必须 fail-fast，但不得新增独立稳定 exact 文本，除非另行取得用户确认。
- C3. 已确认：本计划完成态限定为 9 个现有 demo final IR op 集合。
  - 用户确认：2026-06-03 用户答复“可以”。
  - 确认口径：只覆盖 `kernel/{matmul,conv2d,flash_attention}/inputs_{static_tile_static,static_tile_dynamic,dynamic_tile_dynamic}.py` 这 9 个 demo 的 current final IR，不承诺任意 CUDA SM86 DSL kernel。
- C4. 已确认：维持当前 `cuda-sm86-lowering` no-memory-pool pipeline，不改成 memory-pool / `arch.get_dynamic_memory` byte-pool final IR。
  - 用户确认：2026-06-03 用户在推荐项解释后答复“可以”。
  - 确认口径：维持当前公开 pipeline，不引入 `MemoryPoolPass`；本计划 emit 覆盖当前 no-memory-pool final IR 中的 `dma.alloc/free/slice/transpose` 等 op。
- C5. 已确认：CUDA target 下 DMA hierarchy matmul transform rule 使用 `matmul{["tlm1", "tlm1", "tlm1"]}`。
  - 用户确认：2026-06-03 用户答复“cuda 的target 下，应该是 matmul{[\"tlm1\", \"tlm1\", \"tlm1\"]}”。
  - 确认口径：该 rule 对应 `kernel.matmul(out, lhs, rhs)` 三个 memory operand 均 materialize 到 `tlm1`；它覆盖 Draft 7 依据当前实现保留 `tlm1/tlm2` CUDA pattern 的下发结论。
  - 影响：execute 必须同步更新 CUDA target-specific pattern attach / transform apply spec、实现与测试；仍不接入 `MemoryPoolPass`，不改成 `arch.get_dynamic_memory` byte-pool final IR。若实现需要新增公开参数、pipeline option、稳定错误文本或包外 API，必须另行回用户确认。

## 用户确认与协同约束
- 用户确认方向：CUDA 后端的 emit 和 include 都需要围绕 DSL 最终 IR 重新设计，而不是继续 family source 方案。
- 本计划只做计划书和后续 execute 任务设计，不在计划阶段修改实现。
- 只按最新计划书流程：Codex subagent strict review 持续收敛；除守护最终检验外，不再走旧角色互评。
- execute 候选 diff 中 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md` 必须为空。
