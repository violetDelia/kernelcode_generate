# template_name_default_constraints

## 功能简介

- 定义当前仓库内置 DMA / Kernel / 透明 cast memory op 的默认 template-name 约束注册入口。
- 本文件只注册约束，不承载 pass 遍历、graph 求解或 IR 写回逻辑。
- 当前文件内 builder 只作为注册表回调，不是跨文件公开 API。

## API 列表

- `register_default_template_constraints() -> None`

## 文档信息

- `spec`：[`spec/pass/template_name_default_constraints.md`](../../spec/pass/template_name_default_constraints.md)
- `功能实现`：[`kernel_gen/passes/template_name_default_constraints.py`](../../kernel_gen/passes/template_name_default_constraints.py)
- `test`：[`test/passes/test_template_name_constraints.py`](../../test/passes/test_template_name_constraints.py)、[`test/passes/test_template_name_infer.py`](../../test/passes/test_template_name_infer.py)

## 目标

- `dma.copy`、`dma.reshape`、`dma.slice`、`dma.deslice`、`dma.load`、`dma.store`、`dma.broadcast`、`dma.transpose` 等同 dtype/layout 流转 op 使用 Same 语义。
- `dma.view` 普通 source/result 使用 Same 语义；当 source 是一维 `i8` byte backing pool 且 result 是 typed memory 时，仅校验 source/result，不把 byte pool 与 typed view 合并为同一 template family。
- `kernel.binary_elewise`、`kernel.exp`、`kernel.reduce`、`kernel.reduce_min`、`kernel.img2col1d`、`kernel.img2col2d`、`kernel.select` 使用 Same 语义。
- `arch.get_dynamic_memory`、`arch.launch`、`dma.alloc`、`dma.fill`、`dma.free`、`dma.cast`、`dma.subview`、`kernel.matmul`、`symbol.get_dim`、`symbol.get_stride` 使用 VerifyOnly 语义。
- `kernel.matmul` 的 out/lhs/rhs 不由 matmul 本身合并为同一 family。
- `nn.*` op 约束不属于本计划完成态。

## API 详细说明

### `register_default_template_constraints() -> None`

- 功能：幂等注册当前默认约束矩阵。
- 错误：默认矩阵外的 memory op 仍由 `build_template_constraints(op)` 负责稳定失败，不允许本入口吞掉漏项。

## 测试

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_template_name_constraints.py test/passes/test_template_name_infer.py`
