# expectation 任务规则

## 文件说明
- 功能说明：统一约束 `expectation` 任务的目标、边界与允许操作，减少各角色提示词中的重复描述。
- 使用示例：各角色提示词可直接引用本文件，例如：`通用规则以 [expectation任务规则](../../../standard/expectation任务规则.md) 为准。`
- 使用示例：当管理员分发 `expectation` 任务时，先按本文件核对“是否禁止修改 expectation 文件内容”和“链路是否固定为 spec -> 实现 -> 审查”。

## 通用规则
- `expectation` 任务的目标是以最小改动让指定 `expectation` 文件通过；链路固定按 `spec -> 实现 -> 审查` 推进。
- `expectation` 文件以工作主目录下对应文件为准，禁止直接修改 `expectation` 文件内容。
- 仅允许执行“拷贝/覆盖同步”操作：当 `worktree` 中对应 `expectation` 文件不存在或与工作主目录不一致时，只能拷贝或覆盖为工作主目录版本，不得进行其他修改。
- 若任务需要新增公开接口，必须同步收敛 `spec`、实现与测试。
