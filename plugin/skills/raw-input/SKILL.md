---
name: raw-input
description: >
  計算ソフト別の入力ファイル雛形を対話的に生成するスキル。
  Gaussian / ORCA / CP2K / GROMACS / VASP / Quantum ESPRESSO / ChimeraX に対応。
  Playbook のデフォルト推奨値を起点に、ユーザーの系と目的に合わせて入力ファイルとジョブ記録を 1 計算 1 サブディレクトリ単位で配置する。
trigger: /raw-input
---

# raw-input — 計算入力ジェネレータ

## いつ使うか

- `/raw-input` を実行したとき
- ユーザーが「Gaussian で benzene の構造最適化したい」「ORCA の入力ファイル作って」「CP2K の AIMD 雛形くれる？」など、**計算ソフト + 目的**を指定したとき
- 計算ジョブの新規立ち上げ時

`office/computation/` が存在しない場合、`/raw` で computation 部署を追加することを促す。

---

## はじめてモードを尊重する

このスキルを実行する前に `office/CLAUDE.md`（Codex CLI / GitHub Copilot CLI では `AGENTS.md`）を読み、冒頭に `> 運用モード: はじめて` があれば、`raw` skill の「はじめてモードの挙動」を全応答に適用する：**平易な日本語**で話し、専門用語（分野・計算手法・書誌の用語）は初出で 1 行説明を添え、各ステップの最後に**「次はこれをしましょう」を 1 つ**だけ提示する。元に戻せない操作（削除・上書き・外部登録・送信）は必ず事前確認する。

## ワークフロー

### Step 1: 計算ソフトの確定

ユーザー入力から計算ソフトを判定。曖昧な場合は `AskUserQuestion` で 1 問確認：

```
Q1: どの計算ソフトの入力ファイルを生成しますか？
  - Gaussian
  - ORCA
  - CP2K
  - GROMACS
  - VASP
  - Quantum ESPRESSO
  - ChimeraX（構造/密度マップのフィッティング・可視化）
  - その他（Other 自由入力：Psi4 / NWChem / OpenMolcas / xtb・CREST / LAMMPS / AMBER / OpenMM / AutoDock Vina / PHREEQC 等）
```

> **エンジン方言アダプタ方式（新エンジンはスキルを増やさず拡張）**：入力生成を **「幾何（座標）＋メソッド指定（汎関数/基底/計算種）＋エンジン方言アダプタ（各ソフトの入力文法）」** の 3 層に分けて考える。上記リストに無いエンジンを頼まれたら、**per-engine のテンプレート 1 枚**（最小入力の骨格＋そのエンジンの方言メモ）を `office/computation/playbooks/<engine>.md` に足すだけで対応する（新スキルは作らない）。需要の高い次のものは **raw-analyze の「その場実装＋playbook」好例**として標準レシピ化してよい：**CREST/xtb**（配座探索）・**DP4+ 相当**（Boltzmann 平均＋Student-t の NMR 帰属、純 numpy で容易）・**PHREEQC**（`phreeqpython`）・**AutoDock Vina**（ドッキング）。**計算入力の文法は必ずベンダー一次資料で裁定**（例: ORCA で `! CASSCF` の行が抜けると、エラーにならずに HF だけが走る）。投入したジョブには必ず見張りを付ける（Step 8・`office/` の決まり「計算の見張り」）。

選択されたソフトに対応する Playbook を最初に読む：
- `office/computation/playbooks/<tool>.md`（存在しない場合は `references/playbook-starters.md` から該当セクションを参照）
- **初回利用の種まきオファー（任意・遅延／トークン枠保護）**：その Playbook が **cold-start**（`## Lessons Learned` も `## 外部リファレンス（web 由来・要検証）` も空＝同梱の starter しか無い）なら、入力生成に入る前に **1 回だけ**「このツールの初期 Playbook を web から種まきしますか？（web 検索でトークンを多めに使います・任意）」と尋ねる（`AskUserQuestion`。既定＝「今は入力を進める」）。**同意したときだけ**、その **1 ツールだけ** に対し raw スキルの `references/playbook-web-seeding.md` の手順を実行し（web で一次資料・公式を数クエリ調べ、`## 外部リファレンス（web 由来・要検証）` に出典 URL つきで既定・罠を追記。`## Lessons Learned` には触れない）、その結果を下の Step 4 の既定に反映する。**既に中身のある Playbook では尋ねない**。オンボーディングでは種まきしない方針の受け皿（[raw] Step 3-7）。

あわせて `office/computation/CLAUDE.md`（Codex / GitHub Copilot は `AGENTS.md`、Gemini は `GEMINI.md`）も読む — オンボーディングの計算環境（Q6）で記録された **submission の既定**（HPC か local か、queue・walltime・並列数・module load・account など）を、後段の実行スクリプト生成（Step 5）で使う。

### Step 2: 計算目的の確定

ソフトごとに用途を確認（`AskUserQuestion` 推奨）：

#### Gaussian / ORCA

