"""check_numbers.py（原稿・スライドの数を事実の一覧と照合する）のテスト。"""
from __future__ import annotations

import sys
import zipfile
from decimal import Decimal
from pathlib import Path

import pytest

import check_numbers as cn


def _values(text: str, include_integers: bool = False) -> list[str]:
    """抽出した数を「仮数e指数」の文字列で返す（比べやすくするため）。"""
    nums = cn.extract_numbers(text, location="L1", include_integers=include_integers)
    return [f"{n.mantissa}e{n.exponent}" for n in nums]


# ---------- 抽出 ----------

def test_extracts_decimals_and_skips_integers_by_default() -> None:
    assert _values("収率は 85.3 % で、試料は 12 個、温度は 298.15 K。") == ["85.3e0", "298.15e0"]


def test_include_integers_adds_whole_numbers() -> None:
    assert _values("試料は 12 個、85.3 %", include_integers=True) == ["12e0", "85.3e0"]


def test_range_dash_between_numbers_is_not_a_minus_sign() -> None:
    assert _values("|cos| は 0.689–0.999、幅は 1.5-2.5") == ["0.689e0", "0.999e0", "1.5e0", "2.5e0"]


@pytest.mark.parametrize("text", ["障壁は −3.33 kcal/mol", "障壁は -3.33", "障壁は –3.33", "(−3.33)", "ΔE=-3.33"])
def test_minus_sign_variants_give_a_negative_number(text: str) -> None:
    assert _values(text) == ["-3.33e0"]


@pytest.mark.parametrize(
    "text",
    [
        "B3LYP/6-31G(d) と ωB97X-D/def2-SVP で計算",
        "raw v2.0.1 を使う",
        "バージョン 2.0.1 を使う",
        "doi: 10.1021/acs.jpca.5b00001 を参照",
        "https://doi.org/10.1021/jp123 と https://example.com/a1.5b",
        "出典 https://example.com/page?ratio=1.5 を見る",
        "図は [図](./figs/fig_rate_1.25.png) にある",
        "[値](./a.md?v=0.5) を見る",
        "ファイル run_0.5_v2.log",
    ],
)
def test_identifiers_versions_dois_and_urls_are_not_numbers(text: str) -> None:
    assert _values(text) == []


def test_integers_glued_to_letters_are_identifiers() -> None:
    assert _values("B3LYP/6-31G(d) で計算", include_integers=True) == []


def test_superscript_power_of_ten_is_an_exponent_not_digits() -> None:
    assert _values("濃度は 1.2×10² M") == ["1.2e2"]


def test_a_squared_decimal_keeps_its_own_digits() -> None:
    assert _values("誤差は 0.5² + 0.3²") == ["0.5e0", "0.3e0"]


def test_unit_exponents_written_with_a_hyphen_are_not_numbers() -> None:
    assert _values("吸収は 1650 cm-1 に出る", include_integers=True) == ["1650e0"]


def test_superscript_unit_exponents_are_not_numbers() -> None:
    assert _values("R² は 0.634、吸収は 1650 cm⁻¹", include_integers=True) == ["0.634e0", "1650e0"]


def test_slash_separated_pairs_are_both_numbers_but_paths_are_not() -> None:
    assert _values("橋は 3.002/2.078 Å、図は figs/1.25 にある") == ["3.002e0", "2.078e0"]


def test_latex_double_hyphen_range_is_not_a_minus_sign() -> None:
    assert _values("0.947--0.987 と 1.03--1.09") == ["0.947e0", "0.987e0", "1.03e0", "1.09e0"]


def test_full_width_digits_are_normalized() -> None:
    assert _values("収率は８５．３％") == ["85.3e0"]


def test_thousands_separator_is_one_number() -> None:
    assert _values("合計 1,765.5 mg と 0.5,0.6") == ["1765.5e0", "0.5e0", "0.6e0"]


@pytest.mark.parametrize("text", ["k = 1.2e-3 s⁻¹", "k = 1.2×10⁻³ s⁻¹", "k = 1.2 × 10^-3", "k = 1.2 x 10^{-3}"])
def test_scientific_notation_keeps_the_exponent(text: str) -> None:
    assert _values(text) == ["1.2e-3"]


