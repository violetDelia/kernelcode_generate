# kernel_pattern_attach.md

## 功能简介

- 定义 `kernel-pattern-attach` pass 的公开合同。
- 该 pass 在唯一 `entry_point` host 中识别一个或多个 out / lhs / rhs 均为 TSM 的 `kernel.matmul`，生成 host dispatcher 与两个 pattern 函数。
- dispatcher 固定使用 `tuner.select args(...) + symbol.const 0 + symbol.eq + scf.if + tuner.launch`；`tuner.select` 与每个 `tuner.launch` 都透传 entry runtime operands，默认 `tuner_args=()` 且不打印空 `tuner_args()`；pattern 函数携带 `kernel.pattern_id` 与 `kernel.transform_pipeline`。
- pattern 引用只允许写在 `tuner.select` 的 `patterns` attr 中；不得生成 `tuner.pattern_ref` IR op。
- 没有合格 TSM matmul 时保持 no-op；entry 调 helper、pattern 名称冲突等边界必须 fail-fast。

## API 列表

- `class KernelPatternAttachPass(fold: bool = True)`
- `KernelPatternAttachPass.from_options(options: dict[str, str]) -> KernelPatternAttachPass`
- `KernelPatternAttachPass.apply(ctx: Context, module: ModuleOp) -> None`

## 文档信息

- `spec`：[`spec/pass/tuning/kernel_pattern_attach.md`](kernel_pattern_attach.md)
- `功能实现`：[`kernel_gen/passes/tuning/kernel_pattern_attach.py`](../../../kernel_gen/passes/tuning/kernel_pattern_attach.py)
- `test`：[`test/passes/tuning/test_kernel_pattern_attach.py`](../../../test/passes/tuning/test_kernel_pattern_attach.py)

## 依赖

- [`spec/dialect/kernel.md`](../../dialect/kernel.md)
- [`spec/dialect/tuner.md`](../../dialect/tuner.md)
- [`spec/dialect/symbol.md`](../../dialect/symbol.md)
- [`spec/pass/tuning/transform_apply.md`](transform_apply.md)

## 目标

- registry name 固定为 `kernel-pattern-attach`。
- `from_options({})` 成功；任何未知 option 必须失败，错误文本包含 `kernel-pattern-attach options`。
- module 必须恰好包含一个 `entry_point` 函数；没有或多个必须失败。
- entry 中没有合格 TSM `kernel.matmul` 时 no-op。
- entry 中有一个或多个合格 TSM `kernel.matmul` 时生成两个 pattern 函数：`<entry>_pattern0` 与 `<entry>_pattern1`。
- pattern0 / pattern1 都复制完整 entry body；所有合格 `kernel.matmul` 与其它 kernel op 都必须分别出现在两个 pattern body 中。
- pattern0 的 `kernel.transform_pipeline` 固定为 `--pass "lower-dma-memory-hierarchy={fold=true,apply_op=matmul{[\"\", \"tlm1\", \"tlm2\"]}}" --pass canonicalize`。
- pattern1 的 `kernel.transform_pipeline` 固定为 `--pass "lower-dma-memory-hierarchy={fold=true,apply_op=matmul{[\"\", \"tlm2\", \"tlm1\"]}}" --pass canonicalize`。
- dispatcher 必须保留原 entry 函数名、签名与 `entry_point` 属性，并透传原 block arguments 到 `tuner.select.args` 和两个 `tuner.launch`。
- pattern 函数不得保留 `entry_point`；必须分别写入 `kernel.pattern_id = 0/1`。
- entry 中出现 `func.call`、待生成 pattern 名称已存在或 entry 有非空 result 时必须稳定失败。

## API 详细说明

### `class KernelPatternAttachPass(fold: bool = True)`

- api：`class KernelPatternAttachPass(fold: bool = True)`
- 参数：
  - `fold`：通用 fold 开关；类型 `bool`；默认值 `True`；不允许 `None`；调用方直接构造时可显式传入 `True` 或 `False`，非法类型不属于本 pass 的稳定合同；registry 通用 `fold` option 由 registry 解析后写回实例。
- 返回值：`KernelPatternAttachPass` 实例；实例公开 `name` 固定为 `kernel-pattern-attach`，可通过 `apply(ctx, module)` 原地改写 `ModuleOp`。
- 使用示例：

  ```python
  from kernel_gen.passes.tuning.kernel_pattern_attach import KernelPatternAttachPass

  pass_obj = KernelPatternAttachPass(fold=True)
  ```

