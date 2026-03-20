# Nn.md

## 功能简介

定义 CPU 侧纯头文件 NN 运算接口，面向 `cpu::Memory<T, Rank>` 提供逐元素算术、逐元素比较与显式 `broadcast` 能力。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`摸鱼小分队`
- `spec`：[`spec/include/cpu/Nn.md`](../../../spec/include/cpu/Nn.md)
- `功能实现`：[`include/cpu/Nn.h`](../../../include/cpu/Nn.h)
- `test`：[`test/include/cpu/test_nn.py`](../../../test/include/cpu/test_nn.py)

## 依赖

- [`spec/operation/nn.md`](../../../spec/operation/nn.md)：逐元素算术、逐元素比较与显式广播的上游语义。
- [`spec/include/cpu/Memory.md`](../../../spec/include/cpu/Memory.md)：`cpu::Memory<T, Rank>` 的结构与约束。

## 目标

- 提供纯头文件、可独立包含的 CPU NN 运算接口。
- 不依赖 C++ 标准库，不引入异常体系与动态分配。
- 显式传入输入/输出 `Memory` 视图，不在函数内部创建临时 `Memory`。
- 语义对齐 `spec/operation/nn.md` 已落地的逐元素算术、逐元素比较与显式 `broadcast`。

## 限制与边界

- 不支持隐式广播，不支持 `matmul`。
- 仅处理整数维度；`shape/stride` 为 `long long` 数组，不承诺符号维度语义。
- `MemorySpace` 必须一致（输入与输出空间一致），否则行为未定义。
- 不抛异常、不返回错误码；任何违反形状、空间、stride 预期的调用均为未定义行为。
- 调用方需确保：
  - `shape[i] > 0`、`stride[i] > 0`。
  - `data` 指向足够大的有效内存。
  - 输出缓冲区与输入缓冲区的别名关系满足调用方约束。

## 公开接口

### 逐元素算术

- 功能说明：对两个 `Memory` 执行逐元素算术。
- 参数说明：
  - `lhs: const Memory<T, Rank>&`
  - `rhs: const Memory<T, Rank>&`
  - `out: Memory<T, Rank>&`
- 使用示例：
  - `cpu::add(A, B, C)`
- 注意事项：
  - 不支持标量重载；不做隐式广播。
  - `lhs.shape`、`rhs.shape`、`out.shape` 必须一致。
  - `lhs.stride`、`rhs.stride`、`out.stride` 需可用于同一 rank 的逐元素访问。
  - `lhs.space == rhs.space == out.space`。
- 返回与限制：无返回值，输出写入 `out`。

推荐接口形态：

```cpp
namespace cpu {

template <typename T, unsigned long long Rank>
void add(const Memory<T, Rank>& lhs, const Memory<T, Rank>& rhs, Memory<T, Rank>& out);

// sub/mul/truediv 同形态。

}  // namespace cpu
```

### 逐元素比较

- 功能说明：对两个 `Memory` 执行逐元素比较，输出 predicate 语义结果。
- 参数说明：
  - `lhs: const Memory<T, Rank>&`
  - `rhs: const Memory<T, Rank>&`
  - `out: Memory<PredT, Rank>&`
- 使用示例：
  - `cpu::eq(A, B, C)`
- 注意事项：
  - `lhs.shape`、`rhs.shape`、`out.shape` 必须一致。
  - `lhs.space == rhs.space == out.space`。
  - `out` 的元素类型需能表示 predicate 结果（推荐 `int`，取值为 `0/1`）。
- 返回与限制：无返回值，输出写入 `out`。

推荐接口形态：

```cpp
namespace cpu {

template <typename T, typename PredT, unsigned long long Rank>
void eq(const Memory<T, Rank>& lhs, const Memory<T, Rank>& rhs, Memory<PredT, Rank>& out);

// ne/lt/le/gt/ge 同形态。

}  // namespace cpu
```

### `broadcast`

- 功能说明：将输入 `Memory` 显式广播到目标形状（由输出 `Memory` 指定）。
- 参数说明：
  - `input: const Memory<T, InRank>&`
  - `out: Memory<T, OutRank>&`
- 使用示例：
  - `cpu::broadcast(input, output)`
- 注意事项：
  - `OutRank >= InRank`。
  - 广播按尾维对齐，逐维满足 `input_dim == output_dim` 或 `input_dim == 1`。
  - `input.space == out.space`。
  - `out` 的 `dtype` 与输入一致。
- 返回与限制：无返回值，输出写入 `out`。

推荐接口形态：

```cpp
namespace cpu {

template <typename T, unsigned long long InRank, unsigned long long OutRank>
void broadcast(const Memory<T, InRank>& input, Memory<T, OutRank>& out);

}  // namespace cpu
```

## 测试

- 测试文件：[`test/include/cpu/test_nn.py`](../../../test/include/cpu/test_nn.py)
- 执行命令：`pytest -q test/include/cpu/test_nn.py`

### 测试目标

- 验证逐元素算术在相同 `shape/space` 下输出正确结果。
- 验证逐元素比较输出 predicate 语义结果。
- 验证 `broadcast` 的尾维对齐与 singleton 扩张规则。
- 验证输入/输出 `shape/space` 不一致时由调用方负责拦截（不在 include 层抛错）。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 对应测试 |
| --- | --- | --- | --- | --- | --- | --- |
| INC-NN-001 | 算术 | 同 shape 加法 | N/A | `cpu::add(A, B, C)` | 输出逐元素相加结果 | `test_cpu_nn_add_success` |
| INC-NN-002 | 比较 | 同 shape 相等判断 | N/A | `cpu::eq(A, B, C)` | 输出 predicate 结果 | `test_cpu_nn_compare_eq` |
| INC-NN-003 | 广播 | singleton 扩张 | N/A | `cpu::broadcast(input, output)` | 维度按 singleton 规则扩张 | `test_cpu_nn_broadcast_success` |
| INC-NN-004 | 广播 | 前置维插入 | N/A | `cpu::broadcast(input, output)` | 维度按前置插入规则扩张 | `test_cpu_nn_broadcast_prepend_dim` |
| INC-NN-005 | 算术 | 同 shape 乘法 | N/A | `cpu::mul(A, B, C)` | 输出逐元素相乘结果 | `test_cpu_nn_mul_success` |
