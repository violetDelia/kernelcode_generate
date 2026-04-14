# tile_pass_expectation_refactor_green_plan.md

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`大闸蟹`
- 目标 `spec`：
  - [`spec/pass/lowering/tile.md`](../../spec/pass/lowering/tile.md)
  - [`spec/tools/ircheck.md`](../../spec/tools/ircheck.md)
- 目标 `API`：
  - [`kernel_gen/passes/lowering/tile.py`](../../kernel_gen/passes/lowering/tile.py)
  - [`expectation/pass/tile/__main__.py`](../../expectation/pass/tile/__main__.py)
  - [`expectation/pass/tile/analysis/__main__.py`](../../expectation/pass/tile/analysis/__main__.py)
  - [`expectation/pass/tile/tile_only/__main__.py`](../../expectation/pass/tile/tile_only/__main__.py)
- 目标 `test`：
  - [`test/pass/test_lowering_tile.py`](../../test/pass/test_lowering_tile.py)
- 目标 `验收资产`：
  - [`expectation/pass/tile/__main__.py`](../../expectation/pass/tile/__main__.py)
  - [`expectation/pass/tile/analysis_only.py`](../../expectation/pass/tile/analysis_only.py)
  - [`expectation/pass/tile/basic.py`](../../expectation/pass/tile/basic.py)
  - [`expectation/pass/tile/analysis`](../../expectation/pass/tile/analysis)
  - [`expectation/pass/tile/tile_only`](../../expectation/pass/tile/tile_only)
- 目标 `功能实现`：
  - [`kernel_gen/passes/lowering/tile.py`](../../kernel_gen/passes/lowering/tile.py)
  - [`kernel_gen/tools/ircheck.py`](../../kernel_gen/tools/ircheck.py)

## 任务清单

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `S1` | `无` | `wt-20260413-tile-exp-s1` | `20260413-tile-exp-s1.md` |
| `S2` | `S1` | `wt-20260413-tile-exp-s2` | `20260413-tile-exp-s2.md` |
| `S3` | `S2` | `wt-20260413-tile-exp-s3` | `20260413-tile-exp-s3.md` |
| `S4` | `S3` | `wt-20260413-tile-exp-s4` | `20260413-tile-exp-s4.md` |
| `S5` | `S4` | `wt-20260413-tile-exp-s5` | `20260413-tile-exp-s5.md` |

## 评审摘要

- 评审结论：`通过`
- 评审人：`大闸蟹`、`守护最好的爱莉希雅`
- 结论摘要：
  - `tile` 继续保持单公开 pass；analysis 作为内部前置阶段，不额外新增公开 pass 名。
  - `expectation/pass/tile` 继续作为唯一目录级完成态；`__main__.py` 作为唯一黑盒入口。
  - 允许为跑通 `tile` 完整目录做保守范围的非 `expectation` 文件修正；但本轮主题仍只收口 `tile`。

## S5 环境补齐（2026-04-14 05:53）

- `异常背景`：
  - `T-20260413-4b821840` 已因执行环境缺失被暂停
  - `TODO.md` 中登记的 `worktree` `/home/lfr/kernelcode_generate/wt-20260413-tile-exp-s5` 与记录文件 `agents/codex-multi-agents/log/task_records/2026/15/20260413-tile-exp-s5.md` 当时均不存在
- `当前唯一口径`：
  - `S5` 不改任务号、不改目标范围，继续沿用原 `T-20260413-4b821840`
  - `worktree` 仍固定为 `/home/lfr/kernelcode_generate/wt-20260413-tile-exp-s5`
  - 记录文件仍固定为 `agents/codex-multi-agents/log/task_records/2026/15/20260413-tile-exp-s5.md`
- `恢复条件`：
  - 由架构侧补齐上述 `worktree` 与记录文件后，管理员即可恢复原 `spec` 任务
  - 上游依赖 `T-20260413-d0ad2711` 已完成后，不再另外追加口径修正

