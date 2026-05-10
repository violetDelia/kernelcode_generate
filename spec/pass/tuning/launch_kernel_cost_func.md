# launch_kernel_cost_func.md

## 功能简介

- 定义 standalone tuning pass `launch-kernel-cost-func` 的公开 API、输入域和输出 IR 形态。
- 该 pass 从已有 `arch.launch -> device func` 关系生成 sibling cost host function，用 `tuner.cost` 表示 device body 内受支持 op 的局部成本，并把全部局部 `!symbol.int` 成本通过 `symbol.add` 累计后返回单个 `!symbol.int` 总值。
- 当前公开方向固定为七值 kind：`DMA1|DMA2|DMA3|DMA4|MAC|VECTOR1|VECTOR2`；`cost_kind` 只接受该集合的非空去重子集。

## API 列表

- `class LaunchKernelCostFuncPass(cost_kind: str = "DMA1|DMA2|DMA3|DMA4|MAC|VECTOR1|VECTOR2", fold: bool = True)`
  - `name: str`
  - `cost_kind: str`
  - `__init__(cost_kind: str = "DMA1|DMA2|DMA3|DMA4|MAC|VECTOR1|VECTOR2", fold: bool = True) -> None`
  - `from_options(options: dict[str, str]) -> LaunchKernelCostFuncPass`
  - `apply(ctx: Context, module: ModuleOp) -> None`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/pass/tuning/launch_kernel_cost_func.md`](../../../spec/pass/tuning/launch_kernel_cost_func.md)
- `功能实现`：
  - [`kernel_gen/passes/tuning/launch_kernel_cost_func.py`](../../../kernel_gen/passes/tuning/launch_kernel_cost_func.py)
  - [`kernel_gen/passes/tuning/__init__.py`](../../../kernel_gen/passes/tuning/__init__.py)
  - [`kernel_gen/passes/registry.py`](../../../kernel_gen/passes/registry.py)
- `test`：
  - [`test/passes/tuning/test_launch_kernel_cost_func.py`](../../../test/passes/tuning/test_launch_kernel_cost_func.py)
  - [`test/passes/test_registry.py`](../../../test/passes/test_registry.py)
  - [`test/dialect/test_tuner.py`](../../../test/dialect/test_tuner.py)

## 依赖

- Pass 抽象与管理器：[`spec/pass/pass_manager.md`](../pass_manager.md)
- Pass 注册表：[`spec/pass/registry.md`](../registry.md)
- `arch.launch` 输入形状：[`spec/dialect/arch.md`](../../dialect/arch.md)
- `symbol.for` loop-carried `!symbol.int`：[`spec/dialect/symbol.md`](../../dialect/symbol.md)
- `tuner.cost` 局部成本节点：[`spec/dialect/tuner.md`](../../dialect/tuner.md)
- host launch outline 前置形状：[`spec/pass/outline_device_kernel.md`](../outline_device_kernel.md)

## 术语

- `host wrapper`：包含 `arch.launch` 的 host 侧函数。
- `device func`：`arch.launch` 通过 callee symbol 指向的 device 函数。
- `cost function`：本 pass 新增的 sibling host function，名称形如 `@_cost_<cost_kind>_<device_func_name>`，参数与 device func 一致，返回单个 `!symbol.int`。
- `cost_kind`：当前 cost function 的统计视角；本轮只接受 `DMA1/DMA2/DMA3/DMA4/MAC/VECTOR1/VECTOR2` 的非空、`|` 分隔且去重后的 kind 名列表。

## 目标

- 固定 pass 名称：`launch-kernel-cost-func`。
- 固定公开入口：`LaunchKernelCostFuncPass(cost_kind="DMA1|MAC|VECTOR1")` 与 `build_registered_pass("launch-kernel-cost-func", {"cost_kind": ...})`。
- 固定默认 kind：未显式传入 `cost_kind` 时使用 `DMA1|DMA2|DMA3|DMA4|MAC|VECTOR1|VECTOR2`。
- 固定输出：每个 unique device callee 对请求列表中的每个 `cost_kind` 生成一份 cost function。
- 固定 cost function 返回语义：全部 `tuner.cost(...)->!symbol.int` 必须进入 `symbol.add` 累计链，最终 `func.return` 返回单个总值。
- 保持 helper 保留规则：`arch.get_dynamic_memory`、`builtin.unrealized_conversion_cast`、`dma.view`、`dma.subview`、`dma.reshape` 与 `dma.alloc` 必须保留到 cost function，但不下沉 `tuner.cost`。
- `dma.store` 是写回方向成本节点，生成 `tuner.cost(op_name="dma.store")` 并由 emit 侧复用 `cost::deslice` 公开 helper；`dma.load` / `dma.free` / `dma.broadcast` / `dma.fill` / `dma.cast` / `dma.transpose` 暂无公开 cost helper，本 pass 在 cost function 中直接跳过，不生成 `tuner.cost` 或运行时 side effect。
- `kernel.binary_elewise.kind` 与 `kernel.reduce.kind` 是原业务 op 的算法类别，不是 cost metadata；生成 `tuner.cost` 时必须改名为 `kernel_kind` 保留，避免重新引入旧公开 attr `kind`。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 本 pass 是 standalone tuning pass，同时作为 `npu-demo-lowering` 的末尾 pass 运行；不自动进入 `default-lowering`。
- 输入必须已经存在 `arch.launch`，且 callee symbol 可解析到 module 内的 device `func.func`。
- 原 host wrapper 与原 device func 必须保持不变；本 pass 只新增 sibling cost function。
- 本 pass 不做 target runtime 求值、不查 cost table、不把 `tuner.cost` 折叠为常量。
- `cost_kind` 只接受七值集合的非空去重子集；空串、全空白串、空段、重复段和旧 `compute/memory/DMA` kind 都必须显式失败。
- 本任务不修改 `expectation/`；当前 spec/pytest/实现以新七值 kind 为公开真源，旧 `compute / memory` expectation 入口只作为历史资产背景，不作为本轮 diff 证明。
- 若输入 module 已存在目标命名规则对应的 cost function，必须显式失败，不得覆盖或复用。
- 当前文件不公开 helper 函数、helper 类或可跨文件复用的 rewrite 入口；device 收集、`symbol.for` 递归改写、`tuner.cost` 节点构造都只属于 `LaunchKernelCostFuncPass.apply(...)` 的内部实现边界。

### `class LaunchKernelCostFuncPass(cost_kind: str = "DMA1|DMA2|DMA3|DMA4|MAC|VECTOR1|VECTOR2", fold: bool = True)`

- 功能说明：

- 扫描 module 中的 `arch.launch`，为每个 unique device callee 生成 cost function。

- 参数：

- `cost_kind(str = "DMA1|DMA2|DMA3|DMA4|MAC|VECTOR1|VECTOR2")`：当前 cost function 的统计视角，使用 `|` 分隔的有序列表字符串；每个片段必须来自 `DMA1/DMA2/DMA3/DMA4/MAC/VECTOR1/VECTOR2` 且不得重复。
- `fold(bool = True)`：控制 pass 后通用 folding sweep；该通用选项由 [`spec/pass/pass_manager.md`](../pass_manager.md) 承接。

- 使用示例：

```python
from kernel_gen.passes.tuning.launch_kernel_cost_func import LaunchKernelCostFuncPass

