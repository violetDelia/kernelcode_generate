# execute_engine_api.md

## 功能简介

- 定义执行引擎 `P0` 的请求/结果/参数模型：`CompileRequest / ExecuteRequest / CompiledKernel / ExecuteResult`。
- 冻结字段、默认值与失败短语触发条件，使调用方无需理解实现细节也能稳定调用与比对结果。

## API 列表

- `class CompileRequest(source: str, target: str, function: str, entry_point: str = "kg_execute_entry", compiler: str | None = None, compiler_flags: tuple[str, ...] = ("-std=c++17",), link_flags: tuple[str, ...] = ())`
- `class ExecuteRequest(args: tuple[RuntimeInput, ...], entry_point: str | None = None, capture_function_output: bool = False, stream: None = None)`
- `class CompiledKernel(target: str, soname_path: str, function: str, entry_point: str, compile_stdout: str = "", compile_stderr: str = "")`
- `CompiledKernel.close() -> None`
- `CompiledKernel.execute(args: tuple[RuntimeInput, ...] | None = None, *, request: ExecuteRequest | None = None, entry_point: str | None = None, capture_function_output: bool = False, stream: None = None) -> ExecuteResult`
- `class ExecuteResult(ok: bool, status_code: int, failure_phrase: str | None, compile_stdout: str = "", compile_stderr: str = "", run_stdout: str = "", run_stderr: str = "", elapsed_ms: float = 0.0)`
- `class CompileStrategy(Protocol)`
- `CompileStrategy.compile(self, request: CompileRequest) -> CompiledKernel`
- `register_compile_strategy(target: str, strategy: CompileStrategy, *, override: bool = False) -> None`
- `get_compile_strategy(target: str) -> CompileStrategy`
- `class RuntimeScalarArgInfo(kind: Literal["int", "float"], value: int | float)`（`kernel_gen.execute_engine.runtime_args` 文件级 API，不进入包根导出）
- `class RuntimeMemoryArgInfo(kind: Literal["memory"], dtype: NumericType, shape: tuple[int, ...], stride: tuple[int, ...] | None, is_contiguous: bool)`（`kernel_gen.execute_engine.runtime_args` 文件级 API，不进入包根导出）
- `RuntimeArgInfo: TypeAlias = RuntimeScalarArgInfo | RuntimeMemoryArgInfo`（`kernel_gen.execute_engine.runtime_args` 文件级 API，不进入包根导出）
- `describe_runtime_arg(value: object) -> RuntimeArgInfo | None`（`kernel_gen.execute_engine.runtime_args` 文件级 API，不进入包根导出）
- `invoke_compiled_kernel_capture_output(soname_path: str, entry_point: str, args: tuple[RuntimeInput, ...], allow_absent_memory_args: tuple[AllowAbsentMemoryArg, ...], output_capacity: int = 4096) -> tuple[int, str]`（`kernel_gen.execute_engine.runtime_args` 文件级 API，不进入包根导出）

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/execute_engine/execute_engine_api.md`](spec/execute_engine/execute_engine_api.md)
- `功能实现`：[`kernel_gen/execute_engine/compiler.py`](kernel_gen/execute_engine/compiler.py)
- `功能实现`：[`kernel_gen/execute_engine/strategy.py`](kernel_gen/execute_engine/strategy.py)
- `功能实现`：[`kernel_gen/execute_engine/builtin_strategy/__init__.py`](kernel_gen/execute_engine/builtin_strategy/__init__.py)
- `功能实现`：[`kernel_gen/execute_engine/builtin_strategy/cpu.py`](kernel_gen/execute_engine/builtin_strategy/cpu.py)
- `功能实现`：[`kernel_gen/execute_engine/builtin_strategy/npu_demo.py`](kernel_gen/execute_engine/builtin_strategy/npu_demo.py)
- `功能实现`：[`kernel_gen/execute_engine/builtin_strategy/cuda_sm86.py`](kernel_gen/execute_engine/builtin_strategy/cuda_sm86.py)
- `功能实现`：[`kernel_gen/execute_engine/runtime_args.py`](kernel_gen/execute_engine/runtime_args.py)
- `test`：[`test/execute_engine/test_contract.py`](test/execute_engine/test_contract.py)
- `test`：[`test/execute_engine/test_compile_strategy.py`](test/execute_engine/test_compile_strategy.py)

## 依赖

- 执行引擎总览合同：[`spec/execute_engine/execute_engine.md`](spec/execute_engine/execute_engine.md)
- `emit_c` 输出语义：[`spec/dsl/gen_kernel/emit.md`](spec/dsl/gen_kernel/emit.md)

## 术语

- `failure_phrase`：执行引擎对外固定失败短语集合。

## 目标

- 统一 `CompileRequest/ExecuteRequest/ExecuteResult` 字段与默认值。
- 明确 `args` 与函数形参顺序的一一对应规则。
- 锁定 8 个失败短语与触发条件。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- `P0` 内置真实执行仅支持 `target in {"cpu","npu_demo"}`；第三方 target 可注册 compile strategy，但 execute-only 路径必须以 `execution_unsupported` 失败。
- `compiler.py` 只承接公开请求/结果/facade 和旧公开导入路径；内置 target 编译细节在 `builtin_strategy/` package，运行时参数封送和动态库 entry 调用在 `runtime_args.py`。
- `P0` 不支持 `stream`；当 `ExecuteRequest.stream is not None` 必须失败。
- `capture_function_output=True` 仅在 `target="npu_demo"` 且编译产物存在 `<entry_point>_capture` companion symbol 的 cost summary 场景成功，文本写入 `ExecuteResult.run_stdout`；其它 target 或普通 npu_demo function 必须以 `function_output_capture_not_supported` 失败。
- `args` 必须与 `function` 形参顺序严格一致；不做自动重排或参数推断。
- 运行时参数仅允许 memory / int / float 三类输入；Python / numpy integer scalar 与 Python / numpy floating scalar 进入 ABI 前必须规整为 Python `int` / `float`；`None` 只允许作为源码元数据声明的 allow-absent memory runtime input；其他类型必须失败。
- 失败短语只允许取 8 个固定值（见 `ExecuteResult`）；禁止同义词扩散与 silent fallback。
## API详细说明

### `class CompileRequest(source: str, target: str, function: str, entry_point: str = "kg_execute_entry", compiler: str | None = None, compiler_flags: tuple[str, ...] = ("-std=c++17",), link_flags: tuple[str, ...] = ())`

- api：`class CompileRequest(source: str, target: str, function: str, entry_point: str = "kg_execute_entry", compiler: str | None = None, compiler_flags: tuple[str, ...] = ("-std=c++17",), link_flags: tuple[str, ...] = ())`
- 参数：
  - `source`：源对象、源缓冲区或源文本，提供当前操作读取的数据来源；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `target`：目标对象、目标名称或目标缓冲区，指定当前操作写入或作用的位置；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `function`：Python 函数、DSL 函数或函数级对象，作为构建或执行输入；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `entry_point`：`entry_point` 输入值，参与 `CompileRequest` 的公开处理流程；类型 `str`；默认值 `"kg_execute_entry"`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `compiler`：编译器命令或编译器对象，用于把生成源码编译为可执行产物；类型 `str | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `compiler_flags`：`compiler_flags` 输入值，参与 `CompileRequest` 的公开处理流程；类型 `tuple[str, ...]`；默认值 `("-std=c++17",)`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `link_flags`：`link_flags` 输入值，参与 `CompileRequest` 的公开处理流程；类型 `tuple[str, ...]`；默认值 `()`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`CompileRequest` 实例。
