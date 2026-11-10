# 再開ポイント — 最終更新 2026-11-10

> 次回このプロジェクトを再開するときは、まずこのファイルを読んでください。
> **このファイルの記述は「最後に見た日」であって「正しさの保証」ではありません。**
> 実態は必ず `git log -1` / `.claude-plugin/marketplace.json` の version / `scripts/check-consistency.sh` で確認してください。

## 現在地（2026-11-10 実測）

| 項目 | 値 |
|---|---|
| **配布版** | plugin **2.1.0** / codex 2.1.0 / copilot 1.46.0（**保留中**・旧名 caw）/ gemini 1.49.0（凍結） |
| **直近の作業** | v2.1 系：研究側の更新を 4 本の PR で進めている（2026-11-10 承認）。PR 1＝測定データの置き場の統一・確かめ方の決まり 6 行・数値の照合（`check_numbers.py`）。続き：PR 2＝Codex 版に hook → PR 3＝計算の見張りを既定に（`jobwatch`）→ PR 4＝`raw-ask`（登録論文から答え、無ければ Web で URL つき）。**就活トラックは v2.0.1 で開発終了**（2026-11-10 ユーザー決定。削除はしない） |
| テスト | `plugin/skills` 全体で 332 passed（scaffold 77・check_numbers 54、カバレッジ 99 %） |
| 配布元 | https://github.com/dr-neoueda/researcher-ai-workflow（2026-11-06 に `chemist-ai-workflow` から改名。旧 URL は GitHub が転送） |

## ★ 商品モデル（2026-08-21 確定）— 売り物はプラグインではない

| 要素 | 位置づけ | 課金 |
|---|---|---|
| **プラグイン `raw`** | 無料の配布物。GitHub で公開し続ける | 無料 |
| **導入伴走（マンツーマン）** | **商品本体**。研究室・個人単位で入り、その人の研究に合わせて部署構成・Playbook・MCP まで初期化する | 有料 |
| **教材** | 伴走した相手の**復習用の付属物**。教材だけを単体では売らない | 伴走に付属 |
| **導入体験の作り込み**（オンボーディング / `raw-setup` / `raw-doctor`） | 伴走の土台。開発の重心 | — |

**集合研修（セミナー・ハンズオン）形式は採らない。** テスト会 2 回はその形だったが、
開催のたびに時間が消え、SPRING 期間の終了とともに続かないため。

### 商品名（2026-11-06 改名）

| | |
|---|---|
| 日本語名 | **研究者のための AI エージェント導入伴走** |
| 英語名 | **Researcher's AI Workflow** |
| コマンド / プラグイン ID | **`raw`** |
| 配布元 / マーケットプレイス ID | **`dr-neoueda/researcher-ai-workflow`** |

日本語名に **「エージェント」を必ず含める**（ChatGPT に質問する話ではなく、
エージェントが部署として働く話であることが中核の差別化。短さと引き換えに落とさない）。
旧名は「化学者のための AI エージェント導入伴走」／ Chemist's AI Workflow ／ `caw` ／ `chemist-ai-workflow`。2026-08-21 には改名コストを理由に据え置いたが、2026-11-06 に対象を理工系へ広げるのに合わせて全部変えた（ユーザー判断。経緯は `docs/concept.md`）。コマンド名 `raw` は「生データ」と同じ綴りなので、文書では生データを「生データ」と書く。

## ⚠️ 当初計画からの逸脱（記録）

立ち上げ時（2026-04-29）の計画は **「教材（テキスト商材）を書いて売る」** だったが、
実際に出来上がったのは **「4 CLI 対応のプラグイン ＋ ドキュメントサイト」** で、
売り方は上記のとおり **「導入伴走」** に着地した。

- `content/` `templates/` `case-studies/` `marketing/` は**存在しない**（作られないまま方針転換した）
- 教材の章を書く代わりに、**スキルとして実装した**
- したがって古い roadmap の「教材ページ数」「core/ を 5〜7 章で執筆」等の指標は**もう意味を持たない**

## 何が出来上がっているか

### スキル 15 本（Claude Code 版・Codex CLI 版とも 15・byte 一致ミラー）

