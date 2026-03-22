# cpu

## 功能简介

定义 CPU 后端 include/cpu 头文件规范，覆盖 `include/cpu/Memory.h` 与 `include/cpu/Nn.h` 的公开接口、行为与约束。该 spec 以 CPU 后端现有模板接口为准，描述 `cpu::Memory<T, Rank>` 的视图语义与逐元素/显式 broadcast 运算。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`摸鱼小分队`
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
- 明确 CPU 后端使用编译期 `Rank` 模板参数的接口边界。

## 限制与边界

- `cpu::Memory<T, Rank>` 使用编译期固定 `Rank`，不等同于 include/api 的运行期 `rank` 规范。
- 公开接口均为纯头文件模板与内联实现，不提供动态分配、异常或运行时边界检查。
- 逐元素与比较算子要求输入与输出形状一致，广播仅支持显式 `broadcast`，不提供隐式广播或标量重载。
- 运行时错误由调用方规避；接口返回 `void`，不提供状态码。
- 本 spec 同时覆盖 `include/cpu/Memory.h` 与 `include/cpu/Nn.h`，原因是两者在 CPU 后端中紧密耦合并共用同一视图语义。

## 公开接口

### `cpu::MemoryFormat`

功能说明：

- 表示 `cpu::Memory` 记录的布局格式枚举。

参数说明：

- 无参数。

使用示例：

```cpp
#include "include/cpu/Memory.h"

cpu::MemoryFormat format = cpu::MemoryFormat::CLast;
```

注意事项：

- 当前公开成员仅包含 `cpu::MemoryFormat::Norm` 与 `cpu::MemoryFormat::CLast`。
- 该枚举仅用于记录布局语义，不负责推导 stride 或等价关系。

返回与限制：

- 返回类型：`cpu::MemoryFormat`。
- 返回语义：供 `cpu::Memory` 构造与查询时记录布局格式。
- 限制条件：不定义 `Norm/CLast` 之外的枚举成员。

### `cpu::MemorySpace`

功能说明：

- 表示 `cpu::Memory` 所在的逻辑内存空间。

参数说明：

- 无参数。

使用示例：

```cpp
#include "include/cpu/Memory.h"

cpu::MemorySpace space = cpu::MemorySpace::SM;
```

注意事项：

- 当前公开成员仅包含 `cpu::MemorySpace::GM`、`cpu::MemorySpace::SM`、`cpu::MemorySpace::LM`、`cpu::MemorySpace::TSM`、`cpu::MemorySpace::TLM`。
- 该枚举只负责空间分类，不承诺容量、地址或同步语义。

返回与限制：

- 返回类型：`cpu::MemorySpace`。
- 返回语义：供 `cpu::Memory` 构造与查询时记录内存空间。
- 限制条件：不定义其他空间成员。

### `cpu::Memory<T, Rank>`

功能说明：

- 表示编译期固定 `Rank` 的多维内存视图，记录 `data/shape/stride/format/space` 元信息。

参数说明：

- `T`：元素类型。
- `Rank`：编译期维度数，必须大于 `0`。

使用示例：

```cpp
#include "include/cpu/Memory.h"

int data[6] = {0, 1, 2, 3, 4, 5};
long long shape[2] = {2, 3};
long long stride[2] = {3, 1};

cpu::Memory<int, 2> mem(data, shape, stride, cpu::MemoryFormat::Norm, cpu::MemorySpace::GM);
```

注意事项：

- `shape`/`stride` 由调用方提供，类内部拷贝数组值。
- `data` 必须指向有效连续内存，接口不检查空指针或越界访问。

返回与限制：

- 返回类型：`cpu::Memory<T, Rank>`。
- 返回语义：构造并记录内存视图元信息。
- 限制条件：`Rank == 0` 不允许；非法指针或维度值属于未定义行为。

#### `Memory(data, shape, stride, format, space)`

功能说明：

- 使用显式 `shape` 与 `stride` 构造视图。

参数说明：

