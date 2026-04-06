# cpu

## 功能简介

定义 CPU 后端 include/cpu 头文件规范，覆盖 `include/cpu/Memory.h` 与 `include/cpu/Nn.h` 的公开接口、行为与约束。当前基线要求 `cpu::Memory<Space, T>` 使用运行期 `rank`，并以 `MAX_DIM=8` 作为内部固定上限；逐元素/显式 broadcast、`add` 的 scalar overload（`Memory+scalar` / `scalar+Memory`，其中 `memory + const(i32)` 的目标源码保持 CPU 整数实参直传，`memory + symbol.int` 的 CPU 终点整数标量口径固定为 `long long`）、`exp`、`reduce_sum/reduce_min/reduce_max` 与 `img2col1d/img2col2d` CPU 叶子接口语义仍由 CPU include 层实现负责承接。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`金铲铲大作战`
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
- 明确 CPU 后端 `Memory` 视图使用运行期 `rank` 的接口边界，并以 `MAX_DIM=8` 作为固定容量基线。
- 冻结 `cpu::add` 的标量终点口径：上游 `memory + const(i32)` 在 `target=cpu` 下保持 CPU 整数实参直传，`memory + symbol.int` 在 `target=cpu` 下固定映射为 `long long` 标量调用形态。
- 冻结 `cpu::exp(...)` 与 `cpu::reduce_sum/reduce_min/reduce_max(...)` 的稳定 CPU 公开接口，明确参数约束、输出契约与违约路径。
- 冻结 `cpu::img2col1d(...)` 与 `cpu::img2col2d(...)` 的稳定 CPU 公开接口，使 `emit_c/gen_kernel` 在 CPU 侧拥有固定调用目标。

## 限制与边界

- `cpu::Memory<Space, T>` 以运行期 `rank` 描述维度，并在内部以 `MAX_DIM=8` 保存 `shape/stride`；调用方必须满足前置条件 `0 < rank <= 8`，实现不得对 `rank > 8` 做静默截断。
- 公开接口均为纯头文件模板与内联实现，不提供动态分配、异常或运行时边界检查。
- 逐元素与比较算子要求输入与输出形状一致，广播仅支持显式 `broadcast`，不提供隐式广播；仅 `cpu::add` 允许 `Memory+scalar` / `scalar+Memory` 两个公开 overload。
- `img2col1d/img2col2d` 只定义 CPU include 层叶子接口，不反向规定 AST 节点类型、`nn dialect` 运行时类型、`build_func_op(...)` 结构或 pass 名称。
- `exp/reduce_*` 只定义 CPU include 层叶子接口，不反向规定 AST 节点类型、`nn dialect` 运行时类型、`build_func_op(...)` 结构或 pass 名称。
- `exp/reduce_*` 当前公开口径固定为 `float` 入参与出参，不在 include 层提供自动类型提升或隐式 cast。
- `cpu::add` 的整数标量终点只冻结 `memory + const(i32)` 与 `memory + !symbol.int<"...">` 的 CPU 公开调用口径：前者保持整数实参直传，后者固定为 `long long`；本轮不定义 `f16/f32` mixed scalar 等其他混合标量提升规则，也不扩展到左标量整数形态。
- `reduce_*` 的 `axes` 由调用方提供规范化后的非空轴列表（去重、非负、升序）；`axis=None` 语义由上游在进入 include 层前显式展开。
- 禁止新增笼统 `cpu::img2col(...)` 公开名；CPU include 层只公开 `cpu::img2col1d(...)` 与 `cpu::img2col2d(...)`。
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

### `cpu::Memory<Space, T>`

功能说明：

- 表示运行期 `rank` 的多维内存视图，记录 `data/shape/stride/rank/format/space` 元信息。

参数说明：

- `Space`：内存空间模板参数。
- `T`：元素类型。
- `rank`：运行期维度数，必须大于 `0` 且不超过 `MAX_DIM=8`。

使用示例：

```cpp
#include "include/cpu/Memory.h"

int data[6] = {0, 1, 2, 3, 4, 5};
long long shape[2] = {2, 3};
long long stride[2] = {3, 1};

cpu::Memory<cpu::GM, int> mem(data, 2, shape, stride, cpu::MemoryFormat::Norm);
```

注意事项：

- `shape`/`stride` 由调用方提供，类内部按 `rank` 拷贝数组值。
- `data` 必须指向有效连续内存，接口不检查空指针或越界访问。
- 内部固定容量基线为 `MAX_DIM=8`，调用方需保证 `rank` 不超过该上限；超界属于契约违背，允许实现触发显式失败。
- 公开构造口径仅接受显式 `rank` 参数，不再以定长数组模板参数作为主接口。

返回与限制：

- 返回类型：`cpu::Memory<Space, T>`。
- 返回语义：构造并记录内存视图元信息。
- 限制条件：`rank == 0` 或 `rank > MAX_DIM` 不在支持范围内；实现可通过显式断言/契约式检查终止，不能静默截断；非法指针或维度值属于未定义行为。

#### `Memory(data, rank, shape, stride, format)`

功能说明：

- 使用显式 `shape` 与 `stride` 构造视图。

参数说明：

- `data (T*)`：底层数据指针。
- `rank (unsigned long long)`：运行期维度数。
- `shape (const long long*)`：长度至少为 `rank` 的维度数组。
- `stride (const long long*)`：长度至少为 `rank` 的步幅数组。
- `format (cpu::MemoryFormat)`：布局格式，默认 `Norm`。

使用示例：

