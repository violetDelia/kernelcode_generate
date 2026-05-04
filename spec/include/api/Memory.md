# Memory

## 功能简介

定义统一对外 `Memory<Space, T>` API 规范，描述多维内存视图的元信息与访问接口，`rank` 为运行期维度。该规范不绑定具体后端实现，也不负责内存分配、释放、拷贝或运行时边界检查。

- `Memory<Space, T>` 是视图类型，仅保存 `data`、`shape`、`stride`、`rank`、`format` 元信息，`space` 通过模板参数固定，不拥有底层存储。
- 主合同入口为 `Memory<Space, T>`，允许使用 `Memory<GM, T>` 与 `Memory<MemorySpace::GM, T>` 等价写法。
- public function `build_contiguous_stride` 的成功调用入口固定为 `npu_demo::build_contiguous_stride(...)`；基础类型仍沿用当前全局公开类型边界。
- `get_shape(axis)` 与 `get_stride(axis)` 是 include/api 层统一公开的按轴查询接口。
- `view` 与 `reshape` 在公共层固定为成员式：`source.view<T>(offset, size, stride)`、`source.reshape(shape)`。

## API 列表

- `MemoryFormat(Norm, CLast) -> enum class`
- `MemorySpace(GM, SM, LM, TSM, TLM1, TLM2, TLM3) -> enum class`
- `inline constexpr MemorySpace GM = MemorySpace::GM`
- `inline constexpr MemorySpace SM = MemorySpace::SM`
- `inline constexpr MemorySpace LM = MemorySpace::LM`
- `inline constexpr MemorySpace TSM = MemorySpace::TSM`
- `inline constexpr MemorySpace TLM1 = MemorySpace::TLM1`
- `inline constexpr MemorySpace TLM2 = MemorySpace::TLM2`
- `inline constexpr MemorySpace TLM3 = MemorySpace::TLM3`
- `void npu_demo::build_contiguous_stride(const long long* shape, unsigned long long rank, long long* out_stride)`
- `template <MemorySpace Space, typename T> class Memory(Space: MemorySpace, T: type)`
- `Memory::Memory(T* data, const long long* shape, const long long* stride, unsigned long long rank, MemoryFormat format = MemoryFormat::Norm)`
- `Memory::Memory(T* data, const long long* shape, unsigned long long rank, MemoryFormat format = MemoryFormat::Norm)`
- `Memory::data() -> T*`
- `Memory::data() const -> const T*`
- `Memory::shape() const -> const long long*`
- `Memory::stride() const -> const long long*`
- `Memory::rank() const -> unsigned long long`
- `Memory::format() const -> MemoryFormat`
- `Memory::space() const -> MemorySpace`
- `Memory::get_shape(unsigned long long axis) const -> long long`
- `Memory::get_stride(unsigned long long axis) const -> long long`
- `template <typename ViewT> Memory::view(const Vector& offset, const Vector& size, const Vector& stride) const -> Memory<Space, ViewT>`
- `Memory::reshape(const Vector& shape) const -> Memory<Space, T>`
- `Memory::element_count() const -> long long`
- `Memory::is_contiguous() const -> bool`
- `Memory::linear_offset(const long long* indices) const -> long long`
- `Memory::at(const long long* indices) -> T&`
- `Memory::at(const long long* indices) const -> const T&`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/include/api/Memory.md`](../../../spec/include/api/Memory.md)
- `统一头文件`：[`include/api/Memory.h`](../../../include/api/Memory.h)
- `功能实现`：[`include/npu_demo/Memory.h`](../../../include/npu_demo/Memory.h)
- `test`：
  - [`test/include/api/test_memory.py`](../../../test/include/api/test_memory.py)
  - [`test/include/npu_demo/test_public_namespace.py`](../../../test/include/npu_demo/test_public_namespace.py)

## 依赖

- [`spec/include/api/Core.md`](../../../spec/include/api/Core.md)：统一 `Vector`、`Status`、`StatusCode` 语义。

## 目标

- 为跨后端的多维数据视图提供统一的 API 标准与最小元信息表达，`rank` 使用运行期维度。
- 明确元素类型、维度、布局格式与内存空间等基础语义，便于上层在不复制数据的前提下传递张量信息。
- 为统一代码生成目标提供稳定的按轴查询接口，避免 `get_shape/get_stride` 被后端私有头文件重复定义。
- 明确 `build_contiguous_stride` 的 public function 入口为 `npu_demo::build_contiguous_stride(...)`，不再把未限定的全局函数作为成功调用合同。
- 为 `emit_c / gen_kernel` 收口唯一公共层成员接口：`source.view<T>(...)` 与 `source.reshape(shape)`。
- 明确删旧边界：公共层不再把以 `source` 为首参的自由函数 `view`、自由函数 `reshape`、以及一组旧辅助访问器写成稳定公开合同。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- `Memory<Space, T>` 是视图类型，不分配、释放或拥有底层数据。
- `space()` 返回模板参数 `Space` 对应的常量，不提供运行期可变 `space` 成员。
- 除各 API `注意事项` 已写明的稳定失败语义外，本规范不额外承诺运行时边界检查，不对空指针、越界索引、非法 `shape/stride` 提供额外保护。
- 调用方需要保证 `rank > 0`、`shape[i] > 0`、`stride[i] > 0`。
- 本规范不引入标准库容器、异常或动态分配依赖；实现需避免这些能力。
- `MemoryFormat` 仅公开 `Norm` 与 `CLast`，不定义字符串别名或额外布局成员。
- `MemorySpace` 仅公开 `GM`、`SM`、`LM`、`TSM`、`TLM1`、`TLM2`、`TLM3`，只表达空间分类，不表达容量、对齐或同步规则。
- `MemorySpace::TLM` 不再作为公开输入；需要聚合语义时应使用 `BarrierVisibility::TLM`。
- API 列表记录当前 `include/api/Memory.h` 承载的公开索引；各接口的调用条件、越界责任与非目标必须维护在对应 API 的 `注意事项`。
- `build_contiguous_stride` 不迁移 `Vector`、`Memory`、`MemorySpace` 等基础类型；这些类型继续来自 include/api 的当前公开位置。
- `view` 不再作为 DMA 自由函数暴露在公共层；`dma.view` 的源码目标固定桥接到成员式 `source.view<T>(...)`。
- `reshape(shape)` 只按当前公开子集收口为成员式接口，不在本轮扩展模板参数、隐式拷贝或空间改写语义。
- `include/api/Memory.h` 仅提供声明与类型边界，不提供函数体实现；具体后端实现需在各自 include 层提供。

## API详细说明

### `MemoryFormat(Norm, CLast) -> enum class`

- api：`MemoryFormat(Norm, CLast) -> enum class`
- 参数：无。
- 返回值：公开枚举类型对象。
- 使用示例：

  ```cpp
