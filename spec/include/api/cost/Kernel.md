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

- 创建者：`睡觉小分队`
- 最后一次更改：`守护最好的爱莉希雅`
- `spec`：[`spec/include/api/cost/Kernel.md`](../../../../spec/include/api/cost/Kernel.md)
- `统一头文件`：[`include/api/cost/Kernel.h`](../../../../include/api/cost/Kernel.h)
- `功能实现`：[`include/npu_demo/cost/Kernel.h`](../../../../include/npu_demo/cost/Kernel.h)
- `test`：
  - `test/include/api/test_cost.py`
  - [`test/dsl/gen_kernel/emit/test_emit.py`](../../../../test/dsl/gen_kernel/emit/test_emit.py)
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

## 限制与边界

- 当前公开 helper 集合与 [`spec/include/api/Kernel.md`](../../../../spec/include/api/Kernel.md) 保持一致：`add`、`sub`、`mul`、`truediv`、`eq`、`ne`、`lt`、`le`、`gt`、`ge`、`exp`、`select`、`reduce_sum`、`reduce_min`、`reduce_max`、`matmul`、`img2col1d`、`img2col2d`。
- 当前不公开 `broadcast`、`softmax`、`cast` 或旧 `Nn` helper 的成本接口。
- cost helper 只表达当前 op 的局部成本承接，不负责累计、调度或运行时执行。
- `kind2`、`kind3` 与其他旧 kind 不再属于当前 helper 输入域。

## 公开接口

### `add` / `sub` / `mul` / `truediv`

功能说明：

- 定义逐元素二元算术的成本 helper。
- 对应 `tuner.cost(op_name="kernel.add")` 与 `tuner.cost(op_name="kernel.binary_elewise", kernel_kind="add|sub|mul|div|truediv")` 的稳定落点。

参数说明：

- `Space (template MemorySpace)`：输入与输出共享的内存空间模板参数。
- `InType (template type)`：输入元素类型。
- `OutType (template type)`：输出元素类型。
- `Kind (template CostKind)`：成本统计视角。
- `out (const Memory<Space, OutType>&)`：输出视图。
- `lhs (const Memory<Space, InType>&)`：左操作数视图。
- `rhs (const Memory<Space, InType>&)`：右操作数视图。

使用示例：

```cpp
#include "include/npu_demo/npu_demo.h"

using namespace npu_demo;
S_INT cost0 = cost::add<GM, float, float, compute>(out, lhs, rhs);
S_INT cost1 = cost::truediv<TSM, float, float, memory>(out, lhs, rhs);
```

注意事项：

- 参数顺序固定为 `out -> lhs -> rhs`。
- 模板顺序固定为 `Space -> InType -> OutType -> Kind`。
- 不公开 `cost::kernel::add`、`cost<OpTag, ...>` 或旧 `Nn` 成本别名。

返回与限制：

- 返回类型：`S_INT`。
- 限制条件：本轮不定义标量 overload、广播规则或跨空间算术成本 helper。

### `eq` / `ne` / `lt` / `le` / `gt` / `ge`

功能说明：

- 定义逐元素比较的成本 helper。

参数说明：

- `Space (template MemorySpace)`：输入与输出共享的内存空间模板参数。
- `InType (template type)`：输入元素类型。
- `OutType (template type)`：输出元素类型。
- `Kind (template CostKind)`：成本统计视角。
- `out (const Memory<Space, OutType>&)`：输出视图。
- `lhs (const Memory<Space, InType>&)`：左操作数视图。
- `rhs (const Memory<Space, InType>&)`：右操作数视图。

使用示例：

```cpp
using namespace npu_demo;
S_INT cost0 = cost::eq<GM, float, bool, compute>(out, lhs, rhs);
```

注意事项：

- 参数顺序与 [`spec/include/api/Kernel.md`](../../../../spec/include/api/Kernel.md) 保持一致。
- 模板顺序固定为 `Space -> InType -> OutType -> Kind`。

返回与限制：

- 返回类型：`S_INT`。
- 限制条件：本轮不开放额外 predicate 容器类型。

### `exp` / `select` / `reduce_sum` / `reduce_min` / `reduce_max`

功能说明：

- 定义一元、条件选择与当前公开 reduce helper 的成本接口。

参数说明：

- `exp`：模板顺序为 `Space -> InType -> OutType -> Kind`，参数顺序为 `out -> input`。
- `select`：模板顺序为 `Space -> InType -> OutType -> Kind`，参数顺序为 `out -> cond -> lhs -> rhs`。
- `reduce_sum` / `reduce_min` / `reduce_max`：模板顺序为 `Space -> InType -> OutType -> Kind`，参数顺序为 `out -> input -> axis`。

使用示例：

```cpp
using namespace npu_demo;
S_INT exp_cost = cost::exp<TSM, float, float, compute>(out, input);
S_INT reduce_cost = cost::reduce_sum<GM, float, float, memory>(out, input, 1);
S_INT max_cost = cost::reduce_max<GM, float, float, memory>(out, input, 1);
```

