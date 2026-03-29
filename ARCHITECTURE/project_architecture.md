# project_architecture.md

## 功能简介

- 定义仓库级架构总览，说明项目目标、主链路、模块边界与交接契约。
- 区分“产品代码主链路”和“协作/计划基础设施”，避免将脚本、agents、worktree 误读为产品能力的一部分。
- 为后续专题计划文档提供稳定背景；不在本文档中承载单一专题的实施细节。

## 执行摘要

1. 这个项目的目标是：用户写 DSL/Python，仓库在受支持范围内把它转成高层语义、可校验 IR，或进一步转成 CPU C/C++ 源码字符串。
2. 当前仓库不是一条天然全通的统一流水线，而是“多条局部链路并存”。
3. 代码层只看 `spec/`、`kernel_gen/`、`include/`、`test/`、`expectation/`；不要把 `agents/`、`TODO.md`、`wt-*` 误判为产品架构。
4. `ARCHITECTURE/project_architecture.md` 解释“项目是什么、链路到哪里”；[`ARCHITECTURE/plan`](plan) 解释“某个目标怎么推进”。
5. `operation` 是算子语义唯一来源；若 shape、dtype、错误边界变化，应先改 `spec/operation/* + kernel_gen/operation/* + test/operation/*`。
6. `dsl/ast -> ast_visitor -> emit_mlir/mlir_gen` 是 DSL 前端 lowering；`emit_c/gen_kernel` 是 DSL 代码生成 backend；两者不能混写职责。
7. `mlir_gen` 仅接受函数形参和函数体内可达值；不允许外部值隐式捕获。
8. `passes` 只消费受限 IR 子集，例如 `nn_to_kernel` 只处理少量 `nn` op；它不是所有 dialect 的统一中转站。
9. `emit_c/gen_kernel` 也只接受受控 IR 子集；当前并不意味着所有高层 `nn` 算子都能直接生成 CPU 代码。
10. `conv/img2col` 目前仍主要停留在高层语义层；若要实现 CPU tiled codegen，必须作为专题链路单独推进，而不是假设仓库已经天然串通。

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`大闸蟹`
- `文档`：[`ARCHITECTURE/project_architecture.md`](project_architecture.md)
- `功能实现`：
  - [`kernel_gen/symbol_variable/memory.py`](../kernel_gen/symbol_variable/memory.py)
  - [`kernel_gen/operation/nn.py`](../kernel_gen/operation/nn.py)
  - [`kernel_gen/operation/arch.py`](../kernel_gen/operation/arch.py)
  - [`kernel_gen/dialect/kernel.py`](../kernel_gen/dialect/kernel.py)
  - [`kernel_gen/passes/pass_manager.py`](../kernel_gen/passes/pass_manager.py)
  - [`kernel_gen/passes/lowing/nn_to_kernel.py`](../kernel_gen/passes/lowing/nn_to_kernel.py)
  - [`kernel_gen/dsl/ast.py`](../kernel_gen/dsl/ast.py)
  - [`kernel_gen/dsl/ast_visitor.py`](../kernel_gen/dsl/ast_visitor.py)
  - [`kernel_gen/dsl/emit_mlir.py`](../kernel_gen/dsl/emit_mlir.py)
  - [`kernel_gen/dsl/mlir_gen.py`](../kernel_gen/dsl/mlir_gen.py)
  - [`kernel_gen/dsl/emit_c.py`](../kernel_gen/dsl/emit_c.py)
  - [`kernel_gen/dsl/gen_kernel.py`](../kernel_gen/dsl/gen_kernel.py)
  - [`kernel_gen/target/registry.py`](../kernel_gen/target/registry.py)
  - [`include/cpu/Memory.h`](../include/cpu/Memory.h)
  - [`include/cpu/Nn.h`](../include/cpu/Nn.h)
