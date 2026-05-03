# Dma

## 功能简介

定义 include/api 层统一对外 DMA 操作 API 头文件规范（`include/api/Dma.h`），当前公共层收口 `npu_demo::alloc`、`npu_demo::fill`、`npu_demo::slice`、`npu_demo::deslice`、`npu_demo::transpose` 与 `npu_demo::broadcast` 六个 public function，面向后端无关的 `Memory<Space, T>` 与 `Vector` 抽象。

- `npu_demo::alloc<Space, T>(shape, stride, format)`：定义创建 DMA 临时 `Memory<Space, T>` 视图的公开接口。
- `npu_demo::fill(target, value)`：定义按标量填充目标块全部逻辑元素的公开接口。
- `npu_demo::slice(target, source, offset, size, stride)`：定义把源区域切片读取到预分配 `target` 的公开接口。
- `npu_demo::deslice(target, source, offset, size, stride)`：定义将源块写回目标区域的公开接口。
- `npu_demo::transpose(target, source, perm)`：定义按 `perm` 将源块物化转置到预分配 `target` 的公开接口。
- `npu_demo::broadcast(target, source)`：定义按 trailing-dimension 规则把 `source` 物化扩张到预分配 `target` 的公开接口。
- `view` 与 `reshape` 已移动到 `Memory` 的成员接口，不再保留以 `source` 为首参的公共层自由函数。
- 本规范只冻结统一 API 名称、参数形态、输入约束与错误边界；不绑定任何具体后端实现。

## API 列表

