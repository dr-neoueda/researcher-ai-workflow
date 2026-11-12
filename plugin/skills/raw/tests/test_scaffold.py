"""Tests for raw scaffold.py — parsing helpers, safety guards, end-to-end.

Run: python3 -m pytest plugin/skills/raw/tests/test_scaffold.py -q
The tests exercise the real shipped reference files (no duplicated fixtures).
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent  # plugin/skills/raw
sys.path.insert(0, str(SKILL_DIR / "scripts"))

import scaffold  # noqa: E402

REFS = SKILL_DIR / "references"


# --- pure helpers ---------------------------------------------------------


def test_substitute_replaces_known_leaves_unknown():
    assert scaffold.substitute("a {{X}} b {{Y}}", {"X": "1"}) == "a 1 b {{Y}}"


def test_substitute_value_with_braces_is_literal():
    # a substitution value containing regex/group text must be inserted literally
    assert scaffold.substitute("{{X}}", {"X": r"\1 {{Y}}"}) == r"\1 {{Y}}"


def test_clean_path_strips_annotation_and_rejects_generic_and_traversal():
    assert scaffold._clean_path("secretary/CLAUDE.md") == "secretary/CLAUDE.md"
    assert scaffold._clean_path("secretary/todos/YYYY-MM-DD.md（初日テンプレ）") == "secretary/todos/YYYY-MM-DD.md"
    assert scaffold._clean_path("computation/playbooks/<tool>.md（雛形）") is None
    assert scaffold._clean_path("`<dept>/CLAUDE.md`") is None


def test_normalize_tool_slugs_and_rejects():
    assert scaffold.normalize_tool("Quantum ESPRESSO") == "quantum-espresso"
    assert scaffold.normalize_tool("Gaussian") == "gaussian"
    assert scaffold.normalize_tool("cp2k") == "cp2k"
    for bad in ("../evil", "a/b", "..", "", "  ", "tool!", "con", "nul", "com1", "aux", "CON"):
        with pytest.raises(ValueError):
            scaffold.normalize_tool(bad)


def test_safe_relpath_rejects_traversal_and_absolute():
    assert scaffold.safe_relpath("a/b/c.md") == "a/b/c.md"
    assert scaffold.safe_relpath("a\\b.md") == "a/b.md"  # backslash normalised
    for bad in ("../x", "a/../b", "/etc/passwd", "C:/x", "//unc/x", "a/b:c", "x\x00y",
                "a/con/b.md", "nul.md", "work/COM1/x.md"):  # reserved Windows names
        with pytest.raises(ValueError):
            scaffold.safe_relpath(bad)


def test_resolve_within_confines(tmp_path):
    assert scaffold.resolve_within(tmp_path, "a/b.md") == tmp_path / "a/b.md"
    with pytest.raises(ValueError):
        scaffold.resolve_within(tmp_path, "../escape.md")


def test_extract_path_blocks_variable_fence():
    text = (
        "### a/CLAUDE.md\n\n```markdown\nhello\n```\n\n"
        "### b/CLAUDE.md\n\n````markdown\nnested ```code``` here\n````\n\n"
        "### c/note.md（skip me）\n\nprose only, no fence\n\n## next\n"
    )
    blocks = scaffold.extract_path_blocks(text)
    assert blocks["a/CLAUDE.md"] == "hello"
    assert "nested ```code``` here" in blocks["b/CLAUDE.md"]
    assert "c/note.md" not in blocks


def test_extract_path_blocks_fail_closed_on_unterminated_fence():
    with pytest.raises(ValueError):
        scaffold.extract_path_blocks("### a/x.md\n\n```markdown\nno close here\n")


def test_extract_first_fence_fail_closed():
    with pytest.raises(ValueError):
        scaffold.extract_first_fence("intro\n````markdown\nunterminated\n")


def test_mcp_choice_blocks_fail_loud_on_missing_fence():
    text = "### Q3 = Notion\n\n```markdown\nok\n```\n\n### Q3 = Broken\n\nno fence prose\n\n## other\n"
    with pytest.raises(ValueError):
        scaffold._mcp_choice_blocks(text, "3")


def test_extract_path_blocks_on_real_departments():
    text = (REFS / "research-departments.md").read_text(encoding="utf-8")
    blocks = scaffold.extract_path_blocks(text)
    assert "secretary/CLAUDE.md" in blocks
    assert "secretary/todos/YYYY-MM-DD.md" in blocks
    for dept in ("research", "engineering", "computation", "experiment",
                 "analysis", "writing", "review", "presentation"):
        assert f"{dept}/CLAUDE.md" in blocks, dept
    assert "experiment/templates/measurement-info.md" in blocks
    assert not any("<" in p for p in blocks)
    assert len(blocks) == 11


def test_all_playbook_starters_are_extractable():
    """Regression guard: every ### computation/playbooks/<tool>.md header must
    yield a parsed block (chimerax was silently dropped before its fence fix)."""
    text = (REFS / "playbook-starters.md").read_text(encoding="utf-8")
    headers = re.findall(r"^###\s+(computation/playbooks/[a-z0-9-]+\.md)", text, re.M)
    blocks = scaffold.extract_path_blocks(text)
    dropped = [h for h in headers if h not in blocks]
    assert not dropped, f"starters silently dropped: {dropped}"
    assert "computation/playbooks/chimerax.md" in blocks


def test_select_tool_playbook_hits_and_misses():
    starters = (REFS / "playbook-starters.md").read_text(encoding="utf-8")
    assert "Gaussian Playbook" in (scaffold.select_tool_playbook(starters, "gaussian") or "")
    assert scaffold.select_tool_playbook(starters, "chimerax") is not None
    assert scaffold.select_tool_playbook(starters, "amber") is None  # -> minimal stub


def test_minimal_playbook_has_frontmatter_and_lessons():
    pb = scaffold.minimal_playbook("amber", "2026-07-09")
    assert "tool: amber" in pb and "last_updated: 2026-07-09" in pb and "## Lessons Learned" in pb


def test_assemble_mcp_is_clean_and_selects_right_sections():
    mcp = (REFS / "mcp-setup-templates.md").read_text(encoding="utf-8")
    out = scaffold.assemble_mcp(mcp, "Notion", "Google Drive")
    assert "Notion" in out and "Google Drive" in out
    # no fence debris: 3-backtick+ fence lines must be balanced (even count)
    fences = [ln for ln in out.splitlines() if re.match(r"^`{3,}", ln)]
    assert len(fences) % 2 == 0, f"unbalanced fences in assembled mcp: {len(fences)}"
    # no selector-marker leakage from other options
    assert not re.search(r"^###\s+Q\d+\s*=", out, re.M)
    # unset falls back to the 未設定 sections without raising
    out2 = scaffold.assemble_mcp(mcp, "", "")
    assert "ナレッジベース未設定" in out2 and "クラウドストレージ未設定" in out2
    # ambiguous 'Dropbox' selects the Dropbox cloud section, not OneDrive/GDrive
    out3 = scaffold.assemble_mcp(mcp, "Obsidian", "Dropbox")
    assert "Obsidian" in out3 and "Dropbox" in out3


# --- end-to-end scaffold --------------------------------------------------


@pytest.fixture()
def config() -> dict:
    return {
        "today": "2026-07-09",
        "research_field": "有機化学・結晶化学",
        "computation_categories": "Gaussian, CP2K, MACE",
        "knowledge_base": "Notion",
        "cloud_storage": "Google Drive",
        "personalization_notes": "- 有機化学 + 量子化学の想定",
        "tools": ["gaussian", "cp2k", "amber"],  # amber has no starter -> stub
        "wants_experiment_dir": True,
    }


def test_scaffold_end_to_end(tmp_path, config):
    written = scaffold.scaffold(config, SKILL_DIR, tmp_path)
    office = tmp_path / "office"

    assert (office / "CLAUDE.md").exists()
    for dept in ("secretary", "research", "engineering", "computation",
                 "experiment", "analysis", "writing", "review", "presentation"):
        assert (office / dept / "CLAUDE.md").exists(), dept

    # NO placeholder leaks in ANY written file (dept files include {{PROJECT_ROOT}})
    for f in written:
        body = Path(f).read_text(encoding="utf-8")
        assert "{{" not in body, f"leaked placeholder in {f}"

    assert (office / "secretary" / "todos" / "2026-07-09.md").exists()

    amber = (office / "computation" / "playbooks" / "amber.md").read_text(encoding="utf-8")
    assert "tool: amber" in amber  # minimal stub

    for tool in ("gaussian", "cp2k", "amber"):
        assert (tmp_path / "work" / tool / "README.md").exists()
        assert (tmp_path / "work" / tool / "inbox").is_dir()
        assert (tmp_path / "work" / tool / "_past-data").is_dir()

    assert (tmp_path / "work" / "papers" / "pdf").is_dir()
    assert (tmp_path / "work" / "presentations" / "figures" / "README.md").exists()
    assert (tmp_path / "work" / "experiments" / "README.md").exists()
    assert (tmp_path / "inbox" / "README.md").exists()
    assert (office / ".mcp-setup.md").exists()

    # the model owns work/profile — scaffold must NOT create it
    assert not (tmp_path / "work" / "profile").exists()
    assert all("work/profile" not in w for w in written)

    # LF newlines on all platforms
    assert b"\r\n" not in (office / "CLAUDE.md").read_bytes()


def test_scaffold_agents_variant_codex(tmp_path, config):
    """Codex/Copilot ship agents-md-template.md + ### <dept>/AGENTS.md paths;
    the same script must emit AGENTS.md (not CLAUDE.md) root + dept files."""
    codex_skill = SKILL_DIR.parent.parent.parent / "codex-plugin" / "skills" / "raw"
    if not (codex_skill / "references" / "agents-md-template.md").exists():
        pytest.skip("codex-plugin references not present")
    scaffold.scaffold(config, codex_skill, tmp_path)
    assert (tmp_path / "office" / "AGENTS.md").exists()
    assert not (tmp_path / "office" / "CLAUDE.md").exists()
    assert (tmp_path / "office" / "research" / "AGENTS.md").exists()


def test_scaffold_normalizes_tool_and_confines(tmp_path):
    cfg = {"today": "2026-07-09", "tools": ["Quantum ESPRESSO"]}
    scaffold.scaffold(cfg, SKILL_DIR, tmp_path)
    assert (tmp_path / "work" / "quantum-espresso" / "README.md").exists()
    assert (tmp_path / "office" / "computation" / "playbooks" / "quantum-espresso.md").exists()


def test_scaffold_rejects_malicious_tool(tmp_path):
    cfg = {"today": "2026-07-09", "tools": ["../../evil"]}
    with pytest.raises(ValueError):
        scaffold.scaffold(cfg, SKILL_DIR, tmp_path)


def test_scaffold_unknown_tool_gets_fallback_readme(tmp_path):
    cfg = {"today": "2026-07-09", "tools": ["my-custom-code"]}
    scaffold.scaffold(cfg, SKILL_DIR, tmp_path)
    readme = (tmp_path / "work" / "my-custom-code" / "README.md").read_text(encoding="utf-8")
    assert "主な入出力ファイル" in readme  # fallback text


@pytest.mark.parametrize("tool", ["AlphaFold", "ColabFold", "OpenFOAM", "COMSOL", "ANSYS", "MATLAB",
                                  "Julia", "R", "BLAST", "PyTorch", "PyMOL"])
def test_onboarding_tools_outside_chemistry_get_a_real_readme(tmp_path, tool):
    """Call 4 に載せた化学以外のソフトにも、入出力を書いた README を出す（汎用の文で済ませない）。"""
    scaffold.scaffold({"today": "2026-11-06", "tools": [tool]}, SKILL_DIR, tmp_path)
    slug = scaffold.normalize_tool(tool)
    readme = (tmp_path / "work" / slug / "README.md").read_text(encoding="utf-8")
    assert "主な入出力ファイル" not in readme, slug


def test_dotted_display_name_is_rejected_with_the_name(tmp_path):
    """「AlphaFold・ColabFold」のような表示名は 1 ソフト 1 要素に分けて渡す。混ざったら名前つきで止める。"""
    with pytest.raises(ValueError, match="AlphaFold・ColabFold"):
        scaffold.scaffold({"today": "2026-11-06", "tools": ["AlphaFold・ColabFold"]}, SKILL_DIR, tmp_path)


def test_scaffold_rejects_bad_date(tmp_path, config):
    config["today"] = "07/09/2026"
    with pytest.raises(ValueError):
        scaffold.scaffold(config, SKILL_DIR, tmp_path)


def test_scaffold_protects_mutable_and_static_force(tmp_path, config):
    scaffold.scaffold(config, SKILL_DIR, tmp_path)
    static = tmp_path / "office" / "CLAUDE.md"
    playbook = tmp_path / "office" / "computation" / "playbooks" / "gaussian.md"
    static.write_text("USER EDIT", encoding="utf-8")
    playbook.write_text("USER LESSONS", encoding="utf-8")

    scaffold.scaffold(config, SKILL_DIR, tmp_path)  # no force
    assert static.read_text(encoding="utf-8") == "USER EDIT"
    assert playbook.read_text(encoding="utf-8") == "USER LESSONS"

    scaffold.scaffold(config, SKILL_DIR, tmp_path, force=True)
    assert static.read_text(encoding="utf-8") != "USER EDIT"          # static refreshed
    assert playbook.read_text(encoding="utf-8") == "USER LESSONS"     # mutable protected


# --- field rules (研究分野の規律) -------------------------------------------

FIELD_GROUPS = ("化学・材料", "物理・地球惑星", "生命科学", "工学・情報", "共通")

# 理工系へ広げる前の office/CLAUDE.md にあった化学の規律。化学の利用者には一字一句このまま出す。
CHEMISTRY_RULES = (
    "- **物理量には必ず単位コメントを付ける**（例：`# kJ/mol`, `# Å`, `# fs`, `# K`）",
    "- **計算パラメータは設定ファイルまたは引数で渡す**（ハードコーディング禁止）",
    "- **乱数シードは固定**（再現性確保）",
    "- **エネルギー単位変換に注意**（kcal/mol ↔ kJ/mol ↔ eV ↔ Hartree）",
    "- **計算ソフトのバージョン依存挙動に注意**（GROMACS の mdp 文法など）",
    "- **化学物理の用語は正確に**（汎関数名・基底関数・force field・cell parameter など）",
)

# 化学以外の分野の office/ に出てはいけない「化学向け」の言い回し（化学の具体例そのものは可）
CHEMISTRY_FRAMING = ("化学研究", "化学者", "化学用語", "化学物理", "湿式ラボ", "化学的に")


def _field_rules_text() -> str:
    return (REFS / "field-rules.md").read_text(encoding="utf-8")


def test_field_rules_cover_every_group():
    blocks = scaffold.field_rule_blocks(_field_rules_text())
    assert set(blocks) == set(FIELD_GROUPS)
    assert all(body.strip() for body in blocks.values())


def test_duplicate_choice_section_is_rejected():
    text = "### field = 共通\n\n```markdown\nA\n```\n\n### field = 共通\n\n```markdown\nB\n```\n"
    with pytest.raises(ValueError, match="duplicate"):
        scaffold.field_rule_blocks(text)


def test_nested_fence_that_cuts_the_body_short_is_rejected():
    text = "### field = 共通\n\n```markdown\nA\n```py\nx\n```\nTAIL\n```\n"
    with pytest.raises(ValueError, match="after the fenced body"):
        scaffold.field_rule_blocks(text)


def test_one_line_comment_and_rule_after_the_body_are_allowed():
    """フェンスの後に書けるのは空行・``---``・1 行の HTML コメントだけ（保守の注記を書ける）。"""
    text = "### field = 共通\n\n```markdown\nA\n```\n\n<!-- 保守の注記 -->\n\n---\n\n### field = 生命科学\n\n```markdown\nB\n```\n"
    assert scaffold.field_rule_blocks(text) == {"共通": "A", "生命科学": "B"}


@pytest.mark.parametrize("tail", ["<!-- 閉じていない\nTAIL", "<!-- a --> 後ろに本文", "<!-- a --> 本文 <!-- c -->"])
def test_text_outside_a_one_line_comment_is_still_rejected(tail):
    text = f"### field = 共通\n\n```markdown\nA\n```\n{tail}\n"
    with pytest.raises(ValueError, match="after the fenced body"):
        scaffold.field_rule_blocks(text)


@pytest.mark.parametrize("text", [
    "### field = 共通\n\n```markdown\nA\n```\n<!-- フェンスの直後 -->\n\n### field = 生命科学\n\n```markdown\nB\n```\n",
    "### field = 生命科学\n\n```markdown\nB\n```\n\n### field = 共通\n\n```markdown\nA\n```\n<!-- ファイルの最後 -->",
])
def test_comment_right_after_the_fence_or_at_the_end_is_allowed(text):
    assert scaffold.field_rule_blocks(text) == {"共通": "A", "生命科学": "B"}


def test_empty_rules_body_is_rejected():
    with pytest.raises(ValueError, match="empty"):
        scaffold.select_field_rules("### field = 共通\n\n```markdown\n\n```\n", "共通")


@pytest.mark.parametrize("value", [0, False, [], ["化学・材料"]])
def test_non_string_field_group_is_rejected(value):
    with pytest.raises(ValueError, match="field_group"):
        scaffold.select_field_rules(_field_rules_text(), value)


def test_missing_field_group_falls_back_to_common():
    text = _field_rules_text()
    common = scaffold.select_field_rules(text, "共通")
    assert scaffold.select_field_rules(text, "") == common
    assert scaffold.select_field_rules(text, None) == common
    assert scaffold.select_field_rules(text, " 生命科学 ") == scaffold.select_field_rules(text, "生命科学")


def test_unknown_field_group_is_rejected():
    with pytest.raises(ValueError, match="field_group"):
        scaffold.select_field_rules(_field_rules_text(), "文学")


def test_chemistry_keeps_its_rules_verbatim(tmp_path, config):
    config["field_group"] = "化学・材料"
    scaffold.scaffold(config, SKILL_DIR, tmp_path)
    body = (tmp_path / "office" / "CLAUDE.md").read_text(encoding="utf-8")
    for rule in CHEMISTRY_RULES:
        assert rule in body, rule
    assert "## 研究分野の規律" in body
    assert "**分野の群**: 化学・材料" in body


def _chemistry_framing_hits(root: Path) -> list[str]:
    """``root`` 以下の全 .md から、化学向けの言い回しを ``"<相対パス>: <語>"`` で返す。"""
    return [f"{path.relative_to(root)}: {phrase}"
            for path in root.rglob("*.md")
            for phrase in CHEMISTRY_FRAMING if phrase in path.read_text(encoding="utf-8")]


def _scaffold_group(out: Path, group: str, skill: Path = SKILL_DIR) -> None:
    cfg = {"today": "2026-11-06", "field_group": group, "research_field": "分野",
           "tools": ["r", "openfoam", "alphafold"], "wants_experiment_dir": True}
    scaffold.scaffold(cfg, skill, out)


@pytest.mark.parametrize("group", [g for g in FIELD_GROUPS if g != "化学・材料"])
def test_other_fields_carry_no_chemistry_framing(tmp_path, group):
    _scaffold_group(tmp_path, group)
    assert _chemistry_framing_hits(tmp_path) == []
    body = (tmp_path / "office" / "CLAUDE.md").read_text(encoding="utf-8")
    own = scaffold.select_field_rules(_field_rules_text(), group)
    for rule in CHEMISTRY_RULES:
        if rule not in own:                                    # 単位・パラメータ・シードの行は各群に共通
            assert rule not in body, rule                      # 化学だけの規律が混ざらない


@pytest.mark.parametrize("group", FIELD_GROUPS)
def test_exactly_one_group_of_rules_reaches_the_root_file(tmp_path, group):
    _scaffold_group(tmp_path, group)
    body = (tmp_path / "office" / "CLAUDE.md").read_text(encoding="utf-8")
    blocks = scaffold.field_rule_blocks(_field_rules_text())
    present = [g for g, rules in blocks.items() if rules.strip() in body]
    assert present == [group]


def test_framing_check_catches_an_injected_phrase(tmp_path):
    """検定が働くことの確かめ: 雛形の写しに「化学研究」を戻すと拾う。"""
    skill = tmp_path / "skill"
    shutil.copytree(SKILL_DIR / "references", skill / "references")
    dept = skill / "references" / "research-departments.md"
    dept.write_text(dept.read_text(encoding="utf-8").replace("研究のあらゆる場面", "化学研究のあらゆる場面", 1),
                    encoding="utf-8")
    _scaffold_group(tmp_path / "out", "共通", skill)
    assert any("化学研究" in hit for hit in _chemistry_framing_hits(tmp_path / "out"))


CODEX_SKILL = SKILL_DIR.parent.parent.parent / "codex-plugin" / "skills" / "raw"


@pytest.mark.parametrize("rel", ["references/field-rules.md", "scripts/scaffold.py"])
def test_codex_copy_is_byte_identical(rel):
    assert (CODEX_SKILL / rel).read_bytes() == (SKILL_DIR / rel).read_bytes()


def test_codex_variant_gets_field_rules_too(tmp_path, config):
    config["field_group"] = "工学・情報"
    scaffold.scaffold(config, CODEX_SKILL, tmp_path)
    body = (tmp_path / "office" / "AGENTS.md").read_text(encoding="utf-8")
    assert scaffold.select_field_rules(_field_rules_text(), "工学・情報").strip() in body


def test_main_cli_rejects_unknown_field_group(tmp_path, config, capsys):
    config["field_group"] = "文学"
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "project"
    rc = scaffold.main(["--config", str(cfg_path), "--skill", str(SKILL_DIR), "--out", str(out)])
    assert rc == 2
    assert "field_group" in capsys.readouterr().err
    assert not out.exists() or not any(out.iterdir())         # 止まったら何も書かない


def test_main_cli_happy(tmp_path, config, capsys):
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps(config), encoding="utf-8")
    rc = scaffold.main(["--config", str(cfg_path), "--skill", str(SKILL_DIR), "--out", str(tmp_path)])
    assert rc == 0
    assert "scaffold complete" in capsys.readouterr().out


def test_main_cli_missing_config(tmp_path, capsys):
    rc = scaffold.main(["--config", str(tmp_path / "nope.json"), "--skill", str(SKILL_DIR), "--out", str(tmp_path)])
    assert rc == 2
    assert "not found" in capsys.readouterr().err


def test_main_cli_bad_json(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{ not json", encoding="utf-8")
    rc = scaffold.main(["--config", str(bad), "--skill", str(SKILL_DIR), "--out", str(tmp_path)])
    assert rc == 2
    assert "invalid JSON" in capsys.readouterr().err


# --- v2.1: 測定データの置き場・確かめ方の決まり ---------------------------------


@pytest.mark.parametrize("flag", [None, False, True])
def test_experiments_dir_is_always_created(tmp_path, config, flag):
    cfg = {k: v for k, v in config.items() if k != "wants_experiment_dir"}
    if flag is not None:
        cfg["wants_experiment_dir"] = flag  # 旧い設定のキーは受け取って無視する
    scaffold.scaffold(cfg, SKILL_DIR, tmp_path)
    readme = (tmp_path / "work" / "experiments" / "README.md").read_text(encoding="utf-8")
    assert "<試料 ID>/<手法>/" in readme and "info.md" in readme


@pytest.mark.parametrize("skill", [SKILL_DIR, CODEX_SKILL])
def test_measurement_record_template_is_placed_for_the_experiment_dept(tmp_path, config, skill):
    scaffold.scaffold(config, skill, tmp_path)
    tmpl = (tmp_path / "office" / "experiment" / "templates" / "measurement-info.md").read_text(encoding="utf-8")
    for key in ("sample:", "technique:", "date:", "移動前", "移動後"):
        assert key in tmpl, key


@pytest.mark.parametrize("skill,root", [(SKILL_DIR, "CLAUDE.md"), (CODEX_SKILL, "AGENTS.md")])
def test_root_rules_carry_the_six_verification_rules(tmp_path, config, skill, root):
    scaffold.scaffold(config, skill, tmp_path)
    body = (tmp_path / "office" / root).read_text(encoding="utf-8")
    section = body.split("### 確かめ方の決まり", 1)[1].split("\n## ", 1)[0].split("\n### ", 1)[0]
    assert re.findall(r"^(\d)\. \*\*", section, flags=re.M) == ["1", "2", "3", "4", "5", "6"]


def test_experiment_dept_points_measurement_data_to_the_sample_folders(tmp_path, config):
    scaffold.scaffold(config, SKILL_DIR, tmp_path)
    dept = (tmp_path / "office" / "experiment" / "CLAUDE.md").read_text(encoding="utf-8")
    assert "work/experiments/<試料 ID>/<手法>/" in dept
    assert "measurement-info.md" in dept and "ファイル数" in dept


def test_output_table_names_the_real_slides_folder(tmp_path, config):
    scaffold.scaffold(config, SKILL_DIR, tmp_path)
    body = (tmp_path / "office" / "CLAUDE.md").read_text(encoding="utf-8")
    assert "| `slides/` |" not in body
    assert "| `work/presentations/` |" in body


@pytest.mark.parametrize("skill,root", [(SKILL_DIR, "CLAUDE.md"), (CODEX_SKILL, "AGENTS.md")])
def test_root_rules_require_a_watch_on_every_job(tmp_path, config, skill, root):
    scaffold.scaffold(config, skill, tmp_path)
    body = (tmp_path / "office" / root).read_text(encoding="utf-8")
    section = body.split("### 計算の見張り", 1)[1].split("\n## ", 1)[0]
    assert re.findall(r"^(\d)\. \*\*", section, flags=re.M) == ["1", "2", "3", "4", "5"]
    for word in ("jobwatch.py register", "ensure-watcher", "judge", "終了コード"):
        assert word in section, word
    dept = (tmp_path / "office" / "computation" / root).read_text(encoding="utf-8")
    assert "jobwatch.py register" in dept
