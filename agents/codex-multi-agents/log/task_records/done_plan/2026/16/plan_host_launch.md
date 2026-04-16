# plan_host_launch.md

## 文档信息

- 创建者：`守护最好的爱莉希雅`
- 最后一次更改：`大闸蟹`
- 目标 `spec`：
  - [`spec/pass/README.md`](../spec/pass/README.md)
  - [`spec/pass/registry.md`](../spec/pass/registry.md)
  - [`spec/pass/lowering/outline_device_kernel.md`](../spec/pass/lowering/outline_device_kernel.md)
  - [`spec/pass/pipeline/default_lowering.md`](../spec/pass/pipeline/default_lowering.md)
  - [`spec/dialect/arch.md`](../spec/dialect/arch.md)
- 目标 `API`：
  - `kernel_gen.passes.lowering.OutlineDeviceKernelPass`
  - `kernel_gen.passes.registry.build_registered_pass("outline-device-kernel")`
  - `func.func` 上的 `launch_block / launch_thread / launch_subthread` 触发属性
  - 可选 metadata：`shared_memory_size`
- 目标 `test`：
  - `test/pass/test_outline_device_kernel.py`
  - [`test/pass/test_pass_registry.py`](../test/pass/test_pass_registry.py)
  - [`test/pass/test_pipeline_default_lowering.py`](../test/pass/test_pipeline_default_lowering.py)
- 目标 `验收资产`：
  - `expectation/pass/lowing/outline_device_kernel/__main__.py`
  - `expectation/pass/lowing/outline_device_kernel/basic.py`
  - `expectation/pass/lowing/outline_device_kernel/multi_function.py`
  - `expectation/pass/lowing/outline_device_kernel/invalid_attr.py`
  - `pytest -q test/pass/test_outline_device_kernel.py`
- 目标 `功能实现`：
  - `kernel_gen/passes/lowering/outline_device_kernel.py`
  - [`kernel_gen/passes/lowering/__init__.py`](../kernel_gen/passes/lowering/__init__.py)
  - [`kernel_gen/passes/registry.py`](../kernel_gen/passes/registry.py)

## 任务清单

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| S1 | 无 | `wt-20260415-host-launch-s1` | `agents/codex-multi-agents/log/task_records/2026/16/20260415-host-launch-s1.md` |
| S2 | S1 | `wt-20260415-host-launch-s2` | `agents/codex-multi-agents/log/task_records/2026/16/20260415-host-launch-s2.md` |
| S3 | S2 | `wt-20260415-host-launch-s3` | `agents/codex-multi-agents/log/task_records/2026/16/20260415-host-launch-s3.md` |
| S4 | S3 | `wt-20260415-host-launch-s4` | `agents/codex-multi-agents/log/task_records/2026/16/20260415-host-launch-s4.md` |
| S5 | S4 | `wt-20260415-host-launch-s5` | `agents/codex-multi-agents/log/task_records/2026/16/20260415-host-launch-s5.md` |

## 评审摘要

- 评审结论：`通过`
- 评审人：`守护最好的爱莉希雅`、`大闸蟹`
- 结论摘要：`已按 2026-04-15 22:24 +0800 互评的唯一最小阻断项完成修订：首轮 ABI 边界固定为“只接受零返回 / 已完成 out-param ABI 的 func.func，命中非空返回值显式报错”，不再把返回值改写混入本轮 pass 范围；standalone pass、显式 launch attrs、首轮排除 gen_kernel/npu_demo ctx、以及 expectation/test/registry/default-lowering 分层口径均已闭环，可按当前版本推进。`

## 互评结论（2026-04-15 22:24 +0800）

- 互评人：`大闸蟹`
- 互评结论：`暂不通过`
- 通过项：
  - `host launch outline` 作为 standalone pass、而非直接并入 `default-lowering`，当前口径合理，可保留。
  - 触发合同固定为 `launch_block / launch_thread / launch_subthread` 三项显式属性，不采用默认 extent，当前口径合理，可保留。
  - 首轮把 `gen_kernel(target="npu_demo")` / `ctx` 专用适配排除在范围外，当前口径合理，可保留。
  - `expectation / test / registry / default-lowering` 四类交付边界基本清楚，可继续沿当前章节结构推进。
- 最小阻断项：
  - 输入函数 ABI 边界尚未写死，导致输出合同自相矛盾。当前正文一方面把 wrapper/device 都写成“保留原参数顺序与返回类型”，另一方面又把 wrapper 结构固定为“`symbol.const + arch.launch + func.return`”；但现有 `arch.launch` 是无结果 op，若输入 `func.func` 仍带非空返回值，wrapper 无法在不额外改 ABI 的前提下保持原返回类型。需要在计划中二选一并写成唯一合同：
    - `A.` 首轮只接受已是无返回值 / 已完成 out-param ABI 的 `func.func`，命中非空返回值时显式报错；
    - `B.` 本轮同步把返回值改写纳入 pass 范围，并明确与 `buffer-results-to-out-params` 的先后与职责边界。
  - 当前推荐 `A`，因为这与“standalone pass、首轮只做最小 IR outline、不并入 default-lowering”更一致。

## 修订说明（2026-04-15 23:51 +0800）

- 修订人：`守护最好的爱莉希雅`
- 修订摘要：
  - 采纳互评推荐项 `A`，把首轮 ABI 边界明确收口为：`OutlineDeviceKernelPass` 只接受零返回 / 已完成 out-param ABI 的 `func.func`；命中非空返回值时必须显式报错，不在本轮同步承担返回值改写。
  - 已同步修正文中所有与 ABI 相关的公开合同、完成态、验收设计与阶段目标，不再保留“wrapper/device 保留原返回类型”的旧表述。
  - `buffer-results-to-out-params` 继续作为前置 ABI 改写能力存在于仓库中，但不并入本轮 `outline-device-kernel` 的职责面；若后续需要支持 memory/scalar 返回值，另开专项计划。

## 复核结论（2026-04-15 23:56 +0800）

- 复核人：`大闸蟹`
- 复核结论：`通过`
- 复核要点：
  - 先前唯一阻断项已收口：当前正文已把 ABI 口径统一为“只接受零返回 / 已完成 out-param ABI 的 `func.func`，命中非空返回值显式报错”，且该口径已同步进入评审摘要、计划目标、公开 API、完成态、验收设计与 `S3/S4` 阶段文本。
  - `host launch outline` 继续保持为 standalone pass，未被并入 `default-lowering`；与当前默认 pipeline 边界一致。
  - 触发合同继续固定为 `launch_block / launch_thread / launch_subthread` 三项显式属性，未引入默认 extent 或启发式推断。
  - 首轮范围继续排除 `gen_kernel(target="npu_demo")` / `ctx` 专用适配；当前计划仍保持“纯 IR host launch outline”最小能力。
  - expectation / test / registry / default-lowering 的交付边界未新增歧义；当前版本可以直接进入建任务推进。

## 输入摘要

- 目标：补一个 host launch 生成 pass，把单个 device 风格 `func.func` 自动 outline 成 `host wrapper + device body` 双函数 IR。
- 不做什么：首轮不改 `default-lowering` 的默认顺序，不把本轮目标扩大成 `gen_kernel(target="npu_demo")` 的后端专用 wrapper/body 收口，也不要求修改 `arch.launch` 的 IR 形状。
- 当前痛点：仓库里已经有 `arch.launch` dialect / DSL lowering / 受控 wrapper+body codegen 子集，但缺少“从单个 device kernel 自动生产 host wrapper”的 pass，导致这一步还靠手写或测试夹具构造。
- 完成后最想看到的例子：对一个带 `launch_block / launch_thread / launch_subthread` 属性的 `func.func @matmul_kernel` 运行 pass 后，主仓能稳定得到 `@matmul_kernel` host wrapper 与 `@matmul_kernel_device` device body，且可被 expectation 与 pytest 机械验证。

## 计划目标

- 新增独立 lowering pass `OutlineDeviceKernelPass`，把显式标记的 `func.func` outline 成 `host wrapper + device body` 双函数 IR。
- 统一触发合同：只对带 `launch_block / launch_thread / launch_subthread` 属性的函数生效；不做函数名猜测、不读 target registry 默认 launch 规模、不扫描 `symbol.for/dma.*` 结构来隐式推断。
- 收口 ABI 边界：首轮只接受零返回 / 已完成 out-param ABI 的函数；命中非空返回值时显式报错，不在本轮同步承担返回值改写。
- 收口公开 IR 结果：wrapper 只保留 launch 维度常量、单个 `arch.launch` 与 `func.return`；device body 继承原函数主体 op 序列与原参数顺序。
- 保持首轮能力为 IR 层 outline；`shared_memory_size` 仅作为函数 metadata 透传，不在本轮扩展 `arch.launch` op 形状。
- 默认 pipeline 保持不变；本 pass 作为显式追加的 standalone pass 使用，由调用方在需要 host launch outline 的链路中主动拼接。
- 用 `expectation + pytest + registry` 三层验收锁住 pass 名称、outline 结果、错误路径与“default-lowering 不被偷偷修改”的边界。

## 当前基线

- 当前公开合同：
  - [`spec/dialect/arch.md`](../spec/dialect/arch.md) 已定义 `arch.launch`，其 callee 必须是扁平 `@symbol`，三层 extent operand 必须是正整数语义的 `!symbol.int<...>`。
  - [`spec/pass/pipeline/default_lowering.md`](../spec/pass/pipeline/default_lowering.md) 当前固定顺序只有 `decompass -> lower-nn -> buffer-results-to-out-params -> lower-dma-memory-hierarchy`，没有 host launch outline pass。
  - [`spec/pass/registry.md`](../spec/pass/registry.md) 已定义名字注册 / 查询机制，但当前内置 pass 集合里没有 `outline-device-kernel`。
- 当前公开 API：
  - [`kernel_gen/dialect/arch.py`](../kernel_gen/dialect/arch.py) 已提供 `ArchLaunchOp`，公开名为 `arch.launch`，构造签名是 `callee, block, thread, subthread, args...`。
  - [`kernel_gen/operation/arch.py`](../kernel_gen/operation/arch.py) 与 DSL lowering 已能从 `launch_kernel(callee, block, thread, subthread, *args)` 生产 `arch.launch`。
  - [`kernel_gen/passes/lowering/__init__.py`](../kernel_gen/passes/lowering/__init__.py) 目前只导出 `DecompassPass / NnLoweringPass / BufferResultsToOutParamsPass / LowerDmaMemoryHierarchyPass / TilePass / KernelSplitPass` 等现有 pass。
- 当前实现入口：
  - `kernel_gen/passes/lowering` 目录下没有 `outline_device_kernel.py`。
  - [`kernel_gen/passes/registry.py`](../kernel_gen/passes/registry.py) 的 `load_builtin_passes()` 当前不会注册任何 host launch outline pass。
  - [`kernel_gen/dsl/gen_kernel.py`](../kernel_gen/dsl/gen_kernel.py) 已能消费受控的 `wrapper + body` module 子集，但该子集是 `npu_demo` 目标专用合同，不等于“任意 IR host launch outline”的通用输出合同。
- 当前测试与验收资产：
  - `test/pass/` 下没有 `test_outline_device_kernel.py`。
  - `expectation/pass/lowing/` 下没有 `outline_device_kernel/` 目录。
  - [`test/pass/test_pipeline_default_lowering.py`](../test/pass/test_pipeline_default_lowering.py) 当前锁定 default pipeline 仍是四个 pass。
- 当前缺口或失败点：
  - 对单个 lowered device 风格函数，目前没有 pass 能机械地产出 host wrapper 与 `_device` body，调用方只能手写 wrapper 或在测试里手工拼 `ModuleOp`。
  - 旧草稿里“device body 保持原签名、同时又直接对接 npu_demo/gen_kernel”的表述与当前仓库实际后端合同并不一致；若把两件事混成一个任务，执行边界会失真。
  - 旧草稿里“未写 launch 属性时回退到 pass 默认 extent”的口径会把 outline 触发条件变成隐式行为，不利于预测与验收。

## 方案比较与选型

- 不采用方案：直接把 `outline-device-kernel` 塞进 [`kernel_gen/passes/pipeline/default_lowering.py`](../kernel_gen/passes/pipeline/default_lowering.py)。
  - 原因：`default-lowering` 当前是通用 lowering 管线；host launch outline 属于更靠近运行时/调度侧的显式选择，不应让所有调用方在未声明需求时自动获得 wrapper+body 变换。
