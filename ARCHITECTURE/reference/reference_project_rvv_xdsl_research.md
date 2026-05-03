# reference_project_rvv_xdsl_research.md

## 功能简介

- 调研外部参考项目 `JieGH/RVV_code_gen_via_MLIR_xDSL` 的实现分层、lowering 管线、代码生成方式与实机评测闭环。
- 区分“文章/论文中的宣称”和“仓库源码中可直接确认的实现事实”，避免把宣传性表述误当作稳定架构结论。
- 为当前仓库后续讨论 `DSL -> IR -> C/C++ -> 后端` 链路时提供一个可借鉴、可回避的外部样本。

## 执行摘要

1. 这个参考项目的本质不是“通用编译器框架”，而是“面向 RVV GEMM 微内核的专用代码生成与 benchmark 编排仓库”。
2. 它的核心做法不是让 MLIR 单独完成所有 lowering，而是用 `xDSL` 自定义方言和小步 pass，补齐 `MLIR -> RVV intrinsic -> C/C++` 的“最后一公里”。
3. 它的主链路可以明确拆成四层：`xDSL API 构建微内核 IR -> 自定义 pass 下沉到 EmitC -> mlir-translate 产出 C/C++ -> 远端板卡编译与对比 OpenBLAS/BLIS 基准`。
4. 最值得借鉴的是：每一级 lowering 都有可观察中间产物，RVV 语义集中在单一后段 pass 中映射，且生成与实机 benchmark 形成闭环。
5. 最不该直接照搬的是：把核心编译逻辑堆在 `tests/test_codeGeneration.py` 与单体 `compile.sh` 中，并把远端 SSH、板卡路径、BLIS/OpenBLAS 环境假设直接耦进主链路。
6. 对当前仓库最有价值的启发不是“复制它的工程组织”，而是“先冻结中间契约和 pass 边界，再把后端专有 intrinsic/运行时映射压到链路末段”。

## 文档信息

