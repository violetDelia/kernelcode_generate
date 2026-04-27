# dsl_gen_kernel_mlir_gen_public_api_green_plan.md

> 说明：该文件为 `dsl_gen_kernel_mlir_gen_public_api` 主题的归档承接快照。当前主线 tracked 面不再通过 `ARCHITECTURE/plan/dsl_gen_kernel_mlir_gen_public_api_green_plan.md` 承接该主题；后续计划状态、结论和续接依据统一收口到本归档文件与对应任务记录。若需核对某一轮复验基线，以正文复验段和修复任务记录为准。

## 文档信息

- 创建者：`榕`
- 最后一次更改：`李白`
- 目标 `spec`：
  - [`spec/dsl/mlir_gen.md`](../../../../../../../spec/dsl/mlir_gen.md)
  - [`spec/dsl/gen_kernel/gen_kernel.md`](../../../../../../../spec/dsl/gen_kernel/gen_kernel.md)
  - [`spec/tools/dsl_run.md`](../../../../../../../spec/tools/dsl_run.md)
  - [`spec/tools/mlir_gen_compare.md`](../../../../../../../spec/tools/mlir_gen_compare.md)
  - [`spec/tools/ircheck.md`](../../../../../../../spec/tools/ircheck.md)
- 目标 `API`：
  - [`kernel_gen/dsl/mlir_gen/__init__.py`](../../../../../../../kernel_gen/dsl/mlir_gen/__init__.py)
  - [`kernel_gen/dsl/mlir_gen/function_builder.py`](../../../../../../../kernel_gen/dsl/mlir_gen/function_builder.py)
  - [`kernel_gen/dsl/mlir_gen/module_builder.py`](../../../../../../../kernel_gen/dsl/mlir_gen/module_builder.py)
  - [`kernel_gen/dsl/gen_kernel/__init__.py`](../../../../../../../kernel_gen/dsl/gen_kernel/__init__.py)
  - [`kernel_gen/dsl/gen_kernel/gen_kernel.py`](../../../../../../../kernel_gen/dsl/gen_kernel/gen_kernel.py)
- 目标 `test`：
  - [`test/dsl/test_mlir_gen.py`](../../../../../../../test/dsl/test_mlir_gen.py)
  - [`test/dsl/mlir_gen/test_function_builder.py`](../../../../../../../test/dsl/mlir_gen/test_function_builder.py)
  - [`test/dsl/mlir_gen/test_module_builder.py`](../../../../../../../test/dsl/mlir_gen/test_module_builder.py)
  - [`test/dsl/ast/test_visitor_integration.py`](../../../../../../../test/dsl/ast/test_visitor_integration.py)
  - [`test/dsl/ast/test_package.py`](../../../../../../../test/dsl/ast/test_package.py)
  - [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../../../../test/dsl/gen_kernel/test_gen_kernel.py)
  - [`test/tools/test_dsl_run.py`](../../../../../../../test/tools/test_dsl_run.py)
  - [`test/tools/test_mlir_gen_compare.py`](../../../../../../../test/tools/test_mlir_gen_compare.py)
  - [`test/tools/test_ircheck_runner.py`](../../../../../../../test/tools/test_ircheck_runner.py)
- 目标 `验收资产`：`pytest -q test/dsl/mlir_gen test/dsl/ast/test_visitor_integration.py test/dsl/ast/test_package.py test/dsl/gen_kernel test/tools/test_dsl_run.py test/tools/test_mlir_gen_compare.py test/tools/test_ircheck_runner.py`
- 目标 `功能实现`：
  - [`kernel_gen/dsl/mlir_gen`](../../../../../../../kernel_gen/dsl/mlir_gen)
  - [`kernel_gen/dsl/gen_kernel`](../../../../../../../kernel_gen/dsl/gen_kernel)
  - [`kernel_gen/tools/dsl_run.py`](../../../../../../../kernel_gen/tools/dsl_run.py)
  - [`kernel_gen/tools/mlir_gen_compare.py`](../../../../../../../kernel_gen/tools/mlir_gen_compare.py)
  - [`kernel_gen/tools/ircheck.py`](../../../../../../../kernel_gen/tools/ircheck.py)

## 输入摘要

