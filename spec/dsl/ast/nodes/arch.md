# DSL AST Arch 节点

## 功能简介

- `kernel_gen.dsl.ast.nodes.arch` 定义 arch helper 对应 AST 节点。
- Arch 查询每个 operation 对应唯一 AST 节点；launch 使用四字段 ABI：`block`、`thread`、`subthread`、`shared_memory_size`。

## API 列表

- `class ArchQueryAST(location: SourceLocation | None = None)`
- `class ArchGetBlockIdAST(location: SourceLocation | None = None)`
- `class ArchGetBlockNumAST(location: SourceLocation | None = None)`
- `class ArchGetSubthreadIdAST(location: SourceLocation | None = None)`
- `class ArchGetSubthreadNumAST(location: SourceLocation | None = None)`
- `class ArchGetThreadIdAST(location: SourceLocation | None = None)`
- `class ArchGetThreadNumAST(location: SourceLocation | None = None)`
- `class ArchGetDynamicMemoryAST(space: MemorySpaceAttrAST, location: SourceLocation | None = None)`
- `class ArchBarrierAST(visibility: list[PythonObjectAttrAST], scope: PythonObjectAttrAST, location: SourceLocation | None = None)`
- `class ArchLaunchKernelAST(callee: FunctionAST | PythonObjectAttrAST, block: SymbolDimAST | ConstValueAST, thread: SymbolDimAST | ConstValueAST, subthread: SymbolDimAST | ConstValueAST, args: list[ValueAST] = ..., shared_memory_size: SymbolDimAST | ConstValueAST = ..., location: SourceLocation | None = None)`

## 文档信息

- 创建者：`榕`
- 最后一次更改：`榕`
- `spec`：`spec/dsl/ast/nodes/arch.md`
- `功能实现`：`kernel_gen/dsl/ast/nodes/arch.py`
- `test`：`test/dsl/ast/nodes/test_arch.py`

## 依赖

- `spec/dsl/ast/nodes/basic.md`：`ValueAST`、`StatementAST`、`FunctionAST`。
- `spec/dsl/ast/nodes/symbol.md`：`SymbolDimAST`、`ConstValueAST`。
- `spec/dsl/ast/nodes/attr.md`：`MemorySpaceAttrAST` 与 `PythonObjectAttrAST`。
- `kernel_gen.dialect.arch`：最终发射的 arch dialect op。

## API详细说明

### `class ArchQueryAST(location: SourceLocation | None = None)`

- api：`class ArchQueryAST(location: SourceLocation | None = None)`
- 参数：
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = ArchQueryAST(location=location)
    ```
- 功能说明：执行 `ArchQueryAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class ArchGetBlockIdAST(location: SourceLocation | None = None)`

- api：`class ArchGetBlockIdAST(location: SourceLocation | None = None)`
- 参数：
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = ArchGetBlockIdAST(location=location)
    ```
- 功能说明：执行 `ArchGetBlockIdAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class ArchGetBlockNumAST(location: SourceLocation | None = None)`

- api：`class ArchGetBlockNumAST(location: SourceLocation | None = None)`
- 参数：
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = ArchGetBlockNumAST(location=location)
    ```
- 功能说明：执行 `ArchGetBlockNumAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class ArchGetSubthreadIdAST(location: SourceLocation | None = None)`

- api：`class ArchGetSubthreadIdAST(location: SourceLocation | None = None)`
- 参数：
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = ArchGetSubthreadIdAST(location=location)
    ```
- 功能说明：执行 `ArchGetSubthreadIdAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class ArchGetSubthreadNumAST(location: SourceLocation | None = None)`

- api：`class ArchGetSubthreadNumAST(location: SourceLocation | None = None)`
- 参数：
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = ArchGetSubthreadNumAST(location=location)
    ```
- 功能说明：执行 `ArchGetSubthreadNumAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class ArchGetThreadIdAST(location: SourceLocation | None = None)`

- api：`class ArchGetThreadIdAST(location: SourceLocation | None = None)`
- 参数：
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = ArchGetThreadIdAST(location=location)
    ```
