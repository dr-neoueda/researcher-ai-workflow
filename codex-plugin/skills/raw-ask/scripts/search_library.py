#!/usr/bin/env python3
"""登録済みの論文（work/papers/md の要約）から、研究の質問に関係する論文と節を探す（raw-ask）。

raw-register が作った要約 md（frontmatter に title・authors・year・doi、本文は「## 節」）を読み、BM25 で順位を付ける。
「## Metadata」などの節の「- **Authors**: …」の形の箇条書きも書誌として読む。日本語は漢字・カタカナの 2 文字ずつ
（ひらがなで区切る。漢字は 1 文字ずつも索引に入れ、「光」「X線」のような 1 文字の問いでも長い語に当たる）、英語は単語
（ギリシャ文字は残し、アクセントは外し、ハイフンでつながった語はつないだ形も数える）。題名とタグ、要約・キーワードの
節は重く数える。問いは複数渡せる（日本語と英語の言い換えなど）。問いごとに最高点で割ってから合わせる。

点数は「どれから読むか」の目安で、関係があるかは上位の節を実際に読んで決める。何も当たらないときは、言い換えでも
探してから「登録済みの N 本には見当たらない」と言う（N はこの道具が数える。読めないファイルは別に数えて出す）。

実行: ``python search_library.py "問い" ["言い換え" ...] [--library work/papers/md] [--top 8] [--json]``
終了コード: 0 = 検索した（当たりが無くても 0）、2 = 要約のフォルダが無い・読めない、検索語が 1 つも無い
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

K1 = 1.5
B = 0.75
TOP_DEFAULT = 8
SNIPPET_HALF = 70  # 文字
OTHER_CHUNK_SHARE = 0.25  # 2 番目以降の節の点数を足す割合
TITLE_WEIGHT = 3.0
SUMMARY_WEIGHT = 2.0
SUMMARY_SECTIONS = ("one-line summary", "summary", "abstract", "要約", "概要", "キーワード", "keywords")
METADATA_SECTIONS = ("metadata", "メタデータ", "書誌情報", "bibliographic information")
STOPWORDS = frozenset(
    "a an and are as at be by for from in is it of on or our that the this to was we were with which using".split()
)
_WORD = re.compile(r"[a-z0-9α-ω]+(?:-[a-z0-9α-ω]+)*")
_GREEK = re.compile(r"[α-ω]")
_CJK_RUN = re.compile(r"[぀-ヿ㐀-䶿一-鿿々ー]+")
_HIRAGANA = re.compile(r"[぀-ゟ]+")
_KANJI = re.compile(r"[㐀-䶿一-鿿々]")
_LATIN_ACCENTED = re.compile(r"[À-ɏ]")
_KEY_LINE = re.compile(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$")
_LIST_ITEM = re.compile(r"^\s+-\s+(.*)$")
_META_BULLET = re.compile(r"^\s*[-*]\s*\*\*(.+?)\*\*\s*[:：]\s*(.*)$")
_META_KEYS = {
    "authors": "authors", "author": "authors", "著者": "authors", "year": "year", "年": "year", "発行年": "year",
    "journal": "journal", "誌名": "journal", "雑誌": "journal", "doi": "doi", "url": "url", "tags": "tags",
    "タグ": "tags", "keywords": "tags", "title": "title", "題名": "title", "タイトル": "title",
}
ENCODINGS = ("utf-8-sig", "cp932")


@dataclass(frozen=True)
class Section:
    name: str
    text: str


@dataclass(frozen=True)
class Paper:
    path: Path
    title: str
    authors: tuple[str, ...]
    year: str
    journal: str
    doi: str
    url: str
    tags: tuple[str, ...]
    sections: tuple[Section, ...]


@dataclass(frozen=True)
class Hit:
    paper: Paper
    score: float
    section: str
    snippet: str


def _fold_latin(text: str) -> str:
    """アクセントつきのラテン文字だけ、アクセントを外す（日本語の濁点は触らない）。"""
    return _LATIN_ACCENTED.sub(
        lambda m: "".join(c for c in unicodedata.normalize("NFKD", m.group(0)) if not unicodedata.combining(c)), text
    )


def _normalize(text: str) -> str:
    return _fold_latin(unicodedata.normalize("NFKC", text))


def tokenize(text: str) -> list[str]:
    """検索語に分ける。英語は単語（ギリシャ文字は 1 文字でも残す）、日本語は漢字・カタカナの 2 文字ずつ（1 文字の語はそのまま）。"""
    text = _normalize(text).lower()
    tokens: list[str] = []
    for word in _WORD.findall(text):
        parts = word.split("-")
        tokens.extend(p for p in parts if p not in STOPWORDS and (len(p) > 1 or _GREEK.search(p)))
        if len(parts) > 1 and all(p.isascii() for p in parts):
            tokens.append("".join(parts))  # X-ray → xray、solid-state → solidstate
    for run in _CJK_RUN.findall(text):
        for segment in _HIRAGANA.split(run):
            if len(segment) == 1:
                tokens.append(segment)
            tokens.extend(segment[i : i + 2] for i in range(len(segment) - 1))
    return tokens


def _index_tokens(text: str) -> list[str]:
    """索引に入れる語: 検索語に加えて漢字 1 文字ずつ（1 文字の問いが長い語に当たるように）。"""
    return tokenize(text) + _KANJI.findall(unicodedata.normalize("NFKC", text))


def _strip_quotes(value: str) -> str:
    value = value.strip()
    return value[1:-1] if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'" else value


def _value(raw: str) -> object:
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        return [_strip_quotes(v) for v in raw[1:-1].split(",") if v.strip()]  # tags: [a, b]
    return _strip_quotes(raw) if raw else []


def _frontmatter(lines: list[str]) -> tuple[dict[str, object], int]:
    """先頭の --- で囲まれた部分を読む（key: value・[a, b]・「  - 項目」）。閉じていなくても読めた分は使う。"""
    if not lines or lines[0].strip() != "---":
        return {}, 0
    meta: dict[str, object] = {}
    key = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return meta, i + 1
        item, pair = _LIST_ITEM.match(line), _KEY_LINE.match(line)
        if item and key is not None:
            current = meta.get(key)
            meta[key] = [*(current if isinstance(current, list) else []), _strip_quotes(item.group(1))]
        elif pair:
            key = pair.group(1)
            meta[key] = _value(pair.group(2))
        elif line.strip():
            return meta, i  # 閉じの --- が無い: ここから本文
    return meta, len(lines)


def _sections(lines: list[str]) -> tuple[str, list[Section]]:
    title, name, buf, out = "", "本文", [], []
    for line in lines:
        if line.startswith("# ") and not title:
            title = line[2:].strip()
        elif line.startswith("## "):
            if "".join(buf).strip():
                out.append(Section(name, "\n".join(buf).strip()))
            name, buf = line[3:].strip(), []
        else:
            buf.append(line)
    if "".join(buf).strip():
        out.append(Section(name, "\n".join(buf).strip()))
    return title, out


def _split_list(value: str, field: str) -> list[str]:
    if field == "authors":
        parts = value.split(";") if ";" in value else value.split(",")
    else:
        parts = re.split(r"[,、;]", value)
    return [p.strip() for p in parts if p.strip()]


def _bullet_metadata(sections: list[Section]) -> dict[str, object]:
    """「## Metadata」などの節（無ければ最初の節）の「- **Key**: value」を書誌として読む。"""
    chosen = [s for s in sections if s.name.lower() in METADATA_SECTIONS] or sections[:1]
    meta: dict[str, object] = {}
    for section in chosen:
        for line in section.text.splitlines():
            m = _META_BULLET.match(line)
            field = _META_KEYS.get(m.group(1).strip().lower()) if m else None
            if field and field not in meta:
                value = m.group(2).strip()
                meta[field] = _split_list(value, field) if field in ("authors", "tags") else value
    return meta