- `template <MemorySpace Space, typename T> Memory<Space, T> npu_demo::alloc(std::initializer_list<long long> shape, std::initializer_list<long long> stride, MemoryFormat format = MemoryFormat::Norm)`
- `template <MemorySpace Space, typename T> Status npu_demo::fill(Memory<Space, T>& target, const T& value)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T> Status npu_demo::slice(Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T> Status npu_demo::deslice(Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType> Status npu_demo::transpose(Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& perm)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType> Status npu_demo::broadcast(Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source)`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/include/api/Dma.md`](../../../spec/include/api/Dma.md)
- `统一头文件`：[`include/api/Dma.h`](../../../include/api/Dma.h) / [`include/api/Memory.h`](../../../include/api/Memory.h) / [`include/api/Core.h`](../../../include/api/Core.h)
- `功能实现`：[`include/npu_demo/Dma.h`](../../../include/npu_demo/Dma.h)
- `test`：
  - [`test/include/api/test_dma.py`](../../../test/include/api/test_dma.py)
  - [`test/include/npu_demo/test_public_namespace.py`](../../../test/include/npu_demo/test_public_namespace.py)

## 依赖

- [`spec/include/api/Core.md`](../../../spec/include/api/Core.md)：`Vector`、`Status`、`StatusCode` 统一基础契约。
- [`spec/include/api/Memory.md`](../../../spec/include/api/Memory.md)：`Memory<Space, T>`、`MemorySpace`、`get_shape/get_stride`、`view<T>`、`reshape` 统一语义。
- [`spec/include/api/cost/Dma.md`](../../../spec/include/api/cost/Dma.md)：定义与当前 DMA 公共层对应的成本 helper 合同。
- [`spec/operation/dma.md`](../../../spec/operation/dma.md)：高层 DMA 语义；同名概念需保持职责一致，但允许因分层不同而使用不同签名。

## 目标

- 为跨后端代码生成提供统一、稳定的 DMA 公开 API。
- 统一 `offset/size/stride` 的公开参数类型为 [`spec/include/api/Core.md`](../../../spec/include/api/Core.md) 中的 `Vector`。
- 明确 DMA public function 的成功调用入口统一为 `npu_demo::alloc(...)`、`npu_demo::fill(...)`、`npu_demo::slice(...)`、`npu_demo::deslice(...)`、`npu_demo::transpose(...)`、`npu_demo::broadcast(...)`。
- 明确 `slice/deslice` 的输入约束、返回语义与错误边界。
- 明确删旧边界：`view` / `reshape` 不再属于 DMA 公共层；`source-first deslice`、`store` 等旧公开形态退出本轮稳定口径。
- 为后续 `spec/operation/dma.md`、`spec/dialect/dma.md`、`spec/dsl/ast/mlir_gen.md`、`spec/dsl/gen_kernel/emit.md`、`spec/dsl/gen_kernel/gen_kernel.md` 提供统一收敛目标。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 本规范不定义 DMA 硬件调度、异步执行、带宽模型、barrier、launch、host wrapper 或后端私有运行时。
- 本规范只定义 `npu_demo::alloc`、`npu_demo::fill`、`npu_demo::slice`、`npu_demo::deslice`、`npu_demo::transpose`、`npu_demo::broadcast` 六个 DMA public function；`free/copy/cast/load/store` 等语义若实现暂存，也不属于本轮稳定公共层。
- `offset/size/stride` 的公开参数类型统一为 `Vector`；不得把 `std::vector<long long>`、`std::array<long long, N>`、裸 `long long[N]` 直接暴露成稳定公开签名。
- `alloc/slice/deslice` 的接口面向 `Memory<Space, T>`；不使用 `memory<rank, type>`、`memory<float>` 之类模板占位语言作为公开契约描述。
- `view` 与 `reshape` 已在 `Memory` 公共层收口；`Dma` 不再公开以 `source` 为首参的 `view` 自由函数。
- `deslice` 固定为 `target-first`；不得继续保留 `source-first deslice` 这种旧顺序公共口径。
- `slice` 与 `deslice` 都不改变元素类型；若实现侧需要类型变换，应通过其他明确接口处理。
- `transpose` 固定为 `target-first`；`perm[target_axis]` 表示 target 轴从 source 的哪一轴读取，调用方必须显式准备目标块。
- `slice` 是目标式接口：调用方必须先准备好 `target`；include/api 层不为 `slice` 隐式分配结果内存。
- `include/api/Dma.h` 仅提供声明与类型边界，不提供函数体实现；具体后端实现需在各自 include 层提供。
- 未限定的全局 `alloc`、`slice`、`deslice` 名称不属于成功调用合同；调用方应经 `namespace npu_demo` 消费。

## API详细说明

### `template <MemorySpace Space, typename T> Memory<Space, T> npu_demo::alloc(std::initializer_list<long long> shape, std::initializer_list<long long> stride, MemoryFormat format = MemoryFormat::Norm)`

- api：`template <MemorySpace Space, typename T> Memory<Space, T> npu_demo::alloc(std::initializer_list<long long> shape, std::initializer_list<long long> stride, MemoryFormat format = MemoryFormat::Norm)`
- 参数：
  - `shape`：形状序列，定义张量、内存或符号对象的维度大小；类型 `std::initializer_list<long long>`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按可变容器传入时，是否修改输入必须以本接口功能说明和注意事项为准；非法值按该 API 的公开错误语义处理。
  - `stride`：步长序列，定义各维度在底层线性布局中的跨距；类型 `std::initializer_list<long long>`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按可变容器传入时，是否修改输入必须以本接口功能说明和注意事项为准；非法值按该 API 的公开错误语义处理。
  - `format`：内存格式或输出格式，定义当前对象的布局或文本输出形式；类型 `MemoryFormat`；默认值 `MemoryFormat::Norm`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Memory<Space, T>`。
- 使用示例：

  ```cpp
auto tile = npu_demo::alloc<TSM, float>({16}, {1}, MemoryFormat::Norm);
```
- 功能说明：按给定 `shape/stride/format` 创建 DMA 临时 `Memory<Space, T>` 视图。
- 注意事项：`shape` 与 `stride` 的长度必须一致，且元素值必须满足 `Memory` 视图合同；成功调用入口固定为 `npu_demo::alloc(...)`，未限定的全局 `alloc` 不属于公开合同。

