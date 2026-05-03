# pytest_config.md

## 功能简介

- 定义 `pytest.ini` 中 pytest 配置的公开合同。
- 统一基础设施测试标记与默认测试发现范围，避免扫描 worktree 与临时目录。
- 约束 pytest 导入模式，降低重复 basename 的冲突风险。
- 允许实现同名测试文件不带 `test_` 前缀，保证测试路径能按被测实现目录和文件名组织。

## API 列表

- `pytest.ini: Path`
- `[pytest].markers: list[str]`
- `[pytest].filterwarnings: list[str]`
- `[pytest].testpaths: list[str]`
- `[pytest].python_files: list[str]`
- `[pytest].addopts: str`
- `[pytest].norecursedirs: list[str]`

## 文档信息

- 创建者：`未记录`
- 最后一次更改：`小李飞刀`
- `spec`：[`spec/script/pytest_config.md`](../../spec/script/pytest_config.md)
- `功能实现`：[`pytest.ini`](../../pytest.ini)
- `test`：[`test/script/test_pytest_config.py`](../../test/script/test_pytest_config.py)

## 依赖

- pytest 配置入口：[`pytest.ini`](../../pytest.ini)
- pytest 执行器：`pytest`（命令行）

## 目标

- 保证 `infra` 标记稳定可用，便于分层执行测试。
- 保证 `nn_lowering` 标记稳定可用，避免 `nn_lowering` 专题测试产生未知标记 warning。
- 保证 `npu_demo` 标记稳定可用，避免 npu_demo 端到端测试产生未知标记 warning。
- 通过显式 `filterwarnings` 说明默认 warning 策略，避免把项目 warning 静默吞掉。
- 限制 pytest 只扫描 `test` 目录，避免误采集 worktree 与临时目录。
- 统一使用 `importlib` 导入模式，降低同名测试冲突。

## 额外补充

### 模块级补充

- 本小节只记录模块级非接口补充；接口级参数限制、错误语义、兼容要求与非目标必须维护在对应 API 的 `注意事项`。
- 仅描述 pytest 配置合同，不负责业务测试用例的正确性。
- 不负责运行时覆盖率统计配置；覆盖率插件的启停由调用方控制。

## API详细说明

### `pytest.ini: Path`

- api：`pytest.ini: Path`
- 参数：无。
- 返回值：`Path`；指向仓库根目录的 pytest 配置文件。
- 使用示例：

  ```bash
  pytest -q
  ```
- 功能说明：定义 pytest 的默认标记、发现范围、导入模式和递归排除目录。
- 注意事项：该文件是静态配置入口，不提供 Python 可调用对象；调用方可通过 pytest CLI 覆盖默认行为。

### `[pytest].markers: list[str]`

- api：`[pytest].markers: list[str]`
- 参数：无。
- 返回值：`list[str]`；至少包含 `infra`、`nn_lowering` 与 `npu_demo` 标记说明。
- 使用示例：

  ```bash
  pytest -m "not infra"
  pytest -m infra -p no:cov
  ```
- 功能说明：定义项目级 pytest 标记，避免专题测试产生未知标记 warning。
- 注意事项：新增公开标记必须同步测试；业务测试不得依赖未声明标记。

### `[pytest].filterwarnings: list[str]`

- api：`[pytest].filterwarnings: list[str]`
- 参数：无。
- 返回值：`list[str]`；默认至少包含 `default`。
- 使用示例：

  ```bash
  pytest -q
  ```
- 功能说明：显式保留 warning 可见性。
- 注意事项：不得用全局 ignore 静默吞掉项目 warning；单项 warning 例外必须由对应测试或专题单独说明。

### `[pytest].testpaths: list[str]`

- api：`[pytest].testpaths: list[str]`
- 参数：无。
- 返回值：`list[str]`；默认只包含 `test`。
- 使用示例：

  ```bash
  pytest -q
  ```
- 功能说明：限制 pytest 默认采集范围。
- 注意事项：不得默认扫描 `wt-*` worktree、临时目录或非测试资产目录。

### `[pytest].python_files: list[str]`

