#!/usr/bin/env bash
# lint-bash32.sh — macOS 標準の /bin/bash 3.2 で落ちる「ASCII でない字の直前の裸の変数」を探す。
# bash 3.2 は UTF-8 のロケールで、"$LOG" の直後に全角の「）」が来ると、その最初のバイトまで変数名に読む。set -u のスクリプトは
# 「unbound variable」で落ちる（v2.4.0 の setup/raw-setup.sh が最初の確認の前に落ちた）。直し方: ${LOG} と括る。
#
# コメントの行も、単引用符の中も区別せずに数える（ヒアドキュメントの中は「# 」で始まっても展開されるため。
# 展開されない場所で ${VAR} と書いても害は無い）。
#
# 使い方: 作業コピーの根で bash scripts/lint-bash32.sh
# 出力:   見つかった行（ファイル:行番号:中身）
# 終了:   0 = 無い、1 = 有る、2 = 検査そのものが動かない
set -u

PATTERN='\$[A-Za-z_][A-Za-z0-9_]*[^[:print:][:cntrl:]]'   # C ロケールで 0x80〜0xFF（ASCII でないバイト）だけ

# 検査そのものが動いているか（grep が失敗すると空の結果で素通りするので、既知の不良の例で確かめる）
probe=$(printf 'echo "$X\xef\xbc\x89"\n' | LC_ALL=C grep -c -E "$PATTERN" || true)
if [ "$probe" != "1" ]; then
  echo "grep が既知の不良の例を捕まえない（この環境では検査できない）"
  exit 2
fi

list_files() { # NUL 区切り（日本語・空白・改行の名前も、git の引用に頼らずそのまま渡す）
  if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git ls-files -z --cached --others --exclude-standard -- '*.sh'
  else
    find . -name '*.sh' -not -path '*/node_modules/*' -not -path './.git/*' -print0
  fi
}

found=0
while IFS= read -r -d '' f; do
  [ -e "$f" ] || continue                       # git に載っているが作業コピーで消したもの
  if [ ! -r "$f" ]; then
    printf '%s: 読めない\n' "$f"; found=1; continue
  fi
  hits=$(LC_ALL=C grep -n -E "$PATTERN" "$f")
  rc=$?
  if [ "$rc" -eq 0 ]; then
    found=1
    while IFS= read -r line; do printf '%s:%s\n' "$f" "$line"; done <<<"$hits"
  elif [ "$rc" -ne 1 ]; then
    printf '%s: grep が失敗した（%s）\n' "$f" "$rc"; found=1
  fi
done < <(list_files)
exit "$found"
