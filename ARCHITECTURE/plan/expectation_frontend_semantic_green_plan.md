# expectation_frontend_semantic_green_plan.md

## 进度

| 编号 | 依赖 | worktree | 记录文件 | 进度 |
| --- | --- | --- | --- | --- |
| `S1` | `无` | `wt-20260404-exp-frontend-semantic-s1` | `20260404-exp-frontend-semantic-s1.md` | `spec 草案已建档（T-20260404-6f6042a9，睡觉小分队）；实现+补测完成（T-20260404-99bf6dc7，金铲铲大作战）；复审通过（T-20260404-3f7e38fb，提莫炖蘑菇）；已合并（commit 8784af5，T-20260404-5db48f7e，李白）。补充：spec/operation/nn.md 旧口径对齐已合并（commit 70fef3a，T-20260405-cdab739c，李白；记录 20260404-exp-frontend-semantic-s1-nn-spec-sync.md）。` |
| `S2` | `S1` | `wt-20260405-exp-frontend-semantic-s2` | `20260405-exp-frontend-semantic-s2.md` | `spec 已合并（commit c77101c，T-20260405-6449a15a，李白）；实现+补测完成（T-20260405-106b132b，朽木露琪亚）；复审通过（T-20260405-3177c78a，提莫炖蘑菇）；已合并（commit 741c177，T-20260405-c3c71acd，李白）。` |
| `S3` | `S1` | `wt-20260405-exp-frontend-semantic-s3` | `20260405-exp-frontend-semantic-s3.md` | `spec 已合并（commit 49c33cc，T-20260405-4d4784b3，李白）；实现+补测完成（T-20260405-0dfacddd，jcc你莫辜负）；复审不通过（T-20260405-a1b1ce7a，提莫炖蘑菇；改进建议：移除 kernel_gen/dsl/emit_mlir.py 未使用的 _parse_symbolic_dim_expr 与 sympy/re 死依赖）；修复完成（T-20260405-e827627b，jcc你莫辜负）；复审通过（T-20260405-bc014e9f，提莫炖蘑菇；gate exit=0）；已合并（commit 78fc879，T-20260405-09e5d033，李白；gate exit=0）。` |
| `S4` | `S1` | `wt-20260405-exp-frontend-semantic-s4` | `20260405-exp-frontend-semantic-s4.md` | `spec 已合并（commit 816a972，T-20260405-b0ea5b7f，李白）。` |
| `S5` | `S2、S3、S4` | `wt-20260405-exp-frontend-semantic-s5` | `20260405-exp-frontend-semantic-s5.md` | `spec 完成（T-20260405-1738e127，睡觉小分队）；实现+补测完成（T-20260405-09fe5943，朽木露琪亚）；复审通过（T-20260405-8f51a153，提莫炖蘑菇）；已合并（commit d9c3ca6，T-20260405-39044989，李白）。` |
| `S6` | `S5` |  |  | `未开始` |
| `S7` | `S6` |  |  | `未开始` |

## 功能说明

- 本计划只覆盖以下 expectation 质量基线：
  - `expectation/operation/**`
  - `expectation/dsl/mlir_gen/**`
  - `expectation/symbol_variable/**`
- 本计划明确排除：
  - `expectation/dsl/emit_c/**`
  - `expectation/pass/**`
- 目标不是“按当前实现回写 expectation”，而是先收口公开合同、再补齐必要功能，最终让上述 expectation 与对应单测可以稳定跑通。
- 本计划默认只拆 `spec任务`；实现、测试、审查、复审、合并由管理员另行统筹。
- 本计划不允许通过收窄 expectation、静默 fallback、生成不合法 IR、或把 pipeline/lowered IR/gen_kernel/codegen 结果冒充当前完成态来过关。

## 范围与非目标

### 范围

- `operation` 层：`arch` / `dma` / `nn` / `scf` expectation 与对应公开合同。
- `dsl/mlir_gen` 层：`build_func_op(...)`、AST/emit helper lowering、raw `func.func` / raw MLIR IR 合同。
- `symbol_variable` 层：`Memory` / `SymbolDim` 的 shape/stride/表达式序列化与比较口径。
- 与上述 expectation 直接相关的 `spec -> 实现 -> test` 对齐。

### 非目标

- 不把 `emit_c`、`pass`、`gen_kernel`、`pipeline` 纳入本轮验收闭环。
- 不新增与当前 expectation 清单无关的公开 API。
- 不把 `dma.fill`、`dma.broadcast`、`dma.transpose` 这类可能扩面的主题直接塞进本轮主线，除非新增 expectation 或既有 expectation 明确阻塞到它们。

### 新增 op 判断

