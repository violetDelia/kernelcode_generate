# dma_alias_to_reinterpret

## 功能简介

- `DmaAliasToReinterpretPass` 是公开 `ModulePass`，registry 名称固定为 `dma-alias-to-reinterpret`。
- pass 将 `dma.view`、`dma.reshape` 与 `dma.subview` 归一为 root source 上的单个 `dma.reinterpret`，并组合 alias 链上的线性 offset。
- pass 不删除 `dma.view` / `dma.reshape` / `dma.subview` 方言定义；不能 exact 物化 offset、shape、stride 或 verifier 失败时保持 no-op。

## API 列表

- `class DmaAliasToReinterpretPass(fold: bool = True)`
- `DmaAliasToReinterpretPass.name: str`
- `DmaAliasToReinterpretPass.apply(ctx: Context, module: ModuleOp) -> None`
- registry pass name：`dma-alias-to-reinterpret`

## 文档信息

- `spec`：[`spec/pass/dma_alias_to_reinterpret.md`](../../spec/pass/dma_alias_to_reinterpret.md)
- `功能实现`：[`kernel_gen/passes/dma_alias_to_reinterpret.py`](../../kernel_gen/passes/dma_alias_to_reinterpret.py)
- `test`：[`test/passes/test_dma_alias_to_reinterpret.py`](../../test/passes/test_dma_alias_to_reinterpret.py)
- `expectation`：主仓只读合同资产 `expectation/pass/dma_alias_to_reinterpret/**`

## 依赖

- `spec/dialect/dma.md`：定义 `dma.view`、`dma.reshape`、`dma.subview` 与 `dma.reinterpret`。
- `spec/pass/registry.md`：承载 registry 名称与通用 `fold` option。
- `spec/pass/pipeline/npu_demo_lowering.md`：固定 pass 插入到 `NnLoweringPass` 后。

## 目标

- `dma.reshape(source, shape)` 改写为 `dma.reinterpret(source, offset=0, shape=result.shape, stride=result.stride)`。
- `dma.view(source, offsets, shape, stride)` 改写为 `dma.reinterpret(root, linear_offset, result.shape, result.stride)`，其中 linear offset 按逐层 source physical stride 计算。
- `dma.subview(byte_pool, offset, size, stride)` 改写为 `dma.reinterpret(byte_pool, offset, [size], [stride])`，byte-pool offset 单位固定为 byte。
- source 已经是 `dma.view` / `dma.reshape` / `dma.subview` / `dma.reinterpret` 的 alias result 时，必须追到最早 non-alias root source 并组合 offset；不得生成 `dma.reinterpret(dma.reinterpret(...))` 或 `dma.reinterpret(dma.view(...))` 这类半归一形态。

## 非目标

- 不做复杂代数化简、`mod/div/floordiv/sub` 线性化或跨 region 移动。
- 不迁移高层 DSL API；高层仍可生成旧 alias op。
- 不删除 `hoist-dma-alias-ops` 中服务手动调用或未归一化 IR 的旧 op 专项逻辑。
- 不修改 expectation 合同资产；execute / review / merge 只能只读运行并记录。

## 行为

### rewrite 合同

- 新建 symbol op 必须插入在候选 alias op 前，并支配新 `dma.reinterpret`。
- shape operand 使用原 alias op 的公开 shape operand；stride operand 使用 result type 对应的公开 stride value，缺失静态 SSA 时可在当前 block 物化 `symbol.const` / `symbol.mul`。
- 改写后必须运行 verifier。若新 op 或 clone module verifier 失败，必须回滚为原 IR 并保持 no-op；不得留下部分替换。
- pass `apply(...)` 只负责 alias 到 `dma.reinterpret` 的归一化，不在 pass 内删除未使用的 alias/reinterpret 结果；pipeline 级死代码清理由 `PassManager` 通用 `fold` 开关控制。
- pass apply 后若最终 module verifier 失败，公开错误前缀为 `DmaAliasToReinterpretVerifierError:`。

### no-op 边界

- 候选 op 或其 alias root 位于当前第一版无法安全处理的 region 结构时保持 no-op。
- 任一 offset / shape / stride operand 不是公开 symbol index/int operand，或无法提取稳定表达时保持 no-op。
- `dma.view` 的 source stride 中包含无法物化的 unknown 表达时保持 no-op。
- `dma.subview` source 不是一维 `i8` byte pool 时保持 no-op。
- 改写后 `DmaReinterpretOp.verify()` 失败时保持 no-op。

## API详细说明

### `class DmaAliasToReinterpretPass(fold: bool = True)`

- api：`class DmaAliasToReinterpretPass(fold: bool = True)`
- 参数：
  - `fold`：通用 pass 后 folding 开关；类型 `bool`；默认值 `True`。
- 返回值：`DmaAliasToReinterpretPass` 实例。
- 功能说明：构造 alias 归一化 pass。
- 使用示例：

```python
from kernel_gen.passes.dma_alias_to_reinterpret import DmaAliasToReinterpretPass

pass_obj = DmaAliasToReinterpretPass(fold=False)
```

- 注意事项：不接受 pass 专属 option；新增 option、默认值或公开错误文本变更必须先取得用户确认。

### `DmaAliasToReinterpretPass.name: str`

- api：`DmaAliasToReinterpretPass.name: str`
- 返回值：固定字符串 `"dma-alias-to-reinterpret"`。
- 功能说明：公开 registry pass name。
- 使用示例：

