# expectation_pass_nn_to_kernel_green_plan.md

## 进度

| 编号 | 依赖 | worktree | 记录文件 | 进度 |
| --- | --- | --- | --- | --- |
| `S1` | `无` | `wt-20260405-exp-pass-nn-to-kernel-s1` | `20260405-exp-pass-nn-to-kernel-s1.md` | `spec初稿完成（T-20260405-0f7c2391，咯咯咯）；复审不通过（T-20260405-86f1ff4f，提莫炖蘑菇；原因：worktree 缺 expectation/pass/lowing/nn_to_kernel）；spec修订完成（T-20260405-6c8795ee，咯咯咯）；复审不通过（T-20260405-21ce2596，提莫炖蘑菇；原因：diff 仍为 spec 且 worktree 内 expectation 路径缺失）；同步尝试完成（T-20260405-21ce2596，金铲铲大作战：从主仓同步 11 个 verification 目录）；修复完成（T-20260405-380fc8df，朽木露琪亚：回滚 spec diff + 让 diff 实际包含 11 个 verification 目录并保证路径存在）；复审通过（T-20260405-c4a96e5d，不要啊教练）；已合并（commit 55b2203，T-20260405-f3f39cd9，李白）。` |
| `S2` | `S1` | `wt-20260405-exp-pass-nn-to-kernel-s2` | `20260405-exp-pass-nn-to-kernel-s2.md` | `spec 完成（T-20260405-f3fe9102，睡觉小分队）：已冻结 broadcast/exp/softmax/reduce_*/transpose helper->raw nn.* lowering 合同与失败边界，并补 MGEN-C2A~C2E；待复审（T-20260405-10bc4082，提莫炖蘑菇）。` |
| `S3` | `S1` | `wt-20260405-exp-pass-nn-to-kernel-s3` | `20260405-exp-pass-nn-to-kernel-s3.md` | `spec 完成（T-20260405-88d60767，咯咯咯）：已冻结 matmul 二维/contracting-dim/rank-2 合同与 img2col1d/img2col2d 结构化输出、禁止压扁列块及 fc/conv 收口边界；复审不通过（T-20260405-7b19b678，提莫炖蘑菇：记录文件未追踪，且 fc/conv 小节未机械复述收口边界，存在口径漂移风险）；修复完成（T-20260405-4a39a82d，咯咯咯：记录文件已纳入变更集，fc/conv 小节已机械补齐收口边界）；待复审（T-20260405-5c19f02c，提莫炖蘑菇）。` |
| `S4` | `S2、S3` | `wt-20260405-exp-pass-nn-to-kernel-s4` | `20260405-exp-pass-nn-to-kernel-s4.md` | `已合并（commit 54fe0d8，T-20260405-d18a7c34，李白）。` |
| `S5` | `S1` | `wt-20260405-exp-pass-nn-to-kernel-s5` | `20260405-exp-pass-nn-to-kernel-s5.md` | `spec 完成（T-20260405-4a4d7e34，朽木露琪亚）：已冻结 boundary CASE-12 pass 拒绝路径合同并补充测试目标/COV-N2K-026；复审不通过（T-20260405-0e315ec0，不要啊教练：CASE-12/COV-N2K-026 的 gate 口径存在机械不一致与可执行性证据缺口，且“不得部分成功”与 in-place 修改并存时缺少预检/无副作用约束）；修复进行中（T-20260405-a6c4d2b1，朽木露琪亚）。` |
| `S6` | `S4、S5` | `.` | `不要求` | `未开始` |

## 功能说明

- 本计划只覆盖当前正式 gate：`expectation/pass/lowing/nn_to_kernel/*` 下现存的 verification 文件，以及它们直接依赖的 `spec / DSL frontend / nn/kernel dialect / pass / test`。
- 当前正式 expectation 文件集合为：
  - `boundary`
  - `element_binary`
  - `element_compare`
  - `special_forms`
  - `broadcast`
  - `exp`
  - `softmax`
  - `reduce`
  - `matmul`
  - `transpose`
  - `img2col`
