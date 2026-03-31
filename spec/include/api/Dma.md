# Dma

## 功能简介

定义 include/api 层统一对外 DMA/视图操作 API 头文件规范（`include/api/Dma.h`），提供 `view`、`slice`、`deslice` 三个公开接口，面向后端无关的 `Memory<T>` 与 `Vector` 抽象。

- `view(source, offset, size, stride)`：定义逻辑子视图，不承诺发生数据搬运。
- `slice(target, source, offset, size, stride)`：定义把源区域切片读取到预分配 `target` 的公开接口。
- `deslice(source, target, offset, size, stride)`：定义将源块写回目标区域的公开接口。
- 本规范只冻结统一 API 名称、参数形态、输入约束与错误边界；不绑定任何具体后端实现。

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`大闸蟹`
- `spec`：[`spec/include/api/Dma.md`](../../../spec/include/api/Dma.md)
- `统一头文件`：`include/api/Dma.h` / `include/api/Memory.h` / `include/api/Core.h`
- `功能实现`：无（API 规范暂不绑定实现）
- `test`：无（API 规范暂不提供测试）

## 依赖

- [`spec/include/api/Core.md`](../../../spec/include/api/Core.md)：`Vector`、`Status`、`StatusCode` 统一基础契约。
- [`spec/include/api/Memory.md`](../../../spec/include/api/Memory.md)：`Memory<T>`、`MemorySpace`、`get_shape/get_stride` 统一语义。
- [`spec/operation/dma.md`](../../../spec/operation/dma.md)：用户侧高层 DMA 规范；同名概念需保持职责一致，但允许因分层不同而使用不同签名。

## 目标

- 为跨后端代码生成提供统一、稳定的 DMA/视图公开 API。
- 统一 `offset/size/stride` 的公开参数类型为 [`spec/include/api/Core.md`](../../../spec/include/api/Core.md) 中的 `Vector`，避免各后端公开 `std::vector`、裸数组或后端私有坐标容器。
- 明确 `view/slice/deslice` 的输入约束、返回语义与错误边界。
- 明确 `load/store` 不属于 include/api 层稳定公开接口；后端内部若仍保留底层原语，不影响本规范。
- 为后续 `spec/operation/dma.md`、`spec/dialect/dma.md`、`spec/dsl/mlir_gen.md`、`spec/dsl/emit_c.md`、`spec/dsl/gen_kernel.md` 提供统一收敛目标。
- `include/api` 与 `operation` 可对同一概念使用不同签名：当前固定为 `include.slice(target, source, ...)`，而高层 `operation.slice(...)` 仍可保持表达式式返回值；二者之间的桥接由 lowering 显式完成。

## 限制与边界

- 本规范不定义 DMA 硬件调度、异步执行、带宽模型、barrier、launch、host wrapper 或后端私有运行时。
- 本规范不定义 `alloc/free/copy/cast/reshape/flatten`；这些语义仍以各自规范为准。
- `offset/size/stride` 的公开参数类型统一为 `Vector`；不得把 `std::vector<long long>`、`std::array<long long, N>`、裸 `long long[N]` 直接暴露成稳定公开签名。
- `view/slice/deslice` 的接口面向 `Memory<T>`；不使用 `memory<rank, type>`、`memory<float>` 之类模板占位语言作为公开契约描述。
- `view` 与 `slice` 都不改变元素类型；若实现侧需要类型变换，应通过其他明确接口处理，而不是把类型变换偷渡进 `view/slice`。
- `deslice` 负责写回，不再公开 `store(...)` 作为 include/api 层稳定接口名。
- `slice` 是“目标式”接口：调用方必须先准备好 `target`；include/api 层不为 `slice` 隐式分配结果内存。

## 公开接口

以下示例以统一对外接口名表示，统一头文件为 `include/api/Dma.h` 并依赖 `include/api/Memory.h` 与 `include/api/Core.h`。对外公开接口仅使用无命名空间签名；如实现侧需要命名空间或封装层，仅允许在内部适配/包装，不得改变公开 API 签名。

### `view(source, offset, size, stride)`

功能说明：

- 返回 `source` 的逻辑子视图。
- `offset/size/stride` 仅描述子视图窗口，不承诺发生数据搬运。

参数说明：

- `source (Memory<T>)`：源内存视图。
- `offset (Vector)`：起始偏移向量，长度必须与 `source.rank()` 一致。
- `size (Vector)`：子视图逻辑大小，长度必须与 `source.rank()` 一致。
- `stride (Vector)`：子视图步进，长度必须与 `source.rank()` 一致。

使用示例：

```cpp
long long offset_buf[2] = {0, 16};
long long size_buf[2] = {8, 8};
long long stride_buf[2] = {1, 1};

Vector offset(offset_buf, 2);
Vector size(size_buf, 2);
Vector stride(stride_buf, 2);

auto sub = view(source, offset, size, stride);
```

注意事项：

