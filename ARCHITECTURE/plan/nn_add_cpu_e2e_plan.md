# nn_add_cpu_e2e_plan.md

## 进度

- 更新日期：2026-03-31
- 更新规则：每个任务块进入新子阶段后立即更新本段。
- `A1`：合并完成（main=d400b45）。
- `A2`：同步确认完成（main=ada0738）。
- `A3`：spec 完成（T-20260330-fdffc9c3）；实现完成（T-20260330-fb7519ac）；审查通过（T-20260330-da5be88e）；注释规范修复完成（T-20260330-7a44edc3）。
- `A4`：合并完成（main=12a51fc）。
- `A5`：spec 完成（T-20260331-d2f620c5）；实现完成（T-20260331-0471c4fd）；复审不通过（T-20260331-7693c10d，direct-return nn.add 判定过宽，缺少多 use 反例测试）；实现修复完成（T-20260331-4d78773c）；复审不通过（T-20260331-2af7343e，GK-015 仍使用泛化 `ValueError match=nn.add`，未机械锁定 return 唯一 use 才特化的边界）；二次实现修复完成（T-20260331-e7802e86）；二次复审通过（T-20260331-e62f521e）；合并完成（T-20260331-7162c3e2，commit=f16832b，单次 `git fetch origin` 超时，不影响完成判定，cleanup 已完成）。
- `A6`：任务建档完成（T-20260331-24ed4a87）；阻塞确认（T-20260331-24ed4a87，worktree 缺 expectation 依赖且主仓/A6 基线仍不支持目标成功路径）；实现/测试基线修复完成但 expectation 主仓基线仍为旧失败路径（T-20260331-3343415c，已暂停）；expectation 更新完成（T-20260331-2262e04d）；复审不通过（T-20260331-e03c63c5，功能闭环已通过，但 expectation 产物仍未进入 git 跟踪集合，存在主线不可复现风险）；版本化收口完成（T-20260331-52be2264）；复审回归通过（T-20260331-c1c48400）；合并完成（T-20260331-9731f096，commit=f570c4a，按授权合并指定 expectation 文件，单次 `git fetch origin` 超时不影响完成判定，cleanup 已完成）。
- 当前执行中：无。
- 当前建议推进顺序：`nn_add` 主链已封板；后续仅在出现补推或主线回归时再重开独立任务。

## 功能简介

- 定义 `add` 在当前仓库中的最小端到端串通计划：`DSL -> MLIR(func.func) -> CPU 源码 -> expectation`。
- 目标不是继续让我直接改代码，而是给管理员一份可以分发、可以验收、可以回退的执行计划。
- 本计划只覆盖 `add` 专题，不改变 `conv_cpu_tiled_v1_plan.md` 的推进顺序。

## 文档信息

