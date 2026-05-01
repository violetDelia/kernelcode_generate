# Dma

## 功能简介

定义 include/api 层统一对外 DMA 操作 API 头文件规范（`include/api/Dma.h`），当前公共层收口 `npu_demo::alloc`、`npu_demo::fill`、`npu_demo::slice`、`npu_demo::deslice`、`npu_demo::transpose` 与 `npu_demo::broadcast` 六个 public function，面向后端无关的 `Memory<Space, T>` 与 `Vector` 抽象。

- `npu_demo::alloc<Space, T>(shape, stride, format)`：定义创建 DMA 临时 `Memory<Space, T>` 视图的公开接口。
- `npu_demo::fill(target, value)`：定义按标量填充目标块全部逻辑元素的公开接口。
- `npu_demo::slice(target, source, offset, size, stride)`：定义把源区域切片读取到预分配 `target` 的公开接口。
- `npu_demo::deslice(target, source, offset, size, stride)`：定义将源块写回目标区域的公开接口。
- `npu_demo::transpose(target, source, perm)`：定义按 `perm` 将源块物化转置到预分配 `target` 的公开接口。
- `npu_demo::broadcast(target, source)`：定义按 trailing-dimension 规则把 `source` 物化扩张到预分配 `target` 的公开接口。
- `view` 与 `reshape` 已移动到 `Memory` 的成员接口，不再保留以 `source` 为首参的公共层自由函数。
- 本规范只冻结统一 API 名称、参数形态、输入约束与错误边界；不绑定任何具体后端实现。

## API 列表

- `template <MemorySpace Space, typename T> Memory<Space, T> npu_demo::alloc(std::initializer_list<long long> shape, std::initializer_list<long long> stride, MemoryFormat format = MemoryFormat::Norm)`
- `template <MemorySpace Space, typename T> Status npu_demo::fill(Memory<Space, T>& target, const T& value)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T> Status npu_demo::slice(Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename T> Status npu_demo::deslice(Memory<TargetSpace, T>& target, const Memory<SourceSpace, T>& source, const Vector& offset, const Vector& size, const Vector& stride)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType> Status npu_demo::transpose(Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source, const Vector& perm)`
- `template <MemorySpace TargetSpace, MemorySpace SourceSpace, typename TargetType, typename SourceType> Status npu_demo::broadcast(Memory<TargetSpace, TargetType>& target, const Memory<SourceSpace, SourceType>& source)`

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`大闸蟹`
- `spec`：[`spec/include/api/Dma.md`](../../../spec/include/api/Dma.md)
- `统一头文件`：[`include/api/Dma.h`](../../../include/api/Dma.h) / [`include/api/Memory.h`](../../../include/api/Memory.h) / [`include/api/Core.h`](../../../include/api/Core.h)
- `功能实现`：[`include/npu_demo/Dma.h`](../../../include/npu_demo/Dma.h)
- `test`：
  - [`test/include/api/test_dma.py`](../../../test/include/api/test_dma.py)
  - [`test/include/npu_demo/test_public_namespace.py`](../../../test/include/npu_demo/test_public_namespace.py)

## 依赖

- [`spec/include/api/Core.md`](../../../spec/include/api/Core.md)：`Vector`、`Status`、`StatusCode` 统一基础契约。
- [`spec/include/api/Memory.md`](../../../spec/include/api/Memory.md)：`Memory<Space, T>`、`MemorySpace`、`get_shape/get_stride`、`view<T>`、`reshape` 统一语义。
- [`spec/include/api/cost/Dma.md`](../../../spec/include/api/cost/Dma.md)：定义与当前 DMA 公共层对应的成本 helper 合同。
- [`spec/operation/dma.md`](../../../spec/operation/dma.md)：高层 DMA 语义；同名概念需保持职责一致，但允许因分层不同而使用不同签名。

## 目标

- 为跨后端代码生成提供统一、稳定的 DMA 公开 API。
- 统一 `offset/size/stride` 的公开参数类型为 [`spec/include/api/Core.md`](../../../spec/include/api/Core.md) 中的 `Vector`。
- 明确 DMA public function 的成功调用入口统一为 `npu_demo::alloc(...)`、`npu_demo::fill(...)`、`npu_demo::slice(...)`、`npu_demo::deslice(...)`、`npu_demo::transpose(...)`、`npu_demo::broadcast(...)`。
- 明确 `slice/deslice` 的输入约束、返回语义与错误边界。
- 明确删旧边界：`view` / `reshape` 不再属于 DMA 公共层；`source-first deslice`、`store` 等旧公开形态退出本轮稳定口径。
- 为后续 `spec/operation/dma.md`、`spec/dialect/dma.md`、`spec/dsl/mlir_gen.md`、`spec/dsl/gen_kernel/emit.md`、`spec/dsl/gen_kernel/gen_kernel.md` 提供统一收敛目标。

