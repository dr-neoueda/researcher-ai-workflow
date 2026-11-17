#!/bin/bash
# PostToolUse hook (raw plugin) — Claude Code と Codex CLI の両方で動く
# ファイルの書き込み（Claude Code の Edit / Write / MultiEdit、Codex の apply_patch。シェルで書いたものは
# 直前 2 分に office/ の中で変わったファイルとして拾う）が
# office/<dept>/<旧パス>/ に入ったとき、「成果物配置の二層原則」違反として警告する。
# 警告は標準エラー＋終了コード 2 で返す（PostToolUse の標準出力は Claude / Codex に届かない）。
# 書き込み自体はもう済んでいるので、止めるのではなく直し方を伝える。

set -uo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"
hook_read_input

# 旧い置き場所 → work/ の置き場所（警告の文と、シェルの道具のときのすばやい判定の両方で使う）
LEGACY_MAP="office/research/papers=work/papers
office/research/topics=work/topics
office/research/reports=work/reports
office/writing/manuscripts=work/manuscripts
office/analysis/results=work/analyses
office/analysis/figures=work/figures
office/analysis/notebooks=work/notebooks
office/presentation/slides=work/presentations/slides
office/presentation/figures=work/figures
office/engineering/scripts=work/scripts
office/engineering/tools=work/tools"

suggest() {
    local from to
    while IFS='=' read -r from to; do
        case "$1" in "${from}"/*) echo "${to}/${1#"${from}"/}"; return 0 ;; esac
    done <<< "$LEGACY_MAP"
}

project_dir="$(hook_project)"
[ -n "$project_dir" ] || exit 0

# シェルの道具（Bash など）は毎回呼ばれるので、旧い置き場所のフォルダが 1 つも無ければ Python を呼ばずに終える
shell_re='"tool_name"[[:space:]]*:[[:space:]]*"(Bash|shell|local_shell|exec_command)"'
if [[ $HOOK_INPUT =~ $shell_re ]]; then
    any=0
    while IFS='=' read -r from _; do
        [ -d "${project_dir}/${from}" ] && { any=1; break; }
    done <<< "$LEGACY_MAP"
    [ "$any" -eq 1 ] || exit 0
fi

# シェルの道具のときに見る場所（旧い置き場所だけ）を _hookio.py に渡す
RAW_LEGACY_PLACES="$(while IFS='=' read -r from _; do printf '%s\n' "$from"; done <<< "$LEGACY_MAP")"
export RAW_LEGACY_PLACES
paths="$(hook_io paths 2>/dev/null)" || exit 0  # python が無ければ何もしない（raw-setup が python を入れる）
[ -n "$paths" ] || exit 0

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