### `template <MemorySpace Space, typename T> Status npu_demo::fill(Memory<Space, T>& target, const T& value)`

- api：`template <MemorySpace Space, typename T> Status npu_demo::fill(Memory<Space, T>& target, const T& value)`
- 参数：
  - `target`：目标对象、目标名称或目标缓冲区，指定当前操作写入或作用的位置；类型 `Memory<Space, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
  - `value`：当前接口处理或写入的业务值，作为生成、转换、比较或存储语义的主要输入；类型 `const T&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Status`，表示执行状态。
- 使用示例：

  ```cpp
Status status = npu_demo::fill<TSM, float>(target, 0.0f);
```
- 功能说明：使用标量 `value` 填充 `target` 的全部逻辑元素。
- 注意事项：调用方必须显式提供目标块；`fill` 不分配内存、不返回新 `Memory`；未限定的全局 `fill` 不属于公开合同。

### `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T> Status npu_demo::slice(Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`

- api：`template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T> Status npu_demo::slice(Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`
- 参数：
  - `target`：目标对象、目标名称或目标缓冲区，指定当前操作写入或作用的位置；类型 `Memory<TargetSpace, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
  - `source`：源对象、源缓冲区或源文本，提供当前操作读取的数据来源；类型 `const Memory<SourceSpace, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `offset`：偏移序列或起始偏移，指定切片、访存或源码定位的起点；类型 `const Vector&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `size`：尺寸序列或元素数量，指定切片、缓冲区或范围的大小；类型 `const Vector&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `stride`：步长序列，定义各维度在底层线性布局中的跨距；类型 `const Vector&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Status`，表示执行状态。
- 使用示例：

  ```cpp
Status status = npu_demo::slice(target, source, offset, size, stride);
```
- 功能说明：从 `source` 读取切片区域，并写入预分配的 `target`。
- 注意事项：`target` 与 `source` 的元素类型必须一致；`offset/size/stride` 长度必须与 `source.rank()` 一致；`slice` 不隐式分配结果内存，未限定的全局 `slice` 不属于公开合同。

### `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T> Status npu_demo::deslice(Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`

- api：`template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T> Status npu_demo::deslice(Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`
- 参数：
  - `target`：目标对象、目标名称或目标缓冲区，指定当前操作写入或作用的位置；类型 `Memory<TargetSpace, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
  - `source`：源对象、源缓冲区或源文本，提供当前操作读取的数据来源；类型 `const Memory<SourceSpace, T>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `offset`：偏移序列或起始偏移，指定切片、访存或源码定位的起点；类型 `const Vector&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `size`：尺寸序列或元素数量，指定切片、缓冲区或范围的大小；类型 `const Vector&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `stride`：步长序列，定义各维度在底层线性布局中的跨距；类型 `const Vector&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Status`，表示执行状态。
- 使用示例：

  ```cpp
Status status = npu_demo::deslice(target, source, offset, size, stride);
```
- 功能说明：将 `source` 块写回 `target` 的指定区域。
- 注意事项：`deslice` 固定为 `target-first`；`source` 与 `target` 的元素类型必须一致；未限定的全局 `deslice` 与 `source-first deslice` 不属于公开合同。

### `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType> Status npu_demo::transpose(Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& perm)`

- api：`template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType> Status npu_demo::transpose(Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& perm)`
- 参数：
  - `target`：目标对象、目标名称或目标缓冲区，指定当前操作写入或作用的位置；类型 `Memory<TargetSpace, TargetType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
  - `source`：源对象、源缓冲区或源文本，提供当前操作读取的数据来源；类型 `const Memory<SourceSpace, SourceType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `perm`：维度排列序列，定义输出维度从输入维度读取的顺序；类型 `const Vector&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Status`，表示执行状态。
- 使用示例：

  ```cpp
Status status = npu_demo::transpose(target, source, Vector{1, 0});
```
- 功能说明：将 `source` 按 `perm` 物化转置到预分配 `target`。
- 注意事项：`target.rank()` 必须等于 `source.rank()`；`target.get_shape(axis)` 必须等于 `source.get_shape(perm[axis])`；`perm[target_axis]` 表示 target 轴从 source 的哪一轴读取。

### `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType> Status npu_demo::broadcast(Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source)`

- api：`template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType> Status npu_demo::broadcast(Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source)`
- 参数：
  - `target`：目标对象、目标名称或目标缓冲区，指定当前操作写入或作用的位置；类型 `Memory<TargetSpace, TargetType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
  - `source`：源对象、源缓冲区或源文本，提供当前操作读取的数据来源；类型 `const Memory<SourceSpace, SourceType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Status`，表示执行状态。
- 使用示例：

  ```cpp
Status status = npu_demo::broadcast<TSM, TSM, float, float>(target, source);
```
- 功能说明：将 `source` 按 trailing-dimension broadcast 规则物化到预分配 `target`。
- 注意事项：`source.rank()` 必须小于或等于 `target.rank()`，并按尾部维度对齐；对齐后的每个源维度必须等于目标维度或等于 `1`。

## 测试

- 测试文件：
  - `test/include/api/test_dma.py`
  - `test/include/npu_demo/test_public_namespace.py`
- 执行命令：
  - `pytest -q test/include/api/test_dma.py`
  - `pytest -q test/include/npu_demo/test_public_namespace.py`

### 测试目标

- 验证 `spec/include/api/Dma.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证 DSL、IR 或 EmitC 生成文本与编译链路符合公开合同。
- 验证 Memory/DMA 参数、布局、搬运或 verifier 行为。
- 验证公开导入、注册名、CLI 或命名空间入口只暴露 spec 定义的 API。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-INCLUDE-API-DMA-001 | 生成/编译 | `npu_demo::slice(target, source, ...)` 的最小目标式语义可工作。 | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `API-DMA-001`。 | 生成源码、IR 文本或编译结果体现“`npu_demo::slice(target, source, ...)` 的最小目标式语义可工作。”场景。 | `API-DMA-001` |
| TC-INCLUDE-API-DMA-002 | 生成/编译 | `npu_demo::deslice(target, source, ...)` 的最小目标式语义可工作。 | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `API-DMA-002`。 | 生成源码、IR 文本或编译结果体现“`npu_demo::deslice(target, source, ...)` 的最小目标式语义可工作。”场景。 | `API-DMA-002` |
| TC-INCLUDE-API-DMA-003 | 生成/编译 | `npu_demo::transpose(target, source, ...)` 的最小目标式语义可工作。 | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `API-DMA-003`。 | 生成源码、IR 文本或编译结果体现“`npu_demo::transpose(target, source, ...)` 的最小目标式语义可工作。”场景。 | `API-DMA-003` |
| TC-INCLUDE-API-DMA-004 | 内存/DMA | `npu_demo::fill/broadcast` 的最小目标式语义可工作。 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `API-DMA-003B`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`npu_demo::fill/broadcast` 的最小目标式语义可工作。”场景。 | `API-DMA-003B` |
| TC-INCLUDE-API-DMA-005 | 公开入口 | `npu_demo::alloc/fill/slice/deslice/transpose/broadcast` 可经 `include/npu_demo/npu_demo.h` 正向编译运行，未限定的全局函数不作为成功路径。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `NPU-DEMO-PUBLIC-002`。 | 公开入口在“`npu_demo::alloc/fill/slice/deslice/transpose/broadcast` 可经 `include/npu_demo/npu_demo.h` 正向编译运行，未限定的全局函数不作为成功路径。”场景下可导入、构造、注册或按名称发现。 | `NPU-DEMO-PUBLIC-002` |