- `data (T*)`：底层数据指针。
- `shape (const long long (&)[Rank])`：维度数组。
- `stride (const long long (&)[Rank])`：步幅数组。
- `format (cpu::MemoryFormat)`：布局格式，默认 `Norm`。
- `space (cpu::MemorySpace)`：内存空间，默认 `GM`。

使用示例：

```cpp
cpu::Memory<int, 2> mem(data, shape, stride, cpu::MemoryFormat::CLast, cpu::MemorySpace::SM);
```

注意事项：

- 不进行 `shape/stride` 的合法性检查。

返回与限制：

- 返回类型：`cpu::Memory<T, Rank>`。
- 返回语义：构造并保存显式步幅。
- 限制条件：调用方需保证 `shape/stride` 合法。

#### `Memory(data, shape, format, space)`

功能说明：

- 使用 `shape` 构造连续行主序视图，并自动推导 `stride`。

参数说明：

- `data (T*)`：底层数据指针。
- `shape (const long long (&)[Rank])`：维度数组。
- `format (cpu::MemoryFormat)`：布局格式，默认 `Norm`。
- `space (cpu::MemorySpace)`：内存空间，默认 `GM`。

使用示例：

```cpp
cpu::Memory<float, 2> mem(data, shape);
```

注意事项：

- `stride` 按连续行主序推导，未提供覆盖入口。

返回与限制：

- 返回类型：`cpu::Memory<T, Rank>`。
- 返回语义：构造并填充连续步幅。
- 限制条件：调用方需保证 `shape` 合法。

#### `data()`

功能说明：

- 返回底层数据指针。

参数说明：

- 无参数。

使用示例：

```cpp
int* ptr = mem.data();
```

注意事项：

- 提供 `T*` 与 `const T*` 两个重载。

返回与限制：

- 返回类型：`T*` 或 `const T*`。
- 返回语义：返回内部保存的数据指针。
- 限制条件：不检查空指针。

#### `shape()`

功能说明：

- 返回 `shape` 数组首地址。

参数说明：

- 无参数。

使用示例：

```cpp
const long long* shape = mem.shape();
```

注意事项：

- 返回的是内部数组指针，调用方需保证访问合法。

返回与限制：

- 返回类型：`const long long*`。
- 返回语义：返回 `shape` 数组首地址。
- 限制条件：不提供长度信息，需结合 `rank()` 使用。

#### `stride()`

功能说明：

- 返回 `stride` 数组首地址。

参数说明：

- 无参数。

使用示例：

```cpp
const long long* stride = mem.stride();
```

注意事项：

- 返回的是内部数组指针，调用方需保证访问合法。

返回与限制：

- 返回类型：`const long long*`。
- 返回语义：返回 `stride` 数组首地址。
- 限制条件：不提供长度信息，需结合 `rank()` 使用。

#### `rank()`

功能说明：

- 返回编译期固定维度数。

参数说明：

- 无参数。

使用示例：

```cpp
unsigned long long rank = mem.rank();
```

注意事项：

- `rank()` 为 `static constexpr`，与模板参数一致。

返回与限制：

- 返回类型：`unsigned long long`。
- 返回语义：返回编译期 `Rank`。
- 限制条件：无运行期修改能力。

#### `format()`

功能说明：

- 返回布局格式。

参数说明：

- 无参数。

使用示例：

```cpp
cpu::MemoryFormat format = mem.format();
```

注意事项：

- 返回构造时记录的布局枚举。

返回与限制：

- 返回类型：`cpu::MemoryFormat`。
- 返回语义：返回当前布局格式。
- 限制条件：无。

#### `space()`

功能说明：

- 返回内存空间。

参数说明：

- 无参数。

使用示例：

```cpp
cpu::MemorySpace space = mem.space();
```

注意事项：

- 返回构造时记录的空间枚举。

返回与限制：

- 返回类型：`cpu::MemorySpace`。
- 返回语义：返回当前空间枚举。
- 限制条件：无。

#### `element_count()`

功能说明：

- 返回元素总数（`shape` 各维乘积）。

参数说明：

- 无参数。

