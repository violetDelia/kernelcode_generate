# codebase_refactor_baseline_green_plan.md

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`大闸蟹`
- 来源草稿：
  - [`redine.plan.md`](../../redine.plan.md)
- 目标 `spec`：
  - [`agents/standard/测试文件约定.md`](../../agents/standard/测试文件约定.md)
  - [`spec/dsl/ast.md`](../../spec/dsl/ast.md)
  - [`spec/pass/pass_manager.md`](../../spec/pass/pass_manager.md)
- 目标 `test`：
  - [`test/dsl`](../../test/dsl)
  - [`test/operation`](../../test/operation)
  - [`test/dialect`](../../test/dialect)
  - [`test/codex-multi-agents`](../../test/codex-multi-agents)
  - [`test/script`](../../test/script)
- 目标 `功能实现`：
  - [`kernel_gen/common`](../../kernel_gen/common)
  - [`kernel_gen/symbol_variable`](../../kernel_gen/symbol_variable)
  - [`kernel_gen/dsl/ast.py`](../../kernel_gen/dsl/ast.py)

## 进度

| 编号 | 依赖 | worktree | 记录文件 | 进度 |
| --- | --- | --- | --- | --- |
| `S1` | `无` | `wt-20260411-refactor-s1` | `20260411-refactor-s1.md` | `未开始` |
| `S2` | `S1` | `wt-20260411-refactor-s2` | `20260411-refactor-s2.md` | `未开始` |
| `S3` | `S2` | `wt-20260411-refactor-s3` | `20260411-refactor-s3.md` | `未开始` |
| `S4` | `S3` | `wt-20260411-refactor-s4` | `20260411-refactor-s4.md` | `未开始` |
| `S5` | `S4` | `wt-20260411-refactor-s5` | `20260411-refactor-s5.md` | `未开始` |
| `S6` | `S5` | `wt-20260413-refactor-s6` | `20260413-refactor-s6.md` | `未开始` |

## 评审摘要

- `评审结论`：`通过`
- `评审人`：`大闸蟹`、`守护最好的爱莉希雅`
- `摘要`：`计划目标已收口到 pytest 配置、错误模板、dtype 常量与 dsl.ast 拆分；当前方案比继续做大范围横切重构更稳；阶段顺序采用先公共基线、再逐项收口；测试 ownership 先审计再做最小收口；整体可维护性足够。`

## 当前验收补充（2026-04-13）

- `验收结论`：`不通过`
- `阻断项`：
  - `pytest -m "not infra"` 当前直接在主仓出现 `390 errors during collection`
  - `pytest -m infra` 当前同样出现 `390 errors during collection`
  - 主要失败集中在两类：
    1. 同 basename 测试文件的 import file mismatch（例如 `test/include/api/test_memory.py` 与 `test/include/cpu/test_memory.py`）
    2. `wt-*` 与 `tmp/li_bai_quarantine/*` 目录被 pytest 一并收进来，导致主仓与 worktree 测试重复采集
  - 当前公共常量收敛已基本完成：`rg "_ERROR_TEMPLATE\\s*=|_FLOAT_DTYPES\\s*=|_INT_DTYPES\\s*=" kernel_gen` 只剩
    - [`kernel_gen/common/errors.py`](../../kernel_gen/common/errors.py)
    - [`kernel_gen/symbol_variable/dtype_constants.py`](../../kernel_gen/symbol_variable/dtype_constants.py)
- `后续收口任务`：
  - `S6` 只处理 pytest 采集范围与测试模块命名冲突
  - 目标是让计划书里的 pytest 命令可在主仓直接运行，不再把 `wt-*` / `tmp/*` 一并采集进来

## S6 拆分补充（2026-04-14 05:39）

- `阻塞背景`：
  - `T-20260413-d1708430` 已按异常规则暂停
  - `wt-20260413-refactor-s6` 当前待合并范围混入 `skills/codex-multi-agents/scripts/codex-multi-agents-task-core.py` 与 `skills/codex-multi-agents/scripts/codex-multi-agents-task.sh`
  - 按 [`agents/standard/合并规范.md`](../../agents/standard/合并规范.md)，`skills/` 目录不得进入标准 merge