- 使用示例：

  ```python
  compile_request = CompileRequest(source=source, target=target, function=function, entry_point="kg_execute_entry", compiler=None, compiler_flags=compiler_flags, link_flags=link_flags)
  ```
- 功能说明：定义 `CompileRequest` 公开类型。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `class ExecuteRequest(args: tuple[RuntimeInput, ...], entry_point: str | None = None, capture_function_output: bool = False, stream: None = None)`

- api：`class ExecuteRequest(args: tuple[RuntimeInput, ...], entry_point: str | None = None, capture_function_output: bool = False, stream: None = None)`
- 参数：
  - `args`：位置参数序列，按公开调用约定传递给目标函数或工具入口；类型 `tuple[RuntimeInput, ...]`；无默认值，调用方必须显式提供；`RuntimeInput` 的 memory 参数公开形态包含 `torch.Tensor` 与 `numpy.ndarray`，并允许 Python / numpy integer scalar 与 Python / numpy floating scalar；元素 `None` 仅允许在编译产物源码元数据声明对应 index 为 allow-absent memory 时使用；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `entry_point`：`entry_point` 输入值，参与 `ExecuteRequest` 的公开处理流程；类型 `str | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `capture_function_output`：是否启用 npu_demo cost summary companion 文本捕获；类型 `bool`；默认值 `False`；仅 `target="npu_demo"` 且存在 `<entry_point>_capture` companion 的 generated cost summary sink 场景成功，文本写入 `ExecuteResult.run_stdout`；其它场景以 `function_output_capture_not_supported` 失败。
  - `stream`：输入或输出流对象，用于读取源码、写入文本或传递诊断；类型 `None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`ExecuteRequest` 实例。
