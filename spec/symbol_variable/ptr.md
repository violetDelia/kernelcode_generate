# ptr.md

## 功能简介

用于冻结 Python 上层 `class Ptr` 的公开语义。`Ptr` 是一个仅承载 pointee dtype 的类型对象，面向 DSL 函数输入注解与 runtime args 传入场景。当前稳定入口是子模块 `kernel_gen.symbol_variable.ptr`，不由包入口 `kernel_gen.symbol_variable` 直接重导出。

## API 列表

- `class Ptr(dtype: Attribute)`
  - `dtype: Attribute`
  - `__init__(*dtype: Attribute) -> None`
  - `__repr__() -> str`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/symbol_variable/ptr.md`](../../spec/symbol_variable/ptr.md)
- `test`：[`test/symbol_variable/test_ptr.py`](../../test/symbol_variable/test_ptr.py)
- `功能实现`：[`kernel_gen/symbol_variable/ptr.py`](../../kernel_gen/symbol_variable/ptr.py)

## 依赖

- [`ARCHITECTURE/plan/ptr_symbol_func_input_plan.md`](../../ARCHITECTURE/plan/ptr_symbol_func_input_plan.md)：P1 任务来源与边界定义。
- [`spec/symbol_variable/__init__.md`](../../spec/symbol_variable/__init__.md)：包入口导出边界；当前明确 `Ptr` 不在包入口重导出集合中。
- [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)：用于明确 `Ptr` 与 `Memory` 的职责边界。
- [`spec/symbol_variable/symbol_dim.md`](../../spec/symbol_variable/symbol_dim.md)：用于明确 `Ptr` 与 `SymbolDim` 的职责边界。

## 目标

- 定义上层 `class Ptr` 的最小稳定语义：`Ptr(dtype)`。
- 明确当前稳定导入方式是 `from kernel_gen.symbol_variable.ptr import Ptr`。
- 明确 `Ptr` 只表示 pointee dtype，不带名字。
- 明确 `Ptr` 的构造参数约束与失败边界（缺参、多参）。
- 明确 `Ptr` 不是 `Memory`，也不是 `SymbolDim`，三者无别名关系。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 本文件只定义 Python 上层 `Ptr` 对象，不定义 IR 文本（例如 `!symbol.ptr<...>`）。
- 不定义包入口是否重导出 `Ptr` 以外的包级导出策略；这部分由 [`spec/symbol_variable/__init__.md`](../../spec/symbol_variable/__init__.md) 负责。
- 本文件不定义 DSL AST、lowering、codegen、runtime/include、审查或复审规则。

## API详细说明

### `class Ptr(dtype: Attribute)`

- api：`class Ptr(dtype: Attribute)`
- 参数：
  - `dtype`：数据类型，定义张量、内存或符号对象的元素类型；类型 `Attribute`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`Ptr` 实例。
- 使用示例：

  ```python
  from kernel_gen.symbol_variable.ptr import Ptr
  from xdsl.dialects.builtin import f32

  ptr = Ptr(f32)
  ```
- 功能说明：表示“指向某个 element dtype 的指针类型对象”。
- 注意事项：公开稳定调用方式为 `Ptr(dtype)` 的位置参数形式；`Ptr` 只承载 pointee dtype，不承载地址名、地址值、shape 或 stride；`Ptr` 不是 `Memory`，也不是 `SymbolDim`。

### `dtype: Attribute`

- api：`dtype: Attribute`
- 参数：无。
- 返回值：`Attribute`，构造时传入的唯一 pointee dtype 对象。
- 使用示例：

  ```python
  from kernel_gen.symbol_variable.ptr import Ptr
  from xdsl.dialects.builtin import f32

  ptr = Ptr(f32)
  assert ptr.dtype is f32
  ```
- 功能说明：读取当前 `Ptr` 实例承载的 pointee dtype。
- 注意事项：`dtype` 只表示 pointee element dtype；不承载名字、shape、stride 或地址值。

### `__init__(*dtype: Attribute) -> None`

- api：`__init__(*dtype: Attribute) -> None`
- 参数：
  - `dtype`：数据类型，定义张量、内存或符号对象的元素类型；类型 `Attribute`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  from kernel_gen.symbol_variable.ptr import Ptr
  from xdsl.dialects.builtin import f32

  ptr = Ptr(f32)
  ```
- 功能说明：初始化 `Ptr(dtype)` 并校验参数数量。
- 注意事项：该特殊方法只通过 `Ptr(...)` 构造入口承接 Python 协议语义；仅允许 1 个 dtype 参数；`Ptr()` 与 `Ptr(f32, f32)` 必须抛 `TypeError`，消息包含 `Ptr requires exactly one dtype`。

### `__repr__() -> str`

- api：`__repr__() -> str`
- 参数：无。
- 返回值：`str`，表示生成或格式化后的文本。
- 使用示例：

  ```python
  from kernel_gen.symbol_variable.ptr import Ptr
  from xdsl.dialects.builtin import f32

  assert repr(Ptr(f32)) == "Ptr(f32)"
  ```
- 功能说明：返回稳定公开文本 `Ptr(<dtype>)`。
- 注意事项：该特殊方法只承接 Python 对应协议语义；使用 `str(dtype)` 保持 `f32` 等 xDSL 类型文本稳定。

## 测试

- 测试文件：`test/symbol_variable/test_ptr.py`
- 执行命令：`pytest -q test/symbol_variable/test_ptr.py`

### 测试目标

- `test_ptr_preserves_pointee_dtype`：
- 输入：`ptr = Ptr(f32)`。
- 预期输出：公开文本可表达 `Ptr(f32)`，且 pointee dtype 为 `f32`。
- `test_ptr_rejects_missing_dtype`：
- 输入：`Ptr()`。
- 预期输出：抛 `TypeError`，消息包含 `Ptr requires exactly one dtype`。
- `test_ptr_rejects_extra_args`：
- 输入：`Ptr(f32, f32)`。
- `test_ptr_is_not_memory_or_symbol_dim`：
- 输入：`Ptr(f32)` 与 `Memory(...)` / `SymbolDim("N")`。
- 预期输出：文档明确三者不是同类，不存在公开别名关系。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-SYMBOL-VARIABLE-PTR-001 | 公开入口 | ptr preserves pointee dtype | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_ptr_preserves_pointee_dtype`。 | 公开入口在“ptr preserves pointee dtype”场景下可导入、构造、注册或按名称发现。 | `test_ptr_preserves_pointee_dtype` |
| TC-SYMBOL-VARIABLE-PTR-002 | 边界/异常 | ptr rejects missing dtype | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_ptr_rejects_missing_dtype`。 | “ptr rejects missing dtype”场景按公开错误语义失败或被拒绝。 | `test_ptr_rejects_missing_dtype` |
| TC-SYMBOL-VARIABLE-PTR-003 | 边界/异常 | ptr rejects extra args | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_ptr_rejects_extra_args`。 | “ptr rejects extra args”场景按公开错误语义失败或被拒绝。 | `test_ptr_rejects_extra_args` |
| TC-SYMBOL-VARIABLE-PTR-004 | 内存/DMA | ptr is not memory or symbol dim | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_ptr_is_not_memory_or_symbol_dim`。 | 内存类型、布局、搬运结果或 verifier 行为体现“ptr is not memory or symbol dim”场景。 | `test_ptr_is_not_memory_or_symbol_dim` |
