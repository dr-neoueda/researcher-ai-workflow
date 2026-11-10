#!/usr/bin/env python3
"""raw project scaffolder — build office/ + work/ from shipped templates.

Onboarding (raw SKILL Step 3) otherwise Write-s ~40 files; every Write costs
output tokens equal to the file body. This script does the deterministic bulk
(9 department CLAUDE.md, root office/CLAUDE.md, per-tool playbooks, folder
READMEs, .mcp-setup.md, first todo, integrated inbox) by copying and
substituting the skill's shipped reference files, so the model only writes a
small config JSON + the tiny work/profile/ personalization.

Design: the reference files are already section-structured, so we parse rather
than ship duplicate templates:
  - research-departments.md  : ``### <path>`` + fenced block -> office/<path>
  - claude-md-template.md    : first fenced body -> office/CLAUDE.md
  - field-rules.md           : ``### field = <group>`` fence -> {{FIELD_RULES}}
  - playbook-starters.md     : ``### computation/playbooks/<tool>.md`` block
  - mcp-setup-templates.md   : header fence + ``### Q3/Q4 = <choice>`` fences
Folder READMEs are short, so they live here as templates.

Safety (hardened after adversarial review):
  - all written paths are validated + confined under --out (no traversal)
  - tool names are slugified and charset-checked before use in paths
  - fence parsing is fail-closed (unterminated fence -> ValueError)
  - any ``{{TOKEN}}`` left in a generated file is a hard error
  - an unknown ``field_group`` stops before anything is written
  - mutable files (playbooks, first todo) are never overwritten, even --force

Usage:
    python3 scaffold.py --config <config.json> --skill <SKILL_DIR> --out <PROJECT_DIR>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any

# --- static data (all-9-department research track; matches claude-md-template.md) ---

DEPARTMENT_TREE = "\n".join(
    [
        "├── research/",
        "├── engineering/",
        "├── computation/",
        "├── experiment/",
        "├── analysis/",
        "├── writing/",
        "├── review/",
        "└── presentation/",
    ]
)

DEPARTMENT_TABLE_ROWS = "\n".join(
    [
        "| 文献部 | research | 文献検索、要約、ナレッジ DB 化 |",
        "| 開発部 | engineering | Python ツール、計算入力ジェネレータ、CLI |",
        "| 計算管理部 | computation | 計算ジョブの管理（量子化学・MD・FEM・数値計算 等）+ Playbook |",
        "| 実験部 | experiment | 実験の段取り・電子ノート・試料/試薬の在庫・安全 |",
        "| データ解析部 | analysis | 手法非依存の解析コンパニオン（fit・定量・可視化） |",
        "| 論文執筆部 | writing | LaTeX / Word 原稿、図表、参考文献 |",
        "| レビュー部 | review | コード品質、計算妥当性の確認 |",
        "| プレゼン部 | presentation | スライド生成（SVG-first → native pptx） |",
    ]
)

# tool slug -> (work dir name, main input/output extensions shown in README)
TOOL_DIRS: dict[str, tuple[str, str]] = {
    "gaussian": ("gaussian", "`.gjf` 入力、`.log`/`.chk`/`.fchk` 出力、`run_*.sh`"),
    "gromacs": ("gromacs", "`.gro`/`.top`/`.itp`/`.mdp`/`.ndx`/`.tpr`/`.xtc`/`.edr`"),
    "cp2k": ("cp2k", "`.inp` 入力、`.out`/`.restart`/`.ener`/`.pos` 出力"),
    "orca": ("orca", "`.inp` 入力、`.out`/`.gbw` 出力"),
    "vasp": ("vasp", "`INCAR`/`POSCAR`/`KPOINTS`/`POTCAR`、`OUTCAR`/`CHGCAR`/`vasprun.xml`"),
    "quantum-espresso": ("quantum-espresso", "`.in` 入力、`.out` 出力、`*.UPF` 擬ポテンシャル"),
    "mlip": ("mlip", "学習データ、`.model` チェックポイント、評価 trajectory"),
    "chimerax": ("chimerax", "`.cxc`/`.py` スクリプト、PDB/mmCIF、`.mrc`/`.map`、`.cxs` セッション"),
    "psi4": ("psi4", "`.dat`/`.in` 入力、`.out` 出力、`.fchk`/`.molden`"),
    "amber": ("amber", "`.prmtop`/`.inpcrd`/`.mdin` 入力、`.mdout`/`.nc`/`.rst` 出力"),
    "namd": ("namd", "`.conf`/`.namd` 入力、`.psf`/`.pdb`、`.dcd`、`.log`"),
    "lammps": ("lammps", "`in.*` 入力、`data.*`、`.dump`/`.lammpstrj`、`log.lammps`"),
    "openmm": ("openmm", "Python(`.py`) スクリプト、`.pdb`/`.xml`、`.dcd`"),
    # outside chemistry: the tools offered in onboarding Call 4
    "pymol": ("pymol", "`.pml`/`.py` スクリプト、PDB/mmCIF、`.pse` セッション"),
    "alphafold": ("alphafold", "`.fasta` 入力、`ranked_*.pdb`、信頼度（pLDDT・PAE）の `.pkl`/`.json`"),
    "colabfold": ("colabfold", "`.fasta`/`.a3m` 入力、`*_rank_*.pdb`、`*_scores_*.json`"),
    "blast": ("blast", "`.fasta` クエリ、BLAST データベース、`-outfmt 6` の表"),
    "r": ("r", "`.R`/`.Rmd`/`.qmd` スクリプト、`.rds` データ、`renv.lock`"),
    "openfoam": ("openfoam", "ケース（`0/`・`constant/`・`system/`）、`log.*`、時刻ごとの結果ディレクトリ"),
    "comsol": ("comsol", "`.mph` モデル、バッチ実行のログ、書き出した `.csv`/`.txt`"),
    "ansys": ("ansys", "APDL の `.inp`/`.dat`・journal `.jou`、`.out`/`.rst` 出力"),
    "matlab": ("matlab", "`.m` スクリプト・関数、`.mat` データ"),
    "julia": ("julia", "`.jl` スクリプト、`Project.toml`/`Manifest.toml`"),
    "pytorch": ("pytorch", "`.py` 学習スクリプト、`.pt` チェックポイント、学習ログ"),
}

# always-created domain work dirs -> README one-liner
DOMAIN_DIRS: dict[str, str] = {
    "papers": "`pdf/`＝原本 PDF ／ `md/`＝文献要約。PDF を `pdf/` に入れて「登録して」で `raw-register` が書誌付き要約を `md/<著者-年>.md` に整理します。",
    "topics": "調査トピック・文献リスト（`raw-research` が作る HTML）。",
    "manuscripts": "論文・申請書・要旨のドラフト（`raw-write`。md / LaTeX / Word）、図表、参考文献。",
    "presentations/slides": "発表資料・論文紹介スライド（`.pptx`）。SVG ソースは `_src/<deck>/`（再生成用）。",
    "presentations/figures": "スライドに載せたい画像をここに入れておくと『スライド作って』で `raw-slides` が拾い、縦横比を保って埋め込みます（PNG/JPEG/SVG。例 `xrd_120C.png`）。",
    "analyses": "解析結果（1 トピック 1 サブフォルダ）。",
    "experiments": (
        "測定データと測定の記録（1 試料 1 フォルダ）。生データは `<試料 ID>/<手法>/`（例 `S-001/pxrd/`）に置き、"
        "各フォルダに測定の記録 `info.md`（雛形は `office/experiment/templates/measurement-info.md`）を付けます。"
        "試料に紐づかない校正データは `_calibration/`。生データを `inbox/` に入れて「取り込んで」と言えば、"
        "`raw-intake` が試料 ID・手法・条件を確かめて振り分けます。実験ノートは `office/experiment/notebook/`。"
    ),
    "notebooks": "Jupyter Notebook。",
    "figures": "解析・論文・スライド用の図表（presentation と共有）。",
    "scripts": "単発・一時スクリプト。",
    "tools": "再利用される本格的なツール。",
}

INBOX_README = (
    "# inbox — 何でもここに入れて「処理して」\n\n"
    "種類を問わず過去資料・データをここに入れて **「処理して」** と言えば、`raw-intake` が"
    "中身を見て判定し振り分けます：自分の論文/スライド/CV → 文体・プロフィール抽出、"
    "外部論文 → 登録（`work/papers/`）、計算入出力 → Playbook 取り込み。"
    "処理が済んだ原本は種類ごとに `work/…/_source/` へ移動し、inbox は空になります。"
    "どこに入れるか迷ったらここで OK。\n"
)

# knowledge-base / cloud answer -> mcp template choice token (### Q3/Q4 = <token>)
_KB_ALIASES = {
    "notion": "Notion",
    "obsidian": "Obsidian",
    "logseq": "Logseq",
}
_CLOUD_ALIASES = {
    "google drive": "Google Drive",
    "googledrive": "Google Drive",
    "gdrive": "Google Drive",
    "drive": "Google Drive",
    "dropbox": "Dropbox",
    "onedrive": "OneDrive",
    "one drive": "OneDrive",
}
_KB_UNSET = "使わない / まだ決めていない"
_CLOUD_UNSET = "使わない / ローカルのみ"

# field_group が空のときの規律（field-rules.md の ``### field = 共通``）
FIELD_COMMON = "共通"

_ILLEGAL = set('<>:"|?*\x00')
_WIN_RESERVED = {
    "con", "prn", "aux", "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}


def _is_reserved(part: str) -> bool:
    """True if a path component is a reserved Windows device name (con, nul, com1…)."""
    return part.split(".")[0].strip().lower() in _WIN_RESERVED


def tool_readme(dirname: str, exts: str) -> str:
    """README body for a computation tool work dir (inbox/_past-data folded in)."""
    return (
        f"# work/{dirname}\n\n"
        f"**主な入出力**：{exts}\n\n"
        f"- `inbox/` — これから計算したい構造・下書き入力を一時的に置く場所。"
        f"「`work/{dirname}/inbox/` の構造で入力を作って」のように指示できます。\n"
        f"- `_past-data/` — 過去に自分が回した入力・出力を入れる場所。"
        f"「過去データを取り込んで」と言うと傾向を Playbook に取り込み、以後の入力生成が最適化されます。\n\n"
        f"関連 Playbook: `../../office/computation/playbooks/{dirname}.md`\n"
    )


# --- path safety ----------------------------------------------------------


def normalize_tool(name: str) -> str:
    """Slugify a tool name to ``[a-z0-9-]`` and reject anything unsafe.

    ``Quantum ESPRESSO`` -> ``quantum-espresso``. Raises ValueError for names
    that would escape or produce illegal paths (``..``, ``/``, drive letters).
    """
    s = str(name).strip().lower().replace(" ", "-").replace("_", "-")
    s = re.sub(r"-+", "-", s).strip("-")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", s):
        raise ValueError(f"invalid tool name: {name!r}")
    if _is_reserved(s):
        raise ValueError(f"reserved (Windows device) name not allowed: {name!r}")
    return s


def safe_relpath(rel: str) -> str:
    """Validate a template-derived relative path; reject traversal/absolute.

    Backslashes are normalised to ``/`` (reference paths are POSIX). Rejects
    absolute paths, drive letters, UNC, ``..``/``.`` parts, and Windows-illegal
    characters. Returns the cleaned POSIX-relative path.
    """
    raw = str(rel).replace("\\", "/")
    if re.match(r"^[A-Za-z]:", raw) or raw.startswith("//"):
        raise ValueError(f"unsafe path (absolute/UNC): {rel!r}")
    if any(c in _ILLEGAL for c in raw):
        raise ValueError(f"unsafe path (illegal char): {rel!r}")
    p = PurePosixPath(raw)
    if p.is_absolute():
        raise ValueError(f"unsafe path (absolute): {rel!r}")
    parts = [part for part in p.parts]
    if not parts or any(part in ("..", ".") for part in parts):
        raise ValueError(f"unsafe path (traversal/empty): {rel!r}")
    if any(_is_reserved(part) for part in parts):
        raise ValueError(f"unsafe path (reserved Windows name): {rel!r}")
    return str(PurePosixPath(*parts))


def resolve_within(base: Path, rel: str) -> Path:
    """Return ``base/rel`` guaranteed to stay under ``base`` (belt & suspenders)."""
    safe = safe_relpath(rel)
    base_r = base.resolve()
    target = (base_r / safe).resolve()
    if target != base_r and base_r not in target.parents:
        raise ValueError(f"path escapes output dir: {rel!r}")
    return base / safe


# --- fenced-markdown parsing (fail-closed) --------------------------------

_PATH_HEADER = re.compile(r"^###\s+(.+?)\s*$")
_FENCE_OPEN = re.compile(r"^(`{3,})\s*[A-Za-z0-9_-]*\s*$")
# lines allowed between a closed choice body and the next header: blank, a rule, a one-line comment
_AFTER_BODY_OK = re.compile(r"^(|---|<!--(?:(?!-->).)*-->)$")


def _clean_path(raw: str) -> str | None:
    """Concrete relative path from a ``### <path>`` header, or None for generic."""
    path = re.split(r"[（(]", raw, maxsplit=1)[0].strip()
    path = path.strip("`").strip()
    if not path or "<" in path or ">" in path or "`" in path:
        return None
    return path