def test_decimals_count_digits_after_the_point() -> None:
    (n,) = cn.extract_numbers("0.630", location="L1")
    assert n.decimals == 3 and n.mantissa == Decimal("0.630")


# ---------- 照合 ----------

def _facts(text: str) -> list[cn.Number]:
    return cn.extract_numbers(text, location="facts", include_integers=True)


def _status(draft: str, facts: str) -> str:
    (n,) = cn.extract_numbers(draft, location="L1")
    return cn.classify(n, _facts(facts)).status


def test_exact_match() -> None:
    assert _status("0.634", "R² = 0.634") == "exact"


def test_trailing_zero_is_still_exact() -> None:
    assert _status("0.50", "比は 0.5") == "exact"


def test_rounding_half_up_to_the_written_digits_is_rounded() -> None:
    assert _status("0.63", "R² = 0.634") == "rounded"


def test_rounding_up_without_a_bound_is_a_mismatch() -> None:
    assert _status("0.64", "R² = 0.634") == "round_mismatch"


def test_a_number_two_steps_away_is_missing() -> None:
    assert _status("0.62", "R² = 0.634") == "missing"


def test_sign_flip_is_reported_separately() -> None:
    assert _status("-3.33", "ΔΔE = 3.33") == "sign"


def test_scientific_draft_matches_plain_fact() -> None:
    assert _status("1.2×10⁻³", "k = 0.0012") == "exact"


def test_rounded_match_names_the_fact_it_came_from() -> None:
    (n,) = cn.extract_numbers("0.63", location="L1")
    finding = cn.classify(n, _facts("R² = 0.634"))
    assert finding.source == "0.634"


# ---------- 読み込み ----------

def test_markdown_numbers_carry_line_numbers(tmp_path: Path) -> None:
    p = tmp_path / "draft.md"
    p.write_text("# 結果\n\n障壁は 31.44 kcal/mol。\n比は 0.5。\n", encoding="utf-8")
    nums = cn.read_numbers(p)
    assert [(n.location, str(n.mantissa)) for n in nums] == [("L3", "31.44"), ("L4", "0.5")]


def test_tex_citations_refs_and_comments_are_skipped(tmp_path: Path) -> None:
    p = tmp_path / "draft.tex"
    p.write_text(
        "障壁は 31.44 \\cite{han2021.5} で図 \\ref{fig:1.2} に示す。% 旧値 30.1\n"
        "\\label{eq:2.5}比は 0.5\\% だった。\n",
        encoding="utf-8",
    )
    assert [str(n.mantissa) for n in cn.read_numbers(p)] == ["31.44", "0.5"]


def test_tex_layout_lengths_and_key_value_options_are_skipped(tmp_path: Path) -> None:
    p = tmp_path / "draft.tex"
    p.write_text(
        "\\begin{subfigure}[b]{0.4125\\widefig}\\hspace{0.04\\widefig}\n"
        "\\begin{tabular}{p{0.47\\linewidth}S[table-format=-2.2]}\n"
        "\\includegraphics[width=0.5\\linewidth]{a.png} 障壁は \\SI{31.44}{\\kilo\\joule}\n",
        encoding="utf-8",
    )
    assert [str(n.mantissa) for n in cn.read_numbers(p)] == ["31.44"]


def test_exponent_only_difference_is_its_own_status() -> None:
    (n,) = cn.extract_numbers("\\num{12.55e-5}", location="L1")
    finding = cn.classify(n, _facts("α_c 12.55、α_V 20.00 ×10⁻⁵ K⁻¹"))
    assert finding.status == "exponent" and finding.source == "12.55"