- `test`：
  - [`test/symbol_variable/test_memory.py`](../test/symbol_variable/test_memory.py)
  - [`test/operation/test_operation_nn.py`](../test/operation/test_operation_nn.py)
  - [`test/operation/test_operation_arch.py`](../test/operation/test_operation_arch.py)
  - [`test/dialect/test_kernel_dialect.py`](../test/dialect/test_kernel_dialect.py)
  - [`test/pass/test_pass_manager.py`](../test/pass/test_pass_manager.py)
  - [`test/pass/test_lowing_nn_to_kernel.py`](../test/pass/test_lowing_nn_to_kernel.py)
  - [`test/dsl/test_ast.py`](../test/dsl/test_ast.py)
  - [`test/dsl/test_ast_visitor.py`](../test/dsl/test_ast_visitor.py)
  - [`test/dsl/test_emit_mlir.py`](../test/dsl/test_emit_mlir.py)
  - [`test/dsl/test_mlir_gen.py`](../test/dsl/test_mlir_gen.py)
  - [`test/dsl/test_emit_c.py`](../test/dsl/test_emit_c.py)
  - [`test/dsl/test_gen_kernel.py`](../test/dsl/test_gen_kernel.py)
  - [`test/target/test_target_registry.py`](../test/target/test_target_registry.py)
  - [`test/include/cpu/test_memory.py`](../test/include/cpu/test_memory.py)
  - [`test/include/cpu/test_nn.py`](../test/include/cpu/test_nn.py)

## 依赖

- [`spec/symbol_variable/memory.md`](../spec/symbol_variable/memory.md)：`Memory` / `SymbolDim` / `SymbolShape` 的基础语义。
- [`spec/operation/nn.md`](../spec/operation/nn.md)：高层算子语义、输出元信息与错误边界。
- [`spec/operation/arch.md`](../spec/operation/arch.md)：`arch` helper 的高层调用语义。
- [`spec/dialect/kernel.md`](../spec/dialect/kernel.md)：执行步骤级 IR 的职责边界。
- [`spec/dialect/arch.md`](../spec/dialect/arch.md)：`arch` 方言 IR 语义与 verifier 规则。
- [`spec/pass/pass_manager.md`](../spec/pass/pass_manager.md)：pass 容器与执行顺序约束。
- [`spec/pass/lowing/nn_to_kernel.md`](../spec/pass/lowing/nn_to_kernel.md)：当前 `nn -> kernel` lowering 的公开范围。
- [`spec/dsl/ast.md`](../spec/dsl/ast.md)：DSL AST 节点语义。
- [`spec/dsl/ast_visitor.md`](../spec/dsl/ast_visitor.md)：Python AST 到 DSL AST 的访问规则。
- [`spec/dsl/emit_mlir.md`](../spec/dsl/emit_mlir.md)：DSL AST 到 MLIR 片段的发射规则。
- [`spec/dsl/mlir_gen.md`](../spec/dsl/mlir_gen.md)：DSL 到 `func.func` 入口契约。
- [`spec/dsl/emit_c.md`](../spec/dsl/emit_c.md)：节点级 C/C++ 片段生成边界。
- [`spec/dsl/gen_kernel.md`](../spec/dsl/gen_kernel.md)：函数级源码生成边界。
- [`spec/analysis/analysis_kernel.md`](../spec/analysis/analysis_kernel.md)：静态分析层职责。
- [`spec/target/registry.md`](../spec/target/registry.md)：target 能力与硬件参数注册中心。
- [`spec/include/cpu/cpu.md`](../spec/include/cpu/cpu.md)：CPU 运行时头文件接口边界。

## 项目目标

- 让用户以 DSL/Python 方式描述算子、kernel 或局部执行逻辑。
- 在不同抽象层表达这些语义：高层 `Memory` 语义、可校验 IR、函数级 MLIR、目标后端源码和运行时接口。
- 在当前受支持范围内，把 DSL 子集生成为 CPU C/C++ 源码字符串，或把部分高层 `nn` IR lower 为更低层的 `kernel/dma` IR。
- 通过 `spec -> 实现 -> test` 的映射控制演进节奏，使新能力能按模块边界逐层推进，而不是在单层夹带全部逻辑。

## 非目标

- 本文档不定义单一专题的阶段计划、里程碑或验收项；这些统一放在 [`ARCHITECTURE/plan`](plan) 下。
- 本文档不把“目录已经存在”表述成“能力已经端到端打通”。
- 本文档不替代各子模块 spec，不定义具体算子的实现细节、性能策略或模板细节。
- 本文档不承诺完整编译驱动、链接、运行时调度或全自动优化流水线；当前覆盖范围以对应 spec 和测试为准。
- 协作基础设施层不定义业务语义、不作为产品实现依赖、不直接进入编译产物或代码生成链路。

