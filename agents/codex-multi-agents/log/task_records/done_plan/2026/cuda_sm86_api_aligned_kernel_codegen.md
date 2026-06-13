# CUDA SM86 API Aligned Kernel Codegen Plan

## 文档信息

- 状态：Draft 10 / Round 4 clean worktree subagent strict review 已收敛 / 守护最终检验通过 / 等待下发依赖完成 / 当前不可分发。
- 计划文件：`ARCHITECTURE/plan/cuda_sm86_api_aligned_kernel_codegen.md`
- 计划任务名建议：`cuda-sm86-api-aligned-kernel-codegen`
- 计划级任务类型：唯一计划级 `execute`
- 建议 worktree：`/home/lfr/kernelcode_generate/wt-20260607-cuda-sm86-api-aligned-kernel-codegen`
- 建议记录文件：`agents/codex-multi-agents/log/task_records/2026/23/20260607-cuda-sm86-api-aligned-kernel-codegen.md`
- 固定流转：`execute -> review -> archive_acceptance / 计划书入档验收 -> merge / 归档`
- 下发依赖：
  - 默认必须等待 `T-20260607-0c4db1f1 / multi_buffer_loop_staging_ring` 完成、合并并同步到执行现场后再下发。
  - `T-20260607-0c4db1f1` 当前又依赖 `T-20260607-2b00a1ea / pass_dump_xdsl_pipeline_spec_options`，因此 CUDA execute 不应绕过这条链路。
  - 本计划当前不包含提前下发例外；若后续确需在依赖未完成前下发 CUDA execute，必须先取得用户明确确认并重新 strict review / 守护最终检验。
- 目标 `spec`：
  - `spec/dsl/gen_kernel/emit/cuda_sm86.md`
  - `spec/include/cuda_sm86/cuda_sm86.md`
  - `spec/pass/pipeline/cuda_sm86_lowering.md`
  - `spec/target/registry.md`
- 公开 `API` 快速索引：见 `公开 API 设计 / API 列表`；本计划不改变包外 Python API、工具参数、pipeline option 或 `kg_execute_entry` ABI。`include/cuda_sm86` wrapper 采用 Draft 7 A1，并按 2026-06-09 用户确认把 A1 外 wrapper 覆盖范围收口为“按 npu_demo 当前公开程度支持”；CUDA TLM fragment 只支持 `TLM1`，`TLM2/TLM3` unsupported。
- 测试入口快速索引：
  - `test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py`
  - `test/execute_engine/test_cuda_sm86_strategy.py`
  - `test/passes/pipeline/test_cuda_sm86_lowering.py`
  - `test/cuda/test_cuda_sm86_kernel_demos_runtime.py`
  - 计划内新增或扩展的 CUDA source semantic pytest。
- 验收资产快速索引：当前无必过 `expectation`；不授权修改、移动、重命名、新建或删除 `expectation/`。
- 实现入口快速索引：
  - `kernel_gen/dsl/gen_kernel/emit/cuda_sm86/**`
  - `include/cuda_sm86/cuda_sm86.cuh`
  - `include/cuda_sm86/Arch.h`
  - `kernel_gen/pipeline/cuda_sm86_lowering.py`
- 用户确认来源：
  - 用户指出当前 `cuda_sm86` 后端没有真正按 API/IR 语义生成 kernel，`dma.slice/load/copy` 等路径被固定封装锁死。
  - 用户确认希望 `cuda_sm86` 尽可能和现有 API 对齐，只有 `arch.launch`、`get_thread_id` 等 target 相关映射可不同。
  - 用户确认 TSM 到 TLM 不是 `cudaMemcpy`，而是 shared memory 到 fragment/register；GM 到 SM/fragment 也必须按 CUDA 设备内存层级解释。
  - 用户要求目标是真正生成 kernel 调用形式，输出也是 kernel 代码，并评估是否可以借助 CUTLASS/cuBLAS。
  - 用户要求先推进 multi-buffer loop staging ring 计划，再讨论并形成 CUDA 计划；本计划因此把 ring execute 合并结果列为默认下发依赖。
  - 2026-06-08 用户确认 target-sm 边界选择 A/A：`cuda_sm86` target / sm 来源采用“显式 target 唯一来源”；运行环境不满足 SM86 时不运行 CUDA runtime，不做 fallback，不用 fixed primitive 或其它 backend 替代。
  - 2026-06-08 用户确认可先建立任务；当时按“先创建待依赖任务、不分发、不执行”处理，不绕过 `multi_buffer_loop_staging_ring` 下发依赖。当前该任务已进入 TODO 正在执行列表且状态为暂停，见计划级任务段落。
  - 2026-06-09 用户纠正架构口径：`cuda_sm86` 不应继续沿 SourceBundle family fragment / 手写模板补丁路线推进，应改为类似 `npu_demo` 的 include 函数封装层，再由 emitc 把 final IR op 发射成这些 include 函数调用。
  - 2026-06-09 用户确认可以修订计划；本计划因此进入 Draft 6 / Draft 7 修订链路，旧 Draft 5 strict review / 守护最终检验结论只作为历史记录，不再作为当前可下发依据。
  - 2026-06-09 用户确认 matmul 第一阶段不允许 SIMT-only 作为通过路径；必须保持 `mma.sync` / `nvcuda::wmma` 参与最终 matmul 输出。
  - 2026-06-09 用户确认 include API 签名采用 Draft 7 推荐 A1：`cuda_sm86::` 公开 wrapper、签名尽量镜像 `npu_demo`、低层 Tensor Core / runtime helper 留在 `cuda_sm86::detail`、TLM 仅作为逻辑 fragment view；后续进一步确认 CUDA 只支持 `TLM1` fragment，`TLM2/TLM3` unsupported。
  - 2026-06-09 用户对 unsupported 错误文本回复“随意”；本计划按推荐项收口为不新增稳定 unsupported 文本，测试只断言现有错误体系、非稳定前缀或 fail-fast 行为。
  - 2026-06-09 用户确认 `cuda_sm86::copy/free/view/reshape/reinterpret/launch/block_num/subthread_*` 按照 `npu_demo` 当前程度支持；本计划据此只把 `cuda_sm86::launch` 和一维 generated-source `cuda_sm86::view(...)` 写成 public wrapper，`reshape` 走 `Memory::reshape(...)` 成员，`copy/free/reinterpret/block_num/subthread_*` 不新增同名 public wrapper。
  - 2026-06-09 用户确认 CUDA TLM fragment 只需要 `TLM1` 表示，`TLM2/TLM3` 不支持。
  - 2026-06-13 用户明确确认本任务需要改成 `sm_89`。本确认覆盖此前 `SM86 CUDA device runtime` 硬门槛；当前任务后续完成态以 `nvcc + SM89 CUDA device` runtime 精度验收通过为准，不再等待 SM86 环境。执行链必须同步修订 spec、pytest、runtime preflight、任务记录和入档口径中仍残留的 SM86 runtime 硬门槛；若需要把包外 target 名、目录名或公开 API 从 `cuda_sm86` 重命名为 `cuda_sm89`，必须先列出 exact API 影响面并回用户确认。
- 外部参考说明：
  - NVIDIA CUDA Programming Guide、cuBLAS 文档和 CUTLASS 文档只作为设计参考，不是当前必过验收资产。
  - 本计划不把外部文档中的具体版本号写成固定合同；execute 阶段若引用版本或 API 细节，必须在任务记录写清实际核对来源。
- 计划文件跟踪要求：
  - `ARCHITECTURE/plan/` 当前被 `.gitignore` 忽略。
  - Draft 7 已按榕 prompt 要求让计划文件进入 tracked/index diff；进入新一轮 strict review、请求守护最终检验或提交管理员前，必须记录 `git ls-files --stage`、`git diff --name-status` 和 `git status --short --ignored --untracked-files=all` 证据。
  - Draft 5 守护最终检验已在旧 guard worktree 锁定过 tracked/index diff 证据；Draft 6 因改变公开 include API 边界，必须重新取得 tracked/index diff 证据、strict review 和守护最终检验。

## 计划级任务

| 计划任务 | 任务类型 | worktree | 记录文件 | 流转 |
| --- | --- | --- | --- | --- |
| `cuda-sm86-api-aligned-kernel-codegen` | 唯一计划级 `execute` | 管理员下发时创建 | `agents/codex-multi-agents/log/task_records/2026/23/20260607-cuda-sm86-api-aligned-kernel-codegen.md` | `execute -> review -> archive_acceptance -> merge/归档` |

- 当前已有计划级 execute 任务：`T-20260608-bfe97ae7`；位于 `TODO.md` 的“正在执行的任务”，依赖 `T-20260607-0c4db1f1`，指派 `金铲铲大作战`，状态为 `暂停`。本计划修订不得新建第二个 execute；Draft 9 后续 strict review 收敛、守护最终检验通过且下发依赖完成 / 合并 / 同步后，由管理员决定恢复现有暂停任务、重定任务目标或重新分发。

任务目标：为 `target="cuda_sm86"` 添加 npu_demo-like include 函数封装层与 final-IR-driven emitc lowering，使 `gen_kernel(..., target="cuda_sm86")` 生成与 final IR dataflow 对齐的 `kernel.cu` 和 `generated_entry.cuh`。host `kg_execute_entry` 保持现有 ABI，只负责 slot decode、host/device 边界搬运、launch 和结果回写；generated source 通过 `include/cuda_sm86` 的 target 函数封装表达 `arch`、`dma`、`kernel`、`symbol` op 语义，emitc 负责把 final IR op / operand / shape / stride / space / symbol dataflow 发射为这些函数调用。验收结果必须证明 matmul 和 conv2d 的静态、动态 IR 都能生成可编译、可运行、精度合格的 CUDA kernel，并且 unsupported IR 稳定 fail-fast。

计划级边界：
- 一个计划书只创建一个计划级 `execute`；S0-S8 只是计划内小任务卡，不创建独立 TODO。
- `execute` 必须一次完成本计划内 spec、实现、测试、验收和记录闭环。
- 本计划不得混入 `multi_buffer_loop_staging_ring` 的实现任务，也不得回改已经通过守护的 ring 计划正文。
- 本计划不得混入 memory-pool 后 CSE、pass directory layout、DMA ring 历史任务或其它无关现场。

## 计划目标

- 生成形态必须改变：
  - `kernel.cu` 中存在与 final IR hash / entry 绑定的 generated `__global__` kernel。
  - `kernel.cu` 不再以固定 `kg_cuda_sm86_execute_matmul_ir`、`kg_cuda_sm86_execute_img2col2d_ir`、`kg_cuda_sm86_execute_reduce_exp_ir` 作为主业务入口。
  - `kg_execute_entry(cuda_sm86::ArgSlot *slots, unsigned long long count)` ABI 不变，只做 slot decode、host/device 边界搬运、kernel launch、CUDA error check 和结果回写。
  - `include/cuda_sm86` 必须提供类似 `npu_demo` 的 target 函数封装层；CUDA generated source 的主业务逻辑由 emitc 逐 op 发射这些封装调用，不再由 `source_bundle.py` 根据 family 注入整段固定业务 fragment。
  - device kernel body 由 final IR op、operand、shape、stride、space 和 symbol expression 通过 emitc 调用链生成。final IR 变化必须改变可执行 body 的函数调用、operand 绑定和数据搬运，而不只是 marker/hash 变化。
- CUDA memory hierarchy 语义必须对齐：
  - `global` 表示 CUDA device global memory。
  - `tsm` 表示 block 级 shared memory，不是 host memory，不用 `cudaMemcpy` 表示 TSM/TLM 内部搬运。
  - CUDA 第一阶段只支持 `tlm1` 表示 register tile、Tensor Core fragment 或 warp-local fragment 类对象，不是可 `cudaMemcpy` 的设备指针；`tlm2/tlm3` unsupported / fail-fast。
  - `dma.view`、`dma.reshape`、`dma.reinterpret` 默认是 descriptor/view/fragment view 变化，不做数据复制。
  - `dma.copy`、`dma.slice`、`dma.deslice`、`dma.load`、`dma.store`、`dma.fill`、`dma.broadcast`、`dma.transpose` 必须按源 space 和目标 space 选择 CUDA device-side lowering。
- matmul 和 conv2d 是第一阶段完成态：
  - matmul 的 static shape、dynamic shape、present bias、absent bias 变体都必须从 final IR 生成 device kernel body。
  - conv2d 的 static shape 和 dynamic shape 都必须从 final IR 生成 device kernel body。
  - conv2d 可以采用 direct convolution lowering，也可以采用 implicit GEMM / tiled img2col lowering；默认不得把整张 img2col 物化成 global 中间结果，除非 final IR 明确要求 global materialization。
- multi-buffer / ring 语义必须接入 CUDA lowering：
  - `global` ring 通过 device pointer offset 或 descriptor cursor 表示。
  - `tsm` ring 通过 shared memory backing + cursor offset 表示。
  - `tlm1` ring 只能在可静态证明安全时表示为固定 fragment/register slot；`tlm2/tlm3` ring unsupported / fail-fast。
  - 对于 accumulator / output tile，K reduce loop 内不得每个 K tile 都 advance；如果 alloc 属于 K 累加维度，advance 生命周期必须延后到外层 output tile loop。若没有可轮转的外层 output tile loop，ring `num = 1`。
  - 若 multi-buffer pass 后所有 scratch alloc 都统一 ring-backed，`cuda_sm86` lowering 必须支持 `num = 1` 的非流水 ring，并按生命周期结束点插入 / 发射 advance；不得按每个 use 机械 advance。
- 精度和失败边界必须明确：
  - matmul 第一阶段默认遵守当前 `cuda_sm86` spec：真实 `mma.sync` 或 `nvcuda::wmma` 路径必须参与最终 matmul 输出；SIMT-only 只能作为待用户确认的 spec 变更，不得作为本计划默认完成态。
  - Tensor Core / TF32 path 只能使用当前 CUDA runtime preflight 或 spec 明确允许的 tolerance；不得为了通过测试无依据放宽 tolerance。
  - unsupported op、dtype、layout、rank、target space、dynamic TLM ring 或无法证明的 alias 必须 fail-fast，不得静默回退到旧固定 kernel。
- target / sm 选择边界必须明确：
  - `target="cuda_sm86"` 必须只来自调用方传入 `gen_kernel` / `ExecutionEngine` / pipeline 的显式选择，不由 CUDA codegen 从 IR 或 runtime 反推。
  - `cuda_sm86` codegen 只允许读取 `spec/target/registry.md` 中已注册的 `cuda_sm86` 能力和 memory 参数，不得根据 `cudaGetDeviceProperties`、`cudaDeviceGetAttribute`、compute capability、slot dtype/shape 或 final IR 特征重新选择 `cuda_sm86` / 其它 target。
  - 运行时设备不满足 SM89 CUDA 需求时，不运行 CUDA runtime；只能在调用 `kg_execute_entry`、`cuda_sm86::launch` 或任何 CUDA runtime API 之前 fail-fast / skip 并记录环境原因，不允许 fixed primitive、cuBLAS/cuBLASLt、其它 CUDA sm 或其它 backend fallback 作为本计划完成态。
  - 非 SM89 gate 属于执行策略、测试 harness、CI/调度环境标签或管理员验收现场的前置门禁；generated source、`kg_execute_entry`、`cuda_sm86::launch` 和 include wrapper 不负责查询设备能力、推断 sm 或选择 target。
  - 若测试诊断为了记录 skip 原因读取设备属性，必须在调用 `kg_execute_entry` / `cuda_sm86::launch` 前完成，只能决定 skip / fail-fast，不能改变 target、不能 fallback，也不能作为 generated path 的一部分。