- `文档`：[`ARCHITECTURE/reference_project_rvv_xdsl_research.md`](reference_project_rvv_xdsl_research.md)
- `spec`：不适用；本文为外部参考项目调研文档，不对应本仓 `spec` 文件
- `test`：
  - [tests/test_codeGeneration.py](https://github.com/JieGH/RVV_code_gen_via_MLIR_xDSL/blob/main/tests/test_codeGeneration.py)
  - [tests/README.md](https://github.com/JieGH/RVV_code_gen_via_MLIR_xDSL/blob/main/tests/README.md)
- `功能实现`：
  - [README.md](https://github.com/JieGH/RVV_code_gen_via_MLIR_xDSL/blob/main/README.md)
  - [compile.sh](https://github.com/JieGH/RVV_code_gen_via_MLIR_xDSL/blob/main/compile.sh)
  - [setup_env.sh](https://github.com/JieGH/RVV_code_gen_via_MLIR_xDSL/blob/main/setup_env.sh)
  - [src/xdsltemplate/dialects/gemm.py](https://github.com/JieGH/RVV_code_gen_via_MLIR_xDSL/blob/main/src/xdsltemplate/dialects/gemm.py)
  - [src/xdsltemplate/dialects/rvv.py](https://github.com/JieGH/RVV_code_gen_via_MLIR_xDSL/blob/main/src/xdsltemplate/dialects/rvv.py)
  - [src/xdsltemplate/dialects/emitc_ext.py](https://github.com/JieGH/RVV_code_gen_via_MLIR_xDSL/blob/main/src/xdsltemplate/dialects/emitc_ext.py)
  - [src/xdsltemplate/transforms/gemm_to_arith.py](https://github.com/JieGH/RVV_code_gen_via_MLIR_xDSL/blob/main/src/xdsltemplate/transforms/gemm_to_arith.py)
  - [src/xdsltemplate/transforms/memref_to_emitc.py](https://github.com/JieGH/RVV_code_gen_via_MLIR_xDSL/blob/main/src/xdsltemplate/transforms/memref_to_emitc.py)
  - [src/xdsltemplate/transforms/memref_load_to_emitc.py](https://github.com/JieGH/RVV_code_gen_via_MLIR_xDSL/blob/main/src/xdsltemplate/transforms/memref_load_to_emitc.py)
  - [src/xdsltemplate/transforms/memref_store_to_emitc.py](https://github.com/JieGH/RVV_code_gen_via_MLIR_xDSL/blob/main/src/xdsltemplate/transforms/memref_store_to_emitc.py)
  - [src/xdsltemplate/transforms/arith_to_emitc.py](https://github.com/JieGH/RVV_code_gen_via_MLIR_xDSL/blob/main/src/xdsltemplate/transforms/arith_to_emitc.py)
  - [src/xdsltemplate/transforms/scf_to_emitc.py](https://github.com/JieGH/RVV_code_gen_via_MLIR_xDSL/blob/main/src/xdsltemplate/transforms/scf_to_emitc.py)
  - [src/xdsltemplate/transforms/rvv_to_emitc.py](https://github.com/JieGH/RVV_code_gen_via_MLIR_xDSL/blob/main/src/xdsltemplate/transforms/rvv_to_emitc.py)

## 使用示例

- 当你要判断“`MLIR + xDSL` 的混合 lowering 是否值得借鉴”时，先读本文档的“项目是什么 / 不是什么”和“对当前仓库的启发”两节。
- 当你要设计新的后端专有 lowering 时，优先参考本文档“关键 lowering 管线”中“把后端专有 intrinsic 映射集中在单一末段 pass”的做法。
- 当你要评估一个外部项目是否适合作为本仓长期架构样板时，直接看本文档“最不该直接照搬”的部分，避免把实验脚本结构误抄成正式产品边界。

## 调研对象与证据边界

### 外部来源

- 微信文章：[用 Python 写一个开源 RISC-V 向量编译器：MLIR 与 xDSL 的 GEMM 代码生成，较 OpenBLAS 最高提升 35%](https://mp.weixin.qq.com/s/uLdMSGvwzehrS3xgRA_EDw)
- 公众号：`NeuralTalk`
- 论文：[Enabling RISC-V Vector Code Generation in MLIR through Custom xDSL Lowerings](https://arxiv.org/abs/2603.17800)
- 代码仓库：[JieGH/RVV_code_gen_via_MLIR_xDSL](https://github.com/JieGH/RVV_code_gen_via_MLIR_xDSL)

### 证据边界

- 文章和论文用于确认项目目标、问题定义与性能宣称。
- 仓库源码用于确认“实际实现了什么”，包括方言、pass、翻译方式、部署脚本和 benchmark 闭环。
- 同事交叉结论只作为辅助校验，不替代源码证据。

### 本文明确区分的两类结论

- `文章/论文宣称`：
  - 项目意图补齐 MLIR 到 RVV 代码生成的缺口。
  - 在文章标题中明确宣称“较 OpenBLAS 最高提升 35%”。
  - 论文摘要明确写到该方法把高层操作系统性翻译为调用 RVV intrinsic 的硬件感知 C 代码。
- `仓库可直接确认`：
  - 仓库确实包含自定义 `rvv` / `gemm` / `emitc` 扩展方言、对应 lowering pass、`mlir-translate -mlir-to-cpp` 翻译步骤，以及远端板卡 benchmark 脚本。
  - 仓库确实把 RVV op 通过 `emitc.call_opaque` 映射到 `__riscv_*` intrinsic。
  - 仓库确实把生成、部署、对比 OpenBLAS/BLIS 的流程放进自动脚本。

## 项目是什么 / 不是什么

| 问题 | 结论 | 依据 |
| --- | --- | --- |
| 它是不是通用 DSL 编译器框架？ | 不是 | README 首句就是 “RVV xDSL Microkernel Runner”；主实现围绕 GEMM 微内核与 RVV intrinsic |
| 它是不是专用微内核代码生成项目？ | 是 | `tests/test_codeGeneration.py` 直接构建 `(mr, nr)` GEMM 微内核、beta 模式和 profiling 代码 |
| 它是不是只停留在 IR 演示？ | 不是 | `compile.sh` / `setup_env.sh` 会同步到远端板卡、编译、benchmark、拉回结果 |
| 它是不是完整通用后端？ | 不是 | 目标聚焦 RVV GEMM；大量流程依赖专用脚本、远端环境和 benchmark 编排 |

## 实现分层

| 层级 | 主要文件 | 职责 | 说明 |
| --- | --- | --- | --- |
| IR 构建层 | [tests/test_codeGeneration.py](https://github.com/JieGH/RVV_code_gen_via_MLIR_xDSL/blob/main/tests/test_codeGeneration.py) | 通过 Python/xDSL API 直接构建 GEMM 微内核 IR | 这不是单纯测试文件，实际上承担了 kernel 生成器和集成驱动的职责 |
| 自定义方言层 | [dialects/gemm.py](https://github.com/JieGH/RVV_code_gen_via_MLIR_xDSL/blob/main/src/xdsltemplate/dialects/gemm.py)、[dialects/rvv.py](https://github.com/JieGH/RVV_code_gen_via_MLIR_xDSL/blob/main/src/xdsltemplate/dialects/rvv.py)、[dialects/emitc_ext.py](https://github.com/JieGH/RVV_code_gen_via_MLIR_xDSL/blob/main/src/xdsltemplate/dialects/emitc_ext.py) | 表达 GEMM 索引语义、RVV 向量语义与 EmitC 扩展节点 | 用 xDSL 补齐标准 MLIR/EmitC 在该专题上的缺口 |
| lowering pass 层 | [transforms/*](https://github.com/JieGH/RVV_code_gen_via_MLIR_xDSL/tree/main/src/xdsltemplate/transforms) | 把高层 GEMM / memref / scf / RVV 语义逐级改写为 EmitC 更可翻译的形式 | 采用多个小步 pass，而不是一个巨型 emitter |
| C/C++ 翻译层 | `mlir-translate -mlir-to-cpp`，以及 `tests/test_codeGeneration.py` 中的签名修补逻辑 | 把下沉后的 IR 转成 C/C++，再补目标 ABI 需要的参数形式 | 仓库会把生成函数签名中的 `size_t` 改成 `int`，并补 `void* ctxt` 占位参数 |
| 部署与评测层 | [compile.sh](https://github.com/JieGH/RVV_code_gen_via_MLIR_xDSL/blob/main/compile.sh)、[setup_env.sh](https://github.com/JieGH/RVV_code_gen_via_MLIR_xDSL/blob/main/setup_env.sh)、[tests/README.md](https://github.com/JieGH/RVV_code_gen_via_MLIR_xDSL/blob/main/tests/README.md) | 远端依赖安装、代码同步、编译、跑分、回收 CSV/图表 | 这层更接近 benchmark orchestrator，不应误判为编译器稳定公开接口 |

## 关键 lowering 管线

仓库中可直接确认的 pass 顺序是：

```text
GemmToArithPass
-> MemRefToEmitCPass
-> ArithToEmitCPass
-> MemrefLoadToEmitcPass
-> MemrefStoreToEmitcPass
-> SCFToEmitCPass
-> RVVToEmitCPass
-> mlir-translate -mlir-to-cpp
```

### 1. 用 xDSL API 直接构建 GEMM 微内核 IR

- `tests/test_codeGeneration.py` 不是传统意义上的“只断言测试结果”的测试文件。
- 它实际承担了：
  - `(mr, nr)` 微内核组合枚举
  - `beta` 模式切换
  - kernel header / profiling 代码生成
  - lowering pass 组装
  - 生成后 C/C++ 的 ABI 修补

### 2. 用 `gemm.*` 方言表达 GEMM 专用索引

- `gemm.py` 中定义了 `gemm.acol`、`gemm.bcol`、`gemm.ccol`。
- 这些 op 的职责不是执行数学计算，而是把 A/B/C 的列索引语义先保留为显式 IR 节点。
- `GemmToArithPass` 再把这些节点改写为普通 `arith.muli + arith.addi` 形式。

### 3. 用 `rvv.*` 方言表达 RVV 语义

- `rvv.py` 中定义了 `rvv.setvl`、`rvv.vle32_v_f32m1Op`、`rvv.vfmacc_vf_f32m1Op`、`rvv.vfmv_v_f_f32m1`、`rvv.vse32_v_f32m1Op`。
- 这一步的价值是：先把向量长度设置、向量加载、累加和存储表达成 IR 语义，而不是过早拼接 C intrinsic 字符串。
- 从仓库实现可推断，它使用 `setvl` 路径处理可变向量长度，而不是只支持满向量固定宽度路径。

### 4. 先把 `memref` / `scf` 降到更接近 C 的 EmitC 形态

- `MemRefToEmitCPass` 会把函数签名里的 `memref` 参数改写为 `emitc.ptr` 形态。
- `MemrefLoadToEmitcPass` 会把 `memref.load` 改写为 `emitc.subscript + emitc.load`。
- `MemrefStoreToEmitcPass` 会把 `memref.store` 改写为 `emitc.subscript + emitc.assign`。
- `SCFToEmitCPass` 会把带 `iter_args` 的 `scf.for` 改写为 `emitc.for + emitc.variable/assign` 结构。

### 5. 在末段 pass 中集中做 RVV intrinsic 映射

- `RVVToEmitCPass` 把 `rvv.*` op 改写成 `emitc.call_opaque`。
- 可直接在源码中确认的映射包括：
  - `__riscv_vsetvl_e32m1`
  - `__riscv_vle32_v_f32m1`
  - `__riscv_vfmacc_vf_f32m1`
  - `__riscv_vfmv_v_f_f32m1`
  - `__riscv_vse32_v_f32m1`
- 这是该项目最值得借鉴的结构点之一：后端专有 intrinsic 映射被压在一个边界清晰的后段 pass 中，而不是散落在前端语义层。

### 6. 使用 `mlir-translate` 产出 C/C++，再补目标 ABI

- 仓库不是自己手写完整 C++ pretty-printer，而是把 EmitC 形态交给 `mlir-translate -mlir-to-cpp`。
- 之后在 `tests/test_codeGeneration.py` 中对生成源码再做一次文本级修补：
  - 把函数首参补成 `void* ctxt`
  - 把 `size_t` 替换为 `int`
- 这说明它并没有完全靠稳定公共接口自然落地，而是保留了实验性补丁层。

## 运行与 benchmark 闭环

### 本地侧

- README 明确要求本地准备 `git`、`cmake`、`ninja`、C/C++ 编译器、`python3`、`uv`、`ssh`、`rsync`。
- 如果缺失 `mlir-translate`，`compile.sh` 会自动尝试构建本地 MLIR 工具。

### 远端板卡侧

- README 明确要求远端 RISC-V 板卡准备 `gcc-14`、`gfortran-14`、`make`、`git`、`ssh`。
- `setup_env.sh` / `compile.sh` 会在远端缺失时自动构建 OpenBLAS 和 BLIS。

### 结果产物

- README 写明输出会保存在 `tests/output/`。
- 包括：
  - `*.txt` 日志
  - `*.csv` sweep 表
  - `*.png` / `*.pdf` 图表

### 结论

- 这条链路已经不是“单纯 compiler prototype”，而是“编译 + 部署 + 实机评测”的完整实验流水线。
- 这也是文章能给出性能对比数字的工程基础。

## 这个项目真正解决了什么

1. 它证明了可以用 `xDSL` 在 Python 侧快速定义专题方言和小步 lowering pass，补上 MLIR 在某些硬件专题上的 lowering 缺口。
2. 它证明了“高层 IR -> EmitC -> C/C++ -> RVV intrinsic”的链路可以通过混合 `xDSL + MLIR` 工具链跑通。
3. 它证明了“生成结果必须配 benchmark 闭环验证”，否则很难判断 lower 出来的 kernel 是否真的有价值。

## 最值得借鉴的点

### 1. 后端专有语义放到链路末段

- `rvv.* -> emitc.call_opaque(__riscv_*)` 的设计，把硬件专有细节压在末段 pass。
- 这能保持前面的 GEMM / memref / scf 语义相对稳定，也方便替换最终目标后端。

### 2. 每一级 pass 都有可观察中间产物

- IR 构建、pass 后 IR、生成 C++、远端 benchmark 结果，层层都能检查。
- 这比“单个大 emitter 直接吐代码”更容易定位语义漂移或后端 bug。

### 3. 生成与 benchmark 闭环放在同一工程里

- 对微内核专题来说，只能生成代码还不够，必须能快速验证正确性和性能。
- 该仓库把“能生成”与“能在板卡上测出来”打通了，这一点很实用。

### 4. 小步 lowering 比单体 codegen 更稳

- `gemm_to_arith`、`memref_to_emitc`、`scf_to_emitc`、`rvv_to_emitc` 的职责边界很清楚。
- 这说明“专题 compiler”也不必一开始就做成单文件巨型 emitter。

## 最不该直接照搬的点

### 1. 把核心编译链路塞进测试文件

- `tests/test_codeGeneration.py` 实际承担了 IR 构建、kernel 生成、header 生成、profiling 代码生成和部分 ABI 修补职责。
- 这对原型开发很快，但对长期维护、复用和契约边界不利。

### 2. 把 benchmark 编排和产品边界混在一起

- `compile.sh` 里同时处理本地工具检查、远端依赖安装、代码同步、编译和 benchmark。
- 这对于实验复现实用，但如果照搬到通用编译器仓库，会让“产品接口”和“实验脚本”边界失焦。

### 3. 对环境和路径强耦合

- 远端用户、IP、SSH、workspace、OpenBLAS/BLIS 路径都深度耦合在脚本中。
- 这种耦合适合实验环境，不适合成为长期稳定 API 的组成部分。

### 4. 原型痕迹较重

- `src/xdsltemplate/dialects/__init__.py` 与 `transforms/__init__.py` 都返回空注册表。
- 仓库中还能看到 `NotUse`、备份文件名和注释残留。
- 这不影响专题验证，但不适合作为正式产品工程组织的模板。

## 对当前仓库的启发

### 可以借鉴

1. 先冻结每一级 lowering 的中间契约，再推进下一层，而不是一开始追求“全链路全打通”。
   中间契约至少应显式覆盖：`type`、`shape`、`layout/stride`、`side-effect`。
2. 把后端专有 intrinsic、runtime helper 或 ABI 细节集中在链路末段，而不是渗透到 DSL/operation 层。
3. 给每一级产物明确观察口：IR、EmitC/C++、最终源码、运行结果或 benchmark 结果。
4. 若要做专题后端，优先做“小步可组合 pass”，不要把语义、优化、后端打印、runtime 假设全塞进一个 emitter。

### 不要照搬

1. 不要把“实验编排脚本”误当成稳定产品接口。
2. 不要把“特定 benchmark 场景下的成功路径”误写成通用 DSL 或通用后端契约。
3. 不要因为参考项目能接受大量环境硬编码，就在当前仓库里也把 target/runtime/部署耦死在主链路里。

## 同事交叉校验

本次调研还额外询问了两位同事的只读判断，结论与源码证据一致：

- `摸鱼小分队`：
  - 认为该项目本质上是“生成-下沉-落地-实机评测”的四层流水线，而不是纯编译器仓库。
  - 强调最值得借鉴的是显式 pass 链、可观测产物和 RVV 语义集中映射。
  - 强调最不该照搬的是把核心链路耦进测试脚本和单体 shell。
- `咯咯咯`：
  - 认为关键创新是用 xDSL 自定义方言 + pass 补齐 MLIR 到 RVV intrinsic 的缺口。
  - 认为最值得借鉴的是“显式方言契约 + 小步 lowering pass + 硬件在环 benchmark 闭环”。
  - 认为最不该照搬的是强耦合远端环境脚本和原型式代码组织。
  - 补充强调：对通用 `DSL -> C/C++ -> 后端` 链路，最大启发是先冻结 `type/shape/layout/side-effect` 这类中间契约，再把后端差异收敛到小而清晰的 `lowering + emit` 适配层。

## 结论

这个参考项目值得学习，但学习的重点应当是：

- 如何用自定义方言和小步 pass 补齐后端专题 lowering 缺口；
- 如何把硬件专有 intrinsic 映射压到链路末段；
- 如何让生成结果配套 benchmark 闭环。

不应直接照搬的则是：

- 把测试脚本当编译主入口；
- 把远端部署脚本当产品稳定接口；
- 把专题微内核实验工程误当成通用编译器架构模板。

如果只用一句话概括这份调研结论：

> `RVV_code_gen_via_MLIR_xDSL` 不是“通用编译器范本”，而是“用 xDSL 补齐 MLIR 最后一公里、面向 RVV GEMM 微内核的专用生成与实机评测流水线”。
