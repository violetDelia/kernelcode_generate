# farmat_migration.md

用于规划 `symbol_variable.type.Farmat` 命名债务的兼容迁移方案，明确新旧命名、兼容期行为、异常规则与测试要求。

## 文档信息

- 创建者：`巡检小队`
- 最后一次更改：`巡检小队`
- `spec`：[`spec/symbol_variable/farmat_migration.md`](../../spec/symbol_variable/farmat_migration.md)
- `test`：[`test/symbol_variable/test_memory.py`](../../test/symbol_variable/test_memory.py)
- `功能实现`：[`symbol_variable/type.py`](../../symbol_variable/type.py)

## 背景

- 当前公开格式枚举类型名为 `Farmat`，存在明显拼写债务。
- 现有 `Memory` 相关规范、测试与调用示例已经围绕 `Farmat` 建立使用习惯，不能直接硬改。
- 本次仅规划命名迁移，不处理包根导出策略，不修改 `symbol_variable/__init__.py` 的统一入口设计。

## 重构目标

- 为格式枚举提供新的规范命名，降低理解与沟通成本。
- 保持现有调用方在兼容期内不因命名迁移而立即失效。
- 明确迁移各阶段的行为、告警与移除条件，避免实现阶段边界模糊。
- 为后续实现、测试和文档更新提供统一约束。

## 非目标

- 不在本方案内定义 `symbol_variable` 包根的导出策略。
- 不改变 `NCHW` / `NHWC` 的语义映射。
- 不在本方案内移除 `Norm` / `CLast` 语义别名，只要求它们在兼容期内继续可用。
- 不修改 `Memory`、`MemorySpace`、`NumericType` 的现有接口。

## 现状与问题

当前实现如下：

- 类型名：`Farmat`
- 规范成员：`NCHW`、`NHWC`
- 兼容成员别名：`Norm -> NCHW`、`CLast -> NHWC`

主要问题：

- `Farmat` 拼写错误会持续污染文档、实现、测试与外部调用。
- 如果直接改名为正确拼写，现有代码中的 `from symbol_variable.type import Farmat` 将全部失效。
- 当前测试已经验证 `Farmat.Norm is Farmat.NCHW`、`Farmat.CLast is Farmat.NHWC`，因此迁移必须保留兼容窗口。

## 命名决策

### 新旧命名

- 新的规范类型名：`Format`
- 旧的兼容类型名：`Farmat`
- 规范成员名：`Format.NCHW`、`Format.NHWC`
- 兼容成员别名：`Format.Norm`、`Format.CLast`

### 命名使用要求

- 所有新增文档、示例、测试、实现内部注释应优先使用 `Format`。
- 兼容期内允许旧调用继续使用 `Farmat`。
- `Norm` / `CLast` 在本次迁移范围内保留为语义别名，不要求同步移除。

## 兼容迁移方案

### 阶段一：引入规范命名

目标：

- 新增 `Format` 作为规范公开类型名。
- 保留 `Farmat` 作为兼容入口。

行为约束：

- `Format` 与 `Farmat` 必须指向同一枚举语义，不允许出现两套不同的成员对象。
- `Format.NCHW`、`Format.NHWC` 为规范使用方式。
- `Format.Norm is Format.NCHW`
- `Format.CLast is Format.NHWC`
- 兼容期内 `Farmat.NCHW is Format.NCHW`
- 兼容期内 `Farmat.NHWC is Format.NHWC`
- 兼容期内 `Farmat.Norm is Format.NCHW`
- 兼容期内 `Farmat.CLast is Format.NHWC`

告警约束：

- 通过旧类型名 `Farmat` 访问类型时，应触发 `DeprecationWarning`。
- 告警信息至少包含：
  - 旧名 `Farmat`
  - 新名 `Format`
  - 迁移建议：改用 `Format.NCHW` / `Format.NHWC`
- 告警应避免在单次测试或单个调用链中被无限重复刷屏；实现可按“每进程一次”或等价收敛策略处理。

### 阶段二：文档与调用方收敛

目标：

- 将所有规范文档、示例、实现内部引用迁移到 `Format`。
- 兼容测试继续保留，确保旧调用未被提前破坏。

行为约束：

