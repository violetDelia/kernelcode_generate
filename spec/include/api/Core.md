# Core

## 功能简介

定义 include/api 层统一对外的基础类型与返回状态规范（`include/api/Core.h`），为 `Memory`、`Dma`、后端 helper 与代码生成层提供统一的状态码语义与最小基础类型边界。

- 本轮公共层只收口 `Status`、`StatusCode`、`Vector` 三个公开名字。
- `Vector` 是轻量只读/可写视图；也支持 1..4 个 `long long` 值的花括号构造，并把这些值复制到对象内联存储。
- `Vector` 不做动态分配，不依赖初始化列表或标准库容器。
- `Core` 不定义 `view`、`reshape`、`slice`、`deslice` 等业务 helper。

## API 列表

- `enum StatusCode { kOk = 0, kError = 1 }`
- `using Status = StatusCode`
- `using S_INT = long long`
- `class Vector`
- `Vector::Vector(long long* data, unsigned long long size)`
- `Vector::Vector(const long long* data, unsigned long long size)`
- `Vector::Vector(long long value0)`
- `Vector::Vector(long long value0, long long value1)`
- `Vector::Vector(long long value0, long long value1, long long value2)`
- `Vector::Vector(long long value0, long long value1, long long value2, long long value3)`
- `Vector::Vector(const Vector& other)`
- `Vector::operator=(const Vector& other) -> Vector&`
- `Vector::size() const -> unsigned long long`
- `Vector::data() -> long long*`
- `Vector::data() const -> const long long*`
- `Vector::operator[](unsigned long long index) -> long long&`
- `Vector::operator[](unsigned long long index) const -> const long long&`

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`jcc你莫辜负`
- `spec`：[`spec/include/api/Core.md`](../../../spec/include/api/Core.md)
- `统一头文件`：[`include/api/Core.h`](../../../include/api/Core.h)
- `功能实现`：[`include/npu_demo/Core.h`](../../../include/npu_demo/Core.h)
- `test`：[`test/include/api/test_core.py`](../../../test/include/api/test_core.py)

## 依赖

- 无（`Core` 为 include/api 基础类型规范）。

## 目标

- 为 include/api 全部公开接口提供统一返回状态基座。
- 明确状态码语义，避免各 API 自行定义不一致的错误表达。
- 提供统一基础向量类型 `Vector`，作为坐标、索引、shape、stride、offset 等公共载体。
- 支持 `Vector{...}` 与 `Vector values = {...}` 两种 1..4 个值的调用形态。
- 明确删旧边界：公共层不再把 `std::vector<long long>`、`std::array<long long, N>`、后端私有坐标容器写成稳定接口。

## 限制与边界

- 本规范仅定义状态类型、状态码语义与基础向量类型，不定义日志、异常、诊断对象或错误信息格式。
- 实现侧可扩展更多状态码，但不得改变已定义状态码的语义与数值约束。
- `Status` 表示 API 调用结果；失败时输出参数内容不做保证。
- `Vector` 仅表达统一的坐标/索引序列，不承担 `shape/stride/rank` 之外的业务语义。
- `Vector(data, size)` 是调用方缓冲区视图，不承担底层存储所有权。
- `Vector{...}` 是自有内联存储对象，`data()` 在该 `Vector` 对象生命周期内有效。
- 公共层只允许暴露 `Vector`；`std::vector<long long>`、`std::array<long long, N>`、裸数组类型名或后端私有坐标容器都不属于本轮稳定公开口径。
- `Core` 不定义 `view`、`reshape`、`slice`、`deslice` 的职责，也不承接 `Memory`/`Dma` 的旧别名接口。
- `include/api/Core.h` 仅提供声明与类型边界，不提供函数体实现；具体后端实现由各自 include 层提供。

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

