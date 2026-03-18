# Nn.md

## 功能简介

定义 CPU 侧纯头文件 NN 运算接口，面向 `cpu::Memory<T, Rank>` 提供逐元素算术、逐元素比较与显式 `broadcast` 能力。该层只负责在给定 `Memory` 视图上执行计算，不负责内存分配、类型提升或异常处理。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`摸鱼小分队`
- `spec`：[`spec/include/cpu/Nn.md`](../../../spec/include/cpu/Nn.md)
- `上游语义`：[`spec/operation/nn.md`](../../../spec/operation/nn.md)
- `关联类型`：[`spec/include/cpu/Memory.md`](../../../spec/include/cpu/Memory.md)
- `test`：[`test/include/cpu/test_nn.py`](../../../test/include/cpu/test_nn.py)
- `功能实现`：[`include/cpu/Nn.h`](../../../include/cpu/Nn.h)

## 设计目标

- 提供纯头文件、可独立包含的 CPU 侧 NN 运算接口。
- 不依赖 C++ 标准库，不引入异常体系与动态分配。
- 显式传入输入/输出 `Memory` 视图，不在函数内部创建临时 `Memory`。
- 语义对齐 `spec/operation/nn.md` 中已落地的逐元素算术、逐元素比较与显式 `broadcast`。
- 不覆盖尚未落地的 `operation/nn.matmul`。

## 分层关系

- `spec/operation/nn.md` 定义高层 API 语义、shape/dtype/space 规则与错误边界。
- `spec/include/cpu/Nn.md` 仅描述 CPU 头文件侧接口与行为约束，作为上游语义的具体落地载体之一。
- 该层不定义新的语义规则，也不引入方言/IR 细节。

## 支持范围

- 逐元素算术：`add/sub/mul/truediv`。
- 逐元素比较：`eq/ne/lt/le/gt/ge`。
- 显式广播：`broadcast`。
- 不支持隐式广播；不支持 `matmul`。

## 基础类型与约束

- 输入/输出使用 [`cpu::Memory<T, Rank>`](../../../spec/include/cpu/Memory.md)。
- `shape/stride` 为 `long long` 数组；本层仅处理整数维度，不承诺符号维度语义。
- `MemorySpace` 必须一致（输入与输出空间一致），否则行为未定义。

## 接口约定

### 逐元素算术

功能说明：

- 对两个 `Memory` 执行逐元素算术。
- 不支持标量重载；所有算术操作仅接受 `Memory` 作为输入。
- 不做隐式广播；输入与输出的 `shape/stride` 必须相容。

推荐接口形态：

```cpp
namespace cpu {

template <typename T, unsigned long long Rank>
void add(const Memory<T, Rank>& lhs, const Memory<T, Rank>& rhs, Memory<T, Rank>& out);

// sub/mul/truediv 同形态。

}  // namespace cpu
```

使用示例：

```cpp
#include "include/cpu/Memory.h"
#include "include/cpu/Nn.h"

cpu::Memory<float, 2> A(data_a, shape, stride);
cpu::Memory<float, 2> B(data_b, shape, stride);
cpu::Memory<float, 2> C(data_c, shape, stride);

cpu::add(A, B, C);
```

行为约束：

- `lhs.shape`、`rhs.shape`、`out.shape` 必须一致。
- `lhs.stride`、`rhs.stride`、`out.stride` 必须可用于同一 rank 的逐元素访问。
- `lhs.space == rhs.space == out.space`。

### 逐元素比较

功能说明：

- 对两个 `Memory` 执行逐元素比较，输出 predicate 语义的结果。

推荐接口形态：

```cpp
namespace cpu {

template <typename T, typename PredT, unsigned long long Rank>
void eq(const Memory<T, Rank>& lhs, const Memory<T, Rank>& rhs, Memory<PredT, Rank>& out);

// ne/lt/le/gt/ge 同形态。

}  // namespace cpu
```

使用示例：