**研究トラック（12）**
`raw`（オンボーディング＋運営モード）/ `raw-research`（論文検索→HTML リスト）/ `raw-register`（PDF→書誌付き要約 md→KB 登録）/ `raw-write`（論文・申請書・要旨を本人の文体で執筆）/ `raw-input`（7 ソフトの入力雛形）/ `raw-playbook`（log 解析→Lessons 追記）/ `raw-analyze`（手法非依存の解析コンパニオン）/ `raw-slides`（SVG-first→native pptx）/ `raw-setup`（外部ツール導入）/ `raw-doctor`（構造健全性チェック）/ `raw-intake`（統合 inbox 自動仕分け）/ `raw-report`（匿名動作レポート）

**就活トラック（3）**
`raw-es` / `raw-interview` / `raw-events`

### CLI 別の到達度

| CLI | 状態 |
|---|---|
| **Codex CLI**（Tier 1・**本命**） | 15 スキル。**Hooks は未移植（要対応）**。選定理由＝**5 時間ウィンドウが撤廃され週次上限のみ**（2026-07-12 に OpenAI が撤廃、8 月時点で継続中）＝**伴走の 3 時間セッションが途中で上限に当たらない** |
| **Claude Code**（Tier 2） | 15 スキル ＋ Hooks 3 本（SessionStart / PostToolUse / Stop）。実装は最も厚い |
| **Copilot CLI**（企業向け） | ✅ **2026-08-21 に 15 スキルへフルポート完了**。13 スキルは Codex 版と byte 一致（consistency がディレクトリ単位で強制）。**hooks 未移植**・**`caw-slides` の Windows 実機確認が未実施**。**2026-11-06 から開発を保留**（v1.78 の内容・旧名 `caw` のまま。`copilot-plugin/PAUSED.md`） |
| **Gemini CLI** | ⛔ **2026-08-21 凍結・非推奨**。無料枠ではオンボーディングを完走できず、商品モデル（導入伴走）でも勧める場面が無い。追従させない。`gemini-plugin/FROZEN.md` 参照 |

### その他

- **9 部署**スキャフォールド：secretary / research / engineering / computation / experiment / analysis / writing / review / presentation
- `raw-slides` は **v1.78.0 で lab の到達点へ更新**：生成器（`deck_chrome` / `deck_parts`）＋ `build_deck` の 1 コマンド。lab の実デッキ 2 本の書き出しと全図形が一致することを確認。変換器は lab と同じ版を vendor（MIT）。上流 v6.8.0 への更新は別の作業として見送り（baseline-shift を変換器が扱う模様）
- Web ドキュメント（Astro Starlight、30+ ページ）。CI でビルド検証

## テストユーザー会は 2 回実施済み

| 回 | 日付 | 内容 | 実地で覆った前提 | 対応 |
|---|---|---|---|---|
| 第 1 回 | 2026-06-19 | オンボーディング体験 | ① Gemini CLI 無料枠では**初期構築すら完了できない**（「無料枠が大きい」は誤り）② **git がインストール前提**（全 CLI が clone 型配布） | セミナー HTML・README を修正済 |
| 第 2 回 | 〜2026-07-08 | Windows・スライド作成ハンズオン | **初期構築でトークンを使い過ぎる**（web 種まきの並列自動起動で 10〜30 万トークン級） | v1.73.0（種まきを遅延化）＋ v1.74.0（scaffold を `scaffold.py` 1 実行に）で解消 |

> ⚠️ **第 2 回の記録は CHANGELOG にしかない**（`secretary/notes/` に CAW のノートが無い）。
> トークン問題以外のフィードバックがあったかは**未確認**。

## いま開いている問い（＝次の意思決定）

1. ⚠️ **価格** — **暫定確定**（標準 15 万円/件・謝金ルートなら 7 万円/件・1 件目はパイロット）。**事務局に 3 件確認するまで暫定**：①学生が他研究室の研究費から役務/謝金を受けられるか ②業務委託か謝金か ③SPRING の販売実績判定と期限。確認メールは**保留中**
2. **販売チャネル** — 伴走の申込導線をどこに置くか（自前 LP / note / 大学経由 / 紹介）
3. ~~**商品名**~~ — ✅ **2026-08-21 確定**：「研究者のための AI エージェント導入伴走」
4. **Web サイトのデプロイ先** — `web/astro.config.mjs` に `site` 未設定、デプロイ workflow も無し ＝ **どこにも公開されていない**
5. ~~**Copilot / Gemini トラックの去就**~~ — ✅ **2026-08-21 決定・実装済**：Copilot は **15 スキルへフルポート完了**（就活 3 本も含めた。オンボーディングが就活トラックを提示するため、除くと部署だけ作られてスキルが欠ける状態になる）、Gemini は**凍結**
6. **第 3 回テスト会をやるか** — やるなら題材・対象 OS・目的

