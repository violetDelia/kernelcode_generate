# memory_space_template_parameter_green_plan.md

## 进度

> 说明（2026-04-07）：用户要求“从 0 开始”重新推进与验收，因此此处新增 **重跑进度表** 并将其置为主表。  
> 注意：重跑进度表仅用于重新组织分发与验收，不代表回滚已合入的实现；如确需回滚，请另行明确。

### 重跑进度（从 0 开始）

| 编号 | 依赖 | worktree | 记录文件 | 进度 |
| --- | --- | --- | --- | --- |
| `S1` | `无` | `wt-20260407-memory-space-template-r0-s1` | `20260407-memory-space-template-r0-s1.md` | `未开始` |
| `S2` | `S1` | `wt-20260407-memory-space-template-r0-s2` | `20260407-memory-space-template-r0-s2.md` | `未开始` |
| `S3` | `S2` | `wt-20260407-memory-space-template-r0-s3` | `20260407-memory-space-template-r0-s3.md` | `未开始` |
| `S4` | `S3` | `wt-20260407-memory-space-template-r0-s4` | `20260407-memory-space-template-r0-s4.md` | `未开始` |
| `S5` | `S4` | `wt-20260407-memory-space-template-r0-s5` | `20260407-memory-space-template-r0-s5.md` | `未开始` |

### 历史进度（2026-04-06 已执行）

| 编号 | 依赖 | worktree | 记录文件 | 进度 |
| --- | --- | --- | --- | --- |
| `S1` | `无` | `wt-20260406-memory-space-template-s1` | `20260406-memory-space-template-s1.md` | `已合并收口（T-20260406-2acf11de；merge_commit=c026af2）。` |
| `S2` | `S1` | `wt-20260406-memory-space-template-s2` | `20260406-memory-space-template-s2.md` | `已合并收口（merge_commit=3b7d210；T-20260406-cc035d03，李白；push(main)=0）。` |
| `S3` | `S2` | `wt-20260406-memory-space-template-s3` | `20260406-memory-space-template-s3.md` | `已合并收口（merge_commit=cc9f0bd；T-20260406-b6247e80，李白；push(main)=0）。` |
| `S4` | `S3` | `wt-20260406-memory-space-template-s4` | `20260406-memory-space-template-s4.md` | `已合并收口（merge_commit=6620f46；T-20260406-b7bec449，李白；push(main)=0）。` |
| `S5` | `S4` | `wt-20260406-memory-space-template-s5` | `20260406-memory-space-template-s5.md` | `已合并收口（merge_commit=5ff9871；稳定性复跑记录见 agents/codex-multi-agents/log/task_records/2026/15/20260407-memory-space-template-accept-fix.md）。` |

## 双架构师最终验收摘要（2026-04-07）

- 结论：`通过（可归档 done_plan）`。
- 目标：`Memory<Space, T>` 公开口径与 `include/api + include/cpu + include/npu_demo + dsl/emit_c + dsl/gen_kernel` 合同一致性已收口。
- 边界：未扩展 `stream`/`pass`/`runtime` 新语义；保持在 memory-space 模板化与 emit/gen 合同范围内。
- 依赖门禁与验证命令：按计划清单复核，稳定证据见 [`agents/codex-multi-agents/log/task_records/2026/15/20260407-memory-space-template-accept-fix.md`](agents/codex-multi-agents/log/task_records/2026/15/20260407-memory-space-template-accept-fix.md)。
- 关键稳定性：`include/api` 组合 pytest 连续 `3` 次 `exit=0`；`expectation/dsl/emit_c/npu_demo/add.py` 连续 `3` 次 `exit=0`，`CASE-1~4` 均命中 `Memory<GM, int32_t>` 与 `npu_demo::add` 文本。
- 失败短语与不可改文件：无新增阻断短语残留；沿用仓库 `[immutable]/[immutable-file]` 默认规则，无额外豁免。
- 评审人：`大闸蟹`、`守护最好的爱莉希雅`。

## 功能说明