## 术语

- `语义层`：用 `Memory`、`SymbolDim`、`SymbolShape` 等对象表达算子含义与元信息，不关心具体 IR 或代码模板。
- `IR / dialect 层`：用可校验的 op、type、attribute 表达执行步骤与数据流，强调 verifier 与 lowering 合法性。
- `DSL 前端层`：把用户写的 DSL/Python 函数解析成 AST，再发射为 `func.func` 和相关 dialect op。
- `代码生成层`：把受支持的 MLIR/IR 子集生成目标后端源码字符串。
- `运行时层`：目标后端头文件、数据视图和辅助接口，承接生成代码依赖的底层 API。
- `协作基础设施层`：任务脚本、agents、worktree、TODO/DONE 等支撑协作与审计的仓库内容，不直接构成产品主链路。
- `计划文档`：放在 [`ARCHITECTURE/plan`](plan) 下的专题推进文档，只讨论某个具体目标、阶段和验收。

## 三层总览

| 层级 | 代表目录 / 文件 | 是否进入产品产物链路 | 主要作用 | 常见误用 |
| --- | --- | --- | --- | --- |
| 代码层 | `spec/`、`kernel_gen/`、`include/`、`test/`、`expectation/` | 是；`test/expectation` 负责验证代码层 | 定义契约、实现语义/IR/codegen/runtime，并验证这些能力 | 把阶段计划或任务流程写进 spec / 实现 / 测试 |
| 协作基础设施层 | `agents/`、`skills/`、`script/`、`TODO.md`、`DONE.md`、`agents/.../task_records`、`wt-*` | 否 | 承担任务分发、审计、记录、worktree 协作和脚本支撑 | 把协作脚本、任务状态或 worktree 结构当成产品架构的一部分 |
| 计划文档层 | [`ARCHITECTURE/plan`](plan) | 否 | 承担专题目标、范围、阶段、风险和验收 | 把专题计划回写成项目总览或替代模块 spec |

## 仓库内容分区

### 产品代码与契约

- [`spec`](../spec)：公开契约源头，定义边界、错误规则和测试目标。
- [`kernel_gen`](../kernel_gen)：产品主实现，覆盖语义层、IR 层、DSL 前端、代码生成、分析与 target 查询。
- [`include`](../include)：生成代码依赖的 CPU 头文件接口。
- [`test`](../test)：针对各层 spec 的单元测试。
- [`expectation`](../expectation)：贴近产品链路的脚本化验收样例，用于检查关键路径是否仍可执行。

### 验收与协作基础设施

- [`ARCHITECTURE`](.): 项目总览与专题计划文档。
- `agents/`、`skills/`、`script/`、`TODO.md`、`DONE.md`、`agents/.../task_records`、`wt-*`：协作、分发、记录、审计与 worktree 基础设施，不属于产品能力本身，也不进入产品产物链路。

## 仓库级端到端视图

### 链路 A：高层语义与 IR 合法化

```text
Memory / SymbolDim / SymbolShape
  -> kernel_gen/operation/*
  -> kernel_gen/dialect/*
  -> kernel_gen/passes/*
  -> 合法化后的 kernel / dma / func IR
```

- 输入产物：高层 `Memory` 语义对象，或已构造的 `nn/arch/dma/...` dialect IR。
- 输出产物：更低层、可校验、可继续被 pass 处理的 IR。
- 当前断点：这条链路的输出是 IR，不是 C/C++ 源码；高层 `operation` 能力不会自动进入 `emit_c/gen_kernel`。

### 链路 B：DSL 到 CPU 源码生成

```text
Python / DSL 函数
  -> kernel_gen/dsl/ast.py
  -> kernel_gen/dsl/ast_visitor.py
  -> kernel_gen/dsl/emit_mlir.py + mlir_gen.py
  -> func.func + 相关 dialect op
  -> kernel_gen/dsl/emit_c.py + gen_kernel.py
  -> CPU C/C++ 源码字符串
  -> include/cpu/*.h 运行时接口
```