LaunchKernelCostFuncPass().apply(Context(), module)
LaunchKernelCostFuncPass(cost_kind="DMA1|MAC|VECTOR1").apply(Context(), module)
```

```python
from kernel_gen.passes.registry import build_registered_pass, load_builtin_passes

load_builtin_passes()
pass_obj = build_registered_pass(
    "launch-kernel-cost-func", {"cost_kind": "DMA1|MAC|VECTOR1"}
)
pass_obj.apply(Context(), module)
```

公开属性与方法：

- `name: str`
- `cost_kind: str`
- `__init__(cost_kind: str = "DMA1|DMA2|DMA3|DMA4|MAC|VECTOR1|VECTOR2", fold: bool = True) -> None`
- `from_options(options: dict[str, str]) -> LaunchKernelCostFuncPass`
- `apply(ctx: Context, module: ModuleOp) -> None`

- 注意事项：

- 显式失败统一抛出 `KernelCodeError`，并保持稳定错误前缀 `LaunchKernelCostFuncError:`。
- `cost_kind` 非法时必须显式失败，稳定错误短语为 `LaunchKernelCostFuncError: cost_kind must be '|' separated names from [DMA1,DMA2,DMA3,DMA4,MAC,VECTOR1,VECTOR2]`。
- `cost_kind` 的空段、全空白段、重复段或集合外名称必须显式失败。
- 多个 wrapper 指向同一个 device callee 时，同一 `cost_kind` 下只能生成一份 cost function。
- 不得改变原 wrapper、原 device func、原 `arch.launch` 或原 op attributes。

### Cost function 命名与签名

- 功能说明：

- 定义本 pass 新增 cost function 的可观察形状。

- 参数：

- `cost_kind(str)`：来自 pass 参数 `cost_kind`。
- `device_func_name(str)`：原 device callee 的 raw symbol 名。

- 使用示例：

```text
func.func @_cost_DMA1__device_matmul_kernel_(%lhs, %rhs, %out, %m, %k, %n) -> !symbol.int<"0">
func.func @_cost_VECTOR1__device_matmul_kernel_(%lhs, %rhs, %out, %m, %k, %n) -> !symbol.int<"0">
func.func @_cost_MAC__device_matmul_kernel_(%lhs, %rhs, %out, %m, %k, %n) -> !symbol.int<"0">
```

- 注意事项：

- 命名规则固定为 `@_cost_<cost_kind>_<device_func_name>`。
- raw callee 名直接拼接，不额外去除前导或尾随下划线。
- 参数列表与 device func 完全一致，参数顺序不变。
- 返回类型固定为单结果 `!symbol.int<"...">`。

### `tuner.cost` 生成规则

- 功能说明：

- 将受支持 op 映射为 `tuner.cost(...)->!symbol.int`。

- 参数：

- `operands`：原 op operands，按原顺序透传。
- `cost_kind`：当前 cost function 统计视角。
- `op_name`：原 op 名。

- 使用示例：

```text
%cost = tuner.cost(%tile_m, %k) {cost_kind = "DMA1", op_name = "dma.copy"} : (!symbol.int<"TILE_M">, !symbol.int<"K">) -> !symbol.int<"LOCAL">
```

- 注意事项：

- 下沉成本节点的 op 家族：`dma.*`、`kernel.*`、`arch.*`。
- helper op `arch.get_dynamic_memory`、`builtin.unrealized_conversion_cast`、`dma.view`、`dma.subview`、`dma.reshape`、`dma.alloc` 需要克隆保留，但不生成 `tuner.cost`。
- side-effect DMA op `dma.load`、`dma.free`、`dma.transpose` 在 cost function 中跳过，不克隆且不生成 `tuner.cost`；`dma.store` 按写回方向保留为成本节点，但不执行真实写回。
- `cost_kind` 始终等于 pass 参数展开后的单个 kind；只允许七值集合内名称。
- 不因任一合法 `cost_kind` 取值裁剪 `dma.*` / `kernel.*` / `arch.*` 成本节点。
- `dma.deslice` 只生成 `tuner.cost(op_name="dma.deslice")`，不得在 cost function 中执行真实写回；若原 op result 被后续消费，result 映射为原 target memory。
- 原 op 已存在 `kind`、`cost_kind`、`op_name`、`device_func` 任一同名 attr 时必须显式失败。
- `tuner.cost` 不公开 `kind`、`device_func` 两个 attrs。

### Skip 与失败规则

- 功能说明：

- 固定 device body 内各类 op 的处理边界。

- 使用示例：

```text
arith.constant -> skip
symbol.const -> skip
arch.get_dynamic_memory -> clone helper only
dma.view -> clone helper only
dma.subview -> clone helper only
dma.reshape -> clone helper only
dma.alloc -> clone helper only
dma.load -> skip
dma.store -> tuner.cost(op_name="dma.store")
dma.free -> skip
dma.transpose -> skip
dma.copy -> tuner.cost(op_name="dma.copy")
kernel.add -> tuner.cost(op_name="kernel.add")
```

- 注意事项：

- 允许直接跳过、不生成 `tuner.cost` 的 op：
  - `arith.constant`
  - 非循环结构的 `symbol.*`
  - `func.return`
  - `symbol.for` 自身（循环体递归处理）
  - `arch.get_dynamic_memory`
  - `dma.view`
  - `dma.subview`
  - `dma.reshape`
  - `dma.alloc`
  - `dma.load`
  - `dma.free`
  - `dma.transpose`
- 其他非支持 op 必须显式失败，不做 silent skip。

### `symbol.for` 累计规则

- 功能说明：

- cost function 中若保留 `symbol.for`，通过 loop-carried `!symbol.int` 传递循环内外累计值。

- 使用示例：

```text
%zero = symbol.const 0 : !symbol.int<"0">
%total = symbol.for %i = %start to %end step %step iter_args(%acc = %zero) {iter = #symbol.iter<start = "0", end = "M", step = "TILE_M">} -> !symbol.int<"0"> {
  %local = tuner.cost(value) {cost_kind = "VECTOR1", op_name = "kernel.add"} : (value) -> !symbol.int<"LOCAL">
  %next = symbol.add %acc, %local : !symbol.int<"0">, !symbol.int<"LOCAL"> -> !symbol.int<"0">
  symbol.yield %next : !symbol.int<"0">
}
```

- 注意事项：

- cost function 不得用私有状态、Python 侧列表、隐藏属性或专题专用 op 替代 `symbol.for` carried `!symbol.int`。
- 每个 `tuner.cost(...)->!symbol.int` 必须进入 `symbol.add` 累计链。
- 函数级最终 `func.return` 必须返回包含循环内外全部局部成本的单个 `!symbol.int`。

## API详细说明

### `class LaunchKernelCostFuncPass(cost_kind: str = "DMA1|DMA2|DMA3|DMA4|MAC|VECTOR1|VECTOR2", fold: bool = True)`

- api：`class LaunchKernelCostFuncPass(cost_kind: str = "DMA1|DMA2|DMA3|DMA4|MAC|VECTOR1|VECTOR2", fold: bool = True)`
- 参数：
  - `cost_kind`：`cost_kind` 输入值，参与 `LaunchKernelCostFuncPass` 的公开处理流程；类型 `str`；默认值 `"DMA1|DMA2|DMA3|DMA4|MAC|VECTOR1|VECTOR2"`；不允许 `None`、空值、重复项或七值集合外名称；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `fold`：`fold` 输入值，参与 `LaunchKernelCostFuncPass` 的公开处理流程；类型 `bool`；默认值 `True`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`LaunchKernelCostFuncPass` 实例。
- 使用示例：

  ```python
  launch_kernel_cost_func_pass = LaunchKernelCostFuncPass(cost_kind="DMA1|MAC|VECTOR1", fold=True)
  ```
- 功能说明：定义 `LaunchKernelCostFuncPass` pass 对象。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `name: str`

- api：`name: str`
- 参数：无。
- 返回值：`str` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  from kernel_gen.passes.tuning.launch_kernel_cost_func import LaunchKernelCostFuncPass

  assert LaunchKernelCostFuncPass.name == "launch-kernel-cost-func"
  ```
