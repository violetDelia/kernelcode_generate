# python_coverage_check.md

## 功能简介

- 定义 `script/check_python_coverage.py` 的公开合同。
- 读取 `coverage.py` 生成的 JSON 报告，检查 Python 项目的 line / branch 覆盖率阈值。
- 支持按 `kernel_gen` 模块前缀做阶段内 scoped 验收，不把合同验收资产、`test/`、`spec/` 计入本轮阈值。

## API 列表

- `script/check_python_coverage.py`

## 文档信息

- 创建者：`金铲铲大作战`
- 最后一次更改：`金铲铲大作战`
- `spec`：[`spec/script/python_coverage_check.md`](../../spec/script/python_coverage_check.md)
- `spec`：[`spec/script/python_coverage_omit.md`](../../spec/script/python_coverage_omit.md)
- `功能实现`：[`script/check_python_coverage.py`](../../script/check_python_coverage.py)
- `test`：[`test/script/test_python_coverage_check.py`](../../test/script/test_python_coverage_check.py)

## 依赖

- coverage 入口：[`coverage json`](https://coverage.readthedocs.io/)
- 任务计划：[`ARCHITECTURE/plan/python_spec_impl_test_refactor_green_plan.md`](../../ARCHITECTURE/plan/python_spec_impl_test_refactor_green_plan.md)

## 目标

- 为 S1 / S7 提供稳定的覆盖率阈值检查入口。
- 允许阶段内按 `--include-module` 只检查指定 `kernel_gen` 模块前缀。
- 对缺失或损坏的 coverage JSON 明确失败，不把不完整报告误判为通过。

## 限制与边界

- 仅处理 `coverage.py` JSON 报告，不负责生成覆盖率数据。
- 不读取合同验收资产目录，也不把合同验收资产纳入覆盖率目标。
- 不替代 `pytest`，只负责 coverage 阈值校验。

## 公开接口

### `script/check_python_coverage.py`

功能说明：

- 读取 coverage JSON。
- 计算 line / branch 覆盖率百分比。
- 失败时返回非零退出码并打印原因。

参数说明：

- `--coverage-json(Path)`：coverage JSON 路径。
- `--line-min(float)`：最小 line coverage 百分比。
- `--branch-min(float)`：最小 branch coverage 百分比。
- `--include-module(list[str])`：可重复指定的模块前缀，未指定时检查报告总计。

使用示例：

```bash
python3 script/check_python_coverage.py \
  --coverage-json coverage/S1/coverage.json \
  --line-min 95 \
  --branch-min 60
```

```bash
python3 script/check_python_coverage.py \
  --coverage-json coverage/S1/coverage.json \
  --include-module kernel_gen.passes \
  --line-min 95 \
  --branch-min 60
```

返回与限制：

- 成功：退出码 `0`，输出一行覆盖率摘要。
- 失败：退出码非 `0`，标准错误包含失败原因。

## 测试

- 测试文件：[`test/script/test_python_coverage_check.py`](../../test/script/test_python_coverage_check.py)
- 执行命令：

```bash
pytest -q test/script/test_python_coverage_check.py
```

- 功能与用例清单：
  - 阈值通过。
  - line 不足。
  - branch 不足。
  - JSON 缺字段。
  - `--include-module` 只检查指定模块前缀。
