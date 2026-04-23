# Kernel

## 功能简介

定义 include/api 层统一对外的 Kernel 计算 API 头文件规范（`include/api/Kernel.h`），作为当前 `kernel dialect emit` 的唯一公共计算接口承载层，替代已删除的 `include/api/Nn.h` 公开层。

- `Kernel` 只冻结当前 `emit_c/gen_kernel(target=npu_demo)` 已进入合同真源的 helper 集合。
- 统一源码口径采用 `out-first`，并固定模板参数顺序为“先 space、后 type；多 space 时按 operand 顺序展开”。
- 对 `target=npu_demo`，生成源码必须收口为 `npu_demo::<helper><...>(out, ...)` 的稳定调用形态。

## 文档信息

- 创建者：`朽木露琪亚`
- 最后一次更改：`朽木露琪亚`
- `spec`：[`spec/include/api/Kernel.md`](../../../spec/include/api/Kernel.md)
- `统一头文件`：[`include/api/Kernel.h`](../../../include/api/Kernel.h)
- `功能实现`：[`include/api/Kernel.h`](../../../include/api/Kernel.h)、[`include/npu_demo/Kernel.h`](../../../include/npu_demo/Kernel.h)
- `test`：[`test/include/api/test_kernel.py`](../../../test/include/api/test_kernel.py)、[`test/dsl/test_emit_c.py`](../../../test/dsl/test_emit_c.py)、[`test/dsl/test_gen_kernel.py`](../../../test/dsl/test_gen_kernel.py)

## 依赖

- [`spec/include/api/Core.md`](../../../spec/include/api/Core.md)：统一 `Status` / `StatusCode` 返回语义。
- [`spec/include/api/Memory.md`](../../../spec/include/api/Memory.md)：统一 `Memory<Space, T>` / `MemorySpace` / `MemoryFormat` 语义。
- [`spec/include/api/cost/Kernel.md`](../../../spec/include/api/cost/Kernel.md)：定义与当前 Kernel helper 一一对应的成本 helper 合同。
- [`spec/dialect/kernel.md`](../../../spec/dialect/kernel.md)：`kernel.*` IR 到公开 helper 名的职责映射来源。
- [`spec/dsl/emit_c.md`](../../../spec/dsl/emit_c.md)：冻结 `target=npu_demo` 下 `kernel.* -> npu_demo::<helper>` 的节点级文本合同。
- [`spec/dsl/gen_kernel.md`](../../../spec/dsl/gen_kernel.md)：冻结 `target=npu_demo` 下函数级源码只消费本文件定义的公共 helper。

## 目标

- 建立 `include/api/Kernel.h` 作为当前唯一公共计算接口层，承接 `kernel dialect emit` 已纳入合同真源的 helper 集合。
- 删除 `include/api/Nn.h` 对外职责，不再允许 `Nn` 作为公开计算层与 `Kernel` 并存。
- 冻结当前公开 helper 的名字、模板顺序、参数顺序、返回值语义和最小输入约束，供 `include/npu_demo/Kernel.h`、`emit_c` 与 `gen_kernel` 统一消费。
- 让 `emit_c/gen_kernel(target=npu_demo)` 只消费 `Kernel` 公共接口，不再保留旧 `Nn` 公开名或额外 helper 别名。

## 限制与边界

