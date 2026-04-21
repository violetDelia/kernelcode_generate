# tile.md

## 功能简介

- 本页是 tile family 的总览/索引页，不再承载旧 `TilePass` 的完整公开合同。
- 当前已经完成并对外收口的子合同是 `tile-analysis` 与 `tile-elewise`。
- 当前已经完成并对外收口的子合同是 `tile-analysis`、`tile-elewise` 与 `tile-reduce`。
- tile family 后续若再拆分新阶段，应继续新增独立子 spec，而不是回填本页旧合同。
- 需要具体行为定义时，优先进入子 spec；需要整体迁移背景时，参考计划书。

## 文档信息

- 创建者：`小李飞刀`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/pass/lowering/tile.md`](../../../spec/pass/lowering/tile.md)
- `相关计划`：[`ARCHITECTURE/plan/tile_pass_split_green_plan.md`](../../../ARCHITECTURE/plan/tile_pass_split_green_plan.md)

## 索引

### 已发布

- `tile-analysis`
  - `spec`：[`spec/pass/lowering/tile_analysis.md`](../../../spec/pass/lowering/tile_analysis.md)
  - `功能实现`：[`kernel_gen/passes/lowering/tile_analysis.py`](../../../kernel_gen/passes/lowering/tile_analysis.py)
  - `test`：[`test/pass/test_lowering_tile_analysis.py`](../../../test/pass/test_lowering_tile_analysis.py)
  - `expectation`：[`expectation/pass/tile/analysis`](../../../expectation/pass/tile/analysis)
  - 当前状态：S1 已收口
- `tile-elewise`
  - `spec`：[`spec/pass/lowering/tile_elewise.md`](../../../spec/pass/lowering/tile_elewise.md)
  - `功能实现`：[`kernel_gen/passes/lowering/tile_elewise.py`](../../../kernel_gen/passes/lowering/tile_elewise.py)
  - `test`：[`test/pass/test_lowering_tile_elewise.py`](../../../test/pass/test_lowering_tile_elewise.py)
  - `expectation`：[`expectation/pass/tile/elewise`](../../../expectation/pass/tile/elewise)
  - 当前状态：S2 已收口
- `tile-reduce`
  - `spec`：[`spec/pass/lowering/tile_reduce.md`](../../../spec/pass/lowering/tile_reduce.md)
  - `功能实现`：[`kernel_gen/passes/lowering/tile_reduce.py`](../../../kernel_gen/passes/lowering/tile_reduce.py)
  - `test`：[`test/pass/test_lowering_tile_reduce.py`](../../../test/pass/test_lowering_tile_reduce.py)
  - `expectation`：[`expectation/pass/tile/reduce`](../../../expectation/pass/tile/reduce)
  - 当前状态：S3 已收口

## 迁移说明

- 旧 `TilePass` / `KernelSplitPass` 的完整公开合同不在本页展开。
- `tile-analysis` 与 `tile-elewise` 的公开输出都保持 `tile.analysis + tile.tile_exprs`。
- 旧 `tile.step_value`、`kernel_split.tile_value`、`tile.symbol_literal`、`kernel_split.symbol_literal` 等桥接名属于后续迁移/退场范围。
- 当前 tile family 的黑盒验证以子目录 expectation 为准；已发布目录级入口是 `python -m expectation.pass.tile.analysis`、`python -m expectation.pass.tile.elewise` 与 `python -m expectation.pass.tile.reduce`。

## 验收口径

- 以对应 worktree 的任务记录、pytest 和 expectation 结果作为当前阶段证据。
- 若需要确认流程、权限或日志落点，询问管理员。
- 若需要确认行为、接口或验收边界，询问架构师。

## 相关文件

- `tile-analysis` 说明：[`spec/pass/lowering/tile_analysis.md`](../../../spec/pass/lowering/tile_analysis.md)
- `tile-analysis` 实现：[`kernel_gen/passes/lowering/tile_analysis.py`](../../../kernel_gen/passes/lowering/tile_analysis.py)
- `tile-analysis` 测试：[`test/pass/test_lowering_tile_analysis.py`](../../../test/pass/test_lowering_tile_analysis.py)
- `tile-analysis` expectation：[`expectation/pass/tile/analysis`](../../../expectation/pass/tile/analysis)
- `tile-elewise` 说明：[`spec/pass/lowering/tile_elewise.md`](../../../spec/pass/lowering/tile_elewise.md)
- `tile-elewise` 实现：[`kernel_gen/passes/lowering/tile_elewise.py`](../../../kernel_gen/passes/lowering/tile_elewise.py)
- `tile-elewise` 测试：[`test/pass/test_lowering_tile_elewise.py`](../../../test/pass/test_lowering_tile_elewise.py)
- `tile-elewise` expectation：[`expectation/pass/tile/elewise`](../../../expectation/pass/tile/elewise)
- `tile-reduce` 说明：[`spec/pass/lowering/tile_reduce.md`](../../../spec/pass/lowering/tile_reduce.md)
- `tile-reduce` 实现：[`kernel_gen/passes/lowering/tile_reduce.py`](../../../kernel_gen/passes/lowering/tile_reduce.py)
- `tile-reduce` 测试：[`test/pass/test_lowering_tile_reduce.py`](../../../test/pass/test_lowering_tile_reduce.py)
- `tile-reduce` expectation：[`expectation/pass/tile/reduce`](../../../expectation/pass/tile/reduce)
