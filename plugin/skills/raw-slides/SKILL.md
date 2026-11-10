---
name: raw-slides
description: >
  研究発表用 PowerPoint スライドを SVG-first で生成する。Python の生成器で SVG（1280×720）を作り、
  native DrawingML pptx に変換するので、図形・文字・表が PowerPoint で直接編集できる。
  学会発表・論文紹介（journal club）・研究室報告会・講義の 4 用途に対応。定型の生成物に見える
  構造物を置かない低塗りのデザイン（和文 MS Gothic / 英数 Arial・本文 14 pt 以上）。
  検定→変換→後処理→出力検定を build_deck の 1 コマンドで流す。上付き・下付きの復元、グループ解除、
  動画（自動再生ループ）、発表ノート、手直し版への 1 枚差し替えに対応。各 CLI で自己完結（外部委譲なし）。
  スライド・パワポ・pptx・発表資料・学会発表・論文紹介・journal club・報告会・講義で発火。
trigger: /raw-slides
---

# raw-slides — 研究発表スライド生成（SVG-first）

## いつ使うか

- 「スライド作って」「パワポ作って」「発表資料お願い」「学会発表用に」「ポスター」
- 「この論文を紹介するスライドにして」「journal club」「報告会の資料」「講義スライド」

`office/presentation/`（プレゼン部）が無ければ `raw` でスキャフォールドを促す。**就活トラック**では「これは研究向けのスキルです」と伝える。

## 設計思想（重要）

**SVG を正として描き、同梱の変換器で native pptx にする。** python-pptx でレイアウトを組まない。図形・文字・表は PowerPoint で**直接編集できる**（ラスタ画像にしない）。

- **`references/design-system.md` を発火時に必ず読む。** 既定のデザインと文章の規約がここにある。
- **SVG は手で書かず、`scripts/deck_chrome.py`・`deck_parts.py` を使う Python の生成器で作る。** 手本は `references/sample_deck.py`。部品が規約を守り、行数の超過も検定する。
- **ビルドは `scripts/build_deck.py` の 1 コマンド。** 検定・変換・後処理・出力検定を固定の順で流し、落ちたら配布先に何も出さない。手順を自分で組み直さない（後処理の抜けはゲートでは気づけない）。
- **各 CLI で自己完結**：Codex CLI / Claude Code / GitHub Copilot CLI のどれでも、その CLI 自身が作る。別 CLI へ委譲しない。
- **出力は pptx のみ**（§出力規約）。

`${SKILL}` = このスキルの install 位置（Claude Code: `~/.claude/plugins/marketplaces/*/skills/raw-slides/`）。以下のコマンドの `${SKILL}` を実パスに置換して実行する。Windows では `python3` を `py` に読み替える。

## はじめてモードを尊重する

`office/CLAUDE.md`（Codex/Copilot は `AGENTS.md`、Gemini は `GEMINI.md`）冒頭に `> 運用モード: はじめて` があれば、`raw` skill の「はじめてモードの挙動」を全応答に適用する。

## デッキのフォルダ

```
work/presentations/slides/
├── <deck>.pptx                 配布物（これだけをユーザーが開く）
└── _src/<deck>/                作業場所
    ├── gen_deck.py             生成器（SVG を書く）
    ├── svg_output/*.svg        スライド。名前順が並び（01_cover.svg, 02_...）
    ├── images/                 図。SVG からは ../images/<名前> で参照する
    ├── notes/<SVG の名前>.md   発表原稿（任意。各枚のノートに入る）
    └── videos.json             動画の置き場所（任意）
```

## ワークフロー（Step A–H）

