# execute_engine_target.md

## 功能简介

- 定义执行引擎 `P0` 的 `target` 选择、target 专属 `include` 注入与 `entry shim` 合同。
- 冻结 `entry_point` 命名、`ordered_args` 绑定顺序、编译器默认值与 flags 追加策略，使 `compile -> execute` 在不同 target 下保持机械一致。
- 本文档覆盖 target include、entry shim 与 compiler 三类职责，统一由 `kernel_gen/execute_engine/compiler.py` 承接实现。

## API 列表

- 本文档不新增独立公开 API；target/include/entry shim 行为由 `ExecutionEngine.compile(...)` 承接。

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/execute_engine/execute_engine_target.md`](spec/execute_engine/execute_engine_target.md)
- `功能实现`：[`kernel_gen/execute_engine/compiler.py`](kernel_gen/execute_engine/compiler.py)
- `test`：[`test/execute_engine/test_compile.py`](test/execute_engine/test_compile.py)、[`test/execute_engine/test_invoke.py`](test/execute_engine/test_invoke.py)、[`test/execute_engine/test_contract.py`](test/execute_engine/test_contract.py)

## 依赖

- 执行引擎总览合同：[`spec/execute_engine/execute_engine.md`](spec/execute_engine/execute_engine.md)
- 请求/结果/参数模型：[`spec/execute_engine/execute_engine_api.md`](spec/execute_engine/execute_engine_api.md)
- `emit_c` 输出语义：[`spec/dsl/gen_kernel/emit.md`](spec/dsl/gen_kernel/emit.md)

## 术语

- `target include set`：某个 `target` 在编译阶段必须注入并保持一致的头文件集合。
- `entry shim`：为 C++ 符号或模板/重载函数补齐稳定 `extern "C"` 入口的适配层。
- `ordered_args`：按目标函数形参顺序排列的 内部 ABI 槽位数组。

## 目标

- 冻结 `target=cpu` 与 `target=npu_demo` 的 include 注入结果。
- 冻结 `entry_point` 默认名、`entry shim` C ABI 签名与省略条件。
- 冻结从函数形参到 `ordered_args` 的顺序绑定规则。
- 冻结编译器默认值与 flags 追加规则，避免不同 target 下的隐式回退。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- `P0` 仅支持 `target in {"cpu", "npu_demo"}`；不得扩展新 target。
- `target` 选择只由 `CompileRequest.target` 驱动；不得因为源码内容自动切换到另一 target。
- `target=npu_demo` 不允许以注入 `cpu` include 或回退调用 `cpu::*` 的方式完成编译。
- `entry shim` 只负责统一入口与参数绑定；不改变 `function` 本身的数学语义与参数顺序。
- `ordered_args` 绑定顺序必须与目标函数形参顺序严格一致；不得重排、推断或按名称重新排序。
- 本文档只冻结 target/include/entry shim 合同；`stream`、输出回收与运行时参数类型校验沿用 [`spec/execute_engine/execute_engine.md`](spec/execute_engine/execute_engine.md) 与 [`spec/execute_engine/execute_engine_api.md`](spec/execute_engine/execute_engine_api.md)。
### 内部编译行为

- `ExecutionEngine.compile(...)` 根据 `CompileRequest.target` 选择 target include set。
- `target="npu_demo"` 时只能注入 `#include "include/npu_demo/npu_demo.h"`。
- `target="cpu"` 时必须同时注入 `#include "include/cpu/Memory.h"` 与 `#include "include/cpu/Nn.h"`。
- 当 `compiler is None` 时，编译命令使用 `g++`。
- 编译 flags 必须保留 `-std=c++17` 基线，并按调用方顺序追加 `CompileRequest.compiler_flags`。
- entry shim 仅作为内部桥接逻辑：源码未提供同名 `extern "C"` 入口时，内部生成稳定 C ABI 入口；源码已提供同名入口时可省略。
- `ordered_args` 是内部 ABI 槽位，不作为 Python 公开 API；执行侧只接收 `tuple[RuntimeInput, ...]` 运行时参数。
- 编译器启动失败、返回非零或编译命令无法生成可执行产物时，必须失败并返回 `compile_failed`。
- `entry_point` 或导出符号无法解析时，必须失败并返回 `symbol_resolve_failed`。
- `ordered_args` 数量或顺序与目标函数形参不一致导致执行失败时，必须返回 `runtime_throw_or_abort`。

