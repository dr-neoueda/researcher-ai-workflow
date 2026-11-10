---
name: raw-setup
description: >
  raw を十分に使うための外部ツール（Python・poppler・PyMuPDF・python-pptx・Pillow・解析ライブラリ 等）の不足を、使う機能に応じて検出し、
  各ツールを 1 つずつ「なぜ必要か」を添えて導入するか尋ねる（一括の暗黙導入も勝手なスキップもしない）。OS（macOS / Windows）を判定し、
  既に入っているものは尋ねない。CLI/Node 自体の導入は配布リポジトリの bootstrap スクリプトへ誘導。
---

# raw-setup — 前提ツールの検出と順次インストール

## いつ使うか

- ユーザーが「環境を整えて」「必要なツールを入れて」「セットアップして」と言ったとき
- raw オンボーディング直後に、スライド・図・PDF 機能を使う予定なのに依存が無いとき
- スクリプト実行が `ModuleNotFoundError` や `command not found`（pdftoppm 等）で失敗したとき

このスキルは **CLI（Codex CLI / Claude Code）が既に動いている前提**なので、CLI 本体・Node.js の
導入は対象外（それらは鶏卵問題のため、配布リポジトリの `setup/raw-setup.sh` / `setup/raw-setup.ps1`
を案内する）。本スキルは **Python・poppler・Python パッケージ・任意ツール**の補完を担う。

## 安全方針（厳守）

- **全ツールを個別に、なぜ必要かを説明して尋ねる**。各ツールに「どの raw 機能のために要るか」を 1 行添え、**導入するかをユーザーが 1 つずつ選べる**ようにする（一括の暗黙導入も勝手なスキップもしない）
- **冪等**：既に入っているものは尋ねず ✓ 表示のみ（導入しない）
- **sudo / 管理者権限は使わない**。Homebrew（user 権限）/ winget / Scoop / pip --user の範囲で行う
- 選ばれたツールだけを順に導入し、各ステップの**成否を記録**、失敗しても止めず最後にまとめて報告

## ワークフロー

### Step 1: OS 判定

`uname -s` を実行。`Darwin` なら macOS、それ以外で Windows（`OS` 環境変数 = `Windows_NT`）なら Windows。
対応 OS は **macOS と Windows** のみ。判定できない場合はユーザーに確認する。

### Step 2: 現状チェック（冪等の素）

以下を `command -v`（macOS）/ `Get-Command`（Windows）で確認し、導入済み / 不足を表にまとめる：

| 機能 | ツール | チェック | なぜ必要か（ユーザーに必ず説明する） |
|---|---|---|---|
| コア | Python 3 | `python3` / `python` | raw の全 Python 処理（スライド変換・解析・PDF）の土台 |
| PDF | poppler | `pdftoppm` / `pdftotext` | 論文 PDF のテキスト抽出・画像化（文献登録・レポート・取り込み） |
| スライド | PyMuPDF | `python3 -c "import fitz"` | 論文の図を高解像度で切り抜いてスライドに載せる |
| スライド | python-pptx | `python3 -c "import pptx"` | 手描き SVG を**編集可能な pptx** に変換する（raw-slides の要） |
| スライド | Pillow | `python3 -c "import PIL"` | スライドに写真・切り抜き図（ラスタ画像）を埋め込む |
| スライド（任意） | Chrome または Edge | ブラウザの有無 | 完成前にスライドをプレビュー画像で目視 QA する |
| スライド（任意） | ffmpeg | `ffmpeg -version` | スライドに動画を載せる（変換・自動再生ループ） |
| 解析・作図 | numpy / pandas / scipy | `python3 -c "import numpy, pandas, scipy"` | 測定・計算データの読み込み・整形・数値解析 |
| 解析・作図 | matplotlib | `python3 -c "import matplotlib"` | 解析結果のグラフ作成・スライドの図と数式 |
| 解析（任意） | lmfit | `python3 -c "import lmfit"` | 速度論・スペクトル等の非線形フィッティング |
| 解析（任意） | RDKit | `python3 -c "import rdkit"` | 分子構造の生成・記述子・描画 |
| 解析（任意） | ASE | `python3 -c "import ase"` | 原子構造の読み書き・計算入力の準備 |
| 検索・VC（任意） | GitHub CLI (gh) | `gh` | GitHub の検索・PR |

