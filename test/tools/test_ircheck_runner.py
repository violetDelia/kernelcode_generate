"""ircheck runner tests.

创建者: 小李飞刀
最后一次更改: 朽木露琪亚

功能说明:
- 覆盖 kernel_gen/tools/ircheck.py 的 run 行为：compile args 解析、pass/pipeline 执行、检查语义与退出码。

当前覆盖率信息:
- 当前覆盖率: 未统计（本任务验证未启用 coverage 统计）。
- 达标判定: 待后续补充统计结果。

覆盖率命令:
- `pytest -q --cov=kernel_gen.tools.ircheck --cov-branch --cov-report=term-missing test/tools/test_ircheck_runner.py`

使用示例:
- pytest -q test/tools/test_ircheck_runner.py

关联文件:
- 功能实现: kernel_gen/tools/ircheck.py
- Spec 文档: spec/tools/ircheck.md
- 测试文件: test/tools/test_ircheck_runner.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import importlib
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

registry_module = importlib.import_module("kernel_gen.passes.registry")
_reset_registry_for_test = registry_module._reset_registry_for_test
register_pass = registry_module.register_pass
register_pipeline = registry_module.register_pipeline

from kernel_gen.tools.ircheck import run_ircheck_text

pass_manager_module = importlib.import_module("kernel_gen.passes.pass_manager")
Pass = pass_manager_module.Pass
PassManager = pass_manager_module.PassManager


@pytest.fixture(autouse=True)
def _isolate_registry_state() -> None:
    _reset_registry_for_test()
    yield
    _reset_registry_for_test()


_SIMPLE_IR = """builtin.module {
  func.func @main() {
    func.return
  }
}
"""


# TC-IRCHECK-RUN-001
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-08 21:47:00 +0800
# 最近一次运行成功时间: 2026-04-08 21:47:00 +0800
# 功能说明: 验证 --pass no-op 可执行，并能通过 CHECK/CHECK-NEXT/CHECK-NOT 组合检查。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_pass_ok
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_pass_ok() -> None:
    text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: builtin.module
// CHECK: func.func @main
// CHECK-NEXT: func.return
// CHECK-NOT: func.call

{_SIMPLE_IR}"""
    result = run_ircheck_text(text, source_path="inline.ircheck")
    assert result.ok is True
    assert result.exit_code == 0
    assert "builtin.module" in result.actual_ir


# TC-IRCHECK-RUN-002
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-08 21:47:00 +0800
# 最近一次运行成功时间: 2026-04-08 21:47:00 +0800
# 功能说明: 验证不支持的 COMPILE_ARGS 会返回 exit_code=2 与稳定错误短语前缀。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_unsupported_compile_args
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_unsupported_compile_args() -> None:
    text = f"""// COMPILE_ARGS: --unknown arg
// CHECK: builtin.module

{_SIMPLE_IR}"""
    result = run_ircheck_text(text, source_path="inline.ircheck")
    assert result.ok is False
    assert result.exit_code == 2
    assert result.message is not None
    assert result.message.startswith("IrcheckCompileArgsError: unsupported compile args")


# TC-IRCHECK-RUN-007
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-09 03:00:50 +0800
# 最近一次运行成功时间: 2026-04-09 03:00:50 +0800
# 功能说明: 验证解析期约束（如首条 positive check 为 CHECK-NEXT）会映射为 exit_code=2。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_parse_error_maps_to_exit_code_2
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_parse_error_maps_to_exit_code_2() -> None:
    text = f"""// COMPILE_ARGS: --pass no-op
// CHECK-NEXT: func.return

{_SIMPLE_IR}"""
    result = run_ircheck_text(text, source_path="inline.ircheck")
    assert result.ok is False
    assert result.exit_code == 2
    assert result.message is not None
    assert result.message.startswith("IrcheckParseError: invalid ircheck header")


# TC-IRCHECK-RUN-003
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-08 21:47:00 +0800
# 最近一次运行成功时间: 2026-04-08 21:47:00 +0800
# 功能说明: 验证 CHECK 找不到时返回 exit_code=1 与稳定错误短语前缀，并给出 failed_check。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_check_not_found
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_check_not_found() -> None:
    text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: does.not.exist

