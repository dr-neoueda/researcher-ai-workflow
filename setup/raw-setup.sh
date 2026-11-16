#!/usr/bin/env bash
# raw-setup.sh — macOS 向け raw 前提ツールの一括セットアップ
#
# 方針: OS を検出し、必要なツールが「使える状態か」を確認 → 計画を提示 → 一度だけ承認 →
#       順番にインストール。既に入っているものはスキップ（冪等）。
# 安全: このスクリプト自身は sudo を使わない。ただし Homebrew の公式の導入は Mac のログインパスワード（管理者）を
#       聞き、開発ツールの導入の画面を出すことがある。各ステップの成否を記録し、
#       失敗しても続行して最後にまとめて報告する（失敗があれば終了コード 1）。
# 注意: macOS 標準の bash は 3.2。日本語の直前の変数は必ず ${VAR} と括る
#       （括らないと全角の字の最初のバイトまで変数名に読み、set -u で落ちる）。
#
# 使い方:
#   bash raw-setup.sh
#
# 対応 OS: macOS。Windows は raw-setup.ps1 を使う。
# テスト用の差し替え（ふだんは設定しない）:
#   RAW_SETUP_BREW_PREFIXES     Homebrew を探す場所（既定: /opt/homebrew /usr/local）
#   RAW_SETUP_HOMEBREW_INSTALL  Homebrew の導入コマンド（既定: 公式の install.sh）

set -u
LOG="${TMPDIR:-/tmp}/raw-setup-$(date +%Y%m%d-%H%M%S).log"
FAILS=0

c_blue=$'\033[0;34m'; c_green=$'\033[0;32m'; c_red=$'\033[0;31m'; c_dim=$'\033[2m'; c_off=$'\033[0m'
say()     { printf '%s\n' "$*"; }
section() { printf '\n%s== %s ==%s\n' "$c_blue" "$*" "$c_off"; }
ok()      { printf '%s  OK %s %s\n' "$c_green" "$c_off" "$*"; }
skip()    { printf '%s skip%s %s\n' "$c_dim" "$c_off" "$*"; }
fail()    { FAILS=$((FAILS + 1)); printf '%s FAIL%s %s\n' "$c_red" "$c_off" "$*"; }

if [ "$(uname -s)" != "Darwin" ]; then
  say "このスクリプトは macOS 用です。Windows では raw-setup.ps1 を使ってください。"
  exit 1
fi

have() { command -v "$1" >/dev/null 2>&1; }

# 開発ツール（Command Line Tools）が無い Mac の /usr/bin/git・/usr/bin/python3 は、
# 実行すると「入れますか」を出すだけの入口。名前があっても使えるとはみなさない。
clt_missing() { # xcode-select -p が成功しても、OS の更新の後などで中身が無いことがある（git の有無で見る。実行はしない）
  local dir
  dir="$(xcode-select -p 2>/dev/null)" || return 0
  [ -x "${dir}/usr/bin/git" ] && return 1
  return 0
}
apple_stub() { [ "$(command -v "$1")" = "/usr/bin/$1" ] && clt_missing; }
python_new_enough() { python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; }

ready() { # 使える状態か（名前が見つかるかではない）
  case "$1" in
    git)     have git && ! apple_stub git ;;
    python3) have python3 && ! apple_stub python3 && python_new_enough ;;
    *)       have "$1" ;;
  esac
}

# Homebrew は /opt/homebrew（Apple Silicon）か /usr/local（Intel）に入り、PATH に足すのは利用者の仕事。
# 入れた直後や、PATH を足していない Mac でも brew と brew で入れたものが見えるよう、置き場所から読み込む。
BREW_LOADED_FROM=""
load_brew() {
  have brew && return 0
  local p
  for p in ${RAW_SETUP_BREW_PREFIXES:-/opt/homebrew /usr/local}; do
    if [ -x "${p}/bin/brew" ]; then
      eval "$("${p}/bin/brew" shellenv)"
      BREW_LOADED_FROM="${p}"
      return 0
    fi
  done
  return 1
}
persist_brew() { # 新しいターミナルでも見えるよう ~/.zprofile に足す（すでに書いてあれば足さない）
  local prefix="$1" rc="${HOME}/.zprofile"
  [ -n "${prefix}" ] || return 0
  if [ -f "${rc}" ] && grep -v '^[[:space:]]*#' "${rc}" | grep -Fq "${prefix}/bin/brew shellenv"; then return 0; fi
  if printf '\neval "$(%s/bin/brew shellenv)"\n' "${prefix}" >> "${rc}"; then
    ok "~/.zprofile に Homebrew の PATH を足しました（新しいターミナルで有効）"
  else
    fail "~/.zprofile に Homebrew の PATH を足せませんでした（手で足してください: eval \"\$(${prefix}/bin/brew shellenv)\"）"
  fi
}
install_homebrew() {
  if [ -n "${RAW_SETUP_HOMEBREW_INSTALL:-}" ]; then
    bash -c "${RAW_SETUP_HOMEBREW_INSTALL}"
  else
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  fi
}

