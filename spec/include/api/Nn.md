# Nn

## 功能简介

定义 include/api 层统一对外 NN 运算 API 头文件规范（`include/api/Nn.h`），提供逐元素算术、逐元素比较与显式 broadcast 的标准接口，面向后端无关的内存视图抽象。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`摸鱼小分队`
- `spec`：[`spec/include/api/Nn.md`](../../../spec/include/api/Nn.md)
- `统一头文件`：`include/api/Nn.h` / `include/api/Memory.h` / `include/api/Core.h`
- `功能实现`：无（API 规范暂不绑定实现）
- `test`：无（API 规范暂不提供测试）

## 依赖

- [`spec/include/api/Memory.md`](../../../spec/include/api/Memory.md)：API 统一内存视图抽象。
- [`spec/include/api/Core.md`](../../../spec/include/api/Core.md)：统一返回状态与状态码语义。
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
- 返回状态遵循 `spec/include/api/Core.md` 中的 `Status` 与 `StatusCode` 语义。
- 内存视图抽象需满足以下最小要求：
  - `data` 指向有效连续内存区（实现可扩展为其他存储形式，但需保持语义一致）。
  - `shape`/`stride` 为长度 `rank` 的维度与步长描述，维度为正数；`Memory<T>` 的 `rank` 为运行期属性，不固定为编译期模板参数。
  - 输入与输出视图的类型与后端一致性由实现侧保证。
- `include/api/Nn.h` 仅提供声明与类型边界，不提供函数体实现；具体后端实现需在各自 include 层提供（当前 `npu_demo` 实现头文件为 [`include/npu_demo/Nn.h`](../../../include/npu_demo/Nn.h)）。

## 公开接口

以下示例以统一对外接口名表示，统一头文件为 `include/api/Nn.h` 并依赖 `include/api/Memory.h` 与 `include/api/Core.h`。对外公开接口仅使用无命名空间签名；如实现侧需要命名空间或封装层，仅允许在内部适配/包装，不得改变公开 API 签名。`Status` 与 `StatusCode` 语义以 `spec/include/api/Core.md` 为准。

### `add(lhs, rhs, out)`

功能说明：对两个内存视图执行逐元素加法，结果写入输出视图。

参数说明：

- `lhs (Memory<T>)`：左操作数视图。
- `rhs (Memory<T>)`：右操作数视图。
- `out (Memory<T>)`：输出视图。

使用示例：

```cpp
Status status = add(lhs, rhs, out);
```

注意事项：

- `lhs/rhs/out` 的 `rank` 必须一致，且 `shape` 完全一致。
- `lhs/rhs/out` 的 `stride` 必须可用于同一 `rank` 的逐元素访问。
- 不定义标量重载，不支持隐式广播。

返回与限制：

- 返回状态值；`0` 表示成功，非 `0` 表示失败。
- 当形状、步幅或类型不满足约束时必须返回失败状态值。

### `sub(lhs, rhs, out)`

功能说明：对两个内存视图执行逐元素减法，结果写入输出视图。

参数说明：

- `lhs (Memory<T>)`：左操作数视图。
- `rhs (Memory<T>)`：右操作数视图。
- `out (Memory<T>)`：输出视图。

使用示例：

```cpp
Status status = sub(lhs, rhs, out);
```

注意事项：

- `lhs/rhs/out` 的 `rank` 与 `shape` 必须一致。
- 不定义标量重载，不支持隐式广播。

返回与限制：

- 返回状态值；`0` 表示成功，非 `0` 表示失败。
- 形状、步幅或类型不满足约束时必须返回失败状态值。

### `mul(lhs, rhs, out)`

功能说明：对两个内存视图执行逐元素乘法，结果写入输出视图。

参数说明：

- `lhs (Memory<T>)`：左操作数视图。
- `rhs (Memory<T>)`：右操作数视图。
- `out (Memory<T>)`：输出视图。

使用示例：

```cpp
Status status = mul(lhs, rhs, out);
```

注意事项：

- `lhs/rhs/out` 的 `rank` 与 `shape` 必须一致。
- 不定义标量重载，不支持隐式广播。

返回与限制：

- 返回状态值；`0` 表示成功，非 `0` 表示失败。
- 形状、步幅或类型不满足约束时必须返回失败状态值。

### `truediv(lhs, rhs, out)`

功能说明：对两个内存视图执行逐元素真除法，结果写入输出视图。

参数说明：

- `lhs (Memory<T>)`：左操作数视图。
- `rhs (Memory<T>)`：右操作数视图。
- `out (Memory<T>)`：输出视图。

使用示例：

```cpp
Status status = truediv(lhs, rhs, out);
```

注意事项：

- `lhs/rhs/out` 的 `rank` 与 `shape` 必须一致。
- 不定义标量重载，不支持隐式广播。

返回与限制：

- 返回状态值；`0` 表示成功，非 `0` 表示失败。
- 形状、步幅或类型不满足约束时必须返回失败状态值。

### `eq(lhs, rhs, out)`

功能说明：对两个内存视图执行逐元素相等比较，输出 predicate 结果。

参数说明：

- `lhs (Memory<T>)`：左操作数视图。
- `rhs (Memory<T>)`：右操作数视图。
- `out (Memory<PredT>)`：输出视图，元素类型用于表示 predicate 结果。

