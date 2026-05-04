# Arch

## 功能简介

定义 include/api 层统一对外的架构/运行时 API 头文件规范（`include/api/Arch.h`），收口 `launch<block, thread, subthread, shared_memory_size>(callee, args...)` 的公开源码形态、`BarrierVisibility`/`BarrierScope` 枚举，以及后端 `KernelContext::thread_id()`、`KernelContext::thread_num()`、`KernelContext::barrier(visibility, scope)`、`KernelContext::get_dynamic_memory<Space, T>()` 与 free helper `thread_id()`、`thread_num()`、`get_dynamic_memory<Space>()` 必须遵守的命名与参数合同。

- `launch<block, thread, subthread, shared_memory_size>(callee, args...)`：公开 launch 入口，`callee` 必须是函数对象，不能是字符串。
- `BarrierVisibility`：公开可见域枚举，固定成员为 `TSM` 与 `TLM`；其中 `TLM` 表示聚合可见域，覆盖 `TLM1/TLM2/TLM3`。
- `BarrierScope`：公开同步范围枚举，稳定成员为 `BLOCK`、`THREAD`、`SUBTHREAD`、`GLOBAL`。
- `barrier(visibility, scope)`：公开同步接口名，`visibility` 与 `scope` 必填；不得退化为无参 barrier。

## API 列表

- `BarrierVisibility(TSM, TLM) -> enum class`
- `BarrierScope(BLOCK, THREAD, SUBTHREAD, GLOBAL) -> enum class`
- `template <long long block, long long thread, long long subthread, long long shared_memory_size, typename Callable, typename... Args> Status launch(Callable&& callee, Args&&... args)`
- `class KernelContext`
- `KernelContext::thread_id() const -> long long`
- `KernelContext::thread_num() const -> long long`
- `KernelContext::barrier(std::initializer_list<BarrierVisibility> visibility, BarrierScope scope) const -> void`
- `template <MemorySpace Space, typename T> KernelContext::get_dynamic_memory() const -> Memory<Space, T>`
- `thread_id() -> S_INT`
- `thread_num() -> S_INT`
- `template <MemorySpace Space> get_dynamic_memory() -> DynamicMemoryRef<Space>`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/include/api/Arch.md`](../../../spec/include/api/Arch.md)
- `统一头文件`：[`include/api/Arch.h`](../../../include/api/Arch.h)
- `功能实现`：[`include/npu_demo/Arch.h`](../../../include/npu_demo/Arch.h)
- `test`：[`test/include/api/test_arch.py`](../../../test/include/api/test_arch.py)

## 依赖

- [`spec/include/api/Core.md`](../../../spec/include/api/Core.md)：统一 `Status` / `StatusCode` 返回语义。
- [`spec/include/api/Memory.md`](../../../spec/include/api/Memory.md)：统一 `MemorySpace` 枚举语义，提供 `TLM1/TLM2/TLM3` 三块实际空间定义。
- [`spec/include/api/Trance.md`](../../../spec/include/api/Trance.md)：统一 `TRANCE` 开启时的 runtime sink 与日志输出格式。
- [`spec/include/npu_demo/npu_demo.md`](../../../spec/include/npu_demo/npu_demo.md)：后端私有 runtime 行为与 `KernelContext` 运行时视图由该层承接。
- [`spec/operation/arch.md`](../../../spec/operation/arch.md)：高层 helper 与 include/api 命名需保持一致。
- [`spec/dialect/arch.md`](../../../spec/dialect/arch.md)：`arch.launch` / `arch.barrier` 的 IR 语义与 include/api 源码形态保持同名职责映射。

## 目标

- 为后端无关的源码层提供统一的 launch / barrier 命名与最小类型边界。
- 明确 include/api 与后端私有 include 的职责拆分：include/api 只定义接口与最小语义，不承接线程实现、barrier 对象或具体 runtime。
- 明确 include/npu_demo 承接 runtime 行为，负责 `KernelContext` 的真实线程/同步实现、launch 注入与片上动态内存视图。
- 为后续 `include/npu_demo/Arch.h`、`test/include/api/test_arch.py` 与 `test/include/npu_demo/test_kernel_context.py` 提供稳定收敛目标。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- `include/api/Arch.h` 只声明公开接口，不得放入任何 `npu_demo` 或其他后端的线程创建、barrier 实现、固定硬件模板值或私有辅助函数。
- 本规范只冻结源码级 `launch` / `barrier` 公开合同，不定义 DSL/front-end、MLIR lowering、codegen 或 runtime 调度细节。
- include/api 只定义接口与最小语义；`KernelContext` 的真实线程索引、extent、barrier 共享对象、动态内存 backing store 与 launch 注入方式，都由 include/npu_demo 等后端私有层承接。
- `launch<block, thread, subthread, shared_memory_size>(...)` 的 `block/thread/subthread/shared_memory_size` 是编译期 launch extent，不是运行期位置参数。
- `callee` 的公开语义是“函数对象或等价可调用对象”；不得将 `"my_kernel"` 之类字符串名称暴露为长期稳定合同。
- `barrier(visibility, scope)` 的 `visibility` 元素类型必须是 `BarrierVisibility`；不得改成 `MemorySpace` 列表、字符串列表、自由文本或后端私有空间枚举。
- `BarrierScope` 公开成员允许后端实现做能力裁剪；若某后端暂不支持某个 scope，必须显式失败，不得静默降级为其他 scope。
- include/api 层不定义具体 `KernelContext` 的存储布局、生命周期、默认构造、线程绑定或注入方式；这些职责由后端私有 include 承接。
- `KernelContext::thread_id()` / `KernelContext::thread_num()` / `KernelContext::barrier(...)` / `KernelContext::get_dynamic_memory<Space, T>()` 是 include/api 层公开承诺的最小运行时接口面；后端可以补实现细节，但不得改名、改参数面或改成 target 私有别名。
- `thread_id()` / `thread_num()` / `get_dynamic_memory<Space>()` 是公开代码生成口径；后端必须保证它们可在已绑定 launch 上下文时直接调用。
- `TRANCE` 开启时，后端 launch 实现必须输出 `in func: npu_demo::launch template=<block=..., thread=..., subthread=..., shared_memory_size=...>`、`args =`、`arg0` callable 参数摘要，以及按 forwarded args 原始顺序输出的 `arg1`、`arg2`、... 参数摘要；关闭时不得产生诊断输出。

## API详细说明

### `BarrierVisibility(TSM, TLM) -> enum class`

- api：`BarrierVisibility(TSM, TLM) -> enum class`
- 参数：无。
- 返回值：公开枚举类型对象。
- 使用示例：

  ```cpp
