# emit_c_cpp_execution_engine_green_plan.md

## 进度

| 编号 | 前置关系 | 可并行 | worktree | 记录文件 | 进度 |
| --- | --- | --- | --- | --- | --- |
| `S1` | `无` | `否` | `wt-20260407-execute-engine-s1` | `agents/codex-multi-agents/log/task_records/2026/15/20260407-execute-engine-s1.md` | `已合并收口（merge_commit=7dc4068；T-20260407-8cd48f29，李白；push(main)=exit=0）` |
| `S2` | `S1` | `是（可与 S3 并行）` | `wt-20260407-execute-engine-s2` | `agents/codex-multi-agents/log/task_records/2026/15/20260407-execute-engine-s2.md` | `已合并收口（merge_commit=a4118a8；T-20260407-11433946，李白；push(main)=exit=0）` |
| `S3` | `S1` | `是（可与 S2 并行）` | `wt-20260407-execute-engine-s3` | `agents/codex-multi-agents/log/task_records/2026/15/20260407-execute-engine-s3.md` | `已合并收口（merge_commit=fe9803c；T-20260407-aa81c183，李白；push(main)=exit=0）` |
| `S4` | `S2,S3` | `否` | `wt-20260407-execute-engine-s4` | `agents/codex-multi-agents/log/task_records/2026/15/20260407-execute-engine-s4.md` | `已合并收口（merge_commit=ca498d7；T-20260407-df8ea5ae，李白；push(main)=exit=0）` |

## 历史参考

- 默认不回滚已合入代码；本次仅重置计划推进与验收口径。

| 编号 | 前置关系 | 可并行 | worktree | 记录文件 | 历史状态 |
| --- | --- | --- | --- | --- | --- |
| `S1` | `无` | `否` | `wt-20260406-execute-engine-s1` | `20260406-execute-engine-s1.md` | `已合并收口（merge_commit=e1d6632；T-20260406-8293c2f3，李白；push(main)=0）。` |
| `S2` | `S1` | `是（可与 S3 并行）` | `wt-20260406-execute-engine-s1` | `20260406-execute-engine-s1.md` | `已合并收口（merge_commit=e1d6632；T-20260406-8293c2f3，李白；push(main)=0）。` |
| `S3` | `S1` | `是（可与 S2 并行）` | `wt-20260406-execute-engine-s3` | `20260406-execute-engine-s3.md` | `进行中（T-20260406-56e3e942 -> 咯咯咯）。` |
| `S4` | `S2,S3` | `否` | `待分配` | `待创建` | `未开始` |

## 评审摘要

- 已评审通过。
- 本次按“从 0 重新开始”重置主表；历史推进信息保留在“历史参考”中，仅供追溯。
- `S1~S4` 统一改为“收口任务（规格+实现+测试）”，不再保留仅文档完成态。
- 评审人：`大闸蟹`、`守护最好的爱莉希雅`。

## 双架构师最终验收摘要（2026-04-07）

- 最终验收结论：`通过（可归档 done_plan）`。
- 核对依据：
  - `S1~S4` 均已合并收口：`7dc4068 / a4118a8 / fe9803c / ca498d7`。
  - `agents/codex-multi-agents/log/task_records/2026/15/20260407-execute-engine-s4.md` 记录的存在性检查通过：`spec/execute_engine/*`、`test/execute_engine/*`。
  - `pytest -q test/execute_engine/test_execute_engine_contract.py`、`pytest -q test/execute_engine/test_execute_engine_compile.py`、`pytest -q test/execute_engine/test_execute_engine_invoke.py` 均 `exit=0`。
  - `PYTHONPATH=. python expectation/dsl/emit_c/npu_demo/add.py` 复跑 `exit=0`。
- 阻断项：`无`。
- 评审人：`大闸蟹`、`守护最好的爱莉希雅`。

## 功能说明

- 本计划定义执行引擎 `P0` 合同：输入 `source/target/function/args(memory|int|float)`，执行引擎补齐 `include + 入口适配层(entry shim，可选)`，再完成编译与运行。
- 本计划采用两段式流程：`compile` 与 `execute` 分离。
- 本计划只覆盖 `cpu` 与 `npu_demo`；`stream` 暂不支持；函数输出暂不回收，但保留扩展位。
- 本计划目录口径固定为“新建 `execute_engine` 目录树”，不复用 `runtime` 目录名。
- 目标落点固定为：`spec/execute_engine/*`、`test/execute_engine/*`、`kernel_gen/execute_engine/*`。
- 本计划所有阶段都按“规格 + 实现 + 测试”一起收口，不保留只补文档但未形成可执行结果的阶段完成态。
- 只要信息不清楚，必须先向用户确认，不允许自行猜测。