- 功能说明：执行 `str`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `cost_kind: str`

- api：`cost_kind: str`
- 参数：无。
- 返回值：`str` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  from kernel_gen.passes.tuning.launch_kernel_cost_func import LaunchKernelCostFuncPass

  pass_obj = LaunchKernelCostFuncPass(cost_kind="DMA1|MAC|VECTOR1")
  assert pass_obj.cost_kind == "DMA1|MAC|VECTOR1"
  ```
- 功能说明：执行 `str`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `__init__(cost_kind: str = "DMA1|DMA2|DMA3|DMA4|MAC|VECTOR1|VECTOR2", fold: bool = True) -> None`

- api：`__init__(cost_kind: str = "DMA1|DMA2|DMA3|DMA4|MAC|VECTOR1|VECTOR2", fold: bool = True) -> None`
- 参数：
  - `cost_kind`：`cost_kind` 输入值，参与 `__init__` 的公开处理流程；类型 `str`；默认值 `"DMA1|DMA2|DMA3|DMA4|MAC|VECTOR1|VECTOR2"`；不允许 `None`、空值、重复项或七值集合外名称；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `fold`：`fold` 输入值，参与 `__init__` 的公开处理流程；类型 `bool`；默认值 `True`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  __init__(cost_kind="DMA1|MAC|VECTOR1", fold=True)
  ```
