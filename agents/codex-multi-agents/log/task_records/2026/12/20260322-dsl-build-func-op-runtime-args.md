# 2026-03-23 T-20260322-6a068c74

- 任务 ID：`T-20260322-6a068c74`
- worktree：`/home/lfr/kernelcode_generate/wt-20260322-dsl-build-func-op-runtime-args`
- 变更文件：`spec/dsl/mlir_gen.md`
- 测试：未复测（本轮仅改 spec，不改实现与测试）
- 处理结果：
  - 将 `build_func_op` 的 spec 签名收敛为 `build_func_op(fn, *runtime_args, globals=None, builtins=None, config=None)`
  - 明确调用方必须显式传入与函数形参一一对应的实际输入参数，例如 `build_func_op(func, A)`、`build_func_op(add, A, B)`
  - 补充参数约束、错误路径与使用示例，明确 `globals` / `builtins` 不能替代函数运行时实参
  - 补充测试目标，并更新 `MGEN-001` 对齐 `expectation/dsl/build_func_op.py`
  - 新增 `MGEN-019`，定义“省略实际输入参数 / 实参数量不匹配 / 仅依赖 globals/builtins 补足输入”必须报错的闭环要求
- 结论：已完成本轮 spec 收敛；当前实现与测试仍需后续任务按新显式实参口径继续收敛
- 下一步建议：
  - 创建实现/测试任务，收敛 `kernel_gen/dsl/mlir_gen.py`、`expectation/dsl/build_func_op.py`、`test/dsl/test_ast_visitor.py`
  - 为 `MGEN-019` 补齐正式测试映射

# 2026-03-23 T-20260323-286eec9e

- 任务 ID：`T-20260323-286eec9e`
- worktree：`/home/lfr/kernelcode_generate/wt-20260322-dsl-build-func-op-runtime-args`
- 变更文件：`kernel_gen/dsl/mlir_gen.py`、`expectation/dsl/build_func_op.py`、`expectation/dsl/symbol.py`、`expectation/dsl/for_loop.py`、`test/dsl/test_ast_visitor.py`
- 测试：`pytest -q test/dsl/test_ast_visitor.py`（`51 passed`）
- expectation 执行：`python expectation/dsl/build_func_op.py`、`python expectation/dsl/symbol.py`、`python expectation/dsl/for_loop.py`（均通过）
- 处理结果：
  - 将 `build_func_op` 实现签名收敛为 `build_func_op(fn, *runtime_args, globals=None, builtins=None, config=None)`
  - 增加形参与 `runtime_args` 数量一致性校验，缺参、错参、试图仅用 `globals` / `builtins` 代替运行时实参时统一抛出 `AstVisitorError`
  - 收敛 expectation 样例脚本到显式传参口径，并修正纯 symbol 样例使其符合现有 lowering 约束
  - 更新 `test/dsl/test_ast_visitor.py` 中 `build_func_op` 调用点，并补齐 `MGEN-019` 的三类错误路径测试
- 剩余缺口：
  - 本轮仅收敛 `build_func_op` 显式运行时实参链路；未扩展到其他 DSL 入口的 API 口径审查
- 结论：本任务范围内实现、测试与 expectation 已按 spec 收敛，可进入下一阶段复审

---

# 2026-03-23 T-20260323-1977ce03 复审记录

- 时间：2026-03-23 00:26:00 +0800
- 角色：`朽木露琪亚`
- worktree：`/home/lfr/kernelcode_generate/wt-20260322-dsl-build-func-op-runtime-args`
- 任务描述：复审 `build_func_op` 显式 `runtime_args` 链路，重点核对 `build_func_op(fn, *runtime_args, ...)` 契约、`MGEN-001/MGEN-019` 映射，以及 `expectation/build_func_op.py`、`expectation/dsl/symbol.py`、`expectation/dsl/for_loop.py` 与 `test/dsl/test_ast_visitor.py` 的闭环。

## 结论

- 需修改。

## 复审文件

- `spec/dsl/mlir_gen.md`
- `kernel_gen/dsl/mlir_gen.py`
- `expectation/dsl/build_func_op.py`
- `expectation/dsl/symbol.py`
- `expectation/dsl/for_loop.py`
- `test/dsl/test_ast_visitor.py`