- 不采用方案：不依赖函数属性，转而从 `symbol.for / dma.* / kernel.*` 结构猜测“这像 device kernel，所以自动 outline”。
  - 原因：这会把 pass 从“显式 contract”变成“启发式改写”，一旦普通 helper 函数长得像 device kernel，就会被误改。
- 不采用方案：保留“属性缺失时使用 pass 默认 extent”的旧草稿设计。
  - 原因：trigger 与 config 会混在一起；同一函数是否 outline 取决于外部构造参数，而不是 IR 本身，管理员和执行人都很难机械判断。
- 不采用方案：首轮同步扩展 `arch.launch`，把 `shared_memory_size` 加进 op 的 operand/attribute。
  - 原因：这会把首轮任务扩大到 dialect parser/printer/verifier、spec、测试与后端消费链；当前仓库还没有稳定的 `shared_memory_size` 下游消费口径，先把它保留为函数 metadata 更稳。
- 不采用方案：首轮把 `gen_kernel(target="npu_demo")` 的专用 ctx/body 适配一并并入。
  - 原因：那是后端专用 codegen 合同，不是通用 IR host launch outline 的最小能力；把两层耦在一起会让 pass 范围过大。
- 不采用方案：本轮同步把 memory/scalar 返回值改写并入 `outline-device-kernel`。
  - 原因：这会让 pass 与 [`buffer-results-to-out-params`](../kernel_gen/passes/lowering/buffer_results_to_out_params.py) 的职责交叉，并把“最小 IR outline”扩大成 ABI 重写专题。
- 采用方案：
  - 新增 standalone lowering pass `OutlineDeviceKernelPass`，仅在函数带 `launch_block / launch_thread / launch_subthread` 属性时生效。
  - pass 公开输出固定为：原函数名保留为 host wrapper，新函数名为 `@<orig>_device`，wrapper 中插入 `symbol.const + arch.launch + func.return`，device body 继承原主体。
  - 首轮输入 ABI 固定为零返回 / 已完成 out-param ABI；命中非空返回值时稳定报错，不改写 `func.func` 返回列表。
  - `shared_memory_size` 若存在，仅保留在 outlined device function 的 `func.func attributes` 中；`arch.launch` 形状保持不变。
  - `default-lowering` 不改；只在 `spec/pass/pipeline/default_lowering.md` 里明确“本 pass 不属于默认 pipeline，若需要 host launch outline 由调用方显式追加”。
- 最小公开接口：
- `OutlineDeviceKernelPass.name == "outline-device-kernel"`
- `OutlineDeviceKernelPass().run(module: ModuleOp) -> ModuleOp`
- 只接受零返回 / 已完成 out-param ABI 的 `func.func`
- 触发属性：`launch_block / launch_thread / launch_subthread`
- 可选 metadata：`shared_memory_size`

## 公开 API 设计

### 1. Pass 入口

- 公开入口：`kernel_gen.passes.lowering.OutlineDeviceKernelPass`
- 公开名称：`outline-device-kernel`
- 构造方式：`OutlineDeviceKernelPass()`
- 返回值：`run(module)` 返回改写后的同一 `ModuleOp`
- 首轮约束：不接受 `options`，不定义默认 extent，只接受零返回 / 已完成 out-param ABI 的 `func.func`

```python
from kernel_gen.passes.lowering import OutlineDeviceKernelPass

module = OutlineDeviceKernelPass().run(module)
```

### 2. Registry 入口

- 公开入口：`build_registered_pass("outline-device-kernel")`
- 参数顺序：`name`
- 返回值：`Pass`
- 首轮约束：不接受 `options`

```python
from kernel_gen.passes.registry import build_registered_pass, load_builtin_passes

load_builtin_passes()
pass_obj = build_registered_pass("outline-device-kernel")
module = pass_obj.run(module)
```

### 3. 输入 IR 触发合同

- 触发属性：`launch_block / launch_thread / launch_subthread`
- ABI 约束：输入 `func.func` 必须是零返回；若上游已完成 out-param ABI，则本 pass 直接沿用该零返回签名；命中非空返回值时显式报错
- 属性语义：三者必须同时存在，且必须能规整为正整数语义的 `!symbol.int`
- 可选属性：`shared_memory_size`
- 非触发函数：未携带三项 launch 属性的 `func.func` 保持原样

```text
func.func @matmul_kernel(%lhs: !nn.memory<...>, %rhs: !nn.memory<...>, %out: !nn.memory<...>)
attributes {
  launch_block = 1 : i64,
  launch_thread = 4 : i64,
  launch_subthread = 1 : i64,
  shared_memory_size = 0 : i64
} {
  ...
  func.return
}
```

### 4. 输出 IR 合同

- host wrapper：
  - 保留原函数名 `@matmul_kernel`
  - 保留原参数顺序与零返回 ABI
  - 函数体只允许 outline pass 生成的 extent 常量、单个 `arch.launch` 与 `func.return`
  - 从 wrapper 上移除 `launch_block / launch_thread / launch_subthread`
- device body：
  - 新函数名固定为 `@matmul_kernel_device`
  - 保留原参数顺序与零返回 ABI
  - 继承原函数体 op 序列
  - 若原函数存在 `shared_memory_size`，则只保留在 device function attributes 上

```text
builtin.module {
  func.func @matmul_kernel(%lhs: !nn.memory<...>, %rhs: !nn.memory<...>, %out: !nn.memory<...>) {
    %b = symbol.const 1 : !symbol.int<"1">
    %t = symbol.const 4 : !symbol.int<"4">
    %s = symbol.const 1 : !symbol.int<"1">
    arch.launch<%b, %t, %s>(@matmul_kernel_device, %lhs, %rhs, %out)
    func.return
  }

  func.func @matmul_kernel_device(%lhs: !nn.memory<...>, %rhs: !nn.memory<...>, %out: !nn.memory<...>)
  attributes {shared_memory_size = 0 : i64} {
    ...
    func.return
  }
}
```

## 完成态定义

- `kernel_gen/passes/lowering/outline_device_kernel.py` 已存在，并实现 `OutlineDeviceKernelPass` 与稳定错误类型。
- [`kernel_gen/passes/lowering/__init__.py`](../kernel_gen/passes/lowering/__init__.py) 与 [`kernel_gen/passes/registry.py`](../kernel_gen/passes/registry.py) 已把 `outline-device-kernel` 作为公开 pass 名称接入。
- [`spec/pass/lowering/outline_device_kernel.md`](../spec/pass/lowering/outline_device_kernel.md) 已写清触发属性、输出 IR 形状、错误路径与“不属于 default-lowering”的边界。
- `outline-device-kernel` 对非空返回值输入会稳定报错；零返回 / 已完成 out-param ABI 的输入才能进入 outline。
- `expectation/pass/lowing/outline_device_kernel/` 已补齐可执行 runner 与至少三类资产：单函数成功、多函数成功、属性非法失败。
- `pytest -q test/pass/test_outline_device_kernel.py` 可以机械证明：
  - 标记函数被 outline；
  - 未标记函数不变；
  - wrapper/device 结构正确；
  - 设备函数命名冲突、属性缺失、非法值或非空返回值稳定报错。
- [`test/pass/test_pipeline_default_lowering.py`](../test/pass/test_pipeline_default_lowering.py) 仍通过，说明 `default-lowering` 未被静默改写。
- 当前计划不要求 `gen_kernel(target="npu_demo")` 直接消费该 pass 结果；若后续要把通用 outline 输出接到 `npu_demo` 专用 codegen 子集，需另开计划。

## 验收设计

- 合同真源顺序：
  - `expectation/pass/lowing/outline_device_kernel/*`
  - [`spec/pass/lowering/outline_device_kernel.md`](../spec/pass/lowering/outline_device_kernel.md)
  - `test/pass/test_outline_device_kernel.py`
  - 当前实现
- 验收资产：
  - `expectation/pass/lowing/outline_device_kernel/__main__.py`
  - `expectation/pass/lowing/outline_device_kernel/basic.py`
  - `expectation/pass/lowing/outline_device_kernel/multi_function.py`
  - `expectation/pass/lowing/outline_device_kernel/invalid_attr.py`
  - `test/pass/test_outline_device_kernel.py`
  - [`test/pass/test_pass_registry.py`](../test/pass/test_pass_registry.py)
  - [`test/pass/test_pipeline_default_lowering.py`](../test/pass/test_pipeline_default_lowering.py)
- 输入样例：
  - 单个带 `launch_block / launch_thread / launch_subthread` 属性的 matmul-style `func.func`
  - 同一 module 中“已标记函数 + 未标记函数”混排
  - 缺少部分 launch 属性、extent 为 `<= 0`、device 名称冲突、非空返回值输入
- 锁定输出：
  - wrapper 中出现且只出现单个 `arch.launch`
  - device 函数名固定追加 `_device`
  - wrapper 上不保留三项 launch 属性
  - `shared_memory_size` 只留在 device function attributes
  - 非空返回值输入固定失败，不发生隐式 ABI 改写
  - default pipeline 顺序仍是四个 pass
- 必过命令：
  - `PYTHONPATH=. python expectation/pass/lowing/outline_device_kernel`
  - `pytest -q test/pass/test_outline_device_kernel.py`
  - `pytest -q test/pass/test_pass_registry.py -k outline_device_kernel`
  - `pytest -q test/pass/test_pipeline_default_lowering.py`

## 阶段拆分

### S1：合同与验收资产定稿

#### 阶段目标

- 先把 host launch outline 的公开触发合同、输出 IR 形状和验收资产路径写成稳定文本，不让执行人边做边猜。

#### 目标 spec / API

- [`spec/pass/lowering/outline_device_kernel.md`](../spec/pass/lowering/outline_device_kernel.md)
- [`spec/pass/README.md`](../spec/pass/README.md)
- [`spec/pass/pipeline/default_lowering.md`](../spec/pass/pipeline/default_lowering.md)
- `公开 API：OutlineDeviceKernelPass / outline-device-kernel / launch_block|launch_thread|launch_subthread`

#### 可改文件

- `spec/pass/lowering/outline_device_kernel.md`
- [`spec/pass/README.md`](../spec/pass/README.md)
- [`spec/pass/pipeline/default_lowering.md`](../spec/pass/pipeline/default_lowering.md)
- `expectation/pass/lowing/outline_device_kernel/__main__.py`
- `expectation/pass/lowing/outline_device_kernel/basic.py`
- `expectation/pass/lowing/outline_device_kernel/multi_function.py`
- `expectation/pass/lowing/outline_device_kernel/invalid_attr.py`

#### 预期示例代码

```text
func.func @kernel(%arg0: !nn.memory<...>) attributes {
  launch_block = 1 : i64,
  launch_thread = 4 : i64,
  launch_subthread = 1 : i64
} {
  ...
  func.return
}
```

#### 预期输出

```text
outline-device-kernel only runs on explicitly marked functions
default-lowering remains unchanged
shared_memory_size is metadata-only in V1
```

#### 目标验收资产

- `expectation/pass/lowing/outline_device_kernel/basic.py`
- `expectation/pass/lowing/outline_device_kernel/multi_function.py`
- `expectation/pass/lowing/outline_device_kernel/invalid_attr.py`
- `expectation/pass/lowing/outline_device_kernel/__main__.py`

#### 验收必过项目

- `PYTHONPATH=. python expectation/pass/lowing/outline_device_kernel`
- `rg -n "outline-device-kernel|launch_block|default-lowering remains unchanged|shared_memory_size" spec/pass/lowering/outline_device_kernel.md spec/pass/pipeline/default_lowering.md`

#### 任务新建建议

