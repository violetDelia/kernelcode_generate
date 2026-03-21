# Nn

## 功能简介

定义 include/api 层统一对外 NN 运算 API 头文件规范（`include/api/Nn.h`），提供逐元素算术、逐元素比较与显式 broadcast 的标准接口，面向后端无关的内存视图抽象。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`摸鱼小分队`
- `spec`：[`spec/include/api/Nn.md`](../../../spec/include/api/Nn.md)
- `统一头文件`：`include/api/Nn.h` / `include/api/Memory.h`
- `功能实现`：无（API 规范暂不绑定实现）
- `test`：无（API 规范暂不提供测试）

## 依赖

- [`spec/include/api/Memory.md`](../../../spec/include/api/Memory.md)：API 统一内存视图抽象。
- [`spec/operation/nn.md`](../../../spec/operation/nn.md)：逐元素算术、逐元素比较与显式广播的语义约束。

## 目标

- 提供统一对外的 NN 运算 API 头文件规范，作为所有后端的公共入口。
- 语义对齐 `spec/operation/nn.md` 已定义的逐元素算术、逐元素比较与显式 `broadcast`。
- 保持接口简洁，可由不同后端复用并映射到各自实现头文件。
- 统一头文件定位为 `include/api/Nn.h`（NN 运算）与 `include/api/Memory.h`（内存视图），二者构成 API 对外入口，不绑定仓库既有实现文件。

## 限制与边界

- 不支持隐式广播，不包含 `matmul` 等非逐元素算子。
- 本规范仅定义统一 API 头文件与接口约束，不绑定任何后端实现细节或实现文件路径。
- 后端实现需在各自 spec 中声明与本统一 API 的映射关系，但不得反向修改本规范语义。
- 统一对外头文件仅暴露接口签名与最小类型要求，不包含任何后端特有结构体或实现细节。
- API 仅定义合法输入语义；非法形状或不满足约束的调用必须通过返回失败状态值表达。
- 所有 NN API 必须由调用方显式提供输出视图，接口返回状态值，不通过函数返回输出对象。
- 状态值语义建议遵循：`0` 表示成功，非 `0` 表示失败；具体状态码枚举由实现侧定义。
- 内存视图抽象需满足以下最小要求：
  - `data` 指向有效连续内存区（实现可扩展为其他存储形式，但需保持语义一致）。
  - `shape`/`stride` 为长度 `rank` 的维度与步长描述，维度为正数；`Memory<T>` 的 `rank` 为运行期属性，不固定为编译期模板参数。
  - 输入与输出视图的类型与后端一致性由实现侧保证。

## 公开接口

以下示例以统一对外接口名表示，命名空间由实现侧确定；统一头文件为 `include/api/Nn.h` 并依赖 `include/api/Memory.h`。

### 逐元素算术（add/sub/mul/truediv）

- 功能说明：对两个内存视图执行逐元素算术，结果写入输出视图。
- 参数说明：
  - `lhs (Memory<T>)`：左操作数视图。
  - `rhs (Memory<T>)`：右操作数视图。
  - `out (Memory<T>)`：输出视图。
- 使用示例：
  - `Status status = add(lhs, rhs, out)`
- 注意事项：
  - `lhs.shape`、`rhs.shape`、`out.shape` 必须一致。
  - `lhs.stride`、`rhs.stride`、`out.stride` 需能用于同一 `rank` 的逐元素访问。
  - 不定义标量重载与隐式广播。
- 返回与限制：
  - 返回状态值；`0` 表示成功，非 `0` 表示失败。
  - 当形状、步幅或类型不满足约束时必须返回失败状态值。

### 逐元素比较（eq/ne/lt/le/gt/ge）

- 功能说明：对两个内存视图执行逐元素比较，输出 predicate 结果。
- 参数说明：
  - `lhs (Memory<T>)`：左操作数视图。
  - `rhs (Memory<T>)`：右操作数视图。
  - `out (Memory<PredT>)`：输出视图，元素类型用于表示 predicate 结果。
- 使用示例：
  - `Status status = eq(lhs, rhs, out)`
- 注意事项：
  - `lhs.shape`、`rhs.shape`、`out.shape` 必须一致。
  - `out` 的元素类型需能表示 predicate 结果（例如 `0/1`）。
- 返回与限制：
  - 返回状态值；`0` 表示成功，非 `0` 表示失败。
  - 当形状或类型不满足约束时必须返回失败状态值。

### 显式 broadcast

- 功能说明：将输入视图显式广播到目标形状（由输出视图指定）。
- 参数说明：
  - `input (Memory<T>)`：输入视图。
  - `out (Memory<T>)`：输出视图。
- 使用示例：
  - `Status status = broadcast(input, out)`
- 注意事项：
  - `OutRank >= InRank`。
  - 广播按尾维对齐，逐维满足 `input_dim == output_dim` 或 `input_dim == 1`。
  - 输出视图的元素类型与输入一致。
- 返回与限制：
  - 返回状态值；`0` 表示成功，非 `0` 表示失败。
  - 当广播条件不满足时必须返回失败状态值。

## 测试

- 测试文件：无（API 规范不提供测试实现）
- 执行命令：无（API 规范不提供测试实现）
- 测试目标：无（API 规范不提供测试范围）
- 功能与用例清单：无（API 规范不绑定测试用例）
