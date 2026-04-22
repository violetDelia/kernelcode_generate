# Memory

## 功能简介

定义统一对外 `Memory<Space, T>` API 规范，描述多维内存视图的元信息与访问接口，`rank` 为运行期维度。该规范不绑定具体后端实现，也不负责内存分配、释放、拷贝或运行时边界检查。

- `Memory<Space, T>` 是视图类型，仅保存 `data`、`shape`、`stride`、`rank`、`format` 元信息，`space` 通过模板参数固定，不拥有底层存储。
- 主合同入口为 `Memory<Space, T>`，允许使用 `Memory<GM, T>` 与 `Memory<MemorySpace::GM, T>` 等价写法。
- public function `build_contiguous_stride` 的成功调用入口固定为 `npu_demo::build_contiguous_stride(...)`；基础类型仍沿用当前全局公开类型边界。
- `get_shape(axis)` 与 `get_stride(axis)` 是 include/api 层统一公开的按轴查询接口。
- `view` 与 `reshape` 在公共层固定为成员式：`source.view<T>(offset, size, stride)`、`source.reshape(shape)`。

## 文档信息

- 创建者：`神秘人`
- 最后一次更改：`咯咯咯`
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

## 限制与边界

- `Memory<Space, T>` 是视图类型，不分配、释放或拥有底层数据。
- `space()` 返回模板参数 `Space` 对应的常量，不提供运行期可变 `space` 成员。
- 本规范不承诺运行时边界检查，不对空指针、越界索引、非法 `shape/stride` 提供保护。
- 调用方需要保证 `rank > 0`、`shape[i] > 0`、`stride[i] > 0`。
- 本规范不引入标准库容器、异常或动态分配依赖；实现需避免这些能力。
- `MemoryFormat` 仅公开 `Norm` 与 `CLast`，不定义字符串别名或额外布局成员。
- `MemorySpace` 仅公开 `GM`、`SM`、`LM`、`TSM`、`TLM1`、`TLM2`、`TLM3`，只表达空间分类，不表达容量、对齐或同步规则。
- `MemorySpace::TLM` 不再作为公开输入；需要聚合语义时应使用 `BarrierVisibility::TLM`。
- 本轮公共层只收口 `rank()`、`get_shape(axis)`、`get_stride(axis)`、`source.view<T>(...)`、`source.reshape(shape)` 与 `npu_demo::build_contiguous_stride(...)` 这组访问口径；若实现暂时保留 `shape()`、`stride()`、`element_count()`、`is_contiguous()`、`linear_offset()`、`at()` 等辅助接口，它们也不属于本轮稳定公开合同。
- `build_contiguous_stride` 不迁移 `Vector`、`Memory`、`MemorySpace` 等基础类型；这些类型继续来自 include/api 的当前公开位置。
- `view` 不再作为 DMA 自由函数暴露在公共层；`dma.view` 的源码目标固定桥接到成员式 `source.view<T>(...)`。
- `reshape(shape)` 只按当前公开子集收口为成员式接口，不在本轮扩展模板参数、隐式拷贝或空间改写语义。
- `include/api/Memory.h` 仅提供声明与类型边界，不提供函数体实现；具体后端实现需在各自 include 层提供。

## 公开接口

### `MemoryFormat`

功能说明：

- 表示 `Memory<Space, T>` 记录的布局格式枚举。

参数说明：

- 无参数。

使用示例：

```cpp
#include "include/api/Memory.h"

MemoryFormat format = MemoryFormat::CLast;
```

注意事项：

- 当前公开成员仅包含 `MemoryFormat::Norm` 与 `MemoryFormat::CLast`。

返回与限制：

- 返回类型：`MemoryFormat`。
- 返回语义：供 `Memory<Space, T>` 构造与查询时记录布局格式。
- 限制条件：本文档不定义除 `Norm`、`CLast` 之外的其他公开成员。

### `MemorySpace`

功能说明：

- 表示 `Memory<Space, T>` 所在的逻辑内存空间。

参数说明：

- 无参数。

使用示例：

```cpp
#include "include/api/Memory.h"

MemorySpace space = MemorySpace::SM;
```

注意事项：

- 当前公开成员仅包含 `MemorySpace::GM`、`MemorySpace::SM`、`MemorySpace::LM`、`MemorySpace::TSM`、`MemorySpace::TLM1`、`MemorySpace::TLM2`、`MemorySpace::TLM3`。
- 为便于模板参数书写，允许使用 `GM/SM/LM/TSM/TLM1/TLM2/TLM3` 作为等价常量。
- `MemorySpace::TLM` 不属于公开成员。