- 本计划用于把 `Memory` 从“运行时 space 成员”收口为“模板参数含 space”的公开合同，目标口径为 `Memory<GM, float>`（或等价全限定写法）。
- 本计划的每个阶段任务均按“收口任务（规格+实现+测试）”推进；禁止把阶段任务拆成仅 `spec` 的独立任务来交付完成态。
- 本计划不扩 `stream` 入参，不新增调度/执行语义；仅处理 `Memory` 类型系统与 DSL/codegen 到 include 的合同一致性。
- 计划任务采用“规格+实现+测试”一体化收口，不再拆成独立 `spec` 单任务。

## 六项结论摘要（V1 草案）

- `目标`：将公开口径统一为 `Memory<Space, T>`，并保证 `dsl/emit_c + dsl/gen_kernel + include(api/cpu/npu_demo)` 在纳入合同路径下不再生成/依赖 `Memory<T>` 旧签名。
- `边界`：仅收口 `spec/include/* + spec/dsl/*` 的 `Memory` 类型合同与桥接规则；不扩 `operation` 新语义、不扩 `pass` 新能力、不扩 `runtime stream`。
- `依赖门禁`：
  1. 交付前显式冻结七份 spec：`spec/include/api/Memory.md`、`spec/include/cpu/cpu.md`、`spec/include/api/Nn.md`、`spec/include/api/Dma.md`、`spec/include/npu_demo/npu_demo.md`、`spec/dsl/emit_c.md`、`spec/dsl/gen_kernel.md`。
  2. 目录级 gate 不退化：`test/include/api`、`test/include/cpu`、`test/include/npu_demo`、`test/dsl` 必须按目录/文件全量执行，不允许只跑单测替代。
  3. 目标文本 gate：纳入合同路径的生成源码中，`Memory<T>` 旧签名不得作为完成态；必须出现 `Memory<GM|SM|LM|TSM|TLM, T>` 形态（或等价全限定枚举形态）。
  4. `S2` 启动硬门禁：必须先显式冻结 `include/api/Memory|Nn|Dma` 与 `include/npu_demo/npu_demo` 对应 spec 合同，禁止“先改实现后补 spec”。
- `验证命令`（固定顺序，任一失败即阻断）：
  1. `pytest -q test/include/api/test_memory.py test/include/api/test_nn.py test/include/api/test_dma.py`
  2. `pytest -q test/include/cpu/test_memory.py test/include/cpu/test_nn.py`
  3. `pytest -q test/include/npu_demo/test_kernel_context.py`
  4. `pytest -q test/dsl/test_emit_c.py`
  5. `pytest -q test/dsl/test_gen_kernel.py`
  6. `find expectation/dsl/emit_c/npu_demo -type f ! -path '*/__pycache__/*' | sort | while read -r f; do PYTHONPATH=. python "$f"; done`
- `失败短语`：`legacy Memory<T> signature`、`space-only-runtime-arg`、`fallback to Memory<T>` 不得作为纳入合同路径完成态；仅允许出现在显式负例或未纳入合同入口。
- `不可改文件`：沿用仓库 `[immutable]` / `[immutable-file]` 默认规则，无额外豁免。

## 范围与非目标

### 范围