- `主仓允许合并范围`：
  - [`pyproject.toml`](../../pyproject.toml)
  - [`spec/script/pytest_config.md`](../../spec/script/pytest_config.md)
  - [`test/script/test_pytest_config.py`](../../test/script/test_pytest_config.py)
  - 同链任务记录文件
- `明确排除范围`：
  - `skills/codex-multi-agents/**`
  - `script/notify-admin.sh`
  - `test/codex-multi-agents/**`
  - `kernel_gen/**`
  - `test/dsl/**`
  - `test/dialect/**`
- `执行口径`：
  - 当前暂停的 `merge` 任务不恢复原范围，不允许李白在同一任务里挑拣合并 `skills/` 以外文件
  - 先由新的 `build` 修复任务把 `wt-20260413-refactor-s6` 收口到上述允许范围，再按 `build -> review -> merge` 重新续接
  - 被排除的 `skills/script/kernel_gen/test` 改动不在本计划当前 `S6` 处理，后续如仍需保留，必须另起明确范围的任务链路

## S6 续链执行口径（2026-04-14 05:53）

- `续链形态`：
  - 在原 `T-20260413-d1708430` 之外补建一个新的 `build` 修复任务
  - 该修复任务专用 `worktree` 固定为 `/home/lfr/kernelcode_generate/wt-20260414-refactor-s6-split`
  - 该修复任务记录文件固定为 `agents/codex-multi-agents/log/task_records/2026/16/20260414-refactor-s6-split.md`
- `修复任务目标`：
  - 只处理“把 refactor S6 当前可合入主仓的范围从混合差异中拆出来”这一件事
  - 允许保留的文件仍只限 [`pyproject.toml`](../../pyproject.toml)、[`spec/script/pytest_config.md`](../../spec/script/pytest_config.md)、[`test/script/test_pytest_config.py`](../../test/script/test_pytest_config.py) 与同链记录文件
  - 修复任务必须显式剥离 `skills/`、`script/notify-admin.sh`、`kernel_gen/`、`test/dsl/`、`test/dialect/`、`test/codex-multi-agents/` 等不在本轮允许范围内的差异
- `管理员推进口径`：
  - `T-20260413-d1708430` 继续保持暂停，不恢复原 `merge`
  - 先分发新的 `build` 修复任务；待其通过 `review` 后，再另起合法 `merge` 续接

## S6 收尾口径（2026-04-14 07:11）

- `替代链结果`：
  - `T-20260414-b96a7527` 已完成 `build -> review -> merge` 并合入主仓
  - 该替代链已完整收口本计划 `S6` 允许进入主仓的全部范围：[`pyproject.toml`](../../pyproject.toml)、[`spec/script/pytest_config.md`](../../spec/script/pytest_config.md)、[`test/script/test_pytest_config.py`](../../test/script/test_pytest_config.py) 与同链记录
- `对原任务 T-20260413-d1708430 的结论`：
  - 不再补建新的合法 `merge` 任务
  - 原 `merge` 任务按“已被替代链收口、无额外合法合并内容”直接收尾
  - `wt-20260413-refactor-s6` 中剩余 `skills/`、`script/notify-admin.sh`、`kernel_gen/`、`test/codex-multi-agents/`、`test/dsl/`、`test/dialect/` 等差异继续视为本计划 `S6` 明确排除范围，不在当前计划内续接
- `管理员动作`：
  - 将 `T-20260413-d1708430` 作为“替代链已完成”的暂停任务直接停止推进并从当前进行中列表收尾
  - 如后续仍需保留 `wt-20260413-refactor-s6` 中的排除范围改动，必须另起新的明确任务链路，不复用 `T-20260413-d1708430`

## 最终验收结论（2026-04-14 07:17）

- `我的结论`：`通过`
- `通过依据`：
  - `TODO.md` 当前已将本计划收口为 `7/7`，状态为 `完成待检查`
  - `T-20260414-b96a7527` 已完成 `build -> review -> merge` 并合入主仓，覆盖了本计划 `S6` 唯一允许进入主仓的文件集合
  - 原暂停任务 `T-20260413-d1708430` 已按“被替代链收口、无额外合法合并内容”收尾，不再残留本计划内部未决的合法续链
- `验收范围说明`：
  - 本次终验按本计划已明确的 `S6` 收口边界判定，只检查 pytest 配置拆分范围是否已闭环进入主仓
  - `wt-20260413-refactor-s6` 中继续被排除的 `skills/`、`kernel_gen/`、`test/dsl/`、`test/dialect/` 等差异，不属于本计划当前通过条件
