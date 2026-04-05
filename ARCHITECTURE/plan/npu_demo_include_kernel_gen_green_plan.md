# npu_demo_include_kernel_gen_green_plan.md

## 进度

| 编号 | 依赖 | worktree | 记录文件 | 进度 |
| --- | --- | --- | --- | --- |
| `S1` | `无` | `wt-20260405-npu-demo-include-s1` | `20260405-npu-demo-include-s1.md` | `实现+补测完成（T-20260405-d1d6ada1，金铲铲大作战）；复审通过（T-20260405-49cc719b，不要啊教练）；已合并（commit 092d884，T-20260405-251880e3，李白）。` |
| `S2` | `S1` | `wt-20260405-npu-demo-include-s2` | `20260405-npu-demo-include-s2.md` | `实现+补测完成（T-20260405-2c0148f6，小李飞刀）；复审需修改（T-20260405-7c061dcf，不要啊教练：diff 为空且 test/include/api/test_memory.py 未追踪，spec/include/api/Memory.md test 条目未更新）；修复完成（T-20260405-0e954375，小李飞刀：补 spec test 条目并纳入追踪，pytest exit=0）；复审需修改（T-20260405-ad19ee48，不要啊教练：diff 仅 spec/include/api/Memory.md，test/include/api/test_memory.py 与记录仍未追踪）；修复完成（T-20260405-ad19ee48，小李飞刀）；复审通过（T-20260405-3792c441，不要啊教练；gate exit=0）；已合并（commit f8b5bbe，T-20260405-92ad86c3，李白；gate exit=0）。` |
| `S3` | `S1` | `wt-20260405-npu-demo-include-s3` | `20260405-npu-demo-include-s3.md` | `实现+补测完成（T-20260405-77b08592，金铲铲大作战；pytest exit=0）；复审需修改（T-20260405-f8efb199，不要啊教练：view(标量/Vector) 缺 1-D 边界校验/失败机制与负例门禁）；修复完成（T-20260405-382d7490，金铲铲大作战：补齐 1-D rank/向量长度/非法 offset-size-stride/越界校验，失败机制统一为 runtime_error(dma.view: ...)，并新增 KC-008 负例门禁；pytest exit=0）；待复审（T-20260405-5940bfee，不要啊教练）。` |
| `S4` | `S2、S3` | `wt-20260405-npu-demo-include-s4` | `20260405-npu-demo-include-s4.md` | `已合并（commit d46343c，T-20260405-149e00f9，李白；gate exit=0）。` |
| `S5` | `S4` | `wt-20260405-npu-demo-include-s5` | `20260405-npu-demo-include-s5.md` | `已合并（commit 8b51d3e，T-20260405-4689e197，李白；gate exit=0）。` |
| `S6` | `S5` | `/home/lfr/kernelcode_generate` | `不要求` | `未开始` |
| `S7` | `S6` | `/home/lfr/kernelcode_generate` | `不要求` | `未开始` |

## 功能说明

- 本计划用于把 `npu_demo` 目标当前已经冻结的 `gen_kernel` 源码骨架，补齐到“有正式 include 合同、能经 header 编译通过”的状态。
- 当前真实问题不是 `gen_kernel` 不会生成源码，而是“源码文本已经生成，但缺统一 API include 落点与编译级闭环”：
  - `kernel_gen/dsl/emit_c.py` 与 `kernel_gen/dsl/gen_kernel.py` 已经固定发射 `view(...)`、`slice(...)`、`deslice(...)`、`add(...)`、`Memory<T>`、`MemorySpace::TSM/TLM`。
  - `spec/include/api/Dma.md`、`spec/include/api/Memory.md`、`spec/include/api/Nn.md` 已声明统一头文件目标，但仓库里实际只有 [`include/api/Core.h`](/home/lfr/kernelcode_generate/include/api/Core.h)。
  - [`include/npu_demo/npu_demo.h`](/home/lfr/kernelcode_generate/include/npu_demo/npu_demo.h) 目前只定义 `KernelContext` 与 `get_dynamic_memory(...)`，并未提供 `gen_kernel` 生成源码会直接调用的 free helper。
  - [`test/dsl/test_gen_kernel.py`](/home/lfr/kernelcode_generate/test/dsl/test_gen_kernel.py) 对 `npu_demo` 目前只有字符串门禁，没有 compile gate。