- `spec`
  - [`spec/include/api/Memory.md`](spec/include/api/Memory.md)
  - [`spec/include/cpu/cpu.md`](spec/include/cpu/cpu.md)
  - [`spec/include/api/Nn.md`](spec/include/api/Nn.md)
  - [`spec/include/api/Dma.md`](spec/include/api/Dma.md)
  - [`spec/include/npu_demo/npu_demo.md`](spec/include/npu_demo/npu_demo.md)
  - [`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)
  - [`spec/dsl/gen_kernel.md`](spec/dsl/gen_kernel.md)
- `功能实现（下游对齐范围）`
  - [`include/api/Memory.h`](include/api/Memory.h)
  - [`include/npu_demo/Memory.h`](include/npu_demo/Memory.h)
  - [`include/cpu/Memory.h`](include/cpu/Memory.h)
  - [`include/api/Nn.h`](include/api/Nn.h)
  - [`include/api/Dma.h`](include/api/Dma.h)
  - [`include/npu_demo/Nn.h`](include/npu_demo/Nn.h)
  - [`include/npu_demo/Dma.h`](include/npu_demo/Dma.h)
  - [`include/npu_demo/Arch.h`](include/npu_demo/Arch.h)
  - [`kernel_gen/dsl/emit_c.py`](kernel_gen/dsl/emit_c.py)
  - [`kernel_gen/dsl/gen_kernel.py`](kernel_gen/dsl/gen_kernel.py)
- `test/expectation（下游验收范围）`
  - [`test/include/api/test_memory.py`](test/include/api/test_memory.py)
  - [`test/include/api/test_nn.py`](test/include/api/test_nn.py)
  - [`test/include/api/test_dma.py`](test/include/api/test_dma.py)
  - [`test/include/cpu/test_memory.py`](test/include/cpu/test_memory.py)
  - [`test/include/cpu/test_nn.py`](test/include/cpu/test_nn.py)
  - [`test/include/npu_demo/test_kernel_context.py`](test/include/npu_demo/test_kernel_context.py)
  - [`test/dsl/test_emit_c.py`](test/dsl/test_emit_c.py)
  - [`test/dsl/test_gen_kernel.py`](test/dsl/test_gen_kernel.py)
  - [`expectation/dsl/emit_c/npu_demo/add.py`](expectation/dsl/emit_c/npu_demo/add.py)

### 非目标

- 不新增/修改 `stream` 参数、异步提交、事件同步或 runtime 调度策略。
- 不新增 `operation` / `dialect` / `pass` 能力，仅允许做“现有 space 语义到模板参数”的桥接。
- 不通过缩窄 expectation 或删除断言来“变绿”。
- 不把实现细节写成“允许自行决定”的空口径；必须给出可机械判定的接口文本。

## 文档信息

- 创建者：`守护最好的爱莉希雅`
- 最后一次更改：`守护最好的爱莉希雅`
- `文档`：[`ARCHITECTURE/plan/memory_space_template_parameter_green_plan.md`](ARCHITECTURE/plan/memory_space_template_parameter_green_plan.md)
- `spec`：
  - [`spec/include/api/Memory.md`](spec/include/api/Memory.md)
  - [`spec/include/cpu/cpu.md`](spec/include/cpu/cpu.md)
  - [`spec/include/api/Nn.md`](spec/include/api/Nn.md)
  - [`spec/include/api/Dma.md`](spec/include/api/Dma.md)
  - [`spec/include/npu_demo/npu_demo.md`](spec/include/npu_demo/npu_demo.md)
  - [`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)
  - [`spec/dsl/gen_kernel.md`](spec/dsl/gen_kernel.md)
- `功能实现`：
  - [`include/api/Memory.h`](include/api/Memory.h)
  - [`include/api/Nn.h`](include/api/Nn.h)
  - [`include/api/Dma.h`](include/api/Dma.h)
  - [`include/cpu/Memory.h`](include/cpu/Memory.h)
  - [`include/cpu/Nn.h`](include/cpu/Nn.h)
  - [`include/npu_demo/Memory.h`](include/npu_demo/Memory.h)
  - [`include/npu_demo/Nn.h`](include/npu_demo/Nn.h)
  - [`include/npu_demo/Dma.h`](include/npu_demo/Dma.h)
  - [`include/npu_demo/Arch.h`](include/npu_demo/Arch.h)
  - [`kernel_gen/dsl/emit_c.py`](kernel_gen/dsl/emit_c.py)
  - [`kernel_gen/dsl/gen_kernel.py`](kernel_gen/dsl/gen_kernel.py)
- `test`：
  - [`test/include/api/test_memory.py`](test/include/api/test_memory.py)
  - [`test/include/cpu/test_memory.py`](test/include/cpu/test_memory.py)
  - [`test/include/npu_demo/test_kernel_context.py`](test/include/npu_demo/test_kernel_context.py)
  - [`test/dsl/test_emit_c.py`](test/dsl/test_emit_c.py)
  - [`test/dsl/test_gen_kernel.py`](test/dsl/test_gen_kernel.py)