- `structured` 已从当前目录中删除，不再是 gate，也不再作为迁移入口维护。
- 本计划的 `P0` 目标只有一个：让上述现存 verification 文件全部通过，并保持 `pytest -q test/pass/test_lowering_nn_to_kernel.py` 持续绿灯。
- 已确认但未纳入本轮 `P0` 的合同升级只保留为后续事项，不反向污染当前 gate；其中最典型的是“匿名动态维 `?` 直接驱动 `dma.alloc.dynamic_shape`”。
- 本文件只做计划与边界收口，不直接实现。

## 范围与非目标

### 范围

- expectation：
  - [`expectation/pass/lowing/nn_to_kernel/boundary`](/home/lfr/kernelcode_generate/expectation/pass/lowing/nn_to_kernel/boundary)
  - [`expectation/pass/lowing/nn_to_kernel/element_binary`](/home/lfr/kernelcode_generate/expectation/pass/lowing/nn_to_kernel/element_binary)
  - [`expectation/pass/lowing/nn_to_kernel/element_compare`](/home/lfr/kernelcode_generate/expectation/pass/lowing/nn_to_kernel/element_compare)
  - [`expectation/pass/lowing/nn_to_kernel/special_forms`](/home/lfr/kernelcode_generate/expectation/pass/lowing/nn_to_kernel/special_forms)
  - [`expectation/pass/lowing/nn_to_kernel/broadcast`](/home/lfr/kernelcode_generate/expectation/pass/lowing/nn_to_kernel/broadcast)
  - [`expectation/pass/lowing/nn_to_kernel/exp`](/home/lfr/kernelcode_generate/expectation/pass/lowing/nn_to_kernel/exp)
  - [`expectation/pass/lowing/nn_to_kernel/softmax`](/home/lfr/kernelcode_generate/expectation/pass/lowing/nn_to_kernel/softmax)
  - [`expectation/pass/lowing/nn_to_kernel/reduce`](/home/lfr/kernelcode_generate/expectation/pass/lowing/nn_to_kernel/reduce)
  - [`expectation/pass/lowing/nn_to_kernel/matmul`](/home/lfr/kernelcode_generate/expectation/pass/lowing/nn_to_kernel/matmul)
  - [`expectation/pass/lowing/nn_to_kernel/transpose`](/home/lfr/kernelcode_generate/expectation/pass/lowing/nn_to_kernel/transpose)
  - [`expectation/pass/lowing/nn_to_kernel/img2col`](/home/lfr/kernelcode_generate/expectation/pass/lowing/nn_to_kernel/img2col)
  - [`expectation/utils/pass_lowering_nn_to_kernel.py`](/home/lfr/kernelcode_generate/expectation/utils/pass_lowering_nn_to_kernel.py)
- spec：
  - [`spec/pass/lowering/nn_to_kernel.md`](/home/lfr/kernelcode_generate/spec/pass/lowering/nn_to_kernel.md)
  - [`spec/dsl/ast.md`](/home/lfr/kernelcode_generate/spec/dsl/ast.md)
  - [`spec/dsl/mlir_gen.md`](/home/lfr/kernelcode_generate/spec/dsl/mlir_gen.md)
  - [`spec/operation/nn.md`](/home/lfr/kernelcode_generate/spec/operation/nn.md)
  - [`spec/dialect/nn.md`](/home/lfr/kernelcode_generate/spec/dialect/nn.md)
  - [`spec/dialect/kernel.md`](/home/lfr/kernelcode_generate/spec/dialect/kernel.md)
  - [`spec/dialect/dma.md`](/home/lfr/kernelcode_generate/spec/dialect/dma.md)
