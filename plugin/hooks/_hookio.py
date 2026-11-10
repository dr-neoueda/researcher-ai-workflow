#!/usr/bin/env python3
"""raw の hook の入力（標準入力の JSON）を読む小さな道具。Claude Code と Codex CLI の両方の形を読む。

使い方（標準入力に hook の JSON を渡す）:
  python3 _hookio.py project      office/ のあるプロジェクトの場所（無ければ何も出さない）
  python3 _hookio.py paths        書き換えたファイルを、プロジェクトからの相対パスで 1 行ずつ
  python3 _hookio.py stop-active  Stop hook で、すでに 1 度引き戻した後なら 1、そうでなければ 0

プロジェクトの場所は CLAUDE_PROJECT_DIR（Claude Code）→ 入力の cwd（両方）→ いまの場所 の順に、上へたどって
office/ を探す。書き換えたファイルは、Claude Code の tool_input.file_path と、Codex の apply_patch のパッチの
「*** Add/Update/Delete File:」「*** Move to:」の行から読む。
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterator

PATCH_PATH = re.compile(r"^\*\*\* (?:(?:Add|Update|Delete) File|Move to): (.+?)\s*$", re.M)


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
            if (candidate / "office").is_dir():
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


def edited_paths(data: dict[str, Any], root: Path) -> list[str]:
    """書き換えたファイルの、プロジェクトからの相対パス（プロジェクトの外は除く）。"""
    tool_input = data.get("tool_input")
    raw: list[str] = []
    if isinstance(tool_input, dict) and isinstance(tool_input.get("file_path"), str):
        raw.append(tool_input["file_path"])
    for text in _strings(tool_input):
        raw.extend(m.group(1) for m in PATCH_PATH.finditer(text))
    base = Path(data["cwd"]) if isinstance(data.get("cwd"), str) else Path.cwd()
    out: list[str] = []
    for item in raw:
        path = Path(item)
        absolute = (path if path.is_absolute() else base / path).resolve()
        try:
            out.append(absolute.relative_to(root).as_posix())
        except ValueError:
            continue
    return out


def main(argv: list[str]) -> int:
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
        print("\n".join(edited_paths(data, root)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