使用示例：

```cpp
Status status = eq(lhs, rhs, out);
```

注意事项：

- `lhs/rhs/out` 的 `rank` 与 `shape` 必须一致。
- `out` 的元素类型需能表示 predicate 结果（例如 `0/1`）。
- 不支持隐式广播。

返回与限制：

- 返回状态值；`0` 表示成功，非 `0` 表示失败。
- 形状或类型不满足约束时必须返回失败状态值。

### `ne(lhs, rhs, out)`

功能说明：对两个内存视图执行逐元素不等比较，输出 predicate 结果。

参数说明：

- `lhs (Memory<T>)`：左操作数视图。
- `rhs (Memory<T>)`：右操作数视图。
- `out (Memory<PredT>)`：输出视图，元素类型用于表示 predicate 结果。

使用示例：

```cpp
Status status = ne(lhs, rhs, out);
```

注意事项：

- `lhs/rhs/out` 的 `rank` 与 `shape` 必须一致。
- `out` 的元素类型需能表示 predicate 结果。
- 不支持隐式广播。

返回与限制：

- 返回状态值；`0` 表示成功，非 `0` 表示失败。
- 形状或类型不满足约束时必须返回失败状态值。

### `lt(lhs, rhs, out)`

功能说明：对两个内存视图执行逐元素小于比较，输出 predicate 结果。

参数说明：

- `lhs (Memory<T>)`：左操作数视图。
- `rhs (Memory<T>)`：右操作数视图。
- `out (Memory<PredT>)`：输出视图，元素类型用于表示 predicate 结果。

使用示例：

```cpp
Status status = lt(lhs, rhs, out);
```

注意事项：

- `lhs/rhs/out` 的 `rank` 与 `shape` 必须一致。
- `out` 的元素类型需能表示 predicate 结果。
- 不支持隐式广播。

返回与限制：

- 返回状态值；`0` 表示成功，非 `0` 表示失败。
- 形状或类型不满足约束时必须返回失败状态值。

### `le(lhs, rhs, out)`

功能说明：对两个内存视图执行逐元素小于等于比较，输出 predicate 结果。

参数说明：

- `lhs (Memory<T>)`：左操作数视图。
- `rhs (Memory<T>)`：右操作数视图。
- `out (Memory<PredT>)`：输出视图，元素类型用于表示 predicate 结果。

使用示例：

```cpp
Status status = le(lhs, rhs, out);
```

注意事项：

- `lhs/rhs/out` 的 `rank` 与 `shape` 必须一致。
- `out` 的元素类型需能表示 predicate 结果。
- 不支持隐式广播。

返回与限制：

- 返回状态值；`0` 表示成功，非 `0` 表示失败。
- 形状或类型不满足约束时必须返回失败状态值。

### `gt(lhs, rhs, out)`

功能说明：对两个内存视图执行逐元素大于比较，输出 predicate 结果。

参数说明：

- `lhs (Memory<T>)`：左操作数视图。
- `rhs (Memory<T>)`：右操作数视图。
- `out (Memory<PredT>)`：输出视图，元素类型用于表示 predicate 结果。

使用示例：

```cpp
Status status = gt(lhs, rhs, out);
```

注意事项：

- `lhs/rhs/out` 的 `rank` 与 `shape` 必须一致。
- `out` 的元素类型需能表示 predicate 结果。
- 不支持隐式广播。

返回与限制：

- 返回状态值；`0` 表示成功，非 `0` 表示失败。
- 形状或类型不满足约束时必须返回失败状态值。

### `ge(lhs, rhs, out)`

功能说明：对两个内存视图执行逐元素大于等于比较，输出 predicate 结果。

参数说明：

- `lhs (Memory<T>)`：左操作数视图。
- `rhs (Memory<T>)`：右操作数视图。
- `out (Memory<PredT>)`：输出视图，元素类型用于表示 predicate 结果。

使用示例：

```cpp
Status status = ge(lhs, rhs, out);
```

注意事项：

- `lhs/rhs/out` 的 `rank` 与 `shape` 必须一致。
- `out` 的元素类型需能表示 predicate 结果。
- 不支持隐式广播。

返回与限制：

- 返回状态值；`0` 表示成功，非 `0` 表示失败。
- 形状或类型不满足约束时必须返回失败状态值。

### `broadcast(input, out)`

功能说明：将输入视图显式广播到目标形状（由输出视图指定）。

参数说明：

- `input (Memory<T>)`：输入视图。
- `out (Memory<T>)`：输出视图。

使用示例：

```cpp
Status status = broadcast(input, out);
```

注意事项：

- `out.rank >= input.rank`。
- 广播按尾维对齐，逐维满足 `input_dim == output_dim` 或 `input_dim == 1`。
- 输出视图的元素类型与输入一致。

返回与限制：

- 返回状态值；`0` 表示成功，非 `0` 表示失败。
- 当广播条件不满足时必须返回失败状态值。

## 测试

- 测试文件：无（API 规范不提供测试实现）
- 执行命令：无（API 规范不提供测试实现）
- 测试目标：无（API 规范不提供测试范围）
- 功能与用例清单：无（API 规范不绑定测试用例）