使用示例：

```cpp
long long count = mem.element_count();
```

注意事项：

- 乘积溢出由调用方自行规避。

返回与限制：

- 返回类型：`long long`。
- 返回语义：返回元素数量。
- 限制条件：不检查溢出。

#### `is_contiguous()`

功能说明：

- 判断当前 `stride` 是否为行主序连续布局。

参数说明：

- 无参数。

使用示例：

```cpp
bool contiguous = mem.is_contiguous();
```

注意事项：

- 行主序连续布局按尾维优先、逐维累乘判断。

返回与限制：

- 返回类型：`bool`。
- 返回语义：`true` 表示连续布局。
- 限制条件：不做 `shape` 合法性校验。

#### `linear_offset(indices)`

功能说明：

- 根据多维索引计算线性偏移。

参数说明：

- `indices (const long long (&)[Rank])`：长度为 `Rank` 的索引数组。

使用示例：

```cpp
long long index[2] = {1, 2};
long long offset = mem.linear_offset(index);
```

注意事项：

- 不检查索引越界。

返回与限制：

- 返回类型：`long long`。
- 返回语义：返回线性偏移。
- 限制条件：索引非法属于未定义行为。

#### `at(indices)`

功能说明：

- 返回指定索引位置元素引用。

参数说明：

- `indices (const long long (&)[Rank])`：长度为 `Rank` 的索引数组。

使用示例：

```cpp
long long index[2] = {1, 2};
int& value = mem.at(index);
```

注意事项：

- 提供 `T&` 与 `const T&` 两个重载。
- 不检查索引越界。

返回与限制：

- 返回类型：`T&` 或 `const T&`。
- 返回语义：返回索引位置元素引用。
- 限制条件：索引非法属于未定义行为。

### `cpu::add(lhs, rhs, out)`

功能说明：

- 对两个 `cpu::Memory` 视图执行逐元素加法。

参数说明：

- `lhs (const cpu::Memory<T, Rank>&)`：左操作数视图。
- `rhs (const cpu::Memory<T, Rank>&)`：右操作数视图。
- `out (cpu::Memory<T, Rank>&)`：输出视图。

使用示例：

```cpp
cpu::add(lhs, rhs, out);
```

注意事项：

- `lhs/rhs/out` 的 `Rank`、`shape` 与 `stride` 需保持一致。
- 接口不检查形状合法性。

返回与限制：

- 返回类型：`void`。
- 返回语义：结果写入 `out`。
- 限制条件：输入不满足约束时行为未定义。

### `cpu::sub(lhs, rhs, out)`

功能说明：

- 对两个 `cpu::Memory` 视图执行逐元素减法。

参数说明：

- `lhs (const cpu::Memory<T, Rank>&)`：左操作数视图。
- `rhs (const cpu::Memory<T, Rank>&)`：右操作数视图。
- `out (cpu::Memory<T, Rank>&)`：输出视图。

使用示例：

```cpp
cpu::sub(lhs, rhs, out);
```

注意事项：

- `lhs/rhs/out` 的 `Rank` 与 `shape` 必须一致。

返回与限制：

- 返回类型：`void`。
- 返回语义：结果写入 `out`。
- 限制条件：不检查形状或类型约束。

### `cpu::mul(lhs, rhs, out)`

功能说明：

- 对两个 `cpu::Memory` 视图执行逐元素乘法。

参数说明：

- `lhs (const cpu::Memory<T, Rank>&)`：左操作数视图。
- `rhs (const cpu::Memory<T, Rank>&)`：右操作数视图。
- `out (cpu::Memory<T, Rank>&)`：输出视图。

使用示例：

```cpp
cpu::mul(lhs, rhs, out);
```

注意事项：

- `lhs/rhs/out` 的 `Rank` 与 `shape` 必须一致。

返回与限制：

- 返回类型：`void`。
- 返回语义：结果写入 `out`。
- 限制条件：不检查形状或类型约束。

### `cpu::truediv(lhs, rhs, out)`

功能说明：

