#!/bin/bash
# SessionStart hook (raw plugin) — Claude Code と Codex CLI の両方で動く
# プロジェクトの office/ を見つけ（今の場所から上へたどる）、直近の secretary/notes・
# computation/playbooks の一覧・今日の TODO をコンテキストに入れる。
# SessionStart は標準出力がそのまま Claude / Codex に届く（両 CLI の仕様）。
# ユーザー個人パスをハードコードしない（プラグイン配布版）。

set -uo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"
hook_read_input

project_dir="$(hook_project)"
[ -n "$project_dir" ] || exit 0
company_dir="$project_dir/office"

sec_dir="$company_dir/secretary/notes"
playbooks_dir="$company_dir/computation/playbooks"

cat <<EOF
## raw SessionStart コンテキスト

プロジェクト: $project_dir
office/ 検出済。秘書を窓口に運営モードで起動。

EOF

if [ -d "$sec_dir" ]; then
    # mtime 降順で直近 3 件。ls -t は macOS / Linux / WSL / Git Bash 共通（POSIX）。
    files=$(ls -t "$sec_dir"/*-decisions.md "$sec_dir"/*-learnings.md 2>/dev/null | head -3)
    if [ -n "$files" ]; then
        echo "### 直近の意思決定・学び（mtime 上位 3 件・各 30 行）"
        echo ""
        while IFS= read -r f; do
            [ -z "$f" ] && continue
            echo "#### $(basename "$f")"
            echo ""
            head -30 "$f"
            echo ""
            echo "---"
            echo ""
        done <<< "$files"
    fi
fi

if [ -d "$playbooks_dir" ]; then
    pb_files=$(find "$playbooks_dir" -maxdepth 1 -type f -name "*.md" 2>/dev/null | sort)
    if [ -n "$pb_files" ]; then
        echo "### 利用可能な Playbook（必要に応じて全文を読む）"
        echo ""
        while IFS= read -r f; do
            [ -z "$f" ] && continue
            echo "- $f"
        done <<< "$pb_files"
        echo ""
    fi
fi

py="$(hook_python)"
if [ -n "$py" ]; then
    echo "### 計算の見張り（raw の決まり・必ず）"
    echo ""
    echo "裏で走らせる計算と HPC のジョブには、投入したらユーザーに頼まれなくても必ず見張りを付け、完走まで見る:"
    echo "register で登録 → ensure-watcher で見張りを起動 →（Claude Code は wait <key> を裏で走らせる）→ 終わったら judge で判定"
    echo "（終了コードでは決めない）→ ジョブ記録と Playbook に反映し、同じ応答で次に投入するものを決める。詳しくは office/ の設定ファイルの「計算の見張り」。"
    echo "見張りの道具: $py \"$HOOK_DIR/jobwatch.py\""
    echo ""
    "$py" "$HOOK_DIR/jobwatch.py" pending --project "$project_dir" 2>/dev/null
    echo ""
fi

today=$(date +%F)
todo_file="$company_dir/secretary/todos/$today.md"
if [ -s "$todo_file" ]; then
    echo "### 今日の TODO（${today}）"
    echo ""
    head -30 "$todo_file"
    echo ""
fi
exit 0
