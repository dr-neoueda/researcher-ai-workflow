# Changelog

本ファイルは [Keep a Changelog](https://keepachangelog.com/) と [Semantic Versioning](https://semver.org/) に準拠。

## [2.1.0 / Codex 2.1.0] - 2026-11-10

### Added — 原稿とスライドの数値の照合

- `raw-write/scripts/check_numbers.py`：原稿・スライド（`.md` `.tex` `.txt` `.docx`〔脚注を含む〕 `.pptx`〔発表者ノートを含む〕）の数を抜き出し、事実の一覧（`facts.md`。書式は自由・複数可）と照合する。結果は「そのまま一致／丸めて一致（四捨五入）／不等号つきの丸め／指数だけ違う／丸め方が合わない／符号が違う／一覧に無い」に分け、要確認があれば終了コード 1、原稿から数が 1 つも取れなければ 2。指数は ×10⁻³・e-3・\\times10^{-3}・<sup>・Word と PowerPoint の上付きや数式・「10⁻³」を、マイナスは各種のハイフンと長音を読む。不等号は向きまで見る（上限は切り上げ・下限は切り捨て）。URL・DOI・日付・文献番号・版番号・図や表や行の番号・識別子（B3LYP など）・単位の指数・LaTeX の引用や組版の指定は数として読まない。既定は小数と指数表記だけ（整数は `--integers`）。スライドの位置は PowerPoint の表示順で示す。長い 1 行でも数に比例する時間で終わる。Word・PowerPoint は XML の構造をたどって読む（表・テキストボックス・タブ・改行・改行しないハイフン・数式）。図表の番号・版番号・識別子と判断して読まなかった小数は「（参考）読まなかった小数」として必ず挙げる（黙って捨てない）。一覧の側の不等号（「< 0.05」）は、原稿でも同じ向きの不等号の数だけを裏付ける。Word の上付きは、分かれた run・文字スタイル・位置の上げでも指数として読み、失われて「1.2×103」とくっついたものは「指数が読めない」に挙げる。マイナスは $-$・&minus;・\textminus・「= − 0.52」・Word の記号フォントも読む。数式の分数の分子と分母をつなげない。「1–3 × 10⁻³」の左端は右端の指数を共有する。グラフ・SmartArt・埋め込みの中の数は読まないので、あれば知らせる。大きな事実の一覧でも索引で速く照合する（3 万件 × 3 千件で数秒）。掛け算の記号 ⋅ ∙ ⨯、LaTeX の 1.2\,\times\,10^{-3}・$\times$ も指数として読む。Word で手で打った箇条書きの「- 」を負の符号と読まない
- `raw-write`：書き始める前に数を `facts.md` に集め（値・単位・何の値か・測定か試算か・出どころ）、本文はそこからだけ写す。書き終えるたびに照合し、終了コード 0 になってから報告する
- `raw-slides`：ビルドのたびに、書き出した pptx を同じスクリプトで照合する

### Added — どの分野でも守る「確かめ方の決まり」

- `office/` のルートの設定ファイルに 6 行の決まりを足した：数・日付はコマンドで出す／計算の成否はプログラム自身の出力で決める／「効果がない」の前に陽性が出ることを確かめる／原因や見込みは記録を引いてから伝える／差を取る 2 つは前提を揃える／文献値は一次資料まで辿る

### Changed — 測定データの置き場を試料ごとのフォルダに揃えた

- 測定データの置き場が 3 通りに分かれていた（実験部のルール・`raw-intake` の振り分け・`work/experiments/` を作るかどうかの設定）のを、`work/experiments/<試料 ID>/<手法>/` に揃えた。校正データは `_calibration/`
- `work/experiments/` を全員に作る（「計算は使わない」を選んだ人だけに作っていた）。設定の `wants_experiment_dir` は受け取って無視する
- `raw-intake` に「測定データの取り込み」の手順を足した：試料 ID・手法・条件を確かめる → 移す前に数える → 移す（コピーで元を残さない）→ 前後の数を照合する → 測定の記録 `info.md` を作る
- 実験部に測定の記録の雛形（`office/experiment/templates/measurement-info.md`）を足した

### Fixed

- `raw-analyze`：生データの置き場の説明に、作者の作業場所のパスが残っていた
- ルートの設定ファイルの成果物の表で、発表資料の場所が `slides/` になっていた（実際は `work/presentations/slides/`）

## [2.0.1 / Codex 2.0.1] - 2026-11-06

### Fixed — Codex レビューの指摘（v2.0.0 のマージ後）

- オンボーディング：分野が「共通」のときの計算ソフトの質問に選択肢が 1 つしかなく、質問の道具（選択肢は 2 つ以上）が使えなかった。「計算ソフトを使う」「計算は使わない」の 2 つにした
- 工学・情報の規律：性能の比較で「同じハードウェア」を求めていたのを、比べる対象でない実行環境を揃える書き方にした（ハードウェアそのものを比べる研究を締め出さない）。設計値・計算値・実測値は「混ぜない」でなく「系列・列の名前で分かるようにする」に
- scaffold：選択肢の節のフェンスの後に 1 行の HTML コメント（保守の注記）を書けるようにした。書けるもの（空行・`---`・1 行のコメント）を `field-rules.md` の冒頭に明記
- 文面：Codex 版の README、Web の CLI のページ（導入・スキル・コマンド・外し方）に残っていた「化学者向け」の製品説明と起動の例文を研究一般に直した。Codex の外し方の確認コマンドは新旧どちらのマーケットプレイス名も探す

## [2.0.0 / Codex 2.0.0] - 2026-11-06

### Changed — 対象を理工系の研究者へ広げ、名前を変えた（破壊的変更）

- **名前**：商品名を「研究者のための AI エージェント導入伴走」（英語名 Researcher's AI Workflow）に変えた。
  コマンドとプラグイン ID を `caw` → **`raw`**、スキル名を `caw-*` → **`raw-*`**、配布元とマーケットプレイス ID を
  `chemist-ai-workflow` → **`researcher-ai-workflow`** に変えた。**旧名で入れたプラグインは自動では更新されない**ので
  入れ直す（README「旧名 caw から移る」）。作ってあった `office/` と `work/` はそのまま使える
- **分野ごとの規律**：オンボーディングの分野（化学・材料／物理・地球惑星／生命科学／工学・情報／共通）を設定の
  `field_group` に書くと、scaffold が `references/field-rules.md` から該当する規律を選んで `office/` のルートに差し込む。
  知らない値なら何も書かずに止まる。**化学・材料の規律は従来の 6 行と一字一句同じ**
- **オンボーディング**：分野の大分類を 4 群＋その他に（質問の選択肢の上限 4 に合わせた）。中分類と計算ソフトの
  選択肢を群ごとにした。化学・材料の計算ソフトの候補は従来どおり（7 個を 2 問に分けて聞く）
- **部署の雛形**：`chemistry-departments.md` → `research-departments.md`。化学に寄った言い回しを研究一般に直し、
  化学の具体例は「例：」として残した。計算管理部の対応ソフトの例に構造予測・有限要素・数値計算を足した
- **web 種まき**：有限要素・流体、数値計算、生命系、機械学習の観点を足した
- **`raw-doctor`**：規則ファイルに残った旧名 `caw` を見つけ、了承を得て置き換える検査を足した（メモ・TODO は書き換えない）
- 他のスキル（input / playbook / register / write / intake / doctor / report / slides）の文言を研究一般に直した。
  文書の中で「生データ」の意味の raw は「生データ」と書き、コマンド名と区別した

### Paused — GitHub Copilot CLI 版

- 理工系への拡張と改名は Claude Code 版と Codex CLI 版だけ。Copilot 版は v1.78 の内容（化学者向け・旧名 `caw`）のまま
  開発を保留した（`copilot-plugin/PAUSED.md`）。保留中は `check-consistency.sh` の Codex↔Copilot のミラー検査を飛ばす

## [1.78.0 / Codex 1.77.0 / Copilot 1.46.0] - 2026-11-01

### Changed — `caw-slides` を実運用の到達点まで引き上げ

7 月時点のデザインと手順のまま止まっていた `caw-slides` を、実際の研究発表で固めた規約と道具に揃えた。実デッキ 2 本（計 21 枚・図形 639 個）を新しい経路で書き出し、元の書き出しと種類・位置・大きさ・文字・文字サイズ・和文フォント・上付き・画像の中身まで全図形が一致することを確認した（未発表データのため照合は手元のみ）。

- **デザイン規約を全面改訂**（`references/design-system.md`）：定型の生成物に見える構造物を廃止（強調帯と見出しの縦棒・二言語キッカー・タイトル下のリード文・全ページの注記・固定幅の枠）。タイトルは主張形でなく短い名詞句、区切り線は y=140、フッターは番号のみ、本文は 14 pt 以上、低塗り、要点ボックスは枠線＋ごく薄い地。文章の規約（確定した結果だけ・書き言葉・見出しに人名を入れない・文中に「—」を使わない）を追加。
- **`scripts/build_deck.py`（新規）**：検定→変換→後処理→出力検定を 1 コマンドに固定。落ちたら配布先に何も出さない。CLI ごとに手順がぶれない。旧来の `_build.py` を貼る手順を廃止。
- **描画部品（新規）**：`deck_chrome.py`（見出し・本文・強調帯・表紙。`^{}` / `_{}` で上付き・下付き）、`deck_parts.py`（表・図枠・矢印・バッジ）、`fig_style.py`（matplotlib の書式）。
- **検定（新規）**：`check_margins.py`（右余白）、`vendor/svg_quality_checker.py`（SVG の制約・上流を無改変で同梱）。`assert_no_overlap` は viewBox からキャンバス寸法を読む（ポスターを誤判定しない）。`assert_font_rule` / `fix_ea_font` は丸数字を和文扱いにする。
- **後処理（新規）**：`fix_scripts.py`（変換器が捨てる上付き・下付きを復元）、`ungroup_pptx.py`（グループを解いて編集しやすくする）。
- **動画（新規）**：`prepare_video.py`（H.264・BT.709）、`add_videos.py`（自動再生・ループ）。`videos.json` で位置を指定。
- **発表ノート**：`notes/<SVG の名前>.md` が各枚のノートに入る。
- **手直し版の保護（新規）**：`build_deck` は前回の書き出しと中身が違う pptx を `--force` なしでは上書きしない。`copy_slide_pptx.py` で 1 枚単位の差し替えができる（他の枚からのリンク・背景の画像・図形の結線も引き継ぐ）。
- **プレビュー（新規）**：`make_preview.py`（Chrome / Edge。1280×720 を検定）。
- **見本（新規）**：`references/sample_deck.py`。全機能を使う生成器の手本で、テストでも通しで走る。

### Changed — デッキのフォルダ

- スライドは `_src/<deck>/svg_output/*.svg`、図は `_src/<deck>/images/`（SVG からは `../images/<名前>`）に置く。旧来の `_src/<deck>/*.svg` は `svg_output/` へ移す。

### Removed

- `scripts/embed_image.py`：変換器が `../images/` を直接読むので不要。図の縦横比は `deck_parts.figure` が扱う。
- cairosvg への言及：プレビューは Chrome / Edge に統一（cairosvg は外部画像を空白で描き、重なりを見逃す）。

### Fixed

- 全角空白を含む行の上付き・下付きが復元できなかった（変換器が全角空白を半角へ置き換えるため）。
- 個人化リーク検査の語を追加（`scripts/check-consistency.sh`）。

## [配布物の版は据え置き — リポジトリ側ツールの追加] - 2026-08-24

### Added — USB 等で手渡しするオフライン導入バンドル

**想定シナリオ**：ネットは通るが**ファイルのダウンロードが制限される**環境（企業ネットワークで GitHub がブロックされている等）。USB から相手の PC にコピーして caw 環境を構築する。**完全オフラインは対象外**（caw は CLI がモデル API を呼ぶためネット自体は必須）。

- **`scripts/make-offline-bundle.sh`（新規）**：配る側が実行してバンドルを生成する。**3 CLI 分のマニフェストとプラグインを 1 つのフォルダに同居**させる（`.agents/plugins/` ／ `.claude-plugin/` ／ `.github/plugin/` と読まれる場所が CLI ごとに違うため共存できる）＝**1 本の USB で相手がどの CLI でも使える**。`gemini-plugin` は凍結中のため同梱しない。生成物 **3.1 MB**（リポジトリ 221 MB のうち `web/` 189 MB と `.git` 20 MB は不要）。
  - **設計原則：バンドルは marketplace 配布と byte 一致でなければならない。** 加工すると「第 3 の配布面」が生まれてドリフトするため、copy と除外（`.DS_Store` / `__pycache__`）のみを行い、**最後に `diff -r` で一致を検証**する。
  - 出力先が空でなければ中止する（既存を破壊しない）。
- **`scripts/bundle-templates/`（新規）**：受け取る側が実行する `install.sh`（macOS/Linux）・`install.ps1`（Windows）・`はじめにお読みください.md`。CLI を自動検出し、コピー → marketplace 登録 → プラグイン導入まで行う。スクリプトがスクリプトを生成する形は読みづらく壊れても気づきにくいため、**テンプレートは実ファイルで持つ**。
- **⚠️ 実測で見つけた落とし穴：ローカルパスの marketplace は「その場」を参照し続ける。** Git 由来は `~/.codex/.tmp/marketplaces/<name>/` に**クローンされる**が、**ローカルパス由来は指定パスをそのまま root にする**（コピーされない）。⇒ **USB を直接登録すると抜いた時点で caw が壊れる。** `install.sh` はこれを避けるため必ず `~/caw-plugin` にコピーしてから登録し、既存があれば `caw-plugin.old-<日時>` へ退避する（削除しない）。
- **実測で確定させたコマンド形**（ヘルプの記述だけで判断せず実行して確認）：
  - **Codex**：`codex plugin marketplace add <path>` → `codex plugin add caw@chemist-ai-workflow` ── **完全実証**（1.1 MB のローカルディレクトリを登録し `caw@<name>` が installable と表示されるまで確認、検証後に撤去）
  - **Claude Code**：`claude plugin marketplace add <path>` → `claude plugin install caw@chemist-ai-workflow` ── 登録まで実証（`Source: Directory` として受理）。インストールは既存登録を増やすため未実行
  - **GitHub Copilot CLI**：未検証（実機確認そのものが未了）
  - **git は不要**（clone しないため）。第 1 回テスト会で判明した「git が隠れ前提」はこの経路では消える
- `install.sh` を実走して検証：コピー 3.1 MB・インストーラ自身の除外・全マニフェストの存在・CLI 自動検出（Codex と Claude を発見、Copilot を未導入と判定）。
- **前提**（バンドルは caw 本体のみ。相手側で用意が必要）：CLI 本体・Node.js LTS・Python 3・Python パッケージ。`install.sh` は CLI が無ければ導入コマンドを案内して終了する。
- **配布物（plugin / codex-plugin / copilot-plugin / gemini-plugin）の中身は変更していないため版は据え置き。**

## [1.77.0 / Codex 1.76.0 / Copilot 1.45.0 / Gemini 1.49.0 ⛔FROZEN] - 2026-08-21

### Changed — 本命 CLI を Claude Code → **Codex CLI** に変更

伴走（マンツーマン導入支援・1 セッション 3 時間規模）で**セッション途中に使用量上限へ当たらない**ことを優先し、Tier 1 を入れ替えた。**Codex は 2026-07-12 に 5 時間ローリングウィンドウが撤廃され、週次上限のみ**になっている（OpenAI の Codex 責任者が announce）。

> ⚠️ **調査上の教訓**：`learn.chatgpt.com/docs/pricing` は撤廃後も旧ポリシーの 5 時間テーブルを残しており、**ドキュメントだけを見ると「5 時間制限あり」と誤読する**。決定的だったのは一次コミュニティの検定＝`openai/codex` の issue で **「5-hour limit」への言及は 2026-07-22 が最後**、**8 月に立った使用量 issue 20 件は全て「weekly」**だったこと。「まだ有効か」はドキュメントではなく**新規報告が止まったか**で判定する。

- **Tier 表を入れ替え**（`RESUME.md` / `README.md` / gemini の 2 ファイル）：Codex CLI = Tier 1（本命）、Claude Code = Tier 2。
- **⚠️ 未解決**：本命になった Codex 版に **hooks が無い**。Codex CLI は hooks を公式サポート（`SessionStart`/`PostToolUse`/`Stop` ほか、プラグインが `hooks/hooks.json` で同梱可、Windows 対応、既定で有効、`PLUGIN_ROOT` と互換の `CLAUDE_PLUGIN_ROOT`）だが、**単純コピーでは動かない**：(a) `CLAUDE_PROJECT_DIR` が無く stdin JSON の `cwd` を使う (b) 出力を `{"hookSpecificOutput":{...,"additionalContext":...}}` で包む必要がある (c) **PostToolUse の対象が `apply_patch` で `tool_input.file_path` が存在しない**ため patch 解析が要る。`RESUME.md` に分割方針つきで追跡タスク化。

### Added — GitHub Copilot CLI 版を 2 スキルの PoC から **15 スキルへフルポート**

企業顧客（化学メーカーの研究部門など、GitHub Copilot が全社導入されている組織）での導入伴走を想定したトラック。

- **13 スキルを codex-plugin から byte 一致でコピー**：`caw-research` / `caw-register` / `caw-write` / `caw-input` / `caw-playbook` / `caw-analyze` / `caw-slides`（38 ファイル・vendor 含む）/ `caw-doctor` / `caw-intake` / `caw-report` ＋ `caw-es` / `caw-interview` / `caw-events`。`caw` と `caw-setup` は Copilot 固有の CLI 名を持つため系統別に維持。
- **就活 3 本も入れた（当初方針の変更）**：企業顧客に不要なので落とす想定だったが、**copilot の `caw` オンボーディングは既に就活トラックを提示し `job-hunting-departments.md` も同梱済み**で、3 本を欠くと「部署は作られるがスキルが無い」不整合になるため全 15 本とした。
- **⚠️ dangling reference を修正**：`html-style.md` が copilot に無いのに**移植したスキルから 7 箇所参照**されていた（HTML 生成スキルのデザイン規約）。コピーして解消。全参照の解決を機械監査（唯一残る `shared-standards.md` は **codex 側でも同様に不在**＝上流 PPT Master の出典表記であり同梱物ではないことを対照確認）。
- **⚠️ 版ドリフトを修正**：`.github/plugin/marketplace.json`（Copilot の配布 manifest）が **1.17.0 のまま 2026-06-18 から放置**され、プラグイン本体 1.44.0 と乖離していた。**何もこの組を比較していなかったのが原因**なので、`check-consistency.sh` に比較を追加（**実在の不一致 1.44.0 vs 1.17.0 で BAD が出ることを確認**してから修正）。
- **CLI 列挙で Copilot が抜けていた 7 箇所を 3 系統そろえて修正**：`caw-slides`（自己完結の CLI 列挙）・`caw-playbook`（memory 代替先）・`caw-write`／`caw-es`／`caw-interview`（好み・傾向の学習が共通な CLI）・`caw-report`（`office/` ファイル名の CLI 対応）・`html-style.md`（HTML 統一対象）・`mcp-setup-templates.md`（MCP 登録先。「Codex CLI を併用する場合」→「他の CLI を併用する場合」に一般化）。
- **ドリフト防止を追加**：`check-consistency.sh` に (1) copilot marketplace 版一致 (2) 単一ファイルミラーへ `html-style.md`・`chemistry-departments.md` 追加 (3) **13 スキルのディレクトリ単位 byte 一致検査**。**(3) は copilot 側に 1 行注入して BAD が出ること・復旧で OK に戻ることを実データで確認**。
- `copilot-plugin/README.md` を全面更新（PoC 表記を撤廃・15 スキル表・既知の制約を明記）。`plugin.json` の `"skills": ["skills/"]` はディレクトリ指定のため列挙の更新は不要だった。
- **既知の未了**：`caw-slides` の **Windows 実機確認は未実施**（パイプラインは v1.71.0 で Windows 互換化済みだが Copilot CLI 上では未検証）。hooks 未移植。
- **⚠️ 配布物に混入していた「走らせると落ちるテスト」を除去（既存の欠陥）**：`codex-plugin/skills/caw/tests/test_scaffold.py` は plugin 版からの byte 一致コピーで、**`CLAUDE.md` を期待するアサーションを持つ**。codex/copilot の scaffold は**正しく `AGENTS.md` を出す**ため、その系統で走らせると **3 件が必ず落ちる**（実装は正常・テストが系統を見ていない）。**`plugin` の正本スイートには `test_scaffold_agents_variant_codex` があり、codex-plugin の references を直接読んで `AGENTS.md` 生成を検証している**（skip されず PASSED を確認）ので、codex 側の挙動は既にカバー済み。よって配布物からテストのコピーを削除した（v1.48.0 で `plugin/TESTING.md` を payload から出したのと同じ原則＝開発用成果物を install payload に入れない）。
  - 発見の経緯：copilot に移植した `scaffold.py` を**その同梱テストで実際に走らせた**ところ 3 件 FAIL。`scaffold.py` は 3 系統 byte 一致だったので「同じバイトだからカバーされている」で済ませていたら見逃していた。**対照として codex 版でも走らせ、同じ 3 件が落ちる＝移植起因ではなく既存欠陥**と切り分けた。
  - なお本セッション中に報告していた「125 passed」は **plugin 変種のスイートのみ**の結果であり、codex 変種のテストは一度も走っていなかった。
  - **既知の未了**：`plugin/` は依然としてテストを install payload に同梱している（同種の問題だが今回のスコープ外）。
- `scaffold.py` を plugin↔codex・codex↔copilot 双方のミラー検査に追加（**copilot 側に 1 行注入して BAD が出ることを確認**）。3 系統とも 510 行で byte 一致。
- 版 plugin 1.76→**1.77**・codex 1.75→**1.76**・copilot 1.44→**1.45**（marketplace も 1.17.0→**1.45.0** に同期）。gemini は凍結のため据え置き。

## [1.76.0 / Codex 1.75.0 / Copilot 1.44.0 / Gemini 1.49.0 ⛔FROZEN] - 2026-08-21

### Changed — CLI トラックの再配分：Gemini を凍結し、Copilot を企業向けにフルポートする方針へ

商品モデルが「プラグインを配る」から「**導入伴走を売る**」に変わったこと（同日確定）を受け、4 CLI 系統の保守面積を測って再配分した。**削減ではなく再配分**である点に注意。

**実測した保守コスト**：

| 系統 | 行数 | コミット | 版上げ | スキル |
|---|---|---|---|---|
| plugin（Claude Code） | 21,061 | 89 | 87 | 15 |
| codex-plugin | 19,918 | 82 | 85 | 15 |
| copilot-plugin | 3,440 | 41 | 20 | **2** |
| gemini-plugin | **226** | 43 | **44** | 15 |

- **Gemini を凍結（非推奨）**：`gemini-plugin` は **226 行しかないのに 43 コミット・44 回の版上げ**を消費していた（本体 87 版に対し、**変更のおよそ 2 回に 1 回は追従が必要な定額コスト**）。かつ第 1 回テスト会で「無料枠では caw のオンボーディングすら完走できない」と実地に判定済み。伴走で相手の環境に入れるのは Claude Code / Codex / Copilot の 3 系統になり、Gemini を勧める場面が無くなった。
  - **`gemini-plugin/FROZEN.md`（新規）**：凍結記録の**単一情報源**。`frozen_date` / `frozen_at_plugin_version` / `frozen_at_gemini_version` と、凍結理由・保守コスト実測・**解除条件**・復活手順を記載。
  - **`scripts/check-consistency.sh`**：`FROZEN.md` を読んで **「本体から何 minor 遅れているか」を毎回表示**し、20 minor 以上で NOTE を出す。**ずれを隠さず、測れる形で見せる**方針（「残すが凍結」の既知リスク＝古いファイルが main に残ってずれが再び育つ、への対策）。**既知の遅れ 24 minor で NOTE が発火し、5 minor では発火しないことを実データで検証**。
  - `gemini-plugin/README.md`・`GEMINI.md` の冒頭に凍結告知。版は **1.49.0 で据え置き**（以後上げない）。
- **Copilot をフルポートする方針を決定**（実装は次段）：**企業顧客では Copilot が対象になることが多い**ため。現在 2 スキル（`caw` / `caw-setup`）。移植規模を実測したところ、**単一ファイルの 10 本は SKILL.md のコピー＋`trigger:` 除去等の軽微な置換で済む**（Codex 版との差分を diff で確認）。`caw-input`・`caw-analyze` は `references/` のミラーが加わる。`caw-slides` のみ 19,301 行（うち 12,179 行は無改変 vendor）で Windows 実機確認が要る。**就活トラック 3 本（`caw-es`/`caw-interview`/`caw-events`）は企業顧客に不要なため Copilot には載せない**（研究トラック 12 本に絞る）。
- 版 plugin 1.75→**1.76**・codex 1.74→**1.75**・copilot 1.43→**1.44**。**gemini は凍結のため据え置き 1.49.0**。

## [1.75.0 / Codex 1.74.0 / Copilot 1.43.0 / Gemini 1.49.0] - 2026-08-20

### Fixed — 正典ドキュメントの stale 化を解消（配布物 4 系統の README ＋ リポジトリ内の再開ポイント）

42 日の中断（最終コミット 2026-07-09）を挟んで開発を再開するにあたり全ドキュメントを実態と突き合わせたところ、**「次回まずこれを読む」とされているファイルが軒並み 1〜3 か月 stale** で、なかでも配布物である各 CLI の README が**ユーザーに見える形で誤っていた**。

- **`plugin/README.md`**：見出しが `含まれる内容（v1.30.0）` のまま（実態 v1.74.0）で、**15 スキル中 9 しか記載が無かった**。不足していた `caw-analyze` / `caw-intake` / `caw-report` ＋就活トラック 3 本（`caw-es` / `caw-interview` / `caw-events`）を追記し、研究/就活トラックの区分を明示。プラグイン構造ツリーの `skills/` 一覧も現状化。
- **`codex-plugin/README.md`**：`含まれる内容` が `caw` / `caw-setup` / `caw-playbook` の 3 本しか触れておらず、**Codex 版も 15 スキルある**という事実が読み取れなかった。15 スキルの表に差し替え。Playbook 雛形の列挙も 6 → 11 ソフト（Psi4 / NAMD / LAMMPS / OpenMM / ChimeraX を追加）に修正。
- **`caw-setup` の説明が v1.68.0 で撤回した仕様のまま**（plugin / copilot）：「計画提示 → **一度の承認** → 順番にインストール」と書かれていたが、v1.68.0 で**一括承認は撤回**し per-tool・理由説明つきに変更済み。3 系統の記述を実装に合わせた。
- **`copilot-plugin/README.md`**：未収載スキルを「残りの 6 スキル」としていたが実際は **13 スキル**。全 13 本を列挙し、フルポートの可否が未決である旨を明記。
- **`gemini-plugin/README.md`**：`caw-analyze` / `caw-report` / `caw-setup` が「できること」から漏れていたため追記。
- **リポジトリ内ドキュメント（配布対象外）**：`RESUME.md` は「**凍結中・新規作業は行わない**」（2026-05-09 の記述）のままで次セッションを誤誘導する状態だったため全面書き直し。`README.md`（リポジトリ直下）は「現フェーズ：構想」だったため現状化。`docs/roadmap.md` は Phase 0–3 を実績で置き換え、Phase 4（商品化）を**未決の問い 6 件**として明示。
- **記録した事実**：当初計画の「教材（テキスト商材）」から「4 CLI 対応プラグイン ＋ ドキュメントサイト」へ商品形態が転換しており、`content/` `templates/` `case-studies/` `marketing/` は存在しない。旧 roadmap の「教材ページ数」等の指標は無効として撤回。
- **⚠️ `caw-setup` の frontmatter が本文と矛盾していたのを修正（plugin / codex / copilot の 3 系統）**：SKILL.md の**本文**は v1.68.0 で per-tool 方式（「1 つずつ『なぜ必要か』を添えて尋ねる・一括の暗黙導入も勝手なスキップもしない」）に更新済みだったが、**frontmatter の `description` だけが旧仕様「計画を提示して一度の承認のうえ順番にインストールする」のまま**残っていた。`description` はエージェントが発火判断と挙動把握に使うため、**本文と矛盾した指示を先に読ませている**状態だった。gemini の `GEMINI.md` のみ正しく更新済みだったため、3 系統で修正して揃えた。旧文言の残存を全系統 grep で 0 件確認。
- 上記を除きコード変更なし。consistency 全 OK、125 passed / 4 skipped。
- 版 plugin 1.74→**1.75**・codex 1.73→**1.74**・copilot 1.42→**1.43**・gemini 1.48→**1.49**。

> **教訓**：日付入りのドキュメントは「直した日」ではなく「最後に見た日」しか示さない。`RESUME.md` の冒頭に「本ファイルの記述は正しさの保証ではない・実態は `git log -1` と `check-consistency.sh` で確認せよ」を明記した。参照: memory `feedback_document_staleness_from_source_mtime_not_stated_date`。

## [1.74.0 / Codex 1.73.0 / Copilot 1.42.0 / Gemini 1.48.0] - 2026-07-09

### Changed — 初期構築のトークン第2削減：scaffold をモデルの逐次 Write から `scaffold.py` 1 実行へ

第 2 回テスト会で判明した「初期構築のトークン過多」の第 2 の主因＝**Step 3 scaffold がモデルに ~40 ファイルを個別 Write させていた**（Write の中身＝そのまま出力トークン、概算 15〜25k）。同梱スクリプトが参照ファイルをパース・置換して配置する方式へ変更し、モデルが書くのは **設定 JSON 1 枚＋`work/profile/` の小ファイルだけ**に圧縮。

- **`scripts/scaffold.py`（新規・plugin/codex/copilot 3 変種で byte 一致）**：オンボ回答 JSON を受け、`references/*.md`（`chemistry-departments.md`＝`### <path>`+fenced、`claude-md-template.md`／`agents-md-template.md`、`playbook-starters.md`、`mcp-setup-templates.md`）をパースして `office/**` + `work/**` を一括生成。root 出力は `CLAUDE.md`（Claude Code）／`AGENTS.md`（Codex/Copilot）を自動判定。**24〜40 ファイルの逐次 Write → 1 コマンド実行**。
- **caw SKILL.md Step 3 を配線**（plugin/codex/copilot）：3-1 設定 JSON を書く → 3-2 `python3 ${SKILL}/scripts/scaffold.py` 実行 → 3-3 `work/profile/research-profile.md` だけ Write。Python 未導入時のフォールバックを明記。旧・詳細な部署/work-dir/README テーブルはスクリプトへ移動（SKILL も 496→430 行に圧縮）。
- **安全性（二段レビュー: Claude python-reviewer + Codex adversarial ×2 周）**：path traversal guard（`safe_relpath`/`resolve_within`/`normalize_tool`）・Windows 予約名拒否・fence fail-closed・`assert_no_placeholders`・mutable ファイル（playbook/todo）保護・`assemble_mcp` を fence-aware（`### Q3/Q4 = <choice>`）に。**25 pytest GREEN**。記録 `review/code-reviews/2026-07-09-caw-scaffold.md`。
- **`playbook-starters.md`**：`chimerax` が fence 欠落で silent drop していたのを修正（fence 化＋`{{TODAY}}`）。回帰ガード test（全 `### computation/playbooks/*` header が抽出される）を追加。
- **gemini** は単一 GEMINI.md 構造で参照ファイル/スクリプトを同梱しないため**散文 scaffold のまま**（据置 1.48.0）。plugin/codex/copilot が script 方式。
- 版 plugin 1.73→**1.74**・codex 1.72→**1.73**・copilot 1.41→**1.42**。consistency 全 OK。

## [1.73.0 / Codex 1.72.0 / Copilot 1.41.0 / Gemini 1.48.0] - 2026-07-09

### Changed — 初期構築のトークン過多を解消：Playbook の web 種まきをオンボーディング自動から「初回利用時・1 ツール」の遅延方式へ

第 2 回テスト会で判明した最大の問題＝**初期環境構築でトークンを使い過ぎる**の主因は、オンボーディングの `Step 3-7` が名指しツールごとに web 検索サブエージェントを**並列自動起動**していたこと（3〜6 ツールで 10 万〜30 万トークン級、caw を使い始める前に利用枠を消費）。**種まきを onboarding から外し、遅延（lazy）方式に変更**した。

- **オンボーディングでは web 種まきを自動起動しない**（全 4 変種：plugin/codex/copilot の caw `SKILL.md` §3-7、gemini `GEMINI.md`）。同梱の `playbook-starters.md` 由来の starter でそのまま使い始められる。
- **遅延方式**：`caw-input` が対象ツールの Playbook を **cold-start**（`## Lessons Learned` も `## 外部リファレンス` も空）と検出したときだけ、入力生成前に **1 回だけ**「このツールの初期 Playbook を web から種まきしますか？（トークン多め・任意）」と尋ね、**同意時のみ・そのツール 1 つだけ**種まきする（plugin/codex の `caw-input` Step 1）。明示要求「◯◯を web から種まきして」も 1 ツール単位で `caw-playbook` から実行可（plugin/codex）。
- **`playbook-web-seeding.md`（plugin↔codex↔copilot バイト一致）**：タイトル・「いつ・どう走らせるか」を「初回利用時・1 ツールだけ・遅延／onboarding では走らせない／web 検索は最小限」に作り替え。
- 効果：オンボーディングのトークンを、名指しツール数に比例した web 研究エージェント分だけ丸ごと削減。種まきコストは「実際にそのツールを使うユーザー」にだけ、使うツール分だけ後払いになる。
- 版 plugin 1.72→**1.73**・codex 1.71→**1.72**・copilot 1.40→**1.41**・gemini 1.47→**1.48**。consistency 全 OK。

## [1.72.0 / Codex 1.71.0 / Copilot 1.40.0 / Gemini 1.47.0] - 2026-07-06

### Changed — caw-slides 出力クリーンアップ：最背面フル白パネル廃止＋切り替えアニメを明示無効化

caw-slides の authoring ガイドが本文ページに**フルキャンバスの白 `<rect x0 y0 w1280 h720 fill=#FFFFFF>`** を描くよう指示しており、vendored 変換器がそれを**最背面のスライド大シェイプ**として pptx に出していた。PowerPoint のスライド背景（slideMaster `bgRef schemeClr=bg1`＝既定で白）と冗長で、編集時に背面の白四角を誤選択する・シェイプ数が 1 枚ごとに増える弊害があった。ラボ本体の PPT Master プロセスは 2026-07-06 に同挙動を廃止済みだったが、caw 配布側に未反映（ドリフト）だったため揃えた。

- **`references/design-system.md`（plugin ↔ codex バイト一致）**：本文ページの「背景：`<rect …/>`」を **「背景シェイプは置かない（SVG は実コンテンツから開始・ページ背景は master bg1=白がそのまま出る）」** に変更。§7 オーサリング厳守事項 #5「背景は `<rect>`」を **「全面背景 rect は生成しない。塗りが要る領域だけ部分 `<rect>`/`<path>`」** に修正。
- 影響範囲：SKILL.md のスケルトンは元から bg rect を持たず修正不要。gemini GEMINI.md は design-system を inline せず（bg-rect 指示なし）、copilot は caw-slides 非同梱のため、**copilot/gemini は据置**。
- ドキュメント変更のみ・既存デッキの再生成不要（新規デッキから白パネルが出なくなる）。
- **切り替えアニメの明示無効化**：生成スニペット `_build.py`（SKILL.md・plugin/codex）で `create_pptx_with_native_svg(..., transition=None)` を明示。vendored 変換器は `pptx_animations` を非同梱＝`ANIMATIONS_AVAILABLE=False` で**元から `<p:transition>` を出さない**（実機 2 枚デッキで transition/timing/anim ノード 0 を実証）が、API 既定が `transition='fade'` のままだったため、将来 animation モジュールを同梱しても切り替えが復活しないよう **`None` で短絡**（`if transition and ANIMATIONS_AVAILABLE:` を確実に False に）。スライド切り替えアニメなしがユーザー既定。
- 版 plugin 1.71→**1.72**・codex 1.70→**1.71**。consistency 全 OK。

## [1.71.0 / Codex 1.70.0 / Copilot 1.40.0 / Gemini 1.47.0] - 2026-07-06

### Changed — 第 2 回テスト会（スライド作成ハンズオン・Windows）向けに手順書とパイプラインを整備

明後日のテスト会（Windows ユーザーのみ・スライド作成ハンズオン）に向けて、ツール導入手順とスライド生成の Windows 互換性を整えた。

- **`TESTING-slides-handson.md`（新規）**：Windows 向けスライド作成ハンズオン手順書。①スライド用ツール導入（`環境を整えて` で per-tool 導入 or 手動 `py -m pip install python-pptx pillow pymupdf matplotlib numpy`）②`work/presentations/figures/` に画像を置く ③「スライド作って」④pptx を PowerPoint で開いて編集可能性を確認、の流れ＋Windows トラブルシュート。
- **`web/.../requirements.md` 更新**：スライドツールを現状（SVG-first）に。**PyMuPDF を追加**、python-pptx/pillow/matplotlib の役割を明記、`/caw-setup` を「一括」→「per-tool・理由説明つき」に、動作確認を `import pptx, PIL, fitz, matplotlib` に更新。Windows pip 行に `pymupdf` 追加。
- **caw-slides Step D を Windows 互換に**（plugin/codex）：`for f in ...; do ...; done` の bash ループを撤廃し、**inline（画像 data-URI 化）＋変換を 1 つの Python（`_build.py`）**に統合（`py _build.py` で動く）。実ローカル画像で PICTURE 埋込を確認。
- 版 plugin 1.70→**1.71**・codex 1.69→**1.70**（copilot/gemini はスライド Step 変更の影響外で据置）。consistency 全 OK。

## [1.70.0 / Codex 1.69.0 / Copilot 1.40.0 / Gemini 1.47.0] - 2026-07-04

### Added — ユーザー画像を `work/presentations/figures/` に置いてスライドに使えるように

`work/presentations/figures/` を **スライド用画像のユーザー投入フォルダ**として正式化し、caw-slides がそこの画像（顕微鏡写真・装置スクショ・外部プロット・スキャン図・ロゴ 等）を拾って**アスペクト比を保って埋め込む**ようにした。実データ画像で質の高いスライドを作れる。

- **scaffold**：caw オンボーディングで `work/presentations/figures/` を作成し、README に「ここに画像を入れると『スライド作って』で caw-slides が拾って埋め込む」と平易に明記（plugin/codex/copilot の caw SKILL）。
- **`scripts/embed_image.py`（新規）**：SVG 内の `<image href="local">` を **data-URI にインライン化**（vendored 変換器に埋め込ませる）＋ `image_size`/`fit_box`（アスペクト維持・既定は非拡大）。堅牢化：クォート/空白/`xlink:href` 対応・`data-href` 誤一致回避・コメント領域除外・**MIME は magic bytes 判定**・**path traversal ガード**（base_dir 外は `--allow-outside` 時のみ）。
- **caw-slides SKILL**：Step A に `work/presentations/figures/` を素材源として追加、Step B に画像埋め込み（アスペクト維持）、Step D に「変換前にローカル image href を data-URI 化」を追加。
- **TDD＋二段レビュー**：pytest 32 件（regex 全バリアント・traversal・magic MIME・コメント・upscale）。Claude+Codex が `_HREF_RE` の silent バグ 2 件を一致検出→修正（記録 `review/code-reviews/2026-07-04-caw-slides-embed-image.md`）。caw-slides 全 104 PASS。plugin↔codex バイト一致・gemini 節も更新。
- 版 plugin 1.69→**1.70**・codex 1.68→**1.69**・copilot 1.39→**1.40**（figures scaffold）・gemini 1.46→**1.47**。consistency 全 OK。

## [1.69.0 / Codex 1.68.0 / Copilot 1.39.0 / Gemini 1.46.0] - 2026-07-04

### Added — caw-slides に LaTeX 数式レンダを復活（ハイブリッド：matplotlib オフライン＋codecogs 任意）

SVG-first 化で外していた LaTeX 数式レンダを **拾い直した**（化学スライドに必須）。PPT Master の `latex_render.py`（オンライン provider）を参考に、**caw の方針に合わせてハイブリッド化**。

- **`scripts/render_latex.py`（新規）**：LaTeX → **透過 PNG** にレンダし SVG に data-URI 埋込。**backend 2 段**＝(1) **matplotlib mathtext オフライン既定**（ネット不要・第三者送信なし・追加依存なし。速度論 `k=A e^{-E_a/RT}`・熱力学 `ΔG=ΔH−TΔS`・量子化学 `⟨ψ|H|ψ⟩` 等を広くカバー）(2) `\ce{}` 等フル LaTeX が要る式のみ **codecogs にフォールバック**（`--online`・要ネット）。
- **セキュリティ**：codecogs は **https＋latex.codecogs.com のみ許可＋リダイレクト禁止**（SSRF/ダウングレード防止）、`color` を hex 検証（LaTeX 注入防止）、PNG 署名 8 byte 検証、フォールバックは mathtext 非対応時のみ（保存失敗等は式を送らない）。
- **TDD＋二段レビュー**：pytest 14 件（注入拒否・二重失敗・非PNG拒否・非codecogsホスト拒否・main CLI・透過確認）。Claude+Codex レビューで HIGH/MEDIUM を全対応（記録 `review/code-reviews/2026-07-04-caw-slides-render-latex.md`）。caw-slides 全 72 PASS。
- **配線**：SKILL.md Step B に数式ステップ＋同梱資産/依存（matplotlib）、design-system.md §6、plugin↔codex バイト一致ミラー、gemini GEMINI.md 節、caw-setup の matplotlib 理由に「スライドの数式レンダ」追記。
- 版 plugin 1.68→**1.69**・codex 1.67→**1.68**・copilot 1.38→**1.39**（caw-setup 更新）・gemini 1.45→**1.46**。consistency 全 OK。

## [1.68.0 / Codex 1.67.0 / Copilot 1.38.0 / Gemini 1.45.0] - 2026-07-04

### Changed — 前提ツール導入をオンボーディングで per-tool・理由説明つきに（一括承認を撤回）

ユーザー要望により、caw-setup を **「一括承認 → 順に導入」から「各ツールを個別に、なぜ必要かを説明して導入するか尋ねる」** に変更し、**オンボーディングの一部として必ず実行**するようにした。

- **caw-setup（plugin/codex/copilot）**：安全方針を per-tool 確認に変更（一括の暗黙導入・勝手なスキップをしない）。Step 2 表に **「なぜ必要か」列**を追加し 1 ツール 1 行に展開（poppler＝PDF テキスト抽出、PyMuPDF＝論文図切り抜き、python-pptx＝SVG→編集可能 pptx、Pillow＝ラスタ図埋込、numpy/pandas/scipy＝データ解析、matplotlib＝作図、lmfit/RDKit/ASE＝分野依存、cairosvg/LibreOffice＝プレビュー、gh）。Step 3 を「各ツールを個別に説明して尋ねる」に（Claude Code は AskUserQuestion の機能グループ別複数選択、他 CLI は説明つき列挙）。既存は尋ねない・選ばれたものだけ導入。
- **caw オンボーディング（plugin/codex/copilot）**：scaffold 完了後に **3-6b「前提ツールの per-tool 確認」** を新設し、caw-setup Step 2〜4 を必ず実行（「あとで /caw-setup」の後回しを廃止）。
- **gemini GEMINI.md**：caw-setup 節を per-tool・理由説明・オンボ実行に更新。
- 版 plugin 1.67→**1.68**・codex 1.66→**1.67**・copilot 1.37→**1.38**・gemini 1.44→**1.45**。consistency 全 OK。

## [1.67.0 / Codex 1.66.0 / Copilot 1.37.0 / Gemini 1.44.0] - 2026-07-04

### Changed — caw-setup の依存チェックを全スキル棚卸しで刷新（機能階層・SVG-first 対応）

caw 全体（実在15スキル）の依存を追跡し、caw-setup のツールチェックを**機能階層に再構成**。旧チェックは caw-slides SVG-first 化・caw-analyze 追加の前の内容で欠落・陳腐化していた。

- **追加**：**PyMuPDF**（caw-slides の論文図切り抜き）、**pandas / scipy**（caw-analyze/playbook のコア）、**lmfit / RDKit / ASE**（caw-analyze の fit・分子・構造＝分野依存で任意提案）、**cairosvg**（スライドのプレビュー・任意）。
- **再配置**：**matplotlib** を「スライド必須」から「解析・作図」層へ（SVG-first スライドは native SVG chart のため matplotlib 不要）。**Pillow** をスライドのラスタ図埋め込みとして明示。
- **階層化**：`import pptx, matplotlib, PIL, numpy` の一括チェックを廃し、**機能（PDF／スライド／解析）ごとに検出・提案**。使わない機能の依存は入れない（`feedback_caw_no_assumed_extra_plugin_dependency` と整合）。計算エンジン本体（Gaussian/ORCA/CP2K/GROMACS/MACE）は対象外を明記。
- plugin/codex/copilot の caw-setup SKILL.md（共通ブロックを一致更新）＋ gemini GEMINI.md の caw-setup 節を反映。版 plugin 1.66→**1.67**・codex 1.65→**1.66**・copilot 1.36→**1.37**・gemini 1.43→**1.44**。consistency 全 OK。

## [1.66.0 / Codex 1.65.0 / Copilot 1.36.0 / Gemini 1.43.0] - 2026-07-04

### Changed — caw-slides を SVG-first に全面再設計（native pptx・自己完結・PPT Master default 準拠）

スライド生成を **python-pptx レイアウト＋Codex 委譲** から **手描き SVG → native DrawingML pptx** に転換。図形・表・chart が PowerPoint で直接編集でき、デザインは **PPT Master default に高忠実**（ユーザーが理想とする lab の PPT Master プロセスに寄せた）。実物の論文紹介デッキ（Angew 2025・6枚・論文図切り抜き＋自作チャート）で忠実度と end-to-end を検証済み。

- **Phase 0 — MIT 変換器を vendor**：`skills/caw-slides/vendor/`（`svg_to_pptx` 8163＋`svg_finalize` 3227＋`config`＋`console_encoding` ＝ 12,179 行、上流 PPT Master © Hugo He, MIT・無改変）＋ `LICENSE`/`NOTICE.md`。native shape 出力を隔離 venv（python-pptx のみ）で smoke 実証。cairosvg（system Cairo）不要・画像埋込時のみ Pillow。
- **Phase 1 — `references/design-system.md`**：PPT Master default を distill＋日本語ローカライズ（role ベース配色11役＋navy 既定パレット、和文 MS Gothic/英数 Arial、添字 `baseline-shift` tspan、レイアウトパターン、SVG 制約、ゲートが拾わない2罠）。個人ブランドは載せない。
- **Phase 2 — 品質ゲート＋後処理（pytest 58）**：`scripts/assert_font_rule.py`（和文=日本語フォント・stdlib のみ）、`scripts/assert_no_overlap.py`（重なり/はみ出し・stdlib のみ）、`scripts/crop_paper_figures.py`（論文PDF図の切り抜き）、`scripts/fix_ea_font.py`（ビルド後 pptx の CJK run を ea=MS Gothic に強制・新規）。Claude+Codex 二段レビュー（HIGH4/MED3/LOW2 対応。Claude が HIGH とした ea 挿入順は一次資料+実行時で誤検出と裁定）。
- **Phase 3 — SKILL.md を SVG-first に書き直し**：author→gate→convert→fix_ea→目視→配布 の自己完結ワークフロー。**Codex 委譲を撤廃**（各 CLI 自身が完結・追加プラグイン不要）。**出力は pptx のみ**（preview PNG を配布先に置かない hard rule）。旧 python-pptx 資産（`pptx_helpers.py`/`research_icons.py`/`style-guide.md`/`codex-exec-templates.md`/`templates/generate_*.py`）を撤去。
- **Phase 4 — 配線**：`vendor/`・`scripts/`・`design-system.md` を plugin↔codex バイト一致でミラー（check-consistency の mirror_dirs に scripts・vendor 追加、削除した templates を除去）。gemini `GEMINI.md` の caw-slides 節を SVG-first に更新（変換器は同梱せず PPT Master / caw plugin の vendor を案内）。**copilot は caw-slides 非同梱ゆえ据置**。
- 版 plugin 1.65→**1.66** / codex 1.64→**1.65** / gemini 1.42→**1.43** / copilot 1.36 据置。consistency 全 OK。

## [1.65.0 / Codex 1.64.0 / Copilot 1.36.0 / Gemini 1.42.0] - 2026-07-03

### Changed — 二段レビュー（Claude＋Codex）を全スキルで「応用編・任意」に統一（追加プラグイン依存を仮定しない）

中核スキル（`caw` SKILL.md・`chemistry-departments.md`）は既に二段レビューを「応用編・慣れてから手動追加」と位置づけていたが、**枝葉のスキルが既定手順のように書いていて不整合**だった（Claude Code だけの購入者に `codex:review`＝Codex CLI ＋配線という追加依存を暗黙に要求）。この不整合を解消し、**基本線＝各 CLI 単体のセルフレビュー／二段レビューは応用編（任意・Codex CLI も併用している場合のみ）／追加プラグインは前提にしない**で統一。

- `caw-analyze`（plugin/codex）Step 5：再利用コードのレビュー案内を「その CLI 単体のセルフレビューで十分・二段は応用編」に。
- `caw-write`（plugin/codex）：英文/引用クロスチェックを「各 CLI の自己レビューが基本線・`codex:review` は Codex 併用時の任意」に（従来は Claude 版に codex:review を要求）。
- `caw-playbook`（plugin/codex）：playbook 記録カテゴリの表行・蓄積ルールを「二段レビュー使用時はその指摘も／二段は応用編・単体セルフレビューでも十分」に条件化。
- `GEMINI.md`（caw-analyze 節）：同様に「Gemini 単体の自己レビューが基本線・二段は応用編」に。
- copilot-plugin は該当スキル（caw-analyze/write/playbook）を同梱しないため変更なし＝版据置（1.36.0）。
- 版 plugin 1.64→**1.65**・codex 1.63→**1.64**・gemini 1.41→**1.42**。consistency 全 OK。

## [1.64.0 / Codex 1.63.0 / Copilot 1.36.0 / Gemini 1.41.0] - 2026-07-03

### Changed — web 種まきから「計算入力の構文が絡む種の Codex 二段クロスチェック」を撤去

1.63.0 で入れた web 種まきの規律のうち、**計算入力の構文が絡む種の Codex 二段クロスチェック**を廃止（ユーザー判断）。構文リスクへの安全弁は残すが手段を変更し、**「特にベンダー一次資料（公式マニュアル）で裏取りしてから記す」**に置き換え（`feedback_comp_input_template_primary_source` の「構文は一次資料で裁定」は維持）。

- `skills/caw/references/playbook-web-seeding.md`（plugin↔codex↔copilot バイト一致）の規律 1 項目を Codex 二段 → 一次資料裏取りに変更。
- plugin / codex / copilot の Step 3-7 から「構文が絡む種は書き込み前にクロスチェック」の起動側 1 行を削除（3-7 は起動方法のみに整理）。gemini は元々当該記述なし。
- 版 plugin 1.63→**1.64**・codex 1.62→**1.63**・copilot 1.35→**1.36**・gemini 1.40→**1.41**。consistency 全 OK。

## [1.63.0 / Codex 1.62.0 / Copilot 1.35.0 / Gemini 1.40.0] - 2026-07-03

### Added — オンボーディング後に計算ツール Playbook を web 種まき（バックグラウンド・1 ツール 1 エージェント並列）

Call 4 で名指しされた計算ツールについて、**scaffold 完了後にバックグラウンドで初期 Playbook を種まき**する仕組みを追加。空 Playbook のコールドスタート（使い始めは中身が無く価値が出ない）を、**そのユーザーの named ツールだけ・その場の web 検索**で埋める。配布物に汎用コンテンツを同梱しない（per-technique 量産の失敗を繰り返さない）ための live 生成方式。

- **走らせ方**：オンボーディングの funnel は止めず、完了メッセージ表示後に**自動・バックグラウンド**で起動。**1 ツール＝1 エージェント**、複数ツールは**並列**（並列サブエージェントが使える CLI＝並列、無い CLI＝順次にフォールバック／web 検索不可の CLI＝skip）。全完了後に 1 回だけ通知。
- **seed 先を分離**：各ツールの `office/computation/playbooks/<tool>.md` の新セクション **`## 外部リファレンス（web 由来・要検証）`** に隔離。**`## Lessons Learned`（ユーザー本人が run から得た検証済み知見・`_past-data` seeding 先）には触れない**。両者が食い違えば **Lessons が常に優先**（provenance を明確化）。
- **規律**：一次資料・公式優先（公式は単一ソース可・非公式は 2 つ以上で裏取り）、出典 URL 必須、**計算入力の構文が絡む種は Codex 二段クロスチェック**（`feedback_comp_input_template_primary_source`）、信頼できる出典が無ければ「未取得（要一次資料）」と空欄化し憶測で埋めない。中身は「意思決定に使える既定」（汎関数/基底/力場/擬ポテンシャル/cutoff/既知の罠/version 依存の文法）に絞りチュートリアル丸写しをしない。
- **住処**：オンボーディング専用ステップ（Step 3-7）。共通仕様は新 `skills/caw/references/playbook-web-seeding.md`（plugin↔codex↔copilot バイト一致・consistency で強制）に集約し、各 CLI の 3-7 は起動方法のみ規定（plugin＝Task＋`run_in_background` 並列、codex/copilot＝並列可なら並列・無ければ順次、gemini＝GEMINI.md にインライン）。後日ツールを足したときは同手順を単発で再実行できる door を残す（自動配線はしない）。
- 全 4 CLI 反映・consistency 全 OK（2a plugin↔codex／2b codex↔copilot に新リファレンスを追加）。版 plugin 1.62→**1.63**・codex 1.61→**1.62**・copilot 1.34→**1.35**・gemini 1.39→**1.40**。

## [1.62.0 / Codex 1.61.0 / Copilot 1.34.0 / Gemini 1.39.0] - 2026-07-01

### Added — カバレッジ監査の反映（役割境界の明記・横断ギャップに効く汎用資産 3 つ・caw-input のエンジン方言分離）

化学全分野の対応可否を、web 検索とオープンアクセス論文を参照する並列エージェントで監査（`docs/chemistry-coverage-audit.md`）。全 16 サブ領域で「部分対応」＝有機系＋下流解析は被覆する一方、**ベンダーバイナリ生データと専用ソフト（GUI/MATLAB）の一次還元がギャップ**と判明。**手法別スキルを増やさない**抽象フレームワーク方針を保ったまま、以下 3 点で対処。

- **① 役割境界を正直に明記**（「全分野対応」と誇張しない）：`docs/concept.md` と `docs/analysis-companion-design.md` に役割境界節を追加。caw が担うのは (a) 9 部署の組織化 (b) 下流解析＋規律 (c) 執筆/文献/playbook 蓄積。**GUI/MATLAB 専用の一次還元（SHELX 精密化・CasaXPS・EasySpin・RELION 等）はユーザーに委譲**し、caw は post-export の下流解析と妥当性検証で協働する、と明示。監査サマリを `docs/chemistry-coverage-audit.md` に集約。
- **② 横断ギャップに効く汎用資産 3 つ**（`skills/caw-analyze/references/analysis-conventions.md`、plugin↔codex バイト一致）：
  - **資産1 取込アダプタ規約** — ベンダーバイナリ（NMR FID・MS/クロマト・EPR・`.mpr`・回折フレーム 等）は OSS リーダ（msconvert/galvani/gemmi/mrcfile）か native 実装で**中立形式（CSV/mzML/ASCII/extxyz）に変換**してから解析。手法別パーサは作らず変換レシピを playbook 蓄積。
  - **資産2 外部専用 CLI orchestration 契約** — scriptable（GSAS-II scriptable・xraylarch・phreeqpython・pyglotaran・impedance.py）は caw-analyze が subprocess/Python-API で駆動し規律をラップ。GUI/MATLAB 専用は out-of-scope の外部委譲。
  - **資産3 高リスク解析の規律チェックリスト** — モデル依存工程（EIS 等価回路・TA ターゲット・EXAFS パス数・XPS 背景）は前提開示・代替モデル比較・過剰フィット検知・一意性を必ず求める。
  - caw-analyze SKILL.md に Step 3b（3 規約参照）、caw-playbook に「取込アダプタ・外部専用ソフト orchestrate 手順」の蓄積対象を追記。
- **③ caw-input の分離（幾何＋メソッド＋エンジン方言アダプタ）**：入力生成を 3 層に整理し、リスト外エンジン（Psi4/NWChem/OpenMolcas/xtb・CREST/LAMMPS/AMBER/OpenMM/AutoDock Vina/PHREEQC 等）は **per-engine テンプレ 1 枚を playbook に足すだけ**で対応（新スキルを作らない）。Q1 に「その他（Other 自由入力）」を追加。文法はベンダー一次資料で裁定（`feedback_comp_input_template_primary_source`）。
- 全 4 CLI 反映（gemini は GEMINI.md の caw-input/caw-analyze 節に要約）・consistency 全 OK（mirror_dirs に `caw-analyze/references` 追加済）。版 plugin 1.61→**1.62**・codex 1.60→**1.61**・copilot 1.33→**1.34**・gemini 1.38→**1.39**。

## [1.61.0 / Codex 1.60.0 / Copilot 1.33.0 / Gemini 1.38.0] - 2026-07-01

### Added — 標準部署に「実験部（experiment）」を追加（8 → 9 部署）

主対象が実験系化学者であることを踏まえ、湿式ラボの実験ワークフローを担う **experiment（実験部）** を標準部署に追加。8 → **9 部署**（`secretary / research / engineering / computation / experiment / analysis / writing / review / presentation`）。

- **機能的な役割**（化学サブ領域ではない）：実験の**段取り・電子ノート・試薬/サンプル在庫・安全（SDS/リスク/廃棄）・測定スケジュール**を担当。分野を問わず横断的に支える。
- **境界**：記録・整理・段取りを助けるが、**科学判断（合成ルート・条件・手法選定）はユーザー**。**具体的な測定データの定量・解析は analysis（caw-analyze）が per-data で**扱う（実験部＝湿式ラボの「家」／analysis＝結果の定量、と分担）。→ 「計算＝事前に環境化／実験＝使用時に per-data」の非対称と整合。
- `chemistry-departments.md`（plugin/codex/copilot）に experiment 部署テンプレ（`notebook/` `inventory/` `safety/`）を追加。SKILL.md の scaffold 範囲・3-3・完了ツリー・dispatch 表（「実験の記録・段取り・在庫・安全 → experiment」）、`claude-md/agents-md-template` の DEPARTMENT 対応表、`engine-validation-map`（化学専用バケットに experiment 追加）、GEMINI.md、README、concept.md をすべて 9 部署へ更新。
- 全 4 CLI 反映・consistency 全 OK。版 plugin 1.60→**1.61**・codex 1.59→**1.60**・copilot 1.32→**1.33**・gemini 1.37→**1.38**。

## [1.60.0 / Codex 1.59.0 / Copilot 1.32.0 / Gemini 1.37.0] - 2026-06-30

### Changed — 研究モードを「抽象フレームワーク」に再設計（オンボーディング funnel ＋ 解析コンパニオン）

研究モードの設計方針を転換。**手法別の具体スキルを量産する路線を撤回**し（解析はユーザー依存ゆえスキル化はナンセンス・保守過大）、**薄い土台＋汎用ツール＋ユーザーごとに育つ playbook** で広い化学領域に対応する方針へ。設計の根拠は `docs/analysis-companion-design.md`、スコープは `docs/concept.md`（同リリースで「やらないこと（YAGNI）」を撤廃＝capability 制限なし、保つのは化学者向け identity と抽象フレームワーク規律の 2 点のみ。MLIP 訓練/fine-tune も対象内に）。

- **オンボーディングを abstract→concrete の funnel に**：研究分野を **大分類 → 中分類**（適応的）と絞り、**任意の論文添付**（環境理解のためだけに浅く読む。voice/glossary 等の重い抽出はしない）で研究の輪郭を掴み、**計算ツール**（MLIP/MLFF の利用＋訓練を含む）と標準化項目（計算実行環境・文献管理・クラウド・体制・申請書・論文ステータス）を聞く。**実験手法・装置は onboarding で聞かず、解析時に per-data で尋ねる**（計算＝事前に環境化／実験＝使用時の非対称）。全設問は選択式＋自由入力。
- **`caw-analyze`（解析コンパニオン）を新設**：手法非依存の薄い“司会者”。固定パイプライン・手法別スキルを持たず、汎用ツール（pandas/numpy/scipy/matplotlib/RDKit 等）でその場の解析を組み、単位・再現性・境界検証・正直な fit 報告の規律を効かせ、再利用に値する手順を **ユーザーの playbook** に蒸留する。
- **`caw-playbook` を一般化**：計算 log の Lessons に加え、`work/analyses/_playbook/<topic>.md` に**解析レシピ**も蓄積（使うほどユーザーに特化。スターター素材は同梱しない）。
- dispatch を「データ解析・定量・fit・可視化（手法問わず）→ analysis（caw-analyze）」に更新。
- **配布**：plugin / codex-plugin / copilot-plugin の `caw`・（codex は）`caw-analyze`・`caw-playbook` SKILL.md、gemini `GEMINI.md` ＋ `commands/caw-analyze.toml` を全て funnel・新スキルに更新。consistency 全 OK。
- 版番号は archive ブランチ（撤回した per-technique 実装が 1.51〜1.59 を消費）と衝突しないよう **plugin 1.60.0 / codex 1.59.0 / copilot 1.32.0 / gemini 1.37.0** へ。

> 撤回した per-technique 実装（caw-parse/analyze/xrd/echem/kinetics/medchem/xas/db ＋ caw-input 拡張・237 テスト）は `archive/data-skills-v1` ブランチに保全（main 非マージ）。

## [1.50.0 / Codex 1.49.0 / Copilot 1.23.0 / Gemini 1.27.0] - 2026-06-20

### Changed — caw-intake が処理後に原本を種類別 `_source/` へ移動し inbox を空にする

従来、caw-intake は inbox の原本を**残す（削除しない）**仕様だったため、抽出した成果物は `work/` に行く一方で**自分の ES・論文・CV・スライドの原本は inbox に放置**されていた（外部論文→`work/papers/pdf/`、計算→`_past-data/` は移動済みなのに自分の書類だけ行き場なし）。研究モードの「論文 PDF→`work/papers/pdf/`」と同じ発想で、**全原本を種類ごとに探しやすい場所へ移動**する。

- **処理成功した原本を種類別の宛先へ `mv`**（`rm` しない＝可逆、`feedback_migration_mv_not_rm` 準拠）し **inbox を空にする**：
  - 外部論文 PDF → `work/papers/pdf/`（既存）／ ES・履歴書 → `work/documents/_source/` ／ 自分の論文・申請書・要旨 → `work/manuscripts/_source/` ／ スライド・ポスター → `work/presentations/_source/` ／ CV・業績 → `work/profile/_source/` ／ 計算入出力 → `work/<sw>/_past-data/`（既存）／ 測定 raw → `work/analyses/<topic>/_source/`
  - **判定不能・要確認のファイルは inbox に残す**（移動しない）。完了時に「N 件処理→各 `_source/` へ移動、inbox は空」と報告。
- 原本は AI 生成物の隣（`work/.../_source/`）に種類別で並ぶので、ユーザーが後から原本を探しやすい。
- 反映：`caw-intake/SKILL.md`（plugin + codex）・dispatcher `caw/SKILL.md` の inbox README（plugin + codex + copilot）・`GEMINI.md`。

### Note

- 版: plugin 1.49.1 → **1.50.0** / codex 1.48.1 → **1.49.0** / copilot 1.22.1 → **1.23.0** / gemini 1.26.0 → **1.27.0** / marketplace 同期

## [1.49.1 / Codex 1.48.1 / Copilot 1.22.1] - 2026-06-19

### Docs — テスト会の実地知見を反映（git 前提の明記・Gemini 無料枠の実態修正）

第1回テストユーザー会で判明：(1) caw の導入には **git が前提**（各 CLI の `marketplace add` が配布元 GitHub を clone する）、(2) **Gemini CLI の無料枠は caw を動かすには不十分**（API キー必須・割り当て少で初期構築すら未完）。

- **A: README に git 前提を明記**（plugin / codex / copilot）。「`marketplace add` は GitHub を clone するため git と Node.js（LTS）が事前に必要」を install 手順に追記。`web/requirements.md` は既に git を必須掲載済み。
- **B: Gemini の位置づけを実態に修正**（web）。`gemini-cli/index.md` 冒頭に caution（無料枠は caw に不十分・Codex/Claude 推奨・有料 API 前提）、「手厚い無料枠」の記述を撤回。`index.mdx`・`about.md` の Gemini 紹介も「無料枠は限定的・有料 API 前提」に。
- セミナーガイド（配布外 Desktop）も同内容で更新済み。

### Note

- 版: plugin 1.49.0 → **1.49.1** / codex 1.48.0 → **1.48.1** / copilot 1.22.0 → **1.22.1** / gemini 1.26.0 据え置き（web docs 変更はバージョン非依存）/ marketplace 同期

## [1.49.0 / Codex 1.48.0 / Copilot 1.22.0 / Gemini 1.26.0] - 2026-06-19

### Changed — 論文ライブラリを `work/papers/pdf/` と `work/papers/md/` に分離

caw-register の出力で原本 PDF と生成 md が `work/papers/` 直下に混在していたのを、**PDF は `work/papers/pdf/`、書誌付き要約 md は `work/papers/md/`** に分離。`work/papers/` を参照する全スキルへ波及するため、意味（PDF→`pdf/`／md→`md/`／投入口→`pdf/`／消費側は `md/` を読む／トラック判定など親参照は据え置き）を取り違えないよう全配布で一括整合。

- **caw-register**：PDF を `work/papers/pdf/` から読み、要約を `work/papers/md/<著者-年>.md` に生成（`pdf_local` も `pdf/` 配下を指す）。重複判定は `work/papers/md/` を照合。dir 不在時は登録時に作成。
- **消費側**：caw-research の登録済み除外（`work/papers/md/`）・caw-write の引用源（`work/papers/md/`）・caw-slides journal-club の素材（`work/papers/md/<著者-年>.md`）・caw-intake の振り分け先（`work/papers/md/`）をすべて `md/` に。
- **scaffold**：dispatcher が `work/papers/{pdf/, md/}` を作成。caw-doctor は両 dir を点検。旧 `work/papers/inbox/` の投入口は `work/papers/pdf/` に統合。
- 反映：plugin / codex / copilot / gemini の全スキル・references・README・GEMINI・commands、work/ ディレクトリ表・ツリー図。
- 併せて Gemini `caw-research.toml` の旧記述（就活で出力形式を尋ねる）を「調査レベルのみ・md+html 両方生成」に修正。

### Note

- 版: plugin 1.48.0 → **1.49.0** / codex 1.47.0 → **1.48.0** / copilot 1.21.0 → **1.22.0** / gemini 1.25.0 → **1.26.0** / marketplace 同期

## [1.48.0 / Codex 1.47.0] - 2026-06-19

### Fixed — セミナー前の全体監査で見つかったブロッカー 3 件

テストユーザー向けセミナー直前に、プラグイン全体を並列エージェントで監査（連携・セキュリティ・Python 正当性）。ブロッカー級を修正：

- **caw-slides に `trigger: /caw-slides` を追加**（plugin）— 唯一トリガー欠落していたスキル。`/caw-slides` がスラッシュコマンドとして登録されるように。
- **`plugin/TESTING.md` を install payload から除去**（リポジトリ直下へ移動）— 開発用ノートにオーナーの絶対パス `/Users/neoueda/...` が含まれ、インストールした全テストユーザーに macOS ユーザー名が露出していた。leak-scan（`check-consistency.sh`）に `/Users/neoueda` を追加して再発防止（`<name>` プレースホルダや `dr-neoueda` リポジトリ名は誤検知しない）。
- **`pptx_helpers.py` の画像パス防御**（plugin + codex）— `add_picture_fit` は不正/欠損パスで raw traceback だったのを **明快な `FileNotFoundError`** に、`add_logo_cluster` は欠損ロゴを **スキップ**するよう変更（デッキ全体のクラッシュ回避）。

監査の結論：連携（skill→skill・work/ パス・3-way トラック判定・reference 実在・engine-validation-map）は整合、ハードコード秘密・MCP 鍵の env 経由・caw-report 匿名性・shell injection は **クリア**。残りの指摘（bare `references/` 表記・helper のエッジケースガード・author 名）は非ブロッカーでセミナー後対応。

- レビュー: python-reviewer（監査で指摘）＋ Codex CLEAN。記録 `review/code-reviews/2026-06-19-caw-slides-image-guards.md`。

### Note

- 版: plugin 1.47.0 → **1.48.0** / codex 1.46.0 → **1.47.0** / copilot 1.21.0・gemini 1.25.0 据え置き / marketplace 同期

## [1.47.0 / Codex 1.46.0 / Gemini 1.25.0] - 2026-06-19

### Added — caw-interview が「実際に聞かれた質問」と「提出 ES」も質問の素材に

面接練習の質問づくりを、従来の①企業研究 md＋②自己分析に加えて、次の 2 ソースまで広げた：

- **③就活サイトの選考報告（実際に聞かれた質問）**：ワンキャリア（最優先）・就活会議・みん就・理系ナビ（技術職）等を「社名＋面接」で検索し、その企業で**実際に聞かれた質問・面接フロー・雰囲気**を**出典＋取得日つき**で想定問答・模擬面接に反映（取れなければ定番にフォールバック・捏造しない）。
- **④ユーザーが提出した ES**：`work/documents/`（caw-es 出力）または手元の提出版（`inbox/` で渡す）を読み、**ES の記述を面接官が深掘りする質問**（ガクチカの「なぜ/具体的/数字」、志望動機の裏取り、ES 内の矛盾・弱点）を生成＝本番に最も近い練習。
- 「質問づくりの 4 素材」セクションを新設し、Step A（想定問答）・Step B（模擬面接）の両方で①〜④を使うよう配線。①企業研究 md は従来どおり必須参照を維持。
- 反映：`caw-interview/SKILL.md`（plugin + codex）・`GEMINI.md`。

### Note

- 版: plugin 1.46.0 → **1.47.0** / codex 1.45.0 → **1.46.0** / gemini 1.24.0 → **1.25.0** / copilot 1.21.0 据え置き（caw-interview 非収載）/ marketplace 同期

## [1.46.0 / Codex 1.45.0 / Gemini 1.24.0] - 2026-06-19

### Fixed — caw-slides の図スライドに「図の読み方」支持本文を必ず添える

論文紹介（journal club）スライドで、図表を載せたスライドが**図＋key-message 一行＋出典のみで本文が無く**、情報が伝わりにくいというユーザー報告。原因は journal-club テンプレの `build_figure_slide` が支持本文の引数を持たず、図を全幅で置くだけだったこと（style-guide §3「図＋L1＋支持本文の3要素」に反していた）。

- **`generate_journal_club.py` の `build_figure_slide` を改修**：図を左（max_width 7.7in）、**「▸ 図の読み方」支持カードを右**（軸・色・凡例／主要数値／1 行解釈）に配置。`support: list[str]` 引数を追加（2〜4 点、必須運用）。`assert_no_overlap` 検証済み。
- **style-guide §3 と SKILL.md（journal-club 行）を強化**：原論文の図を貼るスライドも例外でなく支持本文必須を明記。GEMINI の caw-slides にも「『テキスト最小』は空疎化ではない・図スライドにも読み方本文を添える」を追記。
- レビュー: python-reviewer APPROVE（型注釈 2 件修正）＋ Codex CLEAN。記録 `review/code-reviews/2026-06-19-caw-slides-journal-club-figure-slide.md`。
- 反映：`caw-slides`（plugin + codex、テンプレ・style-guide byte-identical）・`GEMINI.md`。

### Note

- 版: plugin 1.45.0 → **1.46.0** / codex 1.44.0 → **1.45.0** / gemini 1.23.0 → **1.24.0** / copilot 1.21.0 据え置き（caw-slides 非収載）/ marketplace 同期

## [1.45.0 / Codex 1.44.0 / Copilot 1.21.0 / Gemini 1.23.0] - 2026-06-19

### Removed — オンボーディングの `はじめにお読みください.md`（START HERE 文書）生成を廃止

caw の初期環境構築でプロジェクトルートに生成していた `はじめにお読みください.md`（START HERE 文書）を**生成しないように変更**。オンボーディング後の「何をしますか？」の最初の一声と完了メッセージは従来どおり残る（ファイルを作らないだけ）。

- **生成の削除**：研究 scaffold（`caw/SKILL.md` §3-6）・就活 scaffold（`job-hunting-departments.md` §D）の START HERE 文書生成ステップを削除。GEMINI のオンボーディング手順からも削除。
- **参照の整理（孤立検出を防ぐ）**：`caw-doctor`（存在チェック）・`caw-report`（有無の報告フィールド）・`engine-validation-map`・README のディレクトリ図・`commands/caw-doctor.toml` から START HERE 文書への参照を除去。就活フローの節番号を整理（§D2→§D）。
- 反映：plugin / codex / copilot / gemini の全 4 配布。

### Note

- 版: plugin 1.44.0 → **1.45.0** / codex 1.43.0 → **1.44.0** / copilot 1.20.0 → **1.21.0** / gemini 1.22.0 → **1.23.0** / marketplace 同期

## [1.44.0 / Codex 1.43.0 / Gemini 1.22.0] - 2026-06-19

### Changed — caw-events を「named 就活ソース＋予測 floor」で底上げ（CLI 差を縮小）

同じ指示でも Codex は出典 2 ドメイン・予測 3 件・「要確認」9 件と弱く、Claude（出典 6 ドメイン〔ワンキャリア/就活会議/理系ナビ/日経/マイナビ〕・予測 23 件・要確認 2 件）に見劣りした。本スキルの主価値＝**有用ソースを明示しながら今年度を予測する**ことなので、ソース利用と予測量を規定して底上げ。

- **Step 2（情報源）を named チェックリスト化**：ワンキャリア（最優先）・就活会議・マイナビ/リクナビ・**理系ナビ/LabBase（技術・研究職はほぼ必須）**・みん就/OpenWork を URL つきで列挙し、**最低 3 つの独立就活ソースを実際に検索**するよう必須化。「公式に無い＝要確認」で済ませない。
- **Step 4（予測）に floor を追加**：**主要イベント種別（サマー/秋冬インターン・本選考説明会・座談会・ES 締切・早期選考）ごとに今年度予測を必ず 1 件ずつ**、過去の実日付を就活サイト出典つきで併記。**「要確認」は過去実績すら無いときだけ**（安易に逃げない）。
- 自由度は維持（種別・ソースはデータに応じて追加可）。反映：`caw-events/SKILL.md`（plugin + codex）・`GEMINI.md`。

### Note

- 版: plugin 1.43.0 → **1.44.0** / codex 1.42.0 → **1.43.0** / gemini 1.21.0 → **1.22.0** / copilot 1.20.0 据え置き（caw-events 非収載）/ marketplace 同期

## [1.43.0 / Codex 1.42.0 / Gemini 1.21.0] - 2026-06-19

### Changed — 就活 caw-research の企業 HTML を「可視化レシピ」で底上げ（CLI 差を縮小）

同じ指示でも Claude Code は横棒チャートを多用するのに Codex は表中心になり、Codex 出力の情報量・見栄えが劣っていた（実例: Claude 版 SVG 11 個／出典 19 件 vs Codex 版 SVG 1 個／出典 10 件。CSS トークンは同一）。原因は「どの数値を図表化するか」が指示で未規定でモデル任せだったこと。**最低限の図表セットを規定しつつ自由度を残す**形で底上げ。

- **`html-style.md` に横棒チャートの定番スニペットを追加**（ラベル→グレートラック→値バー→数値の 4 要素、`width=280×値/最大`、主役=#aa2d00・比較=#888888）。全 CLI・全スキルで再利用。
- **caw-research（就活）の企業プロファイルをブロック別レシピ化**：B 財務（セグメント売上・利益）と D 業界（世界シェア）は**横棒チャートで必ず可視化**、ヘッダに証券コード/代表者/創業/本社/志望度/出典方針、選考フローは横並びステップ、各ブロックに出典＋取得日。**「上記は最低限。データがあれば図表を増やしてよい」と自由度を明記**。
- 反映：`html-style.md`（plugin + codex）・`caw-research/SKILL.md`（plugin + codex）・`GEMINI.md`。

### Note

- 版: plugin 1.42.0 → **1.43.0** / codex 1.41.0 → **1.42.0** / gemini 1.20.0 → **1.21.0** / copilot 1.20.0 据え置き（caw-research 非収載）/ marketplace 同期

## [1.42.0 / Codex 1.41.0 / Gemini 1.20.0] - 2026-06-19

### Changed — 就活 caw-research は md+html を常に両方生成・尋ねるのは調査レベルだけに

就活の企業研究結果は**人間（閲覧）と AI（caw-es/caw-interview が ES・面接準備で読む）の両方**が使うため、出力形式を選ばせる仕様をやめ、**md と html を必ず両方生成**するよう変更。

- **md ＝ 機械可読の正本**（caw-es / caw-interview が読む）、**html ＝ 閲覧用ビュー**（同じ内容を `references/html-style.md` のデザインで整形）。AI は html を読まないため下流の読み込みコストは増えず、追加コストは生成時の 2 形式目の整形（1 社あたり数 K トークン）のみ。
- **ユーザーに尋ねるのは調査レベル（L1/L2/L3）だけ**。出力形式の確認質問とグラフ方式の確認質問（旧 Step V0）を削除。グラフは**オフライン自己完結 SVG に固定**（Chart.js/CDN は使わない）。
- 反映：`caw-research/SKILL.md`（plugin + codex）・`GEMINI.md`。テストユーザーガイド（Desktop）も「深さを選ぶと md+html を自動生成」に更新。

### Note

- 版: plugin 1.41.0 → **1.42.0** / codex 1.40.0 → **1.41.0** / gemini 1.19.0 → **1.20.0** / copilot 1.20.0 据え置き（caw-research 非収載）/ marketplace 同期

## [1.41.0 / Codex 1.40.0 / Copilot 1.20.0 / Gemini 1.19.0] - 2026-06-19

### Changed — 研究/就活トラックの判定を対称マーカー化＋取り違え防止を全スキルで強化

トラック判定が「`> トラック: 就活` があれば就活／**無ければ研究**」という**不在ベースの非対称**で、就活 office からマーカーが欠けると黙って研究側へ倒れる弱点があった。**研究側にも明示マーカー `> トラック: 研究` を付け、判定を 3 分岐に統一**。

- **研究 scaffold が `> トラック: 研究` を冒頭出力**：`claude-md-template.md`（plugin）・`agents-md-template.md`（codex + copilot、byte-identical）に追加。Gemini は既に出力済み。就活 `> トラック: 就活` と対称に。
- **3 分岐リーダー**（`caw-research`・`caw-doctor`・`caw-intake`・`caw-report`、plugin + codex + GEMINI）：`就活`→就活／`研究`→研究／**行が無い旧 office → `work/companies/` か `work/papers/`・`work/topics/` の有無で推定、判別不能なら 1 問尋ねる**。黙って研究へ倒れる挙動を廃止。
- **caw-doctor がマーカーを自己修復**：旧 office で `> トラック:` 行が欠けていれば、推定したトラックの行を冒頭に補記して移行。
- **単一トラックスキルに取り違えガード**：就活専用（`caw-es`/`caw-events`/`caw-interview`）・研究専用（`caw-register`/`caw-write`）は、反対トラックの office で起動されたら「これは○○向けです」と伝えて適切なスキルへ誘導し、無理に進めない。

### Note

- 版: plugin 1.40.0 → **1.41.0** / codex 1.39.0 → **1.40.0** / copilot 1.19.0 → **1.20.0** / gemini 1.18.0 → **1.19.0** / marketplace 同期

## [1.40.0 / Codex 1.39.0 / Copilot 1.19.0 / Gemini 1.18.0] - 2026-06-19

### Changed — 研究オンボーディングで計算ソフトを「カテゴリ」だけでなく「具体ソフト名」まで尋ねる

Q2（計算ソフト）が**カテゴリ**（量子化学・古典 MD・周期系 DFT・構造可視化）までしか聞かず、例えば古典 MD を選んでも **GROMACS / AMBER / NAMD / LAMMPS / OpenMM のどれか**を尋ねていなかった。**カテゴリ選択の直後に具体ソフト名を必ず追加で尋ねる**よう修正。

- **Q2-詳（具体ソフト）を追加**：選んだカテゴリごとに「具体的にどのソフトを使っていますか？」を `AskUserQuestion` で尋ねる（複数カテゴリは 1 回の呼び出しで最大 4 問、各 multiSelect、選択肢 4 超は代表 4＋Other で残りを拾う）。候補＝量子化学（Gaussian/ORCA/Psi4）・古典 MD（GROMACS/AMBER/NAMD/LAMMPS/OpenMM）・周期系 DFT（CP2K/VASP/Quantum ESPRESSO）・可視化（ChimeraX、PyMOL/VMD は Other）。
- **ディレクトリ・Playbook は名指しされたソフトのみ作成**（カテゴリ内の全ソフトを作らない）。`work/` の作業ディレクトリ表に **AMBER・NAMD・LAMMPS・OpenMM・Psi4** を追加（主な入出力拡張子つき）＋**表に無いソフトは `work/<slug>/` を汎用生成**。
- **Playbook starter が無いソフト**（amber/namd/lammps/openmm/psi4 等）は最小 Playbook（frontmatter＋空の `## Lessons Learned`）を作り、以後 caw-playbook が追記。
- 反映：`caw/SKILL.md`（plugin + codex + copilot）・`GEMINI.md`。

### Note

- 版: plugin 1.39.0 → **1.40.0** / codex 1.38.0 → **1.39.0** / copilot 1.18.0 → **1.19.0** / gemini 1.17.0 → **1.18.0** / marketplace 同期

## [1.39.0 / Codex 1.38.0 / Gemini 1.17.0] - 2026-06-19

### Changed — 出力 HTML のデザインを 3 CLI で統一（Claude Code のデザインに揃える）

caw が出力する HTML（文献リスト・企業プロファイル・イベントカタログ）のデザインが **Claude Code / Codex / Gemini で異なる**問題を解消。原因は「HTML デザインがスキルの指示文依存で、配布ごとに精度がバラバラ」だったこと（特に **GEMINI.md は CSS が 0** で Gemini が毎回自己流生成、**caw-events は「caw-research の規約を踏襲」と曖昧参照**でドリフト）。caw-slides を `pptx_helpers.py` でコード化して統一したのと同じ発想を HTML にも適用。

- **共有 HTML デザイン契約 `skills/caw/references/html-style.md` を新設**（plugin + codex、byte-identical）。Claude Code の現行デザインを正典化：`:root{--ink:#181d26;--body:#333840;--accent:#aa2d00;…}`＋部品（`ol.list`/`.card`/`table`/`.badge`/オフライン SVG）＋スケルトン。**白基調・コーラルアクセント・ヘアライン罫線・影/色面/アイコンなし**。
- **caw-research（研究＝文献リスト／就活＝企業）** と **caw-events** の HTML 生成手順を、この契約に**必ず従う**よう明示（自己流 CSS 禁止）。caw-events は「踏襲」→ 契約への明示参照に変更。
- **GEMINI.md に同一の `<style>` をインライン追加**（Gemini は references を読まないため）。caw-research/caw-events の出力指示から参照。← Gemini の乖離の主因を解消。
- **consistency check** に `html-style.md` の plugin↔codex byte-identity ガードを追加。

### Note

- 版: plugin 1.38.0 → **1.39.0** / codex 1.37.0 → **1.38.0** / gemini 1.16.0 → **1.17.0** / copilot 1.18.0 据え置き（HTML 出力スキル非収載）/ marketplace 同期

## [1.38.0 / Codex 1.37.0 / Gemini 1.16.0] - 2026-06-19

### Added — caw-research（就活）L3 で公式開示文書を能動的に読みにいく

「○○社の企業研究をして」に対し、**ユーザーが PDF を手で渡さなくても、L3（ディープ）では秘書が IR から公式開示文書を自分で取得して読む**よう設計を明示。L1/L2 は Web ページ中心で従来どおり（速さ優先）。

- **対象文書**（Step 2 に表で明記）：有価証券報告書・決算短信/四半期決算短信・決算説明会資料・統合報告書/中期経営計画・サステナビリティ/ESG・人的資本レポート・コーポレートガバナンス報告書・新卒採用サイト・プレスリリース。各「探す場所」「読む箇所（抜粋）」つき。
- **取得・読解手順**：web 検索で IR/PDF URL を特定 → `curl` で DL → `pdftotext -layout` で**必要セクションだけ抽出**（有報全文は丸読みせずトークン節約）。**Gemini CLI は PDF 直読み可**。値は〔文書名＋PDF URL＋取得日〕を出典に。取れないとき（Codex のネット制限等）はユーザーへ URL/PDF の貼り付け依頼、**捏造しない**。
- **L3 のみ**に限定（Step 1・Step 3 の L3 説明にも明記）。反映：`caw-research/SKILL.md`（plugin + codex）・`GEMINI.md`・`commands/caw-research.toml`。

### Note

- 版: plugin 1.37.0 → **1.38.0** / codex 1.36.0 → **1.37.0** / gemini 1.15.0 → **1.16.0** / copilot 1.18.0 据え置き（caw-research 未収載）/ marketplace 同期

## [1.37.0 / Codex 1.36.0 / Copilot 1.18.0 / Gemini 1.15.0] - 2026-06-18

### Added — 研究モードの対応計算ソフトに ChimeraX を追加

UCSF ChimeraX（構造可視化・**密度マップへのタンパク質フィッティング**・解析）を caw 研究モードの対応計算ソフトに追加。既存 6 ソフト（Gaussian/ORCA/CP2K/GROMACS/VASP/Quantum ESPRESSO）と同じ扱いで全配布に配線。

- **オンボ Q2** に新カテゴリ「構造可視化・密度マップフィッティング（ChimeraX 等）」、**work/ scaffold** に `work/chimerax/`（`.cxc`/`.py` スクリプト・PDB/mmCIF 構造・`.mrc`/`.map`/`.ccp4` 密度マップ・`.cxs` セッション・フィット結果/レンダ画像）、**秘書ディスパッチ**に ChimeraX。
- **caw-input**：ChimeraX 用途（`fitmap`/Fit in Map・`molmap`・`measure correlation`・`matchmaker`・`morph`・ISOLDE 連携）と生成物（`.cxc` コマンドスクリプト＋ヘッドレス実行 `chimerax --nogui --script x.cxc --exit`／サーバは `--offscreen`）を追加。
- **caw-playbook**：ChimeraX log 解析パターン（fitmap correlation/overlap・ISOLDE clashes/rotamer・OSMesa）を追加。
- **playbook 雛形**に `chimerax.md` スターター（fitmap/molmap/ヘッドレス）、**chemistry-departments** の対応ソフト表、**GEMINI.md**・`commands/caw-input.toml`、各 README・web docs（6→7 ソフト）。
- Web から ChimeraX の用途・ファイル形式（.cxc/.cxs/.mrc）・ヘッドレス実行（`--nogui`/`--offscreen`/`--script`）・fitmap を調査して反映。

### Note

- 版: plugin 1.36.4 → **1.37.0** / codex 1.35.4 → **1.36.0** / copilot 1.17.1 → **1.18.0** / gemini 1.14.0 → **1.15.0** / marketplace 同期（全配布で対応ソフト追加）

## [1.36.4 / Codex 1.35.4] - 2026-06-18

### Changed — 小見出しバーを文字数に自動フィット＋淡色化

`add_subheading_bar` の塗りが短い見出しテキストに対して長すぎた（全幅）問題を修正。`width` を省略すると**文字数からバー幅を自動見積もり**（全角≈1em/半角≈0.6em＋余白）して**塗りが文字に密着**するように。固定幅にしたいときは従来どおり `width` を渡す。塗り色も `#A9D0E0`→**`#DCECF2`（より薄いティール）**に。`font_size` 引数を追加。

- PR ループ（python-reviewer：CRITICAL/HIGH=0、MEDIUM2件〔clearance→padding 0.48in・font_size 単位コメント〕修正／Codex：ASCII 幅見積もりの限界を MEDIUM 記録・短い JA 主体ラベルでは実用上問題なし）。
- 版: plugin 1.36.3 → **1.36.4** / codex 1.35.3 → **1.35.4** / marketplace 同期。

## [1.36.3 / Codex 1.35.3] - 2026-06-18

### Fixed — タイトルバー・小見出しバーの残存テーマ影を除去

1.36.2 で影を全体オフにしたが、`add_slide_chrome`（タイトルバー）と `add_subheading_bar`（小見出しバー）の塗りシェイプは `_set_shape_shadow` を呼んでおらず PowerPoint テーマ既定の drop-shadow を継承していた（ユーザー報告「タイトル/サブタイトルに影が残る」）。両者の `_style_shape_fill` 直後に `_set_shape_shadow(bar, False)` を追加してフラット化。

- PR ループ（python-reviewer CLEAN／Codex CLEAN）。デモ再生成で title bar×4・subheading bar×4 すべて空 effectLst・deck の drop-shadow=0 を確認。
- 版: plugin 1.36.2 → **1.36.3** / codex 1.35.2 → **1.35.3** / marketplace 同期。

## [1.36.2 / Codex 1.35.2] - 2026-06-18

### Changed — drop-shadow をスライド全体で不使用（フラット）に

ユーザー要望「影はスライド全体で使わない」に対応。`_set_shape_shadow` を**常にフラット**化（テーマ既定の影も空 `<a:effectLst/>` で必ず無効化、影注入ブランチを削除）。`add_key_message_band` の shadow 既定 True→False（無視）、`add_pill`/`add_key_message_band` の docstring を修正。`style-guide.md` の §12 原則2・§14-1・§14-2（L1 を shadow ✗・全 tier フラット）・§14-6 を更新。L1 は影でなく **塗り＋角丸＋24pt Bold** で差を付ける。

- PR ループ（python-reviewer CLEAN〔add_pill docstring の MEDIUM 修正〕／Codex CLEAN）。デモ再生成で 33 shapes 中 drop-shadow=0 を確認。
- 版: plugin 1.36.1 → **1.36.2** / codex 1.35.1 → **1.35.2** / marketplace 同期（gemini・copilot 据え置き）

## [1.36.1 / Codex 1.35.1] - 2026-06-18

### Changed — key-message band（L1）を角丸・黒枠なしに

スライド下部のキーメッセージ帯（一番伝えたい 1 行）の見た目をユーザー要望に合わせて調整。`add_key_message_band` を **黒い外枠なし＋角丸（rounded rectangle）** に変更（`border` 既定 `RGBColor(0x22,0x22,0x22)`→`None`、shape `RECTANGLE`→`ROUNDED_RECTANGLE`）。塗り（淡ティール）＋shadow だけで浮かせる。`style-guide.md` §14-1/§14-2 も「角丸・黒枠なし」に更新。

- PR ループ（python-reviewer = CLEAN／Codex）。記録 `review/code-reviews/2026-06-18-caw-slides-pptx-helpers.md`。
- 版: plugin 1.36.0 → **1.36.1** / codex 1.35.0 → **1.35.1** / marketplace 同期（gemini・copilot 据え置き）

## [1.36.0 / Codex 1.35.0] - 2026-06-18

### Changed — caw-slides の視覚アイデンティティ刷新（参考デザイン採用）

X で見かけたスライドデザイン仕様（ティール base ＋ テラコッタ/グリーン、Noto Sans JP / Segoe UI）を参考に、`style-guide.md` の規則と `pptx_helpers.py` の実装を更新。構造ルール（図表優先・assert_no_overlap・3-tier 強調）は不変で、視覚レイヤーのみ刷新。

- **フォント**: 和文 **Noto Sans JP** / 英数字 **Segoe UI**（未導入環境は MS Gothic / Arial に自動フォールバック。matplotlib は `JP_FONT_PATH` が Noto→MS Gothic でファイル探索、`CAW_SLIDES_JPFONT` で上書き可）。
- **カラーパレット**: ベース teal `#3686A6` ＋モノクロ階調 ＋ アクセント **terracotta `#BA5936` / green `#459B2D`**。役割＝構造はティール、強調はテラコッタ/グリーン。純赤 `#FF0000` をテラコッタに置換。`pptx_helpers` の色定数は名前を据え置き revalue（テンプレ後方互換）、`CATEGORICAL_HEX`・energy diagram・timeline も新パレットに。
- **要素追加**: ①塗りタイトルバー（暗ティール＋白文字＝スライドマスター相当）②ページ番号 **`N / total`**（`add_slide_chrome(..., total=N)`）③多パネル用 **`add_subheading_bar`**（淡ティール小見出し）④図中テキスト**太字**（`configure_matplotlib_japanese` が bold rcParams 既定）。
- 反映：`caw-slides/references/style-guide.md`（§1 フォント・§3 パレット・§14-1 chrome）＋ `pptx_helpers.py`（plugin + codex byte-identical）。
- **PR ループ**: python-reviewer（HIGH×3 = phantom-shape/dead-const/誤誘導コメント → 修正）＋ Codex（CRITICAL/HIGH=0、LOW chemistry hex → 修正）。記録 `review/code-reviews/2026-06-18-caw-slides-pptx-helpers.md`。

### Note

- 版: plugin 1.35.0 → **1.36.0** / codex 1.34.0 → **1.35.0** / gemini 1.14.0 据え置き・copilot 1.17.1 据え置き（caw-slides assets 非収載）/ marketplace 同期

## [1.35.0 / Codex 1.34.0 / Gemini 1.14.0] - 2026-06-18

### Changed — caw-events の出力を HTML 既定（出典クリックリンク付き）に

caw-events の標準成果物を **md → HTML** に変更（caw-research と同方針）。理由＝**出典にワンクリックで飛べる**ようにするため。

- **HTML を既定で生成**：`work/recruit/<企業slug>_<YYYYMMDD>.html`（日付つきで再実行ごとに履歴が残る）。AskUserQuestion でのビュー選択は廃止し、3 ビュー（カタログ / 年間スケジュール・予測カレンダー / 過去×今年度対照表）を 1 ファイルに同梱。
- **すべてのイベント・過去実績・予測に出典 URL のクリック可能なリンク（`<a target="_blank">`）＋取得日**を付与。URL の無い項目は「要確認」と明示（リンクは捏造しない）。確定/募集中/予測/要確認をバッジ区別。
- **md は任意**（「md も」と言われたときのみ `<企業slug>_<YYYYMMDD>.md` も生成）。
- 反映：`caw-events/SKILL.md`（plugin + codex）の frontmatter・Step 5（旧 md カタログ＋AskUserQuestion HTML を HTML 既定に統合）・横断モード・注意事項／`GEMINI.md`・`commands/caw-events.toml`／`job-hunting-departments.md`（plugin/codex/copilot）の `work/recruit/` 行。

### Note

- 版: plugin 1.34.0 → **1.35.0** / codex 1.33.0 → **1.34.0** / gemini 1.13.0 → **1.14.0** / copilot 1.17.1 据え置き / marketplace 同期

## [1.34.0 / Codex 1.33.0 / Gemini 1.13.0] - 2026-06-18

### Changed — スキル間連携の配線（caw-slides ← 自分の論文 / caw-report の追跡補完）

スキル連携の監査で見つかった 2 点。研究パイプライン「探す→登録→書く→発表」の後半 2 辺を補強。

- **B. caw-slides が自分の論文を元データに使えるよう配線**：従来 caw-slides は元データ path をユーザーに毎回要求し、journal club（他者論文＝caw-register の `work/papers/`）だけが配線済みだった。**学会発表/修論/研究紹介/報告会では `work/manuscripts/`（caw-write で書いた自分の論文・要旨）・`work/profile/key-findings.md`・解析結果を元データ候補として提示・利用**するよう Step A に明記。関連 Skill にも `caw-write` を追加（**書く→発表の連携**が成立）。
- **A. caw-report の追跡補完**：直前の PR で追加した `work/interview-prep/_notes.md`（面接の傾向ノート）を caw-report が追跡していなかったため、利用状況テーブルに `work/interview-prep/` 行を、personalization ファイル一覧に `interview-prep/_notes.md` を追加。
- 反映：`caw-slides`（plugin の Claude 委譲版 + codex の直接生成版、それぞれの構造に合わせて）・`caw-report`（plugin + codex）・`GEMINI.md`・`commands/caw-slides.toml`。

### Note

- 版: plugin 1.33.0 → **1.34.0** / codex 1.32.0 → **1.33.0** / gemini 1.12.0 → **1.13.0** / copilot 1.17.1 据え置き / marketplace 同期

## [1.33.0 / Codex 1.32.0 / Gemini 1.12.0] - 2026-06-18

### Added — caw-interview に面接の学習ループ（傾向ノート）

全スキル監査で見つかった改善点を反映。`caw-interview` は振り返り（Step D）が**その企業限り**で、セッションを跨ぐ学習蓄積が無く、engine-validation-map の「反復→ログ蓄積→再利用」ペア（caw-playbook の相方）として片肺だった。**caw-write/caw-es で導入した学習ループの面接版**を追加。

- **新ファイル `work/interview-prep/_notes.md`（面接の傾向ノート）**：模擬面接・振り返りから繰り返し見える傾向（繰り返す弱点・よく聞かれる質問・効いた言い回し）を蓄積。
- **適用（Step A）**：想定問答づくりの前に `_notes.md` を読み、既知の弱点を踏まえて準備。
- **記録（Step B/D・confirm-first）**：汎用的な傾向だけを「次回以降の準備にも反映しますか？」と**自分から確認**して 1 行追記（その場限りの指摘は記録しない）。**Claude Code / Codex CLI / Gemini CLI で共通**。
- 使うほど面接準備が自分に最適化される（caw-playbook の Lessons Learned、caw-write/caw-es の writing-preferences と同じ思想）。

### Fixed — スキル一覧ドキュメントの取りこぼし（caw-write 追加・学習ループの反映漏れ）

- **caw-report**：利用痕跡のスキル一覧に **caw-write** を追加、成果物一覧に **writing-preferences** を追加、利用状況テーブルに `work/recruit/`・`work/topics/` 行を追加（動作レポートが新スキル・新成果物を正しく反映）。
- **caw-intake**：出力の読み手の総称「論文執筆」を **caw-write** と明記（他スキル同様に名前で参照）。
- `engine-validation-map`：反復→ログ行を caw-interview の `_notes.md` 横断蓄積つきに更新（plugin/codex/copilot byte-identical）。

### Note

- 版: plugin 1.32.0 → **1.33.0** / codex 1.31.0 → **1.32.0** / gemini 1.11.0 → **1.12.0** / copilot 1.17.1 据え置き（対象スキル未収載・engine-map 参照のみ）/ marketplace 同期

## [1.32.0 / Codex 1.31.0 / Gemini 1.11.0] - 2026-06-18

### Changed — caw-events を「1 社深掘り＋今年度予測」に再設計（就活）

業界横断の一括収集が既定だった caw-events を、**既定で 1 社を深掘り**する設計に変更。複数社・業界横断は**ユーザーが明示指示したときだけ**の「横断モード」に降格。さらに**過去実績から今年度の開催を予測**する機能を新設。

- **既定＝1 社深掘り**：対象企業 1 社の就活イベント（インターン・説明会・座談会・選考）と締切を詳細収集。出力は `work/recruit/<企業>.md`＋HTML。
- **就活サイトを積極併用**：公式採用ページを最優先（一次情報）に保ちつつ、**マイナビ/リクナビ/ワンキャリア/外資就活/unistyle 等を積極的に併用**して今年度・過去の情報を拾う。食い違いは公式優先＋出典明記。
- **今年度予測（新 Step 4）**：過去 2〜3 年の開催実績（時期・種別・締切・コース）からパターンを抽出し、未発表イベントを**「予測（昨年実績ベース）」**として根拠の実日付つきで提示（確定情報と峻別・捏造しない）。例「昨年 6/26 締切 → 今年度は未発表だが 6 月下旬締切と予測」。
- **HTML 3 ビューを 1 社中心に**：① イベントカタログ（確定/募集中/予測をバッジ区別）／② 年間スケジュール・予測カレンダー（確定=実線、予測=点線/淡色で重ね）／③ 過去×今年度 対照表。横断モード時は ③ を企業×イベント比較表に切替。
- **横断モード**：明示指示時のみ。`work/recruit/<業界>.md`（1 社=1 セクション）＋企業比較表、カバレッジ（N/M 社）必須。
- 反映：`caw-events/SKILL.md`（plugin + codex）全面改訂／`GEMINI.md`・`commands/caw-events.toml`／`job-hunting-departments.md`（plugin/codex/copilot）／`caw-research` の相互参照。

### Note

- 版: plugin 1.31.1 → **1.32.0** / codex 1.30.1 → **1.31.0** / gemini 1.10.1 → **1.11.0** / copilot 1.17.1 据え置き（caw-events 未収載・job-hunting-departments 参照のみ更新）/ marketplace 同期

## [1.31.1 / Codex 1.30.1 / Gemini 1.10.1] - 2026-06-18

### Changed — 好み学習の確認を「毎回・自分から」に強化（全 CLI 共通）

1.31.0 の好み学習ループは「汎用的だと判断したら確認」という条件付き・任意トーンで、エージェントが聞き逃す余地があった。ユーザー要望（推敲のたびに自動でルール化を確認してほしい・CLI 不問）に合わせ、**プロンプト指示を「推敲で修正を受けるたびに必ず評価し、汎用的なら言われる前に自分から確認」へ強化**。

- `caw-write` / `caw-es` の Step 6 を「**毎回・自分から確認**」に改訂（**Claude Code / Codex CLI / Gemini CLI で共通**の挙動と明記）。注意事項にも「『覚えて』と言われるのを待たない」を追加。
- `GEMINI.md`・`commands/caw-write.toml`・`commands/caw-es.toml` の捕捉文も「推敲のたびに評価→自分から確認」に統一。
- hook ではなくプロンプト指示で統一する設計（Gemini に hook が無く、Claude だけ hook を足すと CLI 間で挙動が割れるため、全 CLI で同一に効くプロンプトで揃える）。`一度きりの言い回し直しは記録しない`（聞きすぎない）は維持。

### Note

- 版: plugin 1.31.0 → **1.31.1** / codex 1.30.0 → **1.30.1** / gemini 1.10.0 → **1.10.1** / copilot 1.17.1 据え置き / marketplace 同期。挙動の信頼性強化のみ（新ファイル・新パスの追加なし）。

## [1.31.0 / Codex 1.30.0 / Gemini 1.10.0] - 2026-06-18

### Added — 作文の好み学習ループ（`caw-write` / `caw-es` が推敲から学ぶ）

推敲での修正が「その文書限り」で終わり次の作文に持ち越されなかった問題に対し、計算側の **caw-input ↔ caw-playbook 学習ループの作文版**を `caw-write`（研究）と `caw-es`（就活）に対称に追加。使うほどユーザーの作文の好みに最適化される。

- **新ファイル**：`work/manuscripts/_style/writing-preferences.md`（caw-write）／`work/documents/writing-preferences.md`（caw-es）。`caw-intake` の初期文体（過去文書からの一括抽出）に対し、**会話中の推敲からの逐次学習**を蓄積。
- **適用（Step 2）**：作文前に preferences を読み、文体プロファイルの上に重ねて**先回り適用**（同じ直しを繰り返させない）。
- **記録（Step 6・確認してから記録）**：修正が**汎用的な好み**（態・語調・hedging・構成・避ける語など）のときだけ、「次回以降も既定にしますか？」と**確認のうえ** 1 行ルールで追記。**その文書固有の言い回し直しは記録しない**（誤ルールは全作文を劣化させるため confirm-first）。
- 役割分担：`caw-intake`＝初期文体（バッチ抽出）／本ループ＝逐次学習（オンライン）。`office/` 設定ファイルは書き換えない（設定と好みを分離）。
- 反映：`caw-write` / `caw-es` SKILL.md（plugin + codex）・`GEMINI.md`・`commands/caw-write.toml`・`commands/caw-es.toml`・`engine-validation-map`（生成→制約チェックの行に好み学習サブループを明記、plugin/codex/copilot byte-identical）。

### Note

- 版: plugin 1.30.1 → **1.31.0** / codex 1.29.0 → **1.30.0** / gemini 1.9.1 → **1.10.0** / copilot 1.17.1 据え置き（caw-write/caw-es は未収載・engine-map 参照のみ更新）/ marketplace 同期

## [1.30.1 / Gemini 1.9.1 / Copilot 1.17.1] - 2026-06-18

### Fixed — README のスキル一覧に `caw-write` を反映

`caw-write`（1.29.0 で追加）が web `plugin.md` には反映済みだったが各 README に未反映だったため補完（スキル一覧のドキュメント整合）。

- `plugin/README.md`：`### Skills` に `/caw-write` を追加、ディレクトリツリーに `caw-write/SKILL.md`、コア説明の「5 Skills」→「9 Skills」、見出しの版「v1.5.2」→「v1.30.0」。
- `gemini-plugin/README.md`：研究の振り分け行を **文献検索（caw-research）→ 登録（caw-register）→ 執筆（caw-write）** の 3 段に補強。
- `copilot-plugin/README.md`：未収載（フルポート予定）一覧に `caw-write` を追加、「残りの 5 スキル」→「6 スキル」。
- セミナー HTML（Desktop・リポジトリ外）のスキル節は既に最新のため変更なし。

### Note

- 版: plugin 1.30.0 → **1.30.1** / gemini 1.9.0 → **1.9.1** / copilot 1.17.0 → **1.17.1**（各 README 更新）/ codex 1.29.0 据え置き（codex README はスキル列挙なし）/ marketplace 同期。ドキュメントのみ・スキル挙動の変更なし。

## [1.30.0 / Codex 1.29.0 / Gemini 1.9.0] - 2026-06-18

### Changed — `caw-paper` を `caw-register` にリネーム

論文登録スキルの名前 `caw-paper` が「論文を扱うスキル」一般（探す `caw-research`／書く `caw-write`）と紛らわしいため、役割（**登録＝ライブラリ管理**）が明確な `caw-register` に改称。

- **スキル名・ディレクトリ・コマンドを改称**：`plugin/skills/caw-paper/` → `caw-register/`（＋ `codex-plugin` ミラー）、`gemini-plugin/commands/caw-paper.toml` → `caw-register.toml`、SKILL.md frontmatter `name`/`trigger` も更新。
- **全参照を一括置換**：`caw` ディスパッチ（論文 PDF の登録→`caw-register`）・二層テーブル・`engine-validation-map`（plugin/codex/copilot byte-identical）・各スキル相互参照（caw-research / caw-write / caw-intake / caw-report / caw-slides）・`GEMINI.md`・各 README・web docs・配布セミナー HTML。
- 役割分担は不変：**探す `caw-research` → 登録 `caw-register` → 書く `caw-write`**。L1/L2/L3 抽出レベル等の機能はそのまま（`caw-register` は L3 でユーザーの `paper-register` スキル相当のフル抽出。`paper-register` は別物なので改称しない）。
- 過去の CHANGELOG エントリの `caw-paper` 表記は履歴として保持。

### Note

- 版: plugin 1.29.0 → **1.30.0** / codex 1.28.0 → **1.29.0** / gemini 1.8.0 → **1.9.0** / copilot 1.17.0 据え置き（caw-register は未収載・参照のみ更新）/ marketplace 同期

## [1.29.0 / Codex 1.28.0 / Gemini 1.8.0] - 2026-06-18

### Added — caw-write（論文・申請書の執筆スキル）

研究側の「書く」担当 `caw-write` を新設。就活の書類スキル `caw-es` の研究側の対応物で、セミナー／募集で謳う**「論文執筆 AI」を実体化**するスキル（素材＝`work/manuscripts/_style/`〔文体〕・`work/profile/`・`work/papers/`〔引用源〕は既存だったが、それを消費して書く担当が欠けていた）。

- **1 スキル＋文書種別パラメータ**（論文／申請書／学会要旨／その他）。種別が言語（論文＝英語既定/申請書＝日本語既定）・テンプレ・チェックを切り替える（caw-es が ES/志望動機/自己PR を 1 スキルで扱うのと同型）。
- **ワークフロー**：要件確認（種別・投稿先/申請区分・字数）→ 素材収集（文体・プロフィール・**`work/papers/` 登録文献＝引用源**・`work/topics/`）→ アウトライン合意 → セクション→全体ドラフト → 保存（`work/manuscripts/<doc-slug>/`、md 既定／.tex・.docx 要望時）→ 推敲＋`codex:review`。
- **引用は `work/papers/` から本文引用＋文献リストを生成し、裏付けの無いものは「要出典」と明示して捏造しない**。
- **申請書ガード**（メモリ feedback の一般則化）：平易な日本語（他分野審査員）・未検証仮説を断定しない・数値は一次資料で確認・文中言及形式の引用。
- **3 段パイプライン完成**：caw-research（探す）→ caw-paper（登録）→ **caw-write（書く）**。就活（caw-research→caw-es）と対称化し、`engine-validation-map`（間接テストハーネス）に caw-es↔caw-write の生成パスペアを追加。
- 反映：`plugin/skills/caw-write/SKILL.md` 新規（＋ `codex-plugin`）／`GEMINI.md`・`commands/caw-write.toml`／`caw` ディスパッチ＋二層テーブル（plugin/codex/copilot）／`engine-validation-map`（plugin/codex/copilot byte-identical）／web `plugin.md`（Skills 8→9）／配布セミナー HTML §5。**copilot は未収載**（dispatch/engine-map のみ反映、caw-research/caw-paper と同方針）。

### Note

- 版: plugin 1.28.0 → **1.29.0** / codex 1.27.0 → **1.28.0** / gemini 1.7.0 → **1.8.0** / copilot 1.17.0 据え置き（caw-write 未収載）/ marketplace 同期

## [1.28.0 / Codex 1.27.0 / Gemini 1.7.0] - 2026-06-18

### Changed — caw-input / caw-playbook の改良（学習ループを閉じる・HPC 設定・移植性）

計算系スキルの相関（Playbook を挟んだ input↔playbook ループ）を強化し、移植性・利便を改善。

- **A. 学習ループを閉じる**：caw-playbook が「既定の推奨値を変えるべき教訓」を得たら、Lessons Learned への追記だけでなく Playbook の**「デフォルト推奨パラメータ」ブロックも更新**（旧値→新値の理由つき）。caw-input は Step 4 で**「デフォルト＋以降の Lessons Learned で上書き」を明示的に reconcile**（食い違いは後発を優先）。→ 教訓が次回入力に確実に反映。
- **B. caw-input が HPC 設定を参照**：オンボ Q6 で `office/computation/CLAUDE.md`（AGENTS/GEMINI）に記録された **submission 既定（queue/walltime/並列/module/account）を読む**。無ければ Playbook 事例→確認。local 設定ならジョブスクリプトでなく直接実行コマンド。
- **C. 移植性**：caw-playbook の汎用知見の保存先を環境別に（**Claude Code=auto-memory `~/.claude/.../memory/`、Codex/Gemini=`office/computation/<CLAUDE/AGENTS/GEMINI>.md` の「共通知見」or 秘書 notes**）。従来は Claude 専用パスを全 CLI に記載していた。
- **D. 細部**：caw-playbook の解析サマリ・Lessons は**日本語で**明記／caw-input は `jobs/...md` の同名衝突回避（`-2`）／caw-input に**バッチ・スキャン生成**（複数系・汎関数スキャンを 1 計算 1 ディレクトリで一括、多いときは一覧確認）。
- 反映：`caw-input/SKILL.md`・`caw-playbook/SKILL.md`（plugin + codex）／`GEMINI.md`・`commands/caw-input.toml`・`commands/caw-playbook.toml`。

### Note

- 版: plugin 1.27.0 → **1.28.0** / codex 1.26.0 → **1.27.0** / gemini 1.6.0 → **1.7.0** / copilot 1.17.0 据え置き（caw-input/playbook 未収載）/ marketplace 同期

## [1.27.0 / Codex 1.26.0 / Gemini 1.6.0] - 2026-06-18

### Added — caw-research（研究）が登録済み論文を文献リストから除外

研究モード caw-research の論文検索で、**`work/papers/` に登録済み（md がある）論文を既定で一覧から除外**する（目的＝「まだ持っていない論文を見つける」）。

- 新 **R-Step 2b**：HTML 書き出し前に `work/papers/*.md` の frontmatter `doi`（あれば arXiv ID）＋ファイル名で「登録済みセット」を作り、検索結果から **DOI/arXiv 一致**を除外（DOI 無しはタイトル＋筆頭著者の近似一致で厳しめ判定＝誤除外回避）。
- HTML ヘッダの検索条件行に「**（登録済み N 件を除外）**」を明記。掲載件数は除外後の数。
- `work/papers/` が空／無ければ除外なし。**ユーザーが「登録済みも含めて」と言えば全件**を載せる。
- 反映：`caw-research/SKILL.md`（plugin + codex）R-Step 1・新 R-Step 2b・R-Step 3 ヘッダ／`GEMINI.md`・`commands/caw-research.toml`。

### Note

- 版: plugin 1.26.0 → **1.27.0** / codex 1.25.0 → **1.26.0** / gemini 1.5.0 → **1.6.0** / copilot 1.17.0 据え置き（caw-research 未収載）/ marketplace 同期

## [1.26.0 / Codex 1.25.0 / copilot 1.17.0 / Gemini 1.5.0] - 2026-06-18

### Changed — 研究モード caw-research の出力を Markdown 表 → クリック可能な HTML リストに

研究トラックの caw-research（論文検索）の成果物を、`work/topics/<topic>.md`（書誌の md テーブル）から **`work/topics/<topic>.html`（オフライン自己完結の HTML）** に変更。**md は作らない**。

- **タイトルがハイパーリンク**：DOI → `https://doi.org/<doi>`、arXiv → `https://arxiv.org/abs/<id>`、無ければ Google Scholar 検索にフォールバック。クリックで論文ページへ直接飛べる。
- **デザイン**：1 論文 1 ブロックの**静的な縦リスト**（並べ替えなし・JS なし）。タイトル（リンク）＋メタ行（著者・年・誌名）＋要約 1〜2 文＋DOI/arXiv 補助リンク。製品配色・インライン CSS・装飾最小。フッタに「PDF を `work/papers/` に置いて『登録して』で caw-paper が登録」の導線。
- **要約は日本語（ユーザーの言語）で出力**（原文が英語でも日本語に要約）。OpenAlex 等の abstract が出版社ボイラープレートで壊れ／欠落の場合はタイトルから 1 行＋「※要約データなし」（知見は捏造しない）。同じ「日本語で要約」原則を caw-paper にも明記。
- **ファイル名規則**：`<topic-slug>_<YYYYMMDD>_n<件数>.html`（例 `mof_20260618_n10.html`）。トピック・取得日・件数を含め、同テーマの再検索は上書きせず日付で別ファイルとして残す（同一 topic+日付は `-2`,`-3`）。caw の既存出力（`..._YYYYMMDD`）と整合。
- 反映：`caw-research/SKILL.md`（plugin + codex）の R-Step 3・description・intro／`GEMINI.md`・`commands/caw-research.toml`／`caw/SKILL.md` 二層原則の `work/topics/` 説明（3 系統）・`chemistry-departments`・`mcp-setup-templates`／plugin README・web `plugin.md`／配布セミナー HTML のスキル説明。就活モードの caw-research（企業研究の md/HTML 選択）は変更なし。

### Note

- 版: plugin 1.25.0 → **1.26.0** / codex 1.24.0 → **1.25.0** / copilot 1.16.0 → **1.17.0** / gemini 1.4.0 → **1.5.0** / marketplace 同期

## [1.25.0 / Codex 1.24.0 / copilot 1.16.0 / Gemini 1.4.0] - 2026-06-17

### Changed — 論文検索を caw-research（研究トラック）へ移管、caw-paper は登録専任に

研究の文献ワークフローを「**caw-research で探す → caw-paper で登録**」の 2 段に整理した（discovery と library の責務分離）。

- **caw-research をデュアルトラック化**：従来の就活専用（企業・業界研究）に加え、**研究トラックでは関心テーマの論文検索**（arXiv / Crossref / Semantic Scholar / OpenAlex / PubMed）→ `work/topics/<topic>.md` にリスト化する分岐を追加。`> トラック: 就活` マーカーで自動判定（caw-intake / caw-doctor と同方式）。**探索はリスト化まで**で、入手 PDF の登録は caw-paper に渡す。
- **caw-paper を登録専任に**：旧「モード A: 論文検索」を削除し、**モード A: PDF 登録 / モード B: バッチ**の 2 モードに。description・トリガー（「論文を集めて」は caw-research へ）・「いつ使うか」を登録系に絞った。
- **ディスパッチ更新**：`caw/SKILL.md`（3 系統）・`GEMINI.md` の研究振り分けを「文献検索→caw-research / 論文 PDF 登録→caw-paper」に分割。
- **engine-validation-map 更新**：caw-research が両トラックの「収集」を担う形に（就活利用が研究の探索パスを直接検証する関係が強化）。
- gemini commands（caw-research / caw-paper の description・prompt）、plugin README・web `plugin.md`（Skills 7→8、caw-research 追記）、配布セミナー HTML のスキル表も更新。

### Added — caw-paper に抽出レベル（L1/L2/L3、毎回必ず選択・推奨なし）

caw-paper の AI 使用量（トークン）は「PDF 本文を context に入れて要約・タグを生成する」Step 2 が主因のため、**発動時に必ず抽出レベルを `AskUserQuestion` で尋ねる**（省略禁止・自動既定なし、`feedback_skill_default_wording_skips_askuser` に準拠）。**どれを推奨とはせず、レベルで AI 使用量が変わる（L1 < L2 < L3）ことを明示**して選ばせる。

- **L1**：書誌情報＋要旨 4 行＋結論の要点（数値・手法・背景なし）。最小消費。
- **L2**：L1 ＋ One-line summary・背景概要・対象/手法概要・主要な結果（代表テーブル＋数値）。中間。
- **L3**：背景・動機／対象物質・系／手法詳細／主要な結果（全数値）／考察／本研究の限界／関連研究との比較／引用文脈テンプレート／キーワードの**フル抽出＝paper-register スキルと同等の網羅度**。最大消費。
- レベルは **Step 2 の抽出**と **Step 3 の md 充実度**の両方を決める（ノブは 1 つ。Step 3 に独立レベルは設けない）。**バッチ（モード B）は最初に 1 回だけ尋ね**全 PDF に同じレベルを適用。
- 反映：`caw-paper/SKILL.md`（plugin + codex）・`GEMINI.md` の caw-paper 節・`commands/caw-paper.toml`。

### Note

- 版: plugin 1.24.0 → **1.25.0** / codex 1.23.0 → **1.24.0** / copilot 1.15.0 → **1.16.0** / gemini 1.3.0 → **1.4.0** / marketplace 同期

## [1.24.0 / Codex 1.23.0 / copilot 1.15.0 / Gemini 1.3.0] - 2026-06-17

### Changed — 成果物・作業フォルダを `work/` 配下に集約（ルート直下の散らかりを解消）＋ 完了メッセージを実態化

ユーザーフィードバック「ルート直下に生成されるフォルダが多すぎて面くらう」を受け、両モードで **成果物・作業ディレクトリをすべて単一の `work/` ディレクトリ配下に集約**。プロジェクトルート直下は **`office/`（運営）・`work/`（成果物）・`inbox/`（統合投入口）・`はじめにお読みください.md`** の 4 つに整理。

- **研究**：`work/{papers,topics,manuscripts,analyses,notebooks,figures,presentations/slides,scripts,tools}` ＋ 計算ソフト選択時の `work/{gaussian,gromacs,…}`（各 `inbox/`・`_past-data/` 付き）。
- **就活**：`work/{companies,documents,self-analysis,interview-prep,recruit,feedback}`。
- `inbox/`（統合 inbox）は投入口として**ルート直下に維持**。`caw-report/`（開発者向け匿名レポート）も可視性のためルート直下のまま。
- 全スキル（caw-paper/input/playbook/slides/research/es/interview/events/intake/doctor 等）の出力パス、`chemistry-departments` / `job-hunting-departments` / 各テンプレ、`output-location-check` フックの推奨パス、caw-doctor のチェック対象、README・web ドキュメントの例ツリーを `work/` 配下に統一（4 配布ツリー＋web で約 920 箇所）。`office/<部署>/` への成果物配置禁止ルールは不変。

### Fixed — 研究モード完了メッセージの陳腐化を是正

部署選択廃止（v1.19.0）以降ズレていた完了メッセージのツリー表記を実態化：`office/` を「dotfile」→「可視フォルダ」、「(選択された他の部署)」→「全 8 部署を常に作成」、各成果物の「○○選択時」注記を撤去し `work/` 配下のネスト表示に。

### Note

- 版: plugin 1.23.0 → **1.24.0** / codex 1.22.0 → **1.23.0** / copilot 1.14.0 → **1.15.0** / gemini 1.2.0 → **1.3.0** / marketplace 同期

## [1.23.0 / Codex 1.22.0 / copilot 1.14.0 / Gemini 1.2.0] - 2026-06-17

### Changed — 研究オンボーディングのモード（はじめて / 通常 / 詳しく）を廃止し、全ユーザーに全 8 問を質問

研究トラックのオンボーディングから **セットアップモード選択（Call 0）とモードによる質問の出し分けを撤廃**。これまでは「はじめて／通常／詳しく」で質問数が変わっていたが、今後は **全ユーザーに研究プロファイル（Call 1：Q1〜Q4）と詳細プロファイル（Call 2：Q6〜Q9）の全 8 問を一律で尋ね**、回答をすべて scaffold に反映する。作成部署は従来どおり常に全 8 部署。

- 撤去：`Call 0`（モード選択）・`Call 1Q`（はじめてモード最小ヒアリング）・`3-8 初回ツアー`（サンプル PDF 生成含む）・研究トラックでの `> 運用モード: はじめて` フラグ付与。
- 温存：**就活トラックの「はじめてモード」機構**（平易誘導＋`> 運用モード: はじめて`）はそのまま。就活はこれまで通り常に平易モードで進む。
- 反映ファイル：`caw/SKILL.md`（plugin / codex / copilot）・`gemini-plugin/GEMINI.md`・各 README・`caw-doctor`（START HERE の注記）・`caw-report`（運用モードの値）。
- 併せて plugin README のオンボーディング説明を実態に合わせて修正（旧「部署を 7 つから選択」「研究プロファイル 4 問」の陳腐化記述を是正）。

### Note

- 版: plugin 1.22.1 → **1.23.0** / codex 1.21.1 → **1.22.0** / copilot 1.13.0 → **1.14.0** / gemini 1.1.1 → **1.2.0** / marketplace 同期

## [1.22.1 / Codex 1.21.1 / Gemini 1.1.1] - 2026-06-17

### Changed — caw-report に提出先 Google フォーム URL を組み込み

caw-report の Step 5 を「**提出先フォームの URL をチャットに表示**」に更新。テストユーザーが `caw-report` を実行すると、生成完了後にチャットへ提出フォームの URL を表示し、「レポートの中身を貼り付けて提出してください（匿名なのでそのまま提出可）」と案内する。caw が自動送信することはなく、提出はユーザーの操作で行う。

- `caw-report/SKILL.md`（plugin + codex）・`gemini-plugin`（GEMINI.md ＋ `commands/caw-report.toml`）に提出フォーム URL を追記。
- 配布 HTML（セミナー資料・repo 外）の「報」セクションにも提出フォームのボタンリンクを追加。

### Note

- 版: plugin 1.22.0 → **1.22.1** / codex 1.21.0 → **1.21.1** / gemini 1.1.0 → **1.1.1** / copilot 1.13.0 据え置き / marketplace 同期

## [1.22.0 / Codex 1.21.0 / copilot 1.13.0 / Gemini 1.1.0] - 2026-06-17

### Added — caw-report（開発者向け匿名動作レポート）

テストユーザーの caw 環境を点検し、**開発者がレビューするための匿名レポート**を生成する新スキル。テストユーザーが利用 → 生成された `caw-report/<日付>.md` を開発者へ共有 → caw 改善に活かす、という流れ。抽出シグナル（すべて匿名）：**①環境/互換性**（version・CLI・OS・ツール有無・MCP 有無/サーバ数・利用期間/最終活動）**②オンボーディング完遂度**（scaffold 完走・不足数・モード）**③構造の健全性と逸脱**（合否・二層原則違反の種別別件数・規約外フォルダ数・不可視フォルダ検知・設定ファイル肥大）**④利用状況と完成度**（各 dir のファイル数・空/極小数・放置数・HTML/voice/profile/past-answers の有無）**⑤エラー**（スキル別×種別の件数・inbox 未処理・hook 失敗）**⑥運用エンゲージメント**（notes/todos/decisions 件数）**⑦間接検証シグナル**。

- **完全匿名（PII リスクゼロ）**：個人情報・企業名・研究テーマ・ファイル名・本文・絶対パス・研究分野/志望業界の具体名を**一切含めない**。出せるのは標準フォルダ名・件数・合否・エラー種別・version/CLI/トラック/モードのみ。生成後にスキルが**自己点検**して PII が無いことを確認してから保存。caw が自動で外部送信することはしない（共有はユーザーの手で）。
- `caw-report/SKILL.md`（plugin + codex）、`gemini-plugin`（GEMINI.md にスキル節 ＋ `commands/caw-report.toml`）。copilot は PoC のため未収載。
- `engine-validation-map.md`（3 系統 byte 一致）：主観の `feedback/` に対する**客観・匿名の構造シグナル**として caw-report を §2 に追記（§1 のエンジンパス稼働を件数・合否で裏取り）。
- caw-doctor が「ユーザー自身の修復」用なのに対し、caw-report は「開発者へ匿名フィードバック」用。

### Note — caw-report

- 版: plugin 1.21.0 → **1.22.0** / codex 1.20.0 → **1.21.0** / copilot 1.12.0 → **1.13.0** / gemini 1.0.0 → **1.1.0** / marketplace 同期

## [Gemini 1.0.0 追加 / plugin 1.21.0 / Codex 1.20.0 / copilot 1.12.0] - 2026-06-17

### Added — Gemini CLI 版 caw（`gemini-plugin/`、4 つ目の配布ターゲット）

caw を **Gemini CLI の extension** として配布開始。これで caw は **Claude Code / Codex CLI / GitHub Copilot CLI（PoC）/ Gemini CLI** の 4 CLI に対応。

- `gemini-plugin/`：`gemini-extension.json`（manifest, version 1.0.0）＋ `GEMINI.md`（常時ロードの caw 本体）＋ `commands/*.toml`（`/caw` ほか 12 個の明示コマンド）＋ `README.md`。
- Gemini CLI は「説明文で skill を自動発火」する仕組みを持たないため、caw 本体（秘書・両トラックのオンボーディング・ディスパッチ・統合 inbox 自動仕分け・各スキル手順）を**単一の `GEMINI.md`（常時ロード）に集約**。プロジェクト設定は `office/GEMINI.md`。メソッド・二層原則・統合 inbox は 4 CLI 共通。
- 導入：`gemini extensions install https://github.com/dr-neoueda/chemist-ai-workflow`。Gemini CLI には hooks（bash）が無いため Windows でも Git Bash 不要。
- `scripts/check-consistency.sh`：版表示・個人化リーク走査・隠しフォルダ走査に `gemini-plugin/` を追加。
- web `gemini-cli/index.md` を「Phase 2 執筆予定」→「対応（導入・できること）」に更新。

### Note — Gemini 追加

- 版: **gemini-plugin 1.0.0（新規）** / plugin 1.21.0・codex 1.20.0・copilot 1.12.0 は据え置き（無変更）。

## [1.21.0 / Codex 1.20.0 / copilot 1.12.0] - 2026-06-17

### Added — caw-intake を「統合 inbox の自動仕分け」＋デュアルトラック化

`caw-intake` を、**1 つの `inbox/` に何でも入れれば中身を見て自動で振り分ける**統合プロセッサに刷新。ユーザーは「どの資料をどのフォルダに入れるか」を悩まなくてよい。研究・就活の両トラックに対応（caw-doctor 同様に `> トラック: 就活` の有無で分岐）。

- **統合 inbox**：プロジェクト直下に単一の `inbox/`（両トラック共通）。研究は論文/申請書/スライド/CV/計算入出力/測定データ/外部論文、就活は ES/履歴書/企業情報など**種類を問わず投入**。旧 `documents/inbox/`・`profile/inbox/` は廃止し `inbox/` に一本化。
- **内容判定 → 振り分け**：`caw-intake/SKILL.md`（plugin + codex）を「分類表に基づく振り分け」中心に再構築。中身（著者・書式・内容）で種類を判定し処理を分岐——
  - 自分の論文/スライド/CV → 執筆スタイル(`manuscripts/_style/voice-self.md`)・研究プロファイル/知見/業績/引用/手法(`profile/*`)・図表/発表スタイル(`figures/_style.md`・`presentations/_style.md`)・CV(`profile/cv.md`)・用語辞書(`profile/glossary.md`)を抽出
  - 外部論文 → `caw-paper` で登録、計算入出力 → `caw-playbook` の `_past-data/` 取り込み、企業情報 → `caw-research` の素材、に委譲（二重処理しない）
  - ES/履歴書 → `self-analysis/*`・`documents/voice-style.md`・`documents/past-answers.md` を抽出
  - 判定不能はユーザーに確認
- 新トップレベル `profile/`（就活の `self-analysis/` に対応する研究者の自己プロファイル層）。`caw/SKILL.md` scaffold・`caw-doctor`・`engine-validation-map.md` を統合 inbox 前提に更新（検証マップは「統合 inbox の内容判定→振り分け」を 4 つ目のエンジンパターンに）。
- copilot は PoC のため caw-intake スキル本体は未収載（reference の記述のみ追従）。

### Note — caw-intake 統合 inbox

- 版: plugin 1.20.0 → **1.21.0** / codex 1.19.0 → **1.20.0** / copilot 1.11.0 → **1.12.0** / marketplace 同期

## [1.20.0 / Codex 1.19.0 / copilot 1.11.0] - 2026-06-16

### Added — caw-intake（過去書類の取り込み・自己分析ジェネレータ）

過去に書いた ES・志望動機・自己PR・履歴書（`documents/inbox/`）を取り込み、**文体・経験(STAR)・強み/弱み・ガクチカ・志望動機/就活の軸・基本プロフィール・過去回答バンク**（7 種）を抽出して、それぞれ適切なファイルに書き分けて配置する就活モードの新スキル。caw-es / caw-interview がこの出力を参照して「本人の文体・実績」で書けるようになる。

- 新スキル `caw-intake/SKILL.md`（plugin + codex。copilot は PoC 対象外）。発火＝「過去の ES を取り込んで」「inbox の文章から自己分析して」。
- 抽出 → 配置（7 種）：文体 → `documents/voice-style.md`、経験(STAR) → `self-analysis/experiences.md`、強み・弱み・価値観 → `self-analysis/strengths.md`、ガクチカ候補 → `self-analysis/gakuchika.md`、志望動機・就活の軸 → `self-analysis/motivation.md`（新規）、基本プロフィール → `self-analysis/profile.md`（新規）、過去回答バンク（設問×回答） → `documents/past-answers.md`（新規）。既存ファイルは上書きせず追記マージ、個人情報はローカル保持。caw-es / caw-interview は motivation.md・past-answers.md も参照する。
- 配線（3 系統 byte 一致）：`job-hunting-departments.md`（§D2 最初の一声・§E ディスパッチ・§B-4 inbox 説明・analysis 部署テンプレ）、`engine-validation-map.md`（4 つ目のエンジンパターン「過去データ取り込み → 個人最適化 seed」を新設、caw-playbook の `_past-data/` 取り込みと対応づけ）。
- `caw-es` に caw-intake への相互参照を追記（「文体を学習して」は文体のみの軽量版、まとめて抽出は caw-intake）。

### Note — caw-intake

- 版: plugin 1.19.0 → **1.20.0** / codex 1.18.0 → **1.19.0** / copilot 1.10.0 → **1.11.0** / marketplace 同期

## [1.19.0 / Codex 1.18.0 / copilot 1.10.0] - 2026-06-16

### Changed — 初期環境構築でモードに応じた全部署を作成＋化学者モードの質問を再設計

初期 scaffold が「ユーザーが選んだ部署だけ」を作っていたのを、**モードに応じた全部署を常に作成**に変更。これに合わせて化学者モードのオンボーディング質問を作り直した。

- **化学者モード（全 8 部署を常に作成）**：`caw/SKILL.md`（3 系統）。
  - **部署選択質問（Call 2 / Q5a・Q5b）を廃止**。「どの部署を作るか」をユーザーに尋ねない。
  - **Quick（秘書のみ）モードを廃止**。経験レベルは **はじめて / 通常 / 詳しく** の 3 段階に整理（Standard→通常、Advanced→詳しく）。どのモードでも全 8 部署（secretary / research / engineering / computation / analysis / writing / review / presentation）を作成し、モードで変わるのは personalization 質問の深さだけ。
  - 旧 Call 3（詳細プロファイル Q6〜Q9）は Call 2 に繰り上げ。scaffold 範囲・3-3・プレースホルダ説明・MCP 生成条件（Quick→はじめて）を全部署前提に更新。
- **就活モード（全 4 部署を常に作成）**：`job-hunting-departments.md`（3 系統 byte 一致）§B-3。QJ3a の悩みは「どの部署を作るか」ではなく **START HERE の最初の一歩の優先度**に使うよう役割変更（部署は秘書＋ research/analysis/writing/presentation を常に作成）。
- 付随更新：`claude-md-template.md` / `agents-md-template.md`（DEPARTMENT プレースホルダの説明を「全部署」に）、`caw-doctor/SKILL.md`（全部署前提のチェック文言）、`plugin/README.md`・`plugin/TESTING.md`。
- copilot marketplace の `metadata.version` が 1.8.0 で取り残されていたのを 1.10.0 に同期。

### Fixed — Codex CLI のインストールが失敗する問題（authentication）＋ 導入手順の是正

- **`.agents/plugins/marketplace.json` の `"authentication": "NONE"` → `"ON_INSTALL"`**。これが入っていると `codex plugin marketplace add dr-neoueda/chemist-ai-workflow`（marketplace 登録）が（特に Windows で）失敗する。`web/.../codex-cli/skills.md` のサンプルも同様に修正。
- **Codex の導入手順を実態に合わせて 2 ステップ化**：`codex plugin marketplace add ...`（marketplace 登録）→ `codex plugin add caw@chemist-ai-workflow`（プラグイン本体追加）。web 各所の「個別 install コマンドはありません」という誤記を全面修正（`plugin.md` / `codex-cli/{index,setup,skills}.md`）。Desktop 配布 HTML（repo 外）も同時修正。
- **アンインストール手順も是正**（`codex-cli/uninstall.md`）：「caw だけの個別アンインストールは無い」は誤り。実際は 2 レベル—`codex plugin remove caw@chemist-ai-workflow`（プラグイン本体のみ削除、marketplace 登録は残る）／`codex plugin marketplace remove chemist-ai-workflow`（marketplace ごと削除）。再現フロー・モード名（はじめて/通常/詳しく）も更新。

### Note

- 版: plugin 1.18.0 → **1.19.0** / codex 1.17.0 → **1.18.0** / copilot 1.9.0 → **1.10.0** / marketplace 同期

## [1.18.0 / Codex 1.17.0 / copilot 1.9.0] - 2026-06-16

### Added — 文体プロファイル（`documents/voice-style.md`）を caw-es に正式組込

「自分の文体で書く AI」を **書類部の AGENTS.md（CLAUDE.md）を書き換えずに**実現する仕組みを追加。本人の過去の文章（`documents/inbox/`）から文体（トーン・言い回し・一文の長さ・構成の癖）を抽出し、**専用ファイル `documents/voice-style.md` に書き出す**。設定（部署の AGENTS.md）と文体プロファイルを分離することで、誤って部署設定を上書きする事故を防ぐ。

- `caw-es/SKILL.md`（plugin + codex）: 「文体を学習して／私の文体を覚えて」で `documents/inbox/` を読み `documents/voice-style.md` を生成・更新するワークフローを新設。ES 生成時（Step 2）は `voice-style.md` があれば必ず読み、その文体で書く。重要な注意事項に「部署・`office/` の `AGENTS.md`（`CLAUDE.md`）は書き換えない」を明記。
- `job-hunting-departments.md`（3 系統）: §B-4 ディレクトリ表の `documents/` 行に `voice-style.md` を追記、§C 書類部テンプレの成果物に「文体プロファイル（『文体を学習して』で inbox から生成。設定ファイルは書き換えない）」を追記。

### Note

- 版: plugin 1.17.1 → **1.18.0** / codex 1.16.1 → **1.17.0** / copilot 1.8.0 → **1.9.0** / marketplace 同期

## [1.17.1 / Codex 1.16.1] - 2026-06-16

### Fixed — caw-research は発動時に必ず調査レベル/出力形式を尋ねる

テストで「○○について企業研究して」と伝えると caw-research が**尋ねずに既定（L2・md）で実行**される問題を修正。Step 1 の「既定は md・指定なければ md で進める」が「尋ねなくてよい」と解釈されていたため、**【必須・省略禁止】毎回必ず `AskUserQuestion` で調査レベルと出力形式を尋ねる**（企業名・業界だけ言われても自動で既定にしない）と明記。「既定」表現を「推奨（初期選択）」に変え、重要な注意事項にも追記。plugin + codex（copilot は caw-research 未収載で据え置き）。

### Note

- 版: plugin 1.17.0 → **1.17.1** / codex 1.16.0 → **1.16.1** / copilot 1.8.0 据え置き / marketplace 同期

## [1.17.0 / Codex 1.16.0 / copilot 1.8.0] - 2026-06-16

### Changed — 就活: 初期環境構築の後に「何をしますか？」と尋ねる

scaffold ＋ START HERE 生成の直後、**秘書がいきなり作業を始めず、まず `AskUserQuestion` で「何をしますか？」と尋ねる**ようにした（`job-hunting-departments.md` §D2 新設）。立ち上げた部署・QJ3a の悩みに合わせて、最初の一歩（自己分析／企業研究 `caw-research`／ES `caw-es`／面接 `caw-interview`／締切 `caw-events`／予定確認）を 4 つに絞って提示。冒頭の流れ説明にも反映。3 系統 byte 一致。

### Note

- 版: plugin 1.16.0 → **1.17.0** / codex 1.15.0 → **1.16.0** / copilot 1.7.0 → **1.8.0** / marketplace 同期

## [1.16.0 / Codex 1.15.0 / copilot 1.7.0] - 2026-06-16

### Changed — 就活オンボーディング: Q0（経験レベル）廃止＋志望職種の追加

- **就活トラックでは経験レベル（Q0「ターミナル/AI は初めてか」）を聞かない**ようにした。就活生は技術初心者が多いので、**常にはじめてモード（平易な日本語・用語説明）で進める**（`office` 設定に `> 運用モード: はじめて` を必ず書く。慣れた人が「もう普通でいい」と言えば外す）。
- **志望職種の質問（QJ2c）を追加**：志望業界（QJ2a/QJ2b）に加えて「気になっている職種は？」を複数選択で聞く（営業・販売／企画・管理／技術・研究／専門職・クリエイティブ ＋ Other）。
- `job-hunting-departments.md` §A（Q0 廃止・QJ2c 追加・注記更新）・§B-1（常に はじめてモード フラグ）、`caw/SKILL.md` の Call T 就活分岐を 3 系統で更新。

### Note

- 版: plugin 1.15.0 → **1.16.0** / codex 1.14.0 → **1.15.0** / copilot 1.6.0 → **1.7.0** / marketplace 同期

## [1.15.0 / Codex 1.14.0] - 2026-06-16

### Changed — caw-es / caw-interview が caw-research の md を必ず参照

`caw-es`・`caw-interview` が、企業固有の作業で **`caw-research` の出力 `companies/<企業>.md` を必ず参照**するようにした（任意 → 絶対）。企業 A の ES を書くと `companies/A.md` を踏まえて自動でより良いドラフトが書かれる。

- **caw-es**: Step 2 で企業固有の書類（志望動機・ES・自己PR）は最初に `companies/<企業>.md` を読む。研究の 8 ブロック（A 事業・C 強み・D 競合・G 求める人物像・H 接点）を志望動機・接点に反映。**未作成なら `caw-research` を先に実行/提案**してから書く。
- **caw-interview**: 想定問答（A）・逆質問（C）で `companies/<企業>.md` を必ず踏まえる。未作成なら `caw-research` を先に促す。
- 配信 plugin + codex（copilot は両スキル未収載で据え置き）。

### Note

- 版: plugin 1.14.0 → **1.15.0** / codex 1.13.0 → **1.14.0** / copilot 1.6.0 据え置き / marketplace 同期

## [1.14.0 / Codex 1.13.0 / copilot 1.6.0] - 2026-06-16

### Changed — caw-company を caw-research にリネーム＋調査レベル/出力形式の選択を追加

`caw-company`（企業・業界研究スキル）を **`caw-research`** に改名（「company」だと業界研究の面が伝わらず分かりにくいため）。あわせて発動時の選択肢と既定出力を見直した。

- **発動時に `AskUserQuestion` で 3 点を確認**：対象（企業/業界）／**調査レベル（L1 クイック / L2 スタンダード / L3 ディープ）**／**出力形式（md のみ / html のみ / 両方）**。
- **既定の成果物を md に**：何も指定しなければ `companies/<企業>.md`（業界は `companies/_industry/<業界>.md`）のみ生成。HTML は html / 両方 を選んだときだけ。
- **汎用 8 ブロック（A基本〜H接点）× 調査レベルの深さマッピング**を skill 本体に明文化（L1=A·B·C·F 要約／L2=+D·E·G·H／L3=全 8＋拡張）。出典強度ルール・HTML 可視化規約（id 衝突回避等）は継続。
- リネーム：`git mv` でスキルディレクトリ（plugin+codex、履歴保持）。参照（`caw-events` SKILL.md・`engine-validation-map.md`）も `caw-research` に更新。トリガは `/caw-research`。
- 配信 plugin + codex（copilot は caw-research スキル未収載・共有 `engine-validation-map.md` のみ同期）。LP/README 非掲載は継続。

### Note

- 版: plugin 1.13.0 → **1.14.0** / codex 1.12.0 → **1.13.0** / copilot 1.5.0 → **1.6.0** / marketplace 同期

## [1.13.0 / Codex 1.12.0 / copilot 1.5.0] - 2026-06-13

### Changed — 就活オンボーディングの質問を改善（全モードで業界・悩みを聞く）

就活トラックの初期ヒアリング（`job-hunting-departments.md` §A Call 1J）を刷新。**経験レベル（はじめて/Quick/Standard/Advanced）に関わらず QJ1〜QJ3 を全モードで聞く**ようにした（区分・志望業界・悩みは「プログラミング/AI が初心者か」とは無関係なため、はじめてモードでも省略しない）。

- **QJ2 志望業界を 2 段階の詳細分類に**：QJ2a（大分類 4 つ multiSelect＝メーカー／商社・流通・小売・不動産・運輸／IT・通信・メディア／金融・コンサル・インフラ・公共）→ QJ2b（選んだ大分類ごとに中分類を確認、代表 4 つ＋Other）。
- **QJ3 を「悩み」型の複数選択に**：QJ3a（テーマ別の悩み multiSelect＝自己分析／業界・企業研究／ES・書類／面接）＋ QJ3b（進め方・状況 multiSelect＝何から始めれば／複数社の締切管理／モチベ・メンタル）。
- **部署の立ち上げを QJ3a の悩みに連動**（§B-3 を更新）：選んだ悩み → 対応部署（analysis/research/writing/presentation）。何も選ばない／「何から始めれば」→ research＋analysis を既定。「締切管理」→ 秘書のスケジュール強化、「メンタル」→ 秘書が寄り添い。
- 3 系統 byte 一致（plugin の CLI 差分は注記の CLAUDE/AGENTS のみ）。LP/README 非掲載は継続。

### Note

- 版: plugin 1.12.0 → **1.13.0** / codex 1.11.0 → **1.12.0** / copilot 1.4.0 → **1.5.0** / marketplace 同期

## [1.12.0 / Codex 1.11.0 / copilot 1.4.0] - 2026-06-13

### Changed — 運営フォルダを可視化（`.company/` → `office/`）【絶対ルール】

**caw は環境構築でユーザーのプロジェクトに先頭ドット（`.`）始まりの Finder/Explorer 不可視フォルダを作らない**を絶対ルール化。IDE を導入しないユーザーが運営フォルダを確認できないのは不便なため。

- **運営フォルダ `.company/` → 可視の `office/` に全面改名**（製品リポジトリ全体 約290 箇所、plugin/codex/copilot/web/docs/hooks/README/RESUME）。成果物は従来どおり top-level（**二層原則は不変**、運営層の名前だけ可視化）。
- 二層原則の説明文（旧「ドット始まりなので非表示」）を「先頭ドットなしの可視フォルダ」に修正し、絶対ルールを `caw/SKILL.md`・ルート設定テンプレ（`claude-md-template` / `agents-md-template`）・README・`output-location-check` フックに明記。
- **`check-consistency.sh` に回帰防止ガード**を追加（配布ツリーに `.company` が再混入したら BAD で落とす）。
- ユーザー個人の既存 `~/lab/.company/`（著者の実運用環境）は製品とは別物のため不変。`~/.claude` など CLI 自身の設定ディレクトリは対象外（必須）。

### Note

- 版: plugin 1.11.0 → **1.12.0** / codex 1.10.0 → **1.11.0** / copilot 1.3.0 → **1.4.0** / marketplace 同期

## [1.11.0 / Codex 1.10.0 / copilot 1.3.0] - 2026-06-13

### Changed — 就活部署フォルダを化学トラックと統一

就活トラックが作る部署フォルダ名を化学トラックと**共通化**（中身〔CLAUDE.md / AGENTS.md〕は就活向けで別物のまま）。これにより就活 scaffold が化学と同じ部署パスを通り、間接テストハーネス（v1.10.0）の scaffold 検証がより厳密になる。

- **部署フォルダの対応**：`secretary`（窓口/選考スケ）・`research`（企業・業界研究）・`analysis`（自己分析）・`writing`（応募書類）・`presentation`（面接対策）＝化学 8 部署のサブセット。`engineering`/`computation`/`review` は化学専用で就活では作らない。
- **成果物フォルダ（top-level）は据え置き**：`companies/`・`recruit/`（research）／`self-analysis/`（analysis）／`documents/`（writing）／`interview-prep/`（presentation）。部署フォルダ名 ≠ 成果物フォルダ名（化学の `writing`→`manuscripts/` と同じ流儀）。
- 反映：`job-hunting-departments.md`（§B-3 部署表＋対応表新設・§B-4 関連部署列・§C テンプレ見出し・§E ディスパッチ、3 系統 byte 一致）、`caw-doctor` §J（就活診断の期待部署・成果物表、plugin+codex）、`engine-validation-map.md`（部署統一の注記、3 系統）。
- 就活はテストユーザー向けサブ機能のため LP/README 非掲載を継続。

### Note

- 版: plugin 1.10.0 → **1.11.0** / codex 1.9.0 → **1.10.0** / copilot 1.2.0 → **1.3.0** / marketplace 同期

## [1.10.0 / Codex 1.9.0 / copilot 1.2.0] - 2026-06-13

### Added — 就活＝化学の「間接テストハーネス」構造

就活トラックを**化学者向け本機能のテストハーネス**として明示する構造を追加。就活と化学は**同一のドメイン非依存エンジン**（オンボ → 部署 scaffold → 秘書ゲートウェイ/dispatch → スキル3パターン → HTML可視化 → memory → caw-doctor）を共有するため、**就活テストユーザーの利用が、対応する化学機能の間接検証**になる。

- **新リファレンス `skills/caw/references/engine-validation-map.md`**（3系統 byte 一致）：共有エンジン7要素の定義／**検証マップ表**（化学↔就活↔エンジンパス↔就活で検証されること、エンジンパス単位で1対1）／テストユーザー・フィードバック構造（`feedback/` ＋雛形）／著者の照合手順／構造を壊さないルール。
- **就活 scaffold に `feedback/`（top-level）を追加**：`job-hunting-departments.md` の作業ディレクトリ表に `feedback/` を、§F「テストユーザー・フィードバック（化学機能の間接検証）」を新設。秘書が節目に軽くフィードバックを促し、著者が回収して検証マップで化学側エンジンパスの signal に翻訳する。
- フィードバックは**ツールの使い勝手のみ**（個人情報・企業の非公開情報は書かせない・ローカル完結）。
- `check-consistency.sh` の codex↔copilot byte 検査に `engine-validation-map.md` を追加。
- 就活はテストユーザー向けサブ機能のため LP/README 非掲載を継続。

### Note

- 版: plugin 1.9.0 → **1.10.0** / codex 1.8.0 → **1.9.0** / copilot 1.1.2 → **1.2.0** / marketplace 同期

## [1.9.0 / Codex 1.8.0 / copilot 1.1.2] - 2026-06-13

### Added — caw-events（就活イベント・募集情報カタログ スキル）

就活トラックに、**業界横断で多数企業のインターン・企業説明会・座談会・選考イベント・締切を「詳細に」収集**する新スキル `caw-events` を追加。当初追加した締切特化の caw-deadlines を昇華し、締切だけでなくイベントの中身まで集める上位版に統合（caw-deadlines は本リリースで caw-events に置き換え）。

- 業界 or 企業リストを受け、**インターン/オープンカンパニー/説明会/座談会/本選考**を、各イベントの中身（テーマ・職種別コース・形式・対象・締切・実施日・優遇/早期選考・本選考直結・報酬・選考有無・口コミ/倍率）まで収集 → `recruit/<業界>.md`（1 イベント=1 ブロックのカタログ）と `recruit/<業界>.html`（**①イベントカタログ ②締切カレンダー ③企業×イベント比較表** の 3 ビュー）にまとめ、`secretary/todos/` の選考スケジュールへ連携。
- **出典方針**：公式採用ページを一次情報に、ナビ/就活サイトは出典併記の補助。**口コミ・倍率などの非公式は複数ソースで裏取り**。**ログイン必須・未公表は捏造せず「要確認」に分離**、締切は**取得日を併記**し「最新は公式で確認」、**カバレッジ（取得イベント数・N/M 社・未取得社一覧）を honest に報告**。
- HTML は `caw-company` の可視化規約を継承（オフライン SVG / Chart.js 選択・見出し id と canvas id 別名・各カード/行に出典＋取得日・要確認は視覚区別）。
- 就活トラック専用（LP/README の公開スキル一覧には**非掲載**）。`job-hunting-departments.md` の作業ディレクトリ表・運営ディスパッチに `recruit/`・`caw-events` を登録（3 系統 byte 一致）。
- 配信：plugin + codex（copilot は caw-events スキル未収載・共有リファレンスのみ同期）。

### Note

- 版: plugin 1.8.1 → **1.9.0** / codex 1.7.1 → **1.8.0** / copilot 1.1.1 → **1.1.2**（参照同期）/ marketplace 同期。1.9.0 は未リリースのため、当初の caw-deadlines は本エントリで caw-events に統合し版番号は据え置き。

## [1.8.1 / Codex 1.7.1] - 2026-06-13

### Changed — caw-company の出典・正確性ルール強化

企業研究の情報の正確性を担保するため、`caw-company` に**出典強度の使い分け**を明文化した。

- **Step 2「出典の取り方」を追加**：情報を公式／非公式で区別。**公式情報（IR・有価証券報告書・採用ページ＝財務指標・初任給・募集要項・平均年収の有報記載値）は単一の一次出典で可**。**非公式情報（年代別年収カーブ・職種別年収・残業・有給取得率・口コミスコア・離職率・採用大学/倍率、競合他社の年収など「他社」の非公式値）は 2 つ以上の独立ソースで突き合わせて裏取り**する。
- 値が割れたら単一値に丸めず**幅（約 X〜Y）／年度・基準を併記**（出典差に見えて実は年度差のことが多い）。口コミ由来は「**クチコミ集計値**」と明示。独立 2 ソースが取れなければ「**要確認**」。
- **HTML 可視化の注意も更新**：各セクションに出典リンクを併記し、公式は単一・非公式は複数リンクを `公式 / 非公式（複数で裏取り）` ラベルで区別。冒頭に出典方針ノートを置く。グラフは**見出しアンカー id と `<canvas id>` を別名**にする（衝突でグラフが空になる罠を明記、canvas は `ch` 接頭辞推奨）。
- plugin + codex 両配信に同一反映（copilot は caw-company 未収載のため据え置き）。

### Note

- 版: plugin 1.8.0 → **1.8.1** / codex 1.7.0 → **1.7.1** / marketplace 同期（copilot 1.1.1 据え置き）

## [1.8.0 / Codex 1.7.0] - 2026-06-12

### Added — caw-company に HTML 可視化

`caw-company`（企業・業界研究）を拡張し、`companies/*.md` に集めた情報を **ブラウザで開ける HTML** に可視化できるようにした。

- **3 ビュー**: 企業プロファイル（1社、`companies/<企業>.html`）／企業比較（複数社、`companies/_compare.html`、比較テーブル + 属性チャート + 選考スケジュール timeline）／業界ポジショニングマップ（`companies/_industry/<業界>.html`、2 軸散布図）
- **チャートは 2 方式に対応し、実行時に `AskUserQuestion` で選択**: ①オフライン自己完結（インライン SVG + CSS、ネット不要・ダブルクリックで確実に開く・推奨）②Chart.js（CDN、リッチだがネット必要）
- 製品 Web と統一したクリーンな配色（白基調 + インク + コーラル）。雛形（SVG 横棒・Chart.js レーダー）を skill に同梱
- ガードレール: `companies/*.md` の事実のみ・数値の捏造禁止・推定値は「推定」明記・個人情報/非公開情報は HTML に書かない
- caw-company は plugin + codex 配信（copilot は PoC で未収載）

### Note

- 版: plugin 1.7.1 → **1.8.0** / codex 1.6.1 → **1.7.0** / marketplace 同期（copilot 1.1.1 据え置き）

## [1.7.1 / Codex 1.6.1 / copilot 1.1.1] - 2026-06-12

### Added — caw-doctor の就活トラック診断

- **就活ルート設定に `> トラック: 就活` マーカー**を書くようにし（`job-hunting-departments.md` §B-1）、`caw-doctor` がこれを読んでトラックを自動判定するようにした
- **`caw-doctor` に §0 トラック判定 + §J 就活トラックの検査**を追加：就活なら研究向けの §5（Playbook）・§6/§6b（計算ソフト・研究成果物）をスキップし、就活部署（company-research / self-analysis / documents / interview）の設定ファイル、成果物フォルダ（`companies/` `documents/` `self-analysis/` `interview-prep/`）、`documents/inbox/`・START HERE の存在を点検
- caw-doctor は plugin + codex 配信（copilot は PoC で caw-doctor 未収載）。`> トラック` マーカーは 3 系統の job-hunting テンプレに追加

### Note

- 版: plugin 1.7.0 → **1.7.1** / codex 1.6.0 → **1.6.1** / copilot 1.1.0 → **1.1.1** / marketplace 同期

## [1.7.0 / Codex 1.6.0] - 2026-06-12

### Added — 就活専用スキル 3 本

就活モードの高頻度・多段タスクを専用スキル化（部署 + 運営モードでも動くが、一定品質で回すため）。

- **`/caw-es`** — ES・履歴書・職務経歴書・志望動機・自己PR ジェネレータ。企業の設問＋文字数を受け、
  `self-analysis/` の素材と `companies/` の志望理由から **文字数厳守・結論先出し・STAR 構造**のドラフトを生成。
  設問タイプ別の型（ガクチカ／志望動機／自己PR／強み弱み）を内蔵、`documents/inbox/` の過去 ES で文体を踏襲
- **`/caw-interview`** — 面接対策・模擬面接。想定問答生成 →「質問→回答→深掘り→改善フィードバック」の模擬面接
  ループ → 逆質問準備 → `interview-prep/<企業>.md` への振り返り記録（次回へ学びを引き継ぐ）
- **`/caw-company`** — 企業・業界研究。採用ページ・IR・ニュースを調べ `companies/<企業>.md` に構造化
  （web 検索／MCP 前提、無ければ貼り付けフォールバック）。志望動機の素材を抽出して caw-es に橋渡し

各スキルは **はじめてモード**を尊重（用語に 1 行説明・次の 1 手提示）し、**文字数厳守・誇張/虚偽禁止・
個人情報のローカル保持**を遵守。成果物は top-level（`documents/` `interview-prep/` `companies/`）に置く。

### Note

- 配信は **plugin + codex**（就活モードの主軸）。copilot（PoC）への追加は後追い（据え置き 1.1.0）
- 版: plugin 1.6.0 → **1.7.0** / codex 1.5.0 → **1.6.0** / marketplace 同期
- 就活はテストユーザー専用のため、**LP・plugin README の公開スキル一覧には掲載しない**（研究プロダクトのブランドを維持）

## [1.6.0 / Codex 1.5.0 / copilot 1.1.0] - 2026-06-12

### Added — 就活モード（テストユーザー拡大）

caw に **就活トラック**を追加。研究プロジェクトと並ぶ第 2 トラックとして、新卒就活生（学部・修士・博士・既卒）が
自己分析・企業研究・ES・面接準備・選考スケジュール管理に使えるようにした。

- **オンボーディングにトラック選択（Call T）を追加**: 起動時に「研究プロジェクト / 就活」を選ぶ。就活を選ぶと
  就活専用のオンボーディング・scaffold・運営モードに分岐（研究フローは無変更）
- **就活モードの全仕様を 1 参照ファイルに集約**（`references/job-hunting-departments.md`）: 就活プロファイルのヒアリング
  （区分・志望業界・就活フェーズ）／5 部署テンプレ（秘書〔選考スケジュール管理〕・企業/業界研究部・自己分析部・
  書類部〔ES/履歴書〕・面接対策部）／就活の作業ディレクトリ（`companies/` `documents/` `self-analysis/`
  `interview-prep/`）／START HERE（就活版）／運営モードの就活ディスパッチ
- 文字数制約厳守・誇張禁止・個人情報のローカル保持・はじめてモードでの用語説明を就活モードの遵守事項に明記
- plugin / codex / copilot の 3 系統に配信（codex/copilot は AGENTS.md 表記）

### Note

- plugin 1.5.3 → **1.6.0** / codex 1.4.3 → **1.5.0** / copilot 1.0.1 → **1.1.0** / marketplace 同期
- 研究トラックは無変更。Web LP への就活モード掲載は、化学ブランド（SPRING）の位置づけ判断が絡むため保留（テスターには直接案内）
- 次の拡張候補: 就活専用スキル（ES ドラフト `caw-es`）、caw-doctor の就活構造診断、過去 ES 取り込み（`documents/inbox/`）

## [1.5.3 / Codex 1.4.3 / copilot 1.0.1] - 2026-06-12

プロジェクト全体監査（4 観点並列）で見つかった不整合・陳腐化の一括修正。

### Fixed

- **スライド出力パスの矛盾を解消（実害バグ）**: `caw/SKILL.md` だけが `slides/` を案内し、生成側 `caw-slides` と部署テンプレ `chemistry-departments` は `presentations/slides/` を使っていた。outlier の `caw/SKILL.md` を多数派（`presentations/slides/` + スクリプトは `.company/presentation/scripts/`）に統一（plugin / codex / copilot の 3 系統）。`caw-doctor` の期待パス・旧構造移行先も追従
- **`plugin/README.md` の版数 v1.3.1 → v1.5.2 表記、`caw-slides` の記載漏れを修正**（スキル一覧とプラグイン構成ツリーに追加）
- **Web `plugin.md` の陳腐化を修正**: 「現バージョン v1.1.0」→ CLI 別の版テーブル（1.5.2 / 1.4.2 / 1.0.0）、Skills 7 件を完全列挙（caw-doctor / caw-setup / caw-slides を追加）、Hooks に PostToolUse 追記、Phase 表の同日重複を修正、ステータス更新

### Changed

- **Web に GitHub Copilot CLI を反映**: `requirements.md`・`beginner.md` の対応 CLI に追加、インストール手順に `npm install -g @github/copilot`（Node 22+）を併記、関連リンク追加
- **codex / copilot の `chemistry-departments.md` を `CLAUDE.md` → `AGENTS.md` に統一**（AGENTS.md ターゲットとの不一致を解消。plugin 版は CLAUDE.md のまま）
- **「はじめてモード」を `caw-paper` / `caw-input` / `caw-playbook` でも尊重**（plugin / codex）: 各スキル冒頭で `> 運用モード: はじめて` フラグを読み、平易な日本語・用語の 1 行説明・次の 1 手提示を適用
- **`caw-doctor` の診断を拡充**: 初心者向け投入フォルダ（`inbox/` / `_past-data/` / `papers/inbox/`）と START HERE 文書の存在チェックを追加
- **setup スクリプト（`.sh` / `.ps1`）に代替 AI CLI の案内を追加**: Claude Code を既定（Tier 1）のまま、Codex CLI / GitHub Copilot CLI の検出と導入コマンドを表示

### Infra

- **`scripts/check-consistency.sh`**: codex↔copilot の共有テンプレ（`agents-md-template.md` / `playbook-starters.md`）の byte 一致検査を追加
- **GitHub Actions CI を追加**（`.github/workflows/consistency.yml`）: push / PR で `check-consistency.sh` と Web ビルドを自動実行

### Note

- plugin 1.5.2 → **1.5.3** / codex 1.4.2 → **1.4.3** / copilot 1.0.0 → **1.0.1** / marketplace 同期

## [copilot-plugin 1.0.0 + Web] - 2026-06-04

### Added — GitHub Copilot CLI 対応（PoC）

- `copilot-plugin/` 新設：GitHub Copilot CLI 版 caw（`plugin.json` + 2 スキル `caw` / `caw-setup`、`caw` は `references/` 同梱）。Codex CLI 版（AGENTS.md ターゲット）から **CLI 固有箇所のみ**翻訳（起動コマンド `copilot`、MCP は `.mcp.json` 標準 `mcpServers` 形式）
- `.github/plugin/marketplace.json`：Copilot マーケットプレイス定義（`source: ./copilot-plugin`、登録は `copilot plugin marketplace add dr-neoueda/chemist-ai-workflow`）
- `docs/copilot-compatibility.md`：互換性アセスメント。GitHub Copilot CLI が caw のプリミティブ（AGENTS.md/CLAUDE.md 読込・`SKILL.md`・custom agents・**hooks は同名ライフサイクル**・MCP・plugin+marketplace 配布）を同型サポートする根拠と出典、移植コスト、対象外（M365 / Copilot Studio / 消費者 Copilot）を整理
- Web：補助ティアに「GitHub Copilot CLI（PoC 実証済）」を追加（`web/src/content/docs/copilot-cli/`、sidebar、splash の LinkCard + CLI 中立セクションの文言を補助 3 本に更新）
- `scripts/check-consistency.sh`：copilot-plugin の版表示 + 個人化リークスキャン対象に `copilot-plugin` / `.github/plugin` を追加

### Note

- plugin（Claude）1.5.2 / codex-plugin 1.4.2 は**無変更**。本リリースは新トラック **copilot-plugin 1.0.0** + Web + docs の追加
- PoC 簡略化：部署テンプレ見出しの `CLAUDE.md` 表記は据え置き（Copilot は `AGENTS.md`/`CLAUDE.md` 両読みのため機能上問題なし）。フルポート（残りスキル `caw-slides`/`caw-paper` 等・`hooks.json`・`.mcp.json`・実機動作確認）は Phase 2 検討

## [1.5.2 / Codex 1.4.2] - 2026-05-29

### Added — 初回ツアーの「サンプル PDF」フォールバック

- 初回ツアーの論文登録ステップで、手元に PDF が無いユーザー向けに **matplotlib で 1 枚のラベル付きサンプル PDF を生成**（`papers/inbox/caw-sample.pdf`、先頭に「練習用サンプル（削除可）」明記）→ 登録フローを体験 → 確認のうえ削除、という導線を追加。偽の論文をリポジトリに同梱せず、その場で生成して環境を汚さない。plugin / codex 両方
- バージョン: plugin 1.5.1 → 1.5.2 / codex-plugin 1.4.1 → 1.4.2 / marketplace 同期

### Web — Airtable テーマの仕上げ

- splash hero タイトルが白地に白文字で消えていた不具合を修正（`--sl-color-white` / `--sl-color-black` の上書きを削除。Starlight ではこれらは「高/低コントラスト」セマンティクスで literal 色ではない）
- favicon を Airtable パレットの化学フラスコアイコンに刷新（`web/public/favicon.svg`）
- ソーシャルカード（OGP）を追加：`web/public/og-default.png`（1200×630、白キャンバス + インク見出し + コーラルのフラスコ）と `og:image` / `twitter:card=summary_large_image` メタ

### Repo — 整合性チェックスクリプト

- `scripts/check-consistency.sh` を追加：plugin↔marketplace のバージョン一致、plugin↔codex の `caw-slides` references/templates の byte 一致、配布ツリーの個人化リーク（固有名詞）を一括検査。手作業ミラーの取りこぼし防止（CI 利用可）

## [1.5.1 / Codex 1.4.1] - 2026-05-27

### Changed — オンボーディング最初の質問を「経験レベルを率直に尋ねる」形に

- Q0（セットアップモード選択）を「どこまで詳しくやりますか？」から **「パソコンのターミナルや AI エージェントを使うのは初めてですか？」** へ言い換え。「はい、初めて」を先頭に強調し、Quick/Standard/Advanced の語が分からない初心者を取りこぼさないようにした（内部モード名は不変）。plugin / codex 両方
- バージョン: plugin 1.5.0 → 1.5.1 / codex-plugin 1.4.0 → 1.4.1 / marketplace 同期

## [1.5.0 / Codex 1.4.0] - 2026-05-27

### Added — 初心者向け初期環境（投入フォルダ・過去データ取り込み・自動インストーラ）

パソコン操作初心者に寄り添うオンボーディングへ拡張。

- **投入フォルダの自動生成**（caw scaffold）: 各計算ソフトディレクトリに `inbox/`（これから計算する入力の置き場）と `_past-data/`（過去の入出力の置き場）、research に `papers/inbox/`（PDF の置き場）を、平易な README 付きで生成。「どこに何を置くか」で迷わせない
- **過去データ一括取り込み**（caw-playbook 拡張）: `_past-data/` の過去入出力を解析し、よく使う汎関数・基底・収束設定・頻出エラーを Playbook の `## Lessons Learned` に初期 seed → その人向けに最適化
- **`caw-setup` スキル（新規）**: 外部ツール（Python・poppler・python-pptx 等）の不足を検出し、計画提示 → 一度の承認 → 順番にインストール（macOS / Windows、冪等、sudo 不使用、失敗継続）
- **bootstrap スクリプト（新規）**: `setup/caw-setup.sh`（macOS / Homebrew）・`setup/caw-setup.ps1`（Windows / winget + Scoop）。CLI・Node・git まで含めて導入（鶏卵問題対応）。同じ「計画提示 → 一括」方式
- README（plugin / codex）に caw-setup と過去データ取り込みを追記

### Added — 初心者を強めに誘導する仕組み

ターミナル・IDE・AI が初めての人を最初は強めに手引きする。

- **「はじめて」モード**（onboarding Call 0 の 4 つ目）: `.company/CLAUDE.md`（codex は AGENTS.md）に `> 運用モード: はじめて` を記録。運営モードが平易語・専門用語の 1 行説明・毎回「次はこれ」提示・不可逆操作の事前確認・コピペコマンド明示を全応答で適用
- **ガイド付き初回ツアー**（scaffold 後）: 「一緒に最初の 1 件をやってみましょう」で TODO / 論文登録 / 計算入力のいずれかを手取り足取り
- **START HERE 文書**: プロジェクト直下に `はじめにお読みください.md` を生成（これは何 / まず何をするか / 言い方早見表 / フォルダの意味 / 用語ミニ辞典 / 困ったとき）
- **用語ヘルプ + ターミナル/IDE 導入案内**: 「〇〇って何?」に平易に即答する運営ルール + Web 新ページ「はじめての方へ（ターミナル・IDE の基本）」（VS Code 導入・ターミナルの開き方・最初の起動・用語表）
- バージョン: plugin 1.4.5 → 1.5.0 / codex-plugin 1.3.5 → 1.4.0 / marketplace 同期（新スキル追加のため minor）

## [1.4.5 / Codex 1.3.5] - 2026-05-21

### Added — showcase（宣伝・紹介・募集）variant（実デッキ添削からの学び）

ユーザーが手で添削した宣伝デッキを手本に、研究発表用 4 variant とは設計思想の異なる
「実スクリーンショット主役のコラージュ型」を 5 つ目の用途バリアントとして追加。

- **`templates/generate_showcase.py`**（新規・5-8 枚）: 概念（プログラムヘッダ + ツール名サブ行 + ヒーロー図 + 説明カード2枚 + 動作環境ロゴ）／メイン機能（俯瞰図 + カード + 機能図2枚）／使用例（スクショ・コラージュ + キャプション画像上 + アプリロゴクラスタ）／募集（CTA）。個人化なし・全 `<...>` プレースホルダ。画像未挿入でもラベル箱で実行可
- **`pptx_helpers.py` に showcase helper 3 種**: `add_context_header`（プログラムヘッダ + ツール名サブ行）／`add_collage_caption`（画像上 2 行キャプション）／`add_logo_cluster`（アプリロゴを小さく等間隔・空リストは無描画）。いずれも `assert_no_overlap` 用 rect を返す
- **style-guide §15**（showcase レイアウト）: 研究発表 variant との差分表（タイトル＝プログラム名／実スクショ主役／コラージュ密度／キャプション画像上／アプリロゴ／§0 緩和／用語一般化）、helper 早見、配布物の個人化禁止
- **SKILL.md**: 用途バリアント 4→5、同梱資産に generate_showcase.py を追記（plugin / codex 両 SKILL.md）
- PR ループ: python-reviewer → codex（記録: `~/lab/.company/review/code-reviews/2026-05-21-showcase-template.md`）
- バージョン: plugin 1.4.4 → 1.4.5 / codex-plugin 1.3.4 → 1.3.5 / marketplace 同期

## [1.4.4 / Codex 1.3.4] - 2026-05-21

### Changed — フォント階層の固定化 + イラスト文字の本文スケール化（蛍デッキ反復の学び）

子供実験教室「ホタルの発光」デッキをイラスト主体で作る一連の添削から、3 つの調整を caw-slides に恒久反映。

- **フォント階層を 3 段に固定**（style-guide §2 / §14-2 / §14-3）: タイトル 28pt / 強調=L1=重要本文 24pt / 本文 20pt。**key-message band（L1）は常に 24pt**。色も役割分担（navy=見出し / dark=本文 / blue=要点 / red=注意 / grey=補足）。§14-3 がこれまで header 21・body 16 で §2 と矛盾していたのを統一
- **4 テンプレ**（generate_conference/journal_club/lab_report/lecture）の font を新階層に: ▸ヘッダー 21→24 / 本文 16→20 / L1 band 20→24
- **`research_icons` のイラスト内文字を本文スケールに拡大 + アイコンへ近接**: `label` 既定 12→17 / `sublabel` 9→13、3 ビルダーの node/center ラベルも 17–18 に、ラベル位置をアイコン直下へ寄せた（離れた配置の「スカスカ感」を解消）
- **style-guide §11bis 品質ルール拡張**: 「アイコンとラベルは近接」「イラスト内文字も本文サイズ目安（fontsize 主 16–19 / 強調 22–24 / 補助 13–15）」「ドメイン特有アイコンは patches で自作可（材料＝登場人物）」を追加
- PR: python-reviewer（constant-tuning、回帰なし APPROVE。figure-lifecycle/guards 健在）。research_icons は 1.4.3 で codex 二段済・本変更は定数のみのため codex 再実行なし。記録: `~/lab/.company/review/code-reviews/2026-05-21-firefly-deck-and-falsepositive.md`
- バージョン: plugin 1.4.3 → 1.4.4 / codex-plugin 1.3.3 → 1.3.4 / marketplace 同期

## [1.4.3 / Codex 1.3.3] - 2026-05-20

### Added — 概念イラストモジュール `research_icons`

caw 宣伝デッキ等のイラスト作成を重ねて確立したノウハウを、再利用可能な配布
モジュールとして恒久化（references 層、`pptx_helpers` と同階層）。任意テーマの
スライドで同等品質の概念イラストを量産できる。

- **線画アイコン 10 種**（`icon_researcher` / `icon_flask` / `icon_molecule` /
  `icon_document` / `icon_chart` / `icon_slides` / `icon_gear` / `icon_magnifier` /
  `icon_laptop` / `icon_sparkle`）。共通シグネチャ `icon(ax, x, y, s=1.0, color=)`、
  同縮尺で混在可。`ICONS` 名前レジストリ付き。配色は `CATEGORICAL_HEX` に整合
- **構図ビルダー 3 種**（PNG パスを返す → `add_picture_fit` に渡す）:
  - `hub_diagram` — 中心 + 放射（部署図・構成要素）
  - `cycle_diagram` — 円環 + 駅間の隙間に弧矢印（研究サイクル。駅を貫かない）
  - `converging_diagram` — 周辺要素が中心へ収束（負荷が押し寄せる課題図。矢じりはリム着地）
- ヘルパ `label` / `sublabel` / `new_figure` / `save_figure`（ビルダーに無い構図を自作する用）
- **style-guide.md §11bis「概念イラスト（schematic）作成」を新設**: イラスト vs チャートの
  題材判断表（規模・桁比較は定量チャート、構成・サイクルはイラスト）、アイコンカタログ、
  3 ビルダーの使い方、品質ルール（矢印はリム/隙間着地・サブラベルで密度・等間隔等縮尺・
  背景は白基調で過度な装飾を避ける）。§14-6 早見表と SKILL.md にも追記
- PR ループ: python-reviewer（HIGH 1 = Figure リーク + MEDIUM 5 + LOW 2）→ codex-rescue
  二段（MEDIUM 2 = 高密度サイクルの弧反転・save 時クリーンアップ順序 + LOW 2）。全件対応。
  記録: `~/lab/.company/review/code-reviews/2026-05-20-research-icons.md`
- バージョン: plugin 1.4.2 → 1.4.3 / codex-plugin 1.3.2 → 1.3.3 / marketplace 同期

## [1.4.2 / Codex 1.3.2] - 2026-05-20

### Changed — カテゴリカル配色（青一色の解消）

CP2K 初学者向けデッキ生成の添削で「全体が青中心で単調」と判明。図表・グラフに識別・対比・強調のための複数色を導入。

- **`CATEGORICAL_HEX` / `CATEGORICAL_RGB`**: 青→橙→緑→赤→シアン→紫→アンバーの 7 色パレット
- **`add_bar_chart` / `add_scatter_line_chart`**: 系列をパレットで自動色分け（線 + マーカー）。マーカー着色は `show_markers` 時のみ
- **`add_data_table(highlight_row=N)`**: 推奨案 / hero 行を淡アンバー（`COLOR_ROW_HIGHLIGHT_FILL` #FFF2CC）で塗る。範囲外は ValueError
- **`add_energy_diagram`**: 状態を役割色（始=青 / 終=緑 / TS・中間体=赤）、connector はグレー。位置（山/谷）が意味を担うため赤緑 CVD でも判別可
- **style-guide.md §0 に「図表・グラフは青一色を避け、カテゴリカル配色」節**を追加（多系列はパレット巡回、テーブルは highlight_row、対比の鉄則は維持）
- PR ループ: python-reviewer（HIGH 1 + MEDIUM 1 + LOW 2 修正、show_markers ガード等）。codex-rescue は背景継続が時間内未完のため Claude + 自己評価で補完
- バージョン: plugin 1.4.1 → 1.4.2 / codex-plugin 1.3.1 → 1.3.2 / marketplace 同期

## [1.4.1 / Codex 1.3.1] - 2026-05-20

### Changed — caw-slides の「AI 作成感」除去（実デッキ添削 fb 反映）

MLIP 研究紹介デッキを caw-slides で生成し、その添削から得た改善を `pptx_helpers.py` と `style-guide.md` に反映。

- **表の空白圧縮（`add_data_table`）**: デフォルト `word_wrap=False`、header 行 = `header_size × 2.0` / body 行 = `font_size × 2.0` に分離（CJK headroom）、セル上下余白 3pt、`row_height=Emu(0)` を auto 扱い。4 行表が 0.9"/行(3.6") → 0.44"/行(1.78") に圧縮。`row_height` / `cell_margin` / `word_wrap` パラメータ追加（後方互換）
- **style-guide.md §0 に「表とまとめスライドの作り込み（AI 作成感の除去）」節を新設**:
  - 表は内容に密着（tight 行・全幅に伸ばさず中央寄せ）。埋めたいなら空白でなく情報を足す
  - まとめ/結語スライドにも必ず図を置く（positioning 図等）
  - **コンテンツスライドは「図・表・グラフ + L1 + 支持本文」を基本構成に**（図 + L1 だけのスパース構成を避ける。視覚要素が幅を埋めないなら左に視覚・右に支持本文の 2 ゾーン、横長テーブルは上に視覚・下に支持本文）
  - **「箱に文字を詰めた」text-box フロー図（`add_flow_box` × N）は原則作らない**。第一選択はプロセスの効果をグラフで示す（例 active learning → 学習曲線）、第二選択はイラスト/アイコン + 最小ラベル
  - 図表構成要素（フロー box・テーブル・split_2col）は §0 文字数上限の対象外（`assert_text_minimal` の override 指針）