BarrierVisibility visibility = BarrierVisibility::TLM;
```
- 功能说明：定义 `barrier(visibility, scope)` 的公开可见域枚举。
- 注意事项：稳定成员仅包含 `BarrierVisibility::TSM` 与 `BarrierVisibility::TLM`；`TLM` 表示覆盖 `MemorySpace::TLM1`、`MemorySpace::TLM2`、`MemorySpace::TLM3` 的聚合可见域，不是独立真实内存空间。

### `BarrierScope(BLOCK, THREAD, SUBTHREAD, GLOBAL) -> enum class`

- api：`BarrierScope(BLOCK, THREAD, SUBTHREAD, GLOBAL) -> enum class`
- 参数：无。
- 返回值：公开枚举类型对象。
- 使用示例：

  ```cpp
BarrierScope scope = BarrierScope::GLOBAL;
```
- 功能说明：定义公开同步范围枚举，供 `KernelContext::barrier(visibility, scope)` 使用。
- 注意事项：稳定成员仅包含 `BarrierScope::BLOCK`、`BarrierScope::THREAD`、`BarrierScope::SUBTHREAD`、`BarrierScope::GLOBAL`；后端可以显式拒绝暂不支持的 scope，但不得静默降级或改名。

### `template <long long block, long long thread, long long subthread, long long shared_memory_size, typename Callable, typename... Args> Status launch(Callable&& callee, Args&&... args)`

- api：`template <long long block, long long thread, long long subthread, long long shared_memory_size, typename Callable, typename... Args> Status launch(Callable&& callee, Args&&... args)`
- 参数：
  - `callee`：被调用函数名或符号引用，指定 call/launch 类操作的目标；类型 `Callable&&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
  - `args`：位置参数序列，按公开调用约定传递给目标函数或工具入口；类型 `Args&&...`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
