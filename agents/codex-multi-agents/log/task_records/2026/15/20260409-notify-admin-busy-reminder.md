# 20260409-notify-admin-busy-reminder

时间：2026-04-09 05:43:56 +0800
经办人：小李飞刀
任务：T-20260409-8a095ac1（实现；增强 script/notify-admin.sh 定时提醒逻辑）
任务目标：保持每 1800 秒提醒；每轮先提醒管理员推进“正在执行的任务”并分发“任务列表”中可分发任务；同轮对 agents-lists.md 中状态为 busy 的执行人逐一发送提醒（忽略管理员与架构师账号）；保持现有 -init 模式可用。
改动：
- script/notify-admin.sh：默认间隔改为 1800；新增管理员提醒 + busy 执行人提醒同轮发送；解析 agents-lists.md 表格筛选 busy 且跳过管理员/架构师。
- test/script/test_notify_admin.py：构造含 busy/职责 的最小 agents-lists.md；fake tmux 记录多次调用并断言“先管理员后 busy”与忽略规则；同步默认间隔断言为 1800。
结论：
- bash -n script/notify-admin.sh：通过。
- pytest -q test/script/test_notify_admin.py：通过（7 passed）。

时间：2026-04-09 05:48:36 +0800
经办人：不要啊教练
任务：T-20260409-8a095ac1（审查；notify-admin busy 提醒逻辑与文案）
任务目标：从严复核 script/notify-admin.sh 新增 busy 提醒逻辑与文案是否满足需求，并核对 spec/实现/测试一致性与可复现证据。
改动：
- 无代码改动；仅复跑验证命令并核对差异范围与文案/边界。
- 差异文件列表（git diff --name-only）：
  - script/notify-admin.sh
  - test/script/test_notify_admin.py
- 验证命令与结果：
  - bash -n script/notify-admin.sh（exit=0）
  - pytest -q test/script/test_notify_admin.py -> 7 passed in 0.11s（exit=0）
结论：需修改

问题列表：
1) 文件：spec/script/notify-admin.md vs script/notify-admin.sh / test/script/test_notify_admin.py
   - 现象：spec 中“默认 INTERVAL_SECONDS=3600、默认 MESSAGE 为两句固定文案”的描述，与实现/测试当前默认配置（INTERVAL_SECONDS=1800；ADMIN_MESSAGE/BUSY_MESSAGE 两段文案；循环模式对 busy 执行人逐一提醒）不一致。
   - 风险：spec/实现/测试口径不一致会导致后续维护与审查误判；同时文案变更缺少 spec 侧约束，后续不易定位“需求是否变化/是否回归”。
   - 建议：新增后续任务同步更新 spec/script/notify-admin.md：明确默认间隔、管理员提醒文案、busy 提醒文案、以及“先管理员后 busy”的发送顺序与跳过规则；并同步 spec 的测试目标清单。
   - 优先级：P1

2) 文件：script/notify-admin.sh（错误处理语义）
   - 现象：脚本未启用 `set -e`，且 `send_talk` / `send_round` 对下游 tmux 脚本调用失败未显式检查返回码；与 spec 中“下游调用失败时脚本直接报错退出”的表述存在潜在冲突。
   - 风险：会话发送失败时可能静默进入下一轮 sleep，导致管理员/执行人未收到提醒但日志也不一定显式体现；问题定位成本上升。
   - 建议：与管理员确认期望语义（失败即退出 vs 失败可继续循环）。若期望“失败即退出”，建议补齐 `|| err ...` 或等价检查并补测；若期望“失败可继续”，建议更新 spec 明确“最佳努力”语义并补齐日志约束与补测。
   - 优先级：P2

漏洞排查结果（按审查规范 6 类）：
- 输入校验绕过：NOTIFY_ADMIN_RANDOM_ROLL 已做范围校验；agents-lists 表格解析对列名有显式匹配，未见直接绕过导致脚本执行任意命令的路径。
- 类型/形状绕过：不适用（脚本主要处理字符串与表格行）。
- 边界越界：列表解析以行扫描为主，未见数组越界风险；但对“agents-lists 缺失职责列”的容错语义未在 spec 明确。
- 错误处理缺失：存在潜在语义缺口（问题 2）。
- 状态污染：脚本按轮循环发送消息；未见写入外部状态文件（除 LOG_FILE）导致污染的直接证据。
- 资源释放问题：长循环脚本无显式资源分配；未见明显泄露点。

