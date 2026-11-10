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
一覧の側に不等号があるとき（「< 0.05」）は、原稿も同じ向きの不等号で書いた数だけを裏付ける。

既定では小数と指数表記（1.2×10⁻³、1.2e-3、1.2\\times10^{-3}、10⁻³、5 x 10-3 M）だけを照合する。整数は年・図番号と
混ざりやすいので ``--integers`` を付けたときだけ照合する。事実の一覧は書式を問わない（表でも箇条書きでも数を拾う）。
読まないもの: URL・DOI・日付・文献番号 [12]・版番号（2.0.1、Python 3.12）・図や表や行の番号（Fig. 3、Fig. S1.2、表 2、
line 42、12 行目）・識別子（B3LYP、def2-SVP、run_0.5）・単位の指数（cm-1、s⁻¹）・上付きの整数、LaTeX の引用・参照・
コメント・図の幅や色や行間などの組版の指定。このうち小数に見えるのに読まなかったものは「読まなかった小数」として挙げる
（黙って捨てない）。読む範囲: .docx は本文・表・テキストボックス・数式・脚注・文末脚注（ヘッダー・フッター・コメントは
読まない）、.pptx はスライド・数式・発表者ノート（グラフの中のデータは読まない）。小数点のカンマ（0,52）と普通の空白の
桁区切り（1 234.5）は読めないので、小数点はピリオドで、桁区切りはカンマか細い空白で書く。

対応する形式: .md .markdown .txt .tex .csv .tsv .docx .pptx（テキストは UTF-8。BOM つきも可）

実行: ``python check_numbers.py <原稿> --facts <事実の一覧> [--facts <別の一覧> ...] [--integers]``
終了コード: 0 = 全部たどれた、1 = 要確認の数がある、2 = 入力の誤り（原稿から数が 1 つも取れないときも）
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
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
_THIN_GROUP = re.compile(r"(\d+(?:\.\d+)?)[\u00a0\u2009\u202f](?=\d{3}(?!\d))")
_URL_CHARS = r"[^\s|,;<>\"'()\[\]\u0080-\U0010ffff]+"  # 日本語・表の区切りの手前で止める
_NOISE = (
    re.compile(r"https?://" + _URL_CHARS),  # URL
    re.compile(r"\b10\.\d{4,9}/" + _URL_CHARS),  # DOI
    re.compile(r"\]\((?:[^)\s]*[/#:][^)\s]*|[^)\s]*\.[A-Za-z]{2,5})\)"),  # Markdown のリンク先（パス・URL）
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
    r"(?:[≤≦]|<=?|\\leq?|\\lesssim|\bat most|\bup to|\bless than|\bbelow|\bunder)\s*\$?\s*$", re.I
)
_LOWER_BEFORE = re.compile(
    r"(?:[≥≧]|(?<![-=A-Za-z/\"'])>=?|\\geq?|\\gtrsim|\bat least|\bmore than|\bgreater than|\babove|\bover"
    r"|\bexceed(?:s|ing)?)\s*\$?\s*$",  # 「最大 0.068」は最大値という値で、不等号ではない
    re.I,
)
_UNIT_GAP = r"\s*(?:[^\d\s、。,;()\u3040-\u309f]{1,8}\s*)?"  # 単位（kcal/mol・%）は挟めるが、助詞（を・の）は挟めない
_UPPER_AFTER = re.compile(_UNIT_GAP + r"(?:以下|未満)")
_LOWER_AFTER = re.compile(_UNIT_GAP + r"(?:以上|を超え|を上回)")
_SIGN = r"[-+−–‐‑]"
_TIMES = r"(?:[×✕·*xX]|\\times|\\cdot)"
_TIMES_NO_LETTER = r"(?:[×✕·*]|\\times|\\cdot)"
_CARET = r"\s*\$?\s*\^\s*[{(]?\s*"  # 10^-3・10^{-3}・10$^{-3}$・10^(-3)
_LENGTH_UNIT = r"(?:mm|cm|µm|μm|um|nm|pm|m|in|px|pt)\b"
_EXPONENT = (
    rf"(?:\s?[eE](?P<eexp>{_SIGN}?\d+)"
    rf"|\s*{_TIMES}\s*10{_CARET}(?P<texp>{_SIGN}?\d+)\s*[}})]?"
    rf"|\s*{_TIMES_NO_LETTER}\s*10\s*(?P<nexp>{_SIGN}\s*\d+)(?!\d)"
    rf"|\s*[xX]\s*10(?P<xexp>[-−–‐‑]\d+)(?!\d)(?!\s*{_LENGTH_UNIT}))?"  # 5 x 10-3 M は指数、0.5 x 10-20 mm は寸法
)
_MANTISSA_GROUPED = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?|(?<![.\d])\.\d+"
_MANTISSA_PLAIN = r"\d+(?:\.\d+)?|(?<![.\d])\.\d+"
_NUM_GROUPED = re.compile(rf"(?P<sign>[{SIGN_CHARS}])?(?P<mant>{_MANTISSA_GROUPED})" + _EXPONENT)
_NUM_PLAIN = re.compile(rf"(?P<sign>[{SIGN_CHARS}])?(?P<mant>{_MANTISSA_PLAIN})" + _EXPONENT)
_BARE_POWER = re.compile(rf"{_CARET}({_SIGN}?\d+)\s*[}})]?")
_DOTTED = re.compile(r"\.\d")
_DECIMAL_COMMA = re.compile(r"(?<![\d,.])\d+,\d{1,2}(?![\d,])")
_MINUS_LIKE = str.maketrans("−–‐‑", "----")

