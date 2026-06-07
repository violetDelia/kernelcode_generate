# Context-first Kernel / Cost Shared Source Plan Draft 26

## 文档信息

- 计划用途：规划 `target=npu_demo` 的 generated source 与 include API 从旧无上下文 helper 调用切换为 `op<...>(ctx, args...)` / `op(ctx, args...)`，并把 launch callee/name 固定到模板参数中，形成 `launch<block, thread, subthread, shared_memory_size, name>(ctx, args...)` 形态；host 入口函数签名不接收 `ctx`，而是在入口函数内部创建 context 并传入 kernel launch。
- 当前状态：Draft 26；Draft 13 / 17 strict review 与守护最终检验曾通过，但已被后续用户纠偏 supersede；Draft 18 strict review 曾通过但守护最终检验不通过；Draft 19 strict review 曾通过但被 Draft 20 scope 扩展 supersede；Draft 20 strict review 与守护最终检验曾通过，但已被 2026-06-06 用户关于 launch callee/name 的新确认 supersede；Draft 21 subagent strict review 与守护最终检验曾通过，但已被 2026-06-06 用户关于 `KernelContext` 不要 runtime member 函数的纠偏 supersede；Draft 22 subagent strict review 与守护最终检验曾通过，但已被 2026-06-06 用户关于 cost / kernel 经 `include/api` 宏分发的纠偏 supersede；Draft 23 的“直接删除全部 cost 旧链路”方向已被用户进一步澄清 supersede；Draft 24 的“删除清单仍待确认”状态已被 2026-06-06 用户关于目标宏边界、`LaunchKernelCostFuncPass` 删除和 `dsl_cost_run` 保留的确认 supersede；Draft 25 strict review 复审与守护最终检验曾通过，但已被 2026-06-06 用户关于 host 入口函数不接收 `ctx`、入口函数内部创建 `ctx` 后传给 kernel 的确认 supersede。用户新确认 `launch<name>(ctx, args...)`：name 在模板参数中，函数实参顺序为 `ctx` 在前、`args...` 在后；host 入口函数签名没有 `ctx`，只接收业务参数，在入口函数体内创建 `npu_demo::KernelContext ctx;`，再调用 `npu_demo::launch<..., body>(ctx, args...)`；`npu_demo::KernelContext& ctx` 仍作为 launch/body/helper context 对象传递，但 `KernelContext` 不公开 runtime member API；Arch 查询、同步与动态内存继续走 free helper；emitc / generated source 外层调用的是 `include/api` public helper 函数，实际 kernel / cost 实现由 API 层根据编译期 target 宏分发，宏只用于选择本次编译的 target 实现，避免一次编译所有 target；cost 与 kernel 可视为同一 API 在不同 context 类型上的模板实例；`include/npu_demo/kernel` 承载 kernel context 实现，`include/npu_demo/cost` 承载 cost context 实现；generated source 主链路不得直接调用 `npu_demo::cost::*` / `cost::CostKind` / `tuner.cost` / `_cost_*`。`LaunchKernelCostFuncPass` 相关链路直接删除；`dsl_cost_run` 保留，后续另立计划改成“不运行 kernel，只运行 cost 的 kernel，并返回结果”。Draft 26 已按该口径更新计划，strict review 与守护最终检验均已通过；允许管理员后续按流程创建唯一计划级 `execute`：`context-first-kernel-cost-shared-code`，当前未创建 execute。
- 用户确认来源：
  - 2026-06-05 用户确认：cost 模式和 kernel 模式使用同一份 API 接口，只是传入的 context 不同。
  - 2026-06-05 用户确认：`params` 仍是 kernel 参数，不放入 context；context 不携带 target，不同 target 使用不同 context 类型。
  - 2026-06-05 用户确认：cost context 会累加不同后端自行定义的 cost 值；best params 每个 kernel 可不同，但当前不启用 tuner param。
  - 2026-06-05 用户确认：当前不接入 `tuner.param` / `def params`，只要求 kernel 与 cost 代码相同。
  - 2026-06-05 用户确认：不再生成臃肿的 cost func generate sibling，kernel 与 cost 代码是同一份；launch 时传入不同 context。
  - 2026-06-05 用户确认：当前编译尚不生成 host cost 计算，因此本轮只要求 `emit_c` / generated source 添加 context。
  - 2026-06-05 用户确认：不要旧的兼容。
  - 2026-06-05 用户指令：当前角色是架构师，不改代码，只维护 `expectation`，按流程写出计划书。
  - 2026-06-05 用户澄清：emit_c 层只需要把 `ctx` 添加到生成 API 的最前面，同时注意命名空间。
  - 2026-06-05 用户纠偏：预期是在之前的 expectation 基础上添加 `ctx`，不是新增聚合 expectation。
  - 2026-06-05 用户确认：`thread_id()` 这一类 Arch 查询不需要变。
  - 2026-06-05 用户授权：架构师可以修改带 `[immutable-file]` 标记的 expectation。
  - 2026-06-05 用户纠偏：`std::initializer_list<long long> stride` API 应该是 `Vector`；本计划据此将目标 DMA helper layout 参数统一收为 `Vector`。
  - 2026-06-05 用户追问并确认方向：`expectation/dsl/emit_c` 里的 npu_demo emit_c 叶子合同也应更新成 `ctx` 版本；架构口径为 public helper 调用在旧生成形态基础上前置 `ctx`，Arch free helper 与 standalone cost expectation 不纳入本轮 ctx 化。
  - 2026-06-06 用户纠偏：function 输入仍是 `Vector`，生成调用处应传 `{val, val1, val2}` 这样的 braced-init，因为 `Vector` 可以这样构造；因此本计划只调整 generated source / expectation 的 layout 实参文本，不把 public helper API 改成 `std::initializer_list<long long>`。
  - 2026-06-06 用户确认：launch 调用应为 `launch<name>(ctx, args...)` 口径，name 在模板参数中，函数实参中 `ctx` 在前、`args...` 在后；不得把 name 作为普通实参写成 `launch(name, ctx, ...)`、`launch(ctx, name, ...)`、`launch<...>(ctx, name, ...)` 或 `launch<...>(name, ctx, ...)`。
  - 2026-06-06 用户纠偏：`arch_launch_body<npu_demo::KernelContext>` 不要模板；本 Draft 据此将 npu_demo generated / emit_c body 收为 `npu_demo::KernelContext& ctx` 的普通函数，dtype 模板只保留业务 dtype 参数，launch 模板里的 name 使用裸 body 名或 dtype specialization，不再使用 context specialization。
  - 2026-06-06 用户纠偏：`KernelContext` 不要 `block_id()`、`block_num()`、`thread_id()`、`thread_num()`、`subthread_id()`、`subthread_num()`、`barrier(...)`、`get_dynamic_memory<...>()` 这类 runtime member 函数；本 Draft 据此删除 include/api 全局 `KernelContext` 与 `npu_demo::KernelContext` 的 public runtime member API，仅保留 context 对象用于 `launch(ctx, args...)`、body 首参和 DMA / Kernel helper 首参。
  - 2026-06-06 用户纠偏（已被下一条更正 supersede）：曾提出 `cost::CostKind` / cost 相关旧 API 可以删除；Draft 23 未完成收敛，不能作为下发依据。
  - 2026-06-06 用户更正：外层 / emitc 生成代码调用的是 `include/api` 函数；API 层根据宏控制实际调用的 kernel / cost 实现。例如目标宏选择 npu_demo 时，API 分发到 npu_demo kernel 与 npu_demo cost 实现；cost 与 kernel 相当于 API context 的模板实例，`include/npu_demo/cost` 实现 cost context 侧，`include/npu_demo/kernel` 实现 kernel context 侧。
  - 2026-06-06 用户确认：目标宏与编译相关，作用是防止一次把所有 target 的实现都编译进去；选了哪个 target，就只编译哪个 target 的实现。
  - 2026-06-06 用户确认：`LaunchKernelCostFuncPass` 相关链路直接删除。
  - 2026-06-06 用户确认：`dsl_cost_run` 保留，但后续再修改；目标语义是不运行 kernel，只运行 cost 的 kernel，并返回结果。
  - 2026-06-06 用户确认：生成 func 时，host 入口函数签名没有 `ctx`；在 host 入口函数内部创建 `ctx`，再将其传入 kernel / launch。
- 目标 `spec`：
  - `spec/include/api/Dma.md`
  - `spec/include/api/Kernel.md`
  - `spec/include/api/Arch.md`
  - `spec/include/npu_demo/npu_demo.md`
  - `spec/dsl/gen_kernel/gen_kernel.md`
  - `spec/dsl/gen_kernel/kernel_emitter.md`
  - `spec/dsl/gen_kernel/emit.md`
  - `spec/dsl/gen_kernel/emit/npu_demo.md`
  - `spec/dsl/gen_kernel/emit/npu_demo/include.md`
  - `spec/pass/tuning/launch_kernel_cost_func.md`（下线 / 删除 `LaunchKernelCostFuncPass` 公开 pass 的合同真源）
  - `spec/tools/dsl_cost_run.md`（只记录保留边界与后续语义方向；本计划不把其语义切到最终 cost-kernel-only 形态）