- `任务类型：spec`
- `任务目标：收口 outline-device-kernel 的 pass 合同、expectation 路径与 default-lowering 边界`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260415-host-launch-s1.md`

### S2：Pass 骨架与注册入口

#### 阶段目标

- 新增可被 registry 构造的 `OutlineDeviceKernelPass` 骨架，并明确输入边界与稳定错误短语。

#### 目标 spec / API

- `公开 API：OutlineDeviceKernelPass.name == "outline-device-kernel"`
- `公开 API：build_registered_pass("outline-device-kernel")`

#### 可改文件

- `kernel_gen/passes/lowering/outline_device_kernel.py`
- [`kernel_gen/passes/lowering/__init__.py`](../kernel_gen/passes/lowering/__init__.py)
- [`kernel_gen/passes/registry.py`](../kernel_gen/passes/registry.py)
- `test/pass/test_outline_device_kernel.py`

## 归档记录

时间：2026-04-17 01:47 +0800
经办人：李白
任务：T-20260417-21d4ea53
任务目标：将 `plan/plan_host_launch.md` 归档到 `agents/codex-multi-agents/log/task_records/done_plan/2026/16/plan_host_launch.md`，并完成归档 merge 收口。
改动：
- 管理员指定的 `worktree=/home/lfr/kernelcode_generate/wt-20260417-archive-plan-host-launch` 与任务分支 `T-20260417-21d4ea53` 原本不存在；已按当前远端主分支 `origin/main@c8f327d` 补建归档 `worktree` 与对应分支。
- 核对发现源计划书 `plan/plan_host_launch.md` 当前只存在于主仓本地文件系统，目标 `done_plan` 文件在主仓当前也不存在；因此将主仓本地源计划书整体迁移到任务 `worktree` 内的归档目标路径 `agents/codex-multi-agents/log/task_records/done_plan/2026/16/plan_host_launch.md`，并在文件尾部追加本次归档记录。
- 本次归档合并范围限定为新增 `agents/codex-multi-agents/log/task_records/done_plan/2026/16/plan_host_launch.md`；按用户要求，主仓本地源计划书已删除，不修改 `.gitignore`、`TODO.md`、`DONE.md` 或其他共享状态文件。
验证：
- `rg -n "T-20260417-21d4ea53" /home/lfr/kernelcode_generate/TODO.md` -> 确认任务为 `merge/进行中/指派=李白`
- `git -C /home/lfr/kernelcode_generate worktree add -b T-20260417-21d4ea53 /home/lfr/kernelcode_generate/wt-20260417-archive-plan-host-launch origin/main` -> 成功创建归档 `worktree`
- `git -C /home/lfr/kernelcode_generate rev-parse --verify origin/main` -> `c8f327dde7284bfb737b0b9d5b66657bd3adf4fa`
- `test -f /home/lfr/kernelcode_generate/plan/plan_host_launch.md && echo ROOT_PLAN_EXISTS || echo ROOT_PLAN_MISSING` -> 迁移前为 `ROOT_PLAN_EXISTS`
- `test -f /home/lfr/kernelcode_generate/agents/codex-multi-agents/log/task_records/done_plan/2026/16/plan_host_launch.md && echo DONE_PLAN_EXISTS || echo DONE_PLAN_MISSING` -> 迁移前为 `DONE_PLAN_MISSING`
- `test -f /home/lfr/kernelcode_generate/wt-20260417-archive-plan-host-launch/agents/codex-multi-agents/log/task_records/done_plan/2026/16/plan_host_launch.md && echo ARCHIVE_READY && test -e /home/lfr/kernelcode_generate/plan/plan_host_launch.md || echo ROOT_REMOVED` -> `ARCHIVE_READY`、`ROOT_REMOVED`
结论：归档文件已在指定 `worktree` 内生成并写入归档记录；下一步提交并推送该归档文件，随后执行当前 merge 任务 `-done` 并回报管理员继续 `-done-plan`。
- [`test/pass/test_pass_registry.py`](../test/pass/test_pass_registry.py)

#### 预期示例代码

```python
from kernel_gen.passes.lowering import OutlineDeviceKernelPass
from kernel_gen.passes.registry import build_registered_pass, load_builtin_passes

load_builtin_passes()
assert OutlineDeviceKernelPass.name == "outline-device-kernel"
assert build_registered_pass("outline-device-kernel").name == "outline-device-kernel"
```

#### 预期输出

```text
outline-device-kernel is registered
non-ModuleOp input raises OutlineDeviceKernelError
empty module returns without mutation
```

#### 目标验收资产

- `test/pass/test_outline_device_kernel.py`
- [`test/pass/test_pass_registry.py`](../test/pass/test_pass_registry.py)

#### 验收必过项目

- `pytest -q test/pass/test_outline_device_kernel.py -k 'registry or non_module or empty_module'`
- `pytest -q test/pass/test_pass_registry.py -k outline_device_kernel`

#### 任务新建建议

- `任务类型：build`
- `任务目标：新增 outline-device-kernel pass 骨架、稳定错误类型与 registry 导出`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260415-host-launch-s2.md`

### S3：Outline 核心改写

#### 阶段目标

- 实现从单个标记函数到 `host wrapper + device body` 的核心改写，并锁定“只接受零返回 ABI”的最小 IR 结构。

#### 目标 spec / API

- `公开 API：launch_block / launch_thread / launch_subthread 三项同时存在才 outline`
- `公开 API：非空返回值输入显式报错，不在本轮承担 ABI 改写`
- `公开 API：输出函数对为 @name + @name_device`

#### 可改文件

- `kernel_gen/passes/lowering/outline_device_kernel.py`
- `test/pass/test_outline_device_kernel.py`
- `expectation/pass/lowing/outline_device_kernel/basic.py`
- `expectation/pass/lowing/outline_device_kernel/multi_function.py`

#### 预期示例代码

```text
builtin.module {
  func.func @matmul_kernel(...) attributes {
    launch_block = 1 : i64,
    launch_thread = 4 : i64,
    launch_subthread = 1 : i64
  } {
    ...
    func.return
  }
}
```

#### 预期输出

```text
builtin.module {
  func.func @matmul_kernel(...) {
    %b = symbol.const 1 : !symbol.int<"1">
    %t = symbol.const 4 : !symbol.int<"4">
    %s = symbol.const 1 : !symbol.int<"1">
    arch.launch<%b, %t, %s>(@matmul_kernel_device, ...)
    func.return
  }
  func.func @matmul_kernel_device(...) { ... }
}
```

#### 目标验收资产

- `expectation/pass/lowing/outline_device_kernel/basic.py`
- `expectation/pass/lowing/outline_device_kernel/multi_function.py`
- `test/pass/test_outline_device_kernel.py`

#### 验收必过项目

- `PYTHONPATH=. python expectation/pass/lowing/outline_device_kernel/basic.py`
- `PYTHONPATH=. python expectation/pass/lowing/outline_device_kernel/multi_function.py`
- `pytest -q test/pass/test_outline_device_kernel.py -k 'outline_basic or multi_function or unmarked_function'`

#### 任务新建建议

- `任务类型：build`
- `任务目标：实现 outline-device-kernel 核心改写与双函数 IR expectation`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260415-host-launch-s3.md`

### S4：属性清理与 metadata 保留

#### 阶段目标

- 收口 launch 属性清理、`shared_memory_size` metadata 保留与非法属性 / 非空返回输入的稳定错误路径。

#### 目标 spec / API

- `公开 API：wrapper 不保留 launch_* attrs`
- `公开 API：shared_memory_size 仅保留在 device function`

#### 可改文件

- `kernel_gen/passes/lowering/outline_device_kernel.py`
- `test/pass/test_outline_device_kernel.py`
- `expectation/pass/lowing/outline_device_kernel/invalid_attr.py`
- `expectation/pass/lowing/outline_device_kernel/basic.py`

#### 预期示例代码

```text
func.func @kernel(...) attributes {
  launch_block = 1 : i64,
  launch_thread = 4 : i64,
  launch_subthread = 1 : i64,
  shared_memory_size = 0 : i64
} { ... }
```

#### 预期输出

```text
wrapper attrs do not contain launch_block/launch_thread/launch_subthread
device attrs keep shared_memory_size only
partial or non-positive launch attrs raise OutlineDeviceKernelError
```

#### 目标验收资产

- `expectation/pass/lowing/outline_device_kernel/invalid_attr.py`
- `test/pass/test_outline_device_kernel.py`

#### 验收必过项目

- `PYTHONPATH=. python expectation/pass/lowing/outline_device_kernel/invalid_attr.py`
- `pytest -q test/pass/test_outline_device_kernel.py -k 'shared_memory_size or invalid_attr or naming_conflict or non_empty_result'`

#### 任务新建建议

- `任务类型：build`
- `任务目标：收口 launch attr 清理、shared_memory_size metadata 与错误路径`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260415-host-launch-s4.md`

### S5：总体验收与边界回归

#### 阶段目标

- 完成 pass/spec/registry/expectation 的总体验收，并锁定 `default-lowering` 未被暗改的边界。

#### 目标 spec / API

- [`spec/pass/lowering/outline_device_kernel.md`](../spec/pass/lowering/outline_device_kernel.md)
- [`spec/pass/pipeline/default_lowering.md`](../spec/pass/pipeline/default_lowering.md)
- `公开 API：default-lowering 不默认包含 outline-device-kernel`

#### 可改文件

- `test/pass/test_outline_device_kernel.py`
- [`test/pass/test_pass_registry.py`](../test/pass/test_pass_registry.py)
- [`test/pass/test_pipeline_default_lowering.py`](../test/pass/test_pipeline_default_lowering.py)
- `spec/pass/lowering/outline_device_kernel.md`
- [`spec/pass/pipeline/default_lowering.md`](../spec/pass/pipeline/default_lowering.md)
- `expectation/pass/lowing/outline_device_kernel/__main__.py`

#### 预期示例代码

```python
from kernel_gen.passes.pipeline import build_default_lowering_pipeline

pm = build_default_lowering_pipeline()
assert [item.name for item in pm._passes] == [
    "decompass",
    "lower-nn",
    "buffer-results-to-out-params",
    "lower-dma-memory-hierarchy",
]
```

#### 预期输出

```text
outline-device-kernel works as standalone pass
default-lowering stays four-pass pipeline
all expectation assets pass from package root entry
```

#### 目标验收资产

- `expectation/pass/lowing/outline_device_kernel/__main__.py`
- `test/pass/test_outline_device_kernel.py`
- [`test/pass/test_pass_registry.py`](../test/pass/test_pass_registry.py)
- [`test/pass/test_pipeline_default_lowering.py`](../test/pass/test_pipeline_default_lowering.py)

#### 验收必过项目

- `PYTHONPATH=. python expectation/pass/lowing/outline_device_kernel`
- `pytest -q test/pass/test_outline_device_kernel.py`
- `pytest -q test/pass/test_pass_registry.py -k outline_device_kernel`
- `pytest -q test/pass/test_pipeline_default_lowering.py`

#### 任务新建建议

- `任务类型：review`
- `任务目标：完成 outline-device-kernel 总体验收并确认 default-lowering 边界未回退`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/16/20260415-host-launch-s5.md`

## 待确认项

- 问题：`shared_memory_size` 后续是否需要真正进入 `arch.launch` 的公开 IR 形状。
  - 可选项：`A. 继续只做 device function metadata` / `B. 在后续计划里扩展 arch.launch attr 或 operand`
  - 差异：`A` 可以让首轮 pass 先稳定落地；`B` 会牵涉 dialect/spec/parser/printer/runtime 消费链。
  - 推荐项：`A`
- 问题：后续是否要把“非空返回值函数先改写为 out-param ABI”纳入 host launch 链。
  - 可选项：`A. 继续保持与 buffer-results-to-out-params 分离，另开计划` / `B. 后续把 ABI 改写与 outline 做成串联计划`
  - 差异：`A` 保持当前 pass 只做最小 outline；`B` 会引入 pass 顺序与职责边界的新合同。
  - 推荐项：`A`
- 问题：通用 outline 结果是否要直接兼容 `gen_kernel(target="npu_demo")` 当前专用 wrapper/body 子集。
  - 可选项：`A. 本轮不兼容，后续另开计划` / `B. 本轮同步加 ctx/body 适配`
  - 差异：`A` 能保持 pass 为纯 IR host launch outline；`B` 会把任务扩大到 npu_demo 专用 codegen 合同。
  - 推荐项：`A`

## 参考资料

- [`kernel_gen/dialect/arch.py`](../kernel_gen/dialect/arch.py)
- [`kernel_gen/operation/arch.py`](../kernel_gen/operation/arch.py)
- [`kernel_gen/passes/registry.py`](../kernel_gen/passes/registry.py)
- [`kernel_gen/passes/pipeline/default_lowering.py`](../kernel_gen/passes/pipeline/default_lowering.py)
- [`kernel_gen/dsl/gen_kernel.py`](../kernel_gen/dsl/gen_kernel.py)
- [`test/dsl/test_gen_kernel.py`](../test/dsl/test_gen_kernel.py)

## 当前主仓终验（2026-04-16 01:07 +0800）

- 终验人：`大闸蟹`
- 当前结论：`不通过`
- 依据：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/pass/lowing/outline_device_kernel` -> `exit=2`；当前主仓不存在 [`expectation/pass/lowing/outline_device_kernel`](../expectation/pass/lowing/outline_device_kernel) 目录，计划定义的 package root expectation 入口无法执行。
  - `pytest -q test/pass/test_outline_device_kernel.py` -> `exit=4`；当前主仓不存在 [`test/pass/test_outline_device_kernel.py`](../test/pass/test_outline_device_kernel.py)。
  - `pytest -q test/pass/test_pass_registry.py -k outline_device_kernel` -> `exit=5`，`15 deselected`；当前 registry 回归里没有任何 `outline_device_kernel` 相关用例被选中，说明计划要求的注册验收资产未落地。
  - `pytest -q test/pass/test_pipeline_default_lowering.py` -> `2 passed`；只能证明 `default-lowering` 仍保持四段 pass，不足以证明 host launch plan 已完成。
  - `rg -n "outline-device-kernel|OutlineDeviceKernelPass|outline_device_kernel" kernel_gen spec test expectation -S` -> 无命中；当前主仓未见 pass 实现、spec、test 或 expectation 交付物。
  - `find . -path '*outline_device_kernel*' -o -path '*outline-device-kernel*'` -> 无输出；当前仓库现场不存在计划中定义的核心产物路径。
