#!/usr/bin/env bash

set -euo pipefail

readonly INTERVAL_SECONDS=3600

while true; do
  /home/lfr/kernelcode_generate/skills/codex-multi-agents/scripts/codex-multi-agents-tmux.sh -talk -from 榕 -to 神秘人 -session-id 神秘人 -message "继续任务，跟进任务进展，mlir_gen功能复杂，需要仔细审核，允许大面积重构，联网搜索相关内容，保证最终结果正确！如果mlir_gen任务链完成，安排两个巡查任务，发现漏洞/改进点。lwong 负责 ast 下降到不同方言的ir，ast visitor 负责遍历ast，ast定义ast的结构，mlir gen 负责整合，将函数变为mlir 的ir。" -log /home/lfr/kernelcode_generate/agents/codex-multi-agents/log/talk.log
  sleep "$INTERVAL_SECONDS"
done