```cpp
cpu::Memory<cpu::SM, int> mem(data, 2, shape, stride, cpu::MemoryFormat::CLast);
```

注意事项：

- 不进行 `shape/stride` 的合法性检查。
- `rank` 必须满足 `0 < rank <= MAX_DIM`；超界时允许实现直接触发契约失败。

返回与限制：

- 返回类型：`cpu::Memory<Space, T>`。
- 返回语义：构造并保存显式步幅。
- 限制条件：调用方需保证 `rank/shape/stride` 合法。

#### `Memory(data, rank, shape, format)`

功能说明：

- 使用 `shape` 构造连续行主序视图，并自动推导 `stride`。

参数说明：

- `data (T*)`：底层数据指针。
- `rank (unsigned long long)`：运行期维度数。
- `shape (const long long*)`：长度至少为 `rank` 的维度数组。
- `format (cpu::MemoryFormat)`：布局格式，默认 `Norm`。

使用示例：

```cpp
cpu::Memory<cpu::GM, float> mem(data, 2, shape);
```

注意事项：

- `stride` 按连续行主序推导，未提供覆盖入口。
- `rank` 必须满足 `0 < rank <= MAX_DIM`；超界时允许实现直接触发契约失败。

返回与限制：

- 返回类型：`cpu::Memory<Space, T>`。
- 返回语义：构造并填充连续步幅。
- 限制条件：调用方需保证 `rank/shape` 合法。

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

- 返回运行期维度数。

参数说明：

- 无参数。

使用示例：

```cpp
unsigned long long rank = mem.rank();
```

注意事项：

- `rank()` 返回构造时保存的运行期维度数。

返回与限制：

- 返回类型：`unsigned long long`。
- 返回语义：返回运行期 `rank`。
- 限制条件：构造后不提供修改入口。

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

- `indices (const long long*)`：长度至少为 `rank()` 的索引数组。

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

- `indices (const long long*)`：长度至少为 `rank()` 的索引数组。

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

- 对两个 `cpu::Memory<Space, T>` 视图执行逐元素加法。

参数说明：

- `lhs (const cpu::Memory<Space, T>&)`：左操作数视图。
- `rhs (const cpu::Memory<Space, T>&)`：右操作数视图。
- `out (cpu::Memory<Space, T>&)`：输出视图。

使用示例：

```cpp
cpu::add(lhs, rhs, out);
```

注意事项：

- `lhs/rhs/out` 的运行期 `rank`、`shape` 与 `stride` 需保持一致。
- 接口不检查形状合法性。

返回与限制：

- 返回类型：`void`。
- 返回语义：结果写入 `out`。
- 限制条件：输入不满足约束时行为未定义。

### `cpu::add(lhs, rhs_scalar, out)`

功能说明：

- 对 `cpu::Memory<Space, T>` 与标量执行逐元素加法（`Memory+scalar` overload）。

参数说明：

- `lhs (const cpu::Memory<Space, T>&)`：左操作数视图。
- `rhs_scalar (T 或 long long)`：右操作数标量；其中 `memory + const(i32)` 在 `target=cpu` 下保持整数实参直传，`memory + symbol.int` 的稳定公开形态为 `long long`。
- `out (cpu::Memory<Space, T>&)`：输出视图。

使用示例：

```cpp
// Memory + scalar：对 lhs 每个元素加上同一个标量值。
cpu::add(lhs, 3.0f, out);

// memory + const(i32)：常量直接作为 CPU 整数实参出现。
cpu::add(lhs, 1, out);

// memory + symbol.int：CPU 终点公开形态为 long long 命名标量。
long long bias = 7;
cpu::add(lhs, bias, out);
```

注意事项：

- 公开 overload 契约为 `Memory+scalar`，不等价于隐式 broadcast API。
- `lhs/out` 的运行期 `rank`、`shape` 与 `stride` 需保持一致。
- `out` 的 `space/format` 应与 `lhs` 一致；接口不做运行时检查。
- `rhs_scalar` 仅表示单个标量值，不携带独立 `shape/stride/space` 语义。
- 对 `emit_c/gen_kernel` 的稳定 CPU 调用目标，`memory + const(i32)` 必须收敛为 `cpu::add(lhs, 1, out)` 这一类“常量直接作为 CPU 整数实参”的形态，不把 `LL` 后缀写成强制源码口径。
- 对 `emit_c/gen_kernel` 的稳定 CPU 调用目标，`memory + symbol.int` 必须收敛为 `long long bias = ...; cpu::add(lhs, bias, out)`。
- `long long` 标量口径只用于冻结 `memory + symbol.int` 的整数标量终点；本节不定义 `f16/f32` mixed scalar 等其他混合标量调用形态。

返回与限制：

- 返回类型：`void`。
- 返回语义：结果写入 `out`，元素语义为 `out[i] = lhs[i] + rhs_scalar`；当 `rhs_scalar` 来自 `const(i32)` 时保持整数实参直传，当来自 `symbol.int` 时公开 CPU 端调用口径固定为 `long long`。
- 限制条件：输入不满足约束时行为未定义。

### `cpu::add(lhs_scalar, rhs, out)`

功能说明：

- 对标量 `T` 与 `cpu::Memory<Space, T>` 执行逐元素加法（`scalar+Memory` overload）。

参数说明：

- `lhs_scalar (T)`：左操作数标量。
- `rhs (const cpu::Memory<Space, T>&)`：右操作数视图。
- `out (cpu::Memory<Space, T>&)`：输出视图。

使用示例：