## 追跡タスク一覧（2026-08-24 時点）

| # | タスク | 状態 | メモ |
|---|---|---|---|
| T1 | **Copilot CLI の実機動作確認** | 🔲 未着手（後回し・2026-08-24 ユーザー判断） | 15 スキルへフルポート済みだが **Copilot CLI を一度も起動していない**。`docs/copilot-compatibility.md` は 2026-06-04 の**机上調査**。テスト会 2 回はどちらも Claude Code。README の見出しが「インストール（**リポジトリ公開・marketplace 設定後**）」＝ install 手順が未実行。**Codex は実機で誤りが判明し 2 ステップに修正された履歴があるが Copilot には無い**ため、現在の `copilot plugin install raw` は同型の誤りの可能性。ローカルに `copilot` 未導入 |
| T2 | **Codex 版への hooks 移植** | 🔲 未着手 | 下記詳細 |
| T3 | **`raw-slides` の Windows 実機確認** | 🔲 未着手 | v1.78.0 の `build_deck` / `make_preview` / `fig_style` も Windows 実機では未確認（MS ゴシック・Chrome/Edge の場所は OS ごとに探す実装） |
| T8 | **`raw-slides` の動画の PowerPoint 実再生** | 🔲 未着手 | XML と参照までは検定済み。PowerPoint を開いての自動再生・ループは未確認 |
| T4 | **USB 配布の仕組み** | ✅ **2026-08-24 実装・実測済** | `scripts/make-offline-bundle.sh` でバンドル生成（3.1 MB・3 CLI 分・byte 一致検証つき）。受け取る側は `install.sh` / `install.ps1` を実行するだけ。詳細は下記 |
| T5 | チャネル（申込導線）の決定 | 🔲 未決 | Phase 4 |
| T6 | Web サイトの公開 | 🔲 未着手 | `astro.config.mjs` に `site` 未設定・deploy workflow 無し |
| T7 | 事務局への確認メール | ⏸ 保留中（ユーザー判断） | 兼業可否・支払ルート・SPRING の販売実績判定 |

## ★ USB 配布（実装済・2026-08-24）

**想定シナリオ**：ネットは通るが**ファイルのダウンロードが制限される**環境（GitHub がブロック等）。
USB から相手の PC にコピーして、そこから raw 環境を構築する。**完全オフラインは対象外**
（raw は CLI がモデル API を呼ぶのでネット自体は必須）。

### 使い方（配る側）

```bash
bash scripts/make-offline-bundle.sh ~/Desktop/raw-bundle
# → 中身をまるごと USB にコピーして手渡す
```

生成物は **3.1 MB**。3 CLI 分のマニフェストとプラグインが同居するので、
**1 つの USB で相手がどの CLI でも使える**（マニフェストの読まれる場所が CLI ごとに違うため共存できる）。
`gemini-plugin` は凍結中のため同梱しない。

### 使い方（受け取る側）

USB の中身を PC にコピーしてから、`install.sh`（macOS）または `install.ps1`（Windows）を実行。
CLI を自動検出し、コピーと登録とインストールまで行う。

### ★ 設計原則：バンドルは marketplace 配布と byte 一致

加工すると「第 3 の配布面」が生まれてドリフトするため、スクリプトは copy と除外
（`.DS_Store` / `__pycache__`）だけを行い、**最後に `diff -r` で一致を検証**する。

### ⚠️ 実測で見つけた落とし穴：ローカルパスは「その場」を参照し続ける

| 登録元 | marketplace root |
|---|---|
| Git（GitHub） | `~/.codex/.tmp/marketplaces/<name>/`（**クローンされる**） |
| **ローカルパス** | **指定したパスそのまま**（コピーされない） |

