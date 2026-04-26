# __init__.md

## 功能简介

- 定义 `kernel_gen.dsl.ast` package 的公开 facade 合同。
- 聚合 AST 节点类型、诊断类型与解析入口，提供稳定的包级导入路径。
- 节点字段语义以 [`spec/dsl/ast/nodes.md`](../../../spec/dsl/ast/nodes.md) 为准，解析规则以 [`spec/dsl/ast/parser.md`](../../../spec/dsl/ast/parser.md) 为准，访问器契约以 [`spec/dsl/ast/visitor.md`](../../../spec/dsl/ast/visitor.md) 为准。

## API 列表

- `AstParseError`
- `parse_function(fn: Callable[..., object]) -> FunctionAST`
- `AST 节点公开类：见 spec/dsl/ast/nodes.md`
- `诊断与位置信息类型：Diagnostic, SourceLocation`

## 文档信息

- 创建者：`OpenAI Codex`
- 最后一次更改：`OpenAI Codex`
- `spec`：[`spec/dsl/ast/__init__.md`](../../../spec/dsl/ast/__init__.md)
- `功能实现`：[`kernel_gen/dsl/ast/__init__.py`](../../../kernel_gen/dsl/ast/__init__.py)
- `test`：
  - [`test/dsl/ast/test_package.py`](../../../test/dsl/ast/test_package.py)
  - [`test/dsl/ast/test_parser.py`](../../../test/dsl/ast/test_parser.py)

## 依赖

- [`spec/dsl/ast/nodes.md`](../../../spec/dsl/ast/nodes.md)
- [`spec/dsl/ast/parser.md`](../../../spec/dsl/ast/parser.md)
- [`spec/dsl/ast/visitor.md`](../../../spec/dsl/ast/visitor.md)

## 目标

- 为 `kernel_gen.dsl.ast` 包根导入提供稳定合同。
- 保证上层只通过包级公开导出访问 AST 节点与解析入口。

## 限制与边界

- 本文件只定义包级 facade 合同，不重复列出每个节点字段细节。
- 节点字段与 visitor 细节不得在本文件维护第二份副本。

## 测试

- 测试文件：
  - [`test/dsl/ast/test_package.py`](../../../test/dsl/ast/test_package.py)
  - [`test/dsl/ast/test_parser.py`](../../../test/dsl/ast/test_parser.py)
- 执行命令：`pytest -q test/dsl/ast/test_package.py test/dsl/ast/test_parser.py`
- 测试目标：`kernel_gen.dsl.ast` 包级导入与解析入口稳定