- 创建者：`大闸蟹`
- 最后一次更改：`大闸蟹`
- `文档`：[`ARCHITECTURE/plan/nn_add_cpu_e2e_plan.md`](../../ARCHITECTURE/plan/nn_add_cpu_e2e_plan.md)
- `spec`：
  - [`spec/dialect/nn.md`](../../spec/dialect/nn.md)
  - [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
  - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
  - [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
  - [`spec/include/cpu/cpu.md`](../../spec/include/cpu/cpu.md)
- `功能实现`：
  - [`kernel_gen/dialect/nn.py`](../../kernel_gen/dialect/nn.py)
  - [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py)
  - [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py)
  - [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)
  - [`include/cpu/Nn.h`](../../include/cpu/Nn.h)
- `test`：
  - [`test/dialect/test_nn_dialect.py`](../../test/dialect/test_nn_dialect.py)
  - [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py)
  - [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py)
  - [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)
  - [`test/include/cpu/test_nn.py`](../../test/include/cpu/test_nn.py)
  - [`expectation/dsl/emit_c/cpu/add.py`](../../expectation/dsl/emit_c/cpu/add.py)

## 目标与边界

### 目标

- 让以下三种 `add` 形态都能沿公开链路串到 CPU 源码：
  - `memory + memory`
  - `memory + const`
  - `memory + symbol`
- 对外公开入口保持现有口径：`build_func_op(...)` / `build_func_op_from_ast(...)` / `gen_kernel(...)` / `cpu::add(...)`。
- 让 [`expectation/dsl/emit_c/cpu/add.py`](../../expectation/dsl/emit_c/cpu/add.py) 从“描述当前失败边界”切换为“描述目标成功路径”。

### 非目标

- 不扩展 `sub/mul/truediv` 的 mixed memory-scalar 路径。
- 不新增新的 DSL 公开入口函数名，例如 `normalize_emit_mlir_contract(...)`、`emit_mlir_function(...)`。
- 不改 `nn_to_kernel`、`kernel dialect`、`conv` 相关链路。
- 不实现通用 memory SSA 物化；本轮 `gen_kernel` 只承接“`func.return` 直接返回 `nn.add` 结果”的最小闭环。

## 当前真实断点

1. `nn.add` 方言层当前只接受 `nn.memory + nn.memory`，mixed `memory + scalar` / `memory + symbol` 还没有 verifier 契约。
2. `emit_mlir` / `build_func_op` 当前把 `lhs + 1`、`lhs + symbol` 视为非法 memory 二元算术，无法生成 `nn.add`。
3. `include/cpu/Nn.h` 当前只有 `cpu::add(const Memory&, const Memory&, Memory&)`，没有 scalar overload。
4. `gen_kernel` 当前不能把 direct-return 的 `nn.add` 结果直接落为 `cpu::add(..., out);`。
5. `expectation/dsl/emit_c/cpu/add.py` 目前仍在描述失败路径，不符合“应该是什么”的质量基线定位。

## 管理执行规则

- 本计划由管理员统一分发，不带 `-to` 指派。
- 执行者回答架构问题后，应继续自己的原任务；不要因为回复而中断原任务，除非管理员另有安排。
- 验收以本计划里的“测试函数名 + 预期输出 + 命令退出码”为准。
- 若实现者想新增对外公开 API，先驳回，回到本计划确认；本计划不允许通过新增虚拟入口来绕过现有接口。

## 任务依赖

- 可并行：`A1`、`A4`
- `A2` 依赖：`A1`
- `A3` 依赖：`A2`
- `A5` 依赖：`A3`、`A4`
- `A6` 依赖：`A5`

## 任务清单

### A1. nn.add 方言支持 mixed memory-scalar

- 目标：在 [`kernel_gen/dialect/nn.py`](../../kernel_gen/dialect/nn.py) 让 `NnAddOp` 支持 `nn.memory + scalar`、`scalar + nn.memory`、`nn.memory + !symbol.int`，并把 verifier 边界写回 [`spec/dialect/nn.md`](../../spec/dialect/nn.md)。
- 边界：只改 `nn.add`；`sub/mul/truediv` 保持当前行为；不得放开为 `scalar + scalar`。
- 可改文件：
  - [`spec/dialect/nn.md`](../../spec/dialect/nn.md)
  - [`kernel_gen/dialect/nn.py`](../../kernel_gen/dialect/nn.py)
  - [`test/dialect/test_nn_dialect.py`](../../test/dialect/test_nn_dialect.py)
- 注意事项：
  - 至少一侧必须是 `nn.memory`。
  - `result.shape/stride/space` 继承 memory operand。
  - `dtype promotion` 固定为 `i32 < f16 < f32`；`!symbol.int` 按 `i32` 参与 promotion。
  - `space` 不一致必须报错，不能静默转换。
- 示例：
```python
# memory + const
out = lhs + 1

# memory + symbol
out = lhs + rhs
```
- 验收标准：新增并通过以下测试函数。
  - `test_add_op_accepts_memory_const_rhs`
    - 输入：`lhs=!nn.memory<[2,3],[3,1],i32,#nn.space<global>>`，`rhs=i32`，`result` 同 shape/stride/space。
    - 预期输出：`NnAddOp(...).verify()` 返回 `None`。
  - `test_add_op_accepts_memory_symbol_rhs`
    - 输入：`lhs=!nn.memory<[2,3],[3,1],i32,#nn.space<global>>`，`rhs=!symbol.int<"K">`，`result` 为同 shape 的 `i32 memory`。
    - 预期输出：`NnAddOp(...).verify()` 返回 `None`。
  - `test_add_op_rejects_pure_scalar_operands`
    - 输入：`lhs=i32`，`rhs=f32`，`result=!nn.memory<[2,3],[3,1],f32,#nn.space<global>>`。
    - 预期输出：抛 `VerifyException`，消息包含 `at least one nn.memory operand`。
  - `test_add_op_rejects_mixed_result_shape_mismatch`
    - 输入：`lhs=!nn.memory<[2,3],[3,1],i32,#nn.space<global>>`，`rhs=i32`，`result=!nn.memory<[2,2],[2,1],i32,#nn.space<global>>`。
    - 预期输出：抛 `VerifyException`，消息包含 `result shape must match memory operand`。
- 验证命令：
```bash
pytest -q test/dialect/test_nn_dialect.py -k 'test_add_op_accepts_memory_const_rhs or test_add_op_accepts_memory_symbol_rhs or test_add_op_rejects_pure_scalar_operands or test_add_op_rejects_mixed_result_shape_mismatch'
```
- 放行条件：命令退出码为 `0`。

### A2. emit_mlir 支持 memory+const / memory+symbol add lowering

- 目标：在 [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py) 让 `BinaryExprAST(op="add")` 支持 mixed `memory + scalar` lowering，并更新 [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)。
- 边界：仅 `op="add"`；其他 mixed memory-scalar 二元算术仍保持报错。
- 可改文件：
  - [`spec/dsl/emit_mlir.md`](../../spec/dsl/emit_mlir.md)
  - [`kernel_gen/dsl/emit_mlir.py`](../../kernel_gen/dsl/emit_mlir.py)
  - [`test/dsl/test_emit_mlir.py`](../../test/dsl/test_emit_mlir.py)
- 注意事项：
  - mixed add 的 `result_type` 继承 memory operand 的 `shape/stride/space`。
  - 若 scalar dtype 高于 memory dtype，可按既有 promotion 规则对 memory 侧补 `dma.cast`。
  - `sub/mul/div` 遇到 mixed `memory + scalar` 仍必须报错，不能顺手一起放开。
- 示例：
```python
def add_memory_const(lhs: 'Tensor[i32, 2, 3]') -> 'Tensor[i32, 2, 3]':
    out = lhs + 1
    return out


def add_memory_symbol(lhs: 'Tensor[i32, 2, 3]', rhs: int) -> 'Tensor[i32, 2, 3]':
    out = lhs + rhs
    return out
```
- 验收标准：新增并通过以下测试函数。
  - `test_emit_mlir_lowers_memory_const_add_to_nn_add`
    - 输入：`add_memory_const`。
    - 预期输出：block 中包含 `1` 个 `NnAddOp`；其 `rhs.type` 为 `i32`；`result.type` 为 `!nn.memory<[2,3],[3,1],i32,#nn.space<global>>`。
  - `test_emit_mlir_lowers_memory_symbol_add_to_nn_add`
    - 输入：`add_memory_symbol` + 运行时参数 `SymbolDim("K")`。
    - 预期输出：block 中包含 `1` 个 `NnAddOp`；其 `rhs.type` 为 `!symbol.int<"K">`；`result.type.element_type == i32`。
  - `test_emit_mlir_rejects_mixed_memory_scalar_sub`
    - 输入：
```python
def bad(lhs: 'Tensor[i32, 2, 3]') -> 'Tensor[i32, 2, 3]':
    out = lhs - 1
    return out
```
    - 预期输出：抛 `_LoweringError`，消息包含 `Mixed nn.memory/scalar binary op only supports add`。
- 验证命令：
```bash
pytest -q test/dsl/test_emit_mlir.py -k 'test_emit_mlir_lowers_memory_const_add_to_nn_add or test_emit_mlir_lowers_memory_symbol_add_to_nn_add or test_emit_mlir_rejects_mixed_memory_scalar_sub'
```
- 放行条件：命令退出码为 `0`。

### A3. build_func_op 端到端接入 mixed add，且不新增虚拟公开入口

- 目标：让 [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py) 的公开入口 `build_func_op(...)` / `build_func_op_from_ast(...)` 能串起 mixed add；不得新增新的 DSL 公开包装函数名。
- 边界：只做现有公开入口接入；不得引入新的对外入口 `normalize_emit_mlir_contract(...)`、`emit_mlir_function(...)`。
- 可改文件：
  - [`spec/dsl/mlir_gen.md`](../../spec/dsl/mlir_gen.md)
  - [`kernel_gen/dsl/mlir_gen.py`](../../kernel_gen/dsl/mlir_gen.py)
  - [`test/dsl/test_mlir_gen.py`](../../test/dsl/test_mlir_gen.py)
- 注意事项：
  - 管理员分发时要特别说明：这里的“接入”指修通现有公开入口，不是新增一层虚拟 facade。
  - mixed add 只保证 direct-return 路径，先不扩展中间 memory SSA 落地。
- 示例：
```python
def add_memory_symbol(lhs: 'Tensor[i32, 2, 3]', rhs: int) -> 'Tensor[i32, 2, 3]':
    out = lhs + rhs
    return out
```
- 验收标准：新增并通过以下测试函数。
  - `test_build_func_op_supports_memory_const_add_return`
    - 输入：`build_func_op(add_memory_const, MEMORY_I32)`。
    - 预期输出：返回 `FuncOp`；body 中含 `1` 个 `NnAddOp` 与 `1` 个 `func.ReturnOp`；`ReturnOp.arguments[0] is NnAddOp.result`。
  - `test_build_func_op_supports_memory_symbol_add_return`
    - 输入：`build_func_op(add_memory_symbol, MEMORY_I32, SymbolDim("K"))`。
    - 预期输出：返回 `FuncOp`；`NnAddOp.rhs.type == !symbol.int<"K">`；`ReturnOp.arguments[0] is NnAddOp.result`。
  - `test_build_func_op_public_entrypoints_remain_stable`
    - 输入：执行 `rg -n '^def (normalize_emit_mlir_contract|emit_mlir_function)\(' kernel_gen/dsl -S`。
    - 预期输出：命令退出码为 `1`，表示仓库中不存在这两个新公开函数定义。
- 验证命令：
```bash
pytest -q test/dsl/test_mlir_gen.py -k 'test_build_func_op_supports_memory_const_add_return or test_build_func_op_supports_memory_symbol_add_return'
rg -n '^def (normalize_emit_mlir_contract|emit_mlir_function)\(' kernel_gen/dsl -S
```
- 放行条件：第一条命令退出码为 `0`；第二条命令退出码为 `1`。

### A4. CPU runtime 提供 scalar add overload

- 目标：在 [`include/cpu/Nn.h`](../../include/cpu/Nn.h) 为 `cpu::add` 补齐 `Memory + scalar` 与 `scalar + Memory` overload，并更新 [`spec/include/cpu/cpu.md`](../../spec/include/cpu/cpu.md)。
- 边界：只扩 `add`；不扩 `sub/mul/div`；不新增独立的 `add_scalar` 公开 API。
- 可改文件：
  - [`spec/include/cpu/cpu.md`](../../spec/include/cpu/cpu.md)
  - [`include/cpu/Nn.h`](../../include/cpu/Nn.h)
  - [`test/include/cpu/test_nn.py`](../../test/include/cpu/test_nn.py)
- 注意事项：
  - overload 名称必须仍是 `cpu::add`。
  - 标量可以是字面量，也可以是 `long long` 运行时变量，用于承接 `!symbol.int`。
  - 输出必须写入调用方提供的 `out`，不得偷偷分配新 `Memory`。
- 示例：
```cpp
cpu::add(lhs, 1, out_rhs);
cpu::add(2, rhs, out_lhs);
long long scale = 5;
cpu::add(lhs_i32, scale, out_i32);
```
- 验收标准：新增并通过以下测试函数。
  - `test_cpu_nn_add_scalar_rhs_success`
    - 输入：`lhs=[1,2,3,4,5,6]`，`rhs=1`。
    - 预期输出：`out=[2,3,4,5,6,7]`。
  - `test_cpu_nn_add_scalar_lhs_success`
    - 输入：`lhs=2`，`rhs=[6,5,4,3,2,1]`。
    - 预期输出：`out=[8,7,6,5,4,3]`。
  - `test_cpu_nn_add_symbol_like_scalar_success`
    - 输入：`lhs=[1,2,3,4]`，`scale=5`。
    - 预期输出：`out=[6,7,8,9]`。
- 验证命令：
```bash
pytest -q test/include/cpu/test_nn.py -k 'test_cpu_nn_add_scalar_rhs_success or test_cpu_nn_add_scalar_lhs_success or test_cpu_nn_add_symbol_like_scalar_success'
```
- 放行条件：命令退出码为 `0`。

### A5. gen_kernel 让 direct-return nn.add 生成 cpu::add(..., out)

- 目标：在 [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py) 让 direct-return 的 `nn.add` 结果直接生成为 `cpu::add(..., out);`，并更新 [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)。
- 边界：只支持 `func.return` 直接返回 `nn.add.result` 的场景；不做通用 memory SSA 临时变量物化。
- 可改文件：
  - [`spec/dsl/gen_kernel.md`](../../spec/dsl/gen_kernel.md)
  - [`kernel_gen/dsl/gen_kernel.py`](../../kernel_gen/dsl/gen_kernel.py)
  - [`test/dsl/test_gen_kernel.py`](../../test/dsl/test_gen_kernel.py)
- 注意事项：
  - 这里的输出应直接调用 `cpu::add`，不要再要求 `emit_c` 先能独立处理 `nn.add` memory 结果。
  - `memory + memory`、`memory + const`、`memory + symbol` 三条路径都要覆盖。
  - 若 `func.return` 返回的不是 direct `nn.add.result`，保持当前行为或明确报错，不要偷扩范围。
- 示例：
```python
def add_memory_const(lhs: 'Tensor[i32, 2, 3]') -> 'Tensor[i32, 2, 3]':
    out = lhs + 1
    return out
```
- 验收标准：新增并通过以下测试函数。
  - `test_gen_kernel_lowers_direct_return_nn_add_memory_memory_to_cpu_add_call`
    - 输入：`build_func_op(add_memory, MEMORY_I32, MEMORY_I32)`。
    - 预期输出：源码包含
      - `void add_memory(const Memory<int32_t>& lhs, const Memory<int32_t>& rhs, Memory<int32_t>& out)`
      - `cpu::add(lhs, rhs, out);`
  - `test_gen_kernel_lowers_direct_return_nn_add_memory_const_to_cpu_add_call`
    - 输入：`build_func_op(add_memory_const, MEMORY_I32)`。
    - 预期输出：源码包含 `cpu::add(lhs, 1, out);`。
  - `test_gen_kernel_lowers_direct_return_nn_add_memory_symbol_to_cpu_add_call`
    - 输入：`build_func_op(add_memory_symbol, MEMORY_I32, SymbolDim("K"))`。
    - 预期输出：源码包含
      - `void add_memory_symbol(const Memory<int32_t>& lhs, long long rhs, Memory<int32_t>& out)`
      - `cpu::add(lhs, rhs, out);`
- 验证命令：
```bash
pytest -q test/dsl/test_gen_kernel.py -k 'test_gen_kernel_lowers_direct_return_nn_add_memory_memory_to_cpu_add_call or test_gen_kernel_lowers_direct_return_nn_add_memory_const_to_cpu_add_call or test_gen_kernel_lowers_direct_return_nn_add_memory_symbol_to_cpu_add_call'
```
- 放行条件：命令退出码为 `0`。

### A6. expectation/dsl/emit_c/cpu/add.py 改写为目标成功路径

- 目标：把 [`expectation/dsl/emit_c/cpu/add.py`](../../expectation/dsl/emit_c/cpu/add.py) 从“描述当前失败边界”改为“定义 add 端到端应该成功的行为”。
- 边界：只改这一个 expectation 文件；不要把“当前实现还不支持”写回 expectation。
- 可改文件：
  - [`expectation/dsl/emit_c/cpu/add.py`](../../expectation/dsl/emit_c/cpu/add.py)
- 注意事项：
  - expectation 要定义目标质量，不要复述实现限制。
  - 三条成功路径都要保留：`memory + memory`、`memory + const`、`memory + symbol`。
  - expectation 中失败路径只保留长期契约级失败，不保留“当前没做出来”的失败。
- 示例：
```python
def add_memory_const(lhs: 'Tensor[i32, 2, 3]') -> 'Tensor[i32, 2, 3]':
    out = lhs + 1
    return out
```
- 验收标准：脚本执行时，以下四个 case 全部通过。
  - `CASE-1` 标量 + 标量
    - 输入：`add_scalar(2, 3)`。
    - 预期输出：生成源码包含 `long long v0 = (arg0 + arg1);` 与 `return v0;`。
  - `CASE-2` memory + memory
    - 输入：`build_func_op(add_memory, MEMORY_I32, MEMORY_I32)`。
    - 预期输出：`gen_kernel(...)` 生成源码包含 `cpu::add(lhs, rhs, out);`。
  - `CASE-3` memory + const
    - 输入：`build_func_op(add_memory_const, MEMORY_I32)`。
    - 预期输出：`gen_kernel(...)` 生成源码包含 `cpu::add(lhs, 1, out);`。
  - `CASE-4` memory + symbol
    - 输入：`build_func_op(add_memory_symbol, MEMORY_I32, SymbolDim("K"))`。
    - 预期输出：`gen_kernel(...)` 生成源码包含 `cpu::add(lhs, rhs, out);`，且函数签名里第二个参数为 `long long rhs`。
- 验证命令：
```bash
PYTHONPATH=. python expectation/dsl/emit_c/cpu/add.py
```
- 放行条件：命令退出码为 `0`。

## 建议分发顺序

1. 先发 `A1` 与 `A4`，这两项互不冲突。
2. `A1` 完成后发 `A2`。
3. `A2` 完成后发 `A3`。
4. `A3` 与 `A4` 都完成后发 `A5`。
5. `A5` 通过后发 `A6`。

## 统一验收命令

```bash
pytest -q test/dialect/test_nn_dialect.py -k 'test_add_op_accepts_memory_const_rhs or test_add_op_accepts_memory_symbol_rhs or test_add_op_rejects_pure_scalar_operands or test_add_op_rejects_mixed_result_shape_mismatch'
pytest -q test/dsl/test_emit_mlir.py -k 'test_emit_mlir_lowers_memory_const_add_to_nn_add or test_emit_mlir_lowers_memory_symbol_add_to_nn_add or test_emit_mlir_rejects_mixed_memory_scalar_sub'
pytest -q test/dsl/test_mlir_gen.py -k 'test_build_func_op_supports_memory_const_add_return or test_build_func_op_supports_memory_symbol_add_return'
rg -n '^def (normalize_emit_mlir_contract|emit_mlir_function)\(' kernel_gen/dsl -S
pytest -q test/include/cpu/test_nn.py -k 'test_cpu_nn_add_scalar_rhs_success or test_cpu_nn_add_scalar_lhs_success or test_cpu_nn_add_symbol_like_scalar_success'
pytest -q test/dsl/test_gen_kernel.py -k 'test_gen_kernel_lowers_direct_return_nn_add_memory_memory_to_cpu_add_call or test_gen_kernel_lowers_direct_return_nn_add_memory_const_to_cpu_add_call or test_gen_kernel_lowers_direct_return_nn_add_memory_symbol_to_cpu_add_call'
PYTHONPATH=. python expectation/dsl/emit_c/cpu/add.py
```

- 总放行条件：
  - 所有 `pytest` / `python` 命令退出码均为 `0`。
  - `rg -n '^def (normalize_emit_mlir_contract|emit_mlir_function)\(' kernel_gen/dsl -S` 退出码为 `1`。

## 回退原则

- 若 `A1` verifier 设计导致 `nn.add` 纯 memory 路径回归，优先回退 mixed 分支，不要动现有 `memory + memory` 成功路径。
- 若 `A5` 发现 `gen_kernel` 需要扩成通用 memory SSA 物化，立即停止，不要偷扩；回到计划重新立项。
- 若 `A6` 与实现暂时冲突，优先补 `spec/实现/测试` 去追 expectation，不反向收窄 expectation。
