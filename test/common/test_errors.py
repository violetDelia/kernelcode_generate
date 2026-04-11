"""common errors tests.

创建者: 金铲铲大作战
最后一次更改: 金铲铲大作战

功能说明:
- 覆盖 kernel_gen.common.errors 中统一错误模板的固定文本与格式化输出。

使用示例:
- pytest -q test/common/test_errors.py

关联文件:
- 功能实现: kernel_gen/common/errors.py
- Spec 文档: spec/common/errors.md
- 测试文件: test/common/test_errors.py
"""

from __future__ import annotations


# CE-001
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 验证 _ERROR_TEMPLATE 的固定文本保持不变。
# 使用示例: pytest -q test/common/test_errors.py -k test_error_template_literal
# 对应功能实现文件路径: kernel_gen/common/errors.py
# 对应 spec 文件路径: spec/common/errors.md
# 对应测试文件路径: test/common/test_errors.py
def test_error_template_literal() -> None:
    from kernel_gen.common.errors import _ERROR_TEMPLATE

    assert (
        _ERROR_TEMPLATE
        == "场景: {scene}; 期望: {expected}; 实际: {actual}; 建议动作: {action}"
    )


# CE-002
# 创建者: 金铲铲大作战
# 最后一次更改: 金铲铲大作战
# 最近一次运行测试时间: 未运行
# 最近一次运行成功时间: 未运行
# 测试目的: 验证 .format 生成的错误信息字段顺序与文本可用。
# 使用示例: pytest -q test/common/test_errors.py -k test_error_template_format
# 对应功能实现文件路径: kernel_gen/common/errors.py
# 对应 spec 文件路径: spec/common/errors.md
# 对应测试文件路径: test/common/test_errors.py
def test_error_template_format() -> None:
    from kernel_gen.common.errors import _ERROR_TEMPLATE

    message = _ERROR_TEMPLATE.format(
        scene="dma.alloc 参数校验",
        expected="shape must be a dimension sequence",
        actual="str",
        action="请按接口约束传参",
    )

    assert message == (
        "场景: dma.alloc 参数校验; 期望: shape must be a dimension sequence; "
        "实际: str; 建议动作: 请按接口约束传参"
    )
