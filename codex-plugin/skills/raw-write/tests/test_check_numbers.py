"""check_numbers.py（原稿・スライドの数を事実の一覧と照合する）のテスト。"""
from __future__ import annotations

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


@pytest.mark.parametrize("draft", ["0.63", "0.64"])
def test_rounding_down_or_up_to_the_written_digits_is_rounded(draft: str) -> None:
    assert _status(draft, "R² = 0.634") == "rounded"


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
    assert [(n.location, str(n.mantissa)) for n in nums] == [("スライド 2", "31.44"), ("スライド 10", "0.5")]


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
