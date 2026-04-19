# kernel_split.md

## 功能简介

- 定义 `KernelSplitPass` 的兼容入口：行为与 `TilePass` 完全一致。
- 对外仍提供 `kernel_gen.passes.lowering.kernel_split` 模块，以支持旧调用路径。

## 文档信息

- 创建者：`小李飞刀`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/pass/lowering/kernel_split.md`](../../../spec/pass/lowering/kernel_split.md)
- `功能实现`：[`kernel_gen/passes/lowering/kernel_split.py`](../../../kernel_gen/passes/lowering/kernel_split.py)
- `test`：[`test/pass/test_lowering_kernel_split.py`](../../../test/pass/test_lowering_kernel_split.py)

## 依赖

- Tile pass 规范：[`spec/pass/lowering/tile.md`](../../../spec/pass/lowering/tile.md)
- Pass 管理抽象：[`spec/pass/pass_manager.md`](../../../spec/pass/pass_manager.md)

## 术语

- `KernelSplitPass`：旧入口类名，当前委托 TilePass。
- `TilePass`：实际执行 tile loop 改写的 pass。

## 目标

- 保持旧入口可调用，但将语义与 TilePass 对齐。
- 统一错误短语与顺序约束，避免旧接口产生歧义。

## 限制与边界

- `KernelSplitPass` 的输入合同与 `TilePass` 一致。
- `KernelSplitPass.name` 固定为 `"tile"`。
- 兼容入口不依赖额外属性触发。

## 公开接口

### `class KernelSplitPass(Pass)`

功能说明：

- 兼容入口，行为与 TilePass 相同。

参数说明：

- `name (str)`：固定为 `"tile"`。

使用示例：

```python
from kernel_gen.passes.lowering.kernel_split import KernelSplitPass

pass_obj = KernelSplitPass()
module = pass_obj.run(module)
```

注意事项：

- 兼容入口不改变 TilePass 的公开合同。

返回与限制：

- 返回完成 loop 改写后的 module。
- 任一函数不满足输入合同时必须报错。

### `KernelSplitPass.run(module)`

功能说明：

- 直接复用 TilePass 的执行逻辑。

参数说明：

- `module (builtin.module)`：满足 TilePass 输入合同的 IR module。

使用示例：

```text
func.func @vec_add(%arg0: !nn.memory<[M, N], f32, #layout, #GM>,
                   %arg1: !nn.memory<[M, N], f32, #layout, #GM>,
                   %arg2: !nn.memory<[M, N], f32, #layout, #GM>) {
  kernel.binary_elewise %arg0, %arg1, %arg2 {kind = "add", space = #nn.space<global>} : ...
  func.return
}
```

返回与限制：

- 返回完成 loop 改写后的 module。

## 测试

- 测试文件：`test/pass/test_lowering_kernel_split.py`
- 执行命令：`pytest -q test/pass/test_lowering_kernel_split.py`
- 测试目标：
  - 验证 KernelSplitPass 与 TilePass 行为一致。
  - 验证兼容错误类型与 name 仍可用。
- 功能与用例清单：
  - `test_kernel_split_pass_aliases_tile_pass`
