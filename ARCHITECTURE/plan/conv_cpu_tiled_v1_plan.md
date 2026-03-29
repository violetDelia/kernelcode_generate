# conv_cpu_tiled_v1_plan.md

## 功能简介

- 定义第一版 `for-loop + img2col2d + tiled compute -> CPU C/C++` 的可执行推进计划。
- 明确本专题的最终目标、当前真实断点、推荐落点、任务拆分、依赖顺序与验收标准。
- 本文档不是产品长期 `spec` 的替代物；它负责把 `conv cpu tiled v1` 这条链路收敛成管理者可以直接分发的执行计划。
- 本文档坚持一个硬原则：除最终 `emit_c/gen_kernel -> cpu` 与 `include/cpu` 运行时接口之外，前面的 `operation`、`dialect`、DSL 前端、MLIR 发射与中间表示都应尽量保持通用。

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`大闸蟹`
- `文档`：[`ARCHITECTURE/plan/conv_cpu_tiled_v1_plan.md`](../../ARCHITECTURE/plan/conv_cpu_tiled_v1_plan.md)
- `功能实现`：
  - [`kernel_gen/operation/nn.py`](../../kernel_gen/operation/nn.py)
  - [`kernel_gen/dsl/ast.py`](../../kernel_gen/dsl/ast.py)
  - [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py)
  - [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py)
  - [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py)
  - [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)
  - [`include/cpu/Memory.h`](../../include/cpu/Memory.h)
  - [`include/cpu/Nn.h`](../../include/cpu/Nn.h)
- `test`：
  - [`test/operation/test_operation_nn.py`](../../test/operation/test_operation_nn.py)
  - [`test/dsl/test_ast.py`](../../test/dsl/test_ast.py)
  - [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py)
  - [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py)
  - [`test/dsl/test_emit_c.py`](../../test/dsl/test_emit_c.py)
  - [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)
  - [`test/include/cpu/test_nn.py`](../../test/include/cpu/test_nn.py)

## 依赖