## S5 合同冲突口径（2026-04-14 06:46）

- `当前冲突收口`：
  - [`spec/pass/lowering/tile.md`](../../spec/pass/lowering/tile.md) 已明确 `tile-only` 的公开结果为 `tuner.param + tile.step_value + symbol.for + dma.view`
  - [`test/pass/test_lowering_tile.py`](../../test/pass/test_lowering_tile.py) 已固定 low-rank broadcast source 保持自身 rank，以及 fc 组合链路保留 carry alloc 并通过 verifier
  - [`expectation/pass/tile/tile_only`](../../expectation/pass/tile/tile_only) 当前仍残留旧口径：把 `tuner.param` 写成 `!symbol.int<"...">`，并要求 `CHECK-NOT: tile.step_value`
- `本轮唯一优先级`：
  1. 公开合同以 [`spec/pass/lowering/tile.md`](../../spec/pass/lowering/tile.md) 为准
  2. 已通过的 [`test/pass/test_lowering_tile.py`](../../test/pass/test_lowering_tile.py) 用于锁定 low-rank broadcast / fc carry alloc 的实现边界
  3. [`expectation/pass/tile/tile_only`](../../expectation/pass/tile/tile_only) 视为待同步资产，本轮应按前两者更新，不反向拉回 `spec` 或 `pytest`
- `必须收口到的具体合同`：
  - `tuner.param` 结果类型保持 `!symbol.dim<"...">`
  - `tile.step_value` 必须显式存在，并桥接为同名 `!symbol.int<"...">`
  - `fc` 路径允许保留前置 `dma.alloc` / `dma.transpose` 与 carry alloc，不要求为迎合旧 expectation 而删除这些前置 op
  - bias / broadcast 的 low-rank source view 必须保持 source 自身 rank，不再要求把 rank-1 bias source 扩成 rank-2 `dma.view`
- `本轮允许修改范围`：
  - [`expectation/pass/tile/__main__.py`](../../expectation/pass/tile/__main__.py)
  - [`expectation/pass/tile/tile_only/__main__.py`](../../expectation/pass/tile/tile_only/__main__.py)
  - [`expectation/pass/tile/tile_only/element_binary.py`](../../expectation/pass/tile/tile_only/element_binary.py)
  - [`expectation/pass/tile/tile_only/broadcast.py`](../../expectation/pass/tile/tile_only/broadcast.py)
  - [`expectation/pass/tile/tile_only/matmul.py`](../../expectation/pass/tile/tile_only/matmul.py)
  - [`expectation/pass/tile/tile_only/fc.py`](../../expectation/pass/tile/tile_only/fc.py)
  - 同链记录文件
- `明确不做`：
  - 不为了迁就旧 expectation 再回改 [`kernel_gen/passes/lowering/tile.py`](../../kernel_gen/passes/lowering/tile.py)
  - 不回改 [`test/pass/test_lowering_tile.py`](../../test/pass/test_lowering_tile.py) 去迎合旧 `CHECK`
  - 若后续又发现新的实现阻断，再单独回报架构侧，不在本轮补假设

## 计划目标

- 让 `tile` 的公开流程固定为：`先 analysis，再按 analysis 结果进行 tile 改写`。
- 保留当前公开选项集合：
  - `analysis-only`
  - `tile-only`
  - `tile-elewise`
  - `tile-reduce`
- 让 [`expectation/pass/tile`](../../expectation/pass/tile) 目录下的全部 expectation 与 [`test/pass/test_lowering_tile.py`](../../test/pass/test_lowering_tile.py) 最终都能通过。
- 把 `tile.analysis` 的文本合同、`tile-only` 的改写形态、`tile-reduce=true` 的临时累加内存形态都写成稳定示例。
- 允许为了跑通 `expectation/pass/tile` 做保守范围的相关导入与实现修正；但不借机扩展到其他 `nn lowering` 主题。

## 当前基线