MemoryFormat format = MemoryFormat::CLast;
```
- 功能说明：定义 `Memory<Space, T>` 记录的布局格式枚举。
- 注意事项：稳定成员仅包含 `MemoryFormat::Norm` 与 `MemoryFormat::CLast`；不得把字符串别名、整数常量别名或额外布局成员写入公开合同。

### `MemorySpace(GM, SM, LM, TSM, TLM1, TLM2, TLM3) -> enum class`

- api：`MemorySpace(GM, SM, LM, TSM, TLM1, TLM2, TLM3) -> enum class`
- 参数：无。
- 返回值：公开枚举类型对象。
- 使用示例：

  ```cpp
MemorySpace space = MemorySpace::SM;
```
- 功能说明：定义 `Memory<Space, T>` 所在的逻辑内存空间枚举。
- 注意事项：稳定成员仅包含 `MemorySpace::GM`、`MemorySpace::SM`、`MemorySpace::LM`、`MemorySpace::TSM`、`MemorySpace::TLM1`、`MemorySpace::TLM2`、`MemorySpace::TLM3`；`MemorySpace::TLM` 不属于公开成员，聚合可见域应使用 `BarrierVisibility::TLM`。

### `inline constexpr MemorySpace GM = MemorySpace::GM`

- api：`inline constexpr MemorySpace GM = MemorySpace::GM`
- 参数：无。
- 返回值：`MemorySpace` 常量值。
- 使用示例：

  ```cpp
auto space = GM;
```
- 功能说明：定义 `GM` 公开常量。
- 注意事项：该常量只作为 `Memory<GM, T>` 模板参数简写；公开语义等价于 `Memory<MemorySpace::GM, T>`。

### `inline constexpr MemorySpace SM = MemorySpace::SM`

- api：`inline constexpr MemorySpace SM = MemorySpace::SM`
- 参数：无。
- 返回值：`MemorySpace` 常量值。
- 使用示例：

  ```cpp
auto space = SM;
```
- 功能说明：定义 `SM` 公开常量。
- 注意事项：该常量只作为 `Memory<SM, T>` 模板参数简写；公开语义等价于 `Memory<MemorySpace::SM, T>`。

### `inline constexpr MemorySpace LM = MemorySpace::LM`

- api：`inline constexpr MemorySpace LM = MemorySpace::LM`
- 参数：无。
- 返回值：`MemorySpace` 常量值。
- 使用示例：

  ```cpp