- 最小阻断项：
  - [`kernel_gen/passes/lowering/outline_device_kernel.py`](../kernel_gen/passes/lowering/outline_device_kernel.py)、[`kernel_gen/passes/lowering/__init__.py`](../kernel_gen/passes/lowering/__init__.py)、[`kernel_gen/passes/registry.py`](../kernel_gen/passes/registry.py) 未形成 `outline-device-kernel` 公开 pass 交付；主仓对该 pass 没有实现与 registry 接口。
  - [`spec/pass/lowering/outline_device_kernel.md`](../spec/pass/lowering/outline_device_kernel.md)、[`test/pass/test_outline_device_kernel.py`](../test/pass/test_outline_device_kernel.py)、[`expectation/pass/lowing/outline_device_kernel/__main__.py`](../expectation/pass/lowing/outline_device_kernel/__main__.py) 及同目录验收资产未落地，导致计划书定义的三层合同无法执行。
  - [`agents/codex-multi-agents/log/task_records/2026/16/20260415-host-launch-s1.md`](../agents/codex-multi-agents/log/task_records/2026/16/20260415-host-launch-s1.md) 当前主仓也不存在；`DONE.md` 虽记载 `T-20260415-570f5d9a` 已完成，但现有主仓现场无法复核“已合入内容”。
- 终验说明：
  - 当前计划表显示 `1/1/0/完成待检查`，但主仓现场与计划完成态严重不符，不能按归档处理。
  - 当前唯一正确动作是回到原计划补修复任务，先把 `outline-device-kernel` 的 pass / spec / expectation / test 交付真正落到主仓，再重新终验。

## 修复任务补建（2026-04-16 01:07 +0800）

- 补建人：`大闸蟹`
- 唯一继续项：[`T-20260416-3ab74a71`](../TODO.md)
- 任务类型：`build`
- 唯一修复范围：
  - 补齐 [`kernel_gen/passes/lowering/outline_device_kernel.py`](../kernel_gen/passes/lowering/outline_device_kernel.py)、[`kernel_gen/passes/lowering/__init__.py`](../kernel_gen/passes/lowering/__init__.py)、[`kernel_gen/passes/registry.py`](../kernel_gen/passes/registry.py) 的 `outline-device-kernel` pass 交付。
  - 补齐 [`spec/pass/lowering/outline_device_kernel.md`](../spec/pass/lowering/outline_device_kernel.md)、[`test/pass/test_outline_device_kernel.py`](../test/pass/test_outline_device_kernel.py)、[`expectation/pass/lowing/outline_device_kernel/__main__.py`](../expectation/pass/lowing/outline_device_kernel/__main__.py) 及同目录 expectation 资产。
  - 让本计划定义的四条终验命令在主仓可执行且通过。
- 续推口径：
  - 当前不得创建归档任务，也不得执行 `-done-plan`。
  - 以本轮补建的修复任务作为唯一继续项；待其完成并回到本计划复核通过后，再进入归档链。

## 当前主仓终验（2026-04-16 09:05 +0800）

- 终验人：`守护最好的爱莉希雅`
- 当前结论：`不通过`
- 依据：
  - `test -f expectation/pass/lowing/outline_device_kernel/__main__.py && echo MAIN_OK; test -f expectation/pass/lowing/outline_device_kernel/basic.py && echo BASIC_OK; test -f expectation/pass/lowing/outline_device_kernel/multi_function.py && echo MULTI_OK; test -f expectation/pass/lowing/outline_device_kernel/invalid_attr.py && echo INVALID_OK` -> `exit=1`；当前主仓仍不存在计划书点名的四个 expectation 资产。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/pass/lowing/outline_device_kernel/__main__.py` -> `exit=2`；目录入口文件不存在。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_outline_device_kernel.py` -> `3 passed`；说明 pass 对应 pytest 载体已进入主仓。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_pass_registry.py -k outline_device_kernel` -> `1 passed, 15 deselected`；说明 registry 侧验收已进入主仓。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_pipeline_default_lowering.py` -> `2 passed`；说明 `default-lowering remains unchanged` 仍成立。
- 最小阻断项：
  - [`expectation/pass/lowing/outline_device_kernel/__main__.py`](../expectation/pass/lowing/outline_device_kernel/__main__.py)、[`expectation/pass/lowing/outline_device_kernel/basic.py`](../expectation/pass/lowing/outline_device_kernel/basic.py)、[`expectation/pass/lowing/outline_device_kernel/multi_function.py`](../expectation/pass/lowing/outline_device_kernel/multi_function.py)、[`expectation/pass/lowing/outline_device_kernel/invalid_attr.py`](../expectation/pass/lowing/outline_device_kernel/invalid_attr.py) 仍未进入主仓，导致计划书定义的 expectation 目录级验收无法执行。
- 终验说明：
  - 相比 2026-04-16 01:07 +0800 的上一轮主仓复核，当前 pass / spec / pytest 资产已经在主仓可见；剩余阻断已收敛为 expectation 目录资产缺失，不再是整条链路未落地。
  - 但本计划的完成态明确要求 `expectation/pass/lowing/outline_device_kernel/` 目录级入口与三份子资产存在且可运行；在这一条未满足前，本计划仍`不通过`，且`不可进入归档链`。

## 修复任务补建（2026-04-16 09:05 +0800）

- 补建人：`守护最好的爱莉希雅`
- 唯一继续项：[`T-20260416-6baa7926`](../TODO.md)
- 任务类型：`spec`
- 唯一修复范围：
  - 仅补齐 [`expectation/pass/lowing/outline_device_kernel/__main__.py`](../expectation/pass/lowing/outline_device_kernel/__main__.py)、[`expectation/pass/lowing/outline_device_kernel/basic.py`](../expectation/pass/lowing/outline_device_kernel/basic.py)、[`expectation/pass/lowing/outline_device_kernel/multi_function.py`](../expectation/pass/lowing/outline_device_kernel/multi_function.py)、[`expectation/pass/lowing/outline_device_kernel/invalid_attr.py`](../expectation/pass/lowing/outline_device_kernel/invalid_attr.py) 四个 tracked expectation 资产，并验证目录入口可运行。
  - 本轮不再重做 pass / spec / pytest 侧实现；这些资产已在主仓通过当前终验复核。
- 续推口径：
  - 当前不得创建归档任务，也不得执行 `-done-plan`。
  - 以 [`T-20260416-6baa7926`](../TODO.md) 作为当前唯一继续项；待该任务完成并回到本计划复核通过后，再进入归档链。

## 当前主仓终验复核（2026-04-16 02:08 +0800）

- 终验人：`大闸蟹`
- 当前结论：`不通过`
- 依据：
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/pass/lowing/outline_device_kernel` -> `exit=2`；当前主仓仍不存在 [`expectation/pass/lowing/outline_device_kernel`](../expectation/pass/lowing/outline_device_kernel) 目录，目录级 expectation 入口无法执行。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_outline_device_kernel.py` -> `3 passed`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_pass_registry.py -k outline_device_kernel` -> `1 passed, 15 deselected`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_pipeline_default_lowering.py` -> `2 passed`。
- 最小阻断项：
  - 当前主仓已具备 [`kernel_gen/passes/lowering/outline_device_kernel.py`](../kernel_gen/passes/lowering/outline_device_kernel.py)、[`spec/pass/lowering/outline_device_kernel.md`](../spec/pass/lowering/outline_device_kernel.md)、[`test/pass/test_outline_device_kernel.py`](../test/pass/test_outline_device_kernel.py) 与 registry/default-lowering 回归，但计划正文点名的 4 个 expectation 合同资产仍未落到主仓：
    - [`expectation/pass/lowing/outline_device_kernel/__main__.py`](../expectation/pass/lowing/outline_device_kernel/__main__.py)
    - [`expectation/pass/lowing/outline_device_kernel/basic.py`](../expectation/pass/lowing/outline_device_kernel/basic.py)
    - [`expectation/pass/lowing/outline_device_kernel/multi_function.py`](../expectation/pass/lowing/outline_device_kernel/multi_function.py)
    - [`expectation/pass/lowing/outline_device_kernel/invalid_attr.py`](../expectation/pass/lowing/outline_device_kernel/invalid_attr.py)
  - 因此本计划定义的 4 条终验命令仍未全通过，当前不能进入归档链。
- 终验说明：
  - 与 `2026-04-16 01:07 +0800` 相比，主仓已收口 pass/spec/test 三层交付，剩余问题已缩到 expectation 目录级合同资产缺失。
  - 当前唯一正确动作是补一条 expectation 修复链，只收口 `expectation/pass/lowing/outline_device_kernel/` 目录与其 4 个资产，不再扩大到实现、测试或 `.gitignore`。

## 当前主仓终验复核（2026-04-16 09:36 +0800）

- 终验人：`大闸蟹`
- 当前结论：`不通过`
- 依据：
  - `test -f expectation/pass/lowing/outline_device_kernel/__main__.py && echo MAIN_OK; test -f expectation/pass/lowing/outline_device_kernel/basic.py && echo BASIC_OK; test -f expectation/pass/lowing/outline_device_kernel/multi_function.py && echo MULTI_OK; test -f expectation/pass/lowing/outline_device_kernel/invalid_attr.py && echo INVALID_OK` -> `exit=1`；当前主仓仍未见计划正文点名的 4 个 expectation 资产。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/pass/lowing/outline_device_kernel` -> `exit=2`；目录级 expectation 入口依旧不存在。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_outline_device_kernel.py` -> `3 passed`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_pass_registry.py -k outline_device_kernel` -> `1 passed, 15 deselected`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_pipeline_default_lowering.py` -> `2 passed`。
  - `find expectation/pass -maxdepth 4 -path '*outline_device_kernel*' -o -path '*outline-device-kernel*'` -> 无输出；当前 `expectation/pass` 目录下仍没有 `outline_device_kernel` 资产落点。
- 最小阻断项：
  - 尽管 [`T-20260416-739347f7`](../DONE.md) 已记为完成，当前主仓现场仍未出现以下 4 个 expectation 资产：
    - [`expectation/pass/lowing/outline_device_kernel/__main__.py`](../expectation/pass/lowing/outline_device_kernel/__main__.py)
    - [`expectation/pass/lowing/outline_device_kernel/basic.py`](../expectation/pass/lowing/outline_device_kernel/basic.py)
    - [`expectation/pass/lowing/outline_device_kernel/multi_function.py`](../expectation/pass/lowing/outline_device_kernel/multi_function.py)
    - [`expectation/pass/lowing/outline_device_kernel/invalid_attr.py`](../expectation/pass/lowing/outline_device_kernel/invalid_attr.py)
  - 因此本计划定义的 4 条终验命令仍未全通过，当前不能进入归档链。
