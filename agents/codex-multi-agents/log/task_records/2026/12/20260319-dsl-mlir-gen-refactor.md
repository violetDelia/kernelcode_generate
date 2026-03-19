# 20260319-dsl-mlir-gen-refactor

- 任务: T-20260319-5932f3ec
- 执行人: 咯咯咯
- worktree: /home/lfr/kernelcode_generate/wt-20260319-dsl-emit-mlir-mlir-gen-refactor
- 时间: 2026-03-19 09:15:52 +0800

## 范围
- `spec/dsl/mlir_gen.md`

## 已完成
- 按 AGENTS 规范补齐 `功能简介/文档信息/依赖/目标/限制与边界/公开接口/测试`。
- 明确 `emit_mlir` 为公开入口，清理旧 lowering 命名与迁移式表述，仅保留当前 mlir_gen 文本输出口径。
- 与 `ast/ast_visitor/emit_mlir` 分层关系对齐，保留 `nn dialect` 依赖与测试映射。

## 修改文件
- `/home/lfr/kernelcode_generate/wt-20260319-dsl-emit-mlir-mlir-gen-refactor/spec/dsl/mlir_gen.md`

## 测试
- 未运行（spec 文档更新）。

## 待确认
- `spec/dsl/emit_mlir.md` 当前仍保留 lowering 命名与路径口径，需由对应负责人统一命名与分层口径。

---

## T-20260319-ce9ddbe9

- 时间：2026-03-19 09:19:37 +0800
- 角色：`不要啊教练`
- worktree：`/home/lfr/kernelcode_generate/wt-20260319-dsl-emit-mlir-mlir-gen-refactor`
- 审查范围：
  - `spec/dsl/emit_mlir.md`
  - `spec/dsl/mlir_gen.md`
- 结论：不通过

### 问题与建议

1) 分层职责互相冲突，命名与依赖方向不一致
- 位置：
  - `spec/dsl/emit_mlir.md` “目标/分层关系/依赖”段落（强调 `mlir_gen` 负责结构化 IR 生成，`emit_mlir` 只负责打印）。
  - `spec/dsl/mlir_gen.md` “功能简介/依赖/目标/限制与边界/公开接口”段落（将 `mlir_gen` 定义为文本输出规范，并声明 IR 生成规则由 `emit_mlir.md` 约束）。
- 原因：两份 spec 对“mlir_gen 与 emit_mlir 的职责归属”叙述相反，形成循环依赖，导致命名与分层含义不一致。
- 建议改法：明确单向分层并统一描述。
  - 方案 A（更贴合文件命名）：`mlir_gen` 负责结构化 IR 生成规则（func.func/SSA/op/value），`emit_mlir` 只负责打印文本。将 `mlir_gen.md` 中“文本输出规范/公开入口为 emit_mlir/依赖 emit_mlir IR 生成规则”的表述改为“IR 生成规范/公开入口为 visit_to_nn_ir 等”，并在 `emit_mlir.md` 中保留“仅打印”。
  - 方案 B：若坚持 `mlir_gen`=文本输出规范，则需在 `emit_mlir.md` 中移除“mlir_gen 负责结构化 IR 生成”的表述，避免互相指向。

2) 公开接口与分层入口描述重复且易误导
- 位置：`spec/dsl/mlir_gen.md` “公开接口/功能简介/目标”段落。
- 原因：`mlir_gen.md` 将 `emit_mlir` 作为公开入口并定义输出语义，导致与 `emit_mlir.md` 的接口定义重复；同时与文件名“mlir_gen”暗示的 IR 生成层相冲突。
- 建议改法：将 `emit_mlir` 入口的唯一规范集中在 `emit_mlir.md`，`mlir_gen.md` 仅描述 IR 生成入口（如 `visit_to_nn_ir`）及结构化 IR 规则；或明确 `mlir_gen` 只是文档聚合层并改名/调整引用以避免重复定义。

3) 测试映射口径不一致，重复引用同一测试
- 位置：
  - `spec/dsl/emit_mlir.md` “测试映射”使用 `EMIT-001 -> test_emit_mlir_output`。
  - `spec/dsl/mlir_gen.md` “测试映射/测试清单”同时使用 `MLIR-001` 与 `TC-MLIR-002` 绑定同一 `test_emit_mlir_output`。
- 原因：同一测试在两个 spec 中被不同用例 ID 复用，且 `mlir_gen` 的文本输出测试与 `emit_mlir` 的输出测试边界不清。
- 建议改法：统一测试归属与编号。
  - 若 `emit_mlir` 承担输出测试，则 `mlir_gen.md` 应只保留 IR 生成相关测试（如 `visit_to_nn_ir`、SSA 顺序等）。
  - 若 `mlir_gen` 继续覆盖文本输出测试，则 `emit_mlir.md` 需改为引用 `mlir_gen` 的测试或重新划分测试 ID，避免同一测试多头映射。

### 结论说明
- 因存在上述分层与测试映射冲突，当前不满足“命名/分层/公开接口/测试映射一致”的要求，需先修订后再进入提交整理阶段。

---

## T-20260319-f0ea6548

- 时间：2026-03-19 09:28:52 +0800
- 角色：`不要啊教练`
- worktree：`/home/lfr/kernelcode_generate/wt-20260319-dsl-emit-mlir-mlir-gen-refactor`
- 审查范围：
  - `spec/dsl/emit_mlir.md`
  - `spec/dsl/mlir_gen.md`
- 结论：通过
- 是否按要求收敛：是（emit_mlir 仅定义文本输出；mlir_gen 仅定义结构化 IR 生成约束；接口归属/依赖方向/测试编号无冲突）

### 说明
- 两份 spec 的分层职责、公开接口归属与测试映射已闭合且无重复编号冲突。

---

## T-20260319-86c01684

- 时间：2026-03-19 21:30:16 +0800
- 角色：`李白`
- worktree：`/home/lfr/kernelcode_generate/wt-20260319-dsl-emit-mlir-mlir-gen-merge`
- 合入范围：
  - `spec/dsl/emit_mlir.md`
  - `spec/dsl/mlir_gen.md`
- 变更摘要：
  - `emit_mlir` 与 `mlir_gen` 分层职责/测试映射已按复审结论收敛。
  - `mlir_gen` 明确为结构化 IR 生成基线，`emit_mlir` 聚焦文本输出入口规范。
- 合入提交：
  - 合并提交：`ca2cfd3`
  - main 提交：`c28214b`
- 测试：
  - 未执行（按任务要求）。