- `offset/size/stride` 的长度必须与 `source.rank()` 一致。
- `offset` 中静态值必须为非负整数；`size/stride` 中静态值必须为正整数。
- `view` 不改变 `source` 的元素类型、空间分类或格式语义。
- `view` 的公开职责是“定义逻辑窗口”；不承担跨空间写回、类型变换或物化切片职责。

返回与限制：

- 返回类型：`Memory<T>`。
- 返回语义：返回一个逻辑子视图，其 `shape == size`，元素类型继承 `source`。
- 限制条件：静态越界、负 offset、非正 size/stride 均属于调用方违约；实现侧应通过失败状态或文档约定的错误机制表达。

### `slice(target, source, offset, size, stride)`

功能说明：

- 从 `source` 读取一个切片区域，并写入预分配的 `target`。
- 该接口在 include/api 层冻结为“目标式读切片”职责；它不是表达式式返回值接口。

参数说明：

- `target (Memory<T>)`：预分配结果块，承接切片读取结果。
- `source (Memory<T>)`：源内存视图。
- `offset (Vector)`：起始偏移向量，长度必须与 `source.rank()` 一致。
- `size (Vector)`：结果块逻辑大小，长度必须与 `source.rank()` 一致，且必须与 `target.shape` 对齐。
- `stride (Vector)`：访问步进向量，长度必须与 `source.rank()` 一致。

使用示例：

```cpp
float tile_buf[16] = {0};
long long tile_shape_buf[1] = {16};
long long tile_stride_buf[1] = {1};
long long offset_buf[1] = {32};
long long size_buf[1] = {16};
long long stride_buf[1] = {1};

Memory<float> tile(
    tile_buf,
    tile_shape_buf,
    tile_stride_buf,
    1,
    MemoryFormat::Norm,
    MemorySpace::TSM);
Vector offset(offset_buf, 1);
Vector size(size_buf, 1);
Vector stride(stride_buf, 1);

Status status = slice(tile, source, offset, size, stride);
```

注意事项：

- `slice` 与 `deslice` 都采用显式 `target/source` 形态，便于代码生成直接映射到目标式搬运接口。
- `target` 与 `source` 的元素类型必须一致。
- `target.shape` 必须与 `size` 对齐；不得把 `slice` 用成“自动分配并返回结果”的接口。
- 高层 `operation.slice(source, offset, size, stride, space)` 若采用表达式式返回值，必须在 lowering 时先显式补出 `alloc(target)`，再桥接到本接口；include/api 层不承担这部分隐式分配职责。
- `slice` 不公开标量 `load` 变体；标量读取若需要存在，只能是后端私有实现细节，不是稳定公开接口。

返回与限制：

- 返回类型：`Status`。
- 返回语义：`0` 表示切片读取成功，非 `0` 表示失败。
- 限制条件：`target/source` 元素类型不一致、`target.shape` 与 `size` 不一致、`offset/size/stride` 长度不一致、静态越界、负 offset、非正 size/stride 均必须返回失败状态或按实现约定显式报错。

### `deslice(source, target, offset, size, stride)`

功能说明：

- 将 `source` 块写回 `target` 的指定区域。
- 该接口是 include/api 层稳定公开的写回接口名；不再公开 `store(...)` 作为统一 API 名称。

参数说明：

- `source (Memory<T>)`：源块。
- `target (Memory<T>)`：目标内存视图。
- `offset (Vector)`：目标区域起始偏移向量，长度必须与 `target.rank()` 一致。
- `size (Vector)`：目标区域逻辑大小，长度必须与 `target.rank()` 一致，且必须与 `source.shape` 对齐。
- `stride (Vector)`：访问步进向量，长度必须与 `target.rank()` 一致。

使用示例：

```cpp
long long offset_buf[1] = {64};
long long size_buf[1] = {16};
long long stride_buf[1] = {1};

Vector offset(offset_buf, 1);
Vector size(size_buf, 1);
Vector stride(stride_buf, 1);

Status status = deslice(tile, target, offset, size, stride);
```

注意事项：

- `source` 与 `target` 的元素类型必须一致。
- `size` 必须与 `source.shape` 对齐；不得把 `deslice` 用成“源块与目标块大小不一致但自动广播/裁剪”的接口。
- `deslice` 是 include/api 层唯一稳定写回名字；`store` 只能作为后端内部旧原语存在，不能继续出现在稳定源码形态、spec 计划与验收清单中。

返回与限制：

- 返回类型：`Status`。
- 返回语义：`0` 表示写回成功，非 `0` 表示失败。
- 限制条件：元素类型不一致、`size` 与 `source.shape` 不一致、静态越界、负 offset、非正 size/stride 必须返回失败状态或按实现约定显式报错。

## 测试

- 测试文件：无（API 规范不提供测试实现）
- 执行命令：无（API 规范不提供测试实现）
- 测试目标：无（API 规范不提供测试范围）
- 功能与用例清单：无（API 规范不绑定测试用例）
