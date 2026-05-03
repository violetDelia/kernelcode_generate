# nn.md

## 功能简介

- 注册 `kernel_gen.operation.nn` 公开 helper 到 AST builtin registry。
- 每个 NN operation 必须映射到 `nodes/nn.py` 中明确的 AST 节点。
- 注册项 builder 负责构造对应 NN AST 节点，并承接 NN helper 前端合同校验。

## API 列表

本文件不承载公开 API。

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/dsl/ast/plugin/nn.md`](../../../../spec/dsl/ast/plugin/nn.md)
- `功能实现`：[`kernel_gen/dsl/ast/plugin/nn.py`](../../../../kernel_gen/dsl/ast/plugin/nn.py)
- `test`：[`test/dsl/ast/plugin/test_nn.py`](../../../../test/dsl/ast/plugin/test_nn.py)

## 依赖

- [`spec/dsl/ast/plugin/registry.md`](../../../../spec/dsl/ast/plugin/registry.md)
- [`spec/dsl/ast/nodes/nn.md`](../../../../spec/dsl/ast/nodes/nn.md)

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 本文件只承载内部注册副作用；未列入上层公开 API 的 builder、注册函数或 helper 不得跨文件直接调用。
- Python AST 参数求值与错误定位由 `DslAstVisitor` 负责；NN helper arity、keyword 与类型合同由本文件 builder 负责。
- 新增 NN operation 时必须同步新增节点 spec 与注册项。

## API详细说明

本文件没有公开 API 详细条目；内部注册、目录组织与非公开 helper 边界见“额外补充”。

## 测试

- 测试文件：`test/dsl/ast/plugin/test_nn.py`
- 执行命令：`pytest -q test/dsl/ast/plugin/test_nn.py`

### 测试目标

- NN helper 可经 registry 分发到 NN plugin builder，并解析成对应 AST 节点。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-DSL-AST-PLUGIN-NN-001 | 公开入口 | NN helper call uses registered specific ast node | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_nn_helper_call_uses_registered_specific_ast_node`。 | 公开入口在“NN helper call uses registered specific ast node”场景下可导入、构造、注册或按名称发现。 | `test_nn_helper_call_uses_registered_specific_ast_node` |
| TC-DSL-AST-PLUGIN-NN-002 | 公开入口 | NN public helpers parse parameterized return nodes | 通过固定 seed 的参数化顺序覆盖 elementwise、activation、reduce、broadcast、structured、transpose 与 softmax helper。 | 运行 `test_nn_public_helpers_parse_parameterized_return_nodes`。 | NN 公开 helper 均经 parser/registry 解析为对应 AST 节点。 | `test_nn_public_helpers_parse_parameterized_return_nodes` |
| TC-DSL-AST-PLUGIN-NN-003 | 边界/异常 | NN public helpers reject invalid contracts | 准备固定 seed 的 elementwise/compare/unary/reduce/softmax/broadcast/transpose/matmul/conv/img2col 非法 arity、keyword 与类型矩阵。 | 运行 `test_nn_public_helpers_reject_invalid_contracts`。 | 参数错误按公开 KernelCodeError 文案被拒绝，且每类 helper 的错误文本保持稳定。 | `test_nn_public_helpers_reject_invalid_contracts` |