- 当前公开 pass 入口仍是 [`kernel_gen/passes/lowering/tile.py`](../../kernel_gen/passes/lowering/tile.py) 中的 `tile`。
- 当前 [`spec/pass/lowering/tile.md`](../../spec/pass/lowering/tile.md) 已写明：
  - `analysis-only=true` 时只保留分析结果；
  - elementwise / matmul 是本轮主要支持对象；
  - `tile-reduce=true` 需要临时累加内存。
- 当前 [`expectation/pass/tile`](../../expectation/pass/tile) 已拆成三层：
  - 目录入口 [`expectation/pass/tile/__main__.py`](../../expectation/pass/tile/__main__.py)
  - 分析入口 [`expectation/pass/tile/analysis`](../../expectation/pass/tile/analysis)
  - 改写入口 [`expectation/pass/tile/tile_only`](../../expectation/pass/tile/tile_only)
- 当前目录内已覆盖：
  - analysis：`broadcast` / `element_binary` / `element_compare` / `matmul` / `fc`
  - tile-only：`element_binary` / `broadcast` / `matmul` / `fc`
当前需要收口的问题主要有四类：
  1. `analysis-only=true` 与 `tile-only=true` 当前在部分 expectation 中被同时使用，但这两个选项应视为互斥；相关 expectation / 实现 / 测试 需要统一修正。
  2. `tile.analysis` 的输出文本已经改成“只写角色标签、不写维度值”，但还需要统一为“按 operand、按维度”的唯一口径。
  3. `tile-reduce=true` 需要明确 `dma.alloc + dma.fill + partial compute + accumulate` 的完整形态。
  4. 主仓中仍有一部分相邻 expectation / helper / pass 导入问题会影响 tile 目录执行环境，需要在不偏题的前提下保守修正。

## 方案比较与选型

- 不采用方案：把 analysis 拆成单独公开 pass，例如 `tile-analysis`
- 不采用原因：
  - 会新增一层公开命名和注册负担；
  - 用户已要求“整个 tile 的流程是先分析，然后根据分析对被分析的算子进行 tile”，更适合保持单入口。

- 不采用方案：目录级只保留单个 `basic.py`，不再保留 `analysis/` 与 `tile_only/`
- 不采用原因：
  - 调试单类问题时不方便；
  - 用户明确希望能单跑某一组 case 并看到完整 IR 变化。

- 不采用方案：顺手把整个 `expectation/pass/lowing/nn_lowering` 一起大改
- 不采用原因：
  - 本计划目标只收口 `expectation/pass/tile`；
  - 与 tile 无关的 `nn lowering` 公开口径不应在这一轮顺带扩写。

- 采用方案：
  1. `tile` 继续保持单公开 pass；
  2. `analysis-only=true` 表示内部 analysis 阶段执行后立刻停止；
  3. `tile-only=true` 表示先执行 analysis，再进入 tile 改写；
  4. `tile.analysis` 只作为 analysis 阶段的中间合同，进入 tile 改写后必须消失；
  5. 目录级唯一完成态固定为 `PYTHONPATH=. python -m expectation.pass.tile`；
  6. 与 tile 执行环境直接相关的旧导入或实现问题只做保守修正，不扩主题。

## 公开 API 设计

### 一、公开 pass

- 公开入口：`TilePass`
- 名字：`tile`
- 构造方式：
  - `TilePass()`
  - `TilePass.from_options({...})`

最小示例：

```python
from kernel_gen.passes.lowering.tile import TilePass

analysis_pass = TilePass.from_options(
    {
        "analysis-only": "true",
        "tile-elewise": "true",
        "tile-reduce": "false",
    }
)

rewrite_pass = TilePass.from_options(
    {
        "tile-only": "true",
        "tile-elewise": "true",
        "tile-reduce": "true",
    }
)
```

### 二、analysis 阶段公开结果