- 输入产物：用户 DSL/Python 函数或 DSL AST。
- 输出产物：目标后端函数源码字符串。
- 当前断点：代码生成只覆盖已在 `emit_c/gen_kernel` spec 与测试中列出的受控子集，不等于“所有高层 `nn` 算子都能直接出代码”。
- target gating：当前这条链路以 CPU 为已支持目标；若 IR 或 value 只在 `target=cpu` 下有定义，则非 CPU 目标必须明确报错，不能静默降级。

### 侧向支撑链路：target 与 runtime

```text
kernel_gen/target/targets/*.json|*.txt
  -> kernel_gen/target/registry.py
  -> operation/arch 与 dialect/arch 读取能力或硬件参数
  -> include/cpu/*.h 为生成代码提供运行时接口
```

- `target/registry` 只负责解析与查询，不负责业务回退逻辑。
- `operation/arch` 可优先读取静态硬件值；缺失时按各自 spec 回退为符号语义或动态语义。
- `dialect/arch` verifier 可根据当前 target 校验 op 是否允许出现。

## 未打通声明

- 当前仓库不存在 canonical 的统一主流水线：`DSL -> dialect -> passes -> emit_c/gen_kernel -> runtime`。
- DSL 前端会直接产出一部分 `func/dma/arch/symbol/...` 相关 op；这些 op 并不天然要求先经过 `passes` 才能进入 `emit_c/gen_kernel`。
- `passes` 当前只消费受限的 IR 子集，例如 [`spec/pass/lowing/nn_to_kernel.md`](../spec/pass/lowing/nn_to_kernel.md) 中列出的少量 `nn` op；它不是“所有 dialect 的统一中转站”。
- `emit_c/gen_kernel` 当前也只接受受控的 IR 子集，不等于“任何 dialect IR 都能自动生成 CPU C/C++”。
- 因此，看到 `dialect/`、`passes/`、`dsl/`、`include/` 同时存在时，不能推断它们已经自然串通成完整后端流水线。

## 已打通范围矩阵

| 专题 / 路径 | 语义层 | dialect / func 层 | passes | codegen | 当前结论 |
| --- | --- | --- | --- | --- | --- |
| DSL 算术、比较、`scf.for` | 通过 DSL AST 表达 | `emit_mlir/mlir_gen` 可发射受支持 IR | 非必经 | `emit_c/gen_kernel` 支持受控子集 | 已可生成 CPU 源码字符串 |
| unit-tile `dma.load/store` | 通过 DSL/IR 入口表达 | 可进入 `dma` / `func` IR | 非必经 | `emit_c/gen_kernel` 支持 unit-tile 子集 | 已有受控支持 |
| `symbol.add` | 通过 DSL/IR 入口表达 | 可进入 `symbol` / `func` IR | 非必经 | 仅 `target=cpu` 支持 | 已有 CPU-only 支持 |
| `nn.add/sub/mul/div/.../select/cast` | `operation/nn` 与 `nn` IR 均存在 | `nn` dialect 已定义 | `nn_to_kernel` 可消费受支持子集 | 不自动接 `emit_c/gen_kernel` | 目前止于 IR lowering |
| `broadcast` / `softmax` / `fc` / `matmul` | 高层语义已存在 | 是否进入 IR 取决于专题 | 无统一现成路径 | 无统一现成路径 | 目前主要停留在语义层 |
| `conv` / `img2col` | 高层语义已存在 | 无通用既有落点 | 无通用既有路径 | 无既有直出 CPU codegen | 当前未打通 |

## DSL / CPU codegen 最小支持清单

| 类别 | 当前最小支持范围 | 边界说明 |
| --- | --- | --- |
| 算术表达式 | `arith` 二元算术 | 以 [`spec/dsl/emit_c.md`](../spec/dsl/emit_c.md) 与 [`test/dsl/test_emit_c.py`](../test/dsl/test_emit_c.py) 为准 |
| 比较表达式 | `arith.cmpi` | 仅覆盖当前测试锁定的比较生成路径 |
| 控制流 | `scf.for` | 生成完整循环语句块，不代表支持更广控制流 |
| 访存 | unit-tile `dma.load` / `dma.store` | 仅覆盖 unit-tile 访存场景，不代表通用 DMA codegen |
| 符号整数 | `symbol.add` | 仅 `target=cpu` 支持；非 CPU 必须报错 |
| 函数级输出 | `func.func -> C/C++` | 由 [`spec/dsl/gen_kernel.md`](../spec/dsl/gen_kernel.md) 约束签名、返回和 `out` 参数风格 |