- 功能实现：
  - [`kernel_gen/dsl/ast.py`](/home/lfr/kernelcode_generate/kernel_gen/dsl/ast.py)
  - [`kernel_gen/dsl/emit_mlir.py`](/home/lfr/kernelcode_generate/kernel_gen/dsl/emit_mlir.py)
  - [`kernel_gen/dsl/mlir_gen.py`](/home/lfr/kernelcode_generate/kernel_gen/dsl/mlir_gen.py)
  - [`kernel_gen/operation/nn.py`](/home/lfr/kernelcode_generate/kernel_gen/operation/nn.py)
  - [`kernel_gen/dialect/nn.py`](/home/lfr/kernelcode_generate/kernel_gen/dialect/nn.py)
  - [`kernel_gen/dialect/kernel.py`](/home/lfr/kernelcode_generate/kernel_gen/dialect/kernel.py)
  - [`kernel_gen/dialect/dma.py`](/home/lfr/kernelcode_generate/kernel_gen/dialect/dma.py)
  - [`kernel_gen/passes/lowering/nn_to_kernel.py`](/home/lfr/kernelcode_generate/kernel_gen/passes/lowering/nn_to_kernel.py)
- test：
  - [`test/pass/test_lowering_nn_to_kernel.py`](/home/lfr/kernelcode_generate/test/pass/test_lowering_nn_to_kernel.py)
  - [`test/dsl/test_ast_visitor.py`](/home/lfr/kernelcode_generate/test/dsl/test_ast_visitor.py)
  - [`test/dsl/test_mlir_gen.py`](/home/lfr/kernelcode_generate/test/dsl/test_mlir_gen.py)
  - [`test/dialect/test_nn_dialect.py`](/home/lfr/kernelcode_generate/test/dialect/test_nn_dialect.py)
  - [`test/dialect/test_kernel_dialect.py`](/home/lfr/kernelcode_generate/test/dialect/test_kernel_dialect.py)
  - [`test/dialect/test_dma_dialect.py`](/home/lfr/kernelcode_generate/test/dialect/test_dma_dialect.py)

### 非目标

- 不恢复 `structured` 文件。
- 不通过删除 case、放弱正则、只做字符串命中、或绕过 `build_func_op(...)` 的方式伪造绿灯。
- 不把 `pipeline / lowered IR / gen_kernel / codegen` 纳入本轮通过证据。
- 不把“已确认但尚未写进当前 gate 的新合同”强行塞进 `P0`，以免把“当前文件全部通过”和“下一轮合同升级”混成一件事。

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`大闸蟹`
- `文档`：[`ARCHITECTURE/plan/expectation_pass_nn_to_kernel_green_plan.md`](/home/lfr/kernelcode_generate/ARCHITECTURE/plan/expectation_pass_nn_to_kernel_green_plan.md)
- `spec`：
  - [`spec/pass/lowering/nn_to_kernel.md`](/home/lfr/kernelcode_generate/spec/pass/lowering/nn_to_kernel.md)
  - [`spec/dsl/ast.md`](/home/lfr/kernelcode_generate/spec/dsl/ast.md)
  - [`spec/dsl/mlir_gen.md`](/home/lfr/kernelcode_generate/spec/dsl/mlir_gen.md)
  - [`spec/operation/nn.md`](/home/lfr/kernelcode_generate/spec/operation/nn.md)
  - [`spec/dialect/nn.md`](/home/lfr/kernelcode_generate/spec/dialect/nn.md)
  - [`spec/dialect/kernel.md`](/home/lfr/kernelcode_generate/spec/dialect/kernel.md)
  - [`spec/dialect/dma.md`](/home/lfr/kernelcode_generate/spec/dialect/dma.md)
- `功能实现`：
  - [`kernel_gen/dsl/ast.py`](/home/lfr/kernelcode_generate/kernel_gen/dsl/ast.py)
  - [`kernel_gen/dsl/emit_mlir.py`](/home/lfr/kernelcode_generate/kernel_gen/dsl/emit_mlir.py)
  - [`kernel_gen/dsl/mlir_gen.py`](/home/lfr/kernelcode_generate/kernel_gen/dsl/mlir_gen.py)
  - [`kernel_gen/operation/nn.py`](/home/lfr/kernelcode_generate/kernel_gen/operation/nn.py)
  - [`kernel_gen/dialect/nn.py`](/home/lfr/kernelcode_generate/kernel_gen/dialect/nn.py)
  - [`kernel_gen/dialect/kernel.py`](/home/lfr/kernelcode_generate/kernel_gen/dialect/kernel.py)
  - [`kernel_gen/dialect/dma.py`](/home/lfr/kernelcode_generate/kernel_gen/dialect/dma.py)
  - [`kernel_gen/passes/lowering/nn_to_kernel.py`](/home/lfr/kernelcode_generate/kernel_gen/passes/lowering/nn_to_kernel.py)
