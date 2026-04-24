# launch_kernel_cost_func.md

## 功能简介

- 定义 standalone tuning pass `launch-kernel-cost-func` 的当前公开合同。
- 该 pass 从已有 `arch.launch -> device func` 关系生成 sibling cost host function，用 `tuner.cost` 表示 device body 内受支持 op 的局部成本，并把全部局部 `!symbol.int` 成本通过 `symbol.add` 累计后返回单个 `!symbol.int` 总值。
- 当前公开方向为 open-kind：`cost_kind` 接受任意非空 kind 名和任意数量；旧两值 / 四值示例只作为兼容样例保留，不再代表当前输入域上界。

## 文档信息

- 创建者：`睡觉小分队`
- 最后一次更改：`咯咯咯`
- `spec`：[`spec/pass/tuning/launch_kernel_cost_func.md`](../../../spec/pass/tuning/launch_kernel_cost_func.md)
- `功能实现`：
  - [`kernel_gen/passes/tuning/launch_kernel_cost_func.py`](../../../kernel_gen/passes/tuning/launch_kernel_cost_func.py)
  - [`kernel_gen/passes/tuning/__init__.py`](../../../kernel_gen/passes/tuning/__init__.py)
  - [`kernel_gen/passes/registry.py`](../../../kernel_gen/passes/registry.py)
- `test`：
  - [`test/pass/test_launch_kernel_cost_func.py`](../../../test/pass/test_launch_kernel_cost_func.py)
  - [`test/pass/test_pass_registry.py`](../../../test/pass/test_pass_registry.py)
  - [`test/dialect/test_tuner_dialect.py`](../../../test/dialect/test_tuner_dialect.py)

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
- `cost_kind`：当前 cost function 的统计视角；本轮接受任意非空、`|` 分隔且去重后的 kind 名列表。

## 目标

- 固定 pass 名称：`launch-kernel-cost-func`。
- 固定公开入口：`LaunchKernelCostFuncPass(cost_kind="compute|memory|latency")` 与 `build_registered_pass("launch-kernel-cost-func", {"cost_kind": ...})`。
- 固定输出：每个 unique device callee 对请求列表中的每个 `cost_kind` 生成一份 cost function。
- 固定 cost function 返回语义：全部 `tuner.cost(...)->!symbol.int` 必须进入 `symbol.add` 累计链，最终 `func.return` 返回单个总值。
- 保持 helper 保留规则：`dma.view` / `dma.reshape` 必须保留到 cost function，但不下沉 `tuner.cost`。

## 限制与边界

- 本 pass 是 standalone tuning pass，不自动进入 `default-lowering` 或其他默认 pipeline。
- 输入必须已经存在 `arch.launch`，且 callee symbol 可解析到 module 内的 device `func.func`。
- 原 host wrapper 与原 device func 必须保持不变；本 pass 只新增 sibling cost function。
- 本 pass 不做 target runtime 求值、不查 cost table、不把 `tuner.cost` 折叠为常量。
- `cost_kind` 接受任意非空 kind 名；空串、全空白串、空段和重复段都必须显式失败。
- 当前仓库已 tracked [`expectation/pass/tuning/launch_kernel_cost_func`](../../../expectation/pass/tuning/launch_kernel_cost_func) 与 [`expectation/pass/tuning/launch_kernel_cost_func_compute_memory`](../../../expectation/pass/tuning/launch_kernel_cost_func_compute_memory) 两个目录入口；前者只承接后者的 `compute / memory` runner，不引回历史 `multi_kind.py` / `invalid_kind.py` 子资产。
- 若仓库后续需要重新引入历史四 kind companion 资产，或扩展当前目录入口覆盖范围，必须拆到单独的合同资产处理；当前公开合同仍以 open-kind 产品 spec/pytest/实现 与 tracked `compute / memory` expectation 入口分层定义。
- 若输入 module 已存在目标命名规则对应的 cost function，必须显式失败，不得覆盖或复用。

## 公开接口

### `class LaunchKernelCostFuncError(ValueError)`

功能说明：

- 表示 `launch-kernel-cost-func` pass 的稳定错误类型。

使用示例：

```python
raise LaunchKernelCostFuncError(
    "LaunchKernelCostFuncError: cost_kind must be a non-empty '|' separated list of unique kind names"
)
```

注意事项：

- 非法 `cost_kind`、callee 缺失、预存重名 cost function、原 op metadata attr 冲突、非支持 op 等显式失败路径都应统一抛出该错误或 `ValueError` 子类，并保持错误消息可机械匹配。

### `class LaunchKernelCostFuncPass(Pass)`

功能说明：

- 扫描 module 中的 `arch.launch`，为每个 unique device callee 生成 cost function。

参数说明：

