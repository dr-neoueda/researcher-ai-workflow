#!/usr/bin/env python3
"""原稿・スライドの数が、事実の一覧（出どころつき）から来ているかを照合する（raw-write / raw-slides）。

記憶で書いた数は、桁も意味もずれる。書き終えたら原稿の数を機械で抜き出し、事実の一覧に在るかを確かめる。

照合の結果:
- そのまま一致: 一覧に同じ値がある（0.50 と 0.5 のように末尾の 0 だけ違うものも含む）
- 丸めて一致: 一覧の値を、原稿の桁で四捨五入すると一致する
- 不等号つきの丸め: 「≤ 0.64」「0.64 以下」は一覧の値を切り上げ、「≥ 0.63」「0.63 以上」は切り捨てると一致する
- 指数が読めない（要確認）: ×10 の何乗かが桁外れで読めない
- 指数だけ違う（要確認）: 仮数は合うが ×10 の何乗かが違う（一覧の書き方の違いか、指数の取り違え）
- 丸め方が合わない（要確認）: 四捨五入では合わない（0.123 に対する 0.2、上限の向きが逆の「≤ 0.63」など）
- 符号が違う（要確認）: 絶対値だけが一致する
- 一覧に無い数（要確認）: どれとも合わない

既定では小数と指数表記（1.2×10⁻³、1.2e-3、1.2\\times10^{-3}、10⁻³）だけを照合する。整数は年・図番号と混ざりやすい
ので ``--integers`` を付けたときだけ照合する。事実の一覧は書式を問わない（表でも箇条書きでも、書いてある数を拾う）。
読まないもの: URL・DOI・日付・文献番号 [12]・版番号（2.0.1、Python 3.12）・図や表や行の番号（Fig. 3、Fig. S1.2、表 2、
line 42、12 行目）・識別子（B3LYP、def2-SVP）・単位の指数（cm-1、s⁻¹）・上付きの番号、LaTeX の引用・参照・コメント・
図の幅や色や行間などの組版の指定。読む範囲: .docx は本文・数式・脚注・文末脚注（ヘッダー・フッター・コメントは読まない）、
.pptx はスライド・数式・発表者ノート（グラフの中のデータは読まない）。小数点のカンマ（0,52）と空白の桁区切り（1 234.5）は
読めないので、小数点はピリオドで、桁区切りはカンマか細い空白で書く。

対応する形式: .md .markdown .txt .tex .csv .tsv .docx .pptx（テキストは UTF-8。BOM つきも可）

実行: ``python check_numbers.py <原稿> --facts <事実の一覧> [--facts <別の一覧> ...] [--integers]``
終了コード: 0 = 全部たどれた、1 = 要確認の数がある、2 = 入力の誤り（原稿から数が 1 つも取れないときも）
"""
from __future__ import annotations

import argparse
import html
import re
import sys
import unicodedata
import zipfile
from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Literal

Status = Literal["exact", "rounded", "bound", "exp_unread", "exponent", "round_mismatch", "sign", "missing"]
Bound = Literal["upper", "lower"]

TEXT_SUFFIXES = frozenset({".md", ".markdown", ".txt", ".tex"})
TABLE_SUFFIXES = frozenset({".csv", ".tsv"})  # カンマはセルの区切りなので、桁区切りとして読まない
ZIP_SUFFIXES = frozenset({".docx", ".pptx"})
MAX_EXPONENT = 999  # これを超える指数は書き損じとして「指数が読めない」に入れる
LOOKBEHIND = 40  # ラベル・不等号を探す、数の前の文字数（行頭から探すと長い行で 2 乗の時間になる）
SIGN_CHARS = "-+−–‐‑‒―ー"
NEGATIVE_SIGNS = frozenset("-−–‐‑‒―ー")  # 各種のハイフン・マイナス記号・ダッシュ・長音（「ー0.5」の打ち間違い）
RANGE_DASHES = frozenset("–—―")  # 「−0.5–−0.2」の右端は負。LaTeX の「0.947--0.987」（-- は範囲）は正
RANGE_LEFT = frozenset(")]%")  # 「1.5-2.5」「(a)-0.3」のダッシュは範囲・引き算で、符号ではない
REJECT_PREV = frozenset("_\\^")  # 識別子・上付き・下付きの一部（run_0.5・s^-1・x_1）