- 返回值：`Status`，表示执行状态。
- 使用示例：

  ```cpp
Status status = launch<1, 4, 1, 0>(kernel_body, lhs, rhs, out);
```
- 功能说明：公开描述一次 kernel launch 请求，并把 `args...` 传递给 `callee`。
- 注意事项：公开调用形态固定为 `launch<block, thread, subthread, shared_memory_size>(callee, args...)`；`callee` 必须是函数对象或等价可调用对象，不得把字符串 callee 或运行期 extent 位置参数写成稳定合同。

### `class KernelContext`

- api：`class KernelContext`
- 参数：无。
- 返回值：`KernelContext` 实例。
- 使用示例：

  ```cpp
void inspect(KernelContext& ctx) {
    long long tid = ctx.thread_id();
    long long tnum = ctx.thread_num();
    ctx.barrier({BarrierVisibility::TSM}, BarrierScope::BLOCK);
}
```
- 功能说明：定义 `KernelContext` 公开类型。
- 注意事项：include/api 只冻结 `KernelContext` 的公开方法面，不定义存储布局、构造方式、线程绑定、barrier 共享对象或动态内存 backing store。

### `KernelContext::thread_id() const -> long long`

- api：`KernelContext::thread_id() const -> long long`
- 参数：无。
- 返回值：`long long`。
- 使用示例：

  ```cpp
auto tid = ctx.thread_id();
```
- 功能说明：执行 `thread_id`。
- 注意事项：返回值表示当前 launch 的运行时线程索引，不是 target registry 常量，也不是编译期模板值的文本替身。

### `KernelContext::thread_num() const -> long long`

- api：`KernelContext::thread_num() const -> long long`
- 参数：无。
- 返回值：`long long`。
- 使用示例：

  ```cpp
auto threads = ctx.thread_num();
```
- 功能说明：执行 `thread_num`。
- 注意事项：返回值表示当前 launch 的运行时线程总数；include/api 不规定具体整数实现类型，但源码层方法名与返回整型语义必须稳定。

### `KernelContext::barrier(std::initializer_list<BarrierVisibility> visibility, BarrierScope scope) const -> void`

- api：`KernelContext::barrier(std::initializer_list<BarrierVisibility> visibility, BarrierScope scope) const -> void`
- 参数：
  - `visibility`：可见性标识，指定 barrier、符号或公开对象的可见范围；类型 `std::initializer_list<BarrierVisibility>`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按可变容器传入时，是否修改输入必须以本接口功能说明和注意事项为准；非法值按该 API 的公开错误语义处理。
  - `scope`：作用域标识，指定 barrier、注册、查找或名字分配的有效范围；类型 `BarrierScope`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`void`。
- 使用示例：

  ```cpp
ctx.barrier({BarrierVisibility::TSM}, BarrierScope::THREAD);
```
- 功能说明：执行 `barrier`。
- 注意事项：`visibility` 与 `scope` 都是必填；`visibility` 元素类型固定为 `BarrierVisibility`，不得改成 `MemorySpace`、字符串、自由文本或后端私有空间枚举。

### `template <MemorySpace Space, typename T> KernelContext::get_dynamic_memory() const -> Memory<Space, T>`

- api：`template <MemorySpace Space, typename T> KernelContext::get_dynamic_memory() const -> Memory<Space, T>`
- 参数：无。
- 返回值：`Memory<Space, T>`。
- 使用示例：

  ```cpp
auto memory = ctx.get_dynamic_memory<TSM, float>();
```
- 功能说明：读取 `dynamic_memory`。
- 注意事项：该接口是 `KernelContext` 的公开成员模板；include/api 只定义接口与最小语义，具体 `Space` 合法性、容量和失败条件由后端私有层收口。

### `thread_id() -> S_INT`

