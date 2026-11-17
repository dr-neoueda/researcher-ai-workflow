"""search_library.py（登録済みの論文の要約を検索する）のテスト。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import search_library as sl


def _paper(folder: Path, name: str, title: str, body: str, tags: tuple[str, ...] = (), doi: str = "") -> None:
    tag_lines = "".join(f"  - {t}\n" for t in tags)
    folder.joinpath(f"{name}.md").write_text(
        f'---\ntitle: "{title}"\nauthors:\n  - "A. Author"\n  - "B. Author"\nyear: 2024\njournal: "J. Test"\n'
        f'doi: "{doi}"\nurl: "https://doi.org/{doi}"\ntags:\n{tag_lines}---\n\n# {title}\n\n{body}\n',
        encoding="utf-8",
    )


@pytest.fixture()
def library(tmp_path: Path) -> Path:
    lib = tmp_path / "work" / "papers" / "md"
    lib.mkdir(parents=True)
    _paper(lib, "wang-2024", "Machine-learned potentials for crystal reactions",
           "## One-line summary\nMACE potentials reproduce DFT barriers in molecular crystals.\n\n"
           "## 主要な結果\n活性化障壁は 31.4 kcal/mol で、DFT と 1 kcal/mol 以内で一致した。\n",
           tags=("MLIP", "結晶相反応"), doi="10.1000/wang")
    _paper(lib, "sato-2023", "示差走査熱量測定による固相反応速度論",
           "## 背景・動機\nDSC で等温加熱し、Avrami 解析で反応速度を求めた。\n\n## 主要な結果\nAvrami 指数は 2.1 であった。\n",
           tags=("DSC", "速度論"), doi="10.1000/sato")
    _paper(lib, "lee-2022", "Solvent effects on photochemistry",
           "## 背景・動機\nWe study solvent polarity and fluorescence quantum yield.\n", tags=("photochemistry",))
    return lib


def test_loads_frontmatter_and_sections(library: Path) -> None:
    papers = sl.load_library(library)
    wang = next(p for p in papers if p.path.stem == "wang-2024")
    assert wang.title.startswith("Machine-learned") and wang.year == "2024" and wang.doi == "10.1000/wang"
    assert wang.authors == ("A. Author", "B. Author") and "MLIP" in wang.tags
    assert {s.name for s in wang.sections} >= {"One-line summary", "主要な結果"}


def test_english_query_finds_the_right_paper_first(library: Path) -> None:
    hits = sl.search(sl.load_library(library), ["MACE potential barrier crystal"])
    assert hits[0].paper.path.stem == "wang-2024"


def test_japanese_query_uses_character_pairs(library: Path) -> None:
    hits = sl.search(sl.load_library(library), ["固相反応の速度論 DSC"])
    assert hits[0].paper.path.stem == "sato-2023"


def test_several_queries_are_combined(library: Path) -> None:
    hits = sl.search(sl.load_library(library), ["活性化障壁", "activation barrier MLIP"])
    assert hits[0].paper.path.stem == "wang-2024"


def test_title_and_tags_count_more_than_body(library: Path) -> None:
    hits = sl.search(sl.load_library(library), ["photochemistry"])
    assert hits[0].paper.path.stem == "lee-2022"


def test_unrelated_query_returns_nothing(library: Path) -> None:
    assert sl.search(sl.load_library(library), ["zebrafish neuron imaging"]) == []


def test_hit_carries_the_best_section_and_a_snippet(library: Path) -> None:
    (hit, *_rest) = sl.search(sl.load_library(library), ["Avrami 指数"])
    assert hit.paper.path.stem == "sato-2023"
    assert hit.section == "主要な結果" and "Avrami" in hit.snippet


def test_missing_frontmatter_falls_back_to_heading(tmp_path: Path) -> None:
    lib = tmp_path / "md"
    lib.mkdir()
    (lib / "x.md").write_text("# A paper without frontmatter\n\n## Results\nyield 85 %\n", encoding="utf-8")
    (paper,) = sl.load_library(lib)
    assert paper.title == "A paper without frontmatter"


def test_cli_prints_count_paths_and_dois(library: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = sl.main(["MACE barrier", "--library", str(library)])
    out = capsys.readouterr().out
    assert code == 0
    assert "登録済み 3 本" in out and "wang-2024.md" in out and "10.1000/wang" in out


def test_cli_says_nothing_found_with_the_count(library: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert sl.main(["zebrafish neuron", "--library", str(library)]) == 0
    assert "見当たりません（登録済み 3 本" in capsys.readouterr().out


def test_cli_json(library: Path, capsys: pytest.CaptureFixture[str]) -> None:
    sl.main(["Avrami", "--library", str(library), "--json"])
    data = json.loads(capsys.readouterr().out)
    assert data["papers"] == 3 and data["hits"][0]["path"].endswith("sato-2023.md")


def test_cli_missing_library_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert sl.main(["zeolite", "--library", str(tmp_path / "none")]) == 2
    assert "見つかりません" in capsys.readouterr().err


def test_empty_library_is_reported(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    lib = tmp_path / "md"
    lib.mkdir()
    assert sl.main(["zeolite", "--library", str(lib)]) == 0
    assert "登録済みの論文がまだありません" in capsys.readouterr().out


# ---------- 仕組みごとに効いているかを確かめる ----------

def test_japanese_tokens_are_kanji_katakana_pairs_without_particles() -> None:
    assert sl.tokenize("の速度論について") == ["速度", "度論"]
    assert sl.tokenize("カルボニル") == ["カル", "ルボ", "ボニ", "ニル"]


def test_english_stopwords_are_dropped() -> None:
    assert sl.tokenize("the effect of a solvent on the yield") == ["effect", "solvent", "yield"]


def test_japanese_only_query_finds_the_paper(library: Path) -> None:
    hits = sl.search(sl.load_library(library), ["固相反応の速度論"])
    assert hits[0].paper.path.stem == "sato-2023"


def test_a_title_match_beats_a_repeated_body_word(library: Path) -> None:
    _paper(library, "kim-2021", "Unrelated title about catalysis",
           "## 本文の一節\nphotochemistry photochemistry photochemistry photochemistry photochemistry\n")
    hits = sl.search(sl.load_library(library), ["photochemistry"])
    assert hits[0].paper.path.stem == "lee-2022"


def test_each_query_counts_equally(library: Path) -> None:
    hits = sl.search(sl.load_library(library), ["Avrami 指数 DSC 等温 速度論 固相 反応速度", "MACE"])
    scores = {h.paper.path.stem: h.score for h in hits}
    assert scores["wang-2024"] >= 0.9 * scores["sato-2023"]


def test_snippet_shows_the_matching_part_of_a_long_section(tmp_path: Path) -> None:
    lib = tmp_path / "md"
    lib.mkdir()
    _paper(lib, "long", "A long paper", "## 主要な結果\n" + "背景の説明。" * 80 + "Avrami 指数は 2.1 であった。\n")
    (hit,) = sl.search(sl.load_library(lib), ["Avrami"])
    assert "Avrami" in hit.snippet


# ---------- レビューの指摘（2026-11-10）----------

@pytest.mark.parametrize("text,expected", [
    ("ΔE", ["δe"]), ("π-π stacking", ["π", "π", "stacking"]), ("α-helix", ["α", "helix"]),
    ("Müller café", ["muller", "cafe"]),
])
def test_greek_and_accented_letters_are_kept(text: str, expected: list[str]) -> None:
    assert sl.tokenize(text) == expected


def test_hyphenated_terms_also_count_as_one_word() -> None:
    tokens = sl.tokenize("X-ray solid-state")
    assert "xray" in tokens and "solidstate" in tokens and "state" in tokens


def test_a_single_kanji_query_matches_inside_longer_words(tmp_path: Path) -> None:
    lib = tmp_path / "md"
    lib.mkdir()
    _paper(lib, "hikari", "光反応の研究", "## 主要な結果\n光反応で生成物が得られた。\n")
    _paper(lib, "xrd", "X線回折による構造解析", "## 主要な結果\nX線回折で格子定数を求めた。\n")
    assert sl.search(sl.load_library(lib), ["光"])[0].paper.path.stem == "hikari"
    assert sl.search(sl.load_library(lib), ["X線"])[0].paper.path.stem == "xrd"


def test_unterminated_frontmatter_keeps_its_fields(tmp_path: Path) -> None:
    lib = tmp_path / "md"
    lib.mkdir()
    (lib / "x.md").write_text('---\ntitle: "Foo: bar"\nauthors:\n  - A\n  - B\nyear: 2020\n# c\n\n## Results\nok\n', encoding="utf-8")
    (paper,) = sl.load_library(lib)
    assert paper.title == "Foo: bar" and paper.authors == ("A", "B") and paper.year == "2020"


def test_inline_lists_are_split(tmp_path: Path) -> None:
    lib = tmp_path / "md"
    lib.mkdir()
    (lib / "x.md").write_text('---\ntitle: "T"\nauthors: [Smith J, "Doe A"]\ntags: [solid, state]\n---\n# T\n', encoding="utf-8")
    (paper,) = sl.load_library(lib)
    assert paper.authors == ("Smith J", "Doe A") and paper.tags == ("solid", "state")


def test_shift_jis_files_are_read(tmp_path: Path) -> None:
    lib = tmp_path / "md"
    lib.mkdir()
    (lib / "sjis.md").write_bytes("# 分子結晶の研究\n\n## 主要な結果\n分子結晶で反応が進んだ。\n".encode("cp932"))
    assert sl.search(sl.load_library(lib), ["分子結晶"])[0].paper.path.stem == "sjis"


def test_unreadable_files_are_counted_separately(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    lib = tmp_path / "md"
    lib.mkdir()
    _paper(lib, "ok", "Readable paper", "## 本文\nhello world\n")
    (lib / "bad.md").write_bytes(b"\x81\x7f\x81\x7f")  # UTF-8 でも cp932 でも読めない
    sl.main(["hello", "--library", str(lib)])
    out = capsys.readouterr().out
    assert "登録済み 1 本" in out and "読めないファイル 1 本" in out and "bad.md" in out


def test_metadata_bullets_are_read(tmp_path: Path) -> None:
    lib = tmp_path / "md"
    lib.mkdir()
    (lib / "m.md").write_text(
        "# A bullet-style summary\n\n## Metadata\n- **Authors**: Smith, J.; Doe, A.\n- **Year**: 2021\n"
        "- **Journal**: J. Phys. Chem.\n- **DOI**: 10.1/abc\n- **Tags**: crystal, kinetics\n\n## Summary\ntext\n",
        encoding="utf-8",
    )
    (paper,) = sl.load_library(lib)
    assert paper.year == "2021" and paper.doi == "10.1/abc" and paper.journal == "J. Phys. Chem."
    assert paper.authors == ("Smith, J.", "Doe, A.") and paper.tags == ("crystal", "kinetics")


def test_uppercase_md_extension_is_included(tmp_path: Path) -> None:
    lib = tmp_path / "md"
    lib.mkdir()
    _paper(lib, "upper", "Upper case file", "## 本文\nzeolite synthesis\n")
    (lib / "upper.md").rename(lib / "UPPER.MD")
    assert sl.search(sl.load_library(lib), ["zeolite"])


@pytest.mark.parametrize("query", ["", "the of"])
def test_a_query_without_search_words_is_refused(library: Path, query: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert sl.main([query, "--library", str(library)]) == 2
    assert "検索語がありません" in capsys.readouterr().err


def test_top_must_be_positive(library: Path) -> None:
    with pytest.raises(SystemExit):
        sl.main(["MACE", "--library", str(library), "--top", "0"])


def test_paths_with_spaces_are_quoted(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    lib = tmp_path / "my lib"
    lib.mkdir()
    _paper(lib, "a b", "Spaced", "## 本文\nzeolite\n")
    sl.main(["zeolite", "--library", str(lib)])
    assert f'要約: "{lib / "a b.md"}"' in capsys.readouterr().out


def test_snippet_stays_aligned_after_full_width_text(tmp_path: Path) -> None:
    lib = tmp_path / "md"
    lib.mkdir()
    _paper(lib, "fw", "Full width", "## 本文\n" + "ＡＢＣ（株）㈱" * 40 + " target zeolite here\n")
    (hit,) = sl.search(sl.load_library(lib), ["zeolite"])
    assert "zeolite" in hit.snippet


def test_snippet_finds_half_width_katakana(tmp_path: Path) -> None:
    lib = tmp_path / "md"
    lib.mkdir()
    _paper(lib, "hw", "Half width", "## 本文\n" + "前置きの文。" * 40 + "ここで ﾎﾟﾘﾏｰ を合成した。\n")
    (hit,) = sl.search(sl.load_library(lib), ["ポリマー"])
    assert "ポリマー" in hit.snippet


# ---------- マージ前の確かめのレビュー（2026-11-12 python-reviewer）----------

ZEOLITE = "---\ntitle: Zeolite paper\n---\n# Zeolite paper\n\n## 主要な結果\nsolid state zeolite 結晶構造\n"


@pytest.mark.parametrize("encoding", ["utf-16", "utf-16-le", "utf-16-be"])
def test_utf16_files_are_searchable_not_counted_as_garbage(tmp_path: Path, encoding: str) -> None:
    lib = tmp_path / "md"
    lib.mkdir()
    (lib / "u16.md").write_bytes(ZEOLITE.encode(encoding))  # utf-16 は BOM つき、-le・-be は BOM なし
    _paper(lib, "other", "Other paper", "## 本文\nnothing here\n")
    hits = sl.search(sl.load_library(lib), ["zeolite"])
    assert hits and hits[0].paper.path.stem == "u16" and hits[0].paper.title == "Zeolite paper"


def test_a_utf8_file_with_one_broken_byte_is_still_searchable(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    lib = tmp_path / "md"
    lib.mkdir()
    (lib / "broken.md").write_bytes(ZEOLITE.encode("utf-8") + b"\xff")
    hits = sl.search(sl.load_library(lib), ["結晶構造"])
    assert hits and hits[0].paper.path.stem == "broken"
    sl.main(["結晶構造", "--library", str(lib)])
    out = capsys.readouterr().out
    assert "broken.md" in out and "文字コード" in out          # 推定して読んだことを知らせる


def test_a_shift_jis_file_is_reported_as_guessed(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    lib = tmp_path / "md"
    lib.mkdir()
    (lib / "sjis.md").write_bytes("# 分子結晶の研究\n\n## 主要な結果\n分子結晶で反応が進んだ。\n".encode("cp932"))
    sl.main(["分子結晶", "--library", str(lib)])
    out = capsys.readouterr().out
    assert "sjis.md" in out and "文字コード" in out


def test_frontmatter_keys_are_case_insensitive(tmp_path: Path) -> None:
    lib = tmp_path / "md"
    lib.mkdir()
    (lib / "b.md").write_text("---\nTitle: Capital Key\nDOI: 10.1/y\nAuthor: [Kim S]\n---\n\n## Results\nok\n", encoding="utf-8")
    (paper,) = sl.load_library(lib)
    assert paper.title == "Capital Key" and paper.doi == "10.1/y" and paper.authors == ("Kim S",)
    assert sl.search([paper], ["Capital"])


def test_unindented_list_items_stay_in_the_frontmatter(tmp_path: Path) -> None:
    lib = tmp_path / "md"
    lib.mkdir()
    (lib / "y.md").write_text("---\ntags:\n- a1\n- b2\ntitle: T\ndoi: 10.1/x\nyear: 2021\n---\n# H\n", encoding="utf-8")
    (paper,) = sl.load_library(lib)
    assert paper.tags == ("a1", "b2") and paper.title == "T" and paper.doi == "10.1/x" and paper.year == "2021"


@pytest.mark.parametrize("style", [">", "|", ">-", "|+"])
def test_block_scalar_titles_are_read(tmp_path: Path, style: str) -> None:
    lib = tmp_path / "md"
    lib.mkdir()
    (lib / "z.md").write_text(f"---\ntitle: {style}\n  A long title\n  that wraps\nyear: 2019\n---\n# H\n", encoding="utf-8")
    (paper,) = sl.load_library(lib)
    assert paper.title == "A long title that wraps" and paper.year == "2019"


@pytest.mark.parametrize("query", ["Tanaka", "10.1000/abc", "Acta Testica"])
def test_authors_doi_and_journal_are_searchable(tmp_path: Path, query: str) -> None:
    lib = tmp_path / "md"
    lib.mkdir()
    (lib / "t.md").write_text(
        "---\ntitle: Zeolites\nauthors: [Tanaka Hiroshi, Suzuki Ken]\njournal: Acta Testica\ndoi: 10.1000/abc\n---\n"
        "# Zeolites\n\n## 本文\nzeolite\n", encoding="utf-8")
    _paper(lib, "other", "Other paper", "## 本文\nnothing here\n")
    hits = sl.search(sl.load_library(lib), [query])
    assert hits and hits[0].paper.path.stem == "t"


def test_json_is_printed_even_for_an_empty_library(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    lib = tmp_path / "md"
    lib.mkdir()
    assert sl.main(["zeolite", "--library", str(lib), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["papers"] == 0 and data["hits"] == []


def test_the_empty_library_message_does_not_repeat_the_count(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    lib = tmp_path / "md"
    lib.mkdir()
    sl.main(["zeolite", "--library", str(lib)])
    assert capsys.readouterr().out.count("登録済み 0 本") == 1


@pytest.mark.parametrize("text,expected", [("άλφα", ["αλφα"]), ("Ώ", ["ω"])])
def test_accented_greek_is_folded(text: str, expected: list[str]) -> None:
    assert sl.tokenize(text) == expected


def test_skill_requires_both_url_and_label_for_web_claims() -> None:
    skill = (Path(sl.__file__).resolve().parent.parent / "SKILL.md").read_text(encoding="utf-8")
    assert "URL か「（Paper DB 未登録）」" not in skill
    assert "URL と「（Paper DB 未登録）」の両方" in skill
    assert "（根拠なし・推測）" in skill.split("### Step 5")[1]   # 答えの形にも、出どころの無い文の扱いがある


JAPANESE = "# 結晶構造の研究\n\n## 結果\n分子結晶で反応が進んだ。\n"


def test_a_japanese_utf16_file_with_a_bom_is_searchable(tmp_path: Path) -> None:
    lib = tmp_path / "md"
    lib.mkdir()
    (lib / "ja16.md").write_bytes(JAPANESE.encode("utf-16"))  # NUL が少なく、BOM でしか分からない
    hits = sl.search(sl.load_library(lib), ["結晶構造"])
    assert hits and hits[0].paper.title == "結晶構造の研究"


@pytest.mark.parametrize("encoding", ["utf-16-le", "utf-16-be"])
def test_a_japanese_utf16_file_without_a_bom_is_searchable_not_garbage(tmp_path: Path, encoding: str) -> None:
    """NUL が少なく（日本語が多い）BOM も無い UTF-16。cp932 では NUL まじりの化けた字に読めてしまうので、
    NUL のバイトの位置で UTF-16 として読む（Codex #72: 以前は「読めない」に数え、探せなかった）。"""
    lib = tmp_path / "md"
    lib.mkdir()
    (lib / "ja16.md").write_bytes(JAPANESE.encode(encoding))
    papers, unreadable = sl.load_library_report(lib)
    assert unreadable == [] and [p.title for p in papers] == ["結晶構造の研究"]
    assert papers[0].encoding_note == "UTF-16"


