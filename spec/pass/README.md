# pass README

这个目录放的是 pass 相关说明。

这里只说明两件事：

1. pass 怎么写
2. pass 怎么用

如果你要新增一个 pass，直接看下面两段和模板文件即可。

## 1. 怎么写一个 pass

推荐写法：

```python
from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.passes import ModulePass

from kernel_gen.pass_manager import register_pass_class


@register_pass_class()
@dataclass(frozen=True)
class LowerNnToKernelPass(ModulePass):
    name = "lower-nn-to-kernel"

    def apply(self, ctx: Context, op: ModuleOp) -> None:
        ...
```

说明：

- pass 类继承 `ModulePass`
- `name` 是这个 pass 在字符串 pipeline 里的名字
- 如果希望 `PassManager()` 默认能直接使用这个 pass，就加上 `@register_pass_class()`

如果你不想让它进入默认注册表，也可以不加装饰器，后面显式注册或直接传实例。

## 2. 怎么用 pass

### 方式一：字符串 pipeline

```python
from kernel_gen.pass_manager import PassManager

manager = PassManager()
manager.run(module, "lower-nn-to-kernel")
```

如果有多个 pass：

```python
from kernel_gen.pass_manager import PassManager

manager = PassManager()
manager.run(module, "lower-ast-to-nn,lower-nn-to-kernel,cleanup-kernel")
```

说明：

- pass 之间用英文逗号分隔
- 这种方式要求 pass 已经在当前 `PassManager` 的注册表里
- 如果用了 `@register_pass_class()`，通常可以直接这样用

### 方式二：直接传 pass 实例

```python
from kernel_gen.pass_manager import PassManager

manager = PassManager(load_builtin_passes=False)
manager.run(module, [LowerNnToKernelPass()])
```

说明：

- 这种方式不依赖字符串解析
- 这种方式也不要求 pass 已进入默认注册表

### 方式三：先构建 pipeline 再执行

```python
from kernel_gen.pass_manager import PassManager

manager = PassManager(load_builtin_passes=False)
pipeline = manager.build_pipeline(LowerNnToKernelPass())
manager.run(module, pipeline)
```

## 3. 显式注册写法

如果你不想在类定义上加装饰器，也可以局部注册：

```python
from kernel_gen.pass_manager import PassManager

manager = PassManager(load_builtin_passes=False)
manager.register_pass(LowerNnToKernelPass)
manager.run(module, "lower-nn-to-kernel")
```

这适合临时验证、测试或实验场景。

## 4. 查看默认注册表

```python
from kernel_gen.pass_manager import get_builtin_passes

builtin_passes = get_builtin_passes()
print(sorted(builtin_passes))
```

如果某个 pass 加了装饰器但这里看不到，优先检查它所在模块是否已经被导入。

## 5. 模板

新增 pass 时可以直接从下面这个模板开始改：

```python
from dataclasses import dataclass

from xdsl.context import Context
from xdsl.dialects.builtin import ModuleOp
from xdsl.passes import ModulePass

from kernel_gen.pass_manager import register_pass_class


@register_pass_class()
@dataclass(frozen=True)
class YourPassName(ModulePass):
    name = "your-pass-name"

    def apply(self, ctx: Context, op: ModuleOp) -> None:
        ...
```

对应的常见调用方式：

```python
from kernel_gen.pass_manager import PassManager

manager = PassManager()
manager.run(module, "your-pass-name")
```

或者：

```python
from kernel_gen.pass_manager import PassManager

manager = PassManager(load_builtin_passes=False)
manager.run(module, [YourPassName()])
```
