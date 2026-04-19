# launch_kernel_cost_func.md

## 功能简介

- 定义 standalone tuning pass `launch-kernel-cost-func` 的公开合同。
- 该 pass 从已有 `arch.launch -> device func` 关系生成 sibling cost host function，用 `tuner.cost` 表示 device body 内受支持 op 的局部成本，并把全部局部 `f64` 成本累计后返回单个 `f64` 总值。
- 本 pass 不改写原 host wrapper，不改写原 device func，不求值真实成本，也不替代 `analysis/func_cost` 这类只读分析 pass。

## 文档信息

- 创建者：`睡觉小分队`
- 最后一次更改：`睡觉小分队`
- `spec`：[`spec/pass/tuning/launch_kernel_cost_func.md`](../../../spec/pass/tuning/launch_kernel_cost_func.md)
- `功能实现`：
  - [`kernel_gen/passes/tuning/launch_kernel_cost_func.py`](../../../kernel_gen/passes/tuning/launch_kernel_cost_func.py)：公开 pass 入口。
  - [`kernel_gen/passes/tuning/__init__.py`](../../../kernel_gen/passes/tuning/__init__.py)：tuning pass 包导出入口。
  - [`kernel_gen/passes/registry.py`](../../../kernel_gen/passes/registry.py)：registry 名称接入入口。
- `test`：
  - [`test/pass/test_launch_kernel_cost_func.py`](../../../test/pass/test_launch_kernel_cost_func.py)
  - [`test/pass/test_pass_registry.py`](../../../test/pass/test_pass_registry.py)

## 依赖

- Pass 抽象与管理器：[`spec/pass/pass_manager.md`](../pass_manager.md)
- Pass 注册表：[`spec/pass/registry.md`](../registry.md)
- `arch.launch` 输入形状：[`spec/dialect/arch.md`](../../dialect/arch.md)
- `symbol.for` loop-carried `f64`：[`spec/dialect/symbol.md`](../../dialect/symbol.md)
- `tuner.cost` 局部成本节点：[`spec/dialect/tuner.md`](../../dialect/tuner.md)
- host launch outline 前置形状：[`spec/pass/outline_device_kernel.md`](../outline_device_kernel.md)
- 只读分析 pass 边界：[`spec/pass/analysis/func_cost.md`](../analysis/func_cost.md)

## 术语

- `host wrapper`：包含 `arch.launch` 的 host 侧函数。
- `device func`：`arch.launch` 通过 callee symbol 指向的 device 函数。
- `cost function`：本 pass 新增的 sibling host function，名称形如 `@_cost_<cost_kind>_<device_func_name>`，参数与 device func 一致，返回单个 `f64`。
- `kind`：原 op 的成本类别，只允许 `compute` 或 `move`。
- `cost_kind`：当前 cost function 的统计视角，只允许 `compute`、`move` 或 `all`。

## 目标

- 固定 pass 名称：`launch-kernel-cost-func`。
- 固定公开入口：`LaunchKernelCostFuncPass(kind="all")` 与 `build_registered_pass("launch-kernel-cost-func", {"kind": ...})`。
- 固定输出：每个 unique device callee 在同一 `cost_kind` 下最多生成一份 cost function。
- 固定 cost function 返回语义：全部 `tuner.cost(...)->f64` 必须进入 `f64` 累计链，最终 `func.return` 返回单个总值。
- 固定 skip 与失败规则，避免调用方猜测哪些 op 被静默跳过。

## 限制与边界

- 本 pass 是 standalone tuning pass，不自动进入 `default-lowering` 或其他默认 pipeline。
- 输入必须已经存在 `arch.launch`，且 callee symbol 可解析到 module 内的 device `func.func`。
- 原 host wrapper 与原 device func 必须保持不变；本 pass 只新增 sibling cost function。
- 本 pass 不做 target runtime 求值、不查 cost table、不把 `tuner.cost` 折叠为常量。
- 本 pass 不属于 `analysis/func_cost` 主线；`analysis/func_cost` 仍只做只读分析，不生成 IR function。
- 若输入 module 已存在目标命名规则对应的 cost function，必须显式失败，不得覆盖或复用。

## 公开接口

### `class LaunchKernelCostFuncError(ValueError)`

功能说明：

- 表示 `launch-kernel-cost-func` pass 的稳定错误类型。

参数说明：

- `message(str)`：错误说明。

使用示例：

```python
raise LaunchKernelCostFuncError("launch-kernel-cost-func kind must be one of compute, move, all")
```

注意事项：

- 非法 `kind`、callee 缺失、预存重名 cost function、原 op metadata attr 冲突、非支持 op 等显式失败路径都应统一抛出该错误或 `ValueError` 子类，并保持错误消息可机械匹配。

返回与限制：