- 本规范只覆盖当前已进入合同真源的 helper：`add`、`sub`、`mul`、`truediv`、`eq`、`ne`、`lt`、`le`、`gt`、`ge`、`exp`、`select`、`reduce_sum`、`reduce_min`、`matmul`、`img2col1d`、`img2col2d`。
- `broadcast`、`broadcast_to`、`softmax`、`cast`、`reduce_max` 与其他旧 `Nn` 公开名，不属于本轮 `Kernel` 公共接口。
- 除 `matmul`、`img2col1d`、`img2col2d` 外，当前公开 helper 默认要求输入与输出使用同一 `MemorySpace`；若后端实现不支持某个合法组合，必须显式失败，不能静默回退。
- 所有 helper 都要求调用方显式提供输出 `Memory`，统一返回 `Status`；不得通过函数返回值承接输出 memory。
- `include/api/Kernel.h` 只冻结公共 helper 名、模板顺序、参数顺序与最小类型边界，不承接后端私有实现细节。
- `target=npu_demo` 的稳定源码口径固定为 `npu_demo::<helper><...>(out, ...)`；不得回退到 `cpu::...`、旧 `Nn*` 公共符号、表达式拼接或隐式临时变量承接。
- 本文件不定义 launch、barrier、dynamic memory、view/slice/deslice 的职责；这些分别由 [`spec/include/api/Arch.md`](../../../spec/include/api/Arch.md) 与 [`spec/include/api/Dma.md`](../../../spec/include/api/Dma.md) 承接。

## 公开接口

### `add` / `sub` / `mul` / `truediv`

功能说明：

- 定义逐元素二元算术 helper 的统一公共接口。
- 适用于 `kernel.binary_elewise(kind="add" | "sub" | "mul" | "truediv")` 的稳定公开落点。

参数说明：

- `Space (template MemorySpace)`：输入与输出共享的内存空间模板参数。
- `InType (template type)`：输入元素类型。
- `OutType (template type)`：输出元素类型。
- `out (Memory<Space, OutType>&)`：输出视图。
- `lhs (const Memory<Space, InType>&)`：左操作数视图。
- `rhs (const Memory<Space, InType>&)`：右操作数视图。

使用示例：

```cpp
#include "include/npu_demo/npu_demo.h"

Status st = npu_demo::add<GM, float, float>(out, lhs, rhs);
Status st2 = npu_demo::truediv<TSM, int32_t, float>(out, lhs, rhs);
```

注意事项：

- 参数顺序固定为 `out -> lhs -> rhs`。
- 模板顺序固定为 `Space -> InType -> OutType`。
- 不定义 `lhs/rhs/out` 重排别名，也不定义旧 `NnAddOp` / `NnSubOp` 等公开 helper 名。

返回与限制：

- 返回类型：`Status`。
- 返回语义：`StatusCode::kOk` 表示 helper 请求被成功承接；非 `kOk` 表示失败。
- 限制条件：本轮不定义隐式广播、标量 overload 或跨空间输入/输出混用。

### `eq` / `ne` / `lt` / `le` / `gt` / `ge`

功能说明：

- 定义逐元素比较 helper 的统一公共接口。
- 适用于 `kernel.binary_elewise(kind="eq" | "ne" | "lt" | "le" | "gt" | "ge")` 的稳定公开落点。

参数说明：

- `Space (template MemorySpace)`：输入与输出共享的内存空间模板参数。
- `InType (template type)`：输入元素类型。
- `OutType (template type)`：输出元素类型；当前稳定公开口径要求可表达 predicate 结果，`target=npu_demo` 下固定收口为 `bool`。
- `out (Memory<Space, OutType>&)`：输出 predicate 视图。
- `lhs (const Memory<Space, InType>&)`：左操作数视图。
- `rhs (const Memory<Space, InType>&)`：右操作数视图。

使用示例：

```cpp
#include "include/npu_demo/npu_demo.h"

Status st = npu_demo::eq<GM, float, bool>(out, lhs, rhs);
Status st2 = npu_demo::gt<TLM1, int32_t, bool>(out, lhs, rhs);
```

注意事项：

- 参数顺序固定为 `out -> lhs -> rhs`。
- 模板顺序固定为 `Space -> InType -> OutType`。
- `target=npu_demo` 的稳定源码合同要求比较输出为 `Memory<Space, bool>`。

返回与限制：

- 返回类型：`Status`。
- 返回语义：返回比较 helper 的承接状态。
- 限制条件：本轮不开放隐式类型提升、跨空间比较或额外 predicate 容器类型。

### `exp`

功能说明：

- 定义一元指数 helper 的统一公共接口。
- 适用于 `kernel.exp` 的稳定公开落点。