- `test`：
  - [`test/pass/test_lowering_nn_to_kernel.py`](/home/lfr/kernelcode_generate/test/pass/test_lowering_nn_to_kernel.py)
  - [`test/dsl/test_ast_visitor.py`](/home/lfr/kernelcode_generate/test/dsl/test_ast_visitor.py)
  - [`test/dsl/test_mlir_gen.py`](/home/lfr/kernelcode_generate/test/dsl/test_mlir_gen.py)
  - [`test/dialect/test_nn_dialect.py`](/home/lfr/kernelcode_generate/test/dialect/test_nn_dialect.py)
  - [`test/dialect/test_kernel_dialect.py`](/home/lfr/kernelcode_generate/test/dialect/test_kernel_dialect.py)
  - [`test/dialect/test_dma_dialect.py`](/home/lfr/kernelcode_generate/test/dialect/test_dma_dialect.py)

## 外部参考

- 仅作语义校准，不替代仓库内 spec：
  - MLIR Broadcastable trait：<https://mlir.llvm.org/docs/Traits/Broadcastable/>
  - MLIR Linalg dialect：<https://mlir.llvm.org/docs/Dialects/Linalg/>

## 当前实测状态

### 基线命令

```bash
pytest -q test/pass/test_lowering_nn_to_kernel.py
find expectation/pass/lowing/nn_to_kernel -maxdepth 1 -type f | sort | while read -r f; do
  PYTHONPATH=. python "$f"
done
```

### 当前结果（2026-04-05）

- `pytest -q test/pass/test_lowering_nn_to_kernel.py`：`29 passed`

| 文件 | 当前状态 | 当前直接现象 |
| --- | --- | --- |
| `boundary` | `失败` | `Case-12` 命中 `AttributeError: can't set attribute 'ops'` |
| `element_binary` | `通过` | 当前 gate 已绿 |
| `element_compare` | `通过` | 当前 gate 已绿 |
| `special_forms` | `通过` | 当前 gate 已绿 |
| `broadcast` | `失败` | 正例/负例都先命中 `AstVisitorError: Unsupported call expression` |
| `exp` | `失败` | 正例先命中 `AstVisitorError: Unsupported call expression` |
| `softmax` | `失败` | 正例/负例都先命中 `AstVisitorError: Unsupported call expression` |
| `reduce` | `失败` | 正例/负例都先命中 `AstVisitorError: Unsupported call expression` |
| `matmul` | `失败` | `CASE-4` 的 dtype 负例 `DID NOT RAISE` |
| `transpose` | `失败` | 正例/负例都先命中 `AstVisitorError: Unsupported call expression` |
| `img2col` | `失败` | `Unsupported formatted annotation` / `cannot use external value inside function body` |

### 当前真实失败清单

#### `broadcast` / `exp` / `softmax` / `reduce` / `transpose`

- 这五组 expectation 目前都没有进入 `nn -> kernel` lowering 主合同。
- 公开黑盒入口先在 `build_func_op(...)` 阶段失败，统一表现为 `AstVisitorError: Unsupported call expression`。
- 结果是：
  - 正例没法生成目标 `nn.*`
  - 负例也到不了目标失败边界，仍然被前置的 `Unsupported call expression` 吞掉

#### `img2col`

- 当前红点比其他文件更前：
  - `CASE-1 / CASE-2`：`Unsupported formatted annotation`
  - `CASE-3`：`cannot use external value inside function body`
  - `CASE-4`：由于前端更早失败，压扁输出负例还没打到目标 `result shape` 口径
- 这说明 `img2col` 当前至少有三层缺口：
  - 公共 helper 的注解/参数表达还没对齐
  - closure/external value 用法和 `reject_external_values=True` 冲突
  - 即使前端打通，`structured result`、dialect verifier 与 pass lowering 仍需继续对齐