- 本计划目标是先补最小闭环：让 `target="npu_demo"` 当前已经发射的 body-level kernel 源码，在仅引入 `npu_demo` 对应 include 的前提下可以编译；同时把通用接口合同收口到 `include/api`，而把后端具体实现放回 `include/npu_demo`，避免把“公共接口”和“后端实现”混在一层。
- 本文件只给计划，不直接修改实现。
- 分工约束补充如下：
  - 任务默认按 `spec任务` 分发，但执行时允许联动修改 `spec / 功能实现 / test`，不能机械理解成“只改 spec”。
  - 每个 `spec任务` 都是同一条任务链的起点，任务书必须覆盖其后的 `实现/重构 -> 审查（含复审） -> 合并`。
  - `大闸蟹` 只在整个计划全部任务完成并合并后，进行统一的架构师验收；不对单个 `S*` 任务逐个验收。
  - 本轮不触碰 `expectation/**`；本计划主目标是 include/spec/codegen/test 绿灯。

## 范围与非目标

### 范围

- `spec`
  - [`spec/include/api/Core.md`](/home/lfr/kernelcode_generate/spec/include/api/Core.md)
  - [`spec/include/api/Memory.md`](/home/lfr/kernelcode_generate/spec/include/api/Memory.md)
  - [`spec/include/api/Dma.md`](/home/lfr/kernelcode_generate/spec/include/api/Dma.md)
  - [`spec/include/api/Nn.md`](/home/lfr/kernelcode_generate/spec/include/api/Nn.md)
  - [`spec/include/npu_demo/npu_demo.md`](/home/lfr/kernelcode_generate/spec/include/npu_demo/npu_demo.md)
  - [`spec/dsl/emit_c.md`](/home/lfr/kernelcode_generate/spec/dsl/emit_c.md)
  - [`spec/dsl/gen_kernel.md`](/home/lfr/kernelcode_generate/spec/dsl/gen_kernel.md)
- `接口声明`
  - 允许新增：
    - [`include/api/Memory.h`](/home/lfr/kernelcode_generate/include/api/Memory.h)（公共类型声明；不写实现）
    - [`include/api/Dma.h`](/home/lfr/kernelcode_generate/include/api/Dma.h)（公共接口声明；不写实现）
    - [`include/api/Nn.h`](/home/lfr/kernelcode_generate/include/api/Nn.h)（公共接口声明；不写实现）
- `功能实现`
  - 允许新增：
    - [`include/npu_demo/Dma.h`](/home/lfr/kernelcode_generate/include/npu_demo/Dma.h)
    - [`include/npu_demo/Nn.h`](/home/lfr/kernelcode_generate/include/npu_demo/Nn.h)
  - 允许修改：
    - [`include/npu_demo/npu_demo.h`](/home/lfr/kernelcode_generate/include/npu_demo/npu_demo.h)
    - [`kernel_gen/dsl/emit_c.py`](/home/lfr/kernelcode_generate/kernel_gen/dsl/emit_c.py)
    - [`kernel_gen/dsl/gen_kernel.py`](/home/lfr/kernelcode_generate/kernel_gen/dsl/gen_kernel.py)
- `test`
  - 允许新增：
    - [`test/include/api/test_memory.py`](/home/lfr/kernelcode_generate/test/include/api/test_memory.py)
    - [`test/include/api/test_dma.py`](/home/lfr/kernelcode_generate/test/include/api/test_dma.py)
    - [`test/include/api/test_nn.py`](/home/lfr/kernelcode_generate/test/include/api/test_nn.py)
  - 允许修改：
    - [`test/include/npu_demo/test_kernel_context.py`](/home/lfr/kernelcode_generate/test/include/npu_demo/test_kernel_context.py)
    - [`test/dsl/test_gen_kernel.py`](/home/lfr/kernelcode_generate/test/dsl/test_gen_kernel.py)

### 非目标

