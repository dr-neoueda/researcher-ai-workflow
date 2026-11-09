---
title: Commands（スラッシュコマンド）
description: Codex CLI の `commands/<name>.md` フォーマット、Skills との使い分け、化学プロジェクトでの応用
---

Codex CLI には Skills と並ぶ機能拡張機構として **Commands** があります。Skills が「自然言語マッチで自動発火」するのに対し、Commands は **`/<name>` でユーザーが明示的に呼び出す** スラッシュコマンド。本ページでは Commands の構造、書き方、Skills との使い分けを通します。

## Skills vs Commands — Codex の設計思想

Codex は名前空間を明確に分離する設計です。

| 種類 | 発火方法 | 配置 | 用途 |
|---|---|---|---|
| **Skills** | 自然言語マッチ（スラッシュ不要） | `skills/<name>/SKILL.md` | 「やりたいこと」を述べると自動的に選ばれる継続的な能力 |
| **Commands** | `/<name>` 明示 | `commands/<name>.md` | ユーザーが「今、これを実行したい」と意思表示する単発操作 |

Claude Code は両者を `/` 構文に統合していますが、Codex では分離。スキルにスラッシュをつけるのは Codex 文化的には違和感を生じます。

## Commands の場所

```
~/.codex/plugins/cache/<marketplace>/<plugin>/<version>/commands/
├── deploy.md                                 ← /deploy で発火
├── status.md                                 ← /status で発火
└── env.md                                    ← /env で発火
```

ファイル名がそのままコマンド名になります。`deploy.md` なら `/deploy`、`status.md` なら `/status`。

## 最小フォーマット

```markdown
---
description: このコマンドが何をするか、UI のヘルプに表示される
---

# /command-name

このコマンドの目的を 1-2 行で。

## Arguments

- `arg1`: 説明（optional / required）
- `arg2`: 説明

## Workflow

1. Step 1: ...
2. Step 2: ...
3. Step 3: ...

## Guardrails

- 注意事項
- やってはいけないこと
```

`description` は YAML frontmatter に。本文は「ユーザーが `/command-name` を実行した時に Codex に渡される指示プロンプト」として機能します。

## 推奨セクション構成

Vercel プラグインなど公式プラグインの慣習に従うと、以下の構成が安定します。

### 1. Preflight（前提チェック）

```markdown
## Preflight

1. **Project linked?** — `.<config>/project.json` が存在するか確認
2. **CLI available?** — 必要な CLI が PATH にあるか
3. **Repo state** — 未 commit の変更がないか
4. **Scope** — monorepo の場合、対象 package を確認
```

Preflight 失敗時は明確なエラーで止める。silently スキップしない。

### 2. Plan（実行計画）

```markdown
## Plan

実行前に何が起きるかを述べる：

1. **Discover** — ...
2. **Select** — ユーザーが選択
3. **Apply** — ...
4. **Verify** — 結果確認
```

ユーザーが OK と返事してから実行に入る。

### 3. Workflow（実行手順）

具体的なステップ。各ステップで使うコマンドや tool を明示。

### 4. Guardrails（防護）

```markdown
## Guardrails

- 既存ファイルを上書きしない
- destructive な操作（rm -rf, force push 等）は事前確認必須
- secret を含むファイルを log に出さない
```

## Skills を呼び出す Command

「Skills を明示的に発火させたい」ケースのために、Command が Skills を参照することもできます：

```markdown
# /raw-init

研究プロジェクトのための AI 部署システムを初期化する。

## 実行手順

1. **必ず最初に** `${CODEX_PLUGIN_ROOT}/skills/raw/SKILL.md` を Read tool で読み込む
2. SKILL.md の指示に従ってオンボーディング → スキャフォールドを実行する
3. ユーザーが日本語で話しかけたら日本語で応答
```

ただし raw の場合、ユーザーが「raw」と入力するか「研究プロジェクトの環境を作って」と自然言語で言えば Skills が自動発火するので、専用 Command は通常不要。Command を作るのは：

