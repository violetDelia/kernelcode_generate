# ircheck_pass_option_support_green_plan.md

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`守护最好的爱莉希雅`
- 目标 `spec`：
  - [`spec/tools/ircheck.md`](../../spec/tools/ircheck.md)
  - [`spec/pass/registry.md`](../../spec/pass/registry.md)
  - [`spec/pass/lowering/tile.md`](../../spec/pass/lowering/tile.md)
- 目标 `API`：
  - [`kernel_gen/tools/ircheck.py`](../../kernel_gen/tools/ircheck.py)
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
  - [`kernel_gen/passes/lowering/tile.py`](../../kernel_gen/passes/lowering/tile.py)
- 目标 `test`：
  - [`test/tools/test_ircheck_runner.py`](../../test/tools/test_ircheck_runner.py)
  - [`test/pass/test_pass_registry.py`](../../test/pass/test_pass_registry.py)
  - [`test/pass/test_lowering_tile.py`](../../test/pass/test_lowering_tile.py)
- 目标 `功能实现`：
  - [`kernel_gen/tools/ircheck.py`](../../kernel_gen/tools/ircheck.py)
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
  - [`kernel_gen/passes/lowering/tile.py`](../../kernel_gen/passes/lowering/tile.py)

## 任务清单

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| `S1` | `无` | `wt-20260412-ircheck-pass-opt-s1` | `20260412-ircheck-pass-opt-s1.md` |
| `S2` | `S1` | `wt-20260412-ircheck-pass-opt-s2` | `20260412-ircheck-pass-opt-s2.md` |
| `S3` | `S2` | `wt-20260412-ircheck-pass-opt-s3` | `20260412-ircheck-pass-opt-s3.md` |
| `S4` | `S3` | `wt-20260412-ircheck-pass-opt-s4` | `20260412-ircheck-pass-opt-s4.md` |
| `S5` | `S4` | `wt-20260413-ircheck-pass-opt-s5` | `20260413-ircheck-pass-opt-s5.md` |
| `S6` | `S5` | `wt-20260413-ircheck-pass-opt-s6` | `20260413-ircheck-pass-opt-s6.md` |

## 评审摘要

- 评审结论：`通过`
- 评审人：`大闸蟹`、`守护最好的爱莉希雅`
- 结论摘要：`计划目标清晰，已固定 pass / pipeline 多 option 的唯一公开写法；继续采用 name + options 方案，不再拆第二套语法；S1 -> S4 依赖顺序合理；S4 以 test 黑盒用例收口 tile 与 pipeline 多 option 的公开行为；kernel_split 仅保留迁移参考，不再作为正式合同入口。`

## 当前验收补充（2026-04-13）

- `验收结论`：`不通过`
- `阻断项`：
  - `pytest -q test/tools/test_ircheck_runner.py test/pass/test_pass_registry.py test/pass/test_lowering_tile.py test/pass/test_pipeline_default_lowering.py` 当前为 `1 failed, 46 passed`
  - 唯一剩余失败为 `test_load_builtin_passes_is_idempotent`
  - 当前 `load_builtin_passes()` 连续执行两次后，`list_registered_pipelines()` 中仍缺少 `default-lowering`
  - 因此 `default-lowering` 的重复导入/重复注册路径还没有按计划收口
- `后续收口任务`：
  - `S6` 依赖 pass/pipeline 注册计划的后续修复结果
  - 本阶段只复核并补齐 `ircheck` 对 `default-lowering` 多 option 的最终公开行为，不重复扩写 pass/pipeline 主体逻辑

## 最终验收补充（2026-04-13 22:39）

- `最终验收结论`：`通过`
- `验收人`：`守护最好的爱莉希雅`
- `验证结果`：
  - `pytest -q test/tools/test_ircheck_runner.py test/pass/test_pass_registry.py test/pass/test_lowering_tile.py test/pass/test_pipeline_default_lowering.py` => `48 passed`
  - `pytest -q test/tools/test_ircheck_runner.py` => `20 passed`
  - `pytest -q test/pass/test_pass_registry.py` => `15 passed`
  - `pytest -q test/pass/test_lowering_tile.py` => `11 passed`
  - `pytest -q test/pass/test_pipeline_default_lowering.py` => `2 passed`