- `Status` 以 `StatusCode` 为最小语义集合；实现可定义为 `int` 或 `enum`，但需保证与 `StatusCode` 可互换。

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
long long coords_buf[3] = {5, 0, 7};
Vector coords(coords_buf, 3);
unsigned long long n = coords.size();
long long first = coords[0];
```

注意事项：

- `Vector(data, size)` 只封装调用方提供的连续 `int64` 缓冲区，不复制、不分配、不释放底层数据。
- `Vector{...}` 将 1..4 个 `long long` 值复制到对象内联存储，不使用动态分配。
- `Vector` 不依赖标准库容器、标准库数组包装或初始化列表。
- `Vector` 的公开职责是表达“坐标/索引序列”；不得把 `shape/stride/rank` 元信息重新塞入该类型。

返回与限制：

- 返回类型：`Vector`。
- 返回语义：封装调用方提供的连续元素缓冲区及其长度。
- 限制条件：不承担所有权，不提供动态扩容，不定义标准库容器互转接口。

### `Vector{...}`

功能说明：

- 使用 1..4 个 `long long` 固定参数构造 `Vector`。
- 构造时把输入值复制到 `Vector` 自身内联存储，避免引用临时数据。

参数说明：

- `value0..value3 (long long)`：坐标/shape/stride/offset 值；支持 1、2、3、4 个参数。

使用示例：

```cpp
Vector one{16};
Vector shape{2, 3};
Vector dims = {2, 3, 4};
Vector full{1, 2, 3, 4};
```

注意事项：

- `Vector{...}` 的 `data()` 在该 `Vector` 对象生命周期内有效。
- 超过 4 个值不属于合法公开调用。
- 不得通过 `<initializer_list>`、`std::initializer_list`、标准库容器、标准库数组包装、动态分配或动态扩容实现该语法。
- `Vector(data, size)` 的外部缓冲区视图语义保持不变。

返回与限制：

- 返回类型：`Vector`。
- 返回语义：返回一个长度为输入值个数的轻量向量对象。
- 限制条件：最多 4 个元素，不提供动态扩容，不定义标准库容器互转接口。

### `Vector(data, size)`

功能说明：

- 使用调用方提供的连续 `int64` 缓冲区与元素个数构造 `Vector` 视图。

参数说明：

- `data (long long*)` 或 `data (const long long*)`：底层连续元素缓冲区首地址。
- `size (unsigned long long)`：元素个数。

使用示例：

```cpp
long long coords_buf[4] = {0, 1, 2, 3};
Vector coords(coords_buf, 4);
```

注意事项：

- 当 `size == 0` 时允许 `data == nullptr`。
- 当 `size > 0` 时，调用方需保证 `data` 指向至少 `size` 个连续元素。

返回与限制：

- 返回类型：`Vector`。
- 返回语义：返回一个长度为 `size` 的轻量向量视图。
- 限制条件：非法指针与越界访问属于调用方违约；本规范不要求异常机制。

### `size()`

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

### `data()`

功能说明：

- 返回底层连续元素缓冲区首地址。

参数说明：

- 无参数。

使用示例：

```cpp
const long long* raw = coords.data();
```

注意事项：

- 允许提供可写和只读两类重载，具体由实现侧决定，但公开语义必须等价。

返回与限制：

- 返回类型：`long long*` 或 `const long long*`。
- 返回语义：返回底层连续元素缓冲区首地址。
- 限制条件：不检查空指针。

### `operator[](index)`

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

- 返回类型：`long long&` 或 `const long long&`。
- 返回语义：返回第 `index` 个元素。
- 限制条件：越界访问属于调用方违约。

## 测试

- 测试文件：[`test/include/api/test_core.py`](../../../test/include/api/test_core.py)
- 执行命令：`pytest -q test/include/api/test_core.py`
- 测试目标：
  - 验证 `StatusCode::kOk == 0` 的公共语义不变。
  - 验证 `Vector` 的最小构造、`size()`、`data()`、`operator[]` 接口可由后端实现承接。
  - 验证 `Vector{...}` 与 `Vector values = {...}` 支持 1..4 个值，且内部值在对象生命周期内可通过 `data()` 与 `operator[]` 读取。
  - 验证公共层不再把其他坐标容器写成稳定接口。
- 功能与用例清单：
  - `API-CORE-001`：`Vector` 的最小构造与索引读取可工作。
  - `API-CORE-002`：`Vector{...}` 与拷贝/赋值路径保持内联存储有效。
