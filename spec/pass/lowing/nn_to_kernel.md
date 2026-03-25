# nn_to_kernel.md

## 功能简介

- 定义将 `nn` dialect IR lower 到 `kernel` dialect IR 的 pass 规范。
- 当需要为结果分配输出 Memory 时，使用 `dma.alloc`。
- 不负责高层语义推导、跨函数优化或后端代码生成。

## 文档信息

- 创建者：`摸鱼小分队`
- 最后一次更改：`摸鱼小分队`
- `spec`：[`spec/pass/lowing/nn_to_kernel.md`](../../../spec/pass/lowing/nn_to_kernel.md)
- `功能实现`：[`kernel_gen/passes/lowing/nn_to_kernel.py`](../../../kernel_gen/passes/lowing/nn_to_kernel.py)
- `test`：[`test/pass/test_lowing_nn_to_kernel.py`](../../../test/pass/test_lowing_nn_to_kernel.py)

## 依赖

- Pass 抽象与管理器：[`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)
- NN dialect 语义：[`spec/dialect/nn.md`](../../../spec/dialect/nn.md)
- Kernel dialect 语义：[`spec/dialect/kernel.md`](../../../spec/dialect/kernel.md)
- DMA dialect（输出分配）：[`spec/dialect/dma.md`](../../../spec/dialect/dma.md)

## 目标

- 将 `nn` dialect 的逐元素算术/比较/select/cast lower 为 `kernel` dialect 对应 op。
- 保证 Memory 类型与空间在 lowering 前后保持一致，输出 Memory 由 `dma.alloc` 创建并交给 kernel op 使用。
- 产出仅包含 `kernel`/`dma`/`func`/`builtin` 等必要 op，不再保留 `nn` op。

## 限制与边界

- 仅支持以下 `nn` op lowering：`nn.add`/`nn.sub`/`nn.mul`/`nn.div`、`nn.eq`/`nn.lt`/`nn.gt`、`nn.select`、`nn.cast`。
- 不处理 broadcast、reduce、matmul、conv、control-flow 等高阶或结构性 op。
- 不改写函数签名或返回语义，不引入新的返回约束；仅在函数体内替换 op。
- 当 `nn` op 结果需要输出 Memory 时，必须插入 `dma.alloc`；不允许隐式创建其他分配方式。
- 遇到不支持的 `nn` op 或类型不一致，必须抛出明确错误并中止 pass。

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
from kernel_gen.passes.lowing.nn_to_kernel import LowerNnToKernelPass

pm = PassManager(name="lowering")
pm.add_pass(LowerNnToKernelPass())
module = pm.run(module)
```

注意事项：

- pass 只对 `func.func` 中的 `nn` op 生效。
- 输出 Memory 由 `dma.alloc` 创建，并作为 kernel op 的 `outs` operand。

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

返回与限制：

- 返回 lowering 后的 module。
- 不允许保留任何 `nn` op；若存在，视为 pass 失败。

## 测试

- 测试文件：[`test/pass/test_lowing_nn_to_kernel.py`](../../../test/pass/test_lowing_nn_to_kernel.py)
- 执行命令：`pytest -q test/pass/test_lowing_nn_to_kernel.py`
- 测试目标：
  - 验证支持的 `nn` op 被替换为 `kernel` op。
  - 验证输出 Memory 由 `dma.alloc` 创建，且类型/空间与原结果一致。
  - 验证不支持 op 或类型不一致时抛出错误。
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