### Step A: 用途と素材を確定
| 項目 | 内容 |
|---|---|
| 用途 | 論文紹介 / 学会発表 / 報告会 / 講義 |
| 元データ | 論文紹介＝`work/papers/`（`raw-register` 登録の md ＋原論文 PDF）／ 学会・報告会＝`work/manuscripts/`・`work/profile/key-findings.md`・`work/analyses/`／ 講義＝指定教材 |
| **ユーザー画像** | **設計の前に `work/presentations/figures/` を必ず確認**。ユーザーが置いた画像（顕微鏡写真・装置スクショ・ロゴ 等）と `work/figures/`・`work/analyses/` の図を候補に挙げる（質の高いスライドの主材料）。使うものは `images/` にコピーする |
| 言語・場面・制約 | 日本語/英語、枚数目安（下表）、必須で入れる図 |

**自分で作れない画像**（写実画像・装置の写真・表紙の画像など）が欲しいときは、空欄や代用でごまかさず、**必要画像リスト**をユーザーに出す（用途・枚番号・縦横比・背景・推奨ファイル名。生成 AI で作るものは英語のプロンプトも添える）。

### Step B: 図を用意する（`images/` へ）
- **数値で形が決まる図は matplotlib**：`scripts/fig_style.py` を使う。値はデータファイルから読む（`work/analyses/` の表など）。手で写さない。
  ```python
  import fig_style as fs
  fs.setup()
  fig = fs.figure(520, 340)        # 貼る箱の px
  ax = fig.add_subplot()
  ...
  fs.style_axes(ax)                # 目盛りを内向きに
  fs.save(fig, "images/fig_rate.png")
  ```
- **論文図の切り抜き**：まずページを見て座標を当て、region で高解像度に切り抜く。**図の部分だけ**にして、キャプション・本文を含めない。
  ```bash
  python3 ${SKILL}/scripts/crop_paper_figures.py page   <pdf> <page_no> <scratchpad>/pg.png --dpi 150
  python3 ${SKILL}/scripts/crop_paper_figures.py region <pdf> <page_no> <x0> <y0> <x1> <y1> images/fig1.png --dpi 300
  ```
- **数式（LaTeX）**：`scripts/render_latex.py` で透過 PNG にする。既定は matplotlib のオフライン。`\ce{}` などフル LaTeX が要る式だけ `--online`（codecogs へ送信）。
  ```bash
  python3 ${SKILL}/scripts/render_latex.py "k = A e^{-E_a/RT}" images/eq_rate.png --dpi 300 --color "#16283D"
  ```
- **動画**：`scripts/prepare_video.py` で変換する（H.264・BT.709・音声なし）。10 秒ほどのループにする。
  ```bash
  python3 ${SKILL}/scripts/prepare_video.py raw.mp4 images/melt.mp4 --poster images/melt.png --start 12 --duration 40 --speed 4
  ```

### Step C: 生成器で SVG を書く
`references/sample_deck.py` を手本に `gen_deck.py` を書く。
```python
import sys
sys.path.insert(0, r"${SKILL}/scripts")
import deck_chrome as dc
import deck_parts as dp

body = (dc.header("赤外吸収")                       # 短い名詞句。リード文は置かない
        + dc.bullet(80, 186, "吸収は 1705 cm^{-1} に現れる")
        + dc.callout(80, 240, 1120, 60, ["カルボニルの伸縮に帰属する"])
        + dc.footer(2, 12))
Path("svg_output/02_ir.svg").write_text(dc.svg(body), encoding="utf-8")
```
- 枚の並びと数値は 1 か所に集める（番号を手で振らない。値を手で写さない）。
- 本文の頭は線（y=140）の直下から置く。文献・細かい条件だけ `fine=True` で小さくする。
- 図は `dp.figure(images / "fig.png", x, y, w=...)`。動画の枠は `dp.frame(...)`。

### Step D: ビルド
```bash
python3 ${SKILL}/scripts/build_deck.py work/presentations/slides/_src/<deck>
```
次を順に流し、`work/presentations/slides/<deck>.pptx` を作る。落ちたら直して再実行する（検定を外さない）。

