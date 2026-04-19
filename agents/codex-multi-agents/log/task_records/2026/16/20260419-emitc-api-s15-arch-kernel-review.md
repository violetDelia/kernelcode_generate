时间：2026-04-20 02:44 +0800
经办人：提莫炖蘑菇
任务：T-20260419-f6efa359
任务目标：复核 Arch / Kernel codegen 黑盒合同、旧公开名删减与 include/api 分层是否一致
改动：本轮仅做审查。复核范围：[`include/npu_demo/npu_demo.h`](../../../../../../include/npu_demo/npu_demo.h)、[`include/api/Kernel.h`](../../../../../../include/api/Kernel.h)、[`include/npu_demo/Kernel.h`](../../../../../../include/npu_demo/Kernel.h)、[`spec/include/npu_demo/npu_demo.md`](../../../../../../spec/include/npu_demo/npu_demo.md)、[`spec/include/api/Kernel.md`](../../../../../../spec/include/api/Kernel.md)、[`kernel_gen/dsl/gen_kernel.py`](../../../../../../kernel_gen/dsl/gen_kernel.py)、[`test/include/api/test_kernel.py`](../../../../../../test/include/api/test_kernel.py)、[`test/dsl/test_emit_c.py`](../../../../../../test/dsl/test_emit_c.py)、[`test/dsl/test_gen_kernel.py`](../../../../../../test/dsl/test_gen_kernel.py)。问题列表：1）[P1] 文件/接口：[`test/dsl/test_gen_kernel.py`](../../../../../../test/dsl/test_gen_kernel.py:1547)（`test_gen_kernel_compiles_npu_demo_tiled_matmul_source`）、[`kernel_gen/dsl/gen_kernel.py`](../../../../../../kernel_gen/dsl/gen_kernel.py)、[`include/npu_demo/Dma.h`](../../../../../../include/npu_demo/Dma.h:132)。现象：`pytest -q test/dsl/test_gen_kernel.py -k "npu_demo"` 失败，生成 C++ 代码中 `slice(..., {i0, c_0_1}, {c_16_1, c_16_2}, {c_1, c_1_1})` 仍以 brace-list 传参，无法匹配 `slice(..., const Vector&, const Vector&, const Vector&)`；同时同一作用域重复声明 `S_INT c_16` 与 `S_INT c_1`。风险：S15 明确要求通过 `npu_demo` codegen 黑盒复核，当前 `gen_kernel` 产物无法通过编译检查，不能认定 Arch/Kernel 链路已收口。建议：回到 `build` 修复 `gen_kernel` 的 npu_demo 生成文本，统一 `slice/deslice` 为 `Vector` 口径并消除重复 `symbol.const` 变量定义，然后再回 review。漏洞排查结果：- 输入校验绕过：未见新增绕过；`test/include/api/test_kernel.py` 通过，公开参数顺序仍受约束。- 类型/形状绕过：发现问题；`slice` 参数类型与 `Vector` 合同不一致，触发编译失败。- 边界越界：未见新增越界；`include/npu_demo/npu_demo.h` 未重新聚合 `Nn.h`，分层边界仍符合当前文档。- 错误处理缺失：发现问题；`gen_kernel` 生成代码在 `npu_demo` 路径下未生成可编译参数形态。- 状态污染：发现问题；重复 `S_INT c_16/c_1` 声明导致同作用域污染。- 资源释放问题：本轮未见新增资源释放风险。改进建议：未发现额外改进点（除上述必须修改项外）。
验证：`python3 -m pytest -q test/include/api/test_kernel.py` -> `3 passed`；`bash script/run-npu-demo-s11-add-barrier-expectation.sh` -> `exit 0`；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/lfr/kernelcode_generate/wt-20260419-emitc-api-s12-kernel-emitc-build:/home/lfr/kernelcode_generate python3 -m expectation.dsl.emit_c.npu_demo.kernel` -> `exit 0`；`python3 -m pytest -q test/dsl/test_emit_c.py -k "kernel and npu_demo"` -> `1 passed`；`python3 -m pytest -q test/dsl/test_gen_kernel.py -k "npu_demo"` -> `1 failed, 23 passed, 35 deselected`（失败项：`test_gen_kernel_compiles_npu_demo_tiled_matmul_source`）；`git -C /home/lfr/kernelcode_generate/wt-20260419-emitc-api-s15-arch-kernel-review diff --check` -> 通过。
结论：需修改。下一步建议创建 `build` 任务，任务目标：修复 npu_demo matmul codegen 的 `slice/deslice` 参数形态与 `symbol.const` 重复定义问题，并补齐对应回归后再回 review。

时间：2026-04-20 02:50 +0800
经办人：小李飞刀
任务：T-20260419-f6efa359
任务目标：修复 npu_demo matmul codegen 中 `slice/deslice` 参数与 `Vector` 合同不一致、`symbol.const` 重复定义问题，并补齐回归
改动：1）更新 [`kernel_gen/dsl/emit_c.py`](../../../../../../kernel_gen/dsl/emit_c.py)，将 `target=npu_demo` 下多维 `dma.slice` 从 brace-list 调用改为 `Vector` 绑定调用，保证与 [`include/npu_demo/Dma.h`](../../../../../../include/npu_demo/Dma.h) 的 `const Vector&` 合同一致；同时将 `symbol.const` 在 `npu_demo` 路径切换为 `_emit_npu_symbol_const_stmt` 去重发射，避免同作用域重复定义 `S_INT c_16/c_1`。2）更新 [`test/dsl/test_emit_c.py`](../../../../../../test/dsl/test_emit_c.py) 的 `test_emit_c_lowers_npu_demo_tiled_matmul_pipeline`，将二维 `slice` 断言从 brace-list 文本改为 `Vector` 绑定与调用链断言，锁定新合同。
验证：`python3 -m pytest -q test/dsl/test_emit_c.py -k "npu_demo and (symbol_const_cast_and_to_float or symbol_for or slice_deslice_add_pipeline or tiled_matmul_pipeline)"` -> `4 passed, 24 deselected`；`python3 -m pytest -q test/dsl/test_gen_kernel.py -k "npu_demo"` -> `24 passed, 35 deselected`。
结论：当前 build 已完成，`slice/deslice` 与 `Vector` 合同一致，`symbol.const` 重复定义问题已消除，回归通过；下一步建议进入 `review` 复核收口结果。

时间：2026-04-20 02:53 +0800
经办人：提莫炖蘑菇
任务：T-20260419-f6efa359
任务目标：复核 npu_demo matmul codegen 的 slice/deslice Vector 合同与 symbol.const 去重修复及回归结果
改动：本轮仅做审查。复核范围：[`kernel_gen/dsl/emit_c.py`](../../../../../../kernel_gen/dsl/emit_c.py)、[`test/dsl/test_emit_c.py`](../../../../../../test/dsl/test_emit_c.py)、[`test/dsl/test_gen_kernel.py`](../../../../../../test/dsl/test_gen_kernel.py)、[`include/npu_demo/Dma.h`](../../../../../../include/npu_demo/Dma.h)、[`spec/include/api/Dma.md`](../../../../../../spec/include/api/Dma.md)、[`spec/dsl/emit_c.md`](../../../../../../spec/dsl/emit_c.md)。
问题列表：
1. [P1] 文件/接口：[`kernel_gen/dsl/emit_c.py`](../../../../../../kernel_gen/dsl/emit_c.py:1370) - [`kernel_gen/dsl/emit_c.py`](../../../../../../kernel_gen/dsl/emit_c.py:1379)。现象：`_emit_npu_deslice_stmt` 的功能说明仍写“brace-list 文本”，但当前实现已经改为 `Vector` 绑定发射。风险：函数说明与实际行为不一致，后续维护者会按过时口径理解 `deslice`，与 [`spec/include/api/Dma.md`](../../../../../../spec/include/api/Dma.md) 的 `Vector` 合同不一致。建议：同步把 `deslice` 说明改成 `Vector` 绑定，与 `slice` 说明保持一致。
2. [P1] 文件/接口：[`test/dsl/test_emit_c.py`](../../../../../../test/dsl/test_emit_c.py:1323) - [`test/dsl/test_emit_c.py`](../../../../../../test/dsl/test_emit_c.py:1327)。现象：新增 `test_emit_c_lowers_npu_demo_tiled_matmul_pipeline` 的元信息仍写 `最近一次运行成功时间: N/A`，但本轮已复跑并通过。风险：测试元信息未同步，不能直接作为“最新验证成功”证据，也不满足测试文件约定。建议：把成功时间更新为本轮实际验证时间，并保留对应命令。
漏洞排查结果：
- 输入校验绕过：未见新增绕过；`pytest -q test/dsl/test_emit_c.py -k "npu_demo and (symbol_const_cast_and_to_float or symbol_for or slice_deslice_add_pipeline or tiled_matmul_pipeline)"` 与 `pytest -q test/dsl/test_gen_kernel.py -k "npu_demo"` 均已通过，参数边界未再出现失败。
- 类型/形状绕过：功能性问题已解除；`slice/deslice` 运行时路径已与 `Vector` 合同一致。
- 边界越界：未见新增越界；`git -C /home/lfr/kernelcode_generate/wt-20260419-emitc-api-s15-arch-kernel-review diff --check` 通过。
- 错误处理缺失：未见新增错误处理回退。
- 状态污染：`symbol.const` 重复定义问题已消除，当前未见同作用域污染。
- 资源释放问题：本轮未见新增资源释放风险。
验证：
- `python3 -m pytest -q /home/lfr/kernelcode_generate/wt-20260419-emitc-api-s15-arch-kernel-review/test/dsl/test_emit_c.py -k "npu_demo and (symbol_const_cast_and_to_float or symbol_for or slice_deslice_add_pipeline or tiled_matmul_pipeline)"` -> `4 passed, 24 deselected, 8 warnings in 0.34s`
- `python3 -m pytest -q /home/lfr/kernelcode_generate/wt-20260419-emitc-api-s15-arch-kernel-review/test/dsl/test_gen_kernel.py -k "npu_demo"` -> `24 passed, 35 deselected, 8 warnings in 1.82s`
- `git -C /home/lfr/kernelcode_generate/wt-20260419-emitc-api-s15-arch-kernel-review diff --check` -> 通过
结论：需修改。功能回归已通过，但文案与测试元信息未同步，当前还不能判定收口。

时间：2026-04-20 02:55 +0800
经办人：小李飞刀
任务：T-20260419-f6efa359
任务目标：同步 npu_demo matmul codegen 的 `_emit_npu_deslice_stmt` 文案与测试元信息，修正最近一次运行成功时间并补齐说明
改动：1）更新 [`kernel_gen/dsl/emit_c.py`](../../../../../../kernel_gen/dsl/emit_c.py) 中 `_emit_npu_deslice_stmt` 文案：将功能说明改为“一维标量调用 + 多维 Vector 绑定调用”，删除旧的 brace-list 口径，并同步最后一次更改人为 `小李飞刀`。2）更新 [`test/dsl/test_emit_c.py`](../../../../../../test/dsl/test_emit_c.py) 的 `EC-020` 元信息：将“最近一次运行测试时间/最近一次运行成功时间”统一更新为 `2026-04-20 02:54:53 +0800`，并补齐“多维 slice/deslice 采用 Vector 合同、避免回退 brace-list 文本”的说明。
验证：`python3 -m pytest -q test/dsl/test_emit_c.py -k test_emit_c_lowers_npu_demo_tiled_matmul_pipeline` -> `1 passed, 27 deselected`；`python3 -m pytest -q test/dsl/test_gen_kernel.py -k test_gen_kernel_compiles_npu_demo_tiled_matmul_source` -> `1 passed, 58 deselected`。
结论：本轮 build 已完成，`_emit_npu_deslice_stmt` 文案与新测试元信息已与当前实现一致；下一步建议进入 `review` 复核。

时间：2026-04-20 02:59 +0800
经办人：不要啊教练
任务：T-20260419-f6efa359
任务目标：复核 `_emit_npu_deslice_stmt` 文案与 EC-020 测试元信息是否与当前 Vector 合同实现对齐
改动：本轮仅做审查。确认 [`kernel_gen/dsl/emit_c.py`](../../../../../../kernel_gen/dsl/emit_c.py) 中 `_emit_npu_deslice_stmt` 文案与 [`test/dsl/test_emit_c.py`](../../../../../../test/dsl/test_emit_c.py) 的 EC-020 元信息已切到 Vector 口径；同时发现本轮额外切换 `symbol.const` 分发后，npu_demo 的 DMA 索引 helper 输出发生连带变化。
验证：`pytest -q test/dsl/test_emit_c.py -k 'test_emit_c_lowers_npu_demo_slice_deslice_add_pipeline or test_emit_c_lowers_npu_demo_tiled_matmul_pipeline'` -> `2 passed`；`pytest -q test/dsl/test_emit_c.py` -> `1 failed, 27 passed, 8 warnings in 0.39s`，失败项为 `test_emit_c_lowers_npu_demo_dma_indexed_and_fill_helpers`，实际输出已从 brace-list 口径切换为命名常量口径。
结论：需修改。建议恢复与本任务无关的 `symbol.const` 旧分发/短路行为，避免扩大到 DMA 索引 helper 的输出，再回审。

时间：2026-04-20 03:01 +0800
经办人：小李飞刀
任务：T-20260419-f6efa359
任务目标：恢复 npu_demo 侧 `symbol.const` 旧分发/短路行为，避免文案同步连带改变 DMA 索引 helper 输出
改动：更新 [`kernel_gen/dsl/emit_c.py`](../../../../../../kernel_gen/dsl/emit_c.py)：1）`emit_c_op` 在 `target=npu_demo` 下将 `symbol.const` 分发恢复为 `_emit_symbol_const_stmt`，恢复 `DmaLoad/DmaStore` 纯索引常量短路行为；2）为 `_emit_symbol_const_stmt` 增加同名常量避冲突分支（命中已有同名时使用 `_bind_preferred_name`），避免同作用域重复定义导致编译失败。`_emit_npu_deslice_stmt` 文案与 `EC-020` 元信息同步结果保持不变。
验证：`python3 -m pytest -q test/dsl/test_emit_c.py -k "test_emit_c_lowers_npu_demo_dma_indexed_and_fill_helpers or test_emit_c_lowers_npu_demo_tiled_matmul_pipeline or test_emit_c_op_lowers_npu_demo_symbol_const_cast_and_to_float"` -> `3 passed, 25 deselected`；`python3 -m pytest -q test/dsl/test_gen_kernel.py -k "test_gen_kernel_compiles_npu_demo_tiled_matmul_source"` -> `1 passed, 58 deselected`。
结论：本轮 build 已完成，DMA 索引 helper 输出已恢复旧口径，且 npu_demo tiled matmul 编译回归仍通过；下一步建议进入 `review` 复核。

时间：2026-04-20 03:02 +0800
经办人：不要啊教练
任务：T-20260419-f6efa359
任务目标：复核 npu_demo `symbol.const` 旧分发/短路行为是否已恢复，并确认不影响 `_emit_npu_deslice_stmt` 文案与相关回归
改动：本轮仅做审查。确认 [`kernel_gen/dsl/emit_c.py`](../../../../../../kernel_gen/dsl/emit_c.py) 已恢复 `symbol.const` 的 npu_demo 旧分发/短路行为，`_emit_npu_deslice_stmt` 文案仍保持 Vector 口径，[`test/dsl/test_emit_c.py`](../../../../../../test/dsl/test_emit_c.py) 的 EC-020 元信息也已同步到最新验证时间。
验证：`pytest -q test/dsl/test_emit_c.py` -> `28 passed, 8 warnings in 0.39s`；`pytest -q test/dsl/test_gen_kernel.py -k 'npu_demo'` -> `24 passed, 35 deselected, 8 warnings in 1.83s`；`git diff --check` -> 通过。
结论：通过。当前回归覆盖了 `symbol.const` 恢复、`_emit_npu_deslice_stmt` 文案同步以及 npu_demo 相关编译回归，未见新增问题。

时间：2026-04-20 03:03 +0800
经办人：李白
任务：T-20260419-f6efa359
任务目标：合并本轮已通过复核的 npu_demo symbol.const 恢复与 `_emit_npu_deslice_stmt` 文案同步改动。
改动：完成同步确认：当前 worktree 待合并写集为 [`kernel_gen/dsl/emit_c.py`](../../../../../../kernel_gen/dsl/emit_c.py)、[`test/dsl/test_emit_c.py`](../../../../../../test/dsl/test_emit_c.py) 与当前记录文件；当前基线 `HEAD=43a0b15`，最新 `origin/main=0255b0d`，需先提交后前移到主线再推送。
验证：`git -C /home/lfr/kernelcode_generate/wt-20260419-emitc-api-s15-arch-kernel-review status --short --branch` -> 仅命中上述 2 个业务文件与记录文件；`git -C /home/lfr/kernelcode_generate/wt-20260419-emitc-api-s15-arch-kernel-review diff --stat` -> `2 files changed, 40 insertions(+), 15 deletions(-)`；`git -C /home/lfr/kernelcode_generate/wt-20260419-emitc-api-s15-arch-kernel-review rev-parse --short HEAD` -> `43a0b15`，`git -C /home/lfr/kernelcode_generate/wt-20260419-emitc-api-s15-arch-kernel-review rev-parse --short origin/main` -> `0255b0d`。
结论：开始 merge，下一步提交当前写集并前移到最新主线后推送，再执行 `-done` 与回报管理员。
