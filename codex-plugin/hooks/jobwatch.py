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
  ensure-watcher  見張りが動いていなければ起動する（tmux があれば tmux、無ければ切り離して）。
                  Codex の sandbox の中では起動しない（そこでは tmux・ssh・codex queue が使えない）。
                  sandbox の外で動く hook が、ターンの終わり・次の発言のときに起動する
  judge KEY  ログの完走の印・異常の印・できるはずのファイルで判定する（終了コードでは決めない）
  status     登録したジョブの一覧
  pending    hook 向け: 終わったが判定していないジョブ・見張りの無いジョブ
               [--start-watcher] 走っているジョブに見張りが無ければ、先に見張りを起動する

ジョブが終わると、OS の通知を出し、Codex で登録したジョブなら `codex queue` でそのセッションに伝える。
ssh が通らないとき（VPN・二段階認証）は「不明」として走っている扱いのまま残す（終わったとは言わない）。
"""
from __future__ import annotations

import argparse
import contextlib
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
import tempfile
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
# Codex が sandbox の中のコマンドに付ける環境変数。中では tmux のソケットを作れず（つなげず）、ssh も
# ~/.codex への書き込み（codex queue）もできない（2026-11-11 Codex 0.167 の実機）。承認済みの hook は外で動く
SANDBOX_ENV = ("CODEX_SANDBOX", "CODEX_SANDBOX_NETWORK_DISABLED")
SANDBOX_OFF = frozenset({"", "0", "false", "no", "off"})
LOCK = "_watcher.lock"  # 見張りは 1 プロジェクトに 1 本（同時に 2 本起動されたら後の方はすぐ終わる）
LOCK_FRESH = 60.0  # 中身がまだ書かれていない印は、これより新しければ使用中とみなす（秒）
START_FAILED = "_start_failed.json"
HOOK_START_WAIT = 3.0  # hook から起動したとき心拍を待つ（秒）
START_RETRY_AFTER = 600.0  # hook からの起動に失敗したら、これだけあけてから起動し直す（発言のたびに待たせない）

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
    pid_started: str | None = None  # ローカルのジョブのプロセスの開始時刻（PID の使い回しを見分ける）


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


def _write_json(path: Path, data: dict) -> None:
    """書き手ごとに別の一時ファイルに書いてから置き換える（見張りと wait が同時に書いても壊れない）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.stem}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def _save(project: Path, job: Job) -> None:
    _write_json(_watch_dir(project) / f"{job.key}.json", dataclasses.asdict(job))


def _update(project: Path, key: str, expect_state: str, **changes: object) -> Job | None:
    """保存の直前に読み直し、状態がまだ expect_state のときだけ書き換える（古い読み込みで上書きしない）。"""
    job = load_job(project, key)
    if job.state != expect_state:
        return None
    new = dataclasses.replace(job, **changes)
    _save(project, new)
    return new


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
    if kind == "local" and host:
        raise ValueError("local のジョブに --host は付けられません（別の計算機なら pbs か slurm で登録する）")
    tool_key, done_markers, fail_markers = _markers(tool, done, fail)
    template = Job(
        key="", name=name, kind=kind, id=str(job_id), log=log, done=done_markers, fail=fail_markers, host=host,
        tool=tool_key, expect_count=expect_count, outputs=tuple(outputs or ()), expect_minutes=expect_minutes,
        registered_at=_now(), codex_thread=os.environ.get("CODEX_THREAD_ID") or None,
        pid_started=_process_start(str(job_id)) if kind == "local" else None,
    )
    return _create(project, template)


def _create(project: Path, template: Job) -> Job:
    """同じ名前のジョブがあっても上書きしないよう、ファイルを排他的に作って key を決める。"""
    folder = _watch_dir(project)
    folder.mkdir(parents=True, exist_ok=True)
    base = f"{dt.date.today().isoformat()}-{_slug(template.name)}"
    for n in range(1, 1000):
        key = base if n == 1 else f"{base}-{n}"
        job = dataclasses.replace(template, key=key)
        try:
            with open(folder / f"{key}.json", "x", encoding="utf-8") as f:
                json.dump(dataclasses.asdict(job), f, ensure_ascii=False, indent=2)
        except FileExistsError:
            continue
        return job
    raise ValueError(f"同じ名前のジョブが多すぎます: {template.name}")