- `cost_kind(str = "compute")`：当前 cost function 的统计视角，使用 `|` 分隔的有序列表字符串；每个片段必须是非空 kind 名，允许任意文本。

使用示例：

```python
from kernel_gen.passes.tuning.launch_kernel_cost_func import LaunchKernelCostFuncPass

module = LaunchKernelCostFuncPass(cost_kind="compute|memory|latency").run(module)
```

```python
from kernel_gen.passes.registry import build_registered_pass, load_builtin_passes

load_builtin_passes()
pass_obj = build_registered_pass(
    "launch-kernel-cost-func", {"cost_kind": "compute|memory|latency"}
)
module = pass_obj.run(module)
```

注意事项：

- `cost_kind` 非法时必须显式失败，稳定错误短语为 `LaunchKernelCostFuncError: cost_kind must be a non-empty '|' separated list of unique kind names`。
- `cost_kind` 的空段、全空白段或重复段必须显式失败。
- 多个 wrapper 指向同一个 device callee 时，同一 `cost_kind` 下只能生成一份 cost function。
- 不得改变原 wrapper、原 device func、原 `arch.launch` 或原 op attributes。

### Cost function 命名与签名

功能说明：

- 定义本 pass 新增 cost function 的可观察形状。

参数说明：

- `cost_kind(str)`：来自 pass 参数 `cost_kind`。
- `device_func_name(str)`：原 device callee 的 raw symbol 名。

使用示例：

```text
func.func @_cost_compute__device_matmul_kernel_(%lhs, %rhs, %out, %m, %k, %n) -> !symbol.int<"0">
func.func @_cost_memory__device_matmul_kernel_(%lhs, %rhs, %out, %m, %k, %n) -> !symbol.int<"0">
```

注意事项：

- 命名规则固定为 `@_cost_<cost_kind>_<device_func_name>`。
- raw callee 名直接拼接，不额外去除前导或尾随下划线。
- 参数列表与 device func 完全一致，参数顺序不变。
- 返回类型固定为单结果 `!symbol.int<"...">`。

### `tuner.cost` 生成规则

功能说明：

- 将受支持 op 映射为 `tuner.cost(...)->!symbol.int`。

参数说明：

- `operands`：原 op operands，按原顺序透传。
- `cost_kind`：当前 cost function 统计视角。
- `op_name`：原 op 名。

使用示例：

```text
%cost = tuner.cost(%tile_m, %k) {cost_kind = "memory", op_name = "dma.copy"} : (!symbol.int<"TILE_M">, !symbol.int<"K">) -> !symbol.int<"LOCAL">
```

注意事项：

- 下沉成本节点的 op 家族：`dma.*`、`kernel.*`、`arch.*`。
- helper op `dma.view`、`dma.reshape` 需要克隆保留，但不生成 `tuner.cost`。
- `cost_kind` 始终等于 pass 参数展开后的单个 kind；允许任意非空字符串。
- 不因任一合法 `cost_kind` 取值裁剪 `dma.*` / `kernel.*` / `arch.*` 成本节点。
- 原 op 已存在 `kind`、`cost_kind`、`op_name`、`device_func` 任一同名 attr 时必须显式失败。
- `tuner.cost` 不公开 `kind`、`device_func` 两个 attrs。

### Skip 与失败规则

功能说明：

- 固定 device body 内各类 op 的处理边界。

使用示例：

```text
arith.constant -> skip
symbol.const -> skip
dma.view -> clone helper only
dma.reshape -> clone helper only
dma.copy -> tuner.cost(op_name="dma.copy")
kernel.add -> tuner.cost(op_name="kernel.add")
```

注意事项：

- 允许直接跳过、不生成 `tuner.cost` 的 op：
  - `arith.constant`
  - 非循环结构的 `symbol.*`
  - `func.return`
  - `symbol.for` 自身（循环体递归处理）
  - `dma.view`
  - `dma.reshape`
- 其他非支持 op 必须显式失败，不做 silent skip。

### `symbol.for` 累计规则

功能说明：

- cost function 中若保留 `symbol.for`，通过 loop-carried `!symbol.int` 传递循环内外累计值。

使用示例：

```text
%zero = symbol.const 0 : !symbol.int<"0">
%total = symbol.for %i = %start to %end step %step iter_args(%acc = %zero) {iter = #symbol.iter<start = "0", end = "M", step = "TILE_M">} -> !symbol.int<"0"> {
  %local = tuner.cost(...) {cost_kind = "compute", op_name = "kernel.add"} : (...) -> !symbol.int<"LOCAL">
  %next = symbol.add %acc, %local : !symbol.int<"0">, !symbol.int<"LOCAL"> -> !symbol.int<"0">
  symbol.yield %next : !symbol.int<"0">
}
```

注意事项：

