时间: 2026-03-27 02:22:02 +0800
任务: T-20260327-0c4a3155
任务目标: 复审 nn.add DSL 闭环（EMIT-026C/MGEN-032C），核对 spec/实现/测试与 expectation 一致性并给出结论。
改动: 1) 同步 expectation/utils 到 worktree 以便运行 expectation；2) 运行 python expectation/dsl/mlir_gen/dialect/nn/add.py（失败，见结论）；3) 核对 spec/dsl/emit_mlir.md、spec/dsl/mlir_gen.md、kernel_gen/dsl/emit_mlir.py、kernel_gen/dsl/mlir_gen.py、test/dsl/test_ast_visitor.py 与 expectation/dsl/mlir_gen/dialect/nn/add.py。
结论: 需修改。
- 期待/实现不一致：expectation/dsl/mlir_gen/dialect/nn/add.py 中 add_promote_kernel 使用 `lhs + rhs`，PROMO_EXPECTED_MEMORY 计算为 Float32（由 Memory._promote_dtype 取更高精度）；但 emit_mlir 的 _resolve_nn_add_element_type / _NN_ADD_PROMOTION_RANK 选择 i32（低优先级），导致 python expectation 断言 `assert_memory(promote_cast_ops[0].result.type, PROMO_EXPECTED_MEMORY)` 失败。需对齐 dtype promotion 规则（建议以 Memory._promote_dtype 或 spec 口径为准），并同步 test/dsl/test_ast_visitor.py 中 MGEN-032C/EMIT-026C 断言与 spec 描述。
- spec 描述滞后：spec/dsl/emit_mlir.md 的 EMIT-026C 与 spec/dsl/mlir_gen.md 的 MGEN-032C 仍标注“待实现阶段补充”，与当前已有测试与实现不一致，需要移除阶段性表述并写清实际映射。

时间: 2026-03-27 03:46:18 +0800
经手人: 小李飞刀
任务: T-20260327-c3c2c535
任务目标: 对齐 nn.add dtype promotion（_resolve_nn_add_element_type vs Memory._promote_dtype），修正 EMIT-026C/MGEN-032C 状态并跑通 expectation/dsl/mlir_gen/dialect/nn/add.py。
改动:
- kernel_gen/dsl/emit_mlir.py：调整 nn.add dtype promotion 选择规则，按更高优先级 dtype 决议。
- kernel_gen/dsl/mlir_gen.py：BinaryExprAST(op="add") 返回允许 element_type 以 promotion 结果为准；补充 BinaryExprAST 导入与返回校验逻辑。
- test/dsl/test_ast_visitor.py：更新 MGEN-032C/EMIT-026C 断言为 f32 promotion 结果。
- spec/dsl/emit_mlir.md、spec/dsl/mlir_gen.md：移除 EMIT-026C/MGEN-032C 的阶段性表述。
验证:
- 命令：PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/add.py
- 退出码：0
结论：expectation 通过，进入复审阶段。


时间：2026-03-27 02:51:33 +0800
经手人：摸鱼小分队
任务：T-20260327-6d49ee5f
任务目标：复审 nn.add dtype promotion 链路，核对 spec/实现/测试闭环并执行 expectation 验证。
改动：
- 只读复核实现与测试：kernel_gen/dsl/emit_mlir.py、kernel_gen/dsl/mlir_gen.py、test/dsl/test_ast_visitor.py，以及 spec/dsl/{ast,emit_mlir,mlir_gen}.md。
- expectation 一致性核对：cmp /home/lfr/kernelcode_generate/expectation/dsl/mlir_gen/dialect/nn/add.py /home/lfr/kernelcode_generate/wt-20260327-expectation-dsl-mlir-gen-nn-add/expectation/dsl/mlir_gen/dialect/nn/add.py -> exit 0。
- 必跑命令：PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/add.py -> exit 0。
- 回归验证：pytest -q test/dsl/test_ast_visitor.py -k "dtype_promotion or nn_add_promotes_dtype_with_dma_cast or lowers_nn_add_with_dtype_promotion" -> 2 passed。
- 发现问题复现：
  - 在临时脚本中定义 `def bad_ret(lhs: "Tensor[f32,2,2]", rhs: "Tensor[f32,2,2]") -> "Tensor[i32,2,2]": return lhs + rhs`，执行 `PYTHONPATH=. python <tmp_script>` 后 `build_func_op(...)` 未报错（输出 `unexpected_pass`）。
  - 定位：kernel_gen/dsl/mlir_gen.py 中 `_build_func_op_from_ast_impl` 将 `allow_element_type_mismatch` 对所有 `BinaryExprAST(op="add")` 一律放开（约第 318-323 行），导致即使非 dtype promotion 场景也跳过返回 element_type 校验。
结论：需修改（不通过）。
- 建议修复：仅在 `add` 且左右 operand 的 element_type 不一致并触发 promotion 时放宽返回 element_type 校验；普通同 dtype `add` 仍需严格校验返回注解。
- 建议补测：新增负路径测试，覆盖 `f32+f32` 但返回注解 `i32` 必须报 `Return type does not match annotation`。

时间: 2026-03-27 12:20:00 +0800
经手人: 金铲铲大作战
任务: T-20260327-70622ac8
任务目标: 修复 nn.add 返回注解校验，仅 mixed dtype promotion 场景放宽 element_type 校验；同 dtype 返回注解不匹配必须报错，并补齐负路径测试。
改动:
- kernel_gen/dsl/mlir_gen.py: 新增 _allow_add_element_type_mismatch，仅当 nn.add 左右 dtype 不一致时放宽返回注解 element_type 校验。
- test/dsl/test_ast_visitor.py: 新增 MGEN-032D 负路径测试，覆盖同 dtype 返回注解不匹配报错。
验证:
- pytest -q test/dsl/test_ast_visitor.py -k "rejects_nn_add_return_annotation_mismatch_without_promotion"
- PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/add.py
结论: 完成，进入复审阶段。

时间: 2026-03-27 03:12:15 +0800
经手人: 我不是牛马
任务: T-20260327-64a6c9b2
任务目标: 复审 nn.add DSL 闭环（EMIT-026C/MGEN-032C），核对 spec/实现/测试与 expectation 一致性并给出结论。
改动:
- 只读核对 spec/dsl/emit_mlir.md、spec/dsl/mlir_gen.md、kernel_gen/dsl/emit_mlir.py、kernel_gen/dsl/mlir_gen.py、test/dsl/test_ast_visitor.py 与 expectation/dsl/mlir_gen/dialect/nn/add.py。
- 必跑命令: PYTHONPATH=. python expectation/dsl/mlir_gen/dialect/nn/add.py
- 退出码: 0
结论: 通过。未发现 spec/实现/测试/expectation 不一致项。