- `analysis` 不是独立公开 pass。
- `analysis-only=true` 时，输出 IR 中允许出现：
  - `tile.analysis`
  - `tuner.param`
  - `symbol.get_dim`
- 不允许出现：
  - `symbol.for`
  - `dma.view`
  - `tile.step_value`
  - `tile.symbol_literal`
- `analysis-only` 与 `tile-only` 互斥；同时传入必须报错。

最小示例：

```text
"kernel.binary_elewise"(%lhs, %rhs, %out)
  {kind = "add", tile.analysis = [["elewise", "elewise"], ["elewise", "elewise"], ["elewise", "elewise"]]}
```

### 三、tile 改写阶段公开结果

- `tile-only=true` 时：
  - 必须先消费 `tile.analysis`
  - 再生成 `tuner.param + symbol.for + dma.view`
  - 最终不再保留 `tile.analysis`
- `tile-elewise=true` 时：
  - 只对 `elewise` 维度切分；
  - `expand` 维度只参与 view 形状推导，不生成本维度循环。
- `tile-reduce=true` 时：
  - 对 `reduce` 维度允许切分；
  - 必须显式插入临时累加内存与初始化步骤。

最小示例：

```text
%tm = tuner.param : !symbol.int<"TILE_M0">
symbol.for %i = %c0 to %m step %tm { ... }
```

### 四、本轮固定支持的 option 组合

- analysis 目录：
  - `--pass "tile={analysis-only=true,tile-elewise=true,tile-reduce=false}"`
- tile-only 目录：
  - `--pass "tile={tile-only=true,tile-elewise=true,tile-reduce=false}"`
  - `--pass "tile={tile-only=true,tile-elewise=true,tile-reduce=true}"`

说明：

- 本轮计划只收口上述 expectation 已使用到的 option 组合。
- 不额外扩写未出现在 [`expectation/pass/tile`](../../expectation/pass/tile) 里的组合语义。

## 完成态定义

- [`expectation/pass/tile/analysis`](../../expectation/pass/tile/analysis) 目录中的全部 case 可运行通过。
- [`expectation/pass/tile/tile_only`](../../expectation/pass/tile/tile_only) 目录中的全部 case 可运行通过。
- 目录入口 [`expectation/pass/tile/__main__.py`](../../expectation/pass/tile/__main__.py) 可作为唯一黑盒入口一次性跑完整个 tile expectation 目录。
- [`test/pass/test_lowering_tile.py`](../../test/pass/test_lowering_tile.py) 需同时通过，不能只收口 expectation 目录。
- `analysis-only=true` 时：
  - 只保留分析结果；
  - 不生成 loop / view 改写。
- `tile-only=true` 时：
  - analysis 阶段先执行；
  - 之后根据 `tile.analysis` 生成改写；
  - 改写后 `tile.analysis` 消失。
- `analysis-only` 与 `tile-only` 同时出现时必须直接失败，不允许作为完成态存在。
- `tile-elewise=true` 时：
  - 只有全 `elewise` 的维度会被切分；
  - `broadcast` 这类带 `expand` 维度的 op，只切分 `elewise` 维度。
- `tile-reduce=true` 时：
  - `matmul` 等存在 `reduce` 维的 case 需要显式临时累加内存；
  - 不能省略 `dma.alloc` / `dma.fill` / partial accumulate 链路。
- 为跑通 tile 目录所需的相关修正，允许保守修改 `expectation` 以外、但与 tile 执行直接相关的文件；不扩成大范围 `nn lowering` 改名任务。
- 当 `expectation/pass/tile` 与 `test/pass/test_lowering_tile.py` 口径不一致时，优先按 `expectation` 收口，再同步测试。

## 验收设计

- 目录级完成态：
  - `PYTHONPATH=. python -m expectation.pass.tile`
- 分阶段复核入口：
  - `PYTHONPATH=. python -m expectation.pass.tile.analysis`
  - `PYTHONPATH=. python -m expectation.pass.tile.tile_only`
  - `PYTHONPATH=. python expectation/pass/tile/analysis_only.py`
  - `PYTHONPATH=. python expectation/pass/tile/basic.py`
