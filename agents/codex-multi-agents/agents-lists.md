# Agents 名单

| 姓名 | 状态 | 会话 | 启动设置 | agent session | worktree | 介绍 | 提示词 | 归档文件 | 职责 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 金铲铲大作战 | ready | cma-root | codex | root-admin | . | 调度管理员 | agents/codex-multi-agents/agents/金铲铲大作战/金铲铲大作战.prompt.md | agents/codex-multi-agents/agents/金铲铲大作战 | 任务调度与协作管理 |
| 李白 | ready | cma-libai | codex | spec-writer | . | spec 编写 | agents/codex-multi-agents/agents/李白/李白.prompt.md | agents/codex-multi-agents/agents/李白 | 书写 spec |
| 小明 | ready | cma-xiaoming | codex | impl-xiaoming | . | 实现代码（不写测试） | agents/codex-multi-agents/agents/小明/小明.prompt.md | agents/codex-multi-agents/agents/小明 | 根据 spec 在实现代码 |
| 阿飞 | doing | cma-afei | codex | test-afei | . | 测试代码实现 | agents/codex-multi-agents/agents/阿飞/阿飞.prompt.md | agents/codex-multi-agents/agents/阿飞 | 实现代码,测试等 |
| 大哥大 | ready | cma-review | codex | code-reviewer | . | 审查代码与测试回归，输出风险建议 | agents/codex-multi-agents/agents/大哥大/大哥大.prompt.md | agents/codex-multi-agents/agents/大哥大 | 审查代码与测试结果 |