- 功能说明：执行 `ArchGetThreadIdAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class ArchGetThreadNumAST(location: SourceLocation | None = None)`

- api：`class ArchGetThreadNumAST(location: SourceLocation | None = None)`
- 参数：
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = ArchGetThreadNumAST(location=location)
    ```
- 功能说明：执行 `ArchGetThreadNumAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class ArchGetDynamicMemoryAST(space: MemorySpaceAttrAST, location: SourceLocation | None = None)`

- api：`class ArchGetDynamicMemoryAST(space: MemorySpaceAttrAST, location: SourceLocation | None = None)`
- 参数：
  - `space`：内存空间；类型 `MemorySpaceAttrAST`；无默认值；传入时必须是公开 MemorySpace 或 MemorySpaceAttrAST。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = ArchGetDynamicMemoryAST(space=space, location=location)
    ```
- 功能说明：执行 `ArchGetDynamicMemoryAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class ArchBarrierAST(visibility: list[PythonObjectAttrAST], scope: PythonObjectAttrAST, location: SourceLocation | None = None)`

- api：`class ArchBarrierAST(visibility: list[PythonObjectAttrAST], scope: PythonObjectAttrAST, location: SourceLocation | None = None)`
- 参数：
  - `visibility`：barrier 可见性列表；类型 `list[PythonObjectAttrAST]`；无默认值；不允许 None；元素必须是公开 PythonObjectAttrAST。
  - `scope`：barrier scope；类型 `PythonObjectAttrAST`；无默认值；不允许 None；必须是公开 PythonObjectAttrAST。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = ArchBarrierAST(visibility=visibility, scope=scope, location=location)
    ```
- 功能说明：执行 `ArchBarrierAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

### `class ArchLaunchKernelAST(callee: FunctionAST | PythonObjectAttrAST, block: SymbolDimAST | ConstValueAST, thread: SymbolDimAST | ConstValueAST, subthread: SymbolDimAST | ConstValueAST, args: list[ValueAST] = ..., shared_memory_size: SymbolDimAST | ConstValueAST = ..., location: SourceLocation | None = None)`

- api：`class ArchLaunchKernelAST(callee: FunctionAST | PythonObjectAttrAST, block: SymbolDimAST | ConstValueAST, thread: SymbolDimAST | ConstValueAST, subthread: SymbolDimAST | ConstValueAST, args: list[ValueAST] = ..., shared_memory_size: SymbolDimAST | ConstValueAST = ..., location: SourceLocation | None = None)`
- 参数：
  - `callee`：被调用函数或函数属性；类型 `FunctionAST | PythonObjectAttrAST`；无默认值；不允许 None。
  - `block`：block 数表达式或目标 block；类型 `SymbolDimAST | ConstValueAST`；无默认值；调用方必须按具体 API 语义传入。
  - `thread`：线程数表达式；类型 `SymbolDimAST | ConstValueAST`；无默认值；不允许 None。
  - `subthread`：subthread 数表达式；类型 `SymbolDimAST | ConstValueAST`；无默认值；不允许 None。
  - `args`：调用参数列表；类型 `list[ValueAST]`；默认值 `...`；列表元素必须是公开 AST value 节点。
  - `shared_memory_size`：共享内存大小；类型 `SymbolDimAST | ConstValueAST`；默认值 `...`；必须是符号或常量维度节点。
  - `location`：源码位置；类型 `SourceLocation | None`；默认值 `None`；None 表示没有显式诊断位置。
- 返回值：公开对象；具体类型由签名声明。
- 使用示例：

  ```python
    result = ArchLaunchKernelAST(callee=callee, block=block, thread=thread, subthread=subthread, args=args, shared_memory_size=shared_memory_size, location=location)
    ```
- 功能说明：执行 `ArchLaunchKernelAST`，把 DSL AST 节点转换为公开 MLIR/IR 结果或读取节点公开属性。
- 注意事项：构造参数必须是公开 AST 节点、公开 symbol/memory 类型或签名声明的 Python 基础值；不得传入内部 visitor/helper 状态。

