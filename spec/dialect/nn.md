# nn.md

## 功能简介

`nn dialect` 定义方言层稳定接口，负责建模 memory space、memory type，以及逐元素算术、逐元素比较、逐元素 activation、按轴归约（`reduce_sum/reduce_min/reduce_max`）、显式 `broadcast`、`transpose`、`softmax`、`img2col1d/img2col2d` 和二维 `matmul` 的 IR 形态与 verifier 约束。本规范仅描述方言层字段、文本形式与校验语义，不包含上游高层 API 调度逻辑。

## API 列表

- `class NnMemorySpaceAttr(space: StringAttr)`
- `class NnMemoryType(shape: ArrayAttr[SymbolExprAttr], stride: ArrayAttr[SymbolExprAttr], element_type: Attribute, space: NnMemorySpaceAttr, template_name: StringAttr | str | None = None)`
- `memory_template_name(memory_type: NnMemoryType) -> str | None`
- `has_memory_template_name(memory_type: NnMemoryType) -> bool`
- `copy_memory_type(memory_type: NnMemoryType, *, shape: ArrayAttr[SymbolExprAttr] | None = None, stride: ArrayAttr[SymbolExprAttr] | None = None, element_type: Attribute | None = None, space: NnMemorySpaceAttr | None = None) -> NnMemoryType`
- `copy_memory_type_with_template_name(memory_type: NnMemoryType, template_name: str | StringAttr, *, shape: ArrayAttr[SymbolExprAttr] | None = None, stride: ArrayAttr[SymbolExprAttr] | None = None, element_type: Attribute | None = None, space: NnMemorySpaceAttr | None = None) -> NnMemoryType`
- `class NnAddOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnSubOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnMulOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnDivOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnTrueDivOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnFloorDivOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnEqOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnNeOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnLtOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnLeOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnGtOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnGeOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnSelectOp(pred: SSAValue, on_true: SSAValue, on_false: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnCastOp(input_value: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnBroadcastOp(input_value: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnTransposeOp(input_value: SSAValue, result_type: NnMemoryType, perm: Sequence[int] | ArrayAttr[IntegerAttr], space: NnMemorySpaceAttr)`
- `class NnReluOp(input_value: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnSigmoidOp(input_value: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnTanhOp(input_value: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnLeakyReluOp(input_value: SSAValue, alpha: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnHardSigmoidOp(input_value: SSAValue, alpha: SSAValue, beta: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnSoftmaxOp(input_value: SSAValue, result_type: NnMemoryType, axis: int | IntegerAttr, space: NnMemorySpaceAttr)`
- `class NnExpOp(input_value: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class NnReduceSumOp(input_value: SSAValue, result_type: NnMemoryType, axes: Sequence[int] | ArrayAttr[IntegerAttr], keepdim: bool | IntegerAttr, space: NnMemorySpaceAttr)`
- `class NnReduceMinOp(input_value: SSAValue, result_type: NnMemoryType, axes: Sequence[int] | ArrayAttr[IntegerAttr], keepdim: bool | IntegerAttr, space: NnMemorySpaceAttr)`
- `class NnReduceMaxOp(input_value: SSAValue, result_type: NnMemoryType, axes: Sequence[int] | ArrayAttr[IntegerAttr], keepdim: bool | IntegerAttr, space: NnMemorySpaceAttr)`
- `class NnImg2col1dOp(input_value: SSAValue, result_type: NnMemoryType, kw: SSAValue, sw: SSAValue, dw: SSAValue, pl: SSAValue, pr: SSAValue, space: NnMemorySpaceAttr)`
- `class NnImg2col2dOp(input_value: SSAValue, result_type: NnMemoryType, kh: SSAValue, kw: SSAValue, sh: SSAValue, sw: SSAValue, dh: SSAValue, dw: SSAValue, ph: SSAValue, pw: SSAValue, pl: SSAValue, pr: SSAValue, space: NnMemorySpaceAttr)`
- `class NnMatmulOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- `class Nn(Dialect)`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/dialect/nn.md`](../../spec/dialect/nn.md)
- `功能实现`：[`kernel_gen/dialect/nn.py`](../../kernel_gen/dialect/nn.py)
- `test`：[`test/dialect/test_nn.py`](../../test/dialect/test_nn.py)

## 依赖

- [`spec/operation/nn.md`](../../spec/operation/nn.md)：上游算子语义。
- [`spec/symbol_variable/memory.md`](../../spec/symbol_variable/memory.md)：`Memory` 的 `shape/stride/dtype/space` 基础语义。
- [`kernel_gen/dialect/nn.py`](../../kernel_gen/dialect/nn.py)：方言实现。
- [`test/dialect/test_nn.py`](../../test/dialect/test_nn.py)：方言测试。

## 目标