```cpp
// scalar + Memory：对 rhs 每个元素加上同一个标量值。
cpu::add(3.0f, rhs, out);
```

注意事项：

- 公开 overload 契约为 `scalar+Memory`，不等价于隐式 broadcast API。
- `rhs/out` 的运行期 `rank`、`shape` 与 `stride` 需保持一致。
- `out` 的 `space/format` 应与 `rhs` 一致；接口不做运行时检查。
- `lhs_scalar` 仅表示单个标量值，不携带独立 `shape/stride/space` 语义。

返回与限制：

- 返回类型：`void`。
- 返回语义：结果写入 `out`，元素语义为 `out[i] = lhs_scalar + rhs[i]`。
- 限制条件：输入不满足约束时行为未定义。

### `cpu::sub(lhs, rhs, out)`

功能说明：

- 对两个 `cpu::Memory<Space, T>` 视图执行逐元素减法。

参数说明：

- `lhs (const cpu::Memory<Space, T>&)`：左操作数视图。
- `rhs (const cpu::Memory<Space, T>&)`：右操作数视图。
- `out (cpu::Memory<Space, T>&)`：输出视图。

使用示例：

```cpp
cpu::sub(lhs, rhs, out);
```

注意事项：

- `lhs/rhs/out` 的运行期 `rank` 与 `shape` 必须一致。

返回与限制：

- 返回类型：`void`。
- 返回语义：结果写入 `out`。
- 限制条件：不检查形状或类型约束。

### `cpu::mul(lhs, rhs, out)`

功能说明：

- 对两个 `cpu::Memory<Space, T>` 视图执行逐元素乘法。

参数说明：

- `lhs (const cpu::Memory<Space, T>&)`：左操作数视图。
- `rhs (const cpu::Memory<Space, T>&)`：右操作数视图。
- `out (cpu::Memory<Space, T>&)`：输出视图。

使用示例：

```cpp
cpu::mul(lhs, rhs, out);
```

注意事项：

- `lhs/rhs/out` 的运行期 `rank` 与 `shape` 必须一致。

返回与限制：

- 返回类型：`void`。
- 返回语义：结果写入 `out`。
- 限制条件：不检查形状或类型约束。

### `cpu::truediv(lhs, rhs, out)`

功能说明：

- 对两个 `cpu::Memory<Space, T>` 视图执行逐元素真除法。

参数说明：

- `lhs (const cpu::Memory<Space, T>&)`：左操作数视图。
- `rhs (const cpu::Memory<Space, T>&)`：右操作数视图。
- `out (cpu::Memory<Space, T>&)`：输出视图。

使用示例：

```cpp
cpu::truediv(lhs, rhs, out);
```

注意事项：

- `lhs/rhs/out` 的运行期 `rank` 与 `shape` 必须一致。

返回与限制：

- 返回类型：`void`。
- 返回语义：结果写入 `out`。
- 限制条件：不检查除零或形状约束。

### `cpu::exp(value, out)`

功能说明：

- 对输入 `cpu::Memory<Space, float>` 视图执行逐元素指数运算，并把结果写入输出视图。

参数说明：

- `value (const cpu::Memory<Space, float>&)`：输入视图。
- `out (cpu::Memory<Space, float>&)`：输出视图。

使用示例：

```cpp
float in_data[4] = {0.0f, 1.0f, -1.0f, 2.0f};
float out_data[4] = {0.0f, 0.0f, 0.0f, 0.0f};
long long shape[2] = {2, 2};
long long stride[2] = {2, 1};

cpu::Memory<cpu::GM, float> value(in_data, 2, shape, stride);
cpu::Memory<cpu::GM, float> out(out_data, 2, shape, stride);
cpu::exp(value, out);
```

注意事项：

- 公开签名固定为：`void cpu::exp(const cpu::Memory<Space, float>& value, cpu::Memory<Space, float>& out)`。
- `value.rank()` 与 `out.rank()` 必须一致，`value.shape()/stride()` 与 `out.shape()/stride()` 必须逐维一致。
- 不提供隐式广播、自动类型提升或 `float` 之外的公开重载。
- 若调用方违反任一前置条件，应视为契约不满足：`value-out-rank-mismatch`、`value-out-shape-mismatch`、`value-out-stride-mismatch`。

返回与限制：

- 返回类型：`void`。
- 返回语义：结果写入 `out`。
- 限制条件：接口不提供异常与状态码，违约路径由契约失败处理。

### `cpu::reduce_sum(value, out, axes, axes_rank, keepdim)`

功能说明：

- 对输入 `cpu::Memory<Space, float>` 按给定轴集合执行求和归约，并把结果写入输出视图。

参数说明：

- `value (const cpu::Memory<Space, float>&)`：输入视图。
- `out (cpu::Memory<Space, float>&)`：输出视图。
- `axes (const long long*)`：归约轴数组首地址。
- `axes_rank (unsigned long long)`：`axes` 长度，必须大于 `0`。
- `keepdim (bool)`：是否保留归约轴。

使用示例：

```cpp
float in_data[24] = {0.0f};
float out_data[2] = {0.0f, 0.0f};
long long in_shape[3] = {2, 3, 4};
long long in_stride[3] = {12, 4, 1};
long long out_shape[1] = {2};
long long out_stride[1] = {1};
long long axes[2] = {1, 2};

cpu::Memory<cpu::GM, float> value(in_data, 3, in_shape, in_stride);
cpu::Memory<cpu::GM, float> out(out_data, 1, out_shape, out_stride);
cpu::reduce_sum(value, out, axes, 2, false);
```

