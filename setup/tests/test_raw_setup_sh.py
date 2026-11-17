"""setup/raw-setup.sh（macOS の導入スクリプト）のテスト。

真っさらな Mac の流れを、偽物の Homebrew とツールで再現する:
- 開発ツール（Command Line Tools）が無い: 偽の xcode-select が失敗する ⇒ /usr/bin/git・/usr/bin/python3 は「入口」だけ
- Homebrew は入っていない。入れると PATH に無い置き場所（RAW_SETUP_BREW_PREFIXES）に入る
- macOS 標準の /bin/bash 3.2 を、日本語のロケールで走らせる
2026-11-16 の真っさらな仮想機での動作テストで見つかった F1〜F5 を固定する。
"""
from __future__ import annotations

import os
import platform
import re
import stat
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "raw-setup.sh"

pytestmark = pytest.mark.skipif(platform.system() != "Darwin" or not Path("/bin/bash").exists(),
                                reason="macOS の /bin/bash で走らせるテスト")

FAKE_BREW = r'''#!/bin/bash
# 偽の Homebrew: shellenv と install だけ
prefix="$(cd "$(dirname "$0")/.." && pwd)"
case "$1" in
  shellenv) echo "export PATH=\"$prefix/bin:\$PATH\"; export HOMEBREW_PREFIX=\"$prefix\";" ;;
  install)
    shift
    [ "$1" = "--cask" ] && shift
    pkg="$1"
    [ -n "${FAKE_BREW_FAIL:-}" ] && [ "$pkg" = "$FAKE_BREW_FAIL" ] && { echo "Error: $pkg failed" >&2; exit 1; }
    make() { printf '#!/bin/bash\n%s\n' "$2" > "$prefix/bin/$1"; chmod +x "$prefix/bin/$1"; }
    case "$pkg" in
      node)
        make node 'echo v26.0.0'
        make npm 'if [ "$1 $2" = "install -g" ]; then printf "#!/bin/bash\necho \"9.9.9 (Claude Code)\"\n" > "$(dirname "$0")/claude"; chmod +x "$(dirname "$0")/claude"; fi' ;;
      git) make git 'echo "git version 9.9.9"' ;;
      python)
        make python3 'case "$1" in --version) echo "Python 3.13.0";; -m) exit 0;; -c) exit 0;; *) exit 0;; esac' ;;
      poppler) make pdftoppm 'echo "pdftoppm version 9.9.9" >&2' ;;
      *) make "$pkg" 'exit 0' ;;
    esac ;;
  *) exit 0 ;;
esac
'''