def test_a_utf16_file_is_listed_for_resaving(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    lib = tmp_path / "md"
    lib.mkdir()
    (lib / "u16.md").write_bytes(ZEOLITE.encode("utf-16"))
    sl.main(["zeolite", "--library", str(lib)])
    out = capsys.readouterr().out
    assert "文字コードを推定して読んだ 1 本" in out and "u16.md" in out


def test_tags_and_keywords_are_merged(tmp_path: Path) -> None:
    lib = tmp_path / "md"
    lib.mkdir()
    (lib / "k.md").write_text("---\ntitle: T\ntags: [mof]\nkeywords:\n  - zeolite\n---\n# T\n", encoding="utf-8")
    (paper,) = sl.load_library(lib)
    assert paper.tags == ("mof", "zeolite")


# ---------- 確かめの周 2（2026-11-12）----------

def test_inline_tags_and_inline_keywords_are_merged(tmp_path: Path) -> None:
    lib = tmp_path / "md"
    lib.mkdir()
    (lib / "k.md").write_text("---\ntitle: T\ntags: [a1, b2]\nkeywords: [c3, d4]\n---\n# T\n", encoding="utf-8")
    (paper,) = sl.load_library(lib)
    assert paper.tags == ("a1", "b2", "c3", "d4")


def test_a_bullet_after_a_scalar_in_an_unclosed_frontmatter_starts_the_body(tmp_path: Path) -> None:
    lib = tmp_path / "md"
    lib.mkdir()
    (lib / "u.md").write_text("---\ntitle: X\nyear: 2020\n- **Authors**: Kim A\n\n## Results\nok\n", encoding="utf-8")
    (paper,) = sl.load_library(lib)
    assert paper.title == "X" and paper.year == "2020" and paper.authors == ("Kim A",)


def test_a_repeated_key_does_not_append_its_block_to_the_first_value(tmp_path: Path) -> None:
    lib = tmp_path / "md"
    lib.mkdir()
    (lib / "r.md").write_text("---\ntitle: X\nTitle: >\n  Y\nyear: 2001\n---\n# H\n", encoding="utf-8")
    (paper,) = sl.load_library(lib)
    assert paper.title == "X" and paper.year == "2001"


def test_the_doi_link_prefix_is_not_indexed(tmp_path: Path) -> None:
    lib = tmp_path / "md"
    lib.mkdir()
    (lib / "d.md").write_text("---\ntitle: T\ndoi: https://doi.org/10.1/xyz\n---\n# T\n\n## 本文\nzeolite\n", encoding="utf-8")
    papers = sl.load_library(lib)
    assert sl.search(papers, ["https"]) == [] and sl.search(papers, ["10.1/xyz"])


# ---------- Codex の事後レビュー（2026-11-17）----------

def _one(tmp_path: Path, data: bytes, query: str) -> tuple[list[sl.Paper], list[sl.Hit]]:
    lib = tmp_path / "md"
    lib.mkdir()
    (lib / "paper.md").write_bytes(data)
    papers = sl.load_library(lib)
    return papers, sl.search(papers, [query])


def test_a_bomless_utf16_that_also_decodes_as_utf8_is_read_as_utf16(tmp_path: Path) -> None:
    """Codex #72: 日本語の多い BOM の無い UTF-16 は NUL が 2 割ほどで UTF-16 の判定を通らず、しかも UTF-8 として
    読めてしまい（NUL と制御文字の列）、黙って探せなかった。"""
    papers, hits = _one(tmp_path, "# 分子結晶\n\n## 分子結晶\n分子結晶\n".encode("utf-16-le"), "分子結晶")
    assert hits and papers[0].title == "分子結晶" and papers[0].encoding_note == "UTF-16"


def test_one_broken_byte_in_a_short_utf8_file_does_not_turn_it_into_shift_jis(tmp_path: Path) -> None:
    """Codex #72: 非 ASCII の少ない UTF-8 は、壊れた 1 バイトで 5% を超え、cp932 で化けた字に読んでいた。"""
    papers, hits = _one(tmp_path, "# 結晶\n".encode("utf-8") + b"\xff", "結晶")
    assert hits and papers[0].title == "結晶" and papers[0].encoding_note.startswith("UTF-8")


def test_yaml_escapes_in_a_double_quoted_title_are_decoded(tmp_path: Path) -> None:
    data = '---\ntitle: "\\u5206\\u5b50\\u7d50\\u6676 \\"MOF\\""\n---\n# 本文の題\n\n## 結果\n85 %\n'.encode()
    papers, hits = _one(tmp_path, data, "分子結晶")
    assert papers[0].title == '分子結晶 "MOF"' and hits


def test_the_body_heading_is_searchable_even_when_the_frontmatter_has_a_title(tmp_path: Path) -> None:
    """Codex #72: frontmatter の題名があると本文の # 見出しが索引から消えていた。"""
    data = "---\ntitle: Short name\n---\n# 分子結晶の固相反応\n\n## 結果\n85 %\n".encode()
    _papers, hits = _one(tmp_path, data, "固相反応")
    assert hits


@pytest.mark.parametrize("front", [
    "tags: mof\nkeywords: [zeolite]\n",
    "keywords: [zeolite]\ntags: mof\n",
    "tags: mof\nkeywords:\n  - zeolite\n",
])
def test_a_scalar_tag_and_a_list_of_keywords_are_merged(tmp_path: Path, front: str) -> None:
    """Codex #72: tags が文字列で keywords がリストだと、後の方を黙って捨てていた。"""
    papers, hits = _one(tmp_path, f"---\ntitle: Example\n{front}---\n# Example\n".encode(), "zeolite")
    assert set(papers[0].tags) == {"mof", "zeolite"} and hits


def test_a_word_only_in_a_section_heading_is_searchable(tmp_path: Path) -> None:
    """Codex #72: 節の見出し（## Zeolite synthesis）が索引に入らず、見出しにだけある対象名で探せなかった。"""
    _papers, hits = _one(tmp_path, b"# Example\n\n## Zeolite synthesis\nYield: 85 %\n", "zeolite")
    assert hits and hits[0].section == "Zeolite synthesis"


# ---------- python-reviewer（v2.4.2 の 1 周目）----------

def test_an_escape_beyond_unicode_does_not_stop_the_search(tmp_path: Path) -> None:
    """HIGH: \\U の 8 桁が Unicode の外（0x110000 以上）だと chr() が ValueError を上げ、1 本のために検索全体が落ちた。"""
    lib = tmp_path / "md"
    lib.mkdir()
    (lib / "bad.md").write_text('---\ntitle: "C:\\UDEADBEEF zeolite"\n---\n# x\n', encoding="utf-8")
    (lib / "good.md").write_text("# good zeolite\n", encoding="utf-8")
    papers = sl.load_library(lib)
    assert {h.paper.path.stem for h in sl.search(papers, ["zeolite"])} == {"bad", "good"}
    assert next(p for p in papers if p.path.stem == "bad").title == "C:\\UDEADBEEF zeolite"


@pytest.mark.parametrize("heading,query", [("## Summary", "summary"), ("## 主要な結果（数値・数式・図表要点すべて）", "数式"),
                                           ("## 手法（詳細）", "詳細"), ("## Results", "results")])
def test_template_section_headings_are_not_indexed(tmp_path: Path, heading: str, query: str) -> None:
    """MEDIUM: 要約の決まった見出し（Summary・主要な結果…）を索引に入れると、その語の問いが全部の論文に当たる。"""
    lib = tmp_path / "md"
    lib.mkdir()
    for name in ("a", "b"):
        (lib / f"{name}.md").write_text(f"# Paper {name}\n\n{heading}\nnothing here\n", encoding="utf-8")
    assert sl.search(sl.load_library(lib), [query]) == []


# ---------- Codex の確かめの周（2026-11-17、v2.4.2）----------

def test_half_width_katakana_in_shift_jis_is_not_read_as_broken_utf8(tmp_path: Path) -> None:
    """Codex v2.4.2 #5: cp932 の半角カナ（ﾏｲ = CF B2）は偶然 2 バイトの UTF-8 の字になり、「壊れた字より正しい字が多い」
    の条件で壊れた UTF-8 と決め、題名が化けて探せなかった（v2.4.1 までは cp932 で読めていた）。"""
    papers, hits = _one(tmp_path, "# ﾏｲｸﾛ波\n\n## Results\nYield: 85 %\n".encode("cp932"), "マイクロ波")
    assert papers[0].title == "ﾏｲｸﾛ波" and papers[0].encoding_note == "Shift_JIS（cp932）" and hits


@pytest.mark.parametrize("title", ["Müller", "Étude de l'été", "αβγδ", "Привет мир"])
def test_one_broken_byte_in_a_short_latin_utf8_file_is_still_utf8(tmp_path: Path, title: str) -> None:
    """python-reviewer（3 周目）M2: 2 バイトの字を証拠に数えなくしたため、ラテン・ギリシャ・キリルの短い UTF-8 が
    1 バイトの壊れで cp932 に落ちて化けた。cp932 でも損なわずには読めないときは、2 バイトの字も UTF-8 の証拠に数える。"""
    papers, _hits = _one(tmp_path, f"# {title}\n".encode("utf-8") + b"\xff", "x")
    assert papers[0].title == title and papers[0].encoding_note.startswith("UTF-8")
