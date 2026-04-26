# pytest_config.md

## 功能简介

- 定义 `pytest.ini` 中 pytest 配置的公开合同。
- 统一基础设施测试标记与默认测试发现范围，避免扫描 worktree 与临时目录。
- 约束 pytest 导入模式，降低重复 basename 的冲突风险。

## API 列表

- `pytest.ini` / `[pytest]`

## 文档信息

- 创建者：`小李飞刀`
- 最后一次更改：`jcc你莫辜负`
- `spec`：[`spec/script/pytest_config.md`](../../spec/script/pytest_config.md)
- `功能实现`：[`pytest.ini`](../../pytest.ini)
- `test`：[`test/script/test_pytest_config.py`](../../test/script/test_pytest_config.py)

## 依赖

- pytest 配置入口：[`pytest.ini`](../../pytest.ini)
- pytest 执行器：`pytest`（命令行）

## 目标

- 保证 `infra` 标记稳定可用，便于分层执行测试。
- 保证 `nn_lowering` 标记稳定可用，避免 `nn_lowering` 专题测试产生未知标记 warning。
- 通过显式 `filterwarnings` 说明默认 warning 策略，避免把项目 warning 静默吞掉。
- 限制 pytest 只扫描 `test` 目录，避免误采集 worktree 与临时目录。
- 统一使用 `importlib` 导入模式，降低同名测试冲突。

## 限制与边界

- 仅描述 pytest 配置合同，不负责业务测试用例的正确性。
- 不负责运行时覆盖率统计配置；覆盖率插件的启停由调用方控制。

## 公开接口

### `pytest.ini` / `[pytest]`

功能说明：

- 定义 pytest 的默认标记、发现范围与导入模式。

参数说明：

- `markers(list[str])`：按多行配置项组织，至少包含 `infra` 与 `nn_lowering` 标记说明。
- `filterwarnings(list[str])`：按多行配置项组织，默认至少包含 `default`，以显式保留 warning 可见性。
- `testpaths(list[str])`：按多行配置项组织，默认只包含 `test`。
- `addopts(str)`：至少包含 `--import-mode=importlib`。
- `norecursedirs(list[str])`：按多行配置项组织，需包含 `wt-*` 与 `tmp` 相关目录。

使用示例：

```bash
pytest -m "not infra"
pytest -m infra -p no:cov
```

注意事项：

- `norecursedirs` 变更后需复核 pytest 采集结果。
- `addopts` 仅用于默认行为，调用方可在命令行覆盖。

返回与限制：

- pytest 配置为静态合同，不提供运行时返回值。

## 测试

- 测试文件：[`test/script/test_pytest_config.py`](../../test/script/test_pytest_config.py)
- 执行命令：`pytest -q test/script/test_pytest_config.py`
- 测试目标：
  - 校验 pytest 配置存在且包含 `infra` 标记说明。
  - 校验 pytest 配置存在且包含 `nn_lowering` 标记说明。
  - 校验 pytest 配置存在且包含显式 warning 策略。
  - 校验 `testpaths`、`addopts` 与 `norecursedirs` 与合同一致。
- 功能与用例清单：
  - `TC-PC-001 / test_pytest_ini_options_present`：配置块存在且包含 `infra` 标记说明。
  - `TC-PC-002 / test_pytest_config_values`：`testpaths/addopts/norecursedirs` 与合同一致。
  - `TC-PC-003 / test_pytest_ini_options_present`：配置块存在且包含 `nn_lowering` 标记说明。
  - `TC-PC-004 / test_pytest_config_values`：配置块存在且包含 `filterwarnings=default`。
