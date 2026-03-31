# conv_cpu_tiled_v1_plan.md

## 进度
更新日期：2026-04-01
更新规则：每个任务块进入新子阶段后立即更新本段。

| 任务 | 依赖 | 记录文件 | worktree | 当前进度 |
| --- | --- | --- | --- | --- |
| P10（W0） | 无 |  |  |  |
| P11（W0） | 无 |  |  |  |
| P16（W0） | 无 |  |  |  |
| P12（W1） | P10、P11、P16 |  |  |  |
| P13（W2） | P11、P12 |  |  |  |
| P14（W3） | P13 |  |  |  |
| P15（W4） | 条件任务（P17 需要时启用） |  |  |  |
| P17（W5） | P14、P16（若启用 P15 则追加 P15） |  |  |  |
| P18（W6） | P17（条件任务） |  |  |  |

## 功能说明

- 本计划基于当前仓库实现重新拟定，用来把 `for-loop + img2col2d + tiled compute -> CPU C/C++` 这条链真正推进到最终目标。
- 下文只以当前实现为起点描述“已经具备什么”和“还差什么”；管理员后续分发应直接按本计划推进。
- 当前最关键的判断是：`operation / dialect / DSL lowering / include/cpu` 已经形成 `img2col` 主线基线，真正的缺口已经后移到 `emit_c/gen_kernel`。

## 使用示例

- 管理员先确认当前 `img2col` 基线，再按“本轮收口顺序”放行。
- 若执行者回报以下命令均通过，说明 `img2col` 上游与中游链路已经可用，不应继续把资源投入到命名、verifier 或 DSL 入口层：

```bash
PYTHONPATH=. pytest -q test/operation/test_operation_nn.py -k 'img2col1d or img2col2d'
pytest -q test/dialect/test_nn_dialect.py -k 'img2col1d or img2col2d'
pytest -q test/dsl/test_emit_mlir.py -k 'img2col1d or img2col2d'
pytest -q test/dsl/test_mlir_gen.py -k 'img2col'
PYTHONPATH=. pytest -q test/include/cpu/test_nn.py -k 'img2col1d or img2col2d'
```