- PR ループ: python-reviewer + codex-rescue。`add_data_table` 改修で HIGH 1（行高さ × word_wrap）+ MEDIUM 2（header/body 分離・CJK 余裕）+ LOW 2 を修正
- バージョン: plugin 1.4.0 → 1.4.1 / codex-plugin 1.3.0 → 1.3.1 / marketplace 同期

## [1.4.0 / Codex 1.3.0] - 2026-05-15

### Added — `caw-slides` Skill（PowerPoint スライド生成）

化学研究発表用 PowerPoint スライドを python-pptx ベースで生成する専用 Skill。実運用された 12 件のスライドから抽出したスタイルガイドを内蔵し、4 用途バリアントで「学会発表 / 論文紹介 / 報告会 / 講義」に対応する。

- **発火**: 自然言語マッチ（「スライド作って」「パワポ」「学会発表」「論文紹介」「報告会」「講義スライド」等）
- **同梱資産**（plugin / codex-plugin 並列配信）:
  - `references/pptx_helpers.py`（1000+ 行）: `add_slide_chrome` / `add_key_message_band` / `mixed_runs` / `assert_no_overlap` / `add_bar_chart` / `add_scatter_line_chart` / `add_flow_box` / `add_data_table` 等のヘルパ。MS Gothic のクロスプラットフォーム探索（macOS / Windows / Linux、`CAW_SLIDES_MSGOTHIC` 環境変数で override 可）
  - `references/style-guide.md`: 14 セクション + canonical 実装パターン（**§0 絶対ルール = 文字数を極限まで減らし図表で直感的に伝える**、16:9、フォント混在、L1 強調 1 個ルール、3 層 y 座標構造（chrome / 本文 / key-message band）、3 tier 強調 L1/L2/L4（L2 = 影なし・枠線あり・塗りなしの透明箱）、native chart 強制、座標 hygiene、出典は用途別に任意で `add_source_line`）
  - **§0 強制ヘルパ（実装済み）**: `assert_text_minimal(slide)` でテキストボックス数 ≤ 5 / 本文総行数 ≤ 12 / 1 ボックス内 ≤ 120 字を自動検証（違反は ValueError）; `assert_title_assertive(title)` で「結果」「考察」「方法」「目的」等の無味な見出しを lint（22 ワードの blacklist 内蔵）
  - **化学特化ヘルパ**: `add_molecule(slide, smiles)` — SMILES → RDKit Draw → PNG embed (lazy import); `add_reaction_scheme(slide, reactants, products, conditions)` — 反応式の横並び合成（reactant + reactant → product, conditions ラベル付き）; `add_energy_diagram(slide, levels, labels)` — 反応座標 vs エネルギーの 1 ライン図（matplotlib smoothstep、TS は短い dash で sharp peak 表現）
  - **レイアウトパターン**: `split_2col(slide, left_paragraphs, right_paragraphs)` — 2 カラム比較（Form I/II・before/after 等の概念対比受け皿）; `add_timeline(slide, milestones=[(date, event), ...])` — 横軸時系列バー（≤ 8 milestones、衝突 guard 付き）
  - **クロスプラットフォーム / 安全性**: matplotlib 日本語 lazy auto-config（`_ensure_matplotlib_japanese`、未検出時は `RuntimeWarning` で診断）; PNG temp file は `try/finally + os.unlink` で確実 cleanup（Windows の PIL 再オープン bug 対策含む）
  - `references/codex-exec-templates.md`: Codex 委譲 v2（完全お任せ）プロンプトテンプレ集
  - `templates/generate_conference.py`: 学会発表 variant（口頭・ポスター、20-50 枚）
  - `templates/generate_journal_club.py`: 論文紹介 variant（6-12 枚、pdftoppm + crop ワークフロー）
  - `templates/generate_lab_report.py`: 研究室報告会 variant（6-15 枚、native chart + table）
  - `templates/generate_lecture.py`: 講義・チュートリアル variant（15-30 枚、概念フロー図）