_TEX_COMMENT = re.compile(r"(?<!\\)%.*$")
_TEX_REF = re.compile(
    r"\\(?:cite\w*|ref|eqref|autoref|cref|Cref|label|includegraphics|url|href|bibliography\w*)\*?"
    r"(?:\[[^\]]*\])*\{[^}]*\}"
)
_TEX_KEYVAL = re.compile(r"\[[^\]]*=[^\]]*\]")
# [..=..] を組版の指定とみなすのは、命令（\includegraphics[...]）・環境・列の型（S[...]）・} ] の直後だけ
_TEX_OPTION_OWNER = re.compile(
    r"(?:\\(?!(?:left|right|big|Big|bigg|Bigg)\b)[A-Za-z]+\*?\s*|\\begin\{[^}]*\}\s*|(?<![A-Za-z])[A-Z]|[}\]])$"
)
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

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"
_MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"
_TEXT_TAGS = frozenset({_W + "t", _A + "t", _M + "t"})
_SPACE_TAGS = frozenset({_W + "tab", _W + "br", _W + "cr", _A + "br"})
_SKIP_TAGS = frozenset({_MC + "Fallback", _W + "delText", _W + "instrText"})  # 代わりの絵・削除した文字・フィールドの命令
_NOTE_SEPARATORS = frozenset({"separator", "continuationSeparator", "continuationNotice"})
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


@dataclass(frozen=True)
class Skipped:
    """小数に見えるのに、図表の番号・版番号・識別子などと判断して読まなかったもの。"""

    location: str
    text: str
    reason: str


def _join_thin_groups(m: re.Match[str]) -> str:
    left = m.group(1)
    return left if "." not in left and len(left) <= 3 else left + " "  # 0.52 100 はつながない


def normalize(text: str) -> str:
    """上付き（⁻³・<sup>・\\textsuperscript）を ^ に直し、細い空白の桁区切りを詰め、NFKC で全角を半角にする。"""
    text = _TEX_SUP.sub(r"^{\1}", _HTML_SUP.sub(r"^{\1}", text))
    text = _SUPERSCRIPT_RUN.sub(lambda m: "^" + m.group(0).translate(_SUPERSCRIPT), text)
    text = _THIN_GROUP.sub(_join_thin_groups, text)
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


def _looks_like_path(line: str, slash: int) -> bool:
    """slash の位置の / が、パスの区切りか（data/figs/1.25・./figs/1.25）。mg/0.5 mL は単位なのでパスではない。"""
    token = re.split(r"\s", line[:slash])[-1]
    return "/" in token or token.startswith(".")


def _sign_of(match: re.Match[str], line: str) -> tuple[str | None, str]:
    """この数の符号（'-' か ''）と、読まないときの理由。符号が None なら読まない。"""
    sign, mant = match.group("sign"), match.group("mant")
    start = match.start("sign") if sign else match.start("mant")
    prev, before_prev = _char_before(line, start), _char_before(line, start - 1)
    is_decimal = "." in mant
    if prev == "\\" or (prev == "_" and before_prev.isascii() and before_prev.isalnum()):
        return None, "識別子"  # run_0.5・\cmd
    if prev == "^" and not is_decimal:
        return None, ""  # R^2・s^-1 の上付きの整数
    if prev == "/" and _looks_like_path(line, start - 1):
        return None, "パス"
    if prev == "/" and _is_ascii_letter(before_prev) and not is_decimal:
        return None, ""  # B3LYP/6-31G の 6（mg/0.5 mL の 0.5 は読む）
    if not sign:
        if prev.isascii() and prev.isdigit():
            return None, ""  # 2.0.1 の .1（前の数の続き）
        if mant.startswith(".") and prev.isascii() and prev.isalnum():
            return None, "識別子"  # Rev. C.01
        if _is_ascii_letter(prev) and not is_decimal:
            return None, ""  # B3LYP の 3
        return "", ""  # pH7.4・2.5x2.5 は読む
    return _signed(sign, mant, line, start, prev), ""