- 这张表描述的是“当前最小可用 codegen 子集”，不是未来目标清单。
- 未列入这张表的 op / dialect，默认不能推断为已具备 CPU codegen 支持。

## 当前主链路与断点

| 路径 / 专题 | 起点 | 当前终点 | 当前状态 | 断点 / 备注 |
| --- | --- | --- | --- | --- |
| DSL 算术/比较/`scf.for`/unit-tile `dma.load/store`/`symbol.add(cpu)` | DSL/Python 函数 | CPU C/C++ 源码字符串 | 已有受控子集的代码生成链路 | 支持范围以 [`spec/dsl/emit_c.md`](../spec/dsl/emit_c.md) 与 [`spec/dsl/gen_kernel.md`](../spec/dsl/gen_kernel.md) 为准 |
| `nn` 逐元素算术/比较/`select`/`cast` lowering | `nn` dialect IR 或可构造的 `nn` op | `kernel/dma/func` IR | 已有 IR lowering | 由 [`kernel_gen/passes/lowing/nn_to_kernel.py`](../kernel_gen/passes/lowing/nn_to_kernel.py) 负责；不自动衔接源码生成 |
| 高层 `operation` 的 `broadcast` / `softmax` / `fc` / `matmul` | `Memory` 语义调用 | 高层语义结果或局部 IR 设计入口 | 以语义层为主 | 是否进入 dialect/pass/codegen 需按专题单独推进 |
| 高层 `operation` 的 `conv` / `img2col` | `Memory` 语义调用 | 高层语义结果 | 当前仅语义层收敛 | 尚无通用 lowering 或 `emit_c/gen_kernel` 直出代码路径 |
| `arch` helper + target 查询 | `operation/arch` / `dialect/arch` | 符号语义、动态内存入口或 verifier 决策 | 已分层存在 | 硬件值来源是 `target/registry`；业务回退由调用层承担 |

## dialect 的生产者 / 消费者关系

| 模块 | 生产什么 | 消费什么 | 说明 |
| --- | --- | --- | --- |
| [`kernel_gen/operation`](../kernel_gen/operation) | 高层语义对象、形状/类型约束 | `Memory`、标量、`MemorySpace`、target 查询结果 | 不直接消费 DSL AST，也不直接消费 `emit_c` 产物 |
| [`kernel_gen/dsl/emit_mlir.py`](../kernel_gen/dsl/emit_mlir.py) + [`kernel_gen/dsl/mlir_gen.py`](../kernel_gen/dsl/mlir_gen.py) | `func.func` 与一部分 `dialect` op | DSL AST、函数形参、函数体内可达值 | 是 DSL 前端的 IR 生产者，不等于 pass 管线入口 |
| [`kernel_gen/passes`](../kernel_gen/passes) | 变换后的 IR | 已存在的合法 IR | 当前只消费受限 IR 子集，例如特定 `nn` op |
| [`kernel_gen/dsl/emit_c.py`](../kernel_gen/dsl/emit_c.py) + [`kernel_gen/dsl/gen_kernel.py`](../kernel_gen/dsl/gen_kernel.py) | CPU C/C++ 源码字符串 | 受支持的 op、SSA value、`func.func` | 不是所有 dialect IR 的通用消费者 |

- 结论：`dialect` 既可能由 DSL 前端直接生产，也可能由 pass 重写后生产；`emit_c/gen_kernel` 只消费其中受支持的一部分，`passes` 也只消费其中受支持的一部分。
- 因此，项目当前更接近“多条局部链路并存”，而不是“所有模块共享一条 canonical 主流水线”。
- 硬断点：`operation/nn -> passes -> codegen` 不是默认贯通链路。`nn_to_kernel` 当前只消费受限 `nn` 子集，而 `emit_c/gen_kernel` 当前并不接受通用 `nn` dialect 作为输入。

## 产品模块边界与交接契约