- **品質ゲート**: `assert_no_overlap` で shape 矩形交差を物理的に禁止（ValueError raise）、L1 1 個ルール、Excel-editable native chart のみ
- **動作確認**: 4 templates 全て smoke test 成功（標準的な 4 枚のデモ .pptx を生成、`assert_no_overlap` pass）

### Changed

- **`plugin/skills/caw/references/chemistry-departments.md`**: presentation 部の説明を caw-slides skill 利用前提に更新。サブディレクトリ列挙に `scripts/`, `notes/`, `references/` を追加、成果物パスを `slides/` → `presentations/slides/` に統一
- **`plugin/skills/caw/references/playbook-starters.md`**: 「計算外ソフトの Playbook」セクションを追加し、caw-slides との関係を明示
- **`web/src/content/docs/claude-code/application.md`**: §5 を caw-slides skill ベースに改稿（4 用途バリアント、共通スタイルガイド、`assert_no_overlap` 保証）
- `plugin/.claude-plugin/plugin.json` version 1.3.1 → 1.4.0
- `codex-plugin/.codex-plugin/plugin.json` version 1.2.1 → 1.3.0
- `.claude-plugin/marketplace.json` plugin 列挙の version 同期

### Notes

- スライド生成システムは元々ユーザーの `.company/presentation/` で実運用されていた成熟資産を caw plugin 化したもの。新規開発ではなく **配信パッケージング**として実装。個人情報（著者名・研究室名・特定研究テーマ・機器型番）はすべて除去済み
- Codex CLI 版（codex-plugin）も同一資産を並列配信。両 CLI で完全機能パリティ
- python-pptx の依存（`python-pptx`、`matplotlib`、`Pillow`）はユーザーが事前にインストール
- スタイルガイド本体（`references/style-guide.md`）はプラグイン更新で上書きされる。プロジェクト固有のオーバーライドは `.company/presentation/CLAUDE.md` (or AGENTS.md) に追加