{_SIMPLE_IR}"""
    result = run_ircheck_text(text, source_path="inline.ircheck")
    assert result.ok is False
    assert result.exit_code == 1
    assert result.message is not None
    assert result.message.startswith("IrcheckMatchError: CHECK not found")
    assert result.failed_check is not None
    assert result.failed_check.kind == "CHECK"


# TC-IRCHECK-RUN-004
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-08 21:47:00 +0800
# 最近一次运行成功时间: 2026-04-08 21:47:00 +0800
# 功能说明: 验证 CHECK-NEXT 必须在下一行命中，否则返回稳定错误短语前缀。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_check_next_failure
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_check_next_failure() -> None:
    text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: func.func @main
// CHECK-NEXT: builtin.module

{_SIMPLE_IR}"""
    result = run_ircheck_text(text, source_path="inline.ircheck")
    assert result.ok is False
    assert result.exit_code == 1
    assert result.message is not None
    assert result.message.startswith("IrcheckMatchError: CHECK-NEXT not found on next line")
    assert result.failed_check is not None
    assert result.failed_check.kind == "CHECK-NEXT"


# TC-IRCHECK-RUN-005
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-08 21:47:00 +0800
# 最近一次运行成功时间: 2026-04-08 21:47:00 +0800
# 功能说明: 验证 CHECK-NOT 在相邻 positive check 命中行之间命中会失败，并报告稳定错误短语前缀。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_check_not_failure_between_positives
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_check_not_failure_between_positives() -> None:
    text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: builtin.module
// CHECK-NOT: func.func
// CHECK: func.return

{_SIMPLE_IR}"""
    result = run_ircheck_text(text, source_path="inline.ircheck")
    assert result.ok is False
    assert result.exit_code == 1
    assert result.message is not None
    assert result.message.startswith("IrcheckMatchError: CHECK-NOT matched forbidden text")
    assert result.failed_check is not None
    assert result.failed_check.kind == "CHECK-NOT"


# TC-IRCHECK-RUN-020
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-12 11:20:00 +0800
# 最近一次运行成功时间: 2026-04-12 11:20:00 +0800
# 功能说明: 验证带 options 的 pass 可被解析并透传给 from_options。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_pass_with_options
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_pass_with_options() -> None:
    @register_pass
    class OptionPass(Pass):
        name = "option-pass"
        seen_options: dict[str, str] = {}

        @classmethod
        def from_options(cls, options: dict[str, str]) -> "OptionPass":
            cls.seen_options = dict(options)
            return cls()

        def run(self: "OptionPass", target: object) -> object:
            return target

    text = f"""// COMPILE_ARGS: --pass "option-pass={{mode=fast}}"
// CHECK: builtin.module

{_SIMPLE_IR}"""
    result = run_ircheck_text(text, source_path="inline.ircheck")
    assert result.ok is True
    assert OptionPass.seen_options == {"mode": "fast"}


# TC-IRCHECK-RUN-021
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-12 11:20:00 +0800
# 最近一次运行成功时间: 2026-04-12 11:20:00 +0800
# 功能说明: 验证未加引号的 options 写法会被视为不支持的 compile args。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_unquoted_options_rejected
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_unquoted_options_rejected() -> None:
    text = f"""// COMPILE_ARGS: --pass option-pass={{mode=fast}}
// CHECK: builtin.module

{_SIMPLE_IR}"""
    result = run_ircheck_text(text, source_path="inline.ircheck")
    assert result.ok is False
    assert result.exit_code == 2
    assert result.message is not None
    assert result.message.startswith("IrcheckCompileArgsError: unsupported compile args")


# TC-IRCHECK-RUN-030
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-15 03:40:00 +0800
# 最近一次运行成功时间: 2026-04-15 03:40:00 +0800
# 功能说明: 验证 emitc_target=cpu 会在 compile steps 后切到源码文本匹配。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_emitc_cpu_success
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_emitc_cpu_success() -> None:
    text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: void main() {{
// CHECK-NEXT: }}

{_SIMPLE_IR}"""
    result = run_ircheck_text(text, source_path="inline_emitc.ircheck", emitc_target="cpu")
    assert result.ok is True
    assert result.exit_code == 0
    assert result.actual_ir == "void main() {\n}"