- 相关实现测试：
  - `pytest -q test/pass/test_lowering_tile.py`

输入样例固定关注四类：

1. 单 op analysis：
   - `element_binary`
   - `element_compare`
   - `broadcast`
   - `matmul`
2. 组合 analysis：
   - `fc`
3. tile-only 改写：
   - `element_binary`
   - `broadcast`
   - `matmul`
   - `fc`
4. reduce 改写：
   - `matmul` 的 `tile-reduce=true`

锁定输出固定关注五类：

1. `tile.analysis` 是否按 operand / 维度逐项输出角色标签。
2. `analysis-only=true` 是否不会产生 `symbol.for` / `dma.view`。
3. `analysis-only=true` 与 `tile-only=true` 同时出现时是否直接失败。
4. `tile-only=true` 是否把 `tile.analysis` 转换为 `tuner.param + symbol.for + dma.view`。
5. `expectation` 与 `test` 不一致时是否先按 `expectation` 收口。
6. `broadcast` 是否只切 `elewise` 维，不切 `expand` 维。
7. `tile-reduce=true` 是否显式出现累加缓冲链路。

## 阶段拆分

### S1：`tile` 单入口合同与 option 组合收口

#### 阶段目标

- 把 `tile` 的单入口流程、公开 option 组合、analysis 与 rewrite 的前后关系写成唯一合同，并同步到实现测试。

#### 目标 spec / API

- [`spec/pass/lowering/tile.md`](../../spec/pass/lowering/tile.md)
- 公开 API：
  - `TilePass`
  - `TilePass.from_options(options)`

#### 可改文件

- `spec/pass/lowering/tile.md`
- `kernel_gen/passes/lowering/tile.py`
- `test/pass/test_lowering_tile.py`

#### 预期示例代码

```python
pass_obj = TilePass.from_options(
    {
        "analysis-only": "true",
        "tile-elewise": "true",
        "tile-reduce": "false",
    }
)
module = pass_obj.run(module)
```

#### 预期输出

```text
analysis-only=true 时：
- 允许出现 tile.analysis
- 不允许出现 symbol.for / dma.view

analysis-only=true 与 tile-only=true 同时存在时：
- 直接报错

tile-only=true 时：
- analysis 先执行
- 再出现 tuner.param / symbol.for / dma.view
- tile.analysis 消失
```

#### 目标验收资产

- [`spec/pass/lowering/tile.md`](../../spec/pass/lowering/tile.md)
- [`test/pass/test_lowering_tile.py`](../../test/pass/test_lowering_tile.py)

#### 必过项目

- `pytest -q test/pass/test_lowering_tile.py`

#### 任务新建建议

- `任务类型：other`
- `任务目标：收口 tile 单入口流程、公开 option 组合与基础测试`
- `记录文件：20260413-tile-exp-s1.md`

### S2：analysis 结果文本与目录入口收口

#### 阶段目标

- 把 `analysis` 目录中的单 op / 组合链路输出统一为“按 operand、按维度”的角色标签文本，并固定目录入口，同时清掉 analysis case 中与 `tile-only` 并存的非法 option 组合。

#### 目标 spec / API

- [`spec/pass/lowering/tile.md`](../../spec/pass/lowering/tile.md)
- [`expectation/pass/tile/analysis/__main__.py`](../../expectation/pass/tile/analysis/__main__.py)

#### 可改文件

- `kernel_gen/passes/lowering/tile.py`
- `expectation/pass/tile/analysis/__main__.py`
- `expectation/pass/tile/analysis/broadcast.py`
- `expectation/pass/tile/analysis/element_binary.py`
- `expectation/pass/tile/analysis/element_compare.py`
- `expectation/pass/tile/analysis/matmul.py`
- `expectation/pass/tile/analysis/fc.py`
- `expectation/pass/tile/analysis_only.py`