- `管理员后续`：
  - 就我这边的最终验收意见，此计划书已可进入归档链路

## 计划目标

- 基于 [`redine.plan.md`](../../redine.plan.md) 的原始重构草案，裁掉已经不成立或当前证据不足的子任务，整理成可直接分发的串行任务书。
- 优先处理当前仓库里已经有明确静态证据的问题：
  1. 缺少统一 pytest 配置
  2. `_ERROR_TEMPLATE` 仍在多个文件重复
  3. dtype 常量仍有重复定义
  4. [`kernel_gen/dsl/ast.py`](../../kernel_gen/dsl/ast.py) 仍是 3234 行大文件
- 把“测试重叠 / ownership 混乱”从原草案里的笼统大任务，改成“先审计，再最小收口”，避免一开始就分发没有边界的大扫除。

## 当前现状（按当前仓库静态检查）

- `pyproject.toml` 当前不存在。
- `_ERROR_TEMPLATE` 当前在 `kernel_gen/` 中重复定义 `10` 处：
  - [`kernel_gen/operation/arch.py`](../../kernel_gen/operation/arch.py)
  - [`kernel_gen/operation/nn.py`](../../kernel_gen/operation/nn.py)
  - [`kernel_gen/operation/scf.py`](../../kernel_gen/operation/scf.py)
  - [`kernel_gen/operation/dma.py`](../../kernel_gen/operation/dma.py)
  - [`kernel_gen/target/registry.py`](../../kernel_gen/target/registry.py)
  - [`kernel_gen/dialect/arch.py`](../../kernel_gen/dialect/arch.py)
  - [`kernel_gen/dialect/tuner.py`](../../kernel_gen/dialect/tuner.py)
  - [`kernel_gen/dialect/symbol.py`](../../kernel_gen/dialect/symbol.py)
  - [`kernel_gen/dialect/nn.py`](../../kernel_gen/dialect/nn.py)
  - [`kernel_gen/dialect/kernel.py`](../../kernel_gen/dialect/kernel.py)
- dtype 常量当前仍分散：
  - [`kernel_gen/operation/nn.py`](../../kernel_gen/operation/nn.py) 有 `_NN_FLOAT_DTYPES`
  - [`kernel_gen/operation/dma.py`](../../kernel_gen/operation/dma.py) 有 `_FLOAT_DTYPES` 与 `_INT_DTYPES`
- [`kernel_gen/dsl/ast.py`](../../kernel_gen/dsl/ast.py) 当前 `3234` 行。
- `infra` marker 当前未落到 [`test/codex-multi-agents`](../../test/codex-multi-agents) 与 [`test/script`](../../test/script)。
- 原草案里的“跨测试 import”目前静态检索没有直接命中：
  - `importlib.util.spec_from_file_location.*test/`：当前未命中
  - `from test.`：当前未命中
- 原草案里的“dialect 测试直接调用 operation 层 API”目前静态检索也未直接命中，因此这一块不宜直接发实现任务，应该先做审计。

## 精炼结果

相对 [`redine.plan.md`](../../redine.plan.md)，这版任务书做了三件事：

1. **保留** 当前有明确证据的问题  
   - pytest 配置
   - 错误模板收敛
   - dtype 常量收敛
   - ast 模块拆分

2. **降级** 证据不足的问题  
   - 测试 ownership / 重叠问题先做审计，再决定最小改动

3. **移出第一轮** 当前未观察到直接证据的问题  
   - 跨测试 import 清理不再单独立项
   - e2e helper 抽取不再提前假定需要做

## 固定范围

- 不改变现有公开 API 的语义和函数签名。
- 不引入新外部依赖。
- 不处理 [`expectation`](../../expectation) 目录。
- 不处理 AGENTS 文档补全。
- `S1 -> S5` 按串行推进，避免 `dsl/ast.py`、公共错误模块、测试配置三类共享面同时被多任务改写。

## 新增文件配套规则

- 本计划内只要新增实现文件，就必须同时明确它的 `spec` 与 `test` 配套；不能只新增实现文件本体。
- 若新增的是配置文件、公共模块、helper 模块，同样需要：
  1. 一份明确说明其公开职责的 `spec`
  2. 一份直接验证该文件行为或可见结果的 `test`
