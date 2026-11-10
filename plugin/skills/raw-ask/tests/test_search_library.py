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
    assert sl.main(["x", "--library", str(tmp_path / "none")]) == 2
    assert "見つかりません" in capsys.readouterr().err


def test_empty_library_is_reported(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    lib = tmp_path / "md"
    lib.mkdir()
    assert sl.main(["x", "--library", str(lib)]) == 0
    assert "登録済みの論文がまだありません" in capsys.readouterr().out
