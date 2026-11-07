# GitHub Source Backup

Backup source code Project Kandang berjalan terpisah dari main.py
dan backup_upload.py.

## Jadwal
- Setiap hari pukul 02.00 WIB.
- Hanya membuat commit jika terdapat perubahan.
- Persistent timer menjalankan backup setelah Raspberry Pi kembali
  aktif apabila jadwal terlewat.

## Backup manual
sudo systemctl start kandang-github-backup.service

Atau:
python3 backup_github.py

## Pemeriksaan
systemctl status kandang-github-backup.timer
systemctl list-timers kandang-github-backup.timer
sudo journalctl -u kandang-github-backup.service -n 100 --no-pager

## Keamanan
- Hanya branch main.
- Tidak menggunakan force push.
- Tidak membuat commit kosong.
- Menolak file database, secret, runtime, dan virtual environment.
- Berhenti jika remote memiliki commit yang belum ada secara lokal.
