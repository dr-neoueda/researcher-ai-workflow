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
import time
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


def test_quotes_in_a_patch_path_are_part_of_the_name(project: Path) -> None:
    """Codex #70: Codex 0.167 の apply_patch は引用符も名前の一部として書く（実機の apply で確認）。
    「"office/…"」は根に「"office」というフォルダを作るので office/ の置き違いではない。"""
    patch = '*** Begin Patch\n*** Add File: "office/research/papers/a b.md"\n*** End Patch\n'
    payload = {"cwd": str(project), "tool_name": "apply_patch", "tool_input": {"command": patch}}
    res = run_hook("output-location-check.sh", payload, cwd=project)
    assert res.returncode == 0 and res.stderr == ""


def test_a_trailing_apostrophe_stays_in_the_reported_name(project: Path) -> None:
    patch = "*** Begin Patch\n*** Add File: office/research/papers/a.md'\n+x\n*** End Patch\n"
    payload = {"cwd": str(project), "tool_name": "apply_patch", "tool_input": {"command": patch}}
    res = run_hook("output-location-check.sh", payload, cwd=project)
    assert res.returncode == 2 and "office/research/papers/a.md' → work/papers/a.md'" in res.stderr


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


# ---------- v2.4.1: 真っさらな Mac の動作テストで見つかったこと ----------

def test_a_misplaced_file_written_by_a_shell_command_is_caught(project: Path) -> None:
    """F7: Claude が Bash（mkdir && printf > …）で書くと、Write の道具を通らないので警告が出なかった。"""
    target = project / "office" / "research" / "papers" / "note.md"
    target.parent.mkdir(parents=True)
    target.write_text("テスト\n", encoding="utf-8")
    payload = {"cwd": str(project), "tool_name": "Bash",
               "tool_input": {"command": "mkdir -p office/research/papers && printf 'テスト' > office/research/papers/note.md"}}
    res = run_hook("output-location-check.sh", payload, cwd=project)
    assert res.returncode == 2 and "work/papers/note.md" in res.stderr


def test_an_old_misplaced_file_does_not_warn_on_every_shell_command(project: Path) -> None:
    """前からある置き違いでは、シェルの道具のたびに警告しない（2 分の窓を過ぎたら黙る）。
    ctime はテストで過去にできないので、時計を進めて確かめる。"""
    sys.path.insert(0, str(HOOKS))
    import _hookio
    target = project / "office" / "research" / "papers" / "old.md"
    target.parent.mkdir(parents=True)
    target.write_text("前から\n", encoding="utf-8")
    later = time.time() + 2 * _hookio.RECENT_SECONDS
    assert _hookio.recent_office_files(project, now=later, places=["office/research/papers"]) == []
    assert _hookio.recent_office_files(project, places=["office/research/papers"]) == ["office/research/papers/old.md"]


def test_fresh_operations_files_written_by_a_shell_command_are_fine(project: Path) -> None:
    (project / "office" / "secretary" / "notes" / "2026-11-16-decisions.md").write_text("決定\n", encoding="utf-8")
    payload = {"cwd": str(project), "tool_name": "Bash", "tool_input": {"command": "echo 決定 >> …"}}
    res = run_hook("output-location-check.sh", payload, cwd=project)
    assert res.returncode == 0 and res.stderr == ""


def test_the_location_check_runs_after_shell_commands() -> None:
    hooks = json.loads((HOOKS / "hooks.json").read_text(encoding="utf-8"))
    matchers = [h.get("matcher", "") for h in hooks["hooks"]["PostToolUse"]]
    assert any("Bash" in m.split("|") for m in matchers)


LEGACY_TO_WORK = [
    ("office/research/papers/a.md", "work/papers/a.md"),
    ("office/research/topics/a.md", "work/topics/a.md"),
    ("office/research/reports/a.md", "work/reports/a.md"),
    ("office/writing/manuscripts/a.md", "work/manuscripts/a.md"),
    ("office/analysis/results/a.csv", "work/analyses/a.csv"),
    ("office/analysis/figures/a.png", "work/figures/a.png"),
    ("office/analysis/notebooks/a.ipynb", "work/notebooks/a.ipynb"),
    ("office/presentation/slides/a.pptx", "work/presentations/slides/a.pptx"),
    ("office/presentation/figures/a.png", "work/figures/a.png"),
    ("office/engineering/scripts/a.py", "work/scripts/a.py"),
    ("office/engineering/tools/a.py", "work/tools/a.py"),
]


