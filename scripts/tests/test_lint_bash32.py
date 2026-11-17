"""scripts/lint-bash32.sh（bash 3.2 で落ちる「日本語の直前の裸の変数」の検査）のテスト。

Codex の事後レビュー（2026-11-17、PR #73）で見つかった取りこぼしを固定する:
- 日本語の名前の .sh を git が引用して返し、grep が開けずに素通りしていた（core.quotePath）
- ヒアドキュメントの中の「# $X）」をコメントとして外していた（実際は展開されて落ちる）
"""
from __future__ import annotations

import platform
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "lint-bash32.sh"

pytestmark = pytest.mark.skipif(platform.system() != "Darwin" or not Path("/bin/bash").exists(),
                                reason="macOS の /bin/bash 3.2 で走らせるテスト")

BAD = 'set -u\nX=ok\necho "$X）"\n'
GOOD = 'set -u\nX=ok\necho "${X}）"\n'


def _repo(tmp_path: Path, files: dict[str, str], git: bool = True) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    if git:
        subprocess.run(["git", "init", "-q", str(root)], check=True)
    for name, body in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    return root


def _lint(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["/bin/bash", str(SCRIPT)], cwd=root, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=60)


def _bash32_fails(path: Path) -> bool:
    """検査の答え合わせ: 本物の /bin/bash 3.2・UTF-8 で走らせて落ちるか。"""
    res = subprocess.run(["/bin/bash", str(path)], capture_output=True, text=True, errors="replace",
                         env={"PATH": "/usr/bin:/bin", "LC_ALL": "ja_JP.UTF-8"}, timeout=30)
    return res.returncode != 0 and "unbound variable" in res.stderr


def test_a_bare_variable_is_caught(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"a.sh": BAD})
    res = _lint(root)
    assert res.returncode == 1 and "a.sh:3:" in res.stdout


def test_a_braced_variable_passes(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"a.sh": GOOD, "sub/b.sh": GOOD})
    res = _lint(root)
    assert res.returncode == 0, res.stdout


def test_a_japanese_file_name_is_read(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"日本語.sh": BAD})
    assert _bash32_fails(root / "日本語.sh")
    res = _lint(root)
    assert res.returncode == 1 and "日本語.sh:3:" in res.stdout


def test_a_comment_like_line_in_a_heredoc_is_caught(tmp_path: Path) -> None:
    body = 'set -u\nX=ok\ncat <<EOF\n  # $X）\nEOF\n'
    root = _repo(tmp_path, {"here.sh": body})
    assert _bash32_fails(root / "here.sh")
    res = _lint(root)
    assert res.returncode == 1 and "here.sh:4:" in res.stdout


def test_works_outside_a_git_work_tree(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"日本語.sh": BAD, "ok.sh": GOOD}, git=False)
    res = _lint(root)
    assert res.returncode == 1 and "日本語.sh:3:" in res.stdout and "ok.sh" not in res.stdout


def test_a_tracked_file_deleted_from_the_work_tree_is_not_an_error(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"gone.sh": GOOD, "ok.sh": GOOD})
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    (root / "gone.sh").unlink()
    res = _lint(root)
    assert res.returncode == 0, res.stdout


# ---------- Codex の確かめの周（2026-11-17、v2.4.2）----------

def test_an_escaped_dollar_is_a_literal_and_passes(tmp_path: Path) -> None:
    """Codex v2.4.2 #6: 文字どおりの「$X）」を出したいとき、lint を通る同じ出力の書き方が無かった（${X} に変えると
    単引用符の中では出力が変わる）。\\$X は展開されないので落ちない。"""
    body = "set -u\nprintf '%s\\n' \"\\$X）\"\ncat <<EOF\n\\$X）\nEOF\n"
    root = _repo(tmp_path, {"literal.sh": body})
    res = subprocess.run(["/bin/bash", str(root / "literal.sh")], capture_output=True, text=True,
                         env={"PATH": "/usr/bin:/bin", "LC_ALL": "ja_JP.UTF-8"}, timeout=30)
    assert res.returncode == 0 and res.stdout == "$X）\n$X）\n"
    assert _lint(root).returncode == 0


def test_an_escaped_backslash_before_a_dollar_is_still_caught(tmp_path: Path) -> None:
    body = 'set -u\nX=ok\necho "\\\\$X）"\n'                      # \\ は \ 1 つで、$X は展開される
    root = _repo(tmp_path, {"a.sh": body})
    assert _bash32_fails(root / "a.sh")
    res = _lint(root)
    assert res.returncode == 1 and "a.sh:3:" in res.stdout


def test_a_finding_says_how_to_fix_it(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"a.sh": BAD})
    res = _lint(root)
    assert res.returncode == 1 and "${" in res.stdout and "\\$" in res.stdout   # 展開なら ${…}、文字どおりなら \$…


@pytest.mark.parametrize("line", ['v=`echo "\\$X）"`', 'eval "echo \\$X）"', '/bin/bash -uc "X=ok; echo \\$X）"'])
def test_an_escaped_dollar_that_is_parsed_again_is_still_caught(tmp_path: Path, line: str) -> None:
    """Codex（確かめの周 r2）P2: バッククォートの中では \\$ の \\ が外れてから中のコマンドが読まれ、$X） が展開されて落ちる。
    eval・sh -c も文字列をもう一度読むので同じ。これらの行では \\ の数で「文字どおり」と決めない。"""
    root = _repo(tmp_path, {"a.sh": f"set -u\nX=ok\n{line}\n"})
    assert _bash32_fails(root / "a.sh")
    res = _lint(root)
    assert res.returncode == 1 and "a.sh:3:" in res.stdout