def _exe(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


@pytest.fixture()
def fresh_mac(tmp_path: Path) -> dict:
    """真っさらな Mac: 開発ツールなし・Homebrew なし（入れると PATH に無い場所に入る）。"""
    home = tmp_path / "home"
    home.mkdir()
    bindir = tmp_path / "bin"
    bindir.mkdir()
    _exe(bindir / "xcode-select", "#!/bin/bash\necho 'xcode-select: error: no developer tools' >&2\nexit 2\n")
    prefix = tmp_path / "brew"
    installer = tmp_path / "install-brew.sh"
    brew_src = tmp_path / "brew-src"
    brew_src.write_text(FAKE_BREW, encoding="utf-8")
    _exe(installer, f"#!/bin/bash\nmkdir -p '{prefix}/bin' && cp '{brew_src}' '{prefix}/bin/brew' && chmod +x '{prefix}/bin/brew'\n")
    env = {
        "HOME": str(home), "TMPDIR": str(tmp_path), "PATH": f"{bindir}:/usr/bin:/bin",
        "LANG": "ja_JP.UTF-8", "LC_ALL": "ja_JP.UTF-8",
        "RAW_SETUP_BREW_PREFIXES": str(prefix), "RAW_SETUP_HOMEBREW_INSTALL": f"bash '{installer}'",
    }
    return {"env": env, "home": home, "prefix": prefix, "installer": installer}


ANSI = re.compile(r"\x1b\[[0-9;]*m")


def run_setup(env: dict, answers: str = "y\ny\nn\nn\n") -> subprocess.CompletedProcess:
    """色の付け方を外した出力で返す（化けた字＝F1 も読めるように errors=replace）。"""
    res = subprocess.run(["/bin/bash", str(SCRIPT)], input=answers, capture_output=True, text=True,
                         encoding="utf-8", errors="replace", env=env, timeout=120)
    return subprocess.CompletedProcess(res.args, res.returncode, ANSI.sub("", res.stdout), ANSI.sub("", res.stderr))


def test_a_fresh_mac_gets_every_tool_and_claude_code(fresh_mac: dict) -> None:
    res = run_setup(fresh_mac["env"])
    out = res.stdout + res.stderr
    assert "unbound variable" not in out                                   # F1: bash 3.2 の日本語の直前の変数
    assert res.returncode == 0, out
    for name in ("Node.js", "git", "Python 3", "poppler (pdftoppm)", "Claude Code"):
        assert f"OK  {name}" in out, name                                    # F3: Homebrew の直後に brew が見える
    assert "brew 未導入のため" not in out


def test_tool_stubs_without_developer_tools_are_not_counted_as_installed(fresh_mac: dict) -> None:
    out = run_setup(fresh_mac["env"], answers="n\n").stdout                  # 計画を見て中止
    assert "git は導入済み" not in out and "Python 3 は導入済み" not in out   # F2: /usr/bin の入口を取り違えない
    assert "・git" in out and "・Python 3" in out


def test_an_old_python_is_replaced(tmp_path: Path, fresh_mac: dict) -> None:
    _exe(tmp_path / "bin" / "xcode-select", "#!/bin/bash\necho /Library/Developer/CommandLineTools\n")
    py = tmp_path / "bin" / "python3"                                        # 開発ツールの Python 3.9
    _exe(py, "#!/bin/bash\ncase \"$1\" in --version) echo 'Python 3.9.6';; -c) case \"$2\" in *version_info*) exit 1;; *) exit 0;; esac;; *) exit 0;; esac\n")
    out = run_setup(fresh_mac["env"], answers="n\n").stdout
    assert "Python 3 は導入済み" not in out and "3.10 以上" in out


def test_homebrew_is_added_to_zprofile_once(fresh_mac: dict) -> None:
    run_setup(fresh_mac["env"])
    run_setup(fresh_mac["env"])                                              # 2 回目は brew が PATH に無くても置き場所から読む
    zprofile = (fresh_mac["home"] / ".zprofile").read_text(encoding="utf-8")
    assert zprofile.count("brew shellenv") == 1 and str(fresh_mac["prefix"]) in zprofile


def test_an_installed_but_unlisted_homebrew_is_used_without_reinstalling(fresh_mac: dict) -> None:
    subprocess.run(["bash", str(fresh_mac["installer"])], check=True)        # Homebrew は入っているが PATH に無い
    env = {**fresh_mac["env"], "RAW_SETUP_HOMEBREW_INSTALL": "echo REINSTALLED; exit 1"}
    res = run_setup(env, answers="y\nn\nn\n")
    assert "REINSTALLED" not in res.stdout and "Homebrew を導入しますか" not in res.stdout
    assert res.returncode == 0 and "OK  Claude Code" in res.stdout


def test_the_final_check_prints_versions(fresh_mac: dict) -> None:
    out = run_setup(fresh_mac["env"]).stdout
    assert "== -1 ==" not in out                                             # F4: 見出しの関数が head を乗っ取っていた
    assert "node: v26.0.0" in out and "claude: 9.9.9 (Claude Code)" in out


def test_failures_are_summarised_and_exit_non_zero(fresh_mac: dict) -> None:
    env = {**fresh_mac["env"], "FAKE_BREW_FAIL": "poppler"}
    res = run_setup(env)
    assert res.returncode == 1                                               # F5: FAIL があっても 0 で終わっていた
    assert "うまくいかなかったもの" in res.stdout


def test_declining_homebrew_ends_with_a_failure_summary(fresh_mac: dict) -> None:
    res = run_setup(fresh_mac["env"], answers="y\nn\nn\nn\n")
    assert res.returncode == 1 and "うまくいかなかったもの" in res.stdout


# ---------- レビューの指摘（2026-11-16）----------

def _dev_tools(tmp_path: Path, with_git: bool = True) -> None:
    """開発ツールがある Mac: xcode-select -p が開発ツールの場所を返す（with_git=False なら中身が壊れている）。"""
    dev = tmp_path / "devtools"
    (dev / "usr" / "bin").mkdir(parents=True)
    if with_git:
        _exe(dev / "usr" / "bin" / "git", "#!/bin/bash\necho 'git version 2.0 (Apple)'\n")
    _exe(tmp_path / "bin" / "xcode-select", f"#!/bin/bash\necho '{dev}'\n")


def _old_python(tmp_path: Path) -> None:
    _exe(tmp_path / "bin" / "python3",
         "#!/bin/bash\ncase \"$1\" in --version) echo 'Python 3.9.6';; -c) case \"$2\" in *version_info*) exit 1;; *) exit 1;; esac;; *) exit 1;; esac\n")


def test_a_python_installed_by_homebrew_is_used_right_away(tmp_path: Path, fresh_mac: dict) -> None:
    """H1: 開発ツールと Homebrew がある普通の Mac で python3 が 3.9 のとき。計画で古い python3 を走らせると
    bash が場所を覚え、brew で入れた新しい python3 に切り替わらず、pip を飛ばして失敗と報告していた。"""
    _dev_tools(tmp_path)
    _old_python(tmp_path)
    subprocess.run(["bash", str(fresh_mac["installer"])], check=True)          # Homebrew は入っていて PATH にもある
    env = {**fresh_mac["env"], "PATH": f"{fresh_mac['prefix']}/bin:{tmp_path}/bin:/usr/bin:/bin"}
    res = run_setup(env, answers="y\nn\nn\n")
    assert res.returncode == 0, res.stdout
    assert "OK  Python packages" in res.stdout and "python3: Python 3.13.0" in res.stdout


def test_cancelling_leaves_zprofile_untouched(fresh_mac: dict) -> None:
    """M1: 承認の前に ~/.zprofile を書き換えていた（中止しても変わる）。"""
    subprocess.run(["bash", str(fresh_mac["installer"])], check=True)          # 入っているが PATH に無い
    run_setup(fresh_mac["env"], answers="n\n")
    assert not (fresh_mac["home"] / ".zprofile").exists()


def test_broken_developer_tools_are_not_counted(tmp_path: Path, fresh_mac: dict) -> None:
    """M3: xcode-select -p は成功するが、開発ツールの中身が無い（OS の更新で壊れた等）。"""
    _dev_tools(tmp_path, with_git=False)
    out = run_setup(fresh_mac["env"], answers="n\n").stdout
    assert "git は導入済み" not in out


def test_a_commented_out_shellenv_line_does_not_count(fresh_mac: dict) -> None:
    zprofile = fresh_mac["home"] / ".zprofile"
    zprofile.write_text(f'# eval "$({fresh_mac["prefix"]}/bin/brew shellenv)"\n', encoding="utf-8")
    run_setup(fresh_mac["env"])
    lines = [line for line in zprofile.read_text(encoding="utf-8").splitlines() if "brew shellenv" in line]
    assert len(lines) == 2 and not lines[1].lstrip().startswith("#")


def test_the_homebrew_step_warns_about_the_password_prompt(fresh_mac: dict) -> None:
    """M2: Homebrew の公式の導入は sudo のパスワードを聞き、管理者のアカウントが要る。"""
    out = run_setup(fresh_mac["env"]).stdout
    assert "パスワード" in out and "管理者" in out
