# arch_parallelize pass

## 功能简介

- `ArchParallelizePass` 提供 standalone IR-level module pass，遍历 `builtin.module` 中所有非声明 `func.func`，为未带 block 并行语义的函数生成 block 级分发 IR。
- 当前只支持 `parallel_level="block"`；可分发的唯一顶层 `symbol.for` 被改写为 block-strided loop；无顶层 loop 的函数用 block0 guard 包裹原 body。
- 本 pass 不接入默认 `npu-demo-lowering`，不承诺 emit/run，不修改 include/runtime。

## API 列表

- `class ArchParallelizePass(target: str = "npu_demo", parallel_level: str = "block")`
- `ArchParallelizePass.from_options(options: dict[str, str]) -> ArchParallelizePass`
- `ArchParallelizePass.apply(ctx: Context, module: ModuleOp) -> None`
- `kernel_gen.passes.ArchParallelizePass`
- `kernel_gen.passes.arch_parallelize.ArchParallelizePass`
- `build_registered_pass("arch-parallelize", options: dict[str, str] | None = None) -> ModulePass`

## 文档信息

- `spec`：`spec/pass/arch_parallelize.md`
- `功能实现`：`kernel_gen/passes/arch_parallelize.py`
- `test`：`test/passes/test_arch_parallelize.py`、`test/passes/test_registry.py`
- `expectation`：主仓只读合同资产 `expectation/pass/arch_parallelize/**`

## 依赖

- `kernel_gen.dialect.arch`：公开 `ArchGetBlockIdOp` 与 `ArchGetBlockNumOp` 类型，用于检测和生成 block 相关 IR。
- `kernel_gen.dialect.symbol`：公开 `SymbolForOp`、`SymbolConstOp`、`SymbolAddOp`、`SymbolMulOp`、`SymbolNeOp` 与 `SymbolValueType`，用于 loop 边界和 block0 guard。
- `kernel_gen.target.registry`：公开 `is_arch_op_supported(target, op_name)` 与 `get_target_hardware(target, key)`，用于校验 target 与读取静态 `block_num`。
- `kernel_gen.passes.registry`：公开 pass registry 名称 `arch-parallelize`。

## 目标

- pass 必须遍历 module 中所有非声明 `func.func`，每个函数独立判断、独立改写或跳过。
- 已包含 `arch.get_block_id` 或 `arch.get_block_num` 的函数必须跳过，不重复插入 block 并行语义。
- `block_num` 必须来自 target registry 的静态硬件字段，并在 IR 中物化为 `symbol.const <target.block_num>`；不得生成 `arch.get_block_num`。
- 多个顶层 `symbol.for`、loop-carried `symbol.for`、非 void return、多 block 函数体和不可判 loop 同级结构必须显式失败。

## 额外补充

- 顶层 loop 指函数 entry block 的直接子 op；嵌套 region 内的 `symbol.for` 不参与顶层计数。
- 支持结构为 `func { symbol-setup*; symbol.for { body-op*; nested-symbol.for* }; func.return }`，其中同级 `symbol-setup` 只能位于唯一顶层 loop 之前，并且必须是公开 symbol dialect 的纯 setup op。
- 无顶层 loop 时，原 body 放入 `scf.if` 的 block0 分支；`func.return` 必须保持在 `scf.if` 外。
- 本 pass 的失败通过 `KernelCodeError` 暴露，稳定错误短语以 `ArchParallelizePassError:` 或 `ArchParallelizePassVerifierError:` 开头。
- `expectation/pass/arch_parallelize/**` 只作为主仓合同验收资产；任务 worktree 不得复制、修改、新建、移动、删除或同步该目录。

## API详细说明

### `class ArchParallelizePass(target: str = "npu_demo", parallel_level: str = "block")`

- api：`class ArchParallelizePass(target: str = "npu_demo", parallel_level: str = "block")`
- 参数：
  - `target`：目标后端名称；类型 `str`；默认 `"npu_demo"`；必须为非空字符串；必须已注册到 target registry；必须支持 `arch.get_block_id`；必须提供正整数硬件字段 `block_num`。
  - `parallel_level`：并行层级；类型 `str`；默认 `"block"`；当前只允许 `"block"`；`"block_thread"` 必须以稳定错误 `ArchParallelizePassError: parallel_level block_thread is not supported yet` 失败。
- 返回值：构造 `ArchParallelizePass` 实例；构造阶段只保存参数，参数有效性在 `apply(...)` 或 registry 构造后执行时校验。
- 使用示例：

  ```python
  from kernel_gen.passes.arch_parallelize import ArchParallelizePass

  pass_obj = ArchParallelizePass(target="npu_demo", parallel_level="block")
  ```

