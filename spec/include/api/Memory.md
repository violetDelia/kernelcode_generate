# Memory.md

## 功能简介

定义 `api::Memory<T, Rank>` 的 API 标准与配套 `api::MemoryFormat`、`api::MemorySpace` 枚举，用于描述多维内存视图的元信息与访问接口。该规范不绑定具体后端实现，也不负责内存分配、释放、拷贝或运行时边界检查。

- `api::Memory<T, Rank>` 是视图类型，仅保存 `data`、`shape`、`stride`、`format`、`space` 元信息，不拥有底层存储。
- 连续布局指 `stride` 等于按 `shape` 自后向前推导出的行主序步幅；未显式传入 `stride` 时，由 `Memory` 自动生成该连续步幅。

## 文档信息

- 创建者：`神秘人`
- 最后一次更改：`摸鱼小分队`
- `spec`：[`spec/include/api/Memory.md`](../../../spec/include/api/Memory.md)
- `功能实现`：无（API 规范不绑定实现）
- `test`：无（API 规范不提供测试）

## 依赖

- 无（API 标准不绑定具体后端；实现可选择性复用该规范）。

## 目标

- 为跨后端的多维数据视图提供统一的 API 标准与最小元信息表达。
- 明确元素类型、维度、布局格式与内存空间等基础语义，便于上层在不复制数据的前提下传递张量信息。
- 约束 API 不依赖 C++ 标准库与异常机制，便于在受限环境落地实现。

## 限制与边界

- `api::Memory<T, Rank>` 是视图类型，不分配、释放或拥有底层数据。
- 本规范不承诺运行时边界检查，不对空指针、越界索引、非法 `shape/stride` 提供保护。
- 调用方需要保证 `Rank > 0`、`shape[i] > 0`、`stride[i] > 0`，并确保 `indices[i]` 位于合法范围内。
- 本规范不引入标准库容器、异常或动态分配依赖；实现需避免这些能力。
- `MemoryFormat` 仅公开 `Norm` 与 `CLast`，不定义字符串别名或额外布局成员。
- `MemorySpace` 仅公开 `GM`、`SM`、`LM`、`TSM`、`TLM`，只表达空间分类，不表达容量、对齐或同步规则。
- 本规范只覆盖 API 级别的视图语义，不定义算子级搬运、广播或计算行为。

## 公开接口

### `api::MemoryFormat`

功能说明：

- 表示 `api::Memory<T, Rank>` 记录的布局格式枚举。

参数说明：

- 无参数。

使用示例：

```cpp
#include "include/api/Memory.h"

api::MemoryFormat format = api::MemoryFormat::CLast;
```

注意事项：

- 当前公开成员仅包含 `MemoryFormat::Norm` 与 `MemoryFormat::CLast`。
- 该枚举只表达布局语义名称，不定义字符串值、别名等价关系或布局推导规则。

返回与限制：

- 返回类型：`api::MemoryFormat` 枚举值。
- 返回语义：供 `api::Memory<T, Rank>` 构造与查询时记录布局格式。
- 限制条件：本文档不定义除 `Norm`、`CLast` 之外的其他公开成员。

### `api::MemorySpace`

功能说明：

- 表示 `api::Memory<T, Rank>` 所在的逻辑内存空间。

参数说明：

- 无参数。

使用示例：

```cpp
#include "include/api/Memory.h"

api::MemorySpace space = api::MemorySpace::SM;
```

注意事项：

- 当前公开成员仅包含 `MemorySpace::GM`、`MemorySpace::SM`、`MemorySpace::LM`、`MemorySpace::TSM`、`MemorySpace::TLM`。
- 该枚举只负责空间分类，不承诺容量、带宽、地址合法性或跨空间访问规则。

返回与限制：

- 返回类型：`api::MemorySpace` 枚举值。
- 返回语义：供 `api::Memory<T, Rank>` 构造与查询时记录内存空间。
- 限制条件：本文档不定义额外空间成员，也不把空间语义扩展为分配器或 runtime 句柄。

### `api::Memory<T, Rank>`

功能说明：

- 表示一个带 `data`、`shape`、`stride`、`format`、`space` 元信息的多维内存视图。
- 支持显式步幅构造与自动连续步幅构造，并提供查询与访问接口。

参数说明：

- `T(type)`：元素类型。
- `Rank(unsigned long long)`：编译期固定维度数，必须大于 `0`。
- `data(T*)`：底层数据指针。
- `shape(const long long (&)[Rank])`：每一维长度数组。
- `stride(const long long (&)[Rank])`：每一维布局步幅数组。
- `format(api::MemoryFormat)`：布局格式，默认 `api::MemoryFormat::Norm`。
- `space(api::MemorySpace)`：内存空间，默认 `api::MemorySpace::GM`。

使用示例：

```cpp
#include "include/api/Memory.h"

int data[6] = {0, 1, 2, 3, 4, 5};
long long shape[2] = {2, 3};
long long stride[2] = {3, 1};
long long index[2] = {1, 2};

api::Memory<int, 2> explicit_mem(
    data,
    shape,
    stride,
    api::MemoryFormat::CLast,
    api::MemorySpace::SM);

api::Memory<int, 2> auto_mem(data, shape);
long long offset = explicit_mem.linear_offset(index);
int value = explicit_mem.at(index);
```

注意事项：

- `Rank == 0` 在编译期通过 `static_assert` 拒绝。
- 显式步幅构造会直接保存调用方传入的 `stride`；自动步幅构造会按连续行主序推导。
- `data()` 提供 `T*` 与 `const T*` 两个重载；`at()` 提供 `T&` 与 `const T&` 两个重载。
- `shape()`、`stride()` 返回内部数组首地址；调用方需自行保证后续访问合法。
- `linear_offset()` 与 `at()` 不做运行时范围检查。

返回与限制：

- 返回类型：`api::Memory<T, Rank>` 对象，以及其公开方法返回的裸指针、枚举值、整型偏移或元素引用。
- 返回语义：
  - 显式步幅构造返回保存传入 `shape/stride/format/space` 的视图对象。
  - 自动步幅构造返回按连续行主序推导 `stride` 的视图对象。
  - `data()` 返回底层数据指针。
  - `shape()` 与 `stride()` 返回内部数组首地址。
  - `rank()` 返回编译期维度数。
  - `format()` 与 `space()` 返回当前记录的布局格式与内存空间。
  - `element_count()` 返回全部维度长度乘积。
  - `is_contiguous()` 返回当前 `stride` 是否等于连续行主序步幅。
  - `linear_offset()` 返回多维索引按 `stride` 计算出的线性偏移。
  - `at()` 返回指定索引位置的元素引用。
- 限制条件：
  - 非法 `data`、`shape`、`stride` 或索引会导致未定义行为。
  - 本文档不定义运行时异常、错误码或自动恢复行为。

## 测试

- 测试文件：无（API 规范不提供测试实现）
- 执行命令：无（API 规范不提供测试实现）
- 测试目标：无（API 规范不提供测试范围）
- 功能与用例清单：无（API 规范不绑定测试用例）