load_brew   # ~/.zprofile への追記は承認の後（中止したら何も変えない）

# --- 計画づくり -------------------------------------------------------------
# 各ツール: "表示名|チェックコマンド|インストールコマンド"
REQUIRED=(
  "Node.js|node|brew install node"
  "git|git|brew install git"
  "Python 3|python3|brew install python"
  "poppler (pdftoppm)|pdftoppm|brew install poppler"
)
OPTIONAL=(
  "GitHub CLI (gh)|gh|brew install gh"
  "LibreOffice|soffice|brew install --cask libreoffice"
)
PY_PKGS=(python-pptx matplotlib pillow numpy)

section "現在の状態"
plan_req=(); plan_opt=()
for entry in "${REQUIRED[@]}"; do
  IFS='|' read -r name chk inst <<<"$entry"
  if ready "$chk"; then
    ok "${name} は導入済み"
  elif [ "$chk" = "python3" ] && have python3 && ! apple_stub python3; then
    say "  ・${name}（3.10 以上が要る。今は $(python3 --version 2>&1)）→ インストール予定"; plan_req+=("$entry")
  else
    say "  ・${name} → インストール予定"; plan_req+=("$entry")
  fi
done
# Claude Code（CLI 本体。node があれば npm 経由で導入可能）
claude_plan=0
if have claude; then ok "Claude Code は導入済み"; else say "  ・Claude Code → npm でインストール予定"; claude_plan=1; fi
# Python パッケージ
py_missing=()
if ready python3; then
  for p in "${PY_PKGS[@]}"; do
    mod="${p//-/_}"; [ "$p" = "pillow" ] && mod="PIL"; [ "$p" = "python-pptx" ] && mod="pptx"
    if python3 -c "import $mod" >/dev/null 2>&1; then ok "Python: ${p} は導入済み"; else say "  ・Python: ${p} → インストール予定"; py_missing+=("$p"); fi
  done
else
  say "  ・Python パッケージ → Python 導入後にまとめてインストール予定"; py_missing=("${PY_PKGS[@]}")
fi
say ""
say "任意（あると便利。後でも入れられます）:"
for entry in "${OPTIONAL[@]}"; do
  IFS='|' read -r name chk inst <<<"$entry"
  if have "$chk"; then ok "${name} は導入済み"; else say "  ・${name} → 任意でインストール"; plan_opt+=("$entry"); fi
done

if [ ${#plan_req[@]} -eq 0 ] && [ ${#py_missing[@]} -eq 0 ] && [ $claude_plan -eq 0 ]; then
  section "必須ツールはすべて揃っています"
  say "任意ツールを入れたい場合のみ続行してください。"
fi

# --- 承認（一度だけ） -------------------------------------------------------
section "上記の計画でインストールを実行します"
say "（ログ: ${LOG}）"
printf 'よろしいですか？ [y/N]: '
read -r ans
case "$ans" in y|Y|yes|YES) ;; *) say "中止しました。"; exit 0;; esac
persist_brew "${BREW_LOADED_FROM}"   # Homebrew は入っているが PATH に無かった Mac

run() { # 表示名, コマンド...
  local name="$1"; shift
  printf '%s installing%s %s ...\n' "$c_blue" "$c_off" "$name"
  local status=0
  "$@" >>"$LOG" 2>&1 || status=$?
  hash -r   # 入れたばかりのコマンド（brew の python3 等）に切り替える。bash は前に走らせた場所を覚えている
  if [ "$status" -eq 0 ]; then ok "$name"; return 0; else fail "${name}（詳細は ${LOG}）"; return 1; fi
}