def _run(cmd: list[str], host: str | None, timeout: float = SSH_TIMEOUT) -> subprocess.CompletedProcess | None:
    """コマンドを走らせる（host があれば ssh 越し）。時間切れなら子プロセスごと止めて None。"""
    if host:
        cmd = ["ssh", "-o", "BatchMode=yes", "-o", f"ConnectTimeout={SSH_TIMEOUT // 2}", host, shlex.join(cmd)]
    try:
        proc = subprocess.Popen(
            cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace",
            start_new_session=os.name != "nt",
        )
    except OSError:
        return None
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(OSError):
            os.killpg(proc.pid, 9) if os.name != "nt" else proc.kill()
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.communicate(timeout=2)
        return None
    return subprocess.CompletedProcess(cmd, proc.returncode, out, err)


def _process_start(pid_text: str) -> str | None:
    """プロセスの開始時刻（POSIX の ps）。取れなければ None。"""
    if os.name == "nt" or not pid_text.isdigit():
        return None
    res = _run(["ps", "-o", "lstart=", "-p", pid_text], None, timeout=10)
    return res.stdout.strip() or None if res and res.returncode == 0 else None


def _pid_alive(pid: int) -> bool | None:
    if os.name == "nt":
        res = _run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], None, timeout=10)
        return None if res is None else str(pid) in res.stdout
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return None
    res = _run(["ps", "-o", "stat=", "-p", str(pid)], None, timeout=10)
    return not (res and res.stdout.strip().startswith("Z"))  # 終わったのに回収されていないプロセスは終わり扱い


def _local_check(job: Job) -> tuple[bool | None, str]:
    if not job.id.isdigit():
        return None, "不明: PID ではない"
    alive = _pid_alive(int(job.id))
    if alive and job.pid_started and _process_start(job.id) != job.pid_started:
        return False, "終了（同じ PID の別のプロセスが走っている）"
    return alive, {True: "走行中", False: "終了", None: "不明"}[alive]


def _remote_problem(res: subprocess.CompletedProcess | None, job: Job, tool: str) -> str | None:
    """ssh や問い合わせのコマンドの不調。無ければ None。"""
    if res is None:
        return "不明: 応答が無い（ssh・VPN・混雑）"
    text = res.stdout + res.stderr
    if job.host and res.returncode == 255:
        return "不明: ssh が通らない（VPN・二段階認証・鍵）"
    if res.returncode == 127 or "command not found" in text:
        return f"不明: {tool} が見つからない（ssh の先の PATH。ログインシェルの設定を確かめる）"
    return None


def _pbs_check(job: Job) -> tuple[bool | None, str]:
    res = _run(["qstat", "-f", job.id], job.host)
    problem = _remote_problem(res, job, "qstat")
    if problem:
        return None, problem
    text = res.stdout + res.stderr
    if "Job has finished" in text or "Unknown Job" in text or res.returncode in (35, 153):
        return False, "終了"
    if res.returncode != 0:
        return None, f"不明: qstat の終了コード {res.returncode}"
    m = re.search(r"job_state\s*=\s*([A-Z])", text)
    running = (m.group(1) in PBS_RUNNING_STATES and m.group(1) not in "FC") if m else True
    return running, "走行中" if running else "終了"


def _slurm_check(job: Job) -> tuple[bool | None, str]:
    res = _run(["squeue", "-h", "-j", job.id], job.host)
    problem = _remote_problem(res, job, "squeue")
    if problem:
        return None, problem
    if res.returncode != 0:
        return (False, "終了") if "Invalid job id" in res.stderr else (None, f"不明: squeue の終了コード {res.returncode}")
    running = bool(res.stdout.strip())
    return running, "走行中" if running else "終了"


def check(job: Job) -> tuple[bool | None, str]:
    """走っているか（True / False / 確かめられなければ None）と、その説明。"""
    if job.kind == "local":
        return _local_check(job)
    return _pbs_check(job) if job.kind == "pbs" else _slurm_check(job)


def is_running(job: Job) -> bool | None:
    """走っていれば True、終わっていれば False、確かめられなければ None（ssh が通らない等）。"""
    return check(job)[0]


REMOTE_LOG_BYTES = 5_000_000  # HPC のログは末尾のこれだけを読む


def _read_log(project: Path, job: Job) -> str | None:
    """ログの中身。手元に無く host があれば ssh で末尾を読む。読めなければ None。"""
    local = project / job.log
    if local.is_file():
        return local.read_text(encoding="utf-8", errors="replace")
    if job.host:
        res = _run(["tail", "-c", str(REMOTE_LOG_BYTES), job.log], job.host, timeout=60)
        if res is not None and res.returncode == 0:
            return res.stdout
    return None