- 功能说明：构造 `kernel-pattern-attach` pass，供调用方直接运行或交给 `PassManager` / registry 执行。
- 注意事项：
  - `fold` 是 pass manager 通用选项；本 pass 不定义专属 option。
  - 本 pass 的 canonical public import path 固定为 `kernel_gen.passes.tuning.kernel_pattern_attach`。
  - 旧路径 `kernel_gen.passes.kernel_pattern_attach` 不兼容保留，调用方必须迁移到 tuning path。

### `KernelPatternAttachPass.from_options(options: dict[str, str]) -> KernelPatternAttachPass`

- api：`KernelPatternAttachPass.from_options(options: dict[str, str]) -> KernelPatternAttachPass`
- 参数：
  - `options`：pass 专属 options；类型 `dict[str, str]`；无默认值，不允许 `None`；当前唯一合法值为空字典 `{}`；非空字典中的任意 key 都必须失败，错误文本必须包含 `kernel-pattern-attach options` 与未知 key 名称。
- 返回值：`KernelPatternAttachPass` 实例；返回实例的 `name` 固定为 `kernel-pattern-attach`。
- 使用示例：

  ```python
  from kernel_gen.passes.tuning.kernel_pattern_attach import KernelPatternAttachPass

  pass_obj = KernelPatternAttachPass.from_options({})
  ```

- 功能说明：为 pass registry 提供公开 options 构造入口，保持 `kernel-pattern-attach` 第一阶段无专属 option。
- 注意事项：
  - registry 通用 `fold` option 不属于本方法的专属 `options`，由 registry 在调用本方法前剥离并写回实例。
  - 本方法不得静默忽略未知 option，不得接受 `hoist`、`pattern`、`pipeline` 或其它临时扩展 option。

### `KernelPatternAttachPass.apply(ctx: Context, module: ModuleOp) -> None`

- api：`KernelPatternAttachPass.apply(ctx: Context, module: ModuleOp) -> None`
- 参数：
  - `ctx`：xDSL pass 执行上下文；类型 `Context`；无默认值，不允许 `None`；本 pass 不通过 `ctx` 做运行时能力探测，调用方必须提供正常 pass 上下文。
  - `module`：待改写 IR；类型 `ModuleOp`；无默认值，不允许 `None`；必须是 `builtin.module`，且 module 顶层必须满足本文目标章节定义的 entry / pattern 约束。
- 返回值：`None`；方法原地改写 `module`，不会返回新 module；失败时抛出 `KernelCodeError` 且不得留下部分 dispatcher / pattern 改写。
- 使用示例：

  ```python
  from xdsl.context import Context
  from kernel_gen.passes.tuning.kernel_pattern_attach import KernelPatternAttachPass

  pass_obj = KernelPatternAttachPass()
  pass_obj.apply(Context(), module)
  ```

- 功能说明：在唯一 `entry_point` host 中识别合格 TSM `kernel.matmul`，生成保留原 entry 名称和签名的 host dispatcher，并生成 `<entry>_pattern0` / `<entry>_pattern1` 两个 pattern 函数。
- 注意事项：
  - 没有合格 TSM `kernel.matmul` 时必须 no-op，不得生成空 dispatcher 或空 pattern。
  - 合格 `kernel.matmul` 的 out / lhs / rhs operand type 均必须是 `#nn.space<tsm>`；其它 space 不触发 pattern 生成。
  - module 必须恰好包含一个 `entry_point` 函数；没有或多个必须抛出 `KernelCodeError`，错误文本以前缀 `kernel-pattern-attach` 开头。
  - entry 中出现 `func.call`、待生成 pattern 名称已存在或 entry 有非空 result 时必须稳定失败。
  - pattern 函数不得保留 `entry_point`；必须写入 `kernel.pattern_id` 和固定 `kernel.transform_pipeline` 字符串。
  - dispatcher 只通过 `tuner.select` 的 `patterns` attr 引用 pattern；不得生成 `tuner.pattern_ref` IR op。
  - dispatcher 必须把原 entry block arguments 写入 `tuner.select args(...)` 和每个 `tuner.launch`；默认不提供 selector state，因此不得打印空 `tuner_args()` 组。

## 测试

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/tuning/test_kernel_pattern_attach.py`
- 历史 / 本地只读合同来源：`expectation/pass/kernel_pattern_attach/`；本 spec 当前不把该入口列为必过验收。