注意事项：

- 公开签名固定为：
  `void cpu::reduce_sum(const cpu::Memory<Space, float>& value, cpu::Memory<Space, float>& out, const long long* axes, unsigned long long axes_rank, bool keepdim)`。
- `axes_rank > 0`，`axes` 必须非空，且每个轴满足 `0 <= axis < value.rank()`。
- `axes` 必须由调用方预先规范化（去重、非负、升序）；include 层不负责 `axis=None` 语义解析。
- `keepdim=true` 时，`out.rank() == value.rank()` 且归约轴维度必须为 `1`。
- `keepdim=false` 时，`out.rank() == value.rank() - axes_rank`；若归约后 rank 为 `0`，`out` 必须按 rank-1 形状 `[1]` 表达标量结果。
- `out.stride()` 必须与 `out.shape()` 对应的连续行主序一致。
- 若调用方违反任一前置条件，应视为契约不满足：`axes-empty-or-null`、`axes-not-normalized-or-out-of-range`、`out-shape-stride-mismatch-with-reduce-contract`。

返回与限制：

- 返回类型：`void`。
- 返回语义：结果写入 `out`。
- 限制条件：接口不提供异常与状态码，违约路径由契约失败处理。

### `cpu::reduce_min(value, out, axes, axes_rank, keepdim)`

功能说明：

- 对输入 `cpu::Memory<Space, float>` 按给定轴集合执行最小值归约，并把结果写入输出视图。

参数说明：

- 同 `cpu::reduce_sum`。

使用示例：

```cpp
float in_data[24] = {0.0f};
float out_data[6] = {0.0f};
long long in_shape[3] = {2, 3, 4};
long long in_stride[3] = {12, 4, 1};
long long out_shape[2] = {2, 3};
long long out_stride[2] = {3, 1};
long long axes[1] = {2};

cpu::Memory<cpu::GM, float> value(in_data, 3, in_shape, in_stride);
cpu::Memory<cpu::GM, float> out(out_data, 2, out_shape, out_stride);
cpu::reduce_min(value, out, axes, 1, false);
```

注意事项：

- 公开签名固定为：
  `void cpu::reduce_min(const cpu::Memory<Space, float>& value, cpu::Memory<Space, float>& out, const long long* axes, unsigned long long axes_rank, bool keepdim)`。
- `axes/keepdim/out.shape/out.stride` 合同与 `cpu::reduce_sum` 一致。
- 静态可判定时，任一归约轴维度为 `0` 应视为契约不满足：`empty-reduction-extent`。

返回与限制：

- 返回类型：`void`。
- 返回语义：结果写入 `out`。
- 限制条件：接口不提供异常与状态码，违约路径由契约失败处理。

### `cpu::reduce_max(value, out, axes, axes_rank, keepdim)`

功能说明：

- 对输入 `cpu::Memory<Space, float>` 按给定轴集合执行最大值归约，并把结果写入输出视图。

参数说明：

- 同 `cpu::reduce_sum`。

使用示例：

```cpp
float in_data[24] = {0.0f};
float out_data[12] = {0.0f};
long long in_shape[3] = {2, 3, 4};
long long in_stride[3] = {12, 4, 1};
long long out_shape[3] = {1, 3, 4};
long long out_stride[3] = {12, 4, 1};
long long axes[1] = {0};

cpu::Memory<cpu::GM, float> value(in_data, 3, in_shape, in_stride);
cpu::Memory<cpu::GM, float> out(out_data, 3, out_shape, out_stride);
cpu::reduce_max(value, out, axes, 1, true);
```

注意事项：

- 公开签名固定为：
  `void cpu::reduce_max(const cpu::Memory<Space, float>& value, cpu::Memory<Space, float>& out, const long long* axes, unsigned long long axes_rank, bool keepdim)`。
- `axes/keepdim/out.shape/out.stride` 合同与 `cpu::reduce_sum` 一致。
- 静态可判定时，任一归约轴维度为 `0` 应视为契约不满足：`empty-reduction-extent`。

返回与限制：

- 返回类型：`void`。
- 返回语义：结果写入 `out`。
- 限制条件：接口不提供异常与状态码，违约路径由契约失败处理。

### `cpu::eq(lhs, rhs, out)`

功能说明：

- 对两个 `cpu::Memory<Space, T>` 视图执行逐元素相等比较。

参数说明：

- `lhs (const cpu::Memory<Space, T>&)`：左操作数视图。
- `rhs (const cpu::Memory<Space, T>&)`：右操作数视图。
- `out (cpu::Memory<Space, PredT>&)`：输出视图，元素类型用于表示 predicate。

使用示例：

```cpp
cpu::eq(lhs, rhs, out);
```

注意事项：

- `lhs/rhs/out` 的运行期 `rank` 与 `shape` 必须一致。
- `out` 元素类型需能表示比较结果。

返回与限制：

- 返回类型：`void`。
- 返回语义：结果写入 `out`。
- 限制条件：不检查类型或形状约束。

### `cpu::ne(lhs, rhs, out)`

功能说明：

- 对两个 `cpu::Memory<Space, T>` 视图执行逐元素不等比较。

参数说明：

- `lhs (const cpu::Memory<Space, T>&)`：左操作数视图。
- `rhs (const cpu::Memory<Space, T>&)`：右操作数视图。
- `out (cpu::Memory<Space, PredT>&)`：输出视图。

使用示例：

```cpp
cpu::ne(lhs, rhs, out);
```