- 若执行者在 [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py) 与 [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py) 中仍找不到 `img2col`、`cpu::img2col2d`、tile-local compute、输出写回等生成逻辑，则当前主阻塞仍在 CPU 代码生成侧。

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`大闸蟹`
- `文档`：[`ARCHITECTURE/plan/conv_cpu_tiled_v1_plan.md`](../../ARCHITECTURE/plan/conv_cpu_tiled_v1_plan.md)
- `spec`：
  - [`spec/operation/nn.md`](../../spec/operation/nn.md)
  - [`spec/dialect/nn.md`](../../spec/dialect/nn.md)
  - [`spec/dsl/ast.md`](../../spec/dsl/ast.md)
  - [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
  - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
  - [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md)
  - [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
  - [`spec/include/cpu/cpu.md`](../../spec/include/cpu/cpu.md)
- `功能实现`：
  - [`kernel_gen/operation/nn.py`](../../kernel_gen/operation/nn.py)
  - [`kernel_gen/dialect/nn.py`](../../kernel_gen/dialect/nn.py)
  - [`kernel_gen/dsl/ast.py`](../../kernel_gen/dsl/ast.py)
  - [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py)
  - [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py)
  - [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py)
  - [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)
  - [`include/cpu/Nn.h`](../../include/cpu/Nn.h)
- `test`：
  - [`test/operation/test_operation_nn.py`](../../test/operation/test_operation_nn.py)
  - [`test/dialect/test_nn_dialect.py`](../../test/dialect/test_nn_dialect.py)
  - [`test/dsl/test_ast.py`](../../test/dsl/test_ast.py)
  - [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py)
  - [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py)
  - [`test/dsl/test_emit_c.py`](../../test/dsl/test_emit_c.py)
  - [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)
  - [`test/include/cpu/test_nn.py`](../../test/include/cpu/test_nn.py)

## 当前实现基线

### 已具备

- [`kernel_gen/operation/nn.py`](../../kernel_gen/operation/nn.py) 已经提供 `img2col1d(...)` 与 `img2col2d(...)`，并且 [`test/operation/test_operation_nn.py`](../../test/operation/test_operation_nn.py) 对应 case 当前通过。
- [`kernel_gen/dialect/nn.py`](../../kernel_gen/dialect/nn.py) 已经包含 `NnImg2col1dOp` 与 `NnImg2col2dOp`，对应的方言测试当前通过。
- [`kernel_gen/dsl/ast.py`](../../kernel_gen/dsl/ast.py)、[`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py)、[`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py) 已经能解析并 lowering `img2col1d/img2col2d`、`get_shape/get_stride` 等 DSL 入口。
- [`include/cpu/Nn.h`](../../include/cpu/Nn.h) 已经提供 `cpu::img2col1d(...)` 与 `cpu::img2col2d(...)` 叶子接口；CPU include 层不是当前主阻塞。

### 当前断点

1. [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py) 当前只覆盖 `arith.*`、`symbol.add`、`scf.for`、`dma.load/store` 等最小子集，不覆盖 `nn.img2col2d`、`dma.slice/deslice/view/alloc`、tile-local 累加等 `conv` 主线需要的节点。

2. [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py) 当前还是“函数签名 + 简单语句拼装”层，不包含 `conv2d_img2col2d_tiled(...)` 这类结构化 CPU kernel 的装配逻辑。

3. 当前测试集中还没有针对 `img2col2d + tiled compute -> CPU C/C++` 的 `emit_c/gen_kernel` 端到端断言；因此即使上游 lowering 已成，最终代码生成目标仍未被锁定。

## 最终目标

- 用户能够用 `Memory + operation API + Python for-loop` 写出 `img2col2d + tiled compute` 形态的 DSL。
- DSL 经现有通用链路 lowering 后，`emit_c/gen_kernel` 能生成结构正确的 CPU C/C++ 源码。
- 生成源码必须体现以下固定策略：
  - 输入：`NCHW * FCHW`
  - 输出：`[N, F, Ho, Wo]`
  - `Ntile = 1`
  - `Ctile = 16`
  - `Ftile = 16`
  - `Hotile = 16`
  - `Wotile = 16`
  - 逻辑采用 `img2col2d`
  - 物理实现采用 tile-local pack、tiled compute 与 tail 处理

## 本轮边界

- 不回头重做 `img2col1d/img2col2d` 的 operation、dialect、AST、emit_mlir、mlir_gen 命名与公开契约。
- 不新增 `conv_cpu_codegen.py` 或任何绕开现有 `emit_c/gen_kernel` 的专用旁路。
- 不引入 `kernel dialect` / `nn_to_kernel` 作为默认承接层，除非 `emit_c` 明确无法消费当前 lowering 结果。
- 不在本轮扩展 `group`、`depthwise`、动态 tile、bias 条件分支或多后端泛化。

## 本轮收口顺序

1. 在 [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md) 与 [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py) 明确并实现 `img2col2d`、`dma.slice/deslice/view/alloc`、tile-local compute 所需节点的 CPU 文本映射。
2. 在 [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md) 与 [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py) 固定并实现 `conv2d_img2col2d_tiled(...)` 级别的函数签名、局部 buffer、循环组织与输出写回。
3. 只有当 `emit_c` 明确无法直接消费现有 `func.func` 形态时，才新增中间 pass 任务；否则默认直接走当前 lowering 结果到 CPU emitter。
4. 在 `emit_c/gen_kernel` 收口后，再补 compile/run smoke，验证至少一个最小静态 case 能编译并产出正确结果。

## 管理员执行口径

- 当前分发重点必须落在 `emit_c/gen_kernel`；不要再把资源投回 `img2col1d/img2col2d` 的上游合同。
- 若执行者在没有证明 `emit_c` 无法消费当前 IR 的情况下要求先建 pass，应直接退回；先把现有 lowering 终点吃透。
- 任何试图新增 CPU 专用旁路文件、绕开现有 `emit_c/gen_kernel` 主链的做法，都不属于本计划允许范围。

## 本轮验收口径

- 上游基线继续保持通过：

```bash
PYTHONPATH=. pytest -q test/operation/test_operation_nn.py -k 'img2col1d or img2col2d'
pytest -q test/dialect/test_nn_dialect.py -k 'img2col1d or img2col2d'
pytest -q test/dsl/test_emit_mlir.py -k 'img2col1d or img2col2d'
pytest -q test/dsl/test_mlir_gen.py -k 'img2col'
PYTHONPATH=. pytest -q test/include/cpu/test_nn.py -k 'img2col1d or img2col2d'
```

预期：全部退出码为 `0`。

- 新增 `emit_c/gen_kernel` 断言后，生成源码必须可机械命中以下关键片段：
  - `cpu::img2col2d(`
  - 固定 tile 常量 `1/16/16/16/16`
  - tile-local pack 或等价命名的局部 buffer
  - `for` 循环组织
  - 输出写回 `out`

- 至少一个 compile/run smoke 用例必须满足：
  - 输入为静态 shape 的 `conv2d_img2col2d_tiled(...)`
  - 生成源码可编译
  - 运行结果与参考实现一致

## 当前最直接的下一步

- 先在 [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py) 明确并补齐 `img2col2d + DMA + tiled compute` 需要的节点级映射；这是当前离最终 CPU 代码生成最近的硬断点。
