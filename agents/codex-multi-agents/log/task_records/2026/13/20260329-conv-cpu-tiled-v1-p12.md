- 时间：2026-03-29 20:30:05 +0800
- 任务：T-20260329-91ec7f13
- 任务目标：仅更新 `spec/dsl/ast.md`，补齐 `img2col1d/img2col2d`、`get_shape/get_stride`、单顶层 for-loop DSL 语法支持说明，并收敛 v1 限制条件。
- 改动：
  - 更新 `spec/dsl/ast.md` 的“限制与边界”，明确 v1 仅支持单个顶层函数、禁止局部/嵌套 `FunctionDef`、不承诺通用 `if` 与 `if bias is not None`，并禁止继续使用笼统 `img2col(...)` 公开名。
  - 在 `parse_function(fn)` 注意事项补充 `img2col1d/img2col2d` 入口与 `get_shape/get_stride` 索引语义边界。
  - 新增 `conv2d_img2col2d_tiled(...)` DSL 契约小节（含中文注释示例），明确 `calls/supported_img2col_calls/shape_accesses/loops/returns/forbidden` 验收口径，且声明不包含 backend/pass 细节。
  - 在测试目标与用例清单新增 AST-019 映射说明，标注 `normalize_ast_contract(...)` 为验收辅助伪名，不要求新增同名产品接口。
- 结论：P12 规格已在 AST 层完成收敛，改动范围仅 `spec/dsl/ast.md`，未修改实现与测试文件。


- 时间：2026-03-29 21:48:45 +0800
- 任务：T-20260329-01952a79
- 任务目标：实现 P12 AST 语法契约（img2col1d/img2col2d、get_shape/get_stride、单顶层函数限制与禁用项），补齐实现与测试映射。
- 改动：
  - 新增 AST 节点 `Img2ColAST` 与 `TensorAxisAccessAST`，用于承载 img2col1d/img2col2d 调用与 shape/stride 轴索引访问。
  - 解析层支持 `img2col1d/img2col2d`，并拒绝笼统 `img2col(...)` 公开名。
  - 解析层新增禁用项：嵌套 FunctionDef、通用 if、if bias is not None、多个顶层函数定义。
  - 新增/补齐 AST-019 系列测试覆盖上述正负路径。
- 测试：
  - `pytest -q test/dsl/test_ast.py -k "img2col2d_and_shape_stride_accesses or img2col_call_name or nested_function_def or generic_if_statement or if_bias_is_not_none or multiple_top_level_functions"`（exit code: 0）
- 结论：P12 AST 契约实现与测试闭环完成；未修改 spec。
时间：2026-03-29 22:10:39 +0800
任务：T-20260329-67056550
任务目标：复审 P12 DSL AST 合约，核对 kernel_gen/dsl/ast.py 中 img2col/get_shape/get_stride 解析与禁用项诊断；复跑 AST-019 用例并检查中文注释一致性。
改动：
- 审查范围：kernel_gen/dsl/ast.py、spec/dsl/ast.md、test/dsl/test_ast.py（AST-019/019A/019B/019C/019D）。
- 复测：PYTHONPATH=. pytest -q test/dsl/test_ast.py -k "img2col2d_and_shape_stride_accesses or img2col_call_name or nested_function_def or generic_if_statement or if_bias_is_not_none"（exit 0，5 passed）。
- 发现问题：多处解析函数缺少中文函数注释/使用示例（违反“所有函数必须有中文注释”新规）。示例：
  - _parse_expr（img2col/get_shape/get_stride 入口语义解析核心函数）
  - _parse_for、_parse_stmt、_parse_function_impl
结论：需修改。
- 功能正确性：img2col1d/2d 解析为 Img2ColAST；get_shape/get_stride 下标访问解析为 TensorAxisAccessAST；img2col 禁用名诊断为 Unsupported img2col call；禁用项 nested_function_def / generic_if / if_bias_is_not_none 诊断与测试一致。
- 边界/异常路径：get_shape/get_stride arity、来源非 TensorAST、img2col 空参、禁用 if/嵌套函数诊断均有明确错误路径。
- 漏洞排查：未发现输入校验绕过/类型形状绕过/边界越界/错误处理缺失/状态污染/资源释放问题；但注释缺失属流程阻塞。
- 下一步建议：补齐上述解析函数中文注释（功能说明+使用示例+关联文件），确保与实现一致后复核。

- 时间：2026-03-29 22:28:36 +0800
- 任务：T-20260329-84fd417e
- 任务目标：补齐 kernel_gen/dsl/ast.py 中 _parse_expr/_parse_for/_parse_stmt/_parse_function_impl 解析函数中文注释，保持与 img2col/get_shape/get_stride 及禁用项诊断一致。
- 改动：
  - 为 _parse_expr/_parse_for/_parse_stmt/_parse_function_impl 增加中文注释（功能说明/使用示例/关联文件）。
- 测试：未运行（仅注释变更）。
- 结论：解析函数注释已补齐，口径与现有行为一致。
- 时间：`2026-03-29 22:45:57 +0800`
- 任务：`T-20260329-72fbbc07`
- 任务目标：复审 P12 AST 解析注释一致性，核对 _parse_expr/_parse_for/_parse_stmt/_parse_function_impl 中文注释与 img2col/get_shape/get_stride/禁用项诊断一致，抽查注释示例。
- 改动：
  - 审查范围：`kernel_gen/dsl/ast.py`（四个解析函数及相关注释示例）。
  - 未执行测试（本次为注释一致性复审）。
- 结论：通过。
  - 功能正确性：注释已明确 img2col1d/2d 解析入口与 get_shape/get_stride 轴访问语义，与实现逻辑一致。
  - 边界/异常路径：禁止嵌套 FunctionDef/通用 if/if bias is not None、for 中 return、外部值拒绝等禁用项诊断在注释中有明确说明且与实现一致。
  - 潜在漏洞/绕过：未发现因注释错误导致的语义误导或绕过风险。
  - 中文注释：四个解析函数均有中文注释，功能说明与使用示例抽查一致。
  - 可维护性建议：无。
