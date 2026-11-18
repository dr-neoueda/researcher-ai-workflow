#!/usr/bin/env bash
# lint-bash32.sh — macOS 標準の /bin/bash 3.2 で落ちる「ASCII でない字の直前の裸の変数」を探す。
# bash 3.2 は UTF-8 のロケールで、"$LOG" の直後に全角の「）」が来ると、その最初のバイトまで変数名に読む。set -u のスクリプトは
# 「unbound variable」で落ちる（v2.4.0 の setup/raw-setup.sh が最初の確認の前に落ちた）。直し方: ${LOG} と括る。
#
# コメントの行も、引用符の中も区別せずに数える（ヒアドキュメントの中は「# 」や「'」があっても展開される。
# 引用符を解析すると、解析の誤りで本物を見逃すほうが害が大きい）。\$名前 は展開されない（文字どおりの $）ので数えない。
# 文字どおりの「$名前）」を出したいとき: 単引用符の中なら "\$名前）" に書き換える（同じ出力）。引用した
# ヒアドキュメント（<<'EOF'）の中なら、引用しないヒアドキュメントにして \$名前 と書く。
# ただしバッククォート・eval・trap・ssh・-c（sh -c など）のある行では、\ の数によらず数える。バッククォートの中では
# \$ の \ が外れてから中のコマンドが読まれ、eval・trap・sh -c は文字列をもう一度読み、ssh は向こうのシェルが読むので、
# \$名前 も展開される（Codex r2）。バッククォートは $(…) に書き換えると \$名前 が文字どおりになる。
# 見逃す形: シェルに流し込むヒアドキュメント（bash <<EOF）の中の \$名前（行だけでは、どこへ流すのか分からない）。
# 見逃す形: 単引用符の末尾の \ のすぐ後の $名前（例 'C:\'$X の後に全角の字）。\ は単引用符の中の字で $ を守らないが、
# 引用符を解析しないので文字どおりの \$ と区別できない。
#
# 使い方: 作業コピーの根で bash scripts/lint-bash32.sh
# 出力:   見つかった行（ファイル:行番号:中身）
# 終了:   0 = 無い、1 = 有る、2 = 検査そのものが動かない
set -u

# $ の前の \ が偶数個（0 個を含む）なら展開される。最後の [] は C ロケールで 0x80〜0xFF（ASCII でないバイト）だけ
PATTERN='(^|[^\\])(\\\\)*\$[A-Za-z_][A-Za-z0-9_]*[^[:print:][:cntrl:]]'
# もう一度読まれる行（バッククォート・eval・trap・ssh・-c）では、\ の数によらず
ANY='\$[A-Za-z_][A-Za-z0-9_]*[^[:print:][:cntrl:]]'
REPARSED='(`|(^|[^A-Za-z0-9_])(eval|trap|ssh)([^A-Za-z0-9_]|$)|(^|[[:space:]])-[A-Za-z]*c([[:space:]]|$))'
HINT='直し方: 変数として展開するなら ${名前} と括る。文字どおりの $ なら \$名前 と書く。バッククォート・eval・trap・ssh・-c の行は \ の数によらず挙げる（もう一度読まれて展開される。バッククォートは $(…) に。上の説明を参照）'
lint_grep() { LC_ALL=C grep "$@" -E -e "$PATTERN" -e "${REPARSED}.*${ANY}" -e "${ANY}.*${REPARSED}"; }

# 検査そのものが動いているか（grep が失敗すると空の結果で素通りするので、既知の例で確かめる）。
# 不良 3 つ（後に全角の括弧が続く、裸の $X と \\$X とバッククォートの中の \$X）を捕まえ、良品 1 つ（\$X の後に全角の括弧）を通すこと
probe=$(printf 'echo "$X\xef\xbc\x89"\necho "\\$X\xef\xbc\x89"\necho "\\\\$X\xef\xbc\x89"\nv=\x60echo "\\$X\xef\xbc\x89"\x60\n' | lint_grep -c || true)
if [ "$probe" != "3" ]; then
  echo "grep が既知の例を正しく分けない（この環境では検査できない）"
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
hit=0
while IFS= read -r -d '' f; do
  [ -e "$f" ] || continue                       # git に載っているが作業コピーで消したもの
  if [ ! -r "$f" ]; then
    printf '%s: 読めない\n' "$f"; found=1; continue
  fi
  hits=$(lint_grep -n "$f")
  rc=$?
  if [ "$rc" -eq 0 ]; then
    found=1; hit=1
    while IFS= read -r line; do printf '%s:%s\n' "$f" "$line"; done <<<"$hits"
  elif [ "$rc" -ne 1 ]; then
    printf '%s: grep が失敗した（%s）\n' "$f" "$rc"; found=1
  fi
done < <(list_files)
[ "$hit" -eq 1 ] && echo "$HINT"
exit "$found"
