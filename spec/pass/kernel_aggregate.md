# kernel_aggregate.md

## 功能简介

- 定义 `kernel-aggregate` pass 的公开合同。
- `KernelAggregatePass(matmul_acc=True)` 将同 block 相邻 `kernel.matmul(tmp,lhs,rhs)` 与 `kernel.binary_elewise(out,out,tmp){kind="add"}` 聚合为 `kernel.matmul_fusion(out,lhs,rhs,acc,fusion_list="kernel.matmul,kernel.binary_elewise.add")`；tmp alloc/free 可位于同 block 或包住目标 loop 的祖先 owner block。
- `acc` 由 K/reduce owner `symbol.for` 的 iterator 与 start 通过 `symbol.ne` 生成。

## API 列表

- `class KernelAggregatePass(matmul_acc: bool = False, fold: bool = True)`
- `KernelAggregatePass.from_options(options: dict[str, str]) -> KernelAggregatePass`
- `KernelAggregatePass.apply(ctx: Context, module: ModuleOp) -> None`

## 依赖

- `kernel.matmul_fusion`：[`spec/dialect/kernel.md`](../dialect/kernel.md)
- `symbol.ne` / `symbol.for`：[`spec/dialect/symbol.md`](../dialect/symbol.md)
- pass registry：[`spec/pass/registry.md`](registry.md)

## 公开语义

- registry name 固定为 `kernel-aggregate`。
- 唯一专属 option 为 `matmul-acc=true|false|1|0|yes|no|on|off`，默认 `false`。
- unknown option 或非法 bool 必须失败，错误短语包含 `kernel-aggregate options`。
- `matmul_acc=False` 时 no-op。
- `matmul_acc=True` 时仅匹配同 block 相邻 `kernel.matmul` 后接 `kernel.binary_elewise(kind="add")` 的形态。
- 命中时生成的 `kernel.matmul_fusion` 必须携带固定 `fusion_list = "kernel.matmul,kernel.binary_elewise.add"` 字符串 metadata；该 metadata 不改变后续 decompose 语义。
- add 必须是 `out = out + tmp`，其中 `tmp` 是 matmul out。
- tmp 必须来自唯一 `dma.alloc`，只有 matmul 写、add 读和唯一 `dma.free` use；extra use、alias use、metadata use、缺 free 或多 free 均 no-op。
- tmp alloc/free 位于祖先 owner block 时，必须证明 owner block 内 `dma.alloc` 早于承载 matmul/add 的 owner loop，且唯一 `dma.free` 晚于该 owner loop；无法证明时 no-op。
- K/reduce owner 必须唯一可证明；找不到、多候选或误选 M/N loop 必须 fail-fast，错误短语包含 `kernel-aggregate matmul acc iterator`。
- 多个独立 pair 可逐个聚合；共享 tmp 或歧义必须 fail-fast，错误短语包含 `kernel-aggregate ambiguous matmul fusion`。

## 使用示例

```python
from kernel_gen.passes.kernel_aggregate import KernelAggregatePass

KernelAggregatePass(matmul_acc=True).apply(ctx, module)
```

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m kernel_gen.tools.ircheck case.ircheck
```

## 测试

- `pytest -q test/passes/test_kernel_aggregate.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.kernel_aggregate`

## 用例矩阵

| 用例 ID | 场景 | 预期 | 建议测试 |
| --- | --- | --- | --- |
| TC-PASS-KERNEL-AGGREGATE-001 | zero-start K/reduce owner | 生成 `symbol.ne(k_iter,k_start)` 与带固定 `fusion_list` 的 `kernel.matmul_fusion`，删除原 tmp alloc/free、matmul、add | `test_kernel_aggregate_fuses_zero_start_reduce_owner` |
| TC-PASS-KERNEL-AGGREGATE-002 | nonzero start | acc 与实际 loop start 比较，不写死 0 | `test_kernel_aggregate_fuses_nonzero_start_reduce_owner` |
| TC-PASS-KERNEL-AGGREGATE-003 | dynamic start | acc 使用公开 start SSA value | `test_kernel_aggregate_fuses_dynamic_start_reduce_owner` |
| TC-PASS-KERNEL-AGGREGATE-004 | nested K owner | 选择 contracting dimension owner，不按最近 loop 猜测 | `test_kernel_aggregate_fuses_nested_k_owner` |
| TC-PASS-KERNEL-AGGREGATE-004A | outer tmp lifecycle nested K owner | tmp alloc/free 位于祖先 owner block 且包住目标 K loop 时可聚合，删除 tmp 生命周期 | `test_kernel_aggregate_fuses_outer_tmp_lifetime_nested_k_owner` |
| TC-PASS-KERNEL-AGGREGATE-005 | 多个 K owner 候选 | fail-fast `kernel-aggregate matmul acc iterator` | `test_kernel_aggregate_rejects_multiple_k_owner_candidates` |
| TC-PASS-KERNEL-AGGREGATE-006 | M/N loop 误选 | fail-fast `kernel-aggregate matmul acc iterator` | `test_kernel_aggregate_rejects_m_or_n_loop_as_acc_owner` |
| TC-PASS-KERNEL-AGGREGATE-007 | extra tmp use / matmul-acc=false | no-op | `test_kernel_aggregate_keeps_extra_tmp_use_no_op`, `test_kernel_aggregate_matmul_acc_false_no_op` |
