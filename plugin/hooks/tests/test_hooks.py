"""raw の hook（SessionStart・PostToolUse・Stop）のテスト。

Claude Code と Codex CLI の両方の入力の形（標準入力の JSON）で呼び、Claude・Codex に届く形
（SessionStart は標準出力、PostToolUse と Stop は標準エラー＋終了コード 2）で返すかを確かめる。
"""
from __future__ import annotations

import contextlib
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parent.parent
REPO = HOOKS.parent.parent
CODEX_HOOKS = REPO / "codex-plugin" / "hooks"


def run_hook(name: str, payload: dict, cwd: Path, project_dir: Path | None = None,
             extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CLAUDE_", "CODEX_SANDBOX"))}
    env.update(extra_env or {})
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


def test_codex_patch_that_moves_a_file_out_of_old_layout_is_silent(project: Path) -> None:
    patch = "*** Begin Patch\n*** Update File: office/research/papers/a.md\n*** Move to: work/papers/a.md\n*** End Patch\n"
    payload = {"cwd": str(project), "tool_name": "apply_patch", "tool_input": {"input": patch}}
    res = run_hook("output-location-check.sh", payload, cwd=project)
    assert res.returncode == 0 and res.stderr == ""


def test_only_the_moved_file_in_a_patch_drops_its_old_path(project: Path) -> None:
    patch = (
        "*** Begin Patch\n*** Update File: office/research/papers/a.md\n@@\n-x\n+y\n"
        "*** Update File: office/research/papers/b.md\n*** Move to: work/papers/b.md\n*** End Patch\n"
    )
    payload = {"cwd": str(project), "tool_name": "apply_patch", "tool_input": {"input": patch}}
    res = run_hook("output-location-check.sh", payload, cwd=project)
    assert res.returncode == 2 and "work/papers/a.md" in res.stderr and "b.md" not in res.stderr


def test_a_payload_that_starts_with_a_bom_is_read(project: Path) -> None:
    payload = {"cwd": str(project), "tool_name": "Write", "tool_input": {"file_path": "office/research/papers/a.md"}}
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_")}
    res = subprocess.run(
        ["bash", str(HOOKS / "output-location-check.sh")], input="﻿" + json.dumps(payload),
        capture_output=True, text=True, cwd=project, env=env, timeout=30,
    )
    assert res.returncode == 2 and "work/papers/a.md" in res.stderr


def test_a_path_with_a_nul_is_skipped_without_a_traceback(project: Path) -> None:
    patch = "*** Begin Patch\n*** Add File: a\u0000b\n*** Add File: office/research/papers/c.md\n*** End Patch\n"
    payload = {"cwd": str(project), "tool_name": "apply_patch", "tool_input": {"input": patch}}
    res = run_hook("output-location-check.sh", payload, cwd=project)
    assert res.returncode == 2 and "work/papers/c.md" in res.stderr and "Traceback" not in res.stderr


def test_a_move_line_after_an_added_file_does_not_hide_it(project: Path) -> None:
    patch = "*** Begin Patch\n*** Add File: office/research/papers/a.md\n+x\n*** Move to: work/papers/z.md\n*** End Patch\n"
    payload = {"cwd": str(project), "tool_name": "apply_patch", "tool_input": {"input": patch}}
    res = run_hook("output-location-check.sh", payload, cwd=project)
    assert res.returncode == 2 and "work/papers/a.md" in res.stderr


PYTHONS = sorted({sys.executable, *(p for p in ("/usr/bin/python3",) if Path(p).exists())})


@pytest.mark.parametrize("python", PYTHONS)
def test_a_symlink_loop_in_a_path_is_skipped(project: Path, python: str) -> None:
    (project / "loop").symlink_to("loop")  # Python 3.12 以前の resolve() は RuntimeError を上げる
    patch = "*** Begin Patch\n*** Add File: loop/x.md\n*** Add File: office/research/papers/c.md\n*** End Patch\n"
    payload = {"cwd": str(project), "tool_name": "apply_patch", "tool_input": {"input": patch}}
    res = subprocess.run(
        [python, str(HOOKS / "_hookio.py"), "paths"], input=json.dumps(payload),
        capture_output=True, text=True, cwd=project, timeout=30,
    )
    assert res.returncode == 0, res.stderr
    assert "office/research/papers/c.md" in res.stdout.splitlines()  # 3.13 以降はループの先も相対パスで出る


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
def test_hooks_json_wires_the_events(root: Path) -> None:
    data = json.loads((root / "hooks.json").read_text(encoding="utf-8"))
    events = data["hooks"]
    assert set(events) == {"SessionStart", "UserPromptSubmit", "PostToolUse", "Stop"}
    matcher = events["PostToolUse"][0]["matcher"]
    assert {"Edit", "Write", "MultiEdit", "apply_patch"} <= set(matcher.split("|"))
    for groups in events.values():
        for group in groups:
            for hook in group["hooks"]:
                assert "${CLAUDE_PLUGIN_ROOT}/hooks/" in hook["command"]
                script = hook["command"].split("${CLAUDE_PLUGIN_ROOT}/hooks/")[1].split('"')[0]
                assert (root / script).is_file(), script


@pytest.mark.parametrize("name", [
    "hooks.json", "load-playbooks.sh", "output-location-check.sh", "learnings-reminder.sh", "jobs-reminder.sh",
    "jobs-stop-check.sh", "jobwatch.py", "_hookio.py", "_common.sh",
])
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


# ---------- レビューの指摘（2026-11-10）----------

def test_stop_without_python_reads_stop_hook_active_with_spaces(project: Path, tmp_path: Path) -> None:
    notes = project / "office" / "secretary" / "notes"
    (notes / f"{_today()}-decisions.md").write_text("- 決めた\n", encoding="utf-8")
    env = {"PATH": _path_without_python(tmp_path), "CLAUDE_PROJECT_DIR": str(project), "LANG": "en_US.UTF-8"}
    res = subprocess.run(
        [env["PATH"] + "/bash", str(HOOKS / "learnings-reminder.sh")],
        input='{"cwd": "x",\n "stop_hook_active" : true}', capture_output=True, text=True, cwd=project, env=env, timeout=30,
    )
    assert res.returncode == 0, res.stderr


def test_deleting_a_misplaced_file_is_not_a_violation(project: Path) -> None:
    patch = "*** Begin Patch\n*** Delete File: office/research/papers/a.md\n*** End Patch\n"
    payload = {"cwd": str(project), "tool_name": "apply_patch", "tool_input": {"command": patch}}
    res = run_hook("output-location-check.sh", payload, cwd=project)
    assert res.returncode == 0 and res.stderr == ""


def test_patch_lines_inside_written_content_are_ignored(project: Path) -> None:
    payload = {
        "cwd": str(project), "tool_name": "Write",
        "tool_input": {
            "file_path": str(project / "work" / "notes.md"),
            "content": "例:\n*** Add File: office/research/papers/x.md\n",
        },
    }
    res = run_hook("output-location-check.sh", payload, cwd=project)
    assert res.returncode == 0 and res.stderr == ""


def test_quoted_patch_paths_are_unquoted(project: Path) -> None:
    patch = '*** Begin Patch\n*** Add File: "office/research/papers/a b.md"\n*** End Patch\n'
    payload = {"cwd": str(project), "tool_name": "apply_patch", "tool_input": {"command": patch}}
    res = run_hook("output-location-check.sh", payload, cwd=project)
    assert res.returncode == 2 and "work/papers/a b.md" in res.stderr


def test_a_stray_office_folder_above_is_not_the_project(tmp_path: Path) -> None:
    (tmp_path / "q" / "office").mkdir(parents=True)  # raw の office/ ではない（secretary/ が無い）
    inner = tmp_path / "q" / "office" / "x" / "proj"
    inner.mkdir(parents=True)
    res = run_hook("load-playbooks.sh", {"cwd": str(inner)}, cwd=inner)
    assert res.returncode == 0 and res.stdout == ""


def test_japanese_paths_survive_a_cp932_console(tmp_path: Path) -> None:
    root = tmp_path / "研究 プロジェクト"
    (root / "office" / "secretary" / "notes").mkdir(parents=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_")}
    env["PYTHONIOENCODING"] = "cp932"  # 日本語の Windows の既定に近い状態
    payload = json.dumps({"cwd": str(root)}, ensure_ascii=False).encode("utf-8")
    res = subprocess.run(
        ["bash", str(HOOKS / "load-playbooks.sh")], input=payload, capture_output=True, cwd=root, env=env, timeout=30
    )
    assert res.returncode == 0
    assert "研究 プロジェクト" in res.stdout.decode("utf-8")


# ---------- 計算の見張り（jobwatch）と hook ----------

def _finished_job(project: Path) -> str:
    import sys as _sys
    _sys.path.insert(0, str(HOOKS))
    import jobwatch as jw

    proc = subprocess.Popen([_sys.executable, "-c", "pass"])
    proc.wait()
    job = jw.register(project, name="ts1-opt", kind="local", job_id=str(proc.pid), tool="gaussian", log="x.log")
    jw.watch_once(project, notify=None)
    return job.key


def test_session_start_shows_the_watch_tool_and_pending_jobs(project: Path) -> None:
    key = _finished_job(project)
    res = run_hook("load-playbooks.sh", {"cwd": str(project)}, cwd=project)
    assert "jobwatch.py" in res.stdout
    assert key in res.stdout and "判定していない" in res.stdout


def test_prompt_submit_reminds_of_finished_jobs(project: Path) -> None:
    key = _finished_job(project)
    res = run_hook("jobs-reminder.sh", {"hook_event_name": "UserPromptSubmit", "cwd": str(project), "prompt": "続けて"}, cwd=project)
    assert res.returncode == 0 and key in res.stdout


def test_prompt_submit_is_silent_without_jobs(project: Path) -> None:
    res = run_hook("jobs-reminder.sh", {"cwd": str(project), "prompt": "やあ"}, cwd=project)
    assert res.returncode == 0 and res.stdout == ""


def test_stop_holds_until_finished_jobs_are_judged(project: Path) -> None:
    key = _finished_job(project)
    res = run_hook("jobs-stop-check.sh", {"hook_event_name": "Stop", "cwd": str(project)}, cwd=project)
    assert res.returncode == 2 and key in res.stderr


def test_stop_check_does_not_loop(project: Path) -> None:
    _finished_job(project)
    res = run_hook("jobs-stop-check.sh", {"cwd": str(project), "stop_hook_active": True}, cwd=project)
    assert res.returncode == 0 and res.stderr == ""


def test_hooks_json_wires_the_job_hooks() -> None:
    data = json.loads((HOOKS / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    assert "jobs-reminder.sh" in json.dumps(data["UserPromptSubmit"])
    assert "jobs-stop-check.sh" in json.dumps(data["Stop"])


# ---------- hook が見張りを起動する（Codex の sandbox の中では見張りを起動できないため。2026-11-11）----------

def _live_job_and_fake_tmux(project: Path, tmp_path: Path) -> tuple[subprocess.Popen, dict[str, str]]:
    """走っているジョブを 1 本登録し、渡されたコマンドを切り離して走らせる偽の tmux を PATH に置く。"""
    import sys as _sys
    _sys.path.insert(0, str(HOOKS))
    import jobwatch as jw

    live = subprocess.Popen([_sys.executable, "-c", "import time; time.sleep(60)"])
    jw.register(project, name="ts2-opt", kind="local", job_id=str(live.pid), tool="gaussian", log="x.log")
    bindir = tmp_path / "fakebin"
    bindir.mkdir()
    record = tmp_path / "tmux-args.txt"
    tmux = bindir / "tmux"
    pidfile = tmp_path / "fake-tmux.pid"
    tmux.write_text(f'#!/bin/bash\nprintf "%s\\n" "$@" > "{record}"\nnohup bash -c "$5" >/dev/null 2>&1 &\n'
                    f'echo $! > "{pidfile}"\nexit 0\n', encoding="utf-8")
    tmux.chmod(0o755)
    return live, {"PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}"}


def _stop_watcher(project: Path, live: subprocess.Popen, tmp_path: Path) -> None:
    """見張り（心拍の pid）と偽の tmux が切り離したプロセスを止める（テストが途中で落ちても残さない）。"""
    live.kill()
    live.wait()
    pids = []
    beat = project / "office" / "computation" / "watch" / "_watcher.json"
    with contextlib.suppress(OSError, ValueError, KeyError):
        pids.append(int(json.loads(beat.read_text(encoding="utf-8"))["pid"]))
    with contextlib.suppress(OSError, ValueError):
        pids.append(int((tmp_path / "fake-tmux.pid").read_text(encoding="utf-8")))
    for pid in pids:
        with contextlib.suppress(OSError):
            os.kill(pid, 15)


def _heartbeat_written(project: Path) -> bool:
    return (project / "office" / "computation" / "watch" / "_watcher.json").is_file()


def test_prompt_submit_starts_the_watcher_for_unwatched_jobs(project: Path, tmp_path: Path) -> None:
    live, env = _live_job_and_fake_tmux(project, tmp_path)
    try:
        res = run_hook("jobs-reminder.sh", {"cwd": str(project), "prompt": "続けて"}, cwd=project, extra_env=env)
        assert res.returncode == 0 and _heartbeat_written(project)
        assert "見張りの無いジョブ" not in res.stdout
        assert (tmp_path / "tmux-args.txt").read_text(encoding="utf-8").startswith("new-session")
    finally:
        _stop_watcher(project, live, tmp_path)


def test_stop_starts_the_watcher_instead_of_holding(project: Path, tmp_path: Path) -> None:
    live, env = _live_job_and_fake_tmux(project, tmp_path)
    try:
        res = run_hook("jobs-stop-check.sh", {"cwd": str(project)}, cwd=project, extra_env=env)
        assert res.returncode == 0 and res.stderr == "" and _heartbeat_written(project)
    finally:
        _stop_watcher(project, live, tmp_path)


def test_session_start_starts_the_watcher_for_unwatched_jobs(project: Path, tmp_path: Path) -> None:
    live, env = _live_job_and_fake_tmux(project, tmp_path)
    try:
        res = run_hook("load-playbooks.sh", {"cwd": str(project)}, cwd=project, extra_env=env)
        assert res.returncode == 0 and _heartbeat_written(project)
        assert "見張りの無いジョブ" not in res.stdout
    finally:
        _stop_watcher(project, live, tmp_path)