def _as_tuple(value: object) -> tuple[str, ...]:
    if isinstance(value, list):
        return tuple(str(v) for v in value)
    return (str(value),) if value else ()


def _read_text(path: Path) -> str:
    for encoding in ENCODINGS:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("utf-8/cp932", b"", 0, 1, f"{path.name} は UTF-8 でも Shift_JIS でも読めない")


def load_paper(path: Path) -> Paper:
    lines = _read_text(path).splitlines()
    front, start = _frontmatter(lines)
    heading, sections = _sections(lines[start:])
    meta = {**_bullet_metadata(sections), **{k: v for k, v in front.items() if v}}
    return Paper(
        path=path, title=str(meta.get("title") or heading or path.stem), authors=_as_tuple(meta.get("authors")),
        year=str(meta.get("year") or ""), journal=str(meta.get("journal") or ""), doi=str(meta.get("doi") or ""),
        url=str(meta.get("url") or ""), tags=_as_tuple(meta.get("tags")), sections=tuple(sections),
    )


def load_library_report(folder: Path) -> tuple[list[Paper], list[Path]]:
    """要約を読み込む。読めた論文と、読めなかったファイルを返す（大文字の .MD も読む）。"""
    papers, unreadable = [], []
    for path in sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".md"):
        try:
            papers.append(load_paper(path))
        except (UnicodeDecodeError, OSError):
            unreadable.append(path)
    return papers, unreadable


