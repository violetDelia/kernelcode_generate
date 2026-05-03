# Core

## 功能简介

定义 include/api 层统一对外的基础类型与返回状态规范（`include/api/Core.h`），为 `Memory`、`Dma`、后端 helper 与代码生成层提供统一的状态码语义与最小基础类型边界。

- 本轮公共层只收口 `StatusCode`、`Status`、`S_INT`、`Vector` 四个公开名字。
- `Vector` 是轻量只读/可写视图；也支持 1..4 个 `long long` 值的花括号构造，并把这些值复制到对象内联存储。
- `Vector` 不做动态分配，不依赖初始化列表或标准库容器。
- `Core` 不定义 `view`、`reshape`、`slice`、`deslice` 等业务 helper。

## API 列表

- `enum StatusCode { kOk: int = 0, kError: int = 1 }`
- `Status: type alias = StatusCode`
- `S_INT: type alias = long long`
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

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
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

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 本规范仅定义状态类型、状态码语义与基础向量类型，不定义日志、异常、诊断对象或错误信息格式。
- 实现侧可扩展更多状态码，但不得改变已定义状态码的语义与数值约束。
- `Status` 表示 API 调用结果；失败时输出参数内容不做保证。
- `Vector` 仅表达统一的坐标/索引序列，不承担 `shape/stride/rank` 之外的业务语义。
- `Vector(data, size)` 是调用方缓冲区视图，不承担底层存储所有权。
- `Vector{...}` 是自有内联存储对象，`data()` 在该 `Vector` 对象生命周期内有效。
- 公共层只允许暴露 `Vector`；`std::vector<long long>`、`std::array<long long, N>`、裸数组类型名或后端私有坐标容器都不属于本轮稳定公开口径。
- `Core` 不定义 `view`、`reshape`、`slice`、`deslice` 的职责，也不保留 `Memory`/`Dma` 的旧别名接口。
- `include/api/Core.h` 仅提供声明与类型边界，不提供函数体实现；具体后端实现由各自 include 层提供。

## API详细说明

### `enum StatusCode { kOk: int = 0, kError: int = 1 }`

- api：`enum StatusCode { kOk: int = 0, kError: int = 1 }`
- 参数：无。
- 返回值：公开枚举类型对象。
- 使用示例：

  ```cpp
StatusCode code = StatusCode::kOk;
```
- 功能说明：定义统一返回状态码枚举，`kOk` 表示成功，`kError` 表示失败。
- 注意事项：`kOk` 的数值必须保持为 `0`，`kError` 的数值必须保持为 `1`；实现侧可扩展更多状态码，但不得改变已定义状态码的语义与数值。

### `Status: type alias = StatusCode`

- api：`Status: type alias = StatusCode`
- 参数：无。
- 返回值：公开类型别名。
- 使用示例：

  ```cpp
Status status = StatusCode::kOk;
```
- 功能说明：定义统一 API 返回状态类型别名。
- 注意事项：`Status` 必须与 `StatusCode` 可互换；`StatusCode::kOk` 表示成功，其他状态码表示失败。

### `S_INT: type alias = long long`

- api：`S_INT: type alias = long long`
- 参数：无。
- 返回值：公开类型别名。
- 使用示例：

  ```cpp
S_INT dim = 16;
```
- 功能说明：定义统一符号整数类型别名，供动态 shape 与 symbol 参数复用。
- 注意事项：`S_INT` 的公开语义是有符号 64 位整数；不得把后端私有整数别名或平台相关窄整数写成该接口的替代合同。

### `class Vector`

- api：`class Vector`
- 参数：无。
- 返回值：`Vector` 实例。
- 使用示例：

  ```cpp
Vector dims{2, 3, 4};
```
- 功能说明：定义 `Vector` 公开类型。
- 注意事项：`Vector` 固定表达 `long long` 坐标/索引序列；不得把 `shape/stride/rank` 元信息或标准库容器互转能力作为该类型的公开合同。

### `Vector::Vector(long long* data, unsigned long long size)`

- api：`Vector::Vector(long long* data, unsigned long long size)`
- 参数：
  - `data`：输入数据或缓冲区内容；类型 `long long*`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `size`：尺寸序列或元素数量，指定切片、缓冲区或范围的大小；类型 `unsigned long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Vector` 实例。
- 使用示例：

  ```cpp
long long data[2] = {1, 2};
Vector shape(data, 2);
```
- 功能说明：构造 `Vector` 实例。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `Vector::Vector(const long long* data, unsigned long long size)`

- api：`Vector::Vector(const long long* data, unsigned long long size)`
- 参数：
  - `data`：输入数据或缓冲区内容；类型 `const long long*`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `size`：尺寸序列或元素数量，指定切片、缓冲区或范围的大小；类型 `unsigned long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Vector` 实例。
- 使用示例：

  ```cpp
long long data[2] = {1, 2};
Vector shape(data, 2);
```
- 功能说明：构造 `Vector` 实例。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `Vector::Vector(long long value0)`

- api：`Vector::Vector(long long value0)`
- 参数：
  - `value0`：`value0` 输入值，参与 `Vector` 的公开处理流程；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Vector` 实例。
- 使用示例：

  ```cpp