def test_exponent_status_fails_the_check(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    draft = tmp_path / "draft.md"
    facts = tmp_path / "facts.md"
    draft.write_text("係数は 6.36×10⁻⁴\n", encoding="utf-8")
    facts.write_text("係数 6.36×10⁻⁵\n", encoding="utf-8")
    assert cn.main([str(draft), "--facts", str(facts)]) == 1
    assert "指数だけ違う: 1" in capsys.readouterr().out


def test_several_facts_files_are_combined(tmp_path: Path) -> None:
    draft = tmp_path / "draft.md"
    comp = tmp_path / "facts-computation.md"
    expt = tmp_path / "facts-experiments.md"
    draft.write_text("障壁 31.44、収率 85.3\n", encoding="utf-8")
    comp.write_text("31.44\n", encoding="utf-8")
    expt.write_text("85.3\n", encoding="utf-8")
    assert cn.main([str(draft), "--facts", str(comp), "--facts", str(expt)]) == 0


def _write_zip(path: Path, members: dict[str, str]) -> None:
    with zipfile.ZipFile(path, "w") as z:
        for name, body in members.items():
            z.writestr(name, body)


def test_docx_paragraphs_are_read(tmp_path: Path) -> None:
    p = tmp_path / "draft.docx"
    body = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
        "<w:p><w:r><w:t>障壁は 31.</w:t></w:r><w:r><w:t>44 kcal/mol</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>比は 0.5</w:t></w:r></w:p>"
        "</w:body></w:document>"
    )
    _write_zip(p, {"word/document.xml": body})
    nums = cn.read_numbers(p)
    assert [(n.location, str(n.mantissa)) for n in nums] == [("段落 1", "31.44"), ("段落 2", "0.5")]


def test_pptx_slides_are_read_in_slide_order(tmp_path: Path) -> None:
    p = tmp_path / "deck.pptx"
    ns = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
    _write_zip(
        p,
        {
            "ppt/slides/slide10.xml": f"<p:sld {ns}><a:p><a:r><a:t>比は 0.5</a:t></a:r></a:p></p:sld>",
            "ppt/slides/slide2.xml": f"<p:sld {ns}><a:p><a:r><a:t>障壁 31.44</a:t></a:r></a:p></p:sld>",
        },
    )
    nums = cn.read_numbers(p)
    # presentation.xml が無い（最小の zip）ときはファイル番号の順に 1, 2, … と付ける
    assert [(n.location, str(n.mantissa)) for n in nums] == [("スライド 1", "31.44"), ("スライド 2", "0.5")]


def test_unsupported_extension_raises(tmp_path: Path) -> None:
    p = tmp_path / "draft.pdf"
    p.write_bytes(b"%PDF")
    with pytest.raises(ValueError, match="対応していない"):
        cn.read_numbers(p)


# ---------- CLI ----------