| 模块 | 输入 | 输出 | 交接契约 | 负责 | 不负责 |
| --- | --- | --- | --- | --- | --- |
| [`spec/`](../spec) | 需求、边界、错误规则 | 公开契约与测试目标 | 所有公开语义以 spec 为准 | 定义边界、错误、测试映射 | 不直接承载业务实现 |
| [`kernel_gen/symbol_variable/`](../kernel_gen/symbol_variable) | 基础 shape / dim / type 需求 | `Memory`、`SymbolDim`、`SymbolShape` 等基础对象 | 作为上层语义与 IR 的共享底座 | 基础元信息与类型表达 | 不定义算子语义或代码模板 |
| [`kernel_gen/operation/`](../kernel_gen/operation) | `Memory`、标量参数、`MemorySpace`、target 查询结果 | 高层语义结果：`Memory`、`SymbolDim`、调用约束 | 算子形状、类型、错误边界的唯一来源是 `spec/operation/* + kernel_gen/operation/*` | 高层算子/arch helper 的语义推导、参数校验、输出描述 | 不负责 verifier、pass、C/C++ 模板 |
| [`kernel_gen/dialect/`](../kernel_gen/dialect) | 已明确的语义与 IR 设计需求 | 可校验的 op、type、attribute | 交给 pass、emit 或测试的都是“可校验 IR” | IR 语义、parse/print、verifier | 不重新定义高层数学语义，不直接拼装目标源码 |
| [`kernel_gen/passes/`](../kernel_gen/passes) | 合法 IR module / func / op | 变换后的 IR | 只做 IR 到 IR 的组织、合法化与 lowering | pass 调度、lowering、IR 重写 | 不做 DSL 解析、runtime API 或高层算子规则 |
| [`kernel_gen/dsl/ast.py`](../kernel_gen/dsl/ast.py) + [`kernel_gen/dsl/ast_visitor.py`](../kernel_gen/dsl/ast_visitor.py) | Python AST / DSL 写法 | DSL AST | 只负责把用户写法变成内部 AST，不推导算子语义 | AST 节点建模、遍历、语法层转换 | 不负责高层 `Memory` 语义或目标代码模板 |
| [`kernel_gen/dsl/emit_mlir.py`](../kernel_gen/dsl/emit_mlir.py) + [`kernel_gen/dsl/mlir_gen.py`](../kernel_gen/dsl/mlir_gen.py) | DSL AST、函数形参、函数体内可达值 | `func.func` 与相关 dialect op | 仅接受函数体内可达值/实参作为 lowering 输入；不允许外部值隐式捕获；不得在此层复写 `operation` 的算子规则 | DSL 到 MLIR 的发射、函数级装配、必要类型桥接 | 不定义高层算子形状公式，不负责完整 C/C++ 模板 |
| [`kernel_gen/dsl/emit_c.py`](../kernel_gen/dsl/emit_c.py) + [`kernel_gen/dsl/gen_kernel.py`](../kernel_gen/dsl/gen_kernel.py) | 已合法化的单个 op、SSA value、`func.func` | 目标后端源码字符串 | `emit_c` 负责节点级片段，`gen_kernel` 负责函数签名和函数体拼装 | 节点级与函数级源码生成 | 不新增高层 lowering 特例，不负责文件写盘/编译/链接 |
| [`kernel_gen/analysis/`](../kernel_gen/analysis) | IR 或语义对象 | 静态估算结果 | 只输出分析结果，不改写语义 | 计算量/搬运量分析 | 不负责 lowering、调度、真实执行 |
| [`kernel_gen/target/`](../kernel_gen/target) | `json/txt` target 配置 | target 能力与硬件参数查询结果 | registry 不补业务默认值；硬件缺失时由调用层决定回退；`cpu.txt` 的白名单空值特例由 spec 明确 | target 配置解析、注册、查询 | 不生成代码，不决定算子完整 lowering 策略 |
| [`include/cpu/`](../include/cpu) | 代码生成层依赖 | CPU 运行时头文件接口 | 为生成代码提供 `Memory` 与基础算子接口 | 运行时 API 和数据视图模板 | 不负责上层 DSL/IR 语义 |
| [`test/`](../test) | spec 与实现 | 可执行断言 | 测试验证一致性，不反向定义公开语义 | 模块级回归与边界校验 | 不作为契约源头 |