```python
assert DmaAliasToReinterpretPass.name == "dma-alias-to-reinterpret"
```

### `DmaAliasToReinterpretPass.apply(ctx: Context, module: ModuleOp) -> None`

- api：`DmaAliasToReinterpretPass.apply(ctx: Context, module: ModuleOp) -> None`
- 参数：
  - `ctx`：xDSL context；类型 `Context`。
  - `module`：待改写 module；类型 `ModuleOp`，必须是 `builtin.module`。
- 返回值：`None`；原地改写 IR。
- 功能说明：遍历 module 内 alias op，把可证明的旧 alias op 归一为 `dma.reinterpret`。
- 使用示例：

```python
from xdsl.context import Context

DmaAliasToReinterpretPass().apply(Context(), module)
```

- 注意事项：当前文件之外不得调用本 pass 内部 symbol material、alias 链分析或 rewrite helper。

## Pattern MLIR before / after 合同

### reshape

before:

```mlir
%tile = "dma.reshape"(%flat, %m, %n) : (...) -> !nn.memory<[#M, #N], [#N, #1], f32, #nn.space<tsm>>
```

after:

```mlir
%zero = symbol.const 0 : !symbol.int<#symbol.expr<0>>
%tile = "dma.reinterpret"(%flat, %zero, %m, %n, %n, %one)
  <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (...) -> !nn.memory<[#M, #N], [#N, #1], f32, #nn.space<tsm>>
```

### view

before:

```mlir
%view = "dma.view"(%src, %i, %j, %tm, %tn, %one, %one) : (...) -> !nn.memory<[#TM, #TN], [#N, #1], f32, #nn.space<global>>
```

after:

```mlir
%iN = symbol.mul %i, %n : !symbol.iter<...>, !symbol.int<#symbol.expr<N>> -> !symbol.int<#symbol.expr<iter<...>*N>>
%off = symbol.add %iN, %j : !symbol.int<...>, !symbol.iter<...> -> !symbol.int<#symbol.expr<iter<...>*N + iter<...>>>
%view = "dma.reinterpret"(%src, %off, %tm, %tn, %n, %one)
  <{operandSegmentSizes = array<i32: 1, 1, 2, 2>}> : (...) -> !nn.memory<[#TM, #TN], [#N, #1], f32, #nn.space<global>>
```

### subview

before:

```mlir
%tile = "dma.subview"(%pool, %byte_off, %size, %one) : (...) -> !nn.memory<[#SIZE], [#1], f32, #nn.space<tsm>>
```

after:

```mlir
%tile = "dma.reinterpret"(%pool, %byte_off, %size, %one)
  <{operandSegmentSizes = array<i32: 1, 1, 1, 1>}> : (...) -> !nn.memory<[#SIZE], [#1], f32, #nn.space<tsm>>
```

### alias chain

before:

```mlir
%base = "dma.view"(%src, %i, %zero, %tm, %n, %one, %one) : (...) -> !nn.memory<...>
%tile = "dma.view"(%base, %zero, %j, %tm, %tn, %one, %one) : (...) -> !nn.memory<...>
```

after:

```mlir
%off = ... : !symbol.int<#symbol.expr<I*N + J>>
%tile = "dma.reinterpret"(%src, %off, %tm, %tn, %n, %one) : (...) -> !nn.memory<...>
```

## 测试

- 测试文件：`test/passes/test_dma_alias_to_reinterpret.py`
- 执行命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/test_dma_alias_to_reinterpret.py`

### 功能与用例清单

| 用例 | 场景 | 断言 |
| --- | --- | --- |
| TC-DMA-ALIAS-TO-REINTERPRET-001 | registry | `build_registered_pass("dma-alias-to-reinterpret", {"fold": "false"})` 返回 pass 且 fold 关闭 |
| TC-DMA-ALIAS-TO-REINTERPRET-002 | view | `dma.view` 改写为 root source 上 `dma.reinterpret`，offset 为 source stride 点积 |
| TC-DMA-ALIAS-TO-REINTERPRET-003 | reshape | `dma.reshape` 改写为 zero-offset `dma.reinterpret` |
| TC-DMA-ALIAS-TO-REINTERPRET-004 | subview | byte-pool `dma.subview` 改写为 byte-offset `dma.reinterpret` |
| TC-DMA-ALIAS-TO-REINTERPRET-005 | alias chain | `view(reshape(root))` / `reshape(view(root))` / `subview(view(byte_pool))` 追到 root source，不生成嵌套 reinterpret |
| TC-DMA-ALIAS-TO-REINTERPRET-006 | unused alias | 未使用 alias 结果仍在 pass apply 内归一为 `dma.reinterpret`，不被内部 DCE 删除 |
| TC-DMA-ALIAS-TO-REINTERPRET-007 | no-op | 不支持 source、无法 exact verifier 或不安全 region 保持原 alias op |

## 合同验收

- 主仓只读合同资产：`expectation/pass/dma_alias_to_reinterpret/**`。
- execute / review / merge 不得修改、复制、新建、删除或同步 expectation 文件。
- 验收命令：

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=<任务worktree>:/home/lfr/kernelcode_generate \
python3 -m expectation.pass.dma_alias_to_reinterpret
```

- 记录必须写清 `expectation.*` 来自主仓、`kernel_gen.*` 来自任务 worktree。