#### `matmul`

- 当前 `matmul` 不是整条链都红：
  - 静态正例、symbolic 正例、inner-dim mismatch 负例已经能走到既有合同
  - 当前明确缺口只有 `dtype mismatch` 负例没有被拒绝
- 这意味着 `matmul` 优先级不是“补 helper”，而是“补错误边界”和可能缺失的 verifier / lowering reject。

#### `boundary`

- 当前真实红点只有 `CASE-12`。
- 失败原因不是 pass 主逻辑，而是 expectation 自己的坏输入探针无效：
  - 它试图通过 `setattr(module, "ops", None)` 伪造不可遍历 module
  - 但 `ModuleOp.ops` 不能这样覆写
  - 所以最终归因成了 `AttributeError`
- 当前 `CASE-10` 仍是旧合同：匿名动态维 `?` 被当成失败边界；它暂时不是本轮 `P0` 红点，但已知和后续升级方向不一致。

## 当前实现状态判断

### 已经稳定通过的部分

- `element_binary`
- `element_compare`
- `special_forms`

### 需要优先补的前端入口

- `broadcast`
- `exp`
- `softmax`
- `reduce_sum / reduce_min / reduce_max`
- `transpose`

这些 op 的共同现象是：当前 expectation 还没打到 verifier 或 pass，公开入口先卡在 `Unsupported call expression`。

### 需要单独收口的 operation / dialect 合同

- `img2col1d / img2col2d`
  - 结构化输出合同已经写进 expectation
  - 但前端注解、闭包取值、dialect rank/verifier、pass 目标 op 仍未形成闭环
- `matmul`
  - 正例基本能跑
  - dtype mismatch 拒绝口径还没锁住

### 需要单独收口的 pass / 边界

- `boundary CASE-12` 的坏输入构造法不成立，需要换成真正可构造的坏输入
- `Unsupported call expression` 不应长期成为 `broadcast / exp / softmax / reduce / transpose` 的统一出口；这些 expectation 已明确它们都属于支持路径

## 完成定义

- 以下 gate 全部通过：

```bash
pytest -q test/pass/test_lowering_nn_to_kernel.py
find expectation/pass/lowing/nn_to_kernel -maxdepth 1 -type f | sort | while read -r f; do
  PYTHONPATH=. python "$f"
done
```

- `expectation/pass/lowing/nn_to_kernel/*` 下现存 11 个 verification 文件全部通过。
- 每个 expectation 文件都命中它自己定义的目标边界，不再被更前置、更宽泛的错误吞掉。
- `build_func_op(...)` 负责的失败必须停在 frontend；pass 负责的失败必须停在 `LowerNnToKernelPass`；不能混层。
- `P0` 只以当前现存 verification 文件为准；`CASE-10` 的匿名动态维升级另起后续合同任务，不反向阻塞本轮绿灯。

## 计划任务

### `S1`

- `任务类型`：`spec任务`
- `目标`：在 [`spec/pass/lowering/nn_to_kernel.md`](/home/lfr/kernelcode_generate/spec/pass/lowering/nn_to_kernel.md) 冻结当前正式 gate 清单，明确 `structured` 已删除，正式入口只剩 11 个现存 verification 文件。
- `边界`：
  - 不恢复 `structured`
  - 不把“未来合同升级”混入当前绿灯定义
- `注意事项`：
  - spec 必须写清楚当前 gate 命令和正式文件名
  - spec 必须显式区分：frontend 失败、verifier 失败、pass 失败
- `代码示例`：

```bash
find expectation/pass/lowing/nn_to_kernel -maxdepth 1 -type f | sort
```

```bash
pytest -q test/pass/test_lowering_nn_to_kernel.py
find expectation/pass/lowing/nn_to_kernel -maxdepth 1 -type f | sort | while read -r f; do
  PYTHONPATH=. python "$f"
done
```

- `可改文件`：
  - [`spec/pass/lowering/nn_to_kernel.md`](/home/lfr/kernelcode_generate/spec/pass/lowering/nn_to_kernel.md)
