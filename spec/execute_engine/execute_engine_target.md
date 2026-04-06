# execute_engine_target.md

## 功能简介

- 定义执行引擎 `P0` 的 `target` 选择、target 专属 `include` 注入与 `entry shim` 合同。
- 冻结 `entry_point` 命名、`ordered_args` 绑定顺序、编译器默认值与 flags 追加策略，使 `compile -> execute` 在不同 target 下保持机械一致。
- 本文档覆盖 `target_registry / entry_shim_builder / compiler` 三类实现职责，因此属于一个接口 spec 对应多个实现文件的例外场景。

## 文档信息

- 创建者：咯咯咯
- 最后一次更改：咯咯咯
- spec：[`spec/execute_engine/execute_engine_target.md`](spec/execute_engine/execute_engine_target.md)
- 功能实现：[`kernel_gen/execute_engine/target_registry.py`](kernel_gen/execute_engine/target_registry.py)、[`kernel_gen/execute_engine/entry_shim_builder.py`](kernel_gen/execute_engine/entry_shim_builder.py)、[`kernel_gen/execute_engine/compiler.py`](kernel_gen/execute_engine/compiler.py)
- test：[`test/execute_engine/test_execute_engine_compile.py`](test/execute_engine/test_execute_engine_compile.py)、[`test/execute_engine/test_execute_engine_invoke.py`](test/execute_engine/test_execute_engine_invoke.py)、[`test/execute_engine/test_execute_engine_contract.py`](test/execute_engine/test_execute_engine_contract.py)

## 依赖

- 执行引擎总览合同：[`spec/execute_engine/execute_engine.md`](spec/execute_engine/execute_engine.md)
- 请求/结果/参数模型：[`spec/execute_engine/execute_engine_api.md`](spec/execute_engine/execute_engine_api.md)
- `emit_c` 输出语义：[`spec/dsl/emit_c.md`](spec/dsl/emit_c.md)

## 术语

- `target include set`：某个 `target` 在编译阶段必须注入并保持一致的头文件集合。
- `entry shim`：为 C++ 符号或模板/重载函数补齐稳定 `extern "C"` 入口的适配层。
- `ordered_args`：按目标函数形参顺序排列的 `KgArgSlot` 数组。

## 目标

- 冻结 `target=cpu` 与 `target=npu_demo` 的 include 注入结果。
- 冻结 `entry_point` 默认名、`entry shim` C ABI 签名与省略条件。
- 冻结从函数形参到 `ordered_args` 的顺序绑定规则。
- 冻结编译器默认值与 flags 追加规则，避免不同 target 下的隐式回退。

## 限制与边界

- `P0` 仅支持 `target in {"cpu", "npu_demo"}`；不得扩展新 target。
- `target` 选择只由 `CompileRequest.target` 驱动；不得因为源码内容自动切换到另一 target。
- `target=npu_demo` 不允许以注入 `cpu` include 或回退调用 `cpu::*` 的方式完成编译。
- `entry shim` 只负责统一入口与参数绑定；不改变 `function` 本身的数学语义与参数顺序。
- `ordered_args` 绑定顺序必须与目标函数形参顺序严格一致；不得重排、推断或按名称重新排序。
- 本文档只冻结 target/include/entry shim 合同；`stream`、输出回收与运行时参数类型校验沿用 [`spec/execute_engine/execute_engine.md`](spec/execute_engine/execute_engine.md) 与 [`spec/execute_engine/execute_engine_api.md`](spec/execute_engine/execute_engine_api.md)。

## 公开接口

### `target` 选择与 include 注入

功能说明：

- 根据 `CompileRequest.target` 为最终编译单元选择唯一 target，并注入对应 `include` 集合。

参数说明：

- `target(str)`: `"cpu"` 或 `"npu_demo"`。
- `source(str)`: 原始 C++ 源码；编译前会与 target include set、可选 `entry shim` 一起组成最终编译单元。

使用示例：

```text
target=npu_demo -> #include "include/npu_demo/npu_demo.h"
target=cpu      -> #include "include/cpu/Memory.h"
                  #include "include/cpu/Nn.h"
```

注意事项：

- `target=npu_demo` 时，target include set 只能是 `#include "include/npu_demo/npu_demo.h"`。
- `target=cpu` 时，target include set 必须同时包含 `#include "include/cpu/Memory.h"` 与 `#include "include/cpu/Nn.h"`。
- 引擎必须保证最终编译单元与 `target` 对应的 include family 一致；不得注入另一 target 的 include 作为兜底。
- 调用方显式提供的源码若已包含正确 target include，可保留；但最终结果仍必须满足唯一 target family。

返回与限制：

- 不支持的 `target`，或最终编译单元依赖了与 `target` 不一致的 include family，必须失败并返回 `target_header_mismatch`。
- 在正确 include 已注入的前提下仍然编译失败，必须返回 `compile_failed`。

### `compiler` 默认值与 flags 追加

功能说明：

- 冻结编译器选择与 compile/link flags 的基线规则，保证不同调用路径下的编译命令可复现。

参数说明：

- `compiler(str | None)`: 显式编译器；为 `None` 时默认使用 `g++`。
- `compiler_flags(tuple[str, ...])`: 编译 flags；默认 `("-std=c++17",)`。
- `link_flags(tuple[str, ...])`: 链接 flags；默认 `()`。