⇒ **USB を直接登録すると、USB を抜いた時点で raw が壊れる。**
`install.sh` はこれを避けるため、必ず `~/raw-plugin` にコピーしてから登録する。
既存があれば `raw-plugin.old-<日時>` に退避（削除しない）。

### 実測で確認したコマンド形

| CLI | 手順 | 検証状況 |
|---|---|---|
| **Codex** | `codex plugin marketplace add <path>` → `codex plugin add raw@researcher-ai-workflow` | ✅ **完全実証**（登録し `raw@<name>` が installable と表示されるまで確認） |
| **Claude Code** | `claude plugin marketplace add <path>` → `claude plugin install raw@researcher-ai-workflow` | ✅ 登録まで実証（`Source: Directory` として受理）。インストールは既存登録を増やすため未実行 |
| **Copilot** | 未検証（T1） | ⚠️ |

**git は不要**（clone しないため）。テスト会 1 回目で判明した「git が隠れ前提」はこの経路では消える。

### 前提（バンドルは raw 本体のみ。これらは相手側で用意が必要）

CLI 本体（`codex` / `claude`）・Node.js LTS・Python 3・Python パッケージ
（python-pptx / Pillow / PyMuPDF / matplotlib）。
`install.sh` は CLI が無ければ導入コマンドを案内して終了する。

### ⚠️ 2026-08-24 に見つかった別件

- ユーザーの Codex 環境の raw は **1.73.0**（リポジトリは 1.76.0）＝**本セッションの未コミット変更は未反映**
- **Claude Code に `raw@researcher-ai-workflow` が 4 重登録**されている（1.0.0 ×2・1.39.0 ×2、すべて disabled・scope local）。開発中の残骸と思われる。**未対応**（ユーザー判断待ち）

## （旧）オフライン配布の調査メモ

**GitHub に到達できない環境（企業ネットワーク等）でも raw を配れる。** git も不要。

- `claude plugin marketplace add` … `Add a marketplace from a URL, **path**, or GitHub repo`
- `codex plugin marketplace add` … `Add a **local** or Git marketplace` / `Marketplace source: **a local path**, owner/repo[@ref], HTTPS Git URL, or SSH Git URL`
- **実測（Codex 0.149.0）**：`codex-plugin/` ＋ `.agents/plugins/marketplace.json` だけを置いた **1.1 MB** のディレクトリを
  `codex plugin marketplace add <path>` で登録 → `raw@<name>` が installable として認識されることを確認（登録・確認後に撤去済み）。

### ⚠️ 実測で分かった落とし穴：ローカルパスは「その場」を参照し続ける

| 登録元 | marketplace root |
|---|---|
| Git（GitHub） | `~/.codex/.tmp/marketplaces/<name>/`（**クローンされる**） |
| **ローカルパス** | **指定したパスそのまま**（コピーされない） |

⇒ **USB を直接登録すると、USB を抜いた時点で raw が壊れる。**
**必ず USB からローカルディスクにコピーしてから、そのコピー先を登録すること。**

### 配布物のサイズ

| | サイズ |
|---|---|
| リポジトリ全体 | 221 MB |
| うち `web/`（node_modules・dist） | 189 MB ← **不要** |
| うち `.git` | 20 MB ← **不要** |
| Codex 版のみ（`codex-plugin/` ＋ manifest） | **1.1 MB** |
| 4 系統すべて | 約 4 MB |

### ⚠️ 完全オフラインは不可能

raw は CLI がモデル API を呼ぶので**ネットワークは必須**。USB 配布が解くのは
「**GitHub に到達できない／git が無い**」であって「インターネットが無い」ではない。
前提として別途必要なもの（いずれも通常はネット越し）：
**CLI 本体（`codex`/`claude`）・Node.js LTS・Python 3・Python パッケージ**（python-pptx / Pillow / PyMuPDF / matplotlib）。
オフライン導入まで面倒を見るなら、これらのインストーラも USB に同梱する必要がある。

### 副産物（2026-08-24 に判明）

ユーザーのローカルにインストールされている raw は **codex 1.73.0**
（実体 `~/.codex/.tmp/marketplaces/researcher-ai-workflow/codex-plugin`）。
作業リポジトリは **codex 1.76.0** なので、**本セッションの未コミット変更は実環境に未反映**。

## 追跡タスク T2 詳細：Codex 版への hooks 移植（本命なのに未実装）