def _scan_log(text: str, job: Job) -> tuple[list[str], list[str]]:
    done_lines, fail_lines = [], []
    for i, line in enumerate(text.splitlines(), 1):
        if any(m in line for m in job.fail):
            fail_lines.append(f"L{i}: {line.strip()}")
        elif any(m in line for m in job.done):
            done_lines.append(f"L{i}: {line.strip()}")
    return done_lines, fail_lines


def judge(project: Path, key: str) -> Verdict:
    """ログの印とできるはずのファイルで判定する（終了コード・ジョブ管理の表示では決めない）。判定は記録に残す。"""
    job = load_job(project, key)
    text = _read_log(project, job)
    if text is None:
        evidence = (f"ログが見つかりません: {job.log}",)
        if job.host and in_sandbox():
            evidence += ("Codex の sandbox の中では ssh できない。sandbox の外で実行する許可を求めて judge をやり直す",)
        verdict = Verdict("判定できない", evidence)
    else:
        done_lines, fail_lines = _scan_log(text, job)
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
    if job.state == "running":
        return Verdict(verdict.status, verdict.evidence + ("まだ走っている（見張りが終わりを確かめていない）ので、判定は記録しない",))
    if verdict.status != "判定できない":
        _save(project, dataclasses.replace(job, state="judged", verdict=verdict.status))
    return verdict


def _script() -> str:
    return str(Path(__file__).resolve())


def _command(*args: str) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline([Path(sys.executable).name, _script(), *args])
    return shlex.join(["python3", _script(), *args])


def finished_message(project: Path, job: Job) -> str:
    judge_cmd = _command("judge", "--project", str(project), job.key)
    return (
        f"[raw jobwatch] 計算「{job.name}」（{job.key}）が終わりました。"
        f"完走したかを判定し、ジョブ記録と Playbook に反映して、次に投入するものを決めてください: {judge_cmd}"
    )


def os_notify(message: str) -> None:
    """OS の通知（届かなくても止めない）。"""
    short = message[:200].replace("\\", "\\\\").replace('"', "'")
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


def _mark_finished(project: Path, key: str, notify: Notify | None) -> Job | None:
    """まだ走行中の記録なら「終わった」にして知らせる。別の書き手が先に進めていたら何もしない（二重に知らせない）。"""
    done = _update(project, key, "running", state="finished", finished_at=_now(), last_check="終了")
    if done is None:
        return None
    message = finished_message(project, done)
    if notify is not None:
        notify(message)
    _tell_codex(done, message)
    return done


def watch_once(project: Path, notify: Notify | None = os_notify, beat: Callable[[], None] | None = None) -> list[str]:
    """走っているジョブを 1 回ずつ確かめ、終わったものを記録して知らせる。終わったジョブの key を返す。"""
    finished = []
    for job in load_jobs(project):
        if job.state != "running":
            continue
        if beat is not None:
            beat()  # 確かめるのに時間がかかっても、見張りが止まって見えないように
        running, note = check(job)
        if running is False:
            done = _mark_finished(project, job.key, notify)
            if done is not None:
                finished.append(done.key)
        else:
            _update(project, job.key, "running", last_check=note)
    return finished


def _beat(project: Path, interval: float) -> None:
    _write_json(_watch_dir(project) / HEARTBEAT, {"pid": os.getpid(), "beat": time.time(), "interval": interval})


def watch(project: Path, interval: float = DEFAULT_INTERVAL, notify: Notify | None = os_notify,
          max_loops: int | None = None) -> int:
    """走っているジョブが無くなるまで見張る。回った回数を返す。終わるときは心拍を消す（次の見張りが起動できるように）。
    別の見張りが動いていれば（印を持っていれば）何もせずに 0 を返す（二重の通知・心拍の消し合いを防ぐ）。"""
    if not _claim(project):
        return 0
    loops = 0
    try:
        while max_loops is None or loops < max_loops:
            loops += 1
            _beat(project, interval)
            try:
                watch_once(project, notify, lambda: _beat(project, interval))
            except Exception as exc:  # noqa: BLE001 — 1 回の失敗で見張りを止めない
                print(f"{_now()} 見張りの 1 回に失敗（続ける）: {exc!r}", file=sys.stderr, flush=True)
            if not any(j.state == "running" for j in load_jobs(project)):
                break
            time.sleep(interval)
    finally:
        for name in (HEARTBEAT, LOCK):
            with contextlib.suppress(OSError):
                (_watch_dir(project) / name).unlink()
    return loops