## 未通过原因（需改进）

1. `spec/dsl/mlir_gen.md` 与 `kernel_gen/dsl/mlir_gen.py` 仍停留在旧的 `build_func_op(fn, globals=None, builtins=None, config=None)` 口径，没有收敛到本轮要求的 `build_func_op(fn, *runtime_args, ...)` 契约。
   - 位置：
     - `spec/dsl/mlir_gen.md:44-78`
     - `kernel_gen/dsl/mlir_gen.py:107-123`
   - 原因：
     - 公开接口签名、参数说明、示例都没有体现显式 `runtime_args`；
     - 实现函数签名也没有 `*runtime_args`，无法承接“调用方必须显式传入实际输入参数”的新契约。
   - 建议如何改：
     - 先创建 spec/实现对齐任务，统一 `build_func_op` 的公开签名、参数约束、错误路径和实现入口；
     - 明确 `globals` / `builtins` 只用于解析上下文，不能替代运行时实参。

2. `MGEN-001` 仍映射到旧调用方式，不能证明显式 `runtime_args` 契约成立；`MGEN-019` 在主线 spec 与测试中都未闭环。
   - 位置：
     - `spec/dsl/mlir_gen.md:120-137`
     - `test/dsl/test_ast_visitor.py:273-297`
     - `test/dsl/test_ast_visitor.py` 中未找到 `MGEN-019`
   - 原因：
     - `MGEN-001` 当前只验证 `build_func_op(add)` 能返回 `func.func`，没有验证显式传参；
     - `MGEN-019` 在当前主线 spec 中不存在，对应测试也不存在，无法覆盖“缺参 / 参数数量不匹配 / 仅依赖 globals/builtins 补足输入必须报错”的链路。
   - 建议如何改：
     - 将 `MGEN-001` 收紧为显式 `runtime_args` 正向路径；
     - 在 spec 和 `test/dsl/test_ast_visitor.py` 中补齐 `MGEN-019` 及其真实测试函数映射；
     - 错误路径至少覆盖：缺少 runtime args、数量不匹配、试图用 `globals`/`builtins` 代替 runtime args。

3. 三个 expectation 文件仍使用旧式 `build_func_op(...)` 调用，没有按“显式 runtime_args”口径收敛。
   - 位置：
     - `expectation/dsl/build_func_op.py:18-22`
     - `expectation/dsl/symbol.py:13-19`
     - `expectation/dsl/for_loop.py:46-54`
   - 原因：
     - `expectation/dsl/build_func_op.py` 仍是 `build_func_op(add)`；
     - `expectation/dsl/symbol.py` 仍是 `build_func_op(only_symbol)`；
     - `expectation/dsl/for_loop.py` 仍是 `build_func_op(add)`；
     - 这三处都不能证明 expectation 层已切换到显式传参主线。
   - 建议如何改：
     - 为三个 expectation 脚本补齐显式实参调用；
     - 同步保留各自原有断言目标：
       - `build_func_op.py` 继续验证 `func.func` 生成；
       - `symbol.py` 继续验证 `!symbol.int<"expr">` 与 `symbol.add`；
       - `for_loop.py` 继续验证 `scf.for + dma.slice/dma.deslice`。

4. `test/dsl/test_ast_visitor.py` 中与 expectation 对应的主线路径仍依赖旧行为，尚未证明 expectation/test 与显式 `runtime_args` 口径闭环。
   - 位置：
     - `test/dsl/test_ast_visitor.py:284-297`
     - `test/dsl/test_ast_visitor.py:569-601`
     - `test/dsl/test_ast_visitor.py:984-1031`
   - 原因：
     - `test_build_func_op_returns_func_op` 仍调用 `build_func_op(add)`；
     - pure symbol 与 for-loop 场景也仍沿用旧调用方式或依赖 `globals` 注入；
     - 因此 expectation 与测试并未共同证明“build_func_op(fn, *runtime_args, ...)”链路可用。
   - 建议如何改：
     - 将上述正向测试切换到显式 `runtime_args`；
     - 保留 `globals/builtins` 仅作为注解/环境解析入口，而不是函数实参来源；
     - 补一组与 expectation 一一对应的调用样例，避免再次漂移。

