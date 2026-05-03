# cpu

## 功能简介

定义 CPU 后端 include/cpu 头文件规范，覆盖 `include/cpu/Memory.h` 与 `include/cpu/Nn.h` 的公开接口、行为与约束。当前基线要求 `cpu::Memory<Space, T>` 使用运行期 `rank`，并以 `MAX_DIM=8` 作为内部固定上限；逐元素/显式 broadcast、`add` 的 scalar overload（`Memory+scalar` / `scalar+Memory`，其中 `memory + const(i32)` 的目标源码保持 CPU 整数实参直传，`memory + symbol.int` 的 CPU 终点整数标量口径固定为 `long long`）、`exp`、`reduce_sum/reduce_min/reduce_max` 与 `img2col1d/img2col2d` CPU 叶子接口语义仍由 CPU include 层实现负责承接。

## API 列表

- `enum class cpu::MemoryFormat { Norm, CLast }`
- `enum class cpu::MemorySpace { GM, SM, LM, TSM, TLM }`
- `template <cpu::MemorySpace Space, typename T> class cpu::Memory`
- `cpu::Memory::Memory(T* data, unsigned long long rank, const long long* shape, const long long* stride, cpu::MemoryFormat format = cpu::MemoryFormat::Norm)`
- `cpu::Memory::Memory(T* data, unsigned long long rank, const long long* shape, cpu::MemoryFormat format = cpu::MemoryFormat::Norm)`
- `cpu::Memory::data() -> T*`
- `cpu::Memory::data() const -> const T*`
- `cpu::Memory::shape() const -> const long long*`
- `cpu::Memory::stride() const -> const long long*`
- `cpu::Memory::rank() const -> unsigned long long`
- `cpu::Memory::format() const -> cpu::MemoryFormat`
- `cpu::Memory::space() const -> cpu::MemorySpace`
- `cpu::Memory::element_count() const -> long long`
- `cpu::Memory::is_contiguous() const -> bool`
- `cpu::Memory::linear_offset(const long long* indices) const -> long long`
- `cpu::Memory::at(const long long* indices) -> T&`
- `cpu::Memory::at(const long long* indices) const -> const T&`
- `template <cpu::MemorySpace Space, typename T> void cpu::add(const cpu::Memory<Space, T>& lhs, const cpu::Memory<Space, T>& rhs, cpu::Memory<Space, T>& out)`
- `template <cpu::MemorySpace Space, typename T, typename ScalarT> void cpu::add(const cpu::Memory<Space, T>& lhs, ScalarT rhs_scalar, cpu::Memory<Space, T>& out)`
- `template <cpu::MemorySpace Space, typename T> void cpu::add(T lhs_scalar, const cpu::Memory<Space, T>& rhs, cpu::Memory<Space, T>& out)`
- `template <cpu::MemorySpace Space, typename T> void cpu::sub(const cpu::Memory<Space, T>& lhs, const cpu::Memory<Space, T>& rhs, cpu::Memory<Space, T>& out)`
- `template <cpu::MemorySpace Space, typename T> void cpu::mul(const cpu::Memory<Space, T>& lhs, const cpu::Memory<Space, T>& rhs, cpu::Memory<Space, T>& out)`
- `template <cpu::MemorySpace Space, typename T> void cpu::truediv(const cpu::Memory<Space, T>& lhs, const cpu::Memory<Space, T>& rhs, cpu::Memory<Space, T>& out)`
- `template <cpu::MemorySpace Space> void cpu::exp(const cpu::Memory<Space, float>& value, cpu::Memory<Space, float>& out)`
- `template <cpu::MemorySpace Space> void cpu::reduce_sum(const cpu::Memory<Space, float>& value, cpu::Memory<Space, float>& out, const long long* axes, unsigned long long axes_rank, bool keepdim)`
- `template <cpu::MemorySpace Space> void cpu::reduce_min(const cpu::Memory<Space, float>& value, cpu::Memory<Space, float>& out, const long long* axes, unsigned long long axes_rank, bool keepdim)`
- `template <cpu::MemorySpace Space> void cpu::reduce_max(const cpu::Memory<Space, float>& value, cpu::Memory<Space, float>& out, const long long* axes, unsigned long long axes_rank, bool keepdim)`
- `template <cpu::MemorySpace Space, typename T, typename PredT> void cpu::eq(const cpu::Memory<Space, T>& lhs, const cpu::Memory<Space, T>& rhs, cpu::Memory<Space, PredT>& out)`
- `template <cpu::MemorySpace Space, typename T, typename PredT> void cpu::ne(const cpu::Memory<Space, T>& lhs, const cpu::Memory<Space, T>& rhs, cpu::Memory<Space, PredT>& out)`
- `template <cpu::MemorySpace Space, typename T, typename PredT> void cpu::lt(const cpu::Memory<Space, T>& lhs, const cpu::Memory<Space, T>& rhs, cpu::Memory<Space, PredT>& out)`
- `template <cpu::MemorySpace Space, typename T, typename PredT> void cpu::le(const cpu::Memory<Space, T>& lhs, const cpu::Memory<Space, T>& rhs, cpu::Memory<Space, PredT>& out)`
- `template <cpu::MemorySpace Space, typename T, typename PredT> void cpu::gt(const cpu::Memory<Space, T>& lhs, const cpu::Memory<Space, T>& rhs, cpu::Memory<Space, PredT>& out)`
- `template <cpu::MemorySpace Space, typename T, typename PredT> void cpu::ge(const cpu::Memory<Space, T>& lhs, const cpu::Memory<Space, T>& rhs, cpu::Memory<Space, PredT>& out)`
- `template <cpu::MemorySpace Space, typename T> void cpu::broadcast(const cpu::Memory<Space, T>& input, cpu::Memory<Space, T>& out)`
- `template <cpu::MemorySpace Space> void cpu::img2col1d(const cpu::Memory<Space, float>& value, cpu::Memory<Space, float>& out, long long kw, long long sw, long long dw, long long pl, long long pr)`
- `template <cpu::MemorySpace Space> void cpu::img2col2d(const cpu::Memory<Space, float>& value, cpu::Memory<Space, float>& out, long long kh, long long kw, long long sh, long long sw, long long dh, long long dw, long long ph, long long pw, long long pl, long long pr)`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/include/cpu/cpu.md`](../../../spec/include/cpu/cpu.md)
- `功能实现`：[`include/cpu/Memory.h`](../../../include/cpu/Memory.h)、[`include/cpu/Nn.h`](../../../include/cpu/Nn.h)
- `test`：[`test/include/cpu/test_memory.py`](../../../test/include/cpu/test_memory.py)、[`test/include/cpu/test_nn.py`](../../../test/include/cpu/test_nn.py)

## 依赖

- [`include/cpu/Memory.h`](../../../include/cpu/Memory.h)：CPU 后端内存视图类型。
- [`include/cpu/Nn.h`](../../../include/cpu/Nn.h)：CPU 后端逐元素与显式 broadcast 运算。
- [`spec/operation/nn.md`](../../../spec/operation/nn.md)：逐元素与显式 broadcast 的语义基准。

## 目标

- 规范 CPU 后端 `Memory` 视图与 `Nn` 运算接口，便于与 `spec/operation/nn.md` 的语义对齐。
- 保持纯头文件、无标准库依赖、无异常机制的实现约束。
- 明确 CPU 后端 `Memory` 视图使用运行期 `rank` 的接口边界，并以 `MAX_DIM=8` 作为固定容量基线。
- 冻结 `cpu::add` 的标量终点口径：上游 `memory + const(i32)` 在 `target=cpu` 下保持 CPU 整数实参直传，`memory + symbol.int` 在 `target=cpu` 下固定映射为 `long long` 标量调用形态。
- 冻结 `cpu::exp(...)` 与 `cpu::reduce_sum/reduce_min/reduce_max(...)` 的稳定 CPU 公开接口，明确参数约束、输出契约与违约路径。
- 冻结 `cpu::img2col1d(...)` 与 `cpu::img2col2d(...)` 的稳定 CPU 公开接口，使 `emit_c/gen_kernel` 在 CPU 侧拥有固定调用目标。

## API详细说明

### `enum class cpu::MemoryFormat { Norm, CLast }`

- api：`enum class cpu::MemoryFormat { Norm, CLast }`
- 参数：无。
- 返回值：公开枚举类型对象。
- 使用示例：

  ```cpp