- 使用示例：

  ```python
  import numpy as np
  import torch

  args = (
      torch.zeros((2, 3)),
      np.zeros((2, 3), dtype=np.float32),
  )
  execute_request = ExecuteRequest(args=args, entry_point=None, capture_function_output=False, stream=None)
  ```
- 功能说明：定义 `ExecuteRequest` 公开类型。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口；`None` runtime input 不改变 `ExecuteRequest` 公开参数列表，执行引擎只能从生成源码注释 `// kg.allow_absent_memory_args: <index>:<dtype>:<rank>;...` 解析 allow-absent metadata。

### `describe_runtime_arg(value: object) -> RuntimeArgInfo | None`

- api：`describe_runtime_arg(value: object) -> RuntimeArgInfo | None`
- 参数：
  - `value`：待描述的真实 runtime 参数；类型为 `object` 是本 API 的公开分类入口语义；调用方通过 `RuntimeArgInfo | None` 判断是否受支持。
- 返回值：`RuntimeScalarArgInfo | RuntimeMemoryArgInfo | None`。
- 使用示例：

  ```python
  from kernel_gen.execute_engine.runtime_args import describe_runtime_arg

  info = describe_runtime_arg(1.5)
  assert info.kind == "float"
  ```
- 功能说明：描述 runtime arg 基础事实，供 execute ABI 与工具层复用同一分类真源。
- 注意事项：Python / numpy integer scalar 返回 `RuntimeScalarArgInfo(kind="int", value=int(value))`；Python / numpy floating scalar 返回 `RuntimeScalarArgInfo(kind="float", value=float(value))`；torch / numpy memory 参数返回 `RuntimeMemoryArgInfo(kind="memory", dtype=<NumericType>, shape=<tuple>, stride=<tuple | None>, is_contiguous=<bool>)`；`bool`、numpy bool scalar、`None`、unsupported dtype、非法 shape 或 unsupported object 返回 `None`；本 API 不返回 data pointer、不分配 ctypes buffer、不加载 entry symbol，也不抛 tools 层错误文本或 execute failure phrase。

### `invoke_compiled_kernel_capture_output(soname_path: str, entry_point: str, args: tuple[RuntimeInput, ...], allow_absent_memory_args: tuple[AllowAbsentMemoryArg, ...], output_capacity: int = 4096) -> tuple[int, str]`

- api：`invoke_compiled_kernel_capture_output(soname_path: str, entry_point: str, args: tuple[RuntimeInput, ...], allow_absent_memory_args: tuple[AllowAbsentMemoryArg, ...], output_capacity: int = 4096) -> tuple[int, str]`
- 参数：
  - `soname_path`：shared object 路径；类型 `str`；无默认值；必须指向真实文件。
  - `entry_point`：普通 C ABI entry 名；类型 `str`；无默认值；companion symbol 固定为 `<entry_point>_capture`。
  - `args`：运行时实参序列；类型 `tuple[RuntimeInput, ...]`；按普通执行入口的 ABI slot 规则封送。
  - `allow_absent_memory_args`：允许 absent memory 的 metadata；类型 `tuple[AllowAbsentMemoryArg, ...]`；按普通执行入口规则消费。
  - `output_capacity`：输出 buffer 容量；类型 `int`；默认 `4096`；必须为正整数。