- 项目总览：[`ARCHITECTURE/project_architecture.md`](../../ARCHITECTURE/project_architecture.md)
- 高层卷积语义：[`spec/operation/nn.md`](../../spec/operation/nn.md)
- DSL AST：[`spec/dsl/ast.md`](../../spec/dsl/ast.md)
- NN dialect：[`spec/dialect/nn.md`](../../spec/dialect/nn.md)
- DSL 到 MLIR：[`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)、[`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
- DSL 到 CPU 代码：[`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md)、[`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
- 当前 pass / dialect 边界：[`spec/pass/lowering/nn_to_kernel.md`](../../spec/pass/lowering/nn_to_kernel.md)、[`spec/dialect/kernel.md`](../../spec/dialect/kernel.md)
- CPU 运行时接口：[`spec/include/cpu/cpu.md`](../../spec/include/cpu/cpu.md)

## 最终目的

- 用户写的是 `Memory + operation API + Python for-loop` 风格的 DSL。
- 用户在 DSL 中表达的是 `img2col2d + tiled compute` 的算法形态，而不是黑盒 `conv(...)`。
- 仓库把这段 DSL 先转成通用 AST / 通用 `nn dialect` / 通用中间 op，必要时允许插入显式优化或 lowering pass，再由最终 `include/cpu + emit_c/gen_kernel` 负责生成 CPU C/C++ 源码。
- 生成的 CPU 代码必须体现以下固定实现策略，而不是退化成简单标量模板：
  - 输入：`NCHW * FCHW`
  - 输出：`[N, F, Ho, Wo]`
  - `Ntile = 1`
  - `Ctile = 16`
  - `Ftile = 16`
  - `Hotile = 16`
  - `Wotile = 16`
  - 逻辑按 `img2col2d` 思路计算
  - 物理实现采用 tile-local pack 与 tiled CPU compute

## 为什么这样做

- 用户已经明确约束了架构方向：除了最终 `emit_c -> cpu` 之外，其他层都不应为了 `conv` 新开一条一次性旁路。
- 当前仓库虽然有笼统 `conv/img2col` 语义，但没有一条现成的“高层 `conv` 自然落到 CPU 代码”的主链路。
- 如果继续走“新增 `conv_cpu_codegen.py` 或 `kernel_gen/codegen/cpu/nn.py` 专用后端文件”的路线，短期看似快，长期会把本应沉淀成通用 DSL / lowering / emit 规则的能力压成旁路实现。
- 因此本计划改为：
  - `operation` 层继续承载高层语义起点
  - `nn dialect` 承接 `img2col1d/img2col2d` 的通用 IR 表达
  - `dsl/ast -> emit_mlir/mlir_gen` 负责把用户写法 lower 到通用 `nn dialect`
  - 如有必要，在 `nn dialect` 与 CPU emitter 之间插入显式优化或 lowering pass
  - `include/cpu + emit_c/gen_kernel` 作为 CPU 后端完成最终源码生成
- 这条路径更符合项目长期形态，也满足“先做出能串通的一版”的现实目标。

## 核心决定

1. 不新增按单一算子命名的产品模块，例如 `conv_cpu_codegen.py`。
2. 不新增只服务本专题的 `kernel_gen/codegen/cpu/nn.py` 旁路主链作为 v1 正式方案。
3. 笼统 `img2col` 不能继续作为公开能力名扩张，必须拆成 `img2col1d` 与 `img2col2d`；其中本计划的端到端主线只绑定 `img2col2d`。首版链路至少要覆盖：
   - `operation`：[`spec/operation/nn.md`](../../spec/operation/nn.md)
   - `nn dialect`：[`spec/dialect/nn.md`](../../spec/dialect/nn.md)
   - DSL 语法与 lowering：[`spec/dsl/ast.md`](../../spec/dsl/ast.md)、[`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)、[`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
   - CPU 接口：[`spec/include/cpu/cpu.md`](../../spec/include/cpu/cpu.md)
   - CPU 代码生成：[`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md)、[`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
4. 新增公开命名固定为：
   - `img2col1d(value[N,C,W], kw, sw, dw, pl, pr) -> [N, C*Kw, Wo]`
   - `img2col2d(value[N,C,H,W], kh, kw, sh, sw, dh, dw, ph, pw, pl, pr) -> [N, C*Kh*Kw, Ho*Wo]`
   - 不再新增或扩展笼统 `img2col(...)` 公开契约。
5. 当前 `nn_to_kernel` / `kernel dialect` 仍然不是默认主链；除非后续有单独规格任务明确放行，否则首版不得把 `img2col1d/img2col2d/conv` 强塞进这条链。
6. 若在 `nn dialect` 与 CPU emitter 之间引入优化或 lowering pass，必须把该 pass 作为显式公共契约单独立项，不能藏在实现细节里。
7. 当前 `emit_c` 与 `include/cpu` 是 CPU 专项阶段，因此允许它们承接 `nn.img2col2d` 与 tiled compute 的最终落地；这不视为架构越界。
8. 对 `img2col1d/img2col2d` 这类新增公共能力，默认推进顺序固定为：
   - 上游 `operation` 先定义高层 op 语义
   - `dialect` 再定义稳定 IR 表达
   - DSL 前端再补用户写法与节点级 lowering
   - `build_func_op(...)` / 函数级 lowering 再把整函数串到 `func.func`
   - 若上游 IR 不能被 CPU emitter 直接稳定消费，再显式增加中间优化 pass
   - `include/cpu` 再提供对应公开接口
   - 最后由 `emit_c/gen_kernel` 落成 C/C++ 源码
   - 不允许跳层承诺，也不允许先做末端旁路再倒推上游契约
9. 本计划只把 `img2col2d` 串到最终 CPU tiled codegen；`img2col1d` 需要在上游公开命名、方言和 DSL 契约中一起补齐，但不占用本计划的最终 compile/run 验收口径。

## 当前实现盘点

### 已具备

- [`kernel_gen/operation/nn.py`](../../kernel_gen/operation/nn.py) 已定义 `conv` 与笼统 `img2col` 的高层语义、输入校验、输出形状与错误边界；这是当前存量实现现状，不代表后续仍允许继续扩展该笼统公开名。
- [`test/operation/test_operation_nn.py`](../../test/operation/test_operation_nn.py) 已覆盖 `conv` / 笼统 `img2col` 的主要语义测试；后续任务需要把这条测试口径同步拆分到 `img2col1d` / `img2col2d`。
- [`kernel_gen/dsl/ast.py`](../../kernel_gen/dsl/ast.py) 已支持一部分 `nn` 二元运算、`dma` helper 与循环语法解析。
- [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py) 已能发射 `dma.alloc/slice/reshape/deslice` 与部分 `nn` 二元 op。
- [`kernel_gen/dialect/nn.py`](../../kernel_gen/dialect/nn.py) 已有稳定 `nn dialect` 基础设施，但当前公开 op 集不含 `nn.img2col1d` / `nn.img2col2d`。
- [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py) + [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py) 已具备受控子集的 CPU 代码生成能力。
- [`include/cpu/Memory.h`](../../include/cpu/Memory.h) 与 [`include/cpu/Nn.h`](../../include/cpu/Nn.h) 已提供 CPU 运行时基础接口。

### 缺失且阻塞

- DSL 语法层还不能承接目标样例中的关键写法：
  - `tensor.get_shape()[axis]` / `tensor.get_stride()[axis]` 规范已写入 [`spec/dsl/ast.md`](../../spec/dsl/ast.md)，但当前实现未真正打通。
  - `nn.img2col1d(...)` / `nn.img2col2d(...)` 当前未进入 DSL 解析与 lowering 公共契约。
  - 局部 `FunctionDef` 与通用 `if` 当前不进入 v1 DSL 公共契约；目标样例必须收敛为单个顶层函数与固定无条件路径。
- DSL 到 MLIR 层缺少 `nn.img2col1d` / `nn.img2col2d` 的通用发射与端到端测试映射。
- `nn dialect` 当前没有 `nn.img2col1d` / `nn.img2col2d` 的公开表达与 verifier 契约。
- `build_func_op(...)` 当前没有把 `img2col1d` / `img2col2d` 作为稳定 lowering 终点串到 `func.func`。
- CPU include 层当前没有 `cpu::img2col1d(...)` / `cpu::img2col2d(...)` 公开接口。
- CPU emitter 当前支持范围过窄，无法把下面这些通用 op 真正落成 CPU 代码：
  - `dma.alloc`
  - `dma.slice`
  - `dma.reshape`
  - `dma.deslice`
  - `nn.img2col2d`
  - `nn` memory 级乘加组合与对应的 tail 结构
- 若需要在 `nn dialect` 与 CPU emitter 之间做 tile 化、pack 规约或别的优化，当前仓库也没有相应 pass 契约。
- `nn_to_kernel` / `kernel dialect` 不覆盖 `conv/img2col1d/img2col2d`，因此它们不是本计划的默认承接层。

### 结论

- v1 真正的阻塞，不是单点语法支持，而是 `operation -> nn dialect -> build_func_op/lowering -> 可选 pass -> cpu api -> emit_c/gen_kernel` 这条链没有对齐。
- 要跑通 `conv2d_img2col2d_tiled(...)`，必须优先把这条公共能力链补齐，而不是再造一个 `conv` 专用 codegen 旁路文件。

## 范围与边界

### v1 目标范围

- 只支持二维 `conv`。
- `value`：`[N, C, H, W]`。
- `weight`：`[F, C, Kh, Kw]`。
- 输出：`[N, F, Ho, Wo]`。
- 只支持静态整数 `stride/dilation/pad`。
- 只支持连续布局与 `Norm` 格式。
- CPU 为唯一目标后端。
- 固定 tile：`Ntile=1`、`Ctile=16`、`Ftile=16`、`Hotile=16`、`Wotile=16`。
- 必须有 tail 处理。

### v1 非目标

- 不在 v1 中修改 [`spec/pass/lowering/nn_to_kernel.md`](../../spec/pass/lowering/nn_to_kernel.md) 或 [`kernel_gen/passes/lowering/nn_to_kernel.py`](../../kernel_gen/passes/lowering/nn_to_kernel.py) 以支持 `conv/img2col1d/img2col2d`。
- 不在 v1 中修改 [`spec/dialect/kernel.md`](../../spec/dialect/kernel.md) 或 [`kernel_gen/dialect/kernel.py`](../../kernel_gen/dialect/kernel.py) 去定义 `conv/img2col1d/img2col2d`。
- 不在 v1 中支持 `group` / `depthwise` / 动态 shape / `SymbolDim` 驱动 tile / 非 `NCHW` / 非 `FCHW` / 非连续 stride / 隐式转置。
- 不在 v1 中把“全局 `img2col2d` 大 buffer 物化”定义为必须公开契约。
- 不在 v1 中追求向量化、寄存器 blocking 或多目标泛化。
- 不在 v1 中默许“优化 pass 是否存在”处于隐含状态；若确实需要 pass，必须单独立 `spec`。

### v1 语法收敛

- v1 目标样例只允许单个顶层 `func`；不支持局部嵌套 helper 函数或局部 `FunctionDef`。
- v1 目标样例不支持 `if bias is not None` 这类条件分支；首版统一收敛为固定无条件路径。
- 本文档样例锁定为无 `bias` 路径；若后续要补 `bias`，需要以独立固定路径扩展，不能先引入条件语法。
- `tensor.get_shape()[axis]` / `tensor.get_stride()[axis]` 作为通用 DSL 元信息访问，属于 v1 阻塞项，因为这直接影响用户可写性。

## 用户 DSL 目标形态

- 这部分定义的是“产品应该支持的用户写法”，不是“当前仓库已经支持到哪里”。
- 用户入口参数是 `Memory`。
- 用户使用的是 `kernel_gen.operation.*` 中的操作与 Python 原生 `for`。
- 用户显式表达 `img2col2d + tiled compute`，而不是写黑盒 `conv(...)`。
- backend 负责把通用写法转成 CPU tile 代码，用户不手写裸指针偏移。
- v1 样例固定为单个顶层 `func`，不包含局部 `FunctionDef`，也不包含 `if bias is not None`。

```python
from kernel_gen.operation.dma import alloc, deslice, reshape, slice
from kernel_gen.operation.nn import img2col2d
from kernel_gen.operation.scf import loop

NTILE = 1
CTILE = 16
FTILE = 16
HOTILE = 16
WOTILE = 16


def conv2d_img2col2d_tiled(value, weight, stride=(1, 1), dilation=(1, 1), pad=(0, 0, 0, 0)):
    N = value.get_shape()[0]
    C = value.get_shape()[1]
    H = value.get_shape()[2]
    W = value.get_shape()[3]
    F = weight.get_shape()[0]
    Kh = weight.get_shape()[2]
    Kw = weight.get_shape()[3]

    sh, sw = stride
    dh, dw = dilation
    ph, pw, pl, pr = pad

    Ho = (H + ph + pw - dh * (Kh - 1) - 1) // sh + 1
    Wo = (W + pl + pr - dw * (Kw - 1) - 1) // sw + 1

    out = alloc([N, F, Ho, Wo], value.dtype, value.space)

    for n0 in loop(0, N, NTILE):
        for f0 in loop(0, F, FTILE):
            for ho0 in loop(0, Ho, HOTILE):
                for wo0 in loop(0, Wo, WOTILE):
                    acc = alloc([NTILE, FTILE, HOTILE, WOTILE], value.dtype, value.space)
                    for c0 in loop(0, C, CTILE):
                        col_tile = img2col2d(
                            slice(value, [n0, c0, ho0, wo0], [NTILE, CTILE, HOTILE, WOTILE], [1, 1, 1, 1], value.space),
                            kh=Kh,
                            kw=Kw,
                            sh=sh,
                            sw=sw,
                            dh=dh,
                            dw=dw,
                            ph=ph,
                            pw=pw,
                            pl=pl,
                            pr=pr,
                        )
                        # 后续是 tile-local pack 与 tiled accumulate，
                        # 由通用 lowering + CPU emit 负责落成目标代码。
                    deslice(acc, out, [n0, f0, ho0, wo0], [NTILE, FTILE, HOTILE, WOTILE], [1, 1, 1, 1])
    return out
```

## 中间契约

### 高层语义契约

- `conv/img2col1d/img2col2d` 的输入合法性、输出 shape、dtype/space 一致性继续由 [`spec/operation/nn.md`](../../spec/operation/nn.md) + [`kernel_gen/operation/nn.py`](../../kernel_gen/operation/nn.py) 负责。
- 这里不下沉 tile 常量、CPU-only 策略或源码模板细节。

### DSL / MLIR 契约

- DSL 应能表达：
  - `Memory.get_shape()[axis]`
  - `Memory.get_stride()[axis]`
  - `dma.alloc/slice/reshape/deslice`
  - `nn.img2col1d`
  - `nn.img2col2d`
  - Python `for` / `loop(...)`
- DSL 到 MLIR 层产生的是通用 op，不应提前夹带 CPU 专项模板。

### Dialect / Pass 契约

- `img2col1d/img2col2d` 必须在 `nn dialect` 中有稳定公开表达，便于 `build_func_op(...)` lowering 的终点可被观察、验证和后续 pass 复用。
- 若要在最终 CPU 生成前做 tile 化、pack 重排或别的结构优化，必须通过显式 pass 承接；pass 的输入、输出和不变量都要有独立 `spec`。
- `kernel dialect` 与 `nn_to_kernel` 不作为本专题默认承接层，除非后续另开规格任务。

### CPU API 契约

- `include/cpu` 必须提供 `img2col1d/img2col2d` 的公开接口，使最终 C/C++ 源码有稳定调用目标，而不是把所有细节都硬编码在 emitter 字符串模板里。
- CPU runtime 的定位是叶子层实现，不承担 DSL、MLIR、dialect 或 pass 解释职责。
- CPU runtime 允许依赖的内容只包括：`cpu::Memory`、普通标量参数，以及本层可直接检查的运行时条件，例如 rank 检查、输出 shape 公式检查与 stride 一致性检查。
- CPU runtime 不允许依赖 AST 节点类型、`nn dialect` 运行时类型、`build_func_op(...)` 结构、pass 名称或 pass 内部不变量。
- 依赖方向必须固定为：`emit_c/gen_kernel -> cpu api`，而不是 `cpu api -> DSL/MLIR/dialect/pass`。
- `emit_c/gen_kernel` 负责决定何时调用 CPU `img2col2d` 接口，以及如何与 tiled compute 结构拼装成最终函数。

### CPU emit 契约

- `emit_c/gen_kernel` 负责把上述通用 op 落成 CPU C/C++。
- CPU emitter 需要显式体现：
  - 固定 tile 常量
  - `Ctile=16` 推导出的逻辑收缩宽度
  - tile-local pack
  - 累加主体
  - tail 处理
  - 写回 `out[N, F, Ho, Wo]`
- 这里允许 CPU 专项实现细节出现，因为这是最终后端阶段。

## 关键口径

- 不再使用旧口径 `Ktile=16`。
- v1 固定的是 `Ctile=16`。
- 逻辑收缩维仍是 `K = C * Kh * Kw`。
- 当前 tile 的 pack 宽度应按 `current_ctile * Kh * Kw` 推导。
- 计划、测试、生成代码注释都必须统一使用这套口径，避免把错误的 `Ktile=16` 承诺写进对外文本。

## 禁改范围

- [`spec/pass/lowering/nn_to_kernel.md`](../../spec/pass/lowering/nn_to_kernel.md)
- [`kernel_gen/passes/lowering/nn_to_kernel.py`](../../kernel_gen/passes/lowering/nn_to_kernel.py)
- [`spec/dialect/kernel.md`](../../spec/dialect/kernel.md)
- [`kernel_gen/dialect/kernel.py`](../../kernel_gen/dialect/kernel.py)

## 推荐落点

### 规格落点

- [`spec/operation/nn.md`](../../spec/operation/nn.md)：冻结 `img2col1d/img2col2d` 的上游公开语义，作为整条链的高层语义锚点。
- [`spec/dialect/nn.md`](../../spec/dialect/nn.md)：冻结 `nn.img2col1d/nn.img2col2d` 的公开 IR 表达与 verifier。
- [`spec/dsl/ast.md`](../../spec/dsl/ast.md)：冻结用户 DSL 中 `img2col1d/img2col2d`、`get_shape/get_stride`、单顶层函数与固定无条件路径边界。
- [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)：冻结 AST 到 `nn.img2col1d/nn.img2col2d` / DMA / loop 的发射规则。
- [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)：冻结 `build_func_op(...)` 对 `img2col2d` 主线函数的集成 lowering 规则，并注明 `img2col1d` 为同名族能力。
- [`spec/include/cpu/cpu.md`](../../spec/include/cpu/cpu.md)：冻结 `cpu::img2col1d(...)` / `cpu::img2col2d(...)` 公开接口与 CPU 侧最小行为。
- [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md)：冻结 `nn.img2col2d` 与 tiled compute 到 CPU C/C++ 的节点级生成契约。
- 若中间需要显式优化或结构整理，再条件性新增 [`spec/pass/optimization/nn_tiling.md`](../../spec/pass/optimization/nn_tiling.md)。
- 若函数级签名/装配边界超出当前 [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)，再条件性补充该文件。

### 实现落点

- [`kernel_gen/operation/nn.py`](../../kernel_gen/operation/nn.py)
- [`kernel_gen/dialect/nn.py`](../../kernel_gen/dialect/nn.py)
- [`kernel_gen/dsl/ast.py`](../../kernel_gen/dsl/ast.py)
- [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py)
- [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py)
- [`include/cpu/Nn.h`](../../include/cpu/Nn.h)
- [`kernel_gen/dsl/emit_c.py`](../../kernel_gen/dsl/emit_c.py)
- 仅当中间优化成为公开契约时再新增 `kernel_gen/passes/optimization/nn_tiling.py`
- 仅当函数级拼装阻塞时再改 [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)

### 测试落点

- [`test/operation/test_operation_nn.py`](../../test/operation/test_operation_nn.py)
- [`test/dialect/test_nn_dialect.py`](../../test/dialect/test_nn_dialect.py)
- [`test/dsl/test_ast.py`](../../test/dsl/test_ast.py)
- [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py)
- [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py)
- 条件性新增 `test/pass/test_nn_tiling.py`
- [`test/include/cpu/test_nn.py`](../../test/include/cpu/test_nn.py)
- [`test/dsl/test_emit_c.py`](../../test/dsl/test_emit_c.py)
- 条件性使用 [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)
- 编译运行 smoke 建议新增 `test/include/cpu/test_conv_codegen.py`，避免和现有 runtime 测试互相污染

## 里程碑

### M1 计划与规格冻结

- 计划文档改成“operation -> dialect -> build_func_op/lowering -> 可选 pass -> cpu api -> emit_c/gen_kernel”方案。
- `spec/operation/nn.md`、`spec/dialect/nn.md` 收敛 `img2col1d/img2col2d` 公开契约，并明确把笼统 `img2col` 标记为历史口径、禁止继续新增或扩展。

### M2 通用 DSL 前端可表达

- AST 支持 `get_shape/get_stride` 元信息访问。
- AST 支持 `img2col1d(...)` / `img2col2d(...)`，其中当前样例函数使用 `img2col2d(...)`。
- `emit_mlir/mlir_gen` 能把样例函数发成包含 `nn.img2col2d` 的通用 IR 与 `build_func_op(...)` 结果。

### M3 中间层可优化或可直达后端

- 若需要优化，则有显式 `nn_tiling` 类 pass 契约承接 tile/pack 结构整理。
- 若不需要优化，则规格必须明确 `emit_c` 直接消费哪种 `build_func_op(...)` 输出形态。

### M4 CPU emitter 可出结构正确源码

- `include/cpu` 具备 `img2col1d` / `img2col2d` 公开接口。
- `emit_c/gen_kernel` 能输出包含固定 tile、`cpu::img2col2d(...)`、tile-local pack、累加和 tail 的 CPU 源码。
- 结构测试可以直接观察到这些关键形态。

### M5 compile/run smoke

- 至少一个最小支持 case 能编译、运行，并和参考结果一致。

### M6 审查与收口

- 完成只读审查、复审与合并建议。

## 给管理者的执行说明

1. 这是一份“给管理员分发”的计划书，不直接指定执行者姓名。
2. 本文当前只规划 `spec任务`；实现、测试、审查与合并阶段由管理员在规格冻结后另行统筹。
3. 每个任务默认只改 `1` 个文件；若确有必要，最多 `2` 个文件。
4. 同一文件同一时间只允许一个执行者持有。
5. 前置任务未通过，不得放行依赖它的后续任务。
6. 验收时只看本文档中的“完成标准”“验证命令”“验收口径”，不接受口头“差不多能用”。
7. 任何试图在 `spec` 中跳过 `operation -> dialect -> ast/emit_mlir/mlir_gen -> 可选 pass -> cpu api -> emit_c/gen_kernel` 这条链、或提前承诺局部 `FunctionDef`、通用 `if`、`bias` 条件分支、`conv` 专用主链文件的写法，都应直接判不通过。

## 最小任务原则

1. 当前计划只拆 `spec任务`；每个任务单独写成统一模板，交给管理员直接推进。
2. 每个任务默认写清：`任务类型`、`目标`、`边界`、`注意事项`、`依赖`、`可改文件`、`验证命令`、`验收标准`。
3. 同一个大文件上的多个目标要拆成串行小任务。
4. `spec` 只定义公开契约、失败边界与长期目标，不为当前实现缺口背书。
5. 本文不预拆实现/测试任务；规格冻结后，由管理员基于最终 `spec` 再组织后续阶段。

## 波次与依赖

### 波次 0：计划冻结

- 当前计划文档已冻结，不再把 `P00` 作为分发任务。

### 波次 1：公共能力先齐

- `P10`、`P11`、`P16` 允许并行推进。
- `P10` 冻结 `img2col1d/img2col2d` 的高层公开语义。
- `P11` 冻结 `nn.img2col1d/nn.img2col2d` 的方言结构骨架，但不重复冻结高层 shape/stride 公式与错误边界。
- `P16` 冻结 CPU 运行时 `img2col1d/img2col2d` 公开接口，但不反向约束 AST / MLIR / pass 结构。

### 波次 2：DSL AST 入口

- `P12` 在 `P10`、`P11`、`P16` 冻结后放行。
- 原因：用户 DSL 入口要直接复用已经冻结的公开名与公开边界，不能先于 `operation / dialect / cpu include` 自造一套词汇或样例口径。

### 波次 3：节点级 AST -> MLIR lowering

- `P13` 依赖 `P11`、`P12`。
- 原因：`emit_mlir` 既要知道 DSL 入口长什么样，也要知道 `nn.img2col1d/nn.img2col2d` 的方言目标长什么样；当前主线样例落到 `nn.img2col2d`。

### 波次 4：函数级 AST -> MLIR lowering

- `P14` 依赖 `P13`。
- 原因：`build_func_op(...)` 只能在节点级发射规则冻结后，才能稳定描述整函数的输入/输出与函数体。

### 波次 5：条件性中间 pass

- `P15` 为条件 `spec任务`，默认不启用。
- 只有当 `P17` 明确无法直接消费 `P14` 的公开 IR 形态、且需要把 tile/pack/tail 结构整理成可复用的公共优化阶段时，才允许放行 `P15`。

### 波次 6：AST -> C 的 CPU emitter

- `P17` 依赖 `P14`、`P16`；若 `P15` 启用，则额外依赖 `P15`。
- 原因：本文里的 `ast -> c` 不是新增 AST 直出 C 的旁路，而是沿现有 `ast -> emit_mlir/mlir_gen -> emit_c` 链落到 CPU C/C++；因此 `emit_c` 既要知道上游 IR 形态，也要知道最终可以调用的 CPU 公开接口。

### 波次 7：条件性函数级装配

- `P18` 为条件 `spec任务`，仅当 `P17` 已经明确触及 `gen_kernel` 的函数签名、返回风格或函数体装配边界时才启用。

### 后续阶段

- 实现、测试、审查与合并不在本文拆分。
- 管理员应以本轮冻结后的 `spec` 为唯一上游，再单独制定后续阶段任务。

## 多人并行执行建议

### 总体原则

- 当前仓库的真实阻塞不是单点文件缺失，而是公共能力链没有对齐：`operation -> dialect / cpu api -> ast -> emit_mlir -> build_func_op -> 可选 pass -> emit_c/gen_kernel`。
- 本文中的 `ast -> c`，指 AST 经 `emit_mlir/mlir_gen` 形成稳定 IR 后，再由 `emit_c` 产出 CPU C/C++；不新增独立 AST-direct-C 支线。
- 因此多人并行的关键，不是把所有 `spec` 一次性撒出去，而是只在“上游契约已经冻结、下游可以独立写清”的地方放并行。
- 这轮 `spec` 规划的最大安全并发数是 `3`；再往上拆，会落到同一文件或同一契约边界，管理员反而更难控风险。
- 并行时必须严格遵守：
  - 同一时间一个文件只允许一个执行者持有
  - 同一波次内每个任务都要以前置任务的冻结文本为唯一上游
  - 任何任务一旦试图补写别的层的契约，管理员应直接打回

### 并行排期总览

| 波次 | 可并行任务 | 最大并发 | 放行前提 | 本波完成标志 |
| --- | --- | --- | --- | --- |
| W0 | `P10`、`P11`、`P16` | 3 | 无 | `operation / dialect / cpu api` 同时就位 |
| W1 | `P12` | 1 | `P10`、`P11`、`P16` 通过 | DSL AST 入口冻结 |
| W2 | `P13` | 1 | `P11`、`P12` 通过 | AST 到 `nn.img2col1d/img2col2d` 的节点级 lowering 冻结 |
| W3 | `P14` | 1 | `P13` 通过 | `build_func_op(...)` 的整函数 lowering 冻结 |
| W4 | `P15` 判定 或 直接 `P17` | 1 | `P14` 通过 | 明确“是否需要中间 pass” |
| W5 | `P17` | 1 | `P14`、`P16` 通过；若启用 `P15` 则再依赖 `P15` | CPU emitter 公开契约冻结 |
| W6 | `P18` | 1 | `P17` 明确阻塞 | 仅补函数级装配边界 |

### 波次解释

#### W0：先把公共能力名和叶子 API 一次对齐

- 可并行放行：
  - `P10`：`spec/operation/nn.md`
  - `P11`：`spec/dialect/nn.md`
- `P16`：`spec/include/cpu/cpu.md`
- 原因：这三个文件分别冻结“高层语义名”“IR 公开名”“最终 CPU 调用名”，文件独立、边界独立、都围绕同一组 `img2col1d/img2col2d` 公开名工作，适合在管理员统一口径下并行推进。
- 这一步直接对应当前仓库最靠前的三个缺口：
  - 高层公开能力名与输入输出口径未拆干净
  - `nn dialect` 没有 `nn.img2col1d/img2col2d` 的结构骨架
  - CPU include 没有 `cpu::img2col1d/img2col2d`

#### W1：在公共能力冻结后才开放 DSL AST 入口

- 只放行 `P12`：`spec/dsl/ast.md`
- 原因：用户 DSL 是最容易“顺手再发明一套名字/样例”的层，所以必须等 `operation / dialect / cpu include` 三侧已经对齐后，再去冻结 AST 入口。
- 这一步直接对应当前仓库的 DSL 阻塞：
  - DSL 入口没有 `img2col1d/img2col2d + get_shape/get_stride`
  - 现有样例若不受控，容易误写成笼统 `img2col(...)` 或 AST-direct-C 假想路径

#### W2：收敛 AST -> MLIR 的节点级 lowering

- 只放行 `P13`。
- 原因：`emit_mlir` 同时消费 `P11` 和 `P12` 的结果，无法和它们并行。
- 如果在 `P11/P12` 还没冻结前就写 `emit_mlir`，会直接把方言字段或 DSL 语法细节写死在 lowering 文档里，后面必返工。

#### W3：收敛 AST -> MLIR 的整函数 lowering

- 只放行 `P14`。
- 原因：当前仓库另一个明确阻塞是 `build_func_op(...)` 还没有把这条函数主线串到 `func.func`。这一步必须建立在 `P13` 已经把节点级规则写实之后。

#### W4：先判定要不要中间 pass

- 这是一个决策波次，不建议并发放多个写作任务。
- 管理员先根据 `P14` 和 `P17` 的阻塞关系做一次门禁判断：
  - 若 `emit_c` 可以直接消费 `P14` 的公开 IR 形态，跳过 `P15`
  - 若 `emit_c` 无法稳定消费，才放行 `P15`
- 这一步直接对应当前仓库“若需要 tile/pack/tail 结构整理，则缺 pass 契约”的阻塞。

#### W5：冻结 CPU emitter 契约

- 放行 `P17`。
- 依赖：
  - 必须等 `P14` 通过
  - 必须等 `P16` 通过
  - 若 `P15` 被启用，还必须等 `P15` 通过
- 原因：`emit_c` 文档既要知道上游 IR 的最终形态，也要知道最终允许调用的 CPU 接口形态；当前仓库这两头都没完全对齐，所以 `P17` 不能提前。

#### W6：只在明确阻塞时补函数级装配

- `P18` 默认不开。
- 只有在 `P17` 已经清楚说明节点级生成规则，但 `gen_kernel` 在函数签名、返回方式或装配边界上仍然缺合同，才单独补这一项。

### 给管理员的分发方式

1. 第一轮同时发 `P10`、`P11`、`P16`。
2. `P10/P11/P16` 全部通过后，再发 `P12`。
3. `P11/P12` 全部通过后，再发 `P13`。
4. `P13` 通过后，再发 `P14`。
5. `P14` 通过后，先做一次门禁结论：
   - 结论A：`emit_c` 可直连，则直接发 `P17`
   - 结论B：`emit_c` 不可直连，则先发 `P15`，通过后再发 `P17`
6. `P17` 通过后，只有在函数装配仍阻塞时，才发 `P18`。

### 为什么当前并发上限是 3

- `P10/P11/P16` 是唯一一个既不改同一文件、又不会互相复写对方层级契约的三任务组合。
- `P12` 一旦开始，就在冻结 DSL AST 入口；它必须消费已经稳定的公开名与边界，不能和 `W0` 混写。
- 其他任务都在消费前一个波次的冻结文本，天然是串行门。
- 继续硬拆只会出现三种坏结果：
  - 多人同时改同一个 `md` 文件
  - 下游先写死上游本该决定的契约
  - 为了提高并发，提前把 `P15/P18` 这种条件任务常态化，导致过度设计

### 当前最适合多人并行推进的窗口

- 就当前仓库的“缺失且阻塞”来看，唯一值得开的并行窗口是：
  - `P10` + `P11` + `P16`
- 这一步先把“高层公开语义”“方言结构骨架”“CPU 公开接口”一次锁住。
- 这样做的效果是：后面的 AST、MLIR 和 CPU emitter 都只消费同一组公开名，不会在不同层各自发明 `img2col` 口径。

## 任务清单

### P10

- 任务类型：`spec任务`
- 目标：在 [`spec/operation/nn.md`](../../spec/operation/nn.md) 把笼统 `img2col` 拆成 `img2col1d` 与 `img2col2d` 两个高层公开契约，使其成为后续 dialect / lowering / CPU 后端的共同语义基准。
- 边界：只改 `spec/operation/nn.md`；不改实现和测试。
- 注意事项：这里只定义 `Memory -> Memory` 的高层语义、输出形状、dtype/space/format/stride 继承与错误边界；不得提前写入 `Ntile/Ftile/Ctile/Hotile/Wotile`、CPU-only 模板或 pass 细节。必须显式禁止继续扩展笼统 `img2col(...)` 公开名。
- 依赖：无；以当前计划文档冻结版本为准
- 可改文件：`spec/operation/nn.md`
- 示例：

```python
from kernel_gen.operation.nn import img2col1d, img2col2d

col1d = img2col1d(
    value_1d,
    kw=3,
    sw=1,
    dw=1,
    pl=1,
    pr=1,
)

col2d = img2col2d(
    value_2d,
    kh=3,
    kw=3,
    sh=1,
    sw=1,
    dh=1,
    dw=1,
    ph=1,
    pw=1,
    pl=1,
    pr=1,
)
```

- 示例说明：这个任务应明确 `img2col1d` 的输入是 rank-3 `Memory[N,C,W]`、输出是 rank-3 `Memory[N,C*Kw,Wo]`；`img2col2d` 的输入是 rank-4 `Memory[N,C,H,W]`、输出是 rank-3 `Memory[N,C*Kh*Kw,Ho*Wo]`；同时写清参数校验、输出维度公式与失败边界。
- 验证命令：无；管理者人工核对
- 验收标准：`spec/operation/nn.md` 必须能直接支撑下面这个验收测试函数；若文档无法推出同样的 `expected`，则该任务不通过。

```python
def test_operation_img2col1d_img2col2d_contract_v1():
    actual = describe_operation_contract(
        ops=["img2col1d", "img2col2d"],
    )
    expected = {
        "ops": {
            "img2col1d": {
                "value": {
                    "shape": [1, 3, 5],
                    "stride": [15, 5, 1],
                    "dtype": "f32",
                    "space": "GM",
                    "format": "Norm",
                },
                "attrs": {
                    "kw": 3,
                    "sw": 1,
                    "dw": 1,
                    "pl": 1,
                    "pr": 1,
                },
                "returns": {
                    "kind": "Memory",
                    "shape": [1, 9, 5],
                    "stride": [45, 5, 1],
                    "dtype": "f32",
                    "space": "GM",
                    "format": "Norm",
                },
                "rejects": [
                    "value-not-memory",
                    "value-rank-not-3",
                    "kw-sw-dw-not-positive-int-or-symboldim",
                    "pl-pr-negative",
                    "output-width-non-positive",
                ],
            },
            "img2col2d": {
                "value": {
                    "shape": [1, 3, 5, 5],
                    "stride": [75, 25, 5, 1],
                    "dtype": "f32",
                    "space": "GM",
                    "format": "Norm",
                },
                "attrs": {
                    "kh": 3,
                    "kw": 3,
                    "sh": 1,
                    "sw": 1,
                    "dh": 1,
                    "dw": 1,
                    "ph": 1,
                    "pw": 1,
                    "pl": 1,
                    "pr": 1,
                },
                "returns": {
                    "kind": "Memory",
                    "shape": [1, 27, 25],
                    "stride": [675, 25, 1],
                    "dtype": "f32",
                    "space": "GM",
                    "format": "Norm",
                },
                "rejects": [
                    "value-not-memory",
                    "value-rank-not-4",
                    "kh-kw-sh-sw-dh-dw-not-positive-int-or-symboldim",
                    "ph-pw-pl-pr-negative",
                    "output-height-non-positive",
                    "output-width-non-positive",
                ],
            },
        },
        "forbidden_public_names": ["img2col"],
    }
    assert actual == expected
```

### P11

- 任务类型：`spec任务`
- 目标：在 [`spec/dialect/nn.md`](../../spec/dialect/nn.md) 增加 `nn.img2col1d` 与 `nn.img2col2d` 的公开方言表达、字段与 verifier 规则。
- 边界：只改 `spec/dialect/nn.md`；不改实现和测试。
- 注意事项：这里只定义 `nn dialect` 中的稳定 IR 形态，不重复高层 `operation/nn` 语义，也不引入 CPU tile、C++ 模板或 kernel dialect。必须明确禁止继续新增 `nn.img2col` 这种笼统公开 op 名。验收时只检查“方言结构是否完整、是否越权复写高层语义”，不要求在本任务里重复冻结 `P10` 的具体 shape/stride 公式与错误边界文本。
- 依赖：无硬依赖；允许与 `P10` 并行推进
- 可改文件：`spec/dialect/nn.md`
- 示例：

```mlir
%0 = nn.img2col2d %value {
  kh = 3, kw = 3,
  sh = 1, sw = 1,
  dh = 1, dw = 1,
  ph = 1, pw = 1, pl = 1, pr = 1,
  space = #nn.space<global>
} : !nn.memory<[1, 3, 5, 5], [75, 25, 5, 1], f32, #nn.space<global>>
 -> !nn.memory<[1, 27, 25], [675, 25, 1], f32, #nn.space<global>>
```

- 示例说明：这个任务应把 `nn.img2col1d` 与 `nn.img2col2d` 定义成一组稳定的 `nn dialect` op：前者输入 rank-3 `!nn.memory` 输出 rank-3 `!nn.memory`，后者输入 rank-4 `!nn.memory` 输出 rank-3 `!nn.memory`，并明确属性、结果类型与 verifier 约束；但不在方言层重复写一份高层 `img2col1d/img2col2d` 的完整 shape/stride 公式说明。
- 验证命令：无；管理者人工核对
- 验收标准：`spec/dialect/nn.md` 必须能直接支撑下面这个验收测试函数；若文档无法推出同样的 `expected`，则该任务不通过。

```python
def test_nn_dialect_img2col1d_img2col2d_contract_v1():
    actual = describe_dialect_contract(
        ops=["nn.img2col1d", "nn.img2col2d"],
    )
    expected = {
        "ops": {
            "nn.img2col1d": {
                "operand_kind": "!nn.memory",
                "operand_rank": 3,
                "attrs": ["kw", "sw", "dw", "pl", "pr", "space"],
                "result_kind": "!nn.memory",
                "result_rank": 3,
                "verifier": [
                    "operand-must-be-rank-3-nn-memory",
                    "kw-sw-dw-must-be-positive",
                    "pl-pr-must-be-non-negative",
                    "result-rank-must-be-3",
                    "result-element-type-matches-input",
                    "result-space-matches-input",
                    "result-shape-stride-must-match-img2col1d-contract",
                ],
            },
            "nn.img2col2d": {
                "operand_kind": "!nn.memory",
                "operand_rank": 4,
                "attrs": ["kh", "kw", "sh", "sw", "dh", "dw", "ph", "pw", "pl", "pr", "space"],
                "result_kind": "!nn.memory",
                "result_rank": 3,
                "verifier": [
                    "operand-must-be-rank-4-nn-memory",
                    "kh-kw-sh-sw-dh-dw-must-be-positive",
                    "ph-pw-pl-pr-must-be-non-negative",
                    "result-rank-must-be-3",
                    "result-element-type-matches-input",
                    "result-space-matches-input",
                    "result-shape-stride-must-match-img2col2d-contract",
                ],
            },
        },
        "forbidden_scope": [
            "duplicate-operation-level-shape-formula",
            "duplicate-operation-level-error-boundary",
        ],
        "forbidden_public_names": ["nn.img2col"],
    }
    assert actual == expected
```

### P12

- 任务类型：`spec任务`
- 目标：在 [`spec/dsl/ast.md`](../../spec/dsl/ast.md) 增加 `img2col1d` / `img2col2d`、`get_shape/get_stride` 与单顶层 `for-loop` 样例的 DSL 语法支持说明。
- 边界：只改 `spec/dsl/ast.md`；不改实现和测试。
- 注意事项：这里只定义前端语法与 AST 边界；不得把 `cpu::img2col2d`、tile 模板或 pass 细节写进 AST 规格。必须明确 v1 只支持单个顶层函数，暂不承诺局部 `FunctionDef`、通用 `if`、`if bias is not None`。同时明确禁止新的 DSL 样例继续使用笼统 `img2col(...)`。
- 依赖：硬依赖为 `P10`；管理放行顺序上建议等待 `P11`、`P16` 一并冻结后再发，避免 DSL 样例先于公开名和 CPU 叶子 API 漂移
- 可改文件：`spec/dsl/ast.md`
- 示例：

```python
from kernel_gen.operation.dma import alloc, deslice, slice
from kernel_gen.operation.nn import img2col2d
from kernel_gen.operation.scf import loop


def conv2d_img2col2d_tiled(value, weight, sh, sw, ph, pw, pl, pr):
    N = value.get_shape()[0]
    C = value.get_shape()[1]
    F = weight.get_shape()[0]
    Kh = weight.get_shape()[2]
    Kw = weight.get_shape()[3]
    out = alloc([N, F, 5, 5], value.dtype, value.space)
    for n0 in loop(0, N, 1):
        for c0 in loop(0, C, 16):
            tile = img2col2d(
                slice(value, [n0, c0, 0, 0], [1, 16, 5, 5], [1, 1, 1, 1], value.space),
                kh=Kh,
                kw=Kw,
                sh=sh,
                sw=sw,
                dh=1,
                dw=1,
                ph=ph,
                pw=pw,
                pl=pl,
                pr=pr,
            )
        deslice(out, out, [n0, 0, 0, 0], [1, F, 5, 5], [1, 1, 1, 1], value.space)
    return out
```

- 示例说明：这个任务应把 `get_shape()[axis]`、`loop(...)`、`slice(...)`、`img2col1d(...)`、`img2col2d(...)` 写成可解析 DSL 语法，同时写清哪些语法不属于 v1 公开能力；当前 conv2d 样例固定使用 `img2col2d(...)`。
- 验证命令：无；管理者人工核对
- 验收标准：`spec/dsl/ast.md` 必须能直接支撑下面这个验收测试函数；若文档无法推出同样的 `expected`，则该任务不通过。

```python
def test_ast_contract_conv2d_img2col2d_tiled_v1():
    actual = normalize_ast_contract(parse_function(conv2d_img2col2d_tiled))
    expected = {
        "func_name": "conv2d_img2col2d_tiled",
        "args": [
            ("value", "Memory"),
            ("weight", "Memory"),
            ("sh", "int"),
            ("sw", "int"),
            ("ph", "int"),
            ("pw", "int"),
            ("pl", "int"),
            ("pr", "int"),
        ],
        "shape_accesses": [
            ("value", 0),
            ("value", 1),
            ("weight", 0),
            ("weight", 2),
            ("weight", 3),
        ],
        "calls": [
            "alloc",
            "loop",
            "slice",
            "img2col2d",
            "deslice",
        ],
        "supported_img2col_calls": ["img2col1d", "img2col2d"],
        "loops": ["n0", "c0"],
        "returns": "out",
        "forbidden": [
            "nested_function_def",
            "external_capture",
            "generic_if",
            "if_bias_is_not_none",
            "img2col",
        ],
    }
    assert actual == expected
```

### P13

- 任务类型：`spec任务`
- 目标：在 [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md) 增加 `img2col1d` / `img2col2d` 到 `nn.img2col1d` / `nn.img2col2d` / DMA / loop 的节点级发射规则。
- 边界：只改 `spec/dsl/emit_mlir.md`；不改实现和测试。
- 注意事项：这里只定义节点级 lowering；不得提前生成 CPU C/C++ 文本，也不得引入 kernel dialect 或 `nn_to_kernel`。
- 依赖：`P11`、`P12`
- 可改文件：`spec/dsl/emit_mlir.md`
- 示例：

```python
tile = img2col2d(
    slice(value, [n0, c0, 0, 0], [1, 16, 5, 5], [1, 1, 1, 1], value.space),
    kh=Kh,
    kw=Kw,
    sh=sh,
    sw=sw,
    dh=1,
    dw=1,
    ph=ph,
    pw=pw,
    pl=pl,
    pr=pr,
)
```

- 示例说明：这个任务应写清 `slice(...)` 如何 lowering 为 `dma.slice`，`img2col1d(...)` 如何 lowering 为 `nn.img2col1d`，`img2col2d(...)` 如何 lowering 为 `nn.img2col2d`，以及循环/返回值如何保持在通用 IR 层；不得出现 `cpu::img2col2d` 或任何 `for (...) { ... }` 的 C++ 模板。
- 验证命令：无；管理者人工核对
- 验收标准：`spec/dsl/emit_mlir.md` 必须能直接支撑下面这个验收测试函数；若文档无法推出同样的 `expected`，则该任务不通过。

```python
def test_emit_mlir_contract_img2col2d_tile_v1():
    actual = normalize_emit_mlir_contract(
        emit_mlir_function(
            "conv2d_img2col2d_tiled",
            runtime_args={
                "value": "Memory[1,3,5,5]",
                "weight": "Memory[8,3,3,3]",
                "sh": 1,
                "sw": 1,
                "ph": 1,
                "pw": 1,
                "pl": 1,
                "pr": 1,
            },
        )
    )
    expected = {
        "body_ops": [
            "dma.alloc",
            "scf.for",
            "dma.slice",
            "nn.img2col2d",
            "dma.deslice",
        ],
        "img2col_op_mapping": {
            "img2col1d": "nn.img2col1d",
            "img2col2d": "nn.img2col2d",
        },
        "img2col2d_result_type": "!nn.memory<[1, 144, 25], [3600, 25, 1], f32, #nn.space<global>>",
        "forbidden": [
            "cpu::img2col2d",
            "kernel.conv",
            "nn_to_kernel",
            "kernel_dialect",
            "nn.img2col",
        ],
    }
    assert actual == expected
```

### P14

- 任务类型：`spec任务`
- 目标：在 [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md) 为 `build_func_op(...)` 增加 `img2col2d + loop + dma helper` 的整函数 lowering 口径，并注明 `img2col1d` 属于同名族能力。
- 边界：只改 `spec/dsl/mlir_gen.md`；不改实现和测试。
- 注意事项：必须保持“只接受函数形参与函数体内可达值”的边界；不得默许外部值隐式捕获，也不得在这里引入 CPU 代码生成细节。
- 依赖：`P13`
- 可改文件：`spec/dsl/mlir_gen.md`
- 示例：

```python
def conv2d_img2col2d_tiled(value, weight, sh, sw, ph, pw, pl, pr):
    N = value.get_shape()[0]
    C = value.get_shape()[1]
    F = weight.get_shape()[0]
    Kh = weight.get_shape()[2]
    Kw = weight.get_shape()[3]
    out = alloc([N, F, 5, 5], value.dtype, value.space)
    for n0 in loop(0, N, 1):
        for c0 in loop(0, C, 16):
            tile = img2col2d(
                slice(value, [n0, c0, 0, 0], [1, 16, 5, 5], [1, 1, 1, 1], value.space),
                kh=Kh,
                kw=Kw,
                sh=sh,
                sw=sw,
                dh=1,
                dw=1,
                ph=ph,
                pw=pw,
                pl=pl,
                pr=pr,
            )
        deslice(out, out, [n0, 0, 0, 0], [1, F, 5, 5], [1, 1, 1, 1], value.space)
    return out
```

- 示例说明：这个任务应写清 `build_func_op(...)` 如何把这类单顶层函数转换成稳定 `func.func`，包括参数顺序、`Memory`/标量签名、返回值与函数体中 `nn.img2col2d` 的出现位置；同时注明 `img2col1d` 遵循同一命名族 lowering 规则。
- 验证命令：无；管理者人工核对
- 验收标准：`spec/dsl/mlir_gen.md` 必须能直接支撑下面这个验收测试函数；若文档无法推出同样的 `expected`，则该任务不通过。

```python
def test_build_func_op_contract_conv2d_img2col2d_tiled_v1():
    actual = normalize_build_func_contract(
        build_func_op(
            conv2d_img2col2d_tiled,
            "Memory[1,3,5,5]",
            "Memory[8,3,3,3]",
            1,
            1,
            1,
            1,
            1,
            1,
        )
    )
    expected = {
        "func_name": "conv2d_img2col2d_tiled",
        "args": [
            ("value", "!nn.memory<[1, 3, 5, 5], [75, 25, 5, 1], f32, #nn.space<global>>"),
            ("weight", "!nn.memory<[8, 3, 3, 3], [27, 9, 3, 1], f32, #nn.space<global>>"),
            ("sh", "!symbol.int<1>"),
            ("sw", "!symbol.int<1>"),
            ("ph", "!symbol.int<1>"),
            ("pw", "!symbol.int<1>"),
            ("pl", "!symbol.int<1>"),
            ("pr", "!symbol.int<1>"),
        ],
        "returns": ["!nn.memory<[1, 8, 5, 5], [200, 25, 5, 1], f32, #nn.space<global>>"],
        "body_contains": [
            "dma.alloc",
            "scf.for",
            "dma.slice",
            "nn.img2col2d",
            "dma.deslice",
        ],
        "img2col_family": ["img2col1d", "img2col2d"],
        "forbidden": [
            "nested_function_def",
            "external_capture",
            "generic_if",
            "nn.img2col",
        ],
    }
    assert actual == expected
```

### P15

- 任务类型：`条件spec任务`
- 目标：若 `emit_c` 无法直接消费 `build_func_op(...)` 输出形态，则新增 [`spec/pass/optimization/nn_tiling.md`](../../spec/pass/optimization/nn_tiling.md)，定义一个显式公共优化 pass 来承接 tile/pack/tail 结构整理。
- 边界：只有 `P17` 证明“没有中间 pass 就无法稳定表达 CPU tile 生成口径”时才允许启用；只改 `spec/pass/optimization/nn_tiling.md`。
- 注意事项：pass 名称和职责必须保持通用；不得把它写成 `conv` 专用旁路。v1 即便启用，也只能公开承诺当前 `img2col2d` 生产者路径，不得顺手承诺更多高阶算子。
- 依赖：`P14` 完成后，由管理员基于阻塞证据决定是否启用
- 可改文件：`spec/pass/optimization/nn_tiling.md`（新文件）
- 示例：

```mlir
%col = nn.img2col2d %tile {kh = 3, kw = 3, sh = 1, sw = 1, dh = 1, dw = 1, ph = 1, pw = 1, pl = 1, pr = 1}
  : !nn.memory<[1, 16, 5, 5], [400, 25, 5, 1], f32, #nn.space<global>>
 -> !nn.memory<[1, 144, 25], [3600, 25, 1], f32, #nn.space<global>>
```

- 示例说明：只有在中间结构整理成为公共阶段时才启用本任务；该任务要写清 pass 的输入、输出、不变量与失败边界，而不是把优化藏在 emitter 里。
- 验证命令：无；管理者人工核对
- 验收标准：`spec/pass/optimization/nn_tiling.md` 仅在阻塞证据成立后启用；文档必须能支撑下面这个验收测试函数，否则该任务不通过。

```python
def test_nn_tiling_pass_contract_v1():
    actual = normalize_pass_contract(
        pass_name="nn_tiling",
        input_ir={
            "ops": ["scf.for", "nn.img2col2d", "arith.mulf", "arith.addf"],
            "conv_output_shape": [1, 8, 5, 5],
        },
    )
    expected = {
        "pass_name": "nn_tiling",
        "output_contract": {
            "tiles": {
                "Ntile": 1,
                "Ctile": 16,
                "Ftile": 16,
                "Hotile": 16,
                "Wotile": 16,
            },
            "pack_scope": "tile-local-only",
            "tail": "explicit",
        },
        "preserves": {
            "logical_k": "C*Kh*Kw",
            "conv_output_shape": [1, 8, 5, 5],
        },
        "forbidden": [
            "kernel_dialect",
            "nn_to_kernel",
            "conv_private_codegen_path",
            "Ktile=16",
            "require-global-img2col2d-buffer",
            "nn.img2col",
        ],
    }
    assert actual == expected
```

### P16

- 任务类型：`spec任务`
- 目标：在 [`spec/include/cpu/cpu.md`](../../spec/include/cpu/cpu.md) 增加 `cpu::img2col1d(...)` 与 `cpu::img2col2d(...)` 公开接口与最小行为契约。
- 边界：只改 `spec/include/cpu/cpu.md`；不改实现和测试。
- 注意事项：这里只定义 CPU include 层的公开接口，不定义 DSL lowering，也不定义完整 conv 模板。接口应服务最终 emitter 调用，而不是反向规定上游 AST/IR 长什么样。必须显式写清 CPU runtime 只依赖 `cpu::Memory`、普通标量参数和本层运行时契约，不依赖 AST 节点类型、`nn dialect` 类型、`build_func_op(...)` 结构或 pass 名称。
- 依赖：无硬依赖；允许与 `P10`、`P11` 并行推进；验收时必须与本文固定的 `img2col1d/img2col2d` 公开名及 `P10` 最终文本保持一致
- 可改文件：`spec/include/cpu/cpu.md`
- 示例：

```cpp
cpu::img2col1d<float>(value_1d, out_1d, 3, 1, 1, 1, 1);
cpu::img2col2d<float>(value_2d, out_2d, 3, 3, 1, 1, 1, 1, 1, 1, 1, 1);
```

- 示例说明：这个任务应写清 `cpu::img2col1d(...)` 与 `cpu::img2col2d(...)` 的签名、输入 rank、输出 rank、形状关系与调用方前置条件，作为 `emit_c` 的稳定调用目标；并明确禁止继续新增 `cpu::img2col(...)` 笼统接口。
- 验证命令：无；管理者人工核对
- 验收标准：`spec/include/cpu/cpu.md` 必须能直接支撑下面这个验收测试函数；若文档无法推出同样的 `expected`，则该任务不通过。

```python
def test_cpu_img2col_api_contract_v1():
    actual = describe_cpu_api_contract(
        names=["cpu::img2col1d", "cpu::img2col2d"],
        template_type="float",
    )
    expected = {
        "apis": {
            "cpu::img2col1d": {
                "signature": "void cpu::img2col1d(const cpu::Memory<float>& value, cpu::Memory<float>& out, long long kw, long long sw, long long dw, long long pl, long long pr)",
                "depends_only_on": [
                    "cpu::Memory",
                    "long long",
                    "rank-check",
                    "shape-formula-check",
                    "stride-consistency-check",
                ],
                "value_rank": 3,
                "out_rank": 3,
                "rejects": [
                    "value-rank-not-3",
                    "out-rank-not-3",
                    "shape-stride-mismatch-with-img2col1d-formula",
                    "kw-sw-dw-not-positive",
                    "pl-pr-negative",
                ],
            },
            "cpu::img2col2d": {
                "signature": "void cpu::img2col2d(const cpu::Memory<float>& value, cpu::Memory<float>& out, long long kh, long long kw, long long sh, long long sw, long long dh, long long dw, long long ph, long long pw, long long pl, long long pr)",
                "depends_only_on": [
                    "cpu::Memory",
                    "long long",
                    "rank-check",
                    "shape-formula-check",
                    "stride-consistency-check",
                ],
                "value_rank": 4,
                "out_rank": 3,
                "rejects": [
                    "value-rank-not-4",
                    "out-rank-not-3",
                    "shape-stride-mismatch-with-img2col2d-formula",
                    "kh-kw-sh-sw-dh-dw-not-positive",
                    "ph-pw-pl-pr-negative",
                ],
            },
        },
        "forbidden_dependencies": [
            "ast-node-types",
            "nn-dialect-runtime-types",
            "build_func_op-structure",
            "pass-names",
        ],
        "forbidden_public_names": ["cpu::img2col"],
    }
    assert actual == expected
```

### P17

- 任务类型：`spec任务`
- 目标：在 [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md) 增加 `nn.img2col2d + tiled compute` 到 CPU C/C++ 的节点级生成契约。
- 边界：只改 `spec/dsl/emit_c.md`；不改实现和测试。
- 注意事项：CPU 专项细节只允许出现在最终 emitter；这里必须明确会生成固定 tile 循环、`cpu::img2col2d(...)` 调用、tile-local pack、累加与 tail。不得把 `Ktile=16` 写成公开契约，也不得回退到“简单标量乘加模板”。同时必须明确：`emit_c` 依赖的是 `P16` 冻结后的稳定 CPU API，而不是要求 CPU runtime 反向理解 `nn dialect`、AST 或 pass 内部结构。
- 依赖：`P14`、`P16`；若 `P15` 启用，则额外依赖 `P15`
- 可改文件：`spec/dsl/emit_c.md`
- 示例：

```c
for (long long n0 = 0; n0 < N; n0 += 1) {
  for (long long f0 = 0; f0 < F; f0 += 16) {
    for (long long ho0 = 0; ho0 < Ho; ho0 += 16) {
      for (long long wo0 = 0; wo0 < Wo; wo0 += 16) {
        for (long long c0 = 0; c0 < C; c0 += 16) {
          long long current_ctile = min(16, C - c0);
          long long packed_k = current_ctile * Kh * Kw;
          cpu::img2col2d(value_tile, col_tile, Kh, Kw, sh, sw, dh, dw, ph, pw, pl, pr);
        }
      }
    }
  }
}
```

- 示例说明：这个任务应把上面的结构写成“允许出现的 CPU emitter 结果形态”：固定 `Ntile=1/Ftile=16/Ctile=16/Hotile=16/Wotile=16`、`packed_k = current_ctile * Kh * Kw`、显式 tail、`cpu::img2col2d(...)` 调用与 tile-local compute；但不能反向定义上游 DSL/IR 契约。
- 验证命令：无；管理者人工核对
- 验收标准：`spec/dsl/emit_c.md` 必须能直接支撑下面这个验收测试函数；若文档无法推出同样的 `expected`，则该任务不通过。

```python
def test_emit_c_contract_conv2d_img2col2d_tiled_v1():
    actual = normalize_emit_c_contract(
        emit_c(
            func_name="conv2d_img2col2d_tiled",
            input_ir={
                "ops": ["scf.for", "dma.slice", "nn.img2col2d", "arith.mulf", "arith.addf", "dma.deslice"],
                "conv_output_shape": [1, 8, 5, 5],
            },
            target="cpu",
        )
    )
    expected = {
        "output_kind": "cpu-cpp-function-text",
        "target": "cpu",
        "tiles": {
            "Ntile": 1,
            "Ctile": 16,
            "Ftile": 16,
            "Hotile": 16,
            "Wotile": 16,
        },
        "contains": [
            "cpu::img2col2d(",
            "for-n0-step-1",
            "for-f0-step-16",
            "for-ho0-step-16",
            "for-wo0-step-16",
            "for-c0-step-16",
            "packed_k = current_ctile * Kh * Kw",
            "tile-local-pack-buffer",
            "tail-handling",
            "writeback-to-out-N-F-Ho-Wo",
        ],
        "forbidden": [
            "scalar-only-conv-template",
            "Ktile=16",
            "kernel_dialect",
            "nn_to_kernel",
            "cpu::img2col(",
            "nn.img2col",
        ],
    }
    assert actual == expected
```

### P18

- 任务类型：`条件spec任务`
- 目标：若 [`spec/dsl/emit_c.md`](../../spec/dsl/emit_c.md) 已明确触及完整函数签名、返回风格或函数体装配边界，则在 [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md) 增加最小补充说明。
- 边界：只有 `P17` 明确阻塞时才允许启用；只改 `spec/dsl/gen_kernel.md`。
- 注意事项：这里只补函数级装配契约，不重复 `emit_c` 的 op 级规则，不定义新的 `img2col1d/img2col2d` 语义，也不新增高层 lowering 承诺。
- 依赖：`P17` 阻塞
- 可改文件：`spec/dsl/gen_kernel.md`
- 示例：

```c
void conv2d_img2col2d_tiled(
    const Memory& value,
    const Memory& weight,
    long long sh,
    long long sw,
    long long ph,
    long long pw,
    long long pl,
    long long pr,
    Memory& out);
```

- 示例说明：只有当 `emit_c` 已经稳定输出节点级片段，但 `gen_kernel` 仍缺少函数签名/出参拼装规则时，才启用本任务。
- 验证命令：无；管理者人工核对
- 验收标准：`spec/dsl/gen_kernel.md` 仅在 `P17` 阻塞时补充下面这个验收测试函数；若文档无法推出同样的 `expected`，则该任务不通过。

```python
def test_gen_kernel_contract_conv2d_img2col2d_tiled_v1():
    actual = normalize_gen_kernel_contract(
        gen_kernel(
            function_name="conv2d_img2col2d_tiled",
            function_args=[
                ("value", "Memory"),
                ("weight", "Memory"),
                ("sh", "long long"),
                ("sw", "long long"),
                ("ph", "long long"),
                ("pw", "long long"),
                ("pl", "long long"),
                ("pr", "long long"),
            ],
            function_body="cpu-cpp-statements",
            result_style="memory-out-param",
        )
    )
    expected = {
        "function_name": "conv2d_img2col2d_tiled",
        "args": [
            ("value", "Memory"),
            ("weight", "Memory"),
            ("sh", "long long"),
            ("sw", "long long"),
            ("ph", "long long"),
            ("pw", "long long"),
            ("pl", "long long"),
            ("pr", "long long"),
        ],
        "result_style": "memory-out-param",
        "body_role": "cpu-cpp-statements",
        "output_kind": "complete-cpp-kernel-function",
        "forbidden": [
            "redefine-img2col1d-img2col2d-semantics",
            "redefine-tile-semantics",
            "redefine-tail-semantics",
        ],
    }
    assert actual == expected
```

## 共通验收规则

1. `spec任务` 只定义“应该支持什么”和“必须拒绝什么”，不为当前实现缺口背书。
2. 每个 `spec任务` 默认只改 `1` 个 `md` 文件；若超出 `1` 个文件，应退回给管理员重新拆分。
3. 每个任务都必须对应一个可直接核对的验收测试函数；验收结果必须以显式 `expected = {...}` 形式写清输入和输出，不能只写口头目标。
4. 下游 `spec` 不得替上游补契约；例如 `emit_c.md` 不能反向定义 `operation/nn.md`、`dialect/nn.md` 或 `mlir_gen.md` 应该先支持什么。
5. `条件spec任务` 必须先有明确阻塞证据，再由管理员放行。
6. 若引入中间优化 pass，必须单独立项并定义输入/输出/不变量，不能把 pass 行为藏进 `emit_c` 或 `gen_kernel`。
7. 任何 `spec` 一旦出现新开 `conv` 专用主链文件、误接 `nn_to_kernel/kernel dialect`、把局部 `FunctionDef` / 通用 `if` / `bias` 条件分支写成 v1 已承诺能力、继续扩展笼统 `img2col` 公共名、删 tail、或把 `Ktile=16` 写成公开契约，直接判不通过。

## 推荐验证命令

- 规格差异总览：

```bash
git diff -- spec/operation/nn.md spec/dialect/nn.md spec/dsl/ast.md spec/dsl/emit_mlir.md spec/dsl/mlir_gen.md spec/include/cpu/cpu.md spec/dsl/emit_c.md spec/dsl/gen_kernel.md
git diff -- spec/pass/optimization/nn_tiling.md 2>/dev/null || true
```

- 关键术语一致性：

```bash
rg -n "img2col\\b|img2col1d|img2col2d|nn.img2col\\b|nn.img2col1d|nn.img2col2d|cpu::img2col\\b|cpu::img2col1d|cpu::img2col2d|get_shape|get_stride|FunctionDef|if bias is not None|tail|Ntile|Ctile|Ftile|Hotile|Wotile|Ktile|nn_to_kernel|kernel dialect|build_func_op" \
  spec/operation/nn.md spec/dialect/nn.md spec/dsl/ast.md spec/dsl/emit_mlir.md spec/dsl/mlir_gen.md spec/include/cpu/cpu.md spec/dsl/emit_c.md spec/dsl/gen_kernel.md spec/pass/optimization/nn_tiling.md 2>/dev/null
```

- 与计划文档边界核对：

```bash
rg -n "operation|dialect|build_func_op|pass|cpu api|emit_c|单个顶层|固定无条件路径|img2col\\b|img2col1d|img2col2d|tile|tail|禁改范围" \
  ARCHITECTURE/plan/conv_cpu_tiled_v1_plan.md \
  spec/operation/nn.md spec/dialect/nn.md spec/dsl/ast.md spec/dsl/emit_mlir.md spec/dsl/mlir_gen.md spec/include/cpu/cpu.md spec/dsl/emit_c.md spec/dsl/gen_kernel.md spec/pass/optimization/nn_tiling.md 2>/dev/null
```

## 风险与回退

### 风险 1：又绕回 `conv` 专用主链文件

- 表现：新增 `conv_cpu_codegen.py`、`kernel_gen/codegen/cpu/nn.py` 之类旁路主链。
- 回退：直接退回，要求回到现有 `operation -> dialect -> lowering -> cpu api -> emit` 分层。

### 风险 2：跳过 `dialect` 或 `cpu api`，直接从 DSL 生 C++

- 表现：规格里出现“AST/emit_mlir 直接承诺 C++ 细节”或“emit_c 直接吞高层 `img2col2d` 语义而不经过稳定 IR / CPU 接口”。
- 回退：退回到相应 `spec` 任务，补齐缺失层级后再继续。

### 风险 3：把 `Ktile=16` 写成错误公开契约

- 表现：规格、测试或代码注释里出现固定 `Ktile=16`。
- 回退：统一改回 `Ctile=16` 与 `current_ctile * Kh * Kw` 口径。

### 风险 4：为缩 scope 把 tail 删掉

- 表现：只支持整齐 tile。
- 回退：判定当前阶段不通过；tail 是 v1 硬要求。

### 风险 5：把优化 pass 藏成实现细节

- 表现：实现依赖中间 tile/pack 重排，但规格里没有对应 pass 合同。
- 回退：要么补 `P15`，要么回到“`emit_c` 可直接消费上游 IR”的公开口径。

### 风险 6：`spec` 被当前实现牵着走

- 表现：出现“当前不支持所以长期不支持”的收缩写法，或把 `img2col1d/img2col2d` 只写成当前实现里已有的最小临时行为。
- 回退：退回到对应 `spec` 任务，按公开目标行为与失败边界重写。

## 后续扩展方向

- 在 v1 稳定后，再评估：
  - 通用 `if bias is not None` 语法支持
  - 局部 helper / 嵌套函数的 DSL 能力
  - 更广 layout / space
  - `group/depthwise`
  - 向量化与更激进优化
  - 是否需要把一部分稳定能力沉淀成 `expectation` 质量基线
- 这些都属于 v1 之后的增量，不得反向污染当前最小闭环。

## 当前结论

1. 这条链路的正确 v1 方案，不是新开 `conv` 专用后端文件，而是把笼统 `img2col` 拆成 `img2col1d/img2col2d` 两个跨层公共能力，再以 `img2col2d` 串起当前 `conv2d` 主线：`operation -> dialect -> build_func_op/lowering -> 可选 pass -> cpu api -> emit_c/gen_kernel`；旧的笼统 `img2col` 只允许作为存量现状和禁用名出现，不再作为新增公共契约推进。
2. 除最终 `include/cpu` 与 `emit_c/gen_kernel` 外，其余层都应保持通用；`conv` 的特殊性只体现在最终 CPU 代码形态和固定 tile 策略上，而不是回退成笼统 `img2col` 或专用旁路文件。
3. 本文档已经把任务拆到管理者可直接分发的粒度：每个任务只对应一个 `spec` 文件、一个清晰目标、一个明确边界、一个示例和一个可直接核对的验收测试函数。