## 当前问题快照

- 公开签名当前仍以 `Memory<T>` 为主，`MemorySpace` 仅作为运行时构造参数/成员参与，导致“类型系统不携带 space”。
- `dsl/emit_c.py` 与 `dsl/gen_kernel.py` 当前把 `nn.memory` 映射到 `Memory<T>`，space 通过构造参数或额外表达式传递，不能从函数签名直接判定 space。
- `include/api` 与 `include/npu_demo` 的 `Nn/Dma/Arch` 接口多处依赖 `Memory<T>`，跨层桥接时容易出现“类型不含 space + 运行时 space 漂移”的双轨语义。
- `target=npu_demo` 动态内存接口当前是 `ctx.get_dynamic_memory<T>(MemorySpace::TSM/TLM)`，未与“space 进入模板参数”形成统一口径。

## include 接口改造判定规则（新增）

- `必改范围`：凡是公开签名中出现 `Memory<T>` 的 include 接口（参数、返回值、局部公开示例）都必须同步改为 `Memory<Space, T>` 口径。
- `本计划纳入的 include 文件`：
  - [`include/api/Memory.h`](include/api/Memory.h)
  - [`include/api/Nn.h`](include/api/Nn.h)
  - [`include/api/Dma.h`](include/api/Dma.h)
  - [`include/cpu/Memory.h`](include/cpu/Memory.h)
  - [`include/cpu/Nn.h`](include/cpu/Nn.h)
  - [`include/npu_demo/Memory.h`](include/npu_demo/Memory.h)
  - [`include/npu_demo/Nn.h`](include/npu_demo/Nn.h)
  - [`include/npu_demo/Dma.h`](include/npu_demo/Dma.h)
  - [`include/npu_demo/Arch.h`](include/npu_demo/Arch.h)（仅动态内存模板入口相关）
- `非必改范围`：不直接暴露 `Memory` 类型签名的接口可保持不变（例如仅 `launch/barrier` 声明的头文件），除非为保持编译通过必须做最小同步。
- `门禁要求`：S2 交付时必须证明“纳入文件中不再保留 `Memory<T>` 公开签名”，不得通过局部绕过或仅改单 target 达成。

## 关键定义与接口（冻结目标）

### 定义 A：Memory 主类型模板

- 公开主类型收口为：
  - `template <MemorySpace Space, typename T> class Memory;`
- 允许提供简写常量以支持 `Memory<GM, float>` 文本（或使用 `Memory<MemorySpace::GM, float>` 全限定写法）。
- `space()` 必须返回模板常量 `Space`；不得再把“可变 runtime space 成员”作为主合同。

### 定义 B：算子/访存接口的 space 形参策略

- `NN` 同空间算子（算术）显式收口为同一 `Space` 模板参数：
  - `Status add(const Memory<Space, T>& lhs, const Memory<Space, T>& rhs, Memory<Space, T>& out);`
  - `Status sub(const Memory<Space, T>& lhs, const Memory<Space, T>& rhs, Memory<Space, T>& out);`
  - `Status mul(const Memory<Space, T>& lhs, const Memory<Space, T>& rhs, Memory<Space, T>& out);`
  - `Status truediv(const Memory<Space, T>& lhs, const Memory<Space, T>& rhs, Memory<Space, T>& out);`
- `NN` 同空间比较算子保持输入/输出同 `Space`，只允许类型维度变化：
  - `Status eq(const Memory<Space, T>& lhs, const Memory<Space, T>& rhs, Memory<Space, PredT>& out);`
  - `Status ne/lt/le/gt/ge(...)` 同上口径。
- `NN` broadcast P0 先收口同空间模板（不在本计划扩跨空间 broadcast 语义）：
  - `Status broadcast(const Memory<Space, T>& input, Memory<Space, T>& out);`
- `DMA` 接口区分“同空间视图”与“跨空间搬运”：
  - `Memory<Space, T> view(const Memory<Space, T>& source, ...);`
  - `Status slice(Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, ...);`
  - `Status deslice(const Memory<SourceSpace, T>& source, Memory<TargetSpace, T>& target, ...);`