## 测试

- 本轮未复测。
- 说明：任务要求默认只读复审；本次以主线文件现状判断闭环一致性，已足以确认链路仍未收敛。

## 下一步建议

- 建议创建一个 `build_func_op runtime_args` 的实现与测试改进任务，范围限定为：
  - `spec/dsl/mlir_gen.md`
  - `kernel_gen/dsl/mlir_gen.py`
  - `expectation/dsl/build_func_op.py`
  - `expectation/dsl/symbol.py`
  - `expectation/dsl/for_loop.py`
  - `test/dsl/test_ast_visitor.py`
- 目标：
  - 统一切换到 `build_func_op(fn, *runtime_args, ...)`；
  - 收敛 `MGEN-001` 正向映射与 `MGEN-019` 错误路径映射；
  - expectation 与测试对同一调用约束保持一一对应后再发起复审。

---

# 2026-03-23 T-20260323-f96344d8

- 任务 ID：`T-20260323-f96344d8`
- worktree：`/home/lfr/kernelcode_generate/wt-20260322-dsl-build-func-op-runtime-args`
- 变更文件：`spec/dsl/mlir_gen.md`
- 测试：
  - `python expectation/dsl/build_func_op.py`
  - `python expectation/dsl/symbol.py`
  - `python expectation/dsl/for_loop.py`
  - `pytest -q test/dsl/test_ast_visitor.py`（`51 passed in 0.44s`）
- 处理结果：
  - 补齐 `spec/dsl/mlir_gen.md`，将 `build_func_op` 公开签名统一为 `build_func_op(fn, *runtime_args, globals=None, builtins=None, config=None)`
  - 明确 `runtime_args` 为函数运行时实参主线，`globals` / `builtins` 仅用于解析上下文，不能替代函数输入
  - 将 `MGEN-001` 正向用例映射收敛到显式 `runtime_args` 调用
  - 增补 `MGEN-019` 错误路径描述，并与 `test/dsl/test_ast_visitor.py` 中三类错误路径测试对齐
  - 对照 worktree 内现有实现、expectation 与测试，确认 `kernel_gen/dsl/mlir_gen.py`、`expectation/dsl/build_func_op.py`、`expectation/dsl/symbol.py`、`expectation/dsl/for_loop.py`、`test/dsl/test_ast_visitor.py` 已按同一契约闭环
- 结论：`build_func_op` 显式 `runtime_args` 链路已在本任务范围内完成收敛，可进入下一阶段复审
- 剩余缺口：
  - `runtime_args` 链路范围内无新增缺口
  - `symbol.for` lowering 属于独立任务链，不在本任务处理范围内

---

# 2026-03-23 T-20260323-8c2cc7d5

- 任务 ID：`T-20260323-8c2cc7d5`
- 任务类型：`复审`
- worktree：`/home/lfr/kernelcode_generate/wt-20260322-dsl-build-func-op-runtime-args`
- 记录人：`咯咯咯`
- 时间：`2026-03-23 00:58:40 +0800`

## 复审范围

- `spec/dsl/mlir_gen.md`
- `kernel_gen/dsl/mlir_gen.py`
- `expectation/dsl/build_func_op.py`
- `expectation/dsl/symbol.py`
- `expectation/dsl/for_loop.py`
- `test/dsl/test_ast_visitor.py`

## 复审结论

- 结论：`通过`

## 核对要点

- `build_func_op(fn, *runtime_args, ...)` 已作为公开签名，`MGEN-001` 与 `MGEN-019` 映射存在且一致。
- 三个 expectation 脚本均以显式 `runtime_args` 调用 `build_func_op`，未再依赖旧签名或仅靠 `globals/builtins` 传参。
- `test_build_func_op_returns_func_op` 与 `MGEN-019` 三类错误路径测试均按显式 `runtime_args` 口径覆盖。

## 测试

- 未运行测试（只读复审）。

## 下一阶段建议

- 建议进入下一阶段或关闭链路。
