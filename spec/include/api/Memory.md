# Memory.md

## 功能简介

定义统一对外 `Memory<Space, T>` API 规范，描述多维内存视图的元信息与访问接口，`rank` 为运行期维度。该规范不绑定具体后端实现，也不负责内存分配、释放、拷贝或运行时边界检查。

- `Memory<Space, T>` 是视图类型，仅保存 `data`、`shape`、`stride`、`rank`、`format` 元信息，`space` 通过模板参数固定，不拥有底层存储。
- 主合同入口为 `Memory<Space, T>`，允许使用 `Memory<GM, T>` 与 `Memory<MemorySpace::GM, T>` 等价写法。
- `get_shape(axis)` 与 `get_stride(axis)` 是 include/api 层统一公开的按轴查询接口；后端 spec 不得重新发明同义查询名称。
- 连续布局指 `stride` 等于按 `shape` 自后向前推导出的行主序步幅；若需要连续步幅，由调用方提供可写缓冲并显式生成。

## 文档信息

- 创建者：`神秘人`
- 最后一次更改：`jcc你莫辜负`
- `spec`：[`spec/include/api/Memory.md`](../../../spec/include/api/Memory.md)
- `功能实现`：[`include/api/Memory.h`](../../../include/api/Memory.h)
- `test`：[`test/include/api/test_memory.py`](../../../test/include/api/test_memory.py)

## 依赖

- 无（API 标准不绑定具体后端；实现可选择性复用该规范）。

## 目标

- 为跨后端的多维数据视图提供统一的 API 标准与最小元信息表达，`rank` 使用运行期维度。
- 明确元素类型、维度、布局格式与内存空间等基础语义，便于上层在不复制数据的前提下传递张量信息。
- 为统一代码生成目标提供稳定的按轴查询接口，避免 `get_shape/get_stride` 被后端私有头文件重复定义。
- 约束 API 不依赖 C++ 标准库与异常机制，便于在受限环境落地实现。

## 限制与边界

- `Memory<Space, T>` 是视图类型，不分配、释放或拥有底层数据。
- `space()` 返回模板参数 `Space` 对应的常量，不提供运行期可变 `space` 成员。
- 本规范不承诺运行时边界检查，不对空指针、越界索引、非法 `shape/stride` 提供保护。
- 调用方需要保证 `rank > 0`、`shape[i] > 0`、`stride[i] > 0`，并确保 `indices[i]` 位于合法范围内。
- 本规范不引入标准库容器、异常或动态分配依赖；实现需避免这些能力。
- `MemoryFormat` 仅公开 `Norm` 与 `CLast`，不定义字符串别名或额外布局成员。
- `MemorySpace` 仅公开 `GM`、`SM`、`LM`、`TSM`、`TLM`，只表达空间分类，不表达容量、对齐或同步规则。
- 本规范只覆盖 API 级别的视图语义，不定义算子级搬运、广播或计算行为。
- `include/api/Memory.h` 仅提供声明与类型边界，不提供函数体实现；具体后端实现需在各自 include 层提供（当前 `npu_demo` 实现头文件为 [`include/npu_demo/Memory.h`](../../../include/npu_demo/Memory.h)）。

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
- 该枚举只表达布局语义名称，不定义字符串值、别名等价关系或布局推导规则。

返回与限制：

- 返回类型：`MemoryFormat` 枚举值。
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

- 当前公开成员仅包含 `MemorySpace::GM`、`MemorySpace::SM`、`MemorySpace::LM`、`MemorySpace::TSM`、`MemorySpace::TLM`。
- 为便于模板参数书写，提供 `GM/SM/LM/TSM/TLM` 作为 `MemorySpace::...` 等价常量，可直接用于 `Memory<GM, T>`。
- 该枚举只负责空间分类，不承诺容量、带宽、地址合法性或跨空间访问规则。

返回与限制：

- 返回类型：`MemorySpace` 枚举值。
- 返回语义：供 `Memory<Space, T>` 构造与查询时记录内存空间。
- 限制条件：本文档不定义额外空间成员，也不把空间语义扩展为分配器或 runtime 句柄。

### `build_contiguous_stride(shape, rank, out_stride)`

功能说明：

- 根据 `shape` 与 `rank` 生成连续行主序 `stride`。
- 用于在无动态分配前提下生成默认步幅。

参数说明：

- `shape (const long long*)`：长度为 `rank` 的维度数组。
- `rank (unsigned long long)`：运行期维度。
- `out_stride (long long*)`：长度为 `rank` 的可写步幅缓冲区。

使用示例：