- `结论摘要`：
  - `load_builtin_passes()` 的幂等注册问题已收口，`default-lowering` 在重复加载后可稳定出现在 registry 中
  - 本计划书定义的 pass / pipeline option 语法、注册层构造入口与 `tile` / `default-lowering` 黑盒回归均已满足完成态
  - 当前无需再补建修复任务；可由管理员按计划书归档流程继续推进

## 当前复核补充（2026-04-14 05:07）

- `复核结论`：`通过`；与上述最终验收结论一致，无需补建修复任务
- `验证结果`：
  - `pytest -q test/tools/test_ircheck_runner.py test/pass/test_pass_registry.py test/pass/test_lowering_tile.py test/pass/test_pipeline_default_lowering.py` => `48 passed`
- `大闸蟹复核（2026-04-13 22:41）`：
  - 复跑 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_ircheck_runner.py` => `20 passed`
  - 复跑 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_pass_registry.py` => `15 passed`
  - 复跑 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_lowering_tile.py` => `11 passed`
  - 复跑 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/pass/test_pipeline_default_lowering.py` => `2 passed`
  - 复核结论：`通过`；与上述最终验收结论一致，无需补建修复任务

## 计划目标

- 让 `ircheck` 支持带 pass / pipeline 选项的 `COMPILE_ARGS` 写法。
- 本轮唯一公开写法固定为：
  - `--pass "pass_name={analysis-only=true}"`
  - `--pass "pass_name={k1=v1,k2=v2}"`
  - `--pipeline "pipeline_name={k1=v1,k2=v2}"`
- `ircheck` 只负责把 `name` 与 `{k=v}` 拆出来，再交给 pass / pipeline 注册层；不在工具层内置某个 pass 或 pipeline 的业务判断。
- 第一版要求：
  - `tile` 的 `analysis-only=true|false` 路径收口清楚；
  - pass / pipeline 两侧都支持多个 option；
  - 尚未定义业务语义的 pipeline option 也要能被统一解析，并由对应 pipeline 明确接受或拒绝。
- 验证口径：
  - 执行人不改 `expectation`；
  - `S1` ~ `S4` 全部以 `pytest` 与 test 黑盒用例为主；
  - 每个阶段都要明确“测试要测什么”，而不是只写 expectation 文件路径。

## 当前基线

- 现在 `ircheck` 只接受两段 `COMPILE_ARGS`：
  - `--pass <name>`
  - `--pipeline <name>`
- 现在第二段如果写成 `tile={analysis-only=true}` 或 `default-lowering={k=v}`，会整体被视为名字，最后在注册表报：
  - `PassRegistryError: unknown pass 'tile={analysis-only=true}'`
- 当前 pass 注册层只支持“按名字无参构造”：
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py) 中的 [`build_registered_pass`](../../kernel_gen/passes/registry.py) 只做 `pass_cls()`
- 当前 pipeline 注册层也只支持“按名字无参构造”：
  - [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py) 中的 `build_registered_pipeline(...)` 只做 `builder()`
- 当前 `tile` 也没有公开的 `analysis-only` 构造入口：
  - [`kernel_gen/passes/lowering/tile.py`](../../kernel_gen/passes/lowering/tile.py)

## 方案比较与选型

- 不采用方案：`--pass tile --pass-option analysis-only=true`
- 不采用原因：会把 `COMPILE_ARGS` 扩成多段语法，现有 `ircheck`、样例和文档都要一起变宽，第一版没有必要。

- 不采用方案：`--pass tile={analysis-only=true}`（不加引号）
- 不采用原因：虽然 shell 大多能传过去，但计划书与样例里显式加引号更清楚，避免后续出现空格、逗号时歧义变大。