def load_library(folder: Path) -> list[Paper]:
    return load_library_report(folder)[0]


@dataclass(frozen=True)
class _Chunk:
    paper_index: int
    section: str
    text: str
    counts: Counter
    length: int
    weight: float


@dataclass(frozen=True)
class _Index:
    chunks: list[_Chunk]
    postings: dict[str, list[tuple[int, int]]]
    avg_length: float


def _build_index(papers: list[Paper]) -> _Index:
    chunks = []
    for i, paper in enumerate(papers):
        head = " ".join([paper.title, *paper.tags])
        head_tokens = _index_tokens(head)
        chunks.append(_Chunk(i, "題名・タグ", head, Counter(head_tokens), len(head_tokens), TITLE_WEIGHT))
        for section in paper.sections:
            weight = SUMMARY_WEIGHT if section.name.lower() in SUMMARY_SECTIONS else 1.0
            tokens = _index_tokens(section.text)
            chunks.append(_Chunk(i, section.name, section.text, Counter(tokens), len(tokens), weight))
    postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for idx, chunk in enumerate(chunks):
        for term, tf in chunk.counts.items():
            postings[term].append((idx, tf))
    avg = sum(c.length for c in chunks) / len(chunks) if chunks else 1.0
    return _Index(chunks, dict(postings), avg or 1.0)


def _bm25(index: _Index, terms: list[str]) -> dict[int, float]:
    """問いの語を含む節だけを数える（転置索引）。"""
    n = len(index.chunks)
    scores: dict[int, float] = defaultdict(float)
    for term in set(terms):
        plist = index.postings.get(term)
        if not plist:
            continue
        idf = math.log((n - len(plist) + 0.5) / (len(plist) + 0.5) + 1)
        for idx, tf in plist:
            length = index.chunks[idx].length or 1
            scores[idx] += idf * tf * (K1 + 1) / (tf + K1 * (1 - B + B * length / index.avg_length))
    return {idx: s * index.chunks[idx].weight for idx, s in scores.items()}


def _snippet(text: str, query_tokens: list[str]) -> str:
    flat = " ".join(_normalize(text).split())
    low = flat.lower()
    positions = [low.find(t) for t in query_tokens if low.find(t) >= 0]
    at = min(positions) if positions else 0
    start = max(0, at - SNIPPET_HALF)
    piece = flat[start : at + SNIPPET_HALF]
    return ("…" if start > 0 else "") + piece + ("…" if at + SNIPPET_HALF < len(flat) else "")


def search(papers: list[Paper], queries: list[str], top: int = TOP_DEFAULT) -> list[Hit]:
    """問いごとに BM25 で論文の点数を出し、問いごとの最高点で割ってから足し合わせる。当たりの無い論文は返さない。"""
    index = _build_index(papers)
    if not index.chunks:
        return []
    total = [0.0] * len(papers)
    best: dict[int, tuple[float, _Chunk, list[str]]] = {}
    for query in queries:
        terms = tokenize(query)
        per_paper: dict[int, list[float]] = {}
        for idx, score in _bm25(index, terms).items():
            chunk = index.chunks[idx]
            per_paper.setdefault(chunk.paper_index, []).append(score)
            if chunk.section != "題名・タグ" and score > best.get(chunk.paper_index, (0.0,))[0]:
                best[chunk.paper_index] = (score, chunk, terms)
        combined = {i: max(v) + OTHER_CHUNK_SHARE * (sum(v) - max(v)) for i, v in per_paper.items()}
        top_score = max(combined.values(), default=0.0)
        for i, value in combined.items():
            total[i] += value / top_score if top_score else 0.0
    ranked = sorted((i for i, s in enumerate(total) if s > 0), key=lambda i: -total[i])[:top]
    hits = []
    for i in ranked:
        section, snippet = "題名・タグ", papers[i].title
        if i in best:
            _, chunk, terms = best[i]
            section, snippet = chunk.section, _snippet(chunk.text, terms)
        hits.append(Hit(papers[i], round(total[i], 3), section, snippet))
    return hits


