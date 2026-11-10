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