- 不采用方案：工具层直接识别 `tile` 并手写 `analysis-only` 分支
- 不采用原因：这样会把 pass 语义塞进工具层，后面每加一个带选项 pass 都要继续改 `ircheck`。

- 采用方案：
  1. `ircheck` 把 `--pass "tile={analysis-only=true}"` 解析为：
     - `kind="pass"`
     - `name="tile"`
     - `options={"analysis-only": "true"}`
  2. `ircheck` 把 `--pipeline "default-lowering={k1=v1,k2=v2}"` 解析为：
     - `kind="pipeline"`
     - `name="default-lowering"`
     - `options={"k1": "v1", "k2": "v2"}`
  3. 注册层新增“按名字+选项构造 pass / pipeline”的统一入口。
  4. `tile` 自己决定是否接受 `analysis-only`，其他 pass / pipeline 按各自合同决定接受或拒绝，并返回稳定失败短语。

## 公开 API 设计

### 一、`COMPILE_ARGS` 新写法

- 继续保留：
  - `--pass <pass-name>`
  - `--pipeline <pipeline-name>`
- 新增并固定：
  - `--pass "pass_name={k=v}"`
  - `--pass "pass_name={k1=v1,k2=v2}"`
  - `--pipeline "pipeline_name={k=v}"`
  - `--pipeline "pipeline_name={k1=v1,k2=v2}"`

最小示例：

```text
// COMPILE_ARGS: --pass "tile={analysis-only=true}"
// COMPILE_ARGS: --pipeline "default-lowering={bufferize=true,hoist=false}"
```

### 二、`ircheck` 解析结果

- `ircheck` 内部把第二段拆成：
  - `kind: "pass" | "pipeline"`
  - `name: str`
  - `options: dict[str, str]`
- 选项值第一版全部先按字符串保存。
- 第一版不支持嵌套字典、不支持列表、不支持引号内再套引号。

最小示例：

```python
compile_args = '--pass "tile={analysis-only=true}"'
mode = ("pass", "tile", {"analysis-only": "true"})

compile_args = '--pipeline "default-lowering={bufferize=true,hoist=false}"'
mode = ("pipeline", "default-lowering", {"bufferize": "true", "hoist": "false"})
```

### 三、注册层公开入口

- 建议统一为：
  - `build_registered_pass(name: str, options: dict[str, str] | None = None) -> Pass`
  - `build_registered_pipeline(name: str, options: dict[str, str] | None = None) -> PassManager`

作用：

- `options is None` 或空字典时，沿用现在的无参构造路径。
- `options` 非空时：
  - 若 pass 类声明了公开的 `from_options(cls, options)`，则走该入口。
  - 若没有，则报稳定错误短语，明确该 pass 当前不接受选项。

最小示例：

```python
pass_obj = build_registered_pass("tile", {"analysis-only": "true"})
pm = build_registered_pipeline("default-lowering", {"bufferize": "true", "hoist": "false"})
```

### 四、`tile` 第一版公开选项

- 第一版只支持：
  - `analysis-only=true`
  - `analysis-only=false`
- 语义：
  - `true`：只做前置分析与参数/轴次推导，不插入 `symbol.for` / `dma.view` / 重写后的 `kernel.*`
  - `false`：走现有完整 tile 改写

最小示例：

```text
// COMPILE_ARGS: --pass "tile={analysis-only=true}"
// CHECK: tuner.param
// CHECK-NOT: symbol.for
// CHECK-NOT: dma.view
```

### 五、pipeline 第一版公开选项合同

- `ircheck` 与注册层必须支持 pipeline 多 option 语法。
- 第一版不强行要求现有每个 pipeline 都消费这些选项，但要求行为唯一：
  - 空 option：按当前默认行为构造；
  - 非空 option：
    - 若该 pipeline 已定义公开 option，按公开合同处理；
    - 若该 pipeline 尚未定义公开 option，返回稳定失败短语，不得静默忽略。