- 目标：新增 callable 形式的 DSL 源码生成公开入口，名称固定为 `dsl_gen_kernel(...)`。
- 保留：现有 `gen_kernel(op|func|module, ctx)` 必须保持稳定公开入口，不改名、不降级。
- 删除：`build_func_op(...)` 与 `mlir_gen(...)` 的公开 `globals` / `builtins` 参数。
- 不做：本轮不改 `expectation`，也不把范围扩到 `execute_engine`。

## 任务清单

| 任务 | 前置任务 | worktree | 记录文件 |
| --- | --- | --- | --- |
| S1 | 无 | `wt-20260426-mlir-gen-public-api-s1` | `agents/codex-multi-agents/log/task_records/2026/17/20260426-mlir-gen-public-api-s1.md` |
| S2 | S1 | `wt-20260426-dsl-gen-kernel-s2` | `agents/codex-multi-agents/log/task_records/2026/17/20260426-dsl-gen-kernel-s2.md` |
| R1 | `T-20260426-465e7c18` | `wt-20260427-dsl-gen-kernel-public-api-repair-s3` | `/home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/agents/codex-multi-agents/log/task_records/2026/17/20260427-dsl-gen-kernel-public-api-repair-s3.md` |

## 评审摘要

- 评审结论：`通过`
- 评审人：`守护最好的爱莉希雅、大闸蟹`
- 结论摘要：`S1/S2 顺序合理；S1 已把 test/dsl/ast/test_visitor_integration.py、test/dsl/ast/test_package.py 与 mlir_gen.__all__ 去私有导出写成显式交付；S2 的阶段级合同真源也已明确继承 spec/dsl/mlir_gen.md -> spec/dsl/ast/parser.md -> spec/dsl/gen_kernel/gen_kernel.md 整条链。“不改 expectation、保留旧 gen_kernel(op|func|module, ctx)、只新增 dsl_gen_kernel(...)”的边界已写实，适合进入执行阶段。`
- 当前状态：`通过 / 已创建任务 / 待管理员分发`

## 任务创建记录

- 创建时间：`2026-04-26 23:04:57 +0800`
- 创建人：`榕`
- 任务：
  - `S1 = T-20260426-0bf8f426`
  - `S2 = T-20260426-465e7c18`，依赖 `S1`
  - `R1 = T-20260427-107cf710`，依赖 `S2`
- 当前状态：`已创建修复任务；当前待收口点是公开测试边界`

## 终验 / 复验 / 修复复核记录

- 结论人：`守护最好的爱莉希雅`
- 结论：`通过`
- 验证基线：`origin/main@6667542536a6264f1a62bdc8d271dbf334628cfc`
- 执行目录：`/home/lfr/kernelcode_generate-wt-20260427-dsl-gen-kernel-recheck-2`
- 相关 expectation 摘要：`本计划正文当前未保留 expectation 合同验收资产；本轮只运行正文列出的 pytest 合同验收资产。`
- 最小阻断项或通过摘要：`按正文当前保留命令执行 pytest -q test/dsl/mlir_gen test/dsl/ast/test_visitor_integration.py test/dsl/ast/test_package.py test/dsl/gen_kernel test/tools/test_dsl_run.py test/tools/test_mlir_gen_compare.py test/tools/test_ircheck_runner.py，结果 478 passed, 10 warnings, EXIT:0。当前未再发现公开 API 边界上的直接收口点。`
- 是否已创建修复任务：`是；T-20260427-107cf710（已合并）`

### 补充复验（2026-04-27 / 大闸蟹）

- 结论：`通过`
- 验证基线：`origin/main@6667542536a6264f1a62bdc8d271dbf334628cfc`
- 执行目录：`/home/lfr/kernelcode_generate-wt-20260427-dsl-gen-kernel-recheck-2`
- 合同验收摘要：`按正文当前保留命令执行 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate-wt-20260427-dsl-gen-kernel-recheck-2 pytest -q test/dsl/mlir_gen test/dsl/ast/test_visitor_integration.py test/dsl/ast/test_package.py test/dsl/gen_kernel test/tools/test_dsl_run.py test/tools/test_mlir_gen_compare.py test/tools/test_ircheck_runner.py，结果 478 passed, 10 warnings, EXIT:0。`
- 最小阻断项：`无`

### 当前修复任务（2026-04-27）