def _claim(project: Path) -> bool:
    """見張りの印を取る。生きている別の見張りが持っていれば False。死んだ見張りの印は引き継ぐ。"""
    path = _watch_dir(project) / LOCK
    path.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(2):
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            if _lock_held(path):
                return False
            with contextlib.suppress(OSError):
                path.unlink()
            continue
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            out.write(str(os.getpid()))
        return True
    return False


def _lock_held(path: Path) -> bool:
    try:
        holder = int(path.read_text(encoding="utf-8").strip())
    except ValueError:  # 作られた直後でまだ pid が無い
        return time.time() - path.stat().st_mtime < LOCK_FRESH
    except OSError:
        return False
    return _pid_alive(holder) is not False


def wait(project: Path, key: str, interval: float = DEFAULT_INTERVAL, give_up_after: float = 3600.0) -> str:
    """そのジョブが終わるまで待つ。終わったら状態（finished / judged）を、確かめられない状態が
    give_up_after 秒続いたら "unknown" を返す（HPC に届かないまま黙って待ち続けない）。"""
    unknown_since: float | None = None
    while True:
        job = load_job(project, key)
        if job.state != "running":
            return job.state
        running, _note = check(job)
        if running is False:
            _mark_finished(project, key, notify=None)
            return load_job(project, key).state
        if running is None:
            unknown_since = unknown_since or time.time()
            if time.time() - unknown_since >= give_up_after:
                return "unknown"
        else:
            unknown_since = None
        time.sleep(interval)


def _watcher_alive(project: Path) -> bool:
    path = _watch_dir(project) / HEARTBEAT
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    stale = max(STALE_AFTER, 3 * float(data.get("interval", DEFAULT_INTERVAL)))
    if time.time() - float(data.get("beat", 0)) >= stale:
        return False
    pid = data.get("pid")
    return not isinstance(pid, int) or _pid_alive(pid) is not False  # 心拍を書いたプロセスが死んでいれば止まっている


def pending_text(project: Path) -> str:
    """hook 向け: 終わったが判定していないジョブと、見張りの無いジョブ。何も無ければ空。"""
    jobs = load_jobs(project)
    lines = []
    for job in jobs:
        if job.state == "finished":
            lines.append(f"- 終わったが判定していない: {job.name}（{job.key}）→ {_command('judge', '--project', str(project), job.key)}")
    running = [j for j in jobs if j.state == "running"]
    for job in running:
        if (job.last_check or "").startswith("不明"):
            lines.append(f"- 確かめられない: {job.name}（{job.key}）: {job.last_check}")
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
        # Windows: DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP（コンソールの Ctrl-C・閉じる操作を受けない）
        flags = {"creationflags": 0x00000008 | 0x00000200} if os.name == "nt" else {"start_new_session": True}
        subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=out, stderr=out, **flags)  # noqa: S603


def in_sandbox() -> bool:
    """Codex の sandbox の中か（SANDBOX_ENV を参照。「0」「false」などは sandbox でない）。"""
    return any(os.environ.get(name, "").strip().lower() not in SANDBOX_OFF for name in SANDBOX_ENV)


def _log_line(project: Path, text: str) -> None:
    with contextlib.suppress(OSError):
        _watch_dir(project).mkdir(parents=True, exist_ok=True)
        with (_watch_dir(project) / "_watcher.log").open("a", encoding="utf-8") as out:
            out.write(f"{_now()} {text}\n")


def ensure_watcher(project: Path, launch: Launch | None = None, respect_sandbox: bool = True) -> str:
    """見張りが動いていなければ起動する。"already" / "sandboxed" / "tmux" / "detached" を返す。

    Codex の sandbox の中では起動しない（"sandboxed"）。そこで起動した見張りは HPC にも Codex の
    セッションにも届かないため、sandbox の外で動く hook（start_watcher_if_needed）に任せる。
    respect_sandbox=False は sandbox の外だと分かっているとき（hook・--force）。
    tmux で起動できなければ、切り離したプロセスで起動する（二重になっても、後の見張りは印が取れずに終わる）。
    """
    _check_project(project)
    if _watcher_alive(project):
        return "already"
    if respect_sandbox and in_sandbox():
        return "sandboxed"
    launch = launch or _default_launch
    cmd = [sys.executable, _script(), "watch", "--project", str(project)]
    if shutil.which("tmux"):
        session = "raw-watch-" + hashlib.sha1(str(project).encode("utf-8")).hexdigest()[:8]
        log = shlex.quote(str(_watch_dir(project) / "_watcher.log"))
        try:
            launch(["tmux", "new-session", "-d", "-s", session, f"{shlex.join(cmd)} >> {log} 2>&1"])
            return "tmux"
        except (OSError, subprocess.CalledProcessError) as exc:
            print(f"tmux で起動できない（{exc}）。切り離して起動する", file=sys.stderr)
            _log_line(project, f"tmux で起動できない（{exc}）。切り離して起動する")
    launch(cmd)
    return "detached"