def _signed(sign: str, mant: str, line: str, start: int, prev: str) -> str | None:
    if prev == "+" or (sign == "ー" and _is_katakana(prev)):
        return ""  # +- は ±、「メーター0.5」の長音は語の一部
    if _is_ascii_letter(prev):
        if "." not in mant:
            return None  # cm-1・X-D
        return "-" if sign == "−" else ""  # ΔE−0.52 は負、$E-0.5$ は 0.5
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
    raw = match.group("eexp") or match.group("texp") or match.group("nexp") or match.group("xexp")
    if raw is None:
        return None
    return re.sub(r"\s+", "", raw).translate(_MINUS_LIKE)


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
    exponent = int(power.group(1).translate(_MINUS_LIKE))
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


def _skip_reason(match: re.Match[str], line: str) -> str:
    """ラベル・版番号・組版の長さのとき、その理由（どれでもなければ空）。"""
    start, end = match.start(), match.end()
    if _DOTTED.match(line, end):
        return "版番号"
    if _TEX_LENGTH_MACRO.match(line, end):
        return "組版の長さ"
    if _is_label_number(line, start, end):
        return "図表・行の番号"
    return ""


def _read_one(match: re.Match[str], line: str, location: str, include_integers: bool) -> tuple[Number | None, str]:
    """1 つの一致を数にする。読まないなら (None, 理由)。理由が空なら、挙げるまでもない（整数・前の数の続き）。"""
    reason = _skip_reason(match, line)
    if reason:
        return None, reason
    sign, reason = _sign_of(match, line)
    if sign is None:
        return None, reason
    start, end = match.start(), match.end()
    bound = _bound_of(line, start, end)
    power = _bare_power(match, line, sign, location, bound)
    if power is not None:
        return power, ""
    number = _to_number(match, sign, location, bound)
    if number.is_plain_integer and not number.unreadable and _exponent_text(match) is None:
        if not include_integers or _is_ascii_letter(line[end : end + 1]):
            return None, ""
    return number, ""


def extract_numbers(
    text: str,
    location: str,
    include_integers: bool = False,
    thousands: bool = True,
    skipped: list[Skipped] | None = None,
) -> list[Number]:
    """1 行（または 1 段落）から数を抜き出す。``thousands=False`` ならカンマを桁区切りとして読まない（CSV）。

    ``skipped`` を渡すと、小数に見えるのに読まなかったもの（図表の番号・版番号・識別子など）をそこに足す。
    """
    line = _strip_noise(normalize(text))
    pattern = _NUM_GROUPED if thousands else _NUM_PLAIN
    found: list[Number] = []
    for match in pattern.finditer(line):
        number, reason = _read_one(match, line, location, include_integers)
        if number is not None:
            found.append(number)
        elif reason and skipped is not None and ("." in match.group("mant") or _exponent_text(match)):
            skipped.append(Skipped(location, match.group(0).strip(), reason))
    return found


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
    if fact.bound is not None and fact.bound != number.bound:
        return "missing"  # 一覧の「< 0.05」は、原稿の「= 0.05」の裏付けにしない
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


def _strip_tex_options(line: str) -> str:
    def repl(m: re.Match[str]) -> str:
        return " " if _TEX_OPTION_OWNER.search(line, max(0, m.start() - LOOKBEHIND), m.start()) else m.group(0)

    return _TEX_KEYVAL.sub(repl, line)


def _strip_tex(line: str) -> str:
    line = _TEX_REF.sub(" ", _TEX_COMMENT.sub("", line))
    line = _strip_tex_options(line)
    for pattern in (_TEX_BEGIN, _TEX_LINEBREAK_SPACE, _TEX_STRETCH, _TEX_PRIMITIVE_SKIP, *_TEX_LAYOUT):
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


def _is_superscript_run(run: ET.Element) -> bool:
    if run.tag == _W + "r":
        align = run.find(f"{_W}rPr/{_W}vertAlign")
        return align is not None and align.get(_W + "val") == "superscript"
    props = run.find(_A + "rPr")
    try:
        return props is not None and int(props.get("baseline", "0")) > 0
    except ValueError:
        return False