## [1.3.1 / Codex 1.2.1] - 2026-05-14

### Fixed（B16 — Windows / Linux 対応）

- **`plugin/hooks/load-playbooks.sh`**：mtime 降順ソートを BSD/macOS 専用の `xargs -0 stat -f "%m %N"` から `ls -t`（macOS / Linux / WSL / Git Bash 共通の POSIX）に置換。これまで macOS 以外（Linux 含む）で直近ノートの注入が動いていなかったのを修正
- **`plugin/skills/caw-doctor/SKILL.md` / `codex-plugin/skills/caw-doctor/SKILL.md`**：Playbook の `last_updated` 経過日数計算を BSD/macOS 専用の `date -j -f` から、GNU `date -d` → BSD `date -j` フォールバックの `to_epoch` ヘルパーに置換。macOS 以外でも動作するように

### Changed

- **`.company/` の可視性に関する説明を OS 別に正確化**：「Finder / Explorer から不可視」という macOS/Linux 前提の表現を「macOS Finder / Linux のファイルマネージャでは標準で非表示、Windows Explorer では表示される（いずれの OS でも運営情報専用エリアという位置づけは同じ）」に修正。SKILL.md / claude-md-template / agents-md-template / chemistry-departments / output-location-check.sh / README
- **`plugin/README.md`**：「動作環境」節を追加（OS × コア/Hooks の対応表、Windows は WSL / Git Bash 必須の旨）。v1.1.0 のまま古かった Skills / Hooks / Playbook / プラグイン構造の記述を v1.3.1 の実態に更新
- `plugin/.claude-plugin/plugin.json` version 1.3.0 → 1.3.1
- `codex-plugin/.codex-plugin/plugin.json` version 1.2.0 → 1.2.1
- `.claude-plugin/marketplace.json` version 同期

