"""core error template tests.


功能说明:
- 覆盖 kernel_gen.core.error 中统一错误模板的固定文本与格式化输出。

使用示例:
- pytest -q test/core/test_error_template.py

关联文件:
- 功能实现: kernel_gen/core/error.py
- Spec 文档: spec/core/error.md
- 测试文件: test/core/test_error_template.py
"""

from __future__ import annotations


# CE-001
# 测试目的: 验证 ERROR_TEMPLATE 的固定文本保持不变。
# 使用示例: pytest -q test/core/test_error_template.py -k test_error_template_literal
# 对应功能实现文件路径: kernel_gen/core/error.py
# 对应 spec 文件路径: spec/core/error.md
# 对应测试文件路径: test/core/test_error_template.py
def test_error_template_literal() -> None:
    from kernel_gen.core.error import ERROR_ACTION, ERROR_ACTUAL, ERROR_TEMPLATE

    assert (
        ERROR_TEMPLATE
        == "场景: {scene}; 期望: {expected}; 实际: {actual}; 建议动作: {action}"
    )
    assert ERROR_ACTION == "请按接口约束传参"
    assert ERROR_ACTUAL == "不满足期望"


# CE-002
# 测试目的: 验证 .format 生成的错误信息字段顺序与文本可用。
# 使用示例: pytest -q test/core/test_error_template.py -k test_error_template_format
# 对应功能实现文件路径: kernel_gen/core/error.py
# 对应 spec 文件路径: spec/core/error.md
# 对应测试文件路径: test/core/test_error_template.py
def test_error_template_format() -> None:
    from kernel_gen.core.error import ERROR_ACTION, ERROR_ACTUAL, ERROR_TEMPLATE

    message = ERROR_TEMPLATE.format(
        scene="dma.alloc 参数校验",
        expected="shape must be a dimension sequence",
        actual=ERROR_ACTUAL,
        action=ERROR_ACTION,
    )

    assert message == (
        "场景: dma.alloc 参数校验; 期望: shape must be a dimension sequence; "
        "实际: 不满足期望; 建议动作: 请按接口约束传参"
    )