## 讨论结论

### 计划目标

- 形成稳定入口 `ExecutionEngine.compile(...).execute(...)`，可运行 emit C 生成的 C++ 代码，覆盖 `memory/int/float` 三类参数。
- 让 `cpu` 与 `npu_demo` 两个 target 具备一致的调用入口、include 选择规则与失败短语。

### 是否有更合理的方案

- 当前采用“新建 `execute_engine` 目录树”的方案，不复用 `runtime`，更利于把编译与执行语义收在同一处。
- 当前阶段不直接切到 MLIR `ExecutionEngine` 或 LLVM `LLJIT`，先以 C++ 编译 + 动态加载打通最小闭环，后续再扩展更合适。

### 依赖

- 上游依赖 `emit_c` 已能产出可编译源码，至少覆盖 `cpu` 与 `npu_demo` 的基础调用体。
- 下游依赖 `include/cpu/*` 与 `include/npu_demo/*` 已存在稳定头文件接口。
- Python 侧依赖 `ctypes` / `subprocess` / `numpy` 或 `torch` 的基础调用能力。

### 验证合理性

- 先确认目录与文件存在，再分别验证合同、编译、调用三类测试，最后补一条 emit C expectation 作为端到端样例。
- 每一步都要求失败短语可机械匹配，避免同类失败出现多种写法。

### 可维护性

- 每个阶段只收一类能力：共享骨架、编译路径、调用路径、总体对齐，范围清楚。
- 规格、实现、测试在同一阶段一起变化，后续定位问题时更容易直接对应到单个阶段。

## 六项结论摘要（V2）

- `目标`：形成稳定入口 `ExecutionEngine.compile(...).execute(...)`，可运行 emit C 产生的 C++ 片段，覆盖 `memory/int/float` 三类输入。
- `边界`：不扩 `stream`、不扩异步调度、不扩函数输出读取、不改 `ast/mlir_gen/lowering/emit_c` 语义。
- `前置约束`：
  1. 主表所有阶段都按“规格 + 实现 + 测试”一起收口，不保留只补文档的完成态。
  2. 所有失败路径统一使用同一套失败短语，不允许同义多写法。
  3. `target` 与 include 映射必须可机械检查：`npu_demo -> include/npu_demo/*`，`cpu -> include/cpu/*`。
  4. 不允许 `target=npu_demo` 时回退到 `cpu::*`。
  5. 每个阶段都必须同时更新规格、实现与测试，再执行该阶段要求的测试项目。
- `必须测试通过项目`（固定顺序，完成态执行）：
  1. `test -f spec/execute_engine/execute_engine.md && test -f spec/execute_engine/execute_engine_api.md && test -f spec/execute_engine/execute_engine_target.md`
  2. `test -f test/execute_engine/test_execute_engine_contract.py && test -f test/execute_engine/test_execute_engine_compile.py && test -f test/execute_engine/test_execute_engine_invoke.py`
  3. `pytest -q test/execute_engine/test_execute_engine_contract.py`
  4. `pytest -q test/execute_engine/test_execute_engine_compile.py`
  5. `pytest -q test/execute_engine/test_execute_engine_invoke.py`
  6. `PYTHONPATH=. python expectation/dsl/emit_c/npu_demo/add.py`
- `失败短语`：
  - `target_header_mismatch`
  - `source_empty_or_invalid`
  - `compile_failed`
  - `symbol_resolve_failed`
  - `runtime_throw_or_abort`
  - `stream_not_supported`
  - `function_output_capture_not_supported`
- `不可改文件`：沿用仓库 `[immutable]` / `[immutable-file]` 默认规则，无额外豁免。

## 执行引擎关键 md 规划

### 1) 总览文档

- [`spec/execute_engine/execute_engine.md`](spec/execute_engine/execute_engine.md)（新增）
- 内容要求：
  - 生命周期：`compile -> execute`
  - 支持输入：`source/target/function/args`
  - 非目标：`stream`、输出回收
  - 成功判定：无异常退出、返回码为 `0`

### 2) 接口文档

- [`spec/execute_engine/execute_engine_api.md`](spec/execute_engine/execute_engine_api.md)（新增）
- 内容要求：
  - `CompileRequest / ExecuteRequest / CompiledKernel / ExecuteResult`
  - `MemoryArg / IntArg / FloatArg`
  - 默认值与可选项
  - 失败短语与触发条件
  - 未来扩展位（输出回收）