def _read_fence(lines: list[str], i: int) -> tuple[str, int]:
    """Read a fenced block starting at fence-open line ``i``.

    Returns (body, index_after_close). Raises if the fence is never closed.
    """
    fence = _FENCE_OPEN.match(lines[i]).group(1)  # type: ignore[union-attr]
    j = i + 1
    buf: list[str] = []
    while j < len(lines):
        if lines[j].rstrip() == fence:
            return "\n".join(buf), j + 1
        buf.append(lines[j])
        j += 1
    raise ValueError(f"unterminated fenced block opened at line {i + 1}")


def extract_path_blocks(text: str) -> dict[str, str]:
    """Parse ``### <path>`` sections whose first content is a fenced block.

    Returns ``{clean_path: body}``. Fence length is matched exactly so nested
    fences inside a body do not close it early. Prose-only sections and generic
    ``<...>`` example paths are skipped. Unterminated fences raise (fail-closed).
    """
    lines = text.splitlines()
    blocks: dict[str, str] = {}
    i, n = 0, len(lines)
    while i < n:
        m = _PATH_HEADER.match(lines[i])
        if not m:
            i += 1
            continue
        path = _clean_path(m.group(1))
        i += 1
        body: str | None = None
        while i < n:
            line = lines[i]
            if _PATH_HEADER.match(line) or line.startswith("## "):
                break
            if _FENCE_OPEN.match(line):
                body, i = _read_fence(lines, i)
                break
            i += 1
        if path and body is not None:
            blocks[path] = body
    return blocks