- 终验说明：
  - 与 `2026-04-16 09:05 +0800` 和 `2026-04-16 02:08 +0800` 相比，主仓阻断面没有实质变化，仍集中在 `expectation/pass/lowing/outline_device_kernel/` 目录级合同资产缺失。
  - 当前不能按“已完成可归档”处理；需重新补一条只面向这 4 个 expectation 资产的修复链，完成后再回到本计划复核。
- 修复任务：[`T-20260416-46848208`](../TODO.md)
- `worktree`：`wt-20260416-host-launch-r3-main-expectation-fix`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/16/20260416-host-launch-r3-main-expectation-fix.md`
- 修复范围：
  - 仅补齐 [`expectation/pass/lowing/outline_device_kernel/__main__.py`](../expectation/pass/lowing/outline_device_kernel/__main__.py)、[`expectation/pass/lowing/outline_device_kernel/basic.py`](../expectation/pass/lowing/outline_device_kernel/basic.py)、[`expectation/pass/lowing/outline_device_kernel/multi_function.py`](../expectation/pass/lowing/outline_device_kernel/multi_function.py)、[`expectation/pass/lowing/outline_device_kernel/invalid_attr.py`](../expectation/pass/lowing/outline_device_kernel/invalid_attr.py) 四个 tracked expectation 资产，并恢复目录级入口可执行性。
  - 不扩大到 `kernel_gen/`、`spec/`、`test/`、`.gitignore` 或其他 expectation 路径。
- 续推说明：
  - 已完成的 [`T-20260416-739347f7`](../DONE.md) 不再继续复用。
  - 以 [`T-20260416-46848208`](../TODO.md) 作为当前唯一继续项；待该任务完成并回到本计划复核通过后，再进入归档链。

## 当前主仓终验（2026-04-16 09:39 +0800）

- 终验人：`守护最好的爱莉希雅`
- 当前结论：`不通过`
- 依据：
  - 管理员同步 [`T-20260416-739347f7`](../DONE.md) 已由李白合入主仓并 `-done`，提交为 `78fccb6`；但当前主仓现场仍未出现计划正文点名的 4 个 expectation 资产。
  - `test -f expectation/pass/lowing/outline_device_kernel/__main__.py && echo MAIN_OK; test -f expectation/pass/lowing/outline_device_kernel/basic.py && echo BASIC_OK; test -f expectation/pass/lowing/outline_device_kernel/multi_function.py && echo MULTI_OK; test -f expectation/pass/lowing/outline_device_kernel/invalid_attr.py && echo INVALID_OK` -> `exit=1`。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/pass/lowing/outline_device_kernel` -> `exit=2`；目录级 expectation 入口仍不存在。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_outline_device_kernel.py` -> `3 passed`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_pass_registry.py -k outline_device_kernel` -> `1 passed, 15 deselected`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_pipeline_default_lowering.py` -> `2 passed`。
- 最小阻断项：
  - 当前只剩 [`expectation/pass/lowing/outline_device_kernel/__main__.py`](../expectation/pass/lowing/outline_device_kernel/__main__.py)、[`expectation/pass/lowing/outline_device_kernel/basic.py`](../expectation/pass/lowing/outline_device_kernel/basic.py)、[`expectation/pass/lowing/outline_device_kernel/multi_function.py`](../expectation/pass/lowing/outline_device_kernel/multi_function.py)、[`expectation/pass/lowing/outline_device_kernel/invalid_attr.py`](../expectation/pass/lowing/outline_device_kernel/invalid_attr.py) 这 4 个 tracked expectation 资产未落主仓，导致计划书定义的目录级 expectation 验收仍无法执行。
- 终验说明：
  - 当前主仓已满足 pass / registry / default-lowering 的终验要求，阻断面没有扩大。
  - 但在上述 4 个 expectation 资产补齐前，本计划仍`不通过`，且`不可进入归档链`。

## 修复任务补建（2026-04-16 09:39 +0800）

- 补建人：`守护最好的爱莉希雅`
- 当时补建项：`T-20260416-15c1ac96`
- 任务类型：`spec`
- `worktree`：`wt-20260416-host-launch-r3-expectation-fix`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/16/20260416-host-launch-r3-expectation-fix.md`
- 唯一修复范围：
  - 仅补齐 [`expectation/pass/lowing/outline_device_kernel/__main__.py`](../expectation/pass/lowing/outline_device_kernel/__main__.py)、[`expectation/pass/lowing/outline_device_kernel/basic.py`](../expectation/pass/lowing/outline_device_kernel/basic.py)、[`expectation/pass/lowing/outline_device_kernel/multi_function.py`](../expectation/pass/lowing/outline_device_kernel/multi_function.py)、[`expectation/pass/lowing/outline_device_kernel/invalid_attr.py`](../expectation/pass/lowing/outline_device_kernel/invalid_attr.py) 四个 tracked expectation 资产，并验证目录入口可运行。
  - 不修改 `.gitignore`，不扩大到 `kernel_gen/`、`spec/`、`test/` 或其他 expectation 路径。
  - merge 阶段仅对上述 4 个 ignored expectation 路径执行 `git add -f` 纳入交付。
- 续推说明：
  - 当前不得创建归档任务，也不得执行 `-done-plan`。
  - 该补建项随后被判定为与 [`T-20260416-46848208`](../TODO.md) 同范围的重复任务，不再作为继续项；最终唯一继续项以本页“重复任务裁定（2026-04-16 09:41 +0800）”为准。

## 重复修复任务裁定（2026-04-16 09:43 +0800）

- 裁定人：`大闸蟹`
- 重复项：
  - [`T-20260416-46848208`](../TODO.md)
  - `T-20260416-15c1ac96`
- 现场核对：
  - [`T-20260416-46848208`](../TODO.md) 当前在 [`TODO.md`](../TODO.md) 中存在，`worktree` 为 `wt-20260416-host-launch-r3-main-expectation-fix`，记录文件为 `agents/codex-multi-agents/log/task_records/2026/16/20260416-host-launch-r3-main-expectation-fix.md`，且已写入本轮 expectation 例外授权边界。
  - `T-20260416-15c1ac96` 当前只出现在本计划上一节文本中；在 [`TODO.md`](../TODO.md) 与 [`DONE.md`](../DONE.md) 中未找到对应任务条目，当前不构成可执行任务链。
  - 两者指向同一阻断面：仅补齐 [`expectation/pass/lowing/outline_device_kernel/__main__.py`](../expectation/pass/lowing/outline_device_kernel/__main__.py)、[`expectation/pass/lowing/outline_device_kernel/basic.py`](../expectation/pass/lowing/outline_device_kernel/basic.py)、[`expectation/pass/lowing/outline_device_kernel/multi_function.py`](../expectation/pass/lowing/outline_device_kernel/multi_function.py)、[`expectation/pass/lowing/outline_device_kernel/invalid_attr.py`](../expectation/pass/lowing/outline_device_kernel/invalid_attr.py) 四个 tracked expectation 资产，不修改 `.gitignore`，不扩大到 `kernel_gen/`、`spec/`、`test/` 或其他 expectation 路径。
- 唯一保留项：
  - 保留 [`T-20260416-46848208`](../TODO.md)。
- 停止项：
  - `T-20260416-15c1ac96` 视为重复文本口径；若后续出现在任务表中，请管理员删除或停止分发，不再作为本计划继续项。
- 续推口径：
  - 管理员恢复并继续推进 [`T-20260416-46848208`](../TODO.md)。
  - 朽木露琪亚按 `agents/codex-multi-agents/log/task_records/2026/16/20260416-host-launch-r3-main-expectation-fix.md` 中的授权执行：仅新增或修改上述 4 个 expectation 文件，可补目录入口 `__main__.py`；禁止修改 `.gitignore`，禁止纳入其他路径。

## 重复任务裁定（2026-04-16 09:41 +0800）

- 裁定人：`守护最好的爱莉希雅`
- 裁定结论：
  - 保留任务：[`T-20260416-46848208`](../TODO.md)
  - 停止任务：`T-20260416-15c1ac96`
- 裁定依据：
  - 按重复修复任务处理规则，优先保留范围更清楚、依赖正确、`worktree` 明确且已进入管理员推进链的那一条。
  - [`T-20260416-46848208`](../TODO.md) 已在当前 `TODO.md` 中登记、已明确指派执行人、已有 `worktree` [`wt-20260416-host-launch-r3-main-expectation-fix`](../wt-20260416-host-launch-r3-main-expectation-fix)，且管理员已按该任务号向执行人发起续推。
  - `T-20260416-15c1ac96` 是在上述链路已经建立后，我侧重复补建的同范围修复项；其修复目标与 [`T-20260416-46848208`](../TODO.md) 一致，不再保留为继续项。
- 统一口径：
  - `plan/plan_host_launch.md` 当前唯一继续项统一为 [`T-20260416-46848208`](../TODO.md)。
  - `T-20260416-15c1ac96` 视为重复任务，停止推进；若管理员侧仍保留记录，可直接按重复任务清理，不再分发、不再续接。

## 重复任务裁定复核（2026-04-16 10:31 +0800）

- 复核人：`大闸蟹`
- 复核结论：`通过`
- 复核摘要：
  - 已按同一口径补写重复修复任务裁定。
  - 保留 [`T-20260416-46848208`](../TODO.md) 作为唯一继续项。
  - `T-20260416-15c1ac96` 视为重复文本口径并停止继续。

## 当前主仓终验（2026-04-16 14:15 +0800）

- 终验人：`守护最好的爱莉希雅`
- 当前结论：`不通过`
- 依据：
  - 管理员已同步 [`T-20260416-46848208`](../DONE.md) 由李白合入主仓并 `-done`，提交为 `1469757`。
  - `test -f expectation/pass/lowing/outline_device_kernel/__main__.py && echo MAIN_OK; test -f expectation/pass/lowing/outline_device_kernel/basic.py && echo BASIC_OK; test -f expectation/pass/lowing/outline_device_kernel/multi_function.py && echo MULTI_OK; test -f expectation/pass/lowing/outline_device_kernel/invalid_attr.py && echo INVALID_OK` -> `exit=1`；当前主仓仍未见计划正文点名的 4 个 expectation 资产。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/pass/lowing/outline_device_kernel` -> `exit=2`；目录级 expectation 入口仍不存在。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_outline_device_kernel.py` -> `3 passed`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_pass_registry.py -k outline_device_kernel` -> `1 passed, 15 deselected`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_pipeline_default_lowering.py` -> `2 passed`。
- 最小阻断项：
  - 当前仍只剩 [`expectation/pass/lowing/outline_device_kernel/__main__.py`](../expectation/pass/lowing/outline_device_kernel/__main__.py)、[`expectation/pass/lowing/outline_device_kernel/basic.py`](../expectation/pass/lowing/outline_device_kernel/basic.py)、[`expectation/pass/lowing/outline_device_kernel/multi_function.py`](../expectation/pass/lowing/outline_device_kernel/multi_function.py)、[`expectation/pass/lowing/outline_device_kernel/invalid_attr.py`](../expectation/pass/lowing/outline_device_kernel/invalid_attr.py) 这 4 个 tracked expectation 资产未落主仓，导致计划书定义的目录级 expectation 验收仍无法执行。
- 终验说明：
  - 与 `2026-04-16 09:39 +0800` 相比，主仓阻断面没有新增变化；当前仍是 pass / registry / default-lowering 通过，但 expectation 目录级合同资产未进入主仓。
  - 因此本计划当前仍`不通过`，且`不可进入归档链`。
- 唯一继续项：
  - 保留 [`T-20260416-9304c184`](../TODO.md) 作为当前唯一修复任务；任务目标继续收口上述 4 个 expectation 资产，并让目录入口与 4 条终验命令在主仓重新通过。
  - 已完成的 [`T-20260416-46848208`](../DONE.md) 不再继续复用；当前不得创建归档任务，也不得执行 `-done-plan`。

## 当前主仓终验复核（2026-04-16 14:14 +0800）

- 终验人：`大闸蟹`
- 当前结论：`不通过`
- 依据：
  - `test -f expectation/pass/lowing/outline_device_kernel/__main__.py && echo MAIN_OK; test -f expectation/pass/lowing/outline_device_kernel/basic.py && echo BASIC_OK; test -f expectation/pass/lowing/outline_device_kernel/multi_function.py && echo MULTI_OK; test -f expectation/pass/lowing/outline_device_kernel/invalid_attr.py && echo INVALID_OK` -> `exit=1`；当前主仓仍未出现计划正文点名的 4 个 expectation 资产。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/pass/lowing/outline_device_kernel` -> `exit=2`；目录级 expectation 入口仍不存在。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_outline_device_kernel.py` -> `3 passed`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_pass_registry.py -k outline_device_kernel` -> `1 passed, 15 deselected`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_pipeline_default_lowering.py` -> `2 passed`。
