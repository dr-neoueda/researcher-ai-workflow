# raw — Researcher's AI Workflow Plugin (Codex CLI 版)

理工系の研究プロジェクトのための AI 部署システムを 1 コマンドで構築する Codex CLI プラグイン（旧名 caw / Chemist's AI Workflow）。秘書部から開始し、必要な部署を必要なときに増やす。計算ソフトの Playbook と作業ディレクトリも対話的に整備。

Claude Code 版（`../plugin/`）と内容は基本同一。`office/<dept>/CLAUDE.md` の代わりに `office/<dept>/AGENTS.md` を生成する点のみ異なる。

## インストール

```bash
codex plugin marketplace add dr-neoueda/researcher-ai-workflow
codex plugin install raw
```

> **前提**：事前に **git** と **Node.js（LTS）** が必要です（`codex plugin marketplace add` は配布元 GitHub を clone するため git が要ります。macOS は `xcode-select --install`、Windows は「Git for Windows」）。

`codex plugin list` で `raw` が `enabled` 表示されれば導入完了。

## クイックスタート

```bash
cd ~/your-research-project
codex
> raw
```

`office/` が存在しない場合、対話的オンボーディングが起動：

1. **研究プロファイル**（4 問）：研究分野、計算ソフト、ナレッジベース、クラウドストレージ
2. **部署選択**：立ち上げる部署を 7 つから複数選択（秘書部は常設）

選択内容に応じて、`office/` 部署（AGENTS.md 構成）と作業ディレクトリ（`work/gaussian/`、`work/papers/` 等）が一括生成される。

## 生成される構造の例

研究分野：物理化学、計算ソフト：ORCA + GROMACS、KB：Obsidian、ストレージ：Google Drive の場合（全 9 部署を作成。下記は抜粋）：

```
your-research-project/
├── office/                       ← 運営側（全 9 部署。各 AGENTS.md＋運営情報のみ）
│   ├── AGENTS.md
│   ├── secretary/{AGENTS.md, inbox/, todos/, notes/}
│   └── computation/{AGENTS.md, jobs/, parameters/, playbooks/{orca.md, gromacs.md}}
├── inbox/                        ← 統合 inbox（何でも入れて「処理して」）
└── work/                         ← 成果物・作業ファイルはすべてこの中
    ├── orca/    {README.md, inbox/, _past-data/}   ← 入出力ファイル置き場
    ├── gromacs/ {README.md, inbox/, _past-data/}
    ├── papers/  {pdf/, md/}                         ← `pdf/`＝原本 PDF・`md/`＝書誌付き要約
    └── analyses/ figures/ manuscripts/ presentations/slides/ …
```

## 含まれる内容

### スキル（15）

**研究トラック（12）**

| スキル | 役割 |
|---|---|
| `raw` | オンボーディング → 自動スキャフォールド → 運営モードの一連（起動は `raw` と入力、または自然言語で指示） |
| `raw-research` | 関心テーマの論文検索（arXiv / Crossref / Semantic Scholar / OpenAlex / PubMed）→ クリック可能な HTML リスト |
| `raw-register` | 入手済み PDF → 書誌付き要約 md → ナレッジベース + クラウドストレージへ登録 |
| `raw-write` | 登録済み文献を引用源に、論文・申請書・学会要旨を本人の文体で執筆 |
| `raw-input` | 7 ソフト（Gaussian / ORCA / CP2K / GROMACS / VASP / Quantum ESPRESSO / ChimeraX）の入力雛形 + ジョブ記録 |
| `raw-playbook` | 計算 log の解析 → Lessons Learned 起案 → Playbook 追記。`_past-data/` の過去データ一括取り込みで初期 seed |
| `raw-analyze` | 手法非依存の解析コンパニオン。汎用ツールでその場の解析を組み、再利用に値する手順を playbook に蒸留 |
| `raw-slides` | 発表資料を SVG-first（手描き SVG → native DrawingML pptx）で生成。図形・表・数式が PowerPoint で編集可能 |
| `raw-setup` | 外部ツール（Python・poppler・python-pptx 等）の不足を検出し、**1 つずつ「なぜ必要か」を説明しながら**導入。CLI/Node 自体は `setup/raw-setup.sh`・`setup/raw-setup.ps1` を案内 |
| `raw-doctor` | `office/` 構造の健全性チェックと修復提示 |
| `raw-intake` | 統合 `inbox/` の自動仕分け。処理後の原本は種類別 `work/*/_source/` へ移動 |
| `raw-report` | 開発者向けの匿名動作レポート |

**就活トラック（3）**：`raw-es`（エントリーシート）・`raw-interview`（面接対策）・`raw-events`（1 社深掘り＋募集/締切予測）

### テンプレート・生成物

- **9 部署 AGENTS.md テンプレート**：secretary / research / engineering / computation / experiment / analysis / writing / review / presentation
- **Playbook 雛形**：Gaussian / GROMACS / CP2K / ORCA / VASP / Quantum ESPRESSO / Psi4 / NAMD / LAMMPS / OpenMM / ChimeraX + 汎用
- **作業ディレクトリ自動生成**：選択した計算ソフトと部署に応じて配置。投入用 `inbox/` と過去データ用 `_past-data/` も生成

## 自動の仕組み（hook）

Claude Code 版と同じ 3 つの hook を同梱している（`hooks/`、Claude Code 版と同じファイル）。

| いつ | 何をするか |
|---|---|
| 起動したとき | 直近の決定・学び、Playbook の一覧、今日の TODO を読み込む |
| ファイルを書いたとき | 成果物を `office/` の中に書いたら、`work/` へ移すよう伝える |
| 終わる前 | 今日の活動があるのに学びのノートが無ければ、書くよう引き戻す（1 回だけ） |

**Codex では最初に承認が要る。** インストールしたら Codex で `/hooks` と入力し、raw の 3 つを「信頼（trust）」にする。
プラグインを更新して中身が変わったときも、もう一度確認が出る。承認するまで hook は動かない（エラーにもならない）。
置き場所の見張りは Python を使う（`raw-setup` が入れる）。

## Claude Code 版との関係

| 観点 | Claude Code 版 (`plugin/`) | Codex 版 (`codex-plugin/`) |
|---|---|---|
| プラグインマニフェスト | `.claude-plugin/plugin.json` | `.codex-plugin/plugin.json` |
| マーケットプレイス manifest | `<repo>/.claude-plugin/marketplace.json` | `<repo>/.agents/plugins/marketplace.json` |
| 生成される指示ファイル | `<dept>/CLAUDE.md` | `<dept>/AGENTS.md` |
| インストール | `/plugin install raw@researcher-ai-workflow` | `codex plugin install raw` |
| スキル本体（プロンプト指示） | 同一 | 同一 |
| hook（3 つ） | 同一。入れると動く | 同一。`/hooks` で承認してから動く |
| Playbook 雛形 | 同一 | 同一 |

両プラグインは同じリポジトリ（`dr-neoueda/researcher-ai-workflow`）から並列配信。研究室で Claude Code 派と Codex CLI 派が混在しても、同じ `office/` メソッドを共有できる。

## ライセンス

MIT License. 詳細は repo 直下の [LICENSE](../LICENSE) を参照。

## 関連リンク

- 配布元 LP: [Researcher's AI Workflow](https://github.com/dr-neoueda/researcher-ai-workflow)
- Claude Code 版: [`../plugin/`](../plugin/)
- 開発元: 電気通信大学 SPRING（戦略的研究人材育成事業）