- 返回值：`tuple[int, str]`，第一项为 companion 返回的原始 status，第二项为 UTF-8 文本；status 非零时文本为空。
- 使用示例：

  ```python
  from kernel_gen.execute_engine.runtime_args import invoke_compiled_kernel_capture_output

  status, text = invoke_compiled_kernel_capture_output("libkernel.so", "kg_execute_entry", (), ())
  ```
- 功能说明：调用已编译 kernel 的输出捕获 companion，并把 companion 写入的 UTF-8 文本返回给 `CompiledKernel.execute(..., capture_function_output=True)`。
- 注意事项：该 API 是 `runtime_args.py` 文件级 API，不进入 `kernel_gen.execute_engine` 包根 `__all__`；缺 companion 必须以 `symbol_resolve_failed` 失败；非法容量、输出溢出或非 UTF-8 必须以 `runtime_throw_or_abort` 失败。

### `class RuntimeScalarArgInfo(kind: Literal["int", "float"], value: int | float)`

- api：`class RuntimeScalarArgInfo(kind: Literal["int", "float"], value: int | float)`
- 参数：
  - `kind`：scalar 分类；只允许 `"int"` 或 `"float"`。
  - `value`：规整后的 Python scalar；类型 `int | float`。
- 返回值：`RuntimeScalarArgInfo` 实例。
- 功能说明：承载 scalar runtime arg 的基础分类结果。
- 注意事项：Python bool 与 numpy bool scalar 不产生该类型。

### `class RuntimeMemoryArgInfo(kind: Literal["memory"], dtype: NumericType, shape: tuple[int, ...], stride: tuple[int, ...] | None, is_contiguous: bool)`

- api：`class RuntimeMemoryArgInfo(kind: Literal["memory"], dtype: NumericType, shape: tuple[int, ...], stride: tuple[int, ...] | None, is_contiguous: bool)`
- 参数：
  - `kind`：memory 分类；固定为 `"memory"`。
  - `dtype`：公开 dtype 真源；类型 `NumericType`。
  - `shape`：规整后的 shape；类型 `tuple[int, ...]`。
  - `stride`：元素单位 stride；类型 `tuple[int, ...] | None`。
  - `is_contiguous`：运行时对象报告的连续性事实；类型 `bool`。
- 返回值：`RuntimeMemoryArgInfo` 实例。
- 功能说明：承载 torch / numpy memory runtime arg 的基础元数据。
- 注意事项：`is_contiguous=False` 不在 describe 层抛错；execute ABI 是否拒绝由 `CompiledKernel.execute(...)` 路径处理。

### `class CompiledKernel(target: str, soname_path: str, function: str, entry_point: str, compile_stdout: str = "", compile_stderr: str = "")`

- api：`class CompiledKernel(target: str, soname_path: str, function: str, entry_point: str, compile_stdout: str = "", compile_stderr: str = "")`
- 参数：
  - `target`：目标对象、目标名称或目标缓冲区，指定当前操作写入或作用的位置；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `soname_path`：公开名称或符号名；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `function`：Python 函数、DSL 函数或函数级对象，作为构建或执行输入；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `entry_point`：`entry_point` 输入值，参与 `CompiledKernel` 的公开处理流程；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `compile_stdout`：`compile_stdout` 输入值，参与 `CompiledKernel` 的公开处理流程；类型 `str`；默认值 `""`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `compile_stderr`：`compile_stderr` 输入值，参与 `CompiledKernel` 的公开处理流程；类型 `str`；默认值 `""`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`CompiledKernel` 实例。
- 使用示例：

  ```python
  compiled_kernel = CompiledKernel(target=target, soname_path=soname_path, function=function, entry_point=entry_point, compile_stdout="", compile_stderr="")
  ```
- 功能说明：定义 `CompiledKernel` 公开类型。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `CompiledKernel.close() -> None`

- api：`CompiledKernel.close() -> None`
- 参数：无。
- 返回值：无返回值；调用成功表示操作完成。
- 使用示例：

  ```python
  compiled_kernel = compiled_kernel
  compiled_kernel.close()
  ```