- api：`thread_id() -> S_INT`
- 参数：无。
- 返回值：`S_INT`。
- 使用示例：

  ```cpp
S_INT tid = thread_id();
```
- 功能说明：执行 `thread_id`。
- 注意事项：公开语义与 `KernelContext::thread_id()` 一致；该 free helper 隐藏活动上下文绑定细节，生成代码不得再硬编码 `ctx.` 前缀。

### `thread_num() -> S_INT`

- api：`thread_num() -> S_INT`
- 参数：无。
- 返回值：`S_INT`。
- 使用示例：

  ```cpp
S_INT tnum = thread_num();
```
- 功能说明：执行 `thread_num`。
- 注意事项：公开语义与 `KernelContext::thread_num()` 一致；后端必须保证在已有活动 launch 上下文时可直接调用。

### `template <MemorySpace Space> get_dynamic_memory() -> DynamicMemoryRef<Space>`

- api：`template <MemorySpace Space> get_dynamic_memory() -> DynamicMemoryRef<Space>`
- 参数：无。
- 返回值：`DynamicMemoryRef<Space>`。
- 使用示例：

  ```cpp
Memory<TSM, float> memory = get_dynamic_memory<TSM>();
```
- 功能说明：读取 `dynamic_memory`。
- 注意事项：该 free helper 由赋值目标 `Memory<Space, T>` 决定元素类型；后端必须绑定到当前活动 launch 上下文，不得把返回值改成裸指针或 target 私有 buffer 类型作为公开合同。

## 测试

- 测试文件：
  - `test/include/api/test_arch.py`
  - `test/include/api/test_public_namespace.py`
  - `test/include/api/test_trance.py`
- 执行命令：
  - `pytest -q test/include/api/test_arch.py`
  - `pytest -q test/include/api/test_public_namespace.py`
  - `pytest -q test/include/api/test_trance.py`

### 测试目标

- 验证 `spec/include/api/Arch.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证公开导入、注册名、CLI 或命名空间入口只暴露 spec 定义的 API。
- 验证非法输入、边界条件和错误语义按公开合同失败。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-INCLUDE-API-ARCH-001 | 公开入口 | 锁定 `BarrierScope` 与 `launch<...>` 的公开符号面。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_include_api_arch_exports_public_launch_and_scope_contract`。 | 公开入口在“锁定 `BarrierScope` 与 `launch<...>` 的公开符号面。”场景下可导入、构造、注册或按名称发现。 | `test_include_api_arch_exports_public_launch_and_scope_contract` |
| TC-INCLUDE-API-ARCH-002 | 边界/异常 | 锁定字符串 callee 不属于长期公开合同。 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_include_api_arch_rejects_string_callee_contract`。 | “锁定字符串 callee 不属于长期公开合同。”场景按公开错误语义失败或被拒绝。 | `test_include_api_arch_rejects_string_callee_contract` |
| TC-INCLUDE-API-ARCH-003 | 公开入口 | 锁定 `include/api/Arch.h` 不混入 `npu_demo` 私有实现。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_include_api_arch_keeps_backend_impl_out_of_api_header`。 | 公开入口在“锁定 `include/api/Arch.h` 不混入 `npu_demo` 私有实现。”场景下可导入、构造、注册或按名称发现。 | `test_include_api_arch_keeps_backend_impl_out_of_api_header` |
| TC-INCLUDE-API-ARCH-004 | 执行结果 | `TRANCE` 开启时 launch 输出模板参数、callable 与 forwarded args 参数摘要。 | include `include/npu_demo/npu_demo.h`，传 `-DTRANCE`，执行公开 `npu_demo::launch<1, 2, 1, 0>(...)` 并传入两个运行期参数。 | 运行 `test_npu_demo_trance_stdout_memory_and_launch_format`。 | stdout 包含 `in func: npu_demo::launch template=<block=1, thread=2, subthread=1, shared_memory_size=0>`、`arg0 = callable[kernel_body]`、`arg1 = mem[...]` 与 `arg2 = 7`，且 `arg1` 先于 `arg2` 输出。 | `test_npu_demo_trance_stdout_memory_and_launch_format` |