- `DMA` 的 `Vector` 与标量重载都遵循同一模板规则，不允许“一个重载是 `Memory<Space, T>`，另一个重载回退 `Memory<T>`”。

### 定义 C：DSL/IR 到 C++ 的 space 映射

- `#nn.space<global/shared/local/tsm/tlm>` 到模板参数映射固定为：
  - `global -> GM`
  - `shared -> SM`
  - `local -> LM`
  - `tsm -> TSM`
  - `tlm -> TLM`
- `emit_c/gen_kernel` 纳入合同路径的函数签名与局部 `Memory` 声明必须直接生成 `Memory<Space, T>` 形态，不允许只在构造实参写 `MemorySpace::...`。

### 定义 D：npu_demo 动态片上内存入口

- `KernelContext` 动态内存接口需收口为模板携带 space 的稳定口径（说明性示例）：
  - `template <MemorySpace Space, typename T> Memory<Space, T> get_dynamic_memory() const;`
- P0 只纳入 `TSM/TLM`，`SM/LM` 仍按现有报错契约处理；不得因模板化而扩大可用空间集合。

## 目标源码示例（冻结）

### 示例 1：公开签名（include 层）

```cpp
Status add(
    const Memory<GM, float>& lhs,
    const Memory<GM, float>& rhs,
    Memory<GM, float>& out);
```

### 示例 2：npu_demo 动态内存入口

```cpp
Memory<TSM, float> tsm = ctx.get_dynamic_memory<TSM, float>();
Memory<TLM, float> tlm = ctx.get_dynamic_memory<TLM, float>();
```

### 示例 3：gen_kernel(target="npu_demo") 关键片段

```cpp
static void add_body(
    npu_demo::KernelContext& ctx,
    const Memory<GM, float>& lhs,
    const Memory<GM, float>& rhs,
    Memory<GM, float>& out) {
    Memory<TSM, float> tsm = ctx.get_dynamic_memory<TSM, float>();
}
```

## 计划任务

### `S1`

- `任务类型`：`收口任务（规格+实现+测试）`
- `目标`：完成 `Memory<Space, T>` 主类型改造，并提供 `Memory<GM, T>` 与 `Memory<MemorySpace::GM, T>` 等价口径。
- `边界`：只收口 Memory 类型本身；不改 `Nn/Dma/Arch` 算子语义。
- `可改文件`：
  - [`spec/include/api/Memory.md`](spec/include/api/Memory.md)
  - [`include/api/Memory.h`](include/api/Memory.h)
  - [`include/npu_demo/Memory.h`](include/npu_demo/Memory.h)
  - [`include/cpu/Memory.h`](include/cpu/Memory.h)
- `示例代码（目标文本）`：
```cpp
Memory<GM, float> x(data, shape, stride, 2, MemoryFormat::Norm);
Memory<MemorySpace::GM, float> y(data, shape, stride, 2, MemoryFormat::Norm);
```
- `预期输出（机械判定）`：
```text
命中: Memory<GM, float>
命中: Memory<MemorySpace::GM, float>
禁止: class Memory<T>
```
- `验证函数`：
  - `test/include/api/test_memory.py::test_memory_space_template_contract`
  - `test/include/cpu/test_memory.py::test_cpu_memory_space_template_contract`
- `验证命令`：
  - `pytest -q test/include/api/test_memory.py -k "space_template_contract"`
  - `pytest -q test/include/cpu/test_memory.py -k "space_template_contract"`
- `验收标准`：
  - `Memory<T>` 不再是主合同入口。
  - `space()` 返回模板参数对应空间，不再依赖可变成员。
  - 示例文本可机械命中 `Memory<GM, float>`。

### `S2`