long long data[2] = {1, 2};
Vector shape(data, 2);
```
- 功能说明：构造 `Vector` 实例。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `Vector::Vector(long long value0, long long value1)`

- api：`Vector::Vector(long long value0, long long value1)`
- 参数：
  - `value0`：`value0` 输入值，参与 `Vector` 的公开处理流程；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `value1`：`value1` 输入值，参与 `Vector` 的公开处理流程；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Vector` 实例。
- 使用示例：

  ```cpp
long long data[2] = {1, 2};
Vector shape(data, 2);
```
- 功能说明：构造 `Vector` 实例。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `Vector::Vector(long long value0, long long value1, long long value2)`

- api：`Vector::Vector(long long value0, long long value1, long long value2)`
- 参数：
  - `value0`：`value0` 输入值，参与 `Vector` 的公开处理流程；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `value1`：`value1` 输入值，参与 `Vector` 的公开处理流程；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `value2`：`value2` 输入值，参与 `Vector` 的公开处理流程；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Vector` 实例。
- 使用示例：

  ```cpp
long long data[2] = {1, 2};
Vector shape(data, 2);
```
- 功能说明：构造 `Vector` 实例。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `Vector::Vector(long long value0, long long value1, long long value2, long long value3)`

- api：`Vector::Vector(long long value0, long long value1, long long value2, long long value3)`
- 参数：
  - `value0`：`value0` 输入值，参与 `Vector` 的公开处理流程；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `value1`：`value1` 输入值，参与 `Vector` 的公开处理流程；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `value2`：`value2` 输入值，参与 `Vector` 的公开处理流程；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `value3`：`value3` 输入值，参与 `Vector` 的公开处理流程；类型 `long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Vector` 实例。
- 使用示例：

  ```cpp
long long data[2] = {1, 2};
Vector shape(data, 2);
```
- 功能说明：构造 `Vector` 实例。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `Vector::Vector(const Vector& other)`

- api：`Vector::Vector(const Vector& other)`
- 参数：
  - `other`：另一侧操作数或比较对象，用于和当前对象组合、比较或广播；类型 `const Vector&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Vector` 实例。
- 使用示例：

  ```cpp
long long data[2] = {1, 2};
Vector shape(data, 2);
```
- 功能说明：构造 `Vector` 实例。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `Vector::operator=(const Vector& other) -> Vector&`

- api：`Vector::operator=(const Vector& other) -> Vector&`
- 参数：
  - `other`：另一侧操作数或比较对象，用于和当前对象组合、比较或广播；类型 `const Vector&`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Vector&`。
- 使用示例：

  ```cpp
// 使用公开 C++ include API：Vector::operator=(const Vector& other) -> Vector&
```
- 功能说明：执行 `operator=`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `Vector::size() const -> unsigned long long`

- api：`Vector::size() const -> unsigned long long`
- 参数：无。
- 返回值：`unsigned long long`。
- 使用示例：

  ```cpp
auto size = vector.size();
```
- 功能说明：执行 `size`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `Vector::data() -> long long*`

- api：`Vector::data() -> long long*`
- 参数：无。
- 返回值：`long long*`。
- 使用示例：

  ```cpp
auto* data = vector.data();
```
- 功能说明：执行 `data`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `Vector::data() const -> const long long*`

- api：`Vector::data() const -> const long long*`
- 参数：无。
- 返回值：`const long long*`。
- 使用示例：

  ```cpp
auto* data = vector.data();
```
- 功能说明：执行 `data`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `Vector::operator[](unsigned long long index) -> long long&`

- api：`Vector::operator[](unsigned long long index) -> long long&`
- 参数：
  - `index`：`index` 输入值，参与 `operator[]` 的公开处理流程；类型 `unsigned long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`long long&`。
- 使用示例：

  ```cpp
auto value = vector[0];
```
- 功能说明：执行 `operator[]`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `Vector::operator[](unsigned long long index) const -> const long long&`

- api：`Vector::operator[](unsigned long long index) const -> const long long&`
- 参数：
  - `index`：`index` 输入值，参与 `operator[]` 的公开处理流程；类型 `unsigned long long`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`const long long&`。
- 使用示例：

  ```cpp
auto value = vector[0];
```
- 功能说明：执行 `operator[]`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

## 测试

- 测试文件：`test/include/api/test_core.py`
- 执行命令：`pytest -q test/include/api/test_core.py`

### 测试目标

- 验证 `spec/include/api/Core.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证公开导入、注册名、CLI 或命名空间入口只暴露 spec 定义的 API。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-INCLUDE-API-CORE-001 | 公开入口 | `Vector` 的最小构造与索引读取可工作。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `API-CORE-001`。 | 公开入口在“`Vector` 的最小构造与索引读取可工作。”场景下可导入、构造、注册或按名称发现。 | `API-CORE-001` |
| TC-INCLUDE-API-CORE-002 | 公开入口 | `Vector{...}` 与拷贝/赋值路径保持内联存储有效。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `API-CORE-002`。 | 公开入口在“`Vector{...}` 与拷贝/赋值路径保持内联存储有效。”场景下可导入、构造、注册或按名称发现。 | `API-CORE-002` |
