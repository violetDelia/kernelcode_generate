# analysis_engine

## 功能简介

定义 `analysis(op, config, otherargs=None)` 统一分析入口及其结果结构。该入口负责承接单个 IR op 与 `func.func` 两种分析目标，正式结果以 `AnalysisResult` 为准，显式公开 `compute_items / memory_items / compute_totals_by_kind / memory_totals_by_path`；`analyze_kernel(...)` 等旧接口若仍存在，只允许作为 facade / adapter，不再单独定义主线合同。

## 文档信息

- 创建者：`朽木露琪亚`
- 最后一次更改：`朽木露琪亚`
- `spec`：[`spec/analysis/analysis_engine.md`](../../spec/analysis/analysis_engine.md)
- `功能实现`：
  - [`kernel_gen/analysis/analysis.py`](../../kernel_gen/analysis/analysis.py)
  - [`kernel_gen/analysis/compute/__init__.py`](../../kernel_gen/analysis/compute/__init__.py)
  - [`kernel_gen/analysis/compute/kernel.py`](../../kernel_gen/analysis/compute/kernel.py)
  - [`kernel_gen/analysis/compute/nn.py`](../../kernel_gen/analysis/compute/nn.py)
  - [`kernel_gen/analysis/memory/__init__.py`](../../kernel_gen/analysis/memory/__init__.py)
  - [`kernel_gen/analysis/memory/dma.py`](../../kernel_gen/analysis/memory/dma.py)
- `test`：[`test/analysis/test_analysis.py`](../../test/analysis/test_analysis.py)

## 依赖

- [`spec/analysis/analysis_kernel.md`](../../spec/analysis/analysis_kernel.md)：旧 facade/兼容公式入口约束。
- [`spec/pass/analysis/func_cost.md`](../../spec/pass/analysis/func_cost.md)：`func_cost` 对 derived alias 的消费口径。
- [`spec/dialect/nn.md`](../../spec/dialect/nn.md)：`nn.memory` 与 `nn.*` op 类型约束。
- [`spec/dialect/dma.md`](../../spec/dialect/dma.md)：公开 DMA 分支语义。
- [`kernel_gen/analysis/compute/__init__.py`](../../kernel_gen/analysis/compute/__init__.py)：`ComputeKind` 正式枚举。
- [`kernel_gen/analysis/compute/kernel.py`](../../kernel_gen/analysis/compute/kernel.py)：`kernel.*` 标量计算分类实现。
- [`kernel_gen/analysis/compute/nn.py`](../../kernel_gen/analysis/compute/nn.py)：`nn.*` 逐元素与 `nn.matmul` 计算分类实现。

## 目标

- 冻结统一入口：`analysis(op, config, otherargs=None) -> AnalysisResult`。
- 冻结计算主线目录化入口：`kernel_gen/analysis/compute/__init__.py`、`kernel_gen/analysis/compute/kernel.py`、`kernel_gen/analysis/compute/nn.py`。
- 冻结访存主线目录化口径：`kernel_gen/analysis/memory/` 负责 `MemoryPath`、`time_ns` 公式与 DMA 分支。
- 冻结 `AnalysisConfig` 的显式控制字段：
  - `enable_compute`
  - `enable_memory`
  - `target`
  - `metric_overrides`
  - `write_op_attrs`
  - `write_func_attrs`
  - `predicate_size`
  - `dtype_size_overrides`
  - `otherargs`
- 冻结 `path_bandwidth / path_latency_ns / theoretical_compute` 的来源：
  - 默认必须来自 `target registry` 中当前 target 的 analysis 默认参数。
  - 当前默认 target 固定为 `npu_demo`。
  - 调用方只能通过 `metric_overrides` 做显式覆盖，不再把原始指标字典当作长期公开输入。
- 冻结新结果结构：
  - `compute_items`
  - `memory_items`
  - `compute_totals_by_kind`
  - `memory_totals_by_path`
- 冻结正式计算分类枚举：`ComputeKind = {SCALAR, VECTOR, TENSOR, MATH}`。
- 冻结正式 `MemoryPath` 枚举至少包含：
  - `GM_TO_SM`
  - `SM_TO_LM`
  - `GM_TO_LM`
  - `GM_TO_TSM`
  - `TSM_TO_TLM`
  - `FM_TO_TSM`
- 冻结访存时间公式：当某条 `memory_items` 同时命中 `bytes`、`latency_ns`、`bandwidth` 时，
  - `time_ns = latency_ns + bytes / bandwidth`
- 明确默认不写 `analysis.*` 属性；只有显式开启 `write_op_attrs` / `write_func_attrs` 时才写回。

## 限制与边界

- 本层是长期主线；`analyze_kernel(...)`、`func_cost` 等只能消费本层结果或做 derived alias。
- 本轮 `compute` 分类只要求至少能产出当前已承接的：
  - `ComputeKind.SCALAR`
  - `ComputeKind.VECTOR`
  - `ComputeKind.TENSOR`
- 本轮 `memory` 分类只要求保证 `memory_items` 与 `memory_totals_by_path` 可机械读取；对 compute op 可使用泛化 path（如 `GM->compute` / `compute->GM`），对当前已公开 DMA 分支应优先使用 source/target space 路径。
- 当前已公开 DMA 访存分支是 `dma.copy`、`dma.load`、`dma.store`、`dma.slice`；它们的前置条件非法时必须 `hard error`。
- 当前未公开 DMA 分支（如 `dma.alloc`、`dma.deslice`、`dma.free`）继续执行 `skip + warning`，不计入正式 `memory_items / memory_totals_by_path`。
- `write_op_attrs=False` / `write_func_attrs=False` 时，不得产生任何新的 `analysis.*` attribute。
- 旧 `compute/read_bytes/write_bytes` 若仍暴露，只允许是由 `AnalysisResult` 派生的 alias。
- 一旦 `npu_demo` 的 analysis 默认参数缺字段或读取失败，必须显式报错；不允许静默回退到 analysis 侧手写常量。

