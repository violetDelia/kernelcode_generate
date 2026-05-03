# Kernel

## 功能简介

定义 include/api/cost 层统一对外的 Kernel 成本 helper 规范（`include/api/cost/Kernel.h`），作为 `tuner.cost(op_name="kernel.*")` 在 `target=npu_demo` 下的稳定 C++ 承接层。

- `Kernel cost` helper 与 [`spec/include/api/Kernel.md`](../../../../spec/include/api/Kernel.md) 保持同一 helper 集合、同一参数顺序与同一模板顺序，并在模板参数末尾追加 `CostKind Kind`。
- 全部 helper 固定返回 `S_INT`，参数顺序继续采用 `out-first`。
- 当前公开源码口径统一为 `npu_demo::cost::<helper><...>(out, ...)`。

## API 列表

- `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::add(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::sub(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::mul(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::truediv(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::eq(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::ne(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::lt(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::le(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::gt(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::ge(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::exp(const Memory<Space, OutType>& out, const Memory<Space, InType>& input)`
- `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::select(const Memory<Space, OutType>& out, const Memory<Space, bool>& cond, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::reduce_sum(const Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`
- `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::reduce_min(const Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`
- `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::reduce_max(const Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`
- `template <MemorySpace LhsSpace, MemorySpace RhsSpace, MemorySpace OutSpace, typename LhsType, typename RhsType, typename OutType, CostKind Kind> S_INT npu_demo::cost::matmul(const Memory<OutSpace, OutType>& out, const Memory<LhsSpace, LhsType>& lhs, const Memory<RhsSpace, RhsType>& rhs)`
- `template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::img2col1d(const Memory<OutputSpace, OutType>& out, const Memory<InputSpace, InType>& input, long long k, long long s, long long d, long long p_left, long long p_right)`
- `template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::img2col2d(const Memory<OutputSpace, OutType>& out, const Memory<InputSpace, InType>& input, long long kh, long long kw, long long sh, long long sw, long long dh, long long dw, long long ph, long long pw, long long pl, long long pr)`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/include/api/cost/Kernel.md`](../../../../spec/include/api/cost/Kernel.md)
- `统一头文件`：[`include/api/cost/Kernel.h`](../../../../include/api/cost/Kernel.h)
- `功能实现`：[`include/npu_demo/cost/Kernel.h`](../../../../include/npu_demo/cost/Kernel.h)
- `test`：
  - `test/include/api/test_cost.py`
  - [`test/dsl/gen_kernel/emit/test_package.py`](../../../../test/dsl/gen_kernel/emit/test_package.py)
  - [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../test/dsl/gen_kernel/test_gen_kernel.py)

## 依赖

- [`spec/include/api/cost/Core.md`](./Core.md)：提供 `CostKind` 与 `S_INT` 基础合同。
- [`spec/include/api/Kernel.md`](../../../../spec/include/api/Kernel.md)：提供对应计算 helper 的公开名字、模板顺序与参数顺序来源。
- [`spec/include/api/Memory.md`](../../../../spec/include/api/Memory.md)：提供 `Memory<Space, T>` 与 `MemorySpace` 语义。
- [`spec/dsl/gen_kernel/emit.md`](../../../../spec/dsl/gen_kernel/emit.md)：消费 `tuner.cost(op_name="kernel.*") -> npu_demo::cost::<helper>` 的节点级文本合同。
- [`spec/dsl/gen_kernel/gen_kernel.md`](../../../../spec/dsl/gen_kernel/gen_kernel.md)：消费完整 cost function 的函数级源码合同。

## 目标

- 为当前进入公开层的 Kernel helper 提供一一对应的 cost helper。
- 固定 cost helper 的模板顺序：先逐字复用 `Kernel` helper 的模板参数顺序，再在末尾追加 `CostKind Kind`。
- 固定 cost helper 的参数顺序与 `Kernel` helper 完全一致。
- 让 `emit_c/gen_kernel(target="npu_demo")` 在生成 `tuner.cost` 时不需要额外引入私有 helper 名或私有模板重排。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 当前公开 helper 集合与 [`spec/include/api/Kernel.md`](../../../../spec/include/api/Kernel.md) 保持一致：`add`、`sub`、`mul`、`truediv`、`eq`、`ne`、`lt`、`le`、`gt`、`ge`、`exp`、`select`、`reduce_sum`、`reduce_min`、`reduce_max`、`matmul`、`img2col1d`、`img2col2d`。
- 当前不公开 `broadcast`、`softmax`、`cast` 或旧 `Nn` helper 的成本接口。
- cost helper 只表达当前 op 的局部成本承接，不负责累计、调度或运行时执行。
- `kind2`、`kind3` 与其他旧 kind 不再属于当前 helper 输入域。

## API详细说明

### `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::add(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`

- api：`template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::add(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `const Memory<Space, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`S_INT`。
- 使用示例：

  ```cpp
  #include "include/npu_demo/npu_demo.h"

  using namespace npu_demo;
  S_INT add_cost = cost::add<GM, float, float, compute>(out, lhs, rhs);
  ```
- 功能说明：定义逐元素加法的成本 helper。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；参数顺序固定为 `out -> lhs -> rhs`；模板顺序固定为 `Space -> InType -> OutType -> Kind`；不公开 `cost::kernel::add`、`cost<OpTag, ...>` 或旧 `Nn` 成本别名；非法组合必须稳定失败。

### `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::sub(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`

- api：`template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::sub(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `const Memory<Space, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`S_INT`。
- 使用示例：

  ```cpp
  #include "include/npu_demo/npu_demo.h"

  using namespace npu_demo;
  S_INT sub_cost = cost::sub<GM, float, float, compute>(out, lhs, rhs);
  ```
- 功能说明：定义逐元素减法的成本 helper。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；参数顺序固定为 `out -> lhs -> rhs`；模板顺序固定为 `Space -> InType -> OutType -> Kind`；不公开 `cost::kernel::sub`、`cost<OpTag, ...>` 或旧 `Nn` 成本别名；非法组合必须稳定失败。

### `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::mul(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`

- api：`template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::mul(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `const Memory<Space, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`S_INT`。
- 使用示例：

  ```cpp
  #include "include/npu_demo/npu_demo.h"

  using namespace npu_demo;
  S_INT mul_cost = cost::mul<GM, float, float, compute>(out, lhs, rhs);
  ```
- 功能说明：定义逐元素乘法的成本 helper。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；参数顺序固定为 `out -> lhs -> rhs`；模板顺序固定为 `Space -> InType -> OutType -> Kind`；不公开 `cost::kernel::mul`、`cost<OpTag, ...>` 或旧 `Nn` 成本别名；非法组合必须稳定失败。

### `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::truediv(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`

- api：`template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::truediv(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `const Memory<Space, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`S_INT`。
- 使用示例：

  ```cpp
  #include "include/npu_demo/npu_demo.h"

  using namespace npu_demo;
  S_INT div_cost = cost::truediv<TSM, float, float, memory>(out, lhs, rhs);
  ```
- 功能说明：定义逐元素真除法的成本 helper。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；参数顺序固定为 `out -> lhs -> rhs`；模板顺序固定为 `Space -> InType -> OutType -> Kind`；不公开 `cost::kernel::truediv`、`cost<OpTag, ...>` 或旧 `Nn` 成本别名；非法组合必须稳定失败。

### `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::eq(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`

- api：`template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::eq(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `const Memory<Space, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`S_INT`。
- 使用示例：

  ```cpp
  #include "include/npu_demo/npu_demo.h"

  using namespace npu_demo;
  S_INT eq_cost = cost::eq<GM, float, bool, compute>(out, lhs, rhs);
  ```
- 功能说明：定义逐元素相等比较的成本 helper。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；参数顺序固定为 `out -> lhs -> rhs`；模板顺序固定为 `Space -> InType -> OutType -> Kind`；本轮不开放额外 predicate 容器类型；非法组合必须稳定失败。

### `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::ne(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`

- api：`template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::ne(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `const Memory<Space, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`S_INT`。
- 使用示例：

  ```cpp
  #include "include/npu_demo/npu_demo.h"

  using namespace npu_demo;
  S_INT ne_cost = cost::ne<GM, float, bool, compute>(out, lhs, rhs);
  ```
- 功能说明：定义逐元素不等比较的成本 helper。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；参数顺序固定为 `out -> lhs -> rhs`；模板顺序固定为 `Space -> InType -> OutType -> Kind`；本轮不开放额外 predicate 容器类型；非法组合必须稳定失败。

### `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::lt(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`

- api：`template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::lt(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `const Memory<Space, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`S_INT`。
- 使用示例：

  ```cpp
  #include "include/npu_demo/npu_demo.h"

  using namespace npu_demo;
  S_INT lt_cost = cost::lt<GM, float, bool, compute>(out, lhs, rhs);
  ```
- 功能说明：定义逐元素小于比较的成本 helper。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；参数顺序固定为 `out -> lhs -> rhs`；模板顺序固定为 `Space -> InType -> OutType -> Kind`；本轮不开放额外 predicate 容器类型；非法组合必须稳定失败。

### `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::le(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`

- api：`template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::le(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `const Memory<Space, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`S_INT`。
- 使用示例：

  ```cpp
  #include "include/npu_demo/npu_demo.h"

  using namespace npu_demo;
  S_INT le_cost = cost::le<GM, float, bool, compute>(out, lhs, rhs);
  ```
- 功能说明：定义逐元素小于等于比较的成本 helper。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；参数顺序固定为 `out -> lhs -> rhs`；模板顺序固定为 `Space -> InType -> OutType -> Kind`；本轮不开放额外 predicate 容器类型；非法组合必须稳定失败。

### `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::gt(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`

- api：`template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::gt(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `const Memory<Space, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`S_INT`。
- 使用示例：

  ```cpp
  #include "include/npu_demo/npu_demo.h"

  using namespace npu_demo;
  S_INT gt_cost = cost::gt<GM, float, bool, compute>(out, lhs, rhs);
  ```
- 功能说明：定义逐元素大于比较的成本 helper。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；参数顺序固定为 `out -> lhs -> rhs`；模板顺序固定为 `Space -> InType -> OutType -> Kind`；本轮不开放额外 predicate 容器类型；非法组合必须稳定失败。

### `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::ge(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`

- api：`template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::ge(const Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `const Memory<Space, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`S_INT`。
- 使用示例：

  ```cpp
  #include "include/npu_demo/npu_demo.h"

  using namespace npu_demo;
  S_INT ge_cost = cost::ge<GM, float, bool, compute>(out, lhs, rhs);
  ```
- 功能说明：定义逐元素大于等于比较的成本 helper。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；参数顺序固定为 `out -> lhs -> rhs`；模板顺序固定为 `Space -> InType -> OutType -> Kind`；本轮不开放额外 predicate 容器类型；非法组合必须稳定失败。

### `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::exp(const Memory<Space, OutType>& out, const Memory<Space, InType>& input)`

- api：`template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::exp(const Memory<Space, OutType>& out, const Memory<Space, InType>& input)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `const Memory<Space, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `input`：输入对象，作为当前接口读取或转换的来源；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`S_INT`。
- 使用示例：

  ```cpp
  #include "include/npu_demo/npu_demo.h"

  using namespace npu_demo;
  S_INT exp_cost = cost::exp<TSM, float, float, compute>(out, input);
  ```
- 功能说明：定义一元指数运算的成本 helper。
- 注意事项：输入 shape、dtype 和 space 必须符合对应 operation 合同；参数顺序固定为 `out -> input`；模板顺序固定为 `Space -> InType -> OutType -> Kind`；非法组合必须稳定失败。

### `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::select(const Memory<Space, OutType>& out, const Memory<Space, bool>& cond, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`

- api：`template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::select(const Memory<Space, OutType>& out, const Memory<Space, bool>& cond, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `const Memory<Space, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `cond`：条件表达式，用于控制 select、分支或循环是否执行；类型 `const Memory<Space, bool>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`S_INT`。
- 使用示例：

  ```cpp
  #include "include/npu_demo/npu_demo.h"

  using namespace npu_demo;
  S_INT select_cost = cost::select<GM, float, float, compute>(out, cond, lhs, rhs);
  ```
- 功能说明：定义条件选择运算的成本 helper。
- 注意事项：输入 shape、dtype、space 和条件缓冲区必须符合对应 operation 合同；参数顺序固定为 `out -> cond -> lhs -> rhs`；模板顺序固定为 `Space -> InType -> OutType -> Kind`；非法组合必须稳定失败。

### `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::reduce_sum(const Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`

- api：`template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::reduce_sum(const Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `const Memory<Space, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `input`：输入对象，作为当前接口读取或转换的来源；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `axis`：轴编号，指定 reduce、softmax、reshape 或维度相关操作的作用维度；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`S_INT`。
- 使用示例：

  ```cpp
  #include "include/npu_demo/npu_demo.h"

  using namespace npu_demo;
  S_INT reduce_cost = cost::reduce_sum<GM, float, float, memory>(out, input, 1);
  ```
- 功能说明：定义求和归约的成本 helper。
- 注意事项：输入 shape、dtype、space 和 `axis` 必须符合对应 operation 合同；参数顺序固定为 `out -> input -> axis`；模板顺序固定为 `Space -> InType -> OutType -> Kind`；本轮不定义 keepdim 或 axis 容器变体；非法组合必须稳定失败。

### `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::reduce_min(const Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`

- api：`template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::reduce_min(const Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `const Memory<Space, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `input`：输入对象，作为当前接口读取或转换的来源；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `axis`：轴编号，指定 reduce、softmax、reshape 或维度相关操作的作用维度；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`S_INT`。
- 使用示例：

  ```cpp
  #include "include/npu_demo/npu_demo.h"

  using namespace npu_demo;
  S_INT min_cost = cost::reduce_min<GM, float, float, memory>(out, input, 1);
  ```
- 功能说明：定义最小值归约的成本 helper。
- 注意事项：输入 shape、dtype、space 和 `axis` 必须符合对应 operation 合同；参数顺序固定为 `out -> input -> axis`；模板顺序固定为 `Space -> InType -> OutType -> Kind`；本轮不定义 keepdim 或 axis 容器变体；非法组合必须稳定失败。

### `template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::reduce_max(const Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`

- api：`template <MemorySpace Space, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::reduce_max(const Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `const Memory<Space, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `input`：输入对象，作为当前接口读取或转换的来源；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `axis`：轴编号，指定 reduce、softmax、reshape 或维度相关操作的作用维度；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`S_INT`。
- 使用示例：

  ```cpp
  #include "include/npu_demo/npu_demo.h"

  using namespace npu_demo;
  S_INT max_cost = cost::reduce_max<GM, float, float, memory>(out, input, 1);
  ```
- 功能说明：定义最大值归约的成本 helper。
- 注意事项：输入 shape、dtype、space 和 `axis` 必须符合对应 operation 合同；参数顺序固定为 `out -> input -> axis`；模板顺序固定为 `Space -> InType -> OutType -> Kind`；本轮不定义 keepdim 或 axis 容器变体；非法组合必须稳定失败。

### `template <MemorySpace LhsSpace, MemorySpace RhsSpace, MemorySpace OutSpace, typename LhsType, typename RhsType, typename OutType, CostKind Kind> S_INT npu_demo::cost::matmul(const Memory<OutSpace, OutType>& out, const Memory<LhsSpace, LhsType>& lhs, const Memory<RhsSpace, RhsType>& rhs)`

- api：`template <MemorySpace LhsSpace, MemorySpace RhsSpace, MemorySpace OutSpace, typename LhsType, typename RhsType, typename OutType, CostKind Kind> S_INT npu_demo::cost::matmul(const Memory<OutSpace, OutType>& out, const Memory<LhsSpace, LhsType>& lhs, const Memory<RhsSpace, RhsType>& rhs)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `const Memory<OutSpace, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<LhsSpace, LhsType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<RhsSpace, RhsType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`S_INT`。
- 使用示例：

  ```cpp
  #include "include/npu_demo/npu_demo.h"

  using namespace npu_demo;
  S_INT matmul_cost = cost::matmul<TSM, TSM, TLM1, float, float, float, compute>(out, lhs, rhs);
  ```
- 功能说明：定义矩阵乘法的成本 helper。
- 注意事项：输入 shape、dtype 和 space 必须符合对应 operation 合同；参数顺序固定为 `out -> lhs -> rhs`；模板顺序固定为 `LhsSpace -> RhsSpace -> OutSpace -> LhsType -> RhsType -> OutType -> Kind`；多空间 helper 的模板参数顺序不得为了成本接口单独重排；非法组合必须稳定失败。

### `template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::img2col1d(const Memory<OutputSpace, OutType>& out, const Memory<InputSpace, InType>& input, long long k, long long s, long long d, long long p_left, long long p_right)`

- api：`template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::img2col1d(const Memory<OutputSpace, OutType>& out, const Memory<InputSpace, InType>& input, long long k, long long s, long long d, long long p_left, long long p_right)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `const Memory<OutputSpace, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `input`：输入对象，作为当前接口读取或转换的来源；类型 `const Memory<InputSpace, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `k`：核大小、索引或计数参数，具体含义由当前 API 名称限定；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `s`：步长或缩放参数，具体含义由当前 API 名称限定；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `d`：dilation 或距离参数，具体含义由当前 API 名称限定；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `p_left`：`p_left` 输入值，参与 `img2col1d` 的公开处理流程；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `p_right`：`p_right` 输入值，参与 `img2col1d` 的公开处理流程；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`S_INT`。
- 使用示例：

  ```cpp
  #include "include/npu_demo/npu_demo.h"

  using namespace npu_demo;
  S_INT img2col_cost = cost::img2col1d<GM, TSM, float, float, compute>(out, input, 3, 1, 1, 0, 0);
  ```
- 功能说明：定义一维 `img2col` 的成本 helper。
- 注意事项：输入 shape、dtype、space、kernel、stride、dilation 和 padding 必须符合对应 operation 合同；模板与参数顺序跟随对应 `Kernel` helper，并在模板末尾追加 `Kind`；非法组合必须稳定失败。

### `template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::img2col2d(const Memory<OutputSpace, OutType>& out, const Memory<InputSpace, InType>& input, long long kh, long long kw, long long sh, long long sw, long long dh, long long dw, long long ph, long long pw, long long pl, long long pr)`

- api：`template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType, CostKind Kind> S_INT npu_demo::cost::img2col2d(const Memory<OutputSpace, OutType>& out, const Memory<InputSpace, InType>& input, long long kh, long long kw, long long sh, long long sw, long long dh, long long dw, long long ph, long long pw, long long pl, long long pr)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `const Memory<OutputSpace, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `input`：输入对象，作为当前接口读取或转换的来源；类型 `const Memory<InputSpace, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `kh`：卷积或池化窗口高度，定义二维窗口在高维方向的大小；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `kw`：卷积或池化窗口宽度，定义二维窗口在宽维方向的大小；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `sh`：高度方向步长，定义卷积或池化窗口在高维方向每次移动的距离；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `sw`：宽度方向步长，定义卷积或池化窗口在宽维方向每次移动的距离；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `dh`：高度方向 dilation，定义卷积或池化窗口在高维方向的元素间隔；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `dw`：宽度方向 dilation，定义卷积或池化窗口在宽维方向的元素间隔；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `ph`：高度方向 padding，定义卷积或池化在高维方向补边大小；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `pw`：宽度方向 padding，定义卷积或池化在宽维方向补边大小；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `pl`：左侧 padding，定义一维或二维窗口左侧补边大小；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `pr`：右侧 padding，定义一维或二维窗口右侧补边大小；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`S_INT`。
- 使用示例：

  ```cpp
  #include "include/npu_demo/npu_demo.h"

  using namespace npu_demo;
  S_INT img2col_cost = cost::img2col2d<GM, TSM, float, float, compute>(
      out, input, 3, 3, 1, 1, 1, 1, 0, 0, 0, 0);
  ```
- 功能说明：定义二维 `img2col` 的成本 helper。
- 注意事项：输入 shape、dtype、space、kernel、stride、dilation 和 padding 必须符合对应 operation 合同；模板与参数顺序跟随对应 `Kernel` helper，并在模板末尾追加 `Kind`；非法组合必须稳定失败。

## 测试

- 测试文件：
  - `test/dsl/gen_kernel/emit/test_package.py`
  - `test/dsl/gen_kernel/test_gen_kernel.py`
  - `test/include/api/test_cost.py`
- 执行命令：
  - `pytest -q test/include/api/test_cost.py`
  - `pytest -q test/dsl/gen_kernel/emit/test_package.py -k "tuner_cost or npu_demo"`
  - `pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k "tuner_cost or cost_function or npu_demo"`

### 测试目标

- 通过当前聚合入口 `test_include_api_cost_kernel_signatures_compile` 一次性验证 `Kernel cost` helper 的声明、模板顺序与 `S_INT` 返回合同。
- 验证 `tuner.cost(op_name="kernel.add" | "kernel.binary_elewise" | "kernel.exp" | "kernel.select" | "kernel.reduce" | "kernel.matmul" | "kernel.img2col2d")` 的节点级文本发射。
- 验证完整 cost function 生成后可消费 `cost::add` 与 `cost::matmul`。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-COST-KERNEL-001 | 生成/编译 | `cost::add` 独立实例化 | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_include_api_cost_kernel_signatures_compile`。 | 生成源码、IR 文本或编译结果体现“`cost::add` 独立实例化”场景。 | `test_include_api_cost_kernel_signatures_compile` |
| TC-COST-KERNEL-002 | 生成/编译 | `cost::matmul` 独立实例化 | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_include_api_cost_kernel_signatures_compile`。 | 生成源码、IR 文本或编译结果体现“`cost::matmul` 独立实例化”场景。 | `test_include_api_cost_kernel_signatures_compile` |
| TC-COST-KERNEL-003 | pass 改写 | `emit_c` 节点级发射 `kernel.add` 成本调用 | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tuner_cost_kernel_add`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`emit_c` 节点级发射 `kernel.add` 成本调用”场景。 | `test_emit_c_lowers_npu_demo_tuner_cost_kernel_add` |
| TC-COST-KERNEL-003A | pass 改写 | `emit_c` 节点级发射 `kernel.binary_elewise` 成本调用 | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tuner_cost_kernel_binary_elewise`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`emit_c` 节点级发射 `kernel.binary_elewise` 成本调用”场景。 | `test_emit_c_lowers_npu_demo_tuner_cost_kernel_binary_elewise` |
| TC-COST-KERNEL-003B | pass 改写 | `emit_c` 节点级发射 `kernel.exp/select/reduce` 成本调用 | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tuner_cost_kernel_exp_select_reduce`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`emit_c` 节点级发射 `kernel.exp/select/reduce` 成本调用”场景。 | `test_emit_c_lowers_npu_demo_tuner_cost_kernel_exp_select_reduce` |
| TC-COST-KERNEL-004 | 生成/编译 | `gen_kernel` 函数级发射 `kernel.matmul` 成本函数 | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_gen_kernel_emits_npu_demo_cost_matmul_function`。 | 生成源码、IR 文本或编译结果体现“`gen_kernel` 函数级发射 `kernel.matmul` 成本函数”场景。 | `test_gen_kernel_emits_npu_demo_cost_matmul_function` |
| TC-COST-KERNEL-005 | pass 改写 | `emit_c` 节点级发射 `kernel.img2col2d` 成本调用 | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `test_emit_c_lowers_npu_demo_tuner_cost_kernel_img2col2d`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“`emit_c` 节点级发射 `kernel.img2col2d` 成本调用”场景。 | `test_emit_c_lowers_npu_demo_tuner_cost_kernel_img2col2d` |