- 提供 `global/shared/local/tsm/tlm1/tlm2/tlm3` 七种 memory space 的统一属性表示。
- 提供可解析、可打印、可校验的 `!nn.memory<...>` 类型表示；可选 `template = T1` 只由 `template_name` 字段承载。
- 为 `nn.add/sub/mul/div/truediv/floordiv/eq/ne/lt/le/gt/ge/select/cast/relu/sigmoid/tanh/leaky_relu/hard_sigmoid/exp/reduce_sum/reduce_min/reduce_max/broadcast/transpose/softmax/img2col1d/img2col2d/matmul` 提供稳定的方言层接口。
- 明确 `nn dialect` 不支持逐元素隐式 broadcast，所有广播必须显式使用 `nn.broadcast`。
- 承接上游 `operation.broadcast_to(...)` 的 canonical lowering：进入方言时以 `nn.broadcast` 表达目标 shape（由结果类型承载），不在 `nn dialect` 额外新增 `nn.broadcast_to` 独立 op。
- 保证合法文本 IR 可以 round-trip，非法输入在 parse 或 verifier 阶段被拒绝。
- `!nn.memory<...>` 的 `shape/stride` 文本维度入口与 `SymbolDim` 字符串口径一致；每个非静态整数、非 `?` 的维度都按符号维度字符串校验并保持原文 round-trip，支持 `SymbolDim` 已支持的符号表达式，包括 `+`、`-`、`*`、`/`、`//` 与括号。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 本文件只定义 `kernel_gen/dialect/nn.py` 的方言层接口，不重复上游 `operation/nn` 的高层 API 语义。
- 上游若允许逐元素隐式 broadcast，进入 `nn dialect` 前必须显式展开为 `nn.broadcast`。
- 上游 `broadcast_to(source, target_shape, space)` 进入方言时必须归一化为 `nn.broadcast`：目标 `target_shape` 仅通过 `result_type.shape` 体现，`nn dialect` 不承诺提供独立的 `nn.broadcast_to` op。
- `img2col` 在方言层只允许公开 `nn.img2col1d` 与 `nn.img2col2d` 两个稳定 op，禁止新增笼统公开名 `nn.img2col`。
- `nn.img2col1d/img2col2d` 仅定义 operand/attribute/result/verifier 合同，不在方言层重复上游 `operation/nn` 的 shape/stride 公式与错误边界全文。
- 上游 `fc/conv` 在方言层不定义独立 op，进入 `nn dialect` 后下沉为 `nn.matmul` / `nn.img2col1d` / `nn.img2col2d` 的组合与约束。
- `nn.softmax` 在方言层只定义 `input/result/axis/space` 的结构化合同；`axis=-1` 默认值、负轴归一化与数值稳定公式属于上游 `operation/nn` 语义，不在方言层重复展开。
- `nn.softmax` 仍然是合法输入 op；默认 lowering 链通过 `DecompassPass`（见 [`spec/pass/decompass.md`](../../spec/pass/decompass.md)）把 `nn.softmax` 分解成可继续 lowering 的 `nn` 链路，方言层不负责自动分解。
- `NnMemorySpaceAttr` 仅允许 `global/shared/local/tsm/tlm1/tlm2/tlm3` 七种取值。
- `NnMemoryType.space` 与各 op 的 `space` attribute 必须使用同一语义口径。
- `NnMemoryType` 中 `shape` 与 `stride` 的 rank 必须一致；每一维必须由 `SymbolExprAttr` 承载，表达式可表示静态整数、符号或 `?`。
- `NnMemoryType.template_name` 是可选字段；文本 IR 使用 `, template = T1` 形式，省略表示无 template name。合法 template name 必须匹配 `[A-Za-z_][A-Za-z0-9_]*`，`<T1>`、空白、数字开头或带空格文本必须拒绝。
- `memory_template_name(...)` 返回非空 template name；未携带 template name 时返回 `None`。
- `has_memory_template_name(...)` 仅是 `memory_template_name(...) is not None` 的公开谓词。
- `copy_memory_type(...)` 复制 `shape/stride/element_type/space` 并清除 template name，避免新 buffer 派生时泄漏旧 template family。
- `copy_memory_type_with_template_name(...)` 复制 memory type 并写入合法 template name；非法 template name 必须按 `NnMemoryType.verify()` 失败。
- `shape` 中的 `?` 表示动态维度；`stride` 中的 `?` 不允许与同位置 `shape` 中的 `?` 直接成对出现。
- 二元逐元素 op 的 `lhs/rhs/result` 必须满足 `shape/stride/space` 的 verifier 约束，不能依赖方言层做隐式 broadcast。
- 比较 op 的结果 `element_type` 必须为 `i1`。
- `nn.exp` 仅接受浮点 `!nn.memory`，结果必须与输入保持同 `shape/stride/element_type/space`。
- `nn.reduce_sum/reduce_min/reduce_max` 使用规范化后的 `axes` 与显式 `keepdim` 建模归约语义；`result.shape/stride` 必须与归约合同一致。
- `nn.matmul` 仅建模二维矩阵乘，`lhs.shape[1]` 与 `rhs.shape[0]` 必须语义一致。
- `nn.softmax` 已在 `kernel_gen/dialect/nn.py` 与 `test/dialect/test_nn.py` 落地；本节作为公开契约与映射编号基线，后续改动必须保持与本合同闭环一致。
- `space` 指 `nn dialect` 中 memory 所在的物理或逻辑空间，由 `NnMemorySpaceAttr` 表示。
- `memory type` 指 `NnMemoryType`，由 `shape/stride/element_type/space` 组成。
- `round-trip` 指文本 IR 在 parse 后再 print，得到稳定且等价的文本表示。
- 合法 `!nn.memory<...>`、`#nn.space<...>` 与包含公开 op 的模块文本必须支持 round-trip；其中 `!nn.memory<...>` 的 `shape/stride` 维度文本范围与 `SymbolDim` 字符串口径一致，不再按 `xdsl` token 子集额外收窄。
## API详细说明

### `class NnMemorySpaceAttr(space: StringAttr)`

- api：`class NnMemorySpaceAttr(space: StringAttr)`
- 参数：
  - `name`：公开名称、符号名或注册名，用于查找、打印、注册或生成稳定标识；类型 `str`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`NnMemorySpaceAttr` 实例。
- 使用示例：

  ```python
  nn_memory_space_attr = NnMemorySpaceAttr(name=name)
  ```
- 功能说明：构造 `NnMemorySpaceAttr` 实例。
- 注意事项：构造参数必须符合本条目参数说明；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `class NnMemoryType(shape: ArrayAttr[SymbolExprAttr], stride: ArrayAttr[SymbolExprAttr], element_type: Attribute, space: NnMemorySpaceAttr, template_name: StringAttr | str | None = None)`

- api：`class NnMemoryType(shape: ArrayAttr[SymbolExprAttr], stride: ArrayAttr[SymbolExprAttr], element_type: Attribute, space: NnMemorySpaceAttr, template_name: StringAttr | str | None = None)`
- 参数：
  - `shape`：形状序列，定义张量、内存或符号对象的维度大小；类型 `ArrayAttr[SymbolExprAttr]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `stride`：步长序列，定义各维度在底层线性布局中的跨距；类型 `ArrayAttr[SymbolExprAttr]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `element_type`：类型对象或类型名称；类型 `Attribute`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `space`：内存空间标识，定义对象所在的 GM、SM、LM 或其他公开空间；类型 `NnMemorySpaceAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `template_name`：可选 C++ template 类型参数名；类型 `StringAttr | str | None`；默认值 `None`；`None` 或空字符串表示无 template name，非空值必须匹配 `[A-Za-z_][A-Za-z0-9_]*`。
- 返回值：`NnMemoryType` 实例。
- 使用示例：

  ```python
  nn_memory_type = NnMemoryType(shape=shape, stride=stride, element_type=element_type, space=space, template_name="T1")
  ```
- 功能说明：构造 `NnMemoryType` 实例。
- 注意事项：构造参数必须符合本条目参数说明；`shape/stride` 只公开 `ArrayAttr[SymbolExprAttr]`，raw `IntAttr/StringAttr` 或其它 `Attribute` 容器不是公开兼容入口；`template_name` 只接受裸 identifier，不接受尖括号模板实参文本；实例内部缓存、状态字典和派生字段不作为外部可变入口。

### `memory_template_name(memory_type: NnMemoryType) -> str | None`

- api：`memory_template_name(memory_type: NnMemoryType) -> str | None`
- 功能说明：读取 memory type 的非空 template name；未携带时返回 `None`。
- 注意事项：输入必须是合法 `NnMemoryType`；非法 template name 不得被吞掉。

### `has_memory_template_name(memory_type: NnMemoryType) -> bool`

- api：`has_memory_template_name(memory_type: NnMemoryType) -> bool`
- 功能说明：判断 memory type 是否携带非空 template name。
- 注意事项：该接口等价于 `memory_template_name(memory_type) is not None`，不暴露内部空字符串编码。

### `copy_memory_type(memory_type: NnMemoryType, *, shape: ArrayAttr[SymbolExprAttr] | None = None, stride: ArrayAttr[SymbolExprAttr] | None = None, element_type: Attribute | None = None, space: NnMemorySpaceAttr | None = None) -> NnMemoryType`

- api：`copy_memory_type(memory_type: NnMemoryType, *, shape: ArrayAttr[SymbolExprAttr] | None = None, stride: ArrayAttr[SymbolExprAttr] | None = None, element_type: Attribute | None = None, space: NnMemorySpaceAttr | None = None) -> NnMemoryType`
- 功能说明：复制 memory type 的基础字段并清空 template name。
- 注意事项：该接口不得保留旧 template name；需要显式写入 name 时必须使用 `copy_memory_type_with_template_name(...)`。

### `copy_memory_type_with_template_name(memory_type: NnMemoryType, template_name: str | StringAttr, *, shape: ArrayAttr[SymbolExprAttr] | None = None, stride: ArrayAttr[SymbolExprAttr] | None = None, element_type: Attribute | None = None, space: NnMemorySpaceAttr | None = None) -> NnMemoryType`

- api：`copy_memory_type_with_template_name(memory_type: NnMemoryType, template_name: str | StringAttr, *, shape: ArrayAttr[SymbolExprAttr] | None = None, stride: ArrayAttr[SymbolExprAttr] | None = None, element_type: Attribute | None = None, space: NnMemorySpaceAttr | None = None) -> NnMemoryType`
- 功能说明：复制 memory type 的基础字段并写入合法 template name。
- 注意事项：`template_name` 必须匹配 `[A-Za-z_][A-Za-z0-9_]*`；shape/stride 必须继续是 `ArrayAttr[SymbolExprAttr]`。

### `class NnAddOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`

- api：`class NnAddOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- 参数：
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `result_type`：类型对象或类型名称；类型 `NnMemoryType`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `space`：内存空间标识，定义对象所在的 GM、SM、LM 或其他公开空间；类型 `NnMemorySpaceAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`add` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  nn = nn
  result = nn.add(lhs=lhs, rhs=rhs, result_type=result_type, space=space)
  ```
