# multi_buffer.md

## 功能简介

- 定义 multi-buffer pass family 的公开合同。
- `multi-buffer-analysis` 只分析可证明的 loop staging / scratch `dma.alloc/free` 生命周期，给控制流写入稳定 analysis id，并在原 `dma.alloc` 上写三项临时属性。
- `multi-buffer-apply` 只消费三项临时属性，把对应 typed alloc/free 生命周期改写为 DMA ring，并删除临时属性。
- `multi-buffer` 保留旧公开入口，外部行为等价于 analysis 后接 apply。
- 本 family 不插入 `arch.sign` / `arch.wait`，不做 core split，不处理任意 alias、跨 region control flow 或已有 ring 再 ring。

## API 列表

- `class MultiBufferAnalysisPass(memory_stage: int = 2, fold: bool = True, target: str | None = None)`
- `MultiBufferAnalysisPass.from_options(options: dict[str, str]) -> MultiBufferAnalysisPass`
- `MultiBufferAnalysisPass.apply(ctx: Context, module: ModuleOp) -> None`
- `class MultiBufferApplyPass(fold: bool = True, target: str | None = None, alignment: int = 1024)`
- `MultiBufferApplyPass.from_options(options: dict[str, str]) -> MultiBufferApplyPass`
- `MultiBufferApplyPass.apply(ctx: Context, module: ModuleOp) -> None`
- `class MultiBufferPass(memory_stage: int = 2, fold: bool = True, target: str | None = None, alignment: int = 1024)`
- `MultiBufferPass.from_options(options: dict[str, str]) -> MultiBufferPass`
- `MultiBufferPass.apply(ctx: Context, module: ModuleOp) -> None`

## 文档信息

- `spec`：[`spec/pass/memory/multi_buffer.md`](multi_buffer.md)
- `功能实现`：[`kernel_gen/passes/memory/multi_buffer.py`](../../../kernel_gen/passes/memory/multi_buffer.py)
- `test`：[`test/passes/memory/test_multi_buffer.py`](../../../test/passes/memory/test_multi_buffer.py)

## 公开入口

- canonical path：`kernel_gen.passes.memory.multi_buffer`
- package re-export：
  - `from kernel_gen.passes.memory import MultiBufferAnalysisPass, MultiBufferApplyPass, MultiBufferPass`
  - `from kernel_gen.passes import MultiBufferAnalysisPass, MultiBufferApplyPass, MultiBufferPass`
- compat module：`kernel_gen.passes.multi_buffer`
- registry pass name：
  - `multi-buffer-analysis`
  - `multi-buffer-apply`
  - `multi-buffer`

## 依赖

- DMA ring type/op：[`spec/dialect/dma.md`](../../dialect/dma.md)
- Kernel matmul op：[`spec/dialect/kernel.md`](../../dialect/kernel.md)
- Symbol loop/op：[`spec/dialect/symbol.md`](../../dialect/symbol.md)
- pass registry：[`spec/pass/registry.md`](../registry.md)
- npu-demo-lowering pipeline：[`spec/pass/pipeline/npu_demo_lowering.md`](../pipeline/npu_demo_lowering.md)

## Options

- `MultiBufferAnalysisPass`：
  - `memory_stage` 必须为正整数；`target is None` 且候选处于当前区域最大控制流 depth 时写入固定 `multi_buffer.num = str(memory_stage)`。
  - `target` 为 `None` 或非空字符串；`target` 非空且候选处于当前区域最大控制流 depth 时写入 `multi_buffer.num = "auto"`。
  - `from_options(...)` 只接受 `memory-stage` 与 `target`；未知 option 或 `fold` 必须失败。
- `MultiBufferApplyPass`：
  - `target` 为 `None` 或非空字符串；遇到 `"auto"` 时必须通过本 pass 的 `target` 读取 target capacity，`target is None` 时 auto group no-op。
  - `alignment` 为非负整数；默认 `1024`；`0` 关闭对齐。
  - `from_options(...)` 只接受 `target` 与 `alignment`；未知 option 或 `fold` 必须失败。