@pytest.mark.parametrize("written,suggested", LEGACY_TO_WORK)
def test_every_old_place_suggests_its_work_place(project: Path, written: str, suggested: str) -> None:
    payload = {"cwd": str(project), "tool_name": "Write", "tool_input": {"file_path": str(project / written)}}
    res = run_hook("output-location-check.sh", payload, cwd=project)
    assert res.returncode == 2 and f"{written} → {suggested}" in res.stderr


@pytest.mark.parametrize("written,suggested", LEGACY_TO_WORK)
def test_every_old_place_is_seen_after_a_shell_command(project: Path, written: str, suggested: str) -> None:
    (project / written).parent.mkdir(parents=True, exist_ok=True)
    (project / written).write_text("x\n", encoding="utf-8")
    payload = {"cwd": str(project), "tool_name": "Bash", "tool_input": {"command": "…"}}
    res = run_hook("output-location-check.sh", payload, cwd=project)
    assert res.returncode == 2 and suggested in res.stderr


def test_an_old_file_moved_into_an_old_place_by_a_shell_command_is_caught(project: Path) -> None:
    """mv・cp -p は更新時刻を古いまま保つ。置いた時刻（ctime）でも拾う。"""
    src = project / "work" / "old.md"
    src.write_text("前から\n", encoding="utf-8")
    old = time.time() - 3600
    os.utime(src, (old, old))
    dest = project / "office" / "research" / "papers" / "old.md"
    dest.parent.mkdir(parents=True)
    src.rename(dest)                                         # mv: 更新時刻は 1 時間前のまま
    payload = {"cwd": str(project), "tool_name": "Bash", "tool_input": {"command": "mv work/old.md office/research/papers/"}}
    res = run_hook("output-location-check.sh", payload, cwd=project)
    assert res.returncode == 2 and "work/papers/old.md" in res.stderr


def test_only_the_old_places_are_scanned_after_a_shell_command(project: Path) -> None:
    scanned: list[str] = []
    sys.path.insert(0, str(HOOKS))
    import _hookio
    (project / "office" / "computation" / "jobs").mkdir(parents=True, exist_ok=True)
    (project / "office" / "computation" / "jobs" / "x.md").write_text("記録\n", encoding="utf-8")
    (project / "office" / "research" / "papers").mkdir(parents=True)
    (project / "office" / "research" / "papers" / "y.md").write_text("置き違い\n", encoding="utf-8")
    found = _hookio.recent_office_files(project, places=["office/research/papers"])
    assert found == ["office/research/papers/y.md"]