- 功能说明：执行 `add`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `class NnSubOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`

- api：`class NnSubOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- 参数：
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `result_type`：类型对象或类型名称；类型 `NnMemoryType`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `space`：内存空间标识，定义对象所在的 GM、SM、LM 或其他公开空间；类型 `NnMemorySpaceAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`sub` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  nn = nn
  result = nn.sub(lhs=lhs, rhs=rhs, result_type=result_type, space=space)
  ```
- 功能说明：执行 `sub`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `class NnMulOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`

- api：`class NnMulOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- 参数：
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `result_type`：类型对象或类型名称；类型 `NnMemoryType`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `space`：内存空间标识，定义对象所在的 GM、SM、LM 或其他公开空间；类型 `NnMemorySpaceAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`mul` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  nn = nn
  result = nn.mul(lhs=lhs, rhs=rhs, result_type=result_type, space=space)
  ```
- 功能说明：执行 `mul`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `class NnDivOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`

- api：`class NnDivOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- 参数：
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `result_type`：类型对象或类型名称；类型 `NnMemoryType`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `space`：内存空间标识，定义对象所在的 GM、SM、LM 或其他公开空间；类型 `NnMemorySpaceAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`div` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  nn = nn
  result = nn.div(lhs=lhs, rhs=rhs, result_type=result_type, space=space)
  ```
- 功能说明：执行 `div`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `class NnTrueDivOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`

- api：`class NnTrueDivOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- 参数：
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `result_type`：类型对象或类型名称；类型 `NnMemoryType`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `space`：内存空间标识，定义对象所在的 GM、SM、LM 或其他公开空间；类型 `NnMemorySpaceAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`truediv` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  nn = nn
  result = nn.truediv(lhs=lhs, rhs=rhs, result_type=result_type, space=space)
  ```
- 功能说明：执行 `truediv`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `class NnFloorDivOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`

- api：`class NnFloorDivOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- 参数：
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `result_type`：类型对象或类型名称；类型 `NnMemoryType`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `space`：内存空间标识，定义对象所在的 GM、SM、LM 或其他公开空间；类型 `NnMemorySpaceAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`floordiv` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  nn = nn
  result = nn.floordiv(lhs=lhs, rhs=rhs, result_type=result_type, space=space)
  ```
- 功能说明：执行 `floordiv`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `class NnEqOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`

- api：`class NnEqOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- 参数：
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `result_type`：类型对象或类型名称；类型 `NnMemoryType`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `space`：内存空间标识，定义对象所在的 GM、SM、LM 或其他公开空间；类型 `NnMemorySpaceAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`eq` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  nn = nn
  result = nn.eq(lhs=lhs, rhs=rhs, result_type=result_type, space=space)
  ```
- 功能说明：执行 `eq`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `class NnNeOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`

- api：`class NnNeOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- 参数：
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `result_type`：类型对象或类型名称；类型 `NnMemoryType`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `space`：内存空间标识，定义对象所在的 GM、SM、LM 或其他公开空间；类型 `NnMemorySpaceAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`ne` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  nn = nn
  result = nn.ne(lhs=lhs, rhs=rhs, result_type=result_type, space=space)
  ```
- 功能说明：执行 `ne`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `class NnLtOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`

- api：`class NnLtOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- 参数：
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `result_type`：类型对象或类型名称；类型 `NnMemoryType`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `space`：内存空间标识，定义对象所在的 GM、SM、LM 或其他公开空间；类型 `NnMemorySpaceAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`lt` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  nn = nn
  result = nn.lt(lhs=lhs, rhs=rhs, result_type=result_type, space=space)
  ```
- 功能说明：执行 `lt`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `class NnLeOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`

- api：`class NnLeOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- 参数：
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `result_type`：类型对象或类型名称；类型 `NnMemoryType`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `space`：内存空间标识，定义对象所在的 GM、SM、LM 或其他公开空间；类型 `NnMemorySpaceAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`le` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  nn = nn
  result = nn.le(lhs=lhs, rhs=rhs, result_type=result_type, space=space)
  ```
- 功能说明：执行 `le`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `class NnGtOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`

- api：`class NnGtOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- 参数：
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `result_type`：类型对象或类型名称；类型 `NnMemoryType`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `space`：内存空间标识，定义对象所在的 GM、SM、LM 或其他公开空间；类型 `NnMemorySpaceAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`gt` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  nn = nn
  result = nn.gt(lhs=lhs, rhs=rhs, result_type=result_type, space=space)
  ```
- 功能说明：执行 `gt`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `class NnGeOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`