### Notes

- caw のコア（オンボーディング・部署スキャフォールド・5 Skills のワークフロー）は元々 OS 非依存。今回の修正は **hooks と caw-doctor の bash スニペットに混入していた macOS 専用構文**（`stat -f` / `date -j`）の除去で、これらは Windows のみならず Linux でも壊れていた
- Windows でネイティブに hooks を動かすには WSL または Git Bash が必要（`hooks.json` が `bash` を呼ぶため）。コア機能は Windows ネイティブでも動作

## [1.3.0 / Codex 1.2.0] - 2026-05-14

### Added

- **B1 — Codex 版の Skills 機能パリティ**：`caw-paper` / `caw-input` / `caw-playbook` を `codex-plugin/skills/` に移植。Codex 流に合わせ `trigger:` フィールドを削除し、自然言語マッチで発火。CLAUDE.md → AGENTS.md 表記に変換。これで両プラグインとも 5 Skills（caw / caw-doctor / caw-paper / caw-input / caw-playbook）で揃った
- **B2 — `caw-doctor` Skill 新規追加**（Claude / Codex 両版）：`.company/` 構造の健全性チェック。ルート CLAUDE.md・秘書部・各部署 CLAUDE.md の存在確認、旧構造（成果物が `.company/<dept>/X/` に残存）の検出、Playbook 更新滞り、同日ファイル重複、inbox 孤立ファイルを総点検し、レポート + 修復コマンドを提示
- **B7 — Playbook 雛形を 8 件拡充**（Claude / Codex 両版）：計算ソフト 4 件（Psi4 / NAMD / LAMMPS / OpenMM）+ Python ライブラリ 4 件（RDKit / ASE / MDAnalysis / pymatgen）を `playbook-starters.md` に追加。Python ライブラリ Playbook は API quirks・version 依存挙動・よくある罠を体系化
- **B8 — MCP 自動セットアップ案内**（Claude / Codex 両版）：オンボーディング Step 3-5 で Q3（ナレッジベース）/ Q4（クラウドストレージ）の選択に応じて `.company/.mcp-setup.md` を生成。Notion / Obsidian / Logseq / Google Drive / Dropbox / OneDrive / Gmail の MCP 設定手順 + API key の環境変数管理ガイド。`references/mcp-setup-templates.md` を新規追加。**鍵そのものは書かず手順書のみ**
- **B10 — オンボーディングの 3 段階化**（Claude / Codex 両版）：Step 2 に「セットアップモード」選択（Call 0）を追加。Quick（1 問・秘書のみ即起動）/ Standard（現行 6 問）/ Advanced（10+ 問、HPC・研究体制・申請書予定・論文ステータスまでヒアリング）
- **B11 — PostToolUse hook で二層原則違反を検出**（Claude Code 版のみ）：`plugin/hooks/output-location-check.sh` を追加。Edit/Write/MultiEdit が `.company/<dept>/<旧パス>/` に書き込んだ時に警告 + 修復コマンドを提示（block はしない warn-only）。`hooks.json` に PostToolUse エントリを追加。Codex 版は hook framework が未整備のため未対応

