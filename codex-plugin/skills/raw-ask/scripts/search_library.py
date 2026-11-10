#!/usr/bin/env python3
"""登録済みの論文（work/papers/md の要約）から、研究の質問に関係する論文と節を探す（raw-ask）。

raw-register が作った要約 md（frontmatter に title・authors・year・doi、本文は「## 節」）を読み、BM25 で順位を付ける。
日本語は文字の 2 文字ずつ（ひらがなを除く）、英語は単語で数える。題名とタグ、要約・キーワードの節は重く数える。
問いは複数渡せる（日本語と英語の言い換えなど）。それぞれの順位を合わせて並べる。

点数は「どれから読むか」の目安で、関係があるかは上位の節を実際に読んで決める。何も当たらないときは、
言い換えでも探してから「登録済みの N 本には見当たらない」と言う（N はこの道具が数える）。

実行: ``python search_library.py "問い" ["言い換え" ...] [--library work/papers/md] [--top 8] [--json]``
終了コード: 0 = 検索した（当たりが無くても 0）、2 = 要約のフォルダが無い
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import unicodedata
from collections import Counter
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
STOPWORDS = frozenset(
    "a an and are as at be by for from in is it of on or our that the this to was we were with which using".split()
)
_ASCII_WORD = re.compile(r"[a-z0-9]+")
_CJK_RUN = re.compile(r"[぀-ヿ㐀-䶿一-鿿々ー]+")
_HIRAGANA = re.compile(r"[぀-ゟ]+")


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


def tokenize(text: str) -> list[str]:
    """英語は単語、日本語はひらがなで区切った漢字・カタカナの 2 文字ずつ（1 文字の語はそのまま）。"""
    text = unicodedata.normalize("NFKC", text).lower()
    tokens = [w for w in _ASCII_WORD.findall(text) if w not in STOPWORDS and len(w) > 1]
    for run in _CJK_RUN.findall(text):
        for segment in _HIRAGANA.split(run):
            if len(segment) == 1:
                tokens.append(segment)
            tokens.extend(segment[i : i + 2] for i in range(len(segment) - 1))
    return tokens


def _strip_quotes(value: str) -> str:
    value = value.strip()
    return value[1:-1] if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'" else value


def _frontmatter(lines: list[str]) -> tuple[dict[str, object], int]:
    """先頭の --- で囲まれた部分を読む（key: value と「  - 項目」の並びだけ）。本文の始まりの行番号も返す。"""
    if not lines or lines[0].strip() != "---":
        return {}, 0
    meta: dict[str, object] = {}
    key = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return meta, i + 1
        item = re.match(r"^\s+-\s+(.*)$", line)
        if item and key is not None:
            current = meta.get(key)
            meta[key] = [*(current if isinstance(current, list) else []), _strip_quotes(item.group(1))]
            continue
        pair = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", line)
        if pair:
            key = pair.group(1)
            meta[key] = _strip_quotes(pair.group(2)) if pair.group(2).strip() else []
    return {}, 0


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


def _as_tuple(value: object) -> tuple[str, ...]:
    if isinstance(value, list):
        return tuple(str(v) for v in value)
    return (str(value),) if value else ()


def load_paper(path: Path) -> Paper:
    lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    meta, start = _frontmatter(lines)
    heading, sections = _sections(lines[start:])
    return Paper(
        path=path, title=str(meta.get("title") or heading or path.stem), authors=_as_tuple(meta.get("authors")),
        year=str(meta.get("year") or ""), journal=str(meta.get("journal") or ""), doi=str(meta.get("doi") or ""),
        url=str(meta.get("url") or ""), tags=_as_tuple(meta.get("tags")), sections=tuple(sections),
    )


def load_library(folder: Path) -> list[Paper]:
    return [load_paper(p) for p in sorted(folder.glob("*.md")) if p.is_file()]


@dataclass(frozen=True)
class _Chunk:
    paper_index: int
    section: str
    text: str
    counts: Counter
    length: int
    weight: float


def _chunks(papers: list[Paper]) -> list[_Chunk]:
    chunks = []
    for i, paper in enumerate(papers):
        head = " ".join([paper.title, *paper.tags])
        head_tokens = tokenize(head)
        chunks.append(_Chunk(i, "題名・タグ", head, Counter(head_tokens), len(head_tokens), TITLE_WEIGHT))
        for section in paper.sections:
            weight = SUMMARY_WEIGHT if section.name.lower() in SUMMARY_SECTIONS else 1.0
            tokens = tokenize(section.text)
            chunks.append(_Chunk(i, section.name, section.text, Counter(tokens), len(tokens), weight))
    return chunks


def _bm25(chunks: list[_Chunk], query: list[str]) -> list[float]:
    n = len(chunks)
    avg = sum(c.length for c in chunks) / n if n else 1.0
    terms = set(query)
    df = {t: sum(1 for c in chunks if t in c.counts) for t in terms}
    scores = []
    for chunk in chunks:
        length = chunk.length or 1
        score = 0.0
        for term in terms:
            tf = chunk.counts.get(term, 0)
            if tf == 0:
                continue
            idf = math.log((n - df[term] + 0.5) / (df[term] + 0.5) + 1)
            score += idf * tf * (K1 + 1) / (tf + K1 * (1 - B + B * length / avg))
        scores.append(score * chunk.weight)
    return scores


def _snippet(text: str, query_tokens: list[str]) -> str:
    flat = " ".join(text.split())
    low = unicodedata.normalize("NFKC", flat).lower()
    positions = [low.find(t) for t in query_tokens if low.find(t) >= 0]
    at = min(positions) if positions else 0
    start = max(0, at - SNIPPET_HALF)
    piece = flat[start : at + SNIPPET_HALF]
    return ("…" if start > 0 else "") + piece + ("…" if at + SNIPPET_HALF < len(flat) else "")


def search(papers: list[Paper], queries: list[str], top: int = TOP_DEFAULT) -> list[Hit]:
    """問いごとに BM25 で論文の点数を出し、問いごとの最高点で割ってから足し合わせる。当たりの無い論文は返さない。"""
    chunks = _chunks(papers)
    if not chunks:
        return []
    total = [0.0] * len(papers)
    best: dict[int, tuple[float, _Chunk, list[str]]] = {}
    for query in queries:
        terms = tokenize(query)
        scores = _bm25(chunks, terms)
        per_paper: dict[int, list[float]] = {}
        for chunk, score in zip(chunks, scores):
            if score <= 0:
                continue
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


def _print_text(hits: list[Hit], n_papers: int, queries: list[str]) -> None:
    asked = " / ".join(f"「{q}」" for q in queries)
    print(f"登録済み {n_papers} 本を検索（問い: {asked}）")
    if not hits:
        print(f"見当たりません（登録済み {n_papers} 本。言い換え・英語・別の用語でも探してから「無い」と判断する）")
        return
    for rank, hit in enumerate(hits, 1):
        p = hit.paper
        meta = "、".join(x for x in (_who(p), p.year, p.journal) if x)
        print(f"{rank}. {p.title}" + (f" — {meta}" if meta else "") + f"（目安の点 {hit.score}）")
        link = f"doi: {p.doi}　" if p.doi else (f"url: {p.url}　" if p.url else "")
        print(f"   {link}要約: {p.path}")
        print(f"   合う節「{hit.section}」: {hit.snippet}")


def _hits_json(hits: list[Hit], n_papers: int) -> str:
    data = {
        "papers": n_papers,
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


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description="登録済みの論文の要約から、問いに関係する論文と節を探す")
    parser.add_argument("queries", nargs="+", help="問い（日本語・英語の言い換えを複数渡すとよい）")
    parser.add_argument("--library", type=Path, help="要約のフォルダ（既定: プロジェクトの work/papers/md）")
    parser.add_argument("--top", type=int, default=TOP_DEFAULT, help="出す本数")
    parser.add_argument("--json", action="store_true", help="JSON で出す")
    args = parser.parse_args(argv)
    library = args.library or _find_library()
    if not library.is_dir():
        print(f"要約のフォルダが見つかりません: {library}", file=sys.stderr)
        return 2
    papers = load_library(library)
    if not papers:
        print(f"登録済みの論文がまだありません（{library}）。Web で探して答え、役に立った論文は登録を提案する")
        return 0
    hits = search(papers, args.queries, args.top)
    if args.json:
        print(_hits_json(hits, len(papers)))
    else:
        _print_text(hits, len(papers), args.queries)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
