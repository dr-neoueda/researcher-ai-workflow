#!/usr/bin/env python3
"""raw の hook の入力（標準入力の JSON）を読む小さな道具。Claude Code と Codex CLI の両方の形を読む。

使い方（標準入力に hook の JSON を渡す）:
  python3 _hookio.py project      office/ のあるプロジェクトの場所（無ければ何も出さない）
  python3 _hookio.py paths        書き換えたファイルを、プロジェクトからの相対パスで 1 行ずつ
  python3 _hookio.py stop-active  Stop hook で、すでに 1 度引き戻した後なら 1、そうでなければ 0

プロジェクトの場所は CLAUDE_PROJECT_DIR（Claude Code）→ 入力の cwd（両方）→ いまの場所 の順に、上へたどって
raw の office/（中に secretary/ がある）を探す。書き換えたファイルは、Claude Code の tool_input.file_path と、Codex の apply_patch のパッチの
「*** Add/Update/Delete File:」「*** Move to:」の行から読む。シェルの道具（Claude Code の Bash など）で書いたものは
道具の入力から書き込み先が分からないので、直前の RECENT_SECONDS 秒に office/ の中で変わったファイルとして拾う。
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Iterator

SHELL_TOOLS = ("Bash", "shell", "local_shell", "exec_command")  # シェルの道具（Claude Code・Codex）
RECENT_SECONDS = 120  # シェルで書いたファイルを拾う窓（秒）。前からある置き違いでは毎回警告しない
CLOCK_SLACK_SECONDS = 300  # これより先の時刻のファイルは「先の日付」とみなして数えない（時計の進んだ共有ドライブの数分は数える）
PATCH_HEADER = re.compile(r"^\*\*\* (Add File|Update File|Delete File|Move to): (.+?)\s*$", re.M)


def load(stream: Any = None) -> dict[str, Any]:
    try:
        data = json.load(stream or sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def project_root(data: dict[str, Any]) -> Path | None:
    for start in (os.environ.get("CLAUDE_PROJECT_DIR"), data.get("cwd"), os.getcwd()):
        if not isinstance(start, str) or not start:
            continue
        here = Path(start).resolve()
        for candidate in (here, *here.parents):
            if (candidate / "office" / "secretary").is_dir():  # 別の「office」フォルダを取り違えない
                return candidate
    return None


def _strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def _patch_targets(text: str) -> list[str]:
    """apply_patch のパッチで書き込んだファイル。削除は違反ではないので数えない（同じパッチで先に足したものも外す）。
    「Update File: 元」の直後の「Move to: 先」は移動なので、元は書き込み先から外して先だけを数える。
    引用符は外さない（Codex 0.167 の apply_patch は引用符も名前の一部として書く。実機で確かめた）。"""
    targets: list[str] = []
    previous = ""
    for match in PATCH_HEADER.finditer(text):
        kind, path = match.group(1), match.group(2)
        if kind == "Move to" and previous == "Update File" and targets:
            targets[-1] = path
        elif kind == "Delete File":
            targets = [target for target in targets if target != path]
        else:
            targets.append(path)
        previous = kind
    return targets


def recent_office_files(root: Path, now: float | None = None, places: list[str] | None = None) -> list[str]:
    """office/ の中（places があればその旧い置き場所だけ）で、直前 RECENT_SECONDS 秒に置かれたファイル。
    mv・cp -p は更新時刻を古いまま保つので、状態の変更時刻（ctime。移したときに変わる）も見る。ctime は chmod・
    拡張属性・同期ソフトでも変わるので、旧い置き場所に前からあるファイルを 120 秒の間くり返し警告することがある
    （置き違いには違いないので許す）。Windows の st_ctime は作成時刻（コピーは拾い、属性の変更は拾わない）。
    道具の入力から書き込み先が分からないときの拾い方なので、取りこぼしはありうる（長いコマンドの初めに書いたもの等）。
    いまより先の時刻（時計の進んだ機械から時刻ごと写したもの）は、いつ変わったか分からないので数えない。
    旧い置き場所が work/ へのリンクなら、中身の本当の場所は office/ の外なので数えない。"""
    current = time.time() if now is None else now
    cutoff = current - RECENT_SECONDS
    bases = [root / place for place in places] if places is not None else [root / "office"]
    try:
        office = (root / "office").resolve()
    except (OSError, RuntimeError):
        return []
    found: set[str] = set()
    for base in bases:
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            try:
                info = path.stat()
                stamps = [t for t in (info.st_mtime, info.st_ctime) if t <= current + CLOCK_SLACK_SECONDS]
                if not path.is_file() or not stamps or max(stamps) < cutoff:
                    continue
                path.resolve().relative_to(office)   # office/ の外（work/ へのリンクの先）なら ValueError で飛ばす
                found.add(path.relative_to(root).as_posix())
            except (OSError, ValueError, RuntimeError):
                continue
    return sorted(found)


def edited_paths(data: dict[str, Any], root: Path) -> list[str]:
    """書き換えたファイルの、プロジェクトからの相対パス（プロジェクトの外は除く）。"""
    if data.get("tool_name") in SHELL_TOOLS:
        listed = os.environ.get("RAW_LEGACY_PLACES")  # 渡されたら（空でも）その場所だけ。渡されなければ office/ 全体
        places = None if listed is None else [line.strip() for line in listed.splitlines() if line.strip()]
        return recent_office_files(root, places=places)
    tool_input = data.get("tool_input")
    raw: list[str] = []
    if isinstance(tool_input, dict) and isinstance(tool_input.get("file_path"), str):
        raw.append(tool_input["file_path"])
    if data.get("tool_name") in (None, "apply_patch"):  # Write の本文に書いたパッチの例は読まない
        for text in _strings(tool_input):
            raw.extend(_patch_targets(text))
    base = Path(data["cwd"]) if isinstance(data.get("cwd"), str) else Path.cwd()
    out: list[str] = []
    for item in raw:
        path = Path(item)
        try:
            absolute = (path if path.is_absolute() else base / path).resolve()
            out.append(absolute.relative_to(root).as_posix())
        except (ValueError, OSError, RuntimeError):  # プロジェクトの外・NUL を含むパス・リンクの輪（3.12 以前）
            continue
    return out


def _utf8_stdio() -> None:
    """日本語の Windows（cp932）でも、UTF-8 の JSON を読み、UTF-8 で書く。入力の先頭の BOM は読み飛ばす。
    改行は LF に固定する（Windows の Python は CRLF で書き、bash の $(…) は LF しか外さないのでパスに CR が残る）。"""
    for stream, options in ((sys.stdin, {"encoding": "utf-8-sig"}), (sys.stdout, {"encoding": "utf-8", "newline": "\n"})):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="replace", **options)


def _one_line(path: str) -> str:
    """1 行に 1 つのパスで渡すので、名前の中の改行は \\n と書いて見せる（行が途中で切れないように）。"""
    return path.replace("\n", "\\n").replace("\r", "\\r")


def main(argv: list[str]) -> int:
    _utf8_stdio()
    if len(argv) != 2 or argv[1] not in ("project", "paths", "stop-active"):
        print(__doc__, file=sys.stderr)
        return 2
    data = load()
    if argv[1] == "stop-active":
        print("1" if data.get("stop_hook_active") else "0")
        return 0
    root = project_root(data)
    if root is None:
        return 0
    if argv[1] == "project":
        print(root)
    else:
        print("\n".join(_one_line(path) for path in edited_paths(data, root)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
