#!/usr/bin/env python3
"""原稿・スライドの数が、事実の一覧（出どころつき）から来ているかを照合する（raw-write / raw-slides）。

記憶で書いた数は、桁も意味もずれる。書き終えたら原稿の数を機械で抜き出し、事実の一覧に在るかを確かめる。

照合の結果は 5 つに分ける:
- そのまま一致: 一覧に同じ値がある（0.50 と 0.5 のように末尾の 0 だけ違うものも含む）
- 丸めて一致: 一覧の値を、原稿の桁で切り捨てか切り上げにすると一致する（元の桁で手で確かめる）
- 指数だけ違う: 仮数は合うが ×10 の何乗かが違う（一覧の書き方の違いか、指数の取り違え）
- 符号が違う: 絶対値だけが一致する
- 一覧に無い数: どれとも合わない（一次記録で引き直す）

既定では小数（と 1.2×10⁻³ のような指数表記）だけを照合する。整数は年・図番号・文献番号と
混ざりやすいので、``--integers`` を付けたときだけ照合する。事実の一覧は書式を問わない
（表でも箇条書きでも、書いてある数をすべて拾う）。

対応する形式: .md .markdown .txt .tex .csv .tsv .docx .pptx

実行: ``python check_numbers.py <原稿> --facts <事実の一覧> [--facts <別の一覧> ...] [--integers]``
終了コード: 0 = 全部たどれた、1 = 一覧に無い数・指数だけ違う数・符号の違う数がある、2 = 入力の誤り
"""
from __future__ import annotations

import argparse
import html
import re
import sys
import unicodedata
import zipfile
from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, InvalidOperation
from pathlib import Path

TEXT_SUFFIXES = frozenset({".md", ".markdown", ".txt", ".tex", ".csv", ".tsv"})
ZIP_SUFFIXES = frozenset({".docx", ".pptx"})
NEGATIVE_SIGNS = frozenset("-−–")  # ハイフンマイナス・マイナス記号（U+2212）・二分ダッシュ
DASHES = frozenset("-−–—")
RANGE_LEFT = frozenset(")]%")  # 「1.5-2.5」「(a)-0.3」のダッシュは範囲・引き算で、符号ではない
REJECT_PREV = frozenset("_.\\^")  # 識別子・版番号・上付きの一部（run_0.5・v2.0.1・s^-1）

_SUPERSCRIPT = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺", "0123456789-+")
_SUPERSCRIPT_RUN = re.compile(r"[⁻⁺]?[⁰¹²³⁴⁵⁶⁷⁸⁹]+")
_URL = re.compile(r"https?://\S+")
_DOI = re.compile(r"\b10\.\d{4,9}/\S+")
_MD_LINK_TARGET = re.compile(r"\]\([^)]*\)")
_TEX_COMMENT = re.compile(r"(?<!\\)%.*$")
_TEX_KEYVAL_OPTION = re.compile(r"\[[^\]]*=[^\]]*\]")  # [width=0.5\linewidth] [table-format=-2.2]
_TEX_LAYOUT = re.compile(
    r"\\(?:begin\{[^}]*\}|hspace|vspace|setlength|addtolength|rule|raisebox|makebox|parbox)\*?"
    r"(?:\[[^\]]*\])*(?:\{[^}]*\})*"
)
_TEX_LENGTH_MACRO = re.compile(r"\\[A-Za-z]*(?:width|height|skip|size|fig|length)\b")
_TEX_REF = re.compile(
    r"\\(?:cite\w*|ref|eqref|autoref|cref|Cref|label|includegraphics|url|href|bibliography\w*)\*?"
    r"(?:\[[^\]]*\])*\{[^}]*\}"
)
_NUM = re.compile(
    r"(?P<sign>[-+−–])?"
    r"(?P<mant>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?|\.\d+)"
    r"(?:[eE](?P<eexp>[-+−]?\d+)"
    r"|\s*[×xX✕]\s*10\s*\^?\s*\{?(?P<texp>[-+−]?\d+)\}?)?"
)
_W_PARAGRAPH = re.compile(r"<w:p\b[^>]*?(?:/>|>(.*?)</w:p>)", re.S)
_W_TEXT = re.compile(r"<w:t\b[^>]*>(.*?)</w:t>", re.S)
_A_PARAGRAPH = re.compile(r"<a:p\b[^>]*?(?:/>|>(.*?)</a:p>)", re.S)
_A_TEXT = re.compile(r"<a:t\b[^>]*>(.*?)</a:t>", re.S)
_SLIDE_NAME = re.compile(r"ppt/slides/slide(\d+)\.xml$")


@dataclass(frozen=True)
class Number:
    """書かれた 1 つの数。値は ``mantissa × 10^exponent``。"""

    text: str
    mantissa: Decimal
    exponent: int
    decimals: int
    location: str

    @property
    def value(self) -> Decimal:
        return self.mantissa.scaleb(self.exponent)