2026-08-21 に**本命を Claude Code → Codex CLI に変更**した（理由＝Codex は 2026-07-12 に
**5 時間ウィンドウが撤廃され週次上限のみ**になり、**伴走の 3 時間セッションが途中で上限に当たらない**）。
その結果、**本命トラックに hooks が無い**状態になっている。

Codex CLI は hooks を**公式にサポート**している（`SessionStart` / `PostToolUse` / `Stop` 他、
プラグインが `hooks/hooks.json` で同梱可、`.codex-plugin/plugin.json` の `"hooks"` で明示も可、
**Windows 対応**、**既定で有効**、`PLUGIN_ROOT` と互換の `CLAUDE_PLUGIN_ROOT` の両方が使える）。

**ただし単純コピーではない。3 つの適応が要る：**

| # | 差分 | 対応 | 重さ |
|---|---|---|---|
| a | `CLAUDE_PROJECT_DIR` が存在しない | **stdin JSON の `cwd`** から取る（全 3 スクリプト） | 軽 |
| b | 出力形式が違う | 素のテキストではなく `{"hookSpecificOutput":{"hookEventName":"...","additionalContext":"..."}}` で包む | 軽 |
| c | **PostToolUse の対象ツールが違う** | Claude は `Edit\|Write\|MultiEdit` ＋ `tool_input.file_path`。**Codex は `apply_patch` で入力が patch 文字列＝`file_path` が無い**ため、patch を解析して書き込み先を取り出す別実装が要る | **重** |

**推奨する分割**：`SessionStart`（文脈注入）と `Stop`（learnings 記録の督促）は a+b だけで移植でき、
価値も大きいので先に入れる。`PostToolUse`（成果物配置の二層原則チェック）は c があるので別途。

⚠️ **移植したら必ず実機で発火を確認すること。** フィールド名を間違えると
**hooks は無言で何もしない**（落ちない）ので、書けたことは動くことの証拠にならない。

## 再開時にまず確認すべきファイル

| ファイル | 役割 | 鮮度 |
|---|---|---|
| `CHANGELOG.md` | **実際に何が起きたかの唯一の完全な記録**。ここが正典 | ✅ 最新 |
| `docs/concept.md` | 設計方針・差別化・スコープ・役割境界 | ✅ 2026-07-01 更新済 |
| `docs/chemistry-coverage-audit.md` | 化学 16 領域のカバレッジ監査と役割境界 | ✅ |
| `docs/analysis-companion-design.md` | 抽象フレームワーク方針（手法別スキルを量産しない根拠） | ✅ |
| `docs/roadmap.md` | マイルストーン | 2026-08-20 現状化 |
| `TESTING.md` / `TESTING-slides-handson.md` | テスト会の手順書 | 第 1 回 / 第 2 回 |
| `scripts/check-consistency.sh` | 配布物の整合性検査（**変更後は必ず実行**） | ✅ |

## 開発時の規律（既存・継続）

- **配布物を触ったら版を上げる**：plugin / codex / copilot / gemini の 4 系統。`check-consistency.sh` が版一致と mirror byte 一致を強制する
- **plugin ↔ codex はミラー**：`raw-slides/{references,scripts,vendor}`・`raw-analyze/references`・`raw/references/{html-style,playbook-web-seeding}.md` は byte 一致
- **`.py` を書いたら PR ループ**（python-reviewer → codex:review）。記録は lab 本体の `review/code-reviews/` 配下
- **個人化リークを出さない**：`check-consistency.sh` が `neoueda@` と `/Users/neoueda` を検査する
- **ユーザーのプロジェクトに先頭ドットのフォルダを作らない**（`office/` は可視フォルダ・絶対ルール）

## 関連メモリ

- `project_spring_chemist_ai_workflow.md` — プロジェクト長期記録
- `feedback_caw_tool_install_per_tool_with_rationale` — 前提ツールは個別に理由添えで導入
- `feedback_caw_no_assumed_extra_plugin_dependency` — 単体 CLI で完結・追加プラグインを既定にしない
- `feedback_caw_abstract_not_per_technique_skills` — 手法別スキルを量産せず抽象的で柔軟な枠組みに
- `feedback_document_staleness_from_source_mtime_not_stated_date` — **本ファイルが 3 か月 stale 化した原因そのもの**