# TC-IRCHECK-RUN-031
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-15 03:40:00 +0800
# 最近一次运行成功时间: 2026-04-15 03:40:00 +0800
# 功能说明: 验证 emitc_target=npu_demo 且输入不满足受控 module 合同时返回固定错误前缀，并保留进入源码分支前的最终 IR。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_emitc_npu_demo_failure_keeps_ir
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_emitc_npu_demo_failure_keeps_ir() -> None:
    text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: ignored

{_SIMPLE_IR}"""
    result = run_ircheck_text(text, source_path="inline_emitc.ircheck", emitc_target="npu_demo")
    assert result.ok is False
    assert result.exit_code == 2
    assert result.message is not None
    assert result.message.startswith("IrcheckEmitCError: emit_c generation failed")
    assert "builtin.module" in result.actual_ir
    assert 'func.func @main()' in result.actual_ir


# TC-IRCHECK-RUN-032
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-15 03:40:00 +0800
# 最近一次运行成功时间: 2026-04-15 03:40:00 +0800
# 功能说明: 验证 emitc_target 非法时返回固定错误前缀，并保留 compile steps 后的最终 IR。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_emitc_invalid_target
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_emitc_invalid_target() -> None:
    text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: ignored

{_SIMPLE_IR}"""
    result = run_ircheck_text(text, source_path="inline_emitc.ircheck", emitc_target="gpu")
    assert result.ok is False
    assert result.exit_code == 2
    assert result.message is not None
    assert result.message.startswith("IrcheckEmitCError: emit_c generation failed")
    assert "unsupported emitc target 'gpu'" in result.message
    assert "builtin.module" in result.actual_ir


# TC-IRCHECK-RUN-022
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-12 11:20:00 +0800
# 最近一次运行成功时间: 2026-04-12 11:20:00 +0800
# 功能说明: 验证非法 options 语法会回落到 compile args 不支持路径。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_invalid_options_syntax
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_invalid_options_syntax() -> None:
    text = f"""// COMPILE_ARGS: --pass "option-pass={{mode}}"
// CHECK: builtin.module

{_SIMPLE_IR}"""
    result = run_ircheck_text(text, source_path="inline.ircheck")
    assert result.ok is False
    assert result.exit_code == 2
    assert result.message is not None
    assert result.message.startswith("IrcheckCompileArgsError: unsupported compile args")


# TC-IRCHECK-RUN-023
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-12 11:20:00 +0800
# 最近一次运行成功时间: 2026-04-12 11:20:00 +0800
# 功能说明: 验证带 options 的 pipeline 会透传 options 并正常执行。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_pipeline_with_options
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_pipeline_with_options() -> None:
    options_seen: dict[str, str] = {}

    @register_pipeline("option-pipeline")
    def _build_option_pipeline(options: dict[str, str]) -> PassManager:
        options_seen.update(options)
        return PassManager(name="option-pipeline")

    text = f"""// COMPILE_ARGS: --pipeline "option-pipeline={{mode=fast}}"
// CHECK: builtin.module

{_SIMPLE_IR}"""
    result = run_ircheck_text(text, source_path="inline.ircheck")
    assert result.ok is True
    assert options_seen == {"mode": "fast"}


# TC-IRCHECK-RUN-006
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-08 21:47:00 +0800
# 最近一次运行成功时间: 2026-04-08 21:47:00 +0800
# 功能说明: 验证 --pipeline 可通过 pass registry 构造并执行。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_pipeline_ok
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_pipeline_ok() -> None:
    text = f"""// COMPILE_ARGS: --pipeline no-op-pipeline
// CHECK: builtin.module

{_SIMPLE_IR}"""
    result = run_ircheck_text(text, source_path="inline.ircheck")
    assert result.ok is True
    assert result.exit_code == 0


# TC-IRCHECK-RUN-008
# 创建者: 守护最好的爱莉希雅
# 最后一次更改: 守护最好的爱莉希雅
# 最近一次运行测试时间: 2026-04-10 13:10:00 +0800
# 最近一次运行成功时间: 2026-04-10 13:10:00 +0800
# 功能说明: 验证 run_ircheck_text 支持 `// -----` 分隔的多 case 顺序执行；全部通过时返回成功。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_multi_case_ok
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_multi_case_ok() -> None:
    text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: func.func @main