### Changed

- **`plugin/skills/caw/SKILL.md` / `codex-plugin/skills/caw/SKILL.md`**：Step 2 を 3 段階モード化、Step 3 に MCP セットアップ生成（3-5）を追加し完了メッセージを 3-6 にリネーム、「ファイル参照」に `mcp-setup-templates.md` を追加
- **`plugin/skills/caw/SKILL.md` / `codex-plugin/skills/caw/SKILL.md`**：オンボーディング Q2（計算ソフト）の古典 MD 例示に NAMD / OpenMM を追記（B7 と整合）
- `plugin/.claude-plugin/plugin.json` version 1.2.0 → 1.3.0
- `codex-plugin/.codex-plugin/plugin.json` version 1.1.0 → 1.2.0
- `.claude-plugin/marketplace.json` version 同期

### Notes

- Codex 版は hooks 非対応（B11 のみ Claude Code 限定）。それ以外（B1/B2/B7/B8/B10）は両プラグインで機能等価
- caw-doctor は v1.2 の二層原則 migration 状況の点検にも使える（旧構造を検出して移行コマンドを提示）

## [1.2.0 / Codex 1.1.0] - 2026-05-14

### Added

- **成果物配置の二層原則（CRITICAL）**：caw の出力ファイルを `.company/` 配下（運営情報）と project root 直下（成果物）に明確に二層化
  - 第 1 層 `.company/<dept>/` = 運営情報のみ（TODO・意思決定・学び・Playbook・内部レビュー）
  - 第 2 層 project root = 成果物（`papers/`, `topics/`, `manuscripts/`, `slides/`, `analyses/`, `notebooks/`, `figures/`, `scripts/`, `tools/`, `reports/`, `experiments/`, `gaussian/` 等）
  - `.company/` は dotfile で Finder / Explorer から不可視。AI が生成した md / pptx / docx / png / ipynb 等を `.company/<dept>/` に置くと **ユーザーがファイラーで見つけられない** という v1.0 / v1.1 の構造的問題を解消