auto format = MemoryFormat::Norm;
```
- 功能说明：定义 `cpu` 公开枚举。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `enum class cpu::MemorySpace { GM, SM, LM, TSM, TLM }`

- api：`enum class cpu::MemorySpace { GM, SM, LM, TSM, TLM }`
- 参数：无。
- 返回值：公开枚举类型对象。
- 使用示例：

  ```cpp
auto space = MemorySpace::GM;
```
- 功能说明：定义 `cpu` 公开枚举。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `template <cpu::MemorySpace Space, typename T> class cpu::Memory`

- api：`template <cpu::MemorySpace Space, typename T> class cpu::Memory`
- 参数：无。
- 返回值：`Memory` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```cpp
// 使用公开 C++ include API：template <cpu::MemorySpace Space, typename T> class cpu::Memory
```
- 功能说明：执行 `Memory`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `cpu::Memory::Memory(T* data, unsigned long long rank, const long long* shape, const long long* stride, cpu::MemoryFormat format = cpu::MemoryFormat::Norm)`

- api：`cpu::Memory::Memory(T* data, unsigned long long rank, const long long* shape, const long long* stride, cpu::MemoryFormat format = cpu::MemoryFormat::Norm)`
- 参数：
  - `data`：输入数据或缓冲区内容；类型 `T*`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rank`：`rank` 输入值，参与 `Memory` 的公开处理流程；类型 `unsigned long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `shape`：形状序列，定义张量、内存或符号对象的维度大小；类型 `const long long*`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `stride`：步长序列，定义各维度在底层线性布局中的跨距；类型 `const long long*`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `format`：内存格式或输出格式，定义当前对象的布局或文本输出形式；类型 `cpu::MemoryFormat`；默认值 `cpu::MemoryFormat::Norm`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Memory` 实例。
- 使用示例：

  ```cpp
float data[4] = {};
long long shape[2] = {2, 2};
Memory<GM, float> memory(data, shape, 2);
```
- 功能说明：构造 `Memory` 实例。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `cpu::Memory::Memory(T* data, unsigned long long rank, const long long* shape, cpu::MemoryFormat format = cpu::MemoryFormat::Norm)`

- api：`cpu::Memory::Memory(T* data, unsigned long long rank, const long long* shape, cpu::MemoryFormat format = cpu::MemoryFormat::Norm)`
- 参数：
  - `data`：输入数据或缓冲区内容；类型 `T*`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rank`：`rank` 输入值，参与 `Memory` 的公开处理流程；类型 `unsigned long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `shape`：形状序列，定义张量、内存或符号对象的维度大小；类型 `const long long*`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `format`：内存格式或输出格式，定义当前对象的布局或文本输出形式；类型 `cpu::MemoryFormat`；默认值 `cpu::MemoryFormat::Norm`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Memory` 实例。
- 使用示例：

  ```cpp
float data[4] = {};
long long shape[2] = {2, 2};
Memory<GM, float> memory(data, shape, 2);
```
- 功能说明：构造 `Memory` 实例。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `cpu::Memory::data() -> T*`

- api：`cpu::Memory::data() -> T*`
- 参数：无。
- 返回值：`T*`。
- 使用示例：

  ```cpp
auto* data = memory.data();
```
- 功能说明：执行 `data`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `cpu::Memory::data() const -> const T*`

- api：`cpu::Memory::data() const -> const T*`
- 参数：无。
- 返回值：`const T*`。
- 使用示例：

  ```cpp
auto* data = memory.data();
```
- 功能说明：执行 `data`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `cpu::Memory::shape() const -> const long long*`

- api：`cpu::Memory::shape() const -> const long long*`
- 参数：无。
- 返回值：`const long long*`。
- 使用示例：

  ```cpp
auto* shape = memory.shape();
```
- 功能说明：执行 `shape`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `cpu::Memory::stride() const -> const long long*`

- api：`cpu::Memory::stride() const -> const long long*`
- 参数：无。
- 返回值：`const long long*`。
- 使用示例：

  ```cpp
auto* stride = memory.stride();
```
- 功能说明：执行 `stride`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `cpu::Memory::rank() const -> unsigned long long`

- api：`cpu::Memory::rank() const -> unsigned long long`
- 参数：无。
- 返回值：`unsigned long long`。
- 使用示例：

  ```cpp
auto rank = memory.rank();
```
- 功能说明：执行 `rank`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `cpu::Memory::format() const -> cpu::MemoryFormat`

- api：`cpu::Memory::format() const -> cpu::MemoryFormat`
- 参数：无。
- 返回值：`cpu::MemoryFormat`。
- 使用示例：

  ```cpp
auto format = memory.format();
```
- 功能说明：执行 `format`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `cpu::Memory::space() const -> cpu::MemorySpace`

- api：`cpu::Memory::space() const -> cpu::MemorySpace`
- 参数：无。
- 返回值：`cpu::MemorySpace`。
- 使用示例：

  ```cpp
auto space = memory.space();
```
- 功能说明：执行 `space`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `cpu::Memory::element_count() const -> long long`

- api：`cpu::Memory::element_count() const -> long long`
- 参数：无。
- 返回值：`long long`。
- 使用示例：

  ```cpp
auto count = memory.element_count();
```
- 功能说明：执行 `element_count`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `cpu::Memory::is_contiguous() const -> bool`

- api：`cpu::Memory::is_contiguous() const -> bool`
- 参数：无。
- 返回值：`bool`，表示判断结果。
- 使用示例：

  ```cpp
auto contiguous = memory.is_contiguous();
```
- 功能说明：执行 `is_contiguous`。
- 注意事项：该接口只读取公开状态；返回对象的内部可变结构不作为额外公开合同。

### `cpu::Memory::linear_offset(const long long* indices) const -> long long`

- api：`cpu::Memory::linear_offset(const long long* indices) const -> long long`
- 参数：
  - `indices`：`indices` 输入值，参与 `linear_offset` 的公开处理流程；类型 `const long long*`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`long long`。
- 使用示例：

  ```cpp