### 3) target 选择与入口适配文档

- [`spec/execute_engine/execute_engine_target.md`](spec/execute_engine/execute_engine_target.md)（新增）
- 内容要求：
  - target 到 include 映射
  - 编译器默认值与 flags 追加策略
  - `entry_point` 命名规范
  - `entry shim` 何时必须/何时可省略
  - `extern "C"` 入口约定

## 接口规范（P0）

### Python 请求模型

```python
@dataclass(frozen=True)
class CompileRequest:
    source: str
    target: str
    function: str              # 允许 "npu_demo::add"
    entry_point: str = "kg_execute_entry"
    compiler: str | None = None
    compiler_flags: tuple[str, ...] = ("-std=c++17",)
    link_flags: tuple[str, ...] = ()

@dataclass(frozen=True)
class ExecuteRequest:
    args: tuple["ArgSpec", ...]  # 必须与 function 形参顺序一致
    entry_point: str | None = None
    capture_function_output: bool = False
    stream: object | None = None
```

### Python 结果模型

```python
@dataclass(frozen=True)
class CompiledKernel:
    target: str
    soname_path: str
    function: str
    entry_point: str
    compile_stdout: str
    compile_stderr: str

@dataclass(frozen=True)
class ExecuteResult:
    ok: bool
    status_code: int
    failure_phrase: str | None
    compile_stdout: str
    compile_stderr: str
    run_stdout: str
    run_stderr: str
    elapsed_ms: float
```

### 参数模型

```python
@dataclass(frozen=True)
class MemoryArg:
    position: int
    param_name: str | None
    space: str
    dtype: str
    shape: tuple[int, ...]
    stride: tuple[int, ...] | None
    value: object   # torch.Tensor | numpy.ndarray

@dataclass(frozen=True)
class IntArg:
    position: int
    param_name: str | None
    dtype: str
    value: int

@dataclass(frozen=True)
class FloatArg:
    position: int
    param_name: str | None
    dtype: str
    value: float
```

### C ABI 入口适配层（entry shim）

```cpp
enum KgArgKind : unsigned int {
    KG_ARG_MEMORY = 1,
    KG_ARG_INT = 2,
    KG_ARG_FLOAT = 3
};

struct KgMemoryView {
    void* data;
    const long long* shape;
    const long long* stride;
    unsigned long long rank;
};

struct KgArgSlot {
    KgArgKind kind;
    KgMemoryView memory;
    long long int_value;
    double float_value;
};

extern "C" int kg_execute_entry(const KgArgSlot* ordered_args, unsigned long long arg_count);
```

### entry shim 必要性说明（P0）

- 必须使用 `entry shim` 的场景：
  - 入口函数是 `npu_demo::add` / `cpu::add` 这类 C++ 符号（`dlsym` 不能直接稳定按原名解析）。
  - 原函数存在重载或模板实例，运行时调用点无法仅靠函数名唯一定位。
  - 需要把 Python 侧有序参数统一映射为单一 C ABI 入口。
- 可省略 `entry shim` 的场景：
  - 输入源码已显式提供稳定 `extern "C"` 入口，且签名就是 `kg_execute_entry(const KgArgSlot*, arg_count)`。
  - 参数顺序可直接对应 `ordered_args`，不需要额外改写。

## 源码示例与预期输出

### 示例 1：`target=npu_demo`，`memory + memory`

输入片段：

```cpp
void kernel_add(const Memory<GM, int32_t>& lhs, const Memory<GM, int32_t>& rhs, Memory<GM, int32_t>& out) {
    npu_demo::add(lhs, rhs, out);
}
```

预期输出：

```text
生成源码包含: #include "include/npu_demo/npu_demo.h"
生成源码包含: npu_demo::add(
入口参数顺序: ordered_args[0]=lhs, ordered_args[1]=rhs, ordered_args[2]=out
执行结果: ok=True, status_code=0, failure_phrase=None
```

### 示例 2：`target=cpu`，`memory + int`

输入片段：

```cpp
void kernel_add_scalar(const Memory<GM, int32_t>& lhs, long long bias, Memory<GM, int32_t>& out) {
    cpu::add(lhs, bias, out);
}
```

预期输出：

```text
生成源码包含: #include "include/cpu/Memory.h"
生成源码包含: #include "include/cpu/Nn.h"
入口参数顺序: ordered_args[0]=lhs, ordered_args[1]=bias, ordered_args[2]=out
执行结果: ok=True, status_code=0, failure_phrase=None
```

