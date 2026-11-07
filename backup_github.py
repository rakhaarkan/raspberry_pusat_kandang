#!/usr/bin/env python3

import fcntl
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path("/home/rakha/Documents/Project_Kandang")
BRANCH = "main"
REMOTE = "origin"

BLOCKED_PARTS = {
    ".env", "venv", ".venv", "env", "n8n", "state",
    "secrets", "credentials", "__pycache__", ".cache"
}

BLOCKED_NAMES = {
    "config.env",
    "data_state.json",
    "data_sensor.json",
    "model_kandang.pkl",
}

BLOCKED_SUFFIXES = {
    ".db", ".sqlite", ".sqlite3", ".pem", ".key",
    ".pid", ".sock"
}


def log(message):
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    print(f"[{now}] {message}", flush=True)


def git(*args, check=True):
    result = subprocess.run(
        ["git", *args],
        cwd=PROJECT_DIR,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )

    if check and result.returncode != 0:
        raise RuntimeError(result.stdout.strip())

    return result


def is_blocked(path_text):
    path = Path(path_text)
    name = path.name.lower()
    parts = {part.lower() for part in path.parts}

    if name == ".env.example":
        return False

    if parts & BLOCKED_PARTS:
        return True

    if name in BLOCKED_NAMES:
        return True

    if path.suffix.lower() in BLOCKED_SUFFIXES:
        return True

    if name == ".env" or name.startswith(".env."):
        return True

    return False


def main():
    if not PROJECT_DIR.is_dir():
        raise RuntimeError("Direktori proyek tidak ditemukan.")

    lock_path = PROJECT_DIR / ".git" / "backup_github.lock"

    with lock_path.open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            log("Backup lain sedang berjalan. Proses dilewati.")
            return 0

        try:
            root = Path(
                git("rev-parse", "--show-toplevel").stdout.strip()
            ).resolve()

            if root != PROJECT_DIR.resolve():
                raise RuntimeError("Root repository tidak sesuai.")

            branch = git("branch", "--show-current").stdout.strip()

            if branch != BRANCH:
                raise RuntimeError(
                    f"Branch aktif {branch}, seharusnya {BRANCH}."
                )

            git("remote", "get-url", REMOTE)
            git("fetch", REMOTE, BRANCH)

            # Jangan mengambil alih perubahan yang sudah di-stage manual.
            if git("diff", "--cached", "--quiet", check=False).returncode != 0:
                raise RuntimeError(
                    "Ada perubahan yang sudah di-stage manual. "
                    "Selesaikan commit tersebut terlebih dahulu."
                )

            # Stage perubahan repository.
            git("add", "-A")

            staged = git(
                "diff", "--cached", "--name-only"
            ).stdout.splitlines()

            blocked = [p for p in staged if is_blocked(p)]

            if blocked:
                git("reset", "-q")
                raise RuntimeError(
                    "Ditemukan file terlarang: "
                    + ", ".join(blocked)
                    + ". File dikeluarkan dari staging."
                )

            # Commit hanya jika ada perubahan.
            if git("diff", "--cached", "--quiet", check=False).returncode != 0:
                timestamp = datetime.now().astimezone().strftime(
                    "%Y-%m-%d %H:%M:%S %Z"
                )

                git(
                    "commit",
                    "-m",
                    f"backup: automatic project snapshot ({timestamp})"
                )

                log("Commit berhasil dibuat.")
            else:
                log("Tidak ada perubahan baru.")

            # Periksa sinkronisasi dengan GitHub.
            ahead = int(git(
                "rev-list", "--count",
                f"{REMOTE}/{BRANCH}..HEAD"
            ).stdout.strip())

            behind = int(git(
                "rev-list", "--count",
                f"HEAD..{REMOTE}/{BRANCH}"
            ).stdout.strip())

            if behind > 0:
                raise RuntimeError(
                    f"GitHub memiliki {behind} commit yang belum ada "
                    "di Raspberry Pi. Sinkronkan secara manual."
                )

            if ahead == 0:
                log("Repository sudah sinkron. Tidak perlu push.")
                return 0

            git("push", REMOTE, BRANCH)

            log(f"Berhasil push {ahead} commit ke GitHub.")
            return 0

        except Exception as error:
            log(f"BACKUP GAGAL: {error}")
            return 1


if __name__ == "__main__":
    sys.exit(main())