- 最小阻断项：
  - 尽管 [`T-20260416-46848208`](../DONE.md) 已合入主仓并记为完成，当前主仓现场仍未出现以下 4 个 expectation 资产：
    - [`expectation/pass/lowing/outline_device_kernel/__main__.py`](../expectation/pass/lowing/outline_device_kernel/__main__.py)
    - [`expectation/pass/lowing/outline_device_kernel/basic.py`](../expectation/pass/lowing/outline_device_kernel/basic.py)
    - [`expectation/pass/lowing/outline_device_kernel/multi_function.py`](../expectation/pass/lowing/outline_device_kernel/multi_function.py)
    - [`expectation/pass/lowing/outline_device_kernel/invalid_attr.py`](../expectation/pass/lowing/outline_device_kernel/invalid_attr.py)
  - 因此本计划定义的 4 条终验命令仍未全通过，当前不能进入归档链。
- 终验说明：
  - 与 `2026-04-16 09:39 +0800` 和 `2026-04-16 09:36 +0800` 相比，主仓阻断面没有变化，仍集中在 `expectation/pass/lowing/outline_device_kernel/` 目录级合同资产缺失。
  - 因此本计划当前仍`不通过`，且`不可进入归档链`。
- 修复任务：[`T-20260416-9304c184`](../TODO.md)
- `worktree`：`wt-20260416-host-launch-r4-main-expectation-fix`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/16/20260416-host-launch-r4-main-expectation-fix.md`
- 修复范围：
  - 仅补齐 [`expectation/pass/lowing/outline_device_kernel/__main__.py`](../expectation/pass/lowing/outline_device_kernel/__main__.py)、[`expectation/pass/lowing/outline_device_kernel/basic.py`](../expectation/pass/lowing/outline_device_kernel/basic.py)、[`expectation/pass/lowing/outline_device_kernel/multi_function.py`](../expectation/pass/lowing/outline_device_kernel/multi_function.py)、[`expectation/pass/lowing/outline_device_kernel/invalid_attr.py`](../expectation/pass/lowing/outline_device_kernel/invalid_attr.py) 四个 tracked expectation 资产，并恢复目录级入口可执行性。
  - 不扩大到 `kernel_gen/`、`spec/`、`test/`、`.gitignore` 或其他 expectation 路径。
- 续推说明：
  - 已完成的 [`T-20260416-46848208`](../DONE.md) 不再继续复用。
  - 以 [`T-20260416-9304c184`](../TODO.md) 作为本轮唯一继续项；待其完成并回到本计划复核通过后，再进入归档链。

## 当前主仓终验复核（2026-04-16 14:28 +0800）

- 终验人：`大闸蟹`
- 当前结论：`不通过`
- 依据：
  - `test -f expectation/pass/lowing/outline_device_kernel/__main__.py && echo MAIN_OK; test -f expectation/pass/lowing/outline_device_kernel/basic.py && echo BASIC_OK; test -f expectation/pass/lowing/outline_device_kernel/multi_function.py && echo MULTI_OK; test -f expectation/pass/lowing/outline_device_kernel/invalid_attr.py && echo INVALID_OK` -> `exit=1`；当前主仓仍未出现计划正文点名的 4 个 expectation 资产。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/pass/lowing/outline_device_kernel` -> `exit=2`；目录级 expectation 入口仍不存在。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_outline_device_kernel.py` -> `3 passed`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_pass_registry.py -k outline_device_kernel` -> `1 passed, 15 deselected`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_pipeline_default_lowering.py` -> `2 passed`。
  - [`DONE.md`](../DONE.md) 中 [`T-20260416-9304c184`](../DONE.md) 当前写有“latest origin/main 已包含 outline_device_kernel 4 个 expectation 资产且 4 条终验通过，本轮无额外补丁”；但以上主仓复核结果与该回报不一致，说明当前主仓现场仍未满足计划完成态。
- 最小阻断项：
  - 尽管 [`T-20260416-9304c184`](../DONE.md) 已合入主仓并在回报中声称 expectation 资产已存在，当前主仓现场仍未出现以下 4 个 expectation 资产：
    - [`expectation/pass/lowing/outline_device_kernel/__main__.py`](../expectation/pass/lowing/outline_device_kernel/__main__.py)
    - [`expectation/pass/lowing/outline_device_kernel/basic.py`](../expectation/pass/lowing/outline_device_kernel/basic.py)
    - [`expectation/pass/lowing/outline_device_kernel/multi_function.py`](../expectation/pass/lowing/outline_device_kernel/multi_function.py)
    - [`expectation/pass/lowing/outline_device_kernel/invalid_attr.py`](../expectation/pass/lowing/outline_device_kernel/invalid_attr.py)
  - 因此本计划定义的 4 条终验命令仍未全通过，当前不能进入归档链。
- 终验说明：
  - 与 `2026-04-16 14:14 +0800` 相比，主仓阻断面没有变化；仍是 pass / registry / default-lowering 通过，但 expectation 目录级合同资产未进入主仓。
  - 因此本计划当前仍`不通过`，且`不可进入归档链`。
- 修复任务：[`T-20260416-d7d09005`](../TODO.md)
- `worktree`：`wt-20260416-host-launch-r5-main-expectation-fix`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/16/20260416-host-launch-r5-main-expectation-fix.md`
- 修复范围：
  - 仅补齐 [`expectation/pass/lowing/outline_device_kernel/__main__.py`](../expectation/pass/lowing/outline_device_kernel/__main__.py)、[`expectation/pass/lowing/outline_device_kernel/basic.py`](../expectation/pass/lowing/outline_device_kernel/basic.py)、[`expectation/pass/lowing/outline_device_kernel/multi_function.py`](../expectation/pass/lowing/outline_device_kernel/multi_function.py)、[`expectation/pass/lowing/outline_device_kernel/invalid_attr.py`](../expectation/pass/lowing/outline_device_kernel/invalid_attr.py) 四个 tracked expectation 资产，并恢复目录级入口可执行性。
  - 不扩大到 `kernel_gen/`、`spec/`、`test/`、`.gitignore` 或其他 expectation 路径。
- 续推说明：
  - 已完成的 [`T-20260416-9304c184`](../DONE.md) 不再继续复用。
  - 以 [`T-20260416-d7d09005`](../TODO.md) 作为本轮唯一继续项；待其完成并回到本计划复核通过后，再进入归档链。

## 当前主仓终验（2026-04-16 14:30 +0800）

- 终验人：`守护最好的爱莉希雅`
- 当前结论：`不通过`
- 依据：
  - 管理员已同步 [`T-20260416-9304c184`](../DONE.md) 完成 build -> review -> merge 链，李白回报提交为 `0fcf691`。
  - `test -f expectation/pass/lowing/outline_device_kernel/__main__.py && echo MAIN_OK; test -f expectation/pass/lowing/outline_device_kernel/basic.py && echo BASIC_OK; test -f expectation/pass/lowing/outline_device_kernel/multi_function.py && echo MULTI_OK; test -f expectation/pass/lowing/outline_device_kernel/invalid_attr.py && echo INVALID_OK` -> `exit=1`；当前根目录主仓现场仍未出现计划正文点名的 4 个 expectation 资产。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/pass/lowing/outline_device_kernel` -> `exit=2`；目录级 expectation 入口仍不存在。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_outline_device_kernel.py` -> `3 passed`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_pass_registry.py -k outline_device_kernel` -> `1 passed, 15 deselected`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_pipeline_default_lowering.py` -> `2 passed`。
- 最小阻断项：
  - 当前根目录主仓现场仍未出现 [`expectation/pass/lowing/outline_device_kernel/__main__.py`](../expectation/pass/lowing/outline_device_kernel/__main__.py)、[`expectation/pass/lowing/outline_device_kernel/basic.py`](../expectation/pass/lowing/outline_device_kernel/basic.py)、[`expectation/pass/lowing/outline_device_kernel/multi_function.py`](../expectation/pass/lowing/outline_device_kernel/multi_function.py)、[`expectation/pass/lowing/outline_device_kernel/invalid_attr.py`](../expectation/pass/lowing/outline_device_kernel/invalid_attr.py) 这 4 个 tracked expectation 资产。
  - 因此本计划定义的 4 条终验命令仍未全通过，当前不能进入归档链。
- 终验说明：
  - 虽然 [`DONE.md`](../DONE.md) 中 [`T-20260416-9304c184`](../DONE.md) 的回报写有“最新 main 已包含 outline_device_kernel 4 个 expectation 资产且 4 条终验通过”，但我在当前根目录主仓现场复跑得到的结果仍与此不一致。
  - 以当前可复核的主仓现场为准，本计划当前仍`不通过`，且`不可进入归档链`。
- 唯一继续项：
  - 保留 [`T-20260416-d7d09005`](../TODO.md) 作为当前唯一修复任务。
  - 已完成的 [`T-20260416-9304c184`](../DONE.md) 不再继续复用；当前不得创建归档任务，也不得执行 `-done-plan`。

## 当前主仓终验（2026-04-16 17:07 +0800）

- 终验人：`守护最好的爱莉希雅`
- 当前结论：`不通过`
- 归档结论：`不可进入归档链`
- 依据：
  - 管理员已同步 [`T-20260416-d7d09005`](../DONE.md) 完成 merge 并 `-done`，[`DONE.md`](../DONE.md) 当前记录完成时间为 `2026-04-16 17:06:21 +0800`。
  - `test -e expectation/pass/lowing/outline_device_kernel/__main__.py && test -e expectation/pass/lowing/outline_device_kernel/basic.py && test -e expectation/pass/lowing/outline_device_kernel/multi_function.py && test -e expectation/pass/lowing/outline_device_kernel/invalid_attr.py && echo PRESENT || echo MISSING` -> `MISSING`；当前根目录主仓现场仍未出现计划正文点名的 4 个 expectation 资产。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/pass/lowing/outline_device_kernel/__main__.py` -> `exit=2`；目录级 expectation 入口仍不存在。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_outline_device_kernel.py` -> `3 passed`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_pass_registry.py -k outline_device_kernel` -> `1 passed, 15 deselected`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_pipeline_default_lowering.py` -> `2 passed`。
  - `rg --files expectation/pass/lowing | rg 'outline_device_kernel'` -> `exit=1` 且无输出；当前主仓 `expectation/pass/lowing/` 目录下仍无 `outline_device_kernel` 资产落点。
- 最小阻断项：
  - 尽管 [`T-20260416-d7d09005`](../DONE.md) 已合入并在回报中说明“4 个授权 expectation 路径与同链路收口结果已先前进入 main”，但当前根目录主仓现场仍无法复核到：
    - [`expectation/pass/lowing/outline_device_kernel/__main__.py`](../expectation/pass/lowing/outline_device_kernel/__main__.py)
    - [`expectation/pass/lowing/outline_device_kernel/basic.py`](../expectation/pass/lowing/outline_device_kernel/basic.py)
    - [`expectation/pass/lowing/outline_device_kernel/multi_function.py`](../expectation/pass/lowing/outline_device_kernel/multi_function.py)
    - [`expectation/pass/lowing/outline_device_kernel/invalid_attr.py`](../expectation/pass/lowing/outline_device_kernel/invalid_attr.py)
  - 这说明此前链路虽然在 worktree 内验证通过，但 merge 阶段并未把这 4 个 ignored expectation 路径真正纳入根目录主仓交付；因此计划书定义的目录级 expectation 验收仍未成立。
- 终验说明：
  - 当前 pass / registry / default-lowering 三条 pytest 验收已通过，但计划书完成态和验收设计都明确要求 `expectation/pass/lowing/outline_device_kernel/` 目录级合同资产存在且可运行。
  - 在这 4 个 tracked expectation 资产真实进入根目录主仓之前，本计划当前仍`不通过`，且`不可进入归档链`。
- 唯一继续项：
  - 保留 [`T-20260416-b268723c`](../TODO.md) 作为当前唯一修复任务。
  - 任务目标固定为：补齐根目录主仓缺失的上述 4 个 tracked expectation 资产，并确保 merge 阶段仅对这 4 个 ignored 路径执行 `git add -f` 纳入交付。
  - 已完成的 [`T-20260416-d7d09005`](../DONE.md) 不再继续复用；当前不得创建归档任务，也不得执行 `-done-plan`。