### Changed

- **`plugin/skills/caw/SKILL.md`**：「成果物配置の二層原則」セクションを追加。Step 3-4 の作業ディレクトリ生成リストを拡張（research → `papers/` + `topics/`、analysis → `analyses/` + `notebooks/` + `figures/`、engineering → `scripts/` + `tools/`、presentation → `slides/`）
- **`plugin/skills/caw/references/chemistry-departments.md`**：research / engineering / analysis / writing / presentation の各 CLAUDE.md テンプレで出力パスを `.company/<dept>/X/` から `{{PROJECT_ROOT}}/X/` に変更
- **`plugin/skills/caw/references/claude-md-template.md`**：ルート CLAUDE.md にも二層原則を明文化
- **`codex-plugin/skills/caw/SKILL.md`**：同上（AGENTS.md 表記）
- **`codex-plugin/skills/caw/references/agents-md-template.md`**：同上
- **`codex-plugin/skills/caw/references/chemistry-departments.md`**：同上
- `plugin/.claude-plugin/plugin.json` version 1.1.0 → 1.2.0
- `codex-plugin/.codex-plugin/plugin.json` version 1.0.0 → 1.1.0
- `marketplace.json` version 同期

### Migration（v1.0 / v1.1 → v1.2 / Codex 1.0 → 1.1）