@dataclass(frozen=True)
class Finding:
    """原稿の 1 つの数の照合結果。``source`` は一致した一覧の数（無ければ None）。"""

    number: Number
    status: str  # "exact" | "rounded" | "exponent" | "sign" | "missing"
    source: str | None


_RANK = {"exact": 0, "rounded": 1, "exponent": 2, "sign": 3, "missing": 4}


def normalize(text: str) -> str:
    """上付きを ^ 付きの数字に直してから NFKC で全角を半角にする（10⁻³ → 10^-3）。"""
    lifted = _SUPERSCRIPT_RUN.sub(lambda m: "^" + m.group(0).translate(_SUPERSCRIPT), text)
    return unicodedata.normalize("NFKC", lifted)


def _strip_noise(line: str) -> str:
    """URL・DOI・Markdown のリンク先は数として読まない。"""
    line = _URL.sub(" ", line)
    line = _DOI.sub(" ", line)
    return _MD_LINK_TARGET.sub("]", line)


def _is_ascii_alnum(ch: str) -> bool:
    return ch.isascii() and ch.isalnum()


def _sign_of(match: re.Match[str], line: str) -> tuple[str, bool]:
    """符号（'-' か ''）と、この数を捨てるべきか、を返す。"""
    sign = match.group("sign")
    start = match.start("sign") if sign else match.start("mant")
    prev = line[start - 1] if start > 0 else ""
    if prev in REJECT_PREV:
        return "", True
    if prev == "/":
        before = line[start - 2] if start > 1 else ""
        return "", before.isascii() and before.isalpha()  # figs/1.25 はパス、3.002/2.078 は値の組
    if not sign:
        return "", _is_ascii_alnum(prev)
    if prev.isascii() and prev.isalpha():
        return "", True  # 単位の指数（s-1）や識別子（X-D）
    if prev.isdigit() or prev in RANGE_LEFT or prev in DASHES:
        return "", False  # 範囲・引き算のダッシュ（LaTeX の 0.947--0.987 も）
    return ("-" if sign in NEGATIVE_SIGNS else ""), False


def _to_number(match: re.Match[str], sign: str, location: str) -> Number:
    mant = match.group("mant").replace(",", "")
    exp_text = match.group("eexp") or match.group("texp")
    exponent = int(exp_text.replace("−", "-")) if exp_text else 0
    decimals = len(mant.split(".")[1]) if "." in mant else 0
    mantissa = Decimal(sign + (mant if not mant.startswith(".") else "0" + mant))
    shown = f"{mantissa}×10^{exponent}" if exp_text else str(mantissa)
    return Number(text=shown, mantissa=mantissa, exponent=exponent, decimals=decimals, location=location)


def extract_numbers(text: str, location: str, include_integers: bool = False) -> list[Number]:
    """1 行（または 1 段落）から数を抜き出す。"""
    line = _strip_noise(normalize(text))
    found: list[Number] = []
    for match in _NUM.finditer(line):
        end = match.end()
        if re.match(r"\.\d", line[end : end + 2]) or _TEX_LENGTH_MACRO.match(line, end):
            continue  # 2.0.1 のような版番号、0.5\linewidth のような長さ
        sign, reject = _sign_of(match, line)
        if reject:
            continue
        number = _to_number(match, sign, location)
        is_integer = number.decimals == 0 and number.exponent == 0 and not match.group("eexp")
        if is_integer and (not include_integers or _is_ascii_alnum(line[end : end + 1])):
            continue
        found.append(number)
    return found


def _matches(mantissa: Decimal, decimals: int, target: Decimal) -> str:
    """原稿の仮数と、同じ桁にそろえた一覧の値を比べる（exact / rounded / sign / missing）。"""
    if target == mantissa:
        return "exact"
    step = Decimal(1).scaleb(-decimals)
    try:
        bounds = {target.quantize(step, rounding=ROUND_FLOOR), target.quantize(step, rounding=ROUND_CEILING)}
    except InvalidOperation:
        return "missing"
    if mantissa in bounds:
        return "rounded"
    if abs(target) == abs(mantissa) or abs(mantissa) in {abs(b) for b in bounds}:
        return "sign"
    return "missing"


def _compare(number: Number, fact: Number) -> str:
    status = _matches(number.mantissa, number.decimals, fact.value.scaleb(-number.exponent))
    if status != "missing" or number.exponent == fact.exponent:
        return status
    # 値は合わないが仮数は合う: 指数の書き方の違い（「6.36、2.08 ×10⁻⁵」）か、指数の取り違え
    by_mantissa = _matches(number.mantissa, number.decimals, fact.mantissa)
    return "exponent" if by_mantissa in ("exact", "rounded") else "missing"


def classify(number: Number, facts: list[Number]) -> Finding:
    """一覧のどの数と、どの強さで一致するか。最も強い一致を返す。"""
    best = Finding(number=number, status="missing", source=None)
    for fact in facts:
        status = _compare(number, fact)
        if _RANK[status] < _RANK[best.status]:
            best = Finding(number=number, status=status, source=fact.text)
            if status == "exact":
                break
    return best


