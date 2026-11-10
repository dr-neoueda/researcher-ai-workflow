#!/bin/bash
# raw の hook が共通で使う関数（各 hook から source する）。Claude Code と Codex CLI の両方で動く。
#   HOOK_INPUT   … 標準入力の JSON（hook_read_input で読む）
#   hook_python  … 使える python のコマンド名（無ければ空）
#   hook_project … office/ のあるプロジェクトの場所（無ければ空）
# 個人のパスを書かない（配布物）。

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

hook_read_input() {
    HOOK_INPUT="$(cat)"
}

hook_python() {
    local c
    for c in python3 python; do
        # Windows の「python3」は Microsoft Store への案内だけのことがあるので、実際に動くかを確かめる
        if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' >/dev/null 2>&1; then
            echo "$c"
            return 0
        fi
    done
    return 0
}

hook_io() {
    local py
    py="$(hook_python)"
    [ -n "$py" ] || return 1
    printf '%s' "$HOOK_INPUT" | "$py" "$HOOK_DIR/_hookio.py" "$1"
}

hook_project() {
    local root
    if root="$(hook_io project)"; then
        printf '%s' "$root"
        return 0
    fi
    # python が無いとき: Claude Code の CLAUDE_PROJECT_DIR か、いまの場所
    root="${CLAUDE_PROJECT_DIR:-$PWD}"
    [ -d "$root/office" ] && printf '%s' "$root"
    return 0
}

hook_stop_active() {
    # python が無くても読めるように、まず文字列で見る（引き戻しを繰り返さないための大事な判定）
    case "$HOOK_INPUT" in
        *'"stop_hook_active":true'*|*'"stop_hook_active": true'*) return 0 ;;
    esac
    [ "$(hook_io stop-active 2>/dev/null)" = "1" ]
}
