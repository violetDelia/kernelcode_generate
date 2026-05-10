时间：2026-05-10 22:25 +0800
经办人：小李飞刀
任务：T-20260510-afe3f1ec / ast_kernel_operation_demos_green_plan
任务目标：按计划书一次完成 S1-S8 的规格、实现、测试与验收闭环；新增 `kernel_gen.operation.kernel` out-first API、kernel DSL mlir_gen、`Memory.get_shape() -> list[SymbolDim]` 解包/索引、matmul/conv2d/flash_attention 三形态 demo。
执行前阅读记录：
- 已读取个人提示词 `agents/codex-multi-agents/agents/小李飞刀/小李飞刀.prompt.md`。
- 已读取根目录 `AGENTS.md`，确认 execute 角色、公开 API、expectation、`.skills`、跨文件非公开 API、ctx 能力探测、`object` 签名和嵌套函数限制。
- 已读取 `agents/standard/任务记录约定.md` 与 `agents/standard/实现文件规范.md`。
- 已读取任务行：`TODO.md` 中 `T-20260510-afe3f1ec` 为 execute / 小李飞刀 / 进行中。
- 目标 worktree：`/home/lfr/kernelcode_generate/wt-20260510-ast-kernel-operation-demos`，当前分支 `task/ast-kernel-operation-demos`，HEAD `ff95b56cb5e48e394b2b763d4bf43f8ad93d48ec`。
- worktree 内未携带计划书，已只读引用主仓协调资产 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/ast_kernel_operation_demos_green_plan.md`。
- 授权 expectation 范围：仅 `expectation/operation/kernel/**` 与 `expectation/dsl/mlir_gen/dialect/kernel/**`；其它 `expectation/` 默认只读。
- 禁止事项：不得实现 `lhs.getshape(dim)` 或 `get_shape(dim)` 带参重载；不得改 `.skills`；不得新增未确认公开 API；不得跨文件使用非公开 API。
当前状态：
- worktree 当前无任务 diff。
- 记录文件原先不存在，本段为 execute 开工记录。
下一步：
- 扫描现有 operation、dialect kernel、DSL AST、Memory、matmul/conv2d/flash_attention 脚本与授权 expectation 资产，按 S1-S8 逐项落地。

时间：2026-05-10 23:48 +0800
经办人：小李飞刀
任务：T-20260510-afe3f1ec / ast_kernel_operation_demos_green_plan
任务目标：完成 S1-S8 的规格、实现、测试与验收闭环，并进入 review。
改动：
- 新增 `kernel_gen.operation.kernel` 包根公开 API：`KernelBinaryElewiseKind`、`binary_elewise(out, lhs, rhs, *, kind)`、`add/sub/mul/div/truediv/eq/ne/lt/le/gt/ge(out, lhs, rhs)`、`matmul(out, lhs, rhs)`、`img2col1d(...)`、`img2col2d(...)`；`kernel_gen.operation` 仅导出 `kernel` 子模块，不把 helper 外泄到包根。
- 新增 kernel DSL AST 节点与插件注册，支持 `kernel.add/sub/mul/div/truediv/eq/ne/lt/le/gt/ge/matmul/img2col1d/img2col2d` lowering 到现有 kernel dialect op；`binary_elewise` 只接受 `KernelBinaryElewiseKind` 枚举，不接受字符串 kind。
- 新增 `Memory.get_shape(self) -> list[SymbolDim]`，DSL mlir_gen 支持 `memory.get_shape()` 解包与常量索引；未实现也未保留 `get_shape(dim)` 或 `getshape(dim)` 带参入口。
- 为 `NnTransposeAST`、`NnSoftmaxAST` 补 `result_memory()`，使 flash_attention demo 中 `matmul(..., transpose(...))`、`softmax(..., axis=...)`、`matmul(softmax(...), value)` 可按公开 operation.nn 语义推导 Memory。
- 同步 `spec/operation/kernel.md`、`spec/dsl/ast/nodes/kernel.md`、`spec/dsl/ast/plugin/kernel.md` 与相关 `spec/dsl/ast/*`、`spec/symbol_variable/*`。
- 更新 matmul / conv2d / flash_attention 三类 demo：直接使用 `memory.get_shape()`；matmul static-static 补 K/reduce accumulator 形态；flash_attention 三形态补 fixed-seed static/static-dynamic/dynamic-dynamic 脚本与公开 pytest。
- 新增/更新对应公开 pytest：operation.kernel、DSL AST node/plugin/mlir_gen、Memory.get_shape、kernel demo 脚本断言与 package API 入口。
最小功能闭环：
- 公开 API 闭环：spec -> `kernel_gen.operation.kernel` 实现 -> DSL AST/plugin lowering -> pytest -> 授权 expectation 合同验收。
- Demo 闭环：三类 kernel demo 的 static-static / static-dynamic / dynamic-dynamic 脚本均可执行并对比 numpy/torch 参考结果；运行输入仍走现有公开 runner/ExecutionEngine 链路。
- 禁止面：未改 `.skills`；worktree 内未改 `expectation/`；未新增未确认的 `lhs.getshape(dim)` 或 `get_shape(dim)` 带参 API。
验证：
- `python3 -m py_compile kernel_gen/operation/kernel/elementwise.py kernel_gen/operation/kernel/structured.py kernel_gen/dsl/ast/nodes/kernel.py kernel_gen/dsl/ast/plugin/kernel.py kernel_gen/dsl/ast/dsl_ast.py kernel_gen/symbol_variable/memory.py kernel/matmul/inputs_static_tile_static.py kernel/flash_attention/inputs_static_tile_dynamic.py kernel/flash_attention/inputs_dynamic_tile_dynamic.py test/kernel/test_flash_attention_symbolic_memory_genkernel.py`：退出码 0。
- `python3 -m py_compile kernel_gen/dsl/ast/nodes/nn.py kernel/flash_attention/inputs_static_tile_static.py kernel/flash_attention/inputs_static_tile_dynamic.py kernel/flash_attention/inputs_dynamic_tile_dynamic.py`：退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/operation/kernel test/operation/test_package.py`：退出码 0，`14 passed in 0.63s`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/ast/plugin/test_kernel.py test/dsl/ast/nodes/test_kernel.py test/dsl/ast/test_mlir_gen.py test/dsl/ast/plugin/test_package.py test/dsl/ast/nodes/test_package.py test/dsl/ast/test_package.py test/dsl/ast/nodes/test_nn.py`：退出码 0，`82 passed, 1 warning in 1.49s`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/symbol_variable/test_memory_operation.py test/symbol_variable/test_memory.py`：退出码 0，`57 passed in 0.61s`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py test/kernel/test_flash_attention_symbolic_memory_genkernel.py`：退出码 0，`11 passed, 1 warning in 37.02s`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py -k tiled_matmul`：退出码 0，`1 passed, 37 deselected, 2 warnings in 2.50s`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k npu_demo_tiled_matmul_source`：退出码 0，`1 passed, 90 deselected, 2 warnings in 1.11s`。
- 九条 demo 脚本逐条执行：退出码 0；最终摘要分别为 matmul static-static `max_abs_diff=0.0009765625`、matmul static-dynamic `1.9073486328125e-06`、matmul dynamic-dynamic `1.9073486328125e-06`、conv2d static-static `1.7881393432617188e-07`、conv2d static-dynamic `6.103515625e-05`、conv2d dynamic-dynamic `7.2479248046875e-05`、flash_attention static-static `1.4901161193847656e-07`、flash_attention static-dynamic `1.1920928955078125e-07`、flash_attention dynamic-dynamic `1.1920928955078125e-07`。
合同验收：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260510-ast-kernel-operation-demos:/home/lfr/kernelcode_generate python3 -m expectation.operation.kernel`：退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260510-ast-kernel-operation-demos:/home/lfr/kernelcode_generate python3 -m expectation.dsl.mlir_gen.dialect.kernel`：退出码 0。
- `expectation` 仅作为合同验收资产单列；未把其它 expectation 当作本轮 diff 反推测试。
Diff 反推自测：
- `kernel_gen/operation/kernel/*`、`kernel_gen/operation/__init__.py`、`spec/operation/kernel.md` -> `pytest -q test/operation/kernel test/operation/test_package.py` 与 `expectation.operation.kernel`。
- `kernel_gen/dsl/ast/nodes/kernel.py`、`kernel_gen/dsl/ast/plugin/kernel.py`、`kernel_gen/dsl/ast/dsl_ast.py`、`kernel_gen/dsl/ast/*` spec -> DSL AST node/plugin/package/mlir_gen pytest 与 `expectation.dsl.mlir_gen.dialect.kernel`。
- `kernel_gen/symbol_variable/memory.py` 与 `spec/symbol_variable/*` -> `pytest -q test/symbol_variable/test_memory_operation.py test/symbol_variable/test_memory.py`。
- `kernel/matmul/*`、`kernel/conv2d/*`、`kernel/flash_attention/*` 与 `test/kernel/*` -> 三类 kernel pytest、九条 demo 脚本、matmul 相关 `dsl_run` / `gen_kernel` 子集。
- 修改 `kernel_gen/dsl/ast/nodes/nn.py` 的 result-memory 推导 -> `test/dsl/ast/nodes/test_nn.py` 与 flash_attention 三形态 pytest / 脚本。
禁止修改面与静态扫描：
- `git diff --check`：退出码 0。
- `git diff --name-only -- expectation .skills`：退出码 0，无输出，确认 `.skills` 与 `expectation/` 无 diff。
- `rg -n "\.shape\.get_shape\(" kernel/matmul kernel/conv2d kernel/flash_attention test/kernel`：退出码 1，无输出，确认目标 demo/test 不再直连 `memory.shape.get_shape()`。
- 针对本轮改动文件执行 `rg -n "getattr\(|hasattr\(|callable\(|\bobject\b" ...`：实现文件无 ctx 能力探测、无新增 `object` 函数签名；输出仅命中既有公开 package 测试中的 `hasattr/getattr` 断言、测试局部 `dict[str, object]` 和一处旧注释文本，不属于实现兼容分支。
- `rg -n "getshape\(|get_shape\([^)]" kernel_gen kernel test spec`：仅命中本轮明确新增的 `Memory.get_shape(self)`、spec 中禁止带参说明、include C++ 公开 `get_shape(axis)` 及既有未改测试文本；未新增 Python `get_shape(dim)` / `getshape(dim)` API。
- 针对本轮改动文件执行 `rg -n "from .* import .*_[A-Za-z]|\._[A-Za-z]" ...`：命中项为当前文件内私有方法调用、公开 package 测试断言、既有 `kernel_gen.operation` 子模块导入和旧实现内部方法，不存在本轮新增跨文件调用非公开 helper。
自检：
- 接口：新增公开 API 均已写入对应 spec 与文件级 API 列表；未新增计划禁止的带参 `get_shape` / `getshape`。
- 边界：kernel operation 验证 rank、dtype、layout、bool compare output、kind 类型和 img2col/matmul 形状；DSL plugin 拒绝字符串 kind 与非法参数。
- 异常：错误通过现有 `KernelCodeError` / `ErrorKind.CONTRACT` 公开失败语义抛出；未新增稳定错误文本之外的公开入口。
- 兼容性：`kernel_gen.operation` 只新增 `kernel` 子模块导出，未把 helper 名称提升到包根；现有 dma/nn/scf 导出测试仍通过。
- 实现遗漏：S1-S8 涉及 spec、实现、DSL lowering、Memory.get_shape、三类 demo 与授权 expectation 均已覆盖。
- 冗余与复用：kernel AST 通过 out-first AST node 复用公开 operation.kernel 验证；flash_attention 复用公开 nn.transpose/softmax/matmul 语义，不引入跨文件私有 helper。
- 函数粒度：新增逻辑拆在当前文件内 helper 与公开类/函数内，未新增非装饰器嵌套函数。
- 输入输出：新增测试覆盖正向 lowering、错误 kind、shape/dtype/layout mismatch、Memory.get_shape 解包/索引与九条 demo 数值输出。
- 资源/并发/性能：本轮为 AST/IR/脚本层改动，无共享全局状态变更；fixed-seed demo 保持可复现，flash_attention 规模调整到当前 npu_demo TSM 能稳定运行。
- 测试有效性：pytest 对公开 API、IR 文本、错误分支和脚本结果均有断言；demo max_abs_diff 会在错误实现时失败。
结论：
- execute 已完成，当前可流转 review。

时间：2026-05-11 00:05 +0800
经办人：提莫炖蘑菇
任务：T-20260510-afe3f1ec / ast_kernel_operation_demos_green_plan
任务目标：审查 S1-S8 的 spec/operation.kernel、kernel DSL mlir_gen、Memory.get_shape() 解包/索引、matmul/conv2d/flash_attention 三形态 demo、公开 pytest、授权 expectation 合同验收与 Diff 反推自测。
审查前同步：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260510-ast-kernel-operation-demos`。
- 已执行 `git fetch origin`。
- `HEAD=ff95b56cb5e48e394b2b763d4bf43f8ad93d48ec`，`origin/main=ff95b56cb5e48e394b2b763d4bf43f8ad93d48ec`，`git rev-list --left-right --count HEAD...origin/main` 为 `0 0`。
- worktree 与最新 `origin/main` 同基线，无需 merge/rebase；未覆盖任务 diff。
真实审查：
- 已阅读主仓计划书 `ARCHITECTURE/plan/ast_kernel_operation_demos_green_plan.md`，确认本轮授权 expectation 范围仅为 `expectation/operation/kernel/**` 与 `expectation/dsl/mlir_gen/dialect/kernel/**`，worktree 内未修改 `.skills` 与 `expectation/`。
- 已审查新增 `kernel_gen.operation.kernel` 包、DSL AST node/plugin、`Memory.get_shape(self) -> list[SymbolDim]`、三类 kernel demo 与对应 spec/test。
- 阻断 1：新增 `spec/dsl/ast/nodes/kernel.md` 的 `## 测试` 章节在执行命令后直接进入 `### 功能与用例清单`，缺少 `agents/standard/spec文件规范.md` 强制要求的 `### 测试目标` 小节。位置：`spec/dsl/ast/nodes/kernel.md:123`。
- 阻断 2：新增 `spec/dsl/ast/plugin/kernel.md` 的 `## 测试` 章节同样缺少 `### 测试目标` 小节。位置：`spec/dsl/ast/plugin/kernel.md:40`。
- 阻断 3：`kernel_gen/dsl/ast/plugin/kernel.py` 的 `_arg_or_kw(...)` 在存在 keyword 时直接覆盖同名位置参数，`_build_img2col1d(...)` / `_build_img2col2d(...)` 未拒绝位置参数与 keyword 重复传入，导致 DSL parse 接受真实公开 Python 调用会因重复参数失败的形态。复现：`kernel.img2col2d(out, input_value, kh, kw, kh=kh)` 被 `parse_function(...)` 接受并输出 `ACCEPTED`。涉及位置：`kernel_gen/dsl/ast/plugin/kernel.py:114`、`kernel_gen/dsl/ast/plugin/kernel.py:259`、`kernel_gen/dsl/ast/plugin/kernel.py:282`。
- 当前测试只覆盖 `img2col2d` keyword 正例和非法 keyword/字符串 kind，未覆盖“同一参数同时经位置与 keyword 传入应拒绝”的公开 API 边界；该缺口会让 invalid call shape 假绿。
Diff 反推审查：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/operation/kernel test/operation/test_package.py test/dsl/ast/nodes/test_kernel.py test/dsl/ast/plugin/test_kernel.py -ra --tb=short -p no:cacheprovider`：退出码 0，`22 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/ast/test_dsl_ast.py test/dsl/ast/test_mlir_gen.py test/dsl/ast/test_parser.py test/dsl/ast/nodes/test_kernel.py test/dsl/ast/plugin/test_kernel.py -ra --tb=short -p no:cacheprovider`：退出码 0，`118 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py test/kernel/test_flash_attention_symbolic_memory_genkernel.py -ra --tb=short -p no:cacheprovider`：退出码 0，`11 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/operation/nn/test_package.py test/operation/test_dma.py test/operation/test_arch.py test/operation/test_dma_alloc_lifecycle.py -ra --tb=short -p no:cacheprovider`：退出码 0，`45 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/symbol_variable/test_memory.py -ra --tb=short -p no:cacheprovider`：退出码 0，`19 passed`。
- `git diff --check`：退出码 0。
- 静态扫描 `rg -n "hasattr\(|getattr\(|callable\(|: object\b|-> object\b|def [^(]+\([^)]*object" ...`：命中项主要为公开 parser 的 `callable(fn)` 检查、package API 可达性测试和既有非本轮改动实现；本轮未发现 ctx 能力探测或新增 `object` 签名阻断。
合同验收：
- 首次在主仓目录执行授权 expectation 时，`sys.path[0]` 抢先加载主仓 `kernel_gen`，出现主仓旧代码属性缺失；该执行目录不符合待审 worktree 代码优先的验收口径，未作为合同结果。
- 在待审 worktree 目录执行 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260510-ast-kernel-operation-demos:/home/lfr/kernelcode_generate python3 -m expectation.operation.kernel`：退出码 0。
- 在待审 worktree 目录执行 `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260510-ast-kernel-operation-demos:/home/lfr/kernelcode_generate python3 -m expectation.dsl.mlir_gen.dialect.kernel`：退出码 0。
- `git status --short -- expectation .skills`：无输出；主仓 `git -C /home/lfr/kernelcode_generate status --short -- expectation .skills`：无输出。
可改进点 / 退回要求：
- 为 `spec/dsl/ast/nodes/kernel.md` 与 `spec/dsl/ast/plugin/kernel.md` 的测试章节补齐 `### 测试目标`，逐条说明该测试集合验证的公开行为。
- 在 `kernel_gen/dsl/ast/plugin/kernel.py` 中拒绝 `img2col1d/2d` 的位置参数与 keyword 重复传入，语义需对齐真实公开 Python 调用；同时补公开 pytest，覆盖 `kernel.img2col1d(out, input, k, k=...)` 与 `kernel.img2col2d(out, input, kh, kw, kh=...)` 这类重复参数应失败的边界。
- 复修后需重跑公开 pytest、授权 expectation、`git diff --check`、`.skills`/`expectation` 空 diff，并在记录中补充 Diff 反推自测。
审查结论：
- 需修改。当前仍存在可执行阻断项，不予通过；退回 execute 修复。

时间：2026-05-11 00:10 +0800
经办人：小李飞刀
任务：T-20260510-afe3f1ec / ast_kernel_operation_demos_green_plan
任务目标：修复 review 退回项：补齐 kernel AST node/plugin spec 测试目标；拒绝 img2col1d/2d 位置参数与 keyword 重复传入，并补公开 pytest。
执行前阅读记录：
- 已重新读取 `agents/codex-multi-agents/agents/小李飞刀/小李飞刀.prompt.md`、`AGENTS.md`、`agents/standard/实现文件规范.md`、`agents/standard/任务记录约定.md`。
- 已阅读本记录中 2026-05-11 00:05 review 结论，确认本轮只处理三项阻断，不扩大 diff。
- 已确认用户补充口径“如果能用 kernel 的 operation，就用”，当前 AST/plugin 继续通过 `kernel_gen.operation.kernel` 公开 operation 驱动，不引入私有 helper 或其它非公开路径。
改动：
- `spec/dsl/ast/nodes/kernel.md`：在 `## 测试` 下补 `### 测试目标`，明确 node 测试覆盖 AST 发射、便捷 elementwise lower、kind 类型边界和 operation kernel 校验复用。
- `spec/dsl/ast/plugin/kernel.md`：补 `### 测试目标`，并补充 `img2col1d/2d` 同一窗口参数不得同时以位置参数和 keyword 传入的注意事项与 TC-DSL-AST-PLUGIN-KERNEL-005。
- `kernel_gen/dsl/ast/plugin/kernel.py`：修正 `_arg_or_kw(...)`，当同一参数既有位置参数又有 keyword 时抛 `KernelCodeError`，错误文本包含 `position and keyword`。
- `test/dsl/ast/plugin/test_kernel.py`：新增 `test_kernel_plugin_rejects_img2col_duplicate_positional_keyword_parameters`，覆盖 `img2col1d(out, input, k, k=k)` 与 `img2col2d(out, input, kh, kw, kh=kh)` 应失败；补 `img2col1d` registry 可达性断言。
最小功能闭环：
- 修复点仅在 DSL AST kernel plugin 参数解析、公开 pytest 与 spec 文本；未改 operation 语义、demo、expectation 或 `.skills`。
- 重复参数现在对齐真实 Python 公开调用语义：同一参数不能同时经位置参数和 keyword 传入。
验证：
- `python3 -m py_compile kernel_gen/dsl/ast/plugin/kernel.py test/dsl/ast/plugin/test_kernel.py`：退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/ast/plugin/test_kernel.py`：退出码 0，`5 passed, 1 warning in 0.47s`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/ast/nodes/test_kernel.py test/dsl/ast/plugin/test_kernel.py test/dsl/ast/test_mlir_gen.py`：退出码 0，`63 passed, 1 warning in 0.91s`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/operation/kernel test/operation/test_package.py`：退出码 0，`14 passed in 0.46s`。
合同验收：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260510-ast-kernel-operation-demos:/home/lfr/kernelcode_generate python3 -m expectation.dsl.mlir_gen.dialect.kernel`：退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260510-ast-kernel-operation-demos:/home/lfr/kernelcode_generate python3 -m expectation.operation.kernel`：退出码 0。
Diff 反推自测：
- `kernel_gen/dsl/ast/plugin/kernel.py` + `test/dsl/ast/plugin/test_kernel.py` -> `py_compile`、`pytest -q test/dsl/ast/plugin/test_kernel.py`、扩展 DSL AST/mlir_gen 相关 pytest 子集。
- `spec/dsl/ast/nodes/kernel.md` + `spec/dsl/ast/plugin/kernel.md` -> `rg -n "position and keyword|测试目标" ...`：退出码 0，确认两个 spec 均有 `### 测试目标`，重复参数负例和错误文本落位。
- operation kernel 未改语义，但按 review 要求复跑公开 API 与授权合同：`pytest -q test/operation/kernel test/operation/test_package.py`、`expectation.operation.kernel`。
禁止修改面：
- `git diff --check`：退出码 0。
- `git diff --name-only -- expectation .skills`：退出码 0，无输出。
自检：
- 接口：未新增公开 API；只收紧已定义 img2col 参数组合错误语义，spec 已补注意事项和测试目标。
- 边界：重复位置/keyword 参数在当前文件内统一抛合同错误；未知 keyword、缺必填参数、字符串 kind 等既有边界不回退。
- 异常：新增错误通过 `KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, ...)` 抛出，pytest 锁定错误文本关键片段。
- 兼容性：合法位置参数或合法 keyword 调用仍通过；授权 expectation 全部通过。
- 冗余/复用：未新增跨文件 helper；仍通过 `kernel_gen.operation.kernel` 公开 operation 作为 AST lowering 语义真源。
- 测试有效性：新增负例会在重复参数被错误接受时失败；spec 测试目标已补齐 review 点名结构。
结论：
- review 退回项已修复，可再次流转 review。

时间：2026-05-11 00:15 +0800
经办人：提莫炖蘑菇
任务：T-20260510-afe3f1ec / ast_kernel_operation_demos_green_plan
任务目标：复审 review 退回项修复，核对公开 API、Diff 反推自测、授权 expectation 与禁止修改面。
审查前同步：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260510-ast-kernel-operation-demos`。
- 已执行 `git fetch origin`。
- `HEAD=ff95b56cb5e48e394b2b763d4bf43f8ad93d48ec`，`origin/main=ff95b56cb5e48e394b2b763d4bf43f8ad93d48ec`，`git rev-list --left-right --count HEAD...origin/main` 为 `0 0`。
- worktree 与最新 `origin/main` 同基线，无需 merge/rebase；未覆盖任务 diff。
真实审查：
- 上轮阻断 1 已修复：`spec/dsl/ast/nodes/kernel.md` 的 `## 测试` 章节已补 `### 测试目标`，并列出 AST 发射、elementwise lower、kind 类型边界和 operation kernel 校验复用目标。
- 上轮阻断 2 已修复：`spec/dsl/ast/plugin/kernel.md` 的 `## 测试` 章节已补 `### 测试目标`，并补充 `img2col1d/2d` 重复位置 / keyword 参数必须失败的公开边界。
- 上轮阻断 3 已修复：`kernel_gen/dsl/ast/plugin/kernel.py` 的 `_arg_or_kw(...)` 已在同一参数同时存在位置参数和 keyword 时抛 `KernelCodeError`；手工反证 `kernel.img2col1d(out, input, k, k=k)` 与 `kernel.img2col2d(out, input, kh, kw, kh=kh)` 均返回 `KernelCodeError kernel.img2col parameter passed by position and keyword: ...`。
- `test/dsl/ast/plugin/test_kernel.py` 已新增公开 `parse_function(...)` 负例，覆盖 `img2col1d/2d` 重复传参失败；未直连产品私有 helper。
- 未发现新增公开 API、跨文件非公开 API 使用、ctx 能力探测、`object` 签名、非装饰器嵌套函数或越权 expectation / `.skills` 改动。
Diff 反推审查：
- `python3 -m py_compile kernel_gen/dsl/ast/plugin/kernel.py test/dsl/ast/plugin/test_kernel.py`：退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/ast/plugin/test_kernel.py test/dsl/ast/nodes/test_kernel.py test/dsl/ast/test_mlir_gen.py -ra --tb=short -p no:cacheprovider`：退出码 0，`63 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/operation/kernel test/operation/test_package.py -ra --tb=short -p no:cacheprovider`：退出码 0，`14 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py test/kernel/test_flash_attention_symbolic_memory_genkernel.py -ra --tb=short -p no:cacheprovider`：退出码 0，`11 passed, 1 warning`。
- 手工重复参数反证脚本：退出码 0，输出两条 `KernelCodeError kernel.img2col parameter passed by position and keyword: k/kh`。
- 静态扫描 `rg -n "hasattr\(|getattr\(|callable\(|: object\b|-> object\b|def [^(]+\([^)]*object" ...`：命中项为公开 parser 的 `callable(fn)` 检查、package API 可达性测试、既有非本轮改动实现和测试断言；未发现本轮新增 ctx 能力探测或 `object` 签名阻断。
- `rg -n "### 测试目标|position and keyword|TC-DSL-AST-PLUGIN-KERNEL-005" spec/dsl/ast/nodes/kernel.md spec/dsl/ast/plugin/kernel.md test/dsl/ast/plugin/test_kernel.py kernel_gen/dsl/ast/plugin/kernel.py`：退出码 0，确认 spec 与测试落位。
合同验收：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260510-ast-kernel-operation-demos:/home/lfr/kernelcode_generate python3 -m expectation.operation.kernel`：退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260510-ast-kernel-operation-demos:/home/lfr/kernelcode_generate python3 -m expectation.dsl.mlir_gen.dialect.kernel`：退出码 0。
- `git diff --check`：退出码 0。
- `git diff --name-only -- expectation .skills`、`git ls-files --others --exclude-standard -- expectation .skills` 与主仓 `git -C /home/lfr/kernelcode_generate status --short -- expectation .skills` 均无输出。
自检：
- 特殊情况：上轮复现的重复位置 / keyword 参数已由实现和公开 pytest 覆盖；合法 keyword 和合法位置参数路径未被收窄。
- 完整性：spec 测试目标、实现错误分支、公开 pytest、授权 expectation 和禁止修改面均已复核。
- 维护性：修复局限在当前文件 helper，不新增跨文件私有依赖；错误语义通过 `KernelCodeError(ErrorKind.CONTRACT, ErrorModule.AST, ...)` 保持一致。
- 扩展性：后续 img2col 新增参数时需继续在 `_arg_or_kw(...)` 调用处保持“同名参数不可重复”约束。
- 测试有效性：新增负例会在重复参数被错误接受时失败；授权 expectation 仍覆盖 operation/kernel 与 DSL mlir_gen 主合同。
结论：
- 通过。上轮三项阻断均已修复，当前未发现剩余可执行改进项；本任务为计划级任务，review 通过后应进入架构复核 / 终验，不直接进入 merge。

时间：2026-05-11 00:25 +0800
经办人：守护最好的爱莉希雅
任务：T-20260510-afe3f1ec / ast_kernel_operation_demos_green_plan
任务目标：计划级架构复核 / 终验，复核 S1-S8 的 spec、公开 API、kernel DSL mlir_gen、Memory.get_shape()、三形态 demo、授权 expectation、公开 pytest、脚本、Diff 反推测试、禁止修改面与静态扫描。
同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260510-ast-kernel-operation-demos`。
- 已执行 `git fetch --prune origin`。
- `HEAD=ff95b56cb5e48e394b2b763d4bf43f8ad93d48ec`。
- `origin/main=ff95b56cb5e48e394b2b763d4bf43f8ad93d48ec`。
- worktree 与 latest `origin/main` 同基线，无需 merge/rebase，未覆盖任务 diff。
- worktree 内缺 `ARCHITECTURE/plan/ast_kernel_operation_demos_green_plan.md`，本次按既有任务记录口径只读引用主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/ast_kernel_operation_demos_green_plan.md` 作为合同真源，未复制、未新建、未修改计划资产。
复核范围：
- S1：`spec/operation/kernel.md`、`spec/symbol_variable/memory.md`、`spec/dsl/ast/*` 已承接 kernel operation 与 `Memory.get_shape()` 合同。
- S2：`kernel_gen.operation.kernel` 新增 out-first API，`kernel_gen.operation` 仅导出 `kernel` 子模块，不把 helper 上提到包根。
- S3：kernel DSL AST node/plugin 已接入，`kernel.add/sub/...` lower 到 `kernel.binary_elewise`，`kernel.matmul/img2col1d/img2col2d` lower 到对应 kernel dialect op。
- S4：`Memory.get_shape(self) -> list[SymbolDim]` 已落地；手工检查 `Memory(["M", "K"], NumericType.Float32).get_shape()` 返回 `list` 且元素均为 `SymbolDim`；`mem.get_shape(0)` 因签名不接受带参调用而抛 `TypeError`。
- S5-S7：matmul、conv2d、flash_attention 三形态 demo 均已复跑脚本并通过。
- S8：公开 pytest、授权 expectation、脚本、diff check、禁止修改面与静态扫描均已复核。
合同验收：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260510-ast-kernel-operation-demos:/home/lfr/kernelcode_generate python3 -m expectation.operation.kernel`：退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260510-ast-kernel-operation-demos:/home/lfr/kernelcode_generate python3 -m expectation.dsl.mlir_gen.dialect.kernel`：退出码 0。
- worktree 内 `expectation/` 不携带合同资产文件，本次 expectation 使用 worktree code + 主仓只读 expectation 资产执行。
- `git diff --name-only -- expectation .skills`：无输出。
- `git ls-files --others --exclude-standard -- expectation .skills`：无输出。
- 主仓 `/home/lfr/kernelcode_generate` 中 `git status --short -- expectation .skills`：无输出。
- 结论：未发现未授权 expectation 或 `.skills` diff；expectation 修改范围没有超出授权，实际本轮 worktree 未落盘修改 expectation。
公开 pytest / 脚本：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/operation/kernel test/operation/test_package.py`：`14 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/ast/plugin/test_kernel.py test/dsl/ast/nodes/test_kernel.py test/dsl/ast/test_mlir_gen.py test/dsl/ast/plugin/test_package.py test/dsl/ast/nodes/test_package.py test/dsl/ast/test_package.py test/dsl/ast/nodes/test_nn.py`：`83 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/symbol_variable/test_memory_operation.py test/symbol_variable/test_memory.py`：`57 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py test/kernel/test_flash_attention_symbolic_memory_genkernel.py`：`11 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py -k tiled_matmul`：`1 passed, 37 deselected, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k npu_demo_tiled_matmul_source`：`1 passed, 90 deselected, 2 warnings`。
- 九条 demo 脚本逐条执行通过：`kernel/matmul/inputs_static_tile_static.py`、`kernel/matmul/inputs_static_tile_dynamic.py`、`kernel/matmul/inputs_dynamic_tile_dynamic.py`、`kernel/conv2d/inputs_static_tile_static.py`、`kernel/conv2d/inputs_static_tile_dynamic.py`、`kernel/conv2d/inputs_dynamic_tile_dynamic.py`、`kernel/flash_attention/inputs_static_tile_static.py`、`kernel/flash_attention/inputs_static_tile_dynamic.py`、`kernel/flash_attention/inputs_dynamic_tile_dynamic.py`。
- 脚本摘要：matmul 三形态、conv2d 三形态、flash_attention 三形态均输出 `[CHECK] ... max_abs_diff=...` 并退出 0；动态 conv2d 脚本同时确认 memory-pool 形态中 `arch.get_dynamic_memory + dma.view` 存在且 `dma.alloc/allalloc` 缺失。
Diff 反推与静态扫描：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX=/tmp/kernelcode_generate_t20260510_arch_pycache python3 -m py_compile ...` 覆盖 kernel operation、kernel DSL AST、Memory、三类脚本和 flash_attention pytest：退出码 0。
- `git diff --check`：退出码 0。
- `rg -n "lhs\.getshape\(|getshape\(" kernel_gen test kernel spec`：只命中 spec 中“不支持 / 不提供 getshape(dim)”说明，未发现实现或测试新增 `lhs.getshape(dim)`。
- `rg -n "def .*get_shape\([^)]*\)" kernel_gen/symbol_variable/memory.py kernel_gen/dsl/ast kernel_gen/operation test`：仅命中 `kernel_gen/symbol_variable/memory.py` 中 `def get_shape(self: "Memory") -> list[SymbolDim]`，未发现 Python `get_shape(dim)` 带参重载。
- 针对本轮改动文件扫描 `hasattr/getattr/callable/object`：命中项限于 package API 可达性测试、既有公开 parser 检查或非本轮实现，不构成本轮 ctx 能力探测 / object 签名阻断。
- 针对新增核心文件检查非装饰器嵌套函数：`kernel_gen/dsl/ast/plugin/kernel.py`、`kernel_gen/dsl/ast/nodes/kernel.py`、`kernel_gen/operation/kernel/elementwise.py`、`kernel_gen/operation/kernel/structured.py` 均无嵌套函数。
- 针对文件级说明 / API 列表扫描：`kernel_gen/operation/kernel/**`、`kernel_gen/dsl/ast/nodes/kernel.py`、`kernel_gen/dsl/ast/plugin/kernel.py`、`kernel_gen/symbol_variable/memory.py` 均包含文件级 `功能说明 / API 列表 / 使用示例 / 关联文件`，spec 中 `KernelBinaryElewiseKind` 与 `Memory.get_shape(self) -> list[SymbolDim]` 的签名已落位。
边界结论：
- 未实现 `lhs.getshape(dim)` 或 `get_shape(dim)` 带参重载。
- 未发现测试直连新增非 API helper。
- 未发现本轮新增跨文件非公开 API 依赖；静态扫描中带下划线命中主要为当前文件内私有方法、公开模块本地别名或既有测试断言，不构成阻断。
- 授权 expectation 只作为合同验收运行；除授权目录外无 expectation 改动。
终验结论：
- 通过。
- 最小阻断项：无。
- 可进入双架构通过后的 merge 前置流程。

时间：2026-05-11 00:37 +0800
经办人：李白
任务：T-20260510-afe3f1ec / ast_kernel_operation_demos_green_plan
任务目标：merge 前收口复核，确认 latest 同步、双架构终验记录、授权 expectation 范围、公开 pytest、九条 demo 脚本、`git diff --check`、禁止修改面与静态扫描后合并。

merge 前同步：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260510-ast-kernel-operation-demos`。
- 已执行主仓 `git fetch --prune origin`。
- worktree 分支：`task/ast-kernel-operation-demos`。
- `HEAD=ff95b56cb5e48e394b2b763d4bf43f8ad93d48ec`。
- `origin/main=ff95b56cb5e48e394b2b763d4bf43f8ad93d48ec`。
- `git rev-list --left-right --count HEAD...origin/main` 输出 `0 0`，worktree 与 latest main 同基线；未 merge/rebase，未覆盖任务 diff。

真实差异与记录复核：
- 已复核任务记录中 execute、review 退回、修复、复审与两位架构计划级终验记录；最终结论均为通过，最小阻断项无。
- 当前待合入 diff 覆盖 `kernel/` 九条 demo 脚本、`kernel_gen/dsl/ast` kernel node/plugin 接线、`kernel_gen/operation/kernel/`、`kernel_gen/symbol_variable/memory.py`、对应 `spec/` 与公开 `test/`；任务记录文件为本次新增记录资产。
- 未暂存或合入 `.skills` 改动。
- `git status --short -- expectation .skills`、`git diff --name-only -- expectation .skills`、`git ls-files --others --exclude-standard -- expectation .skills` 均无输出。
- `find /home/lfr/kernelcode_generate/expectation -type f -newermt '2026-05-10 22:00:00'` 无输出；本次 merge 未发现任务开始后新增非授权 expectation 文件。
- 授权 expectation 目录仍由主仓只读资产承载，`git check-ignore -v expectation/operation/kernel/__main__.py expectation/dsl/mlir_gen/dialect/kernel/__main__.py` 均命中 `.gitignore:21:expectation`；本次不把 expectation 当作普通任务 diff 暂存。

merge 前 gate：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260510-ast-kernel-operation-demos:/home/lfr/kernelcode_generate python3 -m expectation.operation.kernel`：退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260510-ast-kernel-operation-demos:/home/lfr/kernelcode_generate python3 -m expectation.dsl.mlir_gen.dialect.kernel`：退出码 0。
- `git diff --check`：退出码 0。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/operation/kernel test/operation/test_package.py -ra --tb=short -p no:cacheprovider`：`14 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/ast/plugin/test_kernel.py test/dsl/ast/nodes/test_kernel.py test/dsl/ast/test_mlir_gen.py test/dsl/ast/plugin/test_package.py test/dsl/ast/nodes/test_package.py test/dsl/ast/test_package.py test/dsl/ast/nodes/test_nn.py -ra --tb=short -p no:cacheprovider`：`83 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/symbol_variable/test_memory_operation.py test/symbol_variable/test_memory.py -ra --tb=short -p no:cacheprovider`：`57 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py test/kernel/test_flash_attention_symbolic_memory_genkernel.py -ra --tb=short -p no:cacheprovider`：`11 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py -k tiled_matmul -ra --tb=short -p no:cacheprovider`：`1 passed, 37 deselected, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k npu_demo_tiled_matmul_source -ra --tb=short -p no:cacheprovider`：`1 passed, 90 deselected, 2 warnings`。
- 九条 demo 脚本逐条执行退出码 0：`kernel/matmul/inputs_static_tile_static.py`、`kernel/matmul/inputs_static_tile_dynamic.py`、`kernel/matmul/inputs_dynamic_tile_dynamic.py`、`kernel/conv2d/inputs_static_tile_static.py`、`kernel/conv2d/inputs_static_tile_dynamic.py`、`kernel/conv2d/inputs_dynamic_tile_dynamic.py`、`kernel/flash_attention/inputs_static_tile_static.py`、`kernel/flash_attention/inputs_static_tile_dynamic.py`、`kernel/flash_attention/inputs_dynamic_tile_dynamic.py`。
- `python3 -m py_compile` 覆盖 kernel operation、kernel DSL AST、Memory 与九条 demo 脚本：退出码 0。

静态扫描与禁止修改面：
- `rg -n "def get_shape\(self,|def getshape\(|lhs\.getshape\(|lhs\.get_shape\([^)]*dim|\.getshape\(" kernel_gen test spec kernel`：仅命中 `spec/dsl/ast/parser.md` 中“不支持 `memory.get_shape(dim)` 或 `memory.getshape(dim)`”说明；未发现实现或测试新增带参 `lhs.getshape(dim)` / `get_shape(dim)`。
- `rg -n "def get_shape\([^)]*\)" kernel_gen test spec kernel`：仅命中既有 `kernel_gen/symbol_variable/symbol_shape.py:239 def get_shape(self)` 与本轮 `kernel_gen/symbol_variable/memory.py:244 def get_shape(self: "Memory") -> list[SymbolDim]`；未发现带参重载。
- `rg -n "hasattr\([^)]*ctx|getattr\([^)]*ctx|callable\(getattr\([^)]*ctx|: object\b|-> object\b|def [^(]+\([^)]*object" ...` 针对本轮核心实现与测试无输出。
- 本次 merge 阶段未修改实现 / spec / test，仅做同步、复核、记录与后续合并。

merge 结论：
- 合并前 gate 通过，授权范围未超出，未发现 `.skills` 或未授权 expectation diff。
- 可暂存任务 diff 与记录文件并执行 merge/push/-done。

时间：2026-05-11 00:39 +0800
经办人：李白
任务：T-20260510-afe3f1ec / ast_kernel_operation_demos_green_plan
任务目标：执行主仓快进合并与推送，并准备共享状态 -done。

合并与推送：
- 在 worktree `task/ast-kernel-operation-demos` 暂存任务 diff 与本记录文件；确认 `git diff --cached --name-only -- expectation .skills ARCHITECTURE/plan agents/standard TODO.md DONE.md` 无输出。
- 执行 `git diff --cached --check`：退出码 0。
- 生成任务分支提交：`a64a868a32e6d06f718cc402112baa7f6e980e98`（`T-20260510-afe3f1ec merge ast kernel operation demos`）。
- 在主仓 `/home/lfr/kernelcode_generate` 执行 `git merge --ff-only task/ast-kernel-operation-demos`：快进成功。
- 执行 `git push origin main`：成功，`origin/main` 已更新到 `a64a868a32e6d06f718cc402112baa7f6e980e98`。
- 主仓 `git rev-parse HEAD` 与 `git rev-parse origin/main` 均为 `a64a868a32e6d06f718cc402112baa7f6e980e98`。

状态：
- 业务 diff 已合入并推送。
- 待执行共享状态 `-done`；执行前补录本段真实合并记录。

时间：2026-05-11 00:41 +0800
经办人：李白
任务：T-20260510-afe3f1ec / ast_kernel_operation_demos_green_plan
任务目标：执行 `-done` 并回收已完成 worktree / 本地任务分支。

共享状态：
- 执行 `bash skills/codex-multi-agents/scripts/codex-multi-agents-task.sh -file TODO.md -done -task_id T-20260510-afe3f1ec -log agents/codex-multi-agents/log/task_records/2026/19/20260510-ast-kernel-operation-demos.md -agents-list agents/codex-multi-agents/agents-lists.md`。
- 脚本输出：`OK: done T-20260510-afe3f1ec`、`OK: replace 李白 状态`。
- `rg -n "T-20260510-afe3f1ec|ast-kernel-operation-demos" TODO.md DONE.md agents/codex-multi-agents/agents-lists.md`：DONE.md 中存在该任务 `已完成` 记录，完成时间 `2026-05-11 00:40:55 +0800`；TODO.md 中未再命中该任务。

清理：
- 清理前 `git -C /home/lfr/kernelcode_generate/wt-20260510-ast-kernel-operation-demos status --porcelain --branch`：`## task/ast-kernel-operation-demos...origin/main [behind 1]`，无未提交或未跟踪任务资产。
- `git merge-base --is-ancestor task/ast-kernel-operation-demos origin/main`：退出码 0，确认任务分支已并入远端主线。
- 执行 `git worktree remove /home/lfr/kernelcode_generate/wt-20260510-ast-kernel-operation-demos`：成功。
- 执行 `git branch -d task/ast-kernel-operation-demos`：成功，删除本地任务分支 `a64a868a`。
- `git worktree list` 仅剩主仓 `/home/lfr/kernelcode_generate 695d6282 [main]`。
- `git branch --list 'task/ast-kernel-operation-demos' -vv`：无输出。
- 主仓 `git status --short --branch`：`## main...origin/main`，清理后无未提交改动。

时间：2026-05-11 00:27 +0800
经办人：大闸蟹
任务：T-20260510-afe3f1ec / ast_kernel_operation_demos_green_plan
任务目标：第二架构复核 / 终验，复核 S1-S8、授权 expectation、公开 pytest、九条 kernel demo 脚本、Diff 反推测试、禁止修改面与静态边界。

同步现场：
- 执行目录：`/home/lfr/kernelcode_generate/wt-20260510-ast-kernel-operation-demos`。
- 已执行 `git fetch --prune`。
- `HEAD=ff95b56cb5e48e394b2b763d4bf43f8ad93d48ec`。
- `origin/main=ff95b56cb5e48e394b2b763d4bf43f8ad93d48ec`。
- `merge-base=ff95b56cb5e48e394b2b763d4bf43f8ad93d48ec`，`HEAD...origin/main=0/0`。
- worktree 内缺计划资产，按任务记录既有口径只读引用主仓共享计划 `/home/lfr/kernelcode_generate/ARCHITECTURE/plan/ast_kernel_operation_demos_green_plan.md`，未复制、未新建、未修改计划资产。

合同验收：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260510-ast-kernel-operation-demos:/home/lfr/kernelcode_generate python3 -m expectation.operation.kernel`：退出码 0；operation/kernel elewise arithmetic、elewise compare、img2col1d、img2col2d、matmul 合同均通过。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260510-ast-kernel-operation-demos:/home/lfr/kernelcode_generate python3 -m expectation.dsl.mlir_gen.dialect.kernel`：退出码 0；kernel dialect mlir_gen elementwise arithmetic、elementwise compare、img2col1d、img2col2d、matmul 合同均通过。
- worktree 不携带 `expectation/` 目录；本次以 worktree code + 主仓只读 expectation 资产执行。
- 主仓只读 expectation 近时段变更核对仅命中授权范围 `expectation/operation/kernel/**` 与 `expectation/dsl/mlir_gen/dialect/kernel/**`；未发现其它 expectation 范围作为本任务 diff。
- `git diff --check`：退出码 0。
- `git diff --name-only -- .skills`、`git status --short -- expectation .skills`、`git ls-files --others --exclude-standard -- expectation .skills`：均无未授权输出。

公开 pytest 与脚本：
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/operation/kernel test/operation/test_package.py -ra --tb=short -p no:cacheprovider`：`14 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/ast/plugin/test_kernel.py test/dsl/ast/nodes/test_kernel.py test/dsl/ast/test_mlir_gen.py -ra --tb=short -p no:cacheprovider`：`63 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/symbol_variable/test_memory_operation.py test/symbol_variable/test_memory.py -ra --tb=short -p no:cacheprovider`：`57 passed`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/kernel/test_matmul_symbolic_memory_genkernel.py test/kernel/test_conv2d_symbolic_memory_genkernel.py test/kernel/test_flash_attention_symbolic_memory_genkernel.py -ra --tb=short -p no:cacheprovider`：`11 passed, 1 warning`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/tools/test_dsl_run.py -k tiled_matmul -ra --tb=short -p no:cacheprovider`：`1 passed, 37 deselected, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/gen_kernel/test_gen_kernel.py -k npu_demo_tiled_matmul_source -ra --tb=short -p no:cacheprovider`：`1 passed, 90 deselected, 2 warnings`。
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q test/dsl/ast/test_package.py test/dsl/ast/nodes/test_package.py test/dsl/ast/plugin/test_package.py -ra --tb=short -p no:cacheprovider`：`3 passed, 1 warning`。
- 九条 demo 脚本均退出 0：`kernel/matmul/inputs_static_tile_static.py`、`kernel/matmul/inputs_static_tile_dynamic.py`、`kernel/matmul/inputs_dynamic_tile_dynamic.py`、`kernel/conv2d/inputs_static_tile_static.py`、`kernel/conv2d/inputs_static_tile_dynamic.py`、`kernel/conv2d/inputs_dynamic_tile_dynamic.py`、`kernel/flash_attention/inputs_static_tile_static.py`、`kernel/flash_attention/inputs_static_tile_dynamic.py`、`kernel/flash_attention/inputs_dynamic_tile_dynamic.py`；均输出 `[CHECK] ... max_abs_diff=...`。
- matmul 三形态脚本和 `test/kernel/test_matmul_symbolic_memory_genkernel.py` 复核 K/reduce tile 使用 accumulator：`fill(acc, 0)`、K loop 内 `matmul`、`add(acc, partial)`、先写回 accumulator、最终写回 output，未发现 partial 覆盖 output。

边界与静态扫描：
- `python3 -m py_compile` 覆盖 kernel operation、kernel DSL AST、Memory、flash_attention 脚本与 pytest：退出码 0。
- `rg -n "def get_shape\(self,|def getshape\(|getshape\(" kernel_gen`：无输出；未实现 Python `getshape(dim)` 或 `get_shape(dim)` 带参重载。
- `rg -n "lhs\.getshape\(|lhs\.get_shape\([^)]*\)" kernel_gen test spec kernel`：仅命中 `lhs.get_shape()` / `lhs.get_shape()[idx]` 的无参解包和索引用法，未发现 `lhs.getshape(dim)` 或 `lhs.get_shape(dim)`。
- Diff 静态扫描未发现本轮新增 `ctx` 能力探测、跨文件私有导入、`object` 签名或非装饰器嵌套函数阻断。
- 文件级说明 / API 列表与 spec/API 核对通过：`kernel_gen.operation.kernel`、kernel DSL AST node/plugin、`Memory.get_shape(self) -> list[SymbolDim]` 均已按公开 API 边界落位。

终验结论：
- 通过。
- 最小阻断项：无。
- 可进入双架构通过后的 merge 前置流程。