- api：`class NnGeOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- 参数：
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `result_type`：类型对象或类型名称；类型 `NnMemoryType`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `space`：内存空间标识，定义对象所在的 GM、SM、LM 或其他公开空间；类型 `NnMemorySpaceAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`ge` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  nn = nn
  result = nn.ge(lhs=lhs, rhs=rhs, result_type=result_type, space=space)
  ```
- 功能说明：执行 `ge`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `class NnSelectOp(pred: SSAValue, on_true: SSAValue, on_false: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`

- api：`class NnSelectOp(pred: SSAValue, on_true: SSAValue, on_false: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- 参数：
  - `pred`：谓词对象或布尔表达式，用于决定条件执行或匹配是否成立；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `on_true`：`on_true` 输入值，参与 `select` 的公开处理流程；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `on_false`：`on_false` 输入值，参与 `select` 的公开处理流程；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `result_type`：类型对象或类型名称；类型 `NnMemoryType`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `space`：内存空间标识，定义对象所在的 GM、SM、LM 或其他公开空间；类型 `NnMemorySpaceAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`select` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  nn = nn
  result = nn.select(pred=pred, on_true=on_true, on_false=on_false, result_type=result_type, space=space)
  ```
- 功能说明：执行 `select`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `class NnCastOp(input_value: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`

- api：`class NnCastOp(input_value: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- 参数：
  - `input_value`：`input_value` 输入值，参与 `cast` 的公开处理流程；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `result_type`：类型对象或类型名称；类型 `NnMemoryType`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `space`：内存空间标识，定义对象所在的 GM、SM、LM 或其他公开空间；类型 `NnMemorySpaceAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`cast` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  nn = nn
  result = nn.cast(input_value=input_value, result_type=result_type, space=space)
  ```
- 功能说明：执行 `cast`。
- 注意事项：输入 memory、offset、size、stride 和 dtype 必须符合 DMA operation 合同；非法组合必须稳定失败。

### `class NnBroadcastOp(input_value: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`

- api：`class NnBroadcastOp(input_value: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- 参数：
  - `input_value`：`input_value` 输入值，参与 `broadcast` 的公开处理流程；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `result_type`：类型对象或类型名称；类型 `NnMemoryType`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `space`：内存空间标识，定义对象所在的 GM、SM、LM 或其他公开空间；类型 `NnMemorySpaceAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`broadcast` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  nn = nn
  result = nn.broadcast(input_value=input_value, result_type=result_type, space=space)
  ```
- 功能说明：执行 `broadcast`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `class NnTransposeOp(input_value: SSAValue, result_type: NnMemoryType, perm: Sequence[int] | ArrayAttr[IntegerAttr], space: NnMemorySpaceAttr)`

- api：`class NnTransposeOp(input_value: SSAValue, result_type: NnMemoryType, perm: Sequence[int] | ArrayAttr[IntegerAttr], space: NnMemorySpaceAttr)`
- 参数：
  - `input_value`：`input_value` 输入值，参与 `transpose` 的公开处理流程；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `result_type`：类型对象或类型名称；类型 `NnMemoryType`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `perm`：维度排列序列，定义输出维度从输入维度读取的顺序；类型 `Sequence[int] | ArrayAttr[IntegerAttr]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `space`：内存空间标识，定义对象所在的 GM、SM、LM 或其他公开空间；类型 `NnMemorySpaceAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`transpose` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  nn = nn
  result = nn.transpose(input_value=input_value, result_type=result_type, perm=perm, space=space)
  ```
- 功能说明：执行 `transpose`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `class NnReluOp(input_value: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`

- api：`class NnReluOp(input_value: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- 参数：
  - `input_value`：`input_value` 输入值，参与 `relu` 的公开处理流程；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `result_type`：类型对象或类型名称；类型 `NnMemoryType`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `space`：内存空间标识，定义对象所在的 GM、SM、LM 或其他公开空间；类型 `NnMemorySpaceAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`relu` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  nn = nn
  result = nn.relu(input_value=input_value, result_type=result_type, space=space)
  ```
- 功能说明：执行 `relu`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `class NnSigmoidOp(input_value: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`

- api：`class NnSigmoidOp(input_value: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- 参数：
  - `input_value`：`input_value` 输入值，参与 `sigmoid` 的公开处理流程；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `result_type`：类型对象或类型名称；类型 `NnMemoryType`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `space`：内存空间标识，定义对象所在的 GM、SM、LM 或其他公开空间；类型 `NnMemorySpaceAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`sigmoid` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  nn = nn
  result = nn.sigmoid(input_value=input_value, result_type=result_type, space=space)
  ```
- 功能说明：执行 `sigmoid`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `class NnTanhOp(input_value: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`

- api：`class NnTanhOp(input_value: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- 参数：
  - `input_value`：`input_value` 输入值，参与 `tanh` 的公开处理流程；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `result_type`：类型对象或类型名称；类型 `NnMemoryType`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `space`：内存空间标识，定义对象所在的 GM、SM、LM 或其他公开空间；类型 `NnMemorySpaceAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`tanh` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  nn = nn
  result = nn.tanh(input_value=input_value, result_type=result_type, space=space)
  ```
- 功能说明：执行 `tanh`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `class NnLeakyReluOp(input_value: SSAValue, alpha: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`

- api：`class NnLeakyReluOp(input_value: SSAValue, alpha: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- 参数：
  - `input_value`：`input_value` 输入值，参与 `leaky_relu` 的公开处理流程；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `alpha`：`alpha` 输入值，参与 `leaky_relu` 的公开处理流程；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `result_type`：类型对象或类型名称；类型 `NnMemoryType`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `space`：内存空间标识，定义对象所在的 GM、SM、LM 或其他公开空间；类型 `NnMemorySpaceAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`leaky_relu` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  nn = nn
  result = nn.leaky_relu(input_value=input_value, alpha=alpha, result_type=result_type, space=space)
  ```
- 功能说明：执行 `leaky_relu`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `class NnHardSigmoidOp(input_value: SSAValue, alpha: SSAValue, beta: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`

- api：`class NnHardSigmoidOp(input_value: SSAValue, alpha: SSAValue, beta: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- 参数：
  - `input_value`：`input_value` 输入值，参与 `hard_sigmoid` 的公开处理流程；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `alpha`：`alpha` 输入值，参与 `hard_sigmoid` 的公开处理流程；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `beta`：`beta` 输入值，参与 `hard_sigmoid` 的公开处理流程；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `result_type`：类型对象或类型名称；类型 `NnMemoryType`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `space`：内存空间标识，定义对象所在的 GM、SM、LM 或其他公开空间；类型 `NnMemorySpaceAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`hard_sigmoid` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  nn = nn
  result = nn.hard_sigmoid(input_value=input_value, alpha=alpha, beta=beta, result_type=result_type, space=space)
  ```
- 功能说明：执行 `hard_sigmoid`。
- 注意事项：非法输入必须按本条目参数说明和公开错误语义处理；调用方不得依赖实现内部状态。

### `class NnSoftmaxOp(input_value: SSAValue, result_type: NnMemoryType, axis: int | IntegerAttr, space: NnMemorySpaceAttr)`

- api：`class NnSoftmaxOp(input_value: SSAValue, result_type: NnMemoryType, axis: int | IntegerAttr, space: NnMemorySpaceAttr)`
- 参数：
  - `input_value`：`input_value` 输入值，参与 `softmax` 的公开处理流程；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `result_type`：类型对象或类型名称；类型 `NnMemoryType`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `axis`：轴编号，指定 reduce、softmax、reshape 或维度相关操作的作用维度；类型 `int | IntegerAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `space`：内存空间标识，定义对象所在的 GM、SM、LM 或其他公开空间；类型 `NnMemorySpaceAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`softmax` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  nn = nn
  result = nn.softmax(input_value=input_value, result_type=result_type, axis=axis, space=space)
  ```
- 功能说明：执行 `softmax`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `class NnExpOp(input_value: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`

- api：`class NnExpOp(input_value: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- 参数：
  - `input_value`：`input_value` 输入值，参与 `exp` 的公开处理流程；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `result_type`：类型对象或类型名称；类型 `NnMemoryType`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `space`：内存空间标识，定义对象所在的 GM、SM、LM 或其他公开空间；类型 `NnMemorySpaceAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`exp` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  nn = nn
  result = nn.exp(input_value=input_value, result_type=result_type, space=space)
  ```
- 功能说明：执行 `exp`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `class NnReduceSumOp(input_value: SSAValue, result_type: NnMemoryType, axes: Sequence[int] | ArrayAttr[IntegerAttr], keepdim: bool | IntegerAttr, space: NnMemorySpaceAttr)`

- api：`class NnReduceSumOp(input_value: SSAValue, result_type: NnMemoryType, axes: Sequence[int] | ArrayAttr[IntegerAttr], keepdim: bool | IntegerAttr, space: NnMemorySpaceAttr)`
- 参数：
  - `input_value`：`input_value` 输入值，参与 `reduce_sum` 的公开处理流程；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `result_type`：类型对象或类型名称；类型 `NnMemoryType`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `axes`：轴编号集合，指定多维操作需要处理的维度顺序；类型 `Sequence[int] | ArrayAttr[IntegerAttr]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `keepdim`：`keepdim` 输入值，参与 `reduce_sum` 的公开处理流程；类型 `bool | IntegerAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `space`：内存空间标识，定义对象所在的 GM、SM、LM 或其他公开空间；类型 `NnMemorySpaceAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`bool`，表示判断结果。
- 使用示例：

  ```python
  nn = nn
  result = nn.reduce_sum(input_value=input_value, result_type=result_type, axes=axes, keepdim=keepdim, space=space)
  ```
- 功能说明：执行 `reduce_sum`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `class NnReduceMinOp(input_value: SSAValue, result_type: NnMemoryType, axes: Sequence[int] | ArrayAttr[IntegerAttr], keepdim: bool | IntegerAttr, space: NnMemorySpaceAttr)`

- api：`class NnReduceMinOp(input_value: SSAValue, result_type: NnMemoryType, axes: Sequence[int] | ArrayAttr[IntegerAttr], keepdim: bool | IntegerAttr, space: NnMemorySpaceAttr)`
- 参数：
  - `input_value`：`input_value` 输入值，参与 `reduce_min` 的公开处理流程；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `result_type`：类型对象或类型名称；类型 `NnMemoryType`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `axes`：轴编号集合，指定多维操作需要处理的维度顺序；类型 `Sequence[int] | ArrayAttr[IntegerAttr]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `keepdim`：`keepdim` 输入值，参与 `reduce_min` 的公开处理流程；类型 `bool | IntegerAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `space`：内存空间标识，定义对象所在的 GM、SM、LM 或其他公开空间；类型 `NnMemorySpaceAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`bool`，表示判断结果。
- 使用示例：

  ```python
  nn = nn
  result = nn.reduce_min(input_value=input_value, result_type=result_type, axes=axes, keepdim=keepdim, space=space)
  ```
- 功能说明：执行 `reduce_min`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `class NnReduceMaxOp(input_value: SSAValue, result_type: NnMemoryType, axes: Sequence[int] | ArrayAttr[IntegerAttr], keepdim: bool | IntegerAttr, space: NnMemorySpaceAttr)`

- api：`class NnReduceMaxOp(input_value: SSAValue, result_type: NnMemoryType, axes: Sequence[int] | ArrayAttr[IntegerAttr], keepdim: bool | IntegerAttr, space: NnMemorySpaceAttr)`
- 参数：
  - `input_value`：`input_value` 输入值，参与 `reduce_max` 的公开处理流程；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `result_type`：类型对象或类型名称；类型 `NnMemoryType`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `axes`：轴编号集合，指定多维操作需要处理的维度顺序；类型 `Sequence[int] | ArrayAttr[IntegerAttr]`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `keepdim`：`keepdim` 输入值，参与 `reduce_max` 的公开处理流程；类型 `bool | IntegerAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `space`：内存空间标识，定义对象所在的 GM、SM、LM 或其他公开空间；类型 `NnMemorySpaceAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`bool`，表示判断结果。
- 使用示例：

  ```python
  nn = nn
  result = nn.reduce_max(input_value=input_value, result_type=result_type, axes=axes, keepdim=keepdim, space=space)
  ```
- 功能说明：执行 `reduce_max`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `class NnImg2col1dOp(input_value: SSAValue, result_type: NnMemoryType, kw: SSAValue, sw: SSAValue, dw: SSAValue, pl: SSAValue, pr: SSAValue, space: NnMemorySpaceAttr)`

- api：`class NnImg2col1dOp(input_value: SSAValue, result_type: NnMemoryType, kw: SSAValue, sw: SSAValue, dw: SSAValue, pl: SSAValue, pr: SSAValue, space: NnMemorySpaceAttr)`
- 参数：
  - `input_value`：`input_value` 输入值，参与 `img2col1d` 的公开处理流程；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `result_type`：类型对象或类型名称；类型 `NnMemoryType`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `kw`：卷积或池化窗口宽度，定义二维窗口在宽维方向的大小；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `sw`：宽度方向步长，定义卷积或池化窗口在宽维方向每次移动的距离；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `dw`：宽度方向 dilation，定义卷积或池化窗口在宽维方向的元素间隔；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `pl`：左侧 padding，定义一维或二维窗口左侧补边大小；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `pr`：右侧 padding，定义一维或二维窗口右侧补边大小；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `space`：内存空间标识，定义对象所在的 GM、SM、LM 或其他公开空间；类型 `NnMemorySpaceAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`img2col1d` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  nn = nn
  result = nn.img2col1d(input_value=input_value, result_type=result_type, kw=kw, sw=sw, dw=dw, pl=pl, pr=pr, space=space)
  ```
- 功能说明：执行 `img2col1d`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `class NnImg2col2dOp(input_value: SSAValue, result_type: NnMemoryType, kh: SSAValue, kw: SSAValue, sh: SSAValue, sw: SSAValue, dh: SSAValue, dw: SSAValue, ph: SSAValue, pw: SSAValue, pl: SSAValue, pr: SSAValue, space: NnMemorySpaceAttr)`

- api：`class NnImg2col2dOp(input_value: SSAValue, result_type: NnMemoryType, kh: SSAValue, kw: SSAValue, sh: SSAValue, sw: SSAValue, dh: SSAValue, dw: SSAValue, ph: SSAValue, pw: SSAValue, pl: SSAValue, pr: SSAValue, space: NnMemorySpaceAttr)`
- 参数：
  - `input_value`：`input_value` 输入值，参与 `img2col2d` 的公开处理流程；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `result_type`：类型对象或类型名称；类型 `NnMemoryType`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `kh`：卷积或池化窗口高度，定义二维窗口在高维方向的大小；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `kw`：卷积或池化窗口宽度，定义二维窗口在宽维方向的大小；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `sh`：高度方向步长，定义卷积或池化窗口在高维方向每次移动的距离；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `sw`：宽度方向步长，定义卷积或池化窗口在宽维方向每次移动的距离；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `dh`：高度方向 dilation，定义卷积或池化窗口在高维方向的元素间隔；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `dw`：宽度方向 dilation，定义卷积或池化窗口在宽维方向的元素间隔；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `ph`：高度方向 padding，定义卷积或池化在高维方向补边大小；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `pw`：宽度方向 padding，定义卷积或池化在宽维方向补边大小；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `pl`：左侧 padding，定义一维或二维窗口左侧补边大小；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `pr`：右侧 padding，定义一维或二维窗口右侧补边大小；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `space`：内存空间标识，定义对象所在的 GM、SM、LM 或其他公开空间；类型 `NnMemorySpaceAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`img2col2d` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  nn = nn
  result = nn.img2col2d(input_value=input_value, result_type=result_type, kh=kh, kw=kw, sh=sh, sw=sw, dh=dh, dw=dw, ph=ph, pw=pw, pl=pl, pr=pr, space=space)
  ```
- 功能说明：执行 `img2col2d`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `class NnMatmulOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`

- api：`class NnMatmulOp(lhs: SSAValue, rhs: SSAValue, result_type: NnMemoryType, space: NnMemorySpaceAttr)`
- 参数：
  - `lhs`：左操作数，参与二元运算、比较或矩阵乘语义；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `rhs`：右操作数，参与二元运算、比较或矩阵乘语义；类型 `SSAValue`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `result_type`：类型对象或类型名称；类型 `NnMemoryType`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
  - `space`：内存空间标识，定义对象所在的 GM、SM、LM 或其他公开空间；类型 `NnMemorySpaceAttr`；无默认值，调用方必须显式提供；不允许 `None` 或空值作为稳定输入，除非本接口 `注意事项` 另有明确说明；按值或只读语义消费，调用方不得依赖输入对象被修改；非法值按该 API 的公开错误语义处理。
- 返回值：`matmul` 的返回值；返回类型以 API 签名为准。
- 使用示例：

  ```python
  nn = nn
  result = nn.matmul(lhs=lhs, rhs=rhs, result_type=result_type, space=space)
  ```
- 功能说明：执行 `matmul`。
- 注意事项：输入 shape、dtype、space 和广播关系必须符合对应 operation 合同；非法组合必须稳定失败。

### `class Nn(Dialect)`

- api：`class Nn(Dialect)`
- 参数：无显式构造参数；由 xDSL dialect 注册机制消费。
- 返回值：`Nn` dialect 类或实例；包含本文件 `API 列表` 中列出的 nn attributes 与 operations。
- 使用示例：

  ```python
  from xdsl.context import Context
  from kernel_gen.dialect.nn import Nn

  ctx = Context()
  ctx.load_dialect(Nn)
  ```
- 功能说明：聚合并注册 `nn` dialect 的公开 attributes 与 operations。
- 注意事项：`Nn` 只作为 dialect 注册入口；单个 op 的参数、返回值和 verifier 约束必须按对应 class 条目执行。

## 测试

- 测试文件：`test/dialect/test_nn.py`
- 执行命令：`pytest -q test/dialect/test_nn.py`

### 测试目标

- 验证 `NnMemorySpaceAttr` 的合法取值、非法输入与文本 round-trip。
- 验证 `NnMemoryType` 的字段完整性、rank 约束、`shape/stride` 合法性与文本 round-trip。
- 验证 `nn.add/sub/mul/div/truediv/eq/ne/lt/le/gt/ge` 的 operand/result/type/space verifier 约束，其中 `nn.add` 覆盖 memory+scalar/symbol 与 dtype promotion 规则。
- 验证 `nn.select` 的 `cond/lhs/rhs/result` 约束与 `cond` 的 `i1` 要求。
- 验证 `nn.cast` 的 input/result `shape/stride/space` 一致性与 element_type 变更允许性。
- 验证 `nn.exp` 的浮点输入约束、`shape/stride/element_type/space` 一致性与错误路径。
- 验证 `nn.reduce_sum/reduce_min/reduce_max` 的 `axes/keepdim` 约束、结果 `shape/stride` 合同、`dtype/space` 一致性、`keepdim` 非 `i1` 拒绝、结果 `stride` 非连续布局拒绝与静态空归约域错误路径。
- 验证 `nn.broadcast` 的显式广播规则、space 一致性、element type 一致性与文本 round-trip。
- 验证 `nn.transpose` 的 perm/shape/stride/space/element type 约束与文本 round-trip。
- 验证 `nn.softmax` 的 rank/axis/shape/stride/space/element type verifier 约束与错误路径闭环。
- 验证 `nn.img2col1d` 的 operand rank、属性合法性、result rank/type/space 与方言合同约束。
- 验证 `nn.img2col2d` 的 operand rank、属性合法性、result rank/type/space 与方言合同约束。
- 验证 `nn.matmul` 的 rank、shape、space、element type 约束与文本 round-trip。
- 验证逐元素链路拒绝隐式 broadcast。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-NN-DIA-001 | 解析/打印 | `NnMemoryType` round-trip | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_memory_type_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_memory_type_round_trip` |
| TC-NN-DIA-002 | 解析/打印 | `NnMemorySpaceAttr` round-trip | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_space_attr_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_space_attr_round_trip` |
| TC-NN-DIA-003 | 边界/异常 | 非法 space 拒绝 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_invalid_space_attr_rejected`。 | “非法 space 拒绝”场景按公开错误语义失败或被拒绝。 | `test_invalid_space_attr_rejected` |
| TC-NN-DIA-004 | 边界/异常 | memory type rank 不一致 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_memory_type_rank_mismatch_rejected`。 | “memory type rank 不一致”场景按公开错误语义失败或被拒绝。 | `test_memory_type_rank_mismatch_rejected` |
| TC-NN-DIA-005 | 边界/异常 | `nn.add` 合法路径 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_add_op_verify_success`。 | 公开合法路径通过。 | `test_add_op_verify_success` |
| TC-NN-DIA-006 | 边界/异常 | `nn.add` operand space 不一致 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_add_op_rejects_operand_space_mismatch`。 | “`nn.add` operand space 不一致”场景按公开错误语义失败或被拒绝。 | `test_add_op_rejects_operand_space_mismatch` |
| TC-NN-DIA-007 | 边界/异常 | `nn.add` attribute space 不一致 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_add_op_rejects_attr_space_mismatch`。 | “`nn.add` attribute space 不一致”场景按公开错误语义失败或被拒绝。 | `test_add_op_rejects_attr_space_mismatch` |
| TC-NN-DIA-008 | 边界/异常 | 比较结果必须为 `i1` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_compare_op_requires_i1_result`。 | “比较结果必须为 `i1`”场景按公开错误语义失败或被拒绝。 | `test_compare_op_requires_i1_result` |
| TC-NN-DIA-009 | 解析/打印 | 模块 round-trip | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_module_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_module_round_trip` |
| TC-NN-DIA-010 | 边界/异常 | 文本 operand space 不一致 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_space_mismatch_from_text_rejected`。 | “文本 operand space 不一致”场景按公开错误语义失败或被拒绝。 | `test_space_mismatch_from_text_rejected` |
| TC-NN-DIA-011 | 边界/异常 | 文本 attribute space 不一致 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_attr_space_mismatch_from_text_rejected`。 | “文本 attribute space 不一致”场景按公开错误语义失败或被拒绝。 | `test_attr_space_mismatch_from_text_rejected` |
| TC-NN-DIA-012 | 边界/异常 | memory type 缺失字段 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_memory_type_parse_requires_all_fields`。 | “memory type 缺失字段”场景按公开错误语义失败或被拒绝。 | `test_memory_type_parse_requires_all_fields` |
| TC-NN-DIA-013 | 边界/异常 | `nn.broadcast` 合法路径 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_broadcast_op_verify_success`。 | 公开合法路径通过。 | `test_broadcast_op_verify_success` |
| TC-NN-DIA-014 | 边界/异常 | `nn.broadcast` space 不一致 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_broadcast_op_space_mismatch`。 | “`nn.broadcast` space 不一致”场景按公开错误语义失败或被拒绝。 | `test_broadcast_op_space_mismatch` |
| TC-NN-DIA-015 | 边界/异常 | `nn.broadcast` element type 不一致 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_broadcast_op_element_type_mismatch`。 | “`nn.broadcast` element type 不一致”场景按公开错误语义失败或被拒绝。 | `test_broadcast_op_element_type_mismatch` |
| TC-NN-DIA-016 | 解析/打印 | broadcast 模块 round-trip | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_broadcast_module_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_broadcast_module_round_trip` |
| TC-NN-DIA-017 | 边界/异常 | `nn.matmul` 合法路径 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_matmul_op_verify_success`。 | 公开合法路径通过。 | `test_matmul_op_verify_success` |
| TC-NN-DIA-018 | 边界/异常 | `nn.matmul` contracting 维不匹配 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_matmul_op_shape_mismatch`。 | “`nn.matmul` contracting 维不匹配”场景按公开错误语义失败或被拒绝。 | `test_matmul_op_shape_mismatch` |
| TC-NN-DIA-019 | 边界/异常 | `nn.matmul` 结果 shape 不匹配 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_matmul_op_result_shape_mismatch`。 | “`nn.matmul` 结果 shape 不匹配”场景按公开错误语义失败或被拒绝。 | `test_matmul_op_result_shape_mismatch` |
| TC-NN-DIA-020 | 解析/打印 | matmul 模块 round-trip | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_matmul_module_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_matmul_module_round_trip` |
| TC-NN-DIA-021 | 边界/异常 | `nn.matmul` operand space 不一致 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_matmul_op_space_mismatch`。 | “`nn.matmul` operand space 不一致”场景按公开错误语义失败或被拒绝。 | `test_matmul_op_space_mismatch` |
| TC-NN-DIA-022 | 边界/异常 | `nn.matmul` attribute space 不一致 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_matmul_op_attr_space_mismatch`。 | “`nn.matmul` attribute space 不一致”场景按公开错误语义失败或被拒绝。 | `test_matmul_op_attr_space_mismatch` |
| TC-NN-DIA-023 | 边界/异常 | `nn.matmul` rank 不匹配 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_matmul_op_rank_mismatch`。 | “`nn.matmul` rank 不匹配”场景按公开错误语义失败或被拒绝。 | `test_matmul_op_rank_mismatch` |
| TC-NN-DIA-024 | 边界/异常 | `nn.matmul` element type 不一致 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_matmul_op_element_type_mismatch`。 | “`nn.matmul` element type 不一致”场景按公开错误语义失败或被拒绝。 | `test_matmul_op_element_type_mismatch` |
| TC-NN-DIA-025 | 边界/异常 | `nn.add` 拒绝隐式 broadcast | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_add_op_rejects_implicit_broadcast_shape_mismatch`。 | “`nn.add` 拒绝隐式 broadcast”场景按公开错误语义失败或被拒绝。 | `test_add_op_rejects_implicit_broadcast_shape_mismatch` |
| TC-NN-DIA-026 | 边界/异常 | `nn.eq` 拒绝隐式 broadcast | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_compare_op_rejects_implicit_broadcast_shape_mismatch`。 | “`nn.eq` 拒绝隐式 broadcast”场景按公开错误语义失败或被拒绝。 | `test_compare_op_rejects_implicit_broadcast_shape_mismatch` |
| TC-NN-DIA-027 | 边界/异常 | memory type space 不是 `nn.space` | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_memory_type_parse_rejects_non_space_attr`。 | “memory type space 不是 `nn.space`”场景按公开错误语义失败或被拒绝。 | `test_memory_type_parse_rejects_non_space_attr` |
| TC-NN-DIA-028 | 边界/异常 | memory type 非法维度条目 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_memory_type_rejects_invalid_dim_entry`。 | “memory type 非法维度条目”场景按公开错误语义失败或被拒绝。 | `test_memory_type_rejects_invalid_dim_entry` |
| TC-NN-DIA-029 | 边界/异常 | stride `?` 与 shape `?` 同位拒绝 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_memory_type_rejects_stride_question_dim_pair`。 | “stride `?` 与 shape `?` 同位拒绝”场景按公开错误语义失败或被拒绝。 | `test_memory_type_rejects_stride_question_dim_pair` |
| TC-NN-DIA-030 | 边界/异常 | `nn.add` 纯 scalar/symbol operand 拒绝 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_add_op_rejects_pure_scalar_operands`。 | “`nn.add` 纯 scalar/symbol operand 拒绝”场景按公开错误语义失败或被拒绝。 | `test_add_op_rejects_pure_scalar_operands` |
| TC-NN-DIA-031 | 边界/异常 | `nn.add` space/stride/element type 不一致 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_add_op_rejects_type_mismatch`。 | “`nn.add` space/stride/element type 不一致”场景按公开错误语义失败或被拒绝。 | `test_add_op_rejects_type_mismatch` |
| TC-NN-DIA-032 | 边界/异常 | 算术 op(sub/mul/truediv) 合法路径 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_arithmetic_ops_verify_success`。 | 公开合法路径通过。 | `test_arithmetic_ops_verify_success` |
| TC-NN-DIA-033 | 边界/异常 | 比较 op(ne/lt/le/gt/ge) 合法路径 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_compare_ops_verify_success`。 | 公开合法路径通过。 | `test_compare_ops_verify_success` |
| TC-NN-DIA-034 | 边界/异常 | `nn.broadcast` space/rank/shape 不一致 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_broadcast_op_rejects_invalid_inputs`。 | “`nn.broadcast` space/rank/shape 不一致”场景按公开错误语义失败或被拒绝。 | `test_broadcast_op_rejects_invalid_inputs` |
| TC-NN-DIA-035 | 边界/异常 | `nn.matmul` result space 不一致 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_matmul_op_result_space_mismatch`。 | “`nn.matmul` result space 不一致”场景按公开错误语义失败或被拒绝。 | `test_matmul_op_result_space_mismatch` |
| TC-NN-DIA-036 | 边界/异常 | `nn.transpose` 合法路径 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_transpose_op_verify_success`。 | 公开合法路径通过。 | `test_transpose_op_verify_success` |
| TC-NN-DIA-037 | 边界/异常 | `nn.transpose` perm 非法 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_transpose_op_rejects_invalid_perm`。 | “`nn.transpose` perm 非法”场景按公开错误语义失败或被拒绝。 | `test_transpose_op_rejects_invalid_perm` |
| TC-NN-DIA-038 | 边界/异常 | `nn.transpose` shape/stride 不匹配 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_transpose_op_result_mismatch`。 | “`nn.transpose` shape/stride 不匹配”场景按公开错误语义失败或被拒绝。 | `test_transpose_op_result_mismatch` |
| TC-NN-DIA-039 | 解析/打印 | transpose 模块 round-trip | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_transpose_module_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_transpose_module_round_trip` |
| TC-NN-DIA-040 | 内存/DMA | `nn.add` 接受 memory + const scalar 并做 promotion | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_add_op_accepts_memory_const_rhs`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`nn.add` 接受 memory + const scalar 并做 promotion”场景。 | `test_add_op_accepts_memory_const_rhs` |
| TC-NN-DIA-041 | 内存/DMA | `nn.add` 接受 memory + symbol.int 并做 promotion | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_add_op_accepts_memory_symbol_rhs`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`nn.add` 接受 memory + symbol.int 并做 promotion”场景。 | `test_add_op_accepts_memory_symbol_rhs` |
| TC-NN-DIA-042 | 边界/异常 | `nn.add` mixed 形态 result shape 不匹配拒绝 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_add_op_rejects_mixed_result_shape_mismatch`。 | “`nn.add` mixed 形态 result shape 不匹配拒绝”场景按公开错误语义失败或被拒绝。 | `test_add_op_rejects_mixed_result_shape_mismatch` |
| TC-NN-DIA-043 | 执行结果 | `nn.img2col1d` 合同（operand/attrs/result/verifier） | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_nn_dialect_img2col1d_contract_v1`。 | 命令返回码、输出、执行结果或状态变更体现“`nn.img2col1d` 合同（operand/attrs/result/verifier）”场景。 | `test_nn_dialect_img2col1d_contract_v1` |
| TC-NN-DIA-044 | 执行结果 | `nn.img2col2d` 合同（operand/attrs/result/verifier） | 准备公开输入数据、执行入口或 CLI 状态文件。 | 运行 `test_nn_dialect_img2col2d_contract_v1`。 | 命令返回码、输出、执行结果或状态变更体现“`nn.img2col2d` 合同（operand/attrs/result/verifier）”场景。 | `test_nn_dialect_img2col2d_contract_v1` |
| TC-NN-DIA-045 | 内存/DMA | `nn.softmax` 合法路径（rank/axis/shape/stride/space/element type） | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_softmax_op_verify_success`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`nn.softmax` 合法路径（rank/axis/shape/stride/space/element type）”场景。 | `test_softmax_op_verify_success` |
| TC-NN-DIA-046 | 边界/异常 | `nn.softmax` axis 越界或输入 rank 非法时拒绝 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_softmax_op_rejects_invalid_axis_or_rank`。 | “`nn.softmax` axis 越界或输入 rank 非法时拒绝”场景按公开错误语义失败或被拒绝。 | `test_softmax_op_rejects_invalid_axis_or_rank` |
| TC-NN-DIA-047 | 边界/异常 | `nn.softmax` result shape/stride/dtype/space 不一致时拒绝 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_softmax_op_rejects_result_mismatch`。 | “`nn.softmax` result shape/stride/dtype/space 不一致时拒绝”场景按公开错误语义失败或被拒绝。 | `test_softmax_op_rejects_result_mismatch` |
| TC-NN-DIA-048 | 边界/异常 | `nn.exp` 合法路径（浮点输入与元信息保持） | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_exp_op_verify_success`。 | 公开合法路径通过。 | `test_exp_op_verify_success` |
| TC-NN-DIA-049 | 边界/异常 | `nn.exp` 拒绝非浮点输入与 space/shape/stride 不一致 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_exp_op_rejects_invalid_inputs`。 | “`nn.exp` 拒绝非浮点输入与 space/shape/stride 不一致”场景按公开错误语义失败或被拒绝。 | `test_exp_op_rejects_invalid_inputs` |
| TC-NN-DIA-050 | 内存/DMA | `nn.reduce_sum` 的 `axes/keepdim` 与结果 shape 合同 | 准备公开 Memory/DMA 参数，包括 shape、stride、dtype、space 或切片元信息。 | 运行 `test_reduce_sum_op_shape_contract`。 | 内存类型、布局、搬运结果或 verifier 行为体现“`nn.reduce_sum` 的 `axes/keepdim` 与结果 shape 合同”场景。 | `test_reduce_sum_op_shape_contract` |
| TC-NN-DIA-051 | 边界/异常 | `nn.reduce_sum` 的 `axes` 非法输入拒绝 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_reduce_sum_op_rejects_invalid_axes`。 | “`nn.reduce_sum` 的 `axes` 非法输入拒绝”场景按公开错误语义失败或被拒绝。 | `test_reduce_sum_op_rejects_invalid_axes` |
| TC-NN-DIA-052 | 边界/异常 | `nn.reduce_min` 的 `keepdim` 与静态空归约域拒绝 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_reduce_min_op_contract_and_empty_extent_rejection`。 | “`nn.reduce_min` 的 `keepdim` 与静态空归约域拒绝”场景按公开错误语义失败或被拒绝。 | `test_reduce_min_op_contract_and_empty_extent_rejection` |
| TC-NN-DIA-053 | 边界/异常 | `nn.reduce_max` 的 `keepdim` 与静态空归约域拒绝 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_reduce_max_op_contract_and_empty_extent_rejection`。 | “`nn.reduce_max` 的 `keepdim` 与静态空归约域拒绝”场景按公开错误语义失败或被拒绝。 | `test_reduce_max_op_contract_and_empty_extent_rejection` |
| TC-NN-DIA-054 | 边界/异常 | `nn.reduce_*` 的 `dtype/space` 不一致拒绝 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_reduce_ops_reject_type_or_space_mismatch`。 | “`nn.reduce_*` 的 `dtype/space` 不一致拒绝”场景按公开错误语义失败或被拒绝。 | `test_reduce_ops_reject_type_or_space_mismatch` |
| TC-NN-DIA-055 | 解析/打印 | `nn.exp` 与 `nn.reduce_*` 模块 round-trip | 准备可 parse/print、round-trip 或文本比对的公开输入。 | 运行 `test_exp_reduce_module_round_trip`。 | parse/print、round-trip 或文本比对结果稳定。 | `test_exp_reduce_module_round_trip` |
| TC-NN-DIA-056 | 边界/异常 | `nn.reduce_*` 的 `keepdim` 非 `i1` attribute 拒绝 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_reduce_ops_reject_non_i1_keepdim_attr`。 | “`nn.reduce_*` 的 `keepdim` 非 `i1` attribute 拒绝”场景按公开错误语义失败或被拒绝。 | `test_reduce_ops_reject_non_i1_keepdim_attr` |
| TC-NN-DIA-057 | 边界/异常 | `nn.reduce_*` 的结果 `stride` 非连续布局拒绝 | 准备触发该错误路径的公开输入或非法参数组合。 | 运行 `test_reduce_ops_reject_non_contiguous_result_stride`。 | “`nn.reduce_*` 的结果 `stride` 非连续布局拒绝”场景按公开错误语义失败或被拒绝。 | `test_reduce_ops_reject_non_contiguous_result_stride` |
| TC-NN-DIA-058 | 解析/打印 | `!nn.memory` 原文 parser 的字符串字段、嵌套类型与非法文本边界 | 准备可 parse/print 的公开 memory type 文本和格式错误文本。 | 运行 `test_memory_dim_parser_and_mixed_add_public_parser_contracts`。 | 合法文本 round-trip 稳定，缺失尖括号、参数不完整、维度括号错误与非法打印条目按公开错误语义失败。 | `test_memory_dim_parser_and_mixed_add_public_parser_contracts` |
| TC-NN-DIA-059 | 边界/异常 | `nn.sub/mul/truediv/floordiv` mixed memory+scalar verifier 合同 | 准备公开 op 构造入口、memory operand 与 i32/f16/f32/symbol 标量输入。 | 运行 `test_mixed_scalar_binary_family_public_contracts`。 | memory+scalar 与 scalar+memory 合法路径通过，纯标量、space、shape、stride、unsupported scalar dtype 与 result dtype 不一致稳定失败。 | `test_mixed_scalar_binary_family_public_contracts` |
| TC-NN-DIA-060 | 边界/异常 | `nn.transpose` 动态维度连续 stride 合同 | 准备含动态 `?` 维度的公开 memory type 与 transpose op。 | 运行 `test_transpose_dynamic_stride_public_contract`。 | result 低维为动态时高维 stride 为 `?`、低维 stride 为 1 的公开布局通过 verifier。 | `test_transpose_dynamic_stride_public_contract` |
| TC-NN-DIA-061 | 边界/异常 | `nn.select`/`nn.cast`/activation 公开 verifier 错误矩阵 | 准备公开 op 构造入口、合法 memory operand 与 shape/stride/dtype/space 错误组合。 | 运行 `test_select_cast_activation_public_error_matrix`。 | select/cast/activation 对 space、shape、stride、dtype 与标量参数错误稳定拒绝。 | `test_select_cast_activation_public_error_matrix` |
| TC-NN-DIA-062 | 边界/异常 | `nn.img2col1d/2d` 的 symbol/dynamic 参数与错误矩阵 | 准备公开 op 构造入口、`symbol.const`、动态 shape、symbol 参数、非法 padding 与非连续 result stride。 | 运行 `test_img2col_public_symbol_dynamic_error_matrix`。 | 静态 symbol 常量、动态 shape 与 symbol 参数按公开合同通过或跳过静态公式校验；非法 padding 与非连续 result stride 稳定拒绝。 | `test_img2col_public_symbol_dynamic_error_matrix` |