- 単点エネルギー（SP）
- 構造最適化（Opt）
- 構造最適化 + 振動解析（Opt + Freq）
- 遷移状態探索（TS）
- IRC 計算
- 励起状態（TD-DFT）

#### CP2K

- 単点（SP, RUN_TYPE=ENERGY）
- 構造最適化（GEO_OPT）
- AIMD（MD, NVT/NPT）
- セル最適化（CELL_OPT）

#### GROMACS

- エネルギー最小化（em.mdp）
- NVT 平衡化
- NPT 平衡化
- プロダクション MD

#### VASP

- 単点（IBRION=-1, NSW=0）
- 構造最適化（IBRION=2, ISIF=3）
- AIMD（IBRION=0, MDALGO=2）
- DFT+U / HSE / SOC

#### Quantum ESPRESSO

- SCF（pw.x）
- 構造最適化（vc-relax）
- フォノン（ph.x）
- バンド構造

#### ChimeraX

- 構造/密度マップへのフィッティング（`fitmap` / Fit in Map）
- 可視化・高品質レンダリング（画像・ムービー）
- 解析（`measure correlation`・`molmap` でマップ生成・`matchmaker` で重ね合わせ・`morph`）
- cryo-EM モデル構築（ISOLDE 連携）

### Step 3: 系（system）情報の取得

以下を `AskUserQuestion` または対話で収集：

- 系の通称（例: "benzene", "C6H6 ring", "MOF-5 unit cell"）
- 電荷・スピン多重度（量子化学の場合）
- 初期座標：
  - 既存ファイル指定（`.xyz`, `.gjf`, `.cif`, `.pdb` 等）
  - SMILES → RDKit で 3D 生成
  - 既知の幾何（D6h benzene 等）→ 内部生成
- 周期境界（周期系 DFT / MD の場合）：cell parameters
- 力場（GROMACS の場合）：OPLS-AA / CHARMM36 / GAFF 等

### Step 4: 計算条件の確定（Playbook デフォルト起点）

Playbook の「デフォルト推奨パラメータ」を基準にしつつ、**`## Lessons Learned` の新しい教訓で上書き**して提示する（例: Lessons Learned に「`recalcfc=20` を既定に」とあれば推奨値へ反映）。**デフォルトブロックと Lessons Learned が食い違うときは、後から追記された Lessons Learned を優先**する。ユーザーが OK なら採用、変更要望があれば調整。

例（Gaussian Opt + Freq）:

```
推奨パラメータ：
- 汎関数: B3LYP
- 基底: 6-31G(d)
- 計算種: opt freq=noraman
- 並列: %nprocshared=8
- メモリ: %mem=8GB

これで進めますか？ それとも調整しますか（例: M06-2X / def2-TZVP / D3BJ）？
```

例（ORCA Opt + Freq）:

```
推奨パラメータ：
! B3LYP def2-SVP D3BJ Opt Freq TightSCF
%pal nprocs 8 end
%maxcore 2000

これで進めますか？
```

### Step 5: 作業ディレクトリ + 入力ファイル生成

**配置場所のルール（raw 規約）**: `<tool>/<system>_<purpose>_<YYYYMMDD>/`

```bash
mkdir -p <tool>/<system>_<purpose>_<YYYYMMDD>
```

例: `work/gaussian/benzene_opt_20260513/` / `work/orca/benzene_opt_20260513/` / `work/cp2k/water-box_aimd_20260513/`

このサブディレクトリに **入力ファイル + 実行スクリプト** を配置：

#### Gaussian

- `<system>.gjf` — 入力
- `run_<system>.sh` — qsub / sbatch 用ジョブスクリプト（HPC 利用時）

#### ORCA

- `<system>.inp` — 入力
- `run_<system>.sh` — ジョブスクリプト

#### CP2K

- `<system>.inp` — 入力（&GLOBAL / &FORCE_EVAL / &MOTION の階層構造）
- `run_<system>.sh` — ジョブスクリプト

#### GROMACS

- `<purpose>.mdp` — MD パラメータ（em.mdp / nvt.mdp / npt.mdp / md.mdp）
- 既存の `.gro` / `.top` を参照
- `run_<system>.sh` — `gmx grompp` + `gmx mdrun` の連続実行

#### VASP

- `INCAR` / `POSCAR` / `KPOINTS`（POTCAR は別途準備促す）
- `run_<system>.sh`

#### Quantum ESPRESSO

- `<system>.in` — namelist 形式
- `run_<system>.sh`

#### ChimeraX

- `<system>.cxc` — コマンドスクリプト（`open` 構造 + `open` 密度マップ → `fitmap` → `measure correlation` → `save` セッション/画像）。複雑なら `<system>.py`（`runscript`）
- `run_<system>.sh` — ヘッドレス実行：`chimerax --nogui --script <system>.cxc --exit`（サーバ/HPC でレンダが要るなら `--offscreen`＝Linux/OSMesa）

### Step 6: ジョブ記録の作成