注意事项：

- `lhs/rhs/out` 的运行期 `rank` 与 `shape` 必须一致。

返回与限制：

- 返回类型：`void`。
- 返回语义：结果写入 `out`。
- 限制条件：不检查类型或形状约束。

### `cpu::lt(lhs, rhs, out)`

功能说明：

- 对两个 `cpu::Memory<Space, T>` 视图执行逐元素小于比较。

参数说明：

- `lhs (const cpu::Memory<Space, T>&)`：左操作数视图。
- `rhs (const cpu::Memory<Space, T>&)`：右操作数视图。
- `out (cpu::Memory<Space, PredT>&)`：输出视图。

使用示例：

```cpp
cpu::lt(lhs, rhs, out);
```

注意事项：

- `lhs/rhs/out` 的运行期 `rank` 与 `shape` 必须一致。

返回与限制：

- 返回类型：`void`。
- 返回语义：结果写入 `out`。
- 限制条件：不检查类型或形状约束。

### `cpu::le(lhs, rhs, out)`

功能说明：

- 对两个 `cpu::Memory<Space, T>` 视图执行逐元素小于等于比较。

参数说明：

- `lhs (const cpu::Memory<Space, T>&)`：左操作数视图。
- `rhs (const cpu::Memory<Space, T>&)`：右操作数视图。
- `out (cpu::Memory<Space, PredT>&)`：输出视图。

使用示例：

```cpp
cpu::le(lhs, rhs, out);
```

注意事项：

- `lhs/rhs/out` 的运行期 `rank` 与 `shape` 必须一致。

返回与限制：

- 返回类型：`void`。
- 返回语义：结果写入 `out`。
- 限制条件：不检查类型或形状约束。

### `cpu::gt(lhs, rhs, out)`

功能说明：

- 对两个 `cpu::Memory<Space, T>` 视图执行逐元素大于比较。

参数说明：

- `lhs (const cpu::Memory<Space, T>&)`：左操作数视图。
- `rhs (const cpu::Memory<Space, T>&)`：右操作数视图。
- `out (cpu::Memory<Space, PredT>&)`：输出视图。

使用示例：

```cpp
cpu::gt(lhs, rhs, out);
```

注意事项：

- `lhs/rhs/out` 的运行期 `rank` 与 `shape` 必须一致。

返回与限制：

- 返回类型：`void`。
- 返回语义：结果写入 `out`。
- 限制条件：不检查类型或形状约束。

### `cpu::ge(lhs, rhs, out)`

功能说明：

- 对两个 `cpu::Memory<Space, T>` 视图执行逐元素大于等于比较。

参数说明：

- `lhs (const cpu::Memory<Space, T>&)`：左操作数视图。
- `rhs (const cpu::Memory<Space, T>&)`：右操作数视图。
- `out (cpu::Memory<Space, PredT>&)`：输出视图。

使用示例：

```cpp
cpu::ge(lhs, rhs, out);
```

注意事项：

- `lhs/rhs/out` 的运行期 `rank` 与 `shape` 必须一致。

返回与限制：

- 返回类型：`void`。
- 返回语义：结果写入 `out`。
- 限制条件：不检查类型或形状约束。

### `cpu::broadcast(input, out)`

功能说明：

- 显式广播输入视图到输出形状。

参数说明：

- `input (const cpu::Memory<Space, T>&)`：输入视图。
- `out (cpu::Memory<Space, T>&)`：输出视图。

使用示例：

```cpp
cpu::broadcast(input, out);
```

注意事项：

- `out.rank() >= input.rank()`，并以运行期 `rank` 对齐尾部维度。
- 广播按尾维对齐，逐维满足 `input_dim == output_dim` 或 `input_dim == 1`。
- 接口不检查广播条件，调用方需保证合法。

返回与限制：

- 返回类型：`void`。
- 返回语义：结果写入 `out`。
- 限制条件：广播条件不满足时行为未定义。

### `cpu::img2col1d(value, out, kw, sw, dw, pl, pr)`

功能说明：

- 将 rank-3 输入视图 `value[N, C, W]` 按 1D `img2col` 规则展开到 rank-3 输出视图 `out[N, C*Kw, Wo]`。
- 该接口是 CPU emitter 的稳定叶子调用目标，只依赖 `cpu::Memory<Space, T>` 与普通整型标量参数。

参数说明：

- `value (const cpu::Memory<Space, T>&)`：输入视图，运行期 `rank` 必须为 `3`。
- `out (cpu::Memory<Space, T>&)`：输出视图，运行期 `rank` 必须为 `3`，并由调用方预先分配。
- `kw (long long)`：kernel width，必须为正整数。
- `sw (long long)`：stride width，必须为正整数。
- `dw (long long)`：dilation width，必须为正整数。
- `pl (long long)`：左侧 padding，必须为非负整数。
- `pr (long long)`：右侧 padding，必须为非负整数。

使用示例：

```cpp
cpu::img2col1d(value_1d, out_1d, 3, 1, 1, 1, 1);
```

注意事项：

- 该接口的公开签名固定为：
  `void cpu::img2col1d(const cpu::Memory<Space, float>& value, cpu::Memory<Space, float>& out, long long kw, long long sw, long long dw, long long pl, long long pr)`。
- `value` 必须解释为 `shape=[N, C, W]`；`out` 必须解释为 `shape=[N, C * kw, Wo]`，其中
  `Wo = (W + pl + pr - dw * (kw - 1) - 1) / sw + 1`，按整除下取整口径理解。