### 示例 3：`capture_function_output=True`

预期输出：

```text
ok=False
failure_phrase=function_output_capture_not_supported
```

### 示例 4：`stream` 非空

预期输出：

```text
ok=False
failure_phrase=stream_not_supported
```

## 计划任务

### `S1`

- `任务类型`：`收口任务（规格+实现+测试）`
- `目标`：建好 `execute_engine` 目录骨架，收口共享请求模型、最小 `compile/execute` 壳层、总览文档与合同测试，让执行引擎具备统一入口。
- `边界`：只做共享骨架与公共失败短语，不要求此阶段完成真实调用。
- `注意事项`：
  - `ExecutionEngine` 与请求模型命名在本阶段定稳，后续阶段只能补能力，不能随意改接口。
  - `source_empty_or_invalid`、`stream_not_supported`、`function_output_capture_not_supported` 在本阶段就要统一。
  - 如字段语义不清，先问用户再写。
- `预期示例代码`：
```python
engine = ExecutionEngine(target="cpu")
compiled = engine.compile(
    CompileRequest(
        source="extern \"C\" int kg_execute_entry(...) { return 0; }",
        target="cpu",
        function="cpu::noop",
    )
)
```
- `预期输出`：
```text
目录存在: spec/execute_engine/*, test/execute_engine/*, kernel_gen/execute_engine/*
接口存在: ExecutionEngine.compile(...), CompiledKernel.execute(...)
失败短语统一: source_empty_or_invalid / stream_not_supported / function_output_capture_not_supported
```
- `必须测试通过项目`：
  - `test -f spec/execute_engine/execute_engine.md && test -f spec/execute_engine/execute_engine_api.md && test -f spec/execute_engine/execute_engine_target.md`
  - `test -f test/execute_engine/test_execute_engine_contract.py`
  - `pytest -q test/execute_engine/test_execute_engine_contract.py`

### `S2`

- `任务类型`：`收口任务（规格+实现+测试）`
- `目标`：收口编译路径：`CompileRequest -> 目标头文件选择 -> 编译器调用 -> CompiledKernel`，并完成对应规格与编译测试。
- `边界`：只收编译侧，不要求此阶段完成真实执行结果检查。
- `注意事项`：
  - `target=npu_demo` 只能落到 `include/npu_demo/*`，不能回退成 `cpu::*`。
  - `compiler` 默认值、默认 flags、额外 flags 的拼接顺序要固定。
  - 编译失败时统一收口到 `compile_failed`。
- `预期示例代码`：
```python
compiled = engine.compile(
    CompileRequest(
        source=source,
        target="npu_demo",
        function="npu_demo::add",
    )
)
```
- `预期输出`：
```text
生成源码包含: #include "include/npu_demo/npu_demo.h"
编译结果包含: soname_path / compile_stdout / compile_stderr
失败时短语固定: compile_failed
```
- `必须测试通过项目`：
  - `test -f test/execute_engine/test_execute_engine_compile.py`
  - `pytest -q test/execute_engine/test_execute_engine_compile.py`

### `S3`

- `任务类型`：`收口任务（规格+实现+测试）`
- `目标`：收口调用路径：参数绑定、`entry shim`、动态加载与执行返回，完成 `memory/int/float` 三类参数的调用与对应测试。
- `边界`：只覆盖同步调用；`stream` 与函数返回值回收继续显式不支持。
- `注意事项`：
  - `entry shim` 的参数顺序必须和 `function` 形参顺序一致。
  - `symbol_resolve_failed` 与 `runtime_throw_or_abort` 的触发条件要能直接复现。
  - `MemoryArg` 同时支持 `numpy.ndarray` 与 `torch.Tensor` 输入。
- `预期示例代码`：
```python
result = compiled.execute(
    ExecuteRequest(
        args=(lhs_arg, rhs_arg, out_arg),
        capture_function_output=False,
        stream=None,
    )
)
```
- `预期输出`：
```text
执行结果: ok=True, status_code=0, failure_phrase=None
失败短语固定: symbol_resolve_failed / runtime_throw_or_abort / stream_not_supported / function_output_capture_not_supported
入口适配存在: kg_execute_entry(const KgArgSlot*, unsigned long long)
```
- `必须测试通过项目`：
  - `test -f test/execute_engine/test_execute_engine_invoke.py`
  - `pytest -q test/execute_engine/test_execute_engine_invoke.py`

### `S4`