def _collect(element: ET.Element, paragraph_tag: str, out: list[str]) -> None:
    """段落の文字を集める。入れ子の段落（テキストボックス）は別の段落として読むので、ここでは飛ばす。"""
    for child in element:
        tag = child.tag
        if tag == paragraph_tag or tag in _SKIP_TAGS:
            continue
        if tag in _TEXT_TAGS:
            out.append(child.text or "")
        elif tag in _SPACE_TAGS:
            out.append(" ")
        elif tag == _W + "noBreakHyphen":
            out.append("‑")
        elif tag in (_W + "r", _A + "r"):
            inner: list[str] = []
            _collect(child, paragraph_tag, inner)
            text = "".join(inner)
            out.append("^" + text if text and _is_superscript_run(child) else text)  # 上付きの run は指数（10 + ^-3）
        elif tag in (_M + "sup", _M + "sub"):
            out.append("^" if tag == _M + "sup" else "_")
            _collect(child, paragraph_tag, out)
        else:
            _collect(child, paragraph_tag, out)


def _paragraph_texts(root: ET.Element, paragraph_tag: str) -> list[str]:
    texts = []
    for paragraph in root.iter(paragraph_tag):
        out: list[str] = []
        _collect(paragraph, paragraph_tag, out)
        texts.append("".join(out))
    return texts


def _docx_lines(z: zipfile.ZipFile) -> list[tuple[str, str]]:
    body = _paragraph_texts(ET.fromstring(z.read("word/document.xml")), _W + "p")
    out = [(f"段落 {i}", p) for i, p in enumerate(body, 1)]
    for part, note_tag, label in (
        ("word/footnotes.xml", _W + "footnote", "脚注"),
        ("word/endnotes.xml", _W + "endnote", "文末脚注"),
    ):
        if part not in z.namelist():
            continue
        notes = [n for n in ET.fromstring(z.read(part)).iter(note_tag) if n.get(_W + "type") not in _NOTE_SEPARATORS]
        paras = [p for note in notes for p in _paragraph_texts(note, _W + "p") if p.strip()]
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
        out.extend((f"スライド {num}", p) for p in _paragraph_texts(ET.fromstring(z.read(part)), _A + "p"))
        notes = _notes_part(z, part)
        if notes:
            out.extend((f"ノート {num}", p) for p in _paragraph_texts(ET.fromstring(z.read(notes)), _A + "p"))
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


def read_numbers(path: Path, include_integers: bool = False, skipped: list[Skipped] | None = None) -> list[Number]:
    """ファイルから数を抜き出す。``skipped`` を渡すと、読まなかった小数をそこに足す。"""
    thousands = path.suffix.lower() not in TABLE_SUFFIXES
    return [
        n
        for loc, line in read_lines(path)
        for n in extract_numbers(line, loc, include_integers, thousands, skipped)
    ]


def decimal_comma_spots(path: Path) -> list[str]:
    """小数点をカンマで書いたかもしれない箇所（例「L3 0,52」）。CSV は対象外。"""
    if path.suffix.lower() in TABLE_SUFFIXES:
        return []
    spots = []
    for loc, line in read_lines(path):
        spots.extend(f"{loc} {m.group(0)}" for m in _DECIMAL_COMMA.finditer(_strip_noise(normalize(line))))
    return spots


@dataclass(frozen=True)
class Notes:
    """照合の結果に添える参考の情報（照合していないもの）。"""

    commas: list[str]
    skipped: list[Skipped]


def _report(draft: Path, facts_paths: list[Path], findings: list[Finding], n_facts: int, notes: Notes) -> str:
    groups = {key: [f for f in findings if f.status == key] for key in RANK}
    names = "・".join(p.name for p in facts_paths)
    out = [f"数値の照合: {draft.name} と {names}（原稿の数 {len(findings)} 個、一覧の数 {n_facts} 個）"]
    for key, label in LABELS:
        out.append(f"{label}: {len(groups[key])}")
        for f in groups[key]:
            tail = f"  ← {f.source}" if f.source else ""
            out.append(f"  {f.number.location}  {f.number.text}{tail}")
    out.append(f"そのまま一致: {len(groups['exact'])}")
    if notes.skipped:
        out.append(f"（参考）読まなかった小数 {len(notes.skipped)} 個（照合していない。本文の値が混ざっていないか目で確かめる）:")
        out.extend(f"  {s.location}  {s.text}（{s.reason}）" for s in notes.skipped)
    if notes.commas:
        out.append(f"（参考）小数点がカンマかもしれない箇所 {len(notes.commas)} 個: {'、'.join(notes.commas[:5])}（照合していない）")
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
    skipped: list[Skipped] = []
    try:
        facts = [n for path in args.facts for n in read_numbers(path, include_integers=True)]
        numbers = read_numbers(args.draft, include_integers=args.integers, skipped=skipped)
        commas = decimal_comma_spots(args.draft)
    except UnicodeDecodeError as exc:
        print(f"読めません（UTF-8 で保存し直してください）: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, RuntimeError, NotImplementedError, zipfile.BadZipFile, ET.ParseError) as exc:
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
    print(_report(args.draft, args.facts, findings, len(facts), Notes(commas, skipped)))
    return 1 if any(f.status in FAILING for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