- 副作用が強く、ユーザーの明示的意思表示が必要な操作
- パラメータを毎回受け取る場合
- 同じスキルでも違うモード（例: 強制再 scaffold）を起動したい場合

## 化学プロジェクトでの応用例

研究室で使いそうな Commands の例：

### `/lab-status`

```markdown
---
description: 現在の研究プロジェクト状況を一画面に集約表示
---

# /lab-status

## Workflow

1. `secretary/todos/<today>.md` の未完了を表示
2. `secretary/notes/<today>-decisions.md` の昨日からの差分
3. `computation/jobs/` の最新 5 件
4. `work/papers/` の新規 PDF 数
5. KB（Notion / Obsidian）の最近編集（API 経由）

セッション開始時に手早く状況を把握したい時に。
```

### `/sync-notion`

```markdown
---
description: ローカル secretary/todos と Notion ToDo DB を双方向同期
---

# /sync-notion

## Preflight

1. Notion MCP サーバが接続済か確認
2. Notion DB ID が ~/.codex 設定にあるか確認

## Workflow

1. ローカル TODO 一覧取得
2. Notion DB 一覧取得（未着手 / 進行中 / 戻り待ち）
3. Status drift を検出
4. ユーザーに差分を提示
5. 同期方針を確定（local 優先 / Notion 優先 / 両方手動マージ）
6. 適用
```

### `/job-submit`

```markdown
---
description: 計算ジョブを HPC に投入し、ジョブ記録を office/computation/jobs/ に作成
---

# /job-submit

## Arguments

- `tool`: gaussian / orca / cp2k / gromacs / vasp / qe（required）
- `system`: 系の通称（required）
- `purpose`: opt / freq / ts / sp / md 等（required）

## Workflow

1. <tool>/<system>_<purpose>_<YYYYMMDD>/ ディレクトリ確認
2. ジョブスクリプト存在確認
3. HPC へ qsub / sbatch
4. job ID 取得
5. `office/computation/jobs/<YYYY-MM-DD>-<system>-<purpose>.md` にジョブ ID + 投入時刻を記録
```

## Command の作り方

### 手動

```bash
mkdir -p ~/my-plugin/commands
cat > ~/my-plugin/commands/hello.md <<'EOF'
---
description: 挨拶する
---

# /hello

ユーザーに挨拶を返す。

## Workflow

1. ユーザーの名前を `~/.codex/config.toml` または環境変数から取得
2. 「こんにちは、<name>さん」と返答
EOF
```

これでプラグインを enabled にすれば `/hello` が利用可能。

### `plugin-creator` を使う

raw が使ったのと同じ scaffold スクリプトで commands ディレクトリも含めて生成可能。詳細は `~/.codex/skills/.system/plugin-creator/SKILL.md` を参照。

## ユーザー視点での発見性

Codex で利用可能な Commands は `/` を入力すると候補一覧が表示される（Claude Code と同じ UX）。プラグインインストール時、ユーザーが「/」を打って raw の Commands が見えるかどうかが発見性の鍵。description を分かりやすく書くと UI 上で意図が伝わります。

## raw プラグインに Commands を追加するべきか？

現状の raw（Codex 版）は Skills のみで Commands は無い設計。これは Codex 流の「やりたいことを述べれば発火」UX を尊重した結果。

将来 Commands を追加する場合の候補：

- `/raw-reset` — 既存 `office/` を破棄して再 scaffold（destructive 操作なので明示的 command が妥当）
- `/raw-export` — `office/` 全体を tar.gz でエクスポート（バックアップ用途）
- `/raw-import <path>` — エクスポートを別プロジェクトに展開

destructive または 副作用が強い操作は Command として明示し、ユーザーの確認を 1 ステップ挟む設計が安全。

## 次のステップ

- [Skills](/codex-cli/skills/) — 継続的な能力を Skills として作る
- [MCP サーバー連携](/codex-cli/mcp/) — 外部サービス統合
- [配布プラグイン（raw）](/plugin/) — raw の現状の設計（Skills only）と理由
