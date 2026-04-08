# nn_to_kernel.md

## 功能简介

- 定义将 `nn` dialect IR lower 到 `dma/kernel` dialect IR 的 pass 规范。
- 当需要为结果分配输出 Memory 时，使用 `dma.alloc`。
- `nn.broadcast` / `nn.transpose` 必须 lower 为 `dma.broadcast` / `dma.transpose`，而不是 `kernel` 计算 op。
- `nn.softmax` 直接 lower 为 `kernel.softmax`，并保留 `axis` 属性。
- 不负责高层语义推导、跨函数优化或后端代码生成。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`金铲铲大作战`
- `spec`：[`spec/pass/lowering/nn_to_kernel.md`](../../../spec/pass/lowering/nn_to_kernel.md)
- `功能实现`：[`kernel_gen/passes/lowering/nn_to_kernel.py`](../../../kernel_gen/passes/lowering/nn_to_kernel.py)
- `test`：[`test/pass/test_lowering_nn_to_kernel.py`](../../../test/pass/test_lowering_nn_to_kernel.py)

## 依赖

- Pass 抽象与管理器：[`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)
- NN dialect 语义：[`spec/dialect/nn.md`](../../../spec/dialect/nn.md)
- Kernel dialect 语义：[`spec/dialect/kernel.md`](../../../spec/dialect/kernel.md)
- DMA dialect（输出分配）：[`spec/dialect/dma.md`](../../../spec/dialect/dma.md)

## 目标

- 将 `nn` dialect 的逐元素算术/比较/select/cast lower 为 `kernel` dialect 对应 op。
- 将 `nn.broadcast` / `nn.transpose` lower 为 `dma.broadcast` / `dma.transpose`。
- 将 `nn.exp` / `nn.softmax` / `nn.reduce_*` / `nn.matmul` / `nn.img2col*` lower 为具名 `kernel.*` op。
- 保证 Memory 类型与空间在 lowering 前后保持一致，输出 Memory 由 `dma.alloc` 创建并交给 kernel op 使用。
- 当结果类型包含符号或静态维度时，`dma.alloc` 必须保留对应 `shape` 的维度值。
- 产出仅包含 `kernel`/`dma`/`func`/`builtin` 等必要 op，不再保留 `nn` op。

## 限制与边界

- 仅支持以下 `nn` op lowering：
  - 逐元素：`nn.add`/`nn.sub`/`nn.mul`/`nn.div`/`nn.truediv`、`nn.eq`/`nn.ne`/`nn.lt`/`nn.le`/`nn.gt`/`nn.ge`、`nn.select`、`nn.cast`
  - 结构化：`nn.broadcast`、`nn.transpose`、`nn.exp`、`nn.softmax`、`nn.reduce_sum`/`nn.reduce_min`/`nn.reduce_max`、`nn.matmul`、`nn.img2col1d`/`nn.img2col2d`
- `nn.truediv` 与 `nn.div` 在 pass 层统一 lower 为 `kernel.div`。
- 本 pass 不负责把高层 helper 分解成方言 op（例如 `conv/fc` 的 `img2col/matmul` 分解）；它只处理已进入 `nn dialect` 的 op。
- 不改写函数签名或返回语义，不引入新的返回约束；仅在函数体内替换 op。
- 若模块内还存在跨函数 `memory-return func.call`，本 pass 只负责把函数体里的 `nn` op lower 到 `kernel/dma`；函数签名、caller out 实参补齐与旧 call result SSA 清理必须由后续 `BufferResultsToOutParamsPass` 统一处理。
- 当 `nn` op 结果需要输出 Memory 时，必须插入 `dma.alloc`；不允许隐式创建其他分配方式。
- mixed compare 桥接规则必须写死：
  - `memory + memory` compare：lower 目标为 `kernel.compare family`，且两侧 `shape/stride/space/element_type` 必须已经一致；不得在 `kernel` 层做隐式 broadcast。
  - `memory + symbol/const` compare：必须先使用 `dma.alloc + dma.broadcast` 把 `symbol/const` 物化成与 memory operand 完全一致的 temporary memory，然后再 lower 为 `kernel.compare family`；禁止 `kernel.compare` 直接接收非 memory operand。
- 遇到不支持的 `nn` op、结果类型非法、缺失 `nn.space`、operand 数量不匹配或 kernel 校验失败时，必须抛出 `LowerNnToKernelError` 并中止 pass。
- 阶段阻断：本计划的后续阶段 `S2` 仅允许在本 `S1` spec 合同合并后启动；未合并时不得提前启动 `S2` 的实现/补测任务。

## 公开接口

### `class LowerNnToKernelPass(Pass)`

功能说明：

- 表示 `nn -> kernel` lowering pass。
- 通过 `run(module)` 执行 lowering。

参数说明：

- `name (str)`：固定为 `"lower-nn-to-kernel"`。

使用示例：

```python
from kernel_gen.passes.pass_manager import PassManager
from kernel_gen.passes.lowering.buffer_results_to_out_params import BufferResultsToOutParamsPass
from kernel_gen.passes.lowering.nn_to_kernel import LowerNnToKernelPass

pm = PassManager(name="lowering")
pm.add_pass(LowerNnToKernelPass())
pm.add_pass(BufferResultsToOutParamsPass())
module = pm.run(module)
```

注意事项：

- pass 只对 `func.func` 中的 `nn` op 生效。
- 输出 Memory 由 `dma.alloc` 创建，并作为 kernel op 的 `outs` operand。
- 当前固定 lowering 链顺序是 `LowerNnToKernelPass -> BufferResultsToOutParamsPass`；若模块内存在 `memory-return func.call`，不得跳过后者直接进入 codegen。

前置条件：

- 输入 `module` 已完成 AST/IR 发射，必须是可解析的 `builtin.module`。
- `module` 内 `nn` op 的结果类型必须是 `nn.memory`，并包含必要的 `nn.space` attribute。

后置条件：

- 输出 module 不得包含任何 `nn` op；所有支持的 `nn` op 必须替换为对应 `kernel` op。
- `dma.alloc` 的 `shape/space/dtype` 与原 `nn` 结果保持一致。
- 若原 module 含跨函数 `memory-return func.call`，本 pass 完成后仍允许暂时保留旧函数 ABI；调用点同步改写不是本 pass 的职责，必须交由下游 `BufferResultsToOutParamsPass` 收口。

返回与限制：

- 返回完成 lowering 后的 module（可原地修改或返回新对象，以实现为准）。
- 不支持的 op 必须抛出错误，不能静默跳过。

### `LowerNnToKernelPass.run(module)`

功能说明：

- 对输入 module 执行 `nn -> kernel` lowering。
- 将 `nn` op 替换为 `kernel` op，并插入必要的 `dma.alloc`。

参数说明：

- `module (builtin.module)`：包含 `func.func` 的 IR module。

使用示例：

```python
pass_obj = LowerNnToKernelPass()
module = pass_obj.run(module)
```

注意事项：

- 当 `nn` op 结果需要输出 Memory 时，必须生成 `dma.alloc`，并保持 `shape/stride/type/space` 与原结果一致。
- 若同一块内出现多个 `nn` op，必须按出现顺序逐个 lower，保证数据依赖不变。
- 二元 op 名称映射约束如下：
  - `nn.add -> kernel.add`
  - `nn.sub -> kernel.sub`
  - `nn.mul -> kernel.mul`
  - `nn.div -> kernel.div`
  - `nn.truediv -> kernel.div`
  - `nn.eq -> kernel.eq`
  - `nn.ne -> kernel.ne`
  - `nn.lt -> kernel.lt`
  - `nn.le -> kernel.le`
  - `nn.gt -> kernel.gt`
  - `nn.ge -> kernel.ge`
- 二元 op（含比较）operand arity 固定为 2；`nn.select` 固定为 3；`nn.cast` 固定为 1；不满足时必须报错 `nn op <name> expects <expected> operands, got <actual>`。
  - 结构化 op 的 mapping 约束如下：
    - `nn.broadcast -> dma.broadcast`
    - `nn.transpose -> dma.transpose`
    - `nn.exp -> kernel.exp`
    - `nn.softmax -> kernel.softmax`
    - `nn.reduce_sum -> kernel.reduce_sum`
    - `nn.reduce_min -> kernel.reduce_min`
    - `nn.reduce_max -> kernel.reduce_max`
    - `nn.matmul -> kernel.matmul`
    - `nn.img2col1d -> kernel.img2col1d`
    - `nn.img2col2d -> kernel.img2col2d`

前置条件：

- `module` 必须包含至少一个 `func.func` 或为空 module；当无 `func.func` 时直接返回原 module。
- 传入的 `module` 必须是可遍历 IR；无法遍历或解析时视为 AST 发射失败。

后置条件：

- 若成功完成，结果 module 不包含任何 `nn` op；否则必须抛出 `LowerNnToKernelError`。

返回与限制：

- 返回 lowering 后的 module。
- 不允许保留任何 `nn` op；若存在，视为 pass 失败。

## 额外补充

### 职责矩阵与 lowering 目标面（机械写死）

- `spec/operation/nn.md`：定义高层 helper 的 shape/axis/参数语义与错误边界；允许“隐式 broadcast”的语义表述，但不得把“隐式 broadcast”推给 `kernel` 层兜底。
- `spec/dialect/nn.md`：定义 `nn` 方言字段与 verifier；不支持逐元素隐式 broadcast（广播必须显式使用 `nn.broadcast`）。
- `spec/dialect/dma.md`：定义纯物化/搬运/布局变换原语；本计划冻结 `dma.broadcast` 与 `dma.transpose` 作为 lowering 目标面（不承担计算语义）。
- `spec/dialect/kernel.md`：定义纯计算原语；不允许隐式 broadcast；compare 只接受 memory operand。
- `LowerNnToKernelPass`（本文件）：负责把 `nn` 方言 rewrite 到 `dma/kernel` 方言，并补齐 mixed compare 桥接与输出分配；不得 silent fallback。

### lowering 矩阵（从 nn 方言到目标面）

| nn 侧输入 | 目标面 | 关键约束 |
| --- | --- | --- |
| `nn.broadcast`（含由 `operation.broadcast_to` 归一化而来） | `dma.broadcast` | 必须显式物化，不允许在 `kernel` 层保留隐式 broadcast |
| `nn.transpose` | `dma.transpose` | `perm` 必须为合法排列，目标 shape 必须机械一致 |
| `nn.eq/ne/lt/le/gt/ge`（memory+memory） | `kernel.compare family` | operand 必须同 shape；禁止 kernel 层隐式 broadcast |
| `nn.eq/ne/lt/le/gt/ge`（memory+symbol/const） | `dma.broadcast -> kernel.compare family` | 必须先物化 scalar/symbol 到 temporary memory，再 compare |
| `nn.exp` | `kernel.exp` | 仅浮点；输入/输出 shape/space 一致 |
| `nn.reduce_*` | `kernel.reduce_*` | `axis/keepdim` 与 out.shape 必须机械一致 |
| `nn.softmax` | `kernel.softmax` | `axis` 保持不变，输入/输出 shape/space 一致 |
| `nn.matmul` | `kernel.matmul` | 仅二维；`[M,K] x [K,N] -> [M,N]` 机械一致 |
| `nn.img2col1d/nn.img2col2d` | `kernel.img2col1d/kernel.img2col2d` | 保持结构化输出维度，不允许压扁 |

## 测试

- 测试文件：[`test/pass/test_lowering_nn_to_kernel.py`](../../../test/pass/test_lowering_nn_to_kernel.py)
- 执行命令：
  - `pytest -q test/pass/test_lowering_nn_to_kernel.py`
- 测试目标：
  - 验证支持的 `nn` op 被替换为 `kernel/dma` op，且 `nn.truediv`/`nn.div` 统一映射到 `kernel.div`。
  - 验证 `nn.broadcast/nn.transpose` 分别 lower 到 `dma.broadcast/dma.transpose`。
  - 验证 `nn.softmax` 被改写为 `kernel.softmax`，并保留 `axis` 属性。
  - 验证 mixed compare 触发 `dma.alloc + dma.broadcast -> kernel.compare` 桥接路径，且 `kernel.compare` 不直接接收非 memory operand。
  - 验证输出 Memory 由 `dma.alloc` 创建，且类型/空间与原结果一致。
  - 验证 `dma.alloc` 结果类型中的 `shape` 维度值与原 `nn` 结果保持一致。
  - 验证不支持 op、结果类型非法、缺失 `nn.space`、operand 数量不匹配或 kernel 校验失败时抛出明确错误。
  - 目录级黑盒 gate（expectation）作为门禁证据写入任务记录，不在 spec 文件内绑定具体 expectation 文件路径。
- 功能与用例清单：

| 用例 ID | 约束点 | 对应测试 |
| --- | --- | --- |
| COV-N2K-001 | 缺失 `nn.space` attribute 抛错 | `test_lower_missing_space_attribute_raises` |
| COV-N2K-002 | `nn` op 多结果抛错 | `test_lower_rejects_multi_result_op` |
| COV-N2K-003 | `nn` op 结果类型非 `nn.memory` 抛错 | `test_lower_rejects_non_memory_result_type` |
| COV-N2K-004 | `nn` op operand 数量不匹配抛错 | `test_lower_rejects_operand_count_mismatch` |
| COV-N2K-005 | kernel op 校验失败转为 `LowerNnToKernelError` | `test_lower_wraps_kernel_verify_exception` |
| COV-N2K-006 | 包含 region 的 op 触发递归 lowering | `test_lower_recurses_into_regions` |
| COV-N2K-007 | module 内残留 `nn` op 抛错 | `test_ensure_no_nn_ops_raises` |
| COV-N2K-008 | 静态维度 `shape` 在 `dma.alloc` 中保持一致 | `test_lower_preserves_static_shape_in_alloc` |
| COV-N2K-009 | 符号维度 `shape` 在 `dma.alloc` 中保持一致 | `test_lower_preserves_symbol_shape_in_alloc` |
| COV-N2K-010 | `nn.add -> kernel.add` 目录级黑盒 gate 覆盖（门禁证据见任务记录） | `-` |
| COV-N2K-011 | `nn.sub -> kernel.sub` 目录级黑盒 gate 覆盖（门禁证据见任务记录） | `-` |
| COV-N2K-012 | `nn.mul -> kernel.mul` 目录级黑盒 gate 覆盖（门禁证据见任务记录） | `-` |
| COV-N2K-013 | `nn.eq -> kernel.eq` 目录级黑盒 gate 覆盖（门禁证据见任务记录） | `-` |
| COV-N2K-014 | `nn.lt -> kernel.lt` 目录级黑盒 gate 覆盖（门禁证据见任务记录） | `-` |
| COV-N2K-015 | `nn.gt -> kernel.gt` 目录级黑盒 gate 覆盖（门禁证据见任务记录） | `-` |
| COV-N2K-016 | `nn.ne -> kernel.ne` 目录级黑盒 gate 覆盖（门禁证据见任务记录） | `-` |
| COV-N2K-017 | `nn.le -> kernel.le` 目录级黑盒 gate 覆盖（门禁证据见任务记录） | `-` |
| COV-N2K-018 | `nn.ge -> kernel.ge` 目录级黑盒 gate 覆盖（门禁证据见任务记录） | `-` |
| COV-N2K-019 | `nn.truediv -> kernel.div` 目录级黑盒 gate 覆盖（门禁证据见任务记录） | `-` |
| COV-N2K-020 | `nn.ne -> kernel.ne` 单测映射（实现阶段新增） | `test_lower_ne_to_kernel` |
| COV-N2K-021 | `nn.le -> kernel.le` 单测映射（实现阶段新增） | `test_lower_le_to_kernel` |
| COV-N2K-022 | `nn.ge -> kernel.ge` 单测映射（实现阶段新增） | `test_lower_ge_to_kernel` |
| COV-N2K-023 | `nn.truediv -> kernel.div` 单测映射（实现阶段新增） | `test_lower_truediv_to_kernel_div` |
| COV-N2K-024 | `run(module)` 拒绝非 `builtin.module` 输入并统一归因为 `LowerNnToKernelError` | `test_run_rejects_non_module_input` |
| COV-N2K-025 | `run(module)` 拒绝 `module.ops` 不可遍历输入并统一归因为 `LowerNnToKernelError` | `test_run_rejects_non_iterable_module_ops` |
| COV-N2K-026 | `nn.softmax` 直接 lower 为 `kernel.softmax` 并保留 `axis` | `test_lower_softmax_direct_dialect_op_to_kernel_softmax` |
| COV-N2K-027 | 公开链路 `build_func_op -> LowerNnToKernelPass` 的 `softmax` helper lower 为 `kernel.softmax` | `test_lower_softmax_public_chain_to_kernel_softmax` |

## 失败归因

- AST 发射失败：`module` 非 `builtin.module`、无法遍历或缺失必要结构，lowering 进入前即无法执行。
- Dialect verify 失败：`kernel` 或 `dma` op verifier 抛错（类型/space/operand 约束不满足）时，必须包装为 `LowerNnToKernelError` 并中止。
- Lowering 失败：不支持的 `nn` op、结果类型非法、缺失 `nn.space`、operand 数量不匹配或 `dma.alloc` 构造失败导致的错误均归类为 lowering 失败。