最小示例：

```text
// COMPILE_ARGS: --pipeline "default-lowering={bufferize=true,hoist=false}"
```

## 完成态定义

- `ircheck` 能接受：
  - `--pass "tile={analysis-only=true}"`
  - `--pipeline "default-lowering={k1=v1,k2=v2}"`
- 注册层已经有统一的“名字 + 选项”构造入口，不再把 `tile={...}` 或 `default-lowering={...}` 当成完整名字。
- `tile` 明确接受 `analysis-only=true|false`，非法 key / 非法 value / 不支持的带参 pass 都有固定报错短语。
- pipeline 侧支持多个 option；未声明公开 option 的 pipeline 收到非空 option 时返回固定报错短语。
- 现有无参写法继续可用：
  - `--pass tile`
  - `--pipeline default-lowering`
- 验收资产全部内联 IR 到 `.py` 文件中，不新增 `.mlir` 样例文件。

## 验收设计

- 主要验证测试：
  - [`test/tools/test_ircheck_runner.py`](../../test/tools/test_ircheck_runner.py)
  - [`test/pass/test_pass_registry.py`](../../test/pass/test_pass_registry.py)
  - [`test/pass/test_lowering_tile.py`](../../test/pass/test_lowering_tile.py)
  - [`test/pass/test_pipeline_default_lowering.py`](../../test/pass/test_pipeline_default_lowering.py)
- 输入样例：
  - `--pass "tile={analysis-only=true}"`
  - `--pass "tile={analysis-only=false}"`
  - `--pass "tile={analysis-only=maybe}"`
  - `--pass "no-op={analysis-only=true}"`
  - `--pass "tile={analysis-only=true,unknown=false}"`
  - `--pipeline "default-lowering={bufferize=true,hoist=false}"`
  - `--pipeline "default-lowering={unknown=true}"`
- 锁定输出：
  - 能正确拆出 `name` 与多个 `options`
  - `tile analysis-only=true` 只保留分析结果，不进入完整 loop/view 改写
  - pass 侧多 option 语法可以被统一解析；具体 pass 若未声明额外 key，必须返回固定失败短语
  - 无法接受选项的 pass / pipeline 要返回固定失败短语
- 测试要测什么：
  - `test/tools/test_ircheck_runner.py`
    - `--pass "tile={analysis-only=true}"` / `--pass "tile={analysis-only=true,unknown=false}"` / `--pipeline "default-lowering={bufferize=true,hoist=false}"` 的解析与执行结果；
    - 非法 option 文本、未知 key、未知 pass / pipeline 的固定失败短语；
    - 旧写法 `--pass tile` / `--pipeline default-lowering` 不回退。
  - `test/pass/test_pass_registry.py`
    - `build_registered_pass(name, options)` / `build_registered_pipeline(name, options)` 的无参、有参、非法 key 三条路径；
    - 不支持 option 的 pass / pipeline 返回稳定失败短语。
  - `test/pass/test_lowering_tile.py`
    - `analysis-only=true` 仅保留分析结果；
    - `analysis-only=false` 保持完整 tile 改写；
    - `analysis-only=maybe` 返回固定失败短语。
  - `test/pass/test_pipeline_default_lowering.py`
    - `default-lowering` 接受或拒绝多 option 的唯一行为；
    - 传入未声明公开 option 时返回固定失败短语，不得静默忽略。
- 必过命令：
  - `pytest -q test/tools/test_ircheck_runner.py`
  - `pytest -q test/pass/test_pass_registry.py`
  - `pytest -q test/pass/test_lowering_tile.py`
  - `pytest -q test/pass/test_pipeline_default_lowering.py`

## 阶段拆分

### S1：`spec` 与语法收口

#### 阶段目标

- 把 `ircheck` 的 pass / pipeline 选项写法、注册层入口和 `tile analysis-only` 语义写成唯一合同。