{_SIMPLE_IR}
// -----
// COMPILE_ARGS: --pipeline no-op-pipeline
// CHECK: builtin.module
// CHECK: func.return

{_SIMPLE_IR}"""
    result = run_ircheck_text(text, source_path="inline.ircheck")
    assert result.ok is True
    assert result.exit_code == 0
    assert "func.return" in result.actual_ir


# TC-IRCHECK-RUN-009
# 创建者: 守护最好的爱莉希雅
# 最后一次更改: 守护最好的爱莉希雅
# 最近一次运行测试时间: 2026-04-10 13:10:00 +0800
# 最近一次运行成功时间: 2026-04-10 13:10:00 +0800
# 功能说明: 验证多 case 场景下失败时 fail-fast，并在 message 中标识失败 case 序号。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_multi_case_failfast_marks_case_index
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_multi_case_failfast_marks_case_index() -> None:
    text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: builtin.module

{_SIMPLE_IR}
// -----
// COMPILE_ARGS: --pass no-op
// CHECK: does.not.exist

{_SIMPLE_IR}"""
    result = run_ircheck_text(text, source_path="inline.ircheck")
    assert result.ok is False
    assert result.exit_code == 1
    assert result.message is not None
    assert result.message.startswith("IrcheckMatchError: CHECK not found")
    assert result.message.endswith("[case 2]")


# TC-IRCHECK-RUN-010
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-12 10:20:00 +0800
# 最近一次运行成功时间: 2026-04-12 10:20:00 +0800
# 功能说明: 验证 --pass "name={k=v}" 能解析并走 from_options 构造路径。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_pass_with_options_ok
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_pass_with_options_ok() -> None:
    @register_pass
    class OptionPass(Pass):
        name = "opt-pass"

        def __init__(self, mode: str) -> None:
            self.mode = mode

        @classmethod
        def from_options(cls, options: dict[str, str]) -> "OptionPass":
            if options != {"mode": "fast"}:
                raise ValueError("bad options")
            return cls(options["mode"])

        def run(self, target: object) -> object:
            return target

    text = f"""// COMPILE_ARGS: --pass "opt-pass={{mode=fast}}"
// CHECK: builtin.module

{_SIMPLE_IR}"""
    result = run_ircheck_text(text, source_path="inline.ircheck")
    assert result.ok is True
    assert result.exit_code == 0


# TC-IRCHECK-RUN-011
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-12 10:20:00 +0800
# 最近一次运行成功时间: 2026-04-12 10:20:00 +0800
# 功能说明: 验证 --pipeline "name={k=v}" 能解析并调用带参 builder。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_pipeline_with_options_ok
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_pipeline_with_options_ok() -> None:
    @register_pipeline("opt-pipeline")
    def _build_pipeline(options: dict[str, str]) -> PassManager:
        return PassManager(name=f"opt-{options['mode']}")

    text = f"""// COMPILE_ARGS: --pipeline "opt-pipeline={{mode=fast}}"
// CHECK: builtin.module

{_SIMPLE_IR}"""
    result = run_ircheck_text(text, source_path="inline.ircheck")
    assert result.ok is True
    assert result.exit_code == 0


# TC-IRCHECK-RUN-012
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-12 10:20:00 +0800
# 最近一次运行成功时间: 2026-04-12 10:20:00 +0800
# 功能说明: 验证 option 语法不合法会映射为 compile args 不支持错误。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_rejects_invalid_option_syntax
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_rejects_invalid_option_syntax() -> None:
    text = f"""// COMPILE_ARGS: --pass "opt-pass={{mode}}"
// CHECK: builtin.module

{_SIMPLE_IR}"""
    result = run_ircheck_text(text, source_path="inline.ircheck")
    assert result.ok is False
    assert result.exit_code == 2
    assert result.message is not None
    assert result.message.startswith("IrcheckCompileArgsError: unsupported compile args")