## 公开接口

### `class AnalysisConfig`

- 功能说明：统一入口配置对象。
- 参数说明：
  - `enable_compute: bool`
  - `enable_memory: bool`
  - `target: str`
  - `metric_overrides: Mapping[str, Mapping[str, object]] | None`
  - `write_op_attrs: bool`
  - `write_func_attrs: bool`
  - `predicate_size: int`
  - `dtype_size_overrides: dict[str, int] | None`
  - `otherargs: Iterable[object] | None`
- 使用示例：`AnalysisConfig(enable_compute=True, enable_memory=False, target="npu_demo", write_op_attrs=True)`
- 注意事项：
  - 默认不写回属性；写回只能由显式开关触发。
  - `path_bandwidth/path_latency_ns/theoretical_compute` 是配置对象内部解析出的正式基线结果，不再作为调用方长期手写输入。
- 返回与限制：作为 `analysis(...)` 的必填配置对象。

### `class ComputeItem`

- 功能说明：显式记录一条计算分类项。
- 参数说明：
  - `kind: ComputeKind`
  - `amount: sympy.Basic`
  - `dtype: str`
- 使用示例：`ComputeItem(kind=ComputeKind.SCALAR, amount=1, dtype="i32")`
- 注意事项：本层先冻结 item schema，不在本文件里扩展 target-specific 吞吐细节；`kind` 不再接受自由字符串。
- 返回与限制：作为 `AnalysisResult.compute_items` 元素类型。

### `class MemoryItem`

- 功能说明：显式记录一条访存分类项。
- 参数说明：
  - `path: MemoryPath`
  - `access: str`
  - `bytes: sympy.Basic`
  - `latency_ns: sympy.Basic | None`
  - `bandwidth: sympy.Basic | None`
  - `time_ns: sympy.Basic | None`
- 使用示例：`MemoryItem(path=MemoryPath.GM_TO_LM, access="read", bytes=32)`
- 注意事项：
  - `path` 不能再使用自由字符串；必须来自正式 `MemoryPath` 枚举。
  - 若当前 path 没有带宽/延迟配置，则 `time_ns` 可为空。
  - 若 `latency_ns` 与 `bandwidth` 同时存在，则 `time_ns` 必须满足 `latency_ns + bytes / bandwidth`。
- 返回与限制：作为 `AnalysisResult.memory_items` 元素类型。

### `class AnalysisResult`

- 功能说明：统一入口正式结果。
- 参数说明：
  - `compute_items: Sequence[ComputeItem]`
  - `memory_items: Sequence[MemoryItem]`
  - `compute_totals_by_kind: Mapping[ComputeKind, sympy.Basic]`
  - `memory_totals_by_path: Mapping[MemoryPath, sympy.Basic]`
- 使用示例：`result = analysis(op, config)`
- 注意事项：
  - `compute_totals_by_kind` 必须由 `compute_items` 派生。
  - `memory_totals_by_path` 必须由 `memory_items` 按 `MemoryPath` 派生，不能再主读旧 `read_bytes / write_bytes` 汇总。
  - `total_compute / total_read_bytes / total_write_bytes` 若仍保留，只能作为 derived alias。
- 返回与限制：作为统一入口稳定返回值。

### `analysis(op, config, otherargs=None)`

- 功能说明：统一分析入口。
- 参数说明：
  - `op: Operation | func.FuncOp`
  - `config: AnalysisConfig`
  - `otherargs: Iterable[object] | None`
- 使用示例：

```python
result = analysis(
    op,
    AnalysisConfig(
        enable_compute=True,
        enable_memory=False,
        write_op_attrs=False,
        write_func_attrs=False,
    ),
)
```

- 注意事项：
  - 分析 `func.func` 时，必须建立在逐 op 调用 `analysis(op, config, otherargs)` 的聚合上。
  - 默认不写回 `analysis.*`；只有显式开启时才写。
  - `AnalysisConfig.target` 的默认分析参数必须来自 `target registry`；当前默认 target 固定为 `npu_demo`。
  - 当前未承接的未知 op 继续执行 `skip + warning`。
- 返回与限制：返回 `AnalysisResult`；输入非法或前置条件不满足时抛出 `AnalysisError`。

## 测试

- 测试文件：[`test/analysis/test_analysis.py`](../../test/analysis/test_analysis.py)
- 执行命令：`pytest -q test/analysis/test_analysis.py`
- 重点覆盖：
  - `analysis(...)` 单 op 返回 `AnalysisResult`
  - `ComputeKind.SCALAR / VECTOR / TENSOR` 分类与 `compute_totals_by_kind`
  - `write_op_attrs` / `write_func_attrs` 显式开关
  - `analyze_kernel(...)` 仅作为 facade / adapter
  - `AnalysisConfig` 默认分析参数来自 `npu_demo target registry`
  - `npu_demo` 缺失 analysis 默认参数时显式失败
  - `dma.copy` / `dma.slice` 的 `MemoryPath + bytes + time_ns` 可机械读取
  - unknown op 为 `skip + warning`
  - 非法公开 DMA 分支为 `hard error`
