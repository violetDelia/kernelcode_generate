# tile.md

## 功能简介

- 本页是 tile family 的总览/索引页，不再承载旧 `TilePass` 的完整公开合同。
- 当前已经完成并对外收口的子合同是 `tile-analysis`。
- 后续 `tile-elewise`、`tile-reduce` 将在后续阶段补齐并各自落到独立子 spec。
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

### 规划中

- `tile-elewise`
  - `spec`：待 S2 新增
  - `功能实现`：待 S2 新增
  - `test`：待 S2 新增
  - `expectation`：待 S2 新增
- `tile-reduce`
  - `spec`：待 S3 新增
  - `功能实现`：待 S3 新增
  - `test`：待 S3 新增
  - `expectation`：待 S3 新增

## 迁移说明

- 旧 `TilePass` / `KernelSplitPass` 的完整公开合同不在本页展开。
- 旧 `tile.step_value`、`kernel_split.tile_value`、`tile.symbol_literal`、`kernel_split.symbol_literal` 等桥接名属于后续迁移/退场范围。
- 当前 tile family 的黑盒验证以子目录 expectation 为准；S1 阶段的目录级入口是 `python -m expectation.pass.tile.analysis`。

## 验收口径

- 以对应 worktree 的任务记录、pytest 和 expectation 结果作为当前阶段证据。
- 若需要确认流程、权限或日志落点，询问管理员。
- 若需要确认行为、接口或验收边界，询问架构师。

## 相关文件

- `tile-analysis` 说明：[`spec/pass/lowering/tile_analysis.md`](../../../spec/pass/lowering/tile_analysis.md)
- `tile-analysis` 实现：[`kernel_gen/passes/lowering/tile_analysis.py`](../../../kernel_gen/passes/lowering/tile_analysis.py)
- `tile-analysis` 测试：[`test/pass/test_lowering_tile_analysis.py`](../../../test/pass/test_lowering_tile_analysis.py)
- `tile-analysis` expectation：[`expectation/pass/tile/analysis`](../../../expectation/pass/tile/analysis)
