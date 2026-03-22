# 2026-03-22 T-20260322-949f5802

- 任务目标：重构 `spec/include/api/Core.md` 定义统一返回状态，并与 `spec/include/api/Nn.md` 对齐。
- worktree：`/home/lfr/kernelcode_generate/wt-20260322-spec-include-api-core-status`
- 实际变更：
  - `spec/include/api/Core.md`
  - `spec/include/api/Nn.md`
- 核心变更：
  - 新增 `Core.md`，定义 `Status`/`StatusCode` 作为 include/api 统一返回状态语义基座，并明确 `include/api/Core.h` 头文件定位。
  - `Nn.md` 增加对 `Core.md` 依赖说明，统一返回状态引用 `Status/StatusCode` 语义，并补充 `include/api/Core.h` 头文件关系。
- 测试：未运行（API 规范不提供测试）。
- 阻塞：无。
- 下一步建议：申请复审确认 Core/Nn 状态定义与接口关系闭环。

# 2026-03-22 T-20260322-29fbf72e 复审结论

- 结论：通过。
- worktree：`/home/lfr/kernelcode_generate/wt-20260322-spec-include-api-core-status`。
- 范围：`spec/include/api/Core.md`、`spec/include/api/Nn.md`。
- 核对要点：
  - `Core.md` 明确 `Status/StatusCode` 与状态码语义，`StatusCode::kOk == 0`，`Status` 与 `StatusCode` 可互换。
  - `Nn.md` 依赖 `Core.md`，返回值语义与 `Status/StatusCode` 对齐，且保持显式输出与状态值返回口径。
  - `Core.h` 与 `Nn.h`/`Memory.h` 的层次与依赖关系在文档信息与依赖章节中保持一致。
  - 无实现/无测试绑定口径保持一致。
- 测试：未执行（文档复审）。
