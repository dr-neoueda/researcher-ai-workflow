"""raw の hook（SessionStart・PostToolUse・Stop）のテスト。

Claude Code と Codex CLI の両方の入力の形（標準入力の JSON）で呼び、Claude・Codex に届く形
（SessionStart は標準出力、PostToolUse と Stop は標準エラー＋終了コード 2）で返すかを確かめる。
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parent.parent
REPO = HOOKS.parent.parent
CODEX_HOOKS = REPO / "codex-plugin" / "hooks"


def run_hook(name: str, payload: dict, cwd: Path, project_dir: Path | None = None) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_")}
    if project_dir is not None:
        env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    return subprocess.run(
        ["bash", str(HOOKS / name)], input=json.dumps(payload), capture_output=True, text=True, cwd=cwd, env=env,
        timeout=30,
    )


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / "office" / "secretary" / "notes").mkdir(parents=True)
    (root / "office" / "secretary" / "todos").mkdir(parents=True)
    (root / "office" / "computation" / "playbooks").mkdir(parents=True)
    (root / "office" / "computation" / "playbooks" / "gaussian.md").write_text("# gaussian\n", encoding="utf-8")
    (root / "work" / "analyses").mkdir(parents=True)
    return root


def _today() -> str:
    return dt.date.today().isoformat()


# ---------- SessionStart ----------

def test_session_start_finds_office_from_the_payload_cwd(project: Path, tmp_path: Path) -> None:
    res = run_hook("load-playbooks.sh", {"hook_event_name": "SessionStart", "cwd": str(project)}, cwd=tmp_path)
    assert res.returncode == 0
    assert "office/ 検出済" in res.stdout
    assert "gaussian.md" in res.stdout


def test_session_start_walks_up_from_a_subfolder(project: Path) -> None:
    sub = project / "work" / "analyses"
    res = run_hook("load-playbooks.sh", {"hook_event_name": "SessionStart", "cwd": str(sub)}, cwd=sub)
    assert res.returncode == 0 and "office/ 検出済" in res.stdout


def test_session_start_prefers_claude_project_dir(project: Path, tmp_path: Path) -> None:
    res = run_hook("load-playbooks.sh", {"cwd": str(tmp_path)}, cwd=tmp_path, project_dir=project)
    assert "office/ 検出済" in res.stdout


def test_session_start_is_silent_without_office(tmp_path: Path) -> None:
    res = run_hook("load-playbooks.sh", {"cwd": str(tmp_path)}, cwd=tmp_path)
    assert res.returncode == 0 and res.stdout == ""


# ---------- PostToolUse（置き場所の警告）----------

def test_claude_write_into_old_layout_reaches_the_model(project: Path) -> None:
    payload = {
        "hook_event_name": "PostToolUse", "cwd": str(project), "tool_name": "Write",
        "tool_input": {"file_path": str(project / "office" / "research" / "papers" / "wang-2024.md")},
    }
    res = run_hook("output-location-check.sh", payload, cwd=project)
    assert res.returncode == 2
    assert "work/papers/wang-2024.md" in res.stderr


def test_codex_apply_patch_into_old_layout_reaches_the_model(project: Path) -> None:
    patch = "*** Begin Patch\n*** Add File: office/analysis/figures/fig1.png\n+x\n*** End Patch\n"
    payload = {
        "hook_event_name": "PostToolUse", "cwd": str(project), "tool_name": "apply_patch",
        "tool_input": {"command": patch},
    }
    res = run_hook("output-location-check.sh", payload, cwd=project)
    assert res.returncode == 2
    assert "work/figures/fig1.png" in res.stderr


def test_codex_patch_that_moves_a_file_into_old_layout(project: Path) -> None:
    patch = "*** Begin Patch\n*** Update File: work/a.md\n*** Move to: office/writing/manuscripts/a.md\n*** End Patch\n"
    payload = {"cwd": str(project), "tool_name": "apply_patch", "tool_input": {"input": patch}}
    res = run_hook("output-location-check.sh", payload, cwd=project)
    assert res.returncode == 2 and "work/manuscripts/a.md" in res.stderr


def test_writes_to_the_right_place_are_silent(project: Path) -> None:
    payload = {
        "cwd": str(project), "tool_name": "Write",
        "tool_input": {"file_path": str(project / "work" / "papers" / "md" / "wang-2024.md")},
    }
    res = run_hook("output-location-check.sh", payload, cwd=project)
    assert res.returncode == 0 and res.stdout == "" and res.stderr == ""


def test_other_tools_are_ignored(project: Path) -> None:
    payload = {"cwd": str(project), "tool_name": "Bash", "tool_input": {"command": "ls office/research/papers"}}
    res = run_hook("output-location-check.sh", payload, cwd=project)
    assert res.returncode == 0 and res.stderr == ""


# ---------- Stop（学びの催促）----------

def test_stop_asks_for_learnings_when_today_had_activity(project: Path) -> None:
    notes = project / "office" / "secretary" / "notes"
    (notes / f"{_today()}-decisions.md").write_text("- 決めた\n", encoding="utf-8")
    res = run_hook("learnings-reminder.sh", {"hook_event_name": "Stop", "cwd": str(project)}, cwd=project)
    assert res.returncode == 2
    assert f"{_today()}-learnings.md" in res.stderr


def test_stop_does_not_loop_once_it_has_asked(project: Path) -> None:
    notes = project / "office" / "secretary" / "notes"
    (notes / f"{_today()}-decisions.md").write_text("- 決めた\n", encoding="utf-8")
    payload = {"hook_event_name": "Stop", "cwd": str(project), "stop_hook_active": True}
    res = run_hook("learnings-reminder.sh", payload, cwd=project)
    assert res.returncode == 0 and res.stderr == ""


def test_stop_is_quiet_when_learnings_exist(project: Path) -> None:
    notes = project / "office" / "secretary" / "notes"
    (notes / f"{_today()}-decisions.md").write_text("- 決めた\n", encoding="utf-8")
    (notes / f"{_today()}-learnings.md").write_text("- 学んだ\n", encoding="utf-8")
    res = run_hook("learnings-reminder.sh", {"cwd": str(project)}, cwd=project)
    assert res.returncode == 0 and res.stderr == ""


def test_stop_is_quiet_without_activity(project: Path) -> None:
    yesterday = (dt.datetime.now() - dt.timedelta(days=1)).timestamp()
    playbook = project / "office" / "computation" / "playbooks" / "gaussian.md"
    os.utime(playbook, (yesterday, yesterday))  # 準備で作った Playbook を「今日の更新」に数えない
    res = run_hook("learnings-reminder.sh", {"cwd": str(project)}, cwd=project)
    assert res.returncode == 0 and res.stderr == ""


# ---------- 配線（hooks.json）と Codex 版 ----------

@pytest.mark.parametrize("root", [HOOKS, CODEX_HOOKS])
def test_hooks_json_wires_the_three_events(root: Path) -> None:
    data = json.loads((root / "hooks.json").read_text(encoding="utf-8"))
    events = data["hooks"]
    assert set(events) == {"SessionStart", "PostToolUse", "Stop"}
    matcher = events["PostToolUse"][0]["matcher"]
    assert {"Edit", "Write", "MultiEdit", "apply_patch"} <= set(matcher.split("|"))
    for groups in events.values():
        for group in groups:
            for hook in group["hooks"]:
                assert "${CLAUDE_PLUGIN_ROOT}/hooks/" in hook["command"]
                script = hook["command"].split("${CLAUDE_PLUGIN_ROOT}/hooks/")[1].split('"')[0]
                assert (root / script).is_file(), script


@pytest.mark.parametrize("name", ["hooks.json", "load-playbooks.sh", "output-location-check.sh", "learnings-reminder.sh"])
def test_codex_hooks_are_byte_identical(name: str) -> None:
    assert (CODEX_HOOKS / name).read_bytes() == (HOOKS / name).read_bytes()


def _path_without_python(tmp_path: Path) -> str:
    """bash と基本のコマンドだけを置いた PATH（python3 / python が見えない環境）。"""
    import shutil

    bindir = tmp_path / "bin-no-python"
    bindir.mkdir()
    for tool in ("bash", "cat", "date", "dirname", "basename", "find", "head", "ls", "sort"):
        found = shutil.which(tool)
        assert found, tool
        (bindir / tool).symlink_to(found)
    return str(bindir)


@pytest.mark.parametrize("payload_extra,expected", [({"stop_hook_active": True}, 0), ({}, 2)])
def test_stop_works_without_python(project: Path, tmp_path: Path, payload_extra: dict, expected: int) -> None:
    notes = project / "office" / "secretary" / "notes"
    (notes / f"{_today()}-decisions.md").write_text("- 決めた\n", encoding="utf-8")
    env = {"PATH": _path_without_python(tmp_path), "CLAUDE_PROJECT_DIR": str(project), "LANG": "en_US.UTF-8"}
    res = subprocess.run(
        [env["PATH"] + "/bash", str(HOOKS / "learnings-reminder.sh")],
        input=json.dumps({"hook_event_name": "Stop", **payload_extra}), capture_output=True, text=True,
        cwd=project, env=env, timeout=30,
    )
    assert res.returncode == expected, res.stderr