## 限制与边界

- 本规范不定义 DMA 硬件调度、异步执行、带宽模型、barrier、launch、host wrapper 或后端私有运行时。
- 本规范只定义 `npu_demo::alloc`、`npu_demo::fill`、`npu_demo::slice`、`npu_demo::deslice`、`npu_demo::transpose`、`npu_demo::broadcast` 六个 DMA public function；`free/copy/cast/load/store` 等语义若实现暂存，也不属于本轮稳定公共层。
- `offset/size/stride` 的公开参数类型统一为 `Vector`；不得把 `std::vector<long long>`、`std::array<long long, N>`、裸 `long long[N]` 直接暴露成稳定公开签名。
- `alloc/slice/deslice` 的接口面向 `Memory<Space, T>`；不使用 `memory<rank, type>`、`memory<float>` 之类模板占位语言作为公开契约描述。
- `view` 与 `reshape` 已在 `Memory` 公共层收口；`Dma` 不再公开以 `source` 为首参的 `view` 自由函数。
- `deslice` 固定为 `target-first`；不得继续保留 `source-first deslice` 这种旧顺序公共口径。
- `slice` 与 `deslice` 都不改变元素类型；若实现侧需要类型变换，应通过其他明确接口处理。
- `transpose` 固定为 `target-first`；`perm[target_axis]` 表示 target 轴从 source 的哪一轴读取，调用方必须显式准备目标块。
- `slice` 是目标式接口：调用方必须先准备好 `target`；include/api 层不为 `slice` 隐式分配结果内存。
- `include/api/Dma.h` 仅提供声明与类型边界，不提供函数体实现；具体后端实现需在各自 include 层提供。
- 未限定的全局 `alloc`、`slice`、`deslice` 名称不属于成功调用合同；调用方应经 `namespace npu_demo` 消费。

## 公开接口

### `npu_demo::alloc<Space, T>(shape, stride, format)`

功能说明：

- 按给定 `shape/stride/format` 创建 DMA 临时 `Memory<Space, T>` 视图。
- 该接口供手写 npu_demo 源码与 `emit_c/gen_kernel(target=npu_demo)` 生成源码申请临时块。

参数说明：

- `Space (MemorySpace)`：目标内存空间模板参数。
- `T (type)`：元素类型模板参数。
- `shape (std::initializer_list<long long>)`：临时块逻辑形状。
- `stride (std::initializer_list<long long>)`：临时块步幅。
- `format (MemoryFormat)`：布局格式，默认 `MemoryFormat::Norm`。

使用示例：

```cpp
#include "include/npu_demo/npu_demo.h"

auto tile = npu_demo::alloc<TSM, float>({16}, {1}, MemoryFormat::Norm);
```

注意事项：

- `alloc` 的 public function 入口固定为 `npu_demo::alloc(...)`。
- `shape` 与 `stride` 的长度必须一致，且元素值需要满足 `Memory` 视图合同。
- 未限定的全局 `alloc` 名称不属于成功调用合同。

返回与限制：

- 返回类型：`Memory<Space, T>`。
- 返回语义：返回可由 `npu_demo::slice/deslice` 消费的临时内存视图。
- 限制条件：非法空间、非法形状或非法步幅必须按实现约定显式报错。

### `npu_demo::fill(target, value)`

功能说明：

- 使用标量 `value` 填充 `target` 的全部逻辑元素。
- 该接口用于承接 `dma.fill` lowering 后的目标式初始化源码。

参数说明：

- `Space (MemorySpace)`：目标空间模板参数。
- `T (type)`：元素类型模板参数。
- `target (Memory<Space, T>)`：待填充目标块。
- `value (const T&)`：写入标量值。

使用示例：

```cpp
#include "include/npu_demo/npu_demo.h"

Status status = npu_demo::fill<TSM, float>(target, 0.0f);
```

注意事项：

- `fill` 的 public function 入口固定为 `npu_demo::fill(...)`，未限定的全局 `fill` 名称不属于成功调用合同。
- 调用方必须显式提供目标块；`fill` 不分配内存、不返回新 Memory。
- `target` 的 rank、shape、stride 与 data 指针必须满足 `Memory` 视图合同。