既存ユーザーが旧構造（`.company/research/papers/`, `.company/writing/manuscripts/`, `.company/analysis/results/`, `.company/presentation/slides/`）に成果物を蓄積している場合、以下を手動で実施：

```bash
# 移動例（既存ファイルがある場合のみ実行）
mv .company/research/papers/* papers/ 2>/dev/null
mv .company/research/topics/* topics/ 2>/dev/null
mv .company/writing/manuscripts/* manuscripts/ 2>/dev/null
mv .company/analysis/results/* analyses/ 2>/dev/null
mv .company/analysis/figures/* figures/ 2>/dev/null
mv .company/analysis/notebooks/* notebooks/ 2>/dev/null
mv .company/presentation/slides/* slides/ 2>/dev/null
```

`.company/<dept>/` 配下に残った空ディレクトリ（`papers/` `manuscripts/` 等）は削除して構わない。残しても害は無い（caw が読みに行かなくなるだけ）。

将来 v1.3 で `caw-migrate` Skill を追加予定（自動移動 + 衝突解決 + dry-run）。

## [Codex 1.0.0] - 2026-05-13

### Added (Codex CLI 版)

- **codex-plugin/**：Codex CLI 用 caw プラグイン（v1.0.0）を新規追加
  - `codex-plugin/.codex-plugin/plugin.json` — Codex 用プラグインマニフェスト
  - `codex-plugin/skills/caw/SKILL.md` — `/caw` スキル本体（CLAUDE.md → AGENTS.md ターゲットに変換）
  - `codex-plugin/skills/caw/references/{agents-md-template, chemistry-departments, playbook-starters}.md`
- **`.agents/plugins/marketplace.json`**：Codex 用マーケットプレイス manifest（同リポジトリから並列配信）
- **LP**：`/codex-cli/` セクションを placeholder から実装に書き換え、`/codex-cli/setup/` 環境構築ページを新規作成
- **plugin.md**：両環境のインストール手順（Claude Code / Codex CLI）を併記

研究室で Claude Code 派と Codex CLI 派が混在しても、同じ caw メソッドで `.company/` を運用できる構成。

## [1.1.0] - 2026-05-13

### Added

- **Hooks**：SessionStart で `.company/secretary/notes` の直近 3 件と利用可能 Playbook をコンテキスト自動注入、Stop で今日の活動があるのに learnings.md が無い場合にリマインド。
- **`/caw-paper` スキル**：論文検索（arXiv / Crossref / Semantic Scholar / OpenAlex / PubMed）と入手済み PDF の自動メタデータ抽出 → ナレッジベース（Notion / Obsidian / Logseq 等）+ クラウドストレージ（Google Drive 他）への登録。バッチ処理対応。
- **`/caw-input` スキル**：6 ソフト（Gaussian / ORCA / CP2K / GROMACS / VASP / Quantum ESPRESSO）の入力ファイル雛形生成。Playbook デフォルト推奨値を起点に対話的に系・目的・計算条件を確定、`<tool>/<system>_<purpose>_<YYYYMMDD>/` 配下に配置 + ジョブ記録自動生成。
- **`/caw-playbook` スキル**：計算 log の自動解析（収束 / エラー / 異常パターン）→ Lessons Learned エントリ起案 → Playbook への末尾追記。memory feedback への昇格判定も含む。

### Changed

- `plugin.json` version 1.0.0 → 1.1.0（後方互換のスキル追加）。
- `marketplace.json` version 同期。

## [1.0.0] - 2026-05-13

### Added

- 初回公開。caw プラグイン（Chemist's AI Workflow）。
- `/caw` スキル：オンボーディング → 自動スキャフォールド → 運営モードの一連を実装。
- 化学者向け 8 部署 CLAUDE.md テンプレート（secretary / research / engineering / computation / analysis / writing / review / presentation）。
- 計算ソフト Playbook 雛形：Gaussian / GROMACS / CP2K / ORCA / VASP / Quantum ESPRESSO + 汎用。
- 作業ディレクトリの自動生成：選択した計算ソフトに応じて `gaussian/` / `orca/` 等、選択した部署に応じて `papers/` / `manuscripts/` / `slides/`。
- ローカル marketplace 経由の開発・テスト環境。
- 4 つのテストプロファイルでの実機検証完了。

### Documentation

- 配布マーケットプレイスの `.claude-plugin/marketplace.json` を整備。
- MIT ライセンス採用。
- Chemist's AI Workflow LP（Astro Starlight）。