> 各ツールは上の「なぜ必要か」を添えて**個別に導入可否を尋ねる**（既に入っているものは尋ねない）。計算エンジン本体（Gaussian/ORCA/CP2K/GROMACS/MACE 等）は raw-setup の対象外（ユーザーが HPC/ローカルに導入するもの）。

CLI 本体（`codex` / `claude`）・`node` も確認し、**無ければ** bootstrap スクリプトを案内（Step 5）。

### Step 3: 各ツールを個別に説明して尋ねる

Step 2 で**不足していた**ツールを、**1 つずつ**「なぜ必要か（上表の説明）」を添えて、導入するか尋ねる。

- **尋ね方**：Claude Code は `AskUserQuestion`（機能グループごとに複数選択・各ツールの説明欄に「なぜ必要か」を書く）、他 CLI は不足ツールを説明つきで列挙し、どれを入れるか選ばせる。**全ツールについて説明つきで意思決定を取る**（勝手に入れない・勝手に飛ばさない）。既に入っているものは尋ねない（✓ 表示のみ）。
- **オンボーディングで実行**：`/raw` オンボーディングの scaffold 完了後にこの Step を必ず走らせ、その場で不足ツールを説明つきで尋ねる（「あとで /raw-setup」の後回しではなく初期構築の一部）。
- **導入コマンド（選ばれたツールのみ）**：
  - pip：スライド＝`python-pptx Pillow PyMuPDF matplotlib`／解析＝`numpy pandas scipy matplotlib`／任意＝`lmfit rdkit ase`
  - macOS: poppler は `brew install poppler`／pip は `python3 -m pip install <pkgs>`（PEP 668 で弾かれたら `--user --break-system-packages`）
  - Windows: `winget install -e --id <id>`／poppler は `scoop install poppler`／`python -m pip install <pkgs>`
  - Homebrew / winget / Scoop が無ければ、その導入も選択肢として説明する。

### Step 4: 選ばれたツールを順に導入

Step 3 で選ばれたツールを上から順に実行。各ステップで「installing … → OK / FAIL」を表示。失敗は記録して次へ進む（選ばれなかったツールは入れない）。

### Step 5: CLI / Node が無い場合（bootstrap 誘導）

`codex`/`claude` や `node` が無い環境では、本スキルだけでは完結できない。配布リポジトリの
ワンステップ・スクリプトを案内する：

- macOS: `bash setup/raw-setup.sh`
- Windows: `powershell -ExecutionPolicy Bypass -File setup/raw-setup.ps1`

これらは CLI・Node・git も含めて順番に導入する（前提が無い初回のみ・以降は本スキルの per-tool 方式）。

### Step 6: 動作確認と報告

```
node -v / git --version / python(3) --version / pdftoppm -v / codex --version
python -c "import pptx, PIL; print('slides deps OK')"                 # スライドを入れたら
python -c "import fitz; print('PyMuPDF OK')"                          # 論文図を入れたら
python -c "import numpy, pandas, scipy, matplotlib; print('analysis deps OK')"
```

導入済み / 今回入れた / 失敗 / 任意で見送り、を表で報告。最後に「`work/gaussian/_past-data/` 等に
過去データを入れて『取り込んで』と言うと Playbook を最適化できます」と次の一歩を添える。

**hook の承認（Codex）**：raw の自動の仕組み（起動時の読み込み・置き場所の見張り・学びの催促）は、Codex では
ユーザーが `/hooks` で信頼（trust）するまで動かない。報告の最後に「まだなら `/hooks` で raw の 3 つを信頼にしてください。
プラグインを更新したときも確認が出ます」と添える。hook は Python を使うので、Python が無いと置き場所の見張りは働かない。

## 重要な注意事項

- **対応 OS は macOS と Windows**。Windows の raw Hooks は bash なので Git Bash / WSL2 が要る点も伝える
- インストールコマンドは固定の信頼できるものだけを使い、ユーザー入力をそのままシェルに渡さない
- 失敗時はログ（bootstrap は一時ファイルに出力）と再実行方法を案内する
- 詳細な OS 別手順は LP「必要なツールとインストール」に対応
