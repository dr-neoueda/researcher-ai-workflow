#!/usr/bin/env python3
"""計算ジョブの見張り（raw）。投入したジョブを登録し、終わるまで見張り、完走したかをプログラム自身の出力で判定する。

raw では、裏で走らせる計算と HPC のジョブには必ず見張りを付ける（office/ の決まり）。使い方:

  register   ジョブを登録する（office/computation/watch/<key>.json）
               --name 名前 --kind local|pbs|slurm --id PID かジョブ ID [--host ssh の接続先]
               --tool gaussian|orca|cp2k|gromacs|quantum-espresso|vasp|lammps（完走の印が決まる）
               --log ログのパス [--done 完走の印 ...] [--fail 異常の印 ...] [--expect-count 印の数]
               [--output できるはずのファイル ...] [--expect-minutes 予想の分]
  wait KEY   そのジョブが終わるまで待つ（Claude Code はこれを裏で走らせ、終わったら再開する）
  watch      セッションを閉じても続く見張り（走っているジョブが無くなるまで。tmux の中で動かす）
  ensure-watcher  見張りが動いていなければ起動する（tmux があれば tmux、無ければ切り離して）
  judge KEY  ログの完走の印・異常の印・できるはずのファイルで判定する（終了コードでは決めない）
  status     登録したジョブの一覧
  pending    hook 向け: 終わったが判定していないジョブ・見張りの無いジョブ

ジョブが終わると、OS の通知を出し、Codex で登録したジョブなら `codex queue` でそのセッションに伝える。
ssh が通らないとき（VPN・二段階認証）は「不明」として走っている扱いのまま残す（終わったとは言わない）。
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

KINDS = ("local", "pbs", "slurm")
TOOL_MARKERS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "gaussian": (("Normal termination",), ("Error termination",)),
    "orca": (("ORCA TERMINATED NORMALLY",), ("ABORTING THE RUN", "error termination")),
    "cp2k": (("PROGRAM ENDED AT",), ("*** ABORT ***",)),
    "gromacs": (("Finished mdrun",), ("Fatal error",)),
    "quantum-espresso": (("JOB DONE.",), ("Error in routine",)),
    "vasp": (("General timing and accounting",), ("VERY BAD NEWS",)),
    "lammps": (("Total wall time",), ("ERROR:",)),
}
TOOL_ALIASES = {"qe": "quantum-espresso", "pw": "quantum-espresso", "pw.x": "quantum-espresso", "g16": "gaussian"}
WATCH_DIR = Path("office") / "computation" / "watch"
HEARTBEAT = "_watcher.json"
DEFAULT_INTERVAL = 120.0  # 秒
STALE_AFTER = 600.0  # 見張りの心拍がこれより古ければ止まっているとみなす（秒）
SSH_TIMEOUT = 20  # 秒
PBS_RUNNING_STATES = frozenset("QRHEWTSBM")

Notify = Callable[[str], None]
Launch = Callable[[list[str]], None]


@dataclass(frozen=True)
class Job:
    key: str
    name: str
    kind: str
    id: str
    log: str
    done: tuple[str, ...]
    fail: tuple[str, ...]
    host: str | None = None
    tool: str | None = None
    expect_count: int | None = None
    outputs: tuple[str, ...] = ()
    expect_minutes: float | None = None
    registered_at: str = ""
    state: str = "running"  # running → finished → judged
    finished_at: str | None = None
    verdict: str | None = None
    codex_thread: str | None = None
    last_check: str | None = None


@dataclass(frozen=True)
class Verdict:
    status: str  # 完走 / 完走していない / 異常終了 / 判定できない
    evidence: tuple[str, ...]


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _watch_dir(project: Path) -> Path:
    return project / WATCH_DIR


def _check_project(project: Path) -> None:
    if not (project / "office" / "secretary").is_dir():
        raise ValueError(f"raw の office/ が見つかりません: {project}")


def _save(project: Path, job: Job) -> None:
    folder = _watch_dir(project)
    folder.mkdir(parents=True, exist_ok=True)
    data = dataclasses.asdict(job)
    tmp = folder / f".{job.key}.json.tmp"
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(folder / f"{job.key}.json")


def _from_dict(data: dict) -> Job:
    fields = {f.name for f in dataclasses.fields(Job)}
    clean = {k: v for k, v in data.items() if k in fields}
    for name in ("done", "fail", "outputs"):
        clean[name] = tuple(clean.get(name) or ())
    return Job(**clean)


def load_jobs(project: Path) -> list[Job]:
    folder = _watch_dir(project)
    if not folder.is_dir():
        return []
    jobs = []
    for path in sorted(folder.glob("*.json")):
        if path.name == HEARTBEAT:
            continue
        try:
            jobs.append(_from_dict(json.loads(path.read_text(encoding="utf-8"))))
        except (json.JSONDecodeError, TypeError, OSError):
            continue
    return jobs


def load_job(project: Path, key: str) -> Job:
    path = _watch_dir(project) / f"{key}.json"
    if not path.is_file():
        raise KeyError(f"ジョブが見つかりません: {key}")
    return _from_dict(json.loads(path.read_text(encoding="utf-8")))


def _slug(name: str) -> str:
    slug = re.sub(r"[^\w.-]+", "-", name.strip(), flags=re.UNICODE).strip("-")
    return slug[:40] or "job"


def _markers(tool: str | None, done: list[str] | None, fail: list[str] | None) -> tuple[str | None, tuple, tuple]:
    key = (tool or "").strip().lower()
    key = TOOL_ALIASES.get(key, key) or None
    default_done, default_fail = TOOL_MARKERS.get(key or "", ((), ()))
    done_markers = tuple(done) if done else default_done
    fail_markers = tuple(fail) if fail else default_fail
    if not done_markers:
        raise ValueError(f"完走の印が分かりません（{tool}）。--done でログに出る完走の印を指定してください")
    return key, done_markers, fail_markers


def register(
    project: Path, *, name: str, kind: str, job_id: str, log: str, tool: str | None = None, host: str | None = None,
    done: list[str] | None = None, fail: list[str] | None = None, expect_count: int | None = None,
    outputs: list[str] | None = None, expect_minutes: float | None = None,
) -> Job:
    """ジョブを登録する。完走の印は --tool の既定か --done で決める（決まらなければ止める）。"""
    _check_project(project)
    if kind not in KINDS:
        raise ValueError(f"ジョブの種類が分かりません: {kind}（{' / '.join(KINDS)}）")
    tool_key, done_markers, fail_markers = _markers(tool, done, fail)
    base = f"{dt.date.today().isoformat()}-{_slug(name)}"
    key, n = base, 2
    while (_watch_dir(project) / f"{key}.json").exists():
        key, n = f"{base}-{n}", n + 1
    job = Job(
        key=key, name=name, kind=kind, id=str(job_id), log=log, done=done_markers, fail=fail_markers, host=host,
        tool=tool_key, expect_count=expect_count, outputs=tuple(outputs or ()), expect_minutes=expect_minutes,
        registered_at=_now(), codex_thread=os.environ.get("CODEX_THREAD_ID") or None,
    )
    _save(project, job)
    return job


def _run(cmd: list[str], host: str | None) -> subprocess.CompletedProcess | None:
    if host:
        cmd = ["ssh", "-o", "BatchMode=yes", "-o", f"ConnectTimeout={SSH_TIMEOUT // 2}", host, shlex.join(cmd)]
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=SSH_TIMEOUT, errors="replace")
    except (OSError, subprocess.TimeoutExpired):
        return None


def _local_running(pid_text: str) -> bool | None:
    try:
        pid = int(pid_text)
    except ValueError:
        return None
    if os.name == "nt":
        res = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True, errors="replace")
        return str(pid) in res.stdout
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    state = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
    return not state.startswith("Z")  # 終わったのに回収されていないプロセスは終わり扱い


def _pbs_running(job: Job) -> bool | None:
    res = _run(["qstat", "-f", job.id], job.host)
    if res is None or (job.host and res.returncode == 255):
        return None
    text = res.stdout + res.stderr
    if res.returncode != 0:
        return False if ("Unknown Job" in text or res.returncode == 153) else None
    m = re.search(r"job_state\s*=\s*([A-Z])", text)
    return (m.group(1) in PBS_RUNNING_STATES and m.group(1) not in "FC") if m else True


def _slurm_running(job: Job) -> bool | None:
    res = _run(["squeue", "-h", "-j", job.id], job.host)
    if res is None or (job.host and res.returncode == 255):
        return None
    if res.returncode != 0:
        return False if "Invalid job id" in res.stderr else None
    return bool(res.stdout.strip())


def is_running(job: Job) -> bool | None:
    """走っていれば True、終わっていれば False、確かめられなければ None（ssh が通らない等）。"""
    if job.kind == "local":
        return _local_running(job.id) if not job.host else None
    return _pbs_running(job) if job.kind == "pbs" else _slurm_running(job)


def _scan_log(path: Path, job: Job) -> tuple[list[str], list[str]]:
    done_lines, fail_lines = [], []
    with path.open(encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f, 1):
            text = line.rstrip()
            if any(m in text for m in job.fail):
                fail_lines.append(f"L{i}: {text.strip()}")
            elif any(m in text for m in job.done):
                done_lines.append(f"L{i}: {text.strip()}")
    return done_lines, fail_lines


def judge(project: Path, key: str) -> Verdict:
    """ログの印とできるはずのファイルで判定する（終了コード・ジョブ管理の表示では決めない）。判定は記録に残す。"""
    job = load_job(project, key)
    log = project / job.log
    if not log.is_file():
        verdict = Verdict("判定できない", (f"ログが見つかりません: {job.log}",))
    else:
        done_lines, fail_lines = _scan_log(log, job)
        expected = job.expect_count or 1
        missing = [o for o in job.outputs if not (project / o).is_file() or (project / o).stat().st_size == 0]
        if fail_lines:
            verdict = Verdict("異常終了", tuple(fail_lines[:5]) + tuple(done_lines[:3]))
        elif len(done_lines) < expected or missing:
            notes = [f"完走の印 {len(done_lines)} / {expected} 個（{' / '.join(job.done)}）"]
            notes += [f"できていないファイル: {o}" for o in missing]
            verdict = Verdict("完走していない", tuple(notes + done_lines[:3]))
        else:
            verdict = Verdict("完走", tuple(done_lines[:expected + 2]))
    _save(project, dataclasses.replace(job, state="judged", verdict=verdict.status))
    return verdict


def _script() -> str:
    return str(Path(__file__).resolve())


def _command(*args: str) -> str:
    return shlex.join([Path(sys.executable).name if os.name == "nt" else "python3", _script(), *args])


def finished_message(project: Path, job: Job) -> str:
    judge_cmd = _command("judge", "--project", str(project), job.key)
    return (
        f"[raw jobwatch] 計算「{job.name}」（{job.key}）が終わりました。"
        f"完走したかを判定し、ジョブ記録と Playbook に反映して、次に投入するものを決めてください: {judge_cmd}"
    )


def os_notify(message: str) -> None:
    """OS の通知（届かなくても止めない）。"""
    short = message.replace('"', "'")[:200]
    try:
        if sys.platform == "darwin" and shutil.which("osascript"):
            script = f'display notification "{short}" with title "raw"'
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=10)
        elif shutil.which("notify-send"):
            subprocess.run(["notify-send", "raw", short], capture_output=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        pass


def _tell_codex(job: Job, message: str) -> None:
    """Codex で登録したジョブなら、そのセッションに伝言を入れる（届かなくても止めない）。"""
    if not job.codex_thread or not shutil.which("codex"):
        return
    try:
        subprocess.run(
            ["codex", "queue", "--thread", job.codex_thread, "--message", message, "--resume"],
            capture_output=True, timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass


def _mark_finished(project: Path, job: Job, notify: Notify | None) -> Job:
    done = dataclasses.replace(job, state="finished", finished_at=_now(), last_check="終了")
    _save(project, done)
    message = finished_message(project, done)
    if notify is not None:
        notify(message)
    _tell_codex(done, message)
    return done


def watch_once(project: Path, notify: Notify | None = os_notify) -> list[str]:
    """走っているジョブを 1 回ずつ確かめ、終わったものを記録して知らせる。終わったジョブの key を返す。"""
    finished = []
    for job in load_jobs(project):
        if job.state != "running":
            continue
        running = is_running(job)
        if running is False:
            finished.append(_mark_finished(project, job, notify).key)
        else:
            _save(project, dataclasses.replace(job, last_check="走行中" if running else "不明"))
    return finished


def _beat(project: Path, interval: float) -> None:
    path = _watch_dir(project) / HEARTBEAT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"pid": os.getpid(), "beat": time.time(), "interval": interval}), encoding="utf-8")


def watch(project: Path, interval: float = DEFAULT_INTERVAL, notify: Notify | None = os_notify,
          max_loops: int | None = None) -> int:
    """走っているジョブが無くなるまで見張る。回った回数を返す。"""
    loops = 0
    while max_loops is None or loops < max_loops:
        loops += 1
        _beat(project, interval)
        watch_once(project, notify)
        if not any(j.state == "running" for j in load_jobs(project)):
            break
        time.sleep(interval)
    return loops


def wait(project: Path, key: str, interval: float = DEFAULT_INTERVAL) -> str:
    """そのジョブが終わるまで待つ。終わったら状態（finished / judged）を返す。"""
    while True:
        job = load_job(project, key)
        if job.state != "running":
            return job.state
        if is_running(job) is False:
            return _mark_finished(project, job, notify=None).state
        time.sleep(interval)


def _watcher_alive(project: Path) -> bool:
    path = _watch_dir(project) / HEARTBEAT
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    stale = max(STALE_AFTER, 3 * float(data.get("interval", DEFAULT_INTERVAL)))
    return time.time() - float(data.get("beat", 0)) < stale


def pending_text(project: Path) -> str:
    """hook 向け: 終わったが判定していないジョブと、見張りの無いジョブ。何も無ければ空。"""
    jobs = load_jobs(project)
    lines = []
    for job in jobs:
        if job.state == "finished":
            lines.append(f"- 終わったが判定していない: {job.name}（{job.key}）→ {_command('judge', '--project', str(project), job.key)}")
    running = [j for j in jobs if j.state == "running"]
    if running and not _watcher_alive(project):
        for job in running:
            lines.append(f"- 見張りの無いジョブ: {job.name}（{job.key}）")
        lines.append(f"  → 見張りを起動する: {_command('ensure-watcher', '--project', str(project))}")
    if not lines:
        return ""
    return "### 計算ジョブ（raw の見張り）\n" + "\n".join(lines)


def _default_launch(cmd: list[str]) -> None:
    if cmd[0] == "tmux":
        session = cmd[cmd.index("-s") + 1]
        subprocess.run(["tmux", "kill-session", "-t", session], capture_output=True)
        subprocess.run(cmd, check=True, capture_output=True)
        return
    log = Path(cmd[cmd.index("--project") + 1]) / WATCH_DIR / "_watcher.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as out:
        flags = {"creationflags": 0x00000008} if os.name == "nt" else {"start_new_session": True}
        subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=out, stderr=out, **flags)  # noqa: S603


def ensure_watcher(project: Path, launch: Launch | None = None) -> str:
    """見張りが動いていなければ起動する。"already" / "tmux" / "detached" を返す。"""
    _check_project(project)
    if _watcher_alive(project):
        return "already"
    launch = launch or _default_launch
    cmd = [sys.executable, _script(), "watch", "--project", str(project)]
    if shutil.which("tmux"):
        session = "raw-watch-" + hashlib.sha1(str(project).encode("utf-8")).hexdigest()[:8]
        launch(["tmux", "new-session", "-d", "-s", session, shlex.join(cmd)])
        return "tmux"
    launch(cmd)
    return "detached"


def _project_arg(value: str | None) -> Path:
    if value:
        return Path(value).resolve()
    here = Path.cwd().resolve()
    for candidate in (here, *here.parents):
        if (candidate / "office" / "secretary").is_dir():
            return candidate
    raise ValueError("raw の office/ が見つかりません（--project で指定してください）")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="計算ジョブの見張り（raw）")
    sub = parser.add_subparsers(dest="command", required=True)
    reg = sub.add_parser("register", help="ジョブを登録する")
    reg.add_argument("--name", required=True)
    reg.add_argument("--kind", required=True, choices=KINDS)
    reg.add_argument("--id", required=True, help="ローカルは PID、HPC はジョブ ID")
    reg.add_argument("--host", help="HPC の ssh の接続先（無ければこの計算機で qstat / squeue）")
    reg.add_argument("--tool", help="gaussian / orca / cp2k / gromacs / quantum-espresso / vasp / lammps")
    reg.add_argument("--log", required=True, help="ログのパス（プロジェクトからの相対）")
    reg.add_argument("--done", action="append", help="完走の印（ログに出る文字列。複数可）")
    reg.add_argument("--fail", action="append", help="異常の印（複数可）")
    reg.add_argument("--expect-count", type=int, help="完走の印が出る数（Gaussian の opt+freq なら 2）")
    reg.add_argument("--output", action="append", help="できるはずのファイル（複数可）")
    reg.add_argument("--expect-minutes", type=float, help="予想の所要時間（分）")
    for name in ("wait", "judge"):
        p = sub.add_parser(name)
        p.add_argument("key")
    sub.add_parser("watch")
    for name in ("watch", "wait"):
        sub.choices[name].add_argument("--interval", type=float, default=DEFAULT_INTERVAL)
    for name in ("status", "pending", "ensure-watcher"):
        sub.add_parser(name)
    for p in sub.choices.values():
        p.add_argument("--project", help="プロジェクトのフォルダ（省略時は今の場所から上へ探す）")
    return parser


def _cmd_register(project: Path, a: argparse.Namespace) -> int:
    job = register(
        project, name=a.name, kind=a.kind, job_id=a.id, log=a.log, tool=a.tool, host=a.host, done=a.done,
        fail=a.fail, expect_count=a.expect_count, outputs=a.output, expect_minutes=a.expect_minutes,
    )
    print(f"完走の印: {' / '.join(job.done)}（{job.expect_count or 1} 個）　異常の印: {' / '.join(job.fail) or 'なし'}")
    print(f"見張りを付けてください: {_command('ensure-watcher', '--project', str(project))}")
    print(f"登録しました: {job.key}")
    return 0


def _cmd_judge(project: Path, key: str) -> int:
    verdict = judge(project, key)
    print(f"判定: {verdict.status}（{key}）")
    for line in verdict.evidence:
        print(f"  {line}")
    return 0 if verdict.status == "完走" else 1


def _cmd_status(project: Path) -> int:
    jobs = load_jobs(project)
    if not jobs:
        print("登録したジョブはありません")
    for job in jobs:
        tail = f"・判定 {job.verdict}" if job.verdict else ""
        print(f"{job.key}  {job.state}（最後の確認: {job.last_check or '-'}{tail}）  {job.name}")
    print(f"見張り: {'動いている' if _watcher_alive(project) else '止まっている'}")
    return 0


def _utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    _utf8_stdio()
    a = _parser().parse_args(argv)
    try:
        project = _project_arg(a.project)
        if a.command == "register":
            return _cmd_register(project, a)
        if a.command == "judge":
            return _cmd_judge(project, a.key)
        if a.command == "wait":
            state = wait(project, a.key, a.interval)
            print(finished_message(project, load_job(project, a.key)) if state == "finished" else f"状態: {state}")
            return 0
        if a.command == "watch":
            watch(project, a.interval)
            return 0
        if a.command == "ensure-watcher":
            print(f"見張り: {ensure_watcher(project)}")
            return 0
        if a.command == "pending":
            text = pending_text(project)
            if text:
                print(text)
            return 0
        return _cmd_status(project)
    except (KeyError, ValueError) as exc:
        print(str(exc).strip("'\""), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