- `任务类型`：`收口任务（规格+实现+测试）`
- `目标`：完成 `Nn/Dma/Arch` 对 `Memory<Space, T>` 的接口对齐（同空间算子同 `Space`，DMA 可跨 `SourceSpace/TargetSpace`）。
- `边界`：不新增算子；只做签名和桥接口径统一。
- `可改文件`：
  - [`spec/include/api/Nn.md`](spec/include/api/Nn.md)
  - [`spec/include/api/Dma.md`](spec/include/api/Dma.md)
  - [`spec/include/cpu/cpu.md`](spec/include/cpu/cpu.md)
  - [`spec/include/npu_demo/npu_demo.md`](spec/include/npu_demo/npu_demo.md)
  - [`include/api/Nn.h`](include/api/Nn.h)
  - [`include/api/Dma.h`](include/api/Dma.h)
  - [`include/cpu/Nn.h`](include/cpu/Nn.h)
  - [`include/npu_demo/Nn.h`](include/npu_demo/Nn.h)
  - [`include/npu_demo/Dma.h`](include/npu_demo/Dma.h)
  - [`include/npu_demo/Arch.h`](include/npu_demo/Arch.h)
- `示例代码（目标文本）`：
```cpp
Status st = add(lhs_gm, rhs_gm, out_gm);  // 均为 Memory<GM, float>
Status st2 = sub(lhs_gm, rhs_gm, out_gm);
Status st3 = mul(lhs_gm, rhs_gm, out_gm);
Status st4 = eq(lhs_gm, rhs_gm, pred_gm);  // pred_gm: Memory<GM, bool>
Status st5 = broadcast(in_gm, out_gm);
Memory<GM, float> v = view(src_gm, offset, size, stride);
Status s2 = slice(tile_lm, src_gm, offset, size, stride);  // Memory<LM, float> <- Memory<GM, float>
Status s3 = deslice(tile_lm, dst_gm, offset, size, stride);
Memory<TSM, float> tsm = ctx.get_dynamic_memory<TSM, float>();
```
- `预期输出（机械判定）`：
```text
命中: Status add(const Memory<Space, T>& lhs, const Memory<Space, T>& rhs, Memory<Space, T>& out)
命中: Status sub(const Memory<Space, T>& lhs, const Memory<Space, T>& rhs, Memory<Space, T>& out)
命中: Status mul(const Memory<Space, T>& lhs, const Memory<Space, T>& rhs, Memory<Space, T>& out)
命中: Status truediv(const Memory<Space, T>& lhs, const Memory<Space, T>& rhs, Memory<Space, T>& out)
命中: Status eq(const Memory<Space, T>& lhs, const Memory<Space, T>& rhs, Memory<Space, PredT>& out)
命中: Status broadcast(const Memory<Space, T>& input, Memory<Space, T>& out)
命中: Memory<Space, T> view(const Memory<Space, T>& source, ...)
命中: Status slice(Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, ...)
命中: Status deslice(const Memory<SourceSpace, T>& source, Memory<TargetSpace, T>& target, ...)
命中: void add(const Memory<Space, T>& lhs, const Memory<Space, T>& rhs, Memory<Space, T>& out)  // cpu::add
命中: get_dynamic_memory<TSM, float>()
```
- `验证函数`：
  - `test/include/api/test_nn.py::test_nn_add_requires_same_space_template`
  - `test/include/api/test_nn.py::test_nn_compare_ops_keep_same_space_template`
  - `test/include/api/test_nn.py::test_nn_broadcast_keeps_space_template`
  - `test/include/api/test_dma.py::test_dma_slice_supports_cross_space_templates`
  - `test/include/api/test_dma.py::test_dma_view_returns_same_space_template`
  - `test/include/api/test_dma.py::test_dma_deslice_supports_cross_space_templates`
  - `test/include/npu_demo/test_kernel_context.py::test_get_dynamic_memory_template_space_contract`
- `验证命令`：
  - `pytest -q test/include/api/test_nn.py -k "same_space_template or compare_ops_keep_same_space_template or broadcast_keeps_space_template"`
  - `pytest -q test/include/api/test_dma.py -k "cross_space_templates or view_returns_same_space_template or deslice_supports_cross_space_templates"`
  - `pytest -q test/include/npu_demo/test_kernel_context.py -k "template_space_contract"`