- 执行人收到阶段任务时，若发现计划里提到的新文件没有配套的 `spec/test` 路径，必须先回报管理员，不直接开做。
- 本计划里几类重点新增文件的配套口径固定如下：

| 新增文件 | 必须同步的 spec | 必须同步的 test |
| --- | --- | --- |
| `pyproject.toml` | `spec/script/pytest_config.md` | `test/script/test_pytest_config.py` |
| `kernel_gen/common/errors.py` | `spec/common/errors.md` | `test/common/test_errors.py` |
| `kernel_gen/symbol_variable/dtype_constants.py` | `spec/symbol_variable/dtype_constants.md` | `test/symbol_variable/test_dtype_constants.py` |
| `kernel_gen/dsl/ast_nodes.py` | `spec/dsl/ast_nodes.md` | `test/dsl/test_ast_nodes.py` |
| `kernel_gen/dsl/ast_parser.py` | `spec/dsl/ast_parser.md` | `test/dsl/test_ast_parser.py` |

- 若阶段内新增了这里未列出的新文件，也必须按同一规则补齐 `spec/test`，再进入实现与审查。

## 验收命令

- `pytest -m "not infra"`
- `pytest -m infra`
- `pytest -q test/dsl`
- `pytest -q test/operation`
- `pytest -q test/dialect`
- `rg "_ERROR_TEMPLATE\\s*=" kernel_gen`
- `rg "_FLOAT_DTYPES\\s*=" kernel_gen`
- `rg "_INT_DTYPES\\s*=" kernel_gen`

## 阶段拆分

### S1：pytest 基础配置与测试标签

#### 阶段目标

- 补齐统一 pytest 配置，并把基础设施测试与产品测试分开运行。

#### 当前依据

- 当前没有 [`pyproject.toml`](../../pyproject.toml)。
- [`test/codex-multi-agents`](../../test/codex-multi-agents) 与 [`test/script`](../../test/script) 当前没有 `infra` marker。

#### 目标文件

- `pyproject.toml`
- `spec/script/pytest_config.md`
- `test/script/test_pytest_config.py`
- `test/codex-multi-agents/**`
- `test/script/**`

#### 预期输出

```text
1) pytest 有统一 marker 配置
2) infra 测试可单独运行
3) 产品测试可排除 infra 后单独运行
4) pyproject.toml 有对应 spec 与专门测试
```

#### 验收命令

- `pytest -m "not infra"`
- `pytest -m infra`

#### 任务新建建议

- `首个任务类型：spec`
- `阶段内续接：build -> review -> merge`
- `任务目标：建立 pytest 配置并补齐 infra marker`
- `记录文件：20260411-refactor-s1.md`

### S2：错误模板与 dtype 常量收敛

#### 阶段目标

- 先把低风险、重复度最高的公共常量抽出来，减少后续 AST 与测试整理时的噪音。

#### 当前依据

- `_ERROR_TEMPLATE` 当前重复 `10` 处。
- dtype 常量当前至少分散在 [`kernel_gen/operation/nn.py`](../../kernel_gen/operation/nn.py) 与 [`kernel_gen/operation/dma.py`](../../kernel_gen/operation/dma.py)。

#### 目标文件

- `kernel_gen/common/__init__.py`
- `kernel_gen/common/errors.py`
- `spec/common/errors.md`
- `test/common/test_errors.py`
- `kernel_gen/symbol_variable/dtype_constants.py`
- `spec/symbol_variable/dtype_constants.md`
- `test/symbol_variable/test_dtype_constants.py`
- `kernel_gen/operation/nn.py`
- `kernel_gen/operation/dma.py`
- 其余使用 `_ERROR_TEMPLATE` 的 `operation/dialect/target` 文件

#### 预期输出

```text
1) _ERROR_TEMPLATE 只剩一处定义
2) dtype 常量只剩一处规范定义
3) 现有错误文本不变
4) 新增公共模块都有各自 spec 与专门测试
```

#### 验收命令

- `rg "_ERROR_TEMPLATE\\s*=" kernel_gen`
- `rg "_FLOAT_DTYPES\\s*=" kernel_gen`
- `rg "_INT_DTYPES\\s*=" kernel_gen`
- `pytest -q test/operation`
- `pytest -q test/dialect`