def extract_first_fence(text: str) -> str:
    """Return the body of the first fenced block in ``text`` (fail-closed)."""
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if _FENCE_OPEN.match(line):
            body, _ = _read_fence(lines, idx)
            return body
    raise ValueError("no fenced block found")


def substitute(text: str, mapping: dict[str, str]) -> str:
    """Replace ``{{KEY}}`` occurrences from mapping. Unknown keys are left as-is."""
    return re.sub(r"\{\{([A-Z_]+)\}\}", lambda m: mapping.get(m.group(1), m.group(0)), text)


_LEFTOVER = re.compile(r"\{\{[A-Z_]+\}\}")


def assert_no_placeholders(text: str, where: str) -> None:
    """Fail loudly if any ``{{TOKEN}}`` survived substitution in a written file."""
    left = _LEFTOVER.findall(text)
    if left:
        raise ValueError(f"unresolved placeholder(s) {sorted(set(left))} in {where}")


# --- choice sections (### <label> = <choice> + fence) ----------------------


def _choice_blocks(text: str, label: str) -> dict[str, str]:
    """Return ``{choice_token: fenced_body}`` for each ``### <label> = <token>``."""
    lines = text.splitlines()
    out: dict[str, str] = {}
    pat = re.compile(rf"^###\s+{re.escape(label)}\s*=\s*(.+?)\s*$")
    i, n = 0, len(lines)
    while i < n:
        m = pat.match(lines[i])
        if not m:
            i += 1
            continue
        token = m.group(1).strip()
        i += 1
        while i < n and not _FENCE_OPEN.match(lines[i]):
            if _PATH_HEADER.match(lines[i]) or lines[i].startswith("## "):
                break
            i += 1
        if i >= n or not _FENCE_OPEN.match(lines[i]):
            raise ValueError(f"selector '### {label} = {token}' has no fenced body")
        if token in out:
            raise ValueError(f"duplicate selector '### {label} = {token}'")
        body, i = _read_fence(lines, i)
        # a nested fence closes the block early; the rest of the body would be lost silently
        while i < n and not (_PATH_HEADER.match(lines[i]) or lines[i].startswith("## ")):
            if not _AFTER_BODY_OK.match(lines[i].strip()):
                raise ValueError(f"text after the fenced body of '### {label} = {token}' (line {i + 1})")
            i += 1
        out[token] = body
    return out