# TC-IRCHECK-RUN-013
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-12 11:10:00 +0800
# 最近一次运行成功时间: 2026-04-12 11:10:00 +0800
# 功能说明: 验证带参 pass 必须使用引号包装 name={k=v} 写法。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_rejects_unquoted_pass_options
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_rejects_unquoted_pass_options() -> None:
    text = f"""// COMPILE_ARGS: --pass opt-pass={{mode=fast}}
// CHECK: builtin.module

{_SIMPLE_IR}"""
    result = run_ircheck_text(text, source_path="inline.ircheck")
    assert result.ok is False
    assert result.exit_code == 2
    assert result.message is not None
    assert result.message.startswith("IrcheckCompileArgsError: unsupported compile args")


# TC-IRCHECK-RUN-014
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-12 11:10:00 +0800
# 最近一次运行成功时间: 2026-04-12 11:10:00 +0800
# 功能说明: 验证带参 pipeline 必须使用引号包装 name={k=v} 写法。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_rejects_unquoted_pipeline_options
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_rejects_unquoted_pipeline_options() -> None:
    text = f"""// COMPILE_ARGS: --pipeline opt-pipeline={{mode=fast}}
// CHECK: builtin.module

{_SIMPLE_IR}"""
    result = run_ircheck_text(text, source_path="inline.ircheck")
    assert result.ok is False
    assert result.exit_code == 2
    assert result.message is not None
    assert result.message.startswith("IrcheckCompileArgsError: unsupported compile args")


# TC-IRCHECK-RUN-024
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 2026-04-13 03:43:00 +0800
# 最近一次运行成功时间: 2026-04-13 03:43:00 +0800
# 功能说明: 验证单个 case 支持 pass/pipeline 混合多 step 顺序执行。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_multi_pass_sequence
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_multi_pass_sequence() -> None:
    executed: list[str] = []

    @register_pass
    class PassA(Pass):
        name = "pass-a"

        def run(self, target: object) -> object:
            executed.append("pass-a")
            return target

    @register_pass
    class PassB(Pass):
        name = "pass-b"

        def run(self, target: object) -> object:
            executed.append("pass-b")
            return target

    @register_pass
    class PassC(Pass):
        name = "pass-c"

        def run(self, target: object) -> object:
            executed.append("pass-c")
            return target

    @register_pipeline("pipe-b")
    def _build_pipe() -> PassManager:
        pm = PassManager(name="pipe-b")
        pm.add_pass(PassB())
        return pm

    text = f"""// COMPILE_ARGS: --pass pass-a --pipeline pipe-b --pass pass-c
// CHECK: builtin.module

{_SIMPLE_IR}"""
    result = run_ircheck_text(text, source_path="inline.ircheck")
    assert result.ok is True
    assert result.exit_code == 0
    assert executed == ["pass-a", "pass-b", "pass-c"]


# TC-IRCHECK-RUN-025
# 创建者: 小李飞刀
# 最后一次更改: 小李飞刀
# 最近一次运行测试时间: 2026-04-13 06:30:00 +0800
# 最近一次运行成功时间: 2026-04-13 06:30:00 +0800
# 功能说明: 验证多 step 失败时 message 标明失败 step，actual_ir 返回失败前一刻 IR。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_failing_step_reports_actual_ir
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_failing_step_reports_actual_ir() -> None:
    @register_pass
    class FailingPass(Pass):
        name = "failing-pass"

        def run(self, target: object) -> object:
            raise RuntimeError("boom from failing-pass")

    text = """// COMPILE_ARGS: --pass no-op --pass failing-pass --pass no-op
// CHECK: builtin.module

builtin.module {
  func.func @main() {
    %0 = arith.constant 1 : i32
    func.return
  }
}
"""
    result = run_ircheck_text(text, source_path="inline.ircheck")
    assert result.ok is False
    assert result.exit_code == 2
    assert result.message is not None
    assert result.message.startswith(
        "IrcheckRunError: pass execution failed at step 2 (pass failing-pass)"
    )
    assert "builtin.module" in result.actual_ir
    assert "arith.constant 1 : i32" in result.actual_ir
    assert result.failed_check is None