RANK: dict[Status, int] = {
    "exact": 0, "rounded": 1, "bound": 2, "exp_unread": 3, "exponent": 4, "round_mismatch": 5, "sign": 6,
    "missing": 7,
}
FAILING: frozenset[Status] = frozenset({"exp_unread", "exponent", "round_mismatch", "sign", "missing"})
LABELS: tuple[tuple[Status, str], ...] = (
    ("missing", "一覧に無い数"),
    ("exp_unread", "指数が読めない"),
    ("exponent", "指数だけ違う"),
    ("round_mismatch", "丸め方が合わない"),
    ("sign", "符号が違う"),
    ("bound", "不等号つきの丸め"),
    ("rounded", "丸めて一致"),
)

_SUPERSCRIPT = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺", "0123456789-+")
_SUPERSCRIPT_RUN = re.compile(r"[⁻⁺]?[⁰¹²³⁴⁵⁶⁷⁸⁹]+")
_HTML_SUP = re.compile(r"<sup>\s*(.*?)\s*</sup>", re.I)
_TEX_SUP = re.compile(r"\\textsuperscript\{([^}]*)\}")
_THIN_THOUSANDS = re.compile(r"(?<=\d)[\u00a0\u2009\u202f](?=\d{3}(?!\d))")
_NOISE = (
    re.compile(r"https?://[\x21-\x7e]+"),  # URL（ASCII の範囲で止める。日本語の文を飲み込まない）
    re.compile(r"\b10\.\d{4,9}/[\x21-\x7e]+"),  # DOI
    re.compile(r"\]\([^)]*\)"),  # Markdown のリンク先
    re.compile(r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b"),  # 日付 2026-10-27
    re.compile(r"\d{4}年\d{1,2}月(?:\d{1,2}日)?"),  # 日付 2026年11月10日
    re.compile(r"\[\d+(?:\s*[,–-]\s*\d+)*\]"),  # 文献番号 [12] [3,4] [5–7]
)
_LIST_MARKER = re.compile(r"^\s*(?:>+\s*)*(?:\d+[.)]\s+)?")  # 引用の > と番号付き箇条書きの番号
_LABEL_BEFORE = re.compile(
    r"(?:\b(?:Fig(?:ure)?s?|Tables?|Schemes?|Sections?|Sec|Eqs?|Equations?|Chapters?|Python|[Vv]ersion|[Vv]er|v|Rev"
    r"|lines?|pages?|pp|slides?|refs?|Nos?)\.?|\bp\.|#"
    r"|(?<![A-Za-z0-9\u3040-\u30ff\u3400-\u9fff])(?:図|表|式|章|節|頁|ページ|スライド|文献))"
    r"\s*[(\[]?\s*S?\s*$"
)
_LABEL_AFTER = re.compile(r"\s*(?:行目|頁|ページ|枚目)")
_UPPER_BEFORE = re.compile(
    r"(?:[≤≦]|<=?|\\leq?|\\lesssim|\bat most|\bup to|\bless than|\bbelow|\bunder|最大)\s*\$?\s*$", re.I
)
_LOWER_BEFORE = re.compile(
    r"(?:[≥≧]|(?<![-=A-Za-z/\"'])>=?|\\geq?|\\gtrsim|\bat least|\bmore than|\bgreater than|\babove|\bover"
    r"|\bexceed(?:s|ing)?|最小)\s*\$?\s*$",
    re.I,
)
_UNIT_GAP = r"\s*(?:[^\d\s、。,;()]{1,8}\s*)?"
_UPPER_AFTER = re.compile(_UNIT_GAP + r"(?:以下|未満)")
_LOWER_AFTER = re.compile(_UNIT_GAP + r"(?:以上|を超え|を上回)")
_SIGN = r"[-+−–‐‑]"
_TIMES = r"(?:[×✕·*xX]|\\times|\\cdot)"
_TIMES_NO_LETTER = r"(?:[×✕·*]|\\times|\\cdot)"  # ^ の無い「×10-3」は、文字の x では読まない（寸法の 0.5 x 10-20 mm）
_EXPONENT = (
    rf"(?:\s?[eE](?P<eexp>{_SIGN}?\d+)"
    rf"|\s*{_TIMES}\s*10\s*\^\s*\{{?\s*(?P<texp>{_SIGN}?\d+)\s*\}}?"
    rf"|\s*{_TIMES_NO_LETTER}\s*10\s*(?P<nexp>{_SIGN}\s*\d+))?"
)
_NUM_GROUPED = re.compile(
    rf"(?P<sign>[{SIGN_CHARS}])?(?P<mant>\d{{1,3}}(?:,\d{{3}})+(?:\.\d+)?|\d+(?:\.\d+)?|(?<![.\d])\.\d+)" + _EXPONENT
)
_NUM_PLAIN = re.compile(rf"(?P<sign>[{SIGN_CHARS}])?(?P<mant>\d+(?:\.\d+)?|(?<![.\d])\.\d+)" + _EXPONENT)
_BARE_POWER = re.compile(rf"\s*\^\s*\{{?\s*({_SIGN}?\d+)\s*\}}?")
_DOTTED = re.compile(r"\.\d")
_DECIMAL_COMMA = re.compile(r"(?<![\d,.])\d+,\d{1,2}(?![\d,])")

_TEX_COMMENT = re.compile(r"(?<!\\)%.*$")
_TEX_REF = re.compile(
    r"\\(?:cite\w*|ref|eqref|autoref|cref|Cref|label|includegraphics|url|href|bibliography\w*)\*?"
    r"(?:\[[^\]]*\])*\{[^}]*\}"
)
_TEX_KEYVAL_OPTION = re.compile(r"\[[^\]]*=[^\]]*\]")  # [width=0.5\linewidth] [table-format=-2.2]
_TEX_BEGIN = re.compile(r"\\begin\{[^}]*\}(?:\[[^\]]*\])*(?:\{[^}]*\})*")
_TEX_LINEBREAK_SPACE = re.compile(r"\\\\\[[^\]]*\]")  # \\[0.5em]
_TEX_STRETCH = re.compile(r"\\renewcommand\*?\{\\(?:arraystretch|baselinestretch)\}\{[^}]*\}")
_TEX_PRIMITIVE_SKIP = re.compile(r"\\(?:hskip|vskip|mskip|kern)\s*[-+]?\d*\.?\d+\s*[a-z]{2}")
# 組版の命令と、捨てる {…} の数（中身の {…} は残す: \scalebox{0.8}{本文} の本文は読む）
_TEX_LAYOUT_ARGS = {
    "hspace": 1, "vspace": 1, "setlength": 2, "addtolength": 2, "rule": 2, "raisebox": 1, "parbox": 1,
    "scalebox": 1, "resizebox": 2, "fontsize": 2, "definecolor": 3, "textcolor": 1, "color": 1, "colorbox": 1,
    "geometry": 1, "usepackage": 1, "documentclass": 1, "linespread": 1, "setstretch": 1,
}
_TEX_LAYOUT = tuple(
    re.compile(rf"\\{name}(?![A-Za-z])\*?(?:\[[^\]]*\])*" + r"(?:\{[^}]*\})" * n)
    for name, n in _TEX_LAYOUT_ARGS.items()
)
_TEX_LENGTH_MACRO = re.compile(r"\\[A-Za-z]*(?:width|height|skip|size|fig|length)\b")

_W_PARAGRAPH = re.compile(r"<w:p\b[^>]*?(?:/>|>(.*?)</w:p>)", re.S)
_W_RUN = re.compile(r"<(w|m):r\b[^>]*>(.*?)</\1:r>", re.S)  # 文字の run と数式（OMML）の run
_W_TEXT = re.compile(r"<(?:w|m):t\b[^>]*>(.*?)</(?:w|m):t>", re.S)
_W_NOTE_SEPARATOR = re.compile(
    r"<w:(?:footnote|endnote)\b[^>]*w:type=\"(?:separator|continuationSeparator|continuationNotice)\".*?"
    r"</w:(?:footnote|endnote)>",
    re.S,
)
_A_PARAGRAPH = re.compile(r"<a:p\b[^>]*?(?:/>|>(.*?)</a:p>)", re.S)
_A_RUN = re.compile(r"<(a|m):r\b[^>]*>(.*?)</\1:r>", re.S)
_A_TEXT = re.compile(r"<(?:a|m):t\b[^>]*>(.*?)</(?:a|m):t>", re.S)
_A_BASELINE = re.compile(r"<a:rPr\b[^>]*\bbaseline=\"(-?\d+)\"")
_MC_FALLBACK = re.compile(r"<mc:Fallback\b.*?</mc:Fallback>", re.S)  # 数式の代わりの絵・文字（二重に読まない）
_OMML_MARKERS = (("<m:sup>", "<m:r><m:t>^</m:t></m:r>"), ("<m:sub>", "<m:r><m:t>_</m:t></m:r>"))
_SLIDE_NAME = re.compile(r"^ppt/slides/slide(\d+)\.xml$")
_REL = re.compile(r"<Relationship\b([^>]*)>")
_REL_ID = re.compile(r"\bId=\"([^\"]+)\"")
_REL_TARGET = re.compile(r"\bTarget=\"([^\"]+)\"")
_SLD_ID = re.compile(r"<p:sldId\b[^>]*?\br:id=\"([^\"]+)\"")
_NOTES_TARGET = re.compile(r"notesSlides/(notesSlide\d+\.xml)")


@dataclass(frozen=True)
class Number:
    """書かれた 1 つの数。値は ``mantissa × 10^exponent``。

    ``bound`` は前後の不等号（"upper" = ≤・以下、"lower" = ≥・以上）。``unreadable`` は指数が桁外れで読めない数。
    """

    text: str
    mantissa: Decimal
    exponent: int
    decimals: int
    location: str
    bound: Bound | None = None
    unreadable: bool = False

    @property
    def value(self) -> Decimal:
        return self.mantissa.scaleb(self.exponent)

    @property
    def is_plain_integer(self) -> bool:
        return self.decimals == 0 and self.exponent == 0


@dataclass(frozen=True)
class Finding:
    """原稿の 1 つの数の照合結果。``source`` は一致した一覧の数（無ければ None）。"""

    number: Number
    status: Status
    source: str | None


def normalize(text: str) -> str:
    """上付き（⁻³・<sup>・\\textsuperscript）を ^ に直し、細い空白の桁区切りを詰め、NFKC で全角を半角にする。"""
    text = _TEX_SUP.sub(r"^{\1}", _HTML_SUP.sub(r"^{\1}", text))
    text = _SUPERSCRIPT_RUN.sub(lambda m: "^" + m.group(0).translate(_SUPERSCRIPT), text)
    text = _THIN_THOUSANDS.sub("", text)
    text = text.replace("{-}", "-").replace("{−}", "−")
    return unicodedata.normalize("NFKC", text)


def _strip_noise(line: str) -> str:
    for pattern in _NOISE:
        line = pattern.sub(" ", line)
    return line


def _char_before(line: str, index: int) -> str:
    return line[index - 1] if index > 0 else ""


def _is_ascii_letter(ch: str) -> bool:
    return ch.isascii() and ch.isalpha()


def _is_katakana(ch: str) -> bool:
    return "\u30a0" <= ch <= "\u30ff"


def _unsigned_ok(prev: str, before_prev: str, mant: str) -> bool:
    """符号の付かない数を読むか。"""
    if prev == "." and before_prev.isdigit():
        return False  # 2.0.1 の .1
    if prev.isascii() and prev.isdigit():
        return False
    if mant.startswith(".") and prev.isascii() and prev.isalnum():
        return False  # Rev. C.01
    return not (_is_ascii_letter(prev) and "." not in mant)  # B3LYP は捨て、pH7.4・2.5x2.5 は読む


def _sign_of(match: re.Match[str], line: str) -> str | None:
    """この数の符号（'-' か ''）。数として読まないなら None。"""
    sign, mant = match.group("sign"), match.group("mant")
    start = match.start("sign") if sign else match.start("mant")
    prev, before_prev = _char_before(line, start), _char_before(line, start - 1)
    if prev in REJECT_PREV:
        return None
    if prev == "/" and _is_ascii_letter(before_prev):
        return None  # figs/1.25 はパス（3.002/2.078 は値の組）
    if not sign:
        return "" if _unsigned_ok(prev, before_prev, mant) else None
    if prev == "+" or (sign == "ー" and _is_katakana(prev)):
        return ""  # +- は ±、「メーター0.5」の長音は語の一部
    if _is_ascii_letter(prev):
        return "" if "." in mant else None  # E-0.5 は 0.5、cm-1・X-D は捨てる
    if prev.isdigit() or prev in RANGE_LEFT:
        return ""  # 範囲・引き算のダッシュ
    if prev in NEGATIVE_SIGNS or prev == "—":
        return "-" if (sign == "−" or prev in RANGE_DASHES) else ""
    if sign in RANGE_DASHES and prev.isspace():
        left = line[:start].rstrip()[-1:]
        if left.isdigit() or left in RANGE_LEFT:
            return ""  # 「0.5 –0.8」は範囲
    return "-" if sign in NEGATIVE_SIGNS else ""


def _exponent_text(match: re.Match[str]) -> str | None:
    raw = match.group("eexp") or match.group("texp") or match.group("nexp")
    if raw is None:
        return None
    return re.sub(r"\s+", "", raw).translate(str.maketrans("−–‐‑", "----"))


def _fmt(value: Decimal) -> str:
    return format(value, "f")


def _to_number(match: re.Match[str], sign: str, location: str, bound: Bound | None) -> Number:
    mant = match.group("mant").replace(",", "")
    exp_text = _exponent_text(match)
    exponent = int(exp_text) if exp_text else 0
    decimals = len(mant.split(".")[1]) if "." in mant else 0
    mantissa = Decimal(sign + (mant if not mant.startswith(".") else "0" + mant))
    if abs(exponent) > MAX_EXPONENT:
        return Number(f"{_fmt(mantissa)}×10^{exponent}", mantissa, 0, decimals, location, bound, unreadable=True)
    shown = f"{_fmt(mantissa)}×10^{exponent}" if exp_text else _fmt(mantissa)
    return Number(shown, mantissa, exponent, decimals, location, bound)


def _bare_power(match: re.Match[str], line: str, sign: str, location: str, bound: Bound | None) -> Number | None:
    """「10⁻³」「10^{5}」のように仮数の無い 10 の累乗を 1×10^n として読む。"""
    if match.group("mant") != "10" or _exponent_text(match) is not None:
        return None
    power = _BARE_POWER.match(line, match.end())
    if power is None:
        return None
    exponent = int(power.group(1).translate(str.maketrans("−–‐‑", "----")))
    mantissa = Decimal(sign + "1")
    if abs(exponent) > MAX_EXPONENT:
        return Number(f"10^{exponent}", mantissa, 0, 0, location, bound, unreadable=True)
    return Number(f"10^{exponent}", mantissa, exponent, 0, location, bound)


def _is_label_number(line: str, start: int, end: int) -> bool:
    lo = max(0, start - LOOKBEHIND)
    return bool(_LABEL_BEFORE.search(line, lo, start) or _LABEL_AFTER.match(line, end))


def _bound_of(line: str, start: int, end: int) -> Bound | None:
    lo = max(0, start - LOOKBEHIND)
    if _UPPER_BEFORE.search(line, lo, start) or _UPPER_AFTER.match(line, end):
        return "upper"
    if _LOWER_BEFORE.search(line, lo, start) or _LOWER_AFTER.match(line, end):
        return "lower"
    return None


def _read_one(match: re.Match[str], line: str, location: str, include_integers: bool) -> Number | None:
    start, end = match.start(), match.end()
    if _DOTTED.match(line, end) or _TEX_LENGTH_MACRO.match(line, end) or _is_label_number(line, start, end):
        return None
    sign = _sign_of(match, line)
    if sign is None:
        return None
    bound = _bound_of(line, start, end)
    power = _bare_power(match, line, sign, location, bound)
    if power is not None:
        return power
    number = _to_number(match, sign, location, bound)
    if number.is_plain_integer and not number.unreadable and _exponent_text(match) is None:
        if not include_integers or _is_ascii_letter(line[end : end + 1]):
            return None
    return number


def extract_numbers(
    text: str, location: str, include_integers: bool = False, thousands: bool = True
) -> list[Number]:
    """1 行（または 1 段落）から数を抜き出す。``thousands=False`` ならカンマを桁区切りとして読まない（CSV）。"""
    line = _strip_noise(normalize(text))
    pattern = _NUM_GROUPED if thousands else _NUM_PLAIN
    found = (_read_one(m, line, location, include_integers) for m in pattern.finditer(line))
    return [n for n in found if n is not None]


def _match_at(mantissa: Decimal, decimals: int, target: Decimal, bound: Bound | None) -> Status:
    """原稿の仮数と、同じ桁にそろえた一覧の値を比べる。"""
    if target == mantissa:
        return "exact"
    step = Decimal(1).scaleb(-decimals)
    half_up = target.quantize(step, rounding=ROUND_HALF_UP)
    floor = target.quantize(step, rounding=ROUND_FLOOR)
    ceil = target.quantize(step, rounding=ROUND_CEILING)
    if bound == "upper" and mantissa == ceil or bound == "lower" and mantissa == floor:
        return "bound"
    if bound is None and mantissa == half_up:
        return "rounded"
    if mantissa in (floor, ceil, half_up):
        return "round_mismatch"
    if abs(mantissa) in {abs(target), abs(half_up), abs(floor), abs(ceil)}:
        return "sign"
    return "missing"


def _compare(number: Number, fact: Number) -> Status:
    if fact.is_plain_integer and number.decimals > 0 and number.exponent == 0:
        return "missing"  # 一覧の整数（2 h）は原稿の小数（2.0 h）の裏付けにしない
    try:
        status = _match_at(number.mantissa, number.decimals, fact.value.scaleb(-number.exponent), number.bound)
    except InvalidOperation:
        status = "missing"
    if status != "missing" or number.exponent == fact.exponent:
        return status
    # 値は合わないが仮数は合う: 指数の書き方の違い（「6.36、2.08 ×10⁻⁵」）か、指数の取り違え
    try:
        by_mantissa = _match_at(number.mantissa, number.decimals, fact.mantissa, number.bound)
    except InvalidOperation:
        return "missing"
    return "exponent" if by_mantissa in ("exact", "rounded", "bound") else "missing"


def classify(number: Number, facts: list[Number]) -> Finding:
    """一覧のどの数と、どの強さで一致するか。最も強い一致を返す。"""
    if number.unreadable:
        return Finding(number=number, status="exp_unread", source=None)
    best = Finding(number=number, status="missing", source=None)
    for fact in facts:
        status = _compare(number, fact)
        if RANK[status] < RANK[best.status]:
            best = Finding(number=number, status=status, source=fact.text)
            if status == "exact":
                break
    return best


def _strip_tex(line: str) -> str:
    line = _TEX_REF.sub(" ", _TEX_COMMENT.sub("", line))
    patterns = (_TEX_BEGIN, _TEX_LINEBREAK_SPACE, _TEX_STRETCH, _TEX_PRIMITIVE_SKIP, *_TEX_LAYOUT, _TEX_KEYVAL_OPTION)
    for pattern in patterns:
        line = pattern.sub(" ", line)
    return line


def _text_lines(path: Path) -> list[tuple[str, str]]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    suffix = path.suffix.lower()
    out = []
    for i, line in enumerate(lines, start=1):
        if suffix == ".tex":
            line = _strip_tex(line)
        elif suffix not in TABLE_SUFFIXES:
            line = _LIST_MARKER.sub(" ", line, count=1)
        out.append((f"L{i}", line))
    return out


def _run_text(run_xml: str, text_re: re.Pattern[str], is_superscript: bool) -> str:
    text = html.unescape("".join(text_re.findall(run_xml)))
    return "^" + text if is_superscript and text else text  # 上付きの run は指数として読む（10 + ^-3）


def _with_math_markers(xml: str) -> str:
    """数式（OMML）の上付き・下付きに ^ と _ の印を入れ、代わりの絵・文字（Fallback）を外す。"""
    xml = _MC_FALLBACK.sub("", xml)
    for tag, marker in _OMML_MARKERS:
        xml = xml.replace(tag, marker)
    return xml


def _docx_paragraphs(xml: str) -> list[str]:
    paras = []
    for m in _W_PARAGRAPH.finditer(_with_math_markers(_W_NOTE_SEPARATOR.sub("", xml))):
        runs = [body for _, body in _W_RUN.findall(m.group(1) or "")]
        paras.append("".join(_run_text(r, _W_TEXT, 'w:val="superscript"' in r) for r in runs))
    return paras


def _pptx_paragraphs(xml: str) -> list[str]:
    paras = []
    for m in _A_PARAGRAPH.finditer(_with_math_markers(xml)):
        texts = []
        for _, run in _A_RUN.findall(m.group(1) or ""):
            base = _A_BASELINE.search(run)
            texts.append(_run_text(run, _A_TEXT, bool(base and int(base.group(1)) > 0)))
        paras.append("".join(texts))
    return paras


def _docx_lines(z: zipfile.ZipFile) -> list[tuple[str, str]]:
    body = _docx_paragraphs(z.read("word/document.xml").decode("utf-8"))
    out = [(f"段落 {i}", p) for i, p in enumerate(body, 1)]
    for part, label in (("word/footnotes.xml", "脚注"), ("word/endnotes.xml", "文末脚注")):
        if part in z.namelist():
            paras = [p for p in _docx_paragraphs(z.read(part).decode("utf-8")) if p.strip()]
            out.extend((f"{label} {i}", p) for i, p in enumerate(paras, 1))
    return out


def _relationships(xml: str) -> dict[str, str]:
    """関連づけ（Id → Target）。属性の順は問わない。"""
    rels = {}
    for attrs in _REL.findall(xml):
        rid, target = _REL_ID.search(attrs), _REL_TARGET.search(attrs)
        if rid and target:
            rels[rid.group(1)] = target.group(1)
    return rels


def _slide_parts(z: zipfile.ZipFile) -> list[str]:
    """スライドの部品名を、PowerPoint で表示される順に返す（無ければファイル番号の順）。"""
    names = set(z.namelist())
    if {"ppt/presentation.xml", "ppt/_rels/presentation.xml.rels"} <= names:
        rels = _relationships(z.read("ppt/_rels/presentation.xml.rels").decode("utf-8"))
        order = _SLD_ID.findall(z.read("ppt/presentation.xml").decode("utf-8"))
        parts = ["ppt/" + rels[rid].lstrip("/").removeprefix("ppt/") for rid in order if rid in rels]
        if parts and all(p in names for p in parts):
            return parts
    numbered = sorted((int(m.group(1)), n) for n in names if (m := _SLIDE_NAME.match(n)))
    return [n for _, n in numbered]


def _notes_part(z: zipfile.ZipFile, slide_part: str) -> str | None:
    """スライドに付いた発表者ノートの部品名（関連づけをたどる。番号はスライドと一致しないことがある）。"""
    rels = slide_part.replace("ppt/slides/", "ppt/slides/_rels/") + ".rels"
    if rels not in z.namelist():
        return None
    m = _NOTES_TARGET.search(z.read(rels).decode("utf-8"))
    if not m:
        return None
    part = f"ppt/notesSlides/{m.group(1)}"
    return part if part in z.namelist() else None


def _pptx_lines(z: zipfile.ZipFile) -> list[tuple[str, str]]:
    out = []
    for num, part in enumerate(_slide_parts(z), 1):
        out.extend((f"スライド {num}", p) for p in _pptx_paragraphs(z.read(part).decode("utf-8")))
        notes = _notes_part(z, part)
        if notes:
            out.extend((f"ノート {num}", p) for p in _pptx_paragraphs(z.read(notes).decode("utf-8")))
    return out


def read_lines(path: Path) -> list[tuple[str, str]]:
    """ファイルを（場所, 文）の並びにする。場所は行（L3）・段落（段落 2）・脚注・スライド・ノート。"""
    suffix = path.suffix.lower()
    if suffix in TEXT_SUFFIXES | TABLE_SUFFIXES:
        return _text_lines(path)
    if suffix in ZIP_SUFFIXES:
        with zipfile.ZipFile(path) as z:
            return _docx_lines(z) if suffix == ".docx" else _pptx_lines(z)
    supported = " ".join(sorted(TEXT_SUFFIXES | TABLE_SUFFIXES | ZIP_SUFFIXES))
    raise ValueError(f"対応していない形式です: {suffix or '(拡張子なし)'}（対応: {supported}）")


def read_numbers(path: Path, include_integers: bool = False) -> list[Number]:
    """ファイルから数を抜き出す。"""
    thousands = path.suffix.lower() not in TABLE_SUFFIXES
    return [n for loc, line in read_lines(path) for n in extract_numbers(line, loc, include_integers, thousands)]


def decimal_comma_spots(path: Path) -> list[str]:
    """小数点をカンマで書いたかもしれない箇所（例「L3 0,52」）。CSV は対象外。"""
    if path.suffix.lower() in TABLE_SUFFIXES:
        return []
    spots = []
    for loc, line in read_lines(path):
        spots.extend(f"{loc} {m.group(0)}" for m in _DECIMAL_COMMA.finditer(_strip_noise(normalize(line))))
    return spots


def _report(draft: Path, facts_paths: list[Path], findings: list[Finding], n_facts: int, commas: list[str]) -> str:
    groups = {key: [f for f in findings if f.status == key] for key in RANK}
    names = "・".join(p.name for p in facts_paths)
    out = [f"数値の照合: {draft.name} と {names}（原稿の数 {len(findings)} 個、一覧の数 {n_facts} 個）"]
    for key, label in LABELS:
        out.append(f"{label}: {len(groups[key])}")
        for f in groups[key]:
            tail = f"  ← {f.source}" if f.source else ""
            out.append(f"  {f.number.location}  {f.number.text}{tail}")
    out.append(f"そのまま一致: {len(groups['exact'])}")
    if commas:
        out.append(f"（参考）小数点がカンマかもしれない箇所 {len(commas)} 個: {'、'.join(commas[:5])}（照合していない）")
    if any(groups[key] for key in FAILING):
        out.append(
            "→ 一覧に無い数は一次記録で引き直し、出どころつきで事実の一覧に足してから使う。"
            "指数・符号・丸め方の違いは、一覧の書き方の違いか原稿の誤りかを確かめる。"
        )
    return "\n".join(out)


def _quiet_console() -> None:
    """日本語の Windows のコンソール（cp932）で書けない文字があっても落ちないようにする。"""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="replace")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="原稿・スライドの数を、事実の一覧と照合する")
    parser.add_argument("draft", type=Path, help="原稿・スライド（.md .tex .txt .docx .pptx など）")
    parser.add_argument(
        "--facts", type=Path, required=True, action="append", help="事実の一覧（出どころつき。書式は自由。複数可）"
    )
    parser.add_argument("--integers", action="store_true", help="整数も照合する（既定は小数と指数表記だけ）")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _quiet_console()
    args = _parse_args(argv)
    for path in (args.draft, *args.facts):
        if not path.is_file():
            print(f"見つかりません: {path}", file=sys.stderr)
            return 2
    try:
        facts = [n for path in args.facts for n in read_numbers(path, include_integers=True)]
        numbers = read_numbers(args.draft, include_integers=args.integers)
        commas = decimal_comma_spots(args.draft)
    except UnicodeDecodeError as exc:
        print(f"読めません（UTF-8 で保存し直してください）: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, RuntimeError, NotImplementedError, zipfile.BadZipFile) as exc:
        print(f"読めません: {exc}", file=sys.stderr)
        return 2
    if not facts:
        print(f"事実の一覧に数が 1 つもありません: {', '.join(map(str, args.facts))}", file=sys.stderr)
        return 2
    if not numbers:
        hint = "" if args.integers else "整数も確かめるなら --integers を付ける。"
        print(f"原稿から数が 1 つも取れませんでした（照合していません）: {args.draft}。{hint}", file=sys.stderr)
        return 2
    findings = [classify(n, facts) for n in numbers]
    print(_report(args.draft, args.facts, findings, len(facts), commas))
    return 1 if any(f.status in FAILING for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
