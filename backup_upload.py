import sqlite3
import datetime
import os

DB_PATH = "/home/rakha/Documents/Project_Kandang/kandang_ayam.db"
REMOTE = "backup_db_kandang:/backup_kandang"

def backup_and_upload():
    try:
        now = datetime.datetime.now()
        timestamp = now.strftime("%Y-%m-%d_%H%M%S")

        # nama file langsung pakai timestamp
        backup_path = f"/home/rakha/backup_{timestamp}.db"

        print("[INFO] Mulai backup SQLite...")

        # koneksi DB utama
        src = sqlite3.connect(DB_PATH, timeout=10)

        # pastikan WAL masuk ke DB utama
        src.execute("PRAGMA wal_checkpoint(FULL);")

        # buat DB backup
        dst = sqlite3.connect(backup_path, timeout=10)

        with dst:
            src.backup(dst)

        src.close()
        dst.close()

        print("[INFO] Backup selesai:", backup_path)

        # upload langsung ke folder utama (tanpa subfolder)
        cmd = f"rclone copy {backup_path} {REMOTE}/"
        print("[INFO] Upload:", cmd)

        result = os.system(cmd)

        if result == 0:
            print("[OK] Upload berhasil")

            # hapus file lokal
            os.remove(backup_path)
            print("[INFO] File lokal dihapus")
        else:
            print("[ERROR] Upload gagal, file tidak dihapus")

    except Exception as e:
        print("[ERROR] Backup gagal:", e)


if __name__ == "__main__":
    backup_and_upload()