最终结论：
- 需修改。建议派生唯一后续任务优先同步 spec/script/notify-admin.md 与当前实现/测试一致；并基于管理员确认决定是否补齐 tmux 调用失败的错误处理与对应测试。

时间：2026-04-09 05:47:36 +0800
经办人：小李飞刀
任务：T-20260409-8a095ac1（实现；补齐 busy 提醒忽略规则）
任务目标：对齐 agents-lists.md 真实表头口径，确保 busy 提醒忽略管理员与架构师账号。
改动：
- script/notify-admin.sh：busy 过滤除 TO_NAME 外，增加基于“介绍”列包含“管理员/架构师”与“职责”列包含“架构”跳过提醒。
- test/script/test_notify_admin.py：mock agents-lists.md 增加“介绍”列并模拟架构师条目，验证不会对架构师发送 busy 提醒。
结论：
- bash -n script/notify-admin.sh：通过。
- pytest -q test/script/test_notify_admin.py：通过（7 passed）。

时间：2026-04-09 05:58:37 +0800
经办人：咯咯咯
任务：T-20260409-8a095ac1（spec；同步 notify-admin 文档与当前实现/测试）
任务目标：同步 spec/script/notify-admin.md 与当前实现/测试一致，明确默认间隔=1800、管理员/busy 提醒文案、发送顺序、跳过规则、下游 tmux 调用失败语义与测试目标清单。
改动：
- spec/script/notify-admin.md：将默认配置改为 `INTERVAL_SECONDS=1800`、`ADMIN_MESSAGE`、`BUSY_MESSAGE`，补充“先管理员、后 busy”的发送顺序、busy 目标筛选与跳过规则，以及无合格 busy 条目时仅发送管理员提醒的口径。
- spec/script/notify-admin.md：补充 `NOTIFY_ADMIN_RANDOM_ROLL`、`sleep failed` / `NOTIFY_ADMIN_RANDOM_ROLL must be 0, 1, or 2` 的稳定错误短语，并明确下游 `tmux` 返回非零时当前脚本不会生成独立错误短语、不会中断本轮后续提醒。
- 通过临时 fake repo 复现 `tmux` 返回非零场景，并运行 `bash -n script/notify-admin.sh`、`pytest -q test/script/test_notify_admin.py` 复核当前实现/测试口径。
结论：
- 文档已与 `script/notify-admin.sh`、`test/script/test_notify_admin.py` 对齐。
- `bash -n script/notify-admin.sh`：通过。
- `pytest -q test/script/test_notify_admin.py`：通过（7 passed）。

时间：2026-04-09 06:04:05 +0800
经办人：提莫炖蘑菇
任务：T-20260409-8a095ac1（审查；notify-admin 文档与脚本一致性）
任务目标：核对 spec/script/notify-admin.md 与 script/notify-admin.sh、test/script/test_notify_admin.py 的默认间隔、管理员/busy 文案、发送顺序、跳过规则与 tmux 失败语义一致性，并复测命令。
改动：
- 无代码改动；仅审查与复测。
- 复核文件：spec/script/notify-admin.md；script/notify-admin.sh；test/script/test_notify_admin.py。
结论：
- 一致性：默认间隔=1800、管理员与 busy 文案、发送顺序与跳过规则在 spec/实现/测试中一致；tmux 返回非零时不额外输出错误短语且不阻断本轮提醒的语义一致。
- 注释与示例：脚本与测试文件头部中文说明与示例路径一致。
- 验证：
  - bash -n script/notify-admin.sh（exit=0）
  - pytest -q test/script/test_notify_admin.py（exit=0，7 passed in 0.10s）

问题列表：
- 无。

漏洞排查结果：
- 输入校验绕过：未见（随机分支取值与必填项均有校验）。
- 类型/形状绕过：不适用（脚本与表格行处理为主）。
- 边界越界：未见（表格行遍历与列索引有检查）。
- 错误处理缺失：未见（sleep 失败有固定错误提示并退出；tmux 失败语义已在 spec 中明确）。
- 状态污染：未见（仅写日志，其他状态不持久化）。
- 资源释放问题：未见（无持久资源分配）。

改进建议：
- 未发现额外改进点。

最终结论：
- 通过。
