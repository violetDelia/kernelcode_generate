# arch.md

## 功能简介

- 注册 `kernel_gen.operation.arch` 公开 helper 到 AST builtin registry。
- 覆盖 block/thread/subthread 查询、dynamic memory、barrier 与 launch_kernel。
- 注册项 builder 负责构造对应 arch AST 节点，并承接 arch helper 前端合同校验。

## API 列表

本文件不承载公开 API。

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/dsl/ast/plugin/arch.md`](../../../../spec/dsl/ast/plugin/arch.md)
- `功能实现`：[`kernel_gen/dsl/ast/plugin/arch.py`](../../../../kernel_gen/dsl/ast/plugin/arch.py)
- `test`：[`test/dsl/ast/plugin/test_arch.py`](../../../../test/dsl/ast/plugin/test_arch.py)

## 依赖

- [`spec/dsl/ast/plugin/registry.md`](../../../../spec/dsl/ast/plugin/registry.md)
- [`spec/dsl/ast/nodes/arch.md`](../../../../spec/dsl/ast/nodes/arch.md)

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 本文件只承载内部注册副作用；未列入上层公开 API 的 builder、注册函数或 helper 不得跨文件直接调用。
- `launch_kernel` 注册必须对应四字段 launch AST：`block`、`thread`、`subthread`、`shared_memory_size`。
- `barrier` 注册必须与 operation 公开合同一致，`visibility` 必须且只能包含 `BarrierVisibility.TSM` 与 `BarrierVisibility.TLM` 各一次。
- target 查询与 runtime launch 行为不在 plugin 层实现。

## API详细说明

本文件没有公开 API 详细条目；内部注册、目录组织与非公开 helper 边界见“额外补充”。

## 测试

- 测试文件：`test/dsl/ast/plugin/test_arch.py`
- 执行命令：`pytest -q test/dsl/ast/plugin/test_arch.py`

### 测试目标

- Arch helper call 被注册表识别，并由 arch plugin builder 构造对应节点。

### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-DSL-AST-PLUGIN-ARCH-001 | 公开入口 | arch query helper uses specific ast node | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `test_arch_query_helper_uses_specific_ast_node`。 | 公开入口在“arch query helper uses specific ast node”场景下可导入、构造、注册或按名称发现。 | `test_arch_query_helper_uses_specific_ast_node` |
| TC-DSL-AST-PLUGIN-ARCH-002 | 边界/异常 | arch query rejects invalid helper arity | 通过固定 seed 的参数化顺序覆盖 block/thread/subthread 查询 helper 的非法参数。 | 运行 `test_arch_query_rejects_invalid_helper_arity`。 | 六类查询 helper 的非法 arity 均按公开 KernelCodeError 文案被拒绝。 | `test_arch_query_rejects_invalid_helper_arity` |
| TC-DSL-AST-PLUGIN-ARCH-003 | 公开入口 | arch query public helpers parse to specific nodes | 通过固定 seed 的参数化顺序覆盖 block/thread/subthread 查询 helper。 | 运行 `test_arch_query_public_helpers_parse_to_specific_nodes`。 | 六类查询 helper 均经公开 parser 解析为对应 arch AST 节点。 | `test_arch_query_public_helpers_parse_to_specific_nodes` |
| TC-DSL-AST-PLUGIN-ARCH-004 | 解析/打印 | arch memory barrier and launch helpers parse public nodes | 准备 dynamic memory、list/tuple barrier、静态与符号 extent 下标式 launch_kernel 公开调用。 | 运行 `test_arch_memory_barrier_and_launch_helpers_parse_public_nodes`。 | 三类公开 helper 均经 registry 分发到对应 AST 节点。 | `test_arch_memory_barrier_and_launch_helpers_parse_public_nodes` |
| TC-DSL-AST-PLUGIN-ARCH-005 | 边界/异常 | arch public helpers reject invalid contracts | 通过固定 seed 的参数化顺序覆盖 dynamic memory、barrier 与 launch_kernel 的 arity、literal/expr 类型和值域非法组合。 | 运行 `test_arch_public_helpers_reject_invalid_contracts`。 | 参数错误均按公开 KernelCodeError 文案被拒绝，不依赖 plugin 私有 builder。 | `test_arch_public_helpers_reject_invalid_contracts` |