- 功能说明：执行 `__init__`。
- 注意事项：该特殊方法只承接 Python 对应协议语义；不得额外暴露内部字段。

### `from_options(options: dict[str, str]) -> LaunchKernelCostFuncPass`

- api：`from_options(options: dict[str, str]) -> LaunchKernelCostFuncPass`
- 参数：
  - `options`：IR operation；类型 `dict[str, str]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按可变容器传入时，是否修改输入必须以本接口功能说明和注意事项为准；非法值按该 API 的公开错误语义处理。
- 返回值：`LaunchKernelCostFuncPass`。
- 使用示例：

  ```python
  result = from_options(options=options)
  ```
- 功能说明：执行 `from_options`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `apply(ctx: Context, module: ModuleOp) -> None`

- api：`apply(ctx: Context, module: ModuleOp) -> None`
- 参数：
  - `ctx`：公开上下文对象，提供代码生成、emit、pass 或工具执行所需的配置与状态；类型 `Context`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `module`：模块级 IR 对象，作为 pass、校验或代码生成的处理主体；类型 `ModuleOp`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  apply(ctx=ctx, module=module)
  ```
- 功能说明：执行 `apply`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

## 测试

- 测试文件：
  - `test/dialect/test_tuner.py`
  - `test/passes/test_registry.py`
  - `test/passes/tuning/test_launch_kernel_cost_func.py`