- `任务类型`：`收口任务（规格+实现+测试）`
- `目标`：统一收口 `spec + 实现 + 测试 + expectation` 的最终状态，把前 3 个阶段的结果对齐到一个可直接复跑的版本。
- `边界`：不扩新 target，不扩 stream，不扩函数输出读取。
- `注意事项`：
  - 本阶段只允许收已经确认的能力，不允许顺手加新接口。
  - 计划文档、规格、实现、测试、expectation 中的用词要一致。
- `预期示例代码`：
```python
source = emit_c(...)
engine = ExecutionEngine(target="npu_demo")
kernel = engine.compile(compile_req)
result = kernel.execute(execute_req)
```
- `预期输出`：
```text
计划、规格、实现、测试、expectation 口径一致
可以连续执行合同测试、编译测试、调用测试与 emit_c expectation
```
- `必须测试通过项目`：
  - `pytest -q test/execute_engine/test_execute_engine_contract.py`
  - `pytest -q test/execute_engine/test_execute_engine_compile.py`
  - `pytest -q test/execute_engine/test_execute_engine_invoke.py`

## 必须测试通过项目

1. `test -f spec/execute_engine/execute_engine.md && test -f spec/execute_engine/execute_engine_api.md && test -f spec/execute_engine/execute_engine_target.md`
2. `test -f test/execute_engine/test_execute_engine_contract.py && test -f test/execute_engine/test_execute_engine_compile.py && test -f test/execute_engine/test_execute_engine_invoke.py`
3. `pytest -q test/execute_engine/test_execute_engine_contract.py`
4. `pytest -q test/execute_engine/test_execute_engine_compile.py`
5. `pytest -q test/execute_engine/test_execute_engine_invoke.py`
6. `PYTHONPATH=. python expectation/dsl/emit_c/npu_demo/add.py`

## 外部项目与案例参考

- Python `ctypes`：https://docs.python.org/3/library/ctypes.html
- Python `subprocess`：https://docs.python.org/3/library/subprocess.html
- NumPy `ctypeslib`：https://numpy.org/doc/stable/reference/routines.ctypeslib.html
- Linux `dlopen/dlsym`：https://man7.org/linux/man-pages/man3/dlopen.3.html、https://man7.org/linux/man-pages/man3/dlsym.3.html
- C++ `extern "C"`：https://en.cppreference.com/w/cpp/language/language_linkage
- PyTorch `Tensor.data_ptr` / `from_numpy`：https://docs.pytorch.org/docs/stable/generated/torch.Tensor.data_ptr.html、https://pytorch.org/docs/stable/generated/torch.from_numpy.html
- MLIR ExecutionEngine（后续可选路线）：https://mlir.llvm.org/doxygen/classmlir_1_1ExecutionEngine.html
- LLVM LLJIT 示例（后续可选路线）：https://llvm.googlesource.com/llvm-project/llvm/+/refs/heads/main/examples/HowToUseLLJIT/HowToUseLLJIT.cpp

## 文档信息

- 创建者：`守护最好的爱莉希雅`
- 最后修改人：`大闸蟹`
- `文档`：[`ARCHITECTURE/plan/emit_c_cpp_execution_engine_green_plan.md`](ARCHITECTURE/plan/emit_c_cpp_execution_engine_green_plan.md)
- `spec`：
  - [`spec/execute_engine/execute_engine.md`](spec/execute_engine/execute_engine.md)
  - [`spec/execute_engine/execute_engine_api.md`](spec/execute_engine/execute_engine_api.md)
  - [`spec/execute_engine/execute_engine_target.md`](spec/execute_engine/execute_engine_target.md)
- `test`：
  - [`test/execute_engine/test_execute_engine_contract.py`](test/execute_engine/test_execute_engine_contract.py)
  - [`test/execute_engine/test_execute_engine_compile.py`](test/execute_engine/test_execute_engine_compile.py)
  - [`test/execute_engine/test_execute_engine_invoke.py`](test/execute_engine/test_execute_engine_invoke.py)
- `功能实现`：
  - [`kernel_gen/execute_engine/execute_engine.py`](kernel_gen/execute_engine/execute_engine.py)
  - [`kernel_gen/execute_engine/compiler.py`](kernel_gen/execute_engine/compiler.py)
  - [`kernel_gen/execute_engine/arg_binding.py`](kernel_gen/execute_engine/arg_binding.py)
  - [`kernel_gen/execute_engine/entry_shim_builder.py`](kernel_gen/execute_engine/entry_shim_builder.py)
  - [`kernel_gen/execute_engine/target_registry.py`](kernel_gen/execute_engine/target_registry.py)