- `shape-formula-check` 的含义是：调用方必须保证 `out.shape()` 与上式完全一致。
- `stride-consistency-check` 的含义是：调用方必须保证 `value` 的 `shape/stride` 与其运行期 `rank` 自洽，且 `out` 采用与 `[N, C * kw, Wo]` 一致的密集行主序布局，等价 stride 为 `[(C * kw) * Wo, Wo, 1]`。
- 本接口只依赖 `cpu::Memory<Space, T>`、`long long`、rank 检查、shape 公式检查与 stride 一致性检查；不得依赖 AST 节点类型、`nn dialect` 运行时类型、`build_func_op(...)` 结构或 pass 名称。
- 若调用方违反以下任一前置条件，应视为契约不满足：`value-rank-not-3`、`out-rank-not-3`、`shape-stride-mismatch-with-img2col1d-formula`、`kw-sw-dw-not-positive`、`pl-pr-negative`。
- 禁止继续新增或暴露笼统 `cpu::img2col(...)` 公开接口名。

返回与限制：

- 返回类型：`void`。
- 返回语义：按 `img2col1d` 规则把 `value` 展开写入 `out`。
- 限制条件：接口不提供异常、状态码或运行时分派；契约校验失败属于调用方违约。

### `cpu::img2col2d(value, out, kh, kw, sh, sw, dh, dw, ph, pw, pl, pr)`

功能说明：

- 将 rank-4 输入视图 `value[N, C, H, W]` 按 2D `img2col` 规则展开到 rank-3 输出视图 `out[N, C*Kh*Kw, Ho*Wo]`。
- 该接口是 CPU emitter 的稳定叶子调用目标，只依赖 `cpu::Memory<Space, T>` 与普通整型标量参数。

参数说明：

- 除 `value/out` 外，固定签名必须包含且仅包含 10 个 `long long` 标量参数：`kh/kw/sh/sw/dh/dw/ph/pw/pl/pr`。
- `value (const cpu::Memory<Space, T>&)`：输入视图，运行期 `rank` 必须为 `4`。
- `out (cpu::Memory<Space, T>&)`：输出视图，运行期 `rank` 必须为 `3`，并由调用方预先分配。
- `kh (long long)`：kernel height，必须为正整数。
- `kw (long long)`：kernel width，必须为正整数。
- `sh (long long)`：stride height，必须为正整数。
- `sw (long long)`：stride width，必须为正整数。
- `dh (long long)`：dilation height，必须为正整数。
- `dw (long long)`：dilation width，必须为正整数。
- `ph (long long)`：上侧 padding，必须为非负整数。
- `pw (long long)`：下侧 padding，必须为非负整数。
- `pl (long long)`：左侧 padding，必须为非负整数。
- `pr (long long)`：右侧 padding，必须为非负整数。

使用示例：

```cpp
cpu::img2col2d(value_2d, out_2d, 3, 3, 1, 1, 1, 1, 1, 1, 1, 1);
// 固定签名口径：value/out + 10 个 long long 标量参数。
```

注意事项：

- 该接口的公开签名固定为：
  `void cpu::img2col2d(const cpu::Memory<Space, float>& value, cpu::Memory<Space, float>& out, long long kh, long long kw, long long sh, long long sw, long long dh, long long dw, long long ph, long long pw, long long pl, long long pr)`。
- 调用示例必须与固定签名保持一致：`value/out` 之后只允许 10 个标量参数，不能扩展为其他参数个数。
- `value` 必须解释为 `shape=[N, C, H, W]`；`out` 必须解释为 `shape=[N, C * kh * kw, Ho * Wo]`，其中
  `Ho = (H + ph + pw - dh * (kh - 1) - 1) / sh + 1`，
  `Wo = (W + pl + pr - dw * (kw - 1) - 1) / sw + 1`，
  按整除下取整口径理解。
- `shape-formula-check` 的含义是：调用方必须保证 `out.shape()` 与上述二维公式完全一致。
- `stride-consistency-check` 的含义是：调用方必须保证 `value` 的 `shape/stride` 与其运行期 `rank` 自洽，且 `out` 采用与 `[N, C * kh * kw, Ho * Wo]` 一致的密集行主序布局，等价 stride 为 `[(C * kh * kw) * (Ho * Wo), Ho * Wo, 1]`。
- 本接口只依赖 `cpu::Memory<Space, T>`、`long long`、rank 检查、shape 公式检查与 stride 一致性检查；不得依赖 AST 节点类型、`nn dialect` 运行时类型、`build_func_op(...)` 结构或 pass 名称。
- 若调用方违反以下任一前置条件，应视为契约不满足：`value-rank-not-4`、`out-rank-not-3`、`shape-stride-mismatch-with-img2col2d-formula`、`kh-kw-sh-sw-dh-dw-not-positive`、`ph-pw-pl-pr-negative`。
- 禁止继续新增或暴露笼统 `cpu::img2col(...)` 公开接口名。

返回与限制：

- 返回类型：`void`。
- 返回语义：按 `img2col2d` 规则把 `value` 展开写入 `out`。
- 限制条件：接口不提供异常、状态码或运行时分派；契约校验失败属于调用方违约。

## 额外补充

### `img2col1d/img2col2d` CPU API 契约

目标：

- 在 `spec/include/cpu/cpu.md` 冻结 `cpu::img2col1d(...)` 与 `cpu::img2col2d(...)` 的公开接口与最小行为契约，作为 `emit_c/gen_kernel` 的稳定 CPU 调用目标。

边界：

