# kernel_decompose.md

## 功能简介

- 定义 `kernel-decompose` pass 的公开合同。
- 该 pass 在 source/emit 前把 `kernel.matmul_fusion` 分解为带动态 acc operand 的单条 `kernel.matmul`。
- 该 pass 不删除 `dma.fill`；所有 fill 删除由后续 canonicalization 按 `dma.fill` 合同判断。

## API 列表

- `class KernelDecomposePass(fold: bool = True)`
- `KernelDecomposePass.from_options(options: dict[str, str]) -> KernelDecomposePass`
- `KernelDecomposePass.apply(ctx: Context, module: ModuleOp) -> None`

## 文档信息

- `spec`：`spec/pass/kernel/kernel_decompose.md`
- `功能实现`：`kernel_gen/passes/kernel/kernel_decompose.py`
- `test`：`test/passes/kernel/test_kernel_decompose.py`
- `test`：`test/passes/test_registry.py`，验证 `kernel-decompose` registry 名称、旧 registry 名称退场和旧 module import 失败边界。
- `test`：`test/passes/pipeline/test_npu_demo_lowering.py`，验证 `npu-demo-lowering` 中 `kernel-aggregate -> kernel-decompose -> producer-consumer-analysis -> memory-pool` 相对顺序与 dump marker。

## 依赖

- `kernel.matmul_fusion`：[`spec/dialect/kernel.md`](../../dialect/kernel.md)
- `kernel.matmul`：[`spec/dialect/kernel.md`](../../dialect/kernel.md)
- pass registry：[`spec/pass/registry.md`](../registry.md)

## API详细说明

### `class KernelDecomposePass(fold: bool = True)`

- api：`class KernelDecomposePass(fold: bool = True)`
- 参数：
  - `fold`：通用 pattern rewrite folding 开关；类型 `bool`；默认值为 `True`；不允许 `None`；该参数只控制 pass walker 的通用 folding 行为，不引入本 pass 专属语义。
- 返回值：`KernelDecomposePass` 实例；实例可通过 `apply(ctx, module)` 对 `ModuleOp` 执行分解。
- 使用示例：

  ```python
  from kernel_gen.passes.kernel.kernel_decompose import KernelDecomposePass

  kernel_decompose = KernelDecomposePass()
  ```

- 功能说明：`KernelDecomposePass` 是公开 pass 入口，registry name 固定为 `kernel-decompose`；第一版负责把 `kernel.matmul_fusion(out,lhs,rhs,acc)` 规整为单条带动态 acc operand 的 `kernel.matmul(out,lhs,rhs,acc)`，并保留已有 `dma.fill`。
- 注意事项：
  - 本 pass 只处理 `kernel.matmul_fusion`，不处理其它 kernel 聚合 op。
  - 分解后不得残留 `kernel.matmul_fusion`，不得生成旧 `scf.if` 双分支，且不得写静态 `acc=true/false` attr。
  - `kernel.matmul_fusion.fusion_list` 是 metadata；非空字符串不得改变输出 IR，不得复制到普通 `kernel.matmul`。
  - 本 pass 不新增 include helper；source/emit 由 `kernel.matmul` 动态 acc 直接承接现有 `npu_demo::matmul(..., bool acc)` 参数。
  - 本 pass 不是 `dma.fill` canonicalization；不得在 `apply(...)` 处理 fusion 时删除任何 `dma.fill`。

### `KernelDecomposePass.from_options(options: dict[str, str]) -> KernelDecomposePass`

- api：`KernelDecomposePass.from_options(options: dict[str, str]) -> KernelDecomposePass`
- 参数：
  - `options`：registry 传入的 pass option 字典；类型 `dict[str, str]`；无默认值，调用方必须显式提供；不允许 `None`；第一版必须为空字典。
- 返回值：`KernelDecomposePass` 实例；当前等价于 `KernelDecomposePass()`。
- 使用示例：

  ```python
  from kernel_gen.passes.kernel.kernel_decompose import KernelDecomposePass

  kernel_decompose = KernelDecomposePass.from_options({})
  ```

- 功能说明：从 registry option 字典构造 `KernelDecomposePass`，用于 `kernel-decompose` pass name 的公开构造路径。
- 注意事项：
  - 第一版无自定义 option；`options` 非空时必须失败。
  - unknown option 的稳定错误短语必须包含 `kernel-decompose options`。
  - 本方法不得接受旧 `kernel-matmul-fusion-decompose` 名称或旧 pass option 作为兼容入口。

### `KernelDecomposePass.apply(ctx: Context, module: ModuleOp) -> None`

- api：`KernelDecomposePass.apply(ctx: Context, module: ModuleOp) -> None`
- 参数：
  - `ctx`：xDSL `Context`；无默认值，调用方必须显式提供；不允许 `None`；用于 pattern rewrite walker 的上下文。
  - `module`：xDSL `ModuleOp`；无默认值，调用方必须显式提供；不允许 `None`；必须是 builtin module，非 builtin module 必须按 pass 公共校验失败。
- 返回值：`None`；成功时原地修改 `module`，失败时抛出 `KernelCodeError` 或底层 verifier 错误。
- 使用示例：

  ```python
  from xdsl.context import Context
  from kernel_gen.passes.kernel.kernel_decompose import KernelDecomposePass

  KernelDecomposePass().apply(Context(), module)
  ```

- 功能说明：遍历 `module` 中的 `kernel.matmul_fusion`，把每个 fusion 分解为单条动态 acc matmul：

  ```text
  kernel.matmul(%out, %lhs, %rhs, %acc)
  ```

  分解后不得保留 `kernel.matmul_fusion`；局部生成的动态 acc matmul verifier 失败时必须 fail-fast，稳定错误短语包含 `kernel-decompose matmul acc`。已有 `dma.fill` 必须保留，等待后续 `CanonicalizePass` 按 `dma.fill` 合同判断是否删除。
