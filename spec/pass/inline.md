# inline.md

## 功能简介

- 定义 `inline` pass 的公开合同：把 module 内可内联的本地 `func.call` 展平成调用点，并清理失效的 private helper。
- 首版只覆盖当前 `npu-demo-lowering` 需要的最小 module 内 helper 展平场景，不承诺通用跨 module inline。

## 文档信息

- 创建者：`金铲铲大作战`
- 最后一次更改：`金铲铲大作战`
- `spec`：[`spec/pass/inline.md`](../../../spec/pass/inline.md)
- `功能实现`：[`kernel_gen/passes/inline.py`](../../../kernel_gen/passes/inline.py)
- `test`：[`test/pass/test_inline.py`](../../../test/pass/test_inline.py)

## 依赖

- Pass 管理与执行：[`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)
- pass 注册表：[`spec/pass/registry.md`](../../../spec/pass/registry.md)
- `func.call` / `func.return` IR 语义：[`spec/dialect/func.md`](../../../spec/dialect/func.md)

## 术语

- `inlineable helper`：满足单 block、非 declaration、以 `func.return` 结尾的本地 `func.func`。
- `private helper`：`sym_visibility = private` 的 helper 函数；若不再被引用，应在 inline 后清理。

## 目标

- 把当前 module 内可内联 helper 展平到调用点。
- 保持 SSA 映射稳定，inline 后调用点结果继续指向原返回值。
- 清理已失效的 private helper，避免 module 中残留死函数。

## 限制与边界

- 只接受 `builtin.module` 输入。
- 仅处理 module 内本地 `func.call`，不处理外部声明或跨 module 调用。
- helper 必须是单 block 且 block 末尾为 `func.return`。
- 若 inline 之后仍残留可内联 local call，必须显式失败。

## 公开接口

### `class InlineError(ValueError)`

功能说明：

- 表示 `inline` pass 的稳定错误类型。

使用示例：

```python
raise InlineError("InlineError: module must be builtin.module")
```

### `class InlinePass`

功能说明：

- 对 module 内可内联 helper 执行展平，并清理失效的 private helper。

使用示例：

```python
from kernel_gen.passes.inline import InlinePass

module = InlinePass().run(module)
```

### `build_registered_pass("inline")`

功能说明：

- 通过 registry 的稳定 pass 名称构造 `InlinePass`。

使用示例：

```python
from kernel_gen.passes.registry import build_registered_pass, load_builtin_passes

load_builtin_passes()
pass_obj = build_registered_pass("inline")
```

## 测试

- 测试文件：[`test/pass/test_inline.py`](../../../test/pass/test_inline.py)
- 执行命令：`pytest -q test/pass/test_inline.py`
- 测试目标：
  - inline 可展开本地 helper
  - inline 后 private helper 会被清理
  - 非 module 输入显式失败