#### 预期示例代码

```text
"dma.broadcast"(%out, %src)
  {tile.analysis = [["elewise", "elewise"], ["expand", "elewise"]]}
```

#### 预期输出

```text
analysis case 只输出角色标签：
- 不写具体 dim 值
- 按 operand 顺序写
- 每个 operand 内按维度顺序写
```

#### 目标验收资产

- [`expectation/pass/tile/analysis`](../../expectation/pass/tile/analysis)
- [`expectation/pass/tile/analysis_only.py`](../../expectation/pass/tile/analysis_only.py)

#### 必过项目

- `PYTHONPATH=. python -m expectation.pass.tile.analysis`
- `PYTHONPATH=. python expectation/pass/tile/analysis_only.py`

#### 任务新建建议

- `任务类型：other`
- `任务目标：收口 tile analysis 文本合同、analysis 目录入口与非法 option 组合`
- `记录文件：20260413-tile-exp-s2.md`

### S3：elementwise / broadcast 的 tile-only 改写收口

#### 阶段目标

- 收口 `element_binary` 与 `broadcast` 在 `tile-only=true,tile-elewise=true,tile-reduce=false` 下的改写形态。

#### 目标 spec / API

- [`spec/pass/lowering/tile.md`](../../spec/pass/lowering/tile.md)
- [`expectation/pass/tile/tile_only/__main__.py`](../../expectation/pass/tile/tile_only/__main__.py)

#### 可改文件

- `kernel_gen/passes/lowering/tile.py`
- `test/pass/test_lowering_tile.py`
- `expectation/pass/tile/tile_only/__main__.py`
- `expectation/pass/tile/tile_only/element_binary.py`
- `expectation/pass/tile/tile_only/broadcast.py`
- `expectation/pass/tile/basic.py`

#### 预期示例代码

```text
// COMPILE_ARGS: --pass "tile={tile-only=true,tile-elewise=true,tile-reduce=false}"

"dma.broadcast"(%out, %src)
  {tile.analysis = [["elewise", "elewise"], ["expand", "elewise"]]}
```

#### 预期输出

```text
- 只对 elewise 维生成 symbol.for
- expand 维不生成本维度循环
- 生成 tuner.param / dma.view
- tile.analysis 在改写后消失
```

#### 目标验收资产

- [`expectation/pass/tile/tile_only/element_binary.py`](../../expectation/pass/tile/tile_only/element_binary.py)
- [`expectation/pass/tile/tile_only/broadcast.py`](../../expectation/pass/tile/tile_only/broadcast.py)
- [`expectation/pass/tile/basic.py`](../../expectation/pass/tile/basic.py)

#### 必过项目

- `PYTHONPATH=. python expectation/pass/tile/tile_only/element_binary.py`
- `PYTHONPATH=. python expectation/pass/tile/tile_only/broadcast.py`
- `PYTHONPATH=. python -m expectation.pass.tile.tile_only`

#### 任务新建建议

- `任务类型：other`
- `任务目标：收口 tile-only 的 elementwise 与 broadcast 改写`
- `记录文件：20260413-tile-exp-s3.md`

### S4：matmul / fc / tile-reduce 的改写收口

#### 阶段目标

- 收口 `matmul`、`fc` 与 `tile-reduce=true` 的完整改写，尤其是临时累加内存、partial compute、逐 op 独立 loop 的形态。

#### 目标 spec / API

- [`spec/pass/lowering/tile.md`](../../spec/pass/lowering/tile.md)
- [`expectation/pass/tile/tile_only/matmul.py`](../../expectation/pass/tile/tile_only/matmul.py)
- [`expectation/pass/tile/tile_only/fc.py`](../../expectation/pass/tile/tile_only/fc.py)

#### 可改文件