1. 検定：`svg_quality_checker`（禁止要素・画像）→ `assert_no_overlap`（文字の重なり・はみ出し）→ `assert_font_rule`（和文の豆腐）→ `check_margins`（右余白 1200）
2. 変換：切り替え効果なし。`notes/` は各枚のノートに入る
3. 後処理：`fix_ea_font` → `fix_scripts`（上付き・下付きの復元）→ `add_videos` → `ungroup_pptx`（グループを解く）
4. 出力検定：切り替え効果 0・和文の run が MS Gothic

`[確認] 14 pt 未満の文字` が出たら、文献・注・ページ番号以外が混ざっていないかを見る。

### Step E: 目視 QA（プレビューは scratchpad のみ）
```bash
python3 ${SKILL}/scripts/make_preview.py work/presentations/slides/_src/<deck> <scratchpad>/preview
```
**全ページを絵で見る。** 文字と画像・文字と枠の重なりと、図の中の文字はゲートが見ない（`design-system.md` §10）。Chrome か Edge が要る。プレビューは 1280×720 を検定する。

### Step F: 文章の見直し
**数値の照合（ビルドのたびに必ず）**：スライドの数は、`_src/<deck>/facts.md`（または元になった原稿の `work/manuscripts/<doc-slug>/facts.md`）からだけ写す。書き出した pptx の数を機械で抜き出して照合する（生成器のコードではなく、出来上がった pptx に掛ける）。
```bash
python3 ${SKILL}/../raw-write/scripts/check_numbers.py work/presentations/slides/<deck>.pptx --facts work/presentations/slides/_src/<deck>/facts.md
```
「一覧に無い数」は一次記録で引き直して一覧に足す。「指数だけ違う・符号が違う・丸め方が合わない」は一覧の書き方か誤りかを確かめる。終了コード 0 になってから渡す（照合の読み方は `raw-write` の Step 5 と同じ）。

`design-system.md` §2・§11 に照らして文字を検索する。「—」、話し言葉（合う・使って・ほぼ同じ・だけ・？）、経緯の語り（以前・やり直・訂正・実は・判明）、見出しの人名。枚を外したら「補足 N」などの相互参照も数え直す。

### Step G: 動画を貼るとき
SVG には枠と説明だけを描き、`_src/<deck>/videos.json` に置き場所を書く。`build_deck` が自動で貼る（スライドを開くと再生・ループ）。
```json
[{"slide": "04_micro", "mp4": "melt.mp4", "poster": "melt.png", "x": 81, "y": 171, "w": 478, "h": 268}]
```
`slide` は SVG の名前、`mp4` と `poster` は `images/` の中のファイル名、座標はスライドの px。PowerPoint での実再生はユーザーに確認してもらう。

### Step H: 手で直された pptx を更新するとき
ユーザーが PowerPoint で直した pptx は**正本**であり、生成器から作り直すと直しが消える。`build_deck` は前回の書き出しと中身が違う出力を上書きせず止まる。**`--force` を勝手に付けない。** 直しを残したまま更新するときは `scripts/copy_slide_pptx.py` を使う。
```python
from pptx import Presentation
import copy_slide_pptx as cs

deck = Presentation("work/presentations/slides/<deck>.pptx")           # 手で直された正本
new = Presentation("work/presentations/slides/_src/<deck>/new.pptx")   # 生成器で作った版
cs.replace_slide(deck, 5, new.slides[4])     # 手の入っていない 5 枚目を丸ごと替える
cs.set_notes(deck.slides[4], "発表原稿")
deck.save("work/presentations/slides/<deck>.pptx")
```
図だけ替えるなら `replace_picture`、部品だけ足すなら `copy_shapes`。当てた後は、**意図した枚だけが変わった**ことを前の版と枚ごとに比べて確かめる。繰り返す構成やレシピは `raw-playbook` 方式で `work/presentations/_playbook.md` に残す。