- `MultiBufferPass`：
  - 兼容 facade，接受 `memory-stage`、`target` 与 `alignment`。
  - registry 通用 `fold` option 由 [`spec/pass/registry.md`](../registry.md) 剥离并写回 pass 实例，不属于本 family 专属 options。

## Analysis 合同

- analysis 遍历可证明的 `dma.alloc/free` lifecycle，记录 update points、use points 和 num。
- analysis 会按 module walk 顺序为控制流补齐稳定 id：
  - `symbol.for` 写 `analysis.loop_id = "loopN-D"`；
  - `scf.if` 写 `analysis.if_id = "ifN-D"`；
  - `D` 是控制流 depth：最外层 `symbol.for` 为 1，嵌套 `symbol.for` 逐层加 1，loop 内 `scf.if` 使用所在 loop depth，顶层 `scf.if` 为 1；
  - 既有非空字符串 id 保持不变，新 id 不与已有 id 冲突。
- analysis 不删除、不插入、不替换业务 IR；输出只允许在控制流上新增 analysis id，并在候选 `dma.alloc` 上新增三项属性：

```text
multi_buffer.update_points = ["main" | "loopN-D" | "ifN-D", ...]
multi_buffer.use_points = ["loopN-D" | "ifN-D", ...]
multi_buffer.num = "auto" | "<positive-int>"
```

- `update_points/use_points` 都是非空 `ArrayAttr[StringAttr]`，按首次出现顺序去重。
- loop-local direct use 使用 `update_points = ["main"]`，并写 `multi_buffer.num = "1"`。
- 非 main 候选：
  - 若 `update_points/use_points` 内所有控制流点 depth 均等于目标 loop 区域最大 depth，则 `target` 非空时写 `"auto"`，`target is None` 时写 `str(memory_stage)`；
  - 否则写固定 `"2"`。
- 不满足条件的 alloc 保持 no-op，不写三项属性。

## Apply 合同

- apply 只处理同时带有三项 `multi_buffer.*` 属性的候选。
- apply 不生成或补写 `analysis.loop_id/analysis.if_id`；apply-only 输入缺少 analysis 阶段已产出的控制流 id 时保持 no-op。
- apply 重新校验：
  - alloc/free 仍存在；
  - first/last use 仍可定位；
  - `multi_buffer.update_points/use_points` 是非空 `ArrayAttr[StringAttr]`；
  - `multi_buffer.num` 是正整数字符串或 `"auto"`；
  - update/use points 与当前可证明 lifecycle region 一致；
  - use block 内没有已有 `dma.current_ring` 导致重复 ring。
- fixed candidate：
  - `aligned_slot_bytes = align_unit(slot_bytes(candidate), alignment)`。
  - `fixed_backing_bytes = fixed_num * aligned_slot_bytes`。
  - fixed backing 计入同 memory space 的 `fixed_reserved_bytes`。
- same-scope live alloc：
  - apply 若能证明同一 insertion scope 内、insertion anchor 前存在同 space 且会与 ring backing 共存的非候选 `dma.alloc`，必须把其 memory-pool 对齐 footprint 计入 `same_scope_reserved_bytes`。
  - 无法证明 footprint 时，该 auto group 保持 no-op，避免生成 memory-pool 后会越界的 backing。
- auto candidate：
  - 按 target loop / insertion scope / memory space 分组。
  - `available = target_capacity[space] - fixed_reserved_bytes[space] - same_scope_reserved_bytes[space]`。
  - `group_unit = sum(align_unit(slot_bytes(candidate), alignment) for candidate in auto group)`。
  - `auto_num = available floordiv group_unit`。
  - target 缺失、capacity 非正、available 非正、group_unit 非正或 auto_num 非正时，该 auto group no-op。