def _mcp_choice_blocks(text: str, qnum: str) -> dict[str, str]:
    """MCP template choices for onboarding question ``Q<qnum>``."""
    return _choice_blocks(text, f"Q{qnum}")


def field_rule_blocks(text: str) -> dict[str, str]:
    """``{group: rules}`` from field-rules.md (``### field = <group>`` sections)."""
    return _choice_blocks(text, "field")


def resolve_field_group(group: object) -> str:
    """The field_group key to use: a string, or 共通 when missing/empty."""
    if group is not None and not isinstance(group, str):
        raise ValueError(f"field_group must be a string, got {group!r}")
    return (group or "").strip() or FIELD_COMMON


def select_field_rules(text: str, group: object) -> str:
    """Rules for ``group``; empty/None means 共通. Unknown or empty groups are an error."""
    blocks = field_rule_blocks(text)
    key = resolve_field_group(group)
    if key not in blocks:
        raise ValueError(f"unknown field_group {key!r}; choose one of {sorted(blocks)}")
    if not blocks[key].strip():
        raise ValueError(f"field rules for {key!r} are empty")
    return blocks[key]


def _select_choice(blocks: dict[str, str], answer: str, aliases: dict[str, str], unset_token: str) -> str:
    """Pick a choice body for ``answer`` via alias map, falling back to unset."""
    key = str(answer).strip().lower()
    token = aliases.get(key)
    if token is None:
        # exact (case-insensitive) match against available tokens
        for tok in blocks:
            if tok.strip().lower() == key and key:
                token = tok
                break
    body = blocks.get(token) if token else None
    if body is None:
        body = blocks.get(unset_token)
    return body or ""