```cpp
long long shape[2] = {2, 3};
long long stride[2] = {0, 0};

build_contiguous_stride(shape, 2, stride);
```

注意事项：

- `out_stride` 必须由调用方提供有效缓冲区。
- 本接口不做运行时检查。

返回与限制：

- 返回类型：`void`。
- 返回语义：填充 `out_stride`。
- 限制条件：`rank == 0` 或指针非法属于未定义行为。

### `Memory<Space, T>`

功能说明：

- 表示一个带 `data`、`shape`、`stride`、`rank`、`format` 元信息的多维内存视图，`space` 由模板参数固定。
- 通过运行期 `rank` 与数组指针描述维度与步幅。

参数说明：

- `Space(MemorySpace)`：内存空间模板参数。
- `T(type)`：元素类型。
- `data(T*)`：底层数据指针。
- `shape(const long long*)`：长度为 `rank` 的维度数组。
- `stride(const long long*)`：长度为 `rank` 的步幅数组。
- `rank(unsigned long long)`：运行期维度数，必须大于 `0`。
- `format(MemoryFormat)`：布局格式，默认 `MemoryFormat::Norm`。

使用示例：

```cpp
#include "include/api/Memory.h"

int data[6] = {0, 1, 2, 3, 4, 5};
long long shape[2] = {2, 3};
long long stride[2] = {0, 0};
long long index[2] = {1, 2};

build_contiguous_stride(shape, 2, stride);

Memory<SM, int> mem(
    data,
    shape,
    stride,
    2,
    MemoryFormat::CLast);

long long offset = mem.linear_offset(index);
int value = mem.at(index);
```

注意事项：

- 本规范不提供动态分配，`shape/stride` 由调用方持有并保证生命周期。
- `data()` 提供 `T*` 与 `const T*` 两个重载；`at()` 提供 `T&` 与 `const T&` 两个重载。
- `shape()`、`stride()` 返回内部指针；调用方需自行保证后续访问合法。
- `get_shape(axis)` 与 `get_stride(axis)` 为统一公开查询接口；调用方需保证 `0 <= axis < rank()`。
- `linear_offset()` 与 `at()` 不做运行时范围检查。
- `Memory<GM, T>` 与 `Memory<MemorySpace::GM, T>` 视为等价写法。

返回与限制：

- 返回类型：`Memory<Space, T>` 对象，以及其公开方法返回的裸指针、枚举值、整型偏移或元素引用。
- 返回语义：
  - 构造时记录 `data/shape/stride/rank/format`。
  - `data()` 返回底层数据指针。
  - `shape()` 与 `stride()` 返回数组指针。
  - `get_shape(axis)` 返回 `shape[axis]`。
  - `get_stride(axis)` 返回 `stride[axis]`。
  - `rank()` 返回运行期维度数。
  - `format()` 返回当前记录的布局格式；`space()` 返回模板参数指定的内存空间。
  - `element_count()` 返回全部维度长度乘积。
  - `is_contiguous()` 返回当前 `stride` 是否等于连续行主序步幅。
  - `linear_offset()` 返回多维索引按 `stride` 计算出的线性偏移。
  - `at()` 返回指定索引位置的元素引用。
- 限制条件：
  - 非法 `data`、`shape`、`stride` 或索引会导致未定义行为。
  - 本文档不定义运行时异常、错误码或自动恢复行为。

### `get_shape(axis)`

功能说明：

- 返回指定轴的维度长度。

参数说明：

- `axis (unsigned long long)`：目标维度下标。

使用示例：

```cpp
#include "include/api/Memory.h"

long long n = mem.get_shape(0);
long long c = mem.get_shape(1);
```

注意事项：

- `get_shape(axis)` 属于 include/api 统一公开接口，不得在后端私有 spec 中重新定义同义方法。
- 调用方需保证 `axis < rank()`。
- 本规范不要求运行时越界检查。

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
long long c_stride = mem.get_stride(1);
```

注意事项：

- `get_stride(axis)` 属于 include/api 统一公开接口，不得在后端私有 spec 中重新定义同义方法。
- 调用方需保证 `axis < rank()`。
- 本规范不要求运行时越界检查。

返回与限制：

- 返回类型：`long long`。
- 返回语义：返回 `stride[axis]` 对应的步长。
- 限制条件：越界 `axis` 属于调用方违约。

## 测试

- 测试文件：[`test/include/api/test_memory.py`](../../../test/include/api/test_memory.py)
- 执行命令：`pytest -q test/include/api/test_memory.py`
- 测试目标：验证 include/api/Memory.h 声明可配合 include/npu_demo/Memory.h 实现编译运行。
- 功能与用例清单：`API-MEMORY-001`