- 功能说明：执行 `close`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `CompiledKernel.execute(args: tuple[RuntimeInput, ...] | None = None, *, request: ExecuteRequest | None = None, entry_point: str | None = None, capture_function_output: bool = False, stream: None = None) -> ExecuteResult`

- api：`CompiledKernel.execute(args: tuple[RuntimeInput, ...] | None = None, *, request: ExecuteRequest | None = None, entry_point: str | None = None, capture_function_output: bool = False, stream: None = None) -> ExecuteResult`
- 参数：
  - `args`：位置参数序列，按公开调用约定传递给目标函数或工具入口；类型 `tuple[RuntimeInput, ...] | None`；默认值 `None`；外层 `None` 表示使用 `request.args` 或空参数，元素 `None` 仅用于 allow-absent memory runtime input；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `request`：请求对象，承载工具、执行引擎或服务入口需要处理的输入信息；类型 `ExecuteRequest | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `entry_point`：`entry_point` 输入值，参与 `execute` 的公开处理流程；类型 `str | None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `capture_function_output`：是否通过 `<entry_point>_capture` companion 捕获函数输出文本；类型 `bool`；默认值 `False`；仅 npu_demo cost summary companion 场景支持。
  - `stream`：输入或输出流对象，用于读取源码、写入文本或传递诊断；类型 `None`；默认值 `None`；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`ExecuteResult`。
- 使用示例：

  ```python
  compiled_kernel = compiled_kernel
  result = compiled_kernel.execute(args=None, request=None, entry_point=None, capture_function_output=False, stream=None)
  ```
- 功能说明：执行 `execute`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态；当某个 runtime arg 是 `None` 时，仅源码 metadata 中列出的 allow-absent memory index 可被封送为 data=null、shape=`[0]`、stride=`[1]`、rank=1 的 memory slot，缺少 metadata 或 nominal dtype/rank 时必须以 `runtime_throw_or_abort` 失败，错误说明包含 `None` 与 `allow-absent memory metadata` 或 `nominal memory metadata`；`capture_function_output=True` 只允许 `target="npu_demo"` 且存在 `<entry_point>_capture` companion，成功时 `ExecuteResult.run_stdout` 为 companion 写回的 UTF-8 文本，缺 companion 或非 npu_demo target 必须以 `function_output_capture_not_supported` 失败。

### `class ExecuteResult(ok: bool, status_code: int, failure_phrase: str | None, compile_stdout: str = "", compile_stderr: str = "", run_stdout: str = "", run_stderr: str = "", elapsed_ms: float = 0.0)`

- api：`class ExecuteResult(ok: bool, status_code: int, failure_phrase: str | None, compile_stdout: str = "", compile_stderr: str = "", run_stdout: str = "", run_stderr: str = "", elapsed_ms: float = 0.0)`
- 参数：
  - `ok`：`ok` 输入值，参与 `ExecuteResult` 的公开处理流程；类型 `bool`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `status_code`：`status_code` 输入值，参与 `ExecuteResult` 的公开处理流程；类型 `int`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `failure_phrase`：`failure_phrase` 输入值，参与 `ExecuteResult` 的公开处理流程；类型 `str | None`；无默认值，调用方必须显式提供；允许 `None`/空值仅用于签名或默认值显式声明的可选场景；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `compile_stdout`：`compile_stdout` 输入值，参与 `ExecuteResult` 的公开处理流程；类型 `str`；默认值 `""`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `compile_stderr`：`compile_stderr` 输入值，参与 `ExecuteResult` 的公开处理流程；类型 `str`；默认值 `""`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `run_stdout`：`run_stdout` 输入值，参与 `ExecuteResult` 的公开处理流程；类型 `str`；默认值 `""`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `run_stderr`：`run_stderr` 输入值，参与 `ExecuteResult` 的公开处理流程；类型 `str`；默认值 `""`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `elapsed_ms`：`elapsed_ms` 输入值，参与 `ExecuteResult` 的公开处理流程；类型 `float`；默认值 `0.0`；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`ExecuteResult` 实例。