```cpp
cpu::Memory<float, 2> A(data_a, shape, stride);
cpu::Memory<float, 2> B(data_b, shape, stride);
cpu::Memory<int, 2> C(data_c, shape, stride);

cpu::eq(A, B, C);
```

行为约束：

- `lhs.shape`、`rhs.shape`、`out.shape` 必须一致。
- `lhs.space == rhs.space == out.space`。
- `out` 的元素类型需能表示 predicate 结果（推荐 `int`，取值为 `0/1`）。

### `broadcast`

功能说明：

- 将输入 `Memory` 显式广播到目标形状（由输出 `Memory` 指定）。
- 不进行隐式类型转换，不跨空间搬运。

推荐接口形态：

```cpp
namespace cpu {

template <typename T, unsigned long long InRank, unsigned long long OutRank>
void broadcast(const Memory<T, InRank>& input, Memory<T, OutRank>& out);

}  // namespace cpu
```

使用示例：

```cpp
long long in_shape[2] = {1, 4};
long long out_shape[2] = {3, 4};
long long in_stride[2] = {4, 1};
long long out_stride[2] = {4, 1};

cpu::Memory<float, 2> input(in_data, in_shape, in_stride);
cpu::Memory<float, 2> output(out_data, out_shape, out_stride);

cpu::broadcast(input, output);
```

行为约束：

- `OutRank >= InRank`。
- 广播按尾维对齐，逐维满足：
  - `input_dim == output_dim`，或
  - `input_dim == 1`（允许扩张）。
- `input.space == out.space`。
- `out` 的 `dtype` 与输入一致。

## 错误边界与未定义行为

- 本层不依赖 C++ 标准库，不抛异常、不返回错误码。
- 任何违反形状、空间、stride 预期的调用均为未定义行为。
- 调用方必须确保：
  - `shape[i] > 0`、`stride[i] > 0`。
  - `data` 指向足够大的有效内存。
  - 输出缓冲区与输入缓冲区的别名关系满足调用方约束。

## 测试

- 测试文件：[`test/include/cpu/test_nn.py`](../../../test/include/cpu/test_nn.py)
- 测试命令：`pytest -q test/include/cpu/test_nn.py`

### 测试目标

- 验证逐元素算术在相同 `shape/space` 下输出正确结果。
- 验证逐元素比较输出 predicate 语义结果。
- 验证 `broadcast` 的尾维对齐与 singleton 扩张规则。
- 验证输入/输出 `shape/space` 不一致时由调用方负责拦截（不在 include 层抛错）。

### 测试清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| INC-NN-001 | 算术 | 同 shape 加法 | `shape=[2,3]` | `add(lhs, rhs, out)` | `out` 逐元素等于 `lhs+rhs` | `test_cpu_nn_add_success` |
| INC-NN-002 | 比较 | 同 shape 比较 | `shape=[2,3]` | `eq(lhs, rhs, out)` | `out` 为 `0/1` | `test_cpu_nn_compare_eq` |
| INC-NN-003 | 广播 | singleton 扩张 | `input.shape=[1,4]`, `out.shape=[3,4]` | `broadcast(input, out)` | `out` 重复填充 | `test_cpu_nn_broadcast_success` |
| INC-NN-004 | 广播 | 插入前置维 | `input.shape=[4]`, `out.shape=[3,4]` | `broadcast(input, out)` | `out` 逐行复制 | `test_cpu_nn_broadcast_prepend_dim` |
| INC-NN-005 | 算术 | 同 shape 乘法 | `shape=[2,3]` | `mul(lhs, rhs, out)` | `out` 逐元素等于 `lhs*rhs` | `test_cpu_nn_mul_success` |

## 语义对齐

- 逐元素算术/比较与 [`spec/operation/nn.md`](../../../spec/operation/nn.md) 保持一致：禁止隐式广播，要求输入 `shape` 严格一致。
- `broadcast` 规则与 `operation/nn.broadcast` 保持一致：尾维对齐，仅允许 `1` 扩张。
- 不包含 `operation/nn.matmul` 的任何接口或语义。
