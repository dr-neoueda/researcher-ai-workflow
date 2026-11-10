# Researcher's AI Workflow（raw）

> **研究者のための AI エージェント導入伴走** — 電気通信大学 SPRING リカレント・リスキリング商品

**配布版：plugin 2.1.0 / Codex 2.1.0 / Copilot 1.46.0（保留中・旧名 caw）/ Gemini 1.49.0（凍結）**
現状と次の一手は [`RESUME.md`](./RESUME.md)、変更の全履歴は [`CHANGELOG.md`](./CHANGELOG.md) を参照。

> **プラグイン `raw` は無料です。** 商品はプラグインそのものではなく、研究者が自分の研究に合わせて
> 立ち上げ、使い続けられる状態まで持っていく **マンツーマンの導入伴走** です。
> 詳細は [`docs/concept.md`](./docs/concept.md)。

## これは何か

研究プロジェクト（化学・材料／物理・地球惑星／生命科学／工学・情報）のルートで `/raw` と打つと、**9 つの「AI 部署」からなる運営フォルダ（`office/`）と作業フォルダ（`work/`）を対話的に構築**し、以後その構造の上で研究支援を回す **CLI プラグイン**です。

- **秘書部** が TODO・意思決定・学びを 1 日 1 ファイルで蓄積する
- **計算管理部** が Gaussian / CP2K / GROMACS / COMSOL / MATLAB 等の入力生成・ジョブ記録・log 解析を担い、罠と処方を **Playbook** に貯めていく
- 分野ごと（化学・材料／物理・地球惑星／生命科学／工学・情報）に、単位・命名・誤差・収束の**規律**を最初から持たせる
- **文献部** が論文を検索・登録し、**論文執筆部** がそれを引用源に本人の文体で書く
- **プレゼン部** がSVG から**編集可能な PowerPoint** を生成する

単発のチャットではなく、**ファイルシステム上に状態を持つ組織**として AI を運用するのが中核アイデアです。

## インストール

```bash
# Claude Code
> /plugin marketplace add dr-neoueda/researcher-ai-workflow
> /plugin install raw

# 使う
cd ~/your-research-project && claude
> /raw
```

**前提**：`git` と Node.js（LTS）。`marketplace add` は配布元 GitHub を clone するため git が必須です
（macOS は `xcode-select --install`、Windows は Git for Windows）。

対応 OS は **macOS / Windows** を同列にサポート（Hooks のみ Windows では Git Bash / WSL2 を併用）。

### 旧名 caw（Chemist's AI Workflow）から移る

v2.0.0 で商品名を **Researcher's AI Workflow** に、コマンドを `caw` → **`raw`** に、配布元を
`dr-neoueda/chemist-ai-workflow` → **`dr-neoueda/researcher-ai-workflow`** に変えました。
旧名のまま入れたプラグインは自動では更新されないので、一度外して入れ直してください。

```bash
# Claude Code
> /plugin uninstall caw@chemist-ai-workflow
> /plugin marketplace remove chemist-ai-workflow
> /plugin marketplace add dr-neoueda/researcher-ai-workflow
> /plugin install raw@researcher-ai-workflow

# Codex CLI
codex plugin remove caw@chemist-ai-workflow
codex plugin marketplace remove chemist-ai-workflow
codex plugin marketplace add dr-neoueda/researcher-ai-workflow
codex plugin add raw@researcher-ai-workflow
```

作ってあった `office/` と `work/` はそのまま使えます。プロジェクトで `/raw-doctor`（Codex では「健康診断して」）を
実行すると、規則ファイルに残った旧名 `caw` を見つけて置き換えを提案します（メモ・TODO などの記録は書き換えません）。

## 対応 CLI

| CLI | 位置づけ | 状態 |
|---|---|---|
| **Codex CLI** | **Tier 1（本命）** | 15 スキル。Hooks は移植予定 |
| **Claude Code** | Tier 2 | 15 スキル ＋ Hooks 3 本（Codex 版と byte 一致ミラー） |
| **Gemini CLI** | 参考 | 15 コマンド。**実地検証で「無料枠では初期構築すら完了不可」と判明**（有料 API 前提） |
| **Copilot CLI** | 保留中 | v1.78 の内容（化学者向け・旧名 `caw`）のまま。再開の手順は `copilot-plugin/PAUSED.md` |

ベンダーロックインを避ける設計だが、**実用度には明確な差がある**ことを正直に記載しています。

## スキル一覧（15）

### 研究トラック（12）