- 功能说明：创建 block 级并行 IR pass 实例。
- 注意事项：本接口不公开其它并行层级；新增层级、默认值或错误文本变更必须先取得用户确认。

### `ArchParallelizePass.from_options(options: dict[str, str]) -> ArchParallelizePass`

- api：`ArchParallelizePass.from_options(options: dict[str, str]) -> ArchParallelizePass`
- 参数：
  - `options`：pass 专属 registry options；类型 `dict[str, str]`；只允许键 `target` 与 `parallel_level`；缺省键使用构造默认值。
- 返回值：`ArchParallelizePass` 实例。
- 使用示例：

  ```python
  pass_obj = ArchParallelizePass.from_options({"target": "npu_demo", "parallel_level": "block"})
  ```

- 功能说明：承接 registry `build_registered_pass("arch-parallelize", options)` 的 pass 专属 option 解析。
- 注意事项：未知 option 必须以 `ArchParallelizePassError: unknown option(s)` 失败；registry 通用 `fold` option 由 `kernel_gen.passes.registry` 处理，不属于本接口专属 option。

### `ArchParallelizePass.apply(ctx: Context, module: ModuleOp) -> None`

- api：`ArchParallelizePass.apply(ctx: Context, module: ModuleOp) -> None`
- 参数：
  - `ctx`：xDSL `Context`；类型 `Context`；由 pass manager 或调用方提供。
  - `module`：待改写 IR；类型 `ModuleOp`；必须是 `builtin.module`。
- 返回值：`None`；直接原地改写 `module`。
- 使用示例：

  ```python
  from xdsl.context import Context
  from kernel_gen.passes.arch_parallelize import ArchParallelizePass

  ArchParallelizePass().apply(Context(), module)
  ```

- 功能说明：校验参数与 target，遍历每个非声明 `func.func`，对可分发 loop 改写 block-strided 边界，对无 loop 函数生成 block0 guard，对不支持结构给出稳定失败。
- 注意事项：
  - 已有 `arch.get_block_id` 或 `arch.get_block_num` 的函数必须跳过。
  - 函数有返回值必须失败为 `ArchParallelizePassError: function return values are not supported`。
  - 函数体为 multi-block 必须失败为 `ArchParallelizePassError: multi-block func body is not supported`。
  - 多个顶层 `symbol.for` 必须失败为 `ArchParallelizePassError: multiple top-level symbol.for loops are not supported`。
  - loop-carried `symbol.for` 必须失败为 `ArchParallelizePassError: loop-carried symbol.for is not supported`。
  - 顶层 loop 同级出现非纯 symbol setup op 时必须失败为 `ArchParallelizePassError: unsupported loop structure`。

### `build_registered_pass("arch-parallelize", options: dict[str, str] | None = None) -> ModulePass`

- api：`build_registered_pass("arch-parallelize", options: dict[str, str] | None = None) -> ModulePass`
- 参数：
  - `options`：registry options；类型 `dict[str, str] | None`；允许 `target`、`parallel_level` 与 registry 通用 `fold`。
- 返回值：`ArchParallelizePass` 的 `ModulePass` 实例。
- 使用示例：

  ```python
  from kernel_gen.passes.registry import build_registered_pass, load_builtin_passes

  load_builtin_passes()
  pass_obj = build_registered_pass("arch-parallelize", {"target": "npu_demo", "parallel_level": "block"})
  ```

- 功能说明：通过公开 registry 名称构造 `ArchParallelizePass`。
- 注意事项：调用方必须先执行 `load_builtin_passes()`；registry 不隐式加载内置 pass。

## 测试