def _find_library() -> Path:
    here = Path.cwd().resolve()
    for candidate in (here, *here.parents):
        if (candidate / "office" / "secretary").is_dir():
            return candidate / "work" / "papers" / "md"
    return Path("work") / "papers" / "md"


def _who(paper: Paper) -> str:
    if not paper.authors:
        return ""
    return paper.authors[0] + (" ほか" if len(paper.authors) > 1 else "")


def _shown(path: Path) -> str:
    text = str(path)
    return f'"{text}"' if any(c.isspace() for c in text) else text


def _count_line(n_papers: int, library: Path, unreadable: list[Path]) -> str:
    line = f"登録済み {n_papers} 本（{_shown(library)}）"
    if unreadable:
        names = "、".join(p.name for p in unreadable[:5]) + ("…" if len(unreadable) > 5 else "")
        line += f"。読めないファイル {len(unreadable)} 本（数に入れていない。UTF-8 で保存し直す）: {names}"
    return line


def _print_text(hits: list[Hit], count_line: str, n_papers: int, queries: list[str]) -> None:
    asked = " / ".join(f"「{q}」" for q in queries)
    print(f"{count_line}を検索（問い: {asked}）")
    if not hits:
        print(f"見当たりません（登録済み {n_papers} 本。言い換え・英語・別の用語でも探してから「無い」と判断する）")
        return
    for rank, hit in enumerate(hits, 1):
        p = hit.paper
        meta = "、".join(x for x in (_who(p), p.year, p.journal) if x)
        print(f"{rank}. {p.title}" + (f" — {meta}" if meta else "") + f"（目安の点 {hit.score}）")
        link = f"doi: {p.doi}　" if p.doi else (f"url: {p.url}　" if p.url else "")
        print(f"   {link}要約: {_shown(p.path)}")
        print(f"   合う節「{hit.section}」: {hit.snippet}")


def _hits_json(hits: list[Hit], n_papers: int, library: Path, unreadable: list[Path]) -> str:
    data = {
        "library": str(library),
        "papers": n_papers,
        "unreadable": [str(p) for p in unreadable],
        "hits": [
            {
                "title": h.paper.title, "authors": list(h.paper.authors), "year": h.paper.year,
                "journal": h.paper.journal, "doi": h.paper.doi, "url": h.paper.url, "path": str(h.paper.path),
                "score": h.score, "section": h.section, "snippet": h.snippet,
            }
            for h in hits
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def _positive(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("1 以上にする")
    return number


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description="登録済みの論文の要約から、問いに関係する論文と節を探す")
    parser.add_argument("queries", nargs="+", help="問い（日本語・英語の言い換えを複数渡すとよい）")
    parser.add_argument("--library", type=Path, help="要約のフォルダ（既定: プロジェクトの work/papers/md）")
    parser.add_argument("--top", type=_positive, default=TOP_DEFAULT, help="出す本数（1 以上）")
    parser.add_argument("--json", action="store_true", help="JSON で出す")
    args = parser.parse_args(argv)
    if not any(tokenize(q) for q in args.queries):
        print("検索語がありません（よくある語・記号だけの問いは探せない。専門用語や英語で言い換える）", file=sys.stderr)
        return 2
    library = args.library or _find_library()
    try:
        papers, unreadable = load_library_report(library)
    except OSError:
        print(f"要約のフォルダが見つかりません（読めません）: {library}", file=sys.stderr)
        return 2
    count_line = _count_line(len(papers), library, unreadable)
    if not papers:
        print(f"登録済みの論文がまだありません（{count_line}）。Web で探して答え、役に立った論文は登録を提案する")
        return 0
    hits = search(papers, args.queries, args.top)
    if args.json:
        print(_hits_json(hits, len(papers), library, unreadable))
    else:
        _print_text(hits, count_line, len(papers), args.queries)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
