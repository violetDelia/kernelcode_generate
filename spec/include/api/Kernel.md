# Kernel

## 功能简介

定义 include/api 层统一对外的 Kernel 计算 API 头文件规范（`include/api/Kernel.h`），作为当前 `kernel dialect emit` 的唯一公共计算接口承载层，替代已删除的 `include/api/Nn.h` 公开层。

- `Kernel` 只冻结当前 `emit_c/gen_kernel(target=npu_demo)` 已进入合同真源的 helper 集合。
- 统一源码口径采用 `out-first`，并固定模板参数顺序为“先 space、后 type；多 space 时按 operand 顺序展开”。
- 对 `target=npu_demo`，生成源码必须收口为 `npu_demo::<helper><...>(out, ...)` 的稳定调用形态。
- 逐元素 helper 按 same-shape 多维张量语义执行；不在本层隐式 broadcast。

## API 列表

- `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::add(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::sub(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::mul(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::truediv(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::eq(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::ne(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::lt(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::le(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::gt(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::ge(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::exp(Memory<Space, OutType>& out, const Memory<Space, InType>& input)`
- `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::select(Memory<Space, OutType>& out, const Memory<Space, bool>& cond, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::reduce_sum(Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`
- `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::reduce_min(Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`
- `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::reduce_max(Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`
- `template <MemorySpace LhsSpace, MemorySpace RhsSpace, MemorySpace OutSpace, typename LhsType, typename RhsType, typename OutType> Status npu_demo::matmul(Memory<OutSpace, OutType>& out, const Memory<LhsSpace, LhsType>& lhs, const Memory<RhsSpace, RhsType>& rhs)`
- `template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType> Status npu_demo::img2col1d(Memory<OutputSpace, OutType>& out, const Memory<InputSpace, InType>& input, long long k, long long s, long long d, long long p_left, long long p_right)`
- `template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType> Status npu_demo::img2col2d(Memory<OutputSpace, OutType>& out, const Memory<InputSpace, InType>& input, long long kh, long long kw, long long sh, long long sw, long long dh, long long dw, long long ph, long long pw, long long pl, long long pr)`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/include/api/Kernel.md`](../../../spec/include/api/Kernel.md)
- `统一头文件`：[`include/api/Kernel.h`](../../../include/api/Kernel.h)
- `功能实现`：[`include/api/Kernel.h`](../../../include/api/Kernel.h)、[`include/npu_demo/Kernel.h`](../../../include/npu_demo/Kernel.h)
- `test`：[`test/include/api/test_kernel.py`](../../../test/include/api/test_kernel.py)、[`test/dsl/gen_kernel/emit/test_package.py`](../../../test/dsl/gen_kernel/emit/test_package.py)、[`test/dsl/gen_kernel/test_gen_kernel.py`](../../../test/dsl/gen_kernel/test_gen_kernel.py)

## 依赖

- [`spec/include/api/Core.md`](../../../spec/include/api/Core.md)：统一 `Status` / `StatusCode` 返回语义。
- [`spec/include/api/Memory.md`](../../../spec/include/api/Memory.md)：统一 `Memory<Space, T>` / `MemorySpace` / `MemoryFormat` 语义。
- [`spec/include/api/cost/Kernel.md`](../../../spec/include/api/cost/Kernel.md)：定义与当前 Kernel helper 一一对应的成本 helper 合同。
- [`spec/dialect/kernel.md`](../../../spec/dialect/kernel.md)：`kernel.*` IR 到公开 helper 名的职责映射来源。
- [`spec/dsl/gen_kernel/emit.md`](../../../spec/dsl/gen_kernel/emit.md)：冻结 `target=npu_demo` 下 `kernel.* -> npu_demo::<helper>` 的节点级文本合同。
- [`spec/dsl/gen_kernel/gen_kernel.md`](../../../spec/dsl/gen_kernel/gen_kernel.md)：冻结 `target=npu_demo` 下函数级源码只消费本文件定义的公共 helper。

## 目标

- 建立 `include/api/Kernel.h` 作为当前唯一公共计算接口层，定义 `kernel dialect emit` 已纳入合同真源的 helper 集合。
- 删除 `include/api/Nn.h` 对外职责，不再允许 `Nn` 作为公开计算层与 `Kernel` 并存。
- 冻结当前公开 helper 的名字、模板顺序、参数顺序、返回值语义和最小输入约束，供 `include/npu_demo/Kernel.h`、`emit_c` 与 `gen_kernel` 统一消费。
- 让 `emit_c/gen_kernel(target=npu_demo)` 只消费 `Kernel` 公共接口，不再保留旧 `Nn` 公开名或额外 helper 别名。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 本规范只覆盖当前已进入合同真源的 helper：`add`、`sub`、`mul`、`truediv`、`eq`、`ne`、`lt`、`le`、`gt`、`ge`、`exp`、`select`、`reduce_sum`、`reduce_min`、`reduce_max`、`matmul`、`img2col1d`、`img2col2d`。
- `broadcast`、`broadcast_to`、`softmax`、`cast` 与其他旧 `Nn` 公开名，不属于本轮 `Kernel` 公共接口。
- 除 `matmul`、`img2col1d`、`img2col2d` 外，当前公开 helper 默认要求输入与输出使用同一 `MemorySpace`；若后端实现不支持某个合法组合，必须显式失败，不能静默回退。
- 所有 helper 都要求调用方显式提供输出 `Memory`，统一返回 `Status`；不得通过函数返回值承接输出 memory。
- `include/api/Kernel.h` 只冻结公共 helper 名、模板顺序、参数顺序与最小类型边界，不承接后端私有实现细节。
- `target=npu_demo` 的稳定源码口径固定为 `npu_demo::<helper><...>(out, ...)`；不得回退到 `cpu::...`、旧 `Nn*` 公共符号、表达式拼接或隐式临时变量承接。
- 本文件不定义 launch、barrier、dynamic memory、view/slice/deslice 的职责；这些分别由 [`spec/include/api/Arch.md`](../../../spec/include/api/Arch.md) 与 [`spec/include/api/Dma.md`](../../../spec/include/api/Dma.md) 承接。
## API详细说明

### `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::add(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`

- api：`template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::add(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `Memory<Space, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Status`，表示执行状态。
- 使用示例：

  ```cpp
auto status = npu_demo::add(out, lhs, rhs);
```
- 功能说明：执行 `add`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::sub(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`

- api：`template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::sub(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `Memory<Space, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Status`，表示执行状态。
- 使用示例：

  ```cpp
auto status = npu_demo::sub(out, lhs, rhs);
```
- 功能说明：执行 `sub`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::mul(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`

- api：`template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::mul(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `Memory<Space, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Status`，表示执行状态。
- 使用示例：

  ```cpp
auto status = npu_demo::mul(out, lhs, rhs);
```
- 功能说明：执行 `mul`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::truediv(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`

- api：`template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::truediv(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `Memory<Space, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Status`，表示执行状态。
- 使用示例：

  ```cpp
auto status = npu_demo::truediv(out, lhs, rhs);
```
- 功能说明：执行 `truediv`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::eq(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`

- api：`template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::eq(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `Memory<Space, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Status`，表示执行状态。
- 使用示例：

  ```cpp
auto status = npu_demo::eq(out, lhs, rhs);
```
- 功能说明：执行 `eq`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::ne(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`

- api：`template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::ne(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `Memory<Space, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Status`，表示执行状态。
- 使用示例：

  ```cpp
auto status = npu_demo::ne(out, lhs, rhs);
```
- 功能说明：执行 `ne`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::lt(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`

- api：`template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::lt(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `Memory<Space, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Status`，表示执行状态。
- 使用示例：

  ```cpp
auto status = npu_demo::lt(out, lhs, rhs);
```
- 功能说明：执行 `lt`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::le(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`

- api：`template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::le(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `Memory<Space, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Status`，表示执行状态。
- 使用示例：

  ```cpp
auto status = npu_demo::le(out, lhs, rhs);
```
- 功能说明：执行 `le`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::gt(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`

- api：`template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::gt(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `Memory<Space, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Status`，表示执行状态。
- 使用示例：

  ```cpp
auto status = npu_demo::gt(out, lhs, rhs);
```
- 功能说明：执行 `gt`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::ge(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`

- api：`template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::ge(Memory<Space, OutType>& out, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `Memory<Space, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Status`，表示执行状态。
- 使用示例：

  ```cpp
auto status = npu_demo::ge(out, lhs, rhs);
```
- 功能说明：执行 `ge`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::exp(Memory<Space, OutType>& out, const Memory<Space, InType>& input)`

- api：`template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::exp(Memory<Space, OutType>& out, const Memory<Space, InType>& input)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `Memory<Space, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
  - `input`：输入对象，作为当前接口读取或转换的来源；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Status`，表示执行状态。
- 使用示例：

  ```cpp
auto status = npu_demo::exp(out, input);
```
- 功能说明：执行 `exp`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::select(Memory<Space, OutType>& out, const Memory<Space, bool>& cond, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`

- api：`template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::select(Memory<Space, OutType>& out, const Memory<Space, bool>& cond, const Memory<Space, InType>& lhs, const Memory<Space, InType>& rhs)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `Memory<Space, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
  - `cond`：条件表达式，用于控制 select、分支或循环是否执行；类型 `const Memory<Space, bool>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Status`，表示执行状态。
- 使用示例：

  ```cpp
auto status = npu_demo::select(out, cond, lhs, rhs);
```
- 功能说明：执行 `select`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::reduce_sum(Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`

- api：`template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::reduce_sum(Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `Memory<Space, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
  - `input`：输入对象，作为当前接口读取或转换的来源；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `axis`：轴编号，指定 reduce、softmax、reshape 或维度相关操作的作用维度；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Status`，表示执行状态。
- 使用示例：

  ```cpp
auto status = npu_demo::reduce_sum(out, input, 0);
```
- 功能说明：执行 `reduce_sum`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::reduce_min(Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`

- api：`template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::reduce_min(Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `Memory<Space, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
  - `input`：输入对象，作为当前接口读取或转换的来源；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `axis`：轴编号，指定 reduce、softmax、reshape 或维度相关操作的作用维度；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Status`，表示执行状态。
- 使用示例：

  ```cpp
auto status = npu_demo::reduce_min(out, input, 0);
```
- 功能说明：执行 `reduce_min`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::reduce_max(Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`

- api：`template <MemorySpace Space, typename InType, typename OutType> Status npu_demo::reduce_max(Memory<Space, OutType>& out, const Memory<Space, InType>& input, long long axis)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `Memory<Space, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
  - `input`：输入对象，作为当前接口读取或转换的来源；类型 `const Memory<Space, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `axis`：轴编号，指定 reduce、softmax、reshape 或维度相关操作的作用维度；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Status`，表示执行状态。
- 使用示例：

  ```cpp
auto status = npu_demo::reduce_max(out, input, 0);
```
- 功能说明：执行 `reduce_max`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `template <MemorySpace LhsSpace, MemorySpace RhsSpace, MemorySpace OutSpace, typename LhsType, typename RhsType, typename OutType> Status npu_demo::matmul(Memory<OutSpace, OutType>& out, const Memory<LhsSpace, LhsType>& lhs, const Memory<RhsSpace, RhsType>& rhs)`

- api：`template <MemorySpace LhsSpace, MemorySpace RhsSpace, MemorySpace OutSpace, typename LhsType, typename RhsType, typename OutType> Status npu_demo::matmul(Memory<OutSpace, OutType>& out, const Memory<LhsSpace, LhsType>& lhs, const Memory<RhsSpace, RhsType>& rhs)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `Memory<OutSpace, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<LhsSpace, LhsType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `const Memory<RhsSpace, RhsType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Status`，表示执行状态。
- 使用示例：

  ```cpp
auto status = npu_demo::matmul(out, lhs, rhs);
```
- 功能说明：执行 `matmul`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType> Status npu_demo::img2col1d(Memory<OutputSpace, OutType>& out, const Memory<InputSpace, InType>& input, long long k, long long s, long long d, long long p_left, long long p_right)`

- api：`template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType> Status npu_demo::img2col1d(Memory<OutputSpace, OutType>& out, const Memory<InputSpace, InType>& input, long long k, long long s, long long d, long long p_left, long long p_right)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `Memory<OutputSpace, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
  - `input`：输入对象，作为当前接口读取或转换的来源；类型 `const Memory<InputSpace, InType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `k`：核大小、索引或计数参数，具体含义由当前 API 名称限定；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `s`：步长或缩放参数，具体含义由当前 API 名称限定；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `d`：dilation 或距离参数，具体含义由当前 API 名称限定；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `p_left`：`p_left` 输入值，参与 `img2col1d` 的公开处理流程；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `p_right`：`p_right` 输入值，参与 `img2col1d` 的公开处理流程；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Status`，表示执行状态。
- 使用示例：

  ```cpp
auto status = npu_demo::img2col1d(out, input, 3, 1, 1, 0, 0);
```
- 功能说明：执行 `img2col1d`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType> Status npu_demo::img2col2d(Memory<OutputSpace, OutType>& out, const Memory<InputSpace, InType>& input, long long kh, long long kw, long long sh, long long sw, long long dh, long long dw, long long ph, long long pw, long long pl, long long pr)`

- api：`template <MemorySpace InputSpace, MemorySpace OutputSpace, typename InType, typename OutType> Status npu_demo::img2col2d(Memory<OutputSpace, OutType>& out, const Memory<InputSpace, InType>& input, long long kh, long long kw, long long sh, long long sw, long long dh, long long dw, long long ph, long long pw, long long pl, long long pr)`
- 参数：
  - `out`：输出对象或输出缓冲区，承接当前接口生成或计算的结果；类型 `Memory<OutputSpace, OutType>&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按引用传入，允许当前接口按公开语义修改该对象；非法值按该 API 的公开错误语义处理。
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
- 返回值：`Status`，表示执行状态。
- 使用示例：

  ```cpp
auto status = npu_demo::img2col2d(out, input, 3, 3, 1, 1, 1, 1, 0, 0, 0, 0);
```
- 功能说明：执行 `img2col2d`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

## 测试

- 测试文件：
  - `test/dsl/gen_kernel/emit/test_package.py`
  - `test/dsl/gen_kernel/test_gen_kernel.py`
  - `test/include/api/test_kernel.py`
- 执行命令：
  - `pytest -q test/include/api/test_kernel.py`
  - `pytest -q test/dsl/gen_kernel/emit/test_package.py`
  - `pytest -q test/dsl/gen_kernel/test_gen_kernel.py`

### 测试目标

- 锁定 `include/api/Kernel.h` 的 helper 集合、模板顺序、参数顺序与删除 `Nn` 公开层后的唯一入口语义。
- 锁定 `target=npu_demo` 时 `kernel.*` 节点发射到 `npu_demo::<helper><...>(out, ...)` 的文本合同。
- 锁定 `gen_kernel(target=npu_demo)` 只消费 `Kernel` 公共接口，不再依赖公开 `Nn` 层。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-INCLUDE-API-KERNEL-001 | 公开入口 | 锁定 `Kernel` helper 集合与删除 `Nn` 公开层后的唯一入口语义。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_include_api_kernel_exports_only_public_kernel_helpers`。 | 公开入口在“锁定 `Kernel` helper 集合与删除 `Nn` 公开层后的唯一入口语义。”场景下可导入、构造、注册或按名称发现。 | `test_include_api_kernel_exports_only_public_kernel_helpers` |
| TC-INCLUDE-API-KERNEL-002 | 解析/打印 | 锁定 `target=npu_demo` 的 `out-first` helper 文本。 | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_emit_c_lowers_npu_demo_kernel_helpers_out_first`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_emit_c_lowers_npu_demo_kernel_helpers_out_first` |
| TC-INCLUDE-API-KERNEL-003 | 公开入口 | 锁定函数级源码不再回退到公开 `Nn` 名称。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_gen_kernel_emits_npu_demo_kernel_helpers_without_public_nn_alias`。 | 公开入口在“锁定函数级源码不再回退到公开 `Nn` 名称。”场景下可导入、构造、注册或按名称发现。 | `test_gen_kernel_emits_npu_demo_kernel_helpers_without_public_nn_alias` |