long long indices[2] = {0, 1};
auto offset = memory.linear_offset(indices);
```
- 功能说明：执行 `linear_offset`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `cpu::Memory::at(const long long* indices) -> T&`

- api：`cpu::Memory::at(const long long* indices) -> T&`
- 参数：
  - `indices`：`indices` 输入值，参与 `at` 的公开处理流程；类型 `const long long*`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`T&`。
- 使用示例：

  ```cpp
long long indices[2] = {0, 1};
auto& item = memory.at(indices);
```
- 功能说明：执行 `at`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `cpu::Memory::at(const long long* indices) const -> const T&`

- api：`cpu::Memory::at(const long long* indices) const -> const T&`
- 参数：
  - `indices`：`indices` 输入值，参与 `at` 的公开处理流程；类型 `const long long*`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`const T&`。
- 使用示例：

  ```cpp
long long indices[2] = {0, 1};
auto& item = memory.at(indices);
```
- 功能说明：执行 `at`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `template <cpu::MemorySpace Space, typename T> void cpu::add(const cpu::Memory<Space, T>& lhs, const cpu::Memory<Space, T>& rhs, cpu::Memory<Space, T>& out)`

- api：`template <cpu::MemorySpace Space, typename T> void cpu::add(const cpu::Memory<Space, T>& lhs, const cpu::Memory<Space, T>& rhs, cpu::Memory<Space, T>& out)`
- 参数：
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const cpu::Memory<Space, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const cpu::Memory<Space, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `cpu::Memory<Space, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```cpp
auto status = cpu::add(out, lhs, rhs);
```
- 功能说明：执行 `add`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `template <cpu::MemorySpace Space, typename T, typename ScalarT> void cpu::add(const cpu::Memory<Space, T>& lhs, ScalarT rhs_scalar, cpu::Memory<Space, T>& out)`

- api：`template <cpu::MemorySpace Space, typename T, typename ScalarT> void cpu::add(const cpu::Memory<Space, T>& lhs, ScalarT rhs_scalar, cpu::Memory<Space, T>& out)`
- 参数：
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const cpu::Memory<Space, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs_scalar`：`rhs_scalar` 输入值，参与 `add` 的公开处理流程；类型 `ScalarT`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `cpu::Memory<Space, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```cpp
auto status = cpu::add(out, lhs, rhs);
```
- 功能说明：执行 `add`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `template <cpu::MemorySpace Space, typename T> void cpu::add(T lhs_scalar, const cpu::Memory<Space, T>& rhs, cpu::Memory<Space, T>& out)`

- api：`template <cpu::MemorySpace Space, typename T> void cpu::add(T lhs_scalar, const cpu::Memory<Space, T>& rhs, cpu::Memory<Space, T>& out)`
- 参数：
  - `lhs_scalar`：`lhs_scalar` 输入值，参与 `add` 的公开处理流程；类型 `T`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const cpu::Memory<Space, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `cpu::Memory<Space, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```cpp
auto status = cpu::add(out, lhs, rhs);
```
- 功能说明：执行 `add`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `template <cpu::MemorySpace Space, typename T> void cpu::sub(const cpu::Memory<Space, T>& lhs, const cpu::Memory<Space, T>& rhs, cpu::Memory<Space, T>& out)`

- api：`template <cpu::MemorySpace Space, typename T> void cpu::sub(const cpu::Memory<Space, T>& lhs, const cpu::Memory<Space, T>& rhs, cpu::Memory<Space, T>& out)`
- 参数：
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const cpu::Memory<Space, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const cpu::Memory<Space, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `cpu::Memory<Space, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```cpp
auto status = cpu::sub(out, lhs, rhs);
```
- 功能说明：执行 `sub`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `template <cpu::MemorySpace Space, typename T> void cpu::mul(const cpu::Memory<Space, T>& lhs, const cpu::Memory<Space, T>& rhs, cpu::Memory<Space, T>& out)`

- api：`template <cpu::MemorySpace Space, typename T> void cpu::mul(const cpu::Memory<Space, T>& lhs, const cpu::Memory<Space, T>& rhs, cpu::Memory<Space, T>& out)`
- 参数：
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const cpu::Memory<Space, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const cpu::Memory<Space, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `cpu::Memory<Space, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```cpp
auto status = cpu::mul(out, lhs, rhs);
```
- 功能说明：执行 `mul`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `template <cpu::MemorySpace Space, typename T> void cpu::truediv(const cpu::Memory<Space, T>& lhs, const cpu::Memory<Space, T>& rhs, cpu::Memory<Space, T>& out)`

- api：`template <cpu::MemorySpace Space, typename T> void cpu::truediv(const cpu::Memory<Space, T>& lhs, const cpu::Memory<Space, T>& rhs, cpu::Memory<Space, T>& out)`
- 参数：
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const cpu::Memory<Space, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const cpu::Memory<Space, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `cpu::Memory<Space, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```cpp
auto status = cpu::truediv(out, lhs, rhs);
```
- 功能说明：执行 `truediv`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `template <cpu::MemorySpace Space> void cpu::exp(const cpu::Memory<Space, float>& value, cpu::Memory<Space, float>& out)`

- api：`template <cpu::MemorySpace Space> void cpu::exp(const cpu::Memory<Space, float>& value, cpu::Memory<Space, float>& out)`
- 参数：
  - `value`：当前接口处理或写入的业务值，作为生成、转换、比较或存储语义的主要输入；类型 `const cpu::Memory<Space, float>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `cpu::Memory<Space, float>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```cpp
auto status = cpu::exp(out, input);
```
- 功能说明：执行 `exp`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `template <cpu::MemorySpace Space> void cpu::reduce_sum(const cpu::Memory<Space, float>& value, cpu::Memory<Space, float>& out, const long long* axes, unsigned long long axes_rank, bool keepdim)`

- api：`template <cpu::MemorySpace Space> void cpu::reduce_sum(const cpu::Memory<Space, float>& value, cpu::Memory<Space, float>& out, const long long* axes, unsigned long long axes_rank, bool keepdim)`
- 参数：
  - `value`：当前接口处理或写入的业务值，作为生成、转换、比较或存储语义的主要输入；类型 `const cpu::Memory<Space, float>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `cpu::Memory<Space, float>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
  - `axes`：轴编号集合，指定多维操作需要处理的维度顺序；类型 `const long long*`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `axes_rank`：`axes_rank` 输入值，参与 `reduce_sum` 的公开处理流程；类型 `unsigned long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `keepdim`：`keepdim` 输入值，参与 `reduce_sum` 的公开处理流程；类型 `bool`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`bool`，表示判断结果。
- 使用示例：

  ```cpp