def test_cli_exit_1_and_lists_missing_numbers(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    draft = tmp_path / "draft.md"
    facts = tmp_path / "facts.md"
    draft.write_text("障壁は 31.44 と 22.19、R² は 0.63。\n補償は 20.5 %。\n", encoding="utf-8")
    facts.write_text("- ΔG‡ 31.44（J:x L64）\n- ΔG TS_a 22.19\n- R² 0.634\n", encoding="utf-8")
    code = cn.main([str(draft), "--facts", str(facts)])
    out = capsys.readouterr().out
    assert code == 1
    assert "一覧に無い数" in out and "L2" in out and "20.5" in out
    assert "丸めて一致" in out and "0.634" in out


def test_cli_exit_0_when_everything_traces(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    draft = tmp_path / "draft.md"
    facts = tmp_path / "facts.md"
    draft.write_text("障壁は 31.44。\n", encoding="utf-8")
    facts.write_text("31.44\n", encoding="utf-8")
    assert cn.main([str(draft), "--facts", str(facts)]) == 0
    assert "一覧に無い数: 0" in capsys.readouterr().out


def test_cli_missing_file_exits_2_with_message(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    facts = tmp_path / "facts.md"
    facts.write_text("1.0\n", encoding="utf-8")
    code = cn.main([str(tmp_path / "nope.md"), "--facts", str(facts)])
    assert code == 2
    assert "見つかりません" in capsys.readouterr().err


def test_cli_empty_facts_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    draft = tmp_path / "draft.md"
    facts = tmp_path / "facts.md"
    draft.write_text("31.44\n", encoding="utf-8")
    facts.write_text("数の無い一覧\n", encoding="utf-8")
    assert cn.main([str(draft), "--facts", str(facts)]) == 2
    assert "事実の一覧に数が 1 つも" in capsys.readouterr().err


def test_a_broken_docx_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    draft = tmp_path / "draft.docx"
    facts = tmp_path / "facts.md"
    draft.write_bytes(b"not a zip")
    facts.write_text("1.0\n", encoding="utf-8")
    assert cn.main([str(draft), "--facts", str(facts)]) == 2
    assert "読めません" in capsys.readouterr().err


def test_a_fact_too_large_to_round_is_skipped_not_crashed() -> None:
    (n,) = cn.extract_numbers("0.5", location="L1")
    assert cn.classify(n, _facts("1.0×10^40")).status == "missing"


# ---------- レビューの指摘（2026-11-10）----------

@pytest.mark.parametrize(
    "text", ["$1.5\\times10^{-3}$", "1.5 \\times 10^{-3}", "1.5\\cdot 10^{-3}", "1.5·10^-3"]
)
def test_latex_times_and_cdot_exponents(text: str) -> None:
    assert _values(text) == ["1.5e-3"]


@pytest.mark.parametrize(
    "text,expected", [("0.5 x 100 mm", ["0.5e0"]), ("格子 1.5 x 1000", ["1.5e0"]), ("0.5 x 105 mm", ["0.5e0"])]
)
def test_x_followed_by_a_plain_number_is_not_an_exponent(text: str, expected: list[str]) -> None:
    assert _values(text) == expected


def test_dimensions_written_with_x_keep_both_numbers() -> None:
    assert _values("結晶は 2.5x2.5 mm と 5.0×10.0 mm") == ["2.5e0", "2.5e0", "5.0e0", "10.0e0"]


def test_absurd_exponents_are_ignored_not_crashed() -> None:
    assert _values("1.5×10^99999999999 と 1e999999999999") == []


def test_unreadable_file_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    draft = tmp_path / "draft.md"
    facts = tmp_path / "facts.md"
    draft.write_text("31.44\n", encoding="utf-8")
    facts.write_text("31.44\n", encoding="utf-8")
    draft.chmod(0)
    try:
        if __import__("os").access(draft, __import__("os").R_OK):
            pytest.skip("root などで権限を無視できる環境")
        assert cn.main([str(draft), "--facts", str(facts)]) == 2
        assert "読めません" in capsys.readouterr().err
    finally:
        draft.chmod(0o644)


def test_report_survives_a_cp932_console(tmp_path: Path) -> None:
    import subprocess

    draft = tmp_path / "draft_✓.md"  # ✓ は cp932 で書けない
    facts = tmp_path / "facts.md"
    draft.write_text("比は 1.2×10⁻³ と 0.63\n", encoding="utf-8")
    facts.write_text("0.634 と 0.0012\n", encoding="utf-8")
    script = Path(cn.__file__)
    env = {**__import__("os").environ, "PYTHONIOENCODING": "cp932"}
    res = subprocess.run(
        [sys.executable, str(script), str(draft), "--facts", str(facts)], capture_output=True, env=env
    )
    assert res.returncode == 0, res.stderr.decode("cp932", "replace")


def test_csv_commas_separate_cells_not_thousands(tmp_path: Path) -> None:
    p = tmp_path / "table.csv"
    p.write_text("A,5,123.4\n1,123.4,0.5\n", encoding="utf-8")
    assert [str(n.mantissa) for n in cn.read_numbers(p)] == ["123.4", "123.4", "0.5"]


def test_utf8_bom_does_not_hide_the_first_list_marker(tmp_path: Path) -> None:
    p = tmp_path / "facts.md"
    p.write_text("1. 障壁 31.44\n", encoding="utf-8-sig")
    assert [str(n.mantissa) for n in cn.read_numbers(p, include_integers=True)] == ["31.44"]


@pytest.mark.parametrize("text,expected", [("$E-0.5$", ["0.5e0"]), ("pH7.4 の緩衝液", ["7.4e0"])])
def test_a_decimal_after_a_letter_is_still_read(text: str, expected: list[str]) -> None:
    assert _values(text) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("−0.5–−0.2 V", ["-0.5e0", "-0.2e0"]),
        ("-0.5–-0.2 V", ["-0.5e0", "-0.2e0"]),
        ("$-1.2$--$-0.8$ V", ["-1.2e0", "-0.8e0"]),
        ("1.5+-0.2", ["1.5e0", "0.2e0"]),
    ],
)
def test_negative_right_end_of_a_range_and_plus_minus(text: str, expected: list[str]) -> None:
    assert _values(text) == expected


def _tex_numbers(tmp_path: Path, body: str) -> list[str]:
    p = tmp_path / "d.tex"
    p.write_text(body, encoding="utf-8")
    return [str(n.mantissa) for n in cn.read_numbers(p)]


@pytest.mark.parametrize(
    "line",
    [
        "a\\\\[0.5em] b",
        "\\renewcommand{\\arraystretch}{1.2}",
        "\\scalebox{0.8}{x}",
        "\\resizebox{0.9\\linewidth}{!}{x}",
        "\\definecolor{a}{rgb}{0.2,0.4,0.6}",
        "\\geometry{margin=2.5cm}",
        "\\usepackage[margin=2.5cm]{geometry}",
        "\\fontsize{10.5}{12.5}\\selectfont",
        "\\linespread{1.3}",
        "\\textcolor[rgb]{0.1,0.2,0.3}{x}",
    ],
)
def test_more_tex_layout_is_skipped(tmp_path: Path, line: str) -> None:
    assert _tex_numbers(tmp_path, line + " 値は 31.44\n") == ["31.44"]


@pytest.mark.parametrize(
    "text", ["Figure 2.1 に示す", "Table 3.2 の値", "図 2.1 に示す", "Python 3.12 で動く", "version 2.5 を使う", "式 (3.4) より"]
)
def test_numbering_and_versions_after_a_label_are_skipped(text: str) -> None:
    assert _values(text) == []


def test_half_up_rounding_is_rounded() -> None:
    assert _status("0.13", "0.125") == "rounded"


@pytest.mark.parametrize("draft,fact", [("0.2", "0.123"), ("0.6", "0.51"), ("12.4", "12.46")])
def test_wrong_side_rounding_fails(draft: str, fact: str) -> None:
    assert _status(draft, fact) == "round_mismatch"


@pytest.mark.parametrize("draft", ["R² ≤ 0.64", "R² < 0.64", "0.64 以下", "at most 0.64"])
def test_rounding_toward_a_stated_bound_is_accepted(draft: str) -> None:
    (n,) = cn.extract_numbers(draft, location="L1")
    assert cn.classify(n, _facts("0.634")).status == "bound"


def test_markdown_list_markers_in_facts_are_not_facts(tmp_path: Path) -> None:
    p = tmp_path / "facts.md"
    p.write_text("1. 障壁 31.44\n2. 収率 85.3\n", encoding="utf-8")
    assert [str(n.mantissa) for n in cn.read_numbers(p, include_integers=True)] == ["31.44", "85.3"]


def test_an_integer_fact_does_not_vouch_for_a_decimal() -> None:
    assert _status("2.0", "2 h") == "missing"


def test_an_integer_fact_still_matches_scientific_notation() -> None:
    assert _status("1.2×10^3", "1200 個") == "exact"


def test_docx_footnotes_and_pptx_notes_are_read(tmp_path: Path) -> None:
    w = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    docx = tmp_path / "d.docx"
    _write_zip(
        docx,
        {
            "word/document.xml": f"<w:document {w}><w:body><w:p><w:r><w:t>本文 1.5</w:t></w:r></w:p></w:body></w:document>",
            "word/footnotes.xml": f"<w:footnotes {w}><w:footnote><w:p><w:r><w:t>脚注 2.5</w:t></w:r></w:p></w:footnote></w:footnotes>",
        },
    )
    assert [(n.location, str(n.mantissa)) for n in cn.read_numbers(docx)] == [("段落 1", "1.5"), ("脚注 1", "2.5")]
    a = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
    pptx = tmp_path / "d.pptx"
    _write_zip(
        pptx,
        {
            "ppt/slides/slide1.xml": f"<p:sld {a}><a:p><a:r><a:t>本文 1.5</a:t></a:r></a:p></p:sld>",
            "ppt/slides/_rels/slide1.xml.rels": (
                '<Relationships><Relationship Id="rId2" Target="../notesSlides/notesSlide7.xml"/></Relationships>'
            ),
            "ppt/notesSlides/notesSlide7.xml": f"<p:notes {a}><a:p><a:r><a:t>原稿 2.5</a:t></a:r></a:p></p:notes>",
        },
    )
    assert [(n.location, str(n.mantissa)) for n in cn.read_numbers(pptx)] == [("スライド 1", "1.5"), ("ノート 1", "2.5")]


def test_superscript_runs_in_docx_and_pptx_become_exponents(tmp_path: Path) -> None:
    w = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    docx = tmp_path / "d.docx"
    body = (
        f"<w:document {w}><w:body><w:p><w:r><w:t>k = 1.2×10</w:t></w:r>"
        '<w:r><w:rPr><w:vertAlign w:val="superscript"/></w:rPr><w:t>−3</w:t></w:r></w:p></w:body></w:document>'
    )
    _write_zip(docx, {"word/document.xml": body})
    assert [f"{n.mantissa}e{n.exponent}" for n in cn.read_numbers(docx)] == ["1.2e-3"]
    a = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
    pptx = tmp_path / "d.pptx"
    slide = (
        f'<p:sld {a}><a:p><a:r><a:t>k = 1.2×10</a:t></a:r><a:r><a:rPr lang="en-US" baseline="30000"/>'
        "<a:t>-3</a:t></a:r></a:p></p:sld>"
    )
    _write_zip(pptx, {"ppt/slides/slide1.xml": slide})
    assert [f"{n.mantissa}e{n.exponent}" for n in cn.read_numbers(pptx)] == ["1.2e-3"]


def test_pptx_locations_follow_the_presentation_order(tmp_path: Path) -> None:
    a = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
    pptx = tmp_path / "d.pptx"
    _write_zip(
        pptx,
        {
            "ppt/presentation.xml": '<p:presentation><p:sldIdLst><p:sldId id="256" r:id="rId9"/>'
            '<p:sldId id="257" r:id="rId8"/></p:sldIdLst></p:presentation>',
            "ppt/_rels/presentation.xml.rels": '<Relationships><Relationship Id="rId8" Target="slides/slide1.xml"/>'
            '<Relationship Id="rId9" Target="slides/slide2.xml"/></Relationships>',
            "ppt/slides/slide1.xml": f"<p:sld {a}><a:p><a:r><a:t>後ろ 1.5</a:t></a:r></a:p></p:sld>",
            "ppt/slides/slide2.xml": f"<p:sld {a}><a:p><a:r><a:t>前 2.5</a:t></a:r></a:p></p:sld>",
        },
    )
    assert [(n.location, str(n.mantissa)) for n in cn.read_numbers(pptx)] == [("スライド 1", "2.5"), ("スライド 2", "1.5")]


@pytest.mark.parametrize(
    "line",
    [
        "31.44（出どころ: results.csv line 42; Fig. 3）",
        "31.44（2026-10-27 の記録、p. 12、No. 5）",
        "31.44 は 2026年11月10日 の測定 [12]",
        "31.44（表 2、図 4、スライド 7、12 行目）",
    ],
)
def test_provenance_numbers_in_facts_are_not_facts(tmp_path: Path, line: str) -> None:
    p = tmp_path / "facts.md"
    p.write_text(line + "\n", encoding="utf-8")
    assert [str(n.mantissa) for n in cn.read_numbers(p, include_integers=True)] == ["31.44"]
