# Memory.md

## 功能简介

定义 `cpu::Memory<T, Rank>` 纯头文件张量视图，以及配套的 `cpu::MemoryFormat`、`cpu::MemorySpace` 公开类型。该文件只描述 CPU 侧多维内存视图的元信息与访问接口，不负责底层内存分配、释放、拷贝或运行时边界检查。

- `cpu::Memory<T, Rank>` 是视图类型，仅保存 `data`、`shape`、`stride`、`format`、`space` 元信息，不拥有底层存储。
- 连续布局指 `stride` 等于按 `shape` 自后向前推导出的行主序步幅；未显式传入 `stride` 时，由 `Memory` 自动生成该连续步幅。

## 文档信息

- 创建者：`神秘人`
- 最后一次更改：`朽木露琪亚`
- `spec`：[`spec/include/cpu/Memory.md`](../../../spec/include/cpu/Memory.md)
- `功能实现`：[`include/cpu/Memory.h`](../../../include/cpu/Memory.h)
- `test`：[`test/include/cpu/test_memory.py`](../../../test/include/cpu/test_memory.py)

## 依赖

- [`include/cpu/Memory.h`](../../../include/cpu/Memory.h)：`cpu::Memory<T, Rank>`、`cpu::MemoryFormat`、`cpu::MemorySpace` 的头文件实现。
- [`test/include/cpu/test_memory.py`](../../../test/include/cpu/test_memory.py)：通过编译并运行 C++ 片段验证头文件接口与核心语义。

## 目标

- 为 CPU 侧多维数据提供不依赖标准库容器与异常体系的轻量张量视图。
- 统一表达元素类型、维度、布局格式与内存空间，便于上层在不复制数据的前提下传递张量元信息。
- 提供最小可用的访问接口，包括元素总数计算、连续性判断、线性偏移计算和按索引读写。

## 限制与边界

- `cpu::Memory<T, Rank>` 是视图类型，不分配、释放或拥有底层数据。
- 该头文件不承诺运行时边界检查，不对空指针、越界索引、非法 `shape/stride` 提供保护。
- 调用方需要保证 `Rank > 0`、`shape[i] > 0`、`stride[i] > 0`，并确保 `indices[i]` 位于合法范围内。
- 文档中的“显式步幅”表示调用方直接传入的 `stride` 数组；“自动步幅”表示构造时未显式传入 `stride`，由 `Memory` 按连续行主序推导。
- `MemoryFormat` 当前仅公开 `Norm` 与 `CLast`，不引入字符串别名或额外布局成员。
- `MemorySpace` 当前仅公开 `GM`、`SM`、`LM`、`TSM`、`TLM`，只表达空间分类，不表达容量、对齐或同步规则。
- 该文件只覆盖头文件接口语义，不定义算子级搬运、广播或计算行为。

## 公开接口

### `cpu::MemoryFormat`

功能说明：

- 表示 `cpu::Memory<T, Rank>` 记录的布局格式枚举。

参数说明：

- 无参数。

使用示例：

```cpp
#include "include/cpu/Memory.h"

cpu::MemoryFormat format = cpu::MemoryFormat::CLast;
```

注意事项：

- 当前公开成员仅包含 `MemoryFormat::Norm` 与 `MemoryFormat::CLast`。
- 该枚举只表达布局语义名称，不定义字符串值、别名等价关系或布局推导规则。

返回与限制：

- 返回类型：`cpu::MemoryFormat` 枚举值。
- 返回语义：供 `cpu::Memory<T, Rank>` 构造与查询时记录布局格式。
- 限制条件：本文档不定义除 `Norm`、`CLast` 之外的其他公开成员。

### `cpu::MemorySpace`

功能说明：

- 表示 `cpu::Memory<T, Rank>` 所在的逻辑内存空间。

参数说明：

- 无参数。

使用示例：

```cpp
#include "include/cpu/Memory.h"

cpu::MemorySpace space = cpu::MemorySpace::SM;
```

注意事项：

- 当前公开成员仅包含 `MemorySpace::GM`、`MemorySpace::SM`、`MemorySpace::LM`、`MemorySpace::TSM`、`MemorySpace::TLM`。
- 该枚举只负责空间分类，不承诺容量、带宽、地址合法性或跨空间访问规则。

返回与限制：

- 返回类型：`cpu::MemorySpace` 枚举值。
- 返回语义：供 `cpu::Memory<T, Rank>` 构造与查询时记录内存空间。
- 限制条件：本文档不定义额外空间成员，也不把空间语义扩展为分配器或 runtime 句柄。

### `cpu::Memory<T, Rank>`

功能说明：

- 表示一个带 `data`、`shape`、`stride`、`format`、`space` 元信息的多维内存视图。
- 支持显式步幅构造与自动连续步幅构造，并提供查询与访问接口。

参数说明：

- `T(type)`：元素类型。
- `Rank(unsigned long long)`：编译期固定维度数，必须大于 `0`。
- `data(T*)`：底层数据指针。
- `shape(const long long (&)[Rank])`：每一维长度数组。
- `stride(const long long (&)[Rank])`：每一维布局步幅数组。
- `format(cpu::MemoryFormat)`：布局格式，默认 `cpu::MemoryFormat::Norm`。
- `space(cpu::MemorySpace)`：内存空间，默认 `cpu::MemorySpace::GM`。

使用示例：

```cpp
#include "include/cpu/Memory.h"

int data[6] = {0, 1, 2, 3, 4, 5};
long long shape[2] = {2, 3};
long long stride[2] = {3, 1};
long long index[2] = {1, 2};

cpu::Memory<int, 2> explicit_mem(
    data,
    shape,
    stride,
    cpu::MemoryFormat::CLast,
    cpu::MemorySpace::SM);

cpu::Memory<int, 2> auto_mem(data, shape);
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

- 返回类型：`cpu::Memory<T, Rank>` 对象，以及其公开方法返回的裸指针、枚举值、整型偏移或元素引用。
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

- 测试文件：[`test/include/cpu/test_memory.py`](../../../test/include/cpu/test_memory.py)
- 执行命令：`pytest -q test/include/cpu/test_memory.py`
- 测试目标：
  - 验证显式步幅构造会保留 `shape/stride/format/space` 元信息。
  - 验证自动步幅构造会生成连续行主序 `stride`，并与 `is_contiguous()` 语义一致。
  - 验证 `element_count()`、`linear_offset()`、`at()` 的访问结果符合头文件定义。
  - 验证非连续 `stride` 可被 `is_contiguous()` 正确识别。
  - 验证头文件不依赖标准库头文件即可被最小程序编译。
- 功能与用例清单：

| 用例 ID | 功能点 | 测试函数 |
| --- | --- | --- |
| `CPU-MEM-001` | 显式步幅构造保留 `shape/stride/format/space` | `test_cpu_memory_header_compiles_and_runs` |
| `CPU-MEM-002` | 自动步幅构造生成连续行主序 `stride` | `test_cpu_memory_header_compiles_and_runs` |
| `CPU-MEM-003` | `element_count()`、`linear_offset()`、`at()` 行为正确 | `test_cpu_memory_header_compiles_and_runs` |
| `CPU-MEM-004` | 非连续 `stride` 与 `is_contiguous()` 判定一致 | `test_cpu_memory_header_compiles_and_runs` |
| `CPU-MEM-005` | 头文件不依赖标准库头文件即可编译 | `test_cpu_memory_header_without_std_headers` |
