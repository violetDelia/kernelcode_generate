# spec 文件规范

- 结构目录：
  - `spec.md`
    - `功能简介`
      - 简要说明该 `spec` 对应类、模块或方法的作用与职责。
    - `API 列表`
      - 必须紧跟在 `功能简介` 后，不得后移到其他章节。
      - 只用于快速列举当前 `spec` 覆盖的公开 `API`，方便读者快速判断功能面。
      - 若该 `spec` 对应 `class`，必须列出该 `class` 的公开 `API` 列表；不在列表中的方法默认视为非公开接口。
      - 每个 `API` 必须写出**完整参数签名**，格式按简表写法：
        - `` `api1() -> None` ``
        - `` `api2(target: FooTarget, val: int) -> Result` ``
        - `` `class Foo(target: FooTarget, val: int)` ``
        - `` `Foo.run(target: FooTarget, val: int) -> Result` ``
        - `` `Foo.stop() -> None` ``
    - `文档信息`
      - 创建者
      - 最后一次更改
      - `spec`：`<spec_file>`
      - `功能实现`：`<impl_file>`
      - `test`：`<test_file>`
    - `依赖`
      - 说明该 `spec` 直接依赖的文件、类型或模块，并附对应路径。
    - `术语`（可选）
    - `目标`（可选）
      - 说明该模块对外提供的能力、使用方式和预期场景。
    - `限制与边界`（可选）
      - 说明实现必须满足的限制、与依赖的一致性要求，以及明确的不负责范围。
    - `额外补充`（可选）
    - `测试`
      - 测试文件：`<test_file>`
      - 执行命令
      - 测试目标
      - 功能与用例清单
- 编写要求：
  - 每个 `spec` 原则上只对应一个源文件；如有例外，需要在文档中明确说明原因。
  - `spec` 文件面向开发实现，不写历史迁移、重构过程或任务过程记录。
  - `spec` 中的接口说明、测试目标和示例，应与实际实现和测试保持一致。
  - `API 列表` 必须紧跟在 `功能简介` 后，并显式列出当前 `spec` 覆盖的全部公开 `API`。
  - `API 列表` 只做快速索引，不在这一节展开详细接口说明；但每个公开 `API` 都必须写出参数签名。
  - 若是 `class` 场景，必须把类公开方法逐条列出。
  - 未出现在 `API 列表` 中的函数、方法、类、别名、helper，默认视为非公开接口；实现与测试不得跨文件直连这些非公开接口。
  - 若 `spec` 中定义了测试清单，应与实际测试用例一一对应。
  - `spec` 文件不得出现除 `<结构目录>` 以外的其他章节。
  - `spec` 文件不应绑定某一版实现或测试细节。
  - `README.md` 不属于 `spec` 文件，不需要遵守本节结构要求。
  - `spec` 中不应出现除依赖文件以外的其他文件信息，例如 `expectation` 文件。

## 合法例外写法

- 一对多实现：
  - 当一个公开 `spec` 对应“单一公开入口 + 多个直接协作实现文件”时，可在“文档信息”或“依赖”中列出主实现与辅助实现，并明确谁是公开入口、谁是内部配套实现。
  - 例外成立前提：这些实现文件共同服务同一公开语义，而不是把多个无关模块硬并在一份 `spec`。
- 多测试文件：
  - 当同一公开语义需要用“主路径测试 + 边界/回归测试 + expectation/脚本”共同收口时，可在“测试”章节按“测试文件 / 执行命令 / 覆盖目标”分行列出多个测试文件。
  - 例外成立前提：多测试文件共同锁定同一个公开合同，而不是把其他专题测试顺带挂进来。

## 一对多实现示例

```markdown
## 文档信息
- spec：`spec/execute_engine/execute_engine.md`
- 功能实现：
  - `kernel_gen/execute_engine/execution_engine.py`
  - `kernel_gen/execute_engine/compiler.py`
- test：
  - `test/execute_engine/test_execute_engine_compile.py`
  - `test/execute_engine/test_execute_engine_invoke.py`

## 依赖
- `kernel_gen/execute_engine/execution_engine.py`：公开入口
- `kernel_gen/execute_engine/compiler.py`：编译辅助实现
```

## 多测试文件示例

```markdown
## 测试
- 测试文件：`test/execute_engine/test_execute_engine_compile.py`
- 执行命令：`pytest -q test/execute_engine/test_execute_engine_compile.py`
- 测试目标：锁定 compile 侧公开行为

- 测试文件：`test/execute_engine/test_execute_engine_invoke.py`
- 执行命令：`pytest -q test/execute_engine/test_execute_engine_invoke.py`
- 测试目标：锁定 execute 侧公开行为
```

## API 列表示例

```markdown
## 功能简介
- `Foo` 负责对外提供运行入口和参数校验。

## API 列表
- `foo_run(target: FooTarget, val: int) -> Result`
- `foo_stop(target: FooTarget) -> None`
- `class Foo(target: FooTarget, val: int)`
- `Foo.run(target: FooTarget, val: int) -> Result`
- `Foo.stop() -> None`
```