auto space = LM;
```
- 功能说明：定义 `LM` 公开常量。
- 注意事项：该常量只作为 `Memory<LM, T>` 模板参数简写；公开语义等价于 `Memory<MemorySpace::LM, T>`。

### `inline constexpr MemorySpace TSM = MemorySpace::TSM`

- api：`inline constexpr MemorySpace TSM = MemorySpace::TSM`
- 参数：无。
- 返回值：`MemorySpace` 常量值。
- 使用示例：

  ```cpp
auto space = TSM;
```
- 功能说明：定义 `TSM` 公开常量。
- 注意事项：该常量只作为 `Memory<TSM, T>` 模板参数简写；公开语义等价于 `Memory<MemorySpace::TSM, T>`。

### `inline constexpr MemorySpace TLM1 = MemorySpace::TLM1`

- api：`inline constexpr MemorySpace TLM1 = MemorySpace::TLM1`
- 参数：无。
- 返回值：`MemorySpace` 常量值。
- 使用示例：

  ```cpp
auto space = TLM1;
```
- 功能说明：定义 `TLM1` 公开常量。
- 注意事项：该常量只作为 `Memory<TLM1, T>` 模板参数简写；公开语义等价于 `Memory<MemorySpace::TLM1, T>`。

### `inline constexpr MemorySpace TLM2 = MemorySpace::TLM2`

- api：`inline constexpr MemorySpace TLM2 = MemorySpace::TLM2`
- 参数：无。
- 返回值：`MemorySpace` 常量值。
- 使用示例：

  ```cpp
auto space = TLM2;
```
- 功能说明：定义 `TLM2` 公开常量。
- 注意事项：该常量只作为 `Memory<TLM2, T>` 模板参数简写；公开语义等价于 `Memory<MemorySpace::TLM2, T>`。

### `inline constexpr MemorySpace TLM3 = MemorySpace::TLM3`

- api：`inline constexpr MemorySpace TLM3 = MemorySpace::TLM3`
- 参数：无。
- 返回值：`MemorySpace` 常量值。
- 使用示例：

  ```cpp
auto space = TLM3;
```
- 功能说明：定义 `TLM3` 公开常量。
- 注意事项：该常量只作为 `Memory<TLM3, T>` 模板参数简写；公开语义等价于 `Memory<MemorySpace::TLM3, T>`。

### `void npu_demo::build_contiguous_stride(const long long* shape, unsigned long long rank, long long* out_stride)`

- api：`void npu_demo::build_contiguous_stride(const long long* shape, unsigned long long rank, long long* out_stride)`
- 参数：
  - `shape`：形状序列，定义张量、内存或符号对象的维度大小；类型 `const long long*`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rank`：`rank` 输入值，参与 `build_contiguous_stride` 的公开处理流程；类型 `unsigned long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `out_stride`：步长序列；类型 `long long*`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```cpp
long long shape[2] = {2, 2};
long long stride[2] = {};
npu_demo::build_contiguous_stride(shape, 2, stride);
```
- 功能说明：构建 `contiguous_stride`。
- 注意事项：`out_stride` 必须由调用方提供有效缓冲区；未限定的全局 `build_contiguous_stride` 名称不属于成功调用合同，成功调用入口固定为 `npu_demo::build_contiguous_stride(...)`。

### `template <MemorySpace Space, typename T> class Memory(Space: MemorySpace, T: type)`

- api：`template <MemorySpace Space, typename T> class Memory(Space: MemorySpace, T: type)`
- 参数：无。
- 返回值：`Memory` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```cpp
float data[4] = {};
long long shape[2] = {2, 2};
Memory<GM, float> memory(data, shape, 2);
```
- 功能说明：定义带 `data`、`shape`、`stride`、`rank`、`format` 元信息的多维内存视图，`space` 由模板参数固定。
- 注意事项：`Memory<Space, T>` 不分配、不释放、不拥有底层数据；调用方必须保证 `data/shape/stride` 生命周期覆盖该视图使用期。

### `Memory::Memory(T* data, const long long* shape, const long long* stride, unsigned long long rank, MemoryFormat format = MemoryFormat::Norm)`

- api：`Memory::Memory(T* data, const long long* shape, const long long* stride, unsigned long long rank, MemoryFormat format = MemoryFormat::Norm)`
- 参数：
  - `data`：输入数据或缓冲区内容；类型 `T*`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `shape`：形状序列，定义张量、内存或符号对象的维度大小；类型 `const long long*`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `stride`：步长序列，定义各维度在底层线性布局中的跨距；类型 `const long long*`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rank`：`rank` 输入值，参与 `Memory` 的公开处理流程；类型 `unsigned long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `format`：内存格式或输出格式，定义当前对象的布局或文本输出形式；类型 `MemoryFormat`；默认值 `MemoryFormat::Norm`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Memory` 实例。