返回与限制：

- 返回类型：`MemorySpace`。
- 返回语义：供 `Memory<Space, T>` 构造与查询时记录内存空间。
- 限制条件：本文档不定义额外空间成员。

### `npu_demo::build_contiguous_stride(shape, rank, out_stride)`

功能说明：

- 根据 `shape` 与 `rank` 生成连续行主序 `stride`。

参数说明：

- `shape (const long long*)`：长度为 `rank` 的维度数组。
- `rank (unsigned long long)`：运行期维度。
- `out_stride (long long*)`：长度为 `rank` 的可写步幅缓冲区。

使用示例：

```cpp
#include "include/api/Memory.h"
#include "include/npu_demo/Memory.h"

long long shape[2] = {2, 3};
long long stride[2] = {0, 0};

npu_demo::build_contiguous_stride(shape, 2, stride);
```

注意事项：

- `out_stride` 必须由调用方提供有效缓冲区。
- 未限定的全局 `build_contiguous_stride` 名称不属于成功调用合同；调用方应使用 `npu_demo::build_contiguous_stride`。

返回与限制：

- 返回类型：`void`。
- 返回语义：填充 `out_stride`。
- 限制条件：`rank == 0` 或指针非法属于未定义行为。

### `Memory<Space, T>`

功能说明：

- 表示一个带 `data`、`shape`、`stride`、`rank`、`format` 元信息的多维内存视图，`space` 由模板参数固定。
- 通过运行期 `rank` 与数组指针描述维度与步幅。

参数说明：

- `Space (MemorySpace)`：内存空间模板参数。
- `T (type)`：元素类型。
- `data (T*)`：底层数据指针。
- `shape (const long long*)`：长度为 `rank` 的维度数组。
- `stride (const long long*)`：长度为 `rank` 的步幅数组。
- `rank (unsigned long long)`：运行期维度数。
- `format (MemoryFormat)`：布局格式，默认 `MemoryFormat::Norm`。

使用示例：

```cpp
#include "include/api/Memory.h"

float data[16] = {0};
long long shape[1] = {16};
long long stride[1] = {1};
long long offset_buf[1] = {0};
long long size_buf[1] = {8};
long long view_stride_buf[1] = {1};
long long reshape_shape_buf[2] = {4, 4};

Memory<GM, float> source(data, shape, stride, 1, MemoryFormat::Norm);
Vector offset(offset_buf, 1);
Vector size(size_buf, 1);
Vector view_stride(view_stride_buf, 1);
Vector reshape_shape(reshape_shape_buf, 2);

Memory<GM, float> tile = source.view<float>(offset, size, view_stride);
Memory<GM, float> reshaped = source.reshape(reshape_shape);
```

注意事项：

- 本规范不提供动态分配，`shape/stride` 由调用方持有并保证生命周期。
- `data()` 可保留可写与只读两类重载，供实现层与后端私有层使用。
- `get_shape(axis)` 与 `get_stride(axis)` 为统一公开查询接口；调用方需保证 `0 <= axis < rank()`。
- `view<T>(...)` 与 `reshape(shape)` 是当前公共层唯一稳定的视图变换接口；不得继续把以 `source` 为首参的自由函数 `view` 或其他同义 helper 写成 include/api 口径。
- 当前 `view<T>(...)` 先按公开子集收口为“`T` 与 `source` 元素类型一致”的成员式视图接口。

返回与限制：

- 返回类型：`Memory<Space, T>` 对象，以及其稳定公开方法返回的裸指针、枚举值或整型查询结果。
- 返回语义：
  - 构造时记录 `data/shape/stride/rank/format`。
  - `data()` 返回底层数据指针。
  - `get_shape(axis)` 返回 `shape[axis]`。
  - `get_stride(axis)` 返回 `stride[axis]`。
  - `rank()` 返回运行期维度数。
  - `format()` 返回当前记录的布局格式；`space()` 返回模板参数指定的内存空间。
  - `view<T>(offset, size, stride)` 返回成员式子视图。
  - `reshape(shape)` 返回成员式重解释视图。
- 限制条件：非法 `data`、`shape`、`stride` 或非法参数属于调用方违约；本规范不定义运行时异常、错误码或自动恢复行为。

### `get_shape(axis)`

功能说明：

- 返回指定轴的维度长度。

参数说明：

- `axis (unsigned long long)`：目标维度下标。

使用示例：