- cost function 不得用私有状态、Python 侧列表、隐藏属性或专题专用 op 替代 `symbol.for` carried `!symbol.int`。
- 每个 `tuner.cost(...)->!symbol.int` 必须进入 `symbol.add` 累计链。
- 函数级最终 `func.return` 必须返回包含循环内外全部局部成本的单个 `!symbol.int`。

## 测试

- 测试文件：[`test/pass/test_launch_kernel_cost_func.py`](../../../test/pass/test_launch_kernel_cost_func.py)
- 执行命令：`pytest -q test/pass/test_launch_kernel_cost_func.py -k "launch_kernel_cost_func"`
- 测试目标：锁定 cost function 命名/签名、共享 callee 去重、open-kind 多值语义、helper 保留与失败路径、`!symbol.int` 汇总返回。

- 测试文件：[`test/pass/test_pass_registry.py`](../../../test/pass/test_pass_registry.py)
- 执行命令：`pytest -q test/pass/test_pass_registry.py -k "launch_kernel_cost_func"`
- 测试目标：锁定 registry 名称 `launch-kernel-cost-func` 与 `cost_kind` 选项透传。

- 测试文件：[`test/dialect/test_tuner_dialect.py`](../../../test/dialect/test_tuner_dialect.py)
- 执行命令：`pytest -q test/dialect/test_tuner_dialect.py -k "tuner_cost"`
- 测试目标：锁定 `tuner.cost` 的 open-kind verifier 边界与错误路径。

- 合同验收资产：[`expectation/pass/tuning/launch_kernel_cost_func`](../../../expectation/pass/tuning/launch_kernel_cost_func) 是仓库当前目录入口；它只串行承接 [`expectation/pass/tuning/launch_kernel_cost_func_compute_memory`](../../../expectation/pass/tuning/launch_kernel_cost_func_compute_memory) 的 `compute / memory` case，不替代 diff 反推测试。
- 当前目录入口只运行 `compute / memory` 合同，不引回历史四 kind 子资产；`invalid_kind.py` 不属于该入口接线。

### 功能与用例清单

| 用例 ID | 场景 | 前置条件 | 操作 | 预期结果 | 对应测试 |
| --- | --- | --- | --- | --- | --- |
| LKCF-001 | `cost_kind=compute` 基础成功路径 | 单 wrapper 指向单 device callee，device body 含 `dma.view/dma.reshape/dma.copy/kernel.add` | 执行 `LaunchKernelCostFuncPass(cost_kind="compute")` | 新增 `_cost_compute_<device>`，helper 保留、成本节点不裁剪，函数返回 `!symbol.int` | `test_launch_kernel_cost_func_builds_cost_function_for_compute_kind` |
| LKCF-002 | `cost_kind=memory` 基础成功路径 | 同 LKCF-001 | 执行 `cost_kind="memory"` | 新增 `_cost_memory_<device>`，`tuner.cost.cost_kind` 全为 `"memory"`，节点不裁剪 | `test_launch_kernel_cost_func_memory_keeps_compute_nodes` |
| LKCF-003 | open-kind 列表成功路径 | 同 LKCF-001 | 执行 `cost_kind="compute|memory|latency"` | 新增 3 个 sibling cost function，顺序与列表一致，`tuner.cost.cost_kind` 分别等于对应 kind | `test_launch_kernel_cost_func_builds_cost_functions_for_multi_kind_order` |
| LKCF-004 | 共享 callee 去重 | 两个 wrapper 指向同一 device callee | 执行 pass | 同一 `cost_kind` 下仅生成一份 cost function | `test_launch_kernel_cost_func_shared_callee_once` |
| LKCF-005 | 非法 `cost_kind` | `cost_kind` 为空、含空段、全空白或重复 | 构造或执行 pass | 显式失败，消息为稳定 open-kind 错误短语 | `test_launch_kernel_cost_func_rejects_invalid_cost_kind` |
| LKCF-006 | callee 缺失 | `arch.launch` 指向不存在的 symbol | 执行 pass | 显式失败，不 silent skip | `test_launch_kernel_cost_func_rejects_missing_callee` |
| LKCF-007 | metadata attr 冲突 | 原 op 已有 `kind / cost_kind / op_name / device_func` 任一同名 attr | 执行 pass | 显式失败，不覆盖原 attr | `test_launch_kernel_cost_func_rejects_metadata_attr_conflict` |
| LKCF-008 | 非支持 op | device body 含非支持 op | 执行 pass | 显式失败 | `test_launch_kernel_cost_func_rejects_unsupported_op` |
| LKCF-009 | 预存重名 cost function | module 已有目标 cost function 名 | 执行 pass | 显式失败，不覆盖 | `test_launch_kernel_cost_func_rejects_existing_cost_func` |