- 文档与示例中不再新增 `Farmat.*` 用法。
- 现有依赖方若仍使用 `Farmat`，运行时允许通过，但持续收到弃用告警。
- `Norm` / `CLast` 继续保留，不在本阶段新增移除动作。

### 阶段三：移除旧类型名

触发条件：

- 至少完成两个发布周期或等价的两个稳定迭代窗口。
- 仓库内部文档、测试、示例与主要调用链均已完成迁移。
- 兼容期内未发现必须长期保留旧名的阻塞依赖。

移除后行为：

- `Format` 成为唯一规范类型名。
- `Farmat` 不再作为公开兼容入口。
- 若调用方执行 `from symbol_variable.type import Farmat`，应得到 `ImportError`。
- 若调用方通过模块属性访问 `symbol_variable.type.Farmat`，应得到 `AttributeError`。

## 异常与错误规则

### 兼容期内

- 旧调用 `Farmat` 不应因迁移本身抛出异常。
- 旧调用最多触发 `DeprecationWarning`，不应升级为 `TypeError` / `ValueError`。
- `Format("NCHW")`、`Farmat("NCHW")` 的枚举值解析语义应保持一致。
- 非法枚举值的错误类型保持现有 `Enum` 语义，不因迁移额外包装为其他异常。

### 移除后

- `from symbol_variable.type import Farmat` -> `ImportError`
- `import symbol_variable.type as t; t.Farmat` -> `AttributeError`
- 对 `Format` 的合法/非法成员访问仍遵循 `Enum` 原生规则，不新增自定义异常类型。

## 测试要求

## 测试文件规划

- 保留并更新现有测试：[`test/symbol_variable/test_memory.py`](../../test/symbol_variable/test_memory.py)
- 建议新增专用测试文件：`test/symbol_variable/test_type.py`

### 兼容期测试目标

- 验证 `Format` 为规范类型名。
- 验证 `Farmat` 在兼容期内仍可访问。
- 验证通过旧名访问时触发 `DeprecationWarning`。
- 验证 `Format.NCHW` / `Format.NHWC` 与 `Farmat` 对应成员为同一语义对象。
- 验证 `Norm` / `CLast` 继续作为成员别名可用。
- 验证 `Memory(..., format=Format.NCHW)` 与 `Memory(..., format=Farmat.Norm)` 语义一致。

### 移除期测试目标

- 验证移除 `Farmat` 后：
  - 直接导入旧名触发 `ImportError`
  - 模块属性访问旧名触发 `AttributeError`
- 验证 `Format` 的正常路径不受影响。

### 建议测试用例

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 |
|---|---|---|---|---|---|
| FM-001 | 规范命名 | 新类型名 | 引入 `Format` | 访问 `Format.NCHW` | 成功 |
| FM-002 | 兼容命名 | 旧类型名 | 兼容期内 | 访问 `Farmat.NCHW` | 成功并告警 |
| FM-003 | 成员别名 | 旧语义别名 | 兼容期内 | `Format.Norm` / `Format.CLast` | 分别等价于 `NCHW` / `NHWC` |
| FM-004 | 同一对象 | 新旧类型一致性 | 兼容期内 | 比较 `Farmat.NCHW is Format.NCHW` | True |
| FM-005 | Memory 接口 | format 参数兼容 | 兼容期内 | 分别传 `Format.NCHW` 与 `Farmat.Norm` | 语义一致 |
| FM-006 | 弃用告警 | 旧名访问 | 兼容期内 | 使用 `Farmat` | `DeprecationWarning` |
| FM-007 | 移除行为 | 导入旧名 | 移除期 | `from symbol_variable.type import Farmat` | `ImportError` |
| FM-008 | 移除行为 | 模块属性旧名 | 移除期 | `symbol_variable.type.Farmat` | `AttributeError` |

## 验收标准

- 规范文档明确给出 `Format` 与 `Farmat` 的新旧关系。
- 兼容期行为、移除条件、异常类型与测试要求均可直接映射到实现任务。
- 方案不覆盖包根导出策略，不与并行的接口收敛任务冲突。

## 使用示例

规范写法：

```python
from symbol_variable.type import Format

layout = Format.NCHW
```

兼容期旧写法：

```python
from symbol_variable.type import Farmat

layout = Farmat.Norm
```