- `dma.fill`：`spec/dialect/dma.md` 已有稳定方言合同；当前 expectation 清单并未要求新增 `operation helper` 或 `dsl helper`，因此本轮不把“公开新增 `dma.fill(...)`”列为硬门禁。
- `dma.broadcast` / `dma.transpose`：当前 expectation 清单、spec 与实现现状均未形成必须新增的公开消费者；本轮不建议先行扩面。
- `nn.transpose`：`spec/operation/nn.md` 与 `spec/dialect/nn.md` 已有锚点，但当前 expectation 清单未把它列为缺口；本轮不作为主线阻塞项。

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`大闸蟹`
- `文档`：[`ARCHITECTURE/plan/expectation_frontend_semantic_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/expectation_frontend_semantic_green_plan.md)
- `spec`：
  - [`spec/operation/nn.md`](/home/lfr/kernelcode_generate/spec/operation/nn.md)
  - [`spec/operation/dma.md`](/home/lfr/kernelcode_generate/spec/operation/dma.md)
  - [`spec/dialect/nn.md`](/home/lfr/kernelcode_generate/spec/dialect/nn.md)
  - [`spec/dsl/emit_mlir.md`](/home/lfr/kernelcode_generate/spec/dsl/emit_mlir.md)
  - [`spec/dsl/mlir_gen.md`](/home/lfr/kernelcode_generate/spec/dsl/mlir_gen.md)
  - [`spec/symbol_variable/memory.md`](/home/lfr/kernelcode_generate/spec/symbol_variable/memory.md)
  - [`spec/symbol_variable/symbol_dim.md`](/home/lfr/kernelcode_generate/spec/symbol_variable/symbol_dim.md)
- `功能实现`：
  - [`kernel_gen/operation/nn.py`](/home/lfr/kernelcode_generate/kernel_gen/operation/nn.py)
  - [`kernel_gen/operation/dma.py`](/home/lfr/kernelcode_generate/kernel_gen/operation/dma.py)
  - [`kernel_gen/dialect/nn.py`](/home/lfr/kernelcode_generate/kernel_gen/dialect/nn.py)
  - [`kernel_gen/dialect/dma.py`](/home/lfr/kernelcode_generate/kernel_gen/dialect/dma.py)
  - [`kernel_gen/dsl/ast.py`](/home/lfr/kernelcode_generate/kernel_gen/dsl/ast.py)
  - [`kernel_gen/dsl/emit_mlir.py`](/home/lfr/kernelcode_generate/kernel_gen/dsl/emit_mlir.py)
  - [`kernel_gen/dsl/mlir_gen.py`](/home/lfr/kernelcode_generate/kernel_gen/dsl/mlir_gen.py)
  - [`kernel_gen/symbol_variable/memory.py`](/home/lfr/kernelcode_generate/kernel_gen/symbol_variable/memory.py)
  - [`kernel_gen/symbol_variable/symbol_dim.py`](/home/lfr/kernelcode_generate/kernel_gen/symbol_variable/symbol_dim.py)
  - [`expectation/utils/compare.py`](/home/lfr/kernelcode_generate/expectation/utils/compare.py)
- `test`：
  - [`test/operation/test_operation_nn.py`](/home/lfr/kernelcode_generate/test/operation/test_operation_nn.py)
  - [`test/operation/test_operation_dma.py`](/home/lfr/kernelcode_generate/test/operation/test_operation_dma.py)
  - [`test/dsl/test_ast_visitor.py`](/home/lfr/kernelcode_generate/test/dsl/test_ast_visitor.py)
  - [`test/dsl/test_mlir_gen.py`](/home/lfr/kernelcode_generate/test/dsl/test_mlir_gen.py)
  - [`test/dialect/test_nn_dialect.py`](/home/lfr/kernelcode_generate/test/dialect/test_nn_dialect.py)
  - [`test/dialect/test_dma_dialect.py`](/home/lfr/kernelcode_generate/test/dialect/test_dma_dialect.py)
  - [`test/symbol_variable/test_memory.py`](/home/lfr/kernelcode_generate/test/symbol_variable/test_memory.py)

## 当前实测状态

### expectation 黑盒实测

- 实测命令：

```bash
find expectation/operation expectation/dsl/mlir_gen expectation/symbol_variable \
  -type f ! -path '*/__pycache__/*' | sort | while read -r file; do
  PYTHONPATH=. python "$file"
done
```

- 当前结果：

| 范围 | 总数 | 通过 | 失败 |
| --- | --- | --- | --- |
| `expectation/operation` | `21` | `16` | `5` |
| `expectation/dsl/mlir_gen` | `32` | `19` | `13` |
| `expectation/symbol_variable` | `2` | `1` | `1` |
| `总计` | `55` | `36` | `19` |

### 当前真实失败清单

- `operation` 层：
  - `expectation/operation/dma/memory_manage`
  - `expectation/operation/nn/broadcast_to`
  - `expectation/operation/nn/element_unary`
  - `expectation/operation/nn/img2col1d`
  - `expectation/operation/nn/img2col2d`
- `dsl/mlir_gen` 层：
  - `expectation/dsl/mlir_gen/dialect/dma/copy`
  - `expectation/dsl/mlir_gen/dialect/dma/read_tile`
  - `expectation/dsl/mlir_gen/dialect/dma/reshape_family`
  - `expectation/dsl/mlir_gen/dialect/nn/broadcast`
  - `expectation/dsl/mlir_gen/dialect/nn/broadcast_to`
  - `expectation/dsl/mlir_gen/dialect/nn/conv`
  - `expectation/dsl/mlir_gen/dialect/nn/element_binary`
  - `expectation/dsl/mlir_gen/dialect/nn/element_unary`
  - `expectation/dsl/mlir_gen/dialect/nn/fc`
  - `expectation/dsl/mlir_gen/dialect/nn/img2col1d`
  - `expectation/dsl/mlir_gen/dialect/nn/img2col2d`
  - `expectation/dsl/mlir_gen/dialect/nn/reduce`
  - `expectation/dsl/mlir_gen/dialect/nn/softmax`
- `symbol_variable` 层：
  - `expectation/symbol_variable/symbol_dim`

### 当前实现状态判断

- `spec` 已基本领先、主要是实现未跟上的部分：
  - `spec/dsl/emit_mlir.md` 已明确要求 `copy/img2col/matmul/floordiv` 等 lowering；当前实现仍有缺口。
  - `spec/dsl/mlir_gen.md` 已明确禁止“无 return 注解且无显式 return 时靠最后一个值猜输出”；当前 `build_func_op(...)` 周边仍有多处 helper/语法支持缺口。
  - `spec/dialect/dma.md` 已冻结 `dma.fill` 的 dialect/pass 边界；当前它不是本轮 expectation 主阻塞。
- `spec` 仍不够硬、需要先补清的部分：
  - `spec/operation/nn.md` 仍保留旧的 `broadcast_to(value, target)` 口径，未与 expectation 的 `broadcast_to(source, target_shape, space)` 对齐。
  - `spec/operation/nn.md` 的 `img2col1d/img2col2d` 仍需把“结构化输出维度”写成主合同，避免继续被压扁 rank-3 结果污染。
  - `spec/operation/dma.md` 尚未把 `alloc(..., format=...)` 写成公开合同。
  - `spec/symbol_variable/memory.md` / `spec/symbol_variable/symbol_dim.md` 对“符号表达式等价但底层 sympy 形态不同”时的公开比较口径还不够机械。

### 当前最关键的真实缺口

- `kernel_gen/operation/nn.py`
  - `broadcast_to` 仍是 `(value, target)`，与 expectation 公开合同不一致。
  - `img2col1d/img2col2d` 仍返回压扁形状，而 expectation 已要求结构化输出。
- `kernel_gen/operation/dma.py`
  - `alloc(...)` 当前不接受 `format=`，直接阻塞 `expectation/operation/dma/memory_manage`。
- `kernel_gen/symbol_variable/symbol_dim.py` / `kernel_gen/symbol_variable/memory.py`
  - `Symbol(8*N)` 与 `Mul(8*N)` 这类“文本等价、底层表达式类型不同”的情况，会把 unary expectation 卡在 stride 严格比较上。
  - `static - symbol` 一类混合表达式的 `get_value()` / 序列化顺序仍不稳定。
- `kernel_gen/dsl/ast.py` / `kernel_gen/dsl/emit_mlir.py` / `kernel_gen/dsl/mlir_gen.py`
  - `dma.copy/read_tile/reshape_family` 仍会打到 `Unsupported syntax`。
  - `nn.broadcast/broadcast_to/conv/fc/reduce/softmax/element_unary` 仍会打到 `Unsupported call expression`。
  - `floordiv` tensor lowering 缺失，当前错误为 `Unsupported binary op: floordiv`。
  - `img2col1d/img2col2d` 在 DSL lowering 后返回类型仍与结构化 expectation 不匹配。
- 旁路实现缺口：
  - `kernel_gen/dsl/emit_mlir.py` 仍存在 `_resolve_nn_arith_element_type(...)` 依赖不存在的 `Memory._promote_dtype`。
  - `pytest` 抽样中还可见 `Function return requires explicit return syntax or annotation` 相关失败，说明 helper 支持范围与函数级返回合同仍需一起收口。

### 审查补充与反证要求

- 当前检出下未找到 `ARCHITECTURE/reference/expectation_coverage_gap_record.md`；本计划不再依赖该名单，当前轮次统一以仓库中的 `expectation/operation/**`、`expectation/dsl/mlir_gen/**`、`expectation/symbol_variable/**` 现状与实测结果为准。
- 审查侧最容易误判完成的两类缺口，已提升为本计划硬门禁：
  - `拒绝路径 / Unsupported 口径类`：不能只看到“报错了”就算完成，必须锁定失败层级、错误类型与关键短语，并证明没有静默 fallback。
  - `仅做 raw IR 字符串命中类`：不能只看到 `nn.matmul` / `dma.copy` / `func.return` 等片段就算完成，必须证明 op 出现在正确层级、结果类型正确、且结果被 `return` 或后续 op 真正消费。
- 因此，本计划所有涉及 unsupported/负例/IR 片段的任务，统一追加以下反证要求：
  - 对失败路径：至少锁定 `build_func_op / emit_mlir / verifier / operation helper` 中的一个明确失败层级。
  - 对错误口径：至少锁定 `异常类型 / 错误消息关键短语 / 错误码` 三者之一；优先同时锁定前两项。
  - 对 raw IR 门禁：除字符串命中外，必须再检查 `return` 类型、目标 SSA 归属、或 downstream use，防止“只生成 op 名称但未真正入链”。
  - 对非目标反证：不得引入 `pipeline`、`lowered IR`、`gen_kernel`、`emit_c`、`codegen` 作为伪完成证据。

## 计划任务

### `S1`

- `任务类型`：`spec任务`
- `目标`：在 `spec/operation/nn.md` 冻结 `broadcast_to(source, target_shape, space)` 公开合同，并把 `img2col1d/img2col2d` 的结构化输出维度写成唯一稳定口径。
- `边界`：
  - 不回退到旧的 `broadcast_to(value, target)` 作为长期公开合同。
  - 不把压扁 rank-3 `img2col` 输出写成“实现可选”。
  - 不在本任务中新增 `dma.broadcast`、`dma.transpose`。
- `注意事项`：
  - `broadcast_to` 只接受 `source + target_shape + space`；`target_shape` 是维度列表，不是 `Memory`。
  - `img2col1d` 必须分别写清 `NCHW/NWC` 形态；`img2col2d` 必须分别写清 `NCHW/NHWC` 形态。
  - 动态 symbol 路径必须写成公式合同，而不是“由实现推导”。
- `代码示例`：

```python
src = Memory([1, SymbolDim("N")], NumericType.Float32, space=MemorySpace.GM)
out = broadcast_to(src, [SymbolDim("M"), SymbolDim("N")], MemorySpace.LM)
# 目标合同：out.shape == [M, N]，out.dtype == f32，out.space == LM
```

```python
x = Memory(["N", "C", "H", "W"], NumericType.Float16, space=MemorySpace.GM)
col = img2col2d(x, kh=3, kw=3, sh=1, sw=1, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)
# 目标合同：col.shape == [N, C, 3, 3, H_out, W_out]
# 非法例：broadcast_to(src, [SymbolDim("N")], MemorySpace.LM) 必须显式报 rank 错误
```
- `依赖`：`无`
- `可改文件`：[`spec/operation/nn.md`](/home/lfr/kernelcode_generate/spec/operation/nn.md)
- `下游需要覆盖层`：`operation`、`dialect`、`build_func_op/mlir_gen/emit_mlir`、`test`
- `验证命令`：
  - `PYTHONPATH=. python expectation/operation/nn/broadcast_to`
  - `PYTHONPATH=. python expectation/operation/nn/img2col1d`
  - `PYTHONPATH=. python expectation/operation/nn/img2col2d`
- `验收标准`：
  - `expectation/operation/nn/broadcast_to`：输入 `source=Memory([1, N], f32, GM)`、`target_shape=[M, N]`、`space=LM`，输出必须是 `Memory([M, N], f32, LM)`；非法 target rank / 不可 broadcast 时必须显式报错。
  - `expectation/operation/nn/img2col1d`：输入 `NCHW=[N, C, W]` 时输出必须是 `[N, C, kw, W_out]`；输入 `NWC=[N, W, C]` 时输出必须是 `[N, W_out, kw, C]`。
  - `expectation/operation/nn/img2col2d`：输入 `NCHW=[N, C, H, W]` 时输出必须是 `[N, C, kh, kw, H_out, W_out]`；输入 `NHWC=[N, H, W, C]` 时输出必须是 `[N, H_out, W_out, kh, kw, C]`。

### `S2`

- `任务类型`：`spec任务`
- `目标`：在 `spec/operation/dma.md` 增补 `alloc(shape, dtype, space=..., stride=None, format=...)` 合同，并统一 `copy/load/slice/reshape/flatten` 的 operation 输出与错误边界。
- `边界`：
  - 只定义公开 helper 合同，不把 DSL AST 细节写进本文件。
  - 不在本任务中定义 `dma.fill` DSL helper。
- `注意事项`：
  - `alloc` 的 `format` 必须是公开参数，不得继续依赖 `Memory` 默认格式绕过 expectation。
  - `copy/load/slice/reshape/flatten` 的输入域错误必须锁定错误层级与关键短语。
- `代码示例`：

```python
buf = alloc(
    [SymbolDim("M"), SymbolDim("N")],
    NumericType.Float16,
    space=MemorySpace.LM,
    stride=[1, 1],
    format=Farmat.CLast,
)
# 目标合同：buf.format == Farmat.CLast
```

```python
def copy_kernel(src: "Tensor[f32, 8, 8]") -> "Tensor[f32, 8, 8]":
    from kernel_gen.operation.dma import copy
    return copy(src, MemorySpace.SM)

# 目标 raw IR：dma.alloc + dma.copy + func.return
# 非法例：copy(src, "SM") 必须在 helper/build_func_op 边界显式报错
```
- `依赖`：`无`
- `可改文件`：[`spec/operation/dma.md`](/home/lfr/kernelcode_generate/spec/operation/dma.md)
- `下游需要覆盖层`：`operation`、`build_func_op/mlir_gen/emit_mlir`、`test`
- `验证命令`：
  - `PYTHONPATH=. python expectation/operation/dma/memory_manage`
  - `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/dma/copy`
  - `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/dma/read_tile`
  - `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/dma/reshape_family`
- `验收标准`：
  - `expectation/operation/dma/memory_manage`：输入 `shape=[M, N]`、`dtype=f16`、`space=LM`、`stride=[1, 1]`、`format=CLast`，`alloc(...)` 必须返回携带该 `format` 的 `Memory`。
  - `expectation/dsl/mlir_gen/dialect/dma/copy`：输入 `copy(src, MemorySpace.SM)` 时，raw `func.func` 必须包含 `dma.alloc + dma.copy + func.return`，且返回类型等于目标 memory。
  - `expectation/dsl/mlir_gen/dialect/dma/read_tile`：`load(...)` 必须直接生成 `dma.load`；`slice(...)` 必须生成 `dma.alloc + dma.slice` 并返回 alloc 结果；非法 `space/source/arity` 必须显式报错。
  - `expectation/dsl/mlir_gen/dialect/dma/reshape_family`：`reshape(...)` 与 `flatten(...)` 必须生成 `dma.reshape`；`flatten` 返回 `[prod(shape)]`；返回注解不匹配时必须报 `Return type does not match annotation`。

### `S3`

- `任务类型`：`spec任务`
- `目标`：在 `spec/dialect/nn.md` 把 `nn.broadcast`、`nn.reduce_*`、`nn.img2col1d/img2col2d`、`nn.exp` 的 verifier 失败口径与结果类型合同写得更机械。
- `边界`：
  - 不在本文件重写上游 operation 公式全文，只冻结方言级字段、result type 与 verifier 关键短语。
  - `fc/conv` 若本层无独立 op，则只写它们落到 `nn.matmul` / `nn.img2col*` 的方言边界，不伪造新 op。
- `注意事项`：
  - `img2col1d/img2col2d` 的 result rank 必须与 `S1` 对齐，不允许继续保留压扁口径。
  - `reduce_*`、`exp` 的 unsupported / verifier 失败必须锁定短语，避免后续静默放行。
- `代码示例`：

```mlir
%0 = nn.exp %arg0 : !nn.memory<f32, [N, C], GM> -> !nn.memory<f32, [N, C], GM>
// 目标合同：f32/f16/bf16/f64 通过；i32 输入必须 verifier 失败并包含
// operand-element-type-must-be-float
```

```mlir
%1 = nn.img2col2d %arg0 {
  kh = 3 : i64, kw = 3 : i64, sh = 1 : i64, sw = 1 : i64,
  dh = 1 : i64, dw = 1 : i64, ph = 0 : i64, pw = 0 : i64, pl = 0 : i64, pr = 0 : i64
} : !nn.memory<f16, [N, C, H, W], GM> -> !nn.memory<f16, [N, C, 3, 3, H_out, W_out], GM>
// 目标合同：result rank/type 必须与结构化输出一致
```
- `依赖`：`S1`
- `可改文件`：[`spec/dialect/nn.md`](/home/lfr/kernelcode_generate/spec/dialect/nn.md)
- `下游需要覆盖层`：`dialect`、`build_func_op/mlir_gen/emit_mlir`、`test`
- `验证命令`：
  - `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/element_unary`
  - `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/reduce`
  - `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/img2col1d`
  - `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/img2col2d`
- `验收标准`：
  - `expectation/dsl/mlir_gen/dialect/nn/element_unary`：`exp(float memory)` 可 lower；`exp(int memory)` 必须以 `VerifyException` 显式失败，并包含 `operand-element-type-must-be-float`。
  - `expectation/dsl/mlir_gen/dialect/nn/reduce`：`reduce_sum/reduce_min/reduce_max` 的 `axes/keepdim` 非法输入必须显式失败，并锁定方言 verifier 关键短语。
  - `expectation/dsl/mlir_gen/dialect/nn/img2col1d`：返回 type 必须与 `[N, C, kw, W_out]` 或 `[N, W_out, kw, C]` 对齐。
  - `expectation/dsl/mlir_gen/dialect/nn/img2col2d`：返回 type 必须与 `[N, C, kh, kw, H_out, W_out]` 或 `[N, H_out, W_out, kh, kw, C]` 对齐。

### `S4`

- `任务类型`：`spec任务`
- `目标`：在 `spec/dsl/emit_mlir.md` 收口 DMA/NN helper lowering 矩阵，明确哪些 helper 必须直接 lower、哪些非法输入必须显式失败、以及不允许生成的旁路结果。
- `边界`：
  - 只覆盖 emit 节点级 mapping，不把 pipeline、lowered IR、emit_c、gen_kernel 写进完成态。
  - 不把 `Unsupported call expression` 当成长期允许结果；仅允许它存在于“当前真实缺口描述”与“未支持前的显式失败口径”。
- `注意事项`：
  - 必须把 `floordiv`、`broadcast/broadcast_to`、`conv/fc`、`reduce`、`softmax`、`element_unary`、`img2col1d/img2col2d` 都写进 helper lowering 表。
  - 对 `conv/fc` 要明确是 lower 到 `nn.img2col* + nn.matmul` / `nn.matmul`，还是在 emit 层保持 helper；不能留白。
  - 对 `copy/load/slice/reshape/flatten` 要明确结果 op 与返回 memory 的关系。
- `代码示例`：

```python
def fc_kernel(x: "Tensor[f16, B, K]", w: "Tensor[f16, M, K]") -> "Tensor[f16, B, M]":
    from kernel_gen.operation.nn import fc
    return fc(x, w)

# 目标 emit 语义：helper 不能停在 Unsupported call expression；
# 必须明确 lower 为约定的 nn.matmul 片段及返回类型
```

```python
def reshape_kernel(src: "Tensor[f32, 4, 8]") -> "Tensor[f32, 32]":
    from kernel_gen.operation.dma import flatten
    return flatten(src)

# 目标 emit 语义：生成 dma.reshape，返回 !nn.memory<f32, [32], ...>
```
- `依赖`：`S1`、`S2`、`S3`
- `可改文件`：[`spec/dsl/emit_mlir.md`](/home/lfr/kernelcode_generate/spec/dsl/emit_mlir.md)
- `下游需要覆盖层`：`build_func_op/mlir_gen/emit_mlir`、`dialect`、`test`
- `验证命令`：
  - `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/dma/copy`
  - `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/dma/read_tile`
  - `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/dma/reshape_family`
  - `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/broadcast`
  - `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/broadcast_to`
  - `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/conv`
  - `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/element_binary`
  - `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/element_unary`
  - `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/fc`
  - `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/reduce`
  - `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/softmax`
- `验收标准`：
  - `expectation/dsl/mlir_gen/dialect/nn/element_binary`：`add/sub/mul/truediv/floordiv` 同 shape 输入都能 lower；`floordiv` 不得再报 `Unsupported binary op: floordiv`。
  - `expectation/dsl/mlir_gen/dialect/nn/broadcast`：显式 target memory 路径必须生成 `nn.broadcast`，返回类型与 target 一致。
  - `expectation/dsl/mlir_gen/dialect/nn/broadcast_to`：`broadcast_to(source, target_shape, space)` 必须 lower 成合法 IR，而不是停在 `Unsupported call expression`。
  - `expectation/dsl/mlir_gen/dialect/nn/conv` / `fc`：helper lowering 后必须在 raw IR 中命中约定的 `nn.img2col*` / `nn.matmul` 片段；helper 未支持前的失败边界必须是显式、固定的错误短语。
  - `expectation/dsl/mlir_gen/dialect/dma/copy/read_tile/reshape_family`：禁止生成不合法 IR、禁止静默绕过 helper，且错误必须落在 `AstVisitorError` / verifier。

### `S5`

- `任务类型`：`spec任务`
- `目标`：在 `spec/dsl/mlir_gen.md` 冻结 `build_func_op(...)` 的函数级入口合同，包括 helper 支持范围、`Unsupported syntax` / `Unsupported call expression` 的分工、以及 raw `func.func` 边界。
- `边界`：
  - 不把 pipeline、pass、emit_c、gen_kernel 纳入 `build_func_op(...)` 的职责。
  - 不允许把“helper 还没接好”偷写成“实现可选”。
- `注意事项`：
  - 对 `dma.copy/read_tile/reshape_family` 这类当前打到 `Unsupported syntax` 的 case，要明确问题究竟属于 AST 语法、helper 入口、还是 emit 阶段。
  - 对函数级 return 合同，要继续坚持“无注解且无显式 return 时不得猜输出”。
- `代码示例`：

```python
def add_memory(a: "Tensor[f32, 8, 8]", b: "Tensor[f32, 8, 8]"):
    from kernel_gen.operation.nn import add
    return add(a, b)

# 目标合同：build_func_op(add_memory, A, B) 允许从显式 return 推断输出类型
```

```python
def bad_body(a: "Tensor[f32, 8, 8]", b: "Tensor[f32, 8, 8]"):
    from kernel_gen.operation.nn import add
    add(a, b)

# 目标合同：无返回注解且无显式 return，必须报
# Function return requires explicit return syntax or annotation
```
- `依赖`：`S4`
- `可改文件`：[`spec/dsl/mlir_gen.md`](/home/lfr/kernelcode_generate/spec/dsl/mlir_gen.md)
- `下游需要覆盖层`：`build_func_op/mlir_gen/emit_mlir`、`test`
- `验证命令`：
  - `PYTHONPATH=. python expectation/dsl/mlir_gen/return_type_from_body_not_signature`
  - `PYTHONPATH=. python expectation/dsl/mlir_gen/use_global_value`
  - `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/dma/copy`
  - `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/dma/read_tile`
  - `PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/dma/reshape_family`
- `验收标准`：
  - `return_type_from_body_not_signature`：有显式 `return` 且无返回注解时，`func.return` 类型必须以实际 body lowering 结果为准。
  - `use_global_value`：仍必须拒绝外部值隐式捕获，错误边界不回退。
  - `expectation/dsl/mlir_gen/dialect/dma/copy/read_tile/reshape_family`：合法 helper 不得再先打到 `Unsupported syntax`；非法 helper 语法必须稳定落在指定错误类型与短语。

### `S6`

- `任务类型`：`spec任务`
- `目标`：在 `spec/symbol_variable/memory.md` 明确 `shape/stride` 的公开比较口径，并把“语义等价但底层 sympy 形态不同”的处理规则写成合同。
- `边界`：
  - 不新增 `Memory` 额外公开 API。
  - 不把 expectation compare helper 的临时实现细节写成 `Memory` 长期语义。
- `注意事项`：
  - 要区分“公开值语义等价”和“内部表达式结构完全一致”两种口径。
  - 对继承输入 stride 的 unary/broadcast/softmax 等 helper，要写清到底锁 `get_value()` 还是锁底层 sympy 结构。
- `代码示例`：

```python
lhs = Memory([SymbolDim("M"), SymbolDim("N")], NumericType.Float32, stride=[SymbolDim("N"), 1])
rhs = Memory([SymbolDim("M"), SymbolDim("N")], NumericType.Float32, stride=[SymbolDim("N"), 1])

# 目标合同示例一：若只锁公开值语义，则 Symbol("8*N") 与 Mul(8*N) 不应误判为不同 stride
# 目标合同示例二：若某条 expectation 要锁精确结构，必须在 spec 中显式写明 exact 口径
```
- `依赖`：`无`
- `可改文件`：[`spec/symbol_variable/memory.md`](/home/lfr/kernelcode_generate/spec/symbol_variable/memory.md)
- `下游需要覆盖层`：`symbol_variable`、`operation`、`expectation/utils/compare.py`、`test`
- `验证命令`：
  - `PYTHONPATH=. python expectation/operation/nn/element_unary`
  - `PYTHONPATH=. python expectation/symbol_variable/memory`
- `验收标准`：
  - `expectation/operation/nn/element_unary`：输入带动态 stride 时，输出必须按公开合同继承输入元信息；若合同只锁公开值语义，则 `8*N` 的不同 sympy 内部形态不得误判失败。
  - `expectation/symbol_variable/memory`：默认 stride、显式 stride、动态 stride 的公开返回值与字符串序列化必须保持一致，不引入新的比较旁路。

### `S7`

- `任务类型`：`spec任务`
- `目标`：在 `spec/symbol_variable/symbol_dim.md` 冻结 `get_value()`、混合静动态运算顺序、以及表达式序列化的机械比较口径。
- `边界`：
  - 不新增 `SymbolDim` 新公开方法。
  - 不把 sympy 内部对象类型直接暴露成对外合同。
- `注意事项`：
  - `static - symbol`、`symbol - static`、`static // symbol`、`symbol // static` 的结果文本必须可机械比较。
  - 需要写清哪些场景比较 `int/float`，哪些场景比较稳定字符串。
- `代码示例`：

```python
assert SymbolDim(8).get_value() == 8
assert (SymbolDim(9) // SymbolDim(4)).get_value() == 2
assert (SymbolDim("M") * 4).get_value() == "4*M"
assert (8 - SymbolDim("M")).get_value() == "8 - M"
```

```python
# 目标合同：混合静动态表达式的公开比较以稳定字符串为准，
# 不允许同一语义今天输出 "8 - M"、明天输出 "-M + 8"
```
- `依赖`：`S6`
- `可改文件`：[`spec/symbol_variable/symbol_dim.md`](/home/lfr/kernelcode_generate/spec/symbol_variable/symbol_dim.md)
- `下游需要覆盖层`：`symbol_variable`、`operation`、`dsl/mlir_gen`、`test`
- `验证命令`：
  - `PYTHONPATH=. python expectation/symbol_variable/symbol_dim`
- `验收标准`：
  - `expectation/symbol_variable/symbol_dim`：静态整数输入时，`is_dynamic=False` 且 `get_value()` 可直接与 Python 结果比较。
  - `expectation/symbol_variable/symbol_dim`：混合表达式 `static - symbol`、`symbol * static`、`symbol // static` 的 `get_value()` 文本必须稳定，不因内部规约顺序漂移。

## 规格冻结后的实现收口清单

- `kernel_gen/operation/nn.py`
  - 把 `broadcast_to` 改到 `source + target_shape + space` 合同。
  - 把 `img2col1d/img2col2d` 改到结构化输出 shape。
- `kernel_gen/operation/dma.py`
  - 给 `alloc(...)` 增加 `format=`。
- `kernel_gen/dialect/nn.py`
  - 对 `broadcast/reduce/exp/img2col*` 的 result type 与 verifier 短语按 `S3` 收口。
- `kernel_gen/symbol_variable/memory.py` / `kernel_gen/symbol_variable/symbol_dim.py`
  - 统一 stride / 表达式公开比较口径，避免 `Symbol(...)` 与 `Mul(...)` 的伪差异。
- `kernel_gen/dsl/ast.py` / `kernel_gen/dsl/emit_mlir.py` / `kernel_gen/dsl/mlir_gen.py`
  - 补齐 `copy/load/slice/reshape/flatten` 的合法 helper 路径。
  - 补齐 `broadcast/broadcast_to/conv/fc/reduce/softmax/element_unary/floordiv/img2col*` 的 lowering。
  - 修掉 `_resolve_nn_arith_element_type(...)` 对不存在 `Memory._promote_dtype` 的依赖。
  - 继续保持 raw `func.func` 为唯一完成边界，不提前扩到 pipeline/lowered IR/codegen。

## 总门禁

- expectation 黑盒门禁：

```bash
find expectation/operation expectation/dsl/mlir_gen expectation/symbol_variable \
  -type f ! -path '*/__pycache__/*' | sort | while read -r file; do
  PYTHONPATH=. python "$file"
done
```

- 推荐单测门禁：

```bash
PYTHONPATH=. pytest -q \
  test/operation/test_operation_nn.py \
  test/operation/test_operation_dma.py \
  test/dsl/test_ast_visitor.py \
  test/dsl/test_mlir_gen.py \
  test/dialect/test_nn_dialect.py \
  test/dialect/test_dma_dialect.py \
  test/symbol_variable
```

## 结论

- 当前不是“expectation 写得过头”，而是 `operation -> dialect -> dsl/mlir_gen -> symbol_variable` 这几层存在公开合同漂移与实现断口。
- 本轮最短路径不是先扩 `dma.fill/broadcast/transpose`，而是先把已经进入 expectation 的 `broadcast_to`、`img2col1d/img2col2d`、`alloc(format)`、symbol 比较口径、以及 DSL helper lowering 真正打通。
- 管理员后续若要分发，建议严格按 `S1 -> S3/S2 -> S4 -> S5 -> S6 -> S7` 的顺序收口；其中 `S1`、`S2`、`S3` 是前置规格门禁，未冻结前不要分散实现。