# --- Homebrew（多くのインストールの前提） -----------------------------------
need_brew=0
{ [ ${#plan_req[@]} -gt 0 ] || [ ${#plan_opt[@]} -gt 0 ]; } && need_brew=1
if [ $need_brew -eq 1 ] && ! have brew; then
  section "Homebrew の導入"
  say "Homebrew が必要です。次の公式コマンドで導入します（入れたら ~/.zprofile に PATH を足します）。"
  say "途中で Mac のログインパスワードを聞かれます（管理者のアカウントが要ります）。開発ツールの導入の画面が出たら「インストール」を押してください。数分〜十数分かかります:"
  say '  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
  printf 'Homebrew を導入しますか？ [y/N]: '
  read -r b
  case "$b" in
    y|Y|yes|YES)
      if install_homebrew && load_brew; then
        ok "Homebrew"; persist_brew "${BREW_LOADED_FROM}"
      else
        fail "Homebrew の導入（入ったのに見つからないときは、新しいターミナルでもう一度実行してください）"
      fi ;;
    *) say "Homebrew をスキップ。brew が要るツールは飛ばします。";;
  esac
fi

# --- 必須ツール -------------------------------------------------------------
section "必須ツールのインストール"
for entry in "${plan_req[@]}"; do
  IFS='|' read -r name chk inst <<<"$entry"
  if have brew; then run "$name" bash -c "$inst"; else skip "${name}（brew 未導入のため）"; fi
done

# --- Claude Code ------------------------------------------------------------
if [ $claude_plan -eq 1 ]; then
  section "Claude Code (CLI)"
  if have npm; then run "Claude Code" npm install -g @anthropic-ai/claude-code
  else skip "Claude Code（npm 未導入。Node.js 導入後に再実行してください）"; fi
fi

# --- 代替 AI CLI（任意・案内のみ） -----------------------------------------
# raw は Claude Code を既定（Tier 1）として導入するが、Codex CLI / GitHub Copilot CLI でも動く。
# 好みに応じて npm（Node.js 導入後）で個別に追加できる。
section "代替 AI CLI（任意）"
if have codex;   then ok "Codex CLI は導入済み";          else say "  ・Codex CLI を使う場合: npm install -g @openai/codex"; fi
if have copilot; then ok "GitHub Copilot CLI は導入済み"; else say "  ・GitHub Copilot CLI を使う場合: npm install -g @github/copilot（Node.js 22 以上）"; fi

# --- Python パッケージ ------------------------------------------------------
if [ ${#py_missing[@]} -gt 0 ] && ready python3; then
  section "Python パッケージ"
  if python3 -m pip install "${py_missing[@]}" >>"$LOG" 2>&1; then ok "Python packages: ${py_missing[*]}"
  elif python3 -m pip install --user --break-system-packages "${py_missing[@]}" >>"$LOG" 2>&1; then ok "Python packages（--user）: ${py_missing[*]}"
  else fail "Python packages（詳細は ${LOG}）。venv の利用も検討してください"; fi
fi

# --- 任意ツール -------------------------------------------------------------
if [ ${#plan_opt[@]} -gt 0 ]; then
  section "任意ツール"
  for entry in "${plan_opt[@]}"; do
    IFS='|' read -r name chk inst <<<"$entry"
    printf '%s を入れますか？ [y/N]: ' "$name"; read -r o
    case "$o" in y|Y|yes|YES) if have brew; then run "$name" bash -c "$inst"; else skip "${name}（brew 未導入）"; fi;; *) skip "$name";; esac
  done
fi

# --- 動作確認 ---------------------------------------------------------------
section "動作確認"
for c in "node -v" "git --version" "python3 --version" "pdftoppm -v" "claude --version"; do
  bin="${c%% *}"
  if ready "$bin"; then printf '  %s: %s\n' "$bin" "$(eval "$c" 2>&1 | sed -n 1p)"
  elif [ "$bin" = "python3" ] && have python3 && ! apple_stub python3; then fail "python3 は 3.10 以上が要ります（今は $(python3 --version 2>&1)）"
  else fail "${bin} が見つかりません"; fi
done
if ready python3; then
  python3 -c "import pptx, matplotlib, PIL, numpy; print('  python deps OK')" 2>/dev/null || fail "Python パッケージの import に失敗"
fi

if [ "$FAILS" -gt 0 ]; then
  section "うまくいかなかったもの: ${FAILS} 件"
  say "上の FAIL の行と詳細ログ（${LOG}）を確かめ、直してから新しいターミナルでもう一度 bash raw-setup.sh を実行してください（入っているものは飛ばします）。"
  exit 1
fi
section "完了"
say "詳細ログ: ${LOG}"
say "Homebrew を入れたときは、新しいターミナルを開いてから使ってください（~/.zprofile の PATH が読まれます）。"
say "次は、研究プロジェクトのフォルダで 'claude'（または 'codex'）を起動し raw を実行してください（'copilot' の版は旧名 caw のまま保留中です）。"