- `下游需要覆盖层`：
  - `expectation/pass`
  - `test/pass`
- `验证命令`：

```bash
rg -n "structured|boundary|broadcast|img2col" spec/pass/lowering/nn_to_kernel.md
```

- `验收标准`：
  - spec 中不再出现 `structured` 作为正式 gate 文件
  - spec 中列出 11 个现存 expectation 文件
  - spec 中明确写出当前总 gate 命令

### `S2`

- `任务类型`：`spec任务`
- `目标`：在 [`spec/dsl/mlir_gen.md`](/home/lfr/kernelcode_generate/spec/dsl/mlir_gen.md) 冻结 `broadcast / exp / softmax / reduce_* / transpose` 的公开 helper -> raw `nn.*` 合同。
- `边界`：
  - 只定义公开黑盒入口
  - 不在本任务里定义 pass lowering 细节
- `注意事项`：
  - 目标是消除 `Unsupported call expression`
  - 负例必须在进入 raw `nn.*` 之前或之后有明确层级，不能继续被统一吞成同一个错误
- `代码示例`：

```python
def kernel(v: "Tensor[f32, 1, C]", t: "Tensor[f32, B, C]") -> "Tensor[f32, B, C]":
    return broadcast(v, t)
```

```python
def kernel(v: "Tensor[f32, B, C]") -> "Tensor[f32, B, C]":
    return softmax(v, axis=1)
```

```python
def kernel(v: "Tensor[f32, B, C]") -> "Tensor[f32, C, B]":
    return transpose(v, perm=[1, 0])
```

- `可改文件`：
  - [`spec/dsl/mlir_gen.md`](/home/lfr/kernelcode_generate/spec/dsl/mlir_gen.md)
- `下游需要覆盖层`：
  - `build_func_op / mlir_gen / emit_mlir`
  - `expectation/pass/broadcast`
  - `expectation/pass/exp`
  - `expectation/pass/softmax`
  - `expectation/pass/reduce`
  - `expectation/pass/transpose`
  - `test/dsl`
- `验证命令`：

```bash
PYTHONPATH=. python expectation/pass/lowing/nn_to_kernel/broadcast
PYTHONPATH=. python expectation/pass/lowing/nn_to_kernel/exp
PYTHONPATH=. python expectation/pass/lowing/nn_to_kernel/softmax
PYTHONPATH=. python expectation/pass/lowing/nn_to_kernel/reduce
PYTHONPATH=. python expectation/pass/lowing/nn_to_kernel/transpose
```

- `验收标准`：
  - `broadcast/exp/softmax/reduce/transpose` 的正例不再命中 `Unsupported call expression`
  - 这些文件的负例开始命中各自定义的 `shape / dtype / axis / perm` 边界
  - 失败层级在 spec 中可机械区分

### `S3`

- `任务类型`：`spec任务`
- `目标`：在 [`spec/operation/nn.md`](/home/lfr/kernelcode_generate/spec/operation/nn.md) 冻结 `img2col1d / img2col2d / matmul` 的 operation 合同，优先收口 `img2col` 结构化输出与 `matmul` dtype reject。
- `边界`：
  - 不把 `img2col` 再改回旧的压扁输出
  - 不把 `matmul` 的 dtype mismatch 继续留成“未定义行为”
- `注意事项`：
  - `img2col` 要分别写清 `NCHW/NHWC` 的输出维度排布
  - `img2col` 的 helper 参数应以内联字面量或公开参数表达，不能依赖函数外闭包值
  - `matmul` 必须把 `shape mismatch` 和 `dtype mismatch` 分成两个不同边界
- `代码示例`：

```python
def kernel(v: "Tensor[f32, N, C, H, W]") -> "Tensor[f32, N, C, KH, KW, OH, OW]":
    return img2col2d(v, kh=KH, kw=KW, sh=1, sw=1, dh=1, dw=1, ph=0, pw=0, pl=0, pr=0)
```

```python
def kernel(lhs: "Tensor[f32, M, K]", rhs: "Tensor[i32, K, N]") -> "Tensor[f32, M, N]":
    return matmul(lhs, rhs)
```