- 任务号：`T-20260427-107cf710`
- worktree：`/home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3`
- 记录文件：`/home/lfr/kernelcode_generate/wt-20260427-dsl-gen-kernel-public-api-repair-s3/agents/codex-multi-agents/log/task_records/2026/17/20260427-dsl-gen-kernel-public-api-repair-s3.md`
- 任务类型：`build`
- 任务目标：`删除或改写 test/dsl/ast/test_visitor_integration.py 与 test/dsl/ast/test_package.py 对 kernel_gen.dsl.mlir_gen 非公开 _build_signature_types 的跨文件导入，让正文当前保留的 pytest 合同验收资产只验证公开 API，并跑通正文保留的合同验收命令；不改 expectation。`
- 任务边界：`只处理正文当前保留的 pytest 合同验收资产在公开 API 边界上的收口；不改 expectation，不扩到 execute_engine。`
- 记录要求：`执行记录必须包含真实自检与 Diff 反推自测；测试若仍需跨文件调用非公开 helper，必须如实记录并停止扩写兼容出口。`

## 计划目标

- 为 `kernel_gen.dsl.gen_kernel` 增加新的公开入口 `dsl_gen_kernel(fn, *runtime_args, ...)`，直接完成 DSL 函数到目标源码的前端组装与源码生成。
- 保持现有 `gen_kernel(op|func|module, ctx)` 作为稳定 IR / op 级源码生成入口，不让 callable 新入口回退或破坏旧合同。
- 收回 `build_func_op(...)` 与 `mlir_gen(...)` 的公开 `globals` / `builtins` 参数，消除对外暴露的解析环境注入口径。
- 同步收口 `dsl_run`、`mlir_gen_compare`、`ircheck` 与 `gen_kernel` 相关公开测试，让公开消费者只走保留后的 API。
- 顺手收口 `kernel_gen.dsl.mlir_gen.__all__` 中对带下划线 helper 的错误公开暴露，避免继续把非公开 helper 当包根 API。

## 当前基线

- 当前公开合同：
  - [`spec/dsl/mlir_gen.md`](../../../../../../../spec/dsl/mlir_gen.md) 仍把 `build_func_op(fn, *runtime_args, globals=None, builtins=None)` 与 `mlir_gen(fn, *runtime_args, globals=None, builtins=None, config=None)` 写成公开 API。
  - [`spec/dsl/gen_kernel/gen_kernel.md`](../../../../../../../spec/dsl/gen_kernel/gen_kernel.md) 当前只定义 `gen_kernel(op_or_func, ctx: EmitCContext)`，没有 callable DSL 入口。
- 当前公开 API：
  - [`kernel_gen/dsl/mlir_gen/function_builder.py`](../../../../../../../kernel_gen/dsl/mlir_gen/function_builder.py) 的 `build_func_op(...)` 仍公开接收 `globals` / `builtins`。
  - [`kernel_gen/dsl/mlir_gen/module_builder.py`](../../../../../../../kernel_gen/dsl/mlir_gen/module_builder.py) 的 `mlir_gen(...)` 仍公开接收 `globals` / `builtins`。
  - [`kernel_gen/dsl/mlir_gen/__init__.py`](../../../../../../../kernel_gen/dsl/mlir_gen/__init__.py) 仍把多条带下划线 helper 放进 `__all__`，当前会被视为错误公开面。
  - [`kernel_gen/dsl/gen_kernel/gen_kernel.py`](../../../../../../../kernel_gen/dsl/gen_kernel/gen_kernel.py) 当前仅有 `gen_kernel(obj, ctx)`，其职责是 IR / op 级 emit，不承接 callable DSL 入口。
- 当前实现入口：
  - `mlir_gen` 的解析环境构造仍经由 `parse_env.py` 的内部 helper 处理。
  - `gen_kernel` 的源码生成仍经由 `KernelEmitter` + `emit_c_op(...)` 组合处理。