- 抛错即终止当前 pass，不返回部分改写结果。

### `class LaunchKernelCostFuncPass(Pass)`

功能说明：

- 扫描 module 中的 `arch.launch`，为每个 unique device callee 生成 cost function。

参数说明：

- `kind(str = "all")`：当前 cost function 的统计视角，只允许 `"compute"`、`"move"`、`"all"`。

使用示例：

```python
from kernel_gen.passes.tuning.launch_kernel_cost_func import LaunchKernelCostFuncPass

module = LaunchKernelCostFuncPass(kind="move").run(module)
```

```python
from kernel_gen.passes.registry import build_registered_pass, load_builtin_passes

load_builtin_passes()
pass_obj = build_registered_pass("launch-kernel-cost-func", {"kind": "all"})
module = pass_obj.run(module)
```

注意事项：

- `kind` 非法时必须显式失败，错误消息至少包含 `compute`、`move`、`all` 三个允许值。
- 多个 wrapper 指向同一个 device callee 时，同一 `cost_kind` 下只能生成一份 cost function。
- 不得改变原 wrapper、原 device func、原 `arch.launch` 或原 op attributes。

返回与限制：

- 返回新增 cost function 后的 module。

### Cost function 命名与签名

功能说明：

- 定义本 pass 新增 cost function 的可观察形状。

参数说明：

- `cost_kind(str)`：来自 pass 参数 `kind`。
- `device_func_name(str)`：原 device callee 的 raw symbol 名。

使用示例：

```text
func.func @_cost_all__device_matmul_kernel_(%lhs, %rhs, %out, %m, %k, %n) -> f64
```

注意事项：

- 命名规则固定为 `@_cost_<cost_kind>_<device_func_name>`。
- raw callee 名直接拼接，不额外去除前导或尾随下划线。
- 参数列表与 device func 完全一致，参数顺序不变。
- 返回类型固定为单结果 `f64`。

返回与限制：

- cost function 内必须返回单个 `f64` 总成本。

### `tuner.cost` 生成规则

功能说明：

- 将受支持 op 映射为 `tuner.cost(...)->f64`。

参数说明：

- `operands`：原 op operands，按原顺序透传。
- `kind`：原 op 自身类别。
- `cost_kind`：当前 cost function 统计视角。
- `op_name`：原 op 名。
- `device_func`：当前 device callee symbol。

使用示例：

```text
%cost = tuner.cost(%tile_m, %k) {kind = "move", cost_kind = "all", op_name = "dma.alloc", device_func = @_device_matmul_kernel_} : (!symbol.int<"TILE_M">, !symbol.int<"K">) -> f64
```

注意事项：

- `dma.*` 默认分类为 `kind = "move"`。
- `kernel.*` 默认分类为 `kind = "compute"`。
- `arch.*` 默认分类为 `kind = "move"`。
- `cost_kind` 始终等于 pass 参数 `kind`。
- pass 不因 `cost_kind=compute` 删除 `kind=move` 节点，也不因 `cost_kind=move` 删除 `kind=compute` 节点。
- 原 op 已存在 `kind / cost_kind / op_name / device_func` 任一同名 attr 时必须显式失败。

返回与限制：

- 每条 `tuner.cost` 返回单个 `f64` 局部成本。

### Skip 与失败规则

功能说明：

- 固定 device body 内各类 op 的处理边界。

参数说明：

- 无参数。

使用示例：

```text
arith.constant -> skip
symbol.const -> skip
symbol.for -> preserve region and carry f64 accumulation
dma.alloc -> tuner.cost(kind="move")
kernel.matmul -> tuner.cost(kind="compute")
arch.barrier -> tuner.cost(kind="move")
```

注意事项：

- 允许直接跳过、不生成 `tuner.cost` 的 op 只有：
  - `arith.constant`
  - 非循环结构的 `symbol.*`
  - `func.return`
  - `symbol.for` 自身
- 允许直接生成 `tuner.cost` 的 op 家族只有：
  - `dma.*`
  - `kernel.*`
  - `arch.*`
- 其他非 `symbol` dialect op 必须显式失败，不做 silent skip。

返回与限制：

- skip 不表示删除原 op；原 device func 不变，skip 只影响 cost function 里的映射结果。

### `symbol.for` 累计规则

功能说明：

- cost function 中若保留 `symbol.for`，必须通过 `symbol.for` 的单个 loop-carried `f64` 能力传递循环内外累计值。

参数说明：

- `init(f64)`：循环进入前的累计值。
- `acc(f64)`：循环体内当前累计值。
- `yield(f64)`：下一轮累计值或循环结束后的返回值。

使用示例：