# TC-IRCHECK-RUN-026
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-14 14:10 +0800
# 最近一次运行成功时间: 2026-04-14 14:10 +0800
# 功能说明: 验证 CHECK-REGEX/CHECK-NEXT-REGEX 支持 alias、变量捕获与跨指令引用。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_regex_variable_success
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_regex_variable_success() -> None:
    text = """// COMPILE_ARGS: --pass no-op
// CHECK-REGEX: %[[ID:{int}]] = arith\\.constant [[VAL:{int}]] : i32
// CHECK-NEXT-REGEX: %[[NEXT_ID:{int}]] = arith\\.constant [[VAL]] : i32
// CHECK-NOT-REGEX: func\\.call

builtin.module {
  func.func @main() {
    %0 = arith.constant 7 : i32
    %1 = arith.constant 7 : i32
    func.return
  }
}
"""
    result = run_ircheck_text(text, source_path="inline.ircheck")
    assert result.ok is True
    assert result.exit_code == 0
    assert "arith.constant 7 : i32" in result.actual_ir


# TC-IRCHECK-RUN-027
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-14 14:10 +0800
# 最近一次运行成功时间: 2026-04-14 14:10 +0800
# 功能说明: 验证 regex 语法错误会映射为 exit_code=2 与稳定错误短语前缀。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_invalid_regex_check_maps_to_exit_code_2
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_invalid_regex_check_maps_to_exit_code_2() -> None:
    text = f"""// COMPILE_ARGS: --pass no-op
// CHECK-REGEX: func.func @[[FN:(]]

{_SIMPLE_IR}"""
    result = run_ircheck_text(text, source_path="inline.ircheck")
    assert result.ok is False
    assert result.exit_code == 2
    assert result.message is not None
    assert result.message.startswith("IrcheckParseError: invalid regex check")


# TC-IRCHECK-RUN-027A
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-14 15:05 +0800
# 最近一次运行成功时间: 2026-04-14 15:05 +0800
# 功能说明: 验证未闭合的转义 `[[` 变量片段会在解析阶段映射为 exit_code=2。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_unclosed_escaped_regex_variable_maps_to_exit_code_2
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_unclosed_escaped_regex_variable_maps_to_exit_code_2() -> None:
    text = f"""// COMPILE_ARGS: --pass no-op
// CHECK-REGEX: func.func @main\\(\\[\\[BROKEN:{{reg}}\\]

{_SIMPLE_IR}"""
    result = run_ircheck_text(text, source_path="inline.ircheck")
    assert result.ok is False
    assert result.exit_code == 2
    assert result.message is not None
    assert result.message.startswith("IrcheckParseError: invalid regex check")


# TC-IRCHECK-RUN-027B
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-14 21:02 +0800
# 最近一次运行成功时间: 2026-04-14 21:02 +0800
# 功能说明: 验证按 spec 转义的字面量 `[[...]]` 可作为普通 regex 文本参与匹配。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_escaped_double_brackets_literal_ok
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_escaped_double_brackets_literal_ok() -> None:
    text = """// COMPILE_ARGS: --pass no-op
// CHECK-REGEX: note = "\\[\\[LIT\\]\\]"

builtin.module attributes {note = "[[LIT]]"} {
  func.func @main() {
    func.return
  }
}
"""
    result = run_ircheck_text(text, source_path="inline.ircheck")
    assert result.ok is True
    assert result.exit_code == 0
    assert 'note = "[[LIT]]"' in result.actual_ir


# TC-IRCHECK-RUN-027C
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-14 21:08 +0800
# 最近一次运行成功时间: 2026-04-14 21:08 +0800
# 功能说明: 验证按 spec 转义的字面量 `[[` 前缀可作为普通 regex 文本参与匹配。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_escaped_double_open_brackets_prefix_ok
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_escaped_double_open_brackets_prefix_ok() -> None:
    text = """// COMPILE_ARGS: --pass no-op
// CHECK-REGEX: note = "\\[\\["

builtin.module attributes {note = "[["} {
  func.func @main() {
    func.return
  }
}
"""
    result = run_ircheck_text(text, source_path="inline.ircheck")
    assert result.ok is True
    assert result.exit_code == 0
    assert 'note = "[["' in result.actual_ir


