时间: 2026-03-28
任务: T-20260328-b58043b9
任务目标: 统一 operation/dialect/target 用户可见错误模板，字段顺序为“场景/期望/实际/建议动作”，并补充规范化示例。
改动: 更新 kernel_gen/operation/{arch,scf,dma,nn}.py 的错误文案；为 kernel_gen/dialect/{arch,kernel,tuner,nn,dma,symbol}.py 引入统一模板与 verifier 报错；统一 kernel_gen/target/registry.py 的错误模板；同步调整 test/operation、test/dialect、test/target 中依赖错误文案的断言。
结论: 已完成模板统一与测试收敛，示例见下。
- operation 示例1: 场景: operation.nn 参数校验; 期望: nn.add expects Memory operands; 实际: 不满足期望; 建议动作: 请按接口约束传参
- operation 示例2: 场景: operation.dma 参数校验; 期望: dma.slice sizes length must match rank; 实际: 不满足期望; 建议动作: 请按接口约束传参
- dialect 示例1: 场景: dialect.nn verifier; 期望: nn.broadcast result rank must be >= input rank; 实际: 不满足期望; 建议动作: 请按接口约束传参
- dialect 示例2: 场景: dialect.dma verifier; 期望: dma.view numel mismatch; 实际: 不满足期望; 建议动作: 请按接口约束传参
- target 示例1: 场景: target registry; 期望: target name must match ^[a-z0-9_]+$; 实际: 不满足期望; 建议动作: 请按接口约束传参
- target 示例2: 场景: target registry; 期望: target directory does not exist: /path/to/dir; 实际: 不满足期望; 建议动作: 请按接口约束传参

时间: 2026-03-28 19:47:37 +0800
任务: T-20260328-0af8f7c3
任务目标: 复核 operation/dialect/target 错误模板统一为“场景/期望/实际/建议动作”，检查字段顺序一致性与 verifier 文案/测试闭环。
改动:
- 审查 kernel_gen/operation/*、kernel_gen/dialect/*、kernel_gen/target/registry.py 的错误模板与字段顺序。
- 审查对应测试中错误文案断言与 verifier 报错闭环。
- 复测：pytest -q test/dialect/test_tuner_dialect.py -k test_tuner_param_rejects_invalid_result_type。
结论:
- 问题列表: 未发现。
- 漏洞排查结果:
  - 输入校验绕过：operation/dialect/target 统一使用模板错误并保留类型/值检查，未发现绕过路径。
  - 类型/形状绕过：verifier 中对类型/shape/space/stride 仍有明确校验，未发现模板改动引入绕过。
  - 边界越界：未发现模板改动影响边界控制。
  - 错误处理缺失：模板统一后错误仍显式抛出，未发现遗漏。
  - 状态污染：错误模板为常量字符串，未发现上下文污染。
  - 资源释放问题：无资源分配/释放路径。
- 可维护性改进建议: 未发现额外改进点。
- 验证:
  - `pytest -q test/dialect/test_tuner_dialect.py -k test_tuner_param_rejects_invalid_result_type`，exit code 0（1 passed, 2 deselected, 0.35s）。
- 最终结论: 通过。