- 使用示例：

  ```cpp
float data[4] = {};
long long shape[2] = {2, 2};
Memory<GM, float> memory(data, shape, 2);
```
- 功能说明：构造 `Memory` 实例。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `Memory::Memory(T* data, const long long* shape, unsigned long long rank, MemoryFormat format = MemoryFormat::Norm)`

- api：`Memory::Memory(T* data, const long long* shape, unsigned long long rank, MemoryFormat format = MemoryFormat::Norm)`
- 参数：
  - `data`：输入数据或缓冲区内容；类型 `T*`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `shape`：形状序列，定义张量、内存或符号对象的维度大小；类型 `const long long*`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rank`：`rank` 输入值，参与 `Memory` 的公开处理流程；类型 `unsigned long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `format`：内存格式或输出格式，定义当前对象的布局或文本输出形式；类型 `MemoryFormat`；默认值 `MemoryFormat::Norm`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Memory` 实例。
- 使用示例：

  ```cpp
float data[4] = {};
long long shape[2] = {2, 2};
Memory<GM, float> memory(data, shape, 2);
```
- 功能说明：构造 `Memory` 实例。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `Memory::data() -> T*`

- api：`Memory::data() -> T*`
- 参数：无。
- 返回值：`T*`。
- 使用示例：

  ```cpp
auto* data = memory.data();
```
- 功能说明：执行 `data`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `Memory::data() const -> const T*`

- api：`Memory::data() const -> const T*`
- 参数：无。
- 返回值：`const T*`。
- 使用示例：

  ```cpp
auto* data = memory.data();
```
- 功能说明：执行 `data`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `Memory::shape() const -> const long long*`

- api：`Memory::shape() const -> const long long*`
- 参数：无。
- 返回值：`const long long*`。
- 使用示例：

  ```cpp
auto* shape = memory.shape();
```
- 功能说明：执行 `shape`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `Memory::stride() const -> const long long*`

- api：`Memory::stride() const -> const long long*`
- 参数：无。
- 返回值：`const long long*`。
- 使用示例：

  ```cpp
auto* stride = memory.stride();
```
- 功能说明：执行 `stride`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `Memory::rank() const -> unsigned long long`

- api：`Memory::rank() const -> unsigned long long`
- 参数：无。
- 返回值：`unsigned long long`。
- 使用示例：

  ```cpp
auto rank = memory.rank();
```
- 功能说明：执行 `rank`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `Memory::format() const -> MemoryFormat`

- api：`Memory::format() const -> MemoryFormat`
- 参数：无。
- 返回值：`MemoryFormat`。
- 使用示例：

  ```cpp
auto format = memory.format();
```
- 功能说明：执行 `format`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `Memory::space() const -> MemorySpace`

- api：`Memory::space() const -> MemorySpace`
- 参数：无。
- 返回值：`MemorySpace`。
- 使用示例：

  ```cpp
auto space = memory.space();
```
- 功能说明：执行 `space`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `Memory::get_shape(unsigned long long axis) const -> long long`

- api：`Memory::get_shape(unsigned long long axis) const -> long long`
- 参数：
  - `axis`：轴编号，指定 reduce、softmax、reshape 或维度相关操作的作用维度；类型 `unsigned long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`long long`。
- 使用示例：

  ```cpp
auto dim0 = memory.get_shape(0);
```
- 功能说明：读取 `shape`。
- 注意事项：该接口只读取公开状态；返回对象的内部可变结构不作为额外公开合同。

### `Memory::get_stride(unsigned long long axis) const -> long long`

- api：`Memory::get_stride(unsigned long long axis) const -> long long`
- 参数：
  - `axis`：轴编号，指定 reduce、softmax、reshape 或维度相关操作的作用维度；类型 `unsigned long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`long long`。
- 使用示例：

  ```cpp