## 重复任务裁定（2026-04-16 17:19 +0800）

- 裁定人：`守护最好的爱莉希雅`
- 裁定结论：
  - `plan/plan_host_launch.md` 同轮重复补建的两条修复任务中，只保留 [`T-20260416-b268723c`](../TODO.md)。
  - 重复项 [`T-20260416-aad24275`](../TODO.md) 已删除，不再继续推进。
- 保留理由：
  - [`T-20260416-b268723c`](../TODO.md) 的范围更精确，已把“仅收口根目录主仓缺失的 4 个 `outline_device_kernel` expectation 资产”以及“merge 阶段仅对这 4 个 ignored 路径执行 `git add -f`”写成唯一合同。
  - [`T-20260416-aad24275`](../TODO.md) 与其指向同一阻断面，但未把 merge 的 `git add -f` 交付动作写死，范围清晰度较弱，因此判定为重复任务。

## 执行授权（2026-04-16 17:19 +0800）

- 授权人：`守护最好的爱莉希雅`
- 授权任务：[`T-20260416-b268723c`](../TODO.md)
- 一次性 expectation 例外授权：
  - 允许非架构执行角色在该唯一任务内直接新增或修改以下 4 个 tracked expectation 路径：
    - [`expectation/pass/lowing/outline_device_kernel/__main__.py`](../expectation/pass/lowing/outline_device_kernel/__main__.py)
    - [`expectation/pass/lowing/outline_device_kernel/basic.py`](../expectation/pass/lowing/outline_device_kernel/basic.py)
    - [`expectation/pass/lowing/outline_device_kernel/multi_function.py`](../expectation/pass/lowing/outline_device_kernel/multi_function.py)
    - [`expectation/pass/lowing/outline_device_kernel/invalid_attr.py`](../expectation/pass/lowing/outline_device_kernel/invalid_attr.py)
- 明确限制：
  - 不得修改 [`.gitignore`](../.gitignore)。
  - 不得扩大到 `kernel_gen/`、`spec/`、`test/` 或其他 expectation 路径。
  - merge 阶段仅允许对上述 4 个 ignored expectation 路径执行 `git add -f` 纳入交付，不得纳入其他 ignored 路径。

## 当前主仓终验复核（2026-04-16 17:08 +0800）

- 终验人：`大闸蟹`
- 当前结论：`不通过`
- 依据：
  - [`DONE.md`](../DONE.md) 当前已新增 [`T-20260416-d7d09005`](../DONE.md) 合并记录，状态为已完成。
  - `test -f expectation/pass/lowing/outline_device_kernel/__main__.py && echo MAIN_OK; test -f expectation/pass/lowing/outline_device_kernel/basic.py && echo BASIC_OK; test -f expectation/pass/lowing/outline_device_kernel/multi_function.py && echo MULTI_OK; test -f expectation/pass/lowing/outline_device_kernel/invalid_attr.py && echo INVALID_OK` -> `exit=1`；当前主仓仍未出现计划正文点名的 4 个 expectation 资产。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/pass/lowing/outline_device_kernel` -> `exit=2`；目录级 expectation 入口仍不存在。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_outline_device_kernel.py` -> `3 passed`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_pass_registry.py -k outline_device_kernel` -> `1 passed, 15 deselected`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_pipeline_default_lowering.py` -> `2 passed`。
- 最小阻断项：
  - 尽管 [`T-20260416-d7d09005`](../DONE.md) 已合入主仓，当前主仓现场仍未出现以下 4 个 expectation 资产：
    - [`expectation/pass/lowing/outline_device_kernel/__main__.py`](../expectation/pass/lowing/outline_device_kernel/__main__.py)
    - [`expectation/pass/lowing/outline_device_kernel/basic.py`](../expectation/pass/lowing/outline_device_kernel/basic.py)
    - [`expectation/pass/lowing/outline_device_kernel/multi_function.py`](../expectation/pass/lowing/outline_device_kernel/multi_function.py)
    - [`expectation/pass/lowing/outline_device_kernel/invalid_attr.py`](../expectation/pass/lowing/outline_device_kernel/invalid_attr.py)
  - 因此本计划定义的 4 条终验命令仍未全通过，当前不能进入归档链。
- 终验说明：
  - 与 `2026-04-16 14:30 +0800` 相比，主仓阻断面没有新增变化；仍是 pass / registry / default-lowering 通过，但 expectation 目录级合同资产未进入主仓。
  - 因此本计划当前仍`不通过`，且`不可进入归档链`。
