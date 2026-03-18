# Memory.md

## 功能简介

定义 CPU 侧纯头文件张量视图模板 `cpu::Memory<T, Rank>`，用于描述一段外部连续或跨步存储的多维数据，不负责分配、释放或拷贝底层内存。

## 文档信息

- 创建者：`神秘人`
- 最后一次更改：`摸鱼小分队`
- `spec`：[`spec/include/cpu/Memory.md`](../../../spec/include/cpu/Memory.md)
- `test`：[`test/include/cpu/test_memory.py`](../../../test/include/cpu/test_memory.py)
- `功能实现`：[`include/cpu/Memory.h`](../../../include/cpu/Memory.h)

## 设计目标

- 提供一个不依赖标准库容器、字符串、异常体系的纯头文件 `Memory` 模板。
- 仅表达 `data + shape + stride + format + memory space` 五类元信息。
- 支持显式 stride 构造，也支持按行主序自动推导 stride。
- 提供最小可用的元素访问、线性偏移计算和连续性判断接口。

## 限制与边界

- 该类型是“视图”，不拥有底层内存，也不负责释放 `data`。
- 头文件实现不得包含或依赖 C++ 标准库头文件。
- 不做动态分配。
- 不做运行时边界检查、空指针保护、负维度保护或越界异常抛出。
- 调用方必须保证：
  - `Rank > 0`
  - `shape[i] > 0`
  - `stride[i] > 0`
  - `indices[i]` 落在 `[0, shape[i])`
  - `data` 指向足够大的有效存储

## 命名空间与公开类型

### 命名空间

- 所有实现位于 `cpu` 命名空间下。

### `MemoryFormat`

功能说明：

- 表示张量布局格式。

公开成员：

- `MemoryFormat::Norm`
- `MemoryFormat::CLast`

说明：

- 当前仅保留抽象布局语义，不引入字符串别名或额外格式枚举。

### `MemorySpace`

功能说明：

- 表示内存所在空间。

公开成员：

- `MemorySpace::GM`
- `MemorySpace::SM`
- `MemorySpace::LM`
- `MemorySpace::TSM`
- `MemorySpace::TLM`

说明：

- 该枚举只负责分类，不内嵌容量、对齐或运行时访问规则。

## `Memory<T, Rank>`

### 模板参数

- `T`：元素类型，例如 `int`、`float`。
- `Rank`：张量维度，编译期常量，要求大于 `0`。

### 存储语义

- `data`：外部传入的数据指针。
- `shape`：长度为 `Rank` 的维度数组。
- `stride`：长度为 `Rank` 的步幅数组。
- `format`：布局格式。
- `space`：内存空间。

### 构造接口

#### 显式 stride 构造

接口：

```cpp
template <typename T, unsigned long long Rank>
cpu::Memory<T, Rank>(
    T* data,
    const long long (&shape)[Rank],
    const long long (&stride)[Rank],
    cpu::MemoryFormat format = cpu::MemoryFormat::Norm,
    cpu::MemorySpace space = cpu::MemorySpace::GM);
```

功能说明：

- 使用调用方提供的 `shape` 与 `stride` 初始化视图。

使用示例：

```cpp
#include "include/cpu/Memory.h"

int data[6] = {0, 1, 2, 3, 4, 5};
long long shape[2] = {2, 3};
long long stride[2] = {3, 1};

cpu::Memory<int, 2> mem(data, shape, stride, cpu::MemoryFormat::Norm, cpu::MemorySpace::GM);
```

#### 自动连续 stride 构造

接口：

```cpp
template <typename T, unsigned long long Rank>
cpu::Memory<T, Rank>(
    T* data,
    const long long (&shape)[Rank],
    cpu::MemoryFormat format = cpu::MemoryFormat::Norm,
    cpu::MemorySpace space = cpu::MemorySpace::GM);
```

功能说明：

- 自动按行主序推导连续 stride。
- 例如 `shape = {2, 3, 4}` 时，推导的 `stride = {12, 4, 1}`。

使用示例：

```cpp
long long shape[2] = {2, 3};

cpu::Memory<int, 2> mem(data, shape);
```

### 公开方法

#### `data()`

- 返回底层数据指针。

#### `shape()`

- 返回内部 shape 数组首地址。

#### `stride()`

- 返回内部 stride 数组首地址。

#### `rank()`

- 返回编译期维度数 `Rank`。

#### `format()`

- 返回当前布局格式。

#### `space()`

- 返回当前内存空间。

#### `element_count()`

- 返回所有维度元素数量乘积。

#### `is_contiguous()`

- 判断当前 stride 是否等于按 `shape` 推导的连续行主序 stride。

#### `linear_offset(indices)`

- 根据多维索引和 stride 计算线性偏移。

#### `at(indices)`

- 返回索引位置对应的元素引用。
- `const` 与非常量对象均提供重载。

## 返回与错误

### 成功返回

- 构造成功后返回 `cpu::Memory<T, Rank>` 对象。
- `data()/shape()/stride()` 返回内部记录的裸指针。
- `linear_offset(indices)` 返回按 stride 计算的线性位置。
- `at(indices)` 返回对应元素引用。

### 错误与未定义行为

- 该头文件不抛标准库异常。
- 若调用方传入非法 `shape/stride/indices/data`，行为未定义。
- `Rank == 0` 通过 `static_assert` 在编译期拒绝。

## 测试

- 测试文件：[`test/include/cpu/test_memory.py`](../../../test/include/cpu/test_memory.py)
- 测试命令：`pytest -q test/include/cpu/test_memory.py`