# TC-IRCHECK-RUN-028
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-14 14:10 +0800
# 最近一次运行成功时间: 2026-04-14 14:10 +0800
# 功能说明: 验证 CHECK-NOT-REGEX 定义变量会映射为 exit_code=2 与稳定错误短语前缀。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_check_not_regex_define_variable_maps_to_exit_code_2
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_check_not_regex_define_variable_maps_to_exit_code_2() -> None:
    text = f"""// COMPILE_ARGS: --pass no-op
// CHECK: builtin.module
// CHECK-NOT-REGEX: [[FN:.*]]

{_SIMPLE_IR}"""
    result = run_ircheck_text(text, source_path="inline.ircheck")
    assert result.ok is False
    assert result.exit_code == 2
    assert result.message is not None
    assert result.message.startswith("IrcheckParseError: CHECK-NOT-REGEX cannot define variables")


# TC-IRCHECK-RUN-029
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-14 14:10 +0800
# 最近一次运行成功时间: 2026-04-14 14:10 +0800
# 功能说明: 验证多 case 下 regex 变量作用域按 case 隔离，同名变量可在不同 case 重新定义。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_regex_variables_are_case_local
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_regex_variables_are_case_local() -> None:
    text = """// COMPILE_ARGS: --pass no-op
// CHECK-REGEX: %[[ID:{int}]] = arith\\.constant [[VAL:{int}]] : i32

builtin.module {
  func.func @main() {
    %0 = arith.constant 7 : i32
    func.return
  }
}
// -----
// COMPILE_ARGS: --pass no-op
// CHECK-REGEX: %[[ID:{int}]] = arith\\.constant [[VAL:{int}]] : i32

builtin.module {
  func.func @main() {
    %1 = arith.constant 9 : i32
    func.return
  }
}
"""
    result = run_ircheck_text(text, source_path="inline.ircheck")
    assert result.ok is True
    assert result.exit_code == 0


# TC-IRCHECK-RUN-030
# 创建者: 朽木露琪亚
# 最后一次更改: 朽木露琪亚
# 最近一次运行测试时间: 2026-04-14 15:05 +0800
# 最近一次运行成功时间: 2026-04-14 15:05 +0800
# 功能说明: 验证 `{reg}` 同时支持符号名与数字 SSA id，满足 expectation 的 memory/alloc 匹配。
# 使用示例: pytest -q test/tools/test_ircheck_runner.py -k test_run_ircheck_text_reg_alias_matches_ssa_ids
# 对应功能实现文件路径: kernel_gen/tools/ircheck.py
# 对应 spec 文件路径: spec/tools/ircheck.md
# 对应测试文件路径: test/tools/test_ircheck_runner.py
def test_run_ircheck_text_reg_alias_matches_ssa_ids() -> None:
    text = r"""// COMPILE_ARGS: --pass no-op
// CHECK-REGEX: func.func @main\(%arg0 : !nn.memory<\[[[M:{reg}]], [[N:{reg}]]\], \[[[N]], 1\], f32, #nn.space<global>>\) -> !nn.memory<\[[[M]], [[N]]\], \[[[N]], 1\], f32, #nn.space<global>> {
// CHECK-NEXT-REGEX: %[[ALLOC:{reg}]] = "dma.alloc"\(\) <\{operandSegmentSizes = array<i32: 0>\}> : \(\) -> !nn.memory<\[[[M]], [[N]]\], \[[[N]], 1\], f32, #nn.space<global>>
// CHECK-NEXT-REGEX: func.return %[[ALLOC]] : !nn.memory<\[[[M]], [[N]]\], \[[[N]], 1\], f32, #nn.space<global>>

builtin.module {
  func.func @main(%arg0: !nn.memory<[M, N], [N, 1], f32, #nn.space<global>>) -> !nn.memory<[M, N], [N, 1], f32, #nn.space<global>> {
    %0 = "dma.alloc"() <{operandSegmentSizes = array<i32: 0>}> : () -> !nn.memory<[M, N], [N, 1], f32, #nn.space<global>>
    func.return %0 : !nn.memory<[M, N], [N, 1], f32, #nn.space<global>>
  }
}
"""
    result = run_ircheck_text(text, source_path="inline.ircheck")
    assert result.ok is True
    assert result.exit_code == 0