- 执行命令：
  - `pytest -q test/passes/tuning/test_launch_kernel_cost_func.py -k "launch_kernel_cost_func"`
  - `pytest -q test/passes/test_registry.py -k "launch_kernel_cost_func"`
  - `pytest -q test/dialect/test_tuner.py -k "tuner_cost"`

### 测试目标

- 锁定 cost function 命名/签名、共享 callee 去重、七值 kind 子集语义、helper 保留与失败路径、`!symbol.int` 汇总返回。
- 锁定 registry 名称 `launch-kernel-cost-func` 与 `cost_kind` 选项透传。
- 锁定 `tuner.cost` 的七值 kind 边界与错误路径。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-LKCF-001A | 成本/调优 | 默认七 kind 成功路径 | 准备公开 cost kind、kernel/DMA 参数或 tuning IR 输入。 | 运行 `test_launch_kernel_cost_func_default_kind_is_full_npu_demo_cost_set`。 | 默认生成 `DMA1/DMA2/DMA3/DMA4/MAC/VECTOR1/VECTOR2` 七个 sibling cost function。 | `test_launch_kernel_cost_func_default_kind_is_full_npu_demo_cost_set` |
| TC-LKCF-001 | 成本/调优 | `cost_kind=VECTOR1` 基础成功路径 | 准备公开 cost kind、kernel/DMA 参数或 tuning IR 输入。 | 运行 `test_launch_kernel_cost_func_builds_cost_function_for_vector1_kind`。 | 成本函数、tuning 属性或 cost IR 输出体现 `VECTOR1` 成功路径。 | `test_launch_kernel_cost_func_builds_cost_function_for_vector1_kind` |
| TC-LKCF-002 | 内存/DMA | `cost_kind=DMA1` 基础成功路径 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_launch_kernel_cost_func_dma1_keeps_all_cost_nodes`。 | `DMA1` cost function 仍保留并统计支持的 kernel/DMA cost 节点，最终由 include helper 判定命中与 0。 | `test_launch_kernel_cost_func_dma1_keeps_all_cost_nodes` |
| TC-LKCF-003 | 成本/调优 | 七值子集列表成功路径 | 准备公开 cost kind、kernel/DMA 参数或 tuning IR 输入。 | 运行 `test_launch_kernel_cost_func_builds_cost_functions_for_multi_kind_order`。 | 成本函数、tuning 属性或 cost IR 输出体现七值子集的顺序保留。 | `test_launch_kernel_cost_func_builds_cost_functions_for_multi_kind_order` |
| TC-LKCF-004 | 成本/调优 | 共享 callee 去重 | 准备公开 cost kind、kernel/DMA 参数或 tuning IR 输入。 | 运行 `test_launch_kernel_cost_func_shared_callee_once`。 | 成本函数、tuning 属性或 cost IR 输出体现“共享 callee 去重”场景。 | `test_launch_kernel_cost_func_shared_callee_once` |
| TC-LKCF-005 | 边界/异常 | 非法 `cost_kind` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_launch_kernel_cost_func_rejects_invalid_cost_kind`。 | “非法 `cost_kind`”场景按公开错误语义失败或被拒绝。 | `test_launch_kernel_cost_func_rejects_invalid_cost_kind` |
| TC-LKCF-006 | 边界/异常 | callee 缺失 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_launch_kernel_cost_func_rejects_missing_callee`。 | “callee 缺失”场景按公开错误语义失败或被拒绝。 | `test_launch_kernel_cost_func_rejects_missing_callee` |
| TC-LKCF-007 | 边界/异常 | metadata attr 冲突 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_launch_kernel_cost_func_rejects_metadata_attr_conflict`。 | “metadata attr 冲突”场景按公开错误语义失败或被拒绝。 | `test_launch_kernel_cost_func_rejects_metadata_attr_conflict` |
| TC-LKCF-008 | 边界/异常 | 非支持 op | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_launch_kernel_cost_func_rejects_unsupported_op`。 | “非支持 op”场景按公开错误语义失败或被拒绝。 | `test_launch_kernel_cost_func_rejects_unsupported_op` |
| TC-LKCF-009 | 边界/异常 | 预存重名 cost function | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_launch_kernel_cost_func_rejects_existing_cost_func`。 | “预存重名 cost function”场景按公开错误语义失败或被拒绝。 | `test_launch_kernel_cost_func_rejects_existing_cost_func` |