## 测试

- 测试文件：`test/dsl/ast/nodes/test_arch.py`
- 执行命令：`pytest -q test/dsl/ast/nodes/test_arch.py`

### 测试目标

- arch 查询、dynamic memory、barrier、launch ABI。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-DSL-AST-NODES-ARCH-001 | 边界/异常 | arch query base node rejects direct emit | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_arch_query_base_node_rejects_direct_emit`。 | “arch query base node rejects direct emit”场景按公开错误语义失败或被拒绝。 | `test_arch_query_base_node_rejects_direct_emit` |
| TC-DSL-AST-NODES-ARCH-002 | 生成/编译 | arch get thread num emits specific query op | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_arch_get_thread_num_emits_specific_query_op`。 | 生成源码、IR 文本或编译结果体现“arch get thread num emits specific query op”场景。 | `test_arch_get_thread_num_emits_specific_query_op` |
| TC-DSL-AST-NODES-ARCH-003 | 生成/编译 | arch dynamic memory uses space attr node emit | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_arch_dynamic_memory_uses_space_attr_node_emit`。 | 生成源码、IR 文本或编译结果体现“arch dynamic memory uses space attr node emit”场景。 | `test_arch_dynamic_memory_uses_space_attr_node_emit` |
| TC-DSL-AST-NODES-ARCH-004 | 生成/编译 | arch query nodes emit specific public ops | 准备所有公开 arch 查询 AST 节点。 | 运行 `test_arch_query_nodes_emit_specific_public_ops`。 | 每个查询节点通过公开 `emit_mlir` 发射对应 arch dialect op。 | `test_arch_query_nodes_emit_specific_public_ops` |
| TC-DSL-AST-NODES-ARCH-005 | 生成/编译 | arch dynamic memory emits all on-chip spaces | 准备 spec 定义的片上 MemorySpace。 | 运行 `test_arch_dynamic_memory_emits_all_on_chip_spaces`。 | 每个片上空间生成对应 `arch.get_dynamic_memory`，结果类型携带匹配空间与容量符号。 | `test_arch_dynamic_memory_emits_all_on_chip_spaces` |
| TC-DSL-AST-NODES-ARCH-006 | 边界/异常 | arch dynamic memory rejects global space | 准备 GM 空间作为非法 dynamic memory 输入。 | 运行 `test_arch_dynamic_memory_rejects_global_space`。 | 公开错误语义拒绝非片上 GM 空间。 | `test_arch_dynamic_memory_rejects_global_space` |
| TC-DSL-AST-NODES-ARCH-007 | 边界/异常 | arch barrier emits and rejects public attrs | 准备公开 barrier scope/visibility enum 与非法枚举替代值。 | 运行 `test_arch_barrier_emits_and_rejects_public_attrs`。 | 合法 enum 发射 `arch.barrier`；非法 scope/visibility 按公开错误语义拒绝。 | `test_arch_barrier_emits_and_rejects_public_attrs` |
| TC-DSL-AST-NODES-ARCH-008 | 生成/编译 | arch launch kernel emits public ABI with args | 准备公开 callee、四字段 launch ABI 与公开 ValueAST args。 | 运行 `test_arch_launch_kernel_emits_public_abi_with_args`。 | 发射 `arch.launch_kernel`，callee 与 args 可通过公开 op 属性/result 检查。 | `test_arch_launch_kernel_emits_public_abi_with_args` |
| TC-DSL-AST-NODES-ARCH-009 | 边界/异常 | arch launch kernel rejects arg without SSA value | 准备不能 lower 成 SSA value 的公开 ValueAST。 | 运行 `test_arch_launch_kernel_rejects_arg_without_ssa_value`。 | 公开错误语义拒绝不能生成 SSA value 的 launch arg。 | `test_arch_launch_kernel_rejects_arg_without_ssa_value` |