- ring 物化：
  - backing alloc 为同 memory space 的一维 `i8`，大小 `effective_num * aligned_slot_bytes`。
  - `dma.make_ring(backing, effective_num, aligned_slot_bytes, ring<原 slot type>)`。
  - `dma.current_ring` 插入 use block 最前面，即 block arguments 之后、第一条既有 op 之前，并替换原 alloc/direct alias/direct use operand。
  - `dma.advance_ring` 插入 use block 最后面；若 block 有 terminator，则插在 terminator 之前。
  - 删除原 typed `dma.free` 与 `dma.alloc`，输出不得残留三项临时属性。

```text
align_unit(x, alignment) =
  x, if alignment == 0
  ((x + alignment - 1) floordiv alignment) * alignment, otherwise

slot_bytes(candidate) = element_bytes * product(slot_shape_dims_from_alloc)
fixed_reserved_bytes[space] =
  sum(fixed_num(candidate) * align_unit(slot_bytes(candidate), alignment) for fixed candidate)
same_scope_reserved_bytes[space] =
  memory_pool_footprint(non_candidate_allocs_before_insertion_anchor_in_same_space)
available = target_capacity[space] - fixed_reserved_bytes[space] - same_scope_reserved_bytes[space]
group_unit = sum(align_unit(slot_bytes(candidate), alignment) for auto candidate in group)
auto_num = available floordiv group_unit
backing_bytes(candidate) = effective_num * align_unit(slot_bytes(candidate), alignment)
```

## 候选边界

- 兼容旧 matmul lhs/rhs direct pair：
  - matmul 位于同一 `symbol.for` 直接 body；
  - lhs/rhs 两个 operand 都来自 loop 外同 parent block 的 `dma.alloc`；
  - 每个 alloc 只能被 loop body 内唯一 copy target、该 matmul 对应 lhs/rhs operand、parent block 内唯一 free 使用；
  - 生命周期顺序为 `alloc < symbol.for < free` 和 `copy < kernel.matmul`；
  - lhs/rhs 任一不满足时整对 no-op。
- loop staging / scratch direct alias 与 direct use：
  - 只支持一层 direct alias：`dma.reinterpret`、`dma.view`、`dma.reshape`、`dma.subview`。
  - 支持 direct memory use：`dma.broadcast/copy/deslice/fill/load/slice/store/transpose`、`kernel.binary_elewise/img2col1d/img2col2d/matmul`。
  - 所有 access op 必须能收口到同一个最深共同 `symbol.for`，可位于该 loop body、嵌套 `symbol.for` 或该 loop 下的 `scf.if` branch。
  - 不支持跨 sibling loop/if、loop 外 escape 或无法定位共同 `symbol.for` 的访问。
  - `use_points` 记录每个 access 相对目标 loop 的直接 lifecycle 域：目标 loop body 为 `analysis.loop_id`，嵌套 loop 为该 loop id，if branch 为该 if id。
  - 旧 matmul lhs/rhs direct pair 的 operand 1/2 仍由成对路径处理，loop staging 路径不抢占该合同。
- 动态 shape bytes 必须来自 `dma.alloc` 的公开 dynamic_shape operands，不通过后续 `symbol.get_dim` 反推动静态 / 动态 shape。

## 错误语义

- direct API 错误：
  - `MultiBufferOptionError: memory_stage must be integer`
  - `MultiBufferOptionError: memory_stage must be positive`
  - `MultiBufferOptionError: memory-stage must be integer`
  - `MultiBufferOptionError: memory-stage must be positive`
  - `MultiBufferOptionError: target must be non-empty`
  - `MultiBufferOptionError: alignment must be non-negative integer`
  - `MultiBufferOptionError: unknown option: <name>`