参数说明：

- `Space (template MemorySpace)`：输入与输出共享的内存空间模板参数。
- `InType (template type)`：输入元素类型。
- `OutType (template type)`：输出元素类型。
- `out (Memory<Space, OutType>&)`：输出视图。
- `input (const Memory<Space, InType>&)`：输入视图。

使用示例：

```cpp
#include "include/npu_demo/npu_demo.h"

Status st = npu_demo::exp<TSM, float, float>(out, input);
```

注意事项：

- 参数顺序固定为 `out -> input`。
- 模板顺序固定为 `Space -> InType -> OutType`。

返回与限制：

- 返回类型：`Status`。
- 返回语义：返回一元 helper 的承接状态。
- 限制条件：本轮不定义额外 unary helper 或 inplace 特判。

### `select`

功能说明：

- 定义条件选择 helper 的统一公共接口。
- 适用于 `kernel.select` 的稳定公开落点。

参数说明：

- `Space (template MemorySpace)`：条件、输入与输出共享的内存空间模板参数。
- `InType (template type)`：数据输入元素类型。
- `OutType (template type)`：输出元素类型。
- `out (Memory<Space, OutType>&)`：输出视图。
- `cond (const Memory<Space, bool>&)`：条件视图。
- `lhs (const Memory<Space, InType>&)`：条件为真时选择的输入视图。
- `rhs (const Memory<Space, InType>&)`：条件为假时选择的输入视图。

使用示例：

```cpp
#include "include/npu_demo/npu_demo.h"

Status st = npu_demo::select<GM, float, float>(out, cond, lhs, rhs);
```

注意事项：

- 参数顺序固定为 `out -> cond -> lhs -> rhs`。
- 模板顺序固定为 `Space -> InType -> OutType`。

返回与限制：

- 返回类型：`Status`。
- 返回语义：返回 `select` helper 的承接状态。
- 限制条件：本轮不开放标量条件、标量输入或跨空间选择。

### `reduce_sum` / `reduce_min`

功能说明：

- 定义当前已进入合同真源的 reduce helper 公共接口。
- 适用于 `kernel.reduce(kind="sum")` 与 `kernel.reduce_min` 的稳定公开落点。

参数说明：

- `Space (template MemorySpace)`：输入与输出共享的内存空间模板参数。
- `InType (template type)`：输入元素类型。
- `OutType (template type)`：输出元素类型。
- `out (Memory<Space, OutType>&)`：输出视图。
- `input (const Memory<Space, InType>&)`：输入视图。
- `axis (long long)`：规约轴。

使用示例：

```cpp
#include "include/npu_demo/npu_demo.h"

Status st = npu_demo::reduce_sum<GM, float, float>(out, input, 1);
Status st2 = npu_demo::reduce_min<TSM, int32_t, int32_t>(out, input, 0);
```

注意事项：

- 参数顺序固定为 `out -> input -> axis`。
- 模板顺序固定为 `Space -> InType -> OutType`。
- `reduce_max` 尚未进入本轮公共 `Kernel` 接口。

返回与限制：

- 返回类型：`Status`。
- 返回语义：返回规约 helper 的承接状态。
- 限制条件：本轮只冻结 `reduce_sum` 与 `reduce_min`，不定义额外 keepdim/axis 容器变体。

### `matmul`

功能说明：

- 定义矩阵乘 helper 的统一公共接口。
- 适用于 `kernel.matmul` 的稳定公开落点。

参数说明：

- `LhsSpace (template MemorySpace)`：左输入空间模板参数。
- `RhsSpace (template MemorySpace)`：右输入空间模板参数。
- `OutSpace (template MemorySpace)`：输出空间模板参数。
- `LhsType (template type)`：左输入元素类型。
- `RhsType (template type)`：右输入元素类型。
- `OutType (template type)`：输出元素类型。
- `out (Memory<OutSpace, OutType>&)`：输出视图。
- `lhs (const Memory<LhsSpace, LhsType>&)`：左输入视图。
- `rhs (const Memory<RhsSpace, RhsType>&)`：右输入视图。