auto status = cpu::reduce_sum(out, input, 0);
```
- 功能说明：执行 `reduce_sum`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `template <cpu::MemorySpace Space> void cpu::reduce_min(const cpu::Memory<Space, float>& value, cpu::Memory<Space, float>& out, const long long* axes, unsigned long long axes_rank, bool keepdim)`

- api：`template <cpu::MemorySpace Space> void cpu::reduce_min(const cpu::Memory<Space, float>& value, cpu::Memory<Space, float>& out, const long long* axes, unsigned long long axes_rank, bool keepdim)`
- 参数：
  - `value`：当前接口处理或写入的业务值，作为生成、转换、比较或存储语义的主要输入；类型 `const cpu::Memory<Space, float>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `cpu::Memory<Space, float>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
  - `axes`：轴编号集合，指定多维操作需要处理的维度顺序；类型 `const long long*`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `axes_rank`：`axes_rank` 输入值，参与 `reduce_min` 的公开处理流程；类型 `unsigned long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `keepdim`：`keepdim` 输入值，参与 `reduce_min` 的公开处理流程；类型 `bool`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`bool`，表示判断结果。
- 使用示例：

  ```cpp
auto status = cpu::reduce_min(out, input, 0);
```
- 功能说明：执行 `reduce_min`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `template <cpu::MemorySpace Space> void cpu::reduce_max(const cpu::Memory<Space, float>& value, cpu::Memory<Space, float>& out, const long long* axes, unsigned long long axes_rank, bool keepdim)`

- api：`template <cpu::MemorySpace Space> void cpu::reduce_max(const cpu::Memory<Space, float>& value, cpu::Memory<Space, float>& out, const long long* axes, unsigned long long axes_rank, bool keepdim)`
- 参数：
  - `value`：当前接口处理或写入的业务值，作为生成、转换、比较或存储语义的主要输入；类型 `const cpu::Memory<Space, float>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `cpu::Memory<Space, float>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
  - `axes`：轴编号集合，指定多维操作需要处理的维度顺序；类型 `const long long*`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `axes_rank`：`axes_rank` 输入值，参与 `reduce_max` 的公开处理流程；类型 `unsigned long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `keepdim`：`keepdim` 输入值，参与 `reduce_max` 的公开处理流程；类型 `bool`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`bool`，表示判断结果。
- 使用示例：

  ```cpp
auto status = cpu::reduce_max(out, input, 0);
```
- 功能说明：执行 `reduce_max`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `template <cpu::MemorySpace Space, typename T, typename PredT> void cpu::eq(const cpu::Memory<Space, T>& lhs, const cpu::Memory<Space, T>& rhs, cpu::Memory<Space, PredT>& out)`

- api：`template <cpu::MemorySpace Space, typename T, typename PredT> void cpu::eq(const cpu::Memory<Space, T>& lhs, const cpu::Memory<Space, T>& rhs, cpu::Memory<Space, PredT>& out)`
- 参数：
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const cpu::Memory<Space, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const cpu::Memory<Space, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `cpu::Memory<Space, PredT>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```cpp
auto status = cpu::eq(out, lhs, rhs);
```
- 功能说明：执行 `eq`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `template <cpu::MemorySpace Space, typename T, typename PredT> void cpu::ne(const cpu::Memory<Space, T>& lhs, const cpu::Memory<Space, T>& rhs, cpu::Memory<Space, PredT>& out)`

- api：`template <cpu::MemorySpace Space, typename T, typename PredT> void cpu::ne(const cpu::Memory<Space, T>& lhs, const cpu::Memory<Space, T>& rhs, cpu::Memory<Space, PredT>& out)`
- 参数：
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const cpu::Memory<Space, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const cpu::Memory<Space, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `cpu::Memory<Space, PredT>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```cpp
auto status = cpu::ne(out, lhs, rhs);
```
- 功能说明：执行 `ne`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `template <cpu::MemorySpace Space, typename T, typename PredT> void cpu::lt(const cpu::Memory<Space, T>& lhs, const cpu::Memory<Space, T>& rhs, cpu::Memory<Space, PredT>& out)`

- api：`template <cpu::MemorySpace Space, typename T, typename PredT> void cpu::lt(const cpu::Memory<Space, T>& lhs, const cpu::Memory<Space, T>& rhs, cpu::Memory<Space, PredT>& out)`
- 参数：
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const cpu::Memory<Space, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const cpu::Memory<Space, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `cpu::Memory<Space, PredT>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```cpp
auto status = cpu::lt(out, lhs, rhs);
```
- 功能说明：执行 `lt`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `template <cpu::MemorySpace Space, typename T, typename PredT> void cpu::le(const cpu::Memory<Space, T>& lhs, const cpu::Memory<Space, T>& rhs, cpu::Memory<Space, PredT>& out)`

- api：`template <cpu::MemorySpace Space, typename T, typename PredT> void cpu::le(const cpu::Memory<Space, T>& lhs, const cpu::Memory<Space, T>& rhs, cpu::Memory<Space, PredT>& out)`
- 参数：
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const cpu::Memory<Space, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const cpu::Memory<Space, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `cpu::Memory<Space, PredT>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```cpp
auto status = cpu::le(out, lhs, rhs);
```
- 功能说明：执行 `le`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `template <cpu::MemorySpace Space, typename T, typename PredT> void cpu::gt(const cpu::Memory<Space, T>& lhs, const cpu::Memory<Space, T>& rhs, cpu::Memory<Space, PredT>& out)`

- api：`template <cpu::MemorySpace Space, typename T, typename PredT> void cpu::gt(const cpu::Memory<Space, T>& lhs, const cpu::Memory<Space, T>& rhs, cpu::Memory<Space, PredT>& out)`
- 参数：
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const cpu::Memory<Space, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const cpu::Memory<Space, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `cpu::Memory<Space, PredT>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```cpp
auto status = cpu::gt(out, lhs, rhs);
```
- 功能说明：执行 `gt`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `template <cpu::MemorySpace Space, typename T, typename PredT> void cpu::ge(const cpu::Memory<Space, T>& lhs, const cpu::Memory<Space, T>& rhs, cpu::Memory<Space, PredT>& out)`

- api：`template <cpu::MemorySpace Space, typename T, typename PredT> void cpu::ge(const cpu::Memory<Space, T>& lhs, const cpu::Memory<Space, T>& rhs, cpu::Memory<Space, PredT>& out)`
- 参数：
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const cpu::Memory<Space, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const cpu::Memory<Space, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `cpu::Memory<Space, PredT>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```cpp
auto status = cpu::ge(out, lhs, rhs);
```
- 功能说明：执行 `ge`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `template <cpu::MemorySpace Space, typename T> void cpu::broadcast(const cpu::Memory<Space, T>& input, cpu::Memory<Space, T>& out)`

- api：`template <cpu::MemorySpace Space, typename T> void cpu::broadcast(const cpu::Memory<Space, T>& input, cpu::Memory<Space, T>& out)`
- 参数：
  - `input`：输入对象，作为当前接口读取或转换的来源；类型 `const cpu::Memory<Space, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `cpu::Memory<Space, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```cpp
