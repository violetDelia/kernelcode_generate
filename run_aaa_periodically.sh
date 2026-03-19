#!/usr/bin/env bash

set -euo pipefail

readonly INTERVAL_SECONDS=3600

while true; do
  /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh -talk -from 榕 -to 神秘人 -session-id 神秘人 -message "推进当前执行的任务，直到任务全部完成，如果一个角色询问后没有回报，使用init 提醒他" -log /home/lfr/kernelcode_generate/agents/codex-multi-agents/log/talk.log
  sleep "$INTERVAL_SECONDS"
done