- `kernel_gen/passes/lowering/tile.py`
- `test/pass/test_lowering_tile.py`
- `expectation/pass/tile/tile_only/matmul.py`
- `expectation/pass/tile/tile_only/fc.py`
- `expectation/pass/tile/tile_only/__main__.py`

#### 预期示例代码

```text
// COMPILE_ARGS: --pass "tile={tile-only=true,tile-elewise=true,tile-reduce=true}"

"kernel.matmul"(%lhs, %rhs, %out)
  {tile.analysis = [["elewise", "reduce"], ["reduce", "elewise"], ["elewise", "elewise"]]}
```

#### 预期输出

```text
- matmul 可生成 M/N 或 M/N/K 的循环结构
- tile-reduce=true 时显式出现 dma.alloc + dma.fill
- partial matmul 结果写入临时缓冲
- 后续通过 kernel.binary_elewise 做累加
- fc 中 broadcast / matmul / elementwise 各自拥有独立循环与独立 step
```

#### 目标验收资产

- [`expectation/pass/tile/tile_only/matmul.py`](../../expectation/pass/tile/tile_only/matmul.py)
- [`expectation/pass/tile/tile_only/fc.py`](../../expectation/pass/tile/tile_only/fc.py)

#### 必过项目

- `PYTHONPATH=. python expectation/pass/tile/tile_only/matmul.py`
- `PYTHONPATH=. python expectation/pass/tile/tile_only/fc.py`
- `PYTHONPATH=. python -m expectation.pass.tile.tile_only`

#### 任务新建建议

- `任务类型：other`
- `任务目标：收口 tile-reduce 与 fc 组合链路改写`
- `记录文件：20260413-tile-exp-s4.md`

### S5：目录级黑盒入口与相邻导入修正收口

#### 阶段目标

- 让 `expectation/pass/tile` 目录入口成为唯一黑盒完成态，并把与 tile 运行环境直接相关的旧导入 / 实现问题收掉。

#### 目标 spec / API

- [`expectation/pass/tile/__main__.py`](../../expectation/pass/tile/__main__.py)
- [`expectation/pass/tile/basic.py`](../../expectation/pass/tile/basic.py)
- [`expectation/pass/tile/analysis_only.py`](../../expectation/pass/tile/analysis_only.py)

#### 可改文件

- `expectation/pass/tile/__main__.py`
- `expectation/pass/tile/basic.py`
- `expectation/pass/tile/analysis_only.py`
- `expectation/pass/tile/tile_only/__main__.py`
- `expectation/pass/tile/tile_only/element_binary.py`
- `expectation/pass/tile/tile_only/broadcast.py`
- `expectation/pass/tile/tile_only/matmul.py`
- `expectation/pass/tile/tile_only/fc.py`
- `expectation/pass/lowing/nn_lowering/broadcast.py`
- `expectation/pass/lowing/nn_lowering/broadcast_to.py`
- `expectation/utils/pass_lowering_nn_to_kernel.py`
- `kernel_gen/passes/lowering/tile.py`
- `test/pass/test_lowering_tile.py`

#### 预期示例代码

```text
PYTHONPATH=. python -m expectation.pass.tile
```

#### 预期输出

```text
- 目录入口能串起 analysis 与 tile_only 全部 case
- 不再因为旧 LowerNnToKernelPass 导入名导致相邻 expectation 环境报错
- 目录完成态只以 expectation/pass/tile 为主，不扩成其它主题清理
```

#### 目标验收资产

- [`expectation/pass/tile/__main__.py`](../../expectation/pass/tile/__main__.py)
- [`expectation/pass/tile`](../../expectation/pass/tile)

#### 必过项目

- `PYTHONPATH=. python -m expectation.pass.tile`
- `pytest -q test/pass/test_lowering_tile.py`

#### 任务新建建议

- `任务类型：other`
- `任务目标：收口 tile 目录入口与相邻旧导入问题`
- `记录文件：20260413-tile-exp-s5.md`

## 待确认项