- 注意事项：
  - 不根据 loop trip count、acc 形态、zero 常量或 out alias live-read 情况删除 fill。
  - `kernel.matmul_fusion.fusion_list` 只作为 metadata 被丢弃，不影响 fill 是否保留。
  - 旧 `expectation.pass.kernel_decompose` initial fill 删除 case 已按用户确认降为历史只读来源，不列为本 spec 当前必过合同验收。

## 测试

- 测试文件：`test/passes/kernel/test_kernel_decompose.py`
- 测试文件：`test/passes/test_registry.py`
- 测试文件：`test/passes/pipeline/test_npu_demo_lowering.py`
- 执行命令：`pytest -q test/passes/kernel/test_kernel_decompose.py`
- 执行命令：`pytest -q test/passes/test_registry.py -k 'kernel_aggregate or kernel_decompose'`
- 执行命令：`pytest -q test/passes/pipeline/test_npu_demo_lowering.py`
- 历史只读合同来源：旧 `expectation.pass.kernel_decompose` initial fill 删除 case；按用户确认，该 case 不列为当前必过合同验收。

### 测试目标

- 验证 `kernel-decompose` registry 入口、option 失败语义、fusion 分解、dynamic acc matmul verifier 失败语义、fill 保留职责边界、旧 pass 名称退场和 pipeline 顺序。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-PASS-KERNEL-DECOMPOSE-001 | fusion 分解 | 静态 shape fusion | IR 含 `kernel.matmul_fusion` | 执行 `pytest -q test/passes/kernel/test_kernel_decompose.py` | 分解为单条动态 acc `kernel.matmul`，不生成 `scf.if` 或静态 acc attr | `test_kernel_decompose_static_dynamic_acc_matmul` |
| TC-PASS-KERNEL-DECOMPOSE-002 | fusion 分解 | 动态 shape fusion | IR 含动态 shape `kernel.matmul_fusion` | 执行 `pytest -q test/passes/kernel/test_kernel_decompose.py` | 分解为单条动态 acc `kernel.matmul`，不插入 `symbol.get_dim` | `test_kernel_decompose_dynamic_shape_dynamic_acc_matmul` |
| TC-PASS-KERNEL-DECOMPOSE-003 | no-op | 无 fusion | IR 不含 `kernel.matmul_fusion` | 执行 `pytest -q test/passes/kernel/test_kernel_decompose.py` | module 保持 no-op | `test_kernel_decompose_no_fusion_no_op` |
| TC-PASS-KERNEL-DECOMPOSE-004 | option 失败 | unknown option | registry 传入非空 option | 执行 `pytest -q test/passes/kernel/test_kernel_decompose.py` | fail-fast，错误短语包含 `kernel-decompose options` | `test_kernel_decompose_rejects_options` |
| TC-PASS-KERNEL-DECOMPOSE-005 | metadata 丢弃 | 非空 `fusion_list` | IR fusion 带非空 `fusion_list` | 执行 `pytest -q test/passes/kernel/test_kernel_decompose.py` | 输出不残留 `fusion_list` metadata | `test_kernel_decompose_ignores_fusion_list_metadata` |
| TC-PASS-KERNEL-DECOMPOSE-006 | fill 保留 | initial zero fill | loop 中 acc 为 `symbol.ne(k_iter,k_start)` | 执行 `pytest -q test/passes/kernel/test_kernel_decompose.py` | 保留 `dma.fill(out, 0)`，并分解 fusion 为动态 acc matmul | `test_kernel_decompose_keeps_zero_fill_before_dynamic_acc_matmul` |
| TC-PASS-KERNEL-DECOMPOSE-007 | fill 保留 | loop 前纯 alias setup | fill 与 loop 之间仅有 NoMemoryEffect alias setup | 执行 `pytest -q test/passes/kernel/test_kernel_decompose.py` | 保留 initial fill，只分解 fusion | `test_kernel_decompose_keeps_fill_with_pure_alias_setup_before_k_loop` |
| TC-PASS-KERNEL-DECOMPOSE-008 | fill 保留 | loop 前 alias 写入 | fill 与 loop 之间存在 out alias 写入 | 执行 `pytest -q test/passes/kernel/test_kernel_decompose.py` | 保留所有 fill，只分解 fusion | `test_kernel_decompose_keeps_fill_for_alias_write_before_k_loop` |
| TC-PASS-KERNEL-DECOMPOSE-009 | fill 保留 | acc 无法证明首轮覆盖 | fusion acc 不是 `symbol.ne(k_iter,k_start)` | 执行 `pytest -q test/passes/kernel/test_kernel_decompose.py` | 保留 `dma.fill`，只分解 fusion | `test_kernel_decompose_keeps_fill_for_noncanonical_acc` |
| TC-PASS-KERNEL-DECOMPOSE-010 | fill 保留 | 同一 loop body 内 fusion 前读取 out | fusion 前存在 out 读或 alias 闭包使用 | 执行 `pytest -q test/passes/kernel/test_kernel_decompose.py` | 保留 initial fill，只分解 fusion | `test_kernel_decompose_keeps_fill_when_loop_body_reads_out_before_fusion` |
| TC-PASS-KERNEL-DECOMPOSE-012 | 稳定错误 | fusion acc 非 i1 导致动态 matmul局部 verifier 失败 | fusion acc 类型为非 i1 | 执行 `pytest -q test/passes/kernel/test_kernel_decompose.py` | fail-fast `kernel-decompose matmul acc`，不得泄漏 `NameError` | `test_kernel_decompose_reports_stable_error_for_invalid_fusion_acc` |