## 协作与计划层边界

| 模块 | 作用 | 边界 |
| --- | --- | --- |
| [`ARCHITECTURE/plan`](plan) | 单个专题的目标、范围、阶段、风险与验收 | 只写专题推进，不回写成项目总览 |
| `agents/`、`skills/`、`script/`、`TODO.md`、`DONE.md`、`wt-*` | 多人协作、任务分发、记录和 worktree 支撑 | 不属于产品主链路，不应在产品架构判断中替代 `spec/kernel_gen/include/test` |

## 关键边界规则

### 1. 算子语义唯一来源

- 高层算子的 `shape`、`dtype`、错误边界唯一来源是 [`spec/operation`](../spec/operation) 与 [`kernel_gen/operation`](../kernel_gen/operation)。
- `dsl/emit_mlir/mlir_gen` 可以做语法翻译和必要类型桥接，但不能在该层重写算子规则。
- 若某能力需要补充算子公式、错误类型或 shape 推导，必须先落到 `operation` 对应链路，而不是在 `dsl` 或 `emit_c` 层偷偷补逻辑。

### 2. DSL 到 MLIR 的输入边界

- `mlir_gen` 仅接受函数形参和函数体内可达值作为 lowering 输入。
- 不允许外部值隐式捕获；如需外部值，必须变成显式参数或在 DSL AST 中有明确节点。
- 当前 DSL 只覆盖已在 `spec/dsl/*.md` 与 `test/dsl/*.py` 中列出的 dialect / operation 子集，不应把未覆盖的高阶 `nn` 算子默认视为可直接生成 C/C++。

### 3. target 读取与回退责任

- [`kernel_gen/target/registry.py`](../kernel_gen/target/registry.py) 只负责“加载、注册、查询”。
- `operation/arch` 可优先读取硬件静态值；字段缺失时回退为符号语义或动态语义，以对应 spec 为准。
- `dialect/arch` verifier 可根据当前 target 判断 op 是否允许出现。
- 不允许在 `registry`、`operation/arch`、`passes` 三层分别发明不同的默认值或回退口径。
- `emit_c/gen_kernel` 中与 target 相关的代码生成边界也必须显式受控；例如仅在 `target=cpu` 可生成的路径，非 CPU 必须明确报错。

### 4. 新能力的推进方式

- 若需求只改一层，应只改该层对应的 `spec + 实现 + test`。
- 若需求跨越语义、IR、codegen 多层，必须拆成多个任务，并在 [`ARCHITECTURE/plan`](plan) 中写专题计划。
- 若某专题会改变“当前支持矩阵”，必须同步更新本文档或对应专题计划，显式写出链路终点和断点。

### 5. 协作层的排除边界

- `TODO.md`、`DONE.md`、`task_records`、`agents/`、`skills/`、`script/` 和 `wt-*` 只服务于任务编排、审计、协作和执行组织。
- 这些内容不定义业务语义、不作为产品实现依赖、也不应被引用为“某能力已经存在”的架构证据。
- 若某信息会影响公开行为，必须回收至 `spec/`、实现文件和测试文件；不能只停留在协作记录中。

## 目录归属判定规则（3 问）

1. 这个改动是否改变运行时、编译期、IR 或代码生成语义？
   - 是：归入代码层，落到 `spec/ + kernel_gen/ + include/ + test/` 的对应链路。
2. 这个改动是否只影响任务分发、记录、脚本、worktree 或审计流程？
   - 是：归入协作基础设施层，落到 `agents/`、`skills/`、`script/`、`TODO.md`、`DONE.md` 或记录目录。
3. 这个改动是否只描述某个专题的阶段目标、范围、风险或验收？
   - 是：归入计划文档层，落到 [`ARCHITECTURE/plan`](plan)。

反例：

- 不应把任务推进步骤、派工状态写进 `spec/` 或产品实现文件。
- 不应把“conv CPU tiled 分阶段计划”写进 `ARCHITECTURE/project_architecture.md`。
- 不应把 `TODO.md`、`DONE.md` 或 `task_records` 中的描述当作公开语义依据。

## 公开接口

### `项目总览定位`

功能说明：

- 用于判断某个需求属于项目哪一条主链路，以及当前链路实际能走到哪里。

