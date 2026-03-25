# pass README

这个目录放的是 pass 相关说明。

这里只说明两件事：

1. pass 怎么写
2. pass 怎么用

如果你要新增一个 pass，直接看下面两段即可。

## 1. 怎么写一个 pass

推荐写法：

```python
from kernel_gen.passes.pass_manager import Pass


class LowerNnToKernelPass(Pass):
    name = "lower-nn-to-kernel"

    def run(self, target):
        # target 是任意需要被处理的对象（例如 module）
        return target
```

说明：

- pass 类继承 `Pass`
- `name` 是该 pass 的标识
- `run(self, target)` 必须返回处理后的结果

## 2. 怎么用 pass

### 方式一：逐个注册后执行

```python
from kernel_gen.passes.pass_manager import PassManager

manager = PassManager(name="opt")
manager.add_pass(LowerNnToKernelPass())
result = manager.run(target)
```

### 方式二：批量注册后执行

```python
from kernel_gen.passes.pass_manager import PassManager

manager = PassManager()
manager.extend([LowerNnToKernelPass(), AnotherPass()])
result = manager.run(target)
```

说明：

- `add_pass` 追加单个 pass
- `extend` 依次追加多个 pass
- `run` 依次调用每个 pass 的 `run` 方法
