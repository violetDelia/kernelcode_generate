"""NPU target info.

创建者: 大哥大
最后一次更改: 大哥大

功能说明:
- 定义 NPU 目标的静态配置。

使用示例:
- from target.npu import info
- assert info.cluster_num == 12

关联文件:
- spec: spec/target/npu.md
- test: test/target/test_npu_info.py
- 功能实现: target/npu/info.py
"""

cluster_num = 12