- 本文只定义 CPU include 层的公开接口；不定义 DSL lowering、`nn dialect` 结构、`build_func_op(...)` 结构、pass 名称或完整 conv 模板。
- 本文只修改 `spec/include/cpu/cpu.md` 所覆盖的公开契约，不反向规定上游 AST/IR 该如何组织。

注意事项：

- CPU runtime 只依赖 `cpu::Memory<Space, T>`、普通标量参数和本层运行时契约，不依赖 AST 节点类型、`nn dialect` 运行时类型、`build_func_op(...)` 结构或 pass 名称。
- `cpu::img2col1d(...)` 与 `cpu::img2col2d(...)` 是稳定公开名；不得继续新增 `cpu::img2col(...)` 笼统接口。
- 下文中的 `describe_cpu_api_contract(...)` 仅是验收辅助伪名，不是产品接口，不能在 `include/cpu` 中实现为公开 API。

依赖：

- 无硬依赖；允许与上游 `img2col` 公开名相关规格并行推进。
- 验收口径必须与固定公开名 `img2col1d/img2col2d` 保持一致，并以上游高层公开语义冻结文本为命名与公式基准。

验证命令：

- 无；由管理者人工核对文档。

验收标准：

- 本文必须能直接支撑下面这个验收辅助函数的 `expected` 结构；若文档无法推出同样的契约，则该规格不通过。

```python
def test_cpu_img2col_api_contract_v1():
    actual = describe_cpu_api_contract(
        names=["cpu::img2col1d", "cpu::img2col2d"],
        template_type="float",
    )
    expected = {
        "apis": {
            "cpu::img2col1d": {
                "signature": "void cpu::img2col1d(const cpu::Memory<Space, float>& value, cpu::Memory<Space, float>& out, long long kw, long long sw, long long dw, long long pl, long long pr)",
                "depends_only_on": [
                    "cpu::Memory<Space, T>",
                    "long long",
                    "rank-check",
                    "shape-formula-check",
                    "stride-consistency-check",
                ],
                "value_rank": 3,
                "out_rank": 3,
                "rejects": [
                    "value-rank-not-3",
                    "out-rank-not-3",
                    "shape-stride-mismatch-with-img2col1d-formula",
                    "kw-sw-dw-not-positive",
                    "pl-pr-negative",
                ],
            },
            "cpu::img2col2d": {
                "signature": "void cpu::img2col2d(const cpu::Memory<Space, float>& value, cpu::Memory<Space, float>& out, long long kh, long long kw, long long sh, long long sw, long long dh, long long dw, long long ph, long long pw, long long pl, long long pr)",
                "depends_only_on": [
                    "cpu::Memory<Space, T>",
                    "long long",
                    "rank-check",
                    "shape-formula-check",
                    "stride-consistency-check",
                ],
                "value_rank": 4,
                "out_rank": 3,
                "rejects": [
                    "value-rank-not-4",
                    "out-rank-not-3",
                    "shape-stride-mismatch-with-img2col2d-formula",
                    "kh-kw-sh-sw-dh-dw-not-positive",
                    "ph-pw-pl-pr-negative",
                ],
            },
        },
        "forbidden_dependencies": [
            "ast-node-types",
            "nn-dialect-runtime-types",
            "build_func_op-structure",
            "pass-names",
        ],
        "forbidden_public_names": ["cpu::img2col"],
    }
```

## 测试

- 测试文件：
  - `test/include/cpu/test_memory.py`
  - `test/include/cpu/test_nn.py`
- 执行命令：`pytest -q test/include/cpu/test_memory.py test/include/cpu/test_nn.py`
- 测试说明：`test/include/cpu/test_memory.py` 与 `test/include/cpu/test_nn.py` 均统一引用本 spec `spec/include/cpu/cpu.md`，不再拆分为独立 `Memory.md` / `Nn.md`。
- 测试说明：`INC-NN-019` ~ `INC-NN-026` 已在 `test/include/cpu/test_nn.py` 落地，用于覆盖 `exp/reduce_*` 成功路径与契约失败路径。
- 测试说明：`INC-NN-027` ~ `INC-NN-028` 已在 `test/include/cpu/test_nn.py` 落地，用于覆盖 `cpu::add` 的 `Memory+scalar` / `scalar+Memory` overload。
- 测试目标：
  - CPU-MEM-001：显式 stride 构造与访问。
  - CPU-MEM-002：连续 stride 自动推导。
  - CPU-MEM-003：`element_count/linear_offset` 语义。
  - CPU-MEM-004：`at/is_contiguous` 语义。
  - CPU-MEM-005：头文件不依赖标准库即可编译。
  - CPU-MEM-006：`MAX_DIM=8` 下运行期 `rank` 构造与索引访问。
  - CPU-MEM-007：`rank > MAX_DIM` 违反前置条件时显式失败。
  - INC-NN-001：逐元素加法输出。
  - INC-NN-002：逐元素比较输出 predicate。
  - INC-NN-003：broadcast 单例扩张。
  - INC-NN-004：broadcast 前置维插入。
  - INC-NN-005：逐元素乘法输出。
  - INC-NN-006：逐元素减法输出。
  - INC-NN-007：逐元素除法输出。
  - INC-NN-008：逐元素不等比较输出。
  - INC-NN-009：逐元素小于比较输出。
  - INC-NN-010：逐元素小于等于比较输出。
  - INC-NN-011：逐元素大于比较输出。
  - INC-NN-012：逐元素大于等于比较输出。
  - INC-NN-013：`img2col1d` 基础展开与固定签名校验。
  - INC-NN-014：`img2col2d` 基础展开与固定签名校验。
  - INC-NN-015：`img2col1d` 契约违约触发失败。
  - INC-NN-016：`img2col2d` 契约违约触发失败。
  - INC-NN-017：`img2col1d` 非连续 stride 违约触发失败。
  - INC-NN-018：禁止笼统 `cpu::img2col` 公开名。
  - INC-NN-019：`exp` 逐元素计算成功路径与元信息一致性。
  - INC-NN-020：`exp` rank/shape/stride 违约路径。
  - INC-NN-021：`reduce_sum` 轴集合与 `keepdim` 契约成功路径。
  - INC-NN-022：`reduce_sum` 轴集合非法输入拒绝路径。
  - INC-NN-023：`reduce_min` 归约成功路径与输出契约。
  - INC-NN-024：`reduce_min` 空归约域拒绝路径。
  - INC-NN-025：`reduce_max` 归约成功路径与输出契约。
  - INC-NN-026：`reduce_max` 空归约域拒绝路径。
  - INC-NN-027：`add` 的 `Memory+scalar` overload。
  - INC-NN-028：`add` 的 `scalar+Memory` overload。