```text
%zero = arith.constant 0.0 : f64
%total = symbol.for %i = %start to %end step %step iter_args(%acc = %zero) {iter = #symbol.iter<start = "0", end = "M", step = "TILE_M">} -> f64 {
  %local = tuner.cost(...) {kind = "compute", cost_kind = "all", op_name = "kernel.matmul", device_func = @_device_matmul_kernel_} : (...) -> f64
  %next = arith.addf %acc, %local : f64
  symbol.yield %next : f64
}
```

注意事项：

- cost function 不得用私有状态、Python 侧列表、隐藏属性或专题专用 op 替代 `symbol.for` carried `f64`。
- 每个 `tuner.cost(...)->f64` 必须进入 `arith.addf` 累计链。

返回与限制：

- 函数级最终 `func.return` 必须返回包含循环内外全部局部成本的单个 `f64`。

## 测试

- 测试文件：[`test/pass/test_launch_kernel_cost_func.py`](../../../test/pass/test_launch_kernel_cost_func.py)
- 执行命令：`pytest -q test/pass/test_launch_kernel_cost_func.py`
- 测试目标：锁定 cost function 命名/签名、共享 callee 去重、`kind/cost_kind` 语义、skip 与失败路径、`f64` 汇总返回。

- 测试文件：[`test/pass/test_pass_registry.py`](../../../test/pass/test_pass_registry.py)
- 执行命令：`pytest -q test/pass/test_pass_registry.py -k launch_kernel_cost_func`
- 测试目标：锁定 registry 名称 `launch-kernel-cost-func` 与 `kind` 选项透传。

### 测试目标

- 验证单 wrapper / 单 device callee 成功路径。
- 验证多个 wrapper 共享同一 device callee 时只生成一份 cost function。
- 验证 `kind=compute|move|all` 都生成 `tuner.cost`，且仅 `cost_kind` 随 pass 参数变化。
- 验证 `arith.constant`、非 loop `symbol.*`、`func.return` 与 `symbol.for` 自身不生成 `tuner.cost`。
- 验证所有 `tuner.cost(...)->f64` 进入 `arith.addf` 累计链，最终返回单个 `f64`。
- 验证非法 `kind`、callee 缺失、metadata attr 冲突、非支持 op 与预存重名 cost function 均显式失败。

### 功能与用例清单

| 用例 ID | 场景 | 前置条件 | 操作 | 预期结果 | 对应测试 |
| --- | --- | --- | --- | --- | --- |
| LKCF-001 | `kind=all` 基础成功路径 | 单 wrapper 指向单 device callee，device body 含 `dma.* / kernel.* / arch.*` | 执行 `LaunchKernelCostFuncPass(kind="all")` | 新增 `_cost_all_<device>`，原 wrapper/device 不变，所有局部成本累计后返回 `f64` | `test_launch_kernel_cost_func_all_basic` |
| LKCF-002 | `kind=compute` 成功路径 | 同 LKCF-001 | 执行 `kind="compute"` | 新增 `_cost_compute_<device>`，所有 `tuner.cost.cost_kind` 为 `"compute"`，不删除 `kind="move"` 节点 | `test_launch_kernel_cost_func_compute_keeps_move_nodes` |
| LKCF-003 | `kind=move` 成功路径 | 同 LKCF-001 | 执行 `kind="move"` | 新增 `_cost_move_<device>`，所有 `tuner.cost.cost_kind` 为 `"move"`，不删除 `kind="compute"` 节点 | `test_launch_kernel_cost_func_move_keeps_compute_nodes` |
| LKCF-004 | 共享 callee 去重 | 两个 wrapper 指向同一 device callee | 执行 pass | 同一 `cost_kind` 下仅生成一份 cost function | `test_launch_kernel_cost_func_shared_callee_once` |
| LKCF-005 | 非法 `kind` | `kind` 不在 `compute/move/all` | 构造或执行 pass | 显式失败，消息包含三个允许值 | `test_launch_kernel_cost_func_rejects_invalid_kind` |
| LKCF-006 | callee 缺失 | `arch.launch` 指向不存在的 symbol | 执行 pass | 显式失败，不 silent skip | `test_launch_kernel_cost_func_rejects_missing_callee` |
| LKCF-007 | metadata attr 冲突 | 原 op 已有 `kind / cost_kind / op_name / device_func` 任一同名 attr | 执行 pass | 显式失败，不覆盖原 attr | `test_launch_kernel_cost_func_rejects_metadata_attr_conflict` |
| LKCF-008 | 非支持 op | device body 含非 `symbol` 且非 `dma/kernel/arch` op | 执行 pass | 显式失败 | `test_launch_kernel_cost_func_rejects_unsupported_op` |
| LKCF-009 | 预存重名 cost function | module 已有目标 cost function 名 | 执行 pass | 显式失败，不覆盖 | `test_launch_kernel_cost_func_rejects_existing_cost_func` |
