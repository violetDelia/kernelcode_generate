# Nn

## 功能简介

定义 include/api 层 NN 运算 API，提供逐元素算术、逐元素比较与显式 broadcast 的标准接口，面向后端无关的内存视图抽象。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`咯咯咯`
- `spec`：[`spec/include/api/Nn.md`](../../../spec/include/api/Nn.md)
- `功能实现`：无（API 规范暂不绑定实现）
- `test`：无（API 规范暂不提供测试）

## 依赖

- [`spec/operation/nn.md`](../../../spec/operation/nn.md)：逐元素算术、逐元素比较与显式广播的语义约束。

## 目标

- 提供后端无关的 NN 运算 API 标准接口。
- 语义对齐 `spec/operation/nn.md` 已定义的逐元素算术、逐元素比较与显式 `broadcast`。
- 保持接口简洁，可由不同后端复用并映射到各自的实现。

## 限制与边界

- 不支持隐式广播，不包含 `matmul` 等非逐元素算子。
- API 仅定义合法输入语义，非法形状或不满足约束的调用行为由实现侧决定（可选择检查并报错或视为未定义行为）。
- 内存视图抽象需满足以下最小要求：
  - `data` 指向有效连续内存区（实现可扩展为其他存储形式，但需保持语义一致）。
  - `shape`/`stride` 为长度 `Rank` 的维度与步长描述，维度为正数。
  - 输入与输出视图的类型与后端一致性由实现侧保证。

## 公开接口

以下示例以 `api::` 命名空间表示标准接口名，实际实现可根据后端命名做映射。

### 逐元素算术（add/sub/mul/truediv）

- 功能说明：对两个内存视图执行逐元素算术，结果写入输出视图。
- 参数说明：
  - `lhs (MemoryView<T, Rank>)`：左操作数视图。
  - `rhs (MemoryView<T, Rank>)`：右操作数视图。
  - `out (MemoryView<T, Rank>)`：输出视图。
- 使用示例：
  - `api::add(lhs, rhs, out)`
- 注意事项：
  - `lhs.shape`、`rhs.shape`、`out.shape` 必须一致。
  - `lhs.stride`、`rhs.stride`、`out.stride` 需能用于同一 `Rank` 的逐元素访问。
  - 不定义标量重载与隐式广播。
- 返回与限制：无返回值，输出写入 `out`。

### 逐元素比较（eq/ne/lt/le/gt/ge）

- 功能说明：对两个内存视图执行逐元素比较，输出 predicate 结果。
- 参数说明：
  - `lhs (MemoryView<T, Rank>)`：左操作数视图。
  - `rhs (MemoryView<T, Rank>)`：右操作数视图。
  - `out (MemoryView<PredT, Rank>)`：输出视图，元素类型用于表示 predicate 结果。
- 使用示例：
  - `api::eq(lhs, rhs, out)`
- 注意事项：
  - `lhs.shape`、`rhs.shape`、`out.shape` 必须一致。
  - `out` 的元素类型需能表示 predicate 结果（例如 `0/1`）。
- 返回与限制：无返回值，输出写入 `out`。

### 显式 broadcast

- 功能说明：将输入视图显式广播到目标形状（由输出视图指定）。
- 参数说明：
  - `input (MemoryView<T, InRank>)`：输入视图。
  - `out (MemoryView<T, OutRank>)`：输出视图。
- 使用示例：
  - `api::broadcast(input, out)`
- 注意事项：
  - `OutRank >= InRank`。
  - 广播按尾维对齐，逐维满足 `input_dim == output_dim` 或 `input_dim == 1`。
  - 输出视图的元素类型与输入一致。
- 返回与限制：无返回值，输出写入 `out`。

## 测试

- 测试文件：无（API 规范不提供测试实现）
- 执行命令：无（API 规范不提供测试实现）
- 测试目标：无（API 规范不提供测试范围）
- 功能与用例清单：无（API 规范不绑定测试用例）