- 功能与用例清单：
  - CPU-MEM-001 -> `test/include/cpu/test_memory.py::test_cpu_memory_header_compiles_and_runs`
  - CPU-MEM-002 -> `test/include/cpu/test_memory.py::test_cpu_memory_header_compiles_and_runs`
  - CPU-MEM-003 -> `test/include/cpu/test_memory.py::test_cpu_memory_header_compiles_and_runs`
  - CPU-MEM-004 -> `test/include/cpu/test_memory.py::test_cpu_memory_header_compiles_and_runs`
  - CPU-MEM-005 -> `test/include/cpu/test_memory.py::test_cpu_memory_header_without_std_headers`
  - CPU-MEM-006 -> `test/include/cpu/test_memory.py::test_cpu_memory_runtime_rank_max_dim`
  - CPU-MEM-007 -> `test/include/cpu/test_memory.py::test_cpu_memory_runtime_rank_over_max_dim_fails`
  - INC-NN-001 -> `test/include/cpu/test_nn.py::test_cpu_nn_add_success`
  - INC-NN-002 -> `test/include/cpu/test_nn.py::test_cpu_nn_compare_eq`
  - INC-NN-003 -> `test/include/cpu/test_nn.py::test_cpu_nn_broadcast_success`
  - INC-NN-004 -> `test/include/cpu/test_nn.py::test_cpu_nn_broadcast_prepend_dim`
  - INC-NN-005 -> `test/include/cpu/test_nn.py::test_cpu_nn_mul_success`
  - INC-NN-006 -> `test/include/cpu/test_nn.py::test_cpu_nn_sub_success`
  - INC-NN-007 -> `test/include/cpu/test_nn.py::test_cpu_nn_truediv_success`
  - INC-NN-008 -> `test/include/cpu/test_nn.py::test_cpu_nn_compare_ne`
  - INC-NN-009 -> `test/include/cpu/test_nn.py::test_cpu_nn_compare_lt`
  - INC-NN-010 -> `test/include/cpu/test_nn.py::test_cpu_nn_compare_le`
  - INC-NN-011 -> `test/include/cpu/test_nn.py::test_cpu_nn_compare_gt`
  - INC-NN-012 -> `test/include/cpu/test_nn.py::test_cpu_nn_compare_ge`
  - INC-NN-013 -> `test/include/cpu/test_nn.py::test_cpu_nn_img2col1d_success_and_signature`
  - INC-NN-014 -> `test/include/cpu/test_nn.py::test_cpu_nn_img2col2d_success_and_signature`
  - INC-NN-015 -> `test/include/cpu/test_nn.py::test_cpu_nn_img2col1d_contract_violation_traps`
  - INC-NN-016 -> `test/include/cpu/test_nn.py::test_cpu_nn_img2col2d_contract_violation_traps`
  - INC-NN-017 -> `test/include/cpu/test_nn.py::test_cpu_nn_img2col1d_stride_violation_traps`
  - INC-NN-018 -> `test/include/cpu/test_nn.py::test_cpu_nn_img2col_generic_name_is_forbidden`
  - INC-NN-019 -> `test/include/cpu/test_nn.py::test_cpu_nn_exp_success`
  - INC-NN-020 -> `test/include/cpu/test_nn.py::test_cpu_nn_exp_contract_violation_traps`
  - INC-NN-021 -> `test/include/cpu/test_nn.py::test_cpu_nn_reduce_sum_success`
  - INC-NN-022 -> `test/include/cpu/test_nn.py::test_cpu_nn_reduce_sum_axis_contract_violation_traps`
  - INC-NN-023 -> `test/include/cpu/test_nn.py::test_cpu_nn_reduce_min_success`
  - INC-NN-024 -> `test/include/cpu/test_nn.py::test_cpu_nn_reduce_min_empty_extent_traps`
  - INC-NN-025 -> `test/include/cpu/test_nn.py::test_cpu_nn_reduce_max_success`
  - INC-NN-026 -> `test/include/cpu/test_nn.py::test_cpu_nn_reduce_max_empty_extent_traps`
  - INC-NN-027 -> `test/include/cpu/test_nn.py::test_cpu_nn_add_scalar_rhs_success`
  - INC-NN-028 -> `test/include/cpu/test_nn.py::test_cpu_nn_add_scalar_lhs_success`