- 不新增 host runtime、launch API、stream、event、barrier、async pipeline、driver wrapper。
- 不把 `npu_demo` 一次性扩展到 `dma.fill/load/store/reshape/cast` 的完整 include 面；本轮只收口当前 `gen_kernel` 已经发射或其直接依赖的最小集合。
- 不改 DSL 用户侧 helper 形态，不改 `operation/dialect` 的公开签名。
- 不把 `include/api` 设计成复杂模板库；优先保证 `Memory/View/Copy/Elementwise` 的最小稳定接口。
- 不把 `include/api` 当作实现容器；其中只允许公共类型/接口声明，不写 `npu_demo`、`cpu` 等后端行为实现，也不写通用算子实现。
- 不通过增加 wrapper `using` 样板来规避统一头文件缺失；目标是 include 合同本身成立。

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`大闸蟹`
- `文档`：[`ARCHITECTURE/plan/npu_demo_include_kernel_gen_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/npu_demo_include_kernel_gen_green_plan.md)
- `spec`：
  - [`spec/include/api/Memory.md`](/home/lfr/kernelcode_generate/spec/include/api/Memory.md)
  - [`spec/include/api/Dma.md`](/home/lfr/kernelcode_generate/spec/include/api/Dma.md)
  - [`spec/include/api/Nn.md`](/home/lfr/kernelcode_generate/spec/include/api/Nn.md)
  - [`spec/include/npu_demo/npu_demo.md`](/home/lfr/kernelcode_generate/spec/include/npu_demo/npu_demo.md)
  - [`spec/dsl/gen_kernel.md`](/home/lfr/kernelcode_generate/spec/dsl/gen_kernel.md)
- `接口声明`：
  - [`include/api/Memory.h`](/home/lfr/kernelcode_generate/include/api/Memory.h)
  - [`include/api/Dma.h`](/home/lfr/kernelcode_generate/include/api/Dma.h)
  - [`include/api/Nn.h`](/home/lfr/kernelcode_generate/include/api/Nn.h)
- `功能实现`：
  - [`include/npu_demo/npu_demo.h`](/home/lfr/kernelcode_generate/include/npu_demo/npu_demo.h)
  - [`kernel_gen/dsl/emit_c.py`](/home/lfr/kernelcode_generate/kernel_gen/dsl/emit_c.py)
  - [`kernel_gen/dsl/gen_kernel.py`](/home/lfr/kernelcode_generate/kernel_gen/dsl/gen_kernel.py)
- `test`：
  - [`test/include/npu_demo/test_kernel_context.py`](/home/lfr/kernelcode_generate/test/include/npu_demo/test_kernel_context.py)
  - [`test/dsl/test_gen_kernel.py`](/home/lfr/kernelcode_generate/test/dsl/test_gen_kernel.py)

## 外部参考

- 仅作接口风格校准，不替代仓库内 spec：
  - CUTLASS C++ layout / runtime tensor-view 思路：<https://docs.nvidia.com/cutlass/media/docs/cpp/layout.html>
  - CUDA Runtime memory API：<https://docs.nvidia.com/cuda/cuda-runtime-api/group__CUDART__MEMORY.html>
- 本轮只吸收两点风格，不直接照搬：
  - 运行期 `shape/stride/layout` 是轻量视图，不和 launch/runtime 绑定。
  - copy / writeback 类接口保持显式 `target` / `source` 责任，不做隐式分配或隐式 fallback。

## 当前实测状态

### 当前已经存在的源码合同

- [`kernel_gen/dsl/emit_c.py`](/home/lfr/kernelcode_generate/kernel_gen/dsl/emit_c.py) 已冻结 `target="npu_demo"` 下的节点级文本：
  - `view(source, offset, size, stride)`
  - `slice(target, source, offset, size, stride)`
  - `deslice(source, target, offset, size, stride)`
  - `add(lhs, rhs, out)`
  - `ctx.get_dynamic_memory<T>(MemorySpace::TSM/TLM)`
- [`kernel_gen/dsl/gen_kernel.py`](/home/lfr/kernelcode_generate/kernel_gen/dsl/gen_kernel.py) 已冻结 `npu_demo` body-level kernel 骨架顺序：
  - `thread_id/thread_num`
  - `TSM/TLM dynamic memory`
  - `view`
  - `slice`
  - `add`
  - `deslice`

### 当前真实缺口

| 层级 | 当前状态 | 真实缺口 |
| --- | --- | --- |
| `include/api` | `缺失` | `spec/include/api/*.md` 已声明公共接口头文件目标，但接口声明头文件本身未落地，且“公共接口声明 / 后端实现”边界未固定 |
| `include/npu_demo` | `半完成` | 只有 `KernelContext`，没有按 `include/api` 接口承接 `view/slice/deslice/add` 的后端实现闭环 |
| `gen_kernel` | `文本已冻结` | `npu_demo` 只有字符串检查，没有 compile gate |
| `spec` | `分层不一致` | `include/api`、`npu_demo`、`emit_c/gen_kernel` 之间还没写清“谁提供哪些名字、谁是统一入口” |
| `test` | `覆盖不足` | 没有 `include/api` 的接口头文件测试，也没有 `npu_demo` generated source 的编译测试 |

### 现状判断

- 当前最小成功闭环并不是“再给 `npu_demo.h` 私下塞几个 helper 就结束”，而是：
  1. 先把 `include/api` 的统一接口头文件补齐，但不把后端实现写进去；
  2. 再让 `npu_demo` 侧按这些接口补自己的实现/适配；
  3. 最后加 `gen_kernel` compile gate，证明生成源码确实能被 `npu_demo` 头文件消费。
- 这样后续如果 `cuda_demo`、`rvv_demo` 或其他 target 复用同一批 helper，就不会再次回到“每个后端私有复制一套 `view/slice/add`”。

## 设计原则

- 新增接口若通用，优先先在 `include/api` 冻结名字、参数与返回语义；具体后端实现落到各自后端目录。
- `include/api` 只承载公共类型声明与公共接口声明，不承载 `npu_demo` 等后端算子行为实现，也不承载通用 helper 实现。
- `npu_demo.h` 只保留后端私有能力：`KernelContext`、固定硬件模板常量、动态片上内存入口，以及对 `include/api` 接口的 `npu_demo` 侧实现/汇总。
- `gen_kernel` 当前已经发射的无命名空间接口名保持不变，即继续使用：
  - `Memory<T>`
  - `MemorySpace`
  - `view(...)`
  - `slice(...)`
  - `deslice(...)`
  - `add(...)`
- 因此 `include/api` 必须提供上述名字的统一合同；`npu_demo` 侧必须提供能被这些名字直接消费的实现。不能要求 generated source 再手写 `using cpu::Memory;` 这类额外样板。
- `slice/deslice/add` 可以继续返回 `Status`；`gen_kernel` 当前忽略返回值，不构成编译障碍。但错误边界必须在 include 层明确：
  - shape/stride/rank 不匹配返回 `kError`
  - 不允许静默分配、静默 broadcast 或静默 layout 修复
- `view(...)` 继续返回 `Memory<T>` 视图，保持“逻辑窗口”职责，不发生分配。

## P0 目标合同

### 统一头文件目标

- `include/api/Memory.h`
  - 提供统一公开的 `MemoryFormat`、`MemorySpace`、`Memory<T>` 公共类型声明合同。
  - 本文件只声明类型与签名，不写构造逻辑、访问逻辑或任何后端无关/后端相关实现。
- `include/api/Dma.h`
  - 提供统一公开的 `view / slice / deslice` 接口合同。
  - 本文件只声明接口签名，不承载 `npu_demo` / `cpu` 的具体行为实现。
- `include/api/Nn.h`
  - 至少提供统一公开的 `add(lhs, rhs, out)` 接口合同。
  - 本文件只声明接口签名，不承载 `npu_demo` / `cpu` 的具体行为实现。

### `npu_demo` 目标

- `include/npu_demo/npu_demo.h` 必须成为 `npu_demo` body-level kernel 的唯一必要 include。
- `include/npu_demo/npu_demo.h` 负责汇总 `npu_demo` 的后端实现，使其符合 `include/api` 已冻结的接口名字和参数语义。
- 仅通过：

```cpp
#include "include/npu_demo/npu_demo.h"
```

- 就能让下面这类 generated source 至少编译通过：

```cpp
void demo_kernel(npu_demo::KernelContext& ctx, const Memory<float>& source, Memory<float>& out) {
    long long tid = ctx.thread_id();
    Memory<float> tsm = ctx.get_dynamic_memory<float>(MemorySpace::TSM);
    auto src_view = view(source, tid * 16, 16, 1);
    auto work_tile = view(tsm, 0, 16, 1);
    slice(work_tile, src_view, 0, 16, 1);
    add(work_tile, work_tile, out);
}
```

### compile gate 目标

- [`test/dsl/test_gen_kernel.py`](/home/lfr/kernelcode_generate/test/dsl/test_gen_kernel.py) 需要新增 `npu_demo` compile smoke：
  - 通过 `gen_kernel(...)` 真实生成源码；
  - 外层只加 `#include "include/npu_demo/npu_demo.h"` 与最小 `main`；
  - 至少完成编译与链接；
  - 若运行会触发空指针访问，则该用例允许“只编译不执行”，但必须把原因写入测试注释与 spec。

## P1 预留目标

- 若本轮完成后接口仍明显通用，可继续扩展：
  - `include/api/Nn.h`：`sub/mul/truediv/select/cast/compare`
  - `include/api/Dma.h`：`fill/load/store/reshape/cast`
- 但这些不属于本轮必须 gate；本轮只围绕 `npu_demo` 当前已发射的 helper 集合闭环。

## 完成定义

- `spec/include/api/*.md` 与真实 header 一致，不再出现“spec 有统一头文件、仓库没有实现文件”的空洞状态。
- `include/api` 只落公共类型/接口声明，不落任何实现。
- `spec/include/npu_demo/npu_demo.md` 明确写清：
  - `npu_demo.h` 自身提供什么；
  - `npu_demo.h` 通过 include/适配承接哪些统一 API；
  - generated source 依赖的 helper 名称由哪个层级冻结、由哪个层级实现。
- 至少补齐以下公共接口声明头文件：
  - [`include/api/Memory.h`](/home/lfr/kernelcode_generate/include/api/Memory.h)
  - [`include/api/Dma.h`](/home/lfr/kernelcode_generate/include/api/Dma.h)
  - [`include/api/Nn.h`](/home/lfr/kernelcode_generate/include/api/Nn.h)
- 至少新增以下 `npu_demo` 侧实现或分拆头文件（按实现需要择一或全部）：
  - [`include/npu_demo/Dma.h`](/home/lfr/kernelcode_generate/include/npu_demo/Dma.h)
  - [`include/npu_demo/Nn.h`](/home/lfr/kernelcode_generate/include/npu_demo/Nn.h)
  - [`include/npu_demo/npu_demo.h`](/home/lfr/kernelcode_generate/include/npu_demo/npu_demo.h)
- 至少新增以下测试闭环：
  - `include/api` 接口头文件测试
  - `npu_demo.h` 传递 include 测试
  - `gen_kernel(target="npu_demo")` compile smoke
- 以下 gate 全部通过：

```bash
pytest -q test/include/api/test_core.py test/include/api/test_memory.py test/include/api/test_dma.py test/include/api/test_nn.py
pytest -q test/include/npu_demo/test_kernel_context.py
pytest -q test/dsl/test_gen_kernel.py -k 'npu_demo'
```

- 仅当全部 `S*` 任务都完成并合并后，整个计划才进入 `待架构师验收`。

## 计划任务

### `S1`

- `任务类型`：`spec任务（允许联动 spec / 实现 / test）`
- `阶段链路`：`spec -> 实现/重构 -> 审查（含复审） -> 合并`
- `目标`：冻结 `include/api` 与 `npu_demo` 的分层职责，写清谁定义 `Memory / view / slice / deslice / add`，谁定义 `KernelContext`。
- `需要收口的合同`：
  - `include/api/Memory.h` 是统一 `Memory<T>` 公共类型声明入口
  - `include/api/Dma.h` / `include/api/Nn.h` 只冻结统一接口声明，不承载任何实现
  - `include/npu_demo/*` 按统一接口承接 `npu_demo` 的具体行为实现
  - `include/npu_demo/npu_demo.h` 负责汇总后端私有上下文与后端实现
  - `gen_kernel` 的无命名空间源码形态继续成立
- `代码示例`：

```cpp
#include "include/npu_demo/npu_demo.h"

void demo_kernel(npu_demo::KernelContext& ctx, const Memory<float>& source, Memory<float>& out);
```

```cpp
auto tile = view(source, 16, 16, 1);
Status s0 = slice(tile, source, 16, 16, 1);
Status s1 = add(tile, tile, out);
```

- `可改文件`：
  - [`spec/include/api/Memory.md`](/home/lfr/kernelcode_generate/spec/include/api/Memory.md)
  - [`spec/include/api/Dma.md`](/home/lfr/kernelcode_generate/spec/include/api/Dma.md)
  - [`spec/include/api/Nn.md`](/home/lfr/kernelcode_generate/spec/include/api/Nn.md)
  - [`spec/include/npu_demo/npu_demo.md`](/home/lfr/kernelcode_generate/spec/include/npu_demo/npu_demo.md)
  - [`spec/dsl/emit_c.md`](/home/lfr/kernelcode_generate/spec/dsl/emit_c.md)
  - [`spec/dsl/gen_kernel.md`](/home/lfr/kernelcode_generate/spec/dsl/gen_kernel.md)
- `验收标准`：
  - 不再存在“公共接口 / 后端实现”混层
  - `npu_demo` 与 `include/api` 的边界清楚
  - compile gate 目标写入 spec，而不是只靠口头说明

### `S2`

- `任务类型`：`spec任务（API 声明子任务）`
- `阶段链路`：`spec -> 声明落地 -> 审查（含复审） -> 合并`
- `目标`：补齐 [`include/api/Memory.h`](/home/lfr/kernelcode_generate/include/api/Memory.h) 这一公共类型声明文件，把统一 `Memory<T>` 公共类型声明落地。
- `实现方向`：
  - 公开 `MemoryFormat`、`MemorySpace`、`Memory<T>` 的公共类型声明
  - 不在本文件中写构造/访问/helper 行为实现
  - 具体实现与可执行语义由后端侧头文件承接
- `代码示例`：

```cpp
#include "include/api/Memory.h"

void accept_memory_contract(
    const Memory<float>& source,
    Memory<float>& target,
    MemorySpace space,
    MemoryFormat format);
```

```cpp
Memory<float>* maybe_mem = nullptr;
const Memory<float>* maybe_const_mem = nullptr;
```

- `可改文件`：
  - [`include/api/Memory.h`](/home/lfr/kernelcode_generate/include/api/Memory.h)
  - [`spec/include/api/Memory.md`](/home/lfr/kernelcode_generate/spec/include/api/Memory.md)
  - 允许补充：[`test/include/api/test_memory.py`](/home/lfr/kernelcode_generate/test/include/api/test_memory.py)
- `验收标准`：
  - `#include "include/api/Memory.h"` + 最小声明片段可通过编译
  - `Memory<T>` / `MemorySpace` / `MemoryFormat` 的公共声明无歧义
  - 与 `spec/include/api/Memory.md` 一致

### `S3`

- `任务类型`：`spec任务（API 声明子任务）`
- `阶段链路`：`spec -> 声明落地 -> 审查（含复审） -> 合并`
- `目标`：补齐 [`include/api/Dma.h`](/home/lfr/kernelcode_generate/include/api/Dma.h) 与 [`include/api/Nn.h`](/home/lfr/kernelcode_generate/include/api/Nn.h) 这两份公共接口声明头文件，把 `view/slice/deslice/add` 的公共接口声明落地。
- `最小支持集合`：
  - `view(source, offset, size, stride)` 的统一接口声明
  - `slice(target, source, offset, size, stride)` 的统一接口声明
  - `deslice(source, target, offset, size, stride)` 的统一接口声明
  - `add(lhs, rhs, out)` 的统一接口声明
  - 若 `Vector` 版和标量版都需要，先在接口层明确二者关系，再由后端决定支持子集
- `代码示例`：

```cpp
auto tile = view(source, 32, 16, 1);
Status s = slice(tile, source, 32, 16, 1);
Status t = deslice(tile, target, 64, 16, 1);
```

```cpp
long long offset_buf[1] = {32};
long long size_buf[1] = {16};
long long stride_buf[1] = {1};
Vector offset(offset_buf, 1);
Vector size(size_buf, 1);
Vector stride(stride_buf, 1);
Status ok = slice(tile, source, offset, size, stride);
```

- `可改文件`：
  - [`include/api/Dma.h`](/home/lfr/kernelcode_generate/include/api/Dma.h)
  - [`include/api/Nn.h`](/home/lfr/kernelcode_generate/include/api/Nn.h)
  - [`spec/include/api/Dma.md`](/home/lfr/kernelcode_generate/spec/include/api/Dma.md)
  - [`spec/include/api/Nn.md`](/home/lfr/kernelcode_generate/spec/include/api/Nn.md)
  - 允许补充：[`test/include/api/test_dma.py`](/home/lfr/kernelcode_generate/test/include/api/test_dma.py)
- `验收标准`：
  - `include/api` 头文件只表达公共接口声明
  - 不把 `npu_demo` / `cpu` 行为实现写进 `include/api`
  - 接口与 `spec/include/api/Dma.md` / `spec/include/api/Nn.md` 一致

### `S4`

- `任务类型`：`spec任务（实现子任务）`
- `阶段链路`：`spec -> 实现/重构 -> 审查（含复审） -> 合并`
- `目标`：在 `include/npu_demo` 下按 `include/api` 接口补齐 `view/slice/deslice/add` 的 `npu_demo` 实现。
- `实现方向`：
  - 先完成当前 `gen_kernel` 真实依赖的 1-D 子集
  - `view` 返回 `Memory<T>` 视图
  - `slice/deslice/add` 返回 `Status`
  - shape/stride/rank 不一致时显式失败
  - 允许内部复用 [`include/cpu/Memory.h`](/home/lfr/kernelcode_generate/include/cpu/Memory.h) / [`include/cpu/Nn.h`](/home/lfr/kernelcode_generate/include/cpu/Nn.h)，但只能作为实现细节，不暴露 `cpu::` 作为统一合同
- `代码示例`：

```cpp
auto tile = view(source, 32, 16, 1);
Status s0 = slice(tile, source, 32, 16, 1);
Status s1 = deslice(tile, target, 64, 16, 1);
```

```cpp
add(work_tile, work_tile, out_tile);
```

- `可改文件`：
  - [`include/npu_demo/Dma.h`](/home/lfr/kernelcode_generate/include/npu_demo/Dma.h)
  - [`include/npu_demo/Nn.h`](/home/lfr/kernelcode_generate/include/npu_demo/Nn.h)
  - [`spec/include/npu_demo/npu_demo.md`](/home/lfr/kernelcode_generate/spec/include/npu_demo/npu_demo.md)
  - 允许补充：[`test/include/npu_demo/test_kernel_context.py`](/home/lfr/kernelcode_generate/test/include/npu_demo/test_kernel_context.py)
- `验收标准`：
  - 当前 `gen_kernel` 发出的 1-D `view/slice/deslice/add` 能被 `npu_demo` 真实 header 承接
  - 合法/非法输入边界在 `npu_demo` include 层清楚
  - 不要求本轮一次性补全 `sub/mul/truediv/compare`

### `S5`

- `任务类型`：`spec任务（实现子任务）`
- `阶段链路`：`spec -> 实现/重构 -> 审查（含复审） -> 合并`
- `目标`：重构 [`include/npu_demo/npu_demo.h`](/home/lfr/kernelcode_generate/include/npu_demo/npu_demo.h) 与对应 spec，让它成为 `npu_demo` 的单入口 include。
- `需要收口的合同`：
  - `npu_demo.h` 传递包含 `include/api/Memory.h`、`include/api/Dma.h`、`include/api/Nn.h`
  - `npu_demo.h` 继续只定义/汇总 `KernelContext`、动态内存模板与 `npu_demo` 侧实现
  - `npu_demo` 的实现文件对齐 `include/api` 声明的名字与参数语义
- `代码示例`：

```cpp
#include "include/npu_demo/npu_demo.h"

npu_demo::KernelContext ctx;
auto tsm = ctx.get_dynamic_memory<float>(MemorySpace::TSM);
auto tile = view(tsm, 0, 16, 1);
```

```cpp
try {
    auto sm = ctx.get_dynamic_memory<float>(MemorySpace::SM);
} catch (...) {
}
```

- `可改文件`：
  - [`include/npu_demo/npu_demo.h`](/home/lfr/kernelcode_generate/include/npu_demo/npu_demo.h)
  - [`spec/include/npu_demo/npu_demo.md`](/home/lfr/kernelcode_generate/spec/include/npu_demo/npu_demo.md)
  - [`test/include/npu_demo/test_kernel_context.py`](/home/lfr/kernelcode_generate/test/include/npu_demo/test_kernel_context.py)
- `验收标准`：
  - `npu_demo.h` 单独足以支撑 generated source compile
  - `KernelContext` 旧合同不回退
  - spec 写清“公共接口 + 后端实现 + 私有上下文”的组合关系

### `S6`

- `任务类型`：`spec任务（实现子任务）`
- `阶段链路`：`spec -> 实现/重构 -> 审查（含复审） -> 合并`
- `目标`：补 `gen_kernel` 编译级闭环测试，验证 `target="npu_demo"` 真实源码可编译。
- `需要补的 gate`：
  - 继续保留现有字符串门禁
  - 新增 compile smoke，外层只 include `npu_demo.h`
  - 若运行不安全，则分离 compile-only helper，不强制执行 body
- `代码示例`：

```python
source = gen_kernel(func_op, EmitCContext(target="npu_demo"))
cpp_source = f'''
#include "include/npu_demo/npu_demo.h"
{source}
int main() {{ return 0; }}
'''
```

```python
assert "auto src_view = view(source, tid * 16, 16, 1);" in source
assert "slice(work_tile, src_view, 0, 16, 1);" in source
```

- `可改文件`：
  - [`test/dsl/test_gen_kernel.py`](/home/lfr/kernelcode_generate/test/dsl/test_gen_kernel.py)
  - 允许必要联动：[`kernel_gen/dsl/emit_c.py`](/home/lfr/kernelcode_generate/kernel_gen/dsl/emit_c.py)
  - 允许必要联动：[`kernel_gen/dsl/gen_kernel.py`](/home/lfr/kernelcode_generate/kernel_gen/dsl/gen_kernel.py)
  - [`spec/dsl/gen_kernel.md`](/home/lfr/kernelcode_generate/spec/dsl/gen_kernel.md)
- `验收标准`：
  - `npu_demo` 不再只有字符串命中
  - compile gate 失败时能直接定位是 include 缺口还是 codegen 文本缺口
  - 不允许靠测试里手写 `using cpu::Memory` 之类绕过统一 include 合同

### `S7`

- `任务类型`：`spec任务（收口子任务）`
- `阶段链路`：`spec -> 实现/重构 -> 审查（含复审） -> 合并`
- `目标`：统一回归所有 include 与 `npu_demo` 相关 gate，形成最终绿灯基线。
- `回归命令`：

```bash
pytest -q test/include/api/test_core.py test/include/api/test_memory.py test/include/api/test_dma.py test/include/api/test_nn.py
pytest -q test/include/npu_demo/test_kernel_context.py
pytest -q test/dsl/test_gen_kernel.py -k 'npu_demo'
```

- `需要复核的反证点`：
  - generated source 里不出现 `.view<`、`load<`、`store<`、`launch`、`barrier`
  - `npu_demo` 实现不偏离 `include/api` 已冻结接口
  - `include/api` 不是实现容器，而是明确、可检查的公共声明层
- `验收标准`：
  - 全部 gate 通过
  - spec / 实现 / 测试三层一致
  - 本计划进入 `待架构师验收`

## 管理员分发建议

- 第一优先级：`S1`
  - 先冻结统一 include 边界，否则后续 `Memory.h/Dma.h/Nn.h` 容易边写边变。
- 第二优先级：`S2 + S3`
  - 先把公共类型与公共接口边界冻结干净。
- 第三优先级：`S4 + S5`
  - `npu_demo` 后端实现与 `npu_demo.h` 收口后，`gen_kernel` compile smoke 才有意义。
- 最后执行：`S6 -> S7`
  - 先补 compile gate，再统一收口。