#### 目标 spec / API

- [`spec/tools/ircheck.md`](../../spec/tools/ircheck.md)
- [`spec/pass/registry.md`](../../spec/pass/registry.md)
- [`spec/pass/lowering/tile.md`](../../spec/pass/lowering/tile.md)
- 公开 API：
  - `build_registered_pass(name, options=None)`
  - `build_registered_pipeline(name, options=None)`

#### 可改文件

- `spec/tools/ircheck.md`
- `spec/pass/registry.md`
- `spec/pass/lowering/tile.md`

#### 预期示例代码

```text
// COMPILE_ARGS: --pass "tile={analysis-only=true}"
// COMPILE_ARGS: --pass "tile={analysis-only=true,unknown=false}"
// COMPILE_ARGS: --pipeline "default-lowering={bufferize=true,hoist=false}"
```

#### 预期输出

```text
1) 语法唯一：--pass "pass_name={k=v}" / --pipeline "pipeline_name={k=v}"
2) pass / pipeline 都支持多个 option
3) tile 明确接受 analysis-only=true|false；额外 key 固定拒绝
```

#### 目标验收资产

- `spec/tools/ircheck.md`：写清 `COMPILE_ARGS` 新语法
- `spec/pass/registry.md`：写清名字+选项构造接口
- `spec/pass/lowering/tile.md`：写清 `analysis-only` 语义与失败短语

#### 验收必过项目

- `spec/tools/ircheck.md`
- `spec/pass/registry.md`
- `spec/pass/lowering/tile.md`

#### 任务新建建议

- `任务类型：spec`
- `任务目标：收口 ircheck pass 选项语法、注册入口与 tile analysis-only 合同`
- `记录文件：20260412-ircheck-pass-opt-s1.md`

### S2：`ircheck` 与注册层实现

#### 阶段目标

- 让 `ircheck` 能把带 option 的 pass / pipeline 都解析为 `name + options`，并交给注册层构造。

#### 目标 spec / API

- [`kernel_gen/tools/ircheck.py`](../../kernel_gen/tools/ircheck.py)
- [`kernel_gen/passes/registry.py`](../../kernel_gen/passes/registry.py)
- 公开 API：
  - `build_registered_pass(name, options=None)`
  - `build_registered_pipeline(name, options=None)`

#### 可改文件

- `kernel_gen/tools/ircheck.py`
- `kernel_gen/passes/registry.py`
- `test/tools/test_ircheck_runner.py`
- `test/pass/test_pass_registry.py`

#### 预期示例代码

```python
result = run_ircheck_text(
    """// COMPILE_ARGS: --pass "tile={analysis-only=true}"
// CHECK: builtin.module

builtin.module {}
""",
    source_path="inline.ircheck",
)
```

#### 预期输出

```text
1) compile args 可拆为 ("pass"|"pipeline", name, {k: v})
2) 不支持选项的 pass / pipeline 返回固定错误短语
3) 旧写法 --pass no-op / --pipeline default-lowering 继续工作
```

#### 目标验收资产

- `test/tools/test_ircheck_runner.py`：覆盖 pass / pipeline 的语法解析、非法选项文本、旧写法兼容
- `test/pass/test_pass_registry.py`：覆盖有参构造、无参构造、pass / pipeline 不接受选项三种路径

#### 验收必过项目

- `pytest -q test/tools/test_ircheck_runner.py`
- `pytest -q test/pass/test_pass_registry.py`

#### 任务新建建议

- `任务类型：build`
- `任务目标：实现 ircheck 的 pass / pipeline 选项解析与注册层名字+选项构造入口`
- `记录文件：20260412-ircheck-pass-opt-s2.md`

### S3：`tile analysis-only` 收口

#### 阶段目标

- 让 `tile` 真正接受 `analysis-only=true|false`，并把行为差异写进测试。

#### 目标 spec / API

