"""jobwatch.py（計算ジョブの登録・見張り・完走の判定）のテスト。"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HOOKS))

import jobwatch as jw  # noqa: E402


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / "office" / "secretary" / "notes").mkdir(parents=True)
    (root / "office" / "computation").mkdir(parents=True)
    (root / "work" / "gaussian").mkdir(parents=True)
    return root


def _fake_bin(tmp_path: Path, name: str, script: str) -> Path:
    bindir = tmp_path / "fakebin"
    bindir.mkdir(exist_ok=True)
    path = bindir / name
    path.write_text("#!/bin/bash\n" + script, encoding="utf-8")
    path.chmod(0o755)
    return bindir


def _with_path(monkeypatch: pytest.MonkeyPatch, bindir: Path) -> None:
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")


# ---------- 登録 ----------

def test_register_writes_a_job_file_with_tool_markers(project: Path) -> None:
    job = jw.register(project, name="TS1 opt", kind="local", job_id="12345", tool="gaussian",
                      log="work/gaussian/ts1/ts1.log", expect_count=2)
    path = project / "office" / "computation" / "watch" / f"{job.key}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["done"] == ["Normal termination"] and data["fail"] == ["Error termination"]
    assert data["state"] == "running" and data["expect_count"] == 2 and data["kind"] == "local"


def test_register_keys_are_unique(project: Path) -> None:
    a = jw.register(project, name="ts1", kind="local", job_id="1", tool="orca", log="a.out")
    b = jw.register(project, name="ts1", kind="local", job_id="2", tool="orca", log="b.out")
    assert a.key != b.key


def test_register_needs_markers_for_an_unknown_tool(project: Path) -> None:
    with pytest.raises(ValueError, match="完走の印"):
        jw.register(project, name="x", kind="local", job_id="1", tool="mycode", log="x.log")
    job = jw.register(project, name="x", kind="local", job_id="1", tool="mycode", log="x.log", done=["DONE OK"])
    assert job.done == ("DONE OK",)


def test_register_rejects_a_folder_without_office(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="office"):
        jw.register(tmp_path, name="x", kind="local", job_id="1", tool="gaussian", log="x.log")


def test_register_rejects_an_unknown_kind(project: Path) -> None:
    with pytest.raises(ValueError, match="種類"):
        jw.register(project, name="x", kind="cloud", job_id="1", tool="gaussian", log="x.log")


def test_register_remembers_the_codex_thread(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEX_THREAD_ID", "thread-abc")
    job = jw.register(project, name="x", kind="local", job_id="1", tool="gaussian", log="x.log")
    assert job.codex_thread == "thread-abc"


# ---------- 走っているか ----------

def test_local_job_running_then_finished(project: Path) -> None:
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    job = jw.register(project, name="x", kind="local", job_id=str(proc.pid), tool="gaussian", log="x.log")
    assert jw.is_running(job) is True
    proc.kill()
    proc.wait()
    assert jw.is_running(job) is False


@pytest.mark.parametrize("output,code,expected", [
    ("Job Id: 77.pbs\n    job_state = R\n", 0, True),
    ("Job Id: 77.pbs\n    job_state = F\n", 0, False),
    ("qstat: Unknown Job Id 77.pbs\n", 153, False),
])
def test_pbs_job_state(project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, output: str, code: int, expected: bool) -> None:
    _with_path(monkeypatch, _fake_bin(tmp_path, "qstat", f"printf '%s' '{output}'\nexit {code}\n"))
    job = jw.register(project, name="x", kind="pbs", job_id="77.pbs", tool="gaussian", log="x.log")
    assert jw.is_running(job) is expected


@pytest.mark.parametrize("output,expected", [("  88 short ts1 user R 0:10 1 node1\n", True), ("", False)])
def test_slurm_job_state(project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, output: str, expected: bool) -> None:
    _with_path(monkeypatch, _fake_bin(tmp_path, "squeue", f"printf '%s' '{output}'\nexit 0\n"))
    job = jw.register(project, name="x", kind="slurm", job_id="88", tool="gaussian", log="x.log")
    assert jw.is_running(job) is expected


def test_unreachable_hpc_is_unknown_not_finished(project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _with_path(monkeypatch, _fake_bin(tmp_path, "ssh", "echo 'ssh: connect to host hpc: Operation timed out' >&2\nexit 255\n"))
    job = jw.register(project, name="x", kind="pbs", job_id="77.pbs", host="hpc", tool="gaussian", log="x.log")
    assert jw.is_running(job) is None


def test_remote_qstat_goes_through_ssh(project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    record = tmp_path / "ssh-args.txt"
    _with_path(monkeypatch, _fake_bin(tmp_path, "ssh", f"echo \"$@\" > '{record}'\necho '    job_state = R'\nexit 0\n"))
    job = jw.register(project, name="x", kind="pbs", job_id="77.pbs", host="hpc", tool="gaussian", log="x.log")
    assert jw.is_running(job) is True
    args = record.read_text(encoding="utf-8")
    assert "BatchMode=yes" in args and "hpc" in args and "qstat" in args and "77.pbs" in args


# ---------- 完走の判定 ----------

def _job_with_log(project: Path, text: str, **kw) -> jw.Job:
    log = project / "work" / "gaussian" / "ts1.log"
    log.write_text(text, encoding="utf-8")
    return jw.register(project, name="ts1", kind="local", job_id="1", tool="gaussian",
                       log="work/gaussian/ts1.log", **kw)


def test_judge_complete_when_all_steps_ended_normally(project: Path) -> None:
    job = _job_with_log(project, "...\n Normal termination of Gaussian 16\n...\n Normal termination of Gaussian 16\n", expect_count=2)
    verdict = jw.judge(project, job.key)
    assert verdict.status == "完走"
    assert any("L2" in e for e in verdict.evidence) and any("L4" in e for e in verdict.evidence)


def test_judge_incomplete_when_a_step_is_missing(project: Path) -> None:
    job = _job_with_log(project, " Normal termination of Gaussian 16\n", expect_count=2)
    assert jw.judge(project, job.key).status == "完走していない"


def test_judge_failed_when_the_program_says_so(project: Path) -> None:
    job = _job_with_log(project, " Normal termination of Gaussian 16\n Error termination via Lnk1e\n", expect_count=2)
    verdict = jw.judge(project, job.key)
    assert verdict.status == "異常終了" and any("Error termination" in e for e in verdict.evidence)


def test_judge_unknown_without_a_log(project: Path) -> None:
    job = jw.register(project, name="x", kind="local", job_id="1", tool="gaussian", log="work/none.log")
    assert jw.judge(project, job.key).status == "判定できない"


def test_judge_checks_expected_outputs(project: Path) -> None:
    job = _job_with_log(project, " Normal termination of Gaussian 16\n", outputs=["work/gaussian/ts1.fchk"])
    assert jw.judge(project, job.key).status == "完走していない"
    (project / "work" / "gaussian" / "ts1.fchk").write_text("data", encoding="utf-8")
    assert jw.judge(project, job.key).status == "完走"


def test_judge_records_the_verdict(project: Path) -> None:
    job = _job_with_log(project, " Normal termination of Gaussian 16\n")
    jw._save(project, jw.dataclasses.replace(job, state="finished"))  # 見張りが終わりを確かめた後
    jw.judge(project, job.key)
    (saved,) = jw.load_jobs(project)
    assert saved.state == "judged" and saved.verdict == "完走"


# ---------- 見張り ----------

def test_watch_once_marks_finished_and_tells_codex(project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    record = tmp_path / "codex-args.txt"
    bindir = _fake_bin(tmp_path, "codex", f"echo \"$@\" >> '{record}'\nexit 0\n")
    _with_path(monkeypatch, bindir)
    monkeypatch.setenv("CODEX_THREAD_ID", "thread-abc")
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait()
    job = jw.register(project, name="ts1", kind="local", job_id=str(proc.pid), tool="gaussian", log="x.log")
    notices: list[str] = []
    finished = jw.watch_once(project, notify=notices.append)
    assert finished == [job.key]
    (saved,) = jw.load_jobs(project)
    assert saved.state == "finished" and saved.finished_at
    assert notices and "ts1" in notices[0]
    args = record.read_text(encoding="utf-8")
    assert "queue" in args and "--thread thread-abc" in args and "ts1" in args


def test_watch_once_leaves_unknown_jobs_running(project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _with_path(monkeypatch, _fake_bin(tmp_path, "ssh", "exit 255\n"))
    jw.register(project, name="x", kind="pbs", job_id="77", host="hpc", tool="gaussian", log="x.log")
    assert jw.watch_once(project, notify=lambda _m: None) == []
    (saved,) = jw.load_jobs(project)
    assert saved.state == "running" and (saved.last_check or "").startswith("不明")


def test_watch_writes_a_heartbeat_and_stops_when_nothing_runs(project: Path) -> None:
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait()
    jw.register(project, name="x", kind="local", job_id=str(proc.pid), tool="gaussian", log="x.log")
    beat_file = project / "office" / "computation" / "watch" / "_watcher.json"
    beats: list[dict] = []
    loops = jw.watch(project, interval=0.05, notify=lambda _m: beats.append(json.loads(beat_file.read_text())), max_loops=20)
    assert loops < 20
    assert beats and beats[0]["pid"] == os.getpid()  # 見張りの最中は心拍がある
    assert not beat_file.exists()  # 終わったら消える


def test_wait_returns_when_the_job_ends(project: Path) -> None:
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(0.4)"])
    job = jw.register(project, name="x", kind="local", job_id=str(proc.pid), tool="gaussian", log="x.log")
    t0 = time.perf_counter()
    assert jw.wait(project, job.key, interval=0.05) == "finished"
    proc.wait()
    assert time.perf_counter() - t0 < 10


# ---------- hook 向けの一覧 ----------

def test_pending_lists_finished_unjudged_and_unwatched_jobs(project: Path) -> None:
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait()
    done = jw.register(project, name="done-one", kind="local", job_id=str(proc.pid), tool="gaussian", log="x.log")
    jw.watch_once(project, notify=lambda _m: None)
    live = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        jw.register(project, name="live-one", kind="local", job_id=str(live.pid), tool="gaussian", log="y.log")
        text = jw.pending_text(project)
    finally:
        live.kill()
        live.wait()
    assert "done-one" in text and "判定" in text
    assert "live-one" in text and "見張り" in text
    assert done.key in text


def test_pending_is_empty_when_all_is_well(project: Path) -> None:
    assert jw.pending_text(project) == ""


# ---------- コマンド ----------

def test_cli_register_then_judge(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    log = project / "work" / "gaussian" / "a.log"
    log.write_text(" Normal termination of Gaussian 16\n", encoding="utf-8")
    code = jw.main(["register", "--project", str(project), "--name", "a", "--kind", "local", "--id", "1",
                    "--tool", "gaussian", "--log", "work/gaussian/a.log"])
    assert code == 0
    key = capsys.readouterr().out.strip().splitlines()[-1].split()[-1]
    assert jw.main(["judge", "--project", str(project), key]) == 0
    assert "完走" in capsys.readouterr().out


def test_cli_errors_exit_2(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert jw.main(["judge", "--project", str(project), "no-such-job"]) == 2
    assert "見つかりません" in capsys.readouterr().err


def test_ensure_watcher_uses_tmux_when_available(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    launched: list[list[str]] = []
    monkeypatch.setattr(jw.shutil, "which", lambda name: "/usr/bin/tmux" if name == "tmux" else None)
    how = jw.ensure_watcher(project, launch=lambda cmd: launched.append(cmd))
    assert how == "tmux" and launched and launched[0][:3] == ["tmux", "new-session", "-d"]


def test_ensure_watcher_skips_when_a_fresh_one_runs(project: Path) -> None:
    beat = project / "office" / "computation" / "watch" / "_watcher.json"
    beat.parent.mkdir(parents=True, exist_ok=True)
    beat.write_text(json.dumps({"pid": os.getpid(), "beat": time.time()}), encoding="utf-8")
    assert jw.ensure_watcher(project, launch=lambda cmd: pytest.fail("should not launch")) == "already"


# ---------- レビューの指摘（2026-11-10）----------

def _dead_pid() -> int:
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait()
    return proc.pid


def test_watcher_clears_its_heartbeat_when_it_ends(project: Path) -> None:
    jw.register(project, name="a", kind="local", job_id=str(_dead_pid()), tool="gaussian", log="x.log")
    jw.watch(project, interval=0.05, notify=None, max_loops=5)
    launched: list[list[str]] = []
    assert jw.ensure_watcher(project, launch=launched.append) != "already" and launched


def test_a_heartbeat_from_a_dead_process_is_not_alive(project: Path) -> None:
    beat = project / "office" / "computation" / "watch" / "_watcher.json"
    beat.parent.mkdir(parents=True, exist_ok=True)
    beat.write_text(json.dumps({"pid": _dead_pid(), "beat": time.time(), "interval": 60}), encoding="utf-8")
    assert jw.ensure_watcher(project, launch=lambda cmd: None) != "already"


def test_concurrent_saves_do_not_crash(project: Path) -> None:
    import threading

    job = jw.register(project, name="a", kind="local", job_id="1", tool="gaussian", log="x.log")
    errors: list[BaseException] = []

    def hammer() -> None:
        try:
            for _ in range(300):
                jw._save(project, job)
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=hammer) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []


def test_a_stale_snapshot_does_not_undo_a_judgement(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log = project / "work" / "gaussian" / "a.log"
    log.write_text(" Normal termination of Gaussian 16\n", encoding="utf-8")
    job = jw.register(project, name="a", kind="local", job_id="1", tool="gaussian", log="work/gaussian/a.log")
    calls: list[str] = []

    def judged_meanwhile(j: jw.Job) -> tuple[bool, str]:
        jw._save(project, jw.dataclasses.replace(j, state="finished"))
        jw.judge(project, j.key)  # 確かめている間に判定が済んだ
        return False, "終了"

    monkeypatch.setattr(jw, "check", judged_meanwhile)
    jw.watch_once(project, notify=calls.append)
    assert jw.load_job(project, job.key).state == "judged" and calls == []


def test_judging_a_running_job_does_not_take_it_off_the_watch(project: Path) -> None:
    job = jw.register(project, name="a", kind="local", job_id="1", tool="gaussian", log="work/none.log")
    verdict = jw.judge(project, job.key)
    assert "走っている" in " ".join(verdict.evidence)
    assert jw.load_job(project, job.key).state == "running"


def test_an_unknown_verdict_is_not_saved_as_judged(project: Path) -> None:
    job = jw.register(project, name="a", kind="local", job_id=str(_dead_pid()), tool="gaussian", log="work/none.log")
    jw.watch_once(project, notify=None)
    assert jw.judge(project, job.key).status == "判定できない"
    assert jw.load_job(project, job.key).state == "finished"


@pytest.mark.parametrize("output,code,expected", [
    ("qstat: 77.pbs Job has finished, use -x or -H to obtain historical job information\n", 35, False),
])
def test_pbs_pro_finished_job(project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, output: str, code: int, expected: bool) -> None:
    _with_path(monkeypatch, _fake_bin(tmp_path, "qstat", f"printf '%s' '{output}' >&2\nexit {code}\n"))
    job = jw.register(project, name="x", kind="pbs", job_id="77.pbs", tool="gaussian", log="x.log")
    assert jw.is_running(job) is expected


def test_missing_qstat_over_ssh_is_reported(project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _with_path(monkeypatch, _fake_bin(tmp_path, "ssh", "echo 'bash: qstat: command not found' >&2\nexit 127\n"))
    jw.register(project, name="x", kind="pbs", job_id="77", host="hpc", tool="gaussian", log="x.log")
    jw.watch_once(project, notify=None)
    (saved,) = jw.load_jobs(project)
    assert saved.state == "running" and "qstat が見つからない" in (saved.last_check or "")
    assert "確かめられない" in jw.pending_text(project)


def test_local_job_with_a_host_is_rejected(project: Path) -> None:
    with pytest.raises(ValueError, match="local"):
        jw.register(project, name="x", kind="local", job_id="1", host="hpc", tool="gaussian", log="x.log")


def test_remote_log_is_read_over_ssh(project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _with_path(monkeypatch, _fake_bin(tmp_path, "ssh", "echo ' Normal termination of Gaussian 16'\nexit 0\n"))
    job = jw.register(project, name="x", kind="pbs", job_id="77", host="hpc", tool="gaussian", log="/work/u/ts1.log")
    jw._save(project, jw.dataclasses.replace(job, state="finished"))
    assert jw.judge(project, job.key).status == "完走"


def test_a_reused_pid_is_not_our_job(project: Path) -> None:
    job = jw.register(project, name="x", kind="local", job_id=str(os.getpid()), tool="gaussian", log="x.log")
    assert jw.is_running(job) is True
    jw._save(project, jw.dataclasses.replace(job, pid_started="Thu Jan  1 00:00:00 1970"))
    assert jw.is_running(jw.load_job(project, job.key)) is False


def test_register_never_overwrites_under_a_race(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    first = jw.register(project, name="same", kind="local", job_id="1", tool="gaussian", log="a.log")
    real_exists = Path.exists
    monkeypatch.setattr(Path, "exists", lambda self: False if self.name.startswith(first.key) else real_exists(self))
    second = jw.register(project, name="same", kind="local", job_id="2", tool="gaussian", log="b.log")
    assert second.key != first.key and jw.load_job(project, first.key).id == "1"


def test_wait_gives_up_when_the_job_cannot_be_checked(project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _with_path(monkeypatch, _fake_bin(tmp_path, "ssh", "exit 255\n"))
    job = jw.register(project, name="x", kind="pbs", job_id="77", host="hpc", tool="gaussian", log="x.log")
    assert jw.wait(project, job.key, interval=0.01, give_up_after=0.1) == "unknown"


def test_osascript_message_escapes_backslashes(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[list[str]] = []
    monkeypatch.setattr(jw.sys, "platform", "darwin")
    monkeypatch.setattr(jw.shutil, "which", lambda name: "/usr/bin/osascript")
    monkeypatch.setattr(jw.subprocess, "run", lambda cmd, **kw: seen.append(cmd))
    jw.os_notify('path C:\\work\\ "quoted"\\')
    script = seen[0][2]
    assert script.count('"') == 4 and '\\\\' in script


def test_watch_survives_an_error_in_one_round(project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    jw.register(project, name="x", kind="local", job_id=str(_dead_pid()), tool="gaussian", log="x.log")
    real = jw.watch_once
    calls = {"n": 0}

    def flaky(project: Path, notify=None, beat=None):  # noqa: ANN001
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("一時的な失敗")
        return real(project, notify, beat)

    monkeypatch.setattr(jw, "watch_once", flaky)
    jw.watch(project, interval=0.01, notify=None, max_loops=5)
    assert calls["n"] >= 2 and "一時的な失敗" in capsys.readouterr().err
