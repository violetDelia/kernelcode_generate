# kernel_matmul_fusion_decompose.md

## 功能简介

- 定义 `kernel-matmul-fusion-decompose` pass 的公开合同。
- 该 pass 在 source/emit 前把 `kernel.matmul_fusion` 分解为既有可 emit IR。

## API 列表

- `class KernelMatmulFusionDecomposePass(fold: bool = True)`
- `KernelMatmulFusionDecomposePass.from_options(options: dict[str, str]) -> KernelMatmulFusionDecomposePass`
- `KernelMatmulFusionDecomposePass.apply(ctx: Context, module: ModuleOp) -> None`

## 依赖

- `kernel.matmul_fusion`：[`spec/dialect/kernel.md`](../dialect/kernel.md)
- `kernel.matmul` / `kernel.binary_elewise`：[`spec/dialect/kernel.md`](../dialect/kernel.md)
- pass registry：[`spec/pass/registry.md`](registry.md)

## 公开语义

- registry name 固定为 `kernel-matmul-fusion-decompose`。
- 第一版无自定义 option；unknown option 必须失败，错误短语包含 `kernel-matmul-fusion-decompose options`。
- 每个 `kernel.matmul_fusion(out,lhs,rhs,acc)` 分解为：

```text
scf.if %acc {
  %tmp = dma.alloc : <same memory type as out>
  kernel.matmul(%tmp, %lhs, %rhs)
  kernel.binary_elewise(%out, %out, %tmp) {kind = "add"}
  dma.free %tmp
} else {
  kernel.matmul(%out, %lhs, %rhs)
}
```

- `%tmp` type 必须与 `out` type 完全一致；无法构造时 fail-fast，错误短语包含 `kernel-matmul-fusion-decompose tmp type`。
- 成功后 module 中不得残留 `kernel.matmul_fusion`。
- 本 pass 不新增 include helper、不新增 emitC/gen_kernel source 分支、不改变旧 `kernel.matmul` 语义。

## 使用示例

```python
from kernel_gen.passes.kernel_matmul_fusion_decompose import KernelMatmulFusionDecomposePass

KernelMatmulFusionDecomposePass().apply(ctx, module)
```

## 测试

- `pytest -q test/passes/test_kernel_matmul_fusion_decompose.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python3 -m expectation.pass.kernel_matmul_fusion_decompose`

## 用例矩阵

| 用例 ID | 场景 | 预期 | 建议测试 |
| --- | --- | --- | --- |
| TC-PASS-KERNEL-MATMUL-FUSION-DECOMPOSE-001 | 静态 fusion | 分解为 `scf.if`，true 分支 tmp+matmul+add+free，else 分支 matmul(out) | `test_kernel_matmul_fusion_decompose_static_scf_if` |
| TC-PASS-KERNEL-MATMUL-FUSION-DECOMPOSE-002 | 动态 shape fusion | 插入必要 `symbol.get_dim`，tmp 与 out type 完全一致 | `test_kernel_matmul_fusion_decompose_dynamic_scf_if` |
| TC-PASS-KERNEL-MATMUL-FUSION-DECOMPOSE-003 | 无 fusion | no-op | `test_kernel_matmul_fusion_decompose_no_fusion_no_op` |
| TC-PASS-KERNEL-MATMUL-FUSION-DECOMPOSE-004 | unknown option | fail-fast `kernel-matmul-fusion-decompose options` | `test_kernel_matmul_fusion_decompose_rejects_options` |