使用示例：

```cpp
#include "include/npu_demo/npu_demo.h"

Status st = npu_demo::matmul<TSM, TSM, TLM1, float, float, float>(out, lhs, rhs);
```

注意事项：

- 参数顺序固定为 `out -> lhs -> rhs`。
- 模板顺序固定为 `LhsSpace -> RhsSpace -> OutSpace -> LhsType -> RhsType -> OutType`。
- `matmul` 是本轮唯一稳定公开的多 space Kernel helper。

返回与限制：

- 返回类型：`Status`。
- 返回语义：返回 `matmul` helper 的承接状态。
- 限制条件：本轮不定义 batched matmul、bias 融合或额外 transpose 标志。

### `img2col1d` / `img2col2d`

功能说明：

- 定义 `img2col` family 的统一公共接口。
- 适用于 `kernel.img2col1d` 与 `kernel.img2col2d` 的稳定公开落点。

参数说明：

- `InputSpace (template MemorySpace)`：输入空间模板参数。
- `OutputSpace (template MemorySpace)`：输出空间模板参数。
- `InType (template type)`：输入元素类型。
- `OutType (template type)`：输出元素类型。
- `out (Memory<OutputSpace, OutType>&)`：输出视图。
- `input (const Memory<InputSpace, InType>&)`：输入视图。
- `k/kh/kw/sh/sw/dh/dw/ph/pw/pl/pr (long long)`：窗口与步长参数。

使用示例：

```cpp
#include "include/npu_demo/npu_demo.h"

Status st1 = npu_demo::img2col1d<GM, TSM, float, float>(out, input, 3, 2, 1, 1, 1);
Status st2 = npu_demo::img2col2d<GM, TSM, float, float>(out, input, 3, 2, 1, 2, 1, 1, 1, 0, 0, 1);
```

注意事项：

- 参数顺序固定为 `out -> input -> 其余标量参数`。
- 模板顺序固定为 `InputSpace -> OutputSpace -> InType -> OutType`。
- `img2col1d` 与 `img2col2d` 允许输入与输出使用不同 `MemorySpace`，但必须保持 helper 名与参数顺序稳定。

返回与限制：

- 返回类型：`Status`。
- 返回语义：返回 `img2col` helper 的承接状态。
- 限制条件：本轮不定义额外 layout alias、padding 结构体或隐式输出分配。

## 测试

- 测试文件：[`test/include/api/test_kernel.py`](../../../test/include/api/test_kernel.py)
- 执行命令：`pytest -q test/include/api/test_kernel.py`
- 测试目标：锁定 `include/api/Kernel.h` 的 helper 集合、模板顺序、参数顺序与删除 `Nn` 公开层后的唯一入口语义。

- 测试文件：[`test/dsl/test_emit_c.py`](../../../test/dsl/test_emit_c.py)
- 执行命令：`pytest -q test/dsl/test_emit_c.py`
- 测试目标：锁定 `target=npu_demo` 时 `kernel.*` 节点发射到 `npu_demo::<helper><...>(out, ...)` 的文本合同。

- 测试文件：[`test/dsl/test_gen_kernel.py`](../../../test/dsl/test_gen_kernel.py)
- 执行命令：`pytest -q test/dsl/test_gen_kernel.py`
- 测试目标：锁定 `gen_kernel(target=npu_demo)` 只消费 `Kernel` 公共接口，不再依赖公开 `Nn` 层。

- 功能与用例清单：
  - `test_include_api_kernel_exports_only_public_kernel_helpers`：锁定 `Kernel` helper 集合与删除 `Nn` 公开层后的唯一入口语义。
  - `test_emit_c_lowers_npu_demo_kernel_helpers_out_first`：锁定 `target=npu_demo` 的 `out-first` helper 文本。
  - `test_gen_kernel_emits_npu_demo_kernel_helpers_without_public_nn_alias`：锁定函数级源码不再回退到公开 `Nn` 名称。