auto stride0 = memory.get_stride(0);
```
- 功能说明：读取 `stride`。
- 注意事项：该接口只读取公开状态；返回对象的内部可变结构不作为额外公开合同。

### `template <typename ViewT> Memory::view(const Vector& offset, const Vector& size, const Vector& stride) const -> Memory<Space, ViewT>`

- api：`template <typename ViewT> Memory::view(const Vector& offset, const Vector& size, const Vector& stride) const -> Memory<Space, ViewT>`
- 参数：
  - `offset`：偏移序列或起始偏移，指定切片、访存或源码定位的起点；类型 `const Vector&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `size`：尺寸序列或元素数量，指定切片、缓冲区或范围的大小；类型 `const Vector&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `stride`：步长序列，定义各维度在底层线性布局中的跨距；类型 `const Vector&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Memory<Space, ViewT>`。
- 使用示例：

  ```cpp
auto tile = memory.view<float>(offset, size, stride);
```
- 功能说明：返回源 memory 的成员式子视图，不复制底层数据。
- 注意事项：`offset/size/stride` 的 rank 必须与源 memory rank 一致；npu_demo 实现支持 rank `1..8`；`offset[i] >= 0`、`size[i] > 0`、`stride[i] > 0`、`source.shape[i] > 0`、`source.stride[i] > 0`；结果 shape 等于 `size`，结果 stride 等于源 physical stride 与 view logical stride 的逐维乘积，结果 data 指针等于源 data 加多维线性 offset。公开失败关键字固定为 `memory.view: invalid rank`、`memory.view: vector_rank_mismatch`、`memory.view: invalid offset/size/stride`、`memory.view: invalid source shape`、`memory.view: invalid source stride`、`memory.view: overflow`、`memory.view: out_of_bounds` 或 `memory.view: rank_too_large`。

### `Memory::reshape(const Vector& shape) const -> Memory<Space, T>`

- api：`Memory::reshape(const Vector& shape) const -> Memory<Space, T>`
- 参数：
  - `shape`：形状序列，定义张量、内存或符号对象的维度大小；类型 `const Vector&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Memory<Space, T>`。
- 使用示例：

  ```cpp
auto reshaped = memory.reshape(shape);
```
- 功能说明：执行 `reshape`。
- 注意事项：输入 memory、offset、size、stride 和 dtype 必须符合 DMA operation 合同；非法组合必须稳定失败。

### `Memory::element_count() const -> long long`

- api：`Memory::element_count() const -> long long`
- 参数：无。
- 返回值：`long long`。
- 使用示例：

  ```cpp
auto count = memory.element_count();
```
- 功能说明：执行 `element_count`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `Memory::is_contiguous() const -> bool`

- api：`Memory::is_contiguous() const -> bool`
- 参数：无。
- 返回值：`bool`，表示判断结果。
- 使用示例：

  ```cpp
auto contiguous = memory.is_contiguous();
```
- 功能说明：执行 `is_contiguous`。
- 注意事项：该接口只读取公开状态；返回对象的内部可变结构不作为额外公开合同。

### `Memory::linear_offset(const long long* indices) const -> long long`

- api：`Memory::linear_offset(const long long* indices) const -> long long`
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

### `Memory::at(const long long* indices) -> T&`

- api：`Memory::at(const long long* indices) -> T&`
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

### `Memory::at(const long long* indices) const -> const T&`

- api：`Memory::at(const long long* indices) const -> const T&`
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

## 测试

- 测试文件：
  - `test/include/api/test_memory.py`
  - `test/include/npu_demo/test_public_namespace.py`
- 执行命令：
  - `pytest -q test/include/api/test_memory.py`
  - `pytest -q test/include/npu_demo/test_public_namespace.py`

### 测试目标

- 验证 `spec/include/api/Memory.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证 Memory/DMA 参数、布局、搬运或 verifier 行为。
- 验证公开导入、注册名、CLI 或命名空间入口只暴露 spec 定义的 API。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-INCLUDE-API-MEMORY-001 | 内存/DMA | `Memory<Space, T>` 的最小构造与查询语义可工作。 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `API-MEMORY-001`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`Memory<Space, T>` 的最小构造与查询语义可工作。”场景。 | `API-MEMORY-001` |
| TC-INCLUDE-API-MEMORY-002 | 公开入口 | `npu_demo::build_contiguous_stride` 可经 `include/npu_demo/npu_demo.h` 正向编译运行，未限定的全局函数不作为成功路径。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `NPU-DEMO-PUBLIC-002`。 | 公开入口在“`npu_demo::build_contiguous_stride` 可经 `include/npu_demo/npu_demo.h` 正向编译运行，未限定的全局函数不作为成功路径。”场景下可导入、构造、注册或按名称发现。 | `NPU-DEMO-PUBLIC-002` |
