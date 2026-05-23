# kernel_pattern_attach.md

## 功能简介

- 定义 `kernel-pattern-attach` pass 的公开合同。
- 该 pass 在唯一 `entry_point` host 中识别一个或多个 out / lhs / rhs 均为 TSM 的 `kernel.matmul`，生成 host dispatcher 与两个 pattern 函数。
- dispatcher 固定使用 `tuner.select + symbol.const 0 + symbol.eq + scf.if + tuner.launch`；pattern 函数携带 `kernel.pattern_id` 与 `kernel.transform_pipeline`。
- pattern 引用只允许写在 `tuner.select` 的 `patterns` attr 中；不得生成 `tuner.pattern_ref` IR op。
- 没有合格 TSM matmul 时保持 no-op；entry 调 helper、pattern 名称冲突等边界必须 fail-fast。

## API 列表

- `class KernelPatternAttachPass(fold: bool = True)`
- `KernelPatternAttachPass.from_options(options: dict[str, str]) -> KernelPatternAttachPass`
- `KernelPatternAttachPass.apply(ctx: Context, module: ModuleOp) -> None`

## 文档信息

- `spec`：[`spec/pass/kernel_pattern_attach.md`](../../spec/pass/kernel_pattern_attach.md)
- `功能实现`：[`kernel_gen/passes/kernel_pattern_attach.py`](../../kernel_gen/passes/kernel_pattern_attach.py)
- `test`：[`test/passes/test_kernel_pattern_attach.py`](../../test/passes/test_kernel_pattern_attach.py)

## 依赖

- [`spec/dialect/kernel.md`](../dialect/kernel.md)
- [`spec/dialect/tuner.md`](../dialect/tuner.md)
- [`spec/dialect/symbol.md`](../dialect/symbol.md)
- [`spec/pass/transform_apply.md`](transform_apply.md)

## 目标

- registry name 固定为 `kernel-pattern-attach`。
- `from_options({})` 成功；任何未知 option 必须失败，错误文本包含 `kernel-pattern-attach options`。
- module 必须恰好包含一个 `entry_point` 函数；没有或多个必须失败。
- entry 中没有合格 TSM `kernel.matmul` 时 no-op。
- entry 中有一个或多个合格 TSM `kernel.matmul` 时生成两个 pattern 函数：`<entry>_pattern0` 与 `<entry>_pattern1`。
- pattern0 / pattern1 都复制完整 entry body；所有合格 `kernel.matmul` 与其它 kernel op 都必须分别出现在两个 pattern body 中。
- pattern0 的 `kernel.transform_pipeline` 固定为 `--pass "lower-dma-memory-hierarchy={fold=true,apply_op=matmul{[\"\", \"tlm1\", \"tlm2\"]}}" --pass canonicalize`。
- pattern1 的 `kernel.transform_pipeline` 固定为 `--pass "lower-dma-memory-hierarchy={fold=true,apply_op=matmul{[\"\", \"tlm2\", \"tlm1\"]}}" --pass canonicalize`。
- dispatcher 必须保留原 entry 函数名、签名与 `entry_point` 属性，并透传原 block arguments 到两个 `tuner.launch`。
- pattern 函数不得保留 `entry_point`；必须分别写入 `kernel.pattern_id = 0/1`。
- entry 中出现 `func.call`、待生成 pattern 名称已存在或 entry 有非空 result 时必须稳定失败。

## API 详细说明

### `class KernelPatternAttachPass(fold: bool = True)`

- 功能：构造 kernel pattern attach pass。
- 注意事项：`fold` 是 pass manager 通用选项；本 pass 不定义专属 option。

### `KernelPatternAttachPass.from_options(options: dict[str, str]) -> KernelPatternAttachPass`

- 功能：供 pass registry 根据 options 构造实例。
- 错误：非空 `options` 必须失败，错误文本包含 `kernel-pattern-attach options`。

### `KernelPatternAttachPass.apply(ctx: Context, module: ModuleOp) -> None`

- 功能：原地改写 `module`，在唯一 entry 内为合格 TSM matmul 生成 pattern dispatcher。
- 错误：所有失败边界必须抛出 `KernelCodeError(ErrorModule.PASS, ...)`，错误文本以前缀 `kernel-pattern-attach` 开头。

## 测试

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_kernel_pattern_attach.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<taskwt>:/home/lfr/kernelcode_generate python3 -m expectation.pass.kernel_pattern_attach`
