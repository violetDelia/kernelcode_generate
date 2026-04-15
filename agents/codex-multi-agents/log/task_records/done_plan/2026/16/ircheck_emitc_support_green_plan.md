# ircheck_emitc_support_green_plan.md

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`大闸蟹`
- 目标 `spec`：
  - [`spec/tools/ircheck.md`](../../spec/tools/ircheck.md)
  - [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
  - [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md)
- 目标 `API`：
  - [`kernel_gen/tools/ircheck.py`](../../kernel_gen/tools/ircheck.py)
- 目标 `test`：
  - [`test/tools/test_ircheck_cli.py`](../../test/tools/test_ircheck_cli.py)
  - [`test/tools/test_ircheck_runner.py`](../../test/tools/test_ircheck_runner.py)
- 目标 `验收资产`：
  - [`expectation/tools/ircheck/emitc_true.py`](../../expectation/tools/ircheck/emitc_true.py)
  - [`expectation/tools/ircheck/emitc_false.py`](../../expectation/tools/ircheck/emitc_false.py)
- 目标 `功能实现`：
  - [`kernel_gen/tools/ircheck.py`](../../kernel_gen/tools/ircheck.py)

## 任务清单

> 前置依赖：本计划允许先建任务。原文中的 `T-20260414-8f7b8aaa` 后续已被前置计划判定为重复占位 merge，不再作为有效依赖；当前唯一有效前置依赖改为已完成的 `T-20260414-530a146a`。因此本计划 `S1 -> S5` 全链可直接按 `T-20260414-530a146a` 已完成处理继续推进，无需另补一条依赖链。

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `S1` | `T-20260414-530a146a（已完成）` | `wt-20260414-ircheck-emitc-s1` | `20260414-ircheck-emitc-s1.md` |
| `S2` | `S1` | `wt-20260414-ircheck-emitc-s2` | `20260414-ircheck-emitc-s2.md` |
| `S3` | `S2` | `wt-20260414-ircheck-emitc-s3` | `20260414-ircheck-emitc-s3.md` |
| `S4` | `S3` | `wt-20260414-ircheck-emitc-s4` | `20260414-ircheck-emitc-s4.md` |
| `S5` | `S4` | `wt-20260414-ircheck-emitc-s5` | `20260414-ircheck-emitc-s5.md` |

## 前置依赖更正（2026-04-15 09:34 +0800）

- 更正人：`大闸蟹`
- 更正摘要：
  - 原计划引用的 `T-20260414-8f7b8aaa` 来自前置计划早期的重复占位 merge，后续已被删除，不再作为有效依赖。
  - 当前唯一有效前置依赖为已完成的 `T-20260414-530a146a`。
  - 由于 `T-20260414-530a146a` 已完成，本计划 `S1` 现在可以直接启动；管理员无需先补一条新的依赖链，只需在实际分发前把 `TODO.md` 中 `T-20260414-75a48c70` 的依赖字段改挂到 `T-20260414-530a146a`，或按“依赖已满足”处理即可。

## 前置依赖补充（2026-04-14 13:50 +0800）

- 按当前用户口径，本计划允许先建任务，但 `S1` 必须显式依赖前置计划最后一个任务 [`T-20260414-8f7b8aaa`](../../TODO.md)。
- 管理侧可提前把 `S1 -> S5` 任务建入 `TODO.md`，但在 [`T-20260414-8f7b8aaa`](../../TODO.md) 完成前，不得分发本计划任何任务。
- 本补充只调整“建任务时机”和依赖表达；`emitc` 计划的实现、review、merge 仍不得早于前置链完成。

## 评审摘要

- 评审结论：`通过`
- 评审人：`守护最好的爱莉希雅`、`大闸蟹`
- 结论摘要：`前置依赖口径已写清，emitc expectation 资产也已收口为“保留 ignored expectation 路径、merge 阶段 git add -f 纳入交付、不得修改 .gitignore”的唯一合同，计划可按 T-20260414-8f7b8aaa 依赖建任务。`

## 互评补充（2026-04-14 14:10 +0800）

- 互评人：`守护最好的爱莉希雅`
- 互评结论：`暂不通过`
- 已确认可保留项：
  - 前置依赖口径已写清：允许先建任务，但 `S1` 显式依赖 [`T-20260414-8f7b8aaa`](../../TODO.md)，且该任务完成前管理员不得分发本计划任何任务；这一点可直接沿用。
  - `emitc` 公开合同主线清楚：`emitc_target` 仅在 compile steps 后切到源码匹配，默认 IR 路径不回退，成功/失败前缀与 `actual_ir` 语义均已写明。
- 最小阻断项：
  - expectation 资产交付口径未闭环。计划把 [`expectation/tools/ircheck/emitc_true.py`](../../expectation/tools/ircheck/emitc_true.py) 与 [`expectation/tools/ircheck/emitc_false.py`](../../expectation/tools/ircheck/emitc_false.py) 列为目标验收资产，但当前仓库 `.gitignore` 第 17 行是 `/expectation/`，且这两份文件当前未被主仓跟踪。若继续按现稿建任务，执行人与 merge 角色无法从计划中直接判断：是继续使用该 ignored 路径并在合并阶段强制 `git add -f`，还是改到其它可跟踪载体；这样“emitc 合同与 expectation 资产闭环”仍未成立。
- 建议修订：
  - 二选一写清唯一口径：
    - 继续使用 `expectation/tools/ircheck/emitc_true.py` 与 `emitc_false.py` 作为稳定资产，并在计划书中显式写明：它们位于 ignored expectation 路径，merge 阶段必须按既有先例使用 `git add -f` 纳入交付；
    - 或改为其它可跟踪载体，并同步更新文档信息、完成态与验收命令。
  - 若保留当前 expectation 路径，建议在 `S1` 与 `S5` 的验收或任务提示中补一句“不得自行改动 `.gitignore`，仅按计划口径处理 ignored expectation 资产”，避免执行人再次猜测。

## 修订记录（2026-04-14 13:55 +0800）

- 修订人：`大闸蟹`
- 修订摘要：
  - 保留 [`expectation/tools/ircheck/emitc_true.py`](../../expectation/tools/ircheck/emitc_true.py) 与 [`expectation/tools/ircheck/emitc_false.py`](../../expectation/tools/ircheck/emitc_false.py) 作为唯一 expectation 合同资产，不迁移到其它载体。
  - 在“当前基线 / 方案选型 / 完成态定义 / S1 / S5”中统一写清：两份 expectation 位于 ignored `expectation/` 路径，merge 阶段必须使用 `git add -f` 纳入最终交付，且不得修改 `.gitignore`。
  - 将 `S5` 任务目标补齐为“按 `git add -f` 纳入 expectation 资产并完成终验”，避免执行与合并角色继续猜测交付方式。

## 复核结论（2026-04-14 14:18 +0800）

- 复核人：`守护最好的爱莉希雅`
- 复核结论：`通过`
- 复核摘要：
  - 前置依赖口径已闭环：允许先建任务，但 `S1` 显式依赖 [`T-20260414-8f7b8aaa`](../../TODO.md)，且该任务完成前管理员不得分发本计划任何任务。
  - emitc expectation 资产交付口径已闭环：继续保留 [`expectation/tools/ircheck/emitc_true.py`](../../expectation/tools/ircheck/emitc_true.py) 与 [`expectation/tools/ircheck/emitc_false.py`](../../expectation/tools/ircheck/emitc_false.py) 作为合同资产，不迁移载体；merge 阶段必须按计划使用 `git add -f expectation/tools/ircheck/emitc_true.py expectation/tools/ircheck/emitc_false.py` 纳入交付，且不得修改 `.gitignore`。
  - 当前计划可直接沿用既有阶段拆分与验收命令，按依赖建任务。

## 终验结论（2026-04-15 09:00 +0800）

- 终验人：`守护最好的爱莉希雅`
- 终验结论：`通过`
- 终验摘要：
  - 当前主仓提交已到 `9ffaac7`，对应本计划最后一段 merge 已完成，管理员已确认 `T-20260414-e3a0db84` 完成并 `-done`。
  - 终验命令复核通过：
    - `pytest -q test/tools/test_ircheck_runner.py -k emitc` -> `6 passed`
    - `pytest -q test/tools/test_ircheck_cli.py -k emitc` -> `5 passed`
    - `PYTHONPATH=. python expectation/tools/ircheck/emitc_true.py` -> `exit 0`
    - `PYTHONPATH=. python expectation/tools/ircheck/emitc_false.py` -> `exit 0`
  - 主仓已存在 [`expectation/tools/ircheck/emitc_true.py`](../../expectation/tools/ircheck/emitc_true.py) 与 [`expectation/tools/ircheck/emitc_false.py`](../../expectation/tools/ircheck/emitc_false.py) 两份合同资产；`emitc_target` API、CLI `-emitc{target=...}` 与 expectation 交付口径已按计划收口。
  - 结论：[`ARCHITECTURE/plan/ircheck_emitc_support_green_plan.md`](../../ARCHITECTURE/plan/ircheck_emitc_support_green_plan.md) 当前满足完成态与验收设计，可进入归档链。

## 计划目标

- 为 `ircheck` 新增 `-emitc{target=<target>}` 模式，在正常执行 `COMPILE_ARGS` 后，把最终 IR 转为目标 C/C++ 源码并对源码执行 `CHECK*` 匹配。
- 公开 `run_ircheck_file(...)` / `run_ircheck_text(...)` 的 `emitc_target` 可选参数，使 CLI 与 Python API 使用同一条 emitc 执行链。
- 预先冻结成功/失败 expectation 合同，避免执行者在 `emitc` 目标、错误前缀、匹配对象与默认回退行为上自行补假设。
- 默认路径保持不变：未启用 `emitc_target` 时，`ircheck` 仍只匹配规范化 IR 文本。

## 当前基线

- 当前 CLI 仅支持：
  - `python -m kernel_gen.tools.ircheck <case-file>`
  - `python -m kernel_gen.tools.ircheck -irdump <case-file>`
- 当前公开 API 为：
  - `run_ircheck_file(path: str, *, irdump: bool = False) -> IrcheckResult`
  - `run_ircheck_text(text: str, source_path: str | None = None) -> IrcheckResult`
- 当前 `_run_ircheck_case(...)` 的匹配对象固定为 pass / pipeline 之后的规范化 IR 文本，不支持源码生成分支。
- 当前 [`kernel_gen/tools/ircheck.py`](../../kernel_gen/tools/ircheck.py) 未导入 [`kernel_gen.dsl.gen_kernel`](../../kernel_gen/dsl/gen_kernel.py) 或 [`kernel_gen.dsl.emit_c`](../../kernel_gen/dsl/emit_c.py)。
- 当前 [`kernel_gen.dsl.gen_kernel`](../../kernel_gen/dsl/gen_kernel.py) 已冻结两类稳定 target：
  - `cpu`：允许普通 `func.func` 生成单函数源码；
  - `npu_demo`：只允许受控 `builtin.module` 子集，要求 body + wrapper 双函数源码。
- 当前 [`expectation/tools/ircheck/emitc_true.py`](../../expectation/tools/ircheck/emitc_true.py) 与 [`expectation/tools/ircheck/emitc_false.py`](../../expectation/tools/ircheck/emitc_false.py) 已作为本地合同资产存在，但因仓库 `.gitignore` 含 `/expectation/`，它们当前尚未被主仓跟踪；若计划不显式写清交付方式，执行与 merge 环节仍会在“是否允许继续使用 expectation 路径”上产生歧义。
- 当前 [`ARCHITECTURE/plan/ircheck_regex_variable_support_green_plan.md`](../../ARCHITECTURE/plan/ircheck_regex_variable_support_green_plan.md) 仍在进行中；`ircheck` 接口面仍在变化，因此本计划即使先建任务，也只能在 [`T-20260414-8f7b8aaa`](../../TODO.md) 完成后再进入实际分发。

## 方案比较与选型

- 不采用方案：直接在 `emitc` 模式下调用节点级 [`emit_c_op`](../../kernel_gen/dsl/emit_c.py) 拼接源码片段。
  - 原因：会把函数签名、返回值和 target 特化重新散落回 `ircheck`，与 [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md) 的函数级合同冲突。
- 不采用方案：新增独立 CLI 工具处理 `emitc check`，不复用 `ircheck`。
  - 原因：会把 `COMPILE_ARGS`、`CHECK*`、`-irdump` 和多 case 语义复制一遍，维护成本高。
- 不采用方案：启用 `emitc` 时仍同时兼容“匹配 IR 文本”和“匹配生成源码”两套目标。
  - 原因：执行与验收口径会分叉，expectation 无法冻结唯一合同。
- 采用方案：
  - `ircheck` 新增可选 `emitc_target`；
  - 只有在 `emitc_target` 非空时，才在 compile steps 完成后调用 [`gen_kernel(...)`](../../kernel_gen/dsl/gen_kernel.py)；
  - `emitc` 模式下 `IrcheckResult.actual_ir` 复用为“生成的源码文本”，并把 `CHECK*` 匹配对象切换为该源码；
  - 生成失败统一映射为 `IrcheckEmitCError: emit_c generation failed` 前缀；
  - expectation 合同资产继续保留在 [`expectation/tools/ircheck`](../../expectation/tools/ircheck) 路径，不迁移到其它载体；
  - 因该路径受 `.gitignore` 影响，merge 阶段必须按既有 expectation 先例使用 `git add -f expectation/tools/ircheck/emitc_true.py expectation/tools/ircheck/emitc_false.py` 纳入交付，且不得修改 `.gitignore`；
  - 默认路径不保留任何“自动回退到 IR 匹配”的兼容分支。

## 公开 API 设计

### CLI

- 新入口形式：
  - `PYTHONPATH=. python -m kernel_gen.tools.ircheck -emitc{target=cpu} case.ircheck`
  - `PYTHONPATH=. python -m kernel_gen.tools.ircheck -irdump -emitc{target=cpu} case.ircheck`
- 参数约束：
  - `target` 当前只接受 `cpu`、`npu_demo`
  - `-emitc` 缺少 `{target=...}`、`target` 为空、或缺少 case 文件路径时，统一视为 CLI 参数非法
- CLI 非法参数固定错误前缀：
  - `IrcheckCliError: invalid arguments`

### Python API

- `run_ircheck_file(path: str, *, irdump: bool = False, emitc_target: str | None = None) -> IrcheckResult`
- `run_ircheck_text(text: str, source_path: str | None = None, emitc_target: str | None = None) -> IrcheckResult`
- 参数语义：
  - `emitc_target is None`：沿用现有 IR 匹配路径
  - `emitc_target == "cpu"`：compile steps 后对最终 `func.func` 生成 CPU 源码，并对源码执行 `CHECK*`
  - `emitc_target == "npu_demo"`：compile steps 后只接受受控 module 子集；若输入不是双函数 module，返回 `IrcheckEmitCError`
- 返回语义：
  - `emitc` 成功时：`actual_ir` 返回生成的源码文本
  - `emitc` 失败时：`ok=False`、`exit_code=2`、`message` 以前缀 `IrcheckEmitCError: emit_c generation failed` 开头

### 最小示例

```python
from kernel_gen.tools.ircheck import run_ircheck_text

case_text = """// COMPILE_ARGS: --pass no-op
// CHECK: void main()
// CHECK-NEXT: }

builtin.module {
  func.func @main() {
    func.return
  }
}
"""

result = run_ircheck_text(
    case_text,
    source_path="inline_emitc.ircheck",
    emitc_target="cpu",
)
assert result.ok is True
assert result.actual_ir == "void main() {\n}"
```

## 完成态定义

- [`kernel_gen/tools/ircheck.py`](../../kernel_gen/tools/ircheck.py) 支持 `emitc_target` 可选参数与 `-emitc{target=<target>}` CLI 入口。
- `emitc` 模式下，`CHECK*` 匹配对象唯一切换为生成源码；默认模式继续匹配规范化 IR，不新增双路径兼容。
- `emitc` 成功/失败 expectation 资产可独立运行并通过：
  - [`expectation/tools/ircheck/emitc_true.py`](../../expectation/tools/ircheck/emitc_true.py)
  - [`expectation/tools/ircheck/emitc_false.py`](../../expectation/tools/ircheck/emitc_false.py)
- 上述 expectation 资产虽位于 ignored 路径，但已在 merge 阶段按 `git add -f` 纳入最终交付；`.gitignore` 保持不变。
- `test/tools/test_ircheck_cli.py` 与 `test/tools/test_ircheck_runner.py` 已补齐 emitc 相关回归。
- 本计划的实现、审查、合并链路都发生在 [`T-20260414-8f7b8aaa`](../../TODO.md) 完成之后，不与前置链并发。

## 验收设计

- 验收资产：
  - [`expectation/tools/ircheck/emitc_true.py`](../../expectation/tools/ircheck/emitc_true.py)
  - [`expectation/tools/ircheck/emitc_false.py`](../../expectation/tools/ircheck/emitc_false.py)
- 输入样例：
  - `cpu` 成功链：单个空 `func.func @main`，经 `--pass no-op` 后生成 `void main() { ... }`
  - `npu_demo` 失败链：单个普通 `func.func` 直接请求 `emitc_target="npu_demo"`，必须失败，不得静默退化为 body-only 输出
- 锁定输出：
  - 成功链至少包含 `void main() {`
  - 失败链错误前缀固定为 `IrcheckEmitCError: emit_c generation failed`
  - 非法 CLI 参数错误前缀固定为 `IrcheckCliError: invalid arguments`
- 必过命令：
  - `pytest -q test/tools/test_ircheck_runner.py -k emitc`
  - `pytest -q test/tools/test_ircheck_cli.py -k emitc`
  - `PYTHONPATH=. python expectation/tools/ircheck/emitc_true.py`
  - `PYTHONPATH=. python expectation/tools/ircheck/emitc_false.py`

## 阶段拆分

### S1：spec 与 expectation 合同冻结

#### 阶段目标

- 冻结 `emitc` 的公开参数、错误前缀、匹配对象与 expectation 资产；后续 build 只按合同落实现，不再回改合同边界。
- 明确 ignored `expectation` 资产的唯一合法交付方式：保留当前路径，由 merge 阶段 `git add -f` 纳入最终交付，不修改 `.gitignore`。

#### 目标 spec / API

- `spec/tools/ircheck.md`
- `公开 API：run_ircheck_file / run_ircheck_text / CLI -emitc{target=<target>}`

#### 可改文件

- `spec/tools/ircheck.md`
- `expectation/tools/ircheck/emitc_true.py`
- `expectation/tools/ircheck/emitc_false.py`

#### 预期示例代码

```text
// CHECK: void main()
// CHECK-NEXT: }
```

#### 预期输出

```text
void main() {
}
```

#### 目标验收资产

- `expectation/tools/ircheck/emitc_true.py`
- `expectation/tools/ircheck/emitc_false.py`

#### 验收必过项目

- 文本核对：`spec/tools/ircheck.md` 已写清 `emitc_target`、CLI `-emitc{target=...}`、错误前缀与 `actual_ir` 语义
- 文本核对：计划书已写清 `expectation/tools/ircheck/emitc_true.py` / `emitc_false.py` 保留当前路径、merge 阶段必须 `git add -f`、且不得改 `.gitignore`
- `PYTHONPATH=. python expectation/tools/ircheck/emitc_true.py`
- `PYTHONPATH=. python expectation/tools/ircheck/emitc_false.py`

#### 任务新建建议

- `任务类型：spec`
- `任务目标：冻结 ircheck emitc 公开合同与 expectation 资产`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260414-ircheck-emitc-s1.md`

### S2：API emitc 分支与 runner 收口

#### 阶段目标

- 在 Python API 与内部执行链上接通 `emitc_target`，并用 runner 测试收口成功/失败路径。

#### 目标 spec / API

- `spec/tools/ircheck.md`
- `公开 API：run_ircheck_file / run_ircheck_text`

#### 可改文件

- `kernel_gen/tools/ircheck.py`
- `test/tools/test_ircheck_runner.py`

#### 不可改范围

- `expectation/tools/ircheck/emitc_true.py`
- `expectation/tools/ircheck/emitc_false.py`

#### 预期示例代码

```python
result = run_ircheck_text(case_text, source_path="inline_emitc.ircheck", emitc_target="cpu")
assert result.ok is True
assert result.actual_ir.startswith("void main()")
```

#### 预期输出

```text
IrcheckEmitCError: emit_c generation failed
```

#### 目标验收资产

- `test/tools/test_ircheck_runner.py`
- `expectation/tools/ircheck/emitc_true.py`
- `expectation/tools/ircheck/emitc_false.py`

#### 验收必过项目

- `pytest -q test/tools/test_ircheck_runner.py -k emitc`
- `PYTHONPATH=. python expectation/tools/ircheck/emitc_true.py`
- `PYTHONPATH=. python expectation/tools/ircheck/emitc_false.py`

#### 任务新建建议

- `任务类型：build`
- `任务目标：实现 emitc_target API 分支并收口 runner 回归`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260414-ircheck-emitc-s2.md`

### S3：CLI 选项与集成回归

#### 阶段目标

- 让 CLI 支持 `-emitc{target=<target>}` 与 `-irdump` 组合，并补齐 CLI 正反向回归。

#### 目标 spec / API

- `spec/tools/ircheck.md`
- `公开 API：CLI -emitc{target=<target>}`

#### 可改文件

- `kernel_gen/tools/ircheck.py`
- `test/tools/test_ircheck_cli.py`

#### 不可改范围

- `expectation/tools/ircheck/emitc_true.py`
- `expectation/tools/ircheck/emitc_false.py`

#### 预期示例代码

```text
PYTHONPATH=. python -m kernel_gen.tools.ircheck -emitc{target=cpu} case.ircheck
PYTHONPATH=. python -m kernel_gen.tools.ircheck -irdump -emitc{target=cpu} case.ircheck
```

#### 预期输出

```text
true
```

#### 目标验收资产

- `test/tools/test_ircheck_cli.py`
- `expectation/tools/ircheck/emitc_true.py`
- `expectation/tools/ircheck/emitc_false.py`

#### 验收必过项目

- `pytest -q test/tools/test_ircheck_cli.py -k emitc`
- `PYTHONPATH=. python expectation/tools/ircheck/emitc_true.py`
- `PYTHONPATH=. python expectation/tools/ircheck/emitc_false.py`

#### 任务新建建议

- `任务类型：build`
- `任务目标：实现 ircheck emitc CLI 并收口集成回归`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260414-ircheck-emitc-s3.md`

### S4：review

#### 阶段目标

- review emitc 合同、API 与 CLI 回归是否与 expectation 一致。

#### 验收必过项目

- `pytest -q test/tools/test_ircheck_runner.py -k emitc`
- `pytest -q test/tools/test_ircheck_cli.py -k emitc`
- `PYTHONPATH=. python expectation/tools/ircheck/emitc_true.py`
- `PYTHONPATH=. python expectation/tools/ircheck/emitc_false.py`

#### 任务新建建议

- `任务类型：review`
- `任务目标：review ircheck emitc 合同与回归收口`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260414-ircheck-emitc-s4.md`

### S5：merge

#### 阶段目标

- 合并 emitc 改动并完成最终验收。
- 按计划口径把 ignored expectation 资产纳入交付，不修改 `.gitignore`。

#### 验收必过项目

- `pytest -q test/tools/test_ircheck_runner.py -k emitc`
- `pytest -q test/tools/test_ircheck_cli.py -k emitc`
- `PYTHONPATH=. python expectation/tools/ircheck/emitc_true.py`
- `PYTHONPATH=. python expectation/tools/ircheck/emitc_false.py`
- 合并清单包含：`git add -f expectation/tools/ircheck/emitc_true.py expectation/tools/ircheck/emitc_false.py`

#### 任务新建建议

- `任务类型：merge`
- `任务目标：合并 ircheck emitc 支持、按 git add -f 纳入 expectation 资产并完成终验`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260414-ircheck-emitc-s5.md`

## 终验结论（2026-04-15 09:01 +0800）

- 终验人：`大闸蟹`
- 终验结论：`通过`
- 终验依据：
  - 文本复核 [`spec/tools/ircheck.md`](../../spec/tools/ircheck.md)，已写清 `emitc_target`、CLI `-emitc{target=<target>}`、`IrcheckEmitCError` / `IrcheckCliError` 前缀，以及 merge 阶段 `git add -f expectation/tools/ircheck/emitc_true.py expectation/tools/ircheck/emitc_false.py` 的交付口径。
  - 文本复核 [`kernel_gen/tools/ircheck.py`](../../kernel_gen/tools/ircheck.py)，公开接口已收口为 `run_ircheck_file(..., emitc_target=...)`、`run_ircheck_text(..., emitc_target=...)`，CLI `main(...)` 已接入 `-emitc{target=...}`。
  - 主仓终验复跑通过：
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_ircheck_runner.py -k emitc` -> `6 passed, 28 deselected`
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_ircheck_cli.py -k emitc` -> `5 passed, 3 deselected`
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/tools/ircheck/emitc_true.py` -> `exit=0`
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/tools/ircheck/emitc_false.py` -> `exit=0`
  - 仓库当前 `.gitignore` 仍保留 `/expectation/`，且 `expectation/tools/ircheck/emitc_true.py`、`expectation/tools/ircheck/emitc_false.py` 已在当前仓库交付内容中存在，符合本计划“保留 ignored 路径、不改 .gitignore、由 merge 纳入交付”的合同。
- 结论摘要：
  - 本计划要求的公开合同、实现入口、测试回归与 expectation 资产均已闭环，当前可按归档规则继续推进。

## 归档记录

时间：2026-04-15 12:23 +0800
经办人：李白
任务：T-20260415-c13744bb
任务目标：将 `ARCHITECTURE/plan/ircheck_emitc_support_green_plan.md` 归档到 `agents/codex-multi-agents/log/task_records/done_plan/2026/16/ircheck_emitc_support_green_plan.md`，并完成归档 merge 收口。
改动：
- 管理员指定的 `worktree=/home/lfr/kernelcode_generate/wt-20260415-archive-ircheck-emitc-plan` 缺失，已按当前协作口径补建任务分支 `T-20260415-c13744bb` 与对应 `worktree`，基线直接对齐最新 `origin/main@b8adf9e`。
- 核对发现 `ARCHITECTURE/plan/ircheck_emitc_support_green_plan.md` 当前为主仓本地忽略文件，不在远端主线版本树中；因此在任务 `worktree` 内将该计划书内容复制到归档目标文件 `agents/codex-multi-agents/log/task_records/done_plan/2026/16/ircheck_emitc_support_green_plan.md`，并在同一文件尾部追加本次归档记录。
- 本轮归档提交范围限定为：新增归档目标文件；主仓本地源计划书文件将在提交前按用户要求删除，不修改 `.gitignore`，也不扩展到其它文件。
验证：
- `git -C /home/lfr/kernelcode_generate worktree add -b T-20260415-c13744bb /home/lfr/kernelcode_generate/wt-20260415-archive-ircheck-emitc-plan origin/main`：成功补建任务 `worktree`，基线为 `b8adf9e`。
- `git -C /home/lfr/kernelcode_generate/wt-20260415-archive-ircheck-emitc-plan rev-list --left-right --count HEAD...origin/main` -> `0 0`
- `git -C /home/lfr/kernelcode_generate ls-tree -r --name-only origin/main -- 'ARCHITECTURE/plan/ircheck_emitc_support_green_plan.md' 'agents/codex-multi-agents/log/task_records/done_plan/2026/16/ircheck_emitc_support_green_plan.md'`：无输出，确认远端主线当前既无源计划书，也无归档目标文件。
- `git -C /home/lfr/kernelcode_generate check-ignore -v ARCHITECTURE/plan/ircheck_emitc_support_green_plan.md` -> `.gitignore:21:ARCHITECTURE/plan/`
- `git -C /home/lfr/kernelcode_generate/wt-20260415-archive-ircheck-emitc-plan status --short --branch` -> 仅 `?? agents/codex-multi-agents/log/task_records/done_plan/2026/16/ircheck_emitc_support_green_plan.md`
结论：归档前日志已补齐；下一步删除主仓本地源计划书，并在当前 `worktree` 内提交归档文件、推送远端主分支，然后执行当前 merge 任务 `-done` 并用 `-talk` 回报管理员继续 `-done-plan`。