auto status = cpu::broadcast(target, source);
```
- 功能说明：执行 `broadcast`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `template <cpu::MemorySpace Space> void cpu::img2col1d(const cpu::Memory<Space, float>& value, cpu::Memory<Space, float>& out, long long kw, long long sw, long long dw, long long pl, long long pr)`

- api：`template <cpu::MemorySpace Space> void cpu::img2col1d(const cpu::Memory<Space, float>& value, cpu::Memory<Space, float>& out, long long kw, long long sw, long long dw, long long pl, long long pr)`
- 参数：
  - `value`：当前接口处理或写入的业务值，作为生成、转换、比较或存储语义的主要输入；类型 `const cpu::Memory<Space, float>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `cpu::Memory<Space, float>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
  - `kw`：卷积或池化窗口宽度，定义二维窗口在宽维方向的大小；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `sw`：宽度方向步长，定义卷积或池化窗口在宽维方向每次移动的距离；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `dw`：宽度方向 dilation，定义卷积或池化窗口在宽维方向的元素间隔；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `pl`：左侧 padding，定义一维或二维窗口左侧补边大小；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `pr`：右侧 padding，定义一维或二维窗口右侧补边大小；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```cpp
auto status = cpu::img2col1d(out, input, 3, 1, 1, 0, 0);
```
- 功能说明：执行 `img2col1d`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `template <cpu::MemorySpace Space> void cpu::img2col2d(const cpu::Memory<Space, float>& value, cpu::Memory<Space, float>& out, long long kh, long long kw, long long sh, long long sw, long long dh, long long dw, long long ph, long long pw, long long pl, long long pr)`

- api：`template <cpu::MemorySpace Space> void cpu::img2col2d(const cpu::Memory<Space, float>& value, cpu::Memory<Space, float>& out, long long kh, long long kw, long long sh, long long sw, long long dh, long long dw, long long ph, long long pw, long long pl, long long pr)`
- 参数：
  - `value`：当前接口处理或写入的业务值，作为生成、转换、比较或存储语义的主要输入；类型 `const cpu::Memory<Space, float>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `cpu::Memory<Space, float>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
  - `kh`：卷积或池化窗口高度，定义二维窗口在高维方向的大小；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `kw`：卷积或池化窗口宽度，定义二维窗口在宽维方向的大小；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `sh`：高度方向步长，定义卷积或池化窗口在高维方向每次移动的距离；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `sw`：宽度方向步长，定义卷积或池化窗口在宽维方向每次移动的距离；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `dh`：高度方向 dilation，定义卷积或池化窗口在高维方向的元素间隔；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `dw`：宽度方向 dilation，定义卷积或池化窗口在宽维方向的元素间隔；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `ph`：高度方向 padding，定义卷积或池化在高维方向补边大小；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `pw`：宽度方向 padding，定义卷积或池化在宽维方向补边大小；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `pl`：左侧 padding，定义一维或二维窗口左侧补边大小；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `pr`：右侧 padding，定义一维或二维窗口右侧补边大小；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```cpp
auto status = cpu::img2col2d(out, input, 3, 3, 1, 1, 1, 1, 0, 0, 0, 0);
```
- 功能说明：执行 `img2col2d`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。


## 额外补充

### `img2col1d/img2col2d` CPU API 契约

目标：

- 在 `spec/include/cpu/cpu.md` 冻结 `cpu::img2col1d(...)` 与 `cpu::img2col2d(...)` 的公开接口与最小行为契约，作为 `emit_c/gen_kernel` 的稳定 CPU 调用目标。

边界：

- 本文只定义 CPU include 层的公开接口；不定义 DSL lowering、`nn dialect` 结构、`mlir_gen(...)` 生成结构、pass 名称或完整 conv 模板。
- 本文只修改 `spec/include/cpu/cpu.md` 所覆盖的公开契约，不反向规定上游 AST/IR 该如何组织。

- 注意事项：

- CPU runtime 只依赖 `cpu::Memory<Space, T>`、普通标量参数和本层运行时契约，不依赖 AST 节点类型、`nn dialect` 运行时类型、`mlir_gen(...)` 生成结构或 pass 名称。
- `cpu::img2col1d(...)` 与 `cpu::img2col2d(...)` 是稳定公开名；不得继续新增 `cpu::img2col(...)` 笼统接口。
- 下文中的 `describe_cpu_api_contract(...)` 仅是验收辅助伪名，不是产品接口，不能在 `include/cpu` 中实现为公开 API。

依赖：

- 无硬依赖；允许与上游 `img2col` 公开名相关规格并行推进。
- 验收口径必须与固定公开名 `img2col1d/img2col2d` 保持一致，并以上游高层公开语义冻结文本为命名与公式基准。

验证命令：

- 无；由管理者人工核对文档。

验收标准：

- 本文必须能直接支撑下面这个验收辅助函数的 `expected` 结构；若文档无法推出同样的契约，则该规格不通过。

```python
def test_cpu_img2col_api_contract_v1():
    actual = describe_cpu_api_contract(
        names=["cpu::img2col1d", "cpu::img2col2d"],
        template_type="float",
    )
    expected = {
        "apis": {
            "cpu::img2col1d": {
                "signature": "void cpu::img2col1d(const cpu::Memory<Space, float>& value, cpu::Memory<Space, float>& out, long long kw, long long sw, long long dw, long long pl, long long pr)",
                "depends_only_on": [
                    "cpu::Memory<Space, T>",
                    "long long",
                    "rank-check",
                    "shape-formula-check",
                    "stride-consistency-check",
                ],
                "value_rank": 3,
                "out_rank": 3,
                "rejects": [
                    "value-rank-not-3",
                    "out-rank-not-3",
                    "shape-stride-mismatch-with-img2col1d-formula",
                    "kw-sw-dw-not-positive",
                    "pl-pr-negative",
                ],
            },
            "cpu::img2col2d": {
                "signature": "void cpu::img2col2d(const cpu::Memory<Space, float>& value, cpu::Memory<Space, float>& out, long long kh, long long kw, long long sh, long long sw, long long dh, long long dw, long long ph, long long pw, long long pl, long long pr)",
                "depends_only_on": [
                    "cpu::Memory<Space, T>",
                    "long long",
                    "rank-check",
                    "shape-formula-check",
                    "stride-consistency-check",
                ],
                "value_rank": 4,
                "out_rank": 3,
                "rejects": [
                    "value-rank-not-4",
                    "out-rank-not-3",
                    "shape-stride-mismatch-with-img2col2d-formula",
                    "kh-kw-sh-sw-dh-dw-not-positive",
                    "ph-pw-pl-pr-negative",
                ],
            },
        },
        "forbidden_dependencies": [
            "ast-node-types",
            "nn-dialect-runtime-types",
            "mlir-gen-structure",
            "pass-names",
        ],
        "forbidden_public_names": ["cpu::img2col"],
    }
