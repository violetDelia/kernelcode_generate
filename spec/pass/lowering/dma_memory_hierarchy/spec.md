# dma_memory_hierarchy

## 功能简介

- 定义 `lower-dma-memory-hierarchy` pass 的公开入口、规则语法、默认行为与错误语义。
- 默认 `LowerDmaMemoryHierarchyPass()` 不配置 `apply_op` 时保持 no-op，不再隐式执行固定 `GM -> SM -> LM` / `LM -> SM -> GM` 改写。
- `fold=False` 且不配置 `apply_op` 时保留 legacy hierarchy 兼容路径，用于历史基础合同：global `kernel.*` operand/out 经 `dma.slice / dma.deslice` 搬运到 local 计算。
- 配置 `apply_op="matmul{[...]}"` 时启用当前公开规则：列表按 `kernel.matmul` IR operand 下标对应 `out/lhs/rhs`，非空 target 表示分配目标 space buffer、执行 `dma.copy(target, source)` 并替换该 operand。
- `apply_op` 规则搬运只使用 `dma.alloc + dma.copy`，不得使用 legacy `dma.slice / dma.deslice` 表示规则搬运。

## API 列表

- `class LowerDmaMemoryHierarchyPass(fold: bool = True, apply_op: str | None = None)`
- `LowerDmaMemoryHierarchyPass.from_options(options: dict[str, str]) -> LowerDmaMemoryHierarchyPass`
- `LowerDmaMemoryHierarchyPass.apply(ctx: Context, module: ModuleOp) -> None`

## 文档信息

- `spec`：[`spec/pass/lowering/dma_memory_hierarchy/spec.md`](../../../../spec/pass/lowering/dma_memory_hierarchy/spec.md)
- `功能实现`：[`kernel_gen/passes/dma_memory_hierarchy.py`](../../../../kernel_gen/passes/dma_memory_hierarchy.py)
- `test`：[`test/passes/test_dma_memory_hierarchy.py`](../../../../test/passes/test_dma_memory_hierarchy.py)

## 依赖

- Pass 管理器：[`spec/pass/pass_manager.md`](../../../../spec/pass/pass_manager.md)
- pass registry：[`spec/pass/registry.md`](../../../../spec/pass/registry.md)
- DMA dialect：[`spec/dialect/dma.md`](../../../../spec/dialect/dma.md)
- Kernel dialect：[`spec/dialect/kernel.md`](../../../../spec/dialect/kernel.md)
- NN dialect：[`spec/dialect/nn.md`](../../../../spec/dialect/nn.md)

## 目标

- 为 `lower-dma-memory-hierarchy` 提供稳定公开构造入口：
  - 直接构造：`LowerDmaMemoryHierarchyPass(fold=True, apply_op=None)`
  - options 构造：`LowerDmaMemoryHierarchyPass.from_options({"apply_op": "matmul{[\\"\\", \\"tlm1\\", \\"tlm2\\"]}"})`
  - registry 构造：`build_registered_pass("lower-dma-memory-hierarchy", {"apply_op": "matmul{[\\"\\", \\"tlm1\\", \\"tlm2\\"]}"})`
- 固定当前规则语法为单条 `matmul{[...]}`，本轮不支持多规则、不支持非 `matmul` op。
- 固定目标 space 集合为 `shared/local/tsm/tlm1/tlm2/tlm3`；空字符串 `""` 表示对应 operand 不变。
- 允许 `kernel.matmul(out@A, lhs@B, rhs@C)` 的 mixed-space 结果通过 verifier；`kernel.matmul.space` attribute 只保留为已有 op 空间属性，不重新定义为 out 或执行主导 space。

## 额外补充

### 模块级补充

- 本 pass 只定义 `dma memory hierarchy` 相关搬运规则，不负责 tile 搜索、并行化、double buffer、barrier、async 或 codegen 策略。
- `apply_op` 规则命中后，只处理 `kernel.matmul`；其他 op 保持不变。
- `apply_op` 规则中非空 target operand 必须是 `!nn.memory<...>`；若命中非 memory operand，必须显式失败。
- 被搬运 operand 的 target type 必须复用 source 的 `shape/stride/element_type`，仅替换 `space`。
- `dma.alloc` 的 `dynamic_shape`：
  - 静态 shape 使用空 `dynamic_shape`。
  - 显式符号维度通过 `symbol.get_dim(source, axis)` 读取。
  - 匿名动态维度 `?` 必须通过 `symbol.get_dim(source, axis)` 作为运行时 shape 继续流转，不得伪造稳定符号名。
- `fold=False` legacy 路径是历史基础合同兼容入口；新 `apply_op` 规则不依赖 target registry 的 `SM/LM` 硬件容量。
- 未配置 `apply_op` 且 `fold=True` 时 pass no-op，不要求 target 已选择，也不检查 `SM/LM`。