def start_watcher_if_needed(project: Path, launch: Launch | None = None) -> str | None:
    """hook 向け: 走っているジョブがあるのに見張りが無ければ起動し、起動の仕方を返す。何もしなければ None。
    hook は sandbox の外で動くので、sandbox の環境変数は見ない（引き継がれていても起動する）。"""
    if not any(job.state == "running" for job in load_jobs(project)):
        return None
    how = ensure_watcher(project, launch, respect_sandbox=False)
    return None if how == "already" else how


def _failed_recently(project: Path) -> bool:
    try:
        at = float(json.loads((_watch_dir(project) / START_FAILED).read_text(encoding="utf-8"))["at"])
    except (OSError, ValueError, KeyError, TypeError):
        return False
    return time.time() - at < START_RETRY_AFTER


def _start_from_hook(project: Path) -> str:
    """pending --start-watcher: 見張りを起動する。起動できなかったときだけ、その旨の 1 行を返す。
    失敗したら START_RETRY_AFTER 秒は起動し直さない（壊れた起動で発言のたびに待たせない）。"""
    if _failed_recently(project):
        return ""
    log = _watch_dir(project) / "_watcher.log"
    try:
        how = start_watcher_if_needed(project)
    except (OSError, subprocess.CalledProcessError) as exc:
        reason = str(exc)
    else:
        if how is None or wait_for_heartbeat(project, HOOK_START_WAIT):
            with contextlib.suppress(OSError):
                (_watch_dir(project) / START_FAILED).unlink()
            return ""
        reason = f"起動（{how}）から {HOOK_START_WAIT:.0f} 秒たっても心拍が無い"
    _write_json(_watch_dir(project) / START_FAILED, {"at": time.time(), "reason": reason})
    return (f"  （hook から見張りを起動できなかった: {reason}。ログ: {log}。"
            f"{START_RETRY_AFTER / 60:.0f} 分は hook から起動し直さない）")


def wait_for_heartbeat(project: Path, timeout: float = 5.0) -> bool:
    """起動した見張りが心拍を書くまで待つ（起動直後に「止まっている」と見えないように）。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _watcher_alive(project):
            return True
        time.sleep(0.2)
    return _watcher_alive(project)


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
    sub.choices["ensure-watcher"].add_argument(
        "--force", action="store_true", help="sandbox の外で実行していると分かっているとき（sandbox の環境変数を見ない）")
    sub.choices["pending"].add_argument(
        "--start-watcher", action="store_true", help="走っているジョブに見張りが無ければ、先に見張りを起動する（hook 向け）")
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


SANDBOXED_MESSAGE = (
    "見張り: Codex の sandbox の中なので、ここでは起動しない（sandbox の中では tmux が使えず、"
    "HPC にも Codex のセッションにも届かない）。このターンの終わりに raw の hook が sandbox の外で起動する"
    "（hook を信頼していることが前提）。すぐに要るときは、sandbox の外で実行する許可を求めて、--force を付けてもう一度実行する"
)


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
            if state == "unknown":
                note = load_job(project, a.key).last_check or "不明"
                print(f"[raw jobwatch] {a.key} を 1 時間確かめられません（{note}）。ユーザーに伝え、接続を直してから wait をやり直す")
                return 3
            print(finished_message(project, load_job(project, a.key)) if state == "finished" else f"状態: {state}")
            return 0
        if a.command == "watch":
            watch(project, a.interval)
            return 0
        if a.command == "ensure-watcher":
            how = ensure_watcher(project, respect_sandbox=not a.force)
            if how == "sandboxed":
                print(SANDBOXED_MESSAGE)
                return 0
            if how != "already" and not wait_for_heartbeat(project):
                print(f"見張りを起動しましたが（{how}）、5 秒たっても心拍がありません。status で確かめてください", file=sys.stderr)
                return 1
            print(f"見張り: {'すでに動いている' if how == 'already' else f'起動した（{how}）'}"
                  f"。{DEFAULT_INTERVAL:.0f} 秒おきに確かめる")
            return 0
        if a.command == "pending":
            note = _start_from_hook(project) if a.start_watcher else ""
            text = pending_text(project)
            if text:
                print(text + (f"\n{note}" if note else ""))
            return 0
        return _cmd_status(project)
    except (KeyError, ValueError) as exc:
        print(str(exc).strip("'\""), file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"失敗: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