- `可改文件`：
  - [`spec/operation/nn.md`](/home/lfr/kernelcode_generate/spec/operation/nn.md)
- `下游需要覆盖层`：
  - `operation`
  - `dialect`
  - `expectation/pass/img2col`
  - `expectation/pass/matmul`
  - `test/dsl`
  - `test/dialect`
- `验证命令`：

```bash
PYTHONPATH=. python expectation/pass/lowing/nn_to_kernel/img2col
PYTHONPATH=. python expectation/pass/lowing/nn_to_kernel/matmul
```

- `验收标准`：
  - `img2col` 正例不再先命中 `Unsupported formatted annotation`
  - `img2col CASE-4` 能真正命中“旧压扁输出非法”的目标边界
  - `matmul CASE-4` 明确拒绝 dtype mismatch

### `S4`

- `任务类型`：`spec任务`
- `目标`：在 [`spec/dialect/kernel.md`](/home/lfr/kernelcode_generate/spec/dialect/kernel.md) 冻结 `kernel.broadcast / kernel.exp / kernel.softmax / kernel.reduce_* / kernel.matmul / kernel.transpose / kernel.img2col*` 的目标 op 合同与关键 attrs。
- `边界`：
  - 不使用“万能 kernel op”
  - 不把 `out` 消费链路写成“实现自定”
- `注意事项`：
  - expectation 已经要求 `dma.alloc -> kernel.* -> func.return` 是真实消费链路，不是只命中 op 名称
  - `reduce_sum / reduce_min / reduce_max` 可以共用一组 expectation，但 kernel dialect 不能失去区分
- `代码示例`：

```mlir
%out = dma.alloc ... : !nn.memory<...>
kernel.broadcast %src, %shape, %out : ...
func.return %out : !nn.memory<...>
```

```mlir
%out = dma.alloc ... : !nn.memory<...>
kernel.img2col2d %src, %out {kh = 2, kw = 3, sh = 1, sw = 1, ...} : ...
func.return %out : !nn.memory<...>
```

- `可改文件`：
  - [`spec/dialect/kernel.md`](/home/lfr/kernelcode_generate/spec/dialect/kernel.md)
- `下游需要覆盖层`：
  - `dialect/kernel`
  - `pass/lowering`
  - `expectation/pass/broadcast`
  - `expectation/pass/exp`
  - `expectation/pass/softmax`
  - `expectation/pass/reduce`
  - `expectation/pass/matmul`
  - `expectation/pass/transpose`
  - `expectation/pass/img2col`
  - `test/dialect`
- `验证命令`：

```bash
PYTHONPATH=. python expectation/pass/lowing/nn_to_kernel/broadcast
PYTHONPATH=. python expectation/pass/lowing/nn_to_kernel/reduce
PYTHONPATH=. python expectation/pass/lowing/nn_to_kernel/img2col
```

- `验收标准`：
  - expectation 中要求的 `kernel.*` 目标在 spec 中逐个有名有 attrs
  - `out` operand 的消费链路在 spec 中明确可验
  - `broadcast/exp/softmax/reduce/transpose/img2col` 不再只能停在 frontend 层

### `S5`

- `任务类型`：`spec任务`
- `目标`：在 [`spec/pass/lowering/nn_to_kernel.md`](/home/lfr/kernelcode_generate/spec/pass/lowering/nn_to_kernel.md) 冻结 pass 侧拒绝路径，优先修正 `boundary CASE-12` 的正式合同。
- `边界`：
  - 不通过 `setattr(module, "ops", None)` 这类无效探针伪造坏输入
  - 不删除 `CASE-12`
- `注意事项`：
  - 当前 `P0` 只要求 `CASE-12` 用真实可构造的坏输入命中 `module ops must be iterable`
  - `CASE-10` 的匿名动态维支持升级放到 `P1`，不要和本轮 current-green 混写
- `代码示例`：

```python
class BrokenModuleOp(ModuleOp):
    @property
    def ops(self):
        return None
```