## API详细说明

### `class LowerDmaMemoryHierarchyPass(fold: bool = True, apply_op: str | None = None)`

- api：`class LowerDmaMemoryHierarchyPass(fold: bool = True, apply_op: str | None = None)`
- 参数：
  - `fold`：兼容开关；类型 `bool`；默认 `True`。`True` 且无 `apply_op` 时 no-op；`False` 且无 `apply_op` 时启用 legacy hierarchy 兼容路径。
  - `apply_op`：规则文本；类型 `str | None`；默认 `None`。`None` 表示不启用规则；当前唯一合法非空形式为 `matmul{["", "tlm1", "tlm2"]}` 这类单条 `matmul{[...]}`。
- 返回值：`LowerDmaMemoryHierarchyPass` 实例。
- 使用示例：

  ```python
  from kernel_gen.passes.dma_memory_hierarchy import LowerDmaMemoryHierarchyPass

  pass_obj = LowerDmaMemoryHierarchyPass(apply_op='matmul{["", "tlm1", "tlm2"]}')
  ```
- 功能说明：构造 `lower-dma-memory-hierarchy` pass，并在构造阶段校验 `apply_op` 规则文本。
- 注意事项：
  - `apply_op` 只支持 `matmul{[...]}`，`matmul` 映射到 `kernel.matmul`；非 `matmul` 规则必须报告 `unsupported apply_op`。
  - 规则列表长度必须正好为 `3`，按 `out/lhs/rhs` 对应 IR operand 下标 `0/1/2`。
  - 规则元素必须是 `""` 或 `shared/local/tsm/tlm1/tlm2/tlm3`。
  - `global` 不是合法 target space；source operand 可以来自任意合法 `nn.memory` space。
  - 非法 op 名、非法 JSON、非列表、列表长度错误、非字符串元素、非法 target space 都必须以公开错误失败。

### `LowerDmaMemoryHierarchyPass.from_options(options: dict[str, str]) -> LowerDmaMemoryHierarchyPass`

- api：`LowerDmaMemoryHierarchyPass.from_options(options: dict[str, str]) -> LowerDmaMemoryHierarchyPass`
- 参数：
  - `options`：pass 专属 options；类型 `dict[str, str]`；当前仅接受 `{"apply_op": "<rule>"}` 或空字典。registry 通用 `fold` option 由 registry 层剥离，不属于本方法专属 options。
- 返回值：`LowerDmaMemoryHierarchyPass` 实例。
- 使用示例：

  ```python
  pass_obj = LowerDmaMemoryHierarchyPass.from_options(
      {"apply_op": 'matmul{["", "tlm1", "tlm2"]}'}
  )
  ```
- 功能说明：为 pass registry 提供公开 options 构造入口。
- 注意事项：
  - 未知 option 必须失败，不能被静默忽略。
  - `apply_op` 的语法与 `LowerDmaMemoryHierarchyPass(...)` 构造参数完全一致。

### `LowerDmaMemoryHierarchyPass.apply(ctx: Context, module: ModuleOp) -> None`

- api：`LowerDmaMemoryHierarchyPass.apply(ctx: Context, module: ModuleOp) -> None`
- 参数：
  - `ctx`：xDSL pass 执行上下文；类型 `Context`；调用方必须提供。
  - `module`：待改写 IR；类型 `ModuleOp`；必须是 `builtin.module`。
- 返回值：无返回值；原地改写 `module`。
- 使用示例：

  ```python
  from xdsl.context import Context
  from kernel_gen.passes.dma_memory_hierarchy import LowerDmaMemoryHierarchyPass

  pass_obj = LowerDmaMemoryHierarchyPass(apply_op='matmul{["", "tlm1", "tlm2"]}')
  pass_obj.apply(Context(), module)
  ```
- 功能说明：
  - 有 `apply_op` 时，对每个 `kernel.matmul` 执行 copy-based operand rewrite。
  - 无 `apply_op` 且 `fold=True` 时，不改写 `module`。
  - 无 `apply_op` 且 `fold=False` 时，执行 legacy `GM -> SM -> LM` / `LM -> SM -> GM` 兼容路径。