def assemble_mcp(mcp_text: str, knowledge_base: str, cloud_storage: str) -> str:
    """Build office/.mcp-setup.md: common header fence + selected KB + cloud."""
    header = extract_first_fence(mcp_text)
    q3 = _mcp_choice_blocks(mcp_text, "3")
    q4 = _mcp_choice_blocks(mcp_text, "4")
    kb_body = _select_choice(q3, knowledge_base, _KB_ALIASES, _KB_UNSET)
    cloud_body = _select_choice(q4, cloud_storage, _CLOUD_ALIASES, _CLOUD_UNSET)
    parts = [header, kb_body, cloud_body]
    return "\n\n".join(p.strip() for p in parts if p.strip()).rstrip() + "\n"


# --- playbooks ------------------------------------------------------------


def select_tool_playbook(starters_text: str, tool: str) -> str | None:
    """Starter playbook body for ``tool`` (path key), or None when absent."""
    blocks = extract_path_blocks(starters_text)
    return blocks.get(f"computation/playbooks/{tool}.md")


def minimal_playbook(tool: str, today: str) -> str:
    """Frontmatter + empty Lessons Learned stub for a tool without a starter."""
    return (
        "---\n"
        f"tool: {tool}\n"
        f"last_updated: {today}\n"
        "---\n\n"
        f"# {tool} Playbook\n\n"
        "## Lessons Learned\n\n"
        "_（このツールを使いながら raw-playbook が罠・推奨値・ベンチ値を追記していきます）_\n"
    )