```

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- `cpu::Memory<Space, T>` 以运行期 `rank` 描述维度，并在内部以 `MAX_DIM=8` 保存 `shape/stride`；调用方必须满足前置条件 `0 < rank <= 8`，实现不得对 `rank > 8` 做静默截断。
- 公开接口均为纯头文件模板与内联实现，不提供动态分配、异常或运行时边界检查。
- 逐元素与比较算子要求输入与输出形状一致，广播仅支持显式 `broadcast`，不提供隐式广播；仅 `cpu::add` 允许 `Memory+scalar` / `scalar+Memory` 两个公开 overload。
- `img2col1d/img2col2d` 只定义 CPU include 层叶子接口，不反向规定 AST 节点类型、`nn dialect` 运行时类型、`mlir_gen(...)` 生成结构或 pass 名称。
- `exp/reduce_*` 只定义 CPU include 层叶子接口，不反向规定 AST 节点类型、`nn dialect` 运行时类型、`mlir_gen(...)` 生成结构或 pass 名称。
- `exp/reduce_*` 当前公开口径固定为 `float` 入参与出参，不在 include 层提供自动类型提升或隐式 cast。
- `cpu::add` 的整数标量终点只冻结 `memory + const(i32)` 与 `memory + !symbol.int<"...">` 的 CPU 公开调用口径：前者保持整数实参直传，后者固定为 `long long`；本轮不定义 `f16/f32` mixed scalar 等其他混合标量提升规则，也不扩展到左标量整数形态。
- `reduce_*` 的 `axes` 由调用方提供规范化后的非空轴列表（去重、非负、升序）；`axis=None` 语义由上游在进入 include 层前显式展开。
- 禁止新增笼统 `cpu::img2col(...)` 公开名；CPU include 层只公开 `cpu::img2col1d(...)` 与 `cpu::img2col2d(...)`。
- 运行时错误由调用方规避；接口返回 `void`，不提供状态码。
- 本 spec 同时覆盖 `include/cpu/Memory.h` 与 `include/cpu/Nn.h`，原因是两者在 CPU 后端中紧密耦合并共用同一视图语义。

## 测试

- 测试文件：
  - `test/include/cpu/test_memory.py`
  - `test/include/cpu/test_nn.py`
- 执行命令：`pytest -q test/include/cpu/test_memory.py test/include/cpu/test_nn.py`

### 测试目标

- 验证 `spec/include/cpu/cpu.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证 DSL、IR 或 EmitC 生成文本与编译链路符合公开合同。
- 验证公开执行入口的返回值、输出或状态变化符合预期。
- 验证非法输入、边界条件和错误语义按公开合同失败。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-INCLUDE-CPU-CPU-001 | 生成/编译 | CPU-MEM-001 -> `test/include/cpu/test_memory.py::test_cpu_memory_header_compiles_and_runs` | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `pytest -q test/include/cpu/test_memory.py::test_cpu_memory_header_compiles_and_runs`。 | 生成源码、IR 文本或编译结果体现“CPU-MEM-001 -> `test/include/cpu/test_memory.py::test_cpu_memory_header_compiles_and_runs`”场景。 | test/include/cpu/test_memory.py::test_cpu_memory_header_compiles_and_runs |
| TC-INCLUDE-CPU-CPU-002 | 生成/编译 | CPU-MEM-002 -> `test/include/cpu/test_memory.py::test_cpu_memory_header_compiles_and_runs` | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `pytest -q test/include/cpu/test_memory.py::test_cpu_memory_header_compiles_and_runs`。 | 生成源码、IR 文本或编译结果体现“CPU-MEM-002 -> `test/include/cpu/test_memory.py::test_cpu_memory_header_compiles_and_runs`”场景。 | test/include/cpu/test_memory.py::test_cpu_memory_header_compiles_and_runs |
| TC-INCLUDE-CPU-CPU-003 | 生成/编译 | CPU-MEM-003 -> `test/include/cpu/test_memory.py::test_cpu_memory_header_compiles_and_runs` | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `pytest -q test/include/cpu/test_memory.py::test_cpu_memory_header_compiles_and_runs`。 | 生成源码、IR 文本或编译结果体现“CPU-MEM-003 -> `test/include/cpu/test_memory.py::test_cpu_memory_header_compiles_and_runs`”场景。 | test/include/cpu/test_memory.py::test_cpu_memory_header_compiles_and_runs |
| TC-INCLUDE-CPU-CPU-004 | 生成/编译 | CPU-MEM-004 -> `test/include/cpu/test_memory.py::test_cpu_memory_header_compiles_and_runs` | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `pytest -q test/include/cpu/test_memory.py::test_cpu_memory_header_compiles_and_runs`。 | 生成源码、IR 文本或编译结果体现“CPU-MEM-004 -> `test/include/cpu/test_memory.py::test_cpu_memory_header_compiles_and_runs`”场景。 | test/include/cpu/test_memory.py::test_cpu_memory_header_compiles_and_runs |
| TC-INCLUDE-CPU-CPU-005 | 执行结果 | CPU-MEM-005 -> `test/include/cpu/test_memory.py::test_cpu_memory_header_without_std_headers` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `pytest -q test/include/cpu/test_memory.py::test_cpu_memory_header_without_std_headers`。 | 命令返回码、输出、执行结果或状态变更体现“CPU-MEM-005 -> `test/include/cpu/test_memory.py::test_cpu_memory_header_without_std_headers`”场景。 | test/include/cpu/test_memory.py::test_cpu_memory_header_without_std_headers |
| TC-INCLUDE-CPU-CPU-006 | 执行结果 | CPU-MEM-006 -> `test/include/cpu/test_memory.py::test_cpu_memory_runtime_rank_max_dim` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `pytest -q test/include/cpu/test_memory.py::test_cpu_memory_runtime_rank_max_dim`。 | 命令返回码、输出、执行结果或状态变更体现“CPU-MEM-006 -> `test/include/cpu/test_memory.py::test_cpu_memory_runtime_rank_max_dim`”场景。 | test/include/cpu/test_memory.py::test_cpu_memory_runtime_rank_max_dim |
| TC-INCLUDE-CPU-CPU-007 | 边界/异常 | CPU-MEM-007 -> `test/include/cpu/test_memory.py::test_cpu_memory_runtime_rank_over_max_dim_fails` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `pytest -q test/include/cpu/test_memory.py::test_cpu_memory_runtime_rank_over_max_dim_fails`。 | “CPU-MEM-007 -> `test/include/cpu/test_memory.py::test_cpu_memory_runtime_rank_over_max_dim_fails`”场景按公开错误语义失败或被拒绝。 | test/include/cpu/test_memory.py::test_cpu_memory_runtime_rank_over_max_dim_fails |
| TC-INCLUDE-CPU-CPU-008 | 执行结果 | INC-NN-001 -> `test/include/cpu/test_nn.py::test_cpu_nn_add_success` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `pytest -q test/include/cpu/test_nn.py::test_cpu_nn_add_success`。 | 命令返回码、输出、执行结果或状态变更体现“INC-NN-001 -> `test/include/cpu/test_nn.py::test_cpu_nn_add_success`”场景。 | test/include/cpu/test_nn.py::test_cpu_nn_add_success |
| TC-INCLUDE-CPU-CPU-009 | 执行结果 | INC-NN-002 -> `test/include/cpu/test_nn.py::test_cpu_nn_compare_eq` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `pytest -q test/include/cpu/test_nn.py::test_cpu_nn_compare_eq`。 | 命令返回码、输出、执行结果或状态变更体现“INC-NN-002 -> `test/include/cpu/test_nn.py::test_cpu_nn_compare_eq`”场景。 | test/include/cpu/test_nn.py::test_cpu_nn_compare_eq |
| TC-INCLUDE-CPU-CPU-010 | 执行结果 | INC-NN-003 -> `test/include/cpu/test_nn.py::test_cpu_nn_broadcast_success` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `pytest -q test/include/cpu/test_nn.py::test_cpu_nn_broadcast_success`。 | 命令返回码、输出、执行结果或状态变更体现“INC-NN-003 -> `test/include/cpu/test_nn.py::test_cpu_nn_broadcast_success`”场景。 | test/include/cpu/test_nn.py::test_cpu_nn_broadcast_success |
| TC-INCLUDE-CPU-CPU-011 | 执行结果 | INC-NN-004 -> `test/include/cpu/test_nn.py::test_cpu_nn_broadcast_prepend_dim` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `pytest -q test/include/cpu/test_nn.py::test_cpu_nn_broadcast_prepend_dim`。 | 命令返回码、输出、执行结果或状态变更体现“INC-NN-004 -> `test/include/cpu/test_nn.py::test_cpu_nn_broadcast_prepend_dim`”场景。 | test/include/cpu/test_nn.py::test_cpu_nn_broadcast_prepend_dim |
| TC-INCLUDE-CPU-CPU-012 | 执行结果 | INC-NN-005 -> `test/include/cpu/test_nn.py::test_cpu_nn_mul_success` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `pytest -q test/include/cpu/test_nn.py::test_cpu_nn_mul_success`。 | 命令返回码、输出、执行结果或状态变更体现“INC-NN-005 -> `test/include/cpu/test_nn.py::test_cpu_nn_mul_success`”场景。 | test/include/cpu/test_nn.py::test_cpu_nn_mul_success |
| TC-INCLUDE-CPU-CPU-013 | 执行结果 | INC-NN-006 -> `test/include/cpu/test_nn.py::test_cpu_nn_sub_success` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `pytest -q test/include/cpu/test_nn.py::test_cpu_nn_sub_success`。 | 命令返回码、输出、执行结果或状态变更体现“INC-NN-006 -> `test/include/cpu/test_nn.py::test_cpu_nn_sub_success`”场景。 | test/include/cpu/test_nn.py::test_cpu_nn_sub_success |
| TC-INCLUDE-CPU-CPU-014 | 执行结果 | INC-NN-007 -> `test/include/cpu/test_nn.py::test_cpu_nn_truediv_success` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `pytest -q test/include/cpu/test_nn.py::test_cpu_nn_truediv_success`。 | 命令返回码、输出、执行结果或状态变更体现“INC-NN-007 -> `test/include/cpu/test_nn.py::test_cpu_nn_truediv_success`”场景。 | test/include/cpu/test_nn.py::test_cpu_nn_truediv_success |
| TC-INCLUDE-CPU-CPU-015 | 执行结果 | INC-NN-008 -> `test/include/cpu/test_nn.py::test_cpu_nn_compare_ne` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `pytest -q test/include/cpu/test_nn.py::test_cpu_nn_compare_ne`。 | 命令返回码、输出、执行结果或状态变更体现“INC-NN-008 -> `test/include/cpu/test_nn.py::test_cpu_nn_compare_ne`”场景。 | test/include/cpu/test_nn.py::test_cpu_nn_compare_ne |
| TC-INCLUDE-CPU-CPU-016 | 执行结果 | INC-NN-009 -> `test/include/cpu/test_nn.py::test_cpu_nn_compare_lt` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `pytest -q test/include/cpu/test_nn.py::test_cpu_nn_compare_lt`。 | 命令返回码、输出、执行结果或状态变更体现“INC-NN-009 -> `test/include/cpu/test_nn.py::test_cpu_nn_compare_lt`”场景。 | test/include/cpu/test_nn.py::test_cpu_nn_compare_lt |
| TC-INCLUDE-CPU-CPU-017 | 执行结果 | INC-NN-010 -> `test/include/cpu/test_nn.py::test_cpu_nn_compare_le` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `pytest -q test/include/cpu/test_nn.py::test_cpu_nn_compare_le`。 | 命令返回码、输出、执行结果或状态变更体现“INC-NN-010 -> `test/include/cpu/test_nn.py::test_cpu_nn_compare_le`”场景。 | test/include/cpu/test_nn.py::test_cpu_nn_compare_le |
| TC-INCLUDE-CPU-CPU-018 | 执行结果 | INC-NN-011 -> `test/include/cpu/test_nn.py::test_cpu_nn_compare_gt` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `pytest -q test/include/cpu/test_nn.py::test_cpu_nn_compare_gt`。 | 命令返回码、输出、执行结果或状态变更体现“INC-NN-011 -> `test/include/cpu/test_nn.py::test_cpu_nn_compare_gt`”场景。 | test/include/cpu/test_nn.py::test_cpu_nn_compare_gt |
| TC-INCLUDE-CPU-CPU-019 | 执行结果 | INC-NN-012 -> `test/include/cpu/test_nn.py::test_cpu_nn_compare_ge` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `pytest -q test/include/cpu/test_nn.py::test_cpu_nn_compare_ge`。 | 命令返回码、输出、执行结果或状态变更体现“INC-NN-012 -> `test/include/cpu/test_nn.py::test_cpu_nn_compare_ge`”场景。 | test/include/cpu/test_nn.py::test_cpu_nn_compare_ge |
| TC-INCLUDE-CPU-CPU-020 | 执行结果 | INC-NN-013 -> `test/include/cpu/test_nn.py::test_cpu_nn_img2col1d_success_and_signature` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `pytest -q test/include/cpu/test_nn.py::test_cpu_nn_img2col1d_success_and_signature`。 | 命令返回码、输出、执行结果或状态变更体现“INC-NN-013 -> `test/include/cpu/test_nn.py::test_cpu_nn_img2col1d_success_and_signature`”场景。 | test/include/cpu/test_nn.py::test_cpu_nn_img2col1d_success_and_signature |
| TC-INCLUDE-CPU-CPU-021 | 执行结果 | INC-NN-014 -> `test/include/cpu/test_nn.py::test_cpu_nn_img2col2d_success_and_signature` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `pytest -q test/include/cpu/test_nn.py::test_cpu_nn_img2col2d_success_and_signature`。 | 命令返回码、输出、执行结果或状态变更体现“INC-NN-014 -> `test/include/cpu/test_nn.py::test_cpu_nn_img2col2d_success_and_signature`”场景。 | test/include/cpu/test_nn.py::test_cpu_nn_img2col2d_success_and_signature |
| TC-INCLUDE-CPU-CPU-022 | 执行结果 | INC-NN-015 -> `test/include/cpu/test_nn.py::test_cpu_nn_img2col1d_contract_violation_traps` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `pytest -q test/include/cpu/test_nn.py::test_cpu_nn_img2col1d_contract_violation_traps`。 | 命令返回码、输出、执行结果或状态变更体现“INC-NN-015 -> `test/include/cpu/test_nn.py::test_cpu_nn_img2col1d_contract_violation_traps`”场景。 | test/include/cpu/test_nn.py::test_cpu_nn_img2col1d_contract_violation_traps |
| TC-INCLUDE-CPU-CPU-023 | 执行结果 | INC-NN-016 -> `test/include/cpu/test_nn.py::test_cpu_nn_img2col2d_contract_violation_traps` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `pytest -q test/include/cpu/test_nn.py::test_cpu_nn_img2col2d_contract_violation_traps`。 | 命令返回码、输出、执行结果或状态变更体现“INC-NN-016 -> `test/include/cpu/test_nn.py::test_cpu_nn_img2col2d_contract_violation_traps`”场景。 | test/include/cpu/test_nn.py::test_cpu_nn_img2col2d_contract_violation_traps |
| TC-INCLUDE-CPU-CPU-024 | 执行结果 | INC-NN-017 -> `test/include/cpu/test_nn.py::test_cpu_nn_img2col1d_stride_violation_traps` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `pytest -q test/include/cpu/test_nn.py::test_cpu_nn_img2col1d_stride_violation_traps`。 | 命令返回码、输出、执行结果或状态变更体现“INC-NN-017 -> `test/include/cpu/test_nn.py::test_cpu_nn_img2col1d_stride_violation_traps`”场景。 | test/include/cpu/test_nn.py::test_cpu_nn_img2col1d_stride_violation_traps |
| TC-INCLUDE-CPU-CPU-025 | 执行结果 | INC-NN-018 -> `test/include/cpu/test_nn.py::test_cpu_nn_img2col_generic_name_is_forbidden` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `pytest -q test/include/cpu/test_nn.py::test_cpu_nn_img2col_generic_name_is_forbidden`。 | 命令返回码、输出、执行结果或状态变更体现“INC-NN-018 -> `test/include/cpu/test_nn.py::test_cpu_nn_img2col_generic_name_is_forbidden`”场景。 | test/include/cpu/test_nn.py::test_cpu_nn_img2col_generic_name_is_forbidden |
| TC-INCLUDE-CPU-CPU-026 | 执行结果 | INC-NN-019 -> `test/include/cpu/test_nn.py::test_cpu_nn_exp_success` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `pytest -q test/include/cpu/test_nn.py::test_cpu_nn_exp_success`。 | 命令返回码、输出、执行结果或状态变更体现“INC-NN-019 -> `test/include/cpu/test_nn.py::test_cpu_nn_exp_success`”场景。 | test/include/cpu/test_nn.py::test_cpu_nn_exp_success |
| TC-INCLUDE-CPU-CPU-027 | 执行结果 | INC-NN-020 -> `test/include/cpu/test_nn.py::test_cpu_nn_exp_contract_violation_traps` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `pytest -q test/include/cpu/test_nn.py::test_cpu_nn_exp_contract_violation_traps`。 | 命令返回码、输出、执行结果或状态变更体现“INC-NN-020 -> `test/include/cpu/test_nn.py::test_cpu_nn_exp_contract_violation_traps`”场景。 | test/include/cpu/test_nn.py::test_cpu_nn_exp_contract_violation_traps |
| TC-INCLUDE-CPU-CPU-028 | 执行结果 | INC-NN-021 -> `test/include/cpu/test_nn.py::test_cpu_nn_reduce_sum_success` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `pytest -q test/include/cpu/test_nn.py::test_cpu_nn_reduce_sum_success`。 | 命令返回码、输出、执行结果或状态变更体现“INC-NN-021 -> `test/include/cpu/test_nn.py::test_cpu_nn_reduce_sum_success`”场景。 | test/include/cpu/test_nn.py::test_cpu_nn_reduce_sum_success |
| TC-INCLUDE-CPU-CPU-029 | 执行结果 | INC-NN-022 -> `test/include/cpu/test_nn.py::test_cpu_nn_reduce_sum_axis_contract_violation_traps` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `pytest -q test/include/cpu/test_nn.py::test_cpu_nn_reduce_sum_axis_contract_violation_traps`。 | 命令返回码、输出、执行结果或状态变更体现“INC-NN-022 -> `test/include/cpu/test_nn.py::test_cpu_nn_reduce_sum_axis_contract_violation_traps`”场景。 | test/include/cpu/test_nn.py::test_cpu_nn_reduce_sum_axis_contract_violation_traps |
| TC-INCLUDE-CPU-CPU-030 | 执行结果 | INC-NN-023 -> `test/include/cpu/test_nn.py::test_cpu_nn_reduce_min_success` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `pytest -q test/include/cpu/test_nn.py::test_cpu_nn_reduce_min_success`。 | 命令返回码、输出、执行结果或状态变更体现“INC-NN-023 -> `test/include/cpu/test_nn.py::test_cpu_nn_reduce_min_success`”场景。 | test/include/cpu/test_nn.py::test_cpu_nn_reduce_min_success |
| TC-INCLUDE-CPU-CPU-031 | 执行结果 | INC-NN-024 -> `test/include/cpu/test_nn.py::test_cpu_nn_reduce_min_empty_extent_traps` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `pytest -q test/include/cpu/test_nn.py::test_cpu_nn_reduce_min_empty_extent_traps`。 | 命令返回码、输出、执行结果或状态变更体现“INC-NN-024 -> `test/include/cpu/test_nn.py::test_cpu_nn_reduce_min_empty_extent_traps`”场景。 | test/include/cpu/test_nn.py::test_cpu_nn_reduce_min_empty_extent_traps |
| TC-INCLUDE-CPU-CPU-032 | 执行结果 | INC-NN-025 -> `test/include/cpu/test_nn.py::test_cpu_nn_reduce_max_success` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `pytest -q test/include/cpu/test_nn.py::test_cpu_nn_reduce_max_success`。 | 命令返回码、输出、执行结果或状态变更体现“INC-NN-025 -> `test/include/cpu/test_nn.py::test_cpu_nn_reduce_max_success`”场景。 | test/include/cpu/test_nn.py::test_cpu_nn_reduce_max_success |
| TC-INCLUDE-CPU-CPU-033 | 执行结果 | INC-NN-026 -> `test/include/cpu/test_nn.py::test_cpu_nn_reduce_max_empty_extent_traps` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `pytest -q test/include/cpu/test_nn.py::test_cpu_nn_reduce_max_empty_extent_traps`。 | 命令返回码、输出、执行结果或状态变更体现“INC-NN-026 -> `test/include/cpu/test_nn.py::test_cpu_nn_reduce_max_empty_extent_traps`”场景。 | test/include/cpu/test_nn.py::test_cpu_nn_reduce_max_empty_extent_traps |
| TC-INCLUDE-CPU-CPU-034 | 执行结果 | INC-NN-027 -> `test/include/cpu/test_nn.py::test_cpu_nn_add_scalar_rhs_success` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `pytest -q test/include/cpu/test_nn.py::test_cpu_nn_add_scalar_rhs_success`。 | 命令返回码、输出、执行结果或状态变更体现“INC-NN-027 -> `test/include/cpu/test_nn.py::test_cpu_nn_add_scalar_rhs_success`”场景。 | test/include/cpu/test_nn.py::test_cpu_nn_add_scalar_rhs_success |
| TC-INCLUDE-CPU-CPU-035 | 执行结果 | INC-NN-028 -> `test/include/cpu/test_nn.py::test_cpu_nn_add_scalar_lhs_success` | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `pytest -q test/include/cpu/test_nn.py::test_cpu_nn_add_scalar_lhs_success`。 | 命令返回码、输出、执行结果或状态变更体现“INC-NN-028 -> `test/include/cpu/test_nn.py::test_cpu_nn_add_scalar_lhs_success`”场景。 | test/include/cpu/test_nn.py::test_cpu_nn_add_scalar_lhs_success |