## API详细说明

本文档不定义独立 API 详细条目。`target`、include 注入、entry shim 与 `ordered_args` 绑定属于 `ExecutionEngine.compile(...)` 的行为约束；参数、返回值和调用示例由 [`spec/execute_engine/execute_engine.md`](spec/execute_engine/execute_engine.md) 与 [`spec/execute_engine/execute_engine_api.md`](spec/execute_engine/execute_engine_api.md) 承接。

## 测试

- 测试文件：
  - `test/execute_engine/test_compile.py`
  - `test/execute_engine/test_contract.py`
  - `test/execute_engine/test_invoke.py`
- 执行命令：
  - `pytest -q test/execute_engine/test_compile.py`
  - `pytest -q test/execute_engine/test_invoke.py`
  - `pytest -q test/execute_engine/test_contract.py`

### 测试目标

- 验证 `spec/execute_engine/execute_engine_target.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证公开导入、注册名、CLI 或命名空间入口只暴露 spec 定义的 API。
- 验证 Memory/DMA 参数、布局、搬运或 verifier 行为。
- 验证 DSL、IR 或 EmitC 生成文本与编译链路符合公开合同。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-TARGET-001 | 公开入口 | `target=npu_demo` 注入 `include/npu_demo/npu_demo.h`，且不回退到 `cpu` include。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `EE-TGT-001`。 | 公开入口在“`target=npu_demo` 注入 `include/npu_demo/npu_demo.h`，且不回退到 `cpu` include。”场景下可导入、构造、注册或按名称发现。 | `EE-TGT-001` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-TARGET-002 | 内存/DMA | `target=cpu` 同时注入 `include/cpu/Memory.h` 与 `include/cpu/Nn.h`。 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `EE-TGT-002`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`target=cpu` 同时注入 `include/cpu/Memory.h` 与 `include/cpu/Nn.h`。”场景。 | `EE-TGT-002` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-TARGET-003 | 生成/编译 | `compiler=None` 时使用 `g++`，并保留 `-std=c++17` 基线。 | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `EE-TGT-003`。 | 生成源码、IR 文本或编译结果体现“`compiler=None` 时使用 `g++`，并保留 `-std=c++17` 基线。”场景。 | `EE-TGT-003` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-TARGET-004 | 生成/编译 | 默认 `entry_point=kg_execute_entry`，且 `ExecuteRequest.entry_point=None` 使用编译产物中的入口名。 | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `EE-TGT-004`。 | 生成源码、IR 文本或编译结果体现“默认 `entry_point=kg_execute_entry`，且 `ExecuteRequest.entry_point=None` 使用编译产物中的入口名。”场景。 | `EE-TGT-004` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-TARGET-005 | 生成/编译 | 源码已提供同名同签名 `extern "C"` 入口时可省略 `entry shim`。 | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `EE-TGT-005`。 | 生成源码、IR 文本或编译结果体现“源码已提供同名同签名 `extern "C"` 入口时可省略 `entry shim`。”场景。 | `EE-TGT-005` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-TARGET-006 | 边界/异常 | target/include family 不一致时返回 `target_header_mismatch`。 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `EE-TGT-006`。 | “target/include family 不一致时返回 `target_header_mismatch`。”场景按公开错误语义失败或被拒绝。 | `EE-TGT-006` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-TARGET-007 | 边界/异常 | 导出入口无法解析时返回 `symbol_resolve_failed`。 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `EE-TGT-007`。 | “导出入口无法解析时返回 `symbol_resolve_failed`。”场景按公开错误语义失败或被拒绝。 | `EE-TGT-007` |