参数说明：

- 无显式参数；按需求的输入形态与期望输出选择链路。

使用示例：

```text
1. “我想从 DSL 函数直接生成 CPU C++”：先查 DSL 到源码生成链路。
2. “我想让 nn.add 先变成 kernel.add”：先查语义与 IR 合法化链路。
3. “我想让 conv 自动出 CPU tile 代码”：先定位为跨语义层与代码生成层的专题，而不是默认已有主链路。
```

注意事项：

- 目录存在不代表链路已贯通。
- 需要同时说明输入产物、输出产物和当前断点。

返回与限制：

- 返回语义：指出需求属于哪条主链路，以及当前已打通到哪一层。
- 限制条件：不替代专题计划。

### `变更归属判断`

功能说明：

- 用于判断改动应该落在哪一组目录，并识别需要同步的 `spec/实现/test`。

参数说明：

- 无显式参数；按“改的是语义、IR、DSL、codegen、target、runtime 还是计划”分类。

使用示例：

```text
1. 修改 conv 输出 shape 公式：spec/operation + kernel_gen/operation + test/operation
2. 新增可校验 op 或 verifier 规则：spec/dialect + kernel_gen/dialect + test/dialect
3. 新增 DSL 语法或 AST walk：spec/dsl/ast* + kernel_gen/dsl/{ast,ast_visitor} + test/dsl
4. 新增 CPU 代码模板：spec/dsl/{emit_c,gen_kernel} + kernel_gen/dsl + test/dsl + include/cpu(如 runtime 需要)
5. 新增专题目标与阶段验收：ARCHITECTURE/plan
```

注意事项：

- 跨层需求必须拆分，不能只在单层硬塞全部逻辑。
- 新 pass 应优先放到 [`kernel_gen/passes`](../kernel_gen/passes)。

返回与限制：

- 返回语义：给出推荐修改层与需同步的文件范围。
- 限制条件：只做归属判断，不直接替代实现设计。

### `专题计划入口`

功能说明：

- 约定当某个目标跨多层推进时，如何在架构层保留计划入口而不污染项目总览。

参数说明：

- 无显式参数；按专题创建对应计划文档。

使用示例：

```text
1. 项目级背景放在 ARCHITECTURE/project_architecture.md
2. conv CPU tiled 实现计划放在 ARCHITECTURE/plan/<topic>.md
3. 计划文档写目标、范围、阶段、风险、验收；实现细节仍回收至 spec/实现/test
```

注意事项：

- 项目总览负责解释“项目是什么、当前链路到哪里”。
- 计划文档负责解释“某个目标如何推进”。

返回与限制：

- 返回语义：给出项目总览与专题计划的分工边界。
- 限制条件：计划文档不能替代模块 spec。

## 测试与审阅

- 测试文件：`无独立自动化测试；通过文档审阅清单核验`
- 最近核验时间：`2026-03-28`
- 最近核验责任人：`大闸蟹`
- 同步吸收的只读反馈：`我不是牛马`、`jcc你莫辜负`、`摸鱼小分队`、`李白`
- 审阅清单：
  - 目录划分是否区分产品代码、协作基础设施和计划文档。
  - 两条主链路是否写明输入产物、输出产物与当前断点。
  - `operation -> dialect -> passes` 与 `dsl -> emit_mlir/mlir_gen -> emit_c/gen_kernel` 的交接契约是否清楚。
  - 是否明确写出 `operation` 是算子语义唯一来源，`dsl` 不复写算子规则。
  - 是否明确写出 `target/registry` 只负责查询、调用层负责回退。
  - 是否把当前支持矩阵中“已贯通”和“未贯通”能力区分开。
  - 文件链接与引用路径是否存在，且未把专题计划混入项目总览。
- 功能与用例清单：
  - `DOC-ARCH-001`：读者可区分产品主链路与协作基础设施。
  - `DOC-ARCH-002`：读者可判断某个需求当前属于 DSL 出码链路还是 IR lowering 链路。
  - `DOC-ARCH-003`：读者不会把 `conv/img2col` 误判为当前已具备通用代码生成能力。
  - `DOC-ARCH-004`：读者可根据模块 I/O 与交接契约定位修改范围。