- 对两个 `cpu::Memory` 视图执行逐元素真除法。

参数说明：

- `lhs (const cpu::Memory<T, Rank>&)`：左操作数视图。
- `rhs (const cpu::Memory<T, Rank>&)`：右操作数视图。
- `out (cpu::Memory<T, Rank>&)`：输出视图。

使用示例：

```cpp
cpu::truediv(lhs, rhs, out);
```

注意事项：

- `lhs/rhs/out` 的 `Rank` 与 `shape` 必须一致。

返回与限制：

- 返回类型：`void`。
- 返回语义：结果写入 `out`。
- 限制条件：不检查除零或形状约束。

### `cpu::eq(lhs, rhs, out)`

功能说明：

- 对两个 `cpu::Memory` 视图执行逐元素相等比较。

参数说明：

- `lhs (const cpu::Memory<T, Rank>&)`：左操作数视图。
- `rhs (const cpu::Memory<T, Rank>&)`：右操作数视图。
- `out (cpu::Memory<PredT, Rank>&)`：输出视图，元素类型用于表示 predicate。

使用示例：

```cpp
cpu::eq(lhs, rhs, out);
```

注意事项：

- `lhs/rhs/out` 的 `Rank` 与 `shape` 必须一致。
- `out` 元素类型需能表示比较结果。

返回与限制：

- 返回类型：`void`。
- 返回语义：结果写入 `out`。
- 限制条件：不检查类型或形状约束。

### `cpu::ne(lhs, rhs, out)`

功能说明：

- 对两个 `cpu::Memory` 视图执行逐元素不等比较。

参数说明：

- `lhs (const cpu::Memory<T, Rank>&)`：左操作数视图。
- `rhs (const cpu::Memory<T, Rank>&)`：右操作数视图。
- `out (cpu::Memory<PredT, Rank>&)`：输出视图。

使用示例：

```cpp
cpu::ne(lhs, rhs, out);
```

注意事项：

- `lhs/rhs/out` 的 `Rank` 与 `shape` 必须一致。

返回与限制：

- 返回类型：`void`。
- 返回语义：结果写入 `out`。
- 限制条件：不检查类型或形状约束。

### `cpu::lt(lhs, rhs, out)`

功能说明：

- 对两个 `cpu::Memory` 视图执行逐元素小于比较。

参数说明：

- `lhs (const cpu::Memory<T, Rank>&)`：左操作数视图。
- `rhs (const cpu::Memory<T, Rank>&)`：右操作数视图。
- `out (cpu::Memory<PredT, Rank>&)`：输出视图。

使用示例：

```cpp
cpu::lt(lhs, rhs, out);
```

注意事项：

- `lhs/rhs/out` 的 `Rank` 与 `shape` 必须一致。

返回与限制：

- 返回类型：`void`。
- 返回语义：结果写入 `out`。
- 限制条件：不检查类型或形状约束。

### `cpu::le(lhs, rhs, out)`

功能说明：

- 对两个 `cpu::Memory` 视图执行逐元素小于等于比较。

参数说明：

- `lhs (const cpu::Memory<T, Rank>&)`：左操作数视图。
- `rhs (const cpu::Memory<T, Rank>&)`：右操作数视图。
- `out (cpu::Memory<PredT, Rank>&)`：输出视图。

使用示例：

```cpp
cpu::le(lhs, rhs, out);
```

注意事项：

- `lhs/rhs/out` 的 `Rank` 与 `shape` 必须一致。

返回与限制：

- 返回类型：`void`。
- 返回语义：结果写入 `out`。
- 限制条件：不检查类型或形状约束。

### `cpu::gt(lhs, rhs, out)`

功能说明：

- 对两个 `cpu::Memory` 视图执行逐元素大于比较。

参数说明：

- `lhs (const cpu::Memory<T, Rank>&)`：左操作数视图。
- `rhs (const cpu::Memory<T, Rank>&)`：右操作数视图。
- `out (cpu::Memory<PredT, Rank>&)`：输出视图。

使用示例：

