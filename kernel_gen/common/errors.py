"""Common error templates.

创建者: 睡觉小分队
最后一次更改: 金铲铲大作战

功能说明:
- 提供统一的错误模板字符串，供 kernel_gen 各模块生成一致的参数校验与边界错误消息。

使用示例:
- from kernel_gen.common.errors import _ERROR_TEMPLATE
- message = _ERROR_TEMPLATE.format(
    scene="dma.alloc 参数校验",
    expected="shape must be a dimension sequence",
    actual="str",
    action="请按接口约束传参",
  )

关联文件:
- spec: spec/common/errors.md
- test: test/common/test_errors.py
- 功能实现: kernel_gen/common/errors.py
"""

from __future__ import annotations

__all__ = ["_ERROR_TEMPLATE"]

_ERROR_TEMPLATE = "场景: {scene}; 期望: {expected}; 实际: {actual}; 建议动作: {action}"