返回与限制：

- 返回类型：`Status`。
- 返回语义：`0` 表示填充成功，非 `0` 表示失败。
- 限制条件：空指针、非法 rank、非正 shape/stride 必须返回失败状态或按实现约定显式报错。

### `npu_demo::slice(target, source, offset, size, stride)`

功能说明：

- 从 `source` 读取一个切片区域，并写入预分配的 `target`。
- 该接口在 include/api 层固定为目标式读切片职责；它不是表达式式返回值接口。

参数说明：

- `target (Memory<TargetSpace, T>)`：预分配结果块，承接切片读取结果。
- `source (Memory<SourceSpace, T>)`：源内存视图。
- `offset (Vector)`：起始偏移向量，长度必须与 `source.rank()` 一致。
- `size (Vector)`：结果块逻辑大小，长度必须与 `source.rank()` 一致，且必须与 `target` 对齐。
- `stride (Vector)`：访问步进向量，长度必须与 `source.rank()` 一致。

使用示例：

```cpp
#include "include/npu_demo/npu_demo.h"

long long offset_buf[1] = {32};
long long size_buf[1] = {16};
long long stride_buf[1] = {1};

Vector offset(offset_buf, 1);
Vector size(size_buf, 1);
Vector stride(stride_buf, 1);

Status status = npu_demo::slice(target, source, offset, size, stride);
```

注意事项：

- `slice` 采用显式 `target/source` 形态，便于代码生成直接映射到目标式搬运接口。
- `slice` 的 public function 入口固定为 `npu_demo::slice(...)`，未限定的全局 `slice` 名称不属于成功调用合同。
- `target` 与 `source` 的元素类型必须一致。
- `target` 对应的逻辑大小必须与 `size` 对齐；不得把 `slice` 用成“自动分配并返回结果”的接口。
- 高层 `operation.slice` 若采用表达式式返回值，必须在 lowering 时先显式补出目标内存，再桥接到本接口。

返回与限制：

- 返回类型：`Status`。
- 返回语义：`0` 表示切片读取成功，非 `0` 表示失败。
- 限制条件：`target/source` 元素类型不一致、长度不一致、静态越界、负 offset、非正 size/stride 均必须返回失败状态或按实现约定显式报错。

### `npu_demo::deslice(target, source, offset, size, stride)`

功能说明：

- 将 `source` 块写回 `target` 的指定区域。
- 该接口是 include/api 层稳定公开的写回接口名。

参数说明：

- `target (Memory<TargetSpace, T>)`：目标内存视图。
- `source (Memory<SourceSpace, T>)`：源块。
- `offset (Vector)`：目标区域起始偏移向量，长度必须与 `target.rank()` 一致。
- `size (Vector)`：目标区域逻辑大小，长度必须与 `target.rank()` 一致，且必须与 `source` 对齐。
- `stride (Vector)`：访问步进向量，长度必须与 `target.rank()` 一致。

使用示例：

```cpp
#include "include/npu_demo/npu_demo.h"

long long offset_buf[1] = {64};
long long size_buf[1] = {16};
long long stride_buf[1] = {1};

Vector offset(offset_buf, 1);
Vector size(size_buf, 1);
Vector stride(stride_buf, 1);

Status status = npu_demo::deslice(target, source, offset, size, stride);
```

注意事项：

- `deslice` 固定为 `target-first`；不得继续保留 `source-first deslice` 这种旧顺序公共口径。
- `deslice` 的 public function 入口固定为 `npu_demo::deslice(...)`，未限定的全局 `deslice` 名称不属于成功调用合同。
- `source` 与 `target` 的元素类型必须一致。
- `size` 必须与 `source` 对齐；不得把 `deslice` 用成“源块与目标块大小不一致但自动广播/裁剪”的接口。
- `store(...)` 只能作为后端内部旧原语存在，不能继续出现在稳定源码形态、计划书与公共层验收清单中。

返回与限制：

- 返回类型：`Status`。
- 返回语义：`0` 表示写回成功，非 `0` 表示失败。
- 限制条件：元素类型不一致、长度不一致、静态越界、负 offset、非正 size/stride 必须返回失败状态或按实现约定显式报错。

### `npu_demo::transpose(target, source, perm)`

功能说明：

- 将 `source` 按 `perm` 物化转置到预分配 `target`。
- 该接口用于承接 `dma.transpose` / `nn.transpose` lowering 后的目标式搬运源码。

参数说明：

