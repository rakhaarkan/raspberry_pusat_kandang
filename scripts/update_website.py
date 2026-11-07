#!/usr/bin/env python3

import subprocess
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime


# ==================================================
# KONFIGURASI
# ==================================================

PROJECT_DIR = Path("/home/rakha/Documents/Project_Kandang")

WEBSITE_DIR = Path(
    "/home/rakha/Documents/kandangayamrakha"
)

BRANCH = "main"

LOG_DIR = PROJECT_DIR / "logs"
LOG_FILE = LOG_DIR / "website_updater.log"

TIMEOUT = 120


# ==================================================
# LOGGING
# ==================================================

LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("website_updater")
logger.setLevel(logging.INFO)

handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=1_000_000,
    backupCount=5,
    encoding="utf-8"
)

formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(message)s"
)

handler.setFormatter(formatter)
logger.addHandler(handler)


# ==================================================
# GIT COMMAND
# ==================================================

def git(*args):

    command = [
        "git",
        *args
    ]

    result = subprocess.run(
        command,
        cwd=WEBSITE_DIR,
        capture_output=True,
        text=True,
        timeout=TIMEOUT
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or result.stdout.strip()
            or f"Git command gagal: {command}"
        )

    return result.stdout.strip()


# ==================================================
# UPDATE WEBSITE
# ==================================================

def update_website():

    logger.info("===== MEMULAI PEMERIKSAAN WEBSITE =====")

    try:

        # 1. Pastikan branch benar
        current_branch = git(
            "branch",
            "--show-current"
        )

        if current_branch != BRANCH:
            raise RuntimeError(
                f"Branch tidak sesuai: {current_branch}"
            )

        # 2. Pastikan tidak ada perubahan lokal
        local_changes = git(
            "status",
            "--porcelain"
        )

        if local_changes:
            raise RuntimeError(
                "Repository memiliki perubahan lokal. "
                "Update dibatalkan demi keamanan."
            )

        # 3. Ambil informasi terbaru dari GitHub
        logger.info("Memeriksa pembaruan GitHub...")

        git(
            "fetch",
            "--prune",
            "origin",
            BRANCH
        )

        # 4. Bandingkan commit lokal dan GitHub
        local_commit = git(
            "rev-parse",
            "HEAD"
        )

        remote_commit = git(
            "rev-parse",
            f"origin/{BRANCH}"
        )

        if local_commit == remote_commit:

            logger.info(
                "Website sudah versi terbaru. Tidak ada perubahan."
            )

            return True

        # 5. Pastikan GitHub hanya berada di depan
        behind = git(
            "rev-list",
            "--count",
            f"HEAD..origin/{BRANCH}"
        )

        ahead = git(
            "rev-list",
            "--count",
            f"origin/{BRANCH}..HEAD"
        )

        if int(ahead) > 0:
            raise RuntimeError(
                "Commit lokal berbeda dari GitHub. "
                "Update otomatis dibatalkan."
            )

        logger.info(
            f"Ditemukan {behind} commit baru."
        )

        # 6. Terapkan pembaruan secara fast-forward
        git(
            "merge",
            "--ff-only",
            f"origin/{BRANCH}"
        )

        # 7. Verifikasi hasil
        updated_commit = git(
            "rev-parse",
            "HEAD"
        )

        if updated_commit != remote_commit:
            raise RuntimeError(
                "Verifikasi commit setelah update gagal."
            )

        logger.info(
            f"Website berhasil diperbarui: {updated_commit}"
        )

        logger.info(
            "===== PEMBARUAN SELESAI ====="
        )

        return True

    except Exception as error:

        logger.error(
            f"PEMBARUAN GAGAL: {error}"
        )

        return False


# ==================================================
# MAIN
# ==================================================

if __name__ == "__main__":

    success = update_website()

    if success:
        print("Website sudah terbaru atau berhasil diperbarui.")
    else:
        print("Pembaruan gagal. Periksa log updater.")

        raise SystemExit(1)