def test_an_empty_list_of_old_places_scans_nothing(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sys.path.insert(0, str(HOOKS))
    import _hookio
    (project / "office" / "computation" / "jobs").mkdir(parents=True, exist_ok=True)
    (project / "office" / "computation" / "jobs" / "x.md").write_text("記録\n", encoding="utf-8")
    monkeypatch.setenv("RAW_LEGACY_PLACES", "  \n")
    data = {"cwd": str(project), "tool_name": "Bash", "tool_input": {"command": "ls"}}
    assert _hookio.edited_paths(data, project) == []


# ---------- Codex の事後レビュー（2026-11-17）----------

def _crlf_python(tmp_path: Path) -> str:
    """Windows の Python のように標準出力の改行を CRLF にする「python3」を置いた PATH。"""
    bindir = tmp_path / "bin-crlf"
    bindir.mkdir()
    wrapper = bindir / "python3"
    wrapper.write_text(
        f"#!{sys.executable}\n"
        "import os, runpy, sys\n"
        "if len(sys.argv) > 1 and sys.argv[1] == '-c':\n"
        "    os.execv(sys.executable, [sys.executable] + sys.argv[1:])\n"
        "sys.stdout.reconfigure(newline='\\r\\n')\n"
        "sys.argv = sys.argv[1:]\n"
        "runpy.run_path(sys.argv[0], run_name='__main__')\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    return f"{bindir}{os.pathsep}{os.environ['PATH']}"


def test_a_crlf_python_still_finds_the_project(project: Path, tmp_path: Path) -> None:
    """Codex #70 P1: Windows の Python の標準出力の CRLF が project のパスに残り（bash の $(…) は LF だけ外す）、
    記録の読み込みと Stop の催促が黙って抜けていた。"""
    (project / "office" / "secretary" / "notes" / f"{_today()}-decisions.md").write_text("- 決めた\n", encoding="utf-8")
    env = {"PATH": _crlf_python(tmp_path)}
    stop = run_hook("learnings-reminder.sh", {"cwd": str(project)}, cwd=project, extra_env=env)
    assert stop.returncode == 2 and "learnings" in stop.stderr
    start = run_hook("load-playbooks.sh", {"cwd": str(project)}, cwd=project, extra_env=env)
    assert "決めた" in start.stdout


def test_a_crlf_python_reports_paths_without_a_carriage_return(project: Path, tmp_path: Path) -> None:
    target = project / "office" / "research" / "papers" / "a.md"
    payload = {"cwd": str(project), "tool_name": "Write", "tool_input": {"file_path": str(target)}}
    res = run_hook("output-location-check.sh", payload, cwd=project, extra_env={"PATH": _crlf_python(tmp_path)})
    assert res.returncode == 2 and "office/research/papers/a.md → work/papers/a.md\n" in res.stderr
    assert "\r" not in res.stderr


def test_a_file_added_then_deleted_in_one_patch_is_not_reported(project: Path) -> None:
    patch = ("*** Begin Patch\n*** Add File: office/research/papers/t.md\n+x\n"
             "*** Delete File: office/research/papers/t.md\n*** End Patch\n")
    payload = {"cwd": str(project), "tool_name": "apply_patch", "tool_input": {"command": patch}}
    res = run_hook("output-location-check.sh", payload, cwd=project)
    assert res.returncode == 0 and res.stderr == ""


def test_a_file_deleted_then_added_again_in_one_patch_is_reported(project: Path) -> None:
    patch = ("*** Begin Patch\n*** Delete File: office/research/papers/t.md\n"
             "*** Add File: office/research/papers/t.md\n+x\n*** End Patch\n")
    payload = {"cwd": str(project), "tool_name": "apply_patch", "tool_input": {"command": patch}}
    res = run_hook("output-location-check.sh", payload, cwd=project)
    assert res.returncode == 2 and "work/papers/t.md" in res.stderr


@pytest.mark.parametrize("hook,check", [
    ("learnings-reminder.sh", lambda res: res.returncode == 2),
    ("load-playbooks.sh", lambda res: "office/ 検出済" in res.stdout),
])
def test_without_python_a_subfolder_still_finds_the_project(project: Path, tmp_path: Path, hook: str, check) -> None:
    """Codex #70: python が無く CLAUDE_PROJECT_DIR も無いとき（Codex）、<project>/work で起動すると
    いまの場所しか見ず、SessionStart と Stop が黙っていた。"""
    (project / "office" / "secretary" / "notes" / f"{_today()}-decisions.md").write_text("- 決めた\n", encoding="utf-8")
    sub = project / "work"
    env = {"PATH": _path_without_python(tmp_path), "LANG": "en_US.UTF-8"}
    res = subprocess.run([env["PATH"] + "/bash", str(HOOKS / hook)], input=json.dumps({"cwd": str(sub)}),
                         capture_output=True, text=True, cwd=sub, env=env, timeout=30)
    assert check(res), (res.returncode, res.stdout, res.stderr)


def test_an_old_place_linked_to_its_work_place_is_not_a_violation(project: Path) -> None:
    """Codex #73: office/research/papers が work/papers へのリンクなら、正しい場所に書いたことになる。"""
    (project / "work" / "papers").mkdir(parents=True)
    (project / "office" / "research").mkdir(parents=True)
    (project / "office" / "research" / "papers").symlink_to(project / "work" / "papers", target_is_directory=True)
    (project / "work" / "papers" / "new.md").write_text("x\n", encoding="utf-8")
    payload = {"cwd": str(project), "tool_name": "Bash", "tool_input": {"command": "true"}}
    res = run_hook("output-location-check.sh", payload, cwd=project)
    assert res.returncode == 0 and res.stderr == ""


def test_a_file_dated_in_the_future_is_not_reported_forever(project: Path) -> None:
    """Codex #73: 時計の進んだ機械から更新時刻ごと写したファイルを、120 秒を過ぎても毎回拾っていた。"""
    sys.path.insert(0, str(HOOKS))
    import _hookio
    target = project / "office" / "research" / "papers" / "future.md"
    target.parent.mkdir(parents=True)
    target.write_text("x\n", encoding="utf-8")
    tomorrow = time.time() + 86400
    os.utime(target, (tomorrow, tomorrow))
    later = time.time() + 2 * _hookio.RECENT_SECONDS
    assert _hookio.recent_office_files(project, now=later, places=["office/research/papers"]) == []
    assert _hookio.recent_office_files(project, places=["office/research/papers"]) == ["office/research/papers/future.md"]


def test_a_file_name_with_a_newline_is_reported_whole(project: Path) -> None:
    target = project / "office" / "research" / "papers" / "a\nb.md"
    target.parent.mkdir(parents=True)
    target.write_text("x\n", encoding="utf-8")
    payload = {"cwd": str(project), "tool_name": "Bash", "tool_input": {"command": "true"}}
    res = run_hook("output-location-check.sh", payload, cwd=project)
    assert res.returncode == 2 and "office/research/papers/a\\nb.md → work/papers/a\\nb.md" in res.stderr


def test_a_job_submitted_while_stop_was_holding_still_gets_a_watcher(project: Path, tmp_path: Path) -> None:
    """Codex #71: Stop に引き戻された間（stop_hook_active）に投入したジョブには、次の Stop が起動まで
    たどり着かずに終わるので見張りが付かなかった（Codex の sandbox では hook だけが起動できる）。"""
    live, env = _live_job_and_fake_tmux(project, tmp_path)
    try:
        res = run_hook("jobs-stop-check.sh", {"cwd": str(project), "stop_hook_active": True}, cwd=project, extra_env=env)
        assert res.returncode == 0 and res.stderr == ""            # 引き戻しは繰り返さない
        assert _heartbeat_written(project)                          # が、見張りは起動する
    finally:
        _stop_watcher(project, live, tmp_path)


def test_a_file_a_little_in_the_future_on_a_shared_drive_is_still_caught(project: Path) -> None:
    """LOW: 時計の進んだ共有のドライブ（NFS・同期フォルダ）では、いま書いたファイルの時刻が数秒〜数分先になる。"""
    sys.path.insert(0, str(HOOKS))
    import _hookio
    target = project / "office" / "research" / "papers" / "nfs.md"
    target.parent.mkdir(parents=True)
    target.write_text("x\n", encoding="utf-8")
    behind = time.time() - 60                                   # 手元の時計がサーバより 60 秒遅い（mtime も ctime も 60 秒先に見える）
    assert _hookio.recent_office_files(project, now=behind, places=["office/research/papers"]) == ["office/research/papers/nfs.md"]


def test_a_backslash_in_a_name_is_shown_as_it_is(project: Path) -> None:
    target = project / "office" / "research" / "papers" / "a\\b.md"
    target.parent.mkdir(parents=True)
    target.write_text("x\n", encoding="utf-8")
    payload = {"cwd": str(project), "tool_name": "Bash", "tool_input": {"command": "true"}}
    res = run_hook("output-location-check.sh", payload, cwd=project)
    assert res.returncode == 2 and "office/research/papers/a\\b.md → work/papers/a\\b.md" in res.stderr