注意事项：

- 参数与模板顺序不得脱离对应 `Kernel` helper。

返回与限制：

- 返回类型：`S_INT`。
- 限制条件：本轮不定义 keepdim 或 axis 容器变体。

### `matmul` / `img2col1d` / `img2col2d`

功能说明：

- 定义多空间或多维 Kernel helper 的成本接口。

参数说明：

- `matmul`：模板顺序为 `LhsSpace -> RhsSpace -> OutSpace -> LhsType -> RhsType -> OutType -> Kind`，参数顺序为 `out -> lhs -> rhs`。
- `img2col1d` 与 `img2col2d`：模板与参数顺序跟随对应 `Kernel` helper，再在模板末尾追加 `Kind`。

使用示例：

```cpp
using namespace npu_demo;
S_INT cost0 = cost::matmul<TSM, TSM, TLM1, float, float, float, compute>(out, lhs, rhs);
```

注意事项：

- 多空间 helper 的模板参数顺序不得为了成本接口单独重排。
- `emit_c` 生成源码时，`tuner.cost(op_name="kernel.exp" | "kernel.select" | "kernel.reduce" | "kernel.reduce_min" | "kernel.matmul" | "kernel.img2col1d" | "kernel.img2col2d")` 必须直接落到对应 `cost::*` helper。

返回与限制：

- 返回类型：`S_INT`。
- 限制条件：当前不新增未进入 `Kernel` 公共层的额外 helper。

## 测试

- 测试文件：`test/include/api/test_cost.py`
- 执行命令：`pytest -q test/include/api/test_cost.py`
- 测试目标：通过当前聚合入口 `test_include_api_cost_kernel_signatures_compile` 一次性验证 `Kernel cost` helper 的声明、模板顺序与 `S_INT` 返回合同。

- 测试文件：[`test/dsl/gen_kernel/emit/test_emit.py`](../../../../test/dsl/gen_kernel/emit/test_emit.py)
- 执行命令：`pytest -q test/dsl/gen_kernel/emit/test_emit.py -k "tuner_cost or npu_demo"`
- 测试目标：验证 `tuner.cost(op_name="kernel.add" | "kernel.binary_elewise" | "kernel.exp" | "kernel.select" | "kernel.reduce" | "kernel.matmul" | "kernel.img2col2d")` 的节点级文本发射。

- 测试文件：[`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../test/dsl/gen_kernel/test_gen_kernel.py)
- 执行命令：`pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k "tuner_cost or cost_function or npu_demo"`
- 测试目标：验证完整 cost function 生成后可消费 `cost::add` 与 `cost::matmul`。

- 合同验收资产：
  - `expectation/dsl/emit_c/npu_demo/cost/kernel_binary_add.py`
  - `expectation/dsl/emit_c/npu_demo/cost/kernel_matmul.py`

### 功能与用例清单

| 用例 ID | 场景 | 预期结果 | 对应测试 |
| --- | --- | --- | --- |
| COST-KERNEL-001 | `cost::add` 独立实例化 | 模板顺序为 `Space -> InType -> OutType -> Kind`，返回 `S_INT` | `test_include_api_cost_kernel_signatures_compile` |
| COST-KERNEL-002 | `cost::matmul` 独立实例化 | 模板顺序与 `Kernel.matmul` 一致并在末尾追加 `Kind`，且同一编译入口验证返回 `S_INT` | `test_include_api_cost_kernel_signatures_compile` |
| COST-KERNEL-003 | `emit_c` 节点级发射 `kernel.add` 成本调用 | 生成 `cost::add<...>(out, lhs, rhs)` | `test_emit_c_lowers_npu_demo_tuner_cost_kernel_add` |
| COST-KERNEL-003A | `emit_c` 节点级发射 `kernel.binary_elewise` 成本调用 | 按 `kernel_kind` 生成 `cost::add/sub/mul/truediv/eq/ne/lt/le/gt/ge<...>(out, lhs, rhs)` | `test_emit_c_lowers_npu_demo_tuner_cost_kernel_binary_elewise` |
| COST-KERNEL-003B | `emit_c` 节点级发射 `kernel.exp/select/reduce` 成本调用 | 生成 `cost::exp/select/reduce_*<...>` | `test_emit_c_lowers_npu_demo_tuner_cost_kernel_exp_select_reduce` |
| COST-KERNEL-004 | `gen_kernel` 函数级发射 `kernel.matmul` 成本函数 | 生成 `cost::matmul<...>(out, lhs, rhs)` | `test_gen_kernel_emits_npu_demo_cost_matmul_function` |
| COST-KERNEL-005 | `emit_c` 节点级发射 `kernel.img2col2d` 成本调用 | 生成 `cost::img2col2d<...>(out, input, kh, kw, sh, sw, dh, dw, ph, pw, pl, pr)` | `test_emit_c_lowers_npu_demo_tuner_cost_kernel_img2col2d` |
