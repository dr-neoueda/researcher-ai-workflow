#!/bin/bash
# UserPromptSubmit hook (raw plugin) — Claude Code と Codex CLI の両方で動く
# 計算ジョブが終わったのに判定していないもの、見張りの無いものがあれば、ユーザーの発言に添えて知らせる。
# UserPromptSubmit は標準出力がそのまま Claude / Codex の文脈に入る（両 CLI の仕様）。速く終わること（ssh はしない）。

set -uo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"
hook_read_input

project_dir="$(hook_project)"
[ -n "$project_dir" ] || exit 0
py="$(hook_python)"
[ -n "$py" ] || exit 0
"$py" "$HOOK_DIR/jobwatch.py" pending --project "$project_dir" --start-watcher 2>/dev/null
exit 0