- registry 包装错误：
  - `PassRegistryError: pass 'multi-buffer-analysis' option error: MultiBufferOptionError: <原因>`
  - `PassRegistryError: pass 'multi-buffer-apply' option error: MultiBufferOptionError: <原因>`
  - `PassRegistryError: pass 'multi-buffer' option error: MultiBufferOptionError: <原因>`

## 使用示例

```python
from kernel_gen.passes.memory.multi_buffer import MultiBufferAnalysisPass, MultiBufferApplyPass

MultiBufferAnalysisPass(memory_stage=2, target="npu_demo").apply(ctx, module)
MultiBufferApplyPass(target="npu_demo", alignment=1024).apply(ctx, module)
```

```python
from kernel_gen.passes.registry import build_registered_pass, load_builtin_passes

load_builtin_passes()
pass_obj = build_registered_pass(
    "multi-buffer",
    {"memory-stage": "4", "target": "npu_demo", "alignment": "1024", "fold": "false"},
)
```

## 测试矩阵

| 用例 | 场景 | 断言 |
| --- | --- | --- |
| TC-MULTI-BUFFER-001 | direct API options | 三个公开 class 的默认值、非法参数和 `from_options` 边界稳定。 |
| TC-MULTI-BUFFER-002 | registry options | 三个 registry pass name 可构造，registry 通用 `fold=false` 写回实例。 |
| TC-MULTI-BUFFER-002A | analysis-only | 只写三项属性，不生成 ring，不删除 alloc/free。 |
| TC-MULTI-BUFFER-002B | apply-only / alignment=0 | 只消费三项属性；关闭对齐时 offset/backing 使用 raw slot bytes。 |
| TC-MULTI-BUFFER-002C | apply-only / 无三项属性 | 无 `multi_buffer.*` 候选时不写 `analysis.loop_id/analysis.if_id`，不生成 ring。 |
| TC-MULTI-BUFFER-003 | facade lhs/rhs 成对 ring 化 | `MultiBufferPass` 等价于 analysis + apply，生成两个 aligned ring。 |
| TC-MULTI-BUFFER-004..011 | no-op 边界 | missing free、free before loop、loop internal legacy pair、alias escape、多 free、已有 ring、partial pair、nested use 均 no-op。 |
| TC-MULTI-BUFFER-012 | target same-space static num | 同 space 按 aligned slot 合计计算共享 auto num。 |
| TC-MULTI-BUFFER-013 | target different-space static num | 不同 space 各自按本 space capacity 与 aligned slot 计算 num。 |
| TC-MULTI-BUFFER-014 | target dynamic same-space num | dynamic shape 来自 alloc operands，offset/backing 和 auto num 包含 `1023/1024/floordiv` 对齐公式，不使用 `symbol.get_dim`。 |
| TC-MULTI-BUFFER-015 | loop-local direct use | loop body 内 direct use 改写为 `num=1` aligned ring；已有 prefix/suffix 时 current 在 prefix 前，advance 在 suffix 后。 |
| TC-MULTI-BUFFER-015B | loop-local direct use / terminator | use block 有 terminator 时，advance 插在 terminator 前。 |
| TC-MULTI-BUFFER-015C | if path analysis | `scf.if` branch 内 direct use 写 `analysis.loop_id/if_id`、列表 points，非最大 depth 写 `num=2`。 |
| TC-MULTI-BUFFER-015D | if path apply | if path candidate 改写为 outer loop current/advance ring，branch 内 direct use 被替换，临时属性不残留。 |

## 验收命令

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/passes/memory/test_multi_buffer.py test/passes/test_registry.py
```

## 可选本地诊断

- `expectation/pass/multi_buffer/**` 只作为本地-only 诊断参考，不是本 spec 的必过验收命令，不计入 Diff 反推测试，不替代 pytest。
- 若本地自愿运行 `python3 -m expectation.pass.multi_buffer`，只能记录 `actual / expected / spec / verdict`；失败不授权 execute 修改 `expectation/` 本体。
