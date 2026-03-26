时间: 2026-03-27 03:16:48 +0800
任务: T-20260327-8ac8f0bd
任务目标: 补齐 Tensor 注解 i1/bool dtype 解析支持并跑通 nn.lt expectation。
改动:
- kernel_gen/dsl/ast.py: _DTYPE_MAP 增加 i1/bool 映射。
- kernel_gen/dsl/emit_mlir.py: _dtype_to_xdsl 支持 NumericType.Bool -> i1。
- kernel_gen/symbol_variable/memory.py: 比较返回 dtype 改为 Bool。
- test/dsl/test_ast_visitor.py: 新增 Tensor[i1]/bool 注解解析测试。
- test/operation/test_memory_operation.py: 比较 predicate dtype 断言更新。
结论: expectation/dsl/mlir_gen/dialect/nn/lt.py 运行通过；pytest -q test/dsl/test_ast_visitor.py -k test_ast_parse_function_accepts_tensor_bool_annotations 与 pytest -q test/operation/test_memory_operation.py -k test_memory_compare_predicate 均通过。
经办人: 小李飞刀