- `验收标准`：
  - `add/sub/mul/truediv/compare/broadcast` 文本签名统一为 `Memory<Space, T>` 口径。
  - `view` 返回值保持 `Memory<Space, T>`，`slice/deslice` 能机械区分 `SourceSpace/TargetSpace`。
  - `get_dynamic_memory` 采用模板 space 入口，且仅 `TSM/TLM` 为成功路径。
  - 纳入范围内 include 公开签名不再出现 `Memory<T>`（显式负例/未纳入合同入口除外）。

### `S3`

- `任务类型`：`收口任务（规格+实现+测试）`
- `目标`：完成 `emit_c` 的 `nn.space -> Memory<Space, T>` 发射收口，所有纳入合同路径不再生成 `Memory<T>`。
- `边界`：不扩新 op，只改现有支持子集的类型文本生成规则。
- `可改文件`：
  - [`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)
  - [`kernel_gen/dsl/emit_c.py`](kernel_gen/dsl/emit_c.py)
  - [`test/dsl/test_emit_c.py`](test/dsl/test_emit_c.py)
- `示例代码（目标文本）`：
```cpp
Memory<GM, int32_t> v0(v0_data, v0_shape, v0_stride, 2, MemoryFormat::Norm);
cpu::add(arg1, arg2, arg0);
```
- `预期输出（机械判定）`：
```text
命中: Memory<GM, int32_t>
命中: cpu::add(arg1, arg2, arg0);
禁止: Memory<int32_t> v0(
```
- `验证函数`：
  - `test/dsl/test_emit_c.py::test_emit_c_emits_memory_space_template_types`
  - `test/dsl/test_emit_c.py::test_emit_c_maps_nn_space_to_memory_template_arg`
- `验证命令`：
  - `pytest -q test/dsl/test_emit_c.py -k "memory_space_template or maps_nn_space"`
- `验收标准`：
  - 输出源码可机械命中 `Memory<GM|SM|LM|TSM|TLM, ...>`。
  - 纳入合同路径中 `Memory<T>` 旧文本不得出现。

### `S4`

- `任务类型`：`收口任务（规格+实现+测试）`
- `目标`：完成 `gen_kernel` 函数签名与 npu_demo body 临时内存声明的 space 模板化收口。
- `边界`：不改 pass 新能力；只收口函数级签名与局部声明文本。
- `可改文件`：
  - [`spec/dsl/gen_kernel.md`](spec/dsl/gen_kernel.md)
  - [`kernel_gen/dsl/gen_kernel.py`](kernel_gen/dsl/gen_kernel.py)
  - [`test/dsl/test_gen_kernel.py`](test/dsl/test_gen_kernel.py)
- `示例代码（目标文本）`：
```cpp
void add_direct(Memory<GM, int32_t>& arg0, const Memory<GM, int32_t>& arg1, const Memory<GM, int32_t>& arg2);
Memory<TSM, float> tsm = ctx.get_dynamic_memory<TSM, float>();
Memory<TLM, float> tlm = ctx.get_dynamic_memory<TLM, float>();
```
- `预期输出（机械判定）`：
```text
命中: void add_direct(Memory<GM, int32_t>& arg0, const Memory<GM, int32_t>& arg1, const Memory<GM, int32_t>& arg2)
命中: Memory<TSM, float> tsm = ctx.get_dynamic_memory<TSM, float>();
命中: Memory<TLM, float> tlm = ctx.get_dynamic_memory<TLM, float>();
```
- `验证函数`：
  - `test/dsl/test_gen_kernel.py::test_gen_kernel_emits_space_template_memory_signatures`
  - `test/dsl/test_gen_kernel.py::test_gen_kernel_npu_demo_dynamic_memory_uses_template_space`
- `验证命令`：
  - `pytest -q test/dsl/test_gen_kernel.py -k "space_template_memory_signatures or dynamic_memory_uses_template_space"`
- `验收标准`：
  - CPU 与 npu_demo 路径都生成 `Memory<Space, T>`。
  - npu_demo body 的 `tsm/tlm` 声明采用模板 space 入口。

### `S5`

- `任务类型`：`收口任务（expectation+集成验收）`
- `目标`：完成 `expectation/dsl/emit_c/npu_demo/add.py` 与目录 gate 的口径对齐，明确交付结果文本。
- `边界`：不放宽失败短语，不允许 fallback 到 `Memory<T>` 旧签名或 `cpu` 隐式回退。
- `可改文件`：
  - [`expectation/dsl/emit_c/npu_demo/add.py`](expectation/dsl/emit_c/npu_demo/add.py)
  - （按需）[`expectation/dsl/emit_c/npu_demo/*`](expectation/dsl/emit_c/npu_demo)
- `示例代码（目标文本）`：
```python
assert "Memory<GM, float>" in source
assert "Memory<TSM, float>" in source
assert "fallback to cpu" not in source
```
- `预期输出（机械判定）`：
```text
命中: Memory<GM, float>
命中: Memory<TSM, float>
禁止: Unsupported call expression（纳入合同路径）
禁止: Unsupported nn op（纳入合同路径）
禁止: cpu::add(（纳入合同路径）
禁止: fallback to cpu（纳入合同路径）
禁止: target!=npu_demo（纳入合同路径）
```
- `验证函数`：
  - `expectation/dsl/emit_c/npu_demo/add.py::case_static_add`
  - `expectation/dsl/emit_c/npu_demo/add.py::case_dynamic_add`
  - `expectation/dsl/emit_c/npu_demo/add.py::case_int_add`
  - `expectation/dsl/emit_c/npu_demo/add.py::case_symbol_add`
- `验证命令`（固定顺序，任一失败即阻断）：
  1. `pytest -q test/include/api/test_memory.py test/include/api/test_nn.py test/include/api/test_dma.py`
  2. `pytest -q test/include/cpu/test_memory.py test/include/cpu/test_nn.py`
  3. `pytest -q test/include/npu_demo/test_kernel_context.py`
  4. `pytest -q test/dsl/test_emit_c.py`
  5. `pytest -q test/dsl/test_gen_kernel.py`
  6. `PYTHONPATH=. python expectation/dsl/emit_c/npu_demo/add.py`
  7. `find expectation/dsl/emit_c/npu_demo -type f ! -path '*/__pycache__/*' | sort | while read -r f; do PYTHONPATH=. python "$f"; done`
- `验收标准`：
  - `add.py` 四类 case 输出文本都能命中 `Memory<Space, T>` 口径。
  - `Unsupported call expression` / `Unsupported nn op` / `fallback to cpu` 仅允许出现在未纳入合同入口或显式负例。

## 交付前互审要求

- 本计划由 `守护最好的爱莉希雅` 起草后，必须先提交 `大闸蟹` 评审通过，再交付管理员推进。
- 互审摘要必须至少覆盖：`目标`、`边界`、`依赖门禁`、`验证命令`、`失败短语`、`不可改文件` 六项。
- 若出现“模板参数 vs 运行时参数”双轨口径，评审默认不通过，需先收敛后再交付。

## 架构师互审结论（2026-04-06）

- `评审人`：`大闸蟹`
- `结论`：`通过（可推进，附小修建议）`
- `六项摘要`：
  1. `目标`：通过（S2 include 多接口与机械判定、add expectation 四类链路目标清晰）。
  2. `边界`：通过（限定 include+dsl/gen_kernel+emit_c 合同，expectation 固定 `target=npu_demo` 且不 fallback）。
  3. `依赖门禁`：通过（已补 `S2` 前 spec 冻结硬门禁）。
  4. `验证命令`：通过（计划 gate 完整；已固定 `PYTHONPATH=. python expectation/dsl/emit_c/npu_demo/add.py`）。
  5. `失败短语`：通过（已明确 `cpu::add(` / `fallback to cpu` / `target!=npu_demo` 不得作为纳入合同路径完成态）。
  6. `不可改文件`：通过（沿用仓库 immutable 默认规则，无额外豁免）。