- 当前测试与公开消费者：
  - [`kernel_gen/tools/dsl_run.py`](../../../../../../../kernel_gen/tools/dsl_run.py) 当前直接调用 `mlir_gen(..., globals=globals_table, config=...)`。
  - [`kernel_gen/tools/mlir_gen_compare.py`](../../../../../../../kernel_gen/tools/mlir_gen_compare.py) 依赖 `mlir_gen(...)` 继续作为稳定 module 级公开入口。
  - [`kernel_gen/tools/ircheck.py`](../../../../../../../kernel_gen/tools/ircheck.py)、[`test/tools/test_ircheck_runner.py`](../../../../../../../test/tools/test_ircheck_runner.py)、[`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../../../../test/dsl/gen_kernel/test_gen_kernel.py) 依赖现有 `gen_kernel(op|func|module, ctx)` 的 IR 入口。
- 当前缺口：
  - 公开 `globals` / `builtins` 删除后，`dsl_run` 与相关 spec / pytest 会先断。
  - callable DSL 源码生成公开入口目前不存在。
  - 包根 `__all__` 仍暴露非公开 helper，违反当前公开 API 边界规则。

## 合同真源顺序

- `API / 参数 / 边界`：
  - [`spec/dsl/mlir_gen.md`](../../../../../../../spec/dsl/mlir_gen.md)
  - [`spec/dsl/ast/parser.md`](../../../../../../../spec/dsl/ast/parser.md)
  - [`spec/dsl/gen_kernel/gen_kernel.md`](../../../../../../../spec/dsl/gen_kernel/gen_kernel.md)
  - 对应实现文件 `API 列表`
  - `pytest`：`test/dsl/mlir_gen/**`、[`test/dsl/ast/test_visitor_integration.py`](../../../../../../../test/dsl/ast/test_visitor_integration.py)、[`test/dsl/ast/test_package.py`](../../../../../../../test/dsl/ast/test_package.py)、`test/dsl/gen_kernel/**`、[`test/tools/test_dsl_run.py`](../../../../../../../test/tools/test_dsl_run.py)、[`test/tools/test_mlir_gen_compare.py`](../../../../../../../test/tools/test_mlir_gen_compare.py)、[`test/tools/test_ircheck_runner.py`](../../../../../../../test/tools/test_ircheck_runner.py)
  - 当前实现
- `源码文本 / 稳定错误短语`：
  - [`spec/dsl/gen_kernel/gen_kernel.md`](../../../../../../../spec/dsl/gen_kernel/gen_kernel.md)
  - [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../../../../test/dsl/gen_kernel/test_gen_kernel.py) 与相关公开消费者测试
  - 当前实现
- `expectation`：本轮不改，只保留为只读终验参考，不写成主合同真源。

## 方案比较与选型

- 不采用方案：继续复用同名 `gen_kernel(...)`，同时在一个公开函数里同时承接 `IR/op` 与 `callable DSL` 两套入口。
- 不采用原因：
  - 现有 `gen_kernel(op|func|module, ctx)` 已被 `ircheck`、`dsl_run`、`test/dsl/gen_kernel/**` 与 e2e 消费；继续叠加 callable 语义会把旧 IR 入口与新 DSL 入口搅在一起。
  - 用户已拍板：保留现有 `gen_kernel(...)`，新增入口另起名为 `dsl_gen_kernel(...)`。
- 采用方案：
  - `S1` 先收 `mlir_gen` 公开入口，删除 `globals` / `builtins` 并同步公开消费者。
  - `S2` 再新增 `dsl_gen_kernel(...)`，让 callable DSL 入口独立存在；旧 `gen_kernel(...)` 完整保留。
- 最小公开接口：
  - `build_func_op(fn, *runtime_args)`
  - `mlir_gen(fn, *runtime_args, config=None)`
  - `gen_kernel(op_or_func_or_module, ctx: EmitCContext) -> str`
  - `dsl_gen_kernel(fn, *runtime_args, ctx: EmitCContext, config: dict[str, object] | None = None) -> str`

## 公开 API 设计

- `build_func_op(fn, *runtime_args) -> func.FuncOp`
- `build_func_op_from_ast(func_ast, runtime_args=None, config=None) -> func.FuncOp`
- `mlir_gen(fn, *runtime_args, config: dict[str, object] | None = None) -> ModuleOp`
- `gen_kernel(obj, ctx: EmitCContext) -> str`
- `dsl_gen_kernel(fn, *runtime_args, ctx: EmitCContext, config: dict[str, object] | None = None) -> str`

```python
from kernel_gen.dsl.mlir_gen import mlir_gen
from kernel_gen.dsl.gen_kernel import EmitCContext, dsl_gen_kernel, gen_kernel

module = mlir_gen(add_kernel, lhs, rhs, config={"reject_external_values": True})
source = dsl_gen_kernel(
    add_kernel,
    lhs,
    rhs,
    ctx=EmitCContext(target="npu_demo"),
    config={"reject_external_values": True, "allow_python_callee_calls": True},
)
func_source = gen_kernel(func_op, EmitCContext(target="npu_demo"))
```

## 完成态定义

- `build_func_op(...)` 与 `mlir_gen(...)` 的公开签名中不再出现 `globals` / `builtins`，对应 spec、文件级 `API 列表` 与 pytest 全部同步。
- 新增 `dsl_gen_kernel(...)` 公开入口，能够对 callable DSL 直接执行 `mlir_gen + gen_kernel` 链路生成目标源码。
- 现有 `gen_kernel(op|func|module, ctx)` 保持不变，公开消费者与错误短语不回退。
- `kernel_gen.dsl.mlir_gen.__all__` 与相关包根导出不再把带下划线 helper 暴露为公开 API。
- `dsl_run`、`mlir_gen_compare`、`ircheck` 与相关 pytest 全部改成只走保留后的公开入口。

## 验收设计

- 验收资产：
  - `pytest -q test/dsl/mlir_gen`
  - `pytest -q test/dsl/ast/test_visitor_integration.py test/dsl/ast/test_package.py`
  - `pytest -q test/dsl/gen_kernel`
  - `pytest -q test/tools/test_dsl_run.py test/tools/test_mlir_gen_compare.py test/tools/test_ircheck_runner.py`
- 锁定结果：
  - `mlir_gen` 公开删参后，公开消费者不再通过 `globals=` / `builtins=` 调用。
  - `dsl_gen_kernel(...)` 能生成与 `mlir_gen + gen_kernel` 组合路径一致的目标源码。
  - `gen_kernel(op|func|module, ctx)` 旧 IR 路径继续可用。
- 必过命令：
  - `pytest -q test/dsl/mlir_gen`
  - `pytest -q test/dsl/ast/test_visitor_integration.py test/dsl/ast/test_package.py`
  - `pytest -q test/dsl/gen_kernel`
  - `pytest -q test/tools/test_dsl_run.py test/tools/test_mlir_gen_compare.py test/tools/test_ircheck_runner.py`
- 补充要求：
  - `Diff 反推测试` 单列，不得用上述最低命令替代。
  - `expectation` 本轮只做只读终验参考，不计入 diff 反推测试。

## 阶段拆分

### S1：收口 mlir_gen 公开入口与公开消费者

#### 阶段目标

- 删除 `build_func_op(...)` / `mlir_gen(...)` 的公开 `globals` / `builtins` 参数，并同步收口 `dsl_run`、`mlir_gen_compare`、相关 spec 与 pytest，让所有公开消费者只走删参后的入口。

#### 非目标

- 不新增 `dsl_gen_kernel(...)`。
- 不改变现有 `gen_kernel(op|func|module, ctx)` 行为。
- 不修改 `expectation`。

#### 目标 spec / API

- [`spec/dsl/mlir_gen.md`](../../../../../../../spec/dsl/mlir_gen.md)
- [`spec/tools/dsl_run.md`](../../../../../../../spec/tools/dsl_run.md)
- [`spec/tools/mlir_gen_compare.md`](../../../../../../../spec/tools/mlir_gen_compare.md)
- `公开 API：build_func_op(...) / mlir_gen(...)`

#### 目标模块范围

- `kernel_gen/dsl/mlir_gen/**`
- `kernel_gen/tools/dsl_run.py`
- `kernel_gen/tools/mlir_gen_compare.py`
- `test/dsl/mlir_gen/**`
- `test/dsl/ast/test_visitor_integration.py`
- `test/dsl/ast/test_package.py`
- `test/tools/test_dsl_run.py`
- `test/tools/test_mlir_gen_compare.py`

#### 禁止修改面 / 合同真源

- `禁止修改面：expectation/**；execute_engine/**`
- `合同真源：spec/dsl/mlir_gen.md > spec/dsl/ast/parser.md > 对应实现文件 API 列表 > test/dsl/mlir_gen/** + test/dsl/ast/test_visitor_integration.py + test/dsl/ast/test_package.py + test/tools/test_dsl_run.py + test/tools/test_mlir_gen_compare.py > 当前实现`

#### 最小功能闭环

- `mlir_gen(...)` 与 `build_func_op(...)` 的公开签名删掉 `globals` / `builtins`。
- `dsl_run` 不再通过 `globals=` 调 `mlir_gen(...)`。
- `mlir_gen_compare` 继续把 `mlir_gen(...)` 当作稳定 module 级公开入口。
- `kernel_gen.dsl.mlir_gen.__all__` 与相关包根导出调整为只暴露公开 API，不再把带下划线 helper 暴露为公开 API；这是 S1 的显式交付物，不得只停留在计划目标。
- 旧 `globals` / `builtins` 公开参数调用必须稳定失败，并由公开 pytest 锁住失败口径。
- `test/dsl/ast/test_visitor_integration.py` 与 `test/dsl/ast/test_package.py` 这类公开消费者同步收口，不再经旧 `globals` / `builtins` 公开参数调用。
- 相关测试不得跨文件直连 `compiler` / `parser` / `mlir_gen` 非公开 helper。

#### 预期示例代码

```python
from kernel_gen.dsl.mlir_gen import build_func_op, mlir_gen

func_op = build_func_op(add_kernel, lhs, rhs)
module = mlir_gen(add_kernel, lhs, rhs, config={"reject_external_values": True})
```

#### 预期输出

```text
build_func_op(...) 和 mlir_gen(...) 的公开签名中不再出现 globals / builtins，公开消费者仍可完成 module 组装与后续工具链调用。
```

#### 目标验收资产

- [`test/dsl/test_mlir_gen.py`](../../../../../../../test/dsl/test_mlir_gen.py)
- [`test/dsl/mlir_gen/test_function_builder.py`](../../../../../../../test/dsl/mlir_gen/test_function_builder.py)
- [`test/dsl/mlir_gen/test_module_builder.py`](../../../../../../../test/dsl/mlir_gen/test_module_builder.py)
- [`test/dsl/ast/test_visitor_integration.py`](../../../../../../../test/dsl/ast/test_visitor_integration.py)
- [`test/dsl/ast/test_package.py`](../../../../../../../test/dsl/ast/test_package.py)
- [`test/tools/test_dsl_run.py`](../../../../../../../test/tools/test_dsl_run.py)
- [`test/tools/test_mlir_gen_compare.py`](../../../../../../../test/tools/test_mlir_gen_compare.py)

#### 验收必过项目

- `pytest -q test/dsl/mlir_gen`
- `pytest -q test/dsl/ast/test_visitor_integration.py test/dsl/ast/test_package.py`
- `pytest -q test/tools/test_dsl_run.py test/tools/test_mlir_gen_compare.py`
- `test/dsl/mlir_gen/**`、`test/dsl/ast/test_visitor_integration.py` 与 `test/dsl/ast/test_package.py` 中补齐旧 `globals` / `builtins` 参数稳定失败覆盖，且不直连非公开 helper`

#### 任务新建建议

- `任务类型：spec`
- `任务目标：删除 build_func_op / mlir_gen 的公开 globals/builtins 参数，显式收口 mlir_gen.__all__ 公开面，并同步 dsl_run、mlir_gen_compare、test/dsl/ast/test_visitor_integration.py、test/dsl/ast/test_package.py 等公开消费者的 spec / 实现 / pytest`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260426-mlir-gen-public-api-s1.md`

### S2：新增 dsl_gen_kernel callable 公开入口并保留旧 gen_kernel

#### 阶段目标

- 新增 `dsl_gen_kernel(fn, *runtime_args, ctx, config=None)` 公开入口，直接完成 callable DSL 到目标源码的完整链路；同时保持现有 `gen_kernel(op|func|module, ctx)` 旧 IR 路径不回退。

#### 非目标

- 不回退 `S1` 的删参结果。
- 不修改 `expectation`。
- 不扩到 `execute_engine/**`。

#### 目标 spec / API

- [`spec/dsl/gen_kernel/gen_kernel.md`](../../../../../../../spec/dsl/gen_kernel/gen_kernel.md)
- [`spec/tools/ircheck.md`](../../../../../../../spec/tools/ircheck.md)
- [`spec/tools/dsl_run.md`](../../../../../../../spec/tools/dsl_run.md)
- `公开 API：dsl_gen_kernel(...) / gen_kernel(...)`

#### 目标模块范围

- `kernel_gen/dsl/gen_kernel/**`
- `kernel_gen/tools/ircheck.py`
- `kernel_gen/tools/dsl_run.py`
- `test/dsl/gen_kernel/**`
- `test/tools/test_ircheck_runner.py`
- `test/tools/test_dsl_run.py`

#### 禁止修改面 / 合同真源

- `禁止修改面：expectation/**；execute_engine/**`
- `合同真源：继承计划总合同真源顺序，即 spec/dsl/mlir_gen.md > spec/dsl/ast/parser.md > spec/dsl/gen_kernel/gen_kernel.md > 对应实现文件 API 列表 > test/dsl/gen_kernel/** + test/tools/test_ircheck_runner.py + test/tools/test_dsl_run.py > 当前实现`

#### 最小功能闭环

- 新增 `dsl_gen_kernel(...)` 公开入口。
- `dsl_gen_kernel(...)` 内部明确走 `mlir_gen + gen_kernel` 链路，而不是复制一份第二套 emitter。
- `gen_kernel(op|func|module, ctx)` 原 IR 入口继续保留。
- `ircheck` 与 `dsl_run` 的公开消费边界不再误用 callable 新入口去替代旧 IR 入口。
- `gen_kernel(op|func|module, ctx)` 旧 IR 路径必须写成硬验收，不允许作为“兼容层默认可变”处理。
- `S2` 只新增 `dsl_gen_kernel(fn, *runtime_args, ctx=..., config=None)` 这一条 callable 公开入口；不新增平行别名入口。

#### 预期示例代码

```python
from kernel_gen.dsl.gen_kernel import EmitCContext, dsl_gen_kernel, gen_kernel

source = dsl_gen_kernel(
    add_kernel,
    lhs,
    rhs,
    ctx=EmitCContext(target="npu_demo"),
    config={"reject_external_values": True, "allow_python_callee_calls": True},
)
func_source = gen_kernel(func_op, EmitCContext(target="npu_demo"))
```

#### 预期输出

```text
dsl_gen_kernel(...) 可直接接受 Python DSL 函数与 runtime_args 生成源码；gen_kernel(...) 继续只消费 op / func.func / builtin.module。
```

#### 目标验收资产

- [`test/dsl/gen_kernel/test_gen_kernel.py`](../../../../../../../test/dsl/gen_kernel/test_gen_kernel.py)
- [`test/tools/test_ircheck_runner.py`](../../../../../../../test/tools/test_ircheck_runner.py)
- [`test/tools/test_dsl_run.py`](../../../../../../../test/tools/test_dsl_run.py)

#### 验收必过项目

- `pytest -q test/dsl/gen_kernel`
- `pytest -q test/tools/test_ircheck_runner.py test/tools/test_dsl_run.py`
- `gen_kernel(op|func|module, ctx)` 旧 IR 路径公开测试继续通过，且 `dsl_gen_kernel(...)` 不回退这条旧路径合同`

#### 任务新建建议

- `任务类型：spec`
- `任务目标：新增 dsl_gen_kernel callable 公开入口，并保持 gen_kernel(op|func|module, ctx) 旧 IR 路径、spec 与 pytest 合同不回退`
- `记录文件：agents/codex-multi-agents/log/task_records/2026/17/20260426-dsl-gen-kernel-s2.md`

## 待确认项

- 当前无额外 API 争议待确认；用户已确认：保留现有 `gen_kernel(...)`，新增入口名为 `dsl_gen_kernel(...)`，并允许按当前主方案推进 `S1=mlir_gen/build_func_op` 公开删参、`S2=dsl_gen_kernel(...)`。

## 用户确认与协同约束

- 用户确认状态：`已确认`
- 已确认事项：
  - 保留现有 `gen_kernel(op|func|module, ctx)`。
  - 新 callable 公开入口名称固定为 `dsl_gen_kernel(...)`。
  - 不改 `expectation`。
  - 范围允许覆盖 `pass/pipeline` 之外的 `gen_kernel/emit` 相关公开消费者，但不扩到 `execute_engine`。
- 未确认事项：`无功能争议；用户已明确“都可以，推进”，本计划采用当前主方案：S1=删 globals/builtins，S2=新增 dsl_gen_kernel(...)。`
- 讨论对象 1：`用户本人 / 当前会话 / 已拍板：保留现有 gen_kernel(op|func|module, ctx)，新增 dsl_gen_kernel(...)，不改 expectation`
- 讨论对象 2：`守护最好的爱莉希雅 / agents/codex-multi-agents/log/talk.log / 建议合同真源分两层写，任务拆为 S1=mlir_gen 公开收口、S2=新 callable 入口；点名 dsl_run、mlir_gen_compare、ircheck、gen_kernel 测试与 mlir_gen.__all__ 为最易漏边界`
- 讨论对象 3：`大闸蟹 / agents/codex-multi-agents/log/talk.log / 最小需改项：S1 必须同步收口 dsl_run 与 spec/dsl/mlir_gen.md/test/dsl/mlir_gen/* 中仍暴露 globals/builtins 的公开消费者；S2 只新增 dsl_gen_kernel(...)，保留现有 gen_kernel(obj, ctx) IR 路径且不改 expectation`
- 讨论对象 4：`提莫炖蘑菇 / agents/codex-multi-agents/log/talk.log / 最小需改项：必须把旧 gen_kernel(op|func|module, ctx) IR 路径写成硬验收，同时补死删参后旧参数稳定失败，且测试不得跨文件直连 compiler/parser/mlir_gen 非公开 helper`
- 讨论对象 5：`睡觉小分队 / agents/codex-multi-agents/log/talk.log / 最小需改项：spec 合同真源顺序先写 spec/dsl/mlir_gen.md -> spec/dsl/ast/parser.md -> spec/dsl/gen_kernel/gen_kernel.md；并在 gen_kernel.md 明确 dsl_gen_kernel(...) 为新增公开入口、现有 gen_kernel(...) 保持 IR 入口不变`
- 讨论对象 6：`金铲铲大作战 / agents/codex-multi-agents/log/talk.log / 通过；同意拆成 S1=删 globals/builtins 并先修 dsl_run，S2=新增 dsl_gen_kernel(...)；关键边界是保留现有 gen_kernel(op|func|module, ctx) 不动且不改 expectation`
- 讨论对象 7：`小李飞刀 / agents/codex-multi-agents/log/talk.log / 通过；支持保持当前顺序：S1 先收 mlir_gen/build_func_op 公开删参与 parse_env 承接，S2 再增 dsl_gen_kernel(...)；点名 dsl_run 的 globals/builtins 公开传参链为首要兼容边界`
- 讨论对象 8：`不要啊教练 / agents/codex-multi-agents/log/talk.log / 最小需改项：建议阶段顺序反转，先收 dsl_gen_kernel(...) 与旧 gen_kernel(...) 并存合同，再收 build_func_op/mlir_gen 的 globals/builtins 公开删除；并提醒测试或跨文件实现不得直连非公开 helper`
- 讨论来源：`默认来自 agents/codex-multi-agents/agents-lists.md；用户本人为本轮拍板对象例外。`
- 留痕方式：`角色讨论默认使用 -talk；用户拍板留在当前会话。`
- 处理要求：`当前已满足计划书起草前置条件且用户已放开阶段顺序分歧；下一步进入架构互评。若互评仍指出影响范围、依赖、完成态或验收口径的新争议，再回到用户拍板。`

## 参考资料

- [`agents/standard/计划书标准.md`](../../../../../../standard/计划书标准.md)
- [`agents/standard/计划书模板.md`](../../../../../../standard/计划书模板.md)
- [`spec/dsl/mlir_gen.md`](../../../../../../../spec/dsl/mlir_gen.md)
- [`spec/dsl/gen_kernel/gen_kernel.md`](../../../../../../../spec/dsl/gen_kernel/gen_kernel.md)
- [`spec/tools/dsl_run.md`](../../../../../../../spec/tools/dsl_run.md)
- [`spec/tools/mlir_gen_compare.md`](../../../../../../../spec/tools/mlir_gen_compare.md)
- [`spec/tools/ircheck.md`](../../../../../../../spec/tools/ircheck.md)
