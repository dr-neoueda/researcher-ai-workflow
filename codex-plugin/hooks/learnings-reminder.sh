#!/bin/bash
# Stop hook (raw plugin) — Claude Code と Codex CLI の両方で動く
# 今日の活動（decisions / 新規 notes / playbook 更新 / 計算ジョブ記録）があるのに
# <today>-learnings.md がまだ無いとき、終わる前に学びを書くよう引き戻す。
# 引き戻しは標準エラー＋終了コード 2（Stop の標準出力は Claude / Codex に届かない）。
# 一度引き戻した後（stop_hook_active）は繰り返さない。

set -uo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"
hook_read_input

hook_stop_active && exit 0

project_dir="$(hook_project)"
[ -n "$project_dir" ] || exit 0
company_dir="$project_dir/office"

today=$(date +%F)
sec_dir="$company_dir/secretary/notes"
learnings_file="$sec_dir/$today-learnings.md"
playbooks_dir="$company_dir/computation/playbooks"
jobs_dir="$company_dir/computation/jobs"

[ -s "$learnings_file" ] && exit 0

activity=0
[ -s "$sec_dir/$today-decisions.md" ] && activity=1

if [ "$activity" -eq 0 ] && [ -d "$sec_dir" ]; then
    [ -n "$(find "$sec_dir" -maxdepth 1 -type f -name "*.md" ! -name "*-learnings.md" -newermt "$today 00:00:00" 2>/dev/null | head -1)" ] && activity=1
fi
if [ "$activity" -eq 0 ] && [ -d "$playbooks_dir" ]; then
    [ -n "$(find "$playbooks_dir" -maxdepth 1 -type f -name "*.md" -newermt "$today 00:00:00" 2>/dev/null | head -1)" ] && activity=1
fi
if [ "$activity" -eq 0 ] && [ -d "$jobs_dir" ]; then
    [ -n "$(find "$jobs_dir" -maxdepth 1 -type f -name "$today-*.md" 2>/dev/null | head -1)" ] && activity=1
fi

[ "$activity" -eq 0 ] && exit 0

cat >&2 <<EOF
[raw learnings-reminder] 今日（${today}）は決定・ノート・Playbook・ジョブ記録に動きがありましたが、
$learnings_file がまだありません。終わる前に次をしてください:
  1. 今日の会話と編集から「学び」を 3〜5 件書き出す（記録と食い違った事象、新しいやり方、失敗の教訓、測った値など）
  2. $learnings_file に保存する（あれば追記、無ければ作る）
  3. 計算ソフトの罠や処方なら、その Playbook の Lessons Learned にも足す
学びが本当に無ければ、"no learnings today" とだけ書いたファイルを作れば、この催促は出なくなります。
EOF
exit 2
