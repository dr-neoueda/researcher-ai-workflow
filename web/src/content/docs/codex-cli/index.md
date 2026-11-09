---
title: "Codex CLI"
description: OpenAI 製のターミナル CLI エージェント。AGENTS.md ベース、Skills / Commands / Sub-agents / MCP に対応。Claude Code と並ぶ主軸 CLI として、raw プラグインを並列配信
---

OpenAI 公式のターミナル CLI エージェント。**AGENTS.md** を標準としてプロジェクトルールを記述する。本書では **Claude Code と並ぶ主軸 CLI** として扱う。Claude Code 派と Codex CLI 派が混在する研究室でも、同じ raw メソッドを共有できる。

## raw プラグイン（Codex 版）導入

```bash
# 1. marketplace を登録
codex plugin marketplace add dr-neoueda/researcher-ai-workflow
# 2. raw プラグイン本体を追加
codex plugin add raw@researcher-ai-workflow
```

Codex CLI は **marketplace を登録 → そこからプラグインを追加**の 2 ステップです。`~/.codex/config.toml` に `[plugins."raw@researcher-ai-workflow"]` が追加されていれば導入完了。

## クイックスタート

```bash
cd ~/your-research-project
codex
> raw
```

Codex CLI ではスラッシュ不要。`raw` と入力するか、「研究プロジェクトの環境を作って」など自然言語で指示すれば、スキルが自動的に発火します。

`office/` が存在しない場合、対話的オンボーディング（研究プロファイルのヒアリング）が起動し、研究分野に合わせた全部署と作業ディレクトリが一括生成される。生成される指示ファイルは Codex CLI の標準である **AGENTS.md** 形式。

詳細手順は [環境構築](/codex-cli/setup/) を参照。

## Codex CLI の特徴

- **Skills + Commands の二層構造**：Skills は自然言語マッチで自動発火（スラッシュ不要）、Commands は `/<name>` で明示的に発火。Claude Code がこの 2 つを `/` 構文に統合しているのに対し、Codex は名前空間を明確に分離
- **Sub-agents による並列実行**：Codex も sub-agent を起動でき、複数エージェントを並列化して調査・コード生成を分担可能（著者検証済）
- **MCP（Model Context Protocol）に対応**：Claude Code と同じ MCP サーバー（Notion / Google Drive / GitHub 等）を共有でき、両 CLI 間の二重管理を抑制
- **AGENTS.md は universal な標準**：Codex CLI / Gemini CLI 等の他 CLI エージェントも参照可能で、将来的にエージェント乗り換えが容易
- **OpenAI 系モデル（GPT-5 系）を活用できる**：研究室のメンバー構成や所属機関の契約に応じて選択肢を持てる
- **異なるレビュー観点が得られる**：Claude = 構文 / DRY、Codex = 物理意味論という棲み分けの実例あり（応用編で詳述）

## Claude Code との機能比較

| 機能 | Claude Code | Codex CLI |
|---|---|---|
| Skills | あり（`/` でも明示発火可能） | あり（自然言語マッチのみ、スラッシュ不可） |
| Commands（スラッシュ） | Skills と統合 | 別名前空間で分離（`commands/<name>.md`） |
| Sub-agents | あり、種類豊富、Task tool で並列起動 | あり、並列化可能。種類は Claude Code エコシステムより少ない |
| Hooks | SessionStart / PreToolUse / PostToolUse / Stop / PreCompact 等が網羅 | プラグイン内 lifecycle はあるが種類は Claude Code より少ない |
| MCP | あり（Anthropic 公式 + コミュニティ） | あり（同じ MCP サーバーを共有可能） |
| プロジェクトルールファイル | CLAUDE.md（AGENTS.md も読む） | AGENTS.md |
| プラグインマーケットプレイス | あり | あり |

両者とも raw の中核機能（部署スキャフォールド・Playbook 蓄積・MCP 連携）を実装できる。Hooks エコシステムや Claude Code 専用 sub-agents 群（`everything-claude-code` 等）の規模差はあるが、**入門〜中級の研究者運用ではほぼ機能等価**。

## Claude Code 版との関係

| 観点 | Claude Code 版 | Codex 版 |
|---|---|---|
| インストール | `/plugin install raw@researcher-ai-workflow` | `codex plugin marketplace add dr-neoueda/researcher-ai-workflow` → `codex plugin add raw@researcher-ai-workflow` |
| プラグイン構造 | `.claude-plugin/plugin.json` | `.codex-plugin/plugin.json` |
| 生成される指示ファイル | `<dept>/CLAUDE.md` | `<dept>/AGENTS.md` |
| 部署テンプレ内容 | 同一 | 同一 |
| Playbook 雛形 | 同一 | 同一 |
| 配布元 | `dr-neoueda/researcher-ai-workflow`（同一リポジトリ） | 同左 |

両版は同じ `researcher-ai-workflow` リポジトリから並列配信。研究室で Claude Code 派と Codex CLI 派が混在しても、共通の `office/` メソッドで運用できる。

## 章立て

1. [環境構築](/codex-cli/setup/) — Codex CLI インストール + 認証 + raw プラグイン導入 + `office/` 初期化
2. [アンインストールと環境リセット](/codex-cli/uninstall/) — raw の完全除去、最新版への更新、`office/` の作り直し
3. [設定の階層と基礎](/codex-cli/basics/) — `~/.codex/config.toml`、プロジェクト trust、モデル選択、思考レベル
4. [`AGENTS.md` の書き方](/codex-cli/agents-md/) — Codex 流のプロジェクトルール記述、Claude Code の `CLAUDE.md` との対応
5. [Skills](/codex-cli/skills/) — Codex Skills の構造、`SKILL.md` フォーマット、raw を例として
6. [Commands（スラッシュコマンド）](/codex-cli/commands/) — `commands/<name>.md` の作り方、Skills との使い分け
7. [Sub-agents](/codex-cli/subagents/) — Codex の sub-agent 機能、並列調査・並列レビューの組み方
8. [MCP サーバー連携](/codex-cli/mcp/) — Notion / Google Drive / Gmail などへの統合
9. [office/ 部署テンプレート](/claude-code/company-template/)（共通 — Claude Code 章を参照、AGENTS.md に読み替え）
10. [Claude + Codex 二段レビュー連携](/claude-code/two-stage-review/)（応用編、Claude Code 章を参照）

## 著者メモ（応用編）

実例：MD 自由エネルギー計算で Widom 式の `-RT` 項抜けを Codex が検出し、ナレッジベース登録前に補正。構文・DRY は Claude が、物理意味論は Codex が拾うという役割分担が有効。

詳細は [Claude + Codex 二段レビュー（応用編）](/claude-code/two-stage-review/) を参照。AI エージェント運用に慣れてからの導入を推奨します。

## ステータス

**公開済み**（2026-05-13 に旧名 caw の v1.0.0 として公開、2026-11-06 の v2.0.0 で raw へ改名）：マーケットプレイス（`dr-neoueda/researcher-ai-workflow`）経由で導入可能。Claude Code 版（`/raw`）と内容は基本同一で、AGENTS.md ターゲットに対応。