```cpp
#include "include/api/Memory.h"

long long n = mem.get_shape(0);
```

注意事项：

- `get_shape(axis)` 属于 include/api 统一公开接口，不得在后端私有 spec 中重新定义同义方法。
- 调用方需保证 `axis < rank()`。

返回与限制：

- 返回类型：`long long`。
- 返回语义：返回 `shape[axis]` 对应的维度长度。
- 限制条件：越界 `axis` 属于调用方违约。

### `get_stride(axis)`

功能说明：

- 返回指定轴的步长。

参数说明：

- `axis (unsigned long long)`：目标维度下标。

使用示例：

```cpp
#include "include/api/Memory.h"

long long n_stride = mem.get_stride(0);
```

注意事项：

- `get_stride(axis)` 属于 include/api 统一公开接口，不得在后端私有 spec 中重新定义同义方法。
- 调用方需保证 `axis < rank()`。

返回与限制：

- 返回类型：`long long`。
- 返回语义：返回 `stride[axis]` 对应的步长。
- 限制条件：越界 `axis` 属于调用方违约。

### `view<T>(offset, size, stride)`

功能说明：

- 返回当前 `Memory<Space, T>` 的成员式子视图。

参数说明：

- `T (type)`：当前公开子集下与 `source` 元素类型保持一致的模板参数。
- `offset (Vector)`：起始偏移向量。
- `size (Vector)`：子视图逻辑大小。
- `stride (Vector)`：子视图步进向量。

使用示例：

```cpp
#include "include/api/Memory.h"

long long offset_buf[1] = {0};
long long size_buf[1] = {16};
long long stride_buf[1] = {1};

Vector offset(offset_buf, 1);
Vector size(size_buf, 1);
Vector stride(stride_buf, 1);

Memory<GM, float> tile = source.view<float>(offset, size, stride);
```

注意事项：

- `view<T>(...)` 是本轮 include/api 唯一稳定视图 helper 入口。
- `offset/size/stride` 的长度必须与当前 memory 的 `rank()` 一致。
- 当前公开子集只要求 `T` 与 `source` 元素类型一致；不在本轮公开类型重解释。

返回与限制：

- 返回类型：`Memory<Space, T>`。
- 返回语义：返回逻辑窗口对应的子视图。
- 限制条件：静态越界、负 offset、非正 size/stride 均属于调用方违约。

### `reshape(shape)`

功能说明：

- 返回当前 `Memory<Space, T>` 的成员式重解释视图。

参数说明：

- `shape (Vector)`：目标形状向量。

使用示例：

```cpp
#include "include/api/Memory.h"

long long reshape_shape_buf[2] = {3, 2};
Vector reshape_shape(reshape_shape_buf, 2);

Memory<GM, float> reshaped = source.reshape(reshape_shape);
```

注意事项：

- `reshape(shape)` 固定为成员式接口；不再把自由函数 `reshape(source, ...)` 写成公共层口径。
- 当前公开语义只按公开子集收口，不在本轮扩展模板参数、显式空间改写或隐式数据复制。

返回与限制：

- 返回类型：`Memory<Space, T>`。
- 返回语义：返回按目标 `shape` 重解释后的视图。
- 限制条件：目标形状与底层元素总数是否一致，由实现按当前公开合同和后端规则显式处理。

## 测试

- 测试文件：[`test/include/api/test_memory.py`](../../../test/include/api/test_memory.py)、[`test/include/npu_demo/test_public_namespace.py`](../../../test/include/npu_demo/test_public_namespace.py)
- 执行命令：
  - `pytest -q test/include/api/test_memory.py`
  - `pytest -q test/include/npu_demo/test_public_namespace.py`
- 测试目标：
  - 验证 `Memory<Space, T>`、`MemoryFormat`、`MemorySpace` 的最小公共层语义可由后端实现承接。
  - 验证 `get_shape(axis)`、`get_stride(axis)` 是稳定公开查询接口。
  - 验证成员式 `source.view<T>(...)` 与 `source.reshape(shape)` 是当前公共层唯一视图变换口径。
  - 验证 `npu_demo::build_contiguous_stride(...)` 是连续步幅生成的唯一成功 public function 入口。
- 功能与用例清单：
  - `API-MEMORY-001`：`Memory<Space, T>` 的最小构造与查询语义可工作。
  - `NPU-DEMO-PUBLIC-002`：`npu_demo::build_contiguous_stride` 可经 `include/npu_demo/npu_demo.h` 正向编译运行，未限定的全局函数不作为成功路径。