## 出力規約（HARD rule）
- **配布先（`work/presentations/slides/`）に置く成果物は `.pptx` のみ。** preview PNG・中間 SVG・ページ画像をコピーしない。
- preview PNG は目視 QA 専用として scratchpad で生成し、QA 後は放置でよい。
- デザイン案を文章で聞かない。別ファイルで試作し、実物を見比べてもらってから決める。

## 用途別の目安
| 用途 | 想定枚数 | 特徴 |
|------|---------|------|
| 論文紹介（journal club） | 6–12 | **原論文図が主役**（切り抜き）、自作図表は補助。①表紙 ②背景 ③機構 ④自作データ ⑤主要図 ⑥結論＋**自研究への接続** |
| 学会発表（口頭） | 発表 1 分 1 枚 | 専門家向け、結果の図が主体 |
| 研究室報告会・進捗 | 15–25 | 自前データ主体。補助資料は質疑用なので本編に混ぜない |
| 講義・チュートリアル | 15–30 | 平易語、概念フロー図、目標＋前提＋まとめ |

## 同梱資産
| パス | 役割 |
|---|---|
| `references/design-system.md` | デザインと文章の規約。**発火時必読** |
| `references/sample_deck.py` | 生成器の手本（全機能を使う見本デッキ） |
| `scripts/build_deck.py` | 検定→変換→後処理→出力検定を流す本体 |
| `scripts/deck_chrome.py` / `deck_parts.py` | 見出し・本文・強調帯・表・図枠などの部品 |
| `scripts/fig_style.py` | matplotlib 図の書式 |
| `scripts/assert_font_rule.py` / `assert_no_overlap.py` / `check_margins.py` | 検定 |
| `scripts/fix_ea_font.py` / `fix_scripts.py` / `ungroup_pptx.py` | pptx の後処理 |
| `scripts/add_videos.py` / `prepare_video.py` | 動画の貼り付けと変換 |
| `scripts/copy_slide_pptx.py` | 手で直された pptx への差し替え |
| `scripts/make_preview.py` | 目視 QA 用のプレビュー |
| `scripts/crop_paper_figures.py` / `render_latex.py` | 論文図の切り抜き・数式 |
| `vendor/` | 変換器と `svg_quality_checker`（上流 PPT Master・MIT、`vendor/NOTICE.md` 参照） |

## 依存
```bash
pip install python-pptx Pillow   # 必須
pip install matplotlib           # 図・数式
pip install PyMuPDF              # 論文図の切り抜き
# ffmpeg                         動画を使うとき
# Chrome または Edge             プレビュー
# MS Gothic                      Windows は標準。macOS は Office 同梱。無ければ図の和文は別のフォントになる（警告が出る）
```

## トラブルシュート
| 症状 | 対処 |
|------|------|
| `svg_output に SVG が無い` | 旧いデッキ（`_src/<deck>/*.svg`）は `svg_output/` へ移す |
| `assert_font_rule` に通らない | 和文・丸数字が Arial の run にある。`dc.text` などの部品で書く |
| `assert_no_overlap` に通らない | 座標を調整する。文字に `transform` を使っているなら `x` / `y` で書く |
| `check_margins` に通らない | 行を短くするか折り返す。右端は 1200 px まで |
| `callout ... need height` / `行の幅` | 枠を広げるか行を減らす |
| `pptx に見つからない行` | dy で行を積んだ `<text>` は 1 段落になる。1 行 1 `<text>` で書き直す（部品なら起きない） |
| `手で直した可能性` | Step H。捨ててよいとユーザーが言ったときだけ `--force` |
| 図が編集できない | 図形と文字で描いたか確認する。ラスタは写真・論文図・数値図のみ |

## 関連 Skill
- `raw` — presentation 部を含む scaffold
- `raw-register` — 論文 PDF を `work/papers/` に登録（journal club 素材）
- `raw-write` — 自分の論文・要旨（学会/報告会スライドの元データ）
- `raw-playbook` — 構成・レシピの蓄積