- api：`[pytest].python_files: list[str]`
- 参数：无。
- 返回值：`list[str]`；默认包含 `test_*.py`。
- 使用示例：

  ```bash
  pytest -q test
  ```
- 功能说明：定义测试文件名采集模式。
- 注意事项：测试文件命名必须能被该模式采集；改动后需要复核全量采集结果。

### `[pytest].addopts: str`

- api：`[pytest].addopts: str`
- 参数：无。
- 返回值：`str`；至少包含 `--import-mode=importlib`。
- 使用示例：

  ```bash
  pytest -q
  ```
- 功能说明：约束默认导入模式，降低重复 basename 的冲突风险。
- 注意事项：调用方可在命令行覆盖默认行为；覆盖后产生的导入冲突不属于本配置合同保证范围。

### `[pytest].norecursedirs: list[str]`

- api：`[pytest].norecursedirs: list[str]`
- 参数：无。
- 返回值：`list[str]`；必须包含 `wt-*` 与 `tmp` 相关目录。
- 使用示例：

  ```bash
  pytest --collect-only -q
  ```
- 功能说明：排除 worktree 与临时目录，避免误采集外部副本测试。
- 注意事项：变更后必须复核 pytest 采集结果，确认不会采集 `wt-*` worktree 与临时目录。

## 测试

- 测试文件：`test/script/test_pytest_config.py`
- 执行命令：
  - `test/script/test_pytest_config.py`
  - `pytest -q test/script/test_pytest_config.py`
  - ` 标记说明。
  - 校验 pytest 配置存在且包含 `
  - ` 标记说明。
- 校验 pytest 配置存在且包含显式 warning 策略。
- 校验 `
  - `TC-PC-001 / test_pytest_ini_options_present`
  - `TC-PC-002 / test_pytest_config_values`
  - `TC-PC-003 / test_pytest_ini_options_present`
  - `TC-PC-004 / test_pytest_config_values`

### 测试目标

- 验证 `spec/script/pytest_config.md` 对应公开 API 的正常路径、边界条件与错误语义。
- 验证公开导入、注册名、CLI 或命名空间入口只暴露 spec 定义的 API。
- 验证 pass 或 pipeline 对目标 IR 的改写、no-op 与顺序约束。


### 功能与用例清单

| 用例 ID | 功能 | 场景 | 前置条件 | 操作 | 预期结果 | 建议测试 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-SCRIPT-PYTEST-CONFIG-001 | 公开入口 | 配置块存在且包含 `infra` 标记说明。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `TC-PC-001 / test_pytest_ini_options_present`。 | 公开入口在“配置块存在且包含 `infra` 标记说明。”场景下可导入、构造、注册或按名称发现。 | `TC-PC-001 / test_pytest_ini_options_present` |
| TC-SCRIPT-PYTEST-CONFIG-002 | 公开入口 | `testpaths/python_files/addopts/norecursedirs` 与合同一致。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `TC-PC-002 / test_pytest_config_values`。 | 公开入口在“`testpaths/python_files/addopts/norecursedirs` 与合同一致。”场景下可导入、构造、注册或按名称发现。 | `TC-PC-002 / test_pytest_config_values` |
| TC-SCRIPT-PYTEST-CONFIG-003 | pass 改写 | 配置块存在且包含 `nn_lowering` 标记说明。 | 准备包含目标 op、pass 名称或 pipeline 的公开 IR 输入。 | 运行 `TC-PC-003 / test_pytest_ini_options_present`。 | IR 改写后的 op、属性、顺序或 no-op 行为体现“配置块存在且包含 `nn_lowering` 标记说明。”场景。 | `TC-PC-003 / test_pytest_ini_options_present` |
| TC-SCRIPT-PYTEST-CONFIG-004 | 公开入口 | 配置块存在且包含 `filterwarnings=default`。 | 按 spec 声明的导入路径、CLI 参数、注册名或命名空间访问公开入口。 | 运行 `TC-PC-004 / test_pytest_config_values`。 | 公开入口在“配置块存在且包含 `filterwarnings=default`。”场景下可导入、构造、注册或按名称发现。 | `TC-PC-004 / test_pytest_config_values` |