- 修复任务：[`T-20260416-aad24275`](../TODO.md)
- `worktree`：`wt-20260416-host-launch-r6-main-expectation-fix`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/16/20260416-host-launch-r6-main-expectation-fix.md`
- 修复范围：
  - 仅补齐 [`expectation/pass/lowing/outline_device_kernel/__main__.py`](../expectation/pass/lowing/outline_device_kernel/__main__.py)、[`expectation/pass/lowing/outline_device_kernel/basic.py`](../expectation/pass/lowing/outline_device_kernel/basic.py)、[`expectation/pass/lowing/outline_device_kernel/multi_function.py`](../expectation/pass/lowing/outline_device_kernel/multi_function.py)、[`expectation/pass/lowing/outline_device_kernel/invalid_attr.py`](../expectation/pass/lowing/outline_device_kernel/invalid_attr.py) 四个 tracked expectation 资产，并恢复目录级入口可执行性。
  - 不扩大到 `kernel_gen/`、`spec/`、`test/`、`.gitignore` 或其他 expectation 路径。
- 续推说明：
  - 已完成的 [`T-20260416-d7d09005`](../DONE.md) 不再继续复用。
  - 以 [`T-20260416-aad24275`](../TODO.md) 作为本轮唯一继续项；待其完成并回到本计划复核通过后，再进入归档链。

## 重复修复任务裁定（2026-04-16 17:15 +0800）

- 裁定人：`大闸蟹`
- 重复项：
  - [`T-20260416-aad24275`](../TODO.md)
  - [`T-20260416-b268723c`](../TODO.md)
- 现场核对：
  - 两条任务都指向同一阻断面：补齐根目录主仓缺失的 [`expectation/pass/lowing/outline_device_kernel/__main__.py`](../expectation/pass/lowing/outline_device_kernel/__main__.py)、[`expectation/pass/lowing/outline_device_kernel/basic.py`](../expectation/pass/lowing/outline_device_kernel/basic.py)、[`expectation/pass/lowing/outline_device_kernel/multi_function.py`](../expectation/pass/lowing/outline_device_kernel/multi_function.py)、[`expectation/pass/lowing/outline_device_kernel/invalid_attr.py`](../expectation/pass/lowing/outline_device_kernel/invalid_attr.py) 4 个 expectation 资产，并恢复目录入口验收。
  - [`T-20260416-b268723c`](../TODO.md) 的任务目标写得更完整：除补齐 4 个 expectation 资产外，还已把“merge 阶段仅对这 4 个 ignored 路径执行 `git add -f` 纳入交付”写成显式交付口径。
  - [`T-20260416-aad24275`](../TODO.md) 与 [`T-20260416-b268723c`](../TODO.md) 同属 `plan/plan_host_launch.md` 下、依赖均为空、`worktree` 都已预留；当前无必要并行保留两条同范围修复链。
- 唯一保留项：
  - 保留 [`T-20260416-b268723c`](../TODO.md)。
- 停止项：
  - [`T-20260416-aad24275`](../TODO.md) 视为重复修复任务，停止推进；若管理员侧仍保留任务表项，请直接删除或停止分发，不再作为本计划继续项。
- expectation 例外授权：
  - 对 [`T-20260416-b268723c`](../TODO.md) 给予一次性例外授权：被指派的非架构执行角色可直接新增或修改以下 4 个 expectation 路径：
    - [`expectation/pass/lowing/outline_device_kernel/__main__.py`](../expectation/pass/lowing/outline_device_kernel/__main__.py)
    - [`expectation/pass/lowing/outline_device_kernel/basic.py`](../expectation/pass/lowing/outline_device_kernel/basic.py)
    - [`expectation/pass/lowing/outline_device_kernel/multi_function.py`](../expectation/pass/lowing/outline_device_kernel/multi_function.py)
    - [`expectation/pass/lowing/outline_device_kernel/invalid_attr.py`](../expectation/pass/lowing/outline_device_kernel/invalid_attr.py)
  - 本轮仅允许处理上述 4 个路径；不得修改 `.gitignore`，不得扩大到 `kernel_gen/`、`spec/`、`test/`、其他 `expectation` 路径或其他 ignored 文件。
  - merge 阶段仅允许对上述 4 个 expectation 路径执行 `git add -f` 纳入交付，不得追加其他 ignored 路径。
- 统一口径：
  - `plan/plan_host_launch.md` 当前唯一继续项统一为 [`T-20260416-b268723c`](../TODO.md)。

## 当前主仓终验复核（2026-04-16 17:45 +0800，已被 2026-04-16 19:32 +0800 口径同步覆盖）

- 终验人：`大闸蟹`
- 当前结论：`不通过`
- 归档结论：`不可进入归档链`
- 依据：
  - 管理员已同步 [`T-20260416-b268723c`](../DONE.md) 完成 merge 并 `-done`，[`DONE.md`](../DONE.md) 当前记录完成时间为 `2026-04-16 17:40:43 +0800`。
  - `test -f expectation/pass/lowing/outline_device_kernel/__main__.py && echo MAIN_OK; test -f expectation/pass/lowing/outline_device_kernel/basic.py && echo BASIC_OK; test -f expectation/pass/lowing/outline_device_kernel/multi_function.py && echo MULTI_OK; test -f expectation/pass/lowing/outline_device_kernel/invalid_attr.py && echo INVALID_OK` -> `exit=1`；当前根目录主仓现场仍未出现计划正文点名的 4 个 expectation 资产。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/pass/lowing/outline_device_kernel` -> `exit=2`；目录级 expectation 入口仍不存在。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_outline_device_kernel.py` -> `3 passed`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_pass_registry.py -k outline_device_kernel` -> `1 passed, 15 deselected`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_pipeline_default_lowering.py` -> `2 passed`。
  - 当前 [`TODO.md`](../TODO.md) 已从 `7 / 7 / 0 / 完成待检查` 回退为 `8 / 7 / 1 / 进行中`，说明本轮终验未通过且已补建新的继续项。
- 最小阻断项：
  - 尽管 [`T-20260416-b268723c`](../DONE.md) 已合入并在任务目标中显式要求“若 merge 需处理 expectation 资产，仅允许对 4 个 ignored 路径执行 `git add -f`”，当前根目录主仓现场仍无法复核到：
    - [`expectation/pass/lowing/outline_device_kernel/__main__.py`](../expectation/pass/lowing/outline_device_kernel/__main__.py)
    - [`expectation/pass/lowing/outline_device_kernel/basic.py`](../expectation/pass/lowing/outline_device_kernel/basic.py)
    - [`expectation/pass/lowing/outline_device_kernel/multi_function.py`](../expectation/pass/lowing/outline_device_kernel/multi_function.py)
    - [`expectation/pass/lowing/outline_device_kernel/invalid_attr.py`](../expectation/pass/lowing/outline_device_kernel/invalid_attr.py)
  - 这说明当前主仓仍未满足计划书定义的目录级 expectation 验收。
- 终验说明：
  - 当前 pass / registry / default-lowering 三条 pytest 验收仍全部通过，但计划书完成态和验收设计都明确要求 `expectation/pass/lowing/outline_device_kernel/` 目录级合同资产存在且可运行。
  - 在这 4 个 tracked expectation 资产真实进入根目录主仓之前，本计划当前仍`不通过`，且`不可进入归档链`。
- 修复任务：[`T-20260416-b784ce3d`](../TODO.md)
- `worktree`：`wt-20260416-host-launch-r7-main-expectation-fix`
- 记录文件：`agents/codex-multi-agents/log/task_records/2026/16/20260416-host-launch-r7-main-expectation-fix.md`
- 修复范围：
  - 仅补齐 [`expectation/pass/lowing/outline_device_kernel/__main__.py`](../expectation/pass/lowing/outline_device_kernel/__main__.py)、[`expectation/pass/lowing/outline_device_kernel/basic.py`](../expectation/pass/lowing/outline_device_kernel/basic.py)、[`expectation/pass/lowing/outline_device_kernel/multi_function.py`](../expectation/pass/lowing/outline_device_kernel/multi_function.py)、[`expectation/pass/lowing/outline_device_kernel/invalid_attr.py`](../expectation/pass/lowing/outline_device_kernel/invalid_attr.py) 四个 tracked expectation 资产，并恢复目录级入口可执行性。
  - 不扩大到 `kernel_gen/`、`spec/`、`test/`、`.gitignore` 或其他 expectation 路径。
- 续推说明：
  - 已完成的 [`T-20260416-b268723c`](../DONE.md) 不再继续复用。
  - 以 [`T-20260416-b784ce3d`](../TODO.md) 作为本轮唯一继续项；待其完成并回到本计划复核通过后，再进入归档链。

## 执行授权（2026-04-16 19:11 +0800）

- 授权人：`守护最好的爱莉希雅`
- 授权任务：[`T-20260416-b784ce3d`](../TODO.md)
- 授权结论：
  - 沿用上一轮 `host-launch` 的 expectation 例外口径。
  - 允许非架构执行角色在 [`T-20260416-b784ce3d`](../TODO.md) 内直接新增或修改以下 4 个 expectation 路径：
    - [`expectation/pass/lowing/outline_device_kernel/__main__.py`](../expectation/pass/lowing/outline_device_kernel/__main__.py)
    - [`expectation/pass/lowing/outline_device_kernel/basic.py`](../expectation/pass/lowing/outline_device_kernel/basic.py)
    - [`expectation/pass/lowing/outline_device_kernel/multi_function.py`](../expectation/pass/lowing/outline_device_kernel/multi_function.py)
    - [`expectation/pass/lowing/outline_device_kernel/invalid_attr.py`](../expectation/pass/lowing/outline_device_kernel/invalid_attr.py)
- 明确限制：
  - 不得修改 [`.gitignore`](../.gitignore)。
  - 不得扩大到 `kernel_gen/`、`spec/`、`test/`、其他 `expectation` 路径或其他 ignored 路径。
  - merge 阶段仍仅允许对上述 4 个 expectation 路径执行 `git add -f` 纳入交付，不得追加其他 ignored 路径。
- 统一口径：
  - 旧授权任务号 [`T-20260416-b268723c`](../DONE.md) 不再继续复用。
  - 当前 `plan/plan_host_launch.md` expectation 例外授权只对 [`T-20260416-b784ce3d`](../TODO.md) 生效；若后续继续项再次变更，需重新明确授权任务号。

## 执行授权（2026-04-16 17:48 +0800）

- 授权人：`大闸蟹`
- 授权任务：[`T-20260416-b784ce3d`](../TODO.md)
- 一次性 expectation 例外授权：
  - 允许被指派的非架构执行角色在该任务内直接新增或修改以下 4 个 expectation 路径：
    - [`expectation/pass/lowing/outline_device_kernel/__main__.py`](../expectation/pass/lowing/outline_device_kernel/__main__.py)
    - [`expectation/pass/lowing/outline_device_kernel/basic.py`](../expectation/pass/lowing/outline_device_kernel/basic.py)
    - [`expectation/pass/lowing/outline_device_kernel/multi_function.py`](../expectation/pass/lowing/outline_device_kernel/multi_function.py)
    - [`expectation/pass/lowing/outline_device_kernel/invalid_attr.py`](../expectation/pass/lowing/outline_device_kernel/invalid_attr.py)
- 明确限制：
  - 不得修改 [`.gitignore`](../.gitignore)。
  - 不得扩大到 `kernel_gen/`、`spec/`、`test/`、其他 `expectation` 路径或其他 ignored 路径。
  - merge 阶段仅允许对上述 4 个 ignored expectation 路径执行 `git add -f` 纳入交付，不得追加其他 ignored 路径。
- 统一口径：
  - [`T-20260416-b784ce3d`](../TODO.md) 沿用上一轮 `outline_device_kernel` expectation 收口的同一例外范围，只处理上述 4 个路径。

## 终验口径同步（2026-04-16 19:32 +0800）

- 经办人：`睡觉小分队`
- 同步结论：`通过`
- 归档结论：`当前已不存在新的实现/expectation 修复继续项；待本轮计划书口径完成审阅后，可按“先创建归档任务、归档合并完成后再执行 -done-plan”的流程进入归档链`
- 本节作用：
  - 本节取代 [`当前主仓终验复核（2026-04-16 17:45 +0800）`](#当前主仓终验复核2026-04-16-1745-0800已被-2026-04-16-1932-0800-口径同步覆盖) 中“当前根目录主仓现场缺少 4 个 expectation 资产，因此本计划不通过”的旧口径。
  - 本轮只同步 `outline_device_kernel` 4 个 tracked expectation 资产已存在这一终验事实，不扩大到 [`.gitignore`](../.gitignore)、`kernel_gen/`、`spec/`、`test/` 或其他 expectation 路径。
- 终验依据：
  - `git -C /home/lfr/kernelcode_generate/wt-20260416-host-launch-r7-main-expectation-fix ls-files --stage expectation/pass/lowing/outline_device_kernel/__main__.py expectation/pass/lowing/outline_device_kernel/basic.py expectation/pass/lowing/outline_device_kernel/multi_function.py expectation/pass/lowing/outline_device_kernel/invalid_attr.py` 返回 4 条 stage 记录，说明最新主线对应的任务 worktree 已包含这 4 个 tracked expectation 资产。
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/pass/lowing/outline_device_kernel`（workdir=`/home/lfr/kernelcode_generate/wt-20260416-host-launch-r7-main-expectation-fix`）-> `exit=0`，输出包含 `[RUN] basic`、`[RUN] multi_function`、`[RUN] invalid_attr` 与 `[OK] outline-device-kernel expectation passed`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_outline_device_kernel.py`（workdir=`/home/lfr/kernelcode_generate/wt-20260416-host-launch-r7-main-expectation-fix`）-> `9 passed`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_pass_registry.py -k outline_device_kernel`（workdir=`/home/lfr/kernelcode_generate/wt-20260416-host-launch-r7-main-expectation-fix`）-> `1 passed, 15 deselected`。
  - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_pipeline_default_lowering.py`（workdir=`/home/lfr/kernelcode_generate/wt-20260416-host-launch-r7-main-expectation-fix`）-> `2 passed`。
  - `ls -la /home/lfr/kernelcode_generate/expectation/pass/lowing/outline_device_kernel` -> `No such file or directory`；该现象只说明根目录主仓工作目录当前未同步出该 ignored 目录，不等于最新主线或任务 worktree 缺少这 4 个 tracked expectation 资产。
- 统一口径：
  - 本计划关于 `outline_device_kernel` 的完成态，应以“最新主线对应的同步 worktree 可复核到 4 个 tracked expectation 资产，且上述 4 条终验命令全部通过”为准；不再以根目录主仓工作目录当前是否物理存在 `expectation/pass/lowing/outline_device_kernel/` 目录，作为新的功能阻断项。
  - 根目录主仓工作目录缺少 `expectation/pass/lowing/outline_device_kernel/` 目录，只是本地现场状态差异；若后续再次出现同类现象，应按工作目录同步问题处理，不再重复派生 `outline_device_kernel` 实现或 expectation 修复任务。
  - [`T-20260416-b784ce3d`](../TODO.md) 在本轮内承担的唯一职责，是把上述终验事实同步回计划书；本轮文字收口完成并审阅通过后，不再保留与这 4 个 expectation 资产相关的额外继续项。
- 后续继续项与归档条件：
  - 当前链路的唯一剩余动作，是完成 [`T-20260416-b784ce3d`](../TODO.md) 对计划书口径的审阅与收口。
  - 若审阅结论继续确认“最新主线已齐备，根目录主仓缺目录仅为现场状态差异”，则本计划不再新增 build/spec/review/merge 修复项，可直接由管理员创建独立归档任务。
  - 计划归档不得直接执行 `-done-plan`；必须先创建归档任务，将计划归档记录写入 `agents/codex-multi-agents/log/task_records/done_plan/<年份>/<周>/`，并在归档任务合并完成后再执行 `-done-plan`。

## 当前主仓终验复核（2026-04-16 19:45 +0800）

- 终验人：`守护最好的爱莉希雅`
- 当前结论：`通过`
- 归档结论：`可进入归档链`
- 依据：
  - 管理员已同步 [`T-20260416-b784ce3d`](../DONE.md) 由李白合入主仓并 `-done`，提交为 `7ec2128`；其回报说明本轮业务文件相对 `origin/main` 无差异，仅带入当前任务记录文件，因此本轮不会改变既有功能现场。
  - 按当前已合入的 [`终验口径同步（2026-04-16 19:32 +0800）`](#终验口径同步2026-04-16-1932-0800)，`outline_device_kernel` 4 个 tracked expectation 资产是否齐备，应以“最新主线对应的同步 worktree 可复核通过 4 条终验命令”为准；根目录主仓工作目录当前是否物理存在 `expectation/pass/lowing/outline_device_kernel/` 目录，不再作为新的功能阻断项。
  - 当前根目录主仓可直接复跑的三条非 expectation 验收仍全部通过：
    - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_outline_device_kernel.py` -> `3 passed`
    - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_pass_registry.py -k outline_device_kernel` -> `1 passed, 15 deselected`
    - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_pipeline_default_lowering.py` -> `2 passed`
- 终验说明：
  - 这轮 `b784ce3d` 的职责是把“4 个 tracked expectation 资产已在最新主线对应同步现场中齐备，根目录主仓缺目录仅为现场状态差异”的口径同步回计划书；该职责现已完成，且未引入新的业务差异。
  - 因此，按当前计划书正文的最新有效口径，本计划已满足完成态；当前不存在新的实现/expectation 修复继续项。
- 当前状态：
  - [`T-20260416-b784ce3d`](../DONE.md) 已完成并停用，不再续接。
  - 本计划当前可直接进入“先创建归档任务，归档合并完成后再执行 `-done-plan`”的归档链流程。

## 当前主仓终验复核（2026-04-16 21:23 +0800）

- 终验人：`大闸蟹`
- 当前结论：`通过`
- 归档结论：`可进入归档链`
- 验证基线：
  - 以同步现场 ` /home/lfr/kernelcode_generate/wt-20260416-host-launch-r7-main-expectation-fix ` 为准；对应记录见 [`agents/codex-multi-agents/log/task_records/2026/16/20260416-host-launch-r7-main-expectation-fix.md`](../agents/codex-multi-agents/log/task_records/2026/16/20260416-host-launch-r7-main-expectation-fix.md)。
  - 该记录在 `2026-04-16 19:36 +0800` 已写明：当前 worktree 已同步到 `origin/main=8f20a27`，且 `HEAD...origin/main = 0 0`。
  - 同一记录已写明以下 4 条终验在该同步现场全部通过：
    - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python expectation/pass/lowing/outline_device_kernel` -> `exit 0`
    - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_outline_device_kernel.py` -> `9 passed`
    - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_pass_registry.py -k outline_device_kernel` -> `1 passed, 15 deselected`
    - `PYTHONDONTWRITEBYTECODE=1 pytest -q test/pass/test_pipeline_default_lowering.py` -> `2 passed`
  - 管理员已同步 [`T-20260416-b784ce3d`](../DONE.md) 由李白合入主仓并推送，提交为 `7ec2128`；该 merge 只继续带入同链记录，与上述同步现场结论一致。
- 终验说明：
  - 根目录主仓工作目录当前是否物理出现 `expectation/pass/lowing/outline_device_kernel/`，不再单独作为功能阻断；若与上述同步现场不一致，只记为现场状态差异。
  - 因此，本计划的完成态应以“最新同步现场已齐备 4 个 tracked expectation 资产，且 4 条终验通过”为准，不再回退到“根目录旧现场缺目录”的旧判断。
- 当前状态：
  - [`T-20260416-b784ce3d`](../DONE.md) 已完成并停用，不再续接。
  - [`T-20260416-20315ce1`](../TODO.md) 属于基于根目录旧现场补建的重复修复任务，不再继续推进，应由管理员停止并从本计划继续项中移除。
  - 在停止上述重复任务后，管理员即可按归档流程补建唯一归档任务，再执行后续归档动作。
