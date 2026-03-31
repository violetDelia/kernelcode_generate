# Core

## 功能简介

定义 include/api 层统一对外的基础类型与返回状态规范（`include/api/Core.h`），为 `Nn`、后端 helper 与代码生成层提供统一的状态码语义与最小基础类型边界。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`大闸蟹`
- `spec`：[`spec/include/api/Core.md`](../../../spec/include/api/Core.md)
- `统一头文件`：`include/api/Core.h`
- `功能实现`：无（API 规范暂不绑定实现）
- `test`：无（API 规范暂不提供测试）

## 依赖

- 无（Core 为 include/api 的基础类型规范）。

## 目标

- 为 include/api 全部对外接口提供统一返回状态基座。
- 明确状态码语义，避免各 API 自行定义不一致的错误表达。
- 提供统一基础向量类型 `Vector`，作为后端 helper 与代码生成层传递 `int64` 坐标/索引元组的公共载体。
- 约束状态表示与基础向量类型均不依赖 C++ 标准库与异常机制，便于在受限环境落地实现。

## 限制与边界

- 本规范仅定义状态类型、状态码语义与基础向量类型，不定义日志、异常、诊断对象或错误信息格式。
- 实现侧可扩展更多状态码，但不得改变已定义状态码的语义与数值约束。
- `Status` 表示 API 调用结果；失败时输出参数内容不做保证（由实现侧说明）。
- `Vector` 是“调用方提供底层连续缓冲区，Core 仅做轻量视图封装”的基础类型；元素类型固定为 `int64`，不承担所有权，不做动态分配，不引入 `std::vector`、`std::array`、`std::initializer_list` 或其他标准库容器依赖。
- `Vector` 用于表达 helper 的坐标/索引元组，例如 `view(source, offset, size, stride)`、`slice(source, offset, size, stride)`、`deslice(source, target, offset, size, stride)` 中的 `offset/size/stride`；它不是 `shape/stride` 元信息容器，也不负责推导内存布局。

## 公开接口

### `StatusCode`

功能说明：

- 定义统一返回状态码枚举，用于表达 API 成功或失败原因。

参数说明：

- 无参数。

使用示例：

```cpp
StatusCode code = StatusCode::kOk;
```

注意事项：

- `StatusCode::kOk` 的数值必须为 `0`。
- 非 `kOk` 表示失败，数值由实现侧保持一致性。

返回与限制：

- 返回类型：`StatusCode`。
- 返回语义：作为 `Status` 的标准码值来源。
- 限制条件：实现侧仅可新增码值，不得重定义已有码值含义。

### `Status`

功能说明：

- 统一 API 返回类型，表示调用结果与状态码。

参数说明：

- 无参数。

使用示例：

```cpp
Status status = StatusCode::kOk;
```

注意事项：

- `Status` 以 `StatusCode` 为最小语义集合；实现可将其定义为 `int` 或 `enum`，但需保证与 `StatusCode` 可互换。

返回与限制：

- 返回类型：`Status`。
- 返回语义：`0` 表示成功，非 `0` 表示失败。
- 限制条件：不得依赖异常或标准库错误类型。

### `Vector`

功能说明：

- 定义统一基础向量视图类型，用于表达后端 helper、代码生成与 include/runtime 接口中的 `int64` 坐标/索引元组。

参数说明：

- 无模板参数；元素类型固定为 `int64`。

使用示例：

```cpp
long long coords_buf[4] = {1, 0, 2, 3};
Vector coords(coords_buf, 4);
```

注意事项：

- `Vector` 只封装调用方提供的连续 `int64` 缓冲区，不复制、不分配、不释放底层数据。
- `Vector` 不依赖 `std::vector`、`std::array`、`std::initializer_list` 或其他标准库容器。
- `Vector` 的公开职责是表达“坐标/索引序列”；不得把 `shape/stride/rank` 元信息重新塞入该类型。
- 后端 helper 若需要多维坐标，必须通过 `Vector` 传入，不得各自发明 `std::vector<int64_t>`、`long long[rank]` 裸数组签名或后端私有坐标容器作为对外公开接口。
- 当 `Vector` 用作 `view/slice/deslice` 的 `offset/size/stride` 时，向量长度必须与相关对象的 rank 一致；长度不一致属于公开契约违约。

返回与限制：

- 返回类型：`Vector`。
- 返回语义：封装调用方提供的连续元素缓冲区及其长度。
- 限制条件：不承担所有权，不提供动态扩容，不定义标准库容器互转接口。

#### `Vector(data, size)`

功能说明：

- 使用调用方提供的连续 `int64` 缓冲区与元素个数构造 `Vector` 视图。

参数说明：

- `data (long long*)` 或 `data (const long long*)`：底层连续元素缓冲区首地址。
- `size (unsigned long long)`：元素个数。

使用示例：

```cpp
long long coords_buf[4] = {i, 0, 0, 0};
Vector coords(coords_buf, 4);
```

注意事项：

- 当 `size == 0` 时允许 `data == nullptr`。
- 当 `size > 0` 时，调用方需保证 `data` 指向至少 `size` 个连续元素。
- 该构造仅建立视图，不复制底层数组。

返回与限制：

- 返回类型：`Vector`。
- 返回语义：返回一个长度为 `size` 的轻量向量视图。
- 限制条件：非法指针与越界访问属于调用方违约；本规范不要求异常机制。

#### `size()`

功能说明：

- 返回 `Vector` 当前封装的元素个数。

参数说明：

- 无参数。

使用示例：

```cpp
unsigned long long n = coords.size();
```

注意事项：

- `size()` 只反映视图长度，不表示 shape/rank/stride 的业务语义。

返回与限制：

- 返回类型：`unsigned long long`。
- 返回语义：返回 `Vector` 封装的元素个数。
- 限制条件：无。

#### `data()`

功能说明：

- 返回底层连续元素缓冲区首地址。

参数说明：

- 无参数。

使用示例：

```cpp
const long long* raw = coords.data();
```

注意事项：

- 允许提供 `T*` 与 `const T*` 两类重载，具体由实现侧决定，但公开语义必须等价。
- 返回值仅用于只读或实现侧明确允许的原地写入；所有权仍归调用方。

返回与限制：

- 返回类型：`long long*` 或 `const long long*`。
- 返回语义：返回底层连续元素缓冲区首地址。
- 限制条件：不检查空指针。

#### `operator[](index)`

功能说明：

- 读取指定位置的元素值。

参数说明：

- `index (unsigned long long)`：元素下标。

使用示例：

```cpp
long long axis0 = coords[0];
```

注意事项：

- 调用方需保证 `index < size()`。
- 本规范不要求运行时越界检查，也不要求异常机制。

返回与限制：

- 返回类型：`long long` 或 `const long long&`。
- 返回语义：返回第 `index` 个元素。
- 限制条件：越界访问属于调用方违约。

## 测试

- 测试文件：无（API 规范不提供测试实现）
- 执行命令：无（API 规范不提供测试实现）
- 测试目标：无（API 规范不提供测试范围）
- 功能与用例清单：无（API 规范不绑定测试用例）