- 注意事项：
  - `apply_op='matmul{["", "tlm1", "tlm2"]}'` 输入 `kernel.matmul(out@tsm, lhs@tsm, rhs@tsm)` 后，必须生成：

    ```text
    %lhs_buf = "dma.alloc"() : () -> !nn.memory<..., #nn.space<tlm1>>
    "dma.copy"(%lhs_buf, %lhs) : (...) -> ()
    %rhs_buf = "dma.alloc"() : () -> !nn.memory<..., #nn.space<tlm2>>
    "dma.copy"(%rhs_buf, %rhs) : (...) -> ()
    "kernel.matmul"(%out, %lhs_buf, %rhs_buf) ...
    ```
  - 规则中空字符串 operand 不得插入 `dma.alloc`、`dma.copy` 或替换 operand。
  - 规则命中 out operand 时，out 与 input 使用同一 copy 替换规则；本轮不追加 out writeback。
  - `apply_op` 模式不得生成 legacy `dma.slice / dma.deslice`。
  - legacy `fold=False` 模式若 target 缺失 `SM/LM` 必须失败，错误信息必须包含 `SM/LM` 与 `lower-dma-memory-hierarchy`。

## 测试

- 测试文件：
  - `test/passes/test_dma_memory_hierarchy.py`
  - `test/passes/test_registry.py`
  - `test/dialect/test_kernel.py`
- 执行命令：

  ```bash
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_dma_memory_hierarchy.py
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_registry.py test/passes/test_pass_manager.py test/passes/pipeline/test_default_lowering.py
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dialect/test_kernel.py test/dialect/test_dma.py test/dialect/test_nn.py
  ```

### 测试目标

- 验证默认无 `apply_op` 为 no-op。
- 验证 `fold=False` legacy hierarchy 兼容路径不回退。
- 验证 `apply_op` 合法规则、非法规则、空 target、out target、显式符号 shape 与匿名动态 shape 流转。
- 验证 registry options 能构造并执行 `apply_op` pass。
- 验证 `kernel.matmul` mixed-space verifier 允许规则输出 IR。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-DMH-001 | pass 默认行为 | 默认无 `apply_op` no-op | 构造 `kernel.matmul` module。 | 运行 `LowerDmaMemoryHierarchyPass().apply(...)`。 | 不插入 `dma.alloc/copy/slice/deslice`，operand 保持不变。 | `test_dma_memory_hierarchy_default_no_apply_op_is_noop` |
| TC-DMH-002 | legacy 兼容 | `fold=False` hierarchy | 构造 global `kernel.binary_elewise`，提供 SM/LM target。 | 运行 `LowerDmaMemoryHierarchyPass(fold=False)`。 | 生成 legacy `dma.slice/deslice`，kernel operand 转 local，不生成 `dma.copy`。 | `test_dma_memory_hierarchy_fold_false_legacy_hierarchy` |
| TC-DMH-003 | apply_op rewrite | matmul lhs/rhs copy | 构造 `kernel.matmul`。 | 运行 `apply_op='matmul{["", "tlm1", "tlm2"]}'`。 | lhs/rhs 被 `dma.alloc + dma.copy` 替换到 `tlm1/tlm2`。 | `test_dma_memory_hierarchy_apply_op_matmul_copies_lhs_rhs` |
| TC-DMH-004 | apply_op rewrite | matmul out copy | 构造 `kernel.matmul`。 | 运行 `apply_op='matmul{["tlm1", "", ""]}'`。 | out 也按同一 copy 规则替换到 `tlm1`，不追加写回。 | `test_dma_memory_hierarchy_apply_op_can_copy_out` |
| TC-DMH-005 | apply_op no-op | 空 target rule | 构造 `kernel.matmul`。 | 运行 `apply_op='matmul{["", "", ""]}'`。 | 不插入搬运，operand 保持不变。 | `test_dma_memory_hierarchy_apply_op_empty_rule_noop` |
| TC-DMH-006 | registry | options 构造 | 调用 `load_builtin_passes()`。 | `build_registered_pass("lower-dma-memory-hierarchy", {"fold": "false", "apply_op": ...})`。 | 返回 pass 并执行 copy rewrite。 | `test_dma_memory_hierarchy_registry_apply_op` |
| TC-DMH-007 | dynamic shape | 显式 symbol 维度 | 构造含 `M` 维度的 `kernel.matmul`。 | 运行 `apply_op` 改写 lhs。 | `dma.alloc.dynamic_shape` 使用 `symbol.get_dim` 结果。 | `test_dma_memory_hierarchy_apply_op_symbol_shape` |
| TC-DMH-008 | dynamic shape | 匿名 `?` 维度 | 构造含 `?` 维度的 `kernel.matmul`。 | 运行 `apply_op` 改写该 operand。 | `dma.alloc.dynamic_shape` 使用 `symbol.get_dim` 结果，result shape 保持 `?`。 | `test_dma_memory_hierarchy_apply_op_accepts_anonymous_dynamic_shape` |
| TC-DMH-009 | 错误语义 | 非法 apply_op | 使用非法 op、非法 arity、非法 space、非字符串元素。 | 构造 `LowerDmaMemoryHierarchyPass(apply_op=...)`。 | 稳定抛出 `KernelCodeError`。 | `test_dma_memory_hierarchy_rejects_invalid_apply_op_rules` |