- 当前无新增待确认项。
- 本轮用户已确认：
  - `tile-only` 继续保留为公开选项；
  - `analysis-only=true` 与 `tile-only=true` 互斥，不允许同时存在；
  - 完成态同时看 [`expectation/pass/tile`](../../expectation/pass/tile) 与 [`test/pass/test_lowering_tile.py`](../../test/pass/test_lowering_tile.py)；
  - 若与 tile 通过直接相关，可保守修改 `expectation` 以外的相关文件；
  - 一般情况下 `expectation` 与 `test` 不一致时，优先按 `expectation` 收口；
  - 但 `T-20260413-4b821840` 当前命中的 `tile_only` 旧 expectation 冲突，改以 [`spec/pass/lowering/tile.md`](../../spec/pass/lowering/tile.md) 与已通过的 [`test/pass/test_lowering_tile.py`](../../test/pass/test_lowering_tile.py) 为准，再同步更新 [`expectation/pass/tile/tile_only`](../../expectation/pass/tile/tile_only)。

## 最终验收结论（2026-04-14 07:48）

- `我的结论`：`通过`
- `通过依据`：
  - [`TODO.md`](../../TODO.md) 中 [`ARCHITECTURE/plan/tile_pass_expectation_refactor_green_plan.md`](../../ARCHITECTURE/plan/tile_pass_expectation_refactor_green_plan.md) 当前已为 `5 / 5 / 0 / 完成待检查`
  - [`DONE.md`](../../DONE.md) 中 `T-20260413-4b821840` 已完成，说明本计划最后一项 `S5` 已按链路收尾
  - [`agents/codex-multi-agents/log/task_records/2026/15/20260413-tile-exp-s5.md`](../../agents/codex-multi-agents/log/task_records/2026/15/20260413-tile-exp-s5.md) 已记录完整闭环：先补齐执行环境，再明确 `spec + pytest -> expectation` 的唯一口径，随后完成 build、review、merge
  - 当前主仓 [`spec/pass/lowering/tile.md`](../../spec/pass/lowering/tile.md)、[`spec/tools/ircheck.md`](../../spec/tools/ircheck.md) 与 [`expectation/pass/tile/tile_only/fc.py`](../../expectation/pass/tile/tile_only/fc.py) / [`expectation/pass/tile/tile_only/matmul.py`](../../expectation/pass/tile/tile_only/matmul.py) / [`expectation/pass/tile/tile_only/broadcast.py`](../../expectation/pass/tile/tile_only/broadcast.py) 的文本合同已一致收口到 `tuner.param : !symbol.dim + tile.step_value + symbol.for + dma.view`
  - `S5` 记录中的最终验证已覆盖：
    - `PYTHONPATH=<tile_worktree>:<repo_root> python -m expectation.pass.tile`
    - `PYTHONPATH=<tile_worktree>:<repo_root> python expectation/pass/tile/basic.py`
    - `PYTHONPATH=<tile_worktree>:<repo_root> python expectation/pass/tile/analysis_only.py`
    - `pytest -q test/pass/test_lowering_tile.py`
    - 上述结果均已通过，且复审结论为 `通过`
- `验收摘要`：
  - 本计划要求的目录级黑盒入口、兼容入口、`tile-only` expectation、`tile-reduce/fc` 组合链路，以及 `ircheck` 多 step 示例顺序，均已按最新公开合同收口
  - `tile` 主题本轮不再存在新的最小阻断项，可进入计划归档链路

## 参考资料

- MLIR Passes 文档：<https://mlir.llvm.org/docs/Passes/>
- MLIR Transform Dialect 文档：<https://mlir.llvm.org/docs/Dialects/Transform/>
- 参考借鉴点：
  - 维持“单公开变换入口 + 内部分析阶段”的组织方式；
  - 把分析结果与改写结果分成前后两个可观察状态，便于 expectation 分目录收口；
  - option 由 pass 自身消费，不把业务语义塞进工具层。