- 使用示例：

  ```python
  execute_result = ExecuteResult(ok=ok, status_code=status_code, failure_phrase=failure_phrase, compile_stdout="", compile_stderr="", run_stdout="", run_stderr="", elapsed_ms=0.0)
  ```
- 功能说明：定义 `ExecuteResult` 公开类型。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

## 测试

- 测试文件：`test/execute_engine/test_contract.py`
- 执行命令：`pytest -q test/execute_engine/test_contract.py`

### 测试目标

- 验证 `spec/execute_engine/execute_engine_api.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证公开执行入口的返回值、输出或状态变化符合预期。
- 验证公开导入、注册名、CLI 或命名空间入口只暴露 spec 定义的 API。
- 验证 DSL、IR 或 EmitC 生成文本与编译链路符合公开合同。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-API-001 | 执行结果 | execute engine contract files exist | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_execute_engine_contract_files_exist`。 | 命令返回码、输出、执行结果或状态变更体现“execute engine contract files exist”场景。 | `test_execute_engine_contract_files_exist` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-API-002 | 公开入口 | execute engine public API exports only runtime contract | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_execute_engine_public_api_exports_only_runtime_contract`。 | 公开入口在“execute engine public API exports only runtime contract”场景下可导入、构造、注册或按名称发现。 | `test_execute_engine_public_api_exports_only_runtime_contract` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-API-003 | 生成/编译 | execute engine compile execute ok | 准备公开 DSL/IR 输入、目标配置与源码生成入口。 | 运行 `test_execute_engine_compile_execute_ok`。 | 生成源码、IR 文本或编译结果体现“execute engine compile execute ok”场景。 | `test_execute_engine_compile_execute_ok` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-API-004 | 执行结果 | execute engine stream not supported | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_execute_engine_stream_not_supported`。 | 命令返回码、输出、执行结果或状态变更体现“execute engine stream not supported”场景。 | `test_execute_engine_stream_not_supported` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-API-005 | 执行结果 | execute engine function output capture not supported | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_execute_engine_function_output_capture_not_supported`。 | 命令返回码、输出、执行结果或状态变更体现“execute engine function output capture not supported”场景。 | `test_execute_engine_function_output_capture_not_supported` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-API-006 | 边界/异常 | execute engine source empty or invalid | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_execute_engine_source_empty_or_invalid`。 | “execute engine source empty or invalid”场景按公开错误语义失败或被拒绝。 | `test_execute_engine_source_empty_or_invalid` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-API-007 | 边界/异常 | execute engine target header mismatch | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_execute_engine_target_header_mismatch`。 | “execute engine target header mismatch”场景按公开错误语义失败或被拒绝。 | `test_execute_engine_target_header_mismatch` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-API-008 | 边界/异常 | execute engine failure phrases frozen | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_execute_engine_failure_phrases_frozen`。 | “execute engine failure phrases frozen”场景按公开错误语义失败或被拒绝。 | `test_execute_engine_failure_phrases_frozen` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-API-009 | 执行结果 | `CompiledKernel.execute(...)` 通过真实 entry 绑定 torch/numpy/int/float 运行参数矩阵。 | 使用固定种子矩阵准备公开 runtime args，并通过 `ExecutionEngine.compile(...)` 生成 shared object。 | 运行 `test_execute_engine_invoke_real_entry_runtime_arg_matrix`。 | 真实 `kg_execute_entry` 收到非空参数数量并返回 `ok=True,status_code=0,failure_phrase=None`。 | `test_execute_engine_invoke_real_entry_runtime_arg_matrix` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-API-010 | 边界/异常 | 真实 entry 返回非零状态时映射到 `runtime_throw_or_abort`。 | 使用公开 `ExecutionEngine.compile(...)` 生成返回非零状态的 entry。 | 运行 `test_execute_engine_invoke_real_entry_nonzero_status_uses_runtime_failure`。 | `CompiledKernel.execute(...)` 抛出 `KernelCodeError`，且 `failure_phrase == "runtime_throw_or_abort"`。 | `test_execute_engine_invoke_real_entry_nonzero_status_uses_runtime_failure` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-API-011 | 边界/异常 | 公开 `CompiledKernel` 对空路径、缺失路径与非法 shared object 的加载失败保持固定失败短语。 | 通过公开 `CompiledKernel(...)` 构造加载失败场景。 | 运行 `test_execute_engine_invoke_public_soname_load_failure_matrix`。 | 空/缺失路径返回 `runtime_throw_or_abort`；非法 shared object 入口解析返回 `symbol_resolve_failed`。 | `test_execute_engine_invoke_public_soname_load_failure_matrix` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-API-012 | 边界/异常 | memory runtime 参数的 dtype、shape、stride 与 flags 边界只经公开 execute 入口校验。 | 使用 torch/numpy 风格公开 runtime 参数占位对象。 | 运行 `test_execute_engine_invoke_public_memory_metadata_matrix`。 | 可字符串化 dtype 与可确认连续布局成功；dtype/shape 缺失或连续性不可确认返回 `runtime_throw_or_abort`。 | `test_execute_engine_invoke_public_memory_metadata_matrix` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-API-013 | 边界/异常 | 真实 shared object 调用前 memory 数据指针缺失时返回固定失败短语。 | 使用公开 `ExecutionEngine.compile(...)` 生成真实 entry，并传入缺失 ctypes 数据指针的 numpy 风格参数。 | 运行 `test_execute_engine_invoke_real_entry_rejects_missing_memory_data_pointer`。 | ABI 封送阶段抛出 `KernelCodeError`，且 `failure_phrase == "runtime_throw_or_abort"`。 | `test_execute_engine_invoke_real_entry_rejects_missing_memory_data_pointer` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-API-014 | 边界/异常 | 真实 shared object 存在但入口符号缺失时返回 `symbol_resolve_failed`。 | 使用公开 `CompiledKernel(...)` 指向已有 shared object 的缺失入口名。 | 运行 `test_execute_engine_invoke_real_entry_missing_exported_symbol`。 | 动态符号解析失败抛出 `KernelCodeError`，且 `failure_phrase == "symbol_resolve_failed"`。 | `test_execute_engine_invoke_real_entry_missing_exported_symbol` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-API-015 | 执行结果 | allow-absent memory `None` runtime input 使用源码 metadata 封送。 | 使用公开 `ExecutionEngine.compile(...)` 生成带 `kg.allow_absent_memory_args` 注释的源码并执行。 | 运行 `test_execute_engine_invoke_allows_none_with_absent_memory_metadata`。 | `None` memory 被封送为 null data 与 rank=1 shape/stride 元数据，真实 entry 可执行。 | `test_execute_engine_invoke_allows_none_with_absent_memory_metadata` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-API-016 | 边界/异常 | 缺少 allow-absent metadata 时拒绝 `None` runtime input。 | 使用不含 allow-absent 注释的公开源码执行 `None` memory。 | 运行 `test_execute_engine_invoke_rejects_none_without_absent_memory_metadata`。 | 以 `runtime_throw_or_abort` 失败，错误说明包含 `None` 与 `allow-absent memory metadata`。 | `test_execute_engine_invoke_rejects_none_without_absent_memory_metadata` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-API-017 | 执行结果 | npu_demo capture companion 返回 stdout 文本。 | 使用公开 `ExecutionEngine.compile(...)` 编译带 `std::string&` summary sink 的 npu_demo source。 | 运行 `test_execute_engine_npu_demo_capture_function_output_returns_run_stdout`。 | `CompiledKernel.execute(..., capture_function_output=True)` 返回 `ok=True` 且 `run_stdout` 为 companion 写回文本。 | `test_execute_engine_npu_demo_capture_function_output_returns_run_stdout` |
| TC-EXECUTE-ENGINE-EXECUTE-ENGINE-API-018 | 边界/异常 | 普通函数或非 npu_demo target 不支持 capture。 | 构造普通 npu_demo source、CPU source 或缺 companion shared object。 | 运行 `test_execute_engine_npu_demo_capture_missing_companion_is_unsupported` 与相关 target 负例。 | 以 `function_output_capture_not_supported` 失败；companion nonzero/overflow 按 `runtime_throw_or_abort` 失败。 | `test_execute_engine_npu_demo_capture_missing_companion_is_unsupported` |