| スキル | 役割 |
|---|---|
| `/raw` | オンボーディング（研究プロファイル聴取 → 9 部署 + `work/` を一括生成）→ 以後は運営モード |
| `/raw-research` | 関心テーマの論文検索（arXiv / Crossref / Semantic Scholar / OpenAlex / PubMed）→ クリック可能な HTML リスト |
| `/raw-register` | 入手済み PDF → 書誌付き要約 md → ナレッジベース（Notion / Obsidian 等）+ クラウドストレージへ登録 |
| `/raw-write` | 登録済み文献を引用源に、論文・申請書・学会要旨を**本人の文体**で執筆。本文の数は事実の一覧と機械で照合 |
| `/raw-input` | 7 ソフト（Gaussian / ORCA / CP2K / GROMACS / VASP / Quantum ESPRESSO / ChimeraX）の入力雛形 + ジョブ記録 |
| `/raw-playbook` | 計算 log の解析 → Lessons Learned 起案 → Playbook 追記。過去データの一括取り込みにも対応 |
| `/raw-analyze` | 手法非依存の解析コンパニオン（生データ → 数値化後の下流定量解析） |
| `/raw-slides` | 発表資料を **SVG-first**（SVG → native DrawingML pptx）で生成。図形・表・数式が PowerPoint で編集可能 |
| `/raw-setup` | 不足している外部ツールを検出し、**1 つずつ理由を説明しながら**導入 |
| `/raw-doctor` | `office/` 構造の健全性チェックと修復提示 |
| `/raw-intake` | 統合 inbox に投げ込まれたものを自動仕分け |
| `/raw-report` | 開発者向けの匿名動作レポート |

### 就活トラック（3）

`/raw-es`（エントリーシート）・`/raw-interview`（面接対策）・`/raw-events`（企業イベント調査）

## リポジトリ構成

```
researcher-ai-workflow/
├── RESUME.md              ← 現状と次の一手（再開時に最初に読む）
├── CHANGELOG.md           ← 変更の全履歴（実質の正典）
├── TESTING.md             ← 第 1 回テスト会の手順書
├── TESTING-slides-handson.md ← 第 2 回（スライド・Windows）の手順書
├── .claude-plugin/        ← marketplace.json（配布エントリ）
├── plugin/                ← Claude Code 版（skills/ 15 + hooks/ 3）
├── codex-plugin/          ← Codex CLI 版（skills/ 15）
├── copilot-plugin/        ← Copilot CLI 版（PoC・skills/ 2）
├── gemini-plugin/         ← Gemini CLI 版（commands/ 15 の .toml + GEMINI.md）
├── docs/                  ← 企画ドキュメント（concept / roadmap / 監査）
├── scripts/               ← check-consistency.sh（配布物の整合性検査）
├── setup/                 ← CLI 自体の導入スクリプト（.sh / .ps1）
├── presentations/         ← raw-slides のテンプレ pptx
└── web/                   ← Astro Starlight ドキュメントサイト（未デプロイ）
```

## 開発

```bash
bash scripts/check-consistency.sh                      # 版一致・mirror byte 一致・個人化リーク検査
uv run --with pytest --with pillow python -m pytest \
  plugin/skills/raw-slides/tests plugin/skills/raw/tests -q   # 125 passed / 4 skipped
```

配布物（`plugin/` `codex-plugin/` `copilot-plugin/` `gemini-plugin/`）を変更したら**該当系統の版を上げ**、
`check-consistency.sh` を通すこと。CI（`.github/workflows/consistency.yml`）が push / PR で同じ検査と Web ビルドを強制します。

## プロジェクト背景

電気通信大学 SPRING（戦略的研究人材育成事業）に採択された博士課程院生は、リカレント・リスキリングに資するツールを各自開発・販売する義務があります。本プロジェクトはその成果物です。

- **対象**：理工系の研究者（D 生・PD・若手 PI）。化学・材料／物理・地球惑星／生命科学／工学・情報。**化学が作者の実運用に由来する旗艦分野**
- **差別化**：研究の実務に合わせた事例（化学の実運用が出発点）と分野ごとの規律 ／ 作者自身が日常運用している 9 部署システムの実物由来 ／ ベンダーロックイン回避 ／ 品質ゲート内蔵
- **役割境界**：組織運営・下流定量解析・執筆/文献/Playbook を担う。**ベンダー GUI 専用ソフトでの対話的な生データの還元（SCXRD 精密化・XPS 定量・EPR シミュ等）は代替せず外部連携に委ねる**（化学 16 領域の監査は [`docs/chemistry-coverage-audit.md`](./docs/chemistry-coverage-audit.md)。化学以外の分野の監査はまだ行っていない）

詳細は [`docs/concept.md`](./docs/concept.md)、進行状況は [`docs/roadmap.md`](./docs/roadmap.md)。

## ステータス

- **作成日**：2026-04-29
- **現フェーズ**：プラグイン実装は稼働中（テストユーザー会 2 回実施済）。商品モデルは 2026-08-21 に確定。**2026-11-06 に対象を理工系へ広げ、商品名を「研究者のための AI エージェント導入伴走」（Researcher's AI Workflow・`raw`）に変更**。価格・販売チャネル・Web 公開は未着手
- **オーナー**：上田（電気通信大学 SPRING）

## ライセンス

MIT License（[LICENSE](./LICENSE)）