def _text_lines(path: Path) -> list[tuple[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    is_tex = path.suffix.lower() == ".tex"
    out = []
    for i, line in enumerate(lines, start=1):
        if is_tex:
            line = _TEX_REF.sub(" ", _TEX_COMMENT.sub("", line))
            line = _TEX_KEYVAL_OPTION.sub(" ", _TEX_LAYOUT.sub(" ", line))
        out.append((f"L{i}", line))
    return out


def _xml_paragraphs(xml: str, paragraph: re.Pattern[str], run: re.Pattern[str]) -> list[str]:
    texts = []
    for m in paragraph.finditer(xml):
        inner = m.group(1) or ""
        texts.append(html.unescape("".join(run.findall(inner))))
    return texts


def _zip_lines(path: Path) -> list[tuple[str, str]]:
    with zipfile.ZipFile(path) as z:
        if path.suffix.lower() == ".docx":
            xml = z.read("word/document.xml").decode("utf-8")
            paras = _xml_paragraphs(xml, _W_PARAGRAPH, _W_TEXT)
            return [(f"段落 {i}", p) for i, p in enumerate(paras, start=1)]
        slides = sorted(
            (int(m.group(1)), name) for name in z.namelist() if (m := _SLIDE_NAME.search(name))
        )
        out = []
        for num, name in slides:
            xml = z.read(name).decode("utf-8")
            out.extend((f"スライド {num}", p) for p in _xml_paragraphs(xml, _A_PARAGRAPH, _A_TEXT))
        return out


def read_numbers(path: Path, include_integers: bool = False) -> list[Number]:
    """ファイルから数を抜き出す。場所は行（L3）・段落（段落 2）・スライド（スライド 4）。"""
    suffix = path.suffix.lower()
    if suffix in TEXT_SUFFIXES:
        lines = _text_lines(path)
    elif suffix in ZIP_SUFFIXES:
        lines = _zip_lines(path)
    else:
        supported = " ".join(sorted(TEXT_SUFFIXES | ZIP_SUFFIXES))
        raise ValueError(f"対応していない形式です: {suffix or '(拡張子なし)'}（対応: {supported}）")
    return [n for loc, line in lines for n in extract_numbers(line, loc, include_integers)]


def _report(draft: Path, facts_paths: list[Path], findings: list[Finding], n_facts: int) -> str:
    groups = {key: [f for f in findings if f.status == key] for key in _RANK}
    names = "・".join(p.name for p in facts_paths)
    out = [f"数値の照合: {draft.name} ↔ {names}（原稿の数 {len(findings)} 個、一覧の数 {n_facts} 個）"]
    labels = (("missing", "一覧に無い数"), ("exponent", "指数だけ違う"), ("sign", "符号が違う"), ("rounded", "丸めて一致"))
    for key, label in labels:
        out.append(f"{label}: {len(groups[key])}")
        for f in groups[key]:
            tail = f"  ← {f.source}" if f.source and key != "missing" else ""
            out.append(f"  {f.number.location}  {f.number.text}{tail}")
    out.append(f"そのまま一致: {len(groups['exact'])}")
    if groups["missing"] or groups["exponent"] or groups["sign"]:
        out.append(
            "→ 一覧に無い数は一次記録で引き直し、出どころつきで事実の一覧に足してから使う。"
            "指数・符号の違いは一覧の書き方か原稿の誤りかを確かめる。丸めた数は元の桁で確かめる。"
        )
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="原稿・スライドの数を、事実の一覧と照合する")
    parser.add_argument("draft", type=Path, help="原稿・スライド（.md .tex .txt .docx .pptx など）")
    parser.add_argument(
        "--facts", type=Path, required=True, action="append", help="事実の一覧（出どころつき。書式は自由。複数可）"
    )
    parser.add_argument("--integers", action="store_true", help="整数も照合する（既定は小数と指数表記だけ）")
    args = parser.parse_args(argv)
    for path in (args.draft, *args.facts):
        if not path.is_file():
            print(f"見つかりません: {path}", file=sys.stderr)
            return 2
    try:
        facts = [n for path in args.facts for n in read_numbers(path, include_integers=True)]
        numbers = read_numbers(args.draft, include_integers=args.integers)
    except (ValueError, KeyError, zipfile.BadZipFile, UnicodeDecodeError) as exc:
        print(f"読めません: {exc}", file=sys.stderr)
        return 2
    if not facts:
        print(f"事実の一覧に数が 1 つもありません: {', '.join(map(str, args.facts))}", file=sys.stderr)
        return 2
    findings = [classify(n, facts) for n in numbers]
    print(_report(args.draft, args.facts, findings, len(facts)))
    return 1 if any(f.status in ("missing", "exponent", "sign") for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