#### 任务新建建议

- `首个任务类型：spec`
- `阶段内续接：build -> review -> merge`
- `任务目标：收敛错误模板与 dtype 常量`
- `记录文件：20260411-refactor-s2.md`

### S3：dsl.ast 模块化拆分

#### 阶段目标

- 把 [`kernel_gen/dsl/ast.py`](../../kernel_gen/dsl/ast.py) 拆成“节点定义 + 解析实现 + facade 入口”三层，同时保持旧公开导入方式不变。

#### 当前依据

- [`kernel_gen/dsl/ast.py`](../../kernel_gen/dsl/ast.py) 当前 `3234` 行，混合节点定义与解析逻辑。

#### 目标文件

- `kernel_gen/dsl/ast.py`
- `kernel_gen/dsl/ast_nodes.py`
- `kernel_gen/dsl/ast_parser.py`
- `spec/dsl/ast_nodes.md`
- `spec/dsl/ast_parser.md`
- `kernel_gen/dsl/__init__.py`
- `spec/dsl/ast.md`
- `test/dsl/test_ast_nodes.py`
- `test/dsl/test_ast_parser.py`

#### 预期输出

```text
1) ast.py 只做 facade 与 re-export
2) 节点定义与解析逻辑拆分
3) 旧导入方式保持可用
4) ast_nodes.py / ast_parser.py 各自有对应 spec 与测试
```

#### 验收命令

- `pytest -q test/dsl`
- `python - <<'PY'\nfrom kernel_gen.dsl.ast import parse_function, FunctionAST\nprint(parse_function is not None, FunctionAST is not None)\nPY`

#### 任务新建建议

- `首个任务类型：spec`
- `阶段内续接：build -> review -> merge`
- `任务目标：拆分 dsl.ast 并保持 facade 兼容`
- `记录文件：20260411-refactor-s3.md`

### S4：测试 ownership 审计与最小收口

#### 阶段目标

- 不直接大规模删测例，先把 `operation` / `dialect` / `dsl` 的职责边界审清楚，再做最小调整。

#### 当前依据

- 原草案认为 `operation` 与 `dialect` 测试层次重叠，但当前静态检索没有直接命中“dialect 测试直接调用 operation API”。
- 因此这一步先做证据化审计，再收口最少量改动。

#### 目标文件

- `test/operation/**`
- `test/dialect/**`
- `test/dsl/**`
- `agents/standard/测试文件约定.md`

#### 预期输出

```text
1) 输出一张 operation / dialect / dsl 测试职责表
2) 明确哪些测试保留，哪些测试需要迁移或删除
3) 只对已有重叠证据的文件做最小调整
```

#### 验收命令

- `pytest -q test/operation`
- `pytest -q test/dialect`
- `pytest -q test/dsl`

#### 任务新建建议

- `首个任务类型：spec`
- `阶段内续接：build -> review -> merge`
- `任务目标：先审计测试 ownership，再做最小收口`
- `记录文件：20260411-refactor-s4.md`

### S5：总回归与结构说明收口

#### 阶段目标

- 把前四段改动的结构说明与验收命令收口到统一文档里，并完成一次总回归。

#### 目标文件

- `pyproject.toml`
- `agents/standard/测试文件约定.md`
- `spec/dsl/ast.md`
- `kernel_gen/common/**`
- `kernel_gen/symbol_variable/dtype_constants.py`
- `kernel_gen/dsl/ast*.py`

#### 预期输出

```text
1) pytest 配置、公共错误模块、dtype 常量、ast facade 四块说明一致
2) 前面阶段的验收命令能完整跑通
3) 不再保留本轮已裁掉的历史大任务描述
```

#### 验收命令

- `pytest -m "not infra"`
- `pytest -m infra`
- `pytest -q test/dsl`
- `pytest -q test/operation`
- `pytest -q test/dialect`
- `rg "_ERROR_TEMPLATE\\s*=" kernel_gen`
- `rg "_FLOAT_DTYPES\\s*=" kernel_gen`
- `rg "_INT_DTYPES\\s*=" kernel_gen`

#### 任务新建建议

- `首个任务类型：spec`
- `阶段内续接：build -> review -> merge`
- `任务目标：完成总回归并收口结构说明`
- `记录文件：20260411-refactor-s5.md`
