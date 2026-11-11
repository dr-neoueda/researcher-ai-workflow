#!/bin/bash
# Stop hook (raw plugin) — Claude Code と Codex CLI の両方で動く
# 終わったのに判定していない計算ジョブ、見張りの無いジョブがあれば、終わる前に片付けるよう引き戻す。
# 引き戻しは標準エラー＋終了コード 2。一度引き戻した後（stop_hook_active）は繰り返さない。

set -uo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"
hook_read_input

hook_stop_active && exit 0
project_dir="$(hook_project)"
[ -n "$project_dir" ] || exit 0
py="$(hook_python)"
[ -n "$py" ] || exit 0
pending="$("$py" "$HOOK_DIR/jobwatch.py" pending --project "$project_dir" --start-watcher 2>/dev/null)"
[ -n "$pending" ] || exit 0

cat >&2 <<MSG
[raw jobwatch] 終わる前に、計算ジョブを片付けてください（raw の決まり: どの計算にも見張りを付け、完走まで見る）。

${pending}

- 終わったジョブ: judge で完走かを判定し（終了コードでは決めない）、ジョブ記録と Playbook に反映して、
  次に投入するものを決める（無ければ「無い」と書く）
- 見張りの無いジョブ: ensure-watcher で見張りを起動する
MSG
exit 2