使用示例：

```python
CompileRequest(
    target="cpu",
    function="cpu::add",
    compiler=None,
    compiler_flags=("-std=c++17", "-O2"),
    link_flags=(),
)
```

注意事项：

- 当 `compiler is None` 时，引擎必须按 `g++` 生成编译命令。
- 有效编译 flags 必须保留 `-std=c++17` 这一基线；调用方追加的 flags 按 `CompileRequest.compiler_flags` 给出的顺序保留。
- `link_flags` 仅作为调用方追加项；默认空元组不产生额外链接参数。

返回与限制：

- 编译器启动失败、返回非零或编译命令无法生成可执行产物时，必须失败并返回 `compile_failed`。

### `entry_point` 与 `entry shim`

功能说明：

- 为编译产物提供稳定的 `extern "C"` 入口，使运行阶段可以按统一符号名与统一参数槽位调用目标函数。

参数说明：

- `entry_point(str)`: 编译阶段公开导出的入口名；默认 `"kg_execute_entry"`。
- `function(str)`: 目标函数符号；允许 `npu_demo::add`、`cpu::add` 等 C++ 名称。
- `ordered_args(const KgArgSlot*)`: 按目标函数形参顺序排列的参数槽数组。
- `arg_count(unsigned long long)`: `ordered_args` 的槽位数量。

使用示例：

```cpp
extern "C" int kg_execute_entry(const KgArgSlot* ordered_args, unsigned long long arg_count);
```

```text
ordered_args[0]=lhs, ordered_args[1]=rhs, ordered_args[2]=out
ordered_args[0]=lhs, ordered_args[1]=bias, ordered_args[2]=out
```

注意事项：

- `entry_point` 默认名为 `kg_execute_entry`；若 `CompileRequest.entry_point` 显式指定其他名称，导出符号名必须与该值一致。
- 下游执行阶段若 `ExecuteRequest.entry_point is None`，则使用 `CompiledKernel.entry_point`；若显式指定非空值，则按该值解析导出符号。
- `entry shim` 必须用于以下场景：目标函数是 C++ 符号、存在重载/模板实例，或需要把 Python 侧有序参数统一收口到单一 C ABI 入口。
- `entry shim` 仅可在以下场景省略：源码已显式提供稳定 `extern "C"` 入口，且该入口名与 `CompileRequest.entry_point` 一致、签名为 `int <entry_point>(const KgArgSlot* ordered_args, unsigned long long arg_count)`，并且参数顺序可直接对应 `ordered_args`。
- `ordered_args[i]` 必须绑定到目标函数第 `i` 个形参：
  - `MemoryArg` -> `KgArgSlot.kind = KG_ARG_MEMORY`，并使用 `data/shape/stride/rank` 描述 memory view。
  - `IntArg` -> `KgArgSlot.kind = KG_ARG_INT`，并写入 `int_value`。
  - `FloatArg` -> `KgArgSlot.kind = KG_ARG_FLOAT`，并写入 `float_value`。

返回与限制：

- `entry_point` 或导出符号无法解析时，必须失败并返回 `symbol_resolve_failed`。
- `ordered_args` 数量或顺序与目标函数形参不一致导致执行失败时，必须返回 `runtime_throw_or_abort`。

## 测试

- 测试文件：[`test/execute_engine/test_execute_engine_compile.py`](test/execute_engine/test_execute_engine_compile.py)、[`test/execute_engine/test_execute_engine_invoke.py`](test/execute_engine/test_execute_engine_invoke.py)、[`test/execute_engine/test_execute_engine_contract.py`](test/execute_engine/test_execute_engine_contract.py)
- 执行命令：
  - `pytest -q test/execute_engine/test_execute_engine_compile.py`
  - `pytest -q test/execute_engine/test_execute_engine_invoke.py`
  - `pytest -q test/execute_engine/test_execute_engine_contract.py`
- 测试目标：
  - 覆盖 `target=cpu` 与 `target=npu_demo` 的 include 注入结果。
  - 覆盖默认 `compiler=g++`、默认 `-std=c++17` 与 flags 追加顺序。
  - 覆盖默认 `entry_point=kg_execute_entry`、可选覆盖与 `entry shim` 省略条件。
  - 覆盖 `ordered_args` 与函数形参顺序一致的绑定规则。
  - 覆盖 `target_header_mismatch`、`compile_failed`、`symbol_resolve_failed`、`runtime_throw_or_abort` 的最小触发路径。
- 功能与用例清单：
  - `EE-TGT-001`：`target=npu_demo` 注入 `include/npu_demo/npu_demo.h`，且不回退到 `cpu` include。
  - `EE-TGT-002`：`target=cpu` 同时注入 `include/cpu/Memory.h` 与 `include/cpu/Nn.h`。
  - `EE-TGT-003`：`compiler=None` 时使用 `g++`，并保留 `-std=c++17` 基线。
  - `EE-TGT-004`：默认 `entry_point=kg_execute_entry`，且 `ExecuteRequest.entry_point=None` 使用编译产物中的入口名。
  - `EE-TGT-005`：源码已提供同名同签名 `extern "C"` 入口时可省略 `entry shim`。
  - `EE-TGT-006`：target/include family 不一致时返回 `target_header_mismatch`。
  - `EE-TGT-007`：导出入口无法解析时返回 `symbol_resolve_failed`。
