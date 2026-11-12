#!/bin/bash
# PostToolUse hook (raw plugin) — Claude Code と Codex CLI の両方で動く
# ファイルの書き込み（Claude Code の Edit / Write / MultiEdit、Codex の apply_patch）が
# office/<dept>/<旧パス>/ に入ったとき、「成果物配置の二層原則」違反として警告する。
# 警告は標準エラー＋終了コード 2 で返す（PostToolUse の標準出力は Claude / Codex に届かない）。
# 書き込み自体はもう済んでいるので、止めるのではなく直し方を伝える。

set -uo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"
hook_read_input

project_dir="$(hook_project)"
[ -n "$project_dir" ] || exit 0
paths="$(hook_io paths 2>/dev/null)" || exit 0  # python が無ければ何もしない（raw-setup が python を入れる）
[ -n "$paths" ] || exit 0

suggest() {
    case "$1" in
        office/research/papers/*)        echo "work/papers/${1#office/research/papers/}" ;;
        office/research/topics/*)        echo "work/topics/${1#office/research/topics/}" ;;
        office/research/reports/*)       echo "work/reports/${1#office/research/reports/}" ;;
        office/writing/manuscripts/*)    echo "work/manuscripts/${1#office/writing/manuscripts/}" ;;
        office/analysis/results/*)       echo "work/analyses/${1#office/analysis/results/}" ;;
        office/analysis/figures/*)       echo "work/figures/${1#office/analysis/figures/}" ;;
        office/analysis/notebooks/*)     echo "work/notebooks/${1#office/analysis/notebooks/}" ;;
        office/presentation/slides/*)    echo "work/presentations/slides/${1#office/presentation/slides/}" ;;
        office/presentation/figures/*)   echo "work/figures/${1#office/presentation/figures/}" ;;
        office/engineering/scripts/*)    echo "work/scripts/${1#office/engineering/scripts/}" ;;
        office/engineering/tools/*)      echo "work/tools/${1#office/engineering/tools/}" ;;
    esac
}

found=""
while IFS= read -r rel; do
    [ -n "$rel" ] || continue
    to="$(suggest "$rel")"
    [ -n "$to" ] && found="${found}  - ${rel} → ${to}"$'\n'
done <<< "$paths"
[ -n "$found" ] || exit 0

cat >&2 <<EOF
[raw output-location-check] 成果物を office/ の中に書きました（成果物配置の二層原則の違反）。

office/ は AI 部署の運営情報（TODO・決定・Playbook・ジョブ記録）だけを置く場所です。
要約・図・スライド・原稿などユーザーが開く成果物は work/ の下に移してください:

${found}
移したら、そのファイルを指しているリンクや記録の参照も直してください。
EOF
exit 2