- [`kernel_gen/passes/lowering/tile.py`](../../kernel_gen/passes/lowering/tile.py)
- 公开 API：`TilePass.from_options({"analysis-only": "true"})`

#### 可改文件

- `kernel_gen/passes/lowering/tile.py`
- `test/pass/test_lowering_tile.py`

#### 预期示例代码

```python
tile_pass = build_registered_pass("tile", {"analysis-only": "true"})
module = tile_pass.run(module)
```

#### 预期输出

```text
1) analysis-only=true: 有 tuner.param / 维度推导结果，但没有 symbol.for / dma.view / kernel 重写
2) analysis-only=false: 保持完整 tile 改写
3) analysis-only=maybe: 返回固定失败短语
```

#### 目标验收资产

- `test/pass/test_lowering_tile.py`：拆成带参 true / false / bad-value 三类独立用例

#### 验收必过项目

- `pytest -q test/pass/test_lowering_tile.py`

#### 任务新建建议

- `任务类型：build`
- `任务目标：实现 tile analysis-only 选项并补齐 true/false/非法值测试`
- `记录文件：20260412-ircheck-pass-opt-s3.md`

### S4：黑盒 test 收口

#### 阶段目标

- 在前面测试合同已经收口后，再补齐 `tile` 与 `pipeline` 的黑盒 test 用例，固定带参运行路径的公开行为。

#### 目标 spec / API

- [`test/tools/test_ircheck_runner.py`](../../test/tools/test_ircheck_runner.py)
- [`test/pass/test_pipeline_default_lowering.py`](../../test/pass/test_pipeline_default_lowering.py)
- 公开 API：`run_ircheck_text(...)`

#### 可改文件

- `test/tools/test_ircheck_runner.py`
- `test/pass/test_pipeline_default_lowering.py`
- `test/pass/test_lowering_tile.py`

#### 预期示例代码

```python
def test_run_ircheck_text_tile_analysis_only_option() -> None:
    text = \"\"\"// COMPILE_ARGS: --pass \\\"tile={analysis-only=true}\\\"
// CHECK: tuner.param
// CHECK-NOT: symbol.for
// CHECK-NOT: dma.view

builtin.module {
  func.func @main(%arg0 : !nn.memory<[8, 4], [4, 1], i32, #nn.space<global>>) {
    func.return
  }
}
\"\"\"
    result = run_ircheck_text(text, source_path=\"inline.ircheck\")
    assert result.ok is True
```

#### 预期输出

```text
1) 先有对应 pytest 固定 pass / pipeline 带参合同
2) 不要求执行人修改 expectation
3) tile 与 pipeline 都有唯一主入口黑盒测试
4) 成功路径与失败路径都返回稳定 ok/exit_code/message
5) IR 继续直接内嵌在测试 .py 文件中
```

#### 目标验收资产

- `test/tools/test_ircheck_runner.py`：补充带参 pass / pipeline 的黑盒 run 用例
- `test/pass/test_pipeline_default_lowering.py`：补充 pipeline 多 option 的公开行为测试
- `test/pass/test_lowering_tile.py`：补充 analysis-only 成功/失败的公开行为测试

#### 验收必过项目

- `pytest -q test/tools/test_ircheck_runner.py`
- `pytest -q test/pass/test_pipeline_default_lowering.py`
- `pytest -q test/pass/test_lowering_tile.py`

#### 任务新建建议

- `任务类型：build`
- `任务目标：补齐 pass / pipeline 带参黑盒测试，固定 tile 与 pipeline 的公开行为`
- `记录文件：20260412-ircheck-pass-opt-s4.md`

## 待确认项

- 无。用户已明确选择唯一写法：
  - `--pass "pass_name={analysis-only=true}"`
  - `--pipeline "pipeline_name={k1=v1,k2=v2}"`

## 参考资料

- LLVM lit Command Guide  
  - https://llvm.org/docs/CommandGuide/lit.html
- MLIR Pass Management  
  - https://mlir.llvm.org/docs/PassManagement/