- 测试文件：`test/passes/test_arch_parallelize.py`、`test/passes/test_registry.py`
- 执行命令：`pytest -q test/passes/test_arch_parallelize.py test/passes/test_registry.py`
- 合同验收：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260516-arch-parallelize-pass:/home/lfr/kernelcode_generate python3 -m expectation.pass.arch_parallelize`

### 测试目标

- 验证 `ArchParallelizePass` 的 Python API、registry API、target 校验、loop 改写、block0 guard、跳过和失败边界。
- 验证主仓 `expectation.pass.arch_parallelize` 只读合同在任务 worktree 代码优先生效的导入边界下通过。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-PASS-ARCH-PARALLELIZE-001 | pass 改写 | 单顶层 `symbol.for` | 函数中只有一个顶层 `symbol.for`，loop 前为纯 symbol setup。 | 运行 `ArchParallelizePass().apply(...)`。 | IR 含 `arch.get_block_id`、静态 `symbol.const block_num`、`symbol.mul`、`symbol.add` 和新 block-strided `symbol.for`。 | `test_arch_parallelize_rewrites_single_top_level_loop` |
| TC-PASS-ARCH-PARALLELIZE-002 | pass 改写 | 无顶层 loop | 函数体只有普通 op 和 `func.return`。 | 运行 `ArchParallelizePass().apply(...)`。 | 原 body 位于 `scf.if` 的 block0 分支，`func.return` 仍在 `scf.if` 外。 | `test_arch_parallelize_wraps_no_loop_body_in_block0_guard` |
| TC-PASS-ARCH-PARALLELIZE-003 | pass 改写 | 动态嵌套 loop | 外层顶层 loop 包含内层 loop。 | 运行 `ArchParallelizePass().apply(...)`。 | 只改写外层 loop，内层 loop 保持嵌套。 | `test_arch_parallelize_rewrites_only_outer_dynamic_loop` |
| TC-PASS-ARCH-PARALLELIZE-004 | pass 改写 | 多函数 module | module 含两个非声明函数。 | 运行 `ArchParallelizePass().apply(...)`。 | 两个函数独立处理。 | `test_arch_parallelize_processes_each_non_declaration_func` |
| TC-PASS-ARCH-PARALLELIZE-005 | 跳过边界 | 函数已有 block op | 函数体已有 `arch.get_block_id`。 | 运行 `ArchParallelizePass().apply(...)`。 | 函数保持不重复插入 block 相关 op。 | `test_arch_parallelize_skips_existing_block_parallel_func` |
| TC-PASS-ARCH-PARALLELIZE-006 | 失败边界 | 多顶层 loop | 函数 entry block 直接包含多个 `symbol.for`。 | 运行 `ArchParallelizePass().apply(...)`。 | 失败短语含 `multiple top-level symbol.for loops are not supported`。 | `test_arch_parallelize_rejects_multiple_top_level_loops` |
| TC-PASS-ARCH-PARALLELIZE-007 | 失败边界 | loop-carried | 顶层 `symbol.for` 带 carried value。 | 运行 `ArchParallelizePass().apply(...)`。 | 失败短语含 `loop-carried symbol.for is not supported`。 | `test_arch_parallelize_rejects_loop_carried_symbol_for` |
| TC-PASS-ARCH-PARALLELIZE-008 | 失败边界 | 参数非法 | `parallel_level="block_thread"`、空 target 或未注册 target。 | 运行 `ArchParallelizePass(...).apply(...)`。 | 返回稳定 `ArchParallelizePassError`。 | `test_arch_parallelize_rejects_invalid_options_and_targets` |
| TC-PASS-ARCH-PARALLELIZE-009 | 失败边界 | target 合同缺口 | target 缺 `block_num`、非法 `block_num` 或不支持 `arch.get_block_id`。 | 运行 `ArchParallelizePass(target=...).apply(...)`。 | 返回稳定 `ArchParallelizePassError`。 | `test_arch_parallelize_rejects_target_contract_gaps` |
| TC-PASS-ARCH-PARALLELIZE-010 | 失败边界 | 未知 option | `from_options(...)` 收到非 `target` / `parallel_level` 的专属 option。 | 运行 `ArchParallelizePass.from_options(...)`。 | 失败短语含 `unknown option(s)`。 | `test_arch_parallelize_from_options_rejects_unknown_option` |
| TC-PASS-ARCH-PARALLELIZE-011 | 失败边界 | 非 void return | 函数签名包含返回值。 | 运行 `ArchParallelizePass().apply(...)`。 | 失败短语含 `function return values are not supported`。 | `test_arch_parallelize_rejects_return_values` |
| TC-PASS-ARCH-PARALLELIZE-012 | 失败边界 | multi-block 函数体 | `func.func` body 含多个 block。 | 运行 `ArchParallelizePass().apply(...)`。 | 失败短语含 `multi-block func body is not supported`。 | `test_arch_parallelize_rejects_multi_block_func_body` |
| TC-PASS-ARCH-PARALLELIZE-013 | 失败边界 | unsupported loop structure | 唯一顶层 `symbol.for` 后仍有同级 op。 | 运行 `run_ircheck_text(...)` 触发公开 pass 入口。 | 失败短语含 `unsupported loop structure`。 | `test_arch_parallelize_rejects_unsupported_loop_structure` |
| TC-PASS-ARCH-PARALLELIZE-014 | registry | 内置 pass 注册 | 已调用 `load_builtin_passes()`。 | 运行 `build_registered_pass("arch-parallelize", options)`。 | 返回 `ArchParallelizePass` 实例。 | `test_build_registered_arch_parallelize_pass` |
