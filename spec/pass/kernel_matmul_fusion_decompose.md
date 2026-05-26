# kernel_matmul_fusion_decompose.md

## 功能简介

- 定义 `kernel-matmul-fusion-decompose` pass 的公开合同。
- 该 pass 在 source/emit 前把 `kernel.matmul_fusion` 分解为带静态 `acc` 属性的 `kernel.matmul` 分支 IR；`fusion_list` 字符串 metadata 不参与分解决策。

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
  kernel.matmul(%out, %lhs, %rhs) {acc = true}
} else {
  kernel.matmul(%out, %lhs, %rhs) {acc = false}
}
```

- 该 pass 不创建临时 `dma.alloc`、不生成 `kernel.binary_elewise add`、不插入 `dma.free`，也不为动态 shape 额外插入 `symbol.get_dim`；shape/type 合同由原 `kernel.matmul_fusion` verifier 与目标 `kernel.matmul` verifier 共同保证。
- `kernel.matmul_fusion.fusion_list` 是 metadata；非空字符串不得改变输出 IR，不得复制到普通 `kernel.matmul`。
- 成功后 module 中不得残留 `kernel.matmul_fusion`。
- 本 pass 不新增 include helper、不新增 emitC/gen_kernel source 分支；它依赖 `kernel.matmul(acc=false|true)` 与 include `npu_demo::matmul(..., bool acc=false)` 公开累加语义。

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
| TC-PASS-KERNEL-MATMUL-FUSION-DECOMPOSE-001 | 静态 fusion | 分解为 `scf.if`，true 分支 `kernel.matmul(acc=true)`，else 分支 `kernel.matmul(acc=false)`，不生成 tmp/add/free | `test_kernel_matmul_fusion_decompose_static_scf_if` |
| TC-PASS-KERNEL-MATMUL-FUSION-DECOMPOSE-002 | 动态 shape fusion | 分解为相同两分支 matmul，不插入 `symbol.get_dim`、tmp、add 或 free | `test_kernel_matmul_fusion_decompose_dynamic_scf_if` |
| TC-PASS-KERNEL-MATMUL-FUSION-DECOMPOSE-003 | 无 fusion | no-op | `test_kernel_matmul_fusion_decompose_no_fusion_no_op` |
| TC-PASS-KERNEL-MATMUL-FUSION-DECOMPOSE-004 | unknown option | fail-fast `kernel-matmul-fusion-decompose options` | `test_kernel_matmul_fusion_decompose_rejects_options` |
| TC-PASS-KERNEL-MATMUL-FUSION-DECOMPOSE-005 | 非空 fusion_list | 分解结果与普通 fusion 相同，输出不残留 `fusion_list` metadata | `test_kernel_matmul_fusion_decompose_ignores_fusion_list_metadata` |