- `target (Memory<TargetSpace, TargetType>)`：预分配目标块。
- `source (Memory<SourceSpace, SourceType>)`：源块。
- `perm (Vector)`：转置轴映射，长度必须等于 `source.rank()`，且是 `0..rank-1` 的排列。

使用示例：

```cpp
#include "include/npu_demo/npu_demo.h"

Status status = npu_demo::transpose(target, source, Vector{1, 0});
```

注意事项：

- `transpose` 的 public function 入口固定为 `npu_demo::transpose(...)`，未限定的全局 `transpose` 名称不属于成功调用合同。
- `target.rank()` 必须等于 `source.rank()`。
- `target.get_shape(axis)` 必须等于 `source.get_shape(perm[axis])`。
- 元素类型不同时，后端实现可按目标元素类型显式转换。

返回与限制：

- 返回类型：`Status`。
- 返回语义：`0` 表示转置成功，非 `0` 表示失败。
- 限制条件：rank 不一致、`perm` 非排列、shape 不匹配、空指针或非法 stride 必须返回失败状态或按实现约定显式报错。

### `npu_demo::broadcast(target, source)`

功能说明：

- 将 `source` 按 trailing-dimension broadcast 规则物化到预分配 `target`。
- 该接口用于承接 `dma.broadcast` lowering 后的目标式扩张源码。

参数说明：

- `TargetSpace (MemorySpace)`：目标空间模板参数。
- `SourceSpace (MemorySpace)`：源空间模板参数。
- `TargetType (type)`：目标元素类型模板参数。
- `SourceType (type)`：源元素类型模板参数。
- `target (Memory<TargetSpace, TargetType>)`：预分配目标块。
- `source (Memory<SourceSpace, SourceType>)`：源块。

使用示例：

```cpp
#include "include/npu_demo/npu_demo.h"

Status status = npu_demo::broadcast<TSM, TSM, float, float>(target, source);
```

注意事项：

- `broadcast` 的 public function 入口固定为 `npu_demo::broadcast(...)`，未限定的全局 `broadcast` 名称不属于成功调用合同。
- `source.rank()` 必须小于或等于 `target.rank()`，并按尾部维度对齐。
- 对齐后的每个源维度必须等于目标维度或等于 `1`；源维度为 `1` 时沿目标维度复制。
- 元素类型不同时，后端实现可按目标元素类型显式转换。

返回与限制：

- 返回类型：`Status`。
- 返回语义：`0` 表示 broadcast 物化成功，非 `0` 表示失败。
- 限制条件：rank 不合法、shape 不满足 broadcast 规则、空指针或非法 stride 必须返回失败状态或按实现约定显式报错。

## 测试

- 测试文件：[`test/include/api/test_dma.py`](../../../test/include/api/test_dma.py)、[`test/include/npu_demo/test_public_namespace.py`](../../../test/include/npu_demo/test_public_namespace.py)
- 执行命令：
  - `pytest -q test/include/api/test_dma.py`
  - `pytest -q test/include/npu_demo/test_public_namespace.py`
- 测试目标：
  - 验证 `npu_demo::alloc<Space, T>(...)` 是当前公共层稳定临时块创建接口。
  - 验证 `npu_demo::fill(target, value)` 是当前公共层稳定填充接口。
  - 验证 `npu_demo::slice(target, source, ...)` 是当前公共层稳定读切片接口。
  - 验证 `npu_demo::deslice(target, source, ...)` 是当前公共层稳定写回接口。
  - 验证 `npu_demo::transpose(target, source, ...)` 是当前公共层稳定转置接口。
  - 验证 `npu_demo::broadcast(target, source)` 是当前公共层稳定显式扩张接口。
  - 验证以 `source` 为首参的 `view` 自由函数与 `source-first deslice` 不再作为公共层稳定口径出现。
- 功能与用例清单：
  - `API-DMA-001`：`npu_demo::slice(target, source, ...)` 的最小目标式语义可工作。
  - `API-DMA-002`：`npu_demo::deslice(target, source, ...)` 的最小目标式语义可工作。
  - `API-DMA-003`：`npu_demo::transpose(target, source, ...)` 的最小目标式语义可工作。
  - `API-DMA-003B`：`npu_demo::fill/broadcast` 的最小目标式语义可工作。
  - `NPU-DEMO-PUBLIC-002`：`npu_demo::alloc/fill/slice/deslice/transpose/broadcast` 可经 `include/npu_demo/npu_demo.h` 正向编译运行，未限定的全局函数不作为成功路径。