- 非目标公开链路：`spec/tools/dsl_run.md`、`dsl_cost_run` 工具入口参数签名、非 `LaunchKernelCostFuncPass` 的 pass / registry / 工具入口本轮保留公开 API，不做删除或参数改名；`dsl_cost_run` 后续另立计划改为“不运行 kernel，只运行 cost 的 kernel，并返回结果”；若执行中发现必须新增、删除或重命名公开宏、工具参数、稳定错误语义或除 `LaunchKernelCostFuncPass` 外的公开入口，必须停止并回到用户确认。
- 目标 `API` 全量索引：
  - `enum class BarrierVisibility { TSM, TLM }`
  - `enum class BarrierScope { BLOCK, THREAD, SUBTHREAD, GLOBAL }`
  - `template <long long block, long long thread, long long subthread, long long shared_memory_size, auto name, typename Context, typename... Args> Status launch(Context& ctx, Args&&... args)`
  - `template <long long block, long long thread, long long subthread, long long shared_memory_size, auto name, typename Context, typename... Args> Status npu_demo::launch(Context& ctx, Args&&... args)`
  - `class KernelContext`（不提供 runtime 查询 / 同步 / 动态内存 public member API）
  - `class npu_demo::KernelContext`（不提供 runtime 查询 / 同步 / 动态内存 public member API）
  - `npu_demo::KernelContext::KernelContext()`
  - `npu_demo::block_id() -> S_INT`
  - `npu_demo::thread_id() -> S_INT`
  - `npu_demo::thread_num() -> S_INT`
  - `npu_demo::barrier(std::initializer_list<BarrierVisibility> visibility, BarrierScope scope) -> void`
  - `template <MemorySpace Space> npu_demo::get_dynamic_memory() -> DynamicMemoryRef<Space>`
  - `block_id() -> S_INT`
  - `thread_id() -> S_INT`
  - `thread_num() -> S_INT`
  - `template <MemorySpace Space> get_dynamic_memory() -> DynamicMemoryRef<Space>`
  - `template <MemorySpace Space> class DynamicMemoryRef`
  - include/api emitc-facing DMA helper（未限定名，generated source 正向调用面）：
    - `template <MemorySpace Space, typename T, typename Context> Memory<Space, T> alloc(Context& ctx, const Vector& shape, const Vector& stride, MemoryFormat format = MemoryFormat::Norm)`
    - `template <MemorySpace Space, typename T, typename Context> Status fill(Context& ctx, Memory<Space, T>& target, const T& value)`
    - `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, typename Context> Status slice(Context& ctx, Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`
    - `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, typename Context> Status deslice(Context& ctx, Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`
    - `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context> Status store(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& offset, const Vector& size, const Vector& stride)`
    - `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context> Status load(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& offset, const Vector& size, const Vector& stride)`
    - `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context> Status transpose(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& perm)`
    - `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context> Status broadcast(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source)`
  - include/api emitc-facing Kernel helper（未限定名，generated source 正向调用面）：
    - `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status add(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
    - `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status sub(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
    - `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status mul(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
    - `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status truediv(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
    - `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status min(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
    - `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status max(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
    - `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status eq(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
    - `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status ne(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
    - `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status lt(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
    - `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status le(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
    - `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status gt(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
    - `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status ge(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
    - `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status exp(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& input)`
    - `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status select(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, bool>& cond, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
    - `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status reduce_sum(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`
    - `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status reduce_min(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`
    - `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status reduce_max(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`
    - `template <MemorySpace LhsSpace, MemorySpace RhsSpace, MemorySpace OutSpace, typename LhsType, typename RhsType, typename OutType, typename Context> Status matmul(Context& ctx, Memory<OutSpace, OutType>& out, const Memory<LhsSpace, LhsType>& lhs, const Memory<RhsSpace, RhsType>& rhs, bool acc = false)`
    - `template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType, typename Context> Status img2col1d(Context& ctx, Memory<OutputSpace, OutType>& out, const Memory<InputSpace, InType>& input, long long k, long long s, long long d, long long p_left, long long p_right)`
    - `template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType, typename Context> Status img2col2d(Context& ctx, Memory<OutputSpace, OutType>& out, const Memory<InputSpace, InType>& input, long long kh, long long kw, long long sh, long long sw, long long dh, long long dw, long long ph, long long pw, long long pl, long long pr)`
  - `template <MemorySpace Space, typename T, typename Context> Memory<Space, T> npu_demo::alloc(Context& ctx, const Vector& shape, const Vector& stride, MemoryFormat format = MemoryFormat::Norm)`
  - `template <MemorySpace Space, typename T, typename Context> Status npu_demo::fill(Context& ctx, Memory<Space, T>& target, const T& value)`
  - `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, typename Context> Status npu_demo::slice(Context& ctx, Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`
  - `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T, typename Context> Status npu_demo::deslice(Context& ctx, Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`
  - `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context> Status npu_demo::store(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& offset, const Vector& size, const Vector& stride)`
  - `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context> Status npu_demo::load(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& offset, const Vector& size, const Vector& stride)`
  - `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context> Status npu_demo::transpose(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& perm)`
  - `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType, typename Context> Status npu_demo::broadcast(Context& ctx, Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source)`
  - `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status npu_demo::add(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
  - `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status npu_demo::sub(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
  - `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status npu_demo::mul(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
  - `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status npu_demo::truediv(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
  - `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status npu_demo::min(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
  - `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status npu_demo::max(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
  - `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status npu_demo::eq(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
  - `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status npu_demo::ne(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
  - `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status npu_demo::lt(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
  - `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status npu_demo::le(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
  - `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status npu_demo::gt(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
  - `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status npu_demo::ge(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
  - `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status npu_demo::exp(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& input)`
  - `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status npu_demo::select(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, bool>& cond, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
  - `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status npu_demo::reduce_sum(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`
  - `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status npu_demo::reduce_min(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`
  - `template <MemorySpace Space, typename InType, typename OutType, typename Context> Status npu_demo::reduce_max(Context& ctx, Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`
  - `template <MemorySpace LhsSpace, MemorySpace RhsSpace, MemorySpace OutSpace, typename LhsType, typename RhsType, typename OutType, typename Context> Status npu_demo::matmul(Context& ctx, Memory<OutSpace, OutType>& out, const Memory<LhsSpace, LhsType>& lhs, const Memory<RhsSpace, RhsType>& rhs, bool acc = false)`
  - `template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType, typename Context> Status npu_demo::img2col1d(Context& ctx, Memory<OutputSpace, OutType>& out, const Memory<InputSpace, InType>& input, long long k, long long s, long long d, long long p_left, long long p_right)`
  - `template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType, typename Context> Status npu_demo::img2col2d(Context& ctx, Memory<OutputSpace, OutType>& out, const Memory<InputSpace, InType>& input, long long kh, long long kw, long long sh, long long sw, long long dh, long long dw, long long ph, long long pw, long long pl, long long pr)`
  - 说明：`dma.copy` 是 IR / emit op，不新增 C++ public `npu_demo::copy(ctx, ...)` helper；`target=npu_demo` 的 `dma.copy` 继续发射为公开 `slice(ctx, target, source, zero, target.shape, one)` 形态。
  - 模板参数顺序说明：`ctx` 是函数首参，但 `Context` 类型参数位于 helper 模板参数列表末尾并由 `ctx` 推导；这样 `alloc<Space, T>(ctx, ...)`、`add<Space, InType, OutType>(ctx, ...)`、`matmul<LhsSpace, RhsSpace, OutSpace, ...>(ctx, ...)` 等“旧显式模板调用前置 ctx”的 emit_c 文本在 C++ 上成立。
  - 命名空间 / 分发说明：emitc generated body 生成未限定名 `slice(ctx, ...)`、`add<...>(ctx, ...)`，其调用目标是 `include/api` public helper 声明；API 层再通过编译期 target 宏与 `Context` 类型实例化分发到后端实现。当前目标为 npu_demo 时，kernel context 走 `include/npu_demo/kernel` 实现，cost context 走 `include/npu_demo/cost` 实现；wrapper 中 context 类型与 launch 调用必须显式写成 `npu_demo::KernelContext` 与 `npu_demo::launch(...)`，不得退化为裸 `KernelContext` 或裸 `launch(...)`。
- 公开 `API` 全量变更记录：
  - `npu_demo::launch`
    - 旧签名：`template <long long block, long long thread, long long subthread, long long shared_memory_size, typename Callable, typename... Args> Status npu_demo::launch(Callable&& callee, Args&&... args)`
    - 目标签名：`template <long long block, long long thread, long long subthread, long long shared_memory_size, auto name, typename Context, typename... Args> Status npu_demo::launch(Context& ctx, Args&&... args)`
    - 处理方式：破坏式变更；callee/name 从普通函数实参移入模板参数；删除 `callee(args...)` fallback；静态断言改为只接受 `name(ctx, args...)`。
  - include/api 全局 `launch`
    - 旧签名：`template <long long block, long long thread, long long subthread, long long shared_memory_size, typename Callable, typename... Args> Status launch(Callable&& callee, Args&&... args)`
    - 目标签名：`template <long long block, long long thread, long long subthread, long long shared_memory_size, auto name, typename Context, typename... Args> Status launch(Context& ctx, Args&&... args)`
    - 处理方式：破坏式变更；include/api 只声明 callee-in-template 的 context-first 入口，不保留无 ctx declaration，不作为 `npu_demo::launch` 之外的旧兼容入口。
  - include/api 全局 `KernelContext`
    - 保留：`class KernelContext`
    - 删除：`KernelContext::block_id() const -> long long`
    - 删除：`KernelContext::block_num() const -> long long`
    - 删除：`KernelContext::thread_id() const -> long long`
    - 删除：`KernelContext::thread_num() const -> long long`
    - 删除：`KernelContext::barrier(std::initializer_list<BarrierVisibility> visibility, BarrierScope scope) const -> void`
    - 删除：`template <MemorySpace Space, typename T> KernelContext::get_dynamic_memory() const -> Memory<Space, T>`
    - 处理方式：按 2026-06-06 用户“context 不要这些函数”纠偏做破坏式删除；include/api `KernelContext` 仅作为可传入 `launch(ctx, args...)` / helper `Context& ctx` 的上下文类型占位，不承诺 runtime 查询、同步或动态内存 member API。
  - `npu_demo::KernelContext`
    - 保留：`class npu_demo::KernelContext`
    - 保留：`npu_demo::KernelContext::KernelContext()`
    - 删除：`npu_demo::KernelContext::block_id() const -> long long`
    - 删除：`npu_demo::KernelContext::block_num() const -> long long`
    - 删除：`npu_demo::KernelContext::thread_id() const -> long long`
    - 删除：`npu_demo::KernelContext::thread_num() const -> long long`
    - 删除：`npu_demo::KernelContext::subthread_id() const -> long long`
    - 删除：`npu_demo::KernelContext::subthread_num() const -> long long`
    - 删除：`npu_demo::KernelContext::barrier(std::initializer_list<BarrierVisibility> visibility, BarrierScope scope) const -> void`
    - 删除：`template <MemorySpace Space, typename T> npu_demo::KernelContext::get_dynamic_memory() const -> Memory<Space, T>`
    - 处理方式：按 2026-06-06 用户“context 不要这些函数”纠偏做破坏式删除；`npu_demo::KernelContext` 保留为 wrapper 可默认物化并传给 `launch<..., body>(ctx, args...)` 的 opaque context 对象，runtime 查询、同步和动态内存访问改由 Arch free helper 承接。
    - 非公开收口：当前实现中带 `std::shared_ptr<npu_demo::detail::LaunchBarrierState>` 的 launch-runtime 构造不得作为 public API；execute 必须改为 private / friend / detail factory 等不暴露 `npu_demo::detail` 类型的实现结构，并不得列入文件级 `API 列表` 或 spec public API。
  - Arch free helper 保留公开面：
    - 保留：`npu_demo::block_id() -> S_INT`
    - 保留：`npu_demo::thread_id() -> S_INT`
    - 保留：`npu_demo::thread_num() -> S_INT`
    - 保留：`npu_demo::barrier(std::initializer_list<BarrierVisibility> visibility, BarrierScope scope) -> void`
    - 保留：`template <MemorySpace Space> npu_demo::get_dynamic_memory() -> DynamicMemoryRef<Space>`
    - 保留：全局 `block_id() -> S_INT`
    - 保留：全局 `thread_id() -> S_INT`
    - 保留：全局 `thread_num() -> S_INT`
    - 保留：全局 `template <MemorySpace Space> get_dynamic_memory() -> DynamicMemoryRef<Space>`
    - 保留：`template <MemorySpace Space> class DynamicMemoryRef`
    - 处理方式：用户已明确 `thread_id()` 这一类不需要变；本轮不删除、不改名、不前置 `ctx`，generated body 继续按既有 free helper 口径发射 Arch 查询 / 动态内存 / barrier。
  - DMA helper 旧签名删除并替换为 context-first：
    - `alloc(Vector)`: `npu_demo::alloc(shape, stride, format)` -> `npu_demo::alloc(ctx, shape, stride, format)`；`shape/stride` 目标 public API 为 `const Vector&`。
    - `fill`: `npu_demo::fill(target, value)` -> `npu_demo::fill(ctx, target, value)`
    - `slice(Vector)`: `npu_demo::slice(target, source, offset, size, stride)` -> `npu_demo::slice(ctx, target, source, offset, size, stride)`；`offset/size/stride` 目标 public API 为 `const Vector&`。
    - `deslice(Vector)`: `npu_demo::deslice(target, source, offset, size, stride)` -> `npu_demo::deslice(ctx, target, source, offset, size, stride)`；`offset/size/stride` 目标 public API 为 `const Vector&`。
    - `store(Vector)`: `npu_demo::store(target, source, offset, size, stride)` -> `npu_demo::store(ctx, target, source, offset, size, stride)`；`offset/size/stride` 目标 public API 为 `const Vector&`。
    - `load(Vector)`: `npu_demo::load(target, source, offset, size, stride)` -> `npu_demo::load(ctx, target, source, offset, size, stride)`；`offset/size/stride` 目标 public API 为 `const Vector&`。
    - `transpose(Vector)`: `npu_demo::transpose(target, source, perm)` -> `npu_demo::transpose(ctx, target, source, perm)`；`perm` 目标 public API 为 `const Vector&`。
    - `broadcast`: `npu_demo::broadcast(target, source)` -> `npu_demo::broadcast(ctx, target, source)`
  - Kernel helper 旧签名删除并替换为 context-first：
    - `add`: `npu_demo::add(out, lhs, rhs)` -> `npu_demo::add(ctx, out, lhs, rhs)`
    - `sub`: `npu_demo::sub(out, lhs, rhs)` -> `npu_demo::sub(ctx, out, lhs, rhs)`
    - `mul`: `npu_demo::mul(out, lhs, rhs)` -> `npu_demo::mul(ctx, out, lhs, rhs)`
    - `truediv`: `npu_demo::truediv(out, lhs, rhs)` -> `npu_demo::truediv(ctx, out, lhs, rhs)`
    - `min`: `npu_demo::min(out, lhs, rhs)` -> `npu_demo::min(ctx, out, lhs, rhs)`
    - `max`: `npu_demo::max(out, lhs, rhs)` -> `npu_demo::max(ctx, out, lhs, rhs)`
    - `eq`: `npu_demo::eq(out, lhs, rhs)` -> `npu_demo::eq(ctx, out, lhs, rhs)`
    - `ne`: `npu_demo::ne(out, lhs, rhs)` -> `npu_demo::ne(ctx, out, lhs, rhs)`
    - `lt`: `npu_demo::lt(out, lhs, rhs)` -> `npu_demo::lt(ctx, out, lhs, rhs)`
    - `le`: `npu_demo::le(out, lhs, rhs)` -> `npu_demo::le(ctx, out, lhs, rhs)`
    - `gt`: `npu_demo::gt(out, lhs, rhs)` -> `npu_demo::gt(ctx, out, lhs, rhs)`
    - `ge`: `npu_demo::ge(out, lhs, rhs)` -> `npu_demo::ge(ctx, out, lhs, rhs)`
    - `exp`: `npu_demo::exp(out, input)` -> `npu_demo::exp(ctx, out, input)`
    - `select`: `npu_demo::select(out, cond, lhs, rhs)` -> `npu_demo::select(ctx, out, cond, lhs, rhs)`
    - `reduce_sum`: `npu_demo::reduce_sum(out, input, axis)` -> `npu_demo::reduce_sum(ctx, out, input, axis)`
    - `reduce_min`: `npu_demo::reduce_min(out, input, axis)` -> `npu_demo::reduce_min(ctx, out, input, axis)`
    - `reduce_max`: `npu_demo::reduce_max(out, input, axis)` -> `npu_demo::reduce_max(ctx, out, input, axis)`
    - `matmul`: `npu_demo::matmul(out, lhs, rhs, acc)` -> `npu_demo::matmul(ctx, out, lhs, rhs, acc)`
    - `img2col1d`: `npu_demo::img2col1d(out, input, k, s, d, p_left, p_right)` -> `npu_demo::img2col1d(ctx, out, input, k, s, d, p_left, p_right)`
    - `img2col2d`: `npu_demo::img2col2d(out, input, kh, kw, sh, sw, dh, dw, ph, pw, pl, pr)` -> `npu_demo::img2col2d(ctx, out, input, kh, kw, sh, sw, dh, dw, ph, pw, pl, pr)`
  - include/api emitc-facing helper 旧签名删除并替换为 context-first：
    - 旧签名：`alloc(shape, stride, ...)`、`slice(target, source, ...)`、`add(out, lhs, rhs)`、`matmul(out, lhs, rhs, acc)` 等未限定名 helper 不接收 `ctx`。
    - 目标签名：同名未限定名 helper 全部接收 `Context& ctx` 首参，完整签名见 `目标 API 全量索引 / include/api emitc-facing DMA helper` 与 `include/api emitc-facing Kernel helper`。
    - 处理方式：破坏式变更；generated source 正向只生成 `op(ctx, ...)` 或 `op<...>(ctx, ...)`，API 层再按编译期 target 宏与 `Context` 类型分发到后端实现。
  - include/API 宏分发与 cost / kernel 实例化口径：
    - emitc / generated source 调用 `include/api` public helper：`op<...>(ctx, args...)` 或 `op(ctx, args...)`。
    - API 层根据编译期 target 宏选择实际实现；该宏只负责“选了哪个 target 就只编译哪个 target 的实现”，不得把所有 target 后端一次性编译进同一目标。
    - 目标为 npu_demo 时，kernel-mode `Context` 实例分发到 `include/npu_demo/kernel` 实现，cost-mode `Context` 实例分发到 `include/npu_demo/cost` 实现。
    - cost 与 kernel 是同一 public helper API 在不同 context 类型上的模板实例；generated source 不直接调用 backend-specific cost helper，不把 cost kind 作为 helper 模板实参。
    - 新 context-first cost path 不以 `_cost_*` sibling function、`tuner.cost` op 或 `npu_demo::cost::*<..., CostKind>` 作为 generated source 主链路。
    - 本计划不指定新的公开宏名；execute 应复用既有 build / target 选择机制或在实现内部收口。若发现必须新增或重命名对外宏、公开 cost context 类名、工具入口或稳定错误语义，必须停止并回到用户确认。
  - 历史 cost pass / tool API 处置：
    - `LaunchKernelCostFuncPass`、`launch-kernel-cost-func` registry / pipeline 引用、对应 spec 与测试作为旧 sibling `_cost_*` / `tuner.cost` 生成链路直接删除。
    - `dsl_cost_run` 保留公开入口、参数签名与包根导出；本计划不把它改成最终 cost-kernel-only 语义，只记录后续目标为“不运行 kernel，只运行 cost 的 kernel，并返回结果”。
    - `dsl_run`、非 `LaunchKernelCostFuncPass` 的 pass registry、旧 standalone `npu_demo::cost::*` / `CostKind` surface 不因本计划物理删除；这些 surface 不再作为新 context-first generated source 主链路。
  - 本轮不新增的 API：
    - 不新增 `CostContext` public class。
    - 不新增 host cost runner public function / tool。
    - 不新增 `tuner.param` / `def params` public integration。
- 当前验收资产：
  - 已按用户授权原地调整既有 `[immutable-file]`：`expectation/dsl/emit_c/npu_demo/dma/alloc.py`、`expectation/dsl/emit_c/npu_demo/dma/fill.py`、`expectation/dsl/emit_c/npu_demo/dma/copy.py`、`expectation/dsl/emit_c/npu_demo/dma/slice.py`、`expectation/dsl/emit_c/npu_demo/dma/deslice.py`、`expectation/dsl/emit_c/npu_demo/dma/store.py`、`expectation/dsl/emit_c/npu_demo/dma/load.py`、`expectation/dsl/emit_c/npu_demo/dma/transpose.py`、`expectation/dsl/emit_c/npu_demo/dma/broadcast.py`。
  - 已按用户授权原地调整既有 `[immutable-file]`：`expectation/dsl/emit_c/npu_demo/kernel/binary_elewise.py`、`expectation/dsl/emit_c/npu_demo/kernel/binary_compare.py`、`expectation/dsl/emit_c/npu_demo/kernel/exp.py`、`expectation/dsl/emit_c/npu_demo/kernel/select.py`、`expectation/dsl/emit_c/npu_demo/kernel/reduce.py`、`expectation/dsl/emit_c/npu_demo/kernel/matmul.py`、`expectation/dsl/emit_c/npu_demo/kernel/img2col.py`。
  - 已原地调整既有 `expectation/dsl/emit_c/npu_demo/arch/{get_block_id,get_thread_id,get_thread_num,get_dynamic_memory,launch}.py`；这些 Arch 叶子合同只把完整 launch module 的 body / wrapper 收为 context-first，`npu_demo::block_id()`、`npu_demo::thread_id()`、`npu_demo::thread_num()`、`npu_demo::get_dynamic_memory<Space>()` 等 free helper 保持正向口径。
  - 已原地扩展既有 `expectation/dsl/gen_kernel/context_first_source.py`，并按用户澄清保留 Arch free helper 口径。
  - 已调整既有 `expectation/include/npu_demo/launch_block_grid.py` 为 context-first launch 入口。
  - 当前红灯基线：emit_c DMA public helper 叶子 expectation 锁定 `Context& ctx` 首参、`helper<...>(ctx, ...)` / `slice(ctx, ...)` 与 braced-init `{...}` layout 实参，且正向片段禁止显式 `Vector(` layout；emit_c Kernel public helper 叶子 expectation 锁定 `Context& ctx` 首参与旧显式模板 helper 前置 `ctx`；`arch/{get_block_id,get_thread_id,get_thread_num,get_dynamic_memory,launch}.py` 均为红灯，失败点为旧无 `npu_demo::KernelContext& ctx` body、旧 `npu_demo::launch(body, args...)` 或把 body 当普通参数传递；其中 `get_dynamic_memory.py` 还锁定 `dma.copy` 展开后的 `slice(ctx, ...)` 与 braced-init layout；`context_first_source.py` 三条 case 均红，失败点分别锁定旧无 ctx body / helper、旧 context 模板 body / launch wrapper，Arch 查询本轮保持 `npu_demo::thread_id()` 等 free helper；`launch_block_grid.py` 当前预期编译失败，失败点锁定旧 `launch(callee, args...)` signature 未接收显式 context 且未把 callee/name 放入模板参数。
- expectation 授权 scope 与 manifest / hash 记录：
  - 授权 scope：本轮只允许架构师原地维护 `expectation/dsl/emit_c/npu_demo/dma/{alloc,fill,copy,slice,deslice,store,load,transpose,broadcast}.py`、`expectation/dsl/emit_c/npu_demo/kernel/{binary_elewise,binary_compare,exp,select,reduce,matmul,img2col}.py`、`expectation/dsl/emit_c/npu_demo/arch/{get_block_id,get_thread_id,get_thread_num,get_dynamic_memory,launch}.py`、`expectation/dsl/gen_kernel/context_first_source.py`、`expectation/include/npu_demo/launch_block_grid.py`；scope 外 `expectation/` 文件不得因本计划修改、移动、重命名、新建或删除。
  - Draft 22 冻结点开始 manifest 聚合 hash：`143cb25285f1a911047349a0c753003eef4cf485a45023635105e84083849097`（Draft 21 的 23 文件 scope 守护通过稿）；Draft 22 结束 manifest 聚合 hash：`4fdf05ef7ac6d2b90f689f288e08848c701a1f7daa5f98b07025ca0e82cd1cd5`（23 文件 scope）。
  - manifest 明细 hash：`alloc.py=32aab68a6daeddee153394c4bb476136f67121d33eac2198bed03feaaad36d95`、`fill.py=c20fbe6a6cfb2a25d99cc739a44c67e3d41ce34d745722bded419ae4880df1c3`、`copy.py=4397efb90d21ada7a27dd891e7872f13db91df2209b3daa2a09eb84b8f69c9a9`、`slice.py=c0c0df72f14cddccc08a2cac2b47ec169789ab4c1ef27a8845df90629fa3134a`、`deslice.py=0b049253e1bfc8c3fbc549d23c8398f5cbab11fef872f11a3f4fe1b51ca1485a`、`store.py=eab0e6b34a2f73337a60c2385e0ab40defb59e8383495786cfaade36ead78dfc`、`load.py=4cbe55112e6ee2ac465776b23b6a457f1bef25f10cd72acd62ec579e5c6fe499`、`transpose.py=4e80176499f09e612a77f088f98b2083117ba3675c5fe1835d98c1e5e39364de`、`broadcast.py=d59d9bcebc5391c9edae9d303a444ad1003bcfb0e14058388457b9633cfd0caf`、`binary_elewise.py=d7d50b06105a0ce8ae23a836e8199ee6ea1c3e9f21ba33fe84597ba9b4c3f609`、`binary_compare.py=11596ba6ec702130b0058ba4389cb4921a364e2569d492081939db27799fbeae`、`exp.py=312f05e71487c8d53ec5fc93cd29362372909e7735c24942c7f0733919865c91`、`select.py=ad7e2be869635e23feefbc3cd99ff799cfc2966e5716c0842e2621f7c0c80592`、`reduce.py=7ac91d08b1db968e419e9f8d29189981c35a10c4a1b12cba9c5132f240492953`、`matmul.py=4c901d403a4daa1b9ba0142da572466a8817f000b6150b4a915a2255cd46c63f`、`img2col.py=85c9c3c23424345ea6b7e38a59ec0c47fad9e173338e305274f10fd379f1a51c`、`arch/get_block_id.py=0dd14f066e7418f196af77d6221176deb868769677396b6a03551c980d14040e`、`arch/get_thread_id.py=1ff5d0ccd4b209e90cd4d549d987419d95ac4078691730441b18b5c2a6aa3056`、`arch/get_thread_num.py=e5791c9db9ead50e4107ff408e09ec84fe46c910394da470c99874cb4b70eb73`、`arch/get_dynamic_memory.py=2a9a01028cf1c735a5000fd0ee038c06610e52f3c0703c7f6a1bbebe3c2aa251`、`arch/launch.py=b6c1d2e996f1e18e53a00af668480d2dc529274b20287fd4bd16e568fbe16c1a`、`context_first_source.py=3f2becac1890d53e44e13b5dde79f4e5d140f46065a64ff21889cdbd1bcbedc4`、`launch_block_grid.py=0b8fdc9a0c31b78b6eb2d8bd2c4d27c4f8f81f169ad9b796307afe9343942cdf`。
  - tracked / staged / untracked / ignored 核对：`git status --short --untracked-files=all --ignored -- <scope files>` 当前仅显示上述 23 个 scope 文件为 `!!` ignored；`git status --short --untracked-files=all --ignored -- .skills agents/standard AGENTS.md TODO.md DONE.md` 当前只显示 `!! TODO.md` 与 `!! DONE.md`，未显示 `.skills`、`agents/standard` 或 `AGENTS.md` 改动。由于仓库 `.gitignore` 整体忽略 `expectation/` 与 `ARCHITECTURE/plan/`，下发 / 合并前必须用本 manifest hash 复核 scope 外空 diff，并用 `git add -f` 只纳入本计划授权 scope。
- 计划任务名：`context-first-kernel-cost-shared-code`
- 任务类型：唯一计划级 `execute`
- 流转：`execute -> review -> archive_acceptance/计划书入档验收 -> merge/归档`
- 失败接续：`review` 不通过回 `execute`；`archive_acceptance` 不通过也回 `execute`；不得另建独立 `refactor` 阶段。
- 计划文件跟踪要求：`ARCHITECTURE/plan/` 与 `expectation/` 当前可能被 ignore；下发 / merge 前必须核对本计划正文、上述 emit_c DMA / Kernel 叶子 expectation、`expectation/dsl/emit_c/npu_demo/arch/{get_block_id,get_thread_id,get_thread_num,get_dynamic_memory,launch}.py`、`expectation/dsl/gen_kernel/context_first_source.py` 与 `expectation/include/npu_demo/launch_block_grid.py` 的 `git status --short --ignored`，必要时用 `git add -f` 纳入候选。

## 计划级任务

| 计划任务 | 任务类型 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `context-first-kernel-cost-shared-code` | `execute` | 管理员下发的独立 worktree | `agents/codex-multi-agents/log/task_records/2026/<dd>/<date>-context-first-kernel-cost-shared-code.md` |

任务目标：把 `target=npu_demo` 的 emit_c / generated source 与 include helper 统一改为 context-first 调用形态：device body 显式接收 `npu_demo::KernelContext& ctx`，host 入口 / wrapper 公开签名不接收 `ctx`、只接收业务参数，并在函数体内物化 `npu_demo::KernelContext ctx` 后调用 `npu_demo::launch<block, thread, subthread, shared_memory_size, body>(ctx, args...)`；带 dtype template 的 body 只保留 dtype 模板参数并调用 `npu_demo::launch<..., body<T...>>(ctx, args...)`；DMA / Kernel helper 在旧生成文本基础上前置 `ctx`，即生成 `op<...>(ctx, args...)` 或既有无显式模板的 `op(ctx, args...)`，该调用目标是 `include/api` public helper，实际 kernel / cost 实现由 API 层按编译期 target 宏和 context 类型分发；Arch 查询 / 动态内存 / barrier 保持既有 free helper 口径；wrapper 中 context 类型与 launch 调用必须使用 `npu_demo::` 命名空间，且不得把 `ctx` 透出到 host 入口 ABI，并停止在 npu_demo generated source 主链路生成 / 依赖 sibling `_cost_*` cost functions 或直接 `cost::` helper；删除 `LaunchKernelCostFuncPass` 相关链路，保留 `dsl_cost_run` 入口且不在本计划内改成最终 cost-kernel-only 语义；更新 spec、实现文件 API 列表与 pytest 测试；只读运行本计划列出的 expectation 并记录验收结果。

## 待确认项

- 当前无待用户确认项。
- 用户已确认破坏式 context-first API、不接入 tuner param / host cost runner、params 不进 context、context 不带 target、不要旧兼容，且确认 `thread_id()` 这一类 Arch helper 不需要变。
- 用户已确认 emitc / generated source 调用 `include/api` 函数，API 根据编译期 target 宏控制实际 kernel / cost 实现；宏只用于选择本次编译的 target 实现，避免一次编译所有 target；cost 与 kernel 相当于 API context 的模板实例。
- 用户已确认 `LaunchKernelCostFuncPass` 相关链路直接删除，`dsl_cost_run` 保留且后续另立计划改为“不运行 kernel，只运行 cost 的 kernel，并返回结果”。
- 若执行中发现必须新增或公开具体宏名、公开 cost context 类名，或物理删除 / 改参 `dsl_cost_run`、`dsl_run`、非 `LaunchKernelCostFuncPass` 的 pass registry、旧 `npu_demo::cost::*` / `CostKind` surface，必须作为新增公开 API 待确认项停止推进。

## 用户确认与协同约束

- 公开 API 破坏式变更确认来源见 `文档信息 / 用户确认来源`。
- 本轮已修改的 `expectation/dsl/emit_c/npu_demo/{dma,kernel}` 叶子文件多带 `[immutable-file]`，已由用户明确授权架构师在本轮修改；`expectation/dsl/emit_c/npu_demo/arch/{get_block_id,get_thread_id,get_thread_num,get_dynamic_memory,launch}.py`、`expectation/dsl/gen_kernel/context_first_source.py` 与 `expectation/include/npu_demo/launch_block_grid.py` 已由架构阶段按同一 context-first 口径调整；execute、review、archive_acceptance 只读运行，不得修改、新增、删除或移动 `expectation/`。
- 本轮 expectation 授权 scope、manifest/hash 与 tracked / staged / untracked / ignored 状态核对见 `文档信息 / expectation 授权 scope 与 manifest / hash 记录`；后续任何角色不得把 scope 外 `expectation/` 文件纳入本计划。
- execute 修改功能实现文件时必须同步对应文件级说明的 `API 列表`，并检查不得跨文件调用当前文件之外的非公开 helper。
- 流程 / TODO 状态问管理员；公开 API、需求取舍、expectation 授权问用户；架构口径、验收口径问架构师。

## 迭代审阅记录

### 收敛轮次 1：Draft 1 主线起草与 strict review

- 审阅对象：Draft 1 正文与新增 `expectation/dsl/gen_kernel/context_first_source.py`。
- 输入标准包：根 `AGENTS.md`、当前架构师只维护计划与 expectation 的用户指令、`agents/standard/计划书标准.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`、`agents/standard/spec文件规范.md`、`agents/standard/任务记录约定.md`、本 Draft 1 全文、用户确认口径、禁止修改面和必过验收命令。
- 严格通过口径：公开 API 破坏式变更必须有用户确认来源；不得保留无 ctx 兼容入口；不得引入 `tuner.param`、host cost runner 或参数搜索；generated source 必须只有一份 context-first body；expectation 必须当前红灯、execute 转绿；计划小任务卡必须足够具体。
- 发现问题：
  - Godel `019e97ee-d6ac-79c2-a42e-f09a912136e3`：`LaunchKernelCostFuncPass` 删除/保留未决；任务目标存在 expectation 只读边界冲突；S1-S5 缺五行短口径和详细字段，且 `rg` 被误列入 Diff 反推测试。
  - Maxwell `019e97ef-03d4-73f2-8f6e-bab2e36eceb8`：cost pass 公开链路去留未写死；Arch free helper / `DynamicMemoryRef` 去留未定；expectation 覆盖不足；小任务卡缺五行短口径。
- 主线处理：
  - Draft 2 写死 `LaunchKernelCostFuncPass`、`dsl_cost_run`、registry 与工具公开入口本轮保留，只从 context-first npu_demo generated source 主链路摘除 `_cost_*` sibling 期望。
  - Draft 2 明确删除 / 降级 Arch 旧 free helper：`block_id()`、`thread_id()`、`thread_num()`、`get_dynamic_memory<Space>()`、`DynamicMemoryRef` 不再是 generated source / include/api 公开兼容入口；generated body 使用 `ctx` 成员 API。
  - Draft 2 任务目标改成只读运行 expectation 并记录验收结果；execute 阶段不得修改 `expectation/`。
  - Draft 2 扩展 `expectation/dsl/gen_kernel/context_first_source.py` 至 3 条红灯 case，覆盖 DMA、dtype template + Kernel helper、Arch member API。
  - Draft 2 重写 S1-S5 小任务卡，补五行短口径、模块范围、禁止修改面、合同真源、最小闭环、验收与记录要求，并把 `rg` 移入文本门禁。
- 状态：Draft 1 不通过，Draft 2 待新一轮 subagent strict review。

### 收敛轮次 2：Draft 2 strict review 与 Draft 3 / Draft 4 主线修订

- 审阅对象：Draft 2 正文、`expectation/dsl/gen_kernel/context_first_source.py` 与当时仍为旧 launch 合同的 `expectation/include/npu_demo/launch_block_grid.py`。
- 输入标准包：根 `AGENTS.md`、当前架构师只维护计划与 expectation 的用户指令、`agents/standard/计划书标准.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`、`agents/standard/spec文件规范.md`、`agents/standard/任务记录约定.md`、Draft 2 全文、上一轮问题、用户确认口径、禁止修改面和必过验收命令。
- 严格通过口径：所有列入合同验收的 expectation 必须与计划 API 一致；公开 API 索引必须覆盖用户要求检查的全部变更 / 保留 / 删除项；计划不得用代码示例暗示未确认的 `CostContext` public API；旧 free helper / `DynamicMemoryRef` 处置策略与文本门禁必须一致；launch fallback 门禁不得误伤新版 `Context&` callable 检查。
- 发现问题：
  - Godel `019e97ee-d6ac-79c2-a42e-f09a912136e3`：`expectation.include.npu_demo.launch_block_grid` 仍锁旧 `launch(callee, args...)`，但计划把它列为必过；文本门禁漏查全局 `block_id/thread_id/thread_num/get_dynamic_memory`；Demo 中出现具体 `CostContext` 与 `total_cycles()`，等同于未确认 API。
  - Maxwell `019e97ef-03d4-73f2-8f6e-bab2e36eceb8`：旧 free helper / `DynamicMemoryRef` 一边允许“当前文件内非公开实现细节”短期存在、一边又被文本门禁列为阻断，处置策略冲突；`std::is_invocable<...Args...>` grep 过宽，可能误伤新版 `launch(Context&, ...)` 的正确实现。
- 主线处理：
  - Draft 3 按架构授权把 `expectation/include/npu_demo/launch_block_grid.py` 改为 `npu_demo::KernelContext ctx; npu_demo::launch<...>(ctx, kernel_body, args...)` 红灯合同，并把该资产写入当前验收资产、完成态与验收设计。
  - Draft 3 增加全局 free helper 文本门禁，覆盖裸 `block_id()`、`thread_id()`、`thread_num()`、`get_dynamic_memory()` 残留，并要求人工排除合法 `ctx.*` / `KernelContext::*` 成员和历史基线描述。
  - Draft 3 删除 Demo 中的具体 `CostContext` / `total_cycles()` 代码，只保留 kernel-mode 可编译示例与后续 cost runner 不在本轮生成的文字说明。
  - Draft 3 扩展 API 索引，补齐 `BarrierVisibility` / `BarrierScope`、`dma.copy` 非 C++ public helper说明，以及 standalone cost include API 保留清单，便于用户检查。
  - Draft 4 写死旧 free helper / `DynamicMemoryRef` 为物理删除同名入口；若当前文件内部需要实现复用，只允许使用不导出的 `detail` 私有名字，且不得跨文件调用。
  - Draft 4 把 launch fallback 文本门禁收窄为旧静态断言文本、旧 `std::is_invocable<typename std::decay<Callable>::type, Args...>` 和旧 `callable(unpacked_args...)` 分支，不再用宽泛 `std::is_invocable<...Args...>` 阻断新版 `Context&` 检查。
- 状态：Draft 2 与 Draft 3 不通过；Draft 4 待新一轮 subagent strict review。

### 收敛轮次 3：Draft 4 本地 API 漏项自检与 Draft 5 主线修订

- 审阅对象：Draft 4 API 索引、删除清单、Arch free helper 口径、文本门禁，与当前 `include/npu_demo/Arch.h`、`include/npu_demo/npu_demo.h`、`spec/include/npu_demo/npu_demo.md` 的公开 API 列表。
- 输入标准包：根 `AGENTS.md`、当前架构师只维护计划与 expectation 的用户指令、`agents/standard/计划书标准.md`、Draft 4 全文、用户“所有 API 列出来”的要求、禁止修改面和必过验收命令。
- 严格通过口径：文本门禁中的旧 public surface 必须在删除清单、当前基线、公开 API 设计与任务卡中同口径出现；不得遗漏已公开的旧 free helper。
- 发现问题：
  - 本地自检发现 `npu_demo::barrier(std::initializer_list<BarrierVisibility>, BarrierScope)` 当前位于 `include/npu_demo/Arch.h`、`include/npu_demo/npu_demo.h` 与 `spec/include/npu_demo/npu_demo.md` 的公开 API 列表；Draft 4 文本门禁已阻断 `npu_demo::barrier(...)`，但公开 API 删除清单和 Arch free helper 口径未显式列出该 API。
- 主线处理：
  - Draft 5 把 `npu_demo::barrier(std::initializer_list<BarrierVisibility>, BarrierScope) -> void` 加入旧 free helper 物理删除清单。
  - Draft 5 同步当前基线、Arch free helper 口径、S2 执行步骤和 S5 减法检查，确保 `barrier` 与 `block_id/thread_id/thread_num/get_dynamic_memory/DynamicMemoryRef` 处置一致。
- 状态：Draft 4 不下发；Draft 5 待新一轮 subagent strict review。

### 收敛轮次 4：Draft 5 strict review 与 Draft 6 主线修订

- 审阅对象：Draft 5 正文与两份 expectation。
- 输入标准包：根 `AGENTS.md`、当前架构师只维护计划与 expectation 的用户指令、`agents/standard/计划书标准.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`、`agents/standard/spec文件规范.md`、`agents/standard/任务记录约定.md`、Draft 5 全文、上一轮问题、用户确认口径、禁止修改面和必过验收命令。
- 严格通过口径：公开 API 变更 / 删除面必须覆盖 include/api 与 include/npu_demo 的所有旧入口；不得遗漏全局 public API；旧 no-ctx launch declaration / implementation 不得残留。
- 发现问题：
  - Godel `019e97ee-d6ac-79c2-a42e-f09a912136e3`：Draft 5 只记录 `npu_demo::launch(...)`，未收口当前 `include/api/Arch.h` / `spec/include/api/Arch.md` 中已有的全局 `launch(Callable&&, Args&&...)` 公开入口；可能留下旧无 ctx 兼容入口或未记录破坏式变更。
- 主线处理：
  - Draft 6 把 include/api 全局 `launch(Context& ctx, Callable&& callee, Args&&... args)` 加入目标 API 索引。
  - Draft 6 在公开 API 变更记录中写明全局 `launch(Callable&&, Args&&...)` 破坏式改为 context-first declaration，不保留无 ctx declaration，也不作为 `npu_demo::launch` 之外的旧兼容入口。
  - Draft 6 同步当前基线、S1/S2/S5 和文本门禁，要求 spec / include / test 中旧全局 no-ctx `launch` 形态清零。
- 状态：Draft 5 不通过；Draft 6 待新一轮 subagent strict review。

### 收敛轮次 5：Draft 6 strict review 与 Draft 7 主线修订

- 审阅对象：Draft 6 正文与两份 expectation。
- 输入标准包：根 `AGENTS.md`、当前架构师只维护计划与 expectation 的用户指令、`agents/standard/计划书标准.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`、`agents/standard/spec文件规范.md`、`agents/standard/任务记录约定.md`、Draft 6 全文、上一轮问题、用户确认口径、禁止修改面和必过验收命令。
- 严格通过口径：`KernelContext` class 场景必须按 include/api 全局接口与 npu_demo 具体上下文分别列全公开 API；构造签名必须记录；不得把 `npu_demo::KernelContext ctx;` 写入 expectation 却遗漏默认构造合同。
- 发现问题：
  - Maxwell `019e97ef-03d4-73f2-8f6e-bab2e36eceb8`：Draft 6 只记录 `class npu_demo::KernelContext`，未收口当前 include/api 公开面中的全局 `class KernelContext`；同时 plan / expectation 要求 `npu_demo::KernelContext ctx;` 默认实例化，但未把 `npu_demo::KernelContext()` 公开构造签名列入 API 记录。
- 主线处理：
  - Draft 7 将 include/api 全局 `class KernelContext` 与 `class npu_demo::KernelContext` 拆开列出。
  - Draft 7 补齐 include/api 全局 `KernelContext` 的保留口径：作为抽象接口保留，不改名、不删除，不新增 public 默认构造。
  - Draft 7 补齐 `npu_demo::KernelContext::KernelContext()` 与当前 launch-runtime 构造签名，并同步当前基线、完成态与 S2 执行步骤。
- 状态：Draft 6 不通过；Draft 7 待新一轮 subagent strict review。

### 收敛轮次 6：Draft 7 strict review 与 Draft 8 主线修订

- 审阅对象：Draft 7 正文与两份 expectation。
- 输入标准包：根 `AGENTS.md`、当前架构师只维护计划与 expectation 的用户指令、`agents/standard/计划书标准.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`、`agents/standard/spec文件规范.md`、`agents/standard/任务记录约定.md`、Draft 7 全文、上一轮问题、用户确认口径、禁止修改面和必过验收命令。
- 严格通过口径：公开 API 不得暴露 `npu_demo::detail::*`；若当前实现 public 区域存在 detail 类型构造，计划必须收为非公开实现结构，或显式升级 detail 为公开 API 并取得用户确认。
- 发现问题：
  - Maxwell `019e97ef-03d4-73f2-8f6e-bab2e36eceb8`：Draft 7 把 `npu_demo::KernelContext(long long..., std::shared_ptr<npu_demo::detail::LaunchBarrierState>)` 列为公开 API，但当前 spec 写明 `npu_demo::detail` 只供实现内部使用；该构造会把 detail 类型升级成 public surface。
- 主线处理：
  - Draft 8 从目标公开 API 索引与 `npu_demo::KernelContext` 保留清单中移除该 launch-runtime 构造。
  - Draft 8 明确该构造必须收为 private / friend / detail factory 等不暴露 `npu_demo::detail` 类型的实现结构，不得列入文件级 `API 列表` 或 spec public API。
  - Draft 8 保留 `npu_demo::KernelContext::KernelContext()` 作为 wrapper 物化 kernel context 的公开构造签名。
- 状态：Draft 7 不通过；Draft 8 待新一轮 subagent strict review。

### 收敛轮次 7：Draft 8 strict review

- 审阅对象：Draft 8 正文与两份 expectation。
- 输入标准包：根 `AGENTS.md`、当前架构师只维护计划与 expectation 的用户指令、`agents/standard/计划书标准.md`、`agents/standard/实现文件规范.md`、`agents/standard/测试文件约定.md`、`agents/standard/spec文件规范.md`、`agents/standard/任务记录约定.md`、Draft 8 全文、上一轮问题、用户确认口径、禁止修改面和必过验收命令。
- 严格通过口径：公开 API 变更 / 删除 / 保留项完整；context-first launch/body/helper/Arch 链路贯穿；旧无 ctx 兼容、旧 free helper、`DynamicMemoryRef`、`npu_demo::barrier(...)` 与全局 old launch declaration 不残留；`npu_demo::detail::*` 不暴露为 public API；不新增 `CostContext`、host cost runner、tuner.param 或 best params；两份 expectation 当前红灯且 execute 只读转绿；任务卡和验收门禁可执行。
- 发现问题：
  - Godel `019e97ee-d6ac-79c2-a42e-f09a912136e3`：通过；无阻断项、无最小需改项。
  - Maxwell `019e97ef-03d4-73f2-8f6e-bab2e36eceb8`：通过；无阻断项、无最小需改项。
- 主线处理：无需修改。
- 状态：Draft 8 subagent strict review 收敛，可进入守护最终检验。

### 收敛轮次 8：Draft 9 strict review 与 Draft 10 主线修订

- 审阅对象：Draft 8 通过稿、用户关于“emit_c 的前面添加 ctx，注意命名空间”的澄清、现有 `expectation/dsl/emit_c/npu_demo/**` 合同布局与 Draft 9 正文。
- 输入标准包：根 `AGENTS.md`、当前架构师只维护计划与 expectation 的用户指令、Draft 8 全文、Draft 8 守护最终检验记录、用户最新澄清、禁止修改面、`[immutable-file]` expectation 保护要求和必过验收命令。
- 严格通过口径：emit_c 层必须有独立合同锁定 `ctx` 第一实参；不得修改 `dma/copy.py`、`kernel/binary_elewise.py` 等 `[immutable-file]` 合同；wrapper 物化 context 与 launch 调用必须显式使用 `npu_demo::KernelContext` / `npu_demo::launch`，不得裸用全局 `KernelContext` / `launch`；body helper 调用可保持未限定名 `slice(ctx, ...)` / `add(ctx, ...)` 以服务后续 cost/context overload；Draft 8 通过结论不得直接作为 Draft 9 下发依据。
- 发现问题：
  - Godel `019e97ee-d6ac-79c2-a42e-f09a912136e3`：无阻断项、无待确认项；最小需改项为 Draft 9 仍有三处裸 launch 或未限定 KernelContext 类型文本，和命名空间门禁冲突。
  - Maxwell `019e97ef-03d4-73f2-8f6e-bab2e36eceb8`：无阻断项、无待确认项；最小需改项为新增 expectation 关联了不存在的 emit_c spec 假路径，计划目标 spec 与 S1 未把实际存在的 `spec/dsl/gen_kernel/emit.md` 纳入 emit_c 真源。
- 主线处理：
  - Draft 9 新增 `expectation/dsl/emit_c/npu_demo/context_first_api.py`，以一条可执行红灯 case 锁定 emit_c 层 `Context& ctx` 首参、`slice(ctx, ...)`、`add(ctx, ...)`、`ctx.thread_id()`、`npu_demo::KernelContext ctx;` 与 `npu_demo::launch<...>(ctx, body<npu_demo::KernelContext>, args...)`。
  - Draft 9 不修改既有 `[immutable-file]` expectation；通过新增直模块入口让 `python -m expectation.dsl.emit_c.npu_demo.context_first_api` 可单独运行，也可被 npu_demo emit_c 聚合入口发现。
  - Draft 10 把 Draft 9 中的裸 launch 与未限定 KernelContext 类型文本改为显式 `npu_demo::launch<...>(ctx, ...)` 与 `body(npu_demo::KernelContext&, args...)`。
  - Draft 10 将新增 expectation 的关联 spec 从不存在的 emit_c spec 假路径改为现有 `spec/dsl/gen_kernel/emit.md`，并在目标 spec 与 S1 执行步骤中同步 `spec/dsl/gen_kernel/emit.md`、`spec/dsl/gen_kernel/emit/npu_demo.md` 与 `spec/dsl/gen_kernel/emit/npu_demo/include.md`。
  - Draft 10 在公开 API 索引、任务目标、完成态、S3/S5、验收设计和敏感目录核对中加入 emit_c 合同与命名空间规则。
- 本地红灯自检：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.context_first_api`：红，失败点为旧无 ctx body、`slice(out, ...)`、`add<...>(out, ...)`、`npu_demo::thread_id()` 与旧 `npu_demo::launch(body, args...)`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.gen_kernel.context_first_source`：红，三条 case 分别落在旧无 ctx body / helper、旧 dtype template 顺序和旧 Arch free helper。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.include.npu_demo.launch_block_grid`：红，编译失败点为旧 `launch(callee, args...)` 签名未接收显式 `ctx`。
- 状态：Draft 9 strict review 不通过；Draft 10 待新一轮 subagent strict review，未通过前不得进入守护最终检验或创建 execute。

### 收敛轮次 9：Draft 10 strict review 与 Draft 11 主线修订

- 审阅对象：Draft 10 正文与 `expectation/dsl/emit_c/npu_demo/context_first_api.py`。
- 输入标准包：根 `AGENTS.md`、当前架构师只维护计划与 expectation 的用户指令、Draft 10 全文、Draft 9 strict review 问题、用户最新澄清、禁止修改面和必过验收命令。
- 严格通过口径：Draft 9 的裸 launch / 未限定 KernelContext 问题必须清零；新增 expectation 关联文件、目标 spec 与 S1 目标必须一致；三条 expectation 必须可执行红灯；无待用户确认项。
- 发现问题：
  - Godel `019e97ee-d6ac-79c2-a42e-f09a912136e3`：无阻断项、无待确认项；最小需改项为新增 expectation 关联文件漏列 `spec/dsl/gen_kernel/emit/npu_demo/include.md`，与 Draft 10 目标 spec / S1 不一致。
  - Maxwell `019e97ef-03d4-73f2-8f6e-bab2e36eceb8`：无阻断项、无待确认项；同样要求在新增 expectation 关联文件中补入 `spec/dsl/gen_kernel/emit/npu_demo/include.md`。
- 主线处理：
  - Draft 11 在 `expectation/dsl/emit_c/npu_demo/context_first_api.py` 关联文件中补入 `spec/dsl/gen_kernel/emit/npu_demo/include.md`。
- 状态：Draft 10 strict review 不通过；Draft 11 待新一轮 subagent strict review，未通过前不得进入守护最终检验或创建 execute。

### 收敛轮次 10：Draft 11 strict review

- 审阅对象：Draft 11 正文与 `expectation/dsl/emit_c/npu_demo/context_first_api.py`。
- 输入标准包：根 `AGENTS.md`、当前架构师只维护计划与 expectation 的用户指令、Draft 11 全文、Draft 10 strict review 问题、用户最新澄清、禁止修改面和必过验收命令。
- 严格通过口径：`spec/dsl/gen_kernel/emit/npu_demo/include.md` 必须同时出现在目标 spec、S1 执行步骤和新增 expectation 关联文件；Draft 9 / Draft 10 最小需改项全部清零；无阻断、无最小需改项、无待确认项。
- 发现问题：
  - Godel `019e97ee-d6ac-79c2-a42e-f09a912136e3`：通过；无阻断项、无最小需改项、无待确认项。
  - Maxwell `019e97ef-03d4-73f2-8f6e-bab2e36eceb8`：通过；无阻断项、无最小需改项、无待确认项。
- 主线处理：无需修改。
- 状态：Draft 11 subagent strict review 收敛，可进入守护最终检验。

### 收敛轮次 11：用户纠偏与 Draft 12 主线修订

- 审阅对象：Draft 11 通过稿、用户“之前 expectation 原地加 ctx”与“`thread_id()` 这一类不需要变”的澄清、用户对 `[immutable-file]` expectation 的修改授权。
- 输入标准包：根 `AGENTS.md`、当前架构师只维护计划与 expectation 的用户指令、Draft 11 全文、用户最新澄清、已修改 expectation diff、禁止修改面和必过验收命令。
- 严格通过口径：不得新增聚合 expectation；既有 emit_c expectation 原地体现 `ctx` 首参；DMA / Kernel helper 与 launch context-first；Arch 查询、动态内存和 barrier 保持既有 free helper 口径；带 `[immutable-file]` 的 expectation 修改必须记录用户授权；Draft 11 通过结论不得作为 Draft 12 下发依据。
- 主线处理：
  - Draft 12 删除新增聚合合同 `expectation/dsl/emit_c/npu_demo/context_first_api.py`。
  - Draft 12 原地修改 `expectation/dsl/emit_c/npu_demo/dma/copy.py`，要求函数生成 `Context& ctx` 首参并发射 `slice(ctx, dst, source, ...)`。
  - Draft 12 原地修改 `expectation/dsl/emit_c/npu_demo/kernel/binary_elewise.py`，要求 `add/sub/mul/truediv(ctx, out, lhs, rhs)`，并禁止旧显式模板 no-ctx helper 调用。
  - Draft 12 原地修改 `expectation/dsl/emit_c/npu_demo/arch/launch.py`，要求 launch body 与 wrapper context-first。
  - Draft 12 修改 `expectation/dsl/gen_kernel/context_first_source.py` 的 Arch case：body / launch 仍 context-first，但 `npu_demo::thread_id()`、`npu_demo::get_dynamic_memory<...>()`、`npu_demo::barrier(...)` 作为正向口径保留。
  - Draft 12 将计划 API 索引、公开 API 变更记录、完成态、S1-S5、验收命令和文本门禁同步到“Arch free helper 保留”口径。
- 本地红灯自检：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma.copy`：红，两条 case 失败点为旧函数把 `%ctx` 发射为 `long long ctx` 且 `slice(...)` 未传 `ctx`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.kernel.binary_elewise`：红，八条 case 失败点为旧源码未生成 `template <typename Context>` / context-first helper。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.arch.launch`：红，一条 case 失败点为旧无 ctx body / 旧 `npu_demo::launch(body, args...)`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.gen_kernel.context_first_source`：红，三条 case 失败点为旧无 ctx body / helper、旧 dtype template 顺序、旧 launch wrapper；Arch free helper 文本保持正向。
- 状态：Draft 11 通过结论已 supersede；Draft 12 待 subagent strict review，未通过前不得进入守护最终检验或创建 execute。

### 收敛轮次 12：Draft 12 strict review 与 Draft 13 修订

- 审阅对象：Draft 12 正文、五份当前 expectation、用户最新澄清、禁止修改面和必过验收命令。
- 输入标准包：根 `AGENTS.md`、当前架构师只维护计划与 expectation 的用户指令、相关 `agents/standard/**`、Draft 12 全文、Draft 11 历史问题、Draft 12 主线收口摘要、待确认项、禁止修改面和必过验收命令。
- 严格通过口径：不得新增聚合 expectation；既有 expectation 原地体现 `ctx` 首参；DMA / Kernel helper 与 launch context-first；Arch 查询、动态内存和 barrier 保持 free helper；公开 API 索引与 expectation dtype 口径一致；execute 只读 expectation；无阻断、无最小需改项、无待确认项。
- 发现问题：
  - Godel `019e97ee-d6ac-79c2-a42e-f09a912136e3`：Draft 12 strict review 通过，无阻断、无最小需改项、无待确认项。
  - Maxwell `019e97ef-03d4-73f2-8f6e-bab2e36eceb8`：无阻断、无待确认；最小需改项为计划 API 索引中 `slice(ctx, target, source, ...)` 仍是同一元素类型 `T`，但 `expectation/dsl/emit_c/npu_demo/dma/copy.py` 随机 `src_dtype` 与 `dst_dtype` 两个独立 dtype，合同与 include API 可能不一致。
  - Maxwell 可改进项：S3 测试更新措辞“不再断言 hidden `KernelContext`、free helper...”容易误读为不再检查 Arch free helper。
- 主线处理：
  - Draft 13 将 `dma.copy` expectation 的 `src/dst` dtype 收为同一随机 dtype，保留 src/dst memory space 可不同，不新增双 dtype `slice` public API。
  - Draft 13 将 S3 测试更新措辞改为：移除隐藏 `KernelContext` 的旧断言，保留 / 新增 Arch free helper 正向断言，移除 sibling cost function 正向断言。
- 本地红灯自检：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma.copy`：红，两条 case 仍失败于旧函数把 `%ctx` 发射为 `long long ctx` 且 `slice(...)` 未传 `ctx`；actual source 中 src/dst dtype 已同型，符合公开 `slice(ctx, ...)` API。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.kernel.binary_elewise`：红，八条 case 失败点为旧源码未生成 `template <typename Context>` / context-first helper。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.arch.launch`：红，一条 case 失败点为旧无 ctx body / 旧 `npu_demo::launch(body, args...)`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.gen_kernel.context_first_source`：红，三条 case 失败点为旧无 ctx body / helper、旧 dtype template 顺序、旧 launch wrapper；Arch free helper 文本保持正向。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.include.npu_demo.launch_block_grid`：红，编译失败点为旧 `launch(callee, args...)` signature 未接收显式 context。
- 当时状态：Draft 12 未收敛，进入 Draft 13 新一轮 subagent strict review；该历史状态已由收敛轮次 13 和守护最终检验结论 supersede。

### 收敛轮次 13：Draft 13 strict review 双通过

- 审阅对象：Draft 13 最新正文、五份当前 expectation、Draft 12 Maxwell 最小需改项修复、用户最新澄清、禁止修改面和必过验收命令。
- 输入标准包：根 `AGENTS.md`、当前架构师只维护计划与 expectation 的用户指令、相关 `agents/standard/**`、Draft 13 全文、Draft 12 strict review 问题、Draft 13 修复摘要、待确认项、禁止修改面和必过验收命令。
- 严格通过口径：Draft 13 必须无新增聚合 expectation；`dma.copy` expectation dtype 与公开 `slice(ctx, ...)` API 同口径；launch / DMA / Kernel helper context-first；Arch 查询 / 动态内存 / barrier 保持 free helper；完成态、验收设计、文本门禁和当前五份 expectation 一致；无阻断、无最小需改项、无待确认项。
- 发现问题：
  - Godel `019e97ee-d6ac-79c2-a42e-f09a912136e3`：Draft 13 strict review 通过，无阻断、无最小需改项、无待确认项。
  - Maxwell `019e97ef-03d4-73f2-8f6e-bab2e36eceb8`：Draft 13 strict review 通过，无阻断、无最小需改项、无待确认项。
- 主线处理：无新增修改。
- 状态：Draft 13 strict review 已收敛；进入守护最终检验前置。

### 收敛轮次 14：用户 Vector API 纠偏与 Draft 14 主线修订

- 审阅对象：Draft 13 通过稿、用户“`std::initializer_list<long long> stride` API 应该是 `Vector`”的公开 API 纠偏、当前计划 API 索引与 `expectation/dsl/gen_kernel/context_first_source.py` diff。
- 输入标准包：根 `AGENTS.md`、当前架构师只维护计划与 expectation 的用户指令、相关 `agents/standard/**`、Draft 13 全文、Draft 13 strict review / 守护最终检验结论、用户最新纠偏、禁止修改面和必过验收命令。
- 严格通过口径：本轮目标 DMA helper 的 `shape/offset/size/stride/perm` layout 参数必须统一为 `Vector` 公开面；目标 API 索引、公开 API 变更记录、Demo、generated source expectation 与文本门禁不得把 `std::initializer_list<long long> ... stride` 写成目标 public API；Arch free helper 保持不变；execute 只读 expectation。
- 主线处理：
  - Draft 14 将目标 `npu_demo::alloc(ctx, ...)` 的 `shape/stride` 改为 `const Vector&`。
  - Draft 14 删除目标 `slice/deslice/transpose` 的 initializer-list public overload 记录，并将 `store/load` 的 `offset/size/stride` 改为 `const Vector&`。
  - Draft 14 将 standalone cost Dma layout API 记录收成 `Vector` 口径；cost pass / tool 入口仍保留，不生成 host cost runner。
  - Draft 14 将 `expectation/dsl/gen_kernel/context_first_source.py` 的完整 generated source 期望从 `{...} /*offset/size/stride*/` 改成 `Vector(static_cast<long long>(...))`，并禁止旧 brace-list layout 文本。
- 状态：Draft 13 strict review 与守护最终检验已被 Draft 14 supersede；Draft 14 待 subagent strict review，未通过前不得进入守护最终检验或创建 execute。

### 收敛轮次 15：emit_c 叶子合同扩展与 Draft 15 主线修订

- 审阅对象：Draft 14 正文、用户关于 `/expectation/dsl/emit_c` 是否也要更新为 ctx 版本的追问、当前 `expectation/dsl/emit_c/npu_demo/{dma,kernel}` public helper 叶子合同 diff。
- 输入标准包：根 `AGENTS.md`、当前架构师只维护计划与 expectation 的用户指令、相关 `agents/standard/**`、Draft 14 全文、用户“在之前 expectation 基础上添加 ctx / 注意命名空间 / thread_id 不变 / stride 用 Vector”的确认、禁止修改面和必过验收命令。
- 严格通过口径：所有本轮 public DMA / Kernel helper emit_c 叶子 expectation 必须原地加 `Context& ctx` 首参；旧显式模板 helper 调用必须保留模板参数并前置 `ctx`；DMA layout 参数必须使用 `Vector`；`view/reshape/free/cast` 与 `cost/*` 不作为本轮 public helper ctx 化合同；Arch free helper 保持不变；无阻断、无最小需改项、无待确认项后才可守护终验。
- 主线处理：
  - Draft 15 将 `alloc/fill/slice/deslice/store/load/transpose/broadcast/copy` emit_c 叶子合同统一补为 context-first，并把 layout expectation 收为 `Vector(...)`。
  - Draft 15 将 `binary_elewise/binary_compare/exp/select/reduce/matmul/img2col` emit_c 叶子合同统一补为 context-first；旧显式模板调用生成 `helper<...>(ctx, ...)`，不再收为 `helper(ctx, ...)`。
  - Draft 15 将目标 helper API 的 `Context` 模板参数改为 trailing 可推导参数，保证 `alloc<Space, T>(ctx, ...)` 和 `add<Space, InType, OutType>(ctx, ...)` 这类“旧模板实参加 ctx”文本合法。
  - Draft 15 扩展完成态、验收设计、文本门禁和敏感目录核对范围。
- 状态：Draft 14 strict review 尚未执行即被 Draft 15 supersede；Draft 15 待 subagent strict review，未通过前不得进入守护最终检验或创建 execute。

### 收敛轮次 16：Draft 15 strict review 反馈与 manifest 记录补强

- 审阅对象：Draft 15 正文、用户关于 `/expectation/dsl/emit_c` 叶子合同 ctx 化的确认、当前 expectation 授权 scope 与必过验收命令。
- 输入标准包：根 `AGENTS.md`、当前架构师只维护计划与 expectation 的用户指令、`agents/standard/计划书标准.md`、`agents/standard/审查规范.md`、`agents/standard/spec文件规范.md`、`agents/standard/实现文件规范.md`、`agents/standard/expectation任务规则.md`、Draft 15 全文、Draft 14 / Draft 15 supersede 说明、用户确认项、禁止修改面和必过验收命令。
- 严格通过口径：公开 API / ctx / Vector / Arch free helper / standalone cost 口径不得冲突；计划必须记录 expectation 授权 scope、manifest/hash、scope 外空 diff 核对、tracked / staged / untracked / ignored 状态；所有必过 emit_c 叶子 expectation 必须列入验收；无待确认项；不得创建 execute。
- 发现问题：
  - Godel `019e97ee-d6ac-79c2-a42e-f09a912136e3`：最小需改项，Draft 15 未记录 expectation 授权修改所需的开始 / 结束 manifest 或 hash、授权 scope、scope 外空 diff、tracked / staged / untracked / ignored 检查；API / ctx / Vector / Arch free helper / standalone cost 口径未发现阻断冲突。
  - Maxwell `019e97ef-03d4-73f2-8f6e-bab2e36eceb8`：本轮审阅因远端 `503 Service Unavailable` 中断，无有效结论；不得视为通过。
- 主线处理：
  - Draft 16 在 `文档信息` 中补齐 expectation 授权 scope、19 个 scope 文件 manifest 明细 hash、聚合 hash、tracked / staged / untracked / ignored 核对结果，并明确 `.gitignore` 整体忽略 `expectation/` 与 `ARCHITECTURE/plan/` 时后续必须用 manifest/hash 复核 scope 外空 diff、只用 `git add -f` 纳入授权 scope。
  - Draft 16 不改变 Draft 15 的公开 API 设计、helper 模板参数顺序、`Vector` layout、Arch free helper 保留口径或 standalone cost 非目标。
- 状态：Draft 16 待新一轮 subagent strict review；未通过前不得进入守护最终检验或创建 execute。

### 收敛轮次 17：Draft 16 strict review 反馈与守护对象修正

- 审阅对象：Draft 16 正文、Draft 15 manifest/hash 修复结果、当前下发前置和守护最终检验对象。
- 输入标准包：根 `AGENTS.md`、当前架构师只维护计划与 expectation 的用户指令、`agents/standard/计划书标准.md`、`agents/standard/审查规范.md`、`agents/standard/spec文件规范.md`、`agents/standard/expectation任务规则.md`、Draft 16 全文、Draft 15 / Draft 16 strict review 反馈、用户确认项、禁止修改面和必过验收命令。
- 严格通过口径：Draft 16 manifest/hash 缺口必须补齐；守护最终检验当前对象必须指向最新 Draft，不得把 Draft 15 当作当前下发依据；公开 API / ctx / Vector / Arch free helper / standalone cost 口径不得冲突；无待确认项；不得创建 execute。
- 发现问题：
  - Godel `019e97ee-d6ac-79c2-a42e-f09a912136e3`：最小需改项，`守护最终检验 / 检验对象` 仍写 `Draft 15 正文`，会误导守护终验按旧 Draft 15 正文验收；manifest/hash 修复、API / ctx / Vector / Arch free helper / standalone cost 口径未发现其它阻断。
  - Maxwell `019e97ef-03d4-73f2-8f6e-bab2e36eceb8`：返回空 completed，无有效发现、验证或结论；不得视为通过。
- 主线处理：
  - Draft 17 将守护最终检验当前对象改为 `Draft 17 正文`，并更新当前状态、subagent 收敛结论、守护最终检验结论和下发前置指向 Draft 17。
  - Draft 17 不改变 Draft 16 的公开 API 设计、helper 模板参数顺序、`Vector` layout、Arch free helper 保留口径、standalone cost 非目标或 expectation manifest hash。
- Draft 17 strict review 结果：
  - Godel `019e97ee-d6ac-79c2-a42e-f09a912136e3`：通过；验证 Draft 17 守护对象、subagent 收敛结论、下发前置、manifest/hash、19 个 scope 文件状态、`Context& ctx`、helper 模板 `Context` 末尾推导、`Vector` layout、Arch free helper 保留和 standalone cost 非目标均无阻断。
  - James `019e98b3-a33e-7641-b7d0-d90ad2824049`：通过；验证 19 个 expectation scope 文件 hash 与聚合 hash 匹配，正向 `CHECK` / `expected_snippets` 均要求 `template <typename Context>`、`Context& ctx`、`helper<...>(ctx, ...)` / `slice(ctx, ...)` 和 `Vector(...)`，Arch case 保留 free helper；运行 19 个 expectation 入口均为旧实现未传 ctx 的红灯，未见 `SyntaxError` / `ImportError`。
- 状态：Draft 17 subagent strict review 已收敛；无阻断、无最小需改项、无待确认项；可进入守护最终检验。守护最终检验通过前不得创建 execute。

### 收敛轮次 18：Draft 17 通过稿后的 braced-init 实参纠偏

- 审阅对象：Draft 18 正文、2026-06-06 用户关于 `Vector` 调用实参应写 `{val, val1, val2}` 的纠偏、当前 expectation scope 变更与 manifest/hash。
- 输入标准包：根 `AGENTS.md`、当前架构师只维护计划与 expectation 的用户指令、`agents/standard/计划书标准.md`、`agents/standard/审查规范.md`、`agents/standard/spec文件规范.md`、`agents/standard/expectation任务规则.md`、Draft 18 全文、Draft 17 strict review / 守护最终检验历史结论、用户最新纠偏、禁止修改面和必过验收命令。
- 严格通过口径：public helper API 的 Dma layout 参数仍必须是 `const Vector&`；generated source / emit_c expectation 中 layout 实参必须为 braced-init `{static_cast<long long>(...)}` 以构造 `Vector`，不得把 public API 改成 `std::initializer_list<long long>`，也不得把正向 generated source 写回显式 `Vector(...)`；ctx-first、Arch free helper、launch 命名空间、standalone cost 非目标和 expectation 授权 scope 不得回退；无阻断、无最小需改项、无待确认项；不得创建 execute。
- 发现问题：无阻断、无最小需改项、无待确认项；Draft 17 的 strict review 与守护最终检验通过结论已被本轮用户纠偏 supersede，不能作为当前下发依据。
- 主线处理：
  - Draft 18 将正向 Dma layout generated source / expectation 从显式 `Vector(...)` 改为 braced-init `{...}`，同时保留 API 索引中的 `const Vector&`。
  - Draft 18 更新 manifest/hash、当前红灯基线、Demo、generated body 合同、S3 执行步骤、文本门禁、subagent 收敛结论、守护最终检验和下发前置。
- 本地自检：
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile expectation/dsl/emit_c/npu_demo/dma/{alloc,copy,slice,deslice,store,load,transpose}.py expectation/dsl/gen_kernel/context_first_source.py`：通过。
  - `rg -n --pcre2 "CHECK[^\\n]*Vector\\(|expected_snippets[\\s\\S]*?Vector\\(" expectation/dsl/emit_c/npu_demo/dma/{alloc,copy,slice,deslice,store,load,transpose}.py expectation/dsl/gen_kernel/context_first_source.py`：无命中；正向 expectation 不再要求显式 `Vector(` layout。
  - 逐一运行 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m <module>`，其中 `<module>` 为 `expectation.dsl.emit_c.npu_demo.dma.alloc`、`expectation.dsl.emit_c.npu_demo.dma.copy`、`expectation.dsl.emit_c.npu_demo.dma.slice`、`expectation.dsl.emit_c.npu_demo.dma.deslice`、`expectation.dsl.emit_c.npu_demo.dma.store`、`expectation.dsl.emit_c.npu_demo.dma.load`、`expectation.dsl.emit_c.npu_demo.dma.transpose` 与 `expectation.dsl.gen_kernel.context_first_source`：均为 execute 前红灯；失败点为旧实现仍缺少 `Context& ctx` / helper 仍未传 `ctx` / launch 仍未传显式 context，未见 `SyntaxError`、`ImportError` 或 `ModuleNotFoundError`。
- Draft 18 strict review 结果：
  - Godel `019e97ee-d6ac-79c2-a42e-f09a912136e3`：通过；核对 Draft 18 当前状态、API 口径、braced-init 口径、19 个 scope 文件 hash、聚合 hash `0c47f13129fecb952e675312ae6d5da9092629cbe7366062b6c2efd42d4c503c`、敏感目录状态和 expectation 正向 `Vector(` 文本门禁，均无阻断、无最小需改项、无待确认项。
  - Dirac `019e98d4-e7be-7de2-b91a-d2f8a958a0ea`：通过；核对 19 个 expectation scope 文件数量、明细 hash、聚合 hash、Dma layout braced-init expectation、`Vector(` 仅出现在 forbidden / 历史 / 门禁文本、`fill.py` / `broadcast.py` 无 layout braced-init 需求，均无阻断；仅提出可选审计记录微调，不构成必改项。
- Draft 18 守护最终检验结果：
  - Erdos `019e98d9-8bf0-70e0-b29a-7b17a8d9a6ad`：不通过；阻断项为 `expectation/dsl/emit_c/npu_demo/arch/launch.py` 正向 `CHECK-NEXT` 仍要求 `slice(ctx, ..., Vector(static_cast<long long>(...)), ...)`，违反 Draft 18 braced-init 文本门禁。
  - 其余核验项无阻断：Draft 18 状态、用户确认来源、API 索引、公开 API 变更记录、下发前置已落位；19 个 expectation 入口均为 execute 前红灯，未见 `SyntaxError`、`ImportError` 或 `ModuleNotFoundError`；敏感目录未见越权。
- 状态：Draft 18 strict review 已收敛但守护最终检验不通过；进入 Draft 19 修订。Draft 18 不得作为当前下发依据，不得创建 execute。

### 收敛轮次 19：Draft 18 守护阻断修复

- 审阅对象：Draft 19 正文、Draft 18 守护最终检验不通过结论、`expectation/dsl/emit_c/npu_demo/arch/launch.py` 的 braced-init 修复、当前 expectation scope 变更与 manifest/hash。
- 输入标准包：根 `AGENTS.md`、当前架构师只维护计划与 expectation 的用户指令、`agents/standard/计划书标准.md`、`agents/standard/审查规范.md`、`agents/standard/spec文件规范.md`、`agents/standard/expectation任务规则.md`、Draft 19 全文、Draft 18 strict review 通过结论、Draft 18 守护最终检验失败结论、用户最新纠偏、禁止修改面和必过验收命令。
- 严格通过口径：Draft 18 守护指出的 `arch/launch.py` 正向 `Vector(...)` 漏点必须修复；全 scope 正向 expectation 不得再出现 `CHECK...Vector(`；`Vector(` 只允许在 `forbidden_snippets`、计划历史或文本门禁中；public helper API 仍为 `const Vector&`；ctx-first、Arch free helper、launch 命名空间、standalone cost 非目标和 expectation 授权 scope 不得回退；无阻断、无最小需改项、无待确认项；不得创建 execute。
- 发现问题：Draft 19 strict review 待发起；Draft 18 的 strict review 通过结论和守护失败结论均只作历史证据，不能作为当前下发依据。
- 主线处理：
  - Draft 19 将 `expectation/dsl/emit_c/npu_demo/arch/launch.py` 中 `dma.copy` 展开的 `slice(ctx, ...)` layout 正向 `CHECK` 从显式 `Vector(...)` 改为 braced-init `{...}`，并新增 `Vector(` forbidden snippet。
  - Draft 19 更新 manifest/hash、subagent 收敛结论、守护最终检验、计划书入档验收和下发前置。
- 本地自检：
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile expectation/dsl/emit_c/npu_demo/arch/launch.py`：通过。
  - `rg -n "CHECK[^\\n]*Vector\\(" expectation/dsl/emit_c/npu_demo/dma/{alloc,fill,copy,slice,deslice,store,load,transpose,broadcast}.py expectation/dsl/emit_c/npu_demo/kernel/{binary_elewise,binary_compare,exp,select,reduce,matmul,img2col}.py expectation/dsl/emit_c/npu_demo/arch/launch.py expectation/dsl/gen_kernel/context_first_source.py expectation/include/npu_demo/launch_block_grid.py`：无命中；正向 `CHECK` 不再要求显式 `Vector(` layout。
  - `rg -n "Vector\\(" <19 scope files>`：仅命中 `forbidden_snippets` 中的 `Vector(`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.arch.launch`：execute 前红灯；失败点为旧实现未生成 `template <typename Context>` / `Context& ctx`、helper 未前置 `ctx`、旧 `npu_demo::launch(body, args...)`，未见语法或导入错误。
- Draft 19 strict review 结果：
  - Godel `019e97ee-d6ac-79c2-a42e-f09a912136e3`：远端 `503 Service Unavailable` 中断，无有效结论，不得视为通过。
  - Dirac `019e98d4-e7be-7de2-b91a-d2f8a958a0ea`：通过；核对 Draft 19 状态、manifest/hash、`arch/launch.py` braced-init 修复、全 scope 正向 `CHECK...Vector(` 无命中、public API 仍为 `const Vector&`，无阻断、无最小需改项、无待确认项。
  - Aristotle `019e98e5-ad0f-7922-b5ec-10af22f1ebe5`：通过；核对 Draft 19 状态、manifest/hash、`arch/launch.py` 修复、`Vector(` 仅在 `forbidden_snippets` 中；提出残余风险：scope 外 `expectation/dsl/emit_c/npu_demo/arch/get_dynamic_memory.py` 仍锁旧 launch / layout 口径。
- 状态：Draft 19 strict review 已由 Dirac 与 Aristotle 双通过，但其残余风险触发 Draft 20 scope 扩展；Draft 19 不得作为当前下发依据，不得创建 execute。

### 收敛轮次 20：arch 叶子合同 scope 扩展

- 审阅对象：Draft 20 正文、Draft 19 strict review 残余风险、`expectation/dsl/emit_c/npu_demo/arch/{get_block_id,get_thread_id,get_thread_num,get_dynamic_memory,launch}.py`、当前 23 个 expectation scope 文件 manifest/hash。
- 输入标准包：根 `AGENTS.md`、当前架构师只维护计划与 expectation 的用户指令、`agents/standard/计划书标准.md`、`agents/standard/审查规范.md`、`agents/standard/spec文件规范.md`、`agents/standard/expectation任务规则.md`、Draft 20 全文、Draft 19 strict review 结论、用户关于 `thread_id()` 这一类 Arch free helper 不需要变的确认、用户关于 braced-init 构造 `Vector` 的纠偏、禁止修改面和必过验收命令。
- 严格通过口径：npu_demo emit_c arch 目录中已发现的 5 个叶子合同必须同口径：完整 launch module 的 body / wrapper 为 context-first，wrapper 显式 `npu_demo::KernelContext ctx` 并调用 `npu_demo::launch<...>(ctx, body<npu_demo::KernelContext>, args...)`；Arch 查询 / 动态内存 free helper 保持 `npu_demo::block_id()`、`npu_demo::thread_id()`、`npu_demo::thread_num()`、`npu_demo::get_dynamic_memory<Space>()`，不得改成 `ctx.*`；`dma.copy` 展开的 layout 实参必须为 braced-init `{static_cast<long long>(...)}`，public API 仍为 `const Vector&`；23 个 scope 文件 manifest/hash、验收命令、完成态、文本门禁和下发前置必须一致；无阻断、无最小需改项、无待确认项；不得创建 execute。
- 发现问题：Draft 20 strict review 已发起并收敛；Draft 19 通过结论只作历史证据，不能作为当前下发依据。
- 主线处理：
  - Draft 20 将 `expectation/dsl/emit_c/npu_demo/arch/{get_block_id,get_thread_id,get_thread_num,get_dynamic_memory}.py` 纳入授权 scope，与既有 `arch/launch.py` 一起锁定 context-first body / wrapper。
  - Draft 20 保留 Arch free helper 口径：`npu_demo::block_id()`、`npu_demo::thread_id()`、`npu_demo::thread_num()`、`npu_demo::get_dynamic_memory<Space>()` 均为正向文本。
  - Draft 20 将 `arch/get_dynamic_memory.py` 中 `dma.copy` 展开的 `slice` 收为 `slice(ctx, ...)`，layout 收为 braced-init，并新增 `Vector(` forbidden snippet。
  - Draft 20 更新授权 scope、manifest/hash、完成态、S3 合同验收、总体验收设计、subagent 收敛结论、守护最终检验、计划书入档验收和下发前置。
- 本地自检：
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile <23 scope files>`：通过。
  - 逐一运行 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m <module>`，其中 `<module>` 覆盖 9 个 DMA 叶子、7 个 Kernel 叶子、5 个 Arch 叶子、`expectation.dsl.emit_c.npu_demo.arch` 目录聚合入口、`expectation.dsl.gen_kernel.context_first_source` 与 `expectation.include.npu_demo.launch_block_grid`：均为 execute 前红灯；失败点为旧实现仍缺 `template <typename Context>` / `Context& ctx`、helper 未传 `ctx` 或旧 `npu_demo::launch(body, args...)`，未见 `SyntaxError`、`ImportError`、`ModuleNotFoundError` 或 `NameError`。
  - `rg -n "CHECK[^\\n]*Vector\\(" <23 scope files>`：无命中；正向 `CHECK` 不再要求显式 `Vector(` layout。
  - `rg -n "Vector\\(" <23 scope files>`：仅命中 `forbidden_snippets` / forbidden 文本中的 `Vector(`。
  - `sha256sum <23 scope files> | sha256sum`：`56151ecb9cfe98a7c1492637d14cc3297924104739a1d0dba0e1fedcefb7847c`。
- Draft 20 strict review 结果：
  - Aristotle `019e98e5-ad0f-7922-b5ec-10af22f1ebe5`：通过；核对 Draft 20 标题、23 文件 scope、5 个 arch 叶子、完成态、S3/S5、总体验收、文本门禁、下发前置、manifest/hash `56151ecb9cfe98a7c1492637d14cc3297924104739a1d0dba0e1fedcefb7847c`、Arch free helper、braced-init layout 与 24 个 expectation 入口 execute 前红灯，均无阻断、无最小需改项、无待确认项。
  - Dirac `019e98d4-e7be-7de2-b91a-d2f8a958a0ea`：通过；核对标准包、Draft 20 状态、23 scope 与 5 个 arch 叶子一致性、`Vector(` 门禁、public API 仍为 `const Vector&`、expectation 红灯非脚本错误，均无阻断、无最小需改项、无待确认项。
  - Godel `019e97ee-d6ac-79c2-a42e-f09a912136e3`：通过；复现 23 文件明细 hash 与聚合 hash，核对 5 个 arch 叶子 context-first body / wrapper、Arch free helper、braced-init layout、24 入口 `red_assert=24 script_errors=0`，均无阻断、无最小需改项、无待确认项；其记录中提到 `kernel.img2col` 一次 `exit=139` 已通过单独复跑、连续 5 次复跑和完整 24 入口复跑证明未复现。
- 状态：Draft 20 subagent strict review 已收敛；无阻断、无最小需改项、无待确认项。进入守护最终检验前置；守护通过前不得创建 execute。

### 收敛轮次 21：launch name 模板参数用户纠偏

- 审阅对象：Draft 21 正文、用户 2026-06-06 关于 `launch<name>(ctx, args...)` 与 `arch_launch_body<npu_demo::KernelContext>` 不要模板的纠偏、`expectation/dsl/emit_c/npu_demo/arch/{get_block_id,get_thread_id,get_thread_num,get_dynamic_memory,launch}.py`、`expectation/dsl/gen_kernel/context_first_source.py`、`expectation/include/npu_demo/launch_block_grid.py`。
- 输入标准包：根 `AGENTS.md`、当前架构师只维护计划与 expectation 的用户指令、`agents/standard/计划书标准.md`、`agents/standard/审查规范.md`、`agents/standard/spec文件规范.md`、`agents/standard/expectation任务规则.md`、Draft 21 全文、Draft 20 strict review 与守护通过历史结论、用户最新 launch 纠偏、禁止修改面和必过验收命令。
- 严格通过口径：当前正向合同必须使用 `npu_demo::launch<block, thread, subthread, shared_memory_size, name>(ctx, args...)`；不得把 name 作为普通实参；不得出现 `body<npu_demo::KernelContext>` 作为 launch name；npu_demo generated / emit_c body 不得生成 `template <typename Context>`，dtype body 只保留业务 dtype 模板；Arch free helper 与 Dma braced-init 口径不回退；23 个 scope 文件 manifest/hash、验收命令、完成态、文本门禁和下发前置必须一致；无阻断、无最小需改项、无待确认项；不得创建 execute。
- 发现问题：Draft 20 strict review 与守护通过结论已被本轮用户纠偏 supersede，只作历史证据，不得作为当前下发依据；Draft 21 strict review 早轮反馈中的计划目标旧 `Context` 模板表述和 S5 regex 误伤问题已由当前正文收口。
- 主线处理：
  - Draft 21 将 launch public API 从 `launch<...>(ctx, callee, args...)` 改为 `launch<..., name>(ctx, args...)`。
  - Draft 21 将 `arch/{get_block_id,get_thread_id,get_thread_num,get_dynamic_memory,launch}.py` 的正向 launch CHECK 改为裸 body name，并把 `launch<...>(ctx, body, ...)` 与 `launch<...>(body, ctx, ...)` 加入 forbidden。
  - Draft 21 将 `context_first_source.py` 的 generated body 从 `template <typename Context>` 收为 `npu_demo::KernelContext& ctx`；dtype case 只保留 `template <typename TData>`；launch name 使用裸 body 或 dtype specialization。
  - Draft 21 将 `launch_block_grid.py` 的手写编译合同改为 `npu_demo::launch<kBlocks, kThreads, 1, 0, kernel_body>(ctx, args...)`。
- 本地自检：
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile expectation/dsl/emit_c/npu_demo/arch/launch.py expectation/dsl/emit_c/npu_demo/arch/get_block_id.py expectation/dsl/emit_c/npu_demo/arch/get_thread_id.py expectation/dsl/emit_c/npu_demo/arch/get_thread_num.py expectation/dsl/emit_c/npu_demo/arch/get_dynamic_memory.py expectation/dsl/gen_kernel/context_first_source.py expectation/include/npu_demo/launch_block_grid.py`：通过。
  - `rg -n "CHECK[^\n]*launch<[^\n]*<npu_demo::KernelContext" expectation/dsl/emit_c/npu_demo/arch expectation/dsl/gen_kernel/context_first_source.py expectation/include/npu_demo/launch_block_grid.py`：无正向 CHECK 命中；仅 forbidden / CHECK-NOT 文本保留旧错误形态。
  - 逐一运行 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m <module>`，其中 `<module>` 为 `expectation.dsl.emit_c.npu_demo.arch.launch`、`expectation.dsl.emit_c.npu_demo.arch.get_block_id`、`expectation.dsl.emit_c.npu_demo.arch.get_thread_id`、`expectation.dsl.emit_c.npu_demo.arch.get_thread_num`、`expectation.dsl.emit_c.npu_demo.arch.get_dynamic_memory`、`expectation.dsl.gen_kernel.context_first_source` 与 `expectation.include.npu_demo.launch_block_grid`：均为 execute 前红灯 `exit=1`；`SyntaxError`、`ImportError`、`ModuleNotFoundError`、`NameError` 均无命中。
- Draft 21 strict review 结果：
  - Godel `019e97ee-d6ac-79c2-a42e-f09a912136e3`：通过；复核计划目标已改为 `npu_demo::KernelContext& ctx` 普通函数 / dtype-only 模板，S5 文本门禁已同步总体验收门禁，23 文件聚合 hash 复现为 `143cb25285f1a911047349a0c753003eef4cf485a45023635105e84083849097`，无阻断、无最小需改项、无待确认项。
  - Dirac `019e98d4-e7be-7de2-b91a-d2f8a958a0ea`：通过；核对 Draft 21 状态、目标 API、任务目标、完成态、S1-S3、文本门禁、7 个 expectation 正向 / 负向口径、Arch free helper、Dma braced-init、23 文件 manifest/hash 与 7 入口红灯基线，均无阻断、无最小需改项、无待确认项。
  - Aristotle `019e98e5-ad0f-7922-b5ec-10af22f1ebe5`：复审通过；上一轮提出的计划目标旧 `Context` 模板表述和 S5 regex 误伤问题均已收口，当前文本明确 `args...` 可为普通标识符，均无阻断、无最小需改项、无待确认项。
- 状态：Draft 21 已完成主线修订、本地自检、subagent strict review 与守护最终检验；该允许下发结论已被 Draft 22 用户 `KernelContext` member API 纠偏 supersede，不再作为当前下发依据。

### 收敛轮次 22：KernelContext runtime member API 用户纠偏

- 审阅对象：Draft 22 正文、用户 2026-06-06 关于 `KernelContext` 不要 runtime member 函数的纠偏、`expectation/dsl/emit_c/npu_demo/arch/{get_block_id,get_thread_id,get_thread_num,get_dynamic_memory}.py`、`expectation/dsl/gen_kernel/context_first_source.py`、`expectation/include/npu_demo/launch_block_grid.py`。
- 输入标准包：根 `AGENTS.md`、当前架构师只维护计划与 expectation 的用户指令、`agents/standard/计划书标准.md`、`agents/standard/审查规范.md`、`agents/standard/spec文件规范.md`、`agents/standard/expectation任务规则.md`、Draft 22 全文、Draft 21 strict review 与守护通过历史结论、用户最新 `KernelContext` member API 纠偏、禁止修改面和必过验收命令。
- 严格通过口径：`npu_demo::KernelContext& ctx` 仍作为 launch/body/helper context 对象传递；`KernelContext` 与 `npu_demo::KernelContext` 不再公开 `block_id()`、`block_num()`、`thread_id()`、`thread_num()`、`subthread_id()`、`subthread_num()`、`barrier(...)`、`get_dynamic_memory<...>()` runtime member API；Arch 查询、同步与动态内存只能通过 free helper；launch/name、dtype-only body、Arch free helper、Dma braced-init 与 Vector public API 口径不回退；23 个 scope 文件 manifest/hash、验收命令、完成态、文本门禁和下发前置必须一致；无阻断、无最小需改项、无待确认项；不得创建 execute。
- 发现问题：Draft 21 strict review 与守护通过结论已被本轮用户纠偏 supersede，只作历史证据，不得作为当前下发依据；Draft 22 strict review 已收敛，未发现阻断、最小需改项或待确认项。
- 主线处理：
  - Draft 22 将 include/api 全局 `KernelContext` 与 `npu_demo::KernelContext` 的 runtime member API 从目标公开 API 删除；`npu_demo::KernelContext()` 默认构造仅作为 wrapper 物化 context 保留。
  - Draft 22 将 `expectation/include/npu_demo/launch_block_grid.py` 的手写 body 改为 `(void)ctx;` 并通过 `npu_demo::block_id()`、`npu_demo::thread_id()`、`npu_demo::thread_num()` 读取运行时视图，不再调用 `ctx.block_id()` / `ctx.thread_id()` / `ctx.thread_num()` / `ctx.block_num()`。
  - Draft 22 扩展 `context_first_source.py` 与 emit_c Arch 叶子 forbidden / CHECK-NOT，阻断 `ctx.block_id()`、`ctx.block_num()`、`ctx.thread_id()`、`ctx.thread_num()`、`ctx.subthread_id()`、`ctx.subthread_num()`、`ctx.barrier(...)`、`ctx.get_dynamic_memory...`。
- 本地自检：
  - `PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY' ... compile(...) ... PY` 覆盖 `arch/{launch,get_block_id,get_thread_id,get_thread_num,get_dynamic_memory}.py`、`context_first_source.py` 与 `launch_block_grid.py`：通过，`syntax_ok 7`。
  - `sha256sum <23 scope files> | sha256sum`：复现 Draft 22 结束 manifest 聚合 hash `4fdf05ef7ac6d2b90f689f288e08848c701a1f7daa5f98b07025ca0e82cd1cd5`。
  - 逐一运行 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m <module>`，其中 `<module>` 为 `expectation.dsl.emit_c.npu_demo.arch.launch`、`expectation.dsl.emit_c.npu_demo.arch.get_block_id`、`expectation.dsl.emit_c.npu_demo.arch.get_thread_id`、`expectation.dsl.emit_c.npu_demo.arch.get_thread_num`、`expectation.dsl.emit_c.npu_demo.arch.get_dynamic_memory`、`expectation.dsl.gen_kernel.context_first_source` 与 `expectation.include.npu_demo.launch_block_grid`：均为 execute 前红灯 `exit=1`；`SyntaxError`、`ImportError`、`ModuleNotFoundError`、`NameError` 均无命中。
- Draft 22 strict review 结果：
  - Dirac `019e98d4-e7be-7de2-b91a-d2f8a958a0ea`：通过；核对 Draft 22 状态、下发前置、公开 API 索引、6 个变更 expectation 正向 / 负向口径、launch/name、body、Arch free helper、Dma braced-init、Vector public API、23 文件 manifest/hash 与 7 入口红灯基线，均无阻断、无最小需改项、无待确认项。
  - Aristotle `019e98e5-ad0f-7922-b5ec-10af22f1ebe5`：通过；核对 Draft 22 已 supersede Draft 21、`KernelContext` runtime member API 删除、6 个变更 expectation、23 文件 manifest/hash 与 24 个 expectation 入口预期红灯，均无阻断、无最小需改项、无待确认项。
  - Godel `019e97ee-d6ac-79c2-a42e-f09a912136e3`：通过；只读检查标准包、Draft 22 正文与相关 expectation，复核 `KernelContext` / `npu_demo::KernelContext` 不再公开 runtime member API、`npu_demo::KernelContext()` 仅作为 wrapper 物化 context 保留、`ctx.*` runtime member 仅出现在 `CHECK-NOT` / `forbidden_snippets`，23 文件聚合 hash 复现为 `4fdf05ef7ac6d2b90f689f288e08848c701a1f7daa5f98b07025ca0e82cd1cd5`，无阻断、无最小需改项、无待确认项。
- 状态：Draft 22 已完成主线修订、本地自检、subagent strict review 与守护最终检验；曾允许管理员创建唯一计划级 execute：`context-first-kernel-cost-shared-code`，但该结论已被 Draft 24 用户 include/api 宏分发纠偏 supersede。

### 收敛轮次 23：include/api 宏分发用户纠偏

- 审阅对象：Draft 24 正文、用户 2026-06-06 关于 `include/api` 是 emitc 生成调用函数且 API 根据宏分发 kernel / cost 实现的纠偏、23 个既有 expectation scope。
- 输入标准包：根 `AGENTS.md`、当前架构师只维护计划与 expectation 的用户指令、Draft 22 strict review 与守护通过历史结论、用户最新 include/api 宏分发纠偏、禁止修改面和必过验收命令。
- 严格通过口径：generated source / emitc 外层只调用 `include/api` public helper 的 context-first 形态；API 层根据目标宏与 `Context` 类型实例化分发到 `include/npu_demo/kernel` 与 `include/npu_demo/cost` 实现；generated source 主链路不得直接调用 `_cost_*`、`tuner.cost` 或 `cost::` helper；不得在未确认具体公开宏名、公开 cost context 类名或删除清单前通过 strict review / 守护终检 / execute 下发。
- 发现问题：Draft 22 strict review 与守护通过结论已被本轮用户纠偏 supersede，只作历史证据；Draft 23 的直接删除全部 cost 旧链路方向已被用户更正 supersede，不能作为当前下发依据。
- 主线处理：
  - Draft 24 将当前状态、用户确认来源、API 索引、任务目标、待确认项、计划目标、公开 API 设计、完成态、S1-S5、验收设计与下发前置改为 `include/api` 宏分发口径。
  - Draft 24 保留 23 个 expectation scope 不变；这些 expectation 已锁定 generated source 只生成 `op(ctx, ...)` / `op<...>(ctx, ...)` 并禁止 `_cost_*`、`tuner.cost` 与 `cost::` 正向文本，符合“外层调用 API 函数”的生成侧口径。
  - Draft 24 明确未确认项：具体公开宏名、公开 cost context 类名、以及是否物理删除 `LaunchKernelCostFuncPass`、`dsl_cost_run`、`dsl_run`、pass registry、旧 `npu_demo::cost::*` / `CostKind` surface。
- 本地自检：
  - `git diff --check -- ARCHITECTURE/plan/context_first_kernel_cost_shared_code.md`：通过。
  - `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile <23 scope files>`：通过，`syntax_ok 23`。
  - `sha256sum <23 scope files> | sha256sum`：仍为 Draft 22 结束 manifest 聚合 hash `4fdf05ef7ac6d2b90f689f288e08848c701a1f7daa5f98b07025ca0e82cd1cd5`，证明 Draft 24 未修改 expectation scope。
  - 逐一运行 7 个重点入口 `expectation.dsl.emit_c.npu_demo.arch.{launch,get_block_id,get_thread_id,get_thread_num,get_dynamic_memory}`、`expectation.dsl.gen_kernel.context_first_source`、`expectation.include.npu_demo.launch_block_grid`：均为 execute 前红灯，`red_assert=7 script_errors=0 other=0`。
  - stale dispatch / deletion wording scan：clear。
  - stale standalone cost wording scan：clear。
  - `git status --short --untracked-files=all --ignored -- .skills agents/standard AGENTS.md TODO.md DONE.md`：仅显示 `!! DONE.md` 与 `!! TODO.md`，未显示 `.skills`、`agents/standard` 或 `AGENTS.md` 改动。
- 状态：Draft 24 已完成主线文字修订但存在待确认项；尚未重新 subagent strict review，尚未守护最终检验，不得创建 execute。

### 收敛轮次 24：Draft 25 目标宏 / pass 删除 / dsl_cost_run 保留确认

- 审阅对象：Draft 25 正文、用户 2026-06-06 关于目标宏编译期边界、`LaunchKernelCostFuncPass` 直接删除、`dsl_cost_run` 保留并后续改为 cost-kernel-only 语义的确认、23 个既有 expectation scope。
- 输入标准包：根 `AGENTS.md`、当前架构师只维护计划与 expectation 的用户指令、Draft 24 本地自检结果、用户最新目标宏 / pass / tool 确认、禁止修改面和必过验收命令。
- 严格通过口径：Draft 25 顶部状态、待确认项、API 索引、任务目标、S1-S5、验收设计与下发前置必须同口径；目标宏只能作为编译期 target 选择机制；`LaunchKernelCostFuncPass` 相关链路按用户确认删除；`dsl_cost_run` 保留入口和参数签名，最终 cost-kernel-only 语义只作后续计划方向；generated source 外层只调用 `include/api` context-first helper；API 内部按编译期 target 宏与 context 类型分发；不得新增未确认 public 宏名或 `CostContext` 类名；无阻断、无最小需改项、无待确认项后才可守护终验。
- Draft 25 首轮 strict review 结果：
  - Descartes / Dirac `019e9b0e-10f6-76b2-b613-c26e3d16e86d`：不通过；阻断项为收敛 / 守护 / 下发段落仍残留 Draft 24 待确认状态，以及 `目标 API 全量索引` 未列出 emitc-facing `include/api` DMA / Kernel public helper。
  - Kuhn / Aristotle `019e9b0e-4bcc-7d50-b9a9-6e7c7232b399`：不通过；阻断项为 `subagent 收敛结论`、`守护最终检验`、`计划书入档验收`、`下发前置` 仍停在 Draft 24；最小需改项为 S1 模块范围漏列 `spec/tools/dsl_cost_run.md`。
  - Maxwell / Godel `019e9b0e-74d6-7c43-b047-972e16fffc82`：不通过；阻断项为收敛 / 守护 / 下发段落仍残留 Draft 24 待确认状态；可选建议为 S4 中 `kernel_gen/passes/tuning/__init__.py` 表述改成移除 pass 导出，避免误删整个 package init。
- 主线处理：
  - Draft 25 补齐 `目标 API 全量索引` 中 include/api emitc-facing DMA / Kernel helper 的未限定名 context-first 签名，并在 `公开 API 全量变更记录` 中写明旧 no-ctx 未限定名 helper 破坏式替换为 `Context& ctx` 首参。
  - Draft 25 将 S1 模块范围补入 `spec/tools/dsl_cost_run.md`。
  - Draft 25 将 S4 删除步骤收口为删除 `kernel_gen/passes/tuning/launch_kernel_cost_func.py`、移除 `kernel_gen/passes/tuning/__init__.py` 中的 `launch_kernel_cost_func` 导出、删除 registry / pipeline 中的 `launch-kernel-cost-func` 注册与自动插入。
  - Draft 25 将 subagent 收敛结论、守护最终检验、计划书入档验收与下发前置从 Draft 24 待确认状态改为 Draft 25 当前状态。
- 本地自检：
  - `git diff --check -- ARCHITECTURE/plan/context_first_kernel_cost_shared_code.md`：通过。
  - `PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY' ... compile(...) ... PY` 覆盖 23 个 expectation scope：通过，`syntax_ok 23`。
  - `sha256sum <23 scope files> | sha256sum`：仍为 Draft 22 结束 manifest 聚合 hash `4fdf05ef7ac6d2b90f689f288e08848c701a1f7daa5f98b07025ca0e82cd1cd5`，证明 Draft 25 未修改 expectation scope。
  - 逐一运行 7 个重点入口 `expectation.dsl.emit_c.npu_demo.arch.{launch,get_block_id,get_thread_id,get_thread_num,get_dynamic_memory}`、`expectation.dsl.gen_kernel.context_first_source`、`expectation.include.npu_demo.launch_block_grid`：均为 execute 前红灯，`red_assert=7 script_errors=0 other=0`。
  - `git status --short --untracked-files=all --ignored -- <计划文件 + 23 scope files>`：仅显示计划文件与 23 个 expectation scope 为 `!!` ignored，未出现 scope 外 expectation。
  - `git status --short --untracked-files=all --ignored -- .skills agents/standard AGENTS.md TODO.md DONE.md`：仅显示 `!! DONE.md` 与 `!! TODO.md`，未显示 `.skills`、`agents/standard` 或 `AGENTS.md` 改动。
- Draft 25 strict review 复审结果：
  - Descartes / Dirac `019e9b0e-10f6-76b2-b613-c26e3d16e86d`：通过；无阻断、无最小需改项、无待确认项；复核 Draft 24 残留清零、include/api emitc-facing helper 索引补齐、`LaunchKernelCostFuncPass` 删除、`dsl_cost_run` 保留、目标宏不公开具体名和本地自检记录均一致。
  - Kuhn / Aristotle `019e9b0e-4bcc-7d50-b9a9-6e7c7232b399`：通过；无阻断、无最小需改项、无待确认项；复核 S1 已补 `spec/tools/dsl_cost_run.md`，S4 不误删整个 `__init__.py`，`rg` 仍只作为文本门禁，`expectation/` execute / review / archive_acceptance 只读。
  - Maxwell / Godel `019e9b0e-74d6-7c43-b047-972e16fffc82`：通过；无阻断、无最小需改项、无待确认项；复核收敛记录、守护最终检验、archive 当前结论和下发前置均指向 Draft 25 当前状态，未引入具体公开宏名或 public `CostContext`。
- 状态：Draft 25 strict review 复审已收敛且守护最终检验曾通过；但该允许下发结论已被 2026-06-06 用户关于 host 入口函数不接收 `ctx`、入口函数内部创建 `ctx` 后传给 kernel / launch 的确认 supersede，只作历史证据，不再作为当前下发依据。

### 收敛轮次 25：Draft 26 host 入口无 ctx 用户确认

- 审阅对象：Draft 26 正文、用户 2026-06-06 关于生成 func 时 host 入口函数签名没有 `ctx`、在 host 入口函数内部创建 `ctx` 后传给 kernel / launch 的确认、23 个既有 expectation scope。
- 输入标准包：根 `AGENTS.md`、当前架构师只维护计划与 expectation 的用户指令、Draft 25 strict review 与守护通过历史结论、用户最新 host 入口 ABI 确认、禁止修改面和必过验收命令。
- 严格通过口径：host 入口 / wrapper 公开签名不得新增或接收 `ctx`，只接收业务参数；host 入口函数体内必须创建 `npu_demo::KernelContext ctx;` 并传给 `npu_demo::launch<..., body>(ctx, args...)` 或 dtype 场景 `npu_demo::launch<..., body<T...>>(ctx, args...)`；`ctx` 仍作为 launch/body/helper 链路首参传递；launch/name、include/api helper 分发、Arch free helper、`KernelContext` 无 runtime member API、`LaunchKernelCostFuncPass` 删除与 `dsl_cost_run` 保留口径不得回退；无阻断、无最小需改项、无待确认项后才可守护终验。
- 发现问题：Draft 25 strict review 与守护最终检验通过结论已被本轮用户确认 supersede，只作历史证据，不能作为当前下发依据。
- 主线处理：
  - Draft 26 将当前状态、任务目标、计划目标、公开 API 设计、generated body / emit_c 合同、完成态、S1/S3 执行步骤、验收设计、subagent 收敛结论、守护最终检验、计划书入档验收与下发前置同步到“host 入口签名无 `ctx`、函数体内创建 `npu_demo::KernelContext ctx;` 后下传”的口径。
  - Draft 26 不修改 expectation scope；既有 23 个 expectation 仍锁定 body / launch / helper 链路 context-first，且 S3 / 文本门禁新增 host ABI 人工核对要求，防止把 `ctx` 暴露为 host 入口公开参数。
- 本地自检：
  - `git diff --check -- ARCHITECTURE/plan/context_first_kernel_cost_shared_code.md`：通过。
  - `PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY' ... compile(...) ... PY` 覆盖 23 个 expectation scope：通过，`syntax_ok 23`。
  - `sha256sum <23 scope files> | sha256sum`：仍为 Draft 22 结束 manifest 聚合 hash `4fdf05ef7ac6d2b90f689f288e08848c701a1f7daa5f98b07025ca0e82cd1cd5`，证明 Draft 26 未修改 expectation scope。
  - 逐一运行 7 个重点入口 `expectation.dsl.emit_c.npu_demo.arch.{launch,get_block_id,get_thread_id,get_thread_num,get_dynamic_memory}`、`expectation.dsl.gen_kernel.context_first_source`、`expectation.include.npu_demo.launch_block_grid`：均为 execute 前红灯，`red_assert=7 script_errors=0 other=0 pass=0`。
  - 逐一运行完整 24 个合同入口：均为 execute 前红灯，`red_assert=24 script_errors=0 other=0 pass=0`。
  - `git status --short --untracked-files=all --ignored -- <计划文件 + 23 scope files>`：仅显示计划文件与 23 个 expectation scope 为 `!!` ignored，未出现 scope 外 expectation。
  - `git status --short --untracked-files=all --ignored -- .skills agents/standard AGENTS.md TODO.md DONE.md`：仅显示 `!! DONE.md` 与 `!! TODO.md`，未显示 `.skills`、`agents/standard` 或 `AGENTS.md` 改动。
- Draft 26 strict review 结果：
  - Jason `019e9b33-0a4e-74b1-92bf-a480a699ec77`：通过；无阻断、无最小需改项、无待确认项；复核 Draft 26 标题、当前状态、任务目标、S1-S5、验收设计、subagent / 守护 / 下发前置，确认 Draft 25 通过结论已 supersede，Draft 26 不允许基于 Draft 25 创建 execute；复跑 `git diff --check`、23 scope 语法、manifest hash、7 / 24 expectation 红灯和敏感目录状态，均与 Draft 26 记录一致。
  - Mencius `019e9b33-0a84-7f52-bc04-e0f180b3af53`：通过；无阻断、无最小需改项、无待确认项；复核 Draft 25 下发结论已 supersede、host entry / wrapper ABI 无 `ctx` 且 body/helper 链路 context-first、include/api 宏分发与 `LaunchKernelCostFuncPass` / `dsl_cost_run` 口径未回退；复跑本地基线均与 Draft 26 记录一致。
  - Turing `019e9b33-0abe-71a2-a44b-6df822f6ce23`：通过；无阻断、无最小需改项、无待确认项；复核 Draft 26 顶部状态、用户确认、任务目标、计划目标、公开 API、完成态、S1/S3/S5、验收、subagent 收敛、守护、入档和下发前置同口径；验证 host entry / wrapper 无 `ctx`、launch name 在模板参数、include/api cost / kernel 分发、23 文件 hash与 7 / 24 expectation 红灯记录一致。
- Draft 26 守护最终检验结果：
  - 结论人：`守护最好的爱莉希雅`（subagent Nietzsche `019e9b3a-4a05-70e0-a559-a230271c67ca`）。
  - 结论：通过；无阻断、无最小需改项、无待确认项；未修改文件、未创建 `execute`、未通知管理员。
  - 关键验证：复核 Draft 25 的允许下发结论已在 Draft 26 中明确 supersede，当前有效收敛是 Jason / Mencius / Turing 三方 strict review 通过；host entry / wrapper 公开 ABI 无 `ctx`，函数体内创建 `npu_demo::KernelContext ctx;` 后下传，body/helper/launch 链路仍 context-first；launch name 在模板参数，普通实参为 `ctx, args...`；include/api helper、编译期 target 宏选择、npu_demo kernel/cost context 分发、Arch free helper、`KernelContext` 无 runtime member、Vector braced-init、`LaunchKernelCostFuncPass` 删除、`dsl_cost_run` 保留等口径未回退；未把具体公开宏名或 public `CostContext` 名称写成已确认；`git diff --check -- ARCHITECTURE/plan/context_first_kernel_cost_shared_code.md` 通过；23 个 expectation scope 文件语法检查 `syntax_ok 23`；23 文件 manifest hash 复现 `4fdf05ef7ac6d2b90f689f288e08848c701a1f7daa5f98b07025ca0e82cd1cd5`；完整 24 个合同入口 `red_assert=24 script_errors=0 other=0 pass=0`；敏感路径 `.skills`、`agents/standard`、`AGENTS.md` 无状态输出，`TODO.md` / `DONE.md` 仅为既有 ignored 状态。
- 状态：Draft 26 已完成主线文字修订、本地自检、三方 subagent strict review 与守护最终检验；无阻断、无最小需改项、无待确认项。允许管理员后续按流程创建唯一计划级 execute，当前未创建 execute。

### subagent 收敛结论

- 已发起审阅任务：Godel `019e97ee-d6ac-79c2-a42e-f09a912136e3`、Maxwell `019e97ef-03d4-73f2-8f6e-bab2e36eceb8`、James `019e98b3-a33e-7641-b7d0-d90ad2824049`、Dirac `019e98d4-e7be-7de2-b91a-d2f8a958a0ea`、Erdos `019e98d9-8bf0-70e0-b29a-7b17a8d9a6ad`、Aristotle `019e98e5-ad0f-7922-b5ec-10af22f1ebe5`、Descartes / Dirac `019e9b0e-10f6-76b2-b613-c26e3d16e86d`、Kuhn / Aristotle `019e9b0e-4bcc-7d50-b9a9-6e7c7232b399`、Maxwell / Godel `019e9b0e-74d6-7c43-b047-972e16fffc82`、Jason `019e9b33-0a4e-74b1-92bf-a480a699ec77`、Mencius `019e9b33-0a84-7f52-bc04-e0f180b3af53`、Turing `019e9b33-0abe-71a2-a44b-6df822f6ce23`；Maxwell 的 Draft 15 / Draft 16 / Draft 17 审阅均未产生有效通过结论，Draft 17 有效收敛结论以 Godel 与 James 双通过为准，Draft 18 strict review 有效收敛结论以 Godel 与 Dirac 双通过为准，Draft 19 有效 strict review 结论以 Dirac 与 Aristotle 双通过为准。
- 当前结论：Draft 1、Draft 2、Draft 3、Draft 4、Draft 5、Draft 6、Draft 7、Draft 9 与 Draft 10 均未收敛；Draft 8 与 Draft 11 strict review 曾由 Godel 与 Maxwell 双通过，但均已被后续用户澄清 supersede；Draft 12 strict review 中 Godel 通过、Maxwell 提出最小需改项，已由 Draft 13 修订；Draft 13 strict review 与守护最终检验曾通过，但已被 Draft 14 / Draft 15 用户 API 与 emit_c 叶子合同纠偏 supersede；Draft 15 strict review 中 Godel 提出 manifest/hash 最小需改项且 Maxwell 中断，已进入 Draft 16 修订；Draft 16 strict review 中 Godel 提出守护对象指向最小需改项且 Maxwell 空结论，已进入 Draft 17 修订；Draft 17 strict review 已由 Godel 与 James 双通过，但已被 Draft 18 用户 braced-init 实参纠偏 supersede；Draft 18 strict review 已由 Godel 与 Dirac 双通过，但守护最终检验被 Erdos 判定不通过；Draft 19 strict review 已由 Dirac 与 Aristotle 双通过，但被 Draft 20 scope 扩展 supersede；Draft 20 strict review 与守护最终检验曾通过，但已被 Draft 21 用户 launch/name 纠偏 supersede；Draft 21 strict review 与守护最终检验曾通过，但已被 Draft 22 用户 `KernelContext` member API 纠偏 supersede；Draft 22 strict review 已由 Dirac、Aristotle 与 Godel 收敛通过，但已被 Draft 24 include/api 宏分发纠偏 supersede；Draft 24 未通过 strict review 且已被 Draft 25 用户目标宏 / pass / tool 确认 supersede；Draft 25 strict review 复审已由 Descartes / Dirac、Kuhn / Aristotle、Maxwell / Godel 三方通过且守护最终检验曾通过，但已被 Draft 26 host 入口无 `ctx` 用户确认 supersede；Draft 26 strict review 已由 Jason、Mencius、Turing 三方通过，守护最终检验已由 Nietzsche 通过。
- 遗留项：当前无待用户确认项；Draft 26 strict review 与守护最终检验均无阻断、无最小需改项、无待确认项；未创建 execute。

### 守护最终检验

- 检验对象：Draft 8 / Draft 11 / Draft 13 / Draft 17 / Draft 18 / Draft 19 / Draft 20 / Draft 21 / Draft 22 / Draft 24 / Draft 25 历史正文、Draft 26 正文、`expectation/dsl/emit_c/npu_demo/dma/{alloc,fill,copy,slice,deslice,store,load,transpose,broadcast}.py`、`expectation/dsl/emit_c/npu_demo/kernel/{binary_elewise,binary_compare,exp,select,reduce,matmul,img2col}.py`、`expectation/dsl/emit_c/npu_demo/arch/{get_block_id,get_thread_id,get_thread_num,get_dynamic_memory,launch}.py`、`expectation/dsl/gen_kernel/context_first_source.py`、`expectation/include/npu_demo/launch_block_grid.py`。
- 检验范围：标准包、公开 API 确认来源、expectation 权限、禁止修改面、验收命令、小任务卡、待确认项收口、subagent 收敛结论。
- 必过门禁：subagent strict review 无阻断、无最小需改项、无待确认项；用户确认项已落位；敏感目录无越权。
- Draft 13 已运行当前命令：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma.copy`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.kernel.binary_elewise`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.arch.launch`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.gen_kernel.context_first_source`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.include.npu_demo.launch_block_grid`
  - `test ! -e expectation/dsl/emit_c/npu_demo/context_first_api.py && echo removed context_first_api.py`
  - `git status --short --untracked-files=all --ignored -- ARCHITECTURE/plan/context_first_kernel_cost_shared_code.md expectation/dsl/emit_c/npu_demo/dma/copy.py expectation/dsl/emit_c/npu_demo/kernel/binary_elewise.py expectation/dsl/emit_c/npu_demo/arch/launch.py expectation/dsl/gen_kernel/context_first_source.py expectation/include/npu_demo/launch_block_grid.py expectation/dsl/emit_c/npu_demo/context_first_api.py`
- Draft 13 红灯基线摘要：
  - `dma.copy` 两条 case 红，失败点仍是旧函数把 `%ctx` 发射为 `long long ctx` 且 helper 未传 `ctx`；src/dst dtype 已收为同型，符合公开 `slice(ctx, ...)` API。
  - `kernel.binary_elewise` 八条 case 均红，失败点为旧源码未生成 `template <typename Context>` / context-first helper。
  - `arch.launch` 一条 case 红，失败点为旧无 ctx body 与旧 `npu_demo::launch(body, args...)`。
  - `context_first_source` 三条 case 均红，失败点为旧无 ctx body / helper、旧 dtype template 顺序与旧 launch wrapper；Arch free helper 文本保持正向。
  - `launch_block_grid` 一条 case 红，编译失败点为旧 `launch(callee, args...)` 签名未接收显式 `ctx`。
- Draft 13 敏感目录核对：`ARCHITECTURE/plan/context_first_kernel_cost_shared_code.md`、`expectation/dsl/emit_c/npu_demo/dma/copy.py`、`expectation/dsl/emit_c/npu_demo/kernel/binary_elewise.py`、`expectation/dsl/emit_c/npu_demo/arch/launch.py`、`expectation/dsl/gen_kernel/context_first_source.py`、`expectation/include/npu_demo/launch_block_grid.py` 均为本轮授权范围内文件；`context_first_api.py` 已删除，`git status` 仅显示这些被 ignore 的合同资产。
- Draft 17 历史守护最终检验结果：
  - 结论人：`守护最好的爱莉希雅`（subagent `019e98bc-bcc3-7213-adf5-7c29b1792cc4`）。
  - 结论：通过；无发现项；未修改文件、未创建 execute、未通知管理员。
  - 验证基线：`/home/lfr/kernelcode_generate`，branch `main`，`HEAD=76e19a81`。
  - 关键验证：读取标准包与守护 prompt；复核 Draft 17 状态、用户确认来源、expectation scope/hash/status；`sha256sum <19 files> | sha256sum` 复现 `a5219f4a354a9add94cdda9be9f04ae3cdae2a0791e78abd8638f47bd56c4a5f`；不落盘 `compile(source, path, "exec")` 语法检查 19 个 scope 文件全部通过；运行 19 个 expectation 入口均为旧实现未传 `ctx` / 未生成 `Context& ctx` / 旧 `launch(callee, args...)` 的 execute 前合同红灯，未见 `SyntaxError`、`ImportError` 或 `ModuleNotFoundError`；文本门禁确认正向 expectation 片段要求 `Context& ctx`、`helper<...>(ctx, ...)` / `slice(ctx, ...)` 与 `Vector(...)`，旧 no-ctx 片段仅出现在 `forbidden_snippets` / `CHECK-NOT`。
  - 残余风险：无本次下发前守护阻断；execute 后仍必须把当前红灯 expectation 转绿。
- Draft 18 历史守护最终检验结果：
  - 结论人：`守护最好的爱莉希雅`（subagent Erdos `019e98d9-8bf0-70e0-b29a-7b17a8d9a6ad`）。
  - 结论：不通过；阻断项为 `expectation/dsl/emit_c/npu_demo/arch/launch.py:53` 正向 `CHECK-NEXT` 仍要求 `Vector(static_cast<long long>(...))` layout，违反用户 2026-06-06 braced-init 纠偏与 Draft 18 文本门禁。
  - 关键验证：复算 19 文件 manifest 聚合 hash 为 `0c47f13129fecb952e675312ae6d5da9092629cbe7366062b6c2efd42d4c503c`；19 个 expectation 入口均为 execute 前红灯，未见 `SyntaxError` / `ImportError` / `ModuleNotFoundError`；敏感目录未见 `.skills`、`agents/standard` 或 `AGENTS.md` 越权修改。
- Draft 19 当前守护最终检验结果：未执行；Draft 19 strict review 通过后被 Draft 20 scope 扩展 supersede，未进入守护最终检验。
- Draft 20 当前守护最终检验结果：
  - 结论人：`守护最好的爱莉希雅`（subagent Erdos `019e98d9-8bf0-70e0-b29a-7b17a8d9a6ad`）。
  - 结论：通过；无阻断、无最小需改项、无待确认项；未修改文件、未创建 execute、未通知管理员。
  - 关键验证：读取标准包与守护 prompt；核对 Draft 20 顶部状态、23 文件 scope、5 个 arch 叶子、授权 scope、manifest/hash、完成态、S3/S5、总体验收、文本门禁和下发前置均一致；复现 23 文件聚合 hash `56151ecb9cfe98a7c1492637d14cc3297924104739a1d0dba0e1fedcefb7847c`；不落盘语法检查 23 个 scope 文件全部通过；`CHECK...Vector(` 无命中，`Vector(` 仅命中 forbidden 文本；24 个合同入口结果为 `red_assert=24 script_errors=0 other=0`，红灯均为旧实现未 ctx 化、旧 helper 调用、旧 launch wrapper / 静态断言导致；敏感目录未见 `.skills`、`agents/standard`、`AGENTS.md` 越权。
  - 守护结论：曾允许管理员创建唯一计划级 execute：`context-first-kernel-cost-shared-code`；该结论已被后续用户纠偏 supersede。
- 当前效力：该通过结论已被 2026-06-06 用户 launch/name 纠偏 supersede，不再作为当前下发依据。
- Draft 21 当前守护最终检验结果：
  - 结论人：`守护最好的爱莉希雅`（subagent Erdos `019e98d9-8bf0-70e0-b29a-7b17a8d9a6ad`）。
  - 结论：通过；无阻断、无最小需改项、无待确认项；未修改文件、未创建 execute。
  - 关键验证：读取根 `AGENTS.md` 与 Draft 21 正文；核对顶部状态、下发前置和审阅记录均显示 Godel、Dirac、Aristotle 已通过 strict review，且守护通过前未创建 execute；复现 23 文件聚合 hash `143cb25285f1a911047349a0c753003eef4cf485a45023635105e84083849097`；7 个本轮改动 expectation 不落盘语法检查全部通过；7 个 expectation 入口结果为 `red_assert=7 script_errors=0 other=0`，红灯均为旧实现未生成 `npu_demo::KernelContext& ctx` body、旧 `npu_demo::launch(body, args...)` 或旧 launch API 编译失败；launch/name 文本门禁通过，旧 `body<npu_demo::KernelContext>`、`launch<...>(ctx, body, ...)`、`launch<...>(body, ctx, ...)` 仅在 `CHECK-NOT` / `forbidden_snippets` / 历史文本中出现；Arch free helper、Dma braced-init 与 `Vector` public API 口径未回退；S5 明确 `launch<...>(ctx, args...)` 中 `args...` 可为普通标识符，不误伤合法 `npu_demo::launch<..., body>(ctx, lhs, ...)`。
  - 守护结论：曾允许管理员创建唯一计划级 execute：`context-first-kernel-cost-shared-code`；该结论已被 Draft 22 用户 `KernelContext` member API 纠偏 supersede。
- Draft 22 当前守护最终检验结果：
  - 结论人：`守护最好的爱莉希雅`（subagent Erdos `019e98d9-8bf0-70e0-b29a-7b17a8d9a6ad`）。
  - 结论：通过；无阻断、无最小需改项、无待确认项；未修改文件、未创建 execute、未通知管理员。
  - 关键验证：重新核对 Draft 22 正文、用户 `KernelContext` runtime member API 纠偏、Dirac / Aristotle / Godel strict review 通过记录与下发前置；复现 23 文件聚合 hash `4fdf05ef7ac6d2b90f689f288e08848c701a1f7daa5f98b07025ca0e82cd1cd5`；7 个重点文件 no-bytecode `compile(...)` 语法检查通过 `syntax_ok 7`；7 个重点 expectation 入口结果为 `red_assert=7 script_errors=0 other=0`；226 条正向 `CHECK` 与 295 个 `expected_snippets` 字符串未发现 `ctx.block_id()` / `ctx.thread_id()` / `ctx.thread_num()` / `ctx.block_num()` / `ctx.subthread_*()` / `ctx.barrier(...)` / `ctx.get_dynamic_memory...` 正向要求，命中均在 `CHECK-NOT` / `forbidden_snippets`；`launch_block_grid.py` 正向 body 使用 `(void)ctx;`、`npu_demo::block_id()`、`npu_demo::thread_id()`、`npu_demo::thread_num()`；敏感目录未见 `.skills`、`agents/standard`、`AGENTS.md` 越权状态。
  - 守护结论：曾允许管理员创建唯一计划级 execute：`context-first-kernel-cost-shared-code`；该结论已被 Draft 24 用户 include/api 宏分发纠偏 supersede。
- Draft 24 当前守护最终检验结果：未执行；Draft 24 仍有待确认项的状态已被 Draft 25 用户目标宏 / pass / tool 确认 supersede，不再作为当前下发依据。
- Draft 25 当前守护最终检验结果：
  - 结论人：`守护最好的爱莉希雅`（subagent Epicurus `019e9b1b-cbd7-7312-86df-be31bef39353`）。
  - 结论：通过；无阻断、无最小需改项、无待确认项；未修改文件、未创建 `execute`、未通知管理员。
  - 关键验证：复核根 `AGENTS.md` 流程、Draft 25 三方 strict review 复审通过记录、用户目标宏 / pass / tool 最新确认、include/api emitc-facing helper 与 npu_demo 后端 helper API 索引、未公开具体宏名或 public `CostContext`；`git diff --check -- ARCHITECTURE/plan/context_first_kernel_cost_shared_code.md` 通过；23 个 expectation scope 不落盘语法检查 `syntax_ok 23`；23-file manifest hash 复现 `4fdf05ef7ac6d2b90f689f288e08848c701a1f7daa5f98b07025ca0e82cd1cd5`；7 个重点入口为 `red_assert=7 script_errors=0 other=0 pass=0`；完整 24 个合同入口为 `red_assert=24 script_errors=0 other=0 pass=0`；敏感路径 `.skills`、`agents/standard`、`AGENTS.md` 无状态输出，`TODO.md` / `DONE.md` 仅为既有 ignored 状态。
  - 守护结论：曾允许管理员后续按流程创建唯一计划级 execute：`context-first-kernel-cost-shared-code`；该结论已被 Draft 26 用户 host 入口无 `ctx` 确认 supersede，当前不再作为下发依据。
- Draft 26 当前守护最终检验结果：
  - 结论人：`守护最好的爱莉希雅`（subagent Nietzsche `019e9b3a-4a05-70e0-a559-a230271c67ca`）。
  - 结论：通过；无阻断、无最小需改项、无待确认项；未修改文件、未创建 `execute`、未通知管理员。
  - 关键验证：`git diff --check -- ARCHITECTURE/plan/context_first_kernel_cost_shared_code.md` 通过；23 个 expectation scope 文件语法检查 `syntax_ok 23`；23 文件 manifest hash 复现 `4fdf05ef7ac6d2b90f689f288e08848c701a1f7daa5f98b07025ca0e82cd1cd5`；完整 24 个合同入口 `red_assert=24 script_errors=0 other=0 pass=0`；敏感路径 `.skills`、`agents/standard`、`AGENTS.md` 无状态输出，`TODO.md` / `DONE.md` 仅为既有 ignored 状态；复核 Draft 26 host entry / wrapper ABI 无 `ctx`、body/helper/launch 链路 context-first、Draft 25 允许下发结论已 supersede。
- 结论：Draft 8、Draft 11、Draft 13 与 Draft 17 均为历史通过；Draft 18 strict review 曾通过但守护最终检验不通过；Draft 19 strict review 曾通过但已被 Draft 20 scope 扩展 supersede；Draft 20 strict review 与守护最终检验曾通过但已被 Draft 21 用户 launch/name 纠偏 supersede；Draft 21 strict review 与守护最终检验曾通过但已被 Draft 22 用户 `KernelContext` member API 纠偏 supersede；Draft 22 strict review 与守护最终检验曾通过但已被 Draft 24 用户 include/api 宏分发纠偏 supersede；Draft 23 直接删除全部 cost 旧链路的方向也已被 Draft 24 用户澄清 supersede；Draft 24 的待确认状态已被 Draft 25 用户确认 supersede；Draft 25 strict review 与守护最终检验曾通过但已被 Draft 26 用户 host 入口无 `ctx` 确认 supersede。这些历史结论不再作为当前下发依据。Draft 26 strict review 与守护最终检验均已通过，允许管理员后续按流程创建唯一计划级 `execute`：`context-first-kernel-cost-shared-code`，当前未创建 execute。

## 计划书入档验收 / 复验 / 修复复核记录

- 结论人：待 archive_acceptance 角色填写。
- 验证基线：待 execute 完成、review 通过后，以最新同步现场为准。
- 执行目录：`/home/lfr/kernelcode_generate` 或管理员下发 worktree。
- 合同验收摘要：必须运行本计划 `验收设计 / 合同验收` 中列出的 expectation。
- 当前结论：未执行；Draft 26 当前无待用户确认项，strict review 与守护最终检验均已通过；允许管理员后续按流程创建唯一计划级 `execute`。archive_acceptance 仍须在未来 execute 完成、review 通过后按本节填写。

## 计划目标

- 让 `npu_demo` generated device body 成为显式接收 `npu_demo::KernelContext& ctx` 的普通 C++ 函数；dtype 场景只保留业务 dtype 模板参数。
- 让 host 入口 / wrapper 公开签名不接收 `ctx`、只接收业务参数；在函数体内显式物化 `npu_demo::KernelContext ctx`，并使用 `npu_demo::launch<block, thread, subthread, shared_memory_size, body>(ctx, args...)` 或 `npu_demo::launch<..., body<T...>>(ctx, args...)`。
- 让 `emit_c` 的 DMA / Kernel helper 调用在旧生成形态基础上前置 `ctx`，即 `op<...>(ctx, args...)` 或既有无显式模板的 `op(ctx, args...)`；这些调用面归属 `include/api` public helper，API 层再按编译期 target 宏与 context 类型分发到 npu_demo kernel / cost 实现。
- 让 include DMA / Kernel public helper 签名统一为 context-first，不保留旧无 ctx DMA / Kernel public helper 或 launch fallback；Arch free helper 保留。
- 让 `_cost_*` sibling function、`tuner.cost` 与直接 `cost::` helper 调用不再属于 npu_demo generated source 主链路；新的 cost 行为由 API context 模板实例和后端 cost context 实现承接。
- 提供红灯 expectation 锁定新 generated source 合同，execute 完成后转绿。

## 非目标

- 不接入 `tuner.param` / `def params`。
- 不新增参数搜索、candidate enumeration、best params 存储或 host cost runner。
- 不把 kernel params 放入 context。
- 不在 context 中加入 target 字段。
- 不为 `cuda_sm86` 后端实施同类改造；本计划只收口 `npu_demo` generated source 和 include API。
- 不删除 `dsl_cost_run`、`dsl_run`、非 `LaunchKernelCostFuncPass` 的 pass registry 或旧 `npu_demo::cost::*` / `CostKind` 公开入口；`LaunchKernelCostFuncPass` 相关链路按用户确认直接删除。
- 不在本计划内把 `dsl_cost_run` 切到最终 cost-kernel-only 语义；该语义后续另立计划实现。
- 不修改 `.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md` 或未获授权的 `[immutable]` / `[immutable-file]` 文件。
- 除本计划架构阶段已由用户授权修改的 expectation leaf 以外，`expectation/` 合同资产保持只读；execute 阶段 `expectation/` 只读运行。
- 不跨文件调用当前文件之外的非公开 helper；测试不得直连非公开 helper。

## 当前基线

- `include/api/Dma.h` 与 `include/api/Kernel.h` 当前公开无 ctx helper，例如 `slice(target, source, ...)`、`add(out, lhs, rhs)`、`matmul(out, lhs, rhs, acc)`。
- `include/api/Arch.h` 与 `include/npu_demo/Arch.h` 当前公开 `block_id()`、`thread_id()`、`thread_num()`、`npu_demo::barrier(...)`、`get_dynamic_memory<Space>()`、`DynamicMemoryRef` 等无 ctx free surface；用户已确认 `thread_id()` 这一类不需要变，本轮保留。
- `include/api/Arch.h` 当前声明全局 `launch(Callable&& callee, Args&&... args)` 无 ctx public API；`include/npu_demo/Arch.h::launch` 当前同时支持 `callee(ctx, args...)` 与 `callee(args...)` fallback，静态断言文本包含 `args or npu_demo::KernelContext& plus args`。
- `include/api/Arch.h` 当前公开全局抽象 `class KernelContext` 及 `block_id` / `block_num` / `thread_id` / `thread_num` / `barrier` / `get_dynamic_memory` member API；`include/npu_demo/Arch.h` 当前公开具体 `class npu_demo::KernelContext`、默认构造 `npu_demo::KernelContext()`、runtime member API，且当前 public 区域存在带 `npu_demo::detail::LaunchBarrierState` 的 launch-runtime 构造泄漏；Draft 22 目标是删除这些 runtime member API，只保留 context 对象与 default construction。
- `kernel_gen/dsl/gen_kernel/kernel_emitter.py` 当前对 launch body 生成 `static void body(Memory<...>& ...)`，不把 `KernelContext` 暴露到 body 签名。
- `emit/npu_demo/arch` 当前把 thread / memory / barrier 查询发射为 `npu_demo::thread_id()`、`npu_demo::get_dynamic_memory<...>()`、`npu_demo::barrier(...)`。
- `emit/npu_demo/dma` 与 `emit/npu_demo/kernel` 当前生成 `slice(...)`、`deslice(...)`、`add<...>(...)`、`matmul<...>(...)` 等无 ctx helper 调用。
- `test/dsl/gen_kernel/test_gen_kernel.py` 当前锁定“不暴露 `npu_demo::KernelContext& ctx`”与 sibling cost function 输出，这与用户最新口径冲突。
- `include/api/cost/*` 与 `include/npu_demo/cost/*` 当前仍是独立 cost helper API；Draft 26 当前口径要求新 generated source 主链路不直接依赖这些 `cost::` helper，而是通过 `include/api` context-first helper 由编译期 target 宏 / context 类型分发到 npu_demo kernel 或 cost 实现。旧公开 cost surface 本轮不物理删除，除非执行中回到用户确认。
- 原地修改 expectation 红灯基线：
  - `emit_c-npu_demo-dma-copy-static/dynamic` 当前把 `%ctx` 发射为 `long long ctx`，且仍输出 `slice(out, source, ...)`。
  - `emit_c-npu_demo-kernel-binary-elewise-*` 当前仍输出旧显式模板 no-ctx helper 调用。
  - `emit_c-npu_demo-arch-{get_block_id,get_thread_id,get_thread_num,get_dynamic_memory,launch}` 当前均输出旧无 ctx body 与旧 `npu_demo::launch(body, args...)`；Arch free helper 文本本轮保留，`get_dynamic_memory` 同时锁定 `slice(ctx, ...)` 与 braced-init layout。
  - `context_first_launch_body` 当前输出旧无 ctx body / `slice(out, ...)` / `launch(body, ...)`。
  - `context_first_template_kernel_op` 当前输出 `template <typename TData>`、`add<GM, TData, TData>(...)`、`launch(body<TData>, ...)`。
  - `context_first_arch_ops` 当前仍缺 body / launch 的 context-first 形态；其中 `npu_demo::thread_id()`、`npu_demo::get_dynamic_memory<TSM>()`、`npu_demo::barrier(...)` 是本轮保留的正向口径。
  - `include-npu_demo-launch-block-grid-1` 当前按 context-first 合同编译失败，失败点为旧 `npu_demo::launch` public signature 未把 `ctx` 作为首参。
- 当前工作树存在与本计划无关的 dirty diff，execute / review 必须保护用户改动，不得回退。

## 方案比较与选型

- 不采用兼容桥方案：同时保留 `op(args...)` 和新增 `op(ctx, args...)`。
  - 原因：用户已明确要求“不要旧的兼容”；兼容桥会继续让 generated source 和测试依赖旧 API。
- 不采用本轮完整 tuner 方案：接入 `tuner.param`、搜索 params 并生成 host cost runner。
  - 原因：用户已明确当前不接入 `tuner.param`，只要求 kernel 和 cost 代码相同。
- 不采用本轮 `ctx` 携带 params / target 方案。
  - 原因：用户已明确 params 仍来自 kernel 参数，context 不携带 target。
- 不采用删除全部旧 cost surface 的方案。
  - 原因：用户已纠偏为 `include/api` 宏分发模型，并只确认 `LaunchKernelCostFuncPass` 相关链路直接删除；`dsl_cost_run` 与旧公开 cost surface 保留，额外删除需要回到用户确认。
- 采用方案：破坏式 context-first launch、DMA helper 与 Kernel helper API。
  - `device body` 生成普通 npu_demo kernel context 首参：`static void body(npu_demo::KernelContext& ctx, args...)`。
  - 若 body 还携带 memory dtype template 参数，只保留业务 dtype 参数，例如 `template <typename TData> static void body(npu_demo::KernelContext& ctx, ...)`；不得生成 `template <typename Context>` 或 `body<npu_demo::KernelContext, ...>`。
  - `wrapper` / host 入口公开签名不接收 `ctx`；函数体内物化 kernel-mode context，并调用 `npu_demo::launch<block, thread, subthread, shared_memory_size, body>(ctx, args...)`；dtype body 使用 `npu_demo::launch<..., body<TData>>(ctx, args...)`。
  - `arch` 查询 / 动态内存 / barrier 保持既有 free helper 口径，例如 `npu_demo::thread_id()`、`npu_demo::get_dynamic_memory<Space>()`、`npu_demo::barrier(...)`。
  - `dma/kernel` op 发射统一加 `ctx` 首参；旧生成形态已经显式模板化的 helper 保持模板参数并生成 `op<...>(ctx, args...)`，旧生成形态无显式模板的 helper 生成 `op(ctx, args...)`，不得残留 `op<...>(args...)` 或 `op(args...)` 的 no-ctx 调用。
  - `op(ctx, ...)` / `op<...>(ctx, ...)` 的 API 归属是 `include/api` public helper；API 层按编译期 target 宏选择后端实现，并通过 `Context` 类型实例化区分 kernel / cost。
  - `include/npu_demo/kernel` 承载 `npu_demo::KernelContext` 等 kernel context 实现，`include/npu_demo/cost` 承载 cost context 实现；generated source 不直接调用这两个实现层的私有 helper。
  - 无 ctx DMA / Kernel public helper 从 generated source、include/api API 列表、include/npu_demo 聚合 API 列表和相关测试中物理删除同名入口；Arch free helper 不删除。

## Demo 示例

```cpp
template <typename T>
static void demo_body(npu_demo::KernelContext& ctx, Memory<GM, T>& lhs, Memory<GM, T>& rhs, Memory<GM, T>& out) {
    slice(ctx, out, lhs, {0}, {out.get_shape(0)}, {1});
    add<GM, T, T>(ctx, out, lhs, rhs);
}

void run_kernel(Memory<MemorySpace::GM, float>& lhs, Memory<MemorySpace::GM, float>& rhs, Memory<MemorySpace::GM, float>& out) {
    npu_demo::KernelContext ctx;
    npu_demo::launch<2, 1, 1, 0, demo_body<float>>(ctx, lhs, rhs, out);
}
```

后续 host cost runner 不在本轮生成；本轮生成侧只调用 `include/api` helper。API 内部的 kernel / cost 实现由编译期 target 宏与 `Context` 类型实例化分发；若需要公开具体 cost context 类名或目标宏名，必须作为新增公开 API 待确认项停止推进。

## 公开 API 设计

### `launch` callee 合同

- `npu_demo::launch<block, thread, subthread, shared_memory_size, name>(ctx, args...)` 是 host 入口函数内部调用的 launch public API；它接收 `ctx`，但 generated host 入口 / wrapper 公开 ABI 不接收 `ctx`。
- include/api 全局 `launch<block, thread, subthread, shared_memory_size, name>(ctx, args...)` 是后端无关公开 declaration，必须与 `npu_demo::launch` 的 context-first 调用面一致。
- `ctx` 是当前 launch 模式的 context 实例；kernel 模式使用 `npu_demo::KernelContext`，cost 模式使用对应后端 cost context。本计划不公开具体 cost context 名称；若实现必须写入 spec / API 列表，必须先确认。
- `name` 必须是函数名或函数模板业务参数 specialization；不得把 `npu_demo::KernelContext` 作为 body 模板参数写入 `name`。
- `name` 必须可用传入的 `Context&` 作为首参调用，即满足 `name(ctx, args...)`。
- `launch` 不再接受只满足 `name(args...)` 的 context-free callee。
- 失败语义：字符串 callee 继续拒绝；不满足 context-first callable 的模板静态断言文本必须包含 `launch callee must accept Context& plus args`，不得保留 `args or ...`。
- 负向门禁：不得生成 `launch(name, ctx, ...)`、`launch(ctx, name, ...)`、`launch<...>(ctx, name, ...)`、`launch<...>(name, ctx, ...)`、`launch<..., body<npu_demo::KernelContext>>(ctx, ...)`。

### generated body 合同

- launch body 定义：
  ```cpp
  static void kernel_device(npu_demo::KernelContext& ctx, Memory<GM, float>& lhs, Memory<GM, float>& rhs, Memory<GM, float>& out) {
      slice(ctx, out, lhs, {0}, {out.get_shape(0)}, {1});
  }
  ```
- wrapper 调用：
  ```cpp
  void kernel_device_wrapper(Memory<GM, float>& lhs, Memory<GM, float>& rhs, Memory<GM, float>& out) {
      npu_demo::KernelContext ctx;
      npu_demo::launch<2, 1, 1, 0, kernel_device>(ctx, lhs, rhs, out);
  }
  ```
- host 入口 / wrapper 函数签名只保留业务参数，不得出现 `KernelContext& ctx`、`KernelContext* ctx` 或普通业务参数名 `ctx`；`ctx` 只能在函数体内创建并向 launch/body/helper 链路下传。
- 若 body 还携带 memory dtype template 参数，只生成业务 dtype 模板，例如 `template <typename TData> static void body(npu_demo::KernelContext& ctx, ...)`，wrapper 使用 `npu_demo::launch<..., body<TData>>(ctx, args...)`。
- generated source 不得出现 `_cost_` sibling function、`tuner.cost` 文本或 `cost::` helper 调用；cost 行为只能通过同一 `include/api` helper 在 cost context 实例下由后端 cost 实现承接。

### emit_c 命名空间与 ctx-first 合同

- emit_c 层对 `arch.launch` 生成的 body declaration / definition 必须把 `npu_demo::KernelContext& ctx` 添加为第一个 C++ 参数，业务参数顺序保持不变；不得生成 `template <typename Context>` body。
- emit_c body 内 DMA / Kernel helper 调用只做 context-first 变更：`slice(out, source, ...)` 变为 `slice(ctx, out, source, ...)`，`add<...>(out, lhs, rhs)` 变为 `add<...>(ctx, out, lhs, rhs)`；不得继续生成显式 no-ctx 模板 helper 调用。
- emit_c body 内 Arch 查询 / 动态内存 / barrier 保持既有 free helper 访问：`npu_demo::thread_id()`、`npu_demo::thread_num()`、`npu_demo::get_dynamic_memory<Space>()`、`npu_demo::barrier(...)`；不得改成 `ctx.thread_id()`、`ctx.barrier(...)` 或 `ctx.get_dynamic_memory<...>()` 这一类成员调用。
- wrapper / host 入口公开签名不得包含 `ctx`；wrapper 函数体内 kernel-mode context 声明必须显式为 `npu_demo::KernelContext ctx;`；launch 调用必须显式为 `npu_demo::launch<..., body>(ctx, args...)` 或 dtype 场景 `npu_demo::launch<..., body<T...>>(ctx, args...)`。
- 不得生成裸 `KernelContext ctx;` 或裸 `launch<...>(ctx, ...)`，避免与 include/api 全局 `KernelContext` / `launch` 混用。
- body 内 helper 调用保持未限定名 `slice(ctx, ...)` / `add<...>(ctx, ...)`，由 `include/api` public helper 承接；当前命名空间可继续通过现有 include / using 机制解析，但计划口径不得把 generated source 绑定到 backend-specific `cost::` helper。
- Dma layout 生成调用实参使用 no-cast braced-init `{...}` 构造 `Vector`；public helper API 仍是 `const Vector&`，不得把目标签名改写成 `std::initializer_list<long long>`，也不得在 generated source 正向文本中显式生成 `Vector(...)` 或 `static_cast<long long>(...)`。

### include helper 合同

- `Context& ctx` 是所有 DMA / Kernel public helper 的第一实参。
- 本轮 `npu_demo::KernelContext` 为 kernel 运行上下文；`Context` 模板参数允许 cost context 以同名 helper API 实例化。`include/api` helper 内部按编译期 target 宏分发到 `include/npu_demo/kernel` 或 `include/npu_demo/cost` 实现；本计划不公开具体 `CostContext` 类名。
- public helper 返回值保持 `Status` / `Memory` 语义，不把 cost 数值作为 helper 返回值。
- helper 实现不得对 `ctx` 使用 `hasattr`、`getattr`、`callable(getattr(...))` 或同类运行时能力探测。

### Arch free helper 口径

- `block_id()`、`thread_id()`、`thread_num()`、`npu_demo::barrier(...)`、`get_dynamic_memory<Space>()`、`DynamicMemoryRef` 继续作为公开 free helper 保留。
- `KernelContext` 不再公开 `block_id()`、`block_num()`、`thread_id()`、`thread_num()`、`subthread_id()`、`subthread_num()`、`barrier(...)`、`get_dynamic_memory<...>()` 这类 runtime member API；generated body、手写 include case、spec 和测试均不得依赖 `ctx.member(...)`。
- execute 不得删除、重命名、前置 `ctx` 或降级这些 Arch free helper；相关 spec、include API 列表和测试必须保持正向口径。

### include/api 宏分发与 cost function 口径

- `LaunchKernelCostFuncPass` 生成 sibling `S_INT _cost_*` function 的链路不得作为本轮 npu_demo generated source 主链路。
- generated source、`test/dsl/gen_kernel` 与 `spec/dsl/gen_kernel/**` 中不得再把 `_cost_*` sibling、`tuner.cost`、`cost::` 作为 context-first 主链路正向期望。
- `include/api` DMA / Kernel helper 是 emitc 生成代码调用的函数；API 根据编译期 target 宏与 `Context` 类型实例化选择 npu_demo kernel 或 cost 实现，宏只负责编译期 target 选择，避免一次编译所有 target 实现。
- `include/npu_demo/kernel` 侧实现 kernel context 实例，`include/npu_demo/cost` 侧实现 cost context 实例；这两个后端实现层不得要求 generated source 改为直接调用 backend-specific helper。
- `LaunchKernelCostFuncPass`、`launch-kernel-cost-func` registry / pipeline 引用、对应 spec 与测试直接删除；`dsl_cost_run`、`dsl_run` 与旧 standalone `npu_demo::cost::*` / `CostKind` surface 保留，不得擅自删除或改参数。

## 完成态定义

- `expectation/dsl/emit_c/npu_demo/dma/copy.py` 两条 case 转绿，且 execute 不修改该 expectation。
- `expectation/dsl/emit_c/npu_demo/dma/alloc.py`、`fill.py`、`slice.py`、`deslice.py`、`store.py`、`load.py`、`transpose.py`、`broadcast.py` 全部 case 转绿，且 execute 不修改这些 expectation。
- `expectation/dsl/emit_c/npu_demo/kernel/binary_elewise.py` 八条 case 转绿，且 execute 不修改该 expectation。
- `expectation/dsl/emit_c/npu_demo/kernel/binary_compare.py`、`exp.py`、`select.py`、`reduce.py`、`matmul.py`、`img2col.py` 全部 case 转绿，且 execute 不修改这些 expectation。
- `expectation/dsl/emit_c/npu_demo/arch/{get_block_id,get_thread_id,get_thread_num,get_dynamic_memory,launch}.py` 与 `expectation/dsl/emit_c/npu_demo/arch` 目录聚合入口全部转绿，且 execute 不修改这些 expectation。
- `expectation/dsl/gen_kernel/context_first_source.py` 三条 case 全部转绿，且 execute 不修改该 expectation。
- `expectation/include/npu_demo/launch_block_grid.py` 转绿，证明 `npu_demo::launch<..., body>(ctx, args...)` 运行 block × thread 网格，body 接收但不调用 `ctx.*` runtime member，并通过 Arch free helper 读取 block/thread 运行时视图；execute 不修改该 expectation。
- `npu_demo` launch body 生成 `static void body(npu_demo::KernelContext& ctx, ...)`；dtype body 只保留业务 dtype 模板参数。
- `npu_demo` host 入口 / wrapper 签名不接收 `ctx`、只接收业务参数；函数体内物化 `npu_demo::KernelContext ctx`，并使用 `npu_demo::launch<..., body>(ctx, args...)` 或 `npu_demo::launch<..., body<T...>>(ctx, args...)`。
- generated source 中 DMA / Kernel helper 统一为 `op<...>(ctx, args...)` 或 `op(ctx, args...)`，调用目标是 `include/api` public helper，Arch 查询继续使用既有 free helper。
- include/api 与 include/npu_demo 文件级 `API 列表` 不再公开旧无 ctx DMA / Kernel helper 或 `launch` 的 no-ctx callable fallback；Arch free helper 与 `DynamicMemoryRef` 继续公开。
- include/api 与 include/npu_demo context-first Dma API 列表中，Dma layout 参数使用 `Vector`；不得继续公开 `std::initializer_list<long long> ... stride` Dma helper 目标签名。旧 standalone cost Dma API 本轮不物理删除，除非执行中回到用户确认。
- include/api 全局 `launch` 与 `npu_demo::launch` 均只保留 callee-in-template 的 context-first signature。
- include/api 全局 `KernelContext` 与 `npu_demo::KernelContext` 的文件级 `API 列表` 均不得列出 runtime 查询 / 同步 / 动态内存 member API；`npu_demo::KernelContext()` 默认构造必须作为 kernel-mode wrapper 物化 context 的公开构造签名保留。
- `npu_demo::KernelContext` 的 launch-runtime 构造不得暴露 `npu_demo::detail` 类型；执行时必须收为非公开实现结构。
- npu_demo context-first 主链路不再生成 / 依赖 `_cost_*` sibling function；`LaunchKernelCostFuncPass` 相关链路删除，`dsl_cost_run` 与旧 cost surface 保留并脱离新 generated source 主链路。
- Diff 反推 pytest、合同验收 expectation、文本门禁与任务记录自检全部完成。

## 计划内小任务

### S1：同步 spec 公开合同

- 为什么做：先把公开合同改成用户确认的 context-first 口径，避免实现继续跟旧 spec 对齐。
- 做什么：更新 npu_demo 相关 include / gen_kernel / emit / pass / tool spec 的 API 列表、示例、失败语义、`include/api` 编译期 target 宏分发和主链路说明；把 `LaunchKernelCostFuncPass` spec 标为删除 / 下线。
- 不做什么：不删除 `dsl_cost_run`、`dsl_run` 或旧 cost surface 公开入口；不把 `dsl_cost_run` 改成最终 cost-kernel-only 语义；不触碰 implementation/test；`expectation/` 只读。
- 怎么验收：人工核对目标 spec 中无 ctx DMA / Kernel helper 与 `_cost_*` 主链路正向期望已移除，Arch free helper 正向期望保留；本卡无代码 diff pytest，合同验收由 S3/S5 运行。
- 卡住问谁：公开 API 或需求取舍问用户；架构 / 验收口径问架构师；流程状态问管理员。
- 上下文：Draft 1 review 已确认 spec 边界不清会把公开 API 删除决策带进 execute。
- 模块范围：`spec/include/api/**`、`spec/include/npu_demo/**`、`spec/dsl/gen_kernel/**`、`spec/pass/tuning/launch_kernel_cost_func.md`、`spec/tools/dsl_cost_run.md`。
- 禁止修改面：不得修改 `.skills/`、`agents/standard/`、`expectation/`、`TODO.md`、`DONE.md`、implementation 或测试文件。
- 合同真源：用户确认来源 > 本计划公开 API 设计 > 当前 spec > 当前实现。
- 最小闭环：spec 写明 `launch` 必须把 callee/name 放入模板参数、函数实参只接收 `ctx, args...` 且只接受 context-first name；generated host 入口 / wrapper 公开签名不接收 `ctx`，只在函数体内创建 `npu_demo::KernelContext ctx;` 后下传；generated body 和 DMA / Kernel helper 调用均为 context-first，Arch free helper 保留，`include/api` helper 按编译期 target 宏 / context 类型分发 kernel 与 cost 实现，旧 cost sibling 链路与 `LaunchKernelCostFuncPass` 脱离 npu_demo generated source 主链路并删除。
- 执行步骤：
  - 更新 `spec/include/api/Dma.md` 与 `spec/include/api/Kernel.md`，移除无 ctx helper 签名，新增 `Context& ctx` 首参；Dma layout 参数统一写为 `Vector`，不得保留 `std::initializer_list<long long> ... stride` 目标签名。
  - 更新 `spec/include/api/Arch.md` 与 `spec/include/npu_demo/npu_demo.md`，写明 include/api 全局 `launch` 与 `npu_demo::launch` 都必须把 callee/name 放入模板参数并接收 `ctx, args...` 实参，写明 `KernelContext` 不公开 runtime member API、Arch 查询 / 同步 / 动态内存只保留 free helper 口径，且不再支持 `callee(args...)`、`launch(ctx, callee, ...)` 或 `launch(callee, ctx, ...)`。
  - 更新 `spec/dsl/gen_kernel/gen_kernel.md` 与 `spec/dsl/gen_kernel/kernel_emitter.md`，写明 body 不再使用 `Context` 模板参数、host 入口 / wrapper 签名不接收 `ctx`、wrapper 体内 `KernelContext` 实例化、dtype template 只保留业务类型参数和禁止 sibling cost function。
  - 更新 `spec/dsl/gen_kernel/emit.md`、`spec/dsl/gen_kernel/emit/npu_demo.md` 与 `spec/dsl/gen_kernel/emit/npu_demo/include.md`，写明 `dma/kernel` emit 的 context-first 文本、`arch.launch` 的 `npu_demo::KernelContext& ctx` 首参、host 入口 / wrapper ABI 无 `ctx` 和 `npu_demo::KernelContext` / `npu_demo::launch<..., body>(ctx, ...)` 命名空间规则，并写明 helper 调用归属 `include/api`、实际实现由编译期 target 宏 / context 类型分发，Arch 查询 free helper 保留。
  - 删除或下线 `spec/pass/tuning/launch_kernel_cost_func.md` 对 `LaunchKernelCostFuncPass` 的公开合同；相关 spec / registry 文本不得继续把 `launch-kernel-cost-func` 列为可用 pass。
  - 核对 `spec/tools/dsl_cost_run.md`：只允许记录 `dsl_cost_run` 保留和后续 cost-kernel-only 目标语义，不得在本计划内改参数签名、删除入口或把新语义写成当前已完成合同。
- 记录要求：任务记录写明所有公开 API 删除/保留项、用户确认来源和 spec diff 自检。

### S2：修改 include API 与 npu_demo runtime surface

- 为什么做：generated source 要调用 `op<...>(ctx, args...)` / `op(ctx, args...)`，include public helper 和 launch runtime 必须先承接同一 API。
- 做什么：把 DMA / Kernel helper、launch callable 检查和文件级 API 列表改成 context-first；API helper按编译期 target 宏 / context 类型分发到 npu_demo kernel 或 cost 实现；Arch free helper API 保持不变。
- 不做什么：不新增 public `CostContext` 类名；不删除 `dsl_cost_run`、`dsl_run` 或旧 cost surface；`expectation/` 只读。
- 怎么验收：运行 include 相关 pytest；文本门禁确认 DMA / Kernel no-ctx overload / launch fallback 不再公开残留，同时确认 Arch free helper 仍公开。
- 卡住问谁：公开 API 删除范围问用户；实现结构和验收口径问架构师；任务链状态问管理员。
- 上下文：当前 `include/npu_demo/Arch.h` 支持 `callee(args...)` fallback，并通过 active thread-local free helper 服务旧 generated source；当前 cost helper 是独立 `cost::` surface，Draft 26 当前口径要求新 generated source 通过 `include/api` helper 与 context 实例分发 cost/kernel，host 入口无 `ctx` 且只在函数体内创建 context，`LaunchKernelCostFuncPass` 旧 sibling pass 删除。
- 模块范围：`include/api/Dma.h`、`include/api/Kernel.h`、`include/api/Arch.h`、`include/npu_demo/Dma.h`、`include/npu_demo/Kernel.h`、`include/npu_demo/cost/**`、`include/npu_demo/Arch.h`、`include/npu_demo/npu_demo.h`、相关 include pytest。
- 禁止修改面：不得修改 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。
- 合同真源：本计划公开 API 设计 > S1 更新后 spec > include pytest > 当前实现。
- 最小闭环：手写 `npu_demo::KernelContext ctx; npu_demo::launch<..., body>(ctx, args...)` 能调用 `body(npu_demo::KernelContext&, args...)`，DMA / Kernel helper 只以 `ctx` 首参公开；API helper 在 kernel context 下调用 npu_demo kernel 实现，在 cost context 下可调用 npu_demo cost 实现且不需要 generated source 直接写 `cost::`。
- 执行步骤：
  - 更新 `include/api/Dma.h`、`include/api/Kernel.h` API 列表和声明，删除无 ctx public overload，并把 Dma layout 参数收为 `Vector`；写明该层是 emitc generated source 调用面，实际实现由编译期 target 宏 / context 类型分发。
  - 更新 `include/npu_demo/Dma.h`、`include/npu_demo/Kernel.h` 实现与文件级 API 列表，helper 以 `Context& ctx` 首参承接 kernel context 实例，Dma layout 参数只公开 `Vector` 形态，生成调用可依赖模板参数推导。
  - 更新 `include/npu_demo/cost/**` 对应文件级 API 列表与实现说明，承接 cost context 实例；不得要求 generated source 直接调用 `cost::` helper，且不得公开新 cost context 类名；旧 standalone cost surface 不因本计划删除。
  - 更新 `include/api/Arch.h`、`include/npu_demo/Arch.h` 与 `include/npu_demo/npu_demo.h` API 列表，保留 `block_id()`、`thread_id()`、`thread_num()`、`npu_demo::barrier(...)`、`get_dynamic_memory<Space>()`、`DynamicMemoryRef`，删除 `KernelContext` 的 runtime 查询 / 同步 / 动态内存 public member API。
  - 更新 `include/api/Arch.h` 全局 `launch` declaration 与 `include/npu_demo/Arch.h::launch` implementation，将 public signature 改为 `launch<block, thread, subthread, shared_memory_size, name>(ctx, args...)`，删除 `callee(args...)` fallback 和 `args or ...` 静态断言文本，只接受 context-first name。
  - 更新 `include/api/Arch.h` 与 `include/npu_demo/Arch.h` 文件级 API 列表，分别列出全局 `KernelContext` opaque 类型与 `npu_demo::KernelContext` 默认构造；不得列出 `ctx.block_id()`、`ctx.thread_id()`、`ctx.barrier(...)`、`ctx.get_dynamic_memory<...>()` 等 member API；保留 `npu_demo::KernelContext()` 供 wrapper 物化 kernel context，并把带 `LaunchBarrierState` 的 launch-runtime 构造收为不暴露 `npu_demo::detail` 类型的非公开实现结构。
  - 更新 include pytest，删除旧无 ctx helper 正向断言，新增 no-ctx callable / helper 拒绝或编译失败覆盖。
- Diff 反推测试：
  - `pytest -q test/include/api/test_dma.py`
  - `pytest -q test/include/api/test_kernel.py`
  - `pytest -q test/include/api/test_arch.py`
  - `pytest -q test/include/npu_demo/test_kernel_context.py`
- 合同验收：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.include.npu_demo.launch_block_grid`
- 记录要求：任务记录写明 include API 删除清单、launch fallback 删除证明、Diff 反推自测和自检。

### S3：修改 gen_kernel / emit 生成文本

- 为什么做：核心交付是 generated source 只生成一份 context-first kernel body。
- 做什么：更新 `kernel_emitter` 与 npu_demo emit 注册实现，使 body、wrapper、DMA、Kernel op 输出 context-first 文本；Arch 查询保持 free helper 文本。
- 不做什么：不生成 host cost runner，不接入 tuner param；`expectation/` 只读。
- 怎么验收：运行 gen_kernel / emit pytest；运行 `context_first_source` expectation；文本门禁确认旧 generated source 文本消失。
- 卡住问谁：IR 到源码设计问架构师；公开 API 或 expectation 授权问用户；流程问管理员。
- 上下文：旧 emit_c expectation 已原地覆盖 DMA helper 的 `alloc/fill/slice/deslice/store/load/transpose/broadcast(ctx, ...)`、`dma.copy` 的 `slice(ctx, ...)`、Kernel helper 的 `add/sub/mul/truediv/eq/ne/lt/le/gt/ge/exp/select/reduce/matmul/img2col<...>(ctx, ...)`、`arch/{get_block_id,get_thread_id,get_thread_num,get_dynamic_memory,launch}` 的完整 launch module body / wrapper context-first；`context_first_source` expectation 已覆盖完整 generated source 的 `slice(ctx, ...)`、`add<...>(ctx, ...)`、dtype-only template、`KernelContext` 实例化、callee-in-template launch，并保留 Arch free helper 文本。
- 模块范围：`kernel_gen/dsl/gen_kernel/kernel_emitter.py`、`kernel_gen/dsl/gen_kernel/emit/npu_demo/**`、`test/dsl/gen_kernel/**`。
- 禁止修改面：不得修改 `expectation/`、include API 之外的无关后端、`.skills/`、`agents/standard/`、`TODO.md`、`DONE.md`。
- 合同真源：本计划列出的 `expectation/dsl/emit_c/npu_demo/dma/*.py` public helper 叶子、`expectation/dsl/emit_c/npu_demo/kernel/*.py` public helper 叶子、`expectation/dsl/emit_c/npu_demo/arch/{get_block_id,get_thread_id,get_thread_num,get_dynamic_memory,launch}.py`、`expectation/dsl/emit_c/npu_demo/arch` 目录聚合入口与 `expectation/dsl/gen_kernel/context_first_source.py` > S1 spec > S2 include API > pytest > 当前实现。
- 最小闭环：5 个 arch 叶子 launch module 均输出 `static void body(npu_demo::KernelContext& ctx, ...)`；body 内 DMA / Kernel helper 传 `ctx`，Arch 查询保持 `npu_demo::*` free helper，host 入口 / wrapper 签名无 `ctx`，wrapper 体内物化 `npu_demo::KernelContext ctx` 并调用 `npu_demo::launch<..., body>(ctx, args...)`。
- 执行步骤：
  - 更新 launch body declaration / definition 生成 `npu_demo::KernelContext& ctx` 首参；dtype 场景只生成业务 dtype 模板参数。
  - 更新 wrapper launch 发射，确保 host 入口 / wrapper 函数签名不包含 `ctx`；函数体内先生成 `npu_demo::KernelContext ctx;`，再把 `body` 或 `body<T...>` 放入 `npu_demo::launch` 模板参数，把 launch 函数实参收为 `ctx, args...`。
  - 更新 body 参数绑定，确保 IR 中 `%ctx {name="ctx"}` 绑定为 C++ `ctx`，且不会转发到 wrapper ABI。
  - 更新 `emit/npu_demo/arch/launch` 相关 body / wrapper 发射，确保 launch body 有 `npu_demo::KernelContext& ctx` 首参，wrapper ABI 无 `ctx`，wrapper 函数体内创建 `npu_demo::KernelContext ctx` 并调用 callee-in-template 的 context-first `npu_demo::launch<..., body>(ctx, args...)`。
  - 保持 `emit/npu_demo/arch/*` 中查询、动态内存和 barrier 发射为 `npu_demo::thread_id()`、`npu_demo::thread_num()`、`npu_demo::get_dynamic_memory<Space>()`、`npu_demo::barrier(...)`。
  - 更新 `emit/npu_demo/dma/*` 与 `emit/npu_demo/kernel/*`，所有 public helper 调用加 `ctx` 首参，Dma layout 实参发射为 no-cast braced-init `{...}`，保留旧显式模板参数但移除旧 `add<Space,...>(args...)` 等 no-ctx 调用；这些文本调用视为 `include/api` helper，不得改成直接 `cost::` 或 `_cost_*` 调用。
  - 检查 emit_c wrapper 命名空间和 ABI：wrapper 签名不得接收 `ctx`，context 声明必须为 `npu_demo::KernelContext ctx;`，launch 调用必须为 `npu_demo::launch<..., body>(ctx, args...)` 或 `npu_demo::launch<..., body<T...>>(ctx, args...)`；不得生成裸 `KernelContext`、裸 `launch`、`launch<...>(ctx, body, ...)` 或 `launch<...>(body, ctx, ...)`。
  - 更新测试中对生成源码的文本断言：移除隐藏 `KernelContext` 的旧断言，保留 / 新增 Arch free helper 正向断言，移除 sibling cost function 正向断言。
- Diff 反推测试：
  - `pytest -q test/dsl/gen_kernel/emit/test_package.py`
  - `pytest -q test/dsl/gen_kernel/test_gen_kernel.py`
- 合同验收:
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma.alloc`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma.fill`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma.copy`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma.slice`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma.deslice`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma.store`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma.load`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma.transpose`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma.broadcast`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.kernel.binary_elewise`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.kernel.binary_compare`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.kernel.exp`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.kernel.select`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.kernel.reduce`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.kernel.matmul`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.kernel.img2col`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.arch.get_block_id`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.arch.get_thread_id`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.arch.get_thread_num`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.arch.get_dynamic_memory`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.arch.launch`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.arch`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.gen_kernel.context_first_source`
- 记录要求：任务记录写明 expectation 红转绿前后摘要、生成源码 actual 片段和 Diff 反推自测。

### S4：收口旧 cost func generate 主链路与 API 分发口径

- 为什么做：用户明确外层调用 `include/api` 函数，API 根据编译期 target 宏和 context 类型区分 kernel / cost；generated source 主链路必须从 `_cost_*`、`tuner.cost` 和直接 `cost::` 调用迁走，同时用户已确认 `LaunchKernelCostFuncPass` 相关链路直接删除。
- 做什么：移除 npu_demo context-first 主链路对 `_cost_*`、`tuner.cost`、`cost::` 的依赖和正向期望；删除 `LaunchKernelCostFuncPass`、`launch-kernel-cost-func` registry / pipeline 引用、对应 spec 与测试；把 cost/kernel 区分收口到 `include/api` 编译期 target 宏分发与 context 模板实例。
- 不做什么：不删除 `dsl_cost_run`、`dsl_run`、旧 `npu_demo::cost::*` / `CostKind` 或工具参数；不在本计划内把 `dsl_cost_run` 改成最终 cost-kernel-only 语义；不生成新的 host cost runner。
- 怎么验收：运行 registry / dsl gen / `dsl_cost_run` 保留相关 pytest；文本门禁确认 context-first 主链路不含 `_cost_*` / `tuner.cost` / `cost::`，`launch-kernel-cost-func` 不再作为可注册 pass，且 `include/api` helper 分发说明已写入 spec / API 列表。
- 卡住问谁：若发现必须新增公开宏名、公开 cost context 类名，或删除 / 改参 `dsl_cost_run`、`dsl_run`、旧 cost surface 才能通过，停止并问用户；主链路定义问架构师；流程问管理员。
- 上下文：Draft 23 的“直接删除全部 cost 旧链路”已被用户更正；Draft 24 的确认口径是 `include/api` 统一调用 + 宏 / context 实例分发；Draft 25 追加确认目标宏只做编译期 target 选择、`LaunchKernelCostFuncPass` 删除、`dsl_cost_run` 保留；Draft 26 追加确认 host 入口函数签名无 `ctx`、入口函数体内创建 `ctx` 后下传。
- 模块范围：`spec/pass/tuning/launch_kernel_cost_func.md`、`kernel_gen/passes/tuning/launch_kernel_cost_func.py`、`kernel_gen/passes/tuning/__init__.py`、`kernel_gen/passes/registry.py`、相关 pipeline / registry spec 与测试、`spec/tools/dsl_cost_run.md` 保留说明、`test/dsl/gen_kernel/**` 中 cost 期望、`include/npu_demo/cost/**` 说明与测试中属于 API 分发的部分。
- 禁止修改面：不得删除或改参 `dsl_cost_run`、`dsl_run`、旧 cost surface public 入口；不得修改 `expectation/pass/tuning/**`、`expectation/tools/**` 或本计划未授权的 expectation。
- 合同真源：用户“include/api 根据宏控制实际 kernel / cost 实现”确认与 `LaunchKernelCostFuncPass` 删除 / `dsl_cost_run` 保留确认 > 本计划 cost 口径 > pass/tool 现有公开 API > 当前实现。
- 最小闭环：`gen_kernel(target="npu_demo")` context-first 主链路不再输出 `_cost_*` sibling，不直接写 `tuner.cost` 或 `cost::`；API 层可通过编译期 target 宏 / context 类型把同一 helper 调用分发到 kernel / cost 实现；`LaunchKernelCostFuncPass` 不再可导入、注册或作为 pipeline pass 使用；`dsl_cost_run` 入口仍可公开导入且未改参数签名。
- 执行步骤：
  - 删除 `kernel_gen/passes/tuning/launch_kernel_cost_func.py`，移除 `kernel_gen/passes/tuning/__init__.py` 中的 `launch_kernel_cost_func` 导出，删除 registry / pipeline 中的 `launch-kernel-cost-func` 注册与自动插入，并同步删除或下线 `spec/pass/tuning/launch_kernel_cost_func.md`。
  - 更新 `spec/tools/dsl_cost_run.md` 与 `kernel_gen/tools/dsl_run.py` 文件级说明 / API 列表中的关联说明，确保 `dsl_cost_run` 入口保留、参数签名不变，并记录最终语义后续另立计划改为“不运行 kernel，只运行 cost 的 kernel，并返回结果”；本计划不得把该目标写成已完成实现。
  - 核对 pass registry、pipeline、`dsl_cost_run`、`dsl_run` 与旧 `npu_demo::cost::*` / `CostKind` 当前公开入口；除 `LaunchKernelCostFuncPass` 相关链路外不得删除或改参数。
  - 更新相关 spec，说明旧 sibling cost pass 已删除；新主链路通过 `include/api` helper、编译期 target 宏和 context 类型实例承接 cost/kernel 区分。
  - 移除 `test/dsl/gen_kernel/**` 和 `spec/dsl/gen_kernel/**` 对 `_cost_*` sibling generated source 的正向期望。
  - 删除 `test/passes/tuning/test_launch_kernel_cost_func.py` 或改为不存在 / 不可注册门禁；更新 registry / pipeline 测试，证明 `launch-kernel-cost-func` 已下线且其它 pass 入口未被误删。
  - 更新 `test/tools/test_dsl_cost_run.py` 只覆盖本计划保留边界：入口仍可导入、参数签名不变、不会因 pass 删除误 fallback 到普通 kernel；最终 cost-kernel-only 运行语义留给后续计划。
- Diff 反推测试：
  - `pytest -q test/passes/test_registry.py`
  - `pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k cost`
  - `pytest -q test/tools/test_dsl_cost_run.py`
- 合同验收：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.gen_kernel.context_first_source`
- 记录要求：任务记录写明主链路 `_cost_*` / `tuner.cost` / `cost::` 移除证明、`LaunchKernelCostFuncPass` 删除证明、`dsl_cost_run` 保留证明、API 分发说明落位证明、未越权修改 cost expectation 的证明，以及执行中是否产生新增 public macro / context 名称待确认事项。

### S5：记录、文本门禁与减法检查

- 为什么做：破坏式 API 改动容易残留旧入口，必须用记录和文本门禁证明没有半兼容状态。
- 做什么：补齐执行记录、自检、Diff 反推自测、文本门禁、敏感目录核对和减法检查。
- 不做什么：不把 `rg` 文本扫描记成 Diff 反推测试；`expectation/` 与标准文档只读。
- 怎么验收：pytest 与 expectation 单列通过；文本门禁无未解释残留；任务记录包含执行前阅读、Diff 反推自测、减法检查和自检。
- 卡住问谁：文本门禁残留是否允许问架构师；公开 API 残留需保留问用户；任务记录路径问管理员。
- 上下文：根 `AGENTS.md` 要求 execute 自检、Diff 反推测试和公开 API / 非公开 API 检查。
- 模块范围：本计划实际 touched files、任务记录文件、相关 pytest。
- 禁止修改面：不得修改 `expectation/`、`.skills/`、`agents/standard/`、`AGENTS.md`、`TODO.md`、`DONE.md`。
- 合同真源：本计划完成态定义 > 实际 diff > pytest / expectation > 文本门禁。
- 最小闭环：所有本计划 touched implementation/spec/test 文件有对应记录和验证；旧 API 残留有明确删除或非公开解释。
- 执行步骤：
  - 任务记录写明执行前阅读、最小功能闭环、Diff 反推自测、文本门禁、减法检查、自检。
  - 减法检查列出删除的 DMA / Kernel 无 ctx public helper、launch fallback、`LaunchKernelCostFuncPass` 相关链路和 generated source `_cost_*` / `tuner.cost` / 直接 `cost::` 主链路期望；同时记录 `dsl_cost_run` 入口、Arch free helper / `npu_demo::barrier(...)` / `DynamicMemoryRef` 保留证明。
  - 扫描 touched files，不得新增跨文件非公开 helper 调用。
  - 扫描 DMA / Kernel 无 ctx public helper、old cost sibling、`tuner.cost`、generated source 直接 `cost::` 与 `launch-kernel-cost-func` 注册残留；扫描 `ctx.block_id()`、`ctx.thread_id()`、`ctx.thread_num()`、`ctx.barrier(...)`、`ctx.get_dynamic_memory<...>()` 等 context runtime member 调用并作为阻断。
- Diff 反推测试：
  - 结合实际 diff 补跑 S2/S3/S4 中相关 pytest；不得把 `rg` 计入 Diff 反推测试。
- 合同验收：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma.alloc`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma.fill`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma.copy`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma.slice`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma.deslice`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma.store`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma.load`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma.transpose`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma.broadcast`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.kernel.binary_elewise`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.kernel.binary_compare`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.kernel.exp`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.kernel.select`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.kernel.reduce`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.kernel.matmul`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.kernel.img2col`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.arch.get_block_id`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.arch.get_thread_id`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.arch.get_thread_num`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.arch.get_dynamic_memory`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.arch.launch`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.arch`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.gen_kernel.context_first_source`
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.include.npu_demo.launch_block_grid`
- 文本门禁：
  - `rg -n "npu_demo::launch<" kernel_gen test spec include`：人工核对 npu_demo launch 调用必须把 callee/name 放入模板参数，函数实参必须为 `ctx, args...`；`launch<...>(ctx, body, ...)`、`launch<...>(body, ctx, ...)`、`launch(body, args...)`、`body<npu_demo::KernelContext>` 作为 launch name 均为阻断。
  - `rg -n "(^|[^:])\\bKernelContext ctx;|(^|[^:])\\blaunch<[^\\n]*\\(ctx," kernel_gen/dsl/gen_kernel test/dsl/gen_kernel spec/dsl/gen_kernel`
  - `rg -n "template <long long block, long long thread, long long subthread, long long shared_memory_size, typename Callable, typename\\.\\.\\. Args>|Status launch\\(Callable&& callee, Args&&\\.\\.\\. args\\)|launch<block, thread, subthread, shared_memory_size>\\(callee|body<npu_demo::KernelContext" include/api include/npu_demo spec test kernel_gen`
  - `rg -n "npu_demo::launch<|\\blaunch<" include/api include/npu_demo spec test kernel_gen`：人工核对 `launch<...>(ctx, args...)` 中 `args...` 可为普通标识符；门禁只禁止 body/name 出现在函数实参中，禁止 `launch<...>(ctx, body, ...)` 与 `launch<...>(body, ctx, ...)`。
  - `rg -n "(wrapper|host|entry|run_kernel|gen_kernel)[^\\n]*\\([^\\n]*(KernelContext|\\bctx\\b)" kernel_gen/dsl/gen_kernel test/dsl/gen_kernel spec/dsl/gen_kernel`：人工核对 generated host 入口 / wrapper 公开签名不得包含 `ctx` 或 `KernelContext`；body 函数 `npu_demo::KernelContext& ctx` 是正向口径，不得误判。
  - `rg -n --pcre2 "\\b(slice|deslice)\\((?!ctx\\b)|\\b(alloc|fill|store|load|transpose|broadcast|add|sub|mul|truediv|min|max|eq|ne|lt|le|gt|ge|exp|select|reduce_sum|reduce_min|reduce_max|matmul|img2col1d|img2col2d)<[^\\n>]+>\\((?!ctx\\b)" kernel_gen/dsl/gen_kernel/emit/npu_demo kernel_gen/dsl/gen_kernel/kernel_emitter.py`
  - `rg -n "ctx\\.(block_id|block_num|thread_id|thread_num|subthread_id|subthread_num|barrier|get_dynamic_memory)\\(|ctx\\.template get_dynamic_memory" kernel_gen/dsl/gen_kernel test/dsl/gen_kernel spec/dsl/gen_kernel include/api include/npu_demo test/include spec/include`
  - `rg -n "KernelContext::(block_id|block_num|thread_id|thread_num|subthread_id|subthread_num|barrier|get_dynamic_memory)|virtual long long (block_id|block_num|thread_id|thread_num)\\(|Memory<[^\\n>]+> get_dynamic_memory\\(\\) const|void barrier\\([^\\n]*\\) const" include/api include/npu_demo spec/include test/include`
  - `rg -n "npu_demo::block_id\\(|npu_demo::thread_id\\(|npu_demo::thread_num\\(|npu_demo::get_dynamic_memory|npu_demo::barrier\\(|DynamicMemoryRef" include/api include/npu_demo kernel_gen/dsl/gen_kernel test spec`
  - `rg -n "launch callee must accept args|std::is_invocable<typename std::decay<Callable>::type, Args\\.\\.\\.>|callable\\(unpacked_args\\.\\.\\.\\)" include/api include/npu_demo test spec`
  - `rg -n "npu_demo::detail::LaunchBarrierState|std::shared_ptr<detail::LaunchBarrierState>|std::shared_ptr<npu_demo::detail::LaunchBarrierState>" include/api include/npu_demo spec test`
  - `rg -n "_cost_|tuner\\.cost|cost::" kernel_gen/dsl/gen_kernel test/dsl/gen_kernel spec/dsl/gen_kernel`
  - `rg -n "LaunchKernelCostFuncPass|launch-kernel-cost-func|launch_kernel_cost_func" kernel_gen spec test`：核对旧 pass 已下线；只允许本计划历史记录或删除说明中出现。
  - `rg -n "dsl_cost_run" kernel_gen/tools kernel_gen/tools/__init__.py spec/tools test/tools`：核对 `dsl_cost_run` 公开入口、参数签名与包根导出保留，且未被改成普通 `dsl_run` fallback。
  - `rg -n "include/api.*宏|目标宏|Context.*cost|include/npu_demo/cost|include/npu_demo/kernel" spec/include spec/dsl/gen_kernel include/api include/npu_demo`：人工核对 API 分发口径已落位，且没有未确认的具体公开宏名或 public cost context 类名被偷偷写入。
  - `git status --short --untracked-files=all --ignored -- ARCHITECTURE/plan/context_first_kernel_cost_shared_code.md expectation/dsl/emit_c/npu_demo/dma/{alloc,fill,copy,slice,deslice,store,load,transpose,broadcast}.py expectation/dsl/emit_c/npu_demo/kernel/{binary_elewise,binary_compare,exp,select,reduce,matmul,img2col}.py expectation/dsl/emit_c/npu_demo/arch/{get_block_id,get_thread_id,get_thread_num,get_dynamic_memory,launch}.py expectation/dsl/gen_kernel/context_first_source.py expectation/include/npu_demo/launch_block_grid.py`
  - `git status --short --untracked-files=all --ignored -- .skills agents/standard AGENTS.md TODO.md DONE.md`
- 记录要求：文本门禁输出必须在任务记录中分类说明；敏感目录只允许本轮用户授权的 expectation 架构阶段改动存在，execute diff 不得包含 expectation。

## 验收设计

### Diff 反推测试

- `pytest -q test/include/api/test_dma.py`
- `pytest -q test/include/api/test_kernel.py`
- `pytest -q test/include/api/test_arch.py`
- `pytest -q test/include/npu_demo/test_kernel_context.py`
- `pytest -q test/include/api/test_cost.py`
- `pytest -q test/dsl/gen_kernel/emit/test_package.py`
- `pytest -q test/dsl/gen_kernel/test_gen_kernel.py`
- `pytest -q test/passes/test_registry.py`
- `pytest -q test/tools/test_dsl_cost_run.py`

### 合同验收

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma.copy`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma.alloc`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma.fill`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma.slice`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma.deslice`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma.store`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma.load`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma.transpose`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.dma.broadcast`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.kernel.binary_elewise`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.kernel.binary_compare`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.kernel.exp`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.kernel.select`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.kernel.reduce`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.kernel.matmul`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.kernel.img2col`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.arch.get_block_id`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.arch.get_thread_id`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.arch.get_thread_num`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.arch.get_dynamic_memory`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.arch.launch`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.emit_c.npu_demo.arch`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.dsl.gen_kernel.context_first_source`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.include.npu_demo.launch_block_grid`

### 文本门禁

- `rg -n "npu_demo::launch<" kernel_gen test spec include`：人工核对 npu_demo launch 调用必须把 callee/name 放入模板参数，函数实参必须为 `ctx, args...`；`launch<...>(ctx, body, ...)`、`launch<...>(body, ctx, ...)`、`launch(body, args...)`、`body<npu_demo::KernelContext>` 作为 launch name 均为阻断。
- `rg -n "(^|[^:])\\bKernelContext ctx;|(^|[^:])\\blaunch<[^\\n]*\\(ctx," kernel_gen/dsl/gen_kernel test/dsl/gen_kernel spec/dsl/gen_kernel`：核对生成源码、测试和 spec 中不得把 wrapper context / launch 写成裸 `KernelContext ctx;` 或裸 `launch<...>(ctx, ...)`；必须显式使用 `npu_demo::KernelContext` 与 `npu_demo::launch`。
- `rg -n "template <long long block, long long thread, long long subthread, long long shared_memory_size, typename Callable, typename\\.\\.\\. Args>|Status launch\\(Callable&& callee, Args&&\\.\\.\\. args\\)|launch<block, thread, subthread, shared_memory_size>\\(callee|body<npu_demo::KernelContext" include/api include/npu_demo spec test kernel_gen`：核对 include/api 全局 `launch` 与 `npu_demo::launch` 的旧 no-ctx declaration、示例、context specialization name 和 spec 正向文本全部删除。
- `rg -n "npu_demo::launch<|\\blaunch<" include/api include/npu_demo spec test kernel_gen`：人工核对所有 launch 调用；`launch<...>(ctx, args...)` 中 `args...` 可为普通标识符，门禁只禁止 body/name 出现在函数实参中，禁止 `launch<...>(ctx, body, ...)` 与 `launch<...>(body, ctx, ...)`。
- `rg -n "(wrapper|host|entry|run_kernel|gen_kernel)[^\\n]*\\([^\\n]*(KernelContext|\\bctx\\b)" kernel_gen/dsl/gen_kernel test/dsl/gen_kernel spec/dsl/gen_kernel`：人工核对 generated host 入口 / wrapper 公开签名不得包含 `ctx` 或 `KernelContext`；body 函数 `npu_demo::KernelContext& ctx` 是正向口径，不得误判。
- `rg -n --pcre2 "\\b(slice|deslice)\\((?!ctx\\b)|\\b(alloc|fill|store|load|transpose|broadcast|add|sub|mul|truediv|min|max|eq|ne|lt|le|gt|ge|exp|select|reduce_sum|reduce_min|reduce_max|matmul|img2col1d|img2col2d)<[^\\n>]+>\\((?!ctx\\b)" kernel_gen/dsl/gen_kernel/emit/npu_demo kernel_gen/dsl/gen_kernel/kernel_emitter.py`：核对生成文本不再漏传 `ctx`，且不再保留旧显式 no-ctx helper 模板调用；`helper<...>(ctx, ...)` 是正向口径，不得被当作残留。
- `rg -n "Vector\\(" kernel_gen/dsl/gen_kernel/emit/npu_demo kernel_gen/dsl/gen_kernel/kernel_emitter.py test/dsl/gen_kernel spec/dsl/gen_kernel`：人工核对 generated source 正向 Dma layout 实参不得显式生成 `Vector(...)`；layout 实参应为 no-cast `{...}` braced-init，不得生成 `static_cast<long long>(...)`，公开 helper 目标签名仍保持 `const Vector&`。
- `rg -n "std::initializer_list<long long>[^\\n]*stride" include/api/Dma.h include/npu_demo/Dma.h include/npu_demo/npu_demo.h spec/include/api/Dma.md spec/include/npu_demo/npu_demo.md`：核对本轮 context-first Dma public API 不再暴露 initializer-list `stride`；旧 standalone cost Dma surface 本轮不物理删除。
- `rg -n "ctx\\.(block_id|block_num|thread_id|thread_num|subthread_id|subthread_num|barrier|get_dynamic_memory)\\(|ctx\\.template get_dynamic_memory" kernel_gen/dsl/gen_kernel test/dsl/gen_kernel spec/dsl/gen_kernel include/api include/npu_demo test/include spec/include`：核对 Arch 查询 / 动态内存 / barrier 未被误改成 ctx 成员调用，include/spec/test 不再正向依赖 `KernelContext` runtime member；命中为阻断，历史记录需人工排除。
- `rg -n "KernelContext::(block_id|block_num|thread_id|thread_num|subthread_id|subthread_num|barrier|get_dynamic_memory)|virtual long long (block_id|block_num|thread_id|thread_num)\\(|Memory<[^\\n>]+> get_dynamic_memory\\(\\) const|void barrier\\([^\\n]*\\) const" include/api include/npu_demo spec/include test/include`：核对 `KernelContext` runtime member declarations / docs / tests 已删除；命中为阻断，历史记录需人工排除。
- `rg -n "npu_demo::block_id\\(|npu_demo::thread_id\\(|npu_demo::thread_num\\(|npu_demo::get_dynamic_memory|npu_demo::barrier\\(|DynamicMemoryRef" include/api include/npu_demo kernel_gen/dsl/gen_kernel test spec`：核对 Arch free helper 与 `DynamicMemoryRef` 作为公开 / 生成链路正向口径保留；缺失或被删除为阻断。
- `rg -n "launch callee must accept args|std::is_invocable<typename std::decay<Callable>::type, Args\\.\\.\\.>|callable\\(unpacked_args\\.\\.\\.\\)" include/api include/npu_demo test spec`：核对旧 `callee(args...)` fallback 文本 / 分支被删除；不得用宽泛 `std::is_invocable<...Args...>` 误伤新版 `Context&` callable 检查。
- `rg -n "npu_demo::detail::LaunchBarrierState|std::shared_ptr<detail::LaunchBarrierState>|std::shared_ptr<npu_demo::detail::LaunchBarrierState>" include/api include/npu_demo spec test`：核对 public API 列表、spec 与测试不暴露 detail launch-runtime 构造；实现内部 private / friend / detail factory 残留需人工说明。
- `rg -n "_cost_|tuner\\.cost|cost::" kernel_gen/dsl/gen_kernel test/dsl/gen_kernel spec/dsl/gen_kernel`：核对 npu_demo generated source 主链路不再依赖 sibling cost function。
- `rg -n "LaunchKernelCostFuncPass|launch-kernel-cost-func|launch_kernel_cost_func" kernel_gen spec test`：核对旧 pass 已下线；只允许本计划历史记录或删除说明中出现。
- `rg -n "dsl_cost_run" kernel_gen/tools kernel_gen/tools/__init__.py spec/tools test/tools`：核对 `dsl_cost_run` 公开入口、参数签名与包根导出保留，且未被改成普通 `dsl_run` fallback。
- `rg -n "include/api.*宏|目标宏|Context.*cost|include/npu_demo/cost|include/npu_demo/kernel" spec/include spec/dsl/gen_kernel include/api include/npu_demo`：人工核对 API 分发口径已落位，且没有未确认的具体公开宏名或 public cost context 类名被偷偷写入。
- `git status --short --untracked-files=all --ignored -- ARCHITECTURE/plan/context_first_kernel_cost_shared_code.md expectation/dsl/emit_c/npu_demo/dma/{alloc,fill,copy,slice,deslice,store,load,transpose,broadcast}.py expectation/dsl/emit_c/npu_demo/kernel/{binary_elewise,binary_compare,exp,select,reduce,matmul,img2col}.py expectation/dsl/emit_c/npu_demo/arch/{get_block_id,get_thread_id,get_thread_num,get_dynamic_memory,launch}.py expectation/dsl/gen_kernel/context_first_source.py expectation/include/npu_demo/launch_block_grid.py`：核对本计划授权 scope；只允许计划书与上述 23 个 expectation scope 文件作为本轮合同资产候选。
- `git status --short --untracked-files=all --ignored -- .skills agents/standard AGENTS.md TODO.md DONE.md`：核对敏感目录越权；execute 阶段 expectation 只读，不得新增 scope 外 expectation 改动。

## 下发前置

- Draft 20 subagent strict review 与守护最终检验通过结论已被 Draft 21 用户 launch/name 纠偏 supersede，只作历史证据。
- Draft 21 subagent strict review 与守护最终检验通过结论已被 Draft 22 用户 `KernelContext` member API 纠偏 supersede，只作历史证据。
- Draft 22 subagent strict review 与守护最终检验通过结论已被 Draft 24 用户 include/api 宏分发纠偏 supersede，只作历史证据。
- Draft 24 的具体公开宏名、公开 cost context 类名与删除清单待确认状态已被 2026-06-06 用户确认 supersede：目标宏只作为编译期 target 选择机制且本计划不公开具体宏名；`LaunchKernelCostFuncPass` 相关链路直接删除；`dsl_cost_run` 保留且后续另立计划改为 cost-kernel-only 语义；`dsl_run`、非 `LaunchKernelCostFuncPass` 的 pass registry 与旧 cost surface 本轮不删除。
- Draft 25 strict review 复审与守护最终检验曾通过，但已被 2026-06-06 用户关于 host 入口函数不接收 `ctx`、入口函数内部创建 `ctx` 后传给 kernel / launch 的确认 supersede，只作历史证据。
- Draft 26 当前无待用户确认项，strict review 与守护最终检验均已通过；允许管理员后续按流程创建唯一计划级 `execute`：`context-first-kernel-cost-shared-code`。
- execute 未来开工前必须同步最新 main，记录 dirty worktree 保护范围，不得回退用户已有改动。