`office/computation/jobs/YYYY-MM-DD-<system>-<purpose>.md` に記録：

```markdown
# YYYY-MM-DD <system> <purpose>

## 目的

<計算の目的、何を確認したいか>

## 入力

- 入力ファイル: `../../../<tool>/<system>_<purpose>_<YYYYMMDD>/<system>.<ext>`
- 系: <分子式・charge・multiplicity>
- 初期構造: <出典 or 生成方法>

## パラメータ

- 汎関数 / force field: ...
- 基底 / cutoff: ...
- 計算種: ...
- 並列: ...
- Playbook: `../playbooks/<tool>.md`

## 実行コマンド

\`\`\`bash
cd ../../../<tool>/<system>_<purpose>_<YYYYMMDD>/
<実行コマンド>
\`\`\`

## 結果

- [ ] 実行待ち
- 最終 SCF / エネルギー: TBD
- 収束判定: TBD
- 振動解析（該当時）: TBD

## 次のアクション

- [ ] 実行 → log 確認
- [ ] 必要なら精度拡張 / 範囲拡張
- [ ] 知見があれば Playbook の Lessons Learned に追記
```

### Step 7: 完了報告

ユーザーに以下を報告：

```
入力ファイル生成完了：

- 作業ディレクトリ: <tool>/<system>_<purpose>_<YYYYMMDD>/
- 入力: <file>
- ジョブ記録: office/computation/jobs/YYYY-MM-DD-<system>-<purpose>.md

実行コマンド:
  cd <tool>/<system>_<purpose>_<YYYYMMDD>/
  <実行コマンド>

実行後、log の確認は秘書に「結果を確認して」と伝えてください。
```

### Step 8: 投入するとき（見張りを必ず付ける）

ユーザーに投入を頼まれたら、`office/` の決まり「計算の見張り」に従い、**投入と同時に見張りを付ける**（頼まれなくても）：

1. 数分で終わらない計算は、セッションを閉じても止まらない形で走らせる（ローカルは tmux、HPC は qsub / sbatch）
2. `jobwatch.py register` で登録する（`--tool <ソフト>`・`--log`・PID かジョブ ID。Gaussian の opt+freq なら `--expect-count 2`。HPC が別の計算機なら `--host`）。道具のパスは起動時の文脈の「見張りの道具」にある
3. `jobwatch.py ensure-watcher` で見張りを起動し、Claude Code では `jobwatch.py wait <key>` を裏で走らせる
4. ユーザーに「何を・どの間隔で見ているか」と「予想の所要時間」を伝え、ジョブ記録の「結果」に登録の key を書く
5. 終わったら `jobwatch.py judge <key>` で判定し（終了コードでは決めない）、ジョブ記録と Playbook に反映して、同じ応答で次に投入するものを決める

---

## バッチ／スキャン生成（複数系・複数手法）

「benzene を B3LYP と M06-2X で」「複数分子をまとめて」のように **複数の系または手法（汎関数・基底のスキャン）** を指定された場合、各組み合わせを **1 計算 1 サブディレクトリ**で一括生成する：

- ディレクトリ名で組み合わせを区別：`work/<tool>/<system>_<purpose>_<method-slug>_<YYYYMMDD>/`（例 `work/gaussian/benzene_opt_b3lyp_20260618/`, `..._m062x_20260618/`）。
- 各々に入力＋実行スクリプト、`jobs/` 記録もそれぞれ作る。
- 件数が多いときは**生成する組み合わせ一覧を先に提示して確認**を取る（無断で大量生成しない）。
- 共通部分（系・基底など）は Playbook 既定を共有し、振る軸（汎関数など）だけ変える。

---

## 重要な注意事項

- **物理量には必ず単位コメント**（例: `# 1 fs`, `# 300 K`, `# 1 atm`, `# Å`）
- **エネルギー単位を統一**（Hartree / eV / kcal/mol / kJ/mol — ジョブ記録に明記）
- **乱数シードを固定**（MD の場合、再現性確保）
- **計算手法の選択は Playbook の Lessons Learned を踏まえる**（過去の失敗事例があれば回避策を組み込む）
- **HPC ジョブスクリプトは環境固有**：queue 名・walltime・並列数・モジュール load 順・account は、**まず `office/computation/CLAUDE.md` の submission 既定（オンボ Q6）** を使う。無ければ Playbook の過去事例、それも無ければユーザーに確認。**local 実行（SLURM 等を使わない）** 設定ならジョブスクリプトの代わりに直接実行コマンドを出す
- **入力ファイル・ジョブ記録は上書きしない**：同名サブディレクトリがあれば `<YYYYMMDD>` を `<YYYYMMDD>_v2` などに拡張。`jobs/...md` も同名があれば末尾に `-2` を付ける
- **分野の用語は正確に**：汎関数名（B3LYP は B3LYP）、基底（def2-SVP は def2-SVP）、force field（OPLS-AA / CHARMM36）、ソルバー名・要素の種類などの表記揺れを起こさない