- CUTLASS/cuBLAS 取舍必须明确：
  - cuBLAS/cuBLASLt 是 host library API，第一阶段只可作为精度 / 性能对照或后续另立计划输入；不得作为非 SM89 runtime fallback，也不能替代“按 IR 生成 `__global__` kernel body”的主目标。
  - CUTLASS 更适合作为后续可选高性能模板来源，尤其 GEMM/conv；但强制引入 CUTLASS 会改变构建环境和 generated source 合同，本计划第一阶段不把它设为必需依赖。
  - 本计划允许做 CUTLASS/cuBLAS 只读调研和环境 gated compile-probe，不允许在未获确认时把它们变成必过依赖。

## 非目标

- 不修改 `.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。
- 不修改、移动、重命名、新建或删除 `expectation/`。
- 不新增、删除、重命名或修改包外 Python 公开 API。
- 不修改跨 target `include/api/**` 公开 API。
- 不新增、删除或重命名 `kg_execute_entry`、`cuda_sm86::ArgSlot` 字段、SourceBundle artifact key、Python 包外公开 API 或工具入口。
- 允许在用户 2026-06-09 确认方向下新增 / 重组 `include/cuda_sm86/**` target 专属函数封装层；具体公开签名清单采用 Draft 7 A1 并已获用户确认，A1 清单之外的新增公开签名必须暂停并回用户确认。
- 不新增 pipeline option、脚本参数或公开稳定错误文本；若 execute 发现必须新增，必须暂停并回用户确认。
- 不新增 target / cuda sm 推断逻辑；不得把 `cuda_sm86` codegen 写成根据设备 compute capability、IR 形态或 slot 信息动态选择 target 的机制；非 SM89 设备不运行本计划 CUDA runtime。
- 不把 cuBLAS/cuBLASLt 作为主完成态，因为库调用不是本仓库 IR 驱动生成的 device kernel body。
- 不把 CUTLASS 作为第一阶段必需依赖；是否引入 CUTLASS 正式依赖必须另行确认。
- 不承诺任意未知 DSL kernel 都可生成 CUDA；第一阶段覆盖 matmul/conv2d 相关 final IR 和当前 CUDA runtime demo 已覆盖的必要 op，未知 op 稳定失败。
- 不引入 CUDA memory-pool pipeline 变更；若未来要把 CUDA lowering 改成 memory-pool 形态，必须另开计划。
- 不把本计划作为 `multi_buffer_loop_staging_ring` execute 的一部分。

## 当前基线

- `spec/dsl/gen_kernel/emit/cuda_sm86.md` 当前已要求 generated source 包含 CUDA aggregate include、`__global__` marker、真实 Tensor Core `mma.sync` 或 `nvcuda::wmma` 执行路径和 `kg_execute_entry(slots, count)` C ABI。
- `spec/pass/pipeline/cuda_sm86_lowering.md` 当前公开 builder 是 `build_cuda_sm86_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager`，并明确当前 pipeline 不包含 `MemoryPoolPass`。
- `spec/target/registry.md` 中 `cuda_sm86` target 约束 `tsm_memory_size=49152`，`tlm1/tlm2/tlm3_memory_size=0`，说明 TLM 不是普通动态 byte pool。
- target registry 只作为已选 `cuda_sm86` target 的能力 / memory 参数查询来源；不得升级为 CUDA SM 推断或 runtime target selection 机制。
- `kernel_gen/dsl/gen_kernel/emit/cuda_sm86/source_bundle.py` 当前会遍历 final IR 生成 trace/hash/marker，但 `operation_source_fragments(...)` 仍根据 op family 注入整段固定 implementation fragment。
- `kernel_gen/dsl/gen_kernel/emit/cuda_sm86/kernel/*.py` 当前单 op emit 主要返回 final IR marker，不像 `npu_demo` backend 那样把 IR op 发射成 target include 函数调用。
- 当前 fixed primitive 主入口包括：
  - `kg_cuda_sm86_execute_matmul_ir`
  - `kg_cuda_sm86_execute_img2col2d_ir`
  - `kg_cuda_sm86_execute_reduce_exp_ir`
- 当前 matmul fixed primitive 已含 `mma.sync` 路径，但它只接收固定 out/lhs/rhs/bias 形态，不能表达 final IR 中的 `dma.slice/view/reinterpret/copy` dataflow。
- 当前 conv/img2col fixed primitive 按 slot shape 和固定参数计算，不是从 final IR 的 shared/register staging、view、slice、transpose、deslice 等 op 逐步生成。
- `spec/include/cuda_sm86/cuda_sm86.md` 当前明确 aggregate header 不直接承载 memory/scalar/copy/allocation/TF32 helper 实现，并要求具体 matmul / conv2d / flash_attention kernel entry、host wrapper 与 device kernel 由 generated source 局部实现；该旧口径和用户 2026-06-09 确认的 npu_demo-like include 函数封装路线冲突。
- `include/cuda_sm86/Arch.h` 当前已有 `cuda_sm86::ArgSlot`、`cuda_sm86::detail::MemoryDescriptor`、host/device copy、device allocation、`to_tf32` 等 helper，但缺少面向 emitc 的系统化 CUDA target 函数封装层、device-side TSM/TLM descriptor、fragment object、space-pair copy lowering。
- 当前 tests 更多证明“有 CUDA source / 有 Tensor Core marker / runtime demo 能跑”，不足以证明每个 IR op 的 device 语义真实参与 kernel body。
- 当前 `multi_buffer_loop_staging_ring` 计划已通过守护，但 execute 依赖尚未完成并合并；CUDA execute 必须等待它产出稳定 final IR 语义，否则会和 ring lowering / spec / test 并行覆盖。

## 方案比较与选型

### 不采用 A：继续 fixed primitive，只增加 source marker

- 优点：实现小，当前 demo 容易继续通过。
- 问题：IR 变化仍不会改变 device kernel 的真实计算逻辑。
- 问题：无法表达用户要求的 `dma.slice/load/copy`、TSM/TLM、ring lifecycle 和 dynamic shape。
- 结论：不满足“真正 kernel 调用形式”和 API/IR 语义对齐。

### 不采用 B：把 TSM/TLM 都映射成 device pointer 并用 `cudaMemcpy`

- 优点：表面上容易统一 copy 代码。
- 问题：`cudaMemcpy` 是 host/runtime 层 API，不能表达 device kernel 内 shared memory 到 register fragment 的 load/store。
- 问题：TLM fragment 不是内存指针；把 fragment 当 byte buffer 会破坏 Tensor Core / MMA lowering。
- 结论：不符合用户确认的 CUDA memory hierarchy 语义。

### 不采用 C：用 cuBLAS/cuBLASLt 完成 matmul/conv2d 主路径

- 优点：成熟、高性能，cuBLASLt 对 GEMM 有丰富调参能力。
- 问题：它是 host library API，调用库内部 kernel，不是本仓库 final IR 逐 op 生成的 `__global__` kernel body。
- 问题：conv2d 需要额外 im2col 或 cuDNN 类接口，进一步偏离本仓库 final IR 语义。
- 结论：可作为校验 / 性能对照或后续另立计划输入；不得作为非 SM89 runtime fallback，不作为第一阶段主完成态。

### 谨慎采用 D：CUTLASS 作为可选高性能模板来源

- 优点：CUTLASS 是 CUDA C++ template library，覆盖 GEMM、conv、MMA/copy atom，方向上更接近“生成 kernel code”。
- 风险：强制依赖 CUTLASS 会改变构建环境、include 路径、编译时间和 generated source 合同。
- 风险：CUTLASS pattern matching 需要先有稳定 final IR semantic lowering，否则只是把 fixed primitive 换成 fixed template。
- 结论：第一阶段不强制引入；只做只读 feasibility probe。后续若用户确认，可在第二阶段把 eligible GEMM/conv pattern 替换为 CUTLASS-backed generated kernel。

### 不采用 E：继续在 SourceBundle builder 内部实现 API/IR 对齐 CUDA codegen core

- `SourceBundle` 以 final IR 为真源，生成 host entry 和 device kernel。
- device lowering 先实现 memory space model、descriptor/view、space-pair copy、symbol expression、control flow，再覆盖 matmul/conv2d op。
- matmul 首版必须让 `mma.sync` / `wmma` fragment path 参与最终输出；conv2d 首版可用 direct conv 或 tiled implicit GEMM path。
- CUTLASS/cuBLAS 只作为外部参考、可选对照或后续替换，不阻塞主闭环。
- 问题：如果这些逻辑仍主要落在 `source_bundle.py` 的 generated source fragment 拼装中，`kernel/*.py` 仍只是 marker emit，就没有对齐现有 `npu_demo` 的 emitc 分层，后续会继续在大字符串模板里修补 dataflow。
- 结论：不作为 Draft 6 主方案。

### 采用 F：npu_demo-like include 函数封装 + emitc lowering

- `include/cuda_sm86` 提供 target 专属函数封装层，按 `Arch / Memory / Dma / Kernel` 语义承接 CUDA host/device helper、descriptor、space-pair lowering、fragment / Tensor Core primitive 和 launch 包装。
- `kernel_gen/dsl/gen_kernel/emit/cuda_sm86/**` 像 `npu_demo` backend 一样通过 emit registry 逐 op 发射函数调用；`kernel/*.py` 不再只返回 marker。
- `ModuleOp` / SourceBundle assembly 负责 artifact、include、hash marker、entry 和 wrapper 拼装，不负责按 family 注入固定业务 source fragment；`operation_source_fragments(...)`、`select_entry_symbol(...)`、`CUDA_SM86_KERNEL_*_FRAGMENT` 和固定 `kg_cuda_sm86_execute_*_ir` 不得作为主计算真源或 `kg_execute_entry` 可达路径。
- `generated_entry.cuh` 和 `kg_execute_entry` ABI 保持稳定；新增 include 函数封装必须先在 spec 中列出签名、公开 / detail 边界和用户确认来源。
- CUDA-specific Tensor Core / runtime 细节可以封装在 `cuda_sm86::detail`，但 emitc 正向路径必须通过稳定的 target include 调用层表达 final IR op 语义。
- 结论：采用。该方案改变 Draft 5 公开 include API 边界，必须重新 strict review、用户确认函数签名清单并请求 `守护最好的爱莉希雅` 本人守护最终检验。

## 公开 API 设计

### 功能简介

本计划保持 Python 包外入口、SourceBundle artifact key 和 `kg_execute_entry` C ABI 不变，但按用户 2026-06-09 确认方向新增 / 重组 `include/cuda_sm86` target 专属函数封装层。该层对齐 `npu_demo` 的 emitc 习惯：IR op emit 不直接拼固定业务 kernel fragment，而是发射 `cuda_sm86` include 函数调用；CUDA-specific runtime、Tensor Core 和 helper 实现可继续封装在 `cuda_sm86::detail`。

### API 列表

- 保持不变：`emit_c(obj: SSAValue | Operation | func.FuncOp | ModuleOp, ctx: EmitCContext) -> str`
- 保持不变：`gen_kernel(obj: Operation | func.FuncOp | ModuleOp, ctx: EmitCContext) -> str`
- 保持不变：`emit_c_impl(ModuleOp, target="cuda_sm86")` registry handler 入口，不作为包外 direct-call API。
- 保持不变：`emit_c_include_impl(target="cuda_sm86")` registry handler 入口，不作为包外 direct-call API。
- 保持不变：`build_cuda_sm86_lowering_pipeline(options: dict[str, str] | None = None) -> PassManager`
- 保持不变：`class ExecutionEngine(target: str, compiler: str | None = None, compiler_flags: tuple[str, ...] = ("-std=c++17",), link_flags: tuple[str, ...] = ())`
- 保持不变：`ExecutionEngine.compile(source: str | None = None, function: str | None = None, *, request: CompileRequest | None = None, entry_point: str = "kg_execute_entry") -> CompiledKernel`
- 保持不变：`CompiledKernel.execute(args: tuple[RuntimeInput, ...] | None = None, *, request: ExecuteRequest | None = None, entry_point: str | None = None, capture_function_output: bool = False, stream: None = None) -> ExecuteResult`
- 保持不变：SourceBundle artifact key `kernel.cu`
- 保持不变：SourceBundle artifact key `include/cuda_sm86/generated_entry.cuh`
- 保持不变：`extern "C" int kg_execute_entry(cuda_sm86::ArgSlot *slots, unsigned long long count)` C ABI。
- 保持不变：包外 include API `namespace cuda_sm86`
- 保持不变：包外 include API `struct cuda_sm86::ArgSlot` 字段、顺序和语义。
- 新增 / 重组：`include/cuda_sm86` target 专属函数封装层，按下列类别在 `spec/include/cuda_sm86/cuda_sm86.md` 中列出 exact signatures：
  - `cuda_sm86` launch / entry wrapper：按 `npu_demo::launch` 当前程度承接 static extent public `cuda_sm86::launch<...>`；generated host entry 只能在 SM89 环境已被外部前置门禁确认后调用该 wrapper 发起 CUDA kernel launch，wrapper 自身不做设备能力探测、sm 推断或 target 选择。
  - `cuda_sm86` memory / descriptor wrapper：承接 global、tsm、`tlm1` descriptor、shape、stride、offset、rank、dtype 和 alias/view；CUDA 第一阶段不支持 `tlm2/tlm3` fragment。
  - `cuda_sm86` DMA wrapper：A1 已确认承接 `alloc`、`make_ring`、`DmaRing::current()`、`DmaRing::advance()`、`load/store/slice/deslice`、`fill/broadcast/transpose` 的 space-pair lowering；`copy/free/reinterpret` 按 `npu_demo` 当前程度不新增同名 public wrapper。
  - `cuda_sm86` kernel wrapper：承接 `matmul`、`img2col2d` / conv tile gather、`binary_elewise`、`reduce`、`exp`。
  - `cuda_sm86::detail` helper：承接不进入公开 API 的 Tensor Core fragment、TF32、host/device copy、CUDA error check、device allocation 和低层 runtime helper。
- 用户确认候选 A1：公开 wrapper 采用 `cuda_sm86::` 正向命名空间，签名形状尽量镜像 `npu_demo`，低层 CUDA runtime / Tensor Core helper 留在 `cuda_sm86::detail`。以下 exact signature 清单为本计划获确认的 include 公开 API 边界：

| 类别 | 公开 API 签名 | host/device 边界 | emitc 是否正向调用 | 错误语义 |
| --- | --- | --- | --- | --- |
| launch | `template <long long block, long long thread, long long subthread, long long shared_memory_size, auto name, typename Context, typename... Args> Status cuda_sm86::launch(Context& ctx, Args&&... args)` | host function compiled by `nvcc` | host entry / generated glue 正向调用 | static extents only；`subthread != 1`、非法 extent fail-fast；只发起 CUDA kernel launch 并传播 launch/runtime error，不查询设备能力、不推断 sm、不 fallback |
| arch context | `class cuda_sm86::KernelContext;` | `__device__` 使用 | 否；作为 device wrapper `Context&` 实参类型之一 | public opaque type；A1 不公开 constructor / public method，构造与状态访问留在 `cuda_sm86::detail` |
| arch block id | `__device__ S_INT cuda_sm86::block_id()` | `__device__` | 是 | 不新增稳定错误文本 |
| arch thread id | `__device__ S_INT cuda_sm86::thread_id()` | `__device__` | 是 | 不新增稳定错误文本 |
| arch thread num | `__device__ S_INT cuda_sm86::thread_num()` | `__device__` | 是 | 不新增稳定错误文本 |
| arch sync | `__device__ void cuda_sm86::barrier()` | `__device__` | 是 | 无返回错误；映射 `__syncthreads()` |
| alloc | `template <MemorySpace Space, typename T, typename Context> __device__ Memory<Space, T> cuda_sm86::alloc(Context& ctx, const Vector& shape, const Vector& stride, MemoryFormat format = MemoryFormat::Norm)` | `__device__` | 是 | unsupported `Space` / dynamic TLM 形态由 emit 阶段 fail-fast |
| ring type | `template <MemorySpace Space, typename SlotT, typename BackingT> class cuda_sm86::DmaRing` | `__device__` methods | 是 | `num <= 0`、unsupported dynamic TLM 由 emit 阶段 fail-fast |
| ring current | `template <MemorySpace Space, typename SlotT, typename BackingT> __device__ Memory<Space, SlotT> cuda_sm86::DmaRing<Space, SlotT, BackingT>::current() const` | `__device__` | 是 | 不新增稳定错误文本 |
| ring advance | `template <MemorySpace Space, typename SlotT, typename BackingT> __device__ Memory<Space, SlotT> cuda_sm86::DmaRing<Space, SlotT, BackingT>::advance()` | `__device__` | 是 | advance 位置由 emitc 生命周期分析控制 |
| make ring | `template <typename SlotT, MemorySpace Space, typename BackingT> __device__ cuda_sm86::DmaRing<Space, SlotT, BackingT> cuda_sm86::make_ring(Memory<Space, BackingT>& backing, S_INT num, S_INT offset_bytes, std::initializer_list<long long> shape, std::initializer_list<long long> stride, MemoryFormat format = MemoryFormat::Norm)` | `__device__` | 是 | unsupported / unsafe ring 由 emit 阶段 fail-fast |
| fill | `template <MemorySpace Space, typename T, typename Context> __device__ Status cuda_sm86::fill(Context& ctx, Memory<Space, T>& target, const T& value)` | `__device__` | 是 | 返回 `kError`；不新增稳定文本 |
| slice | `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, typename Context> __device__ Status cuda_sm86::slice(Context& ctx, Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)` | `__device__` | 是 | unsupported space pair 由 emit 阶段 fail-fast |
| deslice | `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, typename Context> __device__ Status cuda_sm86::deslice(Context& ctx, Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)` | `__device__` | 是 | unsupported space pair 由 emit 阶段 fail-fast |
| load | `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context> __device__ Status cuda_sm86::load(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& offset, const Vector& size, const Vector& stride)` | `__device__` | 是 | unsupported space pair 由 emit 阶段 fail-fast |
| store | `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context> __device__ Status cuda_sm86::store(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& offset, const Vector& size, const Vector& stride)` | `__device__` | 是 | unsupported space pair 由 emit 阶段 fail-fast |
| transpose | `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context> __device__ Status cuda_sm86::transpose(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& perm)` | `__device__` | 是 | unsupported rank/layout 由 emit 阶段 fail-fast |
| broadcast | `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context> __device__ Status cuda_sm86::broadcast(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source)` | `__device__` | 是 | unsupported broadcast 由 emit 阶段 fail-fast |
| one-dimensional view | `template <MemorySpace Space, typename T> __host__ __device__ Memory<Space, T> cuda_sm86::view(const Memory<Space, T>& source, long long offset, long long size, long long stride)` | host/device inline wrapper | 是，仅作为 `npu_demo::view` 同程度 generated-source compatibility wrapper | 仅用于 `global/tsm` 等 pointer-view space；多维 pointer view 使用 `Memory::view<T>(...)`；`TLM1/TLM2/TLM3` 不走该 public wrapper，emit 阶段 fail-fast 或转 package-local fragment descriptor glue |
| add | `template <MemorySpace Space, typename InType, typename OutType, typename Context> __device__ Status cuda_sm86::add(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)` | `__device__` | 是 | unsupported dtype 由 emit 阶段 fail-fast |
| sub | `template <MemorySpace Space, typename InType, typename OutType, typename Context> __device__ Status cuda_sm86::sub(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)` | `__device__` | 是 | unsupported dtype 由 emit 阶段 fail-fast |
| mul | `template <MemorySpace Space, typename InType, typename OutType, typename Context> __device__ Status cuda_sm86::mul(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)` | `__device__` | 是 | unsupported dtype 由 emit 阶段 fail-fast |
| truediv | `template <MemorySpace Space, typename InType, typename OutType, typename Context> __device__ Status cuda_sm86::truediv(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)` | `__device__` | 是 | unsupported dtype 由 emit 阶段 fail-fast |
| max | `template <MemorySpace Space, typename InType, typename OutType, typename Context> __device__ Status cuda_sm86::max(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)` | `__device__` | 是 | unsupported dtype 由 emit 阶段 fail-fast |
| exp | `template <MemorySpace Space, typename InType, typename OutType, typename Context> __device__ Status cuda_sm86::exp(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& input)` | `__device__` | 是 | unsupported dtype 由 emit 阶段 fail-fast |
| reduce sum | `template <MemorySpace Space, typename InType, typename OutType, typename Context> __device__ Status cuda_sm86::reduce_sum(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)` | `__device__` | 是 | only supported axis/keepdim patterns pass |
| reduce max | `template <MemorySpace Space, typename InType, typename OutType, typename Context> __device__ Status cuda_sm86::reduce_max(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)` | `__device__` | 是 | only supported axis/keepdim patterns pass |
| matmul | `template <MemorySpace LhsSpace, MemorySpace RhsSpace, MemorySpace OutSpace, typename LhsType, typename RhsType, typename OutType, typename Context> __device__ Status cuda_sm86::matmul(Context& ctx, Memory<OutSpace, OutType>& out, const Memory<LhsSpace, LhsType>& lhs, const Memory<RhsSpace, RhsType>& rhs, bool acc = false)` | `__device__` | 是 | must route to `mma.sync` / `wmma`; unsupported shape/layout fail-fast at emit |
| img2col2d | `template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType, typename Context> __device__ Status cuda_sm86::img2col2d(Context& ctx, Memory<OutputSpace, OutType>& out, const Memory<InputSpace, InType>& input, long long kh, long long kw, long long sh, long long sw, long long dh, long long dw, long long ph, long long pw, long long pl, long long pr)` | `__device__` | 是 | unsupported layout/padding/dilation fail-fast at emit |
| detail-only runtime | `cuda_sm86::detail::check_cuda`、slot guard、host/device copy、device allocation、TF32 conversion、Tensor Core fragment primitive | mixed host/device | 否，除 generated source 内部 glue 外不作为 emitc 正向 op 调用 | 复用现有 `cuda_runtime_failed`；不新增稳定文本 |

- Launch/context 约束：`cuda_sm86::launch<...>(Context& ctx, Args&&...)` 中的 `Context& ctx` 是 host launch descriptor / generated glue context，不是 device `cuda_sm86::KernelContext&`。generated `__global__` kernel 必须在 device 侧通过 `cuda_sm86::detail` 或 generated glue 构造 `cuda_sm86::KernelContext`，再把该 device context 传给 generated `__device__` body 和 device wrapper calls；不得把 host context 指针或引用传入 device business body。
- A1 约束：CUDA wrapper 签名中只允许 `Memory<TLM1, T>` 作为 emit 表面的逻辑 tile / fragment view，不表示可 `cudaMemcpy` 的 device pointer；具体 register fragment、WMMA fragment 或 local register array 由 `cuda_sm86::detail` 承接。`TLM2/TLM3` 在 CUDA 第一阶段 unsupported / fail-fast。
- TLM1 fragment view 约束：`Memory<TLM1, T>` 只能由 CUDA generated fragment 路径产生，例如 `alloc<TLM1>`、load 到 fragment、`DmaRing<TLM1>` 的 `current/advance`、matmul detail/glue 或等价 generated fragment glue。generated source 不得对 `Memory<TLM1, T>` 发射 `data()`、`at()`、`Memory::view(...)`、`Memory::reshape(...)` 或 `cuda_sm86::view(...)`；TLM1 subview / reinterpret / reshape 只能走 package-local/detail fragment descriptor glue，不能实现时必须 fail-fast。
- 用户已确认：上述新增 / 重组 include 函数封装采用 Draft 7 A1，并按 `npu_demo` 当前程度补充 `cuda_sm86::launch` 与一维 `cuda_sm86::view(...)`；`reshape` 使用 `Memory::reshape(...)` 成员；`copy/free/reinterpret/block_num/subthread_*` 不新增同名 public wrapper；`cuda_sm86::detail` 只承接低层 Tensor Core / runtime helper；emitc 正向调用公开 `cuda_sm86::` wrapper 或现有 `Memory` 成员。
- A1 不新增 `cuda_sm86::block_num()`、`cuda_sm86::subthread_id()` 或 `cuda_sm86::subthread_num()` 公开 wrapper；`arch.get_block_num`、`arch.get_subthread_id`、`arch.get_subthread_num` 在本计划第一阶段由 emitc 直接生成 CUDA 内建表达式或常量。

### 稳定错误语义

- 本计划不新增公开稳定错误文本。
- execute 可以在现有错误体系内补充 package-local unsupported diagnostics。
- 如果为了测试或用户可见行为必须新增稳定错误文本，必须暂停并把具体文本、触发条件和兼容影响提交用户确认。

### package-local 边界

- execute 可以在 `kernel_gen/dsl/gen_kernel/emit/cuda_sm86/` 包内新增或重组 package-local helper，但必须：
  - 更新对应功能实现文件的文件级 `功能说明 / API 列表 / 使用示例 / 关联文件`。
  - 不进入 `cuda_sm86.__all__` 或跨包 public path。
  - 不让测试 direct import 当前文件之外的非公开 helper。
  - 不使用运行时能力探测写法，例如 `hasattr(ctx, ...)`、`getattr(ctx, ..., ...)`、`callable(getattr(...))` 来绕过 spec。
  - 不在非装饰器场景中新增函数体内嵌套函数。
- 推荐内部结构：
  - `source_bundle.py`：artifact assembly、hash marker、generated entry header 和 public handler bridge；不再承载 family 固定业务 fragment 真源。
  - `module.py`：继续作为唯一 `ModuleOp` registry handler。
  - `kernel/*.py`、`dma/*.py`、`arch/*.py`、`symbol/*.py`：对齐 `npu_demo` emit 风格，逐 op 发射 `include/cuda_sm86` 函数调用。
  - `ir_context.py`：SSA value、descriptor、symbol expression、scope、name binding。
  - `host.py`：`kg_execute_entry`、slot decode、host/device boundary copy、launch。
  - `device.py`：`__global__` kernel signature、block/thread mapping、device function body。
  - `memory.py`：global/shared/fragment descriptor 和 lifetime model。
  - `dma.py` 或 `dma/*.py`：space-pair lowering。
  - `kernel.py` 或 `kernel/*.py`：matmul、conv/img2col2d、binary、reduce、exp lowering。
- 上述内部结构只是建议，不是逐文件白名单；execute 可以按模块内质量需要调整，但不得突破公开 API 和禁止修改面。
- `include/cuda_sm86` 的新增函数封装不是 package-local Python helper；它们属于 target include 层，必须先在 `spec/include/cuda_sm86/cuda_sm86.md` 明确公开 / detail 边界和 exact signature。测试不得 direct call `cuda_sm86::detail::*`；公开 wrapper 的验证应通过 generated source / emitc / runtime preflight。

## CUDA memory hierarchy 设计

| DSL space | CUDA 对应 | 允许的物理承载 | 禁止解释 |
| --- | --- | --- | --- |
| `global` | device global memory | kernel 参数 device pointer、global descriptor | host pointer、TSM scratch、TLM byte pool |
| `tsm` | block shared memory | `extern __shared__` 或静态 `__shared__` arena 内 descriptor | `cudaMemcpy` 目标、host-visible allocation |
| `tlm1` | register tile / Tensor Core fragment | scalar register array、WMMA fragment、inline PTX MMA operand | device pointer、dynamic byte pool |
| `tlm2` | unsupported in CUDA first stage | fail-fast | device pointer、dynamic byte pool、fragment path |
| `tlm3` | unsupported in CUDA first stage | fail-fast | device pointer、dynamic byte pool、fragment path |

### descriptor 规则

- `global` descriptor 包含 device pointer、shape、stride、rank、dtype、offset。
- `tsm` descriptor 包含 shared arena offset、shape、stride、rank、dtype。
- `tlm1` descriptor 包含 fragment/register object id、shape、layout、dtype、accumulate state；`tlm2/tlm3` descriptor 在 CUDA lowering 中 fail-fast。
- `global/tsm` 的 `view/reshape/reinterpret` 只改变 descriptor 元数据，不复制数据。
- `tlm1` 的 view-like 变化不是 pointer offset：只能由 package-local/detail fragment descriptor glue 在可证明安全的子集内表达；generated source 不得对 `Memory<TLM1, T>` 发射普通 pointer-view API，不能证明时 fail-fast。
- `copy/slice/deslice/transpose/broadcast/fill` 是写入型 materialization，必须根据 target/source space 选择 device-side lowering。

### space-pair lowering 规则

| 操作 | 源 space -> 目标 space | CUDA lowering |
| --- | --- | --- |
| load/copy | `global -> tsm` | cooperative global load 到 shared；首版可用 scalar load/store，后续可替换 `cp.async` |
| load/copy | `global -> tlm1` | global load 到 register tile 或 WMMA fragment load |
| load/copy | `tsm -> tlm1` | shared load 到 register tile、`ldmatrix` 或 WMMA load |
| store/copy | `tlm1 -> tsm` | fragment/register store 到 shared |
| store/copy | `tsm -> global` | shared store 到 global |
| store/copy | `tlm1 -> global` | fragment/register store 到 global |
| copy | `tlm1 -> tlm1` | register move、fragment conversion 或 accumulator transfer |
| any | `tlm2/tlm3 -> *` or `* -> tlm2/tlm3` | unsupported / fail-fast |
| copy | `tsm -> tsm` | shared memory loop copy |
| copy | `global -> global` | device global copy loop；只用于 IR 明确要求的 global materialization |
| slice/deslice | 任意支持 space pair | source window descriptor + target materialization；`deslice` 方向是 source tile 写回 target window |
| transpose | `tsm/tlm1/global` 支持子集 | small tile transpose，优先 shared/register 内完成 |
| broadcast/fill | `tsm/tlm1/global` 支持子集 | device loop 或 register fill；不调用 host runtime copy |

### ring lowering 规则

- `global` ring：
  - static `num` 使用 pointer offset 或 descriptor cursor。
  - dynamic `num` 必须能从 symbol expression 证明 ring segment stride 和 bounds；否则 fail-fast。
- `tsm` ring：
  - static `num` 使用 shared arena 上的 ring segment。
  - dynamic `num` 必须能在 shared memory budget 内证明上界；否则 fail-fast。
- `tlm1` ring：
  - `num == 1` 直接使用单 fragment/register slot。
  - small static `num` 可展开为固定 fragment/register slot 数组。
  - dynamic 或 large `num` 默认不生成 CUDA TLM ring；必须让 upstream lowering 避免该形态，或在 CUDA lowering fail-fast。
- `tlm2/tlm3` ring：
  - CUDA 第一阶段不支持，必须 fail-fast。
- accumulator / output ring lifecycle：
  - 如果 alloc 属于 K/reduce 累加维度，acc fragment 的 advance 不能发生在每个 K tile 尾部。
  - 若存在外层 output tile loop，advance 发生在 output tile 完成后。
  - 若没有外层 output tile loop 可轮转，ring `num = 1`。
  - 对 target 指定的 ring `num`，必须以 target 配置为上界并结合 alloc 生命周期分析；不能只用普通内存 ring 的 num 计算逻辑。

## op lowering 完成态

| IR op | 完成态 |
| --- | --- |
| `arch.launch` | host 端生成 `cuda_sm86::launch<block, thread, subthread, shared_memory_size, generated_kernel>(host_ctx, args...)`；`cuda_sm86::launch` 内发起 `<<<grid, block, shared_bytes>>>`，callee 是 generated `__global__` kernel；generated `__global__` 内部构造 device `cuda_sm86::KernelContext` 并调用 generated `__device__` body；第一阶段只支持 static extents。 |
| `arch.get_block_id` | device 端通过 `cuda_sm86::block_id()` 映射到 `blockIdx.x`，只在 spec 支持轴上生成。 |
| `arch.get_thread_id` | device 端通过 `cuda_sm86::thread_id()` 映射到 `threadIdx.x`，只在 spec 支持轴上生成。 |
| `arch.get_thread_num` | device 端通过 `cuda_sm86::thread_num()` 映射到 `blockDim.x`。 |
| `arch.get_block_num` | A1 不新增 public wrapper；emitc 直接生成 `gridDim.x` 表达式。 |
| `arch.get_subthread_id/get_subthread_num` | A1 不新增 public wrapper；`subthread == 1` 时直接生成常量 `0` / `1`，其它值 fail-fast。 |
| `symbol.get_dim/get_stride` | 从 descriptor shape/stride 生成 device/host scalar expression，支持 dynamic shape。 |
| `symbol` arithmetic / compare / cast ops | 生成 C++ scalar expression；unsupported dtype 或非整数控制表达式 fail-fast。 |
| `dma.alloc/free` | `tsm` 从 shared arena 分配 descriptor；`tlm1` 创建 fragment/register object；`tlm2/tlm3` fail-fast；普通 kernel body 内不做 host/device allocation；`dma.free` 不生成同名 public wrapper。 |
| `dma.reinterpret/view/reshape` | `global/tsm` 走 alias descriptor；一维 pointer-view 可走 `cuda_sm86::view(...)`，多维 pointer-view / reshape 走 `Memory::view<T>(...)` / `Memory::reshape(...)`；`TLM1` 只能走 package-local/detail fragment descriptor glue 或 fail-fast；不复制数据。 |
| `dma.copy/load/store/slice/deslice` | 按 space-pair 生成 device-side load/store/materialization。 |
| `dma.fill/broadcast/transpose` | 按目标 descriptor 生成 device loop 或 fragment/register op。 |
| `kernel.matmul` | TLM/register fragments 走 `mma.sync` / `wmma` 并参与最终输出；`acc` 决定覆盖写或累加写。SIMT-only 若要作为第一阶段通过路径，必须先作为 spec 变更回用户确认。 |
| `kernel.img2col2d` | 默认不物化整张 global img2col；按 conv tile 生成 gather 到 `tsm/tlm1`，必要时显式 fail-fast。 |
| `kernel.binary_elewise` | 生成 register/shared/global elementwise device code，支持当前 final IR 已出现 kind。 |
| `kernel.reduce` | 支持当前 final IR 需要的 row-wise max/sum 和 keepdim 形态；其它形态 fail-fast。 |
| `kernel.exp` | 生成 device-side exp，不用 host library path。 |

## matmul / conv2d 预期形态

### Matmul generated source 形态

```cuda
extern "C" int kg_execute_entry(cuda_sm86::ArgSlot *slots, unsigned long long count) {
  // Decode ArgSlot, allocate/copy global boundary buffers when current ExecutionEngine provides host memory.
  kg_cuda_sm86_kernel_<hash><<<grid, block, shared_bytes>>>(
      out_gm, lhs_gm, rhs_gm, bias_gm, dynamic_dims...);
  // Copy final global output back to current runtime output slot.
}

__global__ void kg_cuda_sm86_kernel_<hash>(
    float *out, const float *lhs, const float *rhs, const float *bias,
    long long m, long long n, long long k, ...) {
  extern __shared__ unsigned char smem[];
  // IR: global -> tsm load for A/B tile.
  // IR: tsm -> tlm fragment load.
  // IR: kernel.matmul on tlm fragments, using mma.sync/wmma.
  // IR: optional bias/binary op in register/shared.
  // IR: tlm/tsm -> global store.
}
```

验收重点：
- static/dynamic `m/n/k` 不可按 demo 名称硬编码。
- present/absent bias 必须来自 IR operand/branch。
- `tlm` 不表现为 `cudaMemcpy` pointer。
- `kernel.matmul` 的 `acc` 语义必须正确；reduce/K 累加维度中的 accumulator 不能在每个 K tile 尾部错误 advance 或清零。

### Conv2d generated source 形态

```cuda
__global__ void kg_cuda_sm86_kernel_<hash>(
    float *out, const float *input, const float *weight, const float *bias, ...) {
  extern __shared__ unsigned char smem[];
  // IR: compute output tile coordinates from block/thread ids.
  // IR: gather input window from global to shared/register tile.
  // IR: load weight tile to shared/register tile.
  // IR: direct conv inner loop or implicit GEMM tile.
  // IR: optional bias/activation.
  // IR: store output tile to global.
}
```

验收重点：
- dynamic batch/channel/spatial dim 来自 descriptor 和 symbol expression。
- `img2col2d` 如果存在于 IR，默认解释为 tile gather，不默认生成全局 full img2col buffer。
- conv2d 也要满足 shared/register fragment semantics，不能退回 fixed host-side family runner。

## 完成态定义

- `gen_kernel(..., target="cuda_sm86")` 输出的 SourceBundle：
  - 包含 `kernel.cu` 和 `include/cuda_sm86/generated_entry.cuh`。
  - `kernel.cu` 中存在 final-IR-specific `__global__` kernel。
  - `kernel.cu` 中不再以固定 `kg_cuda_sm86_execute_matmul_ir` / `kg_cuda_sm86_execute_img2col2d_ir` / `kg_cuda_sm86_execute_reduce_exp_ir` 作为主业务入口。
  - source marker/hash 仍保留，但测试必须扫描可执行 body 的 op-specific include wrapper calls、operand binding 和 space-pair lowering，不得只测 marker 或 hash。
  - `kernel_gen/dsl/gen_kernel/emit/cuda_sm86/kernel/*.py` 的单 op emit 必须产生真实 CUDA target include 调用语句或明确 unsupported，而不是只返回 marker token。
- `ExecutionEngine(target="cuda_sm86")`：
  - 当前 ABI 不变。
  - 在有 `nvcc` 和 SM89 CUDA GPU / SM89 CUDA device 的环境下，matmul/conv2d demo 能编译运行并通过精度验收。
  - 在无 `nvcc` 或无 SM89 CUDA device/GPU（包括只有非 SM89 CUDA device）的普通本地预检现场，外部 runtime preflight 可在调用 `kg_execute_entry` / `cuda_sm86::launch` 前记录 skip，但 source tests、pipeline tests、compile command construction tests 必须运行；最终计划通过必须取得 SM89 GPU runtime 精度验收结果。
- `cuda_sm86` spec：
  - 记录 global/tsm/tlm memory hierarchy 语义。
  - 记录 npu_demo-like include 函数封装层、公开 / `detail` 边界和 exact signatures。
  - 记录 ring lowering policy。
  - 记录 cuBLAS/cuBLASLt 非主完成态、CUTLASS 非强制依赖。
  - 记录 unsupported final IR fail-fast 边界。
- 任务记录：
  - 写清执行前阅读、最小功能闭环、Diff 反推自测、SM89 CUDA 环境状态、CUTLASS/cuBLAS probe 结论、减法检查、自检和结论。
  - 若执行现场无 `nvcc` 或无 SM89 CUDA device（包括只有非 SM89 CUDA device），只能记录 local source/pipeline tests 结果和环境阻塞；不得把 runtime skip 写成计划完成。

## 验收设计

### Diff 反推测试

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_emit.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/execute_engine/test_cuda_sm86_strategy.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/pipeline/test_cuda_sm86_lowering.py`
- 新增或扩展：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_api_aligned_codegen.py`
- 新增或扩展：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_memory_hierarchy.py`
- 新增或扩展：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_launch_mapping.py`
- 新增或扩展：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/emit/test_cuda_sm86_fail_fast.py`
- `nvcc + SM89 CUDA device` 可用时运行：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/cuda/test_cuda_sm86_kernel_demos_runtime.py`
- `nvcc` 或 SM89 CUDA device 不可用时：
  - local runtime preflight 可以按现有 skip 机制记录环境原因，但必须发生在调用 `kg_execute_entry` / `cuda_sm86::launch` 前。
  - source semantic tests、pipeline tests、strategy tests 仍必须通过。
  - 计划级 execute 不得因此宣称完成；必须由管理员调度到有 `nvcc` 和 SM89 CUDA device 的环境补跑 runtime 精度验收，或回用户确认降低完成态。

### Runtime 精度验收硬门槛

- 计划级 execute / review / 入档验收要通过，必须至少在一个有 `nvcc` 和 SM89 CUDA device 的正式验收现场完成 CUDA runtime 精度验证。
- 必跑覆盖：
  - matmul static shape / dynamic shape。
  - matmul present bias / absent bias。
  - conv2d static shape / dynamic shape。
  - ring final IR 覆盖 K reduce accumulator lifecycle；若当前 runtime demo 未覆盖，必须补最小 runtime case 或记录为阻断。
- 允许 skip 的场景只限本地开发现场缺 `nvcc` 或 SM89 CUDA device（包括只有非 SM89 device）；skip 记录不能替代最终通过证据。
- 若 CI 或本机都无法提供 SM89 CUDA device，管理员必须调度 SM89 CUDA GPU 环境；若仍不可用，任务结论只能是阻塞或待用户确认，不得通过。

### Launch / thread mapping 验收

- 第一阶段 CUDA launch 采用 1-D static extent mapping：
  - `arch.launch` 的 `block` extent 生成 `gridDim.x` / `blockIdx.x` 语义。
  - `arch.launch` 的 `thread` extent 生成 `blockDim.x` / `threadIdx.x` 语义。
  - `arch.launch` 的 `shared_memory_size` 生成 launch 第三个参数 `shared_bytes`。
  - `subthread` extent 必须为静态 `1` 或在 lowering 中被静态折叠为 `1`；其它值 fail-fast，直到另一个计划定义 warp/lane/subthread CUDA 语义。
- `arch.get_block_id` 通过 `cuda_sm86::block_id()` 映射为 `blockIdx.x`；`arch.get_block_num` 不新增 public wrapper，emitc 直接映射为 `gridDim.x`。
- `arch.get_thread_id` 通过 `cuda_sm86::thread_id()` 映射为 `threadIdx.x`；`arch.get_thread_num` 通过 `cuda_sm86::thread_num()` 映射为 `blockDim.x`。
- `arch.get_subthread_id` 在 `subthread == 1` 时不新增 public wrapper，emitc 直接映射为常量 `0`；`arch.get_subthread_num` 不新增 public wrapper，emitc 直接映射为常量 `1`。
- dynamic `block` / `thread` extent 不属于本计划第一阶段成功子集；必须 fail-fast，不能按 demo 名称硬编码，也不能静默改成固定 extent。
- 必须有 source semantic tests 锁定：
  - static launch 生成 `cuda_sm86::launch<block, thread, subthread, shared_memory_size, generated_kernel>(host_ctx, args...)`，并在 launch wrapper 内生成 / 承接 `<<<grid, block, shared_bytes>>>`。
  - generated `__global__` 中存在 device `cuda_sm86::KernelContext` 构造或等价 generated glue，device body 的 wrapper calls 使用该 device context；source test 不允许 host launch context 被传入 device business body。
  - dynamic launch、unsupported subthread、unsupported axis、非整数 extent、无法证明的 launch operand fail-fast。

### Unsupported fail-fast 验收

- 必须新增或扩展 fail-fast pytest，至少覆盖：
  - unknown final IR op。
  - unsupported dtype。
  - unsupported rank 或 layout。
  - unsupported source/target space pair。
  - unsupported dynamic or large `tlm1` ring，以及任何 `tlm2/tlm3` ring。
  - unsupported `TLM1` ordinary pointer-view / reshape / reinterpret / `data()` / `at()` path，以及任何 `TLM2/TLM3` fragment path。
  - unsupported `dma.reinterpret/view/reshape` alias 或 type mismatch。
  - unsupported `arch.launch` subthread / extent / callee 形态。
- fail-fast 测试只断言公开可观察入口行为，不 direct import 跨文件 private helper。
- 若执行新增稳定错误文本，必须先回用户确认；否则错误断言只锁定现有错误类型或非稳定前缀。

### 文本门禁

- `rg -n "kg_cuda_sm86_execute_matmul_ir|kg_cuda_sm86_execute_img2col2d_ir|kg_cuda_sm86_execute_reduce_exp_ir" kernel_gen/dsl/gen_kernel/emit/cuda_sm86`
  - 预期：实现中不得存在这些固定主业务入口定义或调用；若保留历史注释也不得被 `kg_execute_entry`、hash-specific generated entry 或测试正向路径引用。
- `rg -n "kg_cuda_sm86_execute_matmul_ir|kg_cuda_sm86_execute_img2col2d_ir|kg_cuda_sm86_execute_reduce_exp_ir" test spec`
  - 预期：只允许负向断言、历史说明或迁移说明；不得作为正向完成态。
- `rg -n "return emitted_token|final IR marker|source fragment|operation_source_fragments|KERNEL_.*_FRAGMENT" kernel_gen/dsl/gen_kernel/emit/cuda_sm86 test spec`
  - 预期：单 op emit 不得只返回 marker token；SourceBundle 不得按 family 固定业务 fragment 作为主计算真源。实现侧 `operation_source_fragments(...)`、`select_entry_symbol(...)` 和 `CUDA_SM86_KERNEL_*_FRAGMENT` 必须删除、停用或只保留不可达历史注释；测试必须证明 `kg_execute_entry -> hash-specific generated entry -> generated __global__ body` 不调用固定 primitive。
- `rg -n "cuda_sm86::(launch|view|load|store|slice|deslice|fill|broadcast|transpose|matmul|img2col2d|add|sub|mul|truediv|max|reduce_sum|reduce_max|exp|make_ring)|\\.current\\(|\\.advance\\(|\\.reshape\\(" kernel_gen/dsl/gen_kernel/emit/cuda_sm86 test`
  - 预期：emitc 正向路径能观察到 Draft 7 A1 已确认 target include wrapper 调用、按 `npu_demo` 当前程度确认的 `cuda_sm86::launch` / 一维 `cuda_sm86::view(...)`、`DmaRing` member call 或 `Memory::reshape(...)` member call；`copy/free/reinterpret/block_num/subthread_*` 不得作为 public wrapper 正向门禁。
- `rg -n "cudaMemcpy\\(|cudaMemcpyAsync\\(" kernel_gen/dsl/gen_kernel/emit/cuda_sm86 include/cuda_sm86 test`
  - 预期：host boundary helper 可存在；TSM/TLM device lowering 不得用 runtime copy 表达。
- `rg -n "hasattr\\(|getattr\\(|callable\\(getattr" kernel_gen/dsl/gen_kernel/emit/cuda_sm86 include/cuda_sm86 test/dsl/gen_kernel/emit`
  - 预期：不得出现上下文能力探测绕过 spec；历史或非相关命中必须人工说明。
- `rg -n "cudaGetDeviceProperties|cudaDeviceGetAttribute|compute capability|major.*minor|infer.*sm|sm.*infer|推论.*sm|推断.*sm" kernel_gen/dsl/gen_kernel/emit/cuda_sm86 include/cuda_sm86`
  - 预期：generated source、`kg_execute_entry`、`cuda_sm86::launch` 和 include wrapper 正向路径不得新增 runtime target selection、runtime device capability probe、silent fallback、fixed primitive fallback 或通过 compute capability 改写 target 的代码。
- `rg -n "cudaGetDeviceProperties|cudaDeviceGetAttribute|compute capability|major.*minor|infer.*sm|sm.*infer|推论.*sm|推断.*sm" test spec`
  - 预期：测试 / spec 中允许出现环境诊断和负向说明，但必须人工分类：诊断只能发生在调用 `kg_execute_entry` / `cuda_sm86::launch` / CUDA kernel runtime 前，只能决定 skip / fail-fast，不能改变 target、不能 fallback。
- source semantic test 必须证明非 SM89 / 无 SM89 验收现场不会进入 `kg_execute_entry`、`cuda_sm86::launch` 或任何 generated CUDA runtime 正向调用。
- `rg -n "def _|class .*:|object" kernel_gen/dsl/gen_kernel/emit/cuda_sm86 test/dsl/gen_kernel/emit`
  - 预期：新增或改动 private callable 满足审查规范；测试不得直连跨文件 private helper；`object` 命中需人工说明。

### 格式和状态门禁

- `git diff --check`
- `git status --short`
- 敏感目录核对：`git diff --name-status -- . ':!expectation/**'` 和 `git diff --name-status -- expectation`
- 公开 API 核对：diff 中若出现公开签名、script 参数、include API 或稳定错误文本变更，必须能定位到用户确认来源；否则阻断。

### 合同验收

- 当前必过 `expectation`：无。
- `expectation/` 只读，不修改，不新增，不删除。
- 若后续架构师把某个 CUDA expectation 列为必过，必须修订本计划并重新 strict review。

## 计划内小任务

### S0 - 同步依赖和最终 IR 基线

- 为什么做：CUDA execute 必须基于已合并的 pipeline spec options 和 multi-buffer loop staging ring 结果，避免并行覆盖或按旧 IR 形态实现。
- 做什么：同步 `T-20260607-2b00a1ea` 和 `T-20260607-0c4db1f1` 合并后的主线，盘点 matmul/conv2d 静态与动态 final IR dump，记录 CUDA lowering 当前缺口，并记录 `target="cuda_sm86"` 来自显式调用方 / pipeline / ExecutionEngine 配置，不允许 CUDA codegen 推断 target / sm。
- 不做什么：不修改 ring 计划，不修改 expectation，不提前改 CUDA 实现。
- 怎么验收：任务记录写清 merge-base、依赖提交、dump 路径、当前 IR op 清单、CUDA execute 可开工判断；运行 `git status --short` 和 `git diff --name-status --cached` 确认无意外暂存。
- 卡住问谁：依赖未合并或同步冲突问管理员；IR 语义与 ring 计划冲突问架构师；需要改公开 API 问用户。

详细字段：
- 上下文：本计划必须消费稳定 final IR 语义，尤其 ring lifecycle、target ring num 和 accumulator advance 规则。
- 目标：给 execute 建立可追溯基线，确保后续 spec/实现/test 对准最新 IR。
- 非目标：不做实现，不重跑无关任务，不改 TODO。
- 模块范围：任务 worktree 内的只读核对、任务记录、必要的 dump 只读分析。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、本计划文件、已通过守护的 ring 计划文件。
- 合同真源：用户确认 > 已合并 ring 计划与实现 > cuda_sm86 spec > final IR dump > 当前实现。
- 最小功能闭环：能列出 matmul/conv2d 静态和动态 final IR 中需要 CUDA lowering 的 op、space、symbol 和 ring 形态，并记录 target 来源是显式 `cuda_sm86` 配置而非 CUDA codegen 推断。
- 执行步骤：
  1. 核对当前任务 worktree 基线、分支、merge-base 和依赖提交。
  2. 只读打开 matmul/conv2d 相关 static/dynamic dump。
  3. 列出 `arch`、`dma`、`kernel`、`symbol` op 清单和 space-pair 清单。
  4. 标出 accumulator / output tile lifecycle 和 ring `num` 决策点。
  5. 记录 `target="cuda_sm86"` 的来源：来自调用方 / pipeline / ExecutionEngine 配置；不得通过 runtime device query、compute capability 或 IR 形态重新判断 sm。
  6. 在任务记录写清可开工结论和仍未覆盖的 IR 形态。
- 合同验收：无必过 `expectation`。

### S1 - 更新 CUDA SM86 spec、include 函数封装和完成态边界

- 为什么做：先把目标从 fixed primitive selector 改成 API/IR 对齐 kernel codegen，避免 execute 在旧 spec 下返工。
- 做什么：更新 `cuda_sm86` emit/include/pipeline/target spec，写清 npu_demo-like include 函数封装层、公开 / `detail` 边界、Draft 7 A1 exact signature 清单、memory hierarchy、generated kernel 形态、ring lowering、CUTLASS/cuBLAS 取舍、unsupported 边界和“显式 target 唯一来源 / 非 SM89 在调用 `kg_execute_entry` / `cuda_sm86::launch` 前停止”的边界。
- 不做什么：不改 Python 包外公开 API，不改跨 target `include/api/**`，不改 expectation，不新增 pipeline option；不得实现 A1 清单之外未获用户确认的 include 公开签名。
- 怎么验收：spec diff 中能看到 `include/cuda_sm86` wrapper API 候选清单、global/tsm/tlm mapping、space-pair lowering、ring policy、matmul/conv2d 完成态、外部库非强制依赖；运行 `git diff --check`。
- 卡住问谁：include 函数签名、公开 / detail 边界或外部依赖是否转必需问用户；验收资产问架构师；流程状态问管理员。

详细字段：
- 上下文：当前 spec 部分描述还允许 fixed primitive selector 作为有效完成态，并且 `spec/include/cuda_sm86/cuda_sm86.md` 明确禁止 aggregate include 承载系统化 helper；这与用户 2026-06-09 确认的 include 函数封装 + emitc 路线冲突。
- 目标：让 execute、review 和入档验收有统一合同。
- 非目标：不把 CUDA memory-pool、CUTLASS 必需依赖或 cuBLAS 主路径写入第一阶段完成态。
- 模块范围：`spec/dsl/gen_kernel/emit/cuda_sm86.md`、`spec/include/cuda_sm86/cuda_sm86.md`、`spec/pass/pipeline/cuda_sm86_lowering.md`、`spec/target/registry.md`。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、本计划文件。
- 合同真源：用户确认 > 本计划 > spec > pytest > 当前实现。
- 最小功能闭环：spec 明确 `include/cuda_sm86` wrapper 层和 Draft 7 A1 exact signature 清单、`tsm != cudaMemcpy`、`tlm != device pointer`、TLM fragment 只支持 `TLM1` 且不走普通 pointer-view API、ring lifecycle、cuBLAS 非主完成态、CUTLASS 非强制依赖，以及 `cuda_sm86` 是显式 target 而非 codegen/runtime 推断结果；非 SM89 现场在进入 `kg_execute_entry` / `cuda_sm86::launch` 前停止。
- 执行步骤：
  1. 删除或降级 fixed primitive selector 完成态描述。
  2. 写入 `include/cuda_sm86` wrapper 分类、公开 / `detail` 边界、Draft 7 A1 exact signature 清单和用户确认来源字段。
  3. 写入 emitc per-op lowering 到 wrapper 调用的目标结构，明确 `kernel/*.py` 不再只返回 marker。
  4. 写入 memory hierarchy 表和 space-pair lowering 表。
  5. 写入 ring lowering policy、`num = 1` 非流水 ring 和 accumulator advance 规则。
  6. 写入 matmul/conv2d 第一阶段覆盖范围。
  7. 写入 unsupported fail-fast 和 public API 边界。
  8. 写入 no cuda-sm inference 边界：不根据 `cudaGetDeviceProperties`、compute capability、IR 形态或 slot 信息选择 / 改写 target；非 SM89 现场必须在 `kg_execute_entry` / `cuda_sm86::launch` / CUDA kernel runtime 前 skip 或 fail-fast。
  9. 写入 CUTLASS/cuBLAS 第一阶段只读/probe 口径。
- 合同验收：无必过 `expectation`。

### S2 - 建立 cuda_sm86 emitc per-op wrapper lowering

- 为什么做：当前 `cuda_sm86/kernel/*.py` 单 op emit 主要返回 marker，主业务 source 仍由 SourceBundle family fragment 注入，偏离 `npu_demo` emitc 分层。
- 做什么：把 `cuda_sm86` per-op emit 改成真实发射 `include/cuda_sm86` wrapper 调用；ModuleOp / SourceBundle assembly 只负责 artifact、entry、hash marker 和 wrapper 拼装。
- 不做什么：不新增包外 Python handler，不让测试 direct call private helper，不在 `source_bundle.py` 继续新增或保留可达 family 固定业务 fragment。
- 怎么验收：source semantic tests 证明同 op 不同 dataflow 会改变可执行 wrapper call、operand binding 和 generated body；单 op emit 不再只返回 marker token。
- 卡住问谁：include wrapper exact signature 或公开 / detail 边界问用户；实现边界问架构师。

详细字段：
- 上下文：`npu_demo` backend 已通过 emit registry 将 IR op 映射为 include 函数调用；`cuda_sm86` 需要对齐该分层，避免继续靠大字符串 family fragment 维护主计算。
- 目标：形成 host entry、device kernel、SSA context、symbol expression、per-op wrapper call emission 和 SourceBundle assembly 的最小框架。
- 非目标：不追求所有 DSL op 全覆盖，不在第一轮引入 CUTLASS。
- 模块范围：`kernel_gen/dsl/gen_kernel/emit/cuda_sm86/**` 和对应 pytest。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、本计划文件。
- 合同真源：spec > pytest > current generated SourceBundle behavior。
- 最小功能闭环：一个含 `arch.launch + dma.copy + kernel.matmul` 的 final IR 能生成 hash-specific `__global__` kernel，且 body 通过 `cuda_sm86` wrapper calls 表达 operand-specific load/compute/store。
- 执行步骤：
  1. 新增或重组 package-local context，用于 SSA value 到 CUDA identifier / descriptor binding。
  2. 实现 host func traversal、device func traversal、region traversal。
  3. 让 `arch.launch` 在 host entry / generated glue 中生成 `cuda_sm86::launch<...>` public launch wrapper 调用，callee 解析到 generated `__global__` kernel；dynamic launch extent fail-fast。
  4. 生成 `__global__` trampoline：在 device 侧构造 `cuda_sm86::KernelContext` 或等价 detail glue，再调用 generated `__device__` business body；device body wrapper calls 使用 device context，不能把 host launch context 传入 device body。
  5. 让 `dma.*`、`kernel.*`、`symbol.*` emit 生成 A1 已确认 wrapper calls、`cuda_sm86::view(...)`、Memory 成员调用、direct CUDA expression、package-local glue 或明确 unsupported。
  6. 让 op emission 失败边界统一纳入现有错误体系。
  7. 保留 marker/hash，但测试可执行 body 和 wrapper call，而不是只测 marker。
  8. 删除、停用或断开 `operation_source_fragments(...)`、`select_entry_symbol(...)`、`CUDA_SM86_KERNEL_*_FRAGMENT` 和固定 `kg_cuda_sm86_execute_*_ir` 的主计算可达路径。
  9. 确认 SourceBundle builder 不新增 target/sm 推断分支；target 已由 `target="cuda_sm86"` registry handler 选择。
- 合同验收：无必过 `expectation`。

### S3 - 实现 include/cuda_sm86 memory、DMA 和 space-pair wrapper

- 为什么做：API 对齐的核心是正确解释 global/shared/register fragment，而不是用 host runtime copy 伪装。
- 做什么：在 `include/cuda_sm86` wrapper 层实现 global/tsm/tlm1 descriptor、shared arena、fragment/register object、slice/deslice/load/store/fill/broadcast/transpose space-pair lowering；按 `npu_demo` 当前程度支持 global/tsm 等 pointer-view space 的一维 `cuda_sm86::view(...)` 和 `Memory::view/reshape` 成员，`copy/free/reinterpret` 不新增同名 public wrapper；`TLM1` fragment 不走普通 pointer-view API，`TLM2/TLM3` 不支持。
- 不做什么：不引入 memory-pool pipeline，不把 TLM 变成 byte pool，不让 generated source 局部大字符串重复实现同类 helper。
- 怎么验收：新增 memory hierarchy pytest 扫描/构造每类 space-pair，确认 emitc 生成已确认 wrapper calls、Memory 成员调用或用户确认的新增 wrapper；TSM/TLM 不用 `cudaMemcpy`，view 类 op 不复制。
- 卡住问谁：target space 语义或 wrapper 签名冲突问用户或架构师。

详细字段：
- 上下文：用户明确要求 GM/SM/fragment 之间按 CUDA device memory hierarchy 解释。
- 目标：建立可被 matmul/conv2d lowering 复用的 descriptor 和 copy model。
- 非目标：不把 device runtime allocation 放进普通 kernel body。
- 模块范围：`include/cuda_sm86/**`、`kernel_gen/dsl/gen_kernel/emit/cuda_sm86/**`、对应 pytest。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、跨 target `include/api/**`、A1 清单之外未获用户确认的 include signatures、本计划文件。
- 合同真源：target registry space semantics > cuda_sm86 spec > pytest > current helper。
- 最小功能闭环：`global -> tsm -> tlm1 -> global` tile round trip 能在 generated device code 中表达，且 TLM1 fragment transfer 不出现 `cudaMemcpy`、ordinary pointer offset、`data()` 或 `at()`。
- 执行步骤：
  1. 定义 `include/cuda_sm86` descriptor / memory wrapper signatures，并按用户确认清单实现。
  2. 定义 shared memory arena layout 和 alignment wrapper。
  3. 定义 TLM fragment/register tile representation wrapper。
  4. 实现 global/tsm pointer-view alias：一维 generated-source path 可使用 `cuda_sm86::view(...)`，多维 path 使用 `Memory::view<T>(...)` / `Memory::reshape(...)`，`reinterpret` 使用 package-local descriptor/type glue 或 fail-fast。
  5. 实现 TLM1 fragment alias 子集：仅允许由 detail fragment descriptor glue 表达可证明安全的形态；generated source 不发射 `Memory<TLM1, T>::data()`、`at()`、`Memory::view(...)`、`Memory::reshape(...)` 或 `cuda_sm86::view(...)`。
  6. 实现 materializing op 的 source/target space dispatch wrapper。
  7. 在 emitc 中把 final IR op 映射到已确认 wrapper calls、Memory 成员调用、direct CUDA expression、package-local glue 或 fail-fast。
  8. 增加 source text tests 和小 IR generated body tests，覆盖 TLM1 ordinary view/reshape/reinterpret fail-fast、TLM2/TLM3 fail-fast、dynamic/large TLM ring fail-fast，以及 fragment transfer 不出现 `cudaMemcpy` 或 ordinary pointer offset。
- 合同验收：无必过 `expectation`。

### S4 - 实现 ring / accumulator lifecycle lowering

- 为什么做：multi-buffer ring 变换后 CUDA backend 必须区分 global/tsm/tlm ring，并且不能在 K 累加维度错误 advance accumulator。
- 做什么：为 CUDA codegen 接入 ring descriptor、cursor、segment stride、target `num` 和 alloc lifecycle 分析。
- 不做什么：不重新实现 multi-buffer pass，不改变 ring plan 的 IR 变换规则。
- 怎么验收：source tests 覆盖 `num == 1`、static tsm ring、static tlm slot unroll、dynamic tlm fail-fast、K reduce accumulator 不提前 advance。
- 卡住问谁：ring lifecycle 与 final IR 形态冲突问架构师；target `num` 规则需要改变问用户。

详细字段：
- 上下文：用户明确要求若 alloc 是 K 累加维度，应在 loop 外或 output tile 完成后 advance；若没有外层 output tile loop，`num == 1`。
- 目标：确保 CUDA generated kernel 对 multi-buffer final IR 的生命周期解释正确。
- 非目标：不做 reinterpret chain composition，不修改 memory-pool 后 CSE。
- 模块范围：`kernel_gen/dsl/gen_kernel/emit/cuda_sm86/**`、ring 相关 pytest。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、multi-buffer ring 计划正文、跨 target `include/api/**`、A1 清单之外未获用户确认的 include signatures、本计划文件。
- 合同真源：用户确认 > multi-buffer loop staging ring 合并结果 > cuda_sm86 spec > pytest。
- 最小功能闭环：一个含 K loop accumulator 的 matmul IR 生成的 CUDA body 中，acc init、accumulate、store 和 ring advance 顺序可被 source test 锁定。
- 执行步骤：
  1. 读取 final IR 中 alloc、loop、advance、consume 的生命周期信息。
  2. 对 global/tsm/tlm ring 分别建立 cursor lowering。
  3. 对 `tlm1 num == 1` 和 small static `num` 建立 fragment slot 策略。
  4. 对 dynamic 或 large TLM ring 生成稳定 fail-fast。
  5. 增加 accumulator advance source tests。
- 合同验收：无必过 `expectation`。

### S5 - 实现 matmul kernel lowering

- 为什么做：matmul 是 CUDA SM86 Tensor Core/TLM fragment 对齐的关键路径。
- 做什么：通过 `include/cuda_sm86` matmul / fragment / DMA wrapper 和 emitc op lowering，从 final IR 生成 matmul tile load、fragment compute、accumulate、bias/elementwise、store。
- 不做什么：不按 demo 名称选择 fixed matmul source，不为了性能牺牲 correctness。
- 怎么验收：static/dynamic、bias present/absent、acc true/false 或 dynamic acc case 的 source tests 和 CUDA runtime tests 通过。
- 卡住问谁：TF32 tolerance 或 acc 语义争议问用户。

详细字段：
- 上下文：当前 fixed matmul primitive 已有 Tensor Core marker，但不能表达 final IR dataflow。
- 目标：让 matmul static/dynamic/bias 变体从 final IR 生成真实 CUDA kernel body。
- 非目标：不在第一阶段追求全形状高性能 autotune。
- 模块范围：`kernel_gen/dsl/gen_kernel/emit/cuda_sm86/**`、`include/cuda_sm86/Arch.h`、matmul pytest/runtime gate。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、跨 target `include/api/**`、A1 清单之外未获用户确认的 include signatures、pipeline option、本计划文件。
- 合同真源：kernel matmul spec > cuda_sm86 spec > pytest > runtime reference。
- 最小功能闭环：一个 dynamic matmul IR 通过 generated kernel 计算出与 CPU reference 合格的结果。
- 执行步骤：
  1. 解析 `kernel.matmul(out, lhs, rhs, acc?)` operand 和 attrs。
  2. 对 A/B/out tile 发射 global/shared/fragment load wrapper calls。
  3. 通过 include wrapper 生成参与最终输出的 `mma.sync` / `wmma` 路径。
  4. 正确处理 accumulator 生命周期；K reduce loop 内不错误 advance 输出 ring，也不在每个 K tile 后清空 acc。
  5. 生成 final store/deslice。
  6. 增加 accuracy tests 和 source body tests。
- 合同验收：无必过 `expectation`。

### S6 - 实现 conv2d / img2col2d kernel lowering

- 为什么做：用户要求 matmul 和 conv2d 都能变成预期 kernel code。
- 做什么：通过 `include/cuda_sm86` 的 `img2col2d`、matmul、DMA 和 kernel wrapper，或 package-local direct conv generated glue，让 conv2d dynamic/static IR 生成 direct conv 或 implicit GEMM CUDA device kernel；`kernel.img2col2d` 解释为 tile gather 或显式支持的 materialization。
- 不做什么：不新增 `cuda_sm86::conv2d` public wrapper，不默认生成全局 full img2col buffer，不退回 fixed conv primitive。
- 怎么验收：conv2d static/dynamic source tests 和 CUDA runtime accuracy tests 通过；source body 包含真实 gather/compute/store。
- 卡住问谁：conv layout、padding/dilation/stride 支持边界问用户或架构师。

详细字段：
- 上下文：当前 conv/img2col fixed primitive 不随 final IR staging 和 descriptor 变化。
- 目标：把 conv2d 也纳入 API/IR 对齐 CUDA codegen，不只修 matmul。
- 非目标：不接入 cuDNN，不把 img2col 默认物化到 global。
- 模块范围：`kernel_gen/dsl/gen_kernel/emit/cuda_sm86/**`、conv2d pytest/runtime gate。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、跨 target `include/api/**`、A1 清单之外未获用户确认的 include signatures、本计划文件。
- 合同真源：conv/img2col spec > cuda_sm86 spec > pytest > runtime reference。
- 最小功能闭环：一个 dynamic conv2d IR 通过 generated kernel 计算出与 CPU reference 合格的结果。
- 执行步骤：
  1. 解析 conv/img2col final IR operand、window、stride、dilation、padding、layout。
  2. 选择 direct conv 或 implicit GEMM tile wrapper path。
  3. 通过 wrapper 实现 input window gather 到 shared/register tile。
  4. 通过 wrapper 实现 weight tile load 和 inner compute。
  5. 通过 wrapper 实现 bias/activation 和 output store。
  6. 增加 source body tests、shape dynamic tests、runtime accuracy tests。
- 合同验收：无必过 `expectation`。

### S7 - CUTLASS/cuBLAS 可行性评估和非阻塞 probe

- 为什么做：外部高性能库可以提升后续性能，但不能替代第一阶段 IR 语义对齐。
- 做什么：只读核对本机/CI 是否存在 CUTLASS/cuBLAS 编译条件，写任务记录；可新增非必过或环境 gated compile-probe 测试。
- 不做什么：不把 CUTLASS/cuBLAS 变成必需依赖，不让主完成态依赖库调用。
- 怎么验收：任务记录写清 headers/libs/nvcc 探测、是否可作为后续计划输入；默认测试在缺依赖时 skip 而非失败。
- 卡住问谁：若要强制依赖 CUTLASS，或把 cuBLAS/cuBLASLt 作为同一 `cuda_sm86` target 内的 whole-GEMM 替代路径 / 性能精度对照以外的任何完成态，必须问用户；不得作为非 SM89 runtime fallback。

详细字段：
- 上下文：用户要求评估 CUTLASS/cuBLAS，但当前主目标是生成本仓库 IR 驱动的 CUDA kernel。
- 目标：给后续性能计划留下证据，不阻塞第一阶段 correctness。
- 非目标：不 vendor 第三方库，不改构建公开参数。
- 模块范围：任务记录、可选 pytest probe、spec 外部参考说明。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、第三方 vendored 目录、跨 target `include/api/**`、A1 清单之外未获用户确认的 include signatures、本计划文件。
- 合同真源：用户确认 > 本计划 > NVIDIA 官方文档 > 本地编译环境。
- 最小功能闭环：不影响无 CUTLASS/cuBLAS 环境的主测试；记录明确下一阶段建议。
- 执行步骤：
  1. 检查 `nvcc`、CUDA include/lib、cuBLAS/cuBLASLt link 条件。
  2. 检查 CUTLASS header/library 是否已存在于仓库或系统 include path。
  3. 若条件存在，做最小 compile-probe，不接入主生成路径。
  4. 记录可用性、风险、推荐后续计划。
- 合同验收：无必过 `expectation`。

### S8 - 测试、验收和减法检查

- 为什么做：这个计划很容易退化成“source 看起来像 CUDA”但实际仍是 fixed runner。
- 做什么：补齐 include wrapper / emitc source semantic tests、memory hierarchy tests、runtime accuracy tests、文本门禁、任务记录。
- 不做什么：不以 expectation 替代 diff 反推测试。
- 怎么验收：验收设计中的 pytest、runtime preflight、text scan、`git diff --check` 均有记录；无 `nvcc` 或无 SM89 CUDA device 时写清 skip 原因。
- 卡住问谁：`nvcc` 或 SM89 CUDA device 不可用时问管理员是否调度 SM89 CUDA GPU 环境；验收资产争议问架构师。

详细字段：
- 上下文：必须证明 final IR 变化会改变 generated body，并且 runtime 结果合格。
- 目标：形成 execute 可交付的验证闭环。
- 非目标：不扩大 expectation scope。
- 模块范围：本计划所有触达文件、任务记录。
- 禁止修改面：`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`、本计划文件。
- 合同真源：本计划 > spec > pytest > runtime reference。
- 最小功能闭环：matmul/conv2d dynamic/static source 里的 wrapper calls、operand binding、generated device body 和 runtime correctness 都被测试覆盖。
- 执行步骤：
  1. 按 diff 反推补 pytest。
  2. 跑所有计划验收命令。
  3. 跑 CUDA runtime preflight 和 SM89 runtime 精度验收，或在进入 `kg_execute_entry` / `cuda_sm86::launch` 前记录 skip。
  4. 跑 fixed primitive selector、marker-only emit 和 source fragment 文本门禁。
  5. 跑 no cuda-sm inference 文本门禁，并核对非 SM89 设备不运行 CUDA runtime、不进入 fallback。
  6. 跑敏感目录和公开 API 边界扫描，确认新增 include signatures 均有用户确认来源。
  7. 在任务记录写清自检、减法检查和结论。
- 合同验收：无必过 `expectation`。

## 待确认项

- 当前阻断性待确认项：无。Draft 10 已完成 clean worktree strict review 收敛和 `守护最好的爱莉希雅` 本人守护最终检验；当前仍不可分发的原因是下发依赖尚未完成、合并并同步，若绕过依赖必须先取得用户明确确认并重新 strict review / 守护最终检验。
- 已收口决策：
  - 决策 1：`cuda_sm86` target / sm 来源边界选择 A。`cuda_sm86` 只来自调用方 / pipeline / `ExecutionEngine(target="cuda_sm86")` / registry handler 的显式选择；codegen 只读取已选 target 的 registry 能力，不做 runtime sm 推断，不切换 target。
  - 决策 2：2026-06-13 用户明确将本任务验收目标改为 SM89。运行环境不满足 SM89 CUDA 需求时选择 A。非 SM89 设备不运行 CUDA runtime；本地可以 skip 并记录，最终完成态必须由满足 SM89 的环境补跑 runtime 精度验收；不得用 fixed primitive、cuBLAS/cuBLASLt、其它 CUDA sm 或其它 backend fallback 替代。
  - 决策 3：2026-06-09 用户确认 `cuda_sm86` 后端应改为类似 `npu_demo` 的 include 函数封装层，再由 emitc 发射调用；不继续沿 SourceBundle family fragment / 手写模板补丁路线推进。
  - 决策 4：2026-06-09 用户确认 matmul 第一阶段不允许 SIMT-only 作为通过路径；保持当前 `cuda_sm86` spec，必须有真实 `mma.sync` / `nvcuda::wmma` 参与最终 matmul 输出。
  - 决策 5：2026-06-09 用户确认 `include/cuda_sm86` exact public signatures 采用 Draft 7 推荐候选 A1。
  - 决策 6：2026-06-09 用户对 unsupported 错误文本回复“随意”；按架构推荐项收口为不新增稳定 unsupported 文本。
  - 决策 7：2026-06-09 用户确认 `cuda_sm86::copy/free/view/reshape/reinterpret/launch/block_num/subthread_*` 按照 `npu_demo` 当前程度支持；据此本计划新增 public `cuda_sm86::launch<...>` 和一维 `cuda_sm86::view(...)`，`reshape` 走 `Memory::reshape(...)` 成员，`copy/free/reinterpret/block_num/subthread_*` 不新增同名 public wrapper。
  - 决策 8：2026-06-09 用户确认 CUDA TLM fragment 只需要 `TLM1` 表示，`TLM2/TLM3` 不支持。
  - 决策 9：`sm_89` 仅改变本计划 runtime 验收现场与完成态门槛，不自动重命名公开 target 名、目录名或包外 API；若 execute 判断确需重命名 `cuda_sm86`，必须先列 exact API 影响面并回用户确认。
- 非阻断后续决策：
  - 是否把 CUTLASS 变成正式依赖：推荐暂不引入；第一阶段先完成内部 IR/API 对齐 kernel codegen。
  - 是否允许 cuBLAS/cuBLASLt 作为同一 `cuda_sm86` target 内的 whole-GEMM 替代路径：推荐不作为第一阶段主路径；可以后续作为性能 / 精度对照另立计划。它不得作为非 SM89 runtime fallback。
  - 是否为 device pointer runtime ABI 增加公开入口：本计划不做；当前 `ExecutionEngine` ABI 保持不变。
  - 是否新增 CUDA pipeline option：本计划不做；若 execute 发现必须新增，暂停回用户确认。

## 用户确认与协同约束

- Draft 6 / Draft 7 / Draft 8 / Draft 9 / Draft 10 已改变公开 include API 边界和 CUDA 技术子合同，Draft 5 的 strict review / 守护最终检验通过结论只保留为历史记录；本计划必须重新完成 Codex subagent strict review 收敛，并由 `守护最好的爱莉希雅` 本人重新执行守护最终检验。
- 当前已有唯一计划级 execute 任务 `T-20260608-bfe97ae7`，位于 `TODO.md` 正在执行列表且状态为 `暂停`；本计划修订不得新建第二个 execute。守护最终检验通过后，仍需等待下发依赖完成、合并并同步，管理员才可按正文决定恢复现有暂停任务、重定任务目标或重新分发；依赖未满足前不得恢复执行或创建第二个 execute。
- 正式计划前必须发起 Codex subagent strict review 持续收敛，并把每轮输入、问题、主线处理和状态写入 `迭代审阅记录`。
- subagent 收敛到无阻断、无最小需改、无待确认后，必须由 `守护最好的爱莉希雅` 做守护最终检验。
- 守护最终检验通过且下发依赖完成、合并并同步后，管理员才允许分发唯一计划级 `execute`。
- `守护最好的爱莉希雅` 本人守护最终检验阶段的正式 guard 证据必须在独立 guard worktree 完成，不得把该阶段的 guard 操作混入主仓 index；Round 2 strict review 前的计划 tracked/index 证据按榕 prompt 已在当前目录建立。
- 本计划不得纳入 `T-20260607-0c4db1f1 / multi_buffer_loop_staging_ring` execute；CUDA execute 默认等待该任务完成、合并并同步后再下发。
- 本计划不得混入 memory-pool 后 CSE / pass directory layout / DMA ring 历史任务 / CUDA 以外 target 后端任务。

## 迭代审阅记录

### Draft 1

- 形成原因：用户要求为 CUDA SM86 API 对齐、真实 kernel codegen、CUTLASS/cuBLAS 取舍出计划书。
- 标准包：未完整发起。
- subagent strict review：未开始。
- 守护最终检验：未开始。
- 状态：草稿，不可下发。

### Draft 2

- 形成原因：用户要求“按照计划书流程显出计划书”，同时已明确 multi-buffer ring 计划先推进，CUDA 不混入 ring execute。
- 标准包：
  - 根 `AGENTS.md`。
  - 当前角色 prompt 中的执行、计划、公开 API、expectation、subagent、守护最终检验要求。
  - `agents/standard/计划书标准.md`。
  - `agents/standard/审查规范.md`。
  - `agents/standard/任务记录约定.md`。
  - 本计划 Draft 2 全文。
  - 用户确认来源、禁止修改面、待确认项、必过验收命令。
- 严格通过口径：
  - 无公开 API 新增、删除、重命名、改签名或稳定错误文本变更。
  - `expectation/` 只读且当前无必过 expectation。
  - 计划级任务唯一，S0-S8 不创建独立 TODO。
  - 每张小任务卡包含 `为什么做 / 做什么 / 不做什么 / 怎么验收 / 卡住问谁`，且详细字段一致。
  - 明确依赖 `T-20260607-0c4db1f1` 完成、合并、同步后再下发，且不混入 ring execute。
  - CUDA memory hierarchy、ring lowering、matmul/conv2d、CUTLASS/cuBLAS 取舍和验收口径无可执行缺口。
- subagent strict review：
  - Reviewer A / 流程边界：结论不通过；无阻断；最小需改项为删除提前下发例外或转用户确认、S3-S7 禁止修改面需自包含。
  - Reviewer B / CUDA 技术：结论不通过；阻断项为 runtime 验收可被 skip 削弱核心目标；最小需改项为补 unsupported fail-fast 验收、补 `arch.launch` / `threadIdx` 轴映射与 grid/block derivation 验收。
- 主线处理：
  - Draft 3 删除提前下发例外，改为依赖未完成前不得下发；若未来要提前下发必须用户确认并重审。
  - Draft 3 统一 S3-S7 禁止修改面，补齐 `.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md` 等敏感范围。
  - Draft 3 增加 Runtime 精度验收硬门槛，明确无 `nvcc` 或无 SM86 CUDA device 时 skip 不能替代计划完成，必须调度 SM86 GPU 环境或回用户确认降低完成态。
  - Draft 3 增加 Launch / thread mapping 验收，固定第一阶段 1-D CUDA mapping 和 unsupported subthread fail-fast。
  - Draft 3 增加 Unsupported fail-fast 验收，覆盖 unknown op、dtype、rank/layout、space pair、TLM ring、alias/type mismatch、launch 形态。
- 收敛结论：R1 未收敛，已进入 Draft 3 返工修订。
- 状态：R1 返工已处理，Draft 3 待 R2 strict review，不可下发。

### Draft 3

- 形成原因：处理 Draft 2 两路 subagent strict review 的全部最小需改项和阻断项。
- 标准包：
  - 根 `AGENTS.md`。
  - 当前角色 prompt 中的执行、计划、公开 API、expectation、subagent、守护最终检验要求。
  - `agents/standard/计划书标准.md`。
  - `agents/standard/审查规范.md`。
  - `agents/standard/任务记录约定.md`。
  - 本计划 Draft 3 全文。
  - Draft 2 两路 reviewer 结论和 Draft 3 收口摘要。
  - 用户确认来源、禁止修改面、待确认项、必过验收命令。
- 严格通过口径：
  - Draft 2 所有问题均已正文闭合。
  - 无公开 API 新增、删除、重命名、改签名或稳定错误文本变更。
  - `expectation/` 只读且当前无必过 expectation。
  - 下发必须等待 `T-20260607-0c4db1f1` 和 `T-20260607-2b00a1ea` 依赖链完成、合并、同步；无提前下发例外。
  - 计划级任务唯一，S0-S8 不创建独立 TODO。
  - 每张小任务卡包含 `为什么做 / 做什么 / 不做什么 / 怎么验收 / 卡住问谁`，且详细字段一致。
  - CUDA memory hierarchy、ring lowering、launch mapping、unsupported fail-fast、matmul/conv2d、CUTLASS/cuBLAS 取舍和验收口径无可执行缺口。
  - runtime 精度验收硬门槛不能被本地 skip 替代。
- subagent strict review：
  - Reviewer A / 流程边界 R2：结论通过；阻断项无；最小需改项无；待确认项无。核对 R1 依赖口径和 S3-S7 禁止修改面问题已闭合，未发现新的公开 API、expectation、唯一 execute、验收或流程阻断。
  - Reviewer B / CUDA 技术 R2：结论通过；阻断项无；最小需改项无；待确认项无。核对 runtime 硬门槛、launch/thread mapping、unsupported fail-fast 已闭合，CUDA 技术方案自洽。
- 主线处理：R2 未提出正文需改项；本次只回写 R2 收敛记录，不改变公开 API、验收资产、任务范围、依赖口径或 `expectation` 授权。
- 收敛结论：已发起的两路 subagent strict review 均收敛到无阻断、无最小需改项、无待确认项；可进入守护最终检验。
- 状态：subagent strict review 收敛通过，待守护最终检验，不可直接下发。

### Draft 5

- 形成原因：2026-06-07 用户追问“不是再推论 cuda sm”，随后明确指出不确定项应由用户决策；2026-06-08 用户确认 A/A：显式 target 唯一来源，非 SM86 不运行 CUDA runtime。
- 标准包：
  - 根 `AGENTS.md`。
  - 当前角色 prompt 中的执行、计划、公开 API、expectation、subagent、守护最终检验要求。
  - `agents/standard/计划书标准.md`。
  - `agents/standard/审查规范.md`。
  - `agents/standard/任务记录约定.md`。
  - 本计划 Draft 5 全文和暂存 diff。
  - Draft 3 R2 历史通过结论、用户 A/A 决策、Hume 第一轮最小需改项、Draft 5 收口摘要。
  - 禁止修改面、待用户确认项、必过验收命令、no cuda-sm inference 文本门禁。
- 严格通过口径：
  - A/A 决策必须落入正文：`cuda_sm86` target/sm 只来自显式 target，不从 runtime、compute capability、IR 或 slot 推断 / 切换 target。
  - 非 SM86 CUDA device 不运行 CUDA runtime；最终完成态必须取得 `nvcc + SM86 CUDA device/GPU` 的 runtime 精度验收。
  - cuBLAS/cuBLASLt/CUTLASS 不得成为非 SM86 runtime fallback 或第一阶段主完成态。
  - 无公开 API 新增、删除、重命名、改签名或稳定错误文本变更；`expectation/` 只读且当前无必过 expectation。
  - 下发仍必须等待 `T-20260607-0c4db1f1 / multi_buffer_loop_staging_ring` 完成、合并并同步；依赖满足前不可下发。
- 主线处理：
  - 按 A/A 决策把 no cuda-sm inference 写成正式执行口径：target 只来自显式 `cuda_sm86` 配置，不从 IR、slot、runtime device property 或 compute capability 重新判断 sm。
  - 在计划目标、非目标、当前基线、S0、S1、S2、S8 和文本门禁中明确：非 SM86 设备不运行 CUDA runtime，不进入 fixed primitive、cuBLAS/cuBLASLt、其它 CUDA sm 或其它 backend fallback。
  - 增加文本门禁扫描 `cudaGetDeviceProperties`、`cudaDeviceGetAttribute`、`compute capability` 和 `infer sm` 类文本，命中必须人工分类并证明不会引入 runtime target selection 或 fallback。
  - 根据 Hume 第一轮 strict review，把完成态、Diff 反推测试、Runtime 精度验收硬门槛、S7/S8 环境措辞全部收窄为 `nvcc + SM86 CUDA device/GPU`；无 `nvcc` 或无 SM86 CUDA device（包括只有非 SM86 CUDA device）只能 skip/fail-fast/记录阻塞，不得通过。
  - 将 cuBLAS/cuBLASLt/CUTLASS 文字收口为同一 `cuda_sm86` target 内性能 / 精度对照或后续计划输入；不得作为非 SM86 runtime fallback，也不得替代第一阶段 IR-driven generated kernel body。
  - 将 matmul SIMT 说明改为同一 `cuda_sm86` target 内可验证 SIMT path，避免和 runtime fallback 混淆。
- 待确认项：无。
- subagent strict review：
  - Hegel / CUDA 技术第一轮：PASS，无阻断、无最小需改项、无待确认项；确认显式 target 唯一来源、SM86 runtime gate、SIMT/cuBLAS/CUTLASS 取舍、memory hierarchy/ring/matmul/conv2d/文本门禁自洽。
  - Hume / 流程边界第一轮：不通过；无阻断；最小需改项为 runtime 验收残留泛化 `CUDA GPU` / `CUDA device` / `CUDA 环境` 口径，且 S7 仍有“cuBLASLt fallback”旧说法。
  - Hume / 流程边界复审：PASS，无阻断、无最小需改项、无待确认项；确认 A/A target-sm 口径、runtime gate、cuBLAS/cuBLASLt/CUTLASS 非 fallback、下发门禁均已闭合。
  - Hegel / CUDA 技术复审：PASS，无阻断、无最小需改项、无待确认项；确认修订后未引入 runtime sm 推断、非 SM86 runtime 执行、fallback 完成态或 CUDA 技术自洽问题。
- 本轮本地证据：`git diff --check -- ARCHITECTURE/plan/cuda_sm86_api_aligned_kernel_codegen.md` 通过；`git diff --cached --check -- ARCHITECTURE/plan/cuda_sm86_api_aligned_kernel_codegen.md` 通过；计划文件已在 guard worktree 以 `git add -f` 暂存。
- 守护最终检验：`守护最好的爱莉希雅` / Curie 结论 PASS，无阻断、无最小需改项、无待确认项；守护证据显示暂存区只有本计划文件，禁止修改面无暂存变更，`git diff --cached --check -- ARCHITECTURE/plan/cuda_sm86_api_aligned_kernel_codegen.md` 通过。
- 收敛结论：Draft 5 已发起的 Hume / Hegel 两路 subagent strict review 均收敛到无阻断、无最小需改项、无待确认项；守护最终检验通过；无待用户确认项。
- 下发建议：Draft 5 当时状态为用户已确认可先建立任务，`T-20260608-bfe97ae7` 已作为待依赖任务进入 `任务列表`；守护通过后仍不能立即分发 CUDA execute，必须等待 `T-20260607-0c4db1f1 / multi_buffer_loop_staging_ring` 完成、合并并同步到执行现场后，管理员才可分发。若要绕过该依赖，必须先取得用户明确确认并重新 strict review / 守护最终检验。
- 状态：Draft 5 strict review 收敛通过，守护最终检验通过；当时待依赖任务已建立，等待下发依赖完成，当前 Draft 5 结论只作为历史记录。

### Draft 6

- 形成原因：2026-06-09 用户纠正架构根因裁定，明确 `cuda_sm86` 后端应采用类似 `npu_demo` 的 include 函数封装层，再由 emitc 发射 final IR op 调用；不是继续在 SourceBundle fixed family fragment / 手写模板中补 dataflow 绑定。
- 标准包：待发起新一轮 subagent strict review 时填写，至少包含根 `AGENTS.md`、当前角色 prompt、`agents/standard/计划书标准.md`、`agents/standard/审查规范.md`、`agents/standard/任务记录约定.md`、本计划 Draft 6 全文或 diff、Draft 5 历史通过结论、本轮用户确认来源、待确认 include signatures、禁止修改面和必过验收命令。
- 严格通过口径：
  - Draft 6 必须证明旧 Draft 5 的 SourceBundle family fragment 路线已降级为历史，不再作为主完成态。
  - 当时必须写清 `include/cuda_sm86` wrapper 层、公开 / `detail` 边界、exact signature 候选和用户确认缺口。
  - 必须保证不改变包外 Python API、工具参数、pipeline option、`kg_execute_entry` ABI、`cuda_sm86::ArgSlot` 字段和跨 target `include/api/**`。
  - 必须保留 A/A target-sm 决策：显式 target 唯一来源，非 SM86 不运行 CUDA runtime，不做 fallback。
  - 必须保留 `expectation/` 只读且当前无必过 expectation。
  - 当时必须写清 execute 不得在 include signatures 用户确认前实现或下发。
- 主线处理：
  - 将状态改为 Draft 6 修订中，旧 guard 通过不再作为当前可分发依据。
  - 将任务目标、计划目标、当前基线、方案选型、公开 API 设计、完成态、文本门禁、S1-S3/S5-S8 和待确认项改为 include wrapper + emitc 路线。
  - 将待确认项收口为 `include/cuda_sm86` exact public signatures 和 `cuda_sm86::detail` 边界。
- subagent strict review：
  - Avicenna / 流程 API 公开边界 Round 1：不通过；阻断项为 exact public signatures 缺失、Draft 6 strict review / 守护链路未收敛、Draft 6 tracked/index 证据未闭合。最小需改项为补 exact signature 候选表、写回 Round 1 审阅记录、重新记录 tracked/index 证据、用户确认签名后再发起下一轮 strict review。
  - Erdos / CUDA 技术 emitc 分层 Round 1：不通过；阻断项为 exact signatures 未定义、SourceBundle fixed fragment 替换边界不够硬、matmul Tensor Core spec 与 SIMT 口径冲突、fail-fast / memory / ring / launch 验收依赖未定义 API。最小需改项为补 exact signature 候选表、硬删除或硬替换 fixed fragment 主路径、统一 matmul 完成态为 `mma.sync` / `wmma` 或将 SIMT-only 转用户确认。
- 守护最终检验：未开始。
- 主线处理：进入 Draft 7，按两路 Round 1 最小需改项修订正文。
- 收敛结论：Round 1 未收敛；存在阻断性待用户确认项，当前不可下发。
- 状态：Draft 6 Round 1 不通过，已进入 Draft 7 修订。

### Draft 7

- 形成原因：处理 Draft 6 两路 Round 1 subagent strict review 的最小需改项。
- 标准包：本轮修订输入为根 `AGENTS.md`、当前角色 prompt、`agents/standard/计划书标准.md`、`agents/standard/审查规范.md`、`agents/standard/任务记录约定.md`、Draft 6 全文、Avicenna / Erdos Round 1 结论、用户 2026-06-09 include wrapper + emitc 确认来源、禁止修改面和必过验收命令。
- 严格通过口径：
  - exact signature 清单必须包含命名空间、函数 / 类型签名、模板参数、参数顺序、返回值、host/device qualifier、公开 vs `detail`、错误语义和 emitc 是否正向调用，并记录用户确认来源。
  - fixed fragment 主路径必须硬替换；`operation_source_fragments(...)`、`select_entry_symbol(...)`、`CUDA_SM86_KERNEL_*_FRAGMENT` 和固定 `kg_cuda_sm86_execute_*_ir` 不得作为主计算真源或 `kg_execute_entry` 可达路径。
  - matmul 默认完成态必须遵守现有 Tensor Core spec：`mma.sync` / `wmma` 参与最终输出；SIMT-only 只能作为待用户确认的 spec 变更。
  - 必须保留 A/A target-sm 决策、`expectation/` 只读、无必过 expectation、A1 清单之外 include signatures 未确认前不可下发。
- 主线处理：
  - 在 `公开 API 设计` 增加推荐候选 A1 exact signature 表，列出 `KernelContext`、arch query、DMA/ring、kernel wrapper、host/device qualifier、错误语义、emitc 是否正向调用和 `detail` 边界。
  - 在 `待确认项` 增加 A1/B/C 选项、TLM 表面类型取舍和稳定 unsupported 文本是否新增，并在用户回复后收口为 A1 与不新增稳定 unsupported 文本。
  - 将 fixed fragment 文本门禁改为实现侧不得存在固定主业务入口定义或调用；测试只能保留负向断言 / 历史说明。
  - 将 matmul SIMT 默认路径收紧为必须 `mma.sync` / `wmma` 参与最终输出，并按用户 2026-06-09 确认移出待确认项。
- tracked/index 证据：
  - 执行目录：`/home/lfr/kernelcode_generate`。
  - 写入本证据段前已执行 `git add -f ARCHITECTURE/plan/cuda_sm86_api_aligned_kernel_codegen.md`。
  - 写入本证据段前采样 `git ls-files --stage -- ARCHITECTURE/plan/cuda_sm86_api_aligned_kernel_codegen.md`：`100644 ec44ad053f2fc8459c82fcf7cb6239eb50d3cacd 0	ARCHITECTURE/plan/cuda_sm86_api_aligned_kernel_codegen.md`。
  - 写入本证据段前采样 `git diff --name-status -- ARCHITECTURE/plan/cuda_sm86_api_aligned_kernel_codegen.md`：无输出。
  - 写入本证据段前采样 `git diff --cached --name-status -- ARCHITECTURE/plan/cuda_sm86_api_aligned_kernel_codegen.md`：`A	ARCHITECTURE/plan/cuda_sm86_api_aligned_kernel_codegen.md`。
  - 写入本证据段前采样 `git status --short --ignored --untracked-files=all -- ARCHITECTURE/plan/cuda_sm86_api_aligned_kernel_codegen.md`：`A  ARCHITECTURE/plan/cuda_sm86_api_aligned_kernel_codegen.md`。
  - 写入本证据段前采样 `git diff --cached --check -- ARCHITECTURE/plan/cuda_sm86_api_aligned_kernel_codegen.md`：无输出。
  - 说明：`ls-files --stage` 的 blob hash 与文件内容自引用，写入本证据段后 hash 会变化；Round 2 strict review 必须在现场重跑上述命令确认当前 index 状态。
- subagent strict review：
  - Nash / 流程 API 公开边界 Round 2：不通过；阻断项为 TODO 真实状态与计划记录不一致、A1 exact signature 表仍使用组合 / 省略写法、`arch.get_block_num` 与公开 API 表不闭合。最小需改项为按 TODO 记录现有暂停态 execute、展开 A1 已确认签名、明确 `get_block_num` 是否走 public wrapper 或直接 lowering。
  - Ptolemy / CUDA 技术 emitc 分层 Round 2：不通过；阻断项为 A1 表未覆盖计划自身出现的 `copy/free/view/reshape/reinterpret/launch/block_num/subthread_*` wrapper / lowering 边界、TLM fragment view 与现有 `Memory<Space,T>` pointer-view 合同未形成可实现子合同。最小需改项为给出 wrapper 覆盖选项并回用户确认，给出 TLM 表示选项并回用户确认。
- 守护最终检验：未开始。
- 收敛结论：Round 2 未收敛；存在阻断性待用户确认项，当前不可下发。
- 状态：Draft 7 Round 2 不通过，已进入 Draft 8 待确认修订。

### Draft 8

- 形成原因：处理 Draft 7 Round 2 两路 subagent strict review 的阻断项，但其中 A1 外 wrapper 覆盖和 TLM fragment 表示涉及公开 API / include 类型边界，必须先由用户确认。
- 标准包：本轮修订输入为根 `AGENTS.md`、当前角色 prompt、`agents/standard/计划书标准.md`、`agents/standard/审查规范.md`、`agents/standard/任务记录约定.md`、Draft 7 全文、Nash / Ptolemy Round 2 结论、当前 `TODO.md` 真实状态、已确认 A1 签名、禁止修改面和必过验收命令。
- 严格通过口径：
  - 计划正文必须与 `TODO.md` 当前真实状态一致，不得新建第二个 execute。
  - A1 已确认 exact signatures 不得使用 `/`、`...`、`同形`、成员返回伪语法等模糊写法。
  - A1 外 wrapper 若新增 public signature，必须先记录用户确认来源；若不新增，必须把对应 IR op lowering 写成既有 wrapper、Memory 成员、direct CUDA expression、package-local glue 或 fail-fast。
  - 当时 TLM fragment 表示必须先收口：要么 `Memory<TLM1/TLM2/TLM3, T>` 作为逻辑 tile descriptor 且 detail 承接真实 fragment，要么新增 public Fragment / Tile 类型并获用户确认；Draft 9 已按用户确认收口为 CUDA 只支持 `TLM1` fragment，`TLM2/TLM3` unsupported。
- 主线处理：
  - 已把计划级任务状态改为 `T-20260608-bfe97ae7` 正在执行 / 暂停 / 指派 `金铲铲大作战`，并声明不得新建第二个 execute。
  - 已展开 A1 表内 `block_id`、`thread_id`、`thread_num`、`load`、`store`、`add`、`sub`、`mul`、`truediv`、`max`、`reduce_sum`、`reduce_max`、`DmaRing::current()` 和 `DmaRing::advance()` 模糊签名。
  - 已明确 A1 不新增 `block_num/subthread_*` public wrapper；推荐直接 lowering，但该推荐仍列入待确认项。
  - 已把 A1 外 wrapper 覆盖和 TLM fragment 表示整理成两个用户待确认项，给出选项、影响和推荐项。
- subagent strict review：Draft 8 待用户确认项收口后再发起下一轮 strict review；当前不通过。
- 守护最终检验：未开始。
- 收敛结论：未收敛；存在 2 项阻断性待用户确认项，当前不可下发。
- 状态：Draft 8 待用户确认；已进入 Draft 9 修订，不可分发。

### Draft 9

- 形成原因：用户收口 Draft 8 的两项公开 API / TLM fragment 待确认。
- 标准包：本轮修订输入为根 `AGENTS.md`、当前角色 prompt、`agents/standard/计划书标准.md`、`agents/standard/审查规范.md`、`agents/standard/任务记录约定.md`、Draft 8 全文、Nash / Ptolemy Round 2 结论、用户 2026-06-09 对 A1 外 wrapper 按 `npu_demo` 当前程度支持的确认、用户 2026-06-09 对 CUDA TLM fragment 只支持 `TLM1` 的确认、禁止修改面和必过验收命令。
- 严格通过口径：
  - `cuda_sm86::launch<...>` 和一维 `cuda_sm86::view(...)` exact signatures 必须记录为用户确认的 public include API。
  - `reshape` 必须走 `Memory::reshape(...)` 成员；`copy/free/reinterpret/block_num/subthread_*` 不得新增同名 public wrapper。
  - CUDA TLM fragment 成功路径只允许 `TLM1`；`TLM2/TLM3`、dynamic / large `tlm1` ring 和无法证明生命周期的 fragment ring 必须 fail-fast。
  - 第一阶段 `cuda_sm86::launch<...>` 按 `npu_demo` 当前程度只支持 static extent；dynamic launch extent 必须 fail-fast。
- 主线处理：
  - 在用户确认来源和已收口决策中补入决策 7 / 决策 8。
  - 在公开 API 表新增 `cuda_sm86::launch<...>` 和一维 `cuda_sm86::view(...)`，并明确 `copy/free/reinterpret/block_num/subthread_*` 不新增同名 public wrapper。
  - 将 memory hierarchy、space-pair lowering、ring lowering、op lowering、launch 验收和任务卡收口为 `TLM1` only / `TLM2/TLM3` unsupported。
  - 将 dynamic launch extent 从成功验收改为 fail-fast 验收。
- subagent strict review：待发起下一轮。
- 守护最终检验：未开始。
- 收敛结论：用户待确认项已收口；仍需下一轮 strict review 收敛和守护最终检验，当前不可下发。
- 状态：Draft 9 待 strict review，不可分发。

### Draft 10

- 形成原因：Draft 9 下一轮 strict review 未通过；同时用户进一步明确 CUDA TLM fragment 只需要 `TLM1` 表示，`TLM2/TLM3` 不支持。
- 标准包：
  - 根 `AGENTS.md`。
  - 当前角色 prompt `agents/codex-multi-agents/agents/榕/榕.prompt.md`。
  - `agents/standard/计划书标准.md`、`agents/standard/审查规范.md`、`agents/standard/任务记录约定.md`。
  - Draft 9 全文和本轮 diff。
  - Draft 9 用户确认来源、Draft 7 / Draft 8 历史问题、James / Wegener 本轮 strict review 回执。
  - 禁止修改面：`.skills/`、`expectation/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。
  - 必过验收命令：本计划 `验收设计` 中列出的 pytest、文本门禁、格式 / 状态门禁；当前无必过 `expectation`。
- 严格通过口径：
  - `cuda_sm86::launch<...>` 必须是 host trampoline / static extent wrapper，不得承担 SM86 设备能力探测、target/sm 推断或 fallback；非 SM86 gate 必须在调用 `kg_execute_entry` / `cuda_sm86::launch` / CUDA runtime 前停止。
  - `cuda_sm86::launch` 的 host `Context&` 与 device `cuda_sm86::KernelContext&` 必须分层；generated `__global__` 需要构造 device context，再调用 generated device body；不得把 host ctx 传入 device business body。
  - CUDA TLM fragment 成功路径只允许 `TLM1`；`TLM1` 不走普通 pointer-view API；`TLM2/TLM3`、dynamic / large TLM ring 和无法证明生命周期的 fragment path 必须 fail-fast。
  - 不新增 `cuda_sm86::conv2d` public wrapper；conv2d 通过 `img2col2d` / matmul / DMA wrapper 或 package-local direct conv generated glue 完成。
  - 无新增待用户确认项、无 `expectation/` 授权变更、无第二个 execute 任务。
- subagent strict review：
  - James / 流程 API 边界 Round 3：不通过；阻断项为当前主仓存在未授权 `expectation/` 变更，strict review 现场不满足敏感目录 clean 要求。最小需改项不是修改计划技术内容，而是在 clean strict-review worktree 或经授权处理 `expectation/` 脏改后重跑审阅。
  - Wegener / CUDA 技术 Round 3：不通过；阻断项一是 `cuda_sm86::launch` 表中“非 SM86 runtime gate”容易把设备探测放进 public launch wrapper，和 A/A 不推断 sm 决策冲突；阻断项二是 host launch `Context&` 与 device `KernelContext` 分层不清，可能把 host ctx 传入 device body；阻断项三是 `Memory<TLM1,T>` 与 pointer-view `Memory` 合同不闭合，`cuda_sm86::view` 若允许 TLM1 会把 fragment 当 pointer offset。
  - Harvey / 流程 API 权限 Round 4：PASS；阻断项无；最小需改项无；待确认项无。证据显示 clean worktree 只暂存本计划文件，`expectation/` 无命中；唯一计划级 execute、公开 API 用户确认、不得替代守护最终检验等流程边界均闭合。
  - Carson / CUDA 技术 Round 4：PASS；阻断项无；最小需改项无；待确认项无。确认非 SM86 gate 在 `kg_execute_entry` / `cuda_sm86::launch` / CUDA runtime 前停止、host launch context 与 device `KernelContext` 分层、TLM1-only fragment 子合同、matmul Tensor Core 硬门槛、conv2d 不新增 public wrapper、文本门禁均闭合。
- 主线处理：
  - 将非 SM86 gate 改为外部执行策略 / test harness / CI 或管理员验收现场的前置门禁；generated source、`kg_execute_entry`、`cuda_sm86::launch` 和 include wrapper 不查询设备能力、不推断 sm、不选择 target。
  - 将 `cuda_sm86::launch<...>` 记录为 host trampoline：host `Context&` 只作为 launch descriptor；generated `__global__` 在 device 侧构造 `cuda_sm86::KernelContext`，再调用 generated device body。
  - 将一维 `cuda_sm86::view(...)` 收窄为 `global/tsm` 等 pointer-view space 的 generated-source compatibility wrapper；`TLM1/TLM2/TLM3` 不走该 public wrapper。
  - 增加 `Memory<TLM1,T>` 子合同：只能由 fragment path 产生，不得发射 `data()`、`at()`、`Memory::view(...)`、`Memory::reshape(...)` 或 `cuda_sm86::view(...)`；TLM1 view-like 变化只能走 detail fragment descriptor glue 或 fail-fast。
  - 增加 source semantic / fail-fast 验收：锁定 device context construction、非 SM86 pre-entry stop、TLM1 ordinary view/reshape/reinterpret fail-fast、TLM2/TLM3 fail-fast、fragment transfer 不出现 `cudaMemcpy` 或 ordinary pointer offset。
  - 明确 conv2d 第一阶段不新增 `cuda_sm86::conv2d` public wrapper。
- 当前本地证据：
  - 执行目录：`/home/lfr/kernelcode_generate`。
  - 写入本证据段前已执行 `git diff --check -- ARCHITECTURE/plan/cuda_sm86_api_aligned_kernel_codegen.md`：无输出。
  - 写入本证据段前已执行 `git add -f ARCHITECTURE/plan/cuda_sm86_api_aligned_kernel_codegen.md`。
  - 写入本证据段前已执行 `git diff --cached --check -- ARCHITECTURE/plan/cuda_sm86_api_aligned_kernel_codegen.md`：无输出。
  - 写入本证据段前采样 `git ls-files --stage -- ARCHITECTURE/plan/cuda_sm86_api_aligned_kernel_codegen.md`：`100644 55595a89580b5edc3ad317989bb604bf6ee93707 0 ARCHITECTURE/plan/cuda_sm86_api_aligned_kernel_codegen.md`。
  - 写入本证据段前采样 `git diff --cached --name-status -- ARCHITECTURE/plan/cuda_sm86_api_aligned_kernel_codegen.md expectation`：`A ARCHITECTURE/plan/cuda_sm86_api_aligned_kernel_codegen.md`。
  - 写入本证据段前采样 `git diff --name-status -- ARCHITECTURE/plan/cuda_sm86_api_aligned_kernel_codegen.md expectation`：`M expectation/dsl/emit_c/npu_demo/dma/deslice.py`。
  - 说明：`ls-files --stage` 的 blob hash 与文件内容自引用，写入本证据段后 hash 会变化；后续 clean strict review 必须在现场重跑上述命令确认当前 index 状态。
  - 主仓存在与本计划无关的 `expectation/` 未授权脏现场；本计划修订未修改 `expectation/`。clean strict-review 需要使用独立 clean worktree，或由用户 / 管理员授权处理该 `expectation/` 脏现场。
  - clean strict-review worktree：`/home/lfr/kernelcode_generate/wt-20260609-cuda-sm86-plan-strict-review`，detached HEAD=`22f89a50fd219637b62485ebf55d0267d56fad94`，merge-base with `origin/main`=`22f89a50fd219637b62485ebf55d0267d56fad94`。
  - clean worktree 写入本证据段前采样 `git -C wt-20260609-cuda-sm86-plan-strict-review status --short --ignored --untracked-files=all -- ARCHITECTURE/plan/cuda_sm86_api_aligned_kernel_codegen.md expectation`：`A  ARCHITECTURE/plan/cuda_sm86_api_aligned_kernel_codegen.md`，无 `expectation/` 命中。
  - clean worktree 写入本证据段前采样 `git -C wt-20260609-cuda-sm86-plan-strict-review diff --cached --check -- ARCHITECTURE/plan/cuda_sm86_api_aligned_kernel_codegen.md`：无输出。
  - clean worktree 写入本证据段前采样 `git -C wt-20260609-cuda-sm86-plan-strict-review ls-files --stage -- ARCHITECTURE/plan/cuda_sm86_api_aligned_kernel_codegen.md`：`100644 c9b0f73c96f3f3bb3fade05d0ee688ba04a103d1 0 ARCHITECTURE/plan/cuda_sm86_api_aligned_kernel_codegen.md`。
  - clean worktree 写入本证据段前采样 `git -C wt-20260609-cuda-sm86-plan-strict-review diff --cached --name-status -- ARCHITECTURE/plan/cuda_sm86_api_aligned_kernel_codegen.md expectation`：`A ARCHITECTURE/plan/cuda_sm86_api_aligned_kernel_codegen.md`。
  - clean worktree 写入本证据段前采样 `git -C wt-20260609-cuda-sm86-plan-strict-review diff --name-status -- expectation`：无输出。
  - Round 4 clean worktree strict review 后采样：Harvey / Carson 均 PASS；执行目录为 `/home/lfr/kernelcode_generate/wt-20260609-cuda-sm86-plan-strict-review`；`git status --short --ignored --untracked-files=all -- ARCHITECTURE/plan/cuda_sm86_api_aligned_kernel_codegen.md expectation` 仅显示计划文件暂存新增；`expectation/` 无未暂存或暂存 diff；`git diff --cached --check -- ARCHITECTURE/plan/cuda_sm86_api_aligned_kernel_codegen.md` 通过；本轮 PASS 时 staged blob 为 `fa01fcdef17b71f817225897858d4c7f4c8bbc84`。
- 守护最终检验：2026-06-10 由 `守护最好的爱莉希雅` 本人在 clean worktree `/home/lfr/kernelcode_generate/wt-20260609-cuda-sm86-plan-strict-review` 执行，结论 PASS；无阻断项、无最小需改项、无待确认项。关键证据：HEAD 与 `origin/main` merge-base 均为 `22f89a50fd219637b62485ebf55d0267d56fad94`；暂存区仅新增本计划文件；`expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md` 无暂存或未暂存 diff；`git diff --cached --check -- ARCHITECTURE/plan/cuda_sm86_api_aligned_kernel_codegen.md` 通过；当前无必过 `expectation`。
- 收敛结论：Round 4 已在 clean worktree 收敛；Harvey / Carson 两路 subagent strict review 均无阻断、无最小需改项、无待确认项；`守护最好的爱莉希雅` 本人守护最终检验通过。当前仍不可直接分发，必须等待 `T-20260607-0c4db1f1 / multi_buffer_loop_staging_ring` 及其依赖完成、合并并同步；若绕过该依赖必须先取得用户明确确认并重新 strict review / 守护最终检验。
- 状态：Draft 10 Round 4 strict review 收敛通过，守护最终检验通过；依赖完成、合并并同步前不可分发。

## 计划书入档验收 / 复验 / 修复复核记录

- 结论人：待计划级 `execute` 完成后由计划书入档验收角色填写。
- 验证基线：待填写。
- 执行目录：待填写。
- 合同验收摘要：当前无必过 `expectation`；若正式计划修订后新增，按正式计划正文执行。
- 结论：待填写。