```cpp
cpu::gt(lhs, rhs, out);
```

注意事项：

- `lhs/rhs/out` 的 `Rank` 与 `shape` 必须一致。

返回与限制：

- 返回类型：`void`。
- 返回语义：结果写入 `out`。
- 限制条件：不检查类型或形状约束。

### `cpu::ge(lhs, rhs, out)`

功能说明：

- 对两个 `cpu::Memory` 视图执行逐元素大于等于比较。

参数说明：

- `lhs (const cpu::Memory<T, Rank>&)`：左操作数视图。
- `rhs (const cpu::Memory<T, Rank>&)`：右操作数视图。
- `out (cpu::Memory<PredT, Rank>&)`：输出视图。

使用示例：

```cpp
cpu::ge(lhs, rhs, out);
```

注意事项：

- `lhs/rhs/out` 的 `Rank` 与 `shape` 必须一致。

返回与限制：

- 返回类型：`void`。
- 返回语义：结果写入 `out`。
- 限制条件：不检查类型或形状约束。

### `cpu::broadcast(input, out)`

功能说明：

- 显式广播输入视图到输出形状。

参数说明：

- `input (const cpu::Memory<T, InRank>&)`：输入视图。
- `out (cpu::Memory<T, OutRank>&)`：输出视图。

使用示例：

```cpp
cpu::broadcast(input, out);
```

注意事项：

- `OutRank >= InRank`。
- 广播按尾维对齐，逐维满足 `input_dim == output_dim` 或 `input_dim == 1`。
- 接口不检查广播条件，调用方需保证合法。

返回与限制：

- 返回类型：`void`。
- 返回语义：结果写入 `out`。
- 限制条件：广播条件不满足时行为未定义。

## 测试

- 测试文件：
  - `test/include/cpu/test_memory.py`
  - `test/include/cpu/test_nn.py`
- 执行命令：`pytest -q test/include/cpu/test_memory.py test/include/cpu/test_nn.py`
- 测试说明：`test/include/cpu/test_memory.py` 与 `test/include/cpu/test_nn.py` 均统一引用本 spec `spec/include/cpu/cpu.md`，不再拆分为独立 `Memory.md` / `Nn.md`。
- 测试目标：
  - CPU-MEM-001：显式 stride 构造与访问。
  - CPU-MEM-002：连续 stride 自动推导。
  - CPU-MEM-003：`element_count/linear_offset` 语义。
  - CPU-MEM-004：`at/is_contiguous` 语义。
  - CPU-MEM-005：头文件不依赖标准库即可编译。
  - INC-NN-001：逐元素加法输出。
  - INC-NN-002：逐元素比较输出 predicate。
  - INC-NN-003：broadcast 单例扩张。
  - INC-NN-004：broadcast 前置维插入。
  - INC-NN-005：逐元素乘法输出。
- 功能与用例清单：
  - CPU-MEM-001 -> `test/include/cpu/test_memory.py::test_cpu_memory_header_compiles_and_runs`
  - CPU-MEM-002 -> `test/include/cpu/test_memory.py::test_cpu_memory_header_compiles_and_runs`
  - CPU-MEM-003 -> `test/include/cpu/test_memory.py::test_cpu_memory_header_compiles_and_runs`
  - CPU-MEM-004 -> `test/include/cpu/test_memory.py::test_cpu_memory_header_compiles_and_runs`
  - CPU-MEM-005 -> `test/include/cpu/test_memory.py::test_cpu_memory_header_without_std_headers`
  - INC-NN-001 -> `test/include/cpu/test_nn.py::test_cpu_nn_add_success`
  - INC-NN-002 -> `test/include/cpu/test_nn.py::test_cpu_nn_compare_eq`
  - INC-NN-003 -> `test/include/cpu/test_nn.py::test_cpu_nn_broadcast_success`
  - INC-NN-004 -> `test/include/cpu/test_nn.py::test_cpu_nn_broadcast_prepend_dim`
  - INC-NN-005 -> `test/include/cpu/test_nn.py::test_cpu_nn_mul_success`