# --- writing --------------------------------------------------------------


def _write(target: Path, content: str, written: list[str], *, force: bool, mutable: bool = False) -> None:
    """Write a file. Never clobber a *mutable* file that already exists; static
    files are overwritten only with ``force``."""
    if target.exists() and (mutable or not force):
        return
    if target.is_dir():
        raise ValueError(f"expected a file but found a directory: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if not content.endswith("\n"):
        content += "\n"
    target.write_text(content, encoding="utf-8", newline="\n")  # LF on all platforms
    written.append(str(target))


def scaffold(config: dict[str, Any], skill_dir: Path, out_dir: Path, *, force: bool = False) -> list[str]:
    """Create the raw project tree under ``out_dir`` from config + skill refs."""
    refs = skill_dir / "references"
    today = str(config.get("today") or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", today):
        raise ValueError(f"config.today must be YYYY-MM-DD, got {today!r}")

    # resolve the field rules first so an unknown field_group writes nothing
    field_group = resolve_field_group(config.get("field_group"))
    field_rules = select_field_rules((refs / "field-rules.md").read_text(encoding="utf-8"), field_group)

    written: list[str] = []
    office = out_dir / "office"

    mapping = {
        "RESEARCH_FIELD": str(config.get("research_field", "")),
        "FIELD_GROUP": field_group,
        "FIELD_RULES": field_rules.strip("\n"),
        "COMPUTATION_CATEGORIES": str(config.get("computation_categories", "")),
        "KNOWLEDGE_BASE": str(config.get("knowledge_base", "")),
        "CLOUD_STORAGE": str(config.get("cloud_storage", "")),
        "CREATED_DATE": today,
        "TODAY": today,
        "PROJECT_ROOT": out_dir.resolve().name or "project-root",
        "DEPARTMENT_TREE": DEPARTMENT_TREE,
        "DEPARTMENT_TABLE_ROWS": DEPARTMENT_TABLE_ROWS,
        "PERSONALIZATION_NOTES": str(config.get("personalization_notes", "")).strip()
        or "_（研究を進める中で追記されます）_",
    }

    def emit(target: Path, content: str, *, mutable: bool = False) -> None:
        assert_no_placeholders(content, str(target))
        _write(target, content, written, force=force, mutable=mutable)

    # 1. root office file: CLAUDE.md (Claude Code) or AGENTS.md (Codex / Copilot).
    #    Dept files auto-adapt because research-departments.md ships the right
    #    ``### <dept>/CLAUDE.md`` or ``### <dept>/AGENTS.md`` paths per variant.
    if (refs / "claude-md-template.md").exists():
        root_tmpl, root_name = "claude-md-template.md", "CLAUDE.md"
    elif (refs / "agents-md-template.md").exists():
        root_tmpl, root_name = "agents-md-template.md", "AGENTS.md"
    else:
        raise FileNotFoundError(
            "no root office template (claude-md-template.md / agents-md-template.md)"
        )
    tmpl = extract_first_fence((refs / root_tmpl).read_text(encoding="utf-8"))
    emit(office / root_name, substitute(tmpl, mapping))

    # 2. department CLAUDE.md + secretary first todo (todo is mutable)
    blocks = extract_path_blocks((refs / "research-departments.md").read_text(encoding="utf-8"))
    for rel_path, body in blocks.items():
        target_rel = safe_relpath(rel_path.replace("YYYY-MM-DD", today))
        emit(resolve_within(office, target_rel), substitute(body, mapping), mutable="todos/" in target_rel)

    # 3. per-tool playbooks (named tools only; mutable — never clobber)
    tools = [normalize_tool(t) for t in config.get("tools", []) if str(t).strip()]
    if tools:
        starter_blocks = extract_path_blocks((refs / "playbook-starters.md").read_text(encoding="utf-8"))
        for tool in tools:
            section = starter_blocks.get(f"computation/playbooks/{tool}.md")
            content = substitute(section, mapping) if section is not None else minimal_playbook(tool, today)
            emit(office / "computation" / "playbooks" / f"{tool}.md", content, mutable=True)

    # 4. .mcp-setup.md
    mcp = assemble_mcp(
        (refs / "mcp-setup-templates.md").read_text(encoding="utf-8"),
        str(config.get("knowledge_base", "")),
        str(config.get("cloud_storage", "")),
    )
    emit(office / ".mcp-setup.md", mcp)

    # 5. work/ tool dirs (named tools) with README + inbox/ + _past-data/
    for tool in tools:
        dirname, exts = TOOL_DIRS.get(tool, (tool, "主な入出力ファイル"))
        base = resolve_within(out_dir / "work", dirname)
        emit(base / "README.md", tool_readme(dirname, exts))
        (base / "inbox").mkdir(parents=True, exist_ok=True)
        (base / "_past-data").mkdir(parents=True, exist_ok=True)

    # 6. work/ domain dirs (always) with a short README
    for rel, blurb in DOMAIN_DIRS.items():
        emit(resolve_within(out_dir / "work", rel) / "README.md", f"# work/{rel}\n\n{blurb}\n")
    (out_dir / "work" / "papers" / "pdf").mkdir(parents=True, exist_ok=True)
    (out_dir / "work" / "papers" / "md").mkdir(parents=True, exist_ok=True)

    # 7. (v2.1) work/experiments は DOMAIN_DIRS で常に作る。旧い設定の wants_experiment_dir は無視する。

    # 8. integrated inbox
    emit(out_dir / "inbox" / "README.md", INBOX_README)

    return written


def main(argv: list[str] | None = None) -> int:
    """CLI entry. Reads --config JSON and scaffolds into --out from --skill
    references. Returns 0 on success, 2 on any input/scaffold error (with a
    human-readable message on stderr instead of a traceback)."""
    p = argparse.ArgumentParser(description="raw project scaffolder")
    p.add_argument("--config", required=True, help="onboarding answers JSON")
    p.add_argument("--skill", required=True, help="raw skill dir (has references/)")
    p.add_argument("--out", required=True, help="project root to scaffold into")
    p.add_argument("--force", action="store_true", help="overwrite existing STATIC files")
    args = p.parse_args(argv)

    try:
        config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"error: config file not found: {args.config}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON in {args.config}: {exc}", file=sys.stderr)
        return 2
    if not isinstance(config, dict):
        print("error: config JSON must be an object", file=sys.stderr)
        return 2

    try:
        written = scaffold(config, Path(args.skill), Path(args.out), force=args.force)
    except (ValueError, OSError) as exc:  # OSError covers FileNotFound/IsADir/FileExists/Permission
        print(f"error: {exc}", file=sys.stderr)
        return 2

    for path in written:
        print(f"wrote: {path}")
    print(f"scaffold complete: {len(written)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