```python
with pytest.raises(LowerNnToKernelError, match="module ops must be iterable"):
    LowerNnToKernelPass().run(BrokenModuleOp([]))
```

- `可改文件`：
  - [`spec/pass/lowering/nn_to_kernel.md`](/home/lfr/kernelcode_generate/spec/pass/lowering/nn_to_kernel.md)
- `下游需要覆盖层`：
  - `expectation/pass/boundary`
  - `test/pass`
  - `expectation/utils`
- `验证命令`：

```bash
PYTHONPATH=. python expectation/pass/lowing/nn_to_kernel/boundary
```

- `验收标准`：
  - `boundary CASE-12` 命中 `module ops must be iterable`
  - `boundary` 不再归因于 `AttributeError`
  - spec 中写清 `CASE-10` 属于后续升级，不属于本轮 current-green

### `S6`

- `任务类型`：`条件spec任务`
- `目标`：收口现存 11 个 verification 文件的一致绿灯定义，并把 `P0/P1` 分界写清。
- `边界`：
  - 不把 `P1` 后续升级伪装成“本轮已完成”
  - 不允许只跑 `pytest` 不跑 expectation
- `注意事项`：
  - `matmul` 当前只剩 dtype 负例缺口，绿灯时必须把它一起收掉
  - `img2col` 不能只让正例过，旧压扁输出负例也必须回到目标边界
- `代码示例`：

```bash
pytest -q test/pass/test_lowering_nn_to_kernel.py
find expectation/pass/lowing/nn_to_kernel -maxdepth 1 -type f | sort | while read -r f; do
  PYTHONPATH=. python "$f"
done
```

- `可改文件`：
  - [`spec/pass/lowering/nn_to_kernel.md`](/home/lfr/kernelcode_generate/spec/pass/lowering/nn_to_kernel.md)
- `下游需要覆盖层`：
  - `expectation/pass`
  - `test/pass`
  - `dsl`
  - `dialect`
  - `pass`
- `验证命令`：

```bash
pytest -q test/pass/test_lowering_nn_to_kernel.py
find expectation/pass/lowing/nn_to_kernel -maxdepth 1 -type f | sort | while read -r f; do
  PYTHONPATH=. python "$f"
done
```

- `验收标准`：
  - 11 个现存 expectation 文件全部通过
  - `pytest -q test/pass/test_lowering_nn_to_kernel.py` 继续通过
  - `broadcast / exp / softmax / reduce / transpose / img2col / matmul / boundary` 的当前红点全部消失
  - spec 中明确写出：本轮 `P0` 完成，`P1` 仅保留匿名动态维 `?` 的合同升级

## 推荐实施顺序

1. `S1`：先冻结当前 gate 清单，避免继续引用已删除的 `structured`
2. `S2`：先打通 `Unsupported call expression` 这组共同前置缺口
3. `S3`：单独收口 `img2col` 与 `matmul` 的 operation 边界
4. `S4`：补全对应 `kernel.*` 目标合同，防止 frontend 打通后 pass 仍无目标面
5. `S5`：修正 `boundary CASE-12` 的正式探针合同
6. `S6`：统一跑 gate，确认 current-green 完成

## 当前建议优先级

- 第一优先级：`S2`
  - 这是 `broadcast / exp / softmax / reduce / transpose` 五组文件的共同阻塞
- 第二优先级：`S3`
  - `img2col` 和 `matmul` 当前不是同一种红法，必须单独收口
- 第三优先级：`S5`
  - `boundary` 当前只有一个真实红点，成本最低，适合尽早拔掉
- 第四优先级：`S4`
  - frontend 合同冻结后，再补 `kernel.*` 目标面最稳

## `P1` 后续事项（不阻塞本轮 `P0`）

- 在 [`spec/dialect/dma.md`](/home/lfr/kernelcode_generate/spec/dialect/dma.md) 与相关 expectation 中正式升级：
  - 匿名动态维 `?` 可以作为 `dma.alloc.dynamic_shape` 来源
  - `boundary CASE-10` 从失败边界改成支持边界
- 这项已被确认是后续方向，但不属于“按当前文件全部通过”的本轮目标。